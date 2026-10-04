# Stock O7 route: raw warp into 154 (FieldEntrance 315, SC 1190) -> the balcony and the west flight -> 158 -> 159 (the forced monologue) -> 160 -> 162 -> 163 -> Field(164) at 342  (reconciled; SPLIT -- O8 = 164 -> 165 -> 166 -> FMV004 -> real 55)

The reconciler's own decode. Every ip below was decoded from the stock US `.eb` by `reconcile/ebtool.py` (O6's
reconciler decoder: storytrace.stock_script_source + ScriptIndex + instruction_stores, run over this worktree's
ff9mapkit, d6b77975) and checked against the listing. Engine claims were re-read in C:\gd\FFIX\Memoria (the deployed
x64/x86 Assembly-CSharp.dll sha256 ba976242..., Sep 26 17:10, no newer .cs: the gates reader's check, O6's pinned engine).
- `ip` = abs - entry start = the s88 trace ip. `Lnnn` = offset from the function start (the predictions' `off`).
- Listings `reconcile/L{154,158..166,55,70}.txt` are byte-identical (cmp) to the bytes, data and walks readers' copies
  and to O6's reconcile listings: NO reader decoded different bytes; every dispute below is interpretive.
- `SWITCH(base, default, case_base, case_base+1, ...)`; `SWITCHEX(default, value, target, ...)`. 2-byte constants are
  SIGNED: 65436 = -100, 57136 = -8400, 59536 = -6000, 53536 = -12000, 50536 = -15000, 63936 = -1600, 65535 = -1.
- Heights: PSX y (up negative) = the kit walkmesh's y = the script's `f[1]` (`-pos[1]`, EBin.cs:1791). The harness
  publishes `player.y = pos[1]` (HarnessAgent.cs:1559) = -PSX y: it RISES as he climbs (lesson 5).
- Walk numbers were RE-PLANNED here (`reconcile/vwalk.py`, `vwalk2.py`, `v154.py`, `vsteps.py`: extract.stock_walkmesh +
  PlayerWalkmesh(closed) + route_avoiding(margin 56, leave_wall) -- exactly route_to's call); member facts re-read from
  the live FF9CustomMap in all 7 languages (`reconcile/members.py`); FMV004 re-measured with ffprobe. The reconciled
  step table (exact closures) is `reconcile/o7_steps_reconciled.json`.

## Segment end: CHOSEN = a SPLIT. O7 ends on arrival in 164 at 342 (163 e2 t2 ip235 `Field(164)`, after ip227 `Int16[2]:=342`), SC 1190; O8 starts there

| # | exit (stock) | arrival | SC | est. min a run | new harness it needs | inside (cumulative) |
|---|---|---|---|---|---|---|
| 1 | 154 e8 t2 ip363 `Field(158)` (300, ip355) | 158@300 | 1190 | ~0.7 | the WALK step kind | 154: balcony -> west flight -> ground, the ground door |
| 2 | 158 e2 t2 ip230 (331, ip222) | 159@331 | 1190 | ~0.85 | as 1 | + 158 (the live door store `Byte[13]:=3` ip194) |
| 3 | 159 e11 t2 ip201 (332, ip193) | 160@332 | 1190 | ~1.3 | as 1 | + 159's forced monologue (5 pages, Byte[208], Bit[3796]) |
| 4-5 | 160 e5 t2 ip235 (333) / 162 e3 t2 ip235 (341) | 162 / 163 | 1190 | ~1.5 / ~1.6 | as 1 | + 160, 162 (back doors 61 / 50 u from the spawns) |
| **6 CHOSEN** | **163 e2 t2 ip235 `Field(164)` (342, ip227)** | **164@342** | **1190** | **~1.8** | **the WALK kind only** | **+ 163's stair (a squeeze at radius 120)** |
| 7 | 164 e2 t2 ip251 (343, ip243) | 165@343 | 1190 | ~2.2 | + per-step clearance 64, height evidence, the knight hold, FakeGame spiral/walker | + the first spiral and the knight's race |
| 8 | 165 e2 t2 ip241 (344, ip233) | 166@344 | 1190 | ~2.4 | as 7 | + the second spiral |
| 9 | 166 e6 t1 ip871 `Field(55)` (110, ip863) | REAL 55 both sides | 1190 | ~3.75 | as 7 + a movie stall freeze | + 166's 6 pages, FMV004 (45.41 s), the seam (the bytes/data/start/gates readers' pick) |
| 10 | 55 e10 t1 ip582 `SC:=1400` | -- | 1400 | ~4.3 | + an end-on-store kind; 31258 rebuilt (owner) | + 55's start-dependent branch e8 t1 ip1354 |

Run times: calibrated on O6's MEASURED R-DOOR (89-99 s for 151 -> 154 incl. New Game and the warp) plus the walks
reader's slope-scaled ticks (154 140+58, 158 48, 159 47+25, 160 66, 162 66, 163 62 ticks), ~3 s calibration on a
field's first walk, ~2 s of settles a step, ~2.5 s a transition and ~2.5 s a page. Freeze the budget from R-FULL.

Why the split at 6:
- **The risk lives in 164/165, and four of the five new harness needs live only there**: the per-step clearance (164's
  narrow turn plans only at <= 64, re-planned: none at 66/67/68/72/80 from P1, the engine's radius there 80), the
  height evidence, the knight hold, the FakeGame spiral + height-triggered walker -- plus the two weakest calibration
  spawns of the whole route (164: a wall 68 u from the spawn, under the radius 80; 165: e3 live 134 u away) and two
  5-point regions with dead centres. Nothing of that has an in-game proof.
- **O7 to 164 needs ONE new step kind** (`walk`, for 154's two levels) and FakeGame two-level support; everything else
  is existing machinery: `cross` steps with `avoid`/`closed_tris`, `interrupts: 1` for the monologue (rule 7 + rule 8),
  the arrival end (rule 1, `side_ends`). ~1.8 min a run (O6: ~1.6).
- **A clean member end**: the chain 31246 -> 31250 -> ... -> 31255 -> 31256 is closed (every route `Field()`
  retargeted, all 7 languages), so `side_ends` {S: [164], F: [31256]} as O4-O6. No seam, no movie, no rebuild.
- **O8's start is clean** (below): a raw warp into 164 at 342 lands where a chained run lands (e7 t0 picks the spawn by
  `Int16[2]` alone) with no start-dependent value or path up to the arrival in 55.
- **Contiguity**: O7 ends where O8 starts (164@342), O8 ends where O9 starts (real 55 at 110: a raw warp into 55 /
  O1's member(55) 31205, the O3 -> O4 hand-off shape). Nothing on the opening's path falls between segments.
- **Why not 9 (one segment, the readers' pick)**: all of O7's and O8's new machinery and every in-game unknown at once,
  ~3.75 min a run; one failing spiral rehearsal would hold the whole stretch. O6's reconciler rejected the same end for
  the same reason ("six new risks in one segment"); O5 ended early to keep its end clean.
- **Why not earlier (1-5)**: each only drops crosses with existing machinery; 163's squeeze is worth proving before the
  spirals (the same engine push-out the narrow turn relies on). **Why not 8**: it carries all of 7's new needs and
  leaves O8 a ~1.2-min movie segment.
- **Fallback if R-STAIR fails** (163 stalls repeatedly): end O7 on arrival in 163 at 341 (162 e3 t2 ip235), side_ends
  {S: [163], F: [31255]}, and move 163 into O8.

## O8 -- where it starts and how its start is built (settled here for O8's design)
- **Route**: raw warp into 164 at 342 -> 164 (walk + the knight hold to P1; trigger into e2 at the top, clearance 64)
  -> 165 (walk; trigger into e2 at the top) -> 166 (no control: six pages, FMV004 played out) -> `Field(55)` -> END on
  arrival in REAL 55 at 110 on both sides (member(166) 31258 keeps a raw `Field(55)`), cut at 55 e0 t0 ip22. SC 1190
  throughout. ~2.3 min a run with FMV004 played out.
- **Start**: New Game, `storytrace 1`, in field 70 (FieldHUD; after 70 e0 t0 ip130, before ip475 -- O7's window, kept for
  uniformity, though 164 takes ip130 for any incoming Byte[13] but 9): `warp 164 342 1190` (S) / `warp 31256 342 1190`
  (F). FOUR residue rows: SC 1190 = 0x04A6 -> byte 0 (0->166), byte 1 (0->4); FieldEntrance 342 = 0x0156 -> byte 2
  (0->86), byte 3 (0->1). START row 164 e0 t0 ip22. START requires 164 ip130 (`Byte[13]` 1 -> 1, same); its ip97 is
  DEAD at 164 (`Int16[9]` is 385 there, so `Byte[13]==2 && Int16[9]<0` never holds) and window 56 (ip581-607) needs an
  incoming 9.
- **Start-dependent keys to the 55 arrival: none in value or path.** Old/same only: 164 ip57 `Int16[9]` (raw 643 -> 385
  | after O7 385 -> 385 same), 164 ip130 `Byte[13]` (raw 1 -> 1 same | after O7 2 -> 1), 166 e6 t1 ip345 `Byte[208]`
  (raw 0 -> 0 same | after O7 1 -> 0). Bit[3811] 0 both (the knight is placed and races the same way); Bit[3855]/[3854]
  are read only by the knight's TALK (164 e1 t3 ip326), never driven. 55's party/UInt16[19] reads lie past the cut.
- **Fork side**: the same O4 chain: 31256 -> 31257 -> 31258 -> real 55. `side_ends` {S: [55], F: [55]} with `members` =
  O4's 20 ONLY (never O1's 31205). The seam, the knight, the movie: the plans below.

## The member set (fork side) -- nothing new, nothing rebuilt
O4's alxc disc-1 chain as deployed in FF9CustomMap (`o4_forks.json`; O5 and O6 reuse it). Re-read today, live, in ALL 7
languages (`reconcile/members.py`): every route member differs from its US donor ONLY in Field() operand bytes (0
differing bytes outside operands), and every language carries the same retargets:
- 31246 (154): e8 t2 ip363 158 -> 31250 (THE ground door); ip203 153 -> 31245; e9 t2 ip203 -> 31248, ip363 -> 31247;
  e10 t2 ip203 -> 31248, ip363 -> 31259; e2 t1 ip1528 -> 31245.
- 31250 (158): e2 t2 ip230 -> 31251; e1 t2 ip229 -> 31246. 31251 (159): e11 t2 ip201 -> 31252; e10 -> 31250; e12 -> 31253.
- 31252 (160): e5 t2 ip235 -> 31254; e4 -> 31251. 31254 (162): e3 t2 ip235 -> 31255; e2 -> 31252.
- 31255 (163): e2 t2 ip235 -> 31256 (THE O7 EXIT); e3 -> 31254.
- (O8) 31256 (164): e2 t2 ip251 -> 31257; e3 -> 31255. 31257 (165): e2 t2 ip241 -> 31258; e3 t2 ip251 -> 31256.
  31258 (166): BYTE-IDENTICAL to stock 166 (US 0 differing bytes; Field(55) raw at e6 t1 ip871 in all 7 languages).
- Live ForkDonorPatch.txt (FF9CustomMap, the only one in the six FolderNames folders, 2026-10-02 09:04): lines 81-93
  `31246 154` .. `31258 166`, each donor once; line 42 `31205 55` (O1). DictionaryPatch.txt lines 158-170:
  `FieldScene 31246..31258 11 O4_... 3` (text block 3); line 119 `FieldScene 31205 11 O1_TH_ORC O1_TH_ORC 2`.
So **F stays inside the chain from 31246 to 31256** and ends in member(164); S ends in real 164: `side_ends` {S: [164],
F: [31256]}. A real 154 or 158-164 on F is V19 (rule 2, segment_drive.py:3360-3366), a finding.

## Ambient prologue and the Byte[13] chain (every visit's e0 t0)
`Bit[191]:=0` (ip22; 154 ip26), `Bit[184]:=0` (ip49; 154 ip53) -- masked; `Int16[9]:=K` (ip57; 154 ip61) with K the
field's environment sound: **-1 in 154, 159, 166, 55; 385 in 158, 160, 162, 163, 164, 165**; then Byte[13]: `==9` ->
nothing; `==2 && Int16[9]<0` -> `:=9` (ip97/101, THE ERROR PATH: window 56 "Error Env Play()" + `:=0` later); else
`Int16[9]<0` -> `:=0` (ip119/123); else `:=1` (ip130/134). `Int16[11]:=-1` (ip138/142); Byte[14] likewise -> `:=0`
(ip200/204). Every K=385 field also stores, right after its grant in the same Main_Init pass (no wait between),
`if Byte[13]<9: Byte[13]:=2` (158 ip445, 160 ip465, 162 ip932, 163 ip684, 164 ip764, 165 ip844); a door from a
K=385 field into a K=-1 field stores `Byte[13]:=3` (LIVE only at 158 e2 ip194 and 165 e2 ip205: the others set
`Map.Bit[162]:=1` first). That is why the chain never reaches the error path:

| field | K | Byte[13] row (old -> new), raw start | post-grant | door |
|---|---|---|---|---|
| 154 @315 | -1 | ip123 1 -> 0 (START: never ip101) | -- | e8 none |
| 158 @300 | 385 | ip130 0 -> 1 | ip445 1 -> 2 | e2 ip194 2 -> 3 |
| 159 @331 | -1 | ip119 3 -> 0 | -- | e11 none |
| 160 @332 | 385 | ip130 0 -> 1 | ip465 1 -> 2 | e5 ip199 dead |
| 162 @333 | 385 | ip130 2 -> 1 | ip932 1 -> 2 | e3 ip199 dead |
| 163 @341 | 385 | ip130 2 -> 1 | ip684 1 -> 2 | e2 ip199 dead |
| 164 @342 (O7's end; O8) | 385 | ip130 2 -> 1 (O8 raw: 1 -> 1) | ip764 1 -> 2 | e2 ip215 dead |
| 165 @343 (O8) | 385 | ip130 2 -> 1 | ip844 1 -> 2 | e2 ip205 2 -> 3 LIVE |
| 166 @344 (O8) | -1 | ip119 3 -> 0 | -- (no grant) | -- |
| 55 @110 (O8's end) | -1 | ip119 0 -> 0 (past the cut) | -- | -- |

Error-path sites (must not fire): ip97/101 and ip178/182 everywhere; window 56 + its `:=0`: 154 ip487/497, ip521/531;
158 ip288/322; 159 ip574/608; 160 ip308/342; 162 ip775/809; 163 ip527/561; 164 ip607/641; 165 ip687/721; 166 ip332/366.
The incoming values at the start come from field 70's prologue (70 e0 t0 ip57 `Int16[9]:=643`, ip130 `Byte[13]:=1`,
ip138, ip200, ip249 `Byte[8]:=125`); a warp after 70 ip475 (`Byte[13]:=2`) sends 154 to ip101 and window 56.

## 154 A. Castle/Hallway (EVT_ALEX1_AC_ENT_2F; FBG ac_fti; block 3) -- visit 1, entrance 315 (S 154, F 31246)
- Main_Init e0 t0: the prologue (ip26 = THE START ROW); ip223 `SetControlDirection(246,0)`; ip234 `SWITCH(304, L392,
  L232)` -> 315 -> **default L392**: ip402 `Map.Byte[24]:=0`, InitObject 15 (Steiner), 5 (Dojebon), 6, 7 (soldiers),
  InitRegion 9, 10, 8 (ip422-428), InitCode 11 (camera code). **No Byte[8] store at 315** (ip279 is in the 304 branch,
  L232-L389). ip465/468 `op_22(2)` x2; ip471 the window-56 test (dead); ip539 `Map.Bit[159]:=1`; ip547 `Map.Bit[158]==1`
  (set by e15 t0 ip2070) -> ip566 `Map.Bit[159]==1`, ip577 `Map.Bit[156]==0` -> **ip588 EnableMove = THE GRANT**; nothing
  stores after it (ip603 EnableMenu, ip633 FadeFilter, RET).
- Steiner = e15: ip14 `SWITCHEX(L2028, 331,L28, 310,L204, 311,L380, 312,L556, 313,L1292)` -> 315 -> **default L2028**:
  Map.Int16 x -58 (65478), z -3758 (61778), facing 128, y 63795 (= -1741); ip2070 `Map.Bit[158]:=1`; its own EnableMove
  ip2100 is skipped (Map.Bit[159] still 0: EBin.cs:115-117); ip2116 `Map.Byte[30]:=2`, SetFieldCamera(0), ip2127
  `SetControlDirection(250,0)`; ip2774 SetModel(5489,104) GEO_MAIN_F0_STN; ip2779 CreateObject; **ip2812
  SetObjectLogicalSize(30,35,50)** (radius 120, collRad 35: DoEventCode.cs:1528-1534); ip2827 MoveInstantXZY(x, -1741,
  z) -> GetTriIdxAtPos's nearest-height tri (FieldMapActorController.cs:1279-1306) = **balcony tri 250, PSX -1716**
  (ground tri 132 at -5 lies under it, re-measured); ip3003 DefinePlayerCharacter. Keys: every SetControlDirection in
  154 is (x, 0): one basis (twist.y 1.4 deg; FieldState.cs:11-17).
- **e8** (exit) (2222,-5555)(-2222,-5555)(-2222,-4080)(2222,-4080) spans BOTH levels. t2: SYSVAR[2]; **ip38 `f[1] <
  -100`** -> the BALCONY branch: ip51 ExitField, ip195 `Int16[2]:=301`, ip203 `Field(153)` (F 31245) -- the wrong door;
  else the GROUND branch: ip211 ExitField ... ip305 `op_22(25)`, **ip355 `Int16[2]:=300`** (L325), **ip363
  `Field(158)`** (F 31250). No Byte[13] store, no facing gate (scan_gateways face_gate None). 322 u south of the spawn.
- **e9** (-3777,-999)(-3777,-3111)(-1888,-3111)(-1888,-999): balcony -> ip195 `:=302` `Field(156)`; ground -> ip355
  `:=300` `Field(155)`. **e10** (3777,-999)(3777,-3111)(1888,-3111)(1888,-999): balcony -> `:=303` `Field(156)`; ground
  -> `:=300` `Field(167)`. 1941 / 2051 u from the spawn.
- **The only way down** (the engine's own triangle links, O6 dispute 5, `wm154.out` re-run identical by the bytes
  reader): the balcony meets the stairs only at tris (289,292) west and (189,190) east; the stairs meet the ground only
  at x -477..482, z -245..-125 (the central flight).
- Dojebon e5 (GEO 5488) at (-2700,-1700) PSX -1716, patrol index 3, waits at ip263 (and index 14 at ip486) while
  `B_DISTANCEA(player) < 3600 || Map.Byte[30]==1` (XZ distance, EBin.cs:1177-1189). The camera code e11 t1 sets
  `Map.Byte[30]:=1` once `f[1] > -600` (ip14-33) and back to 2 only at `f[1] < -500` (ip128-147). Once released his
  patrol runs index 4.. (-1600,-1700) -> (-1600,120) -> (-1300,565) -> (-527,777) -> (0,777): head-on along the west arm
  and the stair top the walk uses, until the next wait at index 14. Talk e5 t3 ip675 `Bit[3852]:=1` (Confirm only).
- Soldiers e6 (-1683,-3795), e7 (1764,-3631) PSX -1716: talk-only (no store), no Range.
- 154's 18 store sites: route e0 t0 ip26/53/61/123/142/204, e8 t2 ip355; dead ip45 (Bit184), ip101/134, ip182/215, ip279
  (304 branch), e2 t1 ip1520 (e2 not instanced at 315); error ip497/531; forbidden e8 t2 ip195, e9 t2 ip195/ip355, e10
  t2 ip195/ip355 (wrong doors), e5 t3 ip675 (talk). No Battle/SetRandomBattles/Cinematic/ATE/naming; the KEYON tests are
  e2 t1's (304 only).

## 158 A. Castle/courtyard south hall (ac_fgo; S 158, F 31250) -- visit 2, entrance 300
- Main_Init: prologue (ip57 `Int16[9]` -1 -> 385, ip130 `Byte[13]` 0 -> 1); EnablePath(1,0) ip232; ip256/259 `op_22(2)`;
  ip330 `Map.Bit[159]:=1`; **grant ip379**; **ip445 `Byte[13]` 1 -> 2** (L439, same pass: ip380-424 are flag, menu,
  screen-position and FadeFilter ops, no wait).
- Steiner = e6: ip14 `SWITCH(300, L47, L12)` -> 300 -> **L12**: (0, -12787) (52749), facing 0; no MoveInstantXZY, so
  CreateObject's y 32768 picks the HIGHEST tri (DoEventCode.cs:384, EventEngine.Constructor.cs:11): tri 38, PSX -268
  (single level). ip130 (30,35,50): radius 120. ip301 DefinePlayerCharacter, ip302 `Map.Bit[158]:=1`.
- **e2** (480,-17752)(-450,-17752)(-1061,-15641)(1009,-15641), unconditional: ip50 ExitField, **ip194 `Byte[13]` 2 -> 3**
  (LIVE: no `Map.Bit[162]` write before ip172), **ip222 `Int16[2]` 300 -> 331**, ip230 `Field(159)` (F 31251).
- e1 (-612,-8797)(588,-8797)(618,-12487)(-642,-12487) 300 u north: ip193 `Byte[13]:=3`, ip221 `:=331`, `Field(154)`.

## 159 A. Castle/guardhouse court (ac_gto; S 159, F 31251) -- visit 3, entrance 331
- Main_Init (no entrance dispatch): prologue (ip57 385 -> -1, **ip119 `Byte[13]` 3 -> 0**); ip219 `SetControlDirection(0,0)`;
  InitCode 1-4 (tile colour/animation: e2/e3 read SYSVAR[0] for timing only, no store); InitObject 16 (Steiner), 5
  (Haagen), 6, 7 (soldiers); InitRegion 10, 11, 12; the SYSVAR[3] sound wait; **ip290 `Byte[8]:=125`** (raw 125 -> 125,
  same); **grant ip665**; no store after it.
- Steiner = e16: ip14 `SWITCH(333, L84, L49, L14)` -> 331 -> **default L84**: (7, 3870), facing 0 -> tri 220 PSX -512.
- **THE FORCED MONOLOGUE**, e16 t1 (his own loop, every tick): **ip390 `Bit[3796]==0 && (self.x < -1600 || self.x > 1600
  || self.z < 800)`** -> ip426 `Map.Bit[158]:=0`, **ip445 DisableMove**, ip457 DisableMenu, ip464 SetTriangleFlagMask(127);
  page **296** "[IMME]What!?" (WindowAsync ip508, WaitWindow ip534); **297** "[STNR] The play seems to be a hit!"
  (WindowSync ip537); **298** (WindowAsync ip543, WaitWindow ip558); **299** (ip561, WaitWindow ip577); **300** "[IMME]I
  must hurry!" (ip602; **ip613 `Byte[208]:=0`** (L223), one loop pass with **ip648 `Byte[208]++`** (L258), WaitWindow
  ip669); **ip672 `Bit[3796]:=1`** (L282); ip681 `Map.Bit[158]:=1`; **ip711 EnableMove** (no Walk: control comes back where
  he stood). Then ip727 `SWITCH(2, L458, L353, L458, L393)` on Map.Byte[24] (0: default, idle). 5 pages, no [TIME].
- **e11** (-3498,955)(-3498,-888)(-2208,-888)(-2569,1039), unconditional: ip49 ExitField, **ip193 `Int16[2]` 331 -> 332**,
  ip201 `Field(160)` (F 31252). It lies wholly at x <= -2208, so the monologue (x < -1600) always comes first.
- e10 (1120,6590)(-1130,6590)(-1160,4910)(1150,4910) -> 158@332 (1040 u N); e12 (3410,901)(3403,-631)(2254,-623)(2550,941)
  -> 161@332: both ip193 `:=332`, other sids (a wrong door shows in the trace).
- Haagen e5 asleep at (-10,-1558) PSX -79 (`Bit[3798]==0`: e5 t0 ip146 -> SetStandAnimation(13027), skipping the
  Map.Byte[25] switch), e5 t1 idles (Map.Byte[24] 0 -> L236 -> Map.Byte[25] 0 -> default); his talk e5 t3 ip636
  `Bit[3849]:=1` / ip698 `Map.Byte[24]:=1` starts the scene with e5 t1 ip311 `Bit[3798]:=1` (forbidden). Soldiers e6
  (-2250,2088), e7 (2250,2088): talk-only (windows 294/295), no store.

## 160 A. Castle/west tower foot (ac_ltw; S 160, F 31252) -- visit 4, entrance 332
- Main_Init: prologue (ip57 -1 -> 385, ip130 0 -> 1); ip219 `SetControlDirection(246,0)`; InitObject 9 (Steiner); ip232
  `Bit[3799]==0` -> InitObject 2 (Weimar); InitObject 3 (soldier); InitRegion 4, 5; **grant ip399**; **ip465 `Byte[13]` 1
  -> 2** (L459).
- Steiner = e9: ip14 `SWITCH(341, L39, L12)` -> 332 -> **default L39**: (1357, -4063), facing 60 -> tri 1 PSX 0.
- **e5** (-561,-127)(-111,-127)(-49,-1065)(-589,-1065): ip38 `Map.Bit[162]:=1`, ip46 `Map.Bit[163]:=1` (so ip199 is
  DEAD), ExitField ip55, **ip227 `Int16[2]` 332 -> 333**, ip235 `Field(162)` (F 31254).
- **e4** (3018,-4012)(3018,-4792)(1459,-4463)(1371,-3599) **61 u EAST of the spawn**: ip194 `Byte[13]:=3` (live), ip222
  `:=333`, `Field(159)`.
- Weimar e2 / soldier e3: talk-only; the conductor e1 t1 and e2/e9 t1 run on Map.Byte[24], set to 1 only by e2 t3 ip348
  (his talk: ip298 `Bit[3850]`, then e2 t1 ip230 `Bit[3799]`, e9 t1 ip380/415/450/485 `Byte[208]`: forbidden).

## 162 A. Castle/west tower hall (ac_lth; S 162, F 31254) -- visit 5, entrance 333
- Main_Init: prologue (ip57 385 -> 385 same, **ip130 `Byte[13]` 2 -> 1**); ip219 `SetControlDirection(244,0)`;
  InitObject 7; InitRegion 2, 3; EnablePath(1,0); **grant ip866**; **ip932 `Byte[13]` 1 -> 2** (L926). No NPCs.
- Steiner = e7: ip14 `SWITCH(342, L39, L12)` -> 333 -> **default L39**: (957, -3800), facing 128 -> tri 40 PSX 0.
- **e3** (755,3730)(1265,3730)(1265,130)(725,130): Map.Bit[162]/[163] first (ip199 dead), **ip227 `Int16[2]` 333 -> 341**,
  ip235 `Field(163)` (F 31255). **e2** (575,-5321)(1385,-5321)(1415,-3850)(-205,-3850) **50 u SOUTH** of the spawn ->
  160@341.

## 163 A. Castle/west tower stair (ac_lti; S 163, F 31255) -- visit 6, entrance 341
- Main_Init: prologue (ip57 same, **ip130 2 -> 1**); **ip219 `SetControlDirection(16,16)`** (twist.y 23.9 deg: the first
  rotated basis); InitObject 7; InitRegion 2, 3; **grant ip618**; **ip684 `Byte[13]` 1 -> 2** (L678). No NPCs.
- Steiner = e7: ip14 `SWITCH(343, L47, L12)` -> 341 -> **default L47**: (690, 2195), facing 128 -> tri 76 PSX -7.
- **e2** (721,4803)(866,5202)(1432,5013)(1300,4705), mid-stair, unconditional (no height test): Map.Bit[162]/[163] first
  (ip199 dead), **ip227 `Int16[2]` 341 -> 342** (L197), **ip235 `Field(164)`** (F 31256) -- THE O7 EXIT.
- **e3** (1210,1307)(437,1254)(377,2244)(1238,1892) **73 u** from the spawn -> 162@342.

## END: arrival in 164 at 342 (visit 7)
Cut at 164's first row, **e0 t0 ip22 `Bit[191]:=0`** (L16; S real 164, F member(164) 31256), right after 163's chain
row e2 t2 ip227. Emitted: 164 is a new site in the epoch. Everything 164 writes is post-end: its prologue (ip57 385
same, ip130 `Byte[13]` 2 -> 1 -- a CHANGE -- ip138, ip200), the grant ip698 and ip764 `Byte[13]` 1 -> 2. **So the live
end-state read races Byte[13]**: read it from the last pre-cut write (163 ip684 = 2), never live. Nothing else in 164
races (Int16[9] 385 = 385; Int16[2], Byte[8], Byte[208], Bit[3796], Bit[3811] untouched there before the knight's
trigger, which needs Steiner at `f[1] <= -8400` -- he never moves). 164@342: Steiner e7 placed at (2040,3335) ->
tri 145 PSX -4780 (radius 80 by DoEventCode.cs:1507-1508); the knight e1 placed at (249,4630) (O8's).

## SC ladder -- no rung inside O7 (nor inside O8)
| value | where | when |
|---|---|---|
| 1190 | the warp's residue in field 70 (byte 0: 0 -> 166, byte 1: 0 -> 4; Ff9mkDebugMenu.cs:2134-2135) | the start; a true run carries it from 150 e3 t1 ip1966 (O4's rung) |
| (1400) | 55 e10 t1 ip582 (L474) | past O8's end too: ip500 `SC > 1400` false (1190) -> JMP L474 -> ip582; ip568 is the debug twin behind the window-2 prompt |
| (1410) | 54 e4 t1 ip458 | beyond (O9+) |
**No store to SC's bytes in any width anywhere in 154-166** (census of the listings: zero `('global', w, 0|1)` sites,
and no `UInt16[0]` reference at all); 55's two are e10 t1 ip568/ip582. O7's LADDER: "no rung" -- SC 1190 at the start
(residue) and at the end.

## FieldEntrance chain
315 (the warp's residue: byte 2 0 -> 59, byte 3 0 -> 1) -> 300 (154 e8 t2 ip355) -> 331 (158 e2 t2 ip222) -> 332 (159
e11 t2 ip193) -> 333 (160 e5 t2 ip227) -> 341 (162 e3 t2 ip227) -> 342 (163 e2 t2 ip227). [O8: -> 343 (164 e2 t2 ip243)
-> 344 (165 e2 t2 ip233) -> 110 (166 e6 t1 ip863); 55's Main_Init then rewrites 110 -> 106 (ip255, past the cut).]

## Expected story keys, in order (O7; S side; F identical in donor terms; raw start)
| visit | field | sid tag | ip (L) | key (old -> new) |
|---|---|---|---|---|
| 0 | 70 | residue | | SC byte 0 (0->166), byte 1 (0->4); FieldEntrance byte 2 (0->59), byte 3 (0->1): exactly **4** rows, set aside by the front cut |
| 1 | 154 | e0 t0 | 26 (16), 53 (43) | Bit191:=0 (THE START ROW), Bit184:=0 -- masked, same |
| 1 | 154 | e0 t0 | 61 (51), 123 (113) | Int16[9] 643 -> -1; Byte13 1 -> 0 (both start-scoped olds; START requires ip123) |
| 1 | 154 | e0 t0 | 142 (132), 204 (194) | Int16[11] -1 (same), Byte14 0 (same) |
| 1 | 154 | e8 t2 | 355 (325) | Int16[2] 315 -> 300 (chain) |
| 2 | 158 | e0 t0 | 22, 49 / 57 (51), 130 (124), 138, 200 | masked / Int16[9] -1 -> 385, Byte13 0 -> 1, same, same |
| 2 | 158 | e0 t0 | 445 (439) | Byte13 1 -> 2 (the grant's pass) |
| 2 | 158 | e2 t2 | 194 (164), 222 (192) | Byte13 2 -> 3; Int16[2] 300 -> 331 (chain) |
| 3 | 159 | e0 t0 | 22, 49 / 57, 119 (113), 138, 200 | masked / Int16[9] 385 -> -1, Byte13 3 -> 0, same, same |
| 3 | 159 | e0 t0 | 290 (284) | Byte8 125 (same) |
| 3 | 159 | e16 t1 | 613 (223), 648 (258), 672 (282) | Byte208 0 -> 0 (same; start-scoped old), 0 -> 1; Bit3796 0 -> 1 |
| 3 | 159 | e11 t2 | 193 (163) | Int16[2] 331 -> 332 (chain) |
| 4 | 160 | e0 t0 | 22, 49 / 57, 130, 138, 200 / 465 (459) | masked / -1 -> 385, 0 -> 1, same, same / Byte13 1 -> 2 |
| 4 | 160 | e5 t2 | 227 (197) | Int16[2] 332 -> 333 (chain) |
| 5 | 162 | e0 t0 | 22, 49 / 57, 130, 138, 200 / 932 (926) | masked / 385 (same), 2 -> 1, same, same / Byte13 1 -> 2 |
| 5 | 162 | e3 t2 | 227 (197) | Int16[2] 333 -> 341 (chain) |
| 6 | 163 | e0 t0 | 22, 49 / 57, 130, 138, 200 / 684 (678) | masked / 385 (same), 2 -> 1, same, same / Byte13 1 -> 2 |
| 6 | 163 | e2 t2 | 227 (197) | Int16[2] 341 -> 342 (chain) |
| 7 | 164 | e0 t0 | 22 (16) | the cut (Bit191, same, emitted: a new site) |
**51 store rows a run before the cut (12 masked + 33 writes + the 6-key chain), every one at its own site** (16 of the
33 same-value, each the first at its site in the epoch, so emitted): no site is written twice, the s88 sink
suppresses nothing and no end-of-epoch `c` row arises (the site key includes the field). Row ORDER is fixed by the
bytes: each field's prologue, its post-grant store in the grant's pass, then (159) the monologue's three rows, then the
door's rows. THE PAIRED-WALK LAW holds in every field: nothing stores between a grant and the loss that a walk could
move (158/160/162/163's post-grant rows precede any press; 159's monologue rows take control first and their values do
not depend on where it fires; the monologue always precedes e11).
Forbidden (diagnostic): every wrong-door, talk, dead and error site listed per field above.
Not gEventGlobal: Steiner's name (the [STNR] pages), party membership, Map vars, the camera.

**End state at the arrival in 164@342 (raw start)**: SC 1190; Int16[2] 342; Byte[8] 125; Int16[9] 385; Int16[11] -1;
Byte[14] 0; Bit[191] 0; Bit[184] 0; Byte[208] 1; Bit[3796] 1; **Byte[13] 2 from the trace (live: raced)**. Untouched
(New Game 0): Bit[3811], Bit[3798], Bit[3799], Bit[3849], Bit[3850], Bit[3851], Bit[3852], Bit[3792], Bit[7211],
Int16[224], Bit[3855], Bit[3854], Bit[3795]. Carried, not O7's (the raw start's, never written or read on O7): Byte[6]
0, UInt16[19] 0, UInt16[21] 0, Byte[303] 0, Byte[18] 0 -- a true O1-O6 run holds 11, 1807, 8, 1, 1.

## Choices, naming, battles, minigames, FMV
- **Choices**: none on O7 (no `[CHOO]`/PCHC window on the route). Keep O1's `{None, "want to skip", "default"}` guard rule
  (O8 needs it: a stray Confirm during FMV004 opens the skip dialog; "default" is No).
- **Naming**: none (no `Menu(1,x)` anywhere in 154-166; the "Menu()" ops are Enable/DisableMenu). The [STNR] pages
  297-299 render New Game's default name for character 3 on the raw start (expected "Steiner"; text only, the same on
  both sides by construction; unverified in game).
- **Battles**: none (opcode census of 154, 158-166 and 55: no Battle 0x2A, no SetRandomBattles, no ATE). Registry
  empty; any battle is V10.
- **Minigames**: none. 154's KEYON tests are e2 t1's (the 304 branch, e2 not instanced at 315). 159 e2/e3 read
  SYSVAR[0] for tile-animation timing only.
- **FMV**: none in O7. FMV004 is O8's (166 e6 t1 ip633/ip711).

## Nondeterminism (O7)
1. START: no start-dependent VALUE or PATH up to the arrival in 164 (every route read resolves the same branch from
   the raw warp and from a true O1-O6 run: Int16[2] 315; Byte[13] normalized by 154's prologue; Int16[9] written before
   read; Byte[8] written before read (159 ip290); Byte[208] written before read (159 ip613); Bit[3796]/[3798]/[3799]
   0 on both). Start-scoped OLDS only: 154 ip61 `Int16[9]` (raw 643 -> -1 | true -1 -> -1 same), 154 ip123 `Byte[13]`
   (raw 1 -> 0 | true 0 -> 0 same), 159 ip613 `Byte[208]` (raw 0 -> 0 same | true 1 -> 0). EMITTED PATTERN: from this
   start every site is first in the epoch; in a single-epoch true chain O5 already wrote 154's prologue sites, so they
   would be suppressed `c` counts there (lesson 14). Freeze every pattern from THIS start.
2. Timing only: the monologue's firing point (the first tick he leaves |x| <= 1600 && z >= 800: ~(-1601,1572) on the
   planned line); 159's animations and pages; fades; the camera switch in 154 (e11); the slides at 160's corner and
   163's stair foot.
3. Positions: every grant is the bytes' spawn (lesson 6: O2 wrong twice, O5/O6 exact) -- rehearse each.
4. No SYSVAR[0]-gated store, no battle, no choice, no revisit.

## The walks (O7)
Six control grants and one re-grant. Steiner throughout: GEO_MAIN_F0_STN, radius 120 (SetObjectLogicalSize(30,35,50) x4:
DoEventCode.cs:1528-1534; the only special case on the whole route is 164's, O8), collRad 35, runs 60 u a tick (two
MovePC calls at speed 30, FieldMapActorController.cs:198-209) x |n.up| (PSXMovementMethod 1, Memoria.ini:125). One key
basis per field (twist.y = (arg2+1)/256*360; FieldState.cs:11-17; UseAbsoluteOrientation 3): 154/158/159/160/162 1.4 deg,
163 23.9 deg. The basis is calibrated on a field id's first walk of the session and cached (S and F calibrate apart:
154 vs 31246, ...). steps_default = O6's (attempts 2, exit_slack 40, exit_wait_s 5, interrupts 1, npcs true, timeout_s
20, tolerance 45). No route door on O7 is facing-gated (scan_gateways face_gate None: every gateway 154-165).

### CONTROL 1 -- 154 (S) / 31246 (F), entrance 315, SC 1190, visit 1, cell (154, 1190): two steps
- **Grant**: Main_Init e0 t0 ip588 (above). **Spawn (bytes; REHEARSE)**: (-58,-3758) facing 128, balcony tri 250, PSX
  -1716 -> published y ~1716. Calibration hazards: e8's balcony part 322 u south (the 31-fps run probe is refused, a walk
  probe used), e9 1941, e10 2051; and Dojebon's 3600 circle (below).
- **Step 0 -- NEW kind `walk`** ("the balcony, the west flight, to the ground"): goal **(0,-600)** (ground tri 12 only:
  single level, so arrival within tolerance 45 with control held proves the ground), avoid [154.e8, 154.e9, 154.e10],
  **closed_tris = 119** (the 73 ground tris whose XZ overlaps a non-ground tri + the 46 non-ground tris with centroid
  x > 450, z > -3250 -- a net that forbids the east flight on any replan; recomputed here from its definition: equal to
  the walks reader's list, `reconcile/closures154.json`), npcs true. Planned (re-planned identically): (-58,-3758) ->
  (-1530,-3182) -> (-1594,-2926) -> (-1594,-46) -> (-1274,530) -> (-570,786) -> (-250,530) -> (0,-600), **7700 u, PSX -1716
  -> -5**, min wall 81 at (-1550,-3103) at the planner's 80 (7803 u / min wall 119 at 120), 140 running ticks (4.7 s).
  Done = route_to's `reached` with control held in this field; a loss in an exit -> the landing judge (V11 on a landing).
- **Step 1 -- `cross`** ("the south door, ground branch"): goal (0,-4500), target 154.e8, to 158, avoid [154.e9,
  154.e10], **closed_tris = 134** (every non-ground tri, centroid PSX <= -150), npcs true: straight south, 3900 u, enters
  e8 at (0,-4080) on ground tri 132 (balcony tri 286 above it is closed) after 3480 u (58 ticks); min wall 870. The
  ground branch fires on entry -> ip355 -> `Field(158)`/31250: the landing proves the branch (a balcony loss would land
  in 153/31245: V11 by `crossed()`).
- **Hazards**: (1) e8's balcony branch (step 0 keeps 322 u away on the balcony; step 1 is on the ground). (2) DOJEBON:
  frozen on this route (max XZ distance 3349 at the spawn; from PSX y > -600, first near (-770,713) on the flight,
  `Map.Byte[30]==1` holds him on the ground). The calibration's east probe is the one way to release him: on z -3758 the
  3600 circle ends at x 254, 312 u east of the spawn; a 4-frame run probe at 31 fps reaches ~x 233 with its tail -- ~20 u
  spare, and a frame hitch can add ticks (tickrate.py: up to ~10 caught up). Released, he patrols head-on up the west
  arm and over the stair top -- a body on the route. Smallest fix (zero code): register a non-exit hazard region east of
  the spawn on the balcony, e.g. `154.dojebon` = (150,-4080)(2222,-4080)(2222,-2950)(150,-2950), and put it in step 0's
  `avoid` (calibration then refuses or shortens the east probe; the route never goes east). Rehearse: his published
  position must not change during R-WALK154 at either render rate. (3) Soldiers e6/e7 on the balcony, 626 / 1826 u from
  the line, talk-only. (4) e11's camera switch at PSX > -600: visual, same basis.
- **THE PAIRED-WALK LAW**: nothing stores in 154 between ip588 and the e8 loss (e11 writes Map vars only).
- **Rehearse**: the grant; the probes (Dojebon static); step 0's arrival (published y ~5); step 1's loss at z ~-4080,
  published y ~5; the landing 158/31250; ticks.

### CONTROL 2 -- 158 / 31250, entrance 300, cell (158, 1190)
- Grant ip379 (+ ip445 in the same pass). Spawn (bytes; REHEARSE): (0,-12787) facing 0, tri 38, PSX -268.
- **Step 0 -- `cross`**: goal (-17,-16444) (region_goal), target 158.e2, to 159, avoid [158.e1], npcs true. Straight,
  3657 u, enters e2 at (-13,-15642) PSX -232 after 2855 u (48 ticks); min wall 603; plans at 80 and 120.
- Hazards: e1 300 u north (unconditional, its live ip193 Byte[13]:=3): in avoid; the 31-fps 'up' run probe refused.
  No NPCs.

### CONTROL 3 -- 159 / 31251, entrance 331, cell (159, 1190): one step, interrupted once
- Grant ip665. Spawn (bytes; REHEARSE): (7,3870) facing 0, tri 220, PSX -512 -- INSIDE the monologue box.
- **Step 0 -- `cross`**: goal (-2910,-300), target 159.e11, to 160, avoid [159.e10, 159.e12], **interrupts 1**, npcs
  true. Straight, 5089 u; min wall 141; plans at 80 and 120. The monologue fires at ~(-1601,1572) after 2805 u (47
  ticks): control goes inside no exit -> `crossed()` "interrupted" (segment_drive.py:2627-2631) -> rule 7 turns pages
  296-300 (lesson 11: WindowSync 297's first Confirm may drop) -> **RE-GRANT e16 t1 ip711 in place** -> rule 8 re-runs
  the same step (basis cached): (-1601,1572) -> (-2910,-300), 2284 u, enters e11 at (-2445,365) after 1473 u (25 ticks).
  A second interruption is V7.
- Hazards: e10 1040 u north, e12 3879 u; soldiers e6 (-2250,2088) 828 u, e7 2859 u (talk_r 410: no Confirm with control
  held); Haagen asleep 3097 u away at another level (|dy| 433 > 400: never paired). Calibration probes (<= ~300 u) stay
  inside the box (x within +-300, z >= 3570): no early monologue.
- Stores inside the step (ip613, ip648, ip672) are the game's, after the loss, values independent of where it fires.
- Rehearse: the loss sample (expect x just under -1600), the five pages, the re-grant position (= the loss), the
  second loss at x <= -2208, published y ~512.

### CONTROL 4 -- 160 / 31252, entrance 332, cell (160, 1190)
- Grant ip399 (+ ip465). Spawn (bytes; REHEARSE): (1357,-4063) facing 60, tri 1, PSX 0 -- **61 u west of e4**.
- **Step 0 -- `cross`**: goal (-313,-813), target 160.e5, to 162, avoid [160.e4], npcs true: (141,-3423) -> (-51,-3167)
  -> (-313,-813), 4063 u at 80 (4113 at 120), PSX 0 -> -256 up the stairs; enters e5 at (-285,-1062) after 3812 u (66
  ticks). At 80 the plan hugs a corner (wall 85 at (-27,-3199)): radius 120 slides him round it.
- Hazards: e4 (live ip194 `Byte[13]:=3`, -> 159@333): the calibration's 'right' probe is refused (inside the pad), 'up'
  run probe refused at 31 fps; one-sided axes must agree with the prior. Weimar (-921,-1406) 670 u and the soldier 888 u:
  talk-only.

### CONTROL 5 -- 162 / 31254, entrance 333, cell (162, 1190)
- Grant ip866 (+ ip932). Spawn (bytes; REHEARSE): (957,-3800) facing 128, tri 40, PSX 0 -- **50 u north of e2**.
- **Step 0 -- `cross`**: goal (1001,406), target 162.e3, to 163, avoid [162.e2], npcs true: straight north, 4206 u,
  enters e3 at (998,136) after 3936 u (66 ticks); min wall 213; plans at 80 and 120. No NPCs. 'down' probe refused.

### CONTROL 6 -- 163 / 31255, entrance 341, cell (163, 1190)
- Grant ip618 (+ ip684). Spawn (bytes; REHEARSE): (690,2195) facing 128, tri 76, PSX -7 -- 73 u from e3. Basis 23.9 deg.
- **Step 0 -- `cross`**: goal (997,4957), target 163.e2, to 164, avoid [163.e3], npcs true: (2098,3731) -> (2098,4115)
  -> (1586,4691) -> (997,4957), 3885 u, PSX -7 -> -1072; enters e2 at (1338,4803) PSX -783 after 3511 u (62 ticks).
  **No route at clearance 120** (re-planned): the flat stair foot x 2008-2244, z ~3850-4000 is 236-256 u wide; at the
  planner's 80 the plan hugs it (wall 88 at (2098,3893)). The real game passes (the engine's push-out averages the
  opposing wall forces, FieldMapActorController.cs:1060-1140, ServiceForces 1161+): expect slides; a stall would bring
  unstick's wait/push/phantom blocker (OBSTACLE_R_W 192) into a 236-u corridor -- REHEARSE (R-STAIR, both render rates);
  the opt-in fix if it stalls: a step key `unstick: false` (FakeGame-tested). No NPCs. 'down' probe refused.
- Its done step lands in 164/31256: rule 1 ends the run.

### No other control up to the end
164@342 is the end (rule 1 fires on its first poll, before the grant ip698). A control sample anywhere off the table is
V4 (game).

### O8's walks (settled here, from the bytes and re-planned; O8's design takes them)
- **164 / 31256 @342** (cell (164, 1190), two steps + a hold). Steiner e7: radius **80** (DoEventCode.cs:1507-1508,
  `effMapNo == 164 && sid == 7 && size == 30` -> 20; effMapNo = EffectiveFieldId, so 31256 gets it through
  ForkDonorPatch line 91). Grant Main_Init ip698 (+ ip764). Spawn (bytes): e7 t0 `SWITCH(344, L47, L12)` -> 342 ->
  default L47: (2040,3335) facing -36, MoveInstantXZY y -5647 -> tri 145, PSX -4780 (tri 110 at -9776 above); wall 68
  (< 80: pushed out on the first move). Basis 57.7 deg. e3 (5-gon) 157 u away is LIVE here (`f[1] > -6000`).
  - Step 0 -- `walk` + `at_y` [8800, 9150] + `hold` {flag 3811, value 1, timeout_s 15}: goal **P1 (1342,2252)** (wall 118 in
    both legs' views; three levels stacked at that XZ: -3961 / -8958 / -13893), avoid [164.e3] (NOT e2: crossed at the
    non-firing middle level), closed = the 93 open tris outside PSX [-9500,-4700], **npcs false** (the knight one turn
    above would be kept as a disc by the level filter, session.py:4956-5008). Re-planned: 24 waypoints, 6404 u at 80; NO
    route at 84 or 120. It enters e2's ring twice at PSX -8008/-8431 (non-firing) and passes PSX -8400 (the knight's
    trigger) at (609,2160), 16 ticks before P1.
  - Step 1 -- `trigger`, goal (59,2214) (tri 12, PSX -13040, in e2's west ear: the 5-gon's centre is DEAD), **until
    {y_gt: 12000}** (new y axis), **to 165**, **clearance 64** (new key), avoid [] (NOT e3: crossed at PSX -9329/-9529,
    where `f[1] > -6000` cannot hold), closed = the 99 open tris outside PSX [-13100,-8700], npcs true (the seated
    knight 300 u off, his walk line 182 u). Re-planned from P1: 22 waypoints, 6327 u at 64, a route at 60/64, NONE at
    66/67/68/72/80; fires entering e2 at (27,2266) PSX -13010 after 6266 u (126 ticks). The narrow turn (x 1054-1211,
    z ~4450-4640, PSX ~-10.7k) is a 140-144 u band, not banked: radius 80 x 2 > 144, the engine squeezes him (REHEARSE).
- **165 / 31257 @343** (cell (165, 1190), two steps). Radius 120. Grant ip778 (+ ip844). Spawn: `SWITCH(345, L47, L12)`
  -> default L47 (2055,3411) facing 128, MoveInstantXZY y -10519 -> tri 57 PSX -10280 (tri 47 at -15133 above); wall 155;
  e3 (5-gon, `f[1] > -11000`) LIVE 134 u away. Basis 35.2 deg.
  - Step 0 -- `walk` + `at_y` [11100, 11450]: goal P1 (1508,4698) (wall 186), avoid [165.e3], closed = 64 tris outside
    [-11800,-9500]; 1423 u at 80 (1452 at 120). One leg is impossible (closing what stacks on the strip walls the
    spawn to 43 u).
  - Step 1 -- `trigger`, goal (2489,3166), until {y_gt: 15000}, to 166, avoid [] (e3 crossed at the top where it cannot
    fire), closed = 16 tris outside [-16000,-11000]; 6672 u at 80 (6832 at 120); fires entering e2 at (2430,3151) PSX
    -15169. e2's ring holds ONLY top-landing tris (all 12 at -15169, re-measured), so a `cross` with target 165.e2 is an
    equally sound fallback.
- **166 / 31258 @344**: NO control (Main_Init's EnableMove ip423 needs `Map.Bit[158]`, never set at 344; e6 is the
  defined player, never granted). No step; a control sample there is V4.

## The start (O7)
**Recommended: (b) the raw warp, O2-O6's mechanism.** New Game, `storytrace 1`, then in field 70 (UIState FieldHUD, after
70 e0 t0 ip130 `Byte[13]:=1`, before ip475 `Byte[13]:=2`) `warp 154 315 1190` (S) / `warp 31246 315 1190` (F):
HarnessAgent -> Ff9mkDebugMenu.HarnessWarp -> FieldEntrance and ScenarioCounter set before SetNextMap (:2120-2135),
refused outside FieldHUD (:2083). O6's F-SMOKE loaded 31246@315.
- **Residue: FOUR rows** `[[0,0,166],[1,0,4],[2,0,59],[3,0,1]]` (315 = 0x013B; O5's count was four too, O6's three).
- Front cut at 154's first `w` row, e0 t0 ip26 (cut_at_start, segment_trace.py:149-165). **START requires ip123**
  (Byte13 old 1 -> 0), never ip101 / window 56 (154 e0 t0 ip487 WindowAsync(6,0,56), "Error Env Play()": a stop page,
  V5 by the driver in the start place).
- **START-DEPENDENT keys up to the end: NONE** (no value, no path). Start-scoped olds: 154 ip61, 154 ip123, 159 ip613
  (above). Declare them in the start's scope as O6 declared "151 takes its ambient branch from the warp's Byte[13] 1".
- **Why the handoff's "not clean" does not bite O7**: the keys a raw warp lacks (the party [Steiner], Bit[3855]/[3854],
  UInt16[21] 8, UInt16[19]/Byte[6] bit 3, Byte[208] 1, Byte[303] 1, Byte[18] 1) are read only at 164 e1 t3 ip326 (the
  knight's TALK: never driven, forbidden) and 55 e8 t1 ip633/ip666/ip1354 (past O8's end too). Byte[208]'s old value
  differs at 159 ip613 only (written before it is read); Byte[8] 125 on both.
- (a) a true O1-O6 chain: not a harness start. (c) an O6 prefix (warp 151/31244 110 + O6's beats): ~94 s more a run,
  O6's VOID risks, and it still leaves UInt16[19] 8 (55's wrong branch) -- buys only true olds; rejected. (d) raw warp +
  pokes (`byte 19 15`, `byte 20 7`, `byte 21 8`, `byte 303 1`, `byte 18 1`, `byte 208 1`, traced `harness` rows into
  `pre`): needed only by a segment that runs 55 e8 t1 past ip1354 (O9); the party cannot be poked (no verb), harmlessly.
- Carry O6's preflight set: P-MANIFEST, P-DEPLOY, P-EB (the O4 build; nothing rebuilt), P-FLOOR (31246, 31250-31252,
  31254-31256: the walks reader's read-only check found each byte-identical to its donor), P-STOCK, P-TEXT (block 3),
  P-RECOVERY, P-DONOR (154, 158-164), P-SETTINGS, P-PAD, P-OVERRIDE (the New-Game override decides the warp window),
  P-ENGINE (ba976242); in game P-CAP, P-OBJECTS (F-SMOKE warps 31246@315, 31250@300, 31251@331, 31252@332, 31254@333,
  31255@341, 31256@342), P-LANG, P-DONOR-LOG, P-LAUNCH.
- **Party and names**: Steiner is the controlled character in every walked field whatever the party (each field's own
  player entry: SetModel(5489) + DefinePlayerCharacter, 154 e15 ip3003, 158 e6 ip301, 159 e16 ip338, 160 e9 ip285, 162
  e7 ip285, 163 e7 ip293); no PARTYCHK or party op in 154-166. Raw New Game party [Zidane], names the defaults.

## The knight plan (O8; 164 is not in O7)
164 e1 (Breireicht, GEO 5488): t0 ip46/ip147 read `Bit[3811]` (0 on every start: placed at (249,4630), CreateObject ->
the highest tri, 130 PSX -11255; seated variant (-585,3879) only if set). t1: **ip160 `Bit[3811]==0`**, **ip178 waits while
the player's `f[1] > -8400`**, then ip190 SetWalkSpeed(15), Walks ip194 (-31,4436), ip201 (-246,4288), ip208 (-409,4128),
ip215 (-586,3884) = 1131 u at 15 u a tick (MoveToward, NOT slope-scaled: EventEngine.MoveToward.cs:141-142 commented
out; a colliding step is undone) ~75-80 ticks; ip221 SetStandAnimation(9924), ip225 RunAnimation(9920) + WaitAnimation
(59 frames at aspeed 16 = one a tick); **ip230 `Bit[3811]:=1`** at ~T0+140 ticks (~4.7 s), T0 = Steiner passing PSX
-8400. e2 t2 fires only at `f[1] < -12000` and Field(165) unloads 164's objects: if Steiner got there first, ip230 would
never run -- a MISSING row, not a reordered one. Without a hold the margin is ~30 ticks on one continuous walk and ~88
with two steps and their settles (dispute 7): timing, never construction.
**The plan**: step 0 ends at P1 (PSX -8958 -- past the trigger, 2300 u below the knight's line: no contact) and HOLDS
there with control held, pressing nothing, until the watched `Bit[3811]` reads 1 (`g.watch(3811)`: a published read,
no store and no trace row -- HarnessAgent.cs:840-858 only adds the bit to `_watch`; read_end_state unwatches all,
segment_drive.py:979-984); timeout 15 s -> VOID by the game (V8 class: a hold begun at a proven point past the
trigger); a field change -> V11. Then step 1. **ORDER check**: in every run's 164 visit, the row 164/31256 e1 t1 ip230
precedes e2 t2 ip243. Zero-code fallback: step 1 `settle` >= 6 s (a time hold, ordered in practice by ~6 s, not by
construction). The knight's TALK (e1 t3: Bit[3851] ip308, the knights' count ip326, Bit[3792] ip420, Bit[7211] ip627,
Int16[224] ip690, RunScriptSync -> e7 t11 Byte[208] ip399/ip434) is Confirm-only and forbidden; step 1 passes his seat
at 300 u (talk_r 395: an icon may show; nothing is pressed with control held, and no page is up in 164).

## The movie plan (O8; FMV004 is not in O7)
166 e6 t1: ip601 `Map.Bit[146]:=0`; ip609 `SYSVAR[15]&128 == 0` -> ip624 RunSoundCode1, **ip633 `Cinematic(0,9,1,1)`**
(raw `28 00 00 09 01 01`: the engine reads getv1/getv2/getv1, DoEventCode.cs:935, = (0, 0x0109, 1) -> fldfmv.cs:56-58
disc 1, no 9 -> MBG.Seek -> **MBGDiscTable[1][9] = MBG_DEF("FMV004", 1, 0)**, MBG.cs:830; MBG_DEF(name, isRGB24, type) ->
**type 0**); ip639-664 the SYSVAR[15] wait, ip667 `Map.Bit[146]:=1`; ip678 the play condition, **ip711
`Cinematic(2,0,0,0)`** (play: fldfmv.cs:64-65); ip717-768 the wait for the movie's end; op_22(1), FadeFilter(6,2), op_22(3);
**ip863 `Int16[2]:=110`**, **ip871 `Field(55)`**. **No page after it; no gEventGlobal store between ip502 and ip863.**
Type 0 arms MovieHitArea (MBG.cs:205-208): a Confirm opens SkipMovieDialog (FieldHUD.cs:277-284; the movie pauses while
it is up, MBG.cs:536); choice 0 skips (:430-433). The live file is MoguriVideo/StreamingAssets/ma/FMV004.bytes,
**45.412 s** (ffprobe today; the base copy 44.867 s; MoguriVideo is 4th in FolderNames, so its copy plays, on both sides).
**The plan: PLAY IT OUT** (rule 9; no `pred["movies"]`): it costs ~45 s a run and needs no code. Keep the skip guard rule
(a stray Confirm's dialog is answered "default" = No: the movie resumes). The stall watchdog's signature
(segment_drive.py:3338-3345) stays static from the ip502 row through the movie to the ip863 row, ~47 s: freeze
`no_progress_s` at no less than twice R-FULL's measured static span (~100 s; O3 froze 271 for FMV003's 84.8 s; O4-O6's
60 would leave ~13 s of margin). During play the target fps is the movie's (MBG.cs:217, restored :306): plan nothing in
ticks across it. A skip needs a non-page span key (FMV004 has no "next page"), O8's own stock A/B reading EQUIVALENT, and
saves ~4.5 min a session: not recommended. Rehearse R-FMV-VOID (stopped mid-movie -> the debug warp from FieldHUD ->
the title).

## The seam plan
- **O7: no seam.** The chain is closed from 31246 to 31256. The last compared row is 163 e2 t2 ip227 `Int16[2]:=342`
  (S: real 163; F: 31255 e2 t2 ip227). Both sides are cut at the end place's first row, 164 e0 t0 ip22 (S real 164, F
  31256). `side_ends` {S: [164], F: [31256]}; `members` = O4's 20; a real 154/158-164 on F is V19. Nothing to rebuild.
- **O8: the seam into real 55, as deployed.** member(166) 31258 keeps a raw `Field(55)` at e6 t1 ip871 in all 7
  languages and a `Field()` op never redirects through ForkDonorPatch (ForkSiblingField serves only the world entry
  ff9.cs:9327 and the battle return HonoluluBattleMain.cs:736-737), so F lands in REAL 55 -- O1's (member(52) -> real 100),
  O2's (member(116) -> 61) and O3's (31213 -> 64) shape. END on arrival in real 55 at 110 on BOTH sides, cut at 55 e0
  t0 ip22 (both sides run the same real 55 script and the same block-2 text). `side_ends` {S: [55], F: [55]} with
  `members` = O4's 20 ONLY: side_ends_of accepts F 55 only as "an end field no member forks" (segment_trace.py:171-206), so
  listing O1's 31205 would be refused at load, and keeping side_ends keeps rule 2's V19 for a real 164/165/166 on F. A
  SEAM check: every F run's last chain row is 31258 e6 t1 ip863 and its next field is 55. 55's Main_Init writes at once
  (ip255 `Int16[2]` 110 -> 106, ip342 `Byte[8]` 0 -> 125 after a sound sync): read Int16[2] (110) and Byte[8] (0) from the
  last pre-cut rows, never live. **No rebuild** (the 31258 rebuild with `retarget = { 55 = 31205 }` is owner-gated, breaks
  O4-O6's P-EB pins until O4's build dir is rebuilt, would be 31205's first run ever, and adds nothing O8's claim needs).
  O9 starts with a raw warp into 55 at 110 (S) / 31205 at 110 (F) on O1's tshp chain, as O4 started at 64.

## Disputes settled (reader claims vs the bytes / engine / walkmesh / code)
1. **The end.** Bytes, data, start-state and gates readers: one segment to the arrival in 55. Walks: steps to 166, no
   end. SETTLED by weighing (not by count): a SPLIT -- O7 to the arrival in 164, O8 from a raw warp into 164 to real 55
   (section 1). The facts it rests on were re-derived: the clearance threshold (no route above 64-66 from P1), the
   calibration room (164: wall 68 < radius 80), the knight's race, the 5-gon dead centres, O8's clean start.
2. **side_ends for a real-55 end.** Bytes: {S:[55], F:[55]}. Data: no side_ends (O1's model). Harness: either, by the
   members map. SETTLED from the code: side_ends_of accepts F [55] when no listed member forks 55 (segment_trace.py
   :197-201), and rule 2's V19 runs only under side_ends (segment_drive.py:3360-3366) -- keep side_ends {S:[55],F:[55]}
   with O4's 20 members; without it a real-field landing on F would read V11 (the driver's).
3. **The play op's ip.** Data: ip678 runs Cinematic(2,0,0,0). Bytes/gates/harness: ip711. SETTLED: ip678 is the play
   CONDITION (`SYSVAR[15]&127 != 17 && SYSVAR[15]&128 == 0 && Map.Bit[146]==1`), ip708 JMP_IFNOT, ip711 Cinematic(2,0,0,0).
4. **FMV004's operands.** Bytes `Cinematic(0, 0x0109, 1)`; data/gates/listing `Cinematic(0,9,1,1)`. SETTLED: the same
   bytes; the kit prints four single bytes, the engine reads getv1/getv2/getv1 (DoEventCode.cs:935) -> disc 1, no 9.
5. **164's leg-B clearance.** Bytes "<= 64"; walks "<= 66 (67 from a finer start cell)"; harness "64". SETTLED
   (re-planned): from P1 (1342,2252) a route at 60 and 64, none at 66/67/68/72/80; from (1382,2319) at 64 and 66, none at
   67+. Freeze 64.
6. **164's hold point.** Bytes (1382,2319); walks (1342,2252). SETTLED: (1342,2252) -- wall 118 in both legs' views vs 81.
7. **The knight's margin.** Walks "~88 ticks"; harness/O6 survey "~30 ticks ahead of the fire". SETTLED: both right for
   their walk shape (one continuous walk ~30; two steps with settles ~88); neither by construction: O8 holds on the bit.
8. **Is a HEIGHT evidence required?** Walks: yes for 164; harness: a cross is sound only with the 5-point region; bytes:
   needs y. SETTLED: not for attribution -- in 164 only e2 (top, `f[1] < -12000`) and e3 (bottom, `f[1] > -6000`) take
   control and their regions are XZ-disjoint (e2 z <= 2401 < 2471 <= e3); at a non-firing level their tag 2 RETs before
   ExitField (ip42/ip51), and the landing (to 165) proves the door. But leg B's open band still holds tri 90 (PSX -8736)
   inside e2's ring, so a ZONE-finish cross is not level-proof: use `trigger` + `until {y_gt: 12000}` + `to` (the
   engine's own test, no zone); zero-new-axis fallback `until {x_lt: 600}` + `to` 165 (sound by the disjointness). 165:
   e2's ring holds only top tris -> cross or trigger both sound; the trigger shape kept for uniformity.
9. **The post-grant Byte[13] rows.** The bytes reader's beats omit them (its notes list them); data/walks list them.
   SETTLED: they are route rows (158 ip445, 160 ip465, 162 ip932, 163 ip684; O8 164 ip764, 165 ip844), and the
   prologue's Byte[13] branch is fixed by each field's `Int16[9]` constant (the chain table above); "ip97/119/130" (data)
   is exactly one site per field.
10. **166's Byte[13] sites.** Data: "ip97/119/130/332". SETTLED: on the route 166 takes ip119 (incoming 3 from 165's live
    ip205); ip97 needs an incoming 2, ip332 is window 56's error store.
11. **Spawn heights.** Data: 154 "PSX y -1741", 164 "-5647", 165 "-10519". SETTLED: those are MoveInstantXZY's
    arguments; GetTriIdxAtPos lands on the nearest-height tri: 154 tri 250 (-1716), 164 tri 145 (-4780), 165 tri 57
    (-10280) (re-measured).
12. **154's step-0 npcs.** Walks: "npcs true" in prose, false in its step JSON. SETTLED: true (the default): Dojebon
    and the soldiers stand on the balcony level the walk starts on, >= 626 u from the line; nothing stands over the
    ground part; O6's reason for false (stacked NPCs over a ground approach) does not arise.
13. **The 154 SWITCH ip.** Start-state "ip230"; bytes/data "ip234". SETTLED: ip230 pushes `Int16[2]`, ip234 is the SWITCH.
14. **154's way down.** Data: down the central flight to (-225,-4654). Walks: two steps via (0,-600). SETTLED: the walks
    reader's legs (re-planned identically; the closures recomputed from their definitions, equal).
15. **The knight's walk units.** Bytes: unverified. SETTLED from the engine: MoveToward moves `speed` a call, its slope
    factor commented out (MoveToward.cs:141-142): 1131 u at 15 = ~75 ticks + turns.
16. **Calibration room at 164.** Walks: 'up' ~35 u free, 'right' 0; harness: up 110, right 70. SETTLED: consistent --
    the walks reader subtracts the controller radius from the wall distances the harness reader gives (115-80, 80-80).

## Harness gaps (summary; evidence in the structured result)
O7 needs ONE new step kind (`walk`: goal/tolerance/reached with control held; the landing judge on a loss), strict
step_of validation of its keys, and FakeGame two-level support (a height model and a height-branch region in the
UNPINNED `_move_to`/`_region_at`/`_enter_regions`; G21 pins only the visit-beat and machine paths). Ready with
configuration: the raw-warp start (4 residue rows), Steiner as the controlled actor, the crosses (`avoid`, `closed_tris`),
the monologue (`interrupts: 1`), the arrival end (rule 1, `side_ends`, `end_row` 164 e0 t0 ip22), recovery (the debug
warp from FieldHUD). RISKS: Dojebon's release by a calibration probe (zero-code hazard region), 163's squeeze (R-STAIR),
the live end-state read racing Byte[13] (read it from the trace). O8 adds: `at_y`, `hold`, `clearance`, the y axis of
`until` (+ the loss sample's y from the ring), the FakeGame spiral height model, y-gated regions and a height-triggered
walker with a store, an opt-in `basis: "prior"` for 164/165's narrow spawns (built opt-in, enabled only if R-CAL164
deflects), 5-point region registration from scan_gateways' `region`, the movie stall freeze.

## Fork gates (summary)
Nothing on O7's route (or O8's) can change a story write between S and F: every member differs from its donor only in
`Field()` operands (7 languages, re-read); no route field has a field-id gate that stores (the 154 camera clamp is
wrapped, FieldMap.cs:638/666; NarrowMapList widths wrapped; no autosave-list id; 162/163's SPS repositions wrapped,
cosmetic; 164's radius fix wrapped -- O8; FMV004's path reads no field id but fldfmv.cs:112's EffectiveFieldId == 100).
Visual only and raw: PSXCameraAspect's RestrictedCams [154,0,352] on 154's camera 0 (S crops at the logged 1286x749
window, F does not; O5 crossed 154 with it and matched): never compare 154 camera-0 screenshots.

## Rehearsals before the freeze (proposed, O6's shape)
| stage | runs | settles |
|---|---|---|
| R-WALK154 (stock 154) | 2 | the grant, the probes (Dojebon static, at both render rates if the regime flips), step 0's arrival on the ground, step 1's loss at z ~-4080 and the landing in 158 |
| R-STAIR (stock 163) | 2 | the stair-foot squeeze at radius 120: slides only, no stall; else `unstick: false` |
| R-FULL (stock 154 -> 164) | 2 | every grant position, 159's loss and five pages and re-grant, 160/162/163's probes beside their back doors, every loss sample, the cut 164 e0 t0 ip22, the end state (Byte[13] from the trace), run times (budget) |
| R-WALK-VOID | 2 | stopped between 154's two steps; stopped mid-monologue in 159 -> the title |
| F-SMOKE | 7 warps | 31246@315, 31250@300, 31251@331, 31252@332, 31254@333, 31255@341, 31256@342 load; object sids = their stock twins' (P-OBJECTS) |
| F-PASS (untraced) | 1 | one F run 31246 -> 31256, no throw, no V-class |
O8's (for its design): R-CAL164 (both render rates), R-SPIRAL (164 legs + the hold, 165), R-KNIGHT (the write tick),
R-FMV (the static span), R-FULL, R-SPIRAL-VOID, R-FMV-VOID, F-SMOKE 31256@342/31257@343/31258@344.

## Owner decisions
1. The split (recommended): O7 = 154 -> arrival in 164; O8 = 164 -> real 55. Alternative: one segment to the arrival in
   55 (~3.75 min a run, every new mechanism at once).
2. (O8) FMV004: play it out (recommended) or skip after O8's own stock A/B (a new span key; saves ~4.5 min a session).
3. (O8) The 55 seam as deployed, real 55 on both sides (recommended), or rebuild 31258 with 55 -> 31205 (owner-gated;
   breaks O4-O6's P-EB pins until O4's build is rebuilt; 31205's first run).
No rebuild, redeploy or relaunch is needed for O7.

## Could not determine / unverified
Every grant position in game (bytes only; lesson 6); the 159 loss sample and its pages under the driver; 163's squeeze
and 160's corner slide in game; the calibration outcomes at 160/162/163 beside their back doors (by the bytes, room
remains); whether a 31-fps calibration probe ever releases Dojebon (~20 u spare); the run time (estimated); the [STNR]
name rendered on a raw start (expected "Steiner"); for O8: the narrow-turn squeeze at radius 80, the calibration at
164/165's spawns, the knight's write tick (+-5 ticks), the published movie state and FMV004's static span, the
PSXCameraAspect crop at run-time window size.
