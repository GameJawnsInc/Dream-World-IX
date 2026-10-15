"""R3 T2 -- THE CUT, HELD: the guest half of the solo two-role bench (studies/battle-coop/R3-SITTING-A-FIXES.md "T2" and
the s119 / s120 / s121 "Bench." paragraphs), run unattended, ONE LEG PER LAUNCH. [ff9mapkit netsync R3 T2]

THE GAP. Sitting A (2026-10-14) cut the link for ~6 s mid-battle. Behind the local bridge the game's hop never drops, so
the s56 watcher read "stale + IsConnected" as "the fight is over": the laptop left its diorama within ~2 s and stamped the
skip (laptop-Memoria.log 155 'diorama LEAVE requested -> FieldMap (mode 1)', 159 'diorama watcher-leave settled (nonce
3) -- the same fight won't re-boot on reconnect'), the 3 s exit ramp reloaded its own autosave (166), and its Menu key was
refused in silence all session. The fixes are GUEST-side, so they are benched here, with the desktop as the GUEST:
  s119  the diorama hold keyed on PEER-ALIVE (IsConnected && GetRemote().Valid): a stale lane holds the scene frozen on the
        same nonce until the peer says the fight is over (back on a real field, or its end block latched terminal) or the
        cap; one hold line, one resume line, the ready mirror re-serves.
  s120  one SessionGraceMs (30000) replaces the 3 s ramp debounce AND the 8 s hold cap: an outage inside it resumes the
        session, the held diorama and the ghost; past it the session ends (bounded), the held diorama leaving first; a
        "reconnecting (N s)" overlay; a peer alive but silent on its battle lane leaves at the 8 s stall cap.
  s121  a mirroring guest's Menu press on FieldHUD/WorldHUD buzzes (FF9Sfx 102) and logs one line per place.

THE BENCH. tools/harness/coop_peer.py `replay-host` stands in for the bridge on ws://127.0.0.1:<COOP_PEER_PORT, 49201> and
replays the HOST tape coop_tape_record.py made (default: the tape latest.json names in <main repo>/.harness-runs/coop-
tapes/; COOP_TAPE overrides), the TCP left open and SILENT through each `--blackhole-at/--blackhole-for` -- exactly what a
Wi-Fi cut looks like behind the decoupled bridge. The desktop: New Game on the tape's field (250), encounters off, the story
marker's bits watched (gEventGlobal byte 1121, 0x00 in the guest's own save, 0xA5 in the host's), then Memoria.ini
[Netsync] (BACKED UP FIRST to the MAIN repo's backups/ and the run dir; restored byte-exact in the `finally`; the engine
hot-reloads it): Enabled 1, Role client, RelayUrl ws://127.0.0.1:<port>, SessionCode ff9-T2BENCH1, FollowHost 1,
TargetField 0, GuestSlots 0, GuestStockMenu 1, SessionGraceMs 30000 (COOP_GRACE_MS, written AS THE ENGINE READS IT --
_coop_peer_bench.engine_grace, ParseSessionGrace's 5000-40000 clamp -- and every window built on that same value),
AutoTeleport 0, DioramaSwirlFrames 0. The exit ramp reloads the guest's OWN autosave of that field, so the install's
[SaveFile] AutoSaveOnlyAtMoogle must be 0 (a non-moogle field never autosaves under it): the leg refuses up front if not.
The replay clock starts at the guest's first frame. Every judged moment is a window "seconds after the BLACKHOLE line" (the
coop-peer's ms stamp; Memoria.log's whole-second stamps are floored), from the engine's clocks (_coop_peer_bench.
leg_windows). Each leg is its OWN launch: replaying one tape twice into one guest session repeats the host's dialogue epoch.

THE LEGS (COOP_CUT_LEG; the cut is planned off the tape's own facts -- _coop_peer_bench.plan_leg -- and refused with the
reason when the tape cannot carry it):
  cal          no blackhole. CAL-1 'paired on the host's field (250)', CAL-2 'state-mirror ARMED', CAL-3 'diorama BOOT
               scene=<the tape's>', CAL-4 'diorama LIVE ... (host battle nonce N, booted from wire nonce N)', CAL-5 the
               end-leave ('diorama END: end-leave attempt', 'diorama LEAVE requested', 'diorama leave noted (nonce N)', a
               RETURN to 250 -- never a watcher-leave), CAL-6 the replay on time (no 'running late', no blackhole). Writes
               <tape>.cal.json: until it reads OK for THIS tape (sha256), every other leg reads "not reached" -- the
               instrument is untrustworthy (COOP_CUT_FORCE=1 runs anyway, its T2-CAL red).
  s119         6 s at battle+10 (the sitting-A row). I: paired/ARMED/BOOT/LIVE logged before the cut, the diorama booted at
               it. G1 no 'diorama LEAVE requested' and no 'watcher-leave settled (nonce N)' from the cut to the resume+3 s;
               G2 exactly one 'diorama: peer silent mid-battle -- holding ... (nonce N; ... a cut; ...)' inside the hold
               window (the CUT variant: a stall variant here would be the engine misreading a cut); G3 one 'back on the
               same fight (nonce N) after a M ms hold -- resuming' in the resume window, M ~ the cut minus StaleMs; G4 the
               reconcile resumes on the SAME nonce (netsync.battle.peer live, nonce N, a seq past the last pre-cut one) and
               the diorama never tore down; G5 the ready mirror re-serves ('ready mirror is SERVING' after the resume line);
               K netsync.diorama.hold holds +1, resumes +1, gaveup +0. [s131] G3 judges M by THE HOLD RULE (below).
  readopt      [ff9mapkit netsync s131] the s119 cut MOVED to the nearest placement at or after battle+10 s whose TAIL is
               >= 66 ms (the re-adopt class: _coop_peer_bench.readopt_placement scans the tape and refuses, with the
               reason, when none fits; the 2026-10-14 tape gives 81.65, the confirmation's 81.66 stretch). I, G1, G2, G4,
               G5 and K as s119; G3 the hold by THE HOLD RULE (no nominal fallback); X the s131 key
               netsync.battle.peer.expired across the cut: count +1, refused +1, frames >= 1, ms in [tail - 100, tail +
               35] (the run-out to its last refused repeat), and one 'battle lane: the host's last frame (nonce N, seq S)
               ran out of freshness ... not re-adopted' line on nonce N -- the key ABSENT reads red (an engine with the
               defect).
  s120-battle  20 s at battle+8. I as s119. G1 no 'session ended -> reloading own autosave' from the cut through the
               post-victory window; G2 one 'session: the host went silent (the hop is up: a cut or a stall upstream) --
               holding the session for up to 30 s ... (the diorama holds); outages=K' in the outage window; G3 one 'the host
               is back after M ms -- inside the 30 s grace, the session continues (no exit ramp; still mirroring)' in the
               resume window, M ~ the cut minus StaleMs; G4 the diorama held through it on the same nonce (one hold line,
               its resume line, no LEAVE / watcher-leave / give-up line in between) [s131] and its M ms by THE HOLD
               RULE against G3's M; G5 after the recorded victory (the end-leave's RETURN, before the tape's end) still
               mirrored: netsync.session.mirroring true, ramp_pending false, state "live", and no 'session ended' line;
               K session outages +1, resumes +1, gaveup +0, hold resumes +1.
  s120-long    40 s in free roam (15 s after the tape's start). I paired/ARMED before it. G1 no 'session ended' before the
               grace runs out; G2 one outage line; G3 the give-up line 'silent for M ms, past the 30 s grace -- the session
               ended; the exit ramp reloads your own autosave ...' (M in [30000, 31500]) and then 'session ended -> reloading
               own autosave (Continue)', both at about grace + 2 s (bounded); K session gaveup +1, outages +1, resumes +0,
               state "grace" on the samples inside it.
  s120-roam    20 s in free roam. I paired/ARMED before it and the marker reading 0xA5 (the host's story). G1 no 'session
               ended' and no ramp from the cut to the resume+8 s; G2 the reconnecting overlay (netsync.session.overlay
               "reconnecting", its detail COUNTING DOWN: never rising, and falling by the seconds the samples span, +-1.5
               s) on every sample from the ghost hold's end to the resume; G3 the
               outage line and the resume line ('... (no exit ramp; still mirroring)'); G4 within 3 s of the resume
               session.ghost true, mirroring true, ramp_pending false, state "live"; G5 THE STORY BYTE: the marker reads
               0xA5 on every sample from the cut to the resume+5 s (an own-autosave reload reads 0x00).
  span         a cut from 4 s before the end block turns terminal to 4 s after the battle lane ends (THE TAPE'S VICTORY
               INSIDE THE CUT). I BOOT/LIVE before it. G1 no LEAVE / watcher-leave before the cut ends (the guest holds
               through the unseen victory); G2 at the resume the over-verdict for the tape's after-battle place -- a field
               tape: 'diorama watcher: the host's fight is over (the peer is alive and back on field 250) -- leaving (nonce
               N, after a M ms hold ...)' [s131] its M by THE HOLD RULE's leave-ended form; a WORLD-MAP tape
               (COOP_CUT_LEG=s120-world requires one): the stall-cap line 'still silent after 8s with the peer alive on
               field 0 ...' (it prints no hold ms: no rule) -- then 'diorama LEAVE requested', 'watcher-leave settled
               (nonce N)' and a RETURN; K netsync.diorama.hold.why == "host_field" | "stall_cap".
  s121         the replay STOPS 25 s after its start (free roam only; --at-end hold: the host then goes silent). I paired/
               ARMED, the guest playable on FieldHUD. G0 before the press netsync.menu_refusal.now == "audible" (the press is
               gated on it when the key exists, never on ui_state); G1 press 1: menu_refusal.count +1, lines +1, last_state
               "FieldHUD", last_field 250 (`muted` reported: the buzz asked for); G2 press 1: exactly one 'main menu
               suppressed (following guest) on field 250'; G3 press 1: ui_state stays FieldHUD for 2 s (never the main
               menu); G4 press 2, same field: count +1, lines +0, no second line; G5 the control row's state: once the replay
               has stopped and the exit ramp fired ('session ended -> reloading own autosave'), on FieldHUD with control:
               now == "open"; C1 the control row itself: Menu then OPENS the stock main menu (closed again).
COMMON: T2-TAPE the tape reads back and this leg's plan fits it; T2-CAL (not on cal) the CAL verdict for this tape;
T2-PEER the port free, the guest config applied live (the engine's own config line: role=client, the bench code), the
guest dialled the peer and the replay started; T2-SAVE (final) the guest had its OWN autosave to end a session on --
AutoSaveOnlyAtMoogle off before the run, and no 'session ended, no autosave to resume -> title screen' line in it (the
exit ramp's other branch: every "no session end" check reads BOTH lines, _coop_peer_bench.session_ends, so a guest with
no autosave can never read green there); T2-INI (final) Memoria.ini restored byte-exact.

THE HOLD RULE [ff9mapkit netsync s131] (R3-SITTING-A-FIXES.md "The hold-onset variance: the Pump null RE-ADOPT"). A hold
length is judged against the SAME run's outage ('session: the host is back after M ms') plus THAT cut's TAIL -- the final
pre-cut seq's last receipt minus its first, read off the tape at --blackhole-at (_coop_peer_bench.tape_tail: 0/33/67/
100/133 ms, set by where the cut lands; the T2-TAPE line names it) -- never a nominal window: s119's 6 s cut sits 9 ms
inside the tail-0 class, so the old 3000-5500 ms window was green by placement luck. Post-fix (s131): (hold - outage) in
[tail - 40, tail + 70]; a leave-ended hold (span's over-verdict): (hold - 500 - outage) in [tail - 55, tail + 85]; and at
most one 'stock menu: closed all (ready mirror: no live peer battle lane)' across the cut. A pre-s131 guest re-adopts the
frozen frame whenever the tail outlasts its Updates, so its hold opens ~(2000 - tail) ms late (and a Ready slot's menu
shuts twice): RED there at a tail >= 66, a maybe at 33, green at 0. The rule lives in S119-G3 (an engine with no outage
line -- pre-s120 -- keeps the nominal window there), S120B-G4, SPAN-G2 (host_field only: a stall-cap verdict prints no
hold ms) and READOPT-G3 (no fallback).
THE CLOSE CLAUSE [s131 fix] bites only when the ready mirror HOLDS a slot at the cut (MirrorStandDown closes nothing
otherwise). On the 2026-10-14 tape that is span's placement (2 closes on s121, 001818) and P5's K4 (2) -- never the
mid-fight s119 / readopt / s120-battle placements, where every archived run logged 0 closes -- the runs that DID re-adopt
included (confirm-s119 at 81.66, both s120-battle runs at 79.59: hold - outage -1938 / -1921 / -1953). There it is INERT
on every engine: those checks read the re-adopt through the hold arithmetic alone; the clause is calibrated by span and
K4 only.

CALIBRATION (COOP_CALIBRATE=1 adds <LEG>-RED -- the s117 defect REPRODUCED, the instrument's proof it can see it -- and
<LEG>-CAL, which judges the run against the predicted red set of the engine it FINDS by its published keys: s117 =
netsync.battle.end.follow_msg, s119 = netsync.diorama.hold, s120 = netsync.session, s121 = netsync.menu_refusal, s131 =
netsync.battle.peer.expired). s117 has no hold/session/menu_refusal block: every GREEN check keys on an engine line or an
observable state FIRST, and a key it also reads is ABSENT there -- read as None, never as a pass.
  s119-RED     the sitting-A pair verbatim: 'diorama LEAVE requested -> FieldMap (mode 1)' and 'diorama watcher-leave
               settled (nonce N) -- the same fight won't re-boot on reconnect', both within ~2 s of the cut.
  s120*-RED    s117's 'session ended -> reloading own autosave (Continue)' at once (3 s after the lanes die).
  span-RED     the sitting-A pair, before the cut ends.
  s121-RED     s117's silence: press 1 gives no refusal line, and the menu stays shut.
  READOPT-RED  [s131] the pre-s131 re-adopt reproduced: (outage - hold) in [2000 - tail - 35, 2000 - tail + 50] ms (the
               hold opened at the SECOND stale edge, after the phantom 2000 ms) -- s121's defect, so GREEN on s119-s121.
  Predicted reds, by the engine found, at a TAIL-0 cut (the tail adds below):
    cal          none, on every engine.
    s119         s117: G1-G5, K.                          s119/s120/s121/s131: RED only.
    readopt      s117: G1-G5, K, X, RED.   s119: G3, X, RED (G2 maybe).   s120/s121: G3, X (G2 maybe: the hold line lands
                 at the SECOND stale edge, ~4.4 s after the cut, at its window's edge).    s131: RED only.
                 (the leg's tail is >= 66 by construction: the tail rule below never adds to it)
    s120-battle  s117: G1-G5, K.   s119: G1-G5, K (RED maybe: its ramp waits for the field).   s120/s121/s131: RED only.
    s120-long    s117 and s119: G1-G3, K.                 s120/s121/s131: RED only.
    s120-roam    s117 and s119: G1-G5.                    s120/s121/s131: RED only.
    span         s117 and s119: G1, G2, K (s119's 8 s cap leaves inside a ~15-20 s span; RED maybe).  s120/s121/s131: RED
                 only.
    s121         s117-s120: G0, G1, G2, G4, G5 (G3 and C1 GREEN: the s38 drop keeps the menu shut, and the control row
                 proves the press path itself).                                        s121/s131: RED only.
  THE TAIL ADDS [s131] (_predicted's tail_ms = the plan's, off the tape): on s120 and s121 -- and on s119 for the s119 leg
  (its nominal window catches a ~2 s-late hold) -- a cut with tail >= 66 adds the leg's hold check to its reds (S119-G3,
  S120B-G4, SPAN-G2), a tail in (0, 66) adds it as a maybe; s131 never. On the 2026-10-14 tape: s119 0 (no change),
  s120-battle 66.5 and span 66.6 -- so on the deployed s121 those two legs predict RED and their hold check.
  [s131 fix] The ONE exception, a stall_cap span (s120-world: _predicted's `why`, the plan's expect.why): SPAN-G2 judges
  no hold ms there and its verdict lands at the resume + the settle on either engine, so only the second no-lane close
  can read the re-adopt -- and that needs a slot Ready at the cut (the tape's, not the tail's): a MAYBE at any tail > 0.
  The I checks, T2-* and CAL-* are never predicted red: a red there is the INSTRUMENT, and the leg's verdict is void.
  The one exception is the forced run: under COOP_CUT_FORCE=1 a red T2-CAL is the force itself (the world-map tape whose
  CAL leg cannot pair), so <LEG>-CAL allows it and judges the leg's own checks -- that run's instrument verdict is manual.

RUN, in order (the game closed -- play.py launches it; the production bridge must NOT hold 49201; nothing heavy beside
it -- a loaded machine stretches the engine's clocks against the windows). Git Bash: `VAR=x py ...` scopes each knob
to that ONE launch, so no leg inherits the last one's:
    py tools/play.py studies/test-harness/scenarios/coop_tape_record.py              # 1. the tape (desktop = HOST)
    py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py                 # 2. COOP_CUT_LEG=cal (the default)
  3. calibration on the DEPLOYED s117 (each must read exactly its predicted reds):
    COOP_CALIBRATE=1 COOP_CUT_LEG=s119        py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py
    COOP_CALIBRATE=1 COOP_CUT_LEG=s120-battle py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py
    COOP_CALIBRATE=1 COOP_CUT_LEG=s120-long   py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py
    COOP_CALIBRATE=1 COOP_CUT_LEG=s120-roam   py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py
    COOP_CALIBRATE=1 COOP_CUT_LEG=span        py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py
    COOP_CALIBRATE=1 COOP_CUT_LEG=s121        py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py
  4. after s118-s121 are deployed: `COOP_CUT_LEG=cal` once more, then each leg WITHOUT COOP_CALIBRATE (all green), then
     with it (each reads RED only). A world-map tape (coop_tape_record.py's hand recording) has no field for its CAL leg
     to pair on, so it runs FORCED -- T2-CAL red by design, <LEG>-CAL allows it, the instrument verdict is manual (the
     force acts only on a red T2-CAL: harmless if that tape's CAL did pass):
    COOP_CUT_FORCE=1 COOP_TAPE=<tape> COOP_CUT_LEG=s120-world py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py
  5. [ff9mapkit netsync s131] THE RE-ADOPT, calibrated red on the DEPLOYED s121 BEFORE s131 deploys (the hold rule made
     step 4's "all green" a tail-0 claim: on s121, s120-battle and span now read their hold check red at the tape's
     66.5 / 66.6 ms tails -- predicted, so each <LEG>-CAL passes):
    COOP_CALIBRATE=1 COOP_CUT_LEG=readopt     py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py
    COOP_CALIBRATE=1 COOP_CUT_LEG=s119        py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py
    COOP_CALIBRATE=1 COOP_CUT_LEG=s120-battle py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py
    COOP_CALIBRATE=1 COOP_CUT_LEG=span        py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py
     (readopt: G3 and X red, G2 maybe, READOPT-RED GREEN -- the defect reproduced; s119 at tail 0: RED only; s120-battle:
     RED + G4; span: RED + G2). After s131 deploys (the DLL rebuild auto-deploys): COOP_CUT_LEG=cal once more, then
     readopt / s119 / s120-battle / span WITHOUT COOP_CALIBRATE (all green), then with it (each reads RED only).
  PowerShell has no per-launch form: a `$env:` value PERSISTS in that shell, so the next "normal" leg would run
  calibrated (or forced, or on another tape) without a word. Clear them after EVERY leg [ff9mapkit netsync R3 fix round 2]:
    $env:COOP_CALIBRATE='1'; $env:COOP_CUT_LEG='s119'; py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py
    Remove-Item Env:COOP_CALIBRATE, Env:COOP_CUT_LEG, Env:COOP_CUT_FORCE, Env:COOP_TAPE -ErrorAction SilentlyContinue
AFTER AN ABORTED RUN (a hard kill, a crash, a power loss -- anything that skips the `finally`): the install's
Memoria.ini may still hold this bench's [Netsync] guest values (SessionCode ff9-T2BENCH1) instead of the owner's session.
Compare it with the newest <main repo>/backups/Memoria.ini.pre-coop-cut-<leg>.<stamp> and copy that back if they differ
(the run dir keeps a second copy). [ff9mapkit netsync R3 resume]
NOT PROVEN HERE: the host side of a cut (s118's hand-back to a live guest is coop_handback_live.py's), the real bridge and
relay in the loop (coop_peer `relay` + `ff9mapkit coop bridge` -- T1's bench), feel. Two machines still decide those.
NOT BENCHED, ON PURPOSE [ff9mapkit netsync R3 fix round 2]: the s119 README row's third cut, "one inside the result
screen (no LEAVE)". The plan's s119 Bench paragraph -- the spec this bench implements -- names two cuts: the 6 s
mid-battle one (s119) and the one spanning the victory (span). A result-screen cut has no calibrated meaning yet: the
exit there is the END-LEAVE's (B5: it latches when the host leaves its battle and waits for the replay's Hide), whose
timing against a cut no run has measured; and the recorder confirms straight through the result screen, so that
stretch of a tape (F5's terminal -> result-hide) is short and unmeasured, with no room planned for StaleMs + the settle
+ a resume inside it. span covers the over-verdict at the victory; DioramaWatchSelfTest's rows cover the step's
terminal-latched, peer-silent HOLD ("terminal, the peer silent: hold" and its result-screen sequence).
Add the leg after a two-machine sitting measures the end-leave around a cut; until then the s119 README row's "Next"
should say it was dropped (memoria-patches/README.md is not a harness file: amend it with the commit).
"""
from __future__ import annotations

import datetime as _dt
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import _coop_peer_bench as pb                              # noqa: E402 - the T2 two-role bench helpers

HarnessError = cb.HarnessError

_RAW_LEG = os.environ.get("COOP_CUT_LEG", "cal").strip().lower()
LEG = pb.canon_leg(_RAW_LEG)
WORLD = _RAW_LEG in ("s120-world", "world")
CALIBRATE = cb.CALIBRATE
FORCE = pb.env_flag("COOP_CUT_FORCE")
PORT = pb.env_int("COOP_PEER_PORT", pb.DEFAULT_PORT)
CODE = pb.BENCH_CODE
#: [ff9mapkit netsync R3 s120] the grace the ENGINE will run: COOP_GRACE_MS through ParseSessionGrace's twin (quotes, the
#: 30000 default, the 5000-40000 clamp) -- the value written to Memoria.ini AND every window's, so the two never disagree
#: (a raw 45000 written as-is would be clamped to 40000 by the engine and judged against 45 s here: a correct s120 red)
GRACE_MS, GRACE_NOTE = pb.engine_grace(os.environ.get("COOP_GRACE_MS", ""))
GRACE_S = GRACE_MS / 1000.0
POLL_S = 0.1

PFX = {"cal": "CAL", "s119": "S119", "readopt": "READOPT", "s120-battle": "S120B", "s120-long": "S120L",
       "s120-roam": "S120R", "span": "SPAN", "s121": "S121"}
#: [ff9mapkit netsync s131] the check that judges each leg's hold LENGTH by THE HOLD RULE (the docstring's): red on a
#: pre-s131 engine at a tail >= 66 ms, a maybe in (0, 66), green at 0 -- _predicted adds it by the plan's tail
HOLD_CHECK = {"s119": "S119-G3", "readopt": "READOPT-G3", "s120-battle": "S120B-G4", "span": "SPAN-G2"}

GUEST_VALUES = {"Enabled": "1", "Role": "client", "RelayUrl": f"ws://127.0.0.1:{PORT}", "SessionCode": CODE,
                "FollowHost": "1", "TargetField": "0", "GuestSlots": "0", "GuestStockMenu": "1",
                "SessionGraceMs": str(GRACE_MS), "AutoTeleport": "0", "DioramaSwirlFrames": "0"}

COMMON = {
    "T2-TAPE": "the host tape reads back and this leg's cut fits it (the plan off its five facts)",
    "T2-CAL": "the CAL leg passed on THIS tape (<tape>.cal.json, sha256-keyed) -- the instrument is trusted",
    "T2-PEER": f"port {PORT} free; the guest config applied live (the engine's 'config enabled=True role=client ... "
               f"code={CODE}'); the guest dialled the replay-host ('GUEST game connected' + 'relay connected ...?role=guest') "
               "and the replay started",
    # [ff9mapkit netsync R3 T2] the exit ramp's own autosave is part of the instrument: with none, ExitMirrorToOwnSave
    # falls back to the title and every session-end check of the run reads the wrong thing
    "T2-SAVE": "the guest had its OWN autosave to end a session on: [SaveFile] AutoSaveOnlyAtMoogle off before the run, and "
               "no 'session ended, no autosave to resume -> title screen' line in it",
    "T2-INI": "Memoria.ini restored byte-exact (sha256) after the run -- the install is shared",
}

LEG_CHECKS = {
    "cal": {
        "CAL-1": "'paired on the host's field (F)' -- F the tape's field -- after the replay starts",
        "CAL-2": "'state-mirror ARMED -- this guest's fields now stage the HOST's story' after the pairing",
        "CAL-3": "'diorama BOOT scene=M' -- M the tape's battle scene -- after the mirror armed",
        "CAL-4": "'diorama LIVE ... (host battle nonce N, booted from wire nonce N)' -- N the tape's nonce",
        "CAL-5": "the end-leave: 'diorama END: end-leave attempt', 'diorama LEAVE requested', 'diorama leave noted (nonce "
                 "N)', a RETURN to F -- and NO 'watcher-leave settled (nonce N)'",
        "CAL-6": "the replay ran on time: no 'replay running ... late' line and no blackhole",
    },
    "s119": {                                                # [ff9mapkit netsync R3 s119]
        "S119-I":"the instrument before the cut: paired, ARMED, BOOT (scene M), LIVE (nonce N) logged, the diorama booted",
        "S119-G1": "no 'diorama LEAVE requested' and no 'watcher-leave settled (nonce N)' from the cut to the resume+3 s",
        "S119-G2": "exactly one 'diorama: peer silent mid-battle -- holding ... (nonce N; ... a cut; ...)' in the hold window "
                   "(and no stall-variant line)",
        "S119-G3": "one 'diorama: the host's battle lane is back on the same fight (nonce N) after a M ms hold -- resuming' in "
                   "the resume window, M by THE HOLD RULE: M - the same run's outage in [tail - 40, tail + 70] and at most "
                   "one no-lane menu close (THE CLOSE CLAUSE: inert unless a slot is Ready at the cut) (pre-s120, no "
                   "outage line: M in the nominal cut-minus-StaleMs window)",
        "S119-G4": "the reconcile resumes the SAME nonce (netsync.battle.peer live, nonce N, a seq past the last pre-cut "
                   "one) and the diorama never tore down",
        "S119-G5": "the ready mirror re-serves: 'stock menu: the ready mirror is SERVING' after the resume line",
        "S119-K": "netsync.diorama.hold: holds +1, resumes +1, gaveup +0 across the leg",
    },
    "readopt": {                                             # [ff9mapkit netsync s131] the s119 cut at a tail >= 66 ms
        "READOPT-I": "the instrument before the cut: paired, ARMED, BOOT (scene M), LIVE (nonce N) logged, the diorama "
                     "booted -- at the plan's tail >= 66 ms placement",
        "READOPT-G1": "no 'diorama LEAVE requested' and no 'watcher-leave settled (nonce N)' from the cut to the resume+3 s",
        "READOPT-G2": "exactly one 'diorama: peer silent mid-battle -- holding ... (nonce N; ... a cut; ...)' in the hold "
                      "window (and no stall-variant line)",
        "READOPT-G3": "one same-nonce resume line in the resume window, its M by THE HOLD RULE: M - the same run's outage in "
                      "[tail - 40, tail + 70] (no nominal fallback) and at most one no-lane menu close across the cut "
                      "(THE CLOSE CLAUSE: inert unless a slot is Ready at the cut)",
        "READOPT-G4": "the reconcile resumes the SAME nonce (netsync.battle.peer live, nonce N, a seq past the last pre-cut "
                      "one) and the diorama never tore down",
        "READOPT-G5": "the ready mirror re-serves: 'stock menu: the ready mirror is SERVING' after the resume line",
        "READOPT-K": "netsync.diorama.hold: holds +1, resumes +1, gaveup +0 across the leg",
        "READOPT-X": "netsync.battle.peer.expired across the cut: count +1, refused +1, frames >= 1, ms in [tail - 100, tail "
                     "+ 35]; one 'battle lane: the host's last frame (nonce N, seq S) ran out of freshness ... not "
                     "re-adopted' line (the key ABSENT = an engine that re-adopts)",
    },
    "s120-battle": {                                         # [ff9mapkit netsync R3 s120] (+ s119's hold under it)
        "S120B-I":"the instrument before the cut: paired, ARMED, BOOT (scene M), LIVE (nonce N) logged, the diorama booted",
        "S120B-G1": "no 'session ended -> reloading own autosave' from the cut through the post-victory window",
        "S120B-G2": "one 'session: the host went silent (the hop is up: ...) -- holding the session for up to G s ... (the "
                    "diorama holds); outages=K' in the outage window",
        "S120B-G3": "one 'session: the host is back after M ms -- inside the G s grace, the session continues (no exit ramp; "
                    "still mirroring)' in the resume window, M ~ the cut minus StaleMs",
        "S120B-G4": "the diorama held on the same nonce: one hold line, its resume line (nonce N), no LEAVE / watcher-leave / "
                    "give-up line between the cut and the resume; its M ms by THE HOLD RULE against G3's outage (at most "
                    "one no-lane menu close: inert unless a slot is Ready at the cut)",
        "S120B-G5": "after the recorded victory (the end-leave's RETURN): still mirrored -- session.mirroring true, "
                    "ramp_pending false, state 'live' -- and no 'session ended' line",
        "S120B-K": "netsync.session outages +1, resumes +1, gaveup +0; netsync.diorama.hold resumes +1",
    },
    "s120-long": {                                           # [ff9mapkit netsync R3 s120]
        "S120L-I":"the instrument before the cut: paired and ARMED logged, the guest on its field",
        "S120L-G1": "no 'session ended -> reloading own autosave' before the grace runs out",
        "S120L-G2": "one 'session: the host went silent ... holding the session for up to G s' in the outage window",
        "S120L-G3": "the give-up 'silent for M ms, past the G s grace -- the session ended' (M in [G, G+1.5 s]) then "
                    "'session ended -> reloading own autosave (Continue)', both at about grace + 2 s",
        "S120L-K": "netsync.session gaveup +1, outages +1, resumes +0; state 'grace' on the samples inside the grace",
    },
    "s120-roam": {                                           # [ff9mapkit netsync R3 s120]
        "S120R-I":"the instrument before the cut: paired and ARMED logged, the story marker reading the HOST's 0xA5",
        "S120R-G1": "no 'session ended' line and no ramp from the cut to the resume+8 s",
        "S120R-G2": "the reconnecting overlay: session.overlay 'reconnecting' (detail counting down) on every sample from the "
                    "ghost hold's end to the resume",
        "S120R-G3": "the outage line, then 'the host is back ... inside the G s grace, the session continues (no exit ramp; "
                    "still mirroring)'",
        "S120R-G4": "within 3 s of the resume: session.ghost true, mirroring true, ramp_pending false, state 'live'",
        "S120R-G5": "THE STORY BYTE: the marker reads 0xA5 on every sample from the cut to the resume+5 s (no own-save reload)",
    },
    "span": {                                                # [ff9mapkit netsync R3 s119] host_field / s120 stall_cap
        "SPAN-I":"the instrument before the cut: BOOT (scene M) and LIVE (nonce N) logged, the diorama booted",
        "SPAN-G1": "no 'diorama LEAVE requested' / 'watcher-leave settled' before the cut ends (held through the unseen "
                   "victory)",
        "SPAN-G2": "at the resume the over-verdict for the tape's after-battle place (host_field: 'the host's fight is over "
                   "(the peer is alive and back on field F)', its 'after a M ms hold' by THE HOLD RULE's leave-ended form "
                   "against the same run's outage, at most one no-lane menu close; stall_cap: 'still silent after 8s with "
                   "the peer alive on field 0'), then LEAVE, 'watcher-leave settled (nonce N)' and a RETURN",
        "SPAN-K": "netsync.diorama.hold.why reads the expected reason ('host_field' | 'stall_cap')",
    },
    "s121": {                                                # [ff9mapkit netsync R3 s121]
        "S121-I":"the instrument before the presses: paired and ARMED logged, the guest playable on FieldHUD",
        "S121-G0": "before the press netsync.menu_refusal.now == 'audible'",
        "S121-G1": "press 1: menu_refusal.count +1, lines +1, last_state 'FieldHUD', last_field F",
        "S121-G2": "press 1: exactly one 'main menu suppressed (following guest) on field F' line",
        "S121-G3": "press 1: ui_state stays FieldHUD for 2 s (never the main menu)",
        "S121-G4": "press 2 on the same field: count +1, lines +0, no second line",
        "S121-G5": "the control row's state: after the replay stops and the exit ramp fires, on FieldHUD with control, "
                   "menu_refusal.now == 'open'",
        "S121-C1": "the control row: Menu then OPENS the stock main menu (the press path itself is live)",
    },
}

RED_CLAIMS = {
    "s119": "CALIBRATION: the sitting-A pair reproduced -- 'diorama LEAVE requested -> FieldMap (mode 1)' and 'diorama "
            "watcher-leave settled (nonce N) -- the same fight won't re-boot on reconnect' within ~2 s of the cut",
    "s120-battle": "CALIBRATION: s117's 'session ended -> reloading own autosave (Continue)' at once (~3 s after the lanes die)",
    "s120-long": "CALIBRATION: s117's 'session ended -> reloading own autosave (Continue)' at once (~3 s after the lanes die)",
    "s120-roam": "CALIBRATION: s117's 'session ended -> reloading own autosave (Continue)' at once (~3 s after the lanes die)",
    "span": "CALIBRATION: the sitting-A pair before the cut ends (the guest left the unseen victory at once)",
    "s121": "CALIBRATION: s117's silence -- press 1 gives no refusal line and the menu stays shut",
    # [ff9mapkit netsync s131] the defect this leg exists for is s121's (not s117's): GREEN on s119-s121, red on s131
    "readopt": "CALIBRATION: the pre-s131 re-adopt reproduced -- (outage - hold) in [2000 - tail - 35, 2000 - tail + 50] ms "
               "(the hold opened at the SECOND stale edge, after the phantom 2000 ms of the re-adopted frame)",
}


def _catalog(leg: str, calibrate: bool) -> dict:
    cat = {"T2-TAPE": COMMON["T2-TAPE"]}
    if leg != "cal":
        cat["T2-CAL"] = COMMON["T2-CAL"]
    cat["T2-PEER"] = COMMON["T2-PEER"]
    cat.update(LEG_CHECKS[leg])
    if calibrate:
        if leg in RED_CLAIMS:
            cat[f"{PFX[leg]}-RED"] = RED_CLAIMS[leg]
        cat[f"{PFX[leg]}-CAL"] = ("CALIBRATION: exactly the predicted checks are red for the engine found (the docstring's "
                                  "table)")
    cat["T2-SAVE"] = COMMON["T2-SAVE"]
    cat["T2-INI"] = COMMON["T2-INI"]
    return cat


def _predicted(leg: str, stage: int, tail_ms: float | None = 0.0, why: str | None = None) -> tuple:
    """(reds, maybe) for ``leg`` on the engine found (its guest stage), at a cut of ``tail_ms`` (the plan's; None = no
    battle lane at the cut, read as 0). The docstring's table: the default is its tail-0 row. [ff9mapkit netsync s131 fix]
    ``why`` = the plan's expected over-verdict (expect.why): a span's "stall_cap" judges no hold ms (THE TAIL ADDS' one
    exception), None/"host_field" the hold rule's leave-ended form."""
    p = PFX[leg]
    red = {f"{p}-RED"}
    ids = list(LEG_CHECKS[leg])
    gk = {c for c in ids if c.split("-")[1][:1] in ("G", "K")}
    if leg == "cal":
        return set(), set()
    if leg == "s121":
        return (red, set()) if stage >= 121 else ({f"{p}-G0", f"{p}-G1", f"{p}-G2", f"{p}-G4", f"{p}-G5"}, set())
    if leg == "readopt":                                    # [ff9mapkit netsync s131] its tail is >= 66 by construction
        if stage >= 131:
            return red, set()
        if stage >= 120:
            return {f"{p}-G3", f"{p}-X"}, {f"{p}-G2"}
        if stage == 119:
            return {f"{p}-G3", f"{p}-X", f"{p}-RED"}, {f"{p}-G2"}
        return gk | {f"{p}-X", f"{p}-RED"}, set()
    if leg == "s119":
        reds, maybe = (set(red), set()) if stage >= 119 else (set(gk), set())
    elif stage >= 120:
        reds, maybe = set(red), set()
    elif stage == 119 and leg in ("s120-battle", "span"):
        reds, maybe = set(gk), set(red)
    else:
        reds, maybe = set(gk), set()
    # [ff9mapkit netsync s131] THE TAIL ADDS: a pre-s131 guest re-adopts the frozen frame on a tail > 0 cut, so the hold
    # check reads ~(2000 - tail) ms off its rule -- on s120/s121 (the outage line exists), and on s119 for the s119 leg
    # (its nominal window); s131 never
    hc, tail = HOLD_CHECK.get(leg), float(tail_ms or 0.0)
    if hc and hc not in reds and tail > 0.0 and (120 <= stage < 131 or (stage == 119 and leg == "s119")):
        # [ff9mapkit netsync s131 fix] a stall_cap span (s120-world) has no hold ms to break, and its verdict lands at the
        # resume + the settle on either engine (DioramaWatchStep: its stale age is past the 8 s cap long before): only the
        # second no-lane close reads the re-adopt there, and that one needs a slot Ready at the cut (MirrorStandDown's
        # `held`) -- the tape's, not the tail's: a maybe at ANY tail, never a predicted red
        stall = leg == "span" and why == "stall_cap"
        (reds if tail >= pb.READOPT_TAIL_MS and not stall else maybe).add(hc)
    return reds, maybe


class _Ctx:
    def __init__(self):
        self.tape = None
        self.facts = None
        self.plan = None
        self.field = pb.BENCH_FIELD
        self.scene = None
        self.nonce = None
        self.stage = 0
        self.guard = None
        self.peer = None
        self.eng = None
        self.samples: list = []
        self.marker_own = None
        self.anchors: dict = {}


def _run_dir(g) -> Path:
    return Path(getattr(g, "scenario_dir", None) or g.run_dir)


def run(g, field: int | None = None):
    leg = LEG or "cal"
    led = cb.Ledger(g, _catalog(leg, CALIBRATE), finals=("T2-SAVE", "T2-INI", f"{PFX[leg]}-CAL"))
    ctx = _Ctx()
    try:
        if LEG is None:
            led.check("T2-TAPE", False, f"COOP_CUT_LEG={_RAW_LEG!r} is no leg: one of {pb.LEGS} (or s120-world)")
            led.close("not reached: no such leg")
            return
        if field is not None:
            g.note(f"--field {field} is ignored: the leg runs on the tape's own field")
        _run(g, led, ctx, leg)
    except HarnessError as err:
        g.note(f"the leg raised: {str(err)[:400]}")
        led.close(f"not reached: the leg raised ({str(err)[:200]})")
    finally:
        _teardown(g, led, ctx)
        if CALIBRATE and LEG is not None:
            ctx.stage = max(ctx.stage, _stage_now(g))       # the keys never vanish: the later read can only add one
            tail = (ctx.plan or {}).get("tail_ms")          # [ff9mapkit netsync s131] the table is the tail's
            why = ((ctx.plan or {}).get("expect") or {}).get("why")    # [ff9mapkit netsync s131 fix] span: the verdict
            reds, maybe = _predicted(leg, ctx.stage, tail, why)
            if HOLD_CHECK.get(leg):
                g.note(f"{PFX[leg]}-CAL: this cut's tail {tail} ms " + (
                       "(a stall_cap span: no hold rule -- a pre-s131 engine reads SPAN-G2 a maybe at any tail > 0, red "
                       "only with a slot Ready at the cut)" if leg == "span" and why == "stall_cap" else
                       f"(THE HOLD RULE: a pre-s131 engine reads {HOLD_CHECK[leg]} red at >= {pb.READOPT_TAIL_MS:g}, maybe "
                       "below, green at 0)"))
            if FORCE and leg != "cal" and led.done.get("T2-CAL") is False:
                # [ff9mapkit netsync R3 T2] COOP_CUT_FORCE=1 ran past an untrusted instrument BY DESIGN (a world-map tape
                # has no field for the CAL leg to pair on): its T2-CAL red is the force, not a finding -- this verdict
                # judges the leg's own checks, and the instrument's trust is the owner's call for this run
                maybe = set(maybe) | {"T2-CAL"}
                g.note(f"{PFX[leg]}-CAL: COOP_CUT_FORCE=1 -- T2-CAL's red is allowed; the instrument verdict is manual")
            g.note(f"{PFX[leg]}-CAL: the engine reads as s{ctx.stage or '<117'}; predicted reds {sorted(reds)}; "
                   f"maybe {sorted(maybe)}")
            led.close("not reached: the leg ended before this check")
            led.judge_calibration(f"{PFX[leg]}-CAL", reds, maybe)
        led.close(final=True)


def _stage_now(g) -> int:
    try:
        return pb.engine_stage(g.state)
    except HarnessError:
        return 0


def _teardown(g, led: cb.Ledger, ctx: _Ctx) -> None:
    """The peer first (a restored owner config must not find a bench peer on its port), then the ini, then the logs."""
    if ctx.peer is not None and ctx.peer.how_ended is None:
        g.note(f"coop_peer replay-host: {ctx.peer.stop()}")
    if "T2-SAVE" not in led.done:
        fell = pb.hits(ctx.eng.lines(), "ramp_failed") if ctx.eng is not None else []
        led.check("T2-SAVE", not fell,
                  f"the exit ramp fell back to the TITLE: {pb.show(fell, 1)} -- the guest had no own autosave to resume, "
                  "so every session-end check of this run read the instrument, not the engine" if fell else
                  "no title fallback" + ("" if ctx.eng is not None else " (the guest never ran a session)"))
    if ctx.guard is not None:
        ok, why = ctx.guard.restore()
        led.check("T2-INI", ok, why)
    else:
        led.check("T2-INI", True, "Memoria.ini was never edited (the leg stopped before the edit)")
    g.note(f"Memoria.log archived: {cb.archive_log(g, f'coop-cut-{LEG or _RAW_LEG}')}")


# ================================================================================================ the run
def _run(g, led: cb.Ledger, ctx: _Ctx, leg: str) -> None:
    p = PFX[leg]
    leg_ids = [c for c in led.catalog if c.startswith(p + "-") and c != f"{p}-CAL"]
    # A. the tape, its facts, this leg's plan -- before any game action
    ctx.tape = pb.latest_tape()
    if ctx.tape is None or not ctx.tape.exists():
        led.check("T2-TAPE", False, f"no tape ({ctx.tape or pb.tape_dir()}): record one first -- py tools/play.py "
                                    "studies/test-harness/scenarios/coop_tape_record.py")
        led.close("not reached: no tape")
        return
    try:
        cp = pb.coop_peer_module()
        _header, records, torn = cp.read_tape(ctx.tape)
    except Exception as err:                 # noqa: BLE001 -- the reason is the check's detail
        led.check("T2-TAPE", False, f"{ctx.tape} does not read back: {err}")
        led.close("not reached: the tape does not read back")
        return
    ctx.facts = pb.tape_facts(records, cp, field=None)
    ctx.plan = pb.plan_leg(leg, ctx.facts, GRACE_S, world=WORLD)
    f1, f3 = ctx.facts["f1"], ctx.facts["f3"]
    ctx.field = f1.get("field") or pb.BENCH_FIELD
    ctx.scene, ctx.nonce = f3.get("map"), f3.get("nonce")
    tail = ctx.plan.get("tail_ms")                  # [ff9mapkit netsync s131] the cut's tail (THE HOLD RULE reads it)
    cut = (f"cut at tape {ctx.plan['bh'][0]:.3f} s for {ctx.plan['bh'][1]:g} s"
           + (f", tail {tail:.1f} ms" if tail is not None else "") if ctx.plan.get("bh") else
           f"stop at tape {ctx.plan['stop_at']:.2f} s" if ctx.plan.get("stop_at") is not None else "no cut")
    if ctx.plan.get("expect", {}).get("placement"):
        g.note(f"readopt placement: {ctx.plan['expect']['placement']}")
    torn_text = f", torn tail {torn} B" if torn else ""
    led.check("T2-TAPE", ctx.plan["ok"], f"{ctx.tape.name} ({len(records)} records{torn_text}): field {ctx.field}, scene "
              f"{ctx.scene}, nonce {ctx.nonce}; {leg}: " + (cut if ctx.plan["ok"] else "CANNOT -- " + ctx.plan["why"]))
    for line in pb.facts_lines(ctx.facts):
        g.note("  " + line)
    if not ctx.plan["ok"]:
        led.close(f"not reached: this tape cannot carry the {leg} leg ({ctx.plan['why'][:200]})")
        return
    if leg != "cal":
        okc, whyc = pb.read_cal(ctx.tape)
        led.check("T2-CAL", okc, whyc + (" -- COOP_CUT_FORCE=1: running anyway" if not okc and FORCE else ""))
        if not okc and not FORCE:
            led.close(f"not reached: the instrument is untrustworthy -- {whyc[:200]}")
            return
    # B. the guest's own game on the tape's field
    free, why = pb.port_free(PORT)
    if not free:
        led.check("T2-PEER", False, why)
        led.close("not reached: the bench port is taken (nothing was edited)")
        return
    # [ff9mapkit netsync R3 T2] the exit ramp needs the guest's OWN autosave of the tape's field: refuse up front when the
    # install cannot write one there (read-only: the guard below edits [Netsync] alone)
    try:
        moogle_only = pb.ini_autosave_moogle_only((Path(g.game_path) / "Memoria.ini").read_text(encoding="utf-8",
                                                                                                errors="replace"))
    except OSError as err:
        moogle_only = False
        g.note(f"Memoria.ini unreadable for the autosave pre-check ({err}) -- T2-SAVE judges the run's lines alone")
    if moogle_only:
        led.check("T2-SAVE", False, f"[SaveFile] AutoSaveOnlyAtMoogle = 1: field {ctx.field} has no save point, so the "
                                    "guest gets no own autosave there and its exit ramp would fall back to the title (or an "
                                    "older autosave elsewhere) -- set it to 0 for the bench (nothing was edited)")
        led.close("the guest can have no own autosave on the bench field (T2-SAVE)")
        return
    cb.provenance(g)
    g.note(f"R3 T2 cut-hold leg {leg} ({p}): {cut}; grace {GRACE_S:g} s"
           + (f" (COOP_GRACE_MS: {GRACE_NOTE})" if GRACE_NOTE else "") + f"; the guest on field {ctx.field}")
    g.newgame()
    if g.state.field_id != ctx.field:
        g.warp(ctx.field)
    try:
        g.no_encounters(True)
    except HarnessError as err:
        g.note(f"noencounter refused ({str(err)[:160]})")
    g.watch(*(pb.MARKER_BYTE * 8 + b for b in range(8)))
    g.wait_frames(45)                          # the field entry's autosave lands: the exit ramp's own "Continue"
    st = g.state
    ctx.stage = pb.engine_stage(st)
    ctx.marker_own = pb.marker_value(st)
    g.note(f"the guest engine reads as s{ctx.stage or '<117'}; {cb.stage_note(st)}; the guest's own story marker reads "
           f"{ctx.marker_own!r}")
    # C. the ini, then the engine's own config line
    ctx.eng = pb.EngineLog(g.engine_log())
    ctx.guard = pb.IniGuard(Path(g.game_path) / "Memoria.ini", GUEST_VALUES, label=f"coop-cut-{leg}", run_dir=_run_dir(g))
    try:
        g.note(ctx.guard.apply())
    except (OSError, RuntimeError) as err:
        led.check("T2-PEER", False, f"the Memoria.ini edit failed: {err}")
        led.close("not reached: Memoria.ini could not be edited")
        return
    cfg = _wait_config(g, ctx)
    if not cfg:
        led.check("T2-PEER", False, f"the engine never logged the guest config (config lines seen: "
                                    f"{pb.show(pb.hits(ctx.eng.lines(), 'config'))}) -- is this the Memoria.ini it reads?")
        led.close("not reached: the guest config never applied")
        return
    # D. the replay-host
    rd = _run_dir(g)
    ctx.peer = pb.PeerProc("replay-host", [ctx.tape, *pb.plan_args(ctx.plan, port=PORT, code=CODE)],
                           log_path=rd / f"coop_peer-replay-{leg}.log", out_path=rd / f"coop_peer-replay-{leg}.out")
    g.note(f"starting: {ctx.peer.command_text()}")
    ctx.peer.start()
    up = ctx.peer.wait_for(pb.PEER["listening"], 15.0, tick=lambda: _sample(g, ctx))
    conn = ctx.peer.wait_for(pb.PEER["guest_connected"], 25.0, tick=lambda: _sample(g, ctx)) if up else None
    start = ctx.peer.wait_for(pb.PEER["replay_start"], 10.0, tick=lambda: _sample(g, ctx)) if conn else None
    relay = pb.hits(ctx.eng.lines(), "relay_up", pred=lambda m: m.group(3) == "guest" and m.group(2) == CODE)
    ok = up is not None and conn is not None and start is not None and bool(relay)
    led.check("T2-PEER", ok, f"config: {pb.show(cfg, 1)}; peer: {up[1] if up else 'never listened'} / "
                             f"{conn[1] if conn else 'no guest'} / {start[1] if start else 'no replay start'}; engine: "
                             f"{pb.show(relay, 1)}; SessionGraceMs written {GRACE_MS}"
                             + (f" (COOP_GRACE_MS: {GRACE_NOTE})" if GRACE_NOTE else "") + f"; peer tail: {ctx.peer.tail(3)}")
    if not ok:
        led.unreached(leg_ids, "the instrument never started (T2-PEER)")
        return
    ctx.anchors["start"] = start[0]
    # E. the leg
    {"cal": _leg_cal, "s119": _leg_s119, "readopt": _leg_readopt, "s120-battle": _leg_s120_battle,
     "s120-long": _leg_s120_long, "s120-roam": _leg_s120_roam, "span": _leg_span, "s121": _leg_s121}[leg](g, led, ctx)


def _wait_config(g, ctx: _Ctx, first: float = 6.0, second: float = 10.0) -> list:
    """The engine's config line for the bench guest. A running NetSyncClient polls Memoria.ini every 2 s; with none yet
    (the owner's Enabled=0), only a field load's Ensure() reads it -- so one same-field warp, then wait."""
    def found():
        return pb.hits(ctx.eng.lines(), "config", pred=lambda m: m.group(1) == "True" and m.group(2) == "client"
                       and m.group(5) == f"ws://127.0.0.1:{PORT}" and m.group(6) == CODE)
    deadline = time.time() + first
    while time.time() < deadline:
        if found():
            return found()
        time.sleep(0.25)
    g.note("no config line within the poll window -- reloading the field (Ensure reads the ini at a field load)")
    try:
        g.warp(ctx.field)
    except HarnessError as err:
        g.note(f"the reload warp failed: {str(err)[:200]}")
    deadline = time.time() + second
    while time.time() < deadline:
        if found():
            return found()
        time.sleep(0.25)
    return []


# ================================================================================================ sampling
def _sample(g, ctx: _Ctx) -> dict:
    st = g.state
    s = {"t": _dt.datetime.now(), "frame": st.frame, "ui": st.ui_state, "field": st.field_id, "control": st.control,
         "dialog": st.dialog_open, "fading": st.fading, "booted": pb.path(st, "netsync.diorama.booted"),
         "peer": pb.path(st, "netsync.battle.peer"), "hold": pb.path(st, "netsync.diorama.hold"),
         "session": pb.path(st, "netsync.session"), "menu": pb.path(st, "netsync.menu_refusal"),
         "marker": pb.marker_value(st)}
    ctx.samples.append(s)
    return s


def _pump(g, ctx: _Ctx) -> dict:
    s = _sample(g, ctx)
    ctx.eng.lines()
    for key in ("bh_begin", "bh_end", "stop_at", "replay_done"):
        if key not in ctx.anchors:
            hit = ctx.peer.first(pb.PEER[key])
            if hit is not None:
                ctx.anchors[key] = hit[0]
    return s


def _until(g, ctx: _Ctx, cond, timeout: float) -> bool:
    """Sample at POLL_S until ``cond()`` holds (True) or ``timeout`` runs out (False)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        _pump(g, ctx)
        try:
            if cond():
                return True
        except (TypeError, KeyError, AttributeError, IndexError, ValueError):
            pass
        time.sleep(POLL_S)
    _pump(g, ctx)
    return False


def _after(ctx: _Ctx, key: str, seconds: float) -> bool:
    a = ctx.anchors.get(key)
    return a is not None and _dt.datetime.now() >= a + _dt.timedelta(seconds=seconds)


def _between(ctx: _Ctx, lo, hi) -> list:
    return [s for s in ctx.samples if lo <= s["t"] <= hi]


def _before(ctx: _Ctx, t) -> dict | None:
    prior = [s for s in ctx.samples if s["t"] < t]
    return prior[-1] if prior else None


def _delta(a: dict | None, b: dict | None, key: str):
    """b[key] - a[key] of two published blocks; None when either block (or key) is absent -- never a zero."""
    if not isinstance(a, dict) or not isinstance(b, dict) or key not in a or key not in b:
        return None
    try:
        return int(b[key]) - int(a[key])
    except (TypeError, ValueError):
        return None


def _span_s(ctx: _Ctx) -> float:
    f = ctx.facts
    return float((f.get("end") or 0.0) - (f.get("start") or 0.0))


def _instrument(ctx: _Ctx, cut, need=("paired", "armed", "boot", "live"), *, booted: bool = False,
                what: str = "the cut") -> tuple:
    """(ok, detail): the CAL facts this leg needs, logged after the replay started and BEFORE ``cut`` -- with them missing
    the leg's verdict would be the instrument's, so its checks read "not reached"."""
    e = ctx.eng.lines()
    start = ctx.anchors.get("start")
    preds = {"paired": lambda m: int(m.group(1)) == ctx.field, "armed": None,
             "boot": lambda m: ctx.scene is None or int(m.group(1)) == ctx.scene,
             "live": lambda m: ctx.nonce is None or int(m.group(2)) == ctx.nonce}
    have, missing = [], []
    for name in need:
        found = pb.hits(e, name, after=start, before=cut, pred=preds[name])
        (have if found else missing).append(name)
    if booted:
        last = _before(ctx, cut) if cut is not None else None
        if not (last and last.get("booted")):
            missing.append("the diorama booted at the cut")
    detail = (f"before {what}: {', '.join(have) or 'nothing'}" + (f"; MISSING {missing}" if missing else "")
              + f" (field {ctx.field}, scene {ctx.scene}, nonce {ctx.nonce})")
    return not missing, detail


def _gate(led: cb.Ledger, ctx: _Ctx, p: str, ok: bool, detail: str) -> bool:
    led.check(f"{p}-I", ok, detail)
    if not ok:
        led.unreached([c for c in led.catalog if c.startswith(p + "-") and c not in (f"{p}-I", f"{p}-CAL")],
                      f"the instrument is untrustworthy on this run -- {detail[:200]}")
    return ok


def _cut_anchors(g, ctx: _Ctx, *, timeout: float) -> tuple:
    """Wait for the replay's BLACKHOLE edges; (begin, end, bh_for) -- begin/end None when the replay never got there."""
    _until(g, ctx, lambda: "bh_end" in ctx.anchors, timeout)
    return ctx.anchors.get("bh_begin"), ctx.anchors.get("bh_end"), ctx.plan["bh"][1]


def _t(a, s: float):
    return a + _dt.timedelta(seconds=s)


# ================================================================================================ the legs
def _leg_cal(g, led: cb.Ledger, ctx: _Ctx) -> None:
    start = ctx.anchors["start"]

    def returned():
        e = ctx.eng.lines()
        el = pb.hits(e, "end_leave", after=start)
        return bool(el) and bool(pb.hits(e, "return", after=el[0][0]))

    _until(g, ctx, returned, _span_s(ctx) + 120.0)
    _until(g, ctx, lambda: False, 3.0)
    e = ctx.eng.lines()
    F, M, N = ctx.field, ctx.scene, ctx.nonce
    paired = pb.hits(e, "paired", after=start, pred=lambda m: int(m.group(1)) == F)
    led.check("CAL-1", bool(paired), pb.show(paired) if paired else
              f"no 'paired on the host's field ({F})' line; other pairings: {pb.show(pb.hits(e, 'paired', after=start))}")
    armed = pb.hits(e, "armed", after=paired[0][0]) if paired else []
    led.check("CAL-2", bool(armed), pb.show(armed) if armed else "no 'state-mirror ARMED' after the pairing")
    boots = pb.hits(e, "boot", after=armed[0][0] if armed else start, pred=lambda m: int(m.group(1)) == M)
    led.check("CAL-3", bool(boots), pb.show(boots, 1) if boots else
              f"no 'diorama BOOT scene={M}'; boots seen: {pb.show(pb.hits(e, 'boot', after=start))}")
    lives = pb.hits(e, "live", after=boots[0][0] if boots else start,
                    pred=lambda m: int(m.group(2)) == N and (m.group(3) is None or int(m.group(3)) == N))
    led.check("CAL-4", bool(lives), pb.show(lives, 1) if lives else
              f"no 'diorama LIVE ... nonce {N}'; LIVE lines: {pb.show(pb.hits(e, 'live', after=start))}")
    el = pb.hits(e, "end_leave", after=lives[0][0] if lives else start)
    lv = pb.hits(e, "leave", after=el[0][0]) if el else []
    noted = pb.hits(e, "leave_noted", after=el[0][0], pred=lambda m: int(m.group(1)) == N) if el else []
    ret = pb.hits(e, "return", after=el[0][0], pred=lambda m: int(m.group(2)) == F) if el else []
    ws = pb.hits(e, "watcher_settled", after=start)
    led.check("CAL-5", bool(el and lv and noted and ret) and not ws,
              f"end-leave {pb.show(el, 1)}; LEAVE {pb.show(lv, 1)}; noted {pb.show(noted, 1)}; RETURN {pb.show(ret, 1)}; "
              f"watcher-leave {pb.show(ws, 1)}")
    lag = ctx.peer.find(pb.PEER["lag"])
    bh = ctx.peer.find(pb.PEER["bh_begin"])
    led.check("CAL-6", not lag and not bh, f"lag lines: {[m for _, m, _ in lag] or 'none'}; blackholes: {len(bh)}")
    names = ("T2-TAPE", "T2-PEER", "CAL-1", "CAL-2", "CAL-3", "CAL-4", "CAL-5", "CAL-6")
    ok = all(led.done.get(c) for c in names)
    bad = [c for c in names if not led.done.get(c)]
    try:
        side = pb.write_cal(ctx.tape, ok, stage=ctx.stage, facts=ctx.facts,
                            detail="all six CAL facts" if ok else f"red: {bad}")
        g.note(f"CAL verdict {'OK' if ok else 'FAILED ' + str(bad)} written: {side}")
    except OSError as err:
        g.note(f"the CAL verdict could not be written: {err}")


def _outage(lines, a, e):
    """[ff9mapkit netsync s131] (the SAME run's outage ms | None, its lines): the ONE 'session: the host is back after M
    ms' of this cut (s120+; none on an older engine -- never a zero)."""
    backs = pb.hits(lines, "session_back", after=a, before=_t(e, 4.0))
    return (int(backs[0][2].group(1)) if len(backs) == 1 else None), backs


def _hold_rule(ctx: _Ctx, lines, held, om, a, until, *, leave: bool = False) -> tuple:
    """[ff9mapkit netsync s131] THE HOLD RULE for one cut -> (ok, detail): the engine's hold ``held`` against the same
    run's outage ``om`` plus the plan's tail (_coop_peer_bench.hold_rule; ``leave`` = a leave-ended hold), and at most
    MENU_CLOSES_MAX 'closed all (ready mirror: no live peer battle lane)' lines in [a, until] -- THE CLOSE CLAUSE, which
    can only fail when the ready mirror held a slot at the cut (the docstring's paragraph: inert mid-fight on the
    2026-10-14 tape, calibrated by span and P5's K4) [ff9mapkit netsync s131 fix]."""
    tail = ctx.plan.get("tail_ms")
    closes = pb.hits(lines, "menu_close_nolane", after=a, before=until)
    ok = pb.hold_rule(held, om, tail, leave=leave)[0] and len(closes) <= pb.MENU_CLOSES_MAX
    eng = ("s131 (netsync.battle.peer.expired published)" if ctx.stage >= 131 else
           f"pre-s131 (s{ctx.stage or '<117'})" + ("" if ok or not tail else ": a tail > 0 cut re-adopts the frozen "
                                                    "frame -- this red is that defect (predicted: _predicted's tail)"))
    return ok, (f"{pb.hold_rule_text(held, om, tail, leave=leave)}; no-lane menu closes across the cut {len(closes)} (want "
                f"<= {pb.MENU_CLOSES_MAX})" + (f": {pb.show(closes)}" if len(closes) > pb.MENU_CLOSES_MAX else "")
                + f"; engine {eng}")


def _leg_s119(g, led: cb.Ledger, ctx: _Ctx) -> None:
    _leg_mid_cut(g, led, ctx, "s119")


def _leg_readopt(g, led: cb.Ledger, ctx: _Ctx) -> None:
    """[ff9mapkit netsync s131] the s119 cut at the plan's tail >= 66 ms placement: s119's checks, G3 by THE HOLD RULE
    with no nominal fallback, X the s131 key, READOPT-RED the pre-s131 re-adopt reproduced."""
    _leg_mid_cut(g, led, ctx, "readopt")


def _last_until(ctx: _Ctx, t) -> dict | None:
    upto = [s for s in ctx.samples if s["t"] <= t]
    return upto[-1] if upto else None


def _expired(sample: dict | None):
    """[ff9mapkit netsync s131] a sample's netsync.battle.peer.expired block -- None when ABSENT (pre-s131), never {}."""
    peer = sample.get("peer") if isinstance(sample, dict) else None
    x = peer.get("expired") if isinstance(peer, dict) else None
    return x if isinstance(x, dict) else None


def _leg_mid_cut(g, led: cb.Ledger, ctx: _Ctx, leg: str) -> None:
    """A 6 s cut mid-battle (s119: at battle+10; readopt: moved to the nearest tail >= 66 placement)."""
    p, N = PFX[leg], ctx.nonce
    a, e, dur = _cut_anchors(g, ctx, timeout=_span_s(ctx) + 60.0)
    if a is None or e is None:
        led.unreached(list(LEG_CHECKS[leg]), f"the replay never reached its blackhole edges ({ctx.peer.tail(3)})")
        return
    _until(g, ctx, lambda: _after(ctx, "bh_end", 12.0), 30.0)
    if not _gate(led, ctx, p, *_instrument(ctx, a, booted=True)):
        return
    ctx.stage = max(ctx.stage, _stage_now(g))
    W = pb.leg_windows(dur, GRACE_S)
    lines = ctx.eng.lines()
    res = pb.hits(lines, "hold_resume", after=a, pred=lambda m: int(m.group(1)) == N)
    t_end = (res[0][0] if res else e) + _dt.timedelta(seconds=3)
    leaves = pb.hits(lines, "leave", after=a, before=t_end)
    settled = pb.hits(lines, "watcher_settled", after=a, before=t_end)
    led.check(f"{p}-G1", not leaves and not settled, f"LEAVE {pb.show(leaves)}; watcher-leave {pb.show(settled)}")
    holds = pb.hits(lines, "hold_cut", after=a, before=_t(e, 2.0), pred=lambda m: int(m.group(1)) == N)
    stalls = pb.hits(lines, "hold_stall", after=a, before=_t(e, 2.0))
    inwin = [h for h in holds if pb.in_window(h[0], a, *W["hold"])]
    led.check(f"{p}-G2", len(holds) == 1 and len(inwin) == 1 and not stalls,
              f"cut holds {pb.show(holds)} (in window {len(inwin)}); stall holds {pb.show(stalls)}")
    held = int(res[0][2].group(2)) if res else None
    om, backs = _outage(lines, a, e)
    in_resume = len(res) == 1 and pb.in_window(res[0][0], a, *W["resume"])
    where = f"{pb.show(res, 1)} (within {W['resume'][0]:g}..{W['resume'][1]:g} s of the cut: {in_resume})"
    if leg == "s119" and ctx.stage < 120:
        # [ff9mapkit netsync s131] an engine with no session lines (pre-s120) has no outage to judge against: the s119-
        # alone engine keeps the nominal window (a ~2 s-late re-adopted hold falls under it all the same)
        closes = pb.hits(lines, "menu_close_nolane", after=a, before=t_end)
        nominal = held is not None and W["held_ms"][0] <= held <= W["held_ms"][1]
        led.check(f"{p}-G3", in_resume and nominal and len(closes) <= pb.MENU_CLOSES_MAX,
                  f"{where}; pre-s120 (no outage line): expected {W['held_ms'][0]:.0f}-{W['held_ms'][1]:.0f} ms; no-lane "
                  f"menu closes {len(closes)} (want <= {pb.MENU_CLOSES_MAX})")
    else:
        ok3, why3 = _hold_rule(ctx, lines, held, om, a, t_end)
        led.check(f"{p}-G3", in_resume and ok3, f"{where}; outage {pb.show(backs, 1)}; {why3}")
    pre = [s for s in ctx.samples if s["t"] < a and isinstance(s["peer"], dict) and s["peer"].get("nonce") == N]
    seq0 = pre[-1]["peer"].get("seq") if pre else None
    post = _between(ctx, e, _t(e, 4.0))
    moved = [s for s in post if isinstance(s["peer"], dict) and s["peer"].get("live") and s["peer"].get("nonce") == N
             and s["peer"].get("seq") != seq0]
    through = _between(ctx, a, _t(e, 3.0))
    torn = [s for s in through if not s.get("booted")]
    led.check(f"{p}-G4", seq0 is not None and bool(moved) and through and not torn,
              f"pre-cut seq {seq0}; post-resume live samples on nonce {N} with a new seq: {len(moved)}"
              + (f" (seq {moved[0]['peer'].get('seq')})" if moved else "") + f"; samples across the cut {len(through)}, "
              f"booted false on {len(torn)}")
    serving = pb.hits(lines, "serving", after=res[0][0]) if res else []
    led.check(f"{p}-G5", bool(res) and bool(serving), f"SERVING after the resume: {pb.show(serving, 1)}")
    h0 = (_before(ctx, a) or {}).get("hold")
    h1 = ctx.samples[-1].get("hold") if ctx.samples else None
    dh, dr, dg = _delta(h0, h1, "holds"), _delta(h0, h1, "resumes"), _delta(h0, h1, "gaveup")
    led.check(f"{p}-K", (dh, dr, dg) == (1, 1, 0),
              f"netsync.diorama.hold {'ABSENT (pre-s119)' if h1 is None else ''} deltas holds {dh}, resumes {dr}, "
              f"gaveup {dg}; why {None if h1 is None else h1.get('why')!r}")
    if leg == "readopt":
        _readopt_x(led, ctx, lines, a, e, t_end)
    if CALIBRATE:
        if leg == "readopt":
            tail = ctx.plan.get("tail_ms")
            ok, d, win = pb.readopt_reproduced(held, om, tail)
            led.check(f"{p}-RED", ok, f"outage {om} - hold {held} = {d} ms against tail {tail} ms: the pre-s131 re-adopt "
                                      f"reads {win[0]:.0f}..{win[1]:.0f}" if win else
                                      f"outage {om}, hold {held}, tail {tail}: a figure is missing (no session line: "
                                      "pre-s120; no resume line; or no battle lane at the cut)")
        else:
            _red_pair(led, ctx, p, a, W, before=_t(a, W["red_leave"][1] + 1.0))


def _readopt_x(led: cb.Ledger, ctx: _Ctx, lines, a, e, t_end) -> None:
    """[ff9mapkit netsync s131] READOPT-X: the s131 key across the cut -- ONE run-out (count +1), ONE refused re-adopt
    episode (refused +1, frames >= 1) whose span (ms) is the tail less up to two Updates, and its one episode line on
    the battle's nonce. The key ABSENT (s121 and older) reads None, never a pass."""
    N, tail = ctx.nonce, ctx.plan.get("tail_ms")
    x0, x1 = _expired(_before(ctx, a)), _expired(_last_until(ctx, _t(e, 4.0)))
    dc, dr, df = _delta(x0, x1, "count"), _delta(x0, x1, "refused"), _delta(x0, x1, "frames")
    ms = x1.get("ms") if x1 is not None else None
    lo = (tail - pb.EXPIRED_MS_SLACK[0]) if tail is not None else None
    hi = (tail + pb.EXPIRED_MS_SLACK[1]) if tail is not None else None
    ms_ok = isinstance(ms, int) and ms >= 0 and lo is not None and lo <= ms <= hi
    eps = pb.hits(lines, "readopt_refused", after=a, before=t_end, pred=lambda m: int(m.group(1)) == N)
    led.check("READOPT-X", (dc, dr) == (1, 1) and df is not None and df >= 1 and ms_ok and len(eps) == 1,
              f"netsync.battle.peer.expired {'ABSENT (pre-s131: the guest re-adopts) ' if x1 is None else ''}deltas "
              f"count {dc}, refused {dr}, frames {df}; ms {ms} (want "
              + (f"{lo:.0f}..{hi:.0f}" if lo is not None else "?") + f": the tail {tail} ms less up to two Updates); "
              f"episode lines on nonce {N}: {len(eps)} ({pb.show(eps, 1)})")


def _red_pair(led: cb.Ledger, ctx: _Ctx, p: str, a, W, *, before) -> None:
    lines = ctx.eng.lines()
    lv = [h for h in pb.hits(lines, "leave", after=a, before=before) if pb.in_window(h[0], a, *W["red_leave"])]
    ws = [h for h in pb.hits(lines, "watcher_settled", after=a, before=before,
                              pred=lambda m: int(m.group(1)) == ctx.nonce) if pb.in_window(h[0], a, *W["red_leave"])]
    exact = (lv and lv[0][1] == "[NetSync] diorama LEAVE requested -> FieldMap (mode 1)" and ws and ws[0][1] ==
             f"[NetSync] diorama watcher-leave settled (nonce {ctx.nonce}) -- the same fight won't re-boot on reconnect")
    led.check(f"{p}-RED", bool(exact), f"LEAVE {pb.show(lv, 1)}; watcher-leave {pb.show(ws, 1)} (window "
                                       f"{W['red_leave'][0]:g}..{W['red_leave'][1]:g} s after the cut)")


def _red_ramp(led: cb.Ledger, ctx: _Ctx, p: str, a, W) -> None:
    # (either exit-ramp line: the reload or its title fallback -- the session ENDED at once; T2-SAVE names the fallback)
    ramps = [h for h in pb.session_ends(ctx.eng.lines(), after=a) if pb.in_window(h[0], a, *W["old_ramp"])]
    led.check(f"{p}-RED", bool(ramps), f"{pb.show(ramps, 1)} (window {W['old_ramp'][0]:g}..{W['old_ramp'][1]:g} s after "
                                       "the cut)")


def _leg_s120_battle(g, led: cb.Ledger, ctx: _Ctx) -> None:
    p, N, F = "S120B", ctx.nonce, ctx.field
    a, e, dur = _cut_anchors(g, ctx, timeout=_span_s(ctx) + 60.0)
    if a is None or e is None:
        led.unreached(list(LEG_CHECKS["s120-battle"]), f"the replay never reached its blackhole edges ({ctx.peer.tail(3)})")
        return

    def returned():
        r = pb.hits(ctx.eng.lines(), "return", after=e)
        return bool(r)

    got_return = _until(g, ctx, returned, max(10.0, (ctx.facts.get("end") or 0) - ctx.plan["bh"][0]) + 30.0)
    r_t = pb.hits(ctx.eng.lines(), "return", after=e)
    t_ret = r_t[0][0] if r_t else None
    if t_ret is not None:
        _until(g, ctx, lambda: _dt.datetime.now() >= _t(t_ret, 6.0), 10.0)
    if not _gate(led, ctx, p, *_instrument(ctx, a, booted=True)):
        return
    W = pb.leg_windows(dur, GRACE_S)
    lines = ctx.eng.lines()
    end_g1 = _t(t_ret, 6.0) if t_ret else _dt.datetime.now()
    ramps = pb.session_ends(lines, after=a, before=end_g1)        # the reload OR its title fallback (T2-SAVE)
    led.check("S120B-G1", not ramps, f"'session ended' lines from the cut to the post-victory window: {pb.show(ramps)}")
    outs = pb.hits(lines, "session_out", after=a, before=e)
    out_ok = (len(outs) == 1 and pb.in_window(outs[0][0], a, *W["out"]) and outs[0][2].group(1).startswith("the hop is up")
              and int(outs[0][2].group(2)) == int(GRACE_S) and "(the diorama holds)" in outs[0][2].group(3))
    led.check("S120B-G2", out_ok, f"{pb.show(outs)} (window {W['out'][0]:g}..{W['out'][1]:g} s)")
    om, backs = _outage(lines, a, e)
    back_ok = (len(backs) == 1 and pb.in_window(backs[0][0], a, *W["resume"]) and W["out_ms"][0] <= om <= W["out_ms"][1]
               and backs[0][2].group(3) == "no exit ramp; still mirroring")
    led.check("S120B-G3", back_ok, f"{pb.show(backs)}; expected {W['out_ms'][0]:.0f}-{W['out_ms'][1]:.0f} ms")
    holds = pb.hits(lines, "hold_cut", after=a, before=e, pred=lambda m: int(m.group(1)) == N)
    res = pb.hits(lines, "hold_resume", after=a, before=_t(e, 4.0), pred=lambda m: int(m.group(1)) == N)
    t_res = res[0][0] if res else e
    bad = (pb.hits(lines, "leave", after=a, before=t_res) + pb.hits(lines, "watcher_settled", after=a, before=t_res)
           + pb.hits(lines, "hold_cap", after=a, before=t_res) + pb.hits(lines, "hold_stall_cap", after=a, before=t_res))
    held = int(res[0][2].group(2)) if res else None
    ok4, why4 = _hold_rule(ctx, lines, held, om, a, _t(t_res, 1.0))       # [ff9mapkit netsync s131]
    led.check("S120B-G4", len(holds) == 1 and len(res) == 1 and not bad and ok4,
              f"hold {pb.show(holds, 1)}; resume {pb.show(res, 1)}; leave/give-up before it {pb.show(bad)}; {why4}")
    post = _between(ctx, _t(t_ret, 1.0), _t(t_ret, 6.0)) if t_ret else []
    sess = [s.get("session") for s in post]
    mirrored = bool(post) and all(isinstance(x, dict) and x.get("mirroring") is True and x.get("ramp_pending") is False
                                  and x.get("state") == "live" for x in sess)
    tape_end_ok = t_ret is not None and ctx.anchors.get("replay_done") is None
    led.check("S120B-G5", bool(got_return) and mirrored and not ramps and tape_end_ok,
              f"RETURN {pb.show(r_t, 1)}; {len(post)} sample(s) after it: session "
              + (f"{sess[-1]!r}"[:300] if sess else "none") + ("" if tape_end_ok else "; the tape ended before the window"))
    s0 = (_before(ctx, a) or {}).get("session")
    s1 = ctx.samples[-1].get("session") if ctx.samples else None
    h0 = (_before(ctx, a) or {}).get("hold")
    h1 = ctx.samples[-1].get("hold") if ctx.samples else None
    d = (_delta(s0, s1, "outages"), _delta(s0, s1, "resumes"), _delta(s0, s1, "gaveup"), _delta(h0, h1, "resumes"))
    led.check("S120B-K", d == (1, 1, 0, 1), f"session {'ABSENT (pre-s120)' if s1 is None else ''} outages/resumes/gaveup "
                                             f"{d[:3]}; hold resumes {d[3]}")
    if CALIBRATE:
        _red_ramp(led, ctx, p, a, W)


def _leg_s120_long(g, led: cb.Ledger, ctx: _Ctx) -> None:
    p = "S120L"
    _until(g, ctx, lambda: "bh_begin" in ctx.anchors, (ctx.plan["bh"][0] - ctx.facts["start"]) + 30.0)
    a = ctx.anchors.get("bh_begin")
    if a is None:
        led.unreached(list(LEG_CHECKS["s120-long"]), f"the replay never reached its blackhole ({ctx.peer.tail(3)})")
        return
    dur = ctx.plan["bh"][1]
    _until(g, ctx, lambda: _after(ctx, "bh_begin", pb.STALE_S + GRACE_S + 10.0), pb.STALE_S + GRACE_S + 20.0)
    if not _gate(led, ctx, p, *_instrument(ctx, a, need=("paired", "armed"))):
        return
    W = pb.leg_windows(dur, GRACE_S)
    lines = ctx.eng.lines()
    early = pb.session_ends(lines, after=a, before=_t(a, pb.STALE_S + GRACE_S - 1.0))   # either exit-ramp line
    led.check("S120L-G1", not early, f"'session ended' before the grace ran out: {pb.show(early)}")
    outs = pb.hits(lines, "session_out", after=a, before=_t(a, 10.0))
    led.check("S120L-G2", len(outs) == 1 and pb.in_window(outs[0][0], a, *W["out"])
              and int(outs[0][2].group(2)) == int(GRACE_S), f"{pb.show(outs)} (window {W['out'][0]:g}..{W['out'][1]:g} s)")
    gave = pb.hits(lines, "session_gaveup", after=a)
    gm = int(gave[0][2].group(1)) if gave else None
    ramps = pb.session_ends(lines, after=gave[0][0]) if gave else []   # the bounded END is the claim; T2-SAVE the reload
    led.check("S120L-G3", len(gave) == 1 and pb.in_window(gave[0][0], a, *W["gaveup"])
              and W["gaveup_ms"][0] <= gm <= W["gaveup_ms"][1] and bool(ramps)
              and pb.in_window(ramps[0][0], a, *W["new_ramp"]),
              f"give-up {pb.show(gave, 1)}; ramp {pb.show(ramps, 1)} (windows {W['gaveup'][0]:g}..{W['gaveup'][1]:g} / "
              f"{W['new_ramp'][0]:g}..{W['new_ramp'][1]:g} s after the cut)")
    s0 = (_before(ctx, a) or {}).get("session")
    s1 = ctx.samples[-1].get("session") if ctx.samples else None
    inside = [s.get("session") for s in _between(ctx, _t(a, pb.STALE_S + 2.0), _t(a, pb.STALE_S + GRACE_S - 2.0))]
    graces = [x for x in inside if isinstance(x, dict) and x.get("state") == "grace"]
    d = (_delta(s0, s1, "gaveup"), _delta(s0, s1, "outages"), _delta(s0, s1, "resumes"))
    led.check("S120L-K", d == (1, 1, 0) and inside and len(graces) == len(inside),
              f"session {'ABSENT (pre-s120)' if s1 is None else ''} gaveup/outages/resumes {d}; state 'grace' on "
              f"{len(graces)} of {len(inside)} sample(s) inside the grace")
    if CALIBRATE:
        _red_ramp(led, ctx, p, a, W)


def _leg_s120_roam(g, led: cb.Ledger, ctx: _Ctx) -> None:
    p = "S120R"
    a, e, dur = _cut_anchors(g, ctx, timeout=(ctx.plan["bh"][0] - ctx.facts["start"]) + ctx.plan["bh"][1] + 40.0)
    if a is None or e is None:
        led.unreached(list(LEG_CHECKS["s120-roam"]), f"the replay never reached its blackhole edges ({ctx.peer.tail(3)})")
        return
    _until(g, ctx, lambda: _after(ctx, "bh_end", 10.0), 20.0)
    ok, why = _instrument(ctx, a, need=("paired", "armed"))
    pre = _before(ctx, a)
    mk = pre.get("marker") if pre else None
    ok = ok and mk == pb.MARKER_VALUE
    if not _gate(led, ctx, p, ok, f"{why}; the marker at the cut reads {mk!r} (own save before pairing "
                                  f"{ctx.marker_own!r}, the host's 0x{pb.MARKER_VALUE:02X})"):
        return
    W = pb.leg_windows(dur, GRACE_S)
    lines = ctx.eng.lines()
    ramps = pb.session_ends(lines, after=a, before=_t(e, 8.0))         # the reload OR its title fallback (T2-SAVE)
    pend = [s for s in _between(ctx, a, _t(e, 8.0)) if isinstance(s.get("session"), dict)
            and s["session"].get("ramp_pending")]
    led.check("S120R-G1", not ramps and not pend, f"'session ended' {pb.show(ramps)}; ramp_pending on {len(pend)} sample(s)")
    win = _between(ctx, _t(a, W["overlay"][0]), _t(a, W["overlay"][1]))
    ovl = [(s.get("session") or {}).get("overlay") if isinstance(s.get("session"), dict) else None for s in win]
    timed = [(s["t"], s["session"].get("overlay_detail")) for s in win if isinstance(s.get("session"), dict)]
    det = [d for _ts, d in timed]
    # [ff9mapkit netsync R3 s120] COUNTING DOWN, not merely "never up": the detail (SessionGraceLeftSec = ceil of the grace
    # left, in s) never rises sample to sample AND falls by the seconds the samples span, +-1.5 s (the ceil and the publish
    # lag) -- a frozen countdown (a stuck clock, a detail pinned at the grace) reads flat, and red
    span_s = (timed[-1][0] - timed[0][0]).total_seconds() if len(timed) >= 2 else 0.0
    drop = det[0] - det[-1] if len(det) >= 2 and all(isinstance(x, int) for x in det) else None
    counting = (drop is not None and all(x > 0 for x in det) and all(y <= x for x, y in zip(det, det[1:]))
                and span_s >= 3.0 and span_s - 1.5 <= drop <= span_s + 1.5)
    led.check("S120R-G2", len(win) >= 5 and all(o == "reconnecting" for o in ovl) and counting,
              f"{len(win)} sample(s) in {W['overlay'][0]:g}..{W['overlay'][1]:g} s: overlay {sorted(set(map(str, ovl)))}, "
              f"detail {det[:1]}..{det[-1:]} over {span_s:.1f} s (drop {drop}; want {span_s:.1f} +- 1.5, never rising)")
    outs = pb.hits(lines, "session_out", after=a, before=e)
    backs = pb.hits(lines, "session_back", after=a, before=_t(e, 4.0))
    om = int(backs[0][2].group(1)) if backs else None
    led.check("S120R-G3", len(outs) == 1 and pb.in_window(outs[0][0], a, *W["out"]) and len(backs) == 1
              and pb.in_window(backs[0][0], a, *W["resume"]) and W["out_ms"][0] <= om <= W["out_ms"][1]
              and backs[0][2].group(3) == "no exit ramp; still mirroring",
              f"outage {pb.show(outs, 1)}; back {pb.show(backs, 1)}")
    after = _between(ctx, e, _t(e, 3.0))
    good = [s for s in after if isinstance(s.get("session"), dict) and s["session"].get("ghost") is True
            and s["session"].get("mirroring") is True and s["session"].get("ramp_pending") is False
            and s["session"].get("state") == "live"]
    led.check("S120R-G4", bool(good), f"{len(good)} of {len(after)} sample(s) within 3 s of the resume read ghost + "
                                      f"mirroring + no ramp + live; last session "
                                      + (repr(after[-1].get('session'))[:300] if after else "none"))
    span = _between(ctx, a, _t(e, 5.0))
    marks = [s.get("marker") for s in span]
    led.check("S120R-G5", len(span) >= 10 and all(m == pb.MARKER_VALUE for m in marks),
              f"{len(span)} sample(s) from the cut to the resume+5 s: marker values {sorted(set(map(str, marks)))} "
              f"(the host's 0x{pb.MARKER_VALUE:02X}; own save {ctx.marker_own!r})")
    if CALIBRATE:
        _red_ramp(led, ctx, p, a, W)


def _leg_span(g, led: cb.Ledger, ctx: _Ctx) -> None:
    p, N = "SPAN", ctx.nonce
    want = ctx.plan["expect"].get("why")
    a, e, dur = _cut_anchors(g, ctx, timeout=_span_s(ctx) + 60.0)
    if a is None or e is None:
        led.unreached(list(LEG_CHECKS["span"]), f"the replay never reached its blackhole edges ({ctx.peer.tail(3)})")
        return
    _until(g, ctx, lambda: _after(ctx, "bh_end", 14.0), 30.0)
    if not _gate(led, ctx, p, *_instrument(ctx, a, need=("boot", "live"), booted=True)):
        return
    W = pb.leg_windows(dur, GRACE_S)
    lines = ctx.eng.lines()
    early = pb.hits(lines, "leave", after=a, before=_t(e, -0.5)) + pb.hits(lines, "watcher_settled", after=a,
                                                                           before=_t(e, -0.5))
    led.check("SPAN-G1", not early, f"LEAVE / watcher-leave before the cut ended: {pb.show(early)}")
    if want == "stall_cap":
        verdict = pb.hits(lines, "hold_stall_cap", after=e, pred=lambda m: int(m.group(2)) == 0)
    else:
        verdict = pb.hits(lines, "watcher_why", after=e,
                          pred=lambda m: m.group(1) == "the host's fight is over (the peer is alive and back on field "
                                                       f"{ctx.plan['expect'].get('after_field')})")
    v_ok = bool(verdict) and pb.in_window(verdict[0][0], a, *W["span_leave"])
    lv = pb.hits(lines, "leave", after=verdict[0][0]) if verdict else []
    ws = pb.hits(lines, "watcher_settled", after=verdict[0][0], pred=lambda m: int(m.group(1)) == N) if verdict else []
    ret = pb.hits(lines, "return", after=verdict[0][0]) if verdict else []
    # [ff9mapkit netsync s131] the over-verdict's 'after a M ms hold' by THE HOLD RULE's leave-ended form (the stall-cap
    # verdict prints no hold ms: only its menu-close count is judged)
    until = verdict[0][0] if verdict else _t(e, 1.0)
    if want == "stall_cap":
        closes = pb.hits(lines, "menu_close_nolane", after=a, before=until)
        ok2 = len(closes) <= pb.MENU_CLOSES_MAX
        why2 = (f"stall_cap prints no hold ms (no hold rule); no-lane menu closes across the cut {len(closes)} (want <= "
                f"{pb.MENU_CLOSES_MAX})")
    else:
        mh = verdict[0][2].group(3) if verdict else None
        om, _backs = _outage(lines, a, e)
        ok2, why2 = _hold_rule(ctx, lines, int(mh) if mh else None, om, a, until, leave=True)
    led.check("SPAN-G2", v_ok and bool(lv) and bool(ws) and bool(ret) and ok2,
              f"want {want}: verdict {pb.show(verdict, 1)} (window {W['span_leave'][0]:g}..{W['span_leave'][1]:g} s); "
              f"LEAVE {pb.show(lv, 1)}; watcher-leave {pb.show(ws, 1)}; RETURN {pb.show(ret, 1)}; {why2}")
    whys = [s["hold"].get("why") for s in _between(ctx, e, _t(e, 14.0)) if isinstance(s.get("hold"), dict)]
    led.check("SPAN-K", want in whys, f"netsync.diorama.hold.why after the cut: {sorted(set(map(str, whys))) or 'ABSENT'}")
    if CALIBRATE:
        _red_pair(led, ctx, p, a, W, before=e)


def _leg_s121(g, led: cb.Ledger, ctx: _Ctx) -> None:
    p, F = "S121", ctx.field
    start = ctx.anchors["start"]
    _until(g, ctx, lambda: bool(pb.hits(ctx.eng.lines(), "armed", after=start)), 40.0)

    def playable(s):
        return (s["ui"] == "FieldHUD" and s["control"] and not s["dialog"] and not s["fading"] and s["field"] == F)

    _until(g, ctx, lambda: playable(ctx.samples[-1]), 20.0)
    _until(g, ctx, lambda: False, 1.5)                          # past the same-field kick's fade-in
    stop = ctx.anchors.get("stop_at")
    ok, why = _instrument(ctx, _dt.datetime.now(), need=("paired", "armed"), what="the presses")
    last = ctx.samples[-1] if ctx.samples else {}
    ok = ok and bool(last) and playable(last) and stop is None
    if not _gate(led, ctx, p, ok, f"{why}; ui {last.get('ui')!r} control {last.get('control')} field {last.get('field')}"
                                  + ("; the replay had ALREADY stopped" if stop is not None else "")):
        return
    if isinstance(last.get("menu"), dict):                     # s121: gate the press on `now`, never on ui_state
        _until(g, ctx, lambda: (ctx.samples[-1].get("menu") or {}).get("now") == "audible", 5.0)
    m0 = ctx.samples[-1].get("menu")
    led.check("S121-G0", isinstance(m0, dict) and m0.get("now") == "audible",
              f"netsync.menu_refusal {'ABSENT (pre-s121)' if m0 is None else repr(m0)[:200]}")
    # press 1
    t1 = _dt.datetime.now()
    g.press("menu", 6)
    _until(g, ctx, lambda: False, 2.0)
    m1 = ctx.samples[-1].get("menu")
    w1 = _between(ctx, t1, _dt.datetime.now())
    l1 = pb.hits(ctx.eng.lines(), "menu_refused", after=t1)
    d1 = (_delta(m0, m1, "count"), _delta(m0, m1, "lines"))
    led.check("S121-G1", d1 == (1, 1) and isinstance(m1, dict) and m1.get("last_state") == "FieldHUD"
              and m1.get("last_field") == F,
              f"count/lines {d1}; last_state {None if m1 is None else m1.get('last_state')!r}, last_field "
              f"{None if m1 is None else m1.get('last_field')!r}, muted {None if m1 is None else m1.get('muted')!r} "
              "(muted true = the buzz was asked for and the engine's SFX are muted)")
    led.check("S121-G2", len(l1) == 1 and l1[0][2].group(1) == "field" and int(l1[0][2].group(2)) == F, pb.show(l1))
    uis = sorted({s["ui"] for s in w1})
    led.check("S121-G3", bool(w1) and uis == ["FieldHUD"], f"{len(w1)} sample(s) over 2 s: ui {uis}")
    # press 2, same field
    t2 = _dt.datetime.now()
    g.press("menu", 6)
    _until(g, ctx, lambda: False, 2.0)
    m2 = ctx.samples[-1].get("menu")
    l12 = pb.hits(ctx.eng.lines(), "menu_refused", after=t1)   # both presses' lines: the latch allows ONE per field
    d2 = (_delta(m1, m2, "count"), _delta(m1, m2, "lines"))
    led.check("S121-G4", d2 == (1, 0) and len(l1) == 1 and len(l12) == 1,
              f"count/lines {d2}; refusal lines since press 1: {len(l12)} ({pb.show(l12)})")
    if CALIBRATE:
        led.check("S121-RED", not l1 and uis == ["FieldHUD"], f"lines after press 1: {pb.show(l1)}; ui {uis}")
    # the control row: the replay stops, the session ends, the exit ramp reloads the guest's own autosave
    _until(g, ctx, lambda: "stop_at" in ctx.anchors, 60.0)
    stop = ctx.anchors.get("stop_at") or _dt.datetime.now()
    _until(g, ctx, lambda: bool(pb.session_ends(ctx.eng.lines(), after=stop)), pb.STALE_S + GRACE_S + 25.0)
    ramp = pb.session_ends(ctx.eng.lines(), after=stop)
    ok_ctl = bool(ramp) and _until(g, ctx, lambda: playable(ctx.samples[-1]) and ctx.samples[-1]["field"] == F, 45.0)
    _until(g, ctx, lambda: False, 1.5)
    m3 = ctx.samples[-1].get("menu")
    led.check("S121-G5", ok_ctl and isinstance(m3, dict) and m3.get("now") == "open",
              f"ramp {pb.show(ramp, 1)}; playable {ok_ctl}; netsync.menu_refusal.now "
              f"{'ABSENT (pre-s121)' if m3 is None else repr(m3.get('now'))}")
    if not ok_ctl:
        # [ff9mapkit netsync R3 T2] a title fallback (no own autosave) or a reload onto ANOTHER field (the Continue slot
        # held an older autosave) is the instrument's, not the engine's -- named here; T2-SAVE judges the first
        last = ctx.samples[-1]
        why = (" -- INSTRUMENT: the exit ramp fell back to the title (no own autosave; T2-SAVE)" if ramp and
               pb.MATCHERS["ramp_failed"].search(ramp[0][1]) else
               f" -- INSTRUMENT: the reload landed on field {last['field']}, not {F} (the Continue slot held an older "
               "autosave)" if ramp and last["ui"] == "FieldHUD" and last["field"] != F else "")
        led.check("S121-C1", False, f"the control row never came: ramp {pb.show(ramp, 1)}; last ui {last['ui']!r} field "
                                    f"{last['field']}{why}")
        return
    g.press("menu", 6)
    opened = _until(g, ctx, lambda: ctx.samples[-1]["ui"] == "MainMenu", 5.0)
    led.check("S121-C1", opened, f"ui after the press: {ctx.samples[-1]['ui']!r}")
    if opened:
        try:
            g.close_menu()
        except HarnessError as err:
            g.note(f"close_menu: {str(err)[:200]}")
