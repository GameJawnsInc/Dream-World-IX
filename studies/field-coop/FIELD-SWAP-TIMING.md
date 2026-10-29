# Field-swap timing, second pass

**Status: DESIGN (2026-10-29). Nothing built.** The owner asked for this after the fourth two-PC session: "more options for
tighter field-swap timing. the guest lags behind slightly, so some scenes the guest will be ~1s behind the host until they
rest at the same dialogue. we looked at improving this before but it's worth a second pass".

The first pass was F2 (wire v11; `gateways.md` sections 2 and 4). The host's MAPJUMP sends a transition intent, and the
guest starts its follow in parallel instead of waiting for the host to land. This pass looks at what F2 left.

**Method.** A workflow ran five readers: the follow timeline, the guest's own `Field()`, dialogue convergence, a catch-up
sprint and a host hold, and the evidence in the four two-PC log pairs. A designer then wrote the options, and two skeptics
tried to refute every one of them, one on mechanism and savings, one on regressions. Their corrections are folded in
below. Cites are against `C:\gd\FFIX\Memoria\Assembly-CSharp` at s163. The evidence scripts are in `swap-timing/`; they
read the archived logs in the main repo's `.harness-runs/twopc-*`.

## 1. What the ~1 s is

Measured from the four two-PC log pairs. `Memoria.log` stamps whole seconds, so each figure is a mean of 1-s values, with
a standard error of about 0.1 s. The clock offset of each session was estimated from 41-101 pairs of the host's
`dialog tap` and the guest's `queued` line, and showed no drift.

| Path | How the guest gets to the new field | Guest behind the host | n |
|---|---|---|---|
| Parallel follow | the intent arrives, the guest fades for 0.9 s, then changes field | 1.04 s (one clock: the host sees the guest's body) | 23 |
| Own `Field()` (the s161 ATE relay) | the guest's copy takes its own scripted `Field()` | 0.11 s | 9 |
| Bounce | the copy's own `Field(352)` ran while the host was loading, was bounced into a reload of 351, then the follow ran | 1.4-1.5 s, plus a visible reload (s158 also replayed a line) | 2 of the 5 scripted Dali transitions |

**The parallel follow, decomposed:** the 0.9 s timer, plus 0.32 s of guest load, minus 0.39 s of host load, plus
0.05-0.1 s of lane latency, gives about 0.88-0.93 s. The timer is about 90% of it. The load-time difference between the
laptop and the desktop measured about 0 (±0.15 s) on the Dali fields. A duo bench (one clock) confirms the timer:
follow start to commit 0.885-0.912 s (`coop_follow_race_duo.py`).

**After the guest lands:** in 13 of 16 scenes entered by a follow, the guest was already waiting at the first line the
host closed. So the owner's "~1 s behind until they rest at the same dialogue" is the entry lag carried through the
scene's opening walks and camera moves. It is shed at the first line the host reads for longer than the lag plus 350 ms.
The long "behind" runs (r3 field 300: +1.2 s growing to +10.2 s) came from a 3x host paging fast, which s163 now
mirrors.

## 2. Why (read in code)

- **The guest's fade starts after the host's has ended.** Stock exits fade before `Field()`: `ExitField`,
  `PreloadField(5,N)`, `FadeFilter(6,24)`, `Wait(25)`, `Field(N)`. A census of the 817 exports found 6276 of 7181
  `Field()` calls preceded by a same-N `PreloadField`. The host's own scene change is then an immediate cut
  (`SceneDirector.Replace("FieldMap", ..., false)`, `HonoluluFieldMain.cs:315`). The intent leaves at the host's MAPJUMP
  (`EventEngine.DoEventCode.cs:1040`). Only then does the guest start a 24-tick `FF9Wipe_FadeOutEx` and a 0.9 s timer
  (`NetSyncClient.cs:215-216, 4665-4672`). F2's design expected the guest's fade to start "essentially in lockstep with
  the host's" (`gateways.md:418-419`); it starts after it.
- **The timer is wall clock.** `ServiceFollowWarp` subtracts `Time.deltaTime` (`NetSyncClient.cs:6606`), which the
  booster does not scale: `FPSManager` runs extra loops and leaves `deltaTime` real. At 3x the guest's fade ends after
  267 ms, and the screen then sits black for about another 630 ms.
- **The follow fade flashes.** `FF9Wipe_FadeOutEx` first sets the screen fully visible, then fades
  (`SceneDirector.cs:671-675, 573-579`). A copy that its own script had already faded pops back to visible before going
  black again.
- **The bounce.** The guest's own `Field(dest)` passes only when `dest` is its own field or `LastHostField`
  (`NetSyncClient.cs:557`). `LastHostField` is the host's position lane (`:2166`), which reads 0 while the host has no
  body, which is its whole load (`:2084-2086`). Any other `dest` becomes a reload of the field being left (`:589-594`).

**Transition classes** (from the own-`Field()` reader):

| Class | When the guest's copy runs its own `Field()` | Today |
|---|---|---|
| A. Host gateway walk | never: the guest is not at that door. The most common swap | follow only, ~1 s |
| B. Scene ends, the guest waiting on the host's close | a few frames after the intent, inside the 0.9 s | bounces unless the host has already landed |
| C. Last line closes on its own timer, or a wordless ending | either side of the intent (s158 351->352: before it) | bounces |
| D. Guest 0.1-0.9 s behind | after the intent | bounces if it beats the host's landing, else passes |
| E. Guest more than 0.9 s behind | never: the follow commits first and cuts the scene's end (Finding 4) | follow only |
| F. Guest ahead (its own booster) | before the intent | bounces |

## 3. Options

Each option went to both skeptics. "Holds" means both found the mechanism real.

### Round-1 candidates (guest side, no wire change)

**A. Millisecond swap stamps (the instrument).** Add Stopwatch millisecond stamps to the existing edge lines: the host's
intent emit, the guest's follow start, the commit, the landing (`NoteFieldLanding`), the own-jump pass or bounce, the
first locked line, and the dialogue tap, queued and closed lines ("waited X ms, shown Y ms"). Add probes for how long the
host's section 4 lives. It saves nothing itself, but without it no option below can be judged: today's 1-s stamps cannot
see the timer, the latency or a 350 ms floor. Cross-PC numbers keep an error of about half the lane latency unless a
clock-offset ping is added. Cost S. Holds.

**B. Finding 11's orphan hold.** `OrphanSettled` (`NetSyncDialog.cs:1198`) becomes `settledLong && !hostHoldsInput`, so a
plain locked line is not orphaned while the host stands on my field with its control off. It saves no lag. It stops the
wrong-order close that a guest arriving first can make, and every option below makes that case more reachable. Cost S.
Holds, with two gaps:
- It does not cover a guest that lands while the host is still on the source field. Only the pre-intent passes below
  reach that case; there the orphan fires after about 7 s (`HostElsewhereMs` 5000 + `OrphanGraceMs` 2000).
- If the cat's leap ran with the host's control on, B does not fire there. The bench must read the host's section-7
  control bit, not assume it.

**C. Let the guest's own `Field()` pass when it matches the host's announced field (the bounce, CLA-11).** Add two pass
terms in `RedirectGuestFieldJump`: `dest` equals the pending follow (`_followWarpPending`), or `dest` equals a guest-side
cache of the last intent. The cache is needed because the host's section 4 probably clears one Update after its MAPJUMP.
A pass is "commit now": the copy's own `Field()` makes the same writes the follow would, without the timer. It saves
about 1.0-1.4 s per avoided bounce, and about 0.7-0.9 s in classes B and D. Cost S. The mechanism holds; the saving is
corrected here. The reviewers' corrections:
- It fixes the s161 bounce (intent first, then the own jump), but not the s158 one, where the own jump ran about 5 frames
  before the intent. C2 covers that.
- The cache must not clear on the stale source-field position frame. Each write tick sends position before state
  (`NetSyncSocket.cs:382-386`), so the guest usually sees the intent while the lane still reads the source field.
- It must re-check the s144 world hold and the s161 ATE holds at pass time.
- The story snapshot: as the guest's landing approaches the host's, the landing's story mirror can apply either the
  MAPJUMP-time frame or a post-landing frame (`ApplyStoryImpl`, `:918`). The story pin below fixes that.
- An ordinary (non-ATE) early landing gets the arrival law, not s162's landing start. So a dressed guest that arrives
  first can show as a double for longer: Finding 9's shape on ordinary fields.

**C2. A destination-blind own-jump pass** (proposed by the review, not yet verified). Let the copy's own `Field()` pass
while it plays the host's co-located control-off scene (s163's `PlaysHostScene` predicate), as s161's hub pass already
does. It keeps the copy's own entrance, and C's rewrite corrects it if the intent later names another field. It is the
only listed fix for the s158 shape: 351's inn-rest `Field(352)` has no `PreloadField` and runs before the intent.

**The story pin** (proposed by the review, not yet verified). The guest keeps the state frame that carried the intent
and applies that frame's story when it lands on that field. The host's VM halts at MAPJUMP, so that frame is exactly the
input to the host's `Main_Init`. Without the pin, tighter landings make the guest's story snapshot differ from run to run.

**The intent lifetime** (proposed by the review, not yet verified). Keep the host's section 4 for about 2 s, or until its
new field reports, and reset the publish clock at the out-of-band emit. Today the next 7 Hz publish can replace the
out-of-band frame in the write slot before the writer sends it. The guest then never sees the intent and falls back to
the serial follow and its 1.2 s debounce. All 27 two-PC follows got their intent, so this is robustness, not lag. It is a
host-side change on the same wire.

**D. A fade-aware follow.** Never restart a fade on a screen already going black. If the copy's own fade is heading to
black, wait for it; if the screen is already black, commit at once; count the follow in game ticks, not wall time.
- It removes the flash everywhere.
- It saves about 630 ms at 3x, and up to about 900 ms when the copy has already faded but its own `Field()` does not pass.
- It saves about 70-100 ms at 1x for a guest that has not faded.

Cost M. The mechanism holds, but the regression skeptic REFUTED it as stated. An early commit drops the guest's last
queued line at a door: a host close applies only 350 ms after the guest's page completes, and the commit destroys the
window. At 3x the commit at about 267 ms is below that floor. "Commit at once when black" fires exactly when a script
shows a line over black before `Field()`. **The fix:** gate every early commit on a backlog check (no locked line on my
copy with a queued host event for my field, with a cap). Two more caveats:
- One global fade slot is shared with the copy's own `FadeFilter`, so "complete" must mean "reads black", with a
  wall-clock fallback.
- `InitFade` restarts a full n-tick fade, so D must never re-init a fade already heading to black.

**E. A shorter follow fade when the guest has not already faded (class A).**
- 12 ticks, stock `FF9Wipe_FadeOut`'s own default (400 ms), saves about 470 ms on every gateway walk.
- 8 ticks saves about 600 ms.
- A near-instant cut saves about 850 ms (the host's own scene change is already a 0.01 s cut).

It only works with D's tick timing; otherwise it is a silent no-op behind the 0.9 s wall timer. It also needs D's backlog
gate, because a shorter window drops more of a lagging guest's last lines at 1x. Cost S. Holds. It is a taste call: the
guest sees a quicker cut than stock's door fade. A variant from the review sizes the follow from the HOST's booster
(section 10 is already on the wire), so a 3x host's door costs the guest about 0.3 s even when the guest's own mirror
refuses.

### Round-2 candidates

**F. A pre-intent at `PreloadField(5, dest)`.** The host announces the destination one host fade early, in a new state
section 11; an extra byte on section 4 would make an old guest commit early. The guest then fades in step and lands about
0.05-0.2 s after the host. It is the only lever that reaches gateway walks without a quicker guest cut. Cost L. The
regression skeptic REFUTED it as designed:
- 25% of `PreloadField` -> `Field` pairs have an ATE title card with `WaitWindow` between them, paced by the host's
  reading, so a watchdog cap misfires.
- Restoring control after a false positive is undecidable.
- An own pass before the host's MAPJUMP lands with a stale entrance and a stale story.
- It adds a third state to the s154 follow-race matrix.

A narrower form needs its own review: arm from the host's `WIPERGB` fade that follows a same-N `PreloadField` in the same
object, skip while an ATE pick or title is in flight, never restore control, and clear in `NoteFieldLanding`. Its real
reach is about 62% of `Field()` sites, and it does not reach the inn-rest bounce (no `PreloadField` there).

**G. The capped follow-hold (Finding 4's open half).** Hold the follow START while my copy still has the host's queued
lines on this field. Holding the commit instead would show those lines over a black screen with control off. The cap is
2 s per `F3.2-DESIGN.md:1029`, or 8-10 s per Finding 4. It adds lag by design, only when the guest is genuinely behind,
and it is the guard that stops D, E and F from dropping more last lines. It needs C's cache or the intent lifetime fix;
otherwise a deferred intent is lost within one publish. Cost M. Holds.

**H. A catch-up paging floor.** When the host's close for a page is already waiting, close the page after a short floor
instead of `MinShowMs` 350. `MinShowMs` is a readability choice; `Dialog.OnKeyConfirm` has no time guard. It saves
about 200-250 ms per page while the guest is behind, and has little effect on ordinary entries. A taste call: voiced
pages play shorter. Cost S. Holds.

**I. A typewriter mirror.** Finish my copy's typing when the host's same page reads complete (the host already
publishes page and complete per window). The guest then converges at the first page the host closes instead of at a
host rest. Cost M. Holds.

**N. Wake the transport's write loop on an out-of-band frame.** About 17 ms. Its real value is the same hole the intent
lifetime fix closes. Cost S.

**Config, no code: the direct transport on a LAN** instead of the relay (its construction path still exists,
`NetSyncClient.cs:2062`). It would take about 50-115 ms off every intent and close, judging by the measured 172/234 ms
round trips. Untested here.

### Rejected

- **J, park the guest's own jump until the intent arrives.** `RedirectGuestFieldJump` is not idempotent, so a per-frame
  rerun repeats its side effects and its logs. Its pre-intent pass also has F's hazards. C2 covers its case without a
  wait.
- **K, pop dialogue windows shut.** About 0.09 s a page, and it looks like a pop.
- **L, a catch-up sprint.** The lag metric is unsound: ticks since landing say nothing about where a lock-parked copy is
  in its scene. It also stacks with s163's no-overshoot product. After C and D only about 50-300 ms is left to win.
  `FastForwardFactor` is an integer bound by the SFX pitch law.
- **M, a host-side entry hold.** The guest sends no state frames, so the host cannot tell a guest loading toward it from
  one that deferred the follow (a menu, the world hold, an ATE episode). Every such door costs the host the full cap, and
  the release puts the guest ahead by construction.
- **Predictive commit** (load the guest at the pre-intent). Stock writes the field entrance after the fade and just
  before `Field()` (359's `Main_11`), and the guest's story would be from before the MAPJUMP.
- **A host hold through the stock 0x102 pause bit.** `FieldHUD` and `FF9TextTool` release it.
- **A guest asset preload.** `PreloadField` is ignored on PC builds, loads are synchronous, and the load difference
  measured about 0.

## 4. Recommendation

**Round 1, one engine round (s164): guest side plus the host's intent lifetime, no wire change.**
1. A, the instrument, first.
2. B, Finding 11's orphan hold.
3. C, with the story pin and the intent lifetime fix; C2 if its review holds.
4. D, with the backlog gate.
5. E at the owner's chosen length, or not at all; always with D's gate.

Expected: no more bounce reloads; scripted transitions land about 0.1-0.3 s after the host instead of about 1 s; every
follow at 3x about 630 ms shorter; no flash. Gateway walks stay at about 1 s unless E is taken: about 0.5 s at 12 ticks,
about 0.15 s with a near-instant cut.

**Round 2, only if round 1's millisecond stamps still show lag that matters:** G (it also closes Finding 4), then H and
I for fast paging, then the narrowed F if gateway walks still matter after E.

**The owner decides:**
1. The follow on a gateway walk: keep 24 ticks (no gain), 12 ticks (stock's wipe speed, about 0.5 s faster), or a
   near-instant cut (about 0.85 s faster, a hard cut).
2. Whether round 2's pre-intent (F) is wanted at all, given E.
3. The follow-hold cap, if G is built: 2 s or 8-10 s.
4. H's floor (350 down to 100-150 or 0 ms), if H is built.

## 5. Bench

`coop_field_swap_timing_duo.py` (not written yet): two real games on one desktop (`tools/harness/duo.py`), `stateevery 1`
on both, one clock.
- **FT-CAL:** the host warps to 30602 (the follow race's FE1 shape), with the host's landing sampled. Commit minus follow
  start must read 0.885-0.912 s today, and a lever that adds 200 ms to the commit must read +200 ms ± 1 frame.
- **FT-A:** a scripted exit, 359 -> 351 (359's `Main_11`, then 351's desk scene, first line win 3 text 129).
- **FT-B:** the bounce shape, 351's rest -> 352 (first line win 4 text 142). Predicted to bounce on a duo too.
- **FT-OWN:** "Dagger Tries" 351 -> 450, the own-jump baseline.
- **A host pace sweep:** the host presses Confirm D s after each line stops typing, D in {0.3, 1.0, 2.5}.

Per transition: the host's MAPJUMP, the guest's follow start and commit, the own-jump outcome, both landings, both
first-line opens, the per-line open and close deltas, and the convergence line. Pre-registered: about 0.95 ± 0.15 s
between landings on a follow, at most 0.3 s on an own pass, and 1.5-2.5 s plus a reload on a bounce. Each round-1 item
gets its own lever calibration.

The duo cannot show real network latency or the laptop/desktop load difference. Those need a two-PC replay with A's
stamps.

## Sources

- Workflow `wf_87a54375-399` (2026-10-29): readers (timeline, own Field, dialogue, sprint and barrier, evidence), a
  designer, and two skeptics (mechanism, regression).
- Evidence scripts in `swap-timing/`: `final.py` (the transition table and aggregates; writes `rows.json`), `conv.py`
  (per-line waiting or behind), `firstline.py` (first-line open lag), `drift.py` (clock offsets), `fe.py` (the duo's
  follow timings from the follow-race run directories), `preload_census.py` (the `PreloadField` census over
  `C:\gd\FFIX\reference\test2\`).
- Logs: `.harness-runs/twopc-r3-20261027`, `twopc-s158-20261028`, `twopc-s161-20261028`, `twopc-s163-20261029` (main repo).
