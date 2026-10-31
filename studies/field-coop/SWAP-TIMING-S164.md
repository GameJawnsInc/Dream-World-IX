# Field-swap timing, round 1 (engine round s164)

**Status: rev 4 (2026-10-30). BUILT: round 1 and owner decision 8's arrival guard (`ARRIVAL-GUARD-S164.md`) are compiled, deployed and captured in `memoria-patches/s164-netsync-field-swap-timing.patch`; deployed as `29f351aaacd3f3d8`. The final bench is green: duo act 45/45 and every duo calibration word exact, solo act 43/43, every regression green on that build. The README row is written. Next: the two-PC session.** The owner chose round 1 of `FIELD-SWAP-TIMING.md` §4, with the 12-tick follow fade for a guest that is not already faded. This document combines five item specs into one round: A, the instrument; B, the orphan hold and the lever scheme; C, the own pass; PIN and LIFE; D and E, the fade. Rev 2 applied the owner's resolution of every finding from the three reviews of rev 1 (timing-race T1-T14, regression R1-R9, proof-bench F1-F14). Rev 3 applies the findings against rev 2 that survived adversarial verification (§ What changed from rev 2). Rev 4 records the arrival guard and the first duo run's bench fixes (see What changed from rev 3).

It builds on s163 (`Assembly-CSharp.dll` `7687fb583c0e6189`). Engine cites are against `C:\gd\FFIX\Memoria\Assembly-CSharp` at s163 (stock `6b8bb2d5` plus the stack through s163). Field-script cites are against the HW exports in `C:\gd\FFIX\reference\test2\` (`reference/field-manifest.tsv`: 350 = `test2_93`, 351 = `test2_94`, 352 = `test2_95`, 359 = `test2_102`, 450 = `test2_112`). Rev 4's re-located cites say "with s164": they are against the clone with s164 and its arrival guard applied. Kit cites are against this worktree. An engine claim with no label was read in the code. **INFER** marks a deduction, and each one names the bench row that settles it.

## The problem

1. **The timer.** A parallel follow lands the guest 1.04 s behind the host (n = 23). The follow's 0.9 s timer is about 90% of that (`FIELD-SWAP-TIMING.md` §1). On a duo (one desktop), follow start to commit measures 0.885-0.912 s.
2. **The fade starts late.** The intent leaves at the host's MAPJUMP (`EventEngine.DoEventCode.cs:1040`). Stock exits fade *before* `Field()`, so the guest's 24-tick fade starts after the host's own fade has already ended (§2; `NetSyncClient.cs:215-216, 4665-4672`).
3. **3x and the flash.** At 3x the guest's fade ends after 267 ms, and the screen then stays black for about 630 ms more. The timer subtracts `Time.deltaTime` once per Unity frame (`NetSyncClient.cs:6918`). `Time.deltaTime` follows `Time.timeScale` (`QuitUI.cs:54-55` sets it to 0; the ~ menu's time-scale buttons set others, `Ff9mkDebugMenu.cs:1338-1343`), but the booster never touches `timeScale` or the frame rate: it runs `FastForwardFactor` main-loop ticks per frame's worth of `deltaTime` (`FPSManager.cs:77-99`; `NetSyncSpeed.cs:12-13`). So the fade runs three ticks a frame while the timer still counts 0.9 s of frame time. The follow fade also flashes a screen that the copy's own script already darkened (`SceneDirector.cs:671-675`).
4. **The bounce.** 2 of the 5 scripted Dali transitions bounced. The copy's own `Field(352)` ran while the host was loading, `LastHostField` read 0, and the guest reloaded 351 first. That cost 1.4-1.5 s plus a visible reload (§1; `NetSyncClient.cs:557, 589-594`).
5. **The instrument.** `Memoria.log` stamps whole seconds. It cannot see the 0.9 s timer, the lane latency or the 350 ms close floor. Every tightening also makes Finding 11 more reachable: the guest's line on 351 was orphaned while the host's control was off (§3 A, B).

**Expected after round 1 (§4):**
- No bounce reload when the intent arrives before the own jump.
- Scripted transitions land 0.1-0.3 s after the host when the last line before the exit stayed fully shown on the host for at least the copy's lag + 350 ms. A faster host carries the copy's catch-up lag into the landing: a host close on a line still typing is held until the page has shown `MinShowMs` (`NetSyncDialog.cs:51, :1337-1343`), and the exit script runs a fixed chain from that close (P7).
- Gateway walks land about 0.5 s behind (12 ticks).
- Every 3x follow is about 630 ms shorter.
- No flash, except on an Add-mode (white) exit, which keeps today's flash (risk 18, G4).

## What changed from rev 1

| Id | Resolution | Where |
|---|---|---|
| T1 | The pin gains spent-nonce memory, as the intent cache has: consuming, dropping, aging or a `here` refusal leaves the nonce spent until a frame carries a different nonce. Rows c13-c15, mutant `pin_recapture_after_consume` | PIN rules; PIN row table |
| T2 | The `afterorder` lever, its LateUpdate hook and the solo L-ORDER row are dropped. Order independence is shown by pure rows `r-order` (act: Keep) and `r-order-old` (s163: EndOld, the R1 hole), plus DESK and REST run under `life old` with `last_life_ms` and the host's frame rate recorded | LIFE; levers; DA-PROBE; risk 5 |
| T3 | L-CLOCK logs `Time.deltaTime`, `Application.targetFrameRate` and a smoothed fps; the block gains `clock.fps`, `intent.host_fps` and `intent.emit_dt_us`. DA-PROBE's under-100 ms branch is pre-registered as "the other Unity order OR a frame time under 10 ms / FastForwardFactor". HonoBehaviorSystem's per-scene re-creation is noted (INFER) | The clocks; conflict 11; LIFE verdict; DA-PROBE |
| T4 | The commit-to-changeScene tick window is stated as a law, with selftest rows `commit_then_own_same_tick` (s1-s5). `JoinGraceTicks` goes from 2 to 3, re-derived from the per-tick order. The `own` calibration word is held to REST-OLD; CAL and DESK keep `own act` | C (the law); D+E (grace); duo calibrations |
| T5 | Pins are keyed by field (a 2-entry map) and kept while a follow targets their field. Rows d1-d4 and t1-t5, mutants `pin_single_slot` and `pin_target_pending_only` | PIN rules; PIN row table |
| T6 | "Watched" is judged by receive-sequence continuity (Accept counts TypeState payloads). Age counts from the host's landing as seen by the guest, with a 10 s backstop when it is never seen. No main-thread stall lever exists; rows c3-c5 and pinbench `skip <n>` (P-LATE, P-RESCUE) cover the stall. The same change adds a guard found while applying R6: no off-field upgrade after the landing is seen (row c18, mutant `pin_upgrade_after_landing`), and a battle frame never counts as off-field (rows o1-o4, mutant `pin_battle_is_offfield`) | A transport probe; PIN; solo P legs |
| T7 | The Left clear appends " (the cached field)" when the new field is the cached one; the landing hook's unreachable "spent" wording is removed. C-CACHE expects the "I left" line | C clears; C-CACHE |
| T8 | Leg C runs under `swap fade old`, registered as such; C-PEND is aimed inside the old 0.9 s window | Solo C legs |
| T9 | `Due` counts `_dlg.RingAhead` as held. Rows `ring_ahead_waits` and `ring_ahead_at_timer`, mutant `due_ring_ahead_free` | D+E DueRule; D+E row table |
| T10 | Deferred to round 2. The claim is corrected: the commit waits for black OR the timer fallback. Accepted risk 18, measured by the "fallback: the fade never read black" due line | D+E; risk 18 |
| T11 | The swap clock reads QueryPerformanceCounter through a kernel32 P/Invoke; Stopwatch is a flagged fallback (`clock.src`). L-CLOCK prints raw ticks and Hz. Rev 1's one-clock law and its mtime fallback are removed. The timer is described as `timeScale`-scaled, and the booster's mechanism is stated from `FPSManager` (rev 1 called the timer unscaled) | The clocks; The problem item 3; risk 4 |
| T12 | `SetStateWatched(frame)` sets the slot and arms the watch under one lock and returns the seq. DA-LANE's numeric windows become reported numbers | A transport probe; DA-LANE |
| T13 | EndStands also needs `LandTailMs` (1000 ms) since the host's landing. Rows `r-slowload`, `r-slowload2`, mutant `life_no_land_tail` | LIFE rules; LIFE row table |
| T14 | `NetSyncClient.cs:5854` is `NoteGuestWorldJump`'s world-exit cancel: it calls `Clear("world")`, and `world` joins `fade.ends` and `fade.last.by`. The session-reset clear claim is removed (s42: a follow in flight always finishes) | D+E call sites; state block |
| R1 | The landing stages section 0 only from the pin; party wraps (sections 1-3) and dress (section 8) come from the latest frame (`NetSyncState.ApplyStorySplit`). Row f1, mutant `party_follows_story`, solo P-PARTY, duo DP-PARTY (reach-gated). Risk 10 rewritten as fixed | PIN; benches; risk 10 |
| R2 | Duo watch row DA-ARRIVE on CAL2 and DESK with a dressed guest, `fade old` as its control. No arrival guard is pre-built; a red at act is a real defect to fix before ship, with the planned guard written down. Rev 4: the guard is built (owner decision 8), DA-ARRIVE is its calibration, and CAL2 and DESK are watches reported apart | Duo benches; risk 14 |
| R3 | PIN excludes world-rejoin landings in round 1 (`fromWorld -> Latest`, counted `pin.world`, mutant `pin_used_from_world`). Ten benches join the regression gates | PIN; gates before the README row |
| R4 | `NoteHostFrame` drops a capture when my field equals the announced field (`pin.here`). Rows c16-c17, mutant `pin_kept_when_here` | PIN |
| R5 | A relock keeps the window's original `OrphanSince` (`OrphanSinceRule`). Solo B-BLIP2, mutant `relock_restarts_read` | B; solo B legs |
| R6 | A battle that started on the intent field keeps section 4 up to the 10 s cap. Rows `r-battle`, `r-battle-cap`, `r-battle-old`, mutants `life_battle_left` and `life_battle_no_cap`. No Main_Init-battle field is pinned, so DL-BATTLE is a SelfTest-only claim | LIFE |
| R7 | Same resolution as T14 | D+E call sites |
| R8 | The `:7780` hunk is an addition after the existing `_glHostHoldsInput = v.HostHoldsInput;`, never a replacement; a kit source test asserts the original line | B call sites; kit side |
| R9 | The refusal literal is `[NetSync] own Field(` (rev 1 had a doubled prefix), pinned in battlewire's builder and a source test | C log lines; kit side |
| F1 | As T11. K-CLOCK becomes a load-time precondition: cross-game rows go VOID with a reason, never red; off Windows it is a SKIP with a reason | The clocks; K-CLOCK; DK-CLOCK |
| F2 | As T8, and DC-B splits into (a), a behaviour row on any path, and (b), an own-pass row on REST-OLD. `counts.follow_won` measures D+E's pre-emption (DC-WON) | Duo REST; state block |
| F3 | As T2 | LIFE; levers; benches |
| F4 | DA-PROBE's `life` predictions and the Unity-order falsifier are registered on MAPJUMP legs only (DESK, REST); CAL's debug-warp figures are exploratory (DA-PROBE-X). The state gains `intent.site` | A; state; duo benches |
| F5 | New `ff9mapkit/tests/test_coop_field_swap_timing_bench.py` in the s163 shape; fakegame gets a clock seam; K-CLOCK off Windows is a skip | Kit side |
| F6 | `last.due_t` and `fade.last.due_t` are published; `fade.last.ms` is the due. A-DELAY and DA-CAL judge `commit_t - due_t` within one follow; the cross-leg comparison is a reported number | A; state block; A-DELAY; DA-CAL |
| F7 | LIFE, PIN and D+E row tables are in this document, with a mutant-to-row map for every item. `quiet_equals_loud` sweep with mutant `quiet_no_exit_hold`; OpenClosesRule mutant `open_leaves_previous_open` | SelfTest |
| F8 | CAT pokes go on the host before its Select pick (`byte 297` bit 0 set, `flag 2075 0`), read back first. Every duo leg's warp, scenario and pokes are pre-registered as data, read from the HW exports and the two-PC logs | Duo legs and setup |
| F9 | The harness-armed read is dropped. Levers follow the s163 shape: role checked at set time, released on every role through `HarnessReleaseBench`, plain getters. Owner question 6 is removed; conflict row 4 is rewritten | Conflicts; levers; owner decisions |
| F10 | As T12; DA-LANE treats `arrived_t == -1` or a missed first send as UNREACHED for that transition | A; DA-LANE |
| F11 | (a) DA-CLOCK becomes DK-CLOCK, "K-CLOCK holds on both games". (b) DB-SHAPE and DP-MARK are timed from `clock.now_ms`, so `stamps` reds exactly DA-LINES. (c) DP-UP gains a reach clause | Duo benches |
| F12 | F-REASSERT and F-KEY are added. No `bkflash` lever; owner default 1 (no flash on the backlog path) is taken | Solo F legs; owner decisions |
| F13 | CAL dwells at least LineWindowMs + 1 s per field. K-RELEASE re-arms (`netsync selftest 1`, `bench 1`, `stateevery 1`) before its final follow | CAL; K-RELEASE |
| F14 | `BodyThereRule` is shared by the host path and the selftest branch. Rows b1-b4 (`r-bench`), mutant `body_any_actor` | LIFE |

## What changed from rev 2

The ids are the findings against rev 2 that survived verification (high and medium first, then the low ones). Where a finding could be closed by removing a mechanism, rev 3 removed it.

| Id | Resolution | Where |
|---|---|---|
| S1 | Applied, by removal. R6's battle term is dropped. Every field battle goes through `SwirlScene` (`HonoluluFieldMain.cs:337`; `SceneDirector.cs:556-560`), where `gMode` still reads 1 and the FieldMap is gone, so the term could never fire. Rev-1 R6 was also not a regression: `_Swirl` waits at least 2 frames on the live field before it loads (`SceneDirector.cs:556-557`), so s163's clear and LIFE's Keep both see the landing. Rows `r-battle`, `r-battle-cap`, `r-battle-old` and mutants `life_battle_left`, `life_battle_no_cap` are removed; row `r-swirl` pins the swirl's EndLeft; DL-LEFT stays, annotated. PIN's b5 term goes too: no battle frame carries section 4 | LIFE; PIN; duo LEFT; risk 25 |
| S2 | Applied with a different fix. `Due` no longer reads `_dlg.RingAhead`, which is always false at :1668. A Black verdict must survive one dialogue pass. The first Update that judges the commit ready returns `Prime` (a Wait). Only the next Update commits; its backlog read includes everything observed at :2168 and merged at :2176 in between. Rows `black_primes_first` and `prime_then_black`; mutant `due_no_prime` replaces `due_ring_ahead_free`; F-FAST gains the live `fade.last.primed` clause | D+E; D+E rows; F-FAST |
| S3 | Applied with a different fix, the skeptics' simpler one. "Watched" by receive-seq continuity is gone. The host stamps its own boundary: section 4's body gains a fourth byte whose bit 0 means "built after my landing hook" (`_intentLanding != Pending`). The guest pins the first frame of a nonce whose bit is clear. A stall, a re-send, bunching, the relay, a reconnect or a bridge cut can no longer mislabel a frame, because the label rides in the frame. An s163 host's 3-byte section reads as landed, so the guest stages the latest frame. `InSeq`, `seqGap`, the off-field upgrade, `PinOffFieldRule`, the b3/lane `landSeen` INFER, pinbench `skip`/`offfield` and row P-RESCUE are removed; pinbench gains `landed` (P-LATE), and DP-UP becomes DP-HALT, which checks that later pre-landing frames carry the same story | A transport probe; PIN; levers; state; solo P; duo; risks 22, 24 |
| V1 | Applied. The split gets a target: `NetSyncState.ApplyStorySplitTo(story, party, target)`, with `ApplyStorySplit` as its live wrapper. `BenchPinLanding` calls `ApplyStorySplitTo` on a scratch array, so P-PARTY runs the shipped split. Live SelfTest row `pin_split_applies`; a kit source test pins the :929 expression. The leak half is resolved as G2 | PIN; SelfTest; kit side |
| V2 | As S2 | D+E |
| V3 | Applied. The selftest `GuestTick(fld, -1)` moves to right after `ServiceSpeed` (`NetSyncClient.cs:1784`), before the `inScope` return, so it runs on every selftest tick, as the client's call does. C-CACHE also requires that no "field 352 loaded" line prints. A kit source test pins the placement | C; C-CACHE; kit side |
| V4 | Applied, in the skeptics' form. The read clock keeps running through a hold; the word "pauses" is corrected. B-BLIP2 opens a fresh line and blips first at t0 + 1.0 s. Green is exactly one relock, then the auto-close on the first orphaned sample at or after t0 + AutoReadMs (+0.3 s). Every B sub-leg after B-RELEASE opens its own line. S5 is tightened to the same tick | B; B rows; solo B legs |
| V5 | Applied. A new CAL sub-leg, ARRIVE, warps the host onto a scratch copy of the bench field with `[camera] entry_settle = 68`, about 2.27 s of wordless control-off on both copies. DA-ARRIVE gains an exposure reach clause on `netsync.stepout.base.age_ms`; the CAL2 and DESK arrivals stay as regression watches. ARRIVE predicts a dwell OUT at act, so by R2's own rule the arrival guard must land before ship. Rev 4: ARRIVE is retuned to `entry_settle = 64` (about 2.13 s) with a pre-registered retune rule, and is the guard's calibration | Duo CAL; DA-ARRIVE; gates; owner decision 8 |
| G1 | As V5. The speed-mirror half is a more frequent case of a risk s163 already accepted (`SPEED-MIRROR.md:120-121`); risk 14 says so, with no new row | Duo; risk 14 |
| G2 | Applied. `BenchPinLanding` sets a swap-owned `_pinBenchMirror` before its parse. It does not use `NetSyncParty.BenchMirrorArmed`, which would turn a later diorama's seat into SeatBench (`NetSyncDiorama.cs:2918-2921`). `HarnessRelease` and `swap clear` call `NetSyncParty.Clear()` when the flag is set, and the release line names it. P-PARTY reads `mirror_party` before leg P's closing `swap clear`, and null after it | PIN bench; release; P-PARTY |
| P2 | As V4 | Solo B legs |
| P3 | Applied. The solo `pin` lever is scoped to P-PIN and P-PARTY (`swap pin act` before the guards), and the duo's to MARK and the 1.2 s MENU run. DP-MARK and DP-DEFER are REACHED only when the landing's held entry was `pre` (`pin.last_use_quality`); otherwise they are UNREACHED with the reason | Solo P; duo; state |
| P4 | Applied. C-PEND's reach is keyed on the own-jump edge (`last.own_t`, with `session.follow.pending` 352 in the sample before it), never on the pass line, and its `own` red has an explicit marker. A predicted-red row that reads UNREACHED fails its calibration | Solo C; the reach rules |
| P5 | As V3 | C |
| P6 | Applied. At scenario 2600, entrance 15, the desk scene leaves through `Dagger_Loop` case 23 (`test2_94.txt:3850-3879`). After text 139 closes, it runs `Wait(100)`, `Wait(30)`, `FadeFilter(6,30)`, `Wait(30)`, entrance 3, `Field(352)`, and lands on 352's text 142 (`test2_95.txt:64-69, 1430-1435, 1649-1654`). Δ is anchored at text 139's close. Leg C's `fade old` rationale and DC-WON are re-derived from ActionRule's 12-tick Join/Hurry split | Solo C; duo REST; predictions |
| P7 | Applied. DC-B(a)'s gap is judged net of the copy's measured lag at text 139, and the raw gap is reported; the 0.1-0.3 s expectation is qualified. DESK states its re-press cadence. DC-B(b) reports its reach rate across D and needs one REACHED run for `own` | Duo DESK, REST; The problem |
| P8 | Applied. The stand-in test runs legs K, A and B only. On an engine, a solo P, L or F leg whose op was acked but whose key stayed at its sentinel is red ("the engine never ran X"), never UNREACHED. DA-LANE gains a reach floor: one reached transition per leg, else red. Source tests pin the three call sites | Kit side; the reach rules |
| I2 | Applied, in the skeptics' form. `OwnFieldPass` keeps its Boolean, writes `_ownLastTerm` and prints nothing. `NoteOwnJump` is the single printer and runs after `JoinRule`: it prints C's pass line, C's refusal line with the final verdict's outcome words, or L-OWN. L-OWN gains a Through outcome; builder rows cover a refusal followed by each verdict | A; C; A rows |
| I4 | Applied. The release half is resolved as G2. Frame B is built through the real encoder: `SnapshotAll()` under the `SlotSource` seam (`NetSyncParty.cs:81, 497-499`), restored in a finally, so no section-1 byte walker is needed | Levers |
| I5 | Applied, in the skeptics' form. Whether to keep the read clock is decided at the hold's falling edge: `KeepRead = (why == Control)`, consumed by the next re-orphan. A Busy, Event, Relay, Left or Forgot end restores s163's restart. `CtlRelocked` is renamed `KeepRead`. Scenario S6, mutant `relock_keeps_after_busy` | B |
| I6 | Applied by S3. The landed bit rides in the frame, so the first frame after a reconnect (post-landing) reads late. The redial sentence is corrected: an in-transport reconnect or a bridge cut keeps the frames object | A transport probe; PIN |
| S4 | Applied by S3: no lane term remains | PIN |
| S5 | Applied in part: the `CtlRelocked` half as I5, the wording as V4. "Credit the held time" is declined: on B-BLIP2's schedule a pause would also close after one relock, and R5 wants the running clock | B |
| V6 | Applied. DC-WON's prediction is re-derived from ActionRule. A new judged row, DF-GRACE (DESK: a Join start ends by `own`), falsifies the `Wait(25)` resume-tick INFER | Duo |
| V7 | Applied by S3 (no receive-seq plumbing remains) and P3 (the DP reach clause). DP-STALL is declined: a stall now matters only when it spans the host's landing, which row c3 and the live codec row cover | PIN; duo |
| G4 | Applied, the cheap option. Outcome 5 and risk 18 name the Add-mode (white) exception; the start line logs the slot's mode | The problem; D+E log; risk 18 |
| P9 | Applied. battlewire gains `_i64()` / `_i32()` two's-complement helpers for every fixed-width twin; a kit test asserts the `ms_naive` twin differs at `tsc_40_days` | Kit side |
| P10 | Applied. Leg C's Δ and DL-DEFER are timed from state keys (`last.own_t`, `last.follow_t`, and the close and menu samples' `clock.now_ms`) | Solo C; DL-DEFER |
| P11 | Applied. F-RECHECK sends `lock 1`, and each F sub-leg's lock state is stated. L-WIRE and the undefined `intent.wire` are removed; the live `frame_carries_4` row carries the claim | Solo F, L; state |
| I7 | Applied: `(Byte)0` in the conditional | B call sites |
| I8 | Applied. One hunk per edge: the `next` end and the `reset` end are each one `NoteIntentEnd` call that A and LIFE share; `NoteEmit` loses `was` | A; LIFE |
| I9 | Applied. `HoldVerdict` is `internal static` and pure over every clock; `HoldInputsNow` gathers the live inputs for both callers; the sweep saves and restores NetSyncAte's statics | C; SelfTest |
| I10 | Applied: `StartSceneAt` :7038 "ended" and :7039 "rose", both stamped; the :7038 form joins `S163_FORMS` | A; kit side |

## What changed from rev 3

Rev 4 builds owner decision 8 and folds in the first duo run (run 20261030-054437). That run confirmed rev 3's predicted DA-ARRIVE red at act (the DA-ARRIVE row under Benches) and found no other engine defect: its other reds were bench defects, fixed in the duo bench and mirrored in the rows below. Every change is tagged `[ff9mapkit netsync s164]`.

| Change | Resolution | Where |
|---|---|---|
| The arrival guard | Owner decision 8 is built as `ARRIVAL-GUARD-S164.md` (its spec, review and build log) and folded into s164: at my landing a wordless base's dwell counts from max(B, min(Hs + 1040, B + 1040)) (B the base start, Hs the host's landing as I first saw it), behind `swap arrive act\|old` and the selftest's `swap arrivebench <lead_ms>`. The proof line gains 75 rows and 37 mutants (501 / 183) and the tail `, arrival lead 1040 ms`; s158's proof line does not move | Levers; state block; SelfTest; files; decision 8 |
| ARRIVE retune | `entry_settle` 68 -> 64 (about 2.13 s), with a pre-registered retune rule read from CAL2. At 68 the guarded green missed whenever O + d7 - dx >= 273 ms: a publish-phase flake on a correct guard | Duo CAL |
| DA-ARRIVE | Now the guard's calibration. Reach: overlap >= DwellMs + 100 ms AND (raw base peak >= DwellMs OR a dwell OUT). The green must be attributable to the guard; a red names its cause (never anchored, guard defect, margin miss). An unfit clock voids only the overlap clause and the cross-game reports, so DA-ARRIVE leaves `CROSS_GAME`. The fade-old controls are judged with the gate; the dressed watches are reported apart, never judged | Duo rows; reach rules; predictions |
| DA-GUARD | New judged row, probabilistic and one-game: every reached act landing anchors (`arrive.lead_ms` non-null), with a floor | Duo rows; reach rules |
| `arrive` word, `life` scope | The duo's `arrive` word reds exactly DA-ARRIVE. `life` holds `life act` for the two ARRIVE runs, because `life old` sends no landed frame and would starve the guard's anchor. The solo `arrive` word reds G-HOLD, G-DELAY and G-LATE | Calibrations |
| `BASELINE_RED` | Empty: rev 3's DA-ARRIVE red at act is now the `arrive` word's red | Duo calibrations |
| World gates | `coop_world_wait` and `coop_world_battle` fold an arrive clause into every world-rejoin row | Gates |
| Risks 7 and 14 | `ArrivalLeadMs` joins the seeds; risk 14 carries the guard's bands and residuals | Risks |
| DA-ARRIVE's DESK watch | The first run's five DESK "watch" OUTs were 352's lawful 7.9 s wordless scene, read through a 351 window that never ended (the desk scene never gives control back on 351). The 351 window now ends at the 352 landing | DA-ARRIVE |
| DF-FLASH | A hurry is lawful: ActionRule hurries a heading start with more than 12 ticks left, from the current colour and with no flash, and DC-WON predicts it, so the first run's D 0.3 red was a bench defect. A hurry must still end by `black` or `own`; a wipe is red whatever ends it | DF-FLASH |
| DP-DRESS | The judge wanted `want_char` = the host's leader, which is the double itself; the first run read (want 3, leader 2) six times, the correct dress. It now wants the latest frame's section-8 pick, never the leader | DP-DRESS |
| DB-SHAPE, DB-BIT | Anchored on the host_flags b0 RISE on 351: rev 3's "first b0 sample on 351" read field 350's sticky scene (-2598 ms) | DB-SHAPE; DB-BIT |
| MENU | A mirroring guest has no main menu (s38's spectator-field refusal, s121's buzz), so the first run's MENU leg timed out. The guest now holds its Pause screen and closes it with cancel; a Pause that never opens is VOID. The host marks at its landing hook | MENU; DL-DEFER; DP-AGED |
| MARK | The host's body stands about 1.77 s after its landing on 30602, after the guest's landing (the first run's -986 ms), so the mark fires at the host's landing hook | MARK |
| LEFT | On 30602 the intent had ended "stands" about 1.7 s before the battle's send, so the swirl never fell inside section 4's life. The leg now exits to HOME and sends the battle 0.8 s after the landing hook; a pre-send sample that is not that intent live, or an end that races the swirl, reads VOID | LEFT; DL-LEFT |
| OPEN | LEFT's flee lost its roll and OPEN burned its seat on a host still in battle. LEFT now escapes first (Zidane's Flee at a host prompt, else the bumper roll; up to 4 attempts, re-rolled only while the party holds half its HP), fights only as the last resort (a wipe would Game-Over both games), and waits for the host's field HUD and the guest back from its diorama; every seat warps the host only on its field HUD (a 10 s grace), and a battle still up reads VOID with that cause | LEFT; OPEN |
| DF-GRACE, DF-FLASH | Fix round 3, from the guarded duo runs (20261030-115757 at act, 20261030-121353 under `arrive`): every DF-GRACE red was a follow that started on 359 AFTER a bounce reload and Joined the reloaded field's idle load-black, which `own` can never end. Both rows now reach only a follow whose copy could still exit (the record followed, `fade.last.field` is 351, and `last.own_t` is unset or >= `last.follow_t`); the post-bounce follows are listed apart, never judged (the s158 shape: DC-WON, risk 8). From its review, a stale `fade.last` makes a row VOID only when no judged run is red. Re-judged, act reaches 4 of 6 and `arrive` 1 of 6, all `own` | DF-GRACE; DF-FLASH; open items |
| DL-DEFER, DP-DEFER | Fix round 3: the MENU hook's awaited cancel starved the watch for its accept-to-ack span (about 134 ms, s157's law), so DL-DEFER's "first sample off Pause" was the ack (the guarded runs' -131 / -132 ms). The close is now bracketed off the guest's ring, the cancel goes out without waiting, and DL-DEFER reds, and DP-DEFER is UNREACHED, without the record seen while paused. From its review: a guest that never lands on AWAY reds DL-DEFER (VOID when its Pause never closed); the cap's frame is DA-CAL's measured one, else the ring's own step; a follow inside the bracket is placed by the ring's frame counter (at most one unsampled frame); the width VOID stands only where the close's place decides the verdict. Re-judged off the saved rings: follow - close -16 / +1 ms, green | DL-DEFER; DP-DEFER |

## Conflicts between the specs, and what this document chose

| # | Conflict | Chosen | Why |
|---|---|---|---|
| 1 | Lever verb: A, B, C and PIN-LIFE use `netsync swap`; D+E proposed `netsync followfade` | One sub-verb, `netsync swap <op>`. D+E's ops become `swap fade ...` and `swap blackout` | One lever scheme means one HarnessAgent case, one release and one driver table |
| 2 | Proof line: A "field swap", B "field-swap", C "own-pass", D+E "follow fade" | One line, `field swap selftest: OK (...)`, from `NetSyncSwap.SelfTest`, as the proof block's last line | The task asks for one proof line |
| 3 | Lever roles: A and PIN-LIFE any role; C client or selftest; B a role table | B's table. Guest-side levers are refused on a host. `life` is refused on a client. `stamps` and `clear` are legal on any role | A calibration sent to the wrong duo game then fails at the step instead of reading as an unpredicted green |
| 4 | Leaked-lever guard: C role-checks in its getter, PIN-LIFE relies on the release alone, A, B and D+E proposed a getter that also reads the harness-armed flag | The s163 shape. The role is checked when the lever is SET (the refusal order below). Every lever is released on every role by `NetSyncSwap.HarnessRelease()`, called from `NetSyncBattle.HarnessReleaseBench` after s163's `NetSyncSpeed.HarnessRelease()` (`NetSyncBattle.cs:6758, 6840`). Getters are plain. No Netsync file reads HarnessAgent | `HarnessReleaseBench` runs on every `HarnessSelfTest(false)`, above its forced-role return (`NetSyncClient.cs:9403-9407`): disarm, fault, `reset`, and the release a harness diorama defers to its teardown (`HarnessAgent.cs:2353-2361`). While that diorama holds the release, the selftest role is held too (`HarnessAgent.cs:2317-2325`), so a getter that added the harness-armed flag to `IsSelfTestRole` would guard nothing there. s163 already ships an any-role lever on the release alone (`NetSyncSpeed.LeverOff`, `NetSyncSpeed.cs:91-93`). The residual (a throw inside `HarnessReleaseBench` before this round's call) is shared with every netsync lever since s133 (risk 20) |
| 5 | `delay` range: A 0-5000, B 0-2000 | 0-2000 | The delay holds a black screen with control off. 2000 still covers DA-CAL's +200 and A-DELAY's +300 |
| 6 | Three guest readers of section 4 (A's seen edge, C's cache, PIN's capture) at three call sites | One site: `NetSyncSwap.NoteHostFrame`, in `ObserveHostDialog`'s new-frame branch, right after `NetSyncSpeed.NoteHostFrame` (`NetSyncClient.cs:7808`) | It runs every client Update (`:2167-2168`). It runs before `ServiceIntentFollow` (`:2170`), so a follow started this Update already has its cache and its pin. PIN reads only section 4 (the nonce, the field and the host's landed bit), so it needs nothing else from the frame. C's cache aging runs in `NetSyncSwap.GuestTick`, right after `:2168` |
| 7 | C asked for the pin's frame to live in its cache record | Kept separate; both written at the one site | The cache ages out at 2000 ms and clears once the host's lane moves past. A pin lives until it is consumed, superseded for a field no follow targets, or aged (2500 ms from the first frame I saw with the host's landed bit), and must survive a "host past" clear |
| 8 | Two lines for one own jump (A's L-OWN and C's pass line) | Exactly one line per own jump. C's pass or refusal line if C decided, else A's instrument line | One line per edge. Line classes are told apart by prefix (§ Log classes) |
| 9 | `stamps off`: A wanted "the exact s163 log" | It removes stamps, the waited/shown tails and every `[NetSync] swap` line. Behaviour lines from B-E still print, without stamps | An instrument lever must never silence a behaviour change |
| 10 | Intent end words: A has landed/next/session; LIFE has stands/left/elsewhere/cap/old/reset | One vocabulary: `stands \| left \| elsewhere \| cap \| old \| next \| reset` | A's "landed" is the s163 self-clear, which is `old`. "session" is `reset`. LIFE's "replaced" is `next` |
| 11 | DA-PROBE prediction: A predicted from code a life under 100 ms and 1-3 sends; LIFE read four host logs | LIFE's evidence, registered on MAPJUMP legs only, with the frame rate logged | Details below the table |
| 12 | FT-CAL's 0.885-0.912 s describes today's fade | The DA-CAL leg pins the guest to `swap fade old`. DF-FAST measures the shipping figure | Under D+E an idle guest commits after about 0.4 s |
| 13 | E as a lever: B had `cut old`, D+E had none | `swap fade long`: D stays on, and the fast path fades 24 ticks | E is its own mechanism, so it gets its own calibration |
| 14 | D+E's five departures from the task | All five taken. The owner took the defaults on two: the backlog path without the flash (owner default 1), and Hurry instead of a literal "never re-init" (owner default 2) | Each keeps today's timing bound, and each has a lever or a follow-up that restores the alternative |
| 15 | C2 | Dropped | C's writer found it unsound (§C, "C2") |
| 16 | Five solo scenario files proposed | One solo scenario, `coop_field_swap_timing.py`, with legs selected by `COOP_LEGS`, plus the duo | LIFE's tape rows (T-*) are read from the duo's two state blocks instead. T-STORY becomes an engine counter (`pin.max_pre_diff`, the halted-VM check; rev 2 named it `pin.last_upgrade_diff`), so `coop_peer.py` does not change |
| 17 | Bounce counters in both A and C | One `counts.bounces`, incremented at the bounce branch | One owner per number |
| 18 | Driver capability name: A `coop_swap_timing`, B `coop_field_swap` | `coop_field_swap` | It matches the scenario names |

**Row 11 in detail: why LIFE's evidence wins, and what it does not settle.**
- In every scripted exit in the four two-PC host logs, "host scene: ended ... -- field change" prints *after* the new field's first-frame lines. Example: `twopc-s163-20261029/desktop-host`, lines 82-84.
- The scene machine falls on "field change" when `onField && fld != Field` (`NetSyncDialog.cs:2353-2357`).
- INFER: under the other Unity order, that line would print in the MAPJUMP frame itself. So on this desktop `NetSyncClient.Update` runs before `HonoBehaviorSystem.Update`, and today's section 4 lives about as long as the host's load.
- **The frame-rate confound (T3).** `SceneDirector.Replace(..., false)` starts `_Fade` with a fade-out time of `0.01 / FastForwardFactor` s (`SceneDirector.cs:516-538`). `_Fade` adds `Time.deltaTime / fadeOutTime` once in the starting frame and yields to the end of the frame before it tests again (`:259-270`). When `deltaTime` is under 10 ms / FastForwardFactor, `ChangeScene` runs only at the end of the next frame (`:276-282`), so the old FieldMap is still alive in that frame's `NetSyncClient.Update`, which then reads `fld == dest` and `onField` true. The live install runs uncapped with VSync (FieldFPS -1), so a panel above 100 Hz opens the R1 shape without any change in Unity order.
- **Per-scene, not per-machine (INFER).** `HonoBehaviorSystem.Instance` creates a new GameObject when none exists (`HonoBehaviorSystem.cs:12-25`) and the file never calls `DontDestroyOnLoad`, so the system is re-created on each scene load and its Update order against the persistent `NetSyncClient` is decided per load. DA-PROBE's samples across many transitions settle whether the order is stable.
- **MAPJUMP, not the debug warp (F4).** The evidence comes from scripted exits, which emit inside `HonoBehaviorSystem`'s `ServiceEvents`. A harness `warp` emits from `Ff9mkDebugMenu.Update` (`Ff9mkDebugMenu.cs:854-856, 2452`), a third MonoBehaviour whose order is undefined, so its figures do not transfer.
- The writer re-sends the state slot on every write tick (`NetSyncSocket.cs:386`; the 33 ms sleep at :800), so the number of sends is about the life divided by the write period.

## The clocks

- **The swap clock.** `NetSyncSwap.NowMs()` = `TicksToMs(qpc, qpcHz)`, an Int64 count of milliseconds, where `qpc` and `qpcHz` come from kernel32's `QueryPerformanceCounter` and `QueryPerformanceFrequency` through `[DllImport("kernel32.dll")]` (the assembly already P/Invokes kernel32: `Memoria/Speedrun/AutoSplitterPipe.cs:168-174`, `Memoria/Battle/SFX/SfxPluginIdentity.cs:59`). Every published `*_t` key and every log stamp uses it.
  - Windows documents QPC as one system-wide counter that runs from boot, so both duo games stamp on the same clock by construction, and the kit reads the same counter through ctypes. K-CLOCK checks it on every run instead of inferring it from Mono's Stopwatch.
  - **The fallback.** Off Windows, or if the P/Invoke throws on its first call, `NowMs()` uses `System.Diagnostics.Stopwatch` (written fully qualified, because a `using` would clash with `UnityEngine.Debug`) and the state reads `clock.src = "stopwatch"`. A Stopwatch value may count from the process's own start (INFER), so K-CLOCK then voids every cross-game row with that reason. Deltas inside one game stay valid. The choice is made once per process and logged in L-CLOCK.
  - Why not `Environment.TickCount`: it ticks every 10-16 ms (INFER), which puts a difference of two stamps off by up to ±2 frames, and the delay rows need ±1. An absolute value also goes negative after 24.9 days of uptime.
  - Why not `DateTime.UtcNow`: NTP can slew or step it, and its resolution follows the system timer.
  - `TicksToMs` uses the split form `(ts / freq) * 1000 + (ts % freq) * 1000 / freq`, which cannot overflow on a raw QPC count after months of uptime.
  - The P/Invoke is safe off the main thread. The host's dialog tap can run on the voice thread (`NetSyncClient.cs:7300-7305`).
- **The frame-rate evidence (T3).** The L-CLOCK line logs `Time.deltaTime`, `Application.targetFrameRate` and the smoothed fps that `FPSManager.GetEstimatedFps` computes (`FPSManager.cs:55-58`). The block publishes `clock.fps` and `clock.target_fps` on every game, and the host stamps `intent.host_fps` and `intent.emit_dt_us` (that frame's `deltaTime` in µs) at each emit.
- **Rule clocks stay as they are.**
  - B's dialogue keeps TickCount; `SettleClock` and `OrphanStep` do not change.
  - C's cache age and the PIN and LIFE ages are TickCount deltas (the tick-baseline law: read only while armed).
  - D's grace counts game ticks (`NetSyncField.KeyTick`), alongside today's float timer.
  - The swap clock is the only clock that compares two games.
- **Mapping a stamp onto the state ring:** every state sample carries `clock.now_ms`, so a stamp `t` is placed directly on the samples' own axis. New benches time rows on `clock.now_ms`; existing benches are left alone.

## Log classes

| Prefix | Class | Under `swap stamps off` |
|---|---|---|
| `[NetSync] swap: ...`, `[NetSync] swap #K ...`, `[NetSync] swap clock: ...` | instrument | not printed |
| `[NetSync] dialogue orphan: ...`, `[NetSync] own Field(...)`, `[NetSync] intent cache: ...`, `[NetSync] story pin: ...`, `[NetSync] transition intent ...`, `[NetSync] follow fade: ...` | behaviour | printed, without stamps |
| `[NetSync] field swap fault (<item> at <site>): ...` | fault, once per site | printed |
| `[NetSync] harness: swap ...` | harness | printed, never stamped |
| `[NetSync] field swap proof cost: N ms on this thread (quiet_equals_loud on K rule sets: verdict grid swept Vx, live hold grid Lx)` | diagnostic (review fix F09), no class | printed once per SelfTest call, never stamped; logged inside SelfTest, before the caller's `field swap selftest: ...` proof line, which stays the proof block's last line. It holds no `selftest: ` text, so no proof regex reads it |

- Every behaviour and instrument line ends with ` (t T ms)` while stamps are on. The stamp always goes at the very end of the `Log.Message` statement, after any closing ")". That keeps every literal the kit's source tests check (`test_coop_speed_mirror_bench.py:667`, `test_world_coop.py:684`).
- An edge reads the clock once, so its log line and its state key carry the same `t`.
- Instrument lines are gated on `NetSyncClient.SwapSessionRole` = `_enabled && (IsSelfTestRole || ((_role == "host" || _role == "client") && _instance != null && _instance._socket != null))`. One exception (review fix F07): the session reset's L-CLOSE logs on the liveness its caller captured BEFORE its teardown nulled `_socket` (`ResetSession(why, rode != null)`), OR on `SwapSessionRole`; every other instrument line still reads the gate live.
- Every fault fails open: the line names the fallback, which is today's behaviour.

---

## Item A: the instrument (millisecond swap stamps and the swap record)

Home: a new file, `Memoria\Netsync\NetSyncSwap.cs`, holding `public static class NetSyncSwap`. It also holds C's, PIN's and LIFE's rules, the round's levers, the state block and the one SelfTest.

### Rules (pure)

Constants: `LineWindowMs = 10000` (how long a landed swap waits for its first line); `RecordSpanMs = 30000` (how long a record can collect edges for the same field).

**Name tables (code = state and log name):**
- **Edges:** Emit 1 `emit`, Seen 2 `seen`, Follow 3 `follow`, Own 4 `own`, Commit 5 `commit`, Drop 6 `drop`, Land 7 `land`, Line 8 `line`.
- **Record states:** None 0 (null), Open 1 `open`, Landed 2 `landed`, Done 3 `done`.
- **Join verdicts:** Ignore 0, Open 1, Join 2, Reload 3.
- **Writers** (the last write of the next field before a load): None 0, Follow 1, Kick 2, Own 3, Bounce 4, Host 5.
- **Via** (name, then log words):
  - `follow`: "via the follow"
  - `kick`: "via the same-field kick"
  - `own`: "via my own Field()"
  - `bounce`: "via a bounce reload"
  - `host`: "via my own transition"
  - `same`: "a reload of the same field"
  - `other`: "another load"
- **Close reasons** (name, then log words):
  - `line`: "its first line"
  - `window`: "the 10 s line window"
  - `stale`: "never landed in 30 s"
  - `superseded`: "superseded by swap #N"
  - `next`: "the next swap (#N)"
  - `reset`: "the session reset"
- **Own-jump verdicts:** `pass`, `bounce`, `through`, `reload`, `ate`, `ate-redirect`, `world`.
- **Own-jump reasons:**
  - from s163: `host-field`, `same-field`, `ending`, `budget`, `not-host`, `fault`, `ate`;
  - from C: `pending`, `committed`, `intent`, `cache`;
  - C's refusals: `refused-world`, `refused-ate`.
- **Commit reasons** (D's due words): `black`, `timer`, `fallback`, `recheck`.
- **Out-of-band frame verdicts:** null (unknown), `sent`, `overwritten`, `none`.
- **Emit sites:** `mapjump`, `debugwarp`, `bench`.
- **Clock sources:** `qpc`, `stopwatch`.

```
Int64 TicksToMs(Int64 ts, Int64 freq)
  freq <= 0 || ts < 0 -> -1
  else (ts / freq) * 1000 + (ts % freq) * 1000 / freq     // no overflow at a 3 GHz counter after 40 days; exact at 3.579545 MHz

String StampText(Boolean on, Int64 t)            on && t >= 0 ? " (t " + t + " ms)" : ""
String WaitedShownText(Boolean on, Int64 t, Int64 seenT, Int64 pageT)
  on && all >= 0 ? " -- waited " + (t - seenT) + " ms, shown " + (t - pageT) + " ms" : ""
Boolean ParseStamp(String line, out Int64 t, out String bare)        // only a final " (t <digits> ms)" suffix
Boolean ParseWaitedShown(String bare, out Int64 waited, out Int64 shown, out String core)   // same suffix-only rule

Int32 JoinRule(Int32 edge, Int32 edgeField, Int32 myField, Boolean kick, Int32 recState, Int32 recDest, Int32 recFrom,
               Int64 recOpenT, Int64 now)
  kick                         -> Ignore                       (the s42 pairing reload is never a swap)
  live   = recState in {Open, Landed, Done};  inSpan = live && now - recOpenT < RecordSpanMs
  same   = inSpan && edgeField == recDest
  Land:  Open && inSpan && edgeField == recDest -> Join;  Open && inSpan && edgeField == recFrom -> Reload
         Landed && same -> Reload;  else Ignore              (a load never opens a record)
  Line:  Landed && edgeField == recDest -> Join, else Ignore
  Own:   edgeField == myField -> (Open && inSpan && myField == recFrom ? Reload : Ignore); else same ? Join : Open
  Seen:  same -> Join; edgeField == myField -> Ignore; else Open
  Emit / Follow / Commit / Drop:  same ? Join : Open

Int32 OpenClosesRule(Int32 recState)             Open -> Superseded; Landed -> Next; else None
Int32 CloseRule(Int32 recState, Boolean firstLine, Int64 openT, Int64 landT, Int64 now)
  Landed && firstLine -> Line;  Landed && now - landT >= LineWindowMs -> Window
  Open && now - openT >= RecordSpanMs -> Stale;  else None
Int32 LandViaRule(Int32 fld, Int32 writeKind, Int32 writeDest, Int32 recDest, Int32 prevField)
  writeKind != None && writeDest == fld -> the writer's via;  fld == prevField -> Same;  else Other
  (recDest is never read: s154's recorded-at-the-source law, NetSyncClient.cs:216-218)
Boolean DelayRule(Int32 delayMs, Int64 followT, Int64 readyT, Int64 now)
  delayMs <= 0 -> true;  readyT < 0 -> false (the caller stamps readyT = now);  else now - readyT >= delayMs
  (followT is never read: the delay counts from the commit verdict, never from the follow's start)
Boolean SeenRule(Boolean haveSection, Int32 nonce, Int32 lastSeen)     haveSection && nonce != lastSeen
Int32 OobVerdict(Boolean set, Boolean replaced, Boolean sent)          !set -> None; sent -> Sent; replaced -> Overwritten; else Unknown
```

The line builders `LandedLine`, `CommitLine`, `OwnLine`, `ClosedLine` and `ClockLine` are pure and return null when stamps are off. Three functions are not pure: `NowMs()`, `Stamp(t)` = `StampText(StampsOn, t)`, and `Stamp()`. Every entry point catches its own exceptions.

### The transport probe (NetSyncSocket.cs, NetSyncRelay.cs)

- `INetTransport` (:37-75) gains three members, following the s133 precedent of `ActionsDropped` (:62-64):
  - `Int64 SetStateWatched(Byte[] payload)`: sets the state slot exactly as `SetLocalState` does and arms the watch at that frame's set seq, under ONE acquisition of the frames lock, and returns the seq (T12, F10). The writer thread therefore cannot send the frame between the set and the arm.
  - `StateProbe ReadStateProbe();`
  - `void WatchStateSeqs(Int64 from, Int64 to);` (used to close the watch).
- `public struct StateProbe` is read all at once under the frames lock. Its fields: `SetSeq`, `SentSeq`, `Sends`, `Unsent`, `WatchFrom`, `WatchTo`, `WatchSends`, `WatchFirstTs`, `WatchLastTs` (raw swap-clock ticks, -1 = none), `FromSent`, `FromReplaced`, `InState` (the latest received payload), `InStateTs` (-1 = none).
- **`SetState` (:314):**
  - a slot replaced before any write counts `Unsent++`;
  - the watch's first frame replaced unsent sets `FromReplaced`;
  - every non-null frame increments `SetSeq`.
- **`CollectOutgoing` (:386):**
  - sets `SentSeq = SetSeq` and increments `Sends`;
  - inside the watch window it also increments `WatchSends` and records the first and last send ticks;
  - it sets `FromSent` when `SetSeq == WatchFrom`.
- **`Accept`, `TypeState` (:436-438):** records `InStateTs` from the swap clock's raw counter, beside `_inStateTick`. Rev 3 removes rev 2's receive counter (`InSeq`): PIN no longer judges by arrival (S3).
- `NetSyncSocket` (:609 area) and `NetSyncRelay.cs` (:121 area) forward the new members to `_frames`.
- **What renews the frames object.** `_frames` is a readonly field created once per transport (`NetSyncSocket.cs:549`, `NetSyncRelay.cs:47`). A config redial (`ApplyConfigChange`, `NetSyncClient.cs:1397-1400`) or `OnDestroy` (:2354-2355) drops the transport, and `Update` builds a new one (:2059-2062). An in-transport reconnect does not: `ClientLoop` and the relay's connect loop reuse the object and only call `ClearRemote` (`NetSyncSocket.cs:718-757`; `NetSyncRelay.cs:189-194`), and behind the local bridge the game's hop stays up through an upstream cut (`NetSyncClient.cs:671-673`). The host probe keeps a reference to the transport it read from (the precedent at `NetSyncBattle.cs:3152`) and shows -1 when that transport is stale. Nothing on the guest depends on the frames object's life.

### Call sites (every hunk tagged `[ff9mapkit netsync s164]`)

| Site | Hunk |
|---|---|
| `EmitFieldIntentIfHost` (:6734-6755) | Gains an overload `EmitFieldIntentIfHost(Int32 dest, Int32 site)`; the one-argument form (called by MAPJUMP, `DoEventCode.cs:1040`) passes `mapjump`. **One hunk owns the `next` end (I8):** after the guards (:6739-6742) and before :6743, `if (i._intentActive) NetSyncSwap.NoteIntentEnd(IntentEndNext, i._socket)`, which counts `ends.next` and `replaced`, closes the watch and prints LIFE's "replaced" line; LIFE's L1 is this same call. The out-of-band write at :6748 becomes `oobSeq = i._socket.SetStateWatched(frame)` (a throw falls back to `SetLocalState(frame)` and records oob unknown). Then `t = NoteEmit(dest, nonce, site, oobSeq, frame != null)`, which opens or joins the host record (Emit), sets the writer to Host, and stamps `host_fps` and `emit_dt_us`. NoteEmit seeds `intent.frames` with 1 when the out-of-band frame was built (`oobSet`) -- that frame's `NoteIntentFrame` ran before the probe was armed -- and 0 for the bench emit (review fix F05). The line at :6749 gains `+ Stamp(t)` |
| `Ff9mkDebugMenu.ServicePendingWarp` (:2452) | `EmitFieldIntentIfHost(mapNo)` becomes `EmitFieldIntentIfHost(mapNo, NetSyncSwap.SiteDebugWarp)` (F4) |
| Host intent end (LIFE's `HostIntentLifeStep`, replacing :2095-2096) | `NoteIntentUpdate()` each Update while active. On the end: `NoteIntentEnd(why, _socket)` records `end_t` and `last_life_ms` and closes the watch at `SetSeq + 1` |
| `BuildStateFrame`, the `if (_intentActive)` append (:6775-6777) | The body becomes `NetSyncSwap.IntentSectionBody(_intentField, _intentNonce, landed)`, four bytes: s163's three, then a flags byte whose bit 0 (`IntentFlagLanded`) is set when `_intentLanding != Pending \|\| _intentFaulted` (PIN, "The host's half"). Then `NoteIntentFrame(landed)`, which counts host frames that carry section 4 and those that carry the bit (the out-of-band frame built before the probe was armed is counted by NoteEmit's seed instead: review fix F05) |
| `ResetIntentAndL1State` (:6676-6726) | Becomes `ResetIntentAndL1State(INetTransport rode)` (review fix F07): both callers (`ApplyConfigChange`, `OnDestroy`) capture `rode = _socket` before `_socket.Stop(); _socket = null;`. **One hunk owns the `reset` end (I8):** before :6680, `if (_intentActive) NetSyncSwap.NoteIntentEnd(IntentEndReset, rode)`; LIFE's L5 is this same call, and its refresh reads the transport the intent rode (`RefreshWatchOn`). Then `NetSyncSwap.ResetSession("the co-op session reset", rode != null)` closes the record as `reset` (logging L-CLOSE when a transport existed, or on `SwapSessionRole`) and forgets the seen nonce. `Reset(why)` stays as the one-argument wrapper `ResetSession(why, false)` |
| `EmitDialogTap` live line (:7370) | `+ Stamp()` (voice-thread safe: it reads static booleans and the clock). The recorded line at :7362 is untouched |
| `UpdateHostScene` :6915 "rose", :6917 "ended"; `StartSceneAt` (:7034, called from `StampTalk` :8385) :7038 "ended" and :7039 "rose" | `+ Stamp()` on all four (I10) |
| `ScanHostOpenSet` (:6840-6885) | Keep the (Id, TextId) of the first lockable window that is not Inh. Before `_hostLineOpen = line` (:6881), on a rising edge on a field: `NoteFirstLine(NowMs(), fld, win, text)`. No log line; the stamped "scene rose" line covers it |
| `ObserveHostDialog` new-frame branch (:7800-7809) | After :7808: `NetSyncSwap.NoteHostFrame(state, now, myField, onWorld, following, LastHostField, offField)`. This is the one guest site (row 6 above). Item A's part: on `SeenRule` it records seen_t, the nonce and arrived_t (`TicksToMs(probe.InStateTs)` when `ReferenceEquals(probe.InState, state)`, else -1), then applies `JoinRule(Seen)`. Each further copy of the same nonce increments `copies`. `ObserveHostDialog` runs before `ServiceIntentFollow` (:2168, :2170), so seen_t ≤ follow_t |
| `ResetGuestDedupForEpoch` (:7822-7838) | `ForgetHostNonce()` |
| `StartFollowWarp(Int32 dest)` (:4665) | Becomes `StartFollowWarp(Int32 dest, Int32 via)`: `_followStartT = NoteFollow(dest, via, fldMapNo); _followDelayFrom = -1;`. Callers: `FollowHostTick` :4649-4650 (serial); `ServiceIntentFollow` :7189 (intent); `DebugInjectIntentImpl` :7280-7281 (intent, plus `NoteBenchSeen` after the codec round trip at :7259). Each caller's line gains the stamp. D replaces the wipe inside (§D+E) |
| `SameFieldKickTick` (:6586-6592) | `_followStartT = NowMs(); _followDelayFrom = -1;`. A kick never touches the record |
| `ServiceFollowWarp` (:6602-6668) | After D's `Due` returns not-Wait, `Due` latches the verdict and its time `due_t`. Then `if (!NetSyncSwap.CommitDelayAllows(ref _followDelayFrom)) return;` (`DelayRule`; fails open to true). The drop lines (:6635, :6651-6655) gain the stamp, preceded by `NoteDrop(...)`. After the write (:6662-6666): `NoteCommit(mapNo, kick, _followStartT, dueWord, delayMs)`, which writes the L-COMMIT line, records `commit_t`, sets the writer (Follow or Kick) and applies `JoinRule(Commit)` |
| `NoteFieldLanding` lines (:5826-5831), `NoteFollowWaits` (:4783) | `+ Stamp()` |
| `ApplyStoryBeforeEvents` (:874) | After `NoteFieldLanding`: `NetSyncSwap.OnFieldLoad(fldMapNo)`. It sets via = `LandViaRule(...)` (the landing consumes the writer) and applies `JoinRule(Land)`. It prints L-LAND only when the landing joined a record or via is follow, kick, own, bounce or host. A landing via `follow` whose record holds no own edge increments `counts.follow_won` (F2) |
| `RedirectGuestFieldJump` (:516-597) | Today's body becomes `RedirectGuestFieldJumpCore(ref dest, ref verdict, ref why)`. The wrapper stamps `OwnJumpT = NowMs()`, sets `NetSyncSwap._ownLastTerm = 0`, runs the core, then calls `NoteOwnJump(asked, dest, myField, verdict, why, LastHostField, t)` (rule list below the table) |
| `NetSyncAte.cs` :609, :622, :638 | `+ Stamp(NetSyncSwap.OwnJumpT)` |
| `NetSyncDialog.cs` | Details below the table |
| `Update` (:1669-1670) | After `if (!_enabled) return;`: `NetSyncSwap.Tick()`. It runs `CloseRule`'s window and stale checks, and costs one bool test when nothing is open |
| Transport start (:2063) | After `_socket.Start()`: the L-CLOCK line, once |
| Proof block (after :1950) | The round's proof line (§ SelfTest) |

**The verdict each return of `RedirectGuestFieldJumpCore` records:**
- gMode 3 (:524-525): World, with no record and no line in round 1;
- the s161 ATE pass (:542-554): Ate, or AteRedirect when redirected;
- C's pass (the new `OwnFieldPass` return before :557): Pass / `pending`, `committed`, `intent` or `cache`;
- `dest == myField` (:557): Reload / `same-field`;
- `dest == LastHostField` (:557): Pass / `host-field`;
- `EndingPasses` (:563): Pass / `ending`;
- the spent budget (:569-579): Through / `budget`;
- the bounce (:589-594): Bounce / `not-host`;
- the catch (:596): Pass / `fault`.

**What `NoteOwnJump` does.** It applies `JoinRule(Own, Bounce ? asked : final, ...)`. For a bounce it sets the writer to (Bounce, myField); otherwise to (Own, final). It increments `counts.bounces` on Bounce. Then it prints the one own-jump line, and it is the only place that prints one (I2). It runs after the core and after `JoinRule`, so the verdict and the record number are final. By `_ownLastTerm`, which `OwnFieldPass` wrote during the core: above 0, C's pass line; below 0, C's refusal line, ending with the outcome words of the core's final verdict; 0, L-OWN. It clears `_ownLastTerm` after printing. READ: today's bounce line is `DeclineOnce`, which is latched once per field (`NetSyncField.cs:578-600`); it is kept.

**The `NetSyncDialog.cs` hunks:**
- `DlgEvent` gains `Int64 SeenT = -1`; `Win` gains `Int64 PageT = -1`.
- `Ingest` (:971-975) stamps `SeenT`.
- `Track`, on a new locked window (:1243-1251), stamps `PageT`, and the "opened locked" line gains its stamp. Then `NoteFirstLine(...)`.
- A page change (:1253-1258) re-stamps `PageT`.
- Stamp only: :1286, :1333, :1357, :1400, :1543, :1589.
- The applied close or advance (:1410-1411) gains `WaitedShownText(...) + Stamp(t)` after its closing ")". So `coop_dialogue_authority.py:292-293` and `coop_ate_relay_duo.py:380` still match.

New fields:
- `NetSyncClient`: `_followStartT`, `_followDelayFrom` (Int64, -1).
- `NetSyncSwap` (static, main thread):
  - `_rec`, the record, a class carrying every key of `last` (§ state);
  - `_writeKind`, `_writeDest`, `_prevField`;
  - the host probe (`intent` keys) and its transport reference;
  - `OwnJumpT`;
  - the clock source and frequency, chosen once;
  - counters, `Faults`, `LastFault`, `SelfTestVerdict`.

Out of round 1: gMode-3 own jumps and the world rejoin are not recorded. Their landings read `other`.

### Log lines (instrument)

- **L-COMMIT:**
  - `[NetSync] swap: follow-warp to field D committed M ms after its start (black|timer|fallback|recheck[; +N ms delay]) (swap #K) (t T ms)`
  - for a kick: `[NetSync] swap: the same-field kick on field D committed M ms after its start (t T ms)`
- **L-OWN** (only for the s163 verdicts, and only when `_ownLastTerm` is 0): `[NetSync] swap: own Field(D) on field F -- <outcome> (swap #K) (t T ms)`. The outcome is one of (the same words end C's refusal line):
  - `passes (the host's field)`
  - `passes (a same-field reload)`
  - `passes (the ending)`
  - `passes (a read fault: the vanilla jump)`
  - `let through (the bounce budget is spent)`
  - `bounced to a reload of F (not the host's field: the host's lane reads field H)`

  ` (swap #K)` is left out when the jump joined no record.
- **L-LAND:** `[NetSync] swap: landed on field F <via words> (swap #K) (t T ms)`
- **L-CLOSE, guest:** `[NetSync] swap #K to field D (from F) closed by <close words>: <via words>; seen +a, follow +b, own +c, due +g, commit +d, landed +e, first line +f ms after its first edge (<open_by>); follows n, bounces m, reloads r (t T ms)`. A missing edge prints `-`.
- **L-CLOSE, host:** `[NetSync] swap #K to field D (from F) closed by <close words>: via my own transition (<site>); emit +0, landed +e, first line +f ms; section 4: U Updates, N frames, S sends over L ms, the out-of-band frame sent|OVERWRITTEN|none (t T ms)`
- **L-CLOCK:** `[NetSync] swap clock: t T ms = yyyy-MM-dd HH:mm:ss.fff UTC (src qpc|stopwatch: N ticks at H Hz, high-res|LOW-RES; frame dt D ms, target fps F, fps S)`

**Existing lines that gain the stamp, and who reads them:**
- `swap-timing/final.py:26`, `conv.py:20` and `drift.py:15` anchor the tap line on `$`. They gain `(?: \(t (\d+) ms\))?$` and prefer the stamp over the whole-second prefix.
- `coop_follow_race_duo.py:208` gets the same tolerant tail. Its `MINE["intent"]` is defined but never used.
- Every other reader matches by substring or search, or swallows the stamp into notes (`coop_follow_race_duo.py:214-218`).
- Nothing under `ff9mapkit/ff9mapkit`, `apps/` or the Workspace parses these lines.

---

## Item B: Finding 11's orphan hold

**Why it is real, and why B fixes it.**
- On field 351 the host's control was off from its landing until its first line:
  - the guest's step-out OUT at its 351 landing needs `hostCtlOff` (`NetSyncStepOut.cs:246-249, 552-562`; `NetSyncClient.cs:6966-6968, 7767, 7780`; guest log `twopc-s163-20261029/laptop-guest...log` line 371);
  - `StartEvents` zeroes `usercontrol` on every load (`EventEngine.cs:647`);
  - 350's Select path runs `set VAR_GlobBool_158 = 0` and `DisableMove()` before `Field(351)` (`test2_93.txt:340-344, 472-473`);
  - 351's `Main_Init` enables movement only `if (VAR_GlobBool_158 == 1)` (`test2_94.txt:281-286`);
  - the Cat's leap then runs `RunScript(4, 6, 28)`, which is `WindowSync(7, 128, 113..117)` (`test2_94.txt:2662-2709, 1115-1116`).
- INFER: the host's control stayed off from the landing through lines 113-117. The duo bench must read that bit across the whole gap (DB-BIT) rather than assume it.
- READ: the host's scene machine is sticky (`NetSyncDialog.cs:2497-2498`). So B changes only two stretches: from the host's landing to its first line, and wordless control-off episodes that never raise a scene.

### Rules (pure)

```
NetSyncDialog.OrphanSettled(Boolean settledLong, Boolean inh, Boolean hostHoldsInput, Boolean leverOld)   // replaces :1194-1201
  act: settledLong && !hostHoldsInput
  old: settledLong && !(inh && hostHoldsInput)            // s163, C3KEYS-4
```

| settledLong | inh | holds | act | old |
|---|---|---|---|---|
| T | F | F | T | T |
| T | F | T | **F** | T (the flip: Finding 11) |
| T | T | F | T | T |
| T | T | T | F | F |
| F | any | any | F | F |

Under act, the orphan rule and the script-key lock's host half (`KeyHostHalf`, :1189-1191) read the same idle for every line.

```
NetSyncClient.HostHoldsRule(Boolean hostHere, Boolean haveView, Int32 hr)   hostHere && haveView && (hr & HrControl) == 0
     // a byte-identical extraction of :7767; HrControl = 32 (:6155)
NetSyncDialog.CtlHoldKind(Byte cls, Int32 actNew, Int32 actOld)            // logs and state only
  actNew == actOld -> CtlNone
  cls == ClsLocked && actNew == OrphNone && actOld == OrphToOrphaned -> CtlHold
  cls == ClsOrphaned && actNew == OrphToLocked && (actOld == OrphNone || actOld == OrphConfirm) -> CtlRelock
  else -> CtlNone
NetSyncDialog.HoldEndWhy(Boolean present, Boolean claimed, Boolean relayOwned, Boolean hostHere, Boolean settledLong, Boolean hostHolds)
  !present -> Closed; claimed -> Event; relayOwned -> Relay; !hostHere -> Left; !settledLong -> Busy; !hostHolds -> Control; else None
  (Forgot is written directly by ForgetWindows / ResetAll; Left must come before Control: HostHoldsInput needs HostHere)
NetSyncDialog.OrphanSinceRule(Boolean keepRead, Int32 kept, Int32 now)      keepRead ? kept : now          // R5
  (a window re-orphaned straight off a CONTROL hold keeps the reading clock it first orphaned with. The clock keeps
   running through the hold: held time counts toward the read, and the hold only defers the confirm to the next
   orphaned tick. Any other hold end restarts the clock, as s163 does. I5)
NetSyncDialog.KeepReadRule(Int32 endWhy)                                     endWhy == Control
```

**R5, why the read clock is kept.** `OrphToOrphaned` sets `w.OrphanSince = v.Now` (`NetSyncDialog.cs:1538-1541`), and the auto-confirm waits `AutoReadMs` from the later of the completed page and `OrphanSince` (`:1680-1683`). Under act, every host control blip on my field relocks an orphaned window. Without the rule, a host that keeps losing control more often than every 2 s (its own climbs, MOVQ walks) would hold a genuinely guest-only line indefinitely. With it, a page that is already complete auto-confirms on the first orphaned tick at or after its first orphaning + `AutoReadMs`; first orphaning + `AutoReadMs` + the summed held time is only a loose ceiling. A relock does not move `CompleteSince` (`:1255-1269`), and `HostHoldsInput` stays out of the settle clock, so the window re-orphans on the first tick the host's control is back.

**Which hold end keeps the clock (I5).** Only a hold that ends because the host's control came back (`HoldEndWhy` = Control) keeps it. A host scene that rises during the hold (Busy), a host event (Event), a relayed start (Relay), the host leaving (Left), or a teardown (Closed, Forgot) ends the hold some other way, and the next re-orphan restarts the clock at `v.Now`, exactly as s163 does for those relocks. So a host cutscene that turns control off before its first line no longer leaves a stale kept clock behind it.

**Unchanged:**
- `SettleClock` (:2418-2475), `OrphanStep` (:1663-1684), `KeyHostHalf`, the chip, and the key idle purge.
- `HostHoldsInput` stays out of the settle clock. Moving it in would change `KeyHostHalf` and the s153 re-ask breaker's memory.

### Call sites

- **`NetSyncDialog.Orphans` (:1526):**
  - `leverOld = NetSyncSwap.OrphanLeverOld || _ctlFaulted`;
  - `settled = OrphanSettled(_settle.Long, d.FlagButtonInh, v.HostHoldsInput, leverOld)`;
  - `OrphanStep` is unchanged.
  - Then, under act, inside a try: compute `actOld` with the old rule, `kind = CtlHoldKind(w.Cls, act, actOld)`, and `StepCtlHold(w, kind, eventPending, ref v)`. A fault calls `CtlFault`. All of this runs before `if (act == OrphNone) continue;` (:1529).
  - The `OrphToOrphaned` branch (:1541) becomes `w.OrphanSince = OrphanSinceRule(w.KeepRead, w.OrphanKept, v.Now); w.KeepRead = false;` (the flag is consumed by the re-orphan it was set for).
- **`StepCtlHold`** runs before the `OrphToOrphaned` branch in the same tick (above), so a hold's falling edge always decides before the re-orphan reads the flag:
  - On the rising edge it sets `w.CtlHeld` and `w.CtlHeldSince` and counts a hold or a relock. On a relock it also stores `w.OrphanKept = w.OrphanSince`. It logs the hold line for a hold only; a relock uses the existing line.
  - On the falling edge it computes `HoldEndWhy`, sets `w.KeepRead = KeepReadRule(why)`, records `last_hold_ms` and `last_end`, and logs the end line.
  - After the loop it sets `holding` to the count of held windows.
- **The OrphToLocked line (:1550-1551)** gains a case after `eventPending`: `kind == CtlRelock ? " held -- the host's control is off on my field"`.
- **New fields:**
  - `Win` gains `Boolean CtlHeld, KeepRead; Int32 CtlHeldSince, OrphanKept`;
  - `NetSyncDialog` gains `Boolean _ctlFaulted`, sticky per session and cleared in `ResetAll`.
- **Window teardown:**
  - the `Track` removal loop (:1281-1289) ends a hold as Closed before `RemoveAt`;
  - `ForgetWindows` (:487) and `ResetAll` (:431) call `EndCtlHolds(Forgot)`, which loops only over held windows.
- **`NetSyncClient.cs`:**
  - :7767 becomes `v.HostHoldsInput = HostHoldsRule(v.HostHere, hv != null, hr)`;
  - **:7780 is an ADDITION, never a replacement (R8).** The existing line `_glHostHoldsInput = v.HostHoldsInput;` stays exactly as it is; it feeds s156's `GuestHostSceneWhy` (:1142-1143), s158's step-out `hostCtlOff` (:6968) and s163's `hostHolds` (:6994). The new line goes after it: `NetSyncSwap.HostHoldsNow = v.HostHoldsInput;   // [ff9mapkit netsync s164]`. The session-off path (:7680) sets `NetSyncSwap.HostHoldsNow = false`. A kit source test asserts the original line is still present.
- **`BenchHostTick` (:7859):**
  - the section-7 flag becomes `Byte f = DebugHostEventFlag != 0 ? NetSyncDialog.HfScene : (NetSyncSwap.BenchHostCtlOff ? (Byte)0 : NetSyncDialog.HfControl);` (the `(Byte)0` keeps the inner conditional a Byte; a bare `0` makes it an int and fails with CS0266, I7);
  - the step-out's and the speed mirror's bench inputs keep reading `DebugHostEventFlag` (:6959-6960, :6994), so their benches do not change.
- **The dialogue selftest's `KeyScript` row (:3228-3229):**
  - `OrphanSettled(true, false, true, false)` must be false: "key: a plain line is orphaned while the host holds input on my field (Finding 11)";
  - `OrphanSettled(true, false, true, true)` must be true;
  - the other terms gain `false` with the same truth, and the detail text is unchanged.

### Log lines (behaviour)

- `[NetSync] dialogue orphan: win W text T held -- the host's control is off on my field (t T ms)`. This is a new line when the hold comes from Locked, and the existing OrphToLocked line's new suffix on a relock.
- `[NetSync] dialogue orphan: win W text T -- the control hold ends after N ms (<why>) (t T ms)`, where why is one of:
  - `the window closed`
  - `a host event claims it`
  - `a relayed start claims it`
  - `the host left my field`
  - `the host is busy (a scene or a line)`
  - `the host's control is back`
  - `the lock let go`

---

## Item C: the guest's own Field() passes on the host's announced field

**What was read that shapes C:**
- **R1. When fldMapNo changes.** On a following guest, MAPJUMP calls the redirect, then `SetNextMap`, then `return 4` (`DoEventCode.cs:1031-1042`). That sets nextMode 1 and `attr|=8` (`HonoluluFieldMain.cs:257-267`). In the same HonoUpdate, `shutdownField` runs and `fldMapNo = nextMapNo` (:303-315, :446). So `fldMapNo` reads the destination from the next `NetSyncClient.Update` on.
- **R2. Today's order in the redirect:** the s161 block (:533-556), then the lane pass (:557), then `EndingPasses` (:563), then the bounce (:566-594).
- **R3. The lane.** `LastHostField` is the host's position lane (:2166), which reads 0 while the host has no body (:2084).
- **R4. Wire order.** Each write tick sends position before state (`NetSyncSocket.cs:382-386`), so the guest usually sees the intent while the lane still reads the source field.
- **R5. 351's rest exits** write globals right before `Field(352)`, with no wait and no `PreloadField` between the writes and the jump (`test2_94.txt:3529-3539, 3866-3879`).

**The commit-to-changeScene window (a law, T4).** The follow's commit writes `nextMapNo`, `nextMode = 1` and `FF9Sys.attr |= 8` from `NetSyncClient.Update` (`NetSyncClient.cs:6658-6666`). The load starts only at the next main-loop tick's `changeScene` test (`HonoluluFieldMain.cs:303-315`). That same tick runs `ServiceEvents` first (`:240-242`; its gate reads `FF9.attr`, a different object from `FF9Sys.attr`, `:15-16`), so the copy's script always gets one more tick after a commit, whichever Unity order runs. A `Field()` the copy runs in that tick goes through `RedirectGuestFieldJump`, and its `SetNextMap` would overwrite the commit's `nextMapNo`. C makes this harmless when the destinations match: the Committed term passes the own jump onto the same `nextMapNo`, which is one load. A copy whose own `Field(N)` names another field bounces, as today (risk 19). D+E aims the commit at the copy's own exit instant, so this window is exercised by design, not by chance; the selftest rows `commit_then_own_same_tick` (s1-s5) pin the outcome over pending, committed and lane states, and the duo's `own` calibration is held to REST-OLD (DESK and CAL keep `own act`) so it cannot red rows outside its registered set.

### Rules (pure, in `NetSyncSwap`)

```
Int32 OwnFieldPassRule(Int32 lever /*0 act, 1 old, 2 nocache*/, Boolean following, Int32 myField, Int32 dest, Boolean usable,
                       Int32 pending, Boolean kick, Int32 committed, Int32 liveIntent, Int32 cacheField, Boolean cacheStands,
                       Boolean worldHeld, Boolean ateHeld)
  lever == old || !following                                               -> None
  dest <= 0 || dest == 65535 || dest == myField || dest == 16000 || !usable -> None   (the same-field pass and EndingPasses own these)
  term = pending == dest && !kick ? Pending : committed == dest ? Committed : liveIntent == dest ? Intent
       : lever != nocache && cacheStands && cacheField == dest ? Cache : None
  term == None -> None;  worldHeld -> RefusedWorld (-1);  ateHeld -> RefusedAte (-2);  else term
  (a refusal is reported only when a term matched; a refusal means today's rule decides)

Int32 OwnJumpVerdictRule(Int32 lever, Boolean following, Int32 myField, Int32 dest, Int32 lane, Boolean usable,
                         Int32 pending, Boolean kick, Int32 committed, Int32 liveIntent, Int32 cacheField, Boolean cacheStands)
  // the core's decision with no hold, no ending and budget to spare: C first, then s163's lane pass, else the bounce
  term = OwnFieldPassRule(lever, following, myField, dest, usable, pending, kick, committed, liveIntent, cacheField, cacheStands, F, F)
  term > 0 -> Pass(term);  dest == myField -> Reload;  dest == lane -> Pass(host-field);  else -> Bounce

Int32 IntentCacheStep(Int32 cacheField, Int32 cacheNonce, Int32 secField, Int32 secNonce, Int32 myField)
  secNonce < 0 || secNonce == cacheNonce -> Keep          (a cleared nonce stays spent)
  secField > 0 && != 65535 && != myField && != 16000 && myField > 0 -> Write
  else -> Skip  (record the nonce; clear a standing cache as superseded)      (nonces compare by !=, so 255 -> 0 writes)

Int32 IntentCacheVerdict(Int32 cacheField, Int32 cacheSrc, Int32 hostFrom, Int32 ageMs, Int32 myField, Int32 hostLane)
  cacheField <= 0 -> None;  myField != cacheSrc -> Left;  ageMs < 0 || ageMs >= IntentCacheMs (2000) -> Aged
  hostLane > 0 && != 65535 && != cacheField && != cacheSrc && != hostFrom -> HostPast;  else Stands
  (the stale source-field frame never clears it: R4)

void OwnPassBook(Int32 term, Int32 dest, ref Int32 pending, ref Int32 committed, out Boolean bend)
  Pending -> pending = -1, committed = dest, bend = true   (the follow's fade becomes its commit); every other code: no change
Boolean OwnPassKeepsOwn(Int32 term, Boolean exitHoldKeepsOwn)   term > 0 && exitHoldKeepsOwn
```

There is also a side-effect-free ATE query. It is a refactor, not a new rule. `NetSyncAte.HoldsFollow` (`NetSyncAte.cs:670-745`) splits into three parts (I9):
- `internal static HoldVerdict(...)`, pure: the exit-hold term (:674) followed by `FollowHoldRule`, with every clock delta (`_preArmed`/`_preSince`, `_tailArmed`/`_tailSince`/`_tailProgress`, `_openTick`, `_pickTick`, read at :670-700), the phase, pending, the exit-hold field and the lever passed as arguments;
- `internal static HoldInputsNow(dest, myCtl, myField, pressQueued, choiceQueued)`, which gathers those live inputs once; both `HoldsFollow` and the new quiet query call it;
- the existing arming, logging and counters, kept byte-identical.

A new `HoldsFollowQuiet(...)` (`HoldVerdict(HoldInputsNow(...))`) returns -1 on a fault, 0 for no hold and 1 for held. It arms nothing and logs nothing. **Its equivalence is proven, not assumed (F7):** the SelfTest row `quiet_equals_loud` has two halves. (1) It drives `HoldVerdict` over the full input grid (exit-hold field set or unset and equal or not to `dest`, the lever, `myCtl`, `myField` against the press field, `pressQueued`, `choiceQueued`, each clock armed and unarmed, past and short of its bound) against the s161 rule twins. (2) For each grid point it writes NetSyncAte's statics, compares `HoldsFollowQuiet` with `HoldsFollow`, and restores every static in a try/finally, so no stale exit-hold field or tail clock survives the proof. The mutant `quiet_no_exit_hold` (`HoldsFollowQuiet` without the :674 term) must fail it. s161's unchanged proof counts (165 rows / 65 mutants) still test the loud path. Within one SelfTest call the sweep is cached (review fix F09): half (1)'s verdict grid reads no rule set and runs once; half (2)'s live hold grid runs for the real rules and again only for a rule set whose `Quiet` delegate differs (today only `quiet_no_exit_hold`); every other rule set reuses the real result. The row still counts once per rule set, so N and M are unchanged. Outside a SelfTest call (an offline runner's direct `Rows`), the full sweep runs each time.

### Call sites and state

- **The cache** is written at the one guest site (`NoteHostFrame`, row 6 of the conflicts table) through `IntentCacheStep`:
  - on Write it sets field, nonce, `src = myField`, `host_from` (`LastHostField` when it is a real field other than `secField`, else -1) and the tick;
  - on Skip it clears a standing cache as "superseded";
  - on the world map, or when not following, it clears ("the world map" / "not following").
- **`NetSyncSwap.GuestTick(myField, hostLane)`** runs on every Update of both roles, on a field or not: on a client right after :2168 as `GuestTick(fld, LastHostField)`, which no `onField` return precedes; on the selftest role right after `ServiceSpeed` (`NetSyncClient.cs:1784`) as `GuestTick(fld, -1)`, beside the other every-tick selftest calls and before the branch's `if (!inScope) return` and player-spawn return (:1785-1794). The lane is passed as -1 there explicitly: the selftest branch writes `LastHostField = -1` only at :2039, later in the same tick (V3, P5). `GuestTick` runs `IntentCacheVerdict` and clears the cache with the reason when the cache no longer stands. It reads only `fldMapNo` and the cache, so it needs neither the old map nor the new player. A Left clear whose new `myField` equals the cached field appends " (the cached field)" (T7). `fldMapNo` flips inside the MAPJUMP tick (R1), and the old scene goes at `ChangeScene` while the new field's landing hook waits for the first `HonoUpdate` after `IsReady` (`SceneDirector.cs:276-284`; `HonoluluFieldMain.cs:203-210, 150`), so this every-Update clear runs before the landing hook on both roles, in either Unity order and at any frame rate. A kit source test pins the selftest placement.
- **Clears that also forget the nonce:**
  - `ResetIntentAndL1State` ("the session reset");
  - `ResetGuestDedupForEpoch` ("the host epoch changed");
  - `TitleTick` after :5196 ("the title").
- **`NoteGuestWorldJump`** (after :5857) clears the cache ("the world map") and keeps the nonce.
- **`NoteFieldLanding`** (after :5793) keeps a backstop: if a cache still stands and `fld != src`, it clears it as "field N loaded". It carries no "spent" wording: `GuestTick` has already cleared a cache for any field the copy left (T7). A bounce reload lands on `src` and keeps the cache, on purpose.
- **`RedirectGuestFieldJumpCore`:** after the s161 block closes (:556) and before :557, `if (OwnFieldPass(myField, dest, keepOwnHeld)) return false;`.
  - It goes before the lane check on purpose. A jump to the pending field converts even when the lane already reads it, so no s154 cancel line appears and no stray commit fires during the load (rows s3, s5).
  - With the lever at `old`, the exact s163 path runs.
- **`OwnFieldPass`** is static and decides inside a try. A throw logs once and returns false.
  - **Inputs:**
    - `following = (IsLiveFollowedSession && !_exitRampPending) || (IsSelfTestRole && NetSyncField.BenchGates)`;
    - `liveIntent = HostIntentFieldNow()` (:7099, no other callers);
    - `cacheStands = IntentCacheVerdict(...) == Stands`;
    - `usable = eventIDToFBGID.ContainsKey(dest)`;
    - `worldHeld = HoldHoldsFor(dest)` (:5353);
    - `ateHeld = NetSyncAteArmed.On && AteHoldsNow(dest)`. `AteHoldsNow` is new: the inputs of `AteHoldsFollow` (:5376-5381) passed to `HoldsFollowQuiet`. A result of -1 counts as a fault, and the old rule decides.
  - **On a refusal (below 0):** count it, write `_ownLastTerm` (-1 RefusedWorld, -2 RefusedAte) and return false. It prints nothing: the old rule below decides the outcome, and `NoteOwnJump` prints C's refusal line with that outcome after the core returns (I2).
  - **On a pass (above 0):** `OwnPassBook` runs in its own try. On Pending it sets `_followWarpPending = -1`, `_followCommittedTo = dest`, calls `NoteMoveCommitted()` and `NetSyncFollowFade.Clear("own")`, and increments `converted`. Then `KeepOwnEntranceFor(dest)` runs if `OwnPassKeepsOwn`. Then the counters and `OwnPassBook`'s state, `_ownLastTerm = term`, and `return true`; `NoteOwnJump` prints the pass line.
  - There is no `SeedHostEntrance`, because dest is unchanged.
- **Not changed by C:**
  - **s154:** C never starts a follow. After a pass `fldMapNo` already equals dest (R1), so `ServiceIntentFollow` marks the nonce seen (:7145-7148). A converted record lands with committed equal to the landed field, which reads `LandNone`. A half-booked pass is still caught by `LandArrived`.
  - **The kick:** it is excluded by `!kick` and `dest != myField`.
  - **The s161 holds:** they are re-checked through `HoldsFollowQuiet`.
  - **The DEST rewrite and the hub pass:** both run first, unchanged.
  - **ENDING:** it is excluded from the rule.
- **New fields** (`NetSyncSwap`):
  - the cache: `_icField`, `_icNonce`, `_icSrc`, `_icHostFrom` (-1), `_icTick`, `_icBench`;
  - counters: `_ownPasses`, `_ownBy[4]`, `_ownConverted`, `_ownRefusedWorld`, `_ownRefusedAte`, `_icWrites`, `_icClears`;
  - last-event fields: `_ownLast*`, `_icLastClear`.
  - `IntentCacheMs = 2000` equals LIFE's `IntentMinLifeMs`.

**Why the cache stays now that LIFE exists.**
- With LIFE, the live section 4 stands for at least 2 s after the emit.
- The cache still covers three cases:
  - an s163 host (the wire is unchanged at v14, so a mixed pair is possible);
  - a lost frame;
  - a host under `life old`. C-CACHE is the cache's own proof (solo); on a following guest the Pending, Committed and Intent terms are reached before the cache term whenever the intent was seen in time, so the cache decides only when the follow was deferred and the live intent is gone.

### C2: dropped

C's writer found it unsound for round 1:
- **Story.** A destination-blind pass lands before any intent exists, so neither the cache nor the pin has a frame. The rest exits write their globals right before `Field()` (R5). `KeepOwnEntranceFor` saves only bytes 2-3 (`NetSyncClient.cs:5676-5689`). On two PCs the margin for the host's out-of-band frame to arrive in time is about 30-100 ms (INFER).
- **The guard.** `PlaysHostScene` term (a) (`NetSyncSpeed.cs:165-168`) is also true through the host's own exit fade and its climbs, so it does not prove my copy runs the host's branch.
- **Order.** The guest would land while the host still stands on the source field. That is B's uncovered gap: the line orphans after about 7 s.

**What remains of the s158 shape.**
- The own `Field(352)` before the intent still bounces once (about 1.4-1.5 s).
- But it no longer costs a second follow. The cache is written on the guest's first Update after the reload (src 351). Then either the copy's re-run `Field(352)` passes by the cache, or the deferred intent fires the follow on the first FieldHUD frame (:7162), now through D+E.

A later C2 would need two things, each with its own review: a lockstep guard, and an "own-ahead landing" law that keeps my copy's own story when no intent frame exists for the landed field.

### Log lines (behaviour)

- **Pass:** `[NetSync] own Field(D) passes on field F -- the host's announced field (<term>)<tail> (swap #K) (t T ms)`
  - tails: pending `; my follow's fade becomes this commit (one load)`; committed `; my follow already committed to it`; intent none; cache `; announced A ms ago`;
  - plus ` -- my copy's own entrance (the ATE exit hold)` when the entrance is kept.
- **Refusal:** `[NetSync] own Field(D) on field F matches the host's announced field (<term>) but <the source-field hold holds it | the ATE relay holds the follow to it> -- the old redirect rule decides: <A's outcome words> (swap #K) (t T ms)`. The literal starts `[NetSync] own Field(` exactly as the pass line does (R9); battlewire's builder and a source test pin it.
- **Cache write:** `[NetSync] intent cache: field F (nonce n) cached on field S (host lane h) (t T ms)`
- **Cache clear:** `[NetSync] intent cache: field F cleared -- <reason> (t T ms)`. The reasons:
  - `aged 2000 ms`
  - `I left field S (now f)[ (the cached field)]`
  - `field N loaded`
  - `the host stands on field H (past it)`
  - `superseded (the host's intent nonce n: field G)`
  - `the session reset`, `the host epoch changed`, `not following`, `the world map`, `the title`, `the harness release`

---

## PIN: the story pin (guest)

**Why pin.**
- The landing applies the *latest* frame (`NetSyncClient.cs:918, 929`), and then runs `Main_Init` (`HonoluluFieldMain.cs:150-151`).
- INFER: a follow lands about 1.2 s after the emit. By then the host has pushed frames from after its own `Main_Init`, so every non-idempotent entry write is applied twice on the guest's copy. Example: Dali's `SByte[296]` countdown is stepped once per room on entry (`studies/story-trace/PLAN.md:318-322`). Tighter landings (C, D, E) make this a coin-flip from run to run.
- The frame captured at MAPJUMP is exactly the host's `Main_Init` input. MAPJUMP returns 4, which calls `adFin` and stops `ProcessCode` for the rest of that frame (`EBin.cs:228-231, 172-176, 112`), and no field script runs until the new field's `StartEvents`.

**What the pin stages, and what it does not (R1).** The pin stages **section 0 only** (the story). `NetSyncState.ApplyStory(payload)` applies section 0 and then calls `NetSyncParty.ParseSections(payload)` on the same payload (`NetSyncState.cs:98-111`). Sections 1-3 are the rung-2 read wraps: `B_PARTYCHK`, `PARTY_MEMBER` and `B_HAVE_ITEM` answer from the host's mirrored party, key items and bag (`NetSyncParty.cs:9-40`), and they refresh only at a relayed talk's R8 (`NetSyncClient.cs:8785-8793`). A pinned party would answer every read for the rest of the visit from before the host's `Main_Init`. So the landing has three outputs: **story = the pin, party = the latest frame, dress = the latest frame.** The dress (section 8) also stays on the latest frame because the host's leader guard re-picks it on the new field (s163 host log line 83: Garnet on 352).

### Rules (pure, in `NetSyncSwap`)

```
const PinMaxAgeMs = 2500, PinBlindCapMs = 10000          // PinBlindCapMs = LIFE's IntentLoadCapMs
const IntentFlagLanded = 0x01                             // section 4's fourth byte, bit 0
// codes: Keep -1 (no change), Here -2 (not stored; counted; the nonce marked spent), None 0, Pre 1, Late 2

Byte[] IntentSectionBody(Int32 field, Byte nonce, Boolean landed)
  { field & 0xFF, (field >> 8) & 0xFF, nonce, landed ? IntentFlagLanded : 0 }    // s163's three bytes, then the flags byte
Boolean IntentLandedOf(Byte[] body)
  body.Length < 4 || (body[3] & IntentFlagLanded) != 0     // no flags byte (an s163 host) reads as landed: fail safe

Int32 PinCaptureRule(Boolean spent, Boolean here, Int32 heldQuality, Int32 frameNonce, Boolean frameLanded)
  // heldQuality: the held entry for frameNonce, if any
  frameNonce < 0                      -> Keep    (no section 4)
  spent                               -> Keep    (T1: consumed, dropped, aged or refused here; until another nonce)
  heldQuality == None && here         -> Here    (R4: I already stand on the announced field)
  heldQuality != None                 -> Keep    (one entry per nonce: a later pre-landing frame is only compared)
  frameLanded                         -> Late    (the first frame of the nonce I saw was built after the host's landing hook)
  else                                -> Pre     (built between the host's MAPJUMP and its landing hook: its Main_Init input)

Boolean PinTargeted(Int32 pinField, Int32 pending, Int32 committed, Int32 warpedTo)
  pinField > 0 && (pinField == pending || pinField == committed || pinField == warpedTo)
Boolean PinDropOnNew(Int32 heldField, Boolean targeted, Int32 newField)
  heldField == newField ? true : !targeted
  // when a new nonce is stored: a held pin for another field survives only while a follow targets it (T5);
  // a held pin for the same field is superseded by the newer nonce

Int32 PinAgeRule(Boolean landSeen, Int32 sinceLandSeenMs, Int32 sinceCaptureMs)
  landSeen -> sinceLandSeenMs                                  (the age counts from the host's landing as I first saw it)
  sinceCaptureMs >= PinBlindCapMs -> sinceCaptureMs            (the backstop: a landing never seen in 10 s)
  else -> 0                                                    (a pin captured before the host's landing is not aged yet)

Int32 PinUseRule(Boolean leverOld, Boolean fromWorld, Int32 quality, Int32 pinField, Int32 ageMs, Int32 fld, out Int32 why)
  leverOld -> Latest/lever;  fromWorld -> Latest/world (R3);  quality == None -> Latest/none;  pinField != fld -> Latest/other
  quality == Late -> Latest/late;  ageMs < 0 || ageMs > PinMaxAgeMs -> Latest/aged;  else -> Pin
Boolean PinConsumed(Int32 quality, Int32 pinField, Int32 fld)      quality != None && pinField == fld
     (a bounce's reload of the source field keeps the pin for the follow's landing)
void LandingFrames(Int32 verdict, Byte[] pin, Byte[] latest, out Byte[] story, out Byte[] party, out Byte[] dress)
  story = verdict == Pin ? pin : latest;  party = latest;  dress = latest          (R1)
```

**The host's half (S3).** The host knows exactly when its own `Main_Init` can have run, so it says so in the frame instead of letting the guest infer it from arrival.
- `BuildStateFrame`'s section-4 append writes `IntentSectionBody(_intentField, _intentNonce, landed)` with `landed = _intentLanding != Pending || _intentFaulted` (A's call-site row).
- `_intentLanding` leaves Pending in LIFE's L2, the first statement of `ApplyStoryBeforeEvents` on the host, which runs before `StartEvents` runs `Main_Init` (`HonoluluFieldMain.cs:150-151`). The out-of-band frame (:6746) is built after L1 sets Pending (L1 runs after :6745), so it carries the bit clear.
- A frame built after the hook but before `Main_Init` has finished is marked landed. That is conservative: the guest then stages the latest frame, which is s163's behaviour. A faulted life marks every frame landed, for the same reason.
- **Wire compatibility.** Section 4 grows from 3 to 4 bytes inside wire v14. Every s163 reader treats `body.Length < 3` as the short case and reads only bytes 0-2 (`NetSyncClient.cs:7065, 7139, 7259`; `SectionFieldIs(state, SectionIntent, 3, myField)` at :7753), so an s163 guest ignores the flags byte. The engine's codec proof checks a 3-byte probe frame it builds itself (`NetSyncState.cs:276-283`) and is unaffected. The kit's tape readers list section 4 by id only (`coop_peer.py:2268, 2571`). An s164 guest reading an s163 host's 3-byte section gets `IntentLandedOf` true and stages the latest frame. The cost is one byte per host frame while section 4 rides.

**The inputs, defined.**
- `frameLanded` = `IntentLandedOf(section 4's body)`.
- **Why a bit in the frame, not arrival.** Every frame the host builds between its MAPJUMP and its landing hook is pre-`Main_Init`: MAPJUMP halts the VM for the rest of that frame, and no field script runs until the new field's `StartEvents` (Why pin). The bit labels a frame by what the host had done when it built it. So the guest's own stalls, the writer's re-sends (`NetSyncSocket.cs:386`), receive bunching, the relay, an in-transport reconnect (the first frame after it is post-landing and reads Late) and a bridge's upstream cut all leave the label true. The one case it cannot rescue is a guest that observes no pre-landing frame of the nonce at all: its own stall spans the host's whole load, or the link was down then. That guest captures Late and stages the latest frame, as s163 does.
- `landSeen` (per held entry) is set at the first observation, after capture, of a frame with that entry's nonce and the bit set; for a Late capture it is set at the capture itself. It is the host's own landing, as the guest first learns of it.
- `here` = `myField > 0 && secField == myField`.
- `fromWorld` = the landing comes from the world map, read as `ee.gMode == 3` at the landing hook, the same read `LandingFollowCandidate` takes (`NetSyncClient.cs:5757`). World rejoins commit at once and land 1-3 s later (`:5599-5615, 5638-5640`), straddling `PinMaxAgeMs`, so round 1 stages the latest frame there (R3).
- **The halted-VM premise, measured.** For a held Pre entry, each later frame of the same nonce with the bit clear is compared with the pin (`StoryDiff`, below): `pin.pre_frames` counts them and `pin.max_pre_diff` keeps the largest difference. DP-HALT judges that difference is 0.

### Call sites

- **Capture.** In `NoteHostFrame`, on a client, for each new frame:
  - read section 4's field, nonce and `IntentLandedOf`;
  - for each held entry with this nonce: with the bit set and `landSeen` false, set `landSeen` and its tick; with the bit clear and quality Pre, count `pre_frames` and update `max_pre_diff`;
  - if the frame carries a nonce different from `_pinSpentNonce`, clear `_pinSpentNonce` (T1: "until a different nonce arrives");
  - run `PinCaptureRule` with the held entry for the frame's nonce. On `Here`, count `pin.here` and mark the nonce spent. On a store of a NEW nonce, first run `PinDropOnNew` over the held entries (a dropped pin logs "dropped unused" and its nonce is spent), then store in the free slot: frame reference, nonce, field, quality, capture tick, and `landSeen = (quality == Late)`;
  - received frames are fresh arrays that nothing mutates (`NetSyncSocket.cs:436-439`), so keeping the reference is safe.
- **The map.** At most two entries `{field -> frame, nonce, quality, captureTick, landSeen, landSeenTick}`. One follow runs at a time, so at most one entry is targeted; after `PinDropOnNew` a new nonce always finds a slot.
- **`ApplyStoryImpl` (:896-947).** After the `host == null` return (:928), `Byte[] latest = host`:
  - `entry = the held entry for fldMapNo, or any held entry if none` (so `other` is counted);
  - `verdict = PinUseRule(PinLeverOld || _pinFaulted, fromWorld, entry.quality, entry.field, PinAgeRule(...), fld, out why)`, then `LandingFrames(verdict, entry.frame, latest, out story, out party, out dress)`; record `pin.last_use_quality` = the entry's quality (`none` when no entry), whatever the verdict, so a bench can read the capture's quality under the lever too (P3);
  - when a pin was held for this field, compute `StoryDiff(pin, latest)` (the section-0 bytes that differ outside the 2032-2041 mask) and log the verdict;
  - **:929** `if (NetSyncState.ApplyStory(host))` becomes:
    ```
    Boolean ok = ReferenceEquals(story, latest) ? NetSyncState.ApplyStory(latest)          // [ff9mapkit netsync s164] byte-for-byte s163
                                                : NetSyncState.ApplyStorySplit(story, party);  // section 0 from the pin, sections 1-3 from the latest
    if (!ok && !ReferenceEquals(story, latest)) { <log "did not apply">; ok = NetSyncState.ApplyStory(latest); }
    if (ok) { ...the s163 body, unchanged... }
    ```
    A kit source test pins this expression, `ApplyStorySplit(story, party)` (V1).
  - **`NetSyncState.ApplyStorySplitTo(Byte[] storyFrame, Byte[] partyFrame, Byte[] target)`** is new, beside `ApplyStory` (`NetSyncState.cs:98-111`), which stays untouched: `applied = ApplyStoryTo(storyFrame, target)`, then `if (applied) NetSyncParty.ParseSections(partyFrame)`. **`ApplyStorySplit(storyFrame, partyFrame)`** is its live-array wrapper, the way `ApplyStory` wraps `ApplyStoryTo`: it targets `gEventGlobal` and adds the same story-trace epoch. With both frames equal the split applies exactly what `ApplyStory` applies (V1).
  - **:938** `NetSyncSelfDress.ArmFromState(host)` is left as it is: the dress is always the latest frame, which is `host`.
  - With the lever at `old`, story == party == dress == latest, which is byte-for-byte s163.
  - `RestorePassEntrance` (:939) and `NoteLandingEntrance` (:879) are unchanged.
- **Consumption.** In `ApplyStoryBeforeEvents`, right after :877: `ConsumePinAt(fldMapNo)`. It runs on every load, whether or not the apply ran: each entry with `PinConsumed` true is removed and its nonce marked spent.
- **Clears:** `ResetIntentAndL1State` ("the co-op session reset"); `ResetGuestDedupForEpoch` ("the host epoch changed"): both drop every entry and mark spent the nonce on the latest received frame, so a section 4 still live across the reset is not re-captured (row c15); the exit ramp, before :1661, silently.
- **The selftest bench (V1, G2).** At the top of `ApplyStoryImpl`, `if (IsSelfTestRole) BenchPinLanding();`. It does nothing unless `swap pinbench` armed it.
  - It runs the same `PinUseRule` and `LandingFrames`.
  - It sets `_pinBenchMirror = true`, then calls `NetSyncState.ApplyStorySplitTo(story, party, scratch)`: the shipped split with a scratch target, so the party half goes through the real `ParseSections` exactly as the live hunk's does. The flag is set before the call because the parse can arm the mirror and then fail (the DIO-6 placement, `NetSyncParty.cs:500`).
  - It copies only the marker flag's byte from the scratch array into the live array.
  - The parse leaves `NetSyncParty.MirrorActive` set (`NetSyncParty.cs:248-249`), and the read wraps answer from it on any role. So the release and `swap clear` call `NetSyncParty.Clear()` whenever `_pinBenchMirror` is set (§ The lever scheme), restoring the law that a selftest machine never stays MirrorActive (`NetSyncClient.cs:10726`). The flag is the pin bench's own: `NetSyncParty.BenchMirrorArmed` is not reused, because with the mirror active it turns a later diorama's seat into SeatBench (`NetSyncDiorama.cs:2918-2921`).
- **New fields:**
  - the two-entry map, `_pinSpentNonce`;
  - counters and last-use fields;
  - `_pinFaulted`, sticky, which reads as `old`;
  - `_pinBenchMirror`.

### Log lines (behaviour)

- `[NetSync] story pin: intent N's frame kept for field D (built before the host's landing) (t T ms)`
- `[NetSync] story pin: intent N's first frame I saw was built after the host's landing -- kept as late (a landing on field D stages the latest frame) (t T ms)`
- `[NetSync] story pin: intent N's later frame from before the host's landing differs from the pin at B story bytes (the halted-VM premise) (t T ms)`, printed only when B > 0
- `[NetSync] story pin: intent N names field D, where I already stand -- not kept (t T ms)`
- `[NetSync] story pin: intent N0's frame for field D0 dropped unused (intent N arrived) (t T ms)`
- `[NetSync] story pin: field D stages intent N's frame for its story, the latest frame for its party and dress (age A ms; the latest differs at B story bytes) (t T ms)`
- `[NetSync] story pin: field D stages the latest frame -- <why> (t T ms)`, where why is one of:
  - `the pin is A ms old (over 2500)`
  - `intent N's first frame came after the host's landing`
  - `a world-map landing (round 1 stages the latest there)`
  - `the lever (s163's rule)`

  This line prints only when a pin for this field was held. A pin for another field is counted, not logged.
- `[NetSync] story pin: intent N's frame did not apply -- the latest frame stages field D (t T ms)`

---

## LIFE: the host's intent lifetime

**Verdict on R1, the study's "the intent self-clears one Update after MAPJUMP".**
- The mechanism behind it is real:
  - the clear is `fld == _intentField && onField` (:2095);
  - `fldMapNo` flips inside the MAPJUMP frame (`HonoluluFieldMain.cs:257-267, 303-311, 446`);
  - the old FieldMap survives at least to the end of that frame (`SceneDirector.cs:251-282, 394-404, 516-538`), and to the end of the NEXT frame when `deltaTime` is under 10 ms / FastForwardFactor (conflict row 11, the frame-rate confound).
- R1 holds under an Update order this desktop does not show at its measured frame rate (conflict 11), and under any order above 100 fps. INFER: today's section 4 lives from the emit until the host's first Update after its new field's first frame, which is about the host's load (0.39 s).
- Under the R1 shape, every scripted-exit intent would be lost. The MAPJUMP frame's own Update would clear the intent, and `PushStateNow` (:6930, :7049-7059) would overwrite the slot before the writer ever sent it.
- So the fix must never read "is the old map still alive". A publish-clock reset alone cannot close that hole, because `PushStateNow` ignores `_storyTick`.

### Rules (pure, in `NetSyncSwap`)

```
const IntentMinLifeMs = 2000   // = the guest lane's staleness (NetSyncSocket.cs:292, NetSyncRelay.cs:30)
const LandTailMs      = 1000   // T13: section 4 outlives the host's landing by at least this
const IntentLoadCapMs = 10000
Int32 IntentLandingStep(Int32 landing, Boolean active, Int32 intentField, Int32 loadedField)    // at the host's field-load hook
  !active || landing != Pending -> landing (it never flips back)
  loadedField == intentField -> OnIntent;  else -> Elsewhere   (the disc-change rewrite, HonoluluFieldMain.cs:306-310)
Int32 IntentLifeRule(Boolean oldRule, Int32 sinceEmitMs, Int32 sinceLandMs, Int32 landing, Boolean onIntentField,
                     Boolean bodyThere)
  oldRule -> onIntentField ? EndOld : Keep                    (s163's :2095, verbatim)
  landing == Elsewhere -> EndElsewhere
  landing == Pending -> sinceEmitMs >= IntentLoadCapMs ? EndCap : Keep     (onIntentField ignored here: the R1 fix)
  !onIntentField -> EndLeft                                   (the world map, the title, any battle: its swirl reads off the field)
  bodyThere && sinceEmitMs >= IntentMinLifeMs && sinceLandMs >= LandTailMs -> EndStands      (T13)
  else -> Keep
Boolean BodyThereRule(Boolean inScope, Boolean haveActor, Boolean haveMapActor)   inScope && haveActor && haveMapActor   (F14)
```

In one line: section 4 lives from the emit until the host has loaded the announced field, its body stands there, 2 s have passed since the emit and 1 s since the landing. It ends early when the host lands elsewhere, leaves after landing (a battle counts as leaving), or never lands within 10 s.

**The inputs, defined.**
- `onIntentField = onField && fld == _intentField` (`onField` as computed at :1684).
- `sinceLandMs = sinceEmitMs - _intentLandedMs` once landed.
- **A battle ends section 4 (S1; rev 2's R6 term is removed).** The field-to-battle change always goes through the swirl: the field's shutdown sets `FF9Sys.mode = 2` (`HonoluluFieldMain.cs:448-452`) and calls `SceneDirector.Replace("BattleMap", SwirlInBlack, true)` (:337). `_Swirl` waits at least 2 frames on the live field, then loads `SwirlScene` (`SceneDirector.cs:547-560`); `BattleMap`, and the battle's `StartEvents` that writes `gMode = 2`, come only after it. So in the first `SwirlScene` Update `gMode` still reads 1 and the FieldMap is gone (INFER: Unity's null overload), `onIntentField` is false, and the rule ends the intent as Left before the publish. Rev 2's `battleOnIntent = gMode == 2` could never be true while the intent was live. Nor is a battle a regression against s163: those 2+ pre-swirl frames on the live field are where s163's :2095 clear runs, and where LIFE keeps the intent (row `r-swirl` pins the swirl frame). A guest that deferred on the source field and is still deferred when the host's battle starts falls back to the serial follow, exactly as on s163 (risk 25).
- `bodyThere = BodyThereRule(inScope, actor != null, actor.fieldMapActor != null)` with `actor = ee.GetControlChar() as Actor`, read the way the host path reads `local` (:2073-2085). On the host it is `local != null` after :2085. On the selftest role the same rule runs inside the selftest branch, which never reaches :2073 (it returns at :2041) (F14).

**Order independence, proven without a lever (T2).** Two pure rows carry it: `r-order` (act, the emit frame itself, landing Pending, the host already reading the intent field with its body there: Keep) and `r-order-old` (the same input under s163's rule: EndOld, the R1 hole). The act rule never reads "is the old map alive", so it gives the same answer under either Unity order and at any frame rate. The in-game measurement is DA-PROBE on the DESK and REST MAPJUMP legs under `swap life old`, which records `last_life_ms`, `intent.host_fps` and `intent.emit_dt_us` for every scripted exit.

**Chosen over "about 2 s, or until the new field reports, whichever comes first"** (that rule is the mutant `life_body_or_min`):
- The guest's deferrals (a menu, the s144 hold, the s161 holds, `FieldTransitionNow`; :7162-7187) must outlive the host's landing to fire by intent, which is what the comment at :7124 already promises. `LandTailMs` guarantees that even when the host's load takes 2 s or more (T13).
- The cost is 7 bytes per frame while section 4 rides: the 3-byte section header, s163's 3-byte body and PIN's flags byte (`NetSyncState.cs:145-157`).

### Call sites

- **L1, `EmitFieldIntentIfHost`:**
  - before :6743, an intent still active ends as `next` and logs "replaced". This is the one `NoteIntentEnd(IntentEndNext, ...)` call of A's call-site row, not a second hunk (I8);
  - after :6745, set `_intentEmitTick`, `_intentLanding = Pending`, `_intentSite = site`, and `_intentLandedMs` and `_intentBodyMs` to -1;
  - after :6748, `if (!LifeOld) _storyTick = Environment.TickCount;` (consistency with :7057).
- **L2, `ApplyStoryBeforeEvents`:** the first statement inside `if (_instance != null)` (:872), before :873, is `NoteIntentLanding(fldMapNo)`.
  - It runs on the host, or on the selftest role while `swap lifebench` is armed.
  - It runs before `StartEvents`, so before the host's `Main_Init`.
  - World emits already name `ForkSiblingField(dest)` (`DoEventCode.cs:1040`).
- **L3, `Update`:** :2095-2096 becomes `if (_intentActive) HostIntentLifeStep(fld, onField, local != null);`, at the same position, before `HostTick`, `UpdateHostScene` and the publish (:2097-2111). So no frame built after an end carries section 4.
  - It records `_intentBodyMs` at the first Update with the body on the field after landing.
  - A fault logs once and falls back to the s163 clause for this intent.
- **L4, the selftest branch:** while `swap lifebench` is armed, the same step runs before :2039 with the branch's own `onField` and `BodyThereRule(...)`.
- **L5:** `ResetIntentAndL1State` resets the life fields and ends an active intent as `reset`, through the one `NoteIntentEnd(IntentEndReset, ...)` call of A's call-site row (I8).
- **New fields:** `_intentEmitTick`, `_intentLanding`, `_intentLandedMs`, `_intentBodyMs`, `_intentSite`, `_intentFaulted`, plus counters.

**Other readers of section 4, checked against the longer life:**
- the nonce dedup (:7143);
- the same-field reload (:7145-7149);
- `HostElsewhere` (:7752-7753);
- `HostIntentAndEntranceNow` and `DestJump` (:7075-7090; `NetSyncAte.cs:259-271`);
- the s144 world branch (:7150-7161): a refused world arm defers with the nonce unmarked (:7158-7159) and can now fire up to 2-3 s after the host's body stands on D, where the serial floor took over after about 0.4 s before. `coop_world_wait`, `coop_world_battle` and `coop_world_party_duo` join the regression gates for this (R3);
- the `coop_peer` tape readers (`coop_peer.py:2268, 2571`), which list section 4 by id only;
- PIN's capture: every frame after the host's landing hook carries the landed bit, so however long section 4 lives, a later frame is never pinned (PIN, "The host's half").

No other side effect was found. The bounce's source reload now re-follows by intent instead of the serial 1.2 s debounce.

### Log lines (behaviour, host)

- `[NetSync] transition intent N0 to field D0 replaced by intent N after M ms (t T ms)`
- `[NetSync] transition intent N: I landed on field D after M ms -- section 4 stays until my body stands there, 2 s since the emit and 1 s since this landing (t T ms)`
- `[NetSync] transition intent N: I landed on field F, not D -- section 4 ends (t T ms)`
- `[NetSync] transition intent N to field D ended after M ms -- <why> (t T ms)`, where why is one of:
  - `I stand on it (my body there, 2 s on the wire, 1 s since my landing)`
  - `I left it`
  - `I landed elsewhere`
  - `no landing in 10 s`
  - `s163's rule (lever)`
  - `the session reset`

---

## D+E: the fade-aware follow and the 12-tick fade

Home: a new file, `Memoria\Netsync\NetSyncFollowFade.cs`, holding a static class modelled on `NetSyncSpeed.cs`.

**Constants:**
- `FastFrames = 12`, stock's own default (`SceneDirector.cs:694-697, 711`);
- `OldFrames = 24` and `OldWaitS = 0.9f`, the same values as `NetSyncClient.cs:215-216`;
- `JoinGraceTicks = 3`, `BlackFloor = 248`, `AheadMaxMs = 3000`.

**The fade slot (read).**
- One global slot: `fadeMode`, `abrColor[2]`, `_curFrame`, `_targetFrame`, `_targetColor` (`SceneDirector.cs:753-763`).
- `InitFade` continues from the current colour (:640-651).
- `ServiceFade` steps once per main-loop tick (:653-663), inside the `FF9.attr & 256` gate (`HonoluluFieldMain.cs:236`). It is skipped while `FF9Field.attr & 2048` is set (:296-298).
- `FF9Wipe_FadeOutEx` first forces the screen fully visible. That step is the flash (:671-675).
- The `FadeFilter` opcode writes the same slot (`DoEventCode.cs:632-648`).

### Rules (pure)

```
Int32 ViewRule(Boolean readOk, Int32 mode, Int32 curMin, Int32 targetMin, Int32 ticksLeft)
  !readOk -> Unknown;  mode != Sub -> Visible (an Add white is not black);  curMin >= BlackFloor -> Black
  targetMin >= BlackFloor && ticksLeft > 0 -> Heading;  else -> Visible
Int32 CountBacklog(IList<EvtFact> ev, IList<WinFact> wins, Int32 myField, Int32 now, Boolean engaged, Boolean keyHere,
                   out Int32 onOpen, out Int32 ahead, out Boolean lineOpen)
  onOpen   = events for myField whose (field, win, text) matches a live window that is neither Local nor Inh (Tried counts)
  ahead    = events for myField whose (field, win, text) matches no live window at all, younger than AheadMaxMs
             (an event on a Local or Inh window is ignored, never counted ahead)
  lineOpen = engaged && a live Locked, not Inh window on myField (an untracked live lockable line counts as Locked)
Int32 BacklogRule(Boolean readOk, Int32 onOpen, Int32 ahead, Boolean keyHere, Boolean lineOpen)
  !readOk -> Unknown; onOpen > 0 -> Line; ahead > 0 -> Ahead; keyHere -> Key; lineOpen -> Open; else None
Int32 PathRule(Boolean kick, Int32 lever, Boolean ownWarp, Int32 view, Int32 backlog)
  kick -> Kick;  lever == Old || ownWarp || view == Unknown || backlog == BkUnknown -> Old (fail open)
  backlog != None && lever != NoGate -> Backlog;  else -> Fast
Int32 ActionRule(Int32 path, Int32 view, Int32 ticksLeft, Int32 lever, out Int32 frames)
  frames = path == Fast && lever != Long ? FastFrames : OldFrames          // E, and its lever
  path in {Old, Kick} -> Wipe (frames 24, today's flash)
  view == Black -> Join;  view == Heading && (ticksLeft <= frames || lever == NoHurry) -> Join
  view == Heading -> Hurry;  view == Visible -> Fade
Int32 GraceRule(Int32 action)                      action == Join ? JoinGraceTicks : 0
void  BlackTicksRule(Boolean black, ref Boolean armed, ref Int32 since, Int32 keyTick, out Int32 blackTicks)
  black && !armed -> armed = true, since = keyTick;  black -> blackTicks = keyTick - since;  !black -> armed = false, blackTicks = -1
Int32 DueRule(Int32 path, Boolean timerOut, Int32 view, Int32 blackTicks, Int32 grace, Int32 backlogNow, Boolean primed, Int32 lever)
  path != Fast -> timerOut ? Timer : Wait
  held = backlogNow != None && lever not in {NoGate, NoRecheck}     (BkUnknown holds)
  held -> timerOut ? Recheck : Wait
  ready = view == Black && blackTicks >= grace
  ready && (primed || timerOut) -> Black
  ready -> Prime                     (a Wait: the verdict must survive one dialogue pass before it commits, T9 / S2)
  else timerOut ? Fallback : Wait
  invariant (the s42 never-abandon law): timerOut never yields Wait or Prime
  // primed = the previous Update's Due for this follow returned Prime; any other verdict clears it
Boolean ReassertRule(Int32 path, Boolean reasserted, Boolean timerOut, Int32 view)
  path in {Fast, Backlog} && !reasserted && !timerOut && view == Visible
```

**What each action does:**
- **Wipe:** `FF9Wipe_FadeOutEx(24)`, byte-identical to today.
- **Hurry and Fade:** `InitFade(FadeMode.Sub, frames, Color.white)`. On a visible screen this equals `FadeOutEx(frames)`; on a dim screen it continues without flashing.
- **Join:** no call.

**What the commit waits for.** On the Fast path the commit waits for black **or** the 0.9 s timer fallback, whichever comes first. A copy `FadeFilter` that re-inits the slot mid-follow with a long frame count can still reach the fallback on a half-dark screen, the same outcome as today; re-pacing that case is round 2 (T10, risk 18).

**Why the backlog gate has four terms, not only "a host close queued for an open line":**
- **Line** is the skeptic's case: a host close applies only 350 ms after the page completes (`NetSyncDialog.cs:51, :1343`).
- **Ahead** is a host close for a line the copy has not opened yet. `Purge` keeps events for my field (:1062-1078), and the age cap stops an unmatchable event from blocking the fast path for the full 20 s TTL.
- **Key** is `KeyPendingFor(myField)` (:2173-2179).
- **Open** is a locked input-taking line with nothing queued.
- Inh windows are excluded everywhere (:1335-1336).

**Why a Black verdict waits one dialogue pass (T9, rev 3's S2).** `Due` runs at the top of `Update` (`NetSyncClient.cs:1668`), before this Update observes the host's frame (:2168) and merges it (:2176). So when `Due` reads `BacklogNow`, it sees the inbox as of the PREVIOUS Update's merge, and a host event that reached the socket since then has not even been observed. Rev 2 read `_dlg.RingAhead` (`NetSyncDialog.cs:2216-2219`) for that, but `RingAhead` needs `_mergedStamp != _viewStamp`, and every Update that observes also merges before the next `Due` (`NetSyncDialog.cs:817, 891-893`; `NetSyncClient.cs:7716, 7720`), so at :1668 it is always false. s161's own use works only because `ServiceIntentFollow` (:2170) sits between the observe and the merge (:7172-7179). Rev 3 drops the input. Instead, the first Update that finds the commit ready (black, grace spent, no hold) returns `Prime`, which waits. That Update's :2168 observes the latest frame, and the section-7 ring is cumulative (`HeadSeq`), so its :2176 merges every host event that reached the socket before the black was first judged. The next Update's `Due` re-reads `BacklogNow` with those events in the inbox: a hold now reads Line, Ahead or Key and waits for the timer (Recheck), and a clear backlog commits (Black). The cost is one Update per follow on the Fast path. At the 0.9 s timer the prime is skipped, as the s42 law requires; today's timer commit has no backlog check at all. An event that reaches the socket after the black was first judged can still meet a commit, the same one-frame race any commit has.

**Why the grace is 3 game ticks (T4).** Within one main-loop tick `ServiceEvents` runs before `ServiceFade` (`HonoluluFieldMain.cs:242, 298`). A stock exit runs `FadeFilter(6,24)` in tick t0's `ServiceEvents`; the slot first reads black after the 24th `ServiceFade`, at the end of tick t0+23 (`SceneDirector.cs:653-663`: `_curFrame` steps once per call and the target colour is exact at call 24). The script's `Wait(25)` then resumes it in tick t0+25 (INFER: the resume tick of `Wait(n)` relative to the issuing tick), whose `ServiceEvents` runs `Field(N)` and whose `changeScene` starts the load. `BlackTicksRule` arms in the first `Update` after t0+23 and counts `KeyTick`, which steps once per `ServiceEvents` (`EventEngine.cs:120`, `NetSyncField.cs:939`). So the copy's own `Field()` lands 2 ticks after the first black read. A grace of 3, plus the one-Update prime, lets a `Field()` up to one tick late still win; the commit-to-changeScene law (§C) covers a `Field()` in the tick after the commit. DF-GRACE (a Join start on DESK ends by `own`) settles the INFER, with DC-WON's `follow_won` count as the report (359's `Main_11`: `FadeFilter(6,24)`, `Wait(25)`, `Field(351)`, `test2_102.txt:290-301`). The tick count scales with the booster and stops while paused. The grace is 0 when we ran the fade ourselves, because then the copy is not exiting.

### Call sites

- **`SceneDirector.cs`**, after :663, a stock file with a read-only accessor:
  - `internal static Boolean NetSyncReadFade(out Int32 mode, out Int32 curMin, out Int32 targetMin, out Int32 ticksLeft)`;
  - it returns false when `abrColor` is null or the mode is outside 0-1;
  - it also cross-checks `Shader.GetGlobalColor("_FadeColor_ABR" + (mode+1))` against `abrColor`, because `ClearFadeColor` (:621-625, :568) writes only the shader. A disagreement returns false, which means today's rule. The build confirms the call exists in this Unity build, or drops the cross-check (risk 6).
- **`Ff9mkDebugMenu.cs`:** `internal static Boolean NetSyncWarpPending { get { return _instance != null && _instance._pendingWarpMap >= 0; } }` (:36, :115). A pending own debug warp forces the Old path, because that warp's commit (:2422-2456) has no guard. This also keeps the s154 FS bench valid.
- **`NetSyncDialog.BacklogNow(...)`:** builds the facts from `_inbox`, `_wins` and `LiveList()` into two reused buffers. It is allocation-free, main thread only, and a fault returns `BkUnknown`.
- **`StartFollowWarp` (:4669):** the wipe becomes `NetSyncFollowFade.Begin(dest, fldMapNo, false, _dlg, _lockEngaged)`, after `SetUserControl(false)` and before `_followWarpPending = dest`.
  - `Begin` reads the slot into `ViewRule`, then reads `BacklogNow` and `NetSyncWarpPending`.
  - It runs `PathRule` and `ActionRule`, issues the action, stamps the per-follow state and logs one start line.
  - A fault runs `FF9Wipe_FadeOutEx(24)` with the Old path.
- **`SameFieldKickTick` (:6587):** `Begin(myField, myField, true, ...)`. That is the Kick path, byte-identical, with no line.
- **`ServiceFollowWarp` (:6607):** `if (_followWarpTimer > 0f) return;` becomes:
  ```
  Int32 due = NetSyncFollowFade.Due(_followWarpTimer <= 0f, fldMapNo, _dlg, _lockEngaged);   // [ff9mapkit netsync s164]
  if (due == NetSyncFollowFade.DueWait) return;
  if (!NetSyncSwap.CommitDelayAllows(ref _followDelayFrom)) return;                          // [ff9mapkit netsync s164] A's calibration
  ```
  - `Due` keeps `primed` for the follow (set when it returns `Prime`, cleared by any other verdict) and treats `Prime` as Wait. It latches its first commit verdict (Black, Timer, Fallback or Recheck) and its swap-clock time (`due_t`) for the follow, so A's delay can hold it without the verdict being re-judged. It logs the due line once.
  - `ServiceFollowWarp` runs *before* the enabled gate (:1664-1669). With `!_enabled`, a null `_dlg` or any fault, `Due` returns `timerOut ? Timer : Wait`, which is today's behaviour.
  - The s154 guard and the write are unchanged. `NetSyncFollowFade.Ended(mapNo, due)` records `last` right after the guard's step try (:6627).
- **`NetSyncFollowFade.Clear(by)`** runs where a pending follow ends without a commit: `NoteFieldLanding` (:5810, "landing"), C's conversion ("own"), `NoteGuestWorldJump`'s world-exit cancel (:5854, "world": a following copy's own `WorldMap()` inside the fade, `NetSyncClient.cs:5849-5857`), and `TitleTick` (:5188, "title"). No session reset ends a follow: by the s42 rule a follow in flight always finishes (`NetSyncClient.cs:1664-1668`) (T14, R7).
- **Per-follow statics** (read only while `_path >= 0`): `_path`, `_action`, `_frames`, `_viewStart`, `_leftStart`, `_backlogStart`, `_startKeyTick`, `_startMs`, `_blackArmed`, `_blackSince`, `_reasserted`, `_held`, `_primed`, `_dueLatched`, `_dueT`. There are also the last-follow fields and the counters.

**Interactions.**
- **s154:** the start gates are unchanged, and the commit guard runs on every non-Wait verdict.
- **s163:** while the mirror stands, 12 ticks at 3x is about 133 ms.
- **Paused mid-fade:** ticks stop, and the fallback equals today. With `Time.timeScale` 0 the timer stops too, as today.
- **Untouched:** s144's world rejoin, and the s158/s162 landing paths.

### Log lines (behaviour)

- **Fast start:** `[NetSync] follow fade: to field D -- fast: the screen reads <view> (<sub|add>)[ (L ticks left)]; <joining its own fade (no re-init) | hurrying it to black in n ticks from where it is (no flash) | fading to black in n ticks>; the commit waits for black (no later than 0.9 s) (t T ms)`
- **Backlog start:** `[NetSync] follow fade: to field D -- today's timing: field F has a backlog (<reason>); <action words, 24>; the commit waits 0.9 s (t T ms)`. The reason is one of:
  - `a host close queued for a line still open here`
  - `a host event for a line not open here yet`
  - `a relayed host key not yet played here`
  - `a locked line open here`
- **Old start:** `[NetSync] follow fade: to field D -- today's rule (<why>): FF9Wipe_FadeOutEx(24), the commit at 0.9 s (t T ms)`, where why is one of:
  - `CALIBRATION: swap fade old`
  - `my own warp is in flight`
  - `the fade slot was unreadable`
  - `the backlog was unreadable`
- **Due:** `[NetSync] follow fade: field D due after M ms / t ticks -- <due words> (t T ms)`, where the due words are one of:
  - `the screen reads black[ after the 3-tick grace][, one dialogue pass later]` (the tail prints when the verdict came through `Prime`)
  - `today's 0.9 s timer`
  - `the 0.9 s fallback: the fade never read black (<view>, darkest channel c)`
  - `today's 0.9 s timer: a backlog rose mid-fade (<reason>)`
- **Backlog mid-fade:** `[NetSync] follow fade: a backlog rose mid-fade on field F (<reason>) -- the commit waits for today's 0.9 s timer (t T ms)`.
- **Reassert:** `[NetSync] follow fade: the fade slot turned away from black mid-follow (<view>, darkest channel c) -- fading to black again in n ticks from where it is (once per follow) (t T ms)`
- **World cancel:** none of its own; s144's existing cancel line (`NetSyncClient.cs:5852-5853`) covers it, and `fade.last.by` reads `world`.

---

## The lever scheme: `netsync swap <op> [arg]`

Dispatch: in `HarnessAgent.cs`, a new `case "swap"` after `case "speed"` (:2245-2262) calls `NetSyncSwap.HarnessLever(s.Args, out why)`. The unknown-sub-verb literal (:2264) gains `|swap`.

| op | args | Roles | What it does |
|---|---|---|---|
| `stamps` | `on\|off` | any | A. `off` = CALIBRATION: no stamps, no tails, no `[NetSync] swap` lines |
| `delay` | `<0-2000>` | client, selftest | A. CALIBRATION of the instrument: every follow commit waits N ms past its verdict (`DelayRule`) |
| `orphan` | `act\|old` | client, selftest | B. `old` = s163's `OrphanSettled` |
| `own` | `act\|old\|nocache` | client, selftest | C. `old` = s163's passes (my field or the lane field; the cache still records); `nocache` = the pending, committed and intent terms only |
| `pin` | `act\|old` | client, selftest | PIN. `old` = every landing stages the latest frame (the capture still runs, so state shows what the pin would have done) |
| `life` | `act\|old` | host, selftest | LIFE. `old` = s163's self-clear at :2095, and no publish-clock reset |
| `fade` | `act\|old\|long\|nogate\|norecheck\|nohurry` | client, selftest | D+E. `old` = today's start and commit; `long` = D with a 24-tick fast fade (E off); `nogate` = no backlog gate (the refuted rule); `norecheck` = the gate checked at the start only; `nohurry` = a fade already heading to black is never re-paced |
| `clear` | none | any | Every lever back to act, stamps on, delay 0, hostctl on, bench state forgotten; a party mirror the pin bench armed is cleared (`NetSyncParty.Clear()` when `_pinBenchMirror` is set) |
| `hostctl` | `off\|on` | selftest | B's bench host: section 7 with b1 and b0 clear (it stands here with its control off and no scene) |
| `intent` | `<field>` | selftest, needs `bench 1` | Section 4 through the real codec into the seen record and the bench cache, then `DebugInjectIntentImpl` (:7239-7289), which starts a real follow. It captures no pin |
| `cache` | `<field>` | selftest | Section 4 through the real codec into C's cache only (src my field, `host_from` -1, `bench` true) |
| `pinbench` | `<field> <flag> [age <ms>] [landed] [party <slot> <char>] [to <field>]` | selftest, needs `bench 1` | Frame A = `SnapshotAll()` plus section 4 (`IntentSectionBody`, the bit clear) through the real `AppendSection` and the real `PinCaptureRule`. `landed` builds A with the landed bit set (the first frame the guest saw was built after the host's landing: Late); `age <ms>` marks the host's landing seen that long ago. Frame B, standing in as the latest frame, is `SnapshotAll()` taken through the real encoder with `<flag>` set in its section 0; with `party`, that `SnapshotAll()` runs with `NetSyncParty.SlotSource` pointing slot `<slot>` at `ff9.player[<char>]` (the SelfTestMirror idiom, `NetSyncParty.cs:497-499`), restored in a finally, so slot `<slot>` carries a self-consistent CharacterId, name and v9 block from the real codec (I4). Then `StartFollowWarp` |
| `lifebench` | `<field>` | selftest | A bench emit (field, nonce, active, tick, Pending, site `bench`) with no socket, then a debug warp. The hook and the per-Update step run in the selftest branch, before :2039 |
| `blackout` | `<1-255>\|off` | selftest | `InitFade(Sub, n, white)` stands in for the copy's own `FadeFilter`. `off` runs `InitFade(Sub, 1, black)` |
| `arrive` | `act\|old` | client, selftest | Rev 4, the arrival guard. `old` = CALIBRATION: s158's dwell from the base start at every landing. Read at the landing (`ARRIVAL-GUARD-S164.md`, "Lever, state, log") |
| `arrivebench` | `<-1000..5000>` | selftest | Rev 4. One-shot: my next landing gets a bench host that landed L ms before me (negative: after me), written through the real codec as section 4 with the landed bit. No `bench 1` needed |

**Refusal order.** For a known op the role comes first, as in s163's `speed host`:
1. An unknown op gets the usage line (as built, with rev 4's two ops): `netsync swap: expected stamps on|off or clear (any role); delay <0-2000>, orphan act|old, own act|old|nocache, pin act|old, fade act|old|long|nogate|norecheck|nohurry or arrive act|old (a client or the selftest role); life act|old (the host or the selftest role); hostctl off|on, intent <field>, cache <field>, pinbench <field> <flag> [age <ms>] [landed] [party <slot> <char>] [to <field>], lifebench <field>, blackout <1-255>|off or arrivebench <lead_ms> (the selftest role)`
2. Co-op off, for every op except `clear`: `netsync swap: co-op is off -- no role to act on`
3. A guest-side op on a host: `netsync swap <op>: a guest-side lever (a client or the selftest role) -- this game is the host`
4. A host-side op on a client: `netsync swap <op>: a host-side lever (the host or the selftest role) -- this game is a client`
5. A bench op off the selftest role: `netsync swap <op>: needs the selftest role (netsync selftest 1)`
6. `intent` or `pinbench` without the gate: `netsync swap <op>: needs the field-gate bench (netsync bench 1)`
7. Bad arity or range: the usage line.

**Getters (the s163 shape, F9).** The role is checked when a lever is set (steps 3-5 above); a lever is stored as set and read through a plain getter. No Netsync file reads HarnessAgent.

```
internal static Boolean StampsOn       { get { return !_stampsOff; } }
internal static Int32   DelayMs        { get { return _delayMs; } }
internal static Boolean OrphanLeverOld { get { return _orphanOld; } }
internal static Int32   OwnLever       { get { return _own; } }
internal static Boolean PinLeverOld    { get { return _pinOld; } }
internal static Boolean LifeOld        { get { return _lifeOld; } }
internal static Int32   FadeLever      { get { return _fade; } }
internal static Boolean BenchHostCtlOff{ get { return _hostCtlOff && NetSyncClient.IsSelfTestRole; } }   // bench state, not a lever
internal static Boolean ArriveOld      { get { return _arriveOld; } }   // rev 4: the arrival guard's lever
```

Every bench op acts only on `IsSelfTestRole`.

**Release.** `NetSyncSwap.HarnessRelease()` runs from `NetSyncBattle.HarnessReleaseBench` right after s163's `NetSyncSpeed.HarnessRelease()` (`NetSyncBattle.cs:6840`), on every role. `HarnessReleaseBench` runs on every `HarnessSelfTest(false)` above its forced-role return (`NetSyncClient.cs:9403-9407`): disarm, fault, `reset`, and a release deferred to a harness diorama's teardown (`HarnessAgent.cs:2353-2361`).
- It sets everything to act, forgets the bench cache, the pin bench and the life bench, and turns the bench host's control back on.
- When `_pinBenchMirror` is set it calls `NetSyncParty.Clear()` and resets the flag (G2). It is gated on that flag, never on the role: `HarnessReleaseBench` runs on every role (`NetSyncBattle.cs:6758, 6840`), and an ungated clear would wipe a live guest's real party mirror on `reset`. `reset` itself never clears the party mirror (`ApplyConfigChange`, `NetSyncClient.cs:1392-1436`, calls no `NetSyncParty.Clear`), which is why the release must.
- A blackout is undone with `InitFade(Sub, 1, black)`.
- Rev 4: `arrive` goes back to act, and the guard's bench arm and any host-landing record that bench wrote are forgotten (never a live host's own record).
- It logs one line, and only when something was set.
- `reset` also tears down a forced selftest role (`NetSyncClient.cs:9415-9431`, `_enabled = false` at :9426), so a solo leg that follows again after a release re-arms first (K-RELEASE, F13).

**What each lever turns red** is registered under § Benches. The dependencies:
- `fade old` makes E moot, because E needs D's tick count.
- `life old` leaves DC-B(a) green: a following guest sees the intent through the follow (Pending/Committed) or the cache.

**Harness lines:**
- `[NetSync] harness: swap stamps OFF -- CALIBRATION: no '(t N ms)' stamps, no waited/shown tails, no swap lines (released with the harness)` and `... swap stamps ON`
- `[NetSync] harness: swap delay N ms -- CALIBRATION: the follow's commit waits N ms past its own verdict (released with the harness)`
- `[NetSync] harness: swap orphan OLD -- CALIBRATION: s163's orphan rule, a plain line ignores the host's control (released with the harness)` and `... swap orphan ACT`
- `[NetSync] harness: swap own OLD -- CALIBRATION: s163's rule, an own Field() passes only on my field or the host's lane field (released with the harness)`, `... swap own NOCACHE -- CALIBRATION: the pending, committed and live-intent terms only (released with the harness)`, and `... swap own ACT`
- `[NetSync] harness: swap pin OLD -- CALIBRATION: s163's rule, every landing stages the latest frame (released with the harness)` and `... ACT`
- `[NetSync] harness: swap life OLD -- CALIBRATION: s163's self-clear, no publish-clock reset (released with the harness)` and `... ACT`
- `[NetSync] harness: swap fade <VALUE> -- ...`, where the value is one of:
  - `OLD -- CALIBRATION: today's rule (FF9Wipe_FadeOutEx(24), the commit at 0.9 s; released with the harness)`
  - `LONG -- CALIBRATION: the fast follow fades 24 ticks, not 12 (released with the harness)`
  - `NOGATE -- CALIBRATION: the fast follow with no backlog gate (the refuted rule; released with the harness)`
  - `NORECHECK -- CALIBRATION: the backlog read at the start only (released with the harness)`
  - `NOHURRY -- CALIBRATION: a fade already heading to black is never re-paced (released with the harness)`
  - `ACT`
- `[NetSync] harness: swap CLEAR -- every lever act, stamps on, delay 0, the bench host's control on, bench state forgotten[; the pin bench's party mirror cleared]`
- `[NetSync] harness: swap hostctl OFF -- the bench host stands on my field with its control off, no scene (section 7 b1 and b0 clear)` and `... ON`
- `[NetSync] harness: swap intent -- a bench host's section 4 for field D (nonce N) through the real codec (the selftest role)`
- `[NetSync] harness: swap cache -- section 4 = field D nonce N through the real codec, cached on field F`
- `[NetSync] harness: swap pinbench -- intent N's frame for field D through the real codec (flag B: pin P, latest L[; party slot S: pin C0, latest C1][; built after the host's landing][; landing seen A ms ago])`
- `[NetSync] harness: swap lifebench -- a bench emit for field D (nonce N), no socket`
- `[NetSync] harness: swap blackout N -- the fade slot heads to black in N ticks (a copy's own FadeFilter stand-in)` and `... swap blackout OFF -- the fade slot back to visible`
- Rev 4: the `swap arrive OLD|ACT` and `swap arrivebench L` lines, and the guard's behaviour lines, are listed in `ARRIVAL-GUARD-S164.md`, "Lever, state, log".
- Release: `[NetSync] harness: swap levers released (every lever act, stamps on, delay 0, the bench host's control on, bench state forgotten[; the pin bench's party mirror cleared])`

---

## The `netsync.swap` state block

- It is netsync's LAST key, after s163's `speed`: `HarnessAgent.cs:4021` gains `sb.Append(","); AppendSwap(sb);`.
- It is additive. The harness protocol stays 5 and the wire stays v14; round 1 adds no wire section.
- `AppendSwap` reads each sub-block through its own try.
- The catch literal (:4074) gains the block at its sentinels, in this order.
- The ProtocolVersion paragraph (:386-397) gains s164: a driver checks for `netsync.swap`, and an s163 engine answers `unknown sub-verb 'swap'`.
- Every `*_t` key is a swap-clock value, -1 = never. Counters are per-process and monotonic; benches read deltas.

```
"swap": {
  "clock":  {"now_ms":-1, "utc_ms":-1, "ticks":-1, "hz":-1, "src":null, "hires":false, "fps":-1, "target_fps":-1},
  "levers": {"stamps":null, "delay_ms":0, "orphan":null, "own":null, "pin":null, "life":null, "fade":null, "hostctl_off":false,
             "arrive":null},
  "open": false,
  "last":   {"id":0, "role":null, "from":-1, "dest":-1, "state":null, "open_by":null, "open_t":-1,
             "emit_t":-1, "nonce":-1, "seen_t":-1, "arrived_t":-1, "seen_copies":0,
             "follow_t":-1, "follow_via":null, "follows":0,
             "own_t":-1, "own_dest":-1, "own_verdict":null, "own_why":null, "owns":0, "bounces":0,
             "due_t":-1, "commit_t":-1, "commit_field":-1, "commit_why":null, "delay_ms":0, "drop_t":-1, "drop_why":null,
             "reloads":0, "reload_t":-1, "land_t":-1, "land_field":-1, "land_via":null, "story":null,
             "fade_path":null, "fade_ticks":-1, "line_t":-1, "line_win":-1, "line_text":-1, "close_t":-1, "close_why":null},
  "seen":   {"nonce":-1, "field":-1, "src":-1, "host_from":-1, "first_t":-1, "last_t":-1, "arrived_t":-1, "copies":0},
  "intent": {"active":false, "field":-1, "nonce":-1, "site":null, "emit_t":-1, "age_ms":-1, "host_fps":-1, "emit_dt_us":-1,
             "landing":null, "landed_ms":-1, "body_ms":-1,
             "frames":0, "landed_frames":0, "updates":0, "sends":0, "first_sent_t":-1, "last_sent_t":-1, "oob":null,
             "end_t":-1, "last_end":null, "last_life_ms":-1, "last_site":null, "emits":0, "replaced":0, "oob_lost":0, "short":0,
             "ends":{"stands":0,"left":0,"elsewhere":0,"cap":0,"old":0,"next":0,"reset":0}, "faults":0},
  "slot":   {"set_seq":-1, "sent_seq":-1, "sends":-1, "unsent":-1},
  "orphan": {"host_holds":false, "holding":0, "holds":0, "relocks":0, "last_hold_ms":-1, "last_end":null, "faults":0},
  "own":    {"passes":0, "by":{"pending":0,"committed":0,"intent":0,"cache":0}, "converted":0,
             "refused":{"world":0,"ate":0}, "host_lane":-1,
             "last":{"dest":-1, "from":-1, "lane":-1, "term":null, "keep_own":false},
             "cache":{"field":-1, "nonce":-1, "src":-1, "host_from":-1, "age_ms":-1, "stands":false, "bench":false,
                      "writes":0, "clears":0, "last_clear":null}, "faults":0},
  "pin":    {"held":[], "spent":-1, "captures":0, "late":0, "pre_frames":0, "max_pre_diff":-1, "dropped":0, "here":0,
             "used":0, "aged":0, "other":0, "world":0, "lever_latest":0,
             "last_use":null, "last_use_quality":null, "last_use_field":-1, "last_use_age_ms":-1, "last_diff":-1, "last_diff_first":-1,
             "last_party":null, "faults":0,
             "bench":{"armed":false, "flag":-1, "chosen":null, "landed":false, "party_slot":-1, "party_char":-1, "mirror":false}},
  "fade":   {"view_now":null, "mode_now":null, "cur_now":-1, "left_now":-1, "backlog_now":null, "primed":false,
             "path":null, "action":null, "frames":-1, "view_start":null, "left_start":-1, "backlog_start":null,
             "age_ms":-1, "age_ticks":-1, "black_ticks":-1, "reasserted":false, "held":false,
             "last":{"field":-1, "path":null, "action":null, "by":null, "due_t":-1, "ms":-1, "ticks":-1, "frames":-1,
                     "view_start":null, "mode_start":null, "backlog_start":null, "primed":false},
             "starts":{"fast":0,"backlog":0,"old":0,"kick":0},
             "ends":{"black":0,"timer":0,"fallback":0,"recheck":0,"landing":0,"own":0,"world":0,"title":0},
             "reasserts":0, "faults":0},
  "counts": {"transitions":0, "landings":0, "own_jumps":0, "bounces":0, "follow_won":0,
             "closed":{"line":0,"window":0,"stale":0,"superseded":0,"next":0,"reset":0}},
  "faults":0, "last_fault":null, "selftest":null,
  "arrive": {"arrival_lead_ms":-1, "armed":false, "field":-1, "land_t":-1, "lead_ms":null, "late":false,
             "host":{"field":-1, "nonce":-1, "seen_t":-1, "age_ms":-1, "bench":false},
             "episode":{"on":false, "held":false, "base_ms":null, "dwell_ms":null, "shift_ms":null},
             "last":{"field":-1, "lead_ms":null, "end":null, "base_ms":null, "dwell_ms":null, "shift_ms":null},
             "arms":0, "late_arms":0, "unanchored":0, "world":0, "held":0, "ends":{"spared":0,"delayed":0,"line":0,"ate":0},
             "spends":{"control":0,"field":0,"out":0,"session":0}, "bench":{"armed":false, "lead_ms":null}, "faults":0}
}
```

Each `pin.held` entry is `{"field", "nonce", "quality", "land_seen", "age_ms", "capture_ms"}` (`age_ms` = `PinAgeRule` now). `pin.bench.mirror` reads `_pinBenchMirror`. `fade.last.primed` is true when the follow's Black verdict came through `Prime` (S2), and `intent.landed_frames` counts host frames that carried the landed bit (S3). `fade.last.ms` and `fade.last.ticks` measure the follow's start to its **due** verdict (`fade.last.due_t`); the commit is `last.commit_t`, and `last.commit_t - last.due_t` is A's delay (F6). Rev 4: `levers.arrive` (null or `old`, the last key of `levers`) and the `arrive` block (the last key of `swap`) are the arrival guard's; the "Lever, state, log" section of `ARRIVAL-GUARD-S164.md` owns their meanings. The fence is read by the kit's sentinel parity test, so it, `FG.NETSYNC_SWAP_SENTINELS` and the engine's netsync-off catch literal change together.

**Value vocabularies:**

| Key | Values |
|---|---|
| `clock.src` | `qpc`, `stopwatch` |
| `last.state` | `open`, `landed`, `done` |
| `last.follow_via` | `intent`, `serial` |
| `last.story` | `pin`, `latest` |
| `intent.site`, `intent.last_site` | `mapjump`, `debugwarp`, `bench` |
| `intent.landing` | `pending`, `on_intent`, `elsewhere` |
| `pin.held[].quality`, `pin.last_use_quality` | `pre`, `late` (`none` in `last_use_quality` when no entry was held) |
| `pin.last_use` | `pin`, `none`, `other`, `late`, `aged`, `world`, `lever`, `skipped_stale` |
| `fade.last.mode_start` | `sub`, `add` |
| `pin.last_party` | `latest` (round 1 never stages the party from the pin) |
| `fade.path` | `fast`, `backlog`, `old`, `kick` |
| `fade.action` | `join`, `hurry`, `fade`, `wipe` |
| `fade.last.by` | `black`, `timer`, `fallback`, `recheck`, `landing`, `own`, `world`, `title` |
| `orphan.last_end` | `closed`, `event`, `relay`, `left`, `busy`, `control`, `forgot` |
| `selftest` | null until the proof ran, then `ok` or `fail: <row or mutant>` |
| `last_fault` | `<item>@<site>: <msg>` |

Existing keys the benches read: `netsync.host_flags` (section 7), `host_settled_ms`, `orphan_closes`, `netsync.stepout` (`active`, `out_why`), and `netsync.dress.party` / `netsync.dress.mirror_party` (`HarnessAgent.cs:4117-4118, 4168`: the party mirror's CharacterIds, the same slots `B_PARTYCHK` reads).

---

## SelfTest: one proof line

`NetSyncSwap.SelfTest(out String detail, Func<Byte[]> frameWithIntent)` runs every rule's rows and then every mutant. Each mutant restores a rejected rule and must fail at least one row.
- The template is `NetSyncSpeed.SelfTest` (`NetSyncSpeed.cs:717, 1112`).
- `frameWithIntent` is supplied by `NetSyncClient`. It saves and restores `_intentActive`, `_intentField`, `_intentNonce` and `_intentLanding` in a try/finally around `BuildStateFrame(true, true)`, the s163 delegate precedent (:1948).
- D+E's rows live in `NetSyncFollowFade.SelfTestRows(ref rows, ref fails)` and are called from it. C's `quiet_equals_loud` sweep drives `NetSyncAte`'s `internal static HoldVerdict` and compares `HoldsFollowQuiet` with `HoldsFollow` under a save and restore of NetSyncAte's statics (I9).
- The live row `pin_split_applies` parses a party, so it runs only when the party mirror is idle (it fails closed when `NetSyncParty.MirrorActive` or `BenchMirrorArmed` is set, like `PartyParsesAlike`, `NetSyncClient.cs:10730`) and calls `NetSyncParty.Clear()` in its finally.

The proof block (after :1950) gets one new last line:

```
[NetSync] field swap selftest: OK (N rows, M mutants caught, clock qpc|stopwatch H Hz high-res|low-res, line window 10000 ms,
span 30000 ms, cache 2000 ms, intent life 2000 ms / land tail 1000 ms / cap 10000 ms, pin age 2500 ms / blind 10000 ms,
fade 12 / 24 ticks / 900 ms, join grace 3 ticks, black floor 248, ahead 3000 ms, arrival lead 1040 ms)
```

Rev 4: the tail `, arrival lead 1040 ms` is the arrival guard's K (`ArrivalLeadMs`), and N and M count the guard's rows and mutants (the table below).

- A failure reads `FAIL (row <id>)` or `FAIL (mutant <id> survived)`.
- The clock source and `hires` are reported and never fail the line.
- The kit regex pins every constant and captures N, M, the source, H and the resolution.
- The dialogue selftest's `KeyScript` row changes as described under §B. Its detail text is unchanged.

| Item | Rules | Rows (about) | Mutants |
|---|---|---|---|
| A | TicksToMs, stamp, parse, waited, JoinRule, OpenClosesRule, CloseRule, LandViaRule, DelayRule, OobVerdict, SeenRule, slot (live on a real `new NetSyncFrames()`), line builders | 102 | 27 |
| B | OrphanSettled ×16, HostHoldsRule ×8, the composite `OrphanStep(OrphanSettled)` ×12 under act and old, CtlHoldKind, HoldEndWhy, OrphanSinceRule, KeepReadRule, scenarios S1-S6 | 66 | 12 |
| C | OwnFieldPassRule, OwnJumpVerdictRule, IntentCacheStep, IntentCacheVerdict, OwnPassBook, OwnPassKeepsOwn, the s154 sequence rows, `quiet_equals_loud`, the codec (live) | 79 | 32 |
| LIFE | IntentLifeRule, BodyThereRule, IntentLandingStep, live `frame_carries_4` | 28 | 13 |
| PIN | PinCaptureRule, IntentSectionBody / IntentLandedOf, PinUseRule, PinConsumed, PinDropOnNew, PinTargeted, PinAgeRule, LandingFrames, one sequence row, live `pin_applies_verbatim` and `pin_split_applies` | 48 | 19 |
| D+E | View, Backlog with its cascade, counting, Path, Action, Grace, BlackTicks, Due with the `never_past_the_timer` sweep, Reassert, live `slot_reads` and `today_constants` | 102 | 43 |
| ARRIVE (rev 4) | The arrival guard's ten rules in a nested `ArriveRules` (seams Seen, Edge, Arm, Anchor, Holds, DwellAge, Held, Spend, End, Count), composition rows on the real `NetSyncStepOut.StartRule`, live `arrive_codec` (`ARRIVAL-GUARD-S164.md`, "SelfTest") | 75 | 37 |
| **Total** | | **about 425** designed, **426** built; **501** with ARRIVE | **about 146** designed, **146** built; **183** with ARRIVE |

Following s163 rev 3, the build drops any mutant that only renames another; every term keeps a row that kills it.

### A: rows and mutants

Rows (the A spec's inputs; ids as the spec writer gave them):
- **clock** (`TicksToMs(ts, freq)`): `zero` (0, 1e7 → 0), `sub_ms` (9999, 1e7 → 0), `one_ms` (10000, 1e7 → 1), `mono_100ns` (12345678901, 1e7 → 1234567), `acpi_exact` (3579545·7 → 7000), `acpi_remainder` (3579545·7 + 3580 → 7001), `acpi_long` (3579545·1000 → 1000000), `tsc_40_days` (40·86400·3e9, 3e9 → 3456000000), `bad_freq` (5, 0 → -1); live `monotonic` (two `NowMs` reads never go backwards) and live `source` (the chosen source is reported; never fails).
- **stamp:** `on` (T, 5 → " (t 5 ms)"), `off` (F, 5 → ""), `negative` (T, -1 → ""), `big` (T, 123456789012 → its text).
- **parse:** `round_trip_intent`, `round_trip_queued`, `round_trip_tap`, `round_trip_closed` (waited 120, shown 2350, the s163 core), `no_stamp` → false, `inner_not_suffix` ("x (t 5 ms) y" → false), `garbage` ("x (t 5a ms)" → false), `waited.off`, `waited.no_seen`, `waited.no_page` (→ "").
- **join** (edge, field, myField, kick, record state/dest/from/age): `seen_opens`, `seen_my_field_ignored`, `seen_joins_landed`, `seen_joins_done_in_span`, `follow_joins`, `follow_other_dest_opens`, `emit_opens`, `own_opens`, `own_same_field_reload`, `own_same_field_no_record`, `kick_ignored`, `kick_commit_ignored`, `land_dest`, `land_source_reload`, `land_dest_again`, `land_never_opens`, `land_elsewhere`, `line_landed`, `line_open_ignored`, `line_done_ignored`, `span_expired_opens` (21).
- **opens/closes:** `opens.open` (Open → Superseded), `opens.landed` (Landed → Next), `opens.done` (Done → None).
- **close:** `line`, `window_not_yet` (land 0, now 9999 → None), `window` (now 10000 → Window), `open_not_stale` (29999 → None), `open_stale` (30000 → Stale), `line_on_open_ignored`, `none`.
- **via** (fld, writer, writer's dest, recDest, prev): `follow`, `follow_wiped` (351, Follow, 352 → Same), `bounce`, `own_on_dest`, `host`, `kick`, `same`, `other`, `dest_only` (352, None, -1, 352, 351 → Other).
- **delay** (delayMs, followT, readyT, now): `off`, `not_ready`, `inside` (200, 0, 900, 1099 → false), `edge` (… 1100 → true), `from_verdict_not_follow` (200, 0, 900, 900 → false), `negative_is_off`.
- **oob:** (T,F,F) → Unknown, (T,F,T) → Sent, (T,T,F) → Overwritten, (T,T,T) → Sent, (F,-,-) → None.
- **seen:** `new`, `same`, `absent`.
- **slot** (live on a real `new NetSyncFrames()`): `oob_sent` (`SetStateWatched(A)`, Collect → FromSent, WatchSends 1), `oob_overwritten` (`SetStateWatched(A)`, Set B → FromReplaced, not FromSent), `window_closed` (… `WatchStateSeqs(from, seq + 1)`, Set C, Collect → WatchSends unchanged), `unsent_count` (Set A, Set B → Unsent 1), `watched_is_atomic` (`SetStateWatched` returns the seq it armed: `WatchFrom == SetSeq` read back in one probe).
- **lines:** each builder against its exemplar (landed, commit, kick commit, own pass, own bounce, both close lines, clock), and each builder's `off` row. Three rows build the own-jump line for a C refusal followed by each verdict the old rule can reach (`own_refusal_host`: pass host-field; `own_refusal_through`: through; `own_refusal_bounce`: bounce). Each yields exactly one line that starts `[NetSync] own Field(` and ends with that verdict's outcome words (I2).

| Mutant | Restores | Caught by |
|---|---|---|
| `ms_naive` | `ts*1000/freq` | clock.tsc_40_days |
| `ms_freq_truncated` | `ts/(freq/1000)` | clock.acpi_long |
| `ms_whole_seconds` | `(ts/freq)*1000` | clock.mono_100ns |
| `stamp_lever_blind` | the stamp ignores the lever | stamp.off |
| `stamp_negative_printed` | "(t -1 ms)" | stamp.negative |
| `stamp_inside` | the stamp before the last ")" | parse.round_trip_closed |
| `parse_anywhere` | a stamp anywhere in the line | parse.inner_not_suffix |
| `waited_negative_printed` | a tail with a missing input | waited.no_seen |
| `join_any_dest` | any destination joins | join.follow_other_dest_opens |
| `landing_opens` | every load is a swap | join.land_never_opens |
| `kick_joins` | the kick joins | join.kick_ignored |
| `seen_opens_my_field` | my own field opens | join.seen_my_field_ignored |
| `span_forever` | no record span | join.span_expired_opens |
| `line_any_state` | a line joins any state | join.line_open_ignored |
| `own_reload_opens` | a same-field own jump opens | join.own_same_field_no_record |
| `open_leaves_previous_open` | a new record leaves an open one open | opens.open |
| `via_by_dest` | the writer inferred from the destination | via.own_on_dest |
| `via_any_writer` | the writer's destination ignored | via.follow_wiped |
| `close_on_landing` | a record closes at its landing | close.window_not_yet |
| `close_on_any_line` | a line closes an open record | close.line_on_open_ignored |
| `stale_never` | no stale close | close.open_stale |
| `delay_from_follow` | the delay hidden inside the 900 ms timer | delay.from_verdict_not_follow |
| `delay_ignored` | no delay | delay.inside |
| `oob_replace_is_send` | a replaced frame counts as sent | oob.(T,T,F) |
| `oob_none_is_unknown` | no frame reads unknown | oob.(F,-,-) |
| `seen_every_frame` | every copy is a new seen edge | seen.same |
| `lines_ignore_stamps_lever` | builders print with stamps off | lines.*.off |

### B: rows and mutants

Rows:
- **R-B1:** the 16 rows of the `OrphanSettled` table above (settledLong, inh, holds under act and old).
- **R-B2** (here, view, control): (T, T, off) → T; every row with here = F → F; every row with view = F → F; (T, T, on) → F (8 rows).
- **Composites** `OrphanStep(cls, OrphanSettled(...))`, under act / old: 1 Locked plain, long, unclaimed, holds: None / ToOrphaned (Finding 11); 2 control on: ToOrphaned / ToOrphaned; 3 event pending: None / None; 4 relayOwned: None / None; 5 not long: None / None; 6 polled, holds: None / None; 7 polled, control on: ToLocal / ToLocal; 8 Orphaned plain, holds, ready, past AutoReadMs: ToLocked / Confirm (the relock); 9 Orphaned, control on, ready, past: Confirm / Confirm; 10 Orphaned, holds, not ready: ToLocked / None; 11 Orphaned polled, holds: ToLocked / ToLocal; 12 Local: None / None.
- **CtlHoldKind** on composites 1, 8 and 10, plus one unreachable combination (→ CtlNone).
- **HoldEndWhy:** 6 rows; the key one (present, unclaimed, no relay, not here, not long, not holds) → Left.
- **OrphanSinceRule:** `since.fresh` (F, -, 5000 → 5000), `since.relock_keeps` (T, 1000, 5000 → 1000).
- **KeepReadRule:** `keep.control` (Control → T), `keep.busy` (Busy → F), `keep.left` (Left → F).
- **Scenarios** (deltas only, across the Int32 tick wrap; `SettleClock` and the composite stepped per 100 ms tick): S1 the leap (the host lands co-located, control off, no scene; under act never ToOrphaned to t0+30000, under old ToOrphaned at t0+OrphanGraceMs); S2 control back at t1 (ToOrphaned on t1's tick, Confirm at t1+AutoReadMs); S3 one blip (no Confirm through t1+AutoReadMs+2000); S4 a scene rising during the hold (Busy, then Event); **S5 repeated blips** (a fresh, complete, single-page line orphaned at t0; control off for 0.5 s every 1.5 s from t0 + 1.0 s: exactly one relock, then Confirm on the first orphaned tick at or after t0 + AutoReadMs, V4); **S6 a control hold that turns into a scene** (orphaned at t0; control off at t0 + 0.5 s, the relock; a host scene rises at t0 + 1.0 s, so the hold ends Busy; the scene falls and the host settles at t1: the re-orphan restarts the clock, and Confirm comes no earlier than the re-orphan + AutoReadMs, I5).

| Mutant | Restores | Caught by |
|---|---|---|
| `orphan_polled_only` | s163's rule under act | R-B1 (T, F, T, act) |
| `orphan_holds_alone` | `!hostHoldsInput`, no settle clock | R-B1 (F, F, F, act) |
| `orphan_lever_ignored` | the lever does nothing | R-B1 (T, F, T, old) |
| `orphan_old_is_c2` | the lever restores pre-C3KEYS-4 `settledLong` alone | R-B1 (T, T, T, old) |
| `holds_without_here` | a host in another field holds my lines | R-B2 (F, T, off) |
| `holds_without_view` | a missing section 7 reads as control off | R-B2 (T, F, 0) |
| `hold_capped` | an 8000 ms cap | S1 |
| `hold_restarts_grace` | the grace restarts when control returns | S2 |
| `end_why_control_first` | "control is back" before "left" | the HoldEndWhy Left row |
| `relock_dropped` | the hold applies to Locked only | composite 8 |
| `relock_restarts_read` | a re-orphan restarts the read clock (rev 1) | since.relock_keeps, S5 |
| `relock_keeps_after_busy` | every hold end keeps the read clock (rev 2's sticky flag) | keep.busy, S6 |

### C: rows and mutants

Rows (my field 351, dest 352, another 350, a third 353):
- **OwnFieldPassRule:** `pass.pending`, `pass.committed`, `pass.intent`, `pass.cache`; `order.pending_first` (all four match), `order.committed_before_intent`, `order.intent_before_cache`; `none.nothing`, `none.pending_other_field` (pending 350, dest 352: the C2 guard), `none.intent_other_field`, `none.cache_other_field`, `none.cache_not_standing`, `none.kick` (pending 352 with kick), `none.my_field`, `none.ending` (dest 16000, live 16000), `none.unusable`, `none.dest_0`, `none.dest_65535`, `none.not_following`; `lever.off_pending`, `lever.off_intent`, `lever.nocache_cache`, `lever.nocache_keeps_pending`, `lever.nocache_keeps_intent`; `refuse.world`, `refuse.ate`, `refuse.world_before_ate`, `refuse.only_on_a_match` (holds set, no term → None), `refuse.lever_off_quiet` (off with a hold and a term → None).
- **OwnJumpVerdictRule, `commit_then_own_same_tick` (T4):** s1 (act, committed 352, pending -1, lane 351, own `Field(352)` → Pass committed: one load), s2 (the same under `own old` → Bounce), s3 (pending 352 → Pass pending; the book converts), s4 (committed 352, own `Field(353)`, lane 351 → Bounce: the divergent copy, risk 19), s5 (committed 352, lane 352, own `Field(352)` → Pass committed, not host-field: C decides before the lane).
- **IntentCacheStep:** `write.first`, `write.new_nonce`, `write.wrapped_nonce` (255 → 0), `write.after_reset` (nonce -1 → 0); `keep.same_nonce`, `keep.spent_nonce`, `keep.no_section`; `skip.my_field`, `skip.supersedes`, `skip.ending`, `skip.no_field` (myField -1).
- **IntentCacheVerdict:** `stands.stale_source_frame` (lane = src), `stands.lane_0`, `stands.lane_65535`, `stands.lane_minus1`, `stands.lane_on_cached`, `stands.lagging_guest_stale_source` (src 349, hostFrom 351, lane 351), `stands.hostfrom_unknown_src_exempt`; `host_past` (lane 353), `left` (myField 352), `aged_at_cap` (2000), `stands_below_cap` (1999), `none`, `negative_age`; `order.left_before_aged`, `order.aged_before_host_past`.
- **OwnPassBook and OwnPassKeepsOwn:** `book.pending_converts`, `book.pending_bends`, `book.committed_unchanged`, `book.intent_no_bend`, `book.cache_no_bend`, `book.refused_no_change`; `entrance.host_by_default`, `entrance.exit_hold_keeps_own`, `entrance.none_never`.
- **Sequence rows** (the real s154 rules, after the book): `seq.pending_pass_lands_clean` (`FollowLandingStep(352, -1, 352, 352, false)` → `LandNone`, keep 352), `seq.commit_idle`, `seq.overwrite_still_rearms` (landing on 351 → `LandLatchVoid`, re-arm 352), `seq.intent_pass_landing`, `seq.kick_never_rearms_follow`.
- **`quiet_equals_loud`** (F7): the full grid through `HoldVerdict` and `HoldsFollowQuiet`, equal at every point (one row, counted once per rule set). Within one SelfTest call the verdict grid runs once and the live hold grid runs only for a rule set with a different `Quiet` delegate (review fix F09); the proof's cost line reports K rule sets, V and L sweeps.
- **Live, counted once:** `codec.intent_section_round_trip`.

| Mutant | Restores | Caught by |
|---|---|---|
| `pass_s163` | always None | pass.pending, s1 |
| `pass_dest_blind` | C2: any present term passes | none.pending_other_field |
| `pass_kick_counts` | a kick's pending counts | none.kick |
| `pass_no_world_recheck` | the s144 hold ignored | refuse.world |
| `pass_no_ate_recheck` | the s161 holds ignored | refuse.ate |
| `pass_refuse_without_match` | a hold refuses with no term | refuse.only_on_a_match |
| `pass_following_blind` | passes while not following | none.not_following |
| `pass_usable_blind` | passes to an unusable field | none.unusable |
| `pass_ending` | passes the ending | none.ending |
| `pass_cache_unchecked` | a cache that no longer stands | none.cache_not_standing |
| `pass_nocache_blind` | `nocache` ignored | lever.nocache_cache |
| `pass_nocache_all` | `nocache` drops every term | lever.nocache_keeps_pending |
| `pass_order_cache_first` | the cache before the intent | order.intent_before_cache |
| `pass_refusal_order` | the ATE refusal before the world one | refuse.world_before_ate |
| `lane_before_own_pass` | s163's lane pass before C | s5 |
| `stands_source_frame_clears` | any lane but the cached field clears | stands.stale_source_frame |
| `stands_src_blind` | the source field ignored | left |
| `stands_no_cap` | no 2000 ms cap | aged_at_cap |
| `stands_cap_inclusive` | `>` for `>=` | aged_at_cap |
| `stands_hostfrom_blind` | `host_from` ignored | stands.lagging_guest_stale_source |
| `stands_sentinel_clears` | 0 / 65535 clear | stands.lane_0, stands.lane_65535 |
| `step_same_nonce_refreshes` | the same nonce re-caches | keep.same_nonce |
| `step_caches_my_field` | caches my own field | skip.my_field |
| `step_caches_ending` | caches the ending | skip.ending |
| `step_no_supersede` | a new nonce leaves the old cache | skip.supersedes |
| `step_wrap_blind` | `>` for `!=` | write.wrapped_nonce |
| `book_leave_pending` | s154's landing cancel instead | book.pending_converts |
| `book_no_bend` | no bend | book.pending_bends |
| `book_bend_always` | every term bends | book.committed_unchanged |
| `entrance_always_own` | s161's `OwnEntranceRule` applied to C | entrance.host_by_default |
| `entrance_exit_hold_blind` | the exit hold ignored | entrance.exit_hold_keeps_own |
| `quiet_no_exit_hold` | `HoldsFollowQuiet` without the :674 term | quiet_equals_loud |

### LIFE: rows and mutants

`IntentLifeRule(oldRule, sinceEmit, sinceLand, landing, onIntentField, bodyThere)`; P = Pending, On = OnIntent, E = Elsewhere; "-" = not read.

| Row | Inputs | Expected |
|---|---|---|
| r1 | old, 0, -, P, T, F | EndOld |
| r2 | old, 0, -, P, F, F | Keep |
| r3 (R1: the shutdown frame) | act, 16, -, P, T, T | Keep |
| r4 | act, 9999, -, P, F, F | Keep |
| r5 | act, 10000, -, P, F, F | EndCap |
| r6 | act, 0, -, E, F, F | EndElsewhere |
| r7 | act, 1999, 1500, On, T, T | Keep |
| r8 | act, 2000, 1000, On, T, T | EndStands |
| r9 | act, 5000, 4000, On, T, F | Keep |
| r9b | act, 30000, 29000, On, T, F | Keep |
| r10 | act, 500, 100, On, F, F | EndLeft |
| r11 | act, 30000, 29000, On, T, T | EndStands |
| r12 | act, 100, 50, On, F, T | EndLeft |
| r-slowload (T13) | act, 2300, 0, On, T, T | Keep |
| r-slowload2 (T13) | act, 3300, 1000, On, T, T | EndStands |
| r-swirl (S1) | act, 1200, 800, On, F, F | EndLeft (the swirl's first frame: the FieldMap gone, `gMode` still 1) |
| r-order (T2) | act, 0, -, P, T, T | Keep |
| r-order-old (T2) | old, 0, -, P, T, T | EndOld (the R1 hole) |

`BodyThereRule(inScope, haveActor, haveMapActor)` (F14, the `r-bench` rows): b1 (T, T, T) → T; b2 (T, T, F) → F (the player actor before its `fieldMapActor` binds); b3 (F, T, T) → F; b4 (T, F, F) → F.

`IntentLandingStep(landing, active, intentField, loadedField)`: l1 (P, T, D, D) → On; l2 (P, T, D, E) → Elsewhere; l3 (On, T, D, E) → On; l4 (P, F, D, D) → P; l5 (Elsewhere, T, D, D) → Elsewhere.

Live: `live.frame_carries_4`: `BuildStateFrame(true, true)` with `_intentActive` true reads back section 4 (field, nonce) with the landed bit clear while `_intentLanding` is Pending and set once it is OnIntent (S3), and a section 7 whose b3 parses through `HostFlagReads`; it reads back no section 4 after the step ends the intent. This row replaces rev 2's L-WIRE bench row (P11).

| Mutant | Restores | Caught by |
|---|---|---|
| `life_s163_self_clear` | today's rule | r3, r7, r9, r-order |
| `life_no_min` | no 2 s floor | r7 |
| `life_no_body` | no body condition | r9 |
| `life_body_or_min` | "about 2 s OR the new field reports" | r7, r9 |
| `life_min_only` | 2 s from the emit, landing ignored | r4 |
| `life_no_cap` | no 10 s cap | r5 |
| `life_cap_after_landing` | the cap also after landing | r9b |
| `life_elsewhere_ignored` | Elsewhere treated as On | r6 |
| `life_left_ignored` | no "left" clause | r10, r12, r-swirl |
| `life_no_land_tail` | no 1 s since the landing (rev 1) | r-slowload |
| `body_any_actor` | `bodyThere` without the `fieldMapActor` | b2 |
| `landing_any_load_is_intent` | any load counts as the intent field | l2 |
| `landing_rearms` | a later load re-evaluates the landing | l3 |

### PIN: rows and mutants

`PinCaptureRule(spent, here, heldQuality, frameNonce, frameLanded)`; n = the frame's nonce. Rev 3 keeps the ids of the T1 rows (c13-c15) and the R4 rows (c16-c17); c8-c12 and c18, rev 2's off-field and receive-seq rows, are retired with their mechanism (S3).

| Row | Inputs | Expected |
|---|---|---|
| c1 | F, F, None, -1, F | Keep (no section 4) |
| c2 | F, F, None, n, F | Pre |
| c3 (S3) | F, F, None, n, T | Late (the first frame I saw was built after the host's landing) |
| c4 | F, F, Pre, n, F | Keep (a later pre-landing frame: compared, never replaces) |
| c5 | F, F, Pre, n, T | Keep (a post-landing frame never replaces the pin) |
| c6 | F, F, Late, n, F | Keep |
| c7 | F, F, None, n2, F (a new nonce while n is held) | Pre |
| c13 (T1) | T, F, None, n, F (after its consumption) | Keep |
| c14 (T1) | T, F, None, n, T | Keep (spent beats everything) |
| c15 (T1) | T, F, None, n, F (after an epoch reset, section 4 still live) | Keep |
| c16 (R4) | F, T, None, n, F | Here |
| c17 (R4) | F, T, None, n, T | Here (here is judged before the landed bit) |

`IntentSectionBody` / `IntentLandedOf` (S3): `body.round_trip` (`IntentSectionBody(352, 7, false)` → bytes 96, 1, 7, 0, and `IntentLandedOf` false); `landed.flag_set` (…, 7, 1 → T); `landed.s163_body` (the 3-byte body 96, 1, 7 → T: an s163 host reads as landed); `landed.other_bits` (…, 7, 2 → F: only bit 0 counts).

`PinUseRule(leverOld, fromWorld, quality, pinField, ageMs, fld)`:

| Row | Inputs | Expected |
|---|---|---|
| u1 | T, F, Pre, D, 500, D | Latest / lever |
| u2 | F, F, None, -1, -1, D | Latest / none |
| u3 | F, F, Pre, D, 1200, D | Pin |
| u4 | F, F, Pre, D, 2500, D | Pin |
| u5 | F, F, Pre, D, 2501, D | Latest / aged |
| u6 | F, F, Pre, D, 500, E | Latest / other |
| u7 | F, F, Late, D, 500, D | Latest / late |
| u8 | F, F, Pre, D, -1, D | Latest / aged |
| u9 (R3) | F, T, Pre, D, 500, D | Latest / world |
| u10 | T, T, Pre, D, 500, D | Latest / lever (the lever first) |

`PinConsumed(quality, pinField, fld)`: k1 (Pre, D, D) → T; k2 (Pre, D, E) → F (the bounce reload keeps the pin); k3 (Late, D, D) → T; k4 (None, -1, D) → F.

`PinDropOnNew(heldField, targeted, newField)` (T5): d1 (D, T, E) → F (the chain: a follow to D is pending when E's nonce arrives; both kept); d2 (D, F, E) → T; d3 (D, T, D) → T (superseded by a newer nonce for the same field); d4 (D, F, D) → T.

`PinTargeted(pinField, pending, committed, warpedTo)` (T5): t1 (D, D, -1, -1) → T; t2 (D, -1, D, -1) → T; t3 (D, -1, -1, D) → T; t4 (D, E, E, E) → F; t5 (-1, -1, -1, -1) → F.

`PinAgeRule(landSeen, sinceLandSeen, sinceCapture)` (T6; `landSeen` is exact since S3): a1 (T, 1200, 3000) → 1200; a2 (F, -, 2000) → 0; a3 (F, -, 10000) → 10000; a4 (T, 2600, 2650) → 2600.

`LandingFrames` (R1): f1 Pin → story = pin, party = latest, dress = latest; f2 Latest → story = party = dress = latest.

Sequence: `seq.landing_ages_the_pin`: a Pre capture at t0; a later pre-landing frame at t0+200 (Keep; `pre_frames` +1, diff 0); the first landed frame at t0+400 (Keep; `landSeen` at t0+400); the guest's landing at t0+1600 → age 1200 → Pin; the same with the guest's landing at t0+3000 → age 2600 → Latest / aged.

Live: `live.pin_applies_verbatim`: `ApplyStoryTo(the pinned real frame, scratch)` equals its section 0 outside the mask, and `StoryDiff` of a frame against itself is 0. `live.pin_split_applies` (V1): `ApplyStorySplitTo(pin, latest, scratch)` on two real frames whose section 0 differs at the marker byte and whose party slot 1 differs (the second built under the `SlotSource` seam): the scratch array equals the pin's section 0 outside the mask, and `NetSyncParty.Slots` equal the latest frame's party; then `Clear()`.

| Mutant | Restores | Caught by |
|---|---|---|
| `pin_latest_always` | today | u3 |
| `pin_last_frame` | the newest frame of a nonce wins | c4, c5 |
| `pin_landed_blind` | the landed bit ignored: every first frame is kept (rev 2's arrival guess, at its worst) | c3 |
| `pin_unknown_is_pre` | an s163 host's 3-byte section reads as built before the landing | landed.s163_body |
| `pin_any_bit_lands` | any flags bit reads as landed | landed.other_bits |
| `pin_any_field` | the field ignored | u6 |
| `pin_never_ages` | the age ignored | u5 |
| `pin_late_used` | Late treated as Pre | u7 |
| `pin_consumed_anywhere` | consumed at any landing | k2 |
| `dress_follows_story` | the dress from the pinned frame | f1 |
| `party_follows_story` | the party wraps from the pinned frame (rev 1) | f1 |
| `pin_recapture_after_consume` | no spent-nonce memory (rev 1) | c13 |
| `pin_single_slot` | one slot: a new nonce always replaces | d1 |
| `pin_target_pending_only` | only a pending follow targets a field | t2, t3 |
| `pin_age_from_capture` | the age from the capture (rev 1) | a1, a2, seq.landing_ages_the_pin |
| `pin_blind_never_ages` | no backstop when the landing is never seen | a3 |
| `pin_kept_when_here` | a pin for the field I stand on | c16 |
| `pin_used_from_world` | the pin used at a world-rejoin landing | u9 |
| `pin_here_after_landed` | `here` judged after the landed bit | c17 |

### D+E: rows and mutants

Ids: my field 351, another 350; frames 12 and 24.

`ViewRule(readOk, mode, curMin, targetMin, ticksLeft)`:

| Row | Inputs | Expected |
|---|---|---|
| unreadable | F, -, -, -, - | Unknown |
| add_white_is_not_black | T, Add, 255, 255, 0 | Visible |
| add_heading_white | T, Add, 0, 255, 10 | Visible |
| sub_black_idle | T, Sub, 255, 255, 0 | Black |
| sub_black_at_floor | T, Sub, 248, 255, 3 | Black |
| sub_below_floor_heading | T, Sub, 247, 255, 1 | Heading |
| sub_heading_from_visible | T, Sub, 0, 255, 24 | Heading |
| sub_fade_in_starting_reads_black | T, Sub, 255, 0, 16 | Black |
| sub_dim_idle | T, Sub, 120, 255, 0 | Visible |
| sub_heading_to_dim | T, Sub, 0, 200, 10 | Visible |
| sub_visible_idle | T, Sub, 0, 0, 0 | Visible |

`BacklogRule(readOk, onOpen, ahead, keyHere, lineOpen)`: `unreadable` (F, …) → Unknown; `none` (T, 0, 0, F, F) → None; `line` (T, 1, 0, F, F) → Line; `ahead` (T, 0, 1, F, F) → Ahead; `key` (T, 0, 0, T, F) → Key; `open` (T, 0, 0, F, T) → Open; cascade: `line_over_ahead` (T, 1, 1, T, T) → Line; `ahead_over_key` (T, 0, 1, T, T) → Ahead; `key_over_open` (T, 0, 0, T, T) → Key; `unknown_over_all` (F, 1, 1, T, T) → Unknown.

`CountBacklog` over synthetic facts (myField 351, now 10000, engaged unless stated):
- counted: `event_on_open_line` (event 351/3/129 seen at 9000, a live Locked window 351/3/129 → onOpen 1); `tried_event_counts` (the same event marked Tried → onOpen 1); `ahead_young` (event 351/3/130 seen at 8000, no window → ahead 1); `key_for_my_field` (keyHere → Key through `BacklogRule`); `locked_line_open` (no event, a live Locked !Inh window on 351 → lineOpen); `untracked_live_line_counts` (an untracked live lockable !Inh line → lineOpen).
- ignored: `event_for_warp_field` (event for 350 → 0, 0); `event_on_inh_line` (the event's window is Inh → 0, 0); `event_on_local_line` (Local → 0, 0); `ahead_aged` (seen at 7000: now − first = 3000 → ahead 0); `key_for_other_field` (no Key); `orphaned_line` (a live Orphaned window → lineOpen F); `inh_line` (a live Locked Inh → F); `lock_off` (engaged F → F).

`PathRule(kick, lever, ownWarp, view, backlog)`: `kick` (T, Act, F, Visible, None) → Kick; `kick_over_nogate` (T, NoGate, …) → Kick; `lever_old` (F, Old, …) → Old; `own_warp_old` (F, Act, T, …) → Old; `view_unknown_old` (…, Unknown, None) → Old; `backlog_unknown_old` (…, Visible, Unknown) → Old; `backlog_unknown_even_nogate` (F, NoGate, F, Visible, Unknown) → Old; `backlog_line`, `backlog_ahead`, `backlog_key`, `backlog_open` (F, Act, F, Visible, that term) → Backlog; `nogate_ignores_backlog` (F, NoGate, F, Visible, Line) → Fast; `norecheck_keeps_start_gate` (F, NoRecheck, F, Visible, Line) → Backlog; `nohurry_keeps_gate` (F, NoHurry, F, Visible, Line) → Backlog; `fast_visible`, `fast_heading`, `fast_black` (F, Act, F, that view, None) → Fast.

`ActionRule(path, view, ticksLeft, lever)` → action / frames: `old_wipes_24` (Old, Black) → Wipe/24; `kick_wipes_24` → Wipe/24; `fast_black_joins` (Fast, Black, 0) → Join/12; `fast_heading_12_joins` (Fast, Heading, 12) → Join/12; `fast_heading_13_hurries` (Fast, Heading, 13) → Hurry/12; `fast_visible_fades_12` (Fast, Visible) → Fade/12; `backlog_black_joins` → Join/24; `backlog_heading_24_joins` → Join/24; `backlog_heading_25_hurries` → Hurry/24; `backlog_visible_fades_24` → Fade/24; `nohurry_heading_60_joins` (Fast, Heading, 60, NoHurry) → Join/12; `long_visible_fades_24` (Fast, Visible, -, Long) → Fade/24.

`GraceRule`: `join_3` (Join → 3), `fade_0` (Fade → 0), `hurry_0` (Hurry → 0).

`BlackTicksRule`: `first_black_arms_0` (black, unarmed, keyTick 100 → armed, since 100, 0); `black_counts` (armed since 100, keyTick 103 → 3); `leaving_black_disarms` (not black → unarmed, -1); `rearm_at_0` (black again at 110 → since 110, 0); `keytick_wrap` (since Int32.MaxValue − 1, keyTick Int32.MinValue + 1 → 3).

`DueRule(path, timerOut, view, blackTicks, grace, backlogNow, primed, lever)`:

| Row | Inputs | Expected |
|---|---|---|
| old_waits_on_black | Old, F, Black, 5, 0, None, F, Act | Wait |
| old_timer | Old, T, Visible, -1, 0, None, F, Act | Timer |
| kick_timer | Kick, T, Black, 5, 0, None, F, Act | Timer |
| backlog_black_waits | Backlog, F, Black, 5, 3, Line, F, Act | Wait |
| backlog_timer | Backlog, T, Black, 5, 3, Line, F, Act | Timer |
| black_primes_first (T9) | Fast, F, Black, 0, 0, None, F, Act | Prime (our own fade: no grace, but one dialogue pass) |
| fast_black_in_grace | Fast, F, Black, 2, 3, None, F, Act | Wait |
| fast_black_grace_spent | Fast, F, Black, 3, 3, None, F, Act | Prime |
| prime_then_black (T9) | Fast, F, Black, 3, 3, None, T, Act | Black |
| fast_black_in_grace_at_timer | Fast, T, Black, 1, 3, None, F, Act | Fallback |
| fast_black_spent_and_timer_is_black | Fast, T, Black, 3, 3, None, F, Act | Black (no prime at the timer) |
| fast_heading_waits | Fast, F, Heading, -1, 0, None, F, Act | Wait |
| fast_fallback_heading | Fast, T, Heading, -1, 0, None, F, Act | Fallback |
| fast_fallback_visible | Fast, T, Visible, -1, 0, None, F, Act | Fallback |
| recheck_holds | Fast, F, Black, 3, 3, Line, T, Act | Wait (a hold beats a prime) |
| recheck_at_timer | Fast, T, Black, 3, 3, Line, F, Act | Recheck |
| recheck_unknown_holds | Fast, F, Black, 3, 3, Unknown, F, Act | Wait |
| nogate_ignores_recheck | Fast, F, Black, 3, 3, Line, T, NoGate | Black |
| norecheck_ignores_recheck | Fast, F, Black, 3, 3, Line, T, NoRecheck | Black |
| never_past_the_timer | every path, view, backlog, primed and lever with timerOut T | never Wait, never Prime (one sweep row) |

`ReassertRule(path, reasserted, timerOut, view)`: `fast_visible_once` (Fast, F, F, Visible) → T; `backlog_visible_once` (Backlog, F, F, Visible) → T; `spent` (Fast, T, F, Visible) → F; `after_timer` (Fast, F, T, Visible) → F; `old_never` (Old, F, F, Visible) → F; `kick_never` (Kick, …) → F; `heading_no` (Fast, F, F, Heading) → F; `black_no` (Fast, F, F, Black) → F.

Live, counted once: `slot_reads` (`NetSyncReadFade` returns true), `today_constants` (OldFrames == `FollowFadeFrames`, OldWaitS == `FollowFadeWait`).

| Mutant | Restores | Caught by |
|---|---|---|
| `view_add_white_black` | an Add white reads black | add_white_is_not_black |
| `view_exact_255` | black only at 255 | sub_black_at_floor |
| `view_target_blind` | heading ignores the target | sub_heading_to_dim |
| `view_idle_heading` | heading with no ticks left | sub_dim_idle |
| `view_fade_in_not_black` | a fade-in from black reads heading | sub_fade_in_starting_reads_black |
| `view_unknown_visible` | an unreadable slot reads visible | unreadable |
| `backlog_line_only` | the task's literal first term | ahead |
| `backlog_no_ahead` | no Ahead term | ahead |
| `backlog_no_key` | no Key term | key |
| `backlog_no_open` | no Open term | open |
| `backlog_unknown_none` | unreadable reads None | unreadable |
| `backlog_order_swapped` | Ahead before Line | line_over_ahead |
| `count_any_field` | events for other fields count | event_for_warp_field |
| `count_inh` | Inh windows count | event_on_inh_line |
| `count_local` | Local windows count | event_on_local_line |
| `count_no_age_cap` | no 3000 ms cap | ahead_aged |
| `count_orphan` | an Orphaned line counts as open | orphaned_line |
| `count_lock_blind` | the lock state ignored | lock_off |
| `path_no_gate` | the refuted D | backlog_line |
| `path_kick_fast` | the kick on the fast path | kick |
| `path_fault_fast` | a fault takes the fast path | view_unknown_old, backlog_unknown_old |
| `path_own_warp_blind` | my own warp ignored | own_warp_old |
| `path_lever_blind` | the lever ignored | lever_old |
| `act_always_wipe` | the flash | fast_visible_fades_12 |
| `act_reinit_heading` | no join | fast_heading_12_joins |
| `act_never_hurry` | the literal "never re-init" | fast_heading_13_hurries |
| `act_black_wipes` | a black screen wipes | fast_black_joins |
| `act_fast_24` | E not taken | fast_visible_fades_12 |
| `act_backlog_12` | E with a backlog | backlog_visible_fades_24 |
| `due_wall_only` | D not taken | prime_then_black |
| `due_backlog_commits_on_black` | the refuted early commit | backlog_black_waits |
| `due_no_recheck` | no recheck | recheck_holds |
| `due_no_grace` | no grace | fast_black_in_grace |
| `due_no_fallback` | the s42 strand | fast_fallback_heading, never_past_the_timer |
| `due_recheck_past_timer` | G's hold, not round 1 | recheck_at_timer |
| `due_unknown_backlog_free` | an unreadable backlog does not hold | recheck_unknown_holds |
| `due_no_prime` | a Black verdict commits in the Update that first judges it (rev 2) | black_primes_first, fast_black_grace_spent |
| `due_prime_at_timer` | the prime also waits at the timer | fast_black_spent_and_timer_is_black, never_past_the_timer |
| `grace_on_own_fade` | a grace after our own fade | fade_0 |
| `reassert_never` | no reassert | fast_visible_once |
| `reassert_every_tick` | reassert on every tick | spent |
| `reassert_old_path` | reassert on the Old path | old_never |
| `blackticks_no_disarm` | leaving black keeps counting | leaving_black_disarms |

---

## Kit side

- **`tools/harness/battlewire.py`** gains a section `[ff9mapkit netsync s164] FIELD-SWAP TIMING`:
  - every constant and name table;
  - twins for every pure rule: A's 13 (`swap_ticks_to_ms` ... `swap_oob_verdict`), B's `swap_orphan_settled`, `swap_host_holds`, `swap_ctl_hold_kind`, `swap_hold_end_why`, `swap_orphan_since` and `swap_keep_read`, C's `own_field_pass_rule`, `own_jump_verdict_rule`, `intent_cache_step`, `intent_cache_verdict`, `own_pass_book` and `own_pass_keeps_own`, LIFE's `intent_landing_step`, `intent_life_rule` and `body_there_rule`, PIN's `intent_section_body`, `intent_landed_of`, `pin_capture_rule`, `pin_targeted`, `pin_drop_on_new`, `pin_age_rule`, `pin_use_rule`, `pin_consumed` and `landing_frames` (three outputs), and D+E's nine;
  - `_i64(x)` and `_i32(x)`, two's-complement wrap helpers. Every twin whose engine form is fixed-width uses them: `swap_ticks_to_ms` and its mutants, `BlackTicksRule`, and B's tick scenarios across the Int32 wrap. Python's integers do not overflow, so without them the `ms_naive` twin equals `swap_ticks_to_ms` on every row (P9);
  - every log builder, including the refusal line with its `[NetSync] own Field(` prefix (R9);
  - `S163_FORMS`, the s163 regex of every line that gains a stamp, including `StartSceneAt`'s "host scene: ended (nonce N) -- a new talk started" (:7038) beside its "rose" line (I10);
  - the lever ops, the refusal and usage strings, and the proof regex.
- **`tools/harness/channel.py`:**
  - `qpc_ms()`: kernel32 `QueryPerformanceCounter` / `QueryPerformanceFrequency` through ctypes, through the same split arithmetic as `TicksToMs`. It returns None off Windows;
  - the State accessor `coop_field_swap` (present when `netsync.swap.clock` is);
  - `swap_block`, `swap_last`, `swap_seen`, `swap_intent`, `swap_pin`, `swap_clock`.
- **`tools/harness/fakegame.py`:**
  - caps registration: `NETSYNC_BATTLE_CAPS["swap"] = ("s164", ("swap",))`, `NETSYNC_S164_CAPS`, `swap` in the verb order, `NETSYNC_TOP_CAP_KEYS["swap"]`, and the sentinels in catch-literal order;
  - the ops, the refusals, the lever lines, the release line and the proof line.
  - **A clock seam (F5):** the stand-in publishes `clock.now_ms` from `channel.qpc_ms()` with `src` `qpc` when that function answers, and from `int(rt*1000)` with `src` `stopwatch` when it does not. K-CLOCK is therefore green offline on Windows and a SKIP with its reason on Linux CI.
  - **What it models:**
    - the block, with `hz` and `hires` matching the source;
    - the levers and the release;
    - `swap intent` through `_field_follow_fire` / `_field_follow_land` (`fakegame.py:8034-8062`), with the record (seen, follow, due, commit, land via follow, closed by window), `swap delay` between `due_t` and `commit_t`, and stamps on those lines;
    - B's orphan model on the twins (`fakegame.py:13482-13490`), extended with `swap_orphan_since` and `swap_keep_read`, and the bench host emitting 0 under `hostctl off` (:13546);
    - its `host_intent` already persists until replaced (:7959-7963).
  - **What it cannot model:** the slot and host probes, a bounce (it has no MAPJUMP), a pin (it has no story frames), `lifebench`, or the fade slot. Those keys stay at their sentinels, so the stand-in is run only on the legs it models (below).
- **`tools/harness/session.py`:**
  - `swap` after `speed` in `NETSYNC_SUBVERBS` (:8415) and `NETSYNC_AUTHORITY_SUBVERBS` (:8424);
  - `NETSYNC_SWAP_SUBVERBS = {"swap": ("coop_field_swap", "netsync.swap", "s164", "the s164 field-swap levers")}` next to the speed table (:8585), and in the `ng = ng or ...` chain (:8986);
  - `NETSYNC_SWAP_OPS`, the role sets, and the refusal and usage strings, verbatim;
  - `_swap_refusal(args, selftest_role)` as a pre-step check, modelled on `_speed_refusal` (:9420).
  - The driver reads the target game's `netsync.role` before sending a role-bound op, and checks each duo Session separately.
- **`ff9mapkit/tests/test_harness_netsync.py`:**
  - every SelfTest row evaluated against the twins, and every mutant failing at least one row (the mutant tables above are the oracle); one test asserts the `ms_naive` twin differs from `swap_ticks_to_ms` at `tsc_40_days` (P9);
  - the stand-in's block, levers, refusals, release and proof line;
  - LV-4: the stand-in at `caps_through("speed")` refuses `netsync swap ...` before any step;
  - the B twin's KeyScript flip;
  - about 20 netsync tail-order asserts gain `swap` (the s163 sites: :15518, :15938, :25711-25713, :26304-26306, :26437, :26577-26579 and others);
  - the sub-verb regex at :416 gains `\|swap`.
- **New: `ff9mapkit/tests/test_coop_field_swap_timing_bench.py`** (F5), in the shape of `test_coop_speed_mirror_bench.py` (every scenario-touching test in a child process):
  - synthetic-sample fixtures in the engine's log and state shapes for every solo and duo judge, built by battlewire's twins, so each judge can go red on each of its parts;
  - each solo and duo calibration word reds exactly its registered rows offline, each with its marker, and every other row stays green;
  - the duo refuses an unknown `COOP_CALIBRATE` word at load, before `duo.py` boots the pair; so does the solo bench;
  - K-CLOCK's three outcomes: green on the seam, VOID-making on `src stopwatch`, SKIP with a reason when `qpc_ms()` is None;
  - DA-LANE reads a transition with `arrived_t == -1` as UNREACHED for that transition, and a leg with no reached transition as red (P8);
  - the solo run on the stand-in uses `COOP_LEGS=KAB`, the legs it models, and is green there. Legs C, P, L and F are not run on the stand-in: on an engine their sentinel keys after an acked op are red, so a stand-in run of them proves nothing (P8);
  - source tests, each a literal the build must keep:
    - the engine still carries `_glHostHoldsInput = v.HostHoldsInput;` next to the new `NetSyncSwap.HostHoldsNow` line (R8);
    - the refusal literal starts `[NetSync] own Field(` (R9), and its builder is called only from `NoteOwnJump` (I2);
    - the :929 hunk reads `NetSyncState.ApplyStorySplit(story, party)` (V1);
    - the selftest branch calls `NetSyncSwap.GuestTick(fld, -1)` before its `if (!inScope)` return (V3);
    - `NetSyncSwap.HarnessRelease` calls `NetSyncParty.Clear()` under `_pinBenchMirror` (G2);
    - the three call sites the solo legs depend on exist: `NetSyncFollowFade.Ended(` in `ServiceFollowWarp`, `BenchPinLanding()` in `ApplyStoryImpl`, and `NoteIntentLanding(fldMapNo)` in `ApplyStoryBeforeEvents` (P8).
- **Evidence scripts:** `studies/field-coop/swap-timing/final.py:26`, `conv.py:20` and `drift.py:15` get the tolerant stamp tail.
- **`coop_follow_race_duo.py`:**
  - the tolerant tail at :208;
  - FE1, FE2 and FD send `netsync swap fade old` to the guest when the engine publishes `netsync.swap`, because those rows model a commit 0.9 game-seconds after the start;
  - FS stays valid through D's own-warp term.
- **Rev 4, the arrival guard:** its battlewire twins, the stand-in's harness half, the driver's two ops and the kit tests are listed in `ARRIVAL-GUARD-S164.md` ("Kit and hunks"), with the build's departures in its "Build log".

---

## Benches

**Reach rules (P4, P8).** Three kinds of row, each with its own meaning of "not reached":
- **Deterministic rows** (every solo row, and the duo's leg-level rows). A row whose op was acked but whose key is still at its sentinel afterwards is red, "the engine never ran X". This is the house `Ledger.unreached`, which records a failed check (`_coop_battle.py:216-219`). A setup clause (leg C's first line, C-PEND's pending sample) that misses marks the run VOID with its reason; it never turns a red into UNREACHED.
- **Probabilistic duo rows** (DA-LANE per transition, DA-GUARD per landing, DF-FLASH, DF-GRACE, DF-PACE, DP-HALT, DP-PARTY, DC-B(b), DP-MARK and DP-DEFER; from fix round 3, DP-DEFER needs the record seen while paused). Each records its reach count, is judged only on reached runs or transitions, and is never red merely for being UNREACHED, except where a floor is stated: DA-LANE needs at least one reached transition per leg (the follow race's "none reached = red", `coop_follow_race_duo.py:717-718`), DA-GUARD at least one reached landing (UNREACHED under the `life` word, its declared unreach), and DA-ARRIVE's ARRIVE leg must reach its exposure. DA-ARRIVE's watches (CAL2, DESK) are reported apart, never judged (rev 4).
- **Calibrations.** A row that a word must red, but which reads UNREACHED, fails that calibration's exactness check; it is never counted as "not green". A calibration whose predicted reds all read UNREACHED is VOID, never a pass.

### Solo: `studies/test-harness/scenarios/coop_field_swap_timing.py`

One game on the selftest role (`netsync selftest 1`, `bench 1`, `stateevery 1`). `COOP_LEGS` picks legs from K, A, B, C, P, L, F and G; leg K always runs. Leg G (rev 4) is the arrival guard's, engine-only, with its rows in `ARRIVAL-GUARD-S164.md` ("Solo"). HOME is the bench field and AWAY is 30602, which is registered and walkable. A harness `warp` never reaches `RedirectGuestFieldJump`, because it goes through `SetNextMap` (`Ff9mkDebugMenu.cs:2453-2455`). So own-jump rows use a real script `Field()`.

**Leg C's setup, pre-registered (F8).** `warp(351, entrance=15, scenario=2600)`, `swap fade old` (T8), `lock 1`, the bench pages each line as it opens.
- Entrance 15 with a scenario below 2990 other than 2840 builds 351's desk scene: the party and the innkeeper pair are created (`test2_94.txt:60-76`), and `Zidane_Init`'s case 15 sets `VAR_GlobInt16_48 = 1` (`:3230-3234`), which starts the scene at its first line, win 3 text 129 (`:3304-3317`). The fourth two-PC session ran 359 and this desk scene at 2600 and, after a reload of 359, at 0 (`twopc-s163-20261029` host log lines 50 and 56); the s158 session ran them at 2505 (its host log lines 67 and 77).
- **The exit (P6).** The scene's chain is `VAR_GlobInt16_48` 1 → 6 → 8 → 9 → 11 → 12 → 13. At 13, `Zidane_Loop` case +12 opens win 3 text 139, waits for it (`WaitWindow(3)`), runs Dagger's script 19 and sets 48 = 23 (`test2_94.txt:3372-3386`). `Dagger_Loop` case 23 then runs `Wait(100)`, `Wait(30)`, `FadeFilter(6,30)` (a Sub fade to black, `EventEngine.DoEventCode.cs:632-647`), `Wait(30)`, the gil and global writes, entrance 3 and `Field(352)` (`test2_94.txt:3850-3879`). That `Field(352)` is the own jump. Text 140 does not gate it, and the slot reads black only about 1-2 ticks before it. The rest exit through `Zidane_Loop` case +16 (entrance 5, :3461-3539) needs 48 = 17, which only the scenario-2840 innkeeper (entry 6) writes (:1093-1110), so it does not run here. 352's entrance 3 builds the party and opens win 4 text 142 (`test2_95.txt:64-69, 1430-1435, 1649-1654`). The s163 host log agrees: texts 129-140 with none of entry 6's, then intent 352, then text 142 (`twopc-s163-20261029` desktop-host lines 69-87).
- The leg warps straight to 351, not through 359: on the selftest role `LastHostField` is -1 (:2039), so 359's own `Field(351)` would bounce.
- REACHED only when "win 3 text 129 opened locked" logs within 30 s of the warp's landing; otherwise the leg is VOID.
- A dry run under `own old` measures Δ from text 139's close to the own jump, from state, not log stamps (P10): the first sample whose `netsync.windows` no longer lists (win 3, text 139), by its `clock.now_ms`, to `last.own_t`. About 161 ticks plus Dagger's script 19 are expected (INFER).
- **Why `fade old` (P6).** C-PEND aims the intent at the own jump − 0.45 s, about 13 ticks before `Field(352)`. Under D+E the copy's `FadeFilter(6,30)` then has about 12-13 ticks left, right on ActionRule's Join/Hurry split (`ticksLeft <= 12` joins, so the copy's own jump wins by Pending; 13 hurries to black in 12 ticks and the follow commits first). Pending versus Committed would be a coin flip. Under `fade old` the follow stays pending for 0.9 s across the own jump, which is the case C's Pending term exists for.

| Row | Leg and setup | Green | Calibration word |
|---|---|---|---|
| K-PROOF | any | The proof line logged; `swap.selftest` = `ok`; the dialogue selftest still OK | none (gate; falsified by any row or mutant) |
| K-CLOCK | any | A load-time precondition, never a red row: at least 20 samples with 0 ≤ kit `qpc_ms()` − `clock.now_ms` ≤ the sample's age + 100 ms, `clock.src` `qpc`, `hz` and `hires` published. A failure is reported with its reason and marks the instrument unfit for the duo (DK-CLOCK). Off Windows (`qpc_ms()` None): SKIP with the reason | none |
| K-LEVER | any | Each op's ack line and its read-back in `levers`; `act` and `clear` restore | none |
| K-RELEASE | any | Every lever set, then `reset`: one release line and everything back; a second `reset` logs nothing. Then the re-arm (`netsync selftest 1`, `bench 1`, `stateevery 1`) and one `swap intent 30602`: `last.commit_t - last.due_t` ≤ 1 frame (no delay leaked) | none |
| K-REFUSE | any | `swap delay 5000` and `swap orphan maybe` get the usage line; `swap intent 30602` before `bench 1` gets the bench refusal; `swap orphan old` after `netsync selftest 0` gets "co-op is off" | none |
| A-FOLLOW | A: `swap intent 30602` | One record (id +1): open_by `seen`, seen_t ≤ follow_t ≤ due_t ≤ commit_t ≤ land_t, follow_via `intent`, land_via `follow`, land_field 30602, closed by `line` or `window` | none (gate; falsified by the record rules) |
| A-STAMP | A | Each edge line's stamp exactly equals the record's `t` | `stamps` |
| A-DELAY | A: legs `delay 0` and `delay 300` | Within each follow, `commit_t - due_t` = the leg's delay ± 1 measured frame; `last.delay_ms` 300 on leg 2. The difference between the legs' `commit_t - follow_t` is reported, not judged (F6) | `delay` (leg 2 sends 0 but still expects +300) |
| A-WORD | A | Every stamped line, with its stamp and tail removed, matches its `S163_FORMS` regex | none (gate) |
| B-HOST | B: dialogue bench field with the keeper (`coop_dialogue_authority.py`'s `_open_by_relay`), `lock 1`; a fresh line opened by relay under `hostscene 1`, then `swap hostctl off`, then `hostscene 0` | Within 2 frames: `host_flags & 0x03 == 0` with b3 set, `orphan.host_holds` true, `levers.hostctl_off` true, `host_settled_ms ≥ 0` | none |
| B-HOLD | B | Held for at least OrphanGraceMs + AutoReadMs + 2 s: every sample `locked`; `host_settled_ms ≥ 2000`; `orphan_closes` Δ0; `holds` +1; one hold line; no "is not on the host's screen" line | `orphan` |
| B-RELEASE | B: `swap hostctl on` | `orphaned` within 0.5 s; the end line "(the host's control is back)" with N within ±0.3 s of the sampled hold; `last_end` `control`; the auto-close AutoReadMs later; `orphan_closes` +1 | `orphan` |
| B-BLIP | B: a fresh line by relay (as B-HOST), then on, then off 1.0 s later | Orphaned, then locked; one relock line; `relocks` +1; no auto-close through AutoReadMs + 1 s | `orphan` |
| B-SCENE | B: B-BLIP's held line, then `hostscene 1` | The end line "(the host is busy (a scene or a line))"; the bench host's ADV closes the line "closed (host seq" | `orphan` |
| B-BLIP2 | B: a fresh single-page line by relay; on (the line orphans at t0); then off for 0.5 s at t0 + 1.0, 2.5, 4.0 and 5.5 s; then on (V4, P2) | Exactly one relock line before the close (`relocks` +1); the auto-close on the first orphaned sample at or after t0 + AutoReadMs, by t0 + AutoReadMs + 0.3 s; `orphan_closes` +1; nothing more counted after it. The rejected restart rule (`relock_restarts_read`) shows as `relocks` ≥ 2 or a close later than t0 + AutoReadMs + 0.8 s | `orphan` (`relocks` +0: the old rule never relocks a plain line) |
| B-CTLON | B: a fresh line by relay, held under `hostscene 1` until RelayOwnMs (3 s) has lapsed since the relayed start, then `hostctl on`, `hostscene 0` | Orphans OrphanGraceMs after settle and auto-closes; `holds` +0 | none (regression) |
| C-BOUNCE | C, no injection | The own jump bounces: `own_verdict` bounce, `own_why` not-host, `counts.bounces` +1, `reloads` +1, a landing on 351 via `bounce` with the record still open; `own.passes` +0 | none (gate; falsified by `via.bounce` / `join.land_source_reload`) |
| C-CACHE | C: `swap cache 352` at text 139's close + Δ − 1.0 s | The cache write line, then `own Field(352) passes on field 351 -- the host's announced field (cache)`; `by.cache` +1; one `Map: 352`; `bounces` +0; then `intent cache: field 352 cleared -- I left field 351 (now 352) (the cached field)` (T7) and no "field 352 loaded" clear (the backstop firing first means `GuestTick` ran too late, V3) | `own`, `nocache` |
| C-PEND | C: `swap intent 352` aimed at the own jump − 0.45 s (inside the old path's 0.9 s pending window). REACHED when `last.own_t` is set with `own_dest` 352 from field 351 and the last state sample before `own_t` reads `session.follow.pending` = 352 (`HarnessAgent.cs:4638`), whatever the verdict (P4); otherwise VOID | `(pending)`; `converted` +1; one load; `fade.ends.own` +1; none of the s154 "cancelled", "dropped" or "never landed" lines | `own` (the marker: `own_verdict` bounce and `own_why` not-host with pending 352, the L-OWN "bounced to a reload of 351" line and no `(pending)` line) |
| C-AGE | C: the cache injected ≥ 3 s before the jump | The "aged 2000 ms" clear, then a bounce | none (control) |
| C-SRC | C: a cache on another field, then a warp to 351 | The Left clear for that field, then a bounce | none (control) |
| P-PIN | P: `flag 8720 0`, `watch 8720`, `swap pinbench 30602 8720` | Flag 8720 = 0 after the landing; "stages intent N's frame for its story ... (age A ms; the latest differs at 1 story bytes)"; `pin.last_use` `pin`; `last.story` `pin` | `pin` |
| P-AGED | P: `age 3000` | Flag = 1; why `aged` | none (guard) |
| P-OTHER | P: `to <E>` | Flag = 1; the held entry still names 30602; `pin.other` +1 | none (guard) |
| P-LATE | P: `landed` | Flag = 1; why `late`; `pin.last_use_quality` `late` (S3) | none (guard) |
| P-PARTY | P: `swap pinbench 30602 8720 party 1 <c>`, where `<c>` differs from slot 1's current CharacterId; then the leg's closing `swap clear` | Flag 8720 = 0 (the story from the pin) AND `netsync.dress.mirror_party[1]` = `<c>` (the party from the latest frame), sampled before the `swap clear`; `pin.last_party` `latest` (R1); after the `swap clear`, `netsync.dress.mirror_party` reads null and the clear line names the pin bench's party mirror (G2) | `pin` (the flag half reds; the party half and the clear stay green under both rules) |
| L-LAND | L: `swap lifebench 30602` | The hook's evidence that outlives the intent's end: the "I landed" line (printed at the hook under either lever) and `intent.landed_ms` >= 0 in some sample. The `intent.landing` `on_intent` sample with the intent still active is reported, not required: under `swap life old` s163's rule can end the intent in the hook's own frame. Under `life`, last_end `old` with no line and `landed_ms` -1 (s163's rule ended the intent before the hook: the R1 hole) reads VOID, never red | none |
| L-STANDS | L | `last_end` `stands`; `body_ms` >= 0; harness_body_ms read; `body_ms` <= harness_body_ms + 100; `last_life_ms` − max(2000, `landed_ms` + 1000, `body_ms`) in [−16, 400] (guard-round live fix, run s164g-act gap −15: the life step decides on, and stamps `body_ms` from, `NetSyncClient._intentEmitTick`, while `last_life_ms` reads `NetSyncSwap._ipEmitTick`, set later in the same emit -- two TickCount reads one ~15.6 ms step apart when they straddle a step). harness_body_ms is the earliest leg-L sample with `field.id` 30602, `intent.landed_ms` >= 0 and `player.uid` not null, as `netsync.swap.clock.now_ms` − `intent.emit_t` (the harness's own `GetControlChar` read, independent of the step that stamps `body_ms` and ends the intent) | `life` |
| F-FAST | F: `swap intent 30602` | `fade.last` = fast / fade / 12; by `black`; `fade.last.primed` true (the commit came one dialogue pass after the black was first judged, S2); ticks 12-14; ms < 600 | `fade`, `long` |
| F-3X | F: `speedmode 1` | ms < 250; ticks 12-17 (the prime's one frame is up to 3 ticks at 3x; a 2-tick batch can push the first black read to 14). The same window as duo DF-3X | `fade`, `long` |
| F-BLACK | F: `swap blackout 1`, wait 3 frames, then intent | view_start `black`, action `join`, by `black`, `black_ticks ≥ 3`, ms < 250; no sample from start to due with `cur_now` < 248 | `fade` (wipe; `cur_now` dips under 128) |
| F-JOIN | F: `blackout 8`, then intent, both in one request (the agent's queue runs them `Block(2)` frames apart, so the follow starts on the heading fade). A follow that still starts black (view_start `black`) is a setup miss: VOID, never red | `heading`, left ≤ 8, `join`; due within left + 3 + 2 ticks (the grace, then the prime) | `fade` |
| F-HURRY | F: `blackout 60`, then intent | `hurry` with frames 12; due by `black` within 14 ticks; `cur_now` never drops | `fade`, `long`, `nohurry` |
| F-OPEN | F: `lock 1`; talk to the talk-relay bench NPC (the line opens locked); intent | backlog_start `open`, path `backlog`, by `timer`, ms ≥ 900 − the measured start frame (a harness-started follow's start-frame debit) | `fade`, `nogate` |
| F-AHEAD | F: `lock 1`, `netsync unmatched`, intent within 1 s | backlog_start `ahead`; by `timer` | `fade`, `nogate` |
| F-AGED | F: as F-AHEAD, but wait 3.2 s first | path `fast` (the age cap) | `fade` |
| F-RECHECK | F: `lock 1` (`netsync unmatched` needs the bench dialogue lock, `NetSyncClient.cs:10963-10965`), intent, then `netsync unmatched` in the same batch | path `fast`, `held`, by `recheck`, ms ≥ 900 − the measured start frame (a harness-started follow's start-frame debit) | `fade`, `nogate`, `norecheck` |
| F-REASSERT | F: intent, then `swap blackout off` 3 ticks into the fade (F12) | One reassert line; `fade.reasserts` +1; by `black` | `fade`. Not run under `long` (a 24-tick re-fade lands on the 0.9 s timer: a coin flip) |
| F-KEY | F: `lock 1`, a bench host key for my field (`netsync host key ...`, `HarnessAgent.cs:1760-1773`), intent before the copy plays it (F12) | backlog_start `key`, path `backlog`, by `timer`, ms ≥ 900 − the measured start frame (a harness-started follow's start-frame debit) | `fade`, `nogate` |

**Amendments after the first live run (run 20261030-024220).** No engine defect was found; these correct rows whose rev-3 text did not match the engine's own registered rules. No Green prediction outside L-STANDS and the three timer floors changes, and no calibration row or SelfTest row changes.
- **B-CTLON (setup).** Rev 3 left out s163's relay claim: a just-accepted relayed start holds every locked window for RelayOwnMs (3000 ms, `NetSyncDialog.cs:57`; OrphanStep's `relayOwned` term), so a settle inside it orphans at the accept + 3 s, not the settle + OrphanGraceMs (the run settled about 0.28 s after the accept and orphaned about 0.72 s past the bound). The line now waits out the claim under `hostscene 1` (no settle while the scene is up), so the settle clock alone gates the orphan. The prediction stands.
- **L-STANDS (bound).** The rev-3 bound left out the body term of its own rule (`bodyThere && sinceEmit >= 2000 && sinceLand >= 1000`). On 30602 the auto `entry_settle` hold (50 ticks, recorded under the duo's CAL leg below) delays the control char's binding about 1.7 s past the landing hook: run 20261030-024220 read landed 1172, body 2891, life 2891. `body_ms` is stamped by the same step that ends the intent, so the row also checks it against the harness's own body read: a step that ran late would carry its own late stamp and read gap 0, and only the independent anchor catches it.
- **F-JOIN (setup).** Sent as three driver round trips, the blackout's 8-tick fade finished before the follow began (left 0: the engine correctly read black and joined). Sending both steps in one request starts the follow with about 7 ticks left; a black start is now a setup miss, VOID.
- **F-OPEN, F-RECHECK, F-KEY (floor).** `swap intent` starts the follow inside `HarnessAgent.Update`, before `NetSyncClient.Update`, so that frame's `ServiceFollowWarp` debits a whole `Time.deltaTime` that elapsed before Begin stamped the swap clock: Begin to due is 900 ms minus the start frame plus overshoot (the run's F-KEY: 882 ms on a 37 ms start frame). The floor is 900 − dt0 − 3 ms, dt0 the swap-clock gap between the start sample (`fade.path` set, `fade.age_ms` ≤ 2) and the sample before it, or 900 − 2 measured frames when no such pair was sampled. s163's 0.885-0.912 s is the live-lane duo only (`FIELD-SWAP-TIMING.md` §1): there the guest's follow starts after `ServiceFollowWarp` in the same Update, with no start-frame debit, so DF-OPEN keeps its 0.885 s.

**Lines, locks and order across the sub-legs.**
- **B.** B-RELEASE's auto-close consumes B-HOST's line. Every later B sub-leg opens a fresh line by relay, except B-SCENE, which continues B-BLIP's held line (V4).
- **P.** The sub-legs run P-PIN, P-AGED, P-OTHER, P-LATE, P-PARTY, and the leg ends with `swap clear`, which clears the party mirror the pin bench armed (G2), so legs L and F and anything later in the process start with the mirror idle.
- **F.** F-OPEN, F-AHEAD, F-AGED, F-RECHECK and F-KEY send `lock 1`; every other F sub-leg sends `lock 0` first, so no lock state leaks from leg C or from the sub-leg before (P11).

**Solo calibrations, pre-registered.** Each word turns exactly these rows red; every other row stays green:

| Word | Lever | Red rows |
|---|---|---|
| `stamps` | `swap stamps off` | A-STAMP (leg C's Δ and C-PEND's aim are timed from state keys, so they stay as they are, P10) |
| `delay` | leg 2 sends `delay 0` but still expects +300 | A-DELAY |
| `orphan` | `swap orphan old` | B-HOLD, B-RELEASE, B-BLIP, B-BLIP2, B-SCENE |
| `own` | `swap own old` | C-CACHE, C-PEND |
| `nocache` | `swap own nocache` | C-CACHE |
| `pin` | `swap pin old`, sent only around the P-PIN and P-PARTY pinbench calls; `swap pin act` before P-AGED, P-OTHER and P-LATE, so the guards keep judging their own why (P3) | P-PIN, P-PARTY |
| `life` | `swap life old` | L-STANDS |
| `fade` | `swap fade old` (leg C keeps its own `fade old`) | F-FAST, F-3X, F-BLACK, F-JOIN, F-HURRY, F-OPEN, F-AHEAD, F-AGED, F-RECHECK, F-REASSERT, F-KEY |
| `long` | `swap fade long` | F-FAST, F-3X, F-HURRY |
| `nogate` | `swap fade nogate` | F-OPEN, F-AHEAD, F-RECHECK, F-KEY |
| `norecheck` | `swap fade norecheck` | F-RECHECK |
| `nohurry` | `swap fade nohurry` | F-HURRY |
| `arrive` | `swap arrive old` before G-HOLD, G-DELAY and G-LATE (leg G, rev 4); `act` again before G-INERT | G-HOLD, G-DELAY, G-LATE |

Spacing: C-leg attempts run more than 20 s apart, or change field between them. The bounce budget (3 bounces in 20 s per field, :567-581) would otherwise let a calibration through. An s163 engine refuses the whole run at load. Any other `COOP_CALIBRATE` word is refused at load.

### Duo: `studies/test-harness/scenarios/coop_field_swap_timing_duo.py`

Two real games on this desktop through `tools/harness/duo.py`, with `stateevery 1` on both. HOME is 250, AWAY is 30602. Every guest-side lever is legal on the duo's client, and `life` goes to the host game. Both games load one DLL through the instance junction, so every calibration is a lever, never a DLL swap.

**The clock precondition (F1, F11a).** DK-CLOCK runs first: K-CLOCK must hold on BOTH games. When it does not, every cross-game row (DA-LANE, DB-BIT, DP-MARK, DL-LEFT) is VOID with the reason, never red, and a row with a cross-game clause loses only that clause (DC-B(a)'s gap, DF-FAST's gap, DA-LINES' host-tap clause, DA-ARRIVE's overlap clause and cross-game reports, DA-GUARD's seen - landing report). Rows inside one game still judge.

**Legs and their pre-registered data (F8).** Every warp, scenario and poke is data in the scenario file, as `coop_speed_mirror_duo.py:109` keeps its own.

| Leg | Host setup | Shape | Rows |
|---|---|---|---|
| CAL | `warp(250, entrance=0)`, then `warp(30602, entrance=0)` and back; the guest idle and visible; each field held at least LineWindowMs + 1 s = 11 s (F13). Sub-legs: CAL0 the guest on `fade old`; CAL1 `fade old` and `delay 200`; CAL2 act; CAL3 act and the guest on `speedmode 1`; **ARRIVE** (V5, G1): from 250, `warp(ARRIVE_ID, entrance=0)` and back, at act and again with the guest on `fade old`. ARRIVE_ID (30611) is a scratch copy of the bench field, `studies/movement/bench/lockt2-arrive.field.toml` (a copy of `lockt2.field.toml`, never the shared 30602), with `[camera] entry_settle = 64` (rev 4; 68 in rev 3). The kit compiles that as `DisableMove` and `Wait(64)` before `Main_Init`'s control grant on both copies (`build.py:8494-8507`, `content/entry_settle.py`), so each copy's arrival holds control off for 64 ticks, about 2.13 s at 30 TPS, with no line. The id comes from the dev scratch band and is read against the live `DictionaryPatch.txt` at build time; it is deployed with an explicit `--id`, its first deploy needed a relaunch, and a retune of the registered id is a redeploy only. **The retune rule (pre-registered, rev 4)** reads CAL2, a watch, never ARRIVE's own outcome: O = CAL2's overlap + L - 1667 ms (30602's 50-tick hold; O is the overhead from the landing hook to the grant) and d7 = CAL2's median delay of the host's control-back as the guest sees it; if ARRIVE's E = 64 ticks / 30 + O + d7 falls outside [D + L + bind, D + K + dx] (D = DwellMs, K = `ArrivalLeadMs`; the terms of `ARRIVAL-GUARD-S164.md`, "Predicted numbers"), `entry_settle` becomes round((2320 - O - d7) / 33.3 ms), the window's centre, before ARRIVE is judged again. DA-ARRIVE's detail reports the check; it is never judged, and VOID under an unfit clock. Record also that 30602 itself leaves `entry_settle` at its "auto" default (`lockt2.field.toml:58`), which a review run resolved to a 50-frame hold, so CAL2's own arrivals overlap about 1.2-1.35 s | the follow race's FE1 shape (debug warps) | DA-LANE, DA-CAL, DA-JOIN, DL-LIFE, DL-NOREG, DC-FE, DF-FAST, DF-3X, DA-ARRIVE (ARRIVE the gate; ARRIVE on `fade old` and CAL0 its controls; CAL2 a watch), DA-GUARD (CAL2, CAL3), DA-PROBE-X |
| DESK | `warp(359, entrance=0, scenario=2600)`; the guest follows; the host presses confirm D after each line opens and again every D until the line closes, D ∈ {0.3, 1.0, 2.5}: a press on a line still typing only finishes it and emits nothing, since the host taps only on a confirm that advances (`NetSyncClient.cs:7293-7294`) | FT-A: 359's scene runs at any scenario (`test2_102.txt` reads none) and ends in `Main_11`: `PreloadField(5,351)`, `FadeFilter(6,24)`, `Wait(25)`, entrance 15, `Field(351)` (`:271-301`, called from `:648`); 351 entrance 15 builds the desk scene (see leg C), first line win 3 text 129 | DA-LINES, DF-FLASH, DF-GRACE, DF-PACE, DA-PROBE, DA-ARRIVE (a watch), DA-GUARD, DC-WON |
| REST | continues each DESK run: the desk scene's own end, `Dagger_Loop` case 23 after text 139 closes (`test2_94.txt:3372-3386, 3850-3879`: `FadeFilter(6,30)`, `Wait(30)`, entrance 3, `Field(352)`; leg C has the detail), to 352 entrance 3, first line win 4 text 142 (`test2_95.txt:64-69, 1430-1435, 1649-1654`) (P6). Sub-legs: REST (act) and REST-OLD (the guest sends `swap fade old` before text 139 closes), each at every D | FT-B | DC-B(a) (REST), DC-B(b) (REST-OLD), DP-HALT, DP-DRESS, DA-PROBE, DA-GUARD (REST and REST-OLD), DC-WON |
| CAT | `warp(350, entrance=0, scenario=2600)` (the session's 350 value), the guest by one follow; pokes below | 350 to 351 "Cat's Eye" | DB-SHAPE, DB-BIT, DB-HOLD, DB-ORDER |
| OWN | s163's recipe: the host's byte 238 poked and read back, then `warp(351, entrance=0, scenario=2600)`; the gate bytes 238 = 1, 241 = 4, 242 = 0 on both, the guest first (`coop_speed_mirror_duo.py:427-429, 551-553`); pick choice 2 | FT-OWN: 351 to 450 "Dagger Tries" | DC-OWN |
| MENU | The guest holds its Pause screen across the host's exit (the bench's harness `warp` to 30602: `SetNextMap` from the debug-warp site, never a MAPJUMP) and closes it with cancel 1.2 s after the emit (and 3.5 s in the aged variant); the host marks flag 8720 at its landing hook (`intent.landed_ms` >= 0). A mirroring guest has no main menu (s38's spectator-field refusal, s121's buzz), and an intent follow defers on any state but FieldHUD, so Pause is the held state (rev 4). A `netsync.menu_refusal.now` of `dialog`, `off`, `silent` or empty before the press, or a Pause that never opens within 5 s, is a setup miss (VOID). Under the `pin` word the guest's `swap pin old` covers the 1.2 s run only (P3) | | DL-DEFER, DP-DEFER, DP-AGED |
| MARK | The host exits to D; once the host's landing hook ran (`intent.landed_ms` >= 0, checked explicitly, on an intent newer than the one before the warp), the bench sends `flag 8720 1` to the host. Rev 3 waited for the host's body, which binds about 1.77 s after the landing on 30602, after the guest's landing. The guest runs `swap fade long` for this leg, to widen the window | | DP-MARK |
| LEFT | From AWAY the host exits to HOME (250: its body binds 245-540 ms after the landing, so section 4's 2 s emit floor ends it and the swirl falls inside its life; on 30602 the intent ends "stands" as control and the body come back). Once the host's landing hook ran and the guest has landed too, the host sends the harness `battle 67 -1` on its field HUD, 0.8 s after its landing hook on the swap clock (`emit_t + landed_ms + 800`). The battle goes through the swirl, whose first frame ends section 4 as Left (S1, row `r-swirl`). Then it escapes, and fights only as the last resort: `scene_info.no_gameover` is false, so a wipe would Game-Over both games (the first run's one lost 60 s roll left Dagger at 7 HP). Each of up to 4 attempts takes Zidane's Flee at a host prompt, the deterministic skill escape `coop_battle_flee_defeat.py`'s H1 uses on this scene (other host slots Defend), else the bumper hold's stock level-ratio roll; an attempt's first prompt gets 45 s (the harness's battle wait returns before the intro, the s114 start hold of up to 8 s and the ATB fill) and each later one 20 s; a queued escape gets 45 s for the battle scene to go, and a re-roll needs the living members' HP at half the whole party's max HP or more (a dead member's max still counts; that lost roll cost 112 of 355). The guest's Steiner needs no move: the host's HUD never prompts a live guest's slot. The leg ends on the host's field HUD with control AND the guest back from its diorama on that field with control (each wait bounded, noted, never raised), so OPEN starts from a settled pair and no battle is left running | | DL-LEFT |
| OPEN | The host opens an NPC line (relayed locked to the guest) and warps with it up. Its seat, like every leg's, warps the host only on its field HUD (a 10 s grace); a battle still up on the host after that grace (a LEFT leftover) is a setup miss, VOID, never a burned seat | | DF-OPEN |
| every leg | the host's `dress.party` sampled at each emit and after each landing | | DP-PARTY (reach-gated) |
| LEVERS | Raw sends | | LVD-ROLE, LVD-LIFE |

**Setup for CAT (F8).**
- Both games on 350 by one follow.
- The guest at `[Cheats] SpeedFactor 3` plus `speedmode 1`; the host at 1x, so the mirror refuses.
- **The menu gate, on both copies,** the guest first and the host last, right before its press: byte 238 = 1, byte 241 = 8 (bit 3: choice 3 "Cat's Eye"), byte 242 = 0. 350's Select path reads `VAR_GenInt8_238` and offers `VAR_GenInt16_241 | 32768` (`test2_93.txt:336-352`), the same pair `coop_speed_mirror_duo.py:427-429` pokes on 351.
- **The leap gate, on the HOST only,** before its Select press, read back first: `byte 297` set to (its current value | 1), and `flag 2075 0`. HW's "Gen" names gEventGlobal (`studies/story-trace/research/design-5-claim-checks.md:10`), so `VARL_GenUInt16_297` is the UInt16 at byte 297 and `VARL_GenBool_2075` is bit 2075; the verbs are `HarnessAgent.cs:1192-1220`. `Cat_Loop` runs the leap only on entrance 16 with `297 & 1` and `2075 == 0` (`test2_94.txt:2662-2664`). 359's `Main_Init` already sets 297 to 1 (`test2_102.txt:47`), so after a DESK run the byte reads 1 and the poke is a guard.
- **Not on the guest:** its 351 landing stages the host's section 0 (the pin or the latest frame), which carries the host's values, and would overwrite a guest-side poke (F8).
- **Read back right before the pick:** 2075 = 0 on the host (`watch 2075`), and 297 bit 0 through `duo.watched_byte`, as s163 reads its gate bytes. 350's own `Code2_Loop` sets 2075 when it offers the Cat's Eye (`test2_93.txt:590-595`), so a read-back of 1 re-pokes before the pick.
- The host presses Select, picks choice 3 (`case +3`: entrance 16, `Field(351)`, `test2_93.txt:472-473`), and pages `PAGE_S` after each line opens.

| Row | Green | Calibration word |
|---|---|---|
| DK-CLOCK | K-CLOCK holds on both games (F11a) | none (the precondition above) |
| DA-LANE | Order, per transition: emit_t ≤ intent.first_sent_t ≤ seen.arrived_t ≤ seen.first_t ≤ follow_t ≤ due_t ≤ commit_t ≤ the guest's land_t. A transition whose `arrived_t` is -1 or whose first send the watch missed is UNREACHED for that transition (F10). The floor (P8): each of CAL, DESK and REST needs at least one reached transition, else DA-LANE is red "not reached: arrived_t was -1 on every transition", with reached/total in the detail. Reported, not judged (T12): first_sent_t − emit_t, seen_t − arrived_t, follow_t − seen_t, the landing gap and the first-line gap | none (gate on order) |
| DA-CAL | CAL1: `commit_t - due_t` = 200 ms ± 1 frame within each follow. Reported: CAL0's commit − follow (0.885-0.912 s predicted) and CAL1 − CAL0 | `delay` (CAL1 sends `delay 0` but still expects +200) |
| DA-PROBE | MAPJUMP legs only (DESK, REST), per intent with `intent.last_site` `mapjump` (a sample from another site is refused): frames, updates and sends ≥ 1; oob `sent` or `overwritten`; 1 ≤ the guest's `seen.copies` ≤ the host's `sends`; `last_end` `stands` under act; the host's `intent.landed_frames` Δ ≥ 1 (frames after its landing carry the bit, S3). Reported: the guest's `pin.last_use_quality` per transition. Predictions below (F4) | none (gate on consistency) |
| DA-PROBE-X | CAL: the same keys on debug-warp emits | exploratory, reported only |
| DA-JOIN | One record per transition on each copy (ids +1); the guest's nonce equals the host's; the guest's land_via `follow`, the host's `host`; both closed by `line` or `window` | none (gate) |
| DL-LIFE | The guest's seen span (last_t − first_t) is 1800-2700 ms; the host's "ended ... I stand on it" line | `life` (span about the host's load) |
| DL-NOREG | Per transition: exactly one parallel-follow line, one commit and one landing; no "follow-warp ... cancelled"; no second follow for the nonce | none (guard) |
| DC-FE | No `[NetSync] own Field(` line on the guest; `own.passes` +0 | none (guard) |
| DF-FAST | CAL2: the guest's `fade.last` = fast / fade / 12, by `black`; commit − follow 0.35-0.60 s; the guest's commit after the host's landing (`last.commit_t` − the host's landing) shorter than CAL0's by ≥ 0.3 s, the landing gain reported. The gap is net of the guest's own load: the fade governs the commit, never the load, and on one PC the fast path's load overlaps the host's own (the guarded duo's `own` run loaded one CAL2 return in 656 ms against about 300, commit on time, and its landing gain fell to 288 ms) | `fade`, `long` |
| DF-3X | CAL3: ticks 12-17 (the prime's one frame is up to 3 ticks at 3x; a 2-tick batch can push the first black read to 14), the same window as solo F-3X; commit − follow ≤ 0.22 s | `fade`, `long` |
| DA-LINES | Every edge line on both logs stamped; for each host tap seq S: tap_t ≤ queued_t ≤ closed_t; "waited X ms" = closed_t − queued_t ± 1 ms; "shown Y ms" ≤ closed_t − that page's open stamp | `stamps` (both games) |
| DF-FLASH | REACHED when `view_start` is `heading` or `black`, on a follow DF-GRACE's precondition admits (fix round 3: a post-bounce follow is listed apart, never judged; its green was vacuous, because the reloaded field's first fade-in brightens the slot one Update after Begin, before the first sample the `cur_now` window reads). Action `join` or `hurry` (a join that C's own pass ends, by `own`, is still a join; a hurry must end by `black` or `own`, never `fallback`, `recheck` or `timer`); a wipe is red on any end (Begin's `FF9Wipe_FadeOutEx` resets the slot to visible before `follow_t` is stamped, so its dip is a coin flip); no `cur_now` dip from the follow start to the first of (due, field load). Otherwise UNREACHED, never red. Rev 4 note: the join clause was rev 2's grace-INFER role, which V6 moved to DF-GRACE (here a join is only a no-flash action; DF-GRACE judges its `own` end). The detail names each run by D and REST-OLD (reported only): REST-OLD's lever goes out on 351, after this follow, so both runs at one D follow at act | `fade` (the wipe) |
| DF-GRACE | DESK at act (V6). REACHED when `fade.last.view_start` is `black`, or `heading` with `left_start` ≤ 12 (the Join action), and only on a follow whose copy could still exit (fix round 3): the record followed (`last.follow_t` set), `fade.last.field` is 351 (fade.last is one global last-follow block: a record with no follow is not judged, and a follow whose fade.last names another field makes the row VOID unless a judged run is red, which stands with the stale run named), and no own jump of this transition came before the follow (`last.own_t` unset or >= `last.follow_t`; the temporal test only, never `last.own_verdict` or `last.bounces`, which would hide a refused own pass that bounces AFTER the follow). A bounce reload's black is the reloaded field's idle load-black, which ViewRule reads Black: the copy is not exiting, so the grace has nothing to wait for and `own` can never end the follow (the bounce spent its `Field(351)`). That follow is s158's shape (DC-WON; DC-B(a) sets it aside by the same test at `last.seen_t`) and is listed apart, never judged: "post-bounce join on the reload's load-black (s158 shape, risk 8)". Green: `fade.last.by` `own`, the copy's own `Field(351)` passing by the Pending term inside the 3-tick grace and the prime. Otherwise UNREACHED | none (it falsifies the `Wait(25)` resume-tick INFER the grace rests on) |
| DF-PACE | At D = 0.3, REACHED only when the copy lags at the intent: backlog_start `line` or `ahead`; by `timer`; the guest's last close for 359 logged before the commit. Otherwise UNREACHED | `fade`, `nogate` |
| DC-B(a) | REST at act, on any path. REACHED when the guest saw the intent before its own jump or made no own jump before its landing. Green: one guest load of 352; `bounces` +0; guest landing − host landing ≤ max(0, L139) + 0.3 s, where L139 = the guest's close of text 139 − the host's close of it, each read as that game's first state sample no longer listing (win 3, text 139), by its `clock.now_ms` (P7, P10). Reported: the raw landing gap and L139. An own jump before the intent (the s158 shape) is recorded as "C2 not built" and not judged (F2). An L139 never read leaves that run's gap clause unjudged: the row is VOID only when no judged run is red, so one unread run never hides another's red (fix round 3 review) | none (behaviour gate) |
| DC-B(b) | REST-OLD (the guest on `fade old`), at every D. REACHED when `last.own_t` is set with `own_dest` 352 and the guest's last sample before it shows the intent seen (`own.cache.field` 352, or `session.follow.pending` 352) with `own.host_lane` 0 or 351 (P4). Green: an own pass (pending, committed, intent or cache), `converted` +1 when the term is pending, one load, `bounces` +0. Reported: the reach count across the D values (the own jump and the host's body race, P7) | `own` (the marker: `own_verdict` bounce and `counts.bounces` +1 -- s163's rule bounces the own `Field(352)` to a reload of 351, the guest's own field, and the follow then loads 352 once, so 352 loads once; the duo `own` run of the guarded engine read exactly this). It needs at least one REACHED run; none reached makes the calibration VOID |
| DC-WON | DESK, REST and REST-OLD: `counts.follow_won` Δ and own passes by term, per leg (F2) | reported, never judged |
| DP-HALT | REACHED when `pin.pre_frames` Δ ≥ 1 across the MAPJUMP exits (a later pre-landing frame of a held nonce was compared), else UNREACHED (F11c). Green: `pin.max_pre_diff` stays 0, the halted-VM premise the pin rests on (S3) | none (gate) |
| DP-DRESS | After the 351 → 352 landing, the guest's `dress.self.want_char` is the latest frame's section-8 pick (the host's `dress.guard.effective` over its `dress.party`, ResolveAuto's walk; 255 the moogle) and never the host's leader (no double). Each part can go red alone. VOID when `want_char`, the pick or the host's `dress.guard.leader` is unread or below 0 (a leader -1 is the `bench leaderguard off` lever's positional rule, which DESK never sends). Rev 3 wanted the leader itself, which is the double | none (the mutant `dress_follows_story` carries it) |
| DP-PARTY | REACHED only on a landing whose host `dress.party` differs between the emit and the host's landing. Green: the guest's `dress.mirror_party` after its landing equals the host's post-landing party (the latest frame), not the emit-time one (R1). UNREACHED otherwise | none (P-PARTY and the mutant `party_follows_story` carry the claim) |
| DB-SHAPE | The guest logs its own `Field(351)` passing (the host's pick, choice 3, on field 350), and its first state sample listing window (win 7, text 113) comes at least 4.5 s before `host_flags` b0 RISES on 351 (the first b0 sample after a b0-clear 351 sample at or before that 113 listing: the 350 scene's sticky tail is not the rise), both on the guest's own `clock.now_ms` (F11b). If text 118 opens first, the else path ran and the run is VOID. Rev 4: rev 3's anchor, the first sample with b0 set on 351, read field 350's sticky scene on the first duo run (-2598 ms): b0 carries no field, and the guest's own `Field(351)` lands before the host stands on a live 351 | none (reach guard) |
| DB-BIT | Between the guest's 113 open and the host's scene rise (DB-SHAPE's b0 rise on 351; a rise that precedes 113 is red, "rise precedes 113", and no rise is red, "no window"): every guest sample reads `host_flags` b1 clear with b3 set, the lane on 351, and `orphan.host_holds` true; every host sample reads `player.control` false | none (Finding 11's premise, read rather than assumed) |
| DB-HOLD | One "win 7 text 113 held -- the host's control is off on my field" line, then the end line at the host's 113 open, predicted "(a host event claims it)"; no "113 is not on the host's screen"; `orphan_closes` Δ0 across 351 | `orphan` |
| DB-ORDER | The guest's 113-117 each close "closed (host seq N)", with N strictly increasing and equal to the host's tap seq for the same text; no "dropped -- it is for field 351" | `orphan` |
| DC-OWN | One load; the term or the lane recorded | none (regression) |
| DL-DEFER | The record must be seen while paused: its own `last.seen_t` at or before the last Pause sample (never `seen.first_t`, the latest-seen slot); else red "not reached" (P8: the bench holds the intent live across the Pause, the cancel going 1.2 s after the emit, so an unseen record is the engine's, never UNREACHED). A guest that never lands on AWAY is red (the deferred follow never came; a ring whose Pause samples aged out is that shape), and VOID when its ring ends on Pause (the Pause never closed: a setup miss) or is empty. The guest's follow starts by the intent within 200 ms of its Pause closing and never while paused, judged on a bracket off the guest's ring (`Session.states_since` from the frame before the Pause press, which holds every read the session made, the press's own polls included): the last Pause sample and the first sample off it, by `clock.now_ms`. Green: `last.follow_via` `intent`; no Pause sample of this record (rec_block's `last.id`) reads `last.follow_t` >= 0; `last.follow_t` >= the last Pause sample; `last.follow_t` minus the last Pause sample <= 200 ms, an upper bound on the lag past the close (it can only overstate it). A follow inside the bracket is placed off Pause only when the bracket spans at most 2 frames on the ring's frame counter (one unsampled frame: the pre-round one-frame tolerance, counted in frames so frame-time jitter cannot move it; by `clock.now_ms`, within the close sample's own frame, only when a frame counter is unread). VOID when the ring holds no Pause sample, or, with the follow by the intent, when the bracket has no close (no sample after the last Pause sample), when a follow inside it is not placed, or when it is wider than 3 frames + 1 ms (DA-CAL's measured frame, else the ring's own median step, never the 1/30 s default) and the verdict depends on where the close falls: a follow inside the bracket, or one past it by <= 200 ms whose lag over the last Pause sample is above 200 ms. A red the ring already decides (a Pause sample of this record with `follow_t` >= 0, `follow_t` unset or before the last Pause sample, or more than 200 ms past the first sample off it), any other follow (red on its first clause), and a placed follow within 200 ms of the last Pause sample are judged whatever the bracket. Fix round 3: rev 4 read the close off the watch, whose "first sample off Pause" came at the hook's awaited cancel's ack, about 134 ms late (s157's law: a synchronous harness call inside a watch starves it), so the guarded runs' -131 / -132 ms were the instrument's; the bracket reads follow - close -16 / +1 ms there (both 2-frame brackets), and the cancel now goes out without waiting (P10; a mirroring guest has no main menu) | `life` (host; the serial follow instead) |
| DP-DEFER | REACHED only when the record was seen while paused (the term DL-DEFER reds without, fix round 3; a ring with no Pause sample is VOID, and so is a run whose guest never landed on AWAY) and that landing came by the intent (`last.follow_via` `intent`) with the pin's age < 2500 ms and `pin.last_use_quality` `pre` (P3); a `late` capture is UNREACHED with the reason "the first frame I saw came after the host's landing", and `pin.late` per leg is reported. Green: flag 8720 = 0. VOID under `life` | `pin` |
| DP-AGED | Pause held to 3.5 s: flag 8720 = 1, why `aged` | none (guard) |
| DP-MARK | VOID unless the host's first sample with flag 8720 = 1 (its `clock.now_ms`) precedes the guest's `last.land_t` by ≥ 300 ms (F11b). REACHED only when `pin.last_use_quality` reads `pre` (P3); a `late` capture is UNREACHED with its reason. Green: flag = 0, the pin line, `last_diff` ≥ 1 | `pin` |
| DL-LEFT | On HOME. REACHED when the host's last sample before its battle's send read `intent.active` for that nonce, else VOID (a setup miss, P8); VOID too when the intent then ended `stands` after that read and no later than the battle start (the race). An intent still active once the battle came up is red. Green: the host's "ended ... I left it" line for that nonce and `intent.last_end` `left`; the guest saw that nonce, and its `seen.last_t` is no later than 300 ms past the battle start (the host's first sample off FieldMap; `intent.end_t` on a Left end when that sample is unread). When the Left end fell against the swirl is not compared: S1's rule (the swirl's first frame ends section 4 as Left) is row `r-swirl`'s, and no end_t <= swirl_t clause is judged here | none (guard; row `r-swirl` pins the rule) |
| DF-OPEN | The guest's backlog_start `open`, path `backlog`, by `timer` ≥ 0.885 s. If the harness `warp` refuses with a window up, DF-PACE stands in as the backlog row | `fade`, `nogate` |
| DA-ARRIVE | **ARRIVE, the gate: the arrival guard's calibration (V5, G1; rev 4, `ARRIVAL-GUARD-S164.md`, "Duo").** REACHED when ARRIVE at act reaches its exposure: the measured overlap (the host's first control-true sample after its landing minus the guest's landing, both on the swap clock) is at least DwellMs + 100 ms, AND the guest's raw peak `netsync.stepout.base.age_ms` (`HarnessAgent.cs:5039` with s164) between its landing and its control is at least DwellMs, or the guest stepped out by dwell (the base age reads -1 while a step-out is active, so an OUT run's published peak sits within a frame of 1500 on either side). A gate that does not reach is red ("not reached"), never green. Green: from the guest's landing until its control returns, no `step-out: OUT ... -- dwell` line and `netsync.stepout.active` never true, and the green is attributable to the guard: `arrive.last.field` 30611 with `last.end` spared, `ends.spared` +1 or more, `levers.arrive` null. A red names its cause, read from the guest alone: the guard off at the landing (`levers.arrive` old: the `arrive` word's red); "the guard never anchored" (the landing's `lead_ms` null); "guard defect" (the episode's `shift_ms` off min(K, max(0, K - (B - Hs))) by more than a frame + 16 ms, where K = `ArrivalLeadMs`, B is the base start, G the guest's landing, Hs the host's landing as the guest saw it, B - Hs = (B - G) + `lead_ms`, and B - G is read at the episode's own base); "margin miss" (a dwell OUT with the guard anchored and its shift right: retune ARRIVE, not a guard defect). Reported: the peaks, `shift_ms`, `lead_ms` and its sign, the overlap, A, dx, d7, "margin thin" above 1450 ms and the retune check. An unfit clock VOIDs only the overlap clause and the cross-game reports: the in-game clauses still judge, and DA-ARRIVE is not in `CROSS_GAME`. **Controls, judged with the gate:** ARRIVE with the guest on `fade old`, CAL0, and a DESK arrival whose run is on `fade old` (under the `fade` word); a dwell OUT on any of them is red (`shift_ms` is reported against about 100 ms). **CAL2 and DESK, watches: reported apart, never judged.** A dressed arrival's (`dress.self.want_char` ≥ 0 and not Zidane) dwell OUTs are listed and reported but never change the verdict; on DESK an OUT by `line` at the desk scene's first line is lawful (with `shift_ms` above 0, reported as a guarded line start), and the 351 arrival's window ends at the 352 landing. The guest need not be dressed at the gate: the OUT is the defect, the stand-in's flash only its visible form. Reported on every arrival: the overlap, from both games' `player.control` samples (R2) | `arrive` (the guest on `swap arrive old` for the ARRIVE act run: guard off, red) |
| DA-GUARD | Rev 4, judged, probabilistic and one-game: the anchor that the ARRIVE green depends on, across ordinary landings. A landing is in scope when it is an act intent landing in CAL2, CAL3, DESK or REST (REST-OLD included: its `fade old` does not touch the guard), and REACHED when its host transition sent a landed frame (the host's `intent.landed_frames` >= 1, a per-intent count reset at its emit); any other landing is UNREACHED, never red. Green: the guest's `arrive.lead_ms` reads non-null for that landing before its control returns. Floor: at least one reached landing, else red "not reached: no landing sent a landed frame". Reported: `lead_ms` per landing, and `arrive.host.seen_t` - the host's landing (cross-game: VOID under an unfit clock) | none (`life`: UNREACHED, its declared unreach) |
| LVD-ROLE | `swap life old` to the guest gives the host-side refusal; `swap orphan old` to the host gives the guest-side refusal; `swap hostctl off` to either gives the selftest refusal | none |
| LVD-LIFE | `swap life old` to the host reads back `levers.life` `old`, and the host's `reset` releases it | none |

**DA-ARRIVE: rev 3's defect, rev 4's calibration.** At a wordless arrival both copies run the same control-off script from their own landings, so the step-out base (the host here, its control off, mine off: `NetSyncStepOut.cs:239-256`) lasts about A − lag, where A is the host's control-off time after its landing. A dwell OUT needs that base to reach `DwellMs = 1500` (:147; `StartRule` :261-268; the base re-arms its clock whenever a term fails, :556-567). So the arrivals that newly step out under s158's ARRIVAL LAW (:22-23) are those with A between 1.5 s + the act lag (about 0.45-0.5 s) and 1.5 s + s163's lag (about 1.04 s). ARRIVE puts A at about 2.27 s by construction. **Pre-registered prediction on round 1's code: RED at act** (a base of about 1.8 s), green on `fade old` (about 1.25 s). By R2's ruling a red at act must be fixed before ship, so the arrival guard is now a ship blocker, not a hope (owner decision 8). The planned fix is unchanged: a landing-scoped arrival guard behind its own lever, a dwell counted from max(the base start, my landing + the host's arrival lead), never a retuned `DwellMs`. It changes s158's step-out, so it gets its own short spec and review before it is built; ARRIVE then becomes that lever's calibration (guard off red, guard on green).

Rev 4: the first duo run (run 20261030-054437) confirmed the prediction at 68. The host led by L = 477 ms, its control came back 2364 ms after its landing (68 ticks plus an overhead of 97 ms), the guest's raw base reached an estimated 1.83 s (the published peak clips at the OUT), and it stepped out by dwell for about 1.1 s; ARRIVE-OLD's base peaked at 1422 ms with no OUT. The guard is built (`ARRIVAL-GUARD-S164.md`), ARRIVE is retuned to 64, and DA-ARRIVE is the guard's calibration: red under the `arrive` word, green at act.

**Duo calibrations, pre-registered.** Each word turns exactly these rows red:

| Word | Lever | Red rows |
|---|---|---|
| `stamps` | both games: `swap stamps off` | DA-LINES (DB-SHAPE, DP-MARK, DL-DEFER and DC-B(a)'s L139 read `clock.now_ms` and state keys, and stay as they are) |
| `delay` | CAL1 sends `delay 0` | DA-CAL |
| `orphan` | guest: `swap orphan old`, from before the pick | DB-HOLD, DB-ORDER |
| `own` | guest: `swap own old`, on REST-OLD only; CAL and DESK hold `own act` (T4) | DC-B(b), on its REACHED runs (at least one, P4, P7) |
| `nocache` | guest: `swap own nocache`, on REST-OLD only | none: a control. When the intent is seen in time the Pending term decides before the cache term is reached, so DC-B(b) stays green; the cache term's red is solo C-CACHE |
| `pin` | guest: `swap pin old`, on the MARK leg and the 1.2 s MENU run only, so DP-AGED (the 3.5 s run) keeps judging `aged` (P3). Their reach reads `pin.last_use_quality`, which records the capture's quality under the lever too | DP-MARK, DP-DEFER |
| `life` | host: `swap life old` on CAL, DESK and the 1.2 s MENU run, but `life act` for the two ARRIVE runs and back to `old` for any CAL sub-leg after them (rev 4, a scope correction: `life old` sends no landed frame, so the guard could not anchor and DA-ARRIVE would go red, breaking the word's exactness) | DL-LIFE, DL-DEFER (DP-DEFER goes VOID; DC-B(a) stays green; DA-GUARD reads UNREACHED, its declared unreach; DA-PROBE records the s163 life as a measurement) |
| `fade` | guest: `swap fade old` (the CAL sub-legs keep their own levers) | DF-FAST, DF-3X, DF-FLASH, DF-OPEN, and DF-PACE if reached (DF-GRACE reads UNREACHED: the Old path never joins) |
| `long` | guest: `swap fade long` | DF-FAST, DF-3X |
| `nogate` | guest: `swap fade nogate` | DF-OPEN, and DF-PACE if reached |
| `arrive` | guest: `swap arrive old` (read back) before the ARRIVE act run only, `act` after it (rev 4). Marker: a dwell OUT on 30611 with `levers.arrive` old and `arrive.armed` false at that landing | DA-ARRIVE |

No row is a pre-registered defect: the bench's `BASELINE_RED` is empty (rev 4), because rev 3's DA-ARRIVE red at act is now the `arrive` word's. A red outside a word's set is unpredicted.

**Pre-registered predictions:**
- **DA-CAL:** CAL0 0.885-0.912 s (the s163 measurement, reported); CAL1 `commit_t - due_t` = 200 ms ± 1 frame.
- **DF-FAST:** commit − follow about 0.40 s (12 ticks at 30 TPS, plus up to 1 tick and the prime's one frame). Landings about 0.5 s apart instead of about 0.95 s (§1: 1.04 s − 0.47 s).
- **DF-3X:** about 0.15 s.
- **DC-B(a) (P7):** no reload, and the guest lands within L139 + 0.3 s of the host. At D = 2.5 the host reads text 139 for longer than the copy's lag + 350 ms, so L139 is about the lane latency and the gap is within 0.3 s outright. At D = 0.3 the copy catches up through `MinShowMs`, so L139 is about the latency + 0.35 s and the raw gap about 0.4 s.
- **DC-WON (P6, V6; INFER on the resume tick):** on DESK (`FadeFilter(6,24)`, `Wait(25)`) and REST (`FadeFilter(6,30)`, `Wait(30)`) the copy's own `Field()` runs about 1-2 ticks after its slot first reads black. At act, when the follow starts with the copy's slot black, or heading with 12 ticks or fewer left (Join: the 3-tick grace, then the prime), the own jump wins by the Pending term (`converted` +1, `fade.last.by` `own`; DF-GRACE judges this on DESK). With more than 12 ticks left (Hurry) or a visible slot (Fade, grace 0), the follow commits first (`follow_won` +1). On the Backlog path the commit waits for the 0.9 s timer, so an own jump inside it wins. An own jump before the intent arrives is s158's shape. Fix round 3: so is an own jump that bounced before the follow started; that follow Joins the reloaded field's idle load-black and ends by recheck or timer, never `own`, and DF-GRACE and DF-FLASH list it apart rather than judge it (the guarded runs' act D 2.5 and `arrive` D 1.0 twice and D 2.5).
- **DA-ARRIVE (V5, G1):** on ARRIVE, RED at act on round 1's code (base about 1.8 s), green on `fade old` (about 1.25 s); CAL2's overlap about 1.2-1.35 s (green, close under the dwell); DESK green (its OUT, if any, is by line). Rev 4, with the guard and ARRIVE at 64: green at act, guarded dwell peak about 1.0-1.475 s (typical 1.235 s) over a raw base peak of about 1.58-2.08 s; red under `arrive` only; ARRIVE-OLD and CAL0 green (`ARRIVAL-GUARD-S164.md`, "Predicted numbers").
- **DA-GUARD (rev 4):** green on every reached landing, with at least one reached.
- **DA-PROBE (MAPJUMP legs):**
  - Under act: `last_life_ms` 2000-2400, `sends` about `last_life_ms` over the measured write period.
  - Under `life` (the s163 rule): `last_end` `old`, `last_life_ms` 250-600 (the host's load), `updates` 1-2, `frames` 1-3.
  - If `life old` reads under 100 ms instead, it is "the other Unity order OR a frame time under 10 ms / FastForwardFactor", told apart by `intent.emit_dt_us` and `intent.host_fps`: a sub-100 ms life with an emit frame of at least 10 ms / factor means the other order.
- **DA-LANE:** reported only; the writer's wait is bounded by its `Thread.Sleep(33)` at the system timer's granularity (`NetSyncSocket.cs:923` with s164; :800 at s163).
- **DB-HOLD:** the hold ends "(a host event claims it)", because the open set and b2 ride one frame.

**Exploratory (pre-registered, never gating): DP-COUNT.** Dali's `SByte[296]` countdown, from a save past 450's ping, into a controller room (356, e2, t1, +12).
- H-STEP first: the host alone must read 296 go 3 → 2, or the row is VOID.
- Then the guest reads 2 under the pin, and 1 under `pin` (the double step).

**Not provable here:** the duo shows no real network latency and no laptop/desktop load difference. The next two-PC session replays with the stamps. One host-alone run on the laptop under `swap life old` on a scripted exit (DESK or REST), read through DA-PROBE's keys including `intent.host_fps` and `emit_dt_us`, settles the laptop's order and frame-rate case.

**Open items from the first duo run (run 20261030-054437): its triage's side observations, for an owner glance. No row judges them.**
- 352's wordless scene, an owner taste call: the guest steps out by dwell about 1.7 s into the inn night scene's 7.9 s wordless lead, a visible stand-in pop after the fade-in. It is s158's accepted design, not an s164 change, but REST shows it on every run.
- A 359 line carried across the follow counts as fresh (seen after a bounce reload of 359): in runs 3 and 5 the reloaded 359 opened a line (text 106, text 105) that was still open when the follow committed, and on 351 it started the step-out about 0.23 s after the landing, because s158's fresh-line snapshot clears at a new field. Harmless on 351's party scene, but it was not 351's own line.
- A Garnet ghost beside the host's Garnet (owner glance): on 352 the guest dresses the scene's Zidane co-actor (uid 17) as Steiner while control binds to Garnet (uid 19), the s140 D3 law, and the host's ghost spawns as the guest's native Garnet body (GEO_MAIN_F0_GRN, the s139/s143 ghost rule), so the host sees a Garnet ghost next to its own Garnet. Neither comes from s164; the glance is whether the dressed co-actor doubles a Steiner already in the scene.
- The host's 350 scene outlives its 351 landing by 239 ms: the scene machine's field change waits for `onField`, so for about a quarter second a guest already on 351 reads `HostSceneUp && HostHere` true for 350's scene. Harmless in that run (no line was open); worth a look only if a row keyed on `_glSceneHere` or step-out's host scene goes red in that window.
- The copy-ahead 359 bounces (the mechanism traced in fix round 3; the noticeability question still open): in runs 3 and 5 the copy ran ahead of the host and its own `Field(351)` bounced to a reload of 359 ("the host's lane reads field 0"). The copy's 359 tail runs on its own clock after text 110 (which closes 24.9-28.4 s before the host's emit), so its phase against the emit scatters by a second or more and repeats per run type. A copy ahead of the intent bounces (OwnBounce); the deferred intent then fires on the reloaded 359's first free tick, one Update before its first event tick, so Begin reads the idle load-black as Black and Joins it; one Update later the reloaded field's fade-in turns the slot to 191/207 (Reassert re-fades it once) and a locked text 105, or a relayed host key still queued, holds the commit to the 0.9 s timer (recheck or timer). `own` cannot end it: the bounce spent the copy's `Field(351)`. The guarded runs bounced 2 of 6 DESK follows at act and 3 of 6 under `arrive`, each a visible reload of 359 plus a 0.9 s follow; DF-GRACE and DF-FLASH now list them apart (the s158 shape, risk 8). Whether a player notices that reload is still referred to the DC-B/DF-PACE triage, which has not happened yet (C2, risk 8's lever, is the owner's call).

---

## Files and hunk estimate

Every hunk is tagged `[ff9mapkit netsync s164]`.

| File (engine) | Hunks | What |
|---|---|---|
| `Memoria\Netsync\NetSyncSwap.cs` (new) | file | A's rules and record, the QPC clock, C's rules, PIN, LIFE, the levers, the state readers, the SelfTest. Rev 4 adds the arrival guard inside it (about 14 of its hunks): the pure rules and the nested `ArriveRules`, the live guard code, the five call sites (`ArriveLanding` as `OnFieldLoad`'s first statement, `ArriveHostFrame` after `PinHostFrame`, `ArriveTick` as `GuestTick`'s first statement, `ForgetArrive("session")` in `ResetSession` and `ForgetHostNonce`), the two levers, the release, `ItemNames` / `FaultsBy` (item `ARRIVE`), the state readers and the proof (`RowsArrive`, `MutantsArrive`, the tail) |
| `Memoria\Netsync\NetSyncFollowFade.cs` (new) | file | D+E's rules, the per-follow state, `Begin` / `Due` / `Ended` / `Clear` |
| `Assembly-CSharp.csproj` | 1 | two includes |
| `Memoria\Netsync\NetSyncClient.cs` | about 60 | A about 28, B 4, C about 10, PIN about 9, LIFE about 9, D+E about 6 (partly shared sites; one hunk each for the `next` and `reset` ends) |
| `Memoria\Netsync\NetSyncDialog.cs` | about 22 | A's stamps, PageT and SeenT; B's rule, hold tracking, `OrphanSinceRule` / `KeepReadRule`, OrphToLocked wording, teardown and KeyScript row; D's `BacklogNow` |
| `Memoria\Netsync\NetSyncAte.cs` | about 7 | A's three stamps; C's `HoldVerdict` / `HoldInputsNow` / `HoldsFollowQuiet` split (the loud path byte-identical) |
| `Memoria\Netsync\NetSyncSocket.cs` | about 8 | interface (three members), struct, frame fields, `SetStateWatched`, SetState, CollectOutgoing, Accept (`InStateTs`), forwarders |
| `Memoria\Netsync\NetSyncRelay.cs` | 3 | forwarders |
| `Memoria\Netsync\NetSyncState.cs` | 1 | `ApplyStorySplitTo` and its live wrapper `ApplyStorySplit` |
| `Memoria\Netsync\NetSyncBattle.cs` | 1 | the release (after :6840) |
| `Memoria\Harness\HarnessAgent.cs` | about 10 | `case "swap"`, the unknown-sub-verb literal, `AppendSwap` and its call, the catch literal, the ProtocolVersion paragraph; rev 4's guard adds 4: `levers.arrive`, the `arrive` block (`AppendSwapArrive`), both keys in the netsync-off catch literal, and the ProtocolVersion paragraph (protocol stays 5) |
| `Memoria\Netsync\NetSyncStepOut.cs` | 2 | Rev 4, the arrival guard: the one behaviour hunk, `StartRule(line, NetSyncSwap.ArriveDwellAge(fld, now, now - _baseSince, line \|\| landing), landing)` (:576-578 with s164), and its comment-only header paragraph (:68-73). s158's rules, rows and proof line are untouched |
| `Assets\Scripts\Common\SceneDirector.cs` (stock) | 1 | the read-only `NetSyncReadFade` |
| `Global\UI\UIKey\Ff9mkDebugMenu.cs` | 2 | `NetSyncWarpPending`; the emit site argument at :2452 |
| **Total** | **about 120 hunks in 13 files, plus 2 new files** (rev 3's 114 in 12, plus the guard's NetSyncStepOut.cs and HarnessAgent.cs hunks; its NetSyncSwap.cs hunks sit inside a new file) | |

**Kit files:**
- `tools/harness/{battlewire.py, fakegame.py, session.py, channel.py}`
- `ff9mapkit/tests/test_harness_netsync.py`
- new: `ff9mapkit/tests/test_coop_field_swap_timing_bench.py`
- `studies/field-coop/swap-timing/{final.py, conv.py, drift.py}`
- `studies/test-harness/scenarios/coop_follow_race_duo.py`
- new: `studies/test-harness/scenarios/coop_field_swap_timing.py` and `coop_field_swap_timing_duo.py`
- new: `studies/movement/bench/lockt2-arrive.field.toml`, ARRIVE's scratch copy of the bench field with `[camera] entry_settle = 64` (68 until rev 4), deployed at 30611 with an explicit `--id` (V5)
- rev 4: `studies/test-harness/scenarios/coop_world_wait.py` and `coop_world_battle.py` (the arrival guard's world-rejoin clause; see the gates below)
- at build: `memoria-patches/s164-netsync-field-swap-timing.patch` with its README row, and `ff9mapkit/CHANGELOG.md`

**Gates before the README row:**
- the proof line OK, at 501 rows and 183 mutants with the tail `, arrival lead 1040 ms` (rev 4), and s158's `step-out selftest: OK (56 rows, 20 mutants caught, dwell 1500 ms, step-in 500 ms)` unchanged;
- `test_coop_field_swap_timing_bench.py` and the domain tests green;
- the solo bench green, leg G included, with every calibration word turning exactly its rows red;
- the duo green with DK-CLOCK holding, with the same; DA-ARRIVE green at act on ARRIVE and attributable to the guard (round 1's code failed it on the first duo run, as predicted), DA-GUARD green, `BASELINE_RED` empty (owner decision 8);
- the regression set:
  - from rev 1: `coop_ate_relay` (s161's counts unchanged: 165 rows / 65 mutants), `coop_step_out`, `coop_chest_relay`, `coop_guest_traversal`, `coop_self_dress`, `coop_climb_anim`, `coop_speed_mirror` and `coop_dialogue_authority`;
  - added for LIFE and PIN (R3): `coop_world_wait`, `coop_world_battle`, `coop_world_party_duo`, `coop_session_edges`, `coop_session_edges_duo`, `coop_ramp_title`, `coop_talk_relay`, `coop_dialogue_lockstep`, `coop_diorama_return`, `coop_ate_relay_duo` and `coop_chest_relay_duo`;
  - the arrival guard's world exclusion (rev 4): `coop_world_wait` and `coop_world_battle` fold an arrive clause into every world-rejoin row, with no new row id (S144-RJ-LAND and S144-D3; S145-WB-300, S145-HF-REJOIN and S145-D3). On the guest's own publishes from the row's base to its last sample on the rejoin field: `arrive.world` +1 or more, `arms` +0 and `arrive.field` the rejoin field, with `arrive.lead_ms` reported in a note (the world-gap INFER: 1040 ms or more says the gap did not shrink; a short or negative one is the trigger to arm world rejoins in a later round). The clause is not judged on an engine with no `netsync.swap.arrive` (every calibration on s143-s145 keeps its set) or on a publisher that numbered no landing (the stand-in); a faulted guard is judged, red;
- `coop_follow_race_duo.py` FS/FD green.

---

## Accepted risks (ranked)

1. **No cap on the orphan hold (B).** A genuine guest-only line waits as long as the host's control is off on my field with no scene: a field movie, a wordless walk, the host's ~ menu (`Ff9mkDebugMenu.cs:840, 845`), or a pause.
   - The escapes are the ~ panic unlock, HostStallMs 10 s and LinkGraceMs 3 s.
   - A cap under about 20-25 s would re-open Finding 11 for a guest running its own booster.
   - R5's kept read clock bounds the repeated-blip case. `orphan.last_hold_ms` and the stamps size a cap if round 2 needs one (owner default 3).
2. **A line the copy has not opened yet, closed by the host's own timer with no tap,** is still cut by a fast commit (D+E). Today's 0.9 s also cuts it unless the line opens in time. The stamps measure this.
3. **Roll-once globals at entry** (`if var == 0: var = random()`). Under the pin, the guest's copy rolls its own value instead of adopting the host's. INFER: no census was run; the census runs during the build round (owner default 5). `pin.last_diff` measures how often the pin changes anything.
4. **The clock source.** The swap clock is QPC by construction, so both duo games stamp on one counter. If the P/Invoke throws, or off Windows, the clock falls back to Stopwatch, `clock.src` reads `stopwatch`, and DK-CLOCK voids every cross-game row with that reason. Deltas inside one game are not affected.
5. **The Unity order is inferred from desktop logs only, and the R1 shape also opens at frame times under 10 ms / FastForwardFactor.** LIFE's act rule never reads "is the old map alive", so neither case changes it: rows `r-order` and `r-order-old` show the act rule keeps an intent the s163 rule ends in the MAPJUMP frame. What the round measures is how often s163's rule would have lost an intent: DA-PROBE under `life old` on DESK and REST, with `host_fps` and `emit_dt_us` telling the two causes apart. A laptop host on the other order, or above 100 fps, already loses scripted-exit intents on s163; the next two-PC session reads it.
6. **The `abrColor` / shader desync after a battle return** (`SceneDirector.cs:568`). A stale "black" causes an immediate cut from a visible screen, which is visual only. The shader cross-check closes it if `Shader.GetGlobalColor` exists in this build.
7. **Seeds, not laws:** the 3-tick grace, `AheadMaxMs` 3000, `PinMaxAgeMs` 2500 from the landing seen, `PinBlindCapMs` 10000, `IntentMinLifeMs` 2000, `LandTailMs` 1000, `IntentCacheMs` 2000 and, rev 4, `ArrivalLeadMs` 1040 (the arrival guard's K: s163's measured landing gap, n = 23, not derived from the 0.9 s timer).
   - A script whose own `Field()` comes more than 3 ticks after its fade reads black loses its own pass and lands by the follow instead (the same field). With the pin and C's entrance handling, that is equivalent; DC-WON counts it.
   - A short cache only loses passes; it never adds one.
8. **The s158 shape keeps one reload** (about 1.4-1.5 s). C2 is not built.
9. **A guest that lands while the host is still on the source field** orphans after about 7 s (B's gap). Only C2 would reach it often.
10. **Fixed in rev 2: the party read wraps no longer follow the pin (R1).** The landing stages section 0 from the pin and sections 1-3 from the latest frame. What remains is s163's own behaviour: a read inside the copy's `Main_Init`, made before its own party change, sees the latest (post-change) party until a relayed talk's R8 refresh.
11. **A `Main_Init` that rewrites FieldEntrance** (bytes 2-3) would make the pin's entrance differ from the latest frame's. Under the pin, my copy replays what the host did.
12. **The `HoldsFollow` split must stay byte-identical** (C). s161's counts check the loud path; `quiet_equals_loud` checks the quiet one.
13. **Under s161's exit hold, a C pass keeps my copy's own entrance** (owner default 4). The exit hold itself is proven by self-test only (`ATE-RELAY.md:290`).
14. **Earlier landings and the step-out.** The tighter gap lengthens the overlap of the two copies' arrival control-off phases, which s158's arrival law guards only by its 1500 ms dwell; Finding 9's dressed double also shows for longer. Under round 1's rule a wordless arrival whose control-off A lies between 1.5 s + L and 2.54 s (L the landing gap: 2.0-2.54 s at a 0.5 s follow, 1.6-2.54 s at a 0.1 s own pass) newly steps out at act. ARRIVE reproduced it (rev 3's predicted red, confirmed by the first duo run), so the arrival guard became a ship blocker (owner decision 8). Rev 4's guard holds that band on every anchored arrival; what it leaves (`ARRIVAL-GUARD-S164.md`, "Worst case"):
   - **The own-pass late-read band.** At L up to about 0.35 s the guest's own load spans the host's first landed frame, so it reads the host's landing late by construction and the threshold becomes DwellMs + L + K (K = `ArrivalLeadMs`, 1.04 s). Arrivals with A from 2.54 s to L + 2.54 s (2.64-2.84 s at L 0.1-0.3) stepped out for a moment on s163; they now show the double for their whole length, bounded by K. The sign of `arrive.lead_ms` measures it; the fix (a "ms since my landing" byte in section 4) is deferred until two-PC logs size it.
   - **The unanchored residual** keeps round 1's band: a host on `swap life old`, an s163 host, a guest stall across the whole landed-frame window, battle returns, save loads and reloads (`arrive.unanchored`).
   - **The world residual:** a world rejoin is not armed (R3's exclusion, `arrive.world`), since s164 left that gap at s163's; the world benches report its `lead_ms`.
   - On an anchored arrival with A of 2.54 s or more the OUT fires at s163's instant measured from the host's landing, so Finding 9's double shows about 0.5 s longer than on s163: from landing earlier, not from the guard.

   The speed mirror's start has no dwell either (`NetSyncSpeed.cs:165-168, 185-210`): a door fade-in can start it, which s163 already accepted (`SPEED-MIRROR.md:120-121`; its latch ends the mirror with my control back). Earlier landings make that more frequent, with no new row.
15. **Bodyless destinations keep section 4** until the host leaves or emits again (7 bytes a frame). A disc change now ends section 4 at the hook.
16. **Log census.** Every `$`-anchored reader in the repo is fixed. Readers outside it, such as the owner's own scripts, are unknown.
17. **Kit churn:** about 20 tail-order asserts, plus the sub-verb regex.
18. **A copy fade that re-inits the slot mid-follow (T10, deferred to round 2), and the Add-mode exit (G4).** A copy's own `FadeFilter` started after the follow's fade re-inits the slot with its own frame count; black can then land after the 0.9 s timer and the commit cuts from a half-dark screen, the same outcome as today. The measure is the due line "the 0.9 s fallback: the fade never read black (<view>, ...)". Separately, a copy fading to WHITE (an Add-mode `FadeFilter`, `EventEngine.DoEventCode.cs:647`; for example before `Field()` in `test2_480.txt:132` and `test2_781.txt:234, 454`) reads Visible, so the Fast path's Fade switches the slot to Sub (`SceneDirector.cs:604, 645`) and the white overlay snaps back before fading to black: today's flash, not a regression, but an exception to "no flash". The fast start line logs the slot's mode, so the stamps count it.
19. **The divergent copy in the commit window (T4).** A copy whose own `Field(N)` names a field other than the follow's runs in the tick after the commit and bounces: one reload and a second follow, as today. A matching `Field()` passes by the Committed term.
20. **Levers rest on the release alone (F9).** A throw inside `HarnessReleaseBench` before `NetSyncSwap.HarnessRelease()` would leave a lever set until restart, the same exposure every netsync lever has had since s133.
21. **World-rejoin landings stage the latest frame in round 1 (R3).** A world script's writes after its MAPJUMP reach the guest exactly as on s163.
22. **The landed bit lengthens section 4 by one byte inside wire v14 (S3).** Every s163 reader takes the first three bytes and treats a longer body as ordinary (PIN, "The host's half"). An s164 guest under an s163 host gets no bit, reads every frame as landed and stages the latest frame, which is s163's behaviour. A frame built after the host's landing hook but before its `Main_Init` finished is also read as landed: conservative, never a wrong pin.
23. **DP-PARTY is not deterministically reachable on the duo.** No harness verb changes a real host's party or bag at a chosen moment. P-PARTY (solo, through the real `ParseSections`) and the mutant `party_follows_story` carry the claim; a host-side party poke is a build-round follow-up if the owner wants the duo row reached on purpose.
24. **A guest that sees no pre-landing frame stages the latest frame.** With the landed bit, a guest stall, a re-send or a reconnect can no longer mislabel a frame. A guest whose own stall (or link outage) spans the host's whole load, from MAPJUMP to the landing hook, observes no frame with the bit clear, captures Late and stages the latest frame, as s163 does. `pin.late` and `pin.last_use_quality` count it; DP-MARK and DP-DEFER read such a run as UNREACHED, not red.
25. **A battle on the new field ends section 4 at its swirl (S1).** A guest still deferred on the source field when the host's battle starts falls back to the serial follow, exactly as on s163. Rev 2's battle-keep could never fire (the swirl reads `gMode` 1 with the FieldMap gone) and is removed rather than rebuilt on `FF9Sys.mode`; rebuilding it would also have needed a PIN guard against swirl frames.

## Owner decisions (defaults taken)

Rev 1 left seven questions open. The owner took a default for each; every default names the lever or follow-up that reverses it. Rev 3 adds question 8.

1. **The backlog path without the flash: yes.** With a backlog the follow keeps today's exact timing (24-tick length, 0.9 s timer), but a screen already black or going black is not forced back to visible first. Reversed by `swap fade old`, which restores today's wipe on every path. A backlog-only wipe lever was considered (F12) and not built.
2. **Hurry, not a literal "never re-init".** A copy fade slower than the follow's budget is re-paced to black from where it is, without a flash. Reversed by `swap fade nohurry`, which keeps the literal rule reachable.
3. **No cap on the orphan hold in round 1.** A cap is sized from `orphan.last_hold_ms` and the stamps if round 2 needs one. `swap orphan old` restores s163's rule.
4. **The entrance for a C pass under s161's exit hold: my copy's own entrance**, consistent with today's passes (`OwnPassKeepsOwn`). Reversing it is a one-term change in a later round; the mutant `entrance_exit_hold_blind` shows the difference.
5. **The entry-write census runs during the build round** (offline: the 817 exports' `Main_Init` and first tag-1 writes classed as set, read-modify-write, once-gated, random-gated or bytes 2-3). `pin.last_diff` measures in play, and `swap pin old` restores the latest frame.
6. **(Removed.)** Rev 1 asked whether to accept a first Netsync read of the harness-armed flag. Rev 2 follows the s163 lever shape and reads nothing from the harness (F9; § The lever scheme).
7. **C2 in a later round.** It needs a lockstep guard and an "own-ahead landing" law (keep my copy's own story when no intent frame exists for the landed field), each with its own review.
8. **The arrival guard (new in rev 3; default taken: R2's own ruling; built in rev 4).** ARRIVE makes DA-ARRIVE's red at act certain on round 1's code. The default keeps R2's rule that a red at act is fixed before ship: the round builds, the first duo run confirms the predicted red, and the planned landing-scoped guard (its own lever, its own short spec and review) lands before the README row, with ARRIVE as its calibration. Reversed by accepting risk 14 instead, which demotes ARRIVE to a reported number and needs an offline census of the HW exports' wordless arrival control-off lengths to size the exposure.
   - **Rev 4: done as specified.** The first duo run confirmed the red, and the guard is `ARRIVAL-GUARD-S164.md` (spec, review and build log), behind `swap arrive act|old`, folded into s164.
   - **The reading taken** of "my landing + the host's arrival lead" is the lead the host is owed, K - (G - Hs), with K = `ArrivalLeadMs` 1040 (s163's measured gap), G my landing and Hs the host's landing as I first saw it: my landing + that lead = Hs + K for every G, so the dwell counts from max(B, min(Hs + 1040, B + 1040)), B the base start, and an anchored arrival steps out at s163's instant whatever the gap. The literal reading (origin 2G - Hs) and "my landing + K" are the mutants `arrive_literal_lag` and `arrive_from_my_landing`, each a one-line reversal. The build took this default, with the own-pass late-read band (risk 14) and ARRIVE's retune to 64.

## Sources

- `studies/field-coop/FIELD-SWAP-TIMING.md` (the measurements, options, corrections and recommendation; workflow `wf_87a54375-399`).
- The five item specs of this round's workflow: A instrument, B orphan and levers, C own pass, PIN-LIFE, D+E fade.
- The three reviews of rev 1: timing-race (T1-T14), regression (R1-R9), proof-bench (F1-F14), with the owner's resolution of each.
- The reviews of rev 2 and their adversarial verification (S1-S5, V1-V7, G1-G4, P2-P11, I2-I10), applied as § What changed from rev 2.
- `studies/field-coop/ARRIVAL-GUARD-S164.md` (owner decision 8: the spec, its review round 1 and the build log), and the first duo run (run 20261030-054437) with its triage and bench fix rounds, applied in What changed from rev 3.
- `studies/field-coop/SPEED-MIRROR.md`, `ff9mapkit/tests/test_coop_speed_mirror_bench.py` and `studies/test-harness/scenarios/coop_speed_mirror_duo.py` (the s163 shape).
- Engine reads at s163:
  - `NetSyncClient.cs` (:215-216, 516-597, 858-947, 1140-1144, 1650-1690, 1940-1951, 2028-2111, 2160-2180, 4655-4675, 5599-5640, 5750-5779, 5832-5860, 6150-6165, 6598-6672, 6728-6756, 6800-6830, 6874-6885, 7155-7192, 7740-7839, 8780-8796, 9371-9432);
  - `NetSyncDialog.cs` (:50-55, 88-96, 815-818, 889-894, 1180-1201, 1335-1346, 1505-1553, 1674-1686, 2214-2220, 3228-3229);
  - `NetSyncSocket.cs` (:37-76, 280-449, 609, 794-802);
  - `NetSyncState.cs` (:37, 79-125, 145-157, 270-290); `NetSyncParty.cs` (:1-40, 76-98, 215-252, 486-512); `NetSyncDiorama.cs` (:2915-2927);
  - `NetSyncAte.cs` (:668-702); `NetSyncSpeed.cs` (:12-44, 88-100); `NetSyncStepOut.cs` (:18-26, 144-150, 236-272, 545-575, 606); `NetSyncRelay.cs` (:47, 187-195);
  - `NetSyncBattle.cs` (:6758-6841);
  - `HarnessAgent.cs` (:398-406, 1188-1226, 1594-1612, 1760-1774, 2238-2337, 2350-2365, 4010-4077, 4117-4120, 4168, 4634-4641, 4990-4997);
  - `HonoluluFieldMain.cs` (:10-20, 148-152, 200-212, 226-340, 440-452); `HonoBehaviorSystem.cs` (:10-40, 90-125); `SceneDirector.cs` (:248-290, 392-404, 512-565, 636-680);
  - `FPSManager.cs` (:1-110); `QuitUI.cs` (:50-58); `Ff9mkDebugMenu.cs` (:854-858, 1338-1344, 2418-2460);
  - `EventEngine.DoEventCode.cs` (:632-648, 1014-1044); `Memoria/Speedrun/AutoSplitterPipe.cs` (:168-174).
- HW exports (`C:\gd\FFIX\reference\test2\`): `test2_93.txt` (350: :336-352, 444-473, 560-620), `test2_94.txt` (351: :56-80, 840-910, 1090-1112, 1115-1116, 2645-2715, 3222-3240, 3285-3320, 3370-3390, 3460-3540, 3848-3881), `test2_95.txt` (352: :60-72, 1428-1450, 1636-1658), `test2_102.txt` (359: :1-60, 138-170, 271-310, 648); `studies/story-trace/research/design-5-claim-checks.md:10`.
- Kit reads: `ff9mapkit/ff9mapkit/build.py` (:8494-8507), `studies/movement/bench/lockt2.field.toml` (:58), `tools/harness/coop_peer.py` (:2268, 2571), `studies/test-harness/scenarios/_coop_battle.py` (:214-220), `coop_follow_race_duo.py` (:715-719); the s163 two-PC host log (`twopc-s163-20261029/desktop-host...log`, lines 69-88).
- The two-PC logs: `.harness-runs/twopc-{r3-20261027, s158-20261028, s161-20261028, s163-20261029}` (main repo).
