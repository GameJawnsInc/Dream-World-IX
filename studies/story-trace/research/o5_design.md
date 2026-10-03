# O5 -- the stair walk and the stored choice under the trace: the design

**Status: DESIGN, offline.** Nothing is imported, built, deployed, launched or frozen. The inputs are `o5_route.md` and
`o5_research.json` in this folder (the reconciled route, the walks, the start, the harness gaps, the fork gates) with the
critic's twelve problems (`critique.problems`) overriding the map where they conflict, and the nine decisions the lead
made on top of both (0.1). This file folds them into code-level decisions in `o4_design.md`'s structure and keeps what
O2-O4 learned. Every number below was read, read-only, from the stock US `.eb` files (through the kit at this branch's
head), the research's scratch listings (`<scratchpad>/o5_research/reconcile/L{151,153,154}.txt`, `win_*.txt`,
`stages*.out`, `route153.out`), the live install (mod folders, `Memoria.ini`) and the live Memoria source
(`C:\gd\FFIX\Memoria`, = the deployed DLL, sha256 `ba976242...`); 0.2 says how. The offline check (section 6)
re-derives every one of them.

**Revised** for two critiques of this design -- driver robustness (eleven items, 11.3) and claim integrity (fourteen,
11.4): every item adopted, five with a correction the bytes, the walkmesh or the engine forced (Blank's body radius,
the stray window's closing press, the stair evidence's statement, Byte[8]'s freeze through O5-PATTERN, the re-ask's
landing), none rejected. New findings from that pass are 0.2 #17-#22.

**The segment** (decision 1): New Game, the trace armed, then in field 70 (after 70 e0 t0 ip130, before ip475) a raw
`warp 153 325 1190` (S) / `warp 31245 325 1190` (F). 153@325 (visit 1; EVT_ALEX1_AC_H2F): pages 113-117; THE STAIR WALK,
the segment's only control grant (e3 t1 EnableMove ip785, Zidane); pages 126 and 127; choice 128 answered "Examine her
face" (absolute 1: `Global.Bit[3795] := SYSVAR[9]` at e3 t1 ip1741, 0 -> 1); path 1's eleven windows, 131-133, the
KEYON pairs 134/135 and 139/138, the timed 137 and 140; `Field(154)` (e3 t1 ip3158, FieldEntrance 304). 154@304 (visit 2;
EVT_ALEX1_AC_ENT_2F; Zorn & Thorn, no control): pages 153/154 and three KEYON pairs; `Field(153)` (e2 t1 ip1528, 316).
153@316 (visit 3, no control): twelve pages and two pairs; `Field(151)` (e18 t1 ip1085, 110). It ENDS on arrival in 151
(EVT_ALEX1_AC_SEAT_R) -- real 151 on S, member(151) 31244 on F -- cut at 151's first EMITTED row, e0 t0 ip22 (0.2 #1).
SC 1190 throughout. No battle, FMV, ATE or naming: Steiner's naming and `Byte[6] |= 8` lie after the cut (O6's).

What O5 newly puts under the trace: a WALK in alxc whose goal is a HEIGHT (the stage-6 test at 153 e3 t1 ip859); a
CHOICE whose answer is STORED (so the claim needs the stored value proven the driver's verified pick); a route that
REVISITS its start place at the same SC (153 at 325, then at 316) -- the engine's per-site same-value suppression shapes
what the revisit emits (0.2 #2); and two members O4 deployed but never ran (31246, 31244) and one it ran only to its
first row (31245).

---

## 0. What this design decides, and what it found

### 0.1 Decided upstream (not relitigated)
1. **The segment** (the critic's problem 3, candidate 3): the run above; `visits` [153, 154, 153], the end on arrival in
   151 with `side_ends` {S: [151], F: [31244]}; the cut at 151's first emitted row (0.2 #1); SC 1190 throughout, O3's
   NO-SC shape. 151 e0 t0 ip315 `Byte[8] := 125` races the end-state read at the arrival: Byte[8] is out of `end_state`
   (its end value is the trace's last pre-cut write, 4.9). The stock event names are 153 EVT_ALEX1_AC_H2F, 154
   EVT_ALEX1_AC_ENT_2F, 151 EVT_ALEX1_AC_SEAT_R (the FBG names AC_FTI/AC_RST are scene names; the kit named the
   members O4_AC_H2F, O4_AC_FTI, O4_ALXC_AC_RST after them).
2. **The fork side:** O4's deployed members 31245 (153), 31246 (154), 31244 (151); nothing imported, built or deployed.
   `o5_forks.json` references O4's chain as `o3_forks.json` referenced O1's (6.4). Every route `Field()` is retargeted;
   O5-BUILD re-checks it offline, per language (6.1).
3. **Choice 128 picks "Examine her face" (absolute 1)** -- a fork that stores a constant fails it. The 127 -> 128
   stray-press race is closed by an OPT-IN PRE-CHOICE GUARD (S10: page-once on the marker page, judged against every
   press of the driver's; the quiet window, closed by the published choice; the stray window from 127's last listed
   sample; the branch witness, 0.2 #20), generalized from O4's machinery as NEW opt-in code (O4's own paths,
   `stray_answer` included, untouched). choose()'s landing is VERIFIED (S11). The fallback (pick 0, `take: "default"`)
   is designed (2.5.7), frozen only if the rehearsals show the race cannot be closed.
4. **The outside-input witness runs the WHOLE run** (S12, `pred["witness"]`).
5. **s88's same-value suppression** is modelled in the FakeGame, opt-in, faithful to the sink (H13); the dry run's
   renderer models it (O4's renderer already does); O5-PATTERN compares the suppressed stores and the emitted pattern
   EXACTLY (5.3; claim critique #1) and the claim's scope line says what it does not compare (5.4); row counts are
   recounted from the model (4.16).
6. **O4's full preflight set** (6.2) minus what is O4's alone (P-GATE, P-TEXT block 2: 11.2 #1); all green today
   (0.2 #12).
7. **Rehearsals** (the lead): R-STAIRS x2, R-FULL x2, R-WALK-VOID, F-SMOKE, F-PASS (untraced, before the freeze) (7.1).
8. **Built ON the shared machinery:** `O5Segment` in `o5_hallway.py`; every shared change keeps O1, O2, O3 AND O4
   analysing byte-identically -- the O4 gate's baseline captured FIRST (1.4); G21's pins extended by its own rules. The
   critic's minor problems are binding fixes (11.1). Predictions frozen by the lead after the rehearsals (`--freeze`
   refusing to overwrite).
9. Master's `Session.fight` hardening may land meanwhile (it has: c5e5dd88, ad57966b, 0.2 #16); O5 has no battle; the
   lead merges master before the merge.

### 0.2 Found while designing (each verified offline, read-only)
1. **The end row is emitted.** The sink keys suppression by `Site {Fld, M, Src, Sid, Tag, Ip, First, Bit, Type}`
   (StoryTrace.cs:101-140), `Fld` the RAW `fldMapNo` (:374-376): 151's first store opens a NEW site in the epoch, and a
   site's first same-value store is emitted (`emit = !site.SameEmitted`, :383-390). So 151 e0 t0 ip22 `Bit[191] := 0`
   (0 -> 0, same 1) is the first `w` row in place 151 -- the cut row on both sides (31244 on F: the member's own
   `fldMapNo`). The row before it is 153 e18 t1 ip1077 `Int16[2] := 110`. (The critic's ip718 row belonged to
   candidate 4.)
2. **The revisit's emitted pattern** (StoryTrace.cs:383-401 over the raw warp's start values: Int16[9] 643, Byte[13] 1,
   Int16[11] -1, Byte[14] 0, Byte[8] 125, Bit[191] 0, Bit[184] 0 -- field 70's prologue, 70 e0 t0 ip57/130/138/200/249).
   `SameEmitted` is set by a SAME-VALUE store alone (:383-387); a change counts toward the 64 (:391-394) and leaves it
   clear. Visit 1 (153@325) emits all six prologue stores: ip22 (0->0, same), ip49 (same), ip57 (643 -> -1, a change), ip119
   (1 -> 0, a change), ip138 (-1 -> -1, same), ip200 (0 -> 0, same). Visit 2 (154) opens eight new sites: all emitted.
   Visit 3 (153@316, the same `fldMapNo`, the same epoch): ip22, ip49, ip138, ip200 are same-value at sites that already
   EMITTED a same-value store -> SUPPRESSED (counted); ip57 (-1 -> -1) and ip119 (0 -> 0) are the FIRST same-value
   stores at sites whose visit-1 store was a change -> EMITTED with `same: 1`. So **visit 3's first emitted row is e0 t0
   ip57**, and the epoch's close (`storytrace 0`: `Stop` -> `EmitCounts`, :187-205, :540-557) writes four `c` rows for
   place 153 (ip22, ip49 masked; ip138 last -1, ip200 last 0; n 1 each), stamped with the SITE's fld/m. `cut_at_end`
   keeps them (their place, 153, is no end place: segment_trace.py:127-136). This pattern is START-DEPENDENT (critic #5,
   5.4): after a true O1-O4 run visit 1's ip57/ip119 would be same-value too, and visit 3's first emitted row would be
   e18 t1 ip890. O5-PATTERN freezes the whole pattern (5.3); the archives say an exact pattern does not flake --
   story-o2's revisit of 103 wrote its five `c` rows identically in all six runs (n 1 each, the same `last`s), and
   story-o2's 122 and story-o4's 36 field-mode script rows (masked included) read identically, in order, value and
   `same`, in all six runs of each.
3. **Row counts before the cut** (from #2): 21 emitted `w` rows (17 unmasked + 4 masked: 153 ip22/ip49, 154 ip26/ip53)
   and 4 `c` rows (2 masked). 15 distinct unmasked keys: 12 writes + 3 chain (4.3-4.4). No SC row.
4. **Every key's function offset**, joined by `ScriptIndex.join` on the stock US bytes: 153 e0 t0 ip22/49/57/119/138/200
   -> off 16/43/51/113/132/194; e3 t1 ip1741/2953/3150 -> 1333/2545/2742; e18 t1 ip890/1077 -> 766/953; 154 e0 t0
   ip26/53/61/123/142/204/279 -> 16/43/51/113/132/194/269; e2 t1 ip1520 -> 1409; 151 e0 t0 ip22/315 -> 16/309; 153 e28 t2
   ip38/227 -> 8/197. Every join `status store`, `census` True.
5. **Store census:** stock 153 holds 51 global store sites, 154 holds 22, 151 holds 21 (`o3_prima_vista.store_sites`, 0
   undecoded). 151's first store at entrance 110 IS the cut: none of its sites precedes it (6.1 O5-CENSUS).
6. **Instancing per route entrance** (`o4_castle.instanced_at`): 153 at 325 {code 1, 2, 22; object 3, 7, 9, 11, 31;
   region 26, 27, 28}; 153 at 316 {code 1, 2; object 18, 20}; 154 at 304 {code 1; object 2, 4}. No instancing op lies
   outside e0 t0 in either field. 153 e15 (`Byte[8] := 125` ip32) is a SHARED entry: run only by e32 t1 ip866
   `RunSharedScript(15)`, and e32 is instanced at 328 alone. The shared entries run on the route (4, 5, 6, 8, 10, 12, 19
   in 153; 3 in 154) hold no store.
7. **Gateways** (`eventscan.scan_gateways`, `face_gate` None on every one): 153 e23 (-> 154 @315), e24 (-> 150 @315), e25
   (-> 64 / 151 @315), e28 (-> 150 @5); 154 e8 (-> 153 @301, 158 @300), e9 (-> 156, 155), e10 (-> 156, 167); 151 e8 (->
   153 @327). Of these only 153 e28 is instanced at a route entrance (325). e23/e26, e24/e28 and e25/e27 share quads.
8. **The side-scene and back-door guards, exact:** 153 e26 t2 ip38 `SET({obj(uid=250).f[1] const(65436) B_GT
   obj(uid=250).f[2] const(1333) B_GT B_ANDAND B_EXPR_END})` (on the ground and z > 1333), ip58 `Map.Byte[24] const(6)
   B_EQ`, ip88 `DisableMove()`, ip110 `Map.Byte[24] := 7`; e27 t2 ip38 the stage-6 test, ip68 `DisableMove()`, ip90
   `Map.Byte[24] := 14`; e28 t2 ip30 `SET({B_SYSVAR[2] B_EXPR_END})` (control) alone, ip38 `Byte[8] := 25`, ip83
   `ExitField()`, ip227 `Int16[2] := 5`, ip235 `Field(150)`.
9. **The stair test:** 153 e3 t1 ip859 `SET({obj(uid=255).f[1] const(65086) B_GT B_EXPR_END})` -- `const(65086)` is
   -450 (a 2-byte constant is signed, EBin.cs:1251-1255), `f[1]` is -pos[1] (EBin.cs:1785-1793), uid 255 the current
   object, e3 (EventEngine.cs:946-949). The grant: ip752 `WaitWindow(1)`, ip755 `Map.Bit[158] := 1`, ip785
   `EnableMove()`; the loss: ip874, ip893 `DisableMove()`; the teleport ip1466 `CreateObject(64371, 856)` = (-1165, 856).
10. **O4's `route_entrances` cannot serve O5:** it maps each route PLACE to one entrance, the place before it's LAST chain
    value -- for route [153, 154] it gives 154 the entrance 110 (153's ip1077). O5 reads entrances by VISIT (153: 325 and
    316; 154: 304) in its own census and region checks (6.1). O4's function is not edited (G25 pins its output).
11. **O2's dormant-region proof cannot serve 153:** `_dormant_problems` reads a `SWITCH` dispatch only (153 uses
    `SWITCHEX(L1098, 325, L273, 5, L438, 328, L603, 316, L799, 3, L951)`, ip255) and requires every `InitRegion(n)` in
    the default block (153's e23-e25 are also instanced at 328, L603). O5-REGIONS proves dormant by `instanced_at` at
    the route's entrances instead (6.1).
12. **The premises hold at the branch head** (a85e8305, off master e7ca1177): `o4_castle.py --analyse <story-o4>
    --predictions o4_predictions_v1.json` reproduces the archived `o4_report.txt` byte for byte (13941 chars + print's
    newline; 16 checks; PROVEN); `o4_dryrun.py --predictions o4_predictions_v1.json` prints "103/103 cases as
    registered" in 46 s; `--offline-check` 4 PASS; O4's `--preflight` on the live install 15/15 PASS today. Read for O5:
    no mod folder overrides 151, 153 or 154 (`storytrace.stock_overrides`); 151, 153 and 154 are each forked by exactly one
    ForkDonorPatch row (FF9CustomMap: 31244, 31245, 31246, registered O4_ALXC_AC_RST, O4_AC_H2F, O4_AC_FTI); 4600 is
    registered in FF9CustomMap-world; block 3 7 byte-equal of 7; the engine and the override at their pins.
13. **No back-door forbidden pattern is needed.** e28's tag 2 runs `Field(150)` right after its stores (ip38, ip227 ->
    ip235), so a run that wrote them lands in 150 (31243 on F, member(150)): there O4's `off_route` pattern hits; a
    driver walk is backed by its own V11 step row (`landed` 150), a fork's would not be (a finding); a covered run cannot
    hold them (WRITES exact). The critic's "no cause choice in place 153" (problem 7) holds: O5 registers only
    `off_route`.
14. **The race in ticks** (revised: driver critique #4, #9; claim critique #3). 127 is `WindowSync(2, 128, 127)` (e31 t1
    ip663, after `RunAnimation(3387)` ip648): e31 resumes when its close tween ends (0.09 s plus a frame,
    DialogAnimator.cs:144-173), waits out what is left of that animation (`WaitAnimation()` ip669), sets `Map.Bit[231]`
    (ip670); e2 runs before e31 in a tick (InitCode(2) ip226 precedes InitObject(31) ip293, and the active list keeps
    creation order), so it advances `Map.Byte[24] := 20` on the NEXT tick, and e3 (after e2) opens 128 in that tick
    (ip1713/ip1724): 128 is created ~2 ticks after 127 is GONE, plus the animation's remainder. 128 is `[IMME]` (its
    source `[PCHC=2,1][WDTH=...][IMME][ZDNE]...`; FFIXTextTag.cs:332 maps IMME to Instantly, NGUIText.cs:1495;
    DialogBoxSymbols.cs:584-587 sets `TypeEffect` false): it has NO type-out. Its opening is 0.105 s (progress 0.3 -> 1
    at deltaTime / 0.15, DialogAnimator.cs:43-47, :61-99); then the text is advanced to its end and, a frame later,
    `AfterShown` sets CompleteAnimation at once (DialogAnimator.cs:117-124, Dialog.cs:645-650), activates the group
    `Dialog.Choice` with the cursor on its default (Dialog.cs:161-162) and sets `isChoiceReady` one frame after that
    (:163-164). A Confirm in the opening sets SelectChoice to the default and closes nothing (Dialog.cs:798-801); one in
    the frame between the group and `isChoiceReady` commits SelectChoice and hides nothing (:787-789); after that a
    Confirm answers at the cursor (0: flags 128 has bit 0 clear, so `sChoose = sChooseInit`, ETb.cs:100-103; no
    choose-param op in 151/153/154). The margin a stray needs is therefore 127's close tween + ~2 ticks + the
    animation's remainder + 128's opening + 1-2 frames, ~0.25-0.3 s (the critique's ~0.2-0.3 s), not a type-out more.
    Page-once judges a sample by its GAME frame against `ack + page_once_ticks` (a stale sample is held off); the quiet
    window presses nothing from 127's going to 128's publication. The residual first designed here (a press decided on
    a fresh 127 sample and stalled past 128's opening) cannot happen: `Session.send` blocks until the agent acks each
    press (session.py:650-703), and 127 -- a WindowSync with no `[TIME]` -- waits for a Confirm, so a press decided on a
    127 that is up and waiting goes down on 127. The real residual and its closer are 2.5.5.
15. **Control at the revisit would not read as the game's.** The beat table is keyed `(donor, sc)` (segment_drive.py
    `cell`): without a visit scope, a control grant at 153@316 (impossible in stock; possible on a fork that deviates)
    would run the stair step there and end V7 by the DRIVER -- which VOID-ASYM (a) never reads, so a one-sided fork
    deviation would be re-run away. S13 scopes the cell to visit 1: control at the revisit is V4 by the game. And the
    VOID's own cell must carry the visit too (claim critique #5): `_Drive.void` keys `[donor, sc]` (segment_drive.py:
    1976-1977) and VOID-ASYM keys `(class, cell)` (o4_castle.py:1735-1768), so V4 at 153@325 after the stair step on one
    side and V4 at 153@316 on the other would cancel -- S13 gives every VOID and `observed` row `[donor, sc, visit]`.
16. **Master moved after the branch point** (c5e5dd88, ad57966b: `Session.fight` reads a vanished battle as its end):
    session.py's hunks sit at 44, 721 and 7280-7605 (the fight), fakegame.py's at 353, 1037 (`_execute`), 2199-2389
    (battle knobs); `source_pins.json` gained a `FakeGame._execute` row; `REQUIRED_TESTS_O3` two names. None touches
    `choose`, `_take_default_choice`, `_choice_left`, the machine beats or the story trace. The lead's merge: keep both
    sides' `source_pins.json` rows (rows of different names replay independently, `pin_rows_bad`), both
    `REQUIRED_TESTS_O3` additions, and re-run the whole gate (11.2 #8).
17. **The engine publishes no `rt`** (driver critique #1). `PublishState` (HarnessAgent.cs:1500-1595) writes `frame`,
    `seq`, `ack`, ... and no clock; `_game_t` (segment_drive.py:1393-1402) and `_game_seconds` (session.py:8377-8386) then
    read state.json's mtime -- the agent's last write, a WALL time (O4's rehearsals record the rate's `source: mtime`).
    A starved harness does not slow it. So no wait in O5 is judged "on the game clock" as if load could not fake it:
    the quiet cap scans what was published before it judges, and is the instrument's V13 (S10).
18. **The agent's dialog-section catch** (driver critique #6). `AppendDialog`'s catch (HarnessAgent.cs:1699-1702)
    publishes `{"open": false, "count": 0, "texts": [], "phrase_raw": [], "choice": null}` for that sample, while
    `AppendMenu` (:1732-1761, its own try) still publishes the group. One such sample opens a quiet window early (127 is
    still up), would read as a choice's close to `_choice_left` (`choice` None is "not ready", session.py:6301-6305), and
    would end `choice_close` early. The engine's own close of a choice sets the group '' at the answering Confirm
    (Dialog.Hide -> `ButtonGroupState.DisableAllGroup`, Dialog.cs:629, ButtonGroupState.cs:291) and keeps it '' until
    another group activates: so NO choice block while the group still reads `Dialog.Choice` is the catch, never a close.
    S10 (re-arm) and S11 (no landing on it) both read it so.
19. **Blank collides with Zidane** (driver critique #5, with a correction). The pair rule skips an object only when it
    has flag 2 and the player flag 4 (WalkMesh.cs:915-917); `SetObjectFlags(5)` (e7 t1 ip770, right after 117 opens at
    ip764) leaves bit 2 clear. `SetObjectLogicalSize(size, collRad, talkRad)` (DoEventCode.cs:1498-1524; the controller
    radius is size x 4, :1531): Blank (20, 20, 30) at e7 t0 ip173, Zidane (20, 24, 40) at e3 t0 ip218. The agent publishes
    him `coll` true, `solid` false (no flag 16), `r` = 4 x (20 + 24) = **176** (HarnessAgent.cs:2348-2349; the critique's
    160 took Zidane's size for his collRad), `range_r` null (no tag 2), `talk_r` = 4 x (30 + 40) + 37 + 60 = 377
    (SetWalkSpeed(37), e7 t1 ip263; :2360). e9, e11 and e31 are `SetObjectFlags(14)` (bit 2 set: walk-through for a
    player with flag 4 -- Zidane's `SetObjectFlags(7)`), published `coll` false. The player is never published
    (HarnessAgent.cs:2321): 153@325 publishes {7, 9, 11, 31}, never 3.
20. **THE BRANCH WITNESS** (claim critique #13, closed rather than stated). 128's answer goes to `Bit[3795]` (ip1741)
    AND to `Map.Byte[27] := SYSVAR[9]` (ip1749); e2 t1 ip840/ip844 `SWITCH(0, L865, L843, L854)` on Map.Byte[27] sends 0
    to stage 21 (path 0: its first page 129 "Wait.  Hold on a sec!", e3 t1 ip1899) and 1 to stage 31 (path 1: its first
    page 141 "Let’s see...", e3 t1 ip3430; the apostrophe is U+2019). Every read of Bit[3795] in 153 sits behind
    `Int16[2] == 3` (e3 t1 ip1542/1571/3358/3387, e7 t1 ip1608/1637, e31 t1 ip686/715/870/899; ip1759 is the else of
    ip1730's `Int16[2] != 3`): at 325 the branch depends on SYSVAR[9] alone. So the first page after the answer is the
    GAME's own record of the answer it took, independent of the stored value -- an outside move of the cursor in the
    answer's last frame (which `selected_before` cannot see) shows 129, while a fork that stores a constant shows 141.
    Both branches rejoin at stage 23 (e2 t1 ip928 and ip1408 both set `Map.Byte[24] := 23`).
21. **The stair route's clearance** (driver critique #11, measured). On stock 153 with the 33 closed, sampled every 5 u:
    the planner's route (clearance 80, the controller radius) passes the stair-foot inner corner at 78.4 u ((-944, 807),
    its second leg, 9.5 deg off "left") and runs 91-93 u off the inner wall along the contour leg (within 1 deg of
    "left+down"); the stair is 325-395 u wide there, 220-295 u free on the outer side. At clearance 120 the planner gives
    (1105, -78) -> (-943, 882) -> (-1391, 690) -> (-1711, 370) -> (-1700, 300), 3273 u, >= 124 u off every wall, the
    contour crossed at ~(-1523, 558) (2935 u along); at 140, 3307 u.
22. **The stair evidence holds by the CONTOUR, not by the vertices** (claim critique #11, and a defect it did not
    name). The PSX y -450 contour of the open mesh runs only through tris 53 and 56 (floor 2), its edge crossings at
    x -1722..-1403 (the planned route crosses it at ~(-1479, 529), tri 56). Heights are continuous across shared edges,
    so a walk first stands at y <= -450 ON that contour. The other open tris reaching y <= -450 -- 50, 51, 57, 60, 61,
    62, 65, 67, 69, 71, 76, 77 -- lie wholly beyond it, reached only across it; four of them (50, 51, 60, 71: the upper
    stair) have vertices AND centroids at x -460..-866, and 62 and 69 vertices at -926 (all 118 open tris are one
    component, reached from the spawn's tri 66). O5-GOALS (d) as first written here ("every open tri vertex and
    centroid at PSX y <= -450 lies at x <= -1100") was therefore false on the real mesh and would have failed the
    offline check; restated in 6.1 on the contour's points (each tri's edge crossings), which is also the critique's
    completeness fix.

---

## 1. Module layout

### 1.1 Files

| File (in `studies/story-trace/` unless a path is given) | | What it holds |
|---|---|---|
| `segment_regress.py` | edit, FIRST (A0) | The gate extended to O4: G0''' (`--capture-o4`), G22-G25 (1.4); G21 over the UNION of the O3 and O4 baselines' `sources`, `--rebaseline-source` over both; `REQUIRED_TESTS_O5` empty; G26 joins at B3, G27 at C2. |
| `research/o4_regress_baseline.json` | new, FIRST (A0) | The captured O4 baseline (LF, `-text`), its `sources` included. |
| `segment_drive.py` | edit (A1-A3) | S10 (the guard and its pure `guard_strays`), S12 (the run-wide witness), S13 (visit-scoped cells and VOID cells). Each opt-in. `stray_answer` is NOT edited (O5 attributes with `guard_strays`). |
| `tools/harness/session.py` | edit (A2) | S11: ONE new method, `Session.choose_landed`. `choose`, `select`, `_take_default_choice`, `_choice_left` untouched. (F15's contingency, if F15 calls it, adds an opt-in `clearance` keyword to `route_to`: 7.3.) |
| `tools/harness/fakegame.py` | edit (B1) | H13 (`story_suppress`), H14 (the `{"visit": knobs}` machine beat, `_VisitBeat`, its own `publish`), H15 (its fault knobs). The dispatch lines in `_next_beat` / `_start_machine` and the trace functions are re-baselined by name (G21). |
| `ff9mapkit/tests/test_harness.py` | edit | The tests of 1.2, 3 and 9; the O5 route builder `_o5_route` (test-side, 3.4). No existing test body changes (G21). |
| `o5_hallway.py` | new (C1) | `O5Segment(o4_castle.O4Segment)` and its module functions (1.3). |
| `o5_forks.json` | new (C1) | The chain manifest: O4's, reused (6.4). |
| `o5_dryrun.py` | new (C2) | Synthetic sessions, units and offline mutants (section 8). |
| `o5_rehearse.py` | new (C3) | R-STAIRS, R-FULL, R-WALK-VOID, F-SMOKE, F-PASS, R-RACE (optional) for `tools/play.py` (section 7). |
| `.gitattributes` | edit | `studies/story-trace/research/o4_regress_baseline.json -text` (A0); `studies/story-trace/o5_predictions*.json -text` (C1, before any freeze). |
| `PLAN.md` | edit (C4) | The O5 section: "draft: rehearsals pending, freeze pending". |

NOT edited: `o1_opening.py`, `o1_dryrun.py`, `o2_alexandria.py`, `o2_dryrun.py`, `o2_rehearse.py`, `o3_prima_vista.py`,
`o3_dryrun.py`, `o3_rehearse.py`, `o4_castle.py`, `o4_dryrun.py`, `o4_rehearse.py`, `tools/harness/channel.py`,
every frozen predictions file. `o2_alexandria`, `o3_prima_vista` and `o4_castle` are imported as shared code; their
outputs are the gate (G8-G11, G15-G18, G22-G25). O5's census, region and entrance logic are its own functions in
`o5_hallway.py` (0.2 #10, #11), never edits to O4's.

### 1.2 The shared changes (each opt-in or behaviour-neutral for O1-O4)

**S10 -- THE PRE-CHOICE GUARD** (`pred["guard"]`; decision 3; critic #2, #6, #7; revised for the driver critique #1,
#2, #6 and the claim critique #2, #4, #6, #13). New code beside O4's policy, never a refactor of it (`quiet_tick`,
`note_choice`, `policy_page` and `stray_answer` stay byte-identical).
```python
GUARD_KEYS = ("donor", "sc", "markers", "choice", "branch", "page_once_ticks", "quiet_cap_s", "why")
def guard_of(pred) -> dict | None:
    """pred["guard"] checked STRICT before anything is driven, or None (then nothing below reads it). ValueError on: a
    key not in GUARD_KEYS or one missing (why optional); donor, sc not ints (a bool is no int); markers not a non-empty
    list of non-empty strings; choice not the `match` of exactly one rule of pred["choices"], that rule without
    `take: "default"` and with a `pick` (the guard exists for a non-default pick); branch not a list of two distinct
    non-empty strings (the pick's branch page marker, then the other branch's); page_once_ticks not an int 4-30;
    quiet_cap_s not a number in (0, 10]; pred also carrying `chanbara` (one input policy a segment)."""
```
In `_Drive` (all behind `self.guard is not None`; state `self.gd`, reset at every new visit by rule 3):
- **Every press under the guard** (rule 7's, page-once's, the answer's) is a `press` row with `seq`, `ack_frame` (the
  frame of the read right after the press returns, O4's `policy_page` shape), `raws` (the listed windows'
  `phrase_raw`) and `marker` (True when page-once pressed a marker window); `gd["last_ack"]` is the latest `ack_frame`
  of any press of the visit.
- **Rule 6 (a choice published):** `guard_note_choice(st)` -- the quiet window closes; when the published choice is the
  guarded one (`rule_for(...)` is the guard's rule) its FIRST publication frame is kept (`gd["first"]`: the ring's
  earliest sample of it since the visit's first frame). Then the readiness hold (O1's) and the answer through S11, its
  presses' seq span kept (`gd["answer"] = [before, after]`).
- **Rule 7 (a page, control off; after the stop pages and `no_pages`):** `guard_page(st)`, in this order:
  (o) THE JUDGMENT -- once, at the first page after the guarded choice's VERIFIED answer: the `guard` row (below) is
  written and judged (128 has closed by then, so its close is known); anything but "ok" VOIDs the run there, nothing
  pressed; "ok" goes on to (iv);
  (i) the guarded choice was published and left with no answer of the driver's (`gd["first"]` set, not answered):
  `guard_stray("choice_gone")`;
  (ii) the quiet window is OPEN: a page holding a marker (raw or text) is 127 itself -- a sample listing no window
  opened the window early (the agent's dialog-section catch, 0.2 #18) -- so the window RE-ARMS (`open_frame` back to
  None, `gd["rearms"] += 1`, a `quiet` row logged) and the page goes to (iii); any other page: an `observed` row (kind
  `quiet_page`), V17 (driver, game-observed: VOID-ASYM (d) reads it), nothing pressed;
  (iii) in the guard's cell (place, published SC, control off) with some listed window holding a marker -- in its
  `phrase_raw` OR its rendered text (the raw holds the whole source from the first sample; the text can grow while it
  types) -> PAGE-ONCE: press only when (a) some marker window's `phrase_raw` is not held off at `st.frame` -- a pressed
  raw is held off until the press's ack-read frame + `frames_for_ticks(page_once_ticks)` (O4's S8 b, keyed on the RAW,
  not the text) -- AND (b) `st.frame` is past `gd["last_ack"]` + `frames_for_ticks(page_once_ticks)`, the hold-off of
  the LAST press of the driver's whatever it pressed (a rule-7 press on 126 can go down on 127 and close it, and 127's
  close-tween samples then carry a raw page-once never held off: 2.5.5). The first such press ARMS the quiet window
  (`gd["quiet"] = {"armed_frame", "open_frame": None, "open_game": None}`);
  (iv) any other page: O1's rule 7 exactly, its press row carrying the fields above.
  Then O1's wait (`frames_for_ticks(CUTSCENE_PAGE_TICKS)`).
- **`guard_quiet_tick()`** (every poll, rule 3's place where O4 runs `quiet_tick`): armed and not open -> the first ring
  sample after `armed_frame` listing no marker window OPENS it (`open_frame`; `open_game` = `_game_t` of that sample);
  open -> FIRST the current sample and every ring sample since `open_frame` are scanned, and one publishing a choice
  closes the window as `guard_note_choice` does (rule 6 answers it on this poll) -- a stalled read never meets the cap
  with 128 already up (a WindowSync choice stays up until answered); only then is the cap judged: no choice within
  `quiet_cap_s` on the game clock since `open_game` (`rt`, else the state file's mtime -- on the engine the agent's own
  write time, a wall clock: 0.2 #17), or within 10 x `quiet_cap_s` of wall time, is V13 (driver: "no choice read
  within N s of the quiet window's opening"). The instrument's, never the game's: a fork that never asks 128 reads V13
  in every F run, which VOID-ASYM (b) catches.
- **`guard_strays(log, events, steps, lo, hi, *, exclude)`** (pure, new): every `press` row with a `seq` not in
  `exclude` whose down frame (its `accepted` event's frame + 1, HarnessAgent.cs:599-607) -- or, with no accepted event to
  place it, its decision frame (`pre.frame`; fail-closed, O4's SWORD (f) rule) -- lies in [`lo`, `hi`) (`hi` None:
  open). Returns `[{"seq", "why", "down_frame", "decision_frame", "placed"}]`. The guard's window: `lo` = `marker_last`
  (the last ring sample before `gd["first"]` listing a marker window: 127's last listed sample -- a press that went
  down after 128 opened but before the ring's earliest 128 sample lies inside it), `hi` = `choice_close` (the first ring
  sample after `gd["first"]` with no choice block while the menu group is not `Dialog.Choice`: a sample with no choice
  but that group is the dialog-section catch, 0.2 #18); `exclude` = the answer's own presses (every seq in
  `gd["answer"]`'s (before, after]: select's Down and every Confirm of `choose_landed`, not only the one `row_choose`
  marks `answer`) and the marker page's CLOSING press (`closing_seq`: the last press with `marker` True). That press is
  excluded by proof, not by trust: page-once presses a marker sample only past every press's hold-off, so 127 is up
  and waiting (a WindowSync with no `[TIME]`, closed by a Confirm alone) and the press goes down on it; when the ring
  holds no sample of 127's close tween its down frame lies AT OR AFTER `marker_last` -- O4's rehearsal 20261002-082739
  run 1 decided its closing press at frame 2229 and read the page gone at its own ack, 2237 -- so without the exclusion
  every such run would read as a stray.
- **`guard_stray(kind)`**: "choice_gone" -- `guard_strays` over the window: one or more -> V17 (driver: "a press of the
  driver's own (seq N, why) went down in [127's last sample, 128's close) before its answer"); none -> V13 (driver:
  "choice 128 left with no press of the driver's in [127's last sample, its close): unattributed input"). Never the
  game's: member(153)'s e3/e31 bytes are the donor's (O5-BUILD) and no dialog code keys on 151/153/154 (the
  field-keyed branches of Dialog.cs, DialogManager.cs and ETb.cs name 100, 206, 1400-1425, 1608, 1652-1659, 1850, 2209,
  2950-2952 and 3009-3011), so the game cannot answer one side's 128 alone -- while outside input the witness misses
  (it reads LEVELS between blocking calls, segment_drive.py:3043-3057) can. "choice_reask" (rule 6's once-VOID of the
  guarded rule after its VERIFIED landing) -> V2 (game) outright: neither answer brings 128 back (both branches rejoin
  at stage 23, 0.2 #20) and S11's verification is not fooled by the dialog-section catch. Logged `{"k": "guard_stray",
  "kind", "lo", "hi", "strays", "v", "by"}`.
- **The `guard` row** (one per guarded choice, written at (o), or at a stray): `{"k": "guard", "field", "visit",
  "armed_frame", "open_frame", "rearms", "marker_last", "choice_first", "choice_ready", "choice_close", "answer":
  [before, after], "closing_seq", "presses": [{"seq", "why", "marker", "accepted_frame", "down_frame",
  "decision_frame", "raws"}], "strays", "branch": "pick" | "other" | None, "branch_frame", "branch_raw", "verdict"}` --
  every press row of the visit with a `seq`, its accepted frame joined from ONE `g.channel.events()` read. THE JUDGMENT,
  in order: `armed_frame` None -> V17 (driver: "the marker page was closed by a press page-once did not make");
  `strays` non-empty -> V17 (driver, as above); the page holds `branch[1]` -> V13 (driver: "the game took the other
  branch (its first page holds '<marker>'): the answer it took is not the pick -- outside input, or a cursor move no
  sample showed"); it holds neither marker -> an `observed` row (kind `after_answer`) and V17 (driver, game-observed);
  else `verdict` "ok", `branch` "pick". O5-CHOICE (b) and (d) re-read the row (5.3).

Tests (A3; each into `REQUIRED_TESTS`, G7's selection):
`test_segment_guard_of_is_strict` (each refusal once, `branch` included);
`test_segment_guard_presses_the_marker_page_once` (a director re-shows the marker page after the first Confirm -- the
"only finished the type-out" case, 127's own: re-pressed only once `page_once_ticks` of GAME frames passed; a stale
sample (`Session.state` wrapped to return the previous document once) is never pressed; break: key the hold-off on the
text, or compare wall time);
`test_segment_guard_holds_off_after_any_press` (the page before the marker page pressed by rule 7 with its send delayed
by a wrapped `g.press` until it goes down on the marker page and closes it: the marker page's close-tween sample is never
pressed, and the guard's judgment reads V17 "never armed"; break: hold off on the marker's own presses only);
`test_segment_guard_quiet_window_presses_nothing_until_the_choice` (a 30-frame gap between the marker page's going and
the choice: no press row in it, the `quiet` and `guard` rows logged, the choice answered; break: open the window at the
press);
`test_segment_guard_marker_page_rearms_the_quiet_window` (a wrapped `Session.state` returns one document whose dialog
section is the agent's catch while the marker page is up: the window opens, the marker page is read again, the window
re-arms, page-once presses it past its hold-off, the run goes on, no `observed` row; break: read every page in an open
window as `quiet_page`);
`test_segment_guard_page_in_the_quiet_window_is_v17_observed` (a NON-marker page);
`test_segment_guard_cap_scans_first_then_is_v13` (the fake on `publish=("mtime",)` -- no `rt`, the engine's own clock --
with a 5 s READ stall across the marker page's close and the choice's publication: the choice answered, never V13 or
V14; the choice withheld past `quiet_cap_s`: V13, driver; break: judge the cap before the scan, or attribute it to the
game);
`test_segment_guard_strays_from_127s_last_sample` (pure, `guard_strays`: a press down between `marker_last` and
`choice_first` counts; the closing marker press excluded though its down frame lies after `marker_last` (O4's 2229/2237
shape); select's Down and both Confirms of a two-Confirm answer excluded; an unplaceable press counted by its decision
frame; break: open the window at `choice_first`, or exclude only the press marked `answer`);
`test_segment_guard_choice_gone_is_v17_or_v13` (a mutant driver's Confirm landing on the choice before its answer: V17;
the fake answering the choice itself with no press of the driver's: V13, no `observed` row);
`test_segment_guard_reask_after_a_verified_landing_is_v2`;
`test_segment_guard_judges_the_branch_page` (the pick's page: "ok"; the other's: V13; neither: `observed` after_answer,
V17; a run whose marker page was never pressed: V17);
`test_segment_guard_is_opt_in` (O2- and O4-shaped predictions: no `gd` state, plain rule 7's press rows carry no `seq`,
`choose` -- never `choose_landed` -- on a non-default pick).
`stray_answer` is left exactly as O4 froze it; A0's `test_segment_stray_answer_keeps_o4s_strings` pins every outcome's
full strings (claim critique #14).

**S11 -- THE VERIFIED LANDING** (`Session.choose_landed`; decision 3; critic #6; revised for the driver critique #4, #7
and the claim critique #6).
```python
def choose_landed(self, index: int, *, timeout: float = 5.0) -> dict:
    """Select option `index` of the ready choice and Confirm it until the GAME took it -- judged as _take_default_choice
    judges its Confirm (the reads after it, on the game's clock: _choice_left), never by a blind wait, with one read
    refused as a landing: no choice block while the menu group still reads CHOICE_GROUP is the agent's dialog-section
    catch (HarnessAgent.cs:1699-1702), not a close -- the engine's close sets the group '' at the answering Confirm
    (Dialog.cs:629, ButtonGroupState.cs:291) -- and the watch goes on from that read. Returns {"index", "text",
    "prompt", "count", "field", "frame", "landed", "confirms", "why"}: landed True when a read after a Confirm stopped
    taking answers, or -- after a read gap -- another window is up (this one was answered); False when the window still
    takes answers after CHOICE_CONFIRMS Confirms, each re-pressed only while the window is ready with its cursor on
    `index` (why "did not land"), or when the cursor left `index` while it waited (why "the cursor left the pick:
    <selected>"; nothing more pressed). Raises ChoiceUnseen, as _take_default_choice does, after a read gap whose window
    reads as this one (_choice_could_be)."""
```
It is `_take_default_choice`'s loop with three differences: the cursor is steered to `index` first (`select`); a "waits"
verdict re-presses only when the last read still publishes `selected == index`; and a "left" read from `_choice_left`
that has no choice block while the group still reads CHOICE_GROUP is skipped (`_choice_left` itself is not edited:
`choose_landed` calls it again from that read). A ready window that does not take a Confirm is real: one in the frame
between the group's activation and `isChoiceReady` commits SelectChoice and hides nothing (Dialog.cs:161-164, :787-789),
and a prompt still TYPING takes the first Confirm as "finish the text" (:803-807) -- O1's candle, not 128, which is
`[IMME]` (0.2 #14). Either way the second Confirm answers: the case a blind `choose()` read as answered and the
driver's once-rule then read as V2 by the GAME. Nothing else in session.py changes.

The driver (rule 6's `answer`, under the guard only): `before = g.channel.seq`; `took = g.choose_landed(index)`
(`ChoiceUnseen` -> V17 driver, "the answer's landing went unseen"); `self.row_choose(before, g.channel.seq, st)` (O4's
S9 rowing, now under the guard too: each press of the answer a `press` row `why` "choose", the Confirm marked `answer`
with `selected_before`); the witness polled at once (S12); `took["landed"]` False -> V17 driver ("the answer N did not
land: <why>"); the answer row's `selected_before` None -> V17 driver ("the answer's Confirm could not be placed: no
accepted event" -- the agent retries a failed append to events.jsonl only at its NEXT event, HarnessAgent.cs:2443-2455,
and `row_choose` leaves `selected_before` None without one, segment_drive.py:3270-3279); a value other than `index` ->
V13 driver ("the cursor read N, not the pick, as the answer's Confirm went down: outside input"); else the `choice` row
(`took` the record), `gd["answered"] = True`, `gd["answer"] = [before, g.channel.seq]`. The answer's last frame (after
the last sample before its down frame) is the branch witness's (S10 (o), 0.2 #20). Without the guard: `g.choose(index)`
exactly as today (O1's candle, O4's encore).

Tests (A2; G7's selection): `test_segment_choose_landed_lands_once`; `test_segment_choose_landed_repress_while_typing`
(the fake scene's `typing` 40 frames: the first Confirm completes the text, the second lands; `confirms` 2; break: a
blind wait after one Confirm); `test_segment_choose_landed_gives_up_unlanded` (the fake instance's `_scene_press`
wrapped to drop Confirms on the choice: landed False after 3, why "did not land"); `test_segment_choose_landed_stops_
when_the_cursor_moves` (a director moves the cursor to 0 after the select: landed False, why "the cursor left the
pick: 0", no Confirm after); `test_segment_choose_landed_raises_on_an_unseen_landing` (a read stall after the Confirm
with the same window up: `ChoiceUnseen`, nothing pressed again -- O2's starved-confirm pattern);
`test_segment_choose_landed_is_not_fooled_by_the_dialog_catch` (the fake drops the first Confirm and a wrapped
`Session.state` returns, right after it, one document whose dialog section is the agent's catch while the menu group
still reads `Dialog.Choice`: not landed on that read, re-pressed, lands; `confirms` 2; break: accept any read without a
choice block as the close).

**S12 -- THE RUN-WIDE WITNESS** (`pred["witness"]`; decision 4; critic #10).
`witness_of(pred)` (strict: keys `input_every_s` -- a positive number at most 0.1 -- and optional `why`); `_Drive`:
`self.witness_pol = witness_of(pred)`, `self.witness_every = (self.witness_pol or self.chanbara or {}).get(
"input_every_s")`; `go()` polls when `self.chanbara is not None or self.witness_pol is not None`; `poll_witness` reads
`self.witness_every` (for O4, its policy's value: today's). The witness callable is `drive(..., witness=)`'s, as
O4's (`o4_castle.input_witness(g)`); a non-neutral reading is an `input` row, then V13. S11 polls it right after the
answer. Tests (A1): `test_segment_witness_of_is_strict`; `test_segment_drive_polls_the_witness_run_wide` (no Chanbara
policy: a stub non-neutral at a page -> V13 and an `input` row; without the key the stub is never called).

**S13 -- VISIT-SCOPED CELLS** (`cell["visit"]`; 0.2 #15; the claim critique #5). `cell(pred, donor, sc, visit=None)`: a
cell carrying `visit` (an int >= 1: the 1-based position of the visit in `visits`) matches only that visit; a cell
without it, any visit (today's). `_Drive.go` passes `self.at + 1` (rule 8 and the watch rows). The drive's start
refuses a `visit` that is no int >= 1 (a bool refused). `step_of`, O2-GOALS and every caller without the key are
unchanged. AND THE VOID CELL: under a table with any visit-scoped cell (`self.visit_cells`), every RouteVoid's cell and
every `observed` row's cell is `[donor, sc, visit]` (`void()`, `observed()`: the visit `self.at + 1`; `stray()`'s late
V11: its step row's `visit`), so the same class at two visits of one place is two keys for VOID-ASYM -- V4 at 153@325
after the stair step on one side and V4 at 153@316 on the other never cancel; a table without one keeps `[donor, sc]`
(O1-O4 byte-identical). Tests (A1): `test_segment_cell_visit_scopes_a_cell` (pure);
`test_segment_drive_control_at_another_visit_is_v4` (the fake: a revisit of the same place at the same SC grants
control -> V4, game; the same table without `visit` runs the step: today's); `test_segment_drive_void_cell_carries_the_
visit` (that V4's cell is `[place, sc, n]`, n the revisit's position in `visits`, and an `observed` row's carries its
visit too; without a visit-scoped cell both are `[place, sc]`; break: key the VOID by `[donor, sc]`).

### 1.3 `o5_hallway.py`

`O5Segment(o4_castle.O4Segment)`:
- `tag = "O5"`, `predictions = HERE / "o5_predictions_v1.json"`, `manifest = HERE / "o5_forks.json"`, `session_file =
  "o5_session.json"`, `report_file = "o5_report.txt"`, `chain_dir`/`build_dir` O4's (`C:\gd\_ns_playtest\o4\fork`,
  `...\o4\build`), `accept_us_build = False`, `recovery = 4600`, `end_session_warps = True`.
- `core_ids = ("START", "NO-SC", "CHAIN", "RESIDUE", "WRITES", "NULL", "STABLE", "LANDING", "CHOICE", "WALK",
  "PATTERN", "MASKED", "STATE", "JOIN")`; `titles` every check's O5 text (the O4 titles' shape).

**Inherited unchanged:** `read_session`, `forbidden_check`, `void_asym_check` (O4's (a)-(d); its keys take S13's
three-element cells as they are -- `tuple(cell)`), `start_check` (O3's, data-driven: four residue rows),
`no_sc_check` (O3's), `span_check` (CHAIN), `residue_check`, `writes_check` (O4's EXACT over writes + chain + ladder
`[]`), `null_check`/`stable_check`/`join_check`, `masked_check`, `history`/`suppressed`/`state_check` (O2's),
`text_check` (O4's, over `text_blocks` [3]), `fingerprint_extra` (O4's: override70, text, lang, settings, battle data,
text3, engine), `drive` (O4's: `SD.drive(..., witness=input_witness(g))`).

**Overridden:** `why_void` (O3's reasons -- O2's A-NOSTART/A-FORBIDDEN/A-MISMATCH, A-START, A-NOEND, `cut_row` -- with
A-START scoped to VISIT 1: O3's rule reads any error-path row of the start place (o3_prima_vista.py:1220-1227), and O5
revisits its start place, so an A-START whose row lies after the run's first row of place 154 is withdrawn -- a visit-3
error path is the game's V5 at `[153, 1190, 3]`, which VOID-ASYM (a) reads, never "the start state took 153's error
path"; the claim critique #7); `draft()` (section 4; members and names from O4's `campaign.toml`, `route_members` over
153, 154, 151); `freeze()` (7.3's refusals, then the base's); `offline_extra` (O5-TEXT, O5-CENSUS, O5-REGIONS, O5-GOALS); `build_check`
(the base rule + O5's route build pins, 6.1); `keys_check` (O4's machinery -- O2's on a filtered copy, the `:=var` key,
`start_music` one key -- then O5's route pins instead of the fight pins); `census_check` (O5's own census);
`preflight_extra` and `capabilities` (6.2: P-DONOR and P-DONOR-LOG over 151, 153, 154; no P-GATE, no P-TEXT2);
`core_checks`; `landing_check`, `choice_check`, `walk_check`, `pattern_check` (5.3); `report_extra` (5.4);
`add_arguments`/`handle` (`--draft`, `--rehearsal-report`).

**Module functions** (pure unless named a reader): `ROUTE_DONORS = (153, 154, 151)`; `route_members(members)` (O4's
shape over 153, 154, 151); `visit_entrances(pred) -> {place: [entrances in visit order]}` (the start's `entrance`, then
each chain key's value for the visit after it: {153: [325, 316], 154: [304]}); `store_census(fields, stock, pred, *,
sites=None, classify=None)` (6.1); `regions_problems(pred, stock)` (6.1); `goals_extra(pred, walkmesh=None)` (6.1);
`pattern_of(rows, pred, members, join)` (5.3: the run's `c` multiset and per-visit `w` sequences as O5-PATTERN compares
them); `route_pins()`; `trace_summary(rows, pred, *, side="S", end_fields=None)` (cut at the stage's end PLACES -- O4's
lesson CI14); `rehearsal_report(run_dir)`; `run(g)`; `main(argv)`.

### 1.4 The regression gate extended to O4 (`segment_regress.py`)

The implementer extends the gate and captures its O4 baseline FIRST (A0), before any shared-code change. The O4 items
import only O4's modules (`o4_castle`, `o4_dryrun`) inside their functions.

`O4S = C:\gd\Dream-World-IX\.harness-runs\20261002-091051-story-o4`, `V1_O4 = HERE / "o4_predictions_v1.json"`
(sha256 `638e43fc...`).

| Item | Check |
|---|---|
| G0''' | `py studies/story-trace/segment_regress.py --capture-o4` writes `research/o4_regress_baseline.json` (LF, `-text`): the full `(checks, report)` of O4S with V1_O4; every `o4_dryrun` session case's `(checks, report)` and "predictions-changed"'s; every unit's `(name, ok, detail)` (`o4_dryrun.units(...)` then `listed_units(...)`, in run_cases's order); `O4.offline_check(V1_O4)`; the tests G19 collects; the HEAD and V1_O4's sha; and `sources`: the AST sha of every test G19 collects and of every function in `FAKE_PINS_O4` (below) -- only names the O3 baseline does not already pin (a name pinned in both is refused). It refuses an existing file, refuses unless G19, G20 and G22-G25's baseline-free halves pass, and takes TWO readings first, refusing when they differ after every temporary root reads `<tmp>` (O3's rule, G0''). |
| G22 | `O4.analyse(O4S, pred_path=V1_O4)`: the report equals `(O4S/"o4_report.txt").read_text(encoding="utf-8")` exactly and the baseline's; the checks the baseline's; PROVEN with 16 checks, all True. |
| G23 | `py studies/story-trace/o4_castle.py --analyse O4S --predictions V1_O4` exits 0 and prints that report (plus print's newline). |
| G24 | Every `o4_dryrun` session case's `(checks, report)` and unit's `(name, ok, detail)` byte-equal to the baseline's (each temporary root `<tmp>`), and `o4_dryrun.run_cases(V1_O4)` returns 0 printing "103/103 cases as registered" (N from the replica: sessions + "predictions-changed" + units). The replica follows `run_cases` step for step (`prepare` -> `pred/`, `sessions/`, the CASES loop through `make_session` and `O4.analyse(d, stock=stock)`, the FROZEN case, `units(pred, stock, scripts, sdir, path, tmp)`, `listed_units(pred, stock, tmp)`), as G17 does O3's. G24 IS O4's VOID-PATH BASELINE: story-o4 holds six covered runs. |
| G25 | `O4.offline_check(V1_O4)` equals the baseline's `[(ok, what, detail)]`: 4 checks, all PASS (reads the O4 build and the install, read-only). |
| G21 (extended) | THE SOURCE PINS over the UNION of the O3 and O4 baselines' `sources`, against one `research/source_pins.json` (append-only; `--rebaseline-source NAME` looks NAME up in either baseline; `pin_row`'s refusals unchanged; its message names "the O3 and O4 baselines' sources"). |
| G26 (from B3) | `pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o5_ or fake_visit or fake_story_suppress"` from `ff9mapkit/`: all passed, 0 failed, 0 skipped, 0 errors; every name in `REQUIRED_TESTS_O5` among them. No baseline: the list is the floor. |
| G27 (from C2) | `o5_dryrun.run_cases` on the frozen O5 predictions once they exist, else the draft: returns 0 printing "N/N cases as registered", N at least `O5_DRYRUN_FLOOR` (the count C2 prints). |

`FAKE_PINS_O4` (the fake O4's tests run on, by qualified name): `FakeGame._start_machine`, `FakeGame._step_machine`,
`FakeGame._frame_once`, `FakeGame._story_row`, `FakeGame._story_start`, `FakeGame._story_stop`,
`FakeGame._story_store`, `FakeGame._warp_writes`, `FakeGame.script_store`, `_machine_knobs`, and every method of
`_Win`, `_Machine`, `_KeyonPairBeat` and `_ChanbaraBeat` (`functions_of` pins `Class.method`; module constants are not
pins -- a constant that changes behaviour fails G19). `_missing()` gains O4S's session and report, V1_O4, the O4
baseline, and from C2 the frozen O5 predictions or O4's `campaign.toml`. Tests O5 adds named `test_segment_*` join
`REQUIRED_TESTS` (G7); every `test_o5_*`, `test_fake_visit_*`, `test_fake_story_suppress_*` joins `REQUIRED_TESTS_O5`.
O5's rehearsal tests are named `test_o5_rehearsal_*` (never "rehearse": G12's selection); no O5 name holds "o4_",
"o3_drive", "o2_" or "o1_".

---

## 2. The drive

### 2.1 The model (keys the driver reads; the rest of the predictions is the analysis's)
- **`table`**: ONE cell, `{"donor": 153, "sc": 1190, "visit": 1, "steps": [the stair step]}` (2.4; S13). Control
  anywhere else -- 154@304, 153@316 (visit 3), 151 before rule 1 -- is V4 (game).
- **`battles: []`** (any battle V10); no `movies`; **`naming: []`** (151's naming is after the cut; one before it is V10).
- **`stop_pages`**: `[{"match": "Env Play()", "why": "153's and 154's ambient error window 56 ('Error Env Play() Slot=n':
  153 e0 t0 ip2304/2338, 154 e0 t0 ip487/521): Byte[13]/[14] arrived as 2 or 9"}]`.
- **`choices`**: the guarded rule and O1's skip net (2.5.1). **`guard`** (its markers, the branch markers, the hold-off
  and the cap), **`witness`** (4.10).
- **`route: [153, 154]`, `visits: [153, 154, 153]`, `end_fields: [151]`, `side_ends: {"S": [151], "F": [31244]}`**
  (S6). **`regions`** (4.15): the driver reads role `exit` (153.e28) for its landing judge and the step's `avoid`.
- **`budget`** with `end_row_s` (rule 1 waits for 151's first row) and `settle_s` (rule 6's readiness hold and rule 8's
  settle).

### 2.2 The driver loop for O5 (O4's rules in O4's order; the opt-in additions marked)
Every poll reads `st`, `sc` and `donor = place(fid, members)`. (S12) the witness first.
1. **End** (`fid in self.ends`: real 151 on S, member(151) 31244 on F): the end state (4.9, no Byte[8]), the last
   scan, the end row (151's first trace row, up to `end_row_s`), `reached`. Then the stall watchdog.
2. **Route**: on F a real 151/153/154 is **V19** (game, a finding: `rerun.stop_on`); anything else off the route V11.
3. **Visit**: the order 153 -> 154 -> 153; (S10) the guard's per-visit state reset; (S10) `guard_quiet_tick()` (the
   window opens; open, a choice in the ring closes it before the cap is judged; the cap V13).
4. Naming: V10. 5. A tutorial or a battle: V10.
6. **A choice**: (S10) `guard_note_choice`; O1's readiness hold; the rules (2.5.1); (S11) the verified landing.
7. **A page**: the stop page (V5, nothing pressed); then (S10) `guard_page` -- the judgment at the first page after the
   answer (the branch witness), the gone choice, the quiet window (a marker page re-arms it), page-once on the marker
   page past every press's hold-off -- else O1's press; each press a row with `seq` and `ack_frame`.
8. **Control held** (settled `settle_s`): (S13) the cell (153, 1190) at visit 1 runs the stair step (2.4); anywhere else
   V4 (game), its cell `[place, 1190, visit]`.
9. Otherwise wait (the scripted climb, fades, the scenes' walks).

`out()` keeps its keys (no `zones`/`prompts`: no Chanbara policy); the guard rows are log rows.

### 2.3 Every research beat, and what handles it
The research's `reconciled.route.beats` 1-34 (the rest are past the cut), with the critic's corrections.

| # | Field | Beat | Handled by |
|---|---|---|---|
| 1 | 70 -> 153 | the raw warp; residue SC bytes 0 (0->166), 1 (0->4), FieldEntrance bytes 2 (0->69), 3 (0->1) | `start_run` (O2's); O5-START (a) expects FOUR rows |
| 1 | 153 | Main_Init at 325 (SWITCHEX ip255 -> L273): the prologue ip22-ip200 (ip119 from old 1), `Map.Byte[24] := 1`, InitObject 3/7/31/9/11, InitRegion 26/27/28, InitCode 22 | nothing (WRITES, START) |
| 2-6 | 153 | pages 113, 114 (e7, waited by WaitWindow ip337/ip351), 115 (e3 + WaitWindow ip622), 116 (WindowSync), 117 (e7; e3's WaitWindow(1) ip752) | rule 7 |
| 7 | 153 | THE GRANT: ip755 `Map.Bit[158] := 1`, ip785 `EnableMove()`, no window up | rule 8: settle, then the cell's step |
| 8 | 153 | stage 6, THE STAIR WALK: the ip859 height test every tick; DisableMove ip893 the first tick PSX y <= -450 | the trigger step (2.4) |
| 9 | 153 | stage 17: the teleport ip1466 (2-3 ticks after the loss), the scripted climb at speed 37 | rule 9 (wait) |
| 10 | 153 | 126 (WindowAsync + WaitWindow ip1699) | rule 7 |
| 11 | 153 | 127 (e31 WindowSync ip663 after RunAnimation(3387) ip648, typed at [SPED=2]; holds the marker "let me pass"); then e31's WaitAnimation ip669 and Bit[231] ip670 | rule 7 under S10: page-once, the quiet window from its going |
| 12 | 153 | choice 128 (e3 WindowSync(0, 128, 128) ip1724, ~2 ticks after 127 is gone plus the animation's rest; [IMME]: no type-out; cursor 0) -> ip1741 `Bit[3795] := SYSVAR[9]`, ip1749 `Map.Byte[27] := SYSVAR[9]` | rule 6: the guarded rule, `choose_landed(1)` (S11) |
| 13 | 153 | path 1 (e2 t1 ip844 switches on Map.Byte[27]: stage 31): 141-150 and 130 (eleven windows, e3/e31 alternating) | rule 7; its first page, 141, is the guard's judgment (S10 (o): the branch witness) |
| 14-15 | 153 | 131 (e31 Sync), 132, 133 (e3, with walks) | rule 7 |
| 16 | 153 | KEYON pair 134 (window 7) + 135 (window 1), [INCS][TIME=-1]; gate (SYSVAR[8] or 250 ticks) then KEYON ip2336 | rule 7 (Confirm every 4 ticks until both close; an edge before the gate is lost) |
| 17 | 153 | 136 (e31 Sync) | rule 7 |
| 18 | 153 | 137 [NFOC][TIME=20] self-closing; the VIB ops ip2443-2453 (s62 on F) | rule 7 (inert Confirms, recorded `timed`) |
| 19 | 153 | KEYON pair 139 (window 0) + 138 (window 1); KEYON ip2711 | rule 7 |
| 20 | 153 | 140 [NFOC][TIME=20]; the jump; ip2953 `Byte[8] := 0`; DisableMove; Wait(65); ip3150 `Int16[2] := 304`; `Field(154)` ip3158 (F: 31246) | rule 7, then rule 3 |
| 21 | 154 | Main_Init at 304 (SWITCH ip234 -> L232): the prologue (eight new sites), the sound wait, ip279 `Byte[8] := 125`; Zorn e2 the defined player, no `Map.Bit[158]`: no control | nothing; control here V4 |
| 22-26 | 154 | pair 151/152 (KEYON ip215), 153 (Sync), 154 (Sync), pair 155/156 (ip392), walks, pair 157/158 (ip1265) | rule 7 |
| 27 | 154 | ip1520 `Int16[2] := 316`; `Field(153)` ip1528 (F: 31245) | rule 3 |
| 28 | 153 | Main_Init at 316 (L799): the prologue -- ip22/49/138/200 SUPPRESSED, ip57/119 emitted same (0.2 #2); Zorn e18 the defined player: no control | nothing; control here V4 (S13) |
| 29-32 | 153 | 159-164, pair 165/166 (KEYON e18 ip444), walks, 167-172, pair 173/174 (KEYON e20 ip883) | rule 7 |
| 33 | 153 | ip890 `Byte[8] := 0`; Wait(65); ip1077 `Int16[2] := 110`; `Field(151)` ip1085 (F: 31244) | rule 3 is never reached: rule 1 |
| 34 | 151 | THE END: 151 e0 t0 ip22 (31244 on F) -- the cut row; then (after the cut) the prologue, the BGM-load wait, ip315 `Byte[8] := 125` (the race) | rule 1 (per side) and its end row |

### 2.4 The stair walk (cell (153, 1190), visit 1)
**The step** (the walk plan with the critic's corrections; O2's `steps_default` under it):
```json
{"kind": "trigger", "name": "the stairs", "goal": [-1700, 300], "until": {"x_le": -1100},
 "avoid": ["153.e26", "153.e27", "153.e28"],
 "closed_tris": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 14, 15, 16, 17, 18, 19, 20, 21, 23, 24, 28, 32, 33, 34, 35, 38, 39,
                 41, 42, 43, 45, 46],
 "npcs": true, "interrupts": 1, "beat": "stairs", "start": [1105, -78]}
```
- **Who and when:** Zidane (e3, DefinePlayerCharacter e3 t0 ip176), controller radius 80 (SetObjectLogicalSize(20,24,40)
  ip218 x 4, DoEventCode.cs:1498-1531 = the planner's default clearance); granted at ip785 right after 117 closes; Blank
  (e7, (1068, 373)) shown and SOLID to him (0.2 #19: SetObjectFlags(5) ip770 leaves bit 2 clear, WalkMesh.cs:915-917 --
  published `coll` true, `solid` false, `r` 176, `talk_r` 377), talk on (118 "Hurry!", no store) -- never Confirmed: the
  driver presses Confirm only on pages (control off).
- **The floor:** `floor_for(153, closed)` = `PlayerWalkmesh(stock 153, closed=the 33)`: the upper corridor (floor 0,
  y -1499) over the hall would otherwise be the first tri `point_on_walkmesh` returns (no route at all on the plain
  mesh: `route153.out`); floor 1 (0xa001) is already closed at mask 255; closing floors [0, 1] would shut 15 real ground
  tris. The same floor on S and F (P-FLOOR pins member(153)'s deployed walkmesh to 153's).
- **The route** (the research's and the critic's re-plan with the harness's own call): (1105, -78) -> (-879, 818) ->
  (-1263, 754) -> (-1700, 300), 3196 u; from (1105 +- 25, -78 +- 25) 3169-3246 u; Blank >= 392 u off it (his body disc
  176); e26/e27/e28 >= 350/885/634 u off every leg; the -450 contour crossed at ~(-1479, 529) (tri 56), x <= -1284 on
  every re-plan. O5-GOALS re-derives it (6.1).
- **Clearance** (0.2 #21; driver critique #11): the route passes the stair-foot inner corner at 78 u -- inside his 80 u
  radius -- and runs 91-93 u off the inner wall on the contour leg, with 220-295 u free on the outer side (the stair
  325-395 u wide there, measured across both legs): wall contacts are possible, not forced. R-STAIRS records every
  hold's slide, push and stall on the last two legs (7.2); any one calls F15's opt-in step `clearance` 120 before the
  freeze (7.3).
- **The evidence** `{x_le: -1100}` (0.2 #9, #22; disputes #3; critic #12): the PSX y -450 contour of the open mesh runs
  only through tris 53 and 56, its points at x -1722..-1403, and heights are continuous across shared edges, so the
  first point a walk stands at y <= -450 is ON it; every other open tri at y <= -450 (the upper stair, some of it at
  x -460..-866) lies wholly beyond it and is reached only across it. No other control loss in stage 6 can stand at
  x <= -1100 (e26 x -264..212, e27 -777..777, e28 >= 1739, Blank's talk at 1068); a late loss sample -- the contour
  (x -1403..-1722), the teleport (-1165, 856), the scripted climb (x <= -1100 for ~49 ticks, ~1814 u at 37 u a tick) --
  still satisfies it. A height predicate would reject the teleport sample (published y ~231); `z_ge: 300` fails ~20
  ticks after the loss. O5-GOALS (d) proves both halves on the bytes (6.1).
- **Hazards:** e28, the back door (live whenever he has control: its tag 2 tests `SYSVAR[2]` alone) -- in `avoid`,
  registered `exit` (to 150, entrance 5), so a loss in it is the landing judge's V11 (driver) and its landing's rows the
  `off_route` pattern's, backed by that step row (0.2 #13). e26/e27, the side scenes (stage 6 only; pages 119-123, no
  store; Walk(1105,-78) ip1230 and the re-grant ip1266) -- in `avoid`, role `scene`; a loss in one is outside every
  exit: `interrupted`, absorbed by `interrupts: 1`; the re-grant runs the same step again (its row's `attempt` 2). The
  hidden e9 (-551, 2104), e11 (30, -1500) and e31 (0, 1915; upper) are published (critic #12, HarnessAgent.cs:2321-2361)
  but walk-through (SetObjectFlags(14): `coll` false, 0.2 #19), >= 1327 u off; Blank is the floor's one body. No facing
  gate (`face_gate` None everywhere), no hot-spot.
- **Calibration:** `route_to` calibrates clear of the `avoid` polygons with `key_prior(153)` (every SetControlDirection in
  153 is (248, 0): one basis); F calibrates `prior_for(153)` too (the place). Blank stands ~452 u in front of the spawn,
  so the "up" probe (~240 u plus its tail at 31 fps, ~300 u) may end inside his body disc (r 176) and be deflected: a
  one-sided "v" axis, checked against the prior, is EXPECTED in R-STAIRS's calibration record (F12), not a fault.
- **Timeouts:** `timeout_s` 20 (the walk ~2 s); `TRIGGER_WAIT_S` 2 after a walk that ended with control held, then
  `failed` (a first `failed` is re-run -- `attempts` 2 -- and O5-WALK (a) admits it, 5.3; a second is V7, driver); the
  stall watchdog does not run inside an executor.
- **Recovery from mid-walk:** a run stopped mid-walk (V7, V13) stands in 153 on FieldHUD, control held or not: the next
  run's `end_run` warps to 4600 and climbs the ladder (R-WALK-VOID proves it, F7).
- **THE PAIRED-WALK LAW** holds by construction: no story key depends on the path. Stage 6 stores nothing; the side
  scenes store nothing (0.2 #6, #8); the back door's stores make the run VOID V11 (driver). O5-WALK (b) checks that the
  walk windows wrote nothing (5.3).

### 2.5 The pre-choice guard and choice 128

#### 2.5.1 The rules
```json
[{"donor": 153, "sc": [1190], "match": "her face", "pick": "her face", "once": true, "beat": "choice128"},
 {"donor": null, "sc": null, "match": "want to skip", "pick": "default", "once": false, "beat": null}]
```
128's source `[PCHC=2,1][WDTH=...][IMME][ZDNE]` + the prompt + `[CHOO][MOVE=18,0]` + two lines: "her face" is on the
second line only, in every publication variant (prompt published or empty; a line short its first character, O1's
candle; or intact, O4's encore) -> absolute 1 through `active`; never `take: "default"` (V3 by design). The cursor opens
on 0 (0.2 #14). No `cause: "choice"` forbidden pattern in place 153 (critic #7): its backing (index other than
`selected`) would back the route's own answer and turn every run V12.

#### 2.5.2 The marker page and the quiet window
`guard.markers` ["let me pass"] (127's source; O5-KEYS pins it in block 3's US mes 127). 127 is pressed by page-once:
the first press usually lands in its opening (dropped, O4's 0.3 #1) or only finishes its [SPED=2] type-out; it is
pressed again only on a sample of GAME frame past BOTH its own hold-off and the hold-off of the driver's last press of
any kind; the press that closes it starts its tween; the quiet window opens at the first ring sample without 127 --
which can be 128's own first sample (128 is created ~2 ticks after 127 is gone and the agent publishes every 2 frames,
HarnessAgent.cs:241: at 31 fps the gap may hold no sample; O4's rehearsal read its page gone at the closing press's
own ack) -- and presses nothing until 128 is published; 128's publication closes it (rule 6 runs before rule 7, so a
sample carrying the choice never reaches rule 7). In the open window a page holding the marker is 127 itself -- the
window opened on a glitched sample (0.2 #18) -- and RE-ARMS it; any other page is V17 with an `observed` row. The cap
scans the ring for 128 first and is V13 (the instrument's) only when nothing published it within `quiet_cap_s`.

#### 2.5.3 The answer
Rule 6's readiness hold (`_choice_ready` and the snapshot unchanged for `settle_s` over live frames; 128 is `[IMME]`,
so its options are whole at readiness and the hold is O1's plain one) then `pick_for` -> (1, the rule) -> S11's
`choose_landed(1)`: `select(1)` (one Down, steered on the published cursor), Confirm, judged on the game's clock;
re-pressed only while still ready with the cursor on 1 (a Confirm in the frame between the group and `isChoiceReady` is
taken and hides nothing, 0.2 #14); rowed; the witness polled; `selected_before` 1 required (None: V17, unplaceable; a
value other than 1: V13). Bit[3795] := SYSVAR[9] at ip1741 is written in the tick 128's WindowSync returns (after its
close tween): the trace row follows the answer's down frame (O5-CHOICE (c)). Then THE BRANCH WITNESS (0.2 #20): the
first page after the answer must hold `guard.branch[0]` (141, "Let’s see", path 1) -- the game's own record of
the answer it took; `branch[1]` (129, "Hold on a sec", path 0) is V13 (the game took 0: outside input, or a cursor
move in the answer's last frame no sample showed); neither is V17 with an `observed` row.

#### 2.5.4 The stray attribution
- **The window** is [127's last listed sample, 128's close), never [128's first sample, close): a press of the driver's
  that went down after 128 opened but before the ring's earliest 128 sample lies inside it. Excluded: the answer's own
  presses (by seq: select's Down and every Confirm of `choose_landed`) and the marker page's closing press (it goes down
  on 127 by construction, S10's `guard_strays`). An unplaceable press counts by its decision frame.
- **The choice gone unanswered** (a page after it, the driver never answered): `guard_stray("choice_gone")` -- a press
  of the driver's in the window is V17 (driver); none is V13 (driver: unattributed input -- the witness reads levels
  between blocking calls and misses a short tap; the game cannot answer one side's 128 alone, S10). No `observed` row:
  VOID-ASYM (d) does not read it.
- **The guarded rule asked again** after its VERIFIED landing: `guard_stray("choice_reask")` -> V2 (game) outright --
  neither answer brings 128 back (both branches rejoin at stage 23) and no press of the driver's can; O4's `encore_stray`
  shape (V17 for a stray Confirm) does not fit 128: after a two-Confirm `choose_landed` it would read the first Confirm
  as a stray and hide a genuine re-ask as the driver's.
- **The judgment** at the first page after the answer: never armed, a stray in the window, the other branch -- each a
  driver VOID with nothing pressed (S10 (o)).
- A stray answer can never cover a run: the beat `choice128` is set only by the driver's verified answer with index 1
  (A-BEATS otherwise), and the judgment VOIDs any run whose guard row is not "ok" -- a stray costs a re-run, never a
  verdict.

#### 2.5.5 The residual
The residual first designed here cannot happen (0.2 #14): sends are serialized and acked, and 127 waits for a Confirm,
so a press decided on a 127 that is up and waiting goes down on 127. The REAL residual (the claim critique #2) is a
press page-once did not make: a rule-7 press on 126, decided on a stale or closing 126 sample and delayed past 127's
opening and type-out, goes down on 127 and closes it; 127's close-tween samples then carry a raw page-once never held
off, and a page-once press decided on one would go down after 127 is gone -- on 128 at its cursor (0) if the stall
outlasts ~2 ticks + the animation's rest + 128's opening. S10 closes it twice over: page-once's hold-off counts from
the LAST press of the driver's whatever it pressed (so that close-tween sample is never pressed), and a run whose
marker page was never pressed by page-once is V17 at the judgment. R-STAIRS and R-FULL measure the margin -- 127's last
listed sample to 128's readiness -- and every guard row's presses (F2).

#### 2.5.6 Timed and paired windows
Rule 7 presses them as pages (O3/O4's shape): the KEYON pairs take Confirms until the gate passes (<= 250 ticks, 8.3 s;
`no_progress_s` >= 60 covers it); the [TIME=20] [NFOC] windows (137, 140; 175/176 after the cut) are expected inert to
Confirm (O4 measured 150's [TIME] windows so) -- F8 records it.

#### 2.5.7 The fallback (designed, not frozen)
If F2 shows the race open with the guard (a stray inside [127's last sample, 128's close) on a guarded run), the lead
freezes instead: the rule `{donor 153, sc [1190], match "her face", pick "Let her pass" (or "et her pass" as F3
publishes it), once, take "default", beat "choice128"}` (absolute 0, the cursor's own), no `guard` (a stray then answers
the same thing) -- and with it no branch witness: an outside move of the cursor to 1 would store 1, read as CHOICE (c)'s
failure, so the fallback's scope line says so -- WRITES' ip1741 key value 0 (a same-value store 0 -> 0, emitted once:
PATTERN's visit-1 row `same` 1), CHOICE (b)-(c) on index 0, and the claim's scope line "the stored choice is the
default; a fork that stores a constant 0 passes it". It is a weaker claim (lesson 13).

### 2.6 154@304, 153@316 and the arrival in 151 (no control)
- 154@304 and 153@316 run pages and KEYON pairs only (no `Map.Bit[158]` at 304 or 316: their Main_Init tails' EnableMove
  stays behind it; Zorn e2 / e18 the defined players). Control there is V4 (game) -- at 153@316 through S13. The
  published player is whichever actor is defined (the harness publishes no identity): only Zidane ever has control.
- 151: rule 1 fires on its first poll (31244 on F). The end state is read live but for Byte[8] (151 e0 t0 ip315 writes
  125 right after the BGM-load wait, ip274-294: a race with the read; its value is the trace's last pre-cut write,
  0 at 153 e18 t1 ip890). Nothing is pressed after rule 1: 151 waits on 177 (stage 1), long before the naming (stage
  20). `end_run` then warps to 4600 from 151's FieldHUD.

### 2.7 VOID conditions (each a RouteVoid with its class, cell and attribution; the run is not covered)
| | Condition in O5 | by |
|---|---|---|
| V1 | A choice no rule matches. | game |
| V2 | The guarded rule asked again after its VERIFIED landing (S10, outright). | game |
| V4 | Control held anywhere but the cell (153, 1190) at visit 1; control after its step is done. | game |
| V5 | The stop page ("Env Play()"), nothing pressed. | driver in visit 1 (the warp's start state); game after |
| V7 | The stair step out of attempts (2) or interruptions (1). | driver |
| V10 | A naming screen, a tutorial, a battle. | game |
| V11 | Off the route or its order; a walk into e28 (the landing judge). | game; driver after a walk |
| V12 | A forbidden write the driver's own log backs. | driver |
| V13 | The budget; an instrument stop; outside input anywhere (S12); the cursor not on the pick as the answer's Confirm went down (S11: a value, not None); no choice read within `quiet_cap_s` of the quiet window's opening, the ring scanned first (S10); choice 128 gone with no press of the driver's in its window (S10); the other branch's page after the answer (S10 (o)). | driver |
| V14 | The watchdog alone. | game |
| V17 | The choice's answer not proven the driver's: it did not land, its landing went unseen, its Confirm could not be placed (S11); the marker page never pressed by page-once; a press of the driver's own in [127's last sample, 128's close) other than the answer's and the closing press (S10). GAME-OBSERVED causes, each with its `observed` row: a NON-marker page in the quiet window; a first page after the answer holding neither branch marker. Nothing is pressed after any of them. | driver |
| V19 | On F, a REAL 151, 153 or 154 (a `Field()` the chain did not retarget). A FINDING (`rerun.stop_on`). | game |

Every cell is `[place, sc, visit]` (S13: a visit-scoped table): V4 at 153@325 is `[153, 1190, 1]`, at 153@316
`[153, 1190, 3]`, at 154@304 `[154, 1190, 2]`; V19 on the arrival in a real 151 is `[151, 1190, 3]` (rule 2 runs before
the visit counts). V3, V6, V8, V9, V15, V16 and V18 cannot arise (no default-take rule, no watched cell, no wait_sc or
climb, no battle, no fight).

---

## 3. Harness additions (FakeGame only; each opt-in, modelled on the bytes, tested)

No change to `channel` or the agent; S11 is the only session change (1.2). What is missing is a fake that (a) emits
the trace as the engine's sink does and (b) plays O5's visits with the timing the driver must survive. Each choice
below cites the byte or engine line it stands for; each knob's default is the engine's, or where unmeasured the
research's estimate, named so.

### 3.1 H13 -- the sink's same-value suppression (`FakeGame.story_suppress`, default False)
With the knob, `_story_store` keys every store by the engine's SITE -- `(fld, m, src, sid, tag, ip, byte, width, bit)`,
`fld` the field id NOW (StoryTrace.cs:374-376), `m` as `_story_row` computes it -- and per site per epoch keeps
`{"same": bool, "changes": int, "n": int, "last": None, "don": <the row's don>}`: a same-value store is emitted only if
the site has emitted no SAME-VALUE row this epoch (`emit = !site.SameEmitted`, and only a same-value store sets it,
:383-387 -- a site whose first store was a change still emits its first same-value one: visit 3's ip57/ip119), a change
only while `changes < 64` (ChangeRowsPerSite, :56, :391-394), else counted (`n += 1`, `last = new`, `story_suppressed += 1`, no row,
`story_rows` unchanged -- the file stays exactly the rows the state block counts). The counts flush as `c` rows (`src
sid tag ip byte w bit n last`, the SITE's `fld`/`don`/`m`, the flush's `f`/`p`/`sc`; EmitCounts :540-557): in
`_story_stop` before the `off` row (Stop :187-205) and in `_story_start` when the trace is already on (Start's re-arm:
`Sync`, then `Resync` emits the running epoch's counts, :149-177), the site table cleared at every epoch. The `c` rows
leave in site-creation order (a Python dict; the reader never reads their order). Residue (`_warp_writes`) is never
suppressed (Diff emits every byte, :514). Not modelled: the published `suppressed` counter (`_publish` keeps 0: no
reader reads it; the knob's count is `fake.story_suppressed`). Without the knob the fake emits every store, as today.

Tests (B1): `test_fake_story_suppress_emits_the_first_same_value_per_site` (0 -> 0 twice: one row, then a `c` row n 1;
a change after it: a row; at a NEW site a change 0 -> 1 then 1 -> 1 twice: the change and the first same-value store
both rows (`same` 0, then 1), the third store counted -- ip1741's shape, the claim critique #8; 65 changes: 64 rows, one
counted; the same (sid, tag, ip) in ANOTHER field: a new site, emitted; break: key the site without `fld`, or let a
change set the same-value flag); `test_fake_story_suppress_counts_close_the_epoch` (`storytrace 0` writes
the `c` rows before `off`; a second `storytrace 1` writes them before its `arm`; each `c` row's fld/don are its site's;
`storytrace(False)` returns: the file's line count equals the published `rows`); `test_fake_story_suppress_is_off_by_
default` (every store a row, no `c` row: today's).

### 3.2 H14 -- the scripted visit (`{"visit": knobs}`, a machine beat)
A `_VisitBeat(_Machine)` runs ONE field visit from its arrival to its `Field()` as a STEP LIST, per field tick, with
O4's window model unchanged (the opening drop, the close tween, the per-frame UI Confirm, the per-tick KEYON edge:
`_Win`, `_Machine.frame`/`ui`). `_next_beat`'s dispatch gains `"visit"` (its one-line change re-baselined by
name, G21) and `_start_machine` picks `_VisitBeat` for it. `_VisitBeat` overrides `publish` (a subclass method:
`_Machine.publish`, a G21 pin, is not edited) to keep the menu group `""` once a choice of the visit has closed --
the engine's DisableAllGroup at the answering Confirm (Dialog.cs:629, ButtonGroupState.cs:291) -- where `_Machine`
publishes None. A scene of four visit beats plays O5's route; each visit ends by moving the field (a fresh visit:
`fake._visit += 1`, as H11's stage 9) and finishing, so the next beat starts in the new field. Knobs (`_machine_knobs`,
strict): `steps` (required), `field_to` map, `donor` (the visit's `fake.donor`: on F the member's donor, DataPatchers'
EffectiveFieldId; None on S), `close_s` 0.09 / `close_frames` 1, `open_s` 0.105 / `open_frames` 2 (O4's),
`ready_lag_frames` 1 (a choice's frame between its group and `isChoiceReady`, Dialog.cs:161-164), `wait_scale` 1.0
(scripted waits only; the tests run 0.25), `publish_order` "agent_first", `bodies` (the visit's published objects as
`fake.blockers` dicts: 3.4), and H15's faults. `fake.visit_log` keeps every step's start tick and frame.

The step vocabulary (each a dict; every number in O5's builder, 3.4, cites its bytes):
| Step | Meaning (engine) |
|---|---|
| `{"store": [sid, tag, ip, byte, width, value, bit]}` | `fake.script_store` (a script store; H13 decides its row); `value` `"answer"` stores the last choice's answer (ip1741 `SYSVAR[9]`) |
| `{"wait": ticks}` | the script's op_22 / walks, scaled by `wait_scale` |
| `{"place": [x, z]}` | a scripted move of the player (no control): the position published |
| `{"page": mes, "slot": n, "typing_s": s}` | a WindowSync, or WindowAsync + WaitWindow: listed this tick (ETb.NewMesWin), complete after its opening, a Confirm while `typing_s` runs only completes the text (Dialog.cs:798-808), the next closes it; the script resumes the tick it is gone |
| `{"timed": mes, "slot": n, "ticks": t}` | a [TIME=t] window: Confirm-inert, closes itself `t` ticks after it opened (then its tween); the script does not wait |
| `{"pair": [[mes, slot], [mes, slot]], "lag": t, "gate": t}` | H10's KEYON pair: b `lag` ticks after a, the gate `gate` ticks after b, the first Confirm/Special EDGE closes both |
| `{"choice": mes, "slot": n, "header": s, "lines": [...], "typing_s": s, "gap": t, "stale": k, "branch": {"0": [...], "1": [...]}}` | `gap` ticks after the previous window is GONE (default 2, the knob 1-10: 0.2 #14 -- e31's WaitAnimation rest, e2's stage tick, e3's open), a WindowSync choice, SelectChoice GATED by its state as the engine gates it: its opening (`open_s`; `selected` published `stale`, the pooled window's last, group `""`; Down/Up do nothing; a Confirm sets SelectChoice to the default and closes nothing, Dialog.cs:798-801); then, with `typing_s` 0 (`[IMME]`, 128's), complete at once -- group `Dialog.Choice`, the cursor on 0 (ETb.cs:100-103) -- a Confirm in its first `ready_lag_frames` committed and nothing hidden (:787-789); after that Down/Up move the cursor (OnItemSelect, only in CompleteAnimation, :826-835) and Confirm answers at it; with `typing_s` > 0 (a typed prompt, not 128) a Confirm while it types only completes the text (:803-807); then its close tween (group `""`, kept after); the answer kept; the branch's steps run |
| `{"grant": [x, z]}` | EnableMove: `fake.control = True` with the player at (x, z) |
| `{"stairs": knobs}` | stage 6 + the side scenes + the back door + stage 17 (below) |
| `{"field": to}` | Field(): the field becomes `field_to[to]` (a fresh visit, control off), the beat finishes |

**The stairs step** (153 e3 t1 stage 6 and its neighbours), per field tick while control is held: (1) the regions'
tag 2 tests in entry order -- `scenes` (153.e26: its quad AND z > 1333 -- the ground half of `f[1] > -100` is the
floor-blind fake's ground; 153.e27: its quad), each live only in stage 6 (`Map.Byte[24] == 6`): the first hit takes
control (DisableMove ip88/ip68), lists the side scene's pages (`scene_pages`, rule 7's), then `{"place": regrant_at}`
(Walk(1105,-78) ip1230) and the re-grant (ip1266), back to stage 6; `back_door` (153.e28: its quad, any stage):
control off, its stores (e28 t2 ip38 `Byte[8] := 25`, ip227 `Int16[2] := 5`), then after `exit_ticks` the field
becomes `back_door_to` and the beat finishes; (2) THE HEIGHT TEST (ip859) -- `height_at(x, z)` (a callable: the real
mesh's interpolated tri height, PSX y) when given, else the `contour` polygon (the floor-blind stand-in): the first tick
he stands at PSX y <= -450 (or inside `contour`) takes control (ip874-915); `teleport_ticks` (3: the stage switch, op_1C,
Wait(1), the Bit[160] test -- an ESTIMATE, R-STAIRS measures) later the player is placed at `teleport` (-1165, 856)
(CreateObject ip1466), then walked along `climb` [(-1419,602), (-1602,298), (-1631,10), (-1631,-140), (-1416,-378),
(-978,-554), (-329,-624)] at `climb_speed` 37 u a tick (SetWalkSpeed(37)); then the next step. With `height_at` the
fake publishes `player[1] = -height` (the published y; the spawn's ~1, the contour's 450).

### 3.3 H15 -- fault knobs (each absent by default)
`store_override` ({ip: value}: a fork that stores another value at a site -- ip1741 0, "a fork that stores a
constant"); `grant_at` ({visit index: [x, z]}: control granted in a visit the bytes never grant -- 154@304, 153@316);
`land_real` (the `field` step lands in the REAL id: a Field() the chain did not retarget, V19's case); `reask` (128
asked again after its answer); `stray_confirm_at_ready` (the fake itself answers 128 at its readiness -- an input the
witness did not see); `cursor_to` ({after_frames: n, index}: the cursor moved by the game n frames after the driver's
select -- outside input's stand-in; `{"at_confirm": true, "index": 0}` moves it in the frame the answer's Confirm goes
down, after every published sample -- the move `selected_before` cannot see, the branch witness's case);
`confirm_deaf` (the choice ignores its first k Confirms); `gap_ticks` override (127 gone -> 128 listed; 1-10 the
measured range, a huge one the quiet cap's case); `no_contour` (the height test never fires); `side_scene_at` (tick n
of stage 6: a side scene fires wherever he stands -- a mis-walk's stand-in); `error_window` ({visit index: 2}: Byte[13]
arrived 2 at that visit: the prologue takes ip97 and lists window 56 "Env Play()": the stop page's case, visit 1's or
visit 3's). Test-side, not knobs: a driver stall (a wrapped `g.press` that sleeps before sending), a stale read (a
wrapped `Session.state` returning the previous document once), a READ stall, the dialog-section catch (a wrapped
`Session.state` returning one document whose `dialog` is the agent's catch shape, HarnessAgent.cs:1701, its `menu`
untouched), the engine's clock (the fake on `publish=("mtime",)`: no `rt`), a stub witness.

Tests (B1; each names its break): `test_fake_visit_pages_open_type_and_close` (a Confirm in the opening dropped, one in
the type-out completes the text, the next closes it, WindowSync resumes after the tween; break: `open_s` 0);
`test_fake_visit_choice_opens_after_its_gap_on_cursor_zero` (127 gone -> 128 listed `gap` ticks later, for `gap` 1 and
10; with `typing_s` 0: a Confirm in its opening changes nothing but SelectChoice (the default) and closes nothing, a
Down there moves nothing; one in its ready-lag frame is taken and hides nothing; the next answers at the cursor (0
unless moved); the group `""` after its close; the ip1741 store carries the answer; branch 0's and branch 1's first
pages; break: open 128 beside a closing 127, or give 128 a type-out);
`test_fake_visit_objects_as_the_agent_publishes_them` (153@325's bodies: Blank sid 7 at (1068, 373) `coll` true,
`solid` false, `r` 176, `talk_r` 377, `range_r` null; e9/e11/e31 `coll` false, `shown` false; the player never in the
list; a walk into Blank's disc is pushed out, one through e9's is not; break: publish Blank walk-through); `test_fake_visit_grant_and_
the_stair_contour` (the grant at the spawn; the contour takes control the tick he crosses it; the teleport
`teleport_ticks` later; x <= -1100 for >= 40 ticks after the loss; with `height_at` the published y; break: teleport in
the loss tick); `test_fake_visit_side_scene_and_regrant` (a side scene's pages, the re-grant at the spawn, stage 6
resumed; break: re-grant before the pages close); `test_fake_visit_back_door_stores_then_leaves` (e28's two stores,
then the field change; break: leave first); `test_fake_visit_keyon_pairs_and_timed_windows` (an edge before the gate
lost, one after closes both; a [TIME=20] window ignores Confirm and closes itself); `test_fake_visit_faults` (one
assertion per H15 knob); `test_fake_visit_sets_the_members_donor` (F rows' `don` the donor: no A-MISMATCH).

### 3.4 The O5 route builder (test-side `_o5_route(side, fields, **knobs)`)
Four visit beats from the bytes (`stages153.out`, `stages154.out`, `win_*.txt`; slots as the scripts open them). Window
TEXTS are placeholders (`"153 mes 113"`, raw `"[STRT=0,0]153 mes 113"`), each distinct, except where the driver
matches: 127 holds "let me pass", 128's lines are "Let her pass" / "Examine her face" (a knob for the first-character
variant), 141's raw holds "Let’s see" and 129's "Hold on a sec" (the branch markers), window 56 holds "Env Play()".
153@325's `bodies` (0.2 #19): Blank `{"sid": 7, "uid": 7, "x": 1068, "z": 373, "r": 176, "coll": true, "solid": false,
"talk_r": 377, "shown": true}`, e9/e11/e31 at (-551, 2104), (30, -1500), (0, 1915) `coll` false, `shown` false.
Fixture fields: S 30820 ("153"), 30821 ("154"), 30810 ("151") -- the
`game` fixture registers these three -- and 30830 ("150", the back door); F 31245, 31246, 31244, 31243. A test-side
`_o5_register(game)` (`_o4_register`'s shape: FieldScene lines appended to the fixture's own
`FF9CustomMap/DictionaryPatch.txt`) registers 30830 and the four F ids under `_O5_NAMES`
({"31243": "O5_HALL", "31244": "O5_SEAT", "31245": "O5_H2F", "31246": "O5_ENT"}); the `game` fixture itself is not
edited. Members {31245: 30820, 31246: 30821, 31244: 30810, 31243: 30830}.
- **153@325:** stores e0 t0 ip22, 49, 57, 119, 138, 200 (Bit[191] 0, Bit[184] 0, Int16[9] -1, Byte[13] 0, Int16[11] -1,
  Byte[14] 0); wait 10; place (1105, -78); pages 113 (slot 1), 114 (1), 115 (0), 116 (1), 117 (1); grant (1105, -78);
  stairs; wait 10 (ip1658); page 126 (0, typing 0.3 s); page 127 (2, typing 0.5 s: [SPED=2], an ESTIMATE); choice 128
  (slot 0, gap 2 -- 1-10 by knob --, typing 0: [IMME]) then store e3 t1 ip1741 `Bit[3795] := answer`; branch "1": pages 141 (0),
  142 (2), 143 (0), 144 (0), 145 (2), 146 (0), 147 (2), 148 (0), 149 (2), 150 (0), 130 (0); branch "0": pages 129 (0),
  130 (0); page 131 (2); 132 (0); 133 (0); pair [[134, 7], [135, 1]] lag 20 gate 40; page 136 (2); timed 137 (2, 20);
  wait 35; pair [[139, 0], [138, 1]] lag 5 gate 40; timed 140 (1, 20); wait 40; store e3 t1 ip2953 `Byte[8] := 0`; wait
  65; store e3 t1 ip3150 `Int16[2] := 304`; field "154".
- **154@304:** stores e0 t0 ip26, 53, 61, 123, 142, 204; wait 10 (RunSoundCode + the SYSVAR[3] wait); store ip279
  `Byte[8] := 125`; wait 20; pair [[151, 2], [152, 3]]; page 153 (2); page 154 (3); pair [[155, 2], [156, 3]]; wait 60;
  pair [[157, 2], [158, 3]]; wait 35; store e2 t1 ip1520 `Int16[2] := 316`; field "153".
- **153@316:** stores e0 t0 ip22, 49, 57, 119, 138, 200; wait 20; pages 159 (6), 160 (5), 161 (6), 162 (5), 163 (6), 164
  (5); pair [[165, 5], [166, 6]]; wait 60; pages 167 (5), 168 (6), 169 (5), 170 (6), 171 (5), 172 (6); pair [[173, 5],
  [174, 6]]; store e18 t1 ip890 `Byte[8] := 0`; wait 65; store e18 t1 ip1077 `Int16[2] := 110`; field "151".
- **151@110:** stores e0 t0 ip22, 49, 57, 119, 138, 200; wait 10 (the BGM-load wait); store ip315 `Byte[8] := 125`; timed
  175 (4, 20); timed 176 (5, 20); page 177 (an end the driver never presses).
The stores are the predictions' sites (C1's `test_o5_hallway_route_builder_matches_the_keys` compares the builder's
store list with the draft's writes, chain, masked and start rows, and the builder's trace under `story_suppress` with
the draft's `pattern`: one source of truth).

---

## 4. Predictions (draft v1: `O5Segment.draft()`)

### 4.1 Top level
```json
{"version": 1,
 "what": "O5: 153@1190 (warp, entrance 325; EVT_ALEX1_AC_H2F) -> the stairs -> choice 128 'Examine her face' -> 154@304 (EVT_ALEX1_AC_ENT_2F) -> 153@316 -> Field(151) (EVT_ALEX1_AC_SEAT_R), SC 1190; stock vs the alxc disc-1 chain as O4 deployed it (route members 31244-31246; PLAN.md, O5) -- a US session",
 "rehearsals": [],
 "order": ["S", "F", "S", "F", "S", "F"], "min_covered": 2, "rerun": {"max": 2, "stop_on": ["V19"]},
 "budget": {"run_s": 600, "run_min_s": 300, "session_s": 3600, "settle_s": 1.0, "no_progress_s": 60, "end_row_s": 10.0},
 "start": {"S": 153, "F": 31245}, "entrance": 325, "scenario": 1190, "lang": "us",
 "end_field": 151, "end_fields": [151], "side_ends": {"S": [151], "F": [31244]},
 "route": [153, 154], "visits": [153, 154, 153], "stock_fields": [151, 153, 154],
 "members": {"31240": 64, "...": "...", "31259": 167}, "names": {"31240": "O4_AC_AST", "...": "..."},
 "text_block": 3, "text_blocks": [3], "recovery": 4600, "cut_start": true,
 "start_first": "4.6", "start_music": "4.6", "start_residue": [[0, 0, 166], [1, 0, 4], [2, 0, 69], [3, 0, 1]],
 "residue_after_start": [], "sc_bytes": [0, 1], "ladder": [], "entrance_bytes": [2, 3], "chain": "4.3",
 "writes": "4.4", "error_path": "4.5", "forbidden_sites": "4.5", "dead": "4.5", "inert": "4.5",
 "start_dependent": [], "noise": [], "forbidden": "4.8", "landing": "5.3", "choice": "5.3", "walk": "5.3",
 "end_state": "4.9", "battles": [], "stop_pages": ["2.1"], "regions": "4.15", "hotspots": {}, "table": ["2.4"],
 "steps_default": "4.15", "choices": ["2.5.1"], "naming": [], "beats": ["stairs", "choice128"],
 "guard": "4.10", "witness": "4.10", "route_pins": "4.14", "pattern": "4.16",
 "settings": "4.13", "override70": "4.13", "derived": "4.13", "engine": "4.13"}
```
- `members`/`names` are O4's twenty (`chain_from_campaign` on O4's `campaign.toml`, exactly O4's donors);
  `route_members` over 153, 154, 151 derives 31245, 31246, 31244 (printed by `--offline-check`, never assumed).
  P-DEPLOY, P-EB, P-FLOOR and the fingerprint read all twenty.
- `start_residue`: SC 1190 = 0x04A6 writes bytes 0 (0 -> 166) and 1 (0 -> 4); FieldEntrance 325 = 0x0145 writes bytes 2
  (0 -> 69) AND 3 (0 -> 1): FOUR rows (StoryTrace.cs Diff per byte, :514-527; O2-O4 had three).
- `start_dependent: []`: no key's VALUE depends on the start (constants and the pick); the ROW PATTERN does (4.16, 5.4).
- `ladder: []` with `sc_bytes`: O5-NO-SC is O3's `no_sc_check` (O2's LADDER on an empty ladder could not fail).

### 4.2 No SC rung
No `Global.UInt16[0]` store in 151 or 153-154 (the census, 6.1); the reads 153 e0 t0 ip232 (`SC > 1900`: false) and 151
e0 t0 ip461 (`< 12000`, after the cut) take the same branch from the raw warp and from a true O4 end (both 1190).

### 4.3 The FieldEntrance chain (`Global.Int16[2]`; O5-CHAIN; the first `old` is 325, the warp's entrance)
| # | donor | sid | tag | ip | off | value | what |
|---|---|---|---|---|---|---|---|
| 1 | 153 | 3 | 1 | 3150 | 2742 | 304 | stage 30, then `Field(154)` ip3158 |
| 2 | 154 | 2 | 1 | 1520 | 1409 | 316 | stage 6, then `Field(153)` ip1528 |
| 3 | 153 | 18 | 1 | 1077 | 953 | 110 | stage 114 (visit 3), then `Field(151)` ip1085 |

### 4.4 Registered writes (O5-WRITES: every covered run's keys are EXACTLY these and the chain)
| donor | sid | tag | ip | off | target | value | op | what |
|---|---|---|---|---|---|---|---|---|
| 153 | 0 | 0 | 57 | 51 | Int16[9] | -1 | := | ambient (visit 1 from 643; visit 3 emitted same) |
| 153 | 0 | 0 | 119 | 113 | Byte[13] | 0 | := | ambient (visit 1 from 1: `start_music`; visit 3 emitted same) |
| 153 | 0 | 0 | 138 | 132 | Int16[11] | -1 | := | ambient (visit 3 suppressed) |
| 153 | 0 | 0 | 200 | 194 | Byte[14] | 0 | := | ambient (visit 3 suppressed) |
| 153 | 3 | 1 | 1741 | 1333 | Bit[3795] | 1 | :=var, rvalue `B_SYSVAR[9]` | **THE STORED CHOICE** (0 -> 1) |
| 153 | 3 | 1 | 2953 | 2545 | Byte[8] | 0 | := | stage 30 (old 125 after the raw warp) |
| 154 | 0 | 0 | 61 | 51 | Int16[9] | -1 | := | ambient |
| 154 | 0 | 0 | 123 | 113 | Byte[13] | 0 | := | ambient |
| 154 | 0 | 0 | 142 | 132 | Int16[11] | -1 | := | ambient |
| 154 | 0 | 0 | 204 | 194 | Byte[14] | 0 | := | ambient |
| 154 | 0 | 0 | 279 | 269 | Byte[8] | 125 | := | the 304 branch, after the sound wait |
| 153 | 18 | 1 | 890 | 766 | Byte[8] | 0 | := | stage 114 (visit 3) |

12 writes + 3 chain = **15 keys a run**, beside the masked prologue rows (Bit[191] ip22/ip26, Bit[184] ip49/ip53:
`boot_scratch`, `field_menu_guard`). The `:=var` key's value 1 rests on O5-CHOICE (the driver's verified pick), never
computed here (O4's score key shape: O4-KEYS reads its `rvalue` in the statement `Global.Bit[3795] B_SYSVAR[9] B_LET`).
EXACT for O4's reason: the key set is small and fully enumerated by the bytes (O5-CENSUS classifies every store site of
153 and 154; O5-KEYS proves every listed site). R-FULL must show the exact set before the freeze (F4).

### 4.5 The error path, the forbidden sites, the dead sites, the inert functions (registered; never expected)
- `error_path` (an incoming Byte[13]/[14] of 2 or 9): 153 e0 t0 ip97/91 `Byte[13] := 9`, ip178/172 `Byte[14] := 9`,
  ip2314/2308 `Byte[13] := 0`, ip2348/2342 `Byte[14] := 0` (window 56's resets); 154 e0 t0 ip101/91, ip182/172,
  ip497/487, ip531/521 (the same four). A 153 row at visit 1 is the start's fault (A-START, V5 driver); later, a fork
  deviation.
- `forbidden_sites`: 153 e28 t2 ip38/8 `Byte[8] := 25`, ip227/197 `Int16[2] := 5` (the back door; 0.2 #13).
- `dead` (each `:=`; why false on the route): 153 e0 t0 ip41/35 `Int16[2] := 10000` (behind `Bit[184] == 1`), ip130/124
  `Byte[13] := 1` and ip211/205 `Byte[14] := 1` (the else of `Int16[9] < 0` / `Int16[11] < 0`, just set -1), ip243/237
  `Int16[2] := 3` (behind ip232 `SC > 1900`), ip1188/1182 and ip1260/1254 `Byte[8] := 125` (the default entrance's
  branch, L1098); 153 e3 t1 ip3168/2760 `Byte[8] := 0` and ip3288/2880 `Int16[2] := 0` (the flashback: ip2942
  `Int16[2] != 3` false only at entrance 3); 154 e0 t0 ip45/35, ip134/124, ip215/205 (the same three shapes).
- `inert` (FUNCTION-level, proven by `instanced_at` at EVERY route entrance of the field, 6.1): `{"donor": 153, "sid":
  s, "tags": "*"}` for s in 23, 24, 25, 32 (instanced at 328 and the default only) and `{"donor": 153, "sid": 15, "tags":
  "*", "shared_by": [32]}` (a shared entry: proven by its callers, 6.1); `{"donor": 154, "sid": s, "tags": "*"}` for s
  in 5, 8, 9, 10 (instanced at 315 / the default only).

### 4.6 The start (O5-START)
```json
"start_first": {"donor": 153, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 22, "off": 16, "target": "Global.Bit[191]",
                "value": 0, "op": ":=", "what": "153's Main_Init: its first store (emitted same: a new site)"},
"start_music": {"donor": 153, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 119, "off": 113, "target": "Global.Byte[13]",
                "value": 0, "op": ":=", "old": 1,
                "what": "153's ambient branch from the warp's Byte[13] 1 (field 70's prologue :=1 at ip130; the warp leaves 70 before ip475's :=2)"}
```
The warp window and `old: 1` are O2-O4's (fifteen runs measured the same start), under the override P-OVERRIDE pins
(critic #8). A 2 would take ip97 and window 56: A-START.

### 4.7 Noise: none
No `SYSVAR[0]` read in 151/153/154; no battle, no ATE; the walk's path writes nothing (2.4); the choice's value is the
frozen pick. `noise: []`: NULL and STABLE set nothing aside.

### 4.8 Forbidden
```json
[{"off_route": true, "cause": "walk",
  "why": "a write off the route: S, a place outside [153, 154] + [151]; F, a field that is neither a member whose donor is on the route nor F's own end field (real 151/153/154 on F: an un-retargeted Field() or an engine id leak; 150/31243 after the back door, backed by its V11 step row)"}]
```
No back-door pattern (0.2 #13), no `cause: "choice"` pattern (critic #7).

### 4.9 End state (read live on arrival in 151 / member(151); O5-STATE (b))
```json
{"Global.UInt16[0]": 1190, "Global.Int16[2]": 110, "Global.Bit[3795]": 1,
 "Global.Byte[13]": 0, "Global.Byte[14]": 0, "Global.Int16[9]": -1, "Global.Int16[11]": -1,
 "Global.Bit[191]": 0, "Global.Bit[184]": 0,
 "Global.Byte[6]": 0, "Global.UInt16[19]": 0, "Global.UInt16[21]": 0, "Global.Byte[303]": 0, "Global.Byte[4]": 0,
 "Global.Byte[17]": 0, "Global.Byte[18]": 0, "Global.Byte[475]": 0, "Global.Bit[3815]": 0, "Global.Bit[3793]": 0,
 "Global.Bit[3717]": 0, "Global.Bit[3718]": 0, "Global.Int16[469]": 0, "Global.Byte[472]": 0, "Global.Byte[206]": 0}
```
Nine the route leaves, fifteen untouched since New Game. Byte[8] is NOT here (critic #4: 151 ip315 races the read);
its end value is the last pre-cut write in every covered run's trace (153 e18 t1 ip890 := 0), FROZEN by O5-PATTERN
(b): Byte[8]'s three rows -- 153 e3 t1 ip2953 := 0 (visit 1), 154 e0 t0 ip279 := 125 (visit 2), 153 e18 t1 ip890 := 0
(visit 3, the last row on Byte[8] before the cut) -- are entries of their visits' frozen sequences (4.16), so a run
whose Byte[8] history differs from the frozen one fails by value, whatever the other runs did (STATE (a) compares runs
with run 0 only, o2_alexandria.py:1469-1484: it alone could not see a symmetric deviation; the claim critique #10).
Bit[3855]/Bit[3854] (153@328's) are not here either.
Stable through 151's arrival: its prologue rewrites equal values (0.2 #2), and nothing else stores before page 177.

### 4.10 The guard and the witness (S10, S12; F2, F6 and F9 re-size them)
```json
"guard": {"donor": 153, "sc": 1190, "markers": ["let me pass"], "choice": "her face",
          "branch": ["Let’s see", "Hold on a sec"], "page_once_ticks": 10, "quiet_cap_s": 4.0,
          "why": "153 e31 t1 ip663 WindowSync(2,128,127) -> ip669 WaitAnimation (RunAnimation(3387) ip648) -> ip670 Map.Bit[231] := 1 -> e2 t1 Map.Byte[24] := 20 (the next tick) -> e3 t1 ip1724 WindowSync(0,128,128) [IMME], ~2 ticks after 127 is gone plus the animation's rest: a Confirm decided on a stale or closing 127 can land on 128 at its cursor (0); 128's answer -> Map.Byte[27] (ip1749) -> e2 t1 ip844: 141 (path 1, the pick) or 129 (path 0) first"},
"witness": {"input_every_s": 0.05, "why": "Bit[3795] stores the player's answer: outside input at the choice would store another value while the driver logs its pick (critic #10)"}
```

### 4.11 Coverage beats
`stairs`: set by the stair step's `done`. `choice128`: set by the guarded rule's VERIFIED answer (S11). Plus `end ==
"reached"`. O5-WALK and O5-CHOICE re-read both from the rows.

### 4.12 Budget and recovery
Estimated ~4.7 min a run (the research: ~37 pages with pick 1, 7 KEYON pairs, 2 timed windows, 1 walk, the scripted
waits; ~4 s a page, calibrated on O4's 150). Drafts: `run_s` 600, `run_min_s` 300, `session_s` 3600, `settle_s` 1.0,
`no_progress_s` 60 (a pair's gate is <= 8.3 s), `end_row_s` 10; the guard's `quiet_cap_s` 4.0 (the gap measured: F6).
F6 replaces every one.
Recovery is `end_run` (O4's): the warp to 4600 first (from 153 mid-walk, from a page, from 154, from 151 -- all FieldHUD),
then the ladder; the session ENDS through `end_run` (`end_session_warps`). F7 proves it from mid-walk.

### 4.13 Settings, the New-Game override, the engine, the derived facts
O4's frozen values, unchanged: `settings` (28 keys: [Battle], [Cheats], [Hacks] incl. `DisableNameChoice` 0, [Control]
incl. `AlwaysCaptureGamepad` 1 and `SwapConfirmCancel` 0, [Graphics] `FieldTPS` 30), `override70` {FF9CustomMap-world:
2ce8887e...}, `engine` {x64, x86: ba976242...}, `derived` (cfg.control 0, 30 ticks a second). `freeze` refuses an
engine that is not the live DLLs'.

### 4.14 The route pins (O5-KEYS (b): the bytes the driver, the guard and the FakeGame rest on)
`route_pins`, each `[donor, sid, tag, ip, eb-src text]`, compared EXACTLY with the stock US script's instruction text:
| what | site | text |
|---|---|---|
| the dispatch | 153 e0 t0 ip255 | `SWITCHEX(L1098, 325, L273, 5, L438, 328, L603, 316, L799, 3, L951)` |
| the SC read | 153 e0 t0 ip232 | `SET({Global.UInt16[0] const(1900) B_GT B_EXPR_END})` |
| the regions at 325 | 153 e0 t0 ip302, 305, 308 | `InitRegion(26, 0)`, `InitRegion(27, 0)`, `InitRegion(28, 0)` |
| the grant | 153 e3 t1 ip752, 755, 785 | `WaitWindow(1)`, `SET({Map.Bit[158] const(1) B_LET B_EXPR_END})`, `EnableMove()` |
| the height test | 153 e3 t1 ip859 | `SET({obj(uid=255).f[1] const(65086) B_GT B_EXPR_END})` |
| the loss | 153 e3 t1 ip874, 893 | `SET({Map.Bit[158] const(0) B_LET B_EXPR_END})`, `DisableMove()` |
| the teleport | 153 e3 t1 ip1466 | `CreateObject(64371, 856)` |
| 127 | 153 e31 t1 ip663, 670 | `WindowSync(2, 128, 127)`, `SET({Map.Bit[231] const(1) B_LET B_EXPR_END})` |
| the gap's animation | 153 e31 t1 ip648, 669 | `RunAnimation(3387)`, `WaitAnimation()` |
| 128 | 153 e3 t1 ip1713, 1724 | `SET({Global.Int16[2] const(3) B_NE B_EXPR_END})`, `WindowSync(0, 128, 128)` |
| the stored answer | 153 e3 t1 ip1741, 1749 | `SET({Global.Bit[3795] B_SYSVAR[9] B_LET B_EXPR_END})`, `SET({Map.Byte[27] B_SYSVAR[9] B_LET B_EXPR_END})` |
| the branch | 153 e2 t1 ip840, 844 | `SET({Map.Byte[27] B_EXPR_END})`, `SWITCH(0, L865, L843, L854)` |
| the branch pages | 153 e3 t1 ip1899, 3430 | `WindowAsync(0, 128, 129)`, `WindowAsync(0, 128, 141)` |
| the pairs | 153 e3 t1 ip2336, 2711; 154 e2 t1 ip215, 392, 1265; 153 e18 t1 ip444; e20 t1 ip883 | `SET({const4(131072) B_KEYON B_NOT const4(524288) B_KEYON B_NOT B_ANDAND B_EXPR_END})` |
| the VIB ops (s62) | 153 e3 t1 ip2443, 2448, 2453 | `RunVibrationTrack(0, 0, 1)`, `RunVibrationTrack(0, 1, 0)`, `ActivateVibration(1)` |
| e26 | 153 e26 t2 ip38, 58, 88, 110 | the ground/z test (0.2 #8), `SET({Map.Byte[24] const(6) B_EQ B_EXPR_END})`, `DisableMove()`, `SET({Map.Byte[24] const(7) B_LET B_EXPR_END})` |
| e27 | 153 e27 t2 ip38, 68, 90 | `SET({Map.Byte[24] const(6) B_EQ B_EXPR_END})`, `DisableMove()`, `SET({Map.Byte[24] const(14) B_LET B_EXPR_END})` |
| e28 | 153 e28 t2 ip30, 38, 83, 227, 235 | `SET({B_SYSVAR[2] B_EXPR_END})`, `SET({Global.Byte[8] const(25) B_LET B_EXPR_END})`, `ExitField()`, `SET({Global.Int16[2] const(5) B_LET B_EXPR_END})`, `Field(150)` |
| the exits | 153 e3 t1 ip3158; 154 e2 t1 ip1528; 153 e18 t1 ip1085 | `Field(154)`; `Field(153)`; `Field(151)` |
| 154's dispatch | 154 e0 t0 ip234 | `SWITCH(304, L392, L232)` |
| the end row and the race | 151 e0 t0 ip22, 232, 315 | `SET({Global.Bit[191] const(0) B_LET B_EXPR_END})`, `SET({Global.Int16[2] const(110) B_EQ B_EXPR_END})`, `SET({Global.Byte[8] const(125) B_LET B_EXPR_END})` |

Plus `route_mes` (block 3, US, the asset the engine reads): mes 127's source holds every `guard.markers` string and no
`[TIME=` (only a Confirm closes it: 2.5.5); mes 128's `[CHOO]` lines hold "her face" in exactly one line (the second),
its source opens `[PCHC=2,1]` and holds `[IMME]` (no type-out: 0.2 #14); mes 141's source holds `guard.branch[0]` and
mes 129's `guard.branch[1]`, neither holding the other's; mes 56 holds "Env Play()". The guard, the rule, the branch
witness and the stop page can then never drift from what the game shows. 53 instruction pins in all.

### 4.15 The regions, the table's defaults
```json
"regions": {
 "153.e28": {"points": [[2850, 347], [2850, -13], [1739, -74], [1739, 406]], "role": "exit", "to": 150, "entrance": 5, "face_gate": null},
 "153.e26": {"points": [[-227, 3000], [200, 3000], [212, 935], [-264, 924]], "role": "scene", "stage": 6,
             "why": "side scene A: tag 2 on the ground and z > 1333 at stage 6, Map.Byte[24] := 7; no global store; re-grant e3 t1 ip1266"},
 "153.e27": {"points": [[-777, -2348], [777, -2348], [777, -900], [-777, -900]], "role": "scene", "stage": 6, "why": "side scene B: Map.Byte[24] := 14"},
 "153.e23": {"points": [[-227, 3000], [200, 3000], [212, 935], [-264, 924]], "role": "dormant", "entrances": [325, 316]},
 "153.e24": {"points": [[2850, 347], [2850, -13], [1739, -74], [1739, 406]], "role": "dormant", "entrances": [325, 316]},
 "153.e25": {"points": [[-777, -2348], [777, -2348], [777, -900], [-777, -900]], "role": "dormant", "entrances": [325, 316]},
 "154.e8": {"points": [[2222, -5555], [-2222, -5555], [-2222, -4080], [2222, -4080]], "role": "dormant", "entrances": [304]},
 "154.e9": {"points": [[-3777, -999], [-3777, -3111], [-1888, -3111], [-1888, -999]], "role": "dormant", "entrances": [304]},
 "154.e10": {"points": [[3777, -999], [3777, -3111], [1888, -3111], [1888, -999]], "role": "dormant", "entrances": [304]}}
```
e23/e24/e25 are e26/e28/e27's twin quads: registered `exit`, they would mislabel a side-scene loss as a door (the
research's dispute 13). `steps_default` is O2's exactly (`attempts` 2, `interrupts` 1, `timeout_s` 20, `tolerance` 45,
`exit_slack` 40, `exit_wait_s` 5.0, `npcs` true, `overlay_ok` false, `immediate` false, `settle` null, `lunge_ticks` 0,
`min_depth` 40, `confirm_s` 4.0, `climb` O2's).

### 4.16 The emitted row pattern (the suppression model's prediction; F4 measures it; O5-PATTERN judges it EXACTLY)
`pattern` = `{"visits": [[[place, sid, tag, off, target, new, same], ...] per visit], "counts": [[place, sid, tag, off,
target, n, last], ...]}`, read by O5-PATTERN (5.3; the claim critique #1) and by LANDING (b)'s re-entry row; the
report prints it:
| visit | emitted `w` rows (in order) | suppressed (counted) |
|---|---|---|
| 153@325 | e0 t0 ip22 (masked, same), ip49 (masked, same), ip57 (643 -> -1), ip119 (1 -> 0), ip138 (same), ip200 (same); e3 t1 ip1741 (0 -> 1), ip2953 (125 -> 0), ip3150 (325 -> 304) | none |
| 154@304 | e0 t0 ip26 (masked), ip53 (masked), ip61, ip123, ip142, ip204 (all same), ip279 (0 -> 125); e2 t1 ip1520 (304 -> 316) | none |
| 153@316 | e0 t0 ip57 (same: the visit's FIRST emitted row), ip119 (same); e18 t1 ip890 (125 -> 0), ip1077 (316 -> 110) | e0 t0 ip22, ip49, ip138, ip200 |
| 151@110 | e0 t0 ip22 (THE CUT) | -- |
The epoch's close: four `c` rows of place 153 (n 1 each; ip138 last -1, ip200 last 0), kept by the cut. Totals before
the cut: 21 `w` rows (17 unmasked), 4 `c` rows. Each `c` row's `last` is a key some emitted row of the run carries, so
STATE (a)'s suppressed set holds no key beyond them (o2_alexandria.py `suppressed`) -- and so STATE cannot judge them:
`suppressed()` drops a count whose `last` an emitted key carries (:1449-1460) and the digest folds it into that key
(storytrace.py:815-824). O5-PATTERN (a) does. As frozen (offsets from the join, 0.2 #4; `same` 1 a same-value store):
- `visits[0]` (153@325): (153, 0, 0, 16, Bit[191], 0, 1), (153, 0, 0, 43, Bit[184], 0, 1), (153, 0, 0, 51, Int16[9],
  -1, 0), (153, 0, 0, 113, Byte[13], 0, 0), (153, 0, 0, 132, Int16[11], -1, 1), (153, 0, 0, 194, Byte[14], 0, 1),
  (153, 3, 1, 1333, Bit[3795], 1, 0), (153, 3, 1, 2545, Byte[8], 0, 0), (153, 3, 1, 2742, Int16[2], 304, 0);
- `visits[1]` (154@304): (154, 0, 0, 16, Bit[191], 0, 1), (154, 0, 0, 43, Bit[184], 0, 1), (154, 0, 0, 51, Int16[9],
  -1, 1), (154, 0, 0, 113, Byte[13], 0, 1), (154, 0, 0, 132, Int16[11], -1, 1), (154, 0, 0, 194, Byte[14], 0, 1),
  (154, 0, 0, 269, Byte[8], 125, 0), (154, 2, 1, 1409, Int16[2], 316, 0);
- `visits[2]` (153@316): (153, 0, 0, 51, Int16[9], -1, 1), (153, 0, 0, 113, Byte[13], 0, 1), (153, 18, 1, 766, Byte[8],
  0, 0), (153, 18, 1, 953, Int16[2], 110, 0);
- `counts`: (153, 0, 0, 16, Bit[191], 1, 0), (153, 0, 0, 43, Bit[184], 1, 0), (153, 0, 0, 132, Int16[11], 1, -1),
  (153, 0, 0, 194, Byte[14], 1, 0).
The tuples carry `same`, not `old`: the suppression pattern turns on whether a store changed its byte, and the `old`
values are CHAIN's (the chain rows) and START's (ip119's 1), so a chain-old or start-old mutant still fails its own
check alone. R-FULL measures every tuple before the freeze (F4).

---

## 5. Checks (O5's analysis)

### 5.1 Reading a run: the COVERED rule
O4's rule (skipped, install changed, the drive did not reach the end, a beat not done, no or an incomplete trace,
A-NOSTART, a BACKED forbidden hit, A-MISMATCH, A-START on 153's error path, A-NOEND), with A-START scoped to visit 1
(1.3: O5 revisits its start place). A drive VOID carries its V-class and its `[place, sc, visit]` cell (2.7). The report
lists every uncovered run's reasons per side.

### 5.2 The cuts (per side, frozen places)
`cut_at_start` from 153's first `w` row (place 153: real 153 on S, member(153) on F; the four residue rows in 70 go to
`pre`); `cut_at_end` at the first `w`/`r` row in an end PLACE -- `end_places(pred, side)`, [151] on both sides (S6).
Kept after the cut: the epoch rows and the `c` rows of places 153 and 154 (0.2 #2). On F the end place 151 is
member(151)'s; LANDING (d) reads the cut row's `fld` (31244 on F, 151 on S); a run that entered real 151 on F is VOID by
rule 2 first (V19).

### 5.3 The checks, in order, each with the mutant that makes it fail (section 8 registers every one)
**All-run checks** (every run with a readable trace, judged even when COVER is short):
- **O5-FORBIDDEN** (O2's). Mutant: back-door-unbacked-F.
- **O5-VOID-ASYM** (O4's (a)-(d) over S13's `[place, sc, visit]` cells; `stop_on` [V19]). Mutants: v19-one-F (a, c),
  v2-reask-one-F (a), v4-control-154-F (a), v4-control-316-F (a), v4-visit1-S-visit3-F (a: one S run V4 at
  `[153, 1190, 1]`, one F run V4 at `[153, 1190, 3]` -- under `[donor, sc]` cells they would cancel; the claim critique
  #5), error-path-316-F (a: V5 game at `[153, 1190, 3]`, no A-START; the claim critique #7), v7-walk-all-F (b),
  v13-cap-all-F (b: every F run V13 "no choice read" -- a fork that never asks 128), observed-quiet-page-one-F (d
  alone), observed-after-answer-one-F (d alone); and the PASS cases observed-quiet-page-each-side, v13-input-one-F,
  v13-choice-gone-one-F (no `observed` row: driver), v13-other-branch-one-S, v17-stray-one-S, v17-never-armed-one-F.

**Then:** **O5-FROZEN**, **O5-COVER**. Mutants: predictions-changed; stairs-beat-missing, choice-beat-missing.

**Core checks** (over the covered runs):
- **O5-START** (O3's): (a) `pre` is exactly the FOUR residue rows; (b) the first `w` row in place 153 is `start_first`,
  raw; (c) the first Byte[13] row in place 153 is ip119 `:= 0` from old 1. Mutants: start-residue-three (S: byte 3's
  row missing -- O2-O4's three-row contract would pass it), start-residue-wrong, front-cut-write, start-first-missing,
  start-music-old-wrong.
- **O5-NO-SC** (O3's `no_sc_check`): no kept row over bytes 0-1 after the start. Mutants: sc-write-fork (a `cs`
  UInt16[0] row in 154 on F), sc-harness-poke-both (NO-SC alone).
- **O5-CHAIN** (O2's `span_check` over bytes 2-3 from 325): exactly 4.3, in order, each from the last. Mutants:
  chain-dropped-fork, chain-first-old-wrong (alone).
- **O5-RESIDUE**: none after the start. Mutant: residue-after-start.
- **O5-WRITES (exact)**: every covered run's keys outside the noise ARE the 15 (O4's `writes_check`). Mutants:
  fork-drops-a-write (no 154 ip279 on F), writes-extra-symmetric (both: 153 e3 t1 ip3168's flashback store),
  inert-row-both (both: 153 e32 t0 ip718 `Bit[3855] := 1`) -- each with PATTERN (b), which reads every route row
  exactly: no WRITES failure in a route place is now WRITES' alone.
- **O5-NULL**, **O5-STABLE** (O1's, no noise). Mutants: NULL -- fork-drops-a-write, bit3795-zero-F; STABLE --
  extra-key-one-F (one F run of three holds the ip3168 store: STABLE F, WRITES F, STATE F, PATTERN F (b); NULL passes;
  registered in section 8 -- the claim critique #9).
- **O5-LANDING** (O4's shape over O5's crossings; every covered run, each clause named):
  - (a) every field-mode `w`/`c` row ran in its place's own field (member(place) on F) and stands in a route place
    [153, 154];
  - (b) the crossings, on field-mode `w` rows at their places' own fields: the run holds `landing.exit153` (153 e3 t1
    ip3150) and the next row after it is `landing.enter154` (154 e0 t0 ip26 `Bit[191] := 0`: 154 loaded by 153's
    Field(154)); it holds `landing.exit154` (154 e2 t1 ip1520) and the next row after it is `landing.enter153b` (153 e0
    t0 ip57 `Int16[9] := -1`, old -1: the revisit's first EMITTED row under this start's suppression pattern, 0.2 #2 --
    start-scoped, 5.4); no row of place 154 after `enter153b`;
  - (c) the last field-mode `w` row before the cut is `landing.exit153b` (153 e18 t1 ip1077, by PLACE), and the run's
    `end` log row names the side's end field (151 on S, 31244 on F);
  - (d) THE END PER SIDE: the cut row is `landing.end_row` (151 e0 t0 ip22 `Bit[191] := 0`) at `fld` the side's end
    field;
  - (e) every F digest records no seam and no seam key (the chain is closed from member(153) to member(151)).
  Mutants: lands-real-154-covered ((a)(b)(e), FORBIDDEN, WRITES), enter153b-unsuppressed-both ((b), with PATTERN (a)(b):
  visit 3 rendered without suppression, its first row ip22), 154-after-153b-both ((b) alone: a harness row, which
  PATTERN leaves out), last-place-harness-both ((c) alone), end-log-row-real-151-F ((c) alone, a synthetic log),
  end-real-151-F ((d) alone), end-boundary-residue-both ((d) alone).
- **O5-CHOICE** (new; decision 3), every covered run of both sides:
  - (a) exactly ONE store at `choice.store`'s site (153 e3 t1 ip1741, `Global.Bit[3795]`): one raw `w` row, old 0, new
    1, at fld member(153)/153, and NO `c` row of that site. Both clauses are needed: the sink emits a site's first
    SAME-VALUE store and counts only later ones (`SameEmitted` is set by a same-value store alone, StoryTrace.cs:
    383-395), so after ip1741's change 0 -> 1 a second store 1 -> 1 is a second `w` row (`same` 1) and only a third is
    a `c` row;
  - (b) exactly one `choice` row for the guarded rule: `index` 1, `took.landed` True, its answer's `press` row (`why`
    "choose", `answer`) with `selected_before` 1 and a `down_frame`; the visit's `guard` row with `verdict` "ok" and
    `branch` "pick" -- the game's own branch page after the answer (0.2 #20); no second;
  - (c) the store's value equals that `index`, and its row's frame `f` is at or after the answer's `down_frame` (both
    Time.frameCount);
  - (d) THE BACKSTOP (S10's judgment VOIDs a run first; the claim critique #2): the `guard` row's `armed_frame` set,
    `open_frame` set and `<= choice_first` (the window opens at the first sample without 127, which can be 128's own
    first sample: 2.5.2 -- a strict "before" would fail correct runs; the driver critique #2), `marker_last` set, and
    `guard_strays` over [`marker_last`, `choice_close`), excluding the answer's seq span and `closing_seq`, re-derived
    from the row's `presses` and equal to its `strays`, empty (an unplaceable press counts by its decision frame,
    fail-closed: O4's SWORD (f) rule).
  Mutants (each CHOICE alone unless named): choice-second-1741-both ((a): a second `w` row 1 -> 1, `same` 1; PATTERN (b)
  too), choice-third-1741-both ((a): that row and a `c` row; PATTERN (a)(b) too), choice-index-0-both ((b), with WRITES
  and PATTERN (b): the log's index 0 and the trace's 0), choice-unlanded-both ((b)), choice-cursor-off-pick-both ((b):
  `selected_before` 0), choice-branch-other-both ((b): the guard row's `branch` "other" on a covered run -- only a
  bypassed judgment could cover it), choice-store-before-answer-both ((c)), choice-stray-press-both ((d): a page press
  down inside [`marker_last`, `choice_close`)), choice-no-quiet-both ((d): `open_frame` None), choice-never-armed-both
  ((d): `armed_frame` None); bit3795-zero-F ((c) with WRITES F, NULL F, STATE F, PATTERN F (b): "a fork that stores a
  constant" -- its branch page is still the pick's, SYSVAR[9] being 1); and the PASS cases choice-open-at-first-both
  (`open_frame` == `choice_first`) and choice-closing-press-late-both (the closing marker press's down frame after
  `marker_last`: O4's recorded 2229/2237 shape).
- **O5-WALK** (new; THE PAIRED-WALK LAW), every covered run:
  - (a) exactly one `step` row of the stair step (`name` "the stairs", `donor` 153, `visit` 1) with `outcome` "done",
    its `lost` sample satisfying its `until` (re-checked: `until_ok`), its `landed` None; before it at most `interrupts`
    (1) `interrupted` rows, each with no `door` (a side scene, never an exit), and at most `attempts` - 1 (1) `failed`
    rows, each with `landed` None and no `door` (a walk that ended with control held: `x_trigger`'s `failed` carries no
    `lost`, segment_drive.py:2292-2302, and `run_step` lets the step run again, :2490-2494; the driver critique #3);
  - (b) no `w` row (any target, masked or not) whose frame lies inside a walk window -- each attempt's [`frame0`, its
    end], the end `lost.frame` for "done" and "interrupted" and the step row's own `frame` for "failed" (it has no
    `lost`), and each gap from an attempt's end to the next attempt's `frame0` (a side scene and its re-grant; a failed
    walk's standing wait): the walk wrote nothing, so no key can depend on its path.
  Mutants (each alone): walk-no-step-both, walk-lost-east-both (the done row's `lost` x -900), walk-two-interrupts-
  both, walk-interrupt-in-door-both, walk-two-failed-both (two `failed` rows, then "done"), walk-failed-in-door-both (a
  `failed` row with `door` 153.e28), walk-window-late-row-both (visit 1's ip200 row stamped inside the walk window, its
  order kept: WRITES, MASKED and PATTERN cannot see it); walk-window-masked-write-both ((b) with PATTERN (b): an extra
  `Bit[191]` row inside the window); and the PASS cases walk-interrupted-once-both and walk-failed-once-both.
- **O5-PATTERN** (new; the claim critique #1, #10): the suppression model's prediction, EXACT, every covered run --
  over the SCRIPT's rows (`src` "eb") of the route places [153, 154] before the cut that join (`ScriptIndex.join` on
  the stock bytes; a row that does not join is JOIN's; a C# or harness row is WRITES', NO-SC's and LANDING's), masked
  rows in:
  - (a) the `c` rows, as a multiset of (place, sid, tag, off, target, n, last), are `pattern.counts` (4.16): the four
    suppressed stores of visit 3 each present, each counted once, each with its last value -- their TIME is not
    compared (the engine writes a count at the epoch's close);
  - (b) the field-mode `w` rows, split into visits (maximal runs of one place), are `pattern.visits` -- each visit's
    sequence of (place, sid, tag, off, target, new, same) in order, a visit more or fewer failing. Byte[8]'s whole
    history is in them, its last row before the cut visit 3's ip890 := 0 (4.9).
  Mutants: c-n2-F ((a) alone: every F run's ip138 count n 2 -- a revisit whose prologue ran twice), c-missing-ip138-F
  ((a) alone: every F run's visit 3 without ip138's store), byte8-repeat-both ((b) alone: a second visit-3 ip890 store
  0 -> 0, emitted `same` 1 -- symmetric, so STATE (a) cannot see it; the claim critique #10).
- **O5-MASKED** (O2's). Mutant: masked-differs (with PATTERN (a)(b): the Bit[184] rows and count are frozen tuples).
- **O5-STATE** (O2's): (a) each unmasked target's emitted history identical across every covered run, in order, and the
  suppressed stores as a set; (b) every covered run's `end_state` == 4.9. Mutants: end-state-differs ((b) alone),
  suppressed-pattern-differs-F ((a), with PATTERN (a)(b): every F run's visit-3 ip138 EMITTED -- an engine that does not
  suppress at that site: NULL's sets are equal, the ordered history is not), fork-drops-a-write (a); and the PASS case
  byte8-race-both (every live end state reads Byte[8] 125: not registered, so the race cannot fail it). (a) now fails
  only with PATTERN (b): an exact per-run sequence subsumes a run-vs-run one; it stays as O2's shape and as the
  report's history.
- **O5-JOIN** (O1's). Mutant: join-failure.
- **O5-THROW** (in `run`): nothing thrown through EventEngine, EBin, StoryTrace or HarnessAgent.

**VERDICT**: O1's `verdict()`. A failed check outranks a void one: a V19 reads "NOT PROVEN: O5-VOID-ASYM", never VOID.

### 5.4 Report-only (`report_extra`)
- **Scope**, six lines:
  - *start dependence* -- "under the raw warp no key's VALUE on the route is start-dependent (constants and the frozen
    pick; Byte[6] |= 8 is after the cut); the EMITTED ROW PATTERN is: the sink emits the first same-value store per site
    per epoch (StoryTrace.cs:383-401), so after this start visit 1's ip57/ip119 are changes and visit 3's are emitted
    (same 1) while its ip22/ip49/ip138/ip200 are suppressed; after a true O1-O4 run visit 1's would be same-value and
    visit 3's first emitted row would be e18 t1 ip890; the `old` values differ too (Int16[9] 643 vs -1, Byte[13] 1 vs 0,
    Byte[8] 125 vs 75 at ip2953). O5-PATTERN's frozen sequences and counts, LANDING (b)'s re-entry row, STATE (a)'s
    ordered histories and every row count are this start's: never reuse them against a chained true-run trace. Not
    covered: party data, names, gil, Map variables (Map.Byte[27] is READ, as the branch witness's page, never compared),
    the camera, field 70's override state, and the fifteen untouched targets' values after a true O1-O4 run" (critic
    #5);
  - *suppressed stores* -- "the four suppressed stores before the cut, 153's visit-3 ip22/ip49 (masked) and ip138/ip200,
    are COMPARED by O5-PATTERN (a): each present, each counted once (n 1), each with its last value, as a multiset --
    their TIME is not compared (the engine writes a count at the epoch's close) and neither is their order among the
    `w` rows. Nothing else compares them: MASKED compares region names (its counts are reported), and STATE (a)'s
    suppressed set drops a count whose last value an emitted key carries -- all four here. The end place 151's `c` rows
    are cut and hold only stores after the cut (its first store IS the cut)" (the claim critique #1);
  - *the stored choice* -- "the stored value is compared with the driver's verified index and with the GAME's own branch
    page after the answer (141 for 1, 129 for 0: Map.Byte[27] := SYSVAR[9] at ip1749, read by e2 t1 ip844), so outside
    input that moved the cursor after the last sample before the answer's down frame -- invisible to `selected_before`
    -- VOIDs the run (the other branch's page: V13) instead of reading as 'a fork that stores a constant'; what remains
    is a fork that stores SYSVAR[9] and branches on something else -- both bytes are pinned, O5-KEYS" (the claim
    critique #13);
  - *the end state* -- "Byte[8] is read from the trace (153 e18 t1 ip890 := 0, the last pre-cut write; frozen by O5-PATTERN
    (b)), not live: 151 e0 t0 ip315 races the read";
  - *settings and engine* -- the recorded `settings`, `derived`, `engine` (O4's lines);
  - *language* -- derived from the session's recorded P-TEXT3 line (O4's `scope_lang` shape, block 3).
- **The walk, per run:** the grant's sample (frame, x, z), the route record (legs, length, replans, pushes, waits,
  blockers, slides), the loss sample (frame, x, z, published y) and the last control sample before it, ticks grant ->
  loss, interruptions and failed attempts, the calibration's probes (one-sided axes named).
- **The guard and the choice, per run:** 127's presses (decision, down and ack frames; which hold-off held each),
  127's last listed sample and the first without, the quiet window's open frame and its re-arms, 128's first
  publication and its readiness (the first sample with the group `Dialog.Choice`), the RACE MARGIN (from 127's last
  listed sample to 128's readiness, in ticks and seconds: the stall a stray press would need), 128 as published at
  readiness (options, active, selected), the pick, `took` (confirms, landed), `selected_before`, the guard row's
  `closing_seq`, `strays`, branch page and verdict.
- **The pattern, per run:** the emitted rows per visit, the `c` rows (site, n, last), visit 3's first emitted row, and
  O5-PATTERN's first difference from 4.16 when it fails.
- The session's end (S5), O4's sections copied (VOID reasons per side, masked counts, forbidden hits, the P-TEXT3 line,
  the folded transcripts), and the re-runs held.

---

## 6. Offline check and preflight

### 6.1 `--offline-check` (the install and O4's build, read-only; reads `--predictions`, else the frozen file, else the DRAFT, and prints which)
- **O5-BUILD**: `Segment.build_check` (every member's `.eb`, 7 languages, its own donor's with only in-chain `Field()`
  literals remapped: "140 files") + O5's ROUTE BUILD PINS, per language (each language's script decoded on its own; the
  US ips listed): the bytes in which member(153), member(154) and member(151) differ from their donors are EXACTLY the
  operands of their in-chain `Field()` instructions -- member(153): e3 t1 ip3158 (154), e18 t1 ip1085 (151), e23 t2 ip211
  (154), e24 t2 ip191 (150), e25 t2 ip203 (64) and ip429 (151), e28 t2 ip235 (150); member(154): e2 t1 ip1528 (153) and
  the six of e8/e9/e10 t2 (153, 158, 156, 155, 156, 167); member(151): e2 t1 ip940 (153), e8 t2 ip245 (153); member(153)'s
  `Field(204)` (e3 t1 ip3296, the flashback: 204 is no chain donor) stays the donor's. The sites are DATA in the
  predictions (`route_build`, O4's `fight.build` shape); C0 measures them on O4's build (every language) before C1
  registers them, and any other differing byte is explained at the byte level, never loosened.
- **O5-KEYS**: O4's `keys_check` machinery -- O2's on a filtered copy (the chain, the writes but the `:=var` key,
  `forbidden_sites` + `error_path` + `dead`, `start_first`), the `:=var` key (153 e3 t1 ip1741, rvalue `B_SYSVAR[9]`, in
  its statement), `start_music` one writes key -- then THE ROUTE PINS (4.14): every pin's text exactly the stock US
  script's, `route_mes` as pinned. Expected: O2's half "36 sites (36 keys), every op in its statement, 0 compound values
  computed from their priors, none masked (start_first's Bit[191] is boot_scratch: O2-START reads it raw)" -- chain 3,
  writes 11 (the `:=var` key filtered out), forbidden 2 + error path 8 + dead 11 (153: 8, 154: 3), start_first 1 --
  then "; the choice's :=var key (153 e3 t1 ip1741, rvalue B_SYSVAR[9]) in its statement; start_music one writes key"
  (37 sites; Bit[3795] lies outside the story-noise mask, `T.noise_regions` empty) and "; 53 route pins equal; mes 127
  holds the marker and no [TIME=, mes 128 opens [PCHC=2,1], holds [IMME] and the pick on its second line, mes 141 holds
  the pick's branch marker and 129 the other's, mes 56 the stop page" (4.14's table: 53 instruction sites -- the first
  design's 47 plus e31 ip648/ip669, e2 ip840/ip844, e3 ip1899/ip3430 -- each text verified against the stock US listing
  while designing).
- **O5-TEXT**: O4's `text_check` on block 3, STRICT (`strict_text`): "block 3: 7 byte-equal of 7; KNOWN-KIT-DEFECT 0,
  FAIL 0".
- **O5-CENSUS** (O5's `store_census`): every gEventGlobal store site of stock 153 and 154 is in `writes`, `chain`, the
  noise mask, `start_first`, `error_path`, `forbidden_sites`, `dead` or an `inert` function (O4's class precedence);
  every function decodes; no unresolved store. THE INERT PROOF, per entrance: every instancing op of the field sits in e0
  t0 (`instancing_sites`), and NO entrance the route enters the field by (`visit_entrances`: 153 at 325 AND 316, 154 at
  304) instances an inert entry (`instanced_at`); a SHARED inert entry (`shared_by`) needs, besides, that every
  `RunSharedScript(n)` site of the field lies in a function of an inert entry (153 e15: its one caller e32 t1 ip866). A
  registered key inside an inert function FAILS by name. Expected: "153: 51, 154: 22 store sites -- all classified
  (writes 7/5, chain 2/1, masked 2/2 (153's ip22 is start_first), error_path 4/4, forbidden 2/0, dead 8/3, inert 26/7);
  0 unresolved; inert 153 e15 (shared, run only from e32), e23, e24, e25, e32 not instanced at 325 or 316; 154 e5, e8,
  e9, e10 not instanced at 304". 151 is the end place: its first store at 110 is the cut (O5-LANDING (d)); no site of
  it precedes the cut, and its census is O6's.
- **O5-REGIONS** (O5's `regions_problems`; 0.2 #11): every frozen region's points are the first SetRegion of its (donor,
  entry); `exit`: `scan_gateways` has its (to, entrance, face_gate) AND it is instanced at some route entrance of its
  place; `scene`: instanced at a route entrance, its tag 2 holds `DisableMove()` after a `Map.Byte[24] const(<stage>)
  B_EQ` test, its entry holds no gEventGlobal store and no `Field()`/`ExitField()`; `dormant`: instanced at none of its
  `entrances`, which must be exactly the place's route entrances. Every gateway of 153 and 154 (`scan_gateways`) and
  every region instanced at a route entrance is registered; no hot-spot (`hotspot_census` of 153 and 154 empty).
  Expected: "9 regions (1 exit, 2 scene, 6 dormant), 0 hot-spots, 7 gateway entries all registered".
- **O5-GOALS**: O2's `goals_check` on the table (the step runnable, `visits` a walk on the route from the start place,
  the goal on the floor >= 80 from a wall with the 33 tris closed, its `until` true at the goal, a route from `start`
  avoiding e26/e27/e28) -- then O5's `goals_extra`: (c) THE CONTOUR ON THE ROUTE: the planned route, sampled every 5 u
  on the real mesh (the open tri under each point, its interpolated height), reaches PSX y <= -450 before its end, at a
  point with x <= `until`'s -1100 (measured: ~(-1479, 529), tri 56, 312 u into the last leg; the check prints the
  measured point -- and for a step carrying F15's `clearance`, the route the planner gives at it: ~(-1523, 558) at
  120); (d) THE EVIDENCE'S SOUNDNESS, ON THE CONTOUR (0.2 #22; the claim critique #11): on the start's open component
  (the 33 closed, the mask's door strips closed), every point where an open tri's EDGE crosses PSX y -450 -- and every
  vertex lying exactly on it -- is at x <= -1100 (measured: tris 53 and 56 only, x -1722..-1403); heights are
  continuous across shared edges, so a walk first stands at y <= -450 on that contour, and every open tri wholly at
  y <= -450 is reached only across it; and every registered `scene` and `exit` region of 153 lies wholly at x > -1100
  -- so a loss at x <= -1100 in stage 6 is the stair's and nothing else's. The first design's "every open tri vertex
  and centroid at y <= -450 lies at x <= -1100" was FALSE on this mesh (the upper stair's tris 50, 51, 60, 71 sit
  wholly beyond the contour at x -460..-866) and would have failed here: the contour's points are both the sound
  statement and the complete sample (a tri's y <= -450 part is a convex polygon whose extreme x lies at one of its
  vertices or edge crossings).
- No SEAM check (the chain is closed: LANDING (e)).

### 6.2 `--preflight` (the live install, read-only; ALL GREEN today -- nothing needs deploying)
- **P-MANIFEST** (`o5_forks.json` members = the frozen members, `deployed` true), **P-DEPLOY** (twenty, each once under
  its name, mapped once), **P-EB** (20 x 7 live `.eb` = O4's build), **P-FLOOR** (twenty deployed walkmeshes = their
  donors'; member(153)'s is the stair walk's floor).
- **P-STOCK**: no mod folder overrides 151, 153 or 154 (today: none).
- **P-TEXT3** (block 3, STRICT: O4's `p_text` with no tolerated copy): today "FF9CustomMap: KNOWN-KIT-DEFECT 0, FAIL 0, 7
  byte-equal of 7".
- **P-RECOVERY**: 4600 registered (FF9CustomMap-world).
- **P-DONOR**: 151, 153 and 154 each forked by exactly ONE ForkDonorPatch row across the stack, its member's (today:
  31244, 31245, 31246 in FF9CustomMap; the stack's twice-forked donors 312, 350-359 are off the route).
- **P-SETTINGS** (4.13's 28 keys), **P-PAD** (O4's), **P-OVERRIDE** (field 70's override, one folder, the pinned sha),
  **P-ENGINE** (the live x64/x86 DLLs the pinned sha).
- Not carried (11.2 #1): P-GATE (R-GATE's +30% witness: O4's fight alone), P-TEXT2 (block 2: no O5 field reads it).
- **In game** (`capabilities`): P-CAP, P-OBJECTS ("the engine publishes the field's objects (s89): the walk's `npcs`
  plans round Blank, the floor's one body; e9/e11/e31 publish walk-through"), P-LANG (English(US)), P-DONOR-LOG (this launch's Memoria.log: the
  patchers ran, no ForkDonorPatch collision for 151, 153 or 154), P-LAUNCH (every stacked patch file, Memoria.ini and
  the engine DLLs older than the launch; the DLLs the pinned engine), P-PAD (re-sampled).
`--preflight` must read all green before any rehearsal; if it does not, the lead says exactly which line failed and
stops (decision 6).

### 6.3 The fingerprint (per run, before and after)
O4's, unchanged (registrations, ForkDonorPatch rows, `.eb` and walkmesh shas, stock overrides, `override70`, `text2`,
`text3`, `lang`, `settings`, battle data, `engine`): another session's deploy, a re-wired New Game or an engine rebuild
mid-session makes runs VOID (A-INSTALL), never skews them.

### 6.4 `o5_forks.json` (the implementer writes it; nothing to flip: the chain is live)
```json
{"what": "O5's fork chain: O4's alxc disc-1 chain as deployed (31240-31259, FF9CustomMap). O5 runs member(153) 31245 (visits 1 and 3), member(154) 31246, and ENDS in member(151) 31244: every route Field() is retargeted, so the chain is closed (no seam). Nothing is imported, built or deployed for O5.",
 "reuses": "studies/story-trace/o4_forks.json",
 "import": "O4's (o4_forks.json import)", "build": "O4's: C:/gd/_ns_playtest/o4/build", "deploy": "O4's, 2026-10-02 09:04 local",
 "mod_folder": "FF9CustomMap", "members": {"<20 fork ids>": "<donor>"}, "names": {"<20 fork ids>": "<name>"},
 "route_members": {"31244": 151, "31245": 153, "31246": 154},
 "text_blocks": {"3": [31243, "...", 31259]},
 "deployed": true, "relaunch_needed": false,
 "relaunch_why": "nothing is deployed for O5; P-LAUNCH proves the launch read the live patch files, P-DONOR-LOG that it logged no collision for 151, 153 or 154",
 "global_side_effects": "O4's (o4_forks.json global_side_effects): O5 adds none",
 "known_defects": [], "revert": "O4's (o4_forks.json revert)",
 "built": {"measured": "<C0: the route members' Field() operand sites per language, read from O4's build>"},
 "verified": null}
```

---

## 7. Rehearsal plan (the lead runs these in game)

### 7.1 The stages (`o5_rehearse.py`: `run(g, field=None)`; `O5_STAGE=<name>` picks one by name, `--field 153` R-STAIRS)
Each traced stage: New Game; `wait_frames(30)`; `storytrace(True)`; the raw warp; `segment_drive.drive(g, stage_pred,
side, log, end_fields=..., observe=recorder, forbid_live=True, witness=input_witness(g))`; the trace to
`rh_<stage>_<n>.jsonl`; the record into `o5_rehearsal.json`; `end_run`. Only R-FULL's traces may define or change the
keys, the start, the end state or the row pattern; the staged runs prove mechanics and are compared within their stage.
F-SMOKE and F-PASS send NO `storytrace` verb: no fork trace exists before the freeze.

| Stage | When | Warp | Ends in | Runs | What it settles |
|---|---|---|---|---|---|
| **R-STAIRS** (the go/no-go) | stock | `warp 153 325 1190` | 154 | 2 | F1-F3, F8, F9, F11, F12, F15: the grant position and frame; the walk (route, every hold's slide, push and stall on the last two legs, calibration probes); the loss sample and its latency (the last control sample, the first without, published y); the teleport sample; the published objects (Blank's `coll`/`r`); 127's presses and 128's timeline, the race margin to 128's readiness; 128 as published at readiness; the landing; the branch page; any dialog-section catch sample; the KEYON pairs' gates and the [TIME=20] windows under Confirm |
| **R-FULL** (by name) | stock | `warp 153 325 1190` | 151 | 2 | F4-F7: the 15 keys, the masked rows, O5-PATTERN's tuples (every visit's emitted sequence, the four `c` rows' n and last), the four residue rows, the end cut 151 e0 t0 ip22, the end state (Byte[8]'s read value recorded), the run time, the longest no-progress stretch |
| **R-WALK-VOID** (by name; LAST in a launch) | stock | `warp 153 325 1190`, the stage overlay `walk_stop_x` -700 | V13 | 1 | F7: the walk stopped MID-WALK -- o5_rehearse wraps `g.send` to raise "the rehearsal's stop mid-walk" before the first `hold` step sent while the published x is <= `walk_stop_x` (on the driver's own thread: nothing keeps sending after it), not a timer (a 0.8 s one expires in `route_to`'s settle, rate wait or calibration, session.py:4394-4421, never on the stair); no `hold` step in steps.jsonl after the raise; `end_run` (warp 4600 from 153's FieldHUD, the ladder) reaches the title |
| **F-SMOKE** (by name; NO trace) | any time (deployed) | `warp 31245 325 1190`, `warp 31246 304 1190`, `warp 31244 110 1190` -- each `member(<donor>)` resolved from the chain (`stage_ids`) -- and their stock twins | -- | 6 warps | F13: each member loads at its entrance and SC (field, FieldHUD), its published object sids EQUAL to its stock twin's measured set after `smoke_s` -- never a hard-coded set: the agent skips the player (HarnessAgent.cs:2321), so 153@325 should publish {7, 9, 11, 31}, 154@304 {4}, 151@110 {4, 5, 12, 17}, but only the twin's reading is compared --, 0 exceptions, `end_run` ok |
| **F-PASS** (by name; NO trace; before the freeze) | after F-SMOKE | `warp 31245 325 1190` | 31244 | 1 | F14: one F run through the whole route on the DRAFT (`forbid_live` False, `end_row_s` None): member(153)'s stage 27 VIB ops (s62's donor-name fix) run once; reached member(151), beats `stairs`/`choice128`, no V-class, no exception through EventEngine/EBin/HarnessAgent/HonoluluFieldMain/vib since the warp. It may only STOP the session (F14); its record is never evidence for any key and never shapes a frozen value |
| **R-RACE** (optional, by name) | stock | `warp 153 325 1190`, the overlay `guard: null` | 154 | <= 3 | the unguarded race's frequency directly: a stray answer is recorded (the choice gone, path 0), never covered |

Default order without `O5_STAGE`: R-STAIRS, R-FULL, R-WALK-VOID (last). F-SMOKE, F-PASS and R-RACE by name only.
Estimates a run: R-STAIRS ~3 min, R-FULL ~4.7 min, R-WALK-VOID ~1 min, F-SMOKE ~3 min in all, F-PASS ~4.7 min.
`o5_rehearse.py` reuses O4's shapes (`select`, `stage_ids` resolving `member(N)` and checking every F-side id against the
chain, `stage_pred` merging an overlay into a COPY and re-checking it with `guard_of`/`step_of`, `one`, `smoke`,
`launch_readings`) and `O4R.Recorder` (each page's windows and `gone_frame`, the KEYON pairs), plus `fpass(g, ...)` (an
untraced start: New Game, `wait_frames(30)`, the warp, then the drive -- never `Segment.start_run`, which arms the trace)
and the walk's and the guard's records off the drive's own rows. Every summary is cut at the stage's end PLACES
(`o5_hallway.trace_summary`). The command: `py tools/play.py studies/story-trace/o5_rehearse.py --label o5-rh --timeout
240`.

### 7.2 What every stage records
O4's record (grants, pages with `timed`, the published choices, the press evidence, the longest no-progress stretch,
the end state, `end_run`'s rows) plus:
- the walk: the grant sample (frame, x, z) and the frames from 117's going to it; the step rows whole (route record,
  `lost`, `door`, attempts, failed attempts); per hold on the last two legs (from the stair-foot corner on) its
  intended and measured travel -- a SLIDE (moved off the leg's heading by more than 20 deg), a PUSH (the route record's
  `pushes`/`pushed`), a STALL (under a quarter of the intended travel) -- the driver critique #11; the last control
  sample and the first without (ring); the published y at both; the teleport sample (the first sample at (-1165, 856)
  +- 32) and its ticks after the loss; the published objects at the grant (sids, `shown`, `coll`, `solid`, `r`,
  `talk_r`, `range_r`); the calibration record (probes, lengths, any one-sided axis);
- the guard: 127's first seen, its presses (decision, accepted, down, ack frames; which hold-off held each), last
  listed, first without; the quiet window's open frame and re-arms; 128's first publication, its first ready sample
  (group Dialog.Choice) and whether its options changed after it (`[IMME]`: they must not); its options/active/selected
  at readiness; `choose_landed`'s record and presses; the guard row (`closing_seq`, `strays`, the branch page, the
  verdict); the RACE MARGIN (ticks and seconds from 127's last listed sample to 128's readiness); every sample of the
  run with no dialog section but the group `Dialog.Choice` or a marker page listed again after a sample without it
  (the dialog-section catch, 0.2 #18: its rate);
- the KEYON pairs (first seen -> gone, Confirms pressed), the timed windows (137, 140: the Confirms pressed while listed
  and their lives in ticks);
- the trace through `trace_summary`: the start rows, the chain rows, each registered key present or absent, every
  unregistered key, the emitted rows per visit and the `c` rows, visit 3's first emitted row, the end cut's row, the
  residue, the masked counts, the join failures;
- the launch's settings and engine, P-LAUNCH, P-DONOR-LOG, P-PAD, P-OVERRIDE and P-ENGINE readings;
- F-SMOKE: per warp the field and UI reached and when, the object sids against the twin's, exceptions, new Memoria.log
  warnings, `end_run`'s result; F-PASS: the drive's outcome and rows, the exceptions since the warp, whether page 137
  (stage 27) was seen.
`py studies/story-trace/o5_hallway.py --rehearsal-report <run dir>` prints all of it, stage by stage, run by run.

### 7.3 The freeze checklist (each item needs its evidence; the run dirs go into `rehearsals`)
- **F1 (the grant and the walk; go/no-go).** In every R-STAIRS and R-FULL run: control granted once in 153 near (1105,
  -78) (within 64 u; else the step's `start` takes the measured point and O5-GOALS runs again before the freeze), the
  stair step `done` on its first attempt (or after one absorbed side scene; a `failed` first attempt is admitted by
  O5-WALK but in a rehearsal it is explained -- F15 when a contact caused it), its loss sample at x <= -1100, no
  V-class. A walk that fails its evidence: STOP and re-derive the contour and the evidence from the measured loss samples.
- **F2 (the race).** In every guarded run: 127 pressed by page-once until gone, its closing press the guard row's
  `closing_seq`; the quiet window opened (at or before 128's first sample); nothing pressed in it; 128 published within
  `quiet_cap_s`; the guard row's verdict "ok" -- no press of the driver's in [127's last listed sample, 128's close) but
  the answer's and the closing press; the race margin recorded. A stray, a never-armed window or a V13 cap on a guarded
  run: STOP -- the fallback (2.5.7) is then the lead's call. (R-RACE, if run, records the unguarded frequency.)
- **F3 (128 as published).** Options/active/selected at readiness: the rule's "her face" matches exactly one line,
  absolute 1; `selected` 0; its options unchanged after readiness (`[IMME]`, no type-out: 0.2 #14 -- a change STOPs the
  freeze for an engine-level explanation); the landing took <= `CHOICE_CONFIRMS` Confirms and `selected_before` 1; the
  first page after it 141 (the guard row's `branch` "pick").
- **F4 (keys and the pattern).** The R-FULL traces define the predictions: per run exactly the 15 keys and the masked
  rows; no error-path, dead, forbidden or inert row; exactly the four start residue rows and none after; 153's first
  `w` row ip22 and its first Byte[13] row ip119 from old 1; every visit's emitted sequence and the four `c` rows (n 1,
  their `last`s) exactly 4.16's tuples -- O5-PATTERN's measurement (the claim critique #1); the end cut 151 e0 t0 ip22;
  the two runs key for key and tuple for tuple identical; any difference explained at the byte level before the freeze
  (a new site only with O5-CENSUS's lists updated).
- **F5 (end state).** Every R-FULL `end_state` equals 4.9; Byte[8]'s live reading recorded (0 or 125: the race).
- **F6 (budgets).** `run_s` = 2 x the slowest R-FULL; `run_min_s` = 1.25 x the median; `session_s` = 8 x the median +
  1800; `no_progress_s` = max(60, 3 x the longest no-progress stretch of any traced stage); `quiet_cap_s` = max(2, 3 x the
  slowest MEASURED gap, 127's last listed sample -> 128's first publication, in game seconds -- it holds e31's
  WaitAnimation rest, 0.2 #14; the driver critique #9); `settle_s` = 1.0, O1's (128 has no type-out to outlast: the
  driver critique #4; critic #6's sizing was for one).
- **F7 (recovery).** R-WALK-VOID: the stop at x <= -700 with no `hold` step in steps.jsonl after the raise (the driver
  critique #8), then `end_run`'s rows `recover-warp` (4600) and the title; `end_run` from 154 (R-STAIRS) and 151
  (R-FULL) reach the title.
- **F8 (pairs and timed windows).** Every KEYON pair closed within 8.3 s of its second window; 137/140 inert to Confirm
  (else explained at the engine level before the freeze: a Confirm that closes them early changes no store).
- **F9 (pages' openings).** The dropped first presses counted; `page_once_ticks` := max(10, 2 x the longest measured
  page opening in ticks).
- **F10 (settings and launch).** P-SETTINGS, P-PAD, P-OVERRIDE, P-ENGINE, P-LAUNCH and P-DONOR-LOG pass on the
  rehearsal launch; its fingerprinted `settings` and `engine` equal 4.13's.
- **F11 (the input witness).** No `input` row in any run; the dialog-section catch's rate recorded (7.2) -- more than
  one such sample in a run is explained before the freeze (S10 and S11 survive one; the reason they must is 0.2 #18).
- **F12 (objects).** Blank published `coll` true, `solid` false, `r` 176, `talk_r` 377, `range_r` null (0.2 #19; the
  driver critique #5 -- 176, not its 160); e9/e11/e31 published `coll` false, `shown` false; the player in no list; the
  walk planned round Blank without a push; the calibration record's one-sided "v" axis, if any, recorded as expected.
- **F13 (F-SMOKE).** The three members load as their twins, their object sids each EQUAL to the twin's measured set.
- **F14 (F-PASS: may only STOP the session; the claim critique #12).** Reached member(151) with no throw and no
  V-class; page 137 seen (stage 27 ran). Any V-class or throw it shows is a FINDING written into PLAN.md before
  anything else; an engine or build change made in response re-pins P-ENGINE and P-EB and repeats F-PASS; nothing it
  records ever shapes a frozen value -- keys, pattern, budgets, guard sizes (those come from the stock stages alone).
- **F15 (stair contacts; the driver critique #11).** No slide, push or stall on the last two legs in any R-STAIRS or
  R-FULL run. Any one: before the freeze the step gains `clearance` 120 -- an opt-in step key, `walk_kw` passing it to
  `route_to(clearance=)`, a keyword-only session addition defaulting to None (today's planner) and threaded into each
  planner call of `_route_to` (`route_avoiding`, `_plan_round`, `_plan_npcs`) -- with its tests and a G21
  re-baseline row named; at 120 the planner gives 3273 u, >= 124 u off every wall, the contour at ~(-1523, 558)
  (0.2 #21); O5-GOALS re-derives it and R-STAIRS runs again (F1) before the freeze.
Then `--freeze` (v1). `freeze` refuses: no `guard` or one `guard_of` refuses (or a `guard: null` overlay); no
`witness`; a table step carrying a rehearsal overlay (`walk_stop_x`); `side_ends` failing `side_ends_of`; a non-empty
`battles`; an empty `rehearsals`; an `engine` that is not the live DLLs'; an existing file.

### 7.4 After the freeze: the session (the lead)
- **G1.** `--preflight` all green on the session's launch (P-LAUNCH, P-ENGINE, P-DONOR-LOG in game).
- **G2.** The session, unattended and hands off (no key while the game has focus, no pad -- the witness VOIDs a run
  that sees one, V13): `py tools/play.py studies/story-trace/o5_hallway.py --label story-o5 --timeout 240`.

---

## 8. The dry run (`o5_dryrun.py`: synthetic sessions through `O5.analyse`)

Built like `o4_dryrun.py`: its own `render` (O4's, with O5's start values -- SC 1190, FieldEntrance 325, Byte[13] 1,
Int16[9] 643, Int16[11] -1, Byte[8] 125, every other target 0 -- and the sink's rule: a same-value store emitted only
while its SITE has emitted no same-value row (a change does not close that), a change up to 64 times, the rest counted
into `c` rows just before `off`; the site key holds `fld`, so the revisit's prologue suppresses exactly as 4.16), O3's
event helpers, and O3's EXACT `case()` (every check a case does not name must read PASS; a COVER-VOID case expects every
core check VOID; LANDING, CHOICE, WALK and PATTERN cases register the clause the detail must name).
- **Real store sites** (every field row joins): 4.3-4.5's, the error-path, forbidden, dead and inert sites, 151 e0 t0
  ip22 (the end row) and 151's post-cut prologue and ip315.
- **A base run**: `arm` (fld 70); the four residue rows (fld 70); visit 1's rows (4.16) with ip1741 (0 -> 1) between the
  walk and the exit; visit 2's; visit 3's six prologue stores (render suppresses four) and its two; 151's ip22, then
  its post-cut rows; `off` (fld 151 / 31244). On F: 153 -> 31245, 154 -> 31246, 151 -> 31244.
- **A log**: the visit rows; the stair step row (`done`, `frame0` and `lost` bracketing no trace row, `lost` (-1479,
  529)); the page presses with `seq` and `ack_frame` (127's with `marker` True); the choice row (options
  `['Zidane\n"Hmm..."', 'Let her pass', 'Examine her face']`, active [0, 1], selected 0, index 1, `took` {landed True,
  confirms 1}); its `choose` press rows (down; confirm with `selected_before` 1, `answer`, a down frame before ip1741's
  row); the `guard` row written at 141 (armed, open a sample before `choice_first`, `marker_last`, the presses with down
  frames, `closing_seq` 127's last press -- its down frame before `marker_last` --, `strays` [], `branch` "pick",
  `verdict` "ok"); the end row (151 / 31244); `end_state` (4.9); beats `{"stairs": true, "choice128": true}`. Every VOID
  a case adds carries a `[place, sc, visit]` cell.

| Case | Want |
|---|---|
| null-pair | PROVEN |
| fork-drops-a-write (no 154 ip279 on F) | NOT PROVEN (WRITES F, NULL F, STATE F, PATTERN F (b)) |
| chain-dropped-fork (no 154 ip1520 on F) | NOT PROVEN (CHAIN F, LANDING F (b), WRITES F, NULL F, STATE F, PATTERN F (b)) |
| chain-first-old-wrong (both: ip3150's old 326) | NOT PROVEN (CHAIN F alone: PATTERN's tuples carry `same`, not `old`) |
| start-residue-three (S: byte 3's row missing) | NOT PROVEN (START F) |
| start-residue-wrong (S: byte 3 0 -> 2) | NOT PROVEN (START F) |
| start-first-missing (both: visit 1's ip22 dropped -- render emits visit 3's ip22 instead, as the sink would) | NOT PROVEN (START F; LANDING, MASKED and PATTERN (a)(b) as the render shows -- registered with their byte-level reason) |
| start-music-old-wrong (both: ip119's old 3) | NOT PROVEN (START F) |
| front-cut-write (F: a `w` row in fld 70 before the start) | NOT PROVEN (START F) |
| error-path-start-S (one S run: visit 1's 153 ip97, stopped at window 56; V5 driver [153, 1190, 1]) | PROVEN (S 2 of 3); the run's classes include V5 and A-START |
| error-path-154-F (one F run: 154 ip101, window 56; V5 game [154, 1190, 2]) | NOT PROVEN (VOID-ASYM F) |
| error-path-316-F (one F run: visit 3's 153 ip97, window 56; V5 game [153, 1190, 3]) | NOT PROVEN (VOID-ASYM F (a)); that run's reasons hold V5 and NO A-START (the claim critique #7) |
| residue-after-start (F: an `r` row on byte 300) | NOT PROVEN (RESIDUE F) |
| writes-extra-symmetric (both: 153 e3 t1 ip3168) | NOT PROVEN (WRITES F, PATTERN F (b); NULL P) |
| inert-row-both (both: 153 e32 t0 ip718) | NOT PROVEN (WRITES F, PATTERN F (b); NULL P) |
| extra-key-one-F (one F run of three holds 153 e3 t1 ip3168's store) | NOT PROVEN (STABLE F, WRITES F, STATE F, PATTERN F (b); NULL P) -- STABLE's mutant, registered (the claim critique #9) |
| sc-write-fork (F: a `cs` UInt16[0] := 1190 row in 154) | NOT PROVEN (NO-SC F, WRITES F, NULL F, STATE F) |
| sc-harness-poke-both | NOT PROVEN (NO-SC F alone) |
| bit3795-zero-F (every F run: ip1741 := 0; end state Bit[3795] 0; the log unchanged, its branch page the pick's) | NOT PROVEN (WRITES F, NULL F, STATE F, CHOICE F (c), PATTERN F (b)) |
| choice-second-1741-both (a second ip1741 store, 1 -> 1: a `w` row, `same` 1) | NOT PROVEN (CHOICE F (a), PATTERN F (b)) |
| choice-third-1741-both (a second and a third ip1741 store: that `w` row and a `c` row n 1) | NOT PROVEN (CHOICE F (a), PATTERN F (a)(b)) |
| choice-index-0-both (the choice row index 0, ip1741 := 0) | NOT PROVEN (CHOICE F (b), WRITES F, PATTERN F (b)) |
| choice-unlanded-both (`took.landed` False) | NOT PROVEN (CHOICE F (b) alone) |
| choice-cursor-off-pick-both (`selected_before` 0) | NOT PROVEN (CHOICE F (b) alone) |
| choice-branch-other-both (the guard row's `branch` "other" with `verdict` "ok": a bypassed judgment) | NOT PROVEN (CHOICE F (b) alone) |
| choice-store-before-answer-both (ip1741's frame before the answer's down frame) | NOT PROVEN (CHOICE F (c) alone) |
| choice-stray-press-both (a page press down inside [`marker_last`, `choice_close`), the row's `strays` [] and verdict "ok": a bypassed judgment) | NOT PROVEN (CHOICE F (d) alone) |
| choice-no-quiet-both (the guard row's `open_frame` None) | NOT PROVEN (CHOICE F (d) alone) |
| choice-never-armed-both (the guard row's `armed_frame` None) | NOT PROVEN (CHOICE F (d) alone) |
| choice-open-at-first-both (`open_frame` == `choice_first`: 128's first sample was the first without 127) | PROVEN (the driver critique #2) |
| choice-closing-press-late-both (127's closing press down after `marker_last`, no close-tween sample: O4's 2229/2237 shape) | PROVEN |
| v17-stray-one-S (one S run VOID V17 driver at [153, 1190, 1]: path 0's rows, ip1741 := 0) | PROVEN (S 2 of 3) |
| v17-unlanded-one-F (one F run VOID V17 driver: the answer did not land) | PROVEN (F 2 of 3) |
| v17-never-armed-one-F (one F run VOID V17 driver: 127 closed by a rule-7 press) | PROVEN (F 2 of 3) |
| v17-unplaceable-one-S (one S run VOID V17 driver: the answer's Confirm had no accepted event) | PROVEN (S 2 of 3) |
| v13-input-one-F (one F run VOID V13 driver: outside input at the choice) | PROVEN (F 2 of 3) |
| v13-choice-gone-one-F (one F run VOID V13 driver: 128 gone with no press of the driver's in its window; no `observed` row) | PROVEN (F 2 of 3) |
| v13-other-branch-one-S (one S run VOID V13 driver: the first page after the answer is 129; path 0's rows, ip1741 := 0) | PROVEN (S 2 of 3) |
| v13-cap-all-F (every F run VOID V13 driver at [153, 1190, 1]: no choice read within the cap) | NOT PROVEN (VOID-ASYM F (b); COVER V) |
| v2-reask-one-F (one F run VOID V2 game at [153, 1190, 1]) | NOT PROVEN (VOID-ASYM F (a)) |
| v4-control-154-F (one F run VOID V4 game at [154, 1190, 2]) | NOT PROVEN (VOID-ASYM F (a)) |
| v4-control-316-F (one F run VOID V4 game at [153, 1190, 3]) | NOT PROVEN (VOID-ASYM F (a)) |
| v4-visit1-S-visit3-F (one S run VOID V4 game at [153, 1190, 1], control after the stair step; one F run V4 game at [153, 1190, 3]) | NOT PROVEN (VOID-ASYM F (a), each side's) -- under `[donor, sc]` cells they cancel (the claim critique #5) |
| v19-one-F (one F run VOID V19 game at [151, 1190, 3]: landed in real 151) | NOT PROVEN (VOID-ASYM F (a)(c)) |
| leak-real-154-F (one F run VOID V19 at [154, 1190, 1]; its rows at fld 154) | NOT PROVEN (FORBIDDEN F, VOID-ASYM F) |
| back-door-S (one S run VOID V11 driver: e28's two rows, a step row V11 `door` 153.e28 `landed` 150, rows in 150) | PROVEN (S 2 of 3; the 150 hits backed: A-FORBIDDEN) |
| back-door-unbacked-F (one F run: e28's rows and rows in 31243, no step row explains them) | NOT PROVEN (FORBIDDEN F, and the co-failures the rows give -- registered with their reason) |
| v7-walk-all-F (every F run VOID V7 driver at [153, 1190, 1]) | NOT PROVEN (VOID-ASYM F (b); COVER V) |
| walk-never-contour-one-S (one S run VOID V7: the walk ended with control held twice) | PROVEN (S 2 of 3) |
| walk-interrupted-once-both (every run: one `interrupted` row, then `done`) | PROVEN |
| walk-failed-once-both (every run: one `failed` row -- no `lost`, `landed` None -- then `done`) | PROVEN (the driver critique #3) |
| walk-no-step-both | NOT PROVEN (WALK F (a) alone) |
| walk-lost-east-both (the done row's `lost` x -900) | NOT PROVEN (WALK F (a) alone) |
| walk-two-interrupts-both | NOT PROVEN (WALK F (a) alone) |
| walk-interrupt-in-door-both (an interrupted row with `door` 153.e28) | NOT PROVEN (WALK F (a) alone) |
| walk-two-failed-both (two `failed` rows, then `done`) | NOT PROVEN (WALK F (a) alone) |
| walk-failed-in-door-both (a `failed` row with `door` 153.e28) | NOT PROVEN (WALK F (a) alone) |
| walk-window-late-row-both (visit 1's ip200 row stamped inside the walk window, its order kept) | NOT PROVEN (WALK F (b) alone) |
| walk-window-masked-write-both (an extra Bit[191] row inside the walk window) | NOT PROVEN (WALK F (b), PATTERN F (b)) |
| lands-real-154-covered (every F run: 154's rows at fld 154, the drive reached) | NOT PROVEN (LANDING F (a)(b)(e), FORBIDDEN F, WRITES F; NULL P) |
| enter153b-unsuppressed-both (visit 3 rendered without suppression: its first row ip22) | NOT PROVEN (LANDING F (b), PATTERN F (a)(b)) |
| 154-after-153b-both (a 154 harness row after visit 3's first row) | NOT PROVEN (LANDING F (b) alone) |
| last-place-harness-both (a harness row in 153 after ip1077) | NOT PROVEN (LANDING F (c) alone) |
| end-log-row-real-151-F (every F run's synthetic `end` row names 151) | NOT PROVEN (LANDING F (c) alone) |
| end-real-151-F (every F run's cut row at fld 151; `off` in 31244) | NOT PROVEN (LANDING F (d) alone) |
| end-boundary-residue-both (an `r` row in place 151 before its ip22) | NOT PROVEN (LANDING F (d) alone) |
| end-row-missing-one-S (one S run: no row in 151, `off` in 151) | PROVEN (S 2 of 3); that run A-NOEND |
| suppressed-pattern-differs-F (every F run: visit 3's ip138 emitted) | NOT PROVEN (STATE F (a), PATTERN F (a)(b)) |
| c-n2-F (every F run: visit 3's ip138 `c` row n 2) | NOT PROVEN (PATTERN F (a) alone) |
| c-missing-ip138-F (every F run: visit 3 without ip138's store, so no `c` row of it) | NOT PROVEN (PATTERN F (a) alone) |
| byte8-repeat-both (a second visit-3 ip890 store 0 -> 0, emitted `same` 1) | NOT PROVEN (PATTERN F (b) alone) -- Byte[8]'s frozen history (the claim critique #10) |
| byte8-race-both (every live end state holds Byte[8] 125) | PROVEN (Byte[8] is not in `end_state`) |
| observed-quiet-page-one-F (one F run VOID V17 with an `observed` quiet_page) | NOT PROVEN (VOID-ASYM F (d) alone) |
| observed-quiet-page-each-side | PROVEN (S 2 of 3, F 2 of 3) |
| observed-after-answer-one-F (one F run VOID V17 with an `observed` after_answer) | NOT PROVEN (VOID-ASYM F (d) alone) |
| control-S (one S run VOID V4 game at [154, 1190, 2]) | NOT PROVEN (VOID-ASYM F (a)) |
| stairs-beat-missing (two S runs: `{"stairs": false}`) | VOID (COVER V; VOID-ASYM P) |
| choice-beat-missing (two S runs: `{"choice128": false}`) | VOID (COVER V; VOID-ASYM P) |
| end-cut (S: rows in 151 past the end) | PROVEN |
| end-state-differs (one covered F run: Bit[3795] 0 live) | NOT PROVEN (STATE F (b)) |
| masked-differs (every F run without its Bit[184] rows) | NOT PROVEN (MASKED F, PATTERN F (a)(b)) |
| mismatched (one F run's member rows name another donor) | PROVEN; that run A-MISMATCH |
| no-start-row (one S run never reaches 153) | PROVEN; that run A-NOSTART |
| join-failure (both: an extra row at 153 e3 t1 ip1742) | NOT PROVEN (JOIN F alone: PATTERN reads only rows that join) |
| trace-without-off | VOID |
| install-changed | VOID |
| predictions-changed | NOT PROVEN (FROZEN F) |

A case's want that the code cannot hold (a co-failure the table did not foresee) is explained at the byte level and
re-registered, never loosened silently (O3 11.6, O4 11.4 C #10 did this).

Units (no session): **guard-of** (each refusal, `branch` included); **witness-of**; **cell-visit** (and the VOID cell:
`[place, sc, visit]` under a visit-scoped table, `[place, sc]` without); **guard-strays** (the window from
`marker_last`; the closing press and the answer's seq span excluded; an unplaceable press by its decision frame; the
2229/2237 shape); **why-void-start** (A-START on a visit-1 error-path row, none on a visit-3 one);
**render-suppression** (the base run's rendered rows: 21 `w` rows before the cut, 4 `c` rows, visit 3's first row
ip57 -- and the SAME event list through the FakeGame's H13 knob gives the same `(k, fld, sid, tag, ip, new, same, n,
last)` sequence: one model, two implementations; and a change then two same-value stores at one site: the change and
the first same-value one emitted, the third counted); **pattern** (`pattern_of` on the base run equals 4.16's tuples
on both sides; on the fake's H13 trace of the builder's route, the same); **trace-summary** (a base S run: the
chain 3/3, writes 12/12, the cut row, the `c` rows; an R-STAIRS stage ending in 154 cut at 154's first row; the same
summary given end FIELDS on an F stage ending in a member is not cut -- the unit's mutant); **state-history**
(Byte[8] `[(153, 0), (154, 125), (153, 0)]`, Int16[11] `[(153, -1), (154, -1)]`, Bit[3795] `[(153, 1)]`); **visit-
entrances** ({153: [325, 316], 154: [304]}; O4's `route_entrances` on the same predictions gives 154 110 -- the reason
O5 has its own); **store-census** (PASS with 6.1's line; mutants each FAIL by name: `dead` without 153 ip41; `inert`
without 32; `error_path` without 154 ip497; an inert entry 3 (instanced at 325); e15 with its caller e32 made non-inert
(the shared proof fails); a registered key inside an inert function); **regions** (PASS; mutants: 153.e28 dormant
(instanced at 325), 153.e23 exit (instanced at no route entrance), 153.e26 role exit, 154.e9 missing, a dormant region
whose `entrances` omit 316); **goals** (PASS with the contour line; mutants: `closed_tris` empty (no route), the goal
at (-1700, 900) (off the floor), `until` x_le -1800 (false at the goal), no `start`, the contour required at x <= -1500
(fails: the crossing is at ~-1479), and on a synthetic mesh a tri whose only vertex at y <= -450 lies at x -1200 and
whose edge crosses -450 at x -1050 -- (d) FAILS by the edge crossing, which the first design's vertex-and-centroid rule
passed (the claim critique #11)); **route-pins** (PASS; mutants: a pin's text changed, mes 127 without the marker, 127
with a `[TIME=`, 128 without `[IMME]`, 128's pick on both lines, 141 without the pick's branch marker, 129 holding it);
**build-pins** (O5's route members on a synthetic three-member build: an extra byte changed in member(153)'s e3
t1, a `PreloadField` operand remapped, an in-chain `Field()` left unremapped: FAIL each); **keys offline mutants** (a
write's value, the `:=var` rvalue `B_SYSVAR[8]`, a chain `off` + 1, `start_first`'s target, a dead site's value,
`start_music` at ip138); **p-donor-log**, **p-launch** (O4's units with 151/153/154); **p-settings**, **p-pad**,
**p-override**, **p-engine**, **text-strict**, **input-witness** (O4's units on O5's pinned values).

It prints the summary columns (FROZEN COVER FORBIDDEN VOID-ASYM START NO-SC CHAIN RESIDUE WRITES NULL STABLE LANDING
CHOICE WALK PATTERN MASKED STATE JOIN) and "N/N cases as registered", exiting 1 on any miss. `stray_answer` has no O5
unit: O5 does not call it, and A0's pytest pins O4's strings (the claim critique #14).

---

## 9. Build order (three parts; no deploy, no game, no `tools/play.py`, no full suite)

Run pytest from `ff9mapkit/`, the study scripts from the worktree root. The harness tests run in REAL TIME (the
FakeGame loops on a thread): run the named `-k` selections, never many at once, and the whole file only where a PART
says so, alone. A SKIPPED test is not a pass: every required pytest run reports 0 failed and its skips/xfails exactly
the PART's baseline's (taken before the PART's first change); a skip for missing templates is fixed with `py -m ff9mapkit
extract-templates` and the run repeated. **Load-robust tests** (O4 lost two nightly runs to load flakes): a test that
drives a long route on the fake re-runs its run (at most 2 more) when, and only when, it ends in a DRIVER class a
starved harness can cause (V13 budget; V17 "landing unseen" / "did not land" / "could not be placed" / "never armed" /
a stray in the guard's window; V7 by a timed-out walk), asserting the class on each discarded attempt -- a GAME class
(V2, V4, V14, V19), a V13 of outside input, the other branch or a gone choice, or a wrong verdict is never re-run;
every race is reproduced by a deterministic stall (a wrapped call), never by real starvation; waits are judged on the
GAME clock (`_choice_left`), and the quiet cap scans the ring before it judges (on the engine its clock is a wall
clock, 0.2 #17); the fake's loop runs at most 4x its `render_fps`. A failure that passes on an immediate
re-run of that test alone is a timing flake: named in the commit message, never ignored. Commit on the branch when a
step is green, one step per commit, each message ending with "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>".
Write non-ASCII files with Python (utf-8) or the Edit/Write tools; frozen JSON and baselines are LF (`-text`); a
Windows path inside a Python string is raw or escaped.

### PART A -- the regression gate extended to O4 (baseline FIRST), then the shared opt-in changes
1. **A0: the O4 gate and its baseline, FIRST.** Extend `segment_regress.py` (1.4: G0''' `--capture-o4` with its
   two-readings rule and refusals; G22-G25; G21 over the union of `sources`; `--rebaseline-source` over both baselines;
   `FAKE_PINS_O4`; `REQUIRED_TESTS_O5` empty; `_missing()`; the module docstring gains G0''', G22-G25 and says G24 is
   O4's VOID-path baseline) with `test_segment_regress_o4_pins_join_the_union` (pure: G21's checker over two
   baselines on temporary copies -- a pinned O4 machine-beat method edited FAILS naming it; a re-baseline row for an
   O4-baseline name passes; a name pinned in both baselines is refused at capture; into `REQUIRED_TESTS`) and
   `test_segment_stray_answer_keeps_o4s_strings` (pure: every outcome of `stray_answer` -- a stray page press, `choose`'s
   Confirm on Yes, a Confirm with no accepted event, none (V2) -- each `v`, `by`, `presses` and FULL `why` string
   asserted equal to LITERALS captured from the function at the branch head, before any change:
   `o4_dryrun.unit_stray_answer` compares `v` alone and G19 substrings, so nothing pinned the strings -- the claim
   critique #14; into `REQUIRED_TESTS`). Run `py studies/story-trace/segment_regress.py --capture-o4`, and commit
   `research/o4_regress_baseline.json` with its `.gitattributes` line before any other code change. Then `py
   studies/story-trace/segment_regress.py` reads G1-G25 (G21 over both).
2. **A1: S12 and S13** (`witness_of`, the run-wide poll; `cell(..., visit=)`, `go()` passing `self.at + 1`, the
   table's `visit` check; `self.visit_cells` and the `[place, sc, visit]` VOID and `observed` cells) with their five
   tests (1.2). Break for each: S12 -- poll only under the Chanbara policy; S13 -- ignore the `visit` key (the revisit
   runs the step: V7 driver, not V4), or key the VOID by `[donor, sc]`.
3. **A2: S11** (`Session.choose_landed`, the dialog-section catch refused as a landing) with its six tests (1.2).
4. **A3: S10** (`guard_of` with `branch`, `_Drive.gd`, the guarded press rows, `guard_note_choice`, `guard_page` with
   (o)-(iv), the hold-off from the last press of any kind, the re-arm, `guard_quiet_tick` scanning first and V13,
   `guard_strays`, `guard_stray`, the `guard` row and its judgment, rule 6's verified answer under the guard;
   `stray_answer` NOT edited) with its twelve tests (1.2).

**PART A REQUIRED-GREEN** (after A0, and again after A1, A2 and A3):

| Command | Expected |
|---|---|
| `py studies/story-trace/segment_regress.py` | exit 0; G1-G25 each PASS (G21: every re-baseline row named in its commit; none expected in PART A) |
| `py studies/story-trace/o1_dryrun.py` | exit 0; "16/16 cases as registered" |
| `py studies/story-trace/o2_dryrun.py --predictions studies/story-trace/o2_predictions_v1.json` | exit 0; "86/86 cases as registered" |
| `py studies/story-trace/o3_dryrun.py --predictions studies/story-trace/o3_predictions_v1.json` | exit 0; "102/102 cases as registered" |
| `py studies/story-trace/o4_dryrun.py --predictions studies/story-trace/o4_predictions_v1.json` | exit 0; "103/103 cases as registered" |
| `py studies/story-trace/o4_castle.py --analyse C:\gd\Dream-World-IX\.harness-runs\20261002-091051-story-o4 --predictions studies/story-trace/o4_predictions_v1.json` | exit 0; `VERDICT: PROVEN`; the archived `o4_report.txt` byte for byte |
| `py studies/story-trace/o4_castle.py --offline-check --predictions studies/story-trace/o4_predictions_v1.json` | exit 0; 4 PASS (0.2 #12) |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "segment"` | all passed, 0 failed, 0 skipped (A0's two; A1's five after A1; A2's six after A2; A3's twelve after A3) |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o4_ or fake_chanbara or fake_keyon"` (after A3) | all passed, 0 failed, 0 skipped: O4's tests untouched by S10-S13 |

### PART B -- the FakeGame for O5's route, then the driver's O5 tests
1. **B0:** the PART's baseline of the whole `tests/test_harness.py` (passed / xfailed / skipped), run alone, from this
   worktree with the templates extracted. Expected: the branch point's count (measured before A0 and recorded in A0's
   commit message) plus PART A's 25 new tests; any other difference is explained before B1.
2. **B1: H13, H14, H15** (`fakegame.py`): `story_suppress` in `_story_store`/`_story_start`/`_story_stop` (each a G21 pin
   from A0's O4 baseline: re-baselined by name with its reason in this commit); `_VisitBeat` with the step vocabulary,
   its own `publish` (the group `""` after a choice closes), the gated choice (opening, ready-lag, `[IMME]`), its
   `bodies` and the stairs step; `_next_beat`'s and `_start_machine`'s `"visit"` dispatch (re-baselined); H15's knobs;
   and the twelve fake tests of 3.1-3.3, each with its break. No existing test's fake changes.
3. **B2: the O5 route builder** (`_o5_route` and the fixture registration, test-side, 3.4) and
   `test_fake_visit_route_plays_to_151_unattended` (a scripted player, not the driver: the builder's four visits
   play to "151" with a director pressing Confirm on every page, Down + Confirm on 128 and walking the stair straight
   west; the trace with `story_suppress` holds exactly 4.16's pattern).
4. **B3: the driver on the fake** -- O5's predictions on the fixture's fields (`_o5_pred`: the cell (30820, 1190,
   visit 1), the guard, the witness stub, `side_ends` {S: [30810], F: [31244]}, the members). Tests (S at 60 fps mean
   ticks, F through the members at 31 fps quantized where named; `wait_scale` 0.25):
   - `test_o5_drive_walks_the_stairs_and_answers_her_face_on_the_fake` -- S and F: beats `stairs` and `choice128`; the
     step row `done`, `lost` x <= -1100; the `guard` row (armed, open at or before 128's first sample, `strays` [],
     `branch` "pick", verdict "ok"); the choice row index 1, `took.landed`, `selected_before` 1; with the trace and
     `story_suppress`: `pattern_of` equal to 4.16 (visit 3's first emitted row ip57, four `c` rows of place 153), the
     end row 151 ip22 (31244 on F), no A-MISMATCH; `end_state`; with `forbid_live` True no forbidden row. Break: drop
     S11 (a blind `choose`).
   - `test_o5_drive_guard_closes_the_stray_press_race` -- a stale read right after 127's closing press (a wrapped
     `Session.state` returning the previous document once) plus a 1.0 s send stall on the next press: with the guard,
     no press decided on the stale sample, the run covered; with a mutant guard keyed on wall time the stale press
     lands on 128 (path 0): V17 by `guard_strays` from `marker_last`; and a rule-7 press on 126, decided on its closing
     sample and stalled until it closes 127 (a wrapped `g.press`): 127's close-tween sample never pressed, V17 "never
     armed", never covered. Break: no page-once (plain rule 7), or a hold-off on the marker's own presses only.
   - `test_o5_drive_choose_landed_repress_when_128_drops_a_confirm` -- `confirm_deaf` 1 (the ready-lag frame's case):
     the first Confirm taken and nothing hidden, the second lands; one choice row; verdict "ok". Break: a blind
     `choose` (the re-ask reads V2 by the game).
   - `test_o5_drive_unlanded_answer_is_the_drivers_v17` -- `confirm_deaf` 5: V17 driver after 3 Confirms. Break: count
     it answered (V2, game).
   - `test_o5_drive_outside_cursor_move_is_v13` -- `cursor_to` after the select: V13 (driver), the trace's ip1741 0; a
     stub witness reporting input at 128: V13 with an `input` row; the answer's accepted event withheld from
     events.jsonl (a wrapped `g.channel.events`): V17 "could not be placed", never V13. Break: trust the logged index,
     or read a missing `selected_before` as off the pick.
   - `test_o5_drive_the_branch_page_witnesses_the_answer` -- `cursor_to` `{"at_confirm": true, "index": 0}` (a move no
     sample shows: `selected_before` 1, the game takes 0): the first page after the answer is 129, V13 (driver), never
     covered; `store_override` {1741: 0} (a fork that stores a constant): 141, verdict "ok", covered -- CHOICE (c)'s to
     judge. Break: no branch judgment (the first covers with ip1741 0).
   - `test_o5_drive_control_off_the_cell_is_v4` -- `grant_at` in 154: V4 game at [154, 1190, 2]; at 153@316: V4 game at
     [153, 1190, 3] (S13). Break: drop `visit` (the step runs at 316: V7 driver), or key the VOID `[donor, sc]`.
   - `test_o5_drive_side_scene_is_one_interrupt` -- `side_scene_at` 5: `interrupted` once, the pages, the re-grant,
     then `done`; two: V7 driver. Break: `interrupts` 0.
   - `test_o5_drive_back_door_is_the_drivers_v11` -- a mutant table walking east into e28: V11 driver, the step row's
     `door` 153.e28 and `landed` "150"; its post-landing rows backed. Break: e28 registered `dormant`.
   - `test_o5_drive_never_reaching_the_contour_is_v7` -- `no_contour`: `failed` twice, V7 driver.
   - `test_o5_drive_fork_landing_in_real_151_is_v19` -- F with `land_real` on the last `field`: V19 game.
   - `test_o5_drive_page_in_the_quiet_window_is_v17_observed` -- a NON-marker page queued between 127's going and 128:
     V17, an `observed` row quiet_page.
   - `test_o5_drive_glitched_sample_rearms_the_quiet_window` -- the dialog-section catch shape returned once while 127
     is up (a wrapped `Session.state`): the window opens, re-arms on 127, 127 pressed again past its hold-off, the run
     covered, no `observed` row. Break: every page in an open window `quiet_page`.
   - `test_o5_drive_quiet_cap_survives_a_read_stall_on_mtime` -- the fake on `publish=("mtime",)` (no `rt`) and a 5 s
     READ stall across 127 -> 128 (a wrapped `Session.state` sleeping once): 128 answered, covered, never V13 or V14.
     Break: judge the cap before the ring scan (the driver critique #1).
   - `test_o5_drive_no_choice_within_the_cap_is_v13` -- `gap_ticks` 600 at `quiet_cap_s` 2: V13 driver. Break: V14
     game.
   - `test_o5_drive_guard_window_opens_on_128s_first_sample_at_31fps` -- F at 31 fps quantized, `gap` 1: with a 0.2 s
     READ stall right after 127's closing press is acked (a wrapped `Session.state`), the ring's first sample without
     127 is 128's own -- `open_frame` == `choice_first` -- and the run is covered; with `gap` 2 and no stall,
     `open_frame` < `choice_first`, covered. Break: a strict "before" (the driver critique #2).
   - `test_o5_drive_choice_gone_unanswered_is_v13` -- `stray_confirm_at_ready`: V13 (driver), no `observed` row, no
     press of the driver's in the window; with a mutant driver's Confirm landing on 128 first: V17. Break: game-observed.
   - `test_o5_drive_reask_after_a_verified_landing_is_v2` -- `reask`: V2 game at [153, 1190, 1], a `guard_stray` row
     kind choice_reask. Break: O4's `encore_stray` shape (V17 on the answer's first Confirm).
   - `test_o5_drive_stop_page_in_the_start_is_v5_driver` -- `error_window` {1: 2}: V5 driver at [153, 1190, 1], nothing
     pressed; {3: 2}: V5 game at [153, 1190, 3].
   - `test_o5_drive_climbs_the_real_stair_on_the_fake` -- the fake's floor `PlayerWalkmesh(stock 153, closed=the 33)`
     with `clearance` 80 and `height_at` from the real mesh; the driver's `floor_for` the same: the walk from (1105,
     -78) meets the contour at x <= -1284, the evidence holds. Reads the install (a skip-with-warning without it: a
     skip fails G26).
   In this commit every `test_o5_*`, `test_fake_visit_*` and `test_fake_story_suppress_*` name goes into
   `REQUIRED_TESTS_O5` and G26 joins the gate.
5. **B4:** the whole `tests/test_harness.py` alone: B0's counts + every new test passed, B0's xfails, 0 skipped, 0 failed.

**PART B REQUIRED-GREEN:**

| When | Command | Expected |
|---|---|---|
| B0, and B4 | `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore` (alone) | B4: B0's counts + every new test passed, B0's xfails, 0 skipped, 0 failed |
| after B1 | `... -k "fake_visit or fake_story_suppress"` | 12 passed (B2: 13), 0 failed, 0 skipped |
| after B1-B3 | `... -k "o1_ or o2_ or o3_ or o4_ or segment or fake_"` | all passed, 0 failed, 0 skipped |
| after B3 | `... -k "o5_"` | 20 passed, 0 failed, 0 skipped |
| after every B step | `py studies/story-trace/segment_regress.py` | exit 0; G1-G25 PASS (G21: each re-baseline row named in its commit), G26 from B3 |

### PART C -- O5 itself
1. **C0: measure, read-only.** From the worktree, on O4's build (`C:\gd\_ns_playtest\o4\build`, never written): the
   route members' byte diffs against their donors, per language (O5-BUILD's pins), and the chain's `campaign.toml`
   (route members 31244/31245/31246 -- anything else STOPS PART C until the predictions are re-derived). No commit (the
   numbers go into C1's `o5_forks.json` `built.measured`).
2. **C1: `o5_hallway.py`** (1.3, sections 4-6: the draft, `why_void` with the visit-1 A-START, the checks LANDING,
   CHOICE, WALK, PATTERN, the offline checks with the route pins, O5-CENSUS per entrance, O5-REGIONS, O5-GOALS, the
   preflight extras, `trace_summary`, the CLI), `o5_forks.json` (6.4), the `.gitattributes` line for
   `o5_predictions*.json`. Tests (into `REQUIRED_TESTS_O5`): `test_o5_hallway_draft_reads_the_chain_from_campaign`;
   `test_o5_hallway_freeze_refuses` (each refusal of 7.3); `test_o5_hallway_route_builder_matches_the_keys` (the
   test-side builder's stores == the draft's writes, chain, masked and start rows, and its H13 trace's `pattern_of` ==
   the draft's `pattern`); `test_o5_hallway_census_proves_inert_per_entrance` (a synthetic Main_Init instancing an
   entry at 316 only fails the proof at 316; e15's shared proof); `test_o5_hallway_regions_roles`;
   `test_o5_hallway_goals_contour` (synthetic mesh: a route that never reaches the contour FAILS (c); a tri whose
   y <= -450 part reaches x > -1100 only at an edge crossing FAILS (d), which the vertex-and-centroid rule passed);
   `test_o5_hallway_pattern_check` (PATTERN (a) on a `c` row's n and on a missing one, (b) on an extra same-value row
   and on a sequence one visit short; the 4.16 tuples pass on both sides); `test_o5_hallway_why_void_scopes_a_start_
   to_visit_1` (an error-path row of 153 in visit 1: A-START; the same in visit 3: no A-START);
   `test_o5_hallway_preflight_verdicts` (P-DONOR over 151/153/154, P-TEXT3 strict, no P-GATE row).
3. **C2: `o5_dryrun.py`** -- every case and unit of section 8 as registered, O3's EXACT `case()`. G27 joins the gate with
   `O5_DRYRUN_FLOOR` = the count C2 prints; `test_o5_hallway_trace_summary_cuts_at_end_places` lands here (it reads the
   dry run's renderer, O4's C2 #11).
4. **C3: `o5_rehearse.py`** + `--rehearsal-report`. Tests (every one with `warp_arrive_control` False and the engine's
   `soft_reset_ui`): `test_o5_rehearsal_plumbing_on_the_fake` (R-STAIRS: the record holds every 7.2 section, the race
   margin to 128's readiness, 128 as published, the per-hold slides/pushes/stalls, the guard row, `end_run`'s rows);
   `test_o5_rehearsal_walk_void_stops_mid_walk_on_the_fake` (R-WALK-VOID: the wrapped `g.send` raises before the first
   `hold` sent at x <= -700 -- the walk had begun, past the spawn's calibration --, no `hold` step in steps.jsonl after
   the raise, `recover-warp` 4600 and the title; break: a timer around `route_to`, which stops before the walk);
   `test_o5_rehearsal_smoke_sends_no_storytrace_on_the_fake` (F-SMOKE: three pairs, each with its own entrance and SC,
   each member's object sids compared with its twin's measured set and the player never in either, no `storytrace` step
   executed);
   `test_o5_rehearsal_fpass_runs_untraced_to_the_member_on_the_fake` (F-PASS: no `storytrace` step, `forbid_live`
   False, reached "member(151)"); `test_o5_rehearsal_stage_ids_follow_the_chain`.
5. **C4: the O5 section in `PLAN.md`** -- the question, the segment, the sides and their ends, the stored choice and the
   guard, the walk, the suppression pattern and its scope, the checks, "draft: rehearsals pending, freeze pending", "a
   US session" in its heading. The brief's milestone line (CLAUDE.md section 10) is left as it is.

**PART C REQUIRED-GREEN** (after each of C1-C4, as far as it exists):

| Command | Expected |
|---|---|
| `py studies/story-trace/o5_hallway.py --offline-check` | exit 0; "predictions: the draft"; "chain: member(153) 31245, member(154) 31246, member(151) 31244"; 6 PASS -- O5-BUILD (140 files, every language its own donor's; the route members' diffs exactly their in-chain Field() operands), O5-KEYS (6.1's line: 53 route pins, the mes pins with [IMME] and the branch markers), O5-TEXT (block 3: 7 byte-equal of 7), O5-CENSUS (6.1's line), O5-REGIONS (6.1's line), O5-GOALS (the step, the route length, the contour crossed at ~(-1479, 529), the evidence sound ON THE CONTOUR: tris 53 and 56, x -1722..-1403) |
| `py studies/story-trace/o5_hallway.py --preflight` | exit 0, ALL GREEN (P-MANIFEST, P-DEPLOY, P-EB, P-FLOOR, P-STOCK, P-TEXT3, P-RECOVERY, P-DONOR, P-SETTINGS, P-PAD, P-OVERRIDE, P-ENGINE) -- or the exact failing line reported to the lead |
| `py studies/story-trace/o5_hallway.py --draft` | exit 0; the draft JSON: `side_ends` {"S": [151], "F": [31244]}, `visits` [153, 154, 153], the guard, the witness, `engine` the pinned sha, `rehearsals` [] |
| `py studies/story-trace/o5_dryrun.py` | exit 0; "N/N cases as registered" (from C2) |
| `py studies/story-trace/segment_regress.py` | exit 0; G1-G26, and G27 from C2 |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o5_ or fake_visit or fake_story_suppress"` | all passed, 0 failed, 0 skipped, every `REQUIRED_TESTS_O5` name among them |

Then the lead's sequence (7.1-7.4): `--preflight`, the rehearsals, the freeze checklist, `--freeze` (v1), the session.

---

## 10. Open risks (what only the game can settle)
1. **The grant and the walk** (F1): the grant position is the bytes' (stage 1's Walk(1105,-78)); the loss sample's
   position and latency (the contour, the teleport or the climb) are unmeasured; the stair's slopes (0.85-0.93) and wall
   contacts on the curve are unwalked by the harness (the harness has never walked a stacked field: 153 is the first);
   the route passes the stair-foot corner at 78 u (0.2 #21). A walk that stalls on the stair is V7 (driver) and
   re-runs, a first `failed` attempt is re-run inside the step; F1 STOPs a systematic failure, F15 adds the clearance.
2. **The race and 128's publication** (F2, F3): 127's type-out ([SPED=2]) and the gap's animation remainder (e31 ip669)
   are unmeasured; 128 has no type-out (`[IMME]`, 0.2 #14), so its margin is ~0.25-0.3 s, smaller than first designed;
   128's options may publish with the first line short its first character (O1) or intact (O4): the rule matches either.
   A guarded stray is V17 (driver), never a finding; F2 decides the fallback.
3. **The suppression pattern in game** (F4): derived from the sink's source and supported by story-o2's revisit (its
   five `c` rows identical in six runs); R-FULL is O5's first measurement. A different pattern changes O5-PATTERN's
   tuples, LANDING (b)'s re-entry row and the counts -- re-derived at the byte level before the freeze, never loosened.
4. **s62's VIB fix on member(153)** (F14): never exercised in game; F-PASS runs it before the freeze. A throw aborts the
   frame (dropped stores): F-PASS STOPs before the session ever sees it.
5. **The [TIME=20] [NFOC] windows under Confirm** (F8): expected inert (O4's 150).
6. **The end-state race** (F5): Byte[8] is out of the claim; the live read of the other nine stays stable through 151's
   prologue (equal values).
7. **Recovery from mid-walk** (F7): `end_run`'s warp from 153 with control held is unmeasured (the same FieldHUD as O4's
   fight); R-WALK-VOID proves it.
8. **The objects** (F12): Blank is the floor's one body (r 176, >= 392 u off the route) and may deflect the "up"
   calibration probe (a one-sided axis, expected); e9/e11/e31 are walk-through (flags 14), published `shown` False.
9. **A pad or a hand at the machine** (F11): the witness polls the whole run between blocking calls; input shorter than
   a gap is unseen. At the choice it is closed twice: `selected_before` catches a cursor moved before the answer's last
   published sample (S11), and the branch witness catches one moved after it -- the game's own branch page (0.2 #20).
   Left: a 128 gone with no press of the driver's is V13 (the witness's blind spot), never a finding.
10. **The shared install**: another session's deploy, a re-wired New Game or an engine rebuild mid-session is A-INSTALL
    (6.3); the lead re-runs `--preflight` on the session's own launch (G1).
11. **The agent's dialog-section catch** (F11; 0.2 #18): one glitched publication is survived by S10 (re-arm) and S11
    (no landing on it). A publication in which BOTH the dialog and the menu sections throw (choice null and group null)
    while 128 waits would still read as its close, and the still-up 128 then as a re-ask, V2 by the game: two independent
    try/catch sections over UI singletons that live through the choice, failing in one publication -- not closed; F11
    records the single-section rate.

Closed by the bytes or the source (no longer open): the end row's emission (0.2 #1); the revisit's suppression (0.2 #2);
the evidence's soundness (O5-GOALS (d), on the contour: 0.2 #22); choice 128's cursor (ETb.cs:100-103) and its lack of
a type-out (0.2 #14); Blank's collision (0.2 #19); Brahne at 110 (shown, size 1, the defined
player, no `Map.Bit[158]`: no control); no SC rung, no battle, FMV, ATE or naming before the cut; every route `Field()`
retargeted (O5-BUILD).

---

## 11. Critique log

### 11.1 The research critic's twelve
Each re-checked in the bytes or the engine source; none disproved.

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| 1 (major) | The chosen end row does not exist: the sink suppresses revisit prologue stores; FakeGame does not model it. | StoryTrace.cs:101-140, :374-401, :540-557; the stock 153/154/151 prologues; segment_trace.py:127-136 | ADOPTED with decision 1: candidate 3's end row 151 e0 t0 ip22 IS emitted (a new site: 0.2 #1); the revisit's pattern derived (0.2 #2, 4.16) and its first emitted row pinned (LANDING (b), start-scoped); H13 models the sink in the fake; the dry run's renderer models it; the counts recounted (21 + 4 rows, 15 keys); the scope line names the compared suppressed stores (5.4). |
| 2 (major) | The quiet window alone does not close the race: page-once is needed. | segment_drive.py rule 7, `quiet_tick`, `policy_page`; 153 e31 t1 ip663-670, e3 t1 ip1713-1724; Dialog.cs:798-808 | ADOPTED (S10): page-once keyed on the window's RAW and judged on GAME frames, the quiet window from the first sample without the marker, closed by the published choice; F2 measures the margin; the fallback designed (2.5.7). (The residual first named here could not happen; the real one and its closer, the hold-off from any press, are 2.5.5 -- 11.4 #2.) |
| 3 (major) | Candidate 3 is the cleaner primary. | rule 1, the live scan, `end_row`, `Segment.cut` | ADOPTED (decision 1): no `end_visit` code at all; O6 starts by a raw warp into 31244 at 110. |
| 4 (minor) | Part of the end state is written at the arrival; Byte[8] races 151 ip315. | 151 e0 t0 ip274-315 | ADOPTED: Byte[8] out of `end_state`, its end value the trace's last pre-cut write, frozen by O5-PATTERN (b) (first written "STATE (a)", which compares runs with run 0 only -- 11.4 #10); Bit[3855]/[3854] not registered; the byte8-race-both PASS case. |
| 5 (minor) | The emitted row pattern is start-dependent too. | StoryTrace.cs:383-401; field 70's override prologue | ADOPTED: the scope line (5.4), LANDING (b)'s pin named start-scoped, "never reuse O5's row expectations against a chained true-run trace". |
| 6 (minor) | `choose()` is fire-and-forget; a re-ask after an unlanded answer reads V2 by the game. | session.py `choose`, `_take_default_choice`, `_choice_left`; Dialog.cs:798-808 | ADOPTED (S11): `choose_landed`, the driver's own V17 for an unlanded answer. (First written with "`settle_s` frozen above 128's measured type-out"; 128 has none -- `[IMME]`, 11.3 #4 -- so `settle_s` is O1's 1.0, F6.) |
| 7 (minor) | The forbidden schema cannot express a value or a count; a `cause: "choice"` pattern in 153 backs the route's own answer. | segment_drive.py FORBID_KEYS, `backing` | ADOPTED: no `choice` pattern; the pick is WRITES-exact and CHOICE (a)-(c) -- (a) counts the site's `c` rows too. (First written "since a same-value repeat is suppressed": wrong -- after ip1741's change a second 1 -> 1 store is EMITTED, `same` 1, and only a third is counted; (a)'s one-`w`-row clause sees the second, its no-`c`-row clause the third. 11.4 #8.) |
| 8 (minor) | The preflight drops O4's P-OVERRIDE and the rest. | the live override (1424 B, 2ce8887e) | ADOPTED: O4's set carried (6.2) but P-GATE and P-TEXT2 (11.2 #1). |
| 9 (minor) | The stock event names are wrong. | FF9DBAll.Events.cs:10, :13, :24 | ADOPTED: the EVT names in every `what` string and in this design; the kit's member names come from the scene names (4.1). |
| 10 (minor) | The outside-input witness runs only under the Chanbara policy. | segment_drive.py `go`, `poll_witness`; 153 e3 t1 ip1741 | ADOPTED (S12) and NARROWED at the choice: the answer's `selected_before` (S11) catches a cursor moved between the select and the answer's last published sample, which a 50 ms witness can miss, and the branch witness one moved after it (0.2 #20; 11.4 #13). |
| 11 (minor) | s62's VIB fix would get its first in-game exercise in the session. | HonoluluFieldMain.cs:93-104; 153 e3 t1 ip2443-2453 | ADOPTED: F-PASS (untraced, before the freeze, 7.1, F14). |
| 12 (minor) | Corrections: hidden objects are published; Blank is a body disc only; the re-plan numbers; the step lacks `start`. | HarnessAgent.cs:2321-2361; `wm153.py`, `route_check.py` | ADOPTED: `start` [1105, -78] in the step; F12 records the objects; O5-GOALS (c)(d) carries the contour and the evidence's soundness on the bytes. (First misread "a body disc only" as "no player collision"; Blank IS a body, r 176 -- 11.3 #5. And (d) was first stated on vertices and centroids, false on this mesh -- 0.2 #22, 11.4 #11.) |

### 11.2 Where this design reads a decision's letter differently (each said, none relitigated)
1. **Decision 6's preflight set** names O4's; P-GATE (the +30% witness for member(64)) and P-TEXT for block 2 are O4's
   fight and fields alone -- carried, they would gate O5 on facts its route never reads. Every other check is carried.
2. **Decision 1's "verify against the s88 suppression"**: verified from the source (0.2 #1); R-FULL measures it (F4).
3. **Decision 3's "page-once on the marker page(s)"**: page-once applies to marker pages only; every other page keeps
   plain rule 7 (it carries a `seq` for the attribution). The hold-off keys on the window's RAW text (O4 keyed the
   rendered text, which can grow while 127 types) AND on the driver's last press of any kind (2.5.5; 11.4 #2).
4. **Decision 3's "re-ask after the driver's own unlanded answer is the driver's V-class"**: V17 (driver), the class O4
   gave "the driver's input not proven the frozen play"; V13 is kept for outside input (the cursor read off the pick,
   the other branch's page, a gone choice no press of the driver's explains). A re-ask after a VERIFIED landing is V2
   (game) outright (11.4 #6).
5. **Decision 5's "Model it in the FakeGame"**: H13 is the sink's rule per site per epoch, both flush points, the
   site's fld/don on `c` rows; the published `suppressed` counter is left at 0 (no reader) so `_publish`, a G21 pin,
   stays untouched.
6. **Decision 7's "the 127 -> 128 race's frequency"**: measured passively in every guarded run (the race margin); an
   unguarded R-RACE is optional, by name.
7. **Decision 8's shared changes**: S13 (visit-scoped cells) is an addition no decision names -- without it a control
   grant at the revisit is the driver's V7 and invisible to VOID-ASYM (a) (0.2 #15). It is opt-in and O1-O4
   byte-identical.
8. **Decision 9**: the lead's merge of master meets three conflicts by construction (0.2 #16): `source_pins.json` (both
   sides append rows: keep all, per name in head order), `REQUIRED_TESTS_O3` (keep both additions), and possibly
   `segment_regress.py`'s neighbouring lines; then the whole gate and `tests/test_harness.py` run on the merged head.
9. **Decisions 3 and 5, after the critiques**: the guard gains the BRANCH WITNESS (0.2 #20) and decision 5's scope line
   becomes a CHECK (O5-PATTERN, 5.3) -- two additions no decision names, the first opt-in under `guard` and the second
   O5's own, both leaving O1-O4 byte-identical. Decision 3's "the fallback is designed but NOT frozen" stands; the
   fallback has no branch witness and says so (2.5.7).

### 11.3 The driver-robustness critique (eleven)
Each re-checked in the engine source, the bytes, the walkmesh, the harness or an archive; each adopted, one with a
correction (#5).

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| 1 (major) | The quiet cap can VOID a correct run as V14 (game): the engine publishes no `rt`, so its "game time" is state.json's mtime -- a wall clock -- and the cap runs at rule 3, before rule 6 closes the window: a stalled poll meets it with 128 already up, and one such run on one side reads VOID-ASYM (a). | HarnessAgent.cs PublishState :1500-1595 (no clock); segment_drive.py:1393-1402, session.py:8377-8386; O4's rehearsal records `source: mtime`; segment_drive.py:2864-2865 (rule 3's `quiet_tick`), :2886 (rule 6); o4_castle.py:1735-1768 | ADOPTED: the cap first scans the current sample and the ring since `open_frame` (a choice closes the window as `guard_note_choice` does), then is V13 (driver); a fork that never asks 128 is VOID-ASYM (b)'s (v13-cap-all-F); `test_segment_guard_cap_scans_first_then_is_v13`, `test_o5_drive_quiet_cap_survives_a_read_stall_on_mtime` (the fake on `publish=("mtime",)`, a 5 s read stall); 0.2 #17, S10, 2.7. |
| 2 (major) | CHOICE (d)'s strict "opened before `choice_first`" fails correct runs: 128 opens ~2 ticks after 127 is gone and the agent publishes every 2 frames. | HarnessAgent.cs:241; 153 e31 t1 ip669-670, e2 t1 ip799-810, e3 t1 ip1713-1724; O4's rehearsal 20261002-082739 run 1 (decided 2229, acked 2237, the window opened 2237) | ADOPTED: `open_frame <= choice_first` in CHOICE (d), now the backstop of S10's live judgment (11.4 #2); the PASS case choice-open-at-first-both; `test_o5_drive_guard_window_opens_on_128s_first_sample_at_31fps`. |
| 3 (major) | WALK cannot accept a failed first attempt the driver retries. | segment_drive.py:2292-2302 (`failed`, `lost` None), :2490-2494 (the retry); the route's clearance (0.2 #21) | ADOPTED: WALK (a) admits up to `attempts` - 1 `failed` rows (`landed` None, no `door`); (b)'s window for a failed attempt ends at its row's `frame`, and every gap to the next `frame0` is a window; walk-failed-once-both PROVEN; walk-two-failed-both, walk-failed-in-door-both WALK (a) alone. |
| 4 (minor) | 128 is `[IMME]`: it has no type-out, but the margin, H14, a B3 test, F3 and F6 modelled one. | mes 153 #128's source; FFIXTextTag.cs:332, NGUIText.cs:1495, DialogBoxSymbols.cs:584-587, DialogAnimator.cs:43-47, :117-124, Dialog.cs:161-164, :645-650, :787-801 | ADOPTED: 0.2 #14 rewritten (the 0.105 s opening, the ready-lag frame, no type-out; the margin ~0.25-0.3 s); H14's choice gated by state, `typing_s` 0 for 128, `ready_lag_frames`; the opening-drop and ready-lag Confirms tested on the fake; `test_o5_drive_choose_landed_repress_when_128_drops_a_confirm` replaces the type-out one; 127 keeps its type-out; F3 checks that 128's options do not change after readiness; F6's `settle_s` is O1's 1.0; 2.5.5's stated residual withdrawn. |
| 5 (minor) | Blank collides with Zidane; F12's expectation is inverted. | WalkMesh.cs:915-917; e7 t1 ip770 SetObjectFlags(5); DoEventCode.cs:1498-1531; HarnessAgent.cs:2348-2360; e7 t0 ip173, e3 t0 ip218, e7 t1 ip263 | ADOPTED WITH A CORRECTION: `coll` true, `solid` false, `talk_r` 377 -- but `r` = 4 x (20 + 24) = **176**, not 160: SetObjectLogicalSize's second argument is collRad and Zidane's is 24 (the critique summed sizes). 0.2 #19, 2.4, F12, the fake's `bodies`, `test_fake_visit_objects_as_the_agent_publishes_them`; the up probe's one-sided axis expected; e9/e11/e31 are walk-through, not hidden colliders. |
| 6 (minor) | One glitched publication (the dialog section's catch) opens the quiet window, and 127 seen again then reads as a game-observed quiet page: one-sided VOID-ASYM (d). | HarnessAgent.cs:1626-1703 (the catch :1699-1702), :1732-1761 (AppendMenu's own try) | ADOPTED: a marker page in an open window RE-ARMS it; only a non-marker page is game-observed (S10 (ii), 2.5.2; two tests). EXTENDED: the same catch would fake a choice's CLOSE for `_choice_left` (no choice block reads not ready) -- `choose_landed` refuses a read with no choice block while the group still reads `Dialog.Choice` (the engine's close sets it '', Dialog.cs:629, ButtonGroupState.cs:291; S11's new test), and `choice_close` skips such a read (0.2 #18). |
| 7 (minor) | A missing accepted event reads as outside input. | segment_drive.py:3270-3279; HarnessAgent.cs:2443-2455 | ADOPTED: `selected_before` None -> V17 driver ("could not be placed"); V13 only for a value other than the pick (S11); B3's outside-move test withholds the event; v17-unplaceable-one-S PASS. |
| 8 (minor) | R-WALK-VOID's 0.8 s timer expires before the walk; a thread would keep sending holds after `end_run`. | session.py:4394-4421 (`wait_control`, the rate, `_calibrate_clear_of`) | ADOPTED: a wrapped `g.send` raises before the first `hold` sent at published x <= -700, on the driver's own thread; no `hold` step in steps.jsonl after the raise (7.1, F7, C3's test). |
| 9 (minor) | The gap omits e31's WaitAnimation. | 153 e31 t1 ip648 RunAnimation(3387), ip669 WaitAnimation | ADOPTED: 0.2 #14; H14's `gap` default 2 and a knob over 1-10 ticks; F6's `quiet_cap_s` from the measured gap; both ops pinned (4.14). |
| 10 (minor) | F-SMOKE's expected sets include the player, never published. | HarnessAgent.cs:2321 | ADOPTED: each member compared with its stock twin's measured set only (7.1, F13, C3's test); the sets the bytes predict are stated without the player and never compared. |
| 11 (minor) | The stair route hugs the inner wall at the body radius. | measured on stock 153 (the 33 closed, every 5 u): 78.4 u at (-944, 807); 91-93 u along the contour leg; the stair 325-395 u wide, 220-295 u free outside; legs 9.5 and 1 deg off their keys | ADOPTED: R-STAIRS records every hold's slide, push and stall on the last two legs (7.2); F15: any one adds an opt-in step `clearance` (a `route_to` keyword, default None) before the freeze -- at 120 the planner's route is 3273 u, >= 124 u off every wall, the contour at ~(-1523, 558) (0.2 #21); not built unless F15 calls it. |

### 11.4 The claim-integrity critique (fourteen)
Each re-checked as above; each adopted, two with a correction (#2, #11), one through another check (#10), one closed
rather than stated (#13).

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| 1 (major) | No check compares the four suppressed stores; the scope line implied one did. | o2_alexandria.py:1409-1419 (MASKED: names only), :1449-1460 (`suppressed()` drops all four), storytrace.py:815-824 (the digest folds a count into its site's key); story-o2's revisit (five `c` rows, identical n and last in six runs) | ADOPTED: O5-PATTERN, an exact core check -- (a) the `c` multiset (place, sid, tag, off, target, n, last), (b) each visit's emitted sequence (place, sid, tag, off, target, new, same), over the joined script rows of the route places, masked included (5.3, 4.16); measured at F4; c-n2-F, c-missing-ip138-F (PATTERN (a) alone), byte8-repeat-both ((b) alone); every co-failure re-registered (section 8); the scope line says what is compared and what is not (a count's time, its order among the `w` rows). |
| 2 (major) | CHOICE (d) judges the instrument: a Confirm dropped in 128's opening, 127 closed by a non-guard press, `open_frame == choice_first`, or the answer's own re-press or Down fail a covered run; 2.5.5's residual cannot happen and the real one is a 126 press. | Dialog.cs:798-801; segment_drive.py rule 7, :3267-3279 (`row_choose` marks only the last Confirm); session.py:650-703 (sends block until acked) | ADOPTED WITH A CORRECTION: judged LIVE at the first page after the answer (S10 (o): never armed V17; a press in [127's last listed sample, 128's close) beyond the answer's seq span V17), CHOICE (d) its backstop with `<=`. The correction: that window holds 127's OWN closing press whenever the ring has no sample of 127's close tween -- O4's recorded shape exactly (decided 2229, the page gone at its ack 2237) -- so taken literally it would VOID every such run; the closing press (the last page-once press on a marker) is excluded, and the hold-off from the driver's last press of any kind makes it provably the press that went down on 127. 2.5.5 rewritten around the 126-press residual. |
| 3 (medium) | 128 has no type-out; H14 and the sizing model one; SelectChoice's state gating is unmodelled. | as 11.3 #4; Dialog.cs:826-835 (OnItemSelect only in CompleteAnimation) | ADOPTED with 11.3 #4: 128 typing 0 (3.4); `[IMME]` pinned in `route_mes`; the margin restated (~0.25-0.3 s); H14 gates SelectChoice (the opening: Down/Up nothing, a Confirm sets the default; the ready-lag frame; then OnItemSelect); F6's type-out term dropped. |
| 4 (medium) | Instrument artifacts are attributed to the game: `choice_gone` with no driver press (the witness misses taps), a stray window from the ring's first 128 sample, a marker page seen again in an early window. | o4_castle.py:806-830, segment_drive.py:3043-3057 (the witness reads levels between blocking calls) | ADOPTED: `choice_gone` with no press of the driver's in its window is V13 (driver), no `observed` row (observed-choice-gone-one-F becomes the PASS case v13-choice-gone-one-F) -- the game cannot be its cause: member(153)'s e3/e31 bytes are the donor's and no dialog code keys on 151/153/154; the window opens at 127's last listed sample; a marker page re-arms (11.3 #6). |
| 5 (medium) | S13 scoped the table by visit but not the VOID cell: V4 at 153@325 and at 153@316 share `[153, 1190]` and cancel. | segment_drive.py:1976-1977; o4_castle.py:1735-1768; o2_alexandria.py:1285-1287 | ADOPTED: under a visit-scoped table every RouteVoid and `observed` cell is `[place, sc, visit]` (S13; O1-O4 keep `[place, sc]`); v4-visit1-S-visit3-F NOT PROVEN; every O5 case's cell re-written; `test_segment_drive_void_cell_carries_the_visit`. |
| 6 (minor) | `choice_reask` reused O4's encore attribution, which hides a genuine re-ask as V17 after a two-Confirm landing. | segment_drive.py:1332-1333; 153 e2 t1 ip844, ip928, ip1408 (both branches rejoin at stage 23) | ADOPTED: a re-ask after a VERIFIED landing is V2 (game) outright; O5 no longer calls `stray_answer`. HARDENED: the verification itself could be faked by the dialog-section catch (a read with no choice block), turning a still-up 128 into a "re-ask" and a false V2 -- S11 refuses such a read (11.3 #6); the both-sections residual is 10 #11. |
| 7 (minor) | A-START is blind to the visit: a visit-3 error path is labelled the start's. | o3_prima_vista.py:1220-1227 | ADOPTED: O5's `why_void` withdraws an A-START whose row lies after the run's first row of place 154 (1.3); error-path-316-F (V5 game at [153, 1190, 3], no A-START); `test_o5_hallway_why_void_scopes_a_start_to_visit_1`; B3's stop-page test at visit 3. |
| 8 (minor) | CHOICE (a)'s `c`-row rationale and H13's prose misread the sink: a second 1 -> 1 store is emitted. | StoryTrace.cs:383-395 (`SameEmitted` set by a same-value store alone) | ADOPTED: H13's prose ("no SAME-VALUE row"), 0.2 #2, CHOICE (a)'s rationale and 11.1 #7 corrected; choice-second-1741-both is a `w`-row case (CHOICE (a), PATTERN (b)); choice-third-1741-both added (CHOICE (a), PATTERN (a)(b)); H13's test covers a change then two same-value stores. |
| 9 (minor) | STABLE's only mutant is not registered. | section 8 | ADOPTED: extra-key-one-F registered (STABLE F, WRITES F, STATE F, PATTERN F (b); NULL P). |
| 10 (minor) | Byte[8]'s end value is report-only: "held by STATE (a)", which compares runs with run 0. | o2_alexandria.py:1469-1484 | ADOPTED THROUGH O5-PATTERN (b), not a separate STATE (c): Byte[8]'s three rows are frozen entries of their visits' sequences, its last before the cut visit 3's ip890 := 0 (4.9); byte8-repeat-both fails PATTERN (b) alone -- a symmetric deviation STATE (a) cannot see. A STATE (c) would repeat it. |
| 11 (minor) | O5-GOALS (d) samples too few points: the extreme x of a straddling tri's y <= -450 part lies on its edge crossings. | stock 153's walkmesh with the 33 closed (0.2 #22) | ADOPTED, AND A DEFECT FOUND: (d) as first stated was FALSE on this mesh -- the upper stair's open tris 50, 51, 60 and 71 lie wholly at y <= -450 with vertices and centroids at x -460..-866 -- so the offline check would have failed; restated on the contour (every edge crossing of -450 -- only tris 53 and 56, x -1722..-1403 -- at x <= -1100; heights continuous across shared edges; every tri beyond reached only across it) (6.1); the goals unit's edge-crossing mutant. |
| 12 (minor) | F-PASS is an untraced look at the fork before the freeze. | 7.1 | ADOPTED: F-PASS may only STOP the session; any V-class or throw it shows is a finding in PLAN.md; an engine or build change in response re-pins P-ENGINE/P-EB and repeats F-PASS; it never shapes a frozen value (F14). |
| 13 (minor) | Outside input in the answer's last frame stores 0 with `selected_before` 1: indistinguishable from "a fork that stores a constant". | 153 e3 t1 ip1749; e2 t1 ip840/844; e3 t1 ip1899/3430; every Bit[3795] read behind `Int16[2] == 3` | ADOPTED AND CLOSED, not only stated: THE BRANCH WITNESS -- the first page after the answer is the game's own record of the answer it took (Map.Byte[27] := SYSVAR[9] drives the branch; Bit[3795] is read on neither path at 325): 129 (the other branch) is V13, so that input VOIDs the run, while a fork that stores a constant still shows 141 and fails CHOICE (c) (0.2 #20, S10 (o), CHOICE (b), `test_o5_drive_the_branch_page_witnesses_the_answer`); the scope line states what remains. |
| 14 (minor) | "G24 proves" `stray_answer`'s strings; it does not. | o4_dryrun.py:1312-1330 (`v` alone); G19's substring asserts | ADOPTED: `test_segment_stray_answer_keeps_o4s_strings` asserts every outcome's full strings from LITERALS captured at the branch head (A0) -- and O5 no longer edits `stray_answer` at all (its attribution is the new `guard_strays`). |

### 11.5 As built (the implementer appends, PART by PART)
Where the design was silent or wrong, each the smallest correct thing, in O4's 11.4 form; and the review's findings, in
O4's 11.5 form.

#### PART A, as built: where the design was silent or wrong (each the smallest correct thing)
A0 first, resumed: the dead run's WIP (44aaf1e1: G0''' `--capture-o4`, G22-G25, G21 over the union, the two tests, the
`.gitattributes` line -- unrun) was read, run and kept but for one defect (#1); the gate as it stood at the merged head
0acec094 read 20/21 (G7 red on that defect alone), green after it (7b2545b8); the O4 baseline was captured there --
two readings identical, G19 (62), G20 (103/103), G22-G25 PASS, 109 sources -- and committed (762368dc) before any
other code change. The branch point's whole-file count is master 2575495e's own record (tests/test_harness.py -n 6:
770 passed, 1 xfailed); PART A adds 25 tests (the WIP's two included). Nothing in 1.2 or 1.4 was disproved.

| # | Where | The design | As built, and why |
|---|---|---|---|
| 1 | A0, `rebaseline_source` | `--rebaseline-source NAME` looks NAME up in either baseline. | The WIP defaulted `baseline_o4` to the COMMITTED O4 baseline, so O4's own pinned test `test_segment_regress_source_pins_catch_an_edit` -- it passes a temporary O3 baseline alone -- read the real file: FileNotFoundError before the capture, the committed baseline leaking into a test after it. `baseline_o4` defaults to None (the O3 baseline's sources alone: O4's call); the CLI passes `--baseline-o4`. |
| 2 | A0, G19's selection | G0''' pins "the AST sha of every test G19 collects". | `test_segment_regress_o4_pins_join_the_union` (the design's name) holds "o4_", so G19 collects it (62) and the O4 baseline pins it with O4's tests. No G19 name is pinned by the O3 baseline (0 of 62), so `o4_pin_names`' refusal (kept: "refused at capture") did not fire. |
| 3 | S13, `stray()`'s late V11 | "its step row's `visit`". | The cell's visit is the run's position in `visits` (`self.at + 1`, `vcell`), which IS the walk's: `walked` is cleared at every new visit (rule 3) and rule 2 judges before it counts one. The step row's own `visit` is the visit COUNTER, which differs from the position on a stage that starts mid-route. |
| 4 | S10 (iii), the hold-offs | (a) per raw, (b) from the driver's last press of any kind; break "key the hold-off on the text". | Both built, but (b) subsumes (a): every raw (a) holds is held until its press's ack + F, at most `last_ack` + F -- so keying (a) on the text is no observable mutant. The page-once test's breaks are "no hold-off" and "the hold-offs by wall time" (the fake at half speed: 10 ticks of game frames are twice the wall seconds a 30 Hz clock reckons). |
| 5 | S10, `gd["first"]` | Set by `guard_note_choice` (rule 6) and the open window's scan. | Also from the ring every poll (`guard_quiet_tick`'s last step): a guarded choice published and gone between the driver's own polls (a blocking call's reads) still reads as published, so (i) attributes it rather than the run walking on down the wrong branch. The window's opening and its scan run BEFORE that note, so a window armed and not yet open opens on the choice's first sample (`open_frame == choice_first`) instead of closing unopened. |
| 6 | S10 (ii), the re-arm | `open_frame` back to None. | The opening scan restarts from the re-arming sample (`from`): from `armed_frame` it would find the same glitched sample and re-open at once. `armed_frame` stays the first arming (the guard row's). |
| 7 | S10, the VOID strings | 127 and 128 by number. | Shared code: "the marker page" and "the guarded choice"; every phrase the design keys on kept ("page-once did not make", "went down in [", "unattributed input", "the game took the other branch", "no choice read within"). |
| 8 | S10, `guard_strays` | `guard_strays(log, events, steps, lo, hi, *, exclude)`. | As written, `steps` naming each stray's button (an added `button` key). The exclusion is the pure `guard_exclude(answer, closing_seq)` -- the answer's whole seq span and the closing marker press -- so "exclude only the press rowed answer" is a testable mutant. A press with neither a down nor a decision frame counts (fail-closed). |
| 9 | S11 in the driver | `selected_before` None -> V17 "could not be placed: no accepted event". | Same class; the reason says which: no accepted event, or a down frame with no earlier sample publishing the cursor (`row_choose`, O4's and untouched, reads the last ring sample before the down frame -- a dialog-section catch there reads no cursor). After a verified answer `gd["last_ack"]` takes the newest frame read (the answer's presses are acked within it). |
| 10 | S11, `choose_landed` | Skip a "left" read with no choice block while the group reads `Dialog.Choice`. | Bounded: a catch on every read for `timeout` raises HarnessError (V13) -- nothing then says whether the Confirm landed. A landing across a read gap with another window up returns `landed` True, `why` naming it. |
| 11 | S10/S11 tests | A wrapped `Session.state`; H14 the fake's (PART B). | `Session.state` is a property; the seams are the channel's: its observer (the dialog-section catch -- the ring and the read both carry it, only on a frame new to the ring), its `state()` (a stale read, a read stall), its `send()` (a stall's trigger). 127's type-out and close tween, and the gap, are test-side on the fake's ordinary scene (a movie beat is the gap: no dialog, inert to Confirm). Load: the guard tests run the fake at the game's own pace (`fps` 60) and re-run, at most twice, only a run ending in a driver VOID a starved harness gives -- never for the class the test asserts (`_g_run_informative`'s `want`); the S11 tests run it at HALF speed (`CHOICE_GAP_S` 0.3 s of wall time) but the unseen-landing test, which starves its reads on purpose. |

#### PART B, as built: where the design was silent or wrong (each the smallest correct thing)
B0 measured the PART's baseline: the whole `tests/test_harness.py` at `-n 6` (master's recorded mode) read 769 passed,
26 failed, 1 xfailed -- 796 collected, master 2575495e's 771 plus PART A's 25. Every failure passes ALONE, serially (the
25 + 8 items re-run): timing flakes of six real-time fakes at once on this machine (O4 drive tests' "instrument: a read
gap of 0.1-0.5 s", "no MEASURED render rate after 2.0s", wall-clock asserts in walk tests), none in PART A's tests -- so
B4 runs the whole file serially, the design's own command ("alone"). B1 (5eeed41a), B2 (023a51ab), B3 (2b46994d): one
DEFECT in PART A's shared code found and fixed (#13); nothing else in 1.2, 3 or 9 disproved. B4, at 2b46994d (the whole
file alone, serially, 60 min): 828 passed, 1 xfailed (B0's), 0 skipped, 0 failed -- B0's 795 and PART B's 33. The
`-k "o1_ or o2_ or o3_ or o4_ or segment or fake_"` run after B3 read one O4 PREMISE flake while other sessions' jobs
loaded the machine (`test_o4_drive_presses_123_again_when_its_first_press_is_dropped`: 123's first press landed after
its 0.25 s opening, so nothing was dropped; 3 of 3 alone, and B4 passed it) -- O4's, reached by no PART B code.

| # | Where | The design | As built, and why |
|---|---|---|---|
| 1 | H13 | The site table per epoch, `c` rows with the site's fld/don/m. | `don` is kept from the site's creation (`fake.donor` then: EffectiveFieldId of its field); `_story_counts` writes through `_story_row`'s keywords (its `m`/`fld`/`don` overridden, the engine's key order kept). `_poll_arm` (the engine's Reset) is not edited: every `_story_start` clears the table instead -- after a Reset the engine's table is empty, so its Start's EmitCounts writes nothing. `story_suppressed` is cumulative per fake. |
| 2 | H14 knobs | `grant_at` and `error_window` keyed by visit index. | The index needs a knob: `index` (the visit's 1-based position in the route), set by the builder. |
| 3 | 3.4, 153@325 | "choice 128 ... then store ip1741; branch ...". | The ip1741 store is the FIRST STEP OF EACH BRANCH: a step after the choice step would run after its branch; the engine runs ip1741 the tick 128's WindowSync returns, before e2's switch on Map.Byte[27] picks the branch. |
| 4 | H14 windows | Placeholder texts; 127 "types on". | `text`/`raw` keys on page, timed and choice steps (`texts`/`raws` on a pair); a typing window publishes its first character through its opening and a growing share as it types (its raw whole from the first sample). Timed windows are kind "timed": Confirm-inert because the UI takes Confirm on a page or a choice alone. Every window the beat lists carries the type-out state (`_VisitBeat.open`, #9). |
| 5 | H15 `side_scene_at` | "tick n of stage 6". | The n-th MOVING tick of a stage-6 period (a tick he stands somewhere new). Counted from the grant, a scene at tick 5 fires during the driver's settle, before its walk -- no walk would see it as an interruption, and B3's interrupt test would read nothing. |
| 6 | H15 `cursor_to` | after_frames: "n frames after the driver's select". | Once, n frames after the first Down/Up that moved the cursor. B3's test holds the answer's Confirm until a published sample shows the move (deterministic: the select's own re-check would otherwise race it, and a late re-check re-selects). |
| 7 | H15 others | `error_window`, `grant_at`, `land_real`, the back door's exit. | `error_window`'s store is 153's ip97 in any field (154's ip101 is not modelled: its test reads the V-class); `grant_at` holds the script after the grant; `land_real` is `{to: id}`; the builder's back door changes the field 30 ticks after its stores (ExitField's fade: an ESTIMATE). |
| 8 | B2/B3 the pattern | `pattern_of` equal to 4.16. | `pattern_of` is C1's (o5_hallway.py): the tests compare 4.16's tuples BY IP (`_o5_pattern`, test-side: the fake's rows carry ips; `pattern_of` joins function offsets on the stock bytes); C1's `test_o5_hallway_route_builder_matches_the_keys` is where the builder's trace meets `pattern_of`. |
| 9 | H14 (found in B3) | -- | A window a director queues (`_Machine.queue_window` -> `_Machine.open`) lacked the type-out state `_VisitBeat.ui` reads: the AttributeError killed the fake's loop thread mid-run. `_VisitBeat.open` (a subclass method: `_Machine.open`, a pin, untouched) gives every window it. |
| 10 | B3 short route | -- | `_o5_pred(short=True)` / `_o5_route(short=True)`: one visit (30820, then the end), no walk, for the guard's tests that need no stair; the table is kept, so every VOID's cell still carries the visit. |
| 11 | B3 pace | "the fake's loop runs at most 4x its render_fps". | 4x but across the guard's stretch -- 126 listed to the first branch page -- at 1x (`_o5_slow`; 0.5x for the race test): page-once's hold-off, the quiet window and S11's CHOICE_GAP_S are then real wall time, as in the game. |
| 12 | B3 end | -- | The end field gets no `visit` row: rule 1 ends the run before rule 3 counts one (the test asserts visits [30820, 30821, 30820]). |
| 13 | S10 (i), PART A's code -- A DEFECT | "(i) the guarded choice was published and left with no answer of the driver's: `guard_stray("choice_gone")`". | Judged on ANY page once `gd["first"]` was set. With O5's 2-tick gap, 128's first sample enters the ring during 127's closing press's OWN reads; the stale read right after that press (this design's fault model, `test_o5_drive_guard_closes_the_stray_press_race`) then served 127 -- older than 128's first sample -- and (i) read it as 128 gone: V13 "unattributed input" though nobody had answered 128. Fixed in `guard_page`: (i) judges only a page sample NEWER than the choice's first publication (`st.frame > gd["first"]`); an older one goes on to (ii)-(iv), where page-once's hold-off holds the stale marker page off. The live channel never serves a document older than an earlier read (a miss is None, retried), so a live run is unchanged; O1-O4 carry no guard (G1-G25 byte-identical). (o) is left as it is: a stale pre-answer page there reads "neither branch", V17 with an `observed` row -- fail-closed. |
| 14 | B3 race (2) | The wall-time mutant: "V17 by `guard_strays` from `marker_last`". | V13 "unattributed input": the stale press the mutant makes is the visit's LAST marker press, so `guard_exclude` takes it for the closing press. Never covered either way; the test asserts a driver VOID (V13 or V17), the stale sample pressed (two presses decided on it) and 128 answered 0 by it. The late press also waits until 128 takes answers (`until`), so a starved fake cannot let it land in 128's opening. |
| 15 | B3 race (3) | "127's close-tween sample never pressed, V17 never armed". | The engine's 0.09 s tween ends inside the stalled press's own wait, so the loop never reads a 127 tween sample and "never armed" held with or without the hold-off (the hold-off mutant was MISSED). Stretched to about 18 frames (`close_s` 0.28: PART A's 18) -- read by the loop, inside page-once's 20-frame hold-off -- with a premise re-run (at most twice) when the loop read none. A 0.5 s tween outlives the hold-off and the REAL guard then covers: page_once_ticks is sized for the engine's tween (R-STAIRS's F9 measures the openings; a longer close would need it re-sized). |
| 16 | B3 31 fps window | "a 0.2 s READ stall right after 127's closing press is acked". | A hold on the fake's state: the reads after the closing press's request is WRITTEN (channel.send reads state itself first -- armed before it, the hold blocked the request 10 s) wait until the fake has published 128, so no ring sample falls in the gap. The gap-2 half re-runs (at most twice) when the ring held no gap sample: a premise, never a verdict. |
| 17 | B3 mtime cap | "a 5 s READ stall across 127 -> 128". | 128 30 ticks after 127 (PART A's 90-frame gap did the same): with the design's gap 2, 128 is published before the stall (0.4 s after the closing press) begins. |
| 18 | B3 real stair | -- | Reuses the `dali` fixture's warned skip; its one-visit route keeps page 126 between the climb and Field(151), as the real route does -- a Field() right after the climb lands inside the walk's own record (V11 by the landing judge). |
| 19 | B3 load | "re-runs only a driver class a starved harness can cause". | `_o5_run_informative` re-runs only `_O5_LOAD_VOIDS` (landing unseen / did not land / could not be placed / the budget / never armed / a stray / a walk out of its attempts), never the class a test asserts (`want`); every outcome-asserting run goes through it. The O5 selection at `-n 6` beside O4's drive tests passed 33 of 33 (the 7 failures there were O4's B0 flakes). |

#### PART C, as built: where the design was silent or wrong (each the smallest correct thing)
C0 measured O4's build read-only (C:\gd\_ns_playtest\o4\build, each language's script decoded on its own): exactly 6.1's
sites -- member(153) 31245 (21980 B in every language) differs from stock 153 in 14 bytes, the operands of its 7 in-chain
Field() sites; member(154) 31246 (9760 B) in 14, its 7; member(151) 31244 (7880 B) in 4, its 2; the same ips in all 7
languages; member(153)'s e3 t1 ip3296 Field(204) stays the donor's. O4's campaign.toml gives the route members 31244 /
31245 / 31246: no STOP. Then C1's `--offline-check` read 6 PASS on its first run, each detail 6.1's expected line (GOALS:
the contour crossed at (-1482, 527), tri 56, 315 u into the last leg -- the design's "~(-1479, 529), 312 u" was sampled
otherwise -- and at clearance 120 at (-1523, 558) exactly; the crossings tris 53 and 56, x -1722..-1403); `--preflight`
on the live install read 12 of 12 PASS once `o5_forks.json` existed (P-MANIFEST read it).

| # | Where | The design | As built, and why |
|---|---|---|---|
| 1 | C1, the predictions' shapes | 4.1 names `landing`, `choice`, `walk` "5.3" and `route_mes` (4.14) without a JSON shape. | `landing`: the six sites of 5.3 (exit153, enter154, exit154, enter153b with `old` -1, exit153b, end_row) and `route_places`; `choice`: `store` (the ip1741 site, old 0, value 1), `rule` (the guarded rule's match), `index` 1, `beat`; `walk`: `name`, `donor`, `visit`, `contour_y` -450 (the height test's constant lives here, so O5-GOALS reads it, never a literal); `route_mes`: `block`, `marker` 127, `choice` {`mes` 128, `opens`, `holds`, `pick_line` 1 (0-based among the [CHOO] lines)}, `branch` [141, 129], `stop_page` 56; `route_build` C0's sites (O4's `fight.build.fields` shape, no score pin). |
| 2 | C1, LANDING (b) | "the next row after it is landing.enter153b (153 e0 t0 ip57 Int16[9] := -1, old -1 ...)". | O4's `is_at` reads (place, sid, tag, ip, target, new); O5's also reads `old` when the site carries one (enter153b alone), so the revisit's first EMITTED row is the same-value store the suppression model predicts, never a change. |
| 3 | C1, CENSUS's shared proof | "every `RunSharedScript(n)` site of the field lies in a function of an inert entry". | That, AND the callers are exactly `shared_by` (a registration naming another caller FAILS by name): the registered fact is checked whole. |
| 4 | C1, REGIONS | "every region instanced at a route entrance is registered". | Any role (the exit e28 and the scenes e26/e27 at 325; nothing at 316 or 304); a scene's "no Field()/ExitField()" read on every function of its entry (FIELD_OP and the eb-src `ExitField(` text), with O2's benign rule's store test. |
| 5 | C1, GOALS (d) | "every registered `scene` and `exit` region of 153 lies wholly at x > -1100". | Read as: no vertex of its quad satisfies the step's `until` -- exact for O5's one half-plane (x <= -1100), said in the docstring; (c) and (d) take the step's `until` and `walk.contour_y`, never literals. |
| 6 | C1, the analysis's stock | PATTERN joins every row on the stock bytes; `core_checks` receives no `stock`. | `O5Segment.read_session` keeps the stock source it reads with (the dry run's, or the install's) for PATTERN and the report: `T.stock_script_source()` opens the bundle again on every call. |
| 7 | C1, `why_void` | "an A-START whose row lies after the run's first row of place 154 is withdrawn". | Read off the predictions' order: the run's first `w`/`r` row in the first place of `visits` after the start place (154). The withdrawn reason is kept on the run (`start_withdrawn`) and printed by the report. |
| 8 | C1, `preflight_extra` | O4's seams (`manifest`, `pads`, `live_engine`). | Also `game` (the install whose Memoria.ini P-SETTINGS reads) and `stock_text` (`{block: {lang: bytes}}`), so the preflight test runs on a synthetic install; P-TEXT3 is O4's `p_text` with `o4_registered` True (block 3 is strict either way). |
| 9 | C1, the report's race margin | "in ticks and seconds". | The session log carries no measured rate, so the session report prints the margin in frames (127's last listed sample to 128's readiness, the guard row's own); the rehearsal record (C3) adds ticks and seconds at the launch's measured rate. |
| 10 | C1 tests | `test_o5_hallway_census_proves_inert_per_entrance`: "a synthetic Main_Init instancing an entry at 316 only". | The REAL Main_Init's e20 (an object instanced at 316 only, holding no store) registered inert: the proof read at the first visit's entrance alone passes it (the mutant), the per-entrance proof fails it by name. `test_o5_hallway_route_builder_matches_the_keys` compares the builder's DISTINCT unmasked keys with the writes and chain, its first write with `start_first`, its cut row with `end_row`, and its masked rows through the pattern (they carry offsets there, not ips). |
| 11 | C2, the renderer's events | O4's `render` with O5's start values and the per-site rule. | Plus three event forms the cases need: `("at", F)` anchors the next row at frame F (the walk window, the choice's frames: ip1741's row at 5000, after the answer's down frame 4800); a store's opt `f` (its row's frame, its order kept) and `emit` (emitted whatever the rule says: an engine that does not suppress there); an `e` event's fourth item `{"fld"}` (an `off` in a REAL field on F: v19, leak). |
| 12 | C2, cases the table left open | Several rows say "as the render shows" or name a want the code cannot hold. | Each registered with its reason: **byte8-race-both** -- an end state CARRYING Byte[8] would fail STATE (b) (the whole frozen dict is compared, and the driver reads only its targets), so the race is in the TRACE: the second run of each side is collected before ip315 runs; PROVEN. **back-door-unbacked-F** -- FORBIDDEN and VOID-ASYM (a) alone (the run VOID V11 by the game at [150, 1190, 1], F only). **start-first-missing** -- START, LANDING (b) and PATTERN (a)(b); MASKED passes (visit 3's ip22 is emitted instead -- a new site in the epoch). **walk-window-masked-write-both** -- 153 ip22 := 1 (a change, emitted) at frame 2100: WALK (b), PATTERN (b). **end-cut** -- the base already holds 151's post-cut rows, so the case stores 151's prologue a second time. **back-door-S** -- the door's rows 300 frames into the walk (an `at` anchor): SD.backing needs the step's `frame0` before the hit. |
| 13 | C2, the census unit | Mutants "inert without 32" and "e15 with its caller e32 made non-inert". | One mutation (e32 out of `inert` IS its caller made non-inert), read by the shared proof's message ("153 e15: shared, run by RunSharedScript(15) at e32 t1 ip866"); the proof's other half gets its own mutant: e15's `shared_by` naming another caller [31]. |
| 14 | C2, the build-pins unit | "O5's route members on a synthetic three-member build". | The three ROUTE members (31244/31245/31246) remapped over the WHOLE chain's map -- their in-chain Field()s also name 64, 150, 155, 156, 158 and 167, so a three-donor map is not O4's build -- and judged by `O5Segment.build_pins` directly (the base rule wants all twenty members' files). |
| 15 | C2, the why-void-start unit | "A-START on a visit-1 error-path row, none on a visit-3 one". | Read through a session's own reading (make_session + read_session), not a hand-built run; it also checks that O4's rule (the mutant) would give the visit-3 run A-START. |
| 16 | C2, the pattern unit | "on the fake's H13 trace of the builder's route, the same". | On the fake's H13 trace of the dry run's OWN event list, fed store by store (the builder's route lives in the test module; B2's test pins its trace to 4.16 by ip and C1's test to the draft) -- so `pattern_of` reads one model in two implementations, as the render-suppression unit compares them row by row. |
| 17 | C2, G27 | "G27 joins the gate with O5_DRYRUN_FLOOR = the count C2 prints". | 144 = 86 session cases + "predictions-changed" + 18 units + 39 listed units (CENSUS 1+6, REGIONS 1+5, GOALS 1+6, route pins 1+7, build pins 1+3, KEYS 1+6); `_missing(o5=True)` reads the frozen O5 predictions or the campaign.toml of O4's chain the draft reads. |
| 18 | C3, the stage table | 7.1 names F-PASS "member(153)@325 -> member(151)" and the stages' keys loosely. | F-PASS is a per-side stage (`field` {S: 153, F: "member(153)"}, `end` {S: [151], F: ["member(151)"]}) that runs F alone (`sides`), so O4's `stage_ids` resolves and checks it against its S twins unchanged; `untraced` (no storytrace verb; the drive's live scan off; `end_row_s` None) and R-RACE's `overlay` ({"guard": None}: a key set to None is DROPPED from the copy) are stage keys; R-WALK-VOID's `walk_stop_x` is laid on the copy's WALK step (`walk.name`). `stage_pred` checks the copy with guard_of, witness_of and step_of, and run() builds every stage's before the session. F-SMOKE is o4_rehearse.smoke itself (its log lines say "[o4-rh]"). |
| 19 | C3, the walk record | "per hold on the last two legs ... a SLIDE (moved off the leg's heading by more than 20 deg)". | A SLIDE is judged against the direction the hold PRESSED (its buttons through the calibrated basis): the 8-way pad quantizes a press up to 22.5 deg off any leg, so the leg's heading would flag an unobstructed hold; `off_leg` is recorded beside `off_pressed`. A hold during which control went (the trigger took him mid-hold) is `control_lost`, neither slide nor stall; STALL is under 1/4 of its frames x the walk's fastest hold per frame. The holds come from THE WALK TAP -- route_to wrapped on the session: its untrimmed waypoints and every sample its own reads kept, taken the moment it returns (by a run's end the ring has moved past the stair) -- and steps.jsonl (each request's steps, wall time, ack frame). |
| 20 | C3, R-WALK-VOID's stop | "before the first `hold` step sent while the published x is <= walk_stop_x" (-700). | As designed on the stock stair: its planned route turns at (-879, 818), so a hold starts there, west of -700 and ~600 u short of the contour. The fake's box has no stair -- one leg, walked in three holds sent at x 1105, ~115 and ~-203, -700 inside the last -- so the test stops at 600 (the second); the mechanism (raise before sending, the session's send restored at once, no direction hold after, end_run to the title) is what it pins. |
| 21 | C3, the guard and window records | 7.2: 127's presses "(decision, accepted, down, ack frames)"; the pairs' and timed windows' Confirms. | 127's presses are read off the guard row's own `presses` (each placed by its accepted event; the ack frame from the press row); the drive's press rows carry `raws` (phrase_raw), never `texts`, so a window's Confirms are matched on either. A timed window is ONE record per window (a page that adds a pair keeps it listed). The dialog-section catch counts, over the samples the recorder read, those with no dialog section while the menu group is Dialog.Choice and those listing a marker page again after one without it. |
| 22 | C3, the rehearsal report | C1's placeholder printed each record as JSON. | `rehearsal_report` prints 7.2 section by section: the capabilities and the launch's readings, then per run its outcome and rate, the grant, each stair attempt (route, holds, last-two-leg slides/stalls/pushes, the loss and teleport samples), the calibration, 127 and the guard row, THE RACE MARGIN (frames, ticks, seconds), 128 as published, the choose presses, the catch, the pairs and timed windows, the evidence, the walk stop, an untraced run's exceptions, the end, and the trace summary (cuts, keys, crossings, the emitted rows per visit, the c rows, visit 3's first, the masked counts, the forbidden hits); F-SMOKE as O4's. |
| 23 | C3 tests | `test_o5_rehearsal_*` on the fake. | The launch pins the session's axes for EVERY field (`_O5Axes`: no calibration walk on the box, where its probes would wander), zeroes the fake's story bytes on each New Game (the fake keeps them; the game's New Game zeroes gEventGlobal) before field 70's prologue, and re-runs a launch whose run ended in a load VOID (`_O5_LOAD_VOIDS`, never the class the test asserts), at most three times. |
