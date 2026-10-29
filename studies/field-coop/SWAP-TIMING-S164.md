# Field-swap timing, round 1 (engine round s164)

**Status: rev 2, DESIGN (2026-10-29). Not built.** The owner chose round 1 of `FIELD-SWAP-TIMING.md` §4, with the 12-tick follow fade for a guest that is not already faded. This document combines five item specs into one round: A, the instrument; B, the orphan hold and the lever scheme; C, the own pass; PIN and LIFE; D and E, the fade. Rev 2 applies the owner's resolution of every finding from the three reviews of rev 1 (timing-race T1-T14, regression R1-R9, proof-bench F1-F14).

It builds on s163 (`Assembly-CSharp.dll` `7687fb583c0e6189`). Engine cites are against `C:\gd\FFIX\Memoria\Assembly-CSharp` at s163 (stock `6b8bb2d5` plus the stack through s163). Field-script cites are against the HW exports in `C:\gd\FFIX\reference\test2\` (`reference/field-manifest.tsv`: 350 = `test2_93`, 351 = `test2_94`, 352 = `test2_95`, 359 = `test2_102`, 450 = `test2_112`). Kit cites are against this worktree. An engine claim with no label was read in the code. **INFER** marks a deduction, and each one names the bench row that settles it.

## The problem

1. **The timer.** A parallel follow lands the guest 1.04 s behind the host (n = 23). The follow's 0.9 s timer is about 90% of that (`FIELD-SWAP-TIMING.md` §1). On a duo (one desktop), follow start to commit measures 0.885-0.912 s.
2. **The fade starts late.** The intent leaves at the host's MAPJUMP (`EventEngine.DoEventCode.cs:1040`). Stock exits fade *before* `Field()`, so the guest's 24-tick fade starts after the host's own fade has already ended (§2; `NetSyncClient.cs:215-216, 4665-4672`).
3. **3x and the flash.** At 3x the guest's fade ends after 267 ms, and the screen then stays black for about 630 ms more. The timer subtracts `Time.deltaTime` once per Unity frame (`NetSyncClient.cs:6606`). `Time.deltaTime` follows `Time.timeScale` (`QuitUI.cs:54-55` sets it to 0; the ~ menu's time-scale buttons set others, `Ff9mkDebugMenu.cs:1338-1343`), but the booster never touches `timeScale` or the frame rate: it runs `FastForwardFactor` main-loop ticks per frame's worth of `deltaTime` (`FPSManager.cs:77-99`; `NetSyncSpeed.cs:12-13`). So the fade runs three ticks a frame while the timer still counts 0.9 s of frame time. The follow fade also flashes a screen that the copy's own script already darkened (`SceneDirector.cs:671-675`).
4. **The bounce.** 2 of the 5 scripted Dali transitions bounced. The copy's own `Field(352)` ran while the host was loading, `LastHostField` read 0, and the guest reloaded 351 first. That cost 1.4-1.5 s plus a visible reload (§1; `NetSyncClient.cs:557, 589-594`).
5. **The instrument.** `Memoria.log` stamps whole seconds. It cannot see the 0.9 s timer, the lane latency or the 350 ms close floor. Every tightening also makes Finding 11 more reachable: the guest's line on 351 was orphaned while the host's control was off (§3 A, B).

**Expected after round 1 (§4):**
- No bounce reload when the intent arrives before the own jump.
- Scripted transitions land 0.1-0.3 s after the host.
- Gateway walks land about 0.5 s behind (12 ticks).
- Every 3x follow is about 630 ms shorter.
- No flash.

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
| R2 | Duo watch row DA-ARRIVE on CAL2 and DESK with a dressed guest, `fade old` as its control. No arrival guard is pre-built; a red at act is a real defect to fix before ship, with the planned guard written down | Duo benches; risk 14 |
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

## Conflicts between the specs, and what this document chose

| # | Conflict | Chosen | Why |
|---|---|---|---|
| 1 | Lever verb: A, B, C and PIN-LIFE use `netsync swap`; D+E proposed `netsync followfade` | One sub-verb, `netsync swap <op>`. D+E's ops become `swap fade ...` and `swap blackout` | One lever scheme means one HarnessAgent case, one release and one driver table |
| 2 | Proof line: A "field swap", B "field-swap", C "own-pass", D+E "follow fade" | One line, `field swap selftest: OK (...)`, from `NetSyncSwap.SelfTest`, as the proof block's last line | The task asks for one proof line |
| 3 | Lever roles: A and PIN-LIFE any role; C client or selftest; B a role table | B's table. Guest-side levers are refused on a host. `life` is refused on a client. `stamps` and `clear` are legal on any role | A calibration sent to the wrong duo game then fails at the step instead of reading as an unpredicted green |
| 4 | Leaked-lever guard: C role-checks in its getter, PIN-LIFE relies on the release alone, A, B and D+E proposed a getter that also reads the harness-armed flag | The s163 shape. The role is checked when the lever is SET (the refusal order below). Every lever is released on every role by `NetSyncSwap.HarnessRelease()`, called from `NetSyncBattle.HarnessReleaseBench` after s163's `NetSyncSpeed.HarnessRelease()` (`NetSyncBattle.cs:6758, 6840`). Getters are plain. No Netsync file reads HarnessAgent | `HarnessReleaseBench` runs on every `HarnessSelfTest(false)`, above its forced-role return (`NetSyncClient.cs:9403-9407`): disarm, fault, `reset`, and the release a harness diorama defers to its teardown (`HarnessAgent.cs:2353-2361`). While that diorama holds the release, the selftest role is held too (`HarnessAgent.cs:2317-2325`), so a getter that added the harness-armed flag to `IsSelfTestRole` would guard nothing there. s163 already ships an any-role lever on the release alone (`NetSyncSpeed.LeverOff`, `NetSyncSpeed.cs:91-93`). The residual (a throw inside `HarnessReleaseBench` before this round's call) is shared with every netsync lever since s133 (risk 20) |
| 5 | `delay` range: A 0-5000, B 0-2000 | 0-2000 | The delay holds a black screen with control off. 2000 still covers DA-CAL's +200 and A-DELAY's +300 |
| 6 | Three guest readers of section 4 (A's seen edge, C's cache, PIN's capture) at three call sites | One site: `NetSyncSwap.NoteHostFrame`, in `ObserveHostDialog`'s new-frame branch, right after `NetSyncSpeed.NoteHostFrame` (`NetSyncClient.cs:7808`) | It runs every client Update (`:2167-2168`). It runs after `_dlg.Observe` has read section 7 (PIN needs b3) and after `LastHostField` is set (`:2166`, PIN's landing-seen lane term), and before `ServiceIntentFollow` (`:2170`), so a follow started this Update already has its cache and its pin. C's cache aging runs in `NetSyncSwap.GuestTick`, right after `:2168` |
| 7 | C asked for the pin's frame to live in its cache record | Kept separate; both written at the one site | The cache ages out at 2000 ms and clears once the host's lane moves past. A pin lives until it is consumed, superseded for a field no follow targets, or aged (2500 ms from the host's landing as seen), and must survive a "host past" clear |
| 8 | Two lines for one own jump (A's L-OWN and C's pass line) | Exactly one line per own jump. C's pass or refusal line if C decided, else A's instrument line | One line per edge. Line classes are told apart by prefix (§ Log classes) |
| 9 | `stamps off`: A wanted "the exact s163 log" | It removes stamps, the waited/shown tails and every `[NetSync] swap` line. Behaviour lines from B-E still print, without stamps | An instrument lever must never silence a behaviour change |
| 10 | Intent end words: A has landed/next/session; LIFE has stands/left/elsewhere/cap/old/reset | One vocabulary: `stands \| left \| elsewhere \| cap \| old \| next \| reset` | A's "landed" is the s163 self-clear, which is `old`. "session" is `reset`. LIFE's "replaced" is `next` |
| 11 | DA-PROBE prediction: A predicted from code a life under 100 ms and 1-3 sends; LIFE read four host logs | LIFE's evidence, registered on MAPJUMP legs only, with the frame rate logged | Details below the table |
| 12 | FT-CAL's 0.885-0.912 s describes today's fade | The DA-CAL leg pins the guest to `swap fade old`. DF-FAST measures the shipping figure | Under D+E an idle guest commits after about 0.4 s |
| 13 | E as a lever: B had `cut old`, D+E had none | `swap fade long`: D stays on, and the fast path fades 24 ticks | E is its own mechanism, so it gets its own calibration |
| 14 | D+E's five departures from the task | All five taken. The owner took the defaults on two: the backlog path without the flash (owner default 1), and Hurry instead of a literal "never re-init" (owner default 2) | Each keeps today's timing bound, and each has a lever or a follow-up that restores the alternative |
| 15 | C2 | Dropped | C's writer found it unsound (§C, "C2") |
| 16 | Five solo scenario files proposed | One solo scenario, `coop_field_swap_timing.py`, with legs selected by `COOP_LEGS`, plus the duo | LIFE's tape rows (T-*) are read from the duo's two state blocks instead. T-STORY becomes an engine counter (`pin.last_upgrade_diff`), so `coop_peer.py` does not change |
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

- Every behaviour and instrument line ends with ` (t T ms)` while stamps are on. The stamp always goes at the very end of the `Log.Message` statement, after any closing ")". That keeps every literal the kit's source tests check (`test_coop_speed_mirror_bench.py:667`, `test_world_coop.py:684`).
- An edge reads the clock once, so its log line and its state key carry the same `t`.
- Instrument lines are gated on `NetSyncClient.SwapSessionRole` = `_enabled && (IsSelfTestRole || ((_role == "host" || _role == "client") && _instance != null && _instance._socket != null))`.
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
- `public struct StateProbe` is read all at once under the frames lock. Its fields: `SetSeq`, `SentSeq`, `Sends`, `Unsent`, `WatchFrom`, `WatchTo`, `WatchSends`, `WatchFirstTs`, `WatchLastTs` (raw swap-clock ticks, -1 = none), `FromSent`, `FromReplaced`, `InState` (the latest received payload), `InStateTs` (-1 = none), `InSeq` (the receive seq of `InState`).
- **`SetState` (:314):**
  - a slot replaced before any write counts `Unsent++`;
  - the watch's first frame replaced unsent sets `FromReplaced`;
  - every non-null frame increments `SetSeq`.
- **`CollectOutgoing` (:386):**
  - sets `SentSeq = SetSeq` and increments `Sends`;
  - inside the watch window it also increments `WatchSends` and records the first and last send ticks;
  - it sets `FromSent` when `SetSeq == WatchFrom`.
- **`Accept`, `TypeState` (:436-438):** increments `InSeq` (a count of TypeState payloads received on this transport) and records `InStateTs` from the swap clock's raw counter, beside `_inStateTick`. PIN's receive-seq continuity reads `InSeq` (T6).
- `NetSyncSocket` (:609 area) and `NetSyncRelay.cs` (:121 area) forward the new members to `_frames`.
- A redial creates a new `NetSyncFrames`. The host probe keeps a reference to the transport it read from (the precedent at `NetSyncBattle.cs:3152`) and shows -1 when that transport is stale. The guest's receive-seq memory resets with it (the next first frame reads Late).

### Call sites (every hunk tagged `[ff9mapkit netsync s164]`)

| Site | Hunk |
|---|---|
| `EmitFieldIntentIfHost` (:6734-6755) | Gains an overload `EmitFieldIntentIfHost(Int32 dest, Int32 site)`; the one-argument form (called by MAPJUMP, `DoEventCode.cs:1040`) passes `mapjump`. Capture `was = _intentActive` before :6745. The out-of-band write at :6748 becomes `oobSeq = i._socket.SetStateWatched(frame)` (a throw falls back to `SetLocalState(frame)` and records oob unknown). Then `t = NoteEmit(dest, nonce, site, oobSeq, frame != null, was)`, which opens or joins the host record (Emit), sets the writer to Host, and stamps `host_fps` and `emit_dt_us`. The line at :6749 gains `+ Stamp(t)` |
| `Ff9mkDebugMenu.ServicePendingWarp` (:2452) | `EmitFieldIntentIfHost(mapNo)` becomes `EmitFieldIntentIfHost(mapNo, NetSyncSwap.SiteDebugWarp)` (F4) |
| Host intent end (LIFE's `HostIntentLifeStep`, replacing :2095-2096) | `NoteIntentUpdate()` each Update while active. On the end: `NoteIntentEnd(why, _socket)` records `end_t` and `last_life_ms` and closes the watch at `SetSeq + 1` |
| `BuildStateFrame`, the `if (_intentActive)` append (~:6780) | `NoteIntentFrame()`, which counts host frames that carry section 4 |
| `ResetIntentAndL1State` (:6676-6726) | Before :6680, an active intent ends as `reset`. Then `NetSyncSwap.Reset("the co-op session reset")` closes the record as `reset` and forgets the seen nonce |
| `EmitDialogTap` live line (:7370) | `+ Stamp()` (voice-thread safe: it reads static booleans and the clock). The recorded line at :7362 is untouched |
| `UpdateHostScene` :6915 "rose", :6917 "ended"; `StampTalk` :7039 | `+ Stamp()` |
| `ScanHostOpenSet` (:6840-6885) | Keep the (Id, TextId) of the first lockable window that is not Inh. Before `_hostLineOpen = line` (:6881), on a rising edge on a field: `NoteFirstLine(NowMs(), fld, win, text)`. No log line; the stamped "scene rose" line covers it |
| `ObserveHostDialog` new-frame branch (:7800-7809) | After :7808: `NetSyncSwap.NoteHostFrame(state, now, myField, onWorld, following, LastHostField, offField)`. This is the one guest site (row 6 above). Item A's part: on `SeenRule` it records seen_t, the nonce, `recv_seq` and arrived_t (`TicksToMs(probe.InStateTs)` when `ReferenceEquals(probe.InState, state)`, else -1), then applies `JoinRule(Seen)`. Each further copy of the same nonce increments `copies`. `ObserveHostDialog` runs before `ServiceIntentFollow` (:2168, :2170), so seen_t ≤ follow_t |
| `ResetGuestDedupForEpoch` (:7822-7838) | `ForgetHostNonce()` |
| `StartFollowWarp(Int32 dest)` (:4665) | Becomes `StartFollowWarp(Int32 dest, Int32 via)`: `_followStartT = NoteFollow(dest, via, fldMapNo); _followDelayFrom = -1;`. Callers: `FollowHostTick` :4649-4650 (serial); `ServiceIntentFollow` :7189 (intent); `DebugInjectIntentImpl` :7280-7281 (intent, plus `NoteBenchSeen` after the codec round trip at :7259). Each caller's line gains the stamp. D replaces the wipe inside (§D+E) |
| `SameFieldKickTick` (:6586-6592) | `_followStartT = NowMs(); _followDelayFrom = -1;`. A kick never touches the record |
| `ServiceFollowWarp` (:6602-6668) | After D's `Due` returns not-Wait, `Due` latches the verdict and its time `due_t`. Then `if (!NetSyncSwap.CommitDelayAllows(ref _followDelayFrom)) return;` (`DelayRule`; fails open to true). The drop lines (:6635, :6651-6655) gain the stamp, preceded by `NoteDrop(...)`. After the write (:6662-6666): `NoteCommit(mapNo, kick, _followStartT, dueWord, delayMs)`, which writes the L-COMMIT line, records `commit_t`, sets the writer (Follow or Kick) and applies `JoinRule(Commit)` |
| `NoteFieldLanding` lines (:5826-5831), `NoteFollowWaits` (:4783) | `+ Stamp()` |
| `ApplyStoryBeforeEvents` (:874) | After `NoteFieldLanding`: `NetSyncSwap.OnFieldLoad(fldMapNo)`. It sets via = `LandViaRule(...)` (the landing consumes the writer) and applies `JoinRule(Land)`. It prints L-LAND only when the landing joined a record or via is follow, kick, own, bounce or host. A landing via `follow` whose record holds no own edge increments `counts.follow_won` (F2) |
| `RedirectGuestFieldJump` (:516-597) | Today's body becomes `RedirectGuestFieldJumpCore(ref dest, ref verdict, ref why)`. The wrapper stamps `OwnJumpT = NowMs()`, runs the core, then calls `NoteOwnJump(asked, dest, myField, verdict, why, LastHostField, t)` (rule list below the table) |
| `NetSyncAte.cs` :609, :622, :638 | `+ Stamp(NetSyncSwap.OwnJumpT)` |
| `NetSyncDialog.cs` | Details below the table |
| `Update` (:1669-1670) | After `if (!_enabled) return;`: `NetSyncSwap.Tick()`. It runs `CloseRule`'s window and stale checks, and costs one bool test when nothing is open |
| Transport start (:2063) | After `_socket.Start()`: the L-CLOCK line, once |
| Proof block (after :1950) | The round's proof line (§ SelfTest) |

**The verdict each return of `RedirectGuestFieldJumpCore` records:**
- gMode 3 (:524-525): World, with no record and no line in round 1;
- the s161 ATE pass (:542-554): Ate, or AteRedirect when redirected;
- `dest == myField` (:557): Reload / `same-field`;
- `dest == LastHostField` (:557): Pass / `host-field`;
- `EndingPasses` (:563): Pass / `ending`;
- the spent budget (:569-579): Through / `budget`;
- the bounce (:589-594): Bounce / `not-host`;
- the catch (:596): Pass / `fault`.

**What `NoteOwnJump` does.** It applies `JoinRule(Own, Bounce ? asked : final, ...)`. For a bounce it sets the writer to (Bounce, myField); otherwise to (Own, final). It increments `counts.bounces` on Bounce. Then it prints the one own-jump line (§C decides which). READ: today's bounce line is `DeclineOnce`, which is latched once per field (`NetSyncField.cs:578-600`); it is kept.

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
- **L-OWN** (only for the s163 verdicts, and only when C printed nothing): `[NetSync] swap: own Field(D) on field F -- <outcome> (swap #K) (t T ms)`. The outcome is one of:
  - `passes (the host's field)`
  - `passes (a same-field reload)`
  - `passes (the ending)`
  - `passes (a read fault: the vanilla jump)`
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
NetSyncDialog.OrphanSinceRule(Boolean relocked, Int32 kept, Int32 now)      relocked ? kept : now          // R5
  (a window re-orphaned after a control relock keeps the reading clock it first orphaned with: a relock pauses
   the read, it never restarts it)
```

**R5, why the read clock is kept.** `OrphToOrphaned` sets `w.OrphanSince = v.Now` (`NetSyncDialog.cs:1538-1541`), and the auto-confirm waits `AutoReadMs` from the later of the completed page and `OrphanSince` (`:1680-1683`). Under act, every host control blip on my field relocks an orphaned window. Without the rule, a host that keeps losing control more often than every 2 s (its own climbs, MOVQ walks) would hold a genuinely guest-only line indefinitely. With it, the line auto-closes no later than its first orphaning + `AutoReadMs` + the time it was held.

**Unchanged:**
- `SettleClock` (:2418-2475), `OrphanStep` (:1663-1684), `KeyHostHalf`, the chip, and the key idle purge.
- `HostHoldsInput` stays out of the settle clock. Moving it in would change `KeyHostHalf` and the s153 re-ask breaker's memory.

### Call sites

- **`NetSyncDialog.Orphans` (:1526):**
  - `leverOld = NetSyncSwap.OrphanLeverOld || _ctlFaulted`;
  - `settled = OrphanSettled(_settle.Long, d.FlagButtonInh, v.HostHoldsInput, leverOld)`;
  - `OrphanStep` is unchanged.
  - Then, under act, inside a try: compute `actOld` with the old rule, `kind = CtlHoldKind(w.Cls, act, actOld)`, and `StepCtlHold(w, kind, eventPending, ref v)`. A fault calls `CtlFault`. All of this runs before `if (act == OrphNone) continue;` (:1529).
  - The `OrphToOrphaned` branch (:1541) becomes `w.OrphanSince = OrphanSinceRule(w.CtlRelocked, w.OrphanKept, v.Now);`.
- **`StepCtlHold`:**
  - On the rising edge it sets `w.CtlHeld` and `w.CtlHeldSince` and counts a hold or a relock. On a relock it also sets `w.CtlRelocked = true` and `w.OrphanKept = w.OrphanSince`. It logs the hold line for a hold only; a relock uses the existing line.
  - On the falling edge it computes `HoldEndWhy`, records `last_hold_ms` and `last_end`, and logs the end line.
  - After the loop it sets `holding` to the count of held windows.
- **The OrphToLocked line (:1550-1551)** gains a case after `eventPending`: `kind == CtlRelock ? " held -- the host's control is off on my field"`.
- **New fields:**
  - `Win` gains `Boolean CtlHeld, CtlRelocked; Int32 CtlHeldSince, OrphanKept`;
  - `NetSyncDialog` gains `Boolean _ctlFaulted`, sticky per session and cleared in `ResetAll`.
- **Window teardown:**
  - the `Track` removal loop (:1281-1289) ends a hold as Closed before `RemoveAt`;
  - `ForgetWindows` (:487) and `ResetAll` (:431) call `EndCtlHolds(Forgot)`, which loops only over held windows.
- **`NetSyncClient.cs`:**
  - :7767 becomes `v.HostHoldsInput = HostHoldsRule(v.HostHere, hv != null, hr)`;
  - **:7780 is an ADDITION, never a replacement (R8).** The existing line `_glHostHoldsInput = v.HostHoldsInput;` stays exactly as it is; it feeds s156's `GuestHostSceneWhy` (:1142-1143), s158's step-out `hostCtlOff` (:6968) and s163's `hostHolds` (:6994). The new line goes after it: `NetSyncSwap.HostHoldsNow = v.HostHoldsInput;   // [ff9mapkit netsync s164]`. The session-off path (:7680) sets `NetSyncSwap.HostHoldsNow = false`. A kit source test asserts the original line is still present.
- **`BenchHostTick` (:7859):**
  - the section-7 flag becomes `DebugHostEventFlag != 0 ? HfScene : (NetSyncSwap.BenchHostCtlOff ? 0 : HfControl)`;
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

There is also a side-effect-free ATE query. It is a refactor, not a new rule. `NetSyncAte.HoldsFollow` (`NetSyncAte.cs:670-745`) splits into two parts:
- a private `HoldVerdict(...)`, which is the exit-hold term (:674) followed by `FollowHoldRule`;
- the existing arming, logging and counters, kept byte-identical.

A new `HoldsFollowQuiet(...)` returns -1 on a fault, 0 for no hold and 1 for held. It arms nothing and logs nothing. **Its equivalence is proven, not assumed (F7):** the SelfTest row `quiet_equals_loud` sweeps the full input grid (exit-hold field set or unset and equal or not to `dest`, the lever, `myCtl`, `myField` against the press field, `pressQueued`, `choiceQueued`, each clock armed and unarmed, past and short of its bound) through `HoldVerdict` and `HoldsFollowQuiet` and requires equal answers at every point. The mutant `quiet_no_exit_hold` (`HoldsFollowQuiet` without the :674 term) must fail it. s161's unchanged proof counts (165 rows / 65 mutants) still test the loud path.

### Call sites and state

- **The cache** is written at the one guest site (`NoteHostFrame`, row 6 of the conflicts table) through `IntentCacheStep`:
  - on Write it sets field, nonce, `src = myField`, `host_from` (`LastHostField` when it is a real field other than `secField`, else -1) and the tick;
  - on Skip it clears a standing cache as "superseded";
  - on the world map, or when not following, it clears ("the world map" / "not following").
- **`NetSyncSwap.GuestTick(myField, LastHostField)`** runs after :2168 on a client, and after :2039 on the selftest role. It runs `IntentCacheVerdict` and clears the cache with the reason when the cache no longer stands. A Left clear whose new `myField` equals the cached field appends " (the cached field)" (T7): fldMapNo flips inside the MAPJUMP tick (R1), so this Update-rate clear always runs before the new field's landing hook.
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
  - **On a refusal (below 0):** count it, and print C's refusal line with the old rule's outcome appended (one line per jump).
  - **On a pass (above 0):** `OwnPassBook` runs in its own try. On Pending it sets `_followWarpPending = -1`, `_followCommittedTo = dest`, calls `NoteMoveCommitted()` and `NetSyncFollowFade.Clear("own")`, and increments `converted`. Then `KeepOwnEntranceFor(dest)` runs if `OwnPassKeepsOwn`. Then the counters, the pass line, and `return true`.
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
// codes: Keep -1 (no change), Here -2 (not stored; counted; the nonce marked spent), None 0, Watched 1, OffField 2, Late 3

Int32 PinCaptureRule(Boolean spent, Boolean here, Int32 heldQuality, Boolean landSeen, Int32 frameNonce, Boolean frameOffField,
                     Int64 seqGap)
  // heldQuality / landSeen: the held entry for frameNonce, if any; seqGap: this frame's receive seq minus the last observed
  // frame's (1 = no unseen frame between them; -1 = no prior observation or the observed frame is not the latest received)
  frameNonce < 0                                -> Keep        (no section 4)
  spent                                         -> Keep        (T1: consumed, dropped, aged or refused here; until another nonce)
  heldQuality == None && here                   -> Here        (R4: I already stand on the announced field)
  frameOffField: heldQuality == OffField        -> Keep
                 heldQuality != None && landSeen -> Keep        (a battle's off-field frame after the host's landing never upgrades)
                 else                           -> OffField    (store; a same-nonce Watched/Late is upgraded)
  heldQuality != None                           -> Keep        (same nonce on a field: a later frame may be post-Main_Init)
  seqGap == 1                                   -> Watched     (T6: the first frame of the nonce that reached me)
  else                                          -> Late

Boolean PinOffFieldRule(Boolean haveSection7, Int32 hr)
  haveSection7 && (hr & HrOnField) == 0 && (hr & HrBattle) == 0
  // a battle frame is never off-field: R6 keeps section 4 through a battle on the intent field, and those frames are post-Main_Init

Boolean PinTargeted(Int32 pinField, Int32 pending, Int32 committed, Int32 warpedTo)
  pinField > 0 && (pinField == pending || pinField == committed || pinField == warpedTo)
Boolean PinDropOnNew(Int32 heldField, Boolean targeted, Int32 newField)
  heldField == newField ? true : !targeted
  // when a new nonce is stored: a held pin for another field survives only while a follow targets it (T5);
  // a held pin for the same field is superseded by the newer nonce

Int32 PinAgeRule(Boolean landSeen, Int32 sinceLandSeenMs, Int32 sinceCaptureMs)
  landSeen -> sinceLandSeenMs                                  (T6: the age counts from the host's landing as I saw it)
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

**The inputs, defined.**
- `frameOffField` = `PinOffFieldRule(section 7 present, HostFlagReads(flags))`: b3 (`HfOnField`) clear and b5 (`HfBattle`, the host's `gMode == 2`, `NetSyncClient.cs:6820-6821`) clear in this frame (`NetSyncDialog.cs:95`; `HostFlagReads`, `NetSyncClient.cs:6155-6165`). A frame with no section 7 reads false. The b5 term closes a hole found while applying R6: a `Main_Init` that starts a battle at once, with no load-window frame observed and the host's lane never naming the field, would otherwise let a battle frame upgrade the pin before `landSeen` is set.
- INFER: the out-of-band frame is built inside the MAPJUMP tick, where `_hostOnField` still holds the source field's value from the last `ScanHostOpenSet` (`NetSyncClient.cs:6878-6882`), so it carries b3 **set**. Only frames built between the old map's teardown and the new map's first live Update read b3 clear. Both kinds are pre-`Main_Init`. DP-UP and its reach clause measure how often an off-field frame is seen at all.
- `seqGap` uses the probe's `InSeq` (§ transport): when `ReferenceEquals(probe.InState, state)`, the observed frame's receive seq is `InSeq`; otherwise a newer payload landed between the read and the probe, and `seqGap` is -1. A guest main-thread stall (its own blocking `LoadLevel`, `SceneDirector.cs:394-402`) leaves frames received but unseen, so the first observed frame of the nonce reads Late unless it was built off-field (T6).
- `landSeen` (per held entry) is set at the first observation after capture of either a b3 rising edge (a b3-clear frame observed, then a b3-set frame), or the host's position lane naming the pin's field (`LastHostField == pinField`, set at `:2166` before `NoteHostFrame`). The lane term is needed because the out-of-band frame already reads b3 set and a fast load may show no b3-clear frame at all (INFER; `pin.land_seen_by` counts each term).
- `here` = `myField > 0 && secField == myField`.
- `fromWorld` = the landing comes from the world map, read as `ee.gMode == 3` at the landing hook, the same read `LandingFollowCandidate` takes (`NetSyncClient.cs:5757`). World rejoins commit at once and land 1-3 s later (`:5599-5615, 5638-5640`), straddling `PinMaxAgeMs`, so round 1 stages the latest frame there (R3).

### Call sites

- **Capture.** In `NoteHostFrame`, on a client, for each new frame:
  - read the probe's `InSeq` and compute `seqGap` against `_pinLastRecvSeq` (armed only after a first observation), then store this frame's seq;
  - update every held entry's `landSeen` (b3 rising edge or the lane);
  - if the frame carries a nonce different from `_pinSpentNonce`, clear `_pinSpentNonce` (T1: "until a different nonce arrives");
  - run `PinCaptureRule` with the held entry for the frame's nonce. On `Here`, count `pin.here` and mark the nonce spent. On a store of a NEW nonce, first run `PinDropOnNew` over the held entries (a dropped pin logs "dropped unused" and its nonce is spent), then store in the free slot: frame reference, nonce, field, quality, capture tick, `landSeen = false`. An upgrade keeps the entry's capture tick and records `last_upgrade_diff = StoryDiff(held, frame)`;
  - received frames are fresh arrays that nothing mutates (`NetSyncSocket.cs:436-439`), so keeping the reference is safe.
- **The map.** At most two entries `{field -> frame, nonce, quality, captureTick, landSeen, landSeenTick, sawOffField}`. One follow runs at a time, so at most one entry is targeted; after `PinDropOnNew` a new nonce always finds a slot.
- **`ApplyStoryImpl` (:896-947).** After the `host == null` return (:928), `Byte[] latest = host`:
  - `entry = the held entry for fldMapNo, or any held entry if none` (so `other` is counted);
  - `verdict = PinUseRule(PinLeverOld || _pinFaulted, fromWorld, entry.quality, entry.field, PinAgeRule(...), fld, out why)`, then `LandingFrames(verdict, entry.frame, latest, out story, out party, out dress)`;
  - when a pin was held for this field, compute `StoryDiff(pin, latest)` (the section-0 bytes that differ outside the 2032-2041 mask) and log the verdict;
  - **:929** `if (NetSyncState.ApplyStory(host))` becomes:
    ```
    Boolean ok = ReferenceEquals(story, latest) ? NetSyncState.ApplyStory(latest)          // [ff9mapkit netsync s164] byte-for-byte s163
                                                : NetSyncState.ApplyStorySplit(story, party);  // section 0 from the pin, sections 1-3 from the latest
    if (!ok && !ReferenceEquals(story, latest)) { <log "did not apply">; ok = NetSyncState.ApplyStory(latest); }
    if (ok) { ...the s163 body, unchanged... }
    ```
  - **`NetSyncState.ApplyStorySplit(Byte[] storyFrame, Byte[] partyFrame)`** is new, beside `ApplyStory` (`NetSyncState.cs:98-111`), which stays untouched: `applied = ApplyStoryTo(storyFrame, g)`; the same story-trace epoch; `if (applied) NetSyncParty.ParseSections(partyFrame)`. With both arguments equal it is `ApplyStory`.
  - **:938** `NetSyncSelfDress.ArmFromState(host)` is left as it is: the dress is always the latest frame, which is `host`.
  - With the lever at `old`, story == party == dress == latest, which is byte-for-byte s163.
  - `RestorePassEntrance` (:939) and `NoteLandingEntrance` (:879) are unchanged.
- **Consumption.** In `ApplyStoryBeforeEvents`, right after :877: `ConsumePinAt(fldMapNo)`. It runs on every load, whether or not the apply ran: each entry with `PinConsumed` true is removed and its nonce marked spent.
- **Clears:** `ResetIntentAndL1State` ("the co-op session reset"); `ResetGuestDedupForEpoch` ("the host epoch changed"): both drop every entry and mark spent the nonce on the latest received frame, so a section 4 still live across the reset is not re-captured (row c15); the exit ramp, before :1661, silently.
- **The selftest bench.** At the top of `ApplyStoryImpl`, `if (IsSelfTestRole) BenchPinLanding();`. It does nothing unless `swap pinbench` armed it. It runs the same `PinUseRule` and `LandingFrames` into a scratch buffer and copies only the marker flag's byte into the live array, then parses the bench's party frame through the real `ParseSections` (P-PARTY).
- **New fields:**
  - the two-entry map, `_pinSpentNonce`, `_pinLastRecvSeq`, `_pinObsArmed`;
  - counters and last-use fields;
  - `_pinFaulted`, sticky, which reads as `old`.

### Log lines (behaviour)

- `[NetSync] story pin: intent N's frame kept for field D (watched|built off-field) (t T ms)`
- `[NetSync] story pin: intent N's frame for field D upgraded to one built off-field (the story differs at B bytes) (t T ms)`
- `[NetSync] story pin: intent N's first frame came after K unseen frames -- not kept (a landing on field D stages the latest frame) (t T ms)`
- `[NetSync] story pin: intent N names field D, where I already stand -- not kept (t T ms)`
- `[NetSync] story pin: intent N0's frame for field D0 dropped unused (intent N arrived) (t T ms)`
- `[NetSync] story pin: field D stages intent N's frame for its story, the latest frame for its party and dress (age A ms; the latest differs at B story bytes) (t T ms)`
- `[NetSync] story pin: field D stages the latest frame -- <why> (t T ms)`, where why is one of:
  - `the pin is A ms old (over 2500)`
  - `intent N's first frame came late`
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
                     Boolean battleOnIntent, Boolean bodyThere)
  oldRule -> onIntentField ? EndOld : Keep                    (s163's :2095, verbatim)
  landing == Elsewhere -> EndElsewhere
  landing == Pending -> sinceEmitMs >= IntentLoadCapMs ? EndCap : Keep     (onIntentField ignored here: the R1 fix)
  battleOnIntent -> sinceEmitMs >= IntentLoadCapMs ? EndCap : Keep         (R6: a battle that started on the intent field)
  !onIntentField -> EndLeft                                   (the world map, the title, a battle elsewhere)
  bodyThere && sinceEmitMs >= IntentMinLifeMs && sinceLandMs >= LandTailMs -> EndStands      (T13)
  else -> Keep
Boolean BodyThereRule(Boolean inScope, Boolean haveActor, Boolean haveMapActor)   inScope && haveActor && haveMapActor   (F14)
```

In one line: section 4 lives from the emit until the host has loaded the announced field, its body stands there, 2 s have passed since the emit and 1 s since the landing. It ends early when the host lands elsewhere, leaves after landing (a battle on the intent field does not count as leaving, up to the cap), or never lands within 10 s.

**The inputs, defined.**
- `onIntentField = onField && fld == _intentField` (`onField` as computed at :1684).
- `sinceLandMs = sinceEmitMs - _intentLandedMs` once landed.
- `battleOnIntent = ee != null && ee.gMode == 2 && fld == _intentField`: the host's own battle read, the one section 7's b5 uses (`NetSyncClient.cs:6820-6821`). `fldMapNo` keeps the field through a battle (`HonoluluFieldMain.cs:448-450` writes `btlMapNo`). R6 is a SelfTest-only claim in round 1 (rows `r-battle`, `r-battle-cap`, `r-battle-old`): no field whose `Main_Init` starts a battle at once is pinned, so there is no DL-BATTLE duo leg.
- `bodyThere = BodyThereRule(inScope, actor != null, actor.fieldMapActor != null)` with `actor = ee.GetControlChar() as Actor`, read the way the host path reads `local` (:2073-2085). On the host it is `local != null` after :2085. On the selftest role the same rule runs inside the selftest branch, which never reaches :2073 (it returns at :2041) (F14).

**Order independence, proven without a lever (T2).** Two pure rows carry it: `r-order` (act, the emit frame itself, landing Pending, the host already reading the intent field with its body there: Keep) and `r-order-old` (the same input under s163's rule: EndOld, the R1 hole). The act rule never reads "is the old map alive", so it gives the same answer under either Unity order and at any frame rate. The in-game measurement is DA-PROBE on the DESK and REST MAPJUMP legs under `swap life old`, which records `last_life_ms`, `intent.host_fps` and `intent.emit_dt_us` for every scripted exit.

**Chosen over "about 2 s, or until the new field reports, whichever comes first"** (that rule is the mutant `life_body_or_min`):
- The guest's deferrals (a menu, the s144 hold, the s161 holds, `FieldTransitionNow`; :7162-7187) must outlive the host's landing to fire by intent, which is what the comment at :7124 already promises. `LandTailMs` guarantees that even when the host's load takes 2 s or more (T13).
- The cost is 6 bytes per frame.

### Call sites

- **L1, `EmitFieldIntentIfHost`:**
  - before :6743, an intent still active ends as `next` and logs "replaced";
  - after :6745, set `_intentEmitTick`, `_intentLanding = Pending`, `_intentSite = site`, and `_intentLandedMs` and `_intentBodyMs` to -1;
  - after :6748, `if (!LifeOld) _storyTick = Environment.TickCount;` (consistency with :7057).
- **L2, `ApplyStoryBeforeEvents`:** the first statement inside `if (_instance != null)` (:872), before :873, is `NoteIntentLanding(fldMapNo)`.
  - It runs on the host, or on the selftest role while `swap lifebench` is armed.
  - It runs before `StartEvents`, so before the host's `Main_Init`.
  - World emits already name `ForkSiblingField(dest)` (`DoEventCode.cs:1040`).
- **L3, `Update`:** :2095-2096 becomes `if (_intentActive) HostIntentLifeStep(fld, onField, ee, local != null);`, at the same position, before `HostTick`, `UpdateHostScene` and the publish (:2097-2111). So no frame built after an end carries section 4.
  - It records `_intentBodyMs` at the first Update with the body on the field after landing.
  - A fault logs once and falls back to the s163 clause for this intent.
- **L4, the selftest branch:** while `swap lifebench` is armed, the same step runs before :2039 with the branch's own `onField` and `BodyThereRule(...)`.
- **L5:** `ResetIntentAndL1State` resets the life fields and ends an active intent as `reset`.
- **New fields:** `_intentEmitTick`, `_intentLanding`, `_intentLandedMs`, `_intentBodyMs`, `_intentSite`, `_intentFaulted`, plus counters.

**Other readers of section 4, checked against the longer life:**
- the nonce dedup (:7143);
- the same-field reload (:7145-7149);
- `HostElsewhere` (:7752-7753);
- `HostIntentAndEntranceNow` and `DestJump` (:7075-7090; `NetSyncAte.cs:259-271`);
- the s144 world branch (:7150-7161): a refused world arm defers with the nonce unmarked (:7158-7159) and can now fire up to 2-3 s after the host's body stands on D, where the serial floor took over after about 0.4 s before. `coop_world_wait`, `coop_world_battle` and `coop_world_party_duo` join the regression gates for this (R3);
- the `coop_peer` decoders (`coop_peer.py:2539-2553`);
- PIN's capture: frames during a battle on the intent field carry nonce n with b3 clear; `PinOffFieldRule` reads them as not off-field (b5 set, row o3), and the `landSeen` term also keeps them from upgrading a pin (row c18).

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
  - `a battle on it outlasted 10 s`
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
Int32 DueRule(Int32 path, Boolean timerOut, Int32 view, Int32 blackTicks, Int32 grace, Int32 backlogNow, Boolean ringAhead, Int32 lever)
  path != Fast -> timerOut ? Timer : Wait
  held = (backlogNow != None || ringAhead) && lever not in {NoGate, NoRecheck}     (BkUnknown and an unmerged ring hold: T9)
  held -> timerOut ? Recheck : Wait
  view == Black && blackTicks >= grace -> Black (also when timerOut);  else timerOut ? Fallback : Wait
  invariant (the s42 never-abandon law): timerOut never yields Wait
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

**Why `Due` also holds on an unmerged ring (T9).** `Due` runs at the top of `Update` (:1668), so `BacklogNow` reads the inbox merged by the PREVIOUS Update's dialogue pass (:2176). A host event that rode in with this Update's frame is not merged yet. `_dlg.RingAhead` (`NetSyncDialog.cs:2214-2216`) says exactly that, and s161 already defers the follow's START one Update on it (`NetSyncClient.cs:7172-7179`). Counting it as held costs at most one Update.

**Why the grace is 3 game ticks (T4).** Within one main-loop tick `ServiceEvents` runs before `ServiceFade` (`HonoluluFieldMain.cs:242, 298`). A stock exit runs `FadeFilter(6,24)` in tick t0's `ServiceEvents`; the slot first reads black after the 24th `ServiceFade`, at the end of tick t0+23 (`SceneDirector.cs:653-663`: `_curFrame` steps once per call and the target colour is exact at call 24). The script's `Wait(25)` then resumes it in tick t0+25 (INFER: the resume tick of `Wait(n)` relative to the issuing tick), whose `ServiceEvents` runs `Field(N)` and whose `changeScene` starts the load. `BlackTicksRule` arms in the first `Update` after t0+23 and counts `KeyTick`, which steps once per `ServiceEvents` (`EventEngine.cs:120`, `NetSyncField.cs:939`). So the copy's own `Field()` lands 2 ticks after the first black read. A grace of 3 lets a `Field()` up to one tick late still win; the commit-to-changeScene law (§C) covers a `Field()` in the tick after the commit. DF-FLASH's action and DC-WON's `follow_won` count on DESK (359's `Main_11`: `FadeFilter(6,24)`, `Wait(25)`, `Field(351)`, `test2_102.txt:290-301`) settle the INFER. The tick count scales with the booster and stops while paused. The grace is 0 when we ran the fade ourselves, because then the copy is not exiting.

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
  - `Due` reads `_dlg.RingAhead` with the backlog. It latches its first non-Wait verdict and its swap-clock time (`due_t`) for the follow, so A's delay can hold it without the verdict being re-judged. It logs the due line once.
  - `ServiceFollowWarp` runs *before* the enabled gate (:1664-1669). With `!_enabled`, a null `_dlg` or any fault, `Due` returns `timerOut ? Timer : Wait`, which is today's behaviour.
  - The s154 guard and the write are unchanged. `NetSyncFollowFade.Ended(mapNo, due)` records `last` right after the guard's step try (:6627).
- **`NetSyncFollowFade.Clear(by)`** runs where a pending follow ends without a commit: `NoteFieldLanding` (:5810, "landing"), C's conversion ("own"), `NoteGuestWorldJump`'s world-exit cancel (:5854, "world": a following copy's own `WorldMap()` inside the fade, `NetSyncClient.cs:5849-5857`), and `TitleTick` (:5188, "title"). No session reset ends a follow: by the s42 rule a follow in flight always finishes (`NetSyncClient.cs:1664-1668`) (T14, R7).
- **Per-follow statics** (read only while `_path >= 0`): `_path`, `_action`, `_frames`, `_viewStart`, `_leftStart`, `_backlogStart`, `_startKeyTick`, `_startMs`, `_blackArmed`, `_blackSince`, `_reasserted`, `_held`, `_dueLatched`, `_dueT`. There are also the last-follow fields and the counters.

**Interactions.**
- **s154:** the start gates are unchanged, and the commit guard runs on every non-Wait verdict.
- **s163:** while the mirror stands, 12 ticks at 3x is about 133 ms.
- **Paused mid-fade:** ticks stop, and the fallback equals today. With `Time.timeScale` 0 the timer stops too, as today.
- **Untouched:** s144's world rejoin, and the s158/s162 landing paths.

### Log lines (behaviour)

- **Fast start:** `[NetSync] follow fade: to field D -- fast: the screen reads <view>[ (L ticks left)]; <joining its own fade (no re-init) | hurrying it to black in n ticks from where it is (no flash) | fading to black in n ticks>; the commit waits for black (no later than 0.9 s) (t T ms)`
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
  - `the screen reads black[ after the 3-tick grace]`
  - `today's 0.9 s timer`
  - `the 0.9 s fallback: the fade never read black (<view>, darkest channel c)`
  - `today's 0.9 s timer: a backlog rose mid-fade (<reason>)`
- **Backlog mid-fade:** `[NetSync] follow fade: a backlog rose mid-fade on field F (<reason>) -- the commit waits for today's 0.9 s timer (t T ms)`. The reasons gain `host events not merged here yet` for a held ring.
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
| `clear` | none | any | Every lever back to act, stamps on, delay 0, hostctl on, bench state forgotten |
| `hostctl` | `off\|on` | selftest | B's bench host: section 7 with b1 and b0 clear (it stands here with its control off and no scene) |
| `intent` | `<field>` | selftest, needs `bench 1` | Section 4 through the real codec into the seen record and the bench cache, then `DebugInjectIntentImpl` (:7239-7289), which starts a real follow. It captures no pin |
| `cache` | `<field>` | selftest | Section 4 through the real codec into C's cache only (src my field, `host_from` -1, `bench` true) |
| `pinbench` | `<field> <flag> [age <ms>] [skip <n> [offfield]] [party <slot> <char>] [to <field>]` | selftest, needs `bench 1` | Frame A = `SnapshotAll()` plus section 4 through the real encoder and the real `PinCaptureRule`. `skip <n>` makes A's receive seq jump by n + 1 (n unseen frames: Late unless `offfield`); `age <ms>` marks the host's landing seen that long ago. Frame B = a copy of A with `<flag>` set, and with party slot `<slot>` set to CharacterId `<char>` when `party` is given, standing in as the latest frame. Then `StartFollowWarp` |
| `lifebench` | `<field>` | selftest | A bench emit (field, nonce, active, tick, Pending, site `bench`) with no socket, then a debug warp. The hook and the per-Update step run in the selftest branch, before :2039 |
| `blackout` | `<1-255>\|off` | selftest | `InitFade(Sub, n, white)` stands in for the copy's own `FadeFilter`. `off` runs `InitFade(Sub, 1, black)` |

**Refusal order.** For a known op the role comes first, as in s163's `speed host`:
1. An unknown op gets the usage line: `netsync swap: expected stamps on|off or clear (any role); delay <0-2000>, orphan act|old, own act|old|nocache, pin act|old or fade act|old|long|nogate|norecheck|nohurry (a client or the selftest role); life act|old (the host or the selftest role); hostctl off|on, intent <field>, cache <field>, pinbench <field> <flag> [age <ms>] [skip <n> [offfield]] [party <slot> <char>] [to <field>], lifebench <field> or blackout <1-255>|off (the selftest role)`
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
```

Every bench op acts only on `IsSelfTestRole`.

**Release.** `NetSyncSwap.HarnessRelease()` runs from `NetSyncBattle.HarnessReleaseBench` right after s163's `NetSyncSpeed.HarnessRelease()` (`NetSyncBattle.cs:6840`), on every role. `HarnessReleaseBench` runs on every `HarnessSelfTest(false)` above its forced-role return (`NetSyncClient.cs:9403-9407`): disarm, fault, `reset`, and a release deferred to a harness diorama's teardown (`HarnessAgent.cs:2353-2361`).
- It sets everything to act, forgets the bench cache, the pin bench and the life bench, and turns the bench host's control back on.
- A blackout is undone with `InitFade(Sub, 1, black)`.
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
- `[NetSync] harness: swap CLEAR -- every lever act, stamps on, delay 0, the bench host's control on, bench state forgotten`
- `[NetSync] harness: swap hostctl OFF -- the bench host stands on my field with its control off, no scene (section 7 b1 and b0 clear)` and `... ON`
- `[NetSync] harness: swap intent -- a bench host's section 4 for field D (nonce N) through the real codec (the selftest role)`
- `[NetSync] harness: swap cache -- section 4 = field D nonce N through the real codec, cached on field F`
- `[NetSync] harness: swap pinbench -- intent N's frame for field D through the real codec (flag B: pin P, latest L[; party slot S: pin C0, latest C1][; K unseen frames][; landing seen A ms ago])`
- `[NetSync] harness: swap lifebench -- a bench emit for field D (nonce N), no socket`
- `[NetSync] harness: swap blackout N -- the fade slot heads to black in N ticks (a copy's own FadeFilter stand-in)` and `... swap blackout OFF -- the fade slot back to visible`
- Release: `[NetSync] harness: swap levers released (every lever act, stamps on, delay 0, the bench host's control on, bench state forgotten)`

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
  "levers": {"stamps":null, "delay_ms":0, "orphan":null, "own":null, "pin":null, "life":null, "fade":null, "hostctl_off":false},
  "open": false,
  "last":   {"id":0, "role":null, "from":-1, "dest":-1, "state":null, "open_by":null, "open_t":-1,
             "emit_t":-1, "nonce":-1, "seen_t":-1, "arrived_t":-1, "seen_copies":0,
             "follow_t":-1, "follow_via":null, "follows":0,
             "own_t":-1, "own_dest":-1, "own_verdict":null, "own_why":null, "owns":0, "bounces":0,
             "due_t":-1, "commit_t":-1, "commit_field":-1, "commit_why":null, "delay_ms":0, "drop_t":-1, "drop_why":null,
             "reloads":0, "reload_t":-1, "land_t":-1, "land_field":-1, "land_via":null, "story":null,
             "fade_path":null, "fade_ticks":-1, "line_t":-1, "line_win":-1, "line_text":-1, "close_t":-1, "close_why":null},
  "seen":   {"nonce":-1, "field":-1, "src":-1, "host_from":-1, "first_t":-1, "last_t":-1, "arrived_t":-1, "recv_seq":-1, "copies":0},
  "intent": {"active":false, "field":-1, "nonce":-1, "site":null, "emit_t":-1, "age_ms":-1, "host_fps":-1, "emit_dt_us":-1,
             "landing":null, "landed_ms":-1, "body_ms":-1,
             "wire":false, "frames":0, "updates":0, "sends":0, "first_sent_t":-1, "last_sent_t":-1, "oob":null,
             "end_t":-1, "last_end":null, "last_life_ms":-1, "last_site":null, "emits":0, "replaced":0, "oob_lost":0, "short":0,
             "ends":{"stands":0,"left":0,"elsewhere":0,"cap":0,"old":0,"next":0,"reset":0}, "faults":0},
  "slot":   {"set_seq":-1, "sent_seq":-1, "sends":-1, "unsent":-1, "in_seq":-1},
  "orphan": {"host_holds":false, "holding":0, "holds":0, "relocks":0, "last_hold_ms":-1, "last_end":null, "faults":0},
  "own":    {"passes":0, "by":{"pending":0,"committed":0,"intent":0,"cache":0}, "converted":0,
             "refused":{"world":0,"ate":0}, "host_lane":-1,
             "last":{"dest":-1, "from":-1, "lane":-1, "term":null, "keep_own":false},
             "cache":{"field":-1, "nonce":-1, "src":-1, "host_from":-1, "age_ms":-1, "stands":false, "bench":false,
                      "writes":0, "clears":0, "last_clear":null}, "faults":0},
  "pin":    {"held":[], "spent":-1, "captures":0, "late":0, "upgrades":0, "last_upgrade_diff":-1, "dropped":0, "here":0,
             "used":0, "aged":0, "other":0, "world":0, "lever_latest":0, "land_seen_by":{"edge":0,"lane":0},
             "last_use":null, "last_use_field":-1, "last_use_age_ms":-1, "last_diff":-1, "last_diff_first":-1, "last_party":null,
             "faults":0, "bench":{"armed":false, "flag":-1, "chosen":null, "party_slot":-1, "party_char":-1}},
  "fade":   {"view_now":null, "mode_now":null, "cur_now":-1, "left_now":-1, "backlog_now":null, "ring_ahead":false,
             "path":null, "action":null, "frames":-1, "view_start":null, "left_start":-1, "backlog_start":null,
             "age_ms":-1, "age_ticks":-1, "black_ticks":-1, "reasserted":false, "held":false,
             "last":{"field":-1, "path":null, "action":null, "by":null, "due_t":-1, "ms":-1, "ticks":-1, "frames":-1,
                     "view_start":null, "backlog_start":null},
             "starts":{"fast":0,"backlog":0,"old":0,"kick":0},
             "ends":{"black":0,"timer":0,"fallback":0,"recheck":0,"landing":0,"own":0,"world":0,"title":0},
             "reasserts":0, "faults":0},
  "counts": {"transitions":0, "landings":0, "own_jumps":0, "bounces":0, "follow_won":0,
             "closed":{"line":0,"window":0,"stale":0,"superseded":0,"next":0,"reset":0}},
  "faults":0, "last_fault":null, "selftest":null
}
```

Each `pin.held` entry is `{"field", "nonce", "quality", "land_seen", "age_ms", "capture_ms"}` (`age_ms` = `PinAgeRule` now). `fade.last.ms` and `fade.last.ticks` measure the follow's start to its **due** verdict (`fade.last.due_t`); the commit is `last.commit_t`, and `last.commit_t - last.due_t` is A's delay (F6).

**Value vocabularies:**

| Key | Values |
|---|---|
| `clock.src` | `qpc`, `stopwatch` |
| `last.state` | `open`, `landed`, `done` |
| `last.follow_via` | `intent`, `serial` |
| `last.story` | `pin`, `latest` |
| `intent.site`, `intent.last_site` | `mapjump`, `debugwarp`, `bench` |
| `intent.landing` | `pending`, `on_intent`, `elsewhere` |
| `pin.held[].quality` | `watched`, `offfield`, `late` |
| `pin.last_use` | `pin`, `none`, `other`, `late`, `aged`, `world`, `lever`, `skipped_stale` |
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
- `frameWithIntent` is supplied by `NetSyncClient`. It saves and restores `_intentActive`, `_intentField` and `_intentNonce` in a try/finally around `BuildStateFrame(true, true)`, the s163 delegate precedent (:1948).
- D+E's rows live in `NetSyncFollowFade.SelfTestRows(ref rows, ref fails)` and are called from it. C's `quiet_equals_loud` sweep calls `NetSyncAte`'s internal `HoldVerdict` and `HoldsFollowQuiet`.

The proof block (after :1950) gets one new last line:

```
[NetSync] field swap selftest: OK (N rows, M mutants caught, clock qpc|stopwatch H Hz high-res|low-res, line window 10000 ms,
span 30000 ms, cache 2000 ms, intent life 2000 ms / land tail 1000 ms / cap 10000 ms, pin age 2500 ms / blind 10000 ms,
fade 12 / 24 ticks / 900 ms, join grace 3 ticks, black floor 248, ahead 3000 ms)
```

- A failure reads `FAIL (row <id>)` or `FAIL (mutant <id> survived)`.
- The clock source and `hires` are reported and never fail the line.
- The kit regex pins every constant and captures N, M, the source, H and the resolution.
- The dialogue selftest's `KeyScript` row changes as described under §B. Its detail text is unchanged.

| Item | Rules | Rows (about) | Mutants |
|---|---|---|---|
| A | TicksToMs, stamp, parse, waited, JoinRule, OpenClosesRule, CloseRule, LandViaRule, DelayRule, OobVerdict, SeenRule, slot (live on a real `new NetSyncFrames()`), line builders | 100 | 27 |
| B | OrphanSettled ×16, HostHoldsRule ×8, the composite `OrphanStep(OrphanSettled)` ×12 under act and old, CtlHoldKind, HoldEndWhy, OrphanSinceRule, scenarios S1-S5 | 62 | 11 |
| C | OwnFieldPassRule, OwnJumpVerdictRule, IntentCacheStep, IntentCacheVerdict, OwnPassBook, OwnPassKeepsOwn, the s154 sequence rows, `quiet_equals_loud`, the codec (live) | 79 | 32 |
| LIFE | IntentLifeRule, BodyThereRule, IntentLandingStep, live `frame_carries_4` | 30 | 15 |
| PIN | PinCaptureRule, PinOffFieldRule, PinUseRule, PinConsumed, PinDropOnNew, PinTargeted, PinAgeRule, LandingFrames, one sequence row, live `pin_applies_verbatim` | 53 | 22 |
| D+E | View, Backlog with its cascade, counting, Path, Action, Grace, BlackTicks, Due with the `never_past_the_timer` sweep, Reassert, live `slot_reads` and `today_constants` | 103 | 42 |
| **Total** | | **about 427** | **about 149** |

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
- **slot** (live on a real `new NetSyncFrames()`): `oob_sent` (`SetStateWatched(A)`, Collect → FromSent, WatchSends 1), `oob_overwritten` (`SetStateWatched(A)`, Set B → FromReplaced, not FromSent), `window_closed` (… `WatchStateSeqs(from, seq + 1)`, Set C, Collect → WatchSends unchanged), `unsent_count` (Set A, Set B → Unsent 1), `watched_is_atomic` (`SetStateWatched` returns the seq it armed: `WatchFrom == SetSeq` read back in one probe), `in_seq_counts` (two Accepts of TypeState → `InSeq` +2).
- **lines:** each builder against its exemplar (landed, commit, kick commit, own pass, own bounce, both close lines, clock), and each builder's `off` row.

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
- **Scenarios** (deltas only, across the Int32 tick wrap; `SettleClock` and the composite stepped per 100 ms tick): S1 the leap (the host lands co-located, control off, no scene; under act never ToOrphaned to t0+30000, under old ToOrphaned at t0+OrphanGraceMs); S2 control back at t1 (ToOrphaned on t1's tick, Confirm at t1+AutoReadMs); S3 one blip (no Confirm through t1+AutoReadMs+2000); S4 a scene rising during the hold (Busy, then Event); **S5 repeated blips** (an orphaned line, its read clock from t0; control off for 0.5 s every 1.5 s for 6 s: Confirm no later than t0 + AutoReadMs + the summed held time).

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

### C: rows and mutants

Rows (my field 351, dest 352, another 350, a third 353):
- **OwnFieldPassRule:** `pass.pending`, `pass.committed`, `pass.intent`, `pass.cache`; `order.pending_first` (all four match), `order.committed_before_intent`, `order.intent_before_cache`; `none.nothing`, `none.pending_other_field` (pending 350, dest 352: the C2 guard), `none.intent_other_field`, `none.cache_other_field`, `none.cache_not_standing`, `none.kick` (pending 352 with kick), `none.my_field`, `none.ending` (dest 16000, live 16000), `none.unusable`, `none.dest_0`, `none.dest_65535`, `none.not_following`; `lever.off_pending`, `lever.off_intent`, `lever.nocache_cache`, `lever.nocache_keeps_pending`, `lever.nocache_keeps_intent`; `refuse.world`, `refuse.ate`, `refuse.world_before_ate`, `refuse.only_on_a_match` (holds set, no term → None), `refuse.lever_off_quiet` (off with a hold and a term → None).
- **OwnJumpVerdictRule, `commit_then_own_same_tick` (T4):** s1 (act, committed 352, pending -1, lane 351, own `Field(352)` → Pass committed: one load), s2 (the same under `own old` → Bounce), s3 (pending 352 → Pass pending; the book converts), s4 (committed 352, own `Field(353)`, lane 351 → Bounce: the divergent copy, risk 19), s5 (committed 352, lane 352, own `Field(352)` → Pass committed, not host-field: C decides before the lane).
- **IntentCacheStep:** `write.first`, `write.new_nonce`, `write.wrapped_nonce` (255 → 0), `write.after_reset` (nonce -1 → 0); `keep.same_nonce`, `keep.spent_nonce`, `keep.no_section`; `skip.my_field`, `skip.supersedes`, `skip.ending`, `skip.no_field` (myField -1).
- **IntentCacheVerdict:** `stands.stale_source_frame` (lane = src), `stands.lane_0`, `stands.lane_65535`, `stands.lane_minus1`, `stands.lane_on_cached`, `stands.lagging_guest_stale_source` (src 349, hostFrom 351, lane 351), `stands.hostfrom_unknown_src_exempt`; `host_past` (lane 353), `left` (myField 352), `aged_at_cap` (2000), `stands_below_cap` (1999), `none`, `negative_age`; `order.left_before_aged`, `order.aged_before_host_past`.
- **OwnPassBook and OwnPassKeepsOwn:** `book.pending_converts`, `book.pending_bends`, `book.committed_unchanged`, `book.intent_no_bend`, `book.cache_no_bend`, `book.refused_no_change`; `entrance.host_by_default`, `entrance.exit_hold_keeps_own`, `entrance.none_never`.
- **Sequence rows** (the real s154 rules, after the book): `seq.pending_pass_lands_clean` (`FollowLandingStep(352, -1, 352, 352, false)` → `LandNone`, keep 352), `seq.commit_idle`, `seq.overwrite_still_rearms` (landing on 351 → `LandLatchVoid`, re-arm 352), `seq.intent_pass_landing`, `seq.kick_never_rearms_follow`.
- **`quiet_equals_loud`** (F7): the full grid through `HoldVerdict` and `HoldsFollowQuiet`, equal at every point (one row).
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

`IntentLifeRule(oldRule, sinceEmit, sinceLand, landing, onIntentField, battleOnIntent, bodyThere)`; P = Pending, On = OnIntent, E = Elsewhere; "-" = not read.

| Row | Inputs | Expected |
|---|---|---|
| r1 | old, 0, -, P, T, F, F | EndOld |
| r2 | old, 0, -, P, F, F, F | Keep |
| r3 (R1: the shutdown frame) | act, 16, -, P, T, F, T | Keep |
| r4 | act, 9999, -, P, F, F, F | Keep |
| r5 | act, 10000, -, P, F, F, F | EndCap |
| r6 | act, 0, -, E, F, F, F | EndElsewhere |
| r7 | act, 1999, 1500, On, T, F, T | Keep |
| r8 | act, 2000, 1000, On, T, F, T | EndStands |
| r9 | act, 5000, 4000, On, T, F, F | Keep |
| r9b | act, 30000, 29000, On, T, F, F | Keep |
| r10 | act, 500, 100, On, F, F, F | EndLeft |
| r11 | act, 30000, 29000, On, T, F, T | EndStands |
| r12 | act, 100, 50, On, F, F, T | EndLeft |
| r-slowload (T13) | act, 2300, 0, On, T, F, T | Keep |
| r-slowload2 (T13) | act, 3300, 1000, On, T, F, T | EndStands |
| r-battle (R6) | act, 1500, 600, On, F, T, F | Keep |
| r-battle-cap (R6) | act, 10000, 9000, On, F, T, F | EndCap |
| r-battle-old (R6) | old, 1500, -, On, F, T, F | Keep |
| r-order (T2) | act, 0, -, P, T, F, T | Keep |
| r-order-old (T2) | old, 0, -, P, T, F, T | EndOld (the R1 hole) |

`BodyThereRule(inScope, haveActor, haveMapActor)` (F14, the `r-bench` rows): b1 (T, T, T) → T; b2 (T, T, F) → F (the player actor before its `fieldMapActor` binds); b3 (F, T, T) → F; b4 (T, F, F) → F.

`IntentLandingStep(landing, active, intentField, loadedField)`: l1 (P, T, D, D) → On; l2 (P, T, D, E) → Elsewhere; l3 (On, T, D, E) → On; l4 (P, F, D, D) → P; l5 (Elsewhere, T, D, D) → Elsewhere.

Live: `live.frame_carries_4`: `BuildStateFrame(true, true)` with `_intentActive` true reads back section 4 (field, nonce) and a section 7 whose b3 parses through `HostFlagReads`; it reads back no section 4 after the step ends the intent.

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
| `life_left_ignored` | no "left" clause | r10, r12 |
| `life_no_land_tail` | no 1 s since the landing (rev 1) | r-slowload |
| `life_battle_left` | a battle on the intent field ends it as left (rev 1) | r-battle |
| `life_battle_no_cap` | a battle keeps it with no cap | r-battle-cap |
| `body_any_actor` | `bodyThere` without the `fieldMapActor` | b2 |
| `landing_any_load_is_intent` | any load counts as the intent field | l2 |
| `landing_rearms` | a later load re-evaluates the landing | l3 |

### PIN: rows and mutants

`PinCaptureRule(spent, here, heldQuality, landSeen, frameNonce, frameOffField, seqGap)`; W = Watched, Off = OffField; n = the frame's nonce.

| Row | Inputs | Expected |
|---|---|---|
| c1 | F, F, None, F, -1, F, 1 | Keep (no section 4) |
| c2 | F, F, None, F, n, F, 1 | Watched |
| c3 (T6) | F, F, None, F, n, F, 2 | Late (one unseen frame) |
| c4 (T6) | F, F, None, F, n, F, -1 | Late (no prior observation) |
| c5 (T6) | F, F, None, F, n, T, 9 | OffField (a stall, but built off-field) |
| c6 | F, F, W, F, n, F, 1 | Keep |
| c7 | F, F, W, F, n, T, 1 | OffField (upgrade) |
| c8 | F, F, Late, F, n, T, 1 | OffField |
| c9 | F, F, Late, F, n, F, 1 | Keep |
| c10 | F, F, Off, F, n, T, 1 | Keep |
| c11 | F, F, Off, F, n, F, 1 | Keep |
| c12 | F, F, None, F, n2, F, 1 (a new nonce after a held Off of n) | Watched |
| c13 (T1) | T, F, None, F, n, F, 1 (after its consumption) | Keep |
| c14 (T1) | T, F, None, F, n, T, 1 | Keep (spent beats off-field) |
| c15 (T1) | T, F, None, F, n, F, 1 (after an epoch reset, section 4 still live) | Keep |
| c16 (R4) | F, T, None, F, n, F, 1 | Here |
| c17 (R4) | F, T, None, F, n, T, 1 | Here |
| c18 (R6 × T6) | F, F, W, T, n, T, 1 (a battle's off-field frame after the landing) | Keep |

`PinOffFieldRule(haveSection7, hr)`: o1 (T, 0) → T; o2 (T, HrOnField) → F; o3 (T, HrBattle) → F (a battle frame is never off-field); o4 (F, 0) → F.

`PinUseRule(leverOld, fromWorld, quality, pinField, ageMs, fld)`:

| Row | Inputs | Expected |
|---|---|---|
| u1 | T, F, W, D, 500, D | Latest / lever |
| u2 | F, F, None, -1, -1, D | Latest / none |
| u3 | F, F, W, D, 1200, D | Pin |
| u4 | F, F, Off, D, 2500, D | Pin |
| u5 | F, F, Off, D, 2501, D | Latest / aged |
| u6 | F, F, W, D, 500, E | Latest / other |
| u7 | F, F, Late, D, 500, D | Latest / late |
| u8 | F, F, W, D, -1, D | Latest / aged |
| u9 (R3) | F, T, W, D, 500, D | Latest / world |
| u10 | T, T, W, D, 500, D | Latest / lever (the lever first) |

`PinConsumed(quality, pinField, fld)`: k1 (W, D, D) → T; k2 (W, D, E) → F (the bounce reload keeps the pin); k3 (Late, D, D) → T; k4 (None, -1, D) → F.

`PinDropOnNew(heldField, targeted, newField)` (T5): d1 (D, T, E) → F (the chain: a follow to D is pending when E's nonce arrives; both kept); d2 (D, F, E) → T; d3 (D, T, D) → T (superseded by a newer nonce for the same field); d4 (D, F, D) → T.

`PinTargeted(pinField, pending, committed, warpedTo)` (T5): t1 (D, D, -1, -1) → T; t2 (D, -1, D, -1) → T; t3 (D, -1, -1, D) → T; t4 (D, E, E, E) → F; t5 (-1, -1, -1, -1) → F.

`PinAgeRule(landSeen, sinceLandSeen, sinceCapture)` (T6): a1 (T, 1200, 3000) → 1200; a2 (F, -, 2000) → 0; a3 (F, -, 10000) → 10000; a4 (T, 2600, 2650) → 2600.

`LandingFrames` (R1): f1 Pin → story = pin, party = latest, dress = latest; f2 Latest → story = party = dress = latest.

Sequence: `seq.upgrade_keeps_capture_tick`: Watched at t0, an off-field upgrade at t0+5000, the landing never seen, the guest's landing at t0+10100 → age 10100 (blind) → Latest / aged.

Live: `live.pin_applies_verbatim`: `ApplyStoryTo(the pinned real frame, scratch)` equals its section 0 outside the mask, and `StoryDiff` of a frame against itself is 0.

| Mutant | Restores | Caught by |
|---|---|---|
| `pin_latest_always` | today | u3 |
| `pin_last_frame` | the newest frame of a nonce wins | c6 |
| `pin_no_gap_guard` | no receive-seq check | c3 |
| `pin_offfield_blind` | b3 ignored | c5, c7, c8 |
| `pin_any_field` | the field ignored | u6 |
| `pin_never_ages` | the age ignored | u5 |
| `pin_late_used` | Late treated as Watched | u7 |
| `pin_consumed_anywhere` | consumed at any landing | k2 |
| `pin_upgrade_resets_age` | an upgrade restamps the capture tick | seq.upgrade_keeps_capture_tick |
| `dress_follows_story` | the dress from the pinned frame | f1 |
| `party_follows_story` | the party wraps from the pinned frame (rev 1) | f1 |
| `pin_offfield_replaces_offfield` | churn between off-field frames | c10 |
| `pin_recapture_after_consume` | no spent-nonce memory (rev 1) | c13 |
| `pin_single_slot` | one slot: a new nonce always replaces | d1 |
| `pin_target_pending_only` | only a pending follow targets a field | t2, t3 |
| `pin_age_from_capture` | the age from the capture (rev 1) | a1, a2 |
| `pin_blind_never_ages` | no backstop when the landing is never seen | a3 |
| `pin_upgrade_after_landing` | an off-field frame upgrades after the landing | c18 |
| `pin_kept_when_here` | a pin for the field I stand on | c16 |
| `pin_used_from_world` | the pin used at a world-rejoin landing | u9 |
| `pin_here_after_offfield` | `here` checked after the off-field upgrade | c17 |
| `pin_battle_is_offfield` | a battle frame (b3 clear, b5 set) counts as off-field | o3 |

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

`DueRule(path, timerOut, view, blackTicks, grace, backlogNow, ringAhead, lever)`:

| Row | Inputs | Expected |
|---|---|---|
| old_waits_on_black | Old, F, Black, 5, 0, None, F, Act | Wait |
| old_timer | Old, T, Visible, -1, 0, None, F, Act | Timer |
| kick_timer | Kick, T, Black, 5, 0, None, F, Act | Timer |
| backlog_black_waits | Backlog, F, Black, 5, 3, Line, F, Act | Wait |
| backlog_timer | Backlog, T, Black, 5, 3, Line, F, Act | Timer |
| fast_black_no_grace | Fast, F, Black, 0, 0, None, F, Act | Black |
| fast_black_in_grace | Fast, F, Black, 2, 3, None, F, Act | Wait |
| fast_black_grace_spent | Fast, F, Black, 3, 3, None, F, Act | Black |
| fast_black_in_grace_at_timer | Fast, T, Black, 1, 3, None, F, Act | Fallback |
| fast_black_spent_and_timer_is_black | Fast, T, Black, 3, 3, None, F, Act | Black |
| fast_heading_waits | Fast, F, Heading, -1, 0, None, F, Act | Wait |
| fast_fallback_heading | Fast, T, Heading, -1, 0, None, F, Act | Fallback |
| fast_fallback_visible | Fast, T, Visible, -1, 0, None, F, Act | Fallback |
| recheck_holds | Fast, F, Black, 3, 3, Line, F, Act | Wait |
| recheck_at_timer | Fast, T, Black, 3, 3, Line, F, Act | Recheck |
| recheck_unknown_holds | Fast, F, Black, 3, 3, Unknown, F, Act | Wait |
| nogate_ignores_recheck | Fast, F, Black, 3, 3, Line, F, NoGate | Black |
| norecheck_ignores_recheck | Fast, F, Black, 3, 3, Line, F, NoRecheck | Black |
| ring_ahead_waits (T9) | Fast, F, Black, 3, 3, None, T, Act | Wait |
| ring_ahead_at_timer (T9) | Fast, T, Black, 3, 3, None, T, Act | Recheck |
| never_past_the_timer | every path, view, backlog, ringAhead and lever with timerOut T | never Wait (one sweep row) |

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
| `due_wall_only` | D not taken | fast_black_grace_spent |
| `due_backlog_commits_on_black` | the refuted early commit | backlog_black_waits |
| `due_no_recheck` | no recheck | recheck_holds |
| `due_no_grace` | no grace | fast_black_in_grace |
| `due_no_fallback` | the s42 strand | fast_fallback_heading, never_past_the_timer |
| `due_recheck_past_timer` | G's hold, not round 1 | recheck_at_timer |
| `due_unknown_backlog_free` | an unreadable backlog does not hold | recheck_unknown_holds |
| `due_ring_ahead_free` | an unmerged ring does not hold (rev 1) | ring_ahead_waits |
| `grace_on_own_fade` | a grace after our own fade | fade_0 |
| `reassert_never` | no reassert | fast_visible_once |
| `reassert_every_tick` | reassert on every tick | spent |
| `reassert_old_path` | reassert on the Old path | old_never |
| `blackticks_no_disarm` | leaving black keeps counting | leaving_black_disarms |

---

## Kit side

- **`tools/harness/battlewire.py`** gains a section `[ff9mapkit netsync s164] FIELD-SWAP TIMING`:
  - every constant and name table;
  - twins for every pure rule: A's 13 (`swap_ticks_to_ms` ... `swap_oob_verdict`), B's `swap_orphan_settled`, `swap_host_holds`, `swap_ctl_hold_kind`, `swap_hold_end_why` and `swap_orphan_since`, C's `own_field_pass_rule`, `own_jump_verdict_rule`, `intent_cache_step`, `intent_cache_verdict`, `own_pass_book` and `own_pass_keeps_own`, LIFE's `intent_landing_step`, `intent_life_rule` and `body_there_rule`, PIN's `pin_capture_rule`, `pin_targeted`, `pin_drop_on_new`, `pin_age_rule`, `pin_use_rule`, `pin_consumed` and `landing_frames` (three outputs), and D+E's nine;
  - every log builder, including the refusal line with its `[NetSync] own Field(` prefix (R9);
  - `S163_FORMS`, the s163 regex of every line that gains a stamp;
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
    - B's orphan model on the twins (`fakegame.py:13482-13490`), including `swap_orphan_since`, and the bench host emitting 0 under `hostctl off` (:13546);
    - its `host_intent` already persists until replaced (:7959-7963).
  - **What it cannot model:** the slot and host probes, a bounce (it has no MAPJUMP), a pin (it has no story frames), `lifebench`, or the fade slot. Those keys stay at their sentinels.
- **`tools/harness/session.py`:**
  - `swap` after `speed` in `NETSYNC_SUBVERBS` (:8415) and `NETSYNC_AUTHORITY_SUBVERBS` (:8424);
  - `NETSYNC_SWAP_SUBVERBS = {"swap": ("coop_field_swap", "netsync.swap", "s164", "the s164 field-swap levers")}` next to the speed table (:8585), and in the `ng = ng or ...` chain (:8986);
  - `NETSYNC_SWAP_OPS`, the role sets, and the refusal and usage strings, verbatim;
  - `_swap_refusal(args, selftest_role)` as a pre-step check, modelled on `_speed_refusal` (:9420).
  - The driver reads the target game's `netsync.role` before sending a role-bound op, and checks each duo Session separately.
- **`ff9mapkit/tests/test_harness_netsync.py`:**
  - every SelfTest row evaluated against the twins, and every mutant failing at least one row (the mutant tables above are the oracle);
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
  - DA-LANE reads `arrived_t == -1` as UNREACHED, never red;
  - the solo run is green on the stand-in for legs K, A and B (the legs it models); legs C, P, L and F report UNREACHED there by construction (their keys sit at sentinels), and the test asserts exactly that;
  - source tests: the engine still carries `_glHostHoldsInput = v.HostHoldsInput;` next to the new `NetSyncSwap.HostHoldsNow` line (R8), and the refusal literal starts `[NetSync] own Field(` (R9).
- **Evidence scripts:** `studies/field-coop/swap-timing/final.py:26`, `conv.py:20` and `drift.py:15` get the tolerant stamp tail.
- **`coop_follow_race_duo.py`:**
  - the tolerant tail at :208;
  - FE1, FE2 and FD send `netsync swap fade old` to the guest when the engine publishes `netsync.swap`, because those rows model a commit 0.9 game-seconds after the start;
  - FS stays valid through D's own-warp term.

---

## Benches

### Solo: `studies/test-harness/scenarios/coop_field_swap_timing.py`

One game on the selftest role (`netsync selftest 1`, `bench 1`, `stateevery 1`). `COOP_LEGS` picks legs from K, A, B, C, P, L and F; leg K always runs. HOME is the bench field and AWAY is 30602, which is registered and walkable. A harness `warp` never reaches `RedirectGuestFieldJump`, because it goes through `SetNextMap` (`Ff9mkDebugMenu.cs:2453-2455`). So own-jump rows use a real script `Field()`.

**Leg C's setup, pre-registered (F8).** `warp(351, entrance=15, scenario=2600)`, `swap fade old` (T8), `lock 1`, the bench pages each line as it opens.
- Entrance 15 with a scenario below 2990 other than 2840 builds 351's desk scene: the party and the innkeeper pair are created (`test2_94.txt:60-76`), and `Zidane_Init`'s case 15 sets `VAR_GlobInt16_48 = 1` (`:3230-3234`), which starts the scene at its first line, win 3 text 129 (`:3304-3317`). The fourth two-PC session ran 359 and this desk scene at 2600 and, after a reload of 359, at 0 (`twopc-s163-20261029` host log lines 50 and 56); the s158 session ran them at 2505 (its host log lines 67 and 77).
- The scene ends in the rest exit: `FadeFilter(6,24)`, `FadeFilter(6,8)`, `Wait(136)`, entrance 5, `Field(352)` (`test2_94.txt:3486-3539`). That `Field(352)` is the own jump.
- The leg warps straight to 351, not through 359: on the selftest role `LastHostField` is -1 (:2039), so 359's own `Field(351)` would bounce.
- REACHED only when "win 3 text 129 opened locked" logs within 30 s of the warp's landing; otherwise the leg is VOID.
- A dry run under `own old` measures Δ from the scene's last line close to the own jump (A's stamps).
- **Why `fade old`.** Under D+E the 351 screen is black for about 4.5 s before `Field(352)`, so a follow started inside it joins, commits after the 3-tick grace and pre-empts the own jump (F2). Under `fade old` the follow stays pending for 0.9 s across the own jump, which is the case C's Pending term exists for.

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
| B-BLIP | B: on, then off 1.0 s later | Orphaned, then locked; one relock line; `relocks` +1; no auto-close through AutoReadMs + 1 s | `orphan` |
| B-BLIP2 | B: on (the line orphans at t0), then off for 0.5 s every 1.5 s for 6 s, then on | `relocks` +4; the auto-close lands no later than t0 + AutoReadMs + the summed held time + 0.3 s (R5) | `orphan` |
| B-SCENE | B: then `hostscene 1` | The end line "(the host is busy (a scene or a line))"; the bench host's ADV closes the line "closed (host seq" | `orphan` |
| B-CTLON | B: `hostctl on`, `hostscene 0` | Orphans OrphanGraceMs after settle and auto-closes; `holds` +0 | none (regression) |
| C-BOUNCE | C, no injection | The own jump bounces: `own_verdict` bounce, `own_why` not-host, `counts.bounces` +1, `reloads` +1, a landing on 351 via `bounce` with the record still open; `own.passes` +0 | none (gate; falsified by `via.bounce` / `join.land_source_reload`) |
| C-CACHE | C: `swap cache 352` at the last line's close + Δ − 1.0 s | The cache write line, then `own Field(352) passes on field 351 -- the host's announced field (cache)`; `by.cache` +1; one `Map: 352`; `bounces` +0; then `intent cache: field 352 cleared -- I left field 351 (now 352) (the cached field)` (T7) | `own`, `nocache` |
| C-PEND | C: `swap intent 352` aimed at the own jump − 0.45 s (inside the old path's 0.9 s pending window). REACHED when a pending 352 is sampled right before the pass line | `(pending)`; `converted` +1; one load; `fade.ends.own` +1; none of the s154 "cancelled", "dropped" or "never landed" lines | `own` |
| C-AGE | C: the cache injected ≥ 3 s before the jump | The "aged 2000 ms" clear, then a bounce | none (control) |
| C-SRC | C: a cache on another field, then a warp to 351 | The Left clear for that field, then a bounce | none (control) |
| P-PIN | P: `flag 8720 0`, `watch 8720`, `swap pinbench 30602 8720` | Flag 8720 = 0 after the landing; "stages intent N's frame for its story ... (age A ms; the latest differs at 1 story bytes)"; `pin.last_use` `pin`; `last.story` `pin` | `pin` |
| P-AGED | P: `age 3000` | Flag = 1; why `aged` | none (guard) |
| P-OTHER | P: `to <E>` | Flag = 1; the held entry still names 30602; `pin.other` +1 | none (guard) |
| P-LATE | P: `skip 3` | Flag = 1; why `late` | none (guard) |
| P-RESCUE | P: `skip 3 offfield` | Flag = 0 (the pin) | `pin` |
| P-PARTY | P: `swap pinbench 30602 8720 party 1 <c>`, where `<c>` differs from slot 1's current CharacterId | Flag 8720 = 0 (the story from the pin) AND `netsync.dress.mirror_party[1]` = `<c>` (the party from the latest frame); `pin.last_party` `latest` (R1) | `pin` (the flag half reds; the party half stays green under both rules) |
| L-LAND | L: `swap lifebench 30602` | At the hook: `intent.landing` `on_intent` with the intent still active (the "I landed" line) | none |
| L-STANDS | L | `last_end` `stands`; `last_life_ms` − max(2000, `landed_ms` + 1000) in [0, 400] | `life` |
| L-WIRE | L | `intent.wire` true while active, false after the end | none (guard) |
| F-FAST | F: `swap intent 30602` | `fade.last` = fast / fade / 12; by `black`; ticks 12-13; ms < 600 | `fade`, `long` |
| F-3X | F: `speedmode 1` | ms < 250; ticks 12-13 | `fade`, `long` |
| F-BLACK | F: `swap blackout 1`, wait 3 frames, then intent | view_start `black`, action `join`, by `black`, `black_ticks ≥ 3`, ms < 250; no sample from start to due with `cur_now` < 248 | `fade` (wipe; `cur_now` dips under 128) |
| F-JOIN | F: `blackout 8`, then intent | `heading`, left ≤ 8, `join`; due within left + 3 + 1 ticks | `fade` |
| F-HURRY | F: `blackout 60`, then intent | `hurry` with frames 12; due by `black` within 13 ticks; `cur_now` never drops | `fade`, `long`, `nohurry` |
| F-OPEN | F: `lock 1`; talk to the talk-relay bench NPC (the line opens locked); intent | backlog_start `open`, path `backlog`, by `timer`, ms ≥ 885 | `fade`, `nogate` |
| F-AHEAD | F: `lock 1`, `netsync unmatched`, intent within 1 s | backlog_start `ahead`; by `timer` | `fade`, `nogate` |
| F-AGED | F: as F-AHEAD, but wait 3.2 s first | path `fast` (the age cap) | `fade` |
| F-RECHECK | F: intent, then `netsync unmatched` in the same batch | path `fast`, `held`, by `recheck`, ms ≥ 885 | `fade`, `nogate`, `norecheck` |
| F-REASSERT | F: intent, then `swap blackout off` 3 ticks into the fade (F12) | One reassert line; `fade.reasserts` +1; by `black` | `fade`. Not run under `long` (a 24-tick re-fade lands on the 0.9 s timer: a coin flip) |
| F-KEY | F: `lock 1`, a bench host key for my field (`netsync host key ...`, `HarnessAgent.cs:1760-1773`), intent before the copy plays it (F12) | backlog_start `key`, path `backlog`, by `timer`, ms ≥ 885 | `fade`, `nogate` |

**Solo calibrations, pre-registered.** Each word turns exactly these rows red; every other row stays green:

| Word | Lever | Red rows |
|---|---|---|
| `stamps` | `swap stamps off` | A-STAMP |
| `delay` | leg 2 sends `delay 0` but still expects +300 | A-DELAY |
| `orphan` | `swap orphan old` | B-HOLD, B-RELEASE, B-BLIP, B-BLIP2, B-SCENE |
| `own` | `swap own old` | C-CACHE, C-PEND |
| `nocache` | `swap own nocache` | C-CACHE |
| `pin` | `swap pin old` | P-PIN, P-RESCUE, P-PARTY |
| `life` | `swap life old` | L-STANDS |
| `fade` | `swap fade old` (leg C keeps its own `fade old`) | F-FAST, F-3X, F-BLACK, F-JOIN, F-HURRY, F-OPEN, F-AHEAD, F-AGED, F-RECHECK, F-REASSERT, F-KEY |
| `long` | `swap fade long` | F-FAST, F-3X, F-HURRY |
| `nogate` | `swap fade nogate` | F-OPEN, F-AHEAD, F-RECHECK, F-KEY |
| `norecheck` | `swap fade norecheck` | F-RECHECK |
| `nohurry` | `swap fade nohurry` | F-HURRY |

Spacing: C-leg attempts run more than 20 s apart, or change field between them. The bounce budget (3 bounces in 20 s per field, :567-581) would otherwise let a calibration through. An s163 engine refuses the whole run at load. Any other `COOP_CALIBRATE` word is refused at load.

### Duo: `studies/test-harness/scenarios/coop_field_swap_timing_duo.py`

Two real games on this desktop through `tools/harness/duo.py`, with `stateevery 1` on both. HOME is 250, AWAY is 30602. Every guest-side lever is legal on the duo's client, and `life` goes to the host game. Both games load one DLL through the instance junction, so every calibration is a lever, never a DLL swap.

**The clock precondition (F1, F11a).** DK-CLOCK runs first: K-CLOCK must hold on BOTH games. When it does not, every cross-game row (DA-LANE, DC-B(a)'s gap, DF-FAST's gap, DB-BIT, DP-MARK, DL-LEFT, DA-ARRIVE's overlap) is VOID with the reason, never red. Rows inside one game still judge.

**Legs and their pre-registered data (F8).** Every warp, scenario and poke is data in the scenario file, as `coop_speed_mirror_duo.py:109` keeps its own.

| Leg | Host setup | Shape | Rows |
|---|---|---|---|
| CAL | `warp(250, entrance=0)`, then `warp(30602, entrance=0)` and back; the guest idle and visible; each field held at least LineWindowMs + 1 s = 11 s (F13). Sub-legs: CAL0 the guest on `fade old`; CAL1 `fade old` and `delay 200`; CAL2 act; CAL3 act and the guest on `speedmode 1` | the follow race's FE1 shape (debug warps) | DA-LANE, DA-CAL, DA-JOIN, DL-LIFE, DL-NOREG, DC-FE, DF-FAST, DF-3X, DA-ARRIVE (CAL2; CAL0 its control), DA-PROBE-X |
| DESK | `warp(359, entrance=0, scenario=2600)`; the guest follows; the host pages each line D after it opens, D ∈ {0.3, 1.0, 2.5} | FT-A: 359's scene runs at any scenario (`test2_102.txt` reads none) and ends in `Main_11`: `PreloadField(5,351)`, `FadeFilter(6,24)`, `Wait(25)`, entrance 15, `Field(351)` (`:271-301`, called from `:648`); 351 entrance 15 builds the desk scene (see leg C), first line win 3 text 129 | DA-LINES, DF-FLASH, DF-PACE, DA-PROBE, DA-ARRIVE, DC-WON |
| REST | continues each DESK run: the desk scene's own end (`Zidane_Loop`'s rest exit, `test2_94.txt:3486-3539`) to 352 entrance 5, first line win 4 text 142. Sub-legs: REST (act) and REST-OLD (the guest sends `swap fade old` before the desk scene's last line) | FT-B | DC-B(a) (REST), DC-B(b) (REST-OLD), DP-UP, DP-DRESS, DA-PROBE, DC-WON |
| CAT | `warp(350, entrance=0, scenario=2600)` (the session's 350 value), the guest by one follow; pokes below | 350 to 351 "Cat's Eye" | DB-SHAPE, DB-BIT, DB-HOLD, DB-ORDER |
| OWN | s163's recipe: the host's byte 238 poked and read back, then `warp(351, entrance=0, scenario=2600)`; the gate bytes 238 = 1, 241 = 4, 242 = 0 on both, the guest first (`coop_speed_mirror_duo.py:427-429, 551-553`); pick choice 2 | FT-OWN: 351 to 450 "Dagger Tries" | DC-OWN |
| MENU | The guest holds its main menu across the host's MAPJUMP and closes it 1.2 s after the emit (and 3.5 s in the aged variant); the host marks flag 8720 during the menu | | DL-DEFER, DP-DEFER, DP-AGED |
| MARK | The host exits to D; once the host's body stands on D, the bench sends `flag 8720 1` to the host. The guest runs `swap fade long` for this leg, to widen the window | | DP-MARK |
| LEFT | The host's harness `battle` 0.8 s after its landing | | DL-LEFT |
| OPEN | The host opens an NPC line (relayed locked to the guest) and warps with it up | | DF-OPEN |
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
| DA-LANE | Order, per transition: emit_t ≤ intent.first_sent_t ≤ seen.arrived_t ≤ seen.first_t ≤ follow_t ≤ due_t ≤ commit_t ≤ the guest's land_t. A transition whose `arrived_t` is -1 or whose first send the watch missed is UNREACHED for that transition, never red (F10). Reported, not judged (T12): first_sent_t − emit_t, seen_t − arrived_t, follow_t − seen_t, the landing gap and the first-line gap | none (gate on order) |
| DA-CAL | CAL1: `commit_t - due_t` = 200 ms ± 1 frame within each follow. Reported: CAL0's commit − follow (0.885-0.912 s predicted) and CAL1 − CAL0 | `delay` (CAL1 sends `delay 0` but still expects +200) |
| DA-PROBE | MAPJUMP legs only (DESK, REST), per intent with `intent.last_site` `mapjump` (a sample from another site is refused): frames, updates and sends ≥ 1; oob `sent` or `overwritten`; 1 ≤ the guest's `seen.copies` ≤ the host's `sends`; `last_end` `stands` under act. Predictions below (F4) | none (gate on consistency) |
| DA-PROBE-X | CAL: the same keys on debug-warp emits | exploratory, reported only |
| DA-JOIN | One record per transition on each copy (ids +1); the guest's nonce equals the host's; the guest's land_via `follow`, the host's `host`; both closed by `line` or `window` | none (gate) |
| DL-LIFE | The guest's seen span (last_t − first_t) is 1800-2700 ms; the host's "ended ... I stand on it" line | `life` (span about the host's load) |
| DL-NOREG | Per transition: exactly one parallel-follow line, one commit and one landing; no "follow-warp ... cancelled"; no second follow for the nonce | none (guard) |
| DC-FE | No `[NetSync] own Field(` line on the guest; `own.passes` +0 | none (guard) |
| DF-FAST | CAL2: the guest's `fade.last` = fast / fade / 12, by `black`; commit − follow 0.35-0.60 s; the host-to-guest landing gap shorter than CAL0's by ≥ 0.3 s | `fade`, `long` |
| DF-3X | CAL3: ticks 12-13; commit − follow ≤ 0.22 s | `fade`, `long` |
| DA-LINES | Every edge line on both logs stamped; for each host tap seq S: tap_t ≤ queued_t ≤ closed_t; "waited X ms" = closed_t − queued_t ± 1 ms; "shown Y ms" ≤ closed_t − that page's open stamp | `stamps` (both games) |
| DF-FLASH | REACHED when `view_start` is `heading` or `black`. Action `join`, or C's own pass ends it (by `own`); no `cur_now` dip from the follow start to the first of (due, field load). Otherwise UNREACHED, never red | `fade` (wipe and the dip) |
| DF-PACE | At D = 0.3, REACHED only when the copy lags at the intent: backlog_start `line` or `ahead`; by `timer`; the guest's last close for 359 logged before the commit. Otherwise UNREACHED | `fade`, `nogate` |
| DC-B(a) | REST at act, on any path. REACHED when the guest saw the intent before its own jump or made no own jump before its landing. Green: one guest load of 352; `bounces` +0; guest landing − host landing ≤ 0.3 s. An own jump before the intent (the s158 shape) is recorded as "C2 not built" and not judged (F2) | none (behaviour gate) |
| DC-B(b) | REST-OLD (the guest on `fade old`). REACHED when the guest saw the intent before its own jump (`own.cache.field` 352, or a pending 352 sampled first) and its `host_lane` read 0 or 351 then. Green: an own pass (pending, committed, intent or cache), `converted` +1 when the term is pending, one load, `bounces` +0 | `own` (a bounce, a second load) |
| DC-WON | DESK, REST and REST-OLD: `counts.follow_won` Δ and own passes by term, per leg (F2) | reported, never judged |
| DP-UP | REACHED when `pin.upgrades` Δ ≥ 1 across the MAPJUMP exits, else UNREACHED (F11c). Green: every such upgrade reads `last_upgrade_diff` 0 (the "VM halted" premise) | none (gate) |
| DP-DRESS | After the 351 → 352 landing, the guest's `dress.self.want_char` matches the latest frame's leader (no double) | none (the mutant `dress_follows_story` carries it) |
| DP-PARTY | REACHED only on a landing whose host `dress.party` differs between the emit and the host's landing. Green: the guest's `dress.mirror_party` after its landing equals the host's post-landing party (the latest frame), not the emit-time one (R1). UNREACHED otherwise | none (P-PARTY and the mutant `party_follows_story` carry the claim) |
| DB-SHAPE | The guest logs its own `Field(351)` passing (the host's pick, choice 3, on field 350), and its first state sample listing window (win 7, text 113) comes at least 4.5 s before its first sample with `host_flags` b0 set on 351, both on the guest's own `clock.now_ms` (F11b). If text 118 opens first, the else path ran and the run is VOID | none (reach guard) |
| DB-BIT | Between the guest's 113 open and the host's scene rise: every guest sample reads `host_flags` b1 clear with b3 set, the lane on 351, and `orphan.host_holds` true; every host sample reads `player.control` false | none (Finding 11's premise, read rather than assumed) |
| DB-HOLD | One "win 7 text 113 held -- the host's control is off on my field" line, then the end line at the host's 113 open, predicted "(a host event claims it)"; no "113 is not on the host's screen"; `orphan_closes` Δ0 across 351 | `orphan` |
| DB-ORDER | The guest's 113-117 each close "closed (host seq N)", with N strictly increasing and equal to the host's tap seq for the same text; no "dropped -- it is for field 351" | `orphan` |
| DC-OWN | One load; the term or the lane recorded | none (regression) |
| DL-DEFER | The guest's "intent: following the peer to field D (parallel)" within 200 ms of its menu closing | `life` (host; the serial follow's line instead) |
| DP-DEFER | REACHED only when that landing came by the intent (`last.follow_via` `intent`) with the pin's age < 2500 ms: flag 8720 = 0. VOID under `life` | `pin` |
| DP-AGED | Menu held to 3.5 s: flag = 1, why `aged` | none (guard) |
| DP-MARK | VOID unless the host's first sample with flag 8720 = 1 (its `clock.now_ms`) precedes the guest's `last.land_t` by ≥ 300 ms (F11b). Flag = 0, the pin line, `last_diff` ≥ 1 | `pin` |
| DL-LEFT | The host logs "ended ... I left it"; the guest's `seen.last_t` stops within 300 ms of the battle start | none (guard) |
| DF-OPEN | The guest's backlog_start `open`, path `backlog`, by `timer` ≥ 0.885 s. If the harness `warp` refuses with a window up, DF-PACE stands in as the backlog row | `fade`, `nogate` |
| DA-ARRIVE | CAL2 and DESK, REACHED only when the guest is dressed at the landing (`dress.self.want_char` ≥ 0 and not Zidane). Green: from the guest's landing until its control returns, no `step-out: OUT ... -- dwell` line and, on CAL2 (no line at all), `netsync.stepout.active` never true. On DESK an OUT by `line` at the desk scene's first line is lawful. Reported: the host-to-guest control-off overlap at each arrival, from both games' `player.control` samples (R2) | none. `fade old` (CAL0, a DESK run with the guest on `fade old`) is its control and must be green too |
| LVD-ROLE | `swap life old` to the guest gives the host-side refusal; `swap orphan old` to the host gives the guest-side refusal; `swap hostctl off` to either gives the selftest refusal | none |
| LVD-LIFE | `swap life old` to the host reads back `levers.life` `old`, and the host's `reset` releases it | none |

**DA-ARRIVE's red is a defect, not a calibration.** No arrival guard is pre-built in round 1. A red at act means the tighter landing feeds s158's ARRIVAL LAW (`NetSyncStepOut.cs:22-23`; `DwellMs = 1500` at :147; `StartRule` :261-268) past its dwell, and it must be fixed before ship. The planned fix is a landing-scoped arrival guard behind its own lever: a dwell counted from max(the base start, my landing + the host's arrival lead), never a retuned `DwellMs`.

**Duo calibrations, pre-registered.** Each word turns exactly these rows red:

| Word | Lever | Red rows |
|---|---|---|
| `stamps` | both games: `swap stamps off` | DA-LINES (DB-SHAPE and DP-MARK read `clock.now_ms` and stay as they are) |
| `delay` | CAL1 sends `delay 0` | DA-CAL |
| `orphan` | guest: `swap orphan old`, from before the pick | DB-HOLD, DB-ORDER |
| `own` | guest: `swap own old`, on REST-OLD only; CAL and DESK hold `own act` (T4) | DC-B(b) |
| `nocache` | guest: `swap own nocache`, on REST-OLD only | none: a control. When the intent is seen in time the Pending term decides before the cache term is reached, so DC-B(b) stays green; the cache term's red is solo C-CACHE |
| `pin` | guest: `swap pin old` | DP-MARK, DP-DEFER |
| `life` | host: `swap life old` | DL-LIFE, DL-DEFER (DP-DEFER goes VOID; DC-B(a) stays green; DA-PROBE records the s163 life as a measurement) |
| `fade` | guest: `swap fade old` (the CAL sub-legs keep their own levers) | DF-FAST, DF-3X, DF-FLASH, DF-OPEN, and DF-PACE if reached |
| `long` | guest: `swap fade long` | DF-FAST, DF-3X |
| `nogate` | guest: `swap fade nogate` | DF-OPEN, and DF-PACE if reached |

**Pre-registered predictions:**
- **DA-CAL:** CAL0 0.885-0.912 s (the s163 measurement, reported); CAL1 `commit_t - due_t` = 200 ms ± 1 frame.
- **DF-FAST:** commit − follow about 0.40 s (12 ticks at 30 TPS, plus up to 1 tick). Landings about 0.5 s apart instead of about 0.95 s (§1: 1.04 s − 0.47 s).
- **DF-3X:** about 0.15 s.
- **DC-B(a):** the guest lands at most 0.3 s after the host, with no reload.
- **DC-WON (INFER):** at act, a copy within 3 ticks of the host passes by its own `Field()`; a copy further behind lands by the follow.
- **DA-PROBE (MAPJUMP legs):**
  - Under act: `last_life_ms` 2000-2400, `sends` about `last_life_ms` over the measured write period.
  - Under `life` (the s163 rule): `last_end` `old`, `last_life_ms` 250-600 (the host's load), `updates` 1-2, `frames` 1-3.
  - If `life old` reads under 100 ms instead, it is "the other Unity order OR a frame time under 10 ms / FastForwardFactor", told apart by `intent.emit_dt_us` and `intent.host_fps`: a sub-100 ms life with an emit frame of at least 10 ms / factor means the other order.
- **DA-LANE:** reported only; the writer's wait is bounded by its `Thread.Sleep(33)` at the system timer's granularity (`NetSyncSocket.cs:800`).
- **DB-HOLD:** the hold ends "(a host event claims it)", because the open set and b2 ride one frame.

**Exploratory (pre-registered, never gating): DP-COUNT.** Dali's `SByte[296]` countdown, from a save past 450's ping, into a controller room (356, e2, t1, +12).
- H-STEP first: the host alone must read 296 go 3 → 2, or the row is VOID.
- Then the guest reads 2 under the pin, and 1 under `pin` (the double step).

**Not provable here:** the duo shows no real network latency and no laptop/desktop load difference. The next two-PC session replays with the stamps. One host-alone run on the laptop under `swap life old` on a scripted exit (DESK or REST), read through DA-PROBE's keys including `intent.host_fps` and `emit_dt_us`, settles the laptop's order and frame-rate case.

---

## Files and hunk estimate

Every hunk is tagged `[ff9mapkit netsync s164]`.

| File (engine) | Hunks | What |
|---|---|---|
| `Memoria\Netsync\NetSyncSwap.cs` (new) | file | A's rules and record, the QPC clock, C's rules, PIN, LIFE, the levers, the state readers, the SelfTest |
| `Memoria\Netsync\NetSyncFollowFade.cs` (new) | file | D+E's rules, the per-follow state, `Begin` / `Due` / `Ended` / `Clear` |
| `Assembly-CSharp.csproj` | 1 | two includes |
| `Memoria\Netsync\NetSyncClient.cs` | about 62 | A about 29, B 4, C about 10, PIN about 10, LIFE about 10, D+E about 6 (partly shared sites) |
| `Memoria\Netsync\NetSyncDialog.cs` | about 22 | A's stamps, PageT and SeenT; B's rule, hold tracking, `OrphanSinceRule`, OrphToLocked wording, teardown and KeyScript row; D's `BacklogNow` |
| `Memoria\Netsync\NetSyncAte.cs` | about 6 | A's three stamps; C's `HoldVerdict` / `HoldsFollowQuiet` split (byte-identical) |
| `Memoria\Netsync\NetSyncSocket.cs` | about 9 | interface (three members), struct, frame fields, `SetStateWatched`, SetState, CollectOutgoing, Accept (`InSeq`), forwarders |
| `Memoria\Netsync\NetSyncRelay.cs` | 3 | forwarders |
| `Memoria\Netsync\NetSyncState.cs` | 1 | `ApplyStorySplit` |
| `Memoria\Netsync\NetSyncBattle.cs` | 1 | the release (after :6840) |
| `Memoria\Harness\HarnessAgent.cs` | about 6 | `case "swap"`, the unknown-sub-verb literal, `AppendSwap` and its call, the catch literal, the ProtocolVersion paragraph |
| `Assets\Scripts\Common\SceneDirector.cs` (stock) | 1 | the read-only `NetSyncReadFade` |
| `Global\UI\UIKey\Ff9mkDebugMenu.cs` | 2 | `NetSyncWarpPending`; the emit site argument at :2452 |
| **Total** | **about 115 hunks in 12 files, plus 2 new files** | |

**Kit files:**
- `tools/harness/{battlewire.py, fakegame.py, session.py, channel.py}`
- `ff9mapkit/tests/test_harness_netsync.py`
- new: `ff9mapkit/tests/test_coop_field_swap_timing_bench.py`
- `studies/field-coop/swap-timing/{final.py, conv.py, drift.py}`
- `studies/test-harness/scenarios/coop_follow_race_duo.py`
- new: `studies/test-harness/scenarios/coop_field_swap_timing.py` and `coop_field_swap_timing_duo.py`
- at build: `memoria-patches/s164-netsync-field-swap-timing.patch` with its README row, and `ff9mapkit/CHANGELOG.md`

**Gates before the README row:**
- the proof line OK;
- `test_coop_field_swap_timing_bench.py` and the domain tests green;
- the solo bench green, with every calibration word turning exactly its rows red;
- the duo green with DK-CLOCK holding, with the same; DA-ARRIVE green at act;
- the regression set:
  - from rev 1: `coop_ate_relay` (s161's counts unchanged: 165 rows / 65 mutants), `coop_step_out`, `coop_chest_relay`, `coop_guest_traversal`, `coop_self_dress`, `coop_climb_anim`, `coop_speed_mirror` and `coop_dialogue_authority`;
  - added for LIFE and PIN (R3): `coop_world_wait`, `coop_world_battle`, `coop_world_party_duo`, `coop_session_edges`, `coop_session_edges_duo`, `coop_ramp_title`, `coop_talk_relay`, `coop_dialogue_lockstep`, `coop_diorama_return`, `coop_ate_relay_duo` and `coop_chest_relay_duo`;
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
7. **Seeds, not laws:** the 3-tick grace, `AheadMaxMs` 3000, `PinMaxAgeMs` 2500 from the landing seen, `PinBlindCapMs` 10000, `IntentMinLifeMs` 2000, `LandTailMs` 1000 and `IntentCacheMs` 2000.
   - A script whose own `Field()` comes more than 3 ticks after its fade reads black loses its own pass and lands by the follow instead (the same field). With the pin and C's entrance handling, that is equivalent; DC-WON counts it.
   - A short cache only loses passes; it never adds one.
8. **The s158 shape keeps one reload** (about 1.4-1.5 s). C2 is not built.
9. **A guest that lands while the host is still on the source field** orphans after about 7 s (B's gap). Only C2 would reach it often.
10. **Fixed in rev 2: the party read wraps no longer follow the pin (R1).** The landing stages section 0 from the pin and sections 1-3 from the latest frame. What remains is s163's own behaviour: a read inside the copy's `Main_Init`, made before its own party change, sees the latest (post-change) party until a relayed talk's R8 refresh.
11. **A `Main_Init` that rewrites FieldEntrance** (bytes 2-3) would make the pin's entrance differ from the latest frame's. Under the pin, my copy replays what the host did.
12. **The `HoldsFollow` split must stay byte-identical** (C). s161's counts check the loud path; `quiet_equals_loud` checks the quiet one.
13. **Under s161's exit hold, a C pass keeps my copy's own entrance** (owner default 4). The exit hold itself is proven by self-test only (`ATE-RELAY.md:290`).
14. **Earlier landings and the step-out.** The tighter gap lengthens the overlap of the two copies' arrival control-off phases, which s158's arrival law guards only by its 1500 ms dwell; Finding 9's dressed double also shows for longer. DA-ARRIVE watches both; a red at act is a defect to fix before ship, with the arrival guard above as the planned fix.
15. **Bodyless destinations keep section 4** until the host leaves or emits again (6 bytes a frame). A disc change now ends section 4 at the hook.
16. **Log census.** Every `$`-anchored reader in the repo is fixed. Readers outside it, such as the owner's own scripts, are unknown.
17. **Kit churn:** about 20 tail-order asserts, plus the sub-verb regex.
18. **A copy fade that re-inits the slot mid-follow (T10, deferred to round 2).** A copy's own `FadeFilter` started after the follow's fade re-inits the slot with its own frame count; black can then land after the 0.9 s timer and the commit cuts from a half-dark screen, the same outcome as today. The measure is the due line "the 0.9 s fallback: the fade never read black (<view>, ...)".
19. **The divergent copy in the commit window (T4).** A copy whose own `Field(N)` names a field other than the follow's runs in the tick after the commit and bounces: one reload and a second follow, as today. A matching `Field()` passes by the Committed term.
20. **Levers rest on the release alone (F9).** A throw inside `HarnessReleaseBench` before `NetSyncSwap.HarnessRelease()` would leave a lever set until restart, the same exposure every netsync lever has had since s133.
21. **World-rejoin landings stage the latest frame in round 1 (R3).** A world script's writes after its MAPJUMP reach the guest exactly as on s163.
22. **The pin's landing-seen lane term (INFER).** It rests on the out-of-band frame carrying b3 set; `pin.land_seen_by` reports which term fired, and DP-UP's reach clause shows how often an off-field frame exists at all.
23. **DP-PARTY is not deterministically reachable on the duo.** No harness verb changes a real host's party or bag at a chosen moment. P-PARTY (solo, through the real `ParseSections`) and the mutant `party_follows_story` carry the claim; a host-side party poke is a build-round follow-up if the owner wants the duo row reached on purpose.
24. **No main-thread stall lever.** T6's stall case is covered by rows c3-c5 and by pinbench `skip <n>` through the real `PinCaptureRule`, not by a real stall: no harness verb blocks the game thread, and one is not cheap to make safe.

## Owner decisions (defaults taken)

Rev 1 left seven questions open. The owner took a default for each; every default names the lever or follow-up that reverses it.

1. **The backlog path without the flash: yes.** With a backlog the follow keeps today's exact timing (24-tick length, 0.9 s timer), but a screen already black or going black is not forced back to visible first. Reversed by `swap fade old`, which restores today's wipe on every path. A backlog-only wipe lever was considered (F12) and not built.
2. **Hurry, not a literal "never re-init".** A copy fade slower than the follow's budget is re-paced to black from where it is, without a flash. Reversed by `swap fade nohurry`, which keeps the literal rule reachable.
3. **No cap on the orphan hold in round 1.** A cap is sized from `orphan.last_hold_ms` and the stamps if round 2 needs one. `swap orphan old` restores s163's rule.
4. **The entrance for a C pass under s161's exit hold: my copy's own entrance**, consistent with today's passes (`OwnPassKeepsOwn`). Reversing it is a one-term change in a later round; the mutant `entrance_exit_hold_blind` shows the difference.
5. **The entry-write census runs during the build round** (offline: the 817 exports' `Main_Init` and first tag-1 writes classed as set, read-modify-write, once-gated, random-gated or bytes 2-3). `pin.last_diff` measures in play, and `swap pin old` restores the latest frame.
6. **(Removed.)** Rev 1 asked whether to accept a first Netsync read of the harness-armed flag. Rev 2 follows the s163 lever shape and reads nothing from the harness (F9; § The lever scheme).
7. **C2 in a later round.** It needs a lockstep guard and an "own-ahead landing" law (keep my copy's own story when no intent frame exists for the landed field), each with its own review.

## Sources

- `studies/field-coop/FIELD-SWAP-TIMING.md` (the measurements, options, corrections and recommendation; workflow `wf_87a54375-399`).
- The five item specs of this round's workflow: A instrument, B orphan and levers, C own pass, PIN-LIFE, D+E fade.
- The three reviews of rev 1: timing-race (T1-T14), regression (R1-R9), proof-bench (F1-F14), with the owner's resolution of each.
- `studies/field-coop/SPEED-MIRROR.md`, `ff9mapkit/tests/test_coop_speed_mirror_bench.py` and `studies/test-harness/scenarios/coop_speed_mirror_duo.py` (the s163 shape).
- Engine reads at s163:
  - `NetSyncClient.cs` (:215-216, 516-597, 858-947, 1140-1144, 1650-1690, 1940-1951, 2028-2111, 2160-2180, 4655-4675, 5599-5640, 5750-5779, 5832-5860, 6150-6165, 6598-6672, 6728-6756, 6800-6830, 6874-6885, 7155-7192, 7740-7839, 8780-8796, 9371-9432);
  - `NetSyncDialog.cs` (:1180-1201, 1505-1553, 1674-1686, 2214-2216, 3228-3229);
  - `NetSyncSocket.cs` (:37-76, 280-449, 609, 794-802);
  - `NetSyncState.cs` (:85-125); `NetSyncParty.cs` (:1-40, 215-230);
  - `NetSyncAte.cs` (:668-680); `NetSyncSpeed.cs` (:12-44, 88-100); `NetSyncStepOut.cs` (:18-26, 147, 239-270, 606);
  - `NetSyncBattle.cs` (:6758-6841);
  - `HarnessAgent.cs` (:398-406, 1188-1226, 1594-1612, 1760-1774, 2238-2337, 2350-2365, 4010-4077, 4117-4120, 4168);
  - `HonoluluFieldMain.cs` (:10-20, 226-320, 440-450); `HonoBehaviorSystem.cs` (:10-40, 90-125); `SceneDirector.cs` (:248-290, 392-404, 512-540, 636-680);
  - `FPSManager.cs` (:1-110); `QuitUI.cs` (:50-58); `Ff9mkDebugMenu.cs` (:854-858, 1338-1344, 2418-2460);
  - `EventEngine.DoEventCode.cs` (:1014-1044); `Memoria/Speedrun/AutoSplitterPipe.cs` (:168-174).
- HW exports (`C:\gd\FFIX\reference\test2\`): `test2_93.txt` (350: :336-352, 444-473, 560-620), `test2_94.txt` (351: :56-80, 840-910, 1115-1116, 2645-2715, 3222-3240, 3285-3320, 3480-3540, 3855-3880), `test2_102.txt` (359: :1-60, 138-170, 271-310, 648); `studies/story-trace/research/design-5-claim-checks.md:10`.
- The two-PC logs: `.harness-runs/twopc-{r3-20261027, s158-20261028, s161-20261028, s163-20261029}` (main repo).
