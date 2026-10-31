# Arrival guard (s164 addendum)

**Status: BUILT (2026-10-30): engine compiled and deployed; folded into the re-captured s164 patch
(`memoria-patches/s164-netsync-field-swap-timing.patch`); proven on the duo (two games on one desktop): DA-ARRIVE green at act on ARRIVE and red exactly under the `arrive` word. DA-GUARD anchored every in-scope landing in 13 runs but one: a true late anchor after a slow host load on CAL3 -> 250, harmless because that arrival's control was already back. Next: two PCs.** Design rev 2, review round 1 applied (15
findings, § Review log); the build's departures from it are in the Build log. This is owner decision 8 of
`SWAP-TIMING-S164.md` (rev 3, :1807): the landing-scoped arrival guard that DA-ARRIVE's predicted red at act makes a ship blocker
(R2 :41, V5 :77, :1677-1681). It folds into s164 as one change tagged `[ff9mapkit netsync s164]`, lands before s164's README row,
and ARRIVE becomes its calibration (guard off red, guard on green). Engine cites are against `C:\gd\FFIX\Memoria\Assembly-CSharp`
with s164 applied, before the guard (the Build log has where the guard's hunks landed); kit cites are against this worktree.
**INFER** marks a deduction and names the row that settles it. It merges two independent designs; see the review log.

Constraints held: harness protocol 5, wire v14 with no new byte or section, no host code, `DwellMs`/`StartRule`/s158's proof line
untouched, levers released with the harness, every pure rule tabled with killing mutants.

## Problem

s164 lands a following guest about 0.5 s behind its host on a gateway follow (DF-FAST) and 0.1-0.3 s behind on a scripted exit
(C's own pass). s163 measured 1.04 s (`FIELD-SWAP-TIMING.md` §1, n = 23).

At a WORDLESS arrival both copies run the same control-off script from their own landings. So s158's step-out base lasts about
A − L, where:
- the base = the host on my field, its control off, mine off (`NetSyncStepOut.cs:239-257`);
- A = the host's control-off time after its landing;
- L = the guest's landing gap.

The base re-arms whenever a term fails (:556-567). With no fresh line, `StartRule` steps out once the base reaches `DwellMs` 1500
(:147, :261-271). In practice THE ARRIVAL LAW (:22-23) was tuned under L = 1.04 s. The table ignores latencies, with B ≈ G. Whether
the guest reads the host's landing (Hs) before or after its own landing decides which guard row applies: the guest's landing hook
comes at the end of its ~0.32 s blocking load, so at L ≤ ~0.35 s the load window [H + L − 0.32, H + L] covers the host's first
landed frame (H + δx, δx ≈ 50-90 ms) and Hs is read **late by construction**; at L ≈ 0.5 the load starts at H + 0.13-0.18 s, after
that frame, and Hs is read **in time** in the normal case.

| Rule | The dwell counts from | A wordless arrival steps out when A ≥ | L 0.1 | 0.3 | 0.5 | 1.04 |
|---|---|---|---|---|---|---|
| s163 | the base start B | D + 1.04 | | | | 2.54 s |
| round 1, no guard | B | D + L | 1.6 | 1.8 | 2.0 | 2.54 |
| decision 8 read literally (§ Mechanism) | my landing G + L | D + 2L | 1.7 | 2.1 | 2.5 | 3.58 |
| **this guard, Hs read in time** (a follow, L ≈ 0.5 and up) | max(B, min(Hs + K, B + K)) | D + max(K, L) | (2.54) | (2.54) | **2.54** | **2.54** |
| **this guard, Hs read late** (an own pass, L ≤ ~0.35: the default there) | ≈ G + K (the cap) | D + L + K | **2.64** | **2.84** | (3.04) | (3.58) |

Parenthesised cells are the off-case for that gap (an own pass read in time needs a guest stall-free load that ends before H + δx; a
follow read late needs a stall that spans the host's landing).

- **The newly exposed band is A ∈ [1.5 + L, 2.54 s].** At a 0.5 s follow that is 2.0-2.54 s, which is risk 14's band (:1783). At a
  0.1 s own pass it is 1.6-2.54 s, which risk 14 does not name. 30602's auto settle (50 ticks, about 1.67 s, :1622) falls inside
  it at an own-pass gap of 0.15 s or less (INFER: no own-pass arrival on 30602 is benched).
- **The own-pass band the guard newly leaves showing the double:** A from 2.54 s to L + 2.54 s (2.64-2.84 s at L 0.1-0.3). Those
  arrivals stepped out for a moment on s163; under the late read they show the double for their whole length, bounded by K (§ Worst
  case, the late-read bias; a rev-4 follow-up on risk 14).
- **ARRIVE** (30611) is predicted RED at act on round-1 code. At today's `entry_settle = 68` (A ≈ 2.27 s + the overhead O) the base
  is about 1.8 s; at the retuned 64 (§ Benches) about 1.65 s nominal. It is predicted green on `fade old`, at about 1.25 s (:1704).
- **Why it matters.** A dwell OUT at an arrival hides a dressed guest's body behind a Zidane stand-in, hides the host's ghost and
  zeroes my wire mask (`NetSyncStepOut.cs:28-36`). On screen that is the flash of Zidane that THE ARRIVAL LAW exists to stop.

## Signals

| Signal | Where it comes from | Clock | Latency and error |
|---|---|---|---|
| **G, my landing** | `ApplyStoryBeforeEvents` → `NetSyncSwap.OnFieldLoad(SwapField())`, before StartEvents runs Main_Init (`NetSyncClient.cs:986-1003`, `NetSyncSwap.cs:1978`). `ArriveLanding` is OnFieldLoad's **first** statement (§ Hooks), so it sees every landing, including the unjoined ViaSame/ViaOther ones that return at :2005. It numbers the landing (`_arriveLanding`, its own counter) | TickCount, the rule clock (`NetSyncSwap.cs:22`); the swap clock for `land_t` | 0 |
| **Hs, the host's landing as I first saw it** | **Host:** the landing hook flips `_intentLanding` (`NetSyncClient.cs:7135-7153`). Every frame built after it carries section 4's bit 0 (:7219-7227; `IntentSectionBody`, `NetSyncSwap.cs:649-652`). Section 4 rides for at least 1 s past the landing and 2 s past the emit (LIFE, :672-686). A frame is built by a dirty push (`NetSyncClient.cs:7386-7391`) or the 150 ms publish (:2354-2358, whose gate has expired during the host's own load, so the first frame after the hook is the host's next Update); the writer re-sends every 33 ms (`NetSyncSocket.cs:923`). **Guest:** `ObserveHostDialog`'s new-frame branch → `SwapNoteHostFrame` → `NoteHostFrame`'s section-4 branch (`NetSyncClient.cs:2415, 8351-8395`; `NetSyncSwap.cs:1101-1116`). `now` is that Update's TickCount; the record also keeps the landing number it was seen in | TickCount | δx = one host frame after its hook, ≤ 33 ms writer tick, network, ≤ 1 guest frame (≈ 50-90 ms on the duo's local link; at least ~16 ms), plus any guest stall. A stall that spans the host's landing (my own load, at L ≤ ~0.35 s by construction) reads Hs late. That error always means more suppression, and the cap bounds it |
| **B, the base start** | `_baseSince` (`NetSyncStepOut.cs:563-567`). It needs my control character bound (:549-553) and the host's control-off view for this field (`NetSyncClient.cs:7424-7427`, cached by ServiceDialogAuthority :8321, :8333-8336) | TickCount | B = G + bind time |
| **The base end (the host's control back)** | Section 7 b1 (`HostDialogFlags`, `NetSyncClient.cs:7266-7269`). A wordless control change is no dirty edge, so it rides the 150 ms publish | n/a | δ7 ≤ 150 + 33 ms + network + 1 frame (0 to ~216 ms). The same in s163 and round 1 |
| *Not used:* the position lane `rs.Field` | It says where the host is, not when it landed | | |
| *Not used:* the transport's arrival stamp | `StateProbe.InStateTs` holds only the latest payload, re-sent every 33 ms (`NetSyncSwap.cs:1121-1127`), so it reads about "now" | | |
| *Not used:* PIN's `LandSeenTick` | The same signal (`NetSyncSwap.cs:1408-1412`), but PIN consumes its entry at my landing (`ConsumePinAt`, `NetSyncClient.cs:1003`), and the guard needs it afterwards | | |

**Why the base rarely leads the anchor.**
- The position lane names a field only once the host's control character has a bound field actor (`NetSyncClient.cs:2318-2329`).
  That happens after its landing hook has set the bit.
- The base needs that lane on my field.
- So B can lead Hs only by the gap to the host's first frame built after the hook plus one write tick, or by a guest stall.
- The cap (§ Mechanism) makes the bound unconditional.

## Mechanism

### Reading decision 8's phrase

The phrase is "a dwell counted from max(the base start, my landing + the host's arrival lead)".

- **Read literally,** the lead is my measured gap (G − Hs). The origin is then Hs + 2L and the threshold D + 2L. That is right only
  near L = 0.5 (2.5 against 2.54 s). It still exposes a 0.2 s own pass at 1.9 s, and at s163's own lag it is 1 s more lenient than
  s163.
- **Taken here:** "the lead the host is owed", K − (G − Hs), where K = s163's measured gap. Then my landing + that lead = Hs + K for
  every G.
  - It puts my dwell OUT at Hs + K + D, the instant s163's fired, whatever L.
  - On ARRIVE the L terms cancel, so the green does not depend on how fast the follow ran.
- **Also rejected:** my landing + K. It is lag-dependent and over-guards `fade old`.
- Both rejected readings are mutants (`arrive_literal_lag`, `arrive_from_my_landing`), so a review can flip the choice with one
  line. **This reading is an owner question** (§ Open, item 1): the review agreed with it, but it adds a constant decision 8 does not
  name.

### The rule

```csharp
// [ff9mapkit netsync s164] THE ARRIVAL GUARD -- pure rules (NetSyncSwap.cs, beside PIN); Int32 TickCount deltas only (unchecked: the
// csproj sets no CheckForOverflowUnderflow, so a delta wraps; the battlewire twins use _i32)
internal const Int32 ArrivalLeadMs = 1040;      // K: s163's measured landing gap (FIELD-SWAP-TIMING.md §1, n = 23); a seed (risk 7)
internal const Int32 LeadNone = Int32.MinValue; // `lead_ms` null: this landing never anchored
internal const Int32 ArmOn = 0, ArmRole = 1, ArmLever = 2, ArmWorld = 3;
internal const Int32 SpendNone = 0, SpendControl = 1, SpendField = 2, SpendOut = 3, SpendSession = 4;
internal const Int32 EndNone = 0, EndSpared = 1, EndDelayed = 2, EndLine = 3, EndAte = 4;
internal const Int32 EvLanding = 0, EvLateEdge = 1, EvSpend = 2;
internal const Int32 CountNone = 0, CountArm = 1, CountLateArm = 2, CountUnanchored = 4;

// strict: an s163 host's 3-byte body is NO landing here (IntentLandedOf, :656-659, reads it landed: PIN's fail-safe, an early anchor here)
internal static Boolean HostLandSeenOf(Byte[] b) { return b != null && b.Length >= 4 && (b[3] & IntentFlagLanded) != 0; }
internal static Boolean ArriveHostEdgeRule(Int32 lastNonce, Int32 lastField, Int32 nonce, Int32 field, Boolean landed)
{ return landed && nonce >= 0 && field > 0 && (nonce != lastNonce || field != lastField); }   // the FIRST landed frame per (nonce, field)
// read at MY landing: the role, then the lever (every landing), then a world rejoin (R3's exclusion, LandingFromWorld :1528)
internal static Int32 ArriveArmRule(Boolean roleOk, Boolean leverOld, Boolean fromWorld)
{ return !roleOk ? ArmRole : leverOld ? ArmLever : fromWorld ? ArmWorld : ArmOn; }
// does the record anchor landing number `landing` on fld? It names fld and was seen in THIS landing's interval: before it and after my
// previous landing (seenLanding == landing - 1) no more than IntentLoadCapMs before it, or after it (seenLanding == landing: the late form).
// rSinceMs = my landing's tick - the record's seen tick. A record from before my previous landing is stale (a battle return, a reload).
internal static Boolean ArriveAnchorRule(Boolean rSet, Int32 rField, Int32 rSeenLanding, Int32 rSinceMs, Int32 fld, Int32 landing)
{ return rSet && fld > 0 && rField == fld && (rSeenLanding == landing || (rSeenLanding == landing - 1 && rSinceMs < IntentLoadCapMs)); }
internal static Boolean ArriveHoldsRule(Boolean armed, Boolean anchored, Int32 armField, Int32 fld)
{ return armed && anchored && armField == fld; }
// the dwell counts from max(B, min(Hs + K, B + K)): never earlier than s158, never more than K later, whatever the anchor
internal static Int32 ArriveDwellAgeRule(Boolean holds, Int32 baseAgeMs, Int32 sinceHostMs)
{ return holds ? Math.Min(baseAgeMs, Math.Max(sinceHostMs - ArrivalLeadMs, baseAgeMs - ArrivalLeadMs)) : baseAgeMs; }
internal static Boolean ArriveHeldRule(Boolean heldAlready, Int32 baseAgeMs, Int32 dwellAgeMs)   // s158 would step out here; the guard holds
{ return !heldAlready && baseAgeMs >= NetSyncStepOut.DwellMs && dwellAgeMs < NetSyncStepOut.DwellMs; }
internal static Int32 ArriveSpendRule(Boolean armed, Int32 armField, Int32 fld, Boolean myCtl, Int32 ctlBackMs, Boolean stepOutActive)
{
    if (!armed) return SpendNone;
    if (fld != armField) return SpendField;
    if (stepOutActive) return SpendOut;
    if (myCtl && ctlBackMs >= NetSyncStepOut.StepInMs) return SpendControl;   // s162's debounced spend (NetSyncAte.cs:404-407)
    return SpendNone;
}
// a HELD episode's end (an unheld one is s158's own and has none). One episode = one base (one _baseSince): a re-armed base ends it,
// because s158's own dwell restarted there too. framesSinceDwell > 2 is GhostHide's freshness idiom (NetSyncStepOut.cs:755-757); it
// classifies in the same frame whichever order ArriveTick and ServiceStepOut run in. An active step-out precedes a re-armed base.
internal static Int32 ArriveEndRule(Boolean held, Int32 framesSinceDwell, Boolean newBase, Boolean stepOutActive, Int32 outWhy)
{
    if (!held) return EndNone;
    if (stepOutActive) return outWhy == NetSyncStepOut.OutDwell ? EndDelayed : outWhy == NetSyncStepOut.OutAte ? EndAte : EndLine;
    return newBase || framesSinceDwell > 2 ? EndSpared : EndNone;
}
// the counters one guard event bumps, each at most once per landing, armed guards only: EvLanding `arms` (anchored, lead < K);
// EvLateEdge (a fresh edge for the guard's field after its landing) `late_arms` once and `arms` if not yet; EvSpend `unanchored`
internal static Int32 ArriveCountRule(Int32 ev, Boolean armed, Boolean anchored, Int32 leadMs, Boolean armCounted, Boolean lateCounted)
{
    if (!armed) return CountNone;
    if (ev == EvLanding) return anchored && leadMs < ArrivalLeadMs ? CountArm : CountNone;
    if (ev == EvLateEdge) return (lateCounted ? CountNone : CountLateArm) | (armCounted ? CountNone : CountArm);
    return ev == EvSpend && !anchored ? CountUnanchored : CountNone;
}
```

`ArriveDwellAgeRule` has four properties, each a SelfTest row:
1. It never steps out earlier than s158: the result is at most the base age.
2. It never holds more than K past the base start: the result is at least the base age − K, even for a stale, future, garbage or
   wrapped anchor.
3. It is inert for a base that starts at or after Hs + K.
4. At s163's lag it is exactly s158.

**The lead, per landing.** At the landing, `leadMs` = G − Hs when the anchor rule holds, else `LeadNone`; `late` = false. After the
landing, every fresh edge for the guard's field (seen with `seenLanding == landing`) replaces the anchor: `leadMs` = G − Hs
(negative), `late` = true. The host's newest landing on my field is the one whose control-off script runs now, and the cap bounds any
replacement to K past the base start, so a replacement mid-episode can only add suppression within the bound.

### State (guest only: a client or the selftest role; main thread; "armed bool + delta")

| Latch | Set | Read | Cleared |
|---|---|---|---|
| **R, the host-landing record** `{field, nonce, tick, seenTick, seenLanding, seenT, bench}` | `ArriveRecordEdge(body, field, nonce, tick, seenTick, seenLanding, bench)` (as built), the shared writer. Live: `ArriveHostFrame` in `NoteHostFrame`'s section-4 branch, right after `PinHostFrame` (:1116), with PIN's client gate at that call (`state != null && HarnessEnabled && HarnessRole == "client"`, the form of :1397), and only when `ArriveHostEdgeRule(…, HostLandSeenOf(body))` holds; `tick = seenTick = now`, `seenLanding = _arriveLanding`. Bench: `arrivebench` (§ Lever) calls the same writer through the real codec | `ArriveAnchorRule` at my landing and at a late edge | Replaced by the next edge. `ForgetHostNonce` (:1186), `ResetSession` (:1059). The release drops a record the bench wrote. A replaced or stale R never touches a guard already anchored: the guard copies Hs |
| **The guard** `{arm, armed, spent, field, landing, landTick, landT, anchored, hsTick, leadMs, late, armCounted, lateCounted, backArmed, backSince, logged}` | `ArriveLanding(fld)`, OnFieldLoad's first statement, at **every** landing (follow, own pass, kick, bounce, rejoin, battle return, ATE DEST, world). It numbers the landing, writes a bench record with lead ≥ 0 (§ Lever), then `arm = ArriveArmRule(roleOk, ArriveOld, LandingFromWorld())`, `armed = arm == ArmOn`, `anchored = ArriveAnchorRule(…)`, `hsTick`, `leadMs`, `late = false`; it resets `spent`, the counted flags, `backArmed`/`backSince` (a control-back carried over from the last field never spends the fresh guard) and the episode. The role and the lever are read **at the landing**, so a lever flip mid-episode waits for the next landing. A late edge for `field` (§ The lead) sets `anchored`, `hsTick`, `leadMs`, `late` | `ArriveHoldsRule(armed && !spent, anchored, field, fld)` | Spent by `ArriveSpendRule` in `ArriveTick` (`spent` = true; `leadMs` stays for the report). `ResetSession` / `ForgetHostNonce` (session). Replaced at the next landing |
| **The episode** `{on, frame, baseStart, base, dwell, shift, held}` | `ArriveDwellAge` on each Tick where the hold applies and neither a line nor `ate` decided. `baseStart = now − baseAgeMs`; a different `baseStart` from the stored one is a new base: `ArriveEndRule(held, 0, true, false, OutNone)` classifies the old episode first, then a new one starts with `held` false | `ArriveTick` evaluates `ArriveEndRule(held, Time.frameCount − frame, false, NetSyncStepOut.Active, why)`, with `why` from `NetSyncStepOut.HarnessWhy` (:1047), before it evaluates the spend | At classification (`on` false; `last` takes its values and end) |

**No time lapse of R and no episode latch.** Each spend coincides with a base that has already failed:
- a field change, or my control back, fails `BaseWhyNot`;
- an active step-out never reads the dwell;
- the guard copies the anchor (`hsTick`), so R's later replacement (the host's next landing, by which time it has left my field)
  changes nothing;
- the formula is inert past Hs + K anyway.

Staleness lives at the anchor (the landing number and the `IntentLoadCapMs` window), not as a lapse of R. It changes no verdict (a
record from before my previous landing, or 10 s old, already gives an inert formula) and exists so `lead_ms`, `arms` and
`unanchored` say what happened. The only flip that can happen mid-episode is the sticky fault, and it fails open to s158, as PIN's
`_pinFaulted` does.

### Hooks

- **`NetSyncStepOut.cs:570`, the one behaviour hunk** (plus a comment-only header paragraph):

  ```csharp
  // [ff9mapkit netsync s164] THE ARRIVAL GUARD (NetSyncSwap.ArriveDwellAge): at my landing a wordless base's dwell counts from the
  // host's landing as I saw it + ArrivalLeadMs, at most ArrivalLeadMs past the base's start -- DwellMs, a line and s162's landing decide as before
  Int32 start = StartRule(line, NetSyncSwap.ArriveDwellAge(fld, now, now - _baseSince, line || landing), landing);
  ```

  - `ArriveDwellAge` returns `baseAgeMs` unchanged when the guard does not hold or the fault is set.
  - Otherwise it applies the rule with `sinceHost = now − hsTick`.
  - When nothing decided, it records the episode (a new base first ends the old one) and prints the held line once.
  - It has its own try: a throw sets the sticky fault, is logged once (item `ARRIVE`) and returns `baseAgeMs`.
- **`NetSyncSwap.cs`** (every guard entry point has its own try with item `ARRIVE`: sticky fault, logged once per site, never
  throws into its caller; as built, a set fault makes `ArriveLanding`, `ArriveHostFrame` and `ArriveTick` inert and drops the guard,
  the episode and the bench, so `armed` reads false, while `ForgetArrive` and the readers still run):
  - `ArriveHostFrame(state, body, field, nonce, now)` in `NoteHostFrame`'s section-4 branch, right after `PinHostFrame` (:1116) and
    before `if (SeenRule(true, nonce, _seenNonce))`. Its own try keeps a guard fault out of item A's catch (:1138-1141), so A's seen
    edge always runs.
  - `ArriveLanding(fld)` as `OnFieldLoad`'s **first statement**, before `Int64 t = NowMs()` and A's try (:1978-1980): before
    `LandViaRule`, `Join` and the unjoined `if (!joined && (via == ViaSame || via == ViaOther)) return;` (:2005), so it runs on the
    battle returns, reloads and solo warps that never join a record, and a throw in A cannot leave the previous guard standing.
  - `ArriveTick(myField)` as `GuestTick`'s **first** statement, before the `_icField <= 0` return (:1299). `GuestTick` runs every
    client Update (`NetSyncClient.cs:2417`, before `ServiceStepOut` at :2429) and every selftest tick (:1984, after `ServiceStepOut`
    at :1982). `ArriveEndRule` classifies a re-armed base inside `ArriveDwellAge` and a stale or stepped-out episode at
    framesSinceDwell 3 / the first active frame, so both orders classify the same end (a client one frame later on an OUT); no spend
    can happen while a base holds.
  - `ArriveTick` reads the user control (the `PersistenSingleton<EventEngine>` read that `SwapNoteHostFrame` already makes),
    `NetSyncStepOut.Active`, `NetSyncStepOut.HarnessWhy` and `Time.frameCount`, and writes a late bench record. It never throws. On a
    client it costs three bool reads per idle Update (as built: the guard, the episode and the bench, since the bench's late write runs
    on an unarmed guard too).
  - `ForgetArrive("session")` in `ResetSession` and `ForgetHostNonce`.
- **`NetSyncClient.cs`:** 0 hunks.
- **A host or a solo game** never arms the guard and never reaches `ArriveDwellAge`, because its base fails on `eligible` first.

### Predicted numbers

E = A + δ7, the host's control-off as the guest sees it end. A = (ARRIVE's `entry_settle` ticks) / 30 + O, where O is the overhead
from the landing hook to the grant (the hold sits before `set MAP159 = 1` and the grant is Main's re-affirm,
`content/entry_settle.py:122-133`; CAL2's measured overlap of 1.2-1.35 s for a 1.667 s hold at L 0.45-0.5 puts O at about 0-180 ms).
Then, with Hs read in time:

- raw base peak = E − L − bind;
- guarded dwell peak = E − δx − K;
- the red (guard off) needs E ≥ D + L + bind ≈ 1950-2100 ms (L 0.45-0.5, bind up to ~100);
- the green needs E < D + K + δx ≈ 2556-2630 ms (δx 16-90).

δ7 is one draw per run and moves both bounds together, so the window in E is about 500 ms wide. At `entry_settle = 68`, E spans
2267-2663 ms and the green misses whenever O + δ7 − δx ≥ 273 ms (O 180 with δ7 ≥ ~110 ms): a publish-phase flake on the ship gate
with a correct guard. **ARRIVE is retuned to 64** (§ Benches): E spans 2133-2529 ms, and inside O ≤ 180 ms and δ7 ≤ 216 ms neither
side misses (a green miss needs O + δ7 − δx ≥ 407 ms; the red reaches with ≥ 33 ms to spare at bind 100). 65 would leave a 7 ms
corner on the green side and 63 a zero margin on the red side. The control on `fade old` shares the green bound (its gap IS
s163's), so 68 put the control at the same risk.

| Arrival (ARRIVE at 64) | L | B − Hs | Raw base peak | Guarded dwell peak | Verdict |
|---|---|---|---|---|---|
| ARRIVE at act, Hs read in time (the normal case) | 0.5 | ≈ 450-580 | ≈ 1580-2080 | E − δx − K ≈ 1000-1475 (typical ≈ 1235) | no OUT; an OUT needs O + δ7 − δx ≥ 407 ms (a margin miss, § Benches) |
| ARRIVE at act, Hs read late (a stall spans the host's landing) | 0.5 | ≤ 0 | the same | ≈ raw − K (the cap) ≈ 540-1040 | no OUT |
| ARRIVE under `swap arrive old` | 0.5 | n/a | ≈ 1580-2080 | = raw | **OUT** (the red) |
| ARRIVE-OLD and CAL0 (`fade old`) | 1.04 | ≈ 1040-1090 | ≈ 990-1490 (typical ≈ 1220) | ≈ raw (shift ≤ about 100 ms) | no OUT (the control) |
| CAL2 (auto settle, 50 ticks) | 0.5 | ≈ 500 | 1200-1350 | ≤ about 800 | no OUT |
| An own pass, A = 2.0 s (Hs read late by construction) | 0.2 | ≤ 0 | ≈ 1750 | ≈ 710 (the cap) | no OUT (round 1: OUT) |
| A wordless 3.0 s scene at act | 0.5 | ≈ 500 | ≈ 2500 | OUT at Hs + 2540 | OUT, ≈ 490 ms after round 1 |

At act the in-time read is the normal case: the host's first landed frame reaches the guest at H + δx, and the guest's 0.32 s
blocking load only starts at H + 0.13-0.18 s (rev 1's INFER that the load straddles it is withdrawn). The sign of `arrive.lead_ms` on
ARRIVE, CAL2 and DESK confirms it; a stall can still read late, and that case is green too.

## Composition with s158/s162

- **What stays byte-identical.**
  - `StartRule` (:261-271): s162's `ate` term and the fresh-line term still win before any age.
  - s158's proof line stays `step-out selftest: OK (56 rows, 20 mutants caught, dwell 1500 ms, step-in 500 ms)` and becomes a
    regression gate.
  - `BaseWhyNot`, `EndRule`, `AnchorRule`, s159's "a start needs a controlled actor" (:549-553), s161's ATE caption term (:555) and
    every lever.
- **The base clock is untouched.** `_baseSince`, its re-arm and `HarnessBaseAgeMs` (:1049) stay raw, so
  `netsync.stepout.base.age_ms` still measures the exposure DA-ARRIVE reaches on. The guarded age is published separately.
- **s162's landing term is untouched.** `LandingTermNow`, `WireMaskRule` and `GhostHideRule` (:295-312, :752-787) do not change.
  The guard never zeroes a wire mask and never hides a ghost; that would be s162's `landing_every_arrival` mutant (:1343).
  - An ATE DEST landing arms the guard too, but `OutAte` decides first.
  - An `ate` OUT spends the guard (SpendOut) and ends a held episode as `ate`.
- **THE ARRIVAL LAW** gets s163's margin back for anchored field-to-field arrivals, measured from the host's landing. Unanchored
  arrivals keep `DwellMs` from the base start, which is round 1. World rejoins are not armed (R3's exclusion).
- **The speed mirror is untouched** (`NetSyncSpeed`). Risk 14's second half stays accepted (`SPEED-MIRROR.md:120-121`).
- **The header paragraph** for `NetSyncStepOut` (comment only):

  > [ff9mapkit netsync s164] THE ARRIVAL GUARD (THE ARRIVAL LAW made lag-invariant, ARRIVAL-GUARD-S164.md): at my landing, a
  > wordless base counts toward the dwell only from ArrivalLeadMs after the host's landing as I first saw it (section 4's landed
  > bit), and never more than ArrivalLeadMs past its own start. The base and its age stay raw. It never starts an OUT earlier than
  > s158, never holds a line or s162's `ate` start, never arms on a world rejoin, and is spent by a field change, any step-out, or my
  > control back for StepInMs. `swap arrive old` = round 1's rule (CALIBRATION).

## Worst case

**Bounds, from the rule:**
- **Added delay** to a dwell OUT = min(K, max(0, Hs + K − B)), which is **at most 1040 ms** for any anchor. Rows `age.cap_out`,
  `age.future`, `age.wrap`.
- **The OUT fires at** max(B + D, min(Hs + K + D, B + K + D)). The guard postpones an OUT and never prevents one: after the shift,
  the guarded age grows 1:1 with time.
- **Zero delay** when:
  - the base starts at or after Hs + K;
  - no record anchors the landing (none, stale, another field, or older than `IntentLoadCapMs`);
  - the lever was old at the landing, or the landing came from the world map;
  - the guard is spent;
  - a line or `ate` decides.
- **Against s163** on an anchored arrival read in time: the same instant relative to the host's landing. Read late: at most L later.

**Real cases where the guest should step out and is delayed** (classes, not a census; decision 8's census alternative is not run;
`ends.spared` and `ends.delayed` measure them in play):
1. **A wordless entry beat longer than about 2.5 s,** such as a party walk-in, a camera pan, or actors posed before the first
   line. 282 stock fields walk a party actor, and 120 place or walk one within 40 u of the player's points; both are upper bounds
   (`GUEST-TRAVERSAL-TWO-PC.md:134-136`). The OUT moves to the s163 instant.
2. **A cutscene that crosses a `Field()`** and opens wordless on the new field. The step-out steps in on the field change (InField)
   and re-starts after the guarded dwell.
3. **The guest lands first or level** (a slow host, a 0.1 s own pass), or Hs is read late. The cap binds: +1040 ms past the base
   start.

**The late-read bias.** When my load spans the host's landing, the threshold becomes D + L + K instead of 2.54 s. At an own pass
(L ≤ ~0.35 s) that is the default, not a corner: 2.64-2.84 s at L 0.1-0.3. Arrivals with A between 2.54 s and L + 2.54 s used to step
out for a moment on s163; they now show the double for their whole length, bounded by K. At act (L ≈ 0.5) the read is in time
unless a stall spans the host's landing. `lead_ms`'s sign measures it. The deferred fix is under Not done.

**Exposure left at round 1's rule (armed, no anchor), counted in `unanchored`:**
- A host on `swap life old`: no landed frame is sent (INFER; the host's `intent.landed_frames` Δ settles it).
- An s163 host, whose section 4 has 3 bytes.
- A guest stall that spans the whole landed-frame window.
- Battle returns, save loads and reloads: the host's record is stale (seen before my previous landing, or more than
  `IntentLoadCapMs` before this one), and no new landed edge comes, since a battle is no MAPJUMP.

**Not armed (round 1's rule by design), counted in `world`:** a landing of mine from the world map (`LandingFromWorld`, gMode 3 at
the hook, the read PIN's R3 takes, `NetSyncSwap.cs:1527-1532`). A world script's `Field()` does emit an intent and the host's landing
does carry the landed bit (`EventEngine.DoEventCode.cs:1040`; `NetSyncClient.cs:7135-7153, 7219-7227`), and the guest reads section 4
on the world map too (`NetSyncClient.cs:2413-2415`), so the guard *could* anchor there; it is excluded because s164 left that gap
alone: world rejoins commit at once and land 1-3 s later (s144's branch, R3), so s158's law there is s163's. INFER: the world
benches' reported `lead_ms` settles that the gap did not shrink; a short one is the trigger to arm there in a later round.

**The double's length.** On an anchored arrival with A ≥ 2.54 s, the OUT fires at s163's instant measured from the host's landing.
Because the guest now lands about 0.5 s earlier, Finding 9's dressed double shows about 0.5 s longer than on s163 before it. Risk 14
already accepts that, and it comes from landing earlier, not from the guard. What the guard removes is round 1's arrival flash.

## Lever, state, log

**Levers** (s164's one scheme; role checked at set time; plain getters; released on every role by `NetSyncSwap.HarnessRelease` and
by `swap clear` through `ReleaseLevers`, :2597-2662):
- **`netsync swap arrive act|old`**, `OpGuest` (a client or the selftest role).
  - `old` = CALIBRATION: s158's dwell from the base start at every landing.
  - It is read at the landing, so the bench sets it before the warp.
  - A host gets `swap_refusal_guest_side("arrive")`.
  - It is a `swap` lever, not `stepout`, because `netsync stepout` refuses anything but the selftest role
    (`NetSyncStepOut.cs:1181-1188`), and DA-ARRIVE's gate runs on the duo's real client.
- **`netsync swap arrivebench <lead>`**, `OpBench` (the selftest role), with lead in −1000..5000 ms.
  - It is one-shot at my next landing. It writes R for the landed field through the **real codec**: `IntentSectionBody(fld, nonce,
    true)` → `AppendSection` / `TryReadSection` → `HostLandSeenOf` → `ArriveHostEdgeRule` → `ArriveRecordEdge` (the live writer's
    body; the client gate sits at the `NoteHostFrame` call, so the selftest role reaches the body only here), with a fresh bench nonce.
  - A lead of 0 or more writes R **inside `ArriveLanding`, before the anchor is evaluated**, with `tick = G − lead`, `seenTick = G`
    and `seenLanding = landing − 1` (the bench host landed before me, so the record belongs to this landing's interval and to no
    later one).
  - A negative lead writes it in `ArriveTick` at the first tick at or after G + |lead|, with `tick = seenTick = now` and
    `seenLanding = landing`: the late form, through the same late-edge path as a live edge.
  - The release forgets the bench and any record it wrote.
  - It proves the rules, the writer and the late path on the live landing and step-out; it does not reach `ArriveHostFrame`'s real
    call site or the live Hs latency. Those are proven only by the duo (DA-ARRIVE's named red and DA-GUARD).
- **Source changes:**
  - The `Usage` literal (:2284) gains `arrive act|old` in the client list and `arrivebench <lead_ms>` in the selftest list.
  - `OpRole` (:2291) gains both ops.
  - `HarnessRelease`'s `any` test gains them.
  - `ItemNames` (:203) gains `"ARRIVE"` (`ItemArrive = 6`), and `FaultsBy` (:365, sized by `ItemNames`) grows to 7.

**State** (additive under protocol 5):
- `netsync.swap.levers.arrive` (null | "old") is the last key of `levers`, after `hostctl_off` (`HarnessAgent.cs:5254-5263`).
- `netsync.swap.arrive` is the last key of `swap`, after `selftest`.
- The netsync-off catch literal (`HarnessAgent.cs:4107`) gains **both**: `levers` ends `"hostctl_off":false,"arrive":null}` and
  `swap` ends `"selftest":null,"arrive":{…}` at the sentinels below.

The block, live at rest (`arrival_lead_ms` reads 1040):

```
"arrive":{"arrival_lead_ms":1040, "armed":false, "field":-1, "land_t":-1, "lead_ms":null, "late":false,
  "host":{"field":-1, "nonce":-1, "seen_t":-1, "age_ms":-1, "bench":false},
  "episode":{"on":false, "held":false, "base_ms":null, "dwell_ms":null, "shift_ms":null},
  "last":{"field":-1, "lead_ms":null, "end":null, "base_ms":null, "dwell_ms":null, "shift_ms":null},
  "arms":0, "late_arms":0, "unanchored":0, "world":0, "held":0, "ends":{"spared":0, "delayed":0, "line":0, "ate":0},
  "spends":{"control":0, "field":0, "out":0, "session":0}, "bench":{"armed":false, "lead_ms":null}, "faults":0}
```

The sentinel form (the catch literal and `SWAP-TIMING-S164.md`'s `netsync.swap` fence): the same keys in the same order, with
`arrival_lead_ms` −1 and every other value exactly as printed above.

- `armed` = this landing's guard is armed and not spent; `field` / `land_t` = its landing.
- `lead_ms` = G − Hs for my last landing, negative when late, null when it never anchored.
  - It is reported whether the guard is armed or not (a world rejoin, `arrive old`): it decides no verdict, and DA-GUARD reads it.
- `host` = R: `seen_t` (swap clock) when it was recorded, `age_ms` = now − its tick (the anchor), `bench` for a bench record.
- `arms` counts armed landings anchored with `lead_ms` < K, at the landing or at its first late edge (the ones the guard can shift).
- `late_arms` counts armed landings first anchored, or re-anchored, by a late edge (once per landing).
- `unanchored` counts spends of an armed guard whose landing never anchored.
- `world` counts landings not armed because they came from the world map.
- `episode.on` says whether a hold ran in the last 2 frames; its values are null when off. The guarded `dwell_ms` can legitimately be
  negative (at a base of 1039 ms on a late anchor it reads −1), so no numeric sentinel is used.
- `held` counts held episodes; `ends` counts their ends (`last.end` ∈ `spared`, `delayed`, `line`, `ate`).
- The `netsync.stepout` block is unchanged.

**Log lines.** All are behaviour lines with `NetSyncSwap.Stamp()`, printed unstamped under `stamps off`. battlewire's
`swap_line_class` (:12579) gains the `[NetSync] arrival guard: ` prefix. s158's OUT and IN lines are unchanged (and unstamped,
`NetSyncStepOut.cs:606`), so the duo's `is_dwell_out` (`coop_field_swap_timing_duo.py:544`) keeps matching.
- At most once per landing, and only for an armed guard whose `lead_ms` < 1040:
  - `[NetSync] arrival guard: field F -- the host landed N ms before me (intent nonce K); a wordless control-off counts toward the dwell from its landing + 1040 ms`
  - the late form: `... -- the host's landing reached me N ms after mine (intent nonce K); a wordless control-off counts toward the dwell from 1040 ms past its start`
- `[NetSync] arrival guard: held the dwell on field F -- the base is B ms, its guarded dwell D ms (s158 would step out here)`, once
  per episode, by `ArriveHeldRule`.
- At a held episode's end (`ArriveEndRule`), one of:
  - `[NetSync] arrival guard: field F -- spared a dwell OUT (base B ms, guarded dwell D ms)`
  - `... -- held the dwell OUT S ms (it stepped out at base B ms)`
  - `... -- a line started the step-out at base B ms (guarded dwell D ms)`
  - `... -- s162's ATE landing started the step-out at base B ms (guarded dwell D ms)`
- `[NetSync] arrival guard: spent on field F -- my control is back | a step-out started | the field changed | the session reset`,
  only for a guard that printed the anchor line. Battle returns, save loads and world rejoins stay quiet.
- `[NetSync] harness: swap arrive OLD -- CALIBRATION: s158's dwell from the base start at every landing, no arrival guard (released with the harness)` and `[NetSync] harness: swap arrive ACT`.
- `[NetSync] harness: swap arrivebench L -- my next landing gets a bench host that landed L ms before me (the selftest role; released with the harness)`
  - then, when R is written: `[NetSync] arrival guard: bench -- the host's landing on field F written L ms before mine (section 4 through the real codec)`
- The fault, sticky and once per site: `[NetSync] field swap fault (ARRIVE at <site>): <msg> -- s158's dwell from the base start from here`.

## SelfTest

The guard's rules get their own rule set, following D+E's shape (`NetSyncFollowFade.cs:606` `Rules`, `SelfTestRows` :981,
`SelfTestMutants` :1004) but inside `NetSyncSwap.cs` (no new file): a private nested `ArriveRules` class whose seams are named
`Seen`, `Edge`, `Arm`, `Anchor`, `Holds`, `DwellAge`, `Held`, `Spend`, `End` and `Count` (never `Age`: `NetSyncSwap.Rules.Age`
is PIN's `PinAgeRule`, :2931). `RowsArrive(ArriveRules, fails)` and `MutantsArrive(out survived)` are called from
`NetSyncSwap.SelfTest` (:4277) beside D+E's calls (:4287, :4309). In the table, K = 1040, D = 1500, S = 500, and n is a landing
number (5 in every Anchor row).

- `DwellAge(holds, base, sinceHost, sinceMine)` is the seam. Its shipped body ignores `sinceMine` (the seam precedent at
  :2895-2907), so the two rejected readings can be mutants.
- The composition rows call the **real** `NetSyncStepOut.StartRule`.

| Group | Rows (input → expected) | n |
|---|---|---|
| Seen | `landed` v4 0x01 → T; `pre` v4 0x00 → F; `s163` 3 bytes → F and `IntentLandedOf` → T; `null` → F; `other_bit` 0x02 → F; `bits` 0x03 → T | 6 |
| Edge | `first` (−1,−1,7,30611,T) T; `same` (7,30611,7,30611,T) F; `next_nonce` (7,30611,8,30611,T) T; `chain` (7,353,7,30611,T) T; `pre` (−1,−1,7,30611,F) F; `no_section` (7,30611,−1,30611,T) F; `field0` (7,30611,7,0,T) F | 7 |
| Arm | `act` (T,F,F) On; `lever` (T,T,F) Lever; `role` (F,F,F) Role; `world` (T,F,T) World; `lever_first` (T,T,T) Lever | 5 |
| Anchor | `in_time` (T,30611,4,600,30611,5) T; `late` (T,30611,5,−400,30611,5) T; `stale` (T,30611,3,600,30611,5) F; `other_field` (T,353,4,600,30611,5) F; `none` (F,30611,4,600,30611,5) F; `old` (T,30611,4,10000,30611,5) F; `old_edge` (T,30611,4,9999,30611,5) T | 7 |
| Holds | `all` (T,T,30611,30611) T; `unarmed` (F,T,30611,30611) F; `unanchored` (T,F,30611,30611) F; `arm_field` (T,T,353,30611) F | 4 |
| DwellAge | `identity` (F,1600,0,0) 1600; `arrive` (T,1750,2300,1800) **1260**; `arrive_late` (T,1750,1720,1800) **710** (the cap); `scene_out` (T,1990,2540,2040) 1500; `scene_edge` (T,1989,2539,2039) 1499; `inert` (T,1500,2700,1550) 1500; `never_earlier` (T,800,5000,4900) 800; `cap_out` (T,2540,2190,2590) 1500; `cap_edge` (T,2539,2189,2589) 1499; `future` (T,1600,−50000,1650) 560; `own_pass` (T,1750,2000,1800) 960 (an own pass read in time; the late default is `arrive_late`); `fade_old` (T,1500,2590,1550) 1500; `wrap` (T,1600,Int32.MinValue,1650) **1600** (the delta wraps positive: inert) | 13 |
| Start | `arrive_act` Start(F, DwellAge(T,1750,2300,1800), F) = None; `arrive_old` Start(F, DwellAge(F,1750,2300,1800), F) = Dwell; `line` Start(T, DwellAge(T,0,0,0), F) = Line; `ate` Start(F, DwellAge(T,0,0,0), T) = Ate | 4 |
| Held | `first` (F,1500,1000) T; `once` (T,1600,1100) F; `under` (F,1499,1000) F; `not_held` (F,1500,1500) F | 4 |
| Spend | `none` (T,30611,30611,F,−1,F) None; `debounce` (T,30611,30611,T,499,F) None; `control` (T,30611,30611,T,500,F) Control; `left` (T,30611,353,F,−1,F) Field; `out` (T,30611,30611,F,−1,T) Out; `unarmed` (F,30611,353,T,600,T) None; `order` (T,30611,353,T,600,T) Field | 7 |
| End | `flicker` (T,2,F,F,None) None; `stale` (T,3,F,F,None) Spared; `rebase` (T,1,T,F,None) Spared; `out_dwell` (T,1,F,T,Dwell) Delayed; `out_line` (T,1,F,T,Line) Line; `out_ate` (T,1,F,T,Ate) Ate; `out_over_rebase` (T,1,T,T,Dwell) Delayed; `unheld` (F,3,T,T,Dwell) None | 8 |
| Count | `landing_arm` (Landing,T,T,600,F,F) Arm; `landing_far` (Landing,T,T,1040,F,F) None; `landing_unanchored` (Landing,T,F,LeadNone,F,F) None; `late_first` (LateEdge,T,T,−400,F,F) Arm\|LateArm; `late_again` (LateEdge,T,T,−300,T,T) None; `late_after_arm` (LateEdge,T,T,−300,T,F) LateArm; `spend_unanchored` (Spend,T,F,LeadNone,F,F) Unanchored; `spend_anchored` (Spend,T,T,600,T,F) None; `unarmed` (Spend,F,F,LeadNone,F,F) None | 9 |
| Live | `live.arrive_codec`: `IntentSectionBody(30611, 7, true)` and `(…, false)`, and an s163-shaped 3-byte section, each through `AppendSection` / `TryReadSection` → `HostLandSeenOf` and `ArriveHostEdgeRule` | 1 |

**75 rows, 37 mutants.** Each mutant and the row that kills it:

| Mutant | Killed by | Mutant | Killed by |
|---|---|---|---|
| `arrive_s163_body_lands` | seen.s163 | `arrive_add_lead_always` (origin B + K) | dwellage.inert, dwellage.fade_old |
| `arrive_any_bit` | seen.other_bit | `arrive_max_not_min` | dwellage.never_earlier |
| `arrive_every_landed_frame` | edge.same | `arrive_no_cap` | dwellage.arrive_late, dwellage.cap_out, dwellage.future |
| `arrive_pre_landing_records` | edge.pre | `arrive_literal_lag` (origin 2G − Hs) | dwellage.own_pass, dwellage.fade_old |
| `arrive_lever_blind` | arm.lever | `arrive_from_my_landing` (origin G + K) | dwellage.fade_old, dwellage.arrive |
| `arrive_on_host` | arm.role | `arrive_age_long_math` (Int64, no wrap) | dwellage.wrap |
| `arrive_from_world` | arm.world | `arrive_held_every_tick` | held.once |
| `arrive_stale_record_anchors` (no landing test) | anchor.stale | `arrive_spend_no_debounce` | spend.debounce |
| `arrive_anchor_field_blind` | anchor.other_field | `arrive_never_spent` | spend.control |
| `arrive_late_never_anchors` | anchor.late | `arrive_spend_field_blind` | spend.left |
| `arrive_anchor_no_window` | anchor.old | `arrive_out_blind` | spend.out |
| `arrive_unarmed_holds` | holds.unarmed | `arrive_end_line_as_delayed` | end.out_line |
| `arrive_unanchored_holds` | holds.unanchored | `arrive_end_ate_unclassified` | end.out_ate |
| `arrive_arm_field_blind` | holds.arm_field | `arrive_end_spared_on_flicker` (threshold ≥ 2) | end.flicker |
| `arrive_no_lead` (sinceHost unshifted) | dwellage.arrive | `arrive_end_rebase_blind` | end.rebase |
| `arrive_count_arm_far` (no lead < K) | count.landing_far | `arrive_end_rebase_first` | end.out_over_rebase |
| `arrive_count_late_every_edge` | count.late_again | `arrive_end_unheld_classified` | end.unheld |
| `arrive_count_late_never` | count.late_first, count.late_after_arm | `arrive_count_unanchored_with_record` | count.spend_anchored |
| `arrive_count_unarmed` | count.unarmed | | |

- **The proof line** gains 75 rows and 37 mutants (as built: the base is 426 / 146, not the 425 rows this spec counted, so the
  line reads 501 / 183; fakegame pins both halves, `FAKE_SWAP_SELFTEST_ROWS_UNGUARDED` 426 and `FAKE_SWAP_ARRIVE_ROWS` 75,
  `fakegame.py:1088-1093`) and the tail `, arrival lead 1040 ms`.
- **s158's line does not move.**
- **No `arrive_holds_line` mutant.** The line and `ate` precedence is structural: StartRule is unchanged and the hunk passes `line`
  and `landing` straight through. A kit source pin on the exact :570 line carries it, as s162's pin did
  (`test_harness_netsync.py:27583`).
- **Twins.** Every battlewire twin of a guard rule that takes an Int32 delta (`swap_arrive_dwell_age`, `_anchor`, `_held`) wraps
  through `_i32` (`battlewire.py:1040`, P9), so `dwellage.wrap` reads 1600 there as in C#.

## Benches

### Solo (`coop_field_swap_timing.py`): new leg G, engine-only

- **Setup.** `LEGS` becomes `"KABCPLFG"` (:170). ARRIVE_ID 30611 must be registered on the solo root; otherwise the leg reads "not
  reached" with the deploy command, in CAL's shape.
- **Engine-only.** The stand-in models no step-out episode (`fakegame.py:6623-6624`), no landing and no record. The docstring's
  stand-in paragraph (:95-97) becomes "models K, A and B only: on an engine, a C, P, L, F or G leg's sentinel keys after an acked op
  are red (P8)", and the kit test stays at `COOP_LEGS=KAB`.
- **P8 extended to G.** On an engine, a G row whose `arrivebench` was acked but which never read a FRESH bench record
  (`arrive.host.bench` for 30611 with an `arrive.host.nonce` other than the row's start: the previous row's record stands, so presence
  alone could never fail; with the start unread, presence suffices), or whose `arrive.field` never read 30611, or (G-HOLD, G-DELAY,
  G-LATE, with `levers.arrive` act at the landing) whose `episode.on` never read true, is red: "the engine never ran the guard".
- **Each row, starting from HOME:**
  0. Wait up to 3 s for HOME's own guard to spend (`arrive.armed` false), then read the row's counter base. HOME's landing arms an
     unanchored guard on the selftest role too, and above about 44 fps its spend could land inside the row's deltas. A guard that never
     spends leaves the row UNREACHED; the wait reads no `arrive.field`, so a faulted guard still reads P8 red (as built).
  1. `hostscene 1`. It survives the load: `DebugHostEventFlag` is cleared only at the selftest disarm (`NetSyncClient.cs:10002`).
  2. `swap arrivebench L`, if the row has a lead.
  3. `warp(ARRIVE_ID, entrance=0)`.
  4. Sample until my control has been back for 1 s, then `hostscene 0`.
  5. Return to HOME.
- **No `swap clear` between rows, on purpose.** HOME's landing gives every row a fresh landing number, so a previous row's bench
  record for 30611 is stale at the next ARRIVE landing. G-OFF runs after G-INERT so it is the live proof of the stale rule.
- **Judging.** Only OUT lines and samples naming ARRIVE_ID count. My control returns at about G + 2130 + O (ARRIVE at 64). Timing is
  judged from state, not from s158's OUT line (it is unstamped, `NetSyncStepOut.cs:606`, and the solo warps never join a swap
  record, so `swap.last.land_t` does not move: `JoinRule` EdgeLand :441-445, OnFieldLoad's :2005 return):
  - the OUT instant = `clock.now_ms − stepout.age_ms` at the first sample with `stepout.active` true and `why` `dwell`
    (`coop_step_out.py:233-245`'s pattern);
  - the landing = `swap.arrive.land_t`, the guard's own swap-clock landing;
  - B − G = (`clock.now_ms` − `arrive.land_t`) − `stepout.base.age_ms` at the episode's own base (the last episode sample with a
    base; the first base sample only when no episode sample has one; as built), ± one frame and TickCount's 16 ms;
  - (the guard's own `held the dwell OUT` end line is stamped, but lags the OUT by up to 2 frames: reported only).

| Row | L | Green | Under `arrive` |
|---|---|---|---|
| **G-HOLD** | 0 | Reach: raw base peak ≥ 1500, or a dwell OUT (as built: the published base age reads -1 once a step-out is active). No dwell OUT on 30611; `ends.spared` +1; `last.end` spared; dwell peak ≈ A − K ≈ 1090-1270 (< 1500); `spends.control` +1 within [-1 frame, S + 0.3 s] of control back | red: OUT at base ≈ 1500 |
| **G-DELAY** | 600 | One OUT by dwell whose instant − `arrive.land_t` is in [1880, 2090] (Hs + K + D = G + 1940); `ends.delayed` +1; `last.shift_ms` = 440 − (B − G) ± one frame + 16 ms (as built: B - G carries TickCount's resolution; the expected value is the full rule min(K, max(0, K - ((B - G) + 600)))) | red: OUT at ≈ land + 1550 |
| **G-LATE** | −400 | `late` true and `late_arms` +1 (G-DELAY's record is stale: seen before HOME's landing); `episode.shift_ms` = **1040 exactly** (the cap binds; uncapped would read 1390); no OUT before my control returns | red: OUT at ≈ land + 1550 |
| **G-INERT** | 1500 | OUT instant − `arrive.land_t` in [1500, 1700]; `shift_ms` 0; `held` +0 | green (a control) |
| **G-OFF** | none | `arrive.host.field` = 30611 and `host.bench` true (G-INERT's record still stands) **and** `lead_ms` null: the stale record does not anchor; OUT by dwell at base 1500 (s158 exactly: OUT instant − B in [1500 - 16, 1500 + one frame + 16], as built: the OUT instant and B mix the QPC swap clock with TickCount ages, so a true 1500 can read 1484); `unanchored` +1 at the OUT's spend | green (a control) |

- **K-legs.** K-REFUSE, K-LEVER and K-RELEASE gain:
  - the `arrive` and `arrivebench` acks and the `levers.arrive` / `arrive.bench.armed` read-back;
  - the usage refusal for `arrivebench 30602`, which is out of range;
  - the release.
- **The stand-in** acks both ops (the harness half: role, arity, bounds, the lever and the bench's arm), publishes `levers.arrive`,
  `arrive.arrival_lead_ms` and `arrive.bench`, and releases them; every other `arrive` key stays at its sentinel (NOT MODELLED: a
  landing, a record, an episode). `SWAP_STANDIN_UNMODELLED` (`fakegame.py:1048`) does **not** gain `arrivebench`: that would refuse
  it and break K-LEVER on the stand-in.
- **The solo word `arrive`** sends `swap arrive old` before G-HOLD, G-DELAY and G-LATE, and reds exactly those three.
- **INFER:** the harness `warp` does not refuse under `hostscene 1`. The first run settles it, since a refusal reads "not reached".

### Duo (`coop_field_swap_timing_duo.py`)

- **ARRIVE is retuned to `entry_settle = 64`** (`studies/movement/bench/lockt2-arrive.field.toml`, and `ARRIVE_SETTLE_TICKS`), a
  data edit and a redeploy with `--id 30611` (already registered: no relaunch). § Predicted numbers has the window. The retune rule
  is pre-registered: if CAL2's measured O (overlap + L − 1667 ms) and its median δ7 would put 64's E outside
  [D + L + bind, D + K + δx], `entry_settle` becomes round((2320 − O − δ7) / 33.3), the window's centre, before ARRIVE is judged
  again. It is read from CAL2, a watch, never from ARRIVE's own outcome. As built it is a reported string in DA-ARRIVE's detail,
  never judged, and VOID under an unfit clock. 30611 was redeployed at 64 after the build (its installed files postdate the retune).
- **An unregistered ARRIVE_ID** (as built) reads DA-ARRIVE "not reached" with the deploy command and records it VOID, a setup miss:
  under the `arrive` word the calibration reads VOID, never the word's predicted red.
- **DA-ARRIVE becomes the guard's calibration** (`judge_da_arrive`, :900).
  - **Reach (a kit fix).** `arrive_reached` (:890-892) becomes overlap ≥ D + 100 **and** (raw base peak ≥ D **or** a dwell OUT).
    `HarnessBaseAgeMs` reads −1 while a step-out is active (`NetSyncStepOut.cs:1049`), so on an OUT run the published peak sits
    within a frame of 1500 on either side. Today the `arrive` word's predicted red would read "not reached" on frame phase. At act,
    raw base peak ≥ D means round 1 would have stepped out on this very run: the run is on the red side of the window.
  - **Green at act:** no dwell OUT, `stepout.active` never true, and the green is attributable to the guard. That means
    `swap.arrive.last.field` = 30611 with `last.end` spared (`ends.spared` Δ ≥ 1), and `levers.arrive` null.
  - **Named reds** (each read from the guest alone):
    - "the guard never anchored: no landed frame seen", when the ARRIVE landing's `lead_ms` is null;
    - "guard defect: shift S ms, the rule gives R ms", when the episode's `shift_ms` differs by more than one frame + 16 ms from
      min(K, max(0, K − (B − Hs))), with B − Hs = (B − G) + `lead_ms` and B - G read at the episode's own base, as the solo's
      leg G reads it (as built; the first base sample in the window could belong to a base that re-armed before the episode);
    - "margin miss: the guard shifted S ms as its rule says, and this arrival's control-off still ran past Hs + K + D (s163's own
      instant) -- retune ARRIVE's entry_settle, not a guard defect", for a dwell OUT with the guard anchored and its shift right.
      A margin miss is red (the gate is not passed) but names the field, not the guard.
  - **Reported:**
    - the guarded dwell peak, `shift_ms`, `lead_ms` and its sign, the raw base peak, the overlap;
    - A (the host's first control-true after its landing − its `last.land_t`, one game), δx (the guest's `arrive.host.seen_t` −
      the host's `last.land_t`) and δ7 (the guest's base end − the host's control-true), both cross-game;
    - "margin thin" when a green run's guarded peak exceeds 1450 ms (< 50 ms to D);
    - the cross-check of ARRIVE's guarded peak against ARRIVE-OLD's raw base peak, **reported only**: they are two independent δ7
      draws, each spanning about 200 ms.
  - **An unfit clock** VOIDs only the overlap clause and the cross-game reports; DA-ARRIVE judges its in-game clauses (reach by the
    raw base peak or a dwell OUT, the green, the named reds). It leaves `CROSS_GAME` (:188) and joins DC-B(a), DF-FAST and DA-LINES,
    which lose a clause instead.
  - **Controls** (ARRIVE on `fade old`, CAL0) stay green, with `shift_ms` ≤ about 100 reported.
  - **Watches.** CAL2 and DESK stay watches, reported apart and never judged (as built, the duo's fix round): their dressed dwell
    OUTs are listed in the detail but never change the verdict, so a watch red cannot break the `arrive` word's exactness. The
    first duo run's five DESK watch OUTs were 352's lawful 7.9 s wordless scene, read through a 351 window that never ended; the
    351 arrival's window now ends at the 352 landing. On DESK an OUT by line is lawful; when `shift_ms` > 0 at it, it is reported as
    a guarded line start ("never delays a line", on real bytes).
- **`BASELINE_RED = ()`** (:195).
- **The new word `arrive`.** The guest sends `swap arrive old` (read back) before the ARRIVE act run only, and `act` after it.
  - Red rows: **DA-ARRIVE**.
  - Marker: a dwell OUT on 30611 with `levers.arrive` old and `arrive.armed` false at that landing.
  - `WORD_LEGS["arrive"] = ("CAL",)` (:270-272): a word without legs is refused at load.
- **The `life` scope (a correction).**
  - Today `life` sets the host's `swap life old` before the whole CAL loop, including both ARRIVE runs (:1693-1699, released at
    :1726).
  - Under `life old` no landed frame is sent, so the guard cannot anchor and DA-ARRIVE would go red. That would break the word's
    exactness.
  - Fix: the host sends `swap life act` before the ARRIVE runs and restores `old` after them. `WORDS["life"]` (:265) and its legend
    (:64) say so.
- **The new row DA-GUARD** (judged; probabilistic, one game; in `PROBABILISTIC`, :190).
  - Scope: each act intent landing in CAL2, CAL3, DESK and REST whose host transition sent a landed frame, i.e. the host's
    `intent.landed_frames` Δ ≥ 1. Any other landing is UNREACHED, never red.
  - Green: the guest's `arrive.lead_ms` is non-null for that landing before its control returns.
  - **Floor:** a plain run needs at least one reached landing across CAL2, CAL3, DESK and REST, else red "not reached: no landing
    sent a landed frame" (DA-LANE's floor, P8). Under the `life` word, its declared unreach, the row reads UNREACHED/VOID instead.
  - Reported: `lead_ms` per landing, and `host.seen_t` − the host's `last.land_t`. The latter is cross-game and VOID under an unfit
    clock.
  - It checks the anchor that the ARRIVE green depends on, across ordinary landings.
- **LVD-ROLE** gains two checks: `swap arrive old` sent to the host gets the guest-side refusal, and `swap arrivebench 0` sent to the
  client gets the selftest refusal.
- **Predictions:**
  - ARRIVE at act: green, guarded dwell peak about 1.0-1.475 s (typical 1.235 s), raw base peak about 1.58-2.08 s.
  - Under `arrive`: DA-ARRIVE red only.
  - ARRIVE-OLD and CAL0: green.
  - DA-GUARD: green on every reached landing, at least one reached.

### Kit and hunks

- **`tools/harness/battlewire.py`:**
  - `ARRIVAL_LEAD_MS`, `ARRIVE_LEAD_NONE`, and the arm, spend, end and count name tuples;
  - the twins `swap_host_land_seen_of`, `swap_arrive_edge`, `_arm`, `_anchor`, `_holds`, `_dwell_age`, `_held`, `_spend`, `_end`,
    `_count` (the Int32-delta ones through `_i32`);
  - the line builders;
  - `SWAP_USAGE` (:13472) and `swap_lever_refusal` (:13571) with the lead range;
  - `_SWAP_PROOF_CONSTANTS` (:13684).
  - The kit has **no** step-out rule twins (rev 1 cited `fakegame.py:852-894`, which holds the stepout lever and proof constants);
    nothing step-out changes there.
- **`tools/harness/fakegame.py`:** the `arrive` block at its sentinels, `levers.arrive`, both ops acked (harness half), and
  `FAKE_SWAP_SELFTEST_ROWS` / `FAKE_SWAP_MUTANTS` 501 / 183 (as built; see SelfTest). `SWAP_STANDIN_UNMODELLED` unchanged.
- **`tools/harness/session.py`** (as built; this list left it out): `arrive` and `arrivebench` in `NETSYNC_SWAP_OPS` and the
  role sets, `NETSYNC_SWAP_WORDS["arrive"]`, `NETSYNC_SWAP_ARRIVEBENCH_RANGE = (-1000, 5000)` and the new usage literal; without
  them the driver refuses both ops itself, with the old usage line, before anything reaches the stand-in or the engine.
- **`ff9mapkit/tests/test_harness_netsync.py`:**
  - The :27583 pin becomes the s164 line.
  - New source pins:
    - in `OnFieldLoad`, `ArriveLanding(` precedes `Int32 via = LandViaRule(` and
      `if (!joined && (via == ViaSame || via == ViaOther))`;
    - in `NoteHostFrame`, `ArriveHostFrame(` follows `PinHostFrame(state, field, nonce, IntentLandedOf(body), myField);` and
      precedes `if (SeenRule(true, nonce, _seenNonce))`;
    - `GuestTick`'s first statement; the `ResetSession` and `ForgetHostNonce` clears; the release.
  - Twin/table parity at 75 rows and 37 mutants.
  - **The sentinel parity test** (`_design_swap_block`, :30106-30111; asserts :30165-30176) reads `SWAP-TIMING-S164.md`'s fence: the
    fence, `FG.NETSYNC_SWAP_SENTINELS` and the :4107 catch literal move together in one commit; the `NETSYNC_SWAP_KEYS` assertion
    (:30166-30167) ends `…, "selftest", "arrive")`.
  - `_SW_ARG_FORMS` (:30120-30131) gains `("arrive","act")`, `("arrive","old")`, `("arrive","x")`, `("arrive",)`,
    `("arrive","old","1")`, `("arrivebench","-1001")`, `("arrivebench","-1000")`, `("arrivebench","5000")`,
    `("arrivebench","5001")`, `("arrivebench","x")`, `("arrivebench",)` and `("arrivebench","0","1")`.
- **`ff9mapkit/tests/test_coop_field_swap_timing_bench.py`:**
  - judges for leg G (state-timed), the P8 extension, the attributable green, the named reds, the reach fix and the `arrive` word;
  - the `life` scope, an empty `BASELINE_RED`, DA-ARRIVE out of `CROSS_GAME`, `WORD_LEGS["arrive"]`, DA-GUARD with its floor;
  - ARRIVE's `entry_settle` 64 (the :1835 docstring and `ARRIVE_SETTLE_TICKS`, :1944).
- **Engine hunks, about 20, no new file:**
  - `NetSyncStepOut.cs`: 2 (the line and the header comment).
  - `NetSyncSwap.cs`: about 14 (the guard section with `ArriveRules`, five call sites, the levers, the release,
    `ItemNames` / `FaultsBy`, the proof).
  - `HarnessAgent.cs`: 4 (`levers`, the `arrive` block, the :4107 sentinel with both keys, the ProtocolVersion paragraph).
  - `NetSyncClient.cs`: 0.
- **Regression gates:**
  - s158's proof line unchanged;
  - `coop_step_out` green (the selftest never writes R, so the guard is inert);
  - `coop_ate_relay` S-LAND and `coop_ate_relay_duo` D10-D12 unchanged (`ate` decides first);
  - `coop_speed_mirror`;
  - `coop_world_wait` (s144) and `coop_world_battle` (s145): green, `arrive.world` Δ ≥ 1 per world rejoin, `arms` +0 on them,
    `lead_ms` reported (the INFER on the world gap). As built, the clause folds into every world-rejoin row (no new row id) and
    also requires `arrive.field` = the rejoin field; the Build log has its not-judged cases;
  - s164's existing regression set.
  - INFER: no regression row changes. The ATE noland marker (`coop_ate_relay.py:352`) accepts a line or a dwell OUT with no
    timing.

## Not done

- **No retune** of `DwellMs` or `StepInMs`, and no change to any s158, s159 or s162 rule.
- **No host code, no wire byte, no section, no protocol bump.**
- **The late-read fix is deferred.** It would be a "ms since my landing" byte in s164's own section-4 body (inside v14, S3's
  precedent), built only if two-PC logs show the own-pass band between 2.54 s and L + 2.54 s matters. The transport's arrival stamp
  cannot do it, because it holds only the latest payload.
- **No provisional hold before an anchor.** An unanchored landing (a battle return, a save load, an s163 host, `life old`) keeps
  round 1's rule rather than delaying arrivals with no paired swap.
- **No guard on world rejoins** (R3's exclusion, § Worst case). Arming there is a later round's one-term change (`arrive_from_world`
  shows the difference), triggered by a short world-rejoin `lead_ms`.
- **No time lapse of R and no episode latch** (§ Mechanism). Freshness lives at the anchor. The lever is read at the landing.
- **No bench host-control schedule** (an `arrivebench … <hold>`). It would cost a hunk in `ServiceStepOut`'s s158 bench branch. The
  duo's ARRIVE is the real replica; the solo rows prove the rule through the live landing and step-out.
- **No 3x scaling.** K, D and the base are all wall-clock TickCount, as in s158.
- **No census** of wordless arrival lengths (decision 8's alternative). `ends.spared`, `ends.delayed` and `held` measure it in play.
- **No change to the speed mirror's undwelled start** (risk 14's second half, G1).
- **Doc follow-ups for `SWAP-TIMING-S164.md` rev 4** (all applied in its rev 4, under What changed from rev 3; the fence went with the
  kit, and the `HarnessAgent.cs` cite is :5039 once the guard's own hunks are in):
  - risk 14's band (1.5 + L to 2.54 s; the own-pass late-read band 2.54 s to L + 2.54 s; the unanchored and world residuals);
  - decision 8 pointing here, with this addendum's reading of "the host's arrival lead";
  - the R2, V5 and DA-ARRIVE rows and the calibration table (`arrive`, the `life` scope, DA-GUARD, DA-ARRIVE's named reds, its
    clause-wise unfit clock);
  - the CAL row: ARRIVE at `entry_settle = 64`, with the retune rule;
  - `BASELINE_RED` and the gates (the two world benches);
  - `ArrivalLeadMs` in risk 7's seed list;
  - the files table;
  - **the `netsync.swap` fence** (:1009-1047): `levers` gains `"arrive":null` after `hostctl_off`, and `swap` gains `"arrive"` after
    `selftest` at the sentinels in § Lever (the kit parity test reads this fence);
  - two stale cites: `NetSyncSocket.cs:800` is now :923, and `HarnessAgent.cs:4996` (base.age_ms) is now :5029.

## Review log

**2026-10-30, design.** Two independent designs were judged against the source: A (minimal) and B (risk-first). This spec takes A's
skeleton and grafts B's safety and bench ideas.

| Decision | From | Why |
|---|---|---|
| Origin Hs + K, not decision 8's literal G + L | A and B (they agreed) | Lag-invariant: it reproduces s163's instant at any gap. The literal form is right only near 0.5 s. Now an owner question (round 1, finding 7) |
| One behaviour hunk at `NetSyncStepOut.cs:570`, the guard's state and rules in `NetSyncSwap.cs`, 0 `NetSyncClient` hunks | A | B's form needed 3 StepOut hunks (`fresh`, `ArriveTick`, `ArriveNoteOut`) and a `ServiceStepOut` bench hunk |
| **The cap** `min(Hs + K, B + K)` | B (F1) | A's bound ("B leads Hs by at most a write tick") holds only while the position lane follows the landing hook (`NetSyncClient.cs:2318-2329`). It fails for a stale, future or garbage anchor. One `Math.Max` makes the 1040 ms bound unconditional |
| The lever read at the landing, not live | B (its latch semantics) | It removes the only snapback A's live lever term allowed, with no episode latch |
| No episode latch, no PENDING window, no `past` arm verdict | A (with B's cap) | Every spend coincides with a failed base. The formula is inert past Hs + K. With the cap, a late anchor needs no window |
| No time lapse of the record | B | A's lapse was verdict-neutral but cost 2 rules, 4 rows and 3 mutants; the formula limits itself. Round 1 keeps it, but adds freshness at the anchor (finding 2/8) |
| Spent by any step-out (`SpendOut`) | B | Read from `NetSyncStepOut.Active` in `ArriveTick`, so no hunk |
| The `held` line and the `spared` / `delayed` / `line` ends | A's ends, B's `ArriveHeldRule` | The gates count them, so the edge is tabled. Round 1 tables the ends too and adds `ate` (finding 9) |
| The reach fix (`base_peak ≥ D or an OUT`) | B | The `arrive` word's red would read "not reached" on frame phase |
| The `life` scope correction | A | `life old` covers both ARRIVE runs (:1693-1699) and would starve the anchor |
| DA-GUARD reach-gated on `landed_frames` | B's DA-GUARD, made one-game and reach-gated | It keeps the `life` word exact |
| G-LATE (the cap) and G-OFF (unanchored) | B | They are the live-path proof of the cap and of the round-1 fallback |
| G-HOLD at L = 0 with `hostscene` held | A | No bench host-off schedule hunk is needed |
| B's DA-GLINE folded into DA-ARRIVE's DESK report | B | The line precedence is structural and pinned; a separate judged row would add little |

**2026-10-30, review round 1 (15 findings; 2+8 and 4+10 report one defect each).** All accepted; finding 1 is accepted with a
correction to its window arithmetic.

| # | Sev | Finding | Resolution |
|---|---|---|---|
| 8 (+2) | high | A stale host-landing record anchors later landings: G-OFF reds by construction, G-LATE's `late_arms` is undefined, `unanchored` reads low in play | **Fixed.** New pure rule `ArriveAnchorRule`: R must name fld and have been seen in this landing's interval (`seenLanding == landing − 1` within `IntentLoadCapMs`, or `== landing`, the late form). The guard copies Hs, so R's replacement no longer matters; `ArriveHoldsRule` takes `anchored`. § The lead defines the late replacement (`late`, `late_arms` once). The bench with lead ≥ 0 writes R inside `ArriveLanding` before the anchor reads it, with `seenLanding = landing − 1`. Rows anchor.* (7), mutants `arrive_stale_record_anchors`, `_anchor_field_blind`, `_late_never_anchors`, `_anchor_no_window`; `arrive_host_field_blind` becomes `arrive_unanchored_holds`. Leg G keeps no `swap clear` on purpose: G-OFF after G-INERT is the live proof of the stale rule (finding 2's alternative of clearing would hide it) |
| 1 | medium | ARRIVE's green has ~70 ms worst-case margin and overhead past the nominal 2267 ms uses it up | **Accepted, corrected.** The prediction is now peak = A + δ7 − δx − K. The finding's two bounds take δ7's extremes on opposite sides; δ7 is one draw per run and moves both, so the window is in E = A + δ7: [D + L + bind, D + K + δx], ~500 ms wide. With O 0-180 ms (CAL2), 68 misses at O + δ7 − δx ≥ 273 ms: a real flake, so ARRIVE is retuned to 64 (no miss on either side inside the stated O and δ7 bounds; the finding's 64-66 holds, and 64 balances the corners at bind up to 100 ms), with a pre-registered retune rule read from CAL2. A, δx and δ7 are reported per run; the ARRIVE-OLD cross-check is reported only; a dwell OUT with a correct shift is the named red "margin miss", told apart from "guard defect"; a green above 1450 ms is "margin thin". rev 1's "load straddles it" INFER is withdrawn |
| 3 | medium | World-to-field arrivals carry section 4 with the landed bit, so the guard anchors on world rejoins | **Fixed by exclusion.** Confirmed: `EventEngine.DoEventCode.cs:1040`, `NetSyncClient.cs:2413-2415, 7135-7153`. `ArriveArmRule` takes `fromWorld` (`LandingFromWorld`, the read PIN's R3 takes) and returns `ArmWorld`; counted in `world`; row arm.world, mutant `arrive_from_world`. Reason: s164 left the world rejoin's gap alone (s144's branch, R3), so s158's law there is s163's. Worst case and Not done corrected; `coop_world_wait` and `coop_world_battle` join the gates, reporting `lead_ms` (the INFER) |
| 10 (+4) | medium | OnFieldLoad's :2005 early return skips an `ArriveLanding` placed at its end (every solo warp); both new hooks sit inside item A's try | **Fixed.** `ArriveLanding` is OnFieldLoad's first statement, before `LandViaRule`, `Join`, :2005 and A's try. `ArriveHostFrame` follows `PinHostFrame` with its own try, so A's seen edge always runs. Every guard entry point has its own try with item ARRIVE (sticky, logged once). `ArriveLanding` resets `backArmed`/`backSince`. Kit source pins for both placements |
| 9 | medium | spared / delayed / line, lead / late, arms and unanchored have no pure rule, rows or mutants; no `ate` end; the freshness test is order-sensitive | **Fixed.** `ArriveEndRule` (8 rows, 6 mutants) with an `ate` end, `ArriveCountRule` (9 rows, 5 mutants), § The lead for `leadMs`/`late`. One episode = one base: a re-armed base ends a held episode as spared inside `ArriveDwellAge` in both orders (s158's own dwell restarted there too, so `spared` counts exactly the OUTs s158 would have made); staleness classifies at framesSinceDwell 3 in both orders. Twins added; tallies 75 / 37 |
| 11 | medium | G-DELAY's / G-INERT's judges read an OUT stamp that does not exist and a `land_t` that does not move on the solo | **Fixed.** Confirmed: the OUT line is unstamped (`NetSyncStepOut.cs:606`) and the solo never joins a record (:441-445, :2005). Leg G is timed from state: OUT instant = `now_ms − stepout.age_ms` at the first active `dwell` sample (`coop_step_out.py:233-245`'s pattern), against `swap.arrive.land_t`; B − G from the first base sample |
| 12 | medium | Leg G must be engine-only and P8 must cover it; wrong twin cite; the solo bench's reach unstated | **Fixed.** Leg G is engine-only; the stand-in acks both ops' harness half and does not add `arrivebench` to `SWAP_STANDIN_UNMODELLED`; P8 extended to `arrive.host.bench`, `arrive.field` and `episode.on`; the kit test stays at `COOP_LEGS=KAB`. `arrivebench` calls `ArriveRecordEdge`, the live writer's body, with the client gate at the `NoteHostFrame` call; the real call site and the live Hs latency are proven only by the duo. The `fakegame.py:852-894` cite is corrected |
| 13 | medium | The kit's sentinel parity test reads SWAP-TIMING's fence; the follow-ups miss it and the catch literal's `levers` key | **Fixed.** Rev-4 list gains the fence; the sentinel form is written out; the :4107 hunk carries `levers.arrive` and `arrive`; `NETSYNC_SWAP_KEYS` assertion updated; `_SW_ARG_FORMS` gains the twelve `arrive`/`arrivebench` forms |
| 5 | low | The 2.54 s threshold for small L assumes Hs is read in time; at an own pass it is late by construction | **Fixed.** The Problem table splits in-time and late rows (late: D + L + K, 2.64 / 2.84 s at L 0.1 / 0.3, the own-pass default); the own-pass row of § Predicted numbers now uses the cap (710); the band 2.54 s to L + 2.54 s is named and joins risk 14's rev-4 follow-up |
| 6 | low | DA-GUARD has no reach floor | **Fixed.** At least one reached landing across CAL2, CAL3, DESK and REST on a plain run, else red "not reached"; UNREACHED/VOID under `life`. Open item 3 settled: judged |
| 7 | low | The spec replaces decision 8's literal reading with a new constant without asking the owner | **Fixed.** Added as owner question 1, with the two mutants as the one-line reversal |
| 14 | low | Seam name clash, rows not buildable as written, a sentinel collision, wrap twins | **Fixed.** The rules live in a nested `ArriveRules` with seam `DwellAge` (PIN owns `Rules.Age`, :2931); Holds and Spend rows carry concrete ids; `episode.on` plus null values replace the −1 sentinel; `_i32` in every Int32-delta twin and row dwellage.wrap (C#'s unchecked wrap reads 1600) with mutant `arrive_age_long_math` |
| 15 | low | DA-ARRIVE can VOID whole; the `arrive` word lacks `WORD_LEGS` | **Fixed.** DA-ARRIVE leaves `CROSS_GAME` and loses only its overlap clause under an unfit clock; `WORD_LEGS["arrive"] = ("CAL",)`; DA-GUARD in `PROBABILISTIC` |

## Build log

**2026-10-30, build.** Rev 2 was built as three parts (engine, kit, bench). An adversarial review of the build confirmed 9 findings
(1 blocker, 1 major, 7 minor), all fixed, and a critic pass closed the world-bench gap. The engine compiled clean (0 errors) and
was deployed, with the live DLLs backed up first (set 20261030-080923). `memoria-patches/s164-netsync-field-swap-timing.patch` was
re-captured with the guard, and ARRIVE (30611) was redeployed at 64. The first duo run (run 20261030-054437), on round 1's code,
had confirmed ARRIVE's predicted red at 68 (`SWAP-TIMING-S164.md` rev 4, under DA-ARRIVE). Nothing has run live on the guard yet: the
proof line, leg G, DA-ARRIVE and DA-GUARD are its first live checks. The owner questions' defaults were taken (Open for the review). `NetSyncClient.cs` has 0 hunks.

Where the hunks landed (the clone with s164 and the guard):

| Hunk | Spec | Built |
|---|---|---|
| The behaviour hunk | `NetSyncStepOut.cs:570` | :576-578 (the two s164 comment lines replace the old trailing s162 comment) |
| The header paragraph | `NetSyncStepOut` | :68-73 |
| `ItemArrive`, `ItemNames`; `FaultsBy` | :203; :365 | :203-204; :394 |
| The state (R, the guard, the episode, `last`, the counters, the fault) | beside PIN | :364-387 |
| The pure rules | beside PIN | :794-903 (`ArrivalLeadMs` :806) |
| `ForgetArrive("session")` | `ResetSession`, `ForgetHostNonce` | :1214, :1333 |
| `ArriveHostFrame(...)` | after `PinHostFrame` (:1116) | :1257 |
| `ArriveTick(myField)` | `GuestTick`'s first statement (:1299) | :1444; `GuestTick`'s doc block now names the guard's reads and writes (review) |
| The live guard | | `ArriveLanding` :1977 to `ArriveFault` :2339 |
| `ArriveLanding(fld)` | `OnFieldLoad`'s first statement (:1978) | :2511 |
| `Usage`, `OpRole`, the lever cases | :2284, :2291 | :2816, :2836 and :2846, :3018 and :3027 |
| The release | `HarnessRelease`, `ReleaseLevers` | :3159, and `ForgetArriveBench` :2329 |
| The state readers | | :3326-3359 |
| The proof | beside D+E's (:4287, :4309) | `ArriveRules` :4646, `RowsArrive` :4665, `ArriveMutantNames` :4858, `MutantsArrive` :4873; called at :5138 and :5169; the tail :5183 |
| `HarnessAgent.cs` | the ProtocolVersion paragraph, :4107, :5254-5263 | :407-413, the catch literal :4114-4117, `levers.arrive` :5275, `AppendSwapArrive` :5324 and :5342 |

Departures from this spec (each passage above that it contradicted now says "as built"):

| # | Part | As built | Why |
|---|---|---|---|
| 1 | Engine, proof | 501 rows / 183 mutants, not 500: the base counted from the code is 426 rows (NetSyncSwap 324 with 11 live rows, plus D+E's 102) and 146 mutants (103 + 43); the guard adds 74 pure rows, the live `arrive_codec` row and 37 mutants | The spec miscounted the base |
| 2 | Engine, R's writer | `ArriveRecordEdge(body, field, nonce, tick, seenTick, seenLanding, bench)`. The late step is split out as `ArriveAfterEdge` -> `ArriveLateEdge` and runs only for writes made after my landing (a live frame, or a negative bench lead) | A bench write with lead >= 0 cannot re-anchor the previous guard on a same-field reload |
| 3 | Engine, episode | An episode still on at the next landing is classified first (framesSinceDwell forced to 3, with the step-out's live Active and why), then reset | A held episode whose base died in a load still counts its end |
| 4 | Engine, the fault | The sticky fault makes `ArriveLanding`, `ArriveHostFrame` and `ArriveTick` inert and clears the live guard, the episode and the bench (`armed` reads false); `ForgetArrive` and the readers still run; its line ends with NoteFault's " (logged once per site)" | The guard fails open to s158 for the rest of the process |
| 5 | Engine, counters | Counting needs armed and not spent, so a late edge after a spend counts nothing; it still updates `lead_ms` and `late` for the report on any guard | The counters follow the spec's "armed guards only" |
| 6 | Engine, cost | `ArriveTick` reads three bools per idle Update, not two | The bench's late write must run on an unarmed guard (G-LATE under the solo `arrive` word) |
| 7 | Engine, bench | A negative-lead bench whose late write has not fired by my next landing is dropped (one-shot); its bench line prints the actual offset | One-shot means one landing |
| 8 | Engine, `last` | `last` takes every classified episode, unheld ones too (end null); only held ends bump `ends` and print | G-INERT can read `last.shift_ms` 0 with `last.end` null |
| 9 | Engine, mutants | Ordered by rule (Seen ... Count), not by the two-column table; `live.arrive_codec` reads no seam, so no mutant decides it | |
| 10 | Engine, `ForgetArrive("session")` | Spends a live guard and forgets R, but leaves the bench arm alone | The release owns the bench |
| 11 | Kit, battlewire / fakegame | Extra names: `ARRIVE_DWELL_MS`, `ARRIVE_STEP_IN_MS`, `ARRIVE_OUT_*`, `SWAP_ARRIVE_RULES`, `ARRIVE_EPISODE_FRESH_FRAMES`, `ARRIVE_LINE_PREFIX`; `FG.NETSYNC_SWAP_ARRIVE_KEYS`; fakegame keeps both halves of the totals | battlewire has no step-out twins and cannot import fakegame |
| 12 | Kit, twins | `arrive_log_anchor` takes an explicit `late` flag; `swap_arrive_spend` and `swap_arrive_count` wrap their Int32 inputs through `_i32` too | The engine picks the wording from its late flag, not from the lead's sign |
| 13 | Kit, the driver (review: blocker) | `tools/harness/session.py` gains both ops, the `arrive` word, the arrivebench range and the usage literal | The kit list left it out, so the driver refused both ops itself |
| 14 | Kit, tests (review) | The row table is hand-written and also checked against `RowsArrive` parsed from the live stack; the 146-mutant base is read off the patch stack with an anchored pattern (unanchored, the swap list reads the guard's 37) | A base checked only against itself could never fail |
| 15 | Bench, leg G's P8 (review: major) | Requires a FRESH bench record: a new `arrive.host.nonce` for 30611 against the row's start | No `swap clear` between rows, so the previous row's record always stood |
| 16 | Bench, HOME's spend (review) | Each row first waits up to 3 s for HOME's own guard to spend (`arrive.armed` false) before its counter base; a timeout is UNREACHED | HOME's unanchored guard could spend inside a row's deltas above about 44 fps |
| 17 | Bench, B - G (review) | Read at the episode's own base on both benches (else the first base sample); a base 0 ms old counts as a base | The first base sample can belong to a base that re-armed before the episode |
| 18 | Bench, G-OFF | Its s158 window is [1500 - 16, 1500 + one frame + 16] | The OUT instant and B mix the QPC clock with TickCount ages (16 ms resolution) |
| 19 | Bench, G-DELAY | `last.shift_ms` within one frame + 16 ms of the full rule min(K, max(0, K - ((B - G) + 600))) | B - G carries TickCount's resolution |
| 20 | Bench, leg G terms | G-HOLD reaches on a raw base peak >= 1500 or a dwell OUT, and spends within [-1 frame, S + 0.3 s]; G-DELAY and G-INERT need exactly one OUT by dwell; G-DELAY also `last.end` delayed; G-OFF also `spends.out` +1; every G row pins `arrival_lead_ms` 1040 (a plain red); P8's episode clause applies only with `levers.arrive` act at the landing | Each term closes a way a row could read green on the wrong run |
| 21 | Bench, K legs | K's arrive checks are unconditional (an engine without the guard reds K; leg G alone is refused when `netsync.swap.arrive` is absent); K-RELEASE also requires `arrive.host.bench` false on its closing follow | Live proof that the release forgot the bench arm |
| 22 | Bench, duo | `life` scope as a per-sub-leg lever (old except the two ARRIVE runs); DA-ARRIVE's tolerance uses the run's frame time; under `arrive` its red reads "the guard was off at this landing" ahead of the named reds; DA-GUARD's scope counts every CAL2, CAL3, DESK and REST landing, REST-OLD included, per intent; the retune rule is a reported string | Equivalent to the spec, read per intent |
| 23 | Bench, an unregistered ARRIVE_ID (review) | Recorded VOID (a setup miss), never the `arrive` word's predicted red | With `BASELINE_RED` empty, a plain red would have passed the word |
| 24 | Bench, the duo's watches (the duo's fix round) | Reported apart, never judged; the DESK watch's 351 window ends at the 352 landing | The first duo run's five DESK watch OUTs were 352's lawful scene |
| 25 | World gates (critic) | `coop_world_wait` and `coop_world_battle` fold the clause into every world-rejoin row (S144-RJ-LAND, S144-D3; S145-WB-300, S145-HF-REJOIN, S145-D3) and also require `arrive.field` = the rejoin field. Not judged on an engine with no `netsync.swap.arrive`, or on a publisher that numbered no landing (the stand-in); a faulted guard is judged, red. `lead_ms` is reported in a note | No new row id, so every catalog and calibration set stays as it was |

## Open for the review

The build took the default on all three (Build log); each stays reversible as stated.

1. **Owner: decision 8's reading.** The spec reads "my landing + the host's arrival lead" as the lead the host is owed, K − (G − Hs),
   which adds `ArrivalLeadMs` (K = 1040, a seed tied to s163's n = 23 measurement and not to `OldWaitS`) and makes the guard
   lag-invariant. The literal reading (origin 2G − Hs) and "my landing + K" are one-line reversals: the mutants
   `arrive_literal_lag` and `arrive_from_my_landing` show each.
2. Whether the own-pass late-read bias (threshold D + L + K, 2.64-2.84 s at L 0.1-0.3) is acceptable until two-PC logs size it.
3. **Owner: ARRIVE's retune 68 → 64.** It changes s164's bench field and its round-1 red prediction (base about 1.65 s nominal
   instead of 1.8 s). The alternative is to keep 68 and accept "margin miss" reds at O + δ7 − δx ≥ 273 ms.
