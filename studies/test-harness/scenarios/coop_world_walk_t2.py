"""s166 -- WORLD-MAP CO-OP RUNG 2, ROUND A: THE T2 AND DUO ROWS (memoria-patch s166). [ff9mapkit netsync s166]

Round A's two-role rows (studies/world-coop/S166-DESIGN.md "The bench": the Round A rows table's A-WIRE, T2-A old / roam / freeze, T2-H
and the Duo row), beside coop_world_walk.py's solo rows (imported, never copied: its round-A readers and judges, coop_world_follow's T2
route and conventions, coop_world_wait's walk out). One leg per launch (COOP_WWT_LEG); the duo through tools/harness/duo.py (run_duo).
The keys are the CLONE's (A3: `netsync.world.lane`, `netsync.world.line`, `netsync.host.world.guest`; A4: `netsync.world.ghost`, the
dot's `src`; A2: `netsync.wire_peer`). Every world row is judged after `world.block_ready` and advancing `world.ticks` (THE PRE-INIT
SAMPLE); every stall row on the ENGINE's clocks (`lane.seq_age_ms`, `ghost.seq_age_ms`), never the wall's; every T2 leg asserts the live
header version before judging (T2-PEER / T2H-PEER: coop_peer's own wire line against the game's published `netsync.wire`).

THE ORACLE, BY SEQ (never by the wall): a T2 replay's host frames carry decision 4's trailer with its own seq (+1 per sender Update, a
re-send repeats it), and the receiver cache publishes the seq it holds (`lane.rx.seq`). So the ghost of a sample is judged against the
TAPE's own trailer at that seq: its target (`ghost.tx / tz`) IS that pose (TARGET_TOL), and its eased pose lies within RM_TOL of the
tape's path over the seqs just before it (the ease lags ~83 ms, RM_LAG_SEQ frames of path) -- "the ghost on the ROAM tape's own trailer
pose at the matched second", matched by the second's own seq. T2-H judges the host's ghost the same way against serve-guest's TAP (what
it sent), and the duo against the other game's own published `lane.tx` (its trailer, at the same seq).

  wire   A-WIRE (the desktop a REAL s166 client, COOP_TAPE_WORLD_WALK -- v14 -- replayed UNRESTAMPED: `replay-host --wire tape`; `auto`
         would restamp it): S166-WIRE-NOPAIR never pairs (no paired / ARMED line, never mirroring, the receiver cache never fed), S166-
         WIRE-REJECT `wire_peer.rejected` rises, last_version 14, ONE peer-wire line, the mismatch words held and `world.line` asked
         'mismatch' (drawn: decision 3's words come first, anywhere), then S166-WIRE-CLEAR the same tape `--wire 15` (a matching engine):
         the words clear within WIRE_CLEAR_S and it pairs (the words never latch). OLD (A0b, v14): it pairs at once -- NOPAIR / REJECT /
         CLEAR red. LEVER (COOP_WWT_LEVER=wire15: `--wire 15` from the start): NOPAIR / REJECT red, MEASURED: pairs, rejected +0, the
         cache reads the capless host (`rx.kind` 'absent'), and on the world map the ghost's why_not 'no_record' (s165 behaviour).
  old    T2-A old: coop_world_follow.py's T2 `walk` leg AS IT IS on the s166 guest (`replay-host --wire auto`: the v14 tape restamped to
         15 = a CAPLESS v15 host, the OLD calibration of round A) -- every s165 row exactly -- plus S166-OLD-WIRE (the restamp line) and
         S166-OLD-DORMANT (round A dormant on a capless host: rejected +0, `rx.kind` absent, no lane line, the ghost never shown, why_not
         'no_record' on the world). OLD: green on v14 (A0b). LEVER: s165's own (`worldfollow off`, COOP_CALIBRATE=1: S165-WK-CAL).
  roam   T2-A roam: COOP_TAPE_WORLD_ROAM (OWNER-GATED: not recorded yet -- studies/world-coop/s166-handoff/ROAM-TAPE.md) replayed into a
         real s166 guest; until it exists THE INSTRUMENT (roam_instrument_tape: a SYNTHETIC v15 host built from ROAM_PLAN through coop_peer's
         real codec, named so on every row) runs the same judges and S166-RM-GATE stays RED ("the instrument, not the owner-gated tape").
         S166-RM-I paired + ARMED on 6603, the follow-out's landing on 9011, frozen. S166-RM-GHOST the frozen guest's ghost on the tape's
         trailer pose by seq (target exact, eased within RM_TOL, facing within YAW_TOL on straight legs). `--blackhole-at` two windows
         chosen off the tape (pick_window): S166-RM-BH23 2.3 s -- one gap line pair (its end ~2300 ms), the ghost held (shown, stood),
         eased back with no snap; S166-RM-BH6 6 s -- hidden 'stale' at a seq age 5000..6500, re-shown with a snap (a first show).
         OLD (A0b): the v15 tape cannot be restamped down -- T2-PEER red, every row unreached. LEVER `ghost` (`worldwalk ghost off`):
         RM-GHOST, BH23, BH6; `lanegap` (`worldwalk lanegap off`): BH23 (counted, no line).
  freeze T2-A freeze: the same tape, `replay-host --freeze-at` two windows (2.3 s and 6 s): the writer's re-send (the seq frozen,
         arrivals continue -- the guest's session never drops, so the world line is the ghost's). S166-FZ-23 held, _STAND by ~300 ms,
         never hidden, ONE hang line worded 'not updating' (the host was on place 4), no gap / lost line, its end ~2300 ms (the sender's
         span). S166-FZ-6 held, stood, hidden 'stale' at 5000..6500, `world.line` 'lost' with the "Lost contact" words AND drawn, its log
         line once; the end ~6000 ms, the lost-over line, re-shown with a snap. OLD: T2-PEER red. LEVER `lanegap`: both (counted, no
         line); `ghost`: both (want true, shown false).
  host   T2-H: the desktop a REAL s166 HOST on 9011 (walked out of 6603), `serve-guest --walk roam` its guest in three phases, each its own
         coop_peer process and TAP (the oracle): A a frozen guest (`--state 0x85`) with a scene window and a 1.5 s gap -- S166-TH-I the
         record reached the host (guest place 2, 3, 4), S166-TH-LINES its three lines (following, loading, scene: guest.line, world.line
         asked + words + drawn, one log line each), S166-TH-GHOST the host's ghost of the guest by seq, S166-TH-GAP one host lane gap
         pair (~1500 ms) with the ghost held; B a RELEASED guest (state b0 clear, flags b0 set) -- S166-TH-RELEASED lines and ghost; C
         `--no-follow` -- S166-TH-NOFOLLOW no line, no log line, no ghost (why_not 'role'). OLD (an A0b host): it shows nothing -- every
         TH row red ('absent'). LEVER `hostlines`: LINES, RELEASED; `ghost`: GHOST, GAP, RELEASED.
  record THE ROAM RECORDER (OWNER-GATED, never run by a bench script unasked: COOP_WWT_RECORD_OWNER=1 names the owner's go-ahead):
         the desktop an s166 HOST walks ROAM_PLAN while `serve-guest --no-follow --tap` records it -- ROAM-TAPE.md.
The duo (`py tools/harness/duo.py coop_world_walk_t2.py`, both games on 6603): S166-D0, D-LINES (the host's lines through the guest's
follow-out, the Taps started BEFORE the guest can leave -- _walk_out_tapped -- so the row is COVERED (the guest read at place 1 first);
[W2c] THE PREMISE, DETERMINISTIC (s165's D-FO2 shape): `worldfollow hold` on the guest BEFORE the host walks out, the release only once
the HOST Tap reads the host LIVE on 9011 (its own lane.tx.place 4 on a judged sample) + D_HOLD_SETTLE_S and the GUEST Tap's own last
sample reads the hold ENGAGED (out.why 'hold', up to D_HOLD_READ_S: s165's D-FO2 waits on the guest's own view too) -- and the row is red "not
covered" unless the host was live at or before the guest's trailer first read place 2 and the guest read back held (out.hold, why 'hold');
[W2b] 'following' lasts through the guest's commit and its synchronous load: no host end line names "the guest's place field" (the
d6df5df17fe0af03 build's signature) and it lasts >= the guest's own landed ms - D_LINES_SLACK_MS; 'loading' and the host's 'not updating'
lane lines REPORTED), D-G2 (the host's ghost of the frozen guest at the guest's own pose; the landing gap REPORTED: ONE-PC LOAD
CONTENTION), D-G1 (the host walks, CLOSED LOOP -- _walk_host stops on tx_moved or the Tap's own world x/z at D_MOVE_U + D_MOVE_MARGIN_U,
a frame cap and a wall deadline: the guest's ghost on the host's trailer by seq), D-TRAILER (the trailer ACTIVE both ways: the s144/s145
duo legs that follow in the runner run under it), D-BATTLE (both re-mint after the warm returns; THE ENTRY HIDE: the guest's ghost never
shown off the host's place 4 through its swirl; zero NON-LOADING hang lines outside the other game's own load windows -- a scene change,
or [W2b] a freeze out of an ANNOUNCED-load place 2 / 3; those inside are ONE-PC LOAD CONTENTION, reported), D-DOTRIDE (`vehicle 1` on
the host, it moves the same closed loop: the guest's dot src 'trailer' within DOT_TOL of the host's own trailer pose by seq), D-REJOIN
(the host Confirms into 300: both ghosts hidden before the guest's fade), D-SHARED. D-PAIR is DEFERRED (both duo games start on 6603:
the s42 same-field kick arms the mirror before any pull -- T2-A pair covers it). LEVERS (COOP_WWT_LEVER, COOP_CALIBRATE=1): `ghost`
(`ghost off` both roles: G2, G1, BATTLE), `sticky` (`ghost sticky` on the guest: BATTLE's entry hide through the host's swirl; inert on
REJOIN by THE ARM-FIRST ORDER), `dot` (`dot section0` on the guest: DOTRIDE). OLD (an A0b pair): every row but D-SHARED red.
(`ghost` also reds REJOIN: its instrument is the guest's ghost shown before the host left.) The host's encounters go off on 6603 BEFORE
the walk: the no-random-encounter booster (SettingsState.IsBoosterButtonActive[4]) lives for the process and survives the world load
(cleared only at the ending fields), so the Taps never share the host with a random battle.

CALIBRATION: every leg's rows can fail -- OLD by the stage (the table's *_OLD_PREDICTED), LEVER by its lever (*_LEVER_PREDICTED, each
red row MEASURING its lever's shape), and offline (ff9mapkit/tests/test_coop_world_walk_t2.py): the stand-in's faults turn exactly the
FAULT_REDS rows red through stub peers on the stand-in's own clock, and every pure judge goes red on each wrong shape.

PRECONDITIONS (the operator's job; studies/world-coop/s166-handoff/round_a_new.sh refuses otherwise): the W1+W2 build deployed (OLD:
the deployed A0b); FF9 closed between launches; no pytest / xdist running (benchguard); THE OWNER'S BRIDGE (127.0.0.1:49201) DOWN for
every T2 leg -- refused, never stopped; [SaveFile] AutoSaveOnlyAtMoogle 0; controllers off, nobody at the keyboard.

    COOP_WWT_LEG=wire   py tools/play.py studies/test-harness/scenarios/coop_world_walk_t2.py      (A-WIRE; COOP_WWT_LEVER=wire15)
    COOP_WWT_LEG=old    py tools/play.py studies/test-harness/scenarios/coop_world_walk_t2.py      (T2-A old)
    COOP_WWT_LEG=roam   py tools/play.py ...   COOP_WWT_LEG=freeze ...   COOP_WWT_LEG=host ...     (COOP_CALIBRATE=1 [COOP_WWT_LEVER=x])
    py tools/harness/duo.py studies/test-harness/scenarios/coop_world_walk_t2.py                   (the duo; COOP_WWT_LEVER for a lever)
    py studies/test-harness/scenarios/coop_world_walk_t2.py --make-roam-instrument <out.f9tape>    (the INSTRUMENT tape, offline)
    COOP_TAPE_WORLD_ROAM=<tape> overrides the ROAM tape; COOP_WWT_FORCE=1 runs past a tape whose facts fail (its T2-TAPE stays red)

ROUND B (s167, memoria-patch s167: the walk) -- the same file, its own legs (COOP_WWT_LEG walk | stallhole | hostb) and the duo's mode
COOP_WWT_DUO=b; the keys W1's contract_final (`netsync.world.walk` / `fp` / `walk.map`, the lane's s167 keys, `world.line.asked`'s s167
names). Each leg reads the STAGE off the probe: no round-B op is ever sent to s166, and every row then MEASURES s166's shape (OLD).
  walk      T2-B on the ROAM tape (OWNER-GATED: recorded on an s167 host -- caps b1, its digest, section 11); until it exists THE
            INSTRUMENT, an s167-shaped synthetic host CALIBRATED to this guest's own 9011 fingerprint (a calibration visit: the guest walks
            out alone, `fp.real` / `fp.components` read, back to 6603 by a field round trip) runs the rows and S167-WR-GATE stays RED (an
            s166-recorded tape reds it too: 'an older build'). The guest pairs on 6603 (mirroring) and follows the host out: S167-WR-FREE
            (walk.free, fp 'match', `hold up` >= WALK_U, b1), S167-WR-REFUSE (`fp fake dead` on the guest: fp_mismatch named 'world map
            meshes' off the HOST's real section 11), S167-WR-REJOIN-FAR (it walks away, free and >= FAR_U from the host when the host
            Confirms into 300: the rejoin pulls it). OLD: all three red, MEASURED frozen. LEVER `walk` (`walk off`): the same three.
  stallhole the guest walks out ALONE (no session), then the ROAM host `replay-host --from` a second on 9011 (stall_windows): S167-WR-PAIR
            (paired ON THE WORLD MAP: frozen, never mirroring, no follow-out, walk.why 'pairing' + its words), S167-W-STALLHOLE
            (`--blackhole-at` 2.3 s: the freeze held on every sample, stall_held past StaleMs, freeze.edges unmoved, no lift line),
            S167-W-STALLHOLE-KEYS (a 3.5 s blackhole, the Confirm at ICE_TILE once the lane passed StaleMs: freeze.keys +>=1, never 300;
            COOP_WWT_SAND_AT=x,z adds a place-52 press: no local battle, by the skip or the mask). OLD: all three red, measured (the stall
            lifts the freeze; the press reaches the script). LEVER `stallhold` (`stallhold old`): STALLHOLE + KEYS; `walk`: WR-PAIR.
  hostb     T2-HB: the desktop an s167 HOST on 9011, serve-guest's walking v15 record in four phases: QUIET (the host's own build: no s167
            line, the control), OLDER (`--caps 1`), FP (`--state 0x95 --digest dead`: 'fp_differs' + the host's fingerprint line),
            CANT (`--state 0x85 --walk-why pairing`: 'cant_walk'). OLD (an s166 host): OLDER / FP / CANT red ('absent'). LEVER `walk`
            on the host: the same three.
  duo b     `COOP_WWT_DUO=b py tools/harness/duo.py coop_world_walk_t2.py`: S167-D0, D-WFREE, D-W1 (the guest walks: the host's ghost
            of it by seq), D-W2 (the host walks: the guest's ghost, the guest free and unmoved), D-W3 (both), D-BATTLE (apart, its full
            map open: closed for the boot, booted and returned at its OWN pose, walks again), D-RIDE (`vehicle 1` on the host: the
            guest's verdict 'riding', never the dot), D-REFUSE (`fp fake dead` on the guest: named on the guest, 'fp_differs' on the
            host), D-ENTRY (W-ENTRY's judge on the duo guest), D-REJOIN-FAR + D-MAP (the guest far, free, its full map open when the
            host enters: closed FIRST -- 'rejoin' -- then pulled), D-REJOIN-WAIT (control off: the rejoin waits, the host walks back out:
            no follow-out, the ghost snaps), D-SHARED. Levers on the GUEST, any-role: `walk` (every walk row), `fullmap` (`fullmap old`
            + `minimap old`: D-MAP). OLD (an s166 pair): every row but D-SHARED. The close-map line ("Close the map to join your
            partner.") needs a RELEASED guest: no harness verb reaches the ~ menu's Release, so no leg can judge it (the stand-in's seam
            only).
  THE REGRESSION RE-KEY: on an s167 build round A's wire / roam / freeze / host legs and its duo pull round B's whole s166 lever set
  (ww.S166_LEVER_SET) right after their setup, and read s166 exactly; the `old` leg is coop_world_follow's own (its re-key is that
  file's). THE RECORDER names its tape by the host's stage (-s167 when the probe shows `netsync.world.walk`).
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import os
import re
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import coop_world_wait as cw                               # noqa: E402 - the s144 route (walk out, teleport, rejoin judges)
import coop_world_follow as wf                             # noqa: E402 - the s165 T2 route, its walk leg, its Tap
import _coop_peer_bench as pb                              # noqa: E402 - the T2 two-role bench helpers
import coop_world_walk as ww                               # noqa: E402 - round A's solo readers and judges (lane lines, levers)

HarnessError = cb.HarnessError
BW = cw._bw()

# ================================================================================================ the legs, the levers
#: [ff9mapkit netsync s167] round B's T2 legs (the section ROUND B: T2 + DUO; the duo's own mode is COOP_WWT_DUO=b)
B_T2_LEGS = ("walk", "stallhole", "hostb")
LEGS = ("wire", "old", "roam", "freeze", "host", "record") + B_T2_LEGS
_RAW_LEG = os.environ.get("COOP_WWT_LEG", "").strip().lower()
LEG = _RAW_LEG if _RAW_LEG in LEGS else None
#: each leg's calibration levers (COOP_WWT_LEVER; unset = the leg's first): `wire15` is replay-host's `--wire 15`; the rest are
#: `netsync worldwalk <op> <word>` on the game under test, sent BEFORE the replay / the serve-guest and held through the leg
LEVERS = {"wire": ("wire15",), "old": (), "roam": ("ghost", "lanegap"), "freeze": ("lanegap", "ghost"), "host": ("hostlines", "ghost"),
          "record": ()}
LEVER_OPS = {"ghost": ("ghost", "off"), "lanegap": ("lanegap", "off"), "hostlines": ("hostlines", "off"), "sticky": ("ghost", "sticky"),
             "dot": ("dot", "section0")}
DUO_LEVERS = ("ghost", "sticky", "dot")
LEVER_RAW = (os.environ.get("COOP_WWT_LEVER") or "").strip().lower() or None
FORCE = pb.env_flag("COOP_WWT_FORCE")


def lever_of(leg: str, raw):
    """The calibration lever for ``leg`` (the duo: "duo"): ``raw`` when it is one of the leg's, the leg's first when ``raw`` is None, else None."""
    levers = DUO_LEVERS if leg == "duo" else LEVERS.get(leg, ())
    if raw is None:
        return levers[0] if levers else None
    return raw if raw in levers else None


# ================================================================================================ the places, the probes, the times
FARSHORE, WORLD, FS_LANDING, ICE_TILE, ICE_CAVERN = cw.FARSHORE, cw.WORLD, cw.FS_LANDING, cw.ICE_TILE, cw.ICE_CAVERN
PORT, CODE = wf.PORT, wf.CODE
GUEST_VALUES = wf.GUEST_VALUES
#: the T2-H host's [Netsync] (coop_tape_record's HOST_VALUES on THIS bench's private port; GuestSlots 0: the fake guest never commands)
HOST_VALUES = {"Enabled": "1", "Role": "host", "RelayUrl": f"ws://127.0.0.1:{PORT}", "SessionCode": CODE, "GuestSlots": "0",
               "FollowHost": "0", "TargetField": "0", "StartHoldMs": "8000"}
LANE, LINE, GHOST, DOT_SRC = ww.LANE_PROBE, ww.LINE_PROBE, ww.GHOST_PROBE, ww.DOT_SRC_PROBE
WIRE_PEER = "netsync.wire_peer"                            # A2's
HOST_GUEST = "netsync.host.world.guest"                    # A3's (the host role)
WIRE_OLD, WIRE_NEW = 14, 15
W, H = BW.WW_WORLD_W, BW.WW_WORLD_H
REPLAY_SPEED = 1.0       # replay-host replays in real time (a test seam)
POLL_S = 0.1
DETAIL_W = 1400
# ---- A-WIRE
WIRE_S = 20.0            # the unrestamped window: the replay's start -> the rows judged (the guest drops every frame)
WIRE_REJECT_MIN = 20     # ...`wire_peer.rejected` rose at least this much (~30 frames a second)
WIRE_CLEAR_S = 6.0       # `--wire 15` started -> the mismatch words gone and a sample after it. [ff9mapkit netsync s166] W3b: the words
                         # now hold 15 s past the last refusal (WireMismatchHoldMs), longer than this window, so the clear here is the
                         # matching engine's FIRST FRAME (NoteMine: a 2 s redial cycle + the connect), never the hold aging out
WIRE_PAIR_S = 30.0       # ...-> paired (the paired line, or mirroring)
WIRE_WORLD_S = 90.0      # the lever's measure: the paired guest's follow-out -> a judged world sample (its ghost why_not)
# ---- the ghost oracle
TARGET_TOL = 0.05        # the ghost's target IS a tape trailer's pose (float32 through the codec)...
TARGET_LAG_SEQ = 2       # ...at the cache's seq or up to this many before it (the harness may publish between NetSyncClient.Update,
                         # which moves the cache, and the driver's LateUpdate, which takes the new target)
RM_TOL = 6.0             # the eased ghost within this (torus) of the tape's recent path (the ease's 83 ms + a frame of publish skew)
RM_LAG_SEQ = 15          # ...that path: the trailer's last RM_LAG_SEQ seqs up to the cache's (~0.5 s at 30 a second)
YAW_TOL = 8.0            # on a straight leg (the tape's yaw steady over the lag) the ghost faces the walker's heading within this
YAW_STEADY = 1.0
MIN_YAWS = 3             # [W2 critic] ...and at least this many straight-leg facings judged (else the clause never ran)
RM_MIN_SAMPLES = 20
SHOW_S = 2.0             # the landing's first judged sample -> the ghost first shown (the lazy mint behind the strict gate)
# ---- the windows off the tape (pick_window)
ROOM_S = 15.0            # the host's world-live start -> the first window (the guest's debounce, fade, ~4.4 s load, the ghost settled)
SEAM_ROOM_S = 4.0        # ...and past the tape's seam crossing (RM-GHOST judges the seam before any window)
RECOVER_S = 3.0          # a window's recovery (ease back / re-show) inside valid, teleport-free trailer rows
GAP_WINDOW_U = (8.0, 50.0)   # BH23: the host moves this much over the window (eases back; under SnapJumpU 64 -- no snap)
BH23_S, BH6_S = 2.3, 6.0
GAP_LEN_TOL = 450        # a gap's end names its length within this of the window's (the receiver's clock: + a write tick, the publish)
HANG_LEN_TOL = 450       # a hang's end names the SENDER's span (the tape's ms jump across the freeze) within this
STAND_MS, STAND_SLACK_MS = BW.WW_GHOST_STAND_MS, 400
HIDE_MS, HIDE_SLACK_MS = BW.WW_GHOST_GRACE_MS, 1500
HOLD_TOL = 0.5
EASE_BACK_S = 1.0        # BH23: after the gap's end, the ghost back on the tape's path within this
LAND_S = 90.0            # the replay's start -> the guest's first judged world sample (pairing, the host's 25 s field stand, the pull)
EVENT_S = 120.0          # ...-> every window over, the host on 300
# ---- T2-H
HOST_PHASES = ("a", "b", "c")
TH_OUT_S, TH_LOAD_S = 1.5, 3.0     # serve-guest's --walk-out / --walk-load
TH_SCENE_AT, TH_SCENE_FOR = 9.0, 2.0
TH_GAP_AT, TH_GAP_FOR = 15.0, 1.5
TH_A_S, TH_B_S, TH_C_S = 30.0, 12.0, 10.0   # each phase's watch (A: until its gap is over; B / C: from their first frame)
TH_TAIL_S = 2.0          # A: the gap's recovery watched this long
GAP_SEEN_MS, GAP_BACK_MS = 300, 200   # the host's cache reads the gap (arrivals stopped this long) / the frames back
TH_DIAL_S = 20.0         # serve-guest listening -> the HOST connected (the engine redials every 2 s)
TH_MIN_SAMPLES = 12
# ---- the duo
D_G2_TOL = 2.0           # the host's ghost of the FROZEN guest on the guest's own pose (it stands: only the publish skew)
D_G1_TOL = 8.0           # the guest's ghost of the walking host: eased within this of its target
D_SEQ_SLACK = 6          # the host's trailer pose at a seq: bracketed by its own samples within this many seqs
D_TARGET_TOL = 4.0       # ...the target within this of the bracketed pose (the host's ~30 u/s over a bracket's half)
DOT_TOL = wf.DOT_TOL     # 8 u: the guest's dot on the host's own pose (the design's)
D_MOVE_U = 20.0          # the host moved at least this (D-G1 / D-DOTRIDE: a parked pose proves nothing)
#: [W2b] THE CLOSED-LOOP WALK (_walk_host): the real on-foot speed is 0.201 u/frame (~12 u/s, the round-A duo 20261104-015601: a fixed
#: 90-frame hold walked 18.4 u < D_MOVE_U), so the hold is a CAP and the walk stops on distance -- the judge's own tx_moved OR the Tap
#: samples' own world x/z (a dark trailer never walks on) reaching D_MOVE_U + D_MOVE_MARGIN_U -- or on the wall deadline D_WALK_S (a host
#: that never gets there fails the row with its real 'moved X u'). Read off the Taps' own buffers only.
D_MOVE_MARGIN_U = 5.0
D_WALK_FRAMES = 200      # the hold's CAP in frames: 25 u on foot at 0.201 u/frame is ~125; a runaway is bounded (~40 u on foot, ~72 riding)
D_WALK_S = 6.0           # the walk's wall deadline (200 frames down to ~33 fps)
D_WALK_TAIL_S = 0.5      # after the release: the last trailer arrivals and the ghost's ease, sampled
TAP_S = 0.04             # the duo's per-game sampler period (coop_world_follow.Tap's; a test seam: the stand-in runs faster)
D_LAND_S = 45.0          # the host's first judged world sample -> the guest landed
D_S = 3.0
D_MIN_SAMPLES = 8
#: [W2b] D-LINES' DURATION TERM: the host's 'following' lasts through the guest's commit AND its synchronous load, so it ends no earlier
#: than the guest's own "world follow-out: landed ... N ms after its start" minus this (the host reads the start a relay hop late; the
#: d6df5df17fe0af03 build ended it at the commit: 235 ms against N 1766)
D_LINES_SLACK_MS = 1000
#: [W2c] D-LINES' PREMISE, MADE DETERMINISTIC the way s165's duo does it (coop_world_follow D-FO2): `worldfollow hold` on the guest before
#: the host walks out; the release only once the HOST Tap reads the host LIVE on WORLD (own_live: its own lane.tx.place 4 on a judged
#: sample) and then this settle. s165's start trigger -- 1200 ms of host-ALIVE section-7 b6 frames -- runs AHEAD of the host's own block
#: load on one PC (ONE-PC LOAD CONTENTION; s165: THE LIVE DEBOUNCE does not reliably straddle it), and the host's HostLineRule needs its
#: OWN live world, so a guest that follows out of a host still on place 3 can never be told 'following' (the round-A duo 20261104-043742:
#: the host on place 3 from 04:38:43.30 to 46.73, the guest's place 2 from 44.50 through its commit; the calibration duo 042230 happened
#: to have the host live in time). The hold is the START only: THE LIVE DEBOUNCE accumulates under it, so the release starts at once.
D_HOLD_SETTLE_S = 0.5
#: [W2c verify] ...and then up to this long for the GUEST Tap's own LAST sample to read the hold ENGAGED (out.hold true, why 'hold': the
#: guest's own view of the host live, its debounce gates passed, only the hold left) -- the guest learns the host is live over the wire,
#: so under load its why still reads 'host_not_world' a 0.5 s settle after the host's own place 4 (the stand-in duo under -n 6: red
#: "not held ... why 'host_not_world'"). s165's D-FO2 waits on the guest's own host cache the same way. At the timeout the last sample
#: is judged as it stands (the premise reds it): a hold the engine ignores never reads 'hold'.
D_HOLD_READ_S = 4.0
#: judge_d_lines' ``held`` for a route that sent no hold (a test seam's W2b route): the premise is the live term alone
NO_HOLD = "no hold"
LOAD_GAP_S = 0.8         # a game's OWN sync load: its published frames stop at least this long across a scene change
#: [W2b] the trailer places a game ANNOUNCES a load from (PlaceTransition / PlaceWorldLoading: LaneGapKind's own 'loading' set,
#: NetSyncWorldWalk.cs:547) -- load_windows' place-keyed term
_LOAD_PLACES = (BW.WW_PLACE_TRANSITION, BW.WW_PLACE_WORLD_LOADING)
CONTENTION_PAD_S = 1.5   # a hang line inside the OTHER game's load window +- this (the log stamps whole seconds) is contention
D_BATTLE = os.environ.get("COOP_WWT_DUO_BATTLE", "1").strip() != "0"   # 0: the stand-in duo (no diorama model): D-BATTLE not run
D_SCENE, D_GROUP = 67, 0
D_FIGHT_S, D_RETURN_S = 240.0, 60.0

# ================================================================================================ THE ROAM PLAN (one source)
#: The host's route on 9011 after its blocks -- the recorder WALKS it (record leg), the instrument SYNTHESIZES it (roam_instrument_tape).
#: ("stand", s) | ("walk", bearing deg -- atan2(dz, dx), Session.world_face's -- , distance u) | ("turn", L1 frames: the camera only,
#: never on the trailer) | ("tile", (x, z): a teleport) | ("enter", field: the tile's Confirm). FS_LANDING (68, -444) first (the follow-out's
#: landing pose); four on-foot legs with stands; ONE L1 turn; leg 2 crosses the x seam west (68 -> 1484, through x 0); then ICE_TILE 20 s
#: and the Confirm into 300 (the design's route).
ROAM_PLAN = (("stand", 3.0), ("walk", 270.0, 90.0), ("stand", 6.0), ("turn", 20), ("walk", 180.0, 120.0), ("stand", 6.0),
             ("walk", 90.0, 90.0), ("stand", 6.0), ("walk", 270.0, 80.0), ("stand", 8.0), ("tile", ICE_TILE), ("stand", 20.0),
             ("enter", ICE_CAVERN), ("stand", 15.0))
INSTRUMENT_UPS = 24.0    # the synthetic walker (coop_peer.WALK_UPS)
INSTRUMENT_FIELD_S = 25.0
INSTRUMENT_LOAD_S = 4.4  # the host's own all-block load: its writer re-sends the place-3 slot, the seq frozen
INSTRUMENT_HZ = 30.0     # type-0 (one per sender Update); type-5 at a third of it
ROAM_POINTER = "latest-world-roam.json"
ROAM_TAPE_MIN = {"field_s": 10.0, "walk_u": 200.0, "legs": 3, "tile_s": 15.0, "enter_s": 8.0}


# ================================================================================================ the catalogs
T2_COMMON = dict(wf.T2_COMMON)
WIRE_CHECKS = {
    "S166-WIRE-NOPAIR": "A-WIRE: the unrestamped v14 tape (`--wire tape`) never pairs a v15 guest -- no paired / ARMED line, never "
                        "mirroring, FieldHUD 6603 throughout, the receiver cache never fed (lane.rx.samples 0)",
    "S166-WIRE-REJECT": "A-WIRE: `wire_peer.rejected` rises, last_version 14, lines +1 and ONE peer-wire log line, the mismatch words "
                        "held, `world.line` asked 'mismatch' with the words, drawn",
    "S166-WIRE-CLEAR": "A-WIRE: the same tape `--wire 15` (a matching engine): the mismatch words gone within WIRE_CLEAR_S of its first "
                       "frame (never latched) and it pairs",
}
WIRE_ROWS = tuple(WIRE_CHECKS)
WIRE_OLD_PREDICTED = WIRE_ROWS                                              # A0b (v14): it pairs; no wire_peer
WIRE_LEVER_PREDICTED = {"wire15": ("S166-WIRE-NOPAIR", "S166-WIRE-REJECT")}
OLD_CHECKS = {
    "S166-OLD-WIRE": "T2-A old: replay-host restamped the v14 tape to the v15 guest ('restamped from the tape's 14') -- on a v14 guest "
                     "'as recorded'",
    "S166-OLD-DORMANT": "T2-A old: round A DORMANT on a capless host -- rejected +0, lane.rx.kind 'absent' (caps 0), no lane line, the "
                        "ghost never shown and why_not 'no_record' on the world (an engine before A3: dormant by construction)",
}
OLD_ROWS = tuple(OLD_CHECKS)
ROAM_CHECKS = {
    "S166-RM-I": "T2-A roam: the instrument -- paired + ARMED on 6603 before the host's exit, the follow-out's landing on 9011 (judged), "
                 "frozen, the ghost wanted",
    "S166-RM-GHOST": "T2-A roam: the frozen guest's ghost on the tape's own trailer pose BY SEQ -- shown, target exact, eased within "
                     "RM_TOL of the tape's path, facing the walker's heading on straight legs",
    "S166-RM-BH23": "T2-A roam: `--blackhole-at` 2.3 s -- one gap line pair (its end ~2300 ms), no hang line, the ghost held (shown, "
                    "stood), eased back with no snap",
    "S166-RM-BH6": "T2-A roam: `--blackhole-at` 6 s -- hidden 'stale' at a seq age 5000..6500 (want false), re-shown after it with a "
                   "snap (a first show)",
}
ROAM_ROWS = tuple(ROAM_CHECKS)
ROAM_GATE = {"S166-RM-GATE": "the OWNER-GATED tape: COOP_TAPE_WORLD_ROAM recorded on the s166 host (ROAM-TAPE.md) -- RED on THE "
                             "INSTRUMENT (a synthetic v15 host: never a substitute)"}
ROAM_OLD_PREDICTED = ("T2-PEER",) + ROAM_ROWS
ROAM_LEVER_PREDICTED = {"ghost": ("S166-RM-GHOST", "S166-RM-BH23", "S166-RM-BH6"), "lanegap": ("S166-RM-BH23",)}
FREEZE_CHECKS = {
    "S166-FZ-23": "T2-A freeze: `--freeze-at` 2.3 s -- held, _STAND by ~300 ms, never hidden, ONE hang line 'not updating', no gap / "
                  "lost line; its end ~2300 ms (the sender's span)",
    "S166-FZ-6": "T2-A freeze: `--freeze-at` 6 s -- held, stood, hidden 'stale' at 5000..6500, `world.line` 'lost' with the words AND "
                 "drawn, its log line once; the end ~6000 ms, the lost-over line, re-shown with a snap",
}
FREEZE_ROWS = tuple(FREEZE_CHECKS)
FREEZE_OLD_PREDICTED = ("T2-PEER",) + FREEZE_ROWS
FREEZE_LEVER_PREDICTED = {"lanegap": FREEZE_ROWS, "ghost": FREEZE_ROWS}
HOST_COMMON = {
    "T2H-PEER": f"port {PORT} free, the owner's bridge down; the host config line; serve-guest listening, the HOST connected, its host "
                "header line (the live header: the host's wire = the fake guest's)",
    "T2H-INI": "Memoria.ini restored byte-exact (sha256) after the run",
}
HOST_CHECKS = {
    "S166-TH-I": "T2-H: the host on 9011 (judged) and the walking record reached it -- host.world.guest place 2, 3 and 4, flags 1",
    "S166-TH-LINES": "T2-H: the host's three lines -- following, loading, scene in that order (guest.line and world.line asked, the "
                     "words, drawn) and one 'host world: the partner is <x>' log line each",
    "S166-TH-GHOST": "T2-H: the host's ghost of the walking guest on serve-guest's tap BY SEQ (target exact, eased within RM_TOL)",
    "S166-TH-GAP": "T2-H: serve-guest's `--gap-at` 1.5 s -- one host lane gap pair (its end ~1500 ms), no hang line, the ghost held, no "
                   "'lost' line",
    "S166-TH-RELEASED": "T2-H: a RELEASED guest (state b0 clear, flags b0 set) -- the 'following' line and the ghost shown",
    "S166-TH-NOFOLLOW": "T2-H: `--no-follow` (flags b0 clear) -- no guest line, no 'host world' log line, the ghost never shown (why_not "
                        "'role')",
}
HOST_ROWS = tuple(HOST_CHECKS)
HOST_OLD_PREDICTED = HOST_ROWS                                              # an A0b host shows nothing
HOST_LEVER_PREDICTED = {"hostlines": ("S166-TH-LINES", "S166-TH-RELEASED"),
                        "ghost": ("S166-TH-GHOST", "S166-TH-GAP", "S166-TH-RELEASED")}
RECORD_CHECKS = {
    "REC-OWNER": "THE OWNER GATE: COOP_WWT_RECORD_OWNER=1 (the owner's go-ahead), the owner's bridge DOWN, an s166 host (wire 15, the "
                 "lane published)",
    "REC-P0": f"the bench port {PORT} free and serve-guest listening",
    "REC-P1": "the host config applied (the engine's own config line)",
    "REC-P2": "the host dialled serve-guest (both sides' lines) at wire 15",
    "REC-M": "the story marker 0xA5 on byte 1121",
    "REC-WX": "the walk out of 6603 landed on 9011",
    "REC-RB": "the blocks (block_ready, ticks advancing)",
    "REC-RL": "the FS_LANDING stand",
    "REC-RW": "every walk leg of ROAM_PLAN walked on foot (world_approach 'reached', or >= 60% of its distance)",
    "REC-RS": "the x seam crossed on foot (a world x >= 1472 next to one < 64)",
    "REC-RT": "the ICE_TILE teleport and its stand",
    "REC-RE": "the Confirm into 300 and its stand",
    "REC-T": "the tape closed and reads back with no torn tail",
    "REC-RF": "the ROAM facts (roam_tape_facts rm1..rm7) and both windows found",
    "REC-INI": "Memoria.ini restored byte-exact",
}
DUO_CHECKS = {
    "S166-D0": "the instrument: both on FieldHUD 6603, the guest mirroring, both s166 (wire 15, lane + ghost published)",
    "S166-D-LINES": "the host walks out (the Taps from BEFORE the guest can leave: COVERED -- the guest read at place 1 first; THE PREMISE: "
                    "the guest held by `worldfollow hold` until the host is live, the host's own place 4 at or before the guest's "
                    "first place 2, the hold read back): the HOST's "
                    "'following' line (guest.line, world.line asked + words + drawn) and ONE log line while the guest follows out, "
                    "through its commit and load (no end line naming 'the guest's place field'; lasting >= the guest's landed ms - "
                    "D_LINES_SLACK_MS); none once it landed ('loading' and 'not updating' lane lines REPORTED: ONE-PC LOAD CONTENTION)",
    "S166-D-G2": "the host's ghost of the FROZEN guest within D_G2_TOL of the guest's own world x/z (the landing gap REPORTED: ONE-PC "
                 "LOAD CONTENTION confounds a landing judgment)",
    "S166-D-G1": "the host walks (closed loop: until it moved D_MOVE_U + D_MOVE_MARGIN_U, a cap and a deadline): the guest's ghost on the "
                 "host's trailer BY SEQ (target within D_TARGET_TOL of the host's own tx, eased within D_G1_TOL), the host moved >= "
                 "D_MOVE_U, the guest's own pose unmoved",
    "S166-D-TRAILER": "the trailer ACTIVE both ways on the world map (tx and rx kind 'fmt1', peer caps 1 on both): the s144 / s145 duo "
                      "legs the runner runs next run under it",
    "S166-D-BATTLE": "the host's world battle and both warm returns: both ghosts RE-MINTED (mints +1) and shown again; the guest's ghost "
                     "never shown off the host's place 4 (THE ENTRY HIDE through the host's swirl); zero NON-LOADING hang lines on either "
                     "game outside the OTHER game's own load windows (a scene change or an ANNOUNCED-load place step; those inside: "
                     "ONE-PC LOAD CONTENTION, reported)",
    "S166-D-DOTRIDE": "`vehicle 1` on the host, it moves: the guest's dot src 'trailer' within DOT_TOL of the host's own trailer pose BY "
                      "SEQ, the host's mode 1, moved >= D_MOVE_U",
    "S166-D-REJOIN": "the host Confirms into 300: the guest's ghost hidden on every sample after the host's trailer left place 4 and "
                     "inside its own rejoin window; the host's hidden off the world; the guest rejoins 300",
    "S166-D-SHARED": "THE SHARED-FILE LAW (the instrument): no 'Sharing violation' / 'When importing FBX' in either log",
}
DUO_ORDER = tuple(DUO_CHECKS)
DUO_OLD_PREDICTED = tuple(c for c in DUO_ORDER if c != "S166-D-SHARED")
#: [W2 critic] `ghost off` also reds D-REJOIN: its instrument (the ghost shown before the host left) never holds under the lever
#: [W2b] `ghost sticky` bites only while the observer is live and the peer publishes place 2: the host's SwirlScene, ahead of InOwnBattle's
#: nonce that boots the guest's diorama (D-BATTLE's ENTRY HIDE). It is INERT on D-REJOIN: the host's MAPJUMP exit publishes place 4 up
#: to its intent, and the guest arms on that intent (GhostNotLive, asked before GhostSample)
#: -- the round-A lever duo 20261104-022302 left it green
DUO_LEVER_PREDICTED = {"ghost": ("S166-D-G2", "S166-D-G1", "S166-D-BATTLE", "S166-D-REJOIN"), "sticky": ("S166-D-BATTLE",),
                       "dot": ("S166-D-DOTRIDE",)}
#: the stand-in's faults (fakegame.WORLD_WALK_A_FAULTS) -> exactly the rows each turns red, by leg (tests pin it; a fault absent from a leg
#: turns nothing red there). The `*_lever_ignored` faults are each CAL row's own.
FAULT_REDS = {
    "wire": {"wire_peer_dark": ("S166-WIRE-REJECT",), "wire_words_latched": ("S166-WIRE-CLEAR",)},
    "old": {"arrival_on_seq": ("S166-OLD-DORMANT",)},              # a capless host never moves the seq: the arrival clock pinned -> gaps
    "roam": {"ghost_unwrapped": ("S166-RM-GHOST",)},               # a naive canonical ease: the ghost sweeps the map at the seam leg
    "freeze": {"hold_on_valid": FREEZE_ROWS,                       # the hold keyed on rs.Valid: re-sends keep it MOVE, never _STAND
               "gap_on_stamp": FREEZE_ROWS,                        # a hang read as a gap
               "arrival_on_seq": FREEZE_ROWS,                      # the arrival clock moved only on a seq move: a gap at every freeze
               "line_dark": ("S166-FZ-6",)},                       # the lost-contact line never decided
    "host": {"host_lines_state_b0": ("S166-TH-LINES", "S166-TH-RELEASED")},   # keyed on state b0: the follow-out (b5) and a released
                                                                              # guest get no line
    "duo": {"dot_src_section0": ("S166-D-DOTRIDE",),    # (state-b0 lines: T2-H's -- the stand-in's follow-out carries b0 there)
            "tx_commit_blind": ("S166-D-LINES",)},      # [W2b] the d6df5df17fe0af03 build: the host's 'following' ends at the commit
}
LEVER_IGNORED = {"ghost": "ghost_lever_ignored", "lanegap": "lanegap_lever_ignored", "hostlines": "hostlines_lever_ignored",
                 "sticky": "ghost_lever_ignored", "dot": "dot_src_lever_ignored"}


def leg_catalog(leg: str, calibrate: bool, *, instrument: bool = False) -> dict:
    """The rows a leg's Ledger carries, in order (the finals last)."""
    if leg == "record":
        return dict(RECORD_CHECKS)
    if leg == "host":
        cat = {"T2H-PEER": HOST_COMMON["T2H-PEER"]}
        cat.update(HOST_CHECKS)
        if calibrate:
            cat["S166-TH-CAL"] = "CALIBRATION: by the HOST's stage -- an A0b host exactly HOST_OLD_PREDICTED red; on s166 under the lever exactly its rows, each MEASURED"
        cat["T2H-INI"] = HOST_COMMON["T2H-INI"]
        return cat
    cat = {"T2-TAPE": T2_COMMON["T2-TAPE"] if leg in ("wire", "old") else
           "the ROAM tape (or THE INSTRUMENT) reads back, wire 15, its facts (roam_tape_facts) and the windows found",
           "T2-PEER": T2_COMMON["T2-PEER"] + "; THE LIVE HEADER: coop_peer's guest-wire line against the game's netsync.wire"}
    cat.update({"wire": WIRE_CHECKS, "old": OLD_CHECKS, "roam": ROAM_CHECKS, "freeze": FREEZE_CHECKS}[leg])
    if leg == "roam":
        cat.update(ROAM_GATE)
    if calibrate:
        cat[f"S166-{leg.upper()}-CAL"] = (f"CALIBRATION: by the GUEST's stage -- OLD exactly {leg}'s OLD_PREDICTED red, on s166 under the "
                                          "lever exactly its LEVER_PREDICTED, each MEASURING its lever's shape")
    cat["T2-SAVE"] = T2_COMMON["T2-SAVE"]
    cat["T2-INI"] = T2_COMMON["T2-INI"]
    return cat


# ================================================================================================ pure readers
def _num(v):
    return ww._num(v)


def _blk(x, probe) -> dict:
    v = cb.path(x, probe) if x is not None else None
    return v if isinstance(v, dict) else {}


def _lane(x) -> dict:
    return _blk(x, LANE)


def _rx(x) -> dict:
    return _lane(x).get("rx") or {}


def _tx(x) -> dict:
    return _lane(x).get("tx") or {}


def _ghost(x) -> dict:
    return _blk(x, GHOST)


def _line(x) -> dict:
    return _blk(x, LINE)


def _dot(x) -> dict:
    return _blk(x, "netsync.world.dot")


def _wp(x) -> dict:
    return _blk(x, WIRE_PEER)


def _hg(x) -> dict:
    return _blk(x, HOST_GUEST)


def _d(a, b, block, key):
    """b's ``block(x)[key]`` - a's; None when either is unread."""
    va = _num(block(a).get(key)) if a is not None else None
    vb = _num(block(b).get(key)) if b is not None else None
    return None if va is None or vb is None else vb - va


def judged(s) -> bool:
    return wf.judged(s)


def stage_of(x) -> str:
    """The game's round-A stage by key PRESENCE: 'a4' (the ghost), 'a3' (the lane), 'a2' (the wire_peer), else 'old' (A0b or older)."""
    if x is None:
        return "old"
    return "a4" if cb.has(x, GHOST) else "a3" if cb.has(x, LANE) else "a2" if cb.has(x, WIRE_PEER) else "old"


def wire_of(x):
    """The game's published `netsync.wire` (State.dialogue_wire), None unread."""
    w = getattr(x, "dialogue_wire", None) if x is not None else None
    return w if isinstance(w, int) else None


def _tdx(d: float, span: float) -> float:
    """``d`` the short way round one torus axis, in [-span/2, span/2)."""
    return (float(d) + span / 2.0) % span - span / 2.0


def torus(ax, az, bx, bz) -> float:
    return math.hypot(_tdx(bx - ax, W), _tdx(bz - az, H))


def _seg_dist(px, pz, ax, az, bx, bz) -> float:
    dx, dz = bx - ax, bz - az
    n = dx * dx + dz * dz
    k = 0.0 if n <= 0.0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / n))
    return math.hypot(px - (ax + k * dx), pz - (az + k * dz))


def path_distance(px: float, pz: float, pts) -> float | None:
    """(PURE) The distance from (px, pz) to the polyline ``pts`` on the TORUS (each point unwrapped next to the probe): None for none."""
    if not pts:
        return None
    u = [(px + _tdx(x - px, W), pz + _tdx(z - pz, H)) for x, z in pts]
    if len(u) == 1:
        return math.hypot(u[0][0] - px, u[0][1] - pz)
    return min(_seg_dist(px, pz, a[0], a[1], b[0], b[1]) for a, b in zip(u, u[1:]))


def _yaw_diff(a: float, b: float) -> float:
    r = math.fmod(abs(float(a) - float(b)), 360.0)
    return min(r, 360.0 - r)


def seq_back(s: int, n: int) -> int:
    return (int(s) - int(n)) & 0xFFFF


# ---- the tape's trailers (the oracle)
def trailer_rows(records, cp, direction: int = 0) -> list:
    """(PURE over tape records) Every type-0 frame of ``direction`` as {t, field, len, has, and -- with a fmt-1 trailer -- seq, ms,
    place, state, world, x, y, z, yaw, mode, flags, caps, model, valid (BlockValid)}, in tape order (re-sends included)."""
    out = []
    for r in records:
        if r.dir != direction:
            continue
        got = cp.parse_frame(r.payload)
        if got is None or got[0] != cp.TYPE_POS:
            continue
        d = cp.parse_pos_payload(got[1])
        if d is None:
            continue
        tr = d["trailer"]
        row = {"t": float(r.t), "field": d["field"], "len": d["length"], "has": tr is not None}
        if tr is not None:
            x, y, z = tr["pos"]
            row.update(seq=tr["seq"], ms=tr["ms"], place=tr["place"], state=tr["state"], world=tr["world"], x=x, y=y, z=z,
                       yaw=tr["yaw"], mode=tr["mode"], flags=tr["flags"], caps=tr["caps"], model=tr["model"],
                       valid=bool(tr["block_valid"]), digest=int(tr.get("digest") or 0))   # [ff9mapkit netsync s167] the digest
        out.append(row)
    return out


def seq_map(rows) -> dict:
    """seq -> the FIRST trailer row carrying it (a re-send repeats the same pose)."""
    out = {}
    for r in rows:
        if r.get("has") and r["seq"] not in out:
            out[r["seq"]] = r
    return out


def oracle_path(smap: dict, s: int, lag: int = RM_LAG_SEQ) -> list:
    """The tape's block-valid poses for seqs (s - lag .. s), oldest first (a gap in the seqs is skipped)."""
    pts = []
    for k in range(lag, -1, -1):
        r = smap.get(seq_back(s, k))
        if r is not None and r.get("valid"):
            pts.append((r["x"], r["z"]))
    return pts


def _steady_yaw(smap: dict, s: int, lag: int = RM_LAG_SEQ):
    """The tape's yaw over (s - lag .. s) when it held within YAW_STEADY and the pose moved (a straight leg), else None."""
    rows = [smap.get(seq_back(s, k)) for k in range(lag, -1, -1)]
    rows = [r for r in rows if r is not None and r.get("valid")]
    if len(rows) < 3:
        return None
    ys = [r["yaw"] for r in rows]
    moved = torus(rows[0]["x"], rows[0]["z"], rows[-1]["x"], rows[-1]["z"])
    if moved < 1.0 or max(_yaw_diff(y, ys[-1]) for y in ys) > YAW_STEADY:
        return None
    return ys[-1]


def judge_ghost_on_oracle(samples, smap: dict, *, min_samples: int = RM_MIN_SAMPLES, tol: float = RM_TOL, what: str = "the tape",
                          min_yaws: int | None = None) -> tuple:
    """(PURE) The ghost on ``smap`` (seq -> trailer row) by the cache's seq: on every judged sample the ghost shown (why_not null), its
    target (tx / tz) the oracle's pose at `lane.rx.seq` or up to TARGET_LAG_SEQ before it (TARGET_TOL), its eased (x, z) within ``tol``
    of the oracle's path over the last
    RM_LAG_SEQ seqs, and on a straight leg (the oracle's yaw steady) its yaw within YAW_TOL of it. ``samples`` already windowed."""
    if not any(cb.has(s, GHOST) for s in samples):
        return False, f"absent: no `{GHOST}` (nothing drawn: an engine before s166 A4)"
    js = [s for s in samples if judged(s)]
    bad, unseq, far, yaws, worst = [], [], [], 0, 0.0
    for s in js:
        g, seq = _ghost(s), _rx(s).get("seq")
        row = smap.get(seq) if isinstance(seq, int) and seq >= 0 else None
        if row is None or not row.get("valid"):
            unseq.append((s.frame, seq))
            continue
        gx, gz, tx, tz = (_num(g.get(k)) for k in ("x", "z", "tx", "tz"))
        why = []
        if g.get("shown") is not True or g.get("why_not") is not None:
            why.append(f"shown {g.get('shown')!r} why_not {g.get('why_not')!r}")
        cands = [smap.get(seq_back(seq, k)) for k in range(TARGET_LAG_SEQ + 1)]
        if None in (tx, tz) or not any(c is not None and c.get("valid") and torus(tx, tz, c["x"], c["z"]) <= TARGET_TOL for c in cands):
            why.append(f"target ({tx}, {tz}) vs the oracle's ({row['x']:.2f}, {row['z']:.2f}) at seq {seq} (or the {TARGET_LAG_SEQ} before)")
        dd = path_distance(gx, gz, oracle_path(smap, seq)) if None not in (gx, gz) else None
        if dd is None or dd > tol:
            why.append(f"eased ({gx}, {gz}) {dd if dd is None else round(dd, 2)} u off the path")
        worst = max(worst, dd or 0.0)
        steady = _steady_yaw(smap, seq)
        gy = _num(g.get("yaw"))
        if steady is not None:
            yaws += 1
            if gy is None or _yaw_diff(gy, steady) > YAW_TOL:
                why.append(f"yaw {gy} vs the walker's heading {steady:.1f}")
        if why:
            bad.append((s.frame, "; ".join(why)))
    judged_n = len(js) - len(unseq)
    min_yaws = MIN_YAWS if min_yaws is None else min_yaws
    # [W2 critic] the facing clause must RUN: a window with no straight leg judged no facing at all (A4's open issue -- does the body
    # face its travel? -- would pass unread), so at least MIN_YAWS straight-leg facings are judged
    ok = judged_n >= min_samples and not bad and len(unseq) <= max(2, len(js) // 10) and yaws >= min_yaws
    return ok, (f"{judged_n} sample(s) judged on {what} by seq (want >= {min_samples}); off {bad[:3] or 'none'} (the worst path "
                f"distance {worst:.2f} u, want <= {tol:g}); {yaws} straight-leg facing(s) judged (want >= {min_yaws}); samples whose "
                f"seq is not on {what}: "
                f"{len(unseq)} {unseq[:3] if unseq else ''}")


# ---- the windows off the tape
def world_live_t(rows):
    """The tape second the host's trailer first reads place 4 with its block valid (the host's world live), None."""
    return next((r["t"] for r in rows if r.get("has") and r.get("valid")), None)


def seam_crossings(rows) -> list:
    """Tape seconds where consecutive block-valid poses (a step under 64 u, torus) straddle the x seam (one x >= W - 64, one < 64)."""
    out, prev = [], None
    for r in rows:
        if not (r.get("has") and r.get("valid")):
            prev = None
            continue
        if prev is not None and torus(prev["x"], prev["z"], r["x"], r["z"]) < 64.0:
            a, b = prev["x"], r["x"]
            if (a >= W - 64.0 and b < 64.0) or (b >= W - 64.0 and a < 64.0):
                out.append(r["t"])
        prev = r
    return out


def pick_window(rows, length: float, *, after: float, move=None, avoid=(), step: float = 0.25) -> float | None:
    """(PURE) The first tape second T >= ``after`` where every trailer row in [T - 0.5, T + length + RECOVER_S] is block-valid with no
    jump of 64 u or more (no teleport, no load), clear of every ``avoid`` (start, end) by 1 s; with ``move`` (lo, hi) the host's
    displacement from T to T + length is in [lo, hi] (BH23: moving, yet under SnapJumpU). None when the tape has none."""
    valid = [r for r in rows if r.get("has")]
    if not valid:
        return None
    end_t = valid[-1]["t"]
    t = float(after)
    while t + length + RECOVER_S <= end_t:
        win = [r for r in valid if t - 0.5 <= r["t"] <= t + length + RECOVER_S]
        ok = bool(win) and all(r.get("valid") for r in win)
        if ok:
            ok = all(torus(a["x"], a["z"], b["x"], b["z"]) < 64.0 for a, b in zip(win, win[1:]))
        if ok and any(not (t + length + RECOVER_S + 1.0 <= a or b + 1.0 <= t) for a, b in avoid):
            ok = False
        if ok and move is not None:
            a = next((r for r in win if r["t"] >= t), None)
            b = next((r for r in reversed(win) if r["t"] <= t + length), None)
            disp = torus(a["x"], a["z"], b["x"], b["z"]) if a is not None and b is not None else -1.0
            ok = move[0] <= disp <= move[1]
        if ok:
            return round(t, 2)
        t += step
    return None


def plan_windows(rows) -> dict:
    """(PURE) The roam / freeze windows off a ROAM tape: {"after", "bh23", "bh6"} tape seconds (None = not found) -- after the host's
    world-live start + ROOM_S and past its seam crossing + SEAM_ROOM_S; the 2.3 s one moving (GAP_WINDOW_U), the 6 s one anywhere valid,
    apart."""
    live = world_live_t(rows)
    if live is None:
        return {"after": None, "bh23": None, "bh6": None}
    seams = [t for t in seam_crossings(rows) if t >= live]
    after = max(live + ROOM_S, (seams[0] + SEAM_ROOM_S) if seams else 0.0)
    bh23 = pick_window(rows, BH23_S, after=after, move=GAP_WINDOW_U)
    bh6 = pick_window(rows, BH6_S, after=after, avoid=((bh23, bh23 + BH23_S + RECOVER_S),) if bh23 is not None else ())
    return {"after": round(after, 2), "bh23": bh23, "bh6": bh6}


def roam_tape_facts(records, cp, *, header=None) -> dict:
    """THE ROAM TAPE's facts (PURE over the records; each rmN = {ok, why}) and its windows:
      rm1 PAIR   the host's first field 6603 held >= 10 s, no battle (world_tape_facts' w1)     rm2 STORY  the marker on the story lane (w2)
      rm3 V15    the host's frames speak wire 15 and its world frames carry fmt-1 trailers: block-valid on 9011, on foot (mode 0),
                 flags 0 (a host never follows)
      rm4 WALK   the block-valid poses walk >= 200 u in >= 3 moving legs separated by stands >= 2 s
      rm5 SEAM   a step across the x seam                         rm6 TILE   >= 15 s within 8 u of ICE_TILE
      rm7 ENTER  a field-300 record after the tile stand, held >= 8 s
    plus ``instrument`` (the header names a synthetic tape) and ``windows`` (plan_windows)."""
    base = pb.world_tape_facts(records, cp, field=FARSHORE)
    rows = trailer_rows(records, cp)
    out = {"rm1": base["w1"], "rm2": base["w2"], "instrument": bool((header or {}).get("instrument")),
           "rows": len(rows), "windows": plan_windows(rows)}
    wire = cp.tape_wire(records)
    vrows = [r for r in rows if r.get("has") and r.get("valid")]
    bad = [r for r in vrows if r["world"] != WORLD or r["mode"] != 0 or r["flags"] != 0]
    out["rm3"] = {"ok": wire == WIRE_NEW and bool(vrows) and not bad,
                  "why": (f"the host's frames speak wire {wire} (want {WIRE_NEW}: a ROAM tape is recorded on the s166 host)" if wire != WIRE_NEW
                          else "no block-valid fmt-1 trailer (a capless host)" if not vrows else
                          f"a trailer off-shape at tape {bad[0]['t']:.2f} s (world {bad[0]['world']}, mode {bad[0]['mode']}, flags "
                          f"{bad[0]['flags']})" if bad else f"{len(vrows)} block-valid trailer(s) on {WORLD}, on foot, flags 0")}
    walk, legs, in_leg, still_since = 0.0, 0, False, None
    for a, b in zip(vrows, vrows[1:]):
        d = torus(a["x"], a["z"], b["x"], b["z"])
        if d >= 64.0:                                      # a teleport: never a walk
            in_leg, still_since = False, None
            continue
        if d > 0.05:
            walk += d
            if not in_leg:
                legs += 1
            in_leg, still_since = True, None
        elif in_leg:
            still_since = a["t"] if still_since is None else still_since
            if b["t"] - still_since >= 2.0:               # a stand of 2 s ends the leg (a re-send inside a leg does not)
                in_leg = False
    out["rm4"] = {"ok": walk >= ROAM_TAPE_MIN["walk_u"] and legs >= ROAM_TAPE_MIN["legs"],
                  "why": f"walked {walk:.0f} u in {legs} leg(s) (want >= {ROAM_TAPE_MIN['walk_u']:g} u in >= {ROAM_TAPE_MIN['legs']})"}
    seams = seam_crossings(rows)
    out["rm5"] = {"ok": bool(seams), "why": f"the x seam crossed at tape {seams[:2]}" if seams else "no step across the x seam"}
    tile = [r for r in vrows if torus(r["x"], r["z"], *ICE_TILE) <= 8.0]
    span = (tile[-1]["t"] - tile[0]["t"]) if len(tile) >= 2 else 0.0
    out["rm6"] = {"ok": span >= ROAM_TAPE_MIN["tile_s"], "why": f"at ICE_TILE {span:.1f} s (want >= {ROAM_TAPE_MIN['tile_s']:g})"}
    f300 = [r for r in rows if r["field"] == ICE_CAVERN and (not tile or r["t"] > tile[-1]["t"])]
    held = (f300[-1]["t"] - f300[0]["t"]) if len(f300) >= 2 else 0.0
    out["rm7"] = {"ok": held >= ROAM_TAPE_MIN["enter_s"], "why": f"field {ICE_CAVERN} held {held:.1f} s after the tile (want >= "
                                                                   f"{ROAM_TAPE_MIN['enter_s']:g})"}
    return out


def facts_ok(f: dict) -> tuple:
    bad = [f"{k}: {f[k]['why']}" for k in ("rm1", "rm2", "rm3", "rm4", "rm5", "rm6", "rm7") if not f[k]["ok"]]
    return not bad, bad


# ---- THE INSTRUMENT (a synthetic v15 host from ROAM_PLAN, through coop_peer's real codec)
def plan_poses(plan=ROAM_PLAN, start=FS_LANDING, ups: float = INSTRUMENT_UPS, hz: float = INSTRUMENT_HZ) -> list:
    """(PURE) ROAM_PLAN's world phase as (dt from the world-live start, kind, x, z, yaw) at ``hz`` -- kind 'world' on 9011 ('stand' /
    'walk' / 'tile' / 'turn'), then 'enter' (the fade) and 'field' (300). The yaw is the walker's HEADING (WalkerYaw: travel + 180, the
    engine's transform.rotation -- never coop_peer's old travel heading)."""
    out, t, x, z, heading = [], 0.0, float(start[0]), float(start[1]), BW.ww_walker_yaw(0.0, -1.0)
    step = 1.0 / hz

    def emit(seconds, kind, px, pz):
        nonlocal t
        n = max(1, int(round(seconds * hz)))
        for _ in range(n):
            out.append((round(t, 4), kind, px, pz, heading))
            t += step
    for item in plan:
        op = item[0]
        if op == "stand":
            emit(item[1], "world" if not out or out[-1][1] in ("world",) else "field", x, z)
        elif op == "turn":
            emit(0.5, "world", x, z)
        elif op == "walk":
            bearing, dist = float(item[1]), float(item[2])
            dx, dz = math.cos(math.radians(bearing)), math.sin(math.radians(bearing))
            heading = BW.ww_walker_yaw(dx, dz)
            n = max(1, int(round(dist / ups * hz)))
            for i in range(1, n + 1):
                k = i / n
                px, pz = cp_wrap(x + dx * dist * k, z + dz * dist * k)
                out.append((round(t, 4), "world", px, pz, heading))
                t += step
            x, z = cp_wrap(x + dx * dist, z + dz * dist)
        elif op == "tile":
            x, z = float(item[1][0]), float(item[1][1])
            emit(step, "world", x, z)
        elif op == "enter":
            emit(1.0, "enter", x, z)
    return out


def cp_wrap(x: float, z: float) -> tuple:
    """coop_peer.torus_wrap (RealPosition's fold: x in [0, 1536), z in (-1280, 0])."""
    xw = float(x) % W
    xw = 0.0 if xw >= W else xw                            # a -1e-14 folds to W itself in floating point
    zw = -((-float(z)) % H)
    zw = 0.0 if zw <= -H else zw
    return xw, (0.0 if zw == 0.0 else zw)


def roam_instrument_tape(cp, *, plan=ROAM_PLAN, field_s: float = INSTRUMENT_FIELD_S, load_s: float = INSTRUMENT_LOAD_S,
                         hz: float = INSTRUMENT_HZ, caps=None, digest: int = 0, fp_comps=None) -> list:
    """THE INSTRUMENT (PURE: records): a SYNTHETIC v15 host shaped like the ROAM tape -- the host on 6603 ``field_s`` (type 0 field live,
    place 1; type 5 its story with the marker and the exit's arrival pose, section 7 on-field), its exit fade (place 2), its own all-block
    load (ONE place-3 frame, then the writer's RE-SENDS byte-identical for ``load_s``, section 7's b6 riding with the heartbeat frozen),
    ROAM_PLAN on 9011 (place 4, state control + visible, the block: world 9011, the pose, WalkerRotation of the heading, mode 0, model 310,
    flags 0 -- a host never follows; section 0 tracking the pose), the Confirm's fade, field 300. Every frame through coop_peer's codec at
    wire 15. NOT a recording: no terrain (y 0), no clip (anim 0), no camera (the L1 turn is a stand) -- named on every row that runs on it.
    [ff9mapkit netsync s167] ``caps`` (default s166's 0x0001): an s167 host's 0x0003 carries ``digest`` on its place-4 trailers
    (FpTxDigestRule) and, with ``fp_comps``, section 11 between sections 0 and 7 of its world-phase state frames (FpSectionSendRule: its
    live world, a nonzero digest) -- round B's walk leg passes the GUEST's own fingerprint, so this host is "of the same install"."""
    R = cp.Record
    caps = cp.CAP_WORLD_POSE if caps is None else int(caps)
    fp_on = bool(caps & cp.CAP_WORLD_FP) and int(digest) != 0
    base = bytearray(2048)
    base[pb.MARKER_BYTE] = pb.MARKER_VALUE
    recs, hb, seq = [], [0], [0]
    dt = 1.0 / hz
    on_field = BW.HF_ON_FIELD | BW.HF_CONTROL
    on_world = BW.HF_WORLD | BW.HF_MENU | BW.HF_CONTROL

    def pos(field, place, state, *, world=0, xyz=(0.0, 0.0, 0.0), yaw=None, frozen=False):
        if not frozen:
            seq[0] = (seq[0] + 1) & 0xFFFF
        fields = dict(caps=caps, seq=seq[0], ms=int(round(t * 1000.0)) & 0xFFFFFFFF, place=place, state=state, world=world,
                      pos=xyz, rot=BW.ww_walker_rotation(yaw) if yaw is not None else (0.0, 0.0, 0.0, 0.0), mode=0,
                      model=310 if place == cp.PLACE_WORLD else 0, world_tps=20, flags=0,
                      digest=int(digest) if fp_on and place == cp.PLACE_WORLD else 0)   # [ff9mapkit netsync s167]
        record = cp.build_pos_payload(field, rot=(0.0, 0.0, 0.0, 1.0), anim_frame=0, frame_n=0)
        return cp.build_frame(cp.TYPE_POS, record + cp.build_world_trailer(**cp.world_block_zeroed(fields)), wire=WIRE_NEW)

    def state(story, flags, fld, beat=True, live_world=False):
        if beat:
            hb[0] = (hb[0] + 1) & 0xFFFF
        sec = BW.append_section(b"", BW.SECTION_STORY, story)
        if live_world and fp_on and fp_comps is not None:
            sec += cp.fp_section_bytes(WORLD, fp_comps)    # [ff9mapkit netsync s167] section 11, between 0 and 7 (8 stays last)
        return cp.build_frame(cp.TYPE_STATE, BW.append_section(sec, BW.SECTION_DIALOG, BW.dialog_section(0x0166, hb[0], flags, 0, fld)),
                              wire=WIRE_NEW)
    fs = cp.story_with_pose(*FS_LANDING, yaw=90.0, idx=11, base=bytes(base))
    t, n = 1.0, 0
    while t < 1.0 + field_s:                               # 6603, field live
        recs.append(R(t, 0, pos(FARSHORE, cp.PLACE_FIELD, cp.ST_CONTROL)))
        if n % 3 == 0:
            recs.append(R(t, 0, state(fs, on_field, FARSHORE)))
        t, n = t + dt, n + 1
    end = t + 0.6                                          # the exit's fade (still the field's record)
    while t < end:
        recs.append(R(t, 0, pos(FARSHORE, cp.PLACE_TRANSITION, 0)))
        t += dt
    load = pos(0, cp.PLACE_WORLD_LOADING, 0)               # the world's first Update, then its sync load: the writer re-sends it
    st_load = state(fs, on_world, 0)
    end = t + load_s
    k = 0
    while t < end:
        recs.append(R(t, 0, load))
        if k % 3 == 0:
            recs.append(R(t, 0, st_load))
        t, k = t + dt, k + 1
    t0 = t
    last = None
    for i, (rel, kind, x, z, yaw) in enumerate(plan_poses(plan, hz=hz)):
        t = t0 + rel
        if kind == "world":
            recs.append(R(t, 0, pos(0, cp.PLACE_WORLD, cp.ST_CONTROL | cp.ST_VISIBLE, world=WORLD, xyz=(x, 0.0, z), yaw=yaw)))
            last = cp.story_with_pose(x, z, yaw=yaw, idx=11, base=bytes(base))   # section 0's facing byte = the heading
            if i % 3 == 0:
                recs.append(R(t, 0, state(last, on_world, 0, live_world=True)))
        elif kind == "enter":
            recs.append(R(t, 0, pos(0, cp.PLACE_TRANSITION, 0)))
            if i % 3 == 0:
                recs.append(R(t, 0, state(last or fs, on_world, 0)))
        else:
            recs.append(R(t, 0, pos(ICE_CAVERN, cp.PLACE_FIELD, cp.ST_CONTROL)))
            if i % 3 == 0:
                recs.append(R(t, 0, state(last or fs, on_field, ICE_CAVERN)))
    return recs


INSTRUMENT_HEADER = {"instrument": "roam", "synthetic": True,
                     "note": "THE INSTRUMENT: a SYNTHETIC v15 host built from coop_world_walk_t2.ROAM_PLAN through coop_peer's codec -- "
                             "NOT COOP_TAPE_WORLD_ROAM (owner-gated: ROAM-TAPE.md); no terrain, no clip, no camera"}


def write_instrument(path, cp=None, **kw) -> Path:
    """Write THE INSTRUMENT to ``path`` through coop_peer's own TapeWriter (its header records the wire from the frames). [ff9mapkit netsync
    s167] ``kw``: roam_instrument_tape's caps / digest / fp_comps (an s167-shaped host; the header names its caps and digest)."""
    cp = cp or pb.coop_peer_module()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    extra = dict(INSTRUMENT_HEADER)
    if kw:
        extra.update(stage="s167", caps=int(kw.get("caps") or cp.CAP_WORLD_POSE), digest=f"0x{int(kw.get('digest') or 0):08X}",
                     calibrated=kw.get("fp_comps") is not None)
    tw = cp.TapeWriter(path, mode="instrument", extra=extra)
    try:
        for r in roam_instrument_tape(cp, **kw):
            tw.write(r.dir, r.payload, t=r.t)
    finally:
        tw.close()
    return path


def roam_tape_dir() -> Path:
    """COOP_TAPE_DIR, else <the MAIN repo>/.harness-runs/coop-tapes/world-roam (the ROAM tape's own home)."""
    env = os.environ.get("COOP_TAPE_DIR", "").strip()
    return Path(env).expanduser().resolve() if env else pb.main_repo() / ".harness-runs" / "coop-tapes" / "world-roam"


def roam_tape() -> tuple:
    """(path or None, how): COOP_TAPE_WORLD_ROAM, else the ROAM dir's pointer, else its newest ``*-world-roam-*.f9tape``; None = not
    recorded (the leg then builds THE INSTRUMENT into its run dir)."""
    env = os.environ.get("COOP_TAPE_WORLD_ROAM", "").strip()
    if env:
        return Path(env).expanduser().resolve(), "COOP_TAPE_WORLD_ROAM"
    d = roam_tape_dir()
    try:
        p = Path(json.loads((d / ROAM_POINTER).read_text(encoding="utf-8"))["tape"])
        if p.exists():
            return p, f"{ROAM_POINTER}"
    except (OSError, ValueError, KeyError, TypeError):
        pass
    tapes = sorted(d.glob("*-world-roam-*.f9tape"), key=lambda p: p.stat().st_mtime) if d.is_dir() else []
    return (tapes[-1], "the newest in the ROAM dir") if tapes else (None, f"none recorded ({d})")


# ================================================================================================ pure judges: the wire
_GUEST_WIRE = re.compile(r"^guest header: wire (\d+|none) -- the replay sends wire (\d+) \((.*)\)$")
_HOST_WIRE = re.compile(r"^host header: wire (\d+) -- this fake guest sends wire (\d+) \((.*)\)$")


def wire_line(text: str | None, side: str = "guest"):
    """coop_peer's wire line -> (game, send, how) or None."""
    m = (_GUEST_WIRE if side == "guest" else _HOST_WIRE).search(text or "")
    if not m:
        return None
    return (None if m.group(1) == "none" else int(m.group(1))), int(m.group(2)), m.group(3)


def judge_live_header(text: str | None, probe, *, want_send=None, side: str = "guest") -> tuple:
    """THE LIVE HEADER (PURE): coop_peer's own wire line present, the game's header the probe's `netsync.wire` (when read), and the
    send version ``want_send`` (None: the game's own -- a match). A mismatch asked for (A-WIRE's `--wire tape`) passes only as asked."""
    got = wire_line(text, side)
    if got is None:
        return False, f"no {side}-header wire line on the peer log (probe netsync.wire {probe!r}) -- the instrument never learnt the wire"
    game, send, how = got
    want = game if want_send is None else want_send
    ok = game is not None and (probe is None or probe == game) and send == want
    return ok, (f"the game's header speaks {game}, coop_peer sends {send} ({how}); probe {probe!r}; want send {want}"
                + ("" if ok else " -- WIRE MISMATCH THE LEG DID NOT ASK FOR: it cannot judge"))


def raw_line(x) -> str:
    """An engine line as Memoria.log wrote it: a parsed (datetime, level, msg) from _coop_peer_bench.EngineLog back to its text."""
    if isinstance(x, tuple) and len(x) == 3:
        return f"{x[0]:%d.%m.%Y %H:%M:%S} |{x[1]}| {x[2]}"
    return str(x)


def parsed(lines) -> list:
    """Engine lines (raw text or EngineLog tuples) as EngineLog's (datetime, level, msg) -- what _coop_peer_bench.hits reads."""
    out = []
    for ln in lines:
        p = ln if isinstance(ln, tuple) and len(ln) == 3 else pb.parse_engine_line(str(ln))
        if p is not None:
            out.append(p)
    return out


def _paired(lines) -> list:
    return pb.hits(parsed(lines), "paired") + pb.hits(parsed(lines), "armed")


def judge_wire_nopair(samples, lines) -> tuple:
    """S166-WIRE-NOPAIR (PURE over the unrestamped window): no paired / ARMED line, never mirroring, FieldHUD 6603 on every sample, the
    receiver cache never fed (`lane.rx.kind` null, `arrival_age_ms` -1 and `lane.rx.samples` 0 -- absent on an engine before A3: that
    engine cannot show it). [W2 critic] `rx.samples` alone could not fail: it counts SEQ MOVES, and a capless (restamped v14) host never
    moves one -- a cache fed by a paired capless host still reads 0; `rx.kind` turns 'absent' on its first frame (the cache's Has)."""
    pl = _paired(lines)
    mir = [s.frame for s in samples if cw._s(s, "mirroring") is True]
    off = [(s.ui_state, s.field_id) for s in samples if not (s.ui_state == "FieldHUD" and s.field_id == FARSHORE)]
    fed = [s.frame for s in samples if (_num(_rx(s).get("samples")) or 0) > 0 or _rx(s).get("kind") is not None
           or (_num(_lane(s).get("arrival_age_ms")) is not None and _num(_lane(s).get("arrival_age_ms")) >= 0)]
    lane = any(cb.has(s, LANE) for s in samples)
    ok = bool(samples) and not pl and not mir and not off and not fed and lane
    return ok, (f"{len(samples)} sample(s); paired / ARMED lines {pb.show(pl, 1) if pl else 'none'}; mirroring on {mir[:3] or 'none'}; "
                f"off 6603 {off[:3] or 'none'}; the cache fed on {fed[:3] or 'none'}" + ("" if lane else f"; absent: no `{LANE}`"))


def judge_wire_reject(base, samples, lines, *, peer: int = WIRE_OLD, own: int = WIRE_NEW) -> tuple:
    """S166-WIRE-REJECT (PURE): `wire_peer.rejected` never falls and rises >= WIRE_REJECT_MIN over the window, last_version ``peer``,
    `lines` +1 and the log's peer-wire line exactly once, `mismatch` true with the words on every sample after the first refusal, and
    `world.line` asked 'mismatch' with the words, drawn, on the last sample."""
    if not any(cb.has(s, WIRE_PEER) for s in samples):
        return False, f"absent: no `{WIRE_PEER}` (an engine before s166 A2)"
    rej = [_num(_wp(s).get("rejected")) for s in samples]
    rej = [r for r in rej if r is not None]
    falls = [(a, b) for a, b in zip(rej, rej[1:]) if b < a]
    d = _d(base, samples[-1], _wp, "rejected")
    after = [s for s in samples if (_num(_wp(s).get("rejected")) or 0) > (_num(_wp(base).get("rejected")) or 0)]
    words = [s.frame for s in after if not (_wp(s).get("mismatch") is True and _wp(s).get("words") == BW.WORDS_WIRE_MISMATCH)]
    last = samples[-1]
    ln = _line(last)
    n_line = cb.count(lines, BW.log_peer_wire(peer, own))
    dl = _d(base, last, _wp, "lines")
    ok = (d is not None and d >= WIRE_REJECT_MIN and not falls and _wp(last).get("last_version") == peer and dl == 1 and n_line == 1
          and bool(after) and not words and ln.get("asked") == "mismatch" and ln.get("text") == BW.WORDS_WW_WIRE_MISMATCH
          and ln.get("drawn") is True)
    return ok, (f"rejected +{d} (want >= {WIRE_REJECT_MIN}, never falling: {falls[:2] or 'ok'}), last_version "
                f"{_wp(last).get('last_version')!r} (want {peer}); lines +{dl} and the log line {n_line}x (want 1 each); the words off on "
                f"{words[:3] or 'no'} sample(s) after the first refusal; world.line {ln.get('asked')!r} drawn {ln.get('drawn')!r}")


def judge_wire_clear(samples, lines, words_window: int) -> tuple:
    """S166-WIRE-CLEAR (PURE over the `--wire 15` window): the mismatch words were up at its start, gone (`mismatch` false, `world.line`
    no longer 'mismatch') on the samples from ``words_window`` on (WIRE_CLEAR_S after its first frame), and the guest paired (a paired
    line, or mirroring)."""
    if not any(cb.has(s, WIRE_PEER) for s in samples):
        return False, f"absent: no `{WIRE_PEER}`"
    late = samples[words_window:] if words_window < len(samples) else []
    stuck = [s.frame for s in late if _wp(s).get("mismatch") is True or _line(s).get("asked") == "mismatch"]
    paired = bool(pb.hits(parsed(lines), "paired")) or any(cw._s(s, "mirroring") is True for s in samples)
    ok = bool(late) and not stuck and paired
    return ok, (f"{len(late)} sample(s) past WIRE_CLEAR_S; the words still up on {stuck[:3] or 'none'}; paired "
                f"{'yes' if paired else 'NO'}")


def wire_lever_measured(samples, lines, world_samples) -> tuple:
    """`--wire 15`'s shape (PURE): it pairs (s165 behaviour), rejected +0 over the window, the cache reads the capless host (`rx.kind`
    'absent'), and -- when the guest reached the world map -- the ghost's why_not 'no_record' on a judged sample."""
    paired = bool(pb.hits(parsed(lines), "paired")) or any(cw._s(s, "mirroring") is True for s in samples)
    rej = [_num(_wp(s).get("rejected")) for s in samples if _num(_wp(s).get("rejected")) is not None]
    flat = bool(rej) and rej[-1] == rej[0]
    capless = any(_rx(s).get("kind") == "absent" for s in samples + list(world_samples))
    nr = [s for s in world_samples if judged(s) and _ghost(s).get("why_not") == "no_record"]
    ok = paired and flat and capless and (bool(nr) or not world_samples)
    return ok, (f"paired {paired}, rejected flat {flat}, rx 'absent' {capless}, why_not no_record on {len(nr)} world sample(s) "
                f"({len(world_samples)} read)")


# ================================================================================================ pure judges: T2-A old
def judge_old_wire(text: str | None) -> tuple:
    """S166-OLD-WIRE (PURE): the replay's wire line -- a v15 guest 'restamped from the tape's 14' (sends 15), a v14 guest 'as recorded'."""
    got = wire_line(text)
    if got is None:
        return False, "no guest-header wire line"
    game, send, how = got
    if game == WIRE_NEW:
        ok = send == WIRE_NEW and f"restamped from the tape's {WIRE_OLD}" in how
    else:
        ok = game == WIRE_OLD and send == WIRE_OLD and how.startswith("as recorded")
    return ok, f"guest {game}, sends {send} ({how})"


def judge_old_dormant(samples, lines) -> tuple:
    """S166-OLD-DORMANT (PURE over the whole replay): on an s166 guest round A stays dormant on a capless host -- `wire_peer.rejected`
    flat, `lane.rx.kind` 'absent' (or unset) and `caps.peer` 0 / -1 on every sample, no lane line, the ghost never shown, why_not
    'no_record' on the judged world samples ('not_live' only through its own transitions), `world.line` never asked. An engine before
    A3: dormant by construction (green: the design's 'green on v14')."""
    if not any(cb.has(s, LANE) for s in samples):
        return True, "an engine before A3 (no `netsync.world.lane`): round A dormant by construction -- the design's 'green on v14'"
    rej = [_num(_wp(s).get("rejected")) for s in samples if _num(_wp(s).get("rejected")) is not None]
    kinds = sorted({str(_rx(s).get("kind")) for s in samples})
    caps = sorted({_num((_lane(s).get("caps") or {}).get("peer")) for s in samples} - {None})
    lanes = ww.lane_lines(lines)
    shown = [s.frame for s in samples if _ghost(s).get("shown") is True]
    worlds = [s for s in samples if judged(s)]
    whys = sorted({str(_ghost(s).get("why_not")) for s in worlds})
    asked = sorted({str(_line(s).get("asked")) for s in samples} - {"None"})
    # [W2 critic] the instrument: the cache FED by the capless host on some sample (rx.kind 'absent', caps.peer 0) -- every other clause
    # also holds for a guest whose cache never saw a frame (kind null, caps -1: the sentinels), so without it DORMANT could not fail
    fed = any(_rx(s).get("kind") == "absent" and _num((_lane(s).get("caps") or {}).get("peer")) == 0 for s in samples)
    ok = ((not rej or rej[-1] == rej[0]) and set(kinds) <= {"None", "absent"} and set(caps) <= {0, -1} and not lanes and not shown
          and (not worlds or ("no_record" in whys and set(whys) <= {"no_record", "not_live"})) and not asked and fed)
    return ok, (f"the cache fed by the capless host: {'yes' if fed else 'NO (never read kind absent / caps 0)'}; "
                f"rejected {rej[:1]}..{rej[-1:]}; rx kinds {kinds}; peer caps {caps}; lane lines {ww._names(lanes) or 'none'}; shown "
                f"on {shown[:3] or 'none'}; {len(worlds)} judged world sample(s), why_not {whys}; world.line asked {asked or 'never'}")


# ================================================================================================ pure judges: roam / freeze
def window_lane(lines) -> list:
    return ww.lane_lines(lines)


def judge_rm_instrument(pre_exit_lines, samples) -> tuple:
    """S166-RM-I (PURE): paired AND ARMED before the host's exit; a judged sample on 9011 (the follow-out's landing); frozen there
    (`world.freeze.on`); the ghost WANTED on a judged sample."""
    pl, al = pb.hits(parsed(pre_exit_lines), "paired"), pb.hits(parsed(pre_exit_lines), "armed")
    land = wf.first_judged([s for s in samples if s.ui_state == "WorldHUD"])
    world = [s for s in samples if judged(s) and s.world_id == WORLD]
    frozen = [s for s in world if ww.frozen(s)]
    wanted = [s for s in world if _ghost(s).get("want") is True]
    ok = bool(pl) and bool(al) and land is not None and bool(world) and len(frozen) == len(world) and bool(wanted)
    return ok, (f"paired {len(pl)}x, ARMED {len(al)}x before the exit; landed {'at frame ' + str(land.frame) if land else 'NEVER'}; "
                f"{len(world)} judged sample(s) on {WORLD}, frozen on {len(frozen)}; the ghost wanted on {len(wanted)}")


def judge_bh23(base, win, rec, lines, smap, length_ms: int = int(BH23_S * 1000)) -> tuple:
    """S166-RM-BH23 (PURE over the blackhole's samples ``win`` and its recovery ``rec``, the lane lines between them): ONE gap_start and
    ONE gap_end, its end naming ``length_ms`` within GAP_LEN_TOL, no hang / load / cut line; the ghost shown on every judged sample of
    both (hides +0), stood (`stall` 'stand') inside the blackhole; snaps +0 (an ease back, never a snap); and within EASE_BACK_S after the
    gap's end on the tape's path again (RM_TOL)."""
    if not any(cb.has(s, GHOST) for s in list(win) + list(rec)):
        return False, f"absent: no `{GHOST}`"
    names = window_lane(lines)
    starts = [x for x in names if x[1] == "gap_start"]
    ends = [x for x in names if x[1] == "gap_end"]
    other = [x[1] for x in names if x[1] in ("hang_start", "load_start", "hang_cut", "hang_end", "load_end")]
    length = ends[0][2] if ends else None
    js = [s for s in list(win) + list(rec) if judged(s)]
    hidden = [s.frame for s in js if _ghost(s).get("shown") is not True]
    stood = any(_ghost(s).get("stall") == "stand" for s in win if judged(s))
    last = js[-1] if js else None
    dh, ds = _d(base, last, _ghost, "hides"), _d(base, last, _ghost, "snaps")
    back = [s for s in rec if judged(s)]
    tail = back[len(back) // 2:] if back else []
    off = []
    for s in tail:
        g, seq = _ghost(s), _rx(s).get("seq")
        dd = path_distance(_num(g.get("x")), _num(g.get("z")), oracle_path(smap, seq)) if isinstance(seq, int) and None not in (
            _num(g.get("x")), _num(g.get("z"))) else None
        if dd is None or dd > RM_TOL:
            off.append((s.frame, dd if dd is None else round(dd, 2)))
    ok = (len(starts) == 1 and len(ends) == 1 and length is not None and abs(length - length_ms) <= GAP_LEN_TOL and not other
          and not hidden and stood and dh == 0 and ds == 0 and bool(tail) and not off)
    return ok, (f"gap lines {len(starts)} / {len(ends)} (want 1 / 1), the end naming {length} ms (want {length_ms} +- {GAP_LEN_TOL}); "
                f"other lane lines {other or 'none'}; hidden on {hidden[:3] or 'none'}; stood {stood}; hides +{dh}, snaps +{ds} "
                f"(want 0 / 0); eased back: {len(tail)} late recovery sample(s), off the path {off[:3] or 'none'}")


def judge_bh6(base, win, rec) -> tuple:
    """S166-RM-BH6 (PURE): never hidden while the cache's seq age is under HIDE_MS - 200; hidden 'stale' (want false) at a seq age in
    [HIDE_MS, HIDE_MS + HIDE_SLACK_MS]; after it re-shown with snaps +1 (a first show)."""
    if not any(cb.has(s, GHOST) for s in list(win) + list(rec)):
        return False, f"absent: no `{GHOST}`"
    js = [s for s in win if judged(s)]
    early = [s.frame for s in js if (_num(_lane(s).get("seq_age_ms")) or 0) < HIDE_MS - 200 and _ghost(s).get("shown") is not True]
    hid = next((s for s in js if _ghost(s).get("shown") is False and _ghost(s).get("why_not") == "stale"), None)
    age = _num(_lane(hid).get("seq_age_ms")) if hid is not None else None
    back = next((s for s in rec if judged(s) and _ghost(s).get("shown") is True), None)
    ds = _d(base, back, _ghost, "snaps") if back is not None else None
    ok = (not early and hid is not None and age is not None and HIDE_MS <= age <= HIDE_MS + HIDE_SLACK_MS
          and _ghost(hid).get("want") is False and back is not None and ds == 1)
    return ok, (f"hidden early on {early[:3] or 'none'}; hidden 'stale' at seq age {age} (want {HIDE_MS}-{HIDE_MS + HIDE_SLACK_MS}); "
                f"re-shown {'yes' if back is not None else 'NO'}, snaps +{ds} (want 1: a first show)")


def judge_t2_freeze(base, win, rec, lines, length_ms: int, *, hide: bool) -> tuple:
    """S166-FZ-23 / S166-FZ-6 (PURE over the freeze's samples ``win``, its recovery ``rec`` and the lane / world lines between them).
    Both: the ghost's target held (one pose through the window), the eased pose on it within HOLD_TOL from a seq age of STAND_MS +
    STAND_SLACK_MS, the first `stall` 'stand' at a seq age in [STAND_MS, STAND_MS + STAND_SLACK_MS] with `anim` 'stand' and `clip` its
    `stand`; ONE hang_start ('not updating') and no gap / load / cut line; its end one hang_end naming ``length_ms`` within HANG_LEN_TOL.
    ``hide`` False (2.3 s): never hidden, `world.line` never 'lost'. ``hide`` True (6 s): hidden 'stale' at a seq age in [HIDE_MS,
    HIDE_MS + HIDE_SLACK_MS], `world.line` asked 'lost' with the words AND drawn (a client on the world map; its session never dropped:
    the re-sends keep it Valid), the lost line logged once and its over line once, re-shown after with snaps +1."""
    if not any(cb.has(s, GHOST) and cb.has(s, LINE) for s in list(win) + list(rec)):
        return False, f"absent: no `{GHOST}` / `{LINE}`"
    js = [s for s in win if judged(s)]
    why = []
    targets = {(round(_num(_ghost(s).get("tx")) or 0.0, 2), round(_num(_ghost(s).get("tz")) or 0.0, 2)) for s in js
               if _ghost(s).get("placed") is True and (_num(_lane(s).get("seq_age_ms")) or 0) >= 200}
    if len(targets) > 1:
        why.append(f"the target moved in the freeze ({sorted(targets)[:3]})")
    held = [s for s in js if _ghost(s).get("placed") is True and (_num(_ghost(s).get("seq_age_ms")) or 0) >= STAND_MS + STAND_SLACK_MS]
    drift = [torus(_ghost(s)["x"], _ghost(s)["z"], _ghost(s)["tx"], _ghost(s)["tz"]) for s in held
             if None not in (_num(_ghost(s).get(k)) for k in ("x", "z", "tx", "tz"))]
    if not held or len(drift) < len(held) or max(drift) > HOLD_TOL:
        why.append(f"the hold: {len(held)} held sample(s), drift {max(drift) if drift else None} (want <= {HOLD_TOL:g})")
    first = next((s for s in js if _ghost(s).get("stall") == "stand"), None)
    fg = _ghost(first)
    f_age = _num(fg.get("seq_age_ms"))
    if first is None or f_age is None or not (STAND_MS <= f_age <= STAND_MS + STAND_SLACK_MS) or fg.get("anim") != "stand" \
            or fg.get("clip") != fg.get("stand") or fg.get("stand") is None:
        why.append(f"the stand: first at seq age {f_age}, anim {fg.get('anim')!r}, clip {fg.get('clip')!r} vs {fg.get('stand')!r}")
    names = ww._names(window_lane(lines))
    if names.count("hang_start") != 1 or any(n in names for n in ("gap_start", "gap_end", "load_start", "hang_cut", "load_end")):
        why.append(f"the lane lines {names} (want one hang_start 'not updating', no gap / load / cut)")
    ends = [x for x in window_lane(lines) if x[1] == "hang_end"]
    if len(ends) != 1 or ends[0][2] is None or abs(ends[0][2] - length_ms) > HANG_LEN_TOL:
        why.append(f"the hang's end {[(n, ln) for _r, n, ln, _t in ends]} (want one naming {length_ms} +- {HANG_LEN_TOL})")
    lost = [s for s in js if _line(s).get("asked") == "lost"]
    if not hide:
        hidden = [s.frame for s in js if _ghost(s).get("shown") is not True]
        if hidden or lost or cb.count(lines, BW.LOG_WW_LINE_LOST):
            why.append(f"hidden on {hidden[:3] or 'none'}, 'lost' asked on {len(lost)} sample(s) (want none at {length_ms} ms)")
    else:
        hid = next((s for s in js if _ghost(s).get("shown") is False and _ghost(s).get("why_not") == "stale"), None)
        h_age = _num(_lane(hid).get("seq_age_ms")) if hid is not None else None
        if hid is None or h_age is None or not (HIDE_MS <= h_age <= HIDE_MS + HIDE_SLACK_MS):
            why.append(f"the hide: 'stale' at seq age {h_age} (want {HIDE_MS}-{HIDE_MS + HIDE_SLACK_MS})")
        lt = _line(lost[0]) if lost else {}
        if not lost or lt.get("text") != BW.WORDS_WW_LOST_CONTACT or any(_line(s).get("drawn") is not True for s in lost):
            why.append(f"the line: 'lost' on {len(lost)} sample(s), text {lt.get('text')!r}, drawn {[_line(s).get('drawn') for s in lost[:2]]}")
        if cb.count(lines, BW.LOG_WW_LINE_LOST) != 1 or cb.count(lines, BW.LOG_WW_LINE_LOST_OVER) != 1:
            why.append(f"the lost lines {cb.count(lines, BW.LOG_WW_LINE_LOST)}x / over {cb.count(lines, BW.LOG_WW_LINE_LOST_OVER)}x "
                       "(want 1 / 1)")
        back = next((s for s in rec if judged(s) and _ghost(s).get("shown") is True), None)
        ds = _d(base, back, _ghost, "snaps") if back is not None else None
        if back is None or ds != 1:
            why.append(f"re-shown {'yes' if back is not None else 'NO'}, snaps +{ds} (want 1)")
    return not why, ("; ".join(why) or "held, stood by ~300 ms, the hang worded 'not updating' and its end on the sender's span"
                     + (", hidden at 5 s with the drawn line, re-shown with a snap" if hide else ", never hidden")) + \
        f" ({len(js)} judged sample(s); lane lines {names})"


def lanegap_measured(base, last, lines, counter: str = "gaps") -> bool:
    """`lanegap off`'s shape (PURE): the counter moved and no lane line."""
    return (_d(base, last, _lane, counter) or 0) >= 1 and not window_lane(lines)


def ghost_off_measured(samples) -> bool:
    """`ghost off`'s shape (PURE): want true and shown false on a judged sample, never shown."""
    js = [s for s in samples if judged(s)]
    return any(_ghost(s).get("want") is True and _ghost(s).get("shown") is False for s in js) and \
        not any(_ghost(s).get("shown") is True for s in js)


# ================================================================================================ pure judges: T2-H
def _first_index(samples, pred):
    return next((i for i, s in enumerate(samples) if pred(s)), None)


def _after_scene(samples) -> list:
    """(PURE) ``samples`` less the first SCENE_SETTLE samples after each scene window (any other refusal hides the ghost and resets its
    motion: the re-show is a first show -- its first frames are judged by the next sample, not this one)."""
    out, skip, prev_scene = [], 0, False
    for s in samples:
        sc = bool((_num(_hg(s).get("state")) or 0) & BW.WW_ST_SCENE)
        if prev_scene and not sc:
            skip = SCENE_SETTLE
        prev_scene = sc
        if skip:
            skip -= 1
            continue
        out.append(s)
    return out


SCENE_SETTLE = 2


def judge_th_instrument(samples) -> tuple:
    """S166-TH-I (PURE over phase A): the host judged on 9011 and the record reached it -- guest place 2, 3 and 4 each read, flags 1."""
    if not any(cb.has(s, HOST_GUEST) for s in samples):
        return False, f"absent: no `{HOST_GUEST}` (an engine before s166 A3: the host shows nothing)"
    places = {_hg(s).get("place") for s in samples}
    flags = {_hg(s).get("flags") for s in samples} - {-1, None}
    world = [s for s in samples if judged(s) and s.world_id == WORLD]
    ok = bool(world) and {2, 3, 4} <= places and flags == {1}
    return ok, f"{len(world)} judged host sample(s) on {WORLD}; guest places {sorted(p for p in places if p is not None)}; flags {sorted(flags)}"


TH_WORDS = {"following": BW.WORDS_WW_HOST_FOLLOWING, "loading": BW.WORDS_WW_HOST_LOADING, "scene": BW.WORDS_WW_HOST_SCENE}


def judge_th_lines(samples, lines, want=("following", "loading", "scene")) -> tuple:
    """S166-TH-LINES (PURE over phase A): each of ``want`` read on `host.world.guest.line` AND `world.line.asked` (its words, drawn) in
    that order, and ONE 'host world: the partner is <x> ("...")' log line each."""
    if not any(cb.has(s, HOST_GUEST) for s in samples):
        return False, f"absent: no `{HOST_GUEST}`"
    firsts, bad = [], []
    for name in want:
        i = _first_index(samples, lambda s, n=name: _hg(s).get("line") == n and _line(s).get("asked") == n)
        firsts.append(i)
        if i is None:
            bad.append(f"{name} never read")
            continue
        ln = _line(samples[i])
        if ln.get("text") != TH_WORDS[name] or ln.get("drawn") is not True:
            bad.append(f"{name}: text {ln.get('text')!r} drawn {ln.get('drawn')!r}")
        n = sum(1 for ln in lines if BW.LOG_WW_HOST_WORLD in ln and f'the partner is {name} ("' in ln)   # alone, or after an end
        if n != 1:
            bad.append(f"{name}'s log line {n}x (want 1)")
    order = [i for i in firsts if i is not None]
    if order != sorted(order):
        bad.append(f"out of order {firsts}")
    return not bad, (f"first reads {dict(zip(want, firsts))}; " + ("; ".join(bad) if bad else "each line drawn with its words, logged once"))


def judge_th_gap(base, win, rec, lines, length_ms: int = int(TH_GAP_FOR * 1000)) -> tuple:
    """S166-TH-GAP (PURE): one HOST lane gap pair (its end ~``length_ms``), no hang / cut line, the host's ghost shown on every judged
    sample of the gap and its recovery (hides +0), no 'lost' host line."""
    if not any(cb.has(s, GHOST) for s in list(win) + list(rec)):
        return False, f"absent: no `{GHOST}`"
    names = window_lane(lines)
    starts = [x for x in names if x[1] == "gap_start" and x[0] == "host"]
    ends = [x for x in names if x[1] == "gap_end" and x[0] == "host"]
    other = [x[1] for x in names if x[1] in ("hang_start", "load_start", "hang_cut")]
    length = ends[0][2] if ends else None
    js = [s for s in list(win) + list(rec) if judged(s)]
    hidden = [s.frame for s in js if _ghost(s).get("shown") is not True]
    dh = _d(base, js[-1] if js else None, _ghost, "hides")
    lost = [s.frame for s in js if _hg(s).get("line") == "lost"]
    ok = (len(starts) == 1 and len(ends) == 1 and length is not None and abs(length - length_ms) <= GAP_LEN_TOL and not other
          and bool(js) and not hidden and dh == 0 and not lost)
    return ok, (f"host gap lines {len(starts)} / {len(ends)} (want 1 / 1), the end naming {length} ms (want {length_ms} +- "
                f"{GAP_LEN_TOL}); other {other or 'none'}; hidden on {hidden[:3] or 'none'}, hides +{dh}; 'lost' on {lost[:3] or 'none'}")


def judge_th_released(samples, lines, tap_rows, smap) -> tuple:
    """S166-TH-RELEASED (PURE over phase B): the tap's world rows a RELEASED guest's (state b0 clear, flags b0 set); the host reads the
    'following' line (and logs it once) and shows the ghost on its tap's pose by seq."""
    rows = [r for r in tap_rows if r.get("has") and r.get("place") == BW.WW_PLACE_WORLD]
    shape = bool(rows) and all(not r["state"] & BW.WW_ST_FROZEN and r["flags"] & BW.WW_FLAG_FOLLOW for r in rows)
    l_ok, l_why = judge_th_lines(samples, lines, want=("following",))
    walk = [s for s in samples if judged(s) and _hg(s).get("place") == BW.WW_PLACE_WORLD]
    # (a short window that may hold no straight leg: the facing is TH-GHOST's and RM-GHOST's to judge -- min_yaws 0 here)
    g_ok, g_why = judge_ghost_on_oracle(walk, smap, min_samples=TH_MIN_SAMPLES // 2, what="the tap", min_yaws=0)
    return shape and l_ok and g_ok, f"released shape {shape} ({len(rows)} world row(s)); LINE {l_why}; GHOST {g_why}"


def judge_th_nofollow(samples, lines, tap_rows) -> tuple:
    """S166-TH-NOFOLLOW (PURE over phase C): the tap's rows flags b0 CLEAR; the host's guest line null and `world.line` never asked on
    every sample, no 'host world:' log line, the ghost never shown and why_not 'role' on its judged samples."""
    if not any(cb.has(s, HOST_GUEST) and cb.has(s, GHOST) for s in samples):
        return False, f"absent: no `{HOST_GUEST}` / `{GHOST}`"
    rows = [r for r in tap_rows if r.get("has")]
    shape = bool(rows) and not any(r["flags"] & BW.WW_FLAG_FOLLOW for r in rows)
    lined = [s.frame for s in samples if _hg(s).get("line") is not None or _line(s).get("asked") is not None]
    logged = cb.count(lines, BW.LOG_WW_HOST_WORLD + "the partner is") + sum(1 for ln in lines if "; the partner is" in ln)
    shown = [s.frame for s in samples if _ghost(s).get("shown") is True]
    whys = sorted({str(_ghost(s).get("why_not")) for s in samples if judged(s)})
    ok = shape and not lined and not logged and not shown and whys == ["role"]
    return ok, (f"no-follow shape {shape}; a line on {lined[:3] or 'none'}; 'host world' lines {logged}; shown on {shown[:3] or 'none'}; "
                f"why_not {whys}")


def hostlines_measured(samples, lines) -> bool:
    """`hostlines off`'s shape (PURE): the record carried place 2 / 3 and a scene (the guest's own facts) while the host's line stayed
    null and nothing was logged."""
    places = {_hg(s).get("place") for s in samples}
    scene = any((_num(_hg(s).get("state")) or 0) & BW.WW_ST_SCENE for s in samples)
    return {2, 3} <= places and scene and not any(_hg(s).get("line") for s in samples) and not cb.count(lines, BW.LOG_WW_HOST_WORLD)


# ================================================================================================ pure judges: the duo
def tx_pose_at(host_samples, seq: int):
    """The host's own trailer pose at ``seq`` off its published `lane.tx` (bracketed and interpolated within D_SEQ_SLACK seqs), else None."""
    pts = []
    for s in host_samples:
        t = _tx(s)
        q, x, z = t.get("seq"), _num(t.get("x")), _num(t.get("z"))
        if isinstance(q, int) and q >= 0 and None not in (x, z):
            pts.append((q, x, z))
    best_lo = best_hi = None
    for q, x, z in pts:
        d = ((seq - q + 0x8000) & 0xFFFF) - 0x8000          # seq - q, u16
        if d == 0:
            return x, z
        if 0 < d <= D_SEQ_SLACK and (best_lo is None or d < best_lo[0]):
            best_lo = (d, x, z)
        if -D_SEQ_SLACK <= d < 0 and (best_hi is None or -d < best_hi[0]):
            best_hi = (-d, x, z)
    if best_lo and best_hi:
        k = best_lo[0] / float(best_lo[0] + best_hi[0])
        ax, az = best_lo[1], best_lo[2]
        return ax + _tdx(best_hi[1] - ax, W) * k, az + _tdx(best_hi[2] - az, H) * k
    one = best_lo or best_hi
    return (one[1], one[2]) if one else None


def _furthest(xs) -> float:
    xs = [p for p in xs if None not in p]
    return max((torus(*xs[0], *p) for p in xs), default=0.0) if xs else 0.0


def tx_moved(host_samples, riding: bool = False) -> float:
    """(PURE) [W2b] The host's furthest torus distance from its FIRST published trailer pose (`lane.tx.x / z`) over ``host_samples`` --
    over its riding samples alone (tx mode 1) when ``riding``: D-G1's and D-DOTRIDE's `moved`, and _walk_host's stop (one measure)."""
    ss = [s for s in host_samples if _num(_tx(s).get("mode")) == 1] if riding else list(host_samples)
    return _furthest([(_num(_tx(s).get("x")), _num(_tx(s).get("z"))) for s in ss])


def world_moved(host_samples) -> float:
    """(PURE) [W2b] The same over the samples' own published `world.x / z` (the host's REAL pose): _walk_host's second stop, so a dark or
    stale trailer never walks the host on (its tx_moved stays 0 and the row fails honestly with 'moved 0.0 u')."""
    return _furthest([tuple(_num(v) for v in wf.world_xz(s)) for s in host_samples])


#: the guest's "world follow-out: landed on world map W -- ..., N ms after its start" (the engine; the stand-in says "after the start")
_RX_WFO_LANDED = re.compile(r"world follow-out: landed on world map \d+\b.*?\b(\d+) ms after (?:its|the) start")
#: the host's edge line ending 'following' (alone, or "...; the partner is <x>" after it), and the guest's raw place it names
_RX_FOLLOW_END = re.compile(r"the partner's following state ended after (\d+) ms")
_RX_GUEST_PLACE = re.compile(r"-- the guest's place (\w+), state (0x[0-9A-Fa-f]+)")


def d_lines_coverage(host_samples) -> tuple:
    """(PURE) D-LINES' COVERAGE: (covered, first guest place read) -- some host sample reads the guest at place 1 (on its field) before its
    first sample off it (place 2, 3 or 4). A Tap that began after the follow-out never saw the window it judges."""
    places = [_hg(s).get("place") for s in host_samples]
    off = next((i for i, p in enumerate(places) if p in (BW.WW_PLACE_TRANSITION, BW.WW_PLACE_WORLD_LOADING, BW.WW_PLACE_WORLD)), None)
    head = places if off is None else places[:off]
    first = next((p for p in places if p is not None and p >= 0), None)
    return BW.WW_PLACE_FIELD in head, first


def own_live(s) -> bool:
    """(PURE) A game LIVE on the world map by its OWN trailer: `lane.tx.place` 4 (world) on a judged sample (WorldHUD, its blocks in)."""
    return judged(s) and _tx(s).get("place") == BW.WW_PLACE_WORLD


def _hms(t) -> str:
    return t.strftime("%H:%M:%S.%f")[:-3] if hasattr(t, "strftime") else str(t)


def _place_name(p) -> str:
    return f"{p} ({BW.WW_PLACE_NAMES[p]})" if isinstance(p, int) and 0 <= p < len(BW.WW_PLACE_NAMES) else str(p)


def d_lines_premise(host_stamped, guest_stamped, held) -> tuple:
    """[W2c] (PURE over the two Taps' (wall, state) samples, one process's clock) D-LINES' PREMISE: the guest's following phase began on a
    LIVE host -- some HOST sample stamped at or before the guest's trailer first read place 2 (its own `lane.tx.place`) is own_live --
    and, when the route held the guest, the hold read back on ``held`` (the guest's last sample before the release: `out.hold` true,
    `out.why` 'hold'; None = never held / unread). ``held`` == NO_HOLD: a route with no hold (the live term alone). -> (ok, why); never
    vacuous: no guest place 2 at all is red."""
    t2 = next((t for t, s in guest_stamped if _tx(s).get("place") == BW.WW_PLACE_TRANSITION), None)
    if t2 is None:
        seen = sorted({_tx(s).get("place") for _t, s in guest_stamped if _tx(s).get("place") is not None})
        return False, f"not covered: the guest's trailer never read place 2 (its own places {seen})"
    prior = [s for t, s in host_stamped if t <= t2]
    live = next((t for t, s in host_stamped if t <= t2 and own_live(s)), None)
    own = _tx(prior[-1]).get("place") if prior else None
    if live is None:
        ok, why = False, (f"not covered: the host was not live when the guest began following (its own place {_place_name(own)} on "
                          f"its last sample at or before the guest's first place 2, {_hms(t2)})")
    else:
        ok, why = True, f"the host live (its own place 4) {(t2 - live).total_seconds():.2f} s before the guest's first place 2"
    if held == NO_HOLD:
        return ok, why + "; no hold on this route"
    hold, hwhy = (wf._o(held, "hold"), wf._o(held, "why")) if held is not None else (None, None)
    if hold is True and hwhy == "hold":
        return ok, why + "; the guest held until the release (out.hold true, why 'hold')"
    return False, why + f"; not covered: the guest was not held before the release (out.hold {hold!r}, why {hwhy!r}; want true, 'hold')"


def judge_d_lines(host_samples, host_lines, guest_lines, landed: bool, premise: tuple) -> tuple:
    """S166-D-LINES (PURE over the HOST from BEFORE the guest can leave to the guest's landing + D_S): [W2c] THE PREMISE (``premise`` =
    d_lines_premise: the host live at or before the guest's first place 2, the hold read back -- else "not covered"); COVERED
    (d_lines_coverage, else "not covered"); 'following' read (guest.line and world.line, its words, drawn) and logged ONCE; [W2b] THE
    DISCRIMINATOR -- no host "following state ended" line names "-- the guest's place field" (the d6df5df17fe0af03 build: the record
    missed, the line ended at the commit), and 'following' lasted >= the guest's own "landed ... N ms after its start" - D_LINES_SLACK_MS
    (through the commit and the sync load; immune to the end line's wording: a HostLineLost end over a long load still passes); the guest landed and the host's line
    none on the last sample. 'loading' and the host's 'not updating' lane lines REPORTED (ONE-PC LOAD CONTENTION thins the samples)."""
    if not any(cb.has(s, HOST_GUEST) for s in host_samples):
        return False, f"absent: no `{HOST_GUEST}` on the host"
    p_ok, p_why = premise
    covered, first = d_lines_coverage(host_samples)
    cov = ("covered (the guest read at place 1 before it left)" if covered
           else f"not covered: the Tap began after the follow-out (first guest place {first})")
    ok1, why1 = judge_th_lines(host_samples, host_lines, want=("following",))
    ends = [ln for ln in host_lines if BW.LOG_WW_HOST_WORLD in ln and _RX_FOLLOW_END.search(ln)]
    at_field = [ln for ln in ends if "-- the guest's place field" in ln]
    named = [m.group(1) + " " + m.group(2) for m in (_RX_GUEST_PLACE.search(ln) for ln in ends) if m]
    follow_ms = int(_RX_FOLLOW_END.search(ends[0]).group(1)) if ends else None
    landed_ms = next((int(m.group(1)) for m in (_RX_WFO_LANDED.search(ln) for ln in guest_lines) if m), None)
    lasted = follow_ms is not None and landed_ms is not None and follow_ms >= landed_ms - D_LINES_SLACK_MS
    loading = any(_hg(s).get("line") == "loading" for s in host_samples)
    hangs = len(hang_lines_timed(host_lines))
    last = host_samples[-1] if host_samples else None
    ended = last is not None and _hg(last).get("line") is None
    ok = bool(p_ok) and covered and ok1 and not at_field and lasted and landed and ended
    return ok, (f"{p_why}; {cov}; {why1}; the end line(s) name the guest's place {named or 'NONE'} (want never 'field': "
                f"{'ok' if not at_field else 'ENDED AT THE COMMIT'}); 'following' lasted {follow_ms} ms against the guest's landing "
                f"{landed_ms} ms after its start (want >= landed - {D_LINES_SLACK_MS}: {'yes' if lasted else 'NO'}); the guest landed "
                f"{landed}; the line none at the end {ended}; 'loading' read {loading}, the host's 'not updating' lane lines {hangs} "
                "(both REPORTED: ONE-PC LOAD CONTENTION)")


def judge_d_g2(host_samples, guest_xz, gap_text: str) -> tuple:
    """S166-D-G2 (PURE): the host's ghost of the FROZEN guest shown within D_G2_TOL of the guest's own world x/z on every judged host
    sample (>= D_MIN_SAMPLES); the landing gap REPORTED."""
    if not any(cb.has(s, GHOST) for s in host_samples):
        return False, f"absent: no `{GHOST}` on the host"
    js = [s for s in host_samples if judged(s)]
    bad = []
    for s in js:
        g = _ghost(s)
        gx, gz = _num(g.get("x")), _num(g.get("z"))
        d = torus(gx, gz, *guest_xz) if None not in (gx, gz) and None not in guest_xz else None
        if g.get("shown") is not True or d is None or d > D_G2_TOL:
            bad.append((s.frame, g.get("shown"), g.get("why_not"), d if d is None else round(d, 2)))
    ok = len(js) >= D_MIN_SAMPLES and not bad
    return ok, f"{len(js)} judged host sample(s); off {bad[:3] or 'none'} (want shown within {D_G2_TOL:g} u of the guest's {guest_xz}); the landing gap (REPORTED, ONE-PC LOAD CONTENTION): {gap_text}"


def judge_d_g1(guest_samples, host_samples, own0, own1) -> tuple:
    """S166-D-G1 (PURE): on every judged guest sample with the ghost placed, shown, its target within D_TARGET_TOL of the host's own
    trailer pose at the guest's `rx.seq` (tx_pose_at), eased within D_G1_TOL of the target; the host moved >= D_MOVE_U over its tx
    poses; the guest's own pose unmoved (< HELD_U: frozen)."""
    if not any(cb.has(s, GHOST) for s in guest_samples):
        return False, f"absent: no `{GHOST}` on the guest"
    js = [s for s in guest_samples if judged(s) and _ghost(s).get("placed") is True]
    bad, unmatched = [], 0
    for s in js:
        g, seq = _ghost(s), _rx(s).get("seq")
        want = tx_pose_at(host_samples, seq) if isinstance(seq, int) and seq >= 0 else None
        if want is None:
            unmatched += 1
            continue
        gx, gz, tx, tz = (_num(g.get(k)) for k in ("x", "z", "tx", "tz"))
        if g.get("shown") is not True or None in (gx, gz, tx, tz) or torus(tx, tz, *want) > D_TARGET_TOL \
                or torus(gx, gz, tx, tz) > D_G1_TOL:
            bad.append((s.frame, g.get("shown"), tx, tz, want))
    moved = tx_moved(host_samples)
    still = None not in (own0[0], own1[0]) and torus(*own0, *own1) < ww.HELD_U
    n = len(js) - unmatched
    ok = n >= D_MIN_SAMPLES and not bad and moved >= D_MOVE_U and still
    return ok, (f"{n} guest sample(s) matched to the host's trailer by seq ({unmatched} unmatched); off {bad[:3] or 'none'}; the host "
                f"moved {moved:.1f} u (want >= {D_MOVE_U:g}); the guest's own pose {'unmoved' if still else 'MOVED'} ({own0} -> {own1})")


def judge_d_trailer(host_samples, guest_samples) -> tuple:
    """S166-D-TRAILER (PURE): on judged world samples of both games, `lane.tx.kind` and `lane.rx.kind` 'fmt1' and the peer's caps 1."""
    parts, ok = [], True
    for who, ss in (("host", host_samples), ("guest", guest_samples)):
        js = [s for s in ss if judged(s) and cb.has(s, LANE)]
        good = [s for s in js if _tx(s).get("kind") == "fmt1" and _rx(s).get("kind") == "fmt1"
                and (_lane(s).get("caps") or {}).get("peer") == BW.WW_OWN_CAPS]
        ok = ok and bool(js) and len(good) == len(js)
        parts.append(f"{who}: {len(good)}/{len(js)} active")
    return ok, "; ".join(parts)


def load_windows(stamped) -> list:
    """(PURE over (wall, state) samples) A game's own sync loads: [(t0, t1)] where its published frames stopped >= LOAD_GAP_S across a
    scene change: ui / field / world differ before and after, OR [W2b] the game's OWN trailer place (`lane.tx.place`) stepped out of a
    place it had ANNOUNCED as loading (2 transition / 3 world_loading -- _LOAD_PLACES, LaneGapKind's own set). A world battle keeps field
    6603 / world 9011 and its warm return flips ui BattleResult -> WorldHUD BEFORE the freeze, so only the announced place sees that load
    (the round-A lever duo 20261104-022513, the host: its 4.18 s freeze 3 -> 4 had equal (ui, field, world) keys -- 0 windows). A step out
    of a NON-loading place (5 battle -> 3, 6 diorama -> 2, 4 -> 3) is never a window: its last frame misnamed the load, so a partner line
    there is a wording defect and stays red. No lane (an older engine): the old key exactly."""
    out = []
    for (ta, a), (tb, b) in zip(stamped, stamped[1:]):
        if (tb - ta).total_seconds() < LOAD_GAP_S:
            continue
        scene = (a.ui_state, a.field_id, a.world_id) != (b.ui_state, b.field_id, b.world_id)
        pa = _tx(a).get("place")
        announced = pa in _LOAD_PLACES and _tx(b).get("place") != pa
        if scene or announced:
            out.append((ta, tb))
    return out


def hang_lines_timed(lines) -> list:
    """(PURE) The non-loading hang starts in an engine log: [(wall, text)] -- 'lane hang: ... not updating' (a hang off place 4)."""
    out = []
    for ln in lines:
        p = pb.parse_engine_line(ln)
        if p is None:
            continue
        m = ww._RX_LANE.search(p[2])
        if m and "(its game is not updating)" in m.group(2):
            out.append((p[0], m.group(2)))
    return out


def split_contention(hangs, windows) -> tuple:
    """(PURE) ``hangs`` split into (outside every window +- CONTENTION_PAD_S, inside one: ONE-PC LOAD CONTENTION)."""
    pad = _dt.timedelta(seconds=CONTENTION_PAD_S)
    inside = [h for h in hangs if any(a - pad <= h[0] <= b + pad for a, b in windows)]
    return [h for h in hangs if h not in inside], inside


def _publish_skew(samples, i) -> bool:
    """(PURE) Sample ``i`` is the ONE-FRAME PUBLISH SKEW, not a shown ghost: the harness may publish between NetSyncClient.Update (which
    moved the cache: `rx` and the live `why_not` already read the new place) and the driver's LateUpdate (which still holds last frame's
    `shown`) -- so it reads shown with a live refusal, and the very next sample is hidden. Under `ghost sticky` the rule itself SHOWS
    (why_not None), so the lever's shape is never this."""
    s = samples[i]
    return (_ghost(s).get("why_not") is not None and i + 1 < len(samples)
            and _ghost(samples[i + 1]).get("shown") is not True)


def entry_hide(guest_samples) -> tuple:
    """(PURE) [W2b] D-BATTLE's ENTRY HIDE over the battle Tap's guest samples: (off, cover, whys) -- `off` the frames whose ghost is SHOWN
    while the cache reads the host OFF place 4 (the host's swirl publishes place 2 ahead of InOwnBattle's nonce that boots the guest's
    diorama: the guest is live on the world through it; a warm return's place 3), the one-frame publish skew excused; `cover` the WorldHUD
    samples reading the host on place 2 (the window `ghost sticky` bends), `whys` their why_not values."""
    off = [s.frame for i, s in enumerate(guest_samples) if _ghost(s).get("shown") is True
           and _rx(s).get("place") != BW.WW_PLACE_WORLD and not _publish_skew(guest_samples, i)]
    cover = [s for s in guest_samples if s.ui_state == "WorldHUD" and _rx(s).get("place") == BW.WW_PLACE_TRANSITION]
    return off, cover, sorted({str(_ghost(s).get("why_not")) for s in cover})


def judge_d_battle(base_h, after_h, base_g, after_g, host_lines, guest_lines, host_windows, guest_windows, guest_samples) -> tuple:
    """S166-D-BATTLE (PURE): both ghosts re-minted (mints >= +1) and shown again after the warm returns; [W2b] THE ENTRY HIDE (entry_hide:
    the guest's ghost never shown off the host's place 4 on the battle Tap's ``guest_samples``; the swirl's coverage REPORTED, never
    required -- a missed swirl cannot flake the no-lever leg); zero non-loading hang lines on each game outside the OTHER game's own load
    windows (inside: ONE-PC LOAD CONTENTION, reported)."""
    if not (cb.has(after_h, GHOST) and cb.has(after_g, GHOST)):
        return False, f"absent: no `{GHOST}`"
    mh, mg = _d(base_h, after_h, _ghost, "mints"), _d(base_g, after_g, _ghost, "mints")
    sh, sg = _ghost(after_h).get("shown") is True, _ghost(after_g).get("shown") is True
    off, cover, whys = entry_hide(list(guest_samples))
    h_out, h_in = split_contention(hang_lines_timed(host_lines), guest_windows)
    g_out, g_in = split_contention(hang_lines_timed(guest_lines), host_windows)
    ok = (mh or 0) >= 1 and (mg or 0) >= 1 and sh and sg and not off and not h_out and not g_out
    return ok, (f"mints host +{mh} guest +{mg} (want >= 1 each), shown again host {sh} guest {sg}; the guest's ghost shown off the host's "
                f"place 4 on {off[:3] or 'none'} (THE ENTRY HIDE; the guest live on the world while the host swirled: {len(cover)} "
                f"sample(s), why_not {whys or 'none'} -- REPORTED); non-loading hang lines OUTSIDE the other's load windows: host "
                f"{len(h_out)} guest {len(g_out)} (want 0) {[t for _w, t in (h_out + g_out)[:2]]}; inside them (ONE-PC LOAD "
                f"CONTENTION, reported): host {len(h_in)} guest {len(g_in)}; load windows host {len(host_windows)} guest "
                f"{len(guest_windows)}")


def judge_d_dotride(guest_samples, host_samples) -> tuple:
    """S166-D-DOTRIDE (PURE): on judged guest samples with the dot placed, src 'trailer' and the pose drawn (src_x / src_z) within DOT_TOL
    of the host's own trailer pose at the guest's `rx.seq`; the host's tx mode 1 (riding) and moved >= D_MOVE_U."""
    if not any(cb.has(s, DOT_SRC) for s in guest_samples):
        return False, f"absent: no `{DOT_SRC}` (the dot parked on section 0: an engine before A4)"
    js = [s for s in guest_samples if judged(s) and _dot(s).get("src") is not None]
    bad, n = [], 0
    for s in js:
        d, seq = _dot(s), _rx(s).get("seq")
        want = tx_pose_at(host_samples, seq) if isinstance(seq, int) and seq >= 0 else None
        if want is None:
            continue
        n += 1
        sx, sz = _num(d.get("src_x")), _num(d.get("src_z"))
        if d.get("src") != "trailer" or None in (sx, sz) or torus(sx, sz, *want) > DOT_TOL:
            bad.append((s.frame, d.get("src"), sx, sz, want))
    riding = [s for s in host_samples if _num(_tx(s).get("mode")) == 1]
    moved = tx_moved(host_samples, riding=True)
    ok = n >= D_MIN_SAMPLES and not bad and moved >= D_MOVE_U
    return ok, (f"{n} dot sample(s) matched by seq; off {bad[:3] or 'none'} (want src 'trailer' within {DOT_TOL:g} u); the host rode "
                f"on {len(riding)} sample(s), moved {moved:.1f} u")


def judge_d_rejoin(guest_samples, host_after, rejoin_row) -> tuple:
    """S166-D-REJOIN (PURE): the guest's ghost hidden on every sample whose cache no longer reads the host on place 4 and inside its own
    rejoin window (cw.in_armed_window) or off the world; the host's ghost not shown on its samples off the world; the guest's rejoin
    (``rejoin_row``: cw.judge_rejoin_land's verdict)."""
    if not any(cb.has(s, GHOST) for s in guest_samples):
        return False, f"absent: no `{GHOST}`"
    left = [s.frame for s in guest_samples if _ghost(s).get("shown") is True
            and (_rx(s).get("place") != BW.WW_PLACE_WORLD or cw.in_armed_window(s) or s.ui_state != "WorldHUD")]
    host_shown = [s.frame for s in host_after if s.ui_state != "WorldHUD" and _ghost(s).get("shown") is True]
    # [W2 critic] the instrument: the guest's ghost SHOWN on a judged sample while the host still stood on place 4 -- "hidden before the
    # fade" is only a claim about a ghost that was there (a ghost never drawn hides nothing: `ghost off` left this row green)
    before = [s.frame for s in guest_samples if judged(s) and _ghost(s).get("shown") is True and _rx(s).get("place") == BW.WW_PLACE_WORLD]
    ok = bool(before) and not left and not host_shown and rejoin_row[0]
    return ok, (f"the guest's ghost shown before the host left on {len(before)} sample(s) (want >= 1); shown after the host left / in "
                f"its own window on {left[:3] or 'none'}; the host's shown off the world on {host_shown[:3] or 'none'}; REJOIN "
                f"{rejoin_row[1]}")


def sticky_measured(guest_samples) -> bool:
    """`ghost sticky`'s shape (PURE): the guest's ghost shown on a sample whose cache reads the host on place 2 (it ignored the fade), the
    rule itself SHOWING there (why_not None -- [W2b] never the one-frame publish skew, whose live why_not is a refusal). [W2b] Measured
    on D-BATTLE's Tap: the host's swirl is the only place-2 window a live guest sees (THE ARM-FIRST ORDER shuts REJOIN's)."""
    return any(_ghost(s).get("shown") is True and _ghost(s).get("why_not") is None and _rx(s).get("place") == BW.WW_PLACE_TRANSITION
               for s in guest_samples)


def dot_lever_measured(guest_samples) -> bool:
    js = [s for s in guest_samples if judged(s) and _dot(s).get("src") is not None]
    return bool(js) and all(_dot(s).get("src") == "section0" for s in js)


def judge_cal(failed, predicted, measured: dict, needs) -> tuple:
    """A *-CAL row (PURE): every predicted row red and nothing else, each row in ``needs`` MEASURED its lever's shape."""
    return ww.judge_a_cal(failed, predicted, measured, tuple(needs))


# ================================================================================================ the moves
class _Ctx(cw._T2):
    def __init__(self):
        super().__init__()
        self.lines_at: dict = {}         # event -> the engine log's line count when the leg saw it (log order exact)
        self.events: dict = {}           # event -> the sample index when the leg saw it
        self.sent: list = []
        self.lever = None
        self.measured: dict = {}
        self.rows = []
        self.smap = {}
        self.windows = {}
        self.instrument = False
        self.gstage = None
        self.peers: list = []
        self.line_counts: list = []


def _ww(g, *args) -> tuple:
    """`netsync worldwalk <args>` (ok, why) -- callers PROBE the piece's key first."""
    ok, why = cb.try_ns(g, "worldwalk", *[str(a) for a in args])
    g.wait_frames(ww.SKEW_FRAMES)                          # THE ORDER SKEW: the op's own publish dropped
    return ok, why


def _lever(g, ctx: _Ctx, lever) -> str:
    """Pull ``lever`` (a `netsync worldwalk` op) on the game under test when its piece is published; read it back."""
    if lever is None or lever not in LEVER_OPS:
        return "no lever"
    op, word = LEVER_OPS[lever]
    need = GHOST if op in ("ghost", "dot") else LANE
    if not cb.has(g.state, need):
        return f"no `{need}`: `worldwalk {op} {word}` never sent (OLD)"
    ok, why = _ww(g, op, word)
    if ok:
        ctx.sent.append(op)
    return f"`worldwalk {op} {word}` {'sent' if ok else 'REFUSED: ' + why[:100]} (the CALIBRATION: held through the leg)"


def _sample(g, ctx: _Ctx):
    st = cw._sample(g, ctx)
    ctx.line_counts.append(_lines_n(ctx))                 # the engine log's length when this sample was read (a window's line mark)
    return st


def _lines_n(ctx: _Ctx) -> int:
    return len(ctx.eng.lines()) if ctx.eng is not None else 0


def _since(ctx: _Ctx, a: str, b: str | None = None) -> list:
    """The engine's lines (raw text, as Memoria.log wrote them) from event ``a``'s mark to ``b``'s (log order exact)."""
    lines = ctx.eng.lines() if ctx.eng is not None else []
    i = ctx.lines_at.get(a, 0)
    j = ctx.lines_at.get(b) if b is not None else None
    return [raw_line(x) for x in (lines[i:j] if j is not None else lines[i:])]


def _samples_between(ctx: _Ctx, a: str, b: str | None = None) -> list:
    i = ctx.events.get(a)
    j = ctx.events.get(b) if b is not None else None
    if i is None:
        return []
    return [s for _t, s in ctx.samples[i:j]] if j is not None else [s for _t, s in ctx.samples[i:]]


def _mark(ctx: _Ctx, name: str) -> None:
    if name not in ctx.events:
        ctx.events[name] = len(ctx.samples)
        ctx.lines_at[name] = _lines_n(ctx)


_BH = re.compile(r"^BLACKHOLE at tape ([\d.]+) s")
_BH_END = re.compile(r"^BLACKHOLE over at tape ([\d.]+) s")
_FZ = re.compile(r"^FREEZE at tape ([\d.]+) s")
_FZ_END = re.compile(r"^FREEZE over at tape ([\d.]+) s")


def _peer_events(ctx: _Ctx, kinds) -> None:
    """Mark each window edge the peer has logged since (bh1 / bh1_end / bh2 / bh2_end, or fz*), in order."""
    if ctx.peer is None:
        return
    begin, end, pfx = (_BH, _BH_END, "bh") if kinds == "bh" else (_FZ, _FZ_END, "fz")
    for i, hit in enumerate(ctx.peer.find(begin)):
        _mark(ctx, f"{pfx}{i + 1}")
    for i, hit in enumerate(ctx.peer.find(end)):
        _mark(ctx, f"{pfx}{i + 1}_end")


def _wait(g, ctx: _Ctx, cond, timeout: float, *, kinds=None) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = _sample(g, ctx)
        if kinds:
            _peer_events(ctx, kinds)
        try:
            if cond(st):
                return True
        except (TypeError, KeyError, AttributeError, IndexError, ValueError):
            pass
        time.sleep(POLL_S)
    return False


# ================================================================================================ run (the T2 legs)
def run(g, field: int | None = None):
    if LEG is None:
        led = cb.Ledger(g, {"S166-T2-LEG": "COOP_WWT_LEG names one leg"})
        led.check("S166-T2-LEG", False, f"COOP_WWT_LEG={_RAW_LEG!r} is not one of {LEGS} -- nothing was launched past the boot")
        return
    if LEG in B_T2_LEGS:                                   # [ff9mapkit netsync s167] round B's legs (their own section)
        _run_b(g)
        return
    if LEG == "old":
        _run_old(g)
        return
    if LEG == "record":
        _run_record(g)
        return
    calibrate = cb.CALIBRATE
    lever = lever_of(LEG, LEVER_RAW) if calibrate else None
    if calibrate and LEVER_RAW is not None and lever is None:
        led = cb.Ledger(g, {"S166-T2-LEVER": "COOP_WWT_LEVER is the leg's own"})
        led.check("S166-T2-LEVER", False, f"COOP_WWT_LEVER={LEVER_RAW!r} is not one of {LEG}'s {LEVERS[LEG]} -- nothing was edited")
        return
    if LEG == "host":
        _run_host(g, calibrate, lever)
        return
    cat = leg_catalog(LEG, calibrate)
    cal = f"S166-{LEG.upper()}-CAL"
    led = cb.Ledger(g, cat, finals=("T2-SAVE", "T2-INI", cal, "S166-RM-GATE"), width=DETAIL_W)
    ctx = _Ctx()
    ctx.field, ctx.lever = FARSHORE, lever
    try:
        _t2(g, led, ctx)
    except HarnessError as err:
        g.note(f"the {LEG} leg raised: {str(err)[:400]}")
        led.close(f"not reached: the leg raised ({str(err)[:200]})")
    finally:
        _t2_teardown(g, led, ctx)
        if LEG == "roam" and "S166-RM-GATE" not in led.done:
            led.check("S166-RM-GATE", not ctx.instrument and ctx.tape is not None,
                      "THE INSTRUMENT ran (a synthetic v15 host), NOT COOP_TAPE_WORLD_ROAM -- the owner-gated row is not run "
                      "(ROAM-TAPE.md)" if ctx.instrument else f"the recorded ROAM tape {ctx.tape}")
        if calibrate:
            _t2_cal(g, led, ctx, cal)
        led.close(final=True)


def _t2_cal(g, led, ctx: _Ctx, cal: str) -> None:
    stage = ctx.gstage or "old"
    try:
        stage = ctx.gstage or stage_of(g.state)
    except HarnessError:
        pass
    leg = LEG
    old = {"wire": WIRE_OLD_PREDICTED, "roam": ROAM_OLD_PREDICTED, "freeze": FREEZE_OLD_PREDICTED}[leg]
    lev = {"wire": WIRE_LEVER_PREDICTED, "roam": ROAM_LEVER_PREDICTED, "freeze": FREEZE_LEVER_PREDICTED}[leg]
    is_old = stage in ("old",) if leg == "wire" else stage not in ("a4",)
    pred = old if is_old else lev.get(ctx.lever, ())
    needs = () if is_old else tuple(pred)
    g.note(f"{cal}: the guest reads as {stage}; {'OLD' if is_old else 'LEVER ' + str(ctx.lever)}; predicted reds {sorted(pred)}; "
           f"measured {ctx.measured}")
    led.close("not reached: the leg ended before this check")
    failed = led.failed() - {cal, "S166-RM-GATE"}
    led.check(cal, *judge_cal(failed, pred, ctx.measured, needs))


def _t2_teardown(g, led, ctx: _Ctx) -> None:
    if ctx.sent:
        ok, why = cb.try_ns(g, "worldwalk", "clear")
        g.note(f"`worldwalk clear` (the levers this leg sent: {ctx.sent}): {'ok' if ok else why[:160]}")
    for p in [ctx.peer] + list(ctx.peers):
        if p is not None and p.how_ended is None:
            g.note(f"coop_peer: {p.stop()}")
    if "T2-SAVE" in led.catalog and "T2-SAVE" not in led.done:
        fell = pb.hits(ctx.eng.lines(), "ramp_failed") if ctx.eng is not None else []
        led.check("T2-SAVE", not fell, f"the exit ramp fell back to the TITLE: {pb.show(fell, 1)}" if fell else
                  "no title fallback" + ("" if ctx.eng is not None else " (the guest never ran a session)"))
    ini = "T2H-INI" if "T2H-INI" in led.catalog else "T2-INI"
    if ctx.guard is not None:
        ok, why = ctx.guard.restore()
        led.check(ini, ok, why)
    else:
        led.check(ini, True, "Memoria.ini was never edited (the leg stopped before the edit)")
    g.note(f"Memoria.log archived: {cb.archive_log(g, f'world-walk-t2-{LEG}')}")


def _load_tape(g, led, ctx: _Ctx) -> list | None:
    """The leg's tape (wire: the world-walk tape; roam / freeze: the ROAM tape, else THE INSTRUMENT built into the run dir) -> records."""
    cp = pb.coop_peer_module()
    if LEG == "wire":
        ctx.tape = pb.latest_world_walk_tape()
        how = "COOP_TAPE_WORLD_WALK"
    else:
        ctx.tape, how = roam_tape()
        if ctx.tape is None:
            ctx.instrument = True
            ctx.tape = write_instrument(cw._run_dir(g) / "roam-INSTRUMENT.f9tape", cp)
            how = f"THE INSTRUMENT ({how}): {ctx.tape.name}"
    if ctx.tape is None or not Path(ctx.tape).exists():
        led.check("T2-TAPE", False, f"no tape ({how})")
        led.close("not reached: no tape")
        return None
    try:
        header, records, torn = cp.read_tape(ctx.tape)
    except Exception as err:                              # noqa: BLE001
        led.check("T2-TAPE", False, f"{ctx.tape} does not read back: {err}")
        led.close("not reached: the tape does not read back")
        return None
    ctx.instrument = ctx.instrument or bool(header.get("instrument"))
    if LEG == "wire":
        facts = pb.world_walk_tape_facts(records, cp)
        ok = all(facts[f"wk{i}"]["ok"] for i in range(1, 7)) and cp.tape_wire(records) == WIRE_OLD
        bad = [f"wk{i}: {facts[f'wk{i}']['why']}" for i in range(1, 7) if not facts[f"wk{i}"]["ok"]]
        detail = (f"{Path(ctx.tape).name} ({len(records)} records{f', torn {torn} B' if torn else ''}): "
                  + ("the six facts hold" if not bad else "CANNOT -- " + "; ".join(bad))
                  + f"; its frames speak wire {cp.tape_wire(records)} (want {WIRE_OLD}: A-WIRE's unrestamped calibration)")
    else:
        facts = roam_tape_facts(records, cp, header=header)
        f_ok, bad = facts_ok(facts)
        w = facts["windows"]
        ok = f_ok and w["bh23"] is not None and w["bh6"] is not None
        ctx.rows = trailer_rows(records, cp)
        ctx.smap = seq_map(ctx.rows)
        ctx.windows = w
        detail = (f"{'THE INSTRUMENT -- ' if ctx.instrument else ''}{Path(ctx.tape).name} ({how}; {len(records)} records"
                  f"{f', torn {torn} B' if torn else ''}): " + ("the facts hold" if f_ok else "CANNOT -- " + "; ".join(bad))
                  + f"; windows {w}")
    led.check("T2-TAPE", ok, detail)
    if not ok and not FORCE:
        led.close("not reached: this tape cannot carry the leg")
        return None
    return records


def _guest_setup(g, led, ctx: _Ctx) -> bool:
    """coop_world_follow's T2 guest: the preflight (the bench port, THE OWNER'S BRIDGE DOWN, the moogle-only autosave), New Game -> 6603,
    encounters off, the marker watched, the field's autosave, the ini (GUEST_VALUES), the engine's config line."""
    if not wf._walk_preflight(g, led):
        return False
    cb.provenance(g)
    g.newgame()
    g.warp(FARSHORE)
    try:
        g.no_encounters(True)
    except HarnessError as err:
        g.note(f"noencounter refused ({str(err)[:160]})")
    g.watch(*(pb.MARKER_BYTE * 8 + b for b in range(8)))
    g.wait_frames(45)
    ctx.gstage = stage_of(g.state)
    g.note(f"the guest engine reads as {ctx.gstage} (netsync.wire {wire_of(g.state)})")
    ctx.eng = pb.EngineLog(g.engine_log())
    ctx.guard = pb.IniGuard(Path(g.game_path) / "Memoria.ini", GUEST_VALUES, label=f"coop-world-walk-t2-{LEG}", run_dir=cw._run_dir(g))
    try:
        g.note(ctx.guard.apply())
    except (OSError, RuntimeError) as err:
        led.check("T2-PEER", False, f"the Memoria.ini edit failed: {err}")
        led.close("not reached: Memoria.ini could not be edited")
        return False
    cfg = cw._wait_config(g, ctx)
    if not cfg:
        led.check("T2-PEER", False, f"the engine never logged the guest config (seen: {pb.show(pb.hits(ctx.eng.lines(), 'config'))})")
        led.close("not reached: the guest config never applied")
        return False
    ctx.cfg = cfg
    return True


def _replay(g, led, ctx: _Ctx, args, *, want_send, tag: str) -> bool:
    """Start replay-host with ``args``, wait for listening / the guest / REPLAY start, and judge T2-PEER with THE LIVE HEADER."""
    rd = cw._run_dir(g)
    ctx.peer = pb.PeerProc("replay-host", [str(ctx.tape), "--port", str(PORT), "--code", CODE, *[str(a) for a in args]],
                           log_path=rd / f"coop_peer-replay-{tag}.log", out_path=rd / f"coop_peer-replay-{tag}.out")
    g.note(f"starting: {ctx.peer.command_text()}")
    _mark(ctx, "launch")                                   # before the peer: its first frames land before REPLAY start is read
    ctx.peer.start()
    up = ctx.peer.wait_for(pb.PEER["listening"], 15.0, tick=lambda: _sample(g, ctx), poll=POLL_S)
    conn = ctx.peer.wait_for(pb.PEER["guest_connected"], wf.DIAL_S, tick=lambda: _sample(g, ctx), poll=POLL_S) if up else None
    start = ctx.peer.wait_for(pb.PEER["replay_start"], 10.0, tick=lambda: _sample(g, ctx), poll=POLL_S) if conn else None
    relay = pb.hits(ctx.eng.lines(), "relay_up", pred=lambda m: m.group(3) == "guest" and m.group(2) == CODE)
    found = ctx.peer.first(pb.PEER["guest_wire"])
    hdr = judge_live_header(found[1] if found else None, pb.probe_wire(g), want_send=want_send) if start else (False, "no replay start")
    ok = up is not None and conn is not None and start is not None and bool(relay) and hdr[0]
    led.check("T2-PEER", ok, f"wire: {hdr[1]}; config: {pb.show(ctx.cfg, 1)}; peer: {up[1] if up else 'never listened'} / "
                             f"{conn[1] if conn else 'no guest'} / {start[1] if start else 'no replay start'}; engine: {pb.show(relay, 1)}")
    if start is not None:
        ctx.anchors["start"] = start[0]
    _mark(ctx, "start")
    return ok


def _t2(g, led, ctx: _Ctx) -> None:
    rows = [c for c in led.catalog if c.startswith("S166-") and not c.endswith("-CAL") and c != "S166-RM-GATE"]
    records = _load_tape(g, led, ctx)
    if records is None:
        return
    if not _guest_setup(g, led, ctx):
        return
    g.note(f"the regression re-key: {_s166_rekey(g, ctx)}")   # [ff9mapkit netsync s167] an s167 guest reads s166 exactly
    lever_note = "no lever"
    if LEG in ("roam", "freeze") and ctx.lever is not None:
        lever_note = _lever(g, ctx, ctx.lever)
    g.note(lever_note)
    ctx.base = g.state
    if LEG == "wire":
        _leg_wire(g, led, ctx, rows)
        return
    w = ctx.windows
    if LEG == "roam":
        args = ["--blackhole-at", f"{w['bh23']:g}", "--blackhole-for", f"{BH23_S:g}", "--blackhole-at", f"{w['bh6']:g}",
                "--blackhole-for", f"{BH6_S:g}", "--at-end", "hold"]
    else:
        args = ["--freeze-at", f"{w['bh23']:g}", "--freeze-for", f"{BH23_S:g}", "--freeze-at", f"{w['bh6']:g}", "--freeze-for",
                f"{BH6_S:g}", "--at-end", "hold"]
    if not _replay(g, led, ctx, args, want_send=None, tag=f"world-roam-{LEG}"):
        led.unreached(rows, "the instrument never started (T2-PEER)")
        return
    _roam_rows(g, led, ctx, rows)


def _leg_wire(g, led, ctx: _Ctx, rows) -> None:
    """A-WIRE. NEW (an s166 guest): `--wire tape` for WIRE_S (NOPAIR, REJECT), then the same tape `--wire 15` (CLEAR: the words gone and
    it pairs). LEVER (`wire15`): ONE replay at `--wire 15` from the start -- NOPAIR / REJECT red, CLEAR judged on it (a matching engine
    from its first frame: no words past WIRE_CLEAR_S, paired), the lever's shape measured through the follow-out. OLD (a v14 guest): ONE
    replay `--wire tape` (14 = its own: it pairs) -- every row red, CLEAR 'absent'."""
    old = ctx.gstage == "old"
    lever = ctx.lever == "wire15" and not old             # OLD pulls no lever: `--wire tape` IS a v14 guest's own wire (the OLD shape)
    mode = "15" if lever else "tape"
    want = None if (old or lever) else WIRE_OLD          # NEW: the mismatch ASKED for (the guest speaks 15, the tape 14)
    if not _replay(g, led, ctx, ["--wire", mode, "--at-end", "hold"], want_send=want, tag=f"world-walk-wire-{mode}"):
        led.unreached(rows, "the instrument never started (T2-PEER)")
        return
    base = ctx.base
    _wait(g, ctx, lambda s: False, WIRE_S)
    win = _samples_between(ctx, "launch")
    lines = _since(ctx, "launch")
    led.check("S166-WIRE-NOPAIR", *judge_wire_nopair(win, lines))
    led.check("S166-WIRE-REJECT", *judge_wire_reject(base, win, lines))
    if lever or old:
        n_early = sum(1 for t, _s in ctx.samples[ctx.events["start"]:]
                      if (t - ctx.anchors.get("start", t)).total_seconds() < WIRE_CLEAR_S)
        led.check("S166-WIRE-CLEAR", *judge_wire_clear(win, lines, n_early))
        world = []
        if lever and _wait(g, ctx, lambda s: wf.first_judged([x for _t, x in ctx.samples[ctx.events["start"]:]
                                                                if x.ui_state == "WorldHUD"]) is not None, WIRE_WORLD_S):
            _wait(g, ctx, lambda s: False, 1.5)
            world = [s for s in _samples_between(ctx, "start") if judged(s)]
        m_ok, m_why = wire_lever_measured(_samples_between(ctx, "start"), _since(ctx, "start"), world)
        ctx.measured["S166-WIRE-NOPAIR"] = ctx.measured["S166-WIRE-REJECT"] = m_ok
        g.note(f"{'the lever' if lever else 'OLD'}'s shape: {m_why}")
        return
    g.note(f"coop_peer replay-host (--wire {mode}): {ctx.peer.stop()}")
    ctx.peers.append(ctx.peer)
    if not _replay_clear(g, led, ctx):
        led.check("S166-WIRE-CLEAR", False, "not reached: the `--wire 15` replay never started")
        return
    _wait(g, ctx, lambda s: False, WIRE_CLEAR_S + 1.0)
    _wait(g, ctx, lambda s: bool(pb.hits(parsed(_since(ctx, "clear2")), "paired")) or cw._s(s, "mirroring") is True, WIRE_PAIR_S)
    cs = _samples_between(ctx, "clear2")
    n_early = sum(1 for t, _s in ctx.samples[ctx.events["clear2"]:]
                  if (t - ctx.anchors.get("clear2", t)).total_seconds() < WIRE_CLEAR_S)
    led.check("S166-WIRE-CLEAR", *judge_wire_clear(cs, _since(ctx, "clear_launch"), n_early))


def _replay_clear(g, led, ctx: _Ctx) -> bool:
    """CLEAR's replay: the same tape at `--wire 15` (the guest's own wire), its start marked `clear2`."""
    rd = cw._run_dir(g)
    ctx.peer = pb.PeerProc("replay-host", [str(ctx.tape), "--port", str(PORT), "--code", CODE, "--wire", "15", "--at-end", "hold"],
                           log_path=rd / "coop_peer-replay-world-walk-wire-clear.log",
                           out_path=rd / "coop_peer-replay-world-walk-wire-clear.out")
    g.note(f"starting: {ctx.peer.command_text()}")
    _mark(ctx, "clear_launch")
    ctx.peer.start()
    up = ctx.peer.wait_for(pb.PEER["listening"], 15.0, tick=lambda: _sample(g, ctx), poll=POLL_S)
    conn = ctx.peer.wait_for(pb.PEER["guest_connected"], wf.DIAL_S, tick=lambda: _sample(g, ctx), poll=POLL_S) if up else None
    start = ctx.peer.wait_for(pb.PEER["replay_start"], 10.0, tick=lambda: _sample(g, ctx), poll=POLL_S) if conn else None
    if start is None:
        return False
    ctx.anchors["clear2"] = start[0]
    _mark(ctx, "clear2")
    return True


def _roam_rows(g, led, ctx: _Ctx, rows) -> None:
    """roam / freeze: the landing, then both windows by the peer's own edges, then the rows."""
    kinds = "bh" if LEG == "roam" else "fz"
    landed = _wait(g, ctx, lambda s: wf.first_judged([x for _t, x in ctx.samples[ctx.events['start']:]
                                                       if x.ui_state == "WorldHUD"]) is not None, LAND_S, kinds=kinds)
    if not landed:
        led.unreached(rows, f"the guest never landed on the world map within {LAND_S:g} s (ui {g.state.ui_state!r})")
        return
    _mark(ctx, "landed")
    pfx = kinds
    _wait(g, ctx, lambda s: f"{pfx}2_end" in ctx.events, EVENT_S, kinds=kinds)
    if f"{pfx}2_end" in ctx.events:
        _wait(g, ctx, lambda s: False, RECOVER_S + 1.0, kinds=kinds)
    _mark(ctx, "after")
    exit_lines = _since(ctx, "launch", "landed")
    all_s = _samples_between(ctx, "start")
    if LEG == "roam":
        led.check("S166-RM-I", *judge_rm_instrument(exit_lines, all_s))
    late = "landed"
    if f"{pfx}1" not in ctx.events or f"{pfx}2" not in ctx.events:
        led.unreached(rows, f"the windows never opened (peer edges {sorted(k for k in ctx.events if k.startswith(pfx))}); the tape's "
                            f"windows {ctx.windows}")
        return
    if ctx.events[f"{pfx}1"] < ctx.events["landed"]:
        led.unreached(rows, "the first window opened before the guest landed (the tape's room is too short for this guest)")
        return
    base1 = ctx.samples[ctx.events[f"{pfx}1"] - 1][1] if ctx.events[f"{pfx}1"] > 0 else ctx.base
    win1 = _samples_between(ctx, f"{pfx}1", f"{pfx}1_end")
    rec1 = _samples_between(ctx, f"{pfx}1_end", f"{pfx}2")
    lines1 = _since(ctx, f"{pfx}1", f"{pfx}2")
    base2 = ctx.samples[ctx.events[f"{pfx}2"] - 1][1]
    win2 = _samples_between(ctx, f"{pfx}2", f"{pfx}2_end")
    rec2 = _samples_between(ctx, f"{pfx}2_end", "after")
    lines2 = _since(ctx, f"{pfx}2", "after")
    if LEG == "roam":
        pre_all = [(t, s) for t, s in ctx.samples[ctx.events[late]:ctx.events[f"{pfx}1"]]]
        t_land = pre_all[0][0] if pre_all else None
        first = next((t for t, s in pre_all if judged(s) and _ghost(s).get("shown") is True), None)
        delay = (first - t_land).total_seconds() if first is not None and t_land is not None else None
        pre = [s for t, s in pre_all if first is not None and t >= first]
        post = [s for s in rec2 if judged(s)][len(rec2) // 2:]
        ok_g, why_g = judge_ghost_on_oracle(pre + post, ctx.smap, what="THE INSTRUMENT" if ctx.instrument else "the tape")
        ok_show = delay is not None and delay <= SHOW_S
        snaps = _d(pre[0], pre[-1], _ghost, "snaps") if pre else None   # on foot (the seam leg included) every step is < 64 u: no snap
        led.check("S166-RM-GHOST", ok_g and ok_show and snaps == 0,
                  f"first shown {delay if delay is None else round(delay, 2)} s after the landing (want <= {SHOW_S:g}); snaps +{snaps} "
                  f"from the first show to the first window (want 0: the seam crossed on foot never snaps); {why_g}")
        led.check("S166-RM-BH23", *judge_bh23(base1, win1, rec1, lines1, ctx.smap))
        led.check("S166-RM-BH6", *judge_bh6(base2, win2, rec2))
        if ctx.lever == "ghost":
            m = ghost_off_measured(pre + win1 + rec1 + win2 + rec2)
            ctx.measured.update({r: m for r in ROAM_LEVER_PREDICTED["ghost"]})
        elif ctx.lever == "lanegap":
            ctx.measured["S166-RM-BH23"] = lanegap_measured(base1, (rec1 or win1)[-1] if (rec1 or win1) else None, lines1)
    else:
        led.check("S166-FZ-23", *judge_t2_freeze(base1, win1, rec1, lines1, int(BH23_S * 1000), hide=False))
        led.check("S166-FZ-6", *judge_t2_freeze(base2, win2, rec2, lines2, int(BH6_S * 1000), hide=True))
        if ctx.lever == "lanegap":
            ctx.measured["S166-FZ-23"] = lanegap_measured(base1, (rec1 or win1)[-1] if (rec1 or win1) else None, lines1, "hangs")
            ctx.measured["S166-FZ-6"] = lanegap_measured(base2, (rec2 or win2)[-1] if (rec2 or win2) else None, lines2, "hangs")
        elif ctx.lever == "ghost":
            ctx.measured["S166-FZ-23"] = ghost_off_measured(win1 + rec1)
            ctx.measured["S166-FZ-6"] = ghost_off_measured(win2[:max(1, len(win2) // 2)])


# ================================================================================================ T2-A old
def _run_old(g) -> None:
    """T2-A old: coop_world_follow's T2 walk leg as it is (its own ledger and calibration), its samples tapped; then two rows of its own."""
    holder = {"ctx": None, "samples": []}
    real = cw._sample

    def tap(g_, ctx_):
        st = real(g_, ctx_)
        holder["ctx"] = ctx_
        holder["samples"].append(st)
        return st
    cw._sample = tap
    try:
        wf._run_walk(g)
    finally:
        cw._sample = real
    led = cb.Ledger(g, dict(OLD_CHECKS), width=DETAIL_W)
    c = holder["ctx"]
    peer = getattr(c, "peer", None) if c is not None else None
    found = peer.first(pb.PEER["guest_wire"]) if peer is not None else None
    led.check("S166-OLD-WIRE", *judge_old_wire(found[1] if found else None))
    # ...judged while the tape STREAMS: from its start to replay-host's 'replay done' (`--at-end hold` then holds the link SILENT -- a
    # real gap the s166 lane rightly names, after the tape)
    lines = c.eng.lines() if c is not None and c.eng is not None else []
    start = c.anchors.get("start") if c is not None else None
    done = peer.first(pb.PEER["replay_done"]) if peer is not None else None
    end = pb.floor_s(done[0]) if done is not None else None
    after = [raw_line(x) for x in lines if (start is None or x[0] >= pb.floor_s(start)) and (end is None or x[0] <= end)]
    samples = [s for t, s in (c.samples if c is not None else []) if (start is None or t >= start) and (done is None or t <= done[0])]
    ok, why = judge_old_dormant(samples or holder["samples"], after)
    led.check("S166-OLD-DORMANT", ok, why + f" (judged {'to the replay done line' if done else 'to the end: NO replay done line'})")
    led.close(final=True)


# ================================================================================================ T2-H (the desktop a real HOST)
def _run_host(g, calibrate: bool, lever) -> None:
    led = cb.Ledger(g, leg_catalog("host", calibrate), finals=("T2H-INI", "S166-TH-CAL"), width=DETAIL_W)
    ctx = _Ctx()
    ctx.field, ctx.lever = FARSHORE, lever
    try:
        _host(g, led, ctx)
    except HarnessError as err:
        g.note(f"the host leg raised: {str(err)[:400]}")
        led.close(f"not reached: the leg raised ({str(err)[:200]})")
    finally:
        _t2_teardown(g, led, ctx)
        if calibrate:
            stage = ctx.gstage or "old"
            is_old = not cb.has(ctx.base, HOST_GUEST) if ctx.base is not None else stage == "old"
            pred = HOST_OLD_PREDICTED if is_old else HOST_LEVER_PREDICTED.get(lever, ())
            led.close("not reached: the leg ended before this check")
            led.check("S166-TH-CAL", *judge_cal(led.failed() - {"S166-TH-CAL"}, pred, ctx.measured, () if is_old else pred))
        led.close(final=True)


def _host_preflight(g, led) -> bool:
    free, why = (False, f"COOP_PEER_PORT={PORT} is the owner's bridge port") if PORT == pb.OWNER_PORT else pb.port_free(PORT)
    if not free:
        led.check("T2H-PEER", False, why)
        led.close("not reached: the bench port is taken (nothing was edited)")
        return False
    if not pb.port_free(pb.OWNER_PORT)[0]:
        led.check("T2H-PEER", False, f"the owner's bridge is UP on 127.0.0.1:{pb.OWNER_PORT}: this host game launched on the owner's "
                                     "Memoria.ini dials it before any edit -- stop it first (never stopped by a bench)")
        led.close("not reached: the owner's bridge is up (nothing was edited)")
        return False
    return True


def _serve(g, ctx: _Ctx, phase: str, extra) -> object:
    """One serve-guest phase: its own process and TAP; waits for the HOST's connection and its host-wire line."""
    rd = cw._run_dir(g)
    tap = rd / f"serve-guest-{phase}.f9tape"
    args = ["--port", str(PORT), "--report", "off", "--walk", "roam", "--walk-out", f"{TH_OUT_S:g}", "--walk-load", f"{TH_LOAD_S:g}",
            "--tap", str(tap), "--status", "5", *extra]
    peer = pb.PeerProc("serve-guest", args, log_path=rd / f"coop_peer-serve-guest-{phase}.log",
                       out_path=rd / f"coop_peer-serve-guest-{phase}.out")
    peer.tap_path = tap
    g.note(f"starting: {peer.command_text()}")
    _mark(ctx, f"{phase}0")
    peer.start()
    ctx.peers.append(peer)
    peer.up = peer.wait_for(pb.PEER["listening"], 15.0, tick=lambda: _sample(g, ctx), poll=POLL_S)
    peer.conn = peer.wait_for(pb.PEER["host_connected"], TH_DIAL_S, tick=lambda: _sample(g, ctx), poll=POLL_S) if peer.up else None
    peer.hdr = peer.wait_for(pb.PEER["host_wire"], 5.0, tick=lambda: _sample(g, ctx), poll=POLL_S) if peer.conn else None
    _mark(ctx, phase)
    return peer


def _end_phase(g, ctx: _Ctx, peer, phase: str) -> list:
    _mark(ctx, f"{phase}_end")
    g.note(f"coop_peer serve-guest ({phase}): {peer.stop()}")
    try:
        cp = pb.coop_peer_module()
        _h, recs, _torn = cp.read_tape(peer.tap_path)
        return trailer_rows(recs, cp, direction=1)
    except Exception as err:                              # noqa: BLE001
        g.note(f"the {phase} tap does not read back: {err}")
        return []


def _host(g, led, ctx: _Ctx) -> None:
    rows = list(HOST_ROWS)
    if not _host_preflight(g, led):
        return
    cb.provenance(g)
    g.newgame()
    g.warp(FARSHORE)
    try:
        g.no_encounters(True)
    except HarnessError as err:
        g.note(f"noencounter refused ({str(err)[:160]})")
    g.wait_frames(45)
    ctx.gstage = stage_of(g.state)
    ctx.eng = pb.EngineLog(g.engine_log())
    ctx.guard = pb.IniGuard(Path(g.game_path) / "Memoria.ini", HOST_VALUES, label="coop-world-walk-t2-host", run_dir=cw._run_dir(g))
    try:
        g.note(ctx.guard.apply())
    except (OSError, RuntimeError) as err:
        led.check("T2H-PEER", False, f"the Memoria.ini edit failed: {err}")
        led.close("not reached: Memoria.ini could not be edited")
        return
    cfg = cb.poll(g, lambda s: bool(pb.hits(ctx.eng.lines(), "config", pred=lambda m: m.group(1) == "True" and m.group(2) == "host"
                                           and m.group(6) == CODE)), 12.0, "the host config line")
    if not cfg:
        g.warp(FARSHORE)
        cfg = cb.poll(g, lambda s: bool(pb.hits(ctx.eng.lines(), "config", pred=lambda m: m.group(2) == "host")), 12.0, "config")
    ok, why, _st = cw.walk_out(g)
    if not ok:
        led.check("T2H-PEER", False, f"the host's walk out failed: {why[:200]}")
        led.unreached(rows, "the host never reached the world map")
        return
    _wait(g, ctx, lambda s: judged(s) and s.world_id == WORLD, 30.0)
    g.note(f"the regression re-key: {_s166_rekey(g, ctx)}")   # [ff9mapkit netsync s167] an s167 host reads s166 exactly
    lever_note = _lever(g, ctx, ctx.lever) if ctx.lever else "no lever"
    g.note(lever_note)
    ctx.base = g.state
    # phase A: a frozen guest, a scene window, a gap
    a = _serve(g, ctx, "a", ["--state", "0x85", "--scene-at", f"{TH_SCENE_AT:g}", "--scene-for", f"{TH_SCENE_FOR:g}",
                             "--gap-at", f"{TH_GAP_AT:g}", "--gap-for", f"{TH_GAP_FOR:g}"])
    hdr = judge_live_header(a.hdr[1] if a.hdr else None, pb.probe_wire(g), side="host") if a.hdr else (False, "no host-wire line")
    relay = pb.hits(ctx.eng.lines(), "relay_up", pred=lambda m: m.group(3) == "host" and m.group(2) == CODE)
    p_ok = a.up is not None and a.conn is not None and hdr[0] and bool(relay) and bool(cfg)
    led.check("T2H-PEER", p_ok, f"wire: {hdr[1]}; config {bool(cfg)}; peer {a.up[1] if a.up else 'never listened'} / "
                                f"{a.conn[1] if a.conn else 'no HOST'}; engine {pb.show(relay, 1)}")
    if not p_ok:
        led.unreached(rows, "the instrument never started (T2H-PEER)")
        return
    # the gap by the HOST's OWN cache (never the wall: serve-guest's session clock is its own): arrivals stopped GAP_SEEN_MS, then back
    _wait(g, ctx, lambda s: _hg(s).get("place") == BW.WW_PLACE_WORLD and (_num(_lane(s).get("arrival_age_ms")) or 0) >= GAP_SEEN_MS,
          TH_A_S)
    _mark(ctx, "gap")
    _wait(g, ctx, lambda s: 0 <= (_num(_lane(s).get("arrival_age_ms")) or -1) < GAP_BACK_MS, TH_A_S)
    _mark(ctx, "gap_end")
    _wait(g, ctx, lambda s: False, TH_TAIL_S)
    tap_a = _end_phase(g, ctx, a, "a")
    smap_a = seq_map(tap_a)
    sa = _samples_between(ctx, "a0", "a_end")             # from the launch: its first frames land before the connection is read
    la = _since(ctx, "a0", "a_end")
    led.check("S166-TH-I", *judge_th_instrument(sa))
    led.check("S166-TH-LINES", *judge_th_lines(sa, la))
    walk = [s for s in _after_scene(_samples_between(ctx, "a0", "gap")) if judged(s) and _hg(s).get("place") == BW.WW_PLACE_WORLD
            and not (_num(_hg(s).get("state")) or 0) & BW.WW_ST_SCENE and (_num(_lane(s).get("arrival_age_ms")) or 0) < GAP_SEEN_MS]
    led.check("S166-TH-GHOST", *judge_ghost_on_oracle(walk, smap_a, min_samples=TH_MIN_SAMPLES, what="the tap"))
    if "gap" in ctx.events and "gap_end" in ctx.events:
        gbase = ctx.samples[ctx.events["gap"] - 1][1] if ctx.events["gap"] > 0 else ctx.base
        led.check("S166-TH-GAP", *judge_th_gap(gbase, _samples_between(ctx, "gap", "gap_end"),
                                               _samples_between(ctx, "gap_end", "a_end"), _since(ctx, "gap", "a_end")))
    else:
        led.check("S166-TH-GAP", False, f"not reached: the host's cache never read the gap (events {sorted(ctx.events)})")
    # phase B: a RELEASED guest -- judged from its FIRST frame on the host's cache: A's last sample is a frozen guest's (state b0 set),
    # every B frame (its follow-out, its load, its walk) carries b0 CLEAR
    b = _serve(g, ctx, "b", [])
    _wait(g, ctx, lambda s: sum(1 for x in _samples_between(ctx, "b0") if _hg(x).get("place") == BW.WW_PLACE_WORLD
                                and not (_num(_hg(x).get("state")) or 0) & BW.WW_ST_FROZEN) >= TH_MIN_SAMPLES * 2, TH_B_S)
    tap_b = _end_phase(g, ctx, b, "b")
    sb = _samples_between(ctx, "b0", "b_end")
    i_b = next((i for i, s in enumerate(sb) if _hg(s).get("place", -1) >= 0 and not (_num(_hg(s).get("state")) or 0) & BW.WW_ST_FROZEN),
               len(sb))
    led.check("S166-TH-RELEASED", *judge_th_released(sb[i_b:], _since(ctx, "b0", "b_end"), tap_b, seq_map(tap_b)))
    # phase C: --no-follow -- from its first frame on the host's cache (flags b0 clear)
    c = _serve(g, ctx, "c", ["--no-follow"])
    if not any(_hg(s).get("flags") == 0 for s in _samples_between(ctx, "c0")):
        _wait(g, ctx, lambda s: _hg(s).get("flags") == 0, TH_C_S)
    sc = _samples_between(ctx, "c0")
    i_c = next((i for i, s in enumerate(sc) if _hg(s).get("flags") == 0), None)
    if i_c is not None:
        k = ctx.events["c0"] + i_c                         # the first sample whose cache reads a C frame (flags b0 clear)
        ctx.events["c_in"] = k
        ctx.lines_at["c_in"] = ctx.line_counts[k] if k < len(ctx.line_counts) else _lines_n(ctx)
    else:
        _mark(ctx, "c_in")
    _wait(g, ctx, lambda s: False, TH_C_S)
    tap_c = _end_phase(g, ctx, c, "c")
    led.check("S166-TH-NOFOLLOW", *judge_th_nofollow(_samples_between(ctx, "c_in", "c_end"), _since(ctx, "c_in", "c_end"), tap_c))
    if ctx.lever == "hostlines":
        m = hostlines_measured(sa, la)
        ctx.measured.update({r: m for r in HOST_LEVER_PREDICTED["hostlines"]})
    elif ctx.lever == "ghost":
        m = ghost_off_measured(walk)
        ctx.measured.update({r: m for r in HOST_LEVER_PREDICTED["ghost"]})


# ================================================================================================ THE ROAM RECORDER (owner-gated)
def _run_record(g) -> None:
    led = cb.Ledger(g, leg_catalog("record", False), finals=("REC-INI",), width=DETAIL_W)
    ctx = _Ctx()
    ctx.field = FARSHORE
    try:
        _record(g, led, ctx)
    except HarnessError as err:
        g.note(f"the recording raised: {str(err)[:400]}")
        led.close(f"the recording raised before this check: {str(err)[:200]}")
    finally:
        for p in ctx.peers:
            if p is not None and p.how_ended is None:
                g.note(f"coop_peer serve-guest: {p.stop()}")
        if ctx.guard is not None:
            ok, why = ctx.guard.restore()
            led.check("REC-INI", ok, why)
        else:
            led.check("REC-INI", True, "Memoria.ini was never edited")
        led.close(final=True)


def _record(g, led, ctx: _Ctx) -> None:
    owner = pb.env_flag("COOP_WWT_RECORD_OWNER")
    bridge_down = pb.port_free(pb.OWNER_PORT)[0]
    st = g.state
    s166 = wire_of(st) == WIRE_NEW and cb.has(st, LANE)
    led.check("REC-OWNER", owner and bridge_down and s166 and not cb.CALIBRATE,
              f"COOP_WWT_RECORD_OWNER {'set' if owner else 'UNSET (the owner has not said go)'}; the owner's bridge "
              f"{'down' if bridge_down else 'UP (never stopped by a bench)'}; the host's wire {wire_of(st)} and the lane "
              f"{'published' if cb.has(st, LANE) else 'ABSENT'} (want an s166 host; round B's walk leg needs an s167 one: "
              f"{'s167' if cb.has(st, ww.WALK_PROBE) else 'NOT s167'})" + ("; COOP_CALIBRATE set: refused" if cb.CALIBRATE else ""))
    if not (owner and bridge_down and s166) or cb.CALIBRATE:
        led.close("THE OWNER GATE: nothing was edited, no tape was made (ROAM-TAPE.md)")
        return
    free, why = pb.port_free(PORT)
    if not free:
        led.check("REC-P0", False, why)
        led.close("the bench port is taken -- nothing was edited")
        return
    cb.provenance(g)
    g.newgame()
    g.note(cb.seed_party(g, back_to=FARSHORE))
    if g.state.field_id != FARSHORE:
        g.warp(FARSHORE)
    try:
        g.no_encounters(True)
    except HarnessError as err:
        g.note(f"noencounter refused ({str(err)[:160]})")
    g.poke(pb.MARKER_BYTE, pb.MARKER_VALUE)
    g.watch(*(pb.MARKER_BYTE * 8 + b for b in range(8)))
    m = cb.poll(g, lambda s: pb.marker_value(s) == pb.MARKER_VALUE, 5.0, "the marker") or g.state
    led.check("REC-M", pb.marker_value(m) == pb.MARKER_VALUE, f"byte {pb.MARKER_BYTE} reads {pb.marker_value(m)!r}")
    ctx.eng = pb.EngineLog(g.engine_log())
    ctx.guard = pb.IniGuard(Path(g.game_path) / "Memoria.ini", HOST_VALUES, label="coop-world-walk-t2-record", run_dir=cw._run_dir(g))
    g.note(ctx.guard.apply())
    cfg = cb.poll(g, lambda s: bool(pb.hits(ctx.eng.lines(), "config", pred=lambda mm: mm.group(2) == "host" and mm.group(6) == CODE)),
                  12.0, "the host config line")
    led.check("REC-P1", bool(cfg), pb.show(pb.hits(ctx.eng.lines(), "config"), 1))
    if not cfg:
        led.close("the host config never applied")
        return
    tdir = roam_tape_dir()
    tdir.mkdir(parents=True, exist_ok=True)
    stage = "s167" if cb.has(g.state, ww.WALK_PROBE) else "s166"   # [ff9mapkit netsync s167] the tape named by the host's stage
    ctx.tape = tdir / f"{time.strftime('%Y%m%d-%H%M%S')}-host{FARSHORE}-world-roam-{stage}.f9tape"
    rd = cw._run_dir(g)
    peer = pb.PeerProc("serve-guest", ["--port", str(PORT), "--report", "live", "--no-follow", "--tap", str(ctx.tape), "--status", "5"],
                       log_path=rd / "coop_peer-serve-guest-roam.log", out_path=rd / "coop_peer-serve-guest-roam.out")
    ctx.peers.append(peer)
    peer.start()
    up = peer.wait_for(pb.PEER["listening"], 15.0)
    led.check("REC-P0", up is not None, up[1] if up else f"no listening line: {peer.tail()}")
    conn = peer.wait_for(pb.PEER["host_connected"], 20.0) if up else None
    hdr = peer.wait_for(pb.PEER["host_wire"], 5.0) if conn else None
    hw = wire_line(hdr[1], "host") if hdr else None
    led.check("REC-P2", conn is not None and hw is not None and hw[0] == WIRE_NEW, f"{conn[1] if conn else 'no HOST'}; {hdr[1] if hdr else 'no host-wire line'}")
    if conn is None:
        led.close("the host never dialled serve-guest")
        return
    time.sleep(INSTRUMENT_FIELD_S)                       # the host on 6603: the replay's pairing room
    ok, why, _st = cw.walk_out(g)
    led.check("REC-WX", ok, why)
    if not ok:
        led.close("the walk out failed")
        return
    st = cb.poll(g, lambda s: judged(s), 30.0, "the blocks")
    led.check("REC-RB", st is not None, f"block_ready on {getattr(st, 'world_id', None)}" if st else "never block_ready")
    walks, xs, turned = [], [], False
    for item in ROAM_PLAN:
        op = item[0]
        if op == "stand":
            end = time.time() + item[1]
            while time.time() < end:
                s = g.state
                xs.append(s.world_x)
                time.sleep(0.1)
            if not walks and op == "stand":
                here = g.state
                d = torus(here.world_x or 0.0, here.world_z or 0.0, *FS_LANDING) if here.world_x is not None else None
                if "REC-RL" not in led.done:
                    led.check("REC-RL", d is not None and d <= cw.ROUTE_TOL, f"stood at ({here.world_x}, {here.world_z}), {d} u from FS_LANDING")
        elif op == "turn":
            g.send(f"hold leftbumper {int(item[1])}", f"wait {int(item[1]) + 2}")
            turned = True
        elif op == "walk":
            try:
                g.world_face(item[1])
                r = g.world_approach(item[1], item[2])
                walks.append((item, r.get("outcome"), r.get("progress")))
                xs += [row.get("x") for row in r.get("trace", [])]
            except HarnessError as err:
                walks.append((item, f"raised: {str(err)[:80]}", 0.0))
        elif op == "tile":
            st = cw.teleport_settle(g, item[1])
            d = torus(st.world_x or 0.0, st.world_z or 0.0, *item[1]) if st.world_x is not None else None
            led.check("REC-RT", d is not None and d <= 8.0, f"teleported to ({st.world_x}, {st.world_z}), {d} u from the tile")
        elif op == "enter":
            g.wait_frames(cw.PROMPT_FRAMES)
            g.press("confirm")
            e = cb.poll(g, lambda s: s.ui_state == "FieldHUD" and s.field_id == item[1], 20.0, f"field {item[1]}")
            led.check("REC-RE", e is not None, f"FieldHUD {item[1]}" if e else f"never entered {item[1]}")
    led.check("REC-RW", all(o == "reached" or (p or 0) >= 0.6 * it[2] for it, o, p in walks) and turned,
              f"legs {[(it[1], it[2], o, p) for it, o, p in walks]}; the L1 turn {'held' if turned else 'NOT held'}")
    xs = [x for x in xs if x is not None]
    led.check("REC-RS", any((a >= W - 64 and b < 64) or (b >= W - 64 and a < 64) for a, b in zip(xs, xs[1:])),
              f"world x reads {len(xs)}; min {min(xs) if xs else None} max {max(xs) if xs else None}")
    g.note(f"coop_peer serve-guest: {peer.stop()}")
    cp = pb.coop_peer_module()
    try:
        header, records, torn = cp.read_tape(ctx.tape)
        led.check("REC-T", not torn, f"{ctx.tape.name}: {len(records)} record(s), torn {torn} B")
        facts = roam_tape_facts(records, cp, header=header)
        f_ok, bad = facts_ok(facts)
        w_ok = facts["windows"]["bh23"] is not None and facts["windows"]["bh6"] is not None
        led.check("REC-RF", f_ok and w_ok, ("the facts hold" if f_ok else "; ".join(bad)) + f"; windows {facts['windows']}")
        if f_ok and w_ok:
            (tdir / ROAM_POINTER).write_text(json.dumps({"tape": str(ctx.tape)}), encoding="utf-8")
            g.note(f"{ROAM_POINTER} -> {ctx.tape}")
    except Exception as err:                              # noqa: BLE001
        led.check("REC-T", False, f"the tape does not read back: {err}")


# ================================================================================================ the duo
#: duo.py's CLI calls ``d.pair(**PAIR)``: both games New Game onto 6603 (the host first)
PAIR = {"field": FARSHORE}


def run_duo(d) -> None:
    """The round-A duo: every row recorded (strict off); COOP_CALIBRATE=1 judges S166-D-CAL by the GUEST's stage (OLD) or the lever.
    [ff9mapkit netsync s167] COOP_WWT_DUO=b runs round B's duo instead (_run_duo_b)."""
    if DUO_MODE == "b":
        _run_duo_b(d)
        return
    calibrate = cb.CALIBRATE
    lever = lever_of("duo", LEVER_RAW) if calibrate and LEVER_RAW else None
    strict, d.strict = d.strict, False
    failed, done, measured, sent = [], set(), {}, []
    marks = {}
    hold = {"asked": False, "sent": False, "released": False}      # [W2c] D-LINES' `worldfollow hold` on the guest

    def check(cid, ok, detail):
        if cid in done:
            return
        done.add(cid)
        if not ok:
            failed.append(cid)
        d.check(bool(ok), f"{cid}: {DUO_CHECKS.get(cid, cid)}", str(detail)[:DETAIL_W], cid=cid)

    def rest(why):
        for cid in DUO_ORDER:
            if cid != "S166-D-SHARED" and cid not in done:
                check(cid, False, f"not reached: {why}"[:DETAIL_W])
    stage = "old"
    try:
        marks["host"], marks["guest"] = cb.mark(d.host), cb.mark(d.guest)
        stage = stage_of(d.guest.state)
        _duo(d, check, rest, lever, sent, measured, hold)
    except HarnessError as err:
        d.note(f"the duo raised: {str(err)[:400]}")
        rest(f"the duo raised ({str(err)[:200]})")
    finally:
        if (hold["asked"] or hold["sent"]) and not hold["released"]:
            # [W2c] EVERY failure path: a red, an early return or a raise never leaves the guest held for the legs that follow (the
            # harness release also clears it -- HarnessReleaseWorldFollow -- this is the leg's own, at once). Keyed on the ASK, not
            # the accept: a hold whose accept was lost (a raise / a timeout after the engine took it) is released too; and never let
            # the backstop itself skip the rows below (any exception is noted, never raised out of the finally)
            try:
                d.note(f"the backstop: {_release_guest(d.guest, hold)}")
            except Exception as err:                       # noqa: BLE001 - the verdict rows below must still be written
                d.note(f"the backstop `worldfollow release` raised: {str(err)[:160]}")
        try:
            hl, gl = cb.new(d.host, marks.get("host", 0)), cb.new(d.guest, marks.get("guest", 0))
        except HarnessError:
            hl, gl = [], []
        check("S166-D-SHARED", *wf.judge_shared(hl, gl))
        rest("the duo ended before this row")
        for who, g in (("host", d.host), ("guest", d.guest)):
            if sent:
                try:
                    ok, why = cb.try_ns(g, "worldwalk", "clear")
                    d.note(f"`worldwalk clear` on the {who}: {'ok' if ok else why[:120]}")
                except HarnessError:
                    pass
        if calibrate:
            is_old = stage != "a4"
            pred = DUO_OLD_PREDICTED if is_old else DUO_LEVER_PREDICTED.get(lever, ())
            skip = set() if D_BATTLE else {"S166-D-BATTLE"}        # not run by configuration (the stand-in duo): out of the verdict, named
            pred = tuple(r for r in pred if r not in skip)
            ok, why = judge_cal(set(failed) - skip, pred, measured, () if is_old else pred)
            why += f"; not run (configuration): {sorted(skip) or 'none'}"
            d.check(ok, "S166-D-CAL: CALIBRATION -- exactly the predicted duo rows red (OLD by the guest's stage, else the lever's)",
                    f"guest {stage}, lever {lever}: {why}", cid="S166-D-CAL")
        d.strict = strict


def _tap_both(d):
    th, tg = wf.Tap(d.host, TAP_S), wf.Tap(d.guest, TAP_S)
    th.start()
    tg.start()
    return th, tg


def _walk_out_tapped(d, tries: int = 3) -> tuple:
    """[W2b] cw.walk_out's route with D-LINES' Taps started BEFORE THE GUEST CAN LEAVE: calibrate_axes (the FS_DOOR hazard, ``tries``
    tries, a re-warp between), the walk into the door (strict=False, halt_on_transition) -- then _tap_both, while the host is still in
    its own exit (the guest's follow-out waits for the host live on the world). From there the Taps are the ONLY readers (never
    walk_out's own wait_world / world_settle beside them, nor its `before_walk` hook). -> (ok, why, th, tg); the Taps None unless ok."""
    host = d.host
    for attempt in range(tries):
        try:
            host.calibrate_axes(hazards=[cw.FS_DOOR], recalibrate=attempt > 0)
            break
        except HarnessError as err:
            if attempt == tries - 1:
                return False, f"calibrate_axes on {FARSHORE} failed {tries}x: {str(err)[:200]}", None, None
            d.note(f"calibrate_axes retry {attempt + 1}: {str(err)[:160]}")
            try:
                host.warp(FARSHORE)
                host.wait_frames(90)
            except HarnessError as err2:
                return False, f"the re-warp to {FARSHORE} failed: {str(err2)[:200]}", None, None
    try:
        host.walk_to(*cw.FS_EXIT, strict=False, halt_on_transition=True)
    except HarnessError as err:
        return False, f"the walk out never left {FARSHORE}: {str(err)[:240]}", None, None
    th, tg = _tap_both(d)
    return True, "walked into the door; the Taps started", th, tg


def _hold_guest(guest, gs, hold: dict) -> str:
    """[W2c] `worldfollow hold` on the guest, s165's D-FO2 way: PROBE FIRST (never sent to an engine without `netsync.world.out`), then
    the read back (out.hold; its why reads 'hold' only once the host is live on the world -- judged at the release). Marks ``hold``."""
    if not cb.has(gs, wf.PROBE):
        return f"no `{wf.PROBE}` on the guest: `worldfollow hold` never sent (the probe-first rule; D-LINES' premise reads it unheld)"
    hold["asked"] = True                       # BEFORE the send: a raise or a lost accept still gets run_duo's backstop release
    ok, why = wf._wf(guest, "hold")
    if not ok:
        return f"`worldfollow hold` REFUSED on the guest ({why[:120]}): D-LINES' premise reads it unheld"
    hold["sent"] = True
    rb = guest.state
    return (f"`worldfollow hold` on the guest: read back out.hold {wf._o(rb, 'hold')!r}, why {wf._o(rb, 'why')!r} (the START waits until "
            "the host is live)")


def _release_guest(guest, hold: dict) -> str:
    """[W2c] `worldfollow release` on the guest (``hold["released"]`` once accepted)."""
    ok, why = wf._wf(guest, "release")
    hold["released"] = hold["released"] or ok
    return f"`worldfollow release` on the guest: {'ok' if ok else 'REFUSED: ' + why[:120]}"


def _await_host_live(th, timeout: float):
    """[W2c] The HOST Tap's own first sample LIVE on WORLD (own_live: its own place 4, judged) -> its wall stamp, or None at ``timeout``.
    Reads ONLY the Tap's buffer."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        t = next((t for t, s in list(th.samples) if s.world_id == WORLD and own_live(s)), None)
        if t is not None:
            return t
        time.sleep(0.02)
    return None


def _await_guest_held(tg, timeout: float):
    """[W2c verify] The GUEST Tap's own LAST sample once it reads the hold ENGAGED (out.hold true, why 'hold'), or at ``timeout`` its
    last sample as it stands (None: none) -- d_lines_premise's ``held``, the guest's last sample before the release. Reads ONLY the
    Tap's buffer."""
    deadline = time.time() + timeout
    while True:
        ss = list(tg.samples)
        last = ss[-1][1] if ss else None
        if last is not None and wf._o(last, "hold") is True and wf._o(last, "why") == "hold":
            return last
        if time.time() >= deadline:
            return last
        time.sleep(0.02)


def _walk_host(host, th, riding: bool = False, button: str = "up") -> str:
    """[W2b] THE CLOSED-LOOP WALK: hold "up" up to D_WALK_FRAMES and stop as soon as EITHER the judge's own tx_moved OR the Tap samples'
    own world x/z (world_moved: a dark trailer never walks on) reached D_MOVE_U + D_MOVE_MARGIN_U, or at the wall deadline D_WALK_S; then
    the release and D_WALK_TAIL_S of tail. Reads ONLY the Tap's own buffer (``th.samples``) -- never a second reader of the driven game.
    [ff9mapkit netsync s167] Any game and ``button`` (round B walks the GUEST: D-W1, D-BATTLE's `down` apart)."""
    goal = D_MOVE_U + D_MOVE_MARGIN_U
    t0 = time.time()
    host.hold(button, D_WALK_FRAMES)
    deadline, why = t0 + D_WALK_S, "the deadline"
    while time.time() < deadline:
        ss = [s for _t, s in list(th.samples)]
        if tx_moved(ss, riding) >= goal or world_moved(ss) >= goal:
            why = "the distance"
            break
        time.sleep(0.02)
    # sent unawaited, like the hold: Channel.send still makes ONE state read first (it confirms the hold's accept -- channel.py
    # _await_accept), the same read the hold made; a release after the hold ran out is a no-op (it never presses)
    host.send(f"release {button}", wait=False)
    time.sleep(D_WALK_TAIL_S)
    return f"the walk stopped on {why} after {time.time() - t0:.1f} s"


def _duo(d, check, rest, lever, sent: list, measured: dict, hold: dict) -> None:
    host, guest = d.host, d.guest
    hs, gs = host.state, guest.state
    both = (hs.ui_state == "FieldHUD" and hs.field_id == FARSHORE and gs.ui_state == "FieldHUD" and gs.field_id == FARSHORE
            and cw._s(gs, "mirroring") is True)
    s166 = all(stage_of(x) == "a4" and wire_of(x) in (None, WIRE_NEW) for x in (hs, gs))
    check("S166-D0", both and s166, f"host {hs.ui_state} {hs.field_id} ({stage_of(hs)}, wire {wire_of(hs)}); guest {gs.ui_state} "
                                    f"{gs.field_id} ({stage_of(gs)}, wire {wire_of(gs)}), mirroring {cw._s(gs, 'mirroring')!r}")
    if not (both and s166):
        rest("the pair is not an s166 pair on 6603 (D0)")
        return
    for who, g in (("host", host), ("guest", guest)):     # [ff9mapkit netsync s167] THE REGRESSION RE-KEY: an s167 pair reads s166
        ok, why = ww.s166_lever_set(g, g.state)
        if why:
            sent.append("s166-set")
            d.note(f"the regression re-key on the {who}: {why}")
    # the lever, on the role it names (BEFORE the walk out: THE DUO CANNOT PULL A SELFTEST-ROLE LEVER -- these are any-role)
    if lever == "ghost":
        for g in (host, guest):
            ok, _w = _ww(g, "ghost", "off")
            sent.append("ghost") if ok else None
    elif lever in ("sticky", "dot"):
        op, word = LEVER_OPS[lever]
        ok, _w = _ww(guest, op, word)
        sent.append(op) if ok else None
    # D-LINES + D-G2: the host walks out, the guest follows out. [W2b] Encounters off FIRST, on the field: the booster lives for the process
    # and survives the world load, so no random battle can take the host while only the Taps read it
    try:
        host.no_encounters(True)
    except (HarnessError, AttributeError) as err:
        d.note(f"noencounter refused on {FARSHORE} ({str(err)[:120]})")
    hat, gat = cb.mark(host), cb.mark(guest)
    # [W2c] THE HOLD, BEFORE THE WALK OUT (a leg-level step: the same route under every lever -- ghost / sticky / dot are `worldwalk`
    # levers, this is `worldfollow`'s START hold, orthogonal to them): the guest's follow-out waits for the host LIVE on the world
    d.note(f"D-LINES: {_hold_guest(guest, gs, hold)}")
    ok, why, th, tg = _walk_out_tapped(d)
    if not ok:
        rest(f"the host's walk out failed ({why[:160]})")
        return                                            # (run_duo's finally releases the hold)
    # [W2c] ...until the HOST Tap reads the host live on WORLD (its own place 4, judged), the settle, the held read back off the GUEST
    # Tap's own last sample -- [W2c verify] once it reads the hold ENGAGED (up to D_HOLD_READ_S) -- then the release
    t_live = _await_host_live(th, cw.WORLD_S)
    if t_live is not None:
        time.sleep(D_HOLD_SETTLE_S)
    held = None
    if hold["sent"]:
        held = _await_guest_held(tg, D_HOLD_READ_S)
        d.note(f"D-LINES: the host live {'at ' + _hms(t_live) if t_live else 'NEVER'}; the guest's last sample read why "
               f"{wf._o(held, 'why') if held is not None else None!r}; {_release_guest(guest, hold)}")
    # ...the host's landing and the guest's, read off the Taps' OWN samples (they are the only readers now)
    deadline = time.time() + cw.WORLD_S
    hland = None
    while time.time() < deadline and hland is None:
        hland = wf.first_judged([s for _t, s in list(th.samples) if s.ui_state == "WorldHUD" and s.world_id == WORLD])
        time.sleep(0.1)
    t_host = next((t for t, s in list(th.samples) if s is hland), None) or _dt.datetime.now()
    deadline = time.time() + D_LAND_S
    while hland is not None and time.time() < deadline \
            and wf.first_judged([s for _t, s in list(tg.samples) if s.ui_state == "WorldHUD"]) is None:
        time.sleep(0.1)
    time.sleep(D_S)
    hsamp, gsamp = th.stop(), tg.stop()
    try:
        host.no_encounters(True)                          # (walk_out's own call, kept: no Tap reads the host now)
    except (HarnessError, AttributeError) as err:
        d.note(f"noencounter refused on the world map ({str(err)[:120]})")
    r_ok, r_why = cw.judge_route(hland) if hland is not None else (False, f"no judged host sample on {WORLD} in {cw.WORLD_S:g} s")
    if not r_ok:
        check("S166-D-LINES", False, f"not reached: the host's walk out never landed ({r_why[:200]})")
        rest(f"the host's walk out failed ({r_why[:160]})")
        return
    land = wf.first_judged([s for _t, s in gsamp if s.ui_state == "WorldHUD"])
    t_land = next((t for t, s in gsamp if s is land), None)
    gap = f"{(t_land - t_host).total_seconds():.1f} s after the host's first judged world sample" if t_land else "never"
    check("S166-D-LINES", *judge_d_lines([s for _t, s in hsamp], cb.new(host, hat), cb.new(guest, gat), land is not None,
                                         d_lines_premise(hsamp, gsamp, held)))
    if land is None:
        rest("the guest never landed on the world map")
        return
    gxz = wf.world_xz(guest.state)
    th2 = wf.Tap(host, TAP_S)
    th2.start()
    time.sleep(D_S)
    h2 = th2.stop()
    check("S166-D-G2", *judge_d_g2([s for _t, s in h2], gxz, gap))
    if lever == "ghost":
        measured["S166-D-G2"] = ghost_off_measured([s for _t, s in h2])
    # D-G1: the host walks
    own0 = wf.world_xz(guest.state)
    th, tg = _tap_both(d)
    d.note(f"D-G1: {_walk_host(host, th)}")
    hsamp, gsamp = th.stop(), tg.stop()
    own1 = wf.world_xz(guest.state)
    check("S166-D-G1", *judge_d_g1([s for _t, s in gsamp], [s for _t, s in hsamp], own0, own1))
    check("S166-D-TRAILER", *judge_d_trailer([s for _t, s in hsamp], [s for _t, s in gsamp]))
    if lever == "ghost":
        measured["S166-D-G1"] = ghost_off_measured([s for _t, s in gsamp])
    # D-BATTLE: the host's world battle, both warm returns
    if D_BATTLE:
        _duo_battle(d, check, lever, measured)
    else:
        check("S166-D-BATTLE", False, "not run: COOP_WWT_DUO_BATTLE=0 (the stand-in duo has no diorama model)")
    # D-DOTRIDE: `vehicle 1` on the host, the guest's minimap on, the host moves
    try:
        guest.press("select")
        guest.wait_frames(20)
        host.vehicle(1)
        host.wait_frames(20)
        th, tg = _tap_both(d)
        d.note(f"D-DOTRIDE: {_walk_host(host, th, riding=True)}")
        hsamp, gsamp = th.stop(), tg.stop()
        check("S166-D-DOTRIDE", *judge_d_dotride([s for _t, s in gsamp], [s for _t, s in hsamp]))
        if lever == "dot":
            measured["S166-D-DOTRIDE"] = dot_lever_measured([s for _t, s in gsamp])
        host.vehicle(0)
        host.wait_frames(20)
    except HarnessError as err:
        check("S166-D-DOTRIDE", False, f"not reached: `vehicle 1` refused ({str(err)[:200]})")
    # D-REJOIN: the host onto the tile, Confirm into 300
    gbase, gat3 = guest.state, cb.mark(guest)
    tg = wf.Tap(guest, TAP_S)
    tg.start()
    try:
        cw.teleport_settle(host, ICE_TILE)
        host.wait_frames(cw.PROMPT_FRAMES)
        host.press("confirm")
        hin = cb.poll(host, lambda s: s.ui_state == "FieldHUD" and s.field_id == ICE_CAVERN, cw.FIELD_S, "the host on 300")
    except HarnessError as err:
        hin = None
        d.note(f"the host's entry raised: {str(err)[:200]}")
    if hin is not None:
        cb.poll(guest, lambda s: s.ui_state == "FieldHUD" and s.field_id == ICE_CAVERN, wf.REJOIN_S, "the guest on 300")
        time.sleep(1.0)
    gsamp = tg.stop()
    hsamp = []
    for _ in range(3):
        try:
            hsamp.append((None, host.state))
        except HarnessError:
            pass
    gl = [s for _t, s in gsamp]
    rejoin = cw.judge_rejoin_land(gl, gbase, cb.new(guest, gat3), field=ICE_CAVERN) if hin is not None else (False, "the host never entered 300")
    check("S166-D-REJOIN", *judge_d_rejoin(gl, [s for _t, s in hsamp], rejoin))
    if lever == "sticky":
        # [W2b] INERT here by THE ARM-FIRST ORDER (no live guest sample reads the host on place 2): reported, never a measure
        d.note(f"`ghost sticky` on REJOIN (REPORTED, inert by THE ARM-FIRST ORDER): its shape seen {sticky_measured(gl)}")
    elif lever == "ghost":
        measured["S166-D-REJOIN"] = ghost_off_measured(gl)


def _duo_battle(d, check, lever, measured: dict) -> None:
    host, guest = d.host, d.guest
    bh, bg = host.state, guest.state
    hat, gat = cb.mark(host), cb.mark(guest)
    th, tg = _tap_both(d)
    try:
        host.world_battle(D_SCENE, group=D_GROUP, rand=True, timeout=60.0)
        host.fight(timeout=D_FIGHT_S, finish=True, max_turns=1_000_000)
        host.wait_world(timeout=D_RETURN_S)
        cb.poll(guest, lambda s: s.ui_state == "WorldHUD" and judged(s), D_RETURN_S, "the guest's warm return")
        time.sleep(D_S)
    except HarnessError as err:
        d.note(f"the duo battle raised: {str(err)[:200]}")
    hsamp, gsamp = th.stop(), tg.stop()
    ah, ag = host.state, guest.state
    check("S166-D-BATTLE", *judge_d_battle(bh, ah, bg, ag, cb.new(host, hat), cb.new(guest, gat), load_windows(hsamp),
                                           load_windows(gsamp), [s for _t, s in gsamp]))
    if lever == "ghost":
        measured["S166-D-BATTLE"] = (_d(bh, ah, _ghost, "mints") or 0) >= 1 and ghost_off_measured([s for _t, s in gsamp[-20:]])
    elif lever == "sticky":
        # [W2b] the lever's shape: a SHOWN ghost on the host's place 2 (its swirl) -- a Tap that missed the swirl reads NOT measured
        measured["S166-D-BATTLE"] = sticky_measured([s for _t, s in gsamp])


# ================================================================================================ [ff9mapkit netsync s167] ROUND B: T2 + DUO
# Round B's two-role rows (S166-DESIGN.md "The bench": the Round B rows table's W-STALLHOLE, T2-B, the Duo row and decision 23's co-op
# close; W1's contract_final for every key, op and line). Every leg reads the STAGE off the probe (`netsync.world.walk` / `fp` /
# `walk.map`, ww.B_PROBES): no round-B op is ever sent to s166, and every row then MEASURES s166's shape (OLD). The levers are any-role
# (`netsync worldwalk walk|stallhold|fullmap|minimap ...`: THE DUO CANNOT PULL A SELFTEST-ROLE LEVER -- none of these is one).
DUO_MODE = (os.environ.get("COOP_WWT_DUO") or "a").strip().lower()
B_PROBES = ww.B_PROBES
WALK_PROBE = ww.WALK_PROBE
#: each round-B leg's calibration levers (COOP_WWT_LEVER; unset = the leg's first) and the duo's
B_T2_LEVERS = {"walk": ("walk",), "stallhole": ("stallhold", "walk"), "hostb": ("walk",)}
DUO_B_LEVERS = ("walk", "fullmap")
#: a lever -> its `netsync worldwalk` ops, pulled on the game under test (the duo: the GUEST) before the leg and held through it.
#: `fullmap old` is s166 exactly only beside `minimap old` (under `fullmap old` alone decision 27 closes a walker's minimap instead)
B_LEVER_OPS = {"walk": (("walk", "off"),), "stallhold": (("stallhold", "old"),), "fullmap": (("fullmap", "old"), ("minimap", "old"))}
CAPS_S167 = BW.WW_OWN_CAPS_WALK
# ---- the times, the distances, the stands
B_READY_S = ww.WALK_READY_S     # a landing -> walk.free (fp.ready after the world load, the hold taking the host's frames)
B_CASE_S = ww.CASE_S            # an op -> its verdict published
FP_READY_S = 25.0               # the walk leg's calibration visit: the walk out -> fp.ready (the CRC over the world's override reads)
FAR_U = 150.0                   # WR-REJOIN-FAR / D-REJOIN-FAR: the guest at least this far (torus) from the host when the host enters
B_POSE_TOL = 4.0                # D-BATTLE: the warm return at the guest's OWN pose within this
D_APART_U = 10.0                # ...which stands at least this far from the host's when the battle starts
STALL_FROM_S = 4.0              # stallhole: `--from` the host's world-live second + this (on foot past its block load)
STALL_ROOM_S = 15.0             # ...the replay's start -> the first window (the dial, the session live, the guest paired on the world)
STALL_GAP_S = BH23_S            # W-STALLHOLE's blackhole (the design's 2.3 s: the lane passes StaleMs 2000 and comes back)
STALL_PRESS_S = 3.5             # a PRESS window: StaleMs 2000 + room for a press past it (2.3 s leaves ~300 ms -- one harness poll)
STALL_RECOVER_S = 4.0           # between windows: frames back, the freeze settled
STALL_TAIL_S = 1.5              # a window's end -> judged on this long (the re-freeze edge s166 prints lands here)
STALL_PAIR_S = 20.0             # the replay's start -> the world-paired guest read frozen
#: a sample is IN the stall once the lane's arrival age passed StaleMs + this: the session's own verdict (`_sessionState`, recomputed once
#: per Update, and GetRemote's Valid read on the publishing frame) may lag the lane's clock by a frame or so at the cliff. The 2.3 s blackhole
#: leaves only 300 ms past StaleMs, so this stays small (~3 frames); a PRESS waits PRESS_PAST_MS (its 3.5 s window has the room)
STALL_SEEN_MS = 100
PRESS_PAST_MS = 300
PRESS_WATCH_S = 4.0             # a press -> watched this long (s165's fade + Field() land inside it)
#: W-STALLHOLE's place-52 clause: a stand on a quicksand cell of the guest's OWN world ("x,z"); unset = not run (the walk worlds carry no
#: quicksand: the real one is WORLD03/09's cell (38, 8) -- an in-game run names it here once K1 places a world-paired guest there)
SAND_AT = ww._b_xz(os.environ.get("COOP_WWT_SAND_AT"), None)
THB_PHASE_S = 6.0               # T2-HB: a phase's guest on place 4 -> watched this long
THB_MIN = 6                     # ...its line asked on at least the last this many place-4 samples
THB_SETTLE = 4                  # ...the first this many place-4 samples skipped (the line's edge, the publish skew)
#: T2-HB's serve-guest phases (each its own process and tap): the control first, then each s167 host line
THB_PHASES = (("quiet", ()), ("older", ("--caps", "1")), ("fp", ("--state", "0x95", "--digest", "dead")),
              ("cant", ("--state", "0x85", "--walk-why", "pairing")))
THB_NAME = {"older": "older", "fp": "fp_differs", "cant": "cant_walk"}
THB_WORDS = {"older": BW.WORDS_WW_HOST_OLDER, "fp": BW.WORDS_WW_HOST_FP_DIFFERS, "cant": BW.WORDS_WW_HOST_CANT_WALK}
D_WAIT_S = 4.0                  # D-REJOIN-WAIT: the host on 300 while the guest's rejoin waits (control off) this long
D_FOLLOW_S = 40.0               # a host's field warp / walk out -> the guest followed

# ---- the catalogs
B_T2_COMMON = {
    "T2-TAPE": ("the ROAM tape (COOP_TAPE_WORLD_ROAM recorded on an s167 host: caps b1, its digest, section 11) or THE INSTRUMENT (a "
                "SYNTHETIC s167 host from ROAM_PLAN -- the walk leg's calibrated to this guest's OWN 9011 fingerprint) reads back, its "
                "facts and the leg's windows"),
    "T2-PEER": T2_COMMON["T2-PEER"] + "; THE LIVE HEADER: coop_peer's guest-wire line against the game's netsync.wire",
    "T2-SAVE": T2_COMMON["T2-SAVE"], "T2-INI": T2_COMMON["T2-INI"]}
WR_CHECKS = {
    "S167-WR-FREE": "T2-B: the guest paired on 6603 (mirroring) and followed the ROAM host out walks its own copy -- walk.free within "
                    "B_READY_S of the landing, fp 'match' against the host's digest, `hold up` moves >= WALK_U, freeze.on still true, "
                    "the trailer's b1",
    "S167-WR-REFUSE": "T2-B: `worldwalk fp fake dead` on the guest -- frozen fp_mismatch, its line naming the component off the HOST's "
                      "real section 11 ('world map meshes'), host_section set (mask 0x3F), one mismatch line, b4, held; `fp act`: free "
                      "again",
    "S167-WR-REJOIN-FAR": "T2-B: the guest walks away on its own (>= D_MOVE_U) and stands >= FAR_U from the host, free, when the host "
                          "Confirms into 300 -- the rejoin pulls it from there: FieldHUD 300, the landed line",
}
WR_GATE = {"S167-WR-GATE": "the OWNER-GATED tape: COOP_TAPE_WORLD_ROAM recorded on an s167 host (ROAM-TAPE.md) -- RED on THE "
                           "INSTRUMENT (a synthetic host: never a substitute) and on an s166-recorded tape ('an older build': no caps b1)"}
SH_CHECKS = {
    "S167-WR-PAIR": "T2-B: the guest on 9011 BEFORE the session (its own walk out), the ROAM host replayed `--from` a second on 9011 -- it "
                    "pairs ON THE WORLD MAP: frozen, never mirroring, no follow-out (out.starts +0), walk.why 'pairing' with its words",
    "S167-W-STALLHOLE": "W-STALLHOLE: `--blackhole-at` 2.3 s on the world-paired guest -- the freeze held on every sample (freeze.on; "
                        "walk.stall_held once the lane passed StaleMs), freeze.edges unmoved across it, no lift line",
    "S167-W-STALLHOLE-KEYS": "W-STALLHOLE: inside a stall (a 3.5 s blackhole, the press past StaleMs) Confirm at ICE_TILE -- freeze.keys "
                             "+>=1, never 300 (no FieldHUD, no next_mode 1); with COOP_WWT_SAND_AT a place-52 press: no local battle "
                             "(freeze.battles +1 -- the skip -- or freeze.keys +1 -- the mask: K1 names which)",
}
THB_CHECKS = {
    "S167-THB-QUIET": "T2-HB (the control): a walking v15 guest of the host's own build (caps auto, digest echo, state 0x86) on the s167 "
                      "host's 9011 -- none of the s167 host lines, no walk log line, the host's ghost of it shown",
    "S167-THB-OLDER": "T2-HB: serve-guest `--caps 1` (an s166-shaped guest) -- world.line asked 'older' with its words, drawn, and one "
                      "'host world: the partner's walk -- older' line",
    "S167-THB-FP": "T2-HB: `--state 0x95 --digest dead` (b4: the guest's map differs) -- 'fp_differs' with its words, drawn, its walk "
                   "line; the host's own fingerprint line (the guest's 0x0000DEAD) once",
    "S167-THB-CANT": "T2-HB: `--state 0x85 --walk-why pairing` (frozen, not walking, its class to a b1 host) -- 'cant_walk' with its "
                     "words, drawn, its walk line",
}
B_T2_CHECKS = {"walk": WR_CHECKS, "stallhole": SH_CHECKS, "hostb": THB_CHECKS}
B_T2_ROWS = {leg: tuple(c) for leg, c in B_T2_CHECKS.items()}
#: [calibration] OLD on s166 (the live b24e0123): each leg's rows red, each MEASURING s166's shape (B_T2_MEASURE); T2-HB's control stays
#: green there (an s166 host never speaks an s167 line: its OLD is its NEW)
B_T2_OLD_PREDICTED = {"walk": B_T2_ROWS["walk"], "stallhole": B_T2_ROWS["stallhole"],
                      "hostb": ("S167-THB-OLDER", "S167-THB-FP", "S167-THB-CANT")}
#: [calibration] LEVER_PREDICTED on s167, by (leg, lever): the lever restores s166, so each predicted row measures the same shape
B_T2_LEVER_PREDICTED = {("walk", "walk"): B_T2_ROWS["walk"],
                        ("stallhole", "stallhold"): ("S167-W-STALLHOLE", "S167-W-STALLHOLE-KEYS"),
                        ("stallhole", "walk"): ("S167-WR-PAIR",),
                        ("hostb", "walk"): ("S167-THB-OLDER", "S167-THB-FP", "S167-THB-CANT")}
B_T2_MEASURE = {
    "S167-WR-FREE": "the guest held under `hold up` (< HELD_U: s166's 0.00 u)",
    "S167-WR-REFUSE": "no `fp_mismatch` (s166: the op never sent; `walk off`: why 'lever') and the guest held",
    "S167-WR-REJOIN-FAR": "the guest's own walk away held (< HELD_U): a frozen guest (the rejoin's pull reported)",
    "S167-WR-PAIR": "frozen and never mirroring with no 'pairing' why (s166: absent; `walk off`: 'lever')",
    "S167-W-STALLHOLE": "the freeze LIFTED inside the stall (freeze.on false on a sample, or a lift line): s166's hole",
    "S167-W-STALLHOLE-KEYS": "the press reached the script: FieldHUD 300 / next_mode 1, or the freeze off at the press with freeze.keys +0",
    **{r: "the phase's guest read on place 4 (>= THB_MIN judged samples) and no s167 host line asked (world.line never 'older' / "
          "'fp_differs' / 'cant_walk')" for r in ("S167-THB-OLDER", "S167-THB-FP", "S167-THB-CANT")},
}
DUO_B_CHECKS = {
    "S167-D0": "the instrument: both on FieldHUD 6603, the guest mirroring, both s167 (wire 15, `netsync.world.walk` / `fp` / `walk.map`)",
    "S167-D-WFREE": "the guest followed the host out (round A's route: the hold until the host is live) and walks -- walk.free within "
                    "B_READY_S, fp 'match', both trailers' caps 0x0003 (the peer's caps 3 on both lanes)",
    "S167-D-W1": "D-W1, the GUEST walks (closed loop) -- the HOST's ghost of it on the guest's own trailer BY SEQ (target within "
                 "D_TARGET_TOL, eased within D_G1_TOL), the guest moved >= D_MOVE_U and free throughout, the host's own pose unmoved",
    "S167-D-W2": "D-W2, the HOST walks, the guest stands free -- the guest's ghost of it by seq, the host moved >= D_MOVE_U, the guest's "
                 "own pose unmoved and walk.free throughout (a walker that does not press stays put)",
    "S167-D-W3": "D-W3, BOTH walk at once -- each ghost on the other's trailer by seq, both moved >= D_MOVE_U, the guest free throughout",
    "S167-D-BATTLE": "the host's world battle with the guest apart (>= D_APART_U) and its full map open: the guest's map closed first "
                     "(map.coop_closes +1, last_close 'boot', the close line), the guest boots and returns at its OWN pose (within "
                     "B_POSE_TOL), then walks again (walk.free)",
    "S167-D-RIDE": "D-RIDE: `vehicle 1` on the HOST -- the GUEST's verdict (never the dot): frozen 'riding' with s165's riding words, "
                   "`hold up` held; `vehicle 0`: free again",
    "S167-D-REFUSE": "D-REFUSE (named both sides): `worldwalk fp fake dead` on the guest -- the guest frozen fp_mismatch, its line naming "
                     "'world map meshes' off the HOST's real section 11, b4, held; the HOST's 'fp_differs' line (asked, its words, drawn, "
                     "its walk line) and its fingerprint line; `fp act`: free again",
    "S167-D-ENTRY": "D-ENTRY: the guest on ICE_TILE, Confirm held 30 frames -- W-ENTRY's judge on the duo guest (one buzz by entry 1 at "
                    "place 4, never 300, Map[29] and the discovery bit unchanged)",
    "S167-D-REJOIN-FAR": "D-REJOIN-FAR: the guest free and >= FAR_U from the host when the host Confirms into 300 -- the rejoin pulls it "
                         "from there (FieldHUD 300, the landed line)",
    "S167-D-MAP": "decision 23's co-op close on a lawful walker: its full map open (Select from the minimap: FullMap, map.opens +1, "
                  "freeze.map +0) when the host enters -- closed FIRST (coop_closes +1, last_close 'rejoin', the close line before the "
                  "rejoin line), then the rejoin lands; with the battle run, the boot's close too",
    "S167-D-REJOIN-WAIT": "D-REJOIN-WAIT: the guest's control off, the host enters 300 (the rejoin waits) and walks back out of 6603 -- the "
                          "guest never left 9011, no follow-out, no landing, its ghost of the host hidden off the world and SNAPPED back "
                          "(snaps +1); control on: free again",
    "S167-D-SHARED": "THE SHARED-FILE LAW (the instrument): no 'Sharing violation' / 'When importing FBX' in either log",
}
DUO_B_ORDER = tuple(DUO_B_CHECKS)
DUO_B_OLD_PREDICTED = tuple(c for c in DUO_B_ORDER if c != "S167-D-SHARED")
_DUO_B_WALKS = ("S167-D-WFREE", "S167-D-W1", "S167-D-W2", "S167-D-W3", "S167-D-BATTLE", "S167-D-RIDE", "S167-D-REFUSE",
                "S167-D-REJOIN-FAR", "S167-D-MAP", "S167-D-REJOIN-WAIT")
#: `fullmap` (= `fullmap old` + `minimap old`) reds D-MAP AND D-BATTLE: both set up by opening the walker's full map, which the lever
#: refuses exactly as s166 does, so the boot close cannot happen (the first LEVER bench run, 2026-11-06, caught the missing row).
DUO_B_LEVER_PREDICTED = {"walk": _DUO_B_WALKS, "fullmap": ("S167-D-MAP", "S167-D-BATTLE")}
DUO_B_MEASURE = {
    "S167-D0": "an s166 pair: no round-B key",
    "S167-D-WFREE": "the guest frozen, never walk.free",
    "S167-D-W1": "the guest held under its own `hold up` (< HELD_U over judged world samples, frozen on the last)",
    "S167-D-W2": "the guest frozen on every sample (never walk.free)",
    "S167-D-W3": "the guest held under its own `hold up` (< HELD_U over judged world samples, frozen on the last)",
    "S167-D-BATTLE": "the guest frozen after the warm return (freeze.on, never walk.free)",
    "S167-D-RIDE": "the guest held with no 'riding' why (frozen before the host rode)",
    "S167-D-REFUSE": "the guest held and the host never asked 'fp_differs'",
    "S167-D-ENTRY": "silent: the press masked, no buzz, no line, never 300",
    "S167-D-REJOIN-FAR": "the guest frozen when the host entered (the pull reported)",
    "S167-D-MAP": "never FullMap, the Select taken a frozen way (refused: freeze.map +1; or decision 27's close: HUDNoMiniMap)",
    "S167-D-REJOIN-WAIT": "the guest frozen once control came back (freeze.on, never walk.free)",
}
#: the stand-in's ROUND-B FAULT LEVERS (fakegame.WORLD_WALK_B_FAULTS) -> exactly the rows each turns red on these legs (tests pin it; a
#: fault absent from a leg turns nothing red there)
B_T2_FAULT_REDS = {
    "stallhole": {"stall_free": ("S167-W-STALLHOLE", "S167-W-STALLHOLE-KEYS"), "pairing_free": ("S167-WR-PAIR",)},
    "walk": {"fp_ignored": ("S167-WR-REFUSE",)},
    "duo": {"fp_ignored": ("S167-D-REFUSE",), "refuse_silent": ("S167-D-ENTRY",)},
}


def b_t2_lever_of(leg: str, raw):
    """The calibration lever for round-B ``leg`` (the duo: "duo"): ``raw`` when it is one of the leg's, the leg's first when ``raw`` is
    None, else None (refused)."""
    levers = DUO_B_LEVERS if leg == "duo" else B_T2_LEVERS.get(leg, ())
    if raw is None:
        return levers[0] if levers else None
    return raw if raw in levers else None


def b_leg_catalog(leg: str, calibrate: bool) -> dict:
    """A round-B T2 leg's rows, in order (the finals last)."""
    if leg == "hostb":
        cat = {"T2H-PEER": HOST_COMMON["T2H-PEER"]}
        cat.update(THB_CHECKS)
    else:
        cat = {"T2-TAPE": B_T2_COMMON["T2-TAPE"], "T2-PEER": B_T2_COMMON["T2-PEER"]}
        cat.update(B_T2_CHECKS[leg])
        cat.update(WR_GATE)
    if calibrate:
        cat[f"S167-{leg.upper()}-CAL"] = (f"CALIBRATION: by the stage -- on s166 exactly {leg}'s B_T2_OLD_PREDICTED red, on s167 under the "
                                          "lever exactly its B_T2_LEVER_PREDICTED, each MEASURING s166's shape (B_T2_MEASURE)")
    if leg == "hostb":
        cat["T2H-INI"] = HOST_COMMON["T2H-INI"]
    else:
        cat["T2-SAVE"] = B_T2_COMMON["T2-SAVE"]
        cat["T2-INI"] = B_T2_COMMON["T2-INI"]
    return cat


def b_new(*states) -> bool:
    """(PURE) Every round-B key on every state (``netsync.world.walk`` / ``fp`` / ``walk.map``): the s167 stage."""
    return bool(states) and all(s is not None and all(cb.has(s, k) for k in B_PROBES) for s in states)


# ---- round B's pure readers (ww's)
_walk, _fp, _freeze, _wmapb = ww._walk, ww._fp, ww._freeze, ww._wmapb


def walk_free(s) -> bool:
    return _walk(s).get("free") is True


def fp_comps_of(st):
    """(PURE) The guest's own fingerprint as section 11 carries it: the six words off `fp.components` (the language's two letters ->
    FpLangWord, the rest hex), with `fp.real` and the world -- or None (not ready / an engine before s167)."""
    fp = _fp(st)
    comps = fp.get("components")
    if fp.get("ready") is not True or not isinstance(comps, dict):
        return None
    try:
        words = [BW.ww_fp_lang_word(comps.get("language"))]
        words += [int(str(comps[n]), 16) for n in BW.WW_FP_COMP_NAMES[1:]]
        real = int(str(fp.get("real")), 16)
    except (KeyError, TypeError, ValueError):
        return None
    return {"world": int(fp.get("world") or 0), "comps": words, "real": real, "combined": BW.ww_fp_combine(words)}


def tape_s167(records, cp) -> dict:
    """(PURE over tape records) rm8 S167: the ROAM tape speaks round B -- its world trailers carry caps b1 and a nonzero digest, and its
    host state frames on the world carry section 11 -- {ok, why, caps, digests, sections}."""
    rows = trailer_rows(records, cp)
    world = [r for r in rows if r.get("has") and r.get("valid")]
    caps = sorted({int(r["caps"]) for r in world})
    digests = sorted({int(r.get("digest") or 0) for r in world})
    sections = sum(1 for _r, w, p in cp.host_frames(records) if w == cp.TYPE_STATE and cp.fp_section_of(p) is not None)
    ok = bool(world) and all(c & BW.WW_CAP_WORLD_FP for c in caps) and 0 not in digests and sections > 0
    return {"ok": ok, "caps": caps, "digests": [f"0x{d:08X}" for d in digests[:3]], "sections": sections,
            "why": (f"world trailers' caps {[f'0x{c:04X}' for c in caps]}, digests {[f'0x{d:08X}' for d in digests[:3]]}, section 11 on "
                    f"{sections} host state frame(s)" + ("" if ok else " -- NOT an s167 host's tape ('an older build': the walk refuses "
                                                                      "old_partner / checking on it)"))}


def judge_wr_free(free_st, st2, moved, adv) -> tuple:
    """S167-WR-FREE (PURE): walk.free on the first sample after the landing that read it (``free_st``) and after the hold (``st2``), why
    null, `hold up` moved >= WALK_U over its frames, freeze.on still true, fp 'match', the trailer's b1."""
    w_ok, w_why = cw.judge_walk(moved, adv, ww.WALK_FRAMES, held=False)
    if st2 is None or not cb.has(st2, WALK_PROBE):
        return False, f"absent: no `{WALK_PROBE}` -- an engine before s167 ({w_why})"
    w0, w = _walk(free_st), _walk(st2)
    b1 = bool((_num(_tx(st2).get("state")) or 0) & BW.WW_ST_WALKING)
    fp = _fp(st2).get("state")
    ok = (free_st is not None and w0.get("free") is True and w.get("free") is True and w.get("why") is None and w_ok
          and (moved or 0) >= ww.WALK_U and ww.frozen(st2) and fp == "match" and b1)
    return ok, (f"walk.free {w0.get('free')!r} -> {w.get('free')!r} (why {w0.get('why')!r} / {w.get('why')!r}); {w_why} (want >= "
                f"{ww.WALK_U:g}u); {ww._freeze_word(st2)} (want on); fp.state {fp!r} (want match: own {_fp(st2).get('own')}, peer "
                f"{_fp(st2).get('peer')}); tx b1 {'set' if b1 else 'CLEAR'}")


def judge_wr_refuse(r: dict) -> tuple:
    """S167-WR-REFUSE (PURE): W-REFUSE-FP's judge (ww.judge_refuse) on the real client, plus the HOST's section 11 read off the wire
    (host_section set, all six components: mask 0x3F)."""
    ok, why = ww.judge_refuse("S167-W-REFUSE-FP", "fp_mismatch", r)
    post = r.get("post")
    if post is None or not cb.has(post, WALK_PROBE):
        return ok, why
    hs = _fp(post).get("host_section") or {}
    s_ok = hs.get("set") is True and hs.get("mask") == (1 << BW.WW_FP_COMPS) - 1 and hs.get("world") == WORLD
    return ok and s_ok, why + f"; the host's section 11 {hs} (want set, world {WORLD}, mask 0x3F)"


def far_at_departure(samples) -> tuple:
    """(PURE) The guest's last WorldHUD sample whose cache still reads the host on place 4 before it left: (that sample, the torus
    distance between the guest's own pose and the host's trailer pose on it), or (None, None)."""
    last = None
    for s in samples:
        if s.ui_state == "WorldHUD" and _rx(s).get("place") == BW.WW_PLACE_WORLD:
            last = s
        elif last is not None and (s.ui_state != "WorldHUD" or _rx(s).get("place") != BW.WW_PLACE_WORLD):
            break
    if last is None:
        return None, None
    gx, gz = wf.world_xz(last)
    hx, hz = _num(_rx(last).get("x")), _num(_rx(last).get("z"))
    if None in (gx, gz, hx, hz):
        return last, None
    return last, torus(gx, gz, hx, hz)


def judge_wr_far(away: tuple, samples, rejoin: tuple) -> tuple:
    """S167-WR-REJOIN-FAR (PURE): ``away`` = (moved, adv) the guest's own walk away (>= D_MOVE_U); at the host's departure (the last
    sample reading it on place 4) the guest free and >= FAR_U from it; the rejoin (``rejoin``: cw.judge_rejoin_land's verdict) landed."""
    moved, _adv = away
    dep, d = far_at_departure(samples)
    if dep is None or not cb.has(dep, WALK_PROBE):
        return False, (f"absent: no `{WALK_PROBE}` -- an engine before s167 (walked {moved}; the rejoin: {rejoin[1]})" if dep is not None
                       else f"not reached: no sample read the host on place 4 before it left (the rejoin: {rejoin[1]})")
    ok = (moved or 0) >= D_MOVE_U and walk_free(dep) and d is not None and d >= FAR_U and rejoin[0]
    return ok, (f"walked away {moved if moved is None else round(moved, 1)} u on its own (want >= {D_MOVE_U:g}); at the host's departure "
                f"free {_walk(dep).get('free')!r} (why {_walk(dep).get('why')!r}), {d if d is None else round(d, 1)} u from the host "
                f"(want >= {FAR_U:g}); REJOIN {rejoin[1]}")


def judge_wr_pair(samples, base) -> tuple:
    """S167-WR-PAIR (PURE over the judged WorldHUD samples from the replay's start to the first window): the guest frozen on the last,
    never mirroring, never off 9011, out.starts +0 since ``base`` (no follow-out: it never left a field), walk.why 'pairing' and the
    pairing words on the last."""
    js = [s for s in samples if s.ui_state == "WorldHUD" and judged(s)]
    if not js:
        return False, "not reached: no judged world sample after the replay started"
    last = js[-1]
    mir = [s.frame for s in samples if cw._s(s, "mirroring") is True]
    off = [(s.ui_state, s.world_id) for s in samples if not (s.ui_state == "WorldHUD" and s.world_id == WORLD)]
    starts = _d(base, last, lambda x: cb.path(x, "netsync.world.out") or {}, "starts")
    if not cb.has(last, WALK_PROBE):
        return False, (f"absent: no `{WALK_PROBE}` -- an engine before s167 ({ww._freeze_word(last)}; mirroring on {mir[:2] or 'no sample'}; "
                       f"out.starts +{starts})")
    w = _walk(last)
    ok = (ww.frozen(last) and not mir and not off and (starts or 0) == 0 and w.get("why") == "pairing" and w.get("free") is False
          and w.get("line") == BW.WORDS_WW_WALK_PAIRING)
    return ok, (f"{ww._freeze_word(last)}; mirroring on {mir[:2] or 'no sample'}; off {WORLD} on {off[:2] or 'no sample'}; out.starts "
                f"+{starts} (want 0); walk.why {w.get('why')!r} (want 'pairing'), free {w.get('free')!r}, line {w.get('line')!r}")


def pair_old_shape(samples) -> bool:
    """WR-PAIR's OLD / `walk off` shape (PURE): frozen on the last judged world sample, never mirroring, and no 'pairing' why."""
    js = [s for s in samples if s.ui_state == "WorldHUD" and judged(s)]
    return bool(js) and ww.frozen(js[-1]) and not any(cw._s(s, "mirroring") is True for s in samples) \
        and _walk(js[-1]).get("why") != "pairing"


def _stalled(s, margin: int = STALL_SEEN_MS) -> bool:
    """(PURE) The lane past StaleMs + ``margin``: no frame arrived for longer than GetRemote's 2000 ms by a frame's skew and more (the stall
    is live on this sample, the session's own verdict caught up)."""
    return (_num(_lane(s).get("arrival_age_ms")) or -1) >= BW.STALE_MS + margin


def judge_stallhole(base, win, after_lines) -> tuple:
    """S167-W-STALLHOLE (PURE over the blackhole's samples ``win`` -- its start to its end + STALL_TAIL_S -- and the engine's lines over it):
    the stall reached (a sample past StaleMs), the freeze held on every WorldHUD sample (freeze.on), walk.stall_held on the stalled
    samples, freeze.edges unmoved from ``base`` to the last, no lift line."""
    ws = [s for s in win if s.ui_state == "WorldHUD"]
    if not ws:
        return False, "not reached: no world sample inside the blackhole"
    stalled = [s for s in ws if _stalled(s)]
    if not stalled:
        return False, f"not reached (the instrument): the blackhole never staled the lane (max arrival age " \
                      f"{max((_num(_lane(s).get('arrival_age_ms')) or -1) for s in ws)} ms; want >= {BW.STALE_MS + STALL_SEEN_MS})"
    lifted = [s.frame for s in ws if not ww.frozen(s)]
    de = _d(base, ws[-1], _freeze, "edges")
    n_lift = cb.count(after_lines, "world freeze lifted on world map ")
    if not cb.has(ws[-1], WALK_PROBE):
        return False, (f"absent: no `{WALK_PROBE}` -- an engine before s167 (stalled on {len(stalled)} sample(s); the freeze off on "
                       f"{lifted[:3] or 'no sample'}; edges +{de}; lift lines {n_lift})")
    held = [s for s in stalled if _walk(s).get("stall_held") is True]
    # THE BOUNDARY SAMPLE (the bench's first LEVER run, 2026-11-06): the lane's arrival age is copied once per Update, while the
    # session's live term reads the socket's receive-thread tick -- the first frame back can make the LIVE term hold the freeze
    # (why 'live', stall_held false) on the LAST stalled sample only. Anywhere else a live why means the live term never lapsed.
    tail = [s for s in stalled[-1:] if _walk(s).get("stall_held") is not True and str(_freeze(s).get("why")) == "live"]
    ok = not lifted and de == 0 and n_lift == 0 and bool(held) and len(held) + len(tail) == len(stalled)
    return ok, (f"stalled on {len(stalled)} of {len(ws)} sample(s) (arrival age >= {BW.STALE_MS + STALL_SEEN_MS} ms); the freeze off on "
                f"{lifted[:3] or 'no sample'} (want none); stall_held on {len(held)} of them (want all, but the last may read the "
                f"live term: {len(tail)}); freeze.edges +{de} (want 0); "
                f"lift lines {n_lift} (want 0); freeze.why on the stall {sorted({str(_freeze(s).get('why')) for s in stalled})}")


def stall_lifted(win, after_lines) -> bool:
    """W-STALLHOLE's OLD / `stallhold old` shape (PURE): the freeze lifted inside the stall -- freeze.on false on a stalled sample, or a
    lift line."""
    return any(_stalled(s, 0) and not ww.frozen(s) for s in win if s.ui_state == "WorldHUD") or \
        cb.count(after_lines, "world freeze lifted on world map ") > 0


def judge_stall_press(press: dict) -> tuple:
    """One press of S167-W-STALLHOLE-KEYS (PURE): ``press`` = {kind 'location' | 'sand', base (the sample the press went out on), after
    (the samples after it), why (not reached)}. The press inside a live stall (base stalled), frozen at it; location: freeze.keys +>=1 and
    never FieldHUD / next_mode 1; sand: freeze.battles or freeze.keys +>=1 and never off WorldHUD (no local battle)."""
    base, after = press.get("base"), press.get("after") or []
    kind = press.get("kind")
    if base is None:
        return False, f"{kind}: not reached ({press.get('why')})"
    if not _stalled(base):
        return False, f"{kind}: not reached (the instrument): the press went out before the stall (arrival age " \
                      f"{_lane(base).get('arrival_age_ms')} ms)"
    last = after[-1] if after else base
    left = [(s.ui_state, s.field_id if s.ui_state == "FieldHUD" else s.world_id, f"next_mode {ww.next_mode(s)}") for s in after
            if s.ui_state != "WorldHUD" or ww.next_mode(s) == 1]
    held = ww.frozen(base) and (_walk(base).get("stall_held") is True or not cb.has(base, WALK_PROBE))
    if kind == "sand":
        # the guard that holds is the engine's to name (K1): the quicksand's read @00204 is entry 1's Confirm, so the held mask may
        # take the press first (freeze.keys +1, the battle never asked) or SkipWorldScriptedBattle skips Battle(0, 144) (freeze.battles
        # +1, the design's row) -- either keeps the battle off the guest; NO local battle is the row
        db, dk = _d(base, last, _freeze, "battles"), _d(base, last, _freeze, "keys")
        ok = held and ((db or 0) >= 1 or (dk or 0) >= 1) and not left
        return ok, (f"sand: frozen at the press {held}; freeze.battles +{db}, freeze.keys +{dk} (want one of them >= 1: the skip or the "
                    f"mask -- reported for K1); left the world on {left[:2] or 'no sample'} (want none: no local battle)")
    dk = _d(base, last, _freeze, "keys")
    de = _d(base, last, _walk, "entry_refused")
    ok = held and (dk or 0) >= 1 and not left
    return ok, (f"location: frozen at the press {held} (stall_held {_walk(base).get('stall_held')!r}); freeze.keys +{dk} (want >= 1); "
                f"entry_refused +{de} (the buzz, reported); left the world on {left[:2] or 'no sample'} (want none: never 300)")


def judge_stall_keys(presses) -> tuple:
    """S167-W-STALLHOLE-KEYS (PURE): every press green; absent with no `netsync.world.walk` (s166)."""
    if not presses:
        return False, "not reached: no press ran"
    parts = [judge_stall_press(p) for p in presses]
    absent = all(p.get("base") is not None and not cb.has(p["base"], WALK_PROBE) for p in presses)
    text = "; ".join(w for _o, w in parts)
    if absent:
        return False, f"absent: no `{WALK_PROBE}` -- an engine before s167 ({text})"
    return all(o for o, _w in parts), text


def press_leaked(presses) -> bool:
    """W-STALLHOLE-KEYS' OLD / `stallhold old` shape (PURE): a press reached the script -- off WorldHUD / next_mode 1 after it, or the
    freeze off at it with freeze.keys +0."""
    for p in presses:
        base, after = p.get("base"), p.get("after") or []
        if base is None:
            continue
        if any(s.ui_state != "WorldHUD" or ww.next_mode(s) == 1 for s in after):
            return True
        if not ww.frozen(base) and (_d(base, after[-1] if after else base, _freeze, "keys") or 0) == 0:
            return True
    return False


def judge_thb(phase: str, samples, lines, other_names=tuple(THB_NAME.values())) -> tuple:
    """A T2-HB row (PURE over the HOST's samples of ``phase`` and its lines): on the samples reading the guest on place 4 (the first
    THB_SETTLE skipped) -- 'quiet': never an s167 host line, no walk log line, the ghost shown on one; else the phase's line asked with its
    words and drawn on the last THB_MIN, never another s167 line, its walk log line once or twice (an edge per link); 'fp' adds the host's
    own fingerprint line."""
    p4 = [s for s in samples if _hg(s).get("place") == BW.WW_PLACE_WORLD and judged(s)][THB_SETTLE:]
    if not p4:
        return False, f"not reached: the host's cache never read the {phase} guest on place 4 (judged)"
    asked = [_line(s).get("asked") for s in p4]
    if phase == "quiet":
        s167 = [a for a in asked if a in other_names]
        n = cb.count(lines, BW.LOG_WW_HOST_WALK)
        shown = any(_ghost(s).get("shown") is True for s in p4)
        return not s167 and n == 0 and shown, (f"{len(p4)} place-4 sample(s); s167 lines asked {sorted(set(s167)) or 'none'} (want none); "
                                               f"walk log lines {n} (want 0); the ghost shown {shown}")
    name, words = THB_NAME[phase], THB_WORDS[phase]
    if not any(cb.has(s, WALK_PROBE) for s in p4):
        return False, f"absent: no `{WALK_PROBE}` on the host -- an engine before s167 (asked {sorted({str(a) for a in asked})})"
    tail = p4[-THB_MIN:]
    good = [s for s in tail if _line(s).get("asked") == name and _line(s).get("text") == words and _line(s).get("drawn") is True]
    wrong = sorted({a for a in asked if a in other_names and a != name})
    n = cb.count(lines, BW.LOG_WW_HOST_WALK + name + " ")
    ok = len(p4) >= THB_MIN and len(good) == len(tail) and not wrong and 1 <= n <= 2
    why = (f"{len(p4)} place-4 sample(s); '{name}' asked + words + drawn on {len(good)} of the last {len(tail)} (want all, >= {THB_MIN}); "
           f"other s167 lines {wrong or 'none'}; the walk log line {n}x (want 1..2)")
    if phase == "fp":
        nf = cb.count(lines, BW.LOG_WW_FP_HOST)
        dead = cb.count(lines, "the guest's 0x0000DEAD")
        ok = ok and nf >= 1 and dead >= 1
        why += f"; the host's fingerprint line {nf}x naming the guest's 0x0000DEAD {dead}x (want >= 1)"
    return ok, why


def thb_quiet_shape(samples) -> bool:
    """T2-HB's OLD / `walk off` shape (PURE): the host's cache READ the phase's guest on place 4 (at least THB_MIN judged samples past
    THB_SETTLE -- [W2 critic] a phase whose serve-guest never reached place 4 asks no line either: that is no measurement) and no s167
    host line was ever asked on the phase's samples."""
    p4 = [s for s in samples if _hg(s).get("place") == BW.WW_PLACE_WORLD and judged(s)][THB_SETTLE:]
    return len(p4) >= THB_MIN and not any(_line(s).get("asked") in THB_NAME.values() for s in samples)


# ---- the duo's pure judges
def ghost_track(observer, mover) -> tuple:
    """(PURE) The observer's ghost on the mover's own trailer BY SEQ: (matched, unmatched, bad) over the observer's judged samples with the
    ghost placed -- shown, its target within D_TARGET_TOL of the mover's tx pose at the observer's `rx.seq` (tx_pose_at), eased within
    D_G1_TOL of the target."""
    js = [s for s in observer if judged(s) and _ghost(s).get("placed") is True]
    bad, unmatched = [], 0
    for s in js:
        g, seq = _ghost(s), _rx(s).get("seq")
        want = tx_pose_at(mover, seq) if isinstance(seq, int) and seq >= 0 else None
        if want is None:
            unmatched += 1
            continue
        gx, gz, tx, tz = (_num(g.get(k)) for k in ("x", "z", "tx", "tz"))
        if g.get("shown") is not True or None in (gx, gz, tx, tz) or torus(tx, tz, *want) > D_TARGET_TOL \
                or torus(gx, gz, tx, tz) > D_G1_TOL:
            bad.append((s.frame, g.get("shown"), tx, tz, want))
    return len(js) - unmatched, unmatched, bad


def judge_dw(kind: str, hs, gs, h0, h1, g0, g1) -> tuple:
    """S167-D-W1 / W2 / W3 (PURE over the two Taps' samples ``hs`` / ``gs`` and each game's own pose before / after): 'w1' the guest
    moves (the host's ghost tracks it, the host unmoved), 'w2' the host moves (the guest's ghost tracks it, the guest unmoved), 'w3' both
    (both ghosts track); the guest walk.free on every judged sample of its Tap in all three."""
    if not any(cb.has(s, WALK_PROBE) for s in gs):
        return False, f"absent: no `{WALK_PROBE}` on the guest -- an engine before s167 (guest moved {world_moved(gs):.1f} u)"
    parts, ok = [], True
    if kind in ("w1", "w3"):
        n, un, bad = ghost_track(hs, gs)
        mv = max(tx_moved(gs), world_moved(gs))
        ok = ok and n >= D_MIN_SAMPLES and not bad and mv >= D_MOVE_U
        parts.append(f"the host's ghost of the guest: {n} matched by seq ({un} unmatched), off {bad[:2] or 'none'}; the guest moved "
                     f"{mv:.1f} u (want >= {D_MOVE_U:g})")
    if kind in ("w2", "w3"):
        n, un, bad = ghost_track(gs, hs)
        mv = max(tx_moved(hs), world_moved(hs))
        ok = ok and n >= D_MIN_SAMPLES and not bad and mv >= D_MOVE_U
        parts.append(f"the guest's ghost of the host: {n} matched by seq ({un} unmatched), off {bad[:2] or 'none'}; the host moved "
                     f"{mv:.1f} u (want >= {D_MOVE_U:g})")
    if kind == "w1":
        still = None not in (h0[0], h1[0]) and torus(*h0, *h1) < ww.HELD_U
        ok = ok and still
        parts.append(f"the host's own pose {'unmoved' if still else 'MOVED'} ({h0} -> {h1})")
    if kind == "w2":
        still = None not in (g0[0], g1[0]) and torus(*g0, *g1) < ww.HELD_U
        ok = ok and still
        parts.append(f"the guest's own pose {'unmoved' if still else 'MOVED'} ({g0} -> {g1})")
    jg = [s for s in gs if judged(s) and s.ui_state == "WorldHUD"]
    not_free = [s.frame for s in jg if not walk_free(s)]
    ok = ok and bool(jg) and not not_free
    parts.append(f"the guest free on {len(jg) - len(not_free)} of {len(jg)} judged sample(s) (want all; why "
                 f"{sorted({str(_walk(s).get('why')) for s in jg if not walk_free(s)}) or 'none'})")
    return ok, "; ".join(parts)


def dw_frozen(gs) -> bool:
    """D-W2's OLD / `walk off` shape (PURE): the guest frozen on every judged sample, never walk.free."""
    jg = [s for s in gs if judged(s) and s.ui_state == "WorldHUD"]
    return bool(jg) and all(ww.frozen(s) and not walk_free(s) for s in jg)


def dw_held(gs) -> bool:
    """D-W1 / D-W3's OLD / `walk off` shape (PURE): the guest's own `hold up` held -- judged world samples read (an empty Tap moves 0.0 u
    too: [W2 critic] that is no measurement), its own pose < HELD_U over them, frozen on the last."""
    jg = [s for s in gs if judged(s) and s.ui_state == "WorldHUD"]
    return bool(jg) and world_moved(jg) < ww.HELD_U and ww.frozen(jg[-1])


def frozen_not_walking(st) -> bool:
    """(PURE) A duo row's OLD / `walk off` shape on one guest sample: `freeze.on` AND never walk.free -- [W2 critic] `not walk_free` alone is
    vacuous on s166 (no `netsync.world.walk`: it reads False on every state)."""
    return st is not None and ww.frozen(st) and not walk_free(st)


def judge_dw_free(st, hs_last) -> tuple:
    """S167-D-WFREE (PURE): the guest walk.free (why null) after its landing, fp 'match', the peer's caps 0x0003 on both lanes."""
    if st is None or not cb.has(st, WALK_PROBE):
        return False, f"absent: no `{WALK_PROBE}` -- an engine before s167 ({ww._freeze_word(st) if st is not None else 'no sample'})"
    pg = (_lane(st).get("caps") or {}).get("peer")
    ph = (_lane(hs_last).get("caps") or {}).get("peer") if hs_last is not None else None
    ok = walk_free(st) and _walk(st).get("why") is None and _fp(st).get("state") == "match" and pg == CAPS_S167 and ph == CAPS_S167
    return ok, (f"walk.free {_walk(st).get('free')!r} (why {_walk(st).get('why')!r}); fp.state {_fp(st).get('state')!r}; the peer's caps "
                f"on the guest {pg!r}, on the host {ph!r} (want {CAPS_S167} each)")


def judge_host_fp(host_samples, host_lines) -> tuple:
    """D-REFUSE's HOST half (PURE): a judged host sample asking 'fp_differs' with its words, drawn; its walk line; its fingerprint line."""
    hit = [s for s in host_samples if _line(s).get("asked") == "fp_differs" and _line(s).get("text") == BW.WORDS_WW_HOST_FP_DIFFERS
           and _line(s).get("drawn") is True]
    nw = cb.count(host_lines, BW.LOG_WW_HOST_WALK + "fp_differs ")
    nf = cb.count(host_lines, BW.LOG_WW_FP_HOST)
    ok = bool(hit) and nw >= 1 and nf >= 1
    return ok, f"the host: 'fp_differs' asked + words + drawn on {len(hit)} sample(s) (want >= 1); its walk line {nw}x, its fingerprint line {nf}x"


def judge_d_battle_b(b: dict) -> tuple:
    """S167-D-BATTLE (PURE): ``b`` = {pre (the guest before), host_pre, opened (FullMap read), after (back on the world), free_after, lines,
    booted (the guest's boot seen), why}: apart >= D_APART_U, the map closed for the boot (coop_closes +1, last_close 'boot', the close
    line), the guest booted, returned within B_POSE_TOL of its own pose, then free."""
    pre, after = b.get("pre"), b.get("after")
    if pre is None or after is None:
        return False, f"not reached: {b.get('why')}"
    if not cb.has(after, WALK_PROBE):
        return False, f"absent: no `{WALK_PROBE}` -- an engine before s167 ({b.get('why')})"
    g0, h0, g1 = wf.world_xz(pre), wf.world_xz(b.get("host_pre")), wf.world_xz(after)
    apart = torus(*g0, *h0) if None not in g0 + h0 else None
    back = torus(*g0, *g1) if None not in g0 + g1 else None
    dc = _d(pre, after, _wmapb, "coop_closes")
    n_c = cb.count(b.get("lines") or [], BW.log_ww_map_closed("boot", WORLD))
    ok = (b.get("opened") is True and (apart or 0) >= D_APART_U and dc == 1 and _wmapb(after).get("last_close") == "boot" and n_c == 1
          and b.get("booted") is True and back is not None and back <= B_POSE_TOL and b.get("free_after") is True)
    return ok, (f"apart {apart if apart is None else round(apart, 1)} u (want >= {D_APART_U:g}); the full map open {b.get('opened')!r}; "
                f"coop_closes +{dc}, last_close {_wmapb(after).get('last_close')!r}, the boot close line {n_c}x (want 1); booted "
                f"{b.get('booted')!r}; back {back if back is None else round(back, 2)} u from its own pose (want <= {B_POSE_TOL:g}); "
                f"free after {b.get('free_after')!r}; {b.get('why')}")


def judge_d_far(far_st, host_xz, rejoin: tuple) -> tuple:
    """S167-D-REJOIN-FAR (PURE): the guest free and >= FAR_U from the host's pose when the host entered, the rejoin (cw.judge_rejoin_land)
    landed it on 300."""
    if far_st is None or not cb.has(far_st, WALK_PROBE):
        return False, f"absent: no `{WALK_PROBE}` -- an engine before s167 (the rejoin: {rejoin[1]})"
    g = wf.world_xz(far_st)
    d = torus(*g, *host_xz) if None not in g + tuple(host_xz) else None
    ok = walk_free(far_st) and d is not None and d >= FAR_U and rejoin[0]
    return ok, (f"free {_walk(far_st).get('free')!r} (why {_walk(far_st).get('why')!r}), {d if d is None else round(d, 1)} u from the host "
                f"(want >= {FAR_U:g}); REJOIN {rejoin[1]}")


def judge_d_map(m: dict) -> tuple:
    """S167-D-MAP (PURE): ``m`` = {base (before the Select), opened (the samples after it), rejoin (the samples to the landing), lines (the
    guest's), landed (verdict), boot (judge_d_battle_b's map half or None)}: FullMap read with map.opens +1 and freeze.map +0; then
    coop_closes +1, last_close 'rejoin', the close line once and BEFORE the rejoin's arm line; landed."""
    base, opened, rj = m.get("base"), m.get("opened") or [], m.get("rejoin") or []
    if base is None:
        return False, f"not reached: {m.get('why')}"
    full = [s for s in opened if _dot(s).get("hud") == "FullMap"]
    last_open = opened[-1] if opened else base
    if not cb.has(last_open, WALK_PROBE):
        return False, (f"absent: no `{WALK_PROBE}` -- an engine before s167 (Select: freeze.map +{_d(base, last_open, _freeze, 'map')}, "
                       f"the HUD {_dot(last_open).get('hud')!r})")
    do, dm = _d(base, last_open, _wmapb, "opens"), _d(base, last_open, _freeze, "map")
    world_rj = [s for s in rj if cb.has(s, WALK_PROBE)]
    end = world_rj[-1] if world_rj else last_open
    dc = _d(last_open, end, _wmapb, "coop_closes")
    lines = [ln for ln in (m.get("lines") or [])]
    close_line = BW.log_ww_map_closed("rejoin", WORLD, ICE_CAVERN)
    i_close = next((i for i, ln in enumerate(lines) if close_line in ln), None)
    i_arm = next((i for i, ln in enumerate(lines) if "rejoining the peer at field" in ln), None)
    order = i_close is not None and (i_arm is None or i_close < i_arm)
    ok = (bool(full) and do == 1 and dm == 0 and dc == 1 and _wmapb(end).get("last_close") == "rejoin" and order
          and m.get("landed") is True)
    why = (f"FullMap on {len(full)} sample(s), opens +{do}, freeze.map +{dm} (want 1 / 0); coop_closes +{dc}, last_close "
           f"{_wmapb(end).get('last_close')!r}; the close line at {i_close}, the rejoin's line at {i_arm} (want the close first); landed "
           f"{m.get('landed')!r}")
    boot = m.get("boot")
    if boot is not None:
        ok = ok and boot[0]
        why += f"; the boot's close: {boot[1]}"
    else:
        why += "; the boot's close: not run (no battle in this configuration)"
    return ok, why


def map_never_full(m: dict) -> bool:
    """D-MAP's OLD / lever shape (PURE): the guest on WorldHUD at the Select, which never reached FullMap -- and the Select WAS taken one
    of the two frozen ways ([W2 critic] a Select never read is no measurement): refused (`freeze.map` +1: s166, `fullmap old` + `minimap
    old`) or decision 27's minimap close (HUDNoMiniMap: `walk off` with `minimap act`)."""
    base, opened = m.get("base"), list(m.get("opened") or [])
    if base is None or base.ui_state != "WorldHUD" or not opened or any(_dot(s).get("hud") == "FullMap" for s in opened):
        return False
    last = opened[-1]
    return (_d(base, last, _freeze, "map") or 0) >= 1 or _dot(last).get("hud") == "HUDNoMiniMap"


def judge_d_wait(w: dict) -> tuple:
    """S167-D-REJOIN-WAIT (PURE): ``w`` = {base (before the host's entry), samples (the guest's Tap through the wait, the host's return and
    control back), entered (the host reached 300), returned (the host back on 9011), after (the guest's last), why}: the guest WorldHUD 9011
    throughout, out.starts +0, rejoin.lands +0, the rejoin's wait read ('a world script holds control') while the host stood on 300, the
    ghost hidden off the world and shown again with snaps +>=1, then free."""
    base, ss, after = w.get("base"), w.get("samples") or [], w.get("after")
    if base is None or after is None or not w.get("entered") or not w.get("returned"):
        return False, f"not reached: {w.get('why')}"
    off = [(s.ui_state, s.field_id if s.ui_state == "FieldHUD" else s.world_id) for s in ss
           if not (s.ui_state == "WorldHUD" and s.world_id == WORLD)]
    starts = _d(base, after, lambda x: cb.path(x, "netsync.world.out") or {}, "starts")
    lands = _d(base, after, lambda x: cb.path(x, "netsync.world.rejoin") or {}, "lands")
    waited = [s for s in ss if "holds control" in str(cb.path(s, "netsync.world.rejoin.why") or "")]
    # LIVE VERDICT vs LAST DRAWN: `shown` judged only where the live verdict `want` agrees (a frame before the draw is neither)
    hidden = [s for s in ss if _rx(s).get("place") != BW.WW_PLACE_WORLD and _ghost(s).get("shown") is False
              and _ghost(s).get("want") is False]
    snaps = _d(base, after, _ghost, "snaps")
    shown = _ghost(after).get("shown") is True and _ghost(after).get("want") is True
    if not cb.has(after, WALK_PROBE):
        return False, (f"absent: no `{WALK_PROBE}` -- an engine before s167 (off the world on {off[:2] or 'no sample'}; out.starts "
                       f"+{starts}; lands +{lands}; snaps +{snaps})")
    ok = not off and starts == 0 and lands == 0 and bool(waited) and bool(hidden) and (snaps or 0) >= 1 and shown and walk_free(after)
    return ok, (f"off {WORLD} on {off[:2] or 'no sample'} (want none); out.starts +{starts}, rejoin.lands +{lands} (want 0 / 0); the "
                f"rejoin waited on {len(waited)} sample(s) ('holds control'); the ghost hidden off the world on {len(hidden)}, snaps "
                f"+{snaps} (want >= 1), shown at the end {shown}; free {_walk(after).get('free')!r} (why {_walk(after).get('why')!r})")


# ---- the moves
def _b_pull(g, ctx: _Ctx, lever) -> str:
    """Pull round-B ``lever`` (B_LEVER_OPS) on ``g`` when the stage is s167; read back off its block. Notes the ops in ``ctx.sent``."""
    if lever is None:
        return "no lever"
    if not b_new(g.state):
        return f"no round-B key: `{lever}` never sent (OLD)"
    notes = []
    for op in B_LEVER_OPS[lever]:
        ok, why = _ww(g, *op)
        if ok:
            ctx.sent.append(op[0])
        notes.append(f"`worldwalk {' '.join(op)}` {'pulled (held through the leg)' if ok else 'REFUSED: ' + why[:100]}")
    st = cb.poll(g, lambda s: all(ww.b_levers(s).get(o) == w for o, w in B_LEVER_OPS[lever]), 3.0, "the lever read back") or g.state
    return "; ".join(notes) + f" -- read back {[ww.b_levers(st).get(o) for o, _w in B_LEVER_OPS[lever]]}"


def _s166_rekey(g, ctx: _Ctx) -> str:
    """THE REGRESSION RE-KEY (round A's legs on an s167 build): round B's whole s166 lever set (ww.S166_LEVER_SET) pulled and read back
    when the probe shows `netsync.world.walk` -- round A's rows then read s166 exactly; nothing on s166."""
    ok, why = ww.s166_lever_set(g, g.state)
    if why:
        ctx.sent.append("s166-set")
    return why or "s166: no round-B key (nothing pulled)"


def _hold_until(g, ctx: _Ctx, goal: float, frames: int = D_WALK_FRAMES, deadline_s: float = D_WALK_S, button: str = "up") -> tuple:
    """The T2 guest's own closed-loop walk: `hold <button>` up to ``frames``, sampled (ctx) until its world x/z moved ``goal`` from the
    start or the deadline, then released. -> (moved, the samples)."""
    x0 = wf.world_xz(g.state)
    g.hold(button, int(frames))
    t0, got, moved = time.time(), [], 0.0
    while time.time() < t0 + deadline_s:
        st = _sample(g, ctx)
        got.append(st)
        xz = wf.world_xz(st)
        if None not in xz and None not in x0:
            moved = max(moved, torus(*x0, *xz))
        if moved >= goal:
            break
        time.sleep(POLL_S)
    g.send(f"release {button}", wait=False)
    _wait(g, ctx, lambda s: False, D_WALK_TAIL_S)
    return moved, got


def _calibration_visit(g, ctx: _Ctx) -> tuple:
    """THE INSTRUMENT's calibration (the walk leg, an s167 guest, no recorded tape): the guest walks out of 6603 alone (no session: nobody
    listens yet), its own 9011 fingerprint read once ready (fp_comps_of), back to 6603 by a field round trip. (fp or None, why)."""
    ok, why, _st = cw.walk_out(g)
    if not ok:
        return None, f"the calibration walk out failed: {why[:160]}"
    st = cb.poll(g, lambda s: judged(s) and fp_comps_of(s) is not None, FP_READY_S, "my own 9011 fingerprint") or g.state
    fp = fp_comps_of(st)
    try:
        g.world_warp(FARSHORE)
        cb.poll(g, lambda s: s.ui_state == "FieldHUD" and s.field_id == FARSHORE, 20.0, f"back on {FARSHORE}")
        g.wait_frames(45)
    except HarnessError as err:
        return fp, f"the field round trip back to {FARSHORE} failed: {str(err)[:160]}"
    if fp is None:
        return None, f"no fingerprint within {FP_READY_S:g} s (fp {_fp(st)})"
    same = fp["combined"] == fp["real"]
    return fp, (f"my 9011 fingerprint 0x{fp['real']:08X} (its six words recombine to 0x{fp['combined']:08X}: "
                f"{'the same' if same else 'DIFFERENT -- the instrument carries the recombined word'}), world {fp['world']}")


def _b_tape(g, led, ctx: _Ctx, *, fp=None) -> list | None:
    """The round-B leg's tape: the recorded ROAM tape, else THE INSTRUMENT shaped like an s167 host (caps 0x0003; with ``fp`` its digest and
    section 11 are the guest's own: a host of this install). Reads back, the facts, rm8 S167 -> ctx.rows / smap / s167."""
    cp = pb.coop_peer_module()
    ctx.tape, how = roam_tape()
    if ctx.tape is None:
        ctx.instrument = True
        kw = {"caps": CAPS_S167}
        if fp is not None:
            kw.update(digest=fp["combined"], fp_comps=fp["comps"])
        ctx.tape = write_instrument(cw._run_dir(g) / f"roam-INSTRUMENT-{LEG}.f9tape", cp, **kw)
        how = f"THE INSTRUMENT ({how}){' calibrated to my own fingerprint' if fp else ' (uncalibrated: digest 0)'}: {ctx.tape.name}"
    try:
        header, records, torn = cp.read_tape(ctx.tape)
    except Exception as err:                              # noqa: BLE001
        led.check("T2-TAPE", False, f"{ctx.tape} does not read back: {err}")
        led.close("not reached: the tape does not read back")
        return None
    ctx.instrument = ctx.instrument or bool(header.get("instrument"))
    facts = roam_tape_facts(records, cp, header=header)
    f_ok, bad = facts_ok(facts)
    ctx.rows = trailer_rows(records, cp)
    ctx.smap = seq_map(ctx.rows)
    ctx.s167 = tape_s167(records, cp)
    ctx.tape_detail = (f"{'THE INSTRUMENT -- ' if ctx.instrument else ''}{Path(ctx.tape).name} ({how}; {len(records)} records"
                       f"{f', torn {torn} B' if torn else ''}): " + ("the facts hold" if f_ok else "CANNOT -- " + "; ".join(bad))
                       + f"; rm8 S167: {ctx.s167['why']}")
    ctx.tape_ok = f_ok
    return records


def stall_windows(rows) -> dict:
    """(PURE) The stallhole leg's tape seconds off a ROAM tape: `from` (the host on 9011 on foot, STALL_FROM_S past its world-live start),
    `gap` (STALL_GAP_S), `sand` (STALL_PRESS_S, only with SAND_AT) and `press` (STALL_PRESS_S), each a pick_window clear of the others and
    ending before the host's first teleport after `from` (its ICE_TILE stand: its entry into 300 would pull the guest)."""
    live = world_live_t(rows)
    if live is None:
        return {"from": None, "gap": None, "sand": None, "press": None}
    frm = next((r["t"] for r in rows if r.get("has") and r.get("valid") and r["t"] >= live + STALL_FROM_S and r.get("mode") == 0), None)
    if frm is None:
        return {"from": None, "gap": None, "sand": None, "press": None}
    valid = [r for r in rows if r.get("has") and r.get("valid") and r["t"] >= frm]
    jump = next((b["t"] for a, b in zip(valid, valid[1:]) if torus(a["x"], a["z"], b["x"], b["z"]) >= 64.0), None)
    end = rows[-1]["t"] if rows else frm
    avoid = [(jump, end)] if jump is not None else []
    out = {"from": round(frm, 2)}
    gap = pick_window(rows, STALL_GAP_S, after=frm + STALL_ROOM_S, avoid=tuple(avoid))
    out["gap"] = gap
    nxt = (gap + STALL_GAP_S + STALL_RECOVER_S) if gap is not None else None
    sand = None
    if SAND_AT is not None and nxt is not None:
        sand = pick_window(rows, STALL_PRESS_S, after=nxt, avoid=tuple(avoid))
        nxt = (sand + STALL_PRESS_S + STALL_RECOVER_S) if sand is not None else None
    out["sand"] = sand
    out["press"] = pick_window(rows, STALL_PRESS_S, after=nxt, avoid=tuple(avoid)) if nxt is not None else None
    return out


def _b_teleport(g, ctx: _Ctx, xz) -> object:
    """Control on, the guest teleported onto ``xz`` (the overworld teleport sticks only with control live), sampled."""
    try:
        ww._control(g, True)
        cw.teleport_settle(g, xz)
    except HarnessError as err:
        g.note(f"the teleport onto {xz} raised: {str(err)[:160]}")
    return _sample(g, ctx)


def _stall_press(g, ctx: _Ctx, name: str, kind: str, length: float) -> dict:
    """One press inside a stall window ``name`` (the peer's own BLACKHOLE edge): waits for the window, then for the lane's arrival age to
    pass StaleMs + PRESS_PAST_MS (the stall LIVE), presses Confirm, watches PRESS_WATCH_S. -> judge_stall_press's dict."""
    if not _wait(g, ctx, lambda s: name in ctx.events, EVENT_S, kinds="bh"):
        return {"kind": kind, "base": None, "why": f"the window {name} never opened (peer edges {sorted(ctx.events)})"}
    deadline = time.time() + length
    base = None
    while time.time() < deadline:
        st = _sample(g, ctx)
        _peer_events(ctx, "bh")
        if _stalled(st, PRESS_PAST_MS):
            base = st
            break
        if f"{name}_end" in ctx.events:
            break
        time.sleep(POLL_S / 2)
    if base is None:
        return {"kind": kind, "base": None, "why": f"the lane never passed StaleMs + {PRESS_PAST_MS} ms inside {name}"}
    _mark(ctx, f"{name}_press")
    g.press("confirm")
    _wait(g, ctx, lambda s: False, PRESS_WATCH_S, kinds="bh")
    return {"kind": kind, "base": base, "after": _samples_between(ctx, f"{name}_press")}


# ---- the T2 legs
def _run_b(g) -> None:
    """Round B's T2 legs (COOP_WWT_LEG walk | stallhole | hostb): one per launch."""
    calibrate = cb.CALIBRATE
    lever = b_t2_lever_of(LEG, LEVER_RAW) if calibrate else None
    if calibrate and LEVER_RAW is not None and lever is None:
        led = cb.Ledger(g, {"S167-T2-LEVER": "COOP_WWT_LEVER is the leg's own"})
        led.check("S167-T2-LEVER", False, f"COOP_WWT_LEVER={LEVER_RAW!r} is not one of {LEG}'s {B_T2_LEVERS[LEG]} -- nothing was edited")
        return
    cal = f"S167-{LEG.upper()}-CAL"
    led = cb.Ledger(g, b_leg_catalog(LEG, calibrate), finals=("T2-SAVE", "T2-INI", "T2H-INI", cal, "S167-WR-GATE"), width=DETAIL_W)
    ctx = _Ctx()
    ctx.field, ctx.lever = FARSHORE, lever
    ctx.new, ctx.s167, ctx.tape_detail, ctx.tape_ok = False, None, None, False
    try:
        {"walk": _b_walk, "stallhole": _b_stallhole, "hostb": _b_hostb}[LEG](g, led, ctx)
    except HarnessError as err:
        g.note(f"the {LEG} leg raised: {str(err)[:400]}")
        led.close(f"not reached: the leg raised ({str(err)[:200]})")
    finally:
        _t2_teardown(g, led, ctx)
        if "S167-WR-GATE" in led.catalog and "S167-WR-GATE" not in led.done:
            s167 = ctx.s167 or {}
            led.check("S167-WR-GATE", not ctx.instrument and ctx.tape is not None and s167.get("ok") is True,
                      "THE INSTRUMENT ran (a synthetic s167 host), NOT COOP_TAPE_WORLD_ROAM -- the owner-gated row is not run "
                      "(ROAM-TAPE.md: record it on an s167 host)" if ctx.instrument else
                      f"the recorded ROAM tape {ctx.tape}: {s167.get('why', 'never read')}")
        if calibrate:
            pred = B_T2_LEVER_PREDICTED.get((LEG, ctx.lever), ()) if ctx.new else B_T2_OLD_PREDICTED[LEG]
            g.note(f"{cal}: {'s167, LEVER ' + str(ctx.lever) if ctx.new else 'OLD (no round-B key)'}; predicted reds {sorted(pred)}; "
                   f"measured {ctx.measured}")
            led.close("not reached: the leg ended before this check")
            failed = led.failed() - {cal, "S167-WR-GATE"}
            led.check(cal, *judge_cal(failed, pred, ctx.measured, pred))
        led.close(final=True)


def _b_setup(g, led, ctx: _Ctx) -> bool:
    """The T2 guest (round A's _guest_setup), the stage off the probe, the calibration lever."""
    if not _guest_setup(g, led, ctx):
        return False
    ctx.new = b_new(g.state)
    g.note(f"the guest engine reads as s{ww.b_stage(g.state)} (round-B keys {'all' if ctx.new else 'NONE: OLD, no round-B op is sent'})")
    g.note(_b_pull(g, ctx, ctx.lever))
    return True


def _b_walk(g, led, ctx: _Ctx) -> None:
    """T2-B: the ROAM host (or THE INSTRUMENT, calibrated), the guest paired on 6603 and followed out: WR-FREE, WR-REFUSE, WR-REJOIN-FAR."""
    rows = list(WR_CHECKS)
    if not _b_setup(g, led, ctx):
        return
    fp = None
    if roam_tape()[0] is None and ctx.new:
        fp, why = _calibration_visit(g, ctx)
        g.note(f"THE INSTRUMENT's calibration visit: {why}")
    if _b_tape(g, led, ctx, fp=fp) is None:
        return
    led.check("T2-TAPE", ctx.tape_ok and (not ctx.new or not ctx.instrument or fp is not None), ctx.tape_detail
              + ("" if fp is not None or not ctx.instrument or not ctx.new else "; the calibration visit read no fingerprint"))
    if not ctx.tape_ok and not FORCE:
        led.unreached(rows, "this tape cannot carry the leg (T2-TAPE)")
        return
    ctx.base = g.state
    if not _replay(g, led, ctx, ["--at-end", "hold"], want_send=None, tag="world-roam-walk"):
        led.unreached(rows, "the instrument never started (T2-PEER)")
        return
    landed = _wait(g, ctx, lambda s: wf.first_judged([x for _t, x in ctx.samples[ctx.events["start"]:] if x.ui_state == "WorldHUD"])
                   is not None, LAND_S)
    if not landed:
        led.unreached(rows, f"the guest never landed on the world map within {LAND_S:g} s (ui {g.state.ui_state!r})")
        return
    _mark(ctx, "landed")
    # WR-FREE
    free_st = None
    if ctx.new:
        _wait(g, ctx, lambda s: judged(s) and walk_free(s), B_READY_S)
        free_st = next((s for s in reversed(_samples_between(ctx, "landed")) if judged(s) and walk_free(s)), None)
    else:
        _wait(g, ctx, lambda s: False, 2.0)
    moved, adv, st2 = cw.hold_walk(g, ww.WALK_FRAMES)
    _sample(g, ctx)
    led.check("S167-WR-FREE", *judge_wr_free(free_st, st2, moved, adv))
    ctx.measured["S167-WR-FREE"] = moved is not None and moved < ww.HELD_U
    # WR-REFUSE: the guest's own `fp fake` against the HOST's real section 11 (on s166: never sent)
    pre, at = _sample(g, ctx), cb.mark(g)
    r = {"pre": pre, "op": "worldwalk fp fake dead", "sent": "`worldwalk fp fake dead` on the guest"}
    if ctx.new:
        ok, why = _ww(g, "fp", "fake", "dead")
        r.update(sent_ok=ok, sent=r["sent"] + ("" if ok else f" REFUSED: {why[:80]}"))
        _wait(g, ctx, lambda s: judged(s) and _walk(s).get("why") == "fp_mismatch", B_CASE_S)
        r["ref"] = next((s for s in reversed(_samples_between(ctx, "landed")) if _walk(s).get("why") == "fp_mismatch"), None)
    else:
        r.update(sent_ok=False, ref=None)
    r["moved"], r["adv"], r["post"] = cw.hold_walk(g, ww.WALK_FRAMES)
    if ctx.new:
        _ww(g, "fp", "act")
        _wait(g, ctx, lambda s: judged(s) and walk_free(s), B_CASE_S)
    r["back"] = _sample(g, ctx)
    r["lines"] = cb.new(g, at)
    led.check("S167-WR-REFUSE", *judge_wr_refuse(r))
    ctx.measured["S167-WR-REFUSE"] = (r["moved"] is not None and r["moved"] < ww.HELD_U
                                      and _walk(r["post"]).get("why") != "fp_mismatch")
    # WR-REJOIN-FAR: the guest walks away on its own, then the tape's host enters 300 from its ICE_TILE stand
    moved_away, _got = _hold_until(g, ctx, D_MOVE_U + D_MOVE_MARGIN_U)
    _mark(ctx, "away")
    at2 = cb.mark(g)
    _wait(g, ctx, lambda s: s.ui_state == "FieldHUD" and s.field_id == ICE_CAVERN, EVENT_S + wf.REJOIN_S)
    _wait(g, ctx, lambda s: False, 1.0)
    after = _samples_between(ctx, "away")
    rejoin = cw.judge_rejoin_land(after, after[0] if after else g.state, cb.new(g, at2), field=ICE_CAVERN)
    led.check("S167-WR-REJOIN-FAR", *judge_wr_far((moved_away, None), after, rejoin))
    ctx.measured["S167-WR-REJOIN-FAR"] = moved_away < ww.HELD_U


def _b_stallhole(g, led, ctx: _Ctx) -> None:
    """WR-PAIR + W-STALLHOLE: the guest walks out ALONE (no session), the ROAM host `--from` a second on 9011 with the blackholes."""
    rows = list(SH_CHECKS)
    if not _b_setup(g, led, ctx):
        return
    if _b_tape(g, led, ctx) is None:
        return
    w = stall_windows(ctx.rows)
    ctx.windows = w
    w_ok = None not in (w["from"], w["gap"], w["press"]) and (SAND_AT is None or w["sand"] is not None)
    led.check("T2-TAPE", ctx.tape_ok and w_ok, ctx.tape_detail + f"; the stall windows {w} (sand {'at ' + str(SAND_AT) if SAND_AT else 'not run: no COOP_WWT_SAND_AT'})")
    if not (ctx.tape_ok and w_ok) and not FORCE:
        led.unreached(rows, "this tape cannot carry the leg (T2-TAPE)")
        return
    ok, why, _st = cw.walk_out(g)                         # ALONE: the guest's own walk out -- it will pair ON THE WORLD MAP
    if not ok:
        led.check("T2-PEER", False, f"the guest's own walk out failed: {why[:200]}")
        led.unreached(rows, "the guest never reached the world map alone")
        return
    ctx.base = g.state
    args = ["--from", f"{w['from']:g}", "--blackhole-at", f"{w['gap']:g}", "--blackhole-for", f"{STALL_GAP_S:g}"]
    order = ["gap"]
    if w["sand"] is not None:
        args += ["--blackhole-at", f"{w['sand']:g}", "--blackhole-for", f"{STALL_PRESS_S:g}"]
        order.append("sand")
    args += ["--blackhole-at", f"{w['press']:g}", "--blackhole-for", f"{STALL_PRESS_S:g}", "--at-end", "hold"]
    order.append("press")
    if not _replay(g, led, ctx, args, want_send=None, tag="world-roam-stallhole"):
        led.unreached(rows, "the instrument never started (T2-PEER)")
        return
    names = {k: f"bh{i + 1}" for i, k in enumerate(order)}
    # WR-PAIR: frozen on the world map (s167: walk.why 'pairing'), before the first window
    _wait(g, ctx, lambda s: s.ui_state == "WorldHUD" and judged(s) and ww.frozen(s)
          and (not ctx.new or _walk(s).get("why") is not None), STALL_PAIR_S, kinds="bh")
    _wait(g, ctx, lambda s: False, 1.0, kinds="bh")
    pre = _samples_between(ctx, "start", names["gap"]) if names["gap"] in ctx.events else _samples_between(ctx, "start")
    led.check("S167-WR-PAIR", *judge_wr_pair(pre, ctx.base))
    ctx.measured["S167-WR-PAIR"] = pair_old_shape(pre)
    # W-STALLHOLE: the 2.3 s blackhole, judged to its end + STALL_TAIL_S
    gap = names["gap"]
    if not _wait(g, ctx, lambda s: gap in ctx.events, EVENT_S, kinds="bh"):
        led.unreached(rows[1:], f"the blackhole never opened (peer edges {sorted(k for k in ctx.events if k.startswith('bh'))})")
        return
    _wait(g, ctx, lambda s: f"{gap}_end" in ctx.events, STALL_GAP_S + 10.0, kinds="bh")
    _wait(g, ctx, lambda s: False, STALL_TAIL_S, kinds="bh")
    _mark(ctx, "gap_after")
    base = ctx.samples[ctx.events[gap] - 1][1] if ctx.events[gap] > 0 else ctx.base
    win = _samples_between(ctx, gap, "gap_after")
    lines = _since(ctx, gap, "gap_after")
    led.check("S167-W-STALLHOLE", *judge_stallhole(base, win, lines))
    ctx.measured["S167-W-STALLHOLE"] = stall_lifted(win, lines)
    # W-STALLHOLE-KEYS: each press stand by a teleport between windows, the press past StaleMs inside its window
    presses = []
    for k, xz in (("sand", SAND_AT), ("press", ICE_TILE)):
        if k not in names:
            continue
        _b_teleport(g, ctx, xz)
        presses.append(_stall_press(g, ctx, names[k], "sand" if k == "sand" else "location", STALL_PRESS_S))
        if g.state.ui_state != "WorldHUD":
            break                                          # OLD's hazard: the press left the world (measured)
    led.check("S167-W-STALLHOLE-KEYS", *judge_stall_keys(presses))
    ctx.measured["S167-W-STALLHOLE-KEYS"] = press_leaked(presses)


def _b_hostb(g, led, ctx: _Ctx) -> None:
    """T2-HB: the desktop an s167 HOST on 9011, serve-guest's walking v15 record in four phases (each its own process and tap)."""
    rows = list(THB_CHECKS)
    if not _host_preflight(g, led):
        return
    cb.provenance(g)
    g.newgame()
    g.warp(FARSHORE)
    try:
        g.no_encounters(True)
    except HarnessError as err:
        g.note(f"noencounter refused ({str(err)[:160]})")
    g.wait_frames(45)
    ctx.eng = pb.EngineLog(g.engine_log())
    ctx.guard = pb.IniGuard(Path(g.game_path) / "Memoria.ini", HOST_VALUES, label="coop-world-walk-t2-hostb", run_dir=cw._run_dir(g))
    try:
        g.note(ctx.guard.apply())
    except (OSError, RuntimeError) as err:
        led.check("T2H-PEER", False, f"the Memoria.ini edit failed: {err}")
        led.close("not reached: Memoria.ini could not be edited")
        return
    cfg = cb.poll(g, lambda s: bool(pb.hits(ctx.eng.lines(), "config", pred=lambda m: m.group(1) == "True" and m.group(2) == "host"
                                           and m.group(6) == CODE)), 12.0, "the host config line")
    if not cfg:                                            # (round A's T2-H: Ensure reads the ini at a field load)
        g.warp(FARSHORE)
        cfg = cb.poll(g, lambda s: bool(pb.hits(ctx.eng.lines(), "config", pred=lambda m: m.group(2) == "host")), 12.0, "config")
    ok, why, _st = cw.walk_out(g)
    if not ok:
        led.check("T2H-PEER", False, f"the host's walk out failed: {why[:200]}")
        led.unreached(rows, "the host never reached the world map")
        return
    _wait(g, ctx, lambda s: judged(s) and s.world_id == WORLD and (not b_new(s) or _fp(s).get("ready") is True), 30.0)
    ctx.new = b_new(g.state)
    g.note(f"the host engine reads as s{ww.b_stage(g.state)}; {_b_pull(g, ctx, ctx.lever)}")
    ctx.base = g.state
    peer_ok = None
    for phase, extra in THB_PHASES:
        row = f"S167-THB-{phase.upper()}"
        p = _serve(g, ctx, phase, ["--walk-out", "0.5", "--walk-load", "0.5", *extra])
        if peer_ok is None:
            hdr = judge_live_header(p.hdr[1] if p.hdr else None, pb.probe_wire(g), side="host") if p.hdr else (False, "no host-wire line")
            relay = pb.hits(ctx.eng.lines(), "relay_up", pred=lambda m: m.group(3) == "host" and m.group(2) == CODE)
            peer_ok = p.up is not None and p.conn is not None and hdr[0] and bool(relay) and bool(cfg)
            led.check("T2H-PEER", peer_ok, f"wire: {hdr[1]}; config {bool(cfg)}; peer {p.up[1] if p.up else 'never listened'} / "
                                           f"{p.conn[1] if p.conn else 'no HOST'}; engine {pb.show(relay, 1)}")
            if not peer_ok:
                _end_phase(g, ctx, p, phase)
                led.unreached(rows, "the instrument never started (T2H-PEER)")
                return
        _wait(g, ctx, lambda s: _hg(s).get("place") == BW.WW_PLACE_WORLD and judged(s), TH_DIAL_S + 10.0)
        _wait(g, ctx, lambda s: False, THB_PHASE_S)
        _end_phase(g, ctx, p, phase)
        ss = _samples_between(ctx, phase, f"{phase}_end")
        led.check(row, *judge_thb(phase, ss, _since(ctx, phase, f"{phase}_end")))
        ctx.measured[row] = thb_quiet_shape(ss)


# ---- the duo (COOP_WWT_DUO=b)
def _run_duo_b(d) -> None:
    """Round B's duo: every row recorded (strict off); COOP_CALIBRATE=1 judges S167-D-CAL by the GUEST's stage (OLD) or the lever."""
    calibrate = cb.CALIBRATE
    lever = b_t2_lever_of("duo", LEVER_RAW) if calibrate else None
    strict, d.strict = d.strict, False
    failed, done, measured, sent = [], set(), {}, []
    marks, hold, state = {}, {"asked": False, "sent": False, "released": False}, {"new": False}

    def check(cid, ok, detail):
        if cid in done:
            return
        done.add(cid)
        if not ok:
            failed.append(cid)
        d.check(bool(ok), f"{cid}: {DUO_B_CHECKS.get(cid, cid)}", str(detail)[:DETAIL_W], cid=cid)

    def rest(why):
        for cid in DUO_B_ORDER:
            if cid != "S167-D-SHARED" and cid not in done:
                check(cid, False, f"not reached: {why}"[:DETAIL_W])
    try:
        if calibrate and LEVER_RAW is not None and lever is None:
            rest(f"COOP_WWT_LEVER={LEVER_RAW!r} is not one of the round-B duo's {DUO_B_LEVERS} -- nothing was sent")
        else:
            marks["host"], marks["guest"] = cb.mark(d.host), cb.mark(d.guest)
            state["new"] = b_new(d.host.state, d.guest.state)
            _duo_b(d, check, rest, lever, sent, measured, hold, state["new"])
    except HarnessError as err:
        d.note(f"the round-B duo raised: {str(err)[:400]}")
        rest(f"the duo raised ({str(err)[:200]})")
    finally:
        if (hold["asked"] or hold["sent"]) and not hold["released"]:
            try:
                d.note(f"the backstop: {_release_guest(d.guest, hold)}")
            except Exception as err:                       # noqa: BLE001 - the verdict rows below must still be written
                d.note(f"the backstop `worldfollow release` raised: {str(err)[:160]}")
        try:
            hl, gl = cb.new(d.host, marks.get("host", 0)), cb.new(d.guest, marks.get("guest", 0))
        except HarnessError:
            hl, gl = [], []
        check("S167-D-SHARED", *wf.judge_shared(hl, gl))
        rest("the duo ended before this row")
        for who, g in (("host", d.host), ("guest", d.guest)):
            if sent:
                try:
                    ok, why = cb.try_ns(g, "worldwalk", "clear")
                    d.note(f"`worldwalk clear` on the {who}: {'ok' if ok else why[:120]}")
                except HarnessError:
                    pass
        if calibrate:
            new = state["new"]
            pred = DUO_B_LEVER_PREDICTED.get(lever, ()) if new else DUO_B_OLD_PREDICTED
            skip = set() if D_BATTLE else {"S167-D-BATTLE"}
            pred = tuple(r for r in pred if r not in skip)
            ok, why = judge_cal(set(failed) - skip, pred, measured, pred)
            why += f"; not run (configuration): {sorted(skip) or 'none'}"
            d.check(ok, "S167-D-CAL: CALIBRATION -- exactly the predicted round-B duo rows red (OLD by the stage, else the lever's)",
                    f"{'s167' if new else 'OLD (no round-B key)'}, lever {lever}: {why}", cid="S167-D-CAL")
        d.strict = strict


def _walk_both(d, th, tg) -> str:
    """D-W3: `hold up` on BOTH games at once, released once each moved D_MOVE_U + D_MOVE_MARGIN_U (the Taps' own buffers) or the deadline."""
    goal = D_MOVE_U + D_MOVE_MARGIN_U
    t0 = time.time()
    d.host.hold("up", D_WALK_FRAMES)
    d.guest.hold("up", D_WALK_FRAMES)
    why = "the deadline"
    while time.time() < t0 + D_WALK_S:
        hs, gs = [s for _t, s in list(th.samples)], [s for _t, s in list(tg.samples)]
        if max(tx_moved(hs), world_moved(hs)) >= goal and max(tx_moved(gs), world_moved(gs)) >= goal:
            why = "the distance"
            break
        time.sleep(0.02)
    d.host.send("release up", wait=False)
    d.guest.send("release up", wait=False)
    time.sleep(D_WALK_TAIL_S)
    return f"both walks stopped on {why} after {time.time() - t0:.1f} s"


def _poll_walk(g, pred, seconds: float, what: str, new: bool):
    """On s167 the first judged sample where ``pred(walk)`` holds (None if never); on s166 the state after SETTLE frames."""
    if not new:
        g.wait_frames(ww.SETTLE_FRAMES)
        return None
    return cb.poll(g, lambda s: judged(s) and pred(_walk(s)), seconds, what)


def _full_map(guest) -> tuple:
    """The guest's full map asked for: the minimap on (ww._b_minimap_on), then Select. -> (the base before the Select, the samples after)."""
    ww._b_minimap_on(guest)
    base = guest.state
    guest.press("select")
    after = [cb.poll(guest, lambda s: _dot(s).get("hud") == "FullMap", ww.SEL_S, "the full map") or guest.state]
    guest.wait_frames(ww.SKEW_FRAMES)
    after.append(guest.state)
    return base, after


def _duo_b(d, check, rest, lever, sent: list, measured: dict, hold: dict, new: bool) -> None:
    host, guest = d.host, d.guest
    hs, gs = host.state, guest.state
    both = (hs.ui_state == "FieldHUD" and hs.field_id == FARSHORE and gs.ui_state == "FieldHUD" and gs.field_id == FARSHORE
            and cw._s(gs, "mirroring") is True)
    check("S167-D0", both and new, f"host {hs.ui_state} {hs.field_id} (s{ww.b_stage(hs)}, wire {wire_of(hs)}); guest {gs.ui_state} "
                                   f"{gs.field_id} (s{ww.b_stage(gs)}, wire {wire_of(gs)}), mirroring {cw._s(gs, 'mirroring')!r}")
    measured["S167-D0"] = not new
    if not both:
        rest("the pair is not on 6603 with the guest mirroring (D0)")
        return
    if not new:
        d.note("OLD (no round-B key on the pair): no round-B op is ever sent; each row MEASURES s166's shape")
    if new and lever in B_LEVER_OPS:                      # on the GUEST: any-role levers (THE DUO CANNOT PULL A SELFTEST-ROLE LEVER)
        for op in B_LEVER_OPS[lever]:
            ok, why = _ww(guest, *op)
            sent.append(op[0]) if ok else d.note(f"`worldwalk {' '.join(op)}` REFUSED on the guest: {why[:120]}")
    try:
        host.no_encounters(True)
    except (HarnessError, AttributeError) as err:
        d.note(f"noencounter refused on {FARSHORE} ({str(err)[:120]})")
    # the follow-out (round A's route: the hold until the host is live, the Taps from before the guest can leave)
    d.note(f"the walk out: {_hold_guest(guest, gs, hold)}")
    ok, why, th, tg = _walk_out_tapped(d)
    if not ok:
        rest(f"the host's walk out failed ({why[:160]})")
        return
    _await_host_live(th, cw.WORLD_S)
    time.sleep(D_HOLD_SETTLE_S)
    if hold["sent"]:
        _await_guest_held(tg, D_HOLD_READ_S)
        d.note(f"the walk out: {_release_guest(guest, hold)}")
    deadline = time.time() + cw.WORLD_S + D_LAND_S
    while time.time() < deadline and wf.first_judged([s for _t, s in list(tg.samples) if s.ui_state == "WorldHUD"]) is None:
        time.sleep(0.1)
    th.stop()
    gsamp = tg.stop()
    if wf.first_judged([s for _t, s in gsamp if s.ui_state == "WorldHUD"]) is None:
        rest("the guest never landed on the world map")
        return
    try:
        host.no_encounters(True)
    except (HarnessError, AttributeError) as err:
        d.note(f"noencounter refused on the world map ({str(err)[:120]})")
    # D-WFREE
    st = _poll_walk(guest, lambda w: w.get("free") is True, B_READY_S, "the guest's walk free", new) or guest.state
    check("S167-D-WFREE", *judge_dw_free(st, host.state))
    measured["S167-D-WFREE"] = ww.frozen(st) and not walk_free(st)
    # D-W1 / D-W2 / D-W3
    for kind, row in (("w1", "S167-D-W1"), ("w2", "S167-D-W2"), ("w3", "S167-D-W3")):
        h0, g0 = wf.world_xz(host.state), wf.world_xz(guest.state)
        th, tg = _tap_both(d)
        if kind == "w1":
            d.note(f"D-W1: {_walk_host(guest, tg)}")
        elif kind == "w2":
            d.note(f"D-W2: {_walk_host(host, th)}")
        else:
            d.note(f"D-W3: {_walk_both(d, th, tg)}")
        hsamp, gsamp = [s for _t, s in th.stop()], [s for _t, s in tg.stop()]
        h1, g1 = wf.world_xz(host.state), wf.world_xz(guest.state)
        check(row, *judge_dw(kind, hsamp, gsamp, h0, h1, g0, g1))
        measured[row] = dw_frozen(gsamp) if kind == "w2" else dw_held(gsamp)
    # D-BATTLE (the host's world battle; the guest apart with its full map open: decision 23's boot close, the review's R1)
    boot = None
    if D_BATTLE:
        boot = _duo_b_battle(d, check, measured, new, lever)
    else:
        check("S167-D-BATTLE", False, "not run: COOP_WWT_DUO_BATTLE=0 (the stand-in duo has no diorama model)")
    # D-RIDE: the host on its chocobo -- the guest's verdict
    pre = guest.state
    r = {"pre": pre, "op": "vehicle 1 (the host)", "sent": "`vehicle 1` on the HOST", "lines": []}
    try:
        host.vehicle(1)
        host.wait_frames(20)
        r["sent_ok"] = True
    except HarnessError as err:
        r.update(sent_ok=False, sent=f"`vehicle 1` on the HOST REFUSED: {str(err)[:120]}")
    r["ref"] = _poll_walk(guest, lambda w: w.get("why") == "riding", B_CASE_S, "the guest's riding verdict", new)
    r["moved"], r["adv"], r["post"] = cw.hold_walk(guest, ww.WALK_FRAMES)
    try:
        host.vehicle(0)
        host.wait_frames(20)
    except HarnessError as err:
        d.note(f"`vehicle 0` on the host refused: {str(err)[:120]}")
    r["back"] = _poll_walk(guest, lambda w: w.get("free") is True, B_CASE_S, "the guest free again", new) or guest.state
    check("S167-D-RIDE", *ww.judge_refuse("S167-D-RIDE", "riding", r))
    measured["S167-D-RIDE"] = r["moved"] is not None and r["moved"] < ww.HELD_U and _walk(r["post"]).get("why") != "riding"
    # D-REFUSE: the guest's `fp fake` -- named on the guest off the host's real section 11, 'fp_differs' on the host
    hat, gat = cb.mark(host), cb.mark(guest)
    r = {"pre": guest.state, "op": "worldwalk fp fake dead", "sent": "`worldwalk fp fake dead` on the guest"}
    thf = wf.Tap(host, TAP_S)
    thf.start()
    if new:
        ok, why = _ww(guest, "fp", "fake", "dead")
        r.update(sent_ok=ok, sent=r["sent"] + ("" if ok else f" REFUSED: {why[:80]}"))
    else:
        r["sent_ok"] = False
    r["ref"] = _poll_walk(guest, lambda w: w.get("why") == "fp_mismatch", B_CASE_S, "the guest's fp_mismatch", new)
    r["moved"], r["adv"], r["post"] = cw.hold_walk(guest, ww.WALK_FRAMES)
    time.sleep(D_S)
    hsamp = [s for _t, s in thf.stop()]
    if new:
        _ww(guest, "fp", "act")
    r["back"] = _poll_walk(guest, lambda w: w.get("free") is True, B_CASE_S, "the guest free again", new) or guest.state
    r["lines"] = cb.new(guest, gat)
    g_ok, g_why = judge_wr_refuse(r)
    h_ok, h_why = judge_host_fp(hsamp, cb.new(host, hat))
    check("S167-D-REFUSE", g_ok and h_ok, f"the guest: {g_why}; {h_why}")
    measured["S167-D-REFUSE"] = (r["moved"] is not None and r["moved"] < ww.HELD_U
                                 and not any(_line(s).get("asked") == "fp_differs" for s in hsamp))
    # D-ENTRY: W-ENTRY's judge on the duo guest
    try:
        guest.watch(ww.DISCOVERY_BIT)
    except HarnessError as err:
        d.note(f"watch {ww.DISCOVERY_BIT} refused on the guest: {str(err)[:120]}")
    ww._control(guest, True)
    cw.teleport_settle(guest, ICE_TILE)
    base, at = guest.state, cb.mark(guest)
    guest.press("confirm", ww.ENTRY_HOLD_FRAMES)
    samples = ww._watch(guest, ww.PRESS_S)
    lines = cb.new(guest, at)
    check("S167-D-ENTRY", *ww.judge_entry(base, samples, lines))
    measured["S167-D-ENTRY"] = ww.entry_silent(base, samples, lines, ww._hazard_field)
    if guest.state.ui_state != "WorldHUD":
        rest("the guest left the world map at the entrance press (its hazard): the rows after it need it there")
        return
    cw.teleport_settle(guest, FS_LANDING)
    # D-REJOIN-FAR + D-MAP: the host onto the tile, the guest far away (free) with its full map open, the host Confirms into 300
    cw.teleport_settle(host, ICE_TILE)
    host.wait_frames(cw.PROMPT_FRAMES)
    far_st = _poll_walk(guest, lambda w: w.get("free") is True, B_CASE_S, "the guest free before the map", new) or guest.state
    m = {"why": "the full map never asked for"}
    m["base"], m["opened"] = _full_map(guest)
    gat3 = cb.mark(guest)
    gbase = guest.state
    tg = wf.Tap(guest, TAP_S)
    tg.start()
    hin = None
    try:
        host.press("confirm")
        hin = cb.poll(host, lambda s: s.ui_state == "FieldHUD" and s.field_id == ICE_CAVERN, cw.FIELD_S, "the host on 300")
    except HarnessError as err:
        d.note(f"the host's entry raised: {str(err)[:200]}")
    if hin is not None:
        cb.poll(guest, lambda s: s.ui_state == "FieldHUD" and s.field_id == ICE_CAVERN, wf.REJOIN_S, "the guest on 300")
        time.sleep(1.0)
    gl = [s for _t, s in tg.stop()]
    glines = cb.new(guest, gat3)
    rejoin = cw.judge_rejoin_land(gl, gbase, glines, field=ICE_CAVERN) if hin is not None else (False, "the host never entered 300")
    check("S167-D-REJOIN-FAR", *judge_d_far(far_st, ICE_TILE, rejoin))
    measured["S167-D-REJOIN-FAR"] = ww.frozen(far_st) and not walk_free(far_st)
    m.update(rejoin=gl, lines=glines, landed=rejoin[0], boot=boot)
    check("S167-D-MAP", *judge_d_map(m))
    measured["S167-D-MAP"] = map_never_full(m)
    if hin is None:
        rest("the host never entered 300")
        return
    _duo_b_wait(d, check, measured, new)


def _duo_b_battle(d, check, measured: dict, new: bool, lever=None):
    """D-BATTLE: the guest walks apart (`hold down`, the closed loop), opens its full map, the host's world battle and both warm returns.
    -> the boot close's (ok, why) for D-MAP, or None when the map never opened."""
    host, guest = d.host, d.guest
    tg = wf.Tap(guest, TAP_S)
    tg.start()
    d.note(f"D-BATTLE: apart -- {_walk_host(guest, tg, button='down')}")
    tg.stop()
    b = {"host_pre": host.state, "why": ""}
    _mb, opened = _full_map(guest)
    b["opened"] = any(_dot(s).get("hud") == "FullMap" for s in opened)
    b["pre"] = guest.state
    gat = cb.mark(guest)
    tg = wf.Tap(guest, TAP_S)
    tg.start()
    try:
        host.world_battle(D_SCENE, group=D_GROUP, rand=True, timeout=60.0)
        host.fight(timeout=D_FIGHT_S, finish=True, max_turns=1_000_000)
        host.wait_world(timeout=D_RETURN_S)
        cb.poll(guest, lambda s: s.ui_state == "WorldHUD" and judged(s), D_RETURN_S, "the guest's warm return")
        time.sleep(D_S)
    except HarnessError as err:
        b["why"] = f"the duo battle raised: {str(err)[:200]}"
    gsamp = [s for _t, s in tg.stop()]
    b["booted"] = any(s.ui_state != "WorldHUD" for s in gsamp) or any(cb.path(s, "netsync.world.dio.booted_world") is True for s in gsamp)
    b["lines"] = cb.new(guest, gat)
    after = _poll_walk(guest, lambda w: w.get("free") is True, B_READY_S, "the guest walks again", new) or guest.state
    b["after"], b["free_after"] = after, walk_free(after)
    ok, why = judge_d_battle_b(b)
    check("S167-D-BATTLE", ok, why)
    if new and lever == "fullmap":
        # the lever's shape (s166's map): the walker's full map refused, so it never opened, no co-op close ran, the boot still ran
        measured["S167-D-BATTLE"] = (not b["opened"]) and _d(b["pre"], after, _wmapb, "coop_closes") == 0 and bool(b["booted"])
    else:
        measured["S167-D-BATTLE"] = frozen_not_walking(after)
    if not b["opened"]:
        return None
    dc = _d(b["pre"], after, _wmapb, "coop_closes")
    n_c = cb.count(b["lines"], BW.log_ww_map_closed("boot", WORLD))
    return (dc == 1 and n_c == 1 and _wmapb(after).get("last_close") == "boot",
            f"coop_closes +{dc}, last_close {_wmapb(after).get('last_close')!r}, the boot close line {n_c}x")


def _duo_b_wait(d, check, measured: dict, new: bool) -> None:
    """D-REJOIN-WAIT: both back on 9011 (the host's warp to 6603 and its walk out, the guest following), the guest's control off, the host
    into 300 (the rejoin waits) and back out of 6603, the guest's control on."""
    host, guest = d.host, d.guest
    w = {"why": ""}
    try:
        host.warp(FARSHORE)
        if cb.poll(guest, lambda s: s.ui_state == "FieldHUD" and s.field_id == FARSHORE, D_FOLLOW_S, "the guest on 6603") is None:
            guest.warp(FARSHORE)
        ok, why, _st = cw.walk_out(host)
        if not ok:
            raise HarnessError(f"the host's second walk out failed: {why[:160]}")
        if cb.poll(guest, lambda s: s.ui_state == "WorldHUD" and s.world_id == WORLD and judged(s), D_FOLLOW_S + D_LAND_S,
                   "the guest followed out") is None:
            raise HarnessError("the guest never followed the host out the second time")
        host.no_encounters(True)
        _poll_walk(guest, lambda x: x.get("free") is True, B_READY_S, "the guest walks", new)
        ww._control(guest, False)
        w["base"] = guest.state
        tg = wf.Tap(guest, TAP_S)
        tg.start()
        try:
            cw.teleport_settle(host, ICE_TILE)
            host.wait_frames(cw.PROMPT_FRAMES)
            host.press("confirm")
            w["entered"] = cb.poll(host, lambda s: s.ui_state == "FieldHUD" and s.field_id == ICE_CAVERN, cw.FIELD_S, "the host on 300") is not None
            time.sleep(D_WAIT_S)
            host.warp(FARSHORE)
            ok, why, _st = cw.walk_out(host)
            w["returned"] = ok
            host.no_encounters(True)
            time.sleep(D_S)
        finally:
            ww._control(guest, True)
            time.sleep(D_S)
            w["samples"] = [s for _t, s in tg.stop()]
        w["after"] = _poll_walk(guest, lambda x: x.get("free") is True, B_READY_S, "the guest free again", new) or guest.state
    except HarnessError as err:
        w["why"] = str(err)[:200]
    check("S167-D-REJOIN-WAIT", *judge_d_wait(w))
    measured["S167-D-REJOIN-WAIT"] = frozen_not_walking(w.get("after"))


# ================================================================================================ CLI (offline: the instrument)
def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) == 2 and argv[0] == "--make-roam-instrument":
        sys.path.insert(0, str(pb.TOOLS))
        p = write_instrument(argv[1])
        cp = pb.coop_peer_module()
        header, records, _torn = cp.read_tape(p)
        facts = roam_tape_facts(records, cp, header=header)
        ok, bad = facts_ok(facts)
        print(f"{p}: {len(records)} record(s), wire {header.get('wire')}; THE INSTRUMENT (synthetic) -- facts "
              f"{'hold' if ok else 'FAIL: ' + '; '.join(bad)}; windows {facts['windows']}")
        return 0 if ok else 1
    print(__doc__.split("\n\n")[0])
    print("usage: py coop_world_walk_t2.py --make-roam-instrument <out.f9tape>   (the legs run under tools/play.py / duo.py)")
    return 2


if __name__ == "__main__":
    sys.exit(main())
