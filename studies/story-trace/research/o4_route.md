# Stock O4 route: raw warp into 64 (FieldEntrance 100, SC 1155) -> the sword fight -> 150 -> Field(153), SC 1190  (reconciled)

The reconciler's own decode, independent of the six readers' outputs. Every ip below was decoded from the stock US
`.eb` by `reconcile/ebtool.py` (storytrace.stock_script_source + ScriptIndex + instruction_stores, the story-trace-o4
worktree = master 5d1b95a6) and checked against the listing; every engine claim was re-read in C:\gd\FFIX\Memoria.
- `ip` = abs - entry code start = the s88 trace ip (the trace latches `Obj.ip` at the opcode byte, StoryTrace.cs:249-255;
  EMinigame's `s1.ip == 223` is the same frame). `Lnnn` = offset from the function start.
- Listings `reconcile/L{64,150,151,153,154}.txt` are byte-identical (cmp) to the bytes, data, chanbara and O3 listings:
  no reader decoded different bytes. Texts: `reconcile/mes_64.json` (block 2), `mes_150.json` (block 3), US.
- `SWITCH(base, default, case_base, case_base+1, ...)`; `SWITCHEX(default, value, target, ...)`.
- Engine: the live source is the deployed engine (x64/x86 Assembly-CSharp.dll sha256 ba9762423da8f3d7 = Output;
  no Assembly-CSharp `.cs` is newer than the build).
- Notes, measurements and arithmetic: `reconcile/notes.txt`.

## Segment end: CHOSEN = arrival in 153 (150 e3 t1 ip2169 `Field(153)`, FieldEntrance 325, SC 1190)
| # | exit (stock) | arrival | SC | est. min a run | new members | inside |
|---|---|---|---|---|---|---|
| 1 | 64 e2 t1 ip536 `Field(150)` (`Int16[2]:=325` ip528) | 150, ent 325 | 1155 | ~2 | member(64) | the sword fight, choice 127, 4 pages (111, 122, 123, 128), 2 KEYON pairs |
| **2 CHOSEN** | 150 e3 t1 ip2169 `Field(153)` (`Int16[2]:=325` ip2161) | 153, ent 325 | **1190** | **~3** | member(64), member(150) (+153 as the landing) | + 13 pages, 1 KEYON pair, SC 1190, party -> Zidane |
| 3 | 153 e3 t1 ip3158 `Field(154)` (304, ip3150) | 154 | 1190 | ~6 | + member(153) | + the first CONTROL (e3 t1 ip785, stairs to f[1] <= -450), choice 128 (Bit[3795]), 2 KEYON pairs, regions 26/27/28 |
| 4 | 154 e2 t1 ip1528 `Field(153)` (316, ip1520) | 153 @316 | 1190 | ~7 | + 154 | Zorn & Thorn (survey) |
| 5 | 153 e18 t1 ip1085 `Field(151)` (110, ip1077) | 151 | 1190 | ~8 | (153 again) | survey |
| 6 | 151 e2 t1 ip940 `Field(153)` (328, ip932) | 153 @328 | 1190 | ~10.5 | + 151 | Steiner naming Menu(1,3) e3 t1 ip603; Byte[6]\|=8 ip610 START-DEPENDENT |
| 7 | 166 e6 t1 ip871 `Field(55)` (110, ip863) | 55 (tshp) | 1190 | 25-30 (graph only) | the whole disc-1 cluster | 2 control phases, 9 doors, FMV004; UInt16[19]\|=8 START-DEPENDENT |

Run times are estimates from the bytes (no stock run of 64/150 exists), calibrated on two measurements: 64's stage 1
lasts 1.83 s (story-o3's ring, run 6: field 64 at frame 83049, window 105 at 83152), and O3's runs took 231-241 s
(o3_session.json). 64 ~70 s (1.8 s walk-in, ~3 s for 105/106, the 111 page, the fight ~51 s, ~3 s for 107/108, ~2 s
walk-off, ~5 s of pages and the choice, a 65-tick fade); 150 ~65 s (~7 s of self-closing lines and fade, 13 pages
with their animations, one KEYON pair, the package toss, stage 10's walks and `Wait(90)`); start and end ~20-30 s.

Why 2 (both route readers' recommendation; the PLAN pointer's "first end"):
- **The owner's requirement and the SC ladder in one run.** It holds the whole sword fight and the encore choice, the
  zone's first SC write (1155 -> 1190, 150 e3 t1 ip1966) and the party rebuild (UInt16[21], Byte[303], Byte[4], [17],
  [18]). Candidate 1 is ~1 min shorter but writes no SC and stops before the rebuild.
- **Run time.** ~3 min a run (less than O3's measured 4): a session of 6+ runs is ~20 min. The readers' 5 and 6.5 min
  assumed 60-80-tick passes; the bytes arm each prompt BEFORE the previous result's reaction (e20 t1 ip721-852 vs
  ip861-1370), so a pass lasts max(reaction, response) ~ 30 ticks (dispute 2).
- **One new driver feature.** No control, battle, FMV, naming, ATE or encounter anywhere in 64@100 or 150@325
  (opcode inventory; 64's EnableMove e0 t0 ip936 sits behind Map.Bit[158], set only by e16 t0 at 315/322; 150's
  e2 t0 sets it only at entrance 5; 150's region exits e18/e19 t2 start with `SYSVAR[2]` (control) and RET without it).
  Pages and KEYON pairs are O1-O3's proven rule 7; the only new things are the Chanbara rule and choice 127.
- **Nondeterminism inside is closed by the 100 policy** (the prompts are random; a 49/49 run writes the same keys).
- Candidate 3 adds the first alxc control grant (positions need rehearsals: lesson 6), region hazards (26/27 side
  scenes, 28 the back door) and choice 128: O5's start, by a raw warp into member(153) at 325 with SC 1190.

## The member set (fork side)
The alxc disc-1 cluster, as O2 forked alxt's: `import-chain 64 --verbatim --ids 64,68-69,150-151,153-167 --fresh-ids
--id-base 31240 --name-prefix O4` (20 members; 152 is Evil Forest, not alxc). Expected member(64)=31240,
member(150)=31243, member(153)=31245 if the ids sort ascending as O2's did (o2_forks.json) -- read them from the written
campaign.toml. Member(64)'s `Field(150)` (ip536) and member(150)'s `Field(153)` (ip2169) are retargeted, so **F ends in
member(153) against real 153 on S**, judged in donor terms; a real-153 landing on F is a finding (an un-retargeted
Field()). PreloadField operands are not remapped (O3: 31211 differs from 61 only in Field()'s operand): harmless.
Free band: the live DictionaryPatch of every stacked folder registers no FieldScene above 31237 (FF9CustomMap 31100-31114,
31200-31237); ForkDonorPatch exists only in FF9CustomMap, with no alxc donor (duplicates only 312, 350-359). Re-read
before minting. Text: 64/68/69 keep block 2, 150-167 block 3 (blocks are GLOBAL: see the fork gates).

## Ambient prologue (every field's e0 t0; the O3 table's shape)
`Bit[191]:=0`, `Bit[184]:=0` (both masked story noise: flags.story_noise_bits), `Int16[9]:=-1`, Byte[13] (==9 -> no write;
==2 && Int16[9]<0 -> `:=9`; Int16[9]<0 -> `:=0`), `Int16[11]:=-1`, Byte[14] likewise. `Int16[2]:=10000` sits behind
`Bit[184]==1` (never). A Byte[13]/[14] of 9 opens the debug window "Error Env Play() Slot=" and then writes `:=0`.
| field | Bit191 | Bit184 | Int16[9] | Byte13:=0 | Int16[11] | Byte14:=0 | error path (must not fire) |
|---|---|---|---|---|---|---|---|
| 64 | ip22 | ip49 | ip57 | ip119 | ip138 | ip200 | ip97/ip178 (:=9), window 3 ip835/ip869, ip845/ip879 |
| 150 | ip26 | ip53 | ip61 | ip123 | ip142 | ip204 | ip101/ip182, window 56 ip999/ip1033, ip1009/ip1043 |
| 153 (cut) | ip22 | | | | | | |
Incoming Byte[13] after New Game + the raw warp: 1 (measured in all 12 O2/O3 runs; 70 e0 t0 ip130), so 64 takes ip119.
A warp after FMV001's tail (70 e0 t0 ip475 `:=2`) would take ip97 and stop on window 3: O4-START requires ip119.

## 64 A. Castle/Public Seats (EVT_ALEX1_TS_SWD_BTL, fbg_n02_alxc_map038a_ac_ast_1, text block 2)
- Main_Init e0 t0: ip232 `SET(Int16[2])`, ip236 `SWITCHEX(L402, 327, L246, 315, L317, 322, L317)`: entrance 100 takes
  L402: ip408 `Map.Byte[24]:=1`, **ip416 `Bit[3815]:=0`**, **ip425 `Byte[475]:=0`** (both zeroed on every arrival),
  InitCode(4) ip434, InitCode(3) ip437, InitObject 5, 6 (swords), 13 (Zidane: DefinePlayerCharacter e13 t0 ip279),
  20 (Blank) ip440-449, **ip475 `Byte[8]:=125`**. SC is read once (ip526 `SC<1900`: tile animations). No control.
- Tick order: e0, e1, e2, e4, e3, e5, e6, e13, e20 (each new Obj is appended to the active list, Obj.cs:31-45;
  EBin.ProcessCode walks it once a tick, EBin.cs:106-160). So **e3 (the key poll) runs before e20 (the prompts)**.
- Conductor e2 t1 ip23 `SWITCH(1, L894, ...)` on Map.Byte[24], advanced by Map.Bit[231] (each actor counts Byte[26]
  down, raises Bit[230] while waiting; e2 clears Bit[230] at the top of every pass, ip11):
  1 -> 2 (ip74), 2 -> 3 (ip134), 3 -> 4 (ip194), 4 -> 5 (ip224), 5 -> 6 (ip254), 6 -> `SWITCH Map.Byte[27]`:
  0 -> 7 (ip298, fight again), 1 -> 9 (ip309); 7 -> 8 (ip104), 8 -> 3 (ip164); 9 = the exit (L320).
- Stage 1: walk-in (e13 t1 ip514 `Walk(-435,-14425)`, e20 t1 ip151 `Walk(35,-14425)`, MoveCamera e13 ip499):
  MEASURED 1.83 s from the field's first published frame to window 105 (story-o3 run 6 ring).
- Stage 2: e20 `Wait(3)`, **105** "Blank / En garde!" `WindowAsync(1,128,105)` ip303; e13 zeroes every minigame Map var
  (ip690-802), `SetDialogProgression(0)` ip810 (gMesSignal := 0), `Wait(15)`, **106** "[ZDNE] / Expect no quarter from
  me!" `WindowAsync(0,128,106)` ip816, both `[INCS][TIME=-1]` (button-inhibited: Confirm cannot page them,
  DialogBoxSymbols.cs:811-826). e13 waits while `SYSVAR[8] < 2 && Byte[29] > 0` (Byte[29] from 250; ip825-859; each
  `[INCS]` raises gMesSignal once its text has typed out, :833-866), then loops each tick while `!KEYON(0x20000) &&
  !KEYON(0x80000)` (ip865-885): a Confirm/Special PRESS EDGE after the wait closes both (ip888/891); one made before the
  loop is lost. `Wait(5)`, **111** the tutorial `WindowSync(6,0,111)` ip900 (an ordinary page), `Wait(10)`, sync.
- Stage 3: THE SWORD FIGHT (its own section below).
- Stage 4: e20 `Wait(25)`, **107** "Blank / We shall finish this later!" ip1618; e13 `CloseWindow(6)`, `Wait(37)`, **108**
  "[ZDNE] / Come back here!" ip1352, the same INCS/250 wait (ip1361-1395), KEYON loop ip1404, close ip1424/1427.
- Stage 5: walk-off to x 1400 (e13 t1 ip1513, e20 t1 ip1701), camera e4 t1 ip136-205.
- Stage 6 (e4 t1 L186): the score, **ip338 `Byte[475]:=score`**, pages 122/123 + **ip390 `Bit[3815]:=1`** (or 120/121),
  `Wait(10)`, the encore choice 124-127 (ip402-462), `SYSVAR[9]` ip476; No -> ip509 `Map.Byte[27]:=1`, `Wait(15)`, sound,
  **128** "They shower you with [NUMB=1] Gil!" ip531 (a page), `AddGi(Int16[50])` ip537, Bit231 ip542.
- Stage 9 (e2 t1 L320): **ip331 `Byte[8]:=0`**, Map.Bit[158]:=0, DisableMove ip404 (Bit159 is 1 from Main_Init ip887),
  DisableMenu ip416, PreloadField(5,150) ip426, FadeFilter(6,64) ip468, `Wait(65)` ip478, **ip528 `Int16[2]:=325`**,
  **`Field(150)` ip536**.
- 64 has 25 store sites (all classified): on route ip22/49/57/119/138/200/416/425/475, e4 t1 ip338/390, e2 t1 ip331/528;
  error/dead ip41, ip97, ip130 (dead: ip57 makes Int16[9] negative first), ip178, ip211, ip295 and ip380 (entrances
  327/315/322), ip845, ip879; off route e2 t1 ip893 (327's exit to 67), e11/e12 t2 ip193 (315/322's regions).

## 150 A. Castle/Guardhouse (EVT_ALEX1_AC_GUARD, fbg_n02_alxc_map042_ac_gdr_0, block 3)
- Main_Init e0 t0: ip238 `SET(Int16[2])`, ip242 `SWITCHEX(L515, 325, L248, 5, L352, 10000, L403)`: 325 -> ip258
  `Map.Byte[24]:=0`, InitObject 2 (Zidane), 3 (Blank), 5, 6, 9, 4 (the package), InitRegion 18, InitCode 17, **ip331
  `Byte[8]:=25`**. No control: e2 t0 `SWITCH(5, L94, L12)` (ip22) takes L94 at 325 (DefinePlayerCharacter ip144 only;
  Map.Bit[158] stays 0, so EnableMove ip1100 is skipped); region 18's tag 2 RETs without control (e18 t2 ip30).
- Conductor e0 t1 ip1179 `SWITCH(0, L532, ...)`: 0 -> 1 -> ... -> 10 on Bit231; 10 -> 17 (ip1530, harmless: e2's
  stage-10 walk raises Bit231 while e3 is already inside its stage-10 code).
- Stage 0 (e3 t1 ip290-425): 85-88 `[TIME=20]`, 89 `[TIME=60]` (self-closing; Confirm does nothing to them), waits of
  130 ticks, fade-in. Then pages (each closed by one Confirm):
  **90** e3 ip444 WindowSync (stage 1); **91** e2 ip404 WindowSync (2); **92** e2 ip435 + WaitWindow(0) ip463 (3);
  **93-97** e3 ip461/524/587/650/713, each + WaitWindow(1) ip485/548/611/674/737 (4); then **98** e3 ip794
  `[INCS][TIME=-1]` stays up; stage 5: **99** e2 ip480 `[INCS][TIME=-1]`, the INCS/250 wait ip495-529, **KEYON
  ip538** closes 98 and 99 (ip558/561); **100** e2 ip571 + WaitWindow ip586; **102** e3 ip864 WindowSync (6, then the
  package toss on Map.Byte[49]); **103** e2 ip601 + WaitWindow ip617 (7); **104** e3 ip1002 + WaitWindow ip1018 (8);
  **106** e3 ip1072 WindowSync (9). 13 pages + 1 KEYON press.
- Stage 10 (e3 t1 L878): **ip1136 `UInt16[21]:=1`**, SetPartyReserve, RemoveParty x12, PARTYADD 0 ip1185 (party
  [Zidane]); **ip1221 `Byte[303]:=0`**, **ip1255 `Byte[303]++`** (=1; ip1277/1299/1321 sit behind `const(0)`);
  B_CURHP checks; `PARTYCHK(5)` ip1632 false -> **ip1652 `Byte[4]:=0`** (ip1641 `:=1` = Quina present, forbidden);
  SetCharacterData(0,1,255,9,0); **ip1667 `Byte[4]:=0`**, **ip1675 `Byte[17]:=0`**, **ip1683 `Byte[18]:=1`**; SetHP 9999 /
  SetMP 999 / CureStatus; RunScriptAsync(4,17,13), walks, `Wait(90)` ip1881; ip1884 `SC>1190` false -> **ip1966
  `SC:=1190`** (L1708; ip1952 is the debug overwrite behind the guard, window 55 and a Start press); **ip1974
  `Byte[8]:=75`**; DisableMove ip2037, DisableMenu ip2049, PreloadField(5,153), FadeFilter(6,24), `Wait(25)`, **ip2161
  `Int16[2]:=325`**, **`Field(153)` ip2169**.
- 150's store sites, classified: route e0 t0 ip26/53/61/123/142/204/331 and e3 t1 ip1136/1221/1255/1652/1667/1675/
  1683/1966/1974/2161; error ip45, ip101, ip134, ip182, ip215, ip1009, ip1043; other entrances ip497, ip609; dead
  ip1277/1299/1321; forbidden ip1641, ip1952; control-only or not instanced at 325: e10 t3 (moogle), e15/e16 t1,
  e18 t2 ip90/242/378, e19 t2 ip90/334, e23. Autosave: none at 150 (EventEngine.cs:682, wrapped; not traced).

## END: arrival in 153 A. Castle/Hallway (EVT_ALEX1_AC_H2F, fbg_n02_alxc_map041a_ac_h2f_1)
Cut at 153's first row, e0 t0 ip22 `Bit[191]:=0` (S: real 153; F: member(153)). 153's dispatch (ip251 `SET(Int16[2])`,
ip255 `SWITCHEX(L1098, 325, L273, 5, L438, 328, L603, 316, L799, 3, L951)`) and `SC>1900` (ip232) are past the cut.

## SC ladder
| value | where | when |
|---|---|---|
| 1155 | the warp's residue in field 70 (bytes 0 and 1: 0 -> 131, 0 -> 4) | O4's start. 64 reads SC once (ip526) and never writes it; 150 holds it through stages 0-9 |
| **1190** | **150 e3 t1 ip1966 (L1708)** | stage 10, after the rebuild and `Wait(90)`, guard ip1884 false. The segment's only SC write |
No stock field stores an SC value in 1156..1189 (O3's census). The next step is 1400 at tshp 55 (outside O4).

## FieldEntrance chain
100 (the warp's residue, byte 2: 0 -> 100) -> 325 (64 e2 t1 ip528) -> 325 (150 e3 t1 ip2161, same value).

## Expected story keys, in order (S side; F identical in donor terms)
| field | sid tag | ip (L) | key |
|---|---|---|---|
| 70 | warp residue | | SC bytes 0 (0->131), 1 (0->4); FieldEntrance byte 2 (0->100): exactly 3 rows, set aside by the front cut |
| 64 | e0 t0 | 22 (16), 49 (43) | Bit191:=0, Bit184:=0 (masked story noise) |
| 64 | e0 t0 | 57 (51), 119 (113), 138 (132), 200 (194) | Int16[9]:=-1, Byte13:=0 (old 1), Int16[11]:=-1, Byte14:=0 |
| 64 | e0 t0 | 416 (410), 425 (419), 475 (469) | Bit3815:=0, Byte475:=0, Byte8:=125 |
| 64 | e4 t1 | **338 (316)** | **Byte475:=100** (0 -> 100; only a perfect-speed run writes 100) |
| 64 | e4 t1 | **390 (368)** | **Bit3815:=1** (only when max combo Int16[42] == 50, i.e. all 49 prompts hit) |
| 64 | e2 t1 | 331 (320), 528 (517) | Byte8:=0, Int16[2]:=325 (chain) |
| 150 | e0 t0 | 26, 53 | Bit191, Bit184 (masked) |
| 150 | e0 t0 | 61, 123, 142, 204, 331 (321) | Int16[9]:=-1, Byte13:=0, Int16[11]:=-1, Byte14:=0, Byte8:=25 |
| 150 | e3 t1 | 1136 (878), 1221 (963), 1255 (997) | UInt16[21]:=1, Byte303:=0, Byte303++ (=1) |
| 150 | e3 t1 | 1652 (1394), 1667 (1409), 1675 (1417), 1683 (1425) | Byte4:=0, Byte4:=0, Byte17:=0, Byte18:=1 |
| 150 | e3 t1 | **1966 (1708)**, 1974 (1716), 2161 (1903) | **SC:=1190**, Byte8:=75, Int16[2]:=325 (chain) |
| 153 | e0 t0 | 22 (16) | the cut |
26 compared keys a run (23 writes + 1 SC + 2 chain) beside 4 masked rows. Forbidden (diagnostic): every error-path,
dead and off-route site listed above; a second ip390 or ip338 row (a replay after "Yes"); an ip338 value other than 100.
Not gEventGlobal: party ([Zidane] after 150 ip1185), gil (AddGi +10000 at a score of 100: 500 -> 10500), SetCharacterData,
HP/MP/status, the Encore achievement, every minigame Map var.

**End state at arrival in 153:** SC 1190; Int16[2] 325; UInt16[21] 1; Byte[303] 1; Byte[4] 0; Byte[17] 0; Byte[18] 1;
Byte[8] 75; **Byte[475] 100; Bit[3815] 1**; Byte[13] 0; Byte[14] 0; Int16[9] -1; Int16[11] -1; Bit[191] 0; Bit[184] 0.
Untouched (0 after the raw warp): Byte[6], UInt16[19], Byte[206], Int16[469], Byte[472], Bit[3717], Bit[3718].

## Choices
- **127** (64 e4 t1 ip462 `WindowSync(5,0,127)`, the one a 100 shows): `[PCHC=2,1][IMME]They demand an encore!\nPerform the
  fight scene again?\n[CHOO][MOVE=18,0]Yes\n[MOVE=18,0]No`. 124 (<25 "booing"), 125 (<50), 126 (<75) have the same
  options. **The cursor opens on Yes (absolute 0)**: PCHC's second parameter is the CANCEL choice (DialogBoxSymbols.cs
  :671-678 `DefaultChoice = ETb.sChoose`, `CancelChoice = preTag.IntParam(1)`), and the flags-0 WindowSync resets
  `sChoose` to `sChooseInit` = 0 (ETb.cs:100-104); 64 has no SetChooseParam opcode (DoEventCode.cs:1967). (The skip
  dialog's cursor is on No only because FieldHUD.cs:280 sets `ETb.sChoose = 1` for it.) Cancel moves the cursor to No
  without confirming (Dialog.cs:810-826). `SYSVAR[9]==0` (Yes) replays the whole fight (stages 7, 8 with 110/109 and a
  KEYON press, 3, 6 again: a second ip390 row on another perfect). **Pick No (absolute 1)**: rule `{donor 64, sc [1155],
  match "No", pick "No", once: true}`, answered by `g.choose(1)` (steers the published cursor; proven on 52's option 1
  in O1); never `take: "default"` (it would be V3) and never the default. Expected publication (unmeasured; lesson 1):
  options `[<prompt or ''>, 'es', 'No']`, active [0, 1], selected 0. If R-CHANBARA shows the No line short its first
  character too, freeze `pick: "o"` (it matches only the No line in ['es','No'], ['es','o'] and ['Yes','No']).
- 128 in 153 (Let her pass / Examine her face, Bit[3795] := SYSVAR[9] at e3 t1 ip1741) is past the end. Its cursor too
  opens on option 0 ("Let her pass"): `WindowSync(0,128,128)` (e3 t1 ip1724) has flags 128 (bit 0 clear, so sChoose
  resets to 0) and 153 holds no EnableDialogChoices op -- not 1 as both route readers said.

## Battles, minigames, FMV
No Battle/SetRandomBattles/Cinematic/Menu op on the route (64@100, 150@325): the battle registry is empty (any battle
is V10), no movie policy. The one minigame is the sword fight (below).

## Nondeterminism
1. The prompt sequence: `Map.Byte[46] := SYSVAR[0] & 7` (64 e20 t1 ip462), SYSVAR[0] = `UnityEngine.Random.Range(0,256)`
   (GetSysvar.cs:13-14, Comn.cs:8-10), unseeded and unsettable. Closed by THE 100 POLICY: a 49/49 run at score 100
   writes exactly the keys above whatever the sequence. What still varies: the order, the reroll count (the RNG stream),
   Map vars (Int16[30] etc.), reaction animations, pass and fight length, gil's raw formula before the 10000 override.
2. Waits that only move timing: the 105/106, 107/108 and 98/99 type-outs (<= 250 ticks), 150's package physics
   (Map.Byte[49]), the stage-10 Byte24:=17 race, 150 e4 t1 ip285 (SYSVAR[0], a cosmetic turn).
3. The encore choice (a frozen rule answers No; a Yes adds a fight and rows).
4. Start: Byte[13] at the warp (1 measured; 2 opens window 3).
5. Outside gEventGlobal: the Encore achievement report on every 100 (EMinigame.cs:20, 34-38; Steam if authenticated).
6. No control, regions, ATEs, encounters, battles, FMV or naming on the route.

## Start state (raw warp, O2/O3's mechanism) -- zero START-DEPENDENT keys over this segment
New Game, `storytrace 1`, then in field 70 (before 70 e0 t0 ip475) `warp 64 100 1155` (S) / `warp <member(64)> 100 1155`
(F) (HarnessAgent.cs:652 -> Ff9mkDebugMenu.HarnessWarp; it needs UIState FieldHUD). Residue: exactly 3 rows (bytes 0, 1, 2).
Reads on the route all resolve the same from a true O1-O3 run and from the raw warp (start reader, checked here):
SC (64 ip526 `<1900`; 150 ip1884 `>1190`; 153 ip232 `>1900` after the cut; the 150 autosave gate EventEngine.cs:682),
Int16[2] (64 ip232 default branch; 150 ip238 325; 150 e2 t0 ip18 `==5` false), Byte[13]/[14]/Bit[184]/Int16[9]/[11]
(prologue; only the `old` of 64 ip57/ip119 differs), Byte[475] (written 0 at ip425 before ip327 reads it), UInt16[21]
and Byte[303] (written before read; the ip1136/ip1221 rows' `old`/`same` differ between starts, not between sides),
Byte[4]/[17]/[18] (no reader on the route). Bit[3815] has no reader in any stock script (the start reader's census,
census_reads.json: written at 64 ip416/ip390 only). Party: [Zidane] after the warp (ff9play.cs:73-77) vs [Zidane,
Cinna, Marcus, Blank] after a true O3 end; 64 reads no party, 150 rebuilds both to [Zidane]; PARTYCHK(5) false and
B_CURHP(0) > 0 in both. Gil 500 in both (never read on the route). First START-DEPENDENT keys: 151 e3 t1 ip610
`Byte[6]|=8` (8 vs 11) and 153@328 e32 t1 ip2206 `UInt16[19]|=8` (8 vs 1807), far past the end. Pokes (option b)
and the story seed (c) are unnecessary/unsuitable, as in O3.

## The sword fight (64 stage 3: Map.Byte[24] == 3)

### The decode (every ref 64's)
- Entry (stage 3 begins on the tick e2 sets `Byte[24]:=3`, ip134): e20 t1 L319 ip440 `Byte[45]:=99`, JMP to the loop
  test ip1546 `Int16[34] < 50`. Each PASS (Int16[34] = p, 0..49):
  - ROLL (ip451-707): `Byte[46]:=88`; repeat `Byte[46] := SYSVAR[0] & 7` (ip462) while it is 88. Filters in order:
    LEFT(0) banned at SByte[38] -1/0 (ip473/499); RIGHT(1) banned at SByte[38] 1/2 (ip525/551); DOWN(3) and UP(5) banned
    while the MAX combo Int16[42] < 10 (ip577/603); CIRCLE(6) -> TRIANGLE(2) and SQUARE(7) -> CROSS(4) while
    Int16[42] < 15 (ip629/655); a repeat of the previous prompt Byte[44] is rerolled (ip681). SByte[38] starts 0
    (e13 ip730), Left hits -- , Right hits ++ (e20 ip918/1066): on any run it stays in {0, 1}, so exactly one of
    LEFT/RIGHT is ever possible. On a perfect run: prompts 1-10 come from {LEFT or RIGHT, TRIANGLE, CROSS}; UP/DOWN
    from prompt 11; CIRCLE/SQUARE from prompt 16. The first prompt is RIGHT 1/5, TRIANGLE 2/5, CROSS 2/5.
  - ARM (only while Int16[34] < 49, ip710): `Byte[47]:=1` ip721, `Byte[44]:=Byte[46]` ip729, **TimeLeft `Byte[52]:=50`
    ip736** (the `:=30` at ip755 needs Int16[36] > 0; Int16[36] is only ever set to 0 (e13 ip722/1010) or, if >= 10,
    to 1 (e20 ip1515-1526): dead), then the prompt window `WindowAsync(1,160,112+Byte[46])` ip789-852 -- all in the
    same tick.
  - REACT to the PREVIOUS result while the new prompt is live: `RunScript(2,13,11)` ip861 (Zidane's tag 11), then
    `SWITCHEX` on Byte[45] ip870: 99 (pass 0) `Wait(30)`; 0/1 (a LEFT/RIGHT hit) a 6-tick slide + 7-frame clip +
    `Wait(22)`; 2-7 and the miss codes 10/11 a 30-frame clip (anim_frames.json), 3/5/7/11 with waits inside it.
  - WAIT (ip1376-1394) each tick while `Byte[52] > 0 && Byte[47] == 1`; then score (ip1397-1541): still 1 -> timeout:
    `Byte[47]:=3`, `Byte[46]:=11`, CloseWindow(1) (ip1408-1424); HIT (Byte[47]==2): **Int16[30] += Byte[52]**
    (ip1438), **Int16[32] += Int16[40]** (the streak BEFORE this hit, ip1456), **Int16[40]++** (ip1474); MISS (3):
    `Int16[40]:=0` (ip1490); `Int16[42] := max` (ip1498-1508); `Byte[45]:=Byte[46]` ip1534; `Int16[34]++` ip1541.
  - THE PHANTOM PASS (p = 49): no arm, so Byte[47] (2) and Byte[52] keep the 49th result: after its reaction the wait
    exits at once and the 49th hit is credited AGAIN: Int16[32] += 49, the streak and max combo reach 50.
- THE POLL, e3 t1 (ip11 `SWITCH(3, L495, L12)`: only at stage 3), once per tick (`Wait(1)` ip506) while
  `Byte[47] == 1` (ip23): for each of the eight pad bits, `KEYON(bit)`: the prompt's own -> `Byte[47]:=2`, any other ->
  `Byte[47]:=3` and `Byte[46]:=10|11`. Then `KEY(8)` (Start HELD, a level read) -> miss (ip412). Then on 2 or 3: a
  sound and **CloseWindow(1)** (ip459/484) on that tick. Then **`Byte[52]--` if > 0 (ip487-498), the hit tick included.**
- Stage 3 ends on e13 t1 ip1263 (`Int16[34] < 50` loop) -> sync -> e2 ip194 `Byte[24]:=4`. e4 t1 at stage 3 only pans
  the camera with SByte[38] (ip40-133).

### Prompts (window, text as stored, the bit e3 polls, the harness press)
| Byte[46] | mes | text (US) -- published `texts` | KEYON bit | e3 ref | harness press (Control -> physical bit) |
|---|---|---|---|---|---|
| 0 | 112 | `[IMME]Press [DBTN=LEFT][MOBI=267] ![TIME=-1]` -- "Press  !" | 0x80 Left | ip34/43, hit ip54, wrong ip65/73 (->11) | `left` (Control.Left -> Left) |
| 1 | 113 | `...[DBTN=RIGHT][MOBI=269]...` | 0x20 Right | ip81/90, ip101, ip112/120 (->10) | `right` |
| 2 | 114 | `...[DBTN=TRIANGLE][MOBI=272]...` | 0x1000 Triangle | ip128/137, ip148, ip159/167 (->10) | `menu` (Control.Menu -> 0x1000000\|Triangle); `triangle` is the same alias |
| 3 | 115 | `...[DBTN=DOWN][MOBI=270]...` | 0x40 Down | ip175/184, ip195, ip206/214 (->11) | `down` |
| 4 | 116 | `...[DBTN=CROSS][MOBI=274]...` | 0x4000 Cross | ip222/231, ip242, ip253/261 (->10) | `confirm` (0x20000\|Cross) |
| 5 | 117 | `...[DBTN=UP][MOBI=268]...` | 0x10 Up | ip269/278, ip289, ip300/308 (->11) | `up` |
| 6 | 118 | `...[DBTN=CIRCLE][MOBI=273]...` | 0x2000 Circle | ip316/325, ip336, ip347/355 (->11) | **`cancel`** (0x10000\|Circle). NOT `circle`: HarnessAgent.cs:1434 maps it to Control.Confirm = the Cross bit = a miss |
| 7 | 119 | `...[DBTN=SQUARE][MOBI=271]...` | 0x8000 Square | ip363/374, ip385, ip396/404 (->11) | `special` (0x80000\|Square); `square` is the same alias |
Every window is WindowAsync(1,160,n) (e20 ip789-852), `[TIME=-1]` (Confirm cannot close it), tail UPRF, strt 54,1.
The physical bits follow `GetKeyMaskFromControl` (EventInput.cs:476-534) through `logicalToButton`, the identity when
`cfg.control == 0` and the layout is not JP (HonoInputManager.cs:967-981; live SwapConfirmCancel = 0, Memoria.ini:127).
Directions set their bits directly in ProcessInput. A Confirm press is therefore ALSO a Cross press.

### Timing
- **TimeLeft unit = one field event tick** (one `Byte[52]--` per e3 pass; `Wait(N)` stores N-1, EBin.cs:1330-1361):
  FieldTPS 30 (Memoria.ini:53) -> 33.3 ms, at ~31 and ~60 fps render alike (FPSManager.cs:77-111; tickrate.py).
- In the arm tick S, e3 has already polled (it runs before e20). **First poll S+1; a press whose edge falls on tick S+j
  credits T = 50 - j** (j = 1..50; 49 at best); poll 50 is the last chance (T = 0, the streak kept); at S+50 e20 times the
  prompt out and arms the next one IN THE SAME TICK (no blank gap after a timeout). A prompt lives 50 ticks = 1.67 s.
- A pass lasts max(A, j): A = the reaction to the previous result (~29-31 ticks; pass 0 `Wait(30)`), which plays
  while the new prompt is live. Fast answers -> ~30.5 ticks a pass -> the fight ~1525 ticks ~ 51 s (clip playback at one
  frame per tick: an estimate). With no presses at all: ~49 x 50 + 30 ~ 2480 ticks ~ 83 s.
- After a hit the window closes on the hit tick and the next prompt opens ~25 ticks later: a visible gap.
- The first prompt arms 12 ticks after 111 leaves the dialog list. T0 = the tick e13's WindowSync wait sees window 6
  gone (that pass only clears the wait, EBin.cs:136-158); e13 runs `Wait(10)` (ip906) at T0+1 and resumes at T0+11
  (Byte[26] -> 0; e2 cleared Bit[230] at the top of that tick, so Bit[231] at once; e20 does the same); e2 sets
  `Byte[24]:=3` (ip134) at T0+12 and e20 arms the first prompt in that tick; **first poll T0+13**.

### Scoring
- Stage 6, e4 t1 ip208: `Int16[48] := (Int16[30] + Int16[32]) / 29` (integer). Then the instruction at ip222
  `SET(Int16[48] > 100)`: its first expression token at **ip223** fires **EMinigame.ChanbaraBonusPoints** (EBin.cs:331,
  before `s1.ip++`; EMinigame.cs:12 gate `EffectiveFieldId(fldMapNo) == 64` [fork-wrapped], :14 `sid == 4 && ip == 223`):
  with SwordplayAssistance >= 1, `score += score/10*3` (:18-19; 79 -> 100, 78 -> 99), the Encore achievement at >= 75
  (:20), written back to Int16[48] (:21). Then clamp > 100 -> 100 (ip233), <= 0 -> 1 (ip252).
- Gil Int16[50] = ((I30/5 + I32) + I42*2 + I40*2)/2 + 1 (ip260), `:= 10000` when Int16[48] == 100 (ip296-307).
  SetTextVariable 0 = score (ip315), 1 = gil (ip321).
- **`Byte[475] := Int16[48]` if larger (ip327-338)** -- zeroed at ip425 on arrival, so the first fight always writes it.
- `Int16[42] < 50` -> 120 + 121 (ip357/366); else 122 + 123 (ip375/384) and **`Bit[3815] := 1` (ip390)**.
- A perfect run: I32 = 0+1+...+48 + 49 = 1225, I42 = 50, I30 = sum over the 49 hits of (50 - j) + (50 - j49).
  raw = floor((I30 + 1225)/29); uniform j: j1 126, j5 119, j10 111, j16 100, j17 99, j20 93, j28 80, j29 78.
  Live SwordplayAssistance = 1 (Memoria.ini:252, [Hacks] Enabled=1 :249): 100 <=> raw >= 79 <=> I30 >= 1066.

### Wrong and extra presses
- Any of the other seven bits in an armed tick: a MISS (`Byte[47]:=3`, Byte[46] 10/11, sound 101, CloseWindow(1)): the
  streak goes to 0 and the prompt ends at once.
- Two bits in one tick: always a miss (every check runs; once Byte[46] is 10/11 even the right bit fails).
- Start held: a miss on every polled tick (B_KEY level, ip412). Never press Start (also the pause key).
- L1/R1/L2/R2/Select and the logical-only bits are never read.
- A press before the arm, between prompts (Byte[47] != 1) or on the arm tick itself: not polled, its edge lost
  (harmless). A press while the PREVIOUS prompt is still armed is judged against it. Prompts never repeat back to
  back (ip681), so re-pressing the button just answered is always WRONG for the next prompt.
- A held button gives one edge (ETb.cs:50-56); a key held across an arm gives no edge for the new prompt.
- KEYON is the per-tick edge of the OR of every frame's level inputs since the last tick (FPSManager.cs:122-136,
  EventInput.ReadInputLight -> ProcessInput(false,false)), so a 1-frame tap lands on exactly one tick at 31 and 60 fps.
  `EventInput.ReadInput` with its Chanbara branch (:80, :113-140) has no caller: the HUD changes nothing on the input path.
- Stages 2/4/8 read only logical Confirm (0x20000) or Special (0x80000) edges; the stage-6 pages and choice are UI.

### What a displayed 100 needs (49 prompts, 1 phantom)
| SwordplayAssistance | 100 needs | uniform j | the plan's j ~3-6 |
|---|---|---|---|
| 0 (PSX) | raw >= 100: I30 >= 1675 | j <= 16 (0.53 s) | raw 117-123 -> 100 |
| **1 (live)** | raw >= 79: I30 >= 1066 | **j <= 28 (0.93 s)** | 100 |
| 2 | any speed (TimeLeft refilled to 50 at every sid-4 fetch, EMinigame.cs:23-30; no timeout ever) | -- | 100 |
Every one of the 49 shown prompts must be HIT for determinism: only then does the phantom pass reach max combo 50
(Bit[3815], pages 122/123). One miss caps the max combo at 48-49: pages 120/121, no Bit[3815] row (34 hits at j=1 can
still display 100 under SA 1: the score alone is not the requirement). Each single response must land by poll 50.

### Display (PC)
No running score: the Chanbara HUD prefab is mobile-only (FieldHUD.cs:115-118); during the fight the only windows are
the prompts. The owner's 100/100 is page **122** `[WDTH=0,96,64,0,-1][IMME]Of 100 nobles watching,\n[NUMB=0] were
impressed.` -> **"Of 100 nobles watching, / 100 were impressed."** (e4 t1 ip375; [NUMB=0] = the clamped score, ip315),
then 123 "Queen Brahne was / quite impressed." (ip384). A non-perfect run shows 120 "Of THE 100 nobles watching, /
N were impressed." and 121 "...not impressed." Then 127 "They demand an encore!" (score >= 75) and 128 "They shower you
with 10000 Gil!" ([NUMB=1] = Int16[50] = 10000 only at score 100).

### Story writes of the fight and its aftermath (64)
On a 100 run: ip338 `Byte[475]:=100` (old 0) and ip390 `Bit[3815]:=1` (old 0); then e2 ip331 `Byte[8]:=0`, ip528
`Int16[2]:=325`. The fight itself stores nothing global; the bonus writes only Map.Int16[48] (no residue row). On a lower
score: ip338 writes the score (1-99), and ip390 is absent unless all 49 were hit. A "Yes" adds a fight and, on another
perfect, a second ip390 row (ip338 never again after a 100). Bit[3815] = byte 476 bit 7, next to Byte[475].

### Engine hooks
| hook | ref | fork-wrapped (source + deployed) | changes a gEventGlobal write if unwrapped? |
|---|---|---|---|
| EMinigame.ChanbaraBonusPoints | EMinigame.cs:9-32, called EBin.cs:331 | yes, :12 `EffectiveFieldId` (s24); the deployed IL has the call (gates reader's scan; the DLL = Output) | only via Byte[475] when raw is 79-99 (or SA 2's refill). At raw >= 100 the clamp hides it: **O4 cannot prove or break this wrap** |
| EventHUD.CheckUIMiniGameForMobile / OpenSpecialHUD | EventHUD.cs:342-358, :240-289; ProcessEvents.cs:124 | yes, :346 | no: on PC it sets CurrentHUD and SetPlayerControlEnable; nothing is drawn (FieldHUD.cs:115-118) and CurrentHUD only gates mouse confirms (UIKeyTrigger.cs:105) |
| EventInput.ReadInput Chanbara branch (ProcessInput(true,true) & ChanbaraMask) | EventInput.cs:80-140 | s65 wraps :88 | dead code: no caller (ETb.GetInputs reads FPSManager.DelayedInputs) |
| B_KEYON / B_KEY | EBin.cs:1094-1129 (NetSyncField.FilterScriptButtons a pass-through solo; JP swap only for JP) | n/a | no |
| TextOpCodeModifier.ReplaceChanbaraText | TextOpCodeModifier.cs:37-72 | keyed on the text block (FieldZoneId 2), not the field id | no (re-lays out 111's diamond only) |
| Encore achievement | EMinigame.cs:20, 34-38 | inside :12 | no (Steam/AchievementState) |
No other `fldMapNo == 64` site in Assembly-CSharp on this route (DoEventCode.cs:665's walk fix is SC 1600 / ent 327).

### Determinism
With 49/49 and a clamped 100, every gEventGlobal write of 64 is fixed in value and order (the 11 compared keys + 2
masked), and so are the window sequence (105, 106, 111, 49 prompts, 107, 108, 122, 123, 127, 128) and the gil.
What varies: the prompt order and reroll count, Map vars, reaction clips, pass and fight lengths, type-out waits.
What breaks it: any miss (no Bit[3815] row, maybe a lower Byte[475]) or a "Yes". Both are the driver's (VOIDs).

## THE 100 PLAN -- how the driver scores 100 on both sides, every run
**Settings (frozen, P-SETTINGS; not changed):** SwordplayAssistance 1, FieldTPS 30, SwapConfirmCancel 0, a US session.
The plan aims at raw >= 100, so its 100 does not depend on the +30% hook (and cannot exercise it).

1. **Watch.** state.json `dialog.phrase_raw` (State.raw_texts = `Dialog.Phrase`, the source with its tags; HarnessAgent.cs
   :1650-1656), published every 2nd frame (:241, :1502). A PROMPT is a published dialog whose phrase_raw holds exactly one
   `[DBTN=(LEFT|RIGHT|UP|DOWN|CROSS|CIRCLE|TRIANGLE|SQUARE)]`, `Press` and `[TIME=-1]`, in place 64 at SC 1155 with
   control off. (`texts` drops button glyphs -- measured on O1's [CBTN] hint -- so every prompt renders "Press  !".)
   111 (eight DBTN tags) is a page; 150's window 55 (two) a stop page. A NEW INSTANCE = a prompt whose DBTN differs
   from the last published prompt's, or one seen after a sample with no prompt. Poll in a tight loop (5-10 ms
   sleeps; a read is ~0.2 ms) from the first prompt to 107/108; ride empty reads (Session._read_state, STATE_MISS_BUDGET
   1 s). Optional `stateevery 1` for the fight (halves the publish lag; the agent resets it on re-arm).
2. **Press.** Exactly ONE `press <name> 2` per instance, blocking for its ack: LEFT `left`, RIGHT `right`, UP `up`,
   DOWN `down`, TRIANGLE `menu`, CROSS `confirm`, CIRCLE **`cancel`**, SQUARE `special`. Never `circle`, never Start,
   never two buttons, nothing between instances, NO re-press (a re-press of a lost press can land after the next
   arm: a certain miss); rule 7 (the page rule) never presses on a prompt.
3. **Budget, in ticks** (T = 50 - j, j = ticks from the arm to the press's edge): hard j <= 50 on all 49; 100 under the
   live SA 1 needs sum(T) over the 50 credits >= 1066 (uniform j <= 28); the plan's own target is assist-independent,
   sum >= 1675 (uniform j <= 16). **Measured latency** (archives, request write -> accepted): 60 fps median 54 ms,
   p99 78-85, max 100-122 (story-o2/o3, 2002 presses); 30 fps 72 / 126-133 / 145-171 (369). Plus the publish lag
   (0-2 frames) and the frame+1 schedule: **j ~3-5 typical, <= ~8-11 at the worst seen** -> raw 114-123 -> 100 with or
   without the bonus. Margins: ~40 ticks to the timeout; ~24 ticks of mean to SA 1's line; ~12 to SA 0's. A 200 ms empty
   read costs ~6 ticks on one prompt. The only fatal event is a stall >= ~1.4 s on a single prompt.
4. **Around the fight.** Rule 7 handles 105/106 (repeated Confirm until the script's KEYON closes them), the 111 page,
   107/108, 122, 123, 128, and 150 as in O1-O3. The choice rule answers 127 No. No Confirm edge may land at T0+13 or
   later (the first poll; T0 = 111 gone): the script and the agent read the same dialog list (MesWinActive =
   CheckDialogShowing, DialogManager.cs:176-182), so a rule-7 press decided while 111 is still published lands within
   the press latency (~3-6 ticks) of T0; the analysis checks it from the press rows.
5. **Evidence (rows).** A `prompt` row per instance: n, DBTN, button, the first frame it was published, the press's
   request seq, its accepted frame and down frame (= accepted + 1), the first frame without it, j bounds in ticks via
   `g.rate()`, the render regime. The pages and the choice as O3 records them (prompts are NOT pages: the transcript
   stays comparable across runs).
6. **The proof (new check O4-SWORD, every covered run, both sides):** (a) exactly one trace row 64 e4 t1 ip338
   `Global.Byte[475]` 0 -> 100 and one ip390 `Global.Bit[3815]` 0 -> 1 (S fld 64, F fld member(64)); (b) the published
   page texts "Of 100 nobles watching,\n100 were impressed." then "Queen Brahne was\nquite impressed.", no 120/121;
   (c) choice 127 ("They demand an encore!") answered No, once; (d) page 128 "They shower you with 10000 Gil!";
   (e) 49 prompt rows, one mapped press each, j within bound, the window gone after the press; (f) no non-prompt
   press between the first prompt and 107. O4-WRITES/NULL/STATE then compare the 26 keys as O3 did.
7. **A miss is a VOID of its own class, never a FAIL by itself.** A score below 100 changes Byte[475] and drops
   Bit[3815] because the driver's INPUT changed, not the scripts under test; a run whose input is not the frozen play
   is no sample of the claim. **V17 (driver, new):** a prompt still published ~50 ticks after first seen (timeout), an
   instance with no press, two presses, a press of the wrong name, a press outside an instance in stage 3, or a score
   page other than 122 with 100. The driver stops at once; `end_run` (warp 4600, soft reset) recovers; re-run
   (`rerun.max` 2). **V18 (game, new, a FINDING, `rerun.stop_on`):** the driver's 49 rows show the frozen play (one
   mapped press per instance, every j in budget, each window gone on its press) and the game still showed 120/121 or a
   score below 100. VOID-ASYM reads it: one side only -> NOT PROVEN (the fork scores or reads input differently);
   every run of both sides -> NOT PROVEN (the instrument, e.g. a remapped pad). A "Yes" is V2 (the `once` rule).
8. **Harness / agent / engine changes: none.** The prompt is published (phrase_raw), presses reach B_KEYON (the path above;
   O1-O3 proved Confirm -> KEYON and held Up -> B_KEY), and the trace sees the two keys. An agent instrument (Dialog.TextId,
   Map.Byte[47]/[52]/Int16[42] in state.json) would give per-prompt hit/miss evidence but needs a DLL rebuild that
   AUTO-DEPLOYS over the live install (build_memoria.py backs up; owner-gated): not worth it for O4. Driver (opt-in
   `pred["chanbara"]`, strict like `movies_of`; O1-O3 byte-identical without it, segment_regress G1-G14): the prompt rule
   before rule 7, the button map (with a test that `circle` FAILS on a CIRCLE prompt), prompt rows, V17/V18, the choice
   rule, an `o4_*.py` checks module (O4-SWORD, P-SETTINGS with SwordplayAssistance, P-DONOR with `<member(64)> 64`).
9. **FakeGame must model:** field 64 at entrance 100 (and member(64)); stage 1 (~1.8 s); 105/106 `[INCS][TIME=-1]` with
   the INCS/250-tick gate before a KEYON loop; the 111 page; 50 passes / 49 prompts with every e20 filter (SByte[38],
   max-combo 10/15, Circle->Triangle and Square->Cross, no repeat; seedable); the arm and the window in one tick, the
   reaction (~29-31 ticks) overlapping the prompt, first poll S+1, TimeLeft 50 decremented per armed tick including the
   hit tick, the timeout at poll 50 re-arming in the same tick; per-tick KEYON edges of the harness's held buttons for
   the 8 bits, held Start, two keys in a tick, the Control -> bit map (so `circle` misses); the window's publication
   (`texts` "Press  !", phrase_raw with the DBTN), Confirm not closing it, a configurable close tween; exact scoring with
   the phantom, /29, the +30% at SA >= 1 (a knob for "the hook fires on member(64)"), SA 2's refill, the clamp, the gil;
   script stores ip338/ip390 as trace rows; pages 120/121 vs 122/123 with [NUMB]; choice 124-127 with the cursor on 0,
   Yes -> replay (110/109 + KEYON, no tutorial), No -> 128 + AddGil; 107/108; the exit to 150 at 325. Faults: a publish
   stall or a driver stall during an armed prompt, a lost press, a double press, a key held across an arm, a stray
   Confirm after 111.
10. **Rehearsals before the freeze (stock):** R-CHANBARA (warp 64 100 1155 -> Field(150), x2: the published prompt form;
    a 49/49 that reads 122/123/127/128 proves the eight buttons and the pad mapping (cfg.control); j per prompt; the
    close tween; T0 vs the first prompt; 127's published options and `selected`; the fight's length); R-CHANBARA-VOID
    (stop mid-fight: `end_run` from 64 reaches the title); R-FULL (64 -> 153 x2: 26 keys, the end state, run time,
    budgets). Optional, owner's call, NOT part of the session: R-CHANBARA-GATE, a paired S/F run at a fixed j ~20
    (raw 93): S shows 100 only through the +30%, so an F that shows 93 would expose the EMinigame wrap.
11. **Unattended means hands off:** real input is OR-ed with the harness's (HarnessAgent.cs header), so a key, a pad press
    or stick drift during stage 3 is a press. The Encore achievement is reported on every perfect run (Steam).

## Disputes settled (reader claims vs the bytes / engine)
1. **End.** Bytes and data: candidate 2. Agreed; their run times (6.5 / 5 min) were too long: a pass is ~30 ticks,
   not 60-80 (dispute 2). ~3 min a run (estimate).
2. **Fight length.** Bytes 1.7-2.7 min (60-80 ticks/iteration); data 75-100 s; chanbara ~50 s. BYTES: e20 arms the
   prompt (ip721-852) BEFORE the previous result's reaction (ip861-1370), so a pass = max(A, j) ~ 30 ticks -> ~51 s.
3. **Encore cursor.** Bytes and data: on No (absolute 1, "the default"). Chanbara and harness: on Yes (0). ENGINE: Yes
   (DialogBoxSymbols.cs:671-678 `DefaultChoice = ETb.sChoose`, PCHC's 2nd param = CancelChoice; ETb.cs:100-104
   `sChoose = sChooseInit` = 0; no SetChooseParam in 64). The pick is No either way; a take-default rule would replay.
4. **Credit per hit / e3-vs-e20 order.** Harness: T = 49-d "or 50-d, order unverified"; data and gates: "of 50";
   chanbara: 50-j, max 49. ENGINE: e3 runs before e20 every tick (Obj.cs:31-45 tail-append; Main_Init InitCode(4)
   ip434, InitCode(3) ip437, InitObject(20) ip449; EBin.cs:106-160): first poll S+1, T = 50 - j, max 49.
5. **Reaction for 100 under SA 1.** Bytes ~28, data 28, harness ~27, gates 28.7, chanbara 28.7 (mean). BYTES: sum of the
   50 credits >= 1066; uniform j <= 28 (j 28 -> raw 80 -> 104 -> 100; j 29 -> raw 78 -> 99); SA 0 j <= 16.
6. **The Chanbara input path.** Gates: ReadInput's Chanbara branch is live (ProcessInput(true,true) & ChanbaraMask;
   "ETb.cs:53 is the edge of ReadInput's result"). Chanbara and harness: dead. ENGINE: dead -- ETb.GetInputs reads
   FPSManager.DelayedInputs (ETb.cs:58-63) fed by ReadInputLight (FPSManager.cs:124-136); `ReadInput()` (EventInput.cs:80)
   has no caller in the clone. Directions are level reads, KEYON the per-tick edge, whatever the HUD.
7. **105/106 (and 107/108, 98/99).** Bytes: press repeatedly. Data: press once after the text completes. BYTES: the
   KEYON loop starts only after `SYSVAR[8] >= 2` or 250 ticks (64 e13 t1 ip825-859, ip1361-1395; 150 e2 t1 ip495-529)
   and reads the edge of its own tick: earlier presses are lost -> repeat until the windows close (rule 7 does).
8. **How the driver knows the prompt.** Bytes: unknown (txid/ParsedText). Harness and chanbara: phrase_raw's [DBTN=X].
   ENGINE + archive: phrase_raw = Dialog.Phrase (HarnessAgent.cs:1650-1656); 64's async 105 published with its tags
   while control was off (story-o3 states-final.jsonl:239); `texts` drops button glyphs (O1). The DBTN form is inferred.
9. **The HUD.** Bytes: "the Chanbara HUD and ChanbaraMask are active only while Byte24==3". ENGINE: CurrentHUD does flip
   on PC (EventHUD.cs:342-358) but nothing is drawn (FieldHUD.cs:115-118) and the mask path is dead (6).
10. **Delay from 111 to the first prompt.** Chanbara: set up ~12 ticks after, first poll ~13 (no other reader timed it).
    BYTES + ENGINE agree with it: armed at T0+12, first poll T0+13 (the wait-254 pass only clears the wait,
    EBin.cs:136-158; e13 `Wait(10)` ip906 at T0+1; the Byte[26]/Bit[230] sync at T0+11; e2 ip134 at T0+12).
11. **The member set.** Bytes: whole-zone (F lands member(153)) or keep 153 out (a seam). Data: the disc-1 --ids set,
    31240-31259. SETTLED: the disc-1 --ids set (the PLAN pointer; O2's precedent): F ends in member(153), judged in
    donor terms; 31238+ is free today (re-read before minting).
12. **alxc size.** Bytes 95; data 94 ("1805 has no live bundle"). Both 95 by FBG token; the whole-zone dry run omits
    1805 as "NOT door-reachable from the seed" (data_route/importchain_alxc_whole.txt:185). Irrelevant to --ids.
13. **Run-time candidates 3-7.** Bytes 12/13.5/15/17.5/30; data 8/9/10/13/25. Estimates only; mine 6/7/8/10.5/25-30.
14. **153's choice 128 default (past the end).** Bytes and data: option 1 ("Examine her face"). ENGINE: option 0 -- the
    same SetupChoose rule as 127; `WindowSync(0,128,128)` flags 128 & ResetChooseMask 1 == 0 resets sChoose to 0, and
    153 holds no CHOOSEPARAM/EnableDialogChoices op (DoEventCode.cs:1963-1968). O5 must freeze its pick knowing that.

## Harness gaps (summary; status and evidence in the structured result)
GAP: rule 7 would press Confirm on every prompt (segment_drive.py:1793-1813, `_Drive.press` hard-codes confirm :911-919)
-> the opt-in prompt rule; the `circle` alias (HarnessAgent.cs:1434, channel.py BUTTONS) -> the map; FakeGame has no
minigame (fakegame.py: no KEYON, async non-page window or countdown model); no in-run 49/49 check -> O4-SWORD + V17/V18;
Map vars unpublished (margin not observable; driver-side j bounds suffice). RISK: the DBTN publication and the glyph
(inferred), instance tracking without a window id, 111/55 misclassification, a stall >= 1.4 s during an armed prompt,
the encore cursor (opens on Yes), the masked +30% gate, the render-regime flip, real input during the fight, a stray
Confirm after 111. UNKNOWN: cfg.control (a remapped pad moves Triangle/Circle/Square/Cross), recovery from inside the
fight. READY: the press path to B_KEYON, tap length, latency, the KEYON pairs, pages, no control/ATE/battle/FMV/naming,
stop pages, the raw-warp start, the engine/agent version.

## Fork gates (summary)
Every gate that can change a story write on the route is wrapped in the live source AND the deployed DLL (= Output):
EMinigame.cs:12 (the +30%; masked by the clamp at the plan's speed -- O4 neither proves nor breaks it), EventHUD.cs:346
(no write either way), EventEngine.cs:682 (150's autosave; not traced). P-DONOR must require `<member(64)> 64` (and
150, 153), and P-LAUNCH a relaunch after the alxc deploy (ForkDonorPatch is read at launch, DataPatchers.cs:124).
Visual/audio only and raw: PSXCameraAspect.cs:47 (153's cam-0 letterbox, past the cut), FF9Snd.cs:1396 (157),
VoicePlayer.cs:486 (voice off). Text: blocks 2 and 3 are GLOBAL: the deploy writes block 2 (64/68/69) into
FF9CustomMap, where O1's block 2 (us == uk, the known defect) lives -- a fixed-kit build turns uk to stock uk for both
sides and O1/O3's P-TEXT known-defect line flips (re-baseline), and the two chains' reverts touch the same files; block 3
has no live override today. Member(64) must stay on block 2 (TextOpCodeModifier keys 111's layout on FieldZoneId 2).

## Could not determine / unverified
The prompts' published `texts`/phrase_raw (inferred from 105 and O1's CBTN hint); 127's published options and selected;
cfg.control under the harness (the physical bits of Menu/Special/Cancel); per-prompt j in game (modelled from archived
accept times); clip playback speed, so the pass (~30 ticks), the fight (~51 s) and the run (~3 min); the windows' close
tween (the stray-Confirm margin); end_run from inside the fight; the member-id order of the import; that member(64)'s
wraps fire (the IL has them; never run on a member under the trace -- and masked anyway); whether the alxc members carry
their SPS (visual); Bit[3815]'s no-reader census (the start reader's, not re-run); 150's page cadence under the driver.
Past the end (153@325 onward): survey only.
