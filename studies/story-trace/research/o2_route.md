# Stock O2 route: arrival in 100 (FieldEntrance 102, SC 1000) -> ... -> 116 Field(61)  (reconciled)

The reconciler's own decode, independent of the two readers' dumps. Every ip below was decoded from the stock US `.eb` by
`reconcile/ebtool.py` (storytrace.stock_script_source + ScriptIndex + instruction_stores), not copied from a reader.
- `ip` = abs - entry code start = the s88 trace ip (ScriptIndex.function_at convention). `Lnnn` = offset from the function start.
- Listings: `reconcile/L{100,101,102,103,104,105,106,115,116,61}.txt` (every instruction, `<<('global', vtype, index)` on each
  gEventGlobal store). `reconcile/win_route.txt` = every Window op with its decoded text. `reconcile/block33.json` = the text
  block (430 entries; identical for 100-117). `reconcile/regions.py` = SetRegion decode (arg = z<<16|x, int16 each);
  `reconcile/inquad.py` = point tests with the ENGINE's rule (IsInQuad: inside any triangle q[i],q[i+1],q[i+2],
  EventEngine.TreadQuad.cs:24-38); every "inside" claim below was tested that way. A region's tag 2 runs every frame the
  player has control inside it (EventEngine.ProcessEvents.cs:184-187 -> EventCollision.cs:300); tag 3 on Confirm|Special.
- `SWITCH(base, default, case_base, case_base+1, ...)`; `SWITCHEX(default, value, target, ...)`.
- Engine: live Memoria source C:\gd\FFIX\Memoria (deployed x64/x86 DLL sha1 46582b24 == Output\Assembly-CSharp.dll, no .cs newer).

## Segment end (both readers agree; verified)
**116 e2 t1 ip1702 `Field(61)`**, stage 13, after `Byte[8]:=0` ip1469, `Byte[13]:=3` ip1666, `Int16[2]:=0` ip1694.
61 = fbg_n00_tshp_map009_th_bst_0 (EVT_ALEX1_TS_STAGE_BK, zone tshp = O1's zone). A census of every `Field()` in the route
fields finds every other target inside alxt (100-117). The segment ends ON ARRIVAL in 61: FieldEntrance 0, SC 1155.
61's first trace row is `Bit[191]:=0` at 61 e0 t0 ip22 (its `Int16[2]:=10000` at ip41 is behind `Bit[184]==1`, never true
here). 61 then plays FMV003 (`Cinematic(0,8,1,1)` = MBGDiscTable[1][8], 61 e2 t1 ip159) - a real, skippable FMV, after the cut.
Earlier checkpoint: none is story-natural. If the run budget forces a split, 115's opening is SC-keyed (Main_Init ip231-287),
so "arrive in 115 with SC 1153" is a clean second start (O2a = 100..Field(115), O2b = 115..Field(61)).

## Ambient prologue (every field's e0 t0; same shape as O1) - the writes that FIRE on this route
`Bit[191]:=0`, `Bit[184]:=0`, `Int16[9]:=song`, `Byte[13]:=1` (incoming Byte[13] is 2 or 3), `Int16[11]:=song2`,
`Byte[14]:=1` (song2>=0) or `:=0` (song2=-1), tail `Byte[13]:=2` and (song2>=0 only) `Byte[14]:=2`. `Int16[2]:=10000` never fires.
| field | Bit191 | Bit184 | Int16[9] | Byte13:=1 | Int16[11] | Byte14 | tail B13:=2 | tail B14:=2 |
|---|---|---|---|---|---|---|---|---|
| 100 | ip30 | ip57 | ip65 (355) | ip138 | ip146 (415) | :=1 ip219 | ip785 | ip826 |
| 101 | ip26 | ip53 | ip61 (355) | ip134 | ip142 (415) | :=1 ip215 | ip742 | ip783 |
| 102 | ip30 | ip57 | ip65 (355) | ip138 | ip146 (415) | :=1 ip219 | ip609 | ip650 |
| 103 | ip26 | ip53 | ip61 (355) | ip134 | ip142 (415) | :=1 ip215 | ip617 | ip658 |
| 104 | ip26 | ip53 | ip61 (355) | ip134 | ip142 (415) | :=1 ip215 | ip462 | ip503 |
| 105 | ip26 | ip53 | ip61 (275) | ip134 | ip142 (-1) | :=0 ip204 | ip560 | - |
| 106 | ip26 | ip53 | ip61 (275) | ip134 | ip142 (-1) | :=0 ip204 | ip533 | - |
| 115 | ip30 | ip57 | ip65 (412) | ip138 | ip146 (-1) | :=0 ip208 | ip709 | - |
| 116 | ip30 | ip57 | ip65 (412) | ip138 | ip146 (-1) | :=0 ip208 | ip902 | - |
Exits that set `Map.Bit[162]/[163]` first SKIP their `Byte[13]/[14]:=3`: 100e15, 101e16, 102e8, 103e30t1, 104e2t1, 105e11,
115e1t1. Map vars are zeroed at every field start (EventEngine.cs:625-626), and no route script clears 162/163 (only the
off-route 101 e17 t2 ip418/426 and 106 e13 t2 ip409/417 write 0). Exits that DO write `:=3`: 103 e22 (Byte13 ip205,
Byte14 ip244), 106 e14 (Byte13 ip194), 116 e2 t1 (Byte13 ip1666).

## 100 Alexandria/Main Street (EVT_ALEX1_AT_STREET_A) - entrance 102
- e0 t0 ip243 `SWITCHEX(L294, 201,L245, 231,L245, 204,L245)`: 102 takes the default L294: `Map.Byte[24]:=0`, InitObject 19 (Vivi),
  2 (girl), kids, 9 (ticket), InitCode(14); ip366 `Bit[3718]==0` -> InitObject(1) = Rat Kid (Puck).
- **Movie = mbg101, not an FMV.** ip473 `Cinematic(0,5,1,1)` = FF9FieldFMVDispatch(0, 0x0105) = MBGDiscTable[1][5] =
  `MBG_DEF("mbg101", isRGB24 0, type 1 MBG_WITH_DATA)`; ip551 `Cinematic(2,0,0,0)` sets the PLAY bit. MBG.Play arms the
  skip hit-area only for type != 1 (MBG.cs:205-208), so a Confirm during mbg101 opens NO "skip movie" dialog. MBG.Play also
  sets the target FPS to the movie's (MBG.cs Play). The `SYSVAR[15]&128==0` test at ip449 is always true (SYSVAR[15] is 0/1/16).
  Vivi's walk-in waits for MBG frame 100 (e19 t1 ip751).
- Stage machine e0 t1 (Map.Byte[24] 0..7 on Map.Bit[231]):
  - 0 e19 t1 L28: `Byte[8]:=125` ip834, Walk(0,850).
  - 2 e2 t1: **146 "Are you alright?"** WindowSync ip194 [Confirm].
  - 3 e19 t1 L287 party: `UInt16[21]:=2` ip981 (Vivi only), SetPartyReserve, PARTYADD 1 (Map var), `Byte[303]:=0` ip1066,
    `Byte[303]++` ip1100 (ip1122/1144/1166 are behind `const(0)`: never), `Byte[4]:=0` ip1497 (PARTYCHK(5) false),
    `UInt16[19]|=2` ip1531 (guard ip1505: bit 1 clear - true after O1 and after a New-Game warp), `Byte[4]:=0` ip1562,
    `Byte[17]:=0` ip1570, `Byte[18]:=1` ip1578. SetCharacterData/SetName write player data, not gEventGlobal (DoEventCode JOIN 0xFE).
  - 4 e2 t1: **147 "Here!  You dropped your ticket."** WindowAsync ip351 + WaitWindow(2) ip384 [Confirm].
  - 5 e2 t1: **148 "Bye-bye![TIME=20]"** WindowSync ip449 [self-closing].
  - 6 e19 t1 L1255: AddItem(262) ip1982 (key item), `EnableMove` ip2020 -> CONTROL at (0,850).
- Rat Kid e1 t1: waits for player z>=1600 (ip112), EnablePath(3,0) ip124, then MoveInstant-chases (z+83/frame, x lagging 8
  frames); at `dist<200 && Map.Byte[31]==0` (ip311): `Map.Byte[31]:=3` ip337, CloseWindow 0..7, DisableMove ip388,
  EnablePath(3,1) ip410, RunScriptSync(4,255,18). e1 t18: **154 "Oww![TIME=10]"** WindowAsync ip537 + WaitWindow ip551
  [self-closing]; **155 "Rat Kid / Why you-get outta my way!!!"** WindowSync ip559 [Confirm]; RunScript(4,19,15) (player
  t15: EnableMove ip2143); **`Bit[3718]:=1` ip579**. Forced: the exit is at z>=6532.
- Exit north e15 (x -371..355, z 6532..7708): bits 162/163 ip38/46, `Int16[2]:=200` ip255, `Field(101)` ip263.
- Off-route: Potion hot-spots e12 (-658,4843) Bit[7215] / e13 (-758,1121) Bit[7214] fire only on Confirm|Special within
  ~281 units (e12 t1 ip37-123); doors e16 (107), e17 (114); card man e8.

## 101 Main Street B (EVT_ALEX1_AT_STREET_B) - first visit
- e0 t0 ip236 `Bit[3717]==1`? no -> L273: `Map.Byte[24]:=1`, **`Int16[2]:=202` ip291**, MoveCamera. Player (entrance 202)
  spawns at (2509,-814) with no control (e19 t0 L166) - inside exit e15 -, and at stage 1 walks to (1939,-883) (e19 t1
  ip691), out of e15, before control.
- Stage 1 e3 t1: **168 "Herald / Honorable nobles of Treno... Castle Alexandria is this way!"** WindowSync ip126 [Confirm].
- Stage 2 e7 t1 L97: nobles walk to (-4000,-400), ReleaseCamera, **`Bit[3717]:=1` ip319**, `EnableMove` ip358 -> CONTROL.
- Exit west e16 (quad (-3500,-600)(-3500,-200)(-2621,444)(-2254,-1444)): `Int16[2]:=201` ip255, `Field(102)` ip263.

## 102 Main Street C (EVT_ALEX1_AT_STREET_C) - no scene
Entrance 201 -> default spawn (865,2525) (e12 t0 L70), control (e12 t0 ip359 / e0 t0 ip543). The cat e3 spawns only for
entrance 205 (e0 t0 ip249). Exit north e8 (x 404..1134, z 5019..6987): `Int16[2]:=203` ip255, `Field(103)` ip263.

## 103 Square (EVT_ALEX1_AT_CENTER) - first visit
- Spawn (-75,-2210) (e30 t0 default L222), control. `Byte[8]:=125` e0 t0 ip367.
- Hippaul e18 (spawned when `Bit[7202]==0 && SC<1152`, e0 t0 ip289): e18 t1 `Byte[472]` in {0,1}: **`Byte[472]:=1` ip218**
  at once, 3 legs at speed 15 (~6600 units), **`Byte[472]:=2` ip254** only if he finishes before 103 unloads (TIMING NOISE).
- Booth: region e28 quad (-500,-111)(550,-111)(250,-1000)(-200,-1000); e28 t2 `Bubble(0)` = "?" (BubbleUI.IconType.Question);
  Confirm|Special inside with control -> e28 t3 `Map.Byte[24]:=1` ip95.
- e30 t1 stage 1: **choice 215** WindowSync(0,128,215) ip727, SYSVAR[9] ip733: option 0 "Peek into the ticket booth" ->
  bits 162/163 ip757/765, `Int16[2]:=205` ip972, `Field(104)` ip980. Option 1 Cancel -> control back (ip1017).
  Default cursor 0 (no EnableDialogChoices; flags 128 -> sChoose = sChooseInit = 0, ETb.cs:100-103).

## 104 Ticket booth (EVT_ALEX1_AT_TICKET) - no control at all
- e7 t0: `Int16[469]==0` -> **`Int16[469]:=1042` ip313**; `SC<1150` -> **`Int16[469]|=1` ip333** (=1043).
- Driver e2 t1: 0->1->2->(Byte27: 0->3, 1->9)->4->(Byte27: 0->5, 1->8)->6->7->8.
  - 0 e7 t1 Walk ip529. 1 e4 t1: **250 "Ticketmaster / Can I help you, son?"** ip155 [Confirm].
  - 2 e7 t1: `EnableDialogChoices(Int16[469],0)` ip546 (SetChooseParam -> default = absolute 0), **choice 251**
    WindowSync ip553, SYSVAR[9] ip559. Mask 1043 shows absolute 0 Show ticket, 1 What's showing today?, 4 Tell me about
    Alexandria!, 10 Leave. Option 0 -> **`Int16[469]&=8190` ip613** -> stage 3. Options 1-9 rewrite Int16[469]
    (ip646..ip863) and re-ask; option 10 -> stage 9 (e7 L789: leave without SC).
  - 3 e4 t1: **252** ip181, **253** ip190 [Confirm x2].
  - 4 e7 t1 L416: **254 "Nooooo!"** WindowAsync ip926; **`Byte[472]:=4` ip955** (guard <4); SC guard `SC>1150` ip964 false ->
    **`UInt16[0]:=1150` ip1046**; `Map.Byte[27]:=SYSVAR[19]>=98` (0 on a fresh game); WaitWindow(1) ip1103 closes 254 [Confirm].
  - 5 e4 t1: **255** ip215 [Confirm], **256** WindowAsync ip221 + WaitWindow ip235 [Confirm].
  - 6 e7 t1: AddItem 512 ip1152, 513 ip1196, 514 ip1240, each with **70 "Received ... Card!"** WindowSync(7,0,70)
    ip1179/1223/1267 [Confirm x3] (69 is behind `const(0)`).
  - 7 e4 t1: **257 "Talk to Alleyway Jack..."** ip257 [Confirm].
  - 8 e2 t1 L332: bits 162/163 ip343/351, `Int16[2]:=209` ip558, `Field(103)` ip566.

## 103 Square - second visit (entrance 209)
Spawn (45,-950) (e30 t0 L32) = INSIDE e28 (point test true): the "?" is up at spawn; a Confirm re-offers 215. Hippaul idle
(Byte[472]=4 -> default). Exit west e22 (quad (-4263,-1798)(-4605,-734)(-3611,-119)(-3150,-2777)): **`Byte[13]:=3` ip205**,
**`Byte[14]:=3` ip244**, `Int16[2]:=205` ip261, `Field(105)` ip269.

## 105 Alley (EVT_ALEX1_AT_BACK_STR)
- Main_Init: `SC<1152` -> Byte24=15, Puck e3, ladder e6, Alleyway Jack e7, EnablePath(2,0) ip296; `SC<1151` -> Byte24=1,
  Dante e4, region e12, EnablePath(2,0) ip325. Spawn (entrance 205 -> e14 t0 default L39) (-51,2986) WITH control.
- **Trigger e12** quad (-964,1677)(-1055,2300)(55,2000)(-122,1203): e12 t2 guard `1150<=SC<1152` ip38, DisableMove ip75,
  `Map.Byte[30]:=1` ip97.
- Driver e1 t1: 1->2->3->4->5->(Byte27 0->6, 1->7)->6->8->9->(Byte27 0->10, 1->16)->10->11->12->13->14->18; 16->17->9.
  - 1 e4 t1: **415 "Blast it![TIME=30]"** ip181 [self-closing]. 2 e4 t1: **416** ip347, **417** ip592, **418** ip694 [Confirm x3].
  - 4 e3 t1 L195: **304** ip344 [Confirm]; **choice 305** ip350, SYSVAR[9] ip356: 0 -> 308 ip372; 1 -> 306 ip381 + 308 ip387;
    2 -> 307 async ip396 + WaitWindow ip417 + 309 ip420. All converge: guard ip429, **`UInt16[0]:=1151` ip511**.
  - 5 e3 t1 L519: **choice 310** ip668, `Map.Byte[27]:=SYSVAR[9]` ip674. Need 0 "Alright".
  - 6 e3 t1 L880: **312** ip1032, **313** ip1038 [Confirm x2]. 8: Vivi walks to the lookout (e14 t1 ip2273/2280), EnablePath(2,1) e3 t1 ip1113.
  - 9 e3 t1 L1083: **choice 314** ip1243, Byte[27] ip1249. Need 0 "Yeah, it's clear" (1 -> 316 async + re-ask via 16/17).
  - 10 e14 t1 L1912 anim. 11 e3 t1 L1165: **315 "Awesome! Engage according to mission parameters!"** ip1314 [Confirm].
  - 12 RunSharedScript(2) (e14 ip2655); 13 Puck climbs (EnablePath(2,1) e3 ip1448); 14 Puck walks off, removes himself.
  - 14 e14 t1 L2175: `Map.Byte[35]:=0` ip2720 (Alleyway Jack wakes), guard ip2736, **`UInt16[0]:=1152` ip2818**,
    `EnableMove` ip2859 -> CONTROL.
- Exit south e11 (quad (-185,-770)(-1223,-895)(-1327,-167)(-220,195)): bits ip38/46, `Int16[2]:=111` ip227, `Field(106)` ip235.
- **HAZARD Alleyway Jack e7:** from stage 14 he patrols (446,3659)->(440,3700)->(-250,2800)->(-600+rand,2000)->
  (-800+rand,1000)->(-750,400)->(-780,-700) at speed 15 and stops at (-780,-700), which is INSIDE e11 (point test true).
  Contact runs e7 t2: a 16-frame "!" window (ip562-662). Confirm|Special inside it -> tutorial 321-326, **`Bit[3714]:=1` ip729**,
  `Int16[2]:=111` ip909, `Field(112)` ip917. No press -> player t12 "Mugged for [NUMB=0] Gil!" (318) / "The stranger ran away."
  (319), **`Bit[3715]:=1` ip945**. Either is a trace-visible divergence: leave for e11 at once (~4800 units of patrol ahead of him).

## 106 By the Steeple (EVT_ALEX1_AT_TSS)
- Main_Init: Ilia e5 spawned (ip254) -> e5 t0 **`Bit[3712]:=0` ip109**. `SC==1152` (ip276) -> Map.Byte[25]=1, Puck e2, e9,
  `Map.Byte[39]:=1` (Ilia frozen). Spawn (entrance 111 -> e16 t0 default L109) (-123,3494), control (e16 t0 ip406).
- Puck e2 t1: walks (300,3000)->(800,2200)->(800,1800); if player farther than 1200 -> **327 "Over here![TIME=45]"** async
  ip198 and waits until <=1400 (ip210); then guard ip230, **`UInt16[0]:=1153` ip312**; walks (800,-300) (ip329) [328 ip362 if
  >1200], (800,-1250) (ip403) [329 ip436], (-300,-1300) (ip498, inside e14); `Map.Byte[39]:=0` ip520; removes himself.
  The player spawn is 1929 from (800,1800): SC 1153 needs the player to come within 1400 AFTER Puck's two legs.
- Exit south e14 (x -327..151, z -1462..-1188): **`Byte[13]:=3` ip194**, `Int16[2]:=211` ip222, `Field(115)` ip230.
- NOISE Ilia e5 t1: after `Map.Byte[39]:=0`, `SYSVAR[0]<128` (ip136) branch A: wait player z<2200 -> **`Bit[3712]:=1` ip165**
  (its `:=0` ip332 needs player x<=-1000: off route); branch B: wait z<=-1800 -> ip475/:=0 ip656 (unreachable before e14).

## 115 Steeple (EVT_ALEX1_AT_SENTOU)
- Main_Init: `SC==1153||1152` -> **`Int16[2]:=213` ip249** (1154 -> 214 ip268, 1155 -> 215 ip287); SWITCH(213..) -> 213:
  Byte24=1, Puck e1, e8, Stiltzkin e7, InitCode(10), InitRegion(15). Kupo e2 always. **`Byte[8]:=125` ip467**.
  Player (entrance 213, e17 t0 L89) at (266,-3431) - inside exit e13 - with NO control; stage 1 walks him to (206,-1911).
- Driver e0 t1: 1->2->3->4->5->6->8->9->10->11->12->13 (7 skipped).
  - 1 e1 t1 L34: **352** ip313, **353** ip374 [Confirm x2]; guard ip380, **`UInt16[0]:=1154` ip462**; `EnableMove` ip500 -> CONTROL.
  - 2 e17 t1 L111 waits `Map.Byte[49]!=0`. Ladder region e15 (x -150..150, z -40..144), e15 t2 `Bubble(1)` = "!";
    Confirm inside -> e15 t3 `Map.Byte[49]:=1` ip65 (stage != 10: nothing else) -> e17 t1 `DisableMove` ip913.
    **Control stays off from ip913 until stage 10 (ip1841).** Kupo's "Ku-Kupo!" (355, the code-101 path with an EnableMove at
    e2 t1 ip367) is dead: no script in 115 ever sets Map.Byte[38]=101.
  - 3 e17 t1 L177: Kupo falls (Map.Byte[38]:=102), **356 "Oww![TIME=10]"** async ip1017 [self-closing].
  - 4 e1 t1 L356: **357 "Ahahaha! What the heck was that!?"** async ip574 + WaitWindow(3) ip601 [Confirm; no control].
  - 5 e17 walks to (50,-968); Kupo L301: **358** ip479 [Confirm].
  - 6 e1 t1 L487: **359** ip737; Kupo L346 **362** ip499 (+Map.Byte[49]:=0); **360** ip815, **361** ip821; Kupo L374 **363** ip527,
    **364** ip533, loop **365** ip550, **366** ip556, **choice 367** ip562 (`Instance.Byte[12]:=SYSVAR[9]` ip568; 1 loops),
    **368** ip590 [Confirm each].
  - 8 e1 t1 L836: **370** ip1054 [Confirm].
  - 9 e1 t1 L900: Puck climbs; **371** async ip1480 + WaitWindow ip1507; Stiltzkin (Map.Byte[55] counter): **372** async e7
    ip144 + WaitWindow(5) ip213, **373** e2 ip628, **374** e2 ip638, **375** e7 ip241, **376** e2 ip674, **377** async e7 ip272 +
    WaitWindow ip292, **378** e2 ip705, **379** e7 ip320, **380** e7 ip326, **381** e17 ip1467, **382** e2 ip758;
    **383** async e1 ip1564 + WaitWindow ip1591 [Confirm each]; guard ip1601, **`UInt16[0]:=1155` ip1683**.
  - 10 e17 t1 L792: Kupo made talkable (Map.Byte[38]:=1 -> SetObjectFlags(5)); `Bit[3784]` READ only (ip1724); `EnableMove`
    ip1841 -> CONTROL (SC already 1155).
  - **Climb:** Confirm in e15 at stage 10 -> e15 t3 guard `Map.Byte[24]==10` ip73, DisableMove ip103,
    `RunScriptSync(2,250,15)` ip125 -> e17 t15: jumps on at y -101; loop: `B_KEY(16)` Up ip2671 -> y-20, else `B_KEY(96)`
    Right|Down ip2759 -> y+20, else `B_KEY(128)` Left ip2847 -> y-20; one animation frame per step; exits the band
    [-2431,-101]; at the top the player stays with control off (e17 t15 ip3210) and e17 t1 L1102 -> DisableMove ip1913 ->
    stage 11. Back at the bottom (y>-1000) e15 t3 re-enables control (ip172): retry.
  - 11 e17 t1 L1177 anim. 12 e1 t1 L1531: **384** ip1758 [Confirm]; bits 162/163 ip1764/1772; DisableMove ip1799;
    `Int16[2]:=0` ip1951; `Field(116)` ip1959 (its `Byte[13]:=3` ip1923 is skipped).

## 116 Rooftop (EVT_ALEX1_AT_ROOF) - SEGMENT END
- Main_Init: `Map.Byte[24]:=1` ip231 (`Int16[2]==217`? no); **`Byte[8]:=125` ip335**. Player e21 (2719,-1902), no control.
  No SetRegion anywhere in 116; all goals are position tests.
- 1 e2 t1 L36: **387** async ip219 + WaitWindow ip246 [Confirm]; **388** ip249, **389** ip255 [Confirm x2]. 2: Vivi crosses a plank.
- 3 e2 t1 L203: **390** async ip336 [Confirm]; both e2 (WaitWindow ip363) and e21 (WaitWindow ip617) wait for it to close;
  then e21 `EnableMove` ip662 -> CONTROL (no window up).
- 4 e21 t1 L305: waits player **x<=900** (ip742), DisableMove ip773.
- 5 e2 t1: **391** ip505, **392** async ip511 + WaitWindow ip538 [Confirm x2]. 6 e21: plank falls, scripted jump (ip877-886).
  7 e2: **393** ip552, **394** ip558 [Confirm x2].
- 8 e21 t1 L480: `EnablePathTriangle(217,0)` ip923, `EnableMove` ip958 -> CONTROL. 9 e21 t1 L601: waits **z>=2300** (ip1038),
  DisableMove ip1069.
- 10 e2 t1 L577: **395** ip728, **396** ip737 [Confirm]; SetName(1,87) ip743; SetCharacterData(1,0,255,5,1) ip748 (player data,
  not gEventGlobal); **Menu(1,1) ip758 = NAMING SCREEN for Vivi**; **`Byte[6]|=2` ip765**; **397** ip776, **398** ip782,
  **399** ip788 [Confirm x3].
- 11 e2 t1 L686: `EnableMove` ip901 -> CONTROL; Puck walks (-1271,6289)(1079,6289)(1754,6321)(4039,6252)(4039,9303)(3410,9303)
  (3348,11138) and waits `Map.Byte[30]`. e16 t1 (InitCode, every frame): player **x>3000 && z>10300** (ip11) -> DisableMove
  ip50, `Map.Byte[30]:=1` ip72.
- 12 e2 t1 L1132: **400** ip1307, **401** ip1390, **402** ip1399 [Confirm x3].
- 13 e2 t1 L1344: **`Byte[8]:=0` ip1469**, DisableMove ip1542, PreloadField(5,61), fade 64, **`Byte[13]:=3` ip1666**,
  **`Int16[2]:=0` ip1694**, **`Field(61)` ip1702**.

## SC ladder (all six decoded at the cited ip; the census finds no other SC store in 100-106/115/116/61)
SC arrives as 1000 (O1: 50 e17 t1 ip1804).
| value | where | when | guard / debug overwrite |
|---|---|---|---|
| 1150 | 104 e7 t1 ip1046 (abs3186) | stage 4, 20 frames after 254 "Nooooo!" opens, before its WaitWindow | ip964 / ip1032 |
| 1151 | 105 e3 t1 ip511 (abs2279) | stage 4, after choice 305 and 308/309 | ip429 / ip497 |
| 1152 | 105 e14 t1 ip2818 (abs9966) | stage 14, Puck gone, before EnableMove ip2859 | ip2736 / ip2804 |
| 1153 | 106 e2 t1 ip312 (abs1516) | after Puck's legs to (800,1800) and the player within 1400 (ip210) | ip230 / ip298 |
| 1154 | 115 e1 t1 ip462 (abs2142) | stage 1, after 353, before EnableMove ip500 | ip380 / ip448 |
| 1155 | 115 e1 t1 ip1683 (abs3363) | stage 9, after 383, before stage 10's EnableMove (e17 ip1841) | ip1601 / ip1669 |
Each debug overwrite is behind `SC > value` ("Error Set Scenario Counter", text 67): false on the route.

## FieldEntrance chain
102 -> 200 (100 e15 t2 ip255) -> 202 (101 e0 t0 ip291) -> 201 (101 e16 t2 ip255) -> 203 (102 e8 t2 ip255) -> 205 (103 e30 t1
ip972) -> 209 (104 e2 t1 ip558) -> 205 (103 e22 t2 ip261) -> 111 (105 e11 t2 ip227) -> 211 (106 e14 t2 ip222) -> 213
(115 e0 t0 ip249) -> 0 (115 e1 t1 ip1951) -> 0 (116 e2 t1 ip1694).

## Expected story keys (besides the ambient table and the ladder)
100: Byte[8]:=125 (e19 t1 ip834); UInt16[21]:=2 ip981; Byte[303]:=0 ip1066, ++ ip1100; Byte[4]:=0 ip1497; UInt16[19]|=2 ip1531;
Byte[4]:=0 ip1562; Byte[17]:=0 ip1570; Byte[18]:=1 ip1578; Bit[3718]:=1 (e1 t18 ip579). 101: Bit[3717]:=1 (e7 t1 ip319).
103: Byte[8]:=125 (e0 t0 ip367, both visits); Byte[472]:=1 (e18 t1 ip218) [+ :=2 ip254, timing]. 104: Int16[469]:=1042 (e7 t0
ip313), |=1 (ip333), &=8190 (e7 t1 ip613); Byte[472]:=4 (ip955). 103 again: Byte[13]:=3 ip205, Byte[14]:=3 ip244.
106: Bit[3712]:=0 (e5 t0 ip109) [+ :=1 e5 t1 ip165, random]; Byte[13]:=3 (e14 ip194). 115: Byte[8]:=125 (e0 ip467).
116: Byte[8]:=125 (e0 ip335); Byte[6]|=2 (e2 ip765); Byte[8]:=0 (ip1469); Byte[13]:=3 (ip1666).
Not gEventGlobal: AddItem 262 and cards 512-514, SetName/SetCharacterData/Menu(1,1), PARTYADD (a Map-var expression).
End state: SC 1155, Int16[2] 0, UInt16[21] 2 (Vivi only), Byte[6] |= 2 (3 after O1; 2 after a warp start), Byte[472] 4,
Int16[469] 1042, Bit[3717]/[3718] 1.

## Choices (default cursor 0 for every one; all needed options are 0)
Match on OPTION text only (the prompt may publish empty; the line after `[CHOO][MOVE=18,0]` loses its first character;
pick_for matches `match` against prompt+lines and maps a hit through `active` to the absolute index, o1_opening.py:320-338).
| field / site | raw options (first published without its 1st char) | rule: match -> pick |
|---|---|---|
| 103 e30 t1 ip727 (215) | Peek into the ticket booth / Cancel (no prompt) | "ticket booth" -> "ticket booth" |
| 104 e7 t1 ip553 (251, PCHM=11,10, mask 1043: abs 0,1,4,10 shown) | Show ticket / What's showing today? / Tell me about Alexandria! / Leave | "ticket" -> "ticket" (abs 0). NOT "Show ticket": it publishes "how ticket" |
| 105 e3 t1 ip350 (305) | Y-Yeah, it's fake / N-No, it's not fake / Are you Alleyway Jack? | "fake" -> "Yeah" |
| 105 e3 t1 ip668 (310) | Alright / N-No, I don't want to | "want to" -> "right" |
| 105 e3 t1 ip1243 (314) | Yeah, it's clear / I think someone's coming | "someone" -> "clear" |
| 115 e2 t1 ip562 (367) | I understand / Once more... | "Once more" -> "understand" |
Keep O1's `{None, "want to skip", default}`: 100's mbg101 cannot raise it, 61's FMV003 comes after the cut.
Apostrophes in this block are U+2019: no rule string above contains one.

## Nondeterminism
1. 103 `Byte[472]:=2` (e18 t1 ip254): only if Hippaul's 3 legs (speed 15) end before 103 unloads; `:=4` in 104 either way.
2. 106 `Bit[3712]:=1` (e5 t1 ip165): random (`SYSVAR[0]<128` ip136) and only if Puck's `Map.Byte[39]:=0` (ip520) lands before
   106 unloads (Puck ends inside e14, so it can land during the exit fade). Register as noise with its `:=0` at e5 t0 ip109.
3. 106 SC 1153 (ip312) needs the player within 1400 of (800,1800) after Puck's legs; a driver that outruns him leaves with
   SC 1152 (115 accepts both). Guard: do not enter e14 before the published scenario reads 1153.
4. 105 Jack patrol (x offsets from SYSVAR[0], e7 t1 ip379/408); any contact is a divergence (Bit[3714] or Bit[3715]).
5. 100: mbg101 and the Rat Kid chase are timing-driven; the bump is forced before the exit; Bit[3718] fixed.
6. 115 climb: held-key minigame; Down/Right descends; the bottom re-enables control (retry). Writes unaffected.
7. Random NPC wander in 100/101/102/103/116 reads SYSVAR[0] but writes no global.
8. Optional Confirm hot-spots (potions 100 e12/e13, 101 e12/e13, 103 e21, 115 e11/e12, 116 e17-e19; scratch Int16[220..228],
   Byte[226]), NPC talks (Tom/Byte[465], card NPCs, Kupo's Mognet/save), the 103 booth on the 2nd visit, 104 info options
   (Int16[469] ip646-863): only on a stray Confirm/Down.

## Disputes settled (reader claims vs the bytes)
1. **100's movie.** Bytes-reader: mbg101 in-field MBG. Data-reader: FMV gated on SYSVAR[15]&128==0, probably FMV003.
   Harness auditor: a Confirm opens the skip dialog. BYTES: `Cinematic(0,5,1,1)` = MBGDiscTable[1][5] "mbg101", type 1
   MBG_WITH_DATA; no skip hit-area for type 1 (MBG.cs:205-208); SYSVAR[15]&128 is always 0. FMV003 = [1][8] = 61's movie.
2. **Exit music writes at 103 e22 / 106 e14.** Bytes-reader: both fire. Data-reader: omitted. BYTES: neither exit sets
   Map.Bit[162]/[163]; guards true; 103 e22 ip205/ip244, 106 e14 ip194 fire.
3. **105 choice 310 option 1.** Bytes-reader: stage 7, re-offer only after re-entering. Data-reader: not traced.
   BYTES: 311 (ip742), EnableMove ip993, endless loop L869; stage 7 waits forever; Puck's talk says 317 unless Byte24==15,
   which only a re-entry sets (e0 t0 ip279); then e3 t3 ip1791 `Map.Byte[24]:=5` re-asks 310.
4. **Jack contact without a press.** Data-reader grouped Bit[3715] with the side trip. BYTES: press -> Bit[3714] ip729 +
   Field(112) ip917; no press -> mugged + Bit[3715] ip945 (exclusive branches).
5. **103 booth bubble.** Data-reader "!"; bytes-reader "?". BYTES: e28 t2 Bubble(0) = Question.
6. **105 stage of 315.** Bytes-reader gate "Byte24=10". BYTES: e3 t1 SWITCH(3,..) maps 11 -> L1165 (315 ip1314); 10 is the
   player's anim (e14 L1912).
7. **115 climb call site.** Bytes-reader: "e15 tag3 ip65 RunScriptSync". BYTES: ip65 is `Map.Byte[49]:=1`; the call is ip125.
8. **Fork ids.** Data-reader used C:/gd/journey-scratch/opening (100->6001 .. 61->6023): not deployed. Live FF9CustomMap:
   O1 chain 31200-31219 (61 -> 31211), no alxt donor rows. O2 member ids are a build decision.
9. **Harness auditor: untimed async windows while control is held (115 357/371).** BYTES: control is off from e17 t1 ip913
   to ip1841 (the only intermediate EnableMove, Kupo's code 101, is dead); 116 enables control only after WaitWindow.
   The only windows up WITH control on the route are 106's [TIME=45] hints. O1's overlay rule is correct; no new rule.
10. **Harness auditor: climb beat key (115,1154, 2nd ladder visit).** BYTES: SC:=1155 at ip1683 precedes stage 10's
    EnableMove; key is (115,1155).
11. **Harness auditor's beat table lacks (106,1152).** BYTES: control on arrival (e16 t0 ip406) with SC 1152; 1153 comes later.
12. **Harness auditor's 104 rule `'Show ticket'`.** Never matches ("how ticket"); use "ticket".
13. **Gates auditor: a failed fldfmv gate would stall 100.** BYTES+code: the gate (fldfmv.cs:112) only lets status 5 play
    without the PLAY bit; 100's own `Cinematic(2,0,0,0)` ip551 sets that bit once SYSVAR[15] reads 0, so a failed gate
    delays the MBG start instead of stalling (not tested in game).
14. **Harness auditor: 61 Main_Init writes Int16[2]:=10000.** BYTES: conditional on Bit[184]==1 (61 e0 t0 ip30-41), never here.

## Harness gaps (merged; see the structured result for status)
Ready: gateway crossing; region + Confirm (103 e28 "?", 115 e15 "!"); 105 e12 walk-in; naming (accept_name); masked choices
(`active`); ATE none; minigames off-route; Kupo off-route; end_run recovery (4600 registered).
Gaps/risks: (a) beat table keyed on (donor, published SC, driver counter): (100,1000) cross e15 [re-issue after the bump];
(101,1000) e16; (102,1000) e8; (103,1000) booth + Confirm; (103,1150) e22, no Confirm (spawn inside e28); (105,1150) into
e12; (105,1152) e11 at once; (106,1152) toward (100,1800) until SC 1153; (106,1153) e14; (115,1154) ladder + Confirm;
(115,1155) ladder + Confirm + hold Up; (116,1155) #1 x<=900, #2 z>=2300, #3 x>3000 && z>10300. (b) hold-Up climb verb.
(c) runtime walkmesh edits the offline planner does not see: 100 EnablePath(3,0) e1 t1 ip124->ip410; 105 EnablePath(2,0)
Main_Init ip296/325 -> (2,1) e3 ip1113/1448; 116 EnablePathTriangle(217,0) e21 ip923. (d) 106 hints need
route_to(overlay_ok=True). (e) Rat Kid MoveInstant chaser vs walker avoidance. (f) Jack contact = VOID.
(g) start: warp into 100/member(100) at entrance 102 with scenario 1000. (h) mbg101 sets the target FPS during playback.
(i) budget, offline rehearsal, stage invisibility, self-closing windows in the transcript.
Suggested goal points (verify on the walkmesh, P-FLOOR): 100 e15 (0,7000); 101 e16 (-2900,-500); 102 e8 (750,5800);
103 booth (45,-950) (103's own entrance-209 spawn, inside e28); 103 e22 (-3900,-1350); 105 e12 (-500,1750); 105 e11
(-700,-400); 106 e14 (-100,-1320); 115 ladder (0,50); 116 (800,260), (-715,2400), (3370,10500) (on Puck's walked lines).

## Fork gates (merged)
No gate on 100-117 or 61 can change a story write: DialogManager.cs:214 (100, Map.Byte[31]==3 at e1 t1 ip337), fldfmv.cs:112
(100), VIB s62 (100 e1 t18 ip517-527, 115 e17 t1 ip996-1006, 116 e21 t1 ip833-843), s30 effMapNo sites (101/103/108/112/114),
EventCollision.cs:358 alias, EMinigame.cs:110 alias - all wrapped (spot-checked). Visual/audio only: PSXCameraAspect.cs:47
(116 cam 1), MCF shadows, SaXAudio reverb. Preconditions: ForkDonorPatch rows for the alxt members + relaunch (none today);
each member registers text block 33 (no mod folder overrides block 33 or any EVT_ALEX1_AT_* / STAGE_BK script today, and
DictionaryPatch has no FieldScene 100-117/61 rows: the S side is stock). Seams: START - O1's member(52) (31202) targets
REAL 100, so the fork side must warp into member(100); END - member(116)'s Field(61) stays real 61 unless the import links
to O1's chain (then 31211, donor 61): cut in donor terms. Sibling (outside O2): TreadQuad.cs:45 raw CreateNPCID.

## Could not determine / unverified
Hold Up reaching B_KEY(16) in game (code path read, never run); climb length in frames; whether 103 ip254 and 106 ip165 land;
whether choice prompts publish; the "how ticket" publication for a PCHM window; mbg101's length; the fldfmv reading;
walkmesh reachability of the goal points (esp. 116 after EnablePathTriangle(217,0)); the chaser vs route_to; Jack's pace vs
the harness; which later field shows block-33 texts 403-407 (not on this route).

## alxt zone (48 fields, FBG token alxt)
100-117 (disc-1 visit), 1850-1865, 2050-2054, 2450-2457, 3000. Route: 100, 101, 102, 103, 104, 103, 105, 106, 115, 116.
Off-route side rooms: 107-114, 117. Scripted Field() seams on the route that a whole-zone verbatim remap must carry:
103->104 (205), 104->103 (209), 115->116 (0), 116->61 (0, tshp). Off-route scripted: 105->112 (Jack, 111), 104 e7 ip1519 (Leave).
