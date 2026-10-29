# The host's speed on a following guest (engine round s163)

**Owner decision (2026-10-28, after the third two-PC session): "match host speed".** When the host plays a scene or an
ATE at 3x, a following guest's copy runs that scene at the booster speed too; free roam, battles and the world map stay
at the guest's own speed, and the guest's own F1 keeps working. This is the cause-level fix for GUEST-TRAVERSAL-TWO-PC.md
Finding 10 ("Dagger Tries" cut at line 162 of 175 behind a 3x host) and the rate half of Finding 4. Finding 4's second
half, a capped follow-hold for NON-ATE scenes, is NOT in this round (open work; s161's tail hold already covers ATEs).
Builds on s162 (the ATE landing start). Revision 2 folds in the design review (three lenses, 2026-10-28). Revision 3 folds
in the code review of the built rev 1 (six lenses, two skeptics per finding, a completeness critic, 2026-10-29): see
"Revision 3" at the end.

## What the booster is (verified in the s161 clone)

- `SettingsState.FastForwardFactor` (`Global/SettingsState.cs:66-75`): `[Cheats] SpeedFactor` (default 3) when the scene
  is `Movie`, or when `IsFastForward` (the raw flag `IsBoosterButtonActive[1]`) and the scene is not `QuadMist`; else 1.
  It is the hottest getter in the engine: `FPSManager.AdvanceUpdateCounter` reads it every frame from boot
  (`FPSManager.cs:83, 95-97`) and runs that many main-loop updates. That is what makes walks, waits and timers 3x.
- `SetFastForward(on)` (`SettingsState.cs:326-362`) writes the raw flag, then drives HonoBehaviorSystem's FAST MODE
  (`_nextFastMode`: typing, dialog waits, bubbles; copied to `_fastMode` one Update later), and re-pitches playing SFX.
  Stock re-runs `SetFastForward(raw)` at every scene load (`UIManager.cs:358`) and every HUD clear (`EventHUD.cs:17`), and
  stops fast mode (not the factor) in the Auction and Pandemonium-elevator HUDs (`:333`, `EventHUD.cs:19`).
- Flipping fast mode mid-scene is safe: field actor clips are re-sampled every HonoUpdate (`FieldMapActorController.cs:
  157-160, 405-430`), the path a stock mid-cutscene F1 already takes. `MBG.SetFastForward` is a no-op in Memoria.
- An MBG exists on every field (`HonoluluFieldMain.cs:197` creates it lazily), so "a movie is playing" is stock's own
  booster lock, `!MBG.IsNull && !MBG.Instance.IsFinishedForDisableBooster()` (`UIKeyTrigger.cs:241`).
- SFX re-pitching compares the live factor with the guest's OWN SpeedFactor and keeps one bool per sound
  (`AllSoundDispatchPlayer.cs:1388-1412`), so any factor other than 1 or the guest's own SpeedFactor strands pitches.
- A battle reads the factor once at its boot (`BattlePlayerCharacter.cs:48, 68`); `_Swirl` sets `SwirlScene` first.
- Nothing about any of it is on the co-op wire today.

## The rule

**Host.** Every state frame carries **section 10** = `[setting u8][fieldTps u8]`: its booster SETTING
(`IsFastForward ? SpeedFactor : 1`, clamped 1-255), not its scene-dependent live factor (which reads 1 at every load, in
battle and on the world map: exactly when a 3x host has just left the guest's field), and its `[Graphics] FieldTPS`.
It goes BEFORE section 7, right after section 5 or the start lane (6 or 9), so `[0,1,2,3,(4),5,(6|9),10,7,8]`:
DressSelfTest and coop_peer's `dress` tape both require section 8 to come right after 7 and last. Additive under wire
v14: every engine and kit walker skips an unknown id by its length; an old host never sends it. One host log line per
booster edge.

**Guest.** `ObserveHostDialog`'s new-frame branch also reads section 10 into a cached host setting (a null state, a
missing id or a malformed body = absent = 1). `NetSyncSpeed.Tick` runs every Update after `ServiceStepOut`. The mirror
is a LATCH, so it never ends on the host's state (s158's law: the guest's copy trails the host, and its tail is still the
scene):

- **START** (all, `StartRule`): a following, mirroring guest (the step-out's `eligible`) on a live field (gMode 1, the
  field scene); my control off; the host's setting > 1; no guest climb in flight; no movie playing; and my copy plays the
  host's scene, one of: (a) the host on my field with its control off (section 7's cached view for THIS field, the
  step-out's `hostCtlOff`), (b) the s161 ATE episode in flight on this field, (c) a relayed talk or chest accept owns my
  control-off episode on this field (`NetSyncStepOut`'s talk latch).
- **END** (any, `EndRule`): my control back for `StepInMs` (500 ms); a field change or landing; leaving the field scene;
  eligibility lost; a guest climb starting; a movie starting; the host's setting dropping to 1; the lever. Never the
  host's control, position or link.
- **The factor** (`FactorRule`): the guest's OWN `SpeedFactor` G, so SFX pitches stay right. It applies only when it
  does not overshoot the host: `G * ownTps <= hostSetting * hostTps`. Otherwise the mirror refuses, and a mismatch of
  SpeedFactor or FieldTPS is logged once.

**Applied through two seams, never through the raw flag.** A holder class with plain static fields and NO initializer
(`NetSyncSpeedArmed { Standing, Factor, Field }`, the `NetSyncAteArmed` pattern), written only by `Tick`, so a vanilla
or solo game pays one bool read and never type-initializes NetSync code from FPSManager:
- the getter keeps the stock body as `StockFastForwardFactor` and returns `max(stock, Factor)` while `Standing`, on the
  field scene (the `str` it already read) and `Field == fldMapNo` (a verdict from another field reads nothing);
- `SetFastForward(on)` still writes the raw flag with the player's own value, but turns FAST MODE on when `on ||
  ModeWanted` (the same three tests). Stock's re-runs at scene loads and HUD clears then keep the mirror's mode, and the
  Auction / Pandemonium branch still refuses it there, as on the host. The guest calls `SetFastForward(IsFastForward)` at
  each edge, which also re-pitches SFX.

`StockFastForwardFactor` is the only "own factor" anything reads (Tick, the log, the harness), so the mirror never reads
its own output. The raw flag is never written: a 1x host with a 3x guest still runs the guest at 3x (README step 3 stays
testable), and the guest's battles keep the guest's own speed. One guest log line per edge, naming the factor and why.

## Levers and harness

- `netsync speed act|off|host <n>|clear` (released by HarnessReleaseBench): `off` = CALIBRATION, s162's rule (never
  mirror), legal on any role since rev 3 (the duo's calibration); `host <n>` (1-255, selftest role only) builds a
  section-10 body through the real codec into the same cache, for the solo bench (with `hostscene 1` as the host's
  control-off scene).
- `speedmode 1|0`, a top-level harness verb on any role (the s94 `noencounter` precedent): the REAL booster path,
  `CallBoosterButtonFuntion(HighSpeedMode, on)` plus the HUD icon; `reset` and the disarm switch it off when the harness
  set it. The duo bench puts the host at 3x with it.
- `netsync.speed`: `host_setting`, `host_tps`, `host_seen`, `src` (wire / bench / none), `own_factor` (stock), `mirror`,
  `factor_now` (the REAL getter), `mode_wanted`, `fast_mode` (HonoBehaviorSystem, read a frame after an edge), `raw`,
  `why_not`, `edges_on`, `edges_off`, `lever`. The top-level state doc gains `ff` (the live getter), so the kit's
  tickrate reach model multiplies by it.
- Kit: `NETSYNC_SUBVERBS` gains `speed` after `ate` (the agent's list, Session and FakeGame must agree in order); a
  battlewire twin `SECTION_SPEED = 10` and its codec; the state-section pin widens to `{9, 10}`; a coop_peer `speed` tape
  check modeled on `tape_dress`.

## Proof

- Pure rules with selftest rows and mutants: `StartRule` (all terms hold -> start; each term false alone refuses with its
  own why_not; each of (a)/(b)/(c) alone starts; a host control-off view cached for ANOTHER field refuses; host here with
  control on refuses), `EndRule` (each end term alone; the host's control back while mine is off keeps it; mine back
  under 500 ms keeps it), `FactorRule` (G within the host's rate; an overshooting G or TPS refuses; host 1 refuses),
  the getter rule (mirror on a field = G; in battle or another field = stock; the guest's own F1 without a mirror =
  stock), `ModeRule`, and the section-10 codec (round trip; an old reader skips it; a truncated body is refused).
  Mutants include: always refuse; each term dropped; a level-triggered end (the host's control back ends it); own read
  through the seamed getter; `>=` vs `>` on the setting; an idle MBG vetoing.
- Solo bench `coop_speed_mirror.py` (selftest role): with `host 3` and `hostscene 1`, my control off: `factor_now` 3,
  `fast_mode` on, `raw` false; `hostscene 0` with my control still off keeps it (the latch); control back past 500 ms, a
  battle, the world map and `off` read 1; `speedmode 1` with `host 1` still reads 3 (the guest's own F1).
- Duo bench `coop_speed_mirror_duo.py`, pinned to Finding 10's ATE (351 -> 450 "Dagger Tries"): the host at 3x through
  `speedmode 1`; the guest's copy keeps pace -- no tail hold released by "the tail hold's progress clock", no host seq
  dropped as another field's, the guest back on 351 within a few seconds of the host. Its CALIBRATION (rev 3) is
  `netsync speed off` on the guest with the same DLL (a swap to s162 would take `speedmode` from the host too), which
  must red exactly those rows.

## Risks accepted

- Stock readers of the RAW flag keep 1x behaviour under the mirror: SceneDirector's fade frames (`SceneDirector.cs:556,
  596`), the Prima Vista 3x fixes (`DoEventCode.cs:1846`), TimerUI's countdown with the `SpeedTimer` cheat on
  (`TimerUI.cs:213`), the booster HUD icon, and stock's own force-off points (the ending fields, field 2934), which the
  mirror follows only when the host's setting drops a frame later.
- A SpeedFactor or FieldTPS mismatch between the machines disables the mirror (logged once) rather than overshoot.
- HostHoldsInput cannot tell the host's scene from its own climb, jump or unserved chest, so a coincident guest
  control-off beat (a door fade-in) can start the mirror; the latch then ends it with my control back.
- At equal speed the guest can now finish an ATE first, which leans on s161's exit hold (proven by self-test only).
- Every two-PC lane was proven with a 1x guest; the step-out's and the dialogue lock's real-time constants now see 3x beats.
- A non-ATE scene's last lines can still be dropped when the host's scripted `Field()` beats the guest's last close by more
  than the host's tail (Finding 4's follow-hold, not built).

## Revision 3 (the code review of rev 1)

Upheld and changed:
- **A stale lane is not an end.** Rev 1 read a null state (no host frame for 2 s) as "absent = setting 1" and ended the
  latch, logged as "the host's booster is off". That is an end on the host's LINK. Now a null state is no news: the last
  fresh section 10 is kept and marked stale; a START refuses while stale; the END never reads it (the latch still ends on
  my control back, and a lost session ends it through eligibility, as the step-out's grace does). Only a FRESH frame
  whose section 10 reads 1, or that carries none (an old host) or a malformed one, drops the setting.
- **Free roam stays at my own speed.** The latch's END is still debounced (my control back for StepInMs), but the factor
  is APPLIED only while my control is off. Rev 1 kept 3x for the 500 ms debounce: about 1.5 s of game time, enough for a
  held direction to reach a gateway.
- **The duo calibrates on one DLL.** Both duo games load the same Assembly-CSharp through the instance junction, so an
  s162 swap leaves the host without `speedmode`. `netsync speed act|off|clear` is therefore legal on ANY role (off only
  disables, and is released with the harness); `host <n>`, which fabricates a host frame, stays selftest-only. The duo's
  calibration is `netsync speed off` on the guest, same DLL.
- A start-edge fault fails open (Stop), the proof line says "FAIL (", `netsync.speed` publishes the end reason and faults,
  the mismatch log waits for an eligible guest, the guest clamps its own SpeedFactor and FieldTPS like the host, the
  identity "rules" and their padding mutants are gone, and every term has a killing row.

Accepted (documented, no code): the guest's own F1 OFF cannot slow a mirrored scene (the max); a guest with
`[Cheats] SpeedMode = 0` still mirrors at its SpeedFactor; the step-out's DwellMs is wall-clock, so under the mirror a
no-line scene shorter than 4.5 s of script never steps out; the latch holds through a host menu or a declined battle
while the copy waits at its next locked line; the ~ debug menu's Speed toggle sets the raw flag without SetFastForward;
the raw-flag readers UIScene (fades), MainMenuUI and HUDMessage stay 1x under the mirror.
