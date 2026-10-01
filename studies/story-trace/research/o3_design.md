# O3 -- the play under the trace: the design

**Status: DESIGN, offline -- revised for the second-round critiques (driver robustness, claim integrity; 11.2,
11.3).** Nothing is imported, built, deployed, launched or frozen; nothing NEEDS deploying (O3 runs
on O1's chain as it stands). The inputs are `o3_route.md` and `o3_research.json` in this folder: the reconciled route,
with the critic's twelve problems (`critique.problems`) overriding the route where the two conflict. This file folds
both into code-level decisions, in `o2_design.md`'s structure, and keeps what O2 learned. Every number below was
read, read-only, from the stock US `.eb` files (through the kit), the reconciler's listings
(`<scratchpad>/o3_research/reconcile/L{61,62,63}.txt`), the battle scenes' own `.eb` and raw16 (through the kit), the
live install (mod folders, `Memoria.ini`, `Memoria.log`) and the live Memoria source; section 0.2 says how. The
offline check (section 6) re-derives every one of them.

**The segment:** New Game, the trace armed, then a raw `warp <61 | member(61)=31211> 0 1155`. The route runs
61 (FMV003, the narrator, the curtain) -> 62 (Act I, then `Battle(0,338)`) -> battle 338 (King Leo) -> 63 (loaded
FRESH by the battle's own `RunBattleCode(37,63)`) -> `Field(64)` (63 e4 t1 ip828). It ends on ARRIVAL in real 64 on
both sides (the cut is 64's first row, e0 t0 ip22). SC holds 1155 throughout: there is no ladder. The F side is O1's
deployed whole-zone tshp chain (31200-31219); its members 31211/31212/31213 run here for the first time.

What O3 newly puts under the trace: a battle beat inside a segment driven by the beat-table driver, the s24
battle-return redirect (scene 338 bakes real 63; a fork run must land in 31213), a type-0 FMV under the driver's
watchdog, a segment with an empty SC ladder, and three members never loaded in game.

---

## 0. What this design decides, and what it found

### 0.1 Decided upstream (not relitigated)
- **The segment and its end.** Arrival in 61 -> 62 -> battle 338 -> 63 -> `Field(64)`; the end is the arrival in REAL
  64 on both sides (31213's `Field(64)` is not retargeted: the seam), cut at 64's first row.
- **The start.** Each run: New Game, `storytrace 1`, then the raw harness warp `warp 61 0 1155` (S) /
  `warp 31211 0 1155` (F) -- O2's form (`Segment.start_run`, unchanged). Not a replay of O2.
- **The session.** S F S F S F, `min_covered` 2 a side, at most 2 re-runs -- except that a FINDING class stops a side's
  re-runs (S2, 1.2).
- **The chain.** O1's: 61 -> 31211, 62 -> 31212, 63 -> 31213, deployed 2026-09-29 21:07 into FF9CustomMap with the
  rest of O1's 20 members. A LEGACY build: every member's jp/fr/gr/it/es `.eb` is US bytecode (`accept_us_build`, as
  O1), and text block 2's uk copy is the US text (a KNOWN-KIT-DEFECT line, never silent). Nothing is imported, built or
  deployed for O3; O1's chain is not touched, rebuilt or redeployed.
- **The freeze.** The lead freezes the predictions AFTER the in-game stock rehearsals and an F-side no-trace load
  smoke (section 7). The code ships `O3Segment.draft()` plus a `--freeze` CLI that refuses to overwrite.
- **The machinery.** O3 is built ON the shared machinery: `O3Segment` (a subclass of `O2Segment`), the battle beat as
  an OPT-IN registry in `segment_drive`, and the regression gate extended to O2 with its baseline captured FIRST.
  Every change to shared code keeps O1 and O2 analysing byte-identically (1.4).
- **The critic's twelve problems are binding** unless the bytes or the engine disprove one (section 11.1). None was
  disproved; one proposed remedy (the movie state in the watchdog's signature) is impossible without an engine patch,
  and the other remedy the critic offered is taken (11.1, #4).
- **The second round's seventeen items** (driver robustness 1-6, claim integrity 1-11) are folded in the same way
  (11.2, 11.3): each re-checked in the bytes, the engine source, the install or the archives. None was disproved and
  all seventeen are adopted; two remedies are re-shaped where the source showed the literal one would misfire (the
  battle-row frame window, the FakeGame's soft-reset knob) and one sub-request is rejected as impossible (a mutant
  failing LANDING (a) alone), each with its reason in the log.

### 0.2 Found while designing (each verified offline, read-only)
1. **Battle 338's one store, located.** `BSC_TH_E002`'s script (read with `battle.battleai._scene_eb("TH_E002")`,
   walked with `eb.model.EbScript` + `storytrace.instruction_stores`) holds exactly ONE gEventGlobal store:
   `Global.Byte[206] := B_SYSVAR[0]` at entry 1 tag 1, abs 539, entry 1's `abs_start` 272, so **entry-relative ip
   267** -- the trace's `ip`. The same walk over `TH_E001` (O1's scene 336) gives e0 t1 ip93, e0 t1 ip168, e0 t1 ip213
   (Byte[199]), e1 t1 ip267, e2 t1 ip37, e3 t1 ip37 -- and O1e's traces hold exactly `(m 2, sid 1, tag 1, ip 267,
   Byte 206)` x64 + its count row, and `(m 2, sid 0, tag 1, ip 93)` x1, at fld 50 (S) / 31200 (F), don 50. So the
   trace's battle ip convention is calibrated, and O3 can pin every battle-mode row to `(1, 1, 267)` (O3-LANDING (b)).
   **The site does not pin the scene:** TH_E001 stores Byte[206] at the SAME e1 t1 ip267, so a 336 fought in 338's
   place would leave rows (b) accepts; the scene is pinned from the driver's log by O3-BATTLE (5.3). The walk also
   leaves 24 TH_E002 stores unresolved (e1 t5 ip672-ip751, e2 and e3 t5 ip513-ip592, "B_LET's lvalue is not a literal
   variable"): every one's lvalue is `B_SYSLIST[0]` (a battle target list, not gEventGlobal), which O3-SCENE now
   classifies by that token (6.1). And the count of Byte[206] rows may be ZERO: e1 t1's first Main pass sets
   `Instance.Byte[31]` at [525] and `[533] JMP(10)` lands on the `[546] SYSVAR[30] != 1` test BEFORE the `[539]`
   store, so a battle whose ATB already reads 1 there writes none (LANDING (c) is anchored on keys, not on them).
2. **The scene, decoded.** 338 = `BSC_TH_E002` (`_scenedb.SCENES`); its raw16 (`battle.extract.read_scene_assets`,
   `battle.scene_codec.parse_scene`): flags **0x1839** -- 0x10 set (WinPose off: a scripted end reports 2,
   BTL_SCENE.cs:222, btl_scrp.cs:785-797), 0x20 (no escape), 0x8 (no EXP), 0x1 (preemptive); MaxHP King Leo (type 0)
   10186, Zenero 32, Benero 28. Entry 0 tag 0 [265] `RunBattleCode(37, 63)`; entry 1 tag 1 [587]
   `B_SYSLIST[1] B_MEMBER(36) const(10000) B_LE_E B_COUNT`: the end needs >= 186 damage to King Leo.
3. **Every drafted key is a real store.** The 43 sites of section 4 (24 writes, 3 chain keys, the forbidden site
   62 ip1345, 14 error-path sites, `start_first`) were run through O2-KEYS's machinery (`O2Segment.keys_check` on a
   synthetic predictions dict): "43 sites (43 keys), every op in its statement, 4 compound values computed from their
   priors, none masked". With the ten `dead` sites of 4.5 added (round 2) the same machinery reads "53 sites (53
   keys), every op in its statement, 4 compound values computed from their priors, none masked". Of O3's targets
   only `Bit[191]` (boot_scratch) and `Bit[184]` (field_menu_guard) lie in the story-noise mask
   (`storytrace.noise_regions`); no non-bit target is masked (`Int16[11]` spans bytes 11-12: an `IntN[i]` index is
   its first byte, as `Int16[2]` is `entrance_bytes` [2, 3] and the trace's `Int16[11]` rows carry `byte` 11).
4. **61, 62 and 63 hold no gateway and no hot-spot.** O2-REGIONS's census (`O2Segment.regions_check` over route
   [61, 62, 63] with no regions registered): "0 regions, 0 hot-spots, 0 gateways all registered". (64 has two
   gateways, to 153; it is the end field, never walked.) Every `EnableMove` in 61-63 sits behind `Map.Bit[158]==1`
   (61 e0 t0 ip399/ip440, 62 ip396/ip437 and e0 t10 ip630/ip671, 63 ip412/ip453), which nothing on the route sets.
5. **Text block 2, measured.** `O2`'s `text_rule` against each language's stock asset read by its ResourceManager
   path (`stock_text_assets(2)`): the O1 build (`C:\gd\_ns_playtest\o1\build`) and the live FF9CustomMap both read
   **6 byte-equal, KNOWN-KIT-DEFECT 1, FAIL 0**: uk ships stock us (3a6f3246c2; stock uk 7ac9f17435).
6. **The live install, read.** No mod folder overrides 61, 62, 63 or 64 (`storytrace.stock_overrides`); field 70's
   New-Game override is FF9CustomMap-world's; 4600 (the recovery field) is registered in FF9CustomMap-world.
   ForkDonorPatch: 73 rows, all in FF9CustomMap; donors 61, 62, 63 appear once each (31211, 31212, 31213); the only
   duplicated donors are 312 and 350-359. Members 31211-31213 are registered once each (O1_TH_BST, O1_TH_STG,
   O1_TSHP_TH_STG). `o1_opening.py --preflight`: 5/5 PASS; `--offline-check`: O1-BUILD "140 files; other languages: 15
   own-language, 105 us-build", O1-KEYS "4 keys".
7. **The launch's own donor map is readable.** The engine logs a ForkDonorPatch collision only as a warning
   (DataPatchers.cs:156-160: "[DataPatchers] ForkDonorPatch: donor field {donor} is forked by both {prev} and {fork}
   -> remap DISABLED") and logs "[DataPatchers] Initialized" (:128) once the patchers ran; there is no positive
   "mapped once" line. Today's `Memoria.log` (launch 2026-09-30, first line 19:27:42) holds the warning for 312 and 350-359 only,
   then "Initialized", then "Updating text localization [English(US)]". So P-DONOR-LOG reads the ABSENCE of the warning
   for 61-63 on a log that proves the patchers ran, and its scan is calibrated on real lines.
8. **The id flip is inside the battle, in the engine's order** (round 2 re-read it phase by phase). (1) cmd 33
   (`RunBattleCode(33,1)`, btl_scrp.cs:785-799) sets result 1, which WinPose off turns into 2, and starts the fade
   (`SEQ_DEFEATCLOSE_FADEOUT`) while `fldMapNo` is still 62/31212. (2) When the fade ends, ONE call of
   `HonoluluBattleMain.UpdateOverFrame` (:721-741) folds 2 into 1 AND sets
   `fldMapNo := IsForkField(PreBattleFieldNo) ? ForkSiblingField(nextMapNo) : nextMapNo` (63 / 31213), then
   `GoToBattleResult()` -- while `SceneDirector.IsBattleScene()` (the published `in_battle`) is still true. (3)
   BattleResult: `InitialEvent` (BattleResultUI.cs:31-35, :374-385) hides every panel and re-runs the scene's e0
   (TH_E002 [238]-[252]: `CloseAllWindows`, `op_22(5)`, `TerminateBattle` -- EventEngine.DoEventCode.cs:2972) at field
   63, result 1, still in the battle. (4) The field load, the UI lagging as BattleResult. (5) FieldHUD. The agent
   publishes the raw `fldMapNo` (HarnessAgent.cs:1537), so for a stretch of samples the run reads `in_battle` AND
   field 63/31213 -- the critic's blocker (a) -- but never field 63/31213 with result 2. `fight()` breaks on its first
   sample with a result, normally phase 1, so it returns 2 at field 62; 1 only if its immediate re-read lands after
   the over frame. `won` is `[1, 2]`.
9. **The warp is refused in a battle, at once.** `Ff9mkDebugMenu.Warp` returns false unless the UI state is FieldHUD
   (:2083); the agent then throws "warp refused (not on a field?)" (HarnessAgent.cs:652-656). So `end_run`'s warp fails
   fast inside a battle; the cost is `restore_baseline`'s `close_ui` (6 Cancels, then a 20 s wait for a field) before
   the soft reset, which has never been tried from a battle. The FakeGame swallows the soft reset outside
   FieldHUD/WorldHUD (fakegame.py:1781) and does not refuse a warp in a battle (fakegame.py:931-946).
   **Where the soft reset can fire (round 2, UIKeyTrigger.cs).** `soft_reset()` holds all six buttons from one frame.
   On that down frame `HandleMenuControlKeyPressCustomInput` consumes Select whenever a scene UI is up and no dialog
   is (:688; `Update` returns at :161), so the reset fires only on a HELD frame, through `GetKey`, which answers false
   outside FieldHUD/WorldHUD/BattleHUD/QuadMistBattle (:94). So it fires from BattleHUD on the 2nd held frame and
   never from BattleResult (no dialog is up there: 338's e0 closes every window). And `HandleBoosterButton`, which
   holds the reset (:344), returns at once while a movie is marked played (:241, `MBG.IsFinishedForDisableBooster`,
   MBG.cs:607-610): `played` is set by `Play` and cleared only by `Stop`/`Seek`/`Purge` (fldfmv's shutdown at the
   movie's end, fldfmv.cs:198) -- so the reset is dead while FMV003 plays.
10. **`fight()` and `leave_battle()` today.** `fight()` raises a plain HarnessError on both no-result exits (max turns,
    session.py:7407-7411; timeout, :7442-7444) -- nothing tells them apart from an instrument failure. `leave_battle()`
    presses Confirm every 20 frames while `in_battle` or the UI reads BattleHUD/BattleResult (:7457-7463) and logs
    neither its presses nor the states it pressed in.
11. **The agent publishes no movie state.** HarnessAgent.cs has no MBG/movie/cinematic field; during FMV003 nothing in
    the driver's progress signature (segment_drive.py:1067-1069) changes. Adding the movie to the signature needs an
    agent patch (an engine rebuild); sizing `no_progress_s` from the rehearsals is the fix (11.1, #4).
12. **The baseline holds at HEAD.** `o2_alexandria.py --analyse <story-o2> --predictions o2_predictions_v1.json`
    reproduces the archived `o2_report.txt` byte for byte (the CLI adds print's newline), PROVEN, 15 checks;
    `o2_dryrun.py --predictions o2_predictions_v1.json` reads "86/86 cases as registered" (65 s); `o2_alexandria.py
    --offline-check` 5 PASS (O2-BUILD 126 files own-language, O2-KEYS 48 sites (50 keys), O2-TEXT 7 byte-equal,
    O2-REGIONS 26 regions 17 hot-spots 21 gateways, O2-GOALS 14 steps). O2's START detail hard-codes "3 residue rows"
    (o2_alexandria.py:1347): O3 writes its own START (its start has two).
13. **The settings the runs live under.** `Memoria.ini`: `[Battle] Enabled 1, SFXRework 1, Speed 5 (Simultaneous),
    CustomBattleFlagsMeaning 0`; `[Cheats] Enabled 1, AutoBattle 1, SpeedMode 1, SpeedFactor 3, SpeedTimer 0,
    BattleAssistance 1, Attack9999 1, NoRandomEncounter 1, MasterSkill 0, LvMax 0, GilMax 0`; `[Hacks] Enabled 1,
    AllCharactersAvailable 1, SwordplayAssistance 1, DisableNameChoice 0`; `[Control] SoftReset 1, TurboDialog 1,
    BattleAutoConfirm 1, DialogProgressButtons "Confirm"`. They shape the battle's timing (SYSVAR[25]/[30] at King
    Leo's latch), not its stores; they are fingerprinted and frozen (4.13).
14. **The map's wording, corrected** (the critic's #4 and #10, re-read in the listings): 61's pages come AFTER FMV003's
    end (61 e2 t1 ip324 passes at movie frame 1100, then ip371-ip422 loops until `SYSVAR[15]&127 == 1`, the movie's end;
    frame 1100 only times sound cues); 61-63 DO read keys -- Bit[184], Byte[13], Int16[9], Byte[14] and Int16[11] in e0
    t0 (ip30-ip189; Bit[184], Byte[13] and Byte[14] before writing them), and Byte[8], UInt16[21] and Byte[303] after
    writing them; O1 already played FMV002 inside its segment -- what is new is a type-0 FMV under `segment_drive`'s
    watchdog; and an incoming Byte[13] of 2 would not stall a run (the page rule would confirm the error window) -- O3
    makes that window a deliberate VOID instead (2.2, rule 7).
15. **Every gEventGlobal store site of 61-63, counted (round 2).** `instruction_stores` over every function of stock
    61, 62 and 63 finds 15, 28 and 15 Global store sites and 0 unresolved ones. Ten were in no list: 61 and 63 e0 t0
    ip41 `Int16[2]:=10000`, ip130 `Byte[13]:=1`, ip211 `Byte[14]:=1`; 62 e0 t0 ip45, ip134, ip215 (the same three, 4
    bytes later); 62 e4 t1 ip1023 `Byte[4]:=1`. They are the `dead` list of 4.5, each with the guard that keeps it
    off the route, and O3-CENSUS (6.1) fails the day a site outside every list appears.
16. **The launch reads its patch files once.** `DataPatchers.Initialize` (DataPatchers.cs:107-134) is called once, from
    `AssetManager`'s static set-up (AssetManager.cs:116), and reads every stacked folder's DictionaryPatch,
    BattlePatch, TextPatch and ForkDonorPatch; `ForkSiblingField(63)` answers 63 itself when that launch saw no
    `31213 63` row (:102-105). Files read at session start prove the files, not the launch: FF9CustomMap's
    ForkDonorPatch.txt and DictionaryPatch.txt were rewritten at 2026-09-30 19:27:04, the launch's first Memoria.log
    line is 19:27:42. Memoria.log lines carry `dd.MM.yyyy HH:mm:ss` stamps, so P-LAUNCH (6.2) can order them.
17. **The live stack already overrides battle data.** FF9CustomMap ships `BattleMap/BattleScene/EVT_BATTLE_LEDGER{1S,
    1W,_A,_B}` (raw16 + raw17) and their `EventBinary/Battle/<lang>/EVT_BATTLE_LEDGER*.eb.bytes`; its BattlePatch.txt
    holds `Battle:` blocks for 67 (twice), 336, 337, 334 and 335 (`Music: 0`, O1's own deploy wrote four of them), and
    FF9CustomMap-msgs's for 67. None names 338, TH_E002 or its enemies -- but a BattlePatch selector (`Battle:`,
    `AnyEnemyByName:`, `AnyAttackByName:`, DataPatchers.cs:747-783) or an `EVT_BATTLE_TH_E002` asset would change
    battle 338 on BOTH sides, which NULL cannot see: P-STOCK-BATTLE (6.2) and the fingerprint (6.3) close that.
18. **The battle's timing races a short timeout.** In story-o1e run 1, TH_E001's same latch took 7 hits in 16.4 s from
    the first `battlecmd` (steps.jsonl, t 1790731999.16 to 2015.52), the next `menus` refused "not asking" 17.1 s
    after it. A rehearsal that meant to stop INSIDE battle 338 by a 15 s timeout could see the latch win, and its
    recovery would then run in the end sequence, not mid-fight; `max_turns` 0 raises at the first command prompt,
    before any attack (session.py:7407), so R-BATTLE-VOID now uses that (7.1).
19. **Control is zeroed on every field start.** `EventEngine` sets `usercontrol = 0` before every Main_Init
    (EventEngine.cs:627), the battle-return load of 63 included (loaded fresh: `lastmap` 62 is not 63, :666); and
    every field load but the listed exceptions runs an autosave (:670-697), a plausible source of a load hitch.
    `[TIME=n]` and `[TIME=-1]` set the dialog's button inhibit (DialogBoxSymbols.cs:811-826), which `OnKeyConfirm`
    honours (Dialog.cs:789): a Confirm cannot close a timed window, so 61-63's transcripts are deterministic.
20. **The stale hit-area warning is no signal.** The research critic's #5 remedy asked R-START to record "no stale
    hit-area warning". The engine clears a leftover movie hit area itself at every field start
    (HonoluluFieldMain.cs:152 -> `ETb.InitMovieHitPoint`, ETb.cs:31-37, which logs "InitMovieHitPoint() =>
    FieldHUD.MovieHitArea has not been deactivated ..." when it does), and that line appears 0 times in story-o1e's
    and story-o2's output_log.txt -- both warped out of a playing type-0 FMV001 -- so its absence proves nothing. F1
    reads FMV003 playing to its end and page 72 opening instead.

---

## 1. Module layout

### 1.1 Files

| File (in `studies/story-trace/` unless a path is given) | | What it holds |
|---|---|---|
| `segment_regress.py` | edit, FIRST | The regression gate extended to O2: items G8-G12 (1.4) beside O1's G1-G7, and `--capture-o2`. Its O2 baseline is captured BEFORE any other code change. G13 (the O3 driver tests by name) joins at B4. |
| `research/o2_regress_baseline.json` | new, FIRST | The captured O2 baseline (1.4 G8-G12), LF, `-text`. |
| `segment_trace.py` | edit (PART A) | S1 (a registered battle's won set in the coverage rule, an int result only), S2 (`rerun.stop_on`), S3 (`end_run` from inside a battle: the soft reset from BattleHUD only, the end sequence waited out), S5 (the session ends through `end_run` when the segment asks). |
| `segment_drive.py` | edit (PART B) | S4: the opt-in battle registry (strict rows) and its executor (the two-tier landing wait, `battle_epoch0`), `stop_pages`, V15 and V16. |
| `o3_prima_vista.py` | new | `O3Segment(O2Segment)`: the draft predictions (with `dead`), O3's checks (O3-BATTLE, O3-LANDING (a)-(e)) and report, the offline checks (O3-SCENE, O3-CENSUS) and preflight extras (P-DONOR, P-SETTINGS, P-STOCK-BATTLE; P-DONOR-LOG and P-LAUNCH in game), `trace_summary`, the CLI (`--offline-check`, `--preflight`, `--draft`, `--analyse`, `--freeze`, `--rehearsal-report`), module-level `run(g)`. |
| `o3_forks.json` | new | The chain manifest: O1's members, `deployed: true`, pointing at O1's deploy and revert record (6.4). |
| `o3_dryrun.py` | new | O3's synthetic sessions, units and offline mutants (section 8). |
| `o3_rehearse.py` | new | The stock rehearsal stages and the F-side load smoke for `tools/play.py` (section 7). |
| `.gitattributes` | edit | `studies/story-trace/research/o2_regress_baseline.json -text` (A0) and `studies/story-trace/o3_predictions*.json -text` (C1, before any freeze). |
| `tools/harness/channel.py` | edit (PART B) | H7's `FightTimeout(HarnessError)`, beside `HarnessError` and `StepRefused` (:86-90), exported where they are. |
| `tools/harness/session.py` | edit (PART B) | H7 (`fight` raises `FightTimeout`; `last_fight` fields), H8 (`leave_battle(stop_on_field=)`, `last_leave`). |
| `tools/harness/fakegame.py` | edit (PART B) | H9 (opt-in knobs: a scripted battle end, a battle exit in the engine's four phases, `warp_field_only`, `warp_arrive_control`, `soft_reset_ui`, a movie beat with the skip dialog that swallows the soft reset while it plays). |
| `ff9mapkit/tests/test_harness.py` | edit | The FakeGame and unit tests named in sections 1.2, 3 and 9. |
| `PLAN.md` | edit (PART C) | The O3 section: "draft: rehearsals pending, freeze pending". |

`o1_opening.py`, `o1_dryrun.py`, `o2_alexandria.py`, `o2_dryrun.py`, `o2_rehearse.py` and every frozen predictions file
are NOT edited. That they keep their outputs is the gate.

### 1.2 The shared changes (each opt-in or behaviour-neutral for O1 and O2)

**S1 -- `Segment.read_session`: a registered battle is judged by its row's won set** (segment_trace.py:653-657).
Today a beat named `battle` is done when its value is in `pred["battle_won"]` (O1's legacy rule), and any other beat
when its value is truthy -- so an O3 beat holding a result 3 (defeat) would read done. The change:
```python
won = {b["beat"]: list(b["won"]) for b in pred.get("battles") or ()}

def done(b):
    if b in won:
        v = beats.get(b)
        return type(v) is int and v in won[b]      # True == 1: a bool is never a battle's result
    return beats.get(b) in pred["battle_won"] if b == "battle" else beats.get(b)
missed = [b for b in pred["beats"] if not done(b)]
if rec.get("end") == "reached" and missed:
    why = (f"beats not done: {missed} (battle result {beats.get('battle')})" if not won   # O1's text, exactly
           else f"beats not done: {missed} (" + ", ".join(f"{b} result {beats.get(b)!r}" for b in won) + ")")
```
O1 and O2 carry no `battles` key: their path and text are unchanged. The row itself is validated where it is loaded
(S4's `battle_of`: `won` exactly `[1, 2]` or `[1]`, `beat` one of `beats` and named by nothing else), so a row this
rule reads is never `won: [1, 2, 3]` and its beat is never set by a step, a naming rule or a choice.
Test (A1): `test_segment_read_session_judges_a_registered_battle_by_its_won` -- a stub session (the `_stub_segment`
pattern) whose runs record `{"leo": 2}`, `{"leo": 1}`, `{"leo": 3}`, `{"leo": None}`, `{"leo": True}` against
`battles: [{"beat": "leo", "won": [1, 2], ...}]`: covered, covered, A-BEATS ("leo result 3"), A-BEATS, A-BEATS ("leo
result True").

**S2 -- `Segment.run`: a FINDING class stops its side's re-runs** (segment_trace.py:585-594). `pred["rerun"]` may
name `stop_on` (a list of V-classes). A side with any run VOID in one of them is not re-run however short it is:
re-running a finding only repeats it (the s24 leak, V16), and VOID-ASYM already reads it (5.3). The re-run loop reads
the session once per pass (today it reads it twice inside the comprehension):
```python
stop_on = set(pred["rerun"].get("stop_on") or ())
while reruns < pred["rerun"]["max"]:
    runs = self.read_session(g.run_dir, pred, session=session)
    held = {s for s in SIDES if any(r["side"] == s and r["rec"].get("v") in stop_on for r in runs)}
    short = [s for s in SIDES if s not in held and
             sum(1 for r in runs if r["side"] == s and r["covered"]) < pred["min_covered"]]
    if held:
        session["rerun_held"] = {s: sorted({r["rec"]["v"] for r in runs if r["side"] == s
                                             and r["rec"].get("v") in stop_on}) for s in sorted(held)}
    ...
```
No `stop_on` (O1, O2): exactly today's behaviour; `rerun_held` is written only when non-empty.
Test (A2): `test_segment_rerun_stops_on_a_finding_class` -- `_stub_segment` (it gains a `rerun` keyword) whose F runs
VOID with `v="V16"`: with `stop_on: ["V16"]` the session is exactly S F S F S F (no re-run) and records
`rerun_held {"F": ["V16"]}`; the control, without `stop_on`, re-runs F twice.

**S3 -- `Segment.end_run` from inside a battle** (segment_trace.py:460-480). A run stopped mid-battle (V15, the
budget, an exception) must not spend the refused warp and `close_ui`'s 20 s before the one rung that can work there
-- and the soft reset works in only ONE battle state (0.2 #9): BattleHUD, mid-fight. In the end sequence (the fade
with a result set, then BattleResult) the combo is swallowed, so there the run waits for the field the battle hands
it, then takes today's warp ladder:
```python
if g.state.ui_state != "Title":
    st = g.state
    if st.in_battle and st.ui_state == "BattleHUD" and st.battle_result == 0:      # mid-fight: the one state
        log.append({"k": "recover-in-battle", "scene": st.battle.get("scene"), "ui": st.ui_state,
                    "result": st.battle_result})
        try:
            g.soft_reset()
            log.append({"k": "recover-reset"})
        except HarnessError as err:
            log.append({"k": "recover-reset-failed", "why": str(err)[:200]})
    else:
        if st.in_battle:                      # the end sequence: a result is set, or BattleResult
            log.append({"k": "recover-battle-ending", "scene": st.battle.get("scene"), "ui": st.ui_state,
                        "result": st.battle_result})
            try:
                st = g.wait_for(lambda s: not s.in_battle and s.ui_state == "FieldHUD" and s.field_id > 0,
                                timeout=self.battle_end_wait_s, what="the battle's end to hand over a field")
                log.append({"k": "recover-battle-ended", "field": st.field_id})
            except HarnessError as err:
                log.append({"k": "recover-battle-ending-failed", "why": str(err)[:200]})
        ...today's warp to `recovery` and its log rows...
ok, why = g.restore_baseline()        # unchanged from here
```
`Segment.battle_end_wait_s = 120.0` (a class attribute: the same cap as the battle row's `land_cap_s`, 2.1). O1 and
O2 never end a run in a battle on their covered paths; a run stopped mid-fight now takes the soft reset first, one
stopped in a battle's end sequence waits for its field. No analysis output changes. (The review, 11.7 #8: the end
sequence's LOAD -- the scene gone, the UI still BattleResult, where a `battle()` stopped before FieldHUD leaves the run
-- reads `in_battle` False, so the test is `st.in_battle or st.ui_state == "BattleResult"`: the load is waited out
too, never warped from.)
Tests: (A3) `test_segment_end_run_resets_from_inside_a_battle_without_a_warp` -- stub session objects (a
`SimpleNamespace` recording `warp`/`soft_reset`/`wait_for`/`restore_baseline`): in BattleHUD with result 0, no warp,
one soft reset, then the ladder, rows `recover-in-battle` (ui BattleHUD) then `recover-reset`; in BattleResult (and
in BattleHUD with result 2), no soft reset, the wait, then the warp and the ladder, rows `recover-battle-ending`,
`recover-battle-ended`, `recover-warp`; a stub whose field never comes: `recover-battle-ending-failed`, then the
warp attempt and the ladder. (B5, once H9 lands) `test_segment_end_run_from_a_battle_on_the_fake` -- the FakeGame with
`warp_field_only`, `warp_arrive_control` False and `soft_reset_ui` the engine's set (H9): from BattleHUD mid-fight, the
title and no warp executed; from H9's BattleResult phase, the field, the warp to `recovery`, the title; with
`soft_reset_ui` left at today's default, from BattleHUD: "the title could not be restored".

**S4 -- `segment_drive`: the battle registry, `stop_pages`, V15 and V16** (PART B; section 2). Every addition is
read only when the predictions carry it (`battles`, `stop_pages`): with neither, the driver is byte-for-byte today's
loop, which the O2 driver tests (G12) prove -- `test_o2_drive_voids_a_battle_without_a_registry` among them, the one
that puts a battle on screen under O2-shaped predictions (1.4).

**S5 -- `Segment.run`: the session can end through `end_run`** (segment_trace.py:597-600; round 2). Today the session
ends with a bare `g.restore_baseline()` where the LAST run stopped (`end_run` runs only before runs 2..n, :547): no
warp first, so a last run stopped in 61 during FMV003 -- where the soft reset is dead (0.2 #9) -- loses 45 s and
leaves the game in 61. A segment that sets `end_session_warps = True` (O3) ends the session as every run between:
`log = []; self.end_run(g, log)` (warp to `recovery` first, S3's battle rule), recorded as `session["ended"] = {"log":
log, "ok": bool, "why": str}` (a HarnessError is caught and recorded, never raised). The default (`False`: O1, O2) is
today's bare call exactly, so their sessions are unchanged; they would gain the same fix by setting it, which is
theirs to decide.
Test (A4): `test_segment_session_end_warps_first_when_asked` -- `_stub_segment` runs one session each way: with
`end_session_warps` the last call sequence is `warp(recovery)` then `restore_baseline` and `session["ended"]` holds
the rows; without, it is a bare `restore_baseline` and no `ended` key. (B5) `test_segment_session_end_leaves_a_movie_on_the_fake`
-- the FakeGame mid-movie (H9's movie beat) at the session's end: with `end_session_warps`, the title; without, the
bare ladder cannot reach it (the movie swallows the combo).

### 1.3 `o3_prima_vista.py`

`O3Segment(o2_alexandria.O2Segment)`:
- `tag = "O3"`, `predictions = HERE / "o3_predictions_v1.json"`, `manifest = HERE / "o3_forks.json"`,
  `session_file = "o3_session.json"`, `report_file = "o3_report.txt"`, `chain_dir = C:\gd\_ns_playtest\o1\fork`,
  `build_dir = C:\gd\_ns_playtest\o1\build`, **`accept_us_build = True`**, `recovery = 4600`,
  **`end_session_warps = True`** (S5).
- `core_ids = ("START", "NO-SC", "CHAIN", "RESIDUE", "WRITES", "NULL", "STABLE", "SEAM", "LANDING", "BATTLE",
  "MASKED", "STATE", "JOIN")`; `titles` gives every check its O3 text (5.3, 6.1, 6.2) -- O3-BUILD's title says "US
  session" (6.1).

**Inherited unchanged from O2Segment:** `current` (the draft until frozen), `text_check` (block 2 through
`pred["text_block"]`), `regions_check`, `read_session`, `_run_log`, `forbidden_check`, `void_asym_check`,
`span_check` (CHAIN), `residue_check`, `null_check`/`stable_check`/`join_check` (the base's), `seam_check` (through
`pred["seam"]`), `masked_check`, `history`/`suppressed`/`state_check`, `add_arguments`, `drive` (`segment_drive.drive`:
the battle beat is in the predictions, so `drive` itself does not change).

**Overridden:**
- `draft()` -- section 4. Members and names come from O1's `campaign.toml` (`ST.chain_from_campaign`), asserted to be
  exactly O1's twenty (`o1_forks.json` members) and to map 31211 -> 61, 31212 -> 62, 31213 -> 63.
- `keys_check(pred, stock)` -- O2's machinery on a filtered copy, so O2's code is untouched:
  `super().keys_check({**pred, "ladder": [], "start_dependent": [], "noise": [], "forbidden_sites":
  pred["forbidden_sites"] + pred["error_path"] + pred["dead"]}, stock)`. O3's one noise pattern is O1's legacy
  battle-mode form, which has no field site to join; O3-SCENE proves it instead (6.1).
- `offline_extra` -- `[text_check, keys_check..., regions_check, scene_check, census_check]` (6.1). No GOALS: there
  is no table.
- `preflight_extra` -- O2's (P-TEXT on block 2, P-RECOVERY) + P-DONOR + P-SETTINGS + P-STOCK-BATTLE (6.2).
- `capabilities(g)` -- O2's (P-CAP, P-OBJECTS, P-LANG) + P-DONOR-LOG + P-LAUNCH (6.2).
- `fingerprint_extra` -- O2's (`override70`, `text2`, `lang`) + `settings` + `battle_patch` + `battle_overrides`
  (6.3).
- `why_void` -- O2's (A-NOSTART, A-FORBIDDEN, A-MISMATCH) + A-START (5.1).
- `core_checks` -- 5.3, in `core_ids` order: O3's own `start_check`, `no_sc_check`, `writes_check` (exact),
  `landing_check`, `battle_check`; the inherited ones for the rest.
- `report_extra` -- O3's own sections (5.4); O2's names O2's scope line and SC timeline.
- `handle(args)` -- `--rehearsal-report` reads `o3_rehearsal.json` (O3's own `rehearsal_report`); everything else is
  O2's `handle`. `--freeze` runs `segment_drive.battle_of` over every `battles` row first (2.1).

**Module functions (pure):** `scene_census(scene_name)` (O3-SCENE's reader), `store_census(fields, stock, pred)`
(O3-CENSUS's), `lvalue_class(token)` (an unresolved store's lvalue token -> its class, or None: `B_SYSLIST[n]` ->
"a battle target list, not gEventGlobal"; nothing else is classified today), `ini_settings(text, keys)` (the
engine's ini reading: the last assignment wins, sections and keys case-insensitive), `donor_log(log_text, donors)` (P-DONOR-LOG's
reader: `(initialized, [warning lines naming a donor])`), `launch_time(log_text)` (P-LAUNCH's: the first line's
`dd.MM.yyyy HH:mm:ss` stamp, or None), `launch_check(files, launched)` (P-LAUNCH's verdict over `{path: mtime}`),
`battle_stock(roots, scene_id, names)` (P-STOCK-BATTLE's scan), `trace_summary(rows, pred, ...)` (O2's shape for O3's
lists, plus the battle's rows and their count, the first field row after 62 ip1285 and the end cut's row; 7.2),
`rehearsal_report(run_dir)`, `run(g)` = `O3.run(g)`, `main(argv)`.

O3 imports `o2_alexandria`, so that module is now shared code: any later edit to it must keep O2's gate (G8-G12) AND
O3's dry run green.

### 1.4 The regression gate extended to O2 (`segment_regress.py`)

The implementer extends the gate and captures its O2 baseline FIRST (A0), before any other code change, at the
design commit. The O2 items import only O2's modules (`o2_alexandria`, `o2_dryrun`) through their public names,
inside their functions (the O1 items keep importing only O1's). From then on the gate is run after every commit that
touches shared code. It exits 0 only if every item passes; 2 if an archive or a baseline is missing (the gate did not
run, which is not a pass).

`O2S = C:\gd\Dream-World-IX\.harness-runs\20260930-192740-story-o2`, `V1 = HERE / "o2_predictions_v1.json"`.

| Item | Check |
|---|---|
| G0' | `py studies/story-trace/segment_regress.py --capture-o2` (once, before any O3 code change) writes `research/o2_regress_baseline.json` (LF, `-text`): the full `(checks, report)` of O2S with V1; every `o2_dryrun` session case's `(checks, report)` and "predictions-changed"'s; every unit case's and offline mutant's `(name, ok, detail)`; `O2.offline_check(V1)`; the G12 tests collected; the HEAD and V1's sha. It refuses an existing file, and refuses to write unless G8-G12's baseline-free halves pass (the archive equality, PROVEN, `run_cases(V1)` 0, 5 PASS offline, the pytest selection green). |
| G8 | `O2.analyse(O2S, pred_path=V1)`: the report equals `(O2S/"o2_report.txt").read_text(encoding="utf-8")` exactly, and the baseline's; the checks are the baseline's; the verdict PROVEN with 15 checks, all True. |
| G9 | `py studies/story-trace/o2_alexandria.py --analyse O2S --predictions V1` exits 0 and prints that report (plus print's newline). |
| G10 | Every `o2_dryrun` case's `(checks, report)` is byte-equal to the baseline's, every unit and offline mutant's `(name, ok, detail)` too, and `o2_dryrun.run_cases(V1)` returns 0 printing "86/86 cases as registered". The gate replicates `run_cases`'s loop step for step (as G3 does O1's), so every session gets the label `run_cases` gives it (`s0`, `s1`, ... in creation order). |
| G11 | `O2.offline_check(V1)` equals the baseline's `[(ok, what, detail)]` (it reads the O2 build and the stock assets, read-only). |
| G12 | `pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o2_ or rehearse"` from `ff9mapkit/`: all passed, 0 failed, 0 skipped, 0 errors; every test the baseline collected still runs, plus every name in `REQUIRED_TESTS_O2`. |
| G13 (from B4) | `pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o3_drive"` from `ff9mapkit/`: all passed, 0 failed, 0 skipped, 0 errors, and every name in `REQUIRED_TESTS_O3` among them -- the battle beat's driver tests (B4), so a later edit to `segment_drive` (O4's) re-runs them. No baseline: the list is the floor. It joins the gate in the B4 commit that adds the tests, never earlier (a selection that collects nothing is not a pass). |
| G14 (the review, 11.7 #12) | `o3_dryrun.run_cases` on the frozen O3 predictions once they exist, else on the draft: it returns 0 printing "N/N cases as registered", N at least `O3_DRYRUN_FLOOR` (92 when it joined). 1.3's rule -- a later edit to `o2_alexandria` (or `segment_trace`, `segment_drive`) must keep O3's dry run green -- enforced at last, not only said. No baseline: the count is the floor. Without the frozen file the draft reads O1's chain build, so the gate says "not run" (exit 2) where that build is absent. |

O1's G1-G7 stay as they are; tests O3 adds whose names match G7's selection (`test_segment_*`) join it through
`REQUIRED_TESTS` as each lands, tests matching G12's (`test_o3_rehearse_*`, and B4's
`test_o2_drive_voids_a_battle_without_a_registry`) through `REQUIRED_TESTS_O2`, and B4's `test_o3_drive_*` through
`REQUIRED_TESTS_O3`.

**What the O2 baseline cannot see.** The story-o2 archive holds six covered runs and no VOID, so G8/G9 never take
S1's VOID or A-BEATS path, nor VOID-ASYM's: **G10's synthetic cases are the only VOID-path baseline**, and an edit to
the coverage rule, the V-classes or VOID-ASYM is proven O2-neutral by G10 alone. S4's no-registry path is proven by
`test_o2_drive_voids_a_battle_without_a_registry` (G12): O2-shaped predictions, a battle on screen, V10 with O2's
message -- none of the existing `test_o2_drive_*` tests puts a battle up.

---

## 2. The drive

### 2.1 The model (keys the driver reads; the rest of the predictions is the analysis's)
- **`table: []`.** 61, 62 and 63 never grant control (0.2 #4), so there is no cell: control anywhere is V4.
- **`battles`** -- the registry, a list of rows, each STRICT (`segment_drive.battle_of`: an unknown key, a missing one
  or a wrong type raises `ValueError` before anything is driven, like `step_of`):
  ```json
  {"donor": 62, "sc": 1155, "scene": 338, "won": [1, 2], "lands": 63, "beat": "leo",
   "timeout_s": 180, "max_turns": 40, "land_s": 30, "land_cap_s": 120,
   "why": "62 e4 t1 ip1293 Battle(0,338) = BSC_TH_E002 (King Leo, 10186): ends by script once King Leo's own cur.hp <= 10000 (>= 186 damage) -- RunBattleCode(33,1), result 2 (WinPose off), folded to 1 at the over frame; its own RunBattleCode(37,63) lands the run in 63, fresh (F: ForkSiblingField(63) = 31213, s24)"}
  ```
  `donor` is the place of the VISIT the battle began in; `sc` the published SC (null = any); `scene` the published
  `battle.scene` (`battleMapIndex`, HarnessAgent.cs:1815); `won` the results that count the beat done (S1); `lands`
  the place the battle must hand the run to; `beat` the beat it sets (its value is the result); `timeout_s` and
  `max_turns` bound `fight()` (`max_turns` 0 raises at the first command prompt, before any attack: R-BATTLE-VOID's
  shape, 7.1); `land_s` is the LATE mark for the landing field's FieldHUD (past it the row records `land_late`, the run
  goes on) and `land_cap_s` the hard cap (past it: V14), 2.3 step 4.
  `battle_of` also checks the row against the predictions, before anything is driven (and at `--freeze`): `won` is
  exactly `[1, 2]` or `[1]` (the two shapes a scripted end can report; O3-SCENE then requires the one the scene's
  WinPose flag gives, 6.1) -- `[1, 2, 3]`, `[2]` or an empty list raise; `beat` is one of `pred["beats"]` and no
  step, naming rule or choice rule names it (only the executor sets it, with the int result); `timeout_s`, `land_s`,
  `land_cap_s` are positive numbers with `land_s <= land_cap_s`, `max_turns` an int >= 0 (a bool is not an int).
- **`stop_pages`** -- pages that VOID instead of being confirmed: `[{"match": "Env Play()", "why": "61-63's ambient
  error window 3 ('Error Env Play()  Slot=n', e0 t0 WindowAsync(6,0,3) + WaitWindow): Byte[13]/[14] arrived as 2 or 9"}]`.
  A page matches when `match` is a substring of its rendered text or of any `raw_texts` line.
- **`choices`**: O1's skip-movie rule only (2.5). **`naming: []`**. **`route: [61, 62, 63]`, `visits: [61, 62, 63]`,
  `end_fields: [64]`.** **`forbidden`**: O2's `off_route` pattern only (4.8). **`beats: ["leo"]`.**

### 2.2 The driver loop for O3 (O2's loop, rules in O2's order, with S4's two opt-in additions)
Every poll reads `st`, `sc` and `donor = place(fid, members)` as O2's does.
1. **End** (`fid in end_fields`, real 64 on both sides): the end state read (`read_end_state`), the last forbidden scan,
   `reached`. Unchanged -- but for **the end row** (the review, 11.7 #3; opt-in: `budget.end_row_s`, O3's draft 10 s):
   before returning, the drive waits up to `end_row_s` (never past the run's deadline) for the run's first trace row in
   an end place -- the row the analysis cuts at, `cut_at_end` over the live trace after its last arm -- and the `end`
   row records `end_row` {"seen", "f", "s"}. Rule 1 fires on the first poll that publishes 64, and the session closes
   the trace right after the drive returns: story-o1e closed it 1-4 frames after the field changed, its run 3 S before
   any row of 100 (covered, cut None). A wait that runs out is no VOID here: the analysis reads that run (A-NOEND, 5.1).
   Without the key, rule 1 is O1's and O2's exactly.
   **The stall watchdog** runs after rule 1, unchanged (its signature cannot see a movie: 0.2 #11; `no_progress_s` is
   sized to cover FMV003, 4.12).
- **1b (new, opt-in: `battles` non-empty) -- a NEW battle.** `st.in_battle` and `st.battle_epoch > self.battle_seen`:
  the battle executor (2.3) runs and owns the loop until the landing field is up; then `continue`. It sits BEFORE
  rules 9, 2 and 3 so that the field id a battle publishes at its over frame (0.2 #8) is never read as a load, a leave
  or a visit. `self.battle_seen` starts at the epoch published when the drive starts (only deltas mean anything).
9. A field id <= 0: waited out. Unchanged.
2. **Route.** On F only a member whose donor is on the route (31211-31213) or the end field; real 61/62/63 on F is
   V11 (game). Unchanged. (Real 63 after the battle is caught earlier, by the executor's landing judge, as V16.)
3. **Visit.** The order 61 -> 62 -> 63; a new visit runs the live forbidden scan. Unchanged.
4. **Naming**: V10 (none registered). Unchanged.
5. **A tutorial or a battle** that rule 1b did not answer (a tutorial outside a battle; a battle already answered and
   still up): V10. Unchanged -- and with no registry it is O2's rule exactly, so O2 sees no difference.
6. **A choice**: O1's readiness hold, then the rules (2.5); no rule -> V1. Unchanged.
7. **A page** (dialog open, text, control off).
   - **(new, opt-in: `stop_pages`)** a page matching a stop page: VOID **V5**, NOTHING pressed. `by` is `driver` when
     the run is in its first visit and that visit is the start place (the error window there is the START's: the
     warp's incoming Byte[13]/[14]), else `game` (62's or 63's error path is reachable only if the run's own fields
     wrote 2 or 9 to Byte[13]/[14], which no route store does: a fork deviation, which VOID-ASYM then reads).
   - Otherwise O1's page rule (record, `press("confirm", 3)`, a `press` row, wait 4 ticks). Unchanged. 61's stage
     lines and 62's play lines are `[TIME=-1]` windows closed by CloseWindow: a Confirm does nothing to them, and
     `timed` records them so the transcript folds them.
8. **Control held**, settled O1's way (`settle_s` 1.0 of consecutive control polls): V4 (the table has no cell).
   Unchanged. The engine zeroes control at every field start (0.2 #19), so a load cannot carry control in; the settle
   stays as O1's net, and a window up WITH control is an overlay, logged and never paged (O1's rule) -- in O3 the
   control itself is the VOID.
9. Otherwise wait.

`out()` gains `"battles": [battle rows]` and `"battle_epoch0"` (the `battle_epoch` published when the drive started,
which `self.battle_seen` starts at) only when the registry is non-empty, and `progress` carries the same two, so a
run that raises inside a battle still records them. O3-BATTLE (5.3) reads both.

### 2.3 The battle executor (`_Drive.battle(st)`)
1. **Match.** `epoch = st.battle_epoch`, `scene = st.battle["scene"]`, `vplace = place(self.cur, members)` (the visit the
   battle began in -- never the per-poll place, which the over frame can flip). The row is
   `battle_row(pred, vplace, self.sc, scene)` (pure): `scene` equal, `donor == vplace`, `sc` null or equal, and not yet
   answered in this run. No row: **V10 (game)** "an unregistered battle: scene {scene} (epoch {epoch}) in {fid} (place
   {vplace}) at SC {sc}" -- another scene, another place or SC, or the same row asked twice. `self.battle_seen = epoch`.
2. **Fight.** `bound = min(row["timeout_s"], deadline - now)`;
   `result = g.fight(timeout=bound, max_turns=row["max_turns"], finish=False)` (the default policy: Attack the first
   standing foe each turn; tutorials are dismissed inside, H7 counts them). It normally returns 2, read on the fade's
   first sample at field 62/31212 (0.2 #8); both 2 and 1 are in `won`.
   - `FightTimeout` (H7) with `bound` the row's own: **V15 (driver)** "battle {scene} reached no result within {bound} s /
     {max_turns} turns" -- King Leo's scripted end fires once (TH_E002 e1 t1 [601] latches `Map.Byte[24]`); a miss
     must cost `timeout_s`, not the run. With `max_turns` 0 (R-BATTLE-VOID) it raises at the first command prompt,
     before any attack, so the run stops mid-fight in BattleHUD by construction. With `bound` cut by the run's
     deadline: `HarnessError("the run's budget ran out in battle {scene}")`, which the session records as V13 like
     any budget.
   - `FightTimeout` kind "gone" (the review, 11.7 #2): the battle scene went away with no result while both bounds
     held -- a soft reset or a crash to the title mid-fight, an engine path that leaves the result 0. No bound ran
     out, so it is neither V15 nor the budget: an instrument stop, `HarnessError("battle {scene}'s scene went away
     with no result: ...")` (STOPPED, V13), the battle row logged first (`timed_out` False).
   - Any other HarnessError propagates (V13, STOPPED), as `fight()`'s instrument failures always have.
3. **Leave.** `g.leave_battle(stop_on_field=True)` (H8): it presses Confirm only while the battle scene is up and stops
   at the first sample with the scene gone (whatever the UI state still says) or FieldHUD. Each of its presses is logged
   as a `press` row (`why: "leave_battle"`, `pre` the sample it was pressed on, `post` None, `near` []). (The review,
   11.7 #1: its `timeout`, which was never read, is honoured, and the executor passes `min(row["land_cap_s"],
   deadline - now)`; a leave that stops on it -- `stopped` "timeout" -- goes on to the landing, whose clocks then end
   the run: V14 past `land_cap_s`, V13 past the deadline.)
4. **Land, in two tiers.** `landed = lambda s: not s.in_battle and s.ui_state == "FieldHUD" and s.field_id > 0`.
   First `g.wait_for(landed, timeout=row["land_s"])`. Past `land_s` the run is NOT voided: the wait goes on, to
   `min(row["land_cap_s"], deadline - now)`, and a landing that comes in that second tier is recorded as
   `land_late = {"frames", "s"}` (the landing's frames and seconds counted from the leave's end; None when on time).
   The fork path (battle, s24, 31213 fresh, its autosave: 0.2 #19) is never timed before the session -- F-SMOKE never
   fights, R-62/R-FULL are stock -- so a slow F landing must not turn into a one-sided game-attributed VOID, which
   VOID-ASYM (a) would read as NOT PROVEN with no re-run able to clear it. No field by the cap: **V14 (game)** "battle
   {scene} ended and no field came up within {land_cap_s} s" (a hang that long is a finding, as the watchdog's V14
   is). The cap cut by the run's deadline: `HarnessError("the run's budget ran out waiting for battle {scene}'s
   field")`, V13 like any budget. The report and the rehearsal record every `land_late` (5.4, 7.2); F9 sizes both
   marks.
5. **The flip, recorded.** From `g.states_since(frame0)`, the first sample with `in_battle` and a field id other than
   the battle's: its frame is the row's `flip_frame`, and that sample's result is `flip_result` -- 1 by the engine's
   order (0.2 #8: the fold and the flip are one call); None if no sample caught it.
6. **The row.** `{"k": "battle", "field", "donor": vplace, "visit", "sc", "scene", "epoch", "row" (its index), "beat",
   "frame0", "t0", "result", "turns", "seconds", "tutorials", "timed_out", "leave": {"presses", "uis", "stopped"},
   "flip_frame", "flip_result", "landed", "landed_place", "land_frame", "land_late", "t1", "v", "by", "why"}` -- logged
   and appended to `out["battles"]`; `beats[row["beat"]] = result` (an int: S1 counts nothing else); `self.since = now`
   (the watchdog); `self.walked = None`.
7. **The landing judge.** `want = row["lands"]`.
   - S: the landed id must be `want` (63).
   - F: the landed id must be a member whose donor is `want` (31213). The landed id equal to `want` itself -- REAL 63 --
     is **V16 (game)** "battle {scene} landed in real {want}, not member({want}) {member}: the s24 redirect did not
     fire". It is a FINDING: `rerun.stop_on: ["V16"]` holds the side's re-runs (S2), and O3-VOID-ASYM (a) reads it.
   - Anything else (62/31212: the battle returned to 62; any other field): **V11 (game)** "battle {scene} landed in
     {fid} (place {p}), not {want}".
8. Return; the loop's next poll starts the new visit (63) by rule 3.

### 2.4 Every research beat, and what handles it
The beats are `o3_research.json`'s `reconciled.route.beats`, with the critic's corrections.

| Beats | Field | Handled by |
|---|---|---|
| 1 | 61 | Nothing: Main_Init's ambient stores (4.4). No control (V4 if any, after the settle). |
| 2 | 61 | Rule 9, waiting: FMV003 (type 0) plays with no dialog and no control; nothing is pressed, so no skip dialog can open. Its whole length plus about 5 s sits inside the watchdog (`no_progress_s`, 4.12). |
| 3 | 61 | The page rule: 72-78, each a Confirm page (WindowAsync + WaitWindow), AFTER the movie's end. |
| 4 | 61 | The page rule on 79-86 (`[TIME=-1]`, closed by CloseWindow; a Confirm is inert; recorded `timed`). |
| 5 | 61 | Nothing: the exit (`Int16[2]:=100` ip363, `Field(62)`), then rule 3 (visit 62). |
| 6 | 62 | Nothing: Main_Init's ambient stores; the play's lines 87-95 by the page rule (inert, timed). |
| 7 | 62 | Nothing: the party rebuild and its stores (4.4). |
| 8 | 62 | Rule 1b: the registry row (62, 1155, 338) -> `fight()`, `leave_battle(stop_on_field)`, the landing. |
| 9 | 62 -> 63 | The executor's landing judge (2.3 step 7); then rule 3 (visit 63). |
| 10 | 63 | Nothing: Main_Init's ambient stores, loaded FRESH (O3-LANDING (c) proves it on the trace). |
| 11 | 63 | The page rule: 98, 100, 101 (Confirm pages); 96, 97, 99, 103 x3, 104 (timed: `[TIME=n]` sets the button inhibit, so a Confirm is inert on them -- 0.2 #19 -- and 63's transcript is deterministic). |
| 12 | 63 | Nothing: the exit (`Int16[2]:=100` ip820, `Field(64)`). |
| 13 | 64 | Rule 1: the end. |
| 14-16 | 64, 150 | Beyond the end (O4). |

### 2.5 Choice rules
O3 has no choice. The only one possible is the skip-movie dialog, opened only by a Confirm during FMV003 (FieldHUD.cs
275-286, cursor `ETb.sChoose = 1`, No); the driver presses only on pages and none is up during the movie.
```json
[{"donor": null, "sc": null, "match": "want to skip", "pick": "default", "once": false, "beat": null}]
```
O1's rule, kept as a net. Its publication is unmeasured: if R-SKIP (7.1, optional) shows the prompt line publishing
empty, the freeze adds a second rule matching the dialog's option line as R-SKIP measured it (F4). Any other choice
is V1.

### 2.6 VOID conditions (each a RouteVoid with its class, cell and attribution; the run is not covered)
O2's classes keep their meaning; O3 can raise these:

| | Condition in O3 | by |
|---|---|---|
| V1 | A choice no rule matches (anything but the skip dialog). | game |
| V4 | Control held anywhere, after the settle (the table is empty). | game |
| V5 | A stop page: the "Error Env Play()" window. Nothing is pressed. | driver in the start visit (the warp's state); game after |
| V10 | A naming screen; a tutorial outside a battle; a battle the registry does not answer (another scene, place or SC; a second battle). | game |
| V11 | The run left the route or its visit order (rule 2/3); the battle landed somewhere other than `lands` (not the s24 case). | game (O3 has no walks) |
| V13 | The run budget (inside a battle, or waiting for its field, too), or an unexpected exception: `STOPPED` -- a battle scene gone with no result (`FightTimeout` "gone", 2.3 step 2) among them. | driver |
| V14 | The watchdog; or a battle that ended with no field up within `land_cap_s` (a landing past `land_s` only records `land_late`). | game |
| **V15** (new) | The registered battle reached no result within its `timeout_s` / `max_turns` (`FightTimeout`). | **driver**: the driver's policy and bound own the fight; a one-off miss re-runs, and a structural one (every run of a side) fails VOID-ASYM (b) |
| **V16** (new) | On F, the registered battle landed in REAL `lands` (63), not its member: the s24 redirect did not fire. A FINDING (`rerun.stop_on`). | **game** |

V2, V3, V6, V7, V8, V9 and V12 cannot arise (no `once` rule, no default-take rule, no watched cell, no step, no
wait, no climb, and the only forbidden pattern is never backed: 4.8). The analysis repeats the trace-visible ones
(5.1), so a driver fault never turns into STOCK ONLY or FORK ONLY.

---

## 3. Harness additions (each minimal, opt-in, modelled in the FakeGame, tested)

Every default keeps today's behaviour; no existing caller changes.

**H7. `Session.fight`: a typed no-result, and what the fight did.**
- A new `FightTimeout(HarnessError)` (beside `HarnessError` and `StepRefused` in `harness/channel.py:86-90`, exported
  where they are), raised on both no-result exits instead of the plain HarnessError: the turns bound
  (session.py:7407-7411) and the timeout (:7442-7444), with the same messages. Every existing `except HarnessError`
  still catches it. `max_turns=0` is legal and raises at the first command prompt, before any `act` (the bound is
  checked before the command, :7407): R-BATTLE-VOID's way to stop mid-fight. (The review, 11.7 #2: a third kind,
  "gone" -- the battle scene went away with no result while both bounds held -- with its own message and `timed_out`
  False: no bound ran out.)
- `self.last_fight` is set on BOTH exits and gains `"seconds"` (wall time from the call), `"tutorials"` (screens
  `_dismiss_tutorial` closed inside the call) and `"timed_out"` (bool). Its existing keys are unchanged.
- Tests: `test_fight_raises_fight_timeout_without_a_result` -- a fake battle no attack can end (one enemy with a huge
  `hp`, no scripted end): `timeout=2` raises `FightTimeout` naming the timeout, `max_turns=1` raises it naming the
  turns, `max_turns=0` raises it with no `battlecmd` executed and the fake still in BattleHUD with result 0, and
  `last_fight["timed_out"]` is True in all three; `test_fight_counts_its_tutorials_and_seconds` -- scene 336 in
  `tutorial_scenes`: `last_fight["tutorials"] == 1`, `"seconds" > 0`.

**H8. `Session.leave_battle(*, timeout=90.0, stop_on_field=False)`: stop where the field begins, and say what it
pressed.**
- Always: `self.last_leave = {"presses": [{"frame", "ui", "in_battle", "field", "result"} for each press],
  "ended": ui_state, "field": field_id, "frame": frame, "stopped": "scene-gone" | "field" | "presses"}`. The return value
  (the UI state) is unchanged. (The review, 11.7 #1: `timeout` -- dead until then -- bounds the loop, checked before
  each Confirm and after the field test: `stopped` "timeout". The default 90 s outlasts the 40 Confirms.)
- With `stop_on_field=True`: before each press, if the sample shows the battle scene gone (`not in_battle`, whatever
  `ui_state` still reads -- it can lag as BattleResult while the field loads) or `ui_state == "FieldHUD"`, stop: never a
  Confirm into a loading field or onto its first windows (63's 96/97/98). The default (`False`) is O1's loop exactly,
  presses recorded.
- Tests: `test_leave_battle_stops_where_the_field_begins_and_logs_its_presses` -- H9's `battle_exit` (its four
  phases, the load lagging as BattleResult): with `stop_on_field=True` every recorded press has `in_battle` True and
  none is executed after the scene is gone; `stopped == "scene-gone"`; the control (`stop_on_field=False`) presses
  during the lag. `test_leave_battle_records_presses_on_o1s_path` -- a same-field battle (O1's shape): the loop and its
  return as today, the presses recorded.

**H9. FakeGame (opt-in knobs; each absent by default).**
- `battle_script_end = {"unit": <name>, "hp_raw_le": n, "result": r, "after_frames": k}` -- King Leo's latch: once
  that unit's `hp_raw` is <= n (after a command resolves), the battle ends with `result` `k` frames later, whoever is
  standing. Without it, today's `_settle_battle` (all foes down) is the only end.
- `battle_exit = {"field": id, "fade_frames": a, "result_frames": b, "load_frames": c, "arrive_control": False}` --
  the engine's end order (0.2 #8), in four phases: (1) the FADE, `a` frames: `battle_result` is the end's result (2)
  while the published field id is still the battle's and `battle_active` True, ui BattleHUD; (2) the OVER FRAME, one
  frame: the result folds 2 -> 1 AND the field id becomes `field`, together, ui "BattleResult", `battle_active` still
  True; (3) BATTLERESULT, `b` frames: `field`, result 1, `battle_active` True, ui BattleResult, no panel; (4) the LOAD,
  `c` frames: `battle_active` False, ui still "BattleResult" (the lag); then FieldHUD in `field`, control as
  `arrive_control` says, `_visit` bumped (a fresh load). No sample ever pairs `field` with result 2. Without it,
  `end_battle` is today's (same field, FieldHUD at once).
- `warp_field_only = False` -- True: `warp` refuses unless `ui_state == "FieldHUD"` ("warp refused (not on a field?)"),
  as the agent does (0.2 #9).
- `warp_arrive_control = True` -- False: a warp lands with control OFF (61-63 never grant it: the engine zeroes it at
  every field start and their `EnableMove`s are unreachable, 0.2 #4, #19). Today's warp sets control True, which is
  how a smoke built on `Session.warp()` -- whose `wait_playable` needs control -- would pass on the fake and hang 60 s a
  warp in the game. Every O3 fake test sets it False, B4's included.
- `soft_reset_ui = ("FieldHUD", "WorldHUD")` -- the UI states the soft-reset combo fires in (today's set, the
  default, so no existing test's fake changes). The engine's set is `("FieldHUD", "WorldHUD", "BattleHUD",
  "QuadMistBattle")` (`GetKey`, UIKeyTrigger.cs:94: 0.2 #9); every O3 fake test passes it. BattleResult is in neither:
  the combo is swallowed there either way. The FakeGame's soft-reset docstring gains the BattleHUD/BattleResult reading.
- A movie scene beat `{"movie": frames, "skip": {"header", "options", "default"}}` -- no dialog and no control for
  `frames` frames, ui FieldHUD; a Confirm during it opens the skip choice (cursor on `default`); answering the default
  resumes the movie for what remains, the other option ends it. While it plays the soft-reset combo is swallowed
  whatever `soft_reset_ui` says (MBG played: UIKeyTrigger.cs:241); a warp ends it (the field load destroys MBG).
- Tests: `test_fake_battle_script_end_ends_on_the_units_hp`, `test_fake_battle_exit_runs_the_engines_four_phases`
  (`fight()` returns 2, read in the fade at the battle's field; the first sample with `in_battle` and the exit field
  has result 1; no sample pairs the exit field with result 2; the load lags as BattleResult with `in_battle` False;
  then FieldHUD), `test_fake_warp_refuses_off_the_field_when_told`, `test_fake_warp_arrives_without_control_when_told`
  (and `Session.warp()` there times out on `wait_playable`, a raw warp plus a field-and-FieldHUD wait does not),
  `test_fake_soft_reset_follows_the_engines_ui_states` (with the engine's set: BattleHUD mid-fight -> the title;
  BattleResult -> swallowed; a playing movie -> swallowed; the default set: BattleHUD swallowed, as today),
  `test_fake_movie_beat_holds_and_offers_the_skip_dialog`.

**Not needed:** a movie state in the published state (impossible without an agent patch: 0.2 #11); a battle-scene
verb (the agent publishes `battle.scene`); a new choice or naming verb; NPC or region modelling (61-63 have none).

---

## 4. Predictions (draft v1: `O3Segment.draft()`)

### 4.1 Top level
```json
{"version": 1,
 "what": "O3: 61@1155 (warp, entrance 0) -> 62 -> battle 338 -> 63 -> Field(64), stock vs O1's tshp chain (members 31211-31213; PLAN.md, O3)",
 "rehearsals": [],
 "order": ["S","F","S","F","S","F"], "min_covered": 2, "rerun": {"max": 2, "stop_on": ["V16"]},
 "budget": {"run_s": 1200, "run_min_s": 600, "session_s": 7200, "settle_s": 1.0, "no_progress_s": 300,
            "end_row_s": 10.0},
 "start": {"S": 61, "F": 31211}, "entrance": 0, "scenario": 1155, "lang": "us",
 "end_field": 64, "end_fields": [64], "route": [61, 62, 63], "visits": [61, 62, 63],
 "stock_fields": [61, 62, 63, 64],
 "members": {"31200": 50, "...": "...", "31219": 3010}, "names": {"31200": "O1_TH_CGR", "...": "..."},
 "text_block": 2, "recovery": 4600,
 "seam": {"donor": 63, "to": 64, "why": "member(63) = 31213's Field(64) (63 e4 t1 ip828) stays real: the end, on both sides"},
 "cut_start": true,
 "start_first": "4.6", "start_music": "4.6", "start_residue": [[0, 0, 131], [1, 0, 4]], "residue_after_start": [],
 "sc_bytes": [0, 1],
 "chain": "4.3", "entrance_bytes": [2, 3],
 "writes": "4.4", "error_path": "4.5", "forbidden_sites": "4.5", "dead": "4.5", "start_dependent": [],
 "noise": "4.7", "forbidden": "4.8", "landing": "4.7",
 "end_state": "4.9",
 "battles": "4.10", "stop_pages": ["2.1"],
 "regions": {}, "hotspots": {}, "table": [],
 "choices": ["2.5"], "naming": [],
 "beats": ["leo"],
 "settings": "4.13"}
```
- `members` and `names` are O1's twenty (31200-31219, `o1_forks.json`): the deployed chain is one unit (one deploy, one
  revert record; text blocks 2 and 187), and P-DEPLOY, P-EB, P-FLOOR and the fingerprint read all of it. The route runs
  three of them.
- `start_residue` is `[byte, old, new]`: SC 1155 = 0x0483 writes byte 0 (0 -> 131) and byte 1 (0 -> 4); entrance 0
  leaves byte 2 at 0, so no row. `residue_after_start` is empty until R-FULL shows otherwise, with a byte-level reason.
- No `ladder`: O3 writes no SC (4.2). `start_dependent` is empty: under the raw warp no key on the route is start
  dependent (5.4's scope line).

### 4.2 No SC write (O3-NO-SC)
61, 62 and 63 neither write nor read `Global.UInt16[0]` (0 stores, 0 reads in each listing); the next SC store is O4's
(150 e3 t1 ip1966, 1190). So after the start the trace carries NO row over bytes 0-1: SC reads 1155 throughout. O2's
LADDER on an empty ladder would be a check that cannot fail; O3-NO-SC selects rows by BYTE SPAN (`span_rows`, any
width, target, mode or source; `c` rows too) and requires none.

### 4.3 The FieldEntrance chain (`Global.Int16[2]`; O3-CHAIN, in order; the first `old` is 0, the warp's entrance)
| # | donor | sid | tag | ip | off | value | what |
|---|---|---|---|---|---|---|---|
| 1 | 61 | 1 | 1 | 363 | 352 | 100 | 61's exit (the conductor's stage 7), then `Field(62)` ip371 |
| 2 | 62 | 4 | 1 | 1285 | 1274 | 0 | stage 10, before `Battle(0,338)` ip1293 |
| 3 | 63 | 4 | 1 | 820 | 809 | 100 | 63's exit (stage 110), then `Field(64)` ip828 |

Every op is `:=`. **62 e4 t1 ip1345 (`Int16[2]:=0`, off 1334) must not appear**: it runs only if the battle returned
to 62; it is registered in `forbidden_sites` (4.5) so O3-KEYS proves the site, and because CHAIN is exact over bytes
2-3, its row (a same-value store, still emitted once) would be a fourth row and fail CHAIN. The prologues'
`Int16[2]:=10000` (61 ip41, 62 ip45, 63 ip41) sit behind `Bit[184]==1`, false on the route: registered in `dead`
(4.5), so O3-KEYS proves each and O3-CENSUS counts them classified.

### 4.4 Registered writes (O3-WRITES: every covered run's keys are EXACTLY these and the chain, the noise aside)
Every op is `:=` but the four `++` (O2's key form: `op` mandatory, a compound value computed from its `prior`).

| donor | sid | tag | ip | off | target | value | what |
|---|---|---|---|---|---|---|---|
| 61 | 0 | 0 | 57 | 51 | Int16[9] | -1 | ambient (65535 as Int16) |
| 61 | 0 | 0 | 119 | 113 | Byte[13] | 0 | ambient: the route's branch (also `start_music`, 4.6) |
| 61 | 0 | 0 | 138 | 132 | Int16[11] | -1 | ambient |
| 61 | 0 | 0 | 200 | 194 | Byte[14] | 0 | ambient |
| 61 | 2 | 1 | 752 | 637 | Byte[8] | 125 | after FMV003 and pages 72-78 |
| 62 | 0 | 0 | 61 | 51 | Int16[9] | -1 | ambient |
| 62 | 0 | 0 | 123 | 113 | Byte[13] | 0 | ambient |
| 62 | 0 | 0 | 142 | 132 | Int16[11] | -1 | ambient |
| 62 | 0 | 0 | 204 | 194 | Byte[14] | 0 | ambient |
| 62 | 4 | 1 | 319 | 308 | UInt16[21] | 3585 | the play's party (0xE01: Zidane, Cinna, Marcus, Blank) |
| 62 | 4 | 1 | 603 | 592 | Byte[303] | 0 | |
| 62 | 4 | 1 | 637 | 626 | Byte[303] | 1 | `++`, prior 62/4/1/603 |
| 62 | 4 | 1 | 659 | 648 | Byte[303] | 2 | `++`, prior 62/4/1/637 |
| 62 | 4 | 1 | 681 | 670 | Byte[303] | 3 | `++`, prior 62/4/1/659 |
| 62 | 4 | 1 | 703 | 692 | Byte[303] | 4 | `++`, prior 62/4/1/681 |
| 62 | 4 | 1 | 1034 | 1023 | Byte[4] | 0 | PARTYCHK(5) false (ip1023 `:=1` not taken) |
| 62 | 4 | 1 | 1085 | 1074 | Byte[4] | 0 | |
| 62 | 4 | 1 | 1093 | 1082 | Byte[17] | 0 | |
| 62 | 4 | 1 | 1101 | 1090 | Byte[18] | 1 | |
| 63 | 0 | 0 | 57 | 51 | Int16[9] | -1 | ambient |
| 63 | 0 | 0 | 119 | 113 | Byte[13] | 0 | ambient |
| 63 | 0 | 0 | 138 | 132 | Int16[11] | -1 | ambient |
| 63 | 0 | 0 | 200 | 194 | Byte[14] | 0 | ambient |
| 63 | 14 | 1 | 805 | 330 | Byte[8] | 125 | stage 5, after 99 (a same-value store: emitted once) |

Every target is `Global.<width>[<index>]`; none is masked (0.2 #3). With the chain these are the route's 27 keyed
field stores; with the six masked prologue rows (`Bit[191]:=0` at ip22/26/22, `Bit[184]:=0` at ip49/53/49) the
research's 33 field rows. Why EXACT and not "at least" (O2's): O3's key set is small and fully enumerated by the
bytes, so any extra key -- even on both sides, where NULL cannot see it (a dead branch firing, an error path, a C#
write) -- is a claim failure, not noise. "Fully enumerated" is a checked claim, not a reading: every gEventGlobal
store site of 61, 62 and 63 (15, 28 and 15, 0 unresolved: 0.2 #15) is in `writes`, the chain, `start_first`, the
story-noise mask, `error_path`, `forbidden_sites` or `dead` (4.3-4.6), and O3-CENSUS (6.1) fails offline on any site
outside them; O3-KEYS proves every listed site a real store of its value. R-FULL must show the exact set before the
freeze (F6).

### 4.5 The error path, the forbidden site and the dead sites (registered so O3-KEYS proves each; never expected)
`error_path` -- each Main_Init's ambient music branch for an incoming Byte[13]/Byte[14] of 2 or 9 (`:=9`, the debug
window 3 "Error Env Play()", then `:=0`). All are `:=`:

| donor | sid | tag | ip / off | target := value |
|---|---|---|---|---|
| 61 | 0 | 0 | 97/91, 178/172, 349/343, 383/377 | Byte[13]:=9, Byte[14]:=9, Byte[13]:=0, Byte[14]:=0 |
| 62 | 0 | 0 | 101/91, 182/172, 346/336, 380/370 | the same four |
| 62 | 0 | 10 | 580/52, 614/86 | Byte[13]:=0, Byte[14]:=0 (Main_Reinit: never runs, 62 is not resumed) |
| 63 | 0 | 0 | 97/91, 178/172, 362/356, 396/390 | the same four |

`forbidden_sites`: `{62, 4, 1, 1345, 1334, Int16[2], 0}` (4.3).
A 61 error-path row is the START's fault: `why_void` uncovers the run (A-START, 5.1) and the live stop page VOIDs it
(V5, driver). A 62/63 one is a fork deviation: the live stop page VOIDs the run (V5, game -> VOID-ASYM), and in a
covered run its keys are extra keys (O3-WRITES).

`dead` (round 2: the census's ten unlisted sites, 0.2 #15) -- each a real store (O3-KEYS) whose guard is false on the
route, every one `:=`; a row from any of them in a covered run is an extra key (O3-WRITES), and the three
`Int16[2]:=10000` would also be a fourth chain row (O3-CHAIN):

| donor | sid | tag | ip / off | target := value | guard (at) | why false on the route |
|---|---|---|---|---|---|---|
| 61 | 0 | 0 | 41/35 | Int16[2] := 10000 | `Bit[184] == 1` (ip30) | Bit[184] is 0: New Game leaves it 0 (O2's and O1's traces: old 0 at the first Bit[184] row) and each prologue clears it right after (ip49) |
| 61 | 0 | 0 | 130/124 | Byte[13] := 1 | else of `Int16[9] < 0` (ip108) | ip57 has just set Int16[9] to 65535, -1 as Int16 |
| 61 | 0 | 0 | 211/205 | Byte[14] := 1 | else of `Int16[11] < 0` (ip189) | ip138 has just set Int16[11] to -1 |
| 62 | 0 | 0 | 45/35, 134/124, 215/205 | the same three | the same, 4 bytes on (ip34, ip112, ip193) | the same (62's prologue clears Bit[184] at ip53; 61 already did) |
| 62 | 4 | 1 | 1023/1012 | Byte[4] := 1 | `PARTYCHK(5)` (ip1014) | Quina is not in the party ip349-ip594 has just rebuilt to [Zidane, Cinna, Marcus, Blank] (`AllCharactersAvailable` 1 changes menus only) |
| 63 | 0 | 0 | 41/35, 130/124, 211/205 | the same three as 61 | the same | the same |

### 4.6 The start (O3-START)
```json
"start_first": {"donor": 61, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 22, "off": 16, "target": "Global.Bit[191]",
                "value": 0, "op": ":=", "what": "61's Main_Init: its first store"},
"start_music": {"donor": 61, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 119, "off": 113, "target": "Global.Byte[13]",
                "value": 0, "op": ":=", "old": 1,
                "what": "61's ambient branch from the warp's Byte[13] 1 (field 70's prologue :=1 at ip130; the warp leaves FMV001 before its tail's :=2)"}
```
`old: 1` is the incoming value as O2 MEASURED it -- in field 100, not in 61: all six O2 runs show old 1 at their
first Byte[13] row after the same New-Game-plus-warp start (100 e0 t0 ip138, old 1 new 1). The warp leaves that
state whichever field it targets, so 61 should read old 1 at ip119, but no run has measured it IN 61 yet: F7 is the
first measurement there. A true O2 end hands 61 a 3 (O2's traces: 61 ip119 old 3 -> 0); both take ip119. A 2 would
take ip97 and the error window: the start state is the instrument's (F7 confirms `old` from R-FULL).

### 4.7 Noise, and the battle's own rows
```json
"noise": [{"not_m": 1, "target": "Global.Byte[206]",
           "why": "battle 338's AI (BSC_TH_E002 e1 t1 ip267): Byte[206] := SYSVAR[0] each frame until ATB starts (random value and count)"}],
"landing": {"route_places": [61, 62, 63], "last_place": 63, "end": 64,
            "battle": {"place": 62, "m": 2, "sid": 1, "tag": 1, "ip": 267, "target": "Global.Byte[206]"},
            "before": {"place": 62, "sid": 4, "tag": 1, "ip": 1285, "target": "Global.Int16[2]", "value": 0},
            "fresh": {"place": 63, "sid": 0, "tag": 0, "ip": 22, "target": "Global.Bit[191]", "value": 0},
            "end_row": {"place": 64, "sid": 0, "tag": 0, "ip": 22, "target": "Global.Bit[191]", "value": 0}}
```
`before` is chain #2, the last store 62 makes before `Battle(0,338)` at ip1293 (L62: nothing global between); `fresh`
is 63's first store, from the Main_Init a fresh load runs; `end_row` is 64's first store, the row the end cut must be
(LANDING (e)). All three are read RAW (two are masked Bit[191] sites).
- The noise is O1's legacy shape (`is_noise`: every key of that target whose mode is NOT field mode), and ONLY
  Byte[206]: O1's second row (Byte[199], TH_E001's) does not come along. TH_E002 stores no Byte[199] (0.2 #1).
- The legacy shape is keyed by target and mode, so alone it would also hide ANOTHER battle's Byte[206]. The SITE is
  pinned by O3-LANDING (b): every battle-mode row must be exactly `landing.battle`'s store (m 2, e1 t1 ip267,
  Byte[206]) in member(62)/62, so a Byte[199] row, a Byte[206] from another SITE (TH_E001's e0 t1 ip93, say), or a
  battle row in real 62 on F is a FAILURE, even when symmetric. The site does NOT pin the SCENE: TH_E001 (336) stores
  Byte[206] at the same e1 t1 ip267 (0.2 #1). The scene is pinned by O3-BATTLE (5.3), from the driver's log: the
  registry asserted scene 338 live (V10 otherwise), the run's log holds exactly one battle row, scene 338, whose epoch
  is the drive's first + 1 and whose start lies inside the window O3-LANDING (c) puts every battle-mode row in. So
  another scene fought in 338's place fails O3-BATTLE, never only a site check.
- The count of Byte[206] rows may be 0 (0.2 #1: the first Main pass jumps over the store to the ATB test). Zero
  battle-mode rows is allowed -- nothing then is noise -- and the count is reported per run (5.4); every LANDING
  clause is anchored on registered keys, never on these rows.
- What is deliberately NOT noise: nothing else on the route is random or timing-bound (research nondeterminism 1-6).
  FMV, page and battle timing change no store.

### 4.8 Forbidden (O2's patterns and backing rule; O3 registers one)
```json
[{"off_route": true, "cause": "walk",
  "why": "a write off the route: S, a place outside route + end_fields; F, a field that is neither a member whose donor is on the route nor an end field (real 61/62/63 on F: the s24 leak)"}]
```
`walk` backing needs a `step` row with a V11 landing; O3 has no steps, so a hit is never backed: it is a FINDING
(O3-FORBIDDEN, judged over EVERY run, VOID ones included). On F, the rows of real 63 that a leaked run writes before
its V16 VOID are exactly such hits -- so the leak fails FORBIDDEN as well as VOID-ASYM, with the rows named.

### 4.9 End state (read live on arrival in 64; O3-STATE (b))
```json
{"Global.UInt16[0]": 1155, "Global.Int16[2]": 100, "Global.UInt16[21]": 3585, "Global.Byte[303]": 4,
 "Global.Byte[4]": 0, "Global.Byte[17]": 0, "Global.Byte[18]": 1, "Global.Byte[8]": 125,
 "Global.Byte[13]": 0, "Global.Byte[14]": 0, "Global.Int16[9]": -1, "Global.Int16[11]": -1,
 "Global.Bit[191]": 0, "Global.Bit[184]": 0,
 "Global.Byte[6]": 0, "Global.UInt16[19]": 0, "Global.Byte[472]": 0, "Global.Int16[469]": 0,
 "Global.Bit[3717]": 0, "Global.Bit[3718]": 0}
```
The first fourteen are what the route leaves; the last six are untouched by it and hold New Game's 0 after the raw
warp (after a real O2 they would hold 3, 1799, 4, 1042, 1, 1 -- the scope line, 5.4). Byte[206] is excluded (random).
64's Main_Init rewrites only equal values before the read can land (Bit[3815]:=0, Byte[475]:=0, Byte[8]:=125, the
ambient keys): the read is stable through it.

### 4.10 The battle registry
One row, 2.1's. Its numbers are drafts: `timeout_s` 180, `max_turns` 40, `land_s` 30, `land_cap_s` 120 (F9 re-sizes
them). R-BATTLE-VOID overrides only `max_turns`, to 0 (7.1).

### 4.11 Coverage beats
`leo`: the registered battle's result, done when it is an int in `won` [1, 2] (S1). Plus `end == "reached"`. The
landing is not a beat: a wrong landing is a VOID with its class (V11, V16), read per side by VOID-ASYM, never a
quietly uncovered run. A covered run's battle is then re-read from its log by O3-BATTLE (5.3).

### 4.12 Budget and recovery
The estimate is about 6 minutes a run (FMV003's 84.8 s file plus the fade, 10 Confirm pages, about 17 timed or
scripted lines, a battle of >= 186 damage, 63's scene). Drafts: `run_s` 1200, `run_min_s` 600, `session_s` 7200
(6 runs + 2 re-runs with slack), `settle_s` 1.0, **`no_progress_s` 300** (3 x the ~90-100 s arrival-to-page-72
stretch, which the signature cannot see move), `end_row_s` 10 (rule 1's wait for 64's first trace row, 2.2: the
review, 11.7 #3). F9 replaces all of them from the rehearsals. Recovery is `end_run`:
warp to 4600 first (from 64, a FieldHUD field; from 61 mid-movie, where the soft reset is dead and the warp works),
the soft reset directly from inside a battle only mid-fight (BattleHUD, result 0), and from a battle's end sequence
the wait for its field, then the warp (S3). The session ENDS through `end_run` too (S5), never a bare ladder. F8
proves the first from 64, F3 the reset from inside battle 338 mid-fight.

### 4.13 Settings (P-SETTINGS; the fingerprint; the report's scope)
```json
{"Battle": {"Enabled": "1", "SFXRework": "1", "Speed": "5", "CustomBattleFlagsMeaning": "0"},
 "Cheats": {"Enabled": "1", "AutoBattle": "1", "SpeedMode": "1", "SpeedFactor": "3", "SpeedTimer": "0",
            "BattleAssistance": "1", "Attack9999": "1", "NoRandomEncounter": "1", "MasterSkill": "0", "LvMax": "0",
            "GilMax": "0"},
 "Hacks": {"Enabled": "1", "AllCharactersAvailable": "1", "SwordplayAssistance": "1", "DisableNameChoice": "0"},
 "Control": {"SoftReset": "1", "TurboDialog": "1", "BattleAutoConfirm": "1", "DialogProgressButtons": "\"Confirm\""}}
```
Raw ini values as the engine takes them (the last assignment wins; read by `ini_settings`). Today's install, measured
(0.2 #13); F12 confirms the rehearsals ran under them.

---

## 5. Checks (O3's analysis)

### 5.1 Reading a run: the COVERED rule
O2's rule (skipped, install changed, the drive did not reach the end, a beat not done (S1: a registered battle's
beat is done only when it holds an int in its row's `won`), no or an incomplete trace, A-NOSTART, a BACKED forbidden
hit, A-MISMATCH), plus:
- **A-START** (driver): the run's rows hold a registered `error_path` site of the START place (61) -- the warp's
  incoming Byte[13]/[14] took the error path. "the start state took 61's error path: <row>".
- **A-NOEND** (driver; the review, 11.7 #3): the drive reached the end and the trace reads whole, yet it holds no row
  in an end place, so there is no end cut -- the trace was collected before 64's first store. story-o1e's run 3 S is
  this race (covered there, its cut None): every O1 run closed its trace 1-4 frames after the field changed. Real 64 is
  the same field on both sides, so the missing row says nothing about the fork: the run is the driver's, never O3-LANDING
  (e)'s finding. Rule 1 waits for that row first (`budget.end_row_s`, 2.2), so A-NOEND marks a wait that ran out.

A drive VOID carries its V-class (2.6). The report lists every uncovered run's reasons per side.

### 5.2 The cuts
O2's: `cut_at_start` from 61's first `w` row (the residue in field 70 goes to `pre`), `cut_at_end` at the first row in
place 64. On F, 64 is no member, so its place is 64 itself; the `off` row (collected in 64 before `end_run`) is kept
as an `e` row and gives the digest its one seam (31213 -> 64), as O1's and O2's. The two cuts are not symmetric:
`cut_at_start` takes only a `w` row (residue cannot become the start), but `cut_at_end` takes the first `w` OR `r`
row in an end place (segment_trace.py:126-135), so a residue row at the 63 -> 64 boundary would itself become the cut
and vanish from every check. START (a)/(b) pin the front cut; LANDING (e) now pins the back one to 64's own first
store (`landing.end_row`).

### 5.3 The checks, in order, each with the mutant that makes it fail (section 8 registers every one)
**All-run checks** (every run with a readable trace, judged even when COVER is short):
- **O3-FORBIDDEN** (inherited): no unbacked forbidden hit. Mutant: lands-real-63 (F rows in real 63: off the chain).
- **O3-VOID-ASYM** (inherited): (a) a game-attributed class (with its cell) on one side only; (b) every run of one side
  VOID in one class while the other has >= `min_covered` covered. Mutants: v16-all-F (a and b), unregistered-battle-F
  (a), control-S (a), v15-all-F (b, a driver class), error-path-63-F (a).

**Then:**
- **O3-FROZEN**, **O3-COVER**: O2's. Mutant: predictions-changed; beat-missing.

**Core checks** (over the covered runs):
- **O3-START.** (a) `pre` is EXACTLY `start_residue` (kind `r`, `(byte, old, new)` as a multiset), nothing else before
  the start; (b) the first `w` row in place 61 is `start_first`, read RAW (Bit[191] is masked); (c) the first Byte[13]
  row in place 61 is `start_music`: e0 t0 ip119 `:= 0` with `old == start_music.old` (1). Its detail counts the
  residue rows from the predictions (O2's hard-codes 3). Mutants: start-residue-wrong (a), front-cut-write (a),
  start-first-missing (b), start-music-old-wrong (c).
- **O3-NO-SC.** No kept row over `sc_bytes` (0-1) after the start: `span_sequence(rows, rk, [0, 1], [], 1155)` must
  return nothing (a `w` row of any width or source fails by name, keyed or not; a `c` row over the span fails as a
  suppressed repeat). Mutants: sc-write-fork (a C# `cs` write of UInt16[0] in 62, F only), sc-write-both (the same on
  both sides: NULL passes it, NO-SC does not); **sc-harness-poke-both** (every run: a `src: harness` row on Byte[0]
  in 61 after its ip752 -- the one row NO-SC alone catches: the digest keeps harness rows out of its keys
  (storytrace.py:811-813) and STATE's `_state_rows` drops them, so WRITES, NULL, STATE and RESIDUE all pass it); unit
  no-sc-span (a Byte[1] row). Every keyed SC row is also an extra key, so the other two fail WRITES as well.
- **O3-CHAIN.** O2's `span_check` over `entrance_bytes` (2-3) with 4.3: exactly the three keys, in line order, each
  `old` the previous value, the first from 0. Mutants: chain-dropped-fork, battle-returned-to-62 (ip1345, a fourth
  row), chain-first-old-wrong (CHAIN alone).
- **O3-RESIDUE** (inherited): no unmasked residue after the start beyond `residue_after_start` (empty). Mutant:
  residue-after-start.
- **O3-WRITES (exact).** For every covered run: `{k for k in digest.keys if not is_noise(k, pred)}` ==
  `{wkey(k) for k in writes + chain}`. Its detail names the missing and the extra keys per run. Exactness rests on
  O3-CENSUS (every store site of 61-63 classified, 6.1) and O3-KEYS (every listed site real). Every non-noise key is
  in its set, battle-mode ones included: a Byte[199] m 2 row is an extra key. Mutants: fork-drops-a-write (missing),
  writes-extra-symmetric (62 ip1023 `Byte[4]:=1`, a proven `dead` site, on both sides: extra; NULL passes it).
- **O3-NULL**, **O3-STABLE**: O1's, with O3's legacy noise set aside (the battle's Byte[206] keys, random values).
  Mutants: fork-drops-a-write (NULL), byte199-fork (NULL, STABLE), byte206-field-mode-fork (NULL: the legacy noise
  covers m != 1 only).
- **O3-SEAM** (inherited, `seam` {63 -> 64}): no seam key, no across-seam or seam-only key, every Seam member(63)
  [31213] -> 64. NULL cannot see a seam leak (`Comparison.stock_only` leaves out keys with a seam count). Mutants:
  lands-real-63-covered, battle-rows-real-62-fork.
- **O3-LANDING (new).** For every covered run (F with the members map; S with its own ids):
  - (a) every field-mode (`m` 1) `w`/`c` row ran in its place's own field: a row whose place is 61/62/63 carries fld
    member(place) on F (31211/31212/31213) and the place itself on S, and no field-mode row stands in any place but
    61, 62 or 63 between the start and the cut;
  - (b) every battle-mode row (`m` != 1, `w` and `c`) is `landing.battle`'s store: m 2, sid 1, tag 1, ip 267,
    Global.Byte[206], fld member(62) (31212) on F / 62 on S. ZERO such rows is allowed (0.2 #1); the detail gives the
    count per run;
  - (c) anchored on registered keys, never on the battle rows (which may be none): the run holds `landing.before`
    (62 e4 t1 ip1285, chain #2, at member(62)/62); the next field-mode `w` row after it is `landing.fresh` -- 63 e0
    t0 ip22 `Bit[191]:=0` at member(63)/63: 63 loaded FRESH from the battle's own `RunBattleCode(37,63)`; no
    field-mode `w` row of place 62 follows `before` (62 was never resumed: its Main_Reinit and ip1298-ip1353 never
    ran); and every battle-mode `w` row lies between `before` and `fresh`;
  - (d) the last field-mode `w` row before the end cut is in place 63 (`last_place`), and the run's `end` log row names
    field 64 itself (real, on both sides); the seam's record is O3-SEAM's;
  - (e) the END: the end cut (`r["cut"]`) is the line of a raw `w` row that is `landing.end_row` -- 64 e0 t0 ip22
    `Bit[191]:=0` at fld 64 -- on both sides (5.2: an `r` row first in 64 would otherwise become the cut unseen).

  (c), (d) and (e) read `w` rows only: the engine writes every `c` (count) row at the epoch's close, after the end, so
  a `c` row's position says nothing about when its stores ran; (a) and (b) read both. The detail names the clause.

  Mutants, each registered with the clause its detail must name, and where one exists, one that fails LANDING ALONE:
  (a) lands-real-63-covered (with FORBIDDEN, SEAM, WRITES -- (a) can never fail alone: FORBIDDEN's `off_route`
  pattern reads the same raw `w` rows by `fld` over every run, and each route donor has one member, so every row (a)
  rejects is also an unbacked hit; (a) stays as the covered-run statement of the law); (b) **other-battle-noise-both** (TH_E001's e0 t1 ip93 site, which the
  legacy noise alone would hide: LANDING alone), battle-rows-real-62-fork, byte199-both (with WRITES); (c)
  **63-main-init-late-both** (every run: 63's e0 t0 rows after its e14 t1 ip805 row -- the same keys, the same per-target
  order: LANDING alone), battle-returned-to-62, battle-zero-rows-62-resumed, fresh-missing; (d)
  **last-place-61-repeat-both** (every run: a second 61 e0 t0 ip119 `Byte[13]:=0` row after 63's ip820 -- a registered
  key again, so WRITES, NULL and STATE pass: LANDING alone), last-place-wrong (61 ip130, a `dead` site: with WRITES);
  (e) **end-boundary-residue-both** (every run: an `r` row in place 64 before its ip22 -- the cut lands on it and every
  other check reads the base run: LANDING alone).
- **O3-BATTLE (new; claim integrity #2).** The trace cannot say which battle wrote its rows (0.2 #1), so for every
  covered run the analysis re-reads the driver's own record of it, from the run log (`_run_log`):
  - (a) exactly ONE `battle` row; it is registry row 0, scene 338, donor 62, its result an int in `won`, `beat` "leo"
    with `beats["leo"]` equal to that result, no `v`;
  - (b) its `epoch` is the run's `battle_epoch0` + 1: no other battle began since the drive started;
  - (c) `landed` is 63 on S and 31213 on F, `landed_place` 63;
  - (d) the field-mode `w` rows nearest its `frame0` in the trace's own `f` (the clock the driver's frames share:
    `segment_drive._visit_at` already joins them) -- the last at or before it and the first after it -- are in place
    62 and place 63: the battle the log names began at the 62 -> 63 boundary, where LANDING (c) puts every
    battle-mode row (in a run LANDING passes, those two rows are `before` and `fresh`). Not "every battle-mode row has
    `f` in [frame0, land_frame]": `frame0` is the driver's first POLL that saw the battle -- up to a poll, or a page
    press, after the scene went live -- and the AI's first `[539]` store can precede it; both ends here are trace
    rows, so nothing races.
  Mutants: battle-scene-336 (every run's log names scene 336, the trace's rows all e1 t1 ip267: LANDING passes them,
  BATTLE alone fails), battle-two-rows (BATTLE alone), battle-epoch-skip (epoch = `battle_epoch0` + 2: BATTLE alone),
  battle-frame0-late (`frame0` after 63's ip22 row: BATTLE alone); battle-returned-to-62 and
  battle-zero-rows-62-resumed also fail (d) (62's ip1345 is the first field row after `frame0`); (c)
  battle-landed-real-63-log-F (every F run's log names real 63) and battle-landed-member-log-S (every S run's log
  names 31213), each BATTLE alone (the review, 11.7 #5).
- **O3-MASKED** (inherited): the story-noise regions per side. Mutant: masked-differs (every F run without its Bit[184]
  rows).
- **O3-STATE** (inherited): (a) each unmasked target's emitted write history, identical across every covered run of
  both sides, in order; suppressed stores as a set; the registered noise (Byte[206] at m 2) left out; (b) every
  covered run's live `end_state` equals 4.9. Mutants: end-state-differs (b), fork-drops-a-write (a).
- **O3-JOIN** (inherited): every field row joins a store in the bytes its field ran (battle rows are census gaps, never
  failures: `storytrace._locate`). Mutant: join-failure.
- **O3-THROW** (in `run`, inherited): nothing thrown through EventEngine, EBin, StoryTrace or HarnessAgent.

**VERDICT:** O1's `verdict()`: PROVEN, NOT PROVEN: <failed>, or VOID: <void>; a failed check outranks a void one, so
FORBIDDEN and VOID-ASYM make a short session NOT PROVEN (the s24 leak reads "NOT PROVEN: O3-FORBIDDEN,
O3-VOID-ASYM", never VOID).

### 5.4 Report-only (`report_extra`, after the shared body)
- **"US session" is said where summaries are read**, not only here: O3-BUILD's title (6.1), the language line below,
  `o3_forks.json`, and the PLAN.md O3 heading and the CLAUDE.md milestone line that record a PROVEN O3 (C4). The
  VERDICT line is the shared body's (O1's `verdict()`) and stays as it is.
- **Scope**, three lines:
  - start dependence (gEventGlobal values only): "under the raw warp no key on the route is start-dependent: 61 reads
    Byte[13]/Byte[14]/Bit[184] before writing them and takes the same branch from the warp's (1, 0, 0) as from a true
    O2 end's (3, 0, 0); 62 writes UInt16[21] and Byte[303] before reading them; battle 338 reads Byte[16..18] (0, and
    17/18 written by 62 first); 63 reads nothing global. The party is rebuilt by 62 e4 t1 from [Zidane] (here) or
    [Vivi] (after O2) to the same four. Not covered: party data, items, gil, AP, cards, field 70's override state, and
    the six untouched targets' values after a real O2 (4.9)";
  - settings: the `settings` dict as recorded in the session's fingerprint;
  - language: "a US session (P-LANG): the members' jp/fr/gr/it/es .eb are US bytecode (accept_us_build), and block 2's
    uk copy is the US text (the KNOWN-KIT-DEFECT line below)".
- **The battle, per run:** scene, epoch (and `battle_epoch0`), result (and whether the harness read 2 or 1), turns,
  seconds, tutorials, the leave presses (count, the UI states pressed in, how it stopped), the flip frame and its
  result, the landing (id, place, frames from the end to FieldHUD) and `land_late` when the landing passed `land_s`,
  the trace's battle-mode `w` row count (0 allowed) and their sites, and V15/V16 when raised.
- **The session's end:** `session["ended"]` (S5): its recovery rows and whether the title came back.
- **61's movie, per run:** the arrival frame (the visit row) and the first page press (frames, seconds).
- O2's sections, copied (not called -- O2's names O2's scope line and SC timeline): VOID reasons per side, the masked
  counts, the forbidden hits with their backing, the P-TEXT KNOWN-KIT-DEFECT lines, the folded transcripts.
- **Re-runs held:** `rerun_held` (S2), when present.

---

## 6. Offline check and preflight

### 6.1 `--offline-check` (the install and O1's build, read-only; reads `--predictions`, else the frozen file, else the DRAFT, and prints which)
- **O3-BUILD (titled "a US session's build")**: `Segment.build_check` with `accept_us_build`: today "140 files; other
  languages: 15 own-language, 105 us-build" (= O1-BUILD). The title carries the limit so no summary of a green
  O3-BUILD can drop it: the members' other-language `.eb` are US bytecode, and the claim is a US session's.
- **O3-TEXT:** O2's `text_check` on block 2 against the O1 build: today "KNOWN-KIT-DEFECT 1, FAIL 0, 6 byte-equal of
  7 languages", and the CLI prints the defect's own line ("KNOWN-KIT-DEFECT uk: ships stock us (3a6f3246c2; stock uk
  7ac9f17435): ..."). A us mismatch would FAIL (the session language).
- **O3-KEYS:** O2's `keys_check` on the filtered copy (1.3): chain, writes, `forbidden_sites` + `error_path` + `dead`,
  `start_first`; `start_music` is a writes site and is checked with them. Today (0.2 #3, measured with `dead`): "53
  sites (53 keys), every op in its statement, 4 compound values computed from their priors, none masked".
- **O3-REGIONS:** O2's `regions_check` over route [61, 62, 63] with no region registered: "0 regions, 0 hot-spots, 0
  gateways all registered" -- it FAILS the day a gateway or a Confirm hot-spot appears in a route field.
- **O3-SCENE (new):** for every `battles` row, `scene_census(name)` over the install's own scene (`_scenedb.SCENES`
  -> `BSC_<name>`; `battle.extract.read_scene_assets(name)`; `scene_codec.parse_scene(raw16)`; `EbScript` +
  `storytrace.instruction_stores` over the scene's `.eb`). It reads the BASE install's copy, not the copy the engine
  loads through the mod stack; P-STOCK-BATTLE (6.2) proves those are the same, and the detail says so.
  - `won` is EXACTLY what the scene's WinPose flag allows: `[1, 2]` with WinPose off (flags & 0x10), `[1]` with it on
    (a `won` of `[1, 2, 3]`, which would count a defeat as covered, FAILS here and raises in `battle_of`);
  - entry 0 tag 0's `RunBattleCode(37, N)`: N == `lands`;
  - the scene's gEventGlobal stores, every entry and function: exactly `landing.battle`'s site (sid, tag, ip, target),
    and the noise pattern's target is that site's;
  - every store the walker cannot resolve (`instruction_stores` -> `("unknown", ...)`) is classified by its statement's
    lvalue token (`lvalue_class`): `B_SYSLIST[n]` is a battle target list, not gEventGlobal; any other token FAILS,
    naming the site -- an unresolved store is never silently skipped;
  - entry 1 tag 1 holds the end test `B_SYSLIST[1] B_MEMBER(36) const(c) B_LE_E` with c below type 0's MaxHP (the
    detail states the damage it needs).
  Today: "338 BSC_TH_E002, the base install's copy (P-STOCK-BATTLE: the one that loads): flags 0x1839 (WinPose off:
  won exactly [1, 2]); RunBattleCode(37, 63) = lands 63; 1 gEventGlobal store, Global.Byte[206] at e1 t1 ip267; 24
  unresolved stores, all B_SYSLIST[0] (target lists, not gEventGlobal); end at cur.hp <= 10000 of 10186 (>= 186
  damage)".
- **O3-CENSUS (new; claim integrity #3):** `store_census([61, 62, 63], stock, pred)` -- `instruction_stores` over EVERY
  function of each stock field (the census script's walk: `ScriptIndex.instrs` per entry and tag). Every Global store
  site must be in `writes`, the chain, `start_first`, the story-noise mask (`storytrace.noise_regions`: the Bit[191]
  and Bit[184] prologue rows), `error_path`, `forbidden_sites` or `dead`; an unresolved store must be classified by
  `lvalue_class` (none today); a function that does not decode FAILS. It FAILS naming every site outside them. Today
  (0.2 #15): "61: 15 store sites, 62: 28, 63: 15 -- all classified (writes 5/14/5, chain 1/1/1, masked 2/2/2 (61's
  ip22 is start_first), error_path 4/6/4, forbidden 0/1/0, dead 3/4/3); 0 unresolved".

### 6.2 `--preflight` (the live install, read-only; GREEN today, since nothing needs deploying)
- **P-MANIFEST:** `o3_forks.json` members == the predictions', `deployed: true`.
- **P-DEPLOY**, **P-EB**, **P-FLOOR:** the base's, over O1's twenty: today PASS (20 members; 20 x 7 files).
- **P-STOCK:** no mod folder overrides 61, 62, 63 or 64: today none.
- **P-TEXT:** O2's `text_rule` on every folder's block 2: today FF9CustomMap ships all 7, PASS with the uk
  KNOWN-KIT-DEFECT line, which the session report repeats.
- **P-RECOVERY:** 4600 registered: today in FF9CustomMap-world.
- **P-DONOR (new):** every route donor (61, 62, 63) appears in exactly ONE ForkDonorPatch row across every stacked
  folder (`rung3_trace._fork_donor_rows`), its member's: today 61 -> 31211, 62 -> 31212, 63 -> 31213; the duplicated
  donors are 312 and 350-359 only. A donor forked twice sets `ForkSiblingMap[donor] = -1` (DataPatchers.cs:156-160)
  and battle 338 would leak the fork run into real 63.
- **P-SETTINGS (new):** `ini_settings(Memoria.ini)` == `pred["settings"]` key for key; a FAIL names each difference.
- **P-STOCK-BATTLE (new; claim integrity #4):** battle 338 is STOCK on both sides, as P-STOCK makes fields 61-64.
  `battle_stock(roots, 338, names)` over every stacked folder (the `FolderNames` order): (a) no file whose path names
  `EVT_BATTLE_TH_E002` (case-insensitive: `BattleMap/BattleScene/EVT_BATTLE_TH_E002/` raw16 and raw17, and
  `EventBinary/Battle/<any lang>/EVT_BATTLE_TH_E002.eb.bytes` -- `[[scene.ai_patch]]`'s output among them); (b) no
  BattlePatch.txt selector that reaches 338 (DataPatchers.cs:747-783): `Battle:` naming 338, `BSC_TH_E002` or
  `TH_E002`, and `AnyEnemyByName:`/`AnyAttackByName:` naming one of 338's enemy or attack names (its US battle text,
  `battle.extract._read_battle_text(338)["us"]` split with `dialogue.parse_mes`: a name selector applies to every
  scene holding the name among ALL its strings, then matches the first `TypCount` as enemies and the next as attacks,
  :770-771/:779-780 -- today King Leo, Zenero, Benero and their attacks); a name selector naming anything else passes,
  listed; (c) (the review, 11.7 #4) no DictionaryPatch.txt `BattleScene` line, read as `PatchDictionaries` reads it
  (:255, :565-575), whose id is 338 -- `SceneData["BSC_" + name] = 338` overwrites the reverse entry the battle's
  scene is looked up by (HonoluluBattleMain.cs:198), rebinding battle 338 to another scene, script and background with
  no file under TH_E002's name and no selector -- or whose name is `TH_E002` (`BSC_TH_E002`'s forward entry
  repointed: 338's sequence, text and background follow it); every other BattleScene line passes, listed. Today PASS:
  the stack's battle-scene overrides are FF9CustomMap's `EVT_BATTLE_LEDGER{1S,1W,_A,_B}` only, its BattlePatch
  selectors are `Battle:` 67 (x2), 336, 337, 334, 335 (FF9CustomMap) and 67 (FF9CustomMap-msgs), no name selector
  anywhere -- 0.2 #17 -- and its BattleScene lines are FF9CustomMap's 30871/30872/30881/30882 (the LEDGER scenes). A
  FAIL means battle 338 differs from stock on BOTH sides, which NULL cannot see: O3's S side would no longer be the
  stock truth.
- **In game only** (`capabilities`): P-CAP, P-OBJECTS, P-LANG (O2's), and:
  - **P-DONOR-LOG (new)**: this launch's Memoria.log (`g._log_paths()`, rewritten at launch) holds "[DataPatchers]
    Initialized" and NO line "[DataPatchers] ForkDonorPatch: donor field <61|62|63> is forked by both" -- the engine's
    donor map is fixed at launch (DataPatchers.cs:107-134, once per launch), so a duplicate present then and removed
    since would read clean in the files and still disable the redirect. Calibrated on today's log (0.2 #7). It cannot
    see a row that was MISSING at launch: P-LAUNCH can.
  - **P-LAUNCH (new; claim integrity #1)**: the launch read the files the preflight read. `launch_time(Memoria.log)` is
    the first line's stamp (`dd.MM.yyyy HH:mm:ss`, local time; today 30.09.2026 19:27:42); every stacked folder's
    DictionaryPatch.txt, BattlePatch.txt, TextPatch.txt and ForkDonorPatch.txt (the four files
    `DataPatchers.Initialize` reads, :114-126) and Memoria.ini must have an mtime, truncated to the second, EARLIER than
    that stamp; a same-second or later mtime FAILS "relaunch: <file> changed at <mtime>, after this launch began at
    <stamp>", and so does an unreadable stamp. A file deleted since the launch cannot be dated: its rows are gone from
    P-DONOR's read too, and a duplicate it held was logged at launch (P-DONOR-LOG). Today: FF9CustomMap's
    ForkDonorPatch.txt and DictionaryPatch.txt 19:27:04, its BattlePatch.txt 2026-09-29 21:06:41, the -world, -schema
    and -msgs files August (MoguriMain and MoguriVideo hold none; no folder has a TextPatch.txt), Memoria.ini
    2026-09-24 -- all before 19:27:42: PASS. With P-DEPLOY and P-DONOR (the files hold the rows) it proves
    `ForkSiblingMap[63]` is 31213 in THIS launch, which no file read alone can.

### 6.3 The fingerprint (per run, before and after, as O1's)
The base's (members' registrations, ForkDonorPatch rows, `.eb` and walkmesh shas, stock overrides) + O2's
(`override70`, `text2`, `lang`) + **`settings`** (`ini_settings` over 4.13's keys) + **`battle_patch`** (each stacked
folder's BattlePatch.txt sha, None when absent) + **`battle_overrides`** (each folder's sorted battle-scene override
names: its `EVT_BATTLE_*` scene directories and battle `.eb` files) + **`battle_scenes`** (each folder's DictionaryPatch
`BattleScene` lines, `[id, name]`: the review, 11.7 #4). Another session re-wiring New Game, touching
block 2, a language change, a settings change, or a BattlePatch or battle-scene deploy mid-session makes runs VOID
(A-INSTALL), never skews them. (A deploy changes the files, not this launch -- P-LAUNCH is checked once, at the
start; a mid-session file change is A-INSTALL whatever the launch read.)

### 6.4 `o3_forks.json` (the implementer writes it; nothing to flip: the chain is live)
```json
{"what": "O3's fork chain: O1's tshp chain as deployed (31200-31219, FF9CustomMap). O3 runs members 31211 (61), 31212 (62), 31213 (63); member(63)'s Field(64) is real 64, the seam and the segment's end on both sides. Nothing is imported, built or deployed for O3.",
 "reuses": "studies/story-trace/o1_forks.json",
 "import": "O1's (o1_forks.json import)", "build": "O1's: C:/gd/_ns_playtest/o1/build",
 "deploy": "O1's, 2026-09-29 21:07 local", "mod_folder": "FF9CustomMap",
 "members": "<O1's twenty>", "names": "<O1's twenty>",
 "route_members": {"31211": 61, "31212": 62, "31213": 63},
 "text_block": 2, "deployed": true, "relaunch_needed": false,
 "relaunch_why": "nothing is deployed for O3. The files hold the chain's FieldScene ids and one ForkDonorPatch row per route donor (P-DEPLOY, P-DONOR); P-LAUNCH proves every stacked patch file and Memoria.ini is older than the launch, so the launch read exactly those rows; P-DONOR-LOG that it logged no donor collision for 61-63. Any P-LAUNCH FAIL means relaunch first",
 "known_defects": [
   "uk/field/2.mes is stock us (3a6f3246c2; stock uk 7ac9f17435): O1's build predates the per-language text pick (aa627d52). Block 2 is a global block: a UK game shows US text in stock 61-69 too. Not redeployed for O3 (the session runs US: P-LANG); O4's alxc members 64/68/69 also carry block 2, so their deploy rewrites it",
   "every member's jp/fr/gr/it/es .eb is US bytecode (the kit before 3d8b7f1b): O3-BUILD accepts the us build, and the claim is a US session's (said in O3-BUILD's title, the report's scope, and the PLAN.md / CLAUDE.md milestone lines)"],
 "revert": "O1's (o1_forks.json revert: 31219 down to 31200, newest first)",
 "verified": null}
```

---

## 7. Rehearsal plan (the lead runs these in game before freezing; nothing is deployed)

### 7.1 The stages (`o3_rehearse.py`: `run(g, field=None)`; `O3_STAGE=<name>` picks one by name, `--field N` the one non-by-name stage warping into N)
Each traced stage: New Game; `wait_frames(30)`; `storytrace(True)`; the raw warp; `segment_drive.drive(g,
stage_pred, "S", log, end_fields=[stage end], observe=recorder, forbid_live=True)`; the trace to
`rh_<stage>_<n>.jsonl`; the record into `o3_rehearsal.json`; `end_run`. Only R-FULL's traces may define or change the
writes, the chain, the noise, the start or the end state; the staged runs prove mechanics, compared within their stage.

| Stage | Warp | Ends in | Runs | What it settles |
|---|---|---|---|---|
| **R-START** (runs first: the go/no-go) | `warp 61 0 1155` | 62 | 2 | F1, F7: FMV003 plays after the warp has cut FMV001 (type 0 into type 0, never measured); no skip dialog; arrival -> page 72 (frames, seconds); the start rows (residue, 61 ip22, ip119 old 1: the first measurement of the incoming Byte[13] IN 61). It does NOT read the "InitMovieHitPoint ... has not been deactivated" warning as a signal (0.2 #20). |
| **F-SMOKE** (by name; NO trace) | `warp 31211 0 1155`, `warp 31212 0 1155`, `warp 31213 0 1155`, and their stock twins `warp 61/62/63 0 1155` | -- | 6 warps, one each | F5: each member loads at entrance 0 SC 1155 (field id, FieldHUD) and its Main_Init runs -- its published object sids after `smoke_s` (8 s) equal its stock twin's (InitObject's entries: 61 {2, 7, 8, 14, 16}, 62 {12 x4, 20, 18, 19, 8, 9, 10}, 63 {11-13, 21, 19, 20, 6, 8, 9}, the player aside -- the twins give the measured sets); 0 exceptions through EventEngine/EBin/HarnessAgent; `end_run` (from mid-movie, mid-play, mid-scene). Each warp is `start_run`'s RAW one -- New Game, `wait_frames(30)`, `_check_field_id`, `send("warp <id> 0 1155")`, then `wait_for(field_id == id and ui_state == "FieldHUD", 60)` -- NEVER `Session.warp()`, whose `wait_playable` waits for control that 61-63 never grant (60 s, then a raise, each warp). It never fights: the 338 landing is the session's claim. No trace, so no fork data exists before the freeze. |
| **R-62** | `warp 62 0 1155` | 64 | 2 | F2, F8: the battle beat (the registry match on the published scene, turns, seconds, the result `fight()` returned, tutorials 0, the leave presses, the flip and its result, the landing in 63 and its latency, `land_late`), the cmd-37 landing on STOCK under the trace (63 e0 t0 ip22 the first field row after 62 ip1285), 63's pages, `end_run` from 64. |
| **R-FULL** | `warp 61 0 1155` | 64 | 2 | Everything in sequence; the only stage whose traces define predictions (F6, F7, F11); the total time (F9). |
| **R-SKIP** (optional, by name) | `warp 61 0 1155`; a wrapper round the recorder's `observe` hook presses Confirm once, 10 s after the run's first poll in 61, and records the frame | 62 | 1 | F4: the skip dialog's published choice (prompt, options, active, selected at readiness); the rule answers it; FMV003 continues. |
| **R-BATTLE-VOID** (LAST in a launch, or its own) | `warp 62 0 1155`, the battle row's `max_turns` 0 (`timeout_s` as drafted) | V15 | 1 | F3: `fight()` raises `FightTimeout` at the FIRST command prompt, before any attack -- so King Leo's latch cannot fire and the run stops mid-fight in BattleHUD by construction (a short `timeout_s` raced the latch: 0.2 #18); `end_run` then takes S3's soft reset from BattleHUD and reaches the title, with its seconds. A failure ends the launch (the next run would start from an unknown state). |

Default order without `O3_STAGE`/`--field`: R-START, F-SMOKE, R-62, R-FULL, R-BATTLE-VOID (R-SKIP only by name).
Estimates a run: R-START ~150 s, F-SMOKE ~150 s in all, R-62 ~240 s, R-FULL ~360 s, R-BATTLE-VOID ~90 s, R-SKIP
~150 s.

`o3_rehearse.py` reuses `o2_rehearse.Recorder` (a stage with `"movie": {"donor": 61}` records arrival, first page and
fps; `tracks` empty) and `stage_pred` (plus O3's `battle_override`, which `battle_of` validates like any row: `max_turns`
0 is legal); it has its own `STAGES`, `select` (keyed on `O3_STAGE`), `one` (O3's `trace_summary`, the battle rows,
`end_run`'s recovery rows), `smoke` (the raw warp and the FieldHUD wait above; no `storytrace` verb is ever sent;
both asserted in its test) and `run`. The command: `py tools/play.py studies/story-trace/o3_rehearse.py --label o3-rh
--timeout 240`.

### 7.2 What every stage records
O2's record (grants -- there must be none --, pages with `timed`, published choices, the `press` evidence, the longest
no-progress stretch and where, the end state, `end_run`'s result) plus:
- **the battle rows** of the driver log (2.3 step 6), whole, with `battle_epoch0`; and the run's own `g.last_fight`
  and `g.last_leave`, cleared before each run (the Session clears them only at a suite member's start, so a run that
  never fights would record the previous run's: the review, 11.7 #7);
- **`end_run`'s recovery rows** (`recover-in-battle` with its ui and result, `recover-reset` / `recover-reset-failed`,
  `recover-battle-ending` ..., `recover-warp`), and how the title came back;
- **the movie** (61): arrival frame, first page frame, fps before/during/after;
- **the trace**, through O3's `trace_summary`: the start rows (residue before, other rows before), the chain rows with
  their keys, the rows over SC's bytes (must be none), each registered key present or absent, every UNREGISTERED key
  (the battle noise aside), the battle-mode rows (count -- 0 allowed --, sites, flds, the c row), the first field row
  after 62 ip1285, the end cut's row, the error-path and `dead` rows (must be none), the residue after the start, the
  masked counts, the join failures (0);
- **the settings** fingerprint, the P-LAUNCH, P-DONOR-LOG and P-STOCK-BATTLE readings of the launch;
- **F-SMOKE:** per warp, the field id and UI reached and when, the published object sids and `objects_status`, the
  exceptions and the new Memoria.log warnings/errors after the warp, `end_run`'s result.

`py studies/story-trace/o3_prima_vista.py --rehearsal-report <run dir>` prints all of it, stage by stage, run by run.

### 7.3 The freeze checklist (each item needs its evidence; the run dirs go into `rehearsals`)
- **F1.** In every R-START and R-FULL run FMV003 plays to its end after the warp and page 72 opens; no skip dialog
  opens. The arrival -> page 72 time is recorded. If FMV003 does not play or the run stalls, STOP: the start must be
  redesigned before anything else (10, risk 1).
- **F2.** In every R-62 and R-FULL run: the registry matched on the PUBLISHED `battle.scene` 338 (if the agent
  publishes another number, STOP and correct the row, re-checked by O3-SCENE); the battle's epoch `battle_epoch0` + 1;
  result in {1, 2} (which one `fight()` returned is recorded: 2 expected, 0.2 #8); tutorials 0; the leave presses all
  inside the battle scene; the flip frame seen inside the battle on a result-1 sample (or not caught), and no sample
  with field 63 and result 2; the landing in 63 (its latency; `land_late` if past `land_s`) with 63 e0 t0 ip22 the
  first field row after 62 ip1285 and no 62 row after ip1285; the battle rows only e1 t1 ip267 Byte[206] at fld 62,
  all between those two rows, their count recorded (0 allowed).
- **F3.** R-BATTLE-VOID: the run is V15 with `last_fight["turns"]` 0 and no `battlecmd` sent; its `end_run` log holds
  a `recover-in-battle` row with ui `BattleHUD` and result 0, followed by `recover-reset`, with NO
  `recover-reset-failed`; and the title is reached. A run that reached the title by any other row sequence does not
  pass F3 (it never exercised S3). If F3 fails, STOP: recovery from a battle is redesigned (e.g. let `end_run` fight
  the battle out first) before any session.
- **F4.** (if run) R-SKIP: the rule matches the published dialog with `selected` 1 (No) at readiness; if the prompt
  published empty, a second rule matching the measured option line is added.
- **F5.** F-SMOKE: every member loads, its object sids equal its twin's, 0 exceptions, `end_run` ok. If a member does
  not load, STOP: that is a chain defect, not a finding the session should discover.
- **F6.** The R-FULL traces define the predictions: per run, keys == the 27 drafted (24 writes + 3 chain) plus the
  Byte[206] noise; no row over SC's bytes; residue exactly the start's two rows and none after; no error-path or `dead`
  row; the two runs key for key identical outside Byte[206]; any difference explained at the byte level before the
  freeze (a new key only with that explanation, and a new site only with O3-CENSUS's list updated to hold it).
- **F7.** R-FULL/R-START: the rows before the start are exactly `[[0, 0, 131], [1, 0, 4]]`; the first `w` row is 61 e0
  t0 ip22; 61's first Byte[13] row is ip119 with old 1 (`start_music.old`) -- the first time the incoming Byte[13] is
  measured in 61 (O2 measured it in 100: 4.6); the end cut is 64 e0 t0 ip22 (LANDING (e)).
- **F8.** `end_run` from 64 reaches the title (R-62, R-FULL).
- **F9.** Budgets: `run_s` = 2x the slowest R-FULL; `run_min_s` = 1.25x the median; `session_s` = 8x the median +
  1800; `no_progress_s` = max(120, 3x the longest no-progress stretch seen in any traced stage, FMV003 included);
  `timeout_s` = max(120, 3x the slowest battle's seconds); `max_turns` = max(30, 3x the most turns); `land_s` =
  max(10, 3x the slowest battle-end -> FieldHUD) (the late mark); `land_cap_s` = max(120, 10x that slowest) (the
  VOID); `Segment.battle_end_wait_s` (S3) stays >= `land_cap_s`. Only stock landings are timed before the session, so
  the F side's are read from the session's own `land_late` rows, never assumed.
- **F10.** P-LAUNCH, P-DONOR-LOG and P-STOCK-BATTLE pass on the rehearsal launch.
- **F11.** Every R-FULL `end_state` read equals 4.9's.
- **F12.** The rehearsal launch's fingerprinted `settings` equal 4.13's.

Then `--freeze` (v1), `--preflight` green (nothing to deploy, no relaunch), and the session:
`py tools/play.py studies/story-trace/o3_prima_vista.py --label story-o3 --timeout 240`.

---

## 8. The dry run (`o3_dryrun.py`: synthetic sessions through `O3.analyse`)

Built like `o2_dryrun.py`, with its own `render` (the start values are O3's: SC 1155, Int16[2] 0, Byte[13] 1; every
other target 0) and O2's event helpers (`w`, `r`, `e`, `drop`, `after`, `before`, `edit`, `upto`).
- **Real store sites** (every field row joins): 4.3-4.6's, the error-path, forbidden and ten `dead` sites (62 e4 t1
  ip1023's `Byte[4]:=1` and 61 e0 t0 ip130's `Byte[13]:=1` among them), 63 e14 t1 ip805, 64 e0 t0 ip22 (the end row).
- **The battle's rows**: m 2 at fld 62 (S) / 31212 (F), don 62, sid 1 tag 1 ip 267, Byte[206], 70 random values a run
  (seeded) -- so each run emits 64 and counts the rest into a `c` row, as the engine does -- all between 62's ip1285
  and 63's ip22 in `f`.
- **A base run**: `arm` (fld 70); residue rows (fld 70) byte 0 0 -> 131, byte 1 0 -> 4; 61's rows (start_first, Bit[184],
  the ambient four, ip752, ip363); 62's (the ambient six, ip319, the Byte[303] five, ip1034, ip1085, ip1093, ip1101,
  ip1285); the battle rows; 63's (the ambient six, ip805, ip820); 64's ip22; `off` (fld 64). On F, fields are shifted
  onto members (61 -> 31211, 62 -> 31212, 63 -> 31213); 64 stays 64.
- **A log**: the visit rows, the battle row (2.3 step 6: row 0, scene 338, donor 62, beat "leo", `epoch` = `battle_epoch0`
  + 1, `result` 2, `flip_result` 1, `frame0` between 62's ip1285 and 63's ip22, `landed` 63 / 31213, `landed_place`
  63, `land_late` None), `battle_epoch0`, `end_state` (4.9), the beats `{"leo": 2}`; a VOID drive's class and cell.

O3's `case()` is EXACT, which O2's is not (O2's compares only the checks a case names, o2_dryrun.py:936): every check
a case does not name must read PASS -- except that a case naming COVER V expects every core check VOID ("too few
covered runs") -- so each NOT PROVEN row below names EVERY check it fails, "alone" is a registered fact, and an
unforeseen co-failure is a miss to explain at the byte level, never a silent pass. A LANDING or BATTLE case also
registers the clause its detail must name.

| Case | Want |
|---|---|
| null-pair | PROVEN |
| fork-drops-a-write (no 62 ip1101 on F) | NOT PROVEN (WRITES F, NULL F, STATE F) |
| sc-write-fork (a `cs` UInt16[0]:=1190 row in 62 before ip1285, F) | NOT PROVEN (NO-SC F, WRITES F, NULL F, STATE F) |
| sc-write-both (the same on both sides) | NOT PROVEN (NO-SC F, WRITES F; NULL P) |
| sc-harness-poke-both (every run: a `src: harness` `Byte[0]` row in 61 after its ip752) | NOT PROVEN (NO-SC F alone: WRITES, NULL, STATE, RESIDUE P) |
| chain-dropped-fork (no 62 ip1285 on F) | NOT PROVEN (CHAIN F, LANDING F (c): no `before` row, WRITES F, NULL F, STATE F) |
| battle-returned-to-62 (both sides: 62 e4 t1 ip1345 after the battle rows, after `frame0`) | NOT PROVEN (CHAIN F, LANDING F (c), BATTLE F (d), WRITES F; NULL P) |
| chain-first-old-wrong (61 ip363's old 102) | NOT PROVEN (CHAIN F alone) |
| byte206-more-rows-fork (F 100 battle rows, S 70) | PROVEN |
| battle-zero-rows (both sides: no battle-mode row at all, 0.2 #1) | PROVEN; the report's battle row count 0 |
| battle-zero-rows-62-resumed (both sides: no battle-mode row, and 62 e4 t1 ip1345 after `frame0`) | NOT PROVEN (CHAIN F, LANDING F (c), BATTLE F (d), WRITES F; NULL P) |
| byte199-fork (one F run: an m 2 Byte[199] row) | NOT PROVEN (NULL F, STABLE F, LANDING F (b), WRITES F, STATE F) |
| byte199-both (every run: the same row, the same value) | NOT PROVEN (LANDING F (b), WRITES F; NULL P, STABLE P, STATE P) |
| other-battle-noise-both (every run: an m 2 Byte[206] row at e0 t1 ip93, TH_E001's site) | NOT PROVEN (LANDING F (b) alone; NULL P) |
| byte206-field-mode-fork (F: an m 1 addition-buffer Byte[206] row at 62 e4 before ip1285, `add` 1) | NOT PROVEN (NULL F, WRITES F, STATE F) |
| lands-real-63-covered (every F run: 63's rows at fld 63, the drive reached) | NOT PROVEN (LANDING F (a), (c), SEAM F, FORBIDDEN F, WRITES F; NULL P: a seam leak is invisible to it, O2's seam-leak lesson) |
| v16-all-F (every F run VOID V16 game at [62, 1155]; its rows reach real 63's prologue) | NOT PROVEN (FORBIDDEN F, VOID-ASYM F; COVER V) |
| v16-one-F (one F run so) | NOT PROVEN (FORBIDDEN F, VOID-ASYM F; COVER P) |
| battle-rows-real-62-fork (every F run's battle rows at fld 62) | NOT PROVEN (LANDING F (b), SEAM F, FORBIDDEN F) |
| fresh-missing (both sides: 63's e0 t0 rows dropped) | NOT PROVEN (LANDING F (c), WRITES F) |
| 63-main-init-late-both (every run: 63's e0 t0 rows after its e14 t1 ip805 row) | NOT PROVEN (LANDING F (c) alone) |
| last-place-wrong (both sides: 61 e0 t0 ip130 `Byte[13]:=1`, a `dead` site, after 63's ip820) | NOT PROVEN (LANDING F (d), WRITES F) |
| last-place-61-repeat-both (every run: a second 61 e0 t0 ip119 `Byte[13]:=0` row after 63's ip820) | NOT PROVEN (LANDING F (d) alone) |
| end-boundary-residue-both (every run: an `r` row in place 64 just before its ip22) | NOT PROVEN (LANDING F (e) alone: the cut lands on the `r` row) |
| end-row-missing-one-S (one S run: its `off` row in 64, no `w` or `r` row there -- story-o1e run 3 S's race; the review, 11.7 #3) | PROVEN (S 2 of 3); that run A-NOEND, never LANDING (e) |
| battle-scene-336 (every run's log: the battle row's scene 336; the trace's battle rows e1 t1 ip267 only) | NOT PROVEN (BATTLE F alone) |
| battle-two-rows (every run's log: two `battle` rows) | NOT PROVEN (BATTLE F alone) |
| battle-epoch-skip (every F run's log: `epoch` = `battle_epoch0` + 2) | NOT PROVEN (BATTLE F alone) |
| battle-frame0-late (every run's log: `frame0` after 63's ip22 row) | NOT PROVEN (BATTLE F alone) |
| battle-landed-real-63-log-F (every F run's log: `landed` 63, real; the trace stays in 31213; the review, 11.7 #5) | NOT PROVEN (BATTLE F (c) alone) |
| battle-landed-member-log-S (every S run's log: `landed` 31213; 11.7 #5) | NOT PROVEN (BATTLE F (c) alone) |
| battle-beat-true-one-S (one S run's beats `{"leo": True}`) | PROVEN (S 2 of 3); that run A-BEATS ("leo result True") |
| land-late-fork (every F run's battle row: `land_late` {frames 2400, s 80}) | PROVEN; the report lists each `land_late` |
| v15-one-S (one S run VOID V15 driver, its rows up to the battle) | PROVEN (S 2 of 3; VOID-ASYM P) |
| v15-all-F (every F run VOID V15 driver) | NOT PROVEN (VOID-ASYM F (b); COVER V) |
| unregistered-battle-F (one F run VOID V10 game at [62, 1155]) | NOT PROVEN (VOID-ASYM F) |
| control-S (one S run VOID V4 game at [63, 1155]) | NOT PROVEN (VOID-ASYM F) |
| error-path-start-S (one S run: 61 ip97 in place of ip119, the run stopped at the window; VOID V5 driver [61, 1155]) | PROVEN (S 2 of 3); the run's classes include V5 and A-START |
| error-path-start-covered-S (61 ip97 and ip349 in place of ip119, then the whole route; the drive reached) | PROVEN (S 2 of 3); the run VOID by A-START |
| error-path-63-F (one F run: 63 ip97 in place of ip119, the run stopped at the window; VOID V5 game [63, 1155]) | NOT PROVEN (VOID-ASYM F) |
| start-residue-wrong (S: byte 0 0 -> 132) | NOT PROVEN (START F) |
| start-first-missing (both: 61 ip22 dropped) | NOT PROVEN (START F; NULL P: masked) |
| start-music-old-wrong (both: the incoming Byte[13] 3, so 61 ip119's old is 3) | NOT PROVEN (START F) |
| front-cut-write (F: a `w` row in fld 70 before the start) | NOT PROVEN (START F) |
| residue-after-start (F: an `r` row on byte 300 after the start) | NOT PROVEN (RESIDUE F) |
| writes-extra-symmetric (both: 62 ip1023 `Byte[4]:=1` before ip1034) | NOT PROVEN (WRITES F; NULL P) |
| end-cut (S: rows in 64 past the end) | PROVEN |
| end-state-differs (one covered F run: Byte[303] 3) | NOT PROVEN (STATE F) |
| battle-result-1 (every run `leo` 1) | PROVEN |
| battle-result-3-one-S (one S run `leo` 3) | PROVEN (S 2 of 3); that run A-BEATS |
| beat-missing (`leo` None in two S runs) | VOID (COVER V; VOID-ASYM P) |
| masked-differs (every F run without its Bit[184] rows) | NOT PROVEN (MASKED F) |
| mismatched (one F run's member rows name another donor) | PROVEN; that run A-MISMATCH |
| no-start-row (one S run never reaches 61) | PROVEN; that run A-NOSTART |
| join-failure (both: an EXTRA row at 62 e4 t1 ip1102, one byte off ip1101's store, joining none; ip1101's own row kept) | NOT PROVEN (JOIN F alone) |
| trace-without-off | VOID |
| install-changed | VOID |
| predictions-changed | NOT PROVEN (FROZEN F) |

Units (no session):
- **no-sc-span:** a `Global.Byte[1]` row is selected by NO-SC's span and fails by name; a Byte[4] row is not selected.
- **trace-summary:** O3's `trace_summary` of a base S run: chain 3/3, writes 24/24, no SC row, the battle's rows (64
  emitted, the rest in one count row; the count reported), the first field row after 62 ip1285 63 e0 t0 ip22, the end
  cut's row 64 e0 t0 ip22, no unregistered key, no error-path or `dead` row, no join failure, the two start residue
  rows; and of a battle-zero-rows run: the count 0, the rest the same.
- **state-history:** Byte[8]'s history is `[(61, 125), (63, 125)]`; the battle noise is in neither history nor
  suppressed set.
- **p-donor-log:** synthetic logs -- "Initialized" plus today's real 351 warning: PASS; plus "donor field 63 is forked by
  both 31213 and 31299": FAIL naming 63; no "Initialized": FAIL.
- **p-launch** (claim integrity #1's cases; P-LAUNCH reads the mtimes, so they are its units): synthetic folders and
  a synthetic Memoria.log whose first line is "30.09.2026 19:27:42 |M| ...": every patch file and Memoria.ini older:
  PASS; a ForkDonorPatch.txt that HOLDS `31213 63` (so P-DONOR passes it) but was touched at 19:27:50: FAIL
  "relaunch" naming it; a same-second mtime (19:27:42.4): FAIL; Memoria.ini touched after: FAIL; a TextPatch.txt
  after: FAIL; a first line with no stamp: FAIL; a folder with no patch file: PASS (nothing to date).
- **p-stock-battle:** synthetic stacked folders -- today's live shape (the four LEDGER overrides; `Battle:` 67, 336,
  337, 334, 335): PASS; plus `BattleMap/BattleScene/EVT_BATTLE_TH_E002/dbfile0000.raw16.bytes`: FAIL; plus
  `EventBinary/Battle/fr/EVT_BATTLE_TH_E002.eb.bytes`: FAIL; plus `Battle: 338`, or `Battle: BSC_TH_E002`: FAIL; plus
  `AnyEnemyByName: King Leo`: FAIL; plus `AnyEnemyByName: Goblin`: PASS, listed; (the review, 11.7 #4) today's four
  LEDGER `BattleScene` lines PASS, listed; plus `BattleScene 338 LEDGER_A BBG_B251` or `BattleScene 30999 TH_E002
  BBG_B065`: FAIL (c); plus `FieldScene 338 11 X X 2`: PASS (the battle never reads EventDB[338]).
- **p-settings:** a synthetic ini equal to 4.13: PASS; `Speed = 0`: FAIL naming it; a later duplicate assignment wins.
- **scene-census:** O3-SCENE on the install: PASS; mutants each FAIL by their clause: `lands` 64, `won` [1] (WinPose
  off allows exactly [1, 2]), `won` [1, 2, 3] (a defeat counted as covered), `landing.battle.ip` 268, the noise
  target `Global.Byte[199]`, an `lvalue_class` that classifies nothing (24 unresolved stores, each FAILED by name).
- **store-census:** O3-CENSUS on the install: PASS, "15 / 28 / 15 store sites, all classified, 0 unresolved"; mutants
  each FAIL naming the site: `dead` without 61 ip130; `error_path` without 62 e0 t10 ip580; `forbidden_sites` empty
  (62 ip1345 unclassified); an injected unresolved store with an unknown lvalue token.
- **battle-row:** `segment_drive.battle_of` on 2.1's row: passes; raises on `won` [1, 2, 3], [2] and []; on a `beat`
  not in `beats`; on a `beat` a naming rule (or a step, or a choice rule) also names; on `max_turns` -1 and on
  `max_turns` True; on `land_s` above `land_cap_s`; `max_turns` 0 passes (R-BATTLE-VOID's row).
- **build-legacy:** `Segment.build_check` on a synthetic two-member build with an injected `stock_lang` (its
  `stock_lang=` seam) and `accept_us_build`: a member whose jp `.eb` is the us build reads PASS, counted "us-build"; one
  whose jp is neither its own donor language remapped nor the us build FAILs by name; the same build without
  `accept_us_build` FAILs the us-build copy -- O3-BUILD's legacy acceptance is the opt-in, never a blanket pass.
- **offline mutants** (O2's `OFFLINE_MUTANTS` pattern, each FAIL by its clause after all read PASS on the draft): KEYS --
  a write's value (UInt16[21] 3586), a `++` prior unknown, an error-path ip + 1, a chain `off` + 1, `start_first`'s
  target, a `dead` site's value (61 ip130 `Byte[13]` 2); REGIONS -- a frozen hot-spot 62 e9 that the bytes lack;
  P-DONOR -- synthetic folders with a second row `31299 63` (FAIL), and with none for 61 (FAIL).

It prints O2's summary columns plus BATTLE (FROZEN COVER FORBIDDEN VOID-ASYM START NO-SC CHAIN RESIDUE WRITES NULL
STABLE SEAM LANDING BATTLE MASKED STATE JOIN) and "N/N cases as registered", exiting 1 on any miss.

---

## 9. Build order (three parts; no deploy, no game, no `tools/play.py`, no full suite)

Run pytest from `ff9mapkit/`, the study scripts from the worktree root. The harness tests run in REAL TIME (the
FakeGame loops on a thread): run the named `-k` selections, never many at once, and the whole file only where a
PART says so. A SKIPPED test is not a pass: every required pytest run reports 0 failed, and its skips and xfails are
exactly the PART's baseline's (taken before the PART's first change); a skip for missing templates is fixed with `py
-m ff9mapkit extract-templates` (read-only on the install) and the run repeated. A failure that passes on an
immediate re-run of that test alone is a timing flake: named in the commit message, never ignored. Commit on the
branch when a step is green, one step per commit, each message ending with
"Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". Write non-ASCII files with Python (utf-8) or the
Edit/Write tools; frozen JSON and baselines are LF (`-text`).

### PART A -- the regression gate extended to O2 (baseline FIRST), then the shared session changes
1. **A0: the O2 gate and its baseline, FIRST.** Extend `segment_regress.py` (1.4: G8-G12, `REQUIRED_TESTS_O2` empty
   for now; the module docstring says G10 is the only VOID-path baseline), run `py
   studies/story-trace/segment_regress.py --capture-o2`, and commit it with `research/o2_regress_baseline.json` and its
   `.gitattributes` line before any other code change. Then `py studies/story-trace/segment_regress.py` reads G1-G12.
2. **A1: S1** (`read_session`'s registered-battle won set, an int result only) +
   `test_segment_read_session_judges_a_registered_battle_by_its_won` (its five runs, `{"leo": True}` among them).
3. **A2: S2** (`rerun.stop_on`) + `test_segment_rerun_stops_on_a_finding_class` (`_stub_segment` gains `rerun=`).
4. **A3: S3** (`end_run` from inside a battle: the soft reset from BattleHUD mid-fight only, the end sequence waited
   out, `battle_end_wait_s`) + `test_segment_end_run_resets_from_inside_a_battle_without_a_warp` (its three stubs).
5. **A4: S5** (`end_session_warps`, `session["ended"]`) + `test_segment_session_end_warps_first_when_asked`.
   Each A1-A4 test joins `REQUIRED_TESTS` as it lands.

**PART A REQUIRED-GREEN** (after A0, and again after each of A1-A4):

| Command | Expected |
|---|---|
| `py studies/story-trace/segment_regress.py` | exit 0; G1-G7 and G8-G12 each PASS |
| `py studies/story-trace/o1_dryrun.py` | exit 0; "16/16 cases as registered" |
| `py studies/story-trace/o2_dryrun.py --predictions studies/story-trace/o2_predictions_v1.json` | exit 0; "86/86 cases as registered" |
| `py studies/story-trace/o1_opening.py --analyse C:\gd\Dream-World-IX\.harness-runs\20260929-213149-story-o1e --predictions studies/story-trace/o1_predictions_v4.json` | exit 0; `VERDICT: PROVEN` |
| `py studies/story-trace/o2_alexandria.py --analyse C:\gd\Dream-World-IX\.harness-runs\20260930-192740-story-o2 --predictions studies/story-trace/o2_predictions_v1.json` | exit 0; `VERDICT: PROVEN`; the archived report |
| `py studies/story-trace/o1_opening.py --offline-check` | exit 0; O1-BUILD (140 files; 15 own-language, 105 us-build), O1-KEYS (4 keys) |
| `py studies/story-trace/o2_alexandria.py --offline-check` | exit 0; 5 PASS as 0.2 #12 |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "segment or pick_for or key_matches or is_noise or cut_at or row_keys"` | all passed, 0 failed, 0 skipped |

### PART B -- the harness additions and the battle beat in `segment_drive`
1. **B0:** the PART's baseline of the whole `tests/test_harness.py` (passed / xfailed / skipped), taken before B1 from
   this worktree with the field manifest present (O2's B0 note: a snapshot lacking `reference/field-manifest.tsv`
   fails 22 stock-warp tests).
2. **B1: H9** (the FakeGame knobs: `battle_script_end`, the four-phase `battle_exit`, `warp_field_only`,
   `warp_arrive_control`, `soft_reset_ui`, the movie beat) + its six fake tests (3, H9).
3. **B2: H7** (`FightTimeout`, `last_fight`, `max_turns` 0) + its two tests.
4. **B3: H8** (`leave_battle(stop_on_field=)`, `last_leave`) + its two tests.
5. **B4: S4** -- `segment_drive`: `battle_of` (strict, validated against the predictions: 2.1) and `battle_row`
   (pure), `_Drive.battle` (the two-tier landing, `flip_result`), rule 1b, rule 7's stop pages, V15/V16, `out()`'s
   `battles` and `battle_epoch0` -- with these FakeGame tests, EVERY one with `warp_arrive_control` False and
   `soft_reset_ui` the engine's set (fields 30820/30821/30810 of the fixture as "61/62/63", an unregistered end id as
   "64"; F-side members appended to the fixture's DictionaryPatch as O1's pinning test does):
   - `test_o3_drive_fights_its_registered_battle_and_lands_fresh` (S): pages, the director starts battle 338 at "62"
     (`battle_script_end` on a 10186-hp "King Leo", `battle_exit` "63"), the drive fights, leaves, lands; `fight()`
     returned 2 (read in the fade); beats `{"leo": 2}`; one `battle` row (scene, epoch = `battle_epoch0` + 1, result 2,
     turns, presses, `flip_frame` on a result-1 sample, `landed` "63", `land_late` None); visits 61, 62, 63; the end
     reached.
   - `test_o3_drive_lands_in_the_member_on_the_fork_side` (F, `battle_exit` member("63")).
   - `test_o3_drive_reads_a_landing_in_the_real_field_as_a_finding` (F, `battle_exit` real "63"): V16, by game, cell
     ["62", sc].
   - `test_o3_drive_ignores_the_id_flip_inside_the_battle` (`result_frames` long: published samples with `in_battle`,
     "63" and result 1 together; no V10, no visit, no V11 until the landing).
   - `test_o3_drive_waits_out_a_late_landing` (`load_frames` past `land_s`, under `land_cap_s`: reached, the row's
     `land_late` set, no VOID) and `test_o3_drive_voids_a_landing_past_its_cap` (past `land_cap_s`: V14, game).
   - `test_o3_drive_voids_an_unregistered_battle` (scene 337 at "62"; scene 338 at "61"; the same row twice): V10, game.
   - `test_o3_drive_voids_a_battle_with_no_result` (no scripted end, a huge hp, `timeout_s` 3: V15, driver, the battle
     row `timed_out`; `max_turns` 0: V15 at the first prompt, no `battlecmd` executed).
   - `test_o3_drive_logs_leave_battle_presses_as_press_rows`.
   - `test_o3_drive_stops_on_a_stop_page` (the error window in the start visit: V5 driver; in a later visit: V5 game;
     nothing pressed either way).
   - `test_o3_drive_answers_a_skip_dialog_at_its_default` (a movie beat, a Confirm injected by the director: the rule
     takes No; the movie resumes; the end reached).
   - `test_o3_drive_watchdog_against_a_long_movie` (a movie longer than `no_progress_s`: V14; with `no_progress_s`
     above it: reached -- the sizing rule of 4.12, on the fake).
   - `test_o3_drive_battle_of_rejects_a_bad_row` (pure: section 8's battle-row unit).
   - `test_o2_drive_voids_a_battle_without_a_registry` (O2-shaped predictions, a battle on screen: V10 with O2's
     message -- the S4 no-registry proof; named `o2_` so G12 runs it).
   In this commit: the `test_o3_drive_*` names go into `REQUIRED_TESTS_O3` and G13 joins the gate (1.4);
   `test_o2_drive_voids_a_battle_without_a_registry` goes into `REQUIRED_TESTS_O2`.
6. **B5:** `test_segment_end_run_from_a_battle_on_the_fake` (S3 on H9's knobs) and
   `test_segment_session_end_leaves_a_movie_on_the_fake` (S5 on the movie beat); both join `REQUIRED_TESTS`.

**PART B REQUIRED-GREEN.** H9, H7 and H8 change the fake and two shared verbs, so the WHOLE file runs after B3 and
once more at the end of PART B:

| When | Command | Expected |
|---|---|---|
| after B1, B2, B4, B5 | `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o1_ or o2_ or o3_ or segment or fight or leave_battle or fake_"` | all passed, 0 failed, 0 skipped |
| after B3 and after B5 | `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore` | B0's counts + the new tests passed, B0's xfails, 0 skipped, 0 failed |
| after every B step | `py studies/story-trace/segment_regress.py` | exit 0; G1-G12 each PASS, and G13 from B4 on (`REQUIRED_TESTS_O2` holding the renamed no-registry test) |

### PART C -- O3 itself
1. **C1: `o3_prima_vista.py`** (1.3, 4-6: the `dead` list, O3-LANDING (a)-(e), O3-BATTLE, O3-SCENE's exact `won` and
   lvalue classes, O3-CENSUS, P-STOCK-BATTLE, P-LAUNCH, the fingerprint's `battle_patch`/`battle_overrides`, O3-BUILD's
   "US session" title), **`o3_forks.json`** (6.4, the corrected `relaunch_why`), the `.gitattributes` line for
   `o3_predictions*.json`. Tests: `test_o3_draft_members_are_o1s_chain` (SKIPS, saying so, where O1's chain is not
   built), `test_o3_freeze_refuses_an_existing_file` (a synthetic chain: runs everywhere),
   `test_o3_p_donor_log_reads_the_launchs_warnings`, `test_o3_p_launch_fails_a_patch_file_newer_than_the_launch`
   (section 8's p-launch cases: the row is in the file and P-LAUNCH still FAILS),
   `test_o3_p_stock_battle_finds_an_override_of_338` (section 8's p-stock-battle cases),
   `test_o3_settings_read_the_ini_the_engines_way`.
2. **C2: `o3_dryrun.py`** -- every case and unit of section 8 as registered, with O3's EXACT `case()`.
3. **C3: `o3_rehearse.py`** + `--rehearsal-report`. Tests, every one with `warp_arrive_control` False and `soft_reset_ui`
   the engine's set: `test_o3_rehearse_plumbing_on_the_fake` (one traced stage with a battle on the fake: the record
   holds every 7.2 section, the battle rows and `end_run`'s recovery rows among them),
   `test_o3_rehearse_smoke_sends_no_storytrace_on_the_fake` (F-SMOKE: raw warps and a field-and-FieldHUD wait, no
   `Session.warp()`, no `storytrace` step executed, the object sids recorded, `end_run` after each warp -- it would
   hang 60 s a warp on `wait_playable` otherwise), and `test_o3_rehearse_battle_void_stops_mid_fight_on_the_fake`
   (R-BATTLE-VOID: V15 with 0 turns and no `battlecmd`, then `recover-in-battle` with ui BattleHUD, `recover-reset`, no
   `recover-reset-failed`, the title: F3's rows). All three join `REQUIRED_TESTS_O2` (G12's selection matches
   "rehearse").
4. **C4: the O3 section in `PLAN.md`** -- the question, the segment, the sides, the entry, the battle beat, the checks,
   "draft: rehearsals pending, freeze pending", the uk KNOWN-KIT-DEFECT and the legacy build as scoped facts, and "US
   session" in its heading (the CLAUDE.md milestone line that later records a PROVEN O3 says it too: 5.4).

**PART C REQUIRED-GREEN** (after each of C1-C4, as far as it exists):

| Command | Expected |
|---|---|
| `py studies/story-trace/o3_prima_vista.py --offline-check` | exit 0; "predictions: the draft"; 6 PASS -- O3-BUILD, titled a US session's build (140 files; 15 own-language, 105 us-build), O3-TEXT (KNOWN-KIT-DEFECT 1, FAIL 0, 6 byte-equal of 7, and the printed KNOWN-KIT-DEFECT uk line), O3-KEYS (53 sites (53 keys), 4 compound values computed, none masked), O3-REGIONS (0 regions, 0 hot-spots, 0 gateways), O3-SCENE (338 as 6.1: the base copy, won exactly [1, 2], 24 unresolved stores all B_SYSLIST[0]), O3-CENSUS (61: 15, 62: 28, 63: 15 store sites, all classified, 0 unresolved) |
| `py studies/story-trace/o3_prima_vista.py --preflight` | exit 0; P-MANIFEST, P-DEPLOY, P-EB, P-FLOOR, P-STOCK, P-TEXT (with the uk line), P-RECOVERY, P-DONOR, P-SETTINGS, P-STOCK-BATTLE PASS (P-DONOR-LOG and P-LAUNCH are in game: their units run in the dry run and C1's tests) |
| `py studies/story-trace/o3_prima_vista.py --draft` | exit 0; the draft JSON, `dead` and the battle row's `land_cap_s` in it |
| `py studies/story-trace/o3_dryrun.py` | exit 0; "N/N cases as registered" |
| `py studies/story-trace/segment_regress.py` | exit 0; G1-G13 each PASS (G1-G14 since the review, 11.7 #12) |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o3_ or segment or rehearse"` | all passed, 0 failed, 0 skipped |

---

## 10. Open risks (what only the game can settle)
1. **FMV003 right after the warp cut FMV001** (F1). Both are type 0 (skip hit-area armed); O2's warp landed in a type-1
   movie, O1's FMV002 came minutes after its warp. If FMV003 does not play, the start needs a redesign (a two-hop
   start through a quiet field changes `start_residue` and START), so R-START runs first.
2. **The s24 redirect under the trace** (the session's own claim). In-game proven only for the June 6013/6014 fork,
   never traced; a leak reads NOT PROVEN through V16 (VOID-ASYM) and FORBIDDEN -- LANDING (a) too only if such a run
   were ever covered: a V16 run is uncovered, and LANDING reads only covered runs -- never VOID. P-DONOR and
   P-DONOR-LOG keep a launch-time duplicate from causing it, and P-LAUNCH a row that was missing when the launch read
   the files.
3. **King Leo's latch fires once** (TH_E002 e1 t1 [601]). A miss is V15 at `timeout_s`; O1's twin latch held in every
   O1 run.
4. **The soft reset from inside a battle** (F3, S3). By the source it fires from BattleHUD on the 2nd held frame and
   never from BattleResult (0.2 #9); S3 resets only mid-fight and waits the end sequence out. If the game swallows it
   in BattleHUD too, a run stopped mid-fight cannot recover and the launch stops (F3's STOP).
5. **The published battle scene and result** (F2). `battle.scene` is `battleMapIndex` (the scene id) by the source;
   `fight()` should return 2, read in the fade (0.2 #8); 1 counts too.
6. **`leave_battle` after a scripted end with no result screen** (F2): the presses are logged and stopped at the scene
   change; a result UI that outlives the battle scene would leave the field down (V14 at `land_cap_s`).
7. **The F side's landing time** (the session): never measured before it (F-SMOKE never fights; R-62 and R-FULL are
   stock), and the fork path adds a fresh 31213 load and its autosave. The two-tier wait (2.3 step 4) records a slow
   landing as `land_late` instead of a one-sided VOID; only a hang past `land_cap_s` is V14.
8. **The watchdog against FMV003** (F9): the signature cannot see a movie; `no_progress_s` must exceed the stretch.
9. **The members' first load** (F5): never loaded in game before the smoke.
10. **Settings the agent cannot see**: the boosters (SpeedMode, Attack9999, AutoBattle) are toggled by keys, not
    published; the ini is fingerprinted, a toggle mid-session is not. They change timing, never a store -- and
    R-BATTLE-VOID's `max_turns` 0 makes it immune to them (no attack is ever made).

Closed by the source in round 2 (no longer open): **control at a field load** -- the engine zeroes `usercontrol` at
every field start, the battle-return load of 63 included (0.2 #19); the settle (1 s) stays as O1's net. **63's timed
windows under the page rule** -- `[TIME=n]` sets the button inhibit, so a Confirm cannot close one and 63's transcript
is deterministic (0.2 #19). **The soft reset while FMV003 plays** -- dead by the source (0.2 #9), so recovery never
relies on it: `end_run` warps first, and the session ends through `end_run` (S5).

---

## 11. Critique log

### 11.1 Round 1: the research critic's twelve
The critic's twelve problems (`o3_research.json` `critique.problems`), each re-checked in the bytes or the engine
source, and its disposition. Nothing was disproved; nothing was rejected outright. Round 2 later revised these
remedies, and the rows below say what round 1 decided: #1's (the landing in two tiers and the engine's end order,
11.2 #2 and #4), #3's (P-LAUNCH, LANDING's key anchors and its clause (e), 11.3 #1, #5, #6), #9's (the scene pinned by
O3-BATTLE, not the site, 11.3 #2), #12's (S3 from BattleHUD only, and S5, 11.2 #1 and #5), and #5's wording (the
hit-area warning is no signal, 11.2 #6).

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| 1 (blocker) | The driver VOIDs every battle; the id flips to 63/31213 inside the battle's end; King Leo's end fires once and a miss burns `fight()`'s 300 s / 120 turns. | segment_drive.py:1114-1116 (rule 5); HonoluluBattleMain.cs:732-741 (the fold and `fldMapNo` on one frame, `in_battle` still true); HarnessAgent.cs:1537 (raw `fldMapNo`), :1815 (`scene` = `battleMapIndex`); session.py:7407-7411, :7442-7444. | ADOPTED: the registry row `{donor 62, sc 1155, scene 338, won [1,2], lands 63}` matched on a NEW epoch, the published scene and the VISIT's place (2.3 step 1); rule 1b before the route and visit rules (2.2); the executor owns the loop through `leave_battle` to FieldHUD (2.3); `timeout_s`/`max_turns` from the row and `FightTimeout` -> V15 (H7, 2.6); FakeGame cases for an unregistered battle, a wrong scene and a real-63 landing (B4). |
| 2 (major) | Members 31211-31213 have never loaded in game. | No archive since 09-29 holds fld 31211-31213 (the research); O1's preflight is static. | ADOPTED: F-SMOKE (7.1), no trace (so no fork data exists before the freeze), Main_Init's evidence the published objects against stock twins, F5 a STOP item. |
| 3 (major) | NULL cannot see the landing; the donor map is fixed at launch. | `Comparison.stock_only` excludes seam-counted keys; DataPatchers.cs:107-127 (read once a launch), :148-160 (-1 and a warning only); today's log (0.2 #7). | ADOPTED: O3-LANDING (a)-(d) and O3-SEAM over the covered runs (5.3); VOID-ASYM reads V16; FORBIDDEN's `off_route` names the leaked rows of a VOID run (4.8); P-DONOR (files) and P-DONOR-LOG (the launch's own log: the absence of the warning for 61-63 on a log holding "Initialized" -- the engine writes no positive "mapped once" line, 0.2 #7). |
| 4 | The pages come after FMV003's end; the whole ~90 s stretch sits in the 120 s watchdog. | 61 e2 t1 ip324, ip371-ip422 (the critic's reading holds); the agent publishes no movie state (0.2 #11). | ADOPTED with one remedy of the two offered: the beat corrected (2.4); `no_progress_s` drafted 300 and sized by F9 from the measured stretch. The other remedy -- the MBG state in the signature -- needs an agent patch (an engine rebuild), outside this arc: not taken. B4 pins the sizing rule on the fake. |
| 5 | The start lands in a type-0 FMV right after cutting another; never measured. | segment_trace.py:447-454 (the warp ~30 frames after New Game, during FMV001); MBG.cs:205-208, :829. | ADOPTED: R-START first, F1 a STOP item; F-SMOKE records the F side's start too. |
| 6 | The chain is a legacy build: BUILD fails unless O3 opts in as O1 did. | O1-BUILD today: 140 files, 15 own-language, 105 us-build (0.2 #6); Memoria.log English(US). | ADOPTED: `accept_us_build = True`, P-LANG kept, the claim scoped to a US session (5.4), the defect in `o3_forks.json`. |
| 7 | Block 2 is a global override read by both sides; uk ships the US text. | `text_rule` today: 6 byte-equal, KNOWN-KIT-DEFECT 1 (uk), FAIL 0, build and live alike (0.2 #5). | ADOPTED: O3-TEXT and P-TEXT on block 2 (us exact, uk a KNOWN-KIT-DEFECT line); no redeploy before O3; the O4 note in `o3_forks.json`. |
| 8 | LADDER would be vacuous; `Byte[303]++` needs O2's key form. | 61-63: 0 stores and 0 reads of UInt16[0]; 62 e4 t1 ip637-ip703 are `B_POST_PLUS` (O2-KEYS computes them: 0.2 #3). | ADOPTED: O3-NO-SC (by byte span, `c` rows included), the CHAIN with ip1345 excluded by exactness and proven by O3-KEYS, Byte[303] keyed `:=0` then `++` x4 with chained priors (4.2-4.4). |
| 9 | Register only Byte[206]; the legacy noise would also hide another battle's Byte[206]. | TH_E002's census: one store, e1 t1 ip267 (0.2 #1); O1's Byte[199] belongs to TH_E001. | ADOPTED: noise = `[{not_m 1, Byte[206]}]` only; the registry asserts scene 338 live; O3-LANDING (b) pins every battle row to that one store, so a Byte[199] or another site's Byte[206] FAILS even when symmetric; Byte[206] out of STATE and the end state (4.7, 4.9). |
| 10 | Wording; the error-path ips must be explicit forbidden rows that VOID the start. | 61 e0 t0 ip65-ip130, ip323-ip383 (and 62/63's), win_route.txt's window 3 text. | ADOPTED: the wording fixed (0.2 #14); the 14 error-path sites registered and proven (O3-KEYS), the window a stop page (V5: driver at the start, game after; 2.2), A-START uncovers a run whose 61 took the path (5.1), START (c) pins the warp's Byte[13] (old 1), and O3-WRITES (exact) fails any error-path key in a covered run. |
| 11 | `leave_battle`'s presses are unlogged and land in the transition; the stock truth runs under non-default battle settings. | session.py:7457-7463; Memoria.ini (0.2 #13). | ADOPTED: H8 (stop where the field begins; `last_leave`), the presses as `press` rows (2.3 step 3); `settings` frozen, fingerprinted and checked (P-SETTINGS), stated in the report's scope. |
| 12 | Recovery is unmeasured from 64 and from inside battle 338. | segment_trace.py:460-480; the warp refused in a battle (0.2 #9). | ADOPTED: S3 (the soft reset first from a battle); F8 (from 64, R-62 and R-FULL) and F3 (R-BATTLE-VOID). |

The critic's GO conditions -- the battle registry, the F load smoke and the landing check before any session -- are
PART B (S4), section 7 (F-SMOKE, F5) and PART C (O3-LANDING) respectively.

### 11.2 Round 2: driver robustness (six items: no blocker, two major, four minor)
Every engine path re-read in `C:\gd\FFIX\Memoria\Assembly-CSharp\` (the live source), every study path at this
branch, every number in the archives named. All six hold; all six are adopted, one remedy re-shaped (#1's fake knob).

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| 1 (major) | F3 can pass without testing S3: R-BATTLE-VOID's `timeout_s` 15 races King Leo's latch, so `end_run` may run in the end sequence; and S3's soft reset can never fire in BattleResult. | story-o1e steps.jsonl: TH_E001's same latch, 7 hits in 16.4 s from the first `battlecmd` (t 1790731999.16 to 2015.52), the next `menus` refused "not asking" at +17.1 s. UIKeyTrigger.cs:161 (`Update` returns when the menu handler consumes a key), :688 (Select consumed on the combo's down frame), :94 (`GetKey` false outside FieldHUD/WorldHUD/BattleHUD/QuadMistBattle), :344 (the reset inside `HandleBoosterButton`); HonoluluBattleMain.cs:721-741, BattleResultUI.cs:31-35 and :374-385, TH_E002 e0 [238]-[252], EventEngine.DoEventCode.cs:2972 (BattleResult is still in the battle). The critic's PDef/Power figures were not re-read: the remedy does not depend on them. | ADOPTED: R-BATTLE-VOID's row takes `max_turns` 0 -- `FightTimeout` at the first command prompt, before any attack (7.1, H7, 0.2 #18); F3 requires `recover-in-battle` (ui BattleHUD, result 0) then `recover-reset` and no `recover-reset-failed` (7.3); S3 resets only in BattleHUD with result 0, and otherwise waits up to `battle_end_wait_s` for the field, then takes the warp ladder (1.2). RE-SHAPED: the FakeGame models the engine's states through an opt-in `soft_reset_ui` set (the engine's: FieldHUD, WorldHUD, BattleHUD, QuadMistBattle; BattleResult never in it; a playing movie swallows the combo whatever the set) rather than the on/off `soft_reset_in_battle`, and its DEFAULT stays today's FieldHUD/WorldHUD pair so no existing test's fake changes (3, H9's rule); every O3 fake test passes the engine's set. |
| 2 (major) | One slow fork-side landing turns the session NOT PROVEN: a `land_s` miss is V14 (game) at [62, 1155], VOID-ASYM (a) fails on one side's game class over every run, and `stop_on` cannot help. | o2_alexandria.py:1289-1313 (VOID-ASYM (a) and (b)); design 2.3 step 4, 2.6, F9 as they stood; EventEngine.cs:670-697 (every field load's autosave); F-SMOKE never fights and R-62/R-FULL are stock, so no fork landing is ever timed before the session. | ADOPTED: the two-tier landing (2.3 step 4): past `land_s` the row records `land_late` and the wait goes on to `land_cap_s` (draft 120) or the deadline; only no field by the cap (V14, game) or a wrong field (V11, V16) VOIDs, the deadline is V13; F9 sizes both marks; the report lists every `land_late` (5.4); dry-run land-late-fork (PROVEN); B4's late-landing and past-the-cap tests. The critic's fallback (a `land_s` VOID attributed to the driver) is not needed: no `land_s` miss VOIDs now. |
| 3 (minor) | F-SMOKE hangs if it calls `Session.warp()`, and the fake hides it. | session.py:2458-2474 (`warp` ends in `wait_playable`) and :1100-1115 (control required); EventEngine.cs:627 (`usercontrol = 0` at every field start); fakegame.py:931-946 (the fake's warp sets control True). | ADOPTED: `smoke()` is `start_run`'s raw warp plus a field-and-FieldHUD wait, never `Session.warp()` (7.1); FakeGame `warp_arrive_control` (default True), False in every O3 fake test, B4's and C3's included (H9, PART B/C); `test_fake_warp_arrives_without_control_when_told` shows `Session.warp()` timing out there. |
| 4 (minor) | H9's `battle_exit` publishes result 2 with the exit field, which the engine never does; in the game `fight()` normally returns 2 at field 62. | btl_scrp.cs:785-799 (cmd 33: 1 -> 2 with WinPose off, the fade); HonoluluBattleMain.cs:721-741 (the fold and the flip in ONE call, then `GoToBattleResult`); BattleResultUI.cs:31-35, :374-385; session.py:7390-7391 (`fight()` breaks on the first sample with a result) and :7432 (its immediate re-read). | ADOPTED: 0.2 #8 rewritten in the engine's order; H9's `battle_exit` in four phases (the fade at the battle's field with result 2; one over frame folding 2 -> 1 with the flip; BattleResult in the battle; the lagging load); `test_fake_battle_exit_runs_the_engines_four_phases` asserts `fight()` returns 2, the flip sample's result is 1, and no sample pairs the exit field with result 2; the battle row gains `flip_result`; F2 records the same in game. |
| 5 (minor) | The session-end restore does not warp first, and the soft reset is dead while any movie plays: a last run stopped in 61 mid-FMV003 loses 45 s and leaves the game in 61. | segment_trace.py:597-600 (the bare `restore_baseline()` after the last run; `end_run` runs only before runs 2..n, :547); UIKeyTrigger.cs:241, MBG.cs:607-610 (`!played \|\| isSkip`), MBG.cs:216/:316/:67 (`played` set by `Play`, cleared by `Stop`/`Seek`), fldfmv.cs:198 (the movie's shutdown purges). O1d's and O1e's restore failures fit this reading (an inference, not measured). | ADOPTED as S5, opt-in (1.2): `end_session_warps = True` (O3) ends the session through `end_run` -- warp first, S3's battle rule -- recorded in `session["ended"]`; the default keeps O1's and O2's session end byte-for-byte, so the shared change is behaviour-neutral for them (1.2's rule); they may opt in. A4's stub test and B5's movie test (the fake's movie beat swallows the bare ladder's reset, as the engine does). S3 is unaffected: a battle scene plays no movie. |
| 6 (minor) | Wording: 63's timed windows cannot be closed by a Confirm; risk 7 is ruled out by the source; the research critic's "stale hit-area warning" is no signal. | DialogBoxSymbols.cs:811-826 (`[TIME=n]`, `[TIME=-1]` set `FlagButtonInh`), Dialog.cs:789 (`OnKeyConfirm` honours it); EventEngine.cs:627 and :666 (63 loads fresh after the battle, control zeroed); HonoluluFieldMain.cs:152 -> ETb.cs:31-37; the warning 0 times in story-o1e's and story-o2's output_log.txt. | ADOPTED: 2.4 row 11 and the old risk 11 corrected (inert; 63's transcript deterministic); risk 7 closed by the source (10); 0.2 #19 and #20; R-START names the warning as no signal (7.1). |

The critic's "checked and needing no change" list (the warp cutting FMV001, the skip dialog, battle 338's turns and
tutorial, rule 1b's epoch edge, the s24 redirect's inputs, recovery from 64, presses on timed windows) stands; none of
it is edited.

### 11.3 Round 2: claim integrity (eleven items: four major, five medium, two minor)
All eleven hold on the facts; all are adopted. One remedy is re-shaped (#2's frame clause) and one sub-request is
rejected as impossible (#8's mutant failing LANDING (a) alone).

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| 1 (major) | The launch's donor map is inferred from files read after the launch: a `31213 63` row missing when the game launched makes `ForkSiblingField(63)` answer 63 -- a false NOT PROVEN against s24 -- and no check sees it. | DataPatchers.cs:102-105 (the fallback), :107-134 (`Initialize`, once: AssetManager.cs:116 is its only caller); FF9CustomMap's ForkDonorPatch.txt and DictionaryPatch.txt mtime 2026-09-30 19:27:04, Memoria.log's first line 19:27:42 (the critic's 19:27:44 is its second line's); P-DONOR-LOG sees only a logged collision. | ADOPTED: P-LAUNCH in `capabilities` (6.2): every stacked folder's DictionaryPatch, BattlePatch, TextPatch (Initialize reads it too, so it is added) and ForkDonorPatch, and Memoria.ini, older than the launch's first Memoria.log stamp, else FAIL "relaunch"; `relaunch_why` corrected (6.4). The unit cases the critic placed under P-DONOR-LOG (the row in the file, the mtime after the launch: FAIL) are P-LAUNCH's -- it is the check that reads mtimes (section 8 p-launch; C1's test). |
| 2 (major) | The analysis never re-checks which battle was fought: LANDING (b) pins the store site, which scene 336 shares. | The critic's scene.py re-run: TH_E001 e1 t1 ip267 `Byte[206]`, the same site as TH_E002's; story-o1e run1_S holds those rows. 4.7's "a Byte[206] from another site or scene ... is a FAILURE" was false for a same-site scene. | ADOPTED as O3-BATTLE, a core check (5.3): exactly one `battle` row -- row 0, scene 338, donor 62, an int result in `won`, the beat's value equal to it -- whose epoch is `battle_epoch0` + 1 (the driver now logs `battle_epoch0`: 2.2), landed 63 / 31213 with `landed_place` 63; 4.7 reworded (the site by LANDING (b), the scene by O3-BATTLE); mutants battle-scene-336 and battle-two-rows, plus battle-epoch-skip and battle-frame0-late (BATTLE alone, each). RE-SHAPED one clause: not "every battle-mode trace row has `f` in [frame0, land_frame]" -- `frame0` is the driver's first POLL that saw the battle, up to a poll or a page press after the scene went live (POLL_S 0.05 s plus the press's wait), and the AI's first [539] store can precede it, so the literal clause would read real runs NOT PROVEN by a race. O3-BATTLE (d) instead requires the field-mode rows nearest `frame0` to be a place-62 row before and a place-63 row after -- the window LANDING (c) puts every battle-mode row in -- both trace rows, so nothing races. |
| 3 (major) | "WRITES is EXACT because every store of 61-63 is classified" was untrue and unenforced; O3-SCENE silently skips TH_E002's 24 unresolved stores. | The critic's census.py re-run: 15/28/15 Global store sites, 0 unresolved; unlisted 61 and 63 e0 t0 ip130/ip211 and 62 ip134/ip215 (the prologue's else-branches, dead by ip57/ip138), named only in prose 61/63 ip41, 62 ip45 (`Int16[2]:=10000`) and 62 ip1023 (`Byte[4]:=1`); a lvalue probe: all 24 TH_E002 unresolved stores are `B_SYSLIST[0] ... B_LET`. | ADOPTED: the `dead` list (4.5: ten sites, each guard and why it is false on the route) proven by O3-KEYS -- measured: "53 sites (53 keys), every op in its statement, 4 compound values computed from their priors, none masked" (0.2 #3); O3-CENSUS (6.1), today "15 / 28 / 15, all classified, 0 unresolved"; O3-SCENE and O3-CENSUS classify every unresolved store by its lvalue token (`lvalue_class`: `B_SYSLIST[n]` only) and FAIL on any other; 4.4's claim now rests on the two checks; writes-extra-symmetric and last-place-wrong now stand on proven `dead` sites. |
| 4 (major) | Battle 338 is outside P-STOCK and the fingerprint, yet the stock S side and the noise claim rest on it. | FF9CustomMap's `EVT_BATTLE_LEDGER{1S,1W,_A,_B}` raw16/raw17 and battle `.eb` overrides; BattlePatch `Battle:` 67 x2, 336, 337, 334, 335 (FF9CustomMap, `Music: 0`), 67 (FF9CustomMap-msgs); DataPatchers.cs:747-783 (the `Battle:`/`AnyEnemyByName:`/`AnyAttackByName:` selectors; a name selector applies to any scene holding the name). | ADOPTED: P-STOCK-BATTLE (6.2) -- extended beyond the critic's list to `AnyAttackByName` and to name selectors matched against 338's own US strings, the engine's whole selector set; the fingerprint's `battle_patch` and `battle_overrides` (6.3); O3-SCENE's detail says it read the base copy and P-STOCK-BATTLE proves that copy loads (6.1); section 8's p-stock-battle unit. |
| 5 (medium) | LANDING (c) is anchored on noise rows, and the bytes allow none. | TH_E002 e1 t1 [517]-[554]: [525] sets `Instance.Byte[31]`, [533] JMP(10) lands on [546] before the [539] store. | ADOPTED: (c) anchored on `landing.before` (62 e4 t1 ip1285, chain #2; L62 holds no global store between it and `Battle(0,338)` at ip1293) and `landing.fresh` (63 e0 t0 ip22); zero battle-mode rows allowed and counted (4.7, 5.4); dry-run battle-zero-rows (PROVEN) and battle-zero-rows-62-resumed -- registered with every check it fails (CHAIN, LANDING, BATTLE, WRITES; the critic named two), as O3's exact `case()` requires. |
| 6 (medium) | The back cut is never checked; a residue row at the 63 -> 64 boundary would become the cut unseen. | segment_trace.py:126-135 (`cut_at_end`: `w` or `r`) against :138-153 (`cut_at_start`: `w` only). | ADOPTED: LANDING (e), `landing.end_row` (64 e0 t0 ip22 `Bit[191]:=0`, read raw, on both sides; 4.7, 5.2, 5.3); mutant end-boundary-residue-both (LANDING alone). |
| 7 (medium) | The coverage rule trusts the registry's `beat` and `won`: `won` [1, 2, 3] counts a defeat, `True == 1`, and nothing checks the beat is listed. | segment_trace.py:653-657; Python's `True in [1, 2]`. | ADOPTED: `battle_of` (2.1) requires `won` exactly [1, 2] or [1], the beat one of `beats` and named by no step, naming or choice rule (only the executor sets it, with the int result); O3-SCENE requires the shape the WinPose flag gives; S1's `done` requires `type(v) is int` (1.2); mutants: won [1, 2, 3] (battle-row unit and scene-census mutant), a beat not in `beats` (battle-row unit), battle-beat-true-one-S (session case). |
| 8 (medium) | NO-SC never fails alone; the byte199 rows contradict WRITES-exact; no LANDING clause has a mutant failing it alone. | storytrace.py:811-813 (harness sites kept out of the keys); o2_alexandria.py `_state_rows` (harness dropped), `span_sequence` (a harness row has no key and fails by name); o2_dryrun.py:936 (O2's `case()` compares only the checks named). | ADOPTED: sc-harness-poke-both (NO-SC alone; WRITES, NULL, STATE, RESIDUE P); WRITES F registered on byte199-fork and byte199-both; one LANDING-alone mutant per clause where one can exist -- (b) other-battle-noise-both, (c) 63-main-init-late-both (the critic's), (d) last-place-61-repeat-both, (e) end-boundary-residue-both; O3's dry-run `case()` made EXACT so "alone" is a checked fact (8). PARTLY REJECTED for clause (a): no mutant can fail (a) alone -- FORBIDDEN's `off_route` pattern reads the same raw `w` rows by `fld`, over every run, in the same start-to-cut window (segment_drive.py:161-169 `on_route`, :297-300, :345-377), and O3's frozen members map gives each route donor exactly one member (P-DONOR), so any row (a) rejects is also an unbacked FORBIDDEN hit (a `c` row (a) reads comes with its site's `w` rows); (a) stays as the covered-run statement of the law, its mutant (lands-real-63-covered) registered with its co-failures and the clause named. |
| 9 (medium) | The O2 gate never runs the one test proving S4 keeps O2's battle rule. | segment_regress.py:60 (G7's `-k "o1_ or overlay_hint or segment"`), the design's G12 `-k "o2_ or rehearse"`: "o2s" is not "o2_"; story-o2's six runs are all covered, so G8/G9 never take a VOID path. | ADOPTED: renamed `test_o2_drive_voids_a_battle_without_a_registry`, in `REQUIRED_TESTS_O2` (B4); 1.4 states G10 is the only VOID-path baseline; G13 (`-k "o3_drive"`, `REQUIRED_TESTS_O3`) joins the gate at B4, so a later shared-code edit (O4's) re-runs the battle beat's driver tests. |
| 10 (minor) | FakeGame H9 publishes a state the engine never does (field 63 with result 2). | As 11.2 #4. | ADOPTED with 11.2 #4: a stretch at (the battle's field, 2), then the fold and the flip on one fake frame; the test asserts no sample pairs the landing field with result 2. |
| 11 (minor) | Scope and wording: the US-session limit lives only in `report_extra` and `o3_forks.json`; Int16[11] is not bytes 22-23; `start_music.old` 1 was measured in field 100, not 61. | The trace's `Int16[11]` rows carry `byte` 11 and `entrance_bytes` is [2, 3] for `Int16[2]`; story-o2's first Byte[13] rows are 100 e0 t0 ip138, old 1 new 1, in all six runs. | ADOPTED: "US session" in O3-BUILD's title, the PLAN.md O3 heading and the CLAUDE.md milestone line (5.4, 6.1, C4); 0.2 #3 says bytes 11-12; 4.6 and F7 say O2 measured old 1 in field 100 and F7 is the first measurement in 61. Not taken (not asked): a change to the shared VERDICT line, which is O1's `verdict()`. |

Round 2 disproved nothing. The two re-shaped remedies -- the fake's `soft_reset_ui` set (11.2 #1) and O3-BATTLE
(d)'s trace-row window (11.3 #2) -- keep the critic's intent and change only what the source showed would misfire;
the one rejection -- a mutant failing LANDING (a) alone (11.3 #8) -- is of something that cannot exist while
FORBIDDEN reads the same rows, and (a)'s mutant is registered with its co-failures instead.

### 11.4 PART A, as built: where the design was silent (each the smallest correct thing)
PART A is built as section 9 orders it -- A0 (the O2 gate and its baseline, captured at 29603e62, the design commit,
before any shared-code change), then S1, S2, S3 and S5, each with its test, each test failing on registered mutants,
the gate 12/12 after every step. Nothing in 1.2 or 1.4 was disproved. Where the design left a choice open:

| # | Where | The design | As built, and why |
|---|---|---|---|
| 1 | G10's run_cases line | "printing 86/86 cases as registered" | The expected line is computed from the replica -- `n/n` with n its sessions plus its units (49 + 37 = 86 at the capture) -- not a literal: G10 also compares the replica's case order and every output to the baseline's, so a case added or dropped fails G10 by name before any count could. |
| 2 | G10's replica | "replicates run_cases's loop step for step" | Every step that makes a directory or an output is replicated in order (`pred/`, `sessions/`, `s0`..`s48`, state-history's session last, the offline mutants on the same temporary root). Left out: run_cases's verdict comparisons and its extra `read_session` reads of a case's VOID classes -- pure reads that make no directory and leave nothing an output reads. Measured before the capture: two readings identical (no temporary path, clock or random in any output), and the 86 print lines rebuilt from the replica equal run_cases's own. |
| 3 | The gate's CLI and output | `--capture-o2`; exit 2 on a missing archive or baseline | `--capture` needs only O1's archives, `--capture-o2` only O2's, the gate both (exit 2 otherwise); `--out` defaults to the baseline of the capture asked for; `--baseline-o2`, like `--baseline`, exists to test the gate. The gate prints O1's items before it collects O2's (a four-minute run shows progress), and its summary names both baselines' heads. |
| 4 | The O2 baseline | 1.4 G0' | As listed there, plus the archive's path: 565 KB, LF, `-text`. Before it was committed, each new item was failed by a mutant of the code it guards: VOID-ASYM's wording fails G10 ALONE (story-o2 takes no VOID path: G10 is O2's only VOID-path baseline, as 1.4 says); O2-START's detail fails G8 and G10; O2-KEYS's detail G11; the CLI's `print(report)` G9; `pick_for`'s refusal text G12. |
| 5 | S1 | `done(b)` with `won` inside | `won` is built once per `read_session`, `done(b, beats)` per run: the same rules. Its legacy branch still returns the beat's own value (truthy), exactly the old expression. |
| 6 | S3 | `if g.state.ui_state != "Title": st = g.state` | ONE read decides everything (`st = g.state`): `Session.state` re-reads the published state on every access, so the snippet's two reads could straddle a change (the Title test on one sample, the battle test on the next). Outside a battle the path is today's single read, warp and ladder. The docstring's old "(a run stopped mid-battle)" warp fallback is gone: mid-fight now never warps. |
| 7 | S5 | `session["ended"] = {"log", "ok", "why"}` | `why` is "" when the title came back and the error (300 characters) when `end_run` raised; `ended` is saved before the analysis runs. |
| 8 | `_stub_segment` | "it gains a `rerun` keyword" (A2) | It gains `beats_of=` (a reached run's beats) and `**over` (any prediction key: `beats`, `battles`) at A1, and `rerun=` and `void=` (the RouteVoid's class, cell and attribution) at A2. Every default is today's, so the existing segment tests run unchanged. |
| 9 | A1-A4's tests | as 1.2 names them | A1 runs its stub session on the fake (True and None travel through the session JSON) and adds a control reading of the same session without the registry (today's rule, O1's text). A2 and A4 run their controls on a second fake install (`tmp_path_factory`). A3 adds the failing soft reset, the outside-a-battle path and the title (the ladder alone). A4 adds a third session whose `end_run` raises: `ended.ok` False, the error kept, the report still written -- 1.2's "never raised", which no listed test reached. |
| 10 | The worktree | -- | The base templates were extracted into this worktree before any test ran (`py -m ff9mapkit extract-templates`: read-only on the install, gitignored outputs), so no required run skipped for them. |

### 11.5 PART B, as built: where the design was silent (each the smallest correct thing)
PART B is built as section 9 orders it: B0 first (the whole of `tests/test_harness.py` before any change, in this
worktree with the field manifest present: 639 passed, 1 xfailed, 0 skipped), then H9, H7, H8, S4 with G13, and the
S3/S5 fake tests. Every step has its tests, every new test fails on registered mutants (42 in all, each named in its
step's commit), and the gate passed after every step. The whole file read 649 passed after B3 and 665 after B5,
always B0's set by name plus the new tests, with B0's one xfail. Nothing in 2.1-2.6 or section 3 was disproved.
Where the design left a choice open:

| # | Where | The design | As built, and why |
|---|---|---|---|
| 1 | H7 `FightTimeout` | "raised on both no-result exits ... with the same messages" | It carries `kind` ("turns" / "timeout"). The executor must tell the row's own turn bound (V15, whatever the clock says) from a timeout the run's deadline cut (the budget, V13). Reading that off the message would hang a verdict on wording. The package exports it beside `HarnessError`. |
| 2 | H7 `last_fight` | `seconds`, `tutorials`, `timed_out` on both exits | One `record()` writes the result exit and both no-result exits, so the keys cannot drift apart. `seconds` is wall time to the millisecond; `tutorials` counts only the screens `_dismiss_tutorial` reports it closed; `timed_out` is False on a result. |
| 3 | H8 `stopped` | "scene-gone" \| "field" \| "presses" | Named from the stopping sample, in both modes: "field" when its UI is FieldHUD; "scene-gone" when the scene is gone and the field is not up (the BattleResult lag, or another UI, which only the default loop stops on); "presses" when the 40 Confirms ran out. `last_leave` starts None and is cleared at `begin_scenario`, as `last_fight` is, so one member's leave is never judged as the next one's. `timeout` stays unused, as it always was. |
| 4 | H9 `battle_exit` | the four phases | It applies to every end while it is set (the scripted one, `_settle_battle`'s, an escape), and `end_battle` refuses a second end while one runs. The over frame and BattleResult are one phase of 1 + `result_frames` frames, since their published states are identical. `exits` records each phase's first frame; the tests read "the frame the scene went" from it. |
| 5 | H9 soft reset | `soft_reset_ui` | A reset that fires from BattleHUD (possible only when the set holds it) ends the battle with the scene, so nothing of the battle is published at the title. `SOFT_RESET_ENGINE_UI` is the engine's set, one literal the tests import. |
| 6 | H9 movie beat | "a warp ends it" | A warp ends the movie's scene only while a movie plays. Any other warp behaves as before and leaves a scene's beats alone. `movies` records each movie (its frames, the frames it played, the skip dialogs opened, how it ended), so "resumes for what remains" is a count a test can check. |
| 7 | H9 scenes | (not named) | `scene(control=False)` is a scene that ends with control still off. 61-63 never grant control, and a scene that handed it back would read as V4 after the settle, or race the settle. The default is unchanged. |
| 8 | S4 `battle_of` | the beat "named by nothing else" | It also refuses a beat that `steps_default` or a battle row of ANOTHER slot (donor, sc, scene) names. A row of the same slot is the same registration, so an override of it (R-BATTLE-VOID's `max_turns` 0) validates against the predictions it overrides. The first cut compared rows by identity and refused that override; B4's unit test caught it. `battle_of` returns a copy. Stop pages are strict too: exactly `{"match", "why"}`, both non-empty strings. |
| 9 | S4 rule 1b | the visit's place | When no visit has begun (a battle at the drive's first poll), the poll's place stands in. There is no visit to take a place from, and nothing can have flipped the id yet. |
| 10 | S4 exits | the messages | V15 states its bound in whole seconds. Every executor exit that ends the run logs its battle row first (V13 for a budget, then V14, V15, V16, V11), so a VOID run still says how far its battle got. `land_wait` reads the state once when no time is left, because `wait_for` with no time left would raise a misleading "published nothing at all". |
| 11 | S4 leave presses | `press` rows | `pre` is the leave's own record of the sample (`frame`, `ui`, `in_battle`, `field`, `result`). It carries no `control`, so the backing rule can never read a leave press as a Confirm on the field. `field` and `donor` are the sample's. |
| 12 | B1-B5 tests | the director | The tests end a battle on the fake's own thread (the scripted-end slot), and the skip test's stray Confirm goes through the fake's step queue: the game's own thread executes both, as it executes a real press. A press that lands after the scene goes is COUNTED (at most the one already in flight), never timed against frames. A press for a window executes in a later frame than the one the window went up in, so "pressed after it" is `frame > up`: 61's last page press shares that frame, because the director answers it at once. |
| 13 | G13 | "joins the gate in the B4 commit" | `REQUIRED_TESTS_O3` holds the thirteen `test_o3_drive_*` names. G13 runs after O2's items and has no baseline: the list is the floor. It was shown to fail on a dropped name, an empty selection and a skip. |

### 11.6 PART C, as built: where the design was silent or wrong (each the smallest correct thing)
PART C is built as section 9 orders it: C1 `o3_prima_vista.py` with `o3_forks.json`, the `.gitattributes` line and six
tests; C2 `o3_dryrun.py`; C3 `o3_rehearse.py` with three fake tests, which joined `REQUIRED_TESTS_O2`; C4 PLAN.md's O3
section. Every new test failed on registered mutants (15 for C1, 9 for C3, each named in its step's commit), and the
dry run caught 20 mutants of the O3 code. `--offline-check` read 6 PASS with the numbers 6.1 gives, `--preflight` read
10/10 PASS on the live install, and the gate passed after every step. Two engine-source readings changed a remedy, and
three rows of section 8's table could not hold. Each is below with its reason; nothing else in sections 4-8 was
disproved.

| # | Where | The design | As built, and why |
|---|---|---|---|
| 1 | P-SETTINGS, `ini_settings` (4.13, 6.2) | "the engine's ini reading: the last assignment wins, sections and keys case-insensitive" | The engine source DISPROVES the case rule. Memoria's configuration reader (Memoria.Prime/Ini/IniReader.cs) looks sections and keys up in dictionaries with the default comparer, so it is CASE-SENSITIVE. It ends a value at its first `;`; a `;` right after that one adds a literal `;`, and the next other character ends the value (ReadPair's escape falls through, so `a;;b` reads `a;`: corrected by the review, 11.7 #9). And after the root Memoria.ini it reads each stacked folder's own Memoria.ini in REVERSE folder order, so the first folder's wins (:94-125). `ini_settings` reads one file that way, and `install_settings` layers the files the same way. Today MoguriMain ships a Memoria.ini, but it sets only `[Graphics] TileSize`, none of 4.13's keys. A case-insensitive reader would only FAIL on a key the engine ignores (the safe direction). A reader without the layering would PASS a folder's override that the engine applies (the unsafe one). The C1 test pins all three rules. |
| 2 | P-LAUNCH (6.2) | the four patch files and Memoria.ini | P-LAUNCH also dates every stacked folder's own Memoria.ini, since the launch's configuration read them (#1). Today's MoguriMain/Memoria.ini (2025-05-20) is older than the launch. P-LAUNCH and P-DONOR-LOG take the stacked folders from the DRIVEN game's Memoria.ini (`dali_tour.mod_roots(g.game_path)`), as P-LANG reads that game's ini, so they read the install the launch is. |
| 3 | O3-KEYS (6.1) | `start_music` "is a writes site and is checked with them" | `start_music` must also be exactly ONE `writes` key (the same site, target, value and op), so the two registrations cannot drift apart; offline mutant keys-start-music covers it. O2's detail says "O2-START reads it raw"; it is rewritten to O3-START. |
| 4 | O3-SCENE / O3-CENSUS, `lvalue_class` (6.1) | "classified by its statement's lvalue token" | `unresolved_lvalues` mirrors `instruction_stores` step for step, with the same CalcStack arities and lvalue depths, and keeps the TEXT of each operand push. Each unresolved store then gets the token it really writes through, never just the expression's first token. A computed lvalue reads None and FAILS by name. TH_E002's 24 stores read `B_SYSLIST[0]`. `scene_census` also returns the scene's US names (TypCount enemies, then AtkCount attacks), which P-STOCK-BATTLE matches name selectors against, so one install read serves both checks. |
| 5 | O3-CENSUS (6.1) | "masked 2/2/2 (61's ip22 is start_first)" | Sites are classified in a fixed order: writes, chain, masked, start_first, error path, forbidden, dead. 61's ip22 is both masked and start_first, so it counts as masked, and the detail says so. The start_first column is printed only when it is non-zero. |
| 6 | O3-LANDING (5.3) | clauses (a)-(e) | (a) and (b) name the first offending row of each run. (a) reads field-mode rows from every source, so a harness or C# row counts as a field row. (c)'s `before` and `fresh` are matched RAW on place, field (member(place) on F), site, target and value. (e) needs the raw row at the cut line, which the kept rows end before, so `why_void` re-reads the trace and keeps that row as `r["cut_row"]`. |
| 7 | O3-BATTLE (5.3) | "exactly ONE battle row ... registry row 0" | Generalized to one row per registry row, in order, each with epoch `battle_epoch0` + 1 + n. With O3's one row this is the design's rule exactly. |
| 8 | dry run: byte199-fork (8) | "NOT PROVEN (NULL F, STABLE F, LANDING F (b), WRITES F, STATE F)" | NULL cannot fail here. A key in ONE fork run of three is UNSTABLE, never FORK ONLY: `storytrace.Comparison.fork_only` needs the key in every fork run (`f == nf`). The case registers NULL P and STABLE F. **byte199-every-F** is added (the row in every F run): NULL F, WRITES F, STATE F, LANDING F (b), STABLE P. It is the NULL proof that O1's second noise row is no O3 noise. |
| 9 | dry run: last-place-wrong and last-place-61-repeat-both (8) | (d) with WRITES; and "(d) alone" | Both also FAIL O3-SEAM. On F the stray 61 row stands at member(61) 31211, the run's last field before 64. The digest's crossing out of the members is therefore member(61) -> 64, which O3-SEAM rejects (it wants member(63) -> 64). So no both-sides construction can fail (d) alone: SEAM reads the same transition on F, just as FORBIDDEN reads (a)'s rows (11.3 #8). Both cases register SEAM F. **last-place-harness-S** is added: every S run has a harness poke (`Byte[300]`) standing in 61 after 63's ip820. No key, no history and no seam reads a harness row on S, so LANDING (d) fails ALONE, and "alone" stays a registered fact. Section 8's 87 rows plus these two give 89, all as registered. |
| 10 | dry run: frame0 with no battle row (8) | "frame0 between 62's ip1285 and 63's ip22" | With battle rows, `frame0` is two battle rows in, since the AI's first stores can precede the driver's first poll. With none, it is just after 62's ip1285, where the battle begins (`Battle(0,338)` is ip1293), never after a later 62 row. battle-zero-rows-62-resumed's (d) depends on this: ip1345 is the first field row after `frame0`. |
| 11 | rehearse: stage selection (7.1) | `O3_STAGE` / `--field` / the default order | `--field 61` picks R-START and `--field 62` picks R-62. R-FULL, R-SKIP and R-BATTLE-VOID are by name only, and so is F-SMOKE, which warps into six fields. The default order is the table's, with R-BATTLE-VOID moved last by its `last` flag; R-SKIP is optional. |
| 12 | rehearse: the launch's readings (7.2, F10, F12) | "the settings fingerprint, the P-LAUNCH, P-DONOR-LOG and P-STOCK-BATTLE readings" | The launch gates on every capability (P-CAP, P-OBJECTS, P-LANG, P-DONOR-LOG, P-LAUNCH), as a session does. It records the settings, P-SETTINGS and P-STOCK-BATTLE without gating, since F10 and F12 only read them. Each traced run also records `g.last_fight` and `g.last_leave` beside the battle rows. |
| 13 | rehearse: F-SMOKE (7.1, F5) | per warp: the field, the objects, the exceptions, the log, end_run | The smoke stops at a failed end_run, because the next warp would start from an unknown state. The exceptions are recorded with a flag for those through the story machinery (O3-THROW's set). Twins compare their sids as sorted lists, so 62's entry instanced four times counts four times. |
| 14 | report: 61's movie (5.4) | "the arrival frame (the visit row) and the first page press (frames, seconds)" | The driver's log keeps frames only (visit and press rows carry no time), so the session report gives frames. Seconds and fps come from the rehearsals' recorder (`movie`). |

### 11.7 The review: twelve findings on the built O3 (eleven defects; each fixed, one half disproved)
A code review of PARTs A-C raised twelve findings: one high, three medium, eight low. #2 and #10 are one defect seen
through two lenses. Each was re-checked against the code, an archive or the engine source before it was fixed. Each
fix has a test that fails without it (a mutant run, named in its commit). The engine source disproves one half (#4's
FieldScene half), and one optional part is not taken (#1's act() clip); both are named below. The gate ran after
every commit that touched shared code (13/13, then 14/14 with G14), and o3_dryrun reads 92/92 (89 before).

| # | Finding | Re-checked | Disposition |
|---|---|---|---|
| 1 (low) | `leave_battle`'s `timeout` is dead, and the executor ties the leave to no deadline: a battle beat can overrun the run's budget. | session.py `leave_battle` (a fixed 40 x (Confirm, 20 frames), `timeout` never read, as on master); segment_drive.py step 3. | FIXED: the loop stops at `timeout`, checked before each Confirm and after the field test (`stopped` "timeout"; the 90 s default outlasts the 40 Confirms, so O1's call is unchanged). The executor passes `min(land_cap_s, the run's time left)` (2.3 step 3, H8). NOT TAKEN, the optional third part: clipping `fight()`'s inner `act()` wait (20 s) to the deadline. Near the row's own bound a clipped `act()` raises an instrument error where the bound is V15, so it would need `act()` errors reclassified as timeouts past the deadline. That is new semantics in a shared verb, to save one `act()`'s bounded overrun. Tests: `test_leave_battle_stops_at_its_timeout`, `test_o3_drive_bounds_the_leave_by_its_row` (G13). |
| 2 and 10 (low) | `fight()` raises FightTimeout "timeout" when the battle scene went away with result 0, and the executor files it as V15 (the driver's bound) or the budget. | session.py `fight` (one exit for the bound and the vanished scene); the FakeGame's soft reset from BattleHUD drops the scene and leaves the result 0; segment_drive.py step 2. | FIXED: a third kind, "gone": the scene gone with no result while both bounds held, its own message, `timed_out` False. The executor treats it as an instrument stop: it logs the battle row (V13, driver), then raises `HarnessError` (STOPPED, V13), never V15 and never the budget's text (2.3 step 2, 2.6, H7). Tests: `test_fight_tells_a_vanished_battle_from_a_timeout`, `test_o3_drive_stops_on_a_battle_gone_without_a_result` (G13). |
| 3 (high) | A reached run whose trace holds no end-place row is covered; O3-LANDING (e) then reads a driver timing artifact as a fork finding. | story-o1e: run 3 S is "covered ... cut at line None"; every O1 run closed its trace 1-4 frames after the field changed, run 3 S 4 frames after its last row in 52, with no row of 100. | FIXED both ways. A-NOEND (driver) uncovers such a run (5.1); dry-run case end-row-missing-one-S reads PROVEN with that run A-NOEND, where without it the case reads NOT PROVEN: O3-LANDING. And rule 1 waits for the row first: opt-in `budget.end_row_s`, O3's draft 10 s. The wait uses `cut_at_end` over the live trace and never runs past the deadline, and the `end` row records `end_row` (2.2). Without the key rule 1 is O1's and O2's exactly. Test: `test_o3_drive_waits_for_the_end_places_first_row` (G13). |
| 4 (medium) | P-STOCK-BATTLE never reads DictionaryPatch.txt: a `BattleScene` line can rebind battle 338 with no file under its name and no selector. | DataPatchers.cs:255 (`Split(' ')`), :565-575 (`SceneData["BSC_"+x] = ID`, `MapModel`); TwoWayDictionary.cs (no duplicate values: the setter overwrites the reverse entry); HonoluluBattleMain.cs:198-215 (the scene is the reverse entry: its raw17, sequence, text and `EVT_BATTLE_<x>`); btlseq.cs:24 and HonoluluBattleMain.cs:202 read the forward entry; FF9CustomMap holds four such lines (30871/30872/30881/30882). | FIXED, (c): a `BattleScene` line whose id is 338 (rebound) or whose name is TH_E002 (`BSC_TH_E002`'s forward entry repointed) FAILS. The line is read as `PatchDictionaries` reads it, and every other BattleScene line is listed (6.2). The fingerprint gains `battle_scenes` (6.3). The live install: PASS, the four LEDGER lines listed. DISPROVED by the source, the FieldScene half: a `FieldScene 338` line sets only `EventDB[338]`. A battle never reads it, because its script is `"EVT_BATTLE_" + name` and `EventDB` is read only by ff9.cs:9306's field and world init. It PASSES, registered in the unit and the test. |
| 5 (low) | O3-BATTLE (c) has no dry-run mutant: dropping it read 89/89. | o3_dryrun.py: every BATTLE case registers (a), (b) or (d); `battle_log_row` always writes the right landing; the V16 cases VOID their F runs. | FIXED: battle-landed-real-63-log-F and battle-landed-member-log-S, BATTLE (c) alone each (5.3, 8). With (c) dropped the dry run reads 89/91, these two. |
| 6 (low) | PLAN.md says LANDING reads a V16. | A V16 run is uncovered and LANDING reads covered runs only: the dry run's v16-all-F reads LANDING VOID, and v16-one-F reads it PASS. | FIXED: PLAN.md and open risk 2 now say VOID-ASYM and FORBIDDEN, with LANDING (a) only if such a run were ever covered (10). |
| 7 (medium) | Each rehearsal record copies `g.last_fight` and `g.last_leave`, which nothing clears between runs: a run that never fights inherits the last fight. | session.py clears them only at `begin_scenario`; `o3_rehearse.one()` never calls it. | FIXED: `one()` clears both first (7.2). Test: `test_o3_rehearse_clears_the_last_fight_between_runs_on_the_fake` (G12). |
| 8 (medium) | `end_run` tests `in_battle` alone. A battle exit's load (the scene gone, the UI still BattleResult) takes the outside-a-battle path: the warp is refused, and the ladder starts from BattleResult. | H8's lag; H9's fourth phase; a throwaway fake run logged exactly `recover-warp-failed`. | FIXED: the end sequence is `in_battle or ui_state == "BattleResult"`, the docstring's own rule. The mid-fight reset is unchanged (1.2 S3). Tests: the A3 stub's load leg, and `test_segment_end_run_waits_out_the_battle_load_on_the_fake` (G7). |
| 9 (low) | `ini_settings` reads `a;;b` as "a;b". The engine reads "a;". | IniReader.cs:169-185: ReadPair's escape branch appends the `;` and clears the escape, with no `continue`, so the same `;` re-arms it and the next other character ends the value. | FIXED: the loop is the engine's, statement for statement (`a;;;;b` reads "a;;;"). The C1 test asserts the engine's values, and 11.6 #1's wording is corrected. |
| 11 (low) | `FakeGame.scene()` writes a movie's countdown into the caller's beat dicts, so a dict staged twice plays no second movie. | fakegame.py `_next_beat`, `_step_scene`, the skip's `movie["_left"] = 0`. No test replays one today. | FIXED: `scene()` copies each dict beat. Test: `test_fake_scene_copies_its_beats`. |
| 12 (low) | o3_dryrun runs in no gate item and no test, yet 1.3 says a later shared-code edit must keep it green. | segment_regress.py's G13 is `-k "o3_drive"` only; nothing imports o3_dryrun. | FIXED: G14 (1.4) runs `o3_dryrun.run_cases` (the frozen predictions once they exist, else the draft): rc 0, N/N, N >= 92. It was shown to fail on a dropped case (91, under the floor) and on (c) disabled (90/92). Without the frozen file or O1's chain build, the gate says "not run". |
