# Stock O8 route: raw warp into 164 (FieldEntrance 342, SC 1190) -> the first spiral and THE KNIGHT HOLD -> 165 (the second spiral) -> 166 (six pages, FMV004 played out) -> Field(55) -> the arrival in REAL 55 at 110 on both sides  (reconciled; the end DECIDED by the owner: option 1)

This is the reconciler's own decode. Every ip below was decoded from the stock US `.eb` by `reconcile/ebtool.py`. That
decoder is O7's reconciler's (storytrace.stock_script_source + ScriptIndex + instruction_stores), re-pointed at this
worktree's ff9mapkit (claude/story-trace-o8 = master 57aac989) and checked against the listing. Engine claims were
re-read in C:\gd\FFIX\Memoria. The deployed x64/x86 Assembly-CSharp.dll is sha256 ba976242..., O7's pinned engine;
Output/ holds the same sha and no .cs file is newer, so that source is the deployed engine (inferred, not decompiled).

Conventions:
- `ip` = abs - entry start = the s88 trace ip. `Lnnn` = offset from the function start (the predictions' `off`).
- `reconcile/L{164,165,166,55,70}.txt` are cmp-identical to O7's `reconcile/L*.txt` and to the bytes, start-state,
  movie and walks readers' copies. No reader decoded different bytes, so every dispute below is about interpretation or
  geometry.
- 2-byte constants are SIGNED: 57136 = -8400, 53536 = -12000, 59536 = -6000, 50536 = -15000, 54536 = -11000,
  65535 = -1.
- Heights: PSX y (up negative) = the kit walkmesh's y = the script's `f[1]` (`-pos[1]`, EBin.cs:1790). The harness
  publishes `player.y = pos[1]` (HarnessAgent.cs:1559) = -PSX y, which RISES as he climbs (lesson 5). So
  `f[1] < -12000` is published y > 12000.
- Walk numbers were RE-PLANNED here with `reconcile/r1_walks.py`. It runs extract.stock_walkmesh + PlayerWalkmesh(closed)
  + pathfind.route_avoiding(margin KEEPOUT_MARGIN_W 56, leave_wall, the step's clearance, cell 64), which is
  `_plan_round`'s call (session.py:5041-5042).
- The ENGINE's wall view (r1) walks open adjacency within reach, the way RadiusValid does
  (FieldMapActorController.cs:1060-1124), so it is level-aware.
- The corridor half-width is the largest engine wall distance on the cross-section perpendicular to the plan, walked
  out on the same level.
- First moves: `reconcile/r3_first*.py`, the harness's own `_plan_hold` offline. Clip lengths: `r4_animlen.py` (p0data5,
  read-only). The start derivation: `r2_derive8.py`, O7's merged functions generalised to O1-O7.
- In-game evidence comes from the archived runs only:
  - `.harness-runs/20261005-060311-story-o7` (O7's session), `20261001-095552-story-o3` and
    `20261001-093510-o3-rh-R-FULL`.
  - No archived run has ever entered 165, 166 or 55.

## The segment (DECIDED -- verified here, not relitigated)
New Game, `storytrace 1`, then in field 70 (UIState FieldHUD) a raw `warp 164 342 1190` (S) / `warp 31256 342 1190` (F).
The warp comes after 70 e0 t0 ip130 and before ip475; the two start reads below classify both edges of that window.

Three visits, `route` = `visits` = [164, 165, 166]:
- **164@342** (visit 1, cell (164, 1190)). A `walk` up the first spiral to P1, then THE KNIGHT HOLD. Then a `trigger`
  up the second spiral into e2 at the top (`until {y_gt: 12000}`, `to` 165).
- **165@343** (visit 2, cell (165, 1190)). A `walk` to P1, then a `trigger` into e2 at the top (`until {y_gt: 15000}`,
  `to` 166).
- **166@344** (visit 3, no cell). No control. Six pages, then FMV004 PLAYED OUT, then e6 t1 ip863 `Int16[2] := 110` and
  ip871 `Field(55)`.

END on the arrival in REAL 55 at 110 on BOTH sides, cut at 55 e0 t0 ip22 (`Bit[191] := 0`, same, emitted as a new site):
- `side_ends` {S: [55], F: [55]}; `members` = O4's twenty ONLY.
- SC 1190 throughout.
- No battle, choice, naming, ATE, SC rung or revisit.
- A covered run writes EXACTLY **23 keys**: 20 writes and the 3-key chain 342 -> 343 -> 344 -> 110.
- It emits **29 `w` rows** before the cut (9 / 9 / 11 a visit, 6 of them masked) and no `c` row.
- ~2.5 min a run (estimate; F8 freezes it from R-FULL).

## O8 -- the start (re-derived with O7's merged machinery: `r2_derive8.py`)
**The residue: FOUR `r` rows in field 70.** `[byte, old, new]` = `[[0,0,166],[1,0,4],[2,0,86],[3,0,1]]`:
- SC 1190 = 0x04A6 -> bytes 0 and 1; FieldEntrance 342 = 0x0156 -> bytes 2 and 3.
- The olds are 0, as in O7's run1_S lines 2-5 (`[2,0,59]` there for 315).
- Ff9mkDebugMenu.cs:2120-2135 sets FieldEntrance, then ScenarioCounter, then SetNextMap (no remap), after
  WarpFadeWait 0.9 s (:114). The warp is refused outside FieldHUD (:2083).
- O6's three-row contract would refuse this; O7's `start_residue` reads four.

**Field 70 is the LIVE New Game override.** FF9CustomMap-world EVT_ALEX1_TS_OPENING, sha 2ce8887e = OVERRIDE70. Its e0 t0
text is identical to stock from ip6 through ip544 except the SWITCH labels at ip278. That includes ip57 `Int16[9] := 643`,
ip130 `Byte[13] := 1`, ip138, ip200, ip249 `Byte[8] := 125` and ip475 `Byte[13] := 2`. Past that point:
- the override has ip558 `Byte[13] := 3`, ip575 `Int16[2] := 0` and ip583 `Field(4600)`;
- stock has ip547 `Int16[2] := 0` and ip555 `Field(50)`.

O7's five kept 70 pins (ip130, ip238, ip246, ip249, ip475) are text-identical in both.

**THE START ROW**: 164 e0 t0 ip22 (L16) `Bit[191] := 0` (same, emitted). It is real 164 on S and member(164) 31256 on F.
ip6/ip14 are Map variables. START requires:
- (a) the rows before the start are exactly the four residue rows;
- (b) the first `w` row in place 164 is ip22;
- (c) start_music: the first Byte[13] row in place 164 is ip130 (L124) `Byte[13] := 1` from old 1 (same 1).

The 164 prologue takes ip130 for ANY incoming Byte[13] from 0 to 8:
- ip79 `Byte[13]==2 && Int16[9]<0` is false, because ip57 wrote 385 first; ip119 needs `Int16[9] < 0`.
- Window 56 (ip581-607) needs a 9, which field 70 never holds.

**The spawn is a chained arrival's.** 164 e7 t0 ip18 pushes `Int16[2]` (342), and ip22 `SWITCH(344, L47, L12)` takes the
default L47 for 342: (2040, 3335), facing 65500 = -36, MoveInstantXZY y 59889 = -5647. GetTriIdxAtPos
(FieldMapActorController.cs:1279-1306: the XZ tri whose centre height is nearest) picks tri 145 (PSX -4780) over tri 110
(-9776), so the published y is ~4780. These are the bytes' numbers; REHEARSE (lesson 6, though O5-O7 were exact).

**THE START-SCOPED OLDS (derived: `scoped_derivation` over a mock O8 key set, O7's FROZEN pattern, O1-O7).** Exactly
three, with no problems:

| site | target | raw start (old -> new, same) | after a true O1-O7 run | after.old read off O7's frozen pattern |
|---|---|---|---|---|
| 164 e0 t0 ip57 (L51) | Int16[9] | 643 -> 385, 0 | 385 -> 385, 1 | `[163,0,0,51,'Global.Int16[9]',385,1]` (163 ip57) |
| 164 e0 t0 ip130 (L124) | Byte[13] | 1 -> 1, 1 | 2 -> 1, 0 | `[163,0,0,678,'Global.Byte[13]',2,0]` (163 ip684) |
| 166 e6 t1 ip345 (L71) | Byte[208] | 0 -> 0, 1 | 1 -> 0, 0 | `[159,16,1,258,'Global.Byte[208]',1,0]` (159 ip648) |

Every other key reads equal olds on both starts. `last_values` over O7's frozen pattern gives Bit[3811] None (so 0),
Byte[13] 2, Byte[14] 0, Byte[208] 1, Byte[8] 125, Int16[11] -1, Int16[2] 342 and Int16[9] 385. The emitted pattern is
frozen from THIS start.

**THE START READS (two).** O7's `start_reads` rule:
- **166 e0 t0 ip255 (L249) `Byte[8] := 125` must read old 125.** It is the route's first Byte[8] store; 164 and 165
  neither store nor read Byte[8]. A warp before 70 ip249 leaves 0. `race_site` over O7's kept 70 pins resolves
  (70, 0, 0, 249), and both branches of `why_void` make it A-START by the driver.
- **NEW: 164 e0 t0 ip130 `Byte[13] := 1` must read old 1.** A warp that left 70 after ip475 (or the override's ip558)
  reaches 164 with Byte[13] 2 (or 3). 164 takes NO error path, so the run is SILENT: ip130 reads 2 -> 1, same 0, which
  is the TRUE chain's old. START (c) and PATTERN would then fail, giving NOT PROVEN rather than A-START (in O7, 154's
  ip101 and window 56 made the same race loud). Register 164 ip130 as a start read with old 1, its raced store 70
  ip475 (`race_site(pred, {Byte[13], old 2})` already returns (70, 0, 0, 475) off O7's pins). ip558 has no stock pin;
  P-OVERRIDE covers it. The A-START message must name the late race, not "before its store".

**THE CARRIED VALUES (derived: `carried_from_segments` over O1 v4 + O2-O7 v1 less O8's own and masked targets).**
FIFTEEN `[raw, true]` pairs, with no problems: Bit[3717] [0,1], Bit[3718] [0,1], Bit[3795] [0,1], **Bit[3796] [0,1]**
(O7's 159 e16 t1 ip672, the only one O7 adds), Bit[3815] [0,1], Bit[3854] [0,1], Bit[3855] [0,1], Byte[18] [0,1],
Byte[303] [0,1], Byte[472] [0,4], Byte[475] [0,100], Byte[6] [0,11], Int16[469] [0,1042], UInt16[19] [0,1807] and
UInt16[21] [0,8].

THE PARTY is [Zidane] raw and [Steiner] after O6's rebuild; it is typed and labelled, never derived, and no party op runs
in 164-166. Steiner is the controlled character on both sides: 164 e7 SetModel(5489) + DefinePlayerCharacter ip325,
165 e7 ip317, 166 e6 ip262. Consequences:
- O8's `end_state` must NOT hold Bit[3796]. O7's held it at 1, but on the raw start it is 0.
- **BUILD TRAP.** O7-KEYS' carried scan (o7_castle_walk.py:2333-2343) scans every function of every entry instanced at
  an entrance (`instanced_texts`). It WILL refuse Bit[3855]/Bit[3854] at 164 e1 t3 ip326 (the knight's TALK, which sums
  the eight knight bits into Map.Byte[30] for SetTextVariable). That talk is never driven; its stores are forbidden.
  Narrow the scan to the functions the route runs: exclude tag 3 and what only it calls (164 e7 t11/t12 via RunScriptSync
  e1 t3 ip415/ip452). No other carried target appears in 164@342 {0,1,2,3,7}, 165@343 {0,1,2,3,7} or 166@344 {0,3,5,6}
  (grep of the listings). 55's reads (UInt16[19]/[21], Byte[303], Byte[18]) lie past the cut.

**START-DEPENDENT: NONE, in value or path, up to the cut.** Every route read resolves the same branch from both starts:
- 164's prologue tests;
- the spawn SWITCH (342 on both);
- the knight's Bit[3811] (0 on both: no O1-O7 key writes it);
- 165's chain (Byte[13] 2 -> 1 -> 2 -> 3, Int16[2] 343);
- 166's (Byte[13] 3 -> 0, Byte[208] written before it is read, Byte[8] 125);
- the movie gates (B_SYSVAR[15] is engine state, GetSysvar.cs:49-50).

Only OLDS differ (the three above).

## The member set (fork side) -- nothing new, nothing rebuilt
F runs O4's alxc chain as deployed in FF9CustomMap (`o4_forks.json` / `o7_forks.json`): `warp 31256 342 1190`, then
31257@343, then 31258@344, then REAL 55. Re-read today (the fork reader's `forkdiff7.out` over the live install, all 7
languages; `preflight_parts.out`):
- **31256** (member(164), EVT_O4_ALXC_AC_LTI, 2872 B) differs from 164 in exactly 4 bytes: e2 t2 ip251 `Field(165)` ->
  `Field(31257)` and e3 t2 ip251 `Field(163)` -> `Field(31255)`.
- **31257** (member(165), EVT_O4_AC_LTI_2, 2048 B): e2 t2 ip241 `Field(166)` -> `Field(31258)` and e3 t2 ip251
  `Field(164)` -> `Field(31256)`.
- **31258** (member(166), EVT_O4_AC_LTT, 2584 B) is BYTE-IDENTICAL to 166 in every language (the same sha). Its only
  Field() is e6 t1 ip871 `Field(55)`, RAW, and ip863 `Int16[2] := 110` is unconditional (the JMP_IFNOTs at ip849/ip860
  land on the next instruction).
- Live ForkDonorPatch.txt (FF9CustomMap): lines 91-93 `31256 164`, `31257 165`, `31258 166`; line 42 `31205 55` (O1).
  DictionaryPatch lines 168-170 `FieldScene 31256..31258 11 O4_... 3`; line 119 `FieldScene 31205 11 O1_TH_ORC ... 2`.
  All 140 member .eb files equal O4's build (`C:/gd/_ns_playtest/o4/build`); O4-O6's P-EB pins stay untouched.
- The member walkmeshes equal their donors' (P-FLOOR normalised; stock 165's .bgi does not round-trip byte-exact through
  BgiWalkmesh, 6376 -> 6374 B, so compare normalised on both sides). No stacked folder overrides 55, 164, 165 or 166.

**THE LANDING IS REAL 55 ON F.**
- MAPJUMP (DoEventCode.cs:1008-1030) -> SetNextMap -> HonoluluFieldMain.cs:444 `fldMapNo = map.nextMapNo`: no remap.
- ForkSiblingField (ForkSiblingMap[55] = 31205) is called only at ff9.cs:9327 (world -> field) and
  HonoluluBattleMain.cs:737 (battle return); 164-166 have no battle op.
- EffectiveFieldId(55) = 55 (DataPatchers.cs:47-50), so 55's rows read fld 55, don 55.
- `side_ends_of` (run here) accepts {S: [55], F: [55]} with O4's twenty and refuses F [31205] or 31205 among `members`.
  `on_route`: 31256-31258 and 55 True, real 164/165/166 False on F (rule 2's V19).

## Ambient prologue and the Byte[13] chain (each visit's e0 t0)
The prologue in each field:
- `Bit[191] := 0` (ip22) and `Bit[184] := 0` (ip49): masked.
- `Int16[9] := K` (ip57): **K = 385 in 164 and 165, -1 in 166 and 55**.
- Byte[13]: `==9` -> nothing; `==2 && Int16[9]<0` -> ip97 `:= 9` (THE ERROR PATH); `Int16[9]<0` -> ip119 `:= 0`;
  else ip130 `:= 1`.
- ip138 `Int16[11] := -1`; ip200 `Byte[14] := 0`.

164 and 165 store `Byte[13] := 2` in the grant's pass (164 ip764, 165 ip844). 165 e2 t2 ip205 `Byte[13] := 3` is LIVE: 165's
e2 sets no Map.Bit[162]. 164 e2 t2 ip215 is DEAD: ip54 `Map.Bit[162] := 1`, then ip193's test.

| field | K | Byte[13] row, raw start (old -> new) | post-grant | door |
|---|---|---|---|---|
| 164 @342 | 385 | ip130 1 -> 1 (START) | ip764 1 -> 2 | e2 ip215 dead |
| 165 @343 | 385 | ip130 2 -> 1 | ip844 1 -> 2 | e2 ip205 2 -> 3 LIVE |
| 166 @344 | -1 | ip119 3 -> 0 | -- (no grant) | -- |
| 55 @110 (past the cut) | -1 | ip119 0 -> 0 | -- | -- |

## 164 A. Castle / west tower, the first spiral (EVT_ALEX1_AC_TOWER_L3; F 31256) -- visit 1, entrance 342
- **Main_Init e0 t0** (one frame): the prologue ip22..ip200, then ip219 `SetControlDirection(40, 40)`, ip223
  InitObject(7) (Steiner), ip226 InitObject(1) (the knight), ip229/ip232 InitRegion(2)/(3), op_22(2) x2 (ip255, ip578).
  ip581/ip615 are the window-56 tests (dead). ip649 `Map.Bit[159] := 1`; ip657 `Map.Bit[158]==1` (set by e7 t0 ip326
  right after DefinePlayerCharacter) -> ip676 `Map.Bit[159]==1`, ip687 `Map.Bit[156]==0` -> **ip698 EnableMove = THE
  GRANT**. Then ip699 SetTriangleFlagMask(255) and **ip764 `Byte[13] := 2`** (1 -> 2) in the same pass. e7 t0 ip356 is
  the twin grant.
- **In game already:** O7's six session runs read 164's prologue past their cut, all six rows in ONE frame. ip764 followed
  2-5 frames later in runs 1, 3, 4, 5; in runs 2 and 6 the `off` row came first.
- **Steiner** (e7, GEO 5489): SetObjectLogicalSize(30, 35, 50) at e7 t0 ip138. **Radius 80**: DoEventCode.cs:1507-1508
  `effMapNo == 164 && sid == 7 && size == 30` -> size 20 -> radius 80 (:1531, :1534). effMapNo = EffectiveFieldId (:25),
  so 31256 gets it through ForkDonorPatch line 91. collRad 35, talkRad 50. All 170 tris are open at mask 0xFF.
  - **The engine's nearest wall at the spawn is 95.8 u**, the east edge (2130, 3517)-(2138, 3267) reached through tri 158
    (r1, `engine_wall`). That is above 80, so there is NO push-out.
  - The "68 u" in PLAN.md is tri 145's edge to tri 154 (PSX -4688), closed only in the planner's band A: dispute 1.
  - e3 is LIVE at this level, 157.2 u away.
- **e2** (5-gon, SetRegion (946,2249) (1122,1974) (222,2039) (-25,2186) (93,2401), the engine's order).
  - t2: ip34 `SYSVAR[2]` (usercontrol), else RET. ip42 `obj(uid=250).f[1] < -12000`, else ip51 -> RET.
  - Firing: ip54 Map.Bit[162] := 1, ip62 Map.Bit[163] := 1, ip70 CalculateExitPosition, ip71 ExitField, ... ip165
    op_22(25), **ip243 `Int16[2] := 343`**, ip251 `Field(165)` (F: 31257).
  - IsInQuad is the ring of ears (EventEngine.TreadQuad.cs:24-39), so the centroid (472, 2170) is DEAD.
  - QuadCircleData has no 164xxx/165xxx row (EventEngineUtils.cs:1722-1737), so S and F test the same ring.
- **e3** (5-gon (938,3257) (1051,2471) (2066,2776) (2233,2840) (1738,3462)): ip42 `f[1] > -6000` (published y < 6000);
  ip243 `Int16[2] := 343` too, then `Field(163)` (F: 31255). It is the back door and FORBIDDEN. A chain key must match
  on sid/tag/ip, never on value alone.
- **The knight** (e1, GEO 5488): t0, t1, t3; no t2 (talk-only). The knight section is below.
- **Store census (25 sites):**
  - route 9: ip22, ip49 (masked); ip57, ip130, ip138, ip200, ip764; e1 t1 ip230; e2 t2 ip243;
  - dead 4: ip41 (`Bit[184]==1`), ip119, ip211, e2 t2 ip215;
  - error path 4: ip97, ip178, ip607 / ip641 (window 56);
  - forbidden 8: e1 t3 ip308 Bit[3851], ip420 Bit[3792], ip627 Bit[7211], ip690 Int16[224] (the TALK); e7 t11 ip399 /
    ip434 Byte[208] (called only by the talk); e3 t2 ip215 / ip243 (the back door).

## 165 A. Castle / west tower, the second spiral (EVT_ALEX1_AC_TOWER_L4; F 31257) -- visit 2, entrance 343
- **Main_Init**: the prologue (ip130 2 -> 1), ip219 `SetControlDirection(24, 24)`, InitCode(1) (SetTileColor only),
  InitObject(7), InitRegion(2)/(3). ip737/756/767 lead to **ip778 EnableMove** (Map.Bit[158] from e7 t0 ip318), then
  **ip844 `Byte[13] := 2`** in the same pass. e7 t0 ip348 is the twin.
- **Spawn**: e7 t0 ip10/ip14 `SWITCH(345, L47, L12)`; 343 takes the default L47: (2055, 3411), facing 128, MoveInstantXZY
  y 55017 = -10519. That lands on tri 57 (PSX -10280; tri 47 at -15133 is above), so the published y is ~10280.
  - **Radius 120**: there is no 165 case in DoEventCode.cs:1503-1520.
  - The engine wall at the spawn is 154.5 u.
  - e3 is LIVE (`f[1] > -11000`) 133.6 u away; e2 is 420 u away.
- **e2** (4-gon (3298,3179) (3241,2829) (2401,3074) (2494,3428): no dead centre).
  - t2 ip38 `f[1] < -15000`, else RET.
  - Firing: ip50 RunSoundCode2, ip60/61 Exit, ip62 Map.Bit[158] := 0, ...; ip183 `Map.Bit[162]==0` is true, so
    **ip205 `Byte[13] := 3`** (2 -> 3) is LIVE; then **ip233 `Int16[2] := 344`**, ip241 `Field(166)` (F: 31258).
- **e3** (5-gon (1209,2668) (1437,2069) (2169,2636) (2395,3155) (1780,3363)): ip42 `f[1] > -11000`; ip243 `Int16[2] := 344`
  then `Field(164)`. Back door, FORBIDDEN.
- **Census (18):**
  - route 9: ip22, ip49, ip57, ip130, ip138, ip200, ip844, e2 t2 ip205, ip233;
  - dead 3: ip41, ip119, ip211;
  - error 4: ip97, ip178, ip687, ip721;
  - forbidden 2: e3 t2 ip215, ip243.

## 166 A. Castle / west tower top (EVT_ALEX1_AC_TOWER_L5; F 31258, byte-identical) -- visit 3, entrance 344, NO CONTROL
- **Main_Init**:
  - ip22..ip200 (ip57 `Int16[9] := -1`, 385 -> -1; **ip119 `Byte[13] := 0`**, 3 -> 0);
  - ip219 `SetControlDirection(64, 64)`; InitObject(6) (Steiner), (3), (5) (the circling pair); ip232
    `RunSoundCode(0, 137)`;
  - the SYSVAR[3] sound-sync loop ip241-252, then **ip255 `Byte[8] := 125`** (THE START READ, 125 -> 125);
  - op_22(2) x2; window-56 tests ip306/ip340 (dead);
  - **the only EnableMove, ip423, sits behind ip382 `Map.Bit[158]==1`**, which only ip393 inside the same branch sets.
    Mapvars are zeroed on every load (EventEngine.cs:625-627), and 165 e2 t2 ip62 had cleared the bit anyway. So NO
    GRANT: a control sample in 166 is V4 (game).
- e1 (the Map.Byte[24] watcher) is NOT instanced in 166. e2 runs only as e6's shared script (ip489 RunSharedScript(2):
  the clank loop). Neither stores a global.
- **The scene, e6 t1** (Map.Byte[24] is 0 at load: ip278 `SWITCH(0, L659, L12)` -> L12):
  - op_22(30), walk, anim, op_22(10);
  - **page 307** (ip310, WindowSync); op_22(30), anim; **page 308** (ip328, Sync); **page 309** (ip334, WindowAsync);
  - anim 6998 (4 frames); **ip345 `Byte[208] := 0`**; one loop pass (anim 6982, sound) with **ip380 `Byte[208]++`** 0 -> 1;
    ip385 `Byte[208] < 1` false; anim 6990; **ip401 WaitWindow(0)**;
  - walk; ip414 Map.Byte[32] := 1 (e3/e5 start circling); op_22(90); teleport and walk;
  - **page 311** (ip454, Sync, under RunAnimation(6605), 39 frames); anim; **page 312** (ip474, Sync); anim;
    RunSharedScript(2); **page 313** (ip492, Sync); ip498 StopSharedScript; op_22(10); **ip502 `Byte[8] := 0`**;
  - fades, op_22(25), op_22(2); the movie (below); **ip863 `Int16[2] := 110`**; **ip871 `Field(55)`** (raw on F).
  - No global store between ip502 and ip863.
- **Census (18):**
  - route 11: ip22, ip49, ip57, ip119, ip138, ip200, ip255, e6 t1 ip345, ip380, ip502, ip863;
  - dead 3: ip41, ip130 (K = -1), ip211;
  - error 4: ip97 (needs an incoming 2; 165's live ip205 gives 3), ip178, ip332, ip366 (window 56).

## END: the arrival in REAL 55 at 110 (both sides)
**The cut is 55 e0 t0 ip22 (L16) `Bit[191] := 0`**, the first gEventGlobal store of 55's Main_Init (ip6/ip14 are Map
variables). It is old 0, same, and emitted as a new site of the epoch. 55 is real on both sides, so `cut_at_end` cuts
both runs the same way.

Everything 55 writes is post-end:
- ip49 Bit[184] 0, ip57 Int16[9] -1, ip119 Byte[13] 0, ip138, ip200: all same-value;
- **ip255 `Int16[2] := 106` (110 -> 106)**: at SC 1190, ip229 `UInt16[0] < 1400 || Int16[2] == 106` is true. No wait op
  between ip22 and ip255 (InitCode(1) and SetDialogProgression do not yield), so it lands IN THE CUT'S FRAME;
- **ip342 `Byte[8] := 125` (0 -> 125)** after the SYSVAR[3] loop ip322-339. In-game precedent: O7's 159 ip290 and O3's
  64 ip475 landed in their prologue's frame in every archived run.

**So the live end-state read races Int16[2] and Byte[8]. Take both from the TRACE:**
- Int16[2] 110 from 166 e6 t1 ip863;
- Byte[8] 0 from 166 e6 t1 ip502 (31258 on F, matched by place).

Nothing else races: Byte[13] and Int16[9] are rewritten same-value; SC stays 1190 (55's only SC stores, e10 t1
ip568/ip582, sit behind Map.Byte[24] case 3, seconds away behind page 129); Bit[3811] and Byte[208] are untouched by 55;
55 stores nothing in any t0 of an entry it instances.

**The live end state (raw start)**:
- SC (UInt16[0]) 1190; Bit[191] 0; Bit[184] 0; Int16[9] -1; Byte[13] 0; Int16[11] -1; Byte[14] 0; Bit[3811] 1;
  Byte[208] 1;
- O8's UNTOUCHED (the targets of 164's forbidden talk sites, 0 since New Game and in O7's frozen end state): Bit[3851] 0,
  Bit[3792] 0, Bit[7211] 0, Int16[224] 0.
- `end_state_trace`: Int16[2] 110 at 166 e6 t1 ip863; Byte[8] 0 at 166 e6 t1 ip502.
- Never in `end_state`: the fifteen carried targets (incl. Bit[3796]).
- Recommended freeze refusal: an `end_state` target that any 55 pre-yield site writes to another value.

## SC ladder and the FieldEntrance chain
- **SC: no rung.** No store to UInt16[0] (bytes 0/1) in any width in 164-166 (census). 1190 comes from the residue and
  holds through the cut.
- **Chain** 342 (residue: byte2 0 -> 86, byte3 0 -> 1; not a key) -> **343** (164 e2 t2 ip243, L209) -> **344** (165 e2
  t2 ip233, L203) -> **110** (166 e6 t1 ip863, L589). Past the cut, 55 ip255 rewrites 110 -> 106.
- **3 chain keys.** The back doors (164 e3 t2 ip243 343, 165 e3 t2 ip243 344) store the same values: match on the
  site, never the value.

## Expected story keys, in order (S; F identical in donor terms; raw start)
| visit | field | sid tag | ip (L) | key (old -> new) |
|---|---|---|---|---|
| 0 | 70 | residue | | SC byte 0 (0->166), byte 1 (0->4); FieldEntrance byte 2 (0->86), byte 3 (0->1): exactly **4** `r` rows, set aside by the front cut |
| 1 | 164 | e0 t0 | 22 (16), 49 (43) | Bit191 := 0 (THE START ROW), Bit184 := 0 -- masked, same |
| 1 | 164 | e0 t0 | 57 (51) | Int16[9] 643 -> 385 (start-scoped: 385 -> 385 after O7) |
| 1 | 164 | e0 t0 | 130 (124) | Byte13 1 -> 1 same (START (c); start-scoped: 2 -> 1 after O7; the new start read) |
| 1 | 164 | e0 t0 | 138 (132), 200 (194) | Int16[11] -1 same, Byte14 0 same |
| 1 | 164 | e0 t0 | 764 (758) | Byte13 1 -> 2 (the grant's pass) |
| 1 | 164 | e1 t1 | 230 (70) | **Bit3811 0 -> 1** (the knight sits: inside step 0's row, during THE HOLD) |
| 1 | 164 | e2 t2 | 243 (209) | Int16[2] 342 -> 343 (chain) |
| 2 | 165 | e0 t0 | 22, 49 / 57, 130, 138, 200 | masked / Int16[9] 385 same, Byte13 2 -> 1, same, same |
| 2 | 165 | e0 t0 | 844 (838) | Byte13 1 -> 2 (the grant's pass) |
| 2 | 165 | e2 t2 | 205 (175), 233 (203) | Byte13 2 -> 3 (live); Int16[2] 343 -> 344 (chain) |
| 3 | 166 | e0 t0 | 22, 49 / 57, 119 (113), 138, 200 | masked / Int16[9] 385 -> -1, Byte13 3 -> 0, same, same |
| 3 | 166 | e0 t0 | 255 (249) | Byte8 125 -> 125 same (THE START READ) |
| 3 | 166 | e6 t1 | 345 (71), 380 (106) | Byte208 0 -> 0 same (start-scoped: 1 -> 0 after O7), 0 -> 1 |
| 3 | 166 | e6 t1 | 502 (228) | Byte8 125 -> 0 |
| 3 | 166 | e6 t1 | 863 (589) | Int16[2] 344 -> 110 (chain; THE SEAM ROW on F: 31258) |
| 4 | 55 | e0 t0 | 22 (16) | the cut (Bit191, same, emitted: a new site) |

**29 `w` rows a run before the cut (6 masked + 20 writes + the 3-key chain), every site once.** 11 of the 20 writes
are same-value, each the first at its site in the epoch (the site key includes the field), so all are emitted, the s88
sink suppresses nothing and no `c` row arises.

**REGISTERED KEYS: EXACTLY 23**:
- 164 (6): ip57, ip130, ip138, ip200, ip764, e1 t1 ip230;
- 165 (6): ip57, ip130, ip138, ip200, ip844, e2 t2 ip205;
- 166 (8): ip57, ip119, ip138, ip200, ip255, e6 t1 ip345, ip380, ip502;
- the chain (3): 164 e2 t2 ip243, 165 e2 t2 ip233, 166 e6 t1 ip863.

**THE PATTERN** (`[place, sid, tag, off, target, new, same]`, raw start; F the same by place):
- V1 164: `[164,0,0,16,Bit[191],0,1] [164,0,0,43,Bit[184],0,1] [164,0,0,51,Int16[9],385,0] [164,0,0,124,Byte[13],1,1]
  [164,0,0,132,Int16[11],-1,1] [164,0,0,194,Byte[14],0,1] [164,0,0,758,Byte[13],2,0] [164,1,1,70,Bit[3811],1,0]
  [164,2,2,209,Int16[2],343,0]` (9)
- V2 165: `[165,0,0,16,Bit[191],0,1] [165,0,0,43,Bit[184],0,1] [165,0,0,51,Int16[9],385,1] [165,0,0,124,Byte[13],1,0]
  [165,0,0,132,Int16[11],-1,1] [165,0,0,194,Byte[14],0,1] [165,0,0,838,Byte[13],2,0] [165,2,2,175,Byte[13],3,0]
  [165,2,2,203,Int16[2],344,0]` (9)
- V3 166: `[166,0,0,16,Bit[191],0,1] [166,0,0,43,Bit[184],0,1] [166,0,0,51,Int16[9],-1,0] [166,0,0,113,Byte[13],0,0]
  [166,0,0,132,Int16[11],-1,1] [166,0,0,194,Byte[14],0,1] [166,0,0,249,Byte[8],125,1] [166,6,1,71,Byte[208],0,1]
  [166,6,1,106,Byte[208],1,0] [166,6,1,228,Byte[8],0,0] [166,6,1,589,Int16[2],110,0]` (11)

The cut is `[55,0,0,16,Bit[191],0,1]`. After a true O1-O7 chain only the same flags of the three start-scoped sites
change (164 ip57 -> 1, 164 ip130 -> 0, 166 ip345 -> 0).

**ORDER**: the bytes fix every in-visit order, with two exceptions:
- (a) 164 e1 t1 ip230 vs e2 t2 ip243 is a RACE. The hold orders it by construction (below).
- (b) 166 ip255 vs e6 t1 ip345 is ordered by timing. ip255 follows the sound sync, which landed in the prologue's frame
  for 159 ip290 and 64 ip475 in every archived run. ip345 needs op_22(30) + a walk + op_22(10) + pages 307 and 308 (two
  Confirms) + op_22(30) + anims: at least ~2.5 s. Practically fixed; R-FULL confirms.

ip764 precedes ip230 (ip230 needs a 3600-u climb).

## Choices, naming, battles, minigames
- **Choices**: none on the route. Keep the guard rule `{donor None, match "want to skip", pick "default"}`: a stray
  Confirm during FMV004 opens SkipMovieDialog, and "default" is No (O3 measured the published dialog, cursor on No).
- **Naming**: none (no `Menu(1, x)` in 164-166).
- **Battles**: none (no 0x2A / SetRandomBattles op in 164-166 or 55's pre-cut). Any battle is V10.
- **Stop page**: window 56 "Env Play()" (164 e0 t0 ip597/631, 165 ip677/711, 166 ip322/356), V5.

## Nondeterminism (O8)
1. **START**: none in value or path. Three start-scoped olds; two start reads (Byte[8] old 125 at 166 ip255; Byte[13]
   old 1 at 164 ip130), each race A-START by the driver.
2. **THE KNIGHT'S RACE**: 164 e1 t1 ip230 lands ~140 ticks after Steiner first stands at PSX <= -8400. Without a hold,
   pure running from T0 to e2's fire is 15.8 + ~125 ticks, a dead heat. e2's Field(165) unloads 164, so ip230 would go
   MISSING. THE HOLD makes the order constructive.
3. **Timing only**: the grant pass (2-5 frames); the pages' Confirms (the first is often dropped, lesson 11: 307 has a
   [SPED=2] crawl); the async 309; FMV004's wall time (45.412 s file, ~50 s static span estimated from O3's +5.3 s);
   the fades; the 55 load.
4. **Positions**: every grant is the bytes' spawn (rehearse). The pinch (below) is the one geometric unknown.
5. **Render rate**: ~31 or ~60 fps, picked by the game; every O7 run was ~31, O3's movie stretches ~60. MBG.cs:217
   calls FPSManager.SetTargetFPS(30), but under the live `[Graphics] VSync = 1` FPSManager.cs:43-44 keeps
   vSyncCount 1, and Unity ignores targetFrameRate then. O3 R-FULL measured fps 60 / 58.6 before, during and after
   FMV003. Plan nothing in ticks across the movie (rule 9 sleeps).

## The walks (O8) -- re-planned here (`r1_walks.py`; numbers in `r1_walks_164.json` / `r1_walks_165.json`)
**Machinery as merged:**
- `walk_kw` (segment_drive.py:2555-2569) forwards `clearance` and `basis` only when the step carries them; it always
  passes `unstick=True`, and `npcs` per step.
- The default floor is `PlayerWalkmesh(extract.stock_walkmesh(donor), closed=closed)` (:4300-4306); a member walks its
  donor's floor (P-FLOOR).
- **Keys read twist.y** (UseAbsoluteOrientation 3). 164 `SetControlDirection(40, 40)`: 41/256 x 360 = 57.66 deg, up
  (0.845, 0.535). 165 `(24, 24)`: 35.16 deg, up (0.576, 0.818).
- Seed `basis: "prior"` (S19, session.py:4539-4546); O8.start_run forgets 164, 165, 31256 and 31257 every run (O7's
  reseed).
- PSXMovementMethod 1 scales the run by the tri's |n.up| (FieldMapActorController.cs:743-744), never turning it. 164's
  |n.up| runs 0.54-0.93.

### CONTROL 1 -- 164 (S) / 31256 (F), entrance 342, SC 1190, visit 1, cell (164, 1190): two steps and a hold
- **Grant** ip698 (+ ip764). **Spawn** (2040, 3335), tri 145, published y ~4780 (REHEARSE). **Basis** prior.
- **First move** (`_plan_hold` offline, pending spread 18.26 deg): pad **'left'** (bearing -32.3; the first leg -19.2 deg
  toward (1776, 4095)) for 2 frames at 31.3 fps (3 at 60); reach 180, inside the evidence band [40, 178]. An engine-like
  walk of that press: 51 / 104 / 156 u at 1 / 2 / 3 ticks, **0.0 deg off**, nearest wall on the way 96 u (> 80).
  Judged within acos(PRIOR_AGREE) = 16.3 deg (session.py:3546-3550). The FIRST first-move check ON A RAMP: the slope
  scales reach, never direction.
- **STEP 0 -- `walk` "164: the first spiral to P1, then THE KNIGHT HOLD"**:
  - goal **P1 (1342, 2252)** (tri 53, PSX -8958; tris 11 at -3961 and 98 at -13893 stack at that XZ; engine wall 118.2;
    gaps e2 335, e3 293.5); start (2040, 3335).
  - `at_y` **[8800, 9150]** (NEW): P1's level is y 8958; within 45 u it spans ~8930-8980; 8800 > the knight's 8400, so a
    proven at_y also proves the knight's release.
  - `hold` **{flag 3811, value 1, timeout_s 15}** (NEW).
  - `avoid` **["164.e3"]**, the 5-point REGION. Required: e3 is live and 157 u away, and the 4-point `zone` would drop its
    near edge.
  - `closed_tris`: **93** = every open tri whose centroid PSX lies outside [-9500, -4700] (0 XZ self-overlaps in the
    band); derived, never typed.
  - `clearance` **80** (none at 84); `basis` "prior"; **`npcs` false** (REQUIRED: `_npc_levels` keeps the knight as a disc
    from any level, and his start (249, 4630) lies 152.5 u from the line, inside P 252: no route); `attempts` 3; beat
    `w164_p1`.
  - **Plan**: 24 waypoints, **6404 u**, all on loop 1, PSX -4780 -> -8958, **128.2 slope-scaled run ticks** (4.3 s).
    - No squeeze: the corridor's least half-width on the line is 83.4 at loop 1's north turn (1191, 4538), PSX -5712.
      The line hugs inner corners at 78.1-80 (a push under 2 u).
    - It passes PSX -8400 (T0, the knight's release) at L 5655 (610, 2160), 750 u / ~16 ticks before P1.
    - It enters e2's ring twice at its DEAD level (PSX -8005 at (61, 2342), -8429 at (646, 2161)): tag 2 runs, passes
      SYSVAR[2] and RETs at ip51, with no store and no loss (the first O-segment to walk through a live region at a dead
      level: REHEARSE).
    - It never enters e3 (gap 157 at the spawn).
- **THE KNIGHT HOLD** (the hold): after the arrival, `g.watch(3811)`, press nothing, poll the published flag until it reads
  1 (None = not yet: a key not published, or an empty state.json, lesson 10), then `g.unwatch()`. Expected 2.8-4.2 s.
  The section below has the full design.
- **STEP 1 -- `trigger` "164: the second spiral into e2 at the top"**:
  - goal **(59, 2214)** (tri 12, PSX -13040, 62 u deep in e2's WEST EAR, outside the dead centre; engine wall 89.5);
    start P1.
  - `until` **{y_gt: 12000}** (NEW axis: e2 t2 ip42's own test); `to` **165**; `avoid` []: e3 is crossed only at its dead
    level.
  - `closed_tris`: **99** = every open tri whose centroid PSX lies outside [-13100, -8700] (0 self-overlaps).
  - **`clearance` 64**: from P1 a route at 60 / 64 / 65, NONE at 66 / 68 / 72 / 80. Freeze 64.
  - `npcs` true (the seated knight at (-586, 3884) lies 300.0 u from the line, outside P 252); `attempts` 3; beat
    `t164_e2`.
  - Not a `cross`: band B still opens tri 90 (PSX -8736) INSIDE e2's XZ ring at its dead level, so a zone finish is not
    level-proof. The zero-new-axis fallback is `until {x_lt: 600}` + `to` 165 (sound: e2 and e3 are XZ-disjoint).
  - **Plan**: 22 waypoints, **6327 u**, loop 2 then the top, PSX -8958 -> -13040, **126.3 run ticks**.
    - It crosses e3's ring at its DEAD level (PSX -9329 / -9528).
    - **e2 fires entering at L 6260 (24.5, 2270.8), PSX -13008** (published y ~13008, margin ~1000), 61 u before the
      goal.
    - ExitField then walks him east along the top (~26 ticks, lesson 4) to Field(165).
  - **THE PINCH** (the ONE squeeze in O8): L 2654-3066, loop 2's north turn, x 906-1301, z 4474-4586, PSX -10621..-10871.
    - The corridor's least half-width is **68.6 at (1202, 4520), PSX -10695**: a ~137-u corridor, **11.4 u a side under
      the radius 80** (O7's 163 foot: 3.3 at 120).
    - Elsewhere on the line the half-width is >= 77.7 at the pinch's ends and 105-200 almost everywhere.
    - The plan at 64 runs ~64 u from walls on ~90% of its length, so the engine pushes him ~16 u outward there (a
      push-out, not a squeeze; dispute 2).
    - ServiceForces averages opposing wall forces x 1.05 (FieldMapActorController.cs:1161-1254), which should hold him
      on the midline. That is unproven in game: **R-SPIRAL is the GO/NO-GO**.
    - Loop 1 crosses the SAME XZ at PSX ~-5600..-5900, so any pinch window carries a y band.
- **Hazards**:
  - e3 is live at the spawn level (157 u); the 5-point region is required in step 0's avoid.
  - Dead-level region crossings: e2 on step 0, e3 on step 1.
  - The knight's talk radius (395: an '!' icon may show at L 4381-4858 of step 1; nothing presses Confirm with control
    held, and the run-wide witness catches outside input).
  - The pinch.
  - No facing gate on either exit.

### CONTROL 2 -- 165 (S) / 31257 (F), entrance 343, SC 1190, visit 2, cell (165, 1190): two steps
- **Grant** ip778 (+ ip844). **Spawn** (2055, 3411), tri 57, y ~10280 (REHEARSE). Radius 120. Engine wall 154.5. **e3
  LIVE 133.6 u**.
- **First move**: **'up+left'** (bearing -9.8; the leg -11.3) for 2 frames at 31.3 fps (3 at 60). Free for 2 ticks
  (~100 u, 0.0 deg off); a 3rd tick touches the west wall's radius line, at most 4.0 deg off, under 16.3. It heads
  north, away from e3 (161 deg behind the leg).
- **STEP 0 -- `walk` "165: the lower stretch to P1"**:
  - goal **(1508, 4698)** (tri 50, PSX -11251, one level; engine wall 178.7); `at_y` **[11100, 11450]**;
  - `avoid` **["165.e3"]** (REQUIRED: band A opens the stairs below the spawn inside e3's live ring);
  - `closed_tris` **64** (outside [-11800, -9500]); `clearance` **120** (130 also routes); `basis` "prior"; `npcs` true
    (165 publishes no other actor); beat `w165_p1`.
  - **Plan**: 3 waypoints, **1452 u**, **29.3 ticks**; least half-width 182; e3 gap >= 134.
- **STEP 1 -- `trigger` "165: the upper stretch into e2 at the top"**:
  - goal **(2489, 3166)** (tri 1, PSX -15169, inside the 4-gon 61.7 u from its west edge, so the 45-u arrival circle lies
    wholly inside e2); `until` **{y_gt: 15000}**; `to` **166**; `avoid` [];
  - `closed_tris` **16** (outside [-16000, -11000]); `clearance` 120; `npcs` true; beat `t165_e2`.
  - **Plan**: 18 waypoints, **6832 u**, **134.4 ticks**; least half-width 138.3 (no squeeze).
    - It crosses e3's ring at its DEAD level (PSX -14698 / -15133).
    - **e2 fires entering at L 6742 (2419.6, 3130.0), PSX -15169** (y 15169, margin 169: the flat top landing).
  - The goal's own wall (107 < 120) never matters: e2 fires ~90 u before it. A `cross` with target 165.e2 is equally
    sound (its ring holds only top tris).

### No control in 166 (S 166 / F 31258)
The only EnableMove (e0 t0 ip423) sits behind `Map.Bit[158]==1`, which nothing sets first; mapvars are zeroed on load. e6
is the defined player and never granted. There is no cell, beat or region in 166. Rule 7 Confirms its pages; rule 9
waits out the movie; a control sample there is V4 (game). The analysis proves 166 through:
- LANDING's crossing 165 -> 166;
- the last pre-cut row 166 e6 t1 ip863;
- PATTERN's 11 rows;
- CHAIN (O3's 61 precedent).

## The knight plan (164 e1; S and F identical bytes)
- **Placement** (t0):
  - ip46 `Bit[3811]` is 0 on every O8 start, so (249, 4630), facing 45. The set variant (-585, 3879) never runs.
  - CreateObject at y POS_COMMAND_DEFAULTY 32768 (EventEngine.Constructor.cs:11; DoEventCode.cs:384); GetTriIdxAtPos
    takes the tri whose centre is nearest that y, i.e. the HIGHEST: **tri 130, PSX -11255 (loop 2)**; loop 1's tri 165
    (-6260) lies under it.
  - ip147 picks the stand anim (521); SetObjectLogicalSize(20, 20, 30) then (4, 20, 30).
- **The engine never pairs him with Steiner across levels.** WalkMesh.Collision (WalkMesh.cs:919-921) and MoveToward's
  collision both need |dy| < 400. Step 0 (loop 1) passes 133.6 u (XZ) from his walk line with |dy| ~5000, so there is
  no contact; `npcs` false keeps the PLANNER from seeing a phantom.
- **Trigger** (t1):
  - ip160 `Bit[3811]==0`; ip178 `obj(uid=250).f[1] > -8400`, JMP_IF back through op_22(1). uid 250 = controlUID
    (EventEngine.cs:950-951).
  - He waits while Steiner's PSX y > -8400 and is released on the first event tick at published y >= 8400: on the
    planned line, T0 = L 5655 (610, 2160).
- **Walk**:
  - ip190 SetWalkSpeed(15), then four synchronous Walks: (-31, 4436), (-246, 4288), (-409, 4128), (-586, 3884). That is
    340.6 + 261.0 + 228.4 + 301.4 = **1131.4 u** along loop 2's north and west sides (PSX -11255 -> -11896).
  - MoveToward moves `speed` a call, NOT slope-scaled (EventEngine.MoveToward.cs:141-142 commented out); a colliding step
    is undone (:186-188). ~75 ticks plus turns.
  - Then ip221 SetStandAnimation(9924), ip225 RunAnimation(**9920: 59 frames at 30**, measured from p0data5 today) +
    ip229 WaitAnimation.
  - Then **ip230 `Bit[3811] := 1`** at ~T0 + 140 +- 8 ticks (~4.7 s), then the t1 idle loop.
  - Seated at (-586, 3884): tri 120, PSX -11896, published y ~11896, static; published r 220 (4 x (20+35)), talk_r 395
    (HarnessAgent.cs:2348-2360).
- **THE HOLD** (opt-in walk key `hold: {flag, value, timeout_s}`, step_of: walk only, requires `at_y`, flag an int in
  0..16383, value 0/1, timeout_s > 0). In `x_walk`, after done's conditions (control held, XZ within tolerance,
  route_to's reached, AND at_y):
  - `g.watch(flag)` (HarnessAgent.cs:840-858 only adds to `_watch`; AppendWatch publishes `"flags"` every 2 frames, with
    NO store and NO trace row);
  - `g.wait_for(flag == value or not control or field changed)`, timeout = min(timeout_s, the run's time left);
  - `g.unwatch()` in a `finally`.
  - Outcomes:
    - value read -> done; the row gets `hold {flag, value, frame, s}`;
    - control gone -> the landing judge (door_loss), else `interrupted`;
    - field changed -> **V11 by the GAME** (dispute 3);
    - timeout -> **V8 by the game** (a hold begun at a proven point past the trigger: x_wait_sc's rule);
    - the run's deadline -> V13 (driver).
  - P1 stands 335 u from e2 and 293.5 u from e3, 2300 u below and ~2500 u (XZ) from the knight's line: no region, no
    contact.
  - Then step 1. `read_end_state` (segment_drive.py:1004-1018) watches and unwatches again at rule 1, with no conflict.
- **THE ORDER CHECK** (per run's 164 visit, S 164 / F 31256): the `w` row 164 e1 t1 ip230 `Bit[3811] := 1`:
  - lies INSIDE step 0's row window [frame0, frame] (the hold included; the bytes put it after T0, so after the release);
  - precedes e2 t2 ip243 by line;
  - never lands after step 1's frame0.
  It is exempt from the walk check there and nowhere else. A run whose 164 visit has NO ip230 row is a MISSING key
  (WRITES).
- **The fake (H25)**, in the UNPINNED `_step_walkers` (segment_regress.py:866-868: `_move_to`, `_step_walkers` and
  `_region_at` stay unpinned): a body that
  - stands at index 0 until the player's published y first reaches 8400 (`start {y_ge: 8400}`, then never held again);
  - walks the 4 legs at 15 u a tick (speed 7.5 at WALKER_FRAME_TICKS 0.5);
  - after `store {after_ticks ~61}` calls `script_store` once (164, 1, 1, 230, Bit 3811 := 1);
  - is then seated, r 220, talk-only, y 11896.
  The MISSING race comes free: a visit's bodies leave with it (fakegame.py:4462-4467). The walker hold should honour
  |dy| < 400 for a body that carries y.

## The movie plan (166 e6 t1; FMV004 PLAYED OUT, no skip, no A/B)
- **The pages**: rule 7 (segment_drive.py:3550-3576) presses Confirm on any published page with control off, then waits
  CUTSCENE_PAGE_TICKS 4. A dropped first Confirm is pressed again on the next poll.
  - Pages 307, 308, 311, 312 and 313 are WindowSync; 309 is WindowAsync (ip345/ip380 land under it either way; ip401
    waits for it to close).
  - No [CHOO] or [TIME=] on any; 310 is not on the route.
  - Keep the pages report-only (never a check that each was pressed).
  - No `no_pages` stop applies (166 has no cell); the stop page is window 56.
- **The movie**:
  - ip601 Map.Bit[146] := 0. ip609 `(SYSVAR[15] & 128) == 0` is always true: FF9FieldFMVDispatch(3) returns only 0, 1 or
    16 (fldfmv.cs:67-82). ip624 RunSoundCode1.
  - **ip633 `Cinematic(0, 9, 1, 1)`**: the engine reads (0, 0x0109, 1), so disc 1, no 9 (fldfmv.cs:56-58) ->
    MBGDiscTable[1][9] = **`MBG_DEF("FMV004", 1, 0)`, type 0** (MBG.cs:830). Init resets attr/status (fldfmv.cs:183-188).
  - ip639-664: wait while SYSVAR[15] != 0 (status 5). ip667 Map.Bit[146] := 1. ip675 op_22(2). ip678 is the play
    condition. **ip711 `Cinematic(2, 0, 0, 0)` plays** (attr |= 1 -> Play -> status 6).
  - ip717-768: wait until (SYSVAR[15] & 127) == 1, i.e. status 8, reached via the finish callback
    `ff9fieldFMVShutdown` -> 7 -> RestoreState -> 8 (fldfmv.cs:191-200).
  - Then op_22(1), FadeFilter(6, 2), op_22(3), ip863, ip871.
  - The live file is MoguriVideo/StreamingAssets/ma/FMV004.bytes: **45.412 s, theora 29.97 fps** (ffprobe today).
    MoguriVideo is 4th in FolderNames, so its copy plays on both sides.
- **No press may reach the movie.** Every Confirm site in the driver is a page, a confirm step, a choice, a name or an
  opt-in policy (`movies` absent, so `movies_of` returns None and rule 9 only sleeps).
  - MovieHitArea arms at MBG.Play (MBG.cs:205-208), which comes after 313 closes and op_22(10) + op_22(25) + op_22(2) +
    the init and its wait + op_22(2): >= ~40 ticks (1.3 s). A press decided on a stale 313 sample (<= ~200 ms) lands
    before it.
  - A stray dialog is answered by the frozen rule: "default" = No, and the movie resumes (FieldHUD.cs:275-287;
    MBG.cs:428-445, 534-542; test_o3_drive_answers_a_skip_dialog_at_its_default).
  - Recommended freeze refusal: a `movies` key.
- **THE STALL FREEZE.**
  - The watchdog signature (segment_drive.py:3427-3429: field, SC, ui, texts, choice, control, x/8, z/8, trace rows) is
    STATIC from the ip502 row to the ip863 row: ~1.1 s of fades and waits + the init + 45.4 s + ~0.2 s. Expect ~47-51 s;
    O3's FMV003 stretch was 90.1 / 90.3 s against an 84.8-s file.
  - O7's frozen 60 would leave ~10 s, and V14 is attributed to the game: one hitch on one side would read VOID-ASYM NOT
    PROVEN.
  - **Freeze `no_progress_s` = max(60, 3 x the longest no-progress stretch of any traced stage)**, O3's and O7's own F8
    rule (~150 s). Refuse anything under 2 x that stretch (PLAN.md's floor).
- **fps**: plan nothing in ticks across the movie. **Pin `[Graphics] VSync = "1"` in P-SETTINGS**: the movie's wall time
  and the measured stretch depend on it (MovieMaterial's clock), and today it is unpinned.
- **The trace keeps writing** through the movie and across Field(55): a field change opens no epoch (StoryTrace.cs:97).
  O3's story-o3 kept one `arm` epoch through FMV003 and its 31213 -> 64 seam.
- **The fake**: model 166 as an H9 scene (pages, then `{movie: N}`, then the move to 55), with rows through
  `fake.script_store`. Do NOT add a `movie` step to the pinned `_VisitBeat` (G21: FAKE_PIN_CLASSES_O5).

## The seam and end plan
- **side_ends** {S: [55], F: [55]}; `members` = O4's twenty exactly (o4_forks.json); no O1 id (31200-31219) and no member
  whose donor is 55. These are freeze refusals.
- **Rule 1** (segment_drive.py:3411-3425) fires on the first poll publishing field 55 on either side, BEFORE rule 2: it
  reads the end state, waits `end_row_s` 10 for the first row in place 55 (55 e0 t0 ip22) and returns "reached". On F a
  REAL 164/165/166 is V19 (rule 2's `due` member, :3446-3455); a landing in 31205 is impossible (raw `Field(55)`, no
  remap).
- **The cut** at 55 e0 t0 ip22 on both sides: `cut_at_end` (segment_trace.py:137-146) drops every `w`/`r` row of place 55
  and every `c` row of place 55, and keeps all `e` rows.
- **THE SEAM is recorded through the `off` row.** `collect_story` stops the trace after the drive returns, with the game
  standing in 55, so the kept `e off fld 55` row makes `_walk_seams` (storytrace.py:838-877) record
  **Seam(frm 31258, donor 166, to 55, fields [55])**.
  - Its exit row is the last `w` row in 31258: **e6 t1 ip863 Int16[2] 344 -> 110**.
  - There is no seam key (55's `w` rows are all cut).
  - This is exactly O3's: story-o3 run2_F line 111 `e off fld 64`, "1 seam crossing(s)", "every seam member(63)
    [31213] -> 64".
- **O7's LANDING (e) FAILS every O8 F run** (o7_castle_walk.py:2734-2739 demands no seam). **O2's `seam_check`**
  (o2_alexandria.py:1386-1407) passes VACUOUSLY with no seam.
- **O8-SEAM** (replaces LANDING (e)), per covered F run:
  - (a) exactly ONE Seam, `(frm, donor, to, fields) == (31258, 166, 55, [55])`;
  - (b) its exit row `(fld, sid, tag, ip, target, old, new) == (31258, 6, 1, 863, Int16[2], 344, 110)`;
  - (c) no seam key; the comparison's `across_seam` and `seam_only` empty;
  - (d) the cut row read from the UNCUT trace (O3's `r["cut_row"]`) is `w` fld 55, don 55, e0 t0 ip22 `Bit[191] := 0`;
  - (e) in the uncut trace the row before the cut row (`c`/`e` aside) is the ip863 row on both sides, by place. In game,
    O7's 163 ip227 -> 164 ip22 (4 frames) and O3's 31213 ip820 -> 64 ip22 (3 frames) had nothing between;
  - (f) ZERO seams is a FAIL, never a vacuous pass.
  The predictions carry `seam` {donor 166, to 55, why}.
- **LANDING (a)-(d)** keep O7's shape:
  - route_places [164, 165, 166];
  - crossings 164 e2 t2 ip243 (343) -> 165 e0 t0 ip22 and 165 e2 t2 ip233 (344) -> 166 e0 t0 ip22;
  - last 166 e6 t1 ip863 (110); end_row 55 e0 t0 ip22.
  O3's A-NOEND (o3_prima_vista.py:1228-1233) covers a 55 row that never came.
- **End state**: generalise O7's `RACED` (one constant, :134; `_end_state` :712-734; freeze :2125-2126) to a SET DERIVED
  from 55's bytes and the pattern: the targets 55 e0 t0 writes before its first long yield to a value other than the
  last pre-cut one, i.e. {Int16[2], Byte[8]}.
  - Each goes into `end_state_trace` at its site by place (166 e6 t1 ip863 = 110, ip502 = 0; 31258 on F).
  - The live read is recorded and never compared; SC stays live.
  - `state_check (c)` (:2922-2952) already iterates `end_state_trace`.
- **The draft with a real end**:
  - `route_members` raises for 55 (:156-165), so take members for 164-166 only.
  - **P-DONOR as O5-O7 call it (route + end_fields, o5_hallway.py:1446) FAILS on the live install today**, on O1's
    `31205 55` row. Call it over the route donors [164, 165, 166] (O3's call), with a line naming that row as outside
    the set.
  - P-DONOR-LOG over [164, 165, 166, 55]; `stock_fields` [164, 165, 166, 55] (real 55 runs on both sides); P-TEXT stays
    on block 3, strict (no check reads 55's block-2 text before the cut).
- **Recovery from every place**: end_run warps FIRST (segment_trace.py:537-596), because the soft reset is dead during a
  movie (UIKeyTrigger.cs:237-344). The debug warp needs only FieldHUD (Ff9mkDebugMenu.cs:2083), and that is the UIState
  during a type-0 movie (O3: the 90-s stretch at ui FieldHUD) and with a page up (O7 R-WALK-VOID page_stop: title in
  4.5 s). From mid-FMV003, O3's F-SMOKE acked `warp 4600` about 8 s into the movie. In 55 the scene halts at page 129,
  still FieldHUD. Unproven: a stop while a stray skip dialog is up.
- **O9 contiguity**: O8 ends at 55@110 (cut 55 e0 t0 ip22). O9 would start with a raw warp into 55@110 (S) / O1's
  31205@110 (F): F switches chains there (O4 alxc -> O1 tshp). Record it in PLAN.md; it is not O8's to fix.

## Disputes settled (reader claims vs the bytes / engine / walkmesh / code)
1. **"The 164 spawn is 68 u from a wall, under the radius 80" (PLAN.md's handoff, O7 research; walk-machinery reader
   took it as a wall) vs "95.8 u, the 68 is a planner artefact" (walks reader).**
   - SETTLED for the walks reader (r1 + the tri dump). z = 3267 is tri 145's edge to **tri 154 (PSX -4688, centroid
     just past band A's -4700)**, closed only in the PLANNER's band-A floor. In the engine tri 154 is open, and
     RadiusValid walks through it.
   - The nearest engine wall is **95.8 u** (east edge (2130, 3517)-(2138, 3267) via tri 158); the west wall is 176.2.
     The raw PlayerWalkmesh also reads 95.8.
   - So there is no push-out at the spawn or on the first move (offline: 0.0 deg). The prior basis is still right, for
     ANOTHER reason: e3 is LIVE 157 u away, and a probe could fire it.
2. **164 step 1: "ONE pinch, 68.6 half-width" (walks reader) vs "a continuous squeeze: 5718 of 6327 u under 80 from a
   wall, local maxima 67-74 at five more places" (walk-machinery reader).**
   - SETTLED for ONE pinch. Engine-view cross-sections along the plan (perpendicular, walked out on the level) give one
     narrow stretch, L 2654-3066 (loop 2's north turn), min **68.6 at (1202, 4520) PSX -10695**.
   - At the walk-machinery reader's other points the corridor is wide: (-287, 3834) 182, (-390, 3266) 199, (-70, 4159)
     148, (241, 4402) 144. A second method, the max engine wall within 160 u on the same level, gives 192 / 203 / 149 /
     146.
   - Their "5718 of 6327 u" is the PLANNED line's own distance to the wall (a plan at clearance 64 runs ~64 u from
     walls): the engine pushes him ~16 u outward there, which is not a squeeze.
   - The fake's stop at slack 8 and pass at 12 is consistent with one pinch at 68.6. The O7 research's "140-144 u band"
     at the turn is the same pinch.
3. **A field change during THE HOLD: V11 by the driver (x_wait_sc's precedent, segment_drive.py:2994-2999) vs by the game
   (walk-machinery reader); the walks reader and the O7 research leave it unattributed.**
   - SETTLED: **V11 by the GAME**. The hold presses nothing, and P1 stands 335 / 293.5 u from e2 / e3 (O8-GOALS proves
     it offline), so only the game's own script can move the field.
   - This mirrors the hold's timeout (V8 by the game, x_wait_sc's "a wait begun AT the point is the game's"). x_wait_sc's
     driver attribution covers a wait point the walk chose near doors; P1 is proven clear.
4. **`no_progress_s`: ">= 2 x R-FULL's static span, ~100 s" (PLAN.md, O7 research) vs "max(60, 3 x the longest
   stretch), ~145 s" (movie reader).**
   - SETTLED for F8's own formula (O3 froze 271 = 3 x 90.3; O7 max(60, 3 x 1.1)). That gives ~150 s, and the freeze
     refuses anything under PLAN.md's 2x floor.
5. **The movie's fps: "MBG sets the target fps to the movie's: plan nothing in ticks" (bytes reader, O7 research) vs
   "SetTargetFPS is ignored under VSync 1" (movie reader).**
   - SETTLED: both true. MBG.cs:217 calls SetTargetFPS(30); FPSManager.cs:41-48 keeps vSyncCount 1 under the live
     VSync = 1, and Unity ignores targetFrameRate then. O3 measured fps 60 / 58.6 before, during and after FMV003.
   - Plan nothing in ticks across it, and pin VSync.
6. **165 step 1's goal: (2489, 3166) (O7 research, walks reader) vs region_goal (2773, 3153) (the walks reader's
   "sounder" alternative).**
   - SETTLED: keep (2489, 3166). It lies inside the 4-gon, 61.7 u from the west edge, so the whole 45-u arrival circle
     is inside e2. The planned route enters e2 at (2419.6, 3130) at y 15169, ~90 u before the goal, and the planner
     routes to it at 120 and 130 (verified). Its wall (107 < 120) is never reached.
7. **The knight's walk vs `_npc_levels` / a phantom on step 0.**
   - Not disputed, CONFIRMED in the engine: WalkMesh.Collision pairs actors only at |dy| < 400 (WalkMesh.cs:919-921), so
     the engine never pairs him with Steiner on loop 1.
   - `npcs` false is required for the PLANNER only.
8. **166's e1 "sets Map.Byte[24] at the scene's end" (walks reader).**
   - SETTLED: e1 is NOT instanced in 166 (Main_Init inits only 6, 3, 5). It stores nothing global either way.
9. **The warp window's second edge (start-state reader, new).**
   - SETTLED as a design fix: a warp after 70 ip475 is SILENT at 164 (K = 385: no error path), unlike O7's 154. Register
     164 ip130 as a start read (old 1, raced store 70 ip475) so it is A-START, never NOT PROVEN.
10. **The squeeze slack for 164's fake level: ">= 11.4" (walks reader) vs ">= 12" (walk-machinery reader).**
    - Consistent: the bound is radius - slack <= 68.6, so slack >= 11.4. Take 12 as an estimate; R-SPIRAL's narrowest
      gap freezes it.
11. **P-FLOOR "raw-diff" for 31257 (fork reader's output line) vs "raw byte-equal" (its summary).**
    - SETTLED: the summary's "raw-diff" compares against the ROUND-TRIPPED stock (6376 -> 6374 B). The deployed bytes
      equal the raw stock bundle; the normalised compare passes.

## Harness gaps (ordered by risk; each the smallest opt-in fix -- O1-O7 drive and analyse exactly as before)
1. **RISK -- THE PINCH at radius 80** (164 step 1, one ~137-u corridor, 11.4 u a side under the radius).
   - A stall there lets `unstick` place a phantom blocker of radius OBSTACLE_R_W 192 (session.py:4985-4995) that seals
     the corridor.
   - Fix: zero-code `attempts` 3, and THE PINCH WINDOW in R-SPIRAL (with a y band). Only on R-SPIRAL evidence, an opt-in
     per-step `unstick: false` (walk_kw: `unstick=bool(step.get("unstick", True))`) with that step's `npcs` false (the
     seated knight is 300 u off the line).
2. **GAP -- the bit `hold`** (none exists; step_of knows no key).
   - Fix: the opt-in walk key above, in x_walk; the row's `hold`; V-classes V8 / V11 (game), V13 (deadline); FakeGame
     H25.
3. **GAP -- `at_y`** (x_walk's done and route_to's reached are XZ only: segment_drive.py:3033-3039, session.py:4756-4758;
   `sample()` has no y, :788-792).
   - Fix: walk only; in x_walk done adds `lo <= st.player_y <= hi`, else `failed` naming the y; the row gets
     `at_y {band, y}`.
4. **GAP -- a y axis on `until`, and the loss's y** (`until_ok` raises on y, :308-320; the probe's `lost` has no y,
   session.py:822-827).
   - Fix: `until_ok(expr, x, z, y=None)` with y_le/lt/ge/gt (a missing y reads False); step_of validates with
     `until_ok(u, 0, 0, 0)`.
   - In x_trigger / x_trigger_to, ONLY when the until has a y term, read y off the ring sample at `lost["frame"]`
     (`ring_since`, :1712-1719; STATE_RING 300 samples) and put it on the row's `lost`. session.py is untouched.
5. **RISK -- `step_of` passes unknown keys silently** (:362-414): a table with `at_y` or `hold` today drives WITHOUT them,
   a check that cannot fail.
   - Fix: validate `at_y` and `hold` explicitly in step_of, plus an O8-local offline refusal of any step key outside
     KNOWN_STEP_KEYS (a global whitelist could break O1-O7 fixtures).
6. **GAP -- the seam**: O7 LANDING (e) fails every O8 F run, and O2's seam_check is vacuous with zero seams. Fix: O8-SEAM
   (a)-(f) above.
7. **GAP -- the end-state race**: RACED is one constant. Fix: a derived set {Int16[2], Byte[8]}.
8. **GAP -- the draft and preflight with a real end**: route_members raises for 55; P-DONOR (route + end) fails on
   `31205 55`; `stock_fields` lacks 55. Fix: route donors only, as above.
9. **GAP -- O7's offline checks misread O8's steps**:
   - `visit_windows` takes doors from `target` only (:1334-1335), so the until-triggers' door rows (164 e2 t2 ip243, 165
     e2 t2 ip205/233) are unexempt;
   - walk_check (a) raises KeyError on an until-trigger with no target (:2810-2819);
   - goals_extra7 (g2)/(g3) fail by construction (:1731-1735, :1770-1799);
   - `height_test` reads only `f[1] < c` (B_LT, :892, :927-931), so 164 e3 and 165 e3 are B_GT gates it cannot read;
   - ENGINE_RADIUS 120 is hard-coded (:112), but 164's is 80.
   - Fix (O8-local, O7's untouched):
     - register every exit with a `gate` read off its pinned tag 2 (`f[1] < -12000` -> y_gt 12000; `f[1] > -6000` ->
       y_lt 6000; 165: y_gt 15000 / y_lt 11000);
     - (g2') exempt an exit whose gate cannot hold on any open tri of the step's floor inside its polygon, and the
       trigger's own door (the exit leading to `to`);
     - (g3') uses at_y; a per-place engine radius {164: 80, 165: 120};
     - doors from `to`;
     - ip230 exempt only inside step 0's row.
10. **GAP -- O7-KEYS' carried scan vs the knight's talk.** Fix: narrow `instanced_texts` for the carried scan to the
    functions the route runs (drop tag 3 and what only it calls).
11. **GAP -- the stall watchdog and budget across FMV004.** Fix: freeze `no_progress_s` and the budget by F8 from R-FULL
    (numbers, no code); recommended freeze refusal under 2x the span.
12. **GAP -- the late-warp race is silent at 164.** Fix: the second start read (164 ip130, old 1, raced store 70 ip475),
    with the A-START wording naming it.
13. **GAP -- FakeGame**:
    - one global `clearance` (fakegame.py:418), so add a per-field override (164 at 80, 165 at 120) or keep the real-floor
      tests per field;
    - 164's Levels needs `squeeze_slack >= 12` (an existing constructor knob);
    - H25 (the knight walker);
    - 166 as an H9 scene with a movie.
    H20's spiral premises hold on 164/165 (walk-machinery reader: steepest 60-u step 93.5 / 76.7, least stacked gap
    4857.6 / 4774.1, 0 edge mismatches). Extend test_fake_level_meshes_hold_the_levels_premises to 164 and 165.
14. **GAP -- rehearsal stops for a movie and a hold.** O7's stops are input hooks (`hold_stop` wraps `g.send`,
    `page_stop` wraps `g.press`); during FMV004 and THE HOLD the driver sends nothing.
    - Fix: a rehearsal-only `movie_stop {place 166, after_s N}` raised from the drive's `observe` hook (:3406-3408) on the
      first poll in place 166 with no window and control off, >= N s after the 313 press row.
    - A `hold_stop` variant that raises on the hold's first poll.
    - Both are refused by the freeze like REHEARSAL_OVERLAYS.
15. **RISK -- VSync unpinned.** Fix: add `[Graphics] VSync = "1"` to O8's SETTINGS (P-SETTINGS).
16. **GAP -- no driver test ends F in a REAL field under side_ends.** Fix: one fake driver test (F reaches real 55 from
    member(166): reached; the same chain landing in real 166: V19).
17. **READY**, with configuration only:
    - S18 clearance; S19 prior basis and forget;
    - `npcs` false; regions from the bytes' SetRegion (the 5-point `region`, never scan_gateways' 4-point `zone`);
    - H22 door y-terms (`y_gt` / `y_le`, DOOR_KEYS fakegame.py:4053);
    - rule 7 pages; no Confirm in the movie; the skip dialog at its default;
    - rule 1 / V19; the trace across the seam; end_run from every place.

## Fork gates (summary; the gates reader, re-checked where it mattered)
Nothing on O8's route can make F's gEventGlobal writes differ from S's:
- The only field-id gate reached is **DoEventCode.cs:1507**, Steiner's radius in 164. It goes through EffectiveFieldId
  (:25), so 31256 has it too; it changes geometry only.
- FMV004's lookup takes no field id (fldfmv.cs:56-58 -> MBG.cs:830). fldfmv.cs:112's `EffectiveFieldId == 100` does not
  apply. MBG.cs's raw 2752/2933 tests evaluate the same for 166 and 31258.
- `Field(55)` does no remap; ForkSiblingField is only world -> field and the battle return.
- QuadCircleData has no 164/165 row.
- Autosave lists, NarrowMapList, VIB/animation donor-name loads, SPS (carried: 31256's 347/349/351/353, 31257's
  46/47/48/53/54), map config, sound, text zone (`FieldZoneId == 166` is Daguerreo's text ZONE), ATE, the harness warp
  and the trace's field key: each wrapped, symmetric, or without rows for these ids.
- P-ENGINE: the live x64/x86 DLL hashes ba976242 = O7's pin (re-hash before the freeze and the session).
- O8-BUILD should pin the 31258 case explicitly: byte-identical to 166 in each language AND its e6 t1 ip871 `Field(55)`
  RAW. A rule of "only in-chain Field() operands differ" passes trivially at zero diffs.

## Rehearsals before the freeze (O7's shape, adapted; `o8_rehearse.py`)
| stage | runs | the warp / end | settles |
|---|---|---|---|
| **R-FULL** (the go/no-go and the predictions; the ONLY stage whose traces define keys, start, pattern or end state) | 2 | `warp 164 342 1190` / [55] | F1-F8, F10, F11, F14: both grants (y), both first moves, every step (route, holds, slides, stalls, losses, landings), THE HOLD (T0, ip230's tick, its seconds), the pinch, the dead-level region crossings, 166's pages, FMV004's static span, the 166 -> 55 crossing (ip863 then 55 ip22, nothing between), the cut, the 23 keys and 6 masked rows, the pattern, the end state (live, and Int16[2] / Byte[8] from the trace), the run time, the longest no-progress stretch, the render rate |
| **R-SPIRAL** | 2 | `warp 164 342 1190` / [165] | F2, F5: 164's grant y ~4780, the 'left' first move, step 0's arrival at_y, THE KNIGHT (T0, ip230 at ~T0+140, the hold's seconds, his seated reading at (-586, 3884)), step 1 through **THE PINCH WINDOW {place 164, x 900-1310, z 4460-4600, published y 10400-11100}** (loop 1 crosses the same XZ at y ~5600-5900: the y band is required; every hold starting or ending in it, every ladder rung after one, the narrowest gap), e2's loss y (~13008), the landing 165 |
| R-SPIRAL165 (optional, by name) | 2 | `warp 165 343 1190` / [166] | F4: 165's grant y ~10280, 'up+left' (<= 4 deg), step 0's at_y, e3's dead-level crossings with no loss, e2's loss y ~15169, the landing 166 |
| **R-FMV** | 2 | `warp 166 344 1190` / [55] | F3: pages 307-313 under rule 7 (a dropped first Confirm recorded), no press after 313 closes, no skip dialog, the static span ip502 -> ip863, ui FieldHUD and fps during it, 55's cut row, the live end-state reads. The warp is clean: 166 ip119 from the warp's Byte[13] 1, ip255 125 -> 125 |
| **R-VOID** (by name, last) | 3 | run 1 164 (stop on THE HOLD's first poll), run 2 164 (hold_stop inside THE PINCH WINDOW), run 3 166 (`movie_stop`, N ~ 15 s) | F9: each V13 (the driver's), nothing pressed after the raise, `recover-warp` 4600, the title (O7: 4.4-4.5 s); run 3 is THE mid-FMV004 recovery |
| **F-SMOKE** (untraced, by name) | 6 warps | `31256 342`/`164 342`, `31257 343`/`165 343`, `31258 344`/`166 344` | F12: each member loads at its entrance and SC, its object sids EQUAL to its twin's after `smoke_s` (31258's mid-scene; end_run from a page or the scene) |
| **F-PASS** (untraced, before the freeze) | 1 | `warp 31256 342 1190` / REAL [55] | F13: every beat on 31256 (the radius-80 pinch through EffectiveFieldId) and 31257, the hold, 31258's pages and FMV004 played out, the landing in REAL 55 (rule 1, never V19), no exception. It may only STOP the session |

**The freeze checklist (O7's F1-F14, adapted):**
- **F1 grants**: 164 within 64 u of (2040, 3335) at published y 4780 +- 30; 165 within 64 u of (2055, 3411) at y
  10280 +- 30. A grant on another level STOPS the freeze.
- **F2 164 + the knight**: no probe; one `basis_check` within 16.3 deg (expect ~0); step 0 done within attempts, its end
  within 45 u of P1 at y in [8800, 9150]; no loss on the dead-level e2 crossings; the hold done in every run; ip230 inside
  step 0's row and before ip243; `hold.timeout_s` = max(15, 3 x the longest hold).
- **F3 166**: the six pages seen and pressed; no press after 313 until the movie ended; ip255 before ip345.
- **F4 165**: one basis_check <= 16.3 deg (expect <= 4); step 0 at_y; step 1's loss in 165.e2 at y > 15000 (expect
  15169); no loss on the dead-level e3 crossings.
- **F5 THE PINCH (the go/no-go)**: GO when every R-SPIRAL and R-FULL run does 164 step 1 within its attempts with no V7
  AND no ladder rung (wait, push, blocker, frozen, boxed) after a hold starting or ending in THE PINCH WINDOW. Record the
  narrowest gap for the fake's squeeze_slack. NO-GO: the opt-in `unstick: false` (+ `npcs` false) on 164 #1, then
  R-SPIRAL again; still NO-GO -> the owner (the only owner decision below).
- **F6 keys / pattern**: exactly 23 keys + 6 masked rows, 29 rows (9 / 9 / 11), the 4 residue rows and none after;
  164's first `w` row ip22 and first Byte[13] row ip130 from old 1; no error / dead / forbidden row; no `c` row; the cut
  55 e0 t0 ip22; the two runs identical bar frames.
- **F7 end state**: the live end state (without Int16[2] / Byte[8]) equals the draft's; the trace's last pre-cut
  Int16[2] is 166 ip863 = 110 and Byte[8] is ip502 = 0; the live reads recorded (expect 106 / 125 or 110 / 0), never
  compared.
- **F8 budgets**: `run_s` 2 x the slowest R-FULL; `run_min_s` 1.25 x the median + the longest recovery; `session_s` 8 x
  the median + 1800; `no_progress_s` max(60, 3 x the longest stretch of any traced stage) (~150 s; refused under 2x);
  `settle_s` 1.0; `end_row_s` 10.
- **F9 recovery**: R-VOID's three stops; R-FULL's end_run from real 55.
- **F10 settings / launch**: P-SETTINGS (+ VSync), P-PAD, P-OVERRIDE, P-ENGINE, P-LAUNCH, P-DONOR-LOG (164, 165, 166,
  55) on the rehearsal launch.
- **F11**: no `input` row.
- **F12**: F-SMOKE's three pairs equal.
- **F13**: F-PASS reached REAL 55 cleanly.
- **F14 render rates**: recorded; a rate no stage met is named in PLAN.md (60 fps unexercised so far for walks).

**Then `--freeze` (v1)**:
- O8 `freeze_problems` refuses:
  - any rehearsal overlay (`hold_stop`, `page_stop`, `movie_stop`, the hold stop); a `movies` key;
  - side_ends != {S: [55], F: [55]}; `members` != O4's twenty; any O1 id;
  - Int16[2] / Byte[8] / a carried target in `end_state`;
  - `no_progress_s` < 2 x the rehearsals' longest stretch;
  - a step without `clearance`;
  - 164 #0 without `at_y` + `hold` + `avoid` ["164.e3"] + `basis` "prior" + `npcs` false;
  - 164 #1 without `until {y_gt}` + `to` 165 + clearance 64;
  - 165 #0 without `avoid` ["165.e3"] + `at_y`; 165 #1 without `until {y_gt}` + `to` 166;
  - VSync unpinned.
- Then `--preflight`, the session (`py tools/play.py studies/story-trace/o8_<name>.py --label story-o8 --timeout 240`),
  one whole-file `harness_tests.py whole` and `segment_regress.py --pytest-junit` on its receipt. The O8 dry run uses
  `frozen_through(8)`. Copy the rehearsal and session run dirs into the MAIN repo's `.harness-runs/` before the gate.

## Owner decisions
None is needed now: the end, the movie and the seam are decided (option 1).

The only conditional one is if F5 is NO-GO after the opt-in `unstick: false` re-rehearsal. Then the owner chooses
between re-opening the split (option 2's 164 -> 166 walk segment) and another walk fallback. **Recommended:** report the
measured pinch and ask; do not change the end without the owner.

## Could not determine / unverified
In game, nothing about 164's walks, 165 or 166 has a proof yet:
- the grants (y ~4780 / ~10280);
- the first moves on a ramp;
- the pinch at radius 80;
- the dead-level region walk-throughs;
- the knight's ip230 tick (estimate ~T0+140 +- 8) and his seated reading;
- 166's pages under rule 7 (307's crawl);
- FMV004's static span (~47-51 s estimated) and the render rate during it;
- the 166 -> 55 crossing (no `r` row before 55 ip22; the published field id across the 31258 -> 55 load);
- whether 55 ip342 lands in the cut's frame (it races either way);
- a stray skip dialog answered No in game; a stop while that dialog is up;
- 60 fps for any O8 walk.

Offline, taken from the readers without re-running:
- the 7-language member diffs and P-EB / P-FLOOR / text-block equalities (the fork reader's `forkdiff7.out`,
  `preflight_parts.out`, `textcheck.py`; only the US decode and the live registrations were re-checked here);
- the FakeGame H20 premises on 164/165 and the hand-stepped fake's stop point (walk-machinery reader's `fake_spiral.py`);
- the deployed DLL's IL (inferred from Output's sha = live, with no newer .cs);
- the carried .sps / spt.tcb bytes vs the donor bundle (names and ids only);
- the embedded mapExtraOffsetList rows (wrapped, cosmetic).
