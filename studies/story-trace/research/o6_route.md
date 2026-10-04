# Stock O6 route: raw warp into 151 (FieldEntrance 110, SC 1190) -> the royal seat box and Steiner's naming -> 153 at 328, the Knights of Pluto and Steiner's first walk -> Field(154) at 315  (reconciled)

The reconciler's own decode. Every ip below was decoded from the stock US `.eb` by `reconcile/ebtool.py` (O5's
reconciler decoder: storytrace.stock_script_source + ScriptIndex + instruction_stores over the MAIN repo's ff9mapkit,
master c954f986) and checked against the listing. Every engine claim was re-read in C:\gd\FFIX\Memoria (the deployed
x64/x86 Assembly-CSharp.dll is sha256 ba9762423da8f3d7..., Sep 26 17:10, re-hashed read-only today: O5's pinned engine).
- `ip` = abs - entry start = the s88 trace ip. `Lnnn` = offset from the function start (the predictions' `off`).
- Listings `reconcile/L{151,153,154,158..166,55,70}.txt` are byte-identical (cmp) to the bytes, data, walks, start-state
  and harness readers' copies and to O5's reconcile listings: NO reader decoded different bytes; every dispute below is
  interpretive. Texts: block 3, US (`reconcile/mes_151.json`; 150-167 share it). Stage blocks:
  `reconcile/stages151.out`, `reconcile/stages153_328.out`; conductor graphs `reconcile/stagemap{151,153}.out`.
- `SWITCH(base, default, case_base, case_base+1, ...)`; `SWITCHEX(default, value, target, ...)`. A 2-byte script constant
  is SIGNED (EBin.cs pushes an Int16): `const(65436)` = -100, `const(64136)` = -1400, `const(57136)` = -8400.
- Scratch evidence (all in `o6_research/reconcile/`): `forkdiff.out` + `langs.out` (the live members, 7 languages),
  `route153.out` + `goals153.out` (the walk, planned on the stock walkmesh), `wm154.out` (154's level links).

## Segment end: CHOSEN = arrival in 154 at 315 (153 e23 t2 ip211 `Field(154)`, after ip203 `Int16[2]:=315`), SC 1190

| # | exit (stock) | arrival | SC | est. min a run | needs | inside (cumulative) |
|---|---|---|---|---|---|---|
| 1 | 151 e2 t1 ip940 `Field(153)` (328, ip932) | 153 @328 | 1190 | ~1.1 | nothing | the royal seat box: 17 pages, 5 KEYON pairs, 2 timed windows, Steiner's NAMING (Menu(1,3) e3 t1 ip603), `Byte[6] \|= 8` (START-DEPENDENT); no control |
| 2 | (no Field) 153 e32 t1 ip2412 `EnableMove` | -- | 1190 | ~1.8 | a NEW end kind (end at control) | + the assembly: 11 pages, the shared script e15 (Byte[8]), Bit[3855]/[3854], the party rebuild, `UInt16[19] \|= 8` (START-DEPENDENT) |
| **3 CHOSEN** | **153 e23 t2 ip211 `Field(154)` (315, ip203)** | **154 @315** | **1190** | **~2 (100-130 s)** | **nothing: existing step kinds and rules** | + Steiner's first control and ONE walk on the ground to the north door (a `trigger` with `until`) |
| 4 | 154 e8 t2 ip363 `Field(158)` (300, ip355) | 158 @300 | 1190 | ~2.3 | a NEW waypoint step kind (`walk`) | + 154: a balcony over the ground (two legs), e8's balcony branch back to 153@301, Dojebon's patrol |
| 5-8 | 158 e2 ip230 -> 159 e11 ip201 -> 160 e5 ip235 -> 162 e3 ip235 | 159 .. 163 | 1190 | ~2.6-3.6 | as 4 | + 158; 159's forced monologue (Bit[3796]); 160/162 back doors 61/50 u from the spawns |
| 9 | 163 e2 t2 ip235 `Field(164)` | 164 @342 | 1190 | ~3.8 | as 4 (163's stair foot is narrower than Steiner's radius 120) | + 163 |
| 10-11 | 164 e2 t2 ip251 -> 165 e2 t2 ip241 `Field(166)` | 166 @344 | 1190 | ~4.3-4.6 | + a per-step `clearance` (164 plans only at <= 64; no fallback), the knight's Bit[3811] race (a hold + an order check) | + the two spiral towers (self-overlapping, height-gated exits) |
| 12 | 166 e6 t1 ip871 `Field(55)` (110, ip863) | REAL 55 on both sides | 1190 | ~5.8 | the seam (member(166) 31258 keeps a raw Field(55)); FMV004 played out or O7's own A/B | + 166's scene and FMV004 (45.41 s) |
| 13 | 55 e10 t1 ip582 `SC:=1400` | -- | 1400 | ~6.2 | a NEW end kind; F needs member(166) rebuilt with 55 -> 31205 (owner-gated) | the first SC rung after 1190; the start-dependent BRANCH at 55 e8 t1 ip1354 |

Run times are estimates calibrated on O5's MEASURED rate (R-FULL 99-112 s for ~36 pages, 7 KEYON pairs, a choice, one
walk and 474 ticks of scripted `op_22` waits). O6 to 154 holds 28 pages, 5 KEYON pairs, 2 timed windows, the naming, one
walk and 511 ticks of scripted waits (151: 319; 153@328: 192; `reconcile/waits.py`). O5's own bytes-only estimates ran
~2.5x too high; the readers' 2.5-3.3 min for this end are of that kind. Freeze the budget from R-FULL.

Why 3:
- **Nothing new to build, deploy or code.** The route members 31244 -> 31245 -> 31246 are deployed and every route
  `Field()` is retargeted in all 7 languages (`langs.out`). The driver needs no new kind: pages and KEYON pairs (rule 7),
  the naming (rule 4 + `accept_name`), one `trigger` step with existing keys (`closed_tris`, `until`, `avoid`, `npcs`),
  and the arrival end (rule 1). The end is clean: 154 is visited once, its first row (e0 t0 ip26) is the first store at
  that site in the epoch (emitted), and 154's Main_Init at 315 writes nothing but same-value ambient keys.
- **It holds every key the PLAN pointer names for 151 and 153@328**: the naming, `Byte[6] |= 8`, Bit[3855]/[3854], the
  party rebuild, `UInt16[19] |= 8` -- both START-DEPENDENT values -- and the shared-script store (the first Seq row since
  O1e), plus Steiner's first control.
- **It stops before the riskiest stretch.** Everything past 154 needs harness work that does not exist and has no
  in-game proof: a waypoint step for overlapping levels (154, 164, 165), a per-step clearance (164's narrow turn plans
  only at <= 64, `route_to` takes none: session.py:4139-4143), FakeGame per-field walkmeshes and height-gated regions,
  the 164 knight race, FMV004 and the seam into tshp 55. That is O7 (154@315 -> ... -> 166 -> 55), started cleanly by
  a raw warp `warp 31246 315 1190` with Steiner's control on arrival.
- **Why not 1 or 2**: 1 has no control and leaves the assembly's start-dependent key to O7 for nothing; 2 needs a new
  end kind. Why not 12 (the data reader's pick): six new risks in one segment, each with a harness gap; O5 ended early
  to keep its end clean, and the same reasoning applies twice over here.

## The member set (fork side) -- nothing new
O4's alxc disc-1 chain as deployed in FF9CustomMap (`o4_forks.json`, 31240-31259; O6 reuses it as O5 did):
member(151) 31244 `EVT_O4_ALXC_AC_RST`, member(153) 31245 `EVT_O4_AC_H2F`, member(154) 31246 `EVT_O4_AC_FTI`
(ForkDonorPatch.txt lines 79-81 `31244 151`, `31245 153`, `31246 154`, each donor once, FF9CustomMap only;
DictionaryPatch.txt lines 156-158 `FieldScene 3124x 11 ... 3` = text block 3). Re-diffed today, instruction by
instruction, in ALL 7 languages against that language's own stock donor (same sizes; `langs.out`):
- 31244: e2 t1 ip940 153 -> 31245; e8 t2 ip245 153 -> 31245 (default entrance only).
- 31245: e23 t2 ip211 154 -> 31246 (THE O6 EXIT); e24 t2 ip191 150 -> 31243; e25 t2 ip203 64 -> 31240, ip429 151 ->
  31244; e3 t1 ip3158 154 -> 31246; e18 t1 ip1085 151 -> 31244; e28 t2 ip235 150 -> 31243. `Field(204)` e3 t1 ip3296
  stays raw (the flashback branch, dead at SC 1190).
- 31246: e2 t1 ip1528 -> 31245; e8 t2 ip203 -> 31245, ip363 -> 31250; e9 t2 ip203 -> 31248, ip363 -> 31247; e10 t2
  ip203 -> 31248, ip363 -> 31259 (O7's doors).
So **F stays inside the chain end to end and ends in member(154) 31246**; S ends in real 154: `side_ends` {S: [154],
F: [31246]}. A real 151/153/154 on F is V19. (Off this route: member(166) 31258 is stock 166 byte for byte, so its
`Field(55)` is real -- O7's seam.)

## Ambient prologue (every visit's e0 t0)
`Bit[191]:=0`, `Bit[184]:=0` (masked), `Int16[9]:=-1`, Byte[13] (`==9` -> nothing; `==2 && Int16[9]<0` -> `:=9`, the
error path; `Int16[9]<0` -> `:=0`), `Int16[11]:=-1`, Byte[14] likewise. `Int16[2]:=10000` sits behind `Bit[184]==1`.
| visit | Bit191 | Bit184 | Int16[9] | Byte13:=0 | Int16[11] | Byte14:=0 | error path (must not fire) | old values (raw start) |
|---|---|---|---|---|---|---|---|---|
| 151 @110 | ip22 (L16) | ip49 (L43) | ip57 (L51) | ip119 (L113) | ip138 (L132) | ip200 (L194) | ip97/ip178 (:=9), window 56 ip950/ip984, ip960/ip994 | Int16[9] 643, Byte13 1, Int16[11] -1, Byte14 0 |
| 153 @328 | ip22 | ip49 | ip57 | ip119 | ip138 | ip200 | ip97/ip178, window 56 ip2304/ip2338, ip2314/ip2348 | all same-value (-1, 0, -1, 0) |
| 154 @315 (the end) | **ip26 = the cut** | ip53 | ip61 | ip123 | ip142 | ip204 | ip101/ip182, window 56 ip487/ip521, ip497/ip531 | same-value |
The incoming values come from field 70's prologue (70 e0 t0 ip57 `Int16[9]:=643`, ip130 `Byte[13]:=1`, ip138, ip200,
ip249 `Byte[8]:=125`). A warp after 70 e0 t0 ip475 (`Byte[13]:=2`) would take 151's ip97 and stop on window 56: the
START contract requires 151's ip119 (old 1).

## 151 A. Castle/Royal Seat (EVT_ALEX1_AC_SEAT_R; FBG fbg_n02_alxc_map039_ac_rst_0; block 3) -- visit 1, entrance 110
- Main_Init e0 t0: prologue; ip219 `SetControlDirection(244, 0)`; ip232 `Int16[2]==110` -> ip243 `Map.Byte[24]:=1`,
  InitObject 3 (Brahne), 4 (Zorn), 5 (Thorn), 17 (Beatrix), 12 (the Pluto captain = Steiner); `RunSoundCode(1792,27)` +
  the SYSVAR[3] wait (ip274-294); **ip315 `Byte[8]:=125`** (raw: 125 -> 125, a same-value store); ip343 `JMP(L432)`
  skips the default branch (L340: InitRegion(8), ip410). ip461 `SC<12000` true -> camera 0 + SPS. Tail: ip1002
  `Map.Bit[159]:=1`, ip1010 `Map.Bit[158]==1` false -> **no EnableMove**.
- No control in 151: Brahne e3 at 110 takes ip160 `SetObjectFlags(7)`, ip166 `SetObjectLogicalSize(1,1,1)`, **ip171
  `DefinePlayerCharacter`**; Steiner e12 t0 ip149 `SWITCH(110, L159, L147)` -> L147 (SetObjectFlags(7)) skips his own
  DefinePlayerCharacter/`Map.Bit[158]:=1`/EnableMove (ip169-ip215). Nothing sets `Map.Bit[158]` at 110 (the only
  setters are the talk handlers e3/e6/e7 t3 and e12's skipped L159).
- Conductor e2 t1 on Map.Byte[24], advanced by Map.Bit[231]: 1 -> 2 -> ... -> 22 -> 23 (`stagemap151.out`). Windows
  (`stages151.out`):
  - 1: **175** (Zorn, e4 ip204) and **176** (Thorn, e5 ip209) `[TIME=20]`, self-closing; **177** (the captain, e12 ip461
    WindowAsync + WaitWindow ip477) a page.
  - 2: **178** (Beatrix, e17 ip253 Sync). 3: **179** (Thorn, e5 ip370 Sync). 4: **180** (Zorn, e4 ip384 Sync).
    5: **181** (Beatrix, e17 ip317 + wait ip332).
  - 6: KEYON pair **182** (e4 ip467 `[INCS][TIME=-1]`) + **183** (e5 ip469); gate SYSVAR[8]<2 && Map.Byte[29] (250-tick
    countdown), **KEYON e4 ip516** (Confirm 0x20000 or Special 0x80000, the EDGE), CloseWindow(2)/(3).
  - 7: **184** (e12 ip613 Sync). 8: **185** (e17 ip346 Sync). 9: **186** (e4 ip608 Sync). 10: **187** (e5 ip538 Sync).
  - 11: KEYON pair **188** (e4 ip644) + **189** (e5 ip560, a WindowSync [INCS]); **KEYON e4 ip693**.
  - 12: **190** (e17 ip363 + wait ip378). 13: waits only (e3 `op_22(90)`, e12 40+50, e4/e5 30) and Beatrix's 8-leg walk.
  - 14: **191** (Brahne, e3 ip307 + wait ip328). 15: **192** (e17 ip752 Sync). 16: **193** (e3 ip342 + wait ip363).
    17: **194** (e17 ip769 Sync). 18: **195** (e3 ip377 + wait ip398).
  - 19: KEYON pair **196** (e3 ip426) + **197** (e17 ip793, WindowSync [INCS]); **KEYON e3 ip475**.
  - **20 -- THE NAMING**: e3 ip565 `Map.Byte[26]:=2`; **198** (Brahne, e3 ip576 WindowAsync, ip582 `op_22(10)`, ip585
    TimedTurn, **ip590 WaitWindow(0)**: a page); **ip593 `SetCharacterData(3,0,3,5,3)`**; ip600 `op_22(5)`; **ip603
    `Menu(1,3)`** (Steiner's naming screen); ip607 `op_22(10)`; **ip610 `Global.Byte[6] |= 8`** (L426); ip618
    `op_22(10)`; the Map.Byte[26] rendezvous with e12's two walks (e12 t1 ip717/727); ip668 Bit231.
  - 21: KEYON pair **199** (e3 ip693) + **200** (Steiner, e12 ip803 WindowSync [INCS]); **KEYON e3 ip742**; then **201**
    (e3 ip771 WindowSync, a page).
  - 22: KEYON pair **203** (e12 ip886) + **202** (e17 ip862 WindowSync [INCS]); **KEYON e12 ip935**.
  - 23 (the exit, e2 t1 L724): **ip735 `Byte[8]:=0`**, ip789 `Map.Bit[158]:=0`, ip808 DisableMove, ip830
    PreloadField(5,153), ip882 `op_22(65)`, **ip932 `Int16[2]:=328`**, **ip940 `Field(153)`** (F: Field(31245)).
  Total: 17 pages (177-181, 184-187, 190-195, 198, 201), 5 KEYON pairs (10 windows), 2 timed (175, 176) = 175..203.
- 151's 21 store sites (`grep '<<' L151.txt`): route e0 t0 ip22/49/57/119/138/200/315, e3 t1 ip610, e2 t1 ip735/932;
  error ip97/178/960/994; dead ip41, ip130, ip211; other entrance ip410 (L340); off e3 t3 ip909 `Bit[3793]` (Brahne's
  talk: she is the player at 110, no control), e8 t2 ip38/ip237 (InitRegion(8) only on the default L340). No
  Battle/SetRandomBattles/Cinematic/ATE/VIB/hot-spot (`Int16[220]/[222]`) and no SYSVAR[0] read.

## 153 A. Castle/Hallway (EVT_ALEX1_AC_H2F; fbg_n02_alxc_map041a_ac_h2f_1) -- visit 2, entrance 328: the Knights of Pluto
- Main_Init e0 t0: prologue (all six same-value from 151's); ip232 `SC>1900` false (ip243 skipped); ip251/255
  `SWITCHEX(L1098, 325,L273, 5,L438, 328,L603, 316,L799, 3,L951)` -> **328 -> L603**: ip609 `Map.Byte[24]:=40`,
  InitObject 32 (Steiner), 16 (Blutzen), 17 (Kohel), **InitRegion 23, 24, 25** (ip626-632), InitCode 21 (camera code),
  InitObject 13, 14 (two soldiers on the UPPER corridor), `RunSoundCode(1792,137)` + the SYSVAR[3] wait, ip667
  `Map.Bit[167]:=0`, SetFieldCamera(1), ip678 `SetControlDirection(248,0)`, SPS, **ip802 `JMP(L1288)`** -- past the
  default branch L1098. **No Byte[8] store at 328 in Main_Init**: ip1188/ip1260 sit in L1098 behind an inner
  `SWITCH(327, L1285, L1213, L1141)` (ip1137) whose case 328 is dead because SWITCHEX already took 328 (dispute 2).
  Tail: ip2356 `Map.Bit[159]:=1`; ip2364 `Map.Bit[158]==1` false (e32 t0 case 328 sets none) -> Main_Init's EnableMove
  ip2405 is skipped.
- Steiner = e32: e32 t0 ip22 `SWITCH(324, L383, L140, L383, L383, L59, L24, L221, L302)` -> **328 -> L24**: Map.Int16
  x -24 / z -2078 / facing 128 / y 64037 (= -1499, the upper corridor), no `Map.Bit[158]`; ip482 `SetModel(5489,104)`
  GEO_MAIN_F0_STN, ip487 CreateObject(-24,-2078), **ip520 `SetObjectLogicalSize(30,35,50)`** (controller radius = 30 x
  4 = **120**, collRad 35: DoEventCode.cs:1498-1534), ip535 MoveInstantXZY, ip548 SetPathing(1), ip551
  SetObjectFlags(7), **ip717 `DefinePlayerCharacter`**, **ip718 `Bit[3855]:=1`** (L700), **ip727 `Bit[3854]:=1`**
  (L709) -- every time e32 t0 runs, so once in O6.
- Conductor e2 t1: 40 -> 41 -> ... -> 48 -> 0 (`stagemap153.out`). Per stage (`stages153_328.out`):
  - 40 (e32 t1 L40): ip778 `Walk(-24,-74)`; **211** (WindowAsync ip798 + WaitWindow ip809); **212** (WindowAsync ip815 ...
    **ip866 `RunSharedScript(15)`** ... WaitWindow ip870); waits 5+5+1+15+10+15 ticks; **213** (ip901 + ip922);
    **214** (ip925 + ip946). All pages.
  - THE SHARED SCRIPT: entry 15 (one function, tag 0 at ip6): `op_22(45)`, `RunSoundCode(0,137)`, wait SYSVAR[3]==0,
    **ip32 `Byte[8]:=125`** (L26; raw 0 -> 125), ip40 RunSoundCode1(16897,137,Byte[8]), `Map.Bit[167]:=0`, op_1C(255),
    RET. STARTSEQ (DoEventCode.cs:1414-1421) makes `new Seq(entry 15, uid = 32 + cSeqOfs 64)`; Obj.cs:47-58 sets
    sid 15, uid 96, ebData = entry 15's, ip from GetIP(15,0), currentByte = ebData; EBin.ProcessCode runs it with
    objV0 = the caller (cid 1, EBin.cs:164). So the s88 row reads **sid 15, uid 96, tag 0, ip 32, add 0** (StoryTrace.cs:354-371:
    sid/uid = EBin.s1's, add 0 since currentByte == ebData, tag = TagAt(entry 15, 32) = 0). Precedent: O1e's trace
    holds field 50 sid 16 uid 79 tag 0 ip 49 `Byte[8]` (a Seq row) and its JOIN passed.
  - 41: **215** (Blutzen, e16 ip157 WindowSync); e16/e17 `SetObjectFlags(7)` (e16 ip144, e17 ip130). 42: **216**
    (Kohel, e17 ip201 WindowSync).
  - 43: **217** (e32 ip960 + WaitWindow ip1027) with the one-pass loop ip971 `Byte[208]:=0` (raw 0 -> 0, same) / ip1006
    `++` (0 -> 1); **218** (ip1030 + WaitWindow ip1138) with ip1041 `:=0` (1 -> 0) / ip1076 `++` (0 -> 1).
    Each loop is `:=0; while (Byte208 < 1) {...; ++}`: one pass.
  - 44: SetWalkSpeed(60) ip1160; Walk(-150,-550) ip1176, (-1235,-558) ip1183, (-1595,-195) ip1190, (-1370,804) ip1197:
    DOWN the curved west stair.
  - 45: `Map.Byte[26]:=3`, ReleaseCamera, SetFieldCamera(0), `SetControlDirection(248,0)` ip1232, **Walk(-575,807) ip1360,
    Walk(-245,42) ip1367**, turns toward e17 and e16, TimedTurn(240); the Map.Byte[26]/Map.Bit[230] rendezvous with the
    knights (e16: CreateObject(589,-261), walks (-89,-151), (-524,-540); e17: CreateObject(664,409), walks (107,107),
    (256,-350)).
  - 46: **219** (ip1469 + WaitWindow ip1490). 47: **221** (ip1551 + WaitWindow ip1572). (Text 220 is never shown.)
  - 48 (L849): **222** (ip1586 + WaitWindow ip1653) with ip1597 `Byte[208]:=0` (1 -> 0) / ip1632 `++` (0 -> 1); then the
    REBUILD, no input: **ip1656 `UInt16[21]:=8`** (0 -> 8), ip1664 SetPartyReserve, RemoveParty 0..11 (ip1669-1702),
    PARTYADD(3) ip1705 (+ three PARTYADD(65535)); **ip1741 `Byte[303]:=0`** (0 -> 0, same), **ip1775 `++`** (0 -> 1;
    ip1797/1819/1841 sit behind `const(0)` tests: dead); CURHP / SetHP / CureStatus; ip2152 `PARTYCHK(5)` false (the
    party is [Steiner]) -> **ip2172 `Byte[4]:=0`** (same; ip2161 dead); ip2180 `(UInt16[19]>>3)&1 == 0` true ->
    ip2199 `SetCharacterData(3,1,3,5,3)`, **ip2206 `UInt16[19] |= 8`** (L1469; raw 0 -> 8), SetRow(3,1); SetHP/SetMP;
    **ip2232 `Byte[4]:=0`** (same), **ip2240 `Byte[17]:=0`** (same), **ip2248 `Byte[18]:=1`** (0 -> 1); HP/MP/cure all;
    **ip2382 `Map.Bit[158]:=1`**, ip2390 `Map.Bit[159]==1` (Main_Init ip2356), ip2401 `Map.Bit[156]==0`, **ip2412
    `EnableMove` = STEINER'S FIRST CONTROL**, ip2413 SetTriangleFlagMask(255), ip2427 EnableMenu, ip2428 Bit231 ->
    conductor 48 -> 0; e32 t1 then idles (stage 0 -> L1702). The knights' stage 48: e16 SetWalkSpeed(55), e17 op_22(10)
    + SetWalkSpeed(40); both walk (1200,64), (2000,64), (2800,64), then `SetObjectFlags(14)` ip389 and `op_1C(255)`
    ip399 (gone).
  - 11 pages in all (211-219, 221, 222); no KEYON pair, no timed window, no choice.
- Regions instanced at 328 (decoded SetRegion z<<16|x): **e23** (-227,3000)(200,3000)(212,935)(-264,924); **e24**
  (2850,347)(2850,-13)(1739,-74)(1739,406); **e25** (-777,-2348)(777,-2348)(777,-900)(-777,-900). Each tag 2 starts with
  `SYSVAR[2]` (control) and RETs without it.
  - **e23 t2**: ip38 `obj(250).f[1] > -100 && obj(250).f[2] > 1333` (on the ground AND z > 1333) -> ip58
    CalculateExitPosition, ip59 ExitField, ip79 DisableMove, ip101 PreloadField(5,154), ip143 FadeFilter, ip153
    `op_22(25)`, **ip203 `Int16[2]:=315`** (L173), **ip211 `Field(154)`** (F: 31246). Not facing-gated.
  - e24 t2: unconditional -> ip183 `Int16[2]:=315`, ip191 `Field(150)` (F: 31243).
  - e25 t2: ip38 ground -> ip195 `Int16[2]:=315`, ip203 `Field(64)` (F: 31240); else ip210 `z < -1400` -> ip222
    `Byte[8]:=0`, ip421 `Int16[2]:=315`, ip429 `Field(151)` (F: 31244).
  - e26/e27/e28 are NOT instanced at 328 (InitRegion only at 325, Main_Init ip302-308).
- 153's store sites live at 328: route e0 t0 ip22/49/57/119/138/200, e32 t0 ip718/727, e15 t0 ip32, e32 t1 ip971/1006/
  1041/1076/1597/1632/1656/1741/1775/2172/2206/2232/2240/2248, e23 t2 ip203; dead ip1797/1819/1841 (const 0), ip2161
  (PARTYCHK false), e0 t0 ip41/130/211/243 and ip1188/ip1260 (other entrances); error ip97/178/2314/2348; forbidden
  (walk) e24 t2 ip183, e25 t2 ip195/222/421. Not instanced at 328: e3, e7, e18, e20, e28, e31 (every other store).
  No Battle/Cinematic/ATE/hot-spot/SYSVAR[0]; the VIB ops (e3 t1 ip2443-2453) are 325-only.

## END: arrival in 154 at 315 (visit 3)
Cut at 154's first row, **e0 t0 ip26 `Bit[191]:=0`** (L16; S: real 154, F: member(154) 31246), right after 153's chain
row e23 t2 ip203 `Int16[2]:=315`. 154's Main_Init at 315: prologue (ip26..ip204, all same-value), ip230/234
`SWITCH(304, L392, L232)` -> default **L392**: `Map.Byte[24]:=0`, InitObject 15 (Steiner), 5 (Dojebon), 6, 7 (soldiers),
InitRegion 9, 10, 8, InitCode 11; **no `Byte[8]` store at 315** (ip279 is the 304 branch's). The end is clean: nothing
written after the cut can move an end-state key (all of 154's prologue is same-value). Steiner's control in 154 (Main_Init
ip588, dispute 4) comes after the end.

## SC ladder -- no rung inside O6
| value | where | when |
|---|---|---|
| 1190 | the warp's residue in field 70 (byte 0: 0 -> 166, byte 1: 0 -> 4; Ff9mkDebugMenu.cs:2135) | the start; a true run carries it from 150 e3 t1 ip1966 (O4's rung) |
| (1400) | 55 e10 t1 ip582 (L474) | past the end (O7+): ip500 `SC > 1400` false -> ip582; ip568 is the debug twin. Then 1410 at 54 e4 t1 ip458 |
**No store to SC's bytes in any width in 151, 153 or 154 -- nor anywhere in 151-166** (census of the listings: zero
`('global', 7, 0)` sites); the only reads are 151 e0 t0 ip461 `<12000` and 153 e0 t0 ip232 `>1900`. O6's LADDER is
"no rung": SC 1190 at the start (residue) and at the end.

## FieldEntrance chain
110 (the warp's residue: byte 2 0 -> 110; 110 = 0x006E, so byte 3 stays 0) -> 328 (151 e2 t1 ip932) -> 315 (153 e23 t2
ip203).

## Expected story keys, in order (S side; F identical in donor terms; raw start)
| visit | field | sid tag | ip (L) | key (old -> new) |
|---|---|---|---|---|
| 0 | 70 | residue | | SC bytes 0 (0->166), 1 (0->4); FieldEntrance byte 2 (0->110): exactly **3** rows, set aside by the front cut |
| 1 | 151 | e0 t0 | 22 (16), 49 (43) | Bit191:=0, Bit184:=0 (masked, same) -- ip22 is the START row |
| 1 | 151 | e0 t0 | 57 (51), 119 (113), 138 (132), 200 (194) | Int16[9] 643->-1, Byte13 1->0, Int16[11] -1 (same), Byte14 0 (same) |
| 1 | 151 | e0 t0 | 315 (309) | Byte8 125->125 (same) |
| 1 | 151 | e3 t1 | **610 (426)** | **Byte6 \|= 8: 0->8** (START-DEPENDENT: 3->11 after a true O1-O5 run) |
| 1 | 151 | e2 t1 | 735 (724), 932 (921) | Byte8 125->0; Int16[2] 110->328 (chain) |
| 2 | 153 | e0 t0 | 22, 49 / 57, 119, 138, 200 | masked / the four ambient keys, all same-value -- EMITTED (each site's first in the epoch) |
| 2 | 153 | e32 t0 | 718 (700), 727 (709) | Bit3855 0->1, Bit3854 0->1 |
| 2 | 153 | **e15 t0** (Seq, uid 96) | **32 (26)** | Byte8 0->125 |
| 2 | 153 | e32 t1 | 971 (234), 1006 (269), 1041 (304), 1076 (339) | Byte208 0->0 (same), 0->1, 1->0, 0->1 |
| 2 | 153 | e32 t1 | 1597 (860), 1632 (895) | Byte208 1->0, 0->1 |
| 2 | 153 | e32 t1 | 1656 (919) | UInt16[21] 0->8 |
| 2 | 153 | e32 t1 | 1741 (1004), 1775 (1038) | Byte303 0->0 (same), 0->1 |
| 2 | 153 | e32 t1 | 2172 (1435) | Byte4 0->0 (same) |
| 2 | 153 | e32 t1 | **2206 (1469)** | **UInt16[19] \|= 8: 0->8** (START-DEPENDENT: 1799->1807 after a true run) |
| 2 | 153 | e32 t1 | 2232 (1495), 2240 (1503), 2248 (1511) | Byte4 0 (same), Byte17 0 (same), Byte18 0->1 |
| 2 | 153 | e23 t2 | 203 (173) | Int16[2] 328->315 (chain) |
| 3 | 154 | e0 t0 | 26 (16) | the cut (Bit191, same, emitted: a new site) |
**34 store rows a run before the cut (4 masked + 28 writes + the 2-key chain), every one at its own site** -- no site is
written twice, so the s88 sink suppresses nothing and no end-of-epoch `c` row arises (StoryTrace.cs:376-399, the site
key includes the field; ChangeRowsPerSite 64). Row ORDER is deterministic in practice: e15's ip32 needs `op_22(45)` + a sound sync after ip866 and lands while pages
212-214 are up, at least 51 ticks of `op_22` and four pages before stage 43's ip971.
Forbidden (diagnostic): 153 e24 t2 ip183, e25 t2 ip195/ip222/ip421 (cause walk); every error-path and dead site above;
151 e3 t3 ip909, e8 t2 ip38/ip237; any row of 153 e3/e7/e18/e20/e28/e31.
Not gEventGlobal: Steiner's name (PLAYER.Name), SetCharacterData, party membership, SetRow/HP/MP, Map vars, the camera.

**End state at the arrival in 154@315 (raw start):** SC 1190; Int16[2] 315; Byte[6] 8; Byte[8] 125; Bit[3855] 1;
Bit[3854] 1; Byte[208] 1; UInt16[21] 8; Byte[303] 1; Byte[4] 0; UInt16[19] 8; Byte[17] 0; Byte[18] 1; Byte[13] 0;
Byte[14] 0; Int16[9] -1; Int16[11] -1; Bit[191] 0; Bit[184] 0. Untouched (New Game values): Bit[3795] 0, Bit[3793] 0,
Byte[475] 0, Bit[3815] 0, Bit[3717] 0, Bit[3718] 0, Int16[469] 0, Byte[472] 0, Byte[206] 0, Bit[3796] 0, Bit[3811] 0.
Nothing in 154@315 races the live read (its Main_Init stores are all same-value), but read Byte[8] and the rebuild keys
from the trace's last pre-cut writes as O5 did.

## Choices
None: no `[CHOO]`/PCHC window is opened on the route (153's choice 128 is 325-only). Keep O1's `{None, "want to skip",
"default"}` guard rule (no movie on the route can raise it).

## The naming
Steiner's naming, once: 151 stage 20 (e3 t1 L381..L484).
- **Sequence**: page **198** (WindowAsync ip576, `op_22(10)`, TimedTurn, **WaitWindow(0) ip590**: closed by a Confirm,
  rule 7) -> **ip593 `SetCharacterData(3,0,3,5,3)`** -> `op_22(5)` -> **ip603 `Menu(1,3)`** -> `op_22(10)` -> **ip610
  `Byte[6] |= 8`** -> `op_22(10)` -> the rendezvous with e12 -> stage 21 (KEYON pair 199/200, page 201).
- **The screen opens**: MENU (DoEventCode.cs:2317-2341) skips the screen only under `Configuration.Hacks.DisableNameChoice`;
  the live Memoria.ini has `DisableNameChoice = 0` (line 256, [Hacks] Enabled), so `EventService.StartMenu(1, 3)` opens
  NameSettingUI for CharacterId 3. `InitID(3)`: id < 12, so `SetData` pre-fills `FF9TextTool.CharacterDefaultName`
  (NameSettingUI.cs:137-151); the box opens focused.
- **What the driver does**: the published `ui_state` becomes "NameSetting" (no dialog) -> **rule 4** (segment_drive.py:3068-3080)
  answers a registered `{donor 151, sc 1190, beat "named"}` with **`g.accept_name()`** (session.py:7134-7156): up to 4
  Confirms, each waiting <= 2 s for `ui_state` to leave NameSetting. Confirm 1 removes the box's focus, Confirm 2 is OK:
  `SetCharacterName` -> `PLAYER.Name = "Steiner"` -> FieldHUD (NameSettingUI.cs OnKeyConfirm, :173-177). Never Cancel
  (it refocuses the box), never Menu (it resets the name). An in-flight rule-7 Confirm that lands on the screen only does
  Confirm 1's job; the outcome is the same default name.
- **How both sides end equal**: the name lives in PLAYER.Name (save data), not gEventGlobal -- the trace cannot see it and
  both sides store the same default by construction. The only story store beside it, ip610 `Byte[6] |= 8`, runs
  whatever the name (8 on both sides from the raw start). Menu(1,3) carries no field key (StartMenu is keyed by the
  character; the gates reader's IL check: no EffectiveFieldId), so S and F open the same screen.
- **Freeze**: P-SETTINGS `DisableNameChoice = 0` (O5's settings already pin it). Checks: one `named` row per run, in 151,
  between page 198 and the ip610 row.
- **Recovery (GAP)**: a run that stops with the screen up cannot warp (Ff9mkDebugMenu.cs:2083: FieldHUD only), and the
  soft reset is swallowed outside FieldHUD/WorldHUD/BattleHUD (UIKeyTrigger.cs:94). `end_run` then calls `accept_name` and
  `restore_baseline` WITHOUT retrying the warp (segment_trace.py:581-585), while 151's scene still plays (O1: a soft reset
  through a running scene failed). Smallest fix: retry `g.warp(recovery)` after `accept_name` (log
  `recover-warp-after-naming`), a FakeGame test that fails without it, and an R-NAMING-VOID rehearsal.

## Battles, minigames, FMV
None on the route: no Battle/SetRandomBattles/AICON/ATE/Cinematic op in 151, in 153's entries live at 328, or in 154's
arrival (opcode census). Battle registry empty (any battle V10); no movie policy. No minigame: the 5 `[INCS][TIME=-1]`
KEYON pairs are rule 7's (repeat Confirm until both windows close): 151 e4 t1 ip516, ip693; e3 t1 ip475, ip742; e12 t1
ip935. FMV004 lies past the end (O7).

## Nondeterminism
1. START-DEPENDENT values, the same on S and F, neither the true game's: 151 e3 t1 ip610 `Byte[6] |= 8` (8 raw vs 11
   true) and 153 e32 t1 ip2206 `UInt16[19] |= 8` (8 raw vs 1807 true; its guard ip2180 tests bit 3, clear in both:
   1799 = bits 0,1,2,8,9,10). OLD/SAME only (value equal): 151 ip57/ip119/ip315, 153 e32 t1 ip1656/ip1741/ip2248.
   EMITTED PATTERN: 153@328's and 154's prologue rows are emitted here; in a single-epoch true chain O4/O5 already used
   those sites and they would be suppressed `c` counts (lesson 14). Freeze every pattern from THIS start.
2. Timing only: the [TIME=20] windows 175/176, the KEYON gates (<= 250 ticks), [SPED] type-outs, scripted walks (Beatrix
   in 151 stage 13; Steiner and the knights in 153 stages 44-45 and 48), fades, e15's sound sync.
3. Positions: the grant at (-245,42) is the bytes' (stage 45's last Walk; the knights' rendezvous does not move him:
   their flags carry bit 2, walk-through) -- rehearse (lesson 6). The loss sample sits just past z 1333 inside e23.
4. No SYSVAR[0] read in 151, 153 or 154; no battle, ATE or choice. No revisit: every site once.

## The walks
**One control grant up to the end.** 151@110 (Brahne e3 defined, no `Map.Bit[158]`) and 154@315 (the end, reached
before any control) have none for the driver.

### CONTROL 1 -- 153 (S) / 31245 (F), entrance 328, SC 1190, visit 2, cell (153, 1190[, visit 2]), step 0
- **Character**: Steiner, e32 (GEO_MAIN_F0_STN 5489; DefinePlayerCharacter e32 t0 ip717). Controller radius **120**
  (`SetObjectLogicalSize(30,35,50)` ip520, x4: DoEventCode.cs:1498-1534; no special case for 153), collRad 35. Runs
  60 u/tick on the flat (two MovePC calls at speed 30: FieldMapActorController.cs:107, :198-209), times |n.up| under
  PSXMovementMethod = 1 (Memoria.ini:125); the hall floor is flat.
- **Grant**: e32 t1 stage 48, **EnableMove ip2412** after page 222 (WaitWindow ip1653), the rebuild and `Map.Bit[158]:=1`
  ip2382 (gates `Map.Bit[159]==1` ip2390, `Map.Bit[156]==0` ip2401). No window is up at the grant (lesson 3 does not
  apply). Main_Init's own EnableMove (ip2405) never runs at 328.
- **Spawn (the bytes; REHEARSE, lesson 6)**: **(-245, 42)** -- stage 45's Walk(-245,42) ip1367 after stage 44's stair
  descent -- ground tri 114 (floor 3, PSX -1, published y ~1); the upper tri 42 (PSX -1499) lies over it.
- **Goal = e23 on the ground with z > 1333**: e23 t2 ip38 `f[1] > -100 && f[2] > 1333` (the quad spans z 924..3000, so
  it fires only past z 1333) -> ExitField ip59 (control goes) -> ... `op_22(25)` -> ip203 `Int16[2]:=315` -> ip211
  `Field(154)` (F: 31246). Lesson 4 holds: control goes ~26 ticks before Field(). No facing gate.
- **Path** (PlayerWalkmesh(stock 153, closed_tris = the 33 upper floor-0 tris, O5's list -- verified equal to every
  floor-0 tri above y -1000), `route_avoiding` as the harness calls it: margin 56, leave_wall, avoid e24/e25):
  **(-245,42) -> (19,1620) STRAIGHT, 1600 u**, min wall 113 at the planner's 80; at Steiner's 120 via (-53,1130), min
  wall 123; PSX y -1 the whole way; e23's condition first holds at ~(-29,1335). From every start within +-25 u of the
  grant the plan is the same straight leg, 1571-1629 u, >= 917 u from e24/e25, e23 firing at ~(-24..-34, 1334..1336)
  (`goals153.out`). ~27 ticks (0.9 s) of running. On the PLAIN mesh there is no route (the upper corridor's tris come
  first under `point_on_walkmesh`, as in O5).
- **The step**: `{kind: "trigger", name: "the north door", goal: [19, 1620], until: {"z_gt": 1200}, avoid:
  ["153.e24", "153.e25"], closed_tris: [0,1,2,3,4,5,6,7,8,9,11,14,15,16,17,18,19,20,21,23,24,28,32,33,34,35,38,39,41,
  42,43,45,46], npcs: false, start: [-245, 42], beat: "steiner_door"}` (attempts/interrupts/timeout as O5's defaults).
  Why each key:
  - **trigger, not cross**: x_cross passes the quad as `zone` (segment_drive.py:2433-2437); under `smooth` route_to's
    leg returns "arrived" on the first sample INSIDE the zone (session.py:3368-3369), ~z 930, where e23 cannot fire;
    route_cross then waits with control held and the step is "failed" (dispute 3). A trigger with an `until` and no
    `target` walks to the goal with no zone (segment_drive.py:2476-2478).
  - **until {z_gt: 1200}**: x_trigger is done when the loss sample satisfies it and the walk has not landed elsewhere
    (segment_drive.py:2485). With `handoff=True` (walk_kw, segment_drive.py:2314) route_to returns AT ONCE when control
    goes (session.py:4150-4155),
    so the loss sample is taken in the ~26-tick fade, before Field(154); every e23 loss is at z > 1333, and the other
    control-takers at 328 never reach z 1200 (e24 max z 406, e25 max z -900). The 133-u margin under the engine's own
    1333 covers a sample a tick stale. A loss at e24/e25 fails the evidence and goes to the landing judge (V11).
  - **npcs false**: the harness's level filter keeps an actor standing on ANY floor under it (session.py:4981-5008), so
    the two soldiers e13 (158,1102) / e14 (-226,1086) on the upper corridor (PSX -1499) become 220-u discs over the
    ground approach; the engine never pairs them (|dy| >= 400, WalkMesh.cs:922). The knights carry flags 7 then 14 --
    bit 2 set, so the player is never paired with them (WalkMesh.cs:915-917). No actor at 328 has a Range (tag 2) and
    talk needs a Confirm, which the driver never presses with control held. Nothing is lost by planning without them.
  - closed_tris: O5's exact fix for this mesh; floor 1 (0xa001) is already player-closed.
- **Hazards and how the driver avoids them**:
  - **e25** (942 u south of the grant): on the ground -> Field(64)@315 (F: 31240) -- the play's field; upstairs with
    z < -1400 -> Byte[8]:=0 and Field(151)@315. In `avoid`; register role `exit`.
  - **e24** (1897 u east): -> Field(150)@315 (F: 31243). In `avoid`; role `exit`.
  - **Calibration**: route_to calibrates clear of `avoid` with the key prior (probes <= ~240 u): nothing within reach.
    One basis for the whole field: every `SetControlDirection` in 153 is (248,0), and movement rotates by twist.y =
    (arg2 + 1)/256*360 (FieldState.cs:11-17; FieldMapActorController.cs:712-721; UseAbsoluteOrientation = 3, WO for
    keys/D-pad, Memoria.ini:139). The camera code e21 (camera 1 at x > 500 or PSX y < -250) is visual; the walk stays at
    camera 0.
  - The knights walk east from (-524,-540) / (256,-350) to (2800,64) as the grant comes: their lines pass >= 480 u south
    and east of his northward leg, and they are walk-through.
  - SETCAM #493 (153's SC-1190 camera exception) is effMapNo-wrapped and camera-only; PSXCameraAspect's raw
    RestrictedCams [153,0,320] letterbox differs between S and F (visual only: never compare 153 camera-0 screenshots).
- **Regions to register for place 153 at 328**: `153.e23` role `exit` (to 154, entrance 315, face_gate None; note:
  fires only on the ground with z > 1333); `153.e24` role `exit` (to 150, entrance 315); `153.e25` role `exit` (to 64,
  entrance 315, ground; its upstairs branch to 151 is unreachable after the grant); `153.e26/e27/e28` role `dormant` at
  328 (instanced only at 325). 151: `151.e8` dormant at 110. 154 (the end): e8/e9/e10 are instanced at 315 (exits for O7:
  e8 ground -> 158@300 / balcony -> 153@301; e9 ground -> 155@300 / balcony -> 156@302; e10 ground -> 167@300 / balcony
  -> 156@303); the run ends before any control there.
- **THE PAIRED-WALK LAW**: nothing stores between the grant (ip2412) and the loss: e32 t1 idles, the knights and soldiers
  store nothing, e15 finished in stage 40, Main_Init is done; the next row is the exit's own chain row ip203, after the
  loss. The walk's path cannot change a key.
- **Numbers to rehearse (R-DOOR, stock, x2)**: the grant position (expect (-245,42)); the calibration probes; the loss
  sample (expect x -40..+20, z 1333-1450, published y ~1); ticks grant -> loss; the knights' samples during the walk;
  whether e13/e14 are published (coll, shown).

### No other control up to the end
151@110 (Brahne e3 the defined player; Map.Bit[158] never set) and 154@315 (the end: rule 1 fires on its first poll).
A control sample in 151 is V4 (game).

### Beyond the end -- O7's walks (survey; settled here only where marked)
- **154@315** (Steiner e15, radius 120): spawn (-58,-3758), MoveInstantXZY y -1741 -> balcony tri 250 (PSX -1716) over
  ground tri 132. **Grant = Main_Init e0 t0 ip588** (settled, dispute 4). Exit e8 t2: `f[1] < -100` -> 153@301 (the
  balcony branch, 322 u south of the spawn); else ip355 `Int16[2]:=300`, ip363 `Field(158)`. **The way down (settled,
  dispute 5)**: by the engine's own triangle links the balcony meets the stairs only at tris (289,292) west and (189,190)
  east, and the stairs meet the ground only at x -477..482, z -245..-125; spawn tri 250 reaches e8's ground tri 131 west
  along the balcony, down the west flight (292 -> 289 -> ... -> 232) to ground tri 173 (-157,-87), then south. Two legs
  with complementary closures (the walks reader's leg A to (0,-400), 7505 u; leg B to (0,-4500), 4100 u): needs a
  waypoint step kind. Dojebon e5 waits while the player is within 3600 or `Map.Byte[30]==1` (survey).
- 158 (ip379), 159 (ip665; the forced monologue e16 t1 ip390 `Bit[3796]==0 && (x < -1600 || x > 1600 || z < 800)`:
  pages 296-300, Byte[208] ip613/648, `Bit[3796]:=1` ip672, EnableMove ip711 in place: `interrupts: 1`), 160 (ip399; back
  door e4 61 u east of the spawn), 162 (ip866; e2 50 u south), 163 (ip618; the stair foot is narrower than radius 120 --
  survey), 164 (ip698; radius 80 by DoEventCode.cs:1507-1508, effMapNo-wrapped; self-overlapping spiral; exit e2 at
  `f[1] < -12000`; e3 live at the spawn; the narrow turn plans only at clearance <= 64 -- survey; the knight e1 t1 ip178
  walks once PSX y <= -8400, then 4 legs at speed 15 + RunAnimation(9920) before ip230 `Bit[3811]:=1`: a RACE with the
  exit, settled as timing-only (dispute 9)), 165 (ip778; exit e2 at `f[1] < -15000` writes ip205 `Byte[13]:=3`; e3 live
  at the spawn), 166 (no control; FMV004 = `MBG_DEF("FMV004", 1, 0)`: type 0, skippable -- settled, dispute 7; 45.41 s
  live; no page after it; raw Field(55) on both sides).
- All Main_Init-tail grants (settled, dispute 4): 154 ip588, 158 ip379, 159 ip665, 160 ip399, 162 ip866, 163 ip618, 164
  ip698, 165 ip778. The door stores `Byte[13]:=3` are live only at 158 e2 ip194 and 165 e2 ip205 (dispute 8).

## The start
**Recommended: (a) the raw warp, O2-O5's mechanism.** New Game, `storytrace 1`, then in field 70 (UIState FieldHUD,
before 70 e0 t0 ip475) `warp 151 110 1190` (S) / `warp 31244 110 1190` (F): HarnessAgent -> Ff9mkDebugMenu.HarnessWarp
(:474, `Warp(mapNo, false)`: no flag reset) -> FieldEntrance set at :2130 and SC at :2135 before SetNextMap; refused
outside FieldHUD (:2083). O5's F-SMOKE loaded 31244@110.
- **Residue: THREE rows** `[[0,0,166],[1,0,4],[2,0,110]]` (O2-O4's count; O5 had four because 325 = 0x0145).
- Front cut at 151's first `w` row, e0 t0 ip22. **START requires ip119** (Byte13 old 1 -> 0), never ip97 / window 56
  ("Env Play()", the stop page).
- Carry O5's preflight set unchanged: P-MANIFEST, P-DEPLOY, P-EB (the route_build pins for 151/153/154 are O5's,
  reusable verbatim), P-FLOOR (31245), P-STOCK, P-TEXT (block 3, per language), P-RECOVERY, P-DONOR (151/153/154),
  P-SETTINGS (+ DisableNameChoice 0), P-PAD, **P-OVERRIDE** (the New-Game override in FF9CustomMap-world is the pinned
  one: the warp window and the start state come from it), P-ENGINE (ba9762423da8f3d7); in game P-CAP, P-OBJECTS
  (31244@110, 31245@328, 31246@315), P-LANG, P-DONOR-LOG, P-LAUNCH, P-PAD.
- **What the route reads before it writes resolves the same branch from the raw warp and from a true O1-O5 run**: SC
  (151 ip461, 153 ip232: 1190 both); Int16[2] (the warp sets 110; every later dispatch reads the chain's value); the
  ambient words (151's prologue normalizes them; only `old` differs); Byte[8] (always written before its sound-op read:
  151 ip315/323, e2 t1 ip735/743, e15 t0 ip32/40); UInt16[21], Byte[303], Byte[208], Byte[4], Byte[17], Byte[18]
  (written first, or equal, in e32 t1); UInt16[19] bit 3 (clear in both); PARTYCHK(5) (read after the rebuild); Bit[3795]
  (no reader on the route: every reader sits behind `Int16[2]==3`, which 153 sets only at SC > 1900); Byte[475] (only
  Brahne's talk, unreachable at 110); Bit[3855]/[3854] (read only by 164's knight's talk, past the end).
- **START-DEPENDENT keys up to the end: TWO values.** Register in O2's 4.5 shape:
  `{donor 151, sid 3, tag 1, ip 610, off 426, m 1, src eb, op "|=", target "Global.Byte[6]", value 8, prior "newgame0",
  after_o5 11}` and `{donor 153, sid 32, tag 1, ip 2206, off 1469, m 1, src eb, op "|=", target "Global.UInt16[19]",
  value 8, prior "newgame0", after_o5 1807}`. (55 e8 t1 ip1354's start-dependent BRANCH lies past the end.)
- (b) Harness pokes in field 70 (`byte 6 3`, `byte 19 7`, `byte 20 7`, ...; HarnessAgent.cs:794-822) would make both
  values true, as `src: harness` rows or silently before `storytrace 1`: a new START contract, and still not the true
  emitted pattern. Only if the owner wants the stored VALUES true. (c) The story seed: F-only `[startup]` -- asymmetric,
  and no channel for Byte[6]/UInt16[19] values. (d) O5 as a prefix: doubles the run and re-exposes O5's walk and choice.
- **Party and names**: [Zidane] at the arrival in both starts (New Game vs 150's rebuild); nothing reads the party before
  153 e32 t1's rebuild, which makes both [Steiner] (SetPartyReserve(8) deletes the roster and adds the mask,
  DoEventCode.cs:2740-2752; RemoveParty runs at AllCharactersAvailable = 1, :2757; PARTYADD(3)). The controlled
  character is always script-defined (Brahne e3 at 110, Steiner e32 at 328, e15 at 315). Steiner joins at level 1 with
  full HP in both. Names: Zidane/Vivi defaults; Steiner's default via `accept_name` (above). Gil 500 raw, never read here.

## Disputes settled (reader claims vs the bytes / engine / walkmesh)
1. **The end.** Bytes: arrival in 154@315. Data: arrival in 55 through FMV004. SETTLED: 154@315 (the section above): the
   only end that needs nothing built, keeps every new interaction to existing machinery, and leaves the overlapping-level
   walks, the clearance key, the knight race, FMV004 and the seam to O7.
2. **153@328's Byte[8] stores.** Start-state: "153 e0 t0 ip1188 `:=125` (328 branch)". Data: "no Byte[8] store at 328"
   and no e15 row. Bytes: e15 t0 ip32 via RunSharedScript(15). SETTLED from the bytes: SWITCHEX ip255 sends 328 to L603,
   whose ip802 `JMP(L1288)` skips the default branch L1098; ip1188 is the case-328 arm of an inner `SWITCH(327, ...)`
   inside L1098 -- unreachable at 328. e15 t0 ip32 DOES run (e32 t1 ip866, stage 40) and its row is sid 15, uid 96,
   tag 0, ip 32 (DoEventCode.cs:1414-1421; Obj.cs:47-58; StoryTrace.cs:354-371; precedent O1e field 50 sid 16 uid 79).
   So Byte[8] is 0 -> 125 in 153@328 (and 159's ip290 `:=125`, O7's, is a same-value store).
3. **The 153@328 walk's step kind.** Bytes: one `cross` step. Walks/harness: `trigger` + `until {z_gt: 1333}`. Data: no
   kind. SETTLED from the code: a cross arrives at the zone's near edge (~z 930; session.py:3368-3369) where e23 cannot
   fire and ends "failed"; a trigger with `until` and no target walks to the goal and is done on the e23 loss
   (segment_drive.py:2465-2515). Threshold z_gt 1200 (a margin under the engine's 1333; no other control-taker reaches
   z 1200).
4. **The control grant in 154 (and 158-165).** Data: e15 t0 ip2100 (154), e6 t0 ip332 (158). Bytes/walks: the Main_Init
   tails. SETTLED from the engine: EBin.ProcessCode moves a new object from stateNew to stateInit and SKIPS it in that
   pass (EBin.cs:115-117); its tag 0 runs in a later pass, while Main_Init sits in `op_22` waits after its InitObject (154 ip465/ip468;
   158 ip256/259; ...). The player entry's tag 0 has no wait before its `Map.Bit[158]:=1` and finds `Map.Bit[159]` still
   0 (every Main_Init's L0), so its own EnableMove is skipped; Main_Init's tail sets Map.Bit[159] and grants: 154 ip588,
   158 ip379, 159 ip665, 160 ip399, 162 ip866, 163 ip618, 164 ip698, 165 ip778. Not a story store; past O6's end.
5. **154's way down.** Data: a side stair at the floor 0/1 seam (x -2943..-1815, z ~-1906), entering e8 at (-1202,-4823).
   Walks: the west flight to a central landing, then south. SETTLED on the engine's neighbour links (`wm154.out`): the
   balcony links to the stairs only at tris (289,292) and (189,190), the stairs to the ground only at x -477..482, z
   -245..-125; (-2400,-1906) holds two stacked, UNLINKED tris (2 at PSX -1716, 86 at -5). The walks reader is right.
6. **Re-calibrate after a camera switch?** Data: yes (153 e21, 154 e11). Harness: one basis per field. SETTLED: movement
   rotates by twist.y = (arg2+1)/256*360 (FieldState.cs:11-17, FieldMapActorController.cs:712-721; keys use WO at
   UseAbsoluteOrientation 3); 153 uses only (248,0), 154 (246,0) and (250,0) -- arg2 0 both: one basis per field.
7. **FMV004's type.** Gates: "type 1 (FMV)". Bytes/harness: type 0. SETTLED: MBG.cs:830 `MBG_DEF("FMV004", 1, 0)` is
   (name, isRGB24, type) by MBG_DEF.cs:5-10 -> type 0 -> MovieHitArea armed (MBG.cs:205-207): skippable. Past the end.
8. **The courtyard/tower doors' `Byte[13]:=3`.** Data: live at 160 e5 ip199, 162 e3 ip199, 163 e2 ip199, 164 e2 ip215.
   Bytes/walks: dead. SETTLED: those doors set `Map.Bit[162]:=1` (ip38 / ip54) before the `Map.Bit[162]==0` test (ip177
   / ip193) -> dead; live only 158 e2 ip194 and 165 e2 ip205 (no Map.Bit[162] write first). Past the end.
9. **164's knight vs the exit.** Data: "always before the exit". Walks/harness/bytes: a race. SETTLED: the TRIGGER (e1 t1
   ip178, PSX y <= -8400) always precedes the exit (y < -12000), but the WRITE (ip230) follows 4 walks at
   SetWalkSpeed(15) and RunAnimation(9920)+WaitAnimation: timing-only against Field(165). Past the end (O7: a hold).
10. **Event names.** Bytes: 151 EVT_ALEX1_AC_RST, 154 EVT_ALEX1_AC_FTI. SETTLED: `_fieldtable.py:739/742` -- 151 =
    EVT_ALEX1_AC_SEAT_R, 154 = EVT_ALEX1_AC_ENT_2F; RST/FTI are the FBG names (the members are named after them).
11. **npcs on the 153 walk.** Bytes: unspecified (default true). Walks: false. Harness: false, or a new `npc_floor` key.
    SETTLED: false (session.py:4981-5008 keeps the upper soldiers; WalkMesh.cs:915-922 pairs neither them nor the
    knights; no Range anywhere at 328). No new key.
12. **Run time.** Bytes 3.3 min, data 2.5 min to 154. SETTLED as an estimate on O5's measured rate: ~100-130 s; freeze
    from R-FULL.
13. (Correction of O5's survey, not O6-critical) "flags 5 = no player collision" is inverted: WalkMesh.cs:915-917 skips
    a pair only when the object carries bit 2; 5 = 1|4 collides. O5's walk never came near Blank.

## Harness gaps (summary; evidence in the structured result)
READY with configuration only: the raw-warp start (3 residue rows), Steiner as the controlled actor (nothing keyed by
identity), calibration (one basis), the 153 walk (`trigger` + `until` + `closed_tris` + `avoid` + `npcs: false`), the
trigger-into-a-door hand-off (route_to returns at the loss; the fade is ~26 ticks), the naming (rule 4 + accept_name),
pages / KEYON pairs / timed windows (rule 7; 151's scene never driven yet), the Seq row (JOIN resolves sid 15 tag 0 in
153's index; O1e precedent), the arrival end (rule 1, `side_ends` {S:[154], F:[31246]}, `end_row` 154 e0 t0 ip26), P-FLOOR
31245. GAP: recovery from the naming screen (retry the warp after `accept_name`). RISK: the run budget (estimates).
NOT NEEDED FOR O6 (O7's): a waypoint step kind, a per-step clearance, FakeGame per-field walkmeshes / height-gated
regions / a height-triggered walker, a movie span for a movie with no page after it, recovery mid-FMV004.

## Fork gates (summary)
Nothing on O6's route can change a story write between S and F: the members differ from their donors only in `Field()`
operands (7 languages); Menu(1,3) has no field key; the party ops have none; SETCAM #493 (153) is wrapped and
camera-only; s62's VIB ops are 325-only (not on this route); no battle/ATE/FMV/autosave row. Visual only and raw:
PSXCameraAspect's RestrictedCams letterbox on 153/154 camera 0. ForkDonorPatch has 31244/31245/31246 once each
(FF9CustomMap only). Re-run P-DONOR, P-EB, P-TEXT and P-ENGINE at session time -- the install is shared.

## Rehearsals before the freeze (proposed, O5's shape)
| stage | runs | settles |
|---|---|---|
| R-THRONE (stock 151 -> 153) | 2 | 151 driven for the first time: the pages, the 5 KEYON pairs, 175/176 inert under rule 7, the naming (ui_state NameSetting, two Confirms, the `named` row), the ip610 row (8), the arrival in 153@328 |
| R-DOOR = R-FULL (stock 151 -> 154) | 2 | the assembly pages, the e15 row's attribution (sid 15 uid 96 tag 0 ip 32 add 0), the rebuild rows, the grant position, the probes, the loss sample (z > 1333), the cut 154 e0 t0 ip26, the end state, run times (budget) |
| R-NAMING-VOID | 1 | after the end_run fix: stopped with the naming screen up -> the title |
| R-WALK-VOID | 1 | stopped mid-walk in 153@328 -> the title |
| F-SMOKE | 3 warps | 31244@110, 31245@328, 31246@315 load; object sids = their stock twins' (P-OBJECTS) |
| F-PASS (untraced) | 1 | one F run 31244 -> 31245 -> 31246, no throw, no V-class |

## Could not determine / unverified
The grant position and the loss sample in game (bytes only); 151's scene under the driver (never driven: O5 cut at its
first row); whether rule 7's Confirm is inert on 151's [TIME=20] windows (O4 measured 150's as inert); the naming
screen's publication for Steiner (proven for Zidane/Vivi only); the e15 Seq row's live attribution (source-read + O1e
precedent, not observed in 153); the run time (estimated); `end_run` from 151's naming screen (a known gap); whether
e13/e14 are published as colliding objects (irrelevant under `npcs: false`); every O7 fact marked "survey".
