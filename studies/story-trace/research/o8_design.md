# O8 -- Steiner up the west tower under the trace: the raw warp into 164 -> 165 -> 166 (FMV004 played out) -> the arrival in REAL 55 (the design)

**Status: DESIGN, offline.** Nothing is imported, built, deployed, launched or frozen. The inputs are `o8_route.md` and
`o8_research.json` in this folder (the reconciled route, the walks, the knight, the start, the movie, the seam, the
harness gaps, the fork gates, the rehearsal plan), the critic's ten problems (`critique.problems`, overriding the map
where they conflict) and the fourteen decisions the lead made on top of both (0.1). This file turns them into
code-level decisions in `o7_design.md`'s structure and keeps what O2-O7 learned. Every number below was read,
read-only, from the stock US `.eb` files (the research's listings `<R>/reconcile/L{164,165,166,55,70}.txt`, re-decoded
here with the kit at 7576c8d8), the live install, the O7 and O3 archives, the frozen `o7_predictions_v1.json` and the
code at the branch head. The checks of 0.2 were run here (`<S>/o8_design/probe1.py`, `race55.py`); `<R>` is
`C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX\4376ce2b-bd6e-4446-a9dc-f1510c3fc187\scratchpad\o8_research`
and `<S>` its parent scratchpad. **Revised by the design review** (two critiques: driver robustness, 13 items; claim
integrity, 11 items): every item re-checked in the bytes, the engine source, the harness and the archives
(`<S>/o8_design_rev/`: `race_any.py`, the stock 64 listing `L64.txt`), and adopted into the body or rejected with its
reason -- 11.3 logs each.

**The segment** (decision 1): New Game, `wait_frames(30)`, the trace armed, then in field 70 from FieldHUD (after 70 e0
t0 ip130 and ip249, before ip475) a raw `warp 164 342 1190` (S) / `warp 31256 342 1190` (F). Three visits:
- 164@342 (visit 1; EVT_ALEX1_AC_TOWER_L3; F 31256): Steiner granted at the spawn (2040, 3335) on loop 1 (published y
  ~4780); step 0, a `walk` up the first spiral to P1 (1342, 2252) at `at_y` [8800, 9150], then THE KNIGHT WAIT (the
  watched `Bit[3811]` until it reads 1: 164 e1 t1 ip230, the knight sitting); step 1, a `trigger` up the second spiral
  into e2 at the top, `until {y_gt: 12000}`, `to` 165, clearance 64 (THE PINCH: 2.5).
- 165@343 (visit 2; EVT_ALEX1_AC_TOWER_L4; F 31257): step 0, a `walk` to (1508, 4698) at `at_y` [11100, 11450];
  step 1, a `trigger` into e2, `until {y_gt: 15000}`, `to` 166.
- 166@344 (visit 3; EVT_ALEX1_AC_TOWER_L5; F 31258, byte-identical): NO control, NO cell. Rule 7 Confirms pages 307,
  308, 309 (Async), 311, 312, 313; ip345/ip380 `Byte[208]`; ip502 `Byte[8] := 0`; FMV004 PLAYED OUT (no `movies` key);
  ip863 `Int16[2] := 110`; ip871 `Field(55)`, raw on F.
- END on arrival in REAL 55 at 110 on BOTH sides, cut at 55 e0 t0 ip22 (`Bit[191] := 0`, same, emitted). On F that
  crossing is THE SEAM (31258 -> 55), recorded through the kept `e off fld 55` row.

SC 1190 throughout (no rung). No battle, choice, naming, ATE or minigame. A covered run writes EXACTLY 23 keys (20
writes + the 3-key chain 342 -> 343 -> 344 -> 110) in 29 emitted rows (9 / 9 / 11 a visit, 6 of them masked), no `c`
row. ~2.5 min a run (estimate; F8 freezes it).

What O8 newly puts under the trace: a walk whose evidence is an arrival at a HEIGHT (P1's XZ stacks three levels); a
door whose evidence is the player's height (`until` on y); a wait on a watched story bit that RACES the next door (the
knight); a played-out type-0 movie inside a no-control visit; and a segment whose fork side ends in a REAL field -- a
declared seam.

---

## 0. What this design decides, and what it found

### 0.1 Decided upstream (not relitigated)
1. **The segment** as above; `route` = `visits` = [164, 165, 166], `end_fields` [55], `side_ends` {S: [55], F: [55]},
   `members` = O4's twenty EXACTLY (never O1's 31205: `side_ends_of` refuses it); SC 1190.
2. **The fork side**: O4's deployed members 31256 (164), 31257 (165), 31258 (166); nothing imported, built or
   deployed. O8-BUILD pins each member to its donor per language AND pins 31258 byte-identical to 166 with its e6 t1
   `Field(55)` raw (6.1). On F a real 164/165/166 is V19 (game); real 55 is the end on both sides.
3. **The start**: residue `[[0,0,166],[1,0,4],[2,0,86],[3,0,1]]`; `start_first` 164 e0 t0 ip22; START requires 164 ip130
   `Byte[13]` 1 -> 1; three start-scoped olds read off O7's FROZEN pattern, the set DERIVED; TWO start reads, each with
   an EXPLICIT raced pin (critique #2); `carried` the 15 values DERIVED over O1-O7 less O8's targets, the knight's talk
   excluded from the scan; `start_dependent` []; every run forgets 164, 165, 31256, 31257 (4.5).
4. **New shared machinery, each OPT-IN, validation-only in `step_of`, FakeGame-tested, O1-O7 byte-identical** (one
   O3-pinned O2 test case flips from refused to accepted under S22 and is re-baselined by name: 11.3 B1): S20
   `at_y`, S21 `wait_flag` (THE KNIGHT WAIT: named apart from rule 6's `hold`, route_to's holds and `hold_stop`,
   critique #7; it runs out only on BOTH clocks and is the game's V8 only when the bit was PUBLISHED 0: 11.3 A4, B4,
   B5), S22 a y axis on `until` (a y term with y None RAISES, critique #6; the loss's y off the ring, read as route_to
   returns: 11.3 A3), S23 an opt-in per-step `unstick` (the pinch's FALLBACK only); an O8-local KNOWN_STEP_KEYS refusal;
   the rehearsal stops `flag_stop`, the pinch's hold stop `pinch_stop`, `movie_stop`, and R-FMV's one deliberate
   `movie_poke` (1.2, 7.1).
5. **THE PINCH**: weighed in 2.5 (decision: ONE trigger at clearance 64; the split rejected, with why). R-SPIRAL's F5 is
   the go/no-go; NO-GO -> `unstick: false` + `npcs: false` on 164 #1 and R-SPIRAL again; still NO-GO -> the owner. F5's
   record classifies every pinch stall (rejected ticks, blocker-sealed, slid: 11.3 A8), which predicts the middle rung.
6. **THE KNIGHT**: the exempt span for 164 e1 t1 ip230 is [step 0's FIRST attempt's frame0, step 1's FIRST attempt's
   frame0) (critique #1), the same span for WALK's exemption; ip230 before e2 t2 ip243 by line; a seat watch on 164 e1
   keyed by place, a CHECK (O8-KNIGHT, critique #9) on the readings -- an unread seat makes the run uncovered
   (A-KNIGHT: the instrument's, 11.3 B3), and its rows are written on whichever poll first can (11.3 A2).
7. **166 and the movie**: pages by rule 7 (report-only); a stray skip dialog answered by O7's `choices` row (never a
   `guard`), plus a second row for its measured option line (11.3 B6); O8-MOVIE (critique #4) -- a press, a skip dialog
   or the net's answer to one in the movie's span makes the run UNCOVERED (A-MOVIE: the dialog is press-only), the
   span's length is the live check, and a choice of any other shape there FAILS (11.3 A1, B3); `no_progress_s` by F8;
   `[Graphics] VSync "1"` pinned.
8. **The seam and the end**: O8-SEAM (a)-(f) against a registered `seam`; LANDING (a)-(d) (O7's (e) dropped); the end
   state's RACED SET derived from 55's bytes (55 e0 t0 walked to its RET; any other 55 store of an `end_state` target
   must sit behind a `Map.Byte[24]` case other than the arrival's: 11.3 B11); the preflight with a real end; O8-SEAM,
   LANDING and the raced end state dry-run against story-o3's archived F traces BEFORE the freeze (critique #3) --
   whose own raced set over stock 64 is EMPTY, so the fixture's STATE (c) runs on a typed fixture registration (8).
9. **FakeGame**: PART A captures the O7 baseline and FAKE_PINS_O7 FIRST; per-field clearance an instance parameter
   (defaults O7's); 164's `squeeze_slack` 12; H25 the height-triggered knight walker with a store; 166 as an H9 scene
   with `{movie: N}`; the real-55 driver test and its V19 twin (3).
10. **The checks layer** (5, 6), each with its mutant.
11. **The rehearsals** (7): R-FULL x2, R-SPIRAL x2, R-SPIRAL165 (optional), R-FMV x2 (+ one `movie_poke` run: 11.3
    A1), R-VOID x3 (last), F-SMOKE, F-PASS; none starts 03:45-04:45 (the nightly: 11.3 A10);
    F1-F14.
12. **The regression gate** extended to O7 (1.4), O8's items registered.
13. **PLAN.md's O8 section** with the O9 HANDOFF (9.1).
14. A parallel session may merge harness fixes into master; the lead merges master before the merge, never the builder.

### 0.2 Found while designing (each verified offline, read-only, at 7576c8d8)
1. **FAKE_PINS_O7, derived** (an AST function diff of `tools/harness/fakegame.py`, O6's merge 9c11d6c8 -> HEAD): O7
   ADDED `FakeGame.place_height`, `Levels.__init__/height/tri_nearest/tri_under/wall_gap/squeeze`,
   `_VisitBeat._scene_fires`, `_VisitBeat._wait_window`; CHANGED `FakeGame.__init__`, `_move_to`, `_objects_doc`,
   `_step_walkers`, `_door_knobs`, `_visit_steps`, `_VisitBeat._door/_page/_place/_run`. Already pinned (O5's class, O6's
   list; re-baselined by name): `_visit_steps`, `_door_knobs`, `_VisitBeat._door/_page/_place/_run`. No O3-O6 baseline
   pins any of the others (checked against the four baselines' `sources`). `FakeGame.__init__` stays unpinned: every knob
   edits it, and no baseline ever pinned it. So FAKE_PINS_O7 = `FakeGame.place_height`, `FakeGame._move_to`,
   `FakeGame._step_walkers`, `FakeGame._objects_doc`, `_VisitBeat._scene_fires`, `_VisitBeat._wait_window`, plus
   FAKE_PIN_CLASSES_O7 = `Levels` (every method). O8 edits `_move_to` (H26) and `_step_walkers` (H25): two re-baseline
   rows, each in the commit that edits it.
2. **H9 stages 166 with no fake edit.** The movie beat (`FakeGame.scene` / `_next_beat` / `_step_scene` /
   `_scene_press` / `_movie_over`) is O3-pinned (FAKE_PINS). A visit beat whose steps run out FINISHES and the scene
   moves on (`_Machine.on_tick` -> `finish`), so 166 is the scene [visit (prologue .. ip502), `{"movie": N, "skip":
   ...}`, visit (ip863, `field` "55")] then the 55 visit -- every store through `fake.script_store`, `_VisitBeat`
   untouched.
3. **The bytes' doors and instancing** (`probe1.py`): `scan_gateways` gives 164 (e2 -> 165 @343, e3 -> 163 @343), 165
   (e2 -> 166 @344, e3 -> 164 @344), 166 none, no face gate; `instanced_at7` (no entrance dispatch in any Main_Init:
   O7's over-approximation) gives 164@342 {object 1, 7; region 2, 3}, 165@343 {code 1; object 7; region 2, 3}, 166@344
   {object 3, 5, 6}; the first SetRegions are 164.e2 / 164.e3 / 165.e3 five points, 165.e2 four -- the research's.
4. **166's e2 is a storeless shared script.** `RunSharedScript(2)` at e6 t1 ip489 is its only caller; e2 stores no
   global. O6's `store_census6` "others" proof accepts exactly that (a shared entry run from an instanced entry holds
   no store); O7's `store_census7` adds a refusal of ANY `RunSharedScript` in an instanced entry, which 166 fails by
   construction -- so O8-CENSUS is O6's census over O7's instancing seam, without O7's extra refusal (6.1).
5. **THE RACED SET, derived** (`race55.py`): walking 55 e0 t0 from its start along the arrival's values (the pattern's
   last values over the raw start, SC 1190, Map vars 0), a `JMP_IF` back over an unresolved `B_SYSVAR` test falling
   through (the sound-sync loop), to the first long yield (ip387 `op_22(2)`), the stores are ip22, ip49, ip57, ip119,
   ip138, ip200 (each the value already held), ip255 `Int16[2]` 110 -> 106 and ip342 `Byte[8]` 0 -> 125. RACED =
   {Int16[2], Byte[8]} exactly; nothing else differs.
6. **`build_pins` already pins a site-less member byte-identical** (o5_hallway.py:1252-1255: with no in-chain operand
   every differing byte fails). The vacuity the research named arises only when 166 is OMITTED from `route_build`, as
   O7's BUILD_FIELDS omits "165" and "166". O8 lists `"166": []` AND adds the raw-exit pin (6.1).
7. **Every `until_ok` caller passes x and z only**: O2 :1134, O5 :802 / :811 / :824 / :1748, O6 :1006 / :1009 / :2173,
   O7 :1650, segment_drive :403 / :2741 / :2809. Under S22 a y term raises in each, so O8 never routes its table through
   O2-O7's goal or walk checks: O8's are O8-local and height-aware (critique #6).
8. **`unstick: false` bites only with `npcs: false`** (session.py:4495 `unstick = unstick or npcs`); with `slides` off,
   a hold deflected to under 0.35 of its travel raises the plain basis HarnessError, no marker (:3554-3563) -- the
   fallback's known cost (2.5, 10).
9. **`run_step` writes one row per attempt, each with its own `frame0`** (segment_drive.py:3051, :3085); rule 8 settles
   between attempts (:3577-3598). Hence the exemption span of decision 6.
10. **`Session.unwatch()` clears every watched bit** (session.py:7928); nothing watches during a step; `read_end_state`
    watches again at rule 1, after the drive left 166 -- no conflict with S21.
11. **The route-run scan** (decision 3): 164 e1 t3 (the knight's TALK) reads Bit[3848]-[3855]; 164 e7 t11 / t12 are
    reached only by `RunScriptSync(4, 250, 11)` / `(4, 250, 12)` at e1 t3 ip415 / ip452 (uid 250: the player entry e7).
    With tag 3 and what only it reaches dropped, no carried target is stored or read in 164@342, 165@343 or 166@344.
12. **Walk wall time**: story-o7 run 1's 154 walk (7725 u) took 18.7 s (t0 1.27 -> t1 19.98). That says nothing about
    `timeout_s` (revised, 11.3 A11): route_to passes its `timeout` only to `wait_control` at the walk's start, the
    landing wait and the facing step (session.py:4518, 4557, 4580, 4748), never to the walk itself, whose bounds are
    the ladder budgets (ROUTE_WAIT_BUDGET, ROUTE_PUSH_BUDGET, ROUTE_BLOCKERS, ROUTE_HOLDS) and the run's deadline (`go()`
    checks it between steps). O8's long legs (6404 / 6327 / 6832 u) therefore carry no `timeout_s` of their own:
    `steps_default`'s 20 is the start's control wait.
13. **The nightly ledger** (`.test-gate/latest.json`): red at d6b77975 (2026-10-05 04:00) on two tests,
    `test_a_live_miss_in_a_replay_is_retried_in_the_same_room_not_struck` and
    `test_a_bounce_the_partner_entered_is_a_replayed_step_that_leaves_him_where_he_was` -- the rung-3 replay tests that
    15f24eee made load-robust, merged before 421dbdfb. PART A's step 0 settles it (9).
14. **The archives**: story-o7 reads PROVEN with 17 checks (FROZEN .. JOIN), its offline check 6 PASS, its dry run
    174/174 on v1 (`o7_predictions_v1.json` sha256 2d646aaf48fa943e...). story-o3's F traces end 31213 e4 t1 ip820
    `Int16[2]` 0 -> 100, then 64 e0 t0 ip22 three frames later, then `e off fld 64`; 62's first store is ip26, not ip22 --
    so the O3 seam fixture reads each place's entry row off the bytes (8).
15. **Block 3's US text**: mes 307, 308, 309, 311, 312 and 313 each hold `[STNR]`; mes 56 holds `Env Play()`.
16. **Names**: no test name in `test_harness.py` holds `o8_`, `fake_spiral`, `fake_knight` or `fake_tower`; no fixture
    uses field ids 30860-30864.
17. **The step vocabulary** of every frozen table and `steps_default` (KNOWN_STEP_KEYS' base): `kind name goal start
    target until to expect sc wait_s then avoid closed_tris closed_floors beat attempts interrupts timeout_s confirm_s
    npcs overlay_ok immediate settle lunge_ticks tolerance min_depth exit_wait_s exit_slack climb clearance basis`.
18. **The live install's settings**: O7's frozen 31 keys hold; `[Graphics]` carries `Enabled` and `FieldTPS` but no
    `VSync`, which Memoria.ini line 71 sets to `1` today (unpinned until O8: decision 7). The engine DLLs hash ba976242
    (O7's pin) and field 70's override 2ce8887e (OVERRIDE70).
19. **164 e3 t2 ip215 and 165 e3 t2 ip215 are DEAD, not forbidden** (the research's census put them with the back
    doors). Each door's tag 2 sets `Map.Bit[162] := 1` at its own ip54 and tests `Map.Bit[162] == 0` at ip193 before
    the store; no other store to `Map.Bit[162]` exists in 164 or 165 (the listings), and Map variables are zeroed at
    load: O7's dead-door rule (its 160/162/163 ip199s). 164 e2 t2 ip215 is dead the same way; 165 e2 t2 ip205 is LIVE
    (165's e2 sets no `Map.Bit[162]`). The totals stand (164 25, 165 18, 166 18) and so does the key count (56); the
    classes become: 164 dead 5, forbidden 7; 165 dead 4, forbidden 1 (4.6). **Revised (11.3 B9): 164 e0 t0 ip97 and
    165 e0 t0 ip97 are DEAD too** -- each field's ip57 stores `Int16[9] := 385` before ip79 tests `Byte[13] == 2 &&
    Int16[9] < 0`, the reason ip119 is already dead; 166's ip97 is LIVE (its ip57 stores -1). So 164 error 3, dead 6;
    165 error 3, dead 5; `error_path` 10, `dead` 14; the totals and the 56 keys stand.
20. **The kept rows hold the seam's evidence.** `cut_at_end` keeps every row before the first end-place `w`/`r` row and
    the `e` rows after it, so the last `w`/`r` row before the cut is in `r["rows"]`, and the `e off fld 55` row is what
    `_walk_seams` reads as the crossing (storytrace.py:838-877): Seam(31258, 166, 55, fields [55], exit = the 166 e6 t1
    ip863 row). O3's `cut_row` (o3_prima_vista.py:1234-1238, inherited through O7) gives the cut row itself.
21. **The drive's observe hook cannot see inside a step.** `go()` calls `observe(st, ctx)` at the top of each poll
    (segment_drive.py:3406-3408), and `run_step` takes that poll's `st` as `frame0` (:3051). A step's own reads (route_to,
    the wait) reach only the session's ring (`ring_since`, :1712; 300 reads). So the knight's seat at the wait's end is
    read off the ring at the wait's read frame, and at step 1's `frame0` off the hook's own reading of that poll (1.3).

Found by the design review (11.3), each verified here:
22. **The door steps land on path A in game** (11.3 B2): all six of story-o6's door steps are `done` with `landed` None,
    `landed_frame` set and `flip_late` True ("landing path A" six times in its o6_report.txt), and O6's `walk_check`
    accepts `landed` None (o6_steiner.py:2149, :2178). O8's triggers carry `to` exactly as O6's door did.
23. **The skip dialog is press-only, and its No answer is unproven in game** (11.3 A1): only FieldHUD.OnKeyConfirm
    attaches "SkipMovieDialog" (FieldHUD.cs:275-285; no other opener in Assembly-CSharp), its hit area armed only by
    MBG.Play for a type-0 movie (MBG.cs:205-208); any answer but 0 re-arms the hit area (FieldHUD.cs:435-437); MBG.Update
    pauses the movie while the dialog is up (MBG.cs:534-541). O3's R-FULL-SKIP published it in full in both runs ("Do
    you want to skip\nthe movie?", "Yes", "No", `selected` 1) and answered YES (`g.choose(0)`); No has run only on the
    fake.
24. **Each tag-2 height test's consuming jump** (11.3 B7): 164 e2 t2 ip51, 164 e3 t2 ip51 and 165 e3 t2 ip51
    `JMP_IFNOT(L221)` (the RET at ip255), 165 e2 t2 ip47 `JMP_IFNOT(L215)` (the RET at ip245): each door fires when its
    test HOLDS. 164 e1 t1 ip187 `JMP_IF(L15)` loops back to ip175's `op_22(1)` WHILE ip178's test holds: that test is
    the knight's HOLD (published y < 8400), his release its negation (y >= 8400).
25. **A door's first global store trails its loss of control by at least 25 event ticks** (11.3 A5): 164 e2 t2
    ExitField at ip71, `op_22(25)` at ip165, then ip243; 165 e2 t2 ExitField at ip61, `op_22(25)` at ip155, then ip205.
26. **The raced sets, re-derived to RET** (11.3 B11; `<S>/o8_design_rev/race_any.py`): 55 e0 t0 from the arrival's
    values to its RET (ip565) races exactly what it races to its first yield, {Int16[2] 110 -> 106, Byte[8] 0 -> 125}:
    its window-3 resets ip419 / ip453 sit behind `Byte[13] == 9` / `Byte[14] == 9`, false (55's own ip119 / ip200 just
    stored 0). Outside e0 t0 only e10 t1 ip568 / ip582 (`UInt16[0] := 1400`, behind `SWITCH(Map.Byte[24])` case 3; 55 e0
    t0 ip247 sets 1 on this arrival -- but e1 t1 advances it on the scene's handshakes, so case 3 IS reachable: SC left
    the live read, 11.4 "The review" #3) store an `end_state` target; e8 t1's case-3 stores (UInt16[21], Byte[303],
    Byte[4], UInt16[19], Byte[17], Byte[18]) hold none; e7 t2 (region 7's door) stores only the raced pair. And stock
    64 from story-o3's arrival values (SC 1155; Int16[2] 100: the SWITCHEX default; Byte[8] 125 from 63 e14 t1 ip805)
    races NOTHING to its RET (ip1053): Bit[191], Bit[184], Int16[9] -1, Byte[13] 0, Int16[11] -1, Byte[14] 0, Bit[3815]
    0, Byte[475] 0 and Byte[8] 125 are each the value held. O3's raced set is EMPTY (the fixture's consequence: 8).
27. **The knight publishes `talk_r` 410 before ip190's SetWalkSpeed(15), 395 after** (11.3 A13): `4 x (talkRad +
    player.talkRad) + speed + 60` (HarnessAgent.cs:2360) = 4 x (30 + 50) + 30 + 60, then + 15 + 60; story-o7's R-FULL
    archive reads him at (249, y 11255, 4630), r 220, talk_r 410, `range` False, `talk` True (frame 5472). He is
    talk-only, so no planner disc reads it (session.py:5265-5266).

### 0.3 What O2-O7's builds taught, and where O8 applies it
- **A frozen segment's dry run reads predictions only through its own segment** (O7's freeze moved O6's 'naming-of'
  unit and failed G36): `o8_dryrun` reads through `frozen_through(8)`; C2 extends the glob test to D8 (8, 9 C2).
- **Never pin in a test a value the lead's in-game steps change** (O2, O4, O5, O6): no test reads the draft's
  `rehearsals`, `rehearsal_fps`, `rehearsed`, a budget, a deployed flag or a gate witness (9).
- **A check that cannot fail is worse than none** (O7's review #4: a typed `start_scoped` list): every list a check
  rests on is DERIVED and compared -- the start-scoped set, the carried values, the raced set, the closures, the gates,
  the seat (4.5, 4.9, 6.1); zero seams FAILS (5.3); a y term with no height RAISES (S22); an unknown step key FAILS
  (KNOWN_STEP_KEYS8); a gate is read through its consuming jump, so a flipped jump FAILS (11.3 B7); the story-o3
  fixture asserts its EMPTY raced set before STATE (c) judges a typed registration, never a vacuous pass (8, 11.3 B11).
  And its converse, THE PAIRED-WALK LAW: a miss of the driver's or the instrument's makes its run uncovered, never a
  failed check (A-MOVIE, A-KNIGHT, S21's unpublished watch: 11.3 A1, A4, B3).
- **The partial-run count reads the registry** (O7's 11.4 A #1) and `fake_pins_*` raises on a missing name (A #2): reused.
- **The A0b replay goes into its REQUIRED tuple at A0b** (A #3), before the selection item joins (B4).
- **Re-run only a driver load class** (A #4, B #13): 9's load-robust rule, V8 never re-run.
- **A held walker publishes `moving` False** (B #6): H25's `start` reuses `_held`.
- **Grants are read off the ring, not the poll** (C #7) and **the ladder tap counts `_blocker_ahead`** (C #8): O7's
  recorder and taps are reused (7.1).
- **STATE (c) matches at the side's own field of the place** (C #3): inherited, now with two targets.
- **`race_site` catches the armed-before race** (review #6): kept, with O8's races explicit (4.5).
- **A recalibration drops the seed** (review #7): inherited; O8 seeds 164 and 165 only.
- **WindowAsync is not WindowSync** (review #1, H24): 166's 309 is staged async (3.4).
- **A re-armed one-shot loops instead of reaching V7** (B #8): no O8 test relies on a second interruption.

---

## 1. Module layout

### 1.1 Files

| File (in `studies/story-trace/` unless a path is given) | | What it holds |
|---|---|---|
| `segment_regress.py` | edit, FIRST (A0) | The gate extended to O7: G0'''''' `--capture-o7`, G40-G43 (1.4), `FAKE_PINS_O7` + `FAKE_PIN_CLASSES_O7`, `fake_pins_o7()`, `o7_pin_names`, G21 over FIVE baselines, `--baseline-o7`; `PYTEST_K_O8`, `REQUIRED_TESTS_O8` (empty at A0); G44 joins at B4, G45 at C2. |
| `research/o7_regress_baseline.json` | new, FIRST (A0) | The captured O7 baseline (LF, `-text`), its `sources` included. |
| `research/o7_fake_replay.json` | new (A0b) | O7's route and O7's level, squeeze and walker scenes on the hand-stepped fake, before any O8 fake edit (3.5). LF, `-text`. |
| `segment_drive.py` | edit (A1-A3) | S20 `at_y`, S21 `wait_flag` (`_Drive.wait_flag`: both clocks, the published count), S22 the y axis on `until` (`until_ok` -- its keys validated first --, `has_y`, `loss_y`, both trigger executors), S23 the opt-in `unstick` (`walk_kw`); `step_of`'s validation; `run_step`'s row keys. |
| `tools/harness/fakegame.py` | edit (B1, B2) | H26 the per-field clearance (`clearances`, `_clearance`, read by `_move_to` and `_pushed_out`); H25 the knight walker (`_step_walkers`: `start`, `store`, the height-aware pair rule for an H25 body). |
| `ff9mapkit/tests/test_harness.py` | edit | The tests of 1.2, 3 and 9; the builder `_o8_route` and its helpers (3.6); the O7 replay (3.5); the registry test's body (1.4); `test_segment_dryrun_globs_close_at_their_segment` extended to O8 (C2); and ONE case of `test_o2_step_of_refuses_a_step_its_executor_cannot_run` (A2: its `until={"y_le": 0}` becomes `{"w_le": 0}`, an O3-baseline pin re-baselined by name in A2's commit -- 11.3 B1). No other existing body changes. |
| `o8_west_tower.py` | new (C1) | `O8Segment(o7_castle_walk.O7Segment)` and its module functions (1.3). |
| `o8_forks.json` | new (C1) | The chain manifest: O4's, reused, the seam declared (6.4). |
| `o8_dryrun.py` | new (C1, joined to the gate at C2) | Synthetic sessions, the story-o3 seam fixture, units, offline mutants (section 8); `as_if_frozen(pred)`, `--as-if-frozen`; reads predictions through `o7_dryrun.frozen_through(8)`. |
| `o8_rehearse.py` | new (C3) | R-FULL, R-SPIRAL, R-SPIRAL165, R-FMV (its `movie_poke` run), R-VOID, F-SMOKE, F-PASS for `tools/play.py` (section 7). |
| `.gitattributes` | edit | `research/o7_regress_baseline.json -text` (A0); `research/o7_fake_replay.json -text` (A0b); `o8_predictions*.json -text` (C1). |
| `PLAN.md` | edit (C4) | The O8 section: "draft: rehearsals pending, freeze pending", the O9 handoff (9.1). |

NOT edited: `o1_*` .. `o7_*` (every module, dry run, rehearse script, frozen predictions: O8 overrides O7's methods on
its own subclass and calls O7's module functions, never edits them), `tools/harness/session.py` (S20-S23 use the
session's existing `watch`, `unwatch`, `wait_for`, `route_to(unstick=...)` and ring), `tools/harness/channel.py`, the
agent, `ff9mapkit/ff9mapkit/storytrace.py`. `o7_castle_walk` (and through it O6-O2) is imported as shared code; its
outputs are the gate (G40-G43).

### 1.2 The shared changes (each opt-in; O1-O7 byte-identical)

Every frozen table through O7 carries none of the new keys and no `y_` term, so `step_of`, `until_ok`, `x_walk`,
`x_trigger`, `x_trigger_to`, `walk_kw` and `run_step` return and write exactly what they did. `step_of`'s new checks
are VALIDATION ONLY: they raise or pass, and never add, drop or normalise a key (critique #5:
`test_segment_step_of_reads_every_frozen_table_unchanged` reads every frozen file, a future `o8_predictions_v1.json`
included, and asserts `{**steps_default, **raw}`).

**What flips between refused and accepted** (the claim review's #1, grepped in the tests, every study module, every
frozen table and every baseline -- not only for message text): exactly ONE input. S22 makes a `y_` term a valid `until`
axis, so `step_of(pred, trigger with until={"y_le": 0})` -- refused today -- is accepted; that very input is a case of
`test_o2_step_of_refuses_a_step_its_executor_cannot_run` (test_harness.py:13534), which G12 collects and the O3
baseline's `sources` AST-pins. A2 changes that case to `until={"w_le": 0}` with the match `"x\\|z\\|y"` (refused under
S22 as today's `y_le` was before it) and re-baselines the test by name in A2's commit (`--rebaseline-source
"ff9mapkit/tests/test_harness.py::test_o2_step_of_refuses_a_step_its_executor_cannot_run" --reason ...`): PART A's ONE
re-baseline row. Nothing else flips: no frozen table, test or dry-run table carries `at_y`, `wait_flag` or a step-level
`unstick` (S20/S21/S23's new refusals meet no existing input; `unstick` appears only as route_to's keyword), no other
`y_` until exists (O7's `y_gt` lives in region `branches`, never an `until`), and the old "x|z + _" message is matched
only as `"x\\|z"`, which the new "x|z|y + _" text still holds.

**S20 -- `at_y`, THE ARRIVAL'S HEIGHT** (decision 4(a); PART A, A1). A walk's arrival proven on a level: P1's XZ
stacks three levels (tris 11, 53 and 98: PSX -3961, -8958, -13893), so "within tolerance of the goal" says nothing
about which.
```python
#: S20/S21 (research/o8_design.md 1.2): the keys only a walk may carry -- its arrival's height band and THE KNIGHT WAIT.
WALK_ONLY = ("at_y", "wait_flag")
#: S21: a wait_flag's keys, exactly these.
WAIT_FLAG_KEYS = ("flag", "value", "timeout_s")
#: S21: the highest gEventGlobal bit (Byte[2048]).
MAX_FLAG_BIT = 16383
```
`step_of` (after S17-S19's refusals, before `target`/`until`): a `WALK_ONLY` key on a step whose kind is not `walk`;
an `at_y` that is not two numbers (a bool is no number) with the first under the second. In `x_walk`, after today's
done conditions (control held in this field, within `tolerance`, route_to's `reached`):
```python
        band = step.get("at_y")                            # S20 (opt-in): the arrival's height, published y
        if band is not None:
            y = st.player_y
            out["at_y"] = {"band": [float(band[0]), float(band[1])], "y": None if y is None else round(y, 1)}
            if y is None or not float(band[0]) <= y <= float(band[1]):
                out["why"] = (f"the walk ended {d:.0f}u from its goal at published y "
                              + ("unread" if y is None else f"{y:.0f}")
                              + f", outside at_y {list(band)}: not the goal's level")
                return "failed", out
        if step.get("wait_flag") is not None:              # S21 (opt-in): THE KNIGHT WAIT, at the proven point
            return self.wait_flag(step, out)
        return "done", out
```
A failed `at_y` spends an attempt like any short walk (the next attempt re-plans from where he stands; V7 at the last).

**S21 -- `wait_flag`, THE KNIGHT WAIT** (decision 4(b); critique #7's name: never `hold`, which already means rule 6's
readiness hold, route_to's smooth-walk holds and O7's `hold_stop`; PART A, A1). `step_of`: `wait_flag` on a walk only
(WALK_ONLY), and only with `at_y` (the wait begins at a proven point); a dict of exactly `WAIT_FLAG_KEYS`; `flag` an int
in 0..`MAX_FLAG_BIT`, `value` 0 or 1, `timeout_s` a positive number (no bool for any).
```python
    def wait_flag(self, step: dict, out: dict) -> tuple:
        """S21, THE KNIGHT WAIT (research/o8_design.md 1.2): standing at a walk's proven goal with control held, press
        nothing until the watched gEventGlobal bit ``flag`` reads ``value``: ``g.watch(flag)`` (the agent publishes
        ``flags`` every 2 frames: no store, no trace row), ``g.wait_for`` the bit, control gone or another field -- and
        ``g.unwatch()`` in a ``finally``. In order: the run's deadline cut the wait -> V13 by the driver (the budget);
        the field changed -> V11 by the GAME (nothing was pressed: only the game's script moves the field; O8-GOALS
        (g5') proves the wait point clear of every exit); the bit read -> done; control gone -> the landing judge
        (door_loss), else interrupted. The wait RUNS OUT only once BOTH clocks ran ``timeout_s`` -- the wall's and the
        GAME's (``_game_seconds``: the fake's published ``rt``, else the engine's state.json write time, which in game
        IS the wall's): a starved harness stretches the wall's alone, never the game's (the claim review's #5). Run out,
        it is V8 by the GAME only when the window's last sample PUBLISHED the bit -- it latches on the route (O8-CENSUS:
        164's only store to Bit[3811] is e1 t1 ip230 := 1), so its last published value is its value throughout -- and
        V13 by the DRIVER when that sample carried no bit (the watch dropped: AppendWatch publishes ``"flags":{}`` on
        any fault, HarnessAgent.cs:2162-2166 -- the instrument's: the reviews' A4 / B4). The row's ``wait_flag``:
        ``{flag, value, read, frame0, frame, s, game_s, published, last}`` (``published`` the distinct frames that
        carried the bit, ``last`` its last published value)."""
        from harness import HarnessError
        from harness.session import _game_seconds
        g, fid = self.g, self.fid
        wf = step["wait_flag"]
        flag, value, limit = int(wf["flag"]), int(wf["value"]), float(wf["timeout_s"])
        st0, t0 = g.state, time.time()
        c0 = _game_seconds(st0)
        rec = out["wait_flag"] = {"flag": flag, "value": value, "read": None, "frame0": st0.frame, "frame": None,
                                  "s": None, "game_s": None, "published": 0, "last": None}
        seen: set = set()

        def has(s) -> bool:
            v = s.flag(flag)
            if v is not None and s.frame not in seen:       # every sample the wait reads: the bit as published
                seen.add(s.frame)
                rec["last"] = int(v)
            return v is not None and int(v) == value

        def game_ran(s):
            c = _game_seconds(s)
            return None if c is None or c0 is None else c - c0

        st, end = None, None
        g.watch(flag)
        try:
            while end is None:
                left = self.deadline - time.time()
                if left <= 0:
                    end = "deadline"
                    break
                try:
                    st = g.wait_for(lambda s: has(s) or not s.control or s.field_id != fid,
                                    timeout=min(limit, left), what=f"the flag wait: Bit[{flag}] == {value}")
                    end = "event"
                except HarnessError as err:
                    if "live samples" not in str(err):
                        raise
                    st = g.state                        # one read: the window's last sample
                    ran = game_ran(st)
                    if time.time() - t0 >= limit and (ran is None or ran >= limit):
                        end = "out"                         # both clocks ran it (one it cannot read: the wall's)
        finally:
            g.unwatch()
        ran = None if st is None else game_ran(st)
        rec.update(s=round(time.time() - t0, 2), game_s=None if ran is None else round(ran, 2), published=len(seen))
        if end == "deadline":
            out.update(v="V13", by="driver", why=f"the run's budget ran out during the flag wait for Bit[{flag}] == "
                                                 f"{value}, {rec['s']:.1f}s into its {limit:.0f}s: the budget")
            rec["read"] = False
            return "void", out
        if st.field_id != fid:
            new = self.switch(out, "the flag wait", float(step["exit_wait_s"]))
            if new is not None:
                out.update(landed=new, v="V11", by="game",
                           why=f"the field left {fid} during the flag wait, nothing pressed: landed in {new} (place "
                               f"{place(new, self.members)})")
                return "void", out
            st = g.state
        if has(st):
            rec.update(read=True, frame=st.frame)
            return "done", out
        if not st.control:
            out["lost"] = sample(st)
            why = f"control went during the flag wait for Bit[{flag}] == {value}"
            verdict = self.door_loss(step, out, why)
            if verdict is not None:
                return verdict
            out["why"] = why
            return "interrupted", out
        rec["read"] = False                                 # run out on both clocks, control held, the bit unread
        if st.flag(flag) is None:
            out.update(v="V13", by="driver", why=f"the watch never published Bit[{flag}] at the wait's end "
                                                 f"({len(seen)} sample(s) carried it): the instrument's")
        else:
            out.update(v="V8", by="game", why=f"Bit[{flag}] read {int(st.flag(flag))}, never {value}, through "
                                              f"{limit:.0f}s of both clocks of a wait begun at the proven point "
                                              f"(published in {len(seen)} sample(s); the bit latches)")
        return "void", out
```
The deadline is a `void` verdict, not the bare HarnessError `go()` raises when its own loop runs out of budget
(segment_drive.py:3605): `run_step` then writes the row and raises `self.void("V13", "driver", ...)` with the cell --
still the driver's V13 (a STOPPED HarnessError reads V13 too, segment_trace.py:841-843, but carries no cell, and
VOID-ASYM reads cells). A wait the wall's clock alone ran out loops on (bounded by the run's deadline: a driver class
the load-robust rule may re-run, section 9), so a starved fake never mints the GAME's V8. An `interrupted` wait re-runs
the whole walk when control comes back (its goal is where he stands: a short re-walk, then the wait again).

`run_step` copies the executor's `at_y` and `wait_flag` onto the row when present, and `unstick` from the step:
```python
        for key in ("clearance", "basis", "unstick"):      # S18/S19/S23 (opt-in): on the row only when carried
            if step.get(key) is not None:
                row[key] = step[key]
        for key in ("at_y", "wait_flag"):                  # S20/S21 (opt-in): the arrival's height, the wait
            if rec.get(key) is not None:
                row[key] = rec[key]
```

**S22 -- A y AXIS ON `until`, AND THE LOSS'S HEIGHT** (decision 4(c); critique #6; PART A, A2).
```python
def until_ok(expr: dict, x, z, y=None) -> bool:
    """Whether (``x``, ``z``) -- and, S22 (research/o8_design.md 1.2), his PUBLISHED height ``y`` (pos[1] = -f[1]: it
    rises as he climbs) -- satisfies an ``until`` predicate: ``{"x_le": 900}``, ``{"y_gt": 12000}`` -- every comparison
    (``x|z|y`` + ``_`` + ``le|lt|ge|gt``) must hold. EVERY KEY IS CHECKED FIRST (the claim review's #10): an unknown
    key raises, and so does a ``y`` term with ``y`` None, whatever x and z read -- a height test on a path that
    supplies no height is a check that cannot fail (the critic's #6), never a False; then a missing x or z is False
    (today's). Callers that may hold no height test for it themselves (O8-WALK (a): "no height"; the executors: V13)
    and never call this with ``y`` None on a y term."""
    for k in expr:
        axis, _, op = k.partition("_")
        if axis not in ("x", "z", "y") or op not in UNTIL_OPS:
            raise ValueError(f"until {expr!r}: {k!r} is not x|z|y + _ + le|lt|ge|gt")
        if axis == "y" and y is None:
            raise ValueError(f"until {expr!r}: {k!r} needs his height, and none was given -- a y term is judged on a "
                             f"height-aware path only")
    if x is None or z is None:
        return False
    pos = {"x": x, "z": z, "y": y}
    return all(UNTIL_OPS[k.partition("_")[2]](float(pos[k.partition("_")[0]]), float(v)) for k, v in expr.items())


def has_y(expr) -> bool:
    """S22: whether an until predicate holds a y term."""
    return any(str(k).startswith("y_") for k in expr or ())


def loss_y(g, lost: dict):
    """S22: his published y AT the loss sample's frame -- the ring's sample of exactly that frame (route_to's loss probe
    read it, so the ring kept it: ``ring_since``); None when the ring no longer holds it or it published no y."""
    f = int(lost["frame"])
    for _t, raw in ring_since(g, f - 1):
        fr = int(raw.get("frame", -1))
        if fr == f:
            y = (raw.get("player") or {}).get("y")
            return None if y is None else round(float(y), 1)
        if fr > f:
            break
    return None
```
The reorder changes no O1-O7 call: every frozen `until` holds only valid x/z keys (`step_of` validates them at load),
so a check-first loop raises on none of them and the None rule reads as before. ONE pinned test input flips (1.2's
"What flips"): A2 edits it and re-baselines it. `step_of` validates with `until_ok(out["until"], 0, 0, 0)`. Both trigger
executors, ONLY when `has_y(step["until"])`:
- `x_trigger_to`: route_to's probe sample (no y: session.py:822-827) gets `lost["y"] = loss_y(g, lost)` AS SOON AS
  route_to RETURNS -- before the executor's control wait and before `left_for`, whose `switch()` can wait up to two
  `exit_wait_s` while the ring (300 distinct samples, ~10 s at 60 fps: artifacts.py:35-40) runs on and could evict the
  loss sample (the driver review's #3); a loss sample the executor's own wait reads IN THIS FIELD gets `"y": None if
  st.player_y is None else round(st.player_y, 1)` where it is made (`{**sample(st), "field": st.field_id, "y": ...}`:
  never `round(None)`, the claim review's #10). After the landing (`lost = out["lost"]; here = ...`), a loss read here
  whose `y` is None is `("void", out)` with `v` V13, `by` driver, `why` "the loss at frame N in F has no height (not on
  the ring / not published): the until's y term cannot be judged" (the instrument's), and `landed` set -- `until_ok` is
  never called with it; else `ok` reads `until_ok(step["until"], lost.get("x"), lost.get("z"), lost.get("y"))`.
- `x_trigger` the same (the probe's y read as route_to returns, the own sample's guarded), before its
  `evidence(out["lost"])`.
`lost["y"]` is on the row only for a y-until: every O1-O7 row reads as today.

**S23 -- THE OPT-IN `unstick`** (decision 4(e); the pinch's FALLBACK only, 2.5; PART A, A3). `step_of`: `unstick`, when
present, a bool. `walk_kw`:
```python
        if step.get("unstick") is not None:                # S23 (opt-in): the pinch's fallback (no ladder)
            kw["unstick"] = bool(step["unstick"])
```
It bites only with the step's `npcs` false (session.py:4495 `unstick = unstick or npcs`), and then a deflected hold
raises the plain basis HarnessError, no marker (0.2 #8): the fallback's known cost, which only R-SPIRAL can weigh.

Tests (A1-A3; each named `test_segment_*`, so G7's selection collects them and they join `REQUIRED_TESTS`):
- A1 (S20, S21; 9): `test_segment_step_of_at_y_wait_flag_unstick_and_y_until_are_strict` (pure: `at_y` on a cross,
  `[9150, 8800]`, `[True, 9000]`, `[8800]` refused; `wait_flag` without `at_y`, on a trigger, with `flag` 16384 or True,
  `value` 2, `timeout_s` 0, an extra or a missing key refused; `unstick` "no" refused; `until {y_gt: 12000}` accepted,
  `{w_gt: 1}` refused; every accepted step returned EXACTLY `{**steps_default, **raw}`; break: `step_of` adding
  `unstick` True to every step); `test_segment_walk_at_y_judges_the_arrival_height_on_the_fake` (the box with 164's
  test-side plane, 3.6: a walk to P1 with `at_y` [8800, 9150] done, its row's `at_y.y` ~8958; with [9200, 9500] failed
  naming the y, then V7; break: `at_y` unread -- done at the wrong band);
  `test_segment_walk_waits_for_its_flag_pressing_nothing_on_the_fake` (a test director stores Bit[3811] := 1 sixty fake
  frames after the wait's FIRST `g.wait_for` call -- keyed on the call, never on the wall clock (the claim review's #5)
  --, `timeout_s` 60, far over any starvation: done; the row's `wait_flag` read True, its frame the store's or later,
  `s` over 0 (a lower bound only), `published` at least 1; `g.send` and `g.press` wrapped to count: nothing between the
  arrival and the read but the `watch` and the `unwatch`; the fake's watched set empty after; break: done at the
  arrival, the flag unread); `test_segment_walk_wait_timeout_is_the_games_v8_on_the_fake` (no store, the bit published
  0, `timeout_s` 1: RouteVoid V8 game at the cell, `read` False, `published` at least 1, `last` 0 -- a deterministic V8:
  nothing ever stores; break: V7 or by driver);
  `test_segment_walk_wait_unpublished_watch_is_the_drivers_v13_on_the_fake` (a test-side wrapper on `g.send` drops the
  `watch` verb, so no sample carries the bit; `timeout_s` 1: V13 by the driver naming "never published", `published` 0;
  break: V8 by the game -- the reviews' A4 / B4); `test_segment_walk_wait_runs_out_on_both_clocks` (pure, a stub session
  whose samples publish `rt` advancing a quarter as fast as the wall's, the bit 0: no verdict before the GAME's clock
  ran `timeout_s` (~4 x it of wall time), then V8; a stub with no readable clock: the wall's alone, today's rule; the
  run's deadline first: V13 driver; break: the wall's timeout alone -- V8 while the game's clock had run a quarter of
  it);
  `test_segment_walk_wait_field_change_is_the_games_v11_on_the_fake` (the director warps the fake on the wait's first
  `g.wait_for` call, `timeout_s` 60: V11 game, `landed` the new field; break: `strayed` -- by driver);
  `test_segment_walk_wait_control_loss_is_interrupted_on_the_fake` (control taken on the wait's first `g.wait_for`
  call, away from every exit, `timeout_s` 60: interrupted, then done after the re-grant and the store; control taken
  with him within `exit_slack` of a registered exit whose switch comes: V11 driver, `door` named -- every event keyed
  on a call, never on the wall clock);
  `test_segment_walk_wait_deadline_is_the_drivers_v13_on_the_fake` (the run's deadline 1 s after the arrival,
  `timeout_s` 15: V13 driver on the row, `read` False, `s` under 15; break: the deadline read as the wait's timeout --
  V8).
- A2 (S22; 4, and the O2 test's one case edited -- `until={"w_le": 0}`, match `"x\\|z\\|y"` -- and re-baselined by name in
  A2's commit, 1.2): `test_segment_until_ok_y_axis_raises_without_y` (pure: `({"y_gt": 12000}, 0, 0, 13000)` True,
  `11000` False, `None` raises; `({"x_le": 900}, 800, 0)` True with no y; `({"x_le": 900, "y_gt": 1}, 1000, 0)` RAISES --
  the y check precedes the evaluation, so a failing x term cannot hide it; `({"y_gt": 1}, None, 0)` and `({"w_gt": 1},
  None, 0)` RAISE -- every key is checked before the None rule (the claim review's #10); `({"x_le": 900}, None, 0)`
  False; break: a missing y read as False, or the None rule run first);
  `test_segment_trigger_until_y_reads_the_loss_height_from_the_ring_on_the_fake` (a `trigger` with `until {y_gt:
  12000}` and `to` on the planed box: the door's `y_gt` fires, route_to's probe sample has no y, the row's `lost.y`
  equals the ring sample's at `lost.frame` and is over 12000, done in `to`; again with a test-side wrapper on
  `_Drive.switch` that empties the ring before it returns (a slow load evicting the loss sample): `lost.y` still read --
  `loss_y` runs as route_to returns, before `left_for` (the driver review's #3); break: y read from the state after
  the switch -- the next field's lower y fails the evidence -- or `loss_y` after `left_for` -- V13);
  `test_segment_trigger_until_y_unread_height_is_the_drivers_v13_on_the_fake` (the ring emptied before the read by a
  test-side wrapper on `ring_since`: V13 driver naming the frame; and a loss the executor's own wait reads with the
  player's `y` blanked by a test-side wrapper: V13 driver, no TypeError; break: the missing y read as False --
  interrupted -- or `round(None)`); `test_segment_trigger_until_without_y_keeps_todays_row_on_the_fake` (O6's `x_le`
  until on the fake: the row's `lost` has no `y` key and the verdict is today's; break: y always added).
- A3 (S23; 2): `test_segment_walk_kw_passes_unstick_only_when_carried` (pure, O7's `unit_walk_kw` stub shape: no
  `unstick` -> True (today's literal), `unstick` False -> False; the row carries `unstick` only when the step does;
  break: a default False); `test_segment_unstick_false_places_no_blocker_on_a_stall_on_the_fake` (a box corridor and a
  `fake.freezes` zone on the line holding him 40 frames: with `npcs` False and `unstick` False the walk places no
  blocker -- `_blocker_ahead` counted on the instance: 0, the record's `blockers` empty -- and ends failed or done
  after the freeze lifts; with `unstick` True the same stall reaches the ladder; break: `walk_kw` ignoring the key).

### 1.3 `o8_west_tower.py`

`O8Segment(o7_castle_walk.O7Segment)`:
- `tag = "O8"`, `predictions = HERE / "o8_predictions_v1.json"`, `manifest = HERE / "o8_forks.json"`, `session_file =
  "o8_session.json"`, `report_file = "o8_report.txt"`, `chain_dir` / `build_dir` O4's, `accept_us_build = False`,
  `recovery = 4600`, `end_session_warps = True`.
- Constants: `ROUTE = VISITS = (164, 165, 166)`; `END_FIELD = 55`; `ROUTE_DONORS = ROUTE` (55 is the end, real on both
  sides, no member's donor: O7's `route_members` raises for it, so it runs over the route only -- the research's
  harness gap 8); `AFTER_RUN = "O1-O7"`;
  `PRIOR_SEGMENTS8 = C7.PRIOR_SEGMENTS + ("o7_predictions_v1.json",)`; `O7_FROZEN = "o7_predictions_v1.json"`;
  `START_VALUES8` (O7's with `Int16[2]` 342: SC 1190, Int16[2] 342, Byte[13] 1, Int16[9] 643, Int16[11] -1, Byte[14] 0,
  Byte[8] 125); `ENGINE_RADII = {164: 80, 165: 120}` (164: DoEventCode.cs:1507-1508 through EffectiveFieldId, so 31256
  too; 165: `SetObjectLogicalSize(30, 35, 50)`'s 30 x 4); `SETTINGS8` (O7's 31 keys and `"Graphics": {"VSync": "1"}`
  added: 32); `REHEARSAL_OVERLAYS8 = frozenset({"hold_stop", "page_stop", "flag_stop", "pinch_stop", "movie_stop",
  "movie_poke"})`;
  `KNOWN_STEP_KEYS8` (0.2 #17's vocabulary plus `at_y`, `wait_flag`, `unstick`); `PINCH_WINDOW = {"place": 164, "x":
  [900, 1310], "z": [4460, 4600], "y": [10400, 11100]}` (published y: loop 1 crosses the same XZ at ~5600-5900);
  `RACED8 = ("Global.Int16[2]", "Global.Byte[8]")` (typed for the draft; O8-KEYS (g) derives it); `UNTOUCHED8 =
  ("Global.Bit[3851]", "Global.Bit[3792]", "Global.Bit[7211]", "Global.Int16[224]")`; `START_READ = C7.START_READ`;
  `MOVIE_SPAN = "the movie span"` (every A-MOVIE reason opens with it: 5.1); `KNIGHT_UNREAD = "the knight's seat
  unread"` (every A-KNIGHT reason: 5.1); `MOVIE`, `SEAM`, `SEAT` (4.10).
- `core_ids = ("START", "NO-SC", "CHAIN", "RESIDUE", "WRITES", "NULL", "STABLE", "LANDING", "SEAM", "WALK", "ORDER",
  "KNIGHT", "MOVIE", "PATTERN", "MASKED", "STATE", "JOIN")`: with FROZEN, COVER, FORBIDDEN and VOID-ASYM, 21 session
  checks; THROW in `run`. `titles` every check's O8 text (section 5).

**Inherited unchanged** (O7's or earlier): `read_session`, `forbidden_check`, `void_asym_check` (over O8's `_void_ids`,
below), `start_check` (O3's: the four residue rows), `no_sc_check`, `span_check` (CHAIN), `residue_check`,
`writes_check` (EXACT), `null_check`,
`stable_check`, `join_check`, `masked_check`, `pattern_check` (O7's: `pattern_diff6`, `floating` []), `state_check`
(O7's (a)-(c): (c) already iterates every `end_state_trace` target, by place at the side's own field), `history` /
`suppressed`, `fingerprint_extra`, `build_pins` (O5's), `text_check` (block 3), `reseed` and `start_run` (O7's:
`seeded_fields` reads the table -- 164, 165, 31256, 31257 -- and forgets them before every run's New Game).

**Overridden:**
- `draft()` (section 4); `freeze_problems()` (7.3); `offline_extra` ([`text_check8`, `census_check`, `regions_check`,
  `goals_check`]); `build_check` (O7's form over `route_build`, then the raw exits, 6.1); `keys_check` (6.1 (a)-(h));
  `route_pins_check`; `census_check` (`store_census8`); `regions_check` (`regions_problems8`); `goals_check` (`goals8`,
  height-aware: never O7's `goals_base7`, whose `until_ok(until, gx, gz)` RAISES on a y term under S22, 0.2 #7);
  `preflight_extra` (O5's, with P-DONOR over the route donors and its `31205 55` line, P-DONOR-LOG over [164, 165, 166,
  55], `SETTINGS8`: 6.2); `capabilities` (O7's shape; P-OBJECTS names the knight).
- `why_void`: `C6.O6Segment.why_void` (O5's A-START on 164's error path, O3's A-NOEND and `cut_row`), then THE START
  READS with their EXPLICIT races (4.5): never O7's, whose `race_site` keys on the read's own old and so resolves 164
  ip130's race to 70 ip130, the wrong store (critique #2); then A-MOVIE and A-KNIGHT (5.1; the reviews' A1, B3).
- `_void_ids` (static): O7's, setting aside every reason that opens with `START_READ` OR `MOVIE_SPAN` -- each is the
  instrument's on either side (the warp's timing; a press, a dialog only a press opens, or an unclocked span: 0.2
  #23), so a side VOID in one in every run is VOID by COVER, never NOT PROVEN by VOID-ASYM (b). A `KNIGHT_UNREAD`
  reason is NOT set aside: a whole side with no published seat is an asymmetry no one has explained.
- `drive`: O4's drive, the run-wide witness, `observe=o8_observe(g, pred, log)`, and a `{"k": "rate", **g.rate()
  .as_dict()}` row in a `finally` (the report's render rate).
- `core_checks` (the 17); `landing_check` (O7's (a)-(d), its (e) left to SEAM: 5.3); `seam_check`, `walk_check`,
  `order_check`, `knight_check`, `movie_check` (new, 5.3); `report_extra` (5.4); `add_arguments` / `handle`
  (`--draft`, `--rehearsal-report`).

**Module functions** (pure unless named a reader):
- `route_members8(members)` (O7's `route_members` over `ROUTE`); `instanced_at8 = C7.instanced_at7` (0.2 #3: no
  dispatch in 164-166).
- `talk_reach(idx, player_sid)`: the functions only a TALK reaches -- every instanced entry's tag 3, and each
  `(player_sid, t)` a tag-3 function calls by `RunScriptSync`/`RunScriptAsync(_, 250, t)` that no other function
  calls (164: e1 t3, e7 t11, e7 t12; 165, 166: none); `route_run_texts(idx, entrance)` = `instanced_texts` less
  `talk_reach` (the carried scan's narrowing, decision 3: 0.2 #11).
- `band_closures(mesh, lo, hi)`: every open tri whose centroid PSX y lies outside [lo, hi] (93, 99, 64, 16 on the four
  steps' bands; 0 XZ self-overlaps inside each band: the step's floor is one level).
- `height_gate(test, jump)`: the condition under which control reaches a height test's GUARDED code, read off the
  test's pinned text AND its consuming jump's (the claim review's #7; 0.2 #24) -- the test `obj(uid=250).f[1]
  const(c) B_LT` is published y > -s16(c), `B_GT` is y < -s16(c) (2-byte constants signed); a `JMP_IFNOT` past the
  guarded code (a door's, to its RET) passes the test as is, a `JMP_IF` back over it (the knight's wait loop, to its
  `op_22(1)`) passes its NEGATION, the strictness flipped (y < 8400 -> `{"y_ge": 8400}`); any other shape None (O7's
  `height_test` reads B_LT only, and no jump); `gate_holds(gate, y)`.
- `end_race8(idx55, values)`: 0.2 #5's walk of 55 e0 t0 from the arrival's values, through its first long yield ON TO
  ITS RET (0.2 #26: the post-yield code adds nothing on this arrival, and a store there would land before a live read
  that waits for a publish) -> the targets stored to another value ({Int16[2], Byte[8]}); a forward branch it cannot
  resolve raises.
- `reach8(idx, sid, tag, ip, known)`: whether a store site is REACHABLE -- a path search over its function from the
  function's start, each `SET` of a constant updating the known values, a test whose operands are all known evaluated
  (a `SWITCH` / `SWITCHEX` on a known value taking its one label), any other test taken BOTH ways (a free arrival
  value, a `B_SYSVAR`), a revisited (ip, known values) pair cut; True when some path reaches `ip`. CENSUS reads it
  with `known` {} (every arrival value free: an `error_path` guard must hold from SOME arrival -- the claim review's
  #9) and KEYS (g) with 55's `{"Map.Byte[24]": 1}` (0.2 #26).
- `race_site8(pred, sr)`: the explicit raced store `sr["race"]` -- `(70, 0, 0, ip)` -- when the field-70 route pin
  there is `SET({<target> const(<race_value>) B_LET B_EXPR_END})`, else None.
- `scoped_derivation8(pred, pred7, segs)`: O7's rule (`last_values` off O7's FROZEN pattern, then the composition over
  `segs`, else the raw start) from `START_VALUES8`; `carried8(pred, segs)` = `carried_from_segments(segs,
  writes=o8_targets(pred))`.
- `exempt_span(log, place_)`: THE KNIGHT'S SPAN, `[frame0 of step 0's FIRST row, frame0 of step 1's FIRST row)` of the
  164 visit (critique #1; decision 6); `visit_windows8(log, pred)` (O7's windows, the doors read from each trigger's
  `to` -- the exit whose `to` is the step's -- never `target` only; that door's own tag-2 store SITES exempt anywhere
  after the trigger step's FIRST `frame0`, matched by site, never bounded by a read loss frame (the driver review's
  #5: the store trails ExitField by 25 ticks or more, 0.2 #25, and a late-read loss can land after it); and the
  knight's site exempt inside the span).
- `knight_watch(g, pred, log)`, `movie_clock(pred, log)` and `o8_observe(g, pred, log, *, extra=None)` (below);
  `movie_span(r, pred, members)`; `seam_problems(r, seam, members)` (pure, parameterised: the O3 fixture runs it, 8).
- `trace_summary8`, `rehearsal_report8(run_dir, *, walkmesh=None)`, `run(g)`, `main(argv)`.

**The observe hook** (0.2 #21). `o8_observe` runs, in order, `knight_watch`'s, `movie_clock`'s and `extra` (the
rehearsal recorder). An exception in the hook would end the run "STOPPED (unexpected)" (segment_trace.py:719-721), so
`knight_watch` and `movie_clock` NEVER RAISE (the driver review's #12): each is wrapped, an exception becomes one
`{"k": "observe_error", "hook", "frame", "error"}` row and the hook goes on; only `extra`'s rehearsal stops
(`movie_stop`) may raise:
- `knight_watch(g, pred, log)` CACHES on PLACE (`ctx["donor"]`; member(164) 31256 reads as 164) and the visit (each
  arrival in a field of the place): every poll in the place caches the watched sid's published `(x, z)` by frame (the
  last 64) with the poll's field and place, and a visit's cache is KEPT after he leaves the place until both of its
  rows are written. It WRITES on any poll, whatever its place (the driver review's #2, the claim review's #8: under
  `x_trigger_to`'s path B the step-1 row is appended after the map switch, so the next poll is in 165, or a load with
  `fid <= 0`): a `{"k": "knight", "what": "seat", ...}` row, once a visit, on the first poll whose log holds the
  visit's step-0 row with `wait_flag.read` True -- the watched object's reading in the RING sample of
  `wait_flag.frame` (`ring_since`), else the first cached reading at or after it (`"from": "poll"`); a `"start1"` row,
  once a visit, on the first poll whose log holds the visit's first step-1 row -- the cached reading of exactly that
  row's `frame0` (the hook read that very sample before `run_step` took it). Each row's `field` and `donor` are the
  READING's (its sample's field and place), never the writing poll's `ctx`. Rows `{"k": "knight", "what", "donor",
  "sid", "field", "visit", "frame", "x", "z", "from"}`; no reading, no row -- the run uncovered, A-KNIGHT (5.1).
- `movie_clock(pred, log)`: on every poll in the movie's place whose frame is at least `movie.clock_every` (30) past
  the last clock row, `{"k": "clock", "frame", "mtime": st.mtime, "field", "ui", "control", "windows"}` (state.json's
  write time: the clock the session's rate is measured from; it can be None, channel.py:1068-1071, and MOVIE skips
  such a row); and a `{"k": "skip_seen", "frame", "field", "options", "prompt_empty"}` row on the first poll of each
  opening of a published choice that IS the skip dialog by text or by shape -- `skip_answer(choice, st.texts) is not
  None or skip_shaped(choice)` (segment_drive.py:714-753: a prompt published empty or localized keeps its shape; the
  claim review's #6, the driver review's #1), never `options[0]` alone.

### 1.4 The regression gate extended to O7 (`segment_regress.py`)

The implementer extends the gate and captures its O7 baseline FIRST (A0), before any shared-code change. The O7 items
import only O7's modules (`o7_castle_walk`, `o7_dryrun`) inside their functions.

`O7S = C:\gd\Dream-World-IX\.harness-runs\20261005-060311-story-o7`, `V1_O7 = HERE / "o7_predictions_v1.json"`
(sha256 `2d646aaf48fa943e...`), `BASELINE_O7 = HERE / "research" / "o7_regress_baseline.json"`, `O7S_VERDICT =
"PROVEN"`, `O7S_CHECKS = 17`, `O7_OFFLINE_CHECKS = 6`.

| Item | Check |
|---|---|
| G0'''''' | `py studies/story-trace/segment_regress.py --capture-o7` writes `research/o7_regress_baseline.json` (LF, `-text`): the full `(checks, report)` of O7S with V1_O7; every `o7_dryrun` session case's `(checks, report)` and "predictions-changed"'s; every unit's `(name, ok, detail)` (`units(...)` then `listed_units(...)`, in `run_cases`'s order); `O7.offline_check(V1_O7)`; the tests G38 collects; the HEAD and V1_O7's sha; and `sources`: the AST sha of every test G38 collects and of every function `fake_pins_o7()` names -- only names none of the O3-O6 baselines pins (`o7_pin_names` refuses one pinned in any). It refuses an existing file, refuses unless G38, G39 and G40-G43's baseline-free halves pass, and takes TWO readings first, refusing when they differ after every temporary root reads `<tmp>`. |
| G40 | `O7.analyse(O7S, pred_path=V1_O7)`: the report equals `(O7S/"o7_report.txt").read_text(encoding="utf-8")` exactly and the baseline's; the checks the baseline's; PROVEN with 17 checks, all True. |
| G41 | `py studies/story-trace/o7_castle_walk.py --analyse O7S --predictions V1_O7` exits 0 and prints that report (`PYTHONIOENCODING=utf-8`). |
| G42 | Every `o7_dryrun` session case's `(checks, report)` and unit's `(name, ok, detail)` byte-equal to the baseline's (each temporary root `<tmp>`), and `o7_dryrun.run_cases(V1_O7)` returns 0 printing "174/174 cases as registered" (N from the replica). G42 IS O7'S VOID-PATH BASELINE. |
| G43 | `O7.offline_check(V1_O7)` equals the baseline's `[(ok, what, detail)]`: 6 checks, all PASS. |
| G21 (extended) | THE SOURCE PINS over the UNION of the O3-O7 baselines' `sources` (`PIN_BASELINES = ("O3", "O4", "O5", "O6", "O7")`; `union_sources(*sources)` refuses a name in two, pair by pair; a call with four baselines reads exactly as today, so O6's pinned `test_segment_regress_o6_pins_join_the_union` passes unedited); `--rebaseline-source NAME` looks NAME up in any of the five (`--baseline-o7` on the CLI). |
| G44 (from B4) | `pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o8_ or fake_spiral or fake_knight or fake_tower"` (`PYTEST_K_O8`): all passed, 0 failed, 0 skipped, 0 errors; every name in `REQUIRED_TESTS_O8` among them. No baseline: the list is the floor. A member of THE union run (`PYTEST_ITEMS`). |
| G45 (from C2) | `o8_dryrun.run_cases` on the frozen O8 predictions once they exist, else the draft, AND on `o8_dryrun.as_if_frozen(draft)`: each returns 0 printing "N/N cases as registered", the same N, at least `O8_DRYRUN_FLOOR` (the count C2 prints). |

`FAKE_PINS_O7` and `FAKE_PIN_CLASSES_O7` (0.2 #1): `("FakeGame.place_height", "FakeGame._move_to",
"FakeGame._step_walkers", "FakeGame._objects_doc", "_VisitBeat._scene_fires", "_VisitBeat._wait_window")` and
`("Levels",)` (`fake_pins_o7(source)` expands the class in the order fakegame.py defines it and raises, naming them,
when fakegame.py defines no function for a name). `FakeGame.__init__` stays unpinned (every knob edits it; no baseline
ever pinned it); `_pushed_out` and `_region_at` stay unpinned (no segment added them). O8's two fake edits are each
re-baselined by name in the commit that makes them (B1 `_move_to`, B2 `_step_walkers`), proven neutral by the three
replays (3.5). So is the one pinned TEST O8 edits: A2's case of `test_o2_step_of_refuses_a_step_its_executor_cannot_run`
(the O3 baseline's: 1.2's "What flips"). Three re-baseline rows in all, each named in its commit.

**The registry** grows in three commits: A0 inserts G40-G43 before G21 and files them under "O7" (`SEGMENT_ITEMS["O7"]
= ("G38", "G39", "G40", "G41", "G42", "G43")`); B4 adds G44 (`PYTEST_ITEMS["G44"]`, `SEGMENT_ITEMS["O8"] =
("G44",)`); C2 adds G45 (`"O8": ("G44", "G45")`). Each of A0, B4 and C2 updates the body of
`test_segment_regress_registry_holds_every_item_once` (no baseline pins it): `ITEM_ORDER` holds G1 to G43 / G44 / G45
each once, G21 last; no item under two segments; the pytest items G7, G12, G13, G19, G26, G32, G38 (and G44 from B4)
with their selections; `select_items((), ["O7"]) == {G38 .. G43}`; `["G46"]`, `["O9"]` and `["g7"]` refused. Break:
drop an item from `ITEM_ORDER`. `test_segment_regress_partial_run_is_not_the_gate` already reads its count off
`ITEM_ORDER` (O7's 11.4 PART A #1): unedited.

`_missing()` gains O7S's session and report, V1_O7 and the O7 baseline (`o7s`), and from C2 O4's `campaign.toml`
(`o8`: the draft's chain). Tests O8 adds named `test_segment_*` join `REQUIRED_TESTS` (G7's selection, by design);
every `test_o8_*`, `test_fake_spiral_*`, `test_fake_knight_*` and `test_fake_tower_*` joins `REQUIRED_TESTS_O8`. Apart
from those `test_segment_*` tests -- and A0's, which holds "o7_" on purpose -- no O8 test name holds a term of an
earlier selection: "segment", "o1_", "overlay_hint", "o2_", "rehearse", "o3_drive", "o3_skip_ab", "o4_",
"fake_chanbara", "fake_keyon", "o5_", "fake_visit", "fake_story_suppress", "o6_", "fake_naming", "fake_door", "o7_",
"fake_level", "fake_monologue", "fake_patrol" (O8's rehearsal tests are `test_o8_rehearsal_*`: "rehearsal" does not
contain "rehearse"). Test (A0, into `REQUIRED_TESTS`; it holds "o7_", so G38 collects it and the O7 baseline pins it,
O5's and O6's precedent): `test_segment_regress_o7_pins_join_the_union` (pure: G21's checker over five baselines on
temporary copies -- an edited pinned O7 test FAILS naming it; a re-baseline row for an O7-baseline name passes; a name
pinned in two baselines is refused at capture and by the union).

---

## 2. The drive

### 2.1 The model (keys the driver reads; the rest of the predictions is the analysis's)
- **`table`**: two visit-scoped cells (S13), (164, 1190, 1) and (165, 1190, 2), two steps each (2.4); control anywhere
  else -- 164 or 165 before its grant or after its cell's last step, 166 at any time (no grant there), 55 before rule
  1 -- is V4 (game) at `[place, 1190, visit]`.
- **`naming`: []**, **`battles`: []** (any battle V10), **no `movies` key** (rule 9 only sleeps through FMV004: PLAN.md
  "Movie skip (opt-in)"), no `guard`, no `chanbara`.
- **`stop_pages`**: `[{"match": "Env Play()", "why": "window 56 of 164 (e0 t0 ip597/ip631), 165 (ip677/ip711), 166
  (ip322/ip356): Byte[13]/[14] arrived 9"}]`.
- **`choices`**: the skip net only -- O7's row (`{"donor": null, "sc": null, "match": "want to skip", "pick":
  "default", "once": false, "beat": null}`) and, second, a row for the dialog's MEASURED option line (`{"donor": 166,
  "sc": null, "match": "No", "pick": "default", "once": false, "beat": null}`: O3's F4 rule -- "if the prompt published
  empty, a second rule matching the measured option line is added" -- and O4's lesson-1 precedent; story-o3's R-FULL-SKIP
  measured the lines "Yes" / "No": 0.2 #23). `pick_for` matches `match` against the prompt and the shown lines only
  (segment_drive.py:268-276), so a skip dialog whose prompt publishes EMPTY fits no O7 row and would be V1 by the GAME
  for what is a press's dialog (the claim review's #6); the 166-scoped row answers it at its default too -- no shared
  code changes. A stray SkipMovieDialog during FMV004 is answered at its default, No, and the movie resumes
  (FieldHUD.cs:275-287, :428-445; MBG.cs:534-541 pauses it while the dialog is up; O3's
  `test_o3_drive_answers_a_skip_dialog_at_its_default`; in game, R-FMV's `movie_poke` run: 7.1) -- and the run is
  uncovered all the same (A-MOVIE, 5.1): the net keeps the run ALIVE (no V1, no V14 for the game), never covered.
  Never a `guard` (S10's strict pre-choice policy refuses a default pick: critique #7). Any other choice is V1 (game).
- **`witness`** (S12): O7's `{"input_every_s": 0.05, "why": ...}`.
- **`route` / `visits`: [164, 165, 166]**, **`end_fields`: [55]**, **`side_ends`: {S: [55], F: [55]}**, **`members`**:
  O4's twenty, never O1's 31205 (`side_ends_of` accepts F [55]: an end field no member forks).
- **`regions`** (4.15): the landing judge reads role `exit` (4 regions); a region's `gate` is the analysis's.
- **`budget`** with `end_row_s` (rule 1 waits for 55's first row) and `settle_s`.

### 2.2 The driver loop for O8 (O7's rules in O7's order; nothing new in the loop)
Rule 1 (the end: real 55 on BOTH sides -- the first poll publishing field 55, before rule 2; the live end state, the
last scan, the end row); the stall watchdog (V14: `no_progress_s` sized by F8 for FMV004's static span, 2.7); rule 2
(on F a REAL 164, 165 or 166 is V19, game: a route `Field()` the chain did not retarget; a wrong door's landing never
reaches it -- the trigger's landing judge returns V11 (driver) for any landing whose place is not `to`); rule 3 (the
visit order 164 -> 165 -> 166; a back door into an earlier place is out of order: V11); rule 5 (a tutorial or a battle:
V10); rule 6 (only the skip net); rule 7 (a page: the stop page V5 -- the driver's in visit 1 (164: the warp's start
state), the game's after -- else Confirm: 166's six pages); rule 8 (control held, settled: the cell's next step -- the
`walk` with S20/S21, the `trigger` with S14's `to` and S22's y-until); rule 9 (fades, loads, FMV004: sleep).

### 2.3 Every research beat, and what handles it

| # | Field | Beat | Handled by |
|---|---|---|---|
| 1 | 70 -> 164 | New Game, the trace armed, the raw warp from FieldHUD after 70 e0 t0 ip130 and ip249, before ip475; residue: SC bytes 0-1 (0 -> 166, 0 -> 4), FieldEntrance bytes 2 (0 -> 86) and 3 (0 -> 1) | `start_run` (O7's: `reseed`, then the Segment's); O8-START (a) expects FOUR rows; the two start reads classify both edges of the window (4.5) |
| 2 | 164 | Main_Init at 342 in one frame: THE START ROW ip22, ip57 643 -> 385, ip130 Byte[13] 1 -> 1 (START (c); the late-edge start read), ip138, ip200; op_22(2) x2; ip698 EnableMove (THE GRANT) at (2040, 3335), published y ~4780, and ip764 1 -> 2 in the grant's pass | rule 8 after the settle |
| 3 | 164 | step 0, `walk` up loop 1 to P1 (1342, 2252), y ~8958: through e2's ring twice at its DEAD level (PSX -8005, -8429: tag 2 RETs at ip51), never in e3; T0 (published y >= 8400) at ~(610, 2160) releases the knight | S17 + S18 (80) + S19 + S20 `at_y` |
| 4 | 164 | THE KNIGHT WAIT at P1: the knight walks 1131.4 u at 15 u a tick, RunAnimation(9920) 59 frames, then e1 t1 ip230 `Bit[3811] := 1` at ~T0 + 140 +- 8 ticks; nothing pressed | S21 `wait_flag`; O8-ORDER; O8-KNIGHT's seat rows (the observe hook) |
| 5 | 164 | step 1, `trigger` up loop 2 -- THE PINCH (half-width 68.6 at (1202, 4520), y ~10695) -- through e3's ring at its dead level (PSX -9329/-9528) to e2 at the top: fires at ~(24.5, 2270.8), y ~13008; ip243 `Int16[2] := 343`, ip251 `Field(165)` (31257 on F) | S14 `to` + S18 (64) + S22 `until {y_gt: 12000}` (2.5) |
| 6 | 165 | Main_Init at 343: ip130 2 -> 1; ip778 THE GRANT at (2055, 3411), y ~10280, ip844 1 -> 2 | rule 8 |
| 7 | 165 | step 0, `walk` to (1508, 4698) at `at_y` [11100, 11450], away from e3 (LIVE, 134 u) | S17 + S19 + S20 |
| 8 | 165 | step 1, `trigger` into e2 at the top: fires at ~(2419.6, 3130), y ~15169; ip205 `Byte[13] := 3` (LIVE), ip233 `Int16[2] := 344`, ip241 `Field(166)` (31258 on F) | S14 + S22 `until {y_gt: 15000}` |
| 9 | 166 | Main_Init at 344: ip57 385 -> -1, ip119 3 -> 0, the SYSVAR[3] sync, ip255 `Byte[8]` 125 -> 125 (THE START READ, early edge); no grant (the only EnableMove, ip423, sits behind `Map.Bit[158] == 1`, never set) | nothing: no cell (control here is V4) |
| 10 | 166 | e6 t1: pages 307 (WindowSync), 308 (Sync), 309 (WindowAsync); ip345 `Byte[208] := 0` and ip380 `++` under 309; ip401 WaitWindow(0) | rule 7 (report-only) |
| 11 | 166 | pages 311, 312, 313 (Sync); RunSharedScript(2) (storeless) | rule 7 |
| 12 | 166 | ip502 `Byte[8] := 0`: the last store before FMV004 (MOVIE's span opens here) | nothing |
| 13 | 166 | FMV004: ip633 `Cinematic(0, 9, 1, 1)` (MBG_DEF("FMV004", 1, 0), type 0), ip711 `Cinematic(2, 0, 0, 0)` plays, PLAYED OUT (45.412 s file); a stray Confirm's SkipMovieDialog answered No (that run uncovered) | rule 9 sleeps; rule 6's skip net (2.1's two rows); A-MOVIE (5.1); O8-MOVIE (a)-(c), (b) the span |
| 14 | 166 | ip863 `Int16[2] := 110`, ip871 `Field(55)` -- raw on F: THE SEAM 31258 -> 55 | LANDING (c); O8-SEAM |
| 15 | 55 | THE END: e0 t0 ip22 (the cut), real 55 on both sides; ip255 (110 -> 106) and ip342 (0 -> 125) race the live read | rule 1 per side; `end_state_trace` (4.9) |

### 2.4 The cells (each `{"donor", "sc": 1190, "visit", "steps"}`; `steps_default` O7's)

| Cell | Grant (bytes; REHEARSE) | Steps | Keys beside goal / to / until | Why |
|---|---|---|---|---|
| (164, 1190, 1) | ip698 at (2040, 3335), facing -36, tri 145 PSX -4780 (published ~4780); the engine's nearest wall 95.8 u (no push-out: dispute 1) | #0 `walk` "164: the first spiral to P1, then THE KNIGHT WAIT", goal P1 (1342, 2252), `start` (2040, 3335) | `at_y` [8800, 9150]; `wait_flag` {flag 3811, value 1, timeout_s 15}; `avoid` ["164.e3"]; `closed_tris` the 93 (`band_closures`, outside PSX [-9500, -4700]); `clearance` 80; `basis` "prior"; `npcs` **false**; `attempts` 3; beat `w164_p1` | P1 is tri 53 at PSX -8958 (11 and 98 stack there: `at_y` names the level); e3 is LIVE 157 u from the spawn (a probe could fire it: the prior basis; the 5-point region, never the 4-point zone, is avoided); `npcs` false is REQUIRED -- the planner keeps the knight as a disc from any level and his start lies 152.5 u from the line, inside P 252 (no route), while the engine pairs actors only at \|dy\| < 400 (WalkMesh.cs:919-921); 6404 u, but no `timeout_s`: route_to's bounds no walk (0.2 #12) |
| | | #1 `trigger` "164: the second spiral into e2 at the top", goal (59, 2214), `to` 165, `start` (1342, 2252) | `until` {y_gt: 12000}; `avoid` []; `closed_tris` the 99 (outside [-13100, -8700]); `clearance` **64**; `npcs` true; `attempts` 3; beat `t164_e2` (no `basis`: 164's is in hand) | from P1 a route at 60/64/65, NONE at 66/68/72/80 (THE PINCH, 2.5); not a `cross` -- band B still opens tri 90 (PSX -8736) inside e2's ring at its dead level, so a zone finish is not level-proof; the until is e2 t2 ip42's own test; the seated knight lies 300.0 u off the line (outside P 252); e3 is crossed at its dead level only |
| (165, 1190, 2) | ip778 at (2055, 3411), facing 128, tri 57 PSX -10280; engine wall 154.5 | #0 `walk` "165: the lower stretch to P1", goal (1508, 4698), `start` (2055, 3411) | `at_y` [11100, 11450]; `avoid` ["165.e3"]; `closed_tris` the 64 (outside [-11800, -9500]); `clearance` 120; `basis` "prior"; `npcs` true; beat `w165_p1` | e3 is LIVE 133.6 u from the spawn (band A opens the stairs below it inside e3's ring); the first move 'up+left' heads north, away from it |
| | | #1 `trigger` "165: the upper stretch into e2 at the top", goal (2489, 3166), `to` 166, `start` (1508, 4698) | `until` {y_gt: 15000}; `avoid` []; `closed_tris` the 16 (outside [-16000, -11000]); `clearance` 120; `npcs` true; beat `t165_e2` | the goal 61.7 u inside e2's west edge (the 45-u arrival circle wholly inside: dispute 6); e2 fires ~90 u before the goal's own wall (107 < 120, never reached); e3 crossed at its dead level |

THE BASES, PER RUN: 164 and 165 (and 31256, 31257) are seeded every run (`seeded_fields` from the table, O7's
`reseed`), so every run judges both first moves -- the FIRST on a ramp: the slope scales a hold's reach
(PSXMovementMethod 1, FieldMapActorController.cs:743-744), never its direction (164's 'left' for 2 frames at 31 fps, 3
at 60: 0.0 deg off offline). `attempts` 3 on 164's two steps (the pinch; a stall that outlasts the waits and the push
ends the attempt, and the next is the fresh re-plan from where he stands: O7's 154/163 rule), O7's 2 elsewhere.

### 2.5 THE PINCH: one trigger at clearance 64 (decision 5; critique #10 weighed, not taken)
164 #1 stays ONE `trigger` planned at 64 from P1 to e2's west ear. The corridor's least half-width on the plan is
68.6 at (1202, 4520), PSX -10695 (L 2654-3066, loop 2's north turn, x 906-1301, z 4474-4586): 11.4 u a side under the
radius 80, against O7's 163 foot at 3.3. Elsewhere it is 77.7 at the pinch's ends and 105-200 almost everywhere
(dispute 2). The critic's split -- walk(80, `at_y`) to the pinch's south end, walk(64, `at_y`) through it, trigger(80)
-- is NOT taken:
1. **The go/no-go evidence is already one short stretch.** F5 judges only holds that start or end in THE PINCH WINDOW
   (x 900-1310, z 4460-4600, published y 10400-11100: ~410 u of the 6327); every rung elsewhere is recorded, never
   judged (O7's F5 rule). The split would buy the same isolation with new steps.
2. **The split needs new authored surface on the one unproven stretch.** Its walk(80) legs cannot end AT the pinch
   (its ends are 77.7, under 80: no goal there stands >= 80 from a wall), so it needs two new goals off the pinch, each
   with an `at_y` band on loop 2 over loop 1 (the same XZ at PSX ~-5600..-5900) -- THE DEFECT FOLLOWS THE AUTHORSHIP
   (CLAUDE.md section 7).
3. **The push-out the critic counts is a regime O7 already ran.** The plan at 64 runs ~64 u off walls on ~90% of the
   leg, so the engine pushes him ~16 u out; O7's 154 descent ran 122-140 u off a railing at radius 120 (O7's 0.2 #17),
   every run done within its attempts.
4. **The fallback applies to one step**, not three.

**The NO-GO ladder** (F5): GO as planned; NO-GO -> 164 #1 gains `unstick: false` and `npcs: false` (S23; the seated
knight is 300 u off the line, so dropping npcs costs no plan) and R-SPIRAL runs again; still NO-GO -> the owner, with
the measured pinch (the narrowest gap, the rungs and the holds they followed), the split above and "another walk
fallback" as the options. The end is never changed without the owner. **Every pinch stall is CLASSIFIED in F5's record**
(the driver review's #8), because the middle rung can help only one kind:
- **rejected** -- holds whose ticks moved him nothing while the game ran: the engine refused the move (IsRadiusValid
  fails, ServiceForces averages the walls' forces -- point forces first -- and BGI_traverseTriangles rejects a pushed
  position that would cross a wall: FieldMapActorController.cs:975-993, 1188-1254);
- **blocker-sealed** -- the ladder placed a blocker (`_blocker_ahead`) whose disc closed the corridor and the replan
  found no route;
- **slid** -- a hold deflected under 0.35 of its travel, read as a slide under `slides`.
`unstick: false` changes the harness's ladder and nothing else: not the line he is pressed along and not the engine's
averaging, and with `slides` off a deflected hold raises the plain basis HarnessError and forgets 164's basis
(session.py:3554-3564: a cell-less V13). So the middle rung is PREDICTED to help only blocker-sealed stalls. It still
runs on any NO-GO, as decision 5 orders; when the classification held only rejected or slid stalls, its R-SPIRAL is a
confirmation whose expected failure (that basis error, or the same stall) is recorded as predicted, never read as a new
finding, and the owner's packet leads with the classification and the split.

### 2.6 THE KNIGHT WAIT (cell (164, 1190, 1), step 0; decision 6)
- **The trigger** (164 e1 t1): ip160 `Bit[3811] == 0`; ip178 `obj(uid=250).f[1] > -8400` and ip187 `JMP_IF(L15)` loop
  back through ip175's op_22(1) while he stands below published y 8400 (uid 250 = controlUID, EventEngine.cs:950-951):
  ip178's test is the HOLD, and `height_gate(ip178, ip187)` reads the RELEASE, `{"y_ge": 8400}` (0.2 #24); T0 = the
  first event tick at published y >= 8400. On the planned line T0 is at L 5655 (610, 2160), ~750 u and ~16 ticks before
  P1. `at_y` [8800, 9150]'s low end is over 8400, so a proven `at_y` proves T0 passed (O8-GOALS (g6')).
- **The walk and the store**: SetWalkSpeed(15), four synchronous Walks to (-586, 3884) -- 340.6 + 261.0 + 228.4 + 301.4 =
  1131.4 u, MoveToward's 15 u a call, not slope-scaled (EventEngine.MoveToward.cs:141-142) -- RunAnimation(9920) (59
  frames at 30) + WaitAnimation, then ip230 `Bit[3811] := 1` at ~T0 + 140 +- 8 ticks (~4.7 s): the wait at P1 is
  expected 2.8-4.2 s; `timeout_s` 15 (F2 sets max(15, 3 x the longest)).
- **No contact, no region**: P1 stands 335 u from e2 and 293.5 u from e3 (O8-GOALS (g5')), ~2300 u below and ~2500 u
  (XZ) from his line; the engine never pairs them (|dy| ~5000 during step 0).
- **THE EXEMPT SPAN** (critique #1): `[frame0 of step 0's FIRST attempt row, frame0 of step 1's FIRST attempt row)` --
  every attempt of step 0, the gaps between them, the wait, the settle before step 1. ip230 must lie inside it and
  precede e2 t2 ip243 by line (O8-ORDER); the same span is O8-WALK (b)'s exemption for ip230, and nowhere else. One row
  per attempt (0.2 #9): a first attempt that passes T0 and then stalls leaves ip230 in its own row or in the gap before
  the retry, where a done-row window would have failed a correct run.
- **The seat** (critique #9): the hook's `seat` row (the ring sample of the wait's read frame) and `start1` row (step
  1's frame0) each read sid 1 within 30 u of (-586, 3884) (tri 120, PSX -11896; published r 220 = 4 x (20 + 35),
  HarnessAgent.cs:2349; talk_r 395 once ip190's SetWalkSpeed(15) ran, 410 before it -- it adds the speed, :2360, 0.2
  #27 -- and read by nothing: he is talk-only): the premise step 1's npcs plan rests on, on both sides (O8-KNIGHT). An
  unread seat or start1 is the instrument's, the run uncovered (A-KNIGHT, 5.1); a reading off the seat FAILS.
- **Without the wait** ip230 would race e2's exit (pure running from T0 to e2's fire is ~16 + ~125 ticks, a dead heat)
  and go MISSING when Field(165) unloads 164: the wait makes the order constructive.

### 2.7 166 and the movie (visit 3; no cell; decision 7)
- **The pages**: rule 7 Confirms each published page with control off, then waits CUTSCENE_PAGE_TICKS 4; a dropped
  first Confirm (307's [SPED=2] crawl) is pressed again on the next poll. 309 is WindowAsync: ip345 and ip380 land
  under it, ip401 WaitWindow(0) waits for it. Report-only: no check counts the presses (decision 7).
- **No press may reach the movie.** With no `movies` key `movies_of` is None and rule 9 only sleeps; every Confirm site
  in the driver is a page, a confirm step, a choice, a name or an opt-in policy. MovieHitArea arms at MBG.Play
  (MBG.cs:205-208), at least ~40 ticks after 313 closes (op_22(10) + op_22(25) + op_22(2) + the init and its wait), so a
  press decided on a stale 313 sample (<= ~200 ms) lands before it, and that sample's frame is at or before the ip502
  row's (313 closes in the same AfterHidden call that releases its WindowSync, Dialog.cs:687-699; ip499 op_22(10)
  precedes ip502): outside the movie's span, which opens AFTER that frame (5.3). The skip dialog is press-only (0.2
  #23), so a press, a skip dialog or the net's answer to one in the span is the driver's or outside input's -- never
  the fork's -- and makes the run uncovered (A-MOVIE, 5.1) while the skip net keeps it alive: No, resumed. (A choice
  of any other shape there would be a script's, where stock has none: O8-MOVIE (a) FAILS it.)
- **The watchdog**: the signature (field, SC, ui, texts, choice, control, x/8, z/8, trace rows: segment_drive.py
  :3427-3429) is STATIC from the ip502 row to the ip863 row -- ~1.1 s of fades and waits, the init, 45.4 s, ~0.2 s:
  ~47-51 s expected (O3's FMV003 stretch was 90.1/90.3 s against an 84.8-s file). O7's frozen 60 would leave ~10 s and
  attribute a V14 to the game (one hitch, one side: VOID-ASYM NOT PROVEN), so F8's rule -- `no_progress_s` = max(60, 3 x
  the longest stretch) -- sizes it (draft 150) and the freeze refuses less than 2 x the stretch.
- **The rate**: plan nothing in ticks across the movie. MBG.cs:217 calls SetTargetFPS(30), but under the live
  `[Graphics] VSync = 1` FPSManager.cs:41-48 keeps vSyncCount 1 and Unity ignores targetFrameRate (O3 measured 60 /
  58.6 fps through FMV003): P-SETTINGS pins VSync "1" (`SETTINGS8`).
- **The trace keeps writing** through the movie and across Field(55): a field change opens no epoch (StoryTrace.cs:97;
  story-o3 kept one `arm` epoch through FMV003 and its 31213 -> 64 seam).

### 2.8 The arrival in REAL 55 (the end per side) and the seam (decision 8)
Rule 1 fires on its first poll in 55 -- real 55 on S AND on F: 31258's e6 t1 ip871 is a raw `Field(55)` and MAPJUMP does
no remap (DoEventCode.cs:1008-1030 -> SetNextMap -> HonoluluFieldMain.cs:444; ForkSiblingField only at ff9.cs:9327 and
HonoluluBattleMain.cs:737); EffectiveFieldId(55) = 55, so 55's rows read fld 55, don 55. Then: the end state read live
(the raced pair aside: 4.9), the last forbidden scan, the end row (55 e0 t0 ip22, waited up to `end_row_s`); nothing is
pressed after rule 1; `end_run` warps to 4600 from 55's FieldHUD. On F the run crossed ONE SEAM, 31258 -> 55, recorded
through the kept `e off fld 55` row (0.2 #20) -- exactly O3's shape (story-o3: "every seam member(63) [31213] -> 64").
O7's LANDING (e) would fail every O8 F run on it and O2's `seam_check` passes vacuously with none, so O8-SEAM owns it
(5.3). A landing in 31205 is impossible (no remap); O1's `31205 55` ForkDonorPatch row is outside O8's set (6.2).

### 2.9 VOID conditions (each a RouteVoid with its class, cell and attribution; the run is not covered)

| | Condition in O8 | by |
|---|---|---|
| V1 | A choice no rule matches (none is on the route; the skip net -- O7's row and the measured-line row, 2.1 -- answers SkipMovieDialog, its prompt published or empty). | game |
| V4 | Control held where no cell's step is due: 164 or 165 before its grant or after its cell's last step; 166 at any time. | game |
| V5 | The stop page ("Env Play()"), nothing pressed (a late-edge warp into 166 takes 166's live ip97 to it: R-FMV's and R-VOID run 3's start, 7.1). | driver in visit 1 (164: the start state; 166 in R-FMV); game after |
| V7 | A step out of attempts (3 on 164's two, 2 on 165's) or interruptions (1): the pinch stalled three times; `at_y` failed on every attempt. | driver |
| V8 | THE KNIGHT WAIT ran out on BOTH clocks (the wall's and the game's) with the bit PUBLISHED as 0 at the window's end: Bit[3811] never read 1 within `timeout_s` of a wait begun at P1 (the knight never sat; the bit latches). | game |
| V10 | A naming screen, a tutorial, a battle. | game |
| V11 | Off the route or its order (rule 2's `stray()`, rule 3); a trigger landing in another place (164.e3 -> 163 / 31255; 165.e3 -> 164 / 31256: a back door, on F a member on the route but out of order); a walk leaving the field; a loss in another exit that lands. | driver after a walk (the landing judge, strayed, door_loss, `stray()` on the walked row); GAME for a field change during THE KNIGHT WAIT (S21: nothing pressed) and otherwise |
| V12 | A forbidden write the driver's own log backs (the knight's talk after a stray Confirm near him). | driver |
| V13 | The budget (the wait's deadline included); an instrument stop; outside input (S12); THE PRIOR BASIS disagreeing with a first move (S19); a y-until's loss with no height on the ring or published (S22); a knight-wait watch that never published the bit at the window's end (S21). | driver |
| V14 | The watchdog alone (the movie never ending; a grant that never comes). | game |
| V19 | On F, a REAL 164, 165 or 166 reached on the route (a `Field()` the chain did not retarget: the landing judge reads it as `to`'s place, rule 2 judges it). A FINDING (`rerun.stop_on`). | game |

Every cell is `[place, sc, visit]` (S13): inside a visit `[its place, 1190, its visit]`; 166's V4/V5/V14 at `[166,
1190, 3]`; V19 on a landing `[place(landing), 1190, the visit just left]` (rule 2 runs before rule 3 counts the
visit). V2, V3, V6, V9, V15-V18 cannot arise (no guarded or default-take choice, no watched cell, no wait_sc or climb,
no battle, no fight, no guard).

### 2.10 Recovery
- **From 55** (every covered run), **mid-walk** (164/165, control held), **mid-wait** (at P1, control held), **mid-page**
  (166, a page up, FieldHUD) and **mid-movie** (166, FieldHUD; the soft reset is dead during a movie,
  UIKeyTrigger.cs:237-344): `end_run` warps to 4600 FIRST (segment_trace.py:537-596; the debug warp needs FieldHUD
  only, Ff9mkDebugMenu.cs:2083 -- O3's F-SMOKE acked `warp 4600` ~8 s into FMV003), then the ladder. R-VOID proves the
  wait, the pinch and the mid-movie stops (F9). A stop while a stray skip dialog is up is unproven (10).
- **The session's end** goes through `end_run` (`end_session_warps`), recorded in `session["ended"]`.

---

## 3. Harness additions (FakeGame only; each opt-in, modelled on the bytes, tested)

No change to `channel.py`, `session.py` or the agent. What is missing is a fake that (a) walks 164 at the engine's radius
80 and 165 at 120 in one run (one global `clearance` today, fakegame.py:418); (b) passes 164's pinch (68.6 a side) the
way the engine's averaged pushes would; (c) holds a walker until the player's HEIGHT releases it and has it store a
story bit after its walk (the knight); (d) plays 166's pages, FMV004 and the move to 55; and (e) plays O8's route. Each
knob's default is today's behaviour; each choice cites the byte or engine line it stands for.

### 3.1 H26 -- THE PER-FIELD CLEARANCE (`fake.clearances`; PART B, B1)
`fake.clearances: dict[int, float] = {}` (set in `FakeGame.__init__`, unpinned) and
```python
    def _clearance(self) -> float | None:
        """H26 (research/o8_design.md 3.1): the engine radius his centre keeps off a wall in THIS field -- the field's
        entry in ``clearances``, else ``clearance`` (today's one value). 164's Steiner is radius 80 (DoEventCode.cs:
        1507-1508, through EffectiveFieldId), 165's 120."""
        return self.clearances.get(self.field_id, self.clearance)
```
`_move_to` (an O7 pin: re-baselined by name in B1's commit) reads `c = self._clearance()` once per step wherever it
read `self.clearance` -- the levels' ValueError, the never-closer rule, `Levels.squeeze(..., c)`, the push-out -- and
`_pushed_out` (unpinned) reads it too. With `clearances` empty every step is today's (the three replays, 3.5). Per-field
`squeeze_slack` needs no knob: it is already a `Levels` constructor argument (one `Levels` per field):
`Levels(PlayerWalkmesh(stock 164), squeeze_slack=12)` for 164 (the bound is radius - slack <= 68.6: slack >= 11.4;
12 is an estimate R-SPIRAL measures, F5), `SQUEEZE_SLACK_W` (8) unchanged.

### 3.2 H25 -- THE KNIGHT WALKER (`_step_walkers`; PART B, B2)
A walker body (`path`, `speed`, `once`) may carry two new keys; a body carrying either is an H25 body:
- **`start`** -- exactly one of `{"y_ge": h}`, `{"y_gt": h}`, `{"y_le": h}`, `{"y_lt": h}` on the PLAYER's published y
  (`player[1]`): the walker stands at index 0 -- `_held` True, so `objects` publishes `moving` False (`_objects_doc`
  unedited) -- until the first tick it holds, then walks and is never held by it again (latched). 164 e1 t1 ip178
  (`f[1] > -8400`, ip187's `JMP_IF` loops while it holds): `{"y_ge": 8400}` -- the release, `height_gate(ip178, ip187)`
  (0.2 #24), which C1's builder test asserts equal to the builder's `start`.
- **`store`** -- `{"after_ticks": n, "args": [sid, tag, ip, byte, width, new, bit]}`: once its `once` path's LAST index is
  reached (`_done`), `n` field ticks later `script_store(*args[:6], bit=args[6])` is called ONCE (`_stored`). The
  countdown runs BEFORE the `_walking` skip (a done walker still counts). ip221-ip230: SetStandAnimation,
  RunAnimation(9920) 59 frames + WaitAnimation, then the store: `{"after_ticks": 61, "args": [1, 1, 230, 3811 >> 3,
  "Bit", 1, 3811]}`. A visit that ends first takes its bodies with it (`_VisitBeat.end`), so the store never comes:
  the MISSING race comes free.
- **The pair rule**: for an H25 body the existing "held by him" test (`near < r`, MoveToward.cs:187-189) applies only at
  `abs(b["y"] - player[1]) < 400` (WalkMesh.Collision's pair band, WalkMesh.cs:919-921: the engine never pairs the
  knight on loop 2 with Steiner on loop 1); every other walker keeps today's XZ-only rule.
- A `start` with any other key, or a `store` without `after_ticks` and seven `args`, raises ValueError on the walker's
  first step (the H23 `hold` reader's place). `_step_walkers` is an O7 pin: re-baselined by name in B2's commit.

The knight in the builder: `{"sid": 1, "uid": 1, "x": 249.0, "z": 4630.0, "y": 11896.0, "r": 220.0, "talk_r": 410.0,
"coll": True, "solid": False, "shown": True, "path": [[249, 4630], [-31, 4436], [-246, 4288], [-409, 4128], [-586,
3884]], "speed": 7.5, "once": True, "start": {"y_ge": 8400}, "store": {"after_ticks": 61, "args": [1, 1, 230, 476,
"Bit", 1, 3811]}}` -- 164 e1 t0 ip14/ip22's placement, t1 ip194-ip215's Walk operands (2-byte, signed), SetWalkSpeed(15)
= 7.5 u a 60-fps frame at WALKER_FRAME_TICKS 0.5, his published r (4 x (20 + 35), HarnessAgent.cs:2349) and his
PRE-RELEASE talk_r (4 x (30 + 50) + 30 + 60 = 410, :2360; 395 only once SetWalkSpeed(15) runs: 0.2 #27 -- the fake does
not model the change, and no test or check reads talk_r: he is talk-only, session.py:5265-5266), y the seat's (the
planner keeps him as a disc on any level: `_npc_levels`). [As built after the review's #2 (11.4): y his placement's
level, 11255.2, and each path point carries its level off stock 164's mesh (H25b: 11255.2 -> 11896.0, the body's y moving
with him), so the pair band reads the level he stands on.]

### 3.3 164's and 165's real meshes (H20 reused)
`Levels(PlayerWalkmesh(extract.stock_walkmesh(164)), squeeze_slack=12)` and `Levels(PlayerWalkmesh(stock 165))` under
`fake.clearances {164's id: 80}`, `fake.clearance` 120. H20's premises hold on both spirals (the walk-machinery
reader: steepest 60-u step 93.5 / 76.7, least stacked gap 4857.6 / 4774.1, 0 edge mismatches): B1 measures and asserts
them in a NEW test (O7's `test_fake_level_meshes_hold_the_levels_premises` is pinned by the O7 baseline: unedited). The
grants place by `place_height` with the bytes' MoveInstantXZY operands: 164 `[2040, 3335, -5647]` -> tri 145 (PSX
-4780, published 4780), not tri 110 (-9776); 165 `[2055, 3411, -10519]` -> tri 57 (-10280), not tri 47 (-15133).

### 3.4 166 and 55 on the fake (H9 and H14 reused: no fake edit)
H9's movie beat is O3-pinned and a visit beat whose steps run out finishes and the scene moves on (0.2 #2), so 166 is
three beats and 55 one, every store through `fake.script_store`:
- **166 A** (visit index 3): the prologue (ip22, 49, 57 := -1, 119 := 0, 138, 200); `{"wait": 2}` (the SYSVAR[3] sync);
  ip255 `Byte[8] := 125`; `{"wait": 34}`; page 307 (slot 0); `{"wait": 30}`; page 308; page 309 `{"async": true}`;
  `{"wait": 4}` (anim 6998); store [6, 1, 345, 208, "Byte", 0, -1]; `{"wait": 30}` (anim 6982 + a sound); store [6, 1,
  380, 208, "Byte", 1, -1]; `{"wait": 30}` (anim 6990); `{"wait_window": 0}` (ip401); `{"wait": 140}` (walk, op_22(10),
  op_22(90), teleport and walk); page 311; `{"wait": 30}`; page 312; `{"wait": 30}`; page 313; `{"wait": 10}`; store [6,
  1, 502, 8, "Byte", 0, -1]; `{"wait": 30}` (the fades, op_22(25), op_22(2), the init). Waits are ticks (x
  `wait_scale`), the animations O7's estimate (`_O7_ANIM_TICKS` 30); R-FMV records the real stretch.
- **The movie**: `{"movie": movie_frames, "skip": dict(_O3_SKIP, armed_after=40)}` (default 120 frames in tests: no
  driver test reads the span; MOVIE's span is the dry run's).
- **166 B** (index 3): `{"wait": 6}` (op_22(1), FadeFilter, op_22(3)); store [6, 1, 863, 2, "Int16", 110, -1];
  `{"field": "55"}` (`field_to["55"]` = 55 itself on BOTH sides: a raw Field(55), 3.6).
- **55** (index 4): the prologue (ip22, 49, 57 := -1, 119 := 0, 138, 200), ip255 `Int16[2] := 106`, ip342 `Byte[8] :=
  125`, `{"wait": 100000}` (rule 1 reads its first poll; the two post-cut stores exercise the race: the live read may
  see 106 and 125).

### 3.5 THE O7 REPLAY (A0b, before any fake edit)
`test_fake_spiral_keeps_the_castle_route_identical` (`REQUIRED_TESTS_O8`): on the hand-stepped fake (`_frame_once`, no
thread, no wall clock), as O7's A0b replayed O6's route, a document of four scenes, every frame whose compact sample
changed -- `[frame, field, ui_state, control, x, y, z, [[slot, raw, text], ...], choice]` -- and every trace row, LF
JSON: (1) and (2) O7's builder `_o7_route` S and F played by O7's scripted player as
`test_fake_level_route_plays_to_164_unattended` plays it (the box, the monologue, Dojebon latched); (3) THE BALCONY: stock
154 with `levels154`, `fake.clearance` 120, scripted presses along 154 #0's planned waypoints (`_o7_plan154`) down the
west flight, Dojebon held (H20's level branch, H23's hold); (4) THE FOOT: stock 163, `squeeze_slack` 8, a press up the
foot from (2098, 3731) toward (2098, 4115) (H21's squeeze and the push-out). (3) and (4) read the install (a warned
skip fails G44). With `O8_CAPTURE_REPLAY=1` it WRITES `research/o7_fake_replay.json` (refusing an existing file, and
unless two captures in one process are equal); without, it COMPARES and fails naming the first differing frame of the
first differing scene; a missing golden FAILS. B1's and B2's edits (`_move_to`, `_pushed_out`, `_step_walkers`) are
neutral when it, O7's own replay of O6 (`test_fake_level_keeps_the_steiner_route_identical`) and O5's
(`test_fake_door_keeps_the_hallway_route_identical`) all read identical.

### 3.6 The O8 route builder (test-side `_o8_route(side, *, short=None, levels=False, wait_scale=0.25, knight=None, movie_frames=120, **faults)`)
Fixture fields `_O8_FIELDS`: S `{"164": 30860, "165": 30861, "166": 30862, "55": 55, "163": 30864}`, F `{"164": 31256,
"165": 31257, "166": 31258, "55": 55, "163": 31255}` -- the end is the LITERAL real id 55 on both sides, as in game: a
seam needs a field of the game's own table (`storytrace.real_field`: `ID_TO_EVT`), so a custom stand-in (30863) would
read as the fork's own ground, never a seam; the fake moves to 55 like any other id. `_O8_MEMBERS = {31256: 30860,
31257: 30861, 31258: 30862, 31255: 30864}`; `_o8_register(game)` (`_o7_register`'s shape) registers 30860-30862, 30864
and the F ids (55 needs no line).
- **The floor**: `_O8_BOX` (-1200, 1600, 3600, 5200) and the planner's `_flat_bgi` over it; on the box a test-side
  `_o8_plane(fake, planes)` wraps `fake._move_to` ON THE INSTANCE and sets `player[1]` after each step from the field's
  plane through three (x, z, published y) anchors -- 164: the spawn (2040, 3335, 4780), P1 (1342, 2252, 8958), e2's
  fire point (24.5, 2270.8, 13008); 165: the spawn (2055, 3411, 10280), P1 (1508, 4698, 11251), e2's fire point (2419.6,
  3130.0, 15169). (A plane through the box is too steep for H20's step bound -- LEVEL_STEP_DY 200 per 60 u -- so heights
  on the box come from the wrapper, never from `Levels`.) With `levels` the two stock meshes (3.3) instead, the plane
  absent.
- **164@342** (index 1): the prologue (ip22, 49, 57 := 385, 130 := 1, 138, 200); `{"wait": 4}`; grant `[2040, 3335,
  -4780]` (box: `place_height` without levels publishes 4780) or `[2040, 3335, -5647]` (levels); store ip764 `Byte[13]
  := 2` (the grant's pass); bodies: the knight (3.2; `knight` overrides its keys -- `{"store": None}` for the
  missing-knight test, `after_ticks` 0 / 300 for the fast and slow ones); door {e2: points 164.e2, stores [[2, 2, 243,
  2, "Int16", 343, -1]], `y_gt` 12000, to "165"; e3: points 164.e3, stores [[3, 2, 243, 2, "Int16", 343, -1]], `y_le`
  6000, to "163"} (`y_le` stands for the bytes' strict `<`: equal heights never occur on these floors), each `ticks` 25
  and its walk-out toward MJPOS's point (`_o7_door`'s rule). The dead stores (e2/e3 t2 ip215) are not modelled: they
  never run.
- **165@343** (index 2): the prologue (ip130 := 1 from 2); grant `[2055, 3411, -10280]` / `[2055, 3411, -10519]`; store
  ip844; door {e2: [[2, 2, 205, 13, "Byte", 3, -1], [2, 2, 233, 2, "Int16", 344, -1]], `y_gt` 15000, to "166"; e3:
  [[3, 2, 243, 2, "Int16", 344, -1]], `y_le` 11000, to "164"}.
- **166@344** and **55@110**: 3.4.
- `short` = a place: that visit alone (its index kept) and the next place's arrival (its prologue, no grant) as the end
  -- R-SPIRAL's 164 -> 165, R-SPIRAL165's 165 -> 166, R-FMV's 166 -> 55 (the movie included).
- The residue: field 70's prologue values by `_o5_field70`; `_warp_writes(342, 1190)` (four rows: [0,0,166], [1,0,4],
  [2,0,86], [3,0,1]).
The builder's stores are the predictions' sites (C1's `test_o8_tower_route_builder_matches_the_keys`: its stores == the
draft's writes, chain, masked and start rows; its trace's `pattern_of` == the draft's `pattern`).

### 3.7 Faults (reused, each absent by default) and test-side stalls
H15/H24's `store_override`, `land_real` (`{"166": 30862}`: 31257's e2 lands in real 166 -- V19), `door_misroute`,
`error_window` (`{1: 9}`: 164's window 56 -- V5 driver; `{2: 9}`: 165's -- V5 game; `{3: 9}`: 166's -- R-FMV's
late-edge V5, 7.1), `grant_at`. Test-side, never knobs:
a wrapper on `g.route_to` that ends 164 #0's first attempt short after T0 and returns only once the fake holds Bit[3811]
(the failed-first-attempt knight: by the store, never by time); one that holds `fake.levels[30860].squeeze_slack` at 8
for the first 164 #1 call (a deterministic stall at the pinch); a wrapper on `g.press` that presses one stray Confirm
once the movie beat passed `armed_after`; the movie beat's skip dict with `header` "" (a skip dialog whose prompt
publishes EMPTY: the measured-line net row's case, 2.1); a wrapper on 164 #1's `g.route_to` that returns only once the
fake's field has left 30860 / 31256, with `landed` set (`x_trigger_to`'s PATH B: the step row appended after the
switch, 1.3's knight_watch); a wrapper on `g.send` that drops the `watch` verb (S21's unpublished watch); a rotated
prior (S19); `fake.freezes` (S23's stall).

---

## 4. Predictions (draft v1: `O8Segment.draft()`; frozen by the LEAD only)

### 4.1 Top level
```json
{"version": 1,
 "what": "O8: 164@1190 (warp, entrance 342; EVT_ALEX1_AC_TOWER_L3) -> the first spiral and THE KNIGHT WAIT -> 165@343 (the second spiral) -> 166@344 (six pages, FMV004 played out) -> Field(55) -> the arrival in REAL 55 at 110 on both sides, SC 1190; stock vs the alxc disc-1 chain as O4 deployed it (route members 31256-31258; one declared seam, 31258 -> 55; PLAN.md, O8) -- a US session",
 "rehearsals": [], "rehearsal_fps": [], "rehearsed": {},
 "order": ["S", "F", "S", "F", "S", "F"], "min_covered": 2, "rerun": {"max": 2, "stop_on": ["V19"]},
 "budget": {"run_s": 600, "run_min_s": 300, "session_s": 3600, "settle_s": 1.0, "no_progress_s": 150, "end_row_s": 10.0},
 "start": {"S": 164, "F": 31256}, "entrance": 342, "scenario": 1190, "lang": "us",
 "end_field": 55, "end_fields": [55], "side_ends": {"S": [55], "F": [55]},
 "route": [164, 165, 166], "visits": [164, 165, 166], "stock_fields": [164, 165, 166, 55],
 "members": {"31240": 64, "...": "...", "31259": 167}, "names": {"31240": "O4_AC_AST", "...": "..."},
 "text_block": 3, "text_blocks": [3], "recovery": 4600, "cut_start": true,
 "start_first": "4.5", "start_music": "4.5", "start_scoped": "4.5", "start_reads": "4.5", "carried": "4.5",
 "start_residue": [[0, 0, 166], [1, 0, 4], [2, 0, 86], [3, 0, 1]], "residue_after_start": [],
 "sc_bytes": [0, 1], "ladder": [], "entrance_bytes": [2, 3], "chain": "4.3", "writes": "4.4",
 "start_dependent": [], "naming": [], "error_path": "4.6", "forbidden_sites": "4.6", "dead": "4.6", "inert": [],
 "live_shared": "4.6", "noise": [], "forbidden": "4.8", "landing": "5.3", "end_state": "4.9", "end_state_trace": "4.9",
 "interruptions": [], "static_objects": [], "seat_watch": "4.10", "movie": "4.10", "seam": "4.10",
 "beats": ["w164_p1", "t164_e2", "w165_p1", "t165_e2"],
 "battles": [], "stop_pages": ["2.1"], "regions": "4.15", "hotspots": {}, "table": ["2.4"], "steps_default": "4.15",
 "choices": ["2.1"], "witness": "2.1", "route_pins": "4.14", "route_mes": "4.14", "route_build": "6.1",
 "pattern": "4.16", "settings": "4.13", "override70": "4.13", "derived": "4.13", "engine": "4.13"}
```
`members` / `names` are O4's twenty (`chain_from_campaign`); `route_members8` derives 31256, 31257, 31258 (printed,
never assumed). `rehearsals`, `rehearsal_fps` and `rehearsed` read EMPTY in the draft: the lead's freeze fills them
(7.3); no test pins any of them, nor a budget, nor a deployed flag, nor a gate witness (O2, O4, O5 and O6 each lost a
pre-merge run to that). `rehearsed` holds what F2-F8 measure and the freeze reads: `stretch_s` (the longest
no-progress stretch of any traced stage), `wait_s` (the longest knight wait), `steps_s` (`{step name: its longest route
wall time}`), `movie_span_s` (the shortest movie span), `narrowest_pinch` (the narrowest wall gap a pinch hold passed).

### 4.2 No SC rung
No store to SC's bytes in any width in 164-166 (the census, 6.1). 55's only SC stores (e10 t1 ip568/ip582) sit behind
`Map.Byte[24]` case 3, past the cut -- reachable on this arrival once e1 t1 advances that case (11.4 "The review" #3),
so SC is not read live (4.9): SC 1190 at the cut is O8-NO-SC's. O8-NO-SC is O3's `no_sc_check`.

### 4.3 The FieldEntrance chain (`Global.Int16[2]`; O8-CHAIN; the first `old` is 342, the warp's entrance)

| # | donor | sid | tag | ip | off | value | what |
|---|---|---|---|---|---|---|---|
| 1 | 164 | 2 | 2 | 243 | 209 | 343 | e2 at the top, then `Field(165)` ip251 (31257 on F) |
| 2 | 165 | 2 | 2 | 233 | 203 | 344 | e2 at the top, then `Field(166)` ip241 (31258 on F) |
| 3 | 166 | 6 | 1 | 863 | 589 | 110 | after FMV004, then `Field(55)` ip871, RAW on F -- the last compared row, THE SEAM's exit row on F |

The back doors store the same values (164 e3 t2 ip243 343, 165 e3 t2 ip243 344): every chain key matches on its site,
never on its value alone. Past the cut 55 ip255 rewrites 110 -> 106.

### 4.4 Registered writes (O8-WRITES: every covered run's keys are EXACTLY these and the chain)

| donor | sid | tag | ip | off | target | value | op | what |
|---|---|---|---|---|---|---|---|---|
| 164 | 0 | 0 | 57 | 51 | Int16[9] | 385 | := | ambient (from 643: START-SCOPED old) |
| 164 | 0 | 0 | 130 | 124 | Byte[13] | 1 | := | ambient (from 1: `start_music`; START-SCOPED old; THE LATE-EDGE START READ) |
| 164 | 0 | 0 | 138 | 132 | Int16[11] | -1 | := | ambient (same) |
| 164 | 0 | 0 | 200 | 194 | Byte[14] | 0 | := | ambient (same) |
| 164 | 0 | 0 | 764 | 758 | Byte[13] | 2 | := | the grant's pass |
| 164 | 1 | 1 | 230 | 70 | Bit[3811] | 1 | := | THE KNIGHT sits (inside THE EXEMPT SPAN, before ip243: O8-ORDER) |
| 165 | 0 | 0 | 57 | 51 | Int16[9] | 385 | := | ambient (same) |
| 165 | 0 | 0 | 130 | 124 | Byte[13] | 1 | := | ambient (from 2) |
| 165 | 0 | 0 | 138 | 132 | Int16[11] | -1 | := | (same) |
| 165 | 0 | 0 | 200 | 194 | Byte[14] | 0 | := | (same) |
| 165 | 0 | 0 | 844 | 838 | Byte[13] | 2 | := | the grant's pass |
| 165 | 2 | 2 | 205 | 175 | Byte[13] | 3 | := | e2, LIVE (165's e2 sets no Map.Bit[162]: 166 off the error path) |
| 166 | 0 | 0 | 57 | 51 | Int16[9] | -1 | := | ambient (K -1) |
| 166 | 0 | 0 | 119 | 113 | Byte[13] | 0 | := | ambient (from 3) |
| 166 | 0 | 0 | 138 | 132 | Int16[11] | -1 | := | (same) |
| 166 | 0 | 0 | 200 | 194 | Byte[14] | 0 | := | (same) |
| 166 | 0 | 0 | 255 | 249 | Byte[8] | 125 | := | (same: field 70 left 125 -- THE EARLY-EDGE START READ) |
| 166 | 6 | 1 | 345 | 71 | Byte[208] | 0 | := | under page 309 (same here: START-SCOPED old) |
| 166 | 6 | 1 | 380 | 106 | Byte[208] | 1 | ++ (prior 166/6/1/345) | one loop pass (ip385 `Byte[208] < 1`) |
| 166 | 6 | 1 | 502 | 228 | Byte[8] | 0 | := | after page 313: the last store before FMV004 (MOVIE's span opens; the end state's Byte[8], 4.9) |

20 writes + 3 chain = **23 keys a run**, beside 6 masked rows (Bit[191] ip22, Bit[184] ip49, each visit). Every key's
`m` 1, `src` "eb". EXACT: the census classifies every site (6.1); R-FULL shows the exact set before the freeze (F6).

### 4.5 The start (O8-START), the start-scoped olds, the start reads, the carried values
```json
"start_first": {"donor": 164, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 22, "off": 16, "target": "Global.Bit[191]", "value": 0, "op": ":=", "what": "164's Main_Init: its first store (emitted same: a new site)"},
"start_music": {"donor": 164, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 130, "off": 124, "target": "Global.Byte[13]", "value": 1, "op": ":=", "old": 1, "what": "164's K-385 branch from the warp's Byte[13] 1 (field 70's prologue :=1 at ip130); ip97 and ip119 are dead (Int16[9] just set 385)"},
"start_scoped": [
 {"site": [164, 0, 0, 57], "target": "Global.Int16[9]", "here": [643, 385], "after": {"run": "O1-O7", "old": 385, "value": 385, "source": "old: the last pre-cut tuple on the target in o7_predictions_v1.json's pattern (163 e0 t0 ip57, 385); story-o7's six runs read 164 ip57 385 -> 385 past the cut"}},
 {"site": [164, 0, 0, 130], "target": "Global.Byte[13]", "here": [1, 1], "after": {"run": "O1-O7", "old": 2, "value": 1, "source": "... (163 e0 t0 ip684, 2); story-o7: 164 ip130 2 -> 1 past the cut"}},
 {"site": [166, 6, 1, 345], "target": "Global.Byte[208]", "here": [0, 0], "after": {"run": "O1-O7", "old": 1, "value": 0, "source": "... (159 e16 t1 ip648, 1); no 166 row in story-o7 (O7 ends in 164)"}}],
"start_reads": [
 {"site": [166, 0, 0, 255], "target": "Global.Byte[8]", "old": 125, "race": [70, 0, 0, 249], "race_value": 125, "edge": "before",
  "why": "field 70 e0 t0 ip249 Byte[8] := 125 lies inside the warp window (after ip130, behind ip238-246's SYSVAR[3] wait, before ip475): a warp before it leaves 0, and this store -- the route's first on Byte[8] (164 and 165 neither store nor read it) -- reads 0 (O7's 159 ip290 rule)"},
 {"site": [164, 0, 0, 130], "target": "Global.Byte[13]", "old": 1, "race": [70, 0, 0, 475], "race_value": 2, "edge": "after",
  "why": "field 70 e0 t0 ip475 Byte[13] := 2 closes the warp window: a warp after it reaches 164 with Byte[13] 2 and 164 takes NO error path (K 385: ip97 needs Int16[9] < 0), so this store reads 2 SILENTLY -- registered so the late race is A-START, never NOT PROVEN by START (c) or PATTERN (research dispute 9)"}],
"carried": {"why": "a true O1-O7 run's value (composed over the frozen O1-O7 keys in segment order) where the raw start holds 0; neither written nor read by any function the route runs in 164@342, 165@343, 166@344 (the knight's TALK -- 164 e1 t3 and what only it reaches, e7 t11/t12 -- set aside: never driven, its stores forbidden)",
 "values": {"Global.Bit[3717]": [0, 1], "Global.Bit[3718]": [0, 1], "Global.Bit[3795]": [0, 1], "Global.Bit[3796]": [0, 1],
            "Global.Bit[3815]": [0, 1], "Global.Bit[3854]": [0, 1], "Global.Bit[3855]": [0, 1], "Global.Byte[18]": [0, 1],
            "Global.Byte[303]": [0, 1], "Global.Byte[472]": [0, 4], "Global.Byte[475]": [0, 100], "Global.Byte[6]": [0, 11],
            "Global.Int16[469]": [0, 1042], "Global.UInt16[19]": [0, 1807], "Global.UInt16[21]": [0, 8]},
 "party": {"values": ["[Zidane]", "[Steiner]"], "source": "not a gEventGlobal target: New Game's party; 153 e32 t1's rebuild (O6, UInt16[21] := 8) -- typed, labelled, never derived; no party op runs in 164-166, and Steiner is the controlled character on both sides (164 e7 ip325, 165 e7 ip317, 166 e6 ip262)"}}
```
**No start-dependent key** (decision 3): every route read resolves the same branch from both starts -- 164's prologue
tests, the spawn SWITCH (342 on both), the knight's `Bit[3811]` (0 on both: no O1-O7 key writes it), 165's and 166's
chains (`Byte[208]` written before read), the movie gates (`B_SYSVAR[15]` is engine state, GetSysvar.cs:49-50). Only
OLDS differ: the three start-scoped sites, each a writes key at the same value, their `after.old` read off O7's FROZEN
pattern (`last_values`, the new of the LAST pre-cut tuple per target) -- never an end state read after the site's own
field ran (O7's claim review #3). The SET is DERIVED (`scoped_derivation8` from `START_VALUES8`: exactly 164 ip57, 164
ip130 and 166 e6 t1 ip345 of the 20 differ); O8-KEYS (b) and the freeze refuse a dropped or an extra entry.

**THE START READS, EACH WITH ITS RACE** (critique #2). `race` names the field-70 store the warp window races, `race_value`
its stored value, `edge` which side of it the warp must fall (`before`: the read sees the pre-store value if the warp
came first; `after`: the read sees the store's value if the warp came last). `race_site8` returns `race` only when the
route pin there is `SET({<target> const(<race_value>) B_LET B_EXPR_END})` (70 ip249 `Byte[8] := 125`; 70 ip475 `Byte[13]
:= 2`), else None -- O7's `race_site` keys on the read's own `old` and would resolve 164 ip130's race to 70 ip130 (`:=
1`), the wrong store. `why_void` (5.1) reads both branches per read with the explicit race, and every reason opens
with `START_READ`, so VOID-ASYM (b) sets it aside. The override's ip558 `Byte[13] := 3` has no stock pin: P-OVERRIDE
covers it (a different override is A-INSTALL).

**THE CARRIED VALUES, DERIVED.** `carried8` composes the FROZEN keys of `PRIOR_SEGMENTS8` (O1 v4, O2-O7 v1) by O7's
rule (`carried_from_segments`: each segment checked against its own `end_state`), less O8's targets (writes, chain,
masked): the fifteen above -- O7's fourteen and `Bit[3796]` (O7's 159 e16 t1 ip672, the only one O7 adds). O8-KEYS (d)
refuses a typed set that differs, a carried target in `end_state` (Bit[3796] above all: O7 held it at 1, the raw
start at 0), or one stored or read by a function the route RUNS (`route_run_texts`: the knight's talk reads
Bit[3848]-[3855] at e1 t3 ip326 and is set aside, 0.2 #11).

### 4.6 The error path, the forbidden sites, the dead sites (registered; never expected)
- `error_path` (10; `Byte[13] := 9` / `Byte[14] := 9` on an incoming 2 with `Int16[9]` / `Int16[11]` < 0 WHERE THAT
  GUARD CAN HOLD, and window 56's two resets `:= 0` on an incoming 9): 164 e0 t0 ip178 (off 172), ip607 (601), ip641
  (635); 165 ip178, ip687 (681), ip721 (715); 166 ip97 (off 91), ip178, ip332 (326), ip366 (360). A 164 row is A-START
  (V5, driver); any other the game's. O8-CENSUS proves each guard reachable from SOME arrival value (`reach8`, 1.3; the
  claim review's #9).
- `forbidden_sites` (8; what the knight's talk, the talk's own scripts and a back door write): 164 e1 t3 ip308 (off 49)
  `Bit[3851] := 1`, ip420 (161) `Bit[3792] := 1`, ip627 (368) `Bit[7211] := 1`, ip690 (431) `Int16[224] := -761`
  (64775); 164 e7 t11 ip399 (16) `Byte[208] := 0`, ip434 (51) `Byte[208] ++` (prior 164/7/11/399) -- reached only by
  `RunScriptSync(4, 250, 11)` at e1 t3 ip415; 164 e3 t2 ip243 (209) `Int16[2] := 343` (the back door -> 163); 165 e3 t2
  ip243 (209) `Int16[2] := 344` (the back door -> 164).
- `dead` (14, each with why): every field's e0 t0 ip41 `Int16[2] := 10000` (behind `Bit[184] == 1`, 0); 164 and 165
  ip97 `Byte[13] := 9` (off 91: ip57 just set `Int16[9]` 385, so ip79's `Byte[13] == 2 && Int16[9] < 0` never holds --
  0.2 #19, revised); 164 and 165 ip119 `Byte[13] := 0` (`Int16[9]` 385 is not < 0); 166 ip130 `Byte[13] := 1`
  (`Int16[9]` just set -1); every field's
  ip211 `Byte[14] := 1` (`Int16[11]` just set -1); 164 e2 t2 ip215, 164 e3 t2 ip215 and 165 e3 t2 ip215 `Byte[13] := 3`
  (off 181: behind `Map.Bit[162] == 0` at ip193, which the door's own ip54 set 1 first: 0.2 #19).
- `inert`: [] (every entry with a store is instanced at its field's route entrance: 0.2 #3).
- `live_shared`: `[{"donor": 166, "sid": 2, "from": [166, 6, 1, 489], "why": "RunSharedScript(2): the clank loop, run
  only from e6 t1 ip489 and stopped at ip498; it stores no global (0.2 #4)"}]`.
3 + 20 + 10 + 8 + 14 + `start_first` = **56 keys**, each over its own site (O8-KEYS (a)).

### 4.7 Noise: none
No `SYSVAR[0]`-gated store; no battle, ATE, choice or revisit; the walks write nothing (each grant's post-grant store
lands in the grant's pass, before rule 8's settle) but the knight's ip230, which O8-ORDER bounds; FMV004 and the
skip dialog write no global (MBG.cs, fldfmv.cs, FieldHUD.cs: none); 166's e2 is storeless. `noise: []`.

### 4.8 Forbidden
```json
[{"off_route": true, "cause": "walk",
  "why": "a write off the route: S, a place outside [164, 165, 166] + [55]; F, a field that is neither a member whose donor is on the route nor REAL 55 (a real 164/165/166 on F: an un-retargeted Field(); 163/31255 after 164.e3, backed by its V11 step row)"},
 {"donor": 164, "sid": 1, "tag": 3, "cause": "confirm_talk", "object": 1,
  "why": "the knight's TALK (164 e1 t3: Bit[3851], Bit[3792], Bit[7211], Int16[224]): a Confirm near him with control held -- nothing on the route presses one there"},
 {"donor": 164, "sid": 7, "tag": 11, "cause": "confirm_talk", "object": 1,
  "why": "164 e7 t11 (Byte[208]), run only by the knight's talk (RunScriptSync(4, 250, 11) at e1 t3 ip415)"}]
```
No door pattern (O7's reason): a back door's tag 2 runs its `Field()` right after its stores, so its landing is off the
route (164.e3 -> 163: `off_route` hits) or out of order (165.e3 -> 164: rule 3's V11, its store in 165, a route place);
a covered run cannot hold either (WRITES exact).

### 4.9 End state
**Corrected by the review's #3 (11.4):** SC is out of the live read too -- 55's own arrival scene stores it 1400 (e10
t1 ip568 / ip582, `end_state_scene`), and O8-KEYS (g) holds a Map variable only where no other 55 function stores it
(`end_map_held8`), never `Map.Byte[24]`. The JSON below is the first draft's; the live read is its twelve without SC.

Read live on arrival in REAL 55 (O8-STATE (b)), WITHOUT the raced pair:
```json
{"Global.UInt16[0]": 1190, "Global.Bit[191]": 0, "Global.Bit[184]": 0, "Global.Int16[9]": -1, "Global.Byte[13]": 0,
 "Global.Int16[11]": -1, "Global.Byte[14]": 0, "Global.Bit[3811]": 1, "Global.Byte[208]": 1,
 "Global.Bit[3851]": 0, "Global.Bit[3792]": 0, "Global.Bit[7211]": 0, "Global.Int16[224]": 0}
```
Nine the route leaves (55's prologue rewrites Int16[9], Byte[13], Int16[11] and Byte[14] same-valued: no race), and
`UNTOUCHED8` -- the knight's talk targets, 0 since New Game and in O7's frozen end state. Never a carried target. And
from the TRACE (O8-STATE (c), by place at the side's own field of 166):
```json
"end_state_trace": {
 "Global.Int16[2]": {"value": 110, "site": {"place": 166, "sid": 6, "tag": 1, "ip": 863}, "why": "55 e0 t0 ip255 rewrites it 110 -> 106 in the cut's frame (ip229: SC 1190 < 1400): the live read races"},
 "Global.Byte[8]": {"value": 0, "site": {"place": 166, "sid": 6, "tag": 1, "ip": 502}, "why": "55 e0 t0 ip342 rewrites it 0 -> 125 after its SYSVAR[3] sync, in the prologue's frame by precedent (O7's 159 ip290; O3's 64 ip475, same-valued there: 0.2 #26): the live read races"}}
```
THE RACED SET IS DERIVED (decision 8): `end_race8` walks 55 e0 t0 from the arrival's values (the pattern's last values
over the raw start, SC 1190, Map variables 0) through its first long yield (ip387 `op_22(2)`) ON TO ITS RET (ip565) and
returns the targets stored to another value -- exactly {Int16[2], Byte[8]} (0.2 #5, #26). To its RET, because the live
read lands LATER than the yield: `read_end_state` sends a `watch` and waits for a publish carrying every bit
(segment_drive.py:1004-1018), by when 55's other tag-1 loops run too (the claim review's #11). So O8-KEYS (g) also
proves that NO OTHER 55 function stores an `end_state` target on this arrival: every such site outside e0 t0 sits
behind a `Map.Byte[24]` case other than the arrival's 1 (`reach8` with `{Map.Byte[24]: 1}`: today e10 t1 ip568 / ip582
`UInt16[0] := 1400`, case 3), else it FAILS naming the site; e8 t1's case-3 stores and e7 t2's door hold no `end_state`
target (0.2 #26). The draft computes `end_state` from the registered keys in route order (the last write of each
target), the raced targets moved to `end_state_trace` at their last pre-cut site, `UNTOUCHED8` 0 -- never typed. O8-KEYS
(g) re-derives the set from the install's 55 and refuses a draft that differs; the freeze refuses a raced target in
`end_state`.

### 4.10 The walks, the knight, the movie, the seam (registrations the analysis reads)
O8-WALK reads every table step (2.4); O8-ORDER and O8-KNIGHT read:
```json
"seat_watch": {"donor": 164, "sid": 1, "name": "the knight", "seat": [-586, 3884], "tol": 30, "site": [164, 1, 1, 230],
  "why": "164 e1 t1 ip215's last Walk(64950, 3884) seats him (tri 120, PSX -11896); step 1 plans with npcs on round him 300.0 u off its line -- the premise read at the wait's end (the ring at wait_flag.frame) and at step 1's frame0, keyed by place (31256 reads as 164), every run (O8-KNIGHT)"},
"movie": {"donor": 166, "visit": 3, "name": "FMV004", "cinematic": [166, 6, 1, 633], "play": [166, 6, 1, 711],
  "from": [166, 6, 1, 502], "to": [166, 6, 1, 863], "file_s": 45.412, "slack_s": 5.0, "clock_every": 30,
  "why": "Cinematic(0, 9, 1, 1) -> MBGDiscTable[1][9] = MBG_DEF(\"FMV004\", 1, 0), type 0 (fldfmv.cs:56-58, MBG.cs:830); MoguriVideo's ma/FMV004.bytes, 45.412 s at 29.97 fps, on both sides; PLAYED OUT: no press, no choice and no skip dialog after the ip502 row's frame through the ip863 row's (a run with one is uncovered, A-MOVIE: the skip dialog is press-only), the span at least file_s - slack_s at the rate measured inside it (O8-MOVIE)"},
"seam": {"donor": 166, "to": 55, "exit": [166, 6, 1, 863], "field": [166, 6, 1, 871], "fields": [55],
  "why": "31258 is 166 byte for byte; its only Field() is e6 t1 ip871 Field(55), RAW, and MAPJUMP does no remap: every F run crosses from member(166) into REAL 55 -- one seam, read through the kept `e off fld 55` row, its exit row ip863 (O8-SEAM)"}
```
The `wait_flag` is the step's (2.4). `interruptions`: [] (none registered: a loss of control on the route that is no
door's is an attempt's `interrupted`, within `interrupts` 1). `static_objects`: [] (the knight walks; his claim is
`seat_watch`'s).

### 4.11 Coverage beats, the input witness
Beats: the four steps' (`w164_p1`, `t164_e2`, `w165_p1`, `t165_e2`) plus `end == "reached"`. `w164_p1` is done only
after THE KNIGHT WAIT read (S21 is step 0's evidence). `witness` (2.1).

### 4.12 Budget and recovery
Estimated ~2.5 min a run (O7's measured 86-101 s for New Game + the warp + six walks, here four walks of 1452-6832 u,
the wait, six pages and FMV004's ~50 s). Drafts: `run_s` 600, `run_min_s` 300, `session_s` 3600, `settle_s` 1.0,
`no_progress_s` 150 (2.7), `end_row_s` 10. F8 replaces every one from R-FULL. No step carries a `timeout_s`: route_to
passes it only to the start's control wait, the landing and the facing step, never to the walk (0.2 #12; the
driver review's #11), so `steps_default`'s 20 stands and nothing measured sizes it.

### 4.13 Settings, the New-Game override, the engine, the derived facts
`SETTINGS8`: O7's frozen 31 keys PLUS `"Graphics": {"VSync": "1"}` (the movie's wall time and the measured stretch rest on
it; live today, Memoria.ini line 71: 0.2 #18) -- 32. P-SETTINGS reads the dict generically (`o3_prima_vista.p_settings`):
no code change. `override70` {FF9CustomMap-world: 2ce8887e...}, `engine` {x64, x86: ba976242...}, `derived` (cfg.control
0, 30 ticks a second). The freeze refuses an engine that is not the live DLLs'.

### 4.14 The route pins and route_mes
`route_pins` -- `[donor, sid, tag, ip, eb-src text]`, each compared EXACTLY with the stock US script's text (O8-KEYS
(e)). The texts below were read off the listings while designing (`<R>/reconcile/L{164,165,166,55,70}.txt`); C1 reads
each the same way and the commit records the count (~120; every height test pinned WITH its consuming jump and
that jump's target, the claim review's #7, 0.2 #24):
- **164**: e0 t0 ip22 `SET({Global.Bit[191] const(0) B_LET B_EXPR_END})`, ip57 `SET({Global.Int16[9] const(385) B_LET
  B_EXPR_END})`, ip130 `SET({Global.Byte[13] const(1) B_LET B_EXPR_END})`, ip219 `SetControlDirection(40, 40)`, ip223
  `InitObject(7, 0)`, ip226 `InitObject(1, 0)`, ip229 `InitRegion(2, 0)`, ip232 `InitRegion(3, 0)`, ip597 / ip631
  `WindowAsync(6, 0, 56)`, ip649 `SET({Map.Bit[159] const(1) B_LET B_EXPR_END})`, ip657 `SET({Map.Bit[158] const(1) B_EQ
  B_EXPR_END})`, ip676 `SET({Map.Bit[159] const(1) B_EQ B_EXPR_END})`, ip687 `SET({Map.Bit[156] const(0) B_EQ
  B_EXPR_END})`, ip698 `EnableMove()`, ip764 `SET({Global.Byte[13] const(2) B_LET B_EXPR_END})`; e7 t0 ip22 `SWITCH(344,
  L47, L12)`, ip65 `SET({Map.Int16[0] const(2040) B_LET B_EXPR_END})`, ip73 `SET({Map.Int16[4] const(3335) B_LET
  B_EXPR_END})`, ip89 `SET({Map.Int16[2] const(59889) B_LET B_EXPR_END})`, ip100 `SetModel(5489, 104)`, ip138
  `SetObjectLogicalSize(30, 35, 50)`, ip153 `MoveInstantXZY({obj(uid=255).f[0] B_EXPR_END}, {Map.Int16[2] B_EXPR_END},
  {obj(uid=255).f[2] B_EXPR_END})`, ip325 `DefinePlayerCharacter()`, ip326 `SET({Map.Bit[158] const(1) B_LET
  B_EXPR_END})`, ip356 `EnableMove()`; e1 t0 ip46 `SET({Global.Bit[3811] B_EXPR_END})`, ip124 `SetObjectLogicalSize(20,
  20, 30)`; e1 t1 ip160 `SET({Global.Bit[3811] const(0) B_EQ B_EXPR_END})`, ip175 `op_22(1)`, ip178
  `SET({obj(uid=250).f[1] const(57136) B_GT B_EXPR_END})`, ip187 `JMP_IF(L15)` (back to ip175: the wait loop), ip190
  `SetWalkSpeed(15)`, ip194 `Walk(65505, 4436)`, ip201 `Walk(65290, 4288)`, ip208 `Walk(65127,
  4128)`, ip215 `Walk(64950, 3884)`, ip225 `RunAnimation(9920)`, ip230 `SET({Global.Bit[3811] const(1) B_LET
  B_EXPR_END})`; e1 t3 ip415 `RunScriptSync(4, 250, 11)`, ip452 `RunScriptSync(4, 250, 12)`; e2 t0 ip10 `SetRegion(...)`
  (its five packed points); e2 t2 ip34 `SET({B_SYSVAR[2] B_EXPR_END})`, ip42 `SET({obj(uid=250).f[1] const(53536) B_LT
  B_EXPR_END})`, ip51 `JMP_IFNOT(L221)`, ip54 `SET({Map.Bit[162] const(1) B_LET B_EXPR_END})`, ip71 `ExitField()`, ip165
  `op_22(25)`, ip193 `SET({Map.Bit[162] const(0) B_EQ B_EXPR_END})`, ip243 `SET({Global.Int16[2] const(343) B_LET
  B_EXPR_END})`, ip251 `Field(165)`, ip255 `RET()` (L221); e3 t0 ip10 `SetRegion(...)`; e3 t2 ip42
  `SET({obj(uid=250).f[1] const(59536) B_GT B_EXPR_END})`, ip51 `JMP_IFNOT(L221)`, ip54, ip193, ip243 (the same texts),
  ip251 `Field(163)`, ip255 `RET()`.
- **165**: e0 t0 ip130 `SET({Global.Byte[13] const(1) B_LET B_EXPR_END})`, ip219 `SetControlDirection(24, 24)`, ip223 `InitCode(1, 0)`, ip226 `InitObject(7, 0)`, ip229 /
  ip232 `InitRegion(2, 0)` / `(3, 0)`, ip778 `EnableMove()`, ip844 `SET({Global.Byte[13] const(2) B_LET B_EXPR_END})`; e7
  t0 ip14 `SWITCH(345, L47, L12)`, ip57 `SET({Map.Int16[0] const(2055) B_LET B_EXPR_END})`, ip65 `SET({Map.Int16[4]
  const(3411) B_LET B_EXPR_END})`, ip81 `SET({Map.Int16[2] const(55017) B_LET B_EXPR_END})`, ip92 `SetModel(5489, 104)`,
  ip130 `SetObjectLogicalSize(30, 35, 50)`, ip145 `MoveInstantXZY(...)`, ip317 `DefinePlayerCharacter()`; e2 t0 ip10
  `SetRegion(...)` (four points); e2 t2 ip38 `SET({obj(uid=250).f[1] const(50536) B_LT B_EXPR_END})`, ip47
  `JMP_IFNOT(L215)`, ip61 `ExitField()`,
  ip62 `SET({Map.Bit[158] const(0) B_LET B_EXPR_END})`, ip183 `SET({Map.Bit[162] const(0) B_EQ B_EXPR_END})`, ip205
  `SET({Global.Byte[13] const(3) B_LET B_EXPR_END})`, ip233 `SET({Global.Int16[2] const(344) B_LET B_EXPR_END})`, ip241
  `Field(166)`, ip245 `RET()` (L215); e3 t0 ip10 `SetRegion(...)`; e3 t2 ip42 `SET({obj(uid=250).f[1] const(54536) B_GT
  B_EXPR_END})`, ip51 `JMP_IFNOT(L221)`, ip54, ip193, ip243, ip251 `Field(164)`, ip255 `RET()`.
- **166**: e0 t0 ip57 `SET({Global.Int16[9] const(65535) B_LET B_EXPR_END})`, ip119 `SET({Global.Byte[13] const(0) B_LET
  B_EXPR_END})`, ip219 `SetControlDirection(64, 64)`, ip223 / ip226 / ip229 `InitObject(6, 0)` / `(3, 0)` / `(5, 0)`,
  ip244 `SET({B_SYSVAR[3] const(0) B_NE B_EXPR_END})`, ip255 `SET({Global.Byte[8] const(125) B_LET B_EXPR_END})`, ip322 /
  ip356 `WindowAsync(6, 0, 56)`, ip382 `SET({Map.Bit[158] const(1) B_EQ B_EXPR_END})`, ip423 `EnableMove()`; e6 t0 ip42
  `SetModel(5489, 104)`, ip80 `SetObjectLogicalSize(30, 35, 50)`, ip262 `DefinePlayerCharacter()`; e6 t1 ip278 `SWITCH(0,
  L659, L12)`, ip310 `WindowSync(0, 128, 307)`, ip328 `WindowSync(0, 128, 308)`, ip334 `WindowAsync(0, 128, 309)`, ip345
  `SET({Global.Byte[208] const(0) B_LET B_EXPR_END})`, ip380 `SET({Global.Byte[208] B_POST_PLUS B_EXPR_END})`, ip401
  `WaitWindow(0)`, ip454 `WindowSync(0, 128, 311)`, ip474 `WindowSync(0, 128, 312)`, ip489 `RunSharedScript(2)`, ip492
  `WindowSync(0, 128, 313)`, ip498 `StopSharedScript()`, ip502 `SET({Global.Byte[8] const(0) B_LET B_EXPR_END})`, ip609
  `SET({B_SYSVAR[15] const(128) B_AND const(0) B_EQ B_EXPR_END})`, ip633 `Cinematic(0, 9, 1, 1)`, ip711 `Cinematic(2, 0,
  0, 0)`, ip756 `SET({B_SYSVAR[15] const(127) B_AND const(1) B_NE B_EXPR_END})`, ip863 `SET({Global.Int16[2] const(110)
  B_LET B_EXPR_END})`, ip871 `Field(55)`.
- **55** (past the cut; what `end_race8` and the end row stand on): e0 t0 ip22 `SET({Global.Bit[191] const(0) B_LET
  B_EXPR_END})`, ip229 `SET({Global.UInt16[0] const(1400) B_LT Global.Int16[2] const(106) B_EQ B_OROR B_EXPR_END})`,
  ip255 `SET({Global.Int16[2] const(106) B_LET B_EXPR_END})`, ip331 `SET({B_SYSVAR[3] const(0) B_NE B_EXPR_END})`, ip342
  `SET({Global.Byte[8] const(125) B_LET B_EXPR_END})`, ip387 `op_22(2)`.
- **70** (the warp's window: what `start_music` and both `start_reads` races stand on): O7's five -- e0 t0 ip130
  `SET({Global.Byte[13] const(1) B_LET B_EXPR_END})`, ip238 `SET({B_SYSVAR[3] const(0) B_NE B_EXPR_END})`, ip246
  `JMP_IF(L229)`, ip249 `SET({Global.Byte[8] const(125) B_LET B_EXPR_END})`, ip475 `SET({Global.Byte[13] const(2) B_LET
  B_EXPR_END})` -- text-identical in stock and in the live override (2ce8887e).
Plus the SCANS O8-KEYS runs over each route field at its entrance (instanced entries only, `instanced_at8`): exactly one
`DefinePlayerCharacter` (the pinned one: control binds to the last); no `B_PARTYCHK`, `SetPartyReserve`, `RemoveParty`
or party-add op; every `SetControlDirection` the pinned one's (one basis a field); no `Map.Bit[144]` store.

`route_mes` (block 3, US, the asset the engine reads; O8-TEXT reads it):
```json
"route_mes": {"block": 3, "pages": [{"mes": 307, "holds": "[STNR]"}, {"mes": 308, "holds": "[STNR]"}, {"mes": 309, "holds": "[STNR]"},
              {"mes": 311, "holds": "[STNR]"}, {"mes": 312, "holds": "[STNR]"}, {"mes": 313, "holds": "[STNR]"}],
              "stop_page": {"mes": 56, "holds": "Env Play()"}}
```
The [STNR] pages render New Game's default name for character 3 on the raw start: text only, the same block on both
sides, never judged (O8 registers no naming).

### 4.15 The regions, the table's defaults
Each exit's `points` the first SetRegion of its (donor, entry), in the engine's order (IsInQuad is a RING OF EARS,
EventEngine.TreadQuad.cs:24-39: 164.e2's centroid (472, 2170) is DEAD; QuadCircleData holds no 164/165 row,
EventEngineUtils.cs:1722-1737, so S and F test the same ring); its `gate` READ off its pinned tag 2 by `height_gate`
over the test AND its consuming jump (O8-REGIONS (c); every door's is a `JMP_IFNOT` to its RET, so the door fires
where its test holds: 0.2 #24):

| key | points | role | to @ entrance | gate (its pin) |
|---|---|---|---|---|
| 164.e2 | (946,2249) (1122,1974) (222,2039) (-25,2186) (93,2401) | exit | 165 @ 343 | `{"y_gt": 12000}` (e2 t2 ip42 `f[1] const(53536) B_LT`, ip51 `JMP_IFNOT(L221)`) |
| 164.e3 | (938,3257) (1051,2471) (2066,2776) (2233,2840) (1738,3462) | exit | 163 @ 343 | `{"y_lt": 6000}` (e3 t2 ip42 `const(59536) B_GT`, ip51 `JMP_IFNOT(L221)`) |
| 165.e2 | (3298,3179) (3241,2829) (2401,3074) (2494,3428) | exit | 166 @ 344 | `{"y_gt": 15000}` (e2 t2 ip38 `const(50536) B_LT`, ip47 `JMP_IFNOT(L215)`) |
| 165.e3 | (1209,2668) (1437,2069) (2169,2636) (2395,3155) (1780,3363) | exit | 164 @ 344 | `{"y_lt": 11000}` (e3 t2 ip42 `const(54536) B_GT`, ip51 `JMP_IFNOT(L221)`) |

166 has no gateway and 55 is the END place (its regions and census are O9's). The 5-point region, never
`scan_gateways`' 4-point `zone`, is what a step avoids (its near edge). `steps_default` is O7's exactly (`attempts` 2,
`interrupts` 1, `timeout_s` 20, `tolerance` 45, `exit_slack` 40, `exit_wait_s` 5.0, `npcs` true, `overlay_ok` false,
`immediate` false, `settle` null, `lunge_ticks` 0, `min_depth` 40, `confirm_s` 4.0, `climb` O2's).

### 4.16 The emitted row pattern (O8-PATTERN; R-FULL measures it)
`pattern` = `{"visits": [...], "floating": [], "counts": [], "why"}`, each tuple `[place, sid, tag, off, target, new,
same]`:
- visit 1 (164): `[164,0,0,16,Bit[191],0,1] [164,0,0,43,Bit[184],0,1] [164,0,0,51,Int16[9],385,0]
  [164,0,0,124,Byte[13],1,1] [164,0,0,132,Int16[11],-1,1] [164,0,0,194,Byte[14],0,1] [164,0,0,758,Byte[13],2,0]
  [164,1,1,70,Bit[3811],1,0] [164,2,2,209,Int16[2],343,0]` -- 9;
- visit 2 (165): `[165,0,0,16,Bit[191],0,1] [165,0,0,43,Bit[184],0,1] [165,0,0,51,Int16[9],385,1]
  [165,0,0,124,Byte[13],1,0] [165,0,0,132,Int16[11],-1,1] [165,0,0,194,Byte[14],0,1] [165,0,0,838,Byte[13],2,0]
  [165,2,2,175,Byte[13],3,0] [165,2,2,203,Int16[2],344,0]` -- 9;
- visit 3 (166): `[166,0,0,16,Bit[191],0,1] [166,0,0,43,Bit[184],0,1] [166,0,0,51,Int16[9],-1,0]
  [166,0,0,113,Byte[13],0,0] [166,0,0,132,Int16[11],-1,1] [166,0,0,194,Byte[14],0,1] [166,0,0,249,Byte[8],125,1]
  [166,6,1,71,Byte[208],0,1] [166,6,1,106,Byte[208],1,0] [166,6,1,228,Byte[8],0,0] [166,6,1,589,Int16[2],110,0]` -- 11.
29 `w` rows before the cut (6 masked), no `c` row (the same-valued writes -- 10 of the 20 by the tuples above -- are
each the first at their site in the epoch: the sink suppresses nothing); then 55 e0 t0 ip22 (`[55,0,0,16,Bit[191],0,1]`), the cut. No floating row: the
bytes fix every order but two, both made fixed -- 164 ip230 before ip243 by THE KNIGHT WAIT (O8-ORDER), and 166 ip255
before e6 t1 ip345 by ~2.5 s of scene (ip255 lands in the prologue's frame by precedent; R-FULL confirms, F6).

---

## 5. Checks (O8's analysis)

### 5.1 Reading a run: the COVERED rule
O7's rule (skipped, install changed, the drive not reaching the end, a beat not done, no or an incomplete trace,
A-NOSTART, a BACKED forbidden hit, A-MISMATCH, A-START on the start place's error path -- 164's -- and A-NOEND, a 55
row that never came), with THE START READS read through their EXPLICIT races (`why_void`, 4.5). For each
`start_reads` entry, two branches, each A-START by the driver, each reason opening with `START_READ`:
- **the read**: the run's row at the site reads another `old`, and NOTHING earlier in the run touched the target's bytes
  (an earlier row explains the old: a store of the run itself, which WRITES and PATTERN judge) -- "the start read
  Global.Byte[8] at 166 e0 t0 ip255 (fld F) reads old 0, not 125, nothing earlier in the run touching it: the warp
  left field 70 before its e0 t0 ip249 (Byte[8] := 125) -- the start's"; for the `after` edge "... reads old 2, not 1
  ...: the warp left field 70 after its e0 t0 ip475 (Byte[13] := 2) -- the warp window's late edge -- the start's";
- **the raced row**: the race's own `w` row (fld 70, its sid, tag, ip and target) among the run's PRE-start rows --
  `before`: "field 70 e0 t0 ip249 := 125 ran after the trace was armed, before the warp (line N): the warp window's
  race, one window later -- the start's"; `after`: "field 70 e0 t0 ip475 := 2 ran before the warp (line N): the warp
  came after the window's late edge -- the start's". Any other field-70 row before the start stays START (a)'s to
  judge.

Then THE MOVIE'S SPAN (the reviews' A1 and B3: O2's FORBIDDEN line -- a backed write is A-FORBIDDEN, the run
uncovered; an unbacked one is FORBIDDEN F -- applied to FMV004, where the engine settles which is which: only a Confirm
opens the skip dialog, 0.2 #23, so nothing the FORK does can put a press, a skip dialog or its answer in the span).
The span is `(f502, f863]` -- AFTER the 166 e6 t1 ip502 row's frame (a page press decided on a stale 313 sample has a
`pre.frame` at or before it, 2.7) through the ip863 row's, both read by place at the side's own field of 166; a run
that never wrote both rows is uncovered already. Each of these makes the run UNCOVERED, A-MOVIE by the driver, each
reason opening with `MOVIE_SPAN` (set aside by VOID-ASYM, 1.3 `_void_ids`):
- **a press**: a `press` row whose `pre.frame` lies in the span -- "the movie span (frames f502-f863): the driver's
  press at frame F (why W)";
- **the skip dialog**: a `skip_seen` row (1.3: by text or by shape) or a `choice` row whose dialog is skip-shaped
  (`skip_answer` of its options, or `skip_shaped`) with its frame in the span -- "... a skip dialog at frame F, answered
  at its default (rule n)" when a press of the driver's in the span precedes it, else "... a skip dialog at frame F with
  no press of the driver's behind it: outside input the witness did not catch (only a Confirm opens it,
  FieldHUD.cs:275-285)" -- the instrument's either way, never the fork's (the claim review's movie-skip-unbacked
  mutant is registered as this, 11.3 B3);
- **unclocked**: fewer than two `clock` rows WITH a write time (`mtime` not None) in the span, or none 300 frames
  apart -- "... unclocked (N clock rows with a write time)" (the driver's loop starved for the whole span).
A `choice` row in the span whose dialog is NOT skip-shaped stays covered: that is a script's choice where stock has
none, answered by the net's default, and O8-MOVIE (a) FAILS it (5.3).

Then THE KNIGHT'S READINGS (the claim review's #3): a covered-candidate run whose 164 visit holds no `knight` `seat`
row, or no `start1` row, is UNCOVERED, A-KNIGHT by the driver, its reason opening with `KNIGHT_UNREAD` -- the hook read
no published sid 1 at that frame (an `observe_error` row named when one is there). NOT set aside by VOID-ASYM: a whole
side unread reads (b).

A drive VOID carries its V-class and `[place, sc, visit]` cell (2.9). The report lists every uncovered run's reasons
per side.

### 5.2 The cuts (per side, frozen places)
`cut_at_start` from 164's first `w` row (place 164: real 164 on S, 31256 on F; the four residue rows in 70 go to
`pre`); `cut_at_end` at the first `w`/`r` row in an end PLACE -- [55] on both sides, real 55 on both. Kept after the
cut: the epoch rows (the `e off fld 55` row the seam is read through) and any `c` rows of the route places (none
expected). A run that entered a real 164, 165 or 166 on F is VOID by rule 2 first (V19).

### 5.3 The checks, in order, each with the mutant that makes it fail (section 8 registers every one)
**All-run checks** (every run with a readable trace, judged even when COVER is short):
- **O8-FORBIDDEN** (O2's). Mutants: back-door-unbacked-F (164 e3 t2 ip243's row and rows in 31255, no step row explains
  them), talk-unbacked-both (164 e1 t3 ip308 `Bit[3851] := 1`, no press near the knight).
- **O8-VOID-ASYM** (O4's (a)-(d), `[place, sc, visit]`; `stop_on` [V19]; O8's `_void_ids` sets aside the `START_READ`
  and `MOVIE_SPAN` reasons, 1.3). Mutants: v19-one-F (a, c), v5-error-165-F (a: V5 game at [165, 1190, 2]), v14-one-S
  (a), wait-v8-one-S (a: V8 game at [164, 1190, 1]), wait-v11-game-one-F (a), v7-pinch-all-F (b: every F run V7 driver
  at [164, 1190, 1]), v13-prior-all-F (b), v13-loss-y-all-F (b), knight-unread-all-F (b: every F run A-KNIGHT -- not
  set aside); and the PASS cases v13-prior-one-F, v13-input-one-F, v7-pinch-one-S, v13-wait-deadline-one-F,
  wait-unpublished-one-S (V13 driver: the watch never published), back-door-e3-S (backed: A-FORBIDDEN),
  error-path-start-S (A-START), byte13-late-warp-all-F (VOID by COVER: the start read's A-START set aside by (b)),
  movie-stray-answered-all-S (VOID by COVER: the A-MOVIE reasons set aside by (b)).

**Then:** **O8-FROZEN**, **O8-COVER**. Mutants: predictions-changed; w164-beat-missing, t165-beat-missing (two S runs:
uncovered, VOID).

**Core checks** (over the covered runs):
- **O8-START** (O3's): (a) `pre` is exactly the FOUR residue rows; (b) the first `w` row in place 164 is `start_first`,
  raw; (c) the first Byte[13] row in place 164 is ip130 `:= 1` from old 1. Mutants: start-residue-three (byte 3's row
  missing), start-residue-315 (byte 2 0 -> 59: O7's entrance), start-first-missing (164's ip22 dropped), front-cut-write
  (F: 70 e0 t0 ip57 `Int16[9] := 643` before the start -- no raced pin's row). (A Byte[13] old 2 at ip130 never reaches
  (c): it is the late-edge start read's A-START, the run uncovered -- critique #2's point, byte13-late-warp-*.)
- **O8-NO-SC**: mutants sc-write-fork, sc-harness-poke-both.
- **O8-CHAIN** (`span_check` over bytes 2-3 from 342): exactly 4.3, in order, each from the last. Mutants:
  chain-dropped-fork (no 165 e2 t2 ip233 on F), chain-first-old-wrong (164 ip243's old 315: CHAIN alone),
  chain-back-door-site-both (164's 343 written at e3 t2 ip243, not e2's: the value right, the site wrong -- a key
  matched on its value alone would pass; re-registered with whatever else the render gives).
- **O8-RESIDUE**: mutant residue-after-start.
- **O8-WRITES (exact)**: the 23. Mutants: fork-drops-a-write (no 165 e2 t2 ip205 on F), writes-extra-symmetric (both:
  164 e2 t2 ip215, dead), forbidden-row-both (164 e7 t11 ip399), knight-row-missing-F -- each with PATTERN (b).
- **O8-NULL**, **O8-STABLE** (O1's, no noise). Mutants: NULL -- fork-drops-a-write; STABLE -- extra-key-one-F (one F run
  holds 164 e1 t3 ip627).
- **O8-LANDING** (O7's (a)-(d); its (e) is SEAM's), every covered run:
  - (a) every field-mode `w`/`c` row ran in its place's own field and stands in a route place;
  - (b) THE CROSSINGS: 164 e2 t2 ip243 (343) -> 165 e0 t0 ip22, 165 e2 t2 ip233 (344) -> 166 e0 t0 ip22, each the next
    field-mode `w` row at the next place's field; no row of the earlier place after;
  - (c) the last field-mode `w` row before the end cut is 166 e6 t1 ip863 (by place), and the run's `end` log row names
    55;
  - (d) the end cut is a raw `w` row 55 e0 t0 ip22 at 55.
  Built as O7's `landing_check` over COPIES of the covered runs whose F digests read `seams` [] and `seam_keys` {}
  (O7's (e) is the only reader of either: (a)-(d) stay single-sourced), its PASS detail's "(e) no seam" read as "(e):
  O8-SEAM's". Mutants: lands-real-165-covered ((a)(b), FORBIDDEN, WRITES), harness-after-exit165-both ((b) alone),
  last-place-harness-both ((c) alone), end-boundary-residue-both ((d) alone); the unit landing-e-dropped (one seam: O7's
  LANDING FAILS (e), O8's PASSES).
- **O8-SEAM** (decision 8; critique #3), every covered run:
  - (a) F: exactly ONE `Seam` in the run's digest, `(frm, donor, to, fields) == (member(166), 166, 55, [55])` -- zero
    FAILS ("no seam: the run never left the members"; never a vacuous pass, O2's `seam_check`'s defect), two FAIL;
  - (b) F: its `exit` row `(fld, sid, tag, ip, target, old, new) == (31258, 6, 1, 863, Int16[2], 344, 110)`;
  - (c) F: no seam key (`seam_keys` empty), and the comparison's `across_seam` and `seam_only` empty;
  - (d) both sides: the cut row (`cut_row`, O3's: the uncut trace's row at the cut line) is `w`, fld 55, don 55, e0 t0
    ip22 `Bit[191] := 0` -- REAL 55, never O1's 31205 (don 55: EffectiveFieldId(55) = 55);
  - (e) both sides: the last `w`/`r` row before the cut (`c`/`e` rows aside; `r["rows"]` keeps every one, 0.2 #20) is
    the 166 e6 t1 ip863 row at the side's own field of 166 -- nothing (a residue row, a harness row) between the exit
    and the landing (in game, O7's 163 -> 164 and O3's 31213 -> 64 had nothing between);
  - (f) S: no seam -- S has no members, so none can arise: said in the detail, never counted as a pass.
  `seam_problems(r, seam, members)` is pure and parameterised by the registration (the O3 fixture runs it, 8).
  Mutants: seam-zero-F ((a): the `e off` row renumbered to fld 31258), seam-two-F ((a): an `e` row stamped at real fld
  164 between 31257's and 31258's rows), seam-exit-wrong-F ((b): the exit row 31258 ip502 -- ip863 dropped; with CHAIN,
  WRITES, LANDING (c) as rendered), seam-key-F ((c): a `w` row at real fld 163 after ip863; with (a)(e), FORBIDDEN as
  rendered), cut-row-don-wrong-F ((d) alone: the cut row's don 31205), seam-residue-before-cut-F ((e) with RESIDUE: an
  `r` row at fld 31258 after ip863), cut-row-not-ip22-both ((d) with LANDING (d): 55's ip22 dropped, the cut at ip49).
- **O8-WALK** (THE PAIRED-WALK LAW over the four table steps), every covered run:
  - (a) per step (its donor, visit and index): exactly one `done` row, the last of its rows; its EVIDENCE -- a `walk`:
    its `to` sample in the side's field of the place, `control` true, within `tolerance` of `goal`, its `at_y.y` inside
    the step's `at_y`, and, with `wait_flag`, `wait_flag.read` True for the step's flag and value; a `trigger` with
    `to`: `landed` None OR the side's field of `to`'s place -- path A or path B, O6's rule (o6_steiner.py:2149, :2178;
    every door step of story-o6 was path A: 0.2 #22, the claim review's #2) --, and with `landed` None, the row's
    `landed_frame` set (S14b's walk-out record) and the run's next `visit` row at the side's field of `to`'s place; its
    `lost` read in the walk's field with a `y` -- a `lost` with no `y` FAILS "no height" here, before any `until_ok`
    (which RAISES on a y term with y None: the claim review's #10) --, satisfying the step's `until` (`until_ok` with
    that y) and inside -- or within `exit_slack` of -- the exit whose `to` is the step's (read from `to`: these triggers
    carry no `target`, O7's `walk_check` (a) raises KeyError on them); before it at most `interrupts` `interrupted` rows
    (none with a `door`) and at most `attempts` - 1 `failed` rows (none `landed`, none with a `door`);
  - (b) THE VISIT WINDOW (`visit_windows8`): per visit (164, 165), no `w` row from its first step row's `frame0` to its
    last done row's end (`lost.frame` read in the walk's field, else `flip_frame`, else `frame`; a `walk` row's
    `frame`) -- except the trigger's door's own tag-2 store SITES (the exit whose `to` is the step's: 164 e2 t2 ip243
    and its dead ip215; 165 e2 t2 ip205 and ip233), matched by SITE anywhere after that trigger step's FIRST `frame0`
    -- never bounded by the read `lost.frame`, which a starved read can put after the door's first store (it trails
    ExitField by 25 ticks or more: 0.2 #25, the driver review's #5) -- and 164 e1 t1 ip230 inside THE EXEMPT SPAN, and
    nowhere else;
  - (c) THE FIRST MOVES: per visit to a seeded place (164, 165), the first step row's route `basis` "prior", exactly one
    of the visit's rows carrying `basis_check`, its `angle` at most acos(`PRIOR_AGREE`) (16.3 deg).
  Mutants (each alone unless named): walk-no-step-both, walk-short-both (164 #0's done `to` 200 u from P1),
  walk-wrong-level-both (its `at_y.y` 13893: tri 98's level), walk-wait-unread-both (its `wait_flag.read` False),
  trigger-lost-low-both (164 #1's `lost.y` 11500), trigger-lost-no-y-both (its `lost` without `y`: "no height", never
  THROW), trigger-landed-wrong-both (165 #1's `landed` 164's field), trigger-landed-none-no-frame-both (164 #1's done row
  `landed` None AND `landed_frame` None), trigger-lost-in-e3-both (164 #1's loss inside 164.e3), walk-window-row-both
  ((b): 164 ip764's row stamped inside 164's window), door-row-before-step-both ((b): 164 e2 t2 ip243's row stamped
  inside step 0's window, before step 1's first `frame0`; ORDER (b) as rendered), knight-outside-span-both ((b), with
  ORDER (c)), basis-check-missing-both ((c)), basis-check-30deg-both ((c)), basis-cached-run3-S ((c): run 3's 164 #0
  route `basis` "cached" -- the per-run forget missed); PASS: walk-failed-once-164-both, trigger-failed-twice-164-both
  (two `failed` rows under `attempts` 3), interrupted-once-165-both, knight-in-failed-attempt-both, trigger-path-b-both
  (both doors' done rows `landed` the next field: path B), door-row-late-loss-both (164 e2 t2 ip243's row 30 ticks
  before a late-read `lost.frame`: exempt by site).
- **O8-ORDER** (decision 6; critique #1), every covered run's 164 visit (by place):
  - (a) exactly one `w` row 164 e1 t1 ip230 `Bit[3811] := 1`, at the side's own field of 164;
  - (b) its line precedes the chain row 164 e2 t2 ip243's;
  - (c) its frame lies in THE EXEMPT SPAN `[frame0 of step 0's FIRST row, frame0 of step 1's FIRST row)`.
  Mutants: knight-after-exit-both ((b); with PATTERN (b), LANDING (b) as rendered), knight-in-step1-both ((c), with
  WALK (b)), knight-twice-both ((a), PATTERN (b)), knight-at-real-164-F ((a); LANDING (a) as rendered),
  knight-row-missing-F ((a), WRITES, NULL, PATTERN (b), STATE); PASS: knight-fast-both (ip230 during step 0's walk,
  before P1), knight-slow-both (12 s into the wait), knight-in-failed-attempt-both (ip230 inside the failed first
  attempt's row: a done-row window would FAIL it -- the unit knight-span-done-row shows that).
- **O8-KNIGHT** (the seat; decision 6; critique #9), every covered run's 164 visit:
  - (a) its `seat` and `start1` rows -- COVER guarantees one of each (an unread one is the instrument's: A-KNIGHT, the
    run uncovered, 5.1; the claim review's #3) -- each the registered sid (1), each READ at the side's own field of 164
    (31256 on F: the reading's field, whatever poll wrote the row, 1.3);
  - (b) each within `tol` (30) of `seat` (-586, 3884): a reading OFF the seat is the only way KNIGHT fails.
  Mutants: knight-seat-off-F ((b): the F runs' seat at (-400, 3900)), knight-start1-moved-both ((b): start1 at (-586,
  3600)), knight-seat-real-164-F ((a): the row's field 164 on F); PASS: knight-unread-one-S (S 2 of 3: that run
  A-KNIGHT), knight-start1-path-b-both (each start1 row appended on a poll in 165, its field the 164 reading's); and
  knight-unread-all-F under VOID-ASYM (b) (above).
- **O8-MOVIE** (decision 7; critique #4), every covered run's 166 visit (by place):
  The span is 5.1's `(f502, f863]`. A press, a skip dialog (by text or shape) or an unclocked span there made the run
  uncovered (A-MOVIE: the driver's press, or outside input -- the dialog is press-only, never the fork's; the reviews'
  A1, B3), so over the covered runs:
  - (a) no `press` row whose `pre.frame`, and no `choice` row whose `frame`, lies in the span -- by COVER no press and
    no skip-shaped choice can; (a) re-checks that, and FAILS a `choice` row of any OTHER shape: a script's choice where
    stock has none, answered by the net's 166-scoped "No" row (2.1), is a finding the net must never hide;
  - (b) the `clock` rows inside the span WITH a write time (a None `mtime` is skipped: channel.py:1068-1071; COVER
    guarantees two, 300 frames apart): the movie's fps = their frame difference / their `mtime` difference; the span
    (f863 - f502) / fps >= `file_s` - `slack_s` (40.4 s) -- "the span at the run's fps", the rate measured inside the
    span itself: the check that can fail on a covered run;
  - (c) no `skip_seen` row in the span (by COVER; re-checked).
  Mutants: movie-script-choice-F ((a): every F run's span holds a three-line choice row, cursor on 0, the net's default
  taken), movie-short-F ((b): ip863 30 s after ip502 at the clocked rate); the unit movie-recheck ((a)(c) FAIL on a run
  the COVER code is bypassed for); PASS: movie-fps-60-both (2730 frames at 60: 45.5 s), movie-fps-31-both (1411 frames
  at 31), movie-clock-mtime-none-both (two clock rows' `mtime` None, enough others), movie-press-at-f502-both (a page
  press whose `pre.frame` IS f502: outside the half-open span), and, by COVER, movie-press-in-span-one-S (S 2 of 3:
  A-MOVIE, the driver's press), movie-stray-answered-one-S (S 2 of 3: A-MOVIE), movie-skip-unbacked-one-F (F 2 of 3:
  A-MOVIE, outside input), movie-skip-empty-prompt-one-S (S 2 of 3: A-MOVIE, the skip dialog read by its shape),
  movie-unclocked-one-S (S 2 of 3: A-MOVIE, one clock row in the span).
- **O8-PATTERN** (O7's `pattern_diff6`, `floating` []): (a) the `c` multiset empty; (b) each of the three visits'
  emitted sequences exactly 4.16's. Mutants: c-row-165-F ((a) alone), byte13-repeat-both ((b): a second 164 ip764 2 ->
  2, emitted same), byte208-order-swap-both ((b): ip380 before ip345 -- one target, two values: STATE (a) too,
  re-registered as rendered), visit-split-both.
- **O8-MASKED** (O2's). Mutant: masked-differs.
- **O8-STATE** (O7's): (a) each unmasked target's emitted history identical across covered runs, in order; (b) every
  covered run's live `end_state` == 4.9's; (c) for each `end_state_trace` target (Int16[2], Byte[8]), the run's last
  pre-cut row on its bytes is the registered site with the registered value, matched by PLACE at the side's own field
  (31258 on F). Mutants: end-state-differs ((b): one F run's live Bit[3811] 0), int16-2-live-race-both (live Int16[2]
  106: PASS -- never compared), byte8-live-race-both (live Byte[8] 125: PASS), int16-2-trace-end-F ((c) with RESIDUE: a
  harness Int16[2] row after ip863), byte8-trace-wrong-site-both ((c): ip502 dropped, Byte[8]'s last row ip255's 125 --
  with WRITES, PATTERN as rendered); the F-side unit state-c-by-place (31258's rows match; renumbered to fld 166 they
  do not).
- **O8-JOIN** (O1's). Mutant: join-failure (both: an extra row at 166 e6 t1 ip346).
- **O8-THROW** (in `run`).

**VERDICT**: O1's `verdict()`. A failed check outranks a void one: a V19 reads "NOT PROVEN: O8-VOID-ASYM".

### 5.4 Report-only (`report_extra`)
- **Scope**, five lines, each RENDERED from the predictions (`start_scoped`, `start_reads`, `carried`, `AFTER_RUN`,
  `seam`, `movie`, the table), never a literal:
  - *start dependence* -- "none in value or path: a raw warp into 164@342 at SC 1190 from New Game, the same on both
    sides. START-SCOPED olds only: 164 ip57 Int16[9] 643 -> 385 here, 385 -> 385 after the O1-O7 routes as driven; 164
    ip130 Byte[13] 1 -> 1 / 2 -> 1; 166 e6 t1 ip345 Byte[208] 0 -> 0 / 1 -> 0. Carried, not claimed (neither written
    nor read by a function the route runs; derived from the frozen O1-O7 keys): <the fifteen, raw and true>, party
    [Zidane] ([Steiner]). THE START READS: 166 ip255 read Byte[8] 125 and 164 ip130 read Byte[13] 1 in every covered
    run (a warp before 70's ip249 / after its ip475 is A-START, the run uncovered and named)";
  - *the end and the seam* -- "the arrival in REAL 55 on both sides; on F one seam, member(166) 31258 -> 55, its exit
    166 e6 t1 ip863 (O8-SEAM); the end state read live but Int16[2] and Byte[8], which 55's prologue rewrites at once
    (ip255 110 -> 106, ip342 0 -> 125): taken from the trace's last pre-cut writes, 166 e6 t1 ip863 (110) and ip502 (0)";
  - *the walks* -- "164 at the engine's radius 80 (step 0 at 80, step 1 at 64: no route at 66+, THE PINCH), 165 at 120;
    every step's arrival proven by its height (at_y, until y); the first moves on the exact prior basis, seeded afresh
    every run, each checked within 16.3 deg";
  - *the movie* -- "FMV004 played out: no press, no choice, no skip dialog after 166's ip502 through its ip863 in any
    covered run (a run with one is uncovered, A-MOVIE: the dialog is press-only); each run's span and rate";
  - *settings and engine* (O7's lines and VSync); *language* (P-TEXT3's line).
- **The walks, per run, per step**: the grant sample (frame, x, z, published y), the basis and `basis_check`, the
  clearance (and `unstick` when carried), the route record (legs, length, replans, waits, pushes, blockers, frozen,
  boxed, fps), `at_y` (band, y), the loss (frame, x, z, y), the landing and `flip_frame`, failed and interrupted rows.
- **THE KNIGHT, per run**: step 0's rows' frames, ip230's trace frame and line, THE EXEMPT SPAN, the wait (`frame0`,
  read frame, wall and game seconds, the samples that published the bit, its last value), the `seat` and `start1`
  readings (each with the poll that wrote it), any `observe_error` row.
- **THE PINCH, per run**: 164 #1's route record and its attempts, each stall classified -- rejected, blocker-sealed or
  slid (2.5; the rehearsal measures the holds: 7.2).
- **166, per run**: the pages pressed (mes, first and gone frames, dropped Confirms); the movie span (ip502 and ip863
  frames, the clock rows used and any skipped for a None `mtime`, fps, seconds); any press, choice or skip dialog in it,
  each with the A-MOVIE reason it made.
- **The seam, per F run**: the Seam (frm, to, fields), its exit row, the cut row and the frames between.
- **The pattern, per run**; **the end state** (live, and the raced pair's trace values beside their live reads);
  the run's render rate (the `rate` row); the session's end, the VOID reasons per side, masked counts, forbidden hits,
  the P-TEXT3 line, the re-runs held.

---

## 6. Offline check and preflight

### 6.1 `--offline-check` (the install and O4's build, read-only; reads `--predictions`, else the frozen file, else the DRAFT, and prints which)
- **O8-BUILD**: the base rule (every member's `.eb`, 7 languages, its donor's with only in-chain `Field()` literals
  remapped: "140 files"); `build_pins` over `route_build` -- `{"164": [[2, 2, 251, 165], [3, 2, 251, 163]], "165": [[2,
  2, 241, 166], [3, 2, 251, 164]], "166": []}` (each `[sid, tag, ip, the donor's literal]`; "166" LISTED with no site,
  so its member must equal it byte for byte: o5_hallway.py:1252-1255 -- the vacuity arises only when a member is
  omitted, as O7's BUILD_FIELDS omits 165 and 166: 0.2 #6); then THE RAW EXITS, `raw_exits = {"166": [[6, 1, 871,
  55]]}`: in every language the member's site decodes as `Field(55)` with 55 itself (no member's id), and the member's
  bytes equal the donor's (sha per language). Expected: "140 files, every language its own donor's; the route members'
  pins hold in 21 member files (3 route members x 7 languages): 31256 and 31257 differ from 164 and 165 only in their 2
  in-chain Field() operands each (N bytes), 31258 is 166 byte for byte with e6 t1 ip871 Field(55) raw; member(164)
  31256, member(165) 31257, member(166) 31258" (N from C0; the fork reader's `forkdiff7.out` read 4 bytes a file).
- **O8-KEYS**:
  - (a) O2's `keys_check` machinery on (the chain, the writes, `error_path` + `forbidden_sites` + `dead`,
    `start_first`): every key a store of its variable at `(sid, tag, ip)`, its `off`, its MANDATORY `op` the
    statement's, a compound value computed from its `prior`;
  - (b) `start_music` one writes key; THE START-SCOPED OLDS: `start_scoped`'s sites == `scoped_derivation8`'s, each
    `here.old` the start's, `after.run` "O1-O7", `after.source` present, `after.old` read off O7's frozen pattern;
  - (c) THE START READS: each a writes key whose target is the key's, no store of its target before it on the route,
    its `race` resolving by `race_site8` to the pinned field-70 store of its target with its `race_value`, its `edge`
    one of `before` / `after`;
  - (d) THE CARRIED VALUES: `carried8` (each segment agreeing with its own `end_state`) equal to the typed `values`, none
    in `end_state`, none stored or read by a function the route RUNS (`route_run_texts`);
  - (e) THE ROUTE PINS exactly (4.14) and THE SCANS (4.14);
  - (f) THE HEIGHTS: every region's `gate` == `height_gate` of its pinned tag-2 test AND that test's consuming jump
    (each door's `JMP_IFNOT` to its RET: the gate is where it FIRES); the knight's release, `{"y_ge": 8400}` --
    `height_gate` over e1 t1 ip178's B_GT and ip187's `JMP_IF` back to ip175 (the loop holds while the test holds, so
    the release is its negation: 0.2 #24; the claim review's #7) -- at or under `at_y`'s low end and equal to H25's
    `start`; his seat (-586, 3884: ip215's Walk operands, signed) and walk (1131.4 u over ip194-ip215) equal
    `seat_watch` and the cell's premises;
  - (g) THE RACED SET: `end_race8` over stock 55 from the arrival's values, to e0 t0's RET, == {Int16[2], Byte[8]} ==
    the `end_state_trace` keys, each trace site a writes or chain key with the registered value; and every other store
    site in stock 55 of an `end_state` target is UNREACHABLE on this arrival -- `reach8` with `{Map.Byte[24]: 1}` (55
    e0 t0 ip247's store on it) -- else FAIL naming the site (the claim review's #11: the live read lands after the
    first yield, 4.9) [as built after the review's #3 (11.4): `reach8` holds only the Map values no other 55 function
    stores (`end_map_held8`), e10 t1 ip568 / ip582 are then reachable -- THE ARRIVAL SCENE, `end_state_scene` exactly
    them, SC out of the live read -- and every candidate neither raced nor the scene's is read live];
  - (h) THE MOVIE AND THE SEAM: `movie.cinematic` / `movie.play` pinned (`Cinematic(0, 9, 1, 1)`, `Cinematic(2, 0, 0,
    0)`), `movie.from` / `movie.to` the ip502 write and the ip863 chain key; `seam.exit` the chain's last key and
    `seam.field` pinned `Field(55)`.
  Expected: "56 keys over 56 distinct sites, every op in its statement, 2 compound values computed from their priors
  (166 e6 t1 ip380 ++ after ip345; 164 e7 t11 ip434 ++ after ip399), none masked but start_first; start_music one writes
  key (164 ip130 from 1); 3 start-scoped olds, derived, after.run O1-O7, after.old from O7's frozen pattern (163 ip57
  385, 163 ip684 2, 159 e16 t1 ip648 1); 2 start reads (166 ip255 Byte[8] old 125, race 70 ip249 := 125, before; 164
  ip130 Byte[13] old 1, race 70 ip475 := 2, after); 15 carried values derived from 7 frozen segments (no end-state
  disagreement), equal to the typed ones, none in end_state, none stored or read by a function the route runs (164 e1
  t3, e7 t11, e7 t12 set aside: the knight's talk); N route pins equal; per field one DefinePlayerCharacter instanced,
  no party op, one key basis, no Map.Bit[144] store; 4 gates read (y > 12000, y < 6000, y > 15000, y < 11000); the
  knight released at y >= 8400 (ip187's loop), seated at (-586, 3884) after 1131.4u; the raced set {Int16[2], Byte[8]}
  from 55's e0 t0 to its RET; no other 55 store of an end_state target reachable at Map.Byte[24] 1 (e10 t1 ip568,
  ip582: case 3); FMV004's Cinematic pins; the seam's exit 166 e6 t1 ip863 and its Field(55)".
- **O8-TEXT**: O4's `text_check` on block 3, STRICT, then `route_mes` (4.14). Expected: "block 3: 7 byte-equal of 7;
  KNOWN-KIT-DEFECT 0, FAIL 0; mes 307, 308, 309, 311, 312, 313 [STNR], 56 'Env Play()'".
- **O8-CENSUS** (`store_census8`): every gEventGlobal store site of stock 164, 165 and 166 is in `writes`, `chain`, the
  noise mask, `start_first`, `error_path`, `forbidden_sites` or `dead` (O4's precedence); every function decodes; no
  unresolved store; THE INSTANCING at each field's route entrance (164@342, 165@343, 166@344) by `instanced_at8`; a
  shared entry run from an instanced one (`RunSharedScript`) accepted only when it holds no global store -- O6's
  `store_census6` "others" proof, WITHOUT O7's `store_census7` refusal of any `RunSharedScript` (166 e6 t1 ip489 runs
  the storeless e2: 0.2 #4); `live_shared` equal to what the scan finds; and EVERY `error_path` SITE REACHABLE from
  some arrival value (`reach8` with no known value: the claim review's #9 -- CENSUS's class membership alone could not
  tell an `error_path` site from a `dead` one). The counts are DERIVED and printed. Expected: "164: 25 (writes 6, chain
  1, masked 2, error 3, forbidden 7, dead 6, inert 0); 165: 18 (6, 1, 2, 3, 1, 5, 0); 166: 18 (8, 1, 2, 4, 0, 3, 0); 0
  unresolved; every error-path guard reachable (10 of 10; 164 and 165 ip97 dead behind ip57's 385); no entrance
  dispatch (every Init reachable); 166 e2 shared from e6 t1 ip489, storeless; 166 e1 not instanced, storeless".
- **O8-REGIONS** (`regions_problems8`): (a) every `exit` region's points are the first SetRegion of its (donor, entry)
  and every `scan_gateways` row of that entry is its (`to`, `entrance`); (b) instanced at the place's route entrance;
  every gateway row of the route fields and every region an entrance instances registered; (c) its `gate` is
  `height_gate` of its pinned tag 2's test and consuming jump (O7's `height_test` reads B_LT only and no jump: 164.e3
  and 165.e3 are B_GT; a flipped jump inverts the gate, the claim review's #7); no hazard, no dormant region, no
  hot-spot. Expected: "4 regions (4 exit: 164.e2 y > 12000, 164.e3 y < 6000, 165.e2 y > 15000,
  165.e3 y < 11000), 0 hot-spots, 4 gateway rows all registered; 166 none".
- **O8-GOALS** (`goals8`; height-aware throughout, decision 4(c), critique #6 -- never O2-O7's XZ-only proofs, whose
  `until_ok(until, x, z)` RAISES on a y term: 0.2 #7), per step:
  - (g0) THE BASE: the step through `step_of`; every key in `KNOWN_STEP_KEYS8` (an unknown key -- `hold`, `at_Y` --
    FAILS: `step_of` passes unknown keys silently, a table that drives without them is a check that cannot fail);
    `visits` a walk on the route; the goal on an open tri of the step's floor (its closures) >= the step's clearance
    from a wall; a route from `start` round `avoid` AT THE STEP'S CLEARANCE; `closed_tris` == `band_closures` of its
    band;
  - (g1') THE CLEARANCE: every step carries `clearance`; one under the place's `ENGINE_RADII` only where the plan at the
    radius fails (164 #1: none at 66/68/72/80 from P1, a route at 64); else at the radius (164 #0 80, 165's 120);
  - (g2') THE EXITS: every OTHER registered exit of the place is in the step's `avoid` UNLESS its gate holds on no open
    tri of the step's floor inside its polygon (a dead-level crossing: 164.e2 on 164 #0, 164.e3 on 164 #1, 165.e3 on
    165 #1); a trigger's own door (the exit whose `to` is the step's) is never avoided;
  - (g3') THE ARRIVAL'S HEIGHT (a walk with `at_y`): every point within `tolerance` of the goal on the step's floor
    stands on open tris whose published heights lie inside `at_y`, and every OTHER level of the stock mesh at the goal's
    XZ lies outside it (P1: tris 11 at 3961 and 98 at 13893 vs 53 at 8958) -- so "within tolerance, control held, at_y"
    proves the level;
  - (g4') THE TRIGGER'S HEIGHT (a trigger with a y-until): the goal stands inside its door's polygon (the ring of ears)
    on an open tri where the until holds; the planned route's FIRST sample where the door's gate holds inside its
    polygon also satisfies the until (the door fires where the evidence holds: 164 at (24.5, 2270.8) y 13008, 165 at
    (2419.6, 3130) y 15169); every sample inside ANOTHER exit's polygon stands where that exit's gate fails (164 #1
    through e3 at y ~9329/9528);
  - (g5') THE WAIT POINT (a walk with `wait_flag`): every point within `tolerance` of its goal lies at least
    `exit_slack` + the place's engine radius from every registered exit (P1: 335 from 164.e2, 293.5 from 164.e3) --
    the premise of the wait's field change being the game's (S21);
  - (g6') THE KNIGHT: `at_y`'s low end inside his release (`height_gate(ip178, ip187)` = `{"y_ge": 8400}`; 8800 >= 8400:
    a proven arrival proves T0 passed);
    the seat lies more than his planning disc (`ROUTE_BODY_MARGIN` + his published r: 252) off step 1's planned route
    (300.0), and his start (249, 4630) inside 152.5 of step 0's -- the reason step 0 carries `npcs` false, and |dy| >=
    400 between loop 1 and his level along it (the engine never pairs them);
  - (g7') THE PINCH WINDOW holds the least half-width point of 164 #1's plan ((1202, 4520), y 10695) and no planned
    sample of loop 1 (its y band excludes ~5600-5900).
  Expected: four step lines ("(164, 1190, 1) #0 walk wall 118 route 24 legs 6404u at 80 ...") and "(g2') 164.e2 dead on
  #0, 164.e3 dead on #1, 165.e3 dead on #1; (g3') P1's disc on tri 53's level only (y 8930-8980), others at 3961 and
  13893; 165's goal disc inside [11100, 11450]; (g4') 164 #1 fires e2 at (24.5, 2270.8) y 13008 > 12000, e3 crossed at y
  9329/9528 (dead); 165 #1 fires e2 at (2419.6, 3130) y 15169 > 15000, e3 crossed dead; (g5') P1 335u from 164.e2,
  293.5u from 164.e3; (g6') release 8400 <= 8800; seat 300.0u off #1 (> 252); start 152.5u off #0 (npcs false); (g7')
  the pinch (1202, 4520) y 10695 inside the window" (the numbers as the planner reads them at C1).

### 6.2 `--preflight` (the live install, read-only; ALL GREEN today -- nothing needs deploying)
O7's set (decision 8): **P-MANIFEST** (`o8_forks.json` members = the draft's members, `deployed` true), **P-DEPLOY**,
**P-EB** (20 x 7 live `.eb` = O4's build), **P-FLOOR** (twenty deployed walkmeshes = their donors', normalised: stock
165's `.bgi` does not round-trip byte-exact through BgiWalkmesh, 6376 -> 6374 B -- O7's P-FLOOR already reads it so),
**P-STOCK** (no mod folder overrides any of `stock_fields` [164, 165, 166, 55]), **P-TEXT3** (block 3, STRICT),
**P-RECOVERY** (4600), **P-DONOR** over the ROUTE donors [164, 165, 166] (each forked by exactly one ForkDonorPatch row,
its member's: lines 91-93), with a line naming O1's `31205 55` (line 42) as OUTSIDE the set -- 55 is the end, real on
both sides, and no O8 run can enter 31205 (raw `Field(55)`, no remap); O5-O7's call over route + `end_fields`
(o5_hallway.py:1446) would FAIL on that row today (the research's harness gap 8), **P-SETTINGS** (`SETTINGS8`: 32 keys, `[Graphics] VSync`
among them), **P-PAD**, **P-OVERRIDE** (2ce8887e), **P-ENGINE** (ba976242): 12 lines. **In game** (`capabilities`):
P-CAP, **P-OBJECTS** ("the engine publishes the field's objects (s89): 164's knight -- O8-KNIGHT's seat and step 1's npcs
plan read him"), P-LANG, **P-DONOR-LOG** over [164, 165, 166, 55], P-LAUNCH, P-PAD. `--preflight` must read all green
before any rehearsal; if not, the lead names the failing line and stops.

### 6.3 The fingerprint (per run, before and after)
O7's, unchanged: another session's deploy, a re-wired New Game or an engine rebuild mid-session is A-INSTALL.

### 6.4 `o8_forks.json`
```json
{"what": "O8's fork chain: O4's alxc disc-1 chain as deployed (31240-31259, FF9CustomMap). O8 starts in member(164) 31256 (at 342), runs 31257 and 31258 and ENDS on arrival in REAL 55 (at 110): 31258 is 166 byte for byte, its only Field() raw, so the chain's one seam (31258 -> 55) is declared, never a defect. Nothing is imported, built or deployed for O8.",
 "reuses": "studies/story-trace/o4_forks.json", "import": "O4's", "build": "O4's: C:/gd/_ns_playtest/o4/build",
 "deploy": "O4's", "mod_folder": "FF9CustomMap", "members": {"...": "..."}, "names": {"...": "..."},
 "route_members": {"31256": 164, "31257": 165, "31258": 166},
 "seam": {"from": 31258, "donor": 166, "to": 55, "why": "e6 t1 ip871 Field(55) raw in all 7 languages; MAPJUMP does no remap (DoEventCode.cs:1008-1030, HonoluluFieldMain.cs:444)"},
 "outside": {"31205": 55, "why": "O1's member(55) (ForkDonorPatch line 42): never entered by O8"},
 "text_blocks": {"3": ["...O4's..."]}, "deployed": true, "relaunch_needed": false,
 "relaunch_why": "nothing is deployed for O8; P-LAUNCH and P-DONOR-LOG read the launch",
 "global_side_effects": "O4's: O8 adds none", "known_defects": [], "revert": "O4's",
 "built": {"where": "C:/gd/_ns_playtest/o4/build (read-only)", "measured": "<C0: the route members' byte diffs per language>"},
 "verified": null}
```

---

## 7. Rehearsal plan (the lead runs these in game)

### 7.1 The stages (`o8_rehearse.py`: `run(g, field=None)`; `O8_STAGE=<name>` picks one by name)
Each traced stage: `O8.start_run` -- `reseed` (164, 165, 31256, 31257 forgotten), New Game, `wait_frames(30)`,
`storytrace(True)`, the raw warp; `segment_drive.drive(g, stage_pred, side, log, end_fields=..., observe=recorder,
forbid_live=True, witness=input_witness(g))` (the recorder wraps `o8_observe`, so the knight and the movie clock are
recorded in rehearsal as in the session); the trace to `rh_<stage>_<n>.jsonl`; the record into `o8_rehearsal.json`;
`end_run`. Only R-FULL's traces may define or change the keys, the start, the end state or the pattern; the staged
runs prove mechanics. F-SMOKE and F-PASS send NO `storytrace` verb; F-PASS calls `O8.reseed` before its warp. O7's
LADDER TAP (`_unstick_leg` and `_blocker_ahead`, each entry tied to the stalled hold it followed) and its grant scan
off the ring are reused unchanged. **No stage starts between 03:45 and 04:45 local** (the nightly gate's `-n 6` whole
file starves the game and the driver alike -- rate flips, late reads, the very timing artifacts the reviews' A1-A5
guard against: the driver review's #10): `o8_rehearse.run` refuses to start a stage then (a STOPPED HarnessError
naming the window), and the lead checks `date` before each launch.

| Stage | When | Warp | Ends in | Runs | What it settles |
|---|---|---|---|---|---|
| **R-FULL** (the go/no-go and the predictions) | stock | `warp 164 342 1190` | 55 | 2 | F1-F8, F10, F11, F14: both grants (sample, objects, published y), both first moves, every step (route, holds, slides, stalls, losses with y, landings, flips), THE KNIGHT (T0, ip230's frame, the wait's seconds, the seat rows), THE PINCH, the dead-level crossings, 166's pages, FMV004's span and rate, the 166 -> 55 crossing (ip863, then 55 ip22, nothing between), the cut, the 23 keys and 6 masked rows, the pattern, the end state (live, and Int16[2] / Byte[8] from the trace), the run time, the longest no-progress stretch, the render rate |
| **R-SPIRAL** | stock | `warp 164 342 1190` | 165 | 2 | F2, F5: 164's grant (y ~4780), the 'left' first move, step 0's `at_y`, THE KNIGHT (T0, ip230 at ~T0 + 140, the wait, the seat), step 1 through THE PINCH WINDOW -- every hold starting or ending in it, every ladder rung after one, the narrowest wall gap (`--rehearsal-report` measures it on stock 164, level-aware) -- e2's loss y (~13008), the landing 165 |
| R-SPIRAL165 (optional, by name) | stock | `warp 165 343 1190` (165's prologue takes ip130 from the window's 1: no error path) | 166 | 2 | F4: 165's grant (y ~10280), 'up+left' (<= 4 deg), step 0's `at_y`, e3's dead-level crossings with no loss, e2's loss y (~15169), the landing 166 |
| **R-FMV** | stock | `warp 166 344 1190` (166's K -1 takes ip119 from the window's 1; ip255 125 -> 125). A warp after 70's ip475 (Byte[13] 2) takes 166's LIVE ip97 (its ip57 stores -1) to window 56: V5 by the driver -- the stage records 166's Byte[13] old (the ip119 or ip97 row) and RE-RUNS such a V5 (70 ip475 among the pre rows, or a 166 e0 t0 ip97 row), at most twice, never counted against F3 (the driver review's #9) | 55 | 2 + 1 | F3: pages 307-313 under rule 7 (a dropped first Confirm recorded), no press after 313 closes until ip863, no skip dialog, the movie span ip502 -> ip863 (frames, the clocked rate, seconds), ui FieldHUD and the rate during it, 55's cut row, the live end-state reads; RUN 3 with `movie_poke`: ONE deliberate Confirm mid-movie -- the skip dialog as published (its prompt's form: text or empty), the net's No (one `choice` row), the movie RESUMED and played out (ip863, then 55: REACHED), no second dialog -- the No path proven in game (the driver review's #1; 0.2 #23) |
| **R-VOID** (by name; LAST) | stock | run 1 `warp 164 342 1190` with `flag_stop`; run 2 `warp 164 342 1190` with `pinch_stop`; run 3 `warp 166 344 1190` with `movie_stop` {"after_s": 15} (R-FMV's late-edge V5 re-run rule) | V13 | 3 | F9: each run V13 (the driver's), no direction hold and no press after the raise, the sends after it exactly F9's list, `end_run`'s warp FIRST (4600), then the title; run 3 is THE mid-FMV004 recovery, its stop frame after the ip502 row's (the report asserts it) |
| **F-SMOKE** (by name; NO trace) | any time | `warp 31256 342 1190`, `31257 343`, `31258 344` -- each `member(<donor>)` from the chain -- and their stock twins | -- | 6 warps | F12: each member loads at its entrance and SC, its published object sids EQUAL to its twin's after `smoke_s` (31258's mid-scene; `end_run` from a page or the scene) |
| **F-PASS** (by name; NO trace; before the freeze) | after F-SMOKE | `warp 31256 342 1190` | REAL 55 | 1 | F13: one F run through the whole route on the DRAFT (`forbid_live` False, `end_row_s` None): 31256's beats (the radius-80 pinch through EffectiveFieldId), the wait, 31257's, 31258's pages and FMV004 played out, the landing in REAL 55 (rule 1, never V19), no exception. It may only STOP the session; its record shapes no frozen value |

Default order without `O8_STAGE`: R-FULL, R-SPIRAL, R-FMV, R-VOID (the void stage last: a recovery that fails ends the
launch, and that failure is the finding). The stops are `o8_rehearse` overlays on a COPY of the stage's table (O7's
`stage_pred`), each raising a HarnessError on the driver's thread with the session's own method restored at once: no
direction hold and no press after it; the only sends after it are S21's `finally` `unwatch` (`flag_stop` only),
`collect_story`'s `storytrace 0` (segment_trace.py:722-729) and `end_run`'s recovery warp and ladder (the driver
review's #6). Each stop's message is FIXED text ("the rehearsal's stop mid-wait (flag_stop)", "... in the pinch
(pinch_stop)", "... mid-movie (movie_stop)") that never embeds a wrapped call's error text -- S21 swallows any
HarnessError holding "live samples" as its own timeout, so an embedded one could read as the game's V8; the stop must
read V13:
- **`flag_stop`** ("the rehearsal's stop mid-wait"): a wrapped `g.wait_for` raises on the first call whose `what` opens
  with "the flag wait" while the published place is 164 -- after S21's `g.watch`, so the stop exercises its `finally`
  `unwatch` -- never a timer;
- **`pinch_stop`** ("the rehearsal's stop in the pinch"): a wrapped `g.send` raises before the first DIRECTION hold
  sent while his published x, z AND y lie in THE PINCH WINDOW during 164 #1 (the log holds 164's one done step row);
  loop 1's pass under the same XZ never fires it;
- **`movie_stop`** ("the rehearsal's stop mid-movie"): raised from the recorder's observe on the first poll in place
  166 -- control off, ui FieldHUD, no window and no choice published -- at least `after_s` (15 s) after the poll that
  first saw the 166 e6 t1 ip502 row in the LIVE trace (`g.story_rows()`, read at most once a second while in 166) and
  with no ip863 row yet: keyed on the movie span's own opener, never on quiet -- the quiet stretch from 309's close to
  311 (anims 6998, 6982, 6990, a Walk, op_22(10), op_22(90), a teleport, a Walk, RunAnimation(6605): L166 ip340-454)
  runs ~6-10 s, too near any quiet threshold (the driver review's #7). FMV004 starts ~1.1 s after ip502 and runs 45.4
  s, so the stop lands ~14 s into it; `--rehearsal-report` FAILS F9 on a stop frame at or before the ip502 row's.
- **`movie_poke`** (R-FMV run 3 only; "the rehearsal's poke mid-movie"): from the recorder's observe, ONE Confirm on the
  first poll in place 166 -- control off, ui FieldHUD, no window and no choice published -- at least `after_s` (10 s)
  after the poll that first saw the ip502 row in the live trace: a `press` row (`why` "movie_poke") appended to the
  log, then nothing; the drive's rule 6 answers the skip dialog by its net. Never a stop: the run goes on to 55.
Estimates a run: R-FULL ~2.5 min, R-SPIRAL ~1 min, R-SPIRAL165 ~40 s, R-FMV ~1.5 min (each of 3), R-VOID ~1 min each,
F-SMOKE ~3 min in all, F-PASS ~2.5 min. The command: `py tools/play.py studies/story-trace/o8_rehearse.py --label o8-rh
--timeout 240`.

### 7.2 What every stage records
O7's record (grants with their objects, pages with `gone_frame`, the press evidence, the longest no-progress stretch,
the end state, `end_run`'s rows, THE WALKS -- every routed step's holds and samples -- THE LEVELS, the calibration record,
the ladder) plus, per run: **the render rate** (`g.rate().as_dict()` at the end and each route record's `fps`); **the
bases** (seeded, cached; every `basis_check`); **THE KNIGHT** (T0 -- the first ring sample at published y >= 8400 in
164 --, ip230's trace frame, the wait's `frame0`, read frame, wall and game seconds and published samples, the `seat`
and `start1` rows, and his published position on every poll in 164); **THE PINCH** (every hold starting or ending in
THE PINCH WINDOW: start, end, pressed direction, travel, slide, its samples `[frame, x, y, z]`; every ladder entry after
such a hold; each STALL there CLASSIFIED -- rejected (ticks ran, he moved nothing), blocker-sealed (a placed blocker's
disc closed the corridor, the replan found no route) or slid (a hold deflected under 0.35 of its travel): 2.5, the
driver review's #8; `--rehearsal-report` measures the narrowest wall gap a pinch hold's samples passed on stock 164,
level-aware, as O7's `foot_gap` did);
**the dead-level crossings** (each entry into a registered exit's polygon at a height where its gate fails: no loss);
**the movie** (the 313 press, the clock rows, the span at the clocked rate, ui and fps during it, any skip dialog --
its published prompt, lines, `selected` --, R-FMV run 3's poke: its press frame, the dialog, the `choice` row, the frame
the movie resumed at, the span; 166's Byte[13] old and any late-edge V5 re-run; R-VOID run 3's stop frame beside the
ip502 row's);
**the crossing** (166 ip863's frame, 55 ip22's frame, every row between); **the trace** through `trace_summary8` (the
start rows, the chain rows, each registered key present or absent, every unregistered key, the crossings, the emitted
rows per visit, any `c` row, the cut row, the residue, the masked counts, the join failures, the raced pair's last
pre-cut rows, both start reads' olds). `py studies/story-trace/o8_west_tower.py --rehearsal-report <run dir>` prints it.

### 7.3 The freeze checklist (each item needs its evidence; the run dirs go into `rehearsals`)
- **F1 (the grants).** 164's within 64 u of (2040, 3335) at published y 4780 +- 30; 165's within 64 u of (2055, 3411) at
  10280 +- 30 (else that step's `start` takes the measured point and O8-GOALS runs again). A grant on another level
  STOPS the freeze.
- **F2 (164 and the knight).** In every R-SPIRAL and R-FULL run: no probe pressed in 164 (`basis` "prior"), exactly one
  `basis_check`, within 16.3 deg (expect ~0); step 0 done within its attempts, its end within 45 u of P1 at published y
  in [8800, 9150]; no loss on the dead-level e2 crossings; the wait read in every run (its seconds into
  `rehearsed.wait_s`, the longest; the bit published on the wait's samples); ip230 inside THE EXEMPT SPAN and before
  ip243; the `seat` and `start1` rows within 30 u of (-586, 3884) in every run -- a miss or an unread row STOPS the
  freeze (re-derive the seat, or the hook); `wait_flag.timeout_s` = max(15, 3 x the longest wait).
- **F3 (166 and the movie).** In every R-FMV run 1-2 and R-FULL run: the six pages seen and pressed (a dropped first
  Confirm recorded); no press after 313 until ip863; no skip dialog; ip255 before ip345; the span recorded (the shortest
  into `rehearsed.movie_span_s`), at least `file_s` - `slack_s`; ui FieldHUD throughout, the rate during it recorded.
  R-FMV RUN 3 (`movie_poke`): exactly one poke press after the ip502 row, exactly one skip dialog (by text or by shape;
  its prompt's published form recorded -- empty or not, the net row that answered it named), one net `choice` row at
  the default (No), no second dialog, the movie RESUMED and played out (ip863, then 55: REACHED, no V-class), its span
  at least `file_s` - `slack_s`; else STOP: the net's No path is redesigned before any session (a stray dialog that
  does not resume would cost its run a game-class V14 -- the driver review's #1). A late-edge V5 in any R-FMV run (70
  ip475 among the pre rows, or a 166 ip97 row) is re-run and never counted here (the driver review's #9).
- **F4 (165).** In every run that reaches it (R-FULL; R-SPIRAL165): one `basis_check` <= 16.3 deg (expect <= 4); step
  0's `at_y`; step 1's loss in 165.e2 at y > 15000 (expect 15169); no loss on the dead-level e3 crossings.
- **F5 (THE PINCH: the go/no-go).** GO when, in every R-SPIRAL and R-FULL run, 164 #1 is done within its attempts with
  no V7 AND no ladder rung (wait, push, blocker, frozen, boxed) followed a hold that STARTED OR ENDED in THE PINCH WINDOW
  (slides allowed; a rung after a hold wholly elsewhere is recorded, never judged); the narrowest gap recorded
  (`rehearsed.narrowest_pinch`; the fake's 12 is checked against it); every stall in the window CLASSIFIED --
  rejected, blocker-sealed or slid (2.5). NO-GO: the ladder of 2.5 -- `unstick: false` + `npcs: false` on 164 #1 and
  R-SPIRAL again, its outcome predicted from the classification (it can help blocker-sealed stalls only); still NO-GO
  -> the owner, the classification first (the only owner decision O8 can meet).
- **F6 (keys and pattern).** Per R-FULL run exactly the 23 keys and the 6 masked rows; no error-path, dead or forbidden
  row; the four residue rows and none after; 164's first `w` row ip22 and its first Byte[13] row ip130 from old 1; every
  visit's sequence exactly 4.16's (9 / 9 / 11), no `c` row; the cut 55 e0 t0 ip22; the two runs key for key and tuple
  for tuple identical (frames aside); any difference explained at the byte level before the freeze.
- **F7 (end state).** Every R-FULL `end_state` (live, without the raced pair) equals 4.9; the trace's last pre-cut
  Int16[2] row is 166 ip863 = 110 and Byte[8]'s ip502 = 0; the live reads recorded (expect 106 / 125, or 110 / 0 on a
  fast read: never compared).
- **F8 (budgets).** `run_s` = 2 x the slowest R-FULL; `run_min_s` = 1.25 x the median + the longest measured recovery
  (R-VOID's, R-FULL's from 55); `session_s` = 8 x the median + 1800; `no_progress_s` = max(60, 3 x the longest
  no-progress stretch of any traced stage -- FMV004's, expect ~150), its stretch into `rehearsed.stretch_s`; `settle_s`
  1.0; `end_row_s` 10; each step's longest measured route wall time into `rehearsed.steps_s` (report and `run_s`'s
  evidence only: no step `timeout_s` is sized, route_to bounds no walk with it -- 0.2 #12, the driver review's #11).
- **F9 (recovery).** R-VOID: each of the three stops V13 by the driver with its FIXED message; NO DIRECTION HOLD AND NO
  PRESS after the raise, the sends after it exactly S21's `unwatch` (run 1 only), `collect_story`'s `storytrace 0` and
  `end_run`'s recovery warp and ladder (the driver review's #6: the old wording "no send" contradicted all three); run
  3's stop frame after the ip502 row's; `recover-warp` 4600, then the title; R-FULL's `end_run` from REAL 55 reaches the
  title.
- **F10 (settings and launch).** P-SETTINGS (with `[Graphics] VSync` "1"), P-PAD, P-OVERRIDE, P-ENGINE, P-LAUNCH,
  P-DONOR-LOG (164, 165, 166, 55) pass on the rehearsal launch; its fingerprinted settings and engine equal 4.13's; no
  stage of it started between 03:45 and 04:45 local (the nightly gate: the driver review's #10).
- **F11 (the input witness).** No `input` row in any run.
- **F12 (F-SMOKE).** The three members load as their twins.
- **F13 (F-PASS: may only STOP the session).** Reached REAL 55 with no throw and no V-class; anything else is a FINDING
  written into PLAN.md first.
- **F14 (render rates).** Every run's measured rate recorded; the set seen goes into `rehearsal_fps`. A rate no stage
  met is named in PLAN.md as unexercised (60 fps for any O-segment walk so far) -- the game picks its rate; nothing
  forces one.

Then `--freeze` (v1; the lead's only). `freeze_problems` refuses (pure but for the live engine read, the stock 55
script `end_race8` walks and the frozen O1-O7 files, each a seam its test fills):
- no `witness`; a table step carrying a rehearsal overlay (`REHEARSAL_OVERLAYS8`, `movie_poke` among them), a typed
  `stale_slack`, or a key outside `KNOWN_STEP_KEYS8`; any step without `clearance`; `choices` other than exactly 2.1's
  two net rows;
- 164 #0 without `at_y`, `wait_flag`, "164.e3" in `avoid`, `basis` "prior" and `npcs` false; 164 #1 without an `until`
  with a `y_gt` term, `to` 165 and `clearance` 64 (or, after F5's fallback, with `unstick` false AND `npcs` false);
  165 #0 without "165.e3" in `avoid` and `at_y`; 165 #1 without a `y_gt` until and `to` 166;
- `side_ends` not exactly {S: [55], F: [55]} or failing `side_ends_of`; `members` not O4's twenty (`chain_from_campaign`);
  any O1 id (31200-31219) among `members`, `side_ends` or `route`;
- a non-empty `battles`, `naming`, `start_dependent`, `inert` or `pattern.floating`; a `movies` key (FMV004 is played
  out: decision 7);
- a raced target (`end_race8`'s set) in `end_state`, or `end_state_trace`'s targets not that set; a carried target in
  `end_state`, or a `carried` that differs from `carried8`; a `start_scoped` whose sites are not `scoped_derivation8`'s;
  a `start_reads` entry without `race`, `race_value` and `edge`, or whose race `race_site8` does not resolve; no
  `seat_watch`, `movie` or `seam`;
- `rehearsed` missing any of `stretch_s`, `wait_s`, `steps_s`, `movie_span_s`, `narrowest_pinch`; `no_progress_s` under
  2 x `rehearsed.stretch_s`; a `wait_flag.timeout_s` under max(15, 3 x `rehearsed.wait_s`); `rehearsed.movie_span_s`
  under `file_s` - `slack_s`;
- `settings` without `[Graphics] VSync` "1"; an empty `rehearsals` or `rehearsal_fps`; an `engine` that is not the live
  DLLs'; an existing file at the predictions path.

### 7.4 After the freeze: the session (the lead)
G1: `--preflight` all green on the session's launch. G2: unattended, hands off, NEVER started between 03:45 and 04:45
local (the nightly's `-n 6` starves the game and the driver: the driver review's #10; check `date`): `py tools/play.py
studies/story-trace/o8_west_tower.py --label story-o8 --timeout 240`. Copy the rehearsal and session run dirs into the
MAIN repo's `C:\gd\Dream-World-IX\.harness-runs\` before any gate reads them (every archive path in code is the main
repo's). Then one `harness_tests.py whole` and one `segment_regress.py --pytest-junit` on its receipt; O8's dry run
reads predictions through `frozen_through(8)`.

---

## 8. The dry run (`o8_dryrun.py`: synthetic sessions through `O8.analyse`)

Built like `o7_dryrun.py`: its own `render` (O7's, with O8's start values -- SC 1190, FieldEntrance 342, Byte[13] 1,
Int16[9] 643, Int16[11] -1, Byte[14] 0, Byte[8] 125, every other target 0 -- and the sink's per-site rule), O3's event
helpers, O5's `at(frame)` anchors and store options, and O3's EXACT `case()` (every check a case does not name must read
PASS; a COVER-VOID case expects every core check VOID; the multi-clause checks register the clause the detail names).
EVERY GLOB IS CLOSED AT ITS SEGMENT: the dry run reads the study's predictions files only through
`o7_dryrun.frozen_through(8)` (rungs and O1-O8; a later freeze cannot move its output, which G45 compares -- the trap
that failed O6's G36 when O7 froze). Every case reads freeze-time values -- budgets, `rehearsals`, `rehearsal_fps`,
`rehearsed`, the steps' `start` -- from the predictions it is given: C2 and G45 run every case on the draft (or the
frozen file) AND on `as_if_frozen(draft)` (every budget x1.5, `rehearsals` and `rehearsal_fps` named, `rehearsed`
filled with plausible values, each step's `start` moved 20 u), N/N each. No case pins a value the lead's in-game steps
change.
- **Real store sites** (every field row joins): 4.3-4.6's and 55's post-cut prologue.
- **A base run**: `arm` (fld 70); the four residue rows; visit 1's 9 rows (164: step 0's walk row `done` with its `to`
  at (1340, 2250) control true, `at_y` {[8800, 9150], 8958}, `wait_flag` read True at a frame after ip230's, its route
  `basis` "prior" and a `basis_check` (angle 0.4), `wait_flag.published` 40; ip230 inside it; the trigger row `done`
  on PATH A -- `lost` (24.5, 2270.8, y 13008) in 164's field, `landed` None, S14b's `flip_frame` with `flip_late` True
  and `landed_frame` --, then the `visit` row at 165 / 31257: every in-game door step of story-o6 was path A, 0.2 #22);
  the knight's `seat` and `start1` rows at (-586, 3884); visit 2's 9 (165: the walk with `at_y` 11251, the trigger on
  path A with `lost` (2419.6, 3130, y 15169), then the `visit` row at 166 / 31258); visit 3's 11 (166: six page press
  rows, the clock rows every 30 frames across the movie at 31 fps, each with an `mtime`, 1411 frames from ip502 to
  ip863); 55's ip22 (the cut) and its post-cut rows (ip49, 57, 119, 138, 200, 255 := 106, 342 := 125); `off` (fld 55);
  the `rate` row. 166 ip255 reads old 125, 164 ip130 old 1. On F the members' ids and one seam.

| Case | Want |
|---|---|
| null-pair | PROVEN |
| fork-drops-a-write (no 165 e2 t2 ip205 on F) | NOT PROVEN (WRITES F, NULL F, STATE F, PATTERN F (b)) |
| knight-row-missing-F (every F run: the wait read, no ip230 row) | NOT PROVEN (WRITES F, NULL F, ORDER F (a), PATTERN F (b), STATE F) |
| knight-after-exit-both / knight-in-step1-both / knight-twice-both / knight-at-real-164-F | NOT PROVEN (ORDER F (b) + PATTERN F (b), LANDING F (b) / ORDER F (c), WALK F (b) / ORDER F (a), PATTERN F (b) / ORDER F (a), LANDING F (a)) -- each re-registered as rendered |
| knight-fast-both / knight-slow-both / knight-in-failed-attempt-both | PROVEN |
| knight-seat-off-F / knight-start1-moved-both / knight-seat-real-164-F | NOT PROVEN (KNIGHT F (b) / (b) / (a)) |
| knight-unread-one-S (one S run: no `seat` row) / knight-start1-path-b-both (each start1 row written on a poll in 165, its field the 164 reading's) | PROVEN (S 2 of 3; that run A-KNIGHT, led by `KNIGHT_UNREAD`) / PROVEN |
| knight-unread-all-F (every F run: no `start1` row) | NOT PROVEN (VOID-ASYM F (b): A-KNIGHT is not set aside; COVER V) |
| wait-v8-one-S / wait-v11-game-one-F | NOT PROVEN (VOID-ASYM F (a)) each |
| wait-unpublished-one-S (one S run: V13 driver, "never published", `published` 0) | PROVEN (S 2 of 3) |
| v13-wait-deadline-one-F | PROVEN (F 2 of 3) |
| chain-dropped-fork (no 165 e2 t2 ip233 on F) | NOT PROVEN (CHAIN F, LANDING F (b), WRITES F, NULL F, STATE F, PATTERN F (b)) |
| chain-first-old-wrong (both: 164 ip243's old 315) | NOT PROVEN (CHAIN F alone) |
| chain-back-door-site-both | NOT PROVEN (CHAIN F, WRITES F, PATTERN F (b) -- re-registered as rendered) |
| start-residue-three / start-residue-315 / start-first-missing / front-cut-write | NOT PROVEN (START F (a) / (a) / (b), PATTERN F (b) as rendered / (a)) |
| error-path-start-S (one S run: 164 ip607 window 56, V5 driver [164, 1190, 1]) | PROVEN (S 2 of 3); A-START |
| byte8-early-warp-one-F (one F run: 166 ip255 reads old 0) | PROVEN (F 2 of 3); A-START, its reason "before its e0 t0 ip249", never PATTERN |
| byte8-early-warp-all-F / byte13-late-warp-all-F | VOID (COVER V; VOID-ASYM P) -- the start's problem on a whole side, never NOT PROVEN |
| byte13-late-warp-one-F (one F run: 164 ip130 reads old 2) | PROVEN (F 2 of 3); A-START, its reason "after its e0 t0 ip475" (O7's `race_site` would name 70 ip130: the unit race-site8 shows it) |
| byte8-race-armed-one-F / byte13-race-armed-one-F (70 ip249 / 70 ip475 among the pre-start rows) | PROVEN (F 2 of 3); A-START (the raced row's branch); NOT PROVEN (START F (a)) with `race_site8` neutralised |
| byte13-explained-F (one F run: a harness `r` row on byte 13 after the start, then 164 ip130 old 2) | NOT PROVEN (START F (c), RESIDUE F) -- an earlier row explains the old: the run's own, never the start's |
| v5-error-165-F (one F run: 165 ip687, V5 game [165, 1190, 2]) | NOT PROVEN (VOID-ASYM F (a)) |
| residue-after-start (F: an `r` row on byte 300) | NOT PROVEN (RESIDUE F) |
| writes-extra-symmetric (both: 164 e2 t2 ip215) / forbidden-row-both (both: 164 e7 t11 ip399) / talk-unbacked-both (both: 164 e1 t3 ip308) | NOT PROVEN (WRITES F, PATTERN F (b); NULL P / and FORBIDDEN F / and FORBIDDEN F) |
| extra-key-one-F (one F run: 164 e1 t3 ip627) | NOT PROVEN (STABLE F, WRITES F, STATE F, PATTERN F (b), FORBIDDEN F; NULL P) |
| sc-write-fork / sc-harness-poke-both | NOT PROVEN (NO-SC F, ...) / (NO-SC F alone) |
| c-row-165-F / byte13-repeat-both / byte208-order-swap-both / visit-split-both | NOT PROVEN (PATTERN F (a) alone) / (PATTERN F (b) alone) / (PATTERN F (b), STATE F (a)) / (PATTERN F (b)) |
| lands-real-165-covered (every F run: 165's rows at fld 165) | NOT PROVEN (LANDING F (a)(b), FORBIDDEN F, WRITES F -- as rendered) |
| harness-after-exit165-both / last-place-harness-both / end-boundary-residue-both | NOT PROVEN (LANDING F (b) / (c) / (d) alone) |
| end-row-missing-one-S | PROVEN (S 2 of 3); A-NOEND |
| v19-one-F (one F run VOID V19 at [166, 1190, 2]) | NOT PROVEN (VOID-ASYM F (a)(c); FORBIDDEN as rendered) |
| back-door-e3-S (one S run: the trigger V11 driver at [164, 1190, 1], `landed` 163, 164 e3 t2 ip243 and rows in 163, backed) | PROVEN (S 2 of 3); A-FORBIDDEN |
| back-door-unbacked-F | NOT PROVEN (FORBIDDEN F + co-failures as rendered) |
| back-door-165-S (one S run: 165 e3 t2 ip243, then 164 out of order: V11 driver on the walked row) | PROVEN (S 2 of 3) |
| v7-pinch-one-S / v7-pinch-all-F | PROVEN (S 2 of 3) / NOT PROVEN (VOID-ASYM F (b); COVER V) |
| v13-prior-one-F / v13-prior-all-F / v13-loss-y-one-F / v13-loss-y-all-F | PROVEN / NOT PROVEN (VOID-ASYM F (b)) / PROVEN / NOT PROVEN (VOID-ASYM F (b)) |
| v13-input-one-F / v14-one-S | PROVEN (F 2 of 3) / NOT PROVEN (VOID-ASYM F (a)) |
| seam-zero-F / seam-two-F / seam-exit-wrong-F / seam-key-F | NOT PROVEN (SEAM F (a) / (a) / (b) / (c) -- each with its co-failures as rendered) |
| cut-row-don-wrong-F / seam-residue-before-cut-F / cut-row-not-ip22-both | NOT PROVEN (SEAM F (d) alone / SEAM F (e), RESIDUE F / SEAM F (d), LANDING F (d)) |
| walk-* (5.3's fifteen WALK mutants: (a)'s nine, (b)'s three, (c)'s three) | NOT PROVEN (WALK F, the clause named; trigger-lost-no-y-both "no height", never THROW) |
| walk-failed-once-164-both / trigger-failed-twice-164-both / interrupted-once-165-both / trigger-path-b-both / door-row-late-loss-both | PROVEN |
| movie-script-choice-F / movie-short-F | NOT PROVEN (MOVIE F (a) / (b)) |
| movie-press-in-span-one-S / movie-stray-answered-one-S / movie-skip-unbacked-one-F / movie-skip-empty-prompt-one-S / movie-unclocked-one-S | PROVEN (2 of 3 on its side each; that run A-MOVIE by the driver, its reason led by `MOVIE_SPAN`: the press / the answered dialog / "outside input" / the dialog read by its SHAPE / "unclocked") |
| movie-stray-answered-all-S | VOID (COVER V; VOID-ASYM P: the `MOVIE_SPAN` reasons set aside) |
| movie-fps-60-both / movie-fps-31-both / movie-clock-mtime-none-both / movie-press-at-f502-both | PROVEN |
| w164-beat-missing / t165-beat-missing (two S runs) | VOID (COVER V; VOID-ASYM P) |
| end-cut (S: rows in 55 past the end) | PROVEN |
| end-state-differs / int16-2-live-race-both / byte8-live-race-both / int16-2-trace-end-F / byte8-trace-wrong-site-both | NOT PROVEN (STATE F (b)) / PROVEN / PROVEN / NOT PROVEN (STATE F (c), RESIDUE F) / NOT PROVEN (STATE F (c) + as rendered) |
| masked-differs / join-failure | NOT PROVEN (MASKED F, PATTERN F (b)) / (JOIN F alone) |
| mismatched / no-start-row | PROVEN; that run A-MISMATCH / A-NOSTART |
| trace-without-off / install-changed / predictions-changed | VOID / VOID / NOT PROVEN (FROZEN F) |

A want the code cannot hold is explained at the byte level and re-registered, never loosened (O3-O7's rule).

**THE STORY-O3 SEAM FIXTURE** (critique #3: the new seam, landing and raced-state code tried on a REAL traced fork
seam before the freeze; registered cases, counted in N). `C:\gd\Dream-World-IX\.harness-runs\20261001-095552-story-o3`
(the MAIN repo's archive, read-only; missing FAILS the dry run, never skips: `_missing()`'s `o3s`), read by O3's own
`read_session` with O3's FROZEN `o3_predictions_v1.json`:
- **o3-seam-F**: every covered F run through `seam_problems(r, seam3, members3)`, `seam3` READ off O3's frozen chain
  (its last key, member(63) 31213 e4 t1 ip820 `Int16[2]` 0 -> 100; `to` 64; `fields` [64]) -> PASS: one seam a run,
  31213 -> 64, its exit ip820, the cut row 64 e0 t0 ip22 at don 64, nothing between (story-o3: three frames, the `e off
  fld 64` row closing).
- **o3-landing**: O8's LANDING over a spec built from O3's frozen chain the way `_landing` builds O8's, each place's
  entry row read off the stock bytes -- 62's first store is ip26, not ip22 (0.2 #14) -- over field-mode rows (62/63's
  battle rows are another mode) -> PASS.
- **o3-state-c**, stated up front (the claim review's #11; 0.2 #26): `end_race8` over stock 64 from story-o3's arrival
  values (SC 1155, Int16[2] 100 -- 64's SWITCHEX default --, Byte[8] 125 from 63 e14 t1 ip805, the rest of O3's frozen
  writes over the raw start) is EMPTY -- every store of 64 e0 t0 to its RET (ip1053) is the value held -- which
  story-o3's live end state agrees with (Int16[2] 100, Byte[8] 125, read and compared by O3-STATE). So the derivation
  alone would leave STATE (c) nothing to judge: the fixture asserts the EMPTY set (a non-empty one FAILS it), then runs
  STATE (c) over a FIXTURE registration, typed in the dry run as the check's input (never derived, never a claim of
  O3's): `{"Global.Int16[2]": {"value": 100, "site": {"place": 63, "sid": 4, "tag": 1, "ip": 820}},
  "Global.Byte[8]": {"value": 125, "site": {"place": 63, "sid": 14, "tag": 1, "ip": 805}}}` -> PASS on every covered F
  run, by place (member(63) 31213).
- Mutants, each FAIL by name: o3-seam-zero (the `e off` row renumbered to fld 31213: (a)), o3-seam-exit-moved (ip820's
  row dropped: (b)), o3-cut-don (the cut row's don renumbered: (d)), o3-landing-entry-ip22 (62's entry read as ip22:
  LANDING (b) -- the reason the spec reads entries off the bytes), o3-state-c-renumbered (the F runs' 63 rows at fld 63:
  STATE (c) by place), o3-race-arrival-byte8-0 (the arrival's Byte[8] 0: `end_race8` -> {Byte[8]}, the empty-set
  assertion FAILS -- the derivation is live).
The synthetic uncut O8 F traces of the case table (seam-residue-before-cut-F: an extra `r` row before 55 ip22;
seam-zero-F) are the critic's second half.

Units (no session): **step-of-o8** (S20-S22's refusals; the draft's steps round-trip EXACTLY; every frozen predictions
file through `frozen_through(8)` passes unchanged); **until-ok-y** (the y axis; the raise; every key checked before the
None rule; x None False with x/z terms only); **walk-kw-unstick**; **wait-both-clocks** (S21's run-out rule on a stub
clock: the game's at a quarter rate; no readable clock; the deadline); **instanced-at8** (164@342 -> {object 1, 7;
region 2, 3}; 165@343 -> {code 1; object 7; region 2, 3}; 166@344 -> {object 3, 5, 6}); **talk-reach** (164: e1 t3, e7
t11, e7 t12; 165, 166: none; a target a non-talk function also calls stays in); **band-closures** (93 / 99 / 64 / 16 on
the stock meshes, 0 XZ self-overlaps in each band; a bound moved 1000 changes the count); **height-gate** (the four
gates and the knight's release `{"y_ge": 8400}` off the pinned tests AND jumps; a mutated constant changes it; a door's
ip51 as `JMP_IF` inverts its gate -- 164.e2 `{"y_le": 12000}` --; the knight's ip187 as `JMP_IFNOT` makes the release
`{"y_lt": 8400}`; another shape None); **end-race** (stock 55 -> {Int16[2], Byte[8]}, the walk running through ip387's
yield to the RET at ip565; a synthetic listing with a post-yield `Byte[13] := 9` behind a test true on the arrival's
values -> {Int16[2], Byte[8], Byte[13]}: the tail counts; stock 64 from story-o3's arrival values -> {}); **reach8** (55
e10 t1 ip568 / ip582 unreachable at `Map.Byte[24]` 1, reachable at 3; 164 and 165 e0 t0 ip97 unreachable from any
arrival value, 166's reachable; 164 e2 t2 ip215 unreachable; a revisit loop terminates); **race-site8** (both races
resolve; `race_value` 2 at ip249 -> None; O7's `race_site` on 164 ip130 -> (70, 0, 0, 130): why O8 types its races);
**scoped-derivation8** (exactly 164 ip57, 164 ip130, 166 e6 t1 ip345); **carried-derivation8** (the fifteen over the
repo's seven frozen files, Bit[3796] among them, no segment disagreeing with its own `end_state`); **exempt-span** (from
step 0's FIRST row's frame0 to step 1's FIRST row's frame0; a failed first attempt inside it); **knight-span-done-row**
(a done-row window FAILS knight-in-failed-attempt; the span PASSES it -- critique #1's scenario); **visit-windows8**
(doors from `to`, their tag-2 SITES exempt by site after the trigger's first `frame0`, a row before it not; ip230 exempt
only inside the span); **knight-watch** (cached by place: 31256 reads as 164; the seat off the ring at the wait's frame,
start1 off the poll of step 1's frame0; PATH B -- the step-1 row first seen on a poll in 30861 / 31257 -- and a LOAD
poll (fid -1) each still write start1, its field the reading's; the cache kept until both rows; the sid unpublished: no
rows; an injected exception: one `observe_error` row, no raise; break: a row a poll, or rows gated on the poll's place);
**movie-clock** (rows every `clock_every` frames in 166 only, an `mtime` None kept on the row; one `skip_seen` an
opening, by text AND by shape -- a prompt published empty, a localized one --; an injected exception: one
`observe_error` row, no raise); **movie-span** (the clocked rate over rows with a write time; one such row -> unclocked;
the half-open span: a press at f502 outside); **movie-recheck** (MOVIE (a)(c) FAIL on a run the COVER code is bypassed
for); **void-ids** (`START_READ` and `MOVIE_SPAN` reasons set aside, `KNIGHT_UNREAD` not); **seam-problems** (synthetic:
PASS, and each clause's FAIL); **landing-e-dropped** (a seam run: O7's LANDING FAILS (e), O8's PASSES);
**state-c-by-place** (two targets: 31258's rows match, renumbered to fld 166 they do not); **render** (the base run: 29
`w` rows before the cut, no `c` row; the same events through the FakeGame's H13 knob give the same sequence);
**pattern**; **trace-summary** (cut at end places; given end FIELDS on F, not cut -- the mutant); **why-void** (both
reads and both branches, each reason led by `START_READ`; none at 125 / 1; none when an earlier row touched the target;
A-MOVIE's four reasons, each led by `MOVIE_SPAN`, a non-skip-shaped choice giving none; A-KNIGHT led by
`KNIGHT_UNREAD`); **as-if-frozen** (changes exactly its keys; `freeze_problems` accepts them); **store-census** (PASS
with 6.1's line; mutants each FAIL by name: 164 e3 t2 ip215 moved to `forbidden_sites`, 166 e6 t1 ip502 out of the
writes, 164 e1 t3 ip308 out of `forbidden_sites`, 166 e2 given a store, 164 e0 t0 ip97 moved back to `error_path` -- its
guard cannot hold, ip57's 385); **regions** (PASS; mutants: 164.e2's points shifted, 164.e3's gate `y_lt` 7000, 165.e2
missing, 165.e3 with role hazard); **goals** ((g0)-(g7') each with its mutant: a step key "hold"; 164 #0's closures from
another band; 164 #1 at 80 (g1': no route); 165 #0 at 110 (g1': a route exists at 120); 165 #0 without 165.e3 in `avoid`
(g2'); 164 #0's `at_y` [13000, 14500] (g3': tri 98's level, not the goal's); 164 #1's until `y_gt` 14000 (g4': the door
fires before the evidence holds); P1 moved 200 u toward e2 (g5'); `at_y` [8000, 9150] (g6': under the release 8400); the
window's y band [5000, 6000] (g7')); **route-pins** (PASS; mutants: 164 e2 t2 ip42's constant, 164 e1 t1 ip178's, 164 e2
t2 ip51 as `JMP_IF(L221)`, 164 e1 t1 ip187 as `JMP_IFNOT(L15)`, 166 e6 t1 ip871 as `Field(31205)`, a second
DefinePlayerCharacter, 70 ip475's constant); **build-pins** (O5's unit on O8's members and the raw exit: 31258 with one
byte changed FAILS, its Field(55) remapped to 31205 FAILS, 31256 differing outside its operands FAILS); **keys offline
mutants** (a write's value; a chain `off` + 1; `start_first`'s target; `start_music` at ip138; a start-scoped
`after.old` 7; `after.run` "O1-O6"; the ip380 `++` prior removed; a start read's `race` [70, 0, 0, 130]; `carried`
without Bit[3796]; `carried` with Bit[3811] (O8's own target); Bit[3796] in `end_state`; a carried target given a route
store site; `end_state_trace` without Byte[8]; a synthetic 55 storing `UInt16[0]` in e10 t1's case 1 (KEYS (g):
reachable at `Map.Byte[24]` 1); the movie's `cinematic` at ip711; the seam's `exit` at ip502); **p-settings** (`VSync`
"0" FAILS; missing FAILS); **p-donor** (over the route donors PASS with the `31205 55` line; over route + end FAILS on
it); **p-donor-log**, **p-launch**, **p-pad**, **p-override**, **p-engine**, **text-strict**, **input-witness** (O4's to
O7's units on O8's values).

It prints the summary columns (FROZEN COVER FORBIDDEN VOID-ASYM START NO-SC CHAIN RESIDUE WRITES NULL STABLE LANDING SEAM
WALK ORDER KNIGHT MOVIE PATTERN MASKED STATE JOIN) and "N/N cases as registered", exiting 1 on any miss.

---

## 9. Build order (three parts; no deploy, no game, no `tools/play.py`, no full suite)

**BUILD TESTING (PLAN.md "Build testing" -- it overrides every earlier design's section 9; never "the whole file alone,
serially").** pytest from `ff9mapkit/`, the study scripts from the worktree root. `<S>` is the builder's scratchpad's
`o8_build` (this session's:
`C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX\4376ce2b-bd6e-4446-a9dc-f1510c3fc187\scratchpad\o8_build`).
- **Inner loop**: only the `-k` selections you touched -- `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W
  ignore -k <expr>`, with `-n 4` past 10 tests. Mid-PART regression checks: `py studies/story-trace/segment_regress.py
  --only <items your change can move>` (a PARTIAL run exits 3 and prints NOT THE GATE: that is its pass).
- **At the END of each PART, ONCE**: `py studies/story-trace/harness_tests.py whole --out <S>\<part>` (the whole file at
  `-n 8`, THE FLAKE PROTOCOL, a receipt), then `py studies/story-trace/segment_regress.py --pytest-junit
  <S>\<part>\receipt.json` (the full gate, exit 0), plus the CLI checks the PART lists. Both can run past 10 minutes
  under load: start each in the background and wait in loops of at most 9.5 minutes; never poll every few minutes.
- **THE NIGHTLY WINDOW**: the gate worktree runs the nightly at 04:00-04:40 local -- never START a whole-file run or a
  full gate between 03:45 and 04:45.
- **GREEN RECEIPT**: a stage whose HEAD and tree match the previous stage's receipt (`py studies/story-trace/
  harness_tests.py check <receipt>` exits 0) does not re-baseline. Never re-run a `-k` selection a whole-file run at the
  same HEAD and tree contains.
- **FLAKES**: the tools re-run only failed tests alone (3/3 a named flake); never re-run a whole file or the gate for a
  flake; name every flake in the commit message. A test that fails alone is a real failure. A load- or
  order-sensitive test is a TEST defect: fix the test.
- **Load-robust tests** (the nightly runs the whole file at `-n 6`, builds at `-n 8`): a drive test re-runs its run (at
  most 2 more) only when it ends in a DRIVER class a starved harness can cause (V13 budget -- the wait's deadline
  included; V7 by a timed-out or stalled walk -- the real-mesh spirals; a failed walk ended short by a stall),
  asserting the class on each discarded attempt (a starved driver re-runs or reads its own V-class: it never flips a
  verdict); a GAME class (V8 above all: the knight's wait), a V11, a V19, a V13 of the prior basis, of S22's unread
  height or of S21's unpublished watch (each deterministic in its test) or a wrong verdict is never re-run. V8 can stay
  deterministic only because S21 runs out on BOTH clocks: a starved fake stretches the wall's alone and the wait goes
  on to the run's deadline, a driver class (the claim review's #5); and no test keys a store, a wait or a stop on the
  wall clock -- a director stores on a call or a fake frame count, a `timeout_s` stands far over any starvation, and a
  measured seconds value is asserted as a bound, never "about N". Every race is reproduced by a
  deterministic stall (a wrapped call keyed on a store or a call count, `fake.stall_publish`, the exit gate), never real
  starvation; the fake's loop runs at most 4x its `render_fps`. A test asserts nothing a lead's in-game step changes: no
  deployed flag, no gate witness, never the draft's `rehearsals` / `rehearsal_fps` / `rehearsed`, never an unfilled
  draft value.
- Commit on the branch when a step is green, one step per commit, each message ending with "Co-Authored-By: Claude Opus
  5.5 <noreply@anthropic.com>". Non-ASCII files with Python (utf-8) or the Edit/Write tools (never a heredoc piped to
  python, never a PowerShell text round-trip); frozen JSON and baselines LF (`-text`); a Windows path in Python raw or
  escaped. Do not merge master: the lead merges it before the merge (a parallel session may land harness fixes there).

### PART A -- the regression gate extended to O7 (baseline FIRST), then the shared opt-in changes
0. **Before anything**: `git log --oneline master..HEAD`, `git status`; read
   `C:\gd\Dream-World-IX\.test-gate\latest.json`. RED LEDGER -> TRIAGE FIRST: at the design it is red at d6b77975 on the
   two rung-3 replay tests (`test_a_live_miss_in_a_replay_is_retried_in_the_same_room_not_struck`,
   `test_a_bounce_the_partner_entered_is_a_replayed_step_that_leaves_him_where_he_was`) that 15f24eee made load-robust
   before 421dbdfb (0.2 #13): re-run exactly those two, alone, at this HEAD (3/3); green -> the red is fixed upstream,
   say so in A0's commit; red -> stop and tell the lead (never build on it). Then the branch-point count of
   `tests/test_harness.py` (`py -m pytest tests/test_harness.py --collect-only -q -p no:cacheprovider`: a collection,
   no run) goes into A0's commit message.
1. **A0: the O7 gate and its baseline, FIRST** (1.4): G0'''''' `--capture-o7` with its two-readings rule and refusals;
   G40-G43; `FAKE_PINS_O7`, `FAKE_PIN_CLASSES_O7`, `fake_pins_o7()`, `o7_pin_names`; `PIN_BASELINES` five and
   `union_sources` / `union_base` / `g21` / `--rebaseline-source` over five (four-baseline calls exactly today's);
   `--baseline-o7`; `PYTEST_K_O8`, `REQUIRED_TESTS_O8 = ()`; `_missing()`'s `o7s` / `o8`; the module docstring (G0'''''',
   G40-G45); the registry test's body to G43; `test_segment_regress_o7_pins_join_the_union` (into `REQUIRED_TESTS`). Run
   `py studies/story-trace/segment_regress.py --only G38,G39` (O7's items green at the head first; exit 3), then
   `--capture-o7`, and commit `research/o7_regress_baseline.json` with its `.gitattributes` line before any other code
   change; then `--only G40,G41,G42,G43,G21` (exit 3).
   **A0b: THE O7 REPLAY, BEFORE ANY FAKE EDIT** (3.5): `test_fake_spiral_keeps_the_castle_route_identical`; capture with
   `O8_CAPTURE_REPLAY=1` (twice in one process, equal), commit the golden with its `.gitattributes` line and the test
   as `REQUIRED_TESTS_O8`'s first entry; then `-k "keeps_the_castle or keeps_the_steiner or keeps_the_hallway"` (3
   passed).
2. **A1: S20, S21** (`WALK_ONLY`, `WAIT_FLAG_KEYS`, `MAX_FLAG_BIT`, `step_of`'s validation, `x_walk`'s `at_y`,
   `_Drive.wait_flag` -- both clocks, the published count --, `run_step`'s row keys) with its nine tests (1.2). Breaks:
   `at_y` unread; done at the arrival with the flag unread; the deadline read as the timeout; a field change attributed
   to the driver; an unpublished watch read as the game's V8; the wall's clock alone running the wait out; `step_of`
   adding a key. Mid-PART: `-k "segment_walk or segment_step_of"`; `segment_regress.py --only
   G3,G4,G10,G11,G17,G18,G24,G25,G30,G31,G36,G37,G42,G43` (every dry run and offline check reads its tables through
   `step_of` and `until_ok`: exit 3).
3. **A2: S22** (`until_ok`'s y axis, its keys checked first and its raise, `has_y`, `loss_y` as route_to returns,
   both trigger executors with the own sample's y guarded) with its four tests; and, IN THE SAME COMMIT, the O3-pinned
   O2 test's one case (`until={"y_le": 0}` -> `{"w_le": 0}`, match `"x\\|z\\|y"`: 1.2's "What flips") re-baselined by name:
   `py studies/story-trace/segment_regress.py --rebaseline-source
   "ff9mapkit/tests/test_harness.py::test_o2_step_of_refuses_a_step_its_executor_cannot_run" --reason "S22 makes a y_
   until term valid: the refused case moves to an unknown axis (w_le)"` -- the commit message names the row. Breaks: a
   missing y read as False; the None rule before the key check; the y read after the switch; `round(None)`. Mid-PART:
   `-k "segment_until or segment_trigger or o2_step_of_refuses"`; `segment_regress.py --only
   G3,G4,G7,G10,G11,G12,G17,G18,G21,G24,G25,G26,G30,G31,G32,G36,G37,G38,G42,G43` (the O1-O7 until-triggers on the fake,
   every dry run and offline check through the reordered `until_ok`, G12's O2 selection with the edited case, G21's
   re-baseline row: exit 3).
4. **A3: S23** (`walk_kw`'s `unstick`, `run_step`'s row key) with its two tests. Break: `walk_kw` ignoring the key.
   Mid-PART: `-k "segment_walk_kw or segment_unstick"`.

**PART A REQUIRED-GREEN** (at A3's head, once):

| Command | Expected |
|---|---|
| `py studies/story-trace/harness_tests.py whole --out <S>\A` (background, waits <= 9.5 min) | exit 0; the receipt for HEAD and the tree; every test passed or a NAMED flake, 0 failed, 0 skipped, the ledger's xfail; collected = the branch point's + PART A's 17 (A0's one, A0b's replay, A1's nine, A2's four, A3's two; the edited O2 test is no new one) |
| `py studies/story-trace/segment_regress.py --pytest-junit <S>\A\receipt.json` (background) | exit 0; G1-G43 and G21 PASS (G21 over five baselines, with PART A's ONE re-baseline row -- `ff9mapkit/tests/test_harness.py::test_o2_step_of_refuses_a_step_its_executor_cannot_run`, A2's commit -- and no fake function touched); G12 collects the edited O2 test, passing |

### PART B -- the FakeGame for O8's route, then the driver's O8 tests
1. **B1: H26 and the spirals' meshes** (`clearances`, `_clearance`, `_move_to` and `_pushed_out` reading it) with four
   tests: `test_fake_spiral_clearance_per_field_defaults_to_the_global` (box: an empty `clearances` moves every step as
   today -- a scripted walk recorded with and without an entry equal to the global; `{30860: 80}` with the global 120: a
   180-u corridor passes in 30860 and stops him in 30861; break: `_pushed_out` reading the global -- a placement 100 u
   from a wall in 30860 is pushed out to 120); `test_fake_spiral_meshes_hold_the_levels_premises` (stock 164 and 165:
   every neighbour pair of open tris shares its edge's heights; the steepest 60-u step MEASURED and printed -- 93.5 /
   76.7 at the research -- and asserted under `LEVEL_STEP_DY`; the least vertical gap between stacked open tris
   measured and printed -- 4857.6 / 4774.1 -- and asserted over 2 x `LEVEL_BAND`; numbers printed, bounds asserted, never
   the numbers); `test_fake_spiral_places_steiner_on_loop_1` (164 `[2040, 3335, -5647]` publishes y 4780 +- 1, tri
   145, not 9776; 165 `[2055, 3411, -10519]` publishes 10280, tri 57; break: `place_height` taking the first tri);
   `test_fake_spiral_pinch_passes_at_slack_12_not_8` (stock 164, `clearances {30860: 80}`, scripted presses along 164
   #1's planned waypoints through THE PINCH WINDOW: with `squeeze_slack` 12 he passes (1202, 4520) and reaches (894,
   4588); with 8 he stops at the pinch's mouth; break: the squeeze without its bound). `_move_to` (an O7 pin) is
   re-baselined by name IN THIS COMMIT (`--rebaseline-source "tools/harness/fakegame.py::FakeGame._move_to" --reason
   ...`); then `-k "fake_spiral or keeps_the_castle or keeps_the_steiner or keeps_the_hallway"` (the three replays
   identical) and `segment_regress.py --only G21,G38` (exit 3). The real-mesh tests read the install: a warned skip fails
   G44.
2. **B2: H25, the knight walker** (`_step_walkers`' `start`, `store`, the H25 pair rule; the ValueErrors) with three
   tests: `test_fake_knight_waits_for_his_height_then_walks_and_stores` (box with 164's plane: he stands, `moving`
   False, while Steiner's published y < 8400; the first tick at >= 8400 he walks 1131.4 u at 15 u a tick; 61 ticks after
   the last index ONE `w` row 164 e1 t1 ip230 `Bit[3811] := 1`; seated at (-586, 3884); latched -- Steiner back under
   8400 does not hold him; break: no latch -- re-held mid-walk); `test_fake_knight_store_is_missing_when_the_visit_ends_first`
   (a door fired before the store: no ip230 row, ever; break: a store that outlives its visit's bodies);
   `test_fake_knight_holds_no_pair_across_levels` (his path crossing Steiner's XZ at |dy| >= 400: never held by him; a
   plain walker (no `start`/`store`) at the same XZ and |dy| still is -- today's XZ-only rule; break: the height rule
   applied to every walker, or to none). `_step_walkers` (an O7 pin) is re-baselined in this commit; then `-k
   "fake_knight or fake_patrol or keeps_the_castle or keeps_the_steiner"` and `segment_regress.py --only G21,G26,G32,G38`
   (exit 3).
3. **B3: the O8 route builder** (`_o8_route`, `_o8_register`, `_O8_FIELDS`, `_O8_MEMBERS`, `_O8_BOX`, `_o8_plane`,
   test-side) and two tests: `test_fake_tower_route_plays_to_55_unattended` (a SCRIPTED player on the planed box: the
   four residue rows; 164's prologue and grant; presses to P1 (the knight released, sits, stores), up to e2 (it fires at
   y > 12000 only: ip243 := 343 -> 165); 165 likewise (ip205, ip233 -> 166); 166's pages each Confirmed, ip345/ip380
   under 309, ip502, the movie beat, ip863, Field(55); 55's prologue: with `story_suppress` the trace holds EXACTLY 4.16's
   29 rows by ip (9 / 9 / 11), no `c` row, the cut 55 e0 t0 ip22 `same` 1; break: doors without their `y_gt` -- e2 fires
   on loop 1 and the route lands in 165 early); `test_fake_tower_movie_skip_dialog_resumes_at_no` (a stray Confirm after
   `armed_after`: the skip dialog opens on No; its default resumes the movie for its remaining frames; ip863 lands after
   them; `fake.movies` records the resume; break: an answer of Yes skips -- the frames played fall short).
4. **B4: the driver on the fake.** O8's predictions on the fixture (`_o8_pred(side, *, levels=False, **over)`: the two
   cells on the fixture's ids -- on the box without `closed_tris`, with `levels` the band closures from a test-side
   `_o8_band_closures` equal to C1's `band_closures` --, the regions keyed by them with their gates, `side_ends` {S:
   [55], F: [55]}, the members, `steps_default` O7's, the skip net, `budget` small) and `_o8_run` /
   `_o8_run_informative` (O7's shape; no basis pre-seeded where S19 is exercised). Twelve tests (S at 60 fps mean ticks,
   F through the members at 31 fps quantized where named; `wait_scale` 0.25; `story_suppress` on):
   - `test_o8_drive_climbs_the_tower_to_real_55_on_the_fake` -- S and F on the planed box: the four beats; step 0's row
     with `at_y` and `wait_flag` read; ip230 inside the span and before ip243; 166's six pages pressed, no press in the
     movie beat; the end row 55 ip22 on both sides (F: 31258 -> 55, REACHED, never V19); the pattern by ip;
     `end_state`; no forbidden row. Break: the cell without `wait_flag` -- ip230 MISSING (the visit ends first).
   - `test_o8_drive_walks_the_real_spirals_on_the_fake` -- stock 164 and 165 levels, `clearances {30860: 80}`, 164's
     `squeeze_slack` 12, the frozen step pair per field (band closures, clearances 80 / 64 / 120 / 120, `basis` "prior"
     on the #0s, `npcs` false on 164 #0), the knight: every step done, `at_y` held, the wait read, e2's losses at y >
     12000 / > 15000, the landings; `_probe_axis` never called. Reads the install (a warned skip fails G44).
   - `test_o8_drive_knight_fast_or_slow_keeps_the_order_on_the_fake` -- the knight's `after_ticks` 0 (stores during step
     0's walk: the wait reads at once) and 300 (a ~10-s wait of FAKE ticks), the fixture's `wait_flag.timeout_s` 60 and
     S21's run-out on both clocks (a starved fake stretches the wall's alone: the claim review's #5): both done, ip230
     inside the span and before ip243. Break: the span's right end at step 0's done row's `frame0` -- the slow knight's
     ip230 falls outside.
   - `test_o8_drive_knight_stores_during_a_failed_first_attempt_on_the_fake` -- step 0's first attempt ended short after
     T0 by a wrapper that returns only once the fake holds Bit[3811]: two step-0 rows, ip230 before the done row's
     `frame0` and inside the span. Break: a done-row window -- ip230 outside it.
   - `test_o8_drive_knight_missing_is_the_games_v8_on_the_fake` -- the knight with `store` None, `timeout_s` 2: V8 game
     at [30860, 1190, 1]. Break: V7 or by driver.
   - `test_o8_drive_fork_lands_in_real_55_from_member_166_on_the_fake` -- F: 31256 -> 31257 -> 31258 -> raw Field(55):
     REACHED by rule 1 before rule 2; the last `w` row before the cut 31258 e6 t1 ip863; the run's trace digest (with
     the fixture's members) holds ONE seam, 31258 -> 55. Break: `on_route` testing the members before the end fields
     -- the real end on F reads off the route (V11).
   - `test_o8_drive_fork_landing_in_real_166_is_v19_on_the_fake` -- F, `land_real` {"166": 30862}: V19 game at [30862,
     1190, 2]. Break: rule 2's V19 skipped (V11).
   - `test_o8_drive_back_door_e3_is_the_drivers_v11_on_the_fake` -- a mutant table walking 165 #0 through 165.e3 at a live
     height (avoid emptied, goal past it): the walk's loss in e3, its switch, V11 driver, `door` 30861.e3, `landed`
     164's id. Break: 165.e3 unregistered -- the loss no door's.
   - `test_o8_drive_movie_stray_dialog_answered_at_no_on_the_fake` -- one stray Confirm mid-movie: the skip net answers No
     (a `choice` row in the movie's span), the movie resumes and plays out, the run REACHED. Break: no skip net -- V1.
   - `test_o8_drive_movie_skip_dialog_with_an_empty_prompt_answered_at_no_on_the_fake` -- the movie beat's skip dict with
     `header` "" (3.7) and one stray Confirm: O7's net row fits nothing, the 166-scoped measured-line row (2.1) answers it
     at its default, No; the movie resumes, the run REACHED. Break: the net without its second row -- V1 by the game for
     a press's dialog (the claim review's #6).
   - `test_o8_drive_dead_level_door_holds_no_fire_on_the_fake` -- the planed box: step 0 crosses 164.e2's ring at y ~8000
     and step 1 crosses 164.e3's at y ~9300: no loss, no store, both done. Break: the doors without height terms -- e2
     fires on loop 1 (V11 by the walk's landing).
   - `test_o8_drive_unstick_false_through_the_pinch_on_the_fake` -- stock 164, 164 #1 with `unstick` False and `npcs`
     False, the squeeze held at 8 for the first call: that attempt fails with no blocker placed (`_blocker_ahead` counted:
     0), the second (12) is done. Break: S23 dropped -- a blocker placed at the stall.
   In this commit every `test_o8_*`, `test_fake_spiral_*`, `test_fake_knight_*` and `test_fake_tower_*` name goes into
   `REQUIRED_TESTS_O8` and G44 joins the gate (the registry and its test to G44). Mid-PART: `-k "o8_drive"` (`-n 4`);
   `segment_regress.py --only G44` (exit 3).

**PART B REQUIRED-GREEN** (at B4's head, once):

| Command | Expected |
|---|---|
| `py studies/story-trace/harness_tests.py whole --out <S>\B` (background) | exit 0; PART A's count + PART B's 21 (B1's four, B2's three, B3's two, B4's twelve), every one passed or a named flake, 0 skipped |
| `py studies/story-trace/segment_regress.py --pytest-junit <S>\B\receipt.json` (background) | exit 0; G1-G44 and G21 (PART B's two re-baseline rows -- `FakeGame._move_to`, `FakeGame._step_walkers` -- named in B1's and B2's commits, beside PART A's one) |

### PART C -- O8 itself
1. **C0: measure, read-only.** On O4's build (`C:\gd\_ns_playtest\o4\build`, never written): the three route members'
   byte diffs against their donors per language (O8-BUILD's pins: 31256's and 31257's two Field() operands each,
   31258's zero and its raw `Field(55)`) and the chain's `campaign.toml` (route members 31256, 31257, 31258 -- anything
   else STOPS PART C). No commit (the numbers go into C1's `o8_forks.json` `built.measured`).
2. **C1: `o8_west_tower.py`** (1.3, sections 4-6), `o8_forks.json` (6.4), `o8_dryrun.py`'s base run and session builder
   (C1's pure tests read them; C2 joins it to the gate), the `.gitattributes` line. Nineteen tests (into
   `REQUIRED_TESTS_O8`):
   `test_o8_tower_draft_reads_the_chain_from_campaign` (route members 31256-31258; `members` O4's twenty, never 31205;
   `side_ends` {S: [55], F: [55]}; `rehearsals` read from the draft, never a literal);
   `test_o8_tower_draft_steps_round_trip_through_step_of` (every draft step and every `as_if_frozen(draft)` step:
   `step_of(pred, raw) == {**steps_default, **raw}` with the climb merge -- critique #5's unit);
   `test_o8_tower_known_step_keys_refuse_an_unknown_key` ("hold" refused by O8-GOALS and the freeze; `KNOWN_STEP_KEYS8`
   holds the vocabulary of every frozen file through `frozen_through(7)`; break: a vocabulary missing "basis");
   `test_o8_tower_freeze_refuses` (each refusal of 7.3);
   `test_o8_tower_route_builder_matches_the_keys` (the B3 builder's stores == the draft's writes, chain, masked and start
   rows; its trace's `pattern_of` == the draft's `pattern`; its knight's `start` == `height_gate(ip178, ip187)`'s
   release, `{"y_ge": 8400}`);
   `test_o8_tower_census_classifies_every_site` (the real bytes: PASS with the derived counts -- error 3 / 3 / 4, dead
   6 / 5 / 3 -- and every `error_path` guard reachable; 164 e3 t2 ip215 moved to `forbidden_sites` -> FAIL (dead: its own
   ip54); 166 e6 t1 ip502 out of the writes -> FAIL; 164 e1 t3 ip308 out -> FAIL; 164 e0 t0 ip97 moved back to
   `error_path` -> FAIL (unreachable: ip57's 385, the claim review's #9));
   `test_o8_tower_regions_gates_read_off_the_pins` (the four gates, each through its test AND its consuming jump; a
   mutated constant moves its gate; a door's `JMP_IFNOT` as `JMP_IF` inverts it and REGIONS (c) FAILS; the knight's
   ip187 as `JMP_IFNOT` makes the release `{"y_lt": 8400}` and KEYS (f) FAILS -- the claim review's #7; a B_LE text ->
   None, refused);
   `test_o8_tower_goals_are_height_aware` ((g0)-(g7'), each with its mutant);
   `test_o8_tower_keys_derive_the_carried_scoped_and_reads` (over the repo's seven frozen files: the fifteen carried
   values, Bit[3796] among them; the narrowed scan sets the knight's talk aside -- without it Bit[3854]/[3855] FAIL at
   e1 t3 ip326; the three start-scoped olds; the two start reads with their races; mutants failing O8-KEYS by name);
   `test_o8_tower_end_race_derives_int16_2_and_byte_8` (stock 55 to e0 t0's RET: {Int16[2], Byte[8]}; the synthetic
   post-yield store counts; KEYS (g)'s other-function proof: stock 55's e10 t1 ip568 / ip582 unreachable at
   `Map.Byte[24]` 1, a synthetic case-1 `UInt16[0]` store FAILS; stock 64 from story-o3's arrival values: {});
   `test_o8_tower_walk_check` (pure: every clause, the at_y and wait evidence, the y-until loss -- a `lost` with no `y`
   FAILS "no height" and raises nothing --, path A (`landed` None with `landed_frame` and the next `visit` row) and path
   B both PASS, `landed` None with no `landed_frame` FAILS, the doors from `to`, their tag-2 SITES exempt after the
   trigger's first `frame0` -- a store before it FAILS --, the span exemption only for ip230);
   `test_o8_tower_order_and_knight_checks` (pure: every clause of each; by place on F; KNIGHT judges readings only);
   `test_o8_tower_landing_and_seam_checks` (pure: LANDING (a)-(d) over seam-free copies -- the run dicts untouched --
   and SEAM (a)-(f), zero seams FAILING);
   `test_o8_tower_movie_check` (pure: (a)-(c) over covered runs, a non-skip-shaped choice in the span FAILING (a), the
   clocked rate at 31 and 60 fps over rows with a write time, a short span FAILING (b));
   `test_o8_tower_knight_watch_reads_the_seat_by_place` (a fake knight under the drive: one `seat` and one `start1` row a
   visit; on F 31256 reads as 164; PATH B -- 164 #1's route_to returning after the switch (3.7) -- and a load poll
   still write start1, its field the reading's (the driver review's #2); sid 1 unpublished -> no rows, the run
   A-KNIGHT; break: a row a poll, or rows gated on the poll's place);
   `test_o8_tower_why_void_reads_the_start_the_movie_and_the_knight` (166 ip255 old 0 -> A-START naming ip249; 164 ip130
   old 2 -> naming ip475; 70 ip249 / ip475 in `pre` -> A-START; every reason led by `START_READ`; 125 / 1 -> none; a
   press, a skip dialog by text and by shape, an unbacked one, an unclocked span in `(f502, f863]` -> A-MOVIE led by
   `MOVIE_SPAN`, a press AT f502 -> none, a non-skip-shaped choice -> none; no seat / no start1 -> A-KNIGHT led by
   `KNIGHT_UNREAD`; `_void_ids` sets aside `START_READ` and `MOVIE_SPAN`, never `KNIGHT_UNREAD`);
   `test_o8_tower_start_run_forgets_every_seeded_basis` (164, 165, 31256, 31257 forgotten, nothing else);
   `test_o8_tower_preflight_verdicts` (P-DONOR over the three, the `31205 55` line named outside; P-DONOR-LOG over four;
   P-SETTINGS failing on `VSync` "0"; P-TEXT3 strict);
   `test_o8_tower_build_pins_hold_member_166_byte_identical_with_its_raw_field55` (synthetic builds: 31258 with a byte
   changed, its Field(55) as 31205, 31256 differing outside its operands -- each FAILS; O4's build PASSES: reads it, a
   warned skip fails G44).
   Mid-PART: `-k "o8_tower"` (`-n 4`).
3. **C2: `o8_dryrun.py`** -- every case, the story-o3 fixture and every unit of section 8, on the draft AND
   `as_if_frozen(draft)`, N/N each; G45 joins the gate with `O8_DRYRUN_FLOOR` = the count C2 prints (the registry and its
   test to G45); `test_o8_tower_trace_summary_cuts_at_end_places` lands here, and
   `test_segment_dryrun_globs_close_at_their_segment` is extended to O8 (`o8_dryrun.frozen_through(8)` holds O7's set
   and no o9+ file; once `o8_predictions_v1.json` exists it is in eight and not in seven). Mid-PART: `segment_regress.py
   --only G45` (exit 3).
4. **C3: `o8_rehearse.py`** + `--rehearsal-report`. Ten tests (every one with `warp_arrive_control` False and the
   engine's `soft_reset_ui`): `test_o8_rehearsal_stage_ids_follow_the_chain` (F-SMOKE's pairs and F-PASS's start from the
   chain; F-PASS's end REAL 55, no member; a stage start between 03:45 and 04:45 refused, by a test-side clock);
   `test_o8_rehearsal_plumbing_on_the_fake` (R-FULL's record holds every 7.2 section);
   `test_o8_rehearsal_void_stops_on_the_wait_on_the_fake` (`flag_stop`: the raise on the wait's first `wait_for`, its
   FIXED message, the run V13 by the driver -- never S21's V8 --, the `unwatch` ran, no direction hold and no press after
   it, the sends after it exactly F9's list, `recover-warp`, the title);
   `test_o8_rehearsal_void_stops_in_the_pinch_window_on_the_fake` (stock 164: the raise before the first hold inside THE
   PINCH WINDOW; a hold at the same XZ on loop 1 never fires it; V13; the title);
   `test_o8_rehearsal_void_stops_mid_movie_on_the_fake` (`movie_stop`, `after_s` scaled: keyed on the 166 e6 t1 ip502 row
   in the live trace, the raise inside the movie beat, its frame after the ip502 row's -- never in the 309 -> 311 quiet
   stretch; V13; the warp FIRST from FieldHUD with the movie playing; the title);
   `test_o8_rehearsal_pokes_the_movie_once_and_the_net_answers_no_on_the_fake` (`movie_poke`: one `press` row after the
   ip502 row, the skip dialog answered No by the net, no second dialog, the movie resumed and played out, REACHED; the
   record's poke section; break: a poke while a page is up);
   `test_o8_rehearsal_fmv_reruns_a_late_edge_v5_on_the_fake` (R-FMV with `error_window` {3: 9} on its first run: V5 by
   the driver, the stage re-runs it and F3's counts exclude it; break: the V5 counted);
   `test_o8_rehearsal_records_the_knight_the_pinch_and_the_movie_on_the_fake` (each pinch stall classified);
   `test_o8_rehearsal_smoke_sends_no_storytrace_on_the_fake`; `test_o8_rehearsal_fpass_runs_untraced_to_real_55_on_the_fake`
   (F-PASS reseeds first; REACHED real 55 via 31258, never V19; no `storytrace` verb). Mid-PART: `-k "o8_rehearsal"`.
5. **C4: the O8 section in `PLAN.md`** -- the question, the segment, the sides and their ends (the declared seam), the
   start and its scope (no start-dependent key; the olds; the two start reads; the carried values), the walks (S20-S23,
   THE PINCH and its ladder), THE KNIGHT WAIT, 166 and FMV004 played out, the end state's race, the checks, "draft:
   rehearsals pending, freeze pending", "a US session" in its heading, and THE O9 HANDOFF (9.1, verbatim). The brief's
   milestone line (CLAUDE.md section 10) is left as it is.
   **THE ROUND-TRIP PROOF** (critique #5), once, before C4's whole-file run: write the draft as a TEMPORARY
   `studies/story-trace/o8_predictions_v1.json` (a Python one-liner: `json.dumps(O8.draft(), sort_keys=True)`, LF), run
   `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "step_of_reads_every_frozen_table_unchanged or
   naming_of_reads_every_frozen_predictions"` (2 passed), DELETE the file (`git status` clean of it: never committed),
   and record the two passes in C4's commit message.

**PART C REQUIRED-GREEN** (at C4's head, once):

| Command | Expected |
|---|---|
| `py studies/story-trace/o8_west_tower.py --offline-check` | exit 0; "predictions: the draft"; the chain line (member(164) 31256, member(165) 31257, member(166) 31258; the end REAL 55); 6 PASS -- O8-BUILD, O8-KEYS, O8-TEXT, O8-CENSUS, O8-REGIONS, O8-GOALS, each detail 6.1's line |
| `py studies/story-trace/o8_west_tower.py --preflight` | exit 0, ALL GREEN (12) -- or the exact failing line reported to the lead |
| `py studies/story-trace/o8_west_tower.py --draft` | exit 0; the draft: `side_ends` {"S": [55], "F": [55]}, `visits` the three, the four steps each with `clearance` (80, 64, 120, 120) and no `timeout_s`, 164 #0 with `at_y`, `wait_flag`, `npcs` false, `basis` "prior" and "164.e3" avoided, the triggers with `y_gt` untils and `to`, `choices` the two net rows (2.1), `start_reads` the two with their races, `carried` the fifteen derived values, `error_path` 10 and `dead` 14, `end_state` without Int16[2], Byte[8] or any carried target, `end_state_trace` the raced pair, `seat_watch`, `movie`, `seam`, no `movies`, `rehearsals` [] |
| the round-trip proof above | 2 passed on the temporary file; the file deleted |
| `py studies/story-trace/o8_dryrun.py` and `... --as-if-frozen` | exit 0 each; "N/N cases as registered", the same N (the story-o3 fixture's o3-state-c asserting its EMPTY raced set) |
| `py studies/story-trace/harness_tests.py whole --out <S>\C` (background) | exit 0; PART B's count + PART C's 30 (C1's nineteen, C2's one, C3's ten), 0 skipped |
| `py studies/story-trace/segment_regress.py --pytest-junit <S>\C\receipt.json` (background) | exit 0; G1-G45 and G21 |

Then the lead's sequence (7.1-7.4): `--preflight`, the rehearsals, the freeze checklist, `--freeze` (v1), the session.

### 9.1 THE O9 HANDOFF (C4 copies it into PLAN.md's O8 section)
"**Next, O9:** O8 ends on the arrival in REAL 55 at 110 (cut at 55 e0 t0 ip22) on both sides. O9 starts with a raw `warp
55 110 1190` (S) / `warp 31205 110 1190` (F): the fork side SWITCHES CHAINS there (O4's alxc -> O1's tshp, whose
member(55) is 31205, ForkDonorPatch line 42 -- the reason O8's F side ends in real 55 and declares its seam). The raw
start's residue: SC bytes 0-1 and FieldEntrance byte 2 (0 -> 110); byte 3 holds 0 (110 = 0x006E), so expect THREE rows,
O6's contract -- re-derive, never assume. 55's START-DEPENDENT reads are e8 t1 ip633 / ip666 / ip1354, the party and
UInt16[19]: there a raw start differs from a true O1-O8 run in VALUE, not only in olds, so O9's start must be SEEDED or
those reads declared -- the owner's options: (a) declare them (`start_dependent` keys with `after.old`, O6's form); (b)
a chained start (O8's arrival as O9's start: not a raw warp); (c) narrow O9 to what 55 does before those reads; (d)
pokes before the warp -- `byte 19 15`, `byte 20 7` (UInt16[19] 1807), `byte 21 8` (UInt16[21] 8), `byte 303 1`, `byte 18
1`, `byte 208 1` -- each a carried value O1-O8 compose (`carried_from_segments` over O1-O8, never typed), the pokes then
registered residue. 55 is block 2 (text); its page 129 (e8 t1's WindowSync, in case 1) halts the scene at FieldHUD until
it is confirmed, and then the scene runs on by itself to case 3 -- e1 t1 advances Map.Byte[24] 1 -> 2 -> 3 on the
scene's Map.Bit[231] handshakes -- where e10 t1 ip582 stores SC 1400 (SC <= 1400): O9 MUST PREDICT SC 1400 from 55's own
scene (O8's end state leaves SC out of its live read: `end_state_scene`, the review's #3). O8 built for it: `at_y`, the
knight wait (`wait_flag`), the y axis on `until` with the loss's height off the ring, the opt-in `unstick`, the
per-field fake clearance, the height-triggered walker with a store, the declared seam (O8-SEAM), the raced end-state set
derived from the end field's bytes to its Main_Init's RET (`end_race8`), and `reach8` -- a store site's reachability
from given values, e.g. which of 55's e8 t1 / e10 t1 sites a `Map.Byte[24]` case reaches -- with `end_map_held8`, which
holds a Map variable only where no other function of the field stores it. If O8's F5 took the fallback (`unstick:
false`), say so here."

---

## 10. Open risks (what only the game can settle)
1. **The grants** (F1): 164 at published y ~4780 (tri 145 by GetTriIdxAtPos, FieldMapActorController.cs:1279-1306), 165
   at ~10280 -- the bytes' numbers (O5-O7's grants were exact).
2. **The prior basis on a ramp** (F2, F4): the first first-move checks on slopes (164 |n.up| 0.54-0.93); expected ~0
   and <= 4 deg; a basis the bytes do not predict stops a run (V13), never walks it astray.
3. **THE PINCH** (F5): 11.4 u a side under the radius 80 for ~410 u of loop 2's north turn; the fake's `squeeze_slack`
   12 is an estimate until R-SPIRAL measures the narrowest gap; the NO-GO ladder (2.5) and the fallback's own cost
   (under `unstick: false` a deflected hold raises the plain basis HarnessError: 0.2 #8) -- each stall classified, so
   the fallback's outcome is predicted before it runs (it can help blocker-sealed stalls only).
4. **The dead-level region crossings** (F2, F4): the first O-segment to walk through live regions at their dead
   levels (164.e2 twice on step 0, 164.e3 and 165.e3 on the steps 1): tag 2's height test fails and it jumps to its
   RET (ip51) before any store or control change -- proven in the bytes, not yet in game.
5. **THE KNIGHT** (F2): ip230 at ~T0 + 140 +- 8 ticks, the wait 2.8-4.2 s, his seat; his object must be published on
   both sides (P-OBJECTS) or the run is uncovered (A-KNIGHT: the instrument's miss), a whole side so reading VOID-ASYM
   (b); the watched bit must be published (a dropped watch is the driver's V13, never the game's V8).
6. **166's pages** (F3): 307's [SPED=2] crawl and a dropped first Confirm; 309 async under the stores.
7. **FMV004** (F3, F8): the static span (~47-51 s), the rate during it (60 fps through O3's FMV003), the watchdog's
   `no_progress_s`; the skip dialog's No path, FakeGame-proven and proven in game only by R-FMV run 3's deliberate poke
   (F3: a dialog that does not resume STOPS the freeze); a stray dialog in a session run makes that run uncovered
   (A-MOVIE), never NOT PROVEN; a stop while that dialog is up (unproven).
8. **The 166 -> 55 crossing on F**: the session's F runs are its first traced in-game proof (R-FMV is stock, F-PASS
   untraced); the story-o3 fixture and the synthetic traces prove the code against a real archived seam (critique #3).
9. **The end** (F7): Int16[2] and Byte[8] race 55's prologue (read from the trace); whether ip342 lands in the cut's
   frame (it races either way).
10. **Render rates** (F14): no O-segment walk has met 60 fps; the game picks its rate.
11. **The budgets** (F8): estimated (~2.5 min a run).
12. **The [STNR] pages** render the default name on a raw start (text only, not judged).
13. **The shared install**: A-INSTALL (6.3); `--preflight` on the session's own launch (7.4).
14. **The nightly window**: the gate's 04:00-04:40 `-n 6` run starves the game and the driver alike; no rehearsal
    stage or session starts between 03:45 and 04:45 local (7.1, F10, 7.4).

Closed by the bytes or the source (no longer open): the four residue rows; the census's 61 sites and their classes
(0.2 #19, revised: 164 and 165 ip97 dead); the instancing without a dispatch; the 29-row pattern; the clearance plans
(80 / 64 / 120 / 120); one basis per field; the four gates and the knight's release, each read through its consuming
jump (0.2 #24); the knight's trigger, walk, store and seat; Steiner the controlled character on both sides; the two
start reads and their races; the fifteen carried values; the raced set, to 55's Main_Init RET, and no other 55 store of
an end-state target on this arrival (0.2 #26); the seam's shape (no remap: MAPJUMP); FMV004's MBG_DEF and type; the
skip dialog press-only (0.2 #23); no SC rung, battle, choice, naming or ATE; no facing gate.

---

## 11. Critique log

### 11.1 The research critic's ten
Each re-checked in the bytes, the harness or the code at 7576c8d8; none disproved. The critic's verdict -- GO, the one
major a cheap spec fix, THE PINCH the one in-game go/no-go -- is the design's.

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| 1 (major) | ORDER and the WALK exemption read "inside step 0's row window": with `attempts` 3 a failed attempt after T0 leaves ip230 outside the done row, and a correct run fails. | segment_drive.py:3051 (`frame0` per call), :3085 (one row per attempt), :3577-3598 (the settle between) | ADOPTED: THE EXEMPT SPAN `[step 0's FIRST row's frame0, step 1's FIRST row's frame0)` for ORDER (c) and WALK (b) alike (2.6, 5.3); ip230 before ip243 by line kept; B4's failed-first-attempt, fast- and slow-knight tests; the dry run's knight cases and the unit knight-span-done-row. |
| 2 (minor) | The second start read's raced store is not what `race_site` resolves (it keys on the read's own old: 70 ip130). | o7_castle_walk.py:366-374, :2612-2646 | ADOPTED, its first form: an explicit `race`, `race_value` and `edge` per start read; `race_site8`; `why_void` over both branches of each race with START_READ-led reasons, the late race worded as such (4.5, 5.1); O8-KEYS (c), the freeze, the unit race-site8. |
| 3 (minor) | O8-SEAM, LANDING without (e) and the raced end state first run on a traced fork run in the session. | F-SMOKE / F-PASS untraced; storytrace.py:838-877; o7 LANDING (e); o2 `seam_check` vacuous at zero seams | ADOPTED: the story-o3 fixture (o3-seam-F, o3-landing, o3-state-c and four mutants) and the synthetic uncut O8 traces, registered dry-run cases counted by G45 (8); `seam_problems` pure and parameterised. |
| 4 (minor) | Nothing in the session proves FMV004 played out. | no global store between ip502 and ip863; movie rows only under `movies` | ADOPTED: O8-MOVIE (a)-(c), the span at the rate measured inside it (the movie clock rows), its mutants; the span reported per run (5.3, 5.4). Revised by 11.3 A1 / B3: a press or a skip dialog in the span makes the run uncovered (A-MOVIE); (b) is the live check. |
| 5 (minor) | The pytest glob twin reads the future frozen file and asserts `step_of` returns `{**steps_default, **raw}`. | test_harness.py:27080-27097, :24508-24518; `frozen_through`'s docstring | ADOPTED: `step_of`'s new checks validation-only (1.2); `test_o8_tower_draft_steps_round_trip_through_step_of`; THE ROUND-TRIP PROOF on a temporary file at C4 (9). |
| 6 (minor) | "A missing y reads False" makes XZ-only proofs vacuous. | o5_hallway.py:802-824; o6_steiner.py:1006-1009; o7_castle_walk.py:1650 | ADOPTED: `until_ok` RAISES on a y term evaluated with y None (S22); O8's goals and regions height-aware ((g2')-(g7'), O8-REGIONS (c)); O2-O7's XZ proofs never receive O8's tables (0.2 #7). |
| 7 (minor) | `hold` already means three things; the skip rule is no `guard`. | segment_drive.py:3526-3533, :1581-1628 | ADOPTED: `wait_flag` (THE KNIGHT WAIT) and `flag_stop`; the skip answer is O7's `choices` row (2.1). |
| 8 (minor) | O7's fake functions are unpinned and O8 edits them. | segment_regress.py:862-873; research/ held o1-o6 baselines | ADOPTED: A0 captures the O7 baseline with FAKE_PINS_O7 (0.2 #1) FIRST; A0b's O7 replay before any fake edit; H26 an instance knob defaulting to O7's behaviour (`squeeze_slack` already one); each edited pin re-baselined in its commit; G38-G43 on every PART's receipt. |
| 9 (minor) | The knight's seat is measured in rehearsal only. | `_npc_discs` (talk-only: a body disc); O7's static watch | ADOPTED as a CHECK (decision 6): `seat_watch`, the hook's `seat` / `start1` rows keyed by place, O8-KNIGHT (5.3); a stop in rehearsal (F2). Revised by 11.3 B3 / A2: a missing reading makes the run uncovered (A-KNIGHT), never a FAIL; the rows are written on any poll. |
| 10 (option) | Split 164 #1 so the 64 applies only through the pinch. | the corridor profile (dispute 2); per-step clearance exists | WEIGHED, NOT TAKEN (decision 5): 2.5's four reasons; the owner's option at the ladder's last rung. |

### 11.2 Where this design reads a decision's letter differently (each said, none relitigated)
1. **Decision 4(b)'s outcomes**: ordered -- the run's deadline first, then the field change, the bit, control, and
   last the run-out -- and the deadline is a `void` verdict (the row written, the cell named), still V13 by the driver,
   not a bare HarnessError. Its "timeout -> V8 by the game" reads (11.3 A4, B4, B5): the wait runs out only once BOTH
   clocks ran `timeout_s`, and is the game's V8 only when the window's last sample published the bit (else the
   driver's V13: the watch never published).
2. **Decision 4(c)'s "the evidence path reads y off the ring at lost.frame"**: for route_to's probe sample (it carries
   no y), read AS route_to RETURNS, before `left_for`'s switch wait (11.3 A3); a loss the executor reads itself carries
   `st.player_y` at once, None kept, never rounded (11.3 B10).
3. **Decision 6's "a static watch ... at the wait's end and at step 1's frame0"**: a CHECK (O8-KNIGHT, decision 10's
   list) on the READINGS -- an unread one makes the run uncovered (A-KNIGHT: 11.3 B3); the wait's end read off the RING
   (the hook cannot see inside a step: 0.2 #21), step 1's frame0 off the hook's own reading of the very poll `run_step`
   takes it from, each row written on whichever poll first can (11.3 A2).
4. **Decision 7's "(b) the span at the run's fps"**: the rate measured INSIDE the span (the clock rows' frames over their
   state.json write times, a None write time skipped), so a rate that flips elsewhere in the run cannot mis-size it.
5. **Decision 8's "the raced end-state set ... taken from the trace by place"**: the SET is derived from 55's bytes
   (`end_race8`), typed in the draft and checked by O8-KEYS (g) and the freeze; the VALUES come from the trace by place
   (STATE (c)).
6. **Decision 8's "LANDING (a)-(d) (O7's (e) dropped)"**: O7's own `landing_check` over seam-free COPIES of the runs --
   (a)-(d) single-sourced, nothing of O7's edited.
7. **Decision 9's "per-field clearance and squeeze_slack become instance parameters"**: `squeeze_slack` already is one
   (`Levels`' constructor, one `Levels` a field); H26 adds the clearance only.
8. **Decisions 1 and 10's census (25/18/18)**: the totals and the 56 keys stand; 164 e3 t2 ip215 and 165 e3 t2 ip215
   are DEAD by O7's own dead-door rule, not forbidden (0.2 #19).
9. **Decision 11's R-VOID run 1** ("the hold's first poll", the research): `flag_stop` on the wait's first `wait_for`,
   after the watch is set, so the stop exercises S21's `unwatch`.
10. **Decision 4(f)'s `movie_stop`** ("at least N s after the 313 press"): keyed at least `after_s` 15 after the 166 e6
    t1 ip502 TRACE row (read off the live trace) -- the span's own opener, ten ticks after 313 closes -- so no game text
    is quoted (all six pages hold "[STNR]"). Revised by 11.3 A7: the design's first keying, on QUIET, had a thin margin
    over the 309 -> 311 quiet stretch.
11. **Decision 12's registry**: one test body edited three times (A0, B4, C2); the partial-run test already reads the
    registry and is not touched.
12. **Decision 7's O8-MOVIE (a)-(c) "per covered run"**: a run with a press, a skip dialog or an unclocked span in the
    movie's span is not a covered run (A-MOVIE, 5.1: the dialog is press-only, so its cause is the driver or outside
    input, never the fork -- O2's FORBIDDEN line, 11.3 A1 / B3); over the covered runs (a) and (c) then hold by
    construction and MOVIE re-checks them -- (a) also FAILS a choice of any other shape --, while (b), the span's
    length, is the check a covered run can fail.
13. **Decision 7's "a `choices` row copied from O7"**: O7's row, plus a second, 166-scoped row for the dialog's measured
    option line ("No"), so a prompt published empty is still answered (11.3 B6; O3's F4 rule).
14. **Decision 5's NO-GO ladder**: kept as ordered; F5's stall classification predicts the middle rung's outcome
    (11.3 A8), and never skips it.
15. **Decision 11's "R-FMV x2"**: two runs as decided, plus a third with `movie_poke`, proving the skip net's No answer
    in game (11.3 A1).

### 11.3 The design review
Two critiques -- driver robustness (A1-A13) and claim integrity (B1-B11) -- each item re-checked at 4ce8e9ff in the
bytes (`<R>/reconcile/L{164,165,166,55}.txt`; the stock 64 listing decoded by the research's own `ebtool.py` into
`<S>/o8_design_rev/L64.txt`), the engine source (`C:\gd\FFIX\Memoria\Assembly-CSharp\`), the harness, and the archives
(story-o6, story-o3, O3's R-FULL-SKIP, O7's R-FULL). Of the 24: 22 ADOPTED whole and 2 IN PART (A8: the classification,
not skipping decision 5's rung; B3: an unbacked skip dialog makes its run uncovered, not a FAIL). Neither review found
a blocker; the second's two HIGHs (B1, B2) would each have failed a build or a session.

**11.3.1 The driver-robustness review**

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| A1 (major) | O8-MOVIE (a)/(c) turn a press, a choice or a skip dialog in FMV004's span -- the driver's or outside input's -- into a session NOT PROVEN; the net's No answer is unproven in game; `skip_seen` keys on `options[0]`. | FieldHUD.cs:275-285 the only attach of "SkipMovieDialog" (grep of Assembly-CSharp), :435-437 (No re-arms the hit area); MBG.cs:205-208 (armed only in Play), :534-541 (paused while up); session.py:6421-6422, :6455-6528 (up to 3 Confirms, only while the window still takes answers); segment_drive.py:714-753, :3686-3701 (the witness polled between blocking calls); O3's R-FULL-SKIP (answered YES, the prompt in full) | ADOPTED: A-MOVIE under the COVERED rule, led by `MOVIE_SPAN`, set aside by VOID-ASYM like `START_READ` (1.3, 5.1); the span half-open after ip502's frame; MOVIE keeps (b) as its live check and re-checks (a)/(c), (a) failing a non-skip-shaped choice (5.3); `skip_seen` by text or shape (1.3); R-FMV run 3's `movie_poke`, refused by the freeze, proves the No path in game (7.1, F3). Re-registered: movie-stray-answered-one-S PROVEN; new movie-stray-answered-all-S (VOID by COVER), movie-script-choice-F, movie-press-at-f502-both. |
| A2 (major) | `start1` can be missed on a correct run: on `x_trigger_to`'s path B the step-1 row is appended after the map switch, so the next poll is in 165 or a load. | segment_drive.py:2610-2629 (`left_for` takes route_to's own landing first), :2774-2836 (`x_trigger_to`), :3042-3085 (the row appended after the executor returns), :3406-3408 (observe at the poll's top, `ctx` the poll's) | ADOPTED: `knight_watch` caches by place and WRITES on any poll, from the cached reading at the row's `frame0`, the row's field and place the reading's; the cache kept until both rows are written (1.3); the knight-watch unit (path B, a load poll), C1's watch test with a path-B wrapper (3.7), the case knight-start1-path-b-both. |
| A3 (minor) | `loss_y` reads the ring only after `left_for`, whose `switch()` can wait two `exit_wait_s` while the 300-sample ring (~10 s at 60 fps) evicts the loss sample; `round(st.player_y)` can meet None. | segment_drive.py:2583-2629 (`switch`, `left_for`); artifacts.py:35-40 (STATE_RING 300) | ADOPTED: `loss_y` as route_to returns, before the control wait and `left_for`; the own sample's y kept None -> V13 (1.2 S22); A2's ring test gains a switch-eviction wrapper. |
| A4 (minor) | THE KNIGHT WAIT reads "never published" as "published 0": a dropped watch times out as the game's V8. | channel.py:834-836 (`flag()` None unless published); HarnessAgent.cs:2162-2166 (AppendWatch's catch publishes `"flags":{}`); session.py:7922-7926 (`watch` a bare send) | ADOPTED (with B4): V8 by the game only when the window's last sample published the bit -- it latches, 164's only store to it being ip230 := 1 -- else V13 by the driver; `published` and `last` on the row (1.2 S21); `test_segment_walk_wait_unpublished_watch_is_the_drivers_v13_on_the_fake`; the case wait-unpublished-one-S. |
| A5 (minor) | WALK (b)'s door exemption ("after its loss") is bounded by the READ `lost.frame`; a loss read 25 ticks or more late puts the door's own first store before it. | L164 e2 t2 ExitField ip71 -> op_22(25) ip165 -> ip243; L165 e2 t2 ip61 -> ip155 -> ip205 (0.2 #25) | ADOPTED: the door's tag-2 store SITES (from `to`) exempt by site anywhere after the trigger step's first `frame0` (1.3 `visit_windows8`, 5.3 WALK (b)); door-row-before-loss-both re-registered as door-row-before-step-both (FAIL), door-row-late-loss-both (PASS). |
| A6 (minor) | F9's "no send, press or further wait after the raise" contradicts S21's `finally` `unwatch`, `collect_story`'s `storytrace 0` and `end_run`'s warp; S21 swallows a HarnessError holding "live samples". | segment_trace.py:722-729, :537-596; 1.2's S21 `except` | ADOPTED: F9 is no direction hold and no press after the raise, the sends listed; every stop a FIXED message that embeds no wrapped error; C3's test asserts V13 (7.1, F9). |
| A7 (minor) | `movie_stop`'s 15-s QUIET window: the 309 -> 311 stretch is quiet ~6-10 s, so run 3 could stop before the movie and claim the mid-movie recovery. | L166 e6 t1 ip340-454 (anims 6998 / 6982 / 6990, a Walk, op_22(10), op_22(90), a teleport, a Walk, RunAnimation(6605)) | ADOPTED: keyed `after_s` 15 after the poll that first saw the ip502 row in the live trace (`g.story_rows()`); the report FAILS F9 on a stop frame at or before ip502's (7.1); 11.2 #10 rewritten. |
| A8 (minor) | The NO-GO ladder's middle rung likely cannot help: with `unstick` and `npcs` off, slides are off (a deflected hold raises the basis error), and neither changes the pressed line or the engine's averaging. | session.py:4495 (`unstick = unstick or npcs`), :4659 (`slides=unstick`), :3554-3564; FieldMapActorController.cs:975-993, :1188-1254 (point forces averaged, a push across a wall rejected) | ADOPTED IN PART: F5's record CLASSIFIES each pinch stall -- rejected, blocker-sealed, slid -- and predicts the middle rung (it can help blocker-sealed stalls only); the owner's packet leads with the classification (2.5, 7.2, F5). NOT adopted: going straight to the owner on rejected or slid stalls -- decision 5 orders the rung on any NO-GO (not relitigated); it costs one R-SPIRAL pair, changes no verdict, and its predicted failure is recorded as predicted. |
| A9 (minor) | R-FMV's warp is not clean at the window's late edge: 166's ip57 sets `Int16[9]` -1 before ip79's test, so a warp after 70's ip475 takes the error path (V5). | L166 e0 t0 ip57 (65535), ip79, ip97; L164 / L165 ip57 (385) | ADOPTED: R-FMV and R-VOID run 3 record 166's Byte[13] old and re-run such a V5 (70 ip475 among the pre rows, or a 166 ip97 row), at most twice, never counted against F3 (7.1, F3); C3's `error_window` {3: 9} test. The same bytes settle B9. |
| A10 (minor) | The in-game stages are not fenced off the nightly window. | CLAUDE.md section 5 (the gate's 04:00-04:40 `-n 6` run) | ADOPTED: no stage and no session starts 03:45-04:45 local -- `o8_rehearse` refuses, F10 checks, 7.4 says so (7.1, 10 #14). |
| A11 (minor) | `timeout_s` bounds nothing in a walk, so 0.2 #12's premise and F8's sizing rule size nothing. | session.py:4518, 4557, 4580, 4748 (`wait_control`, the landing, the facing step); :2677-2706 (the ladder budgets) | ADOPTED: 0.2 #12 corrected; the four steps carry no `timeout_s` (`steps_default`'s 20, the start's control wait); F8's rule dropped, `rehearsed.steps_s` report-only (2.4, 4.12, F8). |
| A12 (minor) | An exception in the observe hook aborts the run; a clock row's `mtime` can be None. | segment_trace.py:719-721 ("STOPPED (unexpected)"); segment_drive.py:3406-3408; channel.py:1068-1071 | ADOPTED: `knight_watch` and `movie_clock` never raise (one `observe_error` row); only `movie_stop` may (1.3); MOVIE (b) and the unclocked reason count only rows with a write time (5.1, 5.3); the units and movie-clock-mtime-none-both. |
| A13 (minor) | Before release the knight publishes `talk_r` 410, not 395. | story-o7 R-FULL `states-final.jsonl`, frame 5472: (249, y 11255, 4630), r 220, talk_r 410, `range` False, `talk` True; HarnessAgent.cs:2349, :2360 (talk_r adds the speed) | ADOPTED: 2.6 and 3.2 corrected -- the builder's pre-release body 410, 395 only after SetWalkSpeed(15); nothing reads it (talk-only, session.py:5265-5266); 0.2 #27. |

The review's "found sound" list was spot-checked where the design leans on it (the knight's published start above; the
skip dialog's only opener and the 313 close order, 0.2 #23); nothing there changes the design.

**11.3.2 The claim-integrity review**

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| B1 (HIGH) | S22 flips an O3-pinned O2 test: `until={"y_le": 0}`, refused today, is accepted under S22 -- while 1.2 and PART A's G21 line said no pinned test changes. | test_harness.py:13515-13545 (the case at :13534); research/o3_regress_baseline.json `sources` (the test pinned); segment_regress.py:397 (G12's "o2_ or rehearse") | ADOPTED: A2 moves the case to `{"w_le": 0}` (match "x\\|z\\|y") and re-baselines it by name in its commit; 1.2's "What flips" records the grep -- no other accept/refuse flip (no table, test or dry run carries `at_y`, `wait_flag`, a step `unstick` or another y until; O7's `y_gt` lives in region `branches`); PART A's REQUIRED-GREEN names its one re-baseline row; A2's mid-PART adds G12, G21 and the dry runs. |
| B2 (HIGH) | WALK (a) wants `landed` the side's field of `to`'s place, but every in-game door step is done on path A with `landed` None. | segment_drive.py:417-447 (`trigger_to_verdict` done with `landed` None), :3075 (copied to the row), :2838-2870 (`walkout_record` adds `landed_frame`, `flip_late`, never `landed`); story-o6's o6_report.txt ("landing path A" six times); o6_steiner.py:2149, :2178 | ADOPTED: WALK (a) takes `landed` None with `landed_frame` set and the next `visit` row at `to`'s place, or the side's field of `to`'s place (5.3); the dry run's base run on path A, trigger-path-b-both PASS, trigger-landed-none-no-frame-both FAIL (8). |
| B3 (MEDIUM) | The driver's and the instrument's misses score as failed checks: MOVIE (a)/(c) on a driver press or the net's answer, MOVIE (b) unclocked, KNIGHT (c) unread. | as A1; O2's FORBIDDEN line (A-FORBIDDEN vs FORBIDDEN F) | ADOPTED IN PART: a press, a skip dialog or an unclocked span -> A-MOVIE (uncovered); an unread seat or start1 -> A-KNIGHT (uncovered, NOT set aside: a whole side unread reads VOID-ASYM (b)); KNIGHT fails only on a reading off the seat, MOVIE on a short span or a non-skip-shaped choice; movie-stray-answered-one-S and knight-unread-one-S PROVEN (2 of 3). REJECTED: movie-skip-unbacked-F expecting MOVIE F (c). The engine settles it -- only FieldHUD.OnKeyConfirm opens the dialog (0.2 #23), so an unbacked one is outside input the sampled witness missed (A1's evidence): the instrument's, and a FAIL would falsify on an instrument fault, against THE PAIRED-WALK LAW. FORBIDDEN's line holds where the game COULD have written the store; it cannot open this dialog. Registered as movie-skip-unbacked-one-F: PROVEN (F 2 of 3), A-MOVIE "outside input". |
| B4 (MEDIUM) | V8 by the game also covers a watch that never published. | as A4 | ADOPTED with A4 (one change). |
| B5 (MEDIUM) | The flag wait is timed on the wall clock while the fake's stores are timed in fake ticks: load can flip a test to V8, which is never re-run. | session.py:8664-8673 (`_game_seconds`: `rt`, else the write time); the design's A1 "`s` about 2" and B4's 300-tick knight | ADOPTED, both halves: S21 runs out only once BOTH clocks ran `timeout_s` (a clock it cannot read: the wall's); the tests key stores on a call or a fake frame count, carry `timeout_s` 60, and assert seconds as bounds (1.2, B4); the stub-clock test `test_segment_walk_wait_runs_out_on_both_clocks`; section 9's load-robust bullet. |
| B6 (LOW-MED) | The skip dialog is recognised by its prompt only: an empty prompt slips past `skip_seen` and the net, a V1 by the game for a press's dialog. | segment_drive.py:268-276 (`_rule_fits`: prompt and lines), :714-753; o3_design.md F4 and o3_route.md lesson 1 (an empty prompt seen on O4's encore) | ADOPTED, the answer by data: `skip_seen` by `skip_answer(choice, texts)` or `skip_shaped` (1.3); the answer by a second, 166-scoped net row for the measured option line, "No" (O3's F4 rule, 2.1) rather than by the predicate -- `_rule_fits` takes no texts, and widening it would be new shared machinery for a form no run has published (in game the prompt came in full both times); the case movie-skip-empty-prompt-one-S and B4's empty-`header` fake test. |
| B7 (LOW-MED) | `height_gate` reads the comparison, not the jump that consumes it: a flipped jump passes every check, and 6.1 (f) called ip178's test (the HOLD) the release. | L164 e1 t1 ip187 `JMP_IF(L15)`; L164 e2 / e3 t2 ip51, L165 e3 t2 ip51 `JMP_IFNOT(L221)`, L165 e2 t2 ip47 `JMP_IFNOT(L215)`, each to its RET (0.2 #24) | ADOPTED: the jumps and their targets pinned (4.14); `height_gate(test, jump)` returns the condition that reaches the guarded code, a `JMP_IF` loop negating it -- the release `{"y_ge": 8400}` (1.3); REGIONS (c), KEYS (f); polarity mutants in the route-pins and height-gate units and C1's regions test. |
| B8 (LOW) | `start1` is written only on a poll in place 164. | as A2 | ADOPTED with A2. |
| B9 (LOW) | `error_path` registers two unreachable sites: 164 / 165 ip97 (ip57 stores 385 before ip79's `Int16[9] < 0`). | L164 / L165 e0 t0 ip57, ip79, ip97; L166 ip57 -1 (its ip97 live) | ADOPTED: both moved to `dead` -- `error_path` 10, `dead` 14; the 56 keys and the field totals stand (0.2 #19, 4.6, 6.1); CENSUS proves every `error_path` site reachable from some arrival value (`reach8`); the mutant 164 ip97 back in `error_path` FAILS. |
| B10 (LOW) | `until_ok`'s None rule runs before the y raise its docstring promises; the mutant trigger-lost-no-y would THROW, not FAIL; `round(st.player_y)` raises on None. | the design's S22 code | ADOPTED: every key checked first (an unknown key, or a y term with y None, raises whatever x and z read); WALK (a) tests `lost.y` itself ("no height"); the executors keep None and take V13 (1.2, 5.3). No O1-O7 call changes: their untils hold valid x/z keys only. |
| B11 (LOW) | `end_race8` stops at 55's first yield, but the live read lands later, when other tag-1 loops run; o3-state-c's raced set was "printed", not stated. | segment_drive.py:1004-1018 (`read_end_state` waits for a publish); L55 (e8 t1 / e10 t1 dispatch on `Map.Byte[24]`, e0 t0 ip247 := 1; e0 t0 ip419 / ip453 behind `Byte[13]` / `Byte[14] == 9`); L64 and `race_any.py` (0.2 #26) | ADOPTED, refined: `end_race8` walks to e0 t0's RET (the same set); KEYS (g) proves no other 55 store of an `end_state` target reachable at `Map.Byte[24]` 1 (`reach8`, 4.9) -- the literal "every function but e0 t0's pre-yield code" would have failed on e0 t0's own post-yield ip419 / ip453, which the RET walk settles instead; o3-state-c stated up front: its raced set is EMPTY (64's default branch stores nothing new), so the fixture asserts {} and runs STATE (c) on a typed fixture registration (8) -- as first designed it would have judged nothing. |

### 11.4 As built (the implementer appends, PART by PART)
Where the design was silent or wrong, each the smallest correct thing, in O7's 11.4 form; then the code review's
findings, each with its re-check and its fix.

#### PART A, as built: where the design was silent or wrong (each the smallest correct thing)
A0 first, from master's merge gate and the nightly ledger, no new baseline: `.test-gate/latest.json` red at d6b77975
(2026-10-05 04:00) on the two rung-3 replay tests -- d6b77975 predates fe2aeafd, which made them load-robust and is on
master (57aac989) -- and each passes ALONE at this head 3/3 (the live-miss test 17.1 / 16.3 / 16.4 s, the bounce test
18.5 s x 3): the red is fixed upstream. `tests/test_harness.py` 1006 collected at the branch point (`--collect-only`,
nothing run). `segment_regress.py --only G38,G39` at the head PASS (G38 55 passed; G39 174/174 as frozen and as if
frozen), exit 3, 4 m 03 s. The gate extended (a8a5bf43), the O7 baseline was captured THERE before any other code change
(1018cab9): two readings identical, G38 56 passed (O7's 55 and the A0 test), G39 174/174 twice, G40 (story-o7, PROVEN,
17 checks, the archived report exactly, 186 lines), G41, G42 (89 sessions + 85 units, 174/174), G43 (6 PASS), 9 m 44 s;
3319115 bytes, LF, ASCII, 68 sources (G38's 56 tests and fake_pins_o7's 12), none pinned by an earlier baseline.
`--only G40,G41,G42,G43,G21` then read 5/5 (G21 over five baselines: 426 sources, 28 re-baseline rows), 3 m 14 s. A0b's
golden, on the unedited fake: route-S and route-F 529 sample changes and 63 trace rows each over 629 frames, the balcony
262 over 264 frames, the foot 13 over 13; 180356 bytes; the three replays green.

1. **A pinned test the design said would pass unedited.** "A call with four baselines reads exactly as today, so O6's
   pinned `test_segment_regress_o6_pins_join_the_union` passes unedited" -- every four-baseline call does, but that test
   ALSO pins the four-baseline BOUND: `union_sources(o3, o4, o5, o6, {})` must raise "joins at most the O3, O4, O5, O6
   baselines, not 5", and with `PIN_BASELINES` five a five-source call is no longer over it. No extension of G21 can keep
   that assertion, so its one statement now reads the bound off the registry (`len(PIN_BASELINES) + 1` sources, the
   message built from `PIN_BASELINES`) -- every later extension keeps it, as the partial-run test reads its count off
   `ITEM_ORDER` (O7's 11.4 PART A #1) -- and the test is re-baselined by name in A0's commit (row 28 of
   `research/source_pins.json`, head 153b0d6c). The row was written by `rebaseline_source(...)` called with the O3-O6
   baselines: the CLI's `--rebaseline-source` reads the committed O7 baseline too, which does not exist until the
   capture, and the edit belongs in the commit BEFORE the capture (the O6 baseline pins the test, the O7 baseline never
   does: G38's selection does not collect it). So PART A carries TWO re-baseline rows, A0's and A2's (1.2's "What
   flips" counted only A2's). The new O7 union test asserts the bound the same registry-relative way.
2. **`_missing()`'s `o7s` without the O7 baseline.** 1.4 lists "the O7 baseline" with O7S's session and report and V1_O7;
   `o7s` (G40-G43's inputs) holds the three archive files, and the baseline sits in the gate's and
   `--rebaseline-source`'s `files`, as O3-O6's do -- so `--capture-o7` never requires the file it writes. `o8` (G45's,
   from C2) reads `o8_predictions_v1.json` once it exists, else O4's `campaign.toml`; no mode passes it before C2.
3. **`fake_pins_o7` with a class.** FAKE_PINS_O7 names functions (O6's rule: a name fakegame.py defines no function for
   raises, naming it) and FAKE_PIN_CLASSES_O7 a class (O4/O5's rule: every method in definition order; a class with no
   method raises, named in the same message). Today: 6 functions and `Levels`' 6 methods, 12 fake pins.
4. **A0b's sample carries the published objects.** 3.5's compact sample is O7's A0b's -- him, the windows, the choice --
   but A0b exists to prove B2's `_step_walkers` edit neutral, and a held walker's own state never reaches that sample:
   Dojebon is talk-only, so a hold that broke would walk him off without moving Steiner by a unit. Each frame's sample
   ends with the published objects, `[[sid, x, z, moving], ...]` (`FakeGame._objects_doc`, itself an O7 pin): a held
   walker's place and `moving` are in the golden. The mutant `_step_walkers` ignoring the hold fails the test (Dojebon
   walks: his `(x, z)` and `moving` change); `place_height` one unit off fails it at the balcony's first frame.
5. **The balcony is 154's visit beat, not a bare level.** 3.5 (3) names `levels154` (O7's builder knob), so the scene is
   `_o7_route("S", short="154", levels154=True)` on stock 154's levels at radius 120 -- the grant at the bytes' height
   (H20's placement), Dojebon and the two soldiers (H23 and the pair band), the doors by height (H22) -- pressed along
   `_o7_plan154`'s ten waypoints from the grant to (0, -600): the plan passes 598 u from soldier e6 and 1091 u from
   Dojebon, who stays held at his placement throughout (asserted in the scene).
6. **`unstick`'s strict read lands in A1.** 1.2 lists `unstick`'s `step_of` check under S23 (A3), but A1's strictness
   test refuses `unstick` "no", so the check (a bool, or absent) is in A1's `step_of` with S20/S21's; A3 adds only
   `walk_kw`'s keyword and the row key. The strictness test's y-until clause (S22) joins it in A2. A `WALK_ONLY` key is
   read off the MERGED step (a `steps_default` carrying one would be refused on every non-walk), and a key whose value
   is None reads as absent, as `clearance` and `basis` do.
7. **A1's fixture.** The box with 164's plane (3.6) lands here: `_O8_BOX`, `_O8_PLANES` and `_o8_plane` (B3's builder
   reuses them), the walk from 164's spawn (2040, 3335) to P1 (1342, 2252). `_s20_drive` builds `SD._Drive` itself, as
   `drive` does, so the deadline test can set the drive's own deadline 1 s after the arrival; it ends a run on the walk's
   DONE row by moving the fake to the end field inside the log's `append` -- in the drive's own thread, the move
   published before the next poll -- so no poll can read control held after the cell's last step (V4) first.
8. **The control-loss test's door 5 u west of P1.** A door 30 u off is within `exit_slack` 40 only when the walk
   stopped within ~18 u of P1 (it stops anywhere within its tolerance 45 on the line from the spawn); 5 u keeps every
   stop within 29 u of the door's edge.
9. **"Nothing between the arrival and the read"** is the sends between route_to's return and the step row's append
   (the log's `on_row` hook): exactly `watch 3811` and `unwatch` -- the session's own `quit` after the run is no part of
   the wait.
10. **S22's trigger tests on S14's door fixture.** "The planed box" for the trigger tests is S14's north door (O6's
    proven fixture: its fire line past z 600, ExitField's walk-out, the test-held exit gate, the end 30821) with a
    test-side plane y = 7000 + 10 z in 30820 -- `y_gt` 12000 is S14's `z_gt` 500 by height, and 30821's arrival
    publishes y 0, so a y read after the switch fails the evidence. The eviction case builds `SD._Drive` to wrap the
    instance's `switch` (it empties the ring before returning) and holds the exit gate until route_to returns, so
    `left_for` must wait the switch out. The unread-height case empties the ring through a wrapper on route_to's
    return (not on `ring_since`: no module global patched), and blanks the executor's own sample at the fake
    (`player[1]` None from the scripted control loss on), so whichever sample the executor reads first carries no y.
    The S22 V13's reason names the loss's frame and field (`_Drive.no_height`), and x_trigger reads a y-until the same
    way (the probe's y as route_to returns; its own wait's sample its own, None kept).
11. **The O2 test's edited case** (1.2's "What flips") re-baselined by name in A2's commit with the CLI (row 29 of
    `research/source_pins.json`, d883a61f -> b52deb1c), as designed.
12. **S23's stall never lifts.** 1.2's "a `fake.freezes` zone holding him 40 frames" is shorter than route_to's stall
    check -- a smooth hold outlasts it and simply walks on (the harness's own freeze-and-wait test needs 360 frames to
    stall one) -- so S23's strip never lifts (`frames` None): with `unstick` False
    and `npcs` false the walk fails with no wait, no push and `_blocker_ahead` never called; with True the ladder runs
    (waits, a push, a blocker, withdrawn as `frozen`). Both are V7 after one attempt; `ROUTE_WAIT_SECONDS` 0.5 on the
    instance keeps the True case short (19 s for the pair).

#### PART B, as built: where the design was silent or wrong (each the smallest correct thing)
B1 from PART A's green receipt (`harness_tests.py check <S>\A\receipt.json`: e110d274 / tree 062569bc, GREEN), no new
baseline.

1. **H21 at a pinch narrower than its bound JITTERED; it never stopped.** 3.3 and 9 B1 ("with 8 he stops at the
   pinch's mouth") rest on the research's fake_spiral run ("slack 8 -> STOPS after 8 wps at (1272,4505)"). Traced a frame
   at a time, the fake never stands there: at the mouth the squeeze places him on the midline at (1242, 4511), gap 73.2
   (>= 80 - 8), and on the next press the step's end lies where the pinch is narrower than 72, so no squeeze places it
   and `_move_to`'s second block pushes him out (`_pushed_out`) onto the radius line BEHIND him, (1272, 4505), gap 80 --
   then squeezed in again: a 30-u jitter a frame, each push-out frame ~0.3 s of `_pushed_out`'s 64 bearings x 9 samples
   x 172 walls. A motion-based stop (`_lv_press`'s `still`) never fires (4000 frames, ~10 min), and a route_to stall is
   decided by the holds' frame parity. H21's own contract says he stops (`Levels.squeeze`: "where the pinch is narrower
   than that bound (he stops: the radius cannot fit)"), and so does the engine (the step refused: IsRadiusValid fails, a
   pushed position across a wall rejected: FieldMapActorController.cs:975-993, 1188-1254). So `_move_to` (re-baselined
   in B1's commit for H26 anyway: row 30 of `research/source_pins.json`) refuses that step: under H21, when the push-out
   lands BEHIND the press (`(push - start) . (step as pressed) < 0`) while he stands where a squeeze places him (the
   midline at his start fits the bound), he stays where he stands. Judged against the PRESS, not the step's end: the
   first block's slide had already bent the end sideways, and a push behind the bent end read as ahead of it. A lone
   wall's push (no pinch at his start: `Levels.squeeze` None there) is untouched. Neutral on O7, proven: A0b's golden
   (`test_fake_spiral_keeps_the_castle_route_identical`, the foot scene's slack-8 pinch included), O6's and O5's
   replays, every `fake_level` test and O7's real-mesh driver tests (the stair squeeze and its two snags at slack 0)
   green. Measured: slack 8 stands at (1258, 4507), y 10658 -- inside THE PINCH WINDOW, 56 u east of the narrowest point
   -- after 8 of the 10 waypoints; slack 12 (and 15) passes every waypoint of 164 #1's plan to (49, 2230), y 13030.
2. **B1 (a)'s break, read on the first moving frame.** "a placement 100 u from a wall in 30860 is pushed out to 120" is
   what `_move_to` reading the GLOBAL does (100 < 120 enters the push-out); `_pushed_out` reading it meets only a
   placement nearer than 80, never one at 100 (the gate before it reads the field's 80). So the test places him twice:
   100 u off (no push at 80; the `_move_to` mutant pushes him to 120) and 60 u off (pushed to 80; the `_pushed_out`
   mutant to 120) -- each read on his FIRST moving frame, where the push-out lands: a press re-aimed at its fixed target
   60 u off the wall walks him back to the 80 line after a push to 120, which hid the second mutant from the end
   position (its first run passed).
3. **B1 (a)'s "box" is a flat corridor under H20's levels.** The clearance acts only on a real walkmesh or a level (the
   tuple box has no walls), so the corridor is `_lv_pinch_bgi(half=200, pinch=90)` -- 400 wide, pinched to 180 over z
   0-200 -- as `Levels` in 30860 and 30861; at the global 120 he stops at its mouth (z ~ -79: the slanted edge's
   perpendicular distance), at 30860's 80 he passes.
4. **B1's real-mesh helpers** (`_o8_band_closures`, `_o8_plan`, `_o8_track`, the constants `_O8_SPAWN`, `_O8_SPAWN_Y`,
   `_O8_P1`, `_O8_GOAL1`, `_O8_BANDS`, `_O8_RADIUS164`, `_O8_PINCH`, `_O8_PINCH_AT`, `_O8_PINCH_PAST`) land in B1,
   ahead of B3/B4, which reuse them. `_o8_band_closures` is 1.3's `band_closures` test-side: C1 asserts the module's
   equal to it. The premises test also asserts each band leaves ONE level (no two of its open triangles overlap in XZ:
   `_lv_stacked_gap` infinite), the premise 1.3 states, and prints the closures (93 / 99 / 64 / 16).
5. **H25's read and its timing, as built.** `_walker_knobs` (a module function: unpinned) reads `start` and `store`
   strict on the walker's first step and marks the body (`_h25`) so it reads once; the store's countdown starts the
   tick AFTER the one that reaches the last index (the walk step runs after the countdown), so `after_ticks` 61 lands
   61 ticks -- 122 frames at 60 fps mean -- after the arrival, asserted to the frame. A `start` with a None player y
   (S22's blanked height) holds: no release on an unpublished height. The walkers run BEFORE the player in a tick
   (`_step_world`), so the knight is released on the frame AFTER the one whose step put Steiner at y >= 8400 -- the
   engine's ip178 reads the previous tick's position too. The design's three B2 tests stand; the main one also asserts
   the strict read's six refusals (3.2's "raises ValueError on the walker's first step" had no test).
6. **B2's "MISSING ... ever".** The door at P1 ends the visit mid-walk; "ever" is checked in the door's field (600
   frames) AND back in 164's id after a warp (600 more): a store that outlived its visit -- `_VisitBeat.end` keeping
   its bodies, the mutant -- would walk on and store there. (In the run the mutant fails earlier: 164's blockers still
   hold the knight after the door.)
7. **B2's held plain walker stands a step outside his r.** MoveToward refuses the step that would come within r, so the
   plain walker stands between r and r + one step (220-227.5 u at 7.5 a frame), still published `moving` -- O7's
   walker contract.
8. **B3's doors walk out toward MJPOS's point of their IN-GAME fire point** (`_o8_door(..., at=)`: 164 e2 at (24.5,
   2270.8), 165 e2 at (2419.6, 3130.0); a door never taken, its centroid) -- for 164.e2 the projection clamps to its first
   vertex (946, 2249): east, as the research's "ExitField walks him east ~26 ticks". On the box the door fires at the
   first ring point whose PLANE height is past its gate (164.e2 ~(375, 2224), not the game's west ear), after the
   step crosses its east ear at the dead level (~10200 on 164's plane): the scripted player's run and B4's step 1 both
   cross a live region at its dead level before the fire.
9. **B3's break is the FAKE's door, not the builder's.** "doors without their `y_gt`" is a mutant of H22's
   `_VisitBeat._door` ignoring `y_gt` (164.e2 then fires on its dead level, at ~10259: the test reads the fire's plane
   height); the test-side builder dropping it would prove nothing about the fake. The scripted player goes ROUND 164.e3
   by (2350, 2800) -- live at the spawn's level (y <= 6000), 157 u off: a straight press would fire it.
10. **`_o8_play`, not `_o7_play`**: FMV004 is a plain scene beat with no machine, where `_o7_play` returns. And B3's skip
    test presses through the agent's `press` verb by hand (`fake._execute`): a held key (`_schedule`) never reaches a
    plain beat -- only `_scene_press` at execute time does. 3.4's 166 is two visit beats round the movie beat, both
    index 3: H15's per-visit faults key both (an `error_window {3: 9}` takes visit A's error branch; B never starts).
11. **B4's fixture readers, as built.** `_o8_pred(*, short=None, closures=None, timeout_s=60, **over)` is O7's form: the
    predictions are the same on both sides (`side_ends` {S: [55], F: [55]}), so the design's `side` argument has nothing
    to key, and the real meshes' band closures come in as `closures` (`_o8_closures(wm)`, through `_o8_band_closures`).
    The wait's `timeout_s` is 60 on the fixture (9 B4) -- 2 for the missing knight -- never the draft's 15 (F2's).
    `_o8_run` takes the box's planes on both sides' ids (`_O8_BOX_PLANES`; `planes={}` on the real meshes, where a level
    sets his height), a log factory (the dead-level test's), and `_o8_route` a `skip` dict (3.7's empty prompt).
12. **THE SPAN is test-side in PART B.** `_o8_span` and `_o8_order` are 1.3's `exempt_span` and O8-ORDER's rule
    (`o8_west_tower` is PART C's): C1 asserts its `exempt_span` equal to `_o8_span` on these logs. The design's breaks
    for the fast/slow and the failed-first-attempt tests are the windows critique #1 rejected -- the right end at step
    0's done row's `frame0`; a done-row window -- run against the test-side span; each test also fails on a PRODUCT
    mutant: `x_walk` skipping THE KNIGHT WAIT (the slow knight's ip230 then MISSING or late), and `run_step` logging no
    failed attempt (one step-0 row where the test reads two).
13. **The fast knight needs more than `after_ticks` 0.** His store lands `after_ticks` after his LAST index, and his walk
    is 75 ticks (1131.4 u at 15 a tick) against ~3 ticks from T0 to P1 on the box (~16 on the real spiral): with
    `after_ticks` 0 alone he stores ~70 ticks into the wait. So the fast knight is also released at published y 5000 (a
    height reached only once step 0's walk is under way: after its `frame0`) and walks 240 u a tick (`speed` 120): his
    store lands MID-WALK, before the wait begins, whatever the load -- a starved driver only gives him more ticks. The
    test asserts step 0's `frame0` < ip230 < the wait's `frame0`; the slow knight's, the wait's `frame0` < ip230 <= its
    read frame and `game_s` >= 10 (300 ticks of the fake's own clock).
14. **The real-55 test's literal break cannot bite.** "on_route testing the members before the end fields": rule 1
    (`fid in self.ends`) runs BEFORE rule 2, so `on_route` is never consulted for an end field in the drive, nor by the
    live scan (cut at the end places): run, the mutant PASSES the test (recorded in B4's commit). The test fails on rule
    1 judging only a member's arrival (REAL 55 on F then reaches rule 3, off the route's order: V11) -- the regime the
    design's sentence describes -- and on a digest blind to real fields (no seam).
15. **The dead level on the box's plane.** 164.e2's ring stands at plane y >= ~10157 on the box (the real mesh's 8005 /
    8429 are loop 1's crossings UNDER it), so the mutant table's step 0 ends in e2's east ear at ~10800 and step 1 in
    e3's ring at ~7900 -- each at its gate's dead side, asserted on the plane first. A table whose last step is no door
    ends in V4, so the run is ended on step 1's done row by a log that moves the fake to 165's id (`_O8EndLog`, `_S20Log`'s
    rule: in the drive's own thread).
16. **One run, two key twists.** The fake's `twist` is one value and the real-spirals run crosses 164's (57.66 deg) and
    165's (35.16 deg): `_o8_real_setup` sets it every frame from the field he stands in (`_step_world` wrapped on the
    instance). The unstick test is 164 #1 ALONE (its fallback is the point): Steiner granted at P1 at the bytes' height
    and 164's prior cached (the frozen pair seeds it on step 0).
17. **`_probe_axis` counted on the wrapper's own list.** O7's real-balcony tests write `probes.extend(_s19_probes(g))`,
    which copies the wrapper's list while it is still EMPTY: their later probes never reach the asserted list (a check
    that cannot fail; O7-pinned, left as found). O8's real-spirals test keeps the wrapper's own list (`wrap.probes`).
18. **Exact attempt lists re-run a load-bent run.** The failed-first-attempt and the unstick tests read an exact step-row
    list ([failed 1, done 2]); a starved walk that fails an attempt more, or the knight's store not come within the
    wrapper's 60 s, is the load's (`spoiled`, its class asserted the driver's) and re-run -- at most twice, so a real
    regression still fails. ORDER is asserted before a step row's `wait_flag` in the segment and fast/slow tests, so
    THE KNIGHT WAIT skipped fails each on ORDER itself (ip230 late, after step 1's `frame0`, on S; the slow knight's
    MISSING) rather than on the row's missing key; the slow knight runs first.
19. **G44 joins the gate in B4** (`ITEM_ORDER` before G21, `SEGMENT_ITEMS["O8"] = ("G44",)`, `PYTEST_ITEMS`, `g44`,
    the gate's judges), `REQUIRED_TESTS_O8` holds PART B's 21 beside A0b's replay, and the registry test's body reads
    G1-G44 (unpinned: G21 unchanged at 426 sources).

#### PART C, as built: where the design was silent or wrong (each the smallest correct thing)
C0 read O4's build read-only: the route members' byte diffs against their donors per language, as O8-BUILD pins them
(31256's and 31257's two in-chain `Field()` operands each; 31258 byte-identical to 166 with its raw `Field(55)`), and
the chain's `campaign.toml` (route members 31256, 31257, 31258) -- `o8_forks.json`'s `built.measured`.

1. **164 e1 t3 ip690 is DEAD, not forbidden.** Its `Int16[224] := -761` (the talk's AddGil branch) sits behind ip641's
   and ip663's `const(1)` tests (bytes `05 7d 01 00 7f`): no value reaches it. The census's reach proof, extended from
   the error path to the forbidden sites (a forbidden site no arrival value reaches is a dead site, and its message says
   so), found it -- and C1's ip215 mutant (164 e3 t2 ip215 moved to `forbidden_sites`) needs exactly that proof: an
   error-path-only proof passed it. So `forbidden_sites` 7 and `dead` 15 (4.6's 8 and 14; the `--draft` row of PART C's
   REQUIRED-GREEN table reads 15), 164 forbidden 6 / dead 7; the 56 keys stand. O8-CENSUS's detail adds "every
   forbidden site reachable (7 of 7)".
2. **`end_race8`'s `globals0`, and `END_MAP_KEYS8`.** The story-o3 fixture walks stock 64 from story-o3's arrival
   values, which name only the targets O3 registered: a global the walk reads and they do not name was UNKNOWN, so
   Bit[3815] and Byte[475] read raced `[None, 0]`. `globals0=0` reads every unnamed global as New Game's 0 (the
   fixture's raw-start zeros), and its raced set is EMPTY, as 0.2 #26 says. O8's own call names every target it reads.
   KEYS (g)'s other-function proof holds `Map.Byte[24]` alone (`END_MAP_KEYS8`), its value read off the e0 t0 walk (the
   arrival sets 1; the walk returns its Map values as `map`). [Superseded by the review's #3 (11.4): a typed hold of a
   variable e1 t1 stores; `end_map_held8` derives the holds.]
3. **The seat watch's `walk_u` is 1131.5**: the four Walk legs summed from the pinned operands (2.6's 1131.4 is the
   same sum truncated); KEYS (f) compares within 0.05.
4. **`live_shared` in O6's census form**: `callers` [[6, 1, 489]] (4.6's `from` [166, 6, 1, 489] is no key the census
   reads).
5. **O8-GOALS' wait point and pinch.** (g5')'s door rule is `_fires_before` (a door fires before the step's goal only
   where its gate holds at the walked line's height) and the pinch's half-width is `least_half_width` (level-aware,
   every 10 u). The design's P1-move mutant can never reach (g5') -- (g4') refuses it first -- so the goals unit's mutant
   is `exit_slack` 300. The dry run's goals lines pin only start-independent substrings (`as_if_frozen` moves the
   measured numbers).
6. **The dry run's cases re-registered as rendered** (O3's EXACT `case()`; each docstring names the clause the design's
   list missed): knight-after-exit-both, knight-at-real-164-F, chain-dropped-fork, chain-back-door-site-both,
   byte13-explained-F, byte208-order-swap-both, visit-split-both, lands-real-165-covered, end-boundary-residue-both,
   seam-exit-wrong-F, seam-key-F (its row REAL 163's ip57 `Int16[9] := 385`, a key: a masked `Bit[191]` row gives
   none), int16-2-trace-end-F (byte 2, not 4: CHAIN passes) and byte8-trace-wrong-site-both; int16-2-live-race-both and
   byte8-live-race-both read PROVEN (`read_end_state` reads only `end_state`'s targets: the raced pair's live values are
   never compared). The end-race unit's tail reads `Byte[208]` (55's own error path resets Byte[13]). 117 cases and
   "predictions-changed", the story-o3 fixture's 9, 40 units and 52 listed units: 219/219, the floor.
7. **last-place-harness is S ONLY** (the design's -both): on F that harness row would be the seam's exit, and
   `storytrace.digest` RAISES joining a harness row to a script position (`_locate`, ValueError) -- a kit defect O8's
   route cannot reach (O8 pokes nothing), flagged as its own task.
8. **`movie_stop` and `movie_poke` lie on the STAGE, never on a step** (166 has no cell): `stage_pred` checks them
   (`_check_stop`: `place`, and `after_s` a number >= 0) and leaves the table as it is; `flag_stop` and `pinch_stop` lie
   on their step of the run's copy, as O7's stops do. F-PASS's end is a plain `[55]` (REAL 55 on both sides: no member
   to resolve).
9. **The rehearsal recorder reads T0 off the RING**, not the poll: the driver polls only between steps, and the release
   comes DURING 164 #0's walk (a poll-read T0 would land at the walk's end, ~750 u late). `t0_scan` keeps its own cursor
   beside O7's grant scan.
10. **THE SEND TAP is first on and last off.** O7's taps each restore what they found, so a tap installed after the hold
    tap is popped by the hold tap's restore -- and the sends a stop's F9 list names (S21's `unwatch`, `collect_story`'s
    `storytrace 0`, end_run's warp and ladder) come after the drive's taps are restored. `SendTap` wraps `send` before
    the hold tap and is restored after `end_run`.
11. **A late-edge re-run keeps its own files and a `counted` flag.** The re-run of run n writes `rh_<stage>_<n>r<k>`
    (`.jsonl`, `_log.json`: the V5's own trace kept), each record carries `counted` (False on the late-edge V5 set
    aside: F3's counts), and `--rehearsal-report` marks the set-aside run and prints what is counted.
12. **The step rows keep `at_y`, `wait_flag` and `unstick`** (`STEP_KEYS8`): O7's `step_records` trims to its own
    keys, and F2 and F5 read these.
13. **The nightly refusal runs twice**: before the session is touched (the launch's first stage, so a pure test reads
    it through the `clock` seam) and at each stage's start (`stopped` recorded, then raised).
14. **On the fake the movie's clocked rate is the fake's loop rate**: FakeGame runs its loop at 4x its render rate, so
    the frames over state.json's write times read ~170 fps, never the published ~60; the plumbing test asserts the span
    CLOCKED and its seconds the frames at that rate (the 31 / 60 fps readings stay C1's pure movie test). On the box
    164 #1 is ONE hold from P1, so the plumbing test's pinch window lies round P1, and the report's gap reads
    "unmeasured (no sample on a level)" there (the flat box under the plane's y); the stock-spiral records test measures
    68.6, the pinch's half-width, its stalls blocker-sealed before the ladder's frozen rung and rejected after it.
15. **The poke test breaks on its ONCE**, not on "a poke while a page is up": no page is up after the ip502 row on the
    fake's route (313 closes before ip502), so the quiet guard has no path to fail there; a poke on every quiet poll past
    `after_s` opens a second skip dialog.

#### The review: five findings on the built O8 (each fixed, none disproved)
A code review of PARTs A-C raised five findings: one medium, four low. Each came with a verifier's re-check against the
code (a scratch drive of the real `Recorder.t0_scan` over a real StateRing for #1; the placement read off stock 164 and
story-o7's archive for #2; `reach8` on stock 55 with and without the hold for #3; a probe of the draft's goals with
looser untils for #4; `Session.wait_for` on a stub channel for #5), and each was fixed with a test or a dry-run mutant
that fails without it (the mutant run named in its commit). None was disproved. One was tempered by the fixer and is
said: #3's failure scenario -- 55's scene setting SC 1400 "a few seconds after the cut" with no input -- does not hold
in a run. The scene reaches case 3 only past e8 t1's WindowSync page 129 (case 1), and the driver presses nothing in 55:
rule 1 ends the run on its first poll there (segment_drive.py's go loop). So the live SC read never raced. The PROOF was
unsound (it held a variable e1 t1 stores) and PLAN.md and the O9 handoff repeated its false claim, and those are what
was fixed. After the last code commit: the dry run 227/227 on the draft and as if frozen (219 and the review's 8 listed
mutants; `O8_DRYRUN_FLOOR` 227), `--offline-check` 6 PASS, and the fixer's whole-file run and full gate on its head (the
fixer's receipt).

| # | Finding | Re-checked | Disposition |
|---|---|---|---|
| 1 (low) | `Recorder.t0_scan` read T0 off the session ring (STATE_RING 300 distinct samples, ~10 s at 60 fps) only on go-loop polls, and none runs inside 164 #0's walk and THE KNIGHT WAIT: a slow knight or a stalled attempt ~10 s past the release evicted the crossing, and the scan took the first sample left at P1 (y ~8958) as T0 -- seconds late, unsaid, under-reporting F2's ip230 - T0. | A scratch drive of the real `t0_scan` over a real StateRing: a 60 fps climb crossing at frame 1160, then 12 s at P1, read T0 at frame 1522 (6 s late) with no marker; the design's own A3 admits the same eviction for the loss sample. | FIXED (316e9ce7): a scan whose ring no longer holds its last frame read records the eviction gap; after it the first passing sample is T0 only once a sample in his place UNDER the release follows the gap, else T0 is `{"frame": None, "evicted": True, "after", "held_from", "first"}` and the report's THE KNIGHT line prints T0 UNMEASURED. `test_o8_rehearsal_t0_scan_marks_an_evicted_release_unmeasured` (pure, a real StateRing: a ring of 300 reads UNMEASURED, one of 5000 frame 1160, and a gap before his place still reads the crossing) fails on the old scan (frame 1504, 5.7 s late). |
| 2 (low) | O8-GOALS (g6') kept loop 1 400 from `seat_watch.y`, 11896 -- his SEAT -- but the bytes place him on tri 130 at PSX -11255 and his walk climbs from there: the check over-stated loop 1's separation by 641 u at his lowest. The fake's H25 pair band kept the body's y at the seat's too. | A13 (story-o7's R-FULL archive reads him at (249, y 11255, 4630)) and o8_route.md's placement (GetTriIdxAtPos's highest: tri 130); his level along his walk off stock 164's mesh: 11255, 11448, 11598, 11727, 11896, monotone. Latent: band (164, 0) caps loop 1 near 9500. | FIXED (047c8736): `seat_watch.start_y` 11255; `knight_levels` reads his level along his pinned walk off the mesh; (g6') requires `start_y` and `y` to be the mesh's placement and seat levels with everything between, then keeps loop 1 400 from the whole range ("loop 1 at least 2297 below his level 11255-11896"). H25b (opt-in, `_step_walkers`, re-baselined by name): a path whose points carry a third coordinate moves the body's y with its x and z, linearly along each leg; `_o8_knight` carries `_O8_KNIGHT_LEVELS`, pinned against `knight_levels`. `test_fake_knight_pairs_at_his_own_level` (Steiner at y 11000: held on the first leg, walked through on the last) fails on the old fake and with the level fixed; dry-run mutants goals-knight-start-y and goals-knight-level PASSED the old (g6'). |
| 3 (medium) | O8-KEYS (g)'s other-function proof ran `reach8` with `Map.Byte[24]` HELD at 1, the value 55 e0 t0 leaves at its RET -- but e1 t1 (instanced by e0 t0 ip223) stores it 2 / 3 / 4 on the scene's `Map.Bit[231]` handshakes, so e10 t1 case 3's `UInt16[0] := 1400` (ip568 / ip582) IS reachable. (g) passed a false claim, and PLAN.md and the O9 handoff repeated it. | `reach8(55, 10, 1, 582)`: False with {Byte[24]: 1}, True with {3}, {} and None; e1 t1 ip76 is itself unreachable under the hold. Tempered (above): page 129 gates the scene, and the driver presses nothing in 55. | FIXED (8d670893): `end_map_held8` holds a Map variable only where no other 55 function stores it (derived: Bit[159] 1 and Byte[17] 255 held, Byte[24] and Bit[167] free; `END_MAP_KEYS8` is gone). `end_proof8` derives THE ARRIVAL SCENE -- the candidates' reachable other-function stores -- and requires `end_state_scene` to be exactly it. Option (b): SC out of the live read (`END_SCENE8`; the draft's end state twelve targets), SC 1190 at the cut resting on O8-NO-SC; the freeze refuses an arrival-scene target in `end_state`. Mutants keys-55-map-held, keys-sc-live, keys-scene-dropped and keys-live-dropped each PASSED HEAD's proof. PLAN.md's end-state paragraph and O9 handoff (O9 must predict 55's own SC 1400) are corrected, and this design's 0.2 #26, 4.2, 4.9, 6.1 (g), 9.1 and PART C #2 are marked. |
| 4 (low) | O8-GOALS (g4')'s "the door's first firing sample satisfies the until" cannot fail for an until looser than the door's gate (`first` is chosen where the gate holds), and nothing else tied a trigger's until to its door: 164 #1 at {y_gt: 9000} or 165 #1 at {y_gt: 11000} passed GOALS and the freeze, which checked only that a `y_gt` key exists. | A probe of the draft: both looser untils read GOALS PASS with the draft's (g4') line; only the stricter mutant (14000) failed. | FIXED (74c58160): `y_implies` -- the until's y terms at least as strict as the gate, per operator. (g4') fails "its until ... is looser than its door ...'s gate", and the freeze refuses a 164 #1 or 165 #1 until that does not imply its door's gate. Mutants goals-164-1-until-loose and goals-165-1-until-loose PASSED with `y_implies` neutralised; the goals test pins `y_implies` on every operator, and the freeze test refuses {y_gt: 9000}. |
| 5 (low) | S21's `wait_flag` absorbed only `Session.wait_for`'s "live samples" timeout. A window of a few tens of ms (the run's deadline just after the walk reached P1, or a re-wait's remainder) reads one sample and raises the frozen-channel error, which escaped unclassified -- the run STOPPED instead of the step's V13. The fake tests with `timeout_s` 1-2 were exposed to a whole-window stall. | `Session.wait_for` on a stub channel at 31 fps: a 0.0 s window raises "published nothing at all", 0.02 s the frozen channel, 0.05 s and up "live samples". | FIXED (958fe0ca): `WAIT_FLOOR_S` 0.5 -- under it the wait ends on the deadline at once (V13 by the driver), and every window lasts at least it; `NO_LIVE_SAMPLE`'s texts are the deadline's once the run's deadline has passed, else propagated as before. `test_segment_walk_wait_short_window_is_the_budget_never_the_channel` (pure, a stub whose every window reads no live sample) fails with the old loop; the fake tests' starvation rule (`_s20_load`, `_O8_LOAD_VOIDS`) re-runs a driver-class no-live-sample error. |
