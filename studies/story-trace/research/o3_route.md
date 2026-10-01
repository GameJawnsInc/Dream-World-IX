# Stock O3 route: arrival in 61 (FieldEntrance 0, SC 1155) -> 62 -> [battle 338] -> 63 -> Field(64)  (reconciled)

The reconciler's own decode, independent of the two readers' dumps. Every ip below was decoded from the stock US `.eb` by
`reconcile/ebtool.py` (storytrace.stock_script_source + ScriptIndex + instruction_stores), not copied from a reader.
- `ip` = abs - entry code start = the s88 trace ip (measured: O2's traces record 61's prologue at ip 22/49/57/119/138/200,
  `.harness-runs/20260930-192740-story-o2/run1_S.jsonl`). `Lnnn` = offset from the function start.
- Listings: `reconcile/L{61,62,63,64,150,153,70}.txt` (every instruction; `<<('global', vtype, index)` on each gEventGlobal
  store). `reconcile/win_route.txt` = every Window op of 61-64/150 with its US text (`mes_<fid>.json`, the block the engine
  picks: 61-64 block 2, 150/153 block 3). `reconcile/scenes_336_338.txt` = the two play battles' scene flags and HP.
- `SWITCH(base, default, case_base, case_base+1, ...)`; `SWITCHEX(default, value, target, ...)`.
- Engine: live Memoria source C:\gd\FFIX\Memoria (the fork-gate reader matched the deployed DLL to Output, nothing newer).

## Segment end: CHOSEN = arrival in real 64 (63 e4 t1 ip828 `Field(64)`, FieldEntrance 100, SC 1155)
| # | exit (stock) | arrival | SC | est. min from 61 | new fork / deploy | inside |
|---|---|---|---|---|---|---|
| **1 CHOSEN** | 63 e4 t1 ip828 `Field(64)` (`Int16[2]:=100` ip820) | real 64 (alxc), ent 100 | 1155 | ~6 | none: 31211-31213 are live; 31213's Field(64) is already the seam | FMV003, 10 pages, battle 338 |
| 2 | 64 e2 t1 ip536 `Field(150)` (`Int16[2]:=325` ip528) | real 150, ent 325 | 1155 | ~10 | alxc member(64) + re-link 31213 in place | + Chanbara minigame, choice 124 |
| 3 | 150 e3 t1 ip2169 `Field(153)` (`Int16[2]:=325` ip2161) | real 153, ent 325 | 1190 | ~12 | alxc members 64, 150 + re-link 31213 | + 13 pages, SC 1190, party -> Zidane |
| 4 | 153 e3 t1 ip3158 `Field(154)` (304) | real 154 | 1190 | ~16 (rough) | + 153 | walking, choice Bit[3795], back door e28 |
| 5 | 166 e6 t1 ip871 `Field(55)` (110) | real 55 (tshp) | 1190 | 26-40 (graph only) | whole alxc disc-1 cluster | Steiner naming, knight hunt, FMV004 |

Why 1 (and not the bytes reader's 3):
- **Run time.** ~6 min a run, O2's size (O1 3.5, O2 ~6). Candidate 3 doubles it (~12 min x 6+ runs + reruns).
- **A whole-zone chain with nothing to build.** 61-63 are the tshp members O1 deployed and never ran (31211/31212/31213).
  The end is the tshp -> alxc boundary, the same seam pattern as O1 (52 -> real 100) and O2 (116 -> real 61). No import,
  no deploy, no relaunch.
- **The longer ends need surgery on O1's proven chain.** 31213 (63) has no retarget: its Field(64) is real 64. To run 64 as
  a fork, 31213 must be rebuilt and redeployed IN PLACE. The bytes reader's other option (fresh copies of 61-63 in an O3
  band) is unsafe: donor 63 forked twice sets `ForkSiblingMap[63] = -1` (DataPatchers.cs:148-160) and battle 338 then
  lands the fork run in REAL 63 (HonoluluBattleMain.cs:736-738).
- **One new driver feature, not three.** O3 adds the battle beat (with the s24 battle-return redirect under the trace and
  the first FMV inside a segment). Candidate 2/3 add the Chanbara minigame (a no-press rule the driver lacks; its fork
  gate EMinigame.cs:12 is still "PENDING playtest" in memory project-ff9-faithful-opening) and a choice.
- **Start.** Under a plain raw warp (O2's), 61-63 read no start-dependent key (start reader; verified below). The first
  start-dependent reads (UInt16[19] at 153 e32 t1 ip2180, Byte[6] at 151 e3 t1 ip610) are far past every candidate.

Everything after the arrival in 64 is O4's: start O4 by a raw warp into member(64) at entrance 100 with SC 1155 (64's
Main_Init dispatch, below), so O1's 31213 never needs re-linking. O4's natural first end is candidate 3 (SC 1190).

## Ambient prologue (every field's e0 t0; song -1 everywhere; same shape as O2's table)
`Bit[191]:=0`, `Bit[184]:=0`, `Int16[9]:=65535` (-1), Byte[13] (==9 -> no write; ==2 && Int16[9]<0 -> `:=9`;
Int16[9]<0 -> `:=0`), `Int16[11]:=65535`, Byte[14] likewise -> `:=0`. `Int16[2]:=10000` is behind `Bit[184]==1` (never).
No tail Byte[13]/[14] writes in 61-64. A Byte[13] or Byte[14] of 9 after the prologue opens the debug CONFIRM window 3
"Error Env Play() Slot=" (WindowAsync(6,0,3) + WaitWindow(6)) and then writes `:=0`.
| field | Bit191 | Bit184 | Int16[9] | Byte13:=0 | Int16[11] | Byte14:=0 | error-path writes (must not fire) |
|---|---|---|---|---|---|---|---|
| 61 | ip22 | ip49 | ip57 | ip119 | ip138 | ip200 | B13:=9 ip97, B14:=9 ip178, :=0 ip349/ip383 |
| 62 | ip26 | ip53 | ip61 | ip123 | ip142 | ip204 | ip101/ip182, ip346/ip380 (e0 t10: ip580/ip614) |
| 63 | ip22 | ip49 | ip57 | ip119 | ip138 | ip200 | ip97/ip178, ip362/ip396 |
| 64 (end) | ip22 | ip49 | ip57 | ip119 | ip138 | ip200 | ip97/ip178, ip845/ip879 |
Incoming Byte[13] at 61: 3 on a true O2 end (116 e2 t1 ip1666; MEASURED: O2 traces record 61 ip119 old 3 -> new 0), 1 after
New Game + the raw warp (MEASURED: all 6 O2 runs show old 1 at their first Byte[13] row; field 70's prologue `:=1` ip130,
its FMV001 tail `:=2` at 70 e0 t0 ip475 comes minutes later). Both take `:=0` at ip119. An incoming 2 (a warp after
FMV001) would take ip97 `:=9` and stall on the error window: O3-START must require 61's first Byte[13] row at ip119.

## 61 Prima Vista/Interior (EVT_ALEX1_TS_STAGE_BK, fbg_n00_tshp_map009_th_bst_0) - the play's prologue
- Main_Init e0 t0: no Int16[2] read anywhere in 61 (any entrance is fine; use 0 = 116 e2 t1 ip1694). `Map.Byte[24]:=0`
  ip229; InitObject 2 (Baku, model 5501), 7, 8 (swords), 9 (Zidane, DefinePlayerCharacter e9 t0 ip274), 14 (Cinna),
  16 (Blank). EnableMove ip440 is behind `Map.Bit[158]==1` (ip399), which nothing sets: **no control in 61**.
- e2 t1 stage 0 (SWITCH(0,L736,L12) ip119): `SYSVAR[15]&128==0` ip135 -> **`Cinematic(0,8,1,1)` ip159 = MBGDiscTable[1][8]
  = MBG_DEF("FMV003",1,0)** (MBG.cs:829): type 0, so MBG.cs:205-208 arms the skip hit-area. PLAY bit `Cinematic(2,0,0,0)`
  ip237. Waits movie frame <4 (ip266), fades in, then waits `SYSVAR[14] < 1100 && SYSVAR[15]&127 != 1` (ip324): resumes at
  movie frame 1100 or the movie's end (fldfmv.cs:68-78 sync 1 = status 8). The live file is MoguriVideo FMV003.bytes,
  theora 29.97 fps, 84.8 s (ffprobe; the base StreamingAssets copy is 15 fps, 83.6 s).
- Then 7 narrator pages, each WindowAsync(1,128,n) + WaitWindow(1) [Confirm]: **72** "Ladies and Gentlemen!" ip533/565,
  **73** ip568/584, **74** ip587/598, **75** ip601/612, **76** ip615/631, **77** ip646/661, **78** ip664/679 ("...Tantalus
  proudly presents 'I Want to Be Your Canary'!"). **`Byte[8]:=125` ip752**. Bit231 ip840 -> stage 2.
- Conductor e1 t1 SWITCH(0, L364, L26, L364, L56, L86, L116, L146, L176, L206) ip15: 0->2->3->4->5->6->7 on Map.Bit[231];
  e9 t1 stage 6 also writes Byte24:=7 (ip453). Lines (all `[TIME=-1]`, closed by CloseWindow after 55 or 20 frames, never
  pages): stage 3 e16 79/80 (ip160/175); stage 4 e14 81/82 (ip144/159); stage 5 e9 83/84 (ip387/402, `[ZDNE]`);
  stage 6 e14 86 (ip182), e16 85 (ip201).
- Exit stage 7 e1 t1 L206: DisableMove ip239, PreloadField(5,62) ip261, FadeFilter ip303, op_22(25), Bit162/163 tests
  empty (ip341/352), **`Int16[2]:=100` ip363**, **`Field(62)` ip371** (31211: retargeted to 31212).

## 62 Prima Vista/Interior (fbg_n00_tshp_map011_th_stg_0) - Act I, then battle 338
- Main_Init: `Map.Byte[24]:=0` ip242; InitCode 1-4, 11; InitObject(12,128..131) (one entry instanced four times: no window,
  no global store), 13 (Zidane, DefinePlayerCharacter), 20 Blank, 18 Cinna, 19 Marcus, 8 King Leo, 9, 10. No control
  (EnableMove ip437 behind Bit158). No Int16[2] read.
- Conductor e4 t1 SWITCH(0, L1346, L38..L278, L308) ip23: stages 0..9 on Map.Bit[231]. Lines, all `[TIME=-1]` CloseWindow'd
  (no page): 87 Blank e20 ip333, 88 Marcus e19 ip206, 89/90 Cinna e18 ip294/309, 91-93 King Leo e8 ip217/232/247,
  94/95 Zidane e13 ip678/693. 61-63 contain no B_KEYON/B_KEY read at all.
- Stage 10 e4 t1 L308 (the play's party):
  - **`UInt16[21]:=3585` ip319** (0xE01 = Zidane + Cinna 9, Marcus 10, Blank 11), SetPartyReserve ip327.
  - PARTYCHK 0..11 ip349-392 -> mask; XOR with {0,9,10,11}; RemoveParty ip494; PARTYADD 0/9/10/11 if absent ip528-594
    (Map.Bit[147] expressions, not gEventGlobal).
  - **`Byte[303]:=0` ip603**, **`Byte[303]++` ip637, ip659, ip681, ip703** (each behind `const(1)`): ends 4.
  - `const(5) PARTYCHK` ip1014 (after the rebuild: Quina absent) false -> **`Byte[4]:=0` ip1034** (ip1023 `:=1` not taken).
  - SetCharacterData 0/9/10/11, SetName(9,28)/(11,30)/(10,29) (player data). **`Byte[4]:=0` ip1085**, **`Byte[17]:=0`
    ip1093**, **`Byte[18]:=1` ip1101**; SetHP 9999 / SetMP 999 / CureStatus for every slot.
  - **`Int16[2]:=0` ip1285**, **`Battle(0,338)` ip1293**.
- **THE BATTLE NEVER RETURNS TO 62.** Scene 338's own script, entry 0 tag 0, at battle start (SYSVAR[26] = gMode==4 is 0):
  InitObject(2,128)/(1,129)/(3,130), **[265] `RunBattleCode(37, 63)`** -> btl_scrp.cs:829-840 "Change next field" ->
  EventEngine.cs:1306-1318 (mode 2) `FF9Battle.map.nextMapNo = 63` (overriding the Awake default 62, HonoluluBattleMain.cs
  :117) -> at the end HonoluluBattleMain.cs:734-738 `fldMapNo = 63` (from a fork: `ForkSiblingField(63)` = 31213) ->
  EventEngine.cs:666 resumes a field only when `lastmap == fldMapNo` (62 != 63), so **63 loads fresh (its Main_Init)**.
  62's Main_Reinit (e0 t10) and e4 t1 ip1298-ip1353 (`Int16[2]:=0` ip1345, `Field(63)` ip1353) are dead on this route.
  In-game proven for a fork in June (memory project-ff9-doeventcode-fork-gates: "the fork's suspended Field(forkId) is
  ABANDONED"; the DataPatchers.cs:98-101 comment names "the play's King Leo battle -> real field 63").

## Battle 338 = BSC_TH_E002 (King Leo + Zenero + Benero)
- Scene flags 0x1839 (scene_codec on the install's raw16): preemptive, no-EXP, no-escape, AfterEvent, and bit 0x10 set ->
  **WinPose false** (BTL_SCENE.cs:222). Puts: type 1 Zenero (HP 32) at (700,200), **type 0 King Leo (HP 10186)** at (0,700),
  type 2 Benero (HP 28) at (-700,200); AP 1. No tutorial (battle.cs:100: scene 336 only).
- AI entry 1 = enemy type 0's AI = King Leo (InitObject order 2,1,3 = the put order type 1,0,2). Tag 1 (Main):
  - [536]-[554] one frame at a time, **`Global.Byte[206]:=SYSVAR[0]` [539]** until `SYSVAR[30]==1`; RunBattleCode(35,0)
    [557] (ATB on); waits `SYSVAR[30]==4`;
  - [579]-[601] each frame: if `Map.Byte[24]==0` and **`B_SYSLIST[1] B_MEMBER(36) <= 10000 B_COUNT`** -> Map.Byte[24]:=1.
    In battle code EBin.ad3 (EBin.cs:178-183) calls ProcessCodeExt, which sets SYSLIST[1] to the RUNNING object's own bit
    (EventEngine.cs:985-994): the test is King Leo's own cur.hp <= 10000, i.e. **>= 186 damage dealt to King Leo**;
  - waits `SYSVAR[25]==0` (no sequence busy), RunBattleCode(32,0) [638] (ATB off), waits `SYSVAR[30]==1`,
    **RunBattleCode(33,1) [660]**: with WinPose false btl_scrp.cs:785-797 stores **result 2 (victory-no-pose)** and closes.
    (HonoluluBattleMain.cs:732-733 later folds 2 into 1; O1 measured 2 for scene 336, flags 0x835, same bit.)
- Enemy tag 5 (ATB) only `Attack`s; party HP 9999 -> nobody falls. Entries 2/3 (the minions) have no counter/death tags.
- gEventGlobal writes: only Byte[206] (random value, random count; O1's registered noise, `not_m FIELD_MODE`). TH_E002 writes
  no Byte[199] (TH_E001 did). The rows carry fld 62 (S) / 31212 (F): fldMapNo changes only at the battle's end.
- Driver: `fight(finish=True)` (attack the first standing foe each turn until a result; it must keep attacking until King
  Leo has taken 186).

## 63 Prima Vista/Interior (fbg_n00_tshp_map011c_th_stg_3) - Zidane vs Blank on stage (loaded fresh after the battle)
- Main_Init: `Map.Byte[24]:=0` ip238; InitCode 1-4, 10; InitObject 11-14 (Zidane e14, DefinePlayerCharacter), 21 (Blank),
  19, 20, 6 (King Leo), 8, 9. No dispatch, no control (EnableMove ip453 behind Bit158). Arrives with Int16[2] = 0 (62 ip1285).
- Conductor e4 t1 SWITCHEX ip23: 0..8 then 100..110 on Map.Bit[231].
- Pages [Confirm]: **98** King Leo "Thou hast not seen the last of me, Marcus!" (e6 t1 stage 2: WindowAsync ip270 +
  WaitWindow ip281), **100** Blank "Consider this, [ZDNE]! If Prince Schneider..." (e21 t1 stage 6: ip386 + WaitWindow
  ip407), **101** Zidane "'Tis foolishness!..." (e14 t1 stage 7: WindowSync ip893). Self-closing: 96 `[TIME=15]` WindowSync
  e6 ip170, 97 `[TIME=15]` e14 ip621/627, 99 `[TIME=20]` e14 ip759/779, 103 "Aha!" `[TIME=10]` x3 (e14 ip1425/1818/2324),
  104 "Mph!" `[TIME=10]` (e21 ip1046).
- **`Byte[8]:=125` e14 t1 ip805** (stage 5, after 99). camIdx reads (e13/e20 t1 `B_SYSVAR[1]==1`) pick SetObjectFlags only.
- Exit stage 110 e4 t1 L666: DisableMove ip696, PreloadField(5,64) ip718, FadeFilter ip760, op_22(25), Bit162/163 empty,
  **`Int16[2]:=100` ip820**, **`Field(64)` ip828** (31213: not retargeted -> real 64 on both sides).

## END: arrival in 64 A. Castle/Public Seats (fbg_n02_alxc_map038a_ac_ast_1; text block 2)
First row `Bit[191]:=0` at 64 e0 t0 ip22: the cut. Its Main_Init then writes the same ambient values, `Bit[3815]:=0` ip416,
`Byte[475]:=0` ip425 (both already 0), `Byte[8]:=125` ip475 (already 125): the end state is stable through it.

## SC ladder
SC arrives 1155 (115 e1 t1 ip1683, O2's last write). **61, 62 and 63 neither write nor read `Global.UInt16[0]`** (0 stores,
0 reads in each listing): O3's ladder is empty, `sc_writes: 0`. The next store is O4's: **1190 at 150 e3 t1 ip1966 (L1708)**,
stage 10, after `UInt16[21]:=1` ip1136, guard ip1884 `SC>1190` false (the debug overwrite ip1952 + window 55 sit behind it).
The census finds no SC store with a value 1156..1189 in any stock field.

## FieldEntrance chain
0 (start; 61 never reads it) -> 100 (61 e1 t1 ip363) -> 0 (62 e4 t1 ip1285, before the battle) -> 100 (63 e4 t1 ip820).
62 ip1345 is NOT on the route (the battle abandons 62).

## Expected story keys, in order (S side; F identical in donor terms) - 33 field rows + battle noise
| field | sid tag | ip (L) | key |
|---|---|---|---|
| 61 | e0 t0 | 22 (16), 49 (43), 57 (51), 119 (113), 138 (132), 200 (194) | Bit191:=0, Bit184:=0, Int16[9]:=-1, Byte13:=0, Int16[11]:=-1, Byte14:=0 |
| 61 | e2 t1 | 752 (637) | Byte[8]:=125 (after FMV003 and pages 72-78) |
| 61 | e1 t1 | 363 (352) | Int16[2]:=100 (exit) |
| 62 | e0 t0 | 26, 53, 61, 123, 142, 204 | the same six ambient keys |
| 62 | e4 t1 | 319 (308) | UInt16[21]:=3585 |
| 62 | e4 t1 | 603 (592); 637 (626), 659 (648), 681 (670), 703 (692) | Byte[303]:=0; ++ x4 (=1,2,3,4) |
| 62 | e4 t1 | 1034 (1023), 1085 (1074), 1093 (1082), 1101 (1090) | Byte[4]:=0, Byte[4]:=0, Byte[17]:=0, Byte[18]:=1 |
| 62 | e4 t1 | 1285 (1274) | Int16[2]:=0, then Battle(0,338) ip1293 |
| (338) | AI e1 t1 | [539] | Byte[206]:=SYSVAR[0], many (noise) |
| 63 | e0 t0 | 22, 49, 57, 119, 138, 200 | the same six ambient keys |
| 63 | e14 t1 | 805 (330) | Byte[8]:=125 |
| 63 | e4 t1 | 820 (809) | Int16[2]:=100 (exit) |
Forbidden (diagnostic): any 61/62/63 error-path row above; 62 e4 t1 ip1345 (would mean the battle returned to 62).
Not gEventGlobal: Cinematic, SetPartyReserve/RemoveParty/PARTYADD, SetCharacterData, SetName, SetHP/SetMP/CureStatus.

**End state at arrival in 64:** SC 1155; Int16[2] 100; UInt16[21] 3585; Byte[303] 4; Byte[4] 0; Byte[17] 0; Byte[18] 1;
Byte[8] 125; Byte[13] 0; Byte[14] 0; Int16[9] -1; Int16[11] -1; Bit[191] 0; Bit[184] 0; Byte[206] random (exclude).
Untouched (start values; 0 after a raw warp): Byte[6], UInt16[19], Byte[472], Int16[469], Bit[3717], Bit[3718].

## Choices
None in 61-63 (no SYSVAR[9] read, no `[CHOO]` text). The only possible one is the skip-movie dialog, which opens only on a
Confirm during FMV003 (FieldHUD.cs:275-286): `Localization.Get("SkipMovieDialog")` = System.strings "SkipMovieDialog0366"
`[STRT=110,4][PCHC=2,1][IMME][FEED=5]Do you want to skip\n[FEED=5]the movie?\n[CHOO][FEED=14]Yes\n...`, cursor
`ETb.sChoose = 1` (No). The driver presses only on pages and none is up during the movie. Keep O1's
`{None, "want to skip", default}` as a net; its published form is unmeasured (a prompt published empty would VOID V1).

## Nondeterminism
1. Battle 338's Byte[206] (random value and count) - registered noise.
2. Battle length (damage rolls until King Leo has lost 186): no story write depends on it.
3. Start: Byte[13] at the warp (1 measured; 2 would open the error page and add ip97/ip349 rows) - O3-START clause.
4. FMV003 skip dialog (only on a stray Confirm). 5. leave_battle's Confirms can land on 63's first windows (96/97 TIMED,
   98 the first page): no choice in 63, no story effect. 6. No control, regions, ATEs, encounters, timers, naming or
   minigame anywhere in 61-63 (no EnableMove reachable, no SetRegion/InitRegion, no ATE/encounter opcode, no key read).

## Start state (raw warp, O2's mechanism) - zero START-DEPENDENT keys over this segment
New Game, `storytrace 1`, then in field 70 `warp 61 0 1155` (S) / `warp 31211 0 1155` (F). Residue: SC bytes 0 (0->131)
and 1 (0->4); FieldEntrance 0 -> 0 writes no row. Reads before writes in 61-63: Byte[13] (1 vs 3 at a true O2 end: both
`:=0` ip119), Byte[14] (0/0), Bit[184] (0/0). UInt16[21] and Byte[303] are written before read (62 ip319, ip603). The party
(not gEventGlobal) is [Zidane] after the warp vs [Vivi] at a true O2 end; 62 e4 t1 rebuilds both to [Zidane, Cinna, Marcus,
Blank]; PARTYCHK(5) is false either way. Battle 338 reads gEventGlobal[16..18] (battle.cs:38-40): Byte[16] 0 in both starts,
17/18 written by 62. 63 reads nothing global. Pokes (option b) are unnecessary here; the story seed (c) is unsuitable
(owner-gated hub + re-wire, non-stock rows before 61, no channel for UInt16[19]/Byte[6]).

## Disputes settled (reader claims vs the bytes)
1. **End.** Bytes reader: candidate 3 (150 -> 153, SC 1190). Data reader: candidate 1. Chosen 1 (section 1); the bytes
   reader's fallback "fresh 61-63 copies" breaks the battle return (DataPatchers.cs:148-160).
2. **Battle 338's result.** Bytes: 2 (by analogy with O1). Data: 1 (with pose, result screen). BYTES: scene flags 0x1839
   carry 0x10 -> WinPose false (BTL_SCENE.cs:222) -> btl_scrp.cs:785-797 maps (33,1) to 2. Keep won [1,2].
3. **Battle 338's end condition.** Bytes: the party-HP count, true at once (HP 9999). Data: King Leo's HP <= 10000.
   BYTES: SYSLIST[1] = the running object (EBin.cs:178-183, EventEngine.cs:985-994); entry 1 = King Leo (10186): 186 damage.
4. **After the battle.** Both route readers: 62's Main_Reinit, `Int16[2]:=0` ip1345, `Field(63)` ip1353. BYTES + engine:
   TH_E002 [265] RunBattleCode(37,63) -> 63 loads fresh; ip1298-ip1353 never run (the gates reader had it right).
5. **Tutorial/result screen.** Data: confirm a tutorial. BYTES: no tutorial for 338 (battle.cs:100); fight() leaves the result.
6. **Run time of candidate 1.** Bytes 7 min, data 5.5. Estimate ~6 (FMV003 84.8 s file); measure in the rehearsals.
7. **(O4) 64's 105/106 and 107/108.** Bytes: e13 waits for the Confirm+Special RELEASE (ip868). BYTES: `JMP_IF` loops while
   `!KEYON(Confirm) && !KEYON(Special)` (ETb.KeyOn = sKeyOn, the press edge): it waits for a PRESS, then closes both
   windows; the same at ip1404 (107/108, missed by both) and 150 e2 t1 ip538 (98/99, missed by both).
8. **(O4) 64's round timer.** Bytes: 50 always. Data: 30 once a streak exists. BYTES: Int16[36] is only ever set to 0
   (e13 t1 ip722/ip1010) or clamped to 1 (e20 L1394-1405); `Byte[52]:=30` (e20 L634) never runs: 50.
9. **(O4) 64's encore choice rule.** Data: match "fight scene again" (the prompt). Bytes: match the option. Lesson 1: the
   prompt may publish empty and pick_for matches `match` against [prompt, *lines]: rule `{64, "No" -> "No"}`.
10. **(O4) SC 1190's site.** Start reader: ip1952. Route readers: ip1966. BYTES: ip1966 (L1708) on the route; ip1952 is
    the debug overwrite behind `SC>1190` + a Start press.
11. **(O4) 150's pages.** Bytes: 13 CONFIRM (98/99 SCRIPT). BYTES: 13 Confirm pages + one KEYON press closing 98/99.
12. **(O4) Text block of alxc members.** Gates reader: keep each alxc member on block 3. BYTES (EVENT_ID_TO_MES): 64, 68,
    69 are block 2; 150-167 block 3. A verbatim fork keeps its donor's own block.
13. **alxc size.** Bytes 95 by FBG token; data 94 (the whole-zone dry run omits 1805). Both true in their frame.

## Harness gaps for O3 (see the structured result for status/evidence)
Gap: the beat-table driver VOIDs on any battle (segment_drive.py:1113-1117) -> a `battles` registry
`[{donor 62, sc 1155, scene 338, won [1,2], beat "battle"}]` calling `fight(finish=True)`; the coverage check reads a
per-battle won set. Gap: FakeGame needs a battle beat whose exit is another field (cmd 37) and the FMV skip dialog.
Risks: the skip dialog's published text; no_progress_s (120 s) against FMV003 (~85 s); recovery (soft reset) from inside
a battle is unmeasured; leave_battle's late Confirms. Ready: pages, the end, the raw-warp start (+ O3-START clause), no
control anywhere (an empty table: any control is V4). O4-only: the Chanbara hold rule (+ SwordplayAssistance != 2
preflight), revisit keying, Steiner's radius, facing gates, NPC talks.

## Fork gates and the chain
No new import or deploy. 31211 (61, retarget {62=31212}) differs from stock only at abs 1105-1106 (Field(62)'s arg),
31212 (62, retarget {63=31213}, dead on the route) only at abs 3175-3176, 31213 (63) is byte-identical. The battle's
after-field goes through s24: live FF9CustomMap ForkDonorPatch rows `31212 62` / `31213 63`; no other folder ships a
ForkDonorPatch; the only duplicate donors are Dali 312/350-359. Visual-only raw gates: PSXCameraAspect.cs:47 row [63,0,320].
Text: the live block 2 (written 2026-09-29 21:06) ships the US text as UK too (us == uk, md5 ddf99c96 = stock US): a
global block, so both sides see it; the fork dir was refreshed later (2026-09-30 10:45) and never redeployed.

## Beyond the end (O4 preview, verified in the bytes)
- 64 Main_Init ip232 `SWITCHEX(L402, 327, 315, 322)`: entrance 100 -> default: Map.Byte[24]:=1, `Bit[3815]:=0` ip416,
  `Byte[475]:=0` ip425, InitCode 4/3, InitObject 5, 6, 13 (Zidane), 20 (Blank), `Byte[8]:=125` ip475. No control.
- e2 t1 SWITCH(1, ...) ip23: 1->2->3->4->5->6->(Map.Byte[27] 0->7, 1->9); 7->8->3 (fight again); 9 exit. Stage 2: 105/106
  (`[INCS][TIME=-1]`), e13 waits <=250 frames or gMesSignal>=2, then a Confirm/Special PRESS (ip868), closes, tutorial
  **111** WindowSync(6,0,111) [Confirm]. Stage 3: 50 iterations (Map.Int16[34]; prompts only while <49): prompt
  `Map.Byte[46]:=SYSVAR[0]&7`, `Byte[52]:=50`, "Press X!" 112-119 (WindowAsync(1,160,n), `[TIME=-1]`); e3 t1 polls B_KEYON
  per button (Cross 0x4000 is what Confirm also sets in the default layout, EventInput.cs:522-531); timeout -> miss.
  Stage 4: 107/108, a Confirm/Special press (ip1404). Stage 6 e4 t1: score `(Int16[30]+Int16[32])/29` ip208, the
  EMinigame hook at sid 4 ip223 (+30% at SwordplayAssistance 1; live Memoria.ini:252 = 1; 2 would refill the timer and
  never end a no-press fight), clamp 1..100, **`Byte[475]:=score` ip338** (if larger), 120/121 [Confirm x2] (or 122/123 +
  **`Bit[3815]:=1` ip390** on a 50-combo), choice 124-127 (score <25 -> 124) SYSVAR[9] ip476, No -> `Map.Byte[27]:=1`
  ip509, 128 "They shower you with N Gil!" ip531, AddGil. No-press policy: score 0 -> 1, Byte[475]=1, gil 1.
  Stage 9: **`Byte[8]:=0` ip331**, **`Int16[2]:=325` ip528**, **`Field(150)` ip536**.
- 150 at 325: no control (e2 t0 SWITCH(5,..) default: DefinePlayerCharacter only); `Byte[8]:=25` ip331; pages 90, 91, 92,
  93-97, [98+99 by one KEYON press, e2 t1 ip538], 100, 102, 103, 104, 106; stage 10: **`UInt16[21]:=1` ip1136**,
  **`Byte[303]:=0` ip1221, ++ ip1255** (=1; ip1277/1299/1321 behind const(0)), **`Byte[4]:=0` ip1652, ip1667**,
  **`Byte[17]:=0` ip1675**, **`Byte[18]:=1` ip1683**, **SC:=1190 ip1966**, **`Byte[8]:=75` ip1974**, **`Int16[2]:=325`
  ip2161**, **`Field(153)` ip2169**. Fork gate EventEngine.cs:682 (no autosave at 150/1155/325; not trace-visible).

## Could not determine / unverified
FMV003's on-screen length and SYSVAR[14]'s frame unit (when 61 resumes); the harness's published result for 338 and the
fight's length (186 damage); the cmd-37 landing on the stock side under the trace (code-read; in-game for a fork only);
whether the skip dialog's prompt publishes; soft reset from inside a battle; per-run time. O4 preview items are code-read
only (no-press scoring, the Confirm=Cross mapping under injected input, 124's publication). Beyond 153: survey only.
