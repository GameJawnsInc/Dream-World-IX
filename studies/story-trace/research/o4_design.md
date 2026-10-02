# O4 -- the sword fight under the trace: the design

**Status: DESIGN, offline.** Nothing is imported, built, deployed, launched or frozen. The inputs are `o4_route.md` and
`o4_research.json` in this folder (the reconciled route, the sword fight's decode, THE 100 PLAN) with the critic's
problems (`critique.problems`) overriding the route where they conflict, and the seven decisions the lead made on
top of both (0.1). This file folds them into code-level decisions in `o3_design.md`'s structure and keeps what O2
and O3 learned. Every number below was read, read-only, from the stock US `.eb` files (through the kit), the
research listings (`<scratchpad>/o4_research/reconcile/L{64,150,153}.txt`, `chanbara/chanbara_annotated.txt`), the live
install (mod folders, `Memoria.ini`) and the live Memoria source (`C:\gd\FFIX\Memoria`, = the deployed DLL); 0.2
says how. The offline check (section 6) re-derives every one of them.

**Revision 2** folds in the second critique round -- driver robustness (12 items) and claim integrity (15) -- each
re-checked in the bytes, the engine source and the archives: 0.3 lists what that re-check found (two of 0.2's
numbers were wrong), 11.3 gives every item's disposition (adopted, refined, or rejected with its reason).

**The segment:** New Game, the trace armed, then in field 70 (after 70 e0 t0 ip130, before ip475) a raw
`warp <64 | member(64)> 100 1155`. The route runs 64 (stage 1 walk-in; the KEYON-closed pair 105/106; the tutorial
page 111; THE SWORD FIGHT, 49 prompts over 50 passes; the KEYON-closed pair 107/108; the score pages 122/123;
choice 127 answered No; page 128) -> `Field(150)` (64 e2 t1 ip536) -> 150 (13 pages, the KEYON-closed pair 98/99,
stage 10's party rebuild, `SC := 1190` at e3 t1 ip1966) -> `Field(153)` (150 e3 t1 ip2169). It ends on ARRIVAL in
153, cut at 153's first row (e0 t0 ip22): real 153 on S, member(153) on F. No control, battle, FMV or naming
anywhere.

What O4 newly puts under the trace: a MINIGAME played by the driver to a fixed outcome (the owner's displayed
100/100) on both sides, the zone's first SC write since O2 (1155 -> 1190), a fork side that ENDS IN A MEMBER (every
earlier segment ended in a real field shared by both sides), and twenty alxc members never built, deployed or loaded.

---

## 0. What this design decides, and what it found

### 0.1 Decided upstream (not relitigated)
1. **The owner's requirement.** The driver scores a displayed 100/100 in the sword fight -- "Of 100 nobles watching,
   / 100 were impressed." (page 122), `Byte[475] := 100` at 64 e4 t1 ip338, `Bit[3815] := 1` at ip390, page 128
   "They shower you with 10000 Gil!" -- on BOTH sides in EVERY covered run, under the LIVE settings (Memoria.ini
   `SwordplayAssistance = 1`, never changed by us; P-SETTINGS pins it). The SESSION plays FAST (react as soon as the
   prompt is published: raw ~114-123, so 100 shows with or without the +30%). A run that scores below 100 is never a
   FAIL by itself: V17 (driver: its own input was not the frozen play) or V18 (game: its rows prove the frozen play and
   the game still scored lower -- a finding VOID-ASYM reads).
2. **The segment** as above; END on arrival in 153, cut at 153 e0 t0 ip22. Control anywhere is V4.
3. **The fork chain:** the alxc disc-1 set, verbatim, per-language (today's kit; no legacy us-build acceptance):
   `import-chain 64 --verbatim --ids 64,68-69,150-151,153-167 --fresh-ids --id-base 31240 --name-prefix O4
   --mod-folder FF9CustomMap --out C:/gd/_ns_playtest/o4/fork`, then `build-all ... --out C:/gd/_ns_playtest/o4/build`
   (outside the repo and the install). Expected member(64) = 31240, member(150) = 31243, member(153) = 31245 -- read
   from the written campaign.toml. `o4_forks.json` records it all with `"deployed": false`; the LEAD deploys later.
4. **Per-side ends** (critique major #1): S ends in real 153, F in member(153); each side driven and judged with its
   own end list, opt-in so O1-O3 analyse byte-identically; an O4-LANDING clause pins F's end-cut row to member(153);
   any real-64/150/153 row on F is a finding.
5. **The +30% gate witness** (critique major #2): the session stays FAST. A REQUIRED paired stage R-GATE, run by the
   lead in game after the deploy and before the session, outside the frozen claim, with a PACED policy option (each
   press scheduled from the prompt's first-seen frame to a target j of ~22 engine ticks). Its report judges whether
   the EMinigame +30% fires on member(64).
6. **The critic's minors are binding fixes** unless the bytes/engine disprove one (then said in 11.1): the fail-closed
   zone; the timeout detectors; page-once and the quiet windows; the stray-Yes attribution; cfg.control and the 30 Hz
   tick as DERIVED; P-PAD; the LEFT/RIGHT x-delta witness; field 70's override sha pinned; the global side-effect
   note; O4-BUILD's fork-gate byte pins.
7. **Built ON the shared machinery**: `O4Segment` in `o4_castle.py`; the Chanbara policy `pred["chanbara"]` in
   `segment_drive`, strict and opt-in like `pred["movies"]`; the regression gate extended to O3 with its baseline
   captured FIRST. Predictions are frozen by the lead after the stock rehearsals (draft + `--freeze` that refuses to
   overwrite). No movie policy (FMV004 is past the end). Every perfect run reports Steam's Encore achievement
   (score >= 75, EMinigame.cs:34-38): outside gEventGlobal, noted, never suppressed.

### 0.2 Found while designing (each verified offline, read-only)
1. **A timed-out prompt LINGERS BESIDE its successor.** On a timeout e20 runs `CloseWindow(1)` (ip1424) and, in the
   same tick, the next pass's `WindowAsync(1,160,112+n)` (ip789-852). `CloseWindow` -> `DialogManager.Close`
   (DialogManager.cs:205-222) -> `Dialog.ForceClose` -> `Hide()`: a chat-style window enters `CloseAnimation`
   (Dialog.cs:610-643) and leaves `activeDialogList` only at `AfterHidden` -> `ReleaseDialogToPool` (Dialog.cs:687-692,
   DialogManager.cs:269-275). The close tween is `StartHideDialog` (DialogAnimator.cs:144-173): one
   `WaitForEndOfFrame`, then progress 0 -> 0.6 at `deltaTime / 0.15` -- **0.09 s plus a frame** (rev. 2; rev. 1 said
   the whole `DEFAULT_ANIMATION_TIME` 0.15 s). `ETb.NewMesWin`'s `DisposWindowByID(1, true)` (ETb.cs:96, :221-224) then
   finds the old window already closing (`ForceClose` is a no-op in `CloseAnimation`), and the new one joins the list
   at once (`AttachDialog` -> `GetDialogFromPool` -> `activeDialogList.Add`, DialogManager.cs:99-101, :184-203). So for
   0.09 s plus a frame the published dialog list holds TWO prompts, old and new, different DBTNs (prompts never
   repeat, e20 ip681). The critic's "no prompt-free sample" holds; "replaced at once" does not: the instance tracker
   reads the NEW instance as a listed DBTN that is neither the current one nor a closing one (2.4.3).
2. **A slow HIT re-arms in its own tick, as a timeout does.** e20 enters its WAIT (`Byte[52] > 0 && Byte[47] == 1`,
   ip1376-1394) only after the previous result's reaction (A ~28 ticks after a LEFT/RIGHT hit: the six-tick slide loop,
   `WaitAnimation`, `Wait(22)`, ip975-1063; ~30 after the others: a 30-frame clip at one frame a tick, `aspeed` 16,
   Actor.cs:20, EventEngine.ProcessAnime.cs:125). A press landing at j > A finds e20 already waiting: e3 sets
   `Byte[47] := 2` and closes the window, e20 (after e3 in the tick) leaves the wait, scores, rolls and arms the next
   prompt in THAT tick. So "a DBTN change with no prompt-free sample" means a timeout OR a hit later than the reaction.
   A hit at j <= A leaves a gap of about A - j - 3.5 ticks (the 0.09 s tween and its frame) before the next prompt:
   >= ~8 ticks (~270 ms) at the fast policy's per-instance cap j_cap 16, so under the fast policy a prompt-free
   sample normally separates two instances (recorded as `gap`; rev. 2 rests no verdict on it); the paced policy (j
   ~22-25) runs within ~0-3 ticks of it, its prompts OVERLAP, and the tracker holds the closing prompt apart (2.4.3,
   11.3).
3. **Bit[3815] is stored AFTER page 123 closes.** 64 e4 t1: ip338 `Byte[475] := Int16[48]` (before the pages),
   ip375 `WindowSync(5,0,122)`, Wait(5), ip384 `WindowSync(5,0,123)`, then ip390 `Bit[3815] := 1`, ip399 Wait(10), the
   choice at ip462. The stray-Confirm window after 123 is that `Wait(10)`.
4. **150 holds 273 store sites.** `instruction_stores` over every function (the census script, 0 unresolved, every
   function decodes): e0 t0 16, e3 t1 15, e10 t3 215 (the moogle's MOGNET talk), e15 t1 5, e16 t1 4 (Confirm
   hot-spots), e18 t2 3, e19 t2 2, e23 t1/t14/t15 13. At entrance 325 Main_Init instances ONLY objects 2, 3, 5, 6, 9,
   4, region 18 and code 17 (e0 t0 L248-277, ip258-287); entries 7, 8, 10-16, 19 and 23 are instanced only on the
   other entrances' branches (ip370-471, ip533-583). So O4's census classifies whole FUNCTIONS as `inert` (not
   instanced at 325: 239 sites) and e18 t2's three as `dead` (region 18 IS instanced, but its tag 2 opens
   `SET(SYSVAR[2]) JMP_IF(L8) RET()` at ip30-37: without control it returns first). 64's 25 sites are classified one
   by one, as O3's were. 153: 51 sites, none before the cut but ip22.
5. **The gamepad hazard, located.** `HonoInputManager.CheckPersistentInput` (HonoInputManager.cs:554-567) reads
   `GamePad.GetState(PlayerIndex.One)` (:558) and ORs the pad's buttons in -- `CheckRawXInput` (:531-552: A, B, X, Y,
   the shoulders, Back, Start, a trigger past 0.75) -- when `Configuration.Control.AlwaysCaptureGamepad ||
   ApplicationIsActivated()` (:563); the keyboard needs focus (:561). Memoria.ini :126 `AlwaysCaptureGamepad = 1`.
   The sticks and the d-pad reach the direction bits through the axis path (not re-read here: P-PAD treats any
   deflection past 0.10 of full scale -- `[AnalogControl] StickThreshold` 10 -- as non-neutral). The engine reads
   slot 0 only; P-PAD samples 0-3 (a reconnect can move a pad's slot).
6. **cfg.control and the tick, derived.** The harness's New Game is `TitleUI.HarnessStartNewGame` ->
   `OnNewGameButtonClick` (TitleUI.cs:963-977) -> `FF9StateSystem.ReInitStateSystem` (FF9StateSystem.cs:64-66) ->
   `SettingsState.Initial` (SettingsState.cs:127-139): `cfg = new FF9CFG()` (FF9CFG.cs:6-10: `control = 0`),
   `IsBoosterButtonActive` rebuilt with [1] false (`IsFastForward`, :55), then `InitialInput` -> `SetPrimaryKeys`
   (HonoInputManager.cs:636-640, 967-975): the identity `logicalToButton` at control 0 (swapped only for
   `EventInput.isJapaneseLayout`). So Menu/Cancel/Special press Triangle/Circle/Square (EventInput.cs:476-534:
   `GetKeyMaskFromControl` = logical | physical by `LogicalControlToPhysicalButton`), and `FastForwardFactor` is 1
   outside a Movie scene (SettingsState.cs:66-74): TimeLeft counts FieldTPS ticks, 30 a second (Memoria.ini:53,
   `[Graphics] Enabled = 1` :49). DIRECTIONS bypass that table: `ProcessInput` sets Up/Down/Left/Right directly
   (EventInput.cs:328-346) -- `GetKeyMaskFromControl` maps all four to `Up` (:509-516), a Memoria bug on a path
   O4 never takes. Start (`Control.Pause`) sets `EventInput.Start` = 0x8 (:303-305), the bit 64 e3 t1 ip412 reads as
   a level (`B_KEY(8)`).
7. **The New-Game override, pinned.** FF9CustomMap-world ships `evt_alex1_ts_opening.eb.bytes` in all seven languages,
   each 1424 B, sha256 `2ce8887ea969db6b6518bd33151b1a8805af10a6c9c96a0f59b49bad9ffc9215` (one file, seven copies).
8. **The live id band.** FieldScene >= 31000 is registered only in FF9CustomMap: 31100-31114 and 31200-31237; the
   other stacked folders register none; ForkDonorPatch exists only in FF9CustomMap (74 lines). 31240-31259 is free
   today (re-read before minting).
9. **The regression premises hold at the branch head** (b3d62304): `segment_regress.py` 14/14 PASS; `o3_prima_vista.py
   --analyse <story-o3> --predictions o3_predictions_v1.json` reproduces the archived `o3_report.txt` byte for byte
   (55310 chars, 17 checks, PROVEN); `--offline-check` 6 PASS; `o3_dryrun.py --predictions o3_predictions_v1.json`
   "102/102 cases as registered" in 24 s.
10. **153 rewrites only equal values before the end-state read lands.** Its 325 branch (e0 t0 L273-435, ip279-441)
    holds no gEventGlobal store; the prologue rewrites Bit[191]/Bit[184]/Int16[9]/Byte[13]/Int16[11]/Byte[14] with
    the values 150 left; its Byte[8] stores (ip1188, ip1260) are other entrances' (L1182/L1254, before the L1288 tail).
11. **EMinigame, re-read** (EMinigame.cs:9-38): the bonus fires at `s1.sid == 4 && s1.ip == 223` under
    `EffectiveFieldId(fldMapNo) == 64` (:12-21) and writes Map.Int16[48] only (no trace row); the SA >= 2 branch
    refills TimeLeft only while `Byte[52] > 0 && Int16[34] < 50` (:23-30); the achievement at score >= 75 (:34-38).
12. **A press's frames are exact from the agent's own log.** `Update` runs `PollRequest` (every 2 frames idle, every 10
    while a queue runs) then `DrainQueue` in the SAME frame (HarnessAgent.cs:301-323, :500-545); `press` Schedules
    down at frame+1 and Blocks frames+2 (:599-607, :1061-1066); the `accepted` event carries `frame`
    (`Event`, :2427-2441). So accepted frame A = that event's `frame`, down frame = A + 1 -- no inference from
    accept_ms.
13. **The fake today** presses at execute time (`_execute` -> `_menu_step`, fakegame.py:952-957) and keeps aliases as
    sent (`_control` maps only directions, :2841-2846): a faithful Chanbara model must instead read HELD BITS per
    frame (the agent's down at frame+1) and map `circle` to Confirm/Cross the agent's way (HarnessAgent.cs:1430-1449).
14. **The harness field warp never redirects a donor.** `Ff9mkDebugMenu.ServicePendingWarp` calls `ee.SetNextMap(mapNo)`
    as given (Ff9mkDebugMenu.cs:2112-2147); `ForkSiblingField` runs only on a fork-entered battle's return
    (HonoluluBattleMain.cs:736-737) and the overworld's field entry (ff9.cs:9327). So `warp 64 100 1155` lands in REAL
    64 on S after the deploy too, and stock 64's `Field(150)` stays real.

### 0.3 Found in the second critique round (rev. 2; each verified offline, read-only)
1. **A page ignores Confirm while it opens.** `Dialog.OnKeyConfirm` hides a window only in `CompleteAnimation`
   (Dialog.cs:762-797); a window without the typewriter reaches it at `AfterShown` (:645-651), which `StartShowDialog`
   runs after growing the box from progress 0.3 to 1 at `deltaTime / 0.15` and one more frame (DialogAnimator.cs:43-47,
   :61-126): **0.105 s plus about two frames** -- ~8 frames at 60 fps, ~5 at 31. A Confirm in it is dropped (on a choice
   it sets `SelectChoice = defaultChoice` and closes nothing, Dialog.cs:798-802). Measured: O2 R-FULL run 1
   (`20260930-184253-o2-rh-R-FULL`), "Received Goblin Card!" first seen at frame 6549 -- the press accepted at 6550
   (down 6551) was dropped, the next (accepted 6570) closed it. Rule 7's first press on a page that opens right after
   another lands in this window by construction (122 closes, `Wait(5)`, 123 opens: the loop sees 123 within 0-3 frames
   and its press goes down 2-4 frames later). So a page pressed once can stay up: no quiet window starts at a press
   (2.4.11).
2. **The edge is frame-scheduled; only the publication's order is unknown.** `HarnessAgent.IsHeld` keys on
   `Time.frameCount` (HarnessAgent.cs:70-77: held in [down, down + frames)), and a frame's tick count is computed by its
   first reader through `FPSManager.AdvanceUpdateCounter`, which reads the input (`ReadInputLight`) BEFORE that frame's
   ticks (FPSManager.cs:13-17, :77-111, :124-139); every tick's `ETb.ProcessKeyEvents` reads that accumulated level
   (ETb.cs:50-63, EventEngine.cs:114-119). So a press down at frame D gives its edge on the first tick of the frames
   >= D, whichever of the agent's Update and HonoBehaviorSystem's runs first. That order decides only what a sample
   shows -- the ticks of frames <= f, or only <= f-1 -- and no execution-order attribute in the source fixes it (none in
   Assembly-CSharp); tickrate.py:67-69 measured "the agent first" in one frame. 2.4.7 bounds j under BOTH orders.
3. **The slides start a tick after the arm.** In the arm tick S, e20 runs `RunScript(2,13,11)` (ip861; REQSW returns 0
   when e13 accepts, EventEngine.DoEventCode.cs:154-183) and walks on into its slide loop (ip918-1063) in the same run:
   i = 0 moves nothing, then `Wait(1)` (ip1040); Blank stands at -60 after tick S+1 and at -300 after S+5 (+300 for
   RIGHT, ip1066-1211). Zidane's loop (e13 t11 ip1617-1765 / ip1768-1916) starts at S+1 -- e13 runs before e20 in a
   tick, so the request is taken the next tick -- with its own no-move i = 0: -60 after S+2, -300 after S+6. A sample
   that lists the new prompt may already show a step or two (at ~31 fps a frame holds about a tick); the last sample
   that does NOT list it yet (its `prev`) shows none (2.4.6).
4. **The ring holds what the press calls read.** Every channel read -- the executor's and `_await_ack`'s 20-ms polls
   while a press blocks (session.py:663-695) -- goes through the channel's observer into the ring and the clock
   (session.py:331, :794-801; channel.py:1058-1063). The ring keeps the last 300 distinct frames (~10 s at 60 fps,
   artifacts.py:35-72), `states_since(frame)` returns them (session.py:7983-7988), and `channel.state` itself can wait
   up to a second on a locked file (channel.py:1023-1075). The executor merges the ring after every press and judges
   on that merged stream (2.4.1).
5. **The menu guard is the route's lack of control.** Triangle (`Control.Menu`) opens the main menu whenever
   `IsMenuControlEnable` is set (UIKeyTrigger.cs:694-700, :863-869); `DisableMove` clears it (EventEngine.DoEventCode.cs
   :1046-1051) and FieldHUD sets it on show to `usercontrol && IsMenuON && IsMovementControl` (FieldHUD.cs:394-397). No
   `EnableMove` runs on the route (2.1), so it stays off -- a reading, not a guarantee: the executor stops (V13, nothing
   pressed) on any sample whose `ui_state` is not FieldHUD (2.4.3).
6. **`[NUMB]` is substituted when the label renders.** A `STRT` window parses only to `ConstantReplaceTags` at show
   (Dialog.cs:1560-1569); `[NUMB=n]` is replaced in the render pass (`UILabel.OnFill` -> `ParseVariableTextReplaceTags`,
   UILabel.cs:787-803, DialogBoxSymbols.cs:154-170). A sample can publish 122 or 128 once before its number is in, so
   the page checks need two consecutive equal samples (2.4.12).
7. **The speed booster is keyed and unpublished.** With `[Cheats] SpeedMode = 1` (live), F1 toggles HighSpeedMode
   (UIKeyTrigger.cs:243-255): `FastForwardFactor` 3 runs three ticks a tick slot (FPSManager.cs:83, :95-97) and cuts the
   dialog tweens threefold (DialogAnimator.cs:8-18). New Game clears it (0.2 #6); mid-run only a key or a pad can set it,
   and no published field shows it -- the input witness (2.4.3 step 0) is the guard.
8. **The engine, pinned.** The live x64 and x86 `Assembly-CSharp.dll` and `C:\gd\FFIX\Memoria\Output\Assembly-CSharp.dll`
   all hash to sha256 `ba9762423da8f3d749a41a9988ef951d2a4fa62c296acc5aa44054439b45dcfc` (5820416 B, Sep 26 17:10): the
   build every fork-gate and EMinigame line in this design was read from. Nothing pinned it until rev. 2
   (segment_trace.py:409-432; o3 `fingerprint_extra` :1148-1159), and an engine rebuild auto-deploys over the shared
   install (4.13, 6.2, 6.3).
9. **The fight's tail.** After pass 49 (the phantom) e20 runs only the Byte[26]/Bit[230] handshake, then at stage 4
   `Wait(25)` and 107 (ip1557-1618); e13's stage-4 branch is `CloseWindow(6)`, `Wait(37)`, 108 (ip1332-1352). Neither
   moves Blank or Zidane, so the 49th prompt's slide (run in the phantom pass) is the last move before 107 (2.4.6).
   (`Map.Int16[36] > 0` would arm a TimeLeft of 30, ip744-755, but it is only ever zeroed -- e13 ip722, ip1010 -- and
   set to 1 only from >= 10, ip1515-1526: dead. TimeLeft is 50 on every arm.)
10. **`g.choose` presses outside the driver's rows.** It steers with `press down/up 4` until the published `selected`
    is the index, then `press confirm 4` (session.py:6717-6751) -- none of them a `press` row. Their seqs and steps are
    in the session's `steps.jsonl` (session.py:640-661, :7972-7975) and their accepted frames in `events.jsonl`
    (HarnessAgent.cs:545, :2427-2441), so the driver rows them without a session.py change (2.4.11).

---

## 1. Module layout

### 1.1 Files

| File (in `studies/story-trace/` unless a path is given) | | What it holds |
|---|---|---|
| `segment_regress.py` | edit, FIRST | The gate extended to O3: G15-G18 (1.4) and `--capture-o3`; G21, the driver's source pins, with `--rebaseline-source` (1.4, rev. 2); G19 joins at B3 (O4's driver and fake tests), G20 at C2 (O4's dry run). |
| `research/o3_regress_baseline.json` | new, FIRST | The captured O3 baseline (1.4), LF, `-text`, its `sources` (G21's pins) included. |
| `research/source_pins.json` | new, FIRST | G21's append-only re-baseline record (`[]` at A0), LF, `-text`. |
| `segment_trace.py` | edit (PART A) | S6: `side_ends_of`, `side_ends`, `end_places`; `Segment.cut` cuts at the side's end PLACES. |
| `o2_alexandria.py` | edit (PART A) | S6: `why_void`'s forbidden scan reads the side's end FIELDS. One line. |
| `segment_drive.py` | edit (PART A, B) | S6 (`_Drive` ends and end places per side; rule 2's V19 under `side_ends`); S7 (the Chanbara policy: `chanbara_of`, the recognizers, `j_bounds`, `raw_bounds`, `chanbara_judge`, `stray_answer`, rule 6b and its executor on the merged sample stream with its closing set, the `zone`/`prompt`/`observed` rows, V17/V18 on positive evidence, the FieldHUD guard, `drive`'s opt-in `witness`); S8 (page-once per window, the quiet windows from the first sample without, the DBTN refusal); S9 (the score/gil pages on two equal samples, the encore attribution over every Confirm of the visit, `choose`'s presses rowed). |
| `o4_castle.py` | new | `O4Segment(o3_prima_vista.O3Segment)`: the draft, O4's checks (LANDING, SWORD, VOID-ASYM (c) and (d)), the offline checks (O4-BUILD with the pins, O4-KEYS with the fight pins, O4-TEXT on blocks 2 and 3, strict, O4-CENSUS), the preflight extras (P-TEXT x2, P-RECOVERY, P-DONOR, P-SETTINGS, P-PAD, P-OVERRIDE, P-ENGINE, P-GATE), the in-game capabilities (+ P-DONOR-LOG, P-LAUNCH with the engine, P-PAD), the run's input witness (`input_witness`, its readers behind seams), `trace_summary` (end PLACES), `gate_verdict` (with its cause), the CLI. |
| `o4_forks.json` | new | The chain manifest (6.4): import, build, members, names, deploy, revert, side effects, `deployed: false`, `gate_witness: null`. |
| `o4_dryrun.py` | new | O4's synthetic sessions, units and offline mutants (section 8). |
| `o4_rehearse.py` | new | R-CHANBARA, R-CHANBARA-VOID, R-FULL (stock), F-SMOKE and R-GATE (after the deploy) for `tools/play.py` (section 7). |
| `.gitattributes` | edit | `studies/story-trace/research/o3_regress_baseline.json -text` and `.../research/source_pins.json -text` (A0); `studies/story-trace/o4_predictions*.json -text` (C1, before any freeze). |
| `tools/harness/fakegame.py` | edit (PART B) | H10 (the KEYON pair beat), H11 (the Chanbara visit beat, its pages' open and close times, its publication order), H12 (its fault knobs). Opt-in: no existing test's fake changes, and G21 pins the existing beat and input functions. |
| `ff9mapkit/tests/test_harness.py` | edit | The tests named in sections 1.2, 3 and 9. No existing test's body changes (G21). |
| `o3_prima_vista.py` | ONE edit (A2, rev. 2) | `SCOPE_LANG`'s uk clause read from the session's recorded P-TEXT lines (9, A2): story-o3 and every o3_dryrun session record the defect line, so G15-G17 prove the edit byte-neutral. |
| `PLAN.md` | edit (PART C) | The O4 section: "draft: rehearsals pending, deploy pending, freeze pending"; the block-2 rewrite's effect on O1/O3. |

`o1_opening.py`, `o1_dryrun.py`, `o2_dryrun.py`, `o2_rehearse.py`, `o3_dryrun.py`, `o3_rehearse.py`,
`tools/harness/session.py` and `tools/harness/channel.py` and every frozen predictions file are NOT edited (the 100
plan, item 8: no engine, agent or harness-verb change); `o3_prima_vista.py` only by the one A2 edit above. That they
keep their outputs is the gate. `o4_castle.py` imports `o3_prima_vista` and `o2_alexandria`: both are shared code for
O4 from now on.

### 1.2 The shared changes (each opt-in or behaviour-neutral for O1-O3)

**S6 -- per-side ends** (PART A; critique major #1, decision 4). Today one list serves both sides: `Segment.cut`
(segment_trace.py:677), `O2Segment.why_void` (o2_alexandria.py:1240), `_Drive.__init__` (segment_drive.py:808). With
`end_fields [153]` an F run reaching 31245 is off the route (rule 2, :1734 -> V11 by "game" on every F run); with
`[153, 31245]` a landing in REAL 153 reads "reached". And the drive uses one list for two jobs: raw field ids
(rule 1 `self.fid in self.ends`, `on_route`) and PLACES (`cut_at_end` in `scan()` :970 and `end_row()` :998 compare
FROZEN places: `place(31245) = 153`, so `[31245]` would never cut). The change separates the two:
```python
# segment_trace.py (pure)
def side_ends_of(pred) -> dict | None:
    """``pred["side_ends"]`` ({"S": [ids], "F": [ids]}), checked STRICT, or None (absent: one list for both sides).
    ValueError on: not a dict of exactly S and F; a side not a non-empty list of ints (a bool is no int); S not
    exactly the end fields (``end_fields`` / ``end_field``); an F id that is neither an end field with no member
    forking it nor a member whose donor is an end field; F's places not exactly the end fields."""
def side_ends(pred, side) -> list:      # side_ends_of(pred)[side], else end_fields or [end_field] (today's list)
def end_places(pred, side) -> list:     # sorted({place(f, members on F) for f in side_ends(pred, side)})
# Segment.cut:   kept, end = cut_at_end(rows, end_places(pred, side), members)
# O2Segment.why_void:   ends = ST.side_ends(pred, r["side"])        (forbidden_hits' end_fields)
# _Drive.__init__:   self.ends = list(end_fields) if end_fields is not None else ST.side_ends(pred, side)
#                    self.end_places = sorted({place(f, self.members) for f in self.ends})
# _Drive.scan / _Drive.end_row:   ST.cut_at_end(rows[arm:], self.end_places, self.members)
```
For O1-O3 (no `side_ends`; their end field is no member's donor) every list and every place is today's exactly.
**Rule 2's V19** (opt-in: only when `side_ends` is present): on F, a field off the route whose id is a DONOR of the
chain (`fid not in members and fid in set(members.values())`) raises `RouteVoid("the fork run entered REAL {fid},
where member({fid}) {m} was due: a Field() the chain did not retarget", v="V19", cell=[donor, sc], by="game")`;
anything else off the route stays `self.stray(...)` (V11). V19 is a FINDING (`rerun.stop_on`, 4.1).
On F the analysis's end cut still lands on a real-153 row (frozen place 153): the run carrying one is VOID by rule 2
first (V19), so no covered run holds one, and O4-LANDING (d) pins the covered runs' cut row to member(153) (5.3).
Tests (A1): `test_segment_side_ends_split_the_cut_and_the_drive` (pure: `side_ends_of`'s refusals, one each;
`end_places`; `Segment.cut` on synthetic F rows cuts at member(153)'s first row; `forbidden_hits` with F ends
[31245] hits a real-150 row and not a member(153) row; O3-shaped predictions read today's lists) and
`test_segment_drive_ends_per_side_on_the_fake` (F reaches "member(153)" and the end row names it; a landing in the
real end on F is V19, game; the same F landing WITHOUT `side_ends` is V11, today's). Both join `REQUIRED_TESTS`.

**S7 -- the Chanbara policy** (PART B; section 2.4). `chanbara_of(pred)` validates `pred["chanbara"]` STRICT before
anything is driven (as `movies_of`, segment_drive.py:403-474): None without the key, and then nothing below reads
it. With it: rule 6b (the fight zone's executor), the `zone`, `prompt`, `observed` and prompt `press` rows, V17 and
V18, `out()["zones"]`/`["prompts"]` and the same in `progress`. `drive()` gains one keyword, `witness=None` (rev. 2):
a callable the executor and, under the policy, the main loop poll for outside input (2.4.3 step 0; O4 passes
`o4_castle.input_witness`); O1-O3 never pass it and run no policy, so for them nothing reads it.

**S8 -- page-once and the quiet windows** (PART B; critique minor, decision 6; rev. 2 on the driver critique #1, #11).
Opt-in under the policy, in rule 7: (a) **the DBTN refusal** -- a page in the policy's cell whose `phrase_raw` holds
`[DBTN=` and is not the registered zone start is V17 with nothing pressed (game-observed: an `observed` row, 2.6), so
a prompt or a 111 in a form neither recognizer claims never falls to rule 7's Confirm; (b) **page-once, per window**
-- rule 7 presses while some listed window's own text is not held off: a window's text pressed within
`page_once_ticks` of that press's ack-read frame is held off (keyed on each window's text, `dialog.texts`, never on
the joined `st.text`, which changes whenever a second window joins or a first one closes); (c) **the quiet window** --
it OPENS at the first sample without any window holding a `quiet` marker after such a window was pressed (until then
page-once re-presses it: a first press dropped in the window's opening, 0.3 #1, is pressed again), and while it is
open nothing is pressed until a choice is published; a page in between is V17 (game-observed, fail-closed); no choice
within `quiet_cap_s` of its opening is V14 (game). Without the policy rule 7 is O3's exactly.

**S9 -- the score and gil pages and the encore attribution** (PART B; rev. 2 on the driver critique #10 and the claim
critique #8). Opt-in under the policy: the first page in the policy's cell after the zone that holds "nobles
watching" must equal `score_page` in TWO consecutive samples (0.3 #6); the first page after the encore rule's answer
is judged by what it is (2.4.12): `gil_page` (two samples) passes, a gil page with another number goes to
`chanbara_judge` (V18 when the play is proven, else V17), a replay page (110/109) or a second 127 goes to
`stray_answer` (V17 when any Confirm of the driver's own -- page, prompt or `choose`'s, each a row with its `seq` --
landed on 127 other than the answer's own on a cursor at No; else V2, game), anything else is V17 (game-observed). A
once-VOID (V2) of the encore rule goes through `stray_answer` the same way. `answer` rows `choose`'s own presses
(0.3 #10) under the policy only.

### 1.3 `o4_castle.py`

`O4Segment(o3_prima_vista.O3Segment)`:
- `tag = "O4"`, `predictions = HERE / "o4_predictions_v1.json"`, `manifest = HERE / "o4_forks.json"`,
  `session_file = "o4_session.json"`, `report_file = "o4_report.txt"`, `chain_dir = C:\gd\_ns_playtest\o4\fork`,
  `build_dir = C:\gd\_ns_playtest\o4\build`, **`accept_us_build = False`**, `recovery = 4600`,
  **`end_session_warps = True`** (S5: a last run stopped mid-fight must not leave the game there).
- `core_ids = ("START", "LADDER", "CHAIN", "RESIDUE", "WRITES", "NULL", "STABLE", "LANDING", "SWORD", "MASKED",
  "STATE", "JOIN")`; `titles` gives every check its O4 text.

**Inherited unchanged:** from O2Segment `current`, `read_session` (with S6's `why_void`), `_run_log`,
`forbidden_check`, `span_check` (LADDER, CHAIN), `residue_check`, `null_check`/`stable_check`/`join_check`,
`masked_check`, `history`/`suppressed`/`state_check`; from O3Segment `why_void` (A-START on 64's error path, A-NOEND,
`cut_row`), `start_check` (data-driven: three residue rows, `start_first`, `start_music`), `fingerprint_extra`'s
settings and battle data.

**Overridden:**
- `draft()` -- section 4; members and names from `campaign.toml` (`chain_from_campaign`: exactly the twenty donors,
  member(64)/(150)/(153) derived and printed).
- `freeze()` -- `chanbara_of(draft)` passes, the policy is `"fast"` with no `pace` and no `stop_after`, the
  `side_ends` pass `side_ends_of`, `battles` is empty, `engine` holds the live sha (6.2 P-ENGINE); then the base's
  (LF, sorted keys, never over a file).
- `drive` -- `segment_drive.drive(...)` as the base calls it, plus `witness=input_witness(g)` (2.4.3; rev. 2).
- `offline_extra` -- `[text_check (blocks 2 and 3, strict), census_check]` after the base's BUILD (with the pins) and
  KEYS.
- `build_check` -- the base's (every language its own donor's) + the fork-gate pins (6.1).
- `keys_check` -- O2's machinery on a filtered copy (ladder, chain, writes without the `:=var` key, `forbidden_sites`
  + `error_path` + `dead`, `start_first`); then the `:=var` key (ip338), `start_music`'s single writes key, and the
  fight pins (6.1).
- `census_check` -- O4's own `store_census` with function-level `inert` classes (0.2 #4); O3's function is not touched.
- `preflight_extra`, `capabilities`, `fingerprint_extra` -- 6.2, 6.3 (+ `engine`, `text3`).
- `all_run_checks` -- `[forbidden_check, void_asym_check]` with O4's `void_asym_check` (O2's (a), (b); (c) and (d)).
- `writes_check` -- EXACT over writes + chain + LADDER (O3's reads writes + chain).
- `landing_check`, `sword_check` -- 5.3.
- `core_checks` -- `core_ids` order.
- `report_extra` -- 5.4 (R-GATE from the session's recorded P-GATE detail; the language line from its recorded P-TEXT
  lines). `handle` -- `--rehearsal-report` reads `o4_rehearsal.json` (and prints R-GATE's verdict and cause).

**Module functions (pure unless named a reader):** `chain_from_campaign`, `store_census` (O4's),
`instanced_at(idx, entrance_branch)` (the 325 branch's InitObject/InitRegion/InitCode set -- O4-CENSUS proves the
`inert` claim with it), `xinput_slots(reader)` and `p_pad(samples)` (P-PAD's reader and verdict, the ctypes reader a
seam), `input_witness(g, *, pads=None, keys=None, focus=None)` (the zone's outside-input witness, 2.4.3: three reader
seams, the ctypes ones the defaults), `strict_text(lines)` (O4-TEXT's and P-TEXT's verdict over `text_rule`'s lines,
6.1), `p_override(fp, pinned)`, `p_engine(live, pinned)`, `p_gate(manifest, live_engine, settings)`,
`gate_verdict(runs) -> {"verdict", "cause", ...}`, `trace_summary(...)` (cut at `end_places`), `rehearsal_report(run_dir)`,
`run(g)`, `main(argv)`.

### 1.4 The regression gate extended to O3 (`segment_regress.py`)

The implementer extends the gate and captures its O3 baseline FIRST (A0), at the design commit, before any other
code change. The O3 items import only O3's modules (`o3_prima_vista`, `o3_dryrun`), inside their functions.

`O3S = C:\gd\Dream-World-IX\.harness-runs\20261001-095552-story-o3`, `V1_O3 = HERE / "o3_predictions_v1.json"`.

| Item | Check |
|---|---|
| G0'' | `py studies/story-trace/segment_regress.py --capture-o3` writes `research/o3_regress_baseline.json` (LF, `-text`): the full `(checks, report)` of O3S with V1_O3; every `o3_dryrun` session case's `(checks, report)` and "predictions-changed"'s; every unit's `(name, ok, detail)` (o3_dryrun's units and offline mutants, the skip-A/B units included); `O3.offline_check(V1_O3)`; the tests G13 collects; the HEAD and V1_O3's sha; and (rev. 2, the claim critique #7) `sources` -- the sha256 of `ast.dump(node, include_attributes=False)` of every test function G7, G12 and G13 collect (`ff9mapkit/tests/test_harness.py`) and of fakegame.py's existing beat and input functions (`FakeGame._execute`, `_block`, `_schedule`, `_extend`, `_is_held`, `_advance_clock`, `_hold_frame`, `_frame_steps`, `_menu_step`, `_publish`, `say`, `offer`, `scene`, `_next_beat`, `_choice_cursor`, `_movie_over`, `_end_scene`, `_step_scene`, `_scene_press`, and the module's `_control`), each by its qualified name. It refuses an existing file, and refuses to write unless G15-G18's baseline-free halves pass. It first takes TWO readings and refuses when they differ (a temporary path, a clock or a random in an output): each temporary root the replica makes is replaced by `<tmp>` before comparing, and anything still differing is named, never excluded silently. |
| G15 | `O3.analyse(O3S, pred_path=V1_O3)`: the report equals `(O3S/"o3_report.txt").read_text(encoding="utf-8")` exactly, and the baseline's; the checks are the baseline's; PROVEN with 17 checks, all True. |
| G16 | `py studies/story-trace/o3_prima_vista.py --analyse O3S --predictions V1_O3` exits 0 and prints that report (plus print's newline). |
| G17 | Every `o3_dryrun` session case's `(checks, report)` byte-equal to the baseline's, every unit's `(name, ok, detail)` too, and `o3_dryrun.run_cases(V1_O3)` returns 0 printing "102/102 cases as registered" (the count computed from the replica: its sessions plus its units). The gate replicates `run_cases`'s loop step for step (`pred/`, `sessions/`, `s0`.. in creation order, the units in their order on the same temporary root), as G10 does O2's. G17 is O3's VOID-path baseline: story-o3 holds six covered runs. |
| G18 | `O3.offline_check(V1_O3)` equals the baseline's `[(ok, what, detail)]`: 6 checks, all PASS (reads O1's build and the install, read-only). |
| G19 (from B3) | `pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o4_ or fake_chanbara or fake_keyon"` from `ff9mapkit/`: all passed, 0 failed, 0 skipped, 0 errors, and every name in `REQUIRED_TESTS_O4` among them. No baseline: the list is the floor. Joins in the commit that adds the tests, never earlier. |
| G20 (from C2) | `o4_dryrun.run_cases` on the frozen O4 predictions once they exist, else the draft: returns 0 printing "N/N cases as registered", N at least `O4_DRYRUN_FLOOR`. Without the frozen file the draft reads the O4 build's `campaign.toml`: "not run" (exit 2) where it is absent. |
| G21 (from A0; rev. 2) | THE DRIVER'S SOURCE PINS: every name in the baseline's `sources` still exists and its current sha equals the baseline's -- or, when `research/source_pins.json` re-baselines it, its LATEST row's `new`. A row is `{"name", "old", "new", "reason", "head"}`, appended only by `py studies/story-trace/segment_regress.py --rebaseline-source NAME --reason TEXT` (it refuses an empty reason, a name not pinned, and an `old` that is not the pin in force; the commit that changes the source carries the row). Comments and whitespace do not count (the AST dump); any code edit does, and a renamed or deleted pinned test FAILS. So an O1-O3 driver test adapted to a changed rule -- which G7/G12/G13 alone would pass, since they pin only names -- fails here until it is re-baselined by name with its reason. |

O1's G1-G7, O2's G8-G12 and O3's G13-G14 stay as they are. `_missing()` gains the O3 inputs (O3S's session and
report, V1_O3, the baseline, `source_pins.json`) and, for G20, O4's frozen file or campaign.toml. Tests O4 adds whose names match G7's
selection (`test_segment_*`) join `REQUIRED_TESTS`; `test_o3_drive_pages_a_prompt_without_the_chanbara_policy` joins
`REQUIRED_TESTS_O3` (G13's selection); every `test_o4_*`, `test_fake_chanbara_*` and `test_fake_keyon_*` joins
`REQUIRED_TESTS_O4`. O4's rehearsal tests are named `test_o4_rehearsal_*` -- not "rehearse", so G12 does not run them
a second time.

---

## 2. The drive

### 2.1 The model (keys the driver reads; the rest of the predictions is the analysis's)
- **`table: []`.** No control on the route: 64's `EnableMove` (e0 t0 ip936) sits behind `Map.Bit[158] == 1`, set only by
  e16 t0 at entrances 315/322 (mapvar is cleared at every field start, EventEngine.cs:625-626); 150's e2 t0 grants
  control only at entrance 5; every region exit's tag 2 opens `SET(SYSVAR[2]) JMP_IF RET()` (64 e11 t2 ip30-37, 150 e18
  t2 ip30-37). So control anywhere is V4.
- **`battles: []`**: any battle is V10 (no `Battle` op on the route: the opcode inventory of 64@100 and 150@325).
- **`stop_pages`**: `[{"match": "Env Play()", "why": "64's and 150's ambient error window ('Error Env Play()  Slot=n':
  64 e0 t0 ip835/869 window 3, 150 e0 t0 ip999/1033 window 56): Byte[13]/[14] arrived as 2 or 9"}, {"match": "Set
  Scenario Counter()", "why": "150's debug window 55 (e3 t1 ip1915, behind SC > 1190 at ip1884): waits for
  Start/Select"}]`.
- **`choices`**: the encore rule and O1's net (2.5). **`naming: []`.** No `movies` (FMV004 is past the end).
- **`route: [64, 150]`, `visits: [64, 150]`, `end_fields: [153]`, `side_ends: {"S": [153], "F": [member(153)]}`**
  (S6). **`forbidden`**: O2's `off_route` pattern only (4.8). **`beats: ["sword", "encore"]`** (4.11).
- **`chanbara`**: the policy (2.4, its draft numbers 4.10).

### 2.2 The driver loop for O4 (O3's rules in O3's order; the opt-in additions marked)
Every poll reads `st`, `sc` and `donor = place(fid, members)` as O3's does.
1. **End** (`fid in self.ends`: real 153 on S, member(153) on F): the end state, the last scan, the end row
   (`budget.end_row_s`: the first trace row in an end PLACE, S6), `reached`. Then the stall watchdog, unchanged.
- 1b (battles), 9 (a load), unchanged.
2. **Route**: unchanged, but under `side_ends` a real DONOR field on F is **V19** (S6).
3. **Visit**: 64 -> 150, unchanged.
4. Naming: V10. 5. A tutorial or a battle: V10. Unchanged.
6. **A choice**: O1's readiness hold, then the rules (2.5). (S9, opt-in) the first frame each choice was published in
   this visit is kept (`self.choice_first`), and a once-VOID of the rule whose `match` is the policy's `encore_match`
   goes through `stray_answer` (2.4.11): V17 (driver) or V2 (game). Under the policy `answer` brackets `g.choose(1)`
   with `g.channel.seq` and rows its presses afterwards (`why` "choose", 2.4.11).
- **6b (new, opt-in: `chanbara`) -- the fight zone.** A published `phrase_raw` line that is a PROMPT (`prompt_dbtn`)
  or the ZONE START (`is_zone_start`: 111), in the policy's cell (place 64, published SC 1155, control off): the
  executor (2.4) owns the loop until the zone ends; then `continue`. A prompt-shaped line anywhere else: V17 "a prompt
  outside the policy's cell", nothing pressed (game-observed). BEFORE rule 7, so a prompt is never paged (rule 7
  presses Confirm on any page, segment_drive.py:1793-1813, and Confirm is the Cross bit: a wrong key on 7 of 8
  prompts).
7. **A page** (dialog open, text, control off): the stop pages first (V5, nothing pressed: O3's). Then, opt-in under
   the policy: (S8 a) the DBTN refusal -- a page in the cell whose `phrase_raw` holds `[DBTN=` and is not the
   registered zone start: V17, nothing pressed (game-observed; rev. 2, the driver critique #11); (S9) the first page of
   the cell after the zone holding "nobles watching" must equal `score_page` in two consecutive samples (else the run
   stops, 2.4.12; equal: the beat `sword` is set); the first page after the encore answer is judged by what it is
   (2.4.12); (S8 b, c) page-once per window and the quiet window. Then O1's press (`press("confirm", 3)`, a `press` row
   -- under the policy it also carries `seq`, `ack_frame` and the window texts it pressed -- and
   `wait_frames(frames_for_ticks(4))`).
8. **Control held** (settled): V4. Unchanged.
9. Otherwise wait. Unchanged.

`out()` and `progress` gain `"zones"` and `"prompts"` (the zone and prompt rows) only with the policy, so O1-O3's
outcomes keep their keys.

### 2.3 Every research beat, and what handles it
The beats are `o4_research.json`'s `reconciled.route.beats`, with the critic's corrections.

| # | Field | Beat | Handled by |
|---|---|---|---|
| 1 | 70 | the warp: residue SC bytes 0 (0 -> 131), 1 (0 -> 4), FieldEntrance byte 2 (0 -> 100) | `start_run` (O2's raw warp) |
| 2 | 64 | Main_Init at 100 (SWITCHEX ip236 default L402): the ambient four, ip408 Map.Byte[24] := 1, ip416 Bit[3815] := 0, ip425 Byte[475] := 0, InitCode 4/3, InitObject 5, 6, 13, 20, ip475 Byte[8] := 125 | nothing (WRITES) |
| 3 | 64 | stage 1, the scripted walk-in (1.83 s measured, story-o3 run 6) | rule 9 |
| 4 | 64 | 105 (e20 ip303) and 106 (e13 ip816), both `[INCS][TIME=-1]`: the INCS/250 gate (e13 ip825-859), then the KEYON(Confirm 0x20000 \| Special 0x80000) loop (ip865-885) closes both (ip888/891); an edge before the loop is lost | rule 7 with page-once: a Confirm every >= `page_once_ticks` while a window's text stays listed, each window keyed on its own text (`[TIME=-1]` inhibits UI paging, DialogBoxSymbols.cs:811-826; only the loop's edge closes them) |
| 5 | 64 | 111, the tutorial (`WindowSync(6,0,111)` e13 ip900; an ordinary page; eight DBTN tags) | rule 6b: the zone start (a Confirm; again only if 111 is still listed `page_once_ticks` later -- a first press dropped in its opening, 0.3 #1; then quiet) |
| 6 | 64 | THE SWORD FIGHT (stage 3): e20 t1 ip440-1554, e3 t1 ip23-509 | rule 6b's executor (2.4) |
| 7 | 64 | 107 (e20 ip1618 after Wait(25)) and 108 (e13 ip1352 after Wait(37)); the INCS/250 gate (ip1361-1395); KEYON ip1404 | the zone END (6b returns); then rule 7 with page-once, as 4 |
| 8 | 64 | stage 5, the walk-off | rule 9 |
| 9 | 64 | stage 6: ip338 Byte[475] := score; 122 (ip375), Wait(5), 123 (ip384); ip390 Bit[3815] := 1; Wait(10) | rule 7: 122 checked against `score_page` in two consecutive samples (S9), then pressed (page-once); 123 pressed (page-once: again while still listed -- its first press usually lands in its opening, 0.3 #1), and from the first sample without it the QUIET window until the choice (S8) |
| 10 | 64 | choice 127 (`WindowSync(5,0,127)` ip462; `[PCHC=2,1]`, cursor on Yes = 0) | rule 6: the encore rule picks "No" (absolute 1) by `g.choose(1)`, once |
| 11 | 64 | 128 (ip531, `[NUMB=1]` = Int16[50] = 10000 at score 100), AddGi ip537 | rule 7: 128 checked against `gil_page` in two consecutive samples (S9, 2.4.12), then pressed (page-once) |
| 12 | 64 | stage 9: ip331 Byte[8] := 0, PreloadField(5,150), FadeFilter, Wait(65), ip528 Int16[2] := 325, `Field(150)` ip536 (member(150) on F) | nothing; rule 3 (visit 150) |
| 13 | 150 | Main_Init at 325 (SWITCHEX ip242 -> L248): InitObject 2, 3, 5, 6, 9, 4, InitRegion 18, InitCode 17, ip331 Byte[8] := 25 | nothing (WRITES) |
| 14 | 150 | stage 0: 85-88 `[TIME=20]`, 89 `[TIME=60]` (self-closing), 130 ticks of waits, the fade-in | rule 7 (inert Confirms, recorded `timed`) |
| 15 | 150 | pages 90 (e3 ip444), 91 (e2 ip404), 92 (e2 ip435 + WaitWindow), 93-97 (e3, each + WaitWindow) | rule 7 |
| 16 | 150 | 98 (e3 ip794) and 99 (e2 ip480), both `[INCS][TIME=-1]`: the INCS/250 gate (ip495-529), KEYON ip538 closes both (ip558/561) | rule 7 with page-once, as 4 |
| 17 | 150 | pages 100, 102 (then the package toss), 103, 104, 106 | rule 7 |
| 18 | 150 | stage 10 (e3 t1 L878): UInt16[21] := 1 ip1136, Byte[303] := 0 / ++ ip1221/1255, Byte[4] := 0 ip1652/1667, Byte[17] := 0, Byte[18] := 1, Wait(90), **SC := 1190 ip1966**, Byte[8] := 75 ip1974, Int16[2] := 325 ip2161, `Field(153)` ip2169 | nothing (LADDER, WRITES, CHAIN) |
| 19 | 153 | THE END: 153 e0 t0 ip22 (real 153 on S, member(153) on F) | rule 1 (per side) and its end row |
| 20-21 | 153 | the first control grant, choice 128 | past the end (O5) |

### 2.4 The Chanbara policy -- rule 6b's executor (`_Drive.chanbara_zone(st)`)

#### 2.4.1 What it watches
- **The published dialog block**: the raw `dialog.phrase_raw` list (`Dialog.Phrase`, the source with its tags;
  HarnessAgent.cs:1650-1656) and `dialog.texts` -- read off `st.raw`, NOT `State.raw_texts`/`texts`, which drop empty
  lines (channel.py:541-552) and so lose the alignment of the two lists. Published every 2nd frame (HarnessAgent.cs
  :241, :1502); a script and the agent read one list (`MesWinActive` = `CheckDialogShowing`, DialogManager.cs:176-182).
- **The MERGED sample stream** (rev. 2; the driver critique #4, #5, the claim critique #2): the executor's own reads
  plus the ring's -- `g.states_since(last_frame)` after every press returns, before every judgment, and at least every
  `ring_every_s` (2 s; the ring keeps ~10 s, 0.3 #4) -- deduplicated on frame, in frame order. The `_await_ack` polls a
  blocking press makes are in it. Every frame-valued fact below (`prev`, `seen`, `last_listed`, `gone`, 111's
  `last_with` / `first_without`, the read gaps, the slides' samples) is read off this stream, never off the executor's
  own reads alone. A kept sample is reduced to `{frame, read_at, ui_state, control, dialogs: [(phrase_raw, text)],
  choice, x_player, x_blank}` (Blank: published object sid 20).
- **`prompt_dbtn(line)`** (pure): the line holds EXACTLY ONE `[DBTN=X]` with X one of LEFT, RIGHT, UP, DOWN, CROSS,
  CIRCLE, TRIANGLE, SQUARE, and holds `Press` and `[TIME=-1]` -> X; else None. Rendered `texts` are never read for
  it: the glyph renders to nothing (O1 measured `[CBTN]` so: story-o1 driver.log:28), so all eight read "Press  !".
  111 (eight DBTN tags) is no prompt; 150's window 55 (two DBTNs, no "Press") is none either.
- **`is_zone_start(lines, pol)`**: a line holding `pol["zone_start"]["match"]` ("To follow Blank") with exactly
  `pol["zone_start"]["dbtns"]` (8) DBTN tags. **`is_zone_end(texts, pol)`**: a rendered text holding one of
  `pol["zone_end"]` ("We shall finish this later!", "Come back here!").
- **Where**: the policy's cell only -- place `donor` (64) and published SC `sc` (1155), control off.

#### 2.4.2 The phases
- **Z0, the zone start (111).** A Confirm (a `press` row, `why` "page", with its `seq`; 111 joins `pages`). Page-once:
  while 111 is listed, no second Confirm until `page_once_ticks` past that press's ack-read frame -- a press dropped
  in 111's opening (0.3 #1) leaves it listed after the hold-off, and only then is it pressed again (a press decided
  while 111 is listed lands before T0, 2.4.11). Recorded off the MERGED stream (2.4.1; rev. 2, the driver critique
  #5): `start_page = {"seen_frame", "presses": [seq], "last_with_frame", "first_without_frame"}` -- the first sample
  without 111 is the driver's T0 (the engine's T0, the tick e13's WindowSync wait sees window 6 gone, lies between
  them). The rate is NOT required here (rev. 2, the driver critique #6): `rate(require=True)` can block 2-10 s
  (session.py:1351-1419), and in a launch's first run at ~31 fps the dialog pairs before 111 (105/106, ~1.5-2 s, the
  first second of a visit quarantined, tickrate.py:94-109) can fall short of MIN_PAIRS -- the executor would miss T0
  and prompt 1. `g.rate()` is read without blocking; each prompt row records its own, and the judge requires every
  row's rate measured (2.4.8).
- **Z1, quiet.** Nothing is pressed until the first prompt (armed at T0+12, first polled at T0+13: e13 Wait(10) ip906
  at T0+1, the Byte[26]/Bit[230] sync at T0+11, e2 `Byte[24] := 3` ip134 at T0+12 and e20's arm in that tick).
  Fail-closed: any other dialog or a choice is V17 (game-observed), nothing pressed; no prompt within `first_prompt_s`
  is V14 (game).
- **Z2, the fight**: the tight loop (2.4.3) until a zone-end text is published (107 or 108).
- **Z3, the close**: the ring merged a last time, the rows completed (2.4.6: the events joined, the j and raw bounds,
  each instance's evidence, the read gaps, the slides), the zone judged (`chanbara_judge`, 2.4.8); a fault ends the run
  (2.4.9). `self.since` is reset, and the main loop resumes (rule 7 pages 107/108).
- Entered on a PROMPT instead of 111 (only if 111 closed with no press of the driver's: under S8's DBTN refusal an
  unrecognized 111 is already V17): the zone starts at Z2 with `start_page` None, and O4-SWORD (f) reads that run's
  rows from the first prompt's `prev_frame`.

#### 2.4.3 The tight loop (Z1 and Z2)
Every `poll_s` (5 ms; a read and parse is ~0.2 ms): ONE `g.state` read (it feeds the clock and the ring; it can wait
up to 1 s on a locked file, channel.py:1023-1075, and the executor is blind while a press blocks -- which is why every
fact is read off the MERGED stream, 2.4.1). Nothing else may stall it: no forbidden scan, no `observe` call (the
recorder sees the zone's first and last sample only), no `wait_frames`, no `rate(require=True)` (a plain `g.rate()`
is a read of the clock). Per sample, in this order:
0. **The input witness** (rev. 2, the claim critique #4): every `input_every_s` (50 ms) the `witness` (S7) is read --
   XInput slots 0-3 through P-PAD's reader (a slot found disconnected is re-read at most once a second: the empty slot
   is the slow call), and the keyboard and mouse buttons (`GetAsyncKeyState` over virtual keys 0x01-0xFE) only while
   the game window has focus (`GetForegroundWindow`'s process is the game's: the keyboard needs focus,
   HonoInputManager.cs:561; the pad does not, `AlwaysCaptureGamepad = 1`, 0.2 #5). Non-neutral: a pad button bit, a
   trigger >= 30, a thumb axis past 3277 (P-PAD's thresholds), or any key down while focused -- F1, the booster, among
   them (0.3 #7). The first non-neutral reading: an `input` entry on the zone row (`{"t", "frame", "what"}`), then V13
   (instrument) "outside input during the fight: <what>", nothing more pressed. The harness's own presses are
   injected below the OS (`HarnessAgent.IsHeld`) and never read here. Under the policy the main loop polls the same
   witness, at the same interval between its own blocking calls, for the WHOLE run (logged as `input` rows): a human
   Confirm on 127, or a Start that pauses 150, cannot then read as the game's V2 or V14 -- it is V13 wherever it falls.
1. Past the run's deadline: `HarnessError("the run's budget ran out in the fight")` (V13).
2. **The UI** (rev. 2, the driver critique #9): `ui_state` not "FieldHUD": V13 "the fight left FieldHUD
   (<ui_state>)", nothing pressed -- a main menu opened on Triangle would hold the prompt to its timeout and read as a
   lost press (0.3 #5).
3. The field id left the visit's field: rule 2's verdict (V19 or V11, game); impossible by the bytes.
4. Control held for `settle_s` of consecutive samples: V4 (game).
5. A choice published: V17 (game-observed, fail-closed), nothing pressed.
6. A zone-end text: Z3.
7. Lines that are neither a prompt nor 111 (closing): V17 "a dialog the prompt rule does not claim in the fight zone:
   <text>" (game-observed), nothing pressed -- never rule 7 (critique minor #4).
8. **Instances** (rev. 2, the driver critique #2, the claim critique #3). The tracker keeps `cur` (the newest
   instance) and `closing` (DBTN -> instance: earlier instances still listed when their successor opened). For the
   current merged sample, with D the set of DBTNs it lists:
   - Each `closing` entry: listed -> its `last_listed_frame` is this frame; not listed -> its `gone_frame` (if unset) is
     this frame and it leaves `closing`. A closing DBTN is never a new instance: prompts never repeat back to back (e20
     ip681), and an A-B-A return comes a pass (>= ~28 ticks) later, long after a tween of 0.09 s plus a frame.
   - D' = D minus `closing`'s DBTNs. cur.dbtn in D -> `cur.last_listed_frame` is this frame; not in D -> `cur.gone_frame`
     (if unset) is this frame. D empty -> `cur.gap = True` (a prompt-free sample; recorded, judged by no rule).
   - A DBTN Y in D' that is not cur.dbtn: a NEW instance. Two at once: V17 "a read gap hid an instance" (driver).
     Before it opens, the switch is judged on `cur`:
     - `cur` has no press: stop -- the judge (V17: the instance ended before the driver pressed);
     - `n` would pass `prompts` (49): stop -- the judge (V18: more prompts than the bytes arm, e20 ip710);
     - `stop_after` reached (R-CHANBARA-VOID only): V17 "the rehearsal's stop after instance N".
     Then, if cur.dbtn is in D, `closing[cur.dbtn] = cur`; instance n+1 opens: `seen_frame` this frame, `prev_frame`
     the last merged sample's frame not listing Y (`prev_kind` "none" or "dbtn"), `published` (this sample's texts and
     phrase_raw lines), `x_seen` and `x_prev` (`{"player", "blank"}` at this sample and at the prev sample), and its
     `prompt` row is appended.
   There is NO live gap rule, under either policy (rev. 2): a missing prompt-free sample is the driver's sampling, not
   evidence about the game (the driver critique #4, the claim critique #2), and under the paced policy prompts overlap
   by design (0.2 #2). The lost press below is the live test for a press the game did not take.
9. **The press.** `cur` unpressed and due (fast: at once; paced: 2.4.10): `g.press(pol["buttons"][dbtn],
   pol["press_frames"])` (blocks for the ack); then `seq = g.channel.seq`; one more read `st2 = g.state` gives
   `ack_frame = st2.frame`; the ring is merged (2.4.1); `rate = g.rate()`; `excess = g._clock.excess_ticks(prev_frame,
   ack_frame, rate)` (a hitch caught up inside the window, tickrate.py:652-673). A `press` row (`why` "prompt",
   `button`, `seq`, `ack_frame`, `pre` the sample decided on, `post` None, `near` []). A refused or failed press: V13
   (instrument), the row kept.
10. **The lost press and the unobserved end** (live; rev. 2), for every pressed instance, `cur` or closing, with `mark
    = ack_frame + rate.frames_for_ticks(gone_ticks)` (`ack_frame` is past the down frame, so `mark` is >= down +
    gone_ticks): a merged sample listing it at or past `mark` -- POSITIVE evidence the game did not take the press --
    or its first sample without it past `mark` with none listing it at or past `mark` -- its end UNOBSERVED (a read
    gap straddles the mark): stop -- the judge (2.4.8 decides on the exact down frames: V18 only on the positive case
    with a proper press; V17 otherwise).
11. **The zone stall**: no new instance and no zone end for `zone_stall_s`: V14 (game).
12. `time.sleep(poll_s)`.
The read gaps (the longest step between consecutive merged samples, in frames, ticks and seconds) are computed at Z3
off the merged stream (2.4.6), never live.

#### 2.4.4 The button map (strict; `chanbara_of`)
| DBTN | press | Control | KEYON bit (e3 t1) | wrong code |
|---|---|---|---|---|
| LEFT | `left` | Left | 0x80 (ip34) | 11 |
| RIGHT | `right` | Right | 0x20 (ip81) | 10 |
| TRIANGLE | `menu` | Menu: 0x1000000 \| Triangle 0x1000 | 0x1000 (ip128) | 10 |
| DOWN | `down` | Down | 0x40 (ip175) | 11 |
| CROSS | `confirm` | Confirm: 0x20000 \| Cross 0x4000 | 0x4000 (ip222) | 10 |
| UP | `up` | Up | 0x10 (ip269) | 11 |
| CIRCLE | `cancel` | Cancel: 0x10000 \| Circle 0x2000 | 0x2000 (ip316) | 11 |
| SQUARE | `special` | Special: 0x80000 \| Square 0x8000 | 0x8000 (ip363) | 11 |

`chanbara_of` refuses any map but exactly this one (DBTN_CONTROL, a module constant), naming the cause: `circle`
(and `x`, `a`) is `Control.Confirm`, the Cross bit (HarnessAgent.cs:1434); `start`/`pause` is Start, which 64 e3 t1
ip412 reads as a LEVEL (`B_KEY(8)`): held, a miss every poll; an alias of a direction (`north`...) is refused to keep
one spelling. `press_frames` must be an int 1-4 (a tap: one edge per tick, ETb.cs:50-56; under the fast policy the
next instance is >= ~8 ticks away, 0.2 #2). Physical bits by 0.2 #6; directions are set straight by ProcessInput.

#### 2.4.5 One press per instance
Exactly one `press <name> <press_frames>` per instance, blocking for its ack. Never a re-press: a re-press of a lost
press can land after the next arm, where it is a certain miss (prompts never repeat, e20 ip681). Never two buttons,
nothing between instances, nothing on the zone's other dialogs.

#### 2.4.6 The rows
- **`prompt`** (one per instance): `{"k": "prompt", "n", "dbtn", "button", "field", "donor", "visit", "sc",
  "prev_frame", "prev_kind", "seen_frame", "seen_t", "published": {"texts", "phrase_raw"}, "x_prev": {"player",
  "blank"}, "x_seen": {...}, "seq", "pressed_t", "ack_frame", "ack_t", "accepted_frame", "down_frame",
  "last_listed_frame", "gone_frame", "gone_kind", "evidence", "read_gap", "rate", "excess", "j_lo", "j_hi", "regime",
  "slide", "v", "why"}`. `accepted_frame` is the `frame` of events.jsonl's `accepted` event for `seq` (0.2 #12), joined
  at Z3 (`g.channel.events()`, one read); `down_frame` = accepted + 1; both None when the event is missing (a fault:
  2.4.8). `regime` is `rate.fps` rounded ("60", "31", or the number). Rev. 2 (the driver critique #4, the claim
  critique #2): `last_listed_frame` is the last merged sample listing the window (after its successor opened too:
  `closing`), `gone_frame` the first without it; `evidence` is what the merged stream PROVES about the press, against
  `mark = down_frame + rate.frames_for_ticks(gone_ticks)`, in this order: `"before"` (a sample after `seen_frame` and
  at or before `down_frame` already lacks it: it left before the press could land); `"lingered"` (a sample lists it at
  or past `mark`: the game read no key); `"closed"` (a sample lists it at or after `down_frame` -- it was still up
  when the press could land -- and the first sample without it lies at or before `mark`: the game read A key; e3
  closes the window on a hit and on a wrong key alike, ip459/484, so only the slide or the score tells which);
  else `"unobserved"` (a read gap straddles `down_frame` or `mark`: the merged stream cannot say when the window
  left). `read_gap` is the longest step between consecutive merged samples from `seen_frame` to the next instance's
  `seen_frame` (or the zone end), in frames and in `ticks_most`.
- **`slide`** (LEFT/RIGHT only; critique minor #8; rev. 2, the driver critique #3, the claim critique #1): a LEFT or
  RIGHT hit on prompt n slides Blank (e20 t1 ip918-1063 / ip1066-1211) and Zidane (e13 t11 ip1617-1765 /
  ip1768-1916) in pass n's reaction -- the pass that arms prompt n+1 at S' -- Blank -60 a tick from S'+1 to -300 /
  +300 after S'+5, Zidane a tick later, done after S'+6 (0.3 #3); a miss (10/11) moves neither. The two samples
  bracket that slide and no other: BASE = instance n+1's `prev` sample (`x_prev`: the last merged sample not listing
  prompt n+1 -- whatever else it lists, its state precedes tick S', so neither prompt n's slide nor anything after has
  begun), END = instance n+2's `prev` sample (its state precedes S'' = prompt n+2's arm, where prompt n+1's own slide
  would begin). Each counts only when it lies at least 7 sure ticks after the previous instance's `seen_frame`
  (`rate.ticks_sure(prev - seen_prev) >= 7`: the earlier slide, done after its arm + 6, plus a jitter tick); else that
  instance's slide is `"unmeasured"`. The tail: prompts 48 and 49 slide in the arms of 49 and of the phantom pass,
  which publishes nothing (0.3 #9), so they are measured JOINTLY from instance 49's `prev` sample to the zone end's
  first sample (107 listed; nothing moves either body between the phantom pass and 107, 0.3 #9), `want` the sum of
  their L/R wants, the one joint result logged on both rows -- `"unmeasured"` when both are L/R with opposite wants
  (a pair of hits and a pair of misses then read alike). `{"want": -300 | 300 | sum, "base": frame, "end": frame,
  "dx_player", "dx_blank", "ok": true | false | "unmeasured"}`, `ok` true when both dx are `want` within 1 unit.
  The rev. 1 baseline -- x at the next instance's `x_seen` -- reads -240 about half the time at ~31 fps (the first
  sample listing a prompt already shows a step), and its end could hold the next slide's first steps: both critics'
  failure, the mutant of the dry run's slides unit (8).
- **`zone`** (one per zone): `{"k": "zone", "field", "donor", "visit", "sc", "policy", "start_page", "first_prompt",
  "end": {"frame", "text"}, "instances", "presses", "samples", "max_read_gap": {"frames", "ticks", "s"}, "input",
  "rate", "raw": [lo, hi], "slides": {"ok", "unmeasured", "not_ok"}, "judge", "t0", "t1", "v", "by", "why"}` --
  `samples` the merged stream's count, `max_read_gap` its longest step over the zone (the ring's reads included;
  rev. 2), `input` the witness's entries (2.4.3 step 0; empty on a quiet zone).
- **`observed`** (rev. 2, the claim critique #5): logged just before a V17 whose cause is something the GAME showed --
  a dialog or choice the zone does not claim, a prompt outside the cell, an unrecognized `[DBTN=` page, a page in the
  quiet window, a page after the encore answer that is neither the gil page nor a replay -- `{"k": "observed", "kind",
  "cell", "frame", "texts", "phrase_raw"}`. VOID-ASYM (d) reads these rows (5.3).
- **`press`** rows for prompts (`why` "prompt") and, under the policy, every page press carries `seq`, `ack_frame` and
  the window texts it pressed, and `choose`'s presses are rowed after it returns (`why` "choose", 2.4.11) -- so S9's
  attribution can join every accepted frame.

#### 2.4.7 The j bounds (`j_bounds(row) -> (lo, hi)`, pure; tickrate's Rate rebuilt from the row's `rate`)
- j = ticks from the arm tick S to the tick the press's edge lands on; T = 50 - j credits (e3 polls BEFORE e20 in a
  tick, Obj.cs:31-45 tail order with InitCode(4), InitCode(3), InitObject 5, 6, 13, 20 at ip434-449: the first poll is
  S+1, j = 1..50).
- **Where S lies** (rev. 2, the driver critique #12, the claim critique #11). The window is listed from S on (it joins
  `activeDialogList` in the arm tick, 0.2 #1). Under the measured publication order (the agent's Update before
  HonoBehaviorSystem's, tickrate.py:67-69) a sample of frame f shows the ticks of frames <= f-1, so S lies in the ticks
  of frames [`prev_frame`, `seen_frame` - 1]; under the other order a sample shows frames <= f, and S lies in
  [`prev_frame` + 1, `seen_frame`]. No source line fixes the order (0.3 #2): both bounds below hold under both.
- **Where the edge lands** -- the same under both orders: the first tick of the frames >= `down_frame` (the input is
  frame-scheduled and read before a frame's ticks; a frame with no tick ORs its level into the next tick,
  FPSManager.cs:77-139; 0.3 #2).
- **`j_hi = rate.ticks_most(down_frame - prev_frame) + 1 + ceil(excess)`** (unchanged; now derived under both
  orders). S is at or after the first tick of frame `prev_frame` and the edge is the first tick of the frames >=
  `down_frame`, so j is at most the ticks of the `down_frame - prev_frame` frames [`prev_frame`, `down_frame` - 1] --
  `ticks_most` of them, `+1` the frame jitter a steady loop needs on top of the spread (TAIL_TICKS, tickrate.py:67-77),
  `excess` a hitch's caught-up ticks. The critics' alternatives both count frame `down_frame`'s own ticks, which the
  edge precedes: DR12's `ticks_most(down - prev + 1) + ceil(excess)` trades the jitter tick for that frame -- at 60
  fps a half-tick frame whose ceil can add nothing, a tick under the harness's own bound -- and CI11's `... + 1 +
  ceil(excess)` keeps the tick and adds the frame: sound, a frame wide (both rejected, 11.3).
- **`j_lo = max(1, rate.ticks_sure(down_frame - seen_frame - 1))`** (rev. 2). S is at or before the last tick of frame
  `seen_frame` (the later order), so j >= the ticks of frames [`seen_frame` + 1, `down_frame` - 1] plus one, which with a
  frame's jitter is >= `ticks_sure(down - seen - 1)`. Rev. 1's `ticks_sure(down - seen)` holds under the measured
  order only and can overstate by a tick under the other -- and `raw_hi` rests on `j_lo`: R-GATE's `raw_hi <= 99` is what
  keeps a WITNESSED verdict from being vacuous (7.4), so this bound must hold whichever order the engine runs in.
- `raw_bounds(rows)`: `raw_lo = floor((sum_k (50 - j_hi_k) + (50 - j_hi_49) + 1225) / 29)`, `raw_hi` likewise from
  `j_lo` (49 hits plus the phantom pass's second credit of the 49th; I32 = 0 + 1 + ... + 48 + 49 = 1225); each j
  clamped to 1..50.

#### 2.4.8 The judge (`chanbara_judge(zone, prompts, presses, policy) -> {"v", "by", "why", "faults", "raw"}`, pure)
Rev. 2 (the driver critique #4, the claim critique #2): V18 rests on POSITIVE evidence only -- something a merged
sample SHOWED. A sample that is missing is the driver's sampling: V17, never V18.
**V17 (driver)** -- the first fault in this order: an instance with no press; two presses; a wrong name; no
`accepted` event; `evidence` "before" (the window left before the press could land: a timeout or another's press);
`evidence` "unobserved" ("instrument: a read gap of X s straddles instance n's mark"); `j_hi > j_cap`; (fast)
`raw_lo < raw_floor`; (paced) `[raw_lo, raw_hi]` outside `raw_band`; a non-prompt press whose down frame lies at or
after the first prompt's `prev_frame` and before the zone end (2.4.11); a `rate` not measured (`source` "default" or
`stale`); a measured `slide` that is neither its want nor its want with whole L/R slides left out (its samples are not
what 2.4.6 needs: the instrument's); fewer than `prompts` instances with the zone's `max_read_gap` above the shortest
life of an unpressed prompt (50 ticks): the driver did not read the game long enough to see one.
**V18 (game, a finding)** -- no V17 fault, and positive evidence: a proper press whose `evidence` is "lingered" (a
merged sample listed its window at or past down + `gone_ticks`: the game read no key); a proper LEFT/RIGHT press whose
measured `slide` shows it left out (both bodies unmoved by it: the game read the key as a miss); more instances than
`prompts` (the 50th was listed); fewer, with the zone's `max_read_gap` at or under 50 ticks (the stream covered every
window a prompt could have lived in); or (called at the score/gil page, 2.4.12) a score page or gil page with another
number, read in two consecutive samples.
**V13** is not the judge's: outside input (2.4.3 step 0) and a fight off FieldHUD (step 2) stop the run before it.
**None** -- the play is proven the frozen play. O4-SWORD (e) runs the same judge on every covered run (5.3).

#### 2.4.9 On a VOID in the zone
The executor completes what rows it can (the events joined), logs the zone row with its verdict, and raises the
RouteVoid (cell [64, 1155]) at once: nothing more is pressed. The run is collected as any VOID run; the next run's
`end_run` (or S5's session end) warps to 4600 -- the fight runs on FieldHUD, where the warp is taken
(Ff9mkDebugMenu.cs:2083) -- and climbs the ladder there. R-CHANBARA-VOID proves it (F7); V17 re-runs
(`rerun.max` 2), V18 holds the side (`rerun.stop_on`).

#### 2.4.10 The pace option (R-GATE only; decision 5)
`policy: "paced"`, `pace: {"target_ticks": 22, "lead_ticks": 2, "raw_band": [79, 99]}`, `j_cap` <= 40 (>= 10 ticks
of timeout margin), no `raw_floor`. Rev. 2 (the driver critique #7): a press is due when the instance's ELAPSED GAME
TIME reaches `target_ticks - lead_ticks` ticks, sized by the AVERAGE, never by a bound -- `(st.mtime - seen.mtime) x
rate.tick_hz` (the state file's write times: the clock the rate is measured from, a hitch's caught-up ticks in it),
or `(st.frame - seen_frame) x rate.per_frame()` for a sample without an mtime. Rev. 1 counted `ticks_sure` of the
frames, a LOWER bound (it divides by `fps_hi`): the press landed about a tick late in steady state, and for the
WINDOW_SECONDS after a 60/31 regime switch -- while `TickClock._switch` keeps the old band (tickrate.py:586-649) --
about twice as late, j ~40 at 31 fps: over `j_cap`, or a timeout. Sizing errs either way by a fraction of a tick, and
only the post-hoc bounds (2.4.7) judge. `lead_ticks` is R-CHANBARA's median, per render regime, of `(down_frame -
pre.frame) x per_frame` over its prompt rows -- the latency from the frame of the sample a press was decided on (the
press row's `pre`) to its down frame (rev. 1 named a `pressed_frame` no row defines). With uniform j = 22, raw =
floor((50 x 28 + 1225) / 29) = 90; the band's edges sit at a mean j of 28 (raw 79) and 17 (raw 99). No live gap rule
runs (none does under either policy, 2.4.3): paced prompts OVERLAP the next arm whenever j > A - 3.5 -- j ~22-25
against A ~28-30, most passes -- which the tracker's `closing` set reads as one instance closing beside its successor
(2.4.3 step 8). A run outside the band is V17 "uninformative" (R-GATE re-runs it). `freeze` refuses `paced`, `pace`
and `stop_after`: the frozen session predictions never carry them.

#### 2.4.11 The stray-Confirm guards (S8, S9; critique minor #5)
- **After 111**: page-once (Z0) and the quiet Z1. A rule-7 Confirm decided while 111 is listed lands within the press
  latency (~3-6 ticks), before T0+13; a second one only after `page_once_ticks` (10) past the first's ack-read frame,
  i.e. only when 111 is still listed then -- a first press dropped in 111's opening (0.3 #1), where the second lands
  before T0 too.
- **After 123 (or 121)**: the QUIET window (rev. 2, the driver critique #1, the claim critique #6). 123 is pressed by
  page-once like any page -- again while it is still listed `page_once_ticks` after a press -- because its first press
  usually lands in its opening and is dropped (0.3 #1). Rev. 1 opened the quiet window AT that press: a dropped first
  press then left 123 up for good (Bit[3815] and the `Wait(10)` run only after 123 closes, 0.2 #3), and the run became
  V14 by "game" at [64, 1155] after `quiet_cap_s` on whichever side the random drop fell -- VOID-ASYM (a), NOT PROVEN.
  The window now OPENS at the first merged sample without any window holding a `quiet` marker ("Queen Brahne was")
  after one was pressed; while it is open nothing is pressed until a choice is published; another page in between is
  V17 (game-observed, fail-closed); no choice within `quiet_cap_s` of its opening is V14 (game). A re-press cannot
  reach 127: one is decided only on a sample still listing 123, and 127 opens no sooner than 123's close tween (0.09 s
  plus a frame), the tick e4 resumes in, and the `Wait(10)` at ip399 -- >= ~11 ticks past that sample, against a press
  latency of ~2-4 frames; and a Confirm in 127's own opening sets `SelectChoice` to its default and closes nothing
  (Dialog.cs:798-802).
- **The encore attribution** (rev. 2, the claim critique #8; `stray_answer(log, events, steps, first_frame,
  close_frame)`, pure): the Confirm-bearing presses OF THE VISIT -- every `press` row with a `seq`: page, prompt, and
  `choose`'s, which `answer` rows once `g.choose(1)` returns (the seqs between `g.channel.seq` before and after it,
  their steps from the session's `steps.jsonl`, their accepted frames from `events.jsonl`, 0.3 #10) -- whose down frame
  lies in [`first_frame`, `close_frame`): 127's first publication to the first merged sample without it -- EXCEPT the
  answer's own Confirm when the last merged sample before its down frame published `selected` 1 (No). One or more: V17
  (driver) "a Confirm of the driver's own landed on choice 127 <before its answer | with the cursor on Yes>"; none: V2
  (game) "the game replayed though the driver confirmed No". It runs when `pick_for` raises the encore rule's once-VOID
  (a second 127), and when the first page after the answer is a replay page -- 110/109, the replay's KEYON pair (64 mes
  110 "Die, traitor!", 109 "Is that the best thou canst do!?") -- never through the fight judge, whose V18 would hold
  the side for an event on the choice's path (rev. 1 sent a replay there).

#### 2.4.12 The score page and the gil page (S9)
In the cell, after the zone: the first page holding "nobles watching" must EQUAL `score_page` ("Of 100 nobles
watching,\n100 were impressed.", page 122 with `[NUMB=0]` = 100; 120 reads "Of the 100 nobles watching,") in TWO
consecutive merged samples (rev. 2, the driver critique #10: `[NUMB]` is filled at render, 0.3 #6, so a first sample
can read the tag unsubstituted) -- then the beat `sword` is set and the page pressed; a page holding "nobles watching"
that differs in two consecutive samples stops the run with nothing pressed: `chanbara_judge` over the zone's rows --
V18 when the play is proven, V17 otherwise. After the encore answer the first page is judged by WHAT IT IS (rev. 2, the
claim critique #8): `gil_page` ("They shower you with 10000 Gil!": `[NUMB=1]` = Int16[50], 10000 only at score 100, e4
t1 ip296-307) in two consecutive samples -- pressed; another page holding "They shower you with" (two samples) -- the
fight judge, as at the score page (the gil is the score's: only a different NUMBER is the fight's evidence); a replay
page or a second 127 -- `stray_answer` (2.4.11); anything else -- V17 (game-observed). Both strings are frozen from
R-CHANBARA (F2).

### 2.5 Choice rules
```json
[{"donor": 64, "sc": [1155], "match": "encore", "pick": "No", "once": true, "beat": "encore"},
 {"donor": null, "sc": null, "match": "want to skip", "pick": "default", "once": false, "beat": null}]
```
127 (`[PCHC=2,1][IMME]They demand an encore!\nPerform the fight scene again?\n[CHOO][MOVE=18,0]Yes\n[MOVE=18,0]No`)
opens with its cursor on YES: PCHC's second parameter is the CANCEL choice (DialogBoxSymbols.cs:671-678,
`DefaultChoice = ETb.sChoose`), and the flags-0 WindowSync resets `sChoose` to `sChooseInit` = 0 (ETb.cs:100-104); 64
holds no SetChooseParam. `pick: "No"` resolves to absolute 1 and is answered by `g.choose(1)` (select steers on the
published cursor, session.py:6717-6751; proven on 52's option 1 in O1); never `take: "default"` (that would replay
the fight). Expected publication (unmeasured; O1's lesson): options `[<prompt or ''>, 'es', 'No']`. If R-CHANBARA shows
the No line short its first character too, the freeze takes `pick: "o"` (it matches only that line in ['es', 'No'],
['es', 'o'] and ['Yes', 'No']) (F6). O1's skip rule stays as a net (no FMV on the route). 124-126 (scores below 75)
match no rule: V1 -- unreachable once 2.4.12 has stopped a run that scored below 100.

### 2.6 VOID conditions (each a RouteVoid with its class, cell and attribution; the run is not covered)
| | Condition in O4 | by |
|---|---|---|
| V1 | A choice no rule matches (124-126, anything but 127 and the skip net). | game |
| V2 | The encore rule asked twice, or a replay page after its answer, with no stray Confirm of the driver's own -- page, prompt or `choose`'s -- on 127 (2.4.11). | game |
| V4 | Control held anywhere (the table is empty), the zone included. | game |
| V5 | A stop page ("Env Play()", "Set Scenario Counter()"), nothing pressed. | driver in 64's first visit (the warp's start state); game after |
| V10 | A naming screen, a tutorial, a battle. | game |
| V11 | Off the route or its order (rule 2/3), but V19. | game (O4 has no walks) |
| V13 | The run budget; an instrument stop (a refused press, an unreadable channel); rev. 2: outside input anywhere in the run (the witness, 2.4.3 step 0); the fight off FieldHUD (step 2). | driver |
| V14 | The watchdog; the zone stalled (`zone_stall_s`); no prompt after 111 (`first_prompt_s`); no choice within `quiet_cap_s` of the quiet window's opening. | game |
| **V17** (new) | The fight's input was not proven the frozen play. DRIVER causes: 2.4.8's faults (a read gap among them: no V18 rests on a missing sample); a stray Confirm of the driver's own on 127 (2.4.11); the rehearsal's `stop_after`. GAME-OBSERVED causes, each with its `observed` row (2.4.6; rev. 2): a dialog or choice the zone does not claim; a prompt outside the cell; a `[DBTN=` page neither recognizer claims (S8 a); a page in the quiet window; a page after the encore answer that is neither the gil page nor a replay. Nothing is pressed after any of them. VOID-ASYM (d) fails a game-observed cause on one side only (5.3). | **driver** |
| **V18** (new) | The rows prove the frozen play and a merged sample SHOWED the game deviate: a proper press's window listed at or past down + `gone_ticks`, a proper L/R press's slide left out, another number of prompts, or a score or gil page with another number in two samples (2.4.8). A FINDING (`rerun.stop_on`). | **game** |
| **V19** (new) | On F, the run entered a REAL field the chain forks (a `Field()` the build did not retarget, or an engine id leak) -- S6. A FINDING (`rerun.stop_on`). | **game** |

V3, V6-V9, V12, V15 and V16 cannot arise (no default-take rule, no watched cell, no step, no climb, no backed
forbidden pattern, no battle). The analysis repeats the trace-visible ones (5.1, 5.3), so a driver fault never turns
into STOCK ONLY or FORK ONLY.

---

## 3. Harness additions (FakeGame only; each opt-in, modelled on the bytes, tested)

No `Session`, `channel` or agent change: the prompt is published (`phrase_raw`), a press reaches `B_KEYON`
(`press` -> Schedule, down at frame+1 -> HonoInputManager.IsInput -> UIKeyTrigger.GetKey -> `ProcessInput(false,
false)` in ReadInputLight -> FPSManager collect/flush -> `ETb.ProcessKeyEvents` -> `B_KEYON`, EBin.cs:1094-1101), and
the trace sees both keys. What is missing is a FakeGame that plays the fight as the engine does, so the driver's
loop is tested against the timing it must survive. Every choice below cites the byte or engine line it stands for;
every knob's default is the engine's (or, where unmeasured, the research's estimate, named as such).

**The input model (shared by H10 and H11), per FRAME of the fake:**
- the LEVEL: the OR of the bits of every button held this frame (`_is_held`, the agent's down-at-frame+1 Schedule,
  fakegame.py:1099-1101), each name mapped the AGENT's way -- `ParseControl` (HarnessAgent.cs:1430-1449: `circle`,
  `x`, `a`, `ok` -> Confirm; `b`, `back` -> Cancel; `triangle`, `y` -> Menu; `square` -> Special; `start`, `pause` ->
  Pause; the four direction aliases) -> `GetKeyMaskFromControl` under the identity `logicalToButton` (EventInput.cs
  :476-534: Confirm 0x20000 | Cross 0x4000, Cancel 0x10000 | Circle 0x2000, Menu 0x1000000 | Triangle 0x1000, Special
  0x80000 | Square 0x8000, L1 0x100000 | 0x400 ...), directions straight (Up 0x10, Right 0x20, Down 0x40, Left 0x80,
  :328-346), Pause -> Start 0x8 (:303-305). A module constant `CONTROL_BITS` holds it; `_control` is NOT changed.
- the DELAYED inputs: after a frame that ran a field tick the accumulator is this frame's level (FlushDelayedInputs);
  after a frame that ran none it ORs this frame's level in (CollectDelayedInputs) -- FPSManager.cs:77-136. (Its release
  bookkeeping, `_delayedInputsOff/On`, matters only for a key released and pressed again between two ticks, which the
  driver never does; modelled as the plain OR.)
- per field TICK of the frame (whole ticks: `floor(ticks_run)` crossings in mean mode, `_steps` in quantized mode):
  `keyon = acc & ~skey; skey = acc` (ETb.ProcessKeyEvents, ETb.cs:50-56): one edge per press, none for a key held
  across ticks.

**H10. The KEYON pair beat** `{"keyon_pair": {"texts": [a, b], "raw": [ra, rb], "lag_ticks": 15, "gate_ticks": 40,
"close_s": 0.09, "close_frames": 1}}` (64's 105/106 and 107/108, 150's 98/99): window a, then b `lag_ticks` later (106
after e13's Wait(15), ip816), ui FieldHUD, control off. A Confirm does not page them (`[TIME=-1]` sets the button
inhibit, DialogBoxSymbols.cs:811-826): `_scene_press` ignores it. From `gate_ticks` after b opened (the INCS/250 gate:
e13 ip825-859 waits while `SYSVAR[8] < 2 && Byte[29] > 0` from 250), each tick reads `keyon & (0x20000 | 0x80000)`
(ip865-885: logical Confirm or Special); the first such edge closes both (ip888/891), each listed `close_s` of the
fake's clock plus `close_frames` frames more (the tween: one `WaitForEndOfFrame`, then progress 0 -> 0.6 at
`deltaTime / 0.15`, DialogAnimator.cs:144-173; rev. 2 -- rev. 1 said 0.15 s), and the beat ends. An edge before the
gate is consumed by that tick and lost.

**H11. The Chanbara visit beat** `{"chanbara": {...}}`: the whole 64@100 visit, arrival to `Field(150)`, staged as one
beat (the score pages depend on the fight). Knobs and defaults:
`seed` 0 (the draws; the game's `SYSVAR[0]` = `UnityEngine.Random.Range(0,256)`, GetSysvar.cs:13-14, Comn.cs:8-10, is
unseeded); `sa` 1 (SwordplayAssistance, Memoria.ini:252); `bonus_fires` True (EMinigame.cs:12: False models the
`EffectiveFieldId` wrap failing on a member); `walk_in_s` 1.83 (measured, story-o3 run 6); `gates` {"105": 40, "107":
40} (ticks, <= 250; estimates); rev. 2 (the driver critique #8): `close_s` 0.09 and `close_frames` 1 (every window's
close tween, DialogAnimator.cs:144-173), `open_s` 0.105 and `open_frames` 2 (every PAGE's opening -- 111, 120-123,
128, the choices: progress 0.3 -> 1 at `deltaTime / 0.15`, then a frame to `AfterShown`, DialogAnimator.cs:43-47,
:61-126; a Confirm whose DOWN FRAME falls in it is dropped -- the UI reads Confirm per frame, not per field tick
-- and on a choice it changes nothing, Dialog.cs:762-802; 0.3 #1)
-- both on the fake's clock, scaled by a fast-forward factor of 1; `reaction` {99: 30, 0: 28, 1: 28, others: 30}
(ticks: pass 0's Wait(30) ip1367; L/R the six-tick slide loop then `WaitAnimation` and Wait(22), ip975-1063; the
30-frame clips of anim_frames.json at one frame a tick -- ESTIMATES, R-CHANBARA measures them); `reqsw_ticks` 0
(RunScript(2,13,11)'s wait for e13, EventEngine.DoEventCode.cs:154-183); `publish_order` "agent_first" (rev. 2, the
driver critique #12, the claim critique #1: a sample of frame f shows the beat's state after the ticks of frames <=
f-1, the engine's measured order, tickrate.py:67-69) or "agent_last" (frames <= f; the fake's legacy order); `prompt_raw`
"[STRT=54,1][TAIL=UPRF][IMME]Press [DBTN={dbtn}][MOBI={mobi}] ![TIME=-1]" and `prompt_text` "Press  !" (INFERRED from
105's measured publication and O1's `[CBTN]`; F1 replaces both); `arm_after_111` 12 (ticks: T0+12); `walk_off_s` 2.0;
`exit_wait_ticks` 65 (stage 9's Wait(65), ip478); `exit_to` (required: the field `Field(150)` lands in);
`choice_lines` ("es", "No") (O1's lesson; F6 replaces); `encore` True; `slides` True; and H12's faults. The beat keeps
`fake.chanbara_log`: per instance its arm tick S, its edge tick and the TRUE j (the tests' oracle for 2.4.7's bounds).
The trace: when on, the beat makes Main_Init's stores at its start (64 e0 t0 ip22, 49, 57, 119, 138, 200, 416, 425,
475 with the engine's values) and the stores below, through `script_store` (fakegame.py:2539-2542), so a driver test
reads a trace shaped like the game's.

Per field tick, in the engine's object order -- e2, e4, e3, e13, e20 (Main_Init's InitCode(4), InitCode(3),
InitObject 5, 6, 13, 20 at ip434-449 append in that order, Obj.cs:31-45; `EBin.ProcessCode` walks the list once a
tick, EBin.cs:106-160):
- **e4** (stage 3, `sa` >= 2): `if b52 > 0 and I34 < 50: b52 = 50` (EMinigame.cs:23-30, every sid-4 token fetch).
- **e3** (stage 3 and `b47 == 1`): the eight checks in ip order -- (0x80, 0, 11) ip34, (0x20, 1, 10) ip81, (0x1000,
  2, 10) ip128, (0x40, 3, 11) ip175, (0x4000, 4, 10) ip222, (0x10, 5, 11) ip269, (0x2000, 6, 11) ip316, (0x8000, 7, 11)
  ip363: `if keyon & bit: b47, b46 = (2, b46) if b46 == value else (3, wrong)` -- evaluated in order, so once a miss
  has set b46 to 10/11 a later right bit fails too (two keys in a tick: a miss); then `if acc & 0x8: b47, b46 = 3, 11`
  (Start held, a LEVEL read, ip412); `if b47 in (2, 3)`: CloseWindow(1) (the prompt's tween starts, ip459/484); then
  `if b52 > 0: b52 -= 1` (ip487-498, still inside the `b47 == 1` block: the hit tick decrements too).
- **e13**: the KEYON pair loops of stages 2, 4, 8 (H10's rule).
- **e20** (stage 3), the pass machine:
  - ARM (pass p): `b46 = 88`, then draw `b46 = rng.randrange(256) & 7` and filter in ip order until it is not 88 --
    SByte38 in (-1, 0) and b46 == 0 -> 88 (ip473/499); SByte38 in (1, 2) and b46 == 1 -> 88 (ip525/551); I42 < 10 and
    b46 in (3, 5) -> 88 (ip577/603); I42 < 15 and b46 == 6 -> 2 (ip629); I42 < 15 and b46 == 7 -> 4 (ip655); b46 == b44
    -> 88 (ip681). If `I34 < 49`: `b47 = 1`, `b44 = b46`, `b52 = 50` (ip721-736) and the window `112 + b46` LISTED IN
    THIS TICK (ip789-852); `react = reaction[b45] + reqsw_ticks`; a LEFT/RIGHT previous hit (b45 0/1, `slides`):
    SByte38 -= 1 / += 1 (ip918/1066) and, PER TICK from the arm (rev. 2; 0.3 #3), Blank (published object sid 20)
    -60 / +60 a tick from S+1 to -300 / +300 after S+5, the player a tick later, to -300 / +300 after S+6
    (MoveInstantXZY, ip986/1134 and e13 t11 ip1691/1842).
  - REACT: `react -= 1` a tick; at 0 the WAIT: each tick while `b52 > 0 and b47 == 1` (ip1376-1394).
  - SCORE (ip1397-1541): `if b47 == 1`: b47, b46 = 3, 11 and CloseWindow(1) (the timeout, ip1408-1424); `if b47 ==
    2`: I30 += b52, I32 += I40, I40 += 1; `if b47 == 3`: I40 = 0; I42 = max(I42, I40); b45 = b46; I34 += 1; if I34 < 50
    the next ARM runs IN THE SAME TICK (no Wait between: a timeout, or a hit later than the reaction, re-arms at
    once, the old window still in its tween beside the new: 0.2 #1, #2); else stage 4.
  - THE PHANTOM: pass 49 arms nothing; b47 and b52 keep pass 48's, so a hit is credited again (I32 1225, I42 50).
- **Stage 6** (after 107/108 and the walk-off): `I48 = (I30 + I32) // 29` (ip208); `if sa >= 1 and bonus_fires: I48 +=
  I48 // 10 * 3` and, at I48 >= 75, `fake.achievements.append("Encore")` (EMinigame.cs:18-20, :34-38); H12's
  `score_override`; clamp `> 100 -> 100`, `<= 0 -> 1` (ip233, ip252); `I50 = ((I30 // 5 + I32) + I42 * 2 + I40 * 2) //
  2 + 1` (ip260), 10000 at I48 == 100 (ip296-307); `if Byte[475] < I48`: script_store e4 t1 ip338 (ip327-338); `I42 <
  50`: pages 120 "Of the 100 nobles watching,\n{I48} were impressed." and 121 "Queen Brahne was\nnot impressed.";
  else 122 "Of 100 nobles watching,\n{I48} were impressed.", Wait(5), 123 "Queen Brahne was\nquite impressed.", then
  script_store e4 t1 ip390 Bit[3815] := 1 (ip346-390: AFTER 123); Wait(10); the choice by band (124 < 25, 125 < 50,
  126 < 75, else 127: ip402-462) with its cursor on 0 (ETb.cs:100-104); No: Wait(15), page 128 "They shower you with
  {I50} Gil!", `fake.gil += I50` (ip509-537); Yes: stage 7/8 (the 110/109 pair, no 111, the minigame vars re-zeroed
  as e13 ip690-802 does) and stage 3 again, then stage 6 again (ip338 only if larger, ip390 again on another perfect).
- **Stage 9**: script_store e2 t1 ip331 Byte[8] := 0; `exit_wait_ticks`; script_store e2 t1 ip528 Int16[2] := 325;
  the field becomes `exit_to` (a fresh visit: `_visit += 1`), and the beat ends.
- Publication: the listed windows (a closing one until its tween ends) give `texts` and `raw_texts`; a page renders
  `[NUMB]` substituted (but H12's `unsubstituted_once`); a prompt `prompt_text` / `prompt_raw`; under `publish_order`
  "agent_first" the beat's whole published state -- windows, x, ui -- is the previous frame's.

**H12. Fault knobs** (each absent by default): `lost` (instance numbers whose press the GAME never reads: their bits
are masked out of the level while that instance is armed -- the agent took the press, the input path dropped it);
`miss_read` (instance numbers whose right key the GAME scores as a miss: the window closes, no slide -- a fork that
reads input differently); `score_override` (the number the score page shows: a fork that scores differently);
`extra_prompts` (passes armed past the bytes' 49: a fork that differs); rev. 2: `menu_on_triangle` (a Triangle edge
opens the main menu, `ui_state` "MainMenu", the prompt left armed -- `IsMenuControlEnable` on, 0.3 #5);
`unsubstituted_once` (122 and 128 publish their raw `[NUMB=n]` text in their first sample, 0.3 #6); `replay_on_no`
(the game replays though No was confirmed: V2's case). With the fake's existing `stall_publish` (a publish stalled
mid-rewrite) and `hitch` (a long frame caught up in its ticks). Test-side, not knobs: a driver stall (a wrapped
`g.press` that sleeps before it sends), a READ stall (a wrapped `g.state` that sleeps 0.5 s once, right after a hit's
press returns: inside the gap), a double press (a mutant driver), a key held across an arm (`g.hold` spanning it), a
stray Confirm after 111 (`fake._schedule("confirm", 2)` at T0+13), a stub witness reporting a pad button or a key.

**Tests** (B1; each names the mutant that must make it fail):
- `test_fake_keyon_pair_takes_only_an_edge_after_its_gate` -- a Confirm before the gate leaves both windows up, the
  first after closes both; Special closes them too. Break: read the level instead of the edge.
- `test_fake_chanbara_arms_and_publishes_in_one_tick` -- the arm and the window in one tick, the first poll S+1, a
  press landing on tick S+j credits 50 - j (j = 1, 5, 50), a one-frame tap lands on exactly one tick at 31 and 60 fps
  (`ticks="quantized"`). Break: e3 after e20.
- `test_fake_chanbara_scores_a_perfect_run_exactly` -- 49 hits at j = 5: raw 119 -> 100; trace rows ip338 0 -> 100
  (before 122) and ip390 0 -> 1 (after 123); pages 122/123; 127 with its cursor on 0; No -> 128 "They shower you with
  10000 Gil!"; `achievements == ["Encore"]`. Break: drop the phantom credit (raw 117, I42 49: pages 120/121).
- `test_fake_chanbara_times_out_and_rearms_in_the_same_tick` -- no press on prompt 7: at S+50 the next DBTN is listed
  beside the closing one, no prompt-free publication between; the combo broken: 120/121, no ip390. Break: a Wait(1)
  between the score and the arm.
- `test_fake_chanbara_misses_a_circle_pressed_as_circle` -- `circle` on a CIRCLE prompt misses, `cancel` hits, `x` on
  CROSS hits. Break: map `circle` to Cancel.
- `test_fake_chanbara_misses_two_keys_start_and_a_held_key` -- two bits in one tick miss; Start held misses every
  poll; a key held across an arm gives no edge (the prompt times out). Break: test the right bit first.
- `test_fake_chanbara_filters_hold_on_every_seed` -- seeds 0-19: no repeat; at SByte38 0 no LEFT; no DOWN/UP before
  max combo 10; no CIRCLE/SQUARE before 15; 49 prompts, 50 passes. Break: drop the no-repeat filter.
- `test_fake_chanbara_bonus_knob_and_assistance_levels` -- uniform j 22: raw 90; SA 1 -> 100 (Byte[475] 100);
  `bonus_fires` False -> 90 (Byte[475] 90, page "90 were impressed."); SA 0 -> 90; SA 2 -> no timeout without presses.
  Break: apply the bonus after the clamp.
- `test_fake_chanbara_encore_yes_replays_without_111` -- Yes: 110/109, no 111, a second fight, 127 again; ip338 not
  rewritten after a 100. Break: replay through stage 2.
- `test_fake_chanbara_close_tween_and_slides` -- a hit's window stays listed 0.09 s plus a frame after the hit tick
  (not 0.15 s); a LEFT hit slides Blank -60 a tick from the next arm's S+1 to -300 after S+5 and the player a tick
  later (-300 after S+6), nothing at S itself; a miss slides nothing. Break: release at once; or move the whole slide
  in the arm tick.
- `test_fake_chanbara_page_ignores_confirm_while_opening` (rev. 2) -- a Confirm whose down frame falls within 123's
  `open_s` + `open_frames` is dropped (123 stays listed) and the next closes it; on 127 such a Confirm closes nothing
  and leaves the cursor where it was. Break: `open_s` 0.
- `test_fake_chanbara_publication_order_and_true_j` (rev. 2) -- under "agent_first" the first sample listing a prompt
  is a frame after its arm frame's ticks, under "agent_last" that frame itself; `chanbara_log` holds each instance's arm
  tick, edge tick and true j, at 31 (quantized) and 60 fps. Break: ignore the knob.
- `test_fake_chanbara_faults` -- `lost` {7}: prompt 7 lingers to its timeout though pressed; `miss_read` {7}: its window
  closes on the right key, no slide, the combo broken; `score_override` 87: page "87 were impressed."; `extra_prompts`
  1: a 50th prompt; `menu_on_triangle`: `ui_state` "MainMenu" after a TRIANGLE press; `unsubstituted_once`: 122's first
  sample reads "[NUMB=0] were impressed.", its second "100 were impressed."; `replay_on_no`: 110/109 after a No. Break:
  ignore `lost`.

**Not needed:** a Map-var or text-id publication (an agent instrument: a DLL rebuild that auto-deploys; the driver's
own j bounds suffice, the 100 plan item 8); a `turn`, battle, movie or naming model for O4.

---

## 4. Predictions (draft v1: `O4Segment.draft()`)

### 4.1 Top level
```json
{"version": 1,
 "what": "O4: 64@1155 (warp, entrance 100) -> the sword fight -> 150 -> Field(153), SC 1190; stock vs the alxc disc-1 chain (members 31240-31259; PLAN.md, O4) -- a US session",
 "rehearsals": [],
 "order": ["S","F","S","F","S","F"], "min_covered": 2, "rerun": {"max": 2, "stop_on": ["V18", "V19"]},
 "budget": {"run_s": 600, "run_min_s": 300, "session_s": 3600, "settle_s": 1.0, "no_progress_s": 120,
            "end_row_s": 10.0},
 "start": {"S": 64, "F": 31240}, "entrance": 100, "scenario": 1155, "lang": "us",
 "end_field": 153, "end_fields": [153], "side_ends": {"S": [153], "F": [31245]},
 "route": [64, 150], "visits": [64, 150], "stock_fields": [64, 150, 153],
 "members": {"31240": 64, "...": "...", "31259": 167}, "names": {"31240": "O4_...", "...": "..."},
 "text_block": 2, "text_blocks": [2, 3], "recovery": 4600,
 "cut_start": true,
 "start_first": "4.6", "start_music": "4.6", "start_residue": [[0, 0, 131], [1, 0, 4], [2, 0, 100]],
 "residue_after_start": [],
 "sc_bytes": [0, 1], "ladder": "4.2", "entrance_bytes": [2, 3], "chain": "4.3",
 "writes": "4.4", "error_path": "4.5", "forbidden_sites": "4.5", "dead": "4.5", "inert": "4.5",
 "start_dependent": [], "noise": [], "forbidden": "4.8", "landing": "5.3", "sword": "5.3",
 "end_state": "4.9",
 "battles": [], "stop_pages": ["2.1"], "regions": {}, "hotspots": {}, "table": [],
 "choices": ["2.5"], "naming": [], "beats": ["sword", "encore"],
 "chanbara": "4.10", "fight": "4.14",
 "settings": "4.13", "override70": "4.13", "derived": "4.13", "engine": "4.13"}
```
- `members` and `names` are the twenty of `campaign.toml` (`chain_from_campaign`: exactly the donors 64, 68, 69, 150,
  151, 153-167; ascending fresh ids give member(64) 31240, member(150) 31243, member(153) 31245, which the draft
  DERIVES and the offline check prints -- never assumed). P-DEPLOY, P-EB, P-FLOOR, P-DONOR and the fingerprint read
  all twenty; the route runs member(64) and member(150) and ends in member(153).
- `start_residue` is `[byte, old, new]`: SC 1155 = 0x0483 writes byte 0 (0 -> 131) and byte 1 (0 -> 4); entrance 100
  writes byte 2 (0 -> 100) and leaves byte 3 at 0: three rows, set aside by the front cut.
- `text_block` (2) keeps O2's single-block readers working; `text_blocks` [2, 3] is O4's: block 2 for 64/68/69, block 3
  for 150-167 (EVENT_ID_TO_MES; the members keep their donors' blocks, and member(64) MUST stay on block 2:
  TextOpCodeModifier.ReplaceChanbaraText keys 111's layout on FieldZoneId 2).
- No `start_dependent` keys: under the raw warp nothing on the route reads a start-dependent value (5.4's scope line).

### 4.2 The SC ladder (`Global.UInt16[0]`; O4-LADDER)
| # | donor | sid | tag | ip | off | value | what |
|---|---|---|---|---|---|---|---|
| 1 | 150 | 3 | 1 | 1966 | 1708 | 1190 | stage 10, after the rebuild and Wait(90) (ip1881); the guard ip1884 `SC > 1190` is false |

The segment's ONLY SC write (no stock field stores a value in 1156..1189); ip1952 (`:= 1190` behind the guard, window
55 and a Start press) is a forbidden site (4.5). O2's `span_check` over bytes 0-1 from 1155: exactly this row.

### 4.3 The FieldEntrance chain (`Global.Int16[2]`; O4-CHAIN; the first `old` is 100, the warp's entrance)
| # | donor | sid | tag | ip | off | value | what |
|---|---|---|---|---|---|---|---|
| 1 | 64 | 2 | 1 | 528 | 517 | 325 | stage 9, then `Field(150)` ip536 |
| 2 | 150 | 3 | 1 | 2161 | 1903 | 325 | stage 10, then `Field(153)` ip2169 (a same-value store: emitted once, old 325) |

### 4.4 Registered writes (O4-WRITES: every covered run's keys are EXACTLY these, the ladder and the chain)
Every op is `:=` but the one `++` (O2's key form: `op` mandatory, a compound value computed from its `prior`) and the
one `:=var` (the score: its rvalue is a Map variable, 6.1).

| donor | sid | tag | ip | off | target | value | what |
|---|---|---|---|---|---|---|---|
| 64 | 0 | 0 | 57 | 51 | Int16[9] | -1 | ambient (65535 as Int16) |
| 64 | 0 | 0 | 119 | 113 | Byte[13] | 0 | ambient: the route's branch (also `start_music`, old 1) |
| 64 | 0 | 0 | 138 | 132 | Int16[11] | -1 | ambient |
| 64 | 0 | 0 | 200 | 194 | Byte[14] | 0 | ambient |
| 64 | 0 | 0 | 416 | 410 | Bit[3815] | 0 | the 50-combo flag zeroed on every entrance-100 arrival (same value: emitted once) |
| 64 | 0 | 0 | 425 | 419 | Byte[475] | 0 | the best score zeroed (same value) |
| 64 | 0 | 0 | 475 | 469 | Byte[8] | 125 | BGM volume, after the sound-sync loop (ip458-472) |
| 64 | 4 | 1 | 338 | 316 | Byte[475] | 100 | **THE SCORE**: `:=var` Map.Int16[48] (ip327 `Byte[475] < Int16[48]`), 0 -> 100 |
| 64 | 4 | 1 | 390 | 368 | Bit[3815] | 1 | **THE 50-COMBO**: 0 -> 1, after page 123 (Int16[42] == 50, ip346) |
| 64 | 2 | 1 | 331 | 320 | Byte[8] | 0 | stage 9 |
| 150 | 0 | 0 | 61 | 51 | Int16[9] | -1 | ambient |
| 150 | 0 | 0 | 123 | 113 | Byte[13] | 0 | ambient |
| 150 | 0 | 0 | 142 | 132 | Int16[11] | -1 | ambient |
| 150 | 0 | 0 | 204 | 194 | Byte[14] | 0 | ambient |
| 150 | 0 | 0 | 331 | 321 | Byte[8] | 25 | the 325 branch |
| 150 | 3 | 1 | 1136 | 878 | UInt16[21] | 1 | the party reserve: Zidane (then SetPartyReserve, RemoveParty x12, PARTYADD 0) |
| 150 | 3 | 1 | 1221 | 963 | Byte[303] | 0 | the party count (same value after the raw warp) |
| 150 | 3 | 1 | 1255 | 997 | Byte[303] | 1 | `++`, prior 150/3/1/1221 |
| 150 | 3 | 1 | 1652 | 1394 | Byte[4] | 0 | `PARTYCHK(5)` false at ip1632 (ip1641 `:= 1` not taken) |
| 150 | 3 | 1 | 1667 | 1409 | Byte[4] | 0 | |
| 150 | 3 | 1 | 1675 | 1417 | Byte[17] | 0 | |
| 150 | 3 | 1 | 1683 | 1425 | Byte[18] | 1 | |
| 150 | 3 | 1 | 1974 | 1716 | Byte[8] | 75 | after SC := 1190 |

23 writes + 1 ladder + 2 chain = **26 keys a run**, beside the masked prologue rows (Bit[191] ip22/26, Bit[184]
ip49/53: `boot_scratch`, `field_menu_guard`) and the end cut. Why EXACT (O3's reason): the key set is small and fully
enumerated by the bytes -- O4-CENSUS classifies every store site of 64 and 150 (6.1) and O4-KEYS proves every listed
site -- so any extra key, even on both sides where NULL cannot see it, is a claim failure. R-FULL must show the exact
set before the freeze (F8).

### 4.5 The error path, the forbidden sites, the dead sites, the inert functions (registered; never expected)
`error_path` -- Main_Init's ambient branch for an incoming Byte[13]/[14] of 2 or 9 (`:= 9`, the debug window, then
`:= 0`): 64 e0 t0 ip97/91 Byte[13] := 9, ip178/172 Byte[14] := 9, ip845/839 Byte[13] := 0, ip879/873 Byte[14] := 0;
150 e0 t0 ip101/91, ip182/172, ip1009/999, ip1043/1033 (the same four). A 64 row is the START's fault (A-START, V5 by
the driver); a 150 row a fork deviation (V5 by the game, an extra key).

`forbidden_sites`: 150 e3 t1 ip1641/1383 `Byte[4] := 1` (PARTYCHK(5) true: Quina in the party); 150 e3 t1 ip1952/1694
`UInt16[0] := 1190` (the debug overwrite behind ip1884, window 55 and a Start press).

`dead` (each a real store whose guard is false on the route; every one `:=` but the three `++`):
| donor | sid | tag | ip / off | target := value | why false on the route |
|---|---|---|---|---|---|
| 64 | 0 | 0 | 41/35 | Int16[2] := 10000 | behind `Bit[184] == 1` (ip30): Bit[184] is 0 (New Game; cleared at ip49) |
| 64 | 0 | 0 | 130/124 | Byte[13] := 1 | else of `Int16[9] < 0` (ip108): ip57 has just set it -1 |
| 64 | 0 | 0 | 211/205 | Byte[14] := 1 | else of `Int16[11] < 0` (ip189) |
| 64 | 0 | 0 | 295/289 | Byte[8] := 125 | entrance 327's branch (SWITCHEX ip236 -> L246) |
| 64 | 0 | 0 | 380/374 | Byte[8] := 125 | entrances 315/322's branch (L317) |
| 64 | 2 | 1 | 893/882 | Int16[2] := 0 | the conductor's stage 17 (the 327 visit's exit to 67): Byte[24] runs 1-9 at 100 |
| 64 | 11 | 2 | 193/163 | Int16[2] := 330 | region 11: instanced only on the 315/322 branch (ip334); its tag 2 RETs without control (ip30-37) |
| 64 | 12 | 2 | 193/163 | Int16[2] := 329 | region 12: never instanced at 100; the same control guard (ip30-37) |
| 150 | 0 | 0 | 45/35 | Int16[2] := 10000 | behind `Bit[184] == 1` (ip34) |
| 150 | 0 | 0 | 134/124 | Byte[13] := 1 | else of `Int16[9] < 0` (ip112) |
| 150 | 0 | 0 | 215/205 | Byte[14] := 1 | else of `Int16[11] < 0` (ip193) |
| 150 | 0 | 0 | 497/487, 609/599 | Byte[8] := 125 | the other entrances' branches (SWITCHEX ip242 -> L352 / L403 / L515) |
| 150 | 3 | 1 | 1277/1019, 1299/1041, 1321/1063 | Byte[303] `++` (2, 3, 4: priors chained from ip1255) | behind `SET({const(0)}) JMP_IFNOT` (ip1269/1274 and the same twice) |
| 150 | 18 | 2 | 90/60, 242/212, 378/348 | Byte[8] := 0, Byte[8] := 75, Int16[2] := 5 | region 18 is instanced at 325, but its tag 2 opens `SET(SYSVAR[2]) JMP_IF(L8) RET()` (ip30-37): no control, no store |

`inert` (FUNCTION-level, O4's own census class; 0.2 #4): `[{"donor": 150, "sid": s, "tags": "*", "why": "not
instanced at entrance 325"} for s in (10, 15, 16, 19, 23)]` -- 239 store sites (e10 t3 215, e15 t1 5, e16 t1 4, e19 t2
2, e23 13). O4-CENSUS PROVES the claim from the bytes (6.1): the 325 branch's InitObject/InitRegion/InitCode set
(`instanced_at`) holds none of them. A row from any of them in a covered run is an extra key (O4-WRITES).

### 4.6 The start (O4-START)
```json
"start_first": {"donor": 64, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 22, "off": 16, "target": "Global.Bit[191]",
                "value": 0, "op": ":=", "what": "64's Main_Init: its first store"},
"start_music": {"donor": 64, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 119, "off": 113, "target": "Global.Byte[13]",
                "value": 0, "op": ":=", "old": 1,
                "what": "64's ambient branch from the warp's Byte[13] 1 (field 70's prologue :=1 at ip130; the warp leaves 70 before ip475's :=2)"}
```
`old: 1` is the incoming value O2 and O3 measured after the same start (all twelve runs: 100 e0 t0 ip138, 61 e0 t0
ip119); F8 is the first measurement in 64. The warp window: after 70 e0 t0 ip130 (`Byte[13] := 1`), before ip475 (the
`:= 2` after FMV001) -- `start_run`'s `wait_frames(30)` after New Game lands in it (O2/O3's twelve runs), under the
override P-OVERRIDE pins (critique minor #9). A 2 would take ip97 and the error window: the instrument's, A-START.

### 4.7 Noise: none
Nothing on the route writes a random or timing-bound value to gEventGlobal. The prompts are random
(`SYSVAR[0] & 7`, e20 ip462), but a 49/49 run at score 100 writes exactly the registered keys whatever the order; the
fight's own variables are Map variables (no trace row); the bonus writes Map.Int16[48] only (EMinigame.cs:21); 150 e4
t1 ip285's `SYSVAR[0]` is a cosmetic turn (no store); the type-outs, the package physics and the stage-10 race move
time, never a value. So `noise` is `[]`: NULL and STABLE set nothing aside, and any unstable key fails.

### 4.8 Forbidden
```json
[{"off_route": true, "cause": "walk",
  "why": "a write off the route: S, a place outside route + end_fields; F, a field that is neither a member whose donor is on the route nor F's own end field (real 64/150 on F: an un-retargeted Field() or an engine id leak)"}]
```
`walk` backing needs a `step` row with a V11 landing; O4 has no steps, so a hit is never backed: a FINDING (O4-
FORBIDDEN over every run, VOID ones included). On F a real-150 row is such a hit; a real-153 row is cut away as place
153 (the end place) and is read by V19 (VOID-ASYM) instead -- 5.3 says which check reads which leak.

### 4.9 End state (read live on arrival in 153 / member(153); O4-STATE (b))
```json
{"Global.UInt16[0]": 1190, "Global.Int16[2]": 325, "Global.UInt16[21]": 1, "Global.Byte[303]": 1,
 "Global.Byte[4]": 0, "Global.Byte[17]": 0, "Global.Byte[18]": 1, "Global.Byte[8]": 75,
 "Global.Byte[475]": 100, "Global.Bit[3815]": 1,
 "Global.Byte[13]": 0, "Global.Byte[14]": 0, "Global.Int16[9]": -1, "Global.Int16[11]": -1,
 "Global.Bit[191]": 0, "Global.Bit[184]": 0,
 "Global.Byte[6]": 0, "Global.UInt16[19]": 0, "Global.Byte[206]": 0, "Global.Int16[469]": 0, "Global.Byte[472]": 0,
 "Global.Bit[3717]": 0, "Global.Bit[3718]": 0}
```
Sixteen the route leaves, seven untouched since New Game (after a true O1 -> O3 run Byte[6] would hold 3 and
UInt16[19] 1799: the scope line, 5.4). Stable through 153's Main_Init (0.2 #10).

### 4.10 The Chanbara policy (draft; F3-F5 and F12 re-size it)
```json
{"policy": "fast", "donor": 64, "sc": 1155,
 "buttons": {"LEFT": "left", "RIGHT": "right", "UP": "up", "DOWN": "down",
             "TRIANGLE": "menu", "CROSS": "confirm", "CIRCLE": "cancel", "SQUARE": "special"},
 "press_frames": 2, "prompts": 49, "j_cap": 16, "raw_floor": 100, "gone_ticks": 12,
 "zone_start": {"match": "To follow Blank", "dbtns": 8},
 "zone_end": ["We shall finish this later!", "Come back here!"],
 "first_prompt_s": 3.0, "zone_stall_s": 5.0, "page_once_ticks": 10,
 "quiet": ["Queen Brahne was"], "quiet_cap_s": 5.0,
 "score_page": "Of 100 nobles watching,\n100 were impressed.",
 "gil_page": "They shower you with 10000 Gil!",
 "encore_match": "encore", "poll_s": 0.005, "state_every": null,
 "input_every_s": 0.05, "ring_every_s": 2.0,
 "why": "64 stage 3, the sword fight: e20 t1 ip440-1554 arms 49 prompts over 50 passes and e3 t1 ip23-509 polls the eight KEYON bits once a tick; one mapped press per prompt, fast -- raw >= 100 shows 100 with or without the +30%"}
```
`chanbara_of` (strict, as `movies_of`): the keys exactly these (`pace` and `stop_after` optional, 2.4.10); `policy`
"fast" or "paced"; `donor`, `sc`, `prompts`, `press_frames` (1-4), `page_once_ticks` ints; `buttons` EXACTLY
DBTN_CONTROL; fast: `j_cap` 1-16 (a hit's gap >= ~8 ticks: 0.2 #2) and `raw_floor` an int 79-126; paced: `pace`
present, `j_cap` 1-40, no `raw_floor`; `gone_ticks` 5-20; the `_s` keys positive numbers (`input_every_s` at most 0.1,
`ring_every_s` at most 5: the ring keeps ~10 s, 0.3 #4); the texts non-empty strings; `zone_start.dbtns` 8;
`state_every` null or 1; `stop_after` an int 1-48. A bool is never a number. `j_cap` 16 is the plan's
assist-independent uniform bound (raw 100); the measured j is ~3-5 (worst seen 8-11), raw 114-123. `gone_ticks` 12 =
the hit tick + the close tween (0.09 s plus a frame: ~3.2 ticks at 60 fps, ~3.7 at 31; rev. 2) + a publication (1-2
ticks) + slack: the lingering rule's mark is a positive test (2.4.6), so slack costs only a later stop.
`state_every` null leaves the agent's 2 frames (`stateevery 1` would halve the publish lag and double the in-place
writes a read can land in; F3 decides).

### 4.11 Coverage beats
`sword`: set at 2.4.12 when the score page equals `score_page` after a zone the judge passed. `encore`: set by the
encore rule's answer (No). Plus `end == "reached"`. The 49 prompts, the gil page and the trace's two keys are
re-read by O4-SWORD (5.3); a wrong landing is a VOID with its class (V19, V11).

### 4.12 Budget and recovery
Estimated ~3 min a run (64 ~70 s: the walk-in 1.8 s, the pairs ~3 s each, the fight ~51 s at ~30.5 ticks a pass --
clip speed unmeasured --, the pages and the choice ~5 s, Wait(65); 150 ~65 s; start and end ~20-30 s). Drafts:
`run_s` 600, `run_min_s` 300, `session_s` 3600 (6 runs + 2 re-runs with slack), `settle_s` 1.0, `no_progress_s` 120
(the longest expected stretch: a KEYON pair's gate, <= 8.3 s), `end_row_s` 10; the policy's `first_prompt_s` 3,
`zone_stall_s` 5, `quiet_cap_s` 5. F10 replaces every one. Recovery is `end_run`: the warp to 4600 first (from the
fight, from 150, from 153: all FieldHUD), then the ladder; the session ENDS through `end_run` too (S5,
`end_session_warps`). F7 proves it from inside the fight.

### 4.13 Settings, the New-Game override, the derived facts
```json
"settings": {"Battle": {"Enabled": "1", "SFXRework": "1", "Speed": "5", "CustomBattleFlagsMeaning": "0"},
             "Cheats": {"Enabled": "1", "AutoBattle": "1", "SpeedMode": "1", "SpeedFactor": "3", "SpeedTimer": "0",
                        "BattleAssistance": "1", "Attack9999": "1", "NoRandomEncounter": "1", "MasterSkill": "0",
                        "LvMax": "0", "GilMax": "0"},
             "Hacks": {"Enabled": "1", "AllCharactersAvailable": "1", "SwordplayAssistance": "1", "DisableNameChoice": "0"},
             "Control": {"Enabled": "1", "SoftReset": "1", "TurboDialog": "1", "BattleAutoConfirm": "1",
                         "DialogProgressButtons": "\"Confirm\"", "AlwaysCaptureGamepad": "1", "SwapConfirmCancel": "0"},
             "Graphics": {"Enabled": "1", "FieldTPS": "30"}},
"override70": {"FF9CustomMap-world": "2ce8887ea969db6b6518bd33151b1a8805af10a6c9c96a0f59b49bad9ffc9215"},
"derived": {"cfg_control": {"value": 0, "why": "0.2 #6: New Game -> SettingsState.Initial -> cfg = new FF9CFG() (control 0) -> SetPrimaryKeys: identity logicalToButton (HonoInputManager.cs:967-975); only a save load restores cfg"},
            "tick_hz": {"value": 30, "why": "FieldTPS 30 (Memoria.ini:53, [Graphics] Enabled 1); FastForwardFactor 1: Initial rebuilds IsBoosterButtonActive with [1] (IsFastForward, SettingsState.cs:55) false, and the factor is 1 outside a Movie scene (:66-74); mid-run only F1 or a pad sets it (0.3 #7), which the input witness catches"}},
"engine": {"x64": "ba9762423da8f3d749a41a9988ef951d2a4fa62c296acc5aa44054439b45dcfc",
           "x86": "ba9762423da8f3d749a41a9988ef951d2a4fa62c296acc5aa44054439b45dcfc",
           "why": "0.3 #8: the Assembly-CSharp.dll every fork gate, EMinigame line and harness behaviour in this design was read from (= C:\\gd\\FFIX\\Memoria\\Output, Sep 26 17:10); an engine rebuild auto-deploys over the shared install"}
```
Raw ini values as the engine takes them (O3's `install_settings`: case-sensitive, the last assignment wins, the
stacked folders' own Memoria.ini layered over the root's). `derived` is recorded, never checked live (the agent
publishes neither); F2's 49/49 reading 122/123 is the in-game confirmation, and the report prints both. `engine`
(rev. 2, the claim critique #9) is CHECKED live: P-ENGINE (6.2), every run's fingerprint (6.3), P-LAUNCH, and R-GATE's
witness (`gate_witness.engine`, P-GATE) -- a session on another engine is no session of this claim, and a witness from
another engine is no witness for this one.

### 4.14 The fight pins (O4-KEYS (b): the bytes the policy and the FakeGame model rest on)
`fight.pins`, each `[donor, sid, tag, ip, eb-src text]`, compared EXACTLY with the stock US script's instruction text:
| what | site | text |
|---|---|---|
| the roll | 64 e20 t1 ip462 | `SET({Map.Byte[46] B_SYSVAR[0] const(7) B_AND B_LET B_EXPR_END})` |
| no repeat | e20 t1 ip681 | `SET({Map.Byte[46] Map.Byte[44] B_EQ B_EXPR_END})` |
| 49 prompts | e20 t1 ip710 | `SET({Map.Int16[34] const(49) B_LT B_EXPR_END})` |
| the arm | e20 t1 ip721 | `SET({Map.Byte[47] const(1) B_LET B_EXPR_END})` |
| TimeLeft 50 | e20 t1 ip736 | `SET({Map.Byte[52] const(50) B_LET B_EXPR_END})` |
| the windows | e20 t1 ip789, 798, 807, 816, 825, 834, 843, 852 | `WindowAsync(1, 160, 112)` .. `WindowAsync(1, 160, 119)` |
| the wait | e20 t1 ip1379 | `SET({Map.Byte[52] const(0) B_GT Map.Byte[47] const(1) B_EQ B_ANDAND B_EXPR_END})` |
| the credits | e20 t1 ip1438, ip1456 | `SET({Map.Int16[30] Map.Byte[52] B_PLUS_LET B_EXPR_END})`, `SET({Map.Int16[32] Map.Int16[40] B_PLUS_LET B_EXPR_END})` |
| 50 passes | e20 t1 ip1546 | `SET({Map.Int16[34] const(50) B_LT B_EXPR_END})` |
| the poll gate | e3 t1 ip23 | `SET({Map.Byte[47] const(1) B_EQ B_EXPR_END})` |
| the eight keys | e3 t1 ip34, 81, 128, 175, 222, 269, 316, 363 | `SET({const(128) B_KEYON B_EXPR_END})`, `const(32)`, `const(4096)`, `const(64)`, `const(16384)`, `const(16)`, `const(8192)`, `const4(32768)` |
| their values | e3 t1 ip43, 90, 137, 184, 231, 278, 325, 374 | `SET({Map.Byte[46] const(N) B_EQ B_EXPR_END})`, N = 0..7 |
| Start held | e3 t1 ip412 | `SET({const(8) B_KEY B_EXPR_END})` |
| TimeLeft-- | e3 t1 ip487, ip498 | `SET({Map.Byte[52] const(0) B_GT B_EXPR_END})`, `SET({Map.Byte[52] B_POST_MINUS B_EXPR_END})` |
| the score | e4 t1 ip208 | `SET({Map.Int16[48] Map.Int16[30] Map.Int16[32] B_PLUS const(29) B_DIV B_LET B_EXPR_END})` |
| the hook's statement | e4 t1 ip222 | `SET({Map.Int16[48] const(100) B_GT B_EXPR_END})` (its first token at ip223: EMinigame.cs:14) |
| the clamp | e4 t1 ip233 | `SET({Map.Int16[48] const(100) B_LET B_EXPR_END})` |
| the combo test | e4 t1 ip346 | `SET({Map.Int16[42] const(50) B_LT B_EXPR_END})` |
| the pages | e4 t1 ip357, 366, 375, 384 | `WindowSync(5, 0, 120)`, `(5, 0, 121)`, `(5, 0, 122)`, `(5, 0, 123)` |
| the encore | e4 t1 ip462, ip476 | `WindowSync(5, 0, 127)`, `SET({B_SYSVAR[9] const(0) B_EQ B_EXPR_END})` |
| the gil page | e4 t1 ip531 | `WindowSync(5, 0, 128)` |
| the tutorial | e13 t1 ip900 | `WindowSync(6, 0, 111)` |
| the pairs | 64 e13 t1 ip868, ip1404; 150 e2 t1 ip538 | `SET({const4(131072) B_KEYON B_NOT const4(524288) B_KEYON B_NOT B_ANDAND B_EXPR_END})` |
| the exits | 64 e2 t1 ip536; 150 e3 t1 ip2169 | `Field(150)`; `Field(153)` |
| the SC guard | 150 e3 t1 ip1884 | `SET({Global.UInt16[0] const(1190) B_GT B_EXPR_END})` |
| PARTYCHK | 150 e3 t1 ip1632 | `SET({const(5) B_PARTYCHK B_EXPR_END})` |

`fight.prompt_mes` `{"112": "LEFT", "113": "RIGHT", "114": "TRIANGLE", "115": "DOWN", "116": "CROSS", "117": "UP",
"118": "CIRCLE", "119": "SQUARE"}` (block 2, US, the asset the engine reads): each message passes `prompt_dbtn` with
exactly its DBTN -- the window `112 + Byte[46]` (ip789-852) and the poll value N (ip43-374) agree; mes 111 passes
`is_zone_start`; mes 122/123/128's sources hold "Of 100 nobles watching,", "quite impressed." and "They shower you
with". The model and the recognizer can then never drift from what the game shows.

---

## 5. Checks (O4's analysis)

### 5.1 Reading a run: the COVERED rule
O3's rule (skipped, install changed, the drive did not reach the end, a beat not done, no or an incomplete trace,
A-NOSTART, a BACKED forbidden hit, A-MISMATCH, A-START on 64's error path, A-NOEND), unchanged. A drive VOID carries
its V-class (2.6). The report lists every uncovered run's reasons per side.

### 5.2 The cuts (per side, frozen places)
`cut_at_start` from 64's first `w` row (place 64: real 64 on S, member(64) on F; the three residue rows in 70 go to
`pre`); `cut_at_end` at the first `w`/`r` row in an end PLACE -- `end_places(pred, side)`, [153] on both sides (S6).
On F the end PLACE 153 is member(153)'s; a real-153 row is the same place, so the cut alone cannot tell them apart:
O4-LANDING (d) reads the cut row's `fld` (31245 on F, 153 on S), and a run that entered real 153 is VOID by rule 2
first (V19). No seam exists on a covered run: F runs member(64) -> member(150) -> member(153) inside the chain (O4-
LANDING (e)), so O2/O3's SEAM check is not run.

### 5.3 The checks, in order, each with the mutant that makes it fail (section 8 registers every one)
**All-run checks** (every run with a readable trace, judged even when COVER is short):
- **O4-FORBIDDEN** (O2's): no unbacked forbidden hit. Mutant: leak-real-150-F.
- **O4-VOID-ASYM**: O2's (a) a game-attributed class (with its cell) on one side only; (b) every run of one side VOID in
  one class while the other has >= `min_covered` covered; **(c) (new)** any run of either side VOID in a FINDING
  class (`rerun.stop_on`: V18, V19) -- a finding is never a VOID, whichever side or sides it is on (the 100 plan
  item 7: one side, the fork scores or reads input differently; both, the instrument); and **(d) (rev. 2, the claim
  critique #5)** a GAME-OBSERVED V17 cause on one side only: the VOID runs' `observed` rows (2.4.6, read through
  `_run_log`), keyed `(kind, cell)`, held by some run of one side and by no run of the other. V17's game-observed
  causes are things the game SHOWED (an unclaimed window, an unrecognized prompt form, a page in the quiet window);
  decision 6 keeps them V17 with nothing pressed, and O2's (a) counts only game-attributed classes
  (o2_alexandria.py:1289-1312) -- so without (d) a fork that shows an extra window in one of its runs is re-run
  (`rerun.max` 2) and comes out PROVEN. Mutants: v18-one-F (a, c), v18-one-each-side (c alone), v19-one-F (a, c),
  v17-all-F (b), control-S (a), observed-unclaimed-one-F (d alone), observed-unclaimed-one-each-side (PASS: a symmetric
  one is no fork deviation).

**Then:** **O4-FROZEN**, **O4-COVER** (O1's). Mutants: predictions-changed; sword-beat-missing.

**Core checks** (over the covered runs):
- **O4-START** (O3's): (a) `pre` is exactly the three residue rows; (b) the first `w` row in place 64 is
  `start_first`, raw; (c) the first Byte[13] row in place 64 is ip119 `:= 0` from old 1. Mutants:
  start-residue-wrong (a), front-cut-write (a), start-first-missing (b), start-music-old-wrong (c).
- **O4-LADDER** (O2's `span_check` over bytes 0-1 from 1155): exactly the one row 1155 -> 1190 at 150 e3 t1 ip1966.
  Mutants: ladder-missing-fork, sc-write-fork (a `cs` UInt16[0] := 1190 row in 64), sc-write-both, ladder-old-wrong
  (LADDER alone), sc-harness-poke-both (a harness Byte[0] row after ip1966: LADDER alone -- the digest keeps harness
  rows out of its keys, so WRITES, NULL, STATE and RESIDUE pass it).
- **O4-CHAIN** (O2's over bytes 2-3 from 100): exactly 4.3, in order, each from the last. Mutants: chain-dropped-fork,
  chain-first-old-wrong (CHAIN alone).
- **O4-RESIDUE** (O2's): none after the start. Mutant: residue-after-start.
- **O4-WRITES (exact)**: for every covered run, `{k for k in digest.keys if not is_noise(k, pred)}` == the 26 keys.
  Mutants: fork-drops-a-write (missing), writes-extra-symmetric (150 ip1277's dead `++` on both sides: extra; NULL
  passes it), inert-row-both (an e10 t3 Byte[1034] row in 150: extra).
- **O4-NULL**, **O4-STABLE** (O1's, no noise). Mutants: NULL -- fork-drops-a-write, byte475-93-every-F; STABLE --
  extra-key-one-F (rev. 2, the claim critique #15: one F run of three holds 150 ip1277's dead `++` after ip1255: STABLE
  F, WRITES F, STATE F; NULL passes it, the key being on no other run). Rev. 1 registered STABLE against the two NULL
  mutants, which change EVERY F run alike -- a side stable in its error -- so STABLE could not fail as registered.
- **O4-LANDING (new; decision 4)**, every covered run (F with the members map; S its own ids), each clause named:
  - (a) every field-mode `w`/`c` row ran in its place's own field (member(place) on F, the place on S) and none stands
    in a place off `route_places` [64, 150] (O3's clause);
  - (b) the 64 -> 150 crossing, on `w` rows: the run holds `landing.exit64` (64 e2 t1 ip528 Int16[2] := 325); the next
    field-mode `w` row after it is `landing.enter150` (150 e0 t0 ip26 Bit[191] := 0, raw) -- 150 loaded by 64's
    `Field(150)`; no field-mode `w` row of place 64 after `enter150`;
  - (c) the last field-mode `w` row before the end cut is `landing.exit150` (150 e3 t1 ip2161), and the run's `end` log
    row names the side's end field (153 on S, member(153) on F);
  - (d) THE END PER SIDE: the end cut (`r["cut_row"]`) is a raw `w` row that is `landing.end_row` (153 e0 t0 ip22
    Bit[191] := 0) at `fld` = the side's end field -- 153 on S, member(153) on F (a real-153 cut row on F fails here);
  - (e) every F digest records no seam and no seam key (the chain is closed from member(64) to member(153)).
  Mutants: (a) lands-real-150-covered (with FORBIDDEN, (b), (e), WRITES -- (a) cannot fail alone while FORBIDDEN reads
  the same raw rows: O3 11.3 #8); (b) 64-after-150-both (alone), chain-dropped-fork; (c) last-place-harness-both
  (alone: a harness row standing in 150 after ip2161, which no key or history reads) and, for its second half,
  end-log-row-real-153-F (rev. 2, the claim critique #15: a SYNTHETIC log whose F runs' `end` row names field 153
  while their traces cut at member(153) -- the live rule 1 writes that row only for a field in the side's end list,
  so no session can produce it; the clause guards the per-side end lists S6 configures, and the dry run proves it can
  fail); (d) end-real-153-F (alone:
  every F run's cut row at fld 153 with its `off` row in member(153)), end-boundary-residue-both (alone: an `r` row in
  place 153 before its ip22 becomes the cut); (e) registered with its co-failures (a seam needs a real non-member row,
  which (a) and FORBIDDEN read too).
- **O4-SWORD (new; the 100 plan item 6)**, every covered run of both sides:
  - (a) exactly ONE raw `w` row of `sword.score` (place 64, e4 t1 ip338, Global.Byte[475], old 0, new 100) and exactly
    ONE of `sword.combo` (ip390, Global.Bit[3815], old 0, new 1), each at fld member(64) on F / 64 on S, the score row
    before the combo row;
  - (b) the transcript (`outcome.pages`) holds `score_page` then the 123 text ("Queen Brahne was\nquite impressed.") in
    order after the zone, and no page holding "Of the 100 nobles watching" or "not impressed";
  - (c) exactly one `choice` row whose options hold `encore_match`, answered absolute 1 by the encore rule, and no
    second;
  - (d) the transcript holds `gil_page` exactly once, after that choice;
  - (e) `chanbara_judge` over the run's `zone` and `prompt` rows returns None: 49 prompt rows, one mapped press each
    (`button == buttons[dbtn]`), its accepted event, `j_hi <= j_cap`, `raw_lo >= raw_floor`, each instance's
    `evidence` "closed" (rev. 2, 2.4.6: positive -- a merged sample listing the window at or after its down frame and
    the first without it by down + `gone_ticks`; a late first-without sample from a read stall no longer reads as
    lingering, the driver critique #4), no LEFT/RIGHT `slide` measured and not ok (the unmeasured are counted and
    reported; Bit[3815] and page 123 already prove 49 hits on a covered run, so a slide is a corroborating witness,
    never a requirement to measure), and the zone's `input` empty (no outside input, 2.4.3 step 0). (At the draft's
    `j_cap` 16 and `raw_floor` 100 the floor is implied -- every `j_hi` <= 16 gives raw_lo >= floor((49 x 34 + 34 +
    1225) / 29) = 100 -- so its fault is the judge's unit in section 8, not a session case; it bites only if F3 freezes
    a `raw_floor` above 100.)
  - (f) no press row other than the prompts' whose down frame lies AT OR AFTER the first prompt's `prev_frame` and
    before the zone end -- the stray-Confirm guard after 111, read from the rows (decision 6). Rev. 2 (the driver
    critique #5): rev. 1 started the window at `start_page.last_with_frame`, but the press that closes 111 goes down
    BEFORE 111 leaves the list (its close tween, 0.09 s plus a frame) and whether any sample lists 111 after that down
    frame is a race -- lost, `last_with` is the decision sample and the run's own closing press is flagged. The harm
    window is the fight's: a Confirm down before the first prompt's `prev_frame` gives its edge no later than the arm
    tick, where e3's poll gate (`Byte[47] == 1`) is still shut (2.4.7's frame-to-tick reading). At Z3 the executor joins
    the accepted frame of EVERY press row of the visit that carries a `seq` (111's presses included), and 111's
    `last_with` / `first_without` come off the merged stream (2.4.1).
  The trace cannot say which presses made the score (the fight's variables are Map variables), so (e)/(f) re-read the
  driver's own record, as O3-BATTLE did. Mutants, each SWORD alone: sword-second-390-both (a: a second ip390 row 1 -> 1,
  a same key, an identical history on every run), sword-page-120-both (b), sword-yes-both (c), sword-gil-page-both
  (d), sword-48-prompts-both, sword-circle-alias-both, sword-j-over-cap-both, sword-evidence-before-both,
  sword-evidence-lingered-both, sword-evidence-unobserved-both, sword-slide-not-ok-both, sword-input-noise-both (e),
  sword-stray-press-both (f: a page press whose down frame lies between instance 1's `prev_frame` and the zone end);
  and byte475-93-every-F, bit3815-missing-F (a, with WRITES, NULL, STATE). Rev. 2 also registers two PASS cases:
  sword-slide-unmeasured-both (unmeasured slides are no fault) and sword-111-closing-press-late-both (every run's 111
  press goes down after `start_page.last_with_frame` and before instance 1's `prev_frame`: PROVEN).
- **O4-MASKED** (O2's). Mutant: masked-differs.
- **O4-STATE** (O2's): (a) each unmasked target's emitted history identical across every covered run, in order, and
  the suppressed stores as a set; (b) every covered run's `end_state` == 4.9. Mutants: end-state-differs (b),
  fork-drops-a-write (a).
- **O4-JOIN** (O1's). Mutant: join-failure.
- **O4-THROW** (in `run`): nothing thrown through EventEngine, EBin, StoryTrace or HarnessAgent.

**VERDICT**: O1's `verdict()`. A failed check outranks a void one, so FORBIDDEN and VOID-ASYM make a short session NOT
PROVEN (a V18 or V19 reads "NOT PROVEN: O4-VOID-ASYM", never VOID).

### 5.4 Report-only (`report_extra`)
- **Scope**, six lines: start dependence -- "under the raw warp no key on the route is start-dependent: 64 zeroes
  Byte[475] (ip425) and Bit[3815] (ip416) before reading either; 64 reads Byte[13]/[14]/Bit[184] before writing them
  and takes ip119/ip200 from the warp's (1, 0, 0) as from a true O3 end's (0, 0, 0); 150 writes UInt16[21] and
  Byte[303] before reading them; Byte[4]/[17]/[18] have no reader on the route. Not covered: party data, items, gil
  (+10000 at a score of 100), AP, field 70's override state, and the seven untouched targets' values after a true
  O1-O3 run"; settings -- the recorded `settings`, and `derived` (cfg.control 0, 30 ticks a second) with their
  citations; the engine -- the recorded `engine` (P-ENGINE's detail); language -- DERIVED from the session's recorded
  P-TEXT lines (rev. 2, the claim critique #12): "a US session (P-LANG): the members' other languages are their own
  donors' (today's kit); blocks 2 and 3: <n> byte-equal per language of 7 each" and every recorded non-ok line quoted,
  never a hard-coded "byte-equal" (P-TEXT FAILs a defect after the deploy, 6.2, so a PROVEN session's line reads 7 of
  7); the fight -- (rev. 2, the claim critique #10) "a FAST play: raw >= 100, so the +30% is hidden by the clamp; the
  bonus on member(64) is R-GATE's: <verdict> (<cause>)", read from the session's recorded P-GATE detail; the
  achievement -- "every run that scored >= 75 reported Steam's Encore achievement (EMinigame.cs:20, 34-38): outside
  gEventGlobal, not suppressed".
- **The fight, per run**: the zone's instances and presses, the first prompt's ticks after T0, j min / median / max
  (`j_hi`), raw [lo, hi], the regime(s), the merged stream's samples and `max_read_gap` (frames, ticks, seconds), the
  instances' `evidence` counts, the gone latency (median ticks, off the first sample without), the slides (ok /
  unmeasured / not ok), the zone's `input`, the published prompt forms seen (distinct `phrase_raw` shapes), the
  judge's verdict; the score page, the gil page, the trace's ip338/ip390 rows.
- **The encore, per run**: 127 as published (options, active, selected at readiness), the pick, its frame, and the
  rowed `choose` presses.
- **R-GATE** (rev. 2, the claim critique #9): the witness AS THE SESSION RECORDED IT -- P-GATE's detail in the session's
  preflight record (`gate_witness`: run dir, verdict, cause, engine, settings) -- never a fresh read of `o4_forks.json`,
  a repo file editable after the session, so an archived analysis cannot change; outside the frozen claim.
- **The session's end** (S5), O2's sections copied (VOID reasons per side, masked counts, forbidden hits, the P-TEXT
  lines for blocks 2 and 3, the folded transcripts: prompts are NOT pages, so the transcripts compare across random
  sequences), and the re-runs held (S2).

---

## 6. Offline check and preflight

### 6.1 `--offline-check` (the install and the O4 build, read-only; reads `--predictions`, else the frozen file, else the DRAFT, and prints which)
- **O4-BUILD**: `Segment.build_check` without `accept_us_build` (today's kit: every language its own donor's,
  remapped): "140 files, every language its own donor's" (20 members x 7). Plus the FORK-GATE PINS (critique minor
  #11), checked PER LANGUAGE against that language's donor (an `.eb` is not language-identical, so each language's
  script is decoded on its own; the ips below are the US ones, each other language's located by decoding):
  - member(64)'s e4 t1 instructions from the score (US ip208) through the Byte[475] store (US ip338, which ends at
    ip346) are byte-equal to the donor's AT THE SAME ips: the score, the statement whose first token EMinigame hooks
    (`sid == 4 && ip == 223`, EMinigame.cs:14 -- an ip shift would skip the bonus silently), the clamp, the store;
  - the bytes in which member(64) differs from stock 64, and member(150) from stock 150, are EXACTLY the operands of
    their in-chain `Field()` instructions (`remap_fields` retargets every `Field()` whose literal is a chain donor):
    member(64) -- e2 t1 `Field(150)` (US ip536, the route's), e11 t2 and e12 t2 `Field(153)` (US ip201 each, region
    exits that never run at 100); member(150) -- e3 t1 `Field(153)` (US ip2169, the route's), e18 t2 `Field(153)`
    (ip386) and e19 t2 `Field(153)` (ip342), region exits that never run at 325. 64 e2 t1's `Field(67)` (ip901) stays
    real (67 is not in the chain), and every `PreloadField` operand (64 ip426 and ip791, 150 ip2059, the regions' ip91
    and ip192) stays the donor's. Each operand keeps its length (31243 and 31245 fit the Int16), so no ip shifts.
    The critic named two operands; the bytes hold six (11.1, #11). The implementer measures the diff on C0's build
    before C1 lands; any other differing byte is explained at the byte level and registered in the pin, never
    loosened silently.
- **O4-KEYS**: (a) O2's `keys_check` on a filtered copy -- the ladder, the chain, the writes but the `:=var` key,
  `forbidden_sites` + `error_path` + `dead`, `start_first`; no noise, no start-dependent keys; then the `:=var` key
  (64 e4 t1 ip338: the joined store's statement is `Global.Byte[475] Map.Int16[48] B_LET`, its registered value 100
  rests on the clamp pin and O4-SWORD (a), never computed here) and `start_music` as exactly one writes key (O3's).
  Today O2's half reads "55 sites (55 keys), every op in its statement, 4 compound values computed from their
  priors, none masked (start_first's Bit[191] is boot_scratch: O4-START reads it raw)" -- ladder 1, chain 2, writes
  22, forbidden 2 + error path 8 + dead 19, start_first 1 -- and O4 appends "; the score's :=var key (64 e4 t1 ip338,
  rvalue Map.Int16[48]) in its statement; start_music one writes key": 56 sites. (b) THE FIGHT PINS (4.14): 56
  instruction texts equal, `prompt_mes` as pinned, 111 a zone start, the three page sources.
- **O4-TEXT**: O2's `text_rule` on block 2 AND block 3 against the O4 build, each language against the asset the engine
  reads (its ResourceManager path): "block 2: 7 byte-equal of 7; block 3: 7 byte-equal of 7; KNOWN-KIT-DEFECT 0, FAIL
  0". STRICT (rev. 2, the claim critique #12): the verdict is `strict_text(lines)` -- FAIL on any FAIL line AND on any
  KNOWN-KIT-DEFECT line. `text_rule` itself only NAMES another language's copy (o2_alexandria.py:443-456), which left
  "per language" printed and never enforced; O4 claims per-language text, so a defect is a failure (its fix:
  `tools/refresh_verbatim_text.py` and a rebuild, before C1 lands). `text_rule` is not edited (G11, G18).
- **O4-CENSUS** (O4's `store_census`): every gEventGlobal store site of stock 64 and 150 is in `writes`, the
  `ladder`, the `chain`, the story-noise mask, `start_first`, `error_path`, `forbidden_sites`, `dead` or an `inert`
  function; every function decodes; no unresolved store; and the `inert` claim is PROVEN: 150's InitObject/InitRegion/
  InitCode instructions all sit in e0 t0, and the ones the 325 branch runs (`instanced_at`: from the SWITCHEX case
  L248 to the branch's end, plus the common code before the SWITCHEX) are {1 (code, ip227), 2, 3, 5, 6, 9, 4, region
  18, code 17} -- none of 10, 15, 16, 19, 23. Today: "64: 25, 150: 273 store sites -- all classified (writes 10/13,
  ladder 0/1, chain 1/1, masked 2/2 (64's ip22 is start_first), error_path 4/4, forbidden 0/2, dead 8/11, inert
  0/239); 0 unresolved; inert 10, 15, 16, 19, 23 not instanced at 325".
- No REGIONS check: the route grants no control, so no walk can enter a region; every region's stores are classified
  by the census (64's e11/e12 dead, 150's e18 dead, e19 inert).

### 6.2 `--preflight` (the live install, read-only; RED until the owner-gated deploy, which is expected)
- **P-MANIFEST**, **P-DEPLOY**, **P-EB**, **P-FLOOR** (the base's, over the twenty): red before the deploy.
- **P-STOCK**: no mod folder overrides 64, 150 or 153 (`storytrace.stock_overrides`): today none.
- **P-TEXT** (blocks 2 and 3, O2's `text_rule` on every folder that ships them; rev. 2, the claim critique #12:
  `strict_text` once O4 is deployed). Block 3: strict always -- any KNOWN-KIT-DEFECT line FAILs (no folder ships block 3
  before O4's deploy: PASS, "none shipped"). Block 2: while NO O4 member is registered (P-DEPLOY red), the one
  tolerated defect is O1's known copy -- FF9CustomMap's block 2 whose per-language shas equal `o4_forks.json`'s
  `text_effects.o1_block2` (today: PASS with "KNOWN-KIT-DEFECT uk: ships stock us (3a6f3246c2; stock uk 7ac9f17435)",
  named); any other defect, or any defect once an O4 member is registered, FAILs. After the deploy: block 2 seven
  byte-equal (O4's copy replaced O1's: 6.4), block 3 seven byte-equal -- and the session's report derives its language
  line from these recorded lines (5.4).
- **P-RECOVERY**: 4600 registered (FF9CustomMap-world).
- **P-DONOR**: 64, 150 and 153 each in exactly ONE ForkDonorPatch row across the stack, its member's (O3's `p_donor`
  over `route + end_fields`): red before the deploy. No redirect fires on O4's route (0.2 #14), so this is the
  install's hygiene the chain must keep: a donor forked twice sets `ForkSiblingMap[donor] = -1` (DataPatchers.cs
  :147-165), the battle-return and overworld redirect off for EVERY chain that forks it (6.4). The member side --
  `EffectiveFieldId(member)` = donor, which the +30% wrap keys on (EMinigame.cs:12) -- reads the fork -> donor map
  (DataPatchers.cs:47-50, `ForkDonorMap[fork] = donor`, the highest folder's row winning), which P-DEPLOY pins
  ("mapped once to its donor").
- **P-SETTINGS**: `install_settings` == `settings` (4.13), key for key: today PASS.
- **P-PAD** (critique minor #7): `xinput_slots(reader)` samples XInput slots 0-3, 25 reads 20 ms apart: FAIL on any
  button bit, a trigger >= 30 (XINPUT_GAMEPAD_TRIGGER_THRESHOLD) or a thumb axis past 0.10 of full scale (3277: the
  engine's `[AnalogControl] StickThreshold` 10, stricter than XInput's deadzone) in any read; a connected idle pad
  PASSES with a printed `WARN: an XInput pad is connected at slot N (idle over the sample) -- unplug it for the
  session: AlwaysCaptureGamepad = 1 ORs its input in even unfocused`; no pad PASSES. The reader (a seam):
  `ctypes.WinDLL("xinput1_4")` (else `xinput1_3`, `xinput9_1_0`), `XInputGetState(slot, byref(XINPUT_STATE))`: 0 =
  connected, 1167 = not; a host with no XInput runtime PASSES ("nothing can be connected").
- **P-OVERRIDE** (critique minor #9): the fingerprint's `override70` == `override70` (4.13): exactly one stacked folder
  ships field 70's override, with that sha -- the file the warp window (4.6) and Byte[13] = 1 are proven under.
- **P-ENGINE** (rev. 2, the claim critique #9): the live `x64` and `x86` `FF9_Data/Managed/Assembly-CSharp.dll` sha256
  == `engine` (4.13): today PASS (0.3 #8).
- **P-GATE** (decision 5; rev. 2, the claim critique #9, #10): `o4_forks.json`'s `gate_witness` names a run dir that
  exists, a verdict, a cause, the `engine` its launch ran and the `settings` it recorded; PASS only when the `engine`
  equals the live DLLs' and `engine` (4.13), the `settings` equal `settings` (4.13) -- `SwordplayAssistance` 1 above
  all (at 2 the refill branch, EMinigame.cs:23-30, makes stock show 100 without the +30%, and "+30% WITNESSED" would
  name the wrong mechanism) -- and the verdict is WITNESSED, or BROKEN with cause `"bonus"` (the wrap did not fire: a
  finding the session survives, its fast play clamp-proof). BROKEN with cause `"combo"` FAILS: the fork did not credit
  proper presses, the +30% was never witnessed, and a session would only re-find it as V18 -- diagnose it first.
  INVALID, UNINFORMATIVE or none: FAIL. Red until R-GATE ran (7.4). Its detail line carries the whole witness, so the
  session's recorded preflight holds it (5.4).
- **In game** (`capabilities`): P-CAP, P-OBJECTS (the slides read Blank's published object), P-LANG (English(US)),
  P-DONOR-LOG (the launch's Memoria.log holds "[DataPatchers] Initialized" and no collision line for 64, 150, 153),
  P-LAUNCH (every stacked folder's four patch files and Memoria.ini, and -- rev. 2 -- the x64 and x86
  `Assembly-CSharp.dll`, older than the launch's first log stamp, the DLLs' sha == `engine`), P-PAD (re-sampled on the
  session's own launch).

Before the deploy, red by design: P-MANIFEST, P-DEPLOY, P-EB, P-FLOOR, P-DONOR, P-GATE (and in game P-LAUNCH until the
relaunch). Green today: P-STOCK, P-TEXT, P-RECOVERY, P-SETTINGS, P-OVERRIDE, P-ENGINE; P-PAD per the host.

### 6.3 The fingerprint (per run, before and after, as O1's)
The base's (registrations, ForkDonorPatch rows, `.eb` and walkmesh shas, stock overrides) + O2's (`override70`,
`text2`, `lang`) + O3's (`settings` over 4.13's keys, `battle_patch`, `battle_overrides`, `battle_scenes`) + O4's
`text3` (block 3 per folder per language) and -- rev. 2, the claim critique #9 -- `engine` (the x64 and x86
`Assembly-CSharp.dll` sha256). A re-wired New Game, a text deploy, a settings change, an engine rebuild (which
auto-deploys) or another session's deploy mid-session makes runs VOID (A-INSTALL), never skews them.

### 6.4 `o4_forks.json` (the implementer writes it; the lead fills `deployed_at` and `gate_witness`)
```json
{"what": "O4's fork chain: the alxc disc-1 cluster, verbatim, per-language (today's kit), --ids 64,68-69,150-151,153-167, fresh ids 31240-31259 (PLAN.md, O4). The route runs member(64) -> member(150) and ENDS in member(153): both Field()s on the route are retargeted, so the chain is closed (no seam).",
 "import": "py -m ff9mapkit import-chain 64 --verbatim --ids 64,68-69,150-151,153-167 --fresh-ids --id-base 31240 --name-prefix O4 --mod-folder FF9CustomMap --out C:/gd/_ns_playtest/o4/fork  (from ff9mapkit/, branch claude/story-trace-o4)",
 "build": "py -m ff9mapkit build-all C:/gd/_ns_playtest/o4/fork/campaign.toml --out C:/gd/_ns_playtest/o4/build",
 "deploy": "py tools/deploy_field.py C:/gd/_ns_playtest/o4/fork/<name>/<name>.field.toml --id <fork id> --name <name> --mod-folder FF9CustomMap, one member at a time, in id order (31240 first); owner-gated, after the stock rehearsals and the freeze; then ONE relaunch",
 "mod_folder": "FF9CustomMap",
 "members": {"<20 fork ids>": "<donor>"}, "names": {"<20 fork ids>": "<name>"},
 "route_members": {"31240": 64, "31243": 150, "31245": 153},
 "text_blocks": {"2": [31240, 31241, 31242], "3": [31243, "...", 31259]},
 "deployed": false, "relaunch_needed": true,
 "relaunch_why": "20 FieldScene ids and 20 ForkDonorPatch rows are read at launch only (DataPatchers.cs:107-134); P-LAUNCH proves the launch read them",
 "text_effects": {"why": "Block 2 is GLOBAL and FF9CustomMap already ships it for O1's tshp chain (31200-31219) with uk == us: the KNOWN-KIT-DEFECT line O1's and O3's P-TEXT print (uk ships stock us 3a6f3246c2; stock uk 7ac9f17435). O4's first block-2 deploy (31240) backs that copy up and writes the per-language-correct block 2, which BOTH chains then read: O1/O3's P-TEXT reads 7 byte-equal (re-baseline any doc that quotes the defect line; archived O1-O3 analyses read their recorded preflight and do not change). Block 3 has no live override: 31243's deploy writes it fresh. O3's report: rev. 1's o3_prima_vista SCOPE_LANG printed the uk clause unconditionally (o3_prima_vista.py:100-101, :1466), so every O3 session after this deploy would assert a defect its own P-TEXT no longer records; A2 derives the clause from the recorded P-TEXT lines (story-o3 and every o3_dryrun session record the defect, so G15-G17 stay byte-equal) and PLAN.md says so.",
                  "o1_block2": {"<lang>": "<sha256 of FF9CustomMap's block 2 as O1 deployed it, per language, read at C1: the one copy P-TEXT tolerates a defect in, and only before O4's deploy>"}},
 "global_side_effects": "ForkDonorPatch rows for 64, 68, 69, 150, 151 and 153-167 make ForkSiblingField resolve those donors to their members (DataPatchers.cs:102-105, :137-167) for EVERY session sharing the install: a fork-entered battle's return (HonoluluBattleMain.cs:736-737) and an overworld field entry (ff9.cs:9327) into those ids land in the member. The harness field warp and a Field() op never redirect (0.2 #14). No battle on O1-O3's routes returns into them (338 returns to 63), and no duplicate donor exists (the live duplicates are 312 and 350-359): no -1 entry appears.",
 "known_defects": [],
 "revert": {"scripts_dir": "C:\\gd\\Dream-World-IX\\tools\\scroll_out",
            "order": "reverse deploy order, 31259 down to 31240, and O4's before O1's",
            "why_order": "block 3 is written fresh by 31243 (its revert deletes it) and backed up by 31244-31259 (theirs restore it); block 2 is backed up by 31240 (O1's copy, which 31240's revert restores): out of order, a revert restores the wrong copy"},
 "deployed_at": null, "gate_witness": null, "verified": null}
```
`gate_witness`, once the lead fills it (7.4 G3): `{"run_dir", "verdict": "WITNESSED" | "BROKEN" | "INVALID" |
"UNINFORMATIVE", "cause": "bonus" | "combo" | null, "engine": {"x64", "x86"}, "settings", "s_run", "f_run", "detail"}`
-- `engine` and `settings` as R-GATE's launch recorded them (rev. 2, the claim critique #9, #10; P-GATE, 6.2).

---

## 7. Rehearsal plan (the lead runs these in game)

### 7.1 The stages (`o4_rehearse.py`: `run(g, field=None)`; `O4_STAGE=<name>` picks one by name, `--field 64` R-CHANBARA)
Each traced stage: New Game; `wait_frames(30)`; `storytrace(True)`; the raw warp; `segment_drive.drive(g,
stage_pred, side, log, end_fields=..., observe=recorder, forbid_live=True, witness=input_witness(g))`; the trace to
`rh_<stage>_<n>.jsonl`; the record into `o4_rehearsal.json`; `end_run`. Only R-FULL's traces may define or change the
keys, the start or the end state; the staged runs prove mechanics and are compared within their stage.

| Stage | When | Warp | Ends in | Runs | What it settles |
|---|---|---|---|---|---|
| **R-CHANBARA** (first: the go/no-go) | stock, before the freeze | `warp 64 100 1155` | 150 | 2 | F1-F6, F12-F15: the prompts' published `phrase_raw` and `texts`; 49/49 reading 122/123/127/128 (the eight buttons and cfg.control, in game); j per prompt and the regime; each instance's evidence and the merged stream's gaps; the gap after each hit; the tweens; T0 vs the first prompt; 127's published options and `selected`; the fight's length and the pass length; the three pairs' gates; the pages' dropped first presses; `lead_ticks`; the input witness |
| **R-FULL** (by name) | stock | `warp 64 100 1155` | 153 | 2 | F7 (end_run from 153), F8-F10: the 26 keys, the start rows, the residue, the end cut, the end state, the run time |
| **R-CHANBARA-VOID** (by name; LAST in a launch) | stock | `warp 64 100 1155`, the policy's `stop_after` 10 | V17 | 1 | F7: a V17 mid-fight stops with nothing more pressed; `end_run` (warp 4600 from the fight's FieldHUD, the ladder) reaches the title |
| **F-SMOKE** (by name; NO trace) | after the deploy and the relaunch | `warp 31240 100 1155`, `warp 31243 325 1155`, `warp 31245 325 1190`, and their stock twins | -- | 6 warps | G1: each member loads at its entrance and SC (field, FieldHUD), its Main_Init's published object sids equal its twin's after `smoke_s` (64@100 {5, 6, 13, 20}; 150@325 {2, 3, 5, 6, 9, 4}; 153@325 {3, 7, 31, 9, 11}; the twins give the measured sets), 0 exceptions through the story machinery, `end_run` ok; the Memoria.log warnings (a missing SPS is visual only) |
| **R-GATE** (by name; traced) | after F-SMOKE | S `warp 64 100 1155`, F `warp 31240 100 1155`; the PACED policy (2.4.10) | 150 / member(150) | S then F, each until informative, <= 3 attempts a side | G2: the +30% witness (7.4), with its launch's `engine` and `settings` recorded |

Default order without `O4_STAGE`: R-CHANBARA, R-FULL, R-CHANBARA-VOID (last). F-SMOKE and R-GATE run only by name,
after the deploy. Estimates a run: R-CHANBARA ~110 s, R-FULL ~200 s, R-CHANBARA-VOID ~60 s, F-SMOKE ~150 s in all,
R-GATE ~110 s. `o4_rehearse.py` reuses `o2_rehearse.Recorder` (no NPC track) and O3's shapes -- `select`,
`stage_pred` (with a `chanbara_override` merged into the draft's policy and checked by `chanbara_of`; a stage's
`end_fields` per side), `one`, `smoke` (each pair with its own entrance and SC: `[member, twin, entrance, sc]`; never
`Session.warp()`, whose wait for control 64/150/153 never grant would hang), `launch_readings` -- and adds `gate(g,
stage)`: R-GATE's side-aware runs (`SD.drive(g, spred, side, ..., witness=input_witness(g))` with the frozen members,
ends per side) and `gate_verdict`. Every summary and rehearsal reader cuts a run at `end_places(pred, side)` of the
stage's ends -- the end PLACES, never the end fields (rev. 2, the claim critique #14): O2's and O3's `trace_summary`
pass end FIELDS to `cut_at_end` (o2_alexandria.py:649-651, o3_prima_vista.py:856-858), which compares places
(segment_trace.py:126-135), so an F stage ending in member(150) (R-GATE) or member(153) would never be cut; O4's
`trace_summary` is its own and O3's shapes are called with places. The command: `py tools/play.py
studies/story-trace/o4_rehearse.py --label o4-rh --timeout 240`.

### 7.2 What every stage records
O3's record (grants -- there must be none --, pages with `timed`, the published choices, the press evidence, the
longest no-progress stretch, the end state, `end_run`'s rows) plus:
- the `zone` and `prompt` rows whole; per instance the published `texts`/`phrase_raw` (F1), `j_lo`/`j_hi` and the
  regime (F3), `evidence`, `last_listed_frame - down_frame` and `gone_frame - down_frame` in ticks, `read_gap` (F4,
  F5), the gap to the next instance in ticks, the pass length (`seen_{n+1} - seen_n`), the slide (ok / unmeasured /
  not ok, its base and end frames), `(down_frame - pre.frame) x per_frame` (F14); per zone T0 -> the first prompt
  (ticks), the fight's seconds, the merged stream's samples and `max_read_gap`, raw [lo, hi], the `input` witness
  (F15), the judge;
- each KEYON pair (105/106, 107/108, 98/99): first seen -> gone (seconds) and the Confirms pressed (F12); each page
  of the cell (111, 122, 123, 128) and 150's: the presses it took until first seen gone, and the frames from first
  seen to each press's down frame (F13: the dropped first presses, 0.3 #1);
- 127 as published at readiness (options, active, selected) and the pick (F6); the score and gil pages as published
  (F2);
- the trace through O4's `trace_summary`: the start rows, the ladder and chain rows, each registered key present or
  absent, every unregistered key, the sword rows (ip338/ip390: count, old, new, fld), the 64 -> 150 crossing, the end
  cut's row, the residue, the masked counts, the join failures;
- the launch's settings and engine, P-LAUNCH, P-DONOR-LOG, P-PAD, P-OVERRIDE and P-ENGINE readings;
- F-SMOKE: per warp the field and UI reached and when, the published object sids against the twin's, the exceptions
  and the new Memoria.log warnings, `end_run`'s result;
- R-GATE: per run its side, the judge (informative or not, and why), raw [lo, hi], the ip338 row's new value, the
  score page, the ip390 row; then the verdict and its cause, with the launch's `engine` and `settings`.

`py studies/story-trace/o4_castle.py --rehearsal-report <run dir>` prints all of it, stage by stage, run by run.

### 7.3 The freeze checklist (each item needs its evidence; the run dirs go into `rehearsals`)
- **F1 (go/no-go: the publication).** In every R-CHANBARA run each of the 49 instances was claimed by `prompt_dbtn`
  (one DBTN, `Press`, `[TIME=-1]` in `phrase_raw`), 111 by `is_zone_start`, and no dialog in the zone went unclaimed.
  The measured forms replace the FakeGame's `prompt_raw`/`prompt_text` defaults. Any other publication: STOP and
  re-design the recognizer before anything else.
- **F2 (the mapping).** Every R-CHANBARA and R-FULL run reads 49/49: the judge passes, page 122 then 123, the trace's
  ip338 0 -> 100 and ip390 0 -> 1, 127, page 128 with 10000; every TRIANGLE, CIRCLE and SQUARE instance (`menu`,
  `cancel`, `special`) and every direction instance hit (its `evidence` "closed"; no L/R slide measured and not ok,
  and in each run at least 3 of 4 L/R slides measured -- else the slide witness is too sparse to corroborate anything,
  and F4's read gaps say why). `score_page` and `gil_page` are frozen as published. A run reading 120/121 with proper
  rows: STOP -- cfg.control or the input path differs from 0.2 #6, and no session runs until it is explained.
- **F3 (j and the regime).** The `j_hi` distribution per regime; `j_cap` := min(16, max(12, 2 x the slowest `j_hi`
  seen)); every run's `raw_lo` >= 100 (else STOP: the fast premise fails; try `state_every` 1 and a tighter poll, and
  rehearse again). The j bounds checked against both publication orders' arithmetic (2.4.7) on the recorded frames.
- **F4 (the merged stream's coverage; rev. 2).** In every run no instance's `evidence` is "unobserved", and the zone's
  `max_read_gap` and every instance's `read_gap` are recorded; the gap after each hit (A - j - the tween) is
  recorded too, though no rule rests on it any more (rev. 1's live no-gap rule is gone, 2.4.3). An unobserved instance
  in a rehearsal: find the stall (the ring's `read_at` steps) before the session.
- **F5 (tweens, T0).** `gone_ticks` := max(observed `gone_frame - down_frame` in ticks) + 4 (draft 12); the close tween
  measured against 0.3's 0.09 s plus a frame (the first sample without a closed page or prompt, from its press's down
  frame); T0 -> first prompt >= 12 ticks in every run (the arm at T0+12); the 111 and 123 tweens recorded.
- **F6 (127).** The published options and `selected` (0 expected); the encore rule's `pick` matches exactly one line,
  absolute 1 ("No", or "o" when the No line too lost its first character).
- **F7 (recovery).** R-CHANBARA-VOID: V17 at instance 11 with nothing pressed after instance 10's press, `end_run`'s
  rows `recover-warp` (field 4600) then the title, and its seconds; `end_run` from 150 (R-CHANBARA) and 153 (R-FULL)
  reach the title.
- **F8 (keys).** The R-FULL traces define the predictions: per run exactly the 26 keys and the masked rows; no
  error-path, dead, forbidden or inert row; residue exactly the three start rows and none after; 64's first `w` row
  e0 t0 ip22 and its first Byte[13] row ip119 from old 1 (the first measurement in 64); the end cut 153 e0 t0 ip22;
  ip338 old 0 new 100, ip390 old 0 new 1; the two runs key for key identical; any difference explained at the byte
  level before the freeze (a new site only with O4-CENSUS's lists updated to hold it).
- **F9 (end state).** Every R-FULL `end_state` equals 4.9.
- **F10 (budgets).** `run_s` = 2 x the slowest R-FULL; `run_min_s` = 1.25 x the median; `session_s` = 8 x the median +
  1800; `no_progress_s` = max(60, 3 x the longest no-progress stretch in any traced stage); `zone_stall_s` = max(3, 3 x
  the longest gap between instances); `first_prompt_s` = max(2, 3 x the slowest T0 -> first prompt); `quiet_cap_s` =
  max(2, 3 x the slowest 123 -> 127).
- **F11 (settings and launch).** P-SETTINGS, P-PAD, P-OVERRIDE, P-ENGINE, P-LAUNCH and P-DONOR-LOG pass on the
  rehearsal launch; its fingerprinted `settings` and `engine` equal 4.13's.
- **F12 (the pairs).** Every pair closed within 8.3 s of its second window (the INCS/250 bound) and its Confirms are
  recorded; `no_progress_s` covers the slowest.
- **F13 (the pages' openings; rev. 2).** Every page of the cell (111, 122, 123, 128) and of 150 closed under page-once:
  the presses each took are recorded, the dropped first presses counted (0.3 #1 predicts 123's first press dropped in
  most runs); none took more than 3; 123's quiet window opened in every run and nothing was pressed in it.
  `page_once_ticks` := max(10, 2 x the longest measured page opening in ticks) -- a re-press must not fall into the
  opening it re-presses (a page that took its first press is gone within its tween, long before the hold-off ends).
- **F14 (the pace; rev. 2).** `lead_ticks` per render regime := the median of `(down_frame - pre.frame) x per_frame`
  over R-CHANBARA's prompt rows (2.4.10); R-GATE's `pace` takes the regime its launch runs in.
- **F15 (the input witness; rev. 2).** In every run no `input` row and the zone's `input` empty (the witness polls the
  whole run); a P-PAD WARN at the launch means the pad stays unplugged for the session.

Then `--freeze` (v1). `freeze` refuses a policy that is not `"fast"`, a `pace`, a `stop_after`, `side_ends` that fail
`side_ends_of`, a non-empty `battles`, an `engine` that is not the live DLLs' (the rehearsals' engine), or an
existing file.

### 7.4 After the freeze: the deploy, F-SMOKE, R-GATE, the session (the lead; owner-gated)
- **G0.** The deploy (6.4: one member at a time, id order, then one relaunch); `--preflight`: all green but P-GATE.
- **G1.** F-SMOKE: every member loads, its sids equal its twin's, 0 exceptions, `end_run` ok. A member that does not
  load: STOP (a chain defect, never a finding the session should discover).
- **G2.** R-GATE and its verdict (`gate_verdict(runs)`, pure): a run is INFORMATIVE when the judge finds no V17 fault
  in the paced play (49 proper rows, every one's evidence observed, `[raw_lo, raw_hi]` inside [79, 99]) -- a V18 there
  is the fork's answer, not an uninformative run. The S run must show page 122 "Of 100 nobles watching,\n100
  were impressed." and Byte[475] = 100 (the stock +30% lifted a raw 79-99 to 100) -- else **INVALID**: STOP (the
  settings or the stock bonus are not what 0.2 #11 reads). The F run then reads: Byte[475] = 100 and page 122 with 100
  -> **WITNESSED** ("the EMinigame +30% fires on member(64)"); Byte[475] = the raw (inside the run's own raw bounds) and
  page 122 with that number -> **BROKEN**, cause `"bonus"` (the wrap does not fire: a finding); pages 120/121 -- or any
  V18 the judge reads on an informative F run (a lingered press, a slide's miss) -- -> **BROKEN** too (decision 5's
  letter), cause `"combo"` (rev. 2, the claim critique #10: the fork did not credit 49 proper presses -- a V18-class
  finding about its input path, and the +30% question unanswered). No informative run on a side within 3 attempts ->
  **UNINFORMATIVE**: STOP and re-tune `pace` from the attempts' j. A BROKEN verdict is recorded and reported (PLAN.md,
  the fork-gate memory). BROKEN/`"bonus"`: the session still runs --
  its fast play's raw >= 100 is clamp-proof, and its report says the bonus is R-GATE's, broken (5.4). BROKEN/`"combo"`:
  STOP -- P-GATE fails it (6.2): the session would only re-find the fault as V18; diagnose it first. Each run's launch
  must record `settings` equal to 4.13's and the pinned `engine`, else that run is no witness (re-run on a corrected
  launch).
- **G3.** `gate_witness` filled in `o4_forks.json` (`{"run_dir", "verdict", "cause", "engine", "settings", "s_run",
  "f_run", "detail"}`, 6.4); `--preflight` all green, P-GATE included (its engine is the live one); P-LAUNCH,
  P-ENGINE and P-DONOR-LOG on the session's launch.
- **G4.** The session, unattended and hands off (no key while the game has focus, no pad -- the input witness VOIDs a
  run that sees one, V13): `py tools/play.py studies/story-trace/o4_castle.py --label story-o4 --timeout 240`.

---

## 8. The dry run (`o4_dryrun.py`: synthetic sessions through `O4.analyse`)

Built like `o3_dryrun.py`: its own `render` (the start values: SC 1155, Int16[2] 100, Byte[13] 1, every other target
0; a same-value store emitted once per site, a change up to 64 times, the rest counted), O3's event helpers (`w`,
`r`, `e`, `drop`, `after`, `before`, `edit`, `upto`) and O3's EXACT `case()` (every check a case does not name must
read PASS; a COVER-VOID case expects every core check VOID; LANDING and SWORD cases register the clause the detail
must name).
- **Real store sites** (every field row joins): 4.2-4.5's, the error-path, forbidden, dead and inert sites (150 e10 t3
  ip2119's `Byte[1034] := 0` among them), 153 e0 t0 ip22 (the end row).
- **A base run**: `arm` (fld 70); the residue (fld 70) bytes 0, 1, 2; 64's rows (start_first, Bit[184], the ambient
  four, ip416, ip425, ip475, then after the zone ip338 (0 -> 100), ip390 (0 -> 1) after 123's frame, ip331, ip528);
  150's (the six prologue rows, ip331, ip1136, ip1221, ip1255, ip1652, ip1667, ip1675, ip1683, ip1966 (SC 1155 ->
  1190), ip1974, ip2161); 153's ip22; `off` (fld 153 on S, member(153) on F). On F, 64 -> 31240, 150 -> 31243, 153 ->
  31245.
- **A log**: the visit rows; the zone row (start_page with last_with/first_without frames, first prompt at T0+13
  ticks, end at 107's frame, `samples`, `max_read_gap` {frames 2, ticks 1, s 0.05}, `input` [], `slides`, the judge
  None); 49 prompt rows (seeded DBTNs drawn with the e20 filters, at 60 fps: `prev` = seen - 2, `accepted` = seen + 3,
  down = seen + 4, `ack` = seen + 7, `last_listed` = down + 8, gone = down + 10 -- `evidence` "closed" (mark = down + 24
  frames); `rate` {fps 59.9, fps_lo 59.5, fps_hi 60.4, tick_hz 30, source "mtime"}, `excess` 0; so `j_bounds` gives
  [1, 5] (`ticks_sure(4 - 1)` = floor(3 x 30 / 60.4) = 1, `ticks_most(6)` + 1 = ceil(6 x 30 / 59.5) + 1 = 5) and
  `raw_bounds` [119, 126]; `x_prev`/`x_seen` such that every L/R slide is measured and ok, the tail jointly); their
  `press` rows; the page presses (111 once, 122, 123 twice -- the first dropped in its opening, 0.3 #1 --, 128, 150's)
  with `seq`, frames and texts; the encore choice row (options ['They demand an encore!\nPerform the fight scene
  again?', 'es', 'No'], selected 0, index 1) and its `choose` press rows (down, confirm); the end row (field 153 /
  31245); `end_state` (4.9); the outcome's pages (111, 122's and 123's texts, 128's, 150's), beats `{"sword": true,
  "encore": true}`, zones, prompts.

| Case | Want |
|---|---|
| null-pair | PROVEN |
| fork-drops-a-write (no 150 ip1683 on F) | NOT PROVEN (WRITES F, NULL F, STATE F) |
| ladder-missing-fork (no 150 ip1966 on F) | NOT PROVEN (LADDER F, WRITES F, NULL F, STATE F) |
| ladder-old-wrong (both: ip1966's old 1154) | NOT PROVEN (LADDER F alone) |
| sc-write-fork (F: a `cs` UInt16[0] := 1190 row in 64 after ip475) | NOT PROVEN (LADDER F, WRITES F, NULL F, STATE F) |
| sc-write-both (the same on both sides) | NOT PROVEN (LADDER F, WRITES F; NULL P) |
| sc-harness-poke-both (every run: a `src: harness` Byte[0] row in 150 after ip1966) | NOT PROVEN (LADDER F alone) |
| chain-dropped-fork (no 64 ip528 on F) | NOT PROVEN (CHAIN F, LANDING F (b), WRITES F, NULL F, STATE F) |
| chain-first-old-wrong (both: ip528's old 101) | NOT PROVEN (CHAIN F alone) |
| start-residue-wrong (S: byte 2 0 -> 101) | NOT PROVEN (START F) |
| start-first-missing (both: 64 ip22 dropped) | NOT PROVEN (START F; NULL P: masked) |
| start-music-old-wrong (both: 64 ip119's old 3) | NOT PROVEN (START F) |
| front-cut-write (F: a `w` row in fld 70 before the start) | NOT PROVEN (START F) |
| error-path-start-S (one S run: 64 ip97 for ip119, stopped at window 3; V5 driver [64, 1155]) | PROVEN (S 2 of 3); the run's classes include V5 and A-START |
| error-path-150-F (one F run: 150 ip101, stopped at window 56; V5 game [150, 1155]) | NOT PROVEN (VOID-ASYM F) |
| residue-after-start (F: an `r` row on byte 300) | NOT PROVEN (RESIDUE F) |
| writes-extra-symmetric (both: 150 ip1277 `++` (2) after ip1255) | NOT PROVEN (WRITES F; NULL P) |
| inert-row-both (both: 150 e10 t3 ip2119 Byte[1034] := 0) | NOT PROVEN (WRITES F; NULL P) |
| byte475-93-every-F (every F run: ip338 := 93, page "93 were impressed.", end state Byte[475] 93) | NOT PROVEN (WRITES F, NULL F, STATE F, SWORD F (a)(b)) |
| bit3815-missing-F (every F run: no ip390 row; end state Bit[3815] 0) | NOT PROVEN (WRITES F, NULL F, STATE F, SWORD F (a)) |
| sword-second-390-both (every run: a second ip390 row, 1 -> 1) | NOT PROVEN (SWORD F (a) alone) |
| sword-page-120-both (every run's pages: 120's and 121's texts) | NOT PROVEN (SWORD F (b) alone) |
| sword-yes-both (every run's encore row: index 0) | NOT PROVEN (SWORD F (c) alone) |
| sword-gil-page-both (every run's 128: "They shower you with 9999 Gil!") | NOT PROVEN (SWORD F (d) alone) |
| sword-48-prompts-both (every run's log: 48 prompt rows) | NOT PROVEN (SWORD F (e) alone) |
| sword-circle-alias-both (every run: a CIRCLE instance pressed `circle`) | NOT PROVEN (SWORD F (e) alone) |
| sword-j-over-cap-both (every run: one instance's frames give `j_hi` 30) | NOT PROVEN (SWORD F (e) alone) |
| sword-evidence-before-both (every run: one instance's window gone at a sample before its down frame) | NOT PROVEN (SWORD F (e) alone) |
| sword-evidence-lingered-both (every run: one proper instance listed at down + 30 frames) | NOT PROVEN (SWORD F (e) alone) |
| sword-evidence-unobserved-both (every run: one instance's samples jump from down + 2 to down + 40 frames, neither listing it after) | NOT PROVEN (SWORD F (e) alone) |
| sword-slide-not-ok-both (every run: an L/R instance measured, dx 0) | NOT PROVEN (SWORD F (e) alone) |
| sword-slide-unmeasured-both (every run: two L/R instances' base samples too close to their predecessor's seen) | PROVEN (the slides counted unmeasured, none not ok) |
| sword-input-noise-both (every run's zone: an `input` entry) | NOT PROVEN (SWORD F (e) alone) |
| sword-stray-press-both (every run: a page press row whose down frame lies between instance 1's `prev_frame` and the zone end) | NOT PROVEN (SWORD F (f) alone) |
| sword-111-closing-press-late-both (every run: 111's press goes down after `start_page.last_with_frame`, before instance 1's `prev_frame`) | PROVEN (rev. 1's boundary flagged it) |
| v17-one-S (one S run VOID V17 driver at [64, 1155], its rows up to the fight) | PROVEN (S 2 of 3; VOID-ASYM P) |
| v17-all-F (every F run VOID V17 driver) | NOT PROVEN (VOID-ASYM F (b); COVER V) |
| v18-one-F (one F run VOID V18 game at [64, 1155]) | NOT PROVEN (VOID-ASYM F (a)(c)) |
| v18-one-each-side (one S and one F run VOID V18) | NOT PROVEN (VOID-ASYM F (c) alone) |
| v19-one-F (one F run VOID V19 game at [153, 1190]; its last rows real 153's, cut away as place 153) | NOT PROVEN (VOID-ASYM F (a)(c)) |
| leak-real-150-F (one F run VOID V19 game at [150, 1155]; its rows at fld 150) | NOT PROVEN (FORBIDDEN F, VOID-ASYM F) |
| control-S (one S run VOID V4 game at [150, 1155]) | NOT PROVEN (VOID-ASYM F (a)) |
| observed-unclaimed-one-F (one F run VOID V17 driver at [64, 1155] with an `observed` row: an unclaimed dialog in the zone) | NOT PROVEN (VOID-ASYM F (d) alone) |
| observed-unclaimed-one-each-side (one S and one F run, the same `observed` kind and cell) | PROVEN (S 2 of 3, F 2 of 3; VOID-ASYM P) |
| v13-input-one-F (one F run VOID V13 driver: outside input in the zone) | PROVEN (F 2 of 3; VOID-ASYM P: an instrument stop, never a finding) |
| stray-yes-driver-S (one S run VOID V17 driver at [64, 1155]: a page press after 127's first frame) | PROVEN (S 2 of 3) |
| extra-key-one-F (one F run of three: 150 ip1277's `++` after ip1255) | NOT PROVEN (STABLE F, WRITES F, STATE F; NULL P) |
| lands-real-150-covered (every F run: 150's rows at fld 150, the drive reached) | NOT PROVEN (LANDING F (a)(b)(e), FORBIDDEN F, WRITES F; NULL P -- a seam leak is invisible to it) |
| 64-after-150-both (every run: a second 64 e0 t0 ip119 row after 150's ip26) | NOT PROVEN (LANDING F (b) alone) |
| last-place-harness-both (every run: a harness Byte[300] row in 150 after ip2161) | NOT PROVEN (LANDING F (c) alone) |
| end-log-row-real-153-F (every F run's synthetic `end` log row names field 153; the trace cut at member(153)) | NOT PROVEN (LANDING F (c) alone) |
| end-real-153-F (every F run: the cut row at fld 153; `off` in member(153)) | NOT PROVEN (LANDING F (d) alone) |
| end-boundary-residue-both (every run: an `r` row in place 153 before its ip22) | NOT PROVEN (LANDING F (d) alone) |
| end-row-missing-one-S (one S run: no row in 153, `off` in 153) | PROVEN (S 2 of 3); that run A-NOEND |
| sword-beat-missing (two S runs: beats `{"sword": false}`) | VOID (COVER V; VOID-ASYM P) |
| end-cut (S: rows in 153 past the end) | PROVEN |
| end-state-differs (one covered F run: Byte[303] 0) | NOT PROVEN (STATE F) |
| masked-differs (every F run without its Bit[184] rows) | NOT PROVEN (MASKED F) |
| mismatched (one F run's member rows name another donor) | PROVEN; that run A-MISMATCH |
| no-start-row (one S run never reaches 64) | PROVEN; that run A-NOSTART |
| join-failure (both: an extra row at 150 e3 t1 ip1684, its ip1683 kept) | NOT PROVEN (JOIN F alone) |
| trace-without-off | VOID |
| install-changed | VOID |
| predictions-changed | NOT PROVEN (FROZEN F) |

A case's want that the code cannot hold (a co-failure the table did not foresee) is explained at the byte level and
re-registered, never loosened silently (O3 11.6 #8, #9 did this twice).

Units (no session):
- **chanbara-policy**: `chanbara_of` passes 4.10's draft and the paced overlay; raises on each of: an unknown key, a
  missing one, `buttons` with `circle` for CIRCLE (the refusal names Control.Confirm), any other map, `j_cap` 17 under
  fast, a `raw_floor` under paced, a `pace` under fast, `press_frames` 0, `stop_after` 49, a bool for an int.
- **prompt-shape**: `prompt_dbtn` on the eight prompt forms (each its DBTN); on 111 (eight tags): None and
  `is_zone_start` True; on 150's window 55 (two tags, no `Press`): None; a prompt without `[TIME=-1]`: None; `texts`
  "Press  !" alone: None.
- **j-bounds**: `j_bounds` at 60 and 31 fps (a row's frames and rate -> the expected [lo, hi]); a hitch's `excess` raises
  `j_hi`; `raw_bounds` on uniform j reproduces the table j1 126, j5 119, j10 111, j16 100, j17 99, j20 93, j28 80, j29
  78; the SA 1 display (79 -> 100, 78 -> 99). Rev. 2 (both orders): synthetic frame-tick schedules at 31 and 60 fps
  with +-5% frame jitter, the arm tick and the edge placed by each publication order's rule (2.4.7) -- the true j
  lies in [j_lo, j_hi] for every one; rev. 1's `j_lo` (`ticks_sure(down - seen)`) overstates a jittered agent-last
  case (the unit's mutant), and `j_hi` with the critics' extra frame is sound but a frame wider (recorded, not used).
- **judge**: `chanbara_judge` -- proper rows: None; proper rows but one instance at `j_hi` 45: V17 (j over the cap);
  proper rows and a score page "99 were impressed." in two samples: V18; one sample of "[NUMB=0] were impressed."
  then "100 were impressed.": None; `evidence` "lingered" on a proper press: V18; "unobserved" (a 0.5-s read stall
  from the press's ack: the first sample without past the mark, none listing it at or past it): V17, NEVER V18 (the
  claim critique #2's case); "before": V17; a proper L/R press with its measured slide 0: V18; a measured slide of
  -240: V17 (the witness's samples); a wrong name, a double press, a missing event: V17 each; 48 instances with a
  60-tick read gap: V17, with none above 50 ticks: V18; 50 instances: V18; paced raw [80, 92]: None; paced raw
  [76, 85]: V17 "uninformative"; a fast policy with `raw_floor` 110 and every `j_hi` 12 (each within the cap, raw_lo
  107): V17 (the raw floor -- unreachable at the draft's 16 and 100, 5.3 (e)).
- **slides** (rev. 2): at ~31 fps with the agent-first publication, a synthetic L/R run whose first samples listing
  each prompt show one or two slide steps -- rev. 1's baseline (`x_seen` of the next instance) reads -240 on about half
  the L/R instances and its end catches the next slide's steps (the unit's mutant: not ok), rev. 2's (`prev` samples,
  2.4.6) reads -300 on all; a base sample under 7 sure ticks after its predecessor's `seen_frame`: "unmeasured"; the
  tail (48 LEFT, 49 LEFT): joint want -600 from instance 49's `prev` to the zone end; (48 RIGHT, 49 LEFT): "unmeasured".
- **stray-answer** (rev. 2): a page press whose down frame lies in [127's first frame, its close): V17; `choose`'s
  confirm with the last sample before its down frame publishing `selected` 0: V17; with `selected` 1: excluded, V2; a
  prompt press long before 127: ignored, V2; none: V2.
- **gate-verdict**: S 100 + F 100: WITNESSED; F Byte[475] 90 with page "90 were impressed.": BROKEN, cause "bonus"; F
  pages 120/121, or an informative F run whose judge reads V18 (a lingered press): BROKEN, cause "combo"; S page
  "93": INVALID; an out-of-band run, or one with an "unobserved" instance, on each side three times: UNINFORMATIVE; a
  run whose launch recorded SwordplayAssistance 2 or another engine: no witness (re-run).
- **trace-summary**: O4's `trace_summary` of a base S run: the ladder 1/1, the chain 2/2, writes 23/23, the sword rows,
  the crossing 64 ip528 -> 150 e0 t0 ip26, the end cut's row 153 e0 t0 ip22, no unregistered key, no join failure, the
  three start residue rows. Rev. 2 (the claim critique #14): an F stage ending in member(150) (R-GATE's shape) is cut
  at member(150)'s first row by `end_places`; the same summary given the end FIELDS (rev. 1's call, O2/O3's shape) is
  not cut at all (the unit's mutant).
- **state-history**: Byte[8]'s history `[(64, 125), (64, 0), (150, 25), (150, 75)]`; Byte[475]'s `[(64, 0), (64, 100)]`;
  Bit[3815]'s `[(64, 0), (64, 1)]`.
- **p-donor-log**, **p-launch**: O3's units with O4's donors (64, 150, 153) and files.
- **p-pad**: a stub reader -- no pad: PASS; an idle pad at slot 2: PASS with the WARN line; a pressed A: FAIL; a trigger
  at 40: FAIL; a thumb at 4000: FAIL; no XInput runtime: PASS.
- **p-override**: the pinned sha: PASS; another sha, two folders shipping field 70, none: FAIL each.
- **p-settings**: SwordplayAssistance 2, FieldTPS 60, SwapConfirmCancel 1, AlwaysCaptureGamepad 0: FAIL naming each; a
  later duplicate assignment wins.
- **p-gate** (rev. 2): no `gate_witness`, UNINFORMATIVE, INVALID, a missing run dir, BROKEN with cause "combo", an
  `engine` other than the live DLLs', `settings` with SwordplayAssistance 2: FAIL each; WITNESSED, or BROKEN with cause
  "bonus", with its run dir, the live engine and 4.13's settings: PASS.
- **p-engine** (rev. 2): the pinned sha on both DLLs: PASS; another sha, or x86 differing from x64: FAIL each.
- **text-strict** (rev. 2, the claim critique #12): block 3's uk equal to stock us -- `text_rule` alone reads it a
  KNOWN-KIT-DEFECT and passes, `strict_text` (O4-TEXT) FAILS; P-TEXT on block 2 with O1's copy (its shas
  `o1_block2`) and no O4 member registered: PASS with the named line; the same copy with an O4 member registered:
  FAIL; another defect copy before the deploy: FAIL.
- **input-witness** (rev. 2): stub readers -- a pad button at slot 1: non-neutral (pad); a trigger at 40, a thumb at
  4000: non-neutral; a key down with the game focused: non-neutral (key); the same key unfocused: neutral; F1
  focused: non-neutral; a slot found disconnected polled at most once a second.
- **store-census**: O4-CENSUS on the install: PASS with 6.1's line; mutants each FAIL by name -- `dead` without 64
  ip41; `inert` without 23; `error_path` without 150 ip1009; an `inert` entry 3 (instanced at 325: the proof fails).
- **build-pins**: O4-BUILD's pins on a synthetic two-member build (a `stock_lang` seam): an extra byte changed in
  member(64)'s e4 t1: FAIL; a `PreloadField` operand remapped: FAIL; an in-chain `Field()` left unremapped: FAIL.
- **fight-pins**: O4-KEYS (b) on the install: PASS; a pin's text changed (`const(51)` for TimeLeft): FAIL; `prompt_mes`
  118 -> "CROSS": FAIL.
- **offline mutants** (each FAIL by its clause after all read PASS on the draft): KEYS -- a write's value (UInt16[21] 2),
  a `++` prior unknown, the `:=var` key's rvalue (`Map.Int16[47]`), a chain `off` + 1, `start_first`'s target, a dead
  site's value (64 ip130 `Byte[13]` 2), `start_music` at ip138.
(O3's derived language clause is tested in PART A, A2, where its edit lands.)

It prints O3's summary columns for O4's checks (FROZEN COVER FORBIDDEN VOID-ASYM START LADDER CHAIN RESIDUE WRITES NULL
STABLE LANDING SWORD MASKED STATE JOIN) and "N/N cases as registered", exiting 1 on any miss.

---

## 9. Build order (three parts; no deploy, no game, no `tools/play.py`, no full suite)

Run pytest from `ff9mapkit/`, the study scripts from the worktree root. The harness tests run in REAL TIME (the
FakeGame loops on a thread, at its default loop `fps` 240: a whole 64 visit -- the pairs, 111, the 49-prompt fight,
the pages -- is about 70 virtual seconds at `render_fps` 60, about 18 wall seconds): run the named `-k` selections,
never many at once, and the whole file only where a PART says so, alone. A fight test keeps the loop at most 4x its
`render_fps` (`fps` 240 at 60, 124 at 31): the driver's wall latency reaches the fight multiplied by that compression,
in ticks, and its j must stay under `j_cap` as in the game (a slow host halves the compression; the judge is the same). A SKIPPED test is not a pass: every required
pytest run reports 0 failed, and its skips and xfails are exactly the PART's baseline's (taken before the PART's first
change); a skip for missing templates is fixed with `py -m ff9mapkit extract-templates` (read-only on the install)
and the run repeated. A failure that passes on an immediate re-run of that test alone is a timing flake: named in the
commit message, never ignored. Commit on the branch when a step is green, one step per commit, each message ending
with "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". Write non-ASCII files with Python (utf-8) or the
Edit/Write tools; frozen JSON and baselines are LF (`-text`). Nothing in PARTs A-C writes to the install, deploys,
launches the game or runs `tools/play.py`: the rehearsals, the freeze, the deploy, F-SMOKE, R-GATE and the session
are the lead's (7.4).

### PART A -- the regression gate extended to O3 (baseline and source pins FIRST), then per-side ends, then O3's language clause
1. **A0: the O3 gate and its baseline, FIRST.** Extend `segment_regress.py` (1.4: G15-G18 and `--capture-o3` with its
   two-readings rule; rev. 2: G21, the `sources` pins in the capture and `--rebaseline-source`; `REQUIRED_TESTS_O4`
   empty; `_missing()` gains O3S's session and report, V1_O3, the baseline and `source_pins.json`; the module docstring
   gains G0'', G15-G18 and G21, and says G17 is O3's VOID-path baseline) with
   `test_segment_regress_source_pins_catch_an_edit` (pure: G21's checker over a temporary copy -- a pinned test's body
   edited FAILS naming it, a comment-only edit passes, a re-baseline row with a reason passes, an empty reason and a
   stale `old` are refused; into `REQUIRED_TESTS`). Write `research/source_pins.json` as `[]`, run `py
   studies/story-trace/segment_regress.py --capture-o3`, and commit it with `research/o3_regress_baseline.json`, the
   pins file and their `.gitattributes` lines before any other code change. Then `py
   studies/story-trace/segment_regress.py` reads G1-G18 and G21.
2. **A1: S6** -- `segment_trace.side_ends_of`, `side_ends`, `end_places`; `Segment.cut` on the side's end places;
   `O2Segment.why_void`'s one line; `_Drive.__init__`'s `ends` and `end_places`, `scan()` and `end_row()` on the
   places, rule 2's V19 under `side_ends` -- with `test_segment_side_ends_split_the_cut_and_the_drive` and
   `test_segment_drive_ends_per_side_on_the_fake` (1.2), both into `REQUIRED_TESTS`. Break for the second: compare
   raw ids in `end_row()` (a member(153) arrival never cuts).
3. **A2: O3's language clause from the record** (rev. 2, the claim critique #13) -- `o3_prima_vista.py`'s one edit:
   `report_extra`'s language line reads the session's recorded P-TEXT rows (`session["preflight"]`, `defect_lines`):
   when they hold the block-2 uk KNOWN-KIT-DEFECT line, or when no P-TEXT row is recorded, it prints rev. 1's
   `SCOPE_LANG` unchanged; when P-TEXT rows are recorded with no block-2 defect, it prints "a US session (P-LANG): the
   members' jp/fr/gr/it/es .eb are US bytecode (accept_us_build); block 2's copies are each their own language's stock
   text (P-TEXT)". story-o3 records the defect line and every o3_dryrun session records it too (o3_dryrun.py:327), so
   G15, G16 and G17 hold the edit byte-neutral; G21 pins no o3_prima_vista function (only tests and the fake). With
   `test_segment_o3_scope_lang_reads_the_recorded_p_text` (a synthetic O3 session each way and one with no P-TEXT;
   into `REQUIRED_TESTS`). Break: print the defect clause unconditionally (rev. 1).

**PART A REQUIRED-GREEN** (after A0, and again after A1 and A2):

| Command | Expected |
|---|---|
| `py studies/story-trace/segment_regress.py` | exit 0; G1-G18 and G21 each PASS (G21: no pinned source changed, `source_pins.json` still `[]`) |
| `py studies/story-trace/o1_dryrun.py` | exit 0; "16/16 cases as registered" |
| `py studies/story-trace/o2_dryrun.py --predictions studies/story-trace/o2_predictions_v1.json` | exit 0; "86/86 cases as registered" |
| `py studies/story-trace/o3_dryrun.py --predictions studies/story-trace/o3_predictions_v1.json` | exit 0; "102/102 cases as registered" |
| `py studies/story-trace/o3_prima_vista.py --analyse C:\gd\Dream-World-IX\.harness-runs\20261001-095552-story-o3 --predictions studies/story-trace/o3_predictions_v1.json` | exit 0; `VERDICT: PROVEN`; the archived `o3_report.txt` byte for byte |
| `py studies/story-trace/o3_prima_vista.py --offline-check` | exit 0; 6 PASS as 0.2 #9 |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "segment or o3_drive or o3_skip_ab"` | all passed, 0 failed, 0 skipped (A0's source-pin test among them, A1's two after A1, A2's one after A2) |

### PART B -- the FakeGame fight, then the Chanbara policy in `segment_drive`
1. **B0:** the PART's baseline of the whole `tests/test_harness.py` (passed / xfailed / skipped), run alone, from this
   worktree with the field manifest present and the templates extracted. Expected: master's "694 passed, 1 xfailed"
   (5d1b95a6) plus A0's one, A1's two and A2's one; any other count is explained before B1.
2. **B1: H10, H11, H12** (`fakegame.py`: `CONTROL_BITS`, the per-frame level and edge model used ONLY inside the two
   new beats, the `keyon_pair` beat, the `chanbara` visit beat with every knob of section 3 -- the pages' open and close
   times, the per-tick slides, `publish_order`, `chanbara_log` --, the fault knobs) + the thirteen fake tests of
   section 3, each with its break. No existing test's fake changes: the beats are opt-in, and G21 holds the existing
   beat and input functions to their A0 shas -- one that must change to host the new beats (a dispatch line in
   `_step_scene`, `_scene_press` or `_publish`) is re-baselined by name with its reason (`--rebaseline-source`) in the
   same commit, and the commit message names it.
3. **B2: the pure half of S7** in `segment_drive`: `DBTN_CONTROL`, `chanbara_of`, `prompt_dbtn`, `is_zone_start`,
   `is_zone_end`, `j_bounds`, `raw_bounds`, the per-instance `evidence` and the `slide` measure (pure over a row set and
   its merged samples), `chanbara_judge`, `stray_answer`. Tests (pure, no fake):
   - `test_o4_chanbara_of_is_strict` -- 4.10's draft and the paced overlay pass; each refusal of 4.10 raises once,
     the `circle` one naming Control.Confirm; `input_every_s` 0.2 and `ring_every_s` 8 refused. Break: accept the
     `circle` alias.
   - `test_o4_prompt_recognizers_claim_exactly_the_prompts` -- section 8's prompt-shape unit. Break: read `texts`.
   - `test_o4_j_and_raw_bounds` -- section 8's j-bounds unit, the uniform-j table, the SA 1 display, both publication
     orders against the true j. Break: rev. 1's `j_lo` (`ticks_sure(down - seen)`): a jittered agent-last case
     overstates.
   - `test_o4_chanbara_judge_classes` -- section 8's judge unit, every line. Break: rate an "unobserved" instance V18
     (rev. 1's negative evidence).
   - `test_o4_slides_bracket_the_slide_from_the_prev_samples` (rev. 2) -- section 8's slides unit. Break: measure
     from the next instance's `x_seen` (rev. 1).
   - `test_o4_stray_answer_attributes_by_the_down_frame` -- section 8's stray-answer unit. Break: compare the press's
     send time instead of its down frame; or leave out `choose`'s presses.
4. **B3: the executor** -- rule 6b and `_Drive.chanbara_zone` (Z0-Z3, the merged stream, the tight loop with its
   witness and UI steps and the `closing` tracker, the rows, the j and raw bounds, the evidence and the slides joined
   at Z3, the VOIDs), `drive`'s `witness` keyword, V17/V18 in the V table, the `observed` rows, S8 (the DBTN refusal,
   page-once per window, the quiet windows), S9 (the score and gil pages on two samples, the encore attribution,
   `choose`'s presses rowed), the pace option, `out()`/`progress`'s `zones` and `prompts`. Tests on the fake (H11 at
   the fixture's 30820 as "64", `exit_to` 30821 as "150", the run ending on arrival there -- R-CHANBARA's shape; F-side
   members appended to the fixture's DictionaryPatch as O1's pinning test does; `publish_order` "agent_first" unless a
   test says otherwise):
   - `test_o4_drive_scores_100_on_the_fake` -- at `render_fps` 60 (mean ticks, loop `fps` 240) and at 31 (`ticks`
     "quantized", loop `fps` 124): 105/106 closed after their gate by page-once; 111 pressed until it closed; 49 prompt
     rows, each pressed once with its mapped button, every `j_hi` <= 16, raw_lo >= 100, every `evidence` "closed", the
     judge None; 122 == `score_page`, then 123 pressed until gone (its first press usually dropped in its opening),
     nothing pressed from 123's going until 127; 127 answered No by `g.choose(1)`, `choose`'s presses rowed; 128 ==
     `gil_page`; the trace's ip338 0 -> 100 before 122 and ip390 0 -> 1 after 123; beats `{"sword": true, "encore":
     true}`; the end reached. Break: drop rule 6b (the prompts fall to rule 7's Confirm: 7 of 8 miss).
   - `test_o4_drive_opens_one_instance_beside_a_lingering_prompt` -- a stalled press on instance 3 (the test wraps
     `g.press`): the timeout re-arms in its tick, the old prompt listed beside the new one; the tracker opens exactly
     instance 4 (`prev_kind` "dbtn", 3 into `closing`), instance 3's evidence is not "closed", and the run stops V17.
     Break: open an instance per listed DBTN.
   - `test_o4_drive_paced_tracks_the_closing_prompt_beside_its_successor` (rev. 2, the driver critique #2, the claim
     critique #3) -- paced, `target_ticks` 22 (j ~23-25) against `reaction` 28 and 30, and again with reactions of j +
     2 and j - 2: exactly 49 instances, every `evidence` "closed", the run informative. Break: track instances on D
     without `closing` (the closing DBTN reopens as a phantom instance: V17).
   - `test_o4_drive_fails_closed_on_an_unclaimed_dialog` -- `prompt_raw` without `[TIME=-1]`: V17 at the first prompt,
     nothing pressed after 111's Confirm, an `observed` row; a page injected in Z2: V17, an `observed` row. Break: let
     rule 7 page it.
   - `test_o4_drive_refuses_an_unrecognized_dbtn_page` (rev. 2, the driver critique #11) -- 111 and the prompts in a
     form neither recognizer claims (an extra tag before `Press`): V17 at 111 with nothing pressed and an `observed` row.
     Break: let rule 7 press a `[DBTN=` page.
   - `test_o4_drive_v17_on_a_stalled_press` -- a 2.5 s stall on instance 5: V17 (driver), the zone row's faults name
     instance 5, nothing pressed after. Break: judge a stall as V18.
   - `test_o4_drive_read_stall_in_a_gap_is_v17_never_v18` (rev. 2, the driver critique #4, the claim critique #2) -- a
     0.5-s READ stall (a wrapped `g.state`) right after instance 9's press returns: instance 9's evidence "unobserved",
     V17 "instrument: a read gap ...", never V18. Break: rate a missing gap sample as V18 (rev. 1's live no-gap rule).
   - `test_o4_drive_v18_on_a_lost_press` -- `lost` {7}: V18 (game) once instance 7 is listed past its mark, cell
     [64, 1155], nothing re-pressed. Break: re-press a lingering prompt.
   - `test_o4_drive_v18_on_a_miss_read` (rev. 2) -- `miss_read` {an L/R instance}: its evidence "closed", its slide
     measured 0, V18 at Z3 before the score page. Break: ignore the slides.
   - `test_o4_drive_v18_on_what_the_game_shows` -- `score_override` 87: the play proven, page "87 were impressed." in
     two samples -> V18 with nothing pressed on it; `extra_prompts` 1 -> V18 at instance 50; `unsubstituted_once`: no
     stop (the first sample alone is never read as the page). Break: check only the trace; or read one sample.
   - `test_o4_drive_slides_at_31_fps_agent_first` (rev. 2, the driver critique #3, the claim critique #1) -- quantized
     31 fps, "agent_first": no slide not ok, at least 3 of 4 measured. Break: measure from `x_seen` (about half the
     L/R slides read -240).
   - `test_o4_drive_page_once_and_the_quiet_windows` -- 105/106 with `gates` 40: its Confirms at least
     `page_once_ticks` apart until both close, keyed per window; 111 pressed until gone; a page injected between 123's
     going and 127: V17 with an `observed` row. Break: page-once off.
   - `test_o4_drive_presses_123_again_when_its_first_press_is_dropped` (rev. 2, the driver critique #1, the claim
     critique #6) -- H11's page `open_s` on, 123's first press landing in its opening: 123 is pressed again
     `page_once_ticks` later, the quiet window opens at the first sample without it, 127 comes and is answered No.
     Break: open the quiet window at the press (rev. 1: V14 after `quiet_cap_s`).
   - `test_o4_drive_attributes_a_stray_yes` -- a mutant driver's Confirm landing after 127's first publication: the
     replay -> V17 (driver), never the fight judge; `replay_on_no` with no stray Confirm: V2 (game); `choose`'s presses
     in the log as rows with their seqs. Break: V2 always; or send a replay page to the fight judge.
   - `test_o4_drive_paced_policy_lands_in_its_band` -- paced, `target_ticks` 22: the judge None, raw in [79, 99];
     `bonus_fires` True: page 122 with 100; False: V18 at the score page with ip338's row = the raw; and with
     `render_fps` switched 60 -> 31 mid-fight, j stays in band. Break: pace by `ticks_sure` of the frames (rev. 1: j ~40
     after the switch, V17).
   - `test_o4_drive_stops_v13_off_fieldhud` (rev. 2, the driver critique #9) -- `menu_on_triangle`: V13 at the first
     TRIANGLE instance's next sample, nothing pressed after. Break: ignore `ui_state`.
   - `test_o4_drive_input_witness_stops_v13` (rev. 2, the claim critique #4) -- a stub witness reporting a pad button at
     instance 20: V13, the zone's `input` entry, nothing more pressed. Break: ignore the witness.
   - `test_o4_drive_never_blocks_on_the_rate` (rev. 2, the driver critique #6) -- `g.rate(require=True)` wrapped to
     raise: the fight runs and every row records `g.rate()`. Break: require the rate at Z0.
   - `test_o4_drive_stop_after_ends_at_instance_eleven` -- `stop_after` 10: V17 when instance 11 opens, no press
     after instance 10's. Break: count presses instead of instances.
   - `test_o4_drive_prompt_outside_its_cell_is_v17` -- a prompt-shaped page at SC 1190: V17, nothing pressed, an
     `observed` row. Break: drop the cell test.
   In this commit every `test_o4_*`, `test_fake_chanbara_*` and `test_fake_keyon_*` name goes into
   `REQUIRED_TESTS_O4` and G19 joins the gate (1.4).
5. **B4:** `test_o3_drive_pages_a_prompt_without_the_chanbara_policy` -- O3-shaped predictions (no `chanbara`): a
   prompt-shaped page is pressed by rule 7 exactly as today (a `press` row `why` "page"; no `zone` or `prompt` row;
   `out()` without `zones`/`prompts`). Into `REQUIRED_TESTS_O3` (G13's selection). Break: run rule 6b without the
   policy.

**PART B REQUIRED-GREEN:**

| When | Command | Expected |
|---|---|---|
| B0, and after B4 | `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore` (alone) | after B4: B0's counts + every new test passed, B0's xfails, 0 skipped, 0 failed |
| after B1 | `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "fake_chanbara or fake_keyon"` | 13 passed, 0 failed, 0 skipped |
| after B1, B2, B3, B4 | `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o1_ or o2_ or o3_ or segment or fake_"` | all passed, 0 failed, 0 skipped |
| after B2, B3 | `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o4_"` | B2: 6 passed; B3: 26 passed; 0 failed, 0 skipped |
| after every B step | `py studies/story-trace/segment_regress.py` | exit 0; G1-G18 and G21 each PASS (G21: every re-baseline row named in its commit), and G19 from B3 (`REQUIRED_TESTS_O3` holding B4's test from B4) |

### PART C -- O4 itself
1. **C0: the chain, outside the repo and the install.** From `ff9mapkit/` on this branch, decision 3's `import-chain`
   and `build-all` (0.1). Read `campaign.toml`: member(64) 31240, member(150) 31243, member(153) 31245 -- anything
   else STOPS PART C until the predictions are re-derived from it. Re-read the live registrations first (31240-31259
   still free) and take the sha256 of every stacked folder's DictionaryPatch.txt, ForkDonorPatch.txt and BattlePatch.txt
   and of the live text blocks 2 and 3 before and after: they must be equal (the import and build wrote nothing to
   the install). The build holds 140 `.eb` files. Measure O4-BUILD's diff set on it (6.1) before C1, and O4-TEXT
   strict on it (a KNOWN-KIT-DEFECT line: `tools/refresh_verbatim_text.py` and a rebuild, then measure again). Nothing
   is deployed; no commit (both directories are outside the repo); C1's `o4_forks.json` records the commands, the ids
   and the shas.
2. **C1: `o4_castle.py`** (1.3, sections 4-6: the draft, the checks, LANDING, SWORD, VOID-ASYM (c) and (d), the
   offline checks with the pins, strict O4-TEXT and O4's census, the preflight extras with P-ENGINE and P-GATE's
   engine/settings/cause, P-PAD's ctypes reader and the input witness's readers behind their seams, `trace_summary` on
   end places, `gate_verdict` with its cause, the CLI), **`o4_forks.json`** (6.4: `text_effects.o1_block2` read from
   the live FF9CustomMap, read-only) and the `.gitattributes` line for `o4_predictions*.json`. Tests:
   - `test_o4_castle_draft_reads_the_chain_from_campaign` -- a synthetic `campaign.toml`: members and names derived,
     member(64)/(150)/(153) printed; a missing or an extra donor raises.
   - `test_o4_castle_freeze_refuses` -- `paced`, `pace`, `stop_after`, failing `side_ends`, a `battles` row, an
     `engine` that is not the live DLLs' (a stub reader), an existing file; a synthetic chain (runs everywhere).
   - `test_o4_castle_census_proves_inert_by_instancing` -- `instanced_at` on a synthetic Main_Init; on stock 150 at
     325: {code 1, 2, 3, 5, 6, 9, 4, region 18, code 17}, no instancing op outside e0 t0.
   - `test_o4_castle_preflight_verdicts` -- `p_pad` (with a stub `xinput_slots` reader), `p_override`, `p_engine`,
     `p_gate`, `strict_text` and P-TEXT's pre/post-deploy rule: section 8's units.
   - `test_o4_castle_input_witness_readers` (rev. 2) -- section 8's input-witness unit.
   - `test_o4_castle_trace_summary_cuts_at_end_places` (rev. 2) -- section 8's trace-summary unit, the member-end F
     stage and its end-fields mutant.
   - `test_o4_castle_void_asym_reads_observed_rows` (rev. 2) -- (d) on synthetic runs: one F run's `observed` row FAILS
     (d) alone; the same kind and cell on one run of each side PASSES. Break: read only O2's (a)-(b) and (c).
   - `test_o4_castle_gate_verdict` -- section 8's gate-verdict unit, with its causes.
   All into `REQUIRED_TESTS_O4`.
3. **C2: `o4_dryrun.py`** -- every case and unit of section 8 as registered, with O3's EXACT `case()`. G20 joins the
   gate with `O4_DRYRUN_FLOOR` = the count C2 prints.
4. **C3: `o4_rehearse.py`** + `--rehearsal-report`. Tests, every one with `warp_arrive_control` False and
   `soft_reset_ui` the engine's set:
   - `test_o4_rehearsal_plumbing_on_the_fake` -- R-CHANBARA on the fake: the record holds every 7.2 section, the zone
     and prompt rows, 127 as published, `end_run`'s rows.
   - `test_o4_rehearsal_void_stage_stops_mid_fight_on_the_fake` -- R-CHANBARA-VOID: V17 when instance 11 opens, no
     press after instance 10's, then `recover-warp` (4600) and the title: F7's rows.
   - `test_o4_rehearsal_smoke_sends_no_storytrace_on_the_fake` -- F-SMOKE: each pair warped with its own entrance and
     SC, no `Session.warp()`, no `storytrace` step executed, the object sids recorded, `end_run` after each warp.
   - `test_o4_rehearsal_gate_reads_the_pair_on_the_fake` -- R-GATE, S then F, paced: F with `bonus_fires` True ->
     WITNESSED; False -> BROKEN, cause "bonus"; F with `miss_read` on one non-LEFT/RIGHT instance (pages 120/121) and
     on one LEFT/RIGHT instance (the slide's miss, V18 at Z3) -> BROKEN, cause "combo" each; S with
     `sa` 0 -> INVALID; the record carries each run's launch `engine` and `settings`; the verdict goes to the record,
     never into `o4_forks.json` (the lead fills `gate_witness`); every stage summary cut at its end PLACES (member(150)
     on F).
   All into `REQUIRED_TESTS_O4` (G19's selection matches "o4_"; none says "rehearse", so G12 does not run them).
5. **C4: the O4 section in `PLAN.md`** -- the question, the segment, the sides and their ends, the fight and the
   displayed-100 rule, the checks, R-GATE outside the claim (with its cause and its engine), "draft: rehearsals
   pending, deploy pending, freeze pending", the block-2 rewrite and the global side effect as scoped facts -- among
   them that O1's and O3's P-TEXT read 7 byte-equal after O4's deploy and O3's report clause is now derived from its
   record (A2) --, "US session" in its heading.

**PART C REQUIRED-GREEN** (after each of C1-C4, as far as it exists):

| Command | Expected |
|---|---|
| `py studies/story-trace/o4_castle.py --offline-check` | exit 0; "predictions: the draft"; 4 PASS -- O4-BUILD (140 files, every language its own donor's; per language member(64)'s e4 t1 score-to-store equal and exactly the six in-chain `Field()` operands differing), O4-KEYS (6.1's line; 56 fight pins), O4-TEXT, strict (block 2: 7 byte-equal of 7; block 3: 7 byte-equal of 7; KNOWN-KIT-DEFECT 0, FAIL 0), O4-CENSUS (6.1's line) |
| `py studies/story-trace/o4_castle.py --preflight` | exit 1, RED BY DESIGN: exactly P-MANIFEST, P-DEPLOY, P-EB, P-FLOOR, P-DONOR and P-GATE FAIL; P-STOCK, P-TEXT (block 2: O1's copy with its named uk KNOWN-KIT-DEFECT line, tolerated before the deploy; block 3 none shipped), P-RECOVERY, P-SETTINGS, P-OVERRIDE, P-ENGINE PASS; P-PAD PASS (or PASS with its WARN line) |
| `py studies/story-trace/o4_castle.py --draft` | exit 0; the draft JSON: members 31240-31259, `side_ends` {"S": [153], "F": [31245]}, the policy "fast", `engine` the pinned sha, `rehearsals` [] |
| `py studies/story-trace/o4_dryrun.py` | exit 0; "N/N cases as registered" (from C2) |
| `py studies/story-trace/segment_regress.py` | exit 0; G1-G19 and G21, and G20 from C2 |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o4_ or fake_chanbara or fake_keyon"` | all passed, 0 failed, 0 skipped, every `REQUIRED_TESTS_O4` name among them |

Then the lead's sequence (7.4): the rehearsals, the freeze (v1), the deploy, F-SMOKE, R-GATE, the session.

---

## 10. Open risks (what only the game can settle)
1. **The prompts' publication** (F1, the go/no-go). `phrase_raw` is inferred from 105's measured publication and O1's
   `[CBTN]`; the recognizer wants exactly one DBTN tag, "Press" and "[TIME=-1]". Another form fails the zone closed at
   the first prompt (V17, nothing pressed): it costs a rehearsal, never a wrong press. R-CHANBARA runs first.
2. **The latency in game** (F3). The fast premise needs every `j_hi` <= 16 (raw >= 100 then follows, 5.3 (e)).
   Expected 3-5 ticks (the publication every 2nd frame, the agent's request poll every 2 frames idle, down at
   accepted + 1), worst ~11. A Windows hitch inside a window adds `excess`; at ~31 fps a frame weighs a whole tick. If
   `j_hi` > 16 recurs, the V17s spend the re-runs (`rerun.max` 2) and the session falls short of coverage: F3 tries a
   tighter `poll_s` and `state_every` 1, or STOPs.
3. **The close tween and the lingering prompt** (F4, F5). 0.2 #1 derives two prompts listed for 0.09 s plus a frame
   (rev. 2); the agent publishes what `activeDialogList` holds, which keeps a closing window until `AfterHidden`. The
   tracker holds a closing prompt apart from new ones (`closing`), so it reads both shapes -- a gap or an overlap --
   under either policy; no rule rests on a gap any more (rev. 2), and F4 checks the merged stream left no instance
   unobserved.
4. **The reaction and the fight's length** (est. ~30 ticks a pass, ~51 s): the clips' speed is unmeasured. It sizes
   `zone_stall_s` and `run_s` only; no score depends on it.
5. **The KEYON pairs' gates** (F12). The INCS/250 gate can hold a pair 8.3 s; page-once re-presses every 10 ticks
   until both windows close, each a press row. A pair that never closes is the watchdog's V14.
6. **Choice 127 as published** (F6): options and cursor unmeasured; the No line may lose its first character as O1's
   did ("o" then). A wrong pick replays the fight and is never covered (V2, or V17 by `stray_answer`).
7. **Recovery from inside the fight** (F7): `end_run`'s warp from FieldHUD while e20 and e3 run is taken by the source
   (Ff9mkDebugMenu.cs:2083) and unmeasured in game. If it does not take, the launch stops (F7's STOP).
8. **The members' first load** (G1): twenty members, built at C0, never loaded until F-SMOKE; SPS warnings are visual
   only.
9. **The +30% wrap on member(64)** (G2): never witnessed under the trace. BROKEN with cause "bonus" is a finding the
   session survives (the fast play's raw >= 100 is clamp-proof); BROKEN with cause "combo", INVALID or UNINFORMATIVE
   stops before the session (P-GATE). The witness is tied to its engine and settings (rev. 2): an engine rebuild after
   R-GATE re-opens it.
10. **The block-2 rewrite** (6.4): O4's first deploy replaces O1's block-2 copy for every chain; O1's and O3's P-TEXT
    then read 7 byte-equal (their uk KNOWN-KIT-DEFECT line disappears): docs quoting that line are re-baselined;
    archived analyses keep their recorded preflight. Reverting O4 restores O1's copy only in the recorded order.
11. **A pad or a hand at the machine**: `AlwaysCaptureGamepad = 1` reads a connected pad unfocused (0.2 #5), and F1
    toggles the 3x booster when the game has focus (0.3 #7). P-PAD samples at the preflight and on the session's
    launch; rev. 2's input witness polls pads, keys and focus every 50 ms through the whole run (in the fight's tight
    loop; elsewhere between the main loop's blocking calls), and a non-neutral reading VOIDs
    that run (V13) instead of letting a two-key miss, a tripled tick rate, a human Yes or a pause read as the fork's
    (V18) or the game's (V2, V14). What it cannot see is input shorter than its gaps outside the fight (a page press
    blocks the main loop for ~4 ticks). The session is hands-off.
12. **The Encore achievement**: every run scoring >= 75 calls Steam's achievement (EMinigame.cs:34-38) on the owner's
    account, in the rehearsals and the session -- harmless after the first unlock, but outward-facing: the lead says so
    to the owner before R-CHANBARA.
13. **The pages' openings** (F13; rev. 2): a Confirm in a page's opening (0.105 s plus about two frames, 0.3 #1) is
    dropped; page-once re-presses it `page_once_ticks` later. If a page's measured opening ever exceeds the hold-off,
    a re-press could land while it still opens and be dropped again -- a slower close, never a wrong one; F13 sizes
    `page_once_ticks` from the measurement.
14. **The publication order** (rev. 2): no source line fixes whether a sample shows its own frame's ticks (0.3 #2).
    2.4.7's bounds hold under both orders, at the cost of up to a tick of `j_lo`; the slides' samples (2.4.6) are
    chosen so either order reads them the same.

Closed by the source (no longer open): **cfg.control and the tick** -- New Game resets both (0.2 #6); **the warp's
redirect** -- the harness warp and `Field()` never redirect (0.2 #14); **the bonus hook's place and its write** --
sid 4 ip 223, Map.Int16[48] only (0.2 #11); **Bit[3815]'s order** -- after page 123 (0.2 #3); **150's inert
functions** -- no instancing op outside Main_Init, none of them on the 325 branch (0.2 #4, O4-CENSUS); **control in
64** -- mapvar is cleared at every field start, so `EnableMove` stays behind `Map.Bit[158]` (2.1).

---

## 11. Critique log

### 11.1 The research critic's eleven
The critic's eleven problems (`o4_research.json` `critique.problems`: two major, nine minor), each re-checked in the
bytes or the engine source, and its disposition. Decisions 4, 5 and 6 (0.1) took them in; nothing was disproved;
#3 and #11 are refined by what the bytes hold.

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| 1 (major) | F ends in member(153), S in real 153; one end list serves both sides: every correct F run VOIDs (V11), and a real-153 landing on F would read reached. | o3_prima_vista.py:242-243; segment_drive.py:808 (one `self.ends`), :970 and :998 (`cut_at_end` compares PLACES), :1734 (rule 2); o2_alexandria.py:1240; segment_trace.py:677. | ADOPTED and widened: S6 separates end FIELDS (rule 1, `on_route`) from end PLACES (the cuts), per side and opt-in (`side_ends`); a real chain donor on F is V19, a finding (`rerun.stop_on`); O4-LANDING (d) pins F's cut row to member(153); the dry run's end-real-153-F, v19-one-F and leak-real-150-F; G15-G18 prove O3 byte-identical. The alternative (153 out of `--ids`) is not taken: decision 4. |
| 2 (major) | The +30% wrap feeds a story write and a fast O4 cannot witness it: the clamp hides it at raw >= 100. | EMinigame.cs:12-21 (EffectiveFieldId == 64; sid 4 ip 223); 64 e4 t1 ip208, ip222-233, ip338; raw = floor((3725 - 50 x mean j) / 29) re-derived (2.4.7). | ADOPTED as decision 5 decided: the REQUIRED paired stage R-GATE (7.1, 7.4 G2), paced to j ~22 ticks with the band [79, 99] checked from the logged j bounds (V17 "uninformative" outside), after the deploy and before the session, outside the frozen claim; P-GATE keeps the session's preflight red until it ran. The session stays fast. |
| 3 | V17's timeout detector ("still published ~50 ticks after first seen") can never fire: the next prompt replaces a timed-out one in the same tick. | 64 e20 t1 ip1424 and ip789-852 (one tick); ETb.cs:221-224 (`NewMesWin`'s `DisposWindowByID`); Dialog.cs:610-643, :687-692; DialogManager.cs:205-222, :268-274. | ADOPTED, refined: the replaced window LINGERS beside its successor for its tween (0.2 #1), and a hit later than the reaction re-arms in its own tick too (0.2 #2). The detectors: live (fast only), a DBTN change with no prompt-free sample since the press; post hoc (both policies), a window gone before the press's down frame; and the lost press, a window lingering past `gone_ticks`. H11 models the same-tick re-arm and the tween. REV. 2 (11.3): the tween is 0.09 s plus a frame, not 0.15 s; the live no-gap detector is gone (a missing sample is the driver's, V17); every detector reads positive evidence off the merged stream. |
| 4 | The fight zone is not fail-closed: an unclaimed prompt falls to rule 7's Confirm (the Cross bit), a miss on 7 of 8 prompts. | segment_drive.py:1793-1813 (rule 7); EventInput.cs:476-534. | ADOPTED: rule 6b before rule 7; Z1-Z2 claim only prompts and the zone end; any other dialog or a choice is V17 with nothing pressed (2.4.3, step 6; rev. 2: steps 5 and 7, each with an `observed` row); a prompt outside the cell is V17 too. REV. 2: also a `[DBTN=` page neither recognizer claims (S8 a). |
| 5 | Stray Confirms after 111 and after 123; a stray on 127 replays the fight and is attributed to the game (V2). | Rule 7's re-press while a text stays listed; the gaps T0+13 and the choice Wait(10) after ip390 (0.2 #3); segment_drive.py:158-161 (V2 by "game"). | ADOPTED: page-once and the quiet windows (S8), `stray_answer` (S9: V17 when the driver's own press rows show a Confirm landing in [127's first frame, the answer)), and SWORD (f) reading the rows post hoc. REV. 2 (11.3): the quiet window opens when 123 is first seen gone, page-once keys each window, `stray_answer` reads every Confirm of the visit (`choose`'s rowed), and SWORD (f)'s window starts at the first prompt's `prev_frame`. |
| 6 | cfg.control and the tick rate follow from the code; they are no unknowns. | TitleUI.cs:963-977; FF9StateSystem.cs:64-66; SettingsState.cs:55, :66-74, :127-139; FF9CFG.cs:6-10; HonoInputManager.cs:636-640, :967-975. | ADOPTED: `derived` with its citations (4.13), F2's 122/123 reading the in-game confirmation; `chanbara_of` refuses the `circle` alias; Start's level read noted (0.2 #6). |
| 7 | The input hazard is miscited: the live risk is a connected pad, read even unfocused. | Memoria.ini:126; HonoInputManager.cs:554-567 (:558 PlayerIndex.One, :561 the keyboard needs focus, :563 AlwaysCaptureGamepad), :531-552. | ADOPTED: P-PAD (6.2) at the preflight and on the session's launch, slots 0-3; the session hands-off (10, #11). |
| 8 | The LEFT/RIGHT slide is a per-prompt hit witness the map leaves unused. | 64 e20 t1 ip918-1063 and ip1066-1211; e13 t11 ip1617-1765 and ip1768-1916; the miss reactions (ip1337, ip1345) move nothing. | ADOPTED: the `slide` row on every LEFT/RIGHT instance (2.4.6); SWORD (e) requires every one ok; H11 models it. REV. 2 (11.3): measured between the `prev` samples that bracket the slide (rev. 1's `x_seen` baseline was taken after the slide had begun), the tail jointly, "unmeasured" allowed and none measured-not-ok required. |
| 9 | The start rests on the live field-70 override, in a folder another worktree owns. | FF9CustomMap-world's `evt_alex1_ts_opening.eb.bytes`: seven languages, 1424 B, one sha (0.2 #7); 70's ip130 and ip475. | ADOPTED: `override70` pinned in the predictions (4.13), P-OVERRIDE (6.2), the fingerprint's `override70` per run; the warp window after ip130 and before ip475 (4.6). |
| 10 | Deploying the twenty donors has a global side effect on the shared install. | DataPatchers.cs:102-105, :137-167; HonoluluBattleMain.cs:736-737; ff9.cs:9327; the live ForkDonorPatch holds none of O4's donors. | ADOPTED: `global_side_effects` and the revert order in `o4_forks.json` (6.4), the deploy owner-gated, P-DONOR (6.2). |
| 11 | O4-BUILD should pin the fork gates' bytes: member(64)'s US e4 t1 from ip208 to ip338 equal, and the only diffs two `Field()` operands. | The members hold SIX in-chain `Field()` operands: member(64) e2 t1 ip536, e11 t2 ip201, e12 t2 ip201; member(150) e3 t1 ip2169, e18 t2 ip386, e19 t2 ip342 (the region exits never run on the route). `remap_fields` retargets every `Field()` whose literal is a chain donor; 64's `Field(67)` and every `PreloadField` stay. | ADOPTED, refined: the pins per language, e4 t1 from the score through the store's whole instruction (US ip208-ip346), the diff set exactly the six operands (6.1), measured on C0's build before C1. |

The critic's GO conditions -- per-side ends, and a decision on witnessing the wrap -- are S6 (PART A) and R-GATE with
P-GATE (7.1, 7.4). Its list of what R-CHANBARA must measure -- the prompts' `phrase_raw`, 127's options, the clips'
speed and the fight's length, j per prompt, `end_run` from mid-fight -- is F1, F6, F10, F3 and F7.

### 11.2 Where this design reads a decision's letter differently (each said, none relitigated)
1. **Decision 1's "never a FAIL by itself"** holds for the DRIVE: a run below 100 stops at the score page as V17 or
   V18 and is never covered. The analysis FAILs only a COVERED run whose rows show less than 100 (SWORD (a) and (b);
   the dry run's byte475-93-every-F): that is the drive's own guard failing, which no VOID class can hold.
2. **Decision 5's BROKEN** names pages 120/121. Those are the COMBO pages (max combo below 50), not the bonus: on an
   informative paced run (49 proper rows) they mean the fork did not credit a proper press, a V18-class finding. The
   verdict keeps the letter (BROKEN) and its detail names the cause ("a combo page: not the +30%"), so no report reads
   it as the wrap failing.
3. **Decision 6's timeout detectors** are scoped: the live no-gap rule runs only under the fast policy, where a hit
   leaves >= 8.5 ticks of gap (0.2 #2); under the paced policy (j ~22, a gap of ~3 ticks) only the post-hoc and the
   lost-press rules run. Unscoped, R-GATE would VOID its own informative runs. REV. 2: decision 6's "a timeout
   detected as a DBTN change with no prompt-free sample since the last instance" is kept in substance and still stops
   the run, but its ATTRIBUTION now follows what the merged stream shows (11.3: driver critique #4, claim critique #2).
   A timeout under the fast policy leaves its window listed beside its successor at S+50, far past its press's mark:
   the live step 10 reads that as `lingered` (V18 for a proper press). The same DBTN change with neither a gap nor the
   old window in sight is a read gap: step 10 reads `unobserved`, V17. No verdict rests on the missing gap itself; the
   tracker records it (`gap`). The decision's other detector, "an instance whose window left before the press's down
   frame", is kept as `before`.
4. **Decision 6's fork-gate pins** (critique #11's "two `Field()` operands"): the bytes hold six in-chain operands;
   the pin is `remap_fields`' own in-chain set (6.1).
5. **VOID-ASYM (c)** is new. Decision 1 makes V18 a finding and decision 4 makes a real-donor landing one (V19); O2's
   (a) sees a finding only on one side, (b) only when a whole side is VOID. (c) reads any run VOID in a
   `rerun.stop_on` class as NOT PROVEN, whichever side holds it.
6. **Decision 7's shared machinery**: O3's `store_census` and O2's `keys_check` ops are not edited (G18 pins O3's
   offline check, G11 O2's); O4 has its own census, with the function-level `inert` class proven by `instanced_at`,
   and its own `:=var` key.
7. **Decision 2's end "on arrival in 153"** is a PLACE on F: the drive's end FIELDS are per side (S6), and both sides
   cut at the end place 153 -- member(153) on F, as O4-LANDING (d) pins.
8. **Decision 6's gamepad hazard** (rev. 2): the decision asks for P-PAD at the preflight, a connected idle pad a
   printed WARN; both are kept. The in-run input witness (2.4.3 step 0) is added on the claim critique #4: it can
   only VOID a run (V13), never change a verdict class decision 1 defines.
9. **Decision 1's V17 / V18 split** (rev. 2): unchanged in letter. V18 still means "its rows prove the frozen play and
   the game still scored lower"; rev. 2 only requires that the proof of the game's deviation be something a sample
   SHOWED. A run whose evidence is incomplete is V17 -- the driver's record does not prove its own play -- which the
   decision's "its own input was not the frozen play" covers as "not proven the frozen play".

### 11.3 The second round: driver robustness (12) and claim integrity (15) -- rev. 2
Every item re-checked in the bytes (the research listings, the stock `.eb` of all seven languages), the engine source
(`C:\gd\FFIX\Memoria` at 6b8bb2d5, the deployed DLL's source: 0.3 #8), the harness and the archives; 0.3 records the
findings. The 27 items are 22 distinct ones: 21 adopted (several refined where the re-check found more than the
critique said), and one (DR12 = CI11) adopted in its premise, its `j_hi` formula rejected and the other bound
changed. Items the two critiques share are disposed of once and cross-referenced (DR = driver robustness, CI =
claim integrity).

| # | Item | Re-checked | Disposition |
|---|---|---|---|
| DR1 = CI6 (blocker) | The quiet window after 123 deadlocks when its first Confirm is dropped in the page's opening: V14 by "game", one-sided, NOT PROVEN. | Dialog.cs:762-797 (closes only in `CompleteAnimation`), :645-651; DialogAnimator.cs:43-47, :61-126 (the opening: 0.105 s plus ~2 frames); segment_drive.py:1810-1812; the O2 R-FULL archive (`20260930-184253-o2-rh-R-FULL`, run 1: "Received Goblin Card!" first seen at frame 6549, the press accepted at 6550 dropped, the one accepted at 6570 closed it); fakegame.py:2779-2783. | ADOPTED (0.3 #1; S8 c; 2.4.11): the quiet window opens at the first sample without the quiet page; until then page-once re-presses it, keyed per window; the re-press cannot reach 127 (>= ~11 ticks: the tween, the tick e4 resumes in, `Wait(10)` at ip399); H11's pages get `open_s` / `open_frames`; `test_o4_drive_presses_123_again_when_its_first_press_is_dropped`, F13. |
| DR2 = CI3 (blocker for R-GATE) | Under the paced policy the tracker reopens the previous, still-closing prompt as a new instance: R-GATE VOIDs itself. | 0.2 #1 / #2 re-derived with the corrected tween (0.09 s plus a frame) against A ~28-30 and paced j ~23-27: the two prompts overlap on most passes; ip681 forbids back-to-back repeats. | ADOPTED (2.4.3 step 8): a `closing` set, never a new instance, each entry left at its first sample without it; its lingering judged by the same mark; `test_o4_drive_paced_tracks_the_closing_prompt_beside_its_successor` with reactions 28, 30, j + 2 and j - 2. |
| DR3 = CI1 (major) | The LEFT/RIGHT slide is measured from a sample taken after the slide began: SWORD (e) fails correct runs, F2 cannot pass. | e20 t1 ip861-1063 (REQSW returns at once, EventEngine.DoEventCode.cs:154-183; i = 0 moves nothing, `Wait(1)` ip1040); e13 t11 ip1617-1765 (a tick later); e20 ip1557-1618 and e13 ip1332-1352 (nothing moves before 107). | ADOPTED, REFINED (0.3 #3, #9; 2.4.6): BASE = instance n+1's `prev` sample whatever it lists (its state precedes the arm in either publication order -- DR3's "prev_kind none" restriction is not needed), END = instance n+2's `prev`; CI1's base, n's own first sample without its window, is NOT taken: a fast hit's window can be gone before n-1's slide ends (Zidane's last step after S_n+6), so its x can sit mid-slide; both samples must lie >= 7 sure ticks after the previous instance's `seen_frame`, else "unmeasured" (DR3's rule); CI1's tail point adopted, done JOINTLY for 48-49 to the zone end (the phantom pass's arm is unpublished); a measured slide of 0 on a proper press is now V18 evidence (the game read a miss), any other wrong value V17; H11 moves per tick from the arm and publishes agent-first; `test_o4_drive_slides_at_31_fps_agent_first` and the dry run's slides unit. |
| DR4 = CI2 (major) | V18 is inferred from samples the driver did not take (a read stall hides the gap or delays the first-without sample): one V18 is NOT PROVEN. | channel.py:1023-1075; session.py:663-695 (`_await_ack` polls into the ring), :984-997, :331, :794-801; artifacts.py:35-72 (the ring, 300 frames); HarnessAgent.cs:599-607 (the press blocks). | ADOPTED (0.3 #4; 2.4.1, 2.4.3, 2.4.6, 2.4.8): the MERGED stream (executor + ring); per-instance `evidence` -- before / lingered / closed / unobserved -- with `last_listed_frame`; V18 only on a sample that SHOWED the deviation; an unobserved instance is V17 "instrument: a read gap"; the live no-gap rule removed (11.2 #3); `max_read_gap` from the merged stream; `test_o4_drive_read_stall_in_a_gap_is_v17_never_v18` (CI2's 0.5-s stall). "The old DBTN listed beside the new one" counts as evidence only through the mark test -- under the paced policy that overlap is normal. |
| DR5 (major) | SWORD (f) flags the run's own press that closes 111 (its down frame precedes 111's leaving, and whether a sample shows 111 after it is a race). | DialogAnimator.cs:144-173 (the close tween); session.py:1151-1152 (`press` returns at the ack); e3's poll gate `Byte[47] == 1` (ip23) shut until the first arm. | ADOPTED (5.3 (f)): the window runs from instance 1's `prev_frame` -- a Confirm down before it gives its edge no later than the arm tick, where the gate is still shut (2.4.7's frame-to-tick reading); 111's `last_with` / `first_without` off the merged stream; the PASS case sword-111-closing-press-late-both. |
| DR6 (minor) | Z0's `rate(require=True)` can block 2-10 s before prompt 1. | session.py:1351-1419; tickrate.py:94-109, :126-133. | ADOPTED (2.4.2): a non-blocking `g.rate()`; the judge still requires every row's rate measured; `test_o4_drive_never_blocks_on_the_rate`. |
| DR7 (minor) | The pace counts ticks with a lower bound, so presses land a tick late, and ~twice as late for 2 s after a regime switch; `pressed_frame` is undefined. | tickrate.py:251-253 (`ticks_sure` divides by `fps_hi`), :586-649 (`_switch` keeps the old band for WINDOW_SECONDS). | ADOPTED (2.4.10): elapsed mtime x `tick_hz` (frames x `per_frame` without an mtime), judged only by the post-hoc bounds; `lead_ticks` from `down_frame - pre.frame`, per regime (F14); the paced test switches 60 -> 31 mid-fight. |
| DR8 (minor) | The animation numbers are wrong: close 0.09 s plus a frame, open 0.105 s plus 2 frames, L/R reaction ~28. | DialogAnimator.cs:144-173, :43-47, :61-126; e20 t1 ip975-1063. | ADOPTED: 0.2 #1, #2; 4.10's `gone_ticks` sizing; section 3's `close_s` / `close_frames`, `open_s` / `open_frames`, `reaction` {0: 28, 1: 28}; F5. |
| DR9 (minor) | The tight loop never checks `ui_state`: a main menu opened on Triangle would read as a lost press (V18). | UIKeyTrigger.cs:694-700, :863-869; FieldHUD.cs:394-397; EventEngine.DoEventCode.cs:1046-1051. | ADOPTED (0.3 #5; 2.4.3 step 2): any sample off FieldHUD is V13 with nothing pressed; H12's `menu_on_triangle`; `test_o4_drive_stops_v13_off_fieldhud`. |
| DR10 (minor) | S9's page check rests on one sample, and `[NUMB]` is filled at render. | Dialog.cs:1560-1569; UILabel.cs:787-803; DialogBoxSymbols.cs:154-170. | ADOPTED (0.3 #6; 2.4.12): two consecutive equal samples, for the score page and the gil page; H12's `unsubstituted_once`. |
| DR11 (minor) | If neither recognizer claims the real form, rule 7 presses Confirm on the first prompt. | segment_drive.py:1793-1813; block 2's messages with button tags are 2 and 38 (other fields' windows: 64 shows only 3, 105-128 and 306-314) and 111, 112-119 -- so on the route only the zone start and the prompts hold `[DBTN=`. | ADOPTED (S8 a): under the policy rule 7 refuses any page in the cell whose `phrase_raw` holds `[DBTN=` and is not the registered zone start -- V17, game-observed, nothing pressed -- after the stop pages; `test_o4_drive_refuses_an_unrecognized_dbtn_page`. |
| DR12 = CI11 (minor) | The j-bound premise is wrong (the agent publishes before the field ticks); `j_hi` survives only by its +1. DR12 proposes `ticks_most(down - prev + 1) + ceil(excess)`, CI11 `ticks_most(down - prev + 1) + 1 + ceil(excess)` or settling the order from the source. | HarnessAgent.cs:70-77 (`IsHeld` keys on `Time.frameCount`); FPSManager.cs:13-17, :77-139 (the input read BEFORE a frame's ticks); ETb.cs:50-63; EventEngine.cs:114-119; no execution-order attribute in Assembly-CSharp (the order is not in the source); tickrate.py:67-77 (one frame measured "agent first"; TAIL_TICKS). | PREMISE ADOPTED, `j_hi` FORMULA REJECTED, `j_lo` CHANGED (0.3 #2; 2.4.7). The premise is corrected and both orders are bounded. But the edge is FRAME-SCHEDULED: it lands on the first tick of the frames >= `down_frame` in either order, so j is at most the ticks of frames [`prev_frame`, `down_frame` - 1] -- `ticks_most(down - prev)` -- plus the jitter tick the harness's own bounds carry (TAIL_TICKS) and the hitch excess: rev. 1's `j_hi`, sound under both orders. DR12's formula drops that jitter tick in exchange for frame `down_frame`'s own ticks, which the edge precedes -- equal at ~31 fps, a tick tighter in some phases at 60 (an extra half-tick frame whose ceil adds nothing): not the harness's bound. CI11's adds a frame to rev. 1's: sound, a frame wider, and it would push `j_hi` past `j_cap` sooner for no soundness gained. What the re-derivation DID find is on the other bound: under the agent-last order a frame of jitter can make rev. 1's `j_lo` (`ticks_sure(down - seen)`) overstate by a tick, and `raw_hi` -- R-GATE's non-vacuity (CI's own "R-GATE vacuity" check assumed the agent-first order) -- rests on it; `j_lo` is now `max(1, ticks_sure(down - seen - 1))`, sound under both. The fake's j tests run under both orders (`publish_order`) against the true j (`chanbara_log`). |
| CI4 (medium) | Real input during the fight -- a pad (read unfocused), a key, the F1 booster (3x ticks) -- can produce a false fork finding; nothing samples input during the session. | HonoInputManager.cs:554-567; Memoria.ini `AlwaysCaptureGamepad = 1`; UIKeyTrigger.cs:243-255 (F1); FPSManager.cs:83, :95-97; DialogAnimator.cs:8-18. | ADOPTED and WIDENED (0.3 #7; 2.4.3 step 0): the input witness (pads 0-3 through P-PAD's reader, every key and mouse button while the game has focus, focus itself) every 50 ms, through the whole run, not only the zone -- a human Yes on 127 or a pause in 150 would otherwise read as V2 or V14 by "game"; a non-neutral reading STOPS the run as V13 at once (not only "V18 turned V13"), since a press already made under outside input cannot be trusted either way; SWORD (e) requires the zone's `input` empty; P-PAD's WARN kept. |
| CI5 (medium) | V17 sub-causes the GAME showed are re-run away: VOID-ASYM (a) reads only game-attributed classes. | o2_alexandria.py:1289-1312. | ADOPTED (2.4.6 `observed`; 5.3 (d)): every game-observed V17 logs an `observed` row; VOID-ASYM (d) FAILS one held by one side only; observed-unclaimed-one-F (NOT PROVEN) and -one-each-side (PROVEN); decision 6's V17 class kept. |
| CI7 (medium) | The regression gate pins only the NAMES of O1-O3's driver tests: an adapted test still passes. | segment_regress.py:480-575 (`_selection_bad`, `g7`, `g12`, `g13`: tests selected and checked by NAME). | ADOPTED (1.4 G21; A0): the AST shas of every test G7/G12/G13 collect and of the fake's existing beat and input functions, captured FIRST; any change FAILS until re-baselined by name with a reason (`--rebaseline-source`, `research/source_pins.json`); `test_segment_regress_source_pins_catch_an_edit`. |
| CI8 (medium) | A replay (Yes taken) is judged by the fight's rows, and `g.choose`'s presses are not rows. | session.py:6717-6751 (`select` steers with `press down/up 4`, then `press confirm 4`); session.py:640-661, :7972-7975 (steps.jsonl); HarnessAgent.cs:545 (the `accepted` event). | ADOPTED (0.3 #10; 2.4.11, 2.4.12): a replay page or a second 127 goes to `stray_answer` over every Confirm of the visit, `choose`'s rowed from the steps ledger and the events without a session.py change; only a gil page with another NUMBER goes to the fight judge; the answer's own Confirm excluded when the cursor read No; the replay pages named (64 mes 109/110). |
| CI9 (medium) | R-GATE's witness is tied to no engine and is read from a mutable file. | segment_trace.py:409-432; o3_prima_vista.py:1148-1159; the live x64/x86 DLLs and Memoria's Output hashed (0.3 #8); EMinigame.cs:23-30 (SA 2's refill). | ADOPTED (4.13 `engine`; 6.2 P-ENGINE, P-GATE, P-LAUNCH; 6.3; 6.4 `gate_witness`; 5.4): the engine pinned in the predictions, checked live, fingerprinted per run, dated before the launch; P-GATE requires the witness's engine and settings (SwordplayAssistance 1) to be the session's; the report reads R-GATE from the session's RECORDED P-GATE detail. |
| CI10 (minor) | "BROKEN" covers the bonus and the combo, and PROVEN loses its scope after a BROKEN. | EMinigame.cs:12-21 vs 64 e4 t1 ip346-366 (the combo pages). | ADOPTED (7.4 G2; 6.2; 5.4): `cause` "bonus" or "combo"; BROKEN/"combo" fails P-GATE (diagnose before the session); the report's fight line states the fast play, the clamp, and R-GATE's verdict with its cause; decision 5's BROKEN letter kept. |
| CI12 (minor) | The per-language text claim is printed, not enforced. | o2_alexandria.py:422-461 (`text_rule` names another language's copy without failing it); all seven stock 64 `.eb` decoded: jp 10604 B with its stores at ip319/ip371, the others 10624 B at ip338/ip390, the bonus statement at ip222 in all seven (CI12's check, confirmed). | ADOPTED (6.1 O4-TEXT strict; 6.2 P-TEXT strict after the deploy, O1's copy tolerated before it by its shas; 5.4's language line derived from the recorded lines); `strict_text` wraps `text_rule`, which stays unedited (G11, G18); the per-language pin form of 6.1 confirmed by the jp decode. |
| CI13 (minor) | O3's report hard-codes the uk defect clause, stale after O4's deploy. | o3_prima_vista.py:100-101, :1462-1466; story-o3's recorded P-TEXT (the defect line); o3_dryrun.py:327 (its sessions record it too). | ADOPTED -- the full fix, not only the note (A2): the clause derived from the recorded P-TEXT lines, byte-neutral for story-o3 and every o3_dryrun session (G15-G17 prove it); o3_prima_vista.py is shared code under the O3 gate, so 1.1's "not edited" gives way to one gated edit; `text_effects` and PLAN.md record it. |
| CI14 (minor) | Not every cutter uses end places: an F stage ending in a member is never cut. | o2_alexandria.py:649-651; o3_prima_vista.py:856-858; segment_trace.py:126-135 (`cut_at_end` compares places). | ADOPTED (7.1; 1.3): O4's `trace_summary` and every rehearsal reader cut at `end_places(pred, side)`; the trace-summary unit with a member-end F stage and its end-fields mutant. |
| CI15 (minor) | O4-STABLE and LANDING (c)'s second half cannot fail as registered. | segment_trace.py:777-788 (`stable_check` reads keys unstable within a side); segment_drive.py:1701-1712 (rule 1 writes the end row only for an end field). | ADOPTED (5.3; 8): extra-key-one-F (STABLE F, WRITES F, STATE F; NULL P) and end-log-row-real-153-F, a synthetic log (LANDING F (c) alone). |

**Where both critics checked the same thing and found it sound**, rev. 2 agrees and keeps it: the button map, the
`circle` alias trap, `cfg.control`, Start read as a level, two keys in one tick; the dialog-confirm bridges; a held key
across an arm; 127's readiness hold and the Yes-on-its-opening path (a Confirm there only sets `SelectChoice`,
Dialog.cs:798-802); 105/106 and 107/108 under page-once; recovery from mid-fight; the absence of noise; luck and wrong
buttons (49 hits are required for 122/123 and Bit[3815]); the per-side ends' neutrality for O1-O3; the global side
effect. One of them shifts under rev. 2's re-derivation: "R-GATE vacuity ... `j_lo` is sound under either publish
order" holds for the agent-first order only, which is why `j_lo` changed (DR12 = CI11 above).

**Found while re-checking, outside both critiques**: the fight's tail moves neither body before 107 (0.3 #9, which
the joint tail slide rests on); `Map.Int16[36]`'s TimeLeft-30 branch is dead (0.3 #9), so the model's 50 stands; a
covered run's slide is a corroborating witness only (Bit[3815] and 123 already prove 49 hits), so "unmeasured" costs
no claim; and the `evidence` "closed" now requires a sample listing the window at or after its down frame -- without
it, a window that timed out during a press's own block would read as closed by the press.

### 11.4 As built (the implementer appends, PART by PART)
Where the design was silent or wrong, each the smallest correct thing, in O3's 11.4-11.6 form; and the review's
findings, in O3's 11.7 form.

#### PART A, as built: where the design was silent (each the smallest correct thing)
A0 first, at the design commit (3d6c8879): the gate extended (G15-G18, G21, `--capture-o3`, `--rebaseline-source`,
`REQUIRED_TESTS_O4` empty), `research/source_pins.json` written `[]`, the O3 baseline captured, and all of it
committed before any other code change. Nothing in 1.4 was disproved. Where it left a choice open:

| # | Where | The design | As built, and why |
|---|---|---|---|
| 1 | G0''s two readings | "each temporary root the replica makes is replaced by `<tmp>`" | Every spelling of the root is replaced: as made and resolved, each as written, with its backslashes doubled (a `repr` or a JSON dump) and as a posix path. Measured: no output of the replica carries a temporary path, a clock or a random today -- the two readings were identical and the baseline holds no `<tmp>` mark. The replacement is a guard for a later output that would. |
| 2 | The capture's refusals | "refuses to write unless G15-G18's baseline-free halves pass" | It also runs G7, G12 and G13 against the committed O1 and O2 baselines and refuses unless all three pass: the tests those selections collect become G21's pins, and pinning a failing or skipped test would pin a broken surface. Measured at the capture: 21, 43 and 24 passed. |
| 3 | G21's names | "each by its qualified name" | `<repo-relative file>::<qualname>`, pytest's node-id form: `ff9mapkit/tests/test_harness.py::test_...`, `tools/harness/fakegame.py::FakeGame._step_scene`, `tools/harness/fakegame.py::_control`. A parametrized test is pinned once, by its function (its cases share one AST). The last definition of a name wins, as Python binds it. 105 pins at the capture: 85 tests (the three selections' 88 results, one test's four parametrized cases folded into one) and the 20 fake functions. |
| 4 | G21's AST | "the sha256 of `ast.dump(node, include_attributes=False)`" | Exactly that, so a DOCSTRING edit to a pinned test counts as a code edit (re-baseline it, with its reason). `ast.dump` is version-specific (3.13+ omit empty fields; a new Python can add node fields), so the baseline records `sources_python` (3.14), and when pins differ under another interpreter G21's detail names the version mismatch first. |
| 5 | `--rebaseline-source` | refuses an empty reason, a name not pinned, an `old` that is not the pin in force | Also refuses a source already at its pin in force (nothing changed: a no-op row only blurs the record) and a pin whose function is gone (a pin never follows a rename; G21 fails it as gone). The gate REPLAYS every row through the same rule, so a hand edit to the pins file -- a reason emptied, an `old` rewritten, rows reordered -- fails G21 by its row. `rebaseline_source` takes a `files` seam for its test. |
| 6 | G14 and G17 | -- | Both run `o3_dryrun.run_cases(v1)` now that v1 exists (G14 is unchanged: its floor; G17: the byte-equality and the count from the replica): about 25 s more a gate. |
| 7 | The O3 baseline | 1.4 G0'' | 3.5 MB (the 60 sessions' reports in full, so G17 names a case's first differing line), LF, `-text`; head 3d6c8879, v1's sha 1bcf11a9; `tests` holds G13's 24 names, `sources_from` the selections and fake functions the pins came from. |
| 8 | `_missing()` | "gains the O3 inputs" | Per mode: the gate needs everything (exit 2 otherwise); `--capture-o3` the story-o3 archive, v1 and the O1 and O2 baselines (its G7 and G12 read them); `--rebaseline-source` only the O3 baseline and the pins file. |
| 9 | A0's test | "G21's checker over a temporary copy" | The copy is of the two real pinned files (bytes), so the edits it makes -- a comment and whitespace edit, a body edit, a fake function's body, a rename -- are edits to the real pinned functions' twins. It also drives `g21` through a pins file and `rebaseline_source` through a temporary baseline (a refusal writes nothing; a re-baseline appends its one row; a second, unchanged, is refused). Mutants run: pin the AST WITH its positions (`include_attributes=True`: the comment edit then fails the test), and `g21_bad` comparing names only (the body edit then passes): each failed it. |
| 10 | A1: `side_ends_of` | "ValueError on ..." (1.2) | As listed, plus a side that lists an id twice (a typo, never a second end); S is compared with the end fields as a set, each listed once. Each refusal names its clause, and the pure test raises each one once. |
| 11 | A1: rule 2's V19 | "`fid not in members and fid in set(members.values())`" | Exactly that, under `side_ends` only (on F: S has no members). The message names the lowest member forking the field when several would; the cell is `[the real field, the published SC]` -- its own place, as the dry run's v19-one-F reads `[153, 1190]`. Holding the side on V19 (`rerun.stop_on`) is O4's predictions' (4.1), not the driver's. V19 is read before `stray`'s walk attribution, as 1.2 orders it: a segment with walks AND `side_ends` would read a walk into a real donor field as the game's V19 -- O4 has no walks (2.1), so the order is moot for it. |
| 12 | A1: `self.end_places` | "`self.end_places = sorted({place(f, self.members) for f in self.ends})`" | Computed from whatever `self.ends` is, so a stage that passes `end_fields` (a rehearsal; R-GATE's member(150) on F) is cut at its places too -- CI14's fix on the drive's side. For every O1-O3 stage (real end fields) the places are the fields: G3, G10, G17 byte-identical, G7/G12/G13 green. |
| 13 | A1's drive test | "F reaches member(153) ...; V19 ...; WITHOUT `side_ends` V11" | On the fake's places -- 30820 "150" (the start), 30830 "153" (the end), members 31243 and 31245 -- plus S's arrival in real "153"; the end row's seen frame is member(153)'s first row's. The V11 case gives the end list as `end_fields` [31245] with no `side_ends`: the driver as it was for an F side ending in a member. Mutants run, each failing its test: `Segment.cut` at the raw end fields (the pure test), `end_row()` on raw ids (the drive test: `end_row` unseen) and rule 2 without V19 (the drive test: V11). |
| 14 | A2: the language clause | the uk line or no P-TEXT row: rev. 1's `SCOPE_LANG`; P-TEXT rows with no block-2 defect: the per-language clause | `o3_prima_vista.scope_lang(session)`, read by `report_extra`. A third case the design did not name: P-TEXT rows recorded with ANOTHER defect (not O1's copy) -- neither clause would be true, so the clause names the recorded languages ("block 2's fr copy is another language's stock text (the KNOWN-KIT-DEFECT line below)"). O1's copy is matched as its line reads, `KNOWN-KIT-DEFECT uk: ships stock us `; a uk line beside other defects keeps `SCOPE_LANG` (its uk statement stays true; every line is listed below it). story-o3 and every o3_dryrun session record O1's line: G15-G17 byte-identical. The module docstring's THE SIDES notes that block 2 is shared with O4's chain. |
| 15 | A2's test | "a synthetic O3 session each way and one with no P-TEXT" | Through `O3.report_extra` itself on synthetic sessions (only the language line is read): O1's uk line (story-o3's form, and o3_dryrun's `TEXT_DEFECT`), no P-TEXT row, no preflight at all, a clean P-TEXT row, another language's defect. Mutant run: the defect clause printed unconditionally (rev. 1) -- the clean case fails. |
