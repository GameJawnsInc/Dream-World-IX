# Stock O5 route: raw warp into 153 (FieldEntrance 325, SC 1190) -> the stairs -> Zorn & Thorn -> the throne room -> Field(153) at 328  (reconciled)

The reconciler's own decode, independent of the six readers' outputs. Every ip below was decoded from the stock US
`.eb` by `reconcile/ebtool.py` (storytrace.stock_script_source + ScriptIndex + instruction_stores, the main repo's
ff9mapkit, master c5e5dd88) and checked against the listing; every engine claim was re-read in C:\gd\FFIX\Memoria.
- `ip` = abs - entry code start = the s88 trace ip. `Lnnn` = offset from the function start (the predictions' `off`).
- Listings `reconcile/L{151,153,154,155..167,55,150}.txt` are byte-identical (cmp) to the bytes, data, walks, harness and
  start-state readers' copies and to O4's reconcile listings: no reader decoded different bytes. Texts: block 3
  (`reconcile/mes_153.json`, the same file for 150-167), US. Window lists `reconcile/win_{151,153,154}.txt`; per-stage
  actor blocks `reconcile/stages{151,153,154}.out`.
- `SWITCH(base, default, case_base, case_base+1, ...)`; `SWITCHEX(default, value, target, ...)`.
- Engine: the live source is the deployed engine (x64/x86 Assembly-CSharp.dll sha256 ba976242.. = Output, the gates
  reader's re-check; no `.cs` newer than the build). Notes, measurements and arithmetic: `reconcile/notes.txt`.
- Constants: a 2-byte script constant is SIGNED (EBin.cs:1251-1255 pushes `getShortIP()`, an Int16): `const(65086)` = -450.

## Segment end: CHOSEN = arrival in 153 at 328 (151 e2 t1 ip940 `Field(153)`, after ip932 `Int16[2]:=328`), SC 1190
| # | exit (stock) | arrival | SC | est. min a run | end check today | inside (cumulative) |
|---|---|---|---|---|---|---|
| 1 | 153 e3 t1 ip3158 `Field(154)` (304, ip3150) | 154 @304 | 1190 | ~3 | works (first arrival in 154) | pages 113-117, THE stair walk (the first alxc control), choice 128 (stored, Bit[3795]), 2 KEYON pairs, 2 timed windows |
| 2 | 154 e2 t1 ip1528 `Field(153)` (316, ip1520) | 153 @316 | 1190 | ~3.8 | GAP (153 = the start place) | + Zorn & Thorn: 2 pages, 3 KEYON pairs, no control |
| 3 | 153 e18 t1 ip1085 `Field(151)` (110, ip1077) | 151 @110 | 1190 | ~4.7 | works (first arrival in 151) | + 12 pages, 2 KEYON pairs, no control |
| **4 CHOSEN** | **151 e2 t1 ip940 `Field(153)` (328, ip932)** | **153 @328** | **1190** | **~6.5** | GAP (153 = the start place): `end_visit` | + the throne room: 17 pages, 5 KEYON pairs, 2 timed, Steiner's NAMING (Menu(1,3) e3 t1 ip603), `Byte[6] \|= 8` (e3 t1 ip610, the first START-DEPENDENT key) |
| 5 | (no Field) Steiner's EnableMove 153 e32 t1 ip2412 | -- | 1190 | ~7.2 | a new end kind | + 11 pages, the party rebuild (UInt16[21], Byte[303], Byte[4], UInt16[19] START-DEPENDENT, Byte[17], Byte[18]) |
| 6 | 153 e23 t2 ip211 `Field(154)` (315, ip203) | 154 @315 | 1190 | ~8 | GAP (154 visited at 304) | + Steiner's first walk (ground, north door) |
| 7-13 | 154 e8 t2 ip363 -> 158 -> 159 -> 160 -> 162 -> 163 -> 164 -> 165 -> Field(166) | 166 @344 | 1190 | ~9-13 | -- | + 8 more walks, two of them spiral towers (height-gated exits), 159's forced monologue, 164's knight (Bit[3811] race) |
| 14 | 166 e6 t1 ip871 `Field(55)` (110, ip863) | 55 (tshp) | 1190 | ~14-16 | F lands in REAL 55 (member(166) 31258 keeps Field(55)) | + 166's scene and FMV004 (45.4 s) |
| 15 | 55 e10 t1 ip582 `SC:=1400` | -- | 1400 | ~15-17 | needs member(166) rebuilt (retarget 55 = 31205) | the first SC rung after 1190 |

Run times are estimates from the bytes, calibrated on O4 (R-FULL 107-126 s for 64 -> 153; 150's 13 pages + 1 KEYON pair
+ the rebuild ~65 s, so ~4 s a page). The chosen end holds 53 pages (pick 1; 44 with pick 0), 12 KEYON pairs, 4 timed
windows, 1 naming, 1 walk; the scripted `op_22` waits sum to 289 + 35 + 150 + 319 ticks (~26 s; `reconcile/waits.py`).
No stock run of 153-151 exists.

Why 4 (both route readers' recommendation, and the PLAN pointer's "then Field(151) at 110 (the throne room: Steiner's
naming, and Byte[6] |= 8 ...)"):
- **One control grant in the whole segment.** 153 at 325 is the only visit with control (e3 t1 ip785); 154@304 (Zorn
  e2), 153@316 (Zorn e18) and 151@110 (Brahne e3) are defined players with no `Map.Bit[158]`, so no EnableMove runs. The
  beat table's key `(153, 1190)` is unambiguous; 153's second (316) visit never shows control, and the third (328) is the end.
- **Every new interaction type here is already proven somewhere.** The walk is O2's trigger step with existing keys
  (`closed_tris`, `until`); the naming is O1/O2's `accept_name`; the non-default choice is O1's (52) and O4's (encore)
  `choose(1)`; the KEYON pairs and pages are O3/O4's rule 7; the START-DEPENDENT key is O2's 4.5 shape. No battle, FMV,
  ATE, hot-spot or character walk-change inside.
- **A clean member set and a clean seam.** Nothing new to build or deploy: member(153) 31245, member(154) 31246,
  member(151) 31244 are deployed and every route `Field()` is retargeted (`reconcile/forkdiff.out`); F ends in
  member(153) 31245 like O4.
- **It hands O6 a clean start.** O6 = a raw warp `warp 31245 328 1190`: Steiner's assembly, his first control at
  (-245,42) on the GROUND, then the nine-field walk. Every O6 field is visited once there, so O6's cells stay
  `(donor, SC)`-unambiguous too; the hard O6 machinery (height-aware routing, radius 120, a waypoint step) stays out of O5.
- **Cost: ONE new opt-in driver/cut feature, `end_visit`** (the run starts in 153, so today's rule 1 and `cut_at_end`
  would end it on its first poll and cut at its first row). It is pure and small (Harness gaps). The fallback with zero
  driver change is candidate 3 (first arrival in 151, ~4.7 min); O6 then absorbs the naming.

## The member set (fork side) -- nothing new
The O4 alxc disc-1 chain, deployed live (FF9CustomMap): member(151) 31244, member(153) 31245, member(154) 31246
(ForkDonorPatch rows `31244 151`, `31245 153`, `31246 154`, each donor once, FF9CustomMap only; DictionaryPatch
`FieldScene 31244/31245/31246 ... 3` = text block 3). The deployed US `.eb`s differ from their donors ONLY in `Field()`
operands (`reconcile/forkdiff.py`, instruction by instruction):
- 31245 (`EVT_O4_AC_H2F`): e3 t1 ip3158 154 -> 31246; e18 t1 ip1085 151 -> 31244; e23 t2 ip211 154 -> 31246; e24 t2
  ip191 150 -> 31243; e25 t2 ip203 64 -> 31240, ip429 151 -> 31244; e28 t2 ip235 150 -> 31243. `Field(204)` at e3 t1
  ip3296 stays raw: the flashback branch (ip2942 `Int16[2] != 3` false only when Int16[2] == 3, set at e0 t0 ip243
  behind `SC > 1900`): dead at SC 1190.
- 31246 (`EVT_O4_AC_FTI`): e2 t1 ip1528 153 -> 31245 (+ e8/e9/e10 t2, entrance 315 only).
- 31244 (`EVT_O4_ALXC_AC_RST`): e2 t1 ip940 153 -> 31245 (+ e8 t2 ip245, default entrance only).
So **F stays inside the chain end to end and ends in member(153) 31245**; S ends in real 153 (`side_ends` {S: [153],
F: [31245]}, O4's). A real 151/153/154 on F is V19. (31258 = member(166) keeps a raw `Field(55)`: O6's seam, below.)

## Ambient prologue (every visit's e0 t0; O4's shape)
`Bit[191]:=0`, `Bit[184]:=0` (masked story noise), `Int16[9]:=-1`, Byte[13] (`==9` -> nothing; `==2 && Int16[9]<0` ->
`:=9`, the error path; `Int16[9]<0` -> `:=0`), `Int16[11]:=-1`, Byte[14] likewise. `Int16[2]:=10000` sits behind
`Bit[184]==1` (never). `:=1` (ip130/ip211 shapes) is dead: Int16[9]/[11] were just made negative.
| visit | Bit191 | Bit184 | Int16[9] | Byte13:=0 | Int16[11] | Byte14:=0 | error path (must not fire) |
|---|---|---|---|---|---|---|---|
| 153 @325, @316 (and @328's ip22 = the cut) | ip22 (L16) | ip49 | ip57 (L51) | ip119 (L113) | ip138 (L132) | ip200 (L194) | ip97/ip178 (:=9), window 56 ip2304/ip2338, ip2314/ip2348 |
| 154 @304 | ip26 | ip53 | ip61 | ip123 | ip142 | ip204 | ip101/ip182, window 56 ip487/ip521, ip497/ip531 |
| 151 @110 | ip22 | ip49 | ip57 | ip119 | ip138 | ip200 | ip97/ip178, window 56 ip950/ip984, ip960/ip994 |
Incoming at 153's first prologue after the raw warp: Byte[13] 1, Int16[9] 643, Int16[11] -1, Byte[14] 0 (field 70 e0 t0
ip130/ip57/ip138/ip200), so 153 takes ip119 (old 1). A warp after 70's ip475 (`Byte[13]:=2`, FMV001's tail) would take
ip97 and stop on window 56: the START contract requires ip119, as O4's required 64's.

## 153 A. Castle/Hallway (EVT_ALEX1_AC_H2F, fbg_n02_alxc_map041a_ac_h2f_1, block 3) -- visit 1, entrance 325
- Main_Init e0 t0: ip232 `SC>1900` false (ip243 `Int16[2]:=3` skipped); ip251 `SET(Int16[2])`, ip255
  `SWITCHEX(L1098, 325,L273, 5,L438, 328,L603, 316,L799, 3,L951)`: 325 -> ip279 `Map.Byte[24]:=1`, InitObject 3 (Zidane),
  7 (Blank), 31 (the hooded girl), 9, 11 (two soldiers, hidden), **InitRegion 26, 27, 28**, InitCode 22 (camera); no BGM
  load, no Byte[8] write. Tail: ip2356 `Map.Bit[159]:=1`; its EnableMove (ip2405) needs `Map.Bit[158]==1` (ip2364): not
  at 325 -- control comes from e3 t1.
- Zidane = e3: e3 t0 ip10/14 `SWITCH(3, L134, ...)` default L134: `CreateObject(2102,75)` (ip185; inside e28's quad),
  facing 64, **DefinePlayerCharacter ip176**, SetModel(203) GEO_MAIN_F1_ZDN, SetObjectLogicalSize(20,24,40) ip218 =
  controller radius 80 (DoEventCode.cs:1498-1531: size x 4).
- Conductor e2 t1 ip23 on Map.Byte[24], advanced by Map.Bit[231] (`reconcile/stagemap.py`): 1 -> 2 -> 3 -> 4 -> 5 -> 6
  -> **17** (ip420); side scenes 7..13 -> 16 -> 6 and 14 -> 15 -> 9 -> ... -> 16 -> 6; 17 -> 18 -> 19 -> 20 ->
  `SWITCH Map.Byte[27]` (ip844): 0 -> 21, 1 -> 31; 21 -> 22 -> 23; 31 -> 32 -> ... -> 39 -> 23; 23 -> 24 -> 25 -> 26 -> 27
  -> 28 -> 30 -> 116.
- Stage 1: e3 `Walk(1105,-78)` ip537; e7 `Walk(1068,373)` ip267 and **113** "Blank / According to recon..." WindowAsync
  ip273. Stage 2: e7 `WaitWindow(1)` ip337 (113 is a PAGE), **114** WindowAsync ip340 + WaitWindow ip351. Stage 3: e3
  **115** "Got it!" ip606 + WaitWindow(0) ip622. Stage 4: e7 **116** WindowSync ip700 ("Uh-oh! The scene where Marcus
  sneaks into..."). Stage 5: e7 **117** WindowAsync ip764 ("Let's get this over with"), SetObjectFlags(5) ip770 (shown,
  NO player collision, talk on); e3 TurnTowardObject(7) ip747, **WaitWindow(1) ip752** (117 closed by Confirm),
  `Map.Bit[158]:=1` ip755, gates `Map.Bit[159]==1` ip763 and `Map.Bit[156]==0` ip774, **EnableMove ip785**,
  SetTriangleFlagMask(255) ip786, EnableMenu ip800. **The first control grant in alxc** (no window up at the grant).
- Stage 6 (e3 t1 L451) -- THE STAIR WALK: every tick (L3430 `Wait(1); JMP L0`) ip859 `obj(uid=255).f[1] > -450` (uid 255
  = gCur = e3, EventEngine.cs:946-949; f[1] = -pos[1], EBin.cs:1785-1793): true -> keep looping; false (PSX y <= -450,
  published y >= 450, only reachable on the curved west stair) -> ip874 `Map.Bit[158]:=0`, **DisableMove ip893**,
  DisableMenu ip905, SetTriangleFlagMask(127) ip912, Bit231 ip915. Live during stage 6: regions e26/e27/e28 and Blank's
  talk (e7 t3, "Hurry!" 118 at ip2195, DisableMove/EnableMove ip2159/ip2231, no store).
- Stage 17: e3 op_1C(22) ip1437 (terminates the camera code), Wait(1), waits while `Map.Bit[160]==1` (nothing in 153
  sets it), **CreateObject(-1165,856) ip1466** (a TELEPORT to the stair foot, tri 52, PSX -231), SetWalkSpeed(37), scripted
  climb ip1479-1521: (-1419,602) (-1602,298) (-1631,10) (-1631,-140) (-1416,-378) (-978,-554) (-329,-624) (the upper
  corridor). e7 walks to (-590,943); e31 (on the upper corridor, y -1499) waits 25+13 ticks and walks (0,1500), (0,0).
  The 314/318/317/321 windows here are behind `Int16[2]==3 && Bit[3795]` (flashback only).
- Stage 18: e3 **126** "(Hmm? She sure is dressed funny...)" ip1672 + WaitWindow ip1699. Stage 19: e31 **127** "Hooded
  Girl / Umm... Would you please let me pass?" WindowSync ip663, then Bit231 ip670 -> stage 20 within ~2 ticks.
- Stage 20: e3 ip1713 `Int16[2] != 3` -> **choice 128** `WindowSync(0,128,128)` ip1724; **ip1741 `Global.Bit[3795] :=
  SYSVAR[9]`**; ip1749 `Map.Byte[27] := SYSVAR[9]` (the conductor's branch). Choices below.
- Path 1 (the pick, "Examine her face"), stages 31-39: e3 **141** ip3430 + wait ip3456; e31 **142** ip1201; e3 **143**
  WindowSync ip3508, **144** ip3525 + wait ip3552; e31 **145** ip1229; e3 **146** ip3577 + wait ip3604; e31 **147** ip1257;
  e3 **148** WindowSync ip3629; e31 **149** ip1285; e3 **150** ip3674 + walk + CreateObject + wait ip3712, **130** ip3726 +
  wait ip3753 -> stage 23. (Path 0, stages 21-22: e3 walk; **129** ip1899 + wait ip1937, **130** ip1951 + wait ip1978.)
  The 315/319/316/320 windows on both paths are flashback-only (same guard).
- Stage 23: e31 **131** "No, I do not know you..." WindowSync ip943. Stage 24: e3 **132** ip2064 (+ 4 walks) + wait
  ip2129; **133** ip2146 (+ 3 walks) + wait ip2201.
- Stage 25: KEYON pair -- e3 SetDialogProgression(0) ip2284, **134** `WindowAsync(7,..)` "Say, you wouldn't-"
  `[INCS][TIME=-1]` ip2287; e7 walks then **135** `WindowAsync(1,..)` `[INCS][TIME=-1]` ip1732; e3 waits while
  `SYSVAR[8] < 2 && Byte29 > 0` (Byte29 from 250, ip2293-2327), then **KEYON ip2336** (Confirm 0x20000 or Special
  0x80000 EDGE), CloseWindow(7) ip2356, CloseWindow(1) ip2359.
- Stage 26: e31 **136** "I..." WindowSync ip1036. Stage 27: e31 **137** `[NFOC]...I must go![TIME=20]` ip1081 (self-closing)
  and her run-off walks; e3 SetObjectFlags(7), **RunVibrationTrack ip2443/ip2448, ActivateVibration ip2453** (the s62
  VIB gate on F), RunSharedScript(4), walks; e7 Wait(35).
- Stage 28: KEYON pair -- e3 Wait(15), **139** "Get up, Blank! That was Princess Garnet!" `WindowAsync(0,..)` [INCS] ip2662,
  gate ip2668-2702, **KEYON ip2711**, CloseWindow(0)/(1) ip2731/2734; e7 **138** "Who the heck was that!?" WindowAsync(1)
  [INCS] ip1951 + WaitWindow(1) ip1957.
- Stage 30: e7 **140** `[NFOC]...Are you serious!?[TIME=20]` ip2029 + walks; e3 SetPathing(0), a jump (SetupJump ip2866,
  Jump ip2875), Walk ip2933, RunSharedScript(6), ip2942 `Int16[2] != 3` -> **ip2953 `Byte[8]:=0`**, `Map.Bit[158]:=0`
  ip3007, DisableMove ip3026, PreloadField(5,154) ip3048, FadeFilter ip3090, Wait(65) ip3100, **ip3150 `Int16[2]:=304`**,
  **`Field(154)` ip3158** (F: Field(31246)).
- 153's store sites, classified (`grep '<<' L153.txt`): route v1 e0 t0 ip22/49/57/119/138/200, e3 t1 ip1741/2953/3150;
  route v3 e0 t0 the same six, e18 t1 ip890/1077; error ip97/178/2314/2348; dead ip41, ip130, ip211, ip243 (SC > 1900),
  e3 t1 ip3168/ip3288 (flashback); other entrances e0 t0 ip1188/1260 (default branch); forbidden at v1 e28 t2 ip38
  (`Byte[8]:=25`), ip227 (`Int16[2]:=5`); past the end (328 only) e23/e24/e25 t2, e32 t0 ip718/727, e32 t1 (all), and
  **e15 t0 ip32 `Byte[8]:=125`, run at 328 by e32 t1 ip866 `RunSharedScript(15)`** (see dispute 6). Shared scripts on the
  route (entries 4, 5, 6, 8, 10, 12, 19) store nothing.

## 154 A. Castle/Hallway (EVT_ALEX1_AC_FTI, map046) -- visit 2, entrance 304: Zorn & Thorn
- Main_Init e0 t0: ip230 `SET(Int16[2])`, ip234 `SWITCH(304, L392, L232)`: 304 -> ip242 `Map.Byte[24]:=1`, InitObject 2
  (Zorn), 4 (Thorn), RunSoundCode(0,53) + the SYSVAR[3] wait, **ip279 `Byte[8]:=125`**. No region (InitRegion 8/9/10 and
  e5/e6/e7/e15 only on the default L392). No control: Zorn e2 is the defined player (e2 t0 ip109) and nothing sets
  `Map.Bit[158]` at 304, so the tail's EnableMove (ip588) is skipped.
- Conductor e0 t1: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 0. Stage 1: walks; **151** `[INCS][TIME=-1]` (e2 ip166, window 2) +
  **152** (e4 ip151, window 3); gate ip172-206; **KEYON e2 ip215**. Stage 2: **153** "This is terrible!" WindowSync (e2
  ip307). Stage 3: **154** "Our heads, Queen Brahne will have!" WindowSync (e4 ip220). Stage 4: **155** (e2 ip343) + **156**
  (e4 ip242) [INCS]; **KEYON e2 ip392**. Stage 5: long walks (e2 7 legs, e4 7 legs), **157** (e2 ip1216) + **158** (e4
  ip366) [INCS]; **KEYON e2 ip1265**. Stage 6: e2 walk, RunSharedScript(3), DisableMove ip1396, PreloadField(5,153) ip1418,
  Wait(25), **ip1520 `Int16[2]:=316`**, **`Field(153)` ip1528** (F: Field(31245)).
- 154's store sites: route e0 t0 ip26/53/61/123/142/204/279, e2 t1 ip1520; error ip101/182/497/531; dead ip45, ip134,
  ip215; off (entrance 315 only) e5 t3 ip675 `Bit[3852]`, e8/e9/e10 t2 ip195/ip355.

## 153 -- visit 3, entrance 316: Zorn & Thorn argue
- Main_Init ip255 316 -> ip805 `Map.Byte[24]:=100`, InitObject 18 (Zorn: DefinePlayerCharacter e18 t0 ip117), 20 (Thorn),
  SetFieldCamera(0), MoveCamera. No region, no `Map.Bit[158]` (e18/e20 set none): no control.
- Stages 100-114 (`stages153.out`): **159** (e20 ip180 Sync), **160** (e18 ip243 + wait ip261), **161** (e20 ip249), **162**
  (e18 ip279), **163** (e20 ip267 + wait ip287), **164** (e18 ip312); KEYON pair **165** (e18 ip395) + **166** (e20 ip381),
  **KEYON e18 ip444**; walks; **167** (e18 ip598), **168** (e20 ip696), **169** (e18 ip667), **170** (e20 ip718), **171** (e18
  ip685 + wait ip705), **172** (e20 ip751); KEYON pair **173** (e18 ip798) + **174** (e20 ip834), **KEYON e20 ip883**.
  Stage 114: e18 RunSharedScript(19), **ip890 `Byte[8]:=0`**, DisableMove ip953, PreloadField(5,151) ip975, Wait(65),
  **ip1077 `Int16[2]:=110`**, **`Field(151)` ip1085** (F: Field(31244)).

## 151 A. Castle/Throne (EVT_ALEX1_AC_RST, fbg_n02_alxc_map039_ac_rst_0, block 3) -- visit 4, entrance 110
- Main_Init e0 t0: ip232 `Int16[2]==110` -> ip243 `Map.Byte[24]:=1`, InitObject 3 (Brahne), 4 (Zorn), 5 (Thorn), 17
  (Beatrix), 12 (the Pluto captain = Steiner), RunSoundCode(1792,27) + wait, **ip315 `Byte[8]:=125`**; ip461 `SC<12000`
  true (camera 0). No region (InitRegion(8) only on the default L340). No control: Brahne e3 at 110 gets SetObjectFlags(7)
  (SHOWN, collides), EnableHeadFocus(0), SetObjectLogicalSize(1,1,1) ip166, **DefinePlayerCharacter ip171**; nothing sets
  `Map.Bit[158]`.
- Conductor e2 t1: 1 -> 2 -> ... -> 22 -> 23 (the exit in stage 23 itself). Windows (`stages151.out`):
  1: **175** (e4 ip204) and **176** (e5 ip209) `[TIME=20]` self-closing; **177** (e12 ip461 + wait ip477) -- 2: **178** (e17
  ip253 Sync) -- 3: **179** (e5 ip370) -- 4: **180** (e4 ip384) -- 5: **181** (e17 ip317 + wait ip332) -- 6: KEYON pair **182**
  (e4 ip467) + **183** (e5 ip469), **KEYON e4 ip516** -- 7: **184** (e12 ip613) -- 8: **185** (e17 ip346) -- 9: **186** (e4 ip608)
  -- 10: **187** (e5 ip538) -- 11: KEYON pair **188** (e4 ip644) + **189** (e5 ip560, a WindowSync [INCS]), **KEYON e4 ip693** --
  12: **190** (e17 ip363 + wait ip378) -- 13: waits (e3 Wait(90), e12 40+50) and Beatrix's walk -- 14: **191** (e3 ip307 +
  wait ip328) -- 15: **192** (e17 ip752) -- 16: **193** (e3 ip342 + wait ip363) -- 17: **194** (e17 ip769) -- 18: **195** (e3 ip377
  + wait ip398) -- 19: KEYON pair **196** "General Beatrix!" (e3 ip426) + **197** (e17 ip793, WindowSync [INCS]), **KEYON e3
  ip475** -- 20: **198** "And, Captain...uh..." (e3 ip576, Wait(10), WaitWindow ip590), **SetCharacterData(3,0,3,5,3)
  ip593**, Wait(5), **Menu(1,3) ip603 = Steiner's naming screen**, Wait(10) ip607, **ip610 `Byte[6] |= 8`**, Wait(10) --
  21: KEYON pair **199** "Captain [STNR]!" (e3 ip693) + **200** (e12 ip803, WindowSync [INCS]), **KEYON e3 ip742**, then
  **201** "Go find Garnet!" (e3 ip771 WindowSync) -- 22: KEYON pair **203** (e12 ip886) + **202** (e17 ip862, WindowSync
  [INCS]), **KEYON e12 ip935** -- 23: e2 t1 **ip735 `Byte[8]:=0`**, DisableMove ip808, PreloadField(5,153) ip830, Wait(65),
  **ip932 `Int16[2]:=328`**, **`Field(153)` ip940** (F: Field(31245)).
- 151's store sites: route e0 t0 ip22/49/57/119/138/200/315, e3 t1 ip610, e2 t1 ip735/932; error ip97/178/960/994; dead
  ip41, ip130, ip211; other entrances ip410 (L340); off e3 t3 ip909 `Bit[3793]` (Brahne's talk: she is the player at 110),
  e8 t2 ip38/ip237 (default entrance only).

## END: arrival in 153 at 328 (visit 5)
Cut at 153's first row of its FIFTH visit, e0 t0 ip22 `Bit[191]:=0` (S: real 153; F: member(153) 31245), right after
151's chain row ip932 `Int16[2]:=328`. 153's dispatch (ip255 -> L603 at 328: `Map.Byte[24]:=40`, InitObject 32/16/17,
InitRegion 23/24/25, ...) is past the cut. The driver must end at this ARRIVAL, not at the run's first 153 poll:
`end_visit` (Harness gaps).

## SC ladder -- no rung inside O5
| value | where | when |
|---|---|---|
| 1190 | the warp's residue in field 70 (bytes 0 and 1: 0 -> 166, 0 -> 4) | O5's start (a true run arrives with it from 150 e3 t1 ip1966, O4's rung) |
| (1400) | 55 e10 t1 ip582 (L474) | past the end: ip500 `SC > 1400` false -> ip582; ip568 is the debug twin behind ip500 + a KEYON-8 window. Then 1410 at 54 e4 t1 ip458 |
**No `Global.UInt16[0]` store in 151 or 153-167** (census of the listings; the only reads are 153 e0 t0 ip232 `>1900` and
151 e0 t0 ip461 `<12000`). O5's LADDER check is "no rung": SC 1190 at the start (residue) and at the end.

## FieldEntrance chain
325 (the warp's residue, bytes 2 and 3: 0 -> 69, 0 -> 1) -> 304 (153 e3 t1 ip3150) -> 316 (154 e2 t1 ip1520) -> 110 (153
e18 t1 ip1077) -> 328 (151 e2 t1 ip932).

## Expected story keys, in order (S side; F identical in donor terms) -- pick 1 ("Examine her face")
| visit | field | sid tag | ip (L) | key |
|---|---|---|---|---|
| 0 | 70 | warp residue | | SC bytes 0 (0->166), 1 (0->4); FieldEntrance bytes 2 (0->69), **3 (0->1)**: exactly **4** rows (O2-O4 had 3), set aside by the front cut |
| 1 | 153 | e0 t0 | 22 (16), 49 (43) | Bit191:=0, Bit184:=0 (masked) -- ip22 is the START row |
| 1 | 153 | e0 t0 | 57 (51), 119 (113), 138 (132), 200 (194) | Int16[9]:=-1 (old 643), Byte13:=0 (old 1), Int16[11]:=-1, Byte14:=0 |
| 1 | 153 | e3 t1 | **1741 (1333)** | **Bit[3795]:=1** (SYSVAR[9]; old 0) -- the stored choice |
| 1 | 153 | e3 t1 | 2953 (2545), 3150 (2742) | Byte8:=0 (old 125 raw / 75 true), Int16[2]:=304 (chain) |
| 2 | 154 | e0 t0 | 26, 53 | Bit191, Bit184 (masked) |
| 2 | 154 | e0 t0 | 61 (51), 123 (113), 142 (132), 204 (194), 279 (269) | Int16[9]:=-1, Byte13:=0, Int16[11]:=-1, Byte14:=0, Byte8:=125 |
| 2 | 154 | e2 t1 | 1520 (1409) | Int16[2]:=316 (chain) |
| 3 | 153 | e0 t0 | 22, 49 / 57, 119, 138, 200 | masked / the same four ambient keys as visit 1 (now old -1, 0, -1, 0) |
| 3 | 153 | e18 t1 | 890 (766), 1077 (953) | Byte8:=0, Int16[2]:=110 (chain) |
| 4 | 151 | e0 t0 | 22, 49 / 57, 119, 138, 200, 315 (309) | masked / the four ambient keys, Byte8:=125 |
| 4 | 151 | e3 t1 | **610 (426)** | **Byte6 \|= 8** -- value 8 after the raw warp (11 on a true run): START-DEPENDENT |
| 4 | 151 | e2 t1 | 735 (724), 932 (921) | Byte8:=0, Int16[2]:=328 (chain) |
| 5 | 153 | e0 t0 | 22 (16) | the cut |
27 store rows a run (23 writes + the 4-key chain; no SC) in **23 distinct keys** (153's four ambient keys recur at visit
3), beside 8 masked rows. With pick 0 the only change is ip1741's value (0, a same-value store).
Forbidden (diagnostic): 153 e28 t2 ip38/ip227 (cause walk); every error-path, dead and off-route site above; a second
ip1741 row; an ip1741 value other than the frozen pick; any row from 153 e23/e24/e25/e32 or e15 before the cut.
Not gEventGlobal: Steiner's name (PLAYER.Name), SetCharacterData, the camera index, Map vars (Byte[27] the branch).

**End state at the arrival in 153@328 (raw start, pick 1):** SC 1190; Int16[2] 328; Byte[6] 8; Byte[8] 0; Bit[3795] 1;
Byte[13] 0; Byte[14] 0; Int16[9] -1; Int16[11] -1; Bit[191] 0; Bit[184] 0. Untouched by O5 (New Game values after the raw
warp): UInt16[19] 0, UInt16[21] 0, Byte[303] 0, Byte[4] 0, Byte[17] 0, Byte[18] 0, Byte[475] 0, Bit[3815] 0, Bit[3717]
0, Bit[3718] 0, Int16[469] 0, Byte[472] 0, Byte[206] 0.

## Choices
- **128** (153 e3 t1 ip1724 `WindowSync(0,128,128)`): `[PCHC=2,1][WDTH=0,0,16,-1,1,90,-1,2,117,-1][IMME][ZDNE]\n“Hmm[SPED=2]...
  [SPED=-1]”\n[CHOO][MOVE=18,0]Let her pass\n[MOVE=18,0]Examine her face`. **The cursor opens on option 0 ("Let her
  pass")**: flags 128 has bit 0 clear, so `sChoose = sChooseInit` = 0 (ETb.cs:100-103), and 151/153/154 hold no
  choose-param op (the only setter is ETb.cs:259). PCHC's 2nd parameter is the CANCEL choice (1). Stored twice: **ip1741
  `Global.Bit[3795] := SYSVAR[9]`** and ip1749 `Map.Byte[27] := SYSVAR[9]` (the conductor's 21-vs-31 branch); both
  branches rejoin at stage 23.
- **Frozen pick: "Examine her face" (absolute 1)**, rule `{donor 153, sc [1190], match "her face", pick "her face", once:
  true, beat "choice128"}`, answered by `g.choose(1)` (O1's 52, O4's encore), never `take: "default"` (V3 by design).
  Why 1: lesson 13 -- the pick IS the claim; a non-default pick turns Bit[3795] 0 -> 1 and so distinguishes a fork that
  stores the answer from one that stores a constant (pick 0 writes 0 over 0). Cost: path 1's 11 windows replace path 0's
  2 (+9 pages, ~35 s a run). Requires the opt-in QUIET WINDOW after 127 (Harness gaps): page 127 (WindowSync, typed at
  [SPED=2]) is followed by 128 within ~2 ticks of closing, so a re-press decided on a stale 127 sample would answer 128 at
  its cursor (0). Fallback with no driver change: pick 0 with `take: "default"` (O2's shape; every O2 choice was option 0).
- Expected publication (unmeasured; lesson 1): options `[<"[ZDNE]\n“Hmm...”" or ''>, 'et her pass', 'Examine her face']`,
  active [0, 1], selected 0. "her face" matches only the second line in every variant.
- Keep O1's `{None, "want to skip", "default"}` rule (no movie on the route can raise it).
- Bit[3795]'s readers (start-state reader's census, not re-run): 153 (only behind `Int16[2]==3`) and field 51.

## Naming
Steiner's naming once, 151 stage 20: e3 t1 ip590 WaitWindow (198 closed), **SetCharacterData(3,0,3,5,3) ip593**, Wait(5),
**Menu(1,3) ip603**, Wait(10), **ip610 `Byte[6] |= 8`**. The MENU opcode opens EventService.StartMenu unless
`Configuration.Hacks.DisableNameChoice` (DoEventCode.cs:2317-2341); the live Memoria.ini has `DisableNameChoice = 0`
(line 256, [Hacks] Enabled = 1): the screen opens. NameSettingUI pre-fills the DEFAULT name for ids < 12 (start-state
reader: NameSettingUI.cs:137/151), so `accept_name` stores "Steiner" on both sides. Register `{donor 151, sc 1190, beat
"named"}` (rule 4, segment_drive.py:2867-2880); freeze DisableNameChoice = 0 in P-SETTINGS. The page 198 -> naming
adjacency is O2's proven shape (116: 396 -> Menu(1,1)).

## Battles, minigames, FMV
None: no Battle/SetRandomBattles/AICON/ATE/Menu(4,0)/Cinematic op in 151, 153, 154 (opcode census); the battle registry
is empty (any battle V10); no movie policy. No minigame: the 12 `[INCS][TIME=-1]` KEYON pairs are rule 7's (repeat Confirm
until both windows close; an edge before the INCS/250-tick gate is lost): 153 e3 t1 ip2336, ip2711; 154 e2 t1 ip215, ip392,
ip1265; 153@316 e18 t1 ip444, e20 t1 ip883; 151 e4 t1 ip516, ip693, e3 t1 ip475, ip742, e12 t1 ip935.

## Nondeterminism
1. Choice 128: the pick is the stored key (a frozen rule; both sides the same). A stray Confirm on 128 would store 0.
2. The stair walk: where control drops (the -450 contour crossing, wherever the walk meets it) and how late the loss
   sample is -- no key depends on either (stage 17 teleports him).
3. Off-route but live during stage 6, all avoided by the route: e26/e27 side scenes (pages 119-123, no store, control
   back at e3 t1 ip1266); e28 the back door (Byte[8]:=25 ip38, Int16[2]:=5 ip227, Field(150)); Blank's talk (118, no store).
4. Timing only: the KEYON gates (<= 250 ticks), [TIME=20] windows 137/140/175/176, [SPED=2] type-outs, NPC walks, fades,
   151's Wait(90). No SYSVAR[0] (random) read in 151/153/154; no battle, no ATE.
5. Start: Byte[6] (8 vs 11) and the `old` of the first 153 prologue rows and of ip2953 -- the same on S and F.

## The walks
**One control grant up to the end** (plus its conditional re-grant). Every other visit (154@304, 153@316, 151@110) has a
script-defined player and no EnableMove; control there is V4.

### CONTROL 1 -- 153 (S) / 31245 (F), entrance 325, SC 1190, visit 1, cell (153, 1190), step 0
- **Character:** Zidane, e3 (GEO_MAIN_F1_ZDN; DefinePlayerCharacter e3 t0 ip176); controller radius **80**
  (SetObjectLogicalSize(20,24,40) ip218) = the planner's default clearance.
- **Grant:** e3 t1 stage 5, **EnableMove ip785** after WaitWindow(1) ip752 (page 117) and `Map.Bit[158]:=1` ip755.
  No window is up at the grant (lesson 3 does not apply); Blank is shown with NO player collision (flags 5).
- **Spawn (the bytes; REHEARSE, lesson 6):** (1105,-78), the end of stage 1's `Walk(1105,-78)` ip537; stages 3-5 only
  animate and turn him toward Blank. Tri 66, floor 2, PSX y -1 (published ~1), 644 u from the nearest wall.
- **Goal = a HEIGHT, not a region:** control ends on the first tick he stands at PSX y <= -450 (published y >= 450),
  e3 t1 ip859 -> DisableMove ip893. Only the curved west stair (floor-2 tris 52/53/55/56/57/61/... rising -1 -> -1492)
  gets there; the -450 contour runs across tris 56/53 from (-1403,476) (inner edge) via (-1583,601) to (-1722,642)
  (outer edge). 2-3 ticks after the loss stage 17 TELEPORTS him to (-1165,856) (ip1466; published y ~231) and walks him
  up by script ((-1419,602), (-1602,298), (-1631,10), ... (-978,-554), (-329,-624)).
- **Path** (PlayerWalkmesh(stock 153, closed_tris = the 33 floor-0 tris at y -1499), `route_avoiding` from the spawn,
  avoid e26/e27/e28): **(1105,-78) -> (-879,818) [tri 55, PSX -114] -> (-1263,754) [tri 78, -308] -> (-1700,300) [tri 61,
  -591]**, 3196 u; the line crosses PSX -450 at ~(-1482,527), 315 u into the last leg; ~2 s of running at ~60 u a tick.
  Leg gaps to (e26, e27, e28): leg 1 (350, 885, 634), leg 2 (624, 1711, 2650), leg 3 (1013, 1514, 3022) -- every one past
  the 56 u keep-out margin. On the PLAIN mesh there is NO route to any goal past x ~ -450: floor 0 mixes the upper
  corridor (33 tris, y -1499, over the hall in XZ) with 15 ground tris, and `point_on_walkmesh` returns the upper tri
  first (e.g. (-245,42): tri 42 y -1499 before tri 114 y -1). Closing floors 0+1 also plans (via (1041,-14), 3202 u) but
  removes 15 real ground tris; closing the 33 upper tris is the exact fix (floor 1, flags 0xa001, is already closed to
  the player at mask 255). `reconcile/route153.out`.
- **Hazards and how the driver avoids them:**
  - **e28, the back door** (2850,347)(2850,-13)(1739,-74)(1739,406): live whenever he has control (its tag 2 tests only
    SYSVAR[2]): Byte[8]:=25 ip38, Int16[2]:=5 ip227, Field(150) ip235 (F: Field(31243)). 634 u east of the spawn: in
    `avoid` (the route heads west), a registered exit (role `exit`, to 150, entrance 5: V11 on a landing) and forbidden
    (cause `walk`). He spawned at (2102,75) INSIDE it but was walked out before control.
  - **e26 / e27, the side scenes:** e26 = e23's quad (-227,3000)(200,3000)(212,935)(-264,924), fires on the ground
    (`f[1] > -100`) with z > 1333 at stage 6 -> Byte24:=7; e27 = e25's quad (-777,-2348)(777,-2348)(777,-900)(-777,-900),
    any height at stage 6 -> Byte24:=14. Each plays pages 119-123 (rule 7), stores nothing, walks him back to (1105,-78)
    (ip1230) and re-grants at ip1266, after which stage 6 resumes. In `avoid`; role `walkin` (they take control); the
    step's `interrupts: 1` absorbs one.
  - **Blank** (e7, (1068,373), flags 5: no player collision; talk on): his talk is a Confirm, never pressed during a
    walk; the route passes 396 u from him. Hidden colliders e9 (-551,2104), e11 (30,-1500), e31 (0,1915; on the upper
    level) are > 1400 u off the route. e22 (camera code) switches cameras at x 500 -- visual only (SETCAM #493 wrapped).
  - **The calibration probes** at the spawn (~4 ticks, <= ~240 u): `route_to` calibrates CLEAR of the `avoid` polygons
    with the key prior (`_calibrate_clear_of`); every SetControlDirection in 153 is (248,0), so one basis serves the field.
  - **Facing gate:** none (a height test; scan_gateways reports face_gate None for every gateway of 151/153/154).
- **The step** (cell (153, 1190), steps_default O2's): `{kind: "trigger", name: "the stairs", goal: [-1700, 300],
  until: {"x_le": -1100}, avoid: ["153.e26", "153.e27", "153.e28"], closed_tris: [0,1,2,3,4,5,6,7,8,9,11,14,15,16,17,18,
  19,20,21,23,24,28,32,33,34,35,38,39,41,42,43,45,46], npcs: true, interrupts: 1, beat: "stairs"}`. The evidence is
  x-only on purpose: every control loss at x <= -1100 in stage 6 is the stair's (e26 x -264..212, e27 x -777..777, e28
  x >= 1739, Blank at x 1068); the contour sample (x -1403..-1722), the teleport (-1165,856) and the scripted climb (x <=
  -1100 for ~50 ticks, ~1800 u at speed 37, into the leg toward (-978,-554)) all satisfy it, so a late loss sample (lesson 10: up to
  ~200 ms of empty reads) still reads "done". A height predicate (published y >= 450) would REJECT the teleport sample
  (y ~231), and `{x_le:-1100, z_ge:300}` fails once the climb passes (-1602,298) (~713 u past the teleport at speed 37:
  ~20 ticks after the loss).
- **Regions to register for place 153:** `153.e28` role `exit` (to 150, entrance 5, face_gate None); `153.e26`,
  `153.e27` role `walkin` (live at stage 6 only); `153.e23`, `153.e24`, `153.e25` role `dormant` (InitRegion only at 328 and
  the default entrance, Main_Init ip626-632/ip1115-1121; O2's 115.e14 precedent) -- they are the TWIN quads of e26, e28,
  e27, so as exits they would mislabel a side-scene loss. 154: e8/e9/e10 `dormant` at 304; 151: e8 `dormant` at 110.
- **Numbers to rehearse (R-STAIRS, stock, x2):** the grant position (expect (1105,-78)); the loss sample (expect x in
  [-1722,-1403] and published y 450-470, or the teleport/climb if late); ticks from the grant to the loss; the 2-3 tick gap
  to CreateObject; whether e9/e11/e31 (flags 14: hidden colliders) are published as objects; the walk's wall contacts on
  the stair (slopes 0.85-0.93); calibration probe lengths at the spawn.

### CONTROL 1b (conditional) -- 153, stage 16 re-grant
Only after a side scene: e3 t1 L677 SetFieldCamera(1), Walk(1105,-78) ip1230, `Map.Bit[158]:=1` ip1236, EnableMove
ip1266. The same step runs again (its interruption counted); no key changes.

### No other control up to the end
154@304 (Zorn e2 the player, no Map.Bit[158]), 153@316 (Zorn e18), 151@110 (Brahne e3, logical size 1): any control
sample there is V4 (game). The published `player` is that actor (the harness publishes no character identity).

### Beyond the end (O6's walks, survey -- not re-derived to this standard except where noted)
- 153@328: Steiner (e32, radius 120). **Grant e32 t1 ip2412 at (-245,42) on the GROUND** (settled here: stage 44 walks him
  DOWN the stair (-150,-550) -> (-1235,-558) [-1119] -> (-1595,-195) [-845] -> (-1370,804) [-316], stage 45 to (-575,807)
  and (-245,42), tri 114 y -1). Goal: north door e23 (ground and z > 1333), e.g. (19,1620) tri 151; ~1600 u straight.
- 154@315 (spawn (-58,-3758) y -1741, the upper gallery): down to the ground and south into e8 on its GROUND branch
  (upstairs -> 153@301). Overlapping levels; Dojebon patrols the gallery.
- 158 -> 159 (forced monologue at e16 t1 ip390 once x < -1600 or x > 1600 or z < 800: Bit[3796]:=1 ip672) -> 160 -> 162 ->
  163 (plans at 80, not 120) -> 164 (spiral; exit e2 needs f[1] < -12000; the knight e1 t1 ip178 walks once f[1] <= -8400,
  Bit[3811]:=1 ip230 after 4 legs + RunAnimation 9920: a race with the exit) -> 165 (exit needs f[1] < -15000) -> 166 (no
  control; FMV004 Cinematic(0,9,1,1) ip633, MBG.cs:830 type 0) -> Field(55) (F: member(166) 31258 is unchanged -> REAL 55).
- O6 needs: height-aware routing (154/164/165), Steiner's radius 120 (DoEventCode.cs:1507 makes 164's 80), a waypoint step
  kind, the movie policy cell (166, 1190) after its own A/B, and a decision on the 55 seam (side_ends F [55] or rebuild
  member(166) with `55 = 31205`). 153@328 also runs e15 t0 ip32 `Byte[8]:=125` (RunSharedScript(15), e32 t1 ip866) and
  the START-DEPENDENT `UInt16[19] |= 8` (e32 t1 ip2206: 8 raw / 1807 true).

## The start
**Recommended: (a) the raw warp, O2-O4's mechanism.** New Game, `storytrace 1`, then in field 70 (before 70 e0 t0 ip475)
`warp 153 325 1190` (S) / `warp 31245 325 1190` (F) (HarnessAgent.cs:653 -> Ff9mkDebugMenu.HarnessWarp: FieldEntrance
and ScenarioCounter set at Ff9mkDebugMenu.cs:2130/2135 before SetNextMap; it needs UIState FieldHUD).
- **Residue: FOUR rows** `[[0,0,166],[1,0,4],[2,0,69],[3,0,1]]` -- 325 = 0x0145 moves FieldEntrance's HIGH byte too
  (StoryTrace.Diff is per byte, StoryTrace.cs:512-522). O2-O4's START contract expected 3: O5's must expect 4.
- Front cut at 153's (member(153)'s) first `w` row, e0 t0 ip22. START requires ip119 (Byte13 old 1 -> 0), never ip97 /
  window 56.
- **Reads on the route resolve the same branch from the raw warp and from a true O1-O4 run** (start-state reader,
  re-checked at the cited sites): SC (153 ip232 `>1900`, 151 ip461 `<12000`: both starts 1190), Int16[2] (the warp sets 325;
  every later visit's dispatch reads the chain value), the ambient Byte13/14/Int16[9]/[11] (normalized by 153's first
  prologue; only `old` differs: Int16[9] 643 vs -1, Byte13 1 vs 0), Byte[8] (always written before its sound-op read; the
  ip2953 row's old 125 vs 75), Bit[3795] (written at ip1741 before any read; reads only behind `Int16[2]==3`), Byte[475]
  (read only by 151 e3 t3, Brahne's talk -- unreachable at 110), party (none read before 153@328's rebuild), the
  controlled character (script-defined), Steiner's name (the default pre-fill either way).
- **START-DEPENDENT keys up to the end: ONE.** 151 e3 t1 ip610 (L426) `Byte[6] |= 8`: writes 8 after the raw warp, 11 on a
  true run (O1 50 e17 t1 ip3240 `|= 1`, O2 116 e2 t1 ip765 `|= 2`), the same on S and F. Register in O2's 4.5 shape:
  `{donor 151, sid 3, tag 1, ip 610, off 426, m 1, src eb, op "|=", target "Global.Byte[6]", value 8, prior "newgame0",
  after_o4 11}`. (UInt16[19] |= 8 is O6's: 153@328 e32 t1 ip2206.)
- (b) Harness pokes in field 70 before the warp (`byte 6 3`; optionally `byte 475 100`, `flag 3815 1`) would make the 151
  row write 11, as `src: harness` rows needing a new START contract: unnecessary for an S/F claim; the owner's call if the
  stored VALUE must be the true game's. (c) The narrative-state story seed: unsuitable (F-only `[startup]` rows; no channel
  for Byte[6]).
- Party and names: [Zidane] at the arrival in both starts (New Game ff9play.cs:74-78 vs 150's rebuild); no party read before
  the cut. Zidane/Vivi keep their default names; Steiner gets the default at 151. Gil 500 (raw) vs >= 10500 (true): never
  read on the route. Untraced and audio-only: field 70's BGM keeps playing after the raw warp until 153 e3 t1 ip2961 fades it.

## Disputes settled (reader claims vs the bytes / engine)
1. **The end.** Bytes and data: the arrival in 153@328. Harness: ends in 153 are a GAP (the start place), ends 154@304,
   151@110 and 55 are ready. BYTES + CODE: rule 1 (segment_drive.py:2801 `if self.fid in self.ends`) fires on the first poll
   in an end field and `cut_at_end` (segment_trace.py:127-136) cuts at the first end-place row -- both would end O5 at its
   start. CHOSEN: the arrival in 153@328 WITH an opt-in `end_visit` (the harness reader's smallest fix); fallback 151@110.
2. **The stair closure.** Walks: `closed_tris` = 33 floor-0 tris. Harness: `closed_floors [0,1]`. WALKMESH: floor 0 = 33
   tris at y -1499 (exactly the walks list) + 15 ground tris at y -1; floor 1 (2 tris) is 0xa001, already player-closed.
   Both plan (`route153.out`); `closed_tris` is exact, `[0,1]` also shuts 15 walkable ground tris.
3. **The stair trigger's evidence.** Walks: `until {x_le:-1100, z_ge:300}`. Harness: a y-aware `until` (or a synthetic
   stair-band target). BYTES: the loss sample can be the contour, the teleport (-1165,856; published y ~231) or the
   scripted climb; `{x_le:-1100}` holds for all of them for ~50 ticks and for nothing else in stage 6; y >= 450 rejects the
   teleport; z >= 300 fails after (-1602,298). SETTLED `{x_le: -1100}` -- no harness change.
4. **Choice 128's pick.** Bytes and data: 1 ("Examine her face"). Harness: prefer 0 (a stray press answers the same).
   SETTLED (design, lesson 13): 1, with the opt-in quiet window after 127; 0 with `take: "default"` is the no-change
   fallback and a weaker claim (0 over 0). The cursor opens on 0 (ETb.cs:100-103) -- all readers agree since O4.
5. **Steiner's grant at 153@328 (O6).** Bytes and data: about (-24,-74) on the UPPER walkway (y -1499). Walks and harness:
   (-245,42) on the ground. BYTES: e32 t1 stage 40 walks to (-24,-74) (ip778), but stage 44 walks him down the stair
   (ip1176-1197) and stage 45 to (-575,807) and (-245,42) (ip1360/ip1367) before the grant (ip2412): the GROUND (tri 114).
6. **153 e15 t0 ip32 `Byte[8]:=125` (O6).** Bytes: dead, e15 not instanced. BYTES: e32 t1 ip866 `RunSharedScript(15)` runs
   entry 15's code at 328 (stage 40): live past the cut; how the trace attributes a shared script's store is O6's question.
7. **166's movie (O6).** Data: "no movie opcode". BYTES: 166 e6 t1 ip633 `Cinematic(0,9,1,1)` = FMV004 (MBG.cs:830), played
   by ip711 `Cinematic(2,0,0,0)`.
8. **Pages 113/114.** Data: "none, or turn pages if they block". BYTES: e7 t1 stage 2 waits on both (WaitWindow(1) ip337,
   ip351): pages, each closed by a Confirm.
9. **Brahne at 151@110.** Start-state: "an invisible anchor". Data: "a size-1 dummy". BYTES: SetObjectFlags(7) (show model +
   collisions, DoEventCode.cs:2073) ip160, size 1 ip166, DefinePlayerCharacter ip171: SHOWN, the defined player, no control.
10. **"talk" beats at 154/153@316/151 (data).** BYTES: pages and KEYON pairs; nobody is talked to; no control.
11. **Run times.** Bytes 3/4/5.5/8 min, data 2.5/3.3/4.5/7 for candidates 1-4. Mine ~3/3.8/4.7/6.5 (pick 1) -- estimates.
12. **Steiner's radius and 164 (O6).** Walks: 164 makes it 80 (DoEventCode.cs:1507). BYTES + ENGINE: `effMapNo == 164 && sid
    == 7 && size == 30 -> 20` (verified), wrapped by effMapNo.

## Harness gaps (summary; status and evidence in the structured result)
GAP: the end in the start place -> opt-in `end_visit` (rule 1, `end_row`, the live scan and `cut_at_end` count the visit;
FakeGame: a start place revisited, ended at its 2nd return). RISK: the 127 -> 128 stray Confirm -> opt-in `quiet`
(O4's `quiet_tick` outside the Chanbara policy); recovery from 151's naming screen (retry the warp after `accept_name`;
an R-VOID stopped in 151). READY: the stair walk with existing keys (`closed_tris`, `until`), pages, 12 KEYON pairs, 4
timed windows, the naming (rule 4), `choose(1)`, the empty battle registry, the stop page "Env Play()", the raw-warp start
(4 residue rows: an analysis change), calibration (one basis per field), no facing gate, no hot-spot, no ATE. MINOR: the
region roles (dormant twins), P-FLOOR for 31245, P-SETTINGS + DisableNameChoice, the published player identity.

## Fork gates (summary)
Nothing on the route can change a story write between S and F except through a gate that is wrapped in the live source
and the deployed DLL: s62's VIB donor-name key (153 e3 t1 ip2443/2448/2453, stage 27; HonoluluFieldMain.cs:93-104 +
vib.cs null guards) -- ON the route, first exercised on member(153) by O5's first F run (an unwrapped miss would abort the
frame and drop later stores: a FORK ONLY/STOCK ONLY finding, never silent); SETCAM #493 (153, wrapped; only SYSVAR[1]/the
camera); the naming MENU (no field gate); no battle/ATE/FMV/autosave row on 151/153/154. Visual only and raw:
PSXCameraAspect's letterbox on 153/154 camera 0. P-DONOR clean (31240-31259 once each, FF9CustomMap only); re-run P-DONOR,
P-EB, P-TEXT (block 3, per language) at session time -- the install is shared.

## Could not determine / unverified
The grant position and the loss sample in game (bytes only: rehearse); choice 128's published options and `selected`
(inferred from O4); the stray-press race 127 -> 128 (not measured); the run time (~6.5 min, estimated); s62's VIB path on
member(153) in game; whether hidden flag-14 objects are published; how a [TIME=20] [NFOC] window reacts to rule 7's Confirm
(O4 measured 150's as inert); `end_run` from 151's naming screen; Bit[3795]'s reader census (the start-state reader's);
every O6 fact beyond the spot checks named above.
