# O7 -- Steiner's walk through the castle under the trace: 154 -> 158 -> 159 -> 160 -> 162 -> 163 -> the arrival in 164 (the design)

**Status: DESIGN, offline.** Nothing is imported, built, deployed, launched or frozen. The inputs are `o7_route.md` and
`o7_research.json` in this folder (the reconciled route, the walks, the start, the harness gaps, the fork gates), with
the critic's six problems (`critique.problems`) overriding the map where they conflict, and the ten decisions the lead
made on top of both (0.1). This file turns them into code-level decisions in `o6_design.md`'s structure and keeps what
O2-O6 learned. Every number below was read, read-only, from the stock US `.eb` files (the research's listings
`<scratch>/o7_research/reconcile/L{154,158..164}.txt`, re-checked with the kit at d6b77975 + the research commit), the
stock walkmeshes (`extract.stock_walkmesh` + `PlayerWalkmesh` + `route_avoiding`, exactly route_to's call), the live
install (`Memoria.ini`, the mod folders), the O6 archive and its frozen `o6_predictions_v1.json`, and the code at the
branch head. The re-plans and proofs of 0.2 were run here (`<scratch>/o7_design/plans.py`, `proofs154.py`);
`<scratch>` is `C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX\2b528e1b-375b-4c19-8f5f-30afde944b42\scratchpad`.

**Rev. 2** folds in the design review's two critiques -- driver robustness (8 items) and claim integrity (10) -- each
adopted or rejected in 11.3 with what it changed. The disputed facts were re-measured here, read-only, in
`<scratch>/o7_design_rev/` (`carried.py`, `derive_carried.py`, `h4.py`, `h4span.py`, `h4mut.py`, `replan3420.py`,
`slope.py`) and with the critics' own
scripts re-run (`<scratch>/o7_critic/foot163.py`, `w154.py`, `sim2.py`; `<scratch>/o7_critic_claims/hazard_cover.py`):
0.2 #11, #12 and #17-#20 hold the results.

**The segment** (decision 1): New Game, the trace armed, then in field 70 (after 70 e0 t0 ip130, before ip475) a raw
`warp 154 315 1190` (S) / `warp 31246 315 1190` (F). Six walked visits, no scene but one forced monologue:
- 154@315 (visit 1; EVT_ALEX1_AC_ENT_2F): Steiner granted on the BALCONY (Main_Init ip588); step 0, the NEW `walk` kind,
  west along the balcony, down the west flight, along the stair top and down the central flight to the ground at
  (0, -600); step 1, a `cross` of e8 ON THE GROUND (its ground branch: ip355 `Int16[2] := 300`, `Field(158)`).
- 158@300 (visit 2): cross e2 (ip194 `Byte[13] := 3` live, ip222 `:= 331`, `Field(159)`).
- 159@331 (visit 3): cross e11; on the way THE FORCED MONOLOGUE (e16 t1 ip390: pages 296-300, `Byte[208]`, `Bit[3796]`)
  takes control once and gives it back where he stands; the step re-runs and crosses (ip193 `:= 332`, `Field(160)`).
- 160@332, 162@333, 163@341 (visits 4-6): one cross each (`:= 333`, `:= 341`, `:= 342`); 163's is the stair-foot squeeze.
- END on arrival in 164 at 342: real 164 on S, member(164) 31256 on F, cut at 164 e0 t0 ip22 (`Bit[191] := 0`, emitted).

SC 1190 throughout (no rung). No battle, FMV, choice, naming, ATE or minigame. ~1.8 min a run (estimated).

What O7 newly puts under the trace: a field whose route crosses TWO LEVELS (a door whose tag 2 branches on his height);
the first WALK whose evidence is an arrival, not a door; the first step kinds planned at a stated CLEARANCE and run on an
exact PRIOR BASIS (no calibration probe); and a scripted interruption whose rows lie BETWEEN two attempts of one step.

---

## 0. What this design decides, and what it found

### 0.1 Decided upstream (not relitigated)
1. **The segment** (the research's SPLIT): as above; `visits` [154, 158, 159, 160, 162, 163]; `side_ends` {S: [164],
   F: [31256]}; the cut at 164 e0 t0 ip22 (Bit[191], emitted: verified 0.2 #13); SC 1190 (NO-SC). The fallback end,
   if R-STAIR fails, is the arrival in 163 at 341 (`side_ends` {S: [163], F: [31255]}) -- ONE line of the draft (4.17).
2. **The fork side**: O4's deployed members 31246 (154), 31250 (158), 31251 (159), 31252 (160), 31254 (162), 31255
   (163), 31256 (164); nothing imported, built or deployed; `o7_forks.json` references O4's chain (6.4).
3. **The start**: the raw warp; residue exactly four rows (0.2 #1); the front cut at 154 e0 t0 ip26; START requires 154
   ip123 (`Byte[13]` 1 -> 0), never ip101 / window 56; NO start-dependent keys (the O6 class is not used); three
   START-SCOPED olds and the carried values declared in the scope line (4.5); Steiner the controlled character on a raw
   start (0.2 #9).
4. **New shared machinery, each OPT-IN, FakeGame-tested, O1-O6 byte-identical**: (a) the `walk` step kind (S17, 1.2);
   (b) a per-step `clearance` threaded into route_to's planner (S18); (c) an opt-in exact PRIOR BASIS (S19); (d) the
   Dojebon hazard region REQUIRED in 154 step 0's `avoid`, a synthetic `hazard` role in O7-REGIONS, his published
   position watched (4.11).
5. **159's monologue in the FakeGame**: a one-shot scene with its five pages and the in-place re-grant (H22, 3.3); a
   test that rule 8's re-run then crosses e11.
6. **The checks layer**: O6's set adapted -- FROZEN, COVER, FORBIDDEN, VOID-ASYM, START, NO-SC, CHAIN, RESIDUE, WRITES
   (exact), NULL, STABLE, LANDING, WALK, PATTERN, MASKED, STATE, JOIN, THROW -- plus O7-CENSUS (counts derived), O7-REGIONS
   (the hazard role) and O7-GOALS (per walk, with mutants) (sections 5, 6).
7. **O6's preflight set** less P-NAME (6.2), all green before any rehearsal.
8. **Rehearsals** (the lead): R-FULL x2, R-WALK154, R-STAIR, R-WALK-VOID, F-SMOKE, F-PASS; the render rate recorded per
   run, never assumed (7).
9. **Built ON the shared machinery**: `O7Segment` in `o7_castle_walk.py`; the regression gate extended to O6 with its
   baseline captured FIRST (1.4); the registry test renamed and extended; predictions frozen by the lead; PLAN.md's O7
   section carries the O8 HANDOFF (9.1).
10. A parallel session may merge harness fixes into master; the lead merges master before the merge (11.2 #9).

### 0.2 Found while designing (each verified offline, read-only)
1. **The residue is FOUR rows**: SC 1190 = 0x04A6 (bytes 0: 0 -> 166, 1: 0 -> 4), FieldEntrance 315 = 0x013B (bytes 2:
   0 -> 59, 3: 0 -> 1): `[[0, 0, 166], [1, 0, 4], [2, 0, 59], [3, 0, 1]]` (StoryTrace's Diff emits a byte that changed).
   O6's three-row contract would refuse it: O7-START (a) is data-driven from `start_residue`.
2. **The census: 122 store sites, every one classified** (critique #5 confirmed: 154 holds 22). From the listings' store
   markers, per field (total: writes, chain, masked, error path, forbidden, dead, inert): 154 22 (4, 1, 2, 4, 6, 4, 1);
   158 18 (6, 1, 2, 4, 2, 3, 0); 159 22 (8, 1, 2, 4, 4, 3, 0); 160 24 (5, 1, 2, 4, 8, 4, 0); 162 18 (5, 1, 2, 4, 1, 5,
   0); 163 18 (5, 1, 2, 4, 1, 5, 0). Totals: writes 33, chain 6, masked 12, error path 24, forbidden 22, dead 24, inert
   1. The lists are 4.4-4.6; O7-CENSUS DERIVES and prints the counts, never reads them from here.
3. **Only 154's Main_Init dispatches on `Int16[2]`** (`SWITCH(304, L392, L232)` ip234). 158, 159, 160, 162 and 163 have
   NO entrance dispatch, so `o4_castle.instanced_at` and `o6_steiner.instanced_at6` RAISE on them; 160's InitObject(2)
   (Weimar) is gated by `Bit[3799] == 0` (ip232). O7 adds `instanced_at7` (1.3): the dispatch when there is one, else
   the same sound over-approximation with no case taken (every branch both ways) -- Weimar counts instanced, so his
   stores are forbidden sites, never inert. At 315, 154 instances {object 15, 5, 6, 7; region 9, 10, 8; code 1, 11}: e2
   (the 304 branch) is not instanced -- its ip1520 is the one inert site.
4. **The emitted pattern: 51 rows a run before the cut, no `c` row** (12 masked + 33 writes + the 6-key chain), every
   site first in its epoch; per visit 7 / 9 / 11 / 8 / 8 / 8 rows (4.16); 16 of the 33 writes same-value, each
   emitted (first at its site). No site is stored twice before the cut.
5. **Every O7 walk re-planned exactly as route_to plans it** (`plans.py`: `route_avoiding(..., KEEPOUT_MARGIN_W,
   leave_wall=True, clearance=c)`, the step's closures):

   | step | at 80 (today) | at 110 | at 120 (the engine radius) |
   |---|---|---|---|
   | 154 #0 walk (-58,-3758) -> (0,-600), closures 119, avoid e8/e9/e10 + the hazard | 7700 u, min wall 81 | 7790, 108 | **7803 u, min wall 119**, 10 waypoints |
   | 154 #1 cross (0,-600) -> (0,-4500), closures 134 | 3900, 870 | same | **3900, 870** |
   | 158 cross (0,-12787) -> (-17,-16444) | 3657, 603 | same | **3657, 603** |
   | 159 cross (7,3870) -> (-2910,-300); re-run from (-1601,1572) | 5089, 141; 2284, 291 | same | **same** |
   | 160 cross (1357,-4063) -> (-313,-813) | 4063, **85** (the corner) | 4103, 109 | **4113, 130** (no corner) |
   | 162 cross (957,-3800) -> (1001,406) | 4206, 213 | same | **4206, 213** |
   | 163 cross (690,2195) -> (997,4957) | 3885, 88 | **3880, 111** | **NONE** (also none at 116, 118) |

   So every walk plans at 120 but 163, which plans at 110 and not at 120 (critique #2): `clearance` 120 on six steps,
   110 on 163's (2.4).
6. **One key basis per field, exact from the bytes** (`UseAbsoluteOrientation = 3`: keys read `twist.y`, operand 1;
   session.py:2848-2866): every `SetControlDirection` in 154 is (246 | 250, 0) -- Main_Init ip223, Steiner's e15 t0 ip2127,
   the camera code e11 t1 -- so one basis 1.4 deg; 158 (0, 0), 159 (0, 0), 160 (246, 0), 162 (244, 0): 1.4 deg; 163 (16,
   16): 23.9 deg. Under `UseAbsoluteOrientation` 1 or 2 154 would read operand 0 and switch basis at the camera code
   (347.3 -> 353.0 deg): P-SETTINGS now pins `[AnalogControl]` (4.13).
7. **154's two levels**: stock 154's FLOOR indices mix heights (floors 0 and 1 each span PSX -1716..-5), so the fake's
   `PlayerWalkmesh.point_on_walkmesh` answers the GROUND under the balcony spawn (tri 132 before tri 250) and
   `distance_to_boundary` measures a floor's walls across both levels. The FakeGame has no level today; H20 adds one.
   Proofs (`proofs154.py`): every point within 45 u of the walk's goal (0, -600) is single-level ground; with step 1's
   134 closures every open tri touching e8 is ground (without them 9 of 27 are the balcony's, PSX -1716).
8. **e8, e9, e10 branch on his height**: tag 2 ip38 `SET({obj(uid=250).f[1] const(65436) B_LT B_EXPR_END})` -- `f[1] <
   -100` (published y = -f[1] > 100: the balcony) takes ip195 / ip203 (`Field(153 | 156)`), else ip355 / ip363
   (`Field(158 | 155 | 167)`). `scan_gateways` reports TWO rows for each (17 gateway rows on the route's six fields).
9. **Steiner is the controlled character on a raw start.** Each walked field's player entry runs `SetModel(5489, 104)`
   (GEO_MAIN_F0_STN) and `DefinePlayerCharacter()` on the route's entrance: 154 e15 t0 ip2774 / ip3003 (e15 instanced at
   315, its SWITCHEX default L2028), 158 e6 ip301, 159 e16 ip338, 160 e9 ip285, 162 e7 ip285, 163 e7 ip293; no other
   instanced entry defines a player, and no `PARTYCHK` or party op lies in an instanced entry of 154-163. A raw New
   Game's party [Zidane] reaches no store. O7-KEYS pins all of it (4.14).
10. **The forced monologue** (159 e16 t1, Steiner's own loop): ip390 `SET({Global.Bit[3796] const(0) B_EQ
    obj(uid=255).f[0] const(63936) B_LT obj(uid=255).f[0] const(1600) B_GT B_OROR obj(uid=255).f[2] const(800) B_LT
    B_OROR B_ANDAND B_EXPR_END})` -- `Bit[3796] == 0 && (x < -1600 || x > 1600 || z < 800)`; ip445 DisableMove; pages
    296 (WindowAsync slot 4), 297 (WindowSync), 298, 299, 300 (Async + WaitWindow); ip613 `Byte[208] := 0`, ip648 `++`
    (one loop pass: ip653 `Byte[208] < 1`), ip672 `Bit[3796] := 1`; ip711 EnableMove, no Walk. On the planned line it
    first holds at x = -1600 (z ~1573); e11's every vertex has x <= -2208, inside the trigger: the monologue always
    precedes e11. Its three rows are written with control OFF, after the step's first loss and before its re-run --
    BETWEEN TWO ATTEMPTS, where O5's `walk_windows` (o5_hallway.py:998-1014) would flag them: O7-WALK (5.3) exempts
    exactly them, there and nowhere else.
11. **Dojebon cannot be released by the route; probes are the only risk** (critique #1, refined). 154 e5 t1 ip263 /
    ip486 `SET({B_PTR(250) B_DISTANCEA const(3600) B_LT Map.Byte[30] const(1) B_EQ B_OROR B_EXPR_END})`; the camera code
    e11 t1 sets `Map.Byte[30] := 1` once `f[1] > -600` (ip14/33) and back to 2 at `f[1] < -500` (ip128/147); e15 ip2116
    sets 2 at the spawn. The planned route at 120 stays within 3349 u of him wherever PSX y < -500 (its far point is the
    spawn), under 3600 - 180 (`ROUTE_CHUNK_MAX` / 2, a hold's drift off its leg); it passes PSX -500 at (-680, 765).
    But the hazard region does NOT bound a probe's reach on its own: of the 13317 open grid points (16 u) at PSX y <
    -500 outside his circle, 5519 lie beyond `PROBE_HAZARD_PAD` of e8/e9/e10/the hazard (the nearest (32, -4048), 304 u
    from the spawn), and from where a 'down' probe leaves him
    (-63, -3998) the circle is 134 u east -- one hitch past a 2-frame walk probe. So the protection is S19 (no probe is
    pressed in 154); the hazard stays REQUIRED (decision 4(d)) for the walk's holds, every replan and any calibrated
    rehearsal. O7-GOALS (h) checks all four (5.3). His patrol stores nothing (e5 t1 holds no store site), so a release
    can never move a key; it is watched and reported (4.11), and a stop in rehearsal (F2).
    **Rev. 2, the hazard's geometry** (claim review #5; `h4.py`, `h4mut.py`, `replan3420.py`): the RELEASE ZONE -- step
    0's open floor (its 119 closures) above PSX -500 at >= 3600 u from his placement, where ip263's test lets him go --
    is covered by the decided polygon and the avoided exits, each dilated by `KEEPOUT_MARGIN_W` (56: no plan comes
    nearer), but for ONE SLIVER at e8's corner left by the decided west edge x 150: 14 points of an 8-u grid in x
    64..88, z -4016..-3984 (3 of the 16-u grid), the farthest (72, -4000) 78 u from e8. A shifted or shrunk polygon
    leaves far more (50 u east: max gap 104; 300 u east: 242; north edge 300 u south: 194). Re-plans: from 229 starts
    in the walk's drift band (every 120 u along the plan at 120, 0 / +-60 / +-120 / +-180 u across it, on open floor
    >= 120 u off a wall), every plan to (0, -600) stays within 3408 u of him wherever PSX y < -500 (worst from (-120,
    -3927)) -- under (h1)'s 3420. O7-GOALS (h4) pins the coverage; the re-plan census is design-time evidence (45 s: too
    slow for the offline check).
12. **The squeeze** (rev. 2, driver review #5; `foot163.py` re-run): 163's stair foot is a 233-u PINCH -- the best
    clearance across the corridor, level-aware, is 116.7 at (2124, 3875) and 117.1 at z 3900, under 120 from z ~3840
    to ~3920 (about 75 u): it overlaps Steiner's radius by 3.3 u a side. (The first draft's "226-256 u wide" was the
    x-extent at z 3850-4000, not the width across the corridor.) The wall push-out uses the CONTROLLER radius, size x 4 =
    120 (DoEventCode.cs:1531 `component1.radius = size * 4`; RadiusValid and ServiceForces, FieldMapActorController.cs:
    1060-1254, each force pushing out to `radius`, several averaged x 1.05); `collRad` 35 is the actor-pair radius
    (:781 `safeDist = radius + 4 * posObj.collRad`), never the wall's. The fake's clearance model (fakegame.py:1491-1528:
    never closer than `clearance` once there) cannot pass the pinch at all, while the engine's opposing pushes average
    out at the midline. H21 lets the fake through a pinch only down to `clearance - SQUEEZE_SLACK_W` (8 u, R-STAIR
    measures it). Memoria special-cases Steiner's size only in 164 (DoEventCode.cs:1507, size 30 -> 20 for sid 7):
    circumstantial evidence that 163 passes as shipped.
13. **The end row and the race**: 164's first store is e0 t0 ip22 `Bit[191] := 0` (same, a new site: emitted); 164's
    prologue then writes ip130 `Byte[13]` 2 -> 1 at once (a CHANGE) and ip764 1 -> 2 at its grant, so a live read of
    Byte[13] races; nothing else read at the end races (Int16[9] 385 -> 385, Int16[11], Byte[14], Bit[191], Bit[184]
    same-value; Int16[2], Byte[8], Byte[208], Bit[3796], Bit[3811] untouched before the knight's trigger). Byte[13] is
    taken from the trace's last pre-cut write, 163 e0 t0 ip684 = 2 (4.9).
14. **No door on the route is facing-gated** (`scan_gateways` face_gate None on all 17 rows) and every door's fade is
    `op_22(25)` before its stores (154 e8 t2 ip305, 158 e2 ip144, 159 e11 ip143, 160 e5 / 162 e3 / 163 e2 ip149); the
    back doors' `Byte[13] := 3` is live only at 158 e1 ip193, 158 e2 ip194 and 160 e4 ip194 -- elsewhere (160 e5, 162
    e2/e3, 163 e2/e3) ip199 sits behind `Map.Bit[162] == 0` (ip177), which the door's own ip38 sets 1 first: dead.
15. **No wall within 160 u of any O7 spawn** (the critic's `walls.py`) and the planned first legs (at 120) keep >= 119
    off every wall: a seeded basis's first hold is a free move, so its heading is evidence of the basis (S19).
16. **The premises at the branch head**: the nightly ledger is green (`.test-gate/latest.json`, c954f986, 11244 passed,
    1 xfailed); master is d6b77975 (O6 merged, the speed pass, two test fixes). O6's offline check and preflight hold
    (PLAN.md O6: 6 PASS, 13/13); P-OVERRIDE `2ce8887e`, P-ENGINE `ba976242`.
17. **The corridors, measured level-aware** (rev. 2, driver review #6-#7; `w154.py`, `slope.py`, `sim2.py`): 154's
    west arm is 330-356 u wide and the plan at 120 runs 124-137 u off its inner railing for 3072 u; the west flight is
    283-311 u wide, the plan 122-140 u off the wall; 163's upper stair at 110 runs 112-119 u off its left wall. With the
    engine radius 120 and pads 1.4-24 deg off each leg he slides along the railing for most of 154's descent (the fake
    walks still arrive, at 60 and 31 fps): planning at 120 does NOT remove 154's wall hugging. The steepest open tri of
    154 is tri 205 on the west flight, at (-896, 683): |grad h| 1.318 (52.8 deg) -- 79 u of height a 60-u step, |n.up|
    0.604; the plan crosses 1.27 (76 u a step) between (-962, 690) and (-842, 722); 163's steepest is 63 u a step.
    Under `PSXMovementMethod` 1 a step is scaled by the active tri's |n.up| (FieldMapActorController.cs:743-744,
    WalkMesh.cs:2666-2678), so a hold on the flight covers ~60% of its predicted reach -- over the movement cross-check's
    `SLOPE_STEP_FLOOR` 0.5, so no strike, but more holds. And where a stall outlasts the waits and the push, the blocker
    rung places `OBSTACLE_R_W` (192) ahead (pathfind.py:447): round it no route exists at 120 or 110 in these corridors,
    the call ends `frozen` or `blocked` and the step fails (reproduced on the fake at 163 with the fake's clearance at
    120: 2 waits, push `hold up 31`, a blocker at (2194, 4011), "no route", frozen). A failed attempt re-plans fresh from
    where he stands -- the call's own sealing blockers are withdrawn (session.py:4486-4497) -- so 154 #0 and 163 #0 carry
    `attempts` 3 (2.4).
18. **The carried values, derived** (rev. 2, claim review #1; `carried.py`): the six PROVEN archives' S traces
    (story-o1e run 3, story-o2..o6 run 1), each cut at its own start and end places, composed in segment order (`|=` on
    Byte[6] and UInt16[19] OR-composed), leave FOURTEEN targets that O7 neither writes nor reads and the raw start holds
    at 0: Bit[3717] 1, Bit[3718] 1, Byte[472] 4, Int16[469] 1042 (O2); Bit[3815] 1, Byte[475] 100 (O4); Bit[3795] 1 (O5,
    the stored choice); Bit[3854] 1, Bit[3855] 1, UInt16[21] 8, Byte[303] 1, Byte[18] 1 (O6); Byte[6] 11, UInt16[19]
    1807 (O1 + O2 + O6). (Byte[206] 213 is noise.) The first draft typed only O6's seven, and claimed Bit[3795] as 0 in
    `end_state`. The same fourteen follow from the REPO alone (4.5's derivation): every O1 write its v4 predictions do
    not register is rewritten by a later registered key or by O7, but UInt16[19]'s, which O6's frozen `start_dependent`
    carries as `after.old` 1799 (read from the archives at O6's design). No route field reads any of them (the listings
    L154-L163; 164 e1 t3, never driven, reads Bit[3854]/[3855]).
19. **The start's Byte[8]** (rev. 2, claim review #7; L70): field 70 e0 t0 ip249 `Byte[8] := 125` lies INSIDE the
    warp window (after ip130's `Byte[13] := 1`, before ip475's `:= 2`), behind ip229-246's wait on `SYSVAR[3]`. START (c)
    proves only "after ip130". A warp before ip249 leaves Byte[8] 0, and 159 e0 t0 ip290 would be emitted 0 -> 125, a
    change -- PATTERN (b) would fail on instrument timing. O7 makes it the start's problem: `start_reads` (4.5), A-START.
    In all 30 runs of story-o2..o6 the trace held no field-70 `w` row (70's prologue ran before the arm; one after it
    would be a `w` row in `pre`, which START (a) fails) and the route's first Byte[8] row read old 125: so 159 ip290's
    `old` is the one reading of the start's Byte[8], and every proven run had the registered value.
20. **A basis is cached per field id for the whole session** (rev. 2, both reviews): `route_to` seeds or calibrates only
    when `origin not in self._axes` (session.py:4411), and only `Session.begin_scenario` clears `_axes` (:8312) -- which
    segment_trace never calls between runs (story-o6: run 1 sent 7 holds, 4 of them calibration probes; runs 3 and 5
    sent 3). So under S19 alone only the first run per launch to reach a seeded field would judge its first move. O7
    therefore FORGETS every seeded field's basis at each run's start (S19's `forget_basis`, O7's `start_run`): every run
    seeds and checks afresh, which costs nothing -- no probe is pressed under a seed.

---

## 1. Module layout

### 1.1 Files

| File (in `studies/story-trace/` unless a path is given) | | What it holds |
|---|---|---|
| `segment_regress.py` | edit, FIRST (A0) | The gate extended to O6: G0''''' `--capture-o6`, G34-G37 (1.4), `FAKE_PINS_O6`, G21 over FOUR baselines, `--baseline-o6`; `PYTEST_K_O7`, `REQUIRED_TESTS_O7` (empty at A0); G38 joins at B4, G39 at C2. |
| `research/o6_regress_baseline.json` | new, FIRST (A0) | The captured O6 baseline (LF, `-text`), its `sources` included. |
| `research/o6_fake_replay.json` | new (A0b) | O6's route on the hand-stepped fake, before any O7 fake edit (3.7). LF, `-text`. |
| `segment_drive.py` | edit (A1-A3) | S17 the `walk` kind (`STEP_KINDS`, `STEP_NEEDS`, `step_of`'s new refusals, `x_walk`), S18/S19's `walk_kw` keys and `run_step`'s prior-basis conversion (keyed on the error's marker); `trim_route`'s three opt-in keys. |
| `tools/harness/session.py` | edit (A2, A3) | S18 `clearance` on route_to / route_cross / `_route_to` / `_plan_round` / `_plan_npcs`; S19 `basis` on route_to / route_cross, the seed, the spread (wide until the first move is judged, then narrowed), the first-move check, `forget_basis` at every pop of `_axes`, and `begin_scenario` clearing S19's state with `_axes`. |
| `tools/harness/fakegame.py` | edit (B1, B2) | H20 `Levels` + `fake.levels` + `place_height` + `_move_to`'s level branch; H21 the squeeze; `_visit_steps` and `_VisitBeat._place` for the place height (O5 pins); H22 the door's height terms and scenes (`DOOR_KEYS`, `DOOR_DEFAULTS`, `_door_knobs`, `_VisitBeat._door`: O6 pins); H23 the held walker (`_step_walkers`). |
| `ff9mapkit/tests/test_harness.py` | edit | The tests of 1.2, 3, 9; the O7 builder `_o7_route` and its helpers (3.6); the O6 replay (3.7). No existing test body changes except the registry test (1.4), which no baseline pins. |
| `o7_castle_walk.py` | new (C1) | `O7Segment(o6_steiner.O6Segment)` and its module functions (1.3). |
| `o7_forks.json` | new (C1) | The chain manifest: O4's, reused (6.4). |
| `o7_dryrun.py` | new (C2) | Synthetic sessions, units, offline mutants (section 8); `as_if_frozen(pred)`, `--as-if-frozen`. |
| `o7_rehearse.py` | new (C3) | R-FULL, R-WALK154, R-STAIR, R-WALK-VOID, F-SMOKE, F-PASS for `tools/play.py` (section 7). |
| `.gitattributes` | edit | `research/o6_regress_baseline.json -text` (A0); `research/o6_fake_replay.json -text` (A0b); `o7_predictions*.json -text` (C1). |
| `PLAN.md` | edit (C4) | The O7 section: "draft: rehearsals pending, freeze pending", the O8 handoff (9.1). |

NOT edited: `o1_*` .. `o6_*` (every module, dry run, rehearse script, frozen predictions), `tools/harness/channel.py`, the
agent. `o6_steiner` (and through it O5-O2) is imported as shared code; its outputs are the gate (G34-G37).

### 1.2 The shared changes (each opt-in; O1-O6 byte-identical)

**S17 -- THE `walk` STEP KIND** (decision 4(a); PART A, A1). A step whose evidence is an ARRIVAL: route_to to a goal,
judged by the landing judge first, then done when he stands within `tolerance` of the goal with control held in the
field.
```python
STEP_KINDS = ("cross", "trigger", "confirm", "wait_sc", "leave_now", "walk")
STEP_NEEDS = {..., "walk": ("goal",)}
#: S17: keys a walk step may not carry (in the RAW step: steps_default fills some for every kind) -- its evidence is
#: its goal, reached with control held; a door, an until, a landing or an answer is another kind's.
WALK_REFUSES = ("target", "until", "to", "expect", "sc", "wait_s", "then")
#: S18/S19: the opt-in keys every kind may carry, each checked strict.
BASIS_KINDS = ("prior",)
```
`step_of` gains three refusals, each raising ValueError naming the step (a table typo fails the offline check and the
driver's start, never a run): a `walk` whose raw step carries any of `WALK_REFUSES`; a `clearance` that is not a
positive number (a bool is no number); a `basis` not in `BASIS_KINDS`. Nothing else changes: O1-O6's frozen tables carry
none of these keys, so `step_of` returns exactly today's merge for them (pinned by a test that globs every frozen table).

`_Drive.x_walk(step)` -- x_wait_sc's walk half (segment_drive.py:2908-2944) without the SC wait:
```python
def x_walk(self, step: dict) -> tuple:
    """S17 (research/o7_design.md 1.2): the walk to the goal, judged by the landing judge first -- the field changed
    -> V11 (driver: strayed); control gone in (or within exit_slack of) a registered exit -> its switch waited out,
    V11 on a landing, else interrupted (door_loss); control gone anywhere else -> interrupted -- then, control held in
    this field within tolerance of the goal and route_to's reached -> done; else failed (blocked, boxed, frozen,
    no route, or short)."""
    g, fid = self.g, self.fid
    wait, tol = float(step["exit_wait_s"]), float(step["tolerance"])
    gx, gz = (float(v) for v in step["goal"])
    rec = g.route_to(gx, gz, tolerance=tol, avoid=polys(self.pred, step.get("avoid")), **self.walk_kw(step))
    out = {"route": trim_route(rec), "lost": rec.get("lost"), "landed": None}
    new = self.left_for(rec, out, "the walk", wait)
    if new is not None:
        return self.strayed(step, out, new, f"the walk left {fid}")
    st = g.state
    if out["lost"] is None and not st.control:
        out["lost"] = sample(st)                         # control went after the call's last read
    if out["lost"] is not None:
        why = "control went during the walk"
        verdict = self.door_loss(step, out, why)
        if verdict is not None:
            return verdict
        out["why"] = why
        return "interrupted", out
    d = None if st.player_x is None else math.hypot(st.player_x - gx, st.player_z - gz)
    if not rec.get("reached") or d is None or d > tol:
        out["why"] = (f"the walk ended " + ("where he stands unknown" if d is None else f"{d:.0f}u from its goal")
                      + f" (reached {rec.get('reached')}, route {out['route'].get('route')}, blocked "
                        f"{rec.get('blocked')}, boxed {rec.get('boxed')}, frozen {rec.get('frozen')})")
        return "failed", out
    return "done", out
```
The step row (`run_step`) keeps today's keys; its `to` (the sample after the executor) is where the walk ended: O7-WALK
(a) re-reads it. A walk carrying `beat` sets it on done, as every kind.

`walk_kw` passes the two new keys ONLY when the step carries them, so every O1-O6 call is literally today's:
```python
    kw = dict(walkmesh=..., prior=..., unstick=True, smooth=True, margin=..., timeout=..., npcs=..., overlay_ok=...,
              settle=step["settle"], handoff=True)                        # today's, unchanged
    if step.get("clearance") is not None:                                  # S18 (opt-in)
        kw["clearance"] = float(step["clearance"])
    if step.get("basis") is not None:                                      # S19 (opt-in)
        kw["basis"] = step["basis"]
    return kw
```
`run_step`'s row gains `clearance` and `basis` only when the step carries them; `trim_route` keeps `clearance`,
`basis` and `basis_check` (present in a route record only when given: S18/S19), so O1-O6 rows are unchanged.

Tests (A1; into `REQUIRED_TESTS`, G7's selection): `test_segment_step_of_walk_and_its_keys_are_strict` (pure: a walk
with `target` / `until` / `to` / `expect` refused; `clearance` 0, -5, True, "120" refused; `basis` "calibrate" refused;
a walk with only `goal` accepted; a cross with `clearance` 120 and `basis` "prior" accepted);
`test_segment_step_of_reads_every_frozen_table_unchanged` (pure: every `studies/story-trace/*predictions*.json`, globbed
at run time, every table step through `step_of` equals `{**steps_default, **raw}` with today's climb merge -- the file
list never pinned); `test_segment_walk_reaches_its_goal_on_the_fake` (box floor: done, the row's `to` within tolerance,
control held; break: done on route_to's `reached` alone -- a fake that hands back control 60 u short fails it);
`test_segment_walk_short_of_its_goal_fails_on_the_fake` (a blocker wall: failed, then V7 on the second; break: done);
`test_segment_walk_interrupted_outside_a_door_on_the_fake` (a `take` region on the line: interrupted, then the re-run
done after a test director re-grants); `test_segment_walk_loss_in_a_door_is_its_landing_on_the_fake` (a registered exit
region on the line that warps: V11 driver, `door` named, `landed` the region's `to`; with the region's switch never
coming: interrupted after `exit_wait_s`); `test_segment_walk_leaving_the_field_is_the_drivers_v11_on_the_fake` (a
gateway the route_to record lands through: V11 driver, `landed` set, the post-landing rows backed by the step row).

**S18 -- PER-STEP CLEARANCE** (decision 4(b); critique #2; PART A, A2). `route_to(..., clearance=None)` and
`route_cross(..., clearance=None)` (forwarded) thread it into the THREE planner calls and nothing else: `_route_to`'s
`pathfind.route_avoiding(wmesh, here, (x, z), polys, margin, leave_wall=True, clearance=clearance)` (session.py:4454),
`_plan_round(..., clearance=None)`'s two `route_avoiding` calls (:4899, :4903), and `_plan_npcs(..., clearance=None)`,
which passes it to its `_plan_round` (:5188). None is `route_avoiding`'s own default -> `route()`'s
`cam.COLLISION_RADIUS_W` (pathfind.py:480): today's plan exactly. The record gains `clearance` only when given. The
zone finish (`_zone_spots`, `_can_stand`) and the walk's holds keep COLLISION_RADIUS_W: a hold's drift is judged against
hazards and blockers, never walls (session.py:2932-2944), and the engine's push is the engine's. Tests (A2; into
`REQUIRED_TESTS`): `test_segment_route_clearance_plans_the_corridor_only_below_its_width` (route_to on the fake over
`_flat_bgi(-100, -2000, 100, 2000)` -- a 200-u corridor -- on both planner paths, plain and `unstick` (which plans
through `_plan_round`): clearance 90 plans, 120 returns `waypoints` None with nothing pressed, no clearance plans
(today's 80); break: the key dropped in `_plan_round` -- the `unstick` call at 120 plans anyway);
`test_segment_route_clearance_absent_keeps_todays_plan` (no `clearance`: route_to's `waypoints` equal
`pathfind.route_avoiding(floor, start, goal, avoid, KEEPOUT_MARGIN_W, leave_wall=True)` called directly -- today's call --
and the record holds no `clearance` key; behavioural, never a patched `pathfind`: memory, a module-global patch is
process-wide; break: a default of 120 inside route_to); `test_segment_route_clearance_plans_the_stair_at_110_not_120` (stock
163's `PlayerWalkmesh`, route_to from (690, 2195) to (997, 4957) round 163.e3 on the fake with no wall model: 110 plans
(>= 6 waypoints), 120 none; reads the install -- a warned skip without it fails G7).

**S19 -- THE PRIOR BASIS** (decision 4(c); critique #3; PART A, A3; rev. 2: the review's driver items #1-#4 and its
claim items #2 and #10). `route_to(..., basis=None)` and `route_cross(..., basis=None)` (forwarded). With `basis="prior"`,
`smooth` must be True (a HarnessError otherwise: only the smooth walk measures each hold) and `prior` a basis dict (else a
HarnessError: "no prior to seed"). Two session sets and a dict, initialized empty in `Session.__init__` beside `_axes`
(session.py:289): `_seeded` (fields whose basis is a seeded prior), `_prior_pending` (those whose first move is not
judged yet) and `_prior_angle` (field -> the first move's measured angle, once judged):
```python
        if origin not in self._axes:
            if basis == "prior":                    # S19 (opt-in): the exact prior, no probe pressed
                self._axes[origin] = {"v": tuple(prior["v"]), "h": tuple(prior["h"])}
                self._seeded.add(origin)            # a seeded basis: its first move judged, its holds wide until then
                self._prior_pending.add(origin)
                record["basis"] = "prior"
            else:
                ...today's calibration (clear of avoid and the published triggers)...
        elif basis is not None:
            record["basis"] = "cached"              # the field's basis already in hand: nothing seeded
        spread = self._field_spread(origin, prior) if smooth else 0.0
```
- **`forget_basis(*fields)`** (public): drops each field's `_axes` entry and its S19 state (`_seeded`, `_prior_pending`,
  `_prior_angle`) -- the next `route_to` on it seeds or calibrates afresh. EVERY pop of `_axes` goes through it: walk_to's
  wrong-basis pop (session.py:2210), `_walk_leg`'s (:3466) and the first-move check's below; and `begin_scenario`
  clears all four where it clears `_axes` (:8312). With the S19 state empty -- always, for O1-O6 -- `forget_basis(f)` is
  `_axes.pop(f, None)` exactly. Without it a field popped while still pending (walk_to's burst check; `begin_scenario`'s
  clear) and then calibrated stayed in `_prior_pending` -- its first evidence hold would run the prior check against a
  calibrated basis, a marker on a step that may carry no `basis` -- and any popped seeded field stayed in `_seeded`
  (a seeded spread on a calibrated basis), into the next scenario too (both reviews).
- **THE SPREAD** (`_field_spread(field, prior)`): a seeded basis is unverified until a move judges it, so until then
  its holds are planned for any error the check accepts -- `ROUTE_HEADING_FLOOR` + acos(`PRIOR_AGREE`) (2 + 16.3 deg),
  the spread an unprimed calibration gets (session.py:2946-2963). Once the check passes at angle theta the field's
  spread is `ROUTE_HEADING_FLOOR` + theta -- calibration's own rule (the measured disagreement) -- and `_walk_leg` re-reads
  it into its leg at every hold of a seeded field (`leg["spread"]`), so the narrowing takes effect at the next hold of the
  same call. Any other field's spread is today's `_heading_spread(basis, prior)` exactly; route_to's facing step (:4606)
  reads `_field_spread` too. WHY NARROW (driver review #4; the first draft's "wider fans shorten holds near avoided
  regions only" was wrong): `_plan_hold` keeps every hold's end within `drift - reach * tan(spread)` of its leg
  (session.py:3162-3163), so a wide spread shortens EVERY hold -- measured on the fake over stock 154 at 31 fps
  (`sim2.py`), step 1's straight 3900 u took 18 holds of 7 shrinking to 1 frames with the seeded spread held wide,
  against 4 probes and 3 holds of 23/23/20 frames calibrated. More holds mean more settles, longer budgets and more
  chances for the stall ladder.
- **THE FIRST-MOVE CHECK** ("the first move must still detect a wrong basis"): in `_walk_leg`, where a hold's
  displacement is measured (session.py:3445-3471), BEFORE the existing `projected < 0.35 * moved` test: the first hold in
  a field of `_prior_pending` whose movement is evidence (`_burst_is_evidence`) is judged -- the angle between his
  measured XZ displacement and the pressed world direction `u`; over acos(`PRIOR_AGREE`) (16.3 deg, the calibration's own
  one-sided acceptance, session.py:2071-2082) the field is forgotten (`forget_basis`) and a HarnessError raised with the
  ATTRIBUTE `prior_basis = {"field", "angle", "moved", "pressed", "measured", "predicted"}` (a marker, never a new class:
  O6's S15 rule -- every handler of HarnessError keeps catching it). Within it: the field leaves `_prior_pending`,
  `_prior_angle[field]` = theta, and the call's record gains `basis_check = {"angle", "moved", "frame", "pressed"}` --
  whatever the call's own `basis` (a step with none, after a seeded step that pressed no evidence hold, carries the
  check). The check runs whatever `slides` is: under `unstick` today's test reads a deflection as a slide
  (:3459-3463), which would hide a wrong basis. A seeded field stays in `_seeded` until `forget_basis` (its later calls
  plan at floor + theta); a field calibrated today never enters either set.
- **The driver** (driver review #3): `run_step` wraps the executor call -- `except HarnessError as err:` re-raises
  unless the ERROR carries `prior_basis`, whatever the step's keys (154's step 1 carries no `basis`, yet takes the check
  when step 0 pressed no evidence hold); then the step row is written with `v` "V13", `by` "driver", `why` "the prior
  basis disagreed with the first move: ..." and the run raises RouteVoid V13 (driver: the instrument's). Only a seeded
  field can raise the marker and O1-O6 never seed: their HarnessErrors propagate exactly as today.
- **Per run, not per launch** (0.2 #20; driver review #1, claim review #2): `forget_basis` is the shared half; O7 calls
  it over every seeded field, S and F, at each run's start (`O7Segment.start_run`, 1.3), so each run seeds and judges
  its own first moves. Nothing else forgets a basis between runs: O1-O6 keep today's per-launch cache.
- `ProbeLeftControl` cannot arise under a seed (no probe). `calibrate_axes` and `_calibrate_clear_of` are untouched.
Tests (A3; into `REQUIRED_TESTS`): `test_segment_prior_basis_presses_no_probe_on_the_fake` (fake twist 30 deg, the
prior its exact basis, `_probe_axis` wrapped to count: 0 calls; the record's `basis` "prior", `basis_check.angle` < 2;
break: no seed -- the probes pressed); `test_segment_prior_basis_wrong_stops_on_the_first_move_on_the_fake` (the prior
rotated 30 deg: the first evidence hold raises with `prior_basis`, the field in none of `_axes`, `_seeded`,
`_prior_pending`, nothing pressed after; break: no check -- the walk goes on and strays);
`test_segment_prior_basis_disagreement_is_the_drivers_v13_on_the_fake` (a table step with `basis` "prior" and the
rotated prior: RouteVoid V13 driver, the step row's `v` V13; a step WITHOUT `basis` converts the same -- a `walk` to
where he stands (seeded, nothing pressed), then a `cross` with no `basis`: V13 on the cross's row; a HarnessError
without the marker, from either step, propagates as today's; break: the conversion keyed on the step's `basis`);
`test_segment_prior_basis_widens_the_hold_spread` (pure: `_field_spread` for a seeded field = floor + acos(PRIOR_AGREE)
while pending, floor + theta once `_prior_angle` holds theta; for a calibrated one with the same prior = floor + the
measured disagreement, today's; break: the spread not narrowed);
`test_segment_prior_basis_narrows_after_its_first_move_on_the_fake` (a straight 3900-u leg on a box floor at 31 fps,
the prior exact: past the first evidence hold the direction holds number at most 3 more than a calibrated walk's on the
same leg; break: the spread held wide -- the critic's 18 shrinking holds);
`test_segment_prior_basis_forget_clears_the_seed_on_the_fake` (a field seeded and still PENDING -- a route_to with
`basis` "prior" to where he stands, nothing pressed -- since the first-move check precedes `_walk_leg`'s own 0.35 test on
every evidence hold, only another path can pop a pending field: (1) the fake's twist turned 90 deg and a `walk_to`
(`slides` off) there: its burst check pops the basis with a plain HarnessError, and the field is in none of `_axes`,
`_seeded`, `_prior_pending`, `_prior_angle`; a following route_to with no `basis` calibrates -- the probes pressed --
its record holds no `basis_check`, no marker is raised, its spread is today's; (2) seeded and pending again, then
`begin_scenario`: all four empty, and the calibrated walk after it the same; (3) `forget_basis`, then route_to with
`basis` "prior": seeded again, a fresh `basis_check`; break: a pop or a clear that leaves `_prior_pending` -- the
calibrated walk raises the marker against its calibrated basis);
`test_segment_prior_basis_absent_calibrates_as_today_on_the_fake` (no `basis`: the calibration's probes and the record's
keys exactly today's -- no `basis`, no `basis_check`).

### 1.3 `o7_castle_walk.py`

`O7Segment(o6_steiner.O6Segment)`:
- `tag = "O7"`, `predictions = HERE / "o7_predictions_v1.json"`, `manifest = HERE / "o7_forks.json"`, `session_file =
  "o7_session.json"`, `report_file = "o7_report.txt"`, `chain_dir` / `build_dir` O4's, `accept_us_build = False`,
  `recovery = 4600`, `end_session_warps = True`; `AFTER_RUN = "O1-O6"` (the start-scoped olds' `after.run`, 4.5);
  `RUN_U_PER_TICK` / `STALE_TICKS` O6's (the derived slack, 180 u); `ENGINE_RADIUS = 120` (`SetObjectLogicalSize(30, 35,
  50)`'s size x 4, DoEventCode.cs:1531 `component1.radius = size * 4`: every O7 player entry's, 4.14 -- the wall
  push-out's radius; the second operand, `collRad` 35, is the actor-pair radius); `PRIOR_SEGMENTS` (the frozen
  predictions O7-KEYS composes, in segment order: `o1_predictions_v4.json`, `o2_..o6_predictions_v1.json`, 4.5);
  `H4_TOLERANCE = KEEPOUT_MARGIN_W + PROBE_HAZARD_PAD` (86 u, (h4)).
- `core_ids = ("START", "NO-SC", "CHAIN", "RESIDUE", "WRITES", "NULL", "STABLE", "LANDING", "WALK", "PATTERN", "MASKED",
  "STATE", "JOIN")`; `titles` every check's O7 text (section 5).

**Inherited unchanged** (O6's, O5's, O4's, O3's or O2's): `read_session` (O6's: its A-NAMING cell pass touches nothing
without a naming), `forbidden_check`, `void_asym_check` (O4's (a)-(d) over S13's `[place, sc, visit]` cells), `start_check`
(O3's, data-driven: four residue rows), `no_sc_check`, `span_check` (CHAIN), `residue_check`, `writes_check` (O4's
EXACT), `null_check` / `stable_check` / `join_check`, `masked_check`, `history` / `suppressed`, `fingerprint_extra`,
`build_pins` (O5's machinery over O7's `route_build`), `text_check` (O4's, block 3).

**Overridden:** `draft()` (section 4, `END_FIELD` its one switch, 4.17); `freeze_problems()` (7.3); `offline_extra`
([`text_check7`, `census_check`, `regions_check`, `goals_check`]); `build_check` (O6's form, O7's route line);
`keys_check` (O2's machinery on the chain, the writes, the error path, forbidden and dead sites, `start_first`; then
`start_music` one writes key, the start-scoped olds (`after.old` from O6's frozen pattern: `olds_from_pattern`), the
`start_reads`, THE CARRIED VALUES (`carried_from_segments`, equal to the typed ones, none in `end_state`, none written
or read on the route), the route pins, the player-entry and party scans, the monologue's and Dojebon's tests read off
their pins: 6.1); `route_pins_check` (O7's pins; `route_mes` moves to O7-TEXT);
`text_check7` (O4's block-3 text check, then `route_mes`); `census_check` (`store_census7`); `regions_check`
(`regions_problems7`); `goals_check` (O2's base, then `goals_extra7`); `preflight_extra` (O5's -- `C5.O5Segment
.preflight_extra`: no P-NAME, decision 7); `capabilities` (O6's shape over O7's `ROUTE_DONORS`); `why_void` (O5's: A-START
scoped to visit 1 -- 154 -- plus a `start_reads` site read with another `old`: 4.5, 5.1; no A-NAMING); `start_run` (rev.
2: `self.reseed(g, pred)`, then the Segment's -- New Game, the trace, the raw warp); `reseed(g, pred)` (`g.forget_basis(
*seeded_fields(pred))`: every run seeds and judges its own first moves, 0.2 #20; o7_rehearse's untraced F-PASS calls it
before its warp too); `drive` (O4's, plus `observe=static_watch(pred, log)`: 4.11); `core_checks`;
`landing_check`, `walk_check`, `pattern_check` (O6's `pattern_diff6` with `floating` []), `state_check` (+ the trace's
end state); `report_extra` (5.4); `add_arguments` / `handle` (`--draft`, `--rehearsal-report`).

**Module functions** (pure unless named a reader): `ROUTE = VISITS = (154, 158, 159, 160, 162, 163)`, `END_FIELD = 164`
(the fallback flips it to 163: 4.17), `ROUTE_DONORS = ROUTE + (END_FIELD,)`; `route_members(members)` /
`route_members_line` (O6's shape over `ROUTE_DONORS`); `closures154(mesh)` (the two closure lists DERIVED from their
definitions on stock 154's open tris -- step 0: every ground tri (centroid PSX y > -150) whose XZ overlaps a non-ground
tri (shrunk 2% toward the centroid so shared edges do not count), plus every non-ground tri with centroid x > 450 and
z > -3250; step 1: every non-ground tri; expected 119 and 134, equal to `reconcile/closures154.json`); `instanced_at7(idx,
entrance, *, items=None)` (0.2 #3); `store_census7`; `regions_problems7`; `goals_extra7`; `monologue_test(text)` (the
trigger and its guard read off 159 e16 t1 ip390's pinned text: `{"any_of": {"x_lt": -1600, "x_gt": 1600, "z_lt": 800},
"unless_bit": 3796}` from `f[0] const(63936) B_LT`, `f[0] const(1600) B_GT`, `f[2] const(800) B_LT`, `Bit[3796] const(0)
B_EQ`, 2-byte constants signed; None for any other shape); `dojebon_test(text)` (`{"within": 3600, "latch": "Map.Byte[30]
== 1"}` off 154 e5 t1 ip263); `seeded_fields(pred)` (every place whose cell holds a step with `basis` "prior", and each
member whose donor is one: 154, 158, 160, 162, 163 and 31246, 31250, 31252, 31254, 31255); `carried_from_segments(
preds, *, writes)` (4.5's derivation over `PRIOR_SEGMENTS`, less the targets `writes` names); `olds_from_pattern(pred6,
targets)` (the `new` of the last tuple on each target in O6's frozen `pattern` visits, in order; a target with a
floating tuple refused); `release_zone(mesh, closures, placement, within)` and `hazard_residual(...)` ((h4));
`visit_windows(rows, pred)` (5.3 WALK (c)); `static_watch(pred, log)` (keyed by PLACE: one `seen` row per visit -- the
first reading of the watched sid, frame, x, z -- and one `moved` row the first time a reading leaves it by more than
`tol`; no reading in a visit is UNOBSERVED in the report, 4.11); `trace_summary(rows, pred, ...)` (O6's shape, O7's
crossings: each route place's chain row -> the next field row, 163 ip227 -> the cut; the monologue's rows and gap;
Byte[13]'s last pre-cut row); `rehearsal_report(run_dir)`; `run(g)`; `main(argv)`.

### 1.4 The regression gate extended to O6 (`segment_regress.py`)

The implementer extends the gate and captures its O6 baseline FIRST (A0), before any shared-code change. The O6 items
import only O6's modules (`o6_steiner`, `o6_dryrun`) inside their functions.

`O6S = C:\gd\Dream-World-IX\.harness-runs\20261004-110827-story-o6`, `V1_O6 = HERE / "o6_predictions_v1.json"` (sha256
`6ec3aea8...`), `O6S_VERDICT = "PROVEN"`, `O6S_CHECKS = 19`, `O6_OFFLINE_CHECKS = 6`.

| Item | Check |
|---|---|
| G0''''' | `py studies/story-trace/segment_regress.py --capture-o6` writes `research/o6_regress_baseline.json` (LF, `-text`): the full `(checks, report)` of O6S with V1_O6; every `o6_dryrun` session case's `(checks, report)` and "predictions-changed"'s; every unit's `(name, ok, detail)` (`units(...)` then `listed_units(...)`, in `run_cases`'s order); `O6.offline_check(V1_O6)`; the tests G32 collects; the HEAD and V1_O6's sha; and `sources`: the AST sha of every test G32 collects and of every function in `FAKE_PINS_O6` -- only names none of the O3, O4 and O5 baselines pins (`o6_pin_names` refuses one pinned in any). It refuses an existing file, refuses unless G32, G33 and G34-G37's baseline-free halves pass, and takes TWO readings first, refusing when they differ after every temporary root reads `<tmp>` (G0''''s rule). |
| G34 | `O6.analyse(O6S, pred_path=V1_O6)`: the report equals `(O6S/"o6_report.txt").read_text(encoding="utf-8")` exactly and the baseline's; the checks the baseline's; PROVEN with 19 checks, all True. |
| G35 | `py studies/story-trace/o6_steiner.py --analyse O6S --predictions V1_O6` exits 0 and prints that report (`PYTHONIOENCODING=utf-8`: O6's pages quote curly quotes). |
| G36 | Every `o6_dryrun` session case's `(checks, report)` and unit's `(name, ok, detail)` byte-equal to the baseline's (each temporary root `<tmp>`), and `o6_dryrun.run_cases(V1_O6)` returns 0 printing "164/164 cases as registered" (N from the replica). G36 IS O6'S VOID-PATH BASELINE: story-o6 holds six covered runs. |
| G37 | `O6.offline_check(V1_O6)` equals the baseline's `[(ok, what, detail)]`: 6 checks, all PASS. |
| G21 (extended) | THE SOURCE PINS over the UNION of the O3, O4, O5 and O6 baselines' `sources` (`PIN_BASELINES = ("O3", "O4", "O5", "O6")`; `union_sources(*sources)` refuses a name in two, pair by pair; a call with three baselines reads exactly as today, so O5's pinned `test_segment_regress_o5_pins_join_the_union` passes unedited); `--rebaseline-source NAME` looks NAME up in any of the four (`--baseline-o6` on the CLI). |
| G38 (from B4) | `pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o7_ or fake_level or fake_monologue or fake_patrol"` (`PYTEST_K_O7`): all passed, 0 failed, 0 skipped, 0 errors; every name in `REQUIRED_TESTS_O7` among them. No baseline: the list is the floor. A member of THE union run (`PYTEST_ITEMS`). |
| G39 (from C2) | `o7_dryrun.run_cases` on the frozen O7 predictions once they exist, else the draft, AND on `o7_dryrun.as_if_frozen(draft)`: each returns 0 printing "N/N cases as registered", the same N, at least `O7_DRYRUN_FLOOR` (the count C2 prints). |

`FAKE_PINS_O6` (the fake functions O6 added or edited -- its own H16-H18 -- by qualified name, the rule FAKE_PINS_O4 /
FAKE_PINS_O5 followed): `FakeGame._enter_regions`, `FakeGame._step_world`, `FakeGame._step_exit_now`,
`FakeGame._exit_open`, `FakeGame._walkout_of`, `FakeGame._step_walkout`, `FakeGame._check_soft_reset`, `_door_knobs`,
`_VisitBeat._naming`, `_VisitBeat._naming_keys`, `_VisitBeat._door`, `_VisitBeat._walk_out` (the four `_VisitBeat` methods
did not exist at the O5 capture, so no baseline pins them yet; `o6_pin_names` refuses any that one does). `_move_to`,
`_step_walkers` and `_region_at` stay unpinned (no segment added them); O7's edits to them are proven neutral by the two
replays (3.7) and by G26/G32's real-floor tests.

**The registry** (`ITEM_ORDER`, `SEGMENT_ITEMS`, `PYTEST_ITEMS`) grows in three commits: A0 inserts G34-G37 before G21 and
files them under "O6"; B4 adds G38 (`PYTEST_ITEMS["G38"]`, `SEGMENT_ITEMS["O7"] = ("G38",)`); C2 adds G39 (`"O7": ("G38",
"G39")`). `test_segment_regress_items_are_g1_to_g33_once` pins that registry contract, which this change legitimately
extends: A0 RENAMES it `test_segment_regress_registry_holds_every_item_once` (its name says what it pins, not a range --
`REQUIRED_TESTS` updated in the same commit; no baseline pins it, so no G21 row) and each of A0, B4 and C2 updates its
body: `ITEM_ORDER` holds G1 to G37 / G38 / G39 each once, G21 last; no item under two segments; the pytest items G7, G12,
G13, G19, G26, G32 (and G38 from B4) with their selections; `select_items((), ["O6"]) == {G32 .. G37}`; `["G40"]`,
`["O8"]` and `["g7"]` refused. Break: drop an item from `ITEM_ORDER`.

`_missing()` gains O6S's session and report, V1_O6, the O6 baseline (`o6s`), and from C2 the frozen O7 predictions or
O4's `campaign.toml` (`o7`). Tests O7 adds named `test_segment_*` join `REQUIRED_TESTS` (G7); every `test_o7_*`,
`test_fake_level_*`, `test_fake_monologue_*` and `test_fake_patrol_*` joins `REQUIRED_TESTS_O7`. No O7 name holds "o6_",
"fake_naming", "fake_door", "o5_", "fake_visit", "o4_", "o3_drive", "o2_", "o1_" or "rehearse" (O7's rehearsal tests are
`test_o7_rehearsal_*`). Test (A0, into `REQUIRED_TESTS`; it holds "o6_", so G32 collects it and the O6 baseline pins it,
O5's precedent): `test_segment_regress_o6_pins_join_the_union` (pure: G21's checker over four baselines on temporary
copies -- an edited pinned O6 test FAILS naming it; a re-baseline row for an O6-baseline name passes; a name pinned in
two baselines is refused at capture and by the union).

---

## 2. The drive

### 2.1 The model (keys the driver reads; the rest of the predictions is the analysis's)
- **`table`**: six visit-scoped cells (S13), one per walked visit (2.4); control anywhere else -- 154 before its grant,
  any field after its cell's last step, 164 before rule 1 -- is V4 (game) at `[place, 1190, visit]`.
- **`naming`: []**, **`battles`: []** (any battle V10), no `movies`, no `guard`, no `chanbara`.
- **`stop_pages`**: `[{"match": "Env Play()", "why": "window 56 of 154 (e0 t0 ip487), 158, 159, 160, 162, 163: Byte[13]/[14]
  arrived 2 or 9"}]`.
- **`choices`**: O1's skip net only (`{"donor": null, "sc": null, "match": "want to skip", "pick": "default", "once":
  false, "beat": null}`); no choice is on the route; any other is V1 (game).
- **`witness`** (S12): `{"input_every_s": 0.05, "why": "a walk is the driver's own input: outside input would move him
  where the walk did not (a step's evidence, a door) -- the run-wide witness VOIDs a run that sees input (V13)"}`.
- **`route` / `visits`: [154, 158, 159, 160, 162, 163]`, `end_fields`: [164]`, `side_ends`: {S: [164], F: [31256]}**;
  `regions` (4.15): the landing judge reads role `exit` (14 regions), `avoid` reads the hazard too.
- **`budget`** with `end_row_s` (rule 1 waits for 164's first row) and `settle_s`.

### 2.2 The driver loop for O7 (O6's rules in O6's order; nothing new in the loop)
Rule 1 (the end: real 164 on S, member(164) 31256 on F; the live end state, the last scan, the end row); the stall
watchdog; rule 2 (on F a real field a member forks is V19, game: real 154 or 158-164 -- a route `Field()` the chain did
not retarget, which crossed() reads as the landing in `to`'s place; else V11 by `stray()`; a WRONG door's landing never
reaches rule 2 -- crossed() returns V11 (driver) for any landing whose place is not `to`, segment_drive.py:2638-2645, a
real 153/155/156/161/167 on F included); rule 3 (the visit order 154 -> 158 -> 159 -> 160 -> 162 -> 163; a revisit of an
earlier place is out of order: V11); rule 5 (a tutorial or a battle: V10); rule 6 (only the skip net); rule 7 (a page:
the stop page V5 -- the driver's in visit 1 (154: the warp's start state), the game's after -- else Confirm: 159's five
monologue pages); rule 8 (control held, settled: the cell's next step -- the `walk` kind included, S17); rule 9 (fades,
loads).

### 2.3 Every research beat, and what handles it

| # | Field | Beat | Handled by |
|---|---|---|---|
| 1 | 70 -> 154 | the raw warp; residue SC bytes 0-1, FieldEntrance bytes 2 (0 -> 59) and 3 (0 -> 1) | `start_run` (O2's); O7-START (a) expects FOUR rows |
| 2 | 154 | Main_Init at 315: the prologue (ip26 THE START ROW; ip123 from old 1), L392 (InitObject 15/5/6/7, regions 9/10/8, code 11), Steiner placed on the balcony (tri 250, PSX -1716), ip588 EnableMove | rule 8 after the settle |
| 3 | 154 | step 0, `walk`: balcony -> west flight -> stair top -> central flight -> the ground at (0, -600); e11's camera switch (visual) | S17 (2.4) |
| 4 | 154 | step 1, `cross` e8 on the ground: ip38 false -> ip211 ExitField -> 25 ticks -> ip355 `:= 300`, ip363 `Field(158)` | O2's cross (crossed(): the landing in 158 / 31250) |
| 5 | 158 | prologue (ip57 -1 -> 385, ip130 0 -> 1), ip379 grant, ip445 `Byte[13]` 1 -> 2 in the grant's pass | nothing; rule 8 |
| 6 | 158 | cross e2: ip194 `Byte[13]` 2 -> 3, ip222 `:= 331`, `Field(159)` | cross |
| 7 | 159 | prologue (385 -> -1, ip119 3 -> 0), ip290 `Byte[8]` 125 (same), ip665 grant at (7, 3870) inside the monologue box | rule 8 |
| 8 | 159 | cross e11, interrupted once at x ~-1600 by THE MONOLOGUE: pages 296-300, ip613, ip648, ip672, re-grant ip711 in place | crossed() `interrupted`; rule 7 x5; rule 8 re-runs the step (2.5) |
| 9 | 159 | the re-run crosses e11 (ip193 `:= 332`, `Field(160)`) | cross |
| 10 | 160 | prologue, ip399 grant 61 u west of e4, ip465 1 -> 2; cross e5 (`:= 333`, `Field(162)`) | rule 8, cross |
| 11 | 162 | prologue (ip130 2 -> 1), ip866 grant 50 u north of e2, ip932 1 -> 2; cross e3 (`:= 341`) | rule 8, cross |
| 12 | 163 | prologue, ip618 grant 73 u from e3, ip684 1 -> 2; cross e2 up the stair through the foot (`:= 342`, `Field(164)`) | rule 8, cross at clearance 110 |
| 13 | 164 | THE END: e0 t0 ip22 (31256 on F), the cut row; 164's prologue races Byte[13] | rule 1 per side; Byte[13] from the trace (4.9) |

### 2.4 The cells (each `{"donor", "sc": 1190, "visit", "steps"}`; `steps_default` O6's, `npcs` true)

| Cell | Grant (bytes; REHEARSE) | Steps | Keys beside goal / target / to | Why |
|---|---|---|---|---|
| (154, 1190, 1) | Main_Init ip588 at (-58, -3758), facing 128, balcony tri 250 PSX -1716 (published y ~1716) | #0 `walk` "154: the balcony, the west flight, to the ground", goal (0, -600), `start` (-58, -3758) | `avoid` [154.e8, 154.e9, 154.e10, 154.hazard.dojebon]; `closed_tris` the 119 (`closures154`); `clearance` 120; `basis` "prior"; **`attempts` 3**; beat `w154_ground` | the only way down is the west flight, the stair top and the central flight (the engine's neighbour links: the research's `wm154.out`); the goal disc is single-level ground (0.2 #7); no probe in 154 (0.2 #11); the arm and the flight are 283-356 u wide, where the blocker rung seals the way: a failed attempt re-plans fresh (0.2 #17) |
| | | #1 `cross` "154: the south door, ground branch", goal (0, -4500), target 154.e8, to 158, `start` (0, -600) | `avoid` [154.e9, 154.e10]; `closed_tris` the 134; `clearance` 120; beat `x154_e8` | every open tri of this floor inside e8 is ground: the fire is the ground branch (0.2 #7) |
| (158, 1190, 2) | ip379 at (0, -12787), facing 0, tri 38 PSX -268 | `cross` "158: the south door", goal (-17, -16444), target 158.e2, to 159, `start` (0, -12787) | `avoid` [158.e1]; `clearance` 120; `basis` "prior"; beat `x158_e2` | e1 (300 u north) is a live back door |
| (159, 1190, 3) | ip665 at (7, 3870), facing 0, tri 220 PSX -512 | `cross` "159: the west door (the forced monologue on the way)", goal (-2910, -300), target 159.e11, to 160, `start` (7, 3870) | `avoid` [159.e10, 159.e12]; `interrupts` 1; `clearance` 120; NO `basis` (calibrated: its probes stay inside the box, x within +-300, z >= 3570); beat `x159_e11` | the monologue is the step's one interruption (2.5) |
| (160, 1190, 4) | ip399 at (1357, -4063), facing 60, tri 1 PSX 0 | `cross` "160: the stair door", goal (-313, -813), target 160.e5, to 162, `start` (1357, -4063) | `avoid` [160.e4]; `clearance` 120 (removes the 85-u corner); `basis` "prior"; beat `x160_e5` | e4 61 u east: the first leg heads west |
| (162, 1190, 5) | ip866 at (957, -3800), facing 128, tri 40 PSX 0 | `cross` "162: the north door", goal (1001, 406), target 162.e3, to 163, `start` (957, -3800) | `avoid` [162.e2]; `clearance` 120; `basis` "prior"; beat `x162_e3` | e2 50 u south: the leg heads north |
| (163, 1190, 6) | ip618 at (690, 2195), facing 128, tri 76 PSX -7 | `cross` "163: the stair top", goal (997, 4957), target 163.e2, to 164, `start` (690, 2195) | `avoid` [163.e3]; **`clearance` 110**; `basis` "prior"; **`attempts` 3**; beat `x163_e2` | no route at 120 (0.2 #5): the engine squeezes him through the 233-u pinch (0.2 #12, H21, R-STAIR); the stair is at most 393 u wide, where the blocker rung seals the way (0.2 #17) |

THE BASES, PER RUN (0.2 #20): a basis is cached per field id (S and F apart: 154 vs 31246), and O7's `start_run`
forgets every seeded field's (`seeded_fields`: 154, 158, 160, 162, 163 and their members) before each run's New Game,
so every run seeds each one and judges its first move (O7-WALK (d)); within a run 154's step 1 uses step 0's. 159's
basis is CALIBRATED once a launch per side and cached after (O2-O6's practice: its probes stay inside the box, and
the fewer the better). `attempts` 3 on 154 #0 and 163 #0 (every other step O6's 2): a stall that outlasts the waits
and the push in those corridors ends the attempt (0.2 #17), and the next attempt is the fresh re-plan from where he
stands; O7-WALK (a) allows `attempts` - 1 `failed` rows per step. Every cross is O2's (crossed(): done on the landing
in `to`'s place; a landing elsewhere V11 driver; a loss in another exit its switch waited out; a loss in no exit
`interrupted`). `TRIGGER_WAIT_S` plays no part (no trigger step).

### 2.5 159: the forced monologue (cell (159, 1190, 3))
- The cross presses from (7, 3870) toward (-2910, -300); the first tick his x < -1600 (z ~1573 on the line), e16 t1
  ip390 holds: ip445 DisableMove. `route_to` (handoff) returns with `lost` at the first read without control; crossed()
  finds it in no exit (e11's nearest point is 600+ u on) and returns `interrupted` (segment_drive.py:2627-2631):
  `tries.interrupted` 1 <= `interrupts` 1.
- Rule 7 Confirms 296 (Async), 297 (WindowSync: a first Confirm may drop -- lesson 11; rule 7 presses again), 298, 299
  and 300; the script writes ip613 and ip648 while 300 is up and ip672 after it closes; ip711 EnableMove where he stands.
- Rule 8 settles and runs step 0 again (its done count still 0; the basis cached): from ~(-1601, 1572) a straight 2284 u
  to the goal, entering e11 at ~(-2445, 365): done on the landing in 160 / 31252.
- A second interruption is V7 (driver). The monologue's rows are fixed values written with control off: THE PAIRED-WALK
  LAW holds (O7-WALK (c) checks they lie between the two attempts and nowhere else).

### 2.6 The arrival in 164 (the end per side)
Rule 1 fires on its first poll in 164 (31256 on F): the end state read live WITHOUT Byte[13] (4.9), the last forbidden
scan, the end row (164's first trace row, e0 t0 ip22, waited up to `end_row_s`). Nothing is pressed after rule 1;
Steiner's control in 164 (ip698) is never read. `end_run` then warps to 4600 from 164's FieldHUD.

### 2.7 VOID conditions (each a RouteVoid with its class, cell and attribution; the run is not covered)

| | Condition in O7 | by |
|---|---|---|
| V1 | A choice no rule matches (none is on the route). | game |
| V4 | Control held where no cell's step is due: 154 before its grant, any field after its cell's last step done. | game |
| V5 | The stop page ("Env Play()"), nothing pressed. | driver in visit 1 (154: the start state); game after |
| V7 | A step out of attempts (2; 3 on 154 #0 and 163 #0) or interruptions (1): 163's squeeze stalled three times; a second monologue. | driver |
| V10 | A naming screen, a tutorial, a battle. | game |
| V11 | Off the route or its order (rule 2's `stray()`, rule 3); a cross landing in another place (154's balcony branch -> 153 / 31245; e9 / e10 -> 155, 156, 167 or their members, or a REAL one on F; a back door); the walk leaving the field; a loss in another exit that lands. | driver after a walk (crossed(), strayed, door_loss, `stray()` on the walked row); game otherwise |
| V12 | A forbidden write the driver's own log backs. | driver |
| V13 | The budget; an instrument stop; outside input (S12); THE PRIOR BASIS disagreeing with the first move (S19). | driver |
| V14 | The watchdog alone (e.g. control never re-granted after the monologue). | game |
| V19 | On F, a REAL field a member forks reached on the route: 154 or 158-164 (a route `Field()` the chain did not retarget: crossed() reads the landing as `to`'s place, rule 2 judges it). A FINDING (`rerun.stop_on`). A real 153 / 155 / 156 / 161 / 167 on F is a WRONG door's landing: V11 (driver) by crossed() first, `landed` the real id, named in the report -- O7-BUILD and P-EB prove those doors' `Field()` retargeted offline. | game |

Every cell is `[place, sc, visit]` (S13): V4 / V5 / V7 / V11 / V13 inside a visit `[its place, 1190, its visit]`; V19 on a
landing `[place(landing), 1190, the visit just left]` (rule 2 runs before rule 3 counts the visit). V2, V3, V6, V8, V9,
V15-V18 cannot arise (no guarded or default-take choice, no watched cell, no wait_sc or climb, no battle, no fight, no
guard).

### 2.8 Recovery
- **From 164** (every covered run), **mid-walk** (any field, control held) and **mid-monologue** (a page up, FieldHUD):
  `end_run` warps to 4600 from FieldHUD, then the ladder -- O5's and O6's path; R-WALK-VOID proves both stops (F9).
- **The session's end** goes through `end_run` (`end_session_warps`), recorded in `session["ended"]`.

---

## 3. Harness additions (FakeGame only; each opt-in, modelled on the bytes, tested)

No change to `channel.py` or the agent. What is missing is a fake that (a) keeps a player on ONE LEVEL of a stacked mesh
and publishes his height (154's balcony over the ground); (b) lets him through a pinch a few units narrower than twice
his radius the way the engine's averaged pushes do (163's foot: 233 u against 2 x 120); (c) runs a door's tag 2 per
height branch and an object's one-shot scene with its pages and an in-place re-grant (154's e8, 159's monologue); (d)
holds a patroller on a distance-and-latch test (Dojebon); and (e) plays O7's route. Each knob's default is today's
behaviour; each choice cites the byte or engine line it stands for.

### 3.1 H20 -- LEVELS (`fake.levels`, `Levels`, `place_height`; PART B, B1)
`fakegame.Levels(wmesh, *, step_dy=LEVEL_STEP_DY, band=LEVEL_BAND, squeeze_slack=None)` over a kit walkmesh (a
`PlayerWalkmesh` or a `BgiWalkmesh`: its open tris, its world verts in PSX y, up negative):
- `tri_under(x, z, h)`: among the open tris containing (x, z) (`mesh.tris_at`), the one whose interpolated height is
  NEAREST `h` and within `step_dy` of it, else None. THE ENGINE: the actor stays on its active triangle and crosses only
  a shared edge to a neighbour (the walkmesh traversal; `wm154.out`'s finding that 154's balcony meets the stairs only
  at tris (289, 292) and (189, 190) and the stairs meet the ground only at x -477..482, z -245..-125 is that graph); a
  placement lands on the nearest-height tri (GetTriIdxAtPos, FieldMapActorController.cs:1279-1306). Nearest-within-step
  is that graph wherever stacked levels lie more than `step_dy` apart and a step changes height by less (B1's premises
  test proves both on 154 and 163).
- `height(ti, x, z)`: the interpolated PSX height on tri `ti`.
- `wall_gap(x, z, h)`: the XZ distance from (x, z) to the nearest WALL of his level -- an edge of an open tri with no open
  neighbour (PlayerWalkmesh's rule, pathfind.py:744-754, per triangle), kept when its height at the nearest point lies
  within `band` of `h`; None when `tri_under` is None. (A floor index mixes levels in 154: 0.2 #7.)
- `LEVEL_STEP_DY = 200.0` (a 60-u tick step on 154's steepest open tri -- tri 205 on the west flight, 52.8 deg --
  changes height by 79.1, on 163's by 63.0: 0.2 #17; the first draft's "~40" was wrong; the levels stack 1711 apart);
  `LEVEL_BAND = 400.0` (the engine's own "same level" pairing band, WalkMesh.cs:922, used here as the stand-in for "his
  own surface"; sound while stacked levels are more than 2 x 400 apart).

`fake.levels: dict[int, Levels] = {}` (default empty: today's fake). `_move_to` (unpinned) takes a level branch when the
current field has an entry: the existing clearance logic (fakegame.py:1491-1528) with `wall(px, pz)` =
`levels.wall_gap(px, pz, h)` and the floor test `levels.tri_under(px, pz, h) is not None`, `h` = -`player[1]` (his
height: `f[1]` = -`pos[1]`, EBin.cs:1791; the agent publishes `pos[1]`, HarnessAgent.cs:1559); after the step
`player[1]` = -`levels.height(tri_under(x, z, h), x, z)`. `fake.clearance` is required under levels (ValueError
otherwise). Everything else in `_move_to` (bodies, the lock) is today's; the bodies' and contacts' |dy| band already reads
`player[1]`.

`FakeGame.place_height(x, z, h)` (new): with a level entry for the field, `player[1]` = minus the height of the open tri
under (x, z) nearest `h` (no `step_dy` bound: a placement, GetTriIdxAtPos); without, `player[1]` = -`h`.
`_VisitBeat._place` (an O5 pin) accepts `[x, z]` (today's: y untouched) or `[x, z, h]` -- `h` the PSX y operand of the
bytes' MoveInstantXZY (154 e15 t0 ip2827, `Map.Int16[2]` = -1741 from the SWITCHEX default) -- and calls `place_height`;
`_visit_steps` (an O5 pin) refuses a `place` or `grant` payload that is not two or three numbers. Both are re-baselined
by name in B1's commit with their reasons; both replays (3.7) read identical.

Tests (B1; `REQUIRED_TESTS_O7`; the real-mesh ones read the install -- the `dali` fixture's warned skip fails G38):
`test_fake_level_meshes_hold_the_levels_premises` (stock 154 and 163: every neighbour pair of open tris shares its edge's
heights; the largest height change of a 60-u step along any open tri is MEASURED and printed -- 79.1 on 154 (tri 205),
63.0 on 163 (tri 134) at the design -- and asserted under `LEVEL_STEP_DY`; 154's stacked open tris lie 1711 apart, over
2 x `LEVEL_BAND`; should a steeper open tri exist, `LEVEL_STEP_DY` is raised -- still under half the separation -- and the
commit says why); `test_fake_level_places_steiner_on_the_balcony` (grant `[-58, -3758, -1741]`: published
y 1716 -- tri 250 -- not the ground's 5; break: `place_height` taking the first tri); `test_fake_level_never_drops_off_the_
balcony_edge` (presses north off the balcony's north edge over the courtyard: he stops on the balcony, y 1716, never 5;
break: nearest height without `step_dy`); `test_fake_level_walks_the_west_flight_down_to_the_ground` (scripted presses
along step 0's planned waypoints at clearance 120: y falls 1716 -> ~5 in steps of < 200, he reaches (0, -600) on the
ground; break: walls of every level -- the balcony's edge stops him on the ground below it); `test_fake_level_place_height_
without_levels_sets_y` (a box floor: `[x, z, -1741]` publishes y 1741, `[x, z]` leaves y as it was).

### 3.2 H21 -- THE SQUEEZE (`Levels(squeeze_slack=...)`; PART B, B1; rev. 2: driver review #5)
With `squeeze_slack` set, a step whose end can keep neither `least` (today's never-closer rule) nor any slide bearing is
placed on the point of the LARGEST wall gap within `fake.clearance` of its end across the step's direction (the
corridor's midline: where the opposing pushes average out -- RadiusValid pushes each wall's force out to the
controller's `radius`, ServiceForces averages several x 1.05, FieldMapActorController.cs:1060-1254) and kept when that
gap is at least `fake.clearance - squeeze_slack`; otherwise today's rule (he stops). The bound is the RADIUS's: the push
is the controller's `radius` = size x 4 (DoEventCode.cs:1531; 120 for Steiner), so the fake passes a pinch the engine's
averaging plausibly passes -- a few units under the radius a side -- and never a slot the radius cannot fit. (The first
draft took `collRad` 35, the actor-pair radius (FieldMapActorController.cs:781): it would have let him through a 70-u
slot.) `SQUEEZE_SLACK_W = 8.0`: an ESTIMATE over 163's measured 3.3-u overlap (0.2 #12) that R-STAIR measures (F5); a
NO-GO there is the fallback end, never a wider slack. Test (B1): `test_fake_level_squeeze_passes_the_stair_foot` (stock
163, `fake.clearance` 120, `squeeze_slack` 8: a press up the foot from (2098, 3731) toward (2098, 4115) passes the 116.7
pinch and stops at the mouth without `squeeze_slack`; a flat box corridor pinched to a best clearance of 100 stops him
WITH it; break: the midline point taken without the bound -- the 100 pinch passes).

### 3.3 H22 -- THE DOOR'S HEIGHT TERMS AND SCENES (`_door_knobs`, `_VisitBeat._door`; PART B, B2)
- **Height terms**: `DOOR_KEYS` += `"y_gt"`, `"y_le"` (numbers, checked by `_door_knobs`); `_door`'s hit test adds
  `published y > y_gt` / `<= y_le` beside `z_gt`. 154's e8 is two doors with one polygon, in entry order: the balcony
  branch `{"y_gt": 100, stores [e8 t2 ip195 Int16[2] := 301], "to": "153"}` and the ground branch `{"y_le": 100, stores
  [ip355 := 300], "to": "158"}` -- tag 2 ip38 `f[1] < -100` is published y > 100 (0.2 #8); e9 and e10 the same shape.
- **Scenes**: `DOOR_DEFAULTS` += `"scenes": ()`; a scene is `{"name", "any_of", "unless_bit", "steps", "regrant"}` --
  `any_of` a dict of `x_lt` / `x_gt` / `z_lt` / `z_gt` (ANY holding fires: ip390's B_OROR), `unless_bit` the
  gEventGlobal bit whose 1 disarms it (ip390's `Bit[3796] == 0`, read from the fake's story bytes), `steps` visit steps
  (`_visit_steps` checks them: pages, stores, waits), `regrant` "in_place" (ip711 EnableMove with no Walk; the only form).
  Each field tick he has control, `_door` tests the doors (entry order: 159's regions e10-e12 precede Steiner's e16, and
  ProcessEvents runs objects by entry), then the scenes in order: an armed scene whose `any_of` holds FIRES -- control
  off (ip445), a `visit_log` row "scene" (name, x, z), its steps (`_run`), then control back where he stands, `_coast`
  None -- and the door loop goes on. A scene whose own steps store its `unless_bit` (ip672) cannot fire again.
- The 159 scene's steps, from the bytes: pages 296, 297, 298, 299 (slot 4), stores ip613 `Byte[208] := 0` and ip648 `:= 1`,
  page 300, store ip672 `Bit[3796] := 1` -- ip613/ip648 run while 300 is up (ip602 is WindowAsync): the fake writes them
  just before it opens, the same row order and the same gap (between the loss and the re-grant).
`_door_knobs` and `_VisitBeat._door` are O6 pins from A0's capture: re-baselined by name in B2's commit; both replays
identical. Tests (B2): `test_fake_level_door_branches_by_height` (in e8's polygon at y 1716 the balcony door fires and
stores ip195; at y 5 the ground door and ip355; break: drop the y terms -- the first door fires at both heights);
`test_fake_monologue_fires_once_outside_the_box` (from (7, 3870) pressing west: the scene fires the first tick x < -1600,
control off, pages 296-300 listed in turn, the three stores in order, control back at the same (x, z); pressing on, it
never fires again; break: no `unless_bit` -- it fires on every tick outside the box); `test_fake_monologue_store_override_
fires_it_again` (H15's `store_override` {672: 0}: Bit[3796] stays 0 and the scene fires again at once after the
re-grant); `test_fake_monologue_regrants_in_place` (the re-grant's sample equals the fire's; break: a re-grant at the
scene's start point).

### 3.4 H23 -- THE HELD WALKER (`blockers` key `hold`; PART B, B2)
A walker body (`path`, `speed`) may carry `"hold": {"within": r, "latch_below": y1, "unlatch_above": y2, "at": [k, ...]}`:
at a path index in `at` it waits while his XZ distance is under `within` OR the latch is set (154 e5 t1 ip263 / ip486:
`B_DISTANCEA < 3600 || Map.Byte[30] == 1`); the latch sets the first tick his published y < `latch_below` (e11 t1 ip14 /
ip33: `f[1] > -600`) and clears at y > `unlatch_above` (ip128 / ip147: `f[1] < -500`); it starts clear (e15 t0 ip2116
`Map.Byte[30] := 2`). Elsewhere on the path he walks without waits (e5 t1 ip316-ip474). `_step_walkers` is unpinned.
Dojebon in the builder: sid 5 at (-2700, -1700), y 1716, `path` 154 e5 t1's Walk operands in order (index 3 his
placement, then (-1600, -1700), (-1600, 120), (-1300, 565), (-527, 777), (0, 777), ... to index 14 -- B3 reads them off the
listing), `speed` from e5's SetWalkSpeed (the critic: 58 u a tick: 29 a 60-fps frame in the fake's units),
`hold` {"within": 3600, "latch_below": 600, "unlatch_above": 500, "at": [0, <index 14's>]}, `r` and `talk_r` from his
entry's size (radius 4 x the first SetObjectLogicalSize operand). Tests (B2): `test_fake_patrol_holds_within_its_circle_
and_its_latch` (he stays put while the player is within 3600; with the player farther but y < 600 he stays; break: no
latch); `test_fake_patrol_released_walks_its_path` (the player at 3700 u on the balcony: he walks to (-1600, -1700)).

### 3.5 H24 -- O7's faults (reused, each absent by default)
`store_override` ({672: 0}: the monologue again -- V7), `land_real` ({"158": id}: V19), `door_misroute` ({door name:
field_to key}), `error_window` ({1: 2}: 154's stop page -- V5 driver; {2: 2}: 158's -- V5 game), `grant_at` ({index: [x,
z]}: control where the bytes grant none). Test-side, not knobs: a released Dojebon (no `hold`), a wrapped `g.send` (R-WALK-
VOID's mid-walk stop), a wrapped `g.press` (its mid-monologue stop), a rotated prior (S19).

### 3.6 The O7 route builder (test-side `_o7_route(side, *, short=None, levels154=False, wait_scale=0.25, **faults)`)
Seven visit beats from the bytes. Fixture fields `_O7_FIELDS`: S {"154": 30840, "158": 30841, "159": 30842, "160": 30843,
"162": 30844, "163": 30845, "164": 30846, "153": 30850, "155": 30851, "156": 30852, "161": 30854, "167": 30853}, F {"154":
31246, "158": 31250, "159": 31251, "160": 31252, "162": 31254, "163": 31255, "164": 31256, "153": 31245, "155": 31247,
"156": 31248, "161": 31253, "167": 31259}; `_o7_register(game)` (`_o6_register`'s shape) registers the S ids and the F ids
under `_O7_NAMES`; members {F id: its S id}. Floor: `_O7_BOX` (-3800, -18000, 3800, 7000), the planner's `_flat_bgi` over
it. Field 70's prologue values via `_o5_field70` (Int16[9] 643, Byte[13] 1, Int16[11] -1, Byte[14] 0, Byte[8] 125); the
warp's residue by the fake's `_warp_writes(315, 1190)` (four rows).
- **154@315** (index 1): stores e0 t0 ip26, 53, 61 (Int16[9] := -1), 123 (Byte[13] := 0), 142, 204; wait 4; grant
  `[-58, -3758]` (box: the floor-blind fake stands him at y 0, the ground branch's side, as O5's e26 model read the
  ground) or, `levels154`, `[-58, -3758, -1741]` on stock 154's mesh (`fake.levels`); bodies Dojebon (3.4), soldiers e6
  (-1683, -3795) and e7 (1764, -3631) at y 1716 (talk only); door {e8 balcony, e8 ground, e9 balcony (ip195 := 302 ->
  "156"), e9 ground (ip355 := 300 -> "155"), e10 balcony (:= 303 -> "156"), e10 ground (:= 300 -> "167")}, each `ticks` 25.
- **158@300** (2): prologue (ip22, 49, 57 := 385, 130 := 1, 138, 200); wait 4; grant `[0, -12787]`; store ip445 := 2 (the
  grant's pass: no wait between); door {e1 (ip193 Byte[13] := 3, ip221 := 331 -> "154"), e2 (ip194 := 3, ip222 := 331 ->
  "159")}.
- **159@331** (3): prologue (57 := -1, 119 := 0); store ip290 Byte[8] := 125; wait 4; grant `[7, 3870]`; bodies soldiers
  e6 (-2250, 2088), e7 (2250, 2088), Haagen e5 (-10, -1558) at y 79 (talk only); door {e10 (ip193 := 332 -> "158"), e11
  (-> "160"), e12 (-> "161")} with the monologue scene (3.3).
- **160@332** (4): prologue (57 := 385, 130 := 1); grant `[1357, -4063]`; store ip465 := 2; bodies Weimar e2 (-921, -1406),
  soldier e3; door {e4 (ip194 := 3, ip222 := 333 -> "159"), e5 (ip227 := 333 -> "162")}.
- **162@333** (5): prologue (130 := 1 from 2); grant `[957, -3800]`; store ip932 := 2; door {e2 (ip227 := 341 -> "160"),
  e3 (-> "163")}.
- **163@341** (6): prologue; grant `[690, 2195]`; store ip684 := 2; door {e2 (ip227 := 342 -> "164"), e3 (-> "162")}.
- **164@342** (7): stores e0 t0 ip22, 49, 57, 130 (2 -> 1), 138, 200; wait 100000 (rule 1 reads its first poll).
- **Every door's walk-out**, as O6's H18 modelled ExitField: `walkout` {"to": MJPOS's point -- his crossing point
  projected onto the region's FIRST edge, q0 -> q1, clamped to it (CalculateExitPosition, DoEventCode.cs:2247-2275),
  computed by the builder for the planned crossing -- "stop_z": None}: he walks on at 60 u a tick through the door's 25
  ticks (MOVJ at his last controlled frame's speed, FieldMapActorController.cs:210-211). A cross judges only the
  landing (crossed() waits the switch), so no stop estimate is needed; the fake's walk-out does not test the floor.
- `short` = a donor: that visit alone (its cell keeps its visit number: the start place's index in `visits`, O6's rule),
  then the next field's arrival as the stage's end.
The stores are the predictions' sites (C1's `test_o7_castle_route_builder_matches_the_keys`: the builder's stores == the
draft's writes, chain, masked and start rows; its trace's `pattern_of` == the draft's `pattern`).
Test (B3; `REQUIRED_TESTS_O7`): `test_fake_level_route_plays_to_164_unattended` (a SCRIPTED player: every page Confirmed,
straight presses to each step's goal; the monologue fires once; the trace with `story_suppress`: 4.16's 51 rows by ip, no
`c` row, the cut row 164 ip22; break: a builder whose 159 scene has no `unless_bit`).

### 3.7 THE O6 REPLAY (A0b, before any fake edit)
`test_fake_level_keeps_the_steiner_route_identical` (`REQUIRED_TESTS_O7`): O6's builder `_o6_route` (S and F) played BY
HAND with O6's scripted player `_o6_play` on the hand-stepped fake (`_frame_once`, no thread, no wall clock), as
`_o5_replay` plays O5's; the document every frame whose compact sample changed -- `[frame, field, ui_state, control, x,
y, z, [[slot, raw, text], ...], choice]` (y included: H20 must leave it untouched) -- and every trace row, LF JSON. With
`O7_CAPTURE_REPLAY=1` it WRITES `research/o6_fake_replay.json` (refusing an existing file, and unless two captures in
one process are equal); without it, it COMPARES and fails naming the first differing frame; a missing golden FAILS. O5's
replay (`test_fake_door_keeps_the_hallway_route_identical`) runs beside it unchanged.

---

## 4. Predictions (draft v1: `O7Segment.draft()`)

### 4.1 Top level
```json
{"version": 1,
 "what": "O7: 154@1190 (warp, entrance 315; EVT_ALEX1_AC_ENT_2F) -> the balcony, the west flight, the ground, the south door -> 158@300 -> 159@331 (the forced monologue) -> 160@332 -> 162@333 -> 163@341 (the stair foot) -> the arrival in 164 at 342, SC 1190; stock vs the alxc disc-1 chain as O4 deployed it (route members 31246-31256; PLAN.md, O7) -- a US session",
 "rehearsals": [], "rehearsal_fps": [],
 "order": ["S", "F", "S", "F", "S", "F"], "min_covered": 2, "rerun": {"max": 2, "stop_on": ["V19"]},
 "budget": {"run_s": 600, "run_min_s": 300, "session_s": 3600, "settle_s": 1.0, "no_progress_s": 60, "end_row_s": 10.0},
 "start": {"S": 154, "F": 31246}, "entrance": 315, "scenario": 1190, "lang": "us",
 "end_field": 164, "end_fields": [164], "side_ends": {"S": [164], "F": [31256]},
 "route": [154, 158, 159, 160, 162, 163], "visits": [154, 158, 159, 160, 162, 163],
 "stock_fields": [154, 158, 159, 160, 162, 163, 164],
 "members": {"31240": 64, "...": "...", "31259": 167}, "names": {"31240": "O4_AC_AST", "...": "..."},
 "text_block": 3, "text_blocks": [3], "recovery": 4600, "cut_start": true,
 "start_first": "4.5", "start_music": "4.5", "start_scoped": "4.5", "start_reads": "4.5", "carried": "4.5",
 "start_residue": [[0, 0, 166], [1, 0, 4], [2, 0, 59], [3, 0, 1]], "residue_after_start": [],
 "sc_bytes": [0, 1], "ladder": [], "entrance_bytes": [2, 3], "chain": "4.3", "writes": "4.4",
 "start_dependent": [], "naming": [], "error_path": "4.6", "forbidden_sites": "4.6", "dead": "4.6", "inert": "4.6",
 "live_shared": [], "noise": [], "forbidden": "4.8", "landing": "5.3", "end_state": "4.9", "end_state_trace": "4.9",
 "interruptions": "4.10", "static_objects": "4.11",
 "beats": ["w154_ground", "x154_e8", "x158_e2", "x159_e11", "x160_e5", "x162_e3", "x163_e2"],
 "battles": [], "stop_pages": ["2.1"], "regions": "4.15", "hotspots": {}, "table": ["2.4"], "steps_default": "4.15",
 "choices": ["2.1"], "witness": "2.1", "route_pins": "4.14", "route_mes": "4.14", "route_build": "6.1",
 "pattern": "4.16", "settings": "4.13", "override70": "4.13", "derived": "4.13", "engine": "4.13"}
```
`members` / `names` are O4's twenty (`chain_from_campaign`); `route_members` over `ROUTE_DONORS` derives 31246, 31250,
31251, 31252, 31254, 31255, 31256 (printed, never assumed). The draft reads `rehearsals` and `rehearsal_fps` as []: the
lead's freeze fills them (7.3); no test pins either.

### 4.2 No SC rung
No store to SC's bytes in any width in 154-163, and no `UInt16[0]` reference at all (the census, 6.1). O7-NO-SC is O3's
`no_sc_check`.

### 4.3 The FieldEntrance chain (`Global.Int16[2]`; O7-CHAIN; the first `old` is 315, the warp's entrance)

| # | donor | sid | tag | ip | off | value | what |
|---|---|---|---|---|---|---|---|
| 1 | 154 | 8 | 2 | 355 | 325 | 300 | the south door's ground branch, then `Field(158)` ip363 |
| 2 | 158 | 2 | 2 | 222 | 192 | 331 | e2, then `Field(159)` ip230 |
| 3 | 159 | 11 | 2 | 193 | 163 | 332 | e11, then `Field(160)` ip201 |
| 4 | 160 | 5 | 2 | 227 | 197 | 333 | e5, then `Field(162)` ip235 |
| 5 | 162 | 3 | 2 | 227 | 197 | 341 | e3, then `Field(163)` ip235 |
| 6 | 163 | 2 | 2 | 227 | 197 | 342 | e2, then `Field(164)` ip235 -- the last compared row |

### 4.4 Registered writes (O7-WRITES: every covered run's keys are EXACTLY these and the chain)

| donor | sid | tag | ip | off | target | value | op | what |
|---|---|---|---|---|---|---|---|---|
| 154 | 0 | 0 | 61 | 51 | Int16[9] | -1 | := | ambient (from 643: START-SCOPED old) |
| 154 | 0 | 0 | 123 | 113 | Byte[13] | 0 | := | ambient (from 1: `start_music`, START-SCOPED old) |
| 154 | 0 | 0 | 142 | 132 | Int16[11] | -1 | := | ambient (same) |
| 154 | 0 | 0 | 204 | 194 | Byte[14] | 0 | := | ambient (same) |
| 158 | 0 | 0 | 57 | 51 | Int16[9] | 385 | := | ambient |
| 158 | 0 | 0 | 130 | 124 | Byte[13] | 1 | := | ambient (from 0) |
| 158 | 0 | 0 | 138 | 132 | Int16[11] | -1 | := | (same) |
| 158 | 0 | 0 | 200 | 194 | Byte[14] | 0 | := | (same) |
| 158 | 0 | 0 | 445 | 439 | Byte[13] | 2 | := | the grant's pass |
| 158 | 2 | 2 | 194 | 164 | Byte[13] | 3 | := | e2, LIVE (no Map.Bit[162] before it) |
| 159 | 0 | 0 | 57 | 51 | Int16[9] | -1 | := | ambient |
| 159 | 0 | 0 | 119 | 113 | Byte[13] | 0 | := | ambient (from 3) |
| 159 | 0 | 0 | 138 | 132 | Int16[11] | -1 | := | (same) |
| 159 | 0 | 0 | 200 | 194 | Byte[14] | 0 | := | (same) |
| 159 | 0 | 0 | 290 | 284 | Byte[8] | 125 | := | (same: field 70 left 125) |
| 159 | 16 | 1 | 613 | 223 | Byte[208] | 0 | := | the monologue (same here: START-SCOPED old) |
| 159 | 16 | 1 | 648 | 258 | Byte[208] | 1 | ++ (prior 159/16/1/613) | the monologue, one loop pass |
| 159 | 16 | 1 | 672 | 282 | Bit[3796] | 1 | := | the monologue's guard set |
| 160 | 0 | 0 | 57 | 51 | Int16[9] | 385 | := | ambient |
| 160 | 0 | 0 | 130 | 124 | Byte[13] | 1 | := | ambient (from 0) |
| 160 | 0 | 0 | 138 | 132 | Int16[11] | -1 | := | (same) |
| 160 | 0 | 0 | 200 | 194 | Byte[14] | 0 | := | (same) |
| 160 | 0 | 0 | 465 | 459 | Byte[13] | 2 | := | the grant's pass |
| 162 | 0 | 0 | 57 | 51 | Int16[9] | 385 | := | ambient (same) |
| 162 | 0 | 0 | 130 | 124 | Byte[13] | 1 | := | ambient (from 2) |
| 162 | 0 | 0 | 138 | 132 | Int16[11] | -1 | := | (same) |
| 162 | 0 | 0 | 200 | 194 | Byte[14] | 0 | := | (same) |
| 162 | 0 | 0 | 932 | 926 | Byte[13] | 2 | := | the grant's pass |
| 163 | 0 | 0 | 57 | 51 | Int16[9] | 385 | := | ambient (same) |
| 163 | 0 | 0 | 130 | 124 | Byte[13] | 1 | := | ambient (from 2) |
| 163 | 0 | 0 | 138 | 132 | Int16[11] | -1 | := | (same) |
| 163 | 0 | 0 | 200 | 194 | Byte[14] | 0 | := | (same) |
| 163 | 0 | 0 | 684 | 678 | Byte[13] | 2 | := | the grant's pass -- the end state's Byte[13] (4.9) |

33 writes + 6 chain = **39 keys a run**, beside 12 masked rows (Bit[191] ip22 / 154 ip26, Bit[184] ip49 / 154 ip53, each
visit). Every key's `m` 1, `src` "eb". EXACT for O6's reason: the census classifies every site (6.1); R-FULL shows the
exact set before the freeze (F6).

### 4.5 The start (O7-START), the start-scoped olds, the carried values
```json
"start_first": {"donor": 154, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 26, "off": 16, "target": "Global.Bit[191]", "value": 0, "op": ":=", "what": "154's Main_Init: its first store (emitted same: a new site)"},
"start_music": {"donor": 154, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 123, "off": 113, "target": "Global.Byte[13]", "value": 0, "op": ":=", "old": 1, "what": "154's ambient branch (Int16[9] < 0) from the warp's Byte[13] 1 (field 70's prologue :=1 at ip130; the warp leaves 70 before ip475's :=2, which would take ip101 and window 56)"},
"start_scoped": [
 {"site": [154, 0, 0, 61], "target": "Global.Int16[9]", "here": [643, -1], "after": {"run": "O1-O6", "old": -1, "value": -1, "source": "old: the last pre-cut tuple on the target in o6_predictions_v1.json's pattern (153 e0 t0 ip57, -1); story-o6's six runs read 154 ip61 -1 -> -1 past the cut"}},
 {"site": [154, 0, 0, 123], "target": "Global.Byte[13]", "here": [1, 0], "after": {"run": "O1-O6", "old": 0, "value": 0, "source": "... (153 e0 t0 ip119, 0); story-o6: 154 ip123 0 -> 0"}},
 {"site": [159, 16, 1, 613], "target": "Global.Byte[208]", "here": [0, 0], "after": {"run": "O1-O6", "old": 1, "value": 0, "source": "... (153 e32 t1 ip1632, 1)"}}],
"start_reads": [
 {"site": [159, 0, 0, 290], "target": "Global.Byte[8]", "old": 125, "why": "field 70 e0 t0 ip249 Byte[8] := 125 lies inside the warp window (after ip130, behind ip229-246's SYSVAR[3] wait, before ip475): a warp before it leaves 0, and this store -- the route's first on Byte[8] -- would read 0 (0.2 #19). The trace is armed after 70's prologue: this old is the only reading"}],
"carried": {"why": "a true O1-O6 run's value (composed over the frozen O1-O6 keys in segment order: 4.5's derivation) where the raw start holds 0; neither written nor read on O7 (154-163)",
 "values": {"Global.Bit[3717]": [0, 1], "Global.Bit[3718]": [0, 1], "Global.Byte[472]": [0, 4], "Global.Int16[469]": [0, 1042],
            "Global.Bit[3815]": [0, 1], "Global.Byte[475]": [0, 100], "Global.Bit[3795]": [0, 1],
            "Global.Bit[3854]": [0, 1], "Global.Bit[3855]": [0, 1], "Global.UInt16[21]": [0, 8], "Global.Byte[303]": [0, 1],
            "Global.Byte[18]": [0, 1], "Global.Byte[6]": [0, 11], "Global.UInt16[19]": [0, 1807]},
 "party": {"values": ["[Zidane]", "[Steiner]"], "source": "not a gEventGlobal target: New Game's party; 153 e32 t1's rebuild (O6, UInt16[21] := 8) -- typed, labelled, never derived"}}
```
**No start-dependent key** (decision 3): every route read resolves the same branch from the raw warp and from a true
O1-O6 run (Int16[2] 315; Byte[13] normalized by 154's prologue; Int16[9], Byte[8] and Byte[208] written before read;
Bit[3796], Bit[3798], Bit[3799] 0 on both). The start-scoped olds differ in `old` / `same` only -- each is a writes key at
the same value; the emitted pattern is this start's (in a single-epoch chained run O5 would have emitted 154's prologue
sites already: lesson 14). O7-KEYS checks each `start_scoped` site is a writes key, `here.old` the start's value (field
70's prologue: 643, 1; New Game's 0), `after.run` the class's `AFTER_RUN`, `after.source` present, and `after.old` the
value `olds_from_pattern` reads off O6's frozen `pattern` at offline-check time -- the `new` of the LAST tuple on the
target before O6's cut (153 ip57 Int16[9] -1, 153 ip119 Byte[13] 0, 153 e32 t1 ip1632 Byte[208] 1), which precedes
the site by construction. (Rev. 2, claim review #3: the first draft read O6's `end_state`, which O6 read live on
arrival in 154 -- after 154's prologue, when Int16[9] and Byte[13] hold what ip61 and ip123 themselves write; there a
wrong old could never fail. story-o6's six runs are the witness: 154 ip61 -1 -> -1 and ip123 0 -> 0, same, past the
cut.)

**The start reads** (rev. 2, claim review #7): each `start_reads` site is a writes key whose `old` the raw start
decides and nothing on the route before it writes. A covered run's row at the site must read `old`; another `old` is
A-START (5.1: the start's problem, the run uncovered -- never a failed PATTERN or STATE). O7-KEYS checks the site is a
writes key, its target the key's, and that no store of the target precedes it on the route (the census: 154's ip279 is
the dead 304 branch's).

**THE CARRIED VALUES, DERIVED** (rev. 2, claim review #1; 0.2 #18). `carried_from_segments` composes the FROZEN keys of
`PRIOR_SEGMENTS` in segment order, each list in its frozen order (every frozen file lists a target's keys in route
order: the composition is checked against each segment's own `end_state` for every target that segment writes and its
`end_state` holds -- that segment replayed alone from the raw start -- and a disagreement refuses): `:=`, `:=var` and a
key with no `op` (O1's v4 ladder) set; `++`, `&=` and a `|=` on an in-segment `prior` take the key's value (computed in
its segment); a `|=` on the `newgame0` prior OR-composes onto the running value; a `start_dependent` key carrying
`after.old` (O6's two) first sets the running value to `after.old` -- refused unless `after.old` holds every bit of the
running value (a `|=` target only gains bits) -- then composes. O1's frozen v4 registers only its ladder, so
UInt16[19]'s O1 bits (1797, with O2's 2: 1799) reach the repo only through that `after.old`. Noise targets are skipped;
the targets O7 writes (writes, chain, masked) are subtracted; a target whose composed value equals the raw start's (New
Game 0, field 70's prologue, the warp's residue) is not carried. O7-KEYS refuses: a typed `values` that differs from the
derivation (a missing, extra or wrong target); a carried target in `end_state` (a raw-start value claimed as an end
state: the first draft's Bit[3795]); a carried target with a store site in the route's census or a read in an instanced
entry of a route field at its entrance (`instanced_at7`: "neither written nor read" enforced). Run at design time over
the repo (`derive_carried.py`): no segment disagrees with its own `end_state`, and the result is the fourteen of 0.2 #18
-- the same numbers the six archives' S traces compose to. The scope line (5.4) renders them; the O8 handoff takes the
derivation, never a typed copy (9.1).

### 4.6 The error path, the forbidden sites, the dead sites, the inert function (registered; never expected)
- `error_path` (24; each field's four -- Byte[13] := 9 and Byte[14] := 9 on an incoming 2 with `Int16[9] < 0`, and window
  56's two resets): 154 e0 t0 ip101, ip182, ip497, ip531; 158 ip97, ip178, ip288, ip322; 159 ip97, ip178, ip574, ip608;
  160 ip97, ip178, ip308, ip342; 162 ip97, ip178, ip775, ip809; 163 ip97, ip178, ip527, ip561. A 154 row is A-START (V5,
  driver); any other the game's.
- `forbidden_sites` (22; what a wrong door, a back door, a talk or a talk's scene writes): 154 e8 t2 ip195 (:= 301, the
  balcony branch), e9 t2 ip195 / ip355, e10 t2 ip195 / ip355, e5 t3 ip675 `Bit[3852]` (Dojebon's talk); 158 e1 t2 ip193
  `Byte[13] := 3`, ip221 `:= 331` (the back door); 159 e5 t3 ip636 `Bit[3849]` (Haagen's talk), e5 t1 ip311 `Bit[3798]`
  (his scene), e10 t2 ip193, e12 t2 ip193 (wrong doors); 160 e2 t3 ip298 `Bit[3850]`, e2 t1 ip230 `Bit[3799]` (Weimar's talk
  and scene), e9 t1 ip380 / ip415 / ip450 / ip485 `Byte[208]` (his scene), e4 t2 ip194, ip222 (the back door); 162 e2 t2
  ip227; 163 e3 t2 ip227.
- `dead` (24, each with why): every field's e0 t0 `Int16[2] := 10000` (154 ip45, others ip41: behind `Bit[184] == 1`,
  0); the prologue's untaken `Byte[13]` branch (154 ip134 and 159 ip130 `:= 1` -- `Int16[9]` just set -1; 158, 160, 162,
  163 ip119 `:= 0` -- `Int16[9]` 385 is not < 0); the untaken `Byte[14] := 1` (154 ip215, others ip211: `Int16[11]` just
  set -1); 154 ip279 `Byte[8] := 125` (the 304 branch L232); the door stores behind `Map.Bit[162] == 0` (ip177), which
  each door's own ip38 sets 1 first: 160 e5 t2 ip199, 162 e2 / e3 t2 ip199, 163 e2 / e3 t2 ip199.
- `inert` (function level, proven by `instanced_at7`): `{"donor": 154, "sid": 2, "tags": "*", "why": "InitObject(2) only
  on the 304 branch L232: not instanced at 315"}` (its ip1520 `Int16[2] := 316`).

### 4.7 Noise: none
No `SYSVAR[0]`-gated store (159 e2/e3 read SYSVAR[0] for tile animation only, storing nothing); no battle, ATE, choice
or revisit; the walks write nothing (every grant's post-grant store precedes the step's first press by rule 8's settle);
the monologue's values do not depend on where it fires; Dojebon's patrol stores nothing. `noise: []`: NULL and STABLE set
nothing aside.

### 4.8 Forbidden
```json
[{"off_route": true, "cause": "walk",
  "why": "a write off the route: S, a place outside the route + [164]; F, a field that is neither a member whose donor is on the route nor F's own end field (real 154/158-164 on F: an un-retargeted Field() or an engine id leak; 153/155/156/161/167 or 31245/31247/31248/31253/31259 after a wrong door, backed by its V11 step row)"}]
```
No door pattern (O6's reason, 4.9 there: a wrong or back door's tag 2 runs its `Field()` right after its stores, so the
landing is off the route -- `off_route` hits -- or out of order -- rule 3's V11; a covered run cannot hold them: WRITES
exact). A back door into 154 lands ON the route: its stores (158 e1 ip193 / ip221) are in 158 and no pattern matches
them; the run is VOID by rule 3 (V11 on the walked row), never covered.

### 4.9 End state
Read live on arrival in 164 / member(164) (O7-STATE (b)), WITHOUT Byte[13]:
```json
{"Global.UInt16[0]": 1190, "Global.Int16[2]": 342, "Global.Byte[8]": 125, "Global.Int16[9]": 385, "Global.Int16[11]": -1,
 "Global.Byte[14]": 0, "Global.Bit[191]": 0, "Global.Bit[184]": 0, "Global.Byte[208]": 1, "Global.Bit[3796]": 1,
 "Global.Bit[3811]": 0, "Global.Bit[3798]": 0, "Global.Bit[3799]": 0, "Global.Bit[3849]": 0, "Global.Bit[3850]": 0,
 "Global.Bit[3851]": 0, "Global.Bit[3852]": 0, "Global.Bit[3792]": 0, "Global.Bit[7211]": 0, "Global.Int16[224]": 0}
```
Ten the route leaves (none raced by 164's prologue: 0.2 #13), ten untouched since New Game AND by O1-O6 (the talk and
scene bits of 154/159/160 and O8's knight: none is in the composition of 0.2 #18). Bit[3795] -- O5's stored choice, 1
after a true run, 0 on the raw start -- is CARRIED (4.5), never an end state (rev. 2, claim review #1). And from the
TRACE (O7-STATE (c)):
```json
"end_state_trace": {"Global.Byte[13]": {"value": 2, "site": {"place": 163, "sid": 0, "tag": 0, "ip": 684},
                    "why": "164's prologue rewrites Byte[13] at once (ip130 2 -> 1) and again at its grant (ip764): the live read races; the last pre-cut write is 163 ip684's 2"}}
```
The draft COMPUTES both: the live targets' values from the registered keys in route order (the last write of each), the
untouched ones 0, Byte[13] from its last pre-cut site -- never typed (the fallback, 4.17, recomputes them). `site.place`
is a frozen PLACE: STATE (c) matches the row by `place(row.fld, members)` -- 163 e0 t0 ip684 at real 163 on S, at
member(163) 31255 on F (claim review #9).

### 4.10 The walks and the registered interruption
O7-WALK reads every table step (2.4) and:
```json
"interruptions": [{"donor": 159, "visit": 3, "step": 0, "name": "the forced monologue",
  "test": {"any_of": {"x_lt": -1600, "x_gt": 1600, "z_lt": 800}, "unless_bit": 3796},
  "rows": [[159, 16, 1, 613], [159, 16, 1, 648], [159, 16, 1, 672]], "pages": [296, 297, 298, 299, 300],
  "why": "159 e16 t1 ip390 takes control the first tick he leaves |x| <= 1600 && z >= 800 (e11 lies wholly at x <= -2208); its three stores are fixed values written with control off, after the step's first loss and before its re-run (ip711 re-grants in place)"}]
```
`test` is READ off ip390's pinned text by `monologue_test` (O7-KEYS fails a frozen `test` that differs: derived, never
typed). The evidence's slack for its loss sample is O6's derived 180 u (`STALE_TICKS` 3 x `RUN_U_PER_TICK` 60).

### 4.11 Coverage beats, the input witness, the static object
Beats: the seven steps' (`w154_ground`, `x154_e8`, `x158_e2`, `x159_e11`, `x160_e5`, `x162_e3`, `x163_e2`) plus `end ==
"reached"`. `witness` (2.1). And, report-only:
```json
"static_objects": [{"donor": 154, "sid": 5, "name": "Dojebon", "tol": 30,
  "why": "154 e5 t1 ip263 holds him while B_DISTANCEA < 3600 or Map.Byte[30] == 1; released, he patrols head-on along the west flight the walk takes. He stores nothing (e5 t1 holds no store), so a release moves no key: it is watched (O7Segment.drive's observe, keyed by PLACE -- 154 on S, member(154) 31246 on F: one 'seen' row per visit, his first published reading (frame, x, z), and one 'moved' row the first time a reading leaves it by more than tol, a MovePC step) and reported; a visit with no reading is UNOBSERVED, never 'static'; in rehearsal a 'moved' row or an UNOBSERVED visit stops the freeze (F2)"}]
```
(Rev. 2, claim review #6: the first draft wrote only the `moved` row, so a sid never published or never read read as
"static".)

### 4.12 Budget and recovery
Estimated ~1.8 min a run (the research: O6's measured 89-99 s for New Game + the warp + one walk, plus ~600 running
ticks, ~2 s of settles a step, ~2.5 s a transition and a page). Drafts: `run_s` 600, `run_min_s` 300, `session_s` 3600,
`settle_s` 1.0, `no_progress_s` 60 (the longest static span is a page or a fade), `end_row_s` 10. F8 replaces every one
from R-FULL. Recovery is `end_run` (2.8).

### 4.13 Settings, the New-Game override, the engine, the derived facts
O4's frozen values (as O6's) PLUS three keys S19 and the walk numbers rest on: `"AnalogControl": {"Enabled": "1",
"UseAbsoluteOrientation": "3"}` (keys read `twist.y`: the prior basis, session.py:2848-2866) and `"Control"`'s
`"PSXMovementMethod": "1"` (the slope-scaled run: the ticks the budgets and walks rest on). Live today: Memoria.ini lines
125 and 136/139. P-SETTINGS reads the predictions' dict generically (o3_prima_vista.p_settings): no code change.
`override70` {FF9CustomMap-world: 2ce8887e...}, `engine` {x64, x86: ba976242...}, `derived` (cfg.control 0, 30 ticks a
second). `freeze` refuses an engine that is not the live DLLs'.

### 4.14 The route pins and route_mes
`route_pins` -- `[donor, sid, tag, ip, eb-src text]`, each compared EXACTLY with the stock US script's text (O7-KEYS (b)).
The texts below were read off the listings while designing; C1 reads the rest the same way (each player entry's spawn
SETs) and the commit records the count:
- **154**: e0 t0 ip26 `SET({Global.Bit[191] const(0) B_LET B_EXPR_END})`, ip223 `SetControlDirection(246, 0)`, ip234
  `SWITCH(304, L392, L232)`, ip539 `SET({Map.Bit[159] const(1) B_LET B_EXPR_END})`, ip547 `SET({Map.Bit[158] const(1) B_EQ
  B_EXPR_END})`, ip566 `SET({Map.Bit[159] const(1) B_EQ B_EXPR_END})`, ip577 `SET({Map.Bit[156] const(0) B_EQ
  B_EXPR_END})`, ip588 `EnableMove()`; e15 t0 ip14 `SWITCHEX(L2028, 331, L28, 310, L204, 311, L380, 312, L556, 313, L1292)`,
  ip2070 `SET({Map.Bit[158] const(1) B_LET B_EXPR_END})`, ip2116 `SET({Map.Byte[30] const(2) B_LET B_EXPR_END})`, ip2127
  `SetControlDirection(250, 0)`, ip2774 `SetModel(5489, 104)`, ip2812 `SetObjectLogicalSize(30, 35, 50)`, ip2827
  `MoveInstantXZY({obj(uid=255).f[0] B_EXPR_END}, {Map.Int16[2] B_EXPR_END}, {obj(uid=255).f[2] B_EXPR_END})`, ip3003
  `DefinePlayerCharacter()`; e8 t2 ip30 `SET({B_SYSVAR[2] B_EXPR_END})`, ip38 `SET({obj(uid=250).f[1] const(65436) B_LT
  B_EXPR_END})`, ip51 / ip211 `ExitField()`, ip195 `SET({Global.Int16[2] const(301) B_LET B_EXPR_END})`, ip203
  `Field(153)`, ip305 `op_22(25)`, ip355 `SET({Global.Int16[2] const(300) B_LET B_EXPR_END})`, ip363 `Field(158)`; e9 t2
  ip38 (the same test), ip195 `... const(302) ...`, ip203 `Field(156)`, ip355 `... const(300) ...`, ip363 `Field(155)`;
  e10 t2 ip38, ip195 `... const(303) ...`, ip203 `Field(156)`, ip355, ip363 `Field(167)`; e5 t1 ip263 and ip486
  `SET({B_PTR(250) B_DISTANCEA const(3600) B_LT Map.Byte[30] const(1) B_EQ B_OROR B_EXPR_END})`; e11 t1 ip14
  `SET({Map.Byte[30] const(2) B_EQ obj(uid=250).f[1] const(64936) B_GT B_ANDAND B_EXPR_END})`, ip33 `SET({Map.Byte[30]
  const(1) B_LET B_EXPR_END})`, ip128 `SET({Map.Byte[30] const(1) B_EQ obj(uid=250).f[1] const(65036) B_LT B_ANDAND
  B_EXPR_END})`, ip147 `SET({Map.Byte[30] const(2) B_LET B_EXPR_END})`.
- **158**: e0 t0 ip57 `SET({Global.Int16[9] const(385) B_LET B_EXPR_END})`, ip130 `SET({Global.Byte[13] const(1) B_LET
  B_EXPR_END})`, ip379 `EnableMove()`, ip445 `SET({Global.Byte[13] const(2) B_LET B_EXPR_END})`; e6 t0 ip14 `SWITCH(300,
  L47, L12)`, ip130 `SetObjectLogicalSize(30, 35, 50)`, ip301 `DefinePlayerCharacter()`; e2 t2 ip30, ip50 `ExitField()`,
  ip144 `op_22(25)`, ip194 `SET({Global.Byte[13] const(3) B_LET B_EXPR_END})`, ip222 `... const(331) ...`, ip230
  `Field(159)`; e1 t2 ip193, ip221, ip229 `Field(154)`.
- **159**: e0 t0 ip119 `SET({Global.Byte[13] const(0) B_LET B_EXPR_END})`, ip219 `SetControlDirection(0, 0)`, ip290
  `SET({Global.Byte[8] const(125) B_LET B_EXPR_END})`, ip665 `EnableMove()`; e16 t0 ip14 `SWITCH(333, L84, L49, L14)`,
  ip167 `SetObjectLogicalSize(30, 35, 50)`, ip338 `DefinePlayerCharacter()`; e16 t1 ip390 (0.2 #10's text), ip445
  `DisableMove()`, ip508 `WindowAsync(4, 128, 296)`, ip537 `WindowSync(4, 128, 297)`, ip543 `WindowAsync(4, 128, 298)`,
  ip561 `WindowAsync(4, 128, 299)`, ip602 `WindowAsync(4, 128, 300)`, ip613 `SET({Global.Byte[208] const(0) B_LET
  B_EXPR_END})`, ip648 `SET({Global.Byte[208] B_POST_PLUS B_EXPR_END})`, ip653 `SET({Global.Byte[208] const(1) B_LT
  B_EXPR_END})`, ip672 `SET({Global.Bit[3796] const(1) B_LET B_EXPR_END})`, ip711 `EnableMove()`; e11 t2 ip30, ip49
  `ExitField()`, ip143 `op_22(25)`, ip193 `... const(332) ...`, ip201 `Field(160)`; e10 t2 ip201 `Field(158)`; e12 t2 ip201
  `Field(161)`.
- **160**: e0 t0 ip219 `SetControlDirection(246, 0)`, ip232 `SET({Global.Bit[3799] const(0) B_EQ B_EXPR_END})`, ip399
  `EnableMove()`, ip465; e9 t0 ip14 `SWITCH(341, L39, L12)`, ip114 `SetObjectLogicalSize(30, 35, 50)`, ip285
  `DefinePlayerCharacter()`; e5 t2 ip38 `SET({Map.Bit[162] const(1) B_LET B_EXPR_END})`, ip177 `SET({Map.Bit[162] const(0)
  B_EQ B_EXPR_END})`, ip199, ip227 `... const(333) ...`, ip235 `Field(162)`; e4 t2 ip194, ip222, ip230 `Field(159)`.
- **162**: e0 t0 ip219 `SetControlDirection(244, 0)`, ip866 `EnableMove()`, ip932; e7 t0 ip14 `SWITCH(342, L39, L12)`,
  ip114 `SetObjectLogicalSize(30, 35, 50)`, ip285 `DefinePlayerCharacter()`; e3 t2 ip38, ip227 `... const(341) ...`, ip235
  `Field(163)`; e2 t2 ip38, ip227, ip235 `Field(160)`.
- **163**: e0 t0 ip219 `SetControlDirection(16, 16)`, ip618 `EnableMove()`, ip684; e7 t0 ip14 `SWITCH(343, L47, L12)`,
  ip122 `SetObjectLogicalSize(30, 35, 50)`, ip293 `DefinePlayerCharacter()`; e2 t2 ip30, ip38, ip55 `ExitField()`, ip149
  `op_22(25)`, ip227 `... const(342) ...`, ip235 `Field(164)`; e3 t2 ip38, ip227, ip235 `Field(162)`.
- **164**: e0 t0 ip22 `SET({Global.Bit[191] const(0) B_LET B_EXPR_END})` (the end row).
- **70** (the warp's window, rev. 2: what `start_music` and `start_reads` stand on, 0.2 #19): e0 t0 ip130
  `SET({Global.Byte[13] const(1) B_LET B_EXPR_END})`, ip238 `SET({B_SYSVAR[3] const(0) B_NE B_EXPR_END})`, ip246
  `JMP_IF(L229)`, ip249 `SET({Global.Byte[8] const(125) B_LET B_EXPR_END})`, ip475 `SET({Global.Byte[13] const(2) B_LET
  B_EXPR_END})` -- the US listing's (`L70`); O7-KEYS compares them as it compares the route's.
Plus the SCANS O7-KEYS runs over each route field at its entrance (instanced entries only, `instanced_at7`): exactly one
`DefinePlayerCharacter` (the pinned one: control binds to the last, memory "Non-Zidane donors"); no `B_PARTYCHK`,
`SetPartyReserve`, `RemoveParty` or party-add op; every `SetControlDirection` with operand 1 the pinned one's (one basis);
no `Map.Bit[144]` store (the doors' `op_22(1)` skip, O6's ip80 lesson).

`route_mes` (block 3, US, the asset the engine reads; O7-TEXT reads it):
```json
"route_mes": {"block": 3, "monologue": [{"mes": 296, "holds": "What!?"}, {"mes": 297, "holds": "[STNR]"},
              {"mes": 298, "holds": "[STNR]"}, {"mes": 299, "holds": "[STNR]"}, {"mes": 300, "holds": "I must hurry!"}],
              "stop_page": {"mes": 56, "holds": "Env Play()"}}
```
The [STNR] pages render New Game's default name for character 3 on the raw start: text only, the same block on both
sides, never judged (O7 registers no naming).

### 4.15 The regions, the table's defaults
Each region's `points` the first SetRegion of its (donor, entry), in the engine's order; every `exit` from `scan_gateways`:

| key | points | role | to @ entrance | branches |
|---|---|---|---|---|
| 154.e8 | (2222,-5555) (-2222,-5555) (-2222,-4080) (2222,-4080) | exit | 158 @ 300 | balcony (`y_gt` 100) 153 @ 301 |
| 154.e9 | (-3777,-999) (-3777,-3111) (-1888,-3111) (-1888,-999) | exit | 155 @ 300 | balcony 156 @ 302 |
| 154.e10 | (3777,-999) (3777,-3111) (1888,-3111) (1888,-999) | exit | 167 @ 300 | balcony 156 @ 303 |
| 154.hazard.dojebon | (150,-4080) (2222,-4080) (2222,-2950) (150,-2950) | hazard | -- | `object` {"sid": 5, "guard": [154, 5, 1, 263]}, `guards` [[154, 1190, 1, 0]] |
| 158.e1 / 158.e2 | (-612,-8797) (588,-8797) (618,-12487) (-642,-12487) / (480,-17752) (-450,-17752) (-1061,-15641) (1009,-15641) | exit | 154 / 159 @ 331 | |
| 159.e10 / e11 / e12 | (1120,6590) (-1130,6590) (-1160,4910) (1150,4910) / (-3498,955) (-3498,-888) (-2208,-888) (-2569,1039) / (3410,901) (3403,-631) (2254,-623) (2550,941) | exit | 158 / 160 / 161 @ 332 | |
| 160.e4 / e5 | (3018,-4012) (3018,-4792) (1459,-4463) (1371,-3599) / (-561,-127) (-111,-127) (-49,-1065) (-589,-1065) | exit | 159 / 162 @ 333 | |
| 162.e2 / e3 | (575,-5321) (1385,-5321) (1415,-3850) (-205,-3850) / (755,3730) (1265,3730) (1265,130) (725,130) | exit | 160 / 163 @ 341 | |
| 163.e2 / e3 | (721,4803) (866,5202) (1432,5013) (1300,4705) / (1210,1307) (437,1254) (377,2244) (1238,1892) | exit | 164 / 162 @ 342 | |

A `hazard` key is `<donor>.hazard.<name>` (never `<donor>.e<sid>`: no bytes pin, never an exit -- `exit_regions` skips it
by role, the landing judge never reads it), its `object` an entry instanced at the place's route entrance whose pinned
guard it protects, its `guards` the (donor, sc, visit, step) whose `avoid` must hold it. 164 is the END place: its regions
and census are O8's. `steps_default` is O6's exactly (`attempts` 2, `interrupts` 1, `timeout_s` 20, `tolerance` 45,
`exit_slack` 40, `exit_wait_s` 5.0, `npcs` true, `overlay_ok` false, `immediate` false, `settle` null, `lunge_ticks` 0,
`min_depth` 40, `confirm_s` 4.0, `climb` O2's).

### 4.16 The emitted row pattern (O7-PATTERN; R-FULL measures it)
`pattern` = `{"visits": [...], "floating": [], "counts": [], "why"}`, each tuple `[place, sid, tag, off, target, new,
same]`; every visit opens with its prologue `P(place, i9, s9, b13, s13)` = `[place, 0, 0, 16, Bit[191], 0, 1], [place, 0,
0, 43, Bit[184], 0, 1], [place, 0, 0, 51, Int16[9], i9, s9], [place, 0, 0, <113 | 124>, Byte[13], b13, s13], [place, 0, 0,
132, Int16[11], -1, 1], [place, 0, 0, 194, Byte[14], 0, 1]` (154's Byte[13] off 113 at ip123; 159's 113 at ip119; the
others' 124 at ip130):
- visit 1 (154): P(154, -1, 0, 0, 0) + `[154, 8, 2, 325, Int16[2], 300, 0]` -- 7 rows;
- visit 2 (158): P(158, 385, 0, 1, 0) + `[158, 0, 0, 439, Byte[13], 2, 0]`, `[158, 2, 2, 164, Byte[13], 3, 0]`, `[158, 2,
  2, 192, Int16[2], 331, 0]` -- 9;
- visit 3 (159): P(159, -1, 0, 0, 0) + `[159, 0, 0, 284, Byte[8], 125, 1]`, `[159, 16, 1, 223, Byte[208], 0, 1]`, `[159,
  16, 1, 258, Byte[208], 1, 0]`, `[159, 16, 1, 282, Bit[3796], 1, 0]`, `[159, 11, 2, 163, Int16[2], 332, 0]` -- 11;
- visit 4 (160): P(160, 385, 0, 1, 0) + `[160, 0, 0, 459, Byte[13], 2, 0]`, `[160, 5, 2, 197, Int16[2], 333, 0]` -- 8;
- visit 5 (162): P(162, 385, 1, 1, 0) + `[162, 0, 0, 926, Byte[13], 2, 0]`, `[162, 3, 2, 197, Int16[2], 341, 0]` -- 8;
- visit 6 (163): P(163, 385, 1, 1, 0) + `[163, 0, 0, 678, Byte[13], 2, 0]`, `[163, 2, 2, 197, Int16[2], 342, 0]` -- 8.
No floating row: every order is the bytes' (the post-grant store runs in the grant's pass; the monologue precedes e11).
51 `w` rows before the cut, no `c` row; then 164 e0 t0 ip22, the cut.

### 4.17 The fallback end (R-STAIR NO-GO: one line)
`END_FIELD = 164` is the draft's one switch. Set to 163: `route` / `visits` [154, 158, 159, 160, 162], `end_fields`
[163], `side_ends` {S: [163], F: [31255]}, the end row 163 e0 t0 ip22, and every list -- the chain, the writes, the
census's fields, the regions, the table, the pattern, the landing's crossings, `ROUTE_DONORS` -- filtered to the route's
places by the draft; the end state recomputed (Int16[2] 341; Byte[13] from 162 ip932's 2 -- 163's prologue races it the
same way). The dry run's unit `fallback-end` drafts it and runs O7-KEYS, -CENSUS, -REGIONS, -GOALS and a null pair
(PROVEN): the fallback is proven before any rehearsal.

---

## 5. Checks (O7's analysis)

### 5.1 Reading a run: the COVERED rule
O5's rule (skipped, install changed, the drive not reaching the end, a beat not done, no or an incomplete trace,
A-NOSTART, a BACKED forbidden hit, A-MISMATCH, A-START on 154's error path, A-NOEND), A-START scoped to visit 1 (154) --
and, rev. 2, A-START on a `start_reads` site read with another `old` (4.5: 159 e0 t0 ip290's Byte[8] not 125, the warp
having left field 70 before ip249) wherever on the route it stands: the start's problem, never a failed check.
No A-NAMING. A drive VOID carries its V-class and `[place, sc, visit]` cell (2.7). The report lists every uncovered run's
reasons per side.

### 5.2 The cuts (per side, frozen places)
`cut_at_start` from 154's first `w` row (place 154: real 154 on S, 31246 on F; the four residue rows in 70 go to `pre`);
`cut_at_end` at the first `w`/`r` row in an end PLACE ([164] on both sides). Kept after the cut: the epoch rows and any `c`
rows of the route places (none expected). On F the end place 164 is member(164)'s; a run that entered real 164 on F is
VOID by rule 2 first (V19).

### 5.3 The checks, in order, each with the mutant that makes it fail (section 8 registers every one)
**All-run checks** (every run with a readable trace, judged even when COVER is short):
- **O7-FORBIDDEN** (O2's). Mutants: balcony-branch-unbacked-F (e8 ip195's row and rows in 31245, no step row explains
  them), wrong-door-unbacked-F (e9 ip355 and rows in 31247).
- **O7-VOID-ASYM** (O4's (a)-(d), `[place, sc, visit]`; `stop_on` [V19]). Mutants: v19-one-F (a, c), v5-error-158-F (a:
  V5 game at [158, 1190, 2]), v14-one-S (a), v7-stair-all-F (b: every F run V7 driver at [163, 1190, 6]), v7-monologue-
  all-F (b: [159, 1190, 3]), v13-prior-all-F (b: every F run V13 driver at [154, 1190, 1], the prior basis), v11-balcony-
  all-F (b); and the PASS cases v13-prior-one-F, v13-input-one-F, v7-stair-one-S, walk-into-balcony-branch-S (backed),
  error-path-start-S (A-START).

**Then:** **O7-FROZEN**, **O7-COVER**. Mutants: predictions-changed; w154-beat-missing, x163-beat-missing (two S runs:
uncovered, VOID).

**Core checks** (over the covered runs):
- **O7-START** (O3's): (a) `pre` is exactly the FOUR residue rows; (b) the first `w` row in place 154 is `start_first`,
  raw; (c) the first Byte[13] row in place 154 is ip123 `:= 0` from old 1. Mutants: start-residue-three (S: byte 3's row
  missing -- O6's three-row contract would pass it), start-residue-wrong (byte 2 0 -> 58), start-first-missing,
  start-music-old-wrong (ip123 old 2), front-cut-write.
- **O7-NO-SC**: mutants sc-write-fork, sc-harness-poke-both.
- **O7-CHAIN** (`span_check` over bytes 2-3 from 315): exactly 4.3, in order, each from the last. Mutants:
  chain-dropped-fork (no 160 ip227 on F), chain-first-old-wrong (154 ip355's old 316: CHAIN alone).
- **O7-RESIDUE**: mutant residue-after-start.
- **O7-WRITES (exact)**: the 39. Mutants: fork-drops-a-write (no 159 ip672 on F), writes-extra-symmetric (both: 160 e5
  t2 ip199, dead), forbidden-row-both (159 e5 t3 ip636), inert-row-both (154 e2 t1 ip1520) -- each with PATTERN (b).
- **O7-NULL**, **O7-STABLE** (O1's, no noise). Mutants: NULL -- fork-drops-a-write; STABLE -- extra-key-one-F (one F run
  holds 160 e2 t3 ip298).
- **O7-LANDING** (O6's shape over six places), every covered run:
  - (a) every field-mode `w`/`c` row ran in its place's own field and stands in a route place;
  - (b) THE CROSSINGS: for each consecutive pair (P, Q) of `visits`, the run holds P's chain row (4.3) at P's field and
    the next field-mode `w` row after it is Q's entry row (Q e0 t0 ip22 `Bit[191] := 0`) at Q's field; no row of P after
    Q's entry row;
  - (c) the last field-mode `w` row before the end cut is 163 e2 t2 ip227 (by place), and the run's `end` log row names
    the side's end field;
  - (d) the end cut is a raw `w` row 164 e0 t0 ip22 at the side's end field;
  - (e) every F digest records no seam and no seam key.
  Mutants: lands-real-158-covered ((a)(b)(e), FORBIDDEN, WRITES), harness-after-exit158-both ((b) alone),
  field-order-flip-both (visits 3 and 4 swapped: (b) with CHAIN, PATTERN (b), STATE (a) -- re-registered with whatever
  else the render gives), last-place-harness-both ((c) alone), end-real-164-F ((d) alone), end-boundary-residue-both ((d)
  alone); the unit landing-e drives (e) alone.
- **O7-WALK** (THE PAIRED-WALK LAW, over the seven table steps), every covered run:
  - (a) per step (its `name`, donor, visit): exactly one `done` row, the last of its rows; its EVIDENCE -- a `walk`: the
    row's `to` sample in the side's field of the place, `control` true, within `tolerance` of `goal`; a `cross`: `landed`
    the side's field of `to`'s place (the end field for 163's), and `lost`, when read, in the walk's field within
    `exit_slack` of the target; before it at most `interrupts` `interrupted` rows (none with a `door`) and at most
    `attempts` - 1 `failed` rows (none `landed`, none with a `door`);
  - (b) THE REGISTERED INTERRUPTION: 159's step holds EXACTLY one `interrupted` row before its done row, its loss read in
    the side's field of place 159 (real 159 on S, member(159) 31251 on F: `place(fld, members)`), satisfying the
    monologue's `test` widened by the derived slack (x < -1600 + 180 or x > 1600 - 180 or z < 800 + 180), no `door`;
  - (c) THE VISIT WINDOW: per visit, no `w` row from its first step row's `frame0` to its last done row's end (`lost.frame`
    when read in the walk's field, else `flip_frame`, else the row's `frame`; the walk's `frame`) -- except the target
    door's own tag-2 rows (they follow its ExitField) and the registered interruption's rows, which must ALL lie, in
    order, inside the gap from the interrupted row's `lost.frame` to the next attempt's `frame0` (`visit_windows`). ONE
    window per VISIT, not per step: 154's spans both steps and the gap between #0's done and #1's `frame0`; a `walk`
    row's end is its `frame` (it has no `lost`);
  - (d) THE FIRST MOVES (rev. 2, claim review #2): per visit to a SEEDED place (`seeded_fields`: 154, 158, 160, 162,
    163), the visit's first step row's route `basis` is "prior" (seeded in this run: the per-run forget held), exactly
    one of the visit's step rows carries `basis_check` (the first evidence hold's; a later row of the visit may carry it
    when an earlier one pressed none), and its `angle` is at most acos(`PRIOR_AGREE`) (16.3 deg).
  Mutants (each alone unless named): walk-no-step-both, walk-short-both (the walk's done row's `to` 200 u from its goal),
  walk-done-without-control-both, cross-landed-wrong-both (158's done row `landed` 155: a bypassed V11),
  cross-lost-outside-both, two-interrupts-159-both, interrupt-missing-159-both ((b): the done row with no interrupted row
  before it), interrupt-inside-box-both ((b): its loss at (7, 3870)), interrupt-loss-real-159-F ((b): the F run's loss
  read at fld 159, not 31251), interrupt-in-a-door-both, walk-window-row-both ((c): 158 ip445's row stamped inside 158's
  window), monologue-row-outside-gap-both ((c): ip672 after the re-run's `frame0`), walk-gap-row-154-both ((c) alone: a
  row stamped between 154 #0's done `frame` and #1's `frame0` -- a per-step window would miss it), walk-kind-window-row-both
  ((c) alone: a row stamped mid-walk in 154 #0, between its `frame0` and its `frame`), basis-check-missing-both ((d)
  alone: 158's rows carry no `basis_check`), basis-check-30deg-both ((d) alone: its angle 30), basis-cached-run3-S ((d)
  alone: run 3's 154 #0 route `basis` "cached" -- the per-run forget missed); and the PASS cases walk-failed-once-162-both,
  walk-failed-twice-163-both (two `failed` rows under `attempts` 3), walk-interrupted-once-160-both,
  cross-lost-unread-both (no `lost`, `flip_frame` set), basis-check-on-step1-154-both (154 #0's rows carry none, #1's
  does).
- **O7-PATTERN** (O6's `pattern_diff6`, `floating` []): (a) the `c` multiset empty; (b) each of the six visits' emitted
  sequences exactly 4.16's. Mutants: c-row-158-F ((a) alone), byte13-repeat-both ((b): a second 158 ip445 2 -> 2,
  emitted same), monologue-order-swap-both ((b) alone: ip648 before ip613 -- one target, two values, so STATE (a) reads it
  too: re-registered), visit-split-both.
- **O7-MASKED** (O2's). Mutant: masked-differs.
- **O7-STATE**: (a) each unmasked target's emitted history identical across covered runs, in order; (b) every covered
  run's live `end_state` == 4.9's; (c) for each `end_state_trace` target, the run's last pre-cut row on its bytes is the
  registered site with the registered value (163 e0 t0 ip684, 2), matched by PLACE (31255 on F). Mutants:
  end-state-differs ((b) alone: one F run's Bit[3796] 0 live), byte13-live-race-both (every run's live Byte[13] 1: PASS --
  the live read is never compared), byte13-trace-end-F ((c) with RESIDUE: a harness Byte[13] row after 163 ip684); and
  the F-side unit state-c-by-place (the F rows at 31255 match; the same rows renumbered to fld 163 do not).
- **O7-JOIN** (O1's). Mutant: join-failure (both: an extra row at 159 e16 t1 ip614).
- **O7-THROW** (in `run`).

**VERDICT**: O1's `verdict()`. A failed check outranks a void one: a V19 reads "NOT PROVEN: O7-VOID-ASYM".

### 5.4 Report-only (`report_extra`)
- **Scope**, five lines:
  - *start dependence* -- "none in value or path: a raw warp into 154@315 at SC 1190 from New Game, the same on both
    sides. START-SCOPED olds only (the value equal, `old`/`same` not): 154 ip61 Int16[9] 643 -> -1 here, -1 -> -1 after
    the <AFTER_RUN> routes as driven; 154 ip123 Byte[13] 1 -> 0 / 0 -> 0; 159 e16 t1 ip613 Byte[208] 0 -> 0 (same) / 1 ->
    0. Carried, not claimed (neither written nor read on O7; derived from the frozen O1-O6 keys): Bit[3717] 0,
    Bit[3718] 0, Byte[472] 0, Int16[469] 0, Bit[3815] 0, Byte[475] 0, Bit[3795] 0, Bit[3854]/[3855] 0, UInt16[21] 0,
    Byte[303] 0, Byte[18] 0, Byte[6] 0, UInt16[19] 0 (1, 1, 4, 1042, 1, 100, 1, 1/1, 8, 1, 1, 11, 1807 after them), party
    [Zidane] ([Steiner]): Steiner is the controlled character in every walked field whatever the party (each field's own
    DefinePlayerCharacter). THE START READ: 159 ip290 read Byte[8] 125 in every covered run (a warp before field 70's
    ip249 would leave 0: A-START, the run uncovered and named). THE EMITTED PATTERN: each run is a fresh epoch -- in a
    single-epoch chained run O5 had emitted 154's prologue sites, so they would be `c` counts there: every frozen
    sequence, count and the cut are this start's" -- rendered from the predictions
    (`start_scoped`, `start_reads`, `carried`, `AFTER_RUN`), never a literal;
  - *the end state* -- "read live on arrival in 164 but Byte[13], which 164's prologue rewrites at once (ip130 2 -> 1):
    taken from the trace's last pre-cut write, 163 e0 t0 ip684 (2)";
  - *the walks* -- "every step planned at its stated clearance (120; 163's 110: no route at the engine radius) and, in
    154, 158, 160, 162 and 163, on the exact prior basis, seeded afresh every run (no calibration probe; every run's first
    move in each checked within 16.3 deg: O7-WALK (d)); 159 calibrated once a launch per side" -- rendered from the
    table and the runs' `basis_check` rows;
  - *settings and engine* (O4's lines, with [AnalogControl]); *language* (P-TEXT3's line).
- **The walks, per run, per step**: the grant sample (frame, x, z, published y), the basis (`prior` / calibrated /
  cached) and `basis_check` (angle, moved), the clearance, the route record (legs, length, replans, waits, pushes,
  blockers, frozen, boxed), the loss sample, the landing and `flip_frame`, interruptions and failed attempts, the render
  rate (`route.fps`).
- **The monologue, per run**: the interrupted row's loss (frame, x, z), the pages pressed (mes, first and gone frames,
  dropped Confirms), the three rows' frames, the re-grant sample (its distance from the loss), the re-run's loss.
- **Dojebon, per run**: the `seen` row (his first reading in 154 / 31246: frame, x, z) and the `moved` rows (none
  expected); UNOBSERVED when the visit holds no reading (the watch could not have seen a release).
- **The pattern, per run**: the emitted rows per visit, any `c` row, O7-PATTERN's first difference when it fails.
- **The end state**: live, and Byte[13]'s trace value and the live read (the race, recorded).
- The session's end, the VOID reasons per side, masked counts, forbidden hits, the P-TEXT3 line, the re-runs held.

---

## 6. Offline check and preflight

### 6.1 `--offline-check` (the install and O4's build, read-only; reads `--predictions`, else the frozen file, else the DRAFT, and prints which)
- **O7-BUILD**: the base rule (every member's `.eb`, 7 languages, its donor's with only in-chain `Field()` literals
  remapped: "140 files") and `build_pins` over `route_build` -- the seven route members (154, 158, 159, 160, 162, 163,
  164), per language, every byte they differ from their donors in an operand of an in-chain `Field()` (C0 measures the
  sites; expected at least 154: e2 t1 ip1528, e8/e9/e10 t2 ip203 and ip363 -- 14 bytes, O6's; 158: e1 t2 ip229, e2 t2
  ip230; 159: e10/e11/e12 t2 ip201; 160: e4 t2 ip230, e5 t2 ip235; 162 and 163: e2/e3 t2 ip235; 164: e2 and e3 t2's).
  Expected: "140 files, every language its own donor's; the route members' pins hold in 49 member files (7 route
  members x 7 languages): the only byte diffs are their N in-chain Field() operands; member(154) 31246, member(158)
  31250, member(159) 31251, member(160) 31252, member(162) 31254, member(163) 31255, member(164) 31256" (N from C0).
- **O7-KEYS**: O2's `keys_check` machinery on (the chain, the writes, `error_path` + `forbidden_sites` + `dead`,
  `start_first`) -- every key a store of its variable at `(sid, tag, ip)`, its `off`, its MANDATORY `op` the statement's,
  a compound value computed from its `prior` -- then `start_music` one writes key; each `start_scoped` entry, its
  `after.old` read off O6's frozen `pattern` (4.5); each `start_reads` entry (4.5); THE CARRIED VALUES (4.5: derived
  over `PRIOR_SEGMENTS`, each segment checked against its own `end_state`, equal to the typed `values`, none in
  `end_state`, none stored or read on the route); THE ROUTE PINS exactly (4.14); THE SCANS (4.14); the
  `interruptions[0].test` equal to `monologue_test` of ip390's pinned text and its `rows` the writes keys at those sites;
  the hazard's `object.guard` site's text read by `dojebon_test` (3600, Map.Byte[30]). Expected: "110 keys over 110
  distinct sites, every op in its statement, 1 compound value computed from its prior (159 e16 t1 ip648 ++ after ip613),
  none masked but start_first; start_music one writes key (154 ip123 from 1); 3 start-scoped olds, each a writes key,
  after.run O1-O6 (AFTER_RUN), after.old from O6's frozen pattern (153 ip57 -1, ip119 0, e32 t1 ip1632 1); 1 start read
  (159 ip290 Byte[8] old 125, no earlier store of Byte[8] on the route); 14 carried values derived from 6 frozen
  segments (no end-state disagreement), equal to the typed ones, none in end_state, none stored or read on the route;
  N route pins equal; per field one DefinePlayerCharacter instanced (Steiner's), no party op, one key basis, no
  Map.Bit[144] store; the monologue's test read (x < -1600 || x > 1600 || z < 800, unless Bit[3796]); Dojebon's wait read
  (3600, Map.Byte[30] == 1)".
- **O7-TEXT**: O4's `text_check` on block 3, STRICT, then `route_mes` (4.14). Expected: "block 3: 7 byte-equal of 7;
  KNOWN-KIT-DEFECT 0, FAIL 0; mes 296 'What!?', 297-299 [STNR], 300 'I must hurry!', 56 'Env Play()'".
- **O7-CENSUS** (`store_census7`): every gEventGlobal store site of stock 154, 158, 159, 160, 162 and 163 is in `writes`,
  `chain`, the noise mask, `start_first`, `error_path`, `forbidden_sites`, `dead` or an `inert` function (O4's
  precedence); every function decodes; no unresolved store; THE INERT PROOF at each field's route entrance
  (`route_entrances`: 154@315, 158@300, 159@331, 160@332, 162@333, 163@341) by `instanced_at7`; no shared script on the
  route (`live_shared` []: no `RunSharedScript` in an instanced entry of a route field -- scanned). The counts are
  DERIVED: the detail prints each field's total and per-class counts as the census found them (expected, from 0.2 #2:
  "154: 22 (writes 4, chain 1, masked 2, error 4, forbidden 6, dead 4, inert 1); 158: 18 (6, 1, 2, 4, 2, 3, 0); 159: 22
  (8, 1, 2, 4, 4, 3, 0); 160: 24 (5, 1, 2, 4, 8, 4, 0); 162: 18 (5, 1, 2, 4, 1, 5, 0); 163: 18 (5, 1, 2, 4, 1, 5, 0); 0
  unresolved; inert 154 e2 not instanced at 315; 158, 159, 160, 162, 163 hold no entrance dispatch (every Init reachable;
  160's Bit[3799]-gated InitObject(2) instanced)").
- **O7-REGIONS** (`regions_problems7`): every `exit` region's points are the first SetRegion of its (donor, entry) and
  every `scan_gateways` row of that entry is its (to, entrance) or one of its `branches`' (with the branch's height test
  read off the pinned ip38: `y_gt` 100 from `f[1] const(65436) B_LT`); instanced at the place's route entrance; every
  gateway row of the route fields and every region an entrance instances registered; a `hazard`: its key
  `<donor>.hazard.<name>`, never an `e<sid>` key, never in `exit_regions`, a polygon of >= 3 points, its `object` an
  entry instanced at the place's entrance whose `guard` site is pinned, and it lies in the `avoid` of every step its
  `guards` names; no `dormant` region; no hot-spot. Expected: "15 regions (14 exit -- 154's three with their balcony
  branches -- 1 hazard: 154.hazard.dojebon guarding 154 e5's wait, in (154, 1190, 1) step 0's avoid), 0 hot-spots, 17
  gateway rows all registered".
- **O7-GOALS**: O2's `goals_check` on the table (each step runnable through `step_of`; `visits` a walk on the route; each
  goal on the step's floor (its closures) >= the step's clearance from a wall; a route from `start` round `avoid` AT THE
  STEP'S CLEARANCE), then `goals_extra7`, per step:
  - **(g1) THE CLEARANCE**: every step carries `clearance`; one below `ENGINE_RADIUS` (120) only where the plan at 120
    fails (163: none at 120, a route at 110); a step at 120 plans at 120;
  - **(g2) THE EXITS**: every OTHER registered exit of the place is in the step's `avoid` and, for a cross, lies wholly
    outside its target's polygon (no vertex inside it); a cross's goal lies inside its target (IsInQuad) on an open tri
    of the step's floor, and the planned route's first sample inside the target stands on an open tri of that floor;
  - **(g3) THE WALK'S ARRIVAL** (154 #0): every point within `tolerance` of the goal is on open tris of one level only,
    every one ground (PSX y > -100: e8's own ground bound, read from its pinned ip38) -- so "within tolerance, control
    held" proves the ground; and every point within `tolerance` of the goal stands on an open tri of the NEXT step's floor
    (154 #1 plans from wherever #0 ended);
  - **(g4) THE BRANCH** (154 #1): every open tri of the step's floor (its 134 closures) touching the target's polygon is
    ground (PSX y > -100) -- the fire is the ground branch; the closure lists equal `closures154`'s derivation;
  - **(g5) THE INTERRUPTION** (159): the registered `test` fails at `start` (the spawn is inside the box) and holds at
    every vertex of the target (e11 lies wholly inside it), so the interruption precedes the door on any route; from the
    planned line's first point satisfying it a route to the goal exists at the step's clearance (the re-run);
  - **(h) DOJEBON** (154 #0): (h1) every sample of the planned route at PSX y < -500 (where `Map.Byte[30]` may read 2)
    lies within 3600 - `ROUTE_CHUNK_MAX` / 2 (3420) of his placement (measured 3349, at the spawn); (h2) the step carries
    `basis` "prior" (no probe pressed: 0.2 #11); (h3) `154.hazard.dojebon` is in its `avoid`; (h4) THE HAZARD'S
    COVERAGE (rev. 2, claim review #5): the RELEASE ZONE -- every point of a 16-u grid on the step's open floor (its
    closures) above PSX -500 and at least `dojebon_test`'s `within` (3600) from his placement -- lies inside, or within
    `H4_TOLERANCE` (`KEEPOUT_MARGIN_W` + `PROBE_HAZARD_PAD`, 86 u) of, the hazard or another avoided exit; the residual
    beyond `KEEPOUT_MARGIN_W` is PRINTED (count, span, largest gap). It is a REGRESSION PIN of the decided polygon's
    coverage, not a reachability proof: the decided west edge (x 150) leaves one sliver at e8's corner (78 u at most
    from e8, 0.2 #11), which the tolerance passes, while a polygon shifted 50 u east leaves a gap of 104 and fails. The
    reachability is (h1) for the first plan and the re-plan census for every other (0.2 #11, design-time).
  Expected: seven step lines ("(154, 1190, 1) #0 walk wall 870 route 10 legs 7803u at 120 ...") and "(g3) the goal disc
  single-level ground, inside #1's floor; (g4) 18 open tris of #1's floor touch 154.e8, all ground; (g5) 159's test fails
  at (7, 3870), holds at e11's 4 vertices; (h1) 3349 <= 3420; (h2) basis prior; (h3) the hazard avoided; (h4) the release
  zone covered but a sliver of N points at e8's corner, largest gap G <= 86" (N, the span and G as the 16-u grid reads
  them: 3 points in x 64..80, z -4016..-4000, G 70 at the design).

### 6.2 `--preflight` (the live install, read-only; ALL GREEN today -- nothing needs deploying; decision 7)
O6's set without P-NAME: **P-MANIFEST** (`o7_forks.json` members = the frozen members, `deployed` true), **P-DEPLOY**,
**P-EB** (20 x 7 live `.eb` = O4's build), **P-FLOOR** (twenty deployed walkmeshes = their donors'), **P-STOCK** (no mod
folder overrides 154 or 158-164), **P-TEXT3** (block 3, STRICT), **P-RECOVERY** (4600), **P-DONOR** (154, 158, 159, 160,
162, 163, 164: each forked by exactly one ForkDonorPatch row, its member's), **P-SETTINGS** (4.13's 31 keys, [AnalogControl]
among them), **P-PAD**, **P-OVERRIDE**, **P-ENGINE**: 12 lines. **In game** (`capabilities`): P-CAP, **P-OBJECTS** ("the
engine publishes the field's objects (s89): the walks plan with npcs on -- Dojebon and the balcony soldiers in 154, the
soldiers and Haagen in 159, Weimar and the soldier in 160"), P-LANG, P-DONOR-LOG (over the seven donors), P-LAUNCH,
P-PAD. `--preflight` must read all green before any rehearsal; if not, the lead names the failing line and stops.

### 6.3 The fingerprint (per run, before and after)
O6's, unchanged: another session's deploy, a re-wired New Game or an engine rebuild mid-session is A-INSTALL.

### 6.4 `o7_forks.json`
```json
{"what": "O7's fork chain: O4's alxc disc-1 chain as deployed (31240-31259, FF9CustomMap). O7 starts in member(154) 31246 (at 315), runs 31250, 31251, 31252, 31254, 31255 and ENDS on arrival in member(164) 31256 (at 342): every route Field() is retargeted in all 7 languages, so the chain is closed (no seam). Nothing is imported, built or deployed for O7.",
 "reuses": "studies/story-trace/o4_forks.json", "import": "O4's", "build": "O4's: C:/gd/_ns_playtest/o4/build",
 "deploy": "O4's, 2026-10-02 09:04 local", "mod_folder": "FF9CustomMap", "members": {"...": "..."}, "names": {"...": "..."},
 "route_members": {"31246": 154, "31250": 158, "31251": 159, "31252": 160, "31254": 162, "31255": 163, "31256": 164},
 "text_blocks": {"3": ["...O4's..."]}, "deployed": true, "relaunch_needed": false,
 "relaunch_why": "nothing is deployed for O7; P-LAUNCH and P-DONOR-LOG read the launch",
 "global_side_effects": "O4's: O7 adds none", "known_defects": [], "revert": "O4's",
 "built": {"where": "C:/gd/_ns_playtest/o4/build (read-only)", "measured": "<C0: the route members' Field() operand sites per language>"},
 "verified": null}
```

---

## 7. Rehearsal plan (the lead runs these in game)

### 7.1 The stages (`o7_rehearse.py`: `run(g, field=None)`; `O7_STAGE=<name>` picks one by name)
Each traced stage: `O7.start_run` -- `reseed` (every seeded field's basis forgotten, S and F: 0.2 #20), New Game,
`wait_frames(30)`, `storytrace(True)`, the raw warp; `segment_drive.drive(g, stage_pred, side, log, end_fields=...,
observe=recorder, forbid_live=True, witness=input_witness(g))`; the trace to `rh_<stage>_<n>.jsonl`; the record into
`o7_rehearsal.json`; `end_run`. So EVERY run of every stage seeds its fields and judges its first moves -- R-FULL's
second run, both R-WALK154 runs and both R-STAIR runs as much as the first (rev. 2: without the forget only the first
run per launch to reach a field would have). Only R-FULL's traces may define or change the keys, the start, the end
state or the pattern; the staged runs prove mechanics. F-SMOKE and F-PASS send NO `storytrace` verb; F-PASS calls
`O7.reseed` before its warp. THE LADDER TAP (rev. 2, driver review #8): for every route call the recorder wraps the
session's `_unstick_leg` ON THE INSTANCE (restored at the call's end, as `hold_stop` restores `g.send`) and records each
entry's sample (frame, x, z, field), the start of the stalled hold that led to it (the walk tap's last hold), and its
outcome, beside the route record's `waits`, `pushes`, `blockers`, `frozen`, `boxed` -- so each rung is tied to the hold
it followed. THE FOOT WINDOW is x 2000-2260, z 3750-4100 in 163 / 31255 (the pinch, under 120 from z ~3840 to ~3920,
with its approaches: 0.2 #12).

| Stage | When | Warp | Ends in | Runs | What it settles |
|---|---|---|---|---|---|
| **R-FULL** (the go/no-go and the predictions) | stock | `warp 154 315 1190` | 164 | 2 | F1-F8, F10-F11, F14: every grant (sample, objects, published y), every first-move check, every walk and cross (route, holds, slides, stalls, losses, landings, flips), the monologue (loss, pages, rows, re-grant), Dojebon static, the end cut, the keys, the masked rows, the pattern, the end state (live and the trace's Byte[13]), the run time, the longest no-progress stretch, the render rate |
| **R-WALK154** | stock | `warp 154 315 1190` | 158 | 2 | F2: the balcony grant (y ~1716), no probe pressed, each run's first-move check, step 0's arrival on the ground (y ~5 within 45 u of (0, -600)), step 1's loss inside e8 on the ground (z ~-4080, y ~5), the landing in 158; THE DESCENT (0.2 #17): every hold on the west arm and the flight -- predicted reach and measured travel, the slide off the leg, published y at both ends; Dojebon's first reading and his published position every poll in 154 (constant) |
| **R-STAIR** | stock | `warp 163 341 1190` (163's prologue takes ip130 from the window's 1: no error path) | 164 | 2 | F5: the foot at clearance 110 -- every hold starting or ending in THE FOOT WINDOW, its travel, slide and the narrowest wall gap among its samples (`--rehearsal-report` measures it on the stock mesh, level-aware, as `foot163.py` does: the measured squeeze, `SQUEEZE_SLACK_W`'s evidence), and every ladder rung that followed such a hold; after a hold wholly elsewhere on the stair the rungs recorded, never judged; the loss in e2 (~(1338, 4803), y ~783); the landing |
| **R-WALK-VOID** (by name; LAST) | stock | run 1 `warp 154 315 1190` with `hold_stop` {"place": 154, "n": 0, "holds": 3}; run 2 `warp 159 331 1190` with `page_stop` {"place": 159} | V13 | 2 | F9: run 1 stopped before step 0's 4th walk hold (on the balcony or the flight, control held); run 2 stopped on its first page press in 159 (mid-monologue, 296 up); each `end_run` reaches the title |
| **F-SMOKE** (by name; NO trace) | any time | `warp 31246 315 1190`, `31250 300`, `31251 331`, `31252 332`, `31254 333`, `31255 341`, `31256 342` -- each `member(<donor>)` from the chain -- and their stock twins | -- | 14 warps | F12: each member loads at its entrance and SC, its published object sids EQUAL to its twin's measured set after `smoke_s` (only the twin's reading is compared), 0 exceptions |
| **F-PASS** (by name; NO trace; before the freeze) | after F-SMOKE | `warp 31246 315 1190` | 31256 | 1 | F13: one F run through the whole route on the DRAFT (`forbid_live` False, `end_row_s` None): reached 31256, every beat, no V-class, no exception since the warp. It may only STOP the session; its record shapes no frozen value |

Default order without `O7_STAGE`: R-FULL, R-WALK154, R-STAIR, R-WALK-VOID (the void stage last: a recovery that fails ends
the launch, and that failure is the finding). The stops are `o7_rehearse` overlays on a COPY of the stage's table:
`hold_stop` raises "the rehearsal's stop mid-walk" from a wrapped `g.send` before the (holds+1)-th DIRECTION hold of the
named step once its field's basis is in `g._axes` (O6's hold tap tells probes from holds; under the seed every hold is a
walk hold), on the driver's thread, the session's send restored at once; `page_stop` raises "the rehearsal's stop
mid-monologue" from a wrapped `g.press` on rule 7's first Confirm while the published field's place is 159 and a window
is listed. Estimates a run: R-FULL ~2 min, R-WALK154 ~1 min, R-STAIR ~40 s, R-WALK-VOID ~1 min each, F-SMOKE ~5 min in
all, F-PASS ~2 min. The command: `py tools/play.py studies/story-trace/o7_rehearse.py --label o7-rh --timeout 240`.

### 7.2 What every stage records
O6's record (grants with their objects, pages with `gone_frame`, the press evidence, the longest no-progress stretch, the
end state, `end_run`'s rows, the walk tap's holds and samples, the calibration record, the published objects at the
grant) plus, per run: **the render rate** (`g.rate().as_dict()` at the end and each route record's `fps`); **the bases**
(per field: seeded, calibrated or cached; `basis_check` -- every run's, after the per-run forget); **the levels**
(published y at each grant, each loss and every walk hold's start and end in 154); **the descent** (154 #0's holds on the
west arm and the flight: predicted reach, measured travel, the slide off the leg); **the ladder** (THE LADDER TAP's
entries: each wait, push, blocker, frozen or boxed with its sample and the stalled hold it followed, per step and
attempt); **Dojebon** (the `seen` row -- his first reading -- and his published (x, z) on every poll in 154 / 31246; any
change a `moved` row; no reading UNOBSERVED); **the monologue** (the interrupted row, the pages with their first and gone
frames and every Confirm's down frame, the three rows' frames, the re-grant sample); **the squeeze** (R-STAIR / R-FULL
163: each hold's start, end, pressed direction and travel, the foot window's holds flagged; every slide, stall, wait,
push and blocker with the hold it followed); **the trace** through `trace_summary` (the start rows, the chain rows, each
registered key present or absent, every unregistered key, the crossings, the emitted rows per visit, any `c` row, the
cut row, the residue, the masked counts, the join failures, Byte[13]'s last pre-cut row, 159 ip290's `old`).
`py studies/story-trace/o7_castle_walk.py --rehearsal-report <run dir>` prints all of it.

### 7.3 The freeze checklist (each item needs its evidence; the run dirs go into `rehearsals`)
- **F1 (the grants).** Each of the six within 64 u of 2.4's spawn (else that step's `start` takes the measured point and
  O7-GOALS runs again before the freeze); 154's on the balcony (published y 1716 +- 30) -- a grant on the ground STOPS
  the freeze (the walk's premise).
- **F2 (154).** In every R-WALK154 and R-FULL run (each seeds afresh: 7.1): no probe pressed in 154 (`basis`
  "prior"), exactly one `basis_check` in the visit, within 16.3 deg (expect under 3); step 0 done within its attempts
  with no V7 (a failed attempt recorded with where its ladder began, never a stop), its end within 45 u of (0, -600) at
  published y < 100; step 1's loss inside e8 (z >= -4080 - 180) at published y < 100, the landing 158; Dojebon's `seen`
  row present and NO `moved` row -- a `moved` row or an UNOBSERVED visit STOPS the freeze (the seed or the hazard failed
  to hold him, or the watch never saw him: re-derive). The descent's measured travel and slides recorded (0.2 #17: the
  first evidence of the radius on the railing).
- **F3 (159).** Exactly one interrupted row, its loss within the widened test (expect x just under -1600, z ~1570); pages
  296-300 each pressed (a dropped first Confirm on 297 recorded); the re-grant sample within 30 u of the loss (in place);
  the re-run done, its loss inside e11.
- **F4 (158, 160, 162, 163's first moves).** In every run that reaches them (R-FULL; R-STAIR for 163): exactly one
  `basis_check` per visit, within 16.3 deg; no back door entered; 160's leg free of the corner (clearance 120); 162/163
  heading away from e2/e3.
- **F5 (R-STAIR: the go/no-go).** GO when, in every R-STAIR and R-FULL run, 163's cross is done within its attempts
  with no V7 AND no ladder rung (wait, push, blocker, frozen, boxed) followed a hold that STARTED OR ENDED in THE FOOT
  WINDOW (slides allowed; a rung elsewhere on the stair -- where the 110 plan runs 112-119 u off the left wall, under
  the radius -- is recorded, never judged: the session's own rule accepts a re-plan); the measured squeeze recorded (the
  narrowest gap a foot hold passed, for `SQUEEZE_SLACK_W`); NO-GO otherwise: `END_FIELD = 163` (4.17), the fallback
  recorded in the freeze and in PLAN.md, and the O8 handoff moves 163 into O8. (Rev. 2, driver review #8: the first
  draft also demanded step 0's first attempt in F2 and a ladder-free 3880 u in F5 -- stricter than the session, which
  accepts a later attempt.)
- **F6 (keys and pattern).** Per R-FULL run exactly the 39 keys and the 12 masked rows; no error-path, dead, forbidden or
  inert row; the four residue rows and none after; 154's first `w` row ip26 and its first Byte[13] row ip123 from old 1;
  every visit's sequence exactly 4.16's, no `c` row; the cut 164 e0 t0 ip22; the two runs key for key and tuple for tuple
  identical (frames aside); any difference explained at the byte level before the freeze.
- **F7 (end state).** Every R-FULL `end_state` (live, without Byte[13]) equals 4.9; the trace's last pre-cut Byte[13]
  row 163 ip684 = 2; the live Byte[13] read recorded (expect 1 or 2: never compared).
- **F8 (budgets).** `run_s` = 2 x the slowest R-FULL; `run_min_s` = 1.25 x the median + the longest measured recovery
  (R-WALK-VOID's, R-FULL's from 164); `session_s` = 8 x the median + 1800; `no_progress_s` = max(60, 3 x the longest
  no-progress stretch of any traced stage); `settle_s` 1.0.
- **F9 (recovery).** R-WALK-VOID: both stops with no `hold` / no further press after the raise, `recover-warp` 4600, then
  the title; R-FULL's `end_run` from 164 reaches the title.
- **F10 (settings and launch).** P-SETTINGS (incl. [AnalogControl] and PSXMovementMethod), P-PAD, P-OVERRIDE, P-ENGINE,
  P-LAUNCH, P-DONOR-LOG pass on the rehearsal launch; its fingerprinted settings and engine equal 4.13's.
- **F11 (the input witness).** No `input` row in any run.
- **F12 (F-SMOKE).** The seven members load as their twins.
- **F13 (F-PASS: may only STOP the session).** Reached 31256 with no throw and no V-class; anything else is a FINDING
  written into PLAN.md first.
- **F14 (render rates).** Every run's measured rate recorded; the set seen goes into `rehearsal_fps`. A rate no stage met
  is named in PLAN.md as unexercised (the session may meet it) -- the game picks its rate; nothing forces one.
Then `--freeze` (v1). `freeze_problems` refuses: no `witness`; a table step carrying a rehearsal overlay (`hold_stop`,
`page_stop`) or a typed `stale_slack`; any step without `clearance`; 154 step 0 without the hazard in `avoid` or without
`basis` "prior"; `side_ends` failing `side_ends_of`; a non-empty `battles`, `naming`, `start_dependent` or
`pattern.floating`; `Global.Byte[13]` in `end_state` (it races: `end_state_trace`); a `carried` target in `end_state`, or
a `carried` that differs from `carried_from_segments`; no `start_reads`; an `interruptions` test that is not
`monologue_test`'s reading; empty `rehearsals` or `rehearsal_fps`; an `engine` that is not the live DLLs'; an existing
file.

### 7.4 After the freeze: the session (the lead)
G1: `--preflight` all green on the session's launch. G2: unattended, hands off: `py tools/play.py studies/story-trace/
o7_castle_walk.py --label story-o7 --timeout 240`.

---

## 8. The dry run (`o7_dryrun.py`: synthetic sessions through `O7.analyse`)

Built like `o6_dryrun.py`: its own `render` (O6's, with O7's start values -- SC 1190, FieldEntrance 315, Byte[13] 1,
Int16[9] 643, Int16[11] -1, Byte[14] 0, Byte[8] 125, every other target 0 -- and the sink's per-site rule), O3's event
helpers, O5's `at(frame)` anchors and store options, and O3's EXACT `case()` (every check a case does not name must read
PASS; a COVER-VOID case expects every core check VOID; LANDING, WALK, PATTERN, STATE and VOID-ASYM cases register the
clause the detail names). Every case reads freeze-time values -- budgets, `rehearsals`, `rehearsal_fps`, the steps'
`start` -- from the predictions it is given: C2 and G39 run every case on the draft (or the frozen file) AND on
`as_if_frozen(draft)` (every budget x1.5, `rehearsals` and `rehearsal_fps` named, each step's `start` moved 20 u), N/N each.
- **Real store sites** (every field row joins): 4.3-4.6's and 164's post-cut prologue.
- **A base run**: `arm` (fld 70); the four residue rows; visit 1's 7 rows (154: the walk's row `done` with its `to` at
  (5, -610) control true, its route `basis` "prior" and a `basis_check` (angle 1.2), then the cross's `done`, `lost`
  (0, -4080) in 154's field, `landed` 158 / 31250, `flip_frame`); visit 2's 9 (158); visit 3's 11 (159: the interrupted
  row with `lost` (-1601, 1572), then five page presses, the three monologue rows inside the gap, the re-run's done row
  with `lost` (-2445, 365) and `landed` 160); visits 4-6 (8 each); each seeded visit's first row `basis` "prior" with one
  `basis_check`; the static watch's `seen` row in 154 (sid 5 at (-2700, -1700)); 164's ip22 (the cut) and its post-cut
  rows; `off`. 159 ip290's row reads old 125. On F the members' ids. Every VOID a case adds carries its cell.

| Case | Want |
|---|---|
| null-pair | PROVEN |
| fork-drops-a-write (no 159 ip672 on F) | NOT PROVEN (WRITES F, NULL F, STATE F, PATTERN F (b)) |
| monologue-absent-F (every F run: no interrupted row, no ip613/648/672: the fork's monologue never ran) | NOT PROVEN (WRITES F, NULL F, WALK F (b), PATTERN F (b), STATE F) |
| monologue-absent-one-F | NOT PROVEN (STABLE F, WRITES F, WALK F (b), PATTERN F, STATE F) |
| chain-dropped-fork (no 160 ip227 on F) | NOT PROVEN (CHAIN F, LANDING F (b), WRITES F, NULL F, STATE F, PATTERN F (b)) |
| chain-first-old-wrong (both: 154 ip355's old 316) | NOT PROVEN (CHAIN F alone) |
| start-residue-three (S: byte 3's row missing) | NOT PROVEN (START F) -- O6's three-row contract would pass it |
| start-residue-wrong (S: byte 2 0 -> 58) | NOT PROVEN (START F) |
| start-first-missing (both: 154's ip26 dropped) | NOT PROVEN (START F, PATTERN F (b); re-registered with its reason if MASKED co-fails) |
| start-music-old-wrong (both: ip123's old 2) | NOT PROVEN (START F) |
| front-cut-write (F: a `w` row in fld 70 before the start) | NOT PROVEN (START F) |
| error-path-start-S (one S run: 154 ip101, window 56, V5 driver [154, 1190, 1]) | PROVEN (S 2 of 3); A-START |
| byte8-early-warp-one-F (one F run: 159 ip290 reads old 0 -- the warp left 70 before ip249 -- and is emitted 0 -> 125, same 0) | PROVEN (F 2 of 3); A-START (the start read), never PATTERN |
| byte8-early-warp-all-F (every F run reads old 0 at 159 ip290) | VOID (COVER V; VOID-ASYM P) -- the start's problem on a whole side, never NOT PROVEN |
| v5-error-158-F (one F run: 158 ip97, V5 game [158, 1190, 2]) | NOT PROVEN (VOID-ASYM F (a)) |
| residue-after-start (F: an `r` row on byte 300) | NOT PROVEN (RESIDUE F) |
| writes-extra-symmetric (both: 160 e5 t2 ip199) | NOT PROVEN (WRITES F, PATTERN F (b); NULL P) |
| forbidden-row-both (both: 159 e5 t3 ip636) | NOT PROVEN (WRITES F, PATTERN F (b); NULL P -- any further co-failure re-registered as rendered) |
| inert-row-both (both: 154 e2 t1 ip1520) | NOT PROVEN (WRITES F, PATTERN F (b); NULL P) |
| extra-key-one-F (one F run: 160 e2 t3 ip298) | NOT PROVEN (STABLE F, WRITES F, STATE F, PATTERN F (b); NULL P) |
| sc-write-fork / sc-harness-poke-both | NOT PROVEN (NO-SC F, ...) / (NO-SC F alone) |
| c-row-158-F / byte13-repeat-both / monologue-order-swap-both | NOT PROVEN (PATTERN F (a) alone) / (PATTERN F (b) alone) / (PATTERN F (b), STATE F (a)) |
| lands-real-158-covered (every F run: 158's rows at fld 158) | NOT PROVEN (LANDING F (a)(b)(e), FORBIDDEN F, WRITES F) |
| harness-after-exit158-both | NOT PROVEN (LANDING F (b) alone) |
| field-order-flip-both (visits 3 and 4 swapped) | NOT PROVEN (LANDING F (b), CHAIN F, PATTERN F (b), STATE F (a) -- re-registered as rendered) |
| last-place-harness-both / end-real-164-F / end-boundary-residue-both | NOT PROVEN (LANDING F (c) / (d) / (d) alone) |
| end-row-missing-one-S | PROVEN (S 2 of 3); A-NOEND |
| v19-one-F (one F run VOID V19 at [158, 1190, 1]) | NOT PROVEN (VOID-ASYM F (a)(c)) |
| walk-into-balcony-branch-S (one S run: the cross V11 driver at [154, 1190, 1], `landed` 153, e8 ip195's row and rows in 153, backed) | PROVEN (S 2 of 3); A-FORBIDDEN |
| balcony-branch-unbacked-F | NOT PROVEN (FORBIDDEN F + co-failures as rendered) |
| v11-balcony-all-F | NOT PROVEN (VOID-ASYM F (b); COVER V) |
| wrong-door-e9-S (one S run V11 driver: e9 ip355, rows in 155, backed) / wrong-door-unbacked-F | PROVEN (S 2 of 3) / NOT PROVEN (FORBIDDEN F) |
| back-door-158-S (one S run: 158 e1's rows, then 154 out of order: V11 driver on the walked row) | PROVEN (S 2 of 3) |
| stall-at-163-one-S / v7-stair-all-F | PROVEN (S 2 of 3) / NOT PROVEN (VOID-ASYM F (b); COVER V) |
| v7-monologue-all-F (every F run V7 driver at [159, 1190, 3]: a second monologue) | NOT PROVEN (VOID-ASYM F (b); COVER V) |
| v13-prior-one-F / v13-prior-all-F | PROVEN (F 2 of 3) / NOT PROVEN (VOID-ASYM F (b); COVER V) |
| v13-input-one-F / v14-one-S | PROVEN (F 2 of 3) / NOT PROVEN (VOID-ASYM F (a)) |
| dojebon-released-S (one S run's log holds a `moved` row for sid 5) | PROVEN; the report names it |
| dojebon-unobserved-S (one S run's log holds no `seen` row for sid 5) | PROVEN; the report reads UNOBSERVED for that run, never "static" |
| walk-* (5.3's seventeen WALK mutants: (a)-(c)'s fourteen, (d)'s three) | NOT PROVEN (WALK F, the clause named) |
| walk-failed-once-162-both / walk-failed-twice-163-both / walk-interrupted-once-160-both / cross-lost-unread-both / basis-check-on-step1-154-both | PROVEN |
| w154-beat-missing / x163-beat-missing (two S runs) | VOID (COVER V; VOID-ASYM P) |
| end-cut (S: rows in 164 past the end) | PROVEN |
| end-state-differs / byte13-live-race-both / byte13-trace-end-F | NOT PROVEN (STATE F (b)) / PROVEN / NOT PROVEN (STATE F (c), RESIDUE F) |
| masked-differs / join-failure | NOT PROVEN (MASKED F, PATTERN F (b)) / (JOIN F alone) |
| mismatched / no-start-row | PROVEN; that run A-MISMATCH / A-NOSTART |
| trace-without-off / install-changed / predictions-changed | VOID / VOID / NOT PROVEN (FROZEN F) |

A want the code cannot hold is explained at the byte level and re-registered, never loosened (O3-O6's rule).

Units (no session): **step-of-walk** (S17's refusals; O1-O6 frozen tables unchanged); **walk-kw** (the two keys only
when given); **instanced-at7** (154 at 315 -> {object 5, 6, 7, 15; region 8, 9, 10; code 1, 11}, e2 not; 159 -> all its
Inits; 160 -> InitObject 2 included; O4's raises on 159 -- the reason O7 has its own); **render** (the base run: 51 `w`
rows before the cut, no `c` row; the same events through the FakeGame's H13 knob give the same sequence); **pattern**;
**trace-summary** (cut at end places; given end FIELDS on F, not cut -- the mutant); **state-history** (Byte[13]'s
eleven entries in order; Byte[208] `[(159, 0), (159, 1)]`); **visit-windows** (each clause's PASS and FAIL; the 154
window spanning both steps and the gap between them; a `walk` row ending at its `frame`); **walk-check** (pure, every
clause incl. (d); F-side: (b)'s loss read at 31251 passes, at 159 fails), **landing-check** (pure, every clause;
landing-e alone); **state-c-by-place** (F rows at 31255 match 163's site; renumbered to fld 163 they do not);
**static-watch** (keyed by place: 31246 on F reads as 154; one `seen` row per visit, one `moved` row on a release,
UNOBSERVED with sid 5 unpublished); **seeded-fields** (154, 158, 160, 162, 163 and 31246, 31250, 31252, 31254, 31255;
159 and 31251 not); **monologue-test** (reads (-1600, 1600, 800, 3796) off the pinned text; a mutated constant changes
it; another shape None); **dojebon-test**; **why-void** (A-START on 154's ip101, none on 158's ip97; A-START on 159
ip290 read with old 0, none with 125 -- on S and on F); **as-if-frozen** (changes exactly its keys; `freeze_problems`
accepts them); **fallback-end** (4.17); **closures154** (the derivation equals the frozen lists; break: the 2% shrink
dropped -- shared edges count); **store-census** (PASS with 6.1's line; mutants each FAIL by name: 154 e2 registered not
inert, 160 e2 registered inert (instanced by the flag-gated InitObject), 159 ip672 removed from the writes, 162 e2 ip199
removed from `dead`, 154 ip101 removed from `error_path`); **regions** (PASS; mutants: 154.e8 without its balcony
branch, the hazard under an `e<sid>` key, the hazard with role exit, the hazard out of step 0's `avoid`, 159.e11
missing, 160.e5's points shifted); **goals** (PASS; mutants: 163 at clearance 120 (g1: no route), 160 at 110 (g1: a
route exists at 120), 158 without e1 in `avoid` (g2), 154 #0's goal (0, -3700) on the balcony (g3), 154 #1 without its
closures (g4: balcony tris inside e8), 159's `test` x_lt -3600 (g5: e11 outside it), 154 #0 without `basis` (h2),
without the hazard (h3), a goal pulling the route east past x 254 on the balcony (h1), the hazard shifted 50 u east (h4:
gap 104 > 86), its north edge 300 u south (h4)); **route-pins** (PASS; mutants: 154 e8 t2 ip38's constant, 159 e16 t1
ip390's, a second DefinePlayerCharacter in an instanced entry, a party op, a `Map.Bit[144]` store, mes 300 without its
text, field 70 e0 t0 ip249's constant); **build-pins** (O5's unit on O7's members); **keys offline mutants** (a write's
value; a chain `off` + 1; `start_first`'s target; `start_music` at ip142; a start-scoped `after.old` 7; `after.run`
"O1-O5"; the ip648 `++` prior removed; O6's pattern with its 153 Int16[9] tuple 385 (the derived `after.old` 385 against
the typed -1); a `start_reads` site off the writes, or with an earlier Byte[8] store before it on the route; `carried`
without Bit[3815]; `carried` with Byte[206] (noise); Bit[3795] in `end_state` (a carried target claimed); a carried
target given a route store site; a frozen segment whose list order contradicts its own `end_state` (the derivation
refuses)); **carried-derivation** (over the repo's six frozen files: the fourteen of 0.2 #18, no segment disagreeing
with its `end_state`; the `after.old` 1799 of O6's UInt16[19] key used, never O1's absent bits); **p-settings**
([AnalogControl] UseAbsoluteOrientation 1 FAILS; PSXMovementMethod 0 FAILS), **p-donor-log**, **p-launch**, **p-pad**,
**p-override**, **p-engine**, **text-strict**, **input-witness** (O4's/O5's units on O7's values).

It prints the summary columns (FROZEN COVER FORBIDDEN VOID-ASYM START NO-SC CHAIN RESIDUE WRITES NULL STABLE LANDING WALK
PATTERN MASKED STATE JOIN) and "N/N cases as registered", exiting 1 on any miss.

---

## 9. Build order (three parts; no deploy, no game, no `tools/play.py`, no full suite)

**BUILD TESTING (PLAN.md "Build testing" -- it overrides every earlier design's section 9; never "the whole file alone,
serially").** pytest from `ff9mapkit/`, the study scripts from the worktree root. `<S>` is
`C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX\2b528e1b-375b-4c19-8f5f-30afde944b42\scratchpad\o7_build`.
- **Inner loop**: only the `-k` selections you touched -- `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W
  ignore -k <expr>`, with `-n 4` past 10 tests. Mid-PART regression checks: `py studies/story-trace/segment_regress.py
  --only <items your change can move>` (a PARTIAL run exits 3 and prints NOT THE GATE: that is its pass).
- **At the END of each PART, ONCE**: `py studies/story-trace/harness_tests.py whole --out <S>\<part>` (the whole file at
  `-n 8`, THE FLAKE PROTOCOL, a receipt), then `py studies/story-trace/segment_regress.py --pytest-junit
  <S>\<part>\receipt.json` (the full gate, exit 0), plus the CLI checks the PART lists. Both can run past 10 minutes
  under load: start each in the background and wait in loops of at most 9.5 minutes; never poll every few minutes.
- **GREEN RECEIPT**: a stage whose HEAD and tree match the previous stage's receipt (`py studies/story-trace/harness_tests.py
  check <receipt>` exits 0) does not re-baseline. Never re-run a `-k` selection a whole-file run at the same HEAD and tree
  contains.
- **FLAKES**: the tools re-run only failed tests alone (3/3 a named flake); never re-run a whole file or the gate for a
  flake; name every flake in the commit message. A test that fails alone is a real failure. A load- or order-sensitive
  test is a TEST defect: fix the test.
- **Load-robust tests** (the nightly runs the whole file at `-n 6`, builds at `-n 8`): a drive test re-runs its run (at
  most 2 more) only when it ends in a DRIVER class a starved harness can cause (V13 budget; V7 by a timed-out or stalled
  walk -- the real-mesh walks; a failed walk ended short by a stall), asserting the class on each discarded attempt; a
  GAME class, a V11, a V19, a V13 of the prior basis (a rotated prior is deterministic) or a wrong verdict is never
  re-run. Every race is reproduced by a deterministic stall (a wrapped call, `fake.stall_publish`, the exit gate), never
  real starvation; the fake's loop runs at most 4x its `render_fps`. A test asserts nothing a lead's in-game step changes:
  no deployed flag, no gate witness, never the draft's `rehearsals` / `rehearsal_fps`, never an unfilled draft value (O2,
  O4, O5 and O6 each lost a pre-merge run to that).
- Commit on the branch when a step is green, one step per commit, each message ending with "Co-Authored-By: Claude Opus
  5.5 <noreply@anthropic.com>". Non-ASCII files with Python (utf-8) or the Edit/Write tools; frozen JSON and baselines
  LF (`-text`); a Windows path in Python raw or escaped.

### PART A -- the regression gate extended to O6 (baseline FIRST), then the shared opt-in changes
0. **Before anything**: `git log --oneline master..HEAD`, `git status`; read `C:\gd\Dream-World-IX\.test-gate\latest.json`
   (green at c954f986: 11244 passed, 1 xfailed; red -> triage first) -- PART A starts from master's merge gate and this
   ledger, not a new baseline; the branch-point count of `tests/test_harness.py` (`py -m pytest tests/test_harness.py
   --collect-only -q -p no:cacheprovider`, a collection, no run) goes into A0's commit message.
1. **A0: the O6 gate and its baseline, FIRST** (1.4): G0''''' `--capture-o6` with its two-readings rule and refusals;
   G34-G37; `FAKE_PINS_O6`, `fake_pins_o6()`, `o6_pin_names`; `PIN_BASELINES` four and `union_sources` / `union_base` /
   `g21` / `--rebaseline-source` over four (three-baseline calls exactly today's); `--baseline-o6`; `PYTEST_K_O7`,
   `REQUIRED_TESTS_O7 = ()`; `_missing()`'s `o6s`/`o7`; the module docstring (G0''''', G34-G39); the registry test renamed
   and extended to G37; `test_segment_regress_o6_pins_join_the_union`. Run `py studies/story-trace/segment_regress.py
   --only G32,G33` (O6's items green at the head first; exit 3), then `--capture-o6`, and commit
   `research/o6_regress_baseline.json` with its `.gitattributes` line before any other code change; then `--only
   G34,G35,G36,G37,G21` (exit 3).
   **A0b: THE O6 REPLAY, BEFORE ANY FAKE EDIT** (3.7): `test_fake_level_keeps_the_steiner_route_identical`; capture with
   `O7_CAPTURE_REPLAY=1`, commit the golden with its `.gitattributes` line; then `-k "keeps_the_steiner or
   keeps_the_hallway"` (2 passed).
2. **A1: S17** (`STEP_KINDS`, `STEP_NEEDS`, `WALK_REFUSES`, `BASIS_KINDS`, `step_of`'s refusals, `x_walk`, `walk_kw`'s keys,
   `run_step`'s row keys, `trim_route`'s keys) with its seven tests (1.2). Breaks: done on `reached` alone; the walk's
   landing read as done; the refusals dropped. Mid-PART: `-k "segment_walk or segment_step_of"`; `segment_regress.py
   --only G3,G4,G10,G11,G17,G18,G24,G25,G30,G31,G36,G37` (every dry run and offline check reads its tables through
   `step_of`: exit 3).
3. **A2: S18** (session.py's `clearance` threading; `walk_kw`) with its three tests. Break: the key dropped in
   `_plan_round`. Mid-PART: `-k "segment_route_clearance"`.
4. **A3: S19** (the seed, `_seeded`, `_prior_pending`, `_prior_angle`, `_field_spread` -- wide until the first move is
   judged, floor + theta after -- the first-move check and its marker, `forget_basis` at every pop of `_axes`,
   `begin_scenario` clearing S19's state, `run_step`'s conversion keyed on the marker) with its seven tests (1.2).
   Breaks: no check; the check under `slides` skipped; the spread not widened; the spread never narrowed; a pop that
   leaves `_prior_pending`; the conversion keyed on the step. Mid-PART: `-k "segment_prior_basis"`; `segment_regress.py
   --only G26,G32` (O5's and O6's drives on the fake run route_to's spread and both pop sites, now through
   `_field_spread` and `forget_basis`: exit 3).

**PART A REQUIRED-GREEN** (at A3's head, once):

| Command | Expected |
|---|---|
| `py studies/story-trace/harness_tests.py whole --out <S>\A` (background, waits <= 9.5 min) | exit 0; the receipt for HEAD and the tree; every test passed or a NAMED flake, 0 failed, 0 skipped, the ledger's xfail; collected = the branch point's + PART A's 19 (A0's one, A0b's replay, A1's seven, A2's three, A3's seven) |
| `py studies/story-trace/segment_regress.py --pytest-junit <S>\A\receipt.json` (background) | exit 0; G1-G37 and G21 PASS (G21 over four baselines; no re-baseline row in PART A: S17-S19 -- `forget_basis` and `begin_scenario` included -- touch no pinned test or fake function) |

### PART B -- the FakeGame for O7's route, then the driver's O7 tests
1. **B1: H20, H21** (`Levels`, `LEVEL_STEP_DY`, `LEVEL_BAND`, `SQUEEZE_SLACK_W`, `fake.levels`, `place_height`, `_move_to`'s
   level and squeeze branches, `_VisitBeat._place`, `_visit_steps`) with six tests (3.1, 3.2). The two O5 pins edited are
   re-baselined by name IN THIS COMMIT (`--rebaseline-source NAME --reason TEXT`); then `-k "fake_level or
   keeps_the_hallway"` (both replays identical) and `segment_regress.py --only G21` (exit 3).
2. **B2: H22, H23** (`DOOR_KEYS`, `DOOR_DEFAULTS`, `_door_knobs`, `_VisitBeat._door`'s height terms and scenes,
   `_step_walkers`' `hold`) with six tests (3.3, 3.4). The two O6 pins edited are re-baselined in this commit; then `-k
   "fake_level or fake_monologue or fake_patrol or keeps_the_hallway"` and `segment_regress.py --only G21,G26,G32`
   (O5's and O6's fake and driver tests on the edited `_VisitBeat`: exit 3).
3. **B3: the O7 route builder** (`_o7_route`, `_o7_register`, `_O7_FIELDS`, `_O7_BOX`, test-side) and
   `test_fake_level_route_plays_to_164_unattended` (3.6).
4. **B4: the driver on the fake.** O7's predictions on the fixture (`_o7_pred`: the six cells on the fixture's ids, the
   regions keyed by them, `side_ends` {S: [30846], F: [31256]}, the members, `steps_default` O6's) and `_o7_run` /
   `_o7_run_informative` (O6's shape; `g._axes` NOT pre-seeded where a test exercises S19). Tests (S at 60 fps mean
   ticks, F through the members at 31 fps quantized where named; `wait_scale` 0.25; `story_suppress` on):
   - `test_o7_drive_walks_the_castle_to_164_on_the_fake` -- S and F on the box: all seven beats; 159's one interrupted
     row and its three rows in the gap; the pattern by ip (4.16); the end row 164 ip22 (31256 on F); `end_state`; no
     forbidden row. Break: the monologue scene without `unless_bit` (V7).
   - `test_o7_drive_walks_the_real_balcony_to_the_ground_on_the_fake` -- stock 154 with `levels154`, `fake.clearance`
     120, 154's own twist, the driver's floor `PlayerWalkmesh(stock 154, closed)` and the frozen step pair (`basis`
     "prior", clearance 120, the two closure lists from `closures154`): both steps done, step 0's end y < 100, the
     landing 158, `_probe_axis` never called, Dojebon (H23) never moved. Reads the install (a warned skip fails G38).
   - `test_o7_drive_balcony_cross_lands_in_153_is_the_drivers_v11` -- stock 154, a mutant table (one cross from the spawn
     with no closures): the balcony branch fires, V11 driver at [30840, 1190, 1], the step row's `landed` 153's fixture id.
     Break: the door without height terms (the ground branch fires and the step is done).
   - `test_o7_drive_squeezes_the_real_stair_on_the_fake` -- stock 163, `fake.levels` with `squeeze_slack` 8,
     `fake.clearance` 120, the cell at clearance 110: done, the landing 164. Break: clearance 120 -- "no route", failed
     three times (`attempts` 3), V7 driver.
   - `test_o7_drive_stair_snags_twice_then_squeezes_on_the_fake` (rev. 2, driver review #6) -- the same cell (`attempts`
     3), and a test-side wrapper on `g.route_to` that holds `squeeze_slack` at 0 for 163's first two calls (the fake then
     snags at the 116.7 pinch as an engine that snags would: waits, a push, a blocker, "no route", frozen) and restores 8
     for the third: two `failed` rows, then done, the landing 164. Break: `attempts` 2 -- V7 driver at [30845, 1190, 6].
     Deterministic: the snags are by call count, never by time.
   - `test_o7_drive_second_monologue_is_v7` -- `store_override` {672: 0}: V7 driver at [30842, 1190, 3].
   - `test_o7_drive_prior_basis_is_the_drivers_v13` -- a rotated prior on 158's cell: V13 driver at [30841, 1190, 2].
   - `test_o7_drive_fork_landing_in_real_158_is_v19` -- F, `land_real` {"158": 30841}: V19 game at [30841, 1190, 1]
     (rule 2 judges before rule 3 counts the visit).
   - `test_o7_drive_wrong_door_e9_is_the_drivers_v11` -- a mutant table walking into e9 on the ground: V11 driver,
     `door` 30840.e9, `landed` 155's fixture id, its rows backed.
   - `test_o7_drive_stop_page_in_154_is_v5_driver` -- `error_window` {1: 2}: V5 driver at [30840, 1190, 1]; {2: 2}: V5
     game at [30841, 1190, 2].
   - `test_o7_drive_walk_into_a_door_is_the_drivers_v11` -- 154's walk step with e8 removed from `avoid` and a goal past
     it on the box: the walk's loss in e8, its switch, V11 driver.
   In this commit every `test_o7_*`, `test_fake_level_*`, `test_fake_monologue_*` and `test_fake_patrol_*` name goes into
   `REQUIRED_TESTS_O7` and G38 joins the gate (registry and its test updated to G38). Mid-PART: `-k "o7_drive"` (`-n 4`);
   `segment_regress.py --only G38` (exit 3). The `_o7_pred` cells carry the draft's `attempts` (3 on 154 #0 and 163 #0).

**PART B REQUIRED-GREEN** (at B4's head, once):

| Command | Expected |
|---|---|
| `py studies/story-trace/harness_tests.py whole --out <S>\B` (background) | exit 0; PART A's count + PART B's 24 (B1's six, B2's six, B3's one, B4's eleven), every one passed or a named flake, 0 skipped |
| `py studies/story-trace/segment_regress.py --pytest-junit <S>\B\receipt.json` (background) | exit 0; G1-G38 and G21 (its four re-baseline rows -- `_visit_steps`, `_VisitBeat._place`, `_door_knobs`, `_VisitBeat._door` -- named in B1's and B2's commits) |

### PART C -- O7 itself
1. **C0: measure, read-only.** On O4's build (`C:\gd\_ns_playtest\o4\build`, never written): the seven route members'
   byte diffs against their donors per language (O7-BUILD's pins) and the chain's `campaign.toml` (route members 31246,
   31250, 31251, 31252, 31254, 31255, 31256 -- anything else STOPS PART C). No commit (the numbers go into C1's
   `o7_forks.json` `built.measured`).
2. **C1: `o7_castle_walk.py`** (1.3, sections 4-6), `o7_forks.json` (6.4), the `.gitattributes` line. Tests (into
   `REQUIRED_TESTS_O7`): `test_o7_castle_draft_reads_the_chain_from_campaign` (rehearsals read from the draft, never a
   literal); `test_o7_castle_freeze_refuses` (each refusal of 7.3); `test_o7_castle_route_builder_matches_the_keys`;
   `test_o7_castle_instanced_at_reads_no_dispatch_and_flag_gates`; `test_o7_castle_census_classifies_every_site` (the
   real bytes: PASS, the counts derived; 160 e2 registered inert -> FAIL; 159 ip672 out of the writes -> FAIL);
   `test_o7_castle_regions_roles_branches_and_hazard`; `test_o7_castle_goals` ((g1)-(g5), (h1)-(h4), each with its
   mutant -- (h4)'s the hazard shifted 50 u east); `test_o7_castle_closures154_follow_their_definitions`;
   `test_o7_castle_monologue_test_reads_the_pinned_text`; `test_o7_castle_walk_check` (pure: every clause incl. (d), the
   gap exemption only for the registered rows, the 154 window across both steps, (b) by place on F);
   `test_o7_castle_landing_check_crossings`; `test_o7_castle_state_reads_byte13_from_the_trace` (by place: 31255 on F);
   `test_o7_castle_fallback_end_is_one_line`; `test_o7_castle_static_watch_reads_the_patrol_once_per_visit` (a fake
   Dojebon: one `seen` row per visit; released, one `moved` row; sid 5 unpublished, no `seen` row and the report's
   UNOBSERVED; on F keyed by place, 31246 reading as 154; break: a row per sample);
   `test_o7_castle_keys_derive_the_carried_and_the_olds` (rev. 2: over the repo's six frozen files the fourteen carried
   values; the start-scoped `after.old` from O6's pattern; the start read's site; mutants -- carried without Bit[3815],
   Bit[3795] in `end_state`, O6's 153 Int16[9] tuple 385, a start read off the writes -- each failing O7-KEYS by name);
   `test_o7_castle_start_run_forgets_every_seeded_basis` (a session's `_axes` and S19 state holding 154, 158, 159, 160,
   162, 163 and their members: `O7.start_run` -- New Game, the warp on the fake -- leaves none of the seeded ones, S or F,
   and keeps 159's and 31251's calibrated bases; break: no `reseed`); `test_o7_castle_why_void_reads_the_start_byte8`
   (159 ip290 old 0 -> A-START on S and on F; 125 -> none); `test_o7_castle_preflight_verdicts` (P-DONOR over the seven,
   P-TEXT3 strict, P-SETTINGS failing on UseAbsoluteOrientation 1 and on PSXMovementMethod 0). Mid-PART: `-k "o7_castle"`.
3. **C2: `o7_dryrun.py`** -- every case and unit of section 8, on the draft AND `as_if_frozen(draft)`, N/N each; G39 joins
   the gate with `O7_DRYRUN_FLOOR` = the count C2 prints (registry and its test updated to G39);
   `test_o7_castle_trace_summary_cuts_at_end_places` lands here. Mid-PART: `segment_regress.py --only G39` (exit 3).
4. **C3: `o7_rehearse.py`** + `--rehearsal-report`. Tests (every one with `warp_arrive_control` False and the engine's
   `soft_reset_ui`): `test_o7_rehearsal_stage_ids_follow_the_chain`; `test_o7_rehearsal_plumbing_on_the_fake` (R-FULL's
   record holds every 7.2 section); `test_o7_rehearsal_walk_void_stops_mid_walk_on_the_fake` (`hold_stop`: the raise
   before the 4th walk hold, no hold after it, `recover-warp`, the title); `test_o7_rehearsal_walk_void_stops_mid_
   monologue_on_the_fake` (`page_stop`: the raise on the first page press in 159, a window listed; the warp from FieldHUD;
   the title); `test_o7_rehearsal_records_dojebon_and_the_rates_on_the_fake`;
   `test_o7_rehearsal_judges_every_runs_first_move_on_the_fake` (rev. 2: R-WALK154's two runs in ONE launch -- each
   run's 154 #0 route `basis` "prior" with its own `basis_check`, `_probe_axis` never called; break: no `reseed` -- the
   second run reads "cached" with no check); `test_o7_rehearsal_places_the_ladder_rungs_on_the_fake` (stock 163 with the
   squeeze held off for one call: THE LADDER TAP records the waits, the push and the blocker, each with the stalled
   hold it followed, which ended inside THE FOOT WINDOW, and `--rehearsal-report` names F5's NO-GO for that run; a rung
   the test provokes after a hold wholly elsewhere on the stair -- a fake blocker body on the upper flight -- is recorded
   and not judged); `test_o7_rehearsal_smoke_sends_no_storytrace_on_the_fake`;
   `test_o7_rehearsal_fpass_runs_untraced_to_the_member_on_the_fake` (F-PASS reseeds first). Mid-PART:
   `-k "o7_rehearsal"`.
5. **C4: the O7 section in `PLAN.md`** -- the question, the segment, the sides and their ends, the start and its scope
   (no start-dependent key; the olds; the carried values), the walks (S17-S19), the monologue, the end state's race, the
   checks, "draft: rehearsals pending, freeze pending", "a US session" in its heading, and THE O8 HANDOFF (9.1, verbatim).
   The brief's milestone line (CLAUDE.md section 10) is left as it is.

**PART C REQUIRED-GREEN** (at C4's head, once):

| Command | Expected |
|---|---|
| `py studies/story-trace/o7_castle_walk.py --offline-check` | exit 0; "predictions: the draft"; the chain line (member(154) 31246 ... member(164) 31256); 6 PASS -- O7-BUILD, O7-KEYS, O7-TEXT, O7-CENSUS, O7-REGIONS, O7-GOALS, each detail 6.1's line |
| `py studies/story-trace/o7_castle_walk.py --preflight` | exit 0, ALL GREEN (12) -- or the exact failing line reported to the lead |
| `py studies/story-trace/o7_castle_walk.py --draft` | exit 0; the draft: `side_ends` {"S": [164], "F": [31256]}, `visits` the six, the seven steps each with `clearance`, 154 #0 and 163 #0 with `attempts` 3, 154 #0 with the hazard and `basis` "prior", `interruptions` with the read test, `start_reads` (159 ip290, 125), `carried` the fourteen derived values, `end_state` without Byte[13] and without any carried target, `end_state_trace` with Byte[13], `rehearsals` [] |
| `py studies/story-trace/o7_dryrun.py` and `... --as-if-frozen` | exit 0 each; "N/N cases as registered", the same N |
| `py studies/story-trace/harness_tests.py whole --out <S>\C` (background) | exit 0; PART B's count + PART C's tests, 0 skipped |
| `py studies/story-trace/segment_regress.py --pytest-junit <S>\C\receipt.json` (background) | exit 0; G1-G39 and G21 |

Then the lead's sequence (7.1-7.4): `--preflight`, the rehearsals, the freeze checklist, `--freeze` (v1), the session.

### 9.1 THE O8 HANDOFF (C4 copies it into PLAN.md's O7 section)
"**Next, O8:** a raw `warp 164 342 1190` (S) / `warp 31256 342 1190` (F) in field 70 (after 70 e0 t0 ip130, before
ip475): four residue rows (342 = 0x0156: byte 2 0 -> 86, byte 3 0 -> 1); START row 164 e0 t0 ip22, START requires 164
ip130 (`Byte[13]` 1 -> 1, same; ip97 is dead at 164, `Int16[9]` being 385); no start-dependent value or path to the
arrival in 55 -- olds only: 164 ip57 `Int16[9]` (643 -> 385 here, 385 -> 385 after O7), 164 ip130 `Byte[13]` (1 -> 1 / 2
-> 1), 166 e6 t1 ip345 `Byte[208]` (0 -> 0 / 1 -> 0), each `after.old` read off O7's FROZEN PATTERN (the last pre-cut
tuple per target), never an end state read after the site's own field ran; the start read (O7's `start_reads` rule): 166
e0 t0 ip255, the route's first `Byte[8]` store, must read old 125 (a warp before field 70's ip249 leaves 0: A-START);
`carried` DERIVED, never typed: O7's `carried_from_segments` over O1-O7's frozen keys less O8's own targets; the spawn
is the chained arrival's (164 e7 t0 keys on `Int16[2]` alone: (2040, 3335), tri 145, PSX -4780). Route: 164 (Steiner's
radius 80 -- DoEventCode.cs:1507-1508 through EffectiveFieldId, so 31256 too; basis 57.7 deg; the spawn 68 u from a
wall, under the radius: use S19's prior basis; a `walk` to P1 (1342, 2252) with `at_y` [8800, 9150], closures outside
PSX [-9500, -4700], `avoid` [164.e3], npcs off, and THE KNIGHT HOLD -- held at P1, pressing nothing, until the watched
`Bit[3811]` reads 1 (164 e1 t1 ip230 races e2's exit; timeout 15 s, VOID by the game) with an ORDER check (ip230 before
e2 t2 ip243); then a `trigger` into e2 at the top, `until {y_gt: 12000}`, `to` 165, clearance 64 (none at 66+ from P1))
-> 165 (a `walk` to (1508, 4698), `at_y` [11100, 11450], `avoid` [165.e3] live 134 u away; a `trigger` `until {y_gt:
15000}`, `to` 166; 165 e2 ip205 `Byte[13] := 3` live) -> 166 (no control: pages 307, 308, 309, 311, 312, 313,
`Byte[208]`, ip502 `Byte[8] := 0`; FMV004 -- `MBG_DEF("FMV004", 1, 0)`, type 0, 45.41 s live -- PLAYED OUT; ip863
`Int16[2] := 110`, ip871 `Field(55)`, raw on F too) -> END on arrival in REAL 55 at 110 on both sides, cut at 55 e0 t0
ip22; `side_ends` {S: [55], F: [55]} with `members` O4's twenty only (never O1's 31205); `Int16[2]` and `Byte[8]` read
from the trace (55's Main_Init rewrites both at once); a SEAM check (every F run's last chain row 31258 e6 t1 ip863, its
next field 55). O7 built for it: the `walk` kind (S17), the per-step `clearance` (S18), the prior basis (S19, with
`forget_basis`: O8's segment forgets its seeded fields at every run's start, as O7's does), the FakeGame's levels (H20),
squeeze (H21, at the radius less `SQUEEZE_SLACK_W` -- 80 in 164), door height terms and scenes (H22). O8 still needs:
`at_y` on the walk, the bit `hold`, a y axis on `until` (and the loss sample's y from the ring), the FakeGame's spirals
on H20 and a height-triggered walker with a store (the knight), the 5-point regions registered from `scan_gateways`'
`region` (164 e2/e3, 165 e3: dead centres), and the movie's stall freeze (`no_progress_s` >= 2 x R-FULL's measured
static span, ~100 s). Owner options: (1) this 2-way split (O8 = 164 -> real 55), recommended; (2) the critic's 3-way
split -- O8 = 164 -> the arrival in 166 (walk machinery only), O9 = a raw warp into 166 at 344 -> FMV004 -> real 55 (the
movie and the seam only; 166's K -1 takes ip119 from the window's `Byte[13]` 1; no grant there); (3) FMV004 skipped
after O8's own stock A/B (a non-page span key) -- not recommended; (4) 31258 rebuilt with 55 -> 31205 (owner-gated;
breaks O4-O6's P-EB pins) -- not recommended. If O7 took the fallback end (R-STAIR NO-GO), O8 starts with a raw warp
into 163 at 341 and walks 163 first."

---

## 10. Open risks (what only the game can settle)
1. **The grants** (F1): every position is the bytes'; 154's on the balcony (y ~1716) is the walk's premise.
2. **The prior basis** (F2, F4): the first-move check's angle on five fields, in every run (expect under 3 deg); a basis
   the bytes do not predict stops a run (V13), never walks it astray.
3. **154's two levels** (F2): the west arm (330-356 u wide) and the west flight (283-311 u, up to 52.8 deg: ~60% of the
   predicted reach a hold under PSXMovementMethod 1) under the engine's push-out at radius 120 -- the plan runs 122-140 u
   off the railing, so he slides along it for most of the descent (0.2 #17); a stall the waits and the push cannot clear
   costs an attempt (`attempts` 3); e11's camera switch mid-walk (visual, one basis); the ground under the balcony is open
   to the engine as the fake models it (H20) -- R-WALK154 shows it.
4. **Dojebon** (F2): static by S19 (no probe) and the route (3349 < 3420; every re-plan from the drift band within
   3408); a release, or a visit where the watch never read him, is reported and stops the freeze.
5. **159's monologue** (F3): the loss sample (x just under -1600: the slack 180), 297's WindowSync dropping a first
   Confirm, the re-grant in place, the re-run.
6. **160's corner** gone at 120 (min wall 130); the back doors at 61 / 50 / 73 u never neared (no probes; first legs away).
7. **163's squeeze** (F5): a 233-u pinch, 3.3 u a side under the radius, for ~75 u: slides or a stall in THE FOOT
   WINDOW; `SQUEEZE_SLACK_W` (8) is the fake's guess until R-STAIR measures it; the fallback end is one line (4.17).
8. **The doors' fades** (25 ticks) and landings (crossed() waits the switch: `exit_wait_s` 5 s).
9. **The end** (F7): Byte[13] races 164's prologue (read from the trace); the live read recorded.
10. **Render rates** (F14): the game picks ~31 or ~60 fps; a rate no rehearsal met stays named.
11. **The budgets** (F8): estimated; R-FULL freezes them.
12. **The [STNR] pages** render the default name on a raw start (text only, not judged).
13. **The shared install**: A-INSTALL (6.3); `--preflight` on the session's own launch (7.4).

Closed by the bytes or the source (no longer open): the four residue rows; the census's 122 sites and their classes; the
instancing without a dispatch; the pattern's 51 rows; the clearance plans; one basis per field; e8's height branches;
Steiner the controlled character; the monologue's test, pages and rows; the hazard's insufficiency for probes (0.2 #11)
and its coverage of the release zone (0.2 #11, (h4)); the squeeze's model need and the radius it is judged by (0.2 #12);
the carried values (0.2 #18); the start's Byte[8] window (0.2 #19); the per-launch basis cache (0.2 #20); the end row
and the race; no facing gate; no SC rung, battle, FMV, choice, naming or ATE.

---

## 11. Critique log

### 11.1 The research critic's six
Each re-checked in the bytes, the stock walkmesh, the harness or the engine source; none disproved.

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| 1 (major) | Dojebon's release understated; the hazard listed optional and "zero code"; probes judged from where the last left him; the O6-style REGIONS check refuses a non-`e<sid>` key. | session.py:2020-2058 (v before h, each probe from the current position), :1911 (PROBE_HAZARD_PAD 30); L154 e5 t1 ip263 / ip486, e11 t1 ip14-147; `proofs154.py`: 5519 uncovered release points, a 'down' probe leaving him 134 u from the circle | ADOPTED and SHARPENED (0.2 #11): the hazard REQUIRED in step 0's `avoid` (decision 4(d)) with a `hazard` role and key form (O7-REGIONS); the PROTECTION is S19 -- no probe pressed in 154 -- since the hazard alone does not bound a probe with a hitch; O7-GOALS (h1)-(h3), and (h4) its coverage in rev. 2 (11.3, claim #5); his position watched and reported (4.11), a stop in rehearsal (F2). |
| 2 (major) | `unstick: false` does nothing (route_to forces unstick under npcs) and turns a deflection into a wrong-basis error; per-step clearance is the sound fix. | session.py:4373, :3459-3471; segment_drive.py:2522-2529; `plans.py`: 163 routes at 110, none at 116/118/120 | ADOPTED: S18 (`clearance`); 163 at 110, every other walk at 120 (0.2 #5); `unstick: false` dropped; H21 models the engine's squeeze; R-STAIR the go/no-go with the fallback end. |
| 3 (minor) | Calibration beside the back doors can fire them with a hitch at 60 fps. | session.py:2040-2045, tickrate.py:72-77; the gaps 300 / 61 / 50 / 73 u | ADOPTED: S19 on 154, 158, 160, 162, 163 (decision 4(c)); 159 calibrates (its probes stay inside the box); the first-move check keeps a wrong basis detectable. |
| 4 (minor) | The monologue's one-shot trigger and pages are missing from the FakeGame; a `take` region would shadow e11. | fakegame.py:1703-1754 (first match; take fires every entry) | ADOPTED in the visit beat (H22): a scene with the bytes' own guard bit (ip390's `Bit[3796] == 0`, set by ip672), its five pages and stores, the in-place re-grant; tested, and rule 8's re-run crossing e11 in B4. |
| 5 (minor) | "154's 18 store sites" is 22. | the listings' store markers | ADOPTED: 0.2 #2 (122 sites); O7-CENSUS derives and prints every count. |
| 6 (minor) | O8 bundles the spirals, the movie and the seam. | 166 reads Byte[208] after ip345, Byte[8] after its prologue; no grant at 344 | ADOPTED as an owner option in the O8 handoff (9.1 option 2). |

### 11.2 Where this design reads a decision's letter differently (each said, none relitigated)
1. **Decision 4(b)'s "consider 120 for every other O7 walk where it plans"**: taken -- six steps at 120, 163 at 110; the
   draft carries `clearance` on every step and O7-GOALS (g1) refuses a value below the radius unless 120 fails. Its
   "which removes 160's corner and 154's wall hugging" holds for 160 (min wall 130) and NOT for 154 (rev. 2, 0.2 #17:
   the arm and the flight are 283-356 u wide and the plan at 120 runs 122-140 u off the railing): planning at the radius
   cannot keep a radius-120 walker off a wall a corridor that narrow puts 122 u away. R-WALK154 measures the slides.
2. **Decision 4(c)'s "the first move must still detect a wrong basis"**: the first EVIDENCE hold judged at acos(PRIOR_
   AGREE), the calibration's own acceptance, and the spread widened by the same angle until that hold is judged, then
   narrowed to the floor plus the measured angle (rev. 2) so no hold is planned tighter than the check guarantees nor
   wider than it measured; P-SETTINGS pins the setting that picks the operand (the one error the angle cannot see in 154);
   and the check runs in EVERY run, the seeded fields forgotten at each run's start (rev. 2, 0.2 #20).
3. **Decision 4(d)'s "the Dojebon hazard ... (any change logged as a run row)"**: logged in the session too (report-
   only, `static_objects`), with the first reading of each visit logged as well so a watch that never saw him reads
   UNOBSERVED (rev. 2), and in rehearsal a stop (F2). The decided polygon is kept exactly; (h4) pins its coverage.
4. **Decision 5's "a one-shot take trigger or a director"**: modelled as a scene in the door step, guarded by the
   bytes' own bit rather than a one-shot flag: "once" is then the script's, and `store_override` {672: 0} reproduces a
   second monologue (V7).
5. **Decision 6's O7-WALK**: generalized to seven steps; THE PAIRED-WALK LAW checked per VISIT window with exactly the
   registered interruption's rows exempt inside its gap (0.2 #10) and the target door's own rows after its loss; and a
   clause (d) for the seeded fields' first moves (rev. 2).
6. **Decision 7's "O6's FULL preflight set"**: P-NAME is O6's own (the page witness's default name); O7 registers no
   naming, so its list (decision 7 names none) drops it.
7. **Decision 8's "both render rates"**: the game picks its rate; rehearsals record it, the freeze names an unmet rate
   (F14), and nothing forces one.
8. **Decision 9's registry test**: renamed to say what it pins (`..._registry_holds_every_item_once`) so the three later
   extensions edit its body, not its name.
9. **Decision 10 (master moving)**: the lead's merge may meet `source_pins.json` (both sides append: keep all, per name in
   head order), `REQUIRED_TESTS*` additions (keep both), and `segment_regress.py`'s neighbouring lines; then one whole-file
   run and one gate on the merged head.
10. **Decision 3's carried list** ("Byte[6] 0, UInt16[19] 0, UInt16[21] 0, Byte[303] 0, Byte[18] 0, Bit[3855]/[3854] 0,
    party [Zidane]"): kept, and COMPLETED by derivation (rev. 2, claim review #1). Its seven are all among the fourteen
    the frozen O1-O6 keys compose to; the list was O6's handoff, which named only O6's own writes. The decision's class --
    carried, not claimed -- is unchanged; its enumeration is now computed and checked, never typed.
11. **Decision 1's cut "at 164 e0 t0 ip22 ... the fallback end ... a one-line predictions change"**: unchanged by rev. 2;
    `attempts` 3 on 163 #0 (0.2 #17) widens what R-STAIR may pass through, never the go/no-go, which F5 judges in the
    foot window alone.

### 11.3 The design review (rev. 2): driver robustness (8) and claim integrity (10)
Every item re-checked against the code at the branch head, the engine source, the stock bytes and walkmeshes, the six
proven archives or the frozen predictions; the critics' scripts re-run where they measured. All eighteen ADOPTED --
driver #1 with claim #2, and driver #2 with claim #10, each as one change. REJECTED IN PART, each with its reason in
its row: driver #1's "every route field id" (159 stays calibrated), driver #6's first form (a new step key), claim #5's
radius and tolerance as written (3420 and the keep-out margin alone fail the decided polygon), claim #7's START (d)
form. No measurement either review reported was found wrong; one proposed fix (claim #5's, as written) would fail
the decided polygon.

**Driver robustness.**

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| 1 (major) | F2/F4 ask for a `basis_check` in every run, but a basis is cached per field id for the launch: only the first run to reach a field checks it. | session.py:4411 (`origin not in self._axes`), :8312 (`begin_scenario` the only clear; segment_trace never calls it); story-o6's holds per run (7, 3, 3) | ADOPTED, the preferred fix: `forget_basis` (S19, shared) and O7's `start_run` forgetting every SEEDED field, S and F, before each run (0.2 #20; 1.2, 1.3, 2.4, 7.1); F2/F4 per run; tests A3 forget, C1 start_run, C3 two runs in one launch. Narrower than "every route field id": 159's CALIBRATED basis stays cached for the launch -- forgetting it would press its probes again every run for no check (there is no prior to judge), against O2-O6's proven per-launch practice. |
| 2 (minor) | S19's sets are not cleared where `_axes` is: a popped-then-calibrated field keeps `_prior_pending` (a THROW on a step with no `basis`) and the wide spread. | session.py:2210, :3466, :8312 | ADOPTED: every pop and clear of `_axes` goes through `forget_basis` (with `_prior_angle`); `begin_scenario` clears all four; the test pops a still-PENDING field -- by walk_to's burst check and by `begin_scenario`, the only paths that can (the first-move check precedes `_walk_leg`'s own 0.35 test) -- then calibrates: no check runs (1.2). |
| 3 (minor) | `run_step` converts the marker only on a step carrying `basis`; 154's step 1 carries none, so a check that falls there THROWs. | segment_drive.py `run_step` (design 1.2) | ADOPTED: the conversion is keyed on the error's `prior_basis` marker alone -- only a seeded field can raise it, and O1-O6 never seed; the V13 test adds a step without `basis` (1.2). |
| 4 (minor, cost) | The widened spread shortens EVERY hold for the whole session; 1.2 said "near avoided regions only". | session.py:3162-3163 (`drift - reach * tan(spread)` on every hold); `sim2.py` re-run: 154 #1 at 31 fps, 18 holds of 7..1 frames seeded-wide vs 4 probes + 3 holds of 23/23/20 calibrated | ADOPTED: `_field_spread` -- floor + acos(PRIOR_AGREE) until the first move is judged, floor + theta after (calibration's rule), re-read into the leg each hold; the sentence corrected; a pure and a fake test (1.2). |
| 5 (minor) | H21 copied `collRad` 35 (the actor-pair radius) as its bound; the wall push-out is the controller radius 120. 0.2 #12's "226-256 u wide" is an x-extent. | DoEventCode.cs:1523 (`collRad`) vs :1531 (`radius = size * 4`); FieldMapActorController.cs:781, 1060-1254; `foot163.py` re-run: best clearance 116.7 at (2124, 3875), 117.1 at z 3900 | ADOPTED: H21 passes a pinch only down to `fake.clearance - SQUEEZE_SLACK_W` (8, R-STAIR measures it); tests 116.7 passes / 100 stops; 0.2 #12 rewritten (3.2, 9 B1, B4). |
| 6 (minor) | A stall outlasting the waits and the push ends the attempt: the blocker rung (192 u) seals 154's arm and flight and 163's stair; two snags make V7. | pathfind.py:447; session.py:4486-4497 (a call's sealing blockers withdrawn: the next attempt re-plans fresh); `sim2.py 163 60 seed 120` re-run: 2 waits, push `hold up 31`, blocker (2194, 4011), "no route", frozen | ADOPTED in its SECOND form: `attempts` 3 on 154 #0 and 163 #0 (2.4, 2.7, 0.2 #17), a B4 test with two deterministic snags. The first form (a key that re-plans inside the attempt) was not taken: a failed attempt already IS that fresh re-plan from where he stands, so the key would add shared surface for what one table number does. |
| 7 (minor) | 154's corridors are tighter and steeper than written; "120 removes 154's wall hugging" is wrong; H20's "~40 a step" is wrong. | `w154.py` re-run (arm 330-356, flight 283-311, plan 122-140 off); `slope.py`: steepest open tri 205, 79.1 a 60-u step, \|n.up\| 0.604; WalkMesh.cs:2666-2678 (the slope factor) | ADOPTED: 0.2 #17, 3.1's comment and B1's premises test (the measured maximum printed and asserted), 10.3, 11.2 #1; R-WALK154 records predicted vs measured travel and the slide for every descent hold. |
| 8 (minor) | F2 demands step 0's first attempt and F5 a ladder-free 3880 u, stricter than the session's own rule. | the 110 plan 112-119 u off 163's upper-stair wall (under the radius) | ADOPTED: F2 "done within its attempts, no V7"; F5 judges a ladder rung only when the stalled hold it followed STARTED OR ENDED in THE FOOT WINDOW (x 2000-2260, z 3750-4100) -- the critic's rule -- each rung tied to its hold by a ladder tap on `_unstick_leg` (7.1-7.3); a C3 test. |

**Claim integrity.**

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| 1 (major) | `carried` lists only O6's writes; seven O2/O4/O5 targets are missing, and Bit[3795] (carried) is claimed in `end_state` as 0. | `carried.py`: the six archives' S traces composed -- the fourteen of 0.2 #18; `derive_carried.py`: the same fourteen from the repo's frozen keys, each segment agreeing with its own `end_state`; the route listings read none | ADOPTED: `carried_from_segments` (4.5) -- O7-KEYS refuses a typed list that differs, a carried target in `end_state` or stored/read on the route; Bit[3795] moved to `carried`; mutants (Bit[3815] dropped, Bit[3795] in `end_state`); the O8 handoff takes the derivation (9.1); 11.2 #10. One refinement over the fix as written: O1's v4 predictions register only its ladder, so UInt16[19]'s O1 bits come from O6's frozen `start_dependent` `after.old` (1799), never from O1's keys. |
| 2 (major) | Same as driver #1, and no check reads `basis_check`. | as driver #1 | ADOPTED with driver #1: O7-WALK (d) (5.3) -- each seeded visit's first row `basis` "prior", exactly one `basis_check`, at most 16.3 deg -- with mutants basis-check-missing, basis-check-30deg, basis-cached-run3-S; the scope line now says "every run" because (d) enforces it. |
| 3 (medium) | The 154 start-scoped `after.old` came from O6's `end_state`, read after 154's prologue -- the values those very sites write, so a wrong old could not fail. | o6_predictions_v1.json `pattern` (153 ip57 -1, ip119 0, e32 t1 ip1632 1); story-o6's six runs: 154 ip61 -1 -> -1, ip123 0 -> 0 past the cut | ADOPTED: `olds_from_pattern` (4.5, 6.1), the past-cut rows cited as the witness; mutant "O6's 153 Int16[9] tuple 385". The values are unchanged. |
| 4 (medium) | WALK (c)'s two new window shapes (154's two-step window and its gap; a `walk` window ending at `frame`) have no mutant. | 5.3's mutant list | ADOPTED: walk-gap-row-154-both and walk-kind-window-row-both, each (c) alone (5.3, 8). |
| 5 (medium-low) | Nothing pins the hazard's geometry: a shifted or shrunk polygon passes every check. | `hazard_cover.py` re-run; `h4.py` / `h4span.py` / `h4mut.py`: with the 56-u keep-out margin the decided polygon leaves a sliver at e8's corner (3 points of the 16-u grid; the farthest 78 u from e8 on the 8- and 4-u grids) -- the fix's "every point within KEEPOUT margin" would FAIL the decided polygon; `replan3420.py`: 229 re-plans, worst 3408 | ADOPTED, with the tolerance re-derived: (h4) covers the release zone at Dojebon's own 3600 within `KEEPOUT_MARGIN_W` + `PROBE_HAZARD_PAD` (86), printing the residual -- the decided polygon passes, a 50-u shift fails (104). Not at 3420 as proposed: there the residual is the pocket between the spawn, e8 and the hazard (179 points of the 16-u grid, x -176..80, z -4016..-3696, the 3420 circle passing ~71 u from the spawn), which a polygon could cover only by bringing its keep-out margin to ~15 u of the spawn; the decided polygon is decision 4(d)'s and is kept. The reachability is (h1) plus the re-plan census (0.2 #11). |
| 6 (medium-low) | The Dojebon watch cannot fail if he is never read. | 4.11 (only a `moved` row) | ADOPTED: a `seen` row per visit; UNOBSERVED in the report and a stop in F2; keyed by place; a fake test with sid 5 unpublished (4.11, 5.4, 7.2, 7.3, C1). |
| 7 (low) | Byte[8]'s raw-start value depends on the warp's timing (field 70 ip249 sits inside the window); START does not check it. | L70: ip130 `Byte[13] := 1`, ip229-246 the `SYSVAR[3]` wait, ip249 `Byte[8] := 125`, ip475 `Byte[13] := 2` | ADOPTED as the A-START reason (the critic's second form): `start_reads` (4.5), the COVERED rule (5.1), `why_void`; the case byte8-early-warp-one-F PROVEN (F 2 of 3) and -all-F VOID (8); O8 inherits the rule (166 ip255, 9.1). A START (d) core check was not taken: it would turn the instrument's timing into NOT PROVEN, which this item exists to prevent. |
| 8 (low) | Two V-classes for a wrong door landing in a real field on F. | segment_drive.py:2638-2645 (crossed() returns V11 for any landing whose place is not `to`, before rule 2) | ADOPTED, keeping what the code does: V11 (driver), the ids dropped from V19's row, rule 2 reworded (2.2, 2.7); P-EB/O7-BUILD prove those doors' `Field()` retargeted offline. |
| 9 (low) | WALK (b), the static watch and STATE (c) name a donor field where F needs member(place). | 5.3, 4.11, 4.9 | ADOPTED: each matches by `place(fld, members)` (31251, 31246, 31255 on F), with an F-side unit for each and a mutant for (b) (8). |
| 10 (low) | `begin_scenario` leaves S19's sets. | session.py:8312 | ADOPTED with driver #2: `begin_scenario` clears `_axes`, `_seeded`, `_prior_pending`, `_prior_angle`; the forget test covers it. |

**Checked and found to hold** (both reviews): the prior basis at a non-trivial angle (O2's 105 and 115); stacked levels
(no open overlap in 158-163, none left open in 154); re-plans from mid-route; the fake walks at 60 and 31 fps; floor 1
closed by flags in 158 and 162; the field scripts' talk loops, spawn, post-grant stores, the monologue's gate, Dojebon's
creation; the census's 122 sites and per-field counts; the 51-row pattern; the 6-key chain and 33 writes; the 24 dead
and 22 forbidden sites; B_DISTANCEA an XZ distance; the knight's write unable to race; the three start-scoped olds
complete; the per-side end judgement; story-o6 re-analysed equal to its report (G34/G35 hold at A0).

### 11.4 As built (the implementer appends, PART by PART)
Where the design was silent or wrong, each the smallest correct thing, in O6's 11.6 form; and the review's findings, in
O6's 11.7 form.

#### PART A, as built: where the design was silent or wrong (each the smallest correct thing)
A0 first, from master's merge gate and the nightly ledger, no new baseline: `.test-gate/latest.json` green at c954f986
(11244 passed, 1 xfailed); master d6b77975 (no merge since the branch point); `tests/test_harness.py` 930 collected at
the branch point; `segment_regress.py --only G32,G33` at the head PASS (G32 49 passed; G33 164/164 as frozen and as if
frozen), exit 3. The gate extended (759b0697), the O6 baseline was captured THERE before any other code change (58b6aea3):
two readings identical, G32 50 passed (O6's 49 and the A0 test), G33 164/164 twice, G34 (story-o6, PROVEN, 19 checks, the
archived report exactly), G35, G36 (93 sessions + 71 units, 164/164), G37 (6 PASS), 4 m 43 s; 2366668 bytes, LF, ASCII,
62 sources (G32's 50 tests and FAKE_PINS_O6's 12), none pinned by an earlier baseline. `--only G34,G35,G36,G37,G21` then
read 5/5 (G21 over four baselines: 358 sources, 20 re-baseline rows). A0b's golden (88d98f19), on the unedited fake: 98
sample changes and 45 trace rows a side over 751 frames, 34047 bytes; both replays green.

1. **A body the design said no change would touch.** "No existing test body changes except the registry test" -- but
   `test_segment_regress_partial_run_is_not_the_gate` asserted the partial line `(32 of 33 not run)`, which G34-G37 make
   `(36 of 37 not run)`. No baseline pins it; it now reads the count off `ITEM_ORDER`, so B4's and C2's extensions leave
   it alone. In the same spirit `select_items`' refusal and the `--only` / `--segment` help derive the item range and the
   segments from the registry instead of the literal "G1-G33" / "O1-O6".
2. **`fake_pins_o6` with no class.** FAKE_PINS_O4/O5 expanded classes; O6 added none, so `fake_pins_o6(source)` returns
   FAKE_PINS_O6 as listed and raises (naming them) when fakegame.py defines no function for a name -- the classes'
   "a renamed class raises" rule, per function.
3. **A0b's test in `REQUIRED_TESTS_O7` at A0b.** A0 committed the tuple empty; A0b adds its replay as its first entry
   (O6's precedent: its A0b replay heads `REQUIRED_TESTS_O6`). Nothing reads the tuple until B4's G38.
4. **S17's tests on O2's fixture.** The design named the cases, not the fixture: 30820 the walk's field with O2's exit
   (Field(30810), the end), 30821 a door's landing; every walk cell ends in O2's crossing so a done walk is never rule 8's
   V4. `_s17_drive` re-runs (at most twice) only a run whose walk was DONE and whose crossing a starved harness spoiled
   (V7 "of its 2 attempts", interrupted twice, the budget), and the door case only a V11 whose loss was read after the
   switch (its door then unnamed) -- each class asserted on the run set aside, never a walk verdict re-run.
5. **S19's unstated edges.** `route_to` refuses a `basis` other than None / "prior" (a HarnessError; `step_of` refuses it
   at the table already), and "no prior to seed" whenever `basis` "prior" comes without a prior basis dict, cached field
   or not (the design's rule, unconditional). `basis_check` reaches the record through a per-call slot that route_to
   sets and restores as it does the loss probe (`_walk_leg` has no record). `_prior_angle` holds DEGREES -- the spread
   converts -- with `basis_check.angle` rounded to 0.01 and the marker's to 0.1. `calibrate_axes` and
   `_calibrate_clear_of` are untouched, as designed: a `calibrate_axes(recalibrate=True)` on a SEEDED field would leave its
   S19 state, and no route path calls it.
6. **The marker on the V13 row.** `run_step` writes the converted step row with `v` V13, `by` driver, `why` "the prior
   basis disagreed with the first move: ..." and -- beyond the design's three -- `prior_basis` (the marker: field, angle,
   moved, pressed, measured, predicted), present on that row alone: O7-WALK's (d) and a rehearsal read the angle off the
   row, not off the prose.
7. **Why the narrowing test needs a twist.** On a box floor a leg that runs exactly along a pad never feels the spread:
   the hold's end lies on the leg, inside any drift. The test gives the fake 154's 1.4-degree basis (every pad 1.4 degrees
   off the 3900-u leg) at 31 fps: the cached walk took 6 holds; the spread held wide (the mutant) took 18 -- the critic's
   `sim2.py` count, reproduced on the fake.
8. **`dali` for 163.** The stair-at-110 test reads stock 163's player walkmesh through the module-scoped `dali` fixture
   (its warned skip without the install, which fails G7), and walks the 110 plan on a fake box over the stair (no wall
   model): 6 waypoints at 110 (3880 u), none at 116, 118 or 120 -- 0.2 #5's numbers, re-measured here.

#### PART B, as built: where the design was silent or wrong (each the smallest correct thing)
B1 (12a12112), B2 (a39dd049), B3 (cc2064b0) and B4 (1b6ed921) on PART A's receipt (2150d6f0, green): no re-baseline.
The four fake pins re-baselined by name with their reasons: `_visit_steps` and `_VisitBeat._place` (B1, O5's),
`_door_knobs` and `_VisitBeat._door` (B2, O6's); both replays (O5's hallway, O6's Steiner route) identical at every
step. G38 joined the gate at B4 (25 tests: PART B's 24 and A0b's replay); every PART B test failed on its mutant.

1. **154's stacked levels lie at least 1298 apart, not 1711.** B1's premises test measures the least vertical gap between
   two stacked open triangles exactly (at the corners of their XZ overlap): 1298, a stair triangle (288) over the ground
   (60); 1711 is the balcony over the ground. Both lie over 2 x `LEVEL_BAND` (800) and `LEVEL_STEP_DY`, so no constant
   moves; the test prints the measurement and asserts the bound, never the number. 163 stacks nothing. The steepest
   60-u steps measured as designed: 79.1 (154, tri 205), 63.0 (163, tri 134).
2. **H21 replaces the push-out inside a pinch.** The design squeezed only a step that "can keep neither `least` nor any
   slide bearing". But the fake's rule for a centre nearer a wall than the radius (`_pushed_out`) then ran on the squeezed
   point and moved him to the nearest spot at full clearance -- in a narrowing pinch, BACK along the corridor to its mouth
   -- undoing every squeeze the next frame (he oscillated at the mouth). So with `squeeze_slack` set a step that ends
   inside a pinch (no point across the step's end at full clearance) is placed on its midline (`Levels.squeeze`) instead
   of pushed out; outside a pinch the push-out is today's. And `squeeze` answers a pinch only: where a point across the
   step's end stands at full clearance -- a press into a wall -- it returns None and the never-closer rule stands (else
   the search across would set him sideways along the wall); each side of the search runs only as far as his level's
   floor.
3. **Silent edges of H20.** `Levels.wall_gap` is infinity when no wall of his level stands anywhere (None stays "no
   triangle of his level under him"); `fake.clearance` None under a level raises at his first step (`_move_to`: the
   levels are a plain dict); `place_height` with no open triangle under (x, z) sets -h.
4. **The balcony-edge test places him 5u inside the north edge**, nearer it than one step. Placed further in, the edge's
   own wall held him whatever the level rule and the step-bound mutant passed; at 5u a step's end lies past the edge,
   where only the level rule stops him (the mutant drops him to y 5).
5. **The west flight's break** is the courtyard's walls under the west arm: with walls of every level they close the
   arm's mouth to him ON THE BALCONY (he stops at (-1542, -3244)); the design guessed "the balcony's edge stops him on the
   ground below it". The test fails on the mutant either way.
6. **A held walker publishes `moving` False** (H23; `_objects_doc`): his script waits in ip263's loop and no walk runs.
   Published `moving` while held, Dojebon would read to route_to's npc watch as a WALKING trigger, whose reach every hold
   keeps clear of.
7. **The bodies' radii**: every NPC on the route has `SetObjectLogicalSize(20, 20, 30)`, so each takes the design's
   Dojebon rule, r and talk_r 4 x the first operand (80); O5's published-pair formula (`_O5_BODIES`) is not used. No
   route walk passes within 400 of one.
8. **A re-armed monologue never reaches V7 on its own -- the bytes loop it.** The design's castle-walk break ("the
   monologue scene without `unless_bit` (V7)") and `test_o7_drive_second_monologue_is_v7` ("`store_override` {672: 0}:
   V7") both assume a re-armed monologue interrupts the step's RE-RUN. It cannot: e16 t1 runs ip390 again a tick after
   ip711 (op_22(1), JMP L0), so a re-armed guard fires AT ONCE after the re-grant -- B2's
   `test_fake_monologue_store_override_fires_it_again` pins exactly that -- control comes back a tick at a time, rule
   8's settle never holds, the step is never re-run, and the run pages the monologue round until its budget STOPS it (a
   HarnessError: STOPPED, never V7; in the game too). So the V7 test makes the second monologue interrupt the re-run --
   a test-side wrapper on `g.send` re-arms Bit[3796] as the re-run's first hold goes out (deterministic: after the
   first monologue's ip672, before any press of the re-run) -- and asserts V7 driver at [30842, 1190, 3]; it pins the
   bytes' own fault beside it: `store_override` {672: 0} loops the monologue (one `interrupted` row, no crossing),
   STOPPED at its budget. 2.7's V7 row ("a second monologue") holds for a monologue during the re-run only. The castle
   walk's documented break is the interruption bound (`>=`: the monologue's one interruption over it, V7 at once); the
   `unless_bit` mutant fails it too, slowly, at the budget.
9. **H22's scene keys**: `unless_bit` (None: never disarmed) and `regrant` ("in_place", the only form) optional; its
   steps pages, stores and waits only (`SCENE_STEP_KINDS`, checked by `_door_knobs` after `_visit_steps`).
10. **The route builder** (B3): 160, 162 and 163 carry no `wait` before their grant (the design lists none: the
    prologue, the grant and the post-grant store run in one tick; the leading stores -- what H15's `error_window` and
    `grant_at` key on -- are still the prologue). Every door walks out toward MJPOS's point for the planned crossing
    (`_o7_crossing`: the first point of the straight line from the step's start to its goal standing in the region); a
    door the route never takes, toward its centroid's projection. `short`'s end is the next place's ARRIVAL -- its
    prologue, no grant -- and `_o7_pred(short=...)` ends there (side_ends the next place's ids, its beats the cell's, no
    end state). 154's closure lists come from a test-side `_o7_closures154` (C1's `closures154` is PART C's), equal to
    the research's `closures154.json` (119, 134).
11. **The castle walk asserts its step rows less any `failed` one** (a load-stalled walk costs an attempt, which the cell
    absorbs); the interrupted 159 row, its re-run and the monologue's three rows between them (by frame) exactly.
12. **The real-balcony test's break** (the design gave none): the walker's hold dropped -- released, Dojebon walks his
    patrol. `_probe_axis` is counted on the instance (`_s19_probes`); Dojebon's every position is recorded by a wrapped
    `_step_walkers` (the visit beat takes its bodies down at its end).
13. **The wrong-door and walk-into-a-door tests re-run a V11 whose loss was read only after the switch** (its door then
    unnamed: `_o7_late`), its class asserted on the run set aside -- O6's wrong-door precedent.

#### PART C, as built: where the design was silent or wrong (each the smallest correct thing)
C1 (5ec2d64a), C2 (7826c047), C3 (a4e5eeb8; the record's THE WALKS -- every routed step's holds -- THE LEVELS over
every hold in the walk's place and the calibration record completed in the commit after C4) and C4 (this text,
PLAN.md's O7 section) on PART B's receipt (10a46257, green):
no re-baseline. C0 read O4's build (20 in-chain `Field()` sites, 40 bytes, 49 member files) into `o7_forks.json`
`built.measured`. G38 holds PART B's 25 tests and PART C's 28 (C1's 18, C2's one, C3's nine); G39 the dry run (167/167
on the draft and as if frozen). Every PART C test failed on its mutant (named in its docstring and its commit).

1. **O7-KEYS computes 3 compound values, not 1.** The registered keys include Weimar's scene stores 160 e9 t1 ip415 and
   ip485 (`Byte[208] ++` after ip380 / ip450: forbidden sites), each computed from its prior as 159 e16 t1 ip648 is; the
   detail prints the count it computes, never a typed one. The route pins number 153 (the design's N), each with its
   instanced-entry scans.
2. **The start read is A-START only when nothing earlier in the run touched its target.** A run's row at a `start_reads`
   site read with another `old`, with an earlier row of the run on the target's bytes, is the run's own store -- WRITES
   and PATTERN judge it on a covered run (the dry run's `byte8-explained-F`), never the start. And VOID-ASYM (b) sets the
   start read's A-START aside (`_void_ids`, by its reason's opening words, `START_READ`): the warp's timing in field 70 is
   the same harness on both sides, never a structural fork deviation, so a side VOID in it in every run reads VOID by
   COVER, never NOT PROVEN. Every other A-START (154's error path) reads as before.
3. **STATE (c) matches the raced row by place AT THE SIDE'S OWN FIELD of it** (real 163 on S, member(163) 31255 on F):
   by place alone, an F run's row at real 163 -- a leak the LANDING check names -- would also match.
4. **`closures154`'s overlap counts a TOUCH** (`_convex_overlap(touch=True)`) on the triangles shrunk 2% toward their
   centroids: so a shared edge is no overlap BECAUSE of the shrink. With a strict overlap the shrink changed nothing (a
   touch never counted) and its mutant survived; now dropping it adds every edge-neighbour and fails the 119/134.
5. **Shapes the design left open**: `regions_problems7` returns five values (the problems, the roles, the gateway rows,
   the hot-spots, the hazards); O7's `trace_summary` keeps the crossings as a LIST (each place's chain row to the next
   field row, the last door into the cut) where O5's summary keyed two by name; `o7_dryrun.py` was committed with C1,
   whose pure tests read its base run and session builder, and C2 joined it to the gate.
6. **The dry run's re-registrations** (each as rendered where the code holds another want, explained in its docstring):
   `inert-row-both` adds CHAIN (FieldEntrance's own bytes); `v19-one-F` adds FORBIDDEN (real 158 is no end place);
   `monologue-order-swap-both` reads WALK (c) "in order" with PATTERN (b), its one-side twin STATE (a) too;
   `field-order-flip-both` reads CHAIN, LANDING (b), PATTERN (b) and WALK (c), never STATE (a) -- a reorder in every run
   of both sides leaves the histories identical; added: `byte8-explained-F` (item 2). `as_if_frozen` also moves each
   step's start 20 u, so the goals unit renders its start-dependent lines from the predictions given (`goals_lines`),
   never pinned numbers.
7. **THE GRANTS are read off the RING** (o7_rehearse's `Recorder.grant_scan`, armed at the run's start, before its New
   Game): the driver polls only between steps, so a grant made inside one -- route_to's wait for the landing, then for
   control in the next field -- never reached O2's poll-to-poll rule (on the fake 158's and 163's were missed). Only a
   grant in a field of the route's places counts: New Game's field 70 is none.
8. **THE LADDER TAP also taps `_blocker_ahead`**, route_to's one unseen-blocker placement, counting each on the entry it
   followed: the route record's `blockers` list is no witness -- a call whose replans never moved him withdraws it and
   ends `frozen`, exactly the foot snag's path. Waits and pushes are the record's counters across the entry; `boxed` its
   return; `frozen` the call's last entry's. And a route record's rate (`fps`) is the walk tap's: a step row's trimmed
   route keeps scalars only.
9. **R-WALK-VOID's two runs differ in warp, end and stop**: the stage carries `each`, one entry a run (`stage_run` lays
   run k's over a copy); run 1 ends at 158 and run 2 at 160, so a stop that never fired ends its run at the next place,
   not at 164. A stop lies on its step of the run's copy as `{"holds": 3}` / `true`, a run stops one way, and a stop
   names its place's ONE cell or refuses. Each stop records the direction holds and Confirms requested after it before
   end_run (none), the hold stop its walk holds before it (3), the page stop the Confirms before it (none: rule 7's first
   was the stop's).
10. **Seams**: THE FOOT WINDOW is `run(..., foot=)` (default 163, x 2000-2260, z 3750-4100); `--rehearsal-report` takes
    `walkmesh` (a place -> its mesh; default the install's stock player walkmesh, read-only) and measures each foot
    hold's narrowest wall gap there, level-aware, from the samples the record keeps (`[frame, x, y, z]`: never a number
    the rehearsal computed). F5's verdict per run is GO when the place's step is done and NO ladder entry -- whatever it
    climbed -- followed a hold that started or ended in the window. THE DESCENT's predicted reach is the hold's frames
    at a run: `RUN_U_PER_TICK` (60) x tick_hz / fps a frame.
11. **The ladder test's push and body**: at the fake's foot snag (squeeze slack 0) the push is never pressed -- its own
    line check refuses it -- and the ladder goes on to the blocker and frozen; so run 1 carries the waits and the
    blocker at the foot, and THE PUSH is run 2's, at a non-solid body on the upper flight. That body is r 140 at (1600,
    4659): at r 80 (the route NPCs') the planner went round it -- the flight is ~330 u wide, the plan 112-118 u off one
    wall and 210-230 off the other.
12. **The rehearsal tests' launch** (`_o7_launch`) pins NO basis -- each run seeds its own (S19) and 159 calibrates --
    and the fake's Memoria.ini holds O7's settings (`_o7_launch_files`), so P-SETTINGS reads 4.13's 31 keys there.

#### The review: seven findings on the built O7 (each fixed, none disproved)
A code review of PARTs A-C raised seven findings: one medium, six low. Each came with a verifier's re-check against the
code (the bytes in the research disasm for #1, a script on the real draft for #4, pathfind's `_in_poly` for #5, the
archives' arm-to-warp gap for #6), and each was fixed with a test or a dry-run mutant that fails without it (the mutant
run named in its commit). None was disproved. Two details were tempered by the verifier and are said: #1's 3.3 had
DOCUMENTED its simplification ("the fake writes them just before it opens") -- its rationale misread WindowAsync, and no
verdict flips; #7's "no current caller passes recalibrate" -- the walkmesh-sensor studies and three harness tests do,
none on a seeded field. After the last code commit: the dry run 174/174 on the draft and as if frozen (167 + the
review's 2 cases, 1 unit and 4 listed mutants; `O7_DRYRUN_FLOOR` 174), `--offline-check` 6 PASS, and the PART's
whole-file run and full gate on its head (the fixer's receipt).

| # | Finding | Re-checked | Disposition |
|---|---|---|---|
| 1 (low) | The fake's monologue wrote ip613 and ip648 in ONE frame BEFORE page 300 opened, and `test_fake_monologue_fires_once_outside_the_box` pinned that order. 159 e16 t1 runs ip602 WindowAsync(4,128,300), RunAnimation(6998)+WaitAnimation, ip613, the loop's pass (RunAnimation(6982)+WaitAnimation, a sound, ip648), RunAnimation(6990)+WaitAnimation, ip669 WaitWindow(4), ip672, ip711 EnableMove; 296, 298 and 299 are WindowAsync with their own animations, 297 WindowSync. | The disasm (bytes_route/L159.txt 716-780); the fake supports `wait` scene steps, but its page step blocked until the window was gone. | FIXED (8f5ad4f4): H24 (opt-in, FakeGame) -- a page's `async` (WindowAsync alone: listed, the script runs on) and a `wait_window` step (WaitWindow(slot)), checked strict, a scene kind. `_O7_MONOLOGUE` is the bytes' list, each animation a wait of `_O7_ANIM_TICKS` 30 (an estimate; R-FULL's F3 records the real stretch): under rule 7's prompt Confirm, 613 and 648 land with control off and NO window up. Re-pinned (open300 <= 613 < 648, an animation apart; 672 >= gone300); new `test_fake_monologue_async_pages_hold_the_script_only_at_waitwindow` (a slow Confirm: both stores while 300 is up, 672 waiting; each WaitWindow holds the next page) fails with WindowAsync read as WindowSync. `_visit_steps`, `_VisitBeat._run` and `_VisitBeat._page` re-baselined by name (source_pins.json rows 25-27); O5/O6 pages carry no `async` (G21, G26 54 and G32 50 passed). |
| 2 (low) | `_monologue_lines` filtered the run's pages with `any(... for m in ())` -- always False -- so the --analyse report's monologue line never printed a page, silently. | Read at o7_castle_walk.py 2918-2930; only the rehearsal report's `_monologue_lines7` showed pages. | FIXED (78e3820b): `monologue_pages` -- from the first listed page holding the registered first page's pinned text (296 "What!?") through the first after it holding the last's (300 "I must hurry!"), or to the run's last page on a stop mid-monologue; the line prints "its pages (k of 5)" or that none was listed. Dry-run unit `monologue-lines` and the null-pair case's report fail on the old filter. Report-only. |
| 3 (low) | On the floor-blind box 154's grant sets no height: Steiner's y is 0 from the start, so Dojebon's latch (y < 600) holds him whatever the route does -- every box-floor "Dojebon static" was the latch's, and the rehearsal test's docstring over-counted the coverage. | `_o7_route`'s box grant `[-58, -3758]`; `_step_walkers`' latch on the first tick; only the levels154 tests exercise the 3600 term. | FIXED (60eff9ff): the docstrings say the box latches him from the grant (a balcony-height grant on the box would fire e8's balcony branch); the hazard's protection pinned on the real mesh -- `test_o7_drive_real_balcony_walk_east_releases_dojebon_on_the_fake`: the walk's mutant, the hazard out of its avoid and its goal east on the balcony at (650, -3530), 3817 from him, releases him (the static watch's seen then moved rows; `_o7_run` now passes an `observe`), then the balcony cross lands in 153 (V11). Fails with his hold's `within` unbounded (seen alone). |
| 4 (medium) | `start_scoped` was a typed list and only its entries were checked: 159 ip613's entry dropped still read O7-KEYS PASS and the freeze accepted it, the scope line understating the start dependence. | Reproduced on the real draft: PASS with "2 start-scoped olds"; `freeze_problems` never read the list. | FIXED (7f44e0d9): `scoped_derivation` -- the route's writes and chain keys in route order from the RAW START and from O6's last values (`last_values`: the one floating tuple, Byte[8]'s, read by its value 125; else the composition over the frozen O1-O6 keys; else the raw value), each carried through the route's own earlier keys: exactly 154 ip61, 154 ip123 and 159 ip613 of the 33 differ. O7-KEYS (c) refuses a derived site no entry claims and an entry whose olds agree; the freeze refuses a set that is not the derivation. Mutants `keys-scoped-dropped`, `keys-scoped-extra` (158 ip57, every per-entry clause satisfied); the keys and freeze tests pin both. |
| 5 (low) | O7-GOALS (g2) promised every other exit "wholly outside" a cross's target but tested only the other exit's vertices inside it: crossing edges, or the target inside the other, passed. | `pathfind._in_poly` on a crossing band and a containing box: nothing reported. | FIXED (98db56d1): the two convex polygons' interiors must be disjoint (`_convex_overlap`, touch=False; a non-convex region is refused -- every O7 region and stock gateway zone is convex). Mutants: 163.e3 as a band crossing 163.e2 and as a box holding it, neither with a vertex inside e2 -- each FAILS "163.e3 overlaps its target 163.e2" (the dry run's unit_goals and `test_o7_castle_goals`). The draft's geometry passes as before. |
| 6 (low) | One harness timing, two verdicts: a warp before field 70's ip249 made the run A-START (the start read), a trace armed before ip249 with the warp after put its row BEFORE the start, where O3's START (a) failed the run as NOT PROVEN. | The archives' ~60 frames between arming and the warp; `front-cut-write` shows a pre-start field-70 store fails START; all 24 archived O3-O6 runs had ip249 before the arm. | FIXED (fd50ffb3): `why_void` reads the race's other branch -- the raced store (`race_site`: the field-70 route pin storing the start read's target its old, 70 e0 t0 ip249, read off the pins) among the run's pre-start rows is A-START by the driver, its reason the start read's, so VOID-ASYM (b) sets it aside; any other field-70 row before the start stays START's (front-cut-write still NOT PROVEN). O7-KEYS (d) requires the raced store pinned. Cases `byte8-race-armed-one-F` (PROVEN, the run uncovered) and `-all-F` (COVER VOID) read NOT PROVEN with `race_site` neutralised; unit why-void and the why_void test likewise. The instrument is unchanged: the rehearsals measure the warp's timing. |
| 7 (low) | `calibrate_axes(recalibrate=True)` overwrote `_axes[key]` (the plain probe's write and `_calibrate_clear_of`'s) without clearing S19's state: a field seeded and still pending kept its seed on a MEASURED basis -- the first-move check run against the calibration (a deflected hold read as the seed's V13), the seeded spread planned. | session.py :1792 and :2127; `_field_spread` and `_judge_first_move` read the stale state. Latent: no caller recalibrates a seeded field. | FIXED (ef153167): both writes call `_drop_seed` (`forget_basis` uses it too); the docstrings say every measured replacement of a basis clears the seed, not only every pop. `test_segment_prior_basis_recalibration_drops_the_seed_on_the_fake` (plain and clear-of: the field in none of the three sets, the walk after it no `basis_check`, calibration's spread) fails without the two calls. No O1-O6 path seeds. |
