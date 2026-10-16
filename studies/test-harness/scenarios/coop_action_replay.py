"""R3 GROUP 2, s134 -- THE GUEST ACTION REPLAY (memoria-patch s134), the solo bench and its T2 tape leg, run unattended.

THE GAP (studies/battle-coop/R3-DESIGN.md 3.3.3 as amended by R3-ACTION-REPLAY-AUDIT.md 2.2 and section 3; the design's
"s123": group 2 was renumbered s133-s141). Since s133 the host ships a START before every action and an END after it
(type-6 records, impact ids, header bit 5). s134 is the GUEST half: each START is REPLAYED on the guest's battle diorama
as a standalone CMD_DATA through the stock SFXRework sequencer -- the attack or the cast plays where before only numbers, a
flinch and a player-only MP_ATTACK swing showed. PRESENTATION ONLY (THE CONTAINMENT LAW): btl_cmd.ExecVfxCommand's first
statement short-circuits every replay hit (no CalcMain, no SysTrans writes, no phase flip); CalcMain's head and the SysTrans
case count a fall-through (THE TRIPWIRE, `act.guest.calc_while_booted`, 0 in a healthy boot). Read back:
`netsync.battle.act.guest` (every role) and `battle.units[].anim|anim_frame|away|rot_y|acting|die_seq|row`. Bench verbs
(selftest role, a booted diorama): `netsync actbench feed <hex[,hex...]>` / `feedat <ms> <hex...>` (type-6 frames into the
bench inbox, through the transport's own route), `tape play [pct]` (s133's loopback tape into it), `replay on|off` (off =
the pre-s134 guest), `rework on|off`, `shortcircuit on|off` (off = the NEXT replay's hits fall through: the tripwire's
red), `knob 0|1|ini` (a process-local [Netsync] ActionReplay), `clear`, `teardown` (ActDiscardAll, no Leave first).

TWO LEGS, one per launch (COOP_ACT_LEG):
  solo (the default) -- the desktop in the forced selftest role, every fabricated leg and every lever calibration.
  tape -- THE T2 TAPE BENCH (audit D09 / 4.9): a RECORDED s133 host tape replayed into this desktop as the GUEST by
          tools/harness/coop_peer.py `replay-host` (coop_cut_hold.py's instrument: the real transport intake, the
          watcher's boot, ActionTick's nonce gate -- the only solo way to exercise them), judged on `act.guest`.

PRECONDITIONS -- THE OPERATOR'S JOB:
  * solo: Memoria.ini [Netsync] Enabled = 0 (or absent). The selftest role is refused on a live-configured install; the
    bench never edits Memoria.ini (S134-INI reads it READ-ONLY and, when it reads 1, records itself red and runs NOTHING).
  * tape: the game CLOSED before the launch (play.py launches it), no production bridge on 49201, [SaveFile]
    AutoSaveOnlyAtMoogle 0; the leg writes [Netsync] (backed up first, restored byte-exact in the `finally`) exactly as
    coop_cut_hold.py does, plus ActionReplay (1; 0 under COOP_CALIBRATE).
  * The DLL under test deployed and the game launched on it (the orchestrator's: this bench deploys nothing).
  * COOPPARTY (studies/battle-coop/bench/coopparty.field.toml, 30604) registered: Zidane / Vivi / Garnet / Steiner (PRE).

THE SOLO BENCH. Field 30602 (cb.FIELD), `stateevery 1`. Battle 1 (the TAPE): s133's in-engine tape (`actbench tape rec`)
over `battle 306 <COOP_ACT_GROUP, default 4>` -- Fang x2 -- with a plan that cannot end the fight early (THE LESSON of
s133's first runs: a check that needs N turns orders its plan so nothing that can END the fight runs first): Zidane Attacks
the sturdiest standing ALLY once, Garnet uses a Potion on herself, every other prompt Defends until both are done and
two more prompts have passed (the Fangs act in between), then `fight` (Attack) to the victory; `tape stop`, the tape paged
out (`tape dump`) and read OFFLINE: Zidane's Attack START (its vfx num, its START -> first impact ms), Garnet's Potion
START (its num), an enemy START (its actor, sub, num). Then THE INVARIANTS (cb.fingerprint: gil, the bag, levels, exp, AP,
kill counters) and eight diorama boots, each `dioboot 306 <group>` on 30602 (the tape's scene and group), the legs below.
Every fed START carries the bench's own nonce byte (0x5C, MARKER: nothing else in the process names it) and a fresh id.

WHAT IS PROVEN (S134-*):
  INI   precondition: [Netsync] Enabled reads 0 / absent (READ-ONLY) -- else NOTHING runs.
  S0    the harness forced the selftest role (Memoria.ini untouched).
  P0    the probe: `netsync.battle.act.guest` is published -- else no guest op is EVER sent (fails closed).
  PROOF the selftest proof block's line reads exactly 'action replay selftest: OK (34 rows)' -- no FAIL line.
  PRE   precondition: battle 1 seats Zidane, Vivi and Garnet and 2+ enemies.
  TAPE  battle 1's s133 tape carries Zidane's Attack START (kind 3, an impact naming it -- its START -> impact ms is
        Leg M's yardstick, taken off an Attack on an ENEMY when the tape has one), Garnet's Potion START and an enemy START
        (kind 2, num == sub) -- the nums the fabricated legs replay; the STARTs matched by WIRE actor (the compacted party
        rank, never a btl slot). (A short fight can leave it red: named.)
  BOOT  boot 1 steady (PHASE_NORMAL, the steady latch) with `act.guest` at rest: starts_rx 0, running 0,
        calc_while_booted 0 -- the no-replay diorama -- and battle_ms counting.
  -- boot 1: the fabricated legs --
  A1    Leg A, a player replay (Zidane, Attack on a Fang, kind 3, the taped num, the TAPED host Speed -- the camera path
        the host taped): within 15 frames of the feed started +1 and units[Zidane].acting.
  A2    ...its `anim` leaves the idle clip, `away` peaks above 400, then falls below 10.
  A3    ...it ENDS naturally: ended +1, hits >= 1, last.state "ended", running 0.
  A4    ...presentation only: every unit's hp_raw / mp unchanged, menu.r9_refused and end.ach_held unchanged, the units
        with a cmd_busy unchanged, calc_while_booted unchanged (0).
  M     Leg M, the stance (audit amendment 17): Zidane's `mot` reads MP_IDLE_CMD (9) or MP_SET (20) between the launch and
        the first hit, and last.first_hit_ms - launch_ms is within one IDLE_CMD loop (1000 ms) of the taped host's START ->
        first impact.
  AH    Leg A-H, the heal leg (review F1): Garnet's Potion START on the most damaged ally, NO impact: that ally's hp_raw
        unchanged after the replay ENDS (SetRecover is not isDebug-gated: a fall-through would heal). It needs an ally
        BELOW its max HP (a full one cannot show a heal): with none, AH reads "not reached: no damaged ally" (red).
  B     Leg B, an enemy replay (EnemyAtk, kind 2, the taped sub): the enemy is `acting`, its `anim` changes (the clip; the
        anim after the end is reported, not judged), the replay ends, Zidane (its target) never shows a damage motion (no
        impact: no flinch).
  F     Leg F, pairing: a START and an impact naming its id (figure 4321, the target's raws unchanged) in ONE feed:
        paired +1, swing_skipped +1 (the replay is the clip), the replay ran.
  G     Leg G, an old host: a 46-byte impact (no extension) from Zidane: old_host true, the 'host predates action replay'
        line once, swing_skipped unchanged, Zidane's mot reads MP_ATTACK (23: the legacy swing).
  J     Leg J, stale (review F6): a START and its END in ONE feed: declined "stale" (stale +1), started unchanged.
  L     Leg L, Change (review F4): a Change START (kind 4) for Vivi: after its hit her `row` has flipped, and `away` < 10
        at its end (from the NEW base_pos).
  H     Leg H: `rework off` -> a START declines "rework" (the 'NO SFXRework' line); `rework on`.
  I     Leg I (audit 4.8): `knob 0` -> a START declines "knob", Memoria.ini byte-identical, the selftest role still
        forced (the session stays up); `knob ini`.
  PAUSE (audit 3.5): a Leg-A replay paused mid-run 4 s (`press pause` twice): no abort, paused_ms +3000 or more, it ends,
        and its battle-time span (end_ms - launch_ms) is shorter than its wall span by the pause. The pause must land
        MID-replay: running >= 1 on the sample where it took hold AND on the first sample after the unpause, end_ms at or
        after that sample's battle_ms (a replay that ended before or under the pause is PAUSE's red, named in its
        detail -- else the span and "no abort" judge nothing). Each press is VERIFIED (the pause: paused_ms rises; the unpause: battle_ms advances) -- a swallowed press is PAUSE's red, never a paused
        diorama left to the legs after it (the pause key is pressed again until battle_ms advances).
  TRIP  THE TRIPWIRE'S OWN RED (every run): `shortcircuit off` + a Leg-A START -> calc_while_booted rises (its hit reached
        CalcMain), the 'runs WITHOUT the short-circuit' and TRIPWIRE lines, the one-shot lever spent.
  TRIPST (audit amendment 13): the same for a SysTrans START (Zidane, kind 3 Special_Trance_Activate): the SysTrans case
        counts (calc_while_booted rises again); end.ach_held named.
  D2    Leg D2 (review F2, audit 4.8): a running replay, then `actbench teardown` (ActDiscardAll with NO Leave first): its
        line names 1 running replay dropped and nothing applied; 90 frames later (past any hit a kept action could land)
        running 0, no unit acting, aborted unchanged, every unit's HP/MP, ach_held and r9_refused unchanged,
        calc_while_booted unchanged; the diorama still booted and contained; then a normal `dioleave`.
  -- boots 2-8 --
  BL    the boot backlog (audit amendment 5): a START fed during boot 2's intro (before the steady latch) declines
        "backlog".
  D     Leg D: boot 2, a running replay, `dioleave` -> aborted +1 "leave", back on the field, running 0.
  D0    a SMOKE check of the deferred Leave: boot 3, `dioleave` during the boot's swirl is refused "deferred" and the
        boot stays usable for E1 (aborted 0). It does NOT prove audit amendment 12 (a deferred Leave aborts nothing): no
        replay can run or park during the swirl (the drain waits for PHASE_NORMAL), so ActAbortAll's place before or after
        LeaveFrom's fade check cannot show here -- amendment 12 is not benched.
  E1    Leg E, victory (audit 3.2: the trailing loop's SFX wait exists only in MENU_OFF): boot 3, a running replay, then
        `endbench victory` -> injected, the phase reads MENU_OFF (5) on every sample while the replay runs, VICTORY (6)
        only after it ended.
  E2    the run-away hold (D02): boot 4, a running replay, `endbench escape` -> NOT injected while it acts (end_held +1,
        the 'waits for N acting replay(s)' line), injected "flee" once it ended.
  E3    W3 (D02): boot 5, a LONG summon replay (Garnet, SummonGarnet / Leviathan, kind 3 Leviathan__Full 179), `endbench
        escape` -> held, then at 4000 ms of battle time aborted "w3" and injected.
  E4    close (audit 3.2: R8 aborts, not W3): boot 6, E3's LONG summon replay (Leviathan__Full: it outlives the close
        fade, ~2.2 s of 15-TPS ticks before R8), `endbench other 4` -> injected "close" at once while it still runs, then
        aborted "r8" within 4 s (the close fade to black, then R8). A replay already ended at the injection is "not
        reached", never the engine's red.
  K     Leg K, the death-attack grace (review F3, D10): boot 7, `bbench start 0x01` + `bbench caps 0x22` -> bit5 latched;
        a LETHAL impact from Zidane on Fang 1. The expectation is PINNED per scene (DIE_ATK_SCENES), never taken from the
        engine's own verdict: scene 306's Fangs have no AttackOnDeath, so NO grace (armed +0, the mask 0 on EVERY publish
        from the feed to the death) and die_seq > 0 within DEATH_BOUND_MS (1000) of battle time from the feed -- a grace
        armed there is K's red (D10 armed it for a plain enemy). On a scene DIE_ATK_SCENES names
        (none yet), the positive half: the grace arms, die_seq stays 0 while that enemy's own EnemyDying START replays, > 0
        after.
  C     Leg C, the real host frames: boot 8 (the tape's scene and group), `tape play` -> every taped START received
        (starts_rx == the tape's), started == starts_rx - declined, every decline "noop" or "stale", running 0 within the
        tape's length + 5 s, faulted 0, aborted 0. A mid-tape frame is SHOT (an artifact to READ: a visible effect -- the
        reading is the operator's, never a verdict here).
  INV   THE INVARIANTS after the last leave: gil, the bag, levels, exp, AP, kill counters byte-equal to the snapshot
        before boot 1 (cb.fingerprint; battle_no reported apart).
  R     `reset` with `replay off`, `rework off`, `shortcircuit off`, `knob 0` left set: the 'levers back' line; RE-READ WITH
        THE ROLE (cb.reread_with_role): every lever at rest, inbox 0.
NOT PROVEN HERE: the TRANSPORT's stale->live resume burst (a backlog after a cut: coop_peer's blackhole drops frames, it
cannot delay them -- audit 4.9), hold-through (`hold_through`: a real cut), the AttackOnDeath positive half (no scene in
DIE_ATK_SCENES yet), audit amendment 12 (D0 is a smoke check), the run-away hold's BREAK on a real host (the host's
CLOSE+ESCAPE or its stale lane while a replay acts: the tape leg's host never flees), the Defend pose (IdleDefend is
never mirrored: risk 8), reflect bounces, a monster-transform command (declined by design), numbers held to the hit
(s135), fallback clips (s136), trance timing (s137).

CALIBRATION -- a check that cannot fail is not a check.
  * THE DEPLOYED DLL AT WRITING (s133) -- and any engine before s134: `act.guest` is absent, so P0 is RED and no guest op
    is ever sent; battle 1 still runs (s133's `act.host` tape is there). RED, exactly: every check but INI, S0, PRE,
    TAPE, INV (nothing booted, nothing to change) -- PROOF, P0, BOOT, A1-A4, M, AH, B, F, G, J, L, H, I, PAUSE, TRIP,
    TRIPST, D2, BL, D, D0, E1-E4, K, C, R not reached. COOP_CALIBRATE=1 there judges exactly that red set as S134-CAL.
  * IN-RUN, on the s134 DLL: TRIP and TRIPST are the tripwire's reds every run (judged GREEN when the counter rises).
    COOP_CALIBRATE=1 also pulls `actbench replay off` (the pre-s134 guest) BEFORE boot 1 -- every START declines `lever`
    at registration, impacts swing as before. Predicted reds, exactly: A1, A2, A3, M, AH, B, F, J, L, H, PAUSE, TRIP,
    TRIPST, D2, BL, D, E1, E2, E3, E4, C (nothing replays: J / BL / H decline `lever` first -- the order
    test_the_decide_twins_order_is_the_engines_if_chain_pair_by_pair pins); GREEN: INI, S0, P0, PROOF, PRE, TAPE, BOOT,
    A4, G, I (knob is ahead of the lever), D0, K (scene 306: no AttackOnDeath, no grace either way), INV, R. S134-CAL
    judges that set (the run is red by design).
  * THE STAND-IN (tools/harness/fakegame.py, cap `actreplay`) models the lane's DECISIONS through battlewire.ActGuestLane
    -- not the sequencer, not this plan (its battles ignore the scene, its replays are shapes): never read S134-CAL
    offline. Its tests (ff9mapkit/tests/test_harness_netsync.py) pin the twins (ActReplaySelfTest's 30 rows evaluated off
    the stack), the verb, the keys and these tables; the engine is the calibration.

THE TAPE LEG (COOP_ACT_LEG=tape). The tape: COOP_ACT_TAPE (a path), else <main repo>/.harness-runs/coop-tapes/act-s133
(COOP_ACT_TAPE_DIR overrides): its latest.json, else its newest *.f9tape. It must carry an s133+ host's action lane on
its first battle (>= 1 START on that battle's nonce): with none -- no tape, or a pre-s133 host's -- the leg refuses
cleanly ("no s133 tape": every check "not reached" -- T2-SAVE too: the guest never ran a session -- but T2-INI, green:
"Memoria.ini was never edited"). T2-CAL: coop_cut_hold's CAL leg must have passed on
THIS tape (its sha256 sidecar). The guest config is coop_cut_hold's (Enabled 1, Role client, the bench relay and code,
FollowHost 1, SessionGraceMs 30000, ...) plus ActionReplay 1 -- 0 under COOP_CALIBRATE. The guest seats the recording
host's party (COOPPARTY, as coop_tape_record.py does: a host actor its diorama lacks would decline `actor`). The whole
tape replays (no cut); every publish is sampled until the end-leave's RETURN. Checks (S134T-*):
  I     the instrument: 'paired', 'state-mirror ARMED', 'diorama BOOT scene=M', 'diorama LIVE ... nonce N' logged.
  P0    `netsync.battle.act.guest` published on the guest during the battle (else every act check fails closed).
  B5    bit5 latched for the boot from the wire (act.guest.bit5 true, host_caps & 0x20) on a sample while booted.
  RX    starts_rx in [1, the tape's battle STARTs], ends_rx >= 1, old_host false, rx_dropped 0 on every read and read at
        least once (the transport's inbound type-6 drop counter, ABSOLUTE: the guest's transport is this run's own, so
        a nonzero first read is a boot-backlog drop, never a baseline).
  RUN   started >= 1, and at rest starts_rx == started + declined (queued 0, waiting 0).
  ACT   a unit read `acting` on some sample (the replay visible to the harness).
  PAIR  paired >= 1, hits >= 1, swing_skipped >= 1 (a player impact covered by its replay).
  DECL  every decline is stale / backlog / superseded / noop, or a START parked at the end that the end's abort-all
        dropped (`dropped`: r8 / w3 / leave) -- declined == their sum.
  END   ended + aborted (+ a teardown's discarded.running) == started, ended >= 1, faulted 0; EVERY abort an end's: by
        `act.guest.aborts`, r8 + w3 + leave == aborted (pending / host-end / cap / actor / fault 0) -- never the last
        reason alone (a mid-fight abort is not masked by the end's).
  TRIP  calc_while_booted 0 on every sample -- the tripwire never fired on the real intake.
  LOG   >= 1 'action replay: started id' line; no 'faulted in the sequencer', 'tick failed' or TRIPWIRE line; the
        'boot summary (teardown)' line names the STARTs received.
  plus coop_cut_hold's COMMON T2-TAPE, T2-CAL, T2-PEER (its config line names ' actionReplay=0' exactly when the knob
  is written 0 -- an s133 guest never prints it), T2-SAVE and T2-INI.
  CALIBRATION: on an s133 GUEST the key is absent: RED exactly P0, B5, RX, RUN, ACT, PAIR, DECL, END, TRIP, LOG (fails
  closed) -- the T2-* and I GREEN. On s134 under COOP_CALIBRATE=1 (ActionReplay=0, the config line's ' actionReplay=0'):
  RED exactly RUN, ACT, PAIR, DECL, END, LOG (every START declines `knob`). S134T-CAL judges the set the engine FOUND.

RECORDING THE s133 HOST TAPE (once, on the s133 DLL -- the deployed one at writing; Git Bash, each knob scoped to ONE
launch; the tape lands OUTSIDE coop-tapes/ itself, so coop_cut_hold's latest.json -- pinned to the s117 arc tape -- never
moves):
    COOP_TAPE_DIR="C:/gd/Dream-World-IX/.harness-runs/coop-tapes/act-s133" py tools/play.py studies/test-harness/scenarios/coop_tape_record.py
      -> <that dir>/<stamp>-host250-s131.f9tape + its latest.json (the name's stage is the GUEST ladder's: s131 for any
         s131+ host) -- REC-* all green; the tape-info.txt in the run dir names its "host action records: N START(s)"
    COOP_TAPE="<that tape>" py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py        (the CAL leg: its
         sidecar <tape>.cal.json)
    COOP_ACT_LEG=tape COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_action_replay.py
         (on s133: the predicted fails-closed reds)
  after s134 deploys: COOP_ACT_LEG=tape, then COOP_ACT_LEG=tape COOP_CALIBRATE=1 (the knob's reds only).

RUN:
    py tools/play.py studies/test-harness/scenarios/coop_action_replay.py --field 30602
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_action_replay.py --field 30602
    COOP_ACT_LEG=tape py tools/play.py studies/test-harness/scenarios/coop_action_replay.py
  PowerShell has no per-launch form: a `$env:` value PERSISTS in that shell -- clear them after each run:
    Remove-Item Env:COOP_CALIBRATE, Env:COOP_ACT_LEG, Env:COOP_ACT_TAPE, Env:COOP_TAPE_DIR -ErrorAction SilentlyContinue
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import itertools
import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import _coop_peer_bench as pb                              # noqa: E402 - the T2 two-role bench helpers

try:                                                       # play.py puts tools/ on sys.path before it loads a scenario
    from harness import battlewire as BW                   # noqa: E402
except ImportError:                                        # pragma: no cover - imported outside the driver
    sys.path.insert(0, str(cb.REPO / "tools"))
    from harness import battlewire as BW                   # noqa: E402

HarnessError = cb.HarnessError

LEG = (os.environ.get("COOP_ACT_LEG", "solo").strip().lower() or "solo")
LEGS = ("solo", "tape")
PROBE = cb.R3_PROBES[134]                  # netsync.battle.act.guest: the guest replays STARTs; absent = s133 or older
HOST_PROBE = cb.R3_PROBES[133]             # netsync.battle.act.host: the in-engine tape (battle 1)
SCENE = 306                                # BSC_EF_R004 (the s133 bench's): Fang x2 at group 4
GROUP = int(os.environ.get("COOP_ACT_GROUP", "4") or 4)
NONCE = 0x5C                               # MARKER: the bench's own nonce byte (bench frames skip only the nonce gate)
FIGURE = 4321                              # MARKER: Leg F's impact figure (exists nowhere else)
FIGHT_S = 300.0
TURN_S = 90.0
INTRO_S = 40.0
REPLAY_S = 20.0                            # a fabricated replay's end, at most
PAGE = BW.ACT_TAPE_PAGE_MAX
LOOP_TOL_MS = 1000                         # Leg M: one IDLE_CMD loop of tolerance (audit amendment 17)
PROOF = "action replay selftest:"
PROOF_OK = BW.proof_ok(BW.PROOF_REPLAY, BW.REPLAY_SELFTEST_ROWS).rstrip()
LINE = {k: getattr(BW, k).split("] ", 1)[1] for k in (
    "LOG_REPLAY_OLD_HOST", "LOG_REPLAY_STARTED", "LOG_REPLAY_DISCARD", "LOG_REPLAY_SUMMARY", "LOG_REPLAY_TRIPWIRE",
    "LOG_REPLAY_TICK_FAILED", "LOG_REPLAY_REWORK_OFF", "LOG_REPLAY_OFF", "LOG_REPLAY_LEVERS_BACK", "LOG_REPLAY_SHORT_OFF")}
NO_SHORT = BW.LOG_REPLAY_NO_SHORT.strip()
FAULTED = BW.LOG_REPLAY_FAULTED.strip()
END_WAITS = BW.LOG_REPLAY_END_WAITS.strip()
END_ABORTS = BW.ACT_END_ABORTS             # r8 / w3 / leave: the aborts an END presentation owns
#: [s134 review harness-4] the scenes whose group puts an AttackOnDeath enemy at Fang 1's wire slot: scene -> {"dying_sub":
#: its EnemyDying sub_no}. Leg K's expectation is PINNED here, never read off the engine's own verdict -- scene 306 (the
#: Fangs) is absent: no grace may arm there. Empty: the positive half is not benched yet.
DIE_ATK_SCENES: dict = {}
#: [s134 review harness-02] K's negative half: a plain enemy's death lands within this much battle time of the lethal
#: feed (the kill sets die_seq in its own frame; below ACT_DEATH_GRACE_MS, so a held death reads red, never green)
DEATH_BOUND_MS = BW.ACT_DEATH_GRACE_MS - 500
#: [s134 review harness-13] what a leg raises when a unit it reads was not published (a missing dict, a None slot): that
#: leg's checks go red with the exception, the legs after it still run
LEG_FAULTS = (TypeError, AttributeError, KeyError, ValueError, IndexError)
PHASE_MENU_OFF, PHASE_VICTORY = cb.PHASE_MENU_OFF, cb.PHASE_VICTORY
_IDS = itertools.count(1)                  # bench ids: unique per process, so unique per boot (no `duplicate`)


# ================================================================================================ the catalogs
def _solo_catalog(calibrate: bool) -> dict:
    c = {
        "S134-INI": "precondition: Memoria.ini [Netsync] Enabled reads 0 (or absent), READ-ONLY -- else NOTHING runs",
        "S134-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
        "S134-P0": f"the engine publishes `{PROBE}` (memoria-patch s134) -- else no guest op is ever sent (fails closed)",
        "S134-PROOF": f"the selftest proof block's line reads exactly '{PROOF_OK}' -- no FAIL line",
        "S134-PRE": f"precondition: battle 1 (`battle {SCENE} {GROUP}`) seats Zidane, Vivi and Garnet and 2+ enemies",
        "S134-TAPE": "battle 1's s133 tape carries Zidane's Attack START (kind 3, an impact naming it), Garnet's Potion "
                     "START and an enemy START (kind 2, num == sub), matched by wire actor",
        "S134-BOOT": "boot 1 steady with act.guest at rest: starts_rx 0, running 0, calc_while_booted 0, battle_ms counting",
        "S134-A1": "Leg A: within 15 frames of the feed, started +1 and Zidane `acting`",
        "S134-A2": "Leg A: Zidane's anim leaves its idle clip, `away` peaks above 400 then falls below 10",
        "S134-A3": "Leg A: it ends naturally -- ended +1, hits >= 1, last.state 'ended', running 0",
        "S134-A4": "Leg A: presentation only -- every hp_raw / mp, r9_refused, ach_held, the cmd_busy units unchanged; "
                   "calc 0",
        "S134-M": "Leg M: MP_IDLE_CMD / MP_SET between the launch and the hit; first_hit - launch within 1000 ms of the "
                  "taped host's START -> first impact",
        "S134-AH": "Leg A-H: a Potion START (no impact) on a DAMAGED ally (below max HP) -- its hp_raw unchanged after "
                   "the end",
        "S134-B": "Leg B: an enemy replay (kind 2) -- the enemy acting, its anim changes (the clip), the end, no flinch",
        "S134-F": "Leg F: START + an impact naming its id in one feed -- paired +1, swing_skipped +1, the replay ran",
        "S134-G": "Leg G: a 46-byte impact -- old_host true, its line once, swing_skipped +0, Zidane's mot MP_ATTACK",
        "S134-J": "Leg J: START + its END in one feed -- declined 'stale' (stale +1), started +0",
        "S134-L": "Leg L: a Change START for Vivi -- her row flipped after its hit, away < 10 at its end",
        "S134-H": "Leg H: `rework off` -> declined 'rework' (the NO SFXRework line); `rework on`",
        "S134-I": "Leg I: `knob 0` -> declined 'knob', Memoria.ini byte-identical, the role still forced; `knob ini`",
        "S134-PAUSE": "the pause leg: 4 s paused mid-replay (each press verified; running when the pause took hold "
                      "and after the unpause) -- no abort, paused_ms +3000, ended after the unpause, battle span < "
                      "wall span",
        "S134-TRIP": "the tripwire's red (every run): `shortcircuit off` + a START -> calc_while_booted rises, its lines",
        "S134-TRIPST": "the SysTrans tripwire (amendment 13): `shortcircuit off` + a SysTrans START -> the counter rises",
        "S134-D2": "Leg D2: `actbench teardown` on a running replay -- the ActDiscardAll line; 90 frames on, nothing "
                   "applied (units' HP/MP, r9, ach, calc_while_booted unchanged), the diorama still booted; then a "
                   "normal leave",
        "S134-BL": "the boot backlog: a START fed during boot 2's intro declines 'backlog'",
        "S134-D": "Leg D: a running replay, `dioleave` -> aborted +1 'leave', back on the field",
        "S134-D0": "SMOKE: `dioleave` during boot 3's swirl refused 'deferred', the boot usable (amendment 12 not benched)",
        "S134-E1": "Leg E victory: MENU_OFF while the replay runs, VICTORY only after it ended",
        "S134-E2": "the run-away hold: `endbench escape` NOT injected while a replay acts (end_held +1, its line), "
                   "injected 'flee' after",
        "S134-E3": "W3: a long summon replay + `endbench escape` -> held, aborted 'w3' at ~4000 ms of battle time, injected",
        "S134-E4": "close: a long summon replay + `endbench other 4` -> injected 'close' at once while it runs, aborted "
                   "'r8' within 4 s",
        "S134-K": "Leg K: bit5 latched; a lethal impact on Fang 1 -- scene 306 (no AttackOnDeath, PINNED): NO grace and "
                  "die_seq > 0 within 1000 ms of battle time, the mask 0 on every publish to it (a grace here is red); "
                  "a DIE_ATK_SCENES scene: the grace holds die_seq 0 "
                  "through its EnemyDying replay",
        "S134-C": "Leg C: `tape play` -- every taped START received, started == starts_rx - declined, declines noop / "
                  "stale only, running 0 in time, faulted 0, aborted 0",
        "S134-INV": "the invariants after the last leave: gil, bag, levels, exp, AP, kill counters == the pre-boot snapshot",
        "S134-R": "`reset` with the replay levers set: the 'levers back' line; RE-READ WITH THE ROLE every lever at rest",
    }
    if calibrate:
        c["S134-CAL"] = ("CALIBRATION: exactly the predicted checks are red -- on an engine without `act.guest` every check "
                         "but INI/S0/PRE/TAPE/INV; on the s134 DLL under `replay off` the LEVER set (K maybe)")
    return c


#: the checks that need `act.guest` (not reached together when the probe fails closed)
GUEST_CHECKS = ("S134-PROOF", "S134-BOOT", "S134-A1", "S134-A2", "S134-A3", "S134-A4", "S134-M", "S134-AH", "S134-B",
                "S134-F", "S134-G", "S134-J", "S134-L", "S134-H", "S134-I", "S134-PAUSE", "S134-TRIP", "S134-TRIPST",
                "S134-D2", "S134-BL", "S134-D", "S134-D0", "S134-E1", "S134-E2", "S134-E3", "S134-E4", "S134-K",
                "S134-C", "S134-R")
#: COOP_CALIBRATE=1 on an engine without `act.guest` (the deployed s133, or older): all but INI, S0, PRE, TAPE, INV.
OLD_PREDICTED = tuple(c for c in _solo_catalog(True) if c not in ("S134-INI", "S134-S0", "S134-PRE", "S134-TAPE",
                                                                    "S134-INV", "S134-CAL"))
#: COOP_CALIBRATE=1 on the s134 DLL: `replay off` before boot 1 -- nothing replays.
LEVER_PREDICTED = ("S134-A1", "S134-A2", "S134-A3", "S134-M", "S134-AH", "S134-B", "S134-F", "S134-J", "S134-L",
                   "S134-H", "S134-PAUSE", "S134-TRIP", "S134-TRIPST", "S134-D2", "S134-BL", "S134-D", "S134-E1",
                   "S134-E2", "S134-E3", "S134-E4", "S134-C")
#: (K is no maybe since the review pass: its expectation is pinned per scene, and on scene 306 no grace arms with or
#: without the lever)
LEVER_MAYBE: tuple = ()

TAPE_COMMON = {
    "T2-TAPE": "the act tape reads back and carries an s133+ host's action lane on its first battle (>= 1 START on its "
               "nonce) -- else 'no s133 tape'",
    "T2-CAL": "coop_cut_hold's CAL leg passed on THIS tape (<tape>.cal.json, sha256-keyed) -- the instrument is trusted",
    "T2-PEER": "the port free; the guest config applied live (its config line: role=client, the bench code, actionReplay "
               "as written); the guest dialled the replay-host and the replay started",
    "T2-SAVE": "the guest had its OWN autosave to end a session on (no 'no autosave to resume -> title screen' line)",
    "T2-INI": "Memoria.ini restored byte-exact (sha256) after the run -- the install is shared",
}
TAPE_CHECKS = {
    "S134T-I": "the instrument: 'paired', 'state-mirror ARMED', 'diorama BOOT scene=M', 'diorama LIVE ... nonce N' logged",
    "S134T-P0": f"`{PROBE}` published on the guest during the battle (else every act check fails closed)",
    "S134T-B5": "bit5 latched for the boot from the wire: act.guest.bit5 true, host_caps & 0x20, on a booted sample",
    "S134T-RX": "starts_rx in [1, the tape's battle STARTs], ends_rx >= 1, old_host false, rx_dropped read and 0 "
                "(absolute)",
    "S134T-RUN": "started >= 1; at rest starts_rx == started + declined (queued 0, waiting 0)",
    "S134T-ACT": "a unit read `acting` on some sample",
    "S134T-PAIR": "paired >= 1, hits >= 1, swing_skipped >= 1",
    "S134T-DECL": "every decline is stale / backlog / superseded / noop / an end's drop (declined == their sum)",
    "S134T-END": "ended + aborted (+ discarded.running) == started, ended >= 1, faulted 0; EVERY abort an end's "
                 "(act.guest.aborts: r8 + w3 + leave == aborted)",
    "S134T-TRIP": "calc_while_booted 0 on every sample (the tripwire never fired on the real intake)",
    "S134T-LOG": "a 'started id' line; no 'faulted in the sequencer' / 'tick failed' / TRIPWIRE line; the 'boot summary "
                 "(teardown)' line names the STARTs received",
}
TAPE_ACT = ("S134T-P0", "S134T-B5", "S134T-RX", "S134T-RUN", "S134T-ACT", "S134T-PAIR", "S134T-DECL", "S134T-END",
            "S134T-TRIP", "S134T-LOG")
#: the tape leg on an s133 GUEST (no `act.guest`): every act check fails closed
TAPE_OLD_PREDICTED = TAPE_ACT
#: the tape leg on s134 under COOP_CALIBRATE=1 (ActionReplay=0 written): every START declines `knob`
TAPE_KNOB_PREDICTED = ("S134T-RUN", "S134T-ACT", "S134T-PAIR", "S134T-DECL", "S134T-END", "S134T-LOG")


def _tape_catalog(calibrate: bool) -> dict:
    cat = {"T2-TAPE": TAPE_COMMON["T2-TAPE"], "T2-CAL": TAPE_COMMON["T2-CAL"], "T2-PEER": TAPE_COMMON["T2-PEER"]}
    cat.update(TAPE_CHECKS)
    if calibrate:
        cat["S134T-CAL"] = ("CALIBRATION: exactly the predicted checks are red for the engine found -- s133: every act "
                            "check; s134 under ActionReplay=0: RUN, ACT, PAIR, DECL, END, LOG")
    cat["T2-SAVE"] = TAPE_COMMON["T2-SAVE"]
    cat["T2-INI"] = TAPE_COMMON["T2-INI"]
    return cat


def _catalog(calibrate: bool, leg: str = "solo") -> dict:
    return _tape_catalog(calibrate) if leg == "tape" else _solo_catalog(calibrate)


def _tape_predicted(has_guest: bool) -> tuple:
    """The tape leg's predicted reds for the engine FOUND (its `act.guest` key) under COOP_CALIBRATE=1."""
    return TAPE_KNOB_PREDICTED if has_guest else TAPE_OLD_PREDICTED


# ================================================================================================ reads
def _num(v) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _sub(d, key: str) -> dict:
    v = d.get(key) if isinstance(d, dict) else None
    return v if isinstance(v, dict) else {}


def _guest(x) -> dict:
    return _sub(_sub(cb.nsb(x), "act"), "guest")


def _host(x) -> dict:
    return _sub(_sub(cb.nsb(x), "act"), "host")


def _gv(x, key: str) -> int:
    return _num(_guest(x).get(key)) or 0


def _brief(x) -> str:
    return "act.guest=" + str(cb.pick(_guest(x), "on", "starts_rx", "started", "running", "declined", "declined_why",
                                      "ended", "aborted", "abort_why", "hits", "paired", "swing_skipped",
                                      "calc_while_booted", "battle_ms"))


def _unit(x, slot: int | None) -> dict:
    return (cb.unit(x, slot) or {}) if slot is not None else {}


def _wire_of(x, unit: dict | None) -> int | None:
    """A unit's WIRE index: a player's compacted party index (its rank among the seated players by btl slot), an enemy's
    btl slot (NetSyncDiorama.ResolveWireUnit's inverse)."""
    if not unit:
        return None
    if unit.get("player"):
        slots = cb.player_slots(x)
        return slots.index(int(unit["slot"])) if int(unit["slot"]) in slots else None
    return int(unit["slot"])


NAMES = {"zidane": ("zidane",), "vivi": ("vivi",), "garnet": ("garnet", "dagger")}


def _unit_named(x, name: str) -> dict | None:
    want = NAMES.get(name, (name,))
    return next((u for u in cb.units(x, player=True) if str(u.get("name") or "").strip().lower() in want), None)


def _invariants(x) -> dict:
    """What a presentation-only replay must never change, read off one publish: every unit's (hp_raw, mp, cmd_busy), the
    R9 counter and the held battle achievements."""
    return {"units": {int(u.get("slot", -1)): (u.get("hp_raw"), u.get("mp")) for u in cb.units(x)},
            "busy": [u.get("cmd_busy") for u in cb.units(x) if u.get("cmd_busy")],
            "r9": cb.bmenu(x).get("r9_refused"), "ach": cb.bend(x).get("ach_held")}


# ================================================================================================ frames
def _start(actor: int, *, player: bool, cmd: int, sub: int, tar: int, kind: int, num: int, speed: int = 5,
           cursor: int = 0) -> tuple:
    """A fresh bench START (s133's 76-byte record, the bench nonce) -> (id, bytes)."""
    act_id = next(_IDS)
    flags = (BW.ACTOR_IS_PLAYER if player else 0) | BW.ACTOR_HOST_REWORK | (BW.ACTOR_HOST_FAST if speed >= 3 else 0)
    return act_id, BW.encode_action_start(NONCE, 1, act_id, actor, flags, cmd, sub, tar, cursor, 0, 0, kind, num, -1, speed)


def _end(act_id: int, cmd: int, sub: int) -> bytes:
    return BW.encode_action_end(NONCE, 2, act_id, cmd, sub)


def _impact(caster: int, target: int, *, fig_hp: int, tgt_raw: tuple, cast_raw: tuple, player_caster: bool,
            player_target: bool, cmd: int, sub: int, act_id: int | None) -> bytes:
    flags = 1 | (32 if player_target else 0) | (64 if player_caster else 0)
    return BW.encode_action_impact(NONCE, 3, caster, target, fig_t=(0, fig_hp, 0),
                                   raws=(tgt_raw[0], tgt_raw[1], cast_raw[0], cast_raw[1]), flags=flags, cmd_no=cmd,
                                   sub_no=sub, act_id=act_id)


# ================================================================================================ acting
def _act_verb(g, *args) -> tuple:
    """`netsync actbench <args>` -- (the state after it or None, why-not). The caller probes `act.guest` first."""
    try:
        return cb.ns_verb(g, "actbench", *args), ""
    except (HarnessError, AttributeError) as err:
        return None, str(err)[:400]


def _feed(g, frames, at_ms: int | None = None) -> tuple:
    frames = [frames] if isinstance(frames, (bytes, bytearray)) else list(frames)
    arg = BW.act_feed_arg(frames)
    return _act_verb(g, "feed", arg) if at_ms is None else _act_verb(g, "feedat", int(at_ms), arg)


def _ctx_new() -> dict:
    return {"probe": False, "ini_ok": False, "tape": {}, "slots": {}, "fp0": None, "levers_set": False}


def _replay(g, frames, until, timeout: float = REPLAY_S) -> tuple:
    """Feed ``frames`` (one drain) and read every publish until ``until(state)``: (samples, the state that ended it or
    None, why-not)."""
    st, why = _feed(g, frames)
    if st is None:
        return [], None, f"the feed was refused: {why}"
    samples, end = cb.watch(g, until, timeout)
    return samples, end, ""


# ================================================================================================ the run
def run(g, field: int = cb.FIELD):
    if LEG not in LEGS:
        led = cb.Ledger(g, {"S134-LEG": f"COOP_ACT_LEG is one of {LEGS}"})
        led.check("S134-LEG", False, f"COOP_ACT_LEG={LEG!r} is no leg: one of {LEGS}")
        return
    if LEG == "tape":
        _run_tape(g)
        return
    calibrate = cb.CALIBRATE
    led = cb.Ledger(g, _solo_catalog(calibrate), finals=("S134-R", "S134-INV", "S134-CAL"))
    ctx = _ctx_new()
    try:
        _run(g, led, field, calibrate, ctx)
    except HarnessError as err:
        g.note(f"the run raised: {str(err)[:400]}")
        led.close(f"not reached: the run raised ({str(err)[:200]})")
    finally:
        g.note(f"logs archived: {_archive_logs(g, 'action-replay')}")
        led.close()
        if ctx["ini_ok"]:
            _release(g, led, ctx)
        else:
            led.unreached(("S134-R", "S134-INV"), "the precondition refused the run (S134-INI): nothing was set")
        if calibrate:
            led.judge_calibration("S134-CAL", LEVER_PREDICTED if ctx["probe"] else OLD_PREDICTED,
                                  LEVER_MAYBE if ctx["probe"] else ())
        led.close(final=True)


def _archive_logs(g, tag: str) -> str:
    """BOTH logs into the run's artifact dir NOW (design 6.1): Memoria.log and Unity's output_log.txt."""
    out = [cb.archive_log(g, tag)]
    try:
        src = g.unity_log()
        dest_dir = getattr(g, "scenario_dir", None) or g.run_dir
        if src is not None and dest_dir is not None:
            dest = Path(dest_dir) / f"output_log-{tag}.txt"
            shutil.copy2(src, dest)
            out.append(str(dest))
    except (OSError, AttributeError) as err:
        out.append(f"output_log archive failed: {err}")
    return "; ".join(out)


def _ini_guard(g) -> tuple:
    raw = cb.ini_value(g, "Netsync", "Enabled")
    role = cb.ini_value(g, "Netsync", "Role")
    if raw is not None and raw.strip() == "1":
        return False, (f"Memoria.ini [Netsync] Enabled = 1 (Role = {role!r}): the selftest role is refused on a live-"
                       f"configured install -- set Enabled = 0 BY HAND (this bench never writes Memoria.ini) and relaunch")
    return True, f"[Netsync] Enabled = {raw!r}" if raw is not None else "[Netsync] Enabled absent (the default 0)"


def _ini_sha(g) -> str | None:
    try:
        return hashlib.sha256((Path(g.game_path) / "Memoria.ini").read_bytes()).hexdigest()
    except (OSError, AttributeError, TypeError):
        return None


def _run(g, led: cb.Ledger, field: int, calibrate: bool, ctx: dict) -> None:
    ok, why = _ini_guard(g)
    led.check("S134-INI", ok, why)
    if not ok:
        led.close(f"refused to run: {why}")
        return
    ctx["ini_ok"] = True
    ok, why = cb.setup(g, field, label=f"R3 s134: the guest action replay, solo (scene {SCENE} group {GROUP})"
                                       + (" -- CALIBRATION (actbench replay off)" if calibrate else ""))
    led.check("S134-S0", ok, why)
    if not ok:
        led.close(f"the selftest role was refused -- {why}")
        return
    st = g.state
    have = ctx["probe"] = cb.has(st, PROBE)
    led.check("S134-P0", have, f"act.guest keys: {sorted(_guest(st))}" if have else
              f"no `{PROBE}` (an engine before s134: no guest op will be sent)")
    g.note(f"probe stage: {cb.stage_note(st)}; act.guest {'present' if have else 'ABSENT'}; act.host "
           f"{'present' if cb.has(st, HOST_PROBE) else 'ABSENT'}")
    _leg_proof(g, led)
    try:
        g.state_every(1)
    except (HarnessError, AttributeError) as err:
        g.note(f"stateevery 1 refused ({str(err)[:120]})")
    _battle_1(g, led, field, ctx)
    fp, fwhy = cb.fingerprint(g, field=field)
    ctx["fp0"] = fp
    g.note(f"the invariants before boot 1: {'read' if fp else 'UNREADABLE: ' + fwhy}")
    if not have:
        led.unreached([c for c in GUEST_CHECKS if c not in ("S134-R",)],
                      f"`{PROBE}` is absent: an engine before s134 (the probe fails closed; no guest op was sent)")
        return
    if calibrate:
        _act_verb(g, "replay", "off")
        ctx["levers_set"] = True
        g.note("CALIBRATION: `actbench replay off` -- the pre-s134 guest for every leg below")
    _boot_1(g, led, field, ctx)
    _boot_2(g, led, field, ctx)
    _boot_3(g, led, field, ctx)
    _boot_e(g, led, field, ctx, "E2")
    _boot_e(g, led, field, ctx, "E3")
    _boot_e(g, led, field, ctx, "E4")
    _boot_k(g, led, field, ctx)
    _boot_c(g, led, field, ctx)
    if calibrate:
        _act_verb(g, "replay", "on")


def _leg_proof(g, led: cb.Ledger) -> None:
    proof = cb.poll(g, lambda s: cb.count(cb.log_lines(g), PROOF) >= 1, 8.0, "the proof block's action-replay line")
    lines = [ln for ln in cb.log_lines(g) if PROOF in ln]
    last = lines[-1] if lines else ""
    failed = [ln for ln in lines if "action replay selftest: FAIL" in ln]
    led.check("S134-PROOF", proof is not None and PROOF_OK in last and not failed,
              (last.split("|", 2)[-1].strip()[-300:] if last else "no 'action replay selftest' line (an engine before "
                                                                  "s134 has no ActReplaySelfTest)")
              + (f"; FAIL lines: {len(failed)}" if failed else "") + f"; want '{PROOF_OK}'")


# ------------------------------------------------------------------------------------------------ battle 1 (the tape)
def _sturdiest_ally(x, but: int) -> int | None:
    allies = [u for u in cb.units(x, player=True) if u.get("alive") and int(u.get("slot", -1)) != but]
    return int(max(allies, key=lambda u: int(u.get("hp") or 0))["slot"]) if allies else None


def _battle_1(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    """`actbench tape rec` + `battle 306 <group>` with a plan that cannot end the fight early: Zidane Attacks the
    sturdiest ally once, Garnet Potions herself, every other prompt Defends until both are done and two more prompts have
    passed (the Fangs act between them), then `fight` to the victory; the tape paged out and read offline."""
    host = cb.has(g.state, HOST_PROBE)
    if host:
        _act_verb(g, "tape", "rec")
    if cb.poll(g, lambda s: cb.free(s) and s.ui_state == "FieldHUD" and not s.in_battle, 30.0, "a playable field") is None:
        led.unreached(("S134-PRE", "S134-TAPE"), f"not on a playable field before battle 1 (ui {g.state.ui_state!r})")
        return
    try:
        st = g.start_battle(SCENE, group=GROUP)
    except HarnessError as err:
        led.unreached(("S134-PRE", "S134-TAPE"), f"`battle {SCENE} {GROUP}` did not start: {str(err)[:200]}")
        return
    _samples, en = cb.watch(g, lambda s: s.commands_enabled, INTRO_S)
    st = en or g.state
    names = {k: _unit_named(st, k) for k in ("zidane", "vivi", "garnet")}
    foes = cb.units(st, player=False)
    led.check("S134-PRE", all(names.values()) and len(foes) >= 2,
              f"party {[(u.get('slot'), u.get('name')) for u in cb.units(st, player=True)]}; enemies "
              f"{[(u.get('slot'), u.get('name'), u.get('id')) for u in foes]}")
    ctx["slots"] = {k: (int(u["slot"]) if u else None) for k, u in names.items()}
    ctx["zidane_wire"] = _wire_of(st, names["zidane"])
    ctx["garnet_wire"] = _wire_of(st, names["garnet"])
    ctx["fang1_wire"] = _who(st)["fang1"][1]
    done, extra = {"attack": False, "potion": False}, 0
    z, gar = ctx["slots"].get("zidane"), ctx["slots"].get("garnet")
    for _turn in range(40):
        if done["attack"] and done["potion"] and extra >= 2:
            break
        try:
            slot = g.wait_turn(timeout=TURN_S)
        except HarnessError as err:
            g.note(f"battle 1 stopped asking: {str(err)[:160]}")
            break
        s = g.state
        try:
            if slot == z and not done["attack"]:
                ally = _sturdiest_ally(s, slot)
                sent = g.act("Attack", slot=slot, target=ally if ally is not None else slot)
                done["attack"] = True
                ctx["attack_sent"] = (int(sent["id"]), int(sent["sub"]))
            elif slot == gar and not done["potion"]:
                sent = g.act("Potion", slot=slot, target=slot)
                done["potion"] = True
                ctx["potion_sent"] = (int(sent["id"]), int(sent["sub"]))
            else:
                g.act("Defend", slot=slot)
                if done["attack"] and done["potion"]:
                    extra += 1
        except HarnessError as err:
            if not g.state.in_battle:
                break
            g.note(f"plan step refused on slot {slot}: {str(err)[:200]}")
    ctx["plan"] = dict(done, extra=extra)
    try:
        if g.state.in_battle:
            g.fight(timeout=FIGHT_S, finish=False)
    except HarnessError as err:
        g.note(f"battle 1's fight did not finish: {str(err)[:200]}")
    _finish(g)
    if not host:
        led.check("S134-TAPE", False, f"no `{HOST_PROBE}`: an engine before s133 records no action tape")
        return
    _act_verb(g, "tape", "stop")
    t = _sub(_host(cb.poll(g, lambda s: _sub(_host(s), "tape").get("state") == "stopped", 3.0, "the tape stopped")
                   or g.state), "tape")
    frames, why = _dump_all(g, _num(t.get("frames")) or 0)
    ctx["tape"] = _read_tape(frames, ctx)
    tp = ctx["tape"]
    led.check("S134-TAPE", not why and tp.get("attack") is not None and tp["attack"].get("hit_ms") is not None
              and tp.get("potion") is not None and tp.get("enemy") is not None,
              why or f"{len(frames)} frame(s); Zidane's Attack START {tp.get('attack')}; Garnet's Potion START "
                     f"{tp.get('potion')}; an enemy START {tp.get('enemy')}; the plan {ctx.get('plan')}")


def _finish(g) -> None:
    for _ in range(40):
        st = g.state
        if not st.in_battle and st.ui_state not in ("BattleHUD", "BattleResult"):
            break
        g.press("confirm", 4)
        g.wait_frames(20)
    cb.poll(g, lambda s: s.on_field and s.ui_state == "FieldHUD", 30.0, "the field after the battle")


def _dump_all(g, total: int) -> tuple:
    """The whole host tape, paged out (`tape dump <i> 16`): ([(i, ms, bytes)], why-not)."""
    frames = []
    while len(frames) < total:
        start = len(frames)
        st, why = _act_verb(g, "tape", "dump", start, PAGE)
        if st is None:
            return frames, f"`tape dump {start} {PAGE}` refused: {why}"
        hit = cb.poll(g, lambda s: _num(_sub(_sub(_host(s), "tape"), "page").get("from")) == start, 5.0,
                      f"the tape page from {start}")
        got = BW.act_tape_page_frames(_sub(_sub(_host(hit), "tape"), "page")) if hit is not None else []
        if not got:
            return frames, f"the page from {start} never landed"
        frames.extend(got)
    return frames, ""


def _read_tape(frames: list, ctx: dict) -> dict:
    """The taped facts the fabricated legs replay: Zidane's Attack START (num, the host's Speed, START -> first impact ms),
    Garnet's Potion START (num), an enemy START (actor, sub, num) -- by the WIRE actors (a START's actor is the host's wire
    index: a player's compacted party rank, never a btl slot -- [s134 review harness-10]) and the cmd/sub the plan sent.
    Leg M's yardstick is taken off a Zidane Attack on an ENEMY (a target bit 4-7: the run-out Leg A replays) when the tape
    has one, else off the first -- `on_enemy` says which ([s134 review harness-7]); the num stays the first START's."""
    out = {"frames": len(frames), "attack": None, "potion": None, "enemy": None}
    decoded = [(ms, BW.decode_action(b)) for _i, ms, b in frames]
    starts = [(ms, d) for ms, d in decoded if BW.classify_action(d) == "start"]
    zw, gw = ctx.get("zidane_wire"), ctx.get("garnet_wire")
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    pcmd, psub = ctx.get("potion_sent") or (BW.CMD_ITEM_ID, BW.ITEM_POTION_ID)

    def player(d) -> bool:
        return bool(d["actor_flags"] & BW.ACTOR_IS_PLAYER)

    def hit_of(ms, d):
        hit = next((ms2 for ms2, e in decoded if BW.classify_action(e) == "impact" and e["has_ext"]
                    and e["act_id"] == d["act_id"] and e["nonce"] == d["nonce"]), None)
        return (hit - ms) if hit is not None else None
    attacks = [(ms, d) for ms, d in starts if player(d) and zw is not None and d["actor_slot"] == zw
               and d["act_cmd_no"] == acmd and d["act_sub_no"] == asub and d["vfx_kind"] == BW.VFX_KIND_SPECIAL]
    if attacks:
        foe = next(((ms, d) for ms, d in attacks if d["act_tar_id"] & 0xF0), None)
        ms1, d1 = foe or attacks[0]
        out["attack"] = {"num": attacks[0][1]["vfx_num"], "hit_ms": hit_of(ms1, d1), "speed": d1.get("host_speed"),
                         "on_enemy": foe is not None}
    for ms, d in starts:
        if (out["potion"] is None and player(d) and gw is not None and d["actor_slot"] == gw and d["act_cmd_no"] == pcmd
                and d["act_sub_no"] == psub):
            out["potion"] = {"num": d["vfx_num"], "kind": d["vfx_kind"]}
        elif (out["enemy"] is None and not player(d) and d["vfx_kind"] == BW.VFX_KIND_ENEMY
              and d["vfx_num"] == d["act_sub_no"]):
            out["enemy"] = {"actor": d["actor_slot"], "cmd": d["act_cmd_no"], "sub": d["act_sub_no"]}
    return out


# ------------------------------------------------------------------------------------------------ boots
def _boot(g, field: int) -> tuple:
    """`endbench clear`, `dioboot <scene> <group>`, the steady phase AND the steady latch (normal_ms >= 0: a START drained
    before it declines `backlog`). (state or None, why)."""
    cb.try_ns(g, "endbench", "clear")
    ok, why = cb.boot(g, SCENE, GROUP)
    if not ok:
        cb.back_to_field(g, field)
        return None, why
    st = cb.poll(g, lambda s: cb.steady(s) and (_num(cb.path(s, "netsync.diorama.intro.normal_ms")) or -1) >= 0,
                 cb.STEADY_S, "the steady phase and its latch")
    if st is None:
        cb.leave(g, field)
        return None, "the diorama never reached its steady latch"
    g.wait_frames(5)
    return g.state, ""


def _out(g, field: int) -> None:
    if cb.dio(g.state).get("booted"):
        cb.leave(g, field)
    else:
        cb.arrive(g, field)
    cb.try_ns(g, "endbench", "clear")


def _who(x) -> dict:
    """The diorama's cast by WIRE index: zidane / vivi / garnet (players), fang1 / fang2 (the first two enemies)."""
    out = {}
    for name in ("zidane", "vivi", "garnet"):
        u = _unit_named(x, name)
        out[name] = (u, _wire_of(x, u))
    foes = sorted(cb.units(x, player=False), key=lambda u: int(u.get("slot", 99)))
    for k, name in enumerate(("fang1", "fang2")):
        u = foes[k] if len(foes) > k else None
        out[name] = (u, _wire_of(x, u))
    return out


def _bit(wire: int | None) -> int:
    return (1 << wire) if wire is not None else 0


def _leg_a_start(x, ctx: dict, *, speed: int | None = None) -> tuple:
    """Leg A's START: Zidane's Attack on Fang 1, kind 3, the TAPED num at the TAPED host Speed (the camera path the host
    taped -- UseCamera / PlayCamera follow a replay's host Speed; 5 when the tape named none: [s134 review timing-07]) --
    the wires read off this diorama, else (a START fed before its units are published: the boot backlog) battle 1's, the
    same scene and group. (id, bytes) or (None, why)."""
    who = _who(x)
    (zu, zw), (fu, fw) = who["zidane"], who["fang1"]
    zw = zw if zw is not None else ctx.get("zidane_wire")
    fw = fw if fw is not None else ctx.get("fang1_wire")
    att = (ctx.get("tape") or {}).get("attack")
    if zw is None or fw is None or att is None:
        return None, f"no Zidane / Fang 1 here, or no taped Attack num (zidane {zw}, fang {fw}, taped {att})"
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    if speed is None:
        speed = att.get("speed") if isinstance(att.get("speed"), int) else 5
    return _start(zw, player=True, cmd=acmd, sub=asub, tar=_bit(fw), kind=BW.VFX_KIND_SPECIAL, num=att["num"],
                  speed=speed)


def _ended(base: dict):
    """until: the guest's `ended` or `aborted` rose past ``base`` and nothing runs -- or the START was DECLINED (a lever,
    the calibration: the leg reads red at once instead of waiting out REPLAY_S)."""
    return lambda s: ((_gv(s, "ended") > base.get("ended", 0) or _gv(s, "aborted") > base.get("aborted", 0))
                      and _gv(s, "running") == 0) or _gv(s, "declined") > base.get("declined", 0)


def _base(x) -> dict:
    return {k: _gv(x, k) for k in ("started", "ended", "aborted", "declined", "stale", "backlog", "hits", "paired",
                                    "swing_skipped", "calc_while_booted", "paused_ms", "end_held", "noop", "starts_rx")}


# ---- boot 1
def _boot_1(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    legs = ("S134-BOOT", "S134-A1", "S134-A2", "S134-A3", "S134-A4", "S134-M", "S134-AH", "S134-B", "S134-F", "S134-G",
            "S134-J", "S134-L", "S134-H", "S134-I", "S134-PAUSE", "S134-TRIP", "S134-TRIPST", "S134-D2")
    st, why = _boot(g, field)
    if st is None:
        led.unreached(legs, f"boot 1 failed: {why}")
        return
    gs = _guest(st)
    b0 = _gv(st, "battle_ms")
    g.wait_frames(15)
    led.check("S134-BOOT", _num(gs.get("starts_rx")) == 0 and _num(gs.get("running")) == 0
              and _num(gs.get("calc_while_booted")) == 0 and _gv(g.state, "battle_ms") > b0,
              f"{_brief(st)}; battle_ms {b0} -> {_gv(g.state, 'battle_ms')}")
    try:
        for ids, leg in ((("S134-A1", "S134-A2", "S134-A3", "S134-A4", "S134-M"), _legs_a), (("S134-AH",), _leg_ah),
                         (("S134-B",), _leg_b), (("S134-F",), _leg_f), (("S134-G",), _leg_g), (("S134-J",), _leg_j),
                         (("S134-L",), _leg_l), (("S134-H",), _leg_h), (("S134-I",), _leg_i),
                         (("S134-PAUSE",), _leg_pause), (("S134-TRIP",), _leg_trip), (("S134-TRIPST",), _leg_tripst),
                         (("S134-D2",), _leg_d2)):
            _guard(led, ids, leg, g, led, ctx)
    finally:
        led.unreached(legs, "boot 1 ended before this leg")
        _out(g, field)


def _guard(led: cb.Ledger, ids, leg, *args) -> None:
    """[s134 review harness-13] One leg, its faults contained: a unit it dereferences that was not published (a None
    slot, a missing dict) turns ITS checks red with the exception -- never the whole scenario."""
    try:
        leg(*args)
    except LEG_FAULTS as err:
        _faulted(led, ids, err)


def _faulted(led: cb.Ledger, ids, err) -> None:
    for cid in ids:
        if cid not in led.done:
            led.check(cid, False, f"the leg faulted ({type(err).__name__}: {str(err)[:200]}) -- a unit it reads was not "
                                  "published")


def _legs_a(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    inv0, base = _invariants(st), _base(st)
    act_id, frame = _leg_a_start(st, ctx)
    if act_id is None:
        led.unreached(("S134-A1", "S134-A2", "S134-A3", "S134-A4", "S134-M"), frame)
        return
    zw_slot = _who(st)["zidane"][0]["slot"]
    idle = _unit(st, zw_slot).get("anim")
    f0 = cb.frame_of(st)
    samples, end, why = _replay(g, frame, _ended(base))
    acting = [s for s in samples if _unit(s, zw_slot).get("acting") is True and _gv(s, "started") > base["started"]]
    first = acting[0] if acting else None
    led.check("S134-A1", first is not None and cb.frame_of(first) - f0 <= 15 + 6,
              why or f"first acting frame {cb.frame_of(first) if first else None} (fed at {f0}); {_brief(end or g.state)}")
    anims = [_unit(s, zw_slot).get("anim") for s in acting]
    aways = [float(_unit(s, zw_slot).get("away") or 0.0) for s in samples]
    peak = max(aways) if aways else 0.0
    tail = aways[aways.index(peak):] if aways else []
    led.check("S134-A2", any(a and a != idle for a in anims) and peak > 400 and bool(tail) and min(tail) < 10,
              f"idle {idle!r}; anims {sorted({a for a in anims if a})[:5]}; away peak {peak:.0f}, after it min "
              f"{(min(tail) if tail else None)}")
    last = _guest(end or g.state).get("last") or {}
    led.check("S134-A3", end is not None and _gv(end, "ended") == base["ended"] + 1 and _gv(end, "hits") > base["hits"]
              and last.get("state") == "ended" and _gv(end, "running") == 0,
              f"{_brief(end or g.state)}; last {cb.pick(last, 'id', 'state', 'hits', 'launch_ms', 'first_hit_ms', 'end_ms')}")
    inv1 = _invariants(end or g.state)
    led.check("S134-A4", inv1 == inv0 and _gv(end or g.state, "calc_while_booted") == base["calc_while_booted"] == 0,
              f"before {inv0}; after {inv1}; calc {_gv(end or g.state, 'calc_while_booted')}")
    # Leg M: the stance, and the host's timing
    mots = [_unit(s, zw_slot).get("mot") for s in acting if (_num((_guest(s).get("last") or {}).get("first_hit_ms")) or -1) < 0]
    stance = any(m in (BW.MP_IDLE_CMD, BW.MP_SET) for m in mots)
    host_ms = ((ctx.get("tape") or {}).get("attack") or {}).get("hit_ms")
    mine = (last.get("first_hit_ms") - last.get("launch_ms")) if _num(last.get("first_hit_ms")) is not None and \
        _num(last.get("launch_ms")) is not None and last.get("first_hit_ms") >= 0 else None
    att = (ctx.get("tape") or {}).get("attack") or {}
    on = "on an ENEMY" if att.get("on_enemy") else "on an ALLY: the run-out differs"
    led.check("S134-M", stance and host_ms is not None and mine is not None and abs(mine - host_ms) <= LOOP_TOL_MS,
              f"mots before the hit {mots[:12]}; the guest's launch -> hit {mine} ms vs the taped host's START -> impact "
              f"{host_ms} ms (tolerance {LOOP_TOL_MS}; the taped Attack {on}, host speed {att.get('speed')})")


def _damaged(u: dict | None) -> bool:
    return u is not None and int(u.get("hp_raw") or 0) < int(u.get("hp_max_raw") or 0)


def _leg_ah(g, led: cb.Ledger, ctx: dict) -> None:
    """[s134 review harness-3] AH proves nothing on a full ally (a fall-through heal would leave hp_raw at its cap): the
    leg needs an ally BELOW its max. With none, the precondition is made explicit -- one id-tagged impact (an id no START
    names: the legacy route, no old-host note) from Fang 1 lowers that ally's raw HP by 100 -- and with still none, AH
    reads "not reached: no damaged ally"."""
    st = g.state
    who = _who(st)
    (gu, gw) = who["garnet"]
    pot = (ctx.get("tape") or {}).get("potion")
    allies = [u for u in cb.units(st, player=True) if u.get("alive")]
    hurt = min(allies, key=lambda u: (int(u.get("hp_raw") or 0) - int(u.get("hp_max_raw") or 0)), default=None)
    if gw is None or pot is None or hurt is None:
        led.check("S134-AH", False, f"not reached: no Garnet ({gw}), no taped Potion ({pot}) or no ally")
        return
    made = ""
    if not _damaged(hurt):
        fu, fw = who["fang1"]
        hw = _wire_of(st, hurt)
        en = (ctx.get("tape") or {}).get("enemy") or {}
        if fu is not None and fw is not None and hw is not None:
            low = max(1, int(hurt.get("hp_max_raw") or 0) - 100)
            hit = _impact(fw, hw, fig_hp=100, tgt_raw=(low, hurt.get("mp") or 0),
                          cast_raw=(fu.get("hp_raw") or 0, fu.get("mp") or 0), player_caster=False, player_target=True,
                          cmd=en.get("cmd", BW.CMD_ATTACK_ID), sub=en.get("sub", BW.ABILITY_ATTACK_ID), act_id=next(_IDS))
            _feed(g, hit)
            hit_st = cb.poll(g, lambda s: _damaged(_unit(s, int(hurt["slot"]))), 3.0, "the ally damaged")
            g.wait_frames(20)                                          # (the flinch plays out)
            st = g.state
            hurt = _unit(st, int(hurt["slot"])) or hurt
            made = f"; damaged first by a bench impact ({'landed' if hit_st is not None else 'NEVER landed'})"
    if not _damaged(hurt):
        led.check("S134-AH", False, f"not reached: no damaged ally (ally slot {hurt.get('slot')} hp_raw "
                                    f"{hurt.get('hp_raw')} of {hurt.get('hp_max_raw')}{made})")
        return
    base = _base(st)
    pcmd, psub = ctx.get("potion_sent") or (BW.CMD_ITEM_ID, BW.ITEM_POTION_ID)
    _id, frame = _start(gw, player=True, cmd=pcmd, sub=psub, tar=_bit(_wire_of(st, hurt)), kind=pot.get("kind", 3),
                        num=pot["num"])
    hp0 = hurt.get("hp_raw")
    samples, end, why = _replay(g, frame, _ended(base))
    hp1 = _unit(end or g.state, int(hurt["slot"])).get("hp_raw")
    led.check("S134-AH", end is not None and _gv(end, "ended") == base["ended"] + 1 and hp1 == hp0,
              why or f"ally slot {hurt['slot']} hp_raw {hp0} -> {hp1} (hp_max_raw {hurt.get('hp_max_raw')}{made}); "
                     f"{_brief(end or g.state)}")


def _leg_b(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    who = _who(st)
    en = (ctx.get("tape") or {}).get("enemy")
    zu, zw = who["zidane"]
    foe = cb.unit(st, en["actor"]) if en else None
    if en is None or foe is None or zw is None:
        led.check("S134-B", False, f"not reached: taped enemy START {en}, its unit here {foe is not None}")
        return
    base = _base(st)
    anim0 = foe.get("anim")
    _id, frame = _start(int(foe["slot"]), player=False, cmd=en["cmd"], sub=en["sub"], tar=_bit(zw),
                        kind=BW.VFX_KIND_ENEMY, num=en["sub"])
    samples, end, why = _replay(g, frame, _ended(base))
    acting = [s for s in samples if _unit(s, int(foe["slot"])).get("acting") is True]
    anims = {_unit(s, int(foe["slot"])).get("anim") for s in acting}
    flinch = [cb.frame_of(s) for s in samples if _unit(s, int(zu["slot"])).get("mot") in (BW.MP_DAMAGE1, BW.MP_DAMAGE2)]
    back = _unit(end or g.state, int(foe["slot"])).get("anim")
    led.check("S134-B", bool(acting) and any(a != anim0 for a in anims) and end is not None
              and _gv(end, "ended") == base["ended"] + 1 and not flinch,
              why or f"enemy slot {foe['slot']} anim {anim0!r} -> {sorted(a for a in anims if a)[:4]} -> {back!r}; Zidane "
                     f"flinch frames {flinch[:4]}; {_brief(end or g.state)}")


def _leg_f(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    who = _who(st)
    (zu, zw), (fu, fw) = who["zidane"], who["fang1"]
    act_id, frame = _leg_a_start(st, ctx)
    if act_id is None:
        led.check("S134-F", False, f"not reached: {frame}")
        return
    base = _base(st)
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    impact = _impact(zw, fw, fig_hp=FIGURE, tgt_raw=(fu.get("hp_raw") or 0, fu.get("mp") or 0),
                     cast_raw=(zu.get("hp_raw") or 0, zu.get("mp") or 0), player_caster=True, player_target=False,
                     cmd=acmd, sub=asub, act_id=act_id)
    samples, end, why = _replay(g, [frame, impact], _ended(base))
    x = end or g.state
    led.check("S134-F", _gv(x, "paired") == base["paired"] + 1 and _gv(x, "swing_skipped") == base["swing_skipped"] + 1
              and _gv(x, "started") == base["started"] + 1,
              why or f"paired {base['paired']} -> {_gv(x, 'paired')}, swing_skipped {base['swing_skipped']} -> "
                     f"{_gv(x, 'swing_skipped')}; {_brief(x)}")


def _leg_g(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    who = _who(st)
    (zu, zw), (fu, fw) = who["zidane"], who["fang1"]
    if zw is None or fw is None:
        led.check("S134-G", False, "not reached: no Zidane / Fang 1")
        return
    base, at = _base(st), cb.mark(g)
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    old = _impact(zw, fw, fig_hp=FIGURE, tgt_raw=(fu.get("hp_raw") or 0, fu.get("mp") or 0),
                  cast_raw=(zu.get("hp_raw") or 0, zu.get("mp") or 0), player_caster=True, player_target=False,
                  cmd=acmd, sub=asub, act_id=None)
    samples, end, why = _replay(g, old, lambda s: _guest(s).get("old_host") is True
                                and _unit(s, int(zu["slot"])).get("mot") == BW.MP_ATTACK, 5.0)
    lines = cb.wait_log(g, at, LINE["LOG_REPLAY_OLD_HOST"], 2.0)
    x = end or g.state
    led.check("S134-G", end is not None and cb.count(lines, LINE["LOG_REPLAY_OLD_HOST"]) <= 1
              and cb.count(cb.log_lines(g), LINE["LOG_REPLAY_OLD_HOST"]) >= 1
              and _gv(x, "swing_skipped") == base["swing_skipped"],
              why or f"old_host {_guest(x).get('old_host')!r}, Zidane mot {_unit(x, int(zu['slot'])).get('mot')!r}; "
                     f"{cb.grep(lines, 'predates action replay', limit=200)}")
    g.wait_frames(40)                                      # the swing plays out


def _leg_j(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    act_id, frame = _leg_a_start(st, ctx)
    if act_id is None:
        led.check("S134-J", False, f"not reached: {frame}")
        return
    base = _base(st)
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    samples, end, why = _replay(g, [frame, _end(act_id, acmd, asub)], lambda s: _gv(s, "declined") > base["declined"], 5.0)
    x = end or g.state
    led.check("S134-J", _guest(x).get("declined_why") == "stale" and _gv(x, "stale") == base["stale"] + 1
              and _gv(x, "started") == base["started"],
              why or f"declined_why {_guest(x).get('declined_why')!r}; {_brief(x)}")


def _leg_l(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    vu, vw = _who(st)["vivi"]
    if vw is None:
        led.check("S134-L", False, "not reached: no Vivi in the diorama")
        return
    base, row0 = _base(st), vu.get("row")
    _id, frame = _start(vw, player=True, cmd=BW.CMD_CHANGE_ID, sub=0, tar=_bit(vw), kind=BW.VFX_KIND_COMMON,
                        num=BW.CMD_CHANGE_ID)
    samples, end, why = _replay(g, frame, _ended(base))
    x = end or g.state
    g.wait_frames(10)
    row1, away = _unit(g.state, int(vu["slot"])).get("row"), _unit(g.state, int(vu["slot"])).get("away")
    led.check("S134-L", end is not None and _gv(x, "hits") > base["hits"] and row0 in (0, 1) and row1 == 1 - row0
              and away is not None and float(away) < 10,
              why or f"Vivi row {row0} -> {row1}, away {away}; {_brief(x)}")


def _decline_leg(g, led: cb.Ledger, ctx: dict, cid: str, lever: tuple, back: tuple, want: str, line: str | None) -> None:
    st = g.state
    act_id, frame = _leg_a_start(st, ctx)
    if act_id is None:
        led.check(cid, False, f"not reached: {frame}")
        return
    sha0, at = _ini_sha(g), cb.mark(g)
    s1, w1 = _act_verb(g, *lever)
    base = _base(g.state)
    samples, end, why = _replay(g, frame, lambda s: _gv(s, "declined") > base["declined"], 5.0)
    x = end or g.state
    lines = cb.new(g, at)
    s2, w2 = _act_verb(g, *back)
    roled = bool((g.state.netsync or {}).get("forced")) and bool((g.state.netsync or {}).get("selftest"))
    ok = s1 is not None and _guest(x).get("declined_why") == want and _gv(x, "started") == base["started"] \
        and (line is None or cb.count(lines, line) >= 1) and s2 is not None and roled
    if cid == "S134-I":
        ok = ok and sha0 is not None and _ini_sha(g) == sha0
    led.check(cid, ok, (w1 or w2 or why) or f"declined_why {_guest(x).get('declined_why')!r} (want {want!r}); role "
                                             f"forced {roled}; Memoria.ini sha {'unchanged' if _ini_sha(g) == sha0 else 'CHANGED'}"
                                             f"; {_brief(x)}")


def _leg_h(g, led: cb.Ledger, ctx: dict) -> None:
    _decline_leg(g, led, ctx, "S134-H", ("rework", "off"), ("rework", "on"), "rework", LINE["LOG_REPLAY_REWORK_OFF"])


def _leg_i(g, led: cb.Ledger, ctx: dict) -> None:
    _decline_leg(g, led, ctx, "S134-I", ("knob", "0"), ("knob", "ini"), "knob", None)


def _leg_pause(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    act_id, frame = _leg_a_start(st, ctx)
    if act_id is None:
        led.check("S134-PAUSE", False, f"not reached: {frame}")
        return
    base = _base(st)
    st1, why = _feed(g, frame)
    run = cb.poll(g, lambda s: _gv(s, "running") >= 1, 3.0, "the replay running")
    if st1 is None or run is None:
        led.check("S134-PAUSE", False, f"not reached: {why or 'the replay never ran'}")
        return
    t0 = time.time()
    g.press("pause", 2)
    on = cb.poll(g, lambda s: _gv(s, "paused_ms") > base["paused_ms"], 3.0, "the pause taking effect (paused_ms rising)")
    cb.hold_for(g, 4.0)
    g.press("pause", 2)
    off, retries = _unpaused(g), 0
    while off is None and retries < 3:                     # [s134 review harness-6] never leave the legs a paused diorama
        retries += 1
        g.press("pause", 2)
        off = _unpaused(g)
    end = cb.poll(g, _ended(base), REPLAY_S, "the paused replay's end") if off is not None else None
    wall_ms = int((time.time() - t0) * 1000)
    x = end or g.state
    last = _guest(x).get("last") or {}
    span = (last.get("end_ms") - last.get("launch_ms")) if _num(last.get("end_ms")) is not None and \
        _num(last.get("launch_ms")) is not None else None
    paused = _gv(x, "paused_ms") - base["paused_ms"]
    # [s134 review harness-01] the pause must land MID-replay and the replay must outlive it: running on the sample where
    # the pause took hold AND on the first sample after the unpause, its end after the unpause's battle_ms -- else the span
    # and the "no abort" clause judge nothing
    run_on = on is not None and _gv(on, "running") >= 1
    run_off = off is not None and _gv(off, "running") >= 1
    off_ms = _gv(off, "battle_ms") if off is not None else None
    end_after = off_ms is not None and _num(last.get("end_ms")) is not None and last.get("end_ms") >= off_ms
    presses = ("the first press never paused (paused_ms flat) -- " if on is None else "") + \
        (f"the unpause took {retries} extra press(es) -- " if retries and off is not None else "") + \
        ("the diorama NEVER unpaused (battle_ms flat after 4 presses) -- " if off is None else "")
    timing = ("the replay ended before the pause took hold -- " if on is not None and not run_on else "") + \
        ("the replay ended or aborted under the pause (not running after the unpause) -- "
         if run_on and off is not None and not run_off else "") + \
        (f"its end_ms {last.get('end_ms')} precedes the unpause's battle_ms {off_ms} -- "
         if run_off and end is not None and not end_after else "")
    led.check("S134-PAUSE", on is not None and off is not None and retries == 0 and end is not None
              and run_on and run_off and end_after
              and _gv(x, "aborted") == base["aborted"] and paused >= 3000
              and _gv(x, "ended") == base["ended"] + 1 and span is not None and span <= wall_ms - 3000,
              f"{presses}{timing}paused_ms +{paused}; aborted {base['aborted']} -> {_gv(x, 'aborted')}; battle span {span} "
              f"ms vs wall {wall_ms} ms; {_brief(x)}")


def _unpaused(g):
    """The state once battle_ms advances again (the diorama runs), or None within 3 s."""
    bm = _gv(g.state, "battle_ms")
    return cb.poll(g, lambda s: _gv(s, "battle_ms") > bm + 100, 3.0, "the unpause (battle_ms advancing)")


def _leg_trip(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    act_id, frame = _leg_a_start(st, ctx)
    if act_id is None:
        led.check("S134-TRIP", False, f"not reached: {frame}")
        return
    at = cb.mark(g)
    s1, w1 = _act_verb(g, "shortcircuit", "off")
    base = _base(g.state)
    samples, end, why = _replay(g, frame, _ended(base))
    x = end or g.state
    lines = cb.new(g, at)
    led.check("S134-TRIP", s1 is not None and _gv(x, "calc_while_booted") > base["calc_while_booted"]
              and cb.count(lines, NO_SHORT) == 1 and _sub(_guest(x), "levers").get("shortcircuit_off") is False
              and cb.count(cb.log_lines(g), LINE["LOG_REPLAY_TRIPWIRE"]) >= 1,
              (w1 or why) or f"calc_while_booted {base['calc_while_booted']} -> {_gv(x, 'calc_while_booted')}; "
                             f"{cb.grep(lines, 'WITHOUT the short-circuit', 'TRIPWIRE', limit=300)}")


def _leg_tripst(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    zu, zw = _who(st)["zidane"]
    if zw is None:
        led.check("S134-TRIPST", False, "not reached: no Zidane")
        return
    s1, w1 = _act_verb(g, "shortcircuit", "off")
    base, ach0 = _base(g.state), cb.bend(g.state).get("ach_held")
    _id, frame = _start(zw, player=True, cmd=BW.CMD_SYS_TRANS, sub=0, tar=_bit(zw), kind=BW.VFX_KIND_SPECIAL,
                        num=BW.SPECIAL_TRANCE_ACTIVATE)
    samples, end, why = _replay(g, frame, _ended(base))
    x = end or g.state
    led.check("S134-TRIPST", s1 is not None and _gv(x, "calc_while_booted") > base["calc_while_booted"],
              (w1 or why) or f"calc_while_booted {base['calc_while_booted']} -> {_gv(x, 'calc_while_booted')}; ach_held "
                             f"{ach0} -> {cb.bend(x).get('ach_held')}; {_brief(x)}")


def _leg_d2(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    act_id, frame = _leg_a_start(st, ctx)
    if act_id is None:
        led.check("S134-D2", False, f"not reached: {frame}")
        return
    base, inv0 = _base(st), _invariants(st)
    _feed(g, frame)
    run = cb.poll(g, lambda s: _gv(s, "running") >= 1, 3.0, "a replay to tear down")
    at = cb.mark(g)
    s1, w1 = _act_verb(g, "teardown")
    lines = cb.wait_log(g, at, LINE["LOG_REPLAY_DISCARD"], 2.0)
    # [s134 review harness-03] past any hit the dropped action could still land (a zombie the sequencer kept would reach
    # ExecVfxCommand later): ~90 frames, then NOTHING may have changed -- every unit's HP/MP, the R9 counter, the held
    # achievements -- and the tripwire (calc_while_booted, kept across ActResetForBoot(false)) must not have moved
    g.wait_frames(90)
    x = g.state
    acting = [u.get("slot") for u in cb.units(x) if u.get("acting")]
    inv1 = _invariants(x)
    calc0, calc1 = base["calc_while_booted"], _gv(x, "calc_while_booted")
    led.check("S134-D2", run is not None and s1 is not None and _gv(x, "running") == 0 and not acting
              and _gv(x, "aborted") == base["aborted"] and inv1 == inv0 and calc1 == calc0
              and cb.count(lines, "teardown (bench)) -- 1 running replay(s) dropped") == 1
              and cb.dio(x).get("booted") is True and cb.bmenu(x).get("contained") is not False,
              w1 or f"{cb.grep(lines, 'ActDiscardAll', limit=300)}; acting {acting}; calc_while_booted {calc0} -> "
                    f"{calc1}; units/r9/ach {'unchanged' if inv1 == inv0 else f'CHANGED: before {inv0}; after {inv1}'}; "
                    f"{_brief(x)}")


# ---- boot 2: the boot backlog, then Leg D
def _boot_2(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    cb.try_ns(g, "endbench", "clear")
    ok, why = cb.try_ns(g, "dioboot", SCENE, GROUP)
    if not ok:
        led.unreached(("S134-BL", "S134-D"), f"boot 2 refused: {why}")
        return
    try:
        act_id, frame = _leg_a_start(g.state, ctx)        # (fed at once: during the boot's swirl / intro)
        fed, early = None, False
        if act_id is not None:
            fed, _fwhy = _feed(g, frame)
            early = fed is not None and (_num(cb.path(fed, "netsync.diorama.intro.normal_ms")) or -1) < 0
        st = cb.poll(g, lambda s: cb.steady(s) and (_num(cb.path(s, "netsync.diorama.intro.normal_ms")) or -1) >= 0,
                     cb.STEADY_S, "boot 2's steady latch")
        x = cb.poll(g, lambda s: _gv(s, "backlog") >= 1, 5.0, "the backlog decline") or g.state
        led.check("S134-BL", fed is not None and early and _guest(x).get("declined_why") == "backlog"
                  and _gv(x, "backlog") == 1,
                  f"fed during the intro {early}; {_brief(x)}" if fed is not None else "not reached: nothing fed")
        if st is None:
            led.unreached(("S134-D",), "boot 2 never reached its steady latch")
            return
        st = g.state
        act_id, frame = _leg_a_start(st, ctx)
        if act_id is None:
            led.check("S134-D", False, f"not reached: {frame}")
            return
        base = _base(st)
        _feed(g, frame)
        run = cb.poll(g, lambda s: _gv(s, "running") >= 1, 3.0, "a replay to leave on")
        ok, lwhy = cb.leave(g, field)
        x = g.state
        led.check("S134-D", run is not None and ok and _gv(x, "aborted") == base["aborted"] + 1
                  and _guest(x).get("abort_why") == "leave" and _gv(x, "running") == 0,
                  lwhy or f"{_brief(x)}")
    except LEG_FAULTS as err:
        _faulted(led, ("S134-BL", "S134-D"), err)
    finally:
        led.unreached(("S134-BL", "S134-D"), "boot 2 ended before this leg")
        _out(g, field)


# ---- boot 3: the deferred Leave, then victory
def _boot_3(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    cb.try_ns(g, "endbench", "clear")
    base = _base(g.state)
    ok, why = cb.try_ns(g, "dioboot", SCENE, GROUP)
    if not ok:
        led.unreached(("S134-D0", "S134-E1"), f"boot 3 refused: {why}")
        return
    try:
        lok, lwhy = cb.try_ns(g, "dioleave")
        deferred = not lok and "deferred" in lwhy
        x = g.state
        led.check("S134-D0", deferred and _gv(x, "aborted") == 0,
                  f"SMOKE (amendment 12 is not benched: no replay can run or park in the swirl): dioleave during the "
                  f"swirl: {'deferred' if deferred else ('LEFT' if lok else lwhy)}; aborted {_gv(x, 'aborted')} (base "
                  f"{base['aborted']}, reset per boot)")
        if not deferred:
            led.unreached(("S134-E1",), "the leave was not deferred (the swirl had ended): this boot is gone")
            return
        st = cb.poll(g, lambda s: cb.steady(s) and (_num(cb.path(s, "netsync.diorama.intro.normal_ms")) or -1) >= 0,
                     cb.STEADY_S, "boot 3's steady latch")
        if st is None:
            led.unreached(("S134-E1",), "boot 3 never reached its steady latch")
            return
        g.wait_frames(5)
        _guard(led, ("S134-E1",), _leg_e1, g, led, ctx)
    except LEG_FAULTS as err:
        _faulted(led, ("S134-D0", "S134-E1"), err)
    finally:
        led.unreached(("S134-D0", "S134-E1"), "boot 3 ended before this leg")
        _out(g, field)


def _leg_e1(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    act_id, frame = _leg_a_start(st, ctx)
    if act_id is None:
        led.check("S134-E1", False, f"not reached: {frame}")
        return
    base = _base(st)
    _feed(g, frame)
    run = cb.poll(g, lambda s: _gv(s, "running") >= 1, 3.0, "a replay before the victory")
    ok, why = cb.try_ns(g, "endbench", "victory")
    samples, done = cb.watch(g, lambda s: cb.battle(s).get("phase") == PHASE_VICTORY, 15.0)
    acting = [s for s in samples if _gv(s, "running") >= 1 and cb.bend(s).get("injected") is True]
    wrong = [cb.frame_of(s) for s in acting if cb.battle(s).get("phase") != PHASE_MENU_OFF]
    early = [cb.frame_of(s) for s in samples if cb.battle(s).get("phase") == PHASE_VICTORY and _gv(s, "running") >= 1]
    led.check("S134-E1", run is not None and ok and bool(acting) and not wrong and not early and done is not None,
              why or f"{len(acting)} acting sample(s) after the injection, not MENU_OFF at {wrong[:4]}; VICTORY while "
                     f"acting at {early[:4]}; {_brief(done or g.state)}")


# ---- boots 4-6: the end presentations
def _boot_e(g, led: cb.Ledger, field: int, ctx: dict, leg: str) -> None:
    cid = f"S134-{leg}"
    st, why = _boot(g, field)
    if st is None:
        led.check(cid, False, f"not reached: {why}")
        return
    try:
        who = _who(st)
        if leg in ("E3", "E4"):                            # [s134 review timing-02 / harness-04] E4 too: a replay that
            gu, gw = who["garnet"]                         # outlives the close fade (~2.2 s at 15 TPS) before R8
            foes = [_wire_of(st, u) for u in cb.units(st, player=False)]
            if gw is None or not foes:
                led.check(cid, False, "not reached: no Garnet or no enemy")
                return
            tar = 0
            for w in foes:
                tar |= _bit(w)
            act_id, frame = _start(gw, player=True, cmd=BW.CMD_SUMMON_GARNET, sub=BW.ABILITY_LEVIATHAN_ID, tar=tar,
                                   kind=BW.VFX_KIND_SPECIAL, num=BW.SPECIAL_LEVIATHAN_FULL, cursor=2)
        else:
            act_id, frame = _leg_a_start(st, ctx)
            if act_id is None:
                led.check(cid, False, f"not reached: {frame}")
                return
        base = _base(st)
        at = cb.mark(g)
        _feed(g, frame)
        run = cb.poll(g, lambda s: _gv(s, "running") >= 1, 3.0, "a replay before the end")
        args = ("other", 4) if leg == "E4" else ("escape",)
        ok, ewhy = cb.try_ns(g, "endbench", *args)
        t_inj = time.time()
        samples, inj = cb.watch(g, lambda s: cb.bend(s).get("injected") is True, 12.0)
        lines = cb.new(g, at)
        if leg == "E2":
            held = [s for s in samples if _gv(s, "running") >= 1]
            injected_while = [cb.frame_of(s) for s in held if cb.bend(s).get("injected") is True]
            led.check(cid, run is not None and ok and inj is not None and held and not injected_while
                      and _gv(inj, "end_held") == base["end_held"] + 1 and cb.count(lines, END_WAITS) >= 1
                      and cb.bend(inj).get("action") == "flee",
                      ewhy or f"{len(held)} held sample(s) while acting, injected while acting at {injected_while[:4]}; "
                              f"end {cb.pick(cb.bend(inj or g.state), 'injected', 'action')}; {_brief(inj or g.state)}")
        elif leg == "E3":
            held_ms = None
            if inj is not None and samples:
                held_ms = _gv(inj, "battle_ms") - _gv(samples[0], "battle_ms")
            led.check(cid, run is not None and ok and inj is not None and _guest(inj).get("abort_why") == "w3"
                      and _gv(inj, "aborted") == base["aborted"] + 1 and held_ms is not None
                      and BW.ACT_W3_MS - 300 <= held_ms <= BW.ACT_W3_MS + 1500,
                      ewhy or f"held {held_ms} ms of battle time (W3 {BW.ACT_W3_MS}); {_brief(inj or g.state)}")
        else:                                              # E4: close -- injected at once, R8 aborts
            # the replay must still act when the close injects, else R8 has nothing to abort: a natural end first is
            # named "not reached" (the bench's own timing), never read as the engine's red
            acting_at_inj = inj is not None and _gv(inj, "running") >= 1
            after = cb.poll(g, lambda s: _guest(s).get("abort_why") == "r8", 4.0, "the R8 abort") \
                if acting_at_inj else None
            took = time.time() - t_inj
            if inj is not None and not acting_at_inj and run is not None and ok:
                led.check(cid, False, f"not reached: the replay was no longer running when the close injected (ended "
                                      f"{base['ended']} -> {_gv(inj, 'ended')}, aborted {base['aborted']} -> "
                                      f"{_gv(inj, 'aborted')}) -- nothing left for R8 to abort; {_brief(inj)}")
            else:
                led.check(cid, run is not None and ok and inj is not None and cb.bend(inj).get("action") == "close"
                          and acting_at_inj and after is not None and took <= 4.0
                          and _gv(after, "aborted") == base["aborted"] + 1,
                          ewhy or f"injected {cb.pick(cb.bend(inj or g.state), 'action', 'inject_phase')}; abort_why "
                                  f"{_guest(after or g.state).get('abort_why')!r} after {took:.1f}s; "
                                  f"{_brief(after or g.state)}")
    except LEG_FAULTS as err:
        _faulted(led, (cid,), err)
    finally:
        led.unreached((cid,), f"boot {leg} ended before this leg")
        _out(g, field)


# ---- boot 7: the death-attack grace
def _boot_k(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    st, why = _boot(g, field)
    if st is None:
        led.check("S134-K", False, f"not reached: {why}")
        return
    try:
        a, b = cb.try_ns(g, "bbench", "start", "0x01"), cb.try_ns(g, "bbench", "caps", "0x22")
        latched = cb.poll(g, lambda s: _guest(s).get("bit5") is True, 3.0, "the bit-5 latch")
        g.wait_frames(10)                                  # (the feed's lane edge marks the next bench drain a backlog)
        st = g.state
        who = _who(st)
        (zu, zw), (fu, fw) = who["zidane"], who["fang1"]
        if latched is None or zw is None or fw is None:
            led.check("S134-K", False, f"not reached: bit5 {_guest(st).get('bit5')!r} (bbench {a} {b}); zidane {zw} fang {fw}")
            return
        base = _base(st)
        armed0 = _num(_sub(_guest(st), "grace").get("armed")) or 0
        acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
        lethal = _impact(zw, fw, fig_hp=FIGURE, tgt_raw=(0, 0), cast_raw=(zu.get("hp_raw") or 0, zu.get("mp") or 0),
                         player_caster=True, player_target=False, cmd=acmd, sub=asub, act_id=None)
        fslot = int(fu["slot"])

        def die(s) -> int:
            return _num(_unit(s, fslot).get("die_seq")) or 0

        def gmask(s) -> int:
            return _num(_sub(_guest(s), "grace").get("mask")) or 0

        bm0 = _gv(g.state, "battle_ms")                    # [s134 review harness-02] the feed's battle-time stamp
        fed, _fwhy = _feed(g, lethal)
        fsamples, x = cb.watch_from(g, fed, lambda s: (_num(_sub(_guest(s), "grace").get("armed")) or 0) > armed0
                                    or die(s) > 0, 3.0)
        x = x or g.state
        armed = (_num(_sub(_guest(x), "grace").get("armed")) or 0) > armed0
        expect = DIE_ATK_SCENES.get(SCENE)                 # [s134 review harness-4] pinned, never the engine's verdict
        if expect is None and armed:
            led.check("S134-K", False, f"a grace ARMED for an enemy without AttackOnDeath (scene {SCENE}'s Fang 1 -- "
                                       f"DIE_ATK_SCENES names no such enemy here): D10 armed it for a plain enemy; "
                                       f"{_brief(x)}")
        elif expect is not None and not armed:
            led.check("S134-K", False, f"NO grace for scene {SCENE}'s AttackOnDeath enemy (DIE_ATK_SCENES); {_brief(x)}")
        elif armed:
            _id, dying = _start(fw, player=False, cmd=BW.CMD_ENEMY_DYING, sub=expect["dying_sub"], tar=_bit(zw),
                                kind=BW.VFX_KIND_ENEMY, num=expect["dying_sub"])
            samples, end, rwhy = _replay(g, dying, _ended(base), 15.0)
            running = [s for s in samples if _gv(s, "running") >= 1]
            held = all((_num(_unit(s, int(fu["slot"])).get("die_seq")) or 0) == 0 for s in running)
            g.wait_frames(30)
            after = _num(_unit(g.state, int(fu["slot"])).get("die_seq")) or 0
            led.check("S134-K", bool(running) and held and after > 0,
                      rwhy or f"AttackOnDeath (scene {SCENE}, pinned): the grace ARMED; die_seq 0 through {len(running)} "
                              f"running sample(s) {held}, after {after}; {_brief(end or g.state)}")
        else:
            # [s134 review harness-02] the plain death within DEATH_BOUND_MS of battle time from the feed, and the grace
            # mask 0 on EVERY publish from the feed to the death -- a grace-like hold that sets the mask (or holds the
            # death) without counting `armed` reads red here, never green
            tail, died = ([], x) if die(x) > 0 else cb.watch(g, lambda s: die(s) > 0, 1.5)
            window = fsamples + tail
            masked = [(cb.frame_of(s), gmask(s)) for s in window if gmask(s)]
            died_ms = (_gv(died, "battle_ms") - bm0) if died is not None else None
            led.check("S134-K", died is not None and died_ms is not None and died_ms <= DEATH_BOUND_MS and not masked,
                      f"scene {SCENE} has no AttackOnDeath enemy (pinned): NO grace (armed +0; the mask set on "
                      f"{len(masked)} of {len(window)} publish(es) from the feed to the death"
                      f"{(' ' + str(masked[:4])) if masked else ''}); die_seq "
                      f"{_unit(died or g.state, fslot).get('die_seq')!r} after {died_ms} ms of battle time (bound "
                      f"{DEATH_BOUND_MS}) -- the positive half needs a DIE_ATK_SCENES scene")
    except LEG_FAULTS as err:
        _faulted(led, ("S134-K",), err)
    finally:
        led.unreached(("S134-K",), "boot 7 ended before this leg")
        cb.try_ns(g, "bbench", "stop")
        _out(g, field)


# ---- boot 8: the real host frames
def _boot_c(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    st, why = _boot(g, field)
    if st is None:
        led.check("S134-C", False, f"not reached: {why}")
        return
    try:
        taped = _num(_sub(_host(st), "tape").get("starts")) or 0
        span_ms = _num(_sub(_host(st), "tape").get("ms")) or 0
        if taped < 1:
            led.check("S134-C", False, f"not reached: the host lane's tape holds no START ({_sub(_host(st), 'tape')})")
            return
        base = _base(st)
        s1, w1 = _act_verb(g, "tape", "play")
        mid, t0, shot = span_ms / 2000.0, time.time(), {}

        def snap(_s):                                      # ONE mid-tape frame, an artifact to READ (never a verdict)
            if not shot and time.time() - t0 >= mid:
                shot["png"] = cb.shot(g, "s134-leg-c-tape")[0]
        samples, done = cb.watch(g, lambda s: _gv(s, "starts_rx") - base["starts_rx"] >= taped and _gv(s, "running") == 0
                                 and _gv(s, "inbox") == 0, span_ms / 1000.0 + 5.0, on_sample=snap)
        x = done or g.state
        gs = _guest(x)
        rx = _gv(x, "starts_rx") - base["starts_rx"]
        declined = _gv(x, "declined") - base["declined"]
        started = _gv(x, "started") - base["started"]
        whys = gs.get("declined_why")
        other = declined - ((_gv(x, "noop") - base["noop"]) + (_gv(x, "stale") - base["stale"]))
        led.check("S134-C", s1 is not None and done is not None and rx == taped and started == rx - declined
                  and other == 0 and _gv(x, "faulted") == 0 and _gv(x, "aborted") == base["aborted"],
                  w1 or f"taped STARTs {taped} ({span_ms} ms); received {rx}, started {started}, declined {declined} "
                        f"(last {whys!r}, other {other}); {_brief(x)}; shot {shot.get('png')}")
    except LEG_FAULTS as err:
        _faulted(led, ("S134-C",), err)
    finally:
        led.unreached(("S134-C",), "boot 8 ended before this leg")
        _out(g, field)


# ------------------------------------------------------------------------------------------------ the release
def _release(g, led: cb.Ledger, ctx: dict) -> None:
    """INV first (the last leave is behind us), then the levers left SET on purpose and `reset`: the 'levers back' line,
    and every lever at rest when re-read WITH the role."""
    fp0 = ctx.get("fp0")
    if ctx["probe"]:
        fp1, why = cb.fingerprint(g, field=cb.FIELD)
        diff = cb.fp_diff(fp0, fp1) if fp0 and fp1 else None
        led.check("S134-INV", fp0 is not None and fp1 is not None and not diff,
                  why or f"changed: {diff}; battle_no {fp0.get('_battle_no') if fp0 else None} -> "
                         f"{fp1.get('_battle_no') if fp1 else None} (a diorama's InitBattle bumps it: not judged)")
        for args in (("replay", "off"), ("rework", "off"), ("shortcircuit", "off"), ("knob", "0")):
            _act_verb(g, *args)
    else:
        led.check("S134-INV", True, "nothing was booted (the probe failed closed): nothing to compare")
    at = cb.mark(g)
    cb.release(g)
    lines = cb.new(g, at)
    if not ctx["probe"]:
        led.check("S134-R", False, f"`{PROBE}` absent: nothing was set")
        return
    rr, rwhy = cb.reread_with_role(g)
    lv = _sub(_guest(rr), "levers") if rr is not None else {}
    led.check("S134-R", rr is not None and cb.count(lines, LINE["LOG_REPLAY_LEVERS_BACK"]) == 1
              and lv == {"replay_off": False, "rework_off": False, "shortcircuit_off": False, "knob": -1}
              and _gv(rr, "inbox") == 0,
              (f"re-read WITH the role: levers {lv}, inbox {_gv(rr, 'inbox')}" if rr is not None else
               f"no re-read with the role ({rwhy})") + f"; {cb.grep(lines, 'released with the harness')}")


# ================================================================================================ THE TAPE LEG
PORT = pb.env_int("COOP_PEER_PORT", pb.DEFAULT_PORT)
CODE = pb.BENCH_CODE
GRACE_MS = pb.BENCH_GRACE_MS
POLL_S = 0.1


def act_tape_dir() -> Path:
    """COOP_ACT_TAPE_DIR, else <the MAIN repo>/.harness-runs/coop-tapes/act-s133 -- beside coop-tapes/, never in it, so
    coop_cut_hold's latest.json (pinned to the s117 arc tape) never moves (audit 4.9)."""
    env = os.environ.get("COOP_ACT_TAPE_DIR", "").strip()
    return Path(env).expanduser().resolve() if env else pb.main_repo() / ".harness-runs" / "coop-tapes" / "act-s133"


def act_tape() -> Path | None:
    """COOP_ACT_TAPE, else act_tape_dir()'s latest.json, else its newest *.f9tape; None = no tape there."""
    env = os.environ.get("COOP_ACT_TAPE", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    d = act_tape_dir()
    try:
        p = Path(json.loads((d / "latest.json").read_text(encoding="utf-8"))["tape"])
        if p.exists():
            return p
    except (OSError, ValueError, KeyError, TypeError):
        pass
    tapes = sorted(d.glob("*.f9tape"), key=lambda q: q.stat().st_mtime) if d.is_dir() else []
    return tapes[-1] if tapes else None


def tape_act_facts(records, cp, nonce: int | None) -> dict:
    """The host's action lane on a tape's battle ``nonce``: its type-6 frames counted through battlewire (``starts``,
    ``ends``, ``impacts``, ``ext``, ``stat``, ``bad``), ``ok`` (>= 1 START: an s133+ host's tape) and ``why``."""
    frames = [p for _t, p in cp.tape_action_frames(records)]
    mine = [p for p in frames if len(p) >= BW.ACT_LEGACY_LEN and (nonce is None or p[0] == (nonce & 0xFF))]
    s = BW.act_tape_summary(mine)
    s["all_frames"] = len(frames)
    s["ok"] = s["starts"] >= 1
    s["why"] = (f"{s['starts']} START(s), {s['ends']} END(s), {s['impacts']} impact(s) ({s['ext']} with an id) on battle "
                f"nonce {nonce}" if s["ok"] else
                f"no s133 tape: no START on battle nonce {nonce} ({len(frames)} type-6 frame(s) on the tape -- a pre-s133 "
                "host's, or its `hoststarts off`)")
    return s


GUEST_VALUES = {"Enabled": "1", "Role": "client", "RelayUrl": f"ws://127.0.0.1:{PORT}", "SessionCode": CODE,
                "FollowHost": "1", "TargetField": "0", "GuestSlots": "0", "GuestStockMenu": "1",
                "SessionGraceMs": str(GRACE_MS), "AutoTeleport": "0", "DioramaSwirlFrames": "0"}


class _TapeCtx:
    def __init__(self):
        self.tape = None
        self.facts = None
        self.act = None
        self.field = pb.BENCH_FIELD
        self.scene = None
        self.nonce = None
        self.guard = None
        self.peer = None
        self.eng = None
        self.samples: list = []
        self.has_guest = False
        self.anchors: dict = {}


def _run_tape(g) -> None:
    calibrate = cb.CALIBRATE
    led = cb.Ledger(g, _tape_catalog(calibrate), finals=("T2-SAVE", "T2-INI", "S134T-CAL"))
    ctx = _TapeCtx()
    try:
        _tape_leg(g, led, ctx, calibrate)
    except HarnessError as err:
        g.note(f"the tape leg raised: {str(err)[:400]}")
        led.close(f"not reached: the leg raised ({str(err)[:200]})")
    finally:
        if ctx.peer is not None and ctx.peer.how_ended is None:
            g.note(f"coop_peer replay-host: {ctx.peer.stop()}")
        if "T2-SAVE" not in led.done:
            if ctx.eng is None:                            # [s134 review harness-14] a refusal: nothing to judge
                led.unreached(("T2-SAVE",), "the guest never ran a session (the leg stopped before it)")
            else:
                fell = pb.hits(ctx.eng.lines(), "ramp_failed")
                led.check("T2-SAVE", not fell, f"the exit ramp fell back to the TITLE: {pb.show(fell, 1)}" if fell else
                          "no title fallback")
        if ctx.guard is not None:
            ok, why = ctx.guard.restore()
            led.check("T2-INI", ok, why)
        else:
            led.check("T2-INI", True, "Memoria.ini was never edited (the leg stopped before the edit)")
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'action-replay-tape')}")
        if calibrate:
            led.close("not reached: the leg ended before this check")
            led.judge_calibration("S134T-CAL", _tape_predicted(ctx.has_guest))
        led.close(final=True)


def _tape_leg(g, led: cb.Ledger, ctx: _TapeCtx, calibrate: bool) -> None:
    act_ids = list(TAPE_CHECKS)
    ctx.tape = act_tape()
    if ctx.tape is None or not ctx.tape.exists():
        led.check("T2-TAPE", False, f"no s133 tape ({ctx.tape or act_tape_dir()}): record one first (the docstring's "
                                    "RECORDING steps)")
        led.close("not reached: no s133 tape")
        return
    try:
        cp = pb.coop_peer_module()
        _header, records, torn = cp.read_tape(ctx.tape)
    except Exception as err:                               # noqa: BLE001 -- the reason is the check's detail
        led.check("T2-TAPE", False, f"no s133 tape: {ctx.tape} does not read back ({err})")
        led.close("not reached: no s133 tape")
        return
    ctx.facts = pb.tape_facts(records, cp, field=None)
    f1, f3 = ctx.facts["f1"], ctx.facts["f3"]
    ctx.field = f1.get("field") or pb.BENCH_FIELD
    ctx.scene, ctx.nonce = f3.get("map"), f3.get("nonce")
    ctx.act = tape_act_facts(records, cp, ctx.nonce)
    plan = pb.plan_leg("cal", ctx.facts, GRACE_MS / 1000.0)
    ok = ctx.act["ok"] and plan["ok"]
    led.check("T2-TAPE", ok, f"{ctx.tape.name} ({len(records)} records{', torn ' + str(torn) + ' B' if torn else ''}): "
                             f"field {ctx.field}, scene {ctx.scene}, nonce {ctx.nonce}; {ctx.act['why']}"
                             + ("" if plan["ok"] else f"; the five facts: {plan['why'][:200]}"))
    if not ok:
        led.close("not reached: no s133 tape" if not ctx.act["ok"] else "not reached: the tape lacks a CAL fact")
        return
    okc, whyc = pb.read_cal(ctx.tape)
    led.check("T2-CAL", okc, whyc)
    if not okc:
        led.close(f"not reached: the instrument is untrustworthy -- {whyc[:200]}")
        return
    free, why = pb.port_free(PORT)
    if not free:
        led.check("T2-PEER", False, why)
        led.close("not reached: the bench port is taken (nothing was edited)")
        return
    try:
        moogle_only = pb.ini_autosave_moogle_only((Path(g.game_path) / "Memoria.ini").read_text(encoding="utf-8",
                                                                                                errors="replace"))
    except OSError:
        moogle_only = False
    if moogle_only:
        led.check("T2-SAVE", False, "[SaveFile] AutoSaveOnlyAtMoogle = 1 -- set it to 0 for the bench (nothing edited)")
        led.close("the guest can have no own autosave on the bench field (T2-SAVE)")
        return
    cb.provenance(g)
    g.note(f"R3 s134 tape leg: {ctx.tape.name}, ActionReplay {0 if calibrate else 1}"
           + (" -- CALIBRATION (the knob)" if calibrate else ""))
    g.newgame()
    # the guest seats the recording host's party (coop_tape_record seeds COOPPARTY too): a host actor the guest's
    # diorama lacks declines `actor`, which S134T-DECL counts as a defect of the RUN (its detail names it)
    g.note(cb.seed_party(g, back_to=ctx.field))
    if g.state.field_id != ctx.field:
        g.warp(ctx.field)
    try:
        g.no_encounters(True)
    except HarnessError as err:
        g.note(f"noencounter refused ({str(err)[:160]})")
    g.wait_frames(45)
    ctx.eng = pb.EngineLog(g.engine_log())
    values = dict(GUEST_VALUES, ActionReplay="0" if calibrate else "1")
    rd = Path(getattr(g, "scenario_dir", None) or g.run_dir)
    ctx.guard = pb.IniGuard(Path(g.game_path) / "Memoria.ini", values, label="coop-action-replay-tape", run_dir=rd)
    try:
        g.note(ctx.guard.apply())
    except (OSError, RuntimeError) as err:
        led.check("T2-PEER", False, f"the Memoria.ini edit failed: {err}")
        led.close("not reached: Memoria.ini could not be edited")
        return
    cfg = _tape_config(g, ctx, calibrate)
    if not cfg:
        led.check("T2-PEER", False, f"the engine never logged the guest config (config lines: "
                                    f"{pb.show(pb.hits(ctx.eng.lines(), 'config'))})")
        led.close("not reached: the guest config never applied")
        return
    ctx.peer = pb.PeerProc("replay-host", [ctx.tape, *pb.plan_args(plan, port=PORT, code=CODE)],
                           log_path=rd / "coop_peer-replay-act.log", out_path=rd / "coop_peer-replay-act.out")
    g.note(f"starting: {ctx.peer.command_text()}")
    ctx.peer.start()
    up = ctx.peer.wait_for(pb.PEER["listening"], 15.0, tick=lambda: _tape_sample(g, ctx))
    conn = ctx.peer.wait_for(pb.PEER["guest_connected"], 25.0, tick=lambda: _tape_sample(g, ctx)) if up else None
    start = ctx.peer.wait_for(pb.PEER["replay_start"], 10.0, tick=lambda: _tape_sample(g, ctx)) if conn else None
    relay = pb.hits(ctx.eng.lines(), "relay_up", pred=lambda m: m.group(3) == "guest" and m.group(2) == CODE)
    knob_ok, knob_why = _tape_knob(cfg, calibrate, cb.has(g.state, PROBE))
    ok = up is not None and conn is not None and start is not None and bool(relay) and knob_ok
    led.check("T2-PEER", ok, f"config: {pb.show(cfg, 1)}; {knob_why}; peer: {up[1] if up else 'never listened'} / "
                             f"{conn[1] if conn else 'no guest'} / {start[1] if start else 'no replay start'}; engine: "
                             f"{pb.show(relay, 1)}")
    if not ok:
        led.unreached(act_ids, "the instrument never started (T2-PEER)")
        return
    ctx.anchors["start"] = start[0]
    _tape_run(g, led, ctx)


def _tape_config(g, ctx: _TapeCtx, calibrate: bool) -> list:
    """The engine's config line for the bench guest -- with ' actionReplay=0' exactly when the knob is written 0 (an engine
    without the key never prints it: s133 reads any value as nothing)."""
    def found():
        return pb.hits(ctx.eng.lines(), "config", pred=lambda m: m.group(1) == "True" and m.group(2) == "client"
                       and m.group(5) == f"ws://127.0.0.1:{PORT}" and m.group(6) == CODE)
    for wait in (6.0, 10.0):
        deadline = time.time() + wait
        while time.time() < deadline:
            if found():
                return found()
            time.sleep(0.25)
        if wait == 6.0:
            try:
                g.warp(ctx.field)
            except HarnessError as err:
                g.note(f"the reload warp failed: {str(err)[:200]}")
    return []


def _tape_knob(cfg: list, calibrate: bool, has_guest: bool) -> tuple:
    """[s134 review harness-8] The config line's ' actionReplay=0' exactly when the knob was written 0 -- on an engine that
    prints it (s134+: `act.guest` published); an s133 engine reads the key as nothing and never prints it (a note).
    (ok, why)."""
    if not cfg:
        return False, "no config line"
    off = "actionReplay=0" in (cfg[-1][2].group(4) or "")
    if not has_guest:
        return True, f"actionReplay {'printed' if off else 'not printed'} (an engine without act.guest: never judged)"
    if off != calibrate:
        return False, (f"the knob did NOT land: actionReplay written {0 if calibrate else 1}, the config line "
                       f"{'names' if off else 'lacks'} ' actionReplay=0'")
    return True, f"actionReplay {0 if calibrate else 1} as written"


def _tape_sample(g, ctx: _TapeCtx) -> dict:
    st = g.state
    s = {"t": _dt.datetime.now(), "frame": st.frame, "booted": cb.path(st, "netsync.diorama.booted"),
         "guest": cb.path(st, "netsync.battle.act.guest"),
         "units": [(u.get("slot"), bool(u.get("acting")), u.get("anim")) for u in cb.units(st)]}
    if isinstance(s["guest"], dict):
        ctx.has_guest = True
    ctx.samples.append(s)
    return s


def _tape_run(g, led: cb.Ledger, ctx: _TapeCtx) -> None:
    start = ctx.anchors["start"]
    span = float((ctx.facts.get("end") or 0.0) - (ctx.facts.get("start") or 0.0))

    def returned():
        e = ctx.eng.lines()
        el = pb.hits(e, "end_leave", after=start)
        return bool(el) and bool(pb.hits(e, "return", after=el[0][0]))
    deadline = time.time() + span + 120.0
    while time.time() < deadline and not returned():
        _tape_sample(g, ctx)
        time.sleep(POLL_S)
    for _ in range(20):
        _tape_sample(g, ctx)
        time.sleep(POLL_S)
    e = ctx.eng.lines()
    F, M, N = ctx.field, ctx.scene, ctx.nonce
    need = {"paired": pb.hits(e, "paired", after=start, pred=lambda m: int(m.group(1)) == F),
            "armed": pb.hits(e, "armed", after=start),
            "boot": pb.hits(e, "boot", after=start, pred=lambda m: M is None or int(m.group(1)) == M),
            "live": pb.hits(e, "live", after=start, pred=lambda m: N is None or int(m.group(2)) == N)}
    missing = [k for k, v in need.items() if not v]
    led.check("S134T-I", not missing, f"missing {missing}" if missing else "paired, ARMED, BOOT, LIVE logged")
    judge_tape(led, ctx.samples, [m for _t, _l, m in e], ctx.act)


def judge_tape(led, samples: list, messages: list, act: dict) -> None:
    """THE TAPE LEG'S JUDGE (pure: the samples -- each {booted, guest, units} -- and the engine's messages since the start;
    test_harness_netsync.py runs it on synthetic runs): P0, B5, RX, RUN, ACT, PAIR, DECL, END, TRIP, LOG."""
    blocks = [s["guest"] for s in samples if isinstance(s.get("guest"), dict)]
    if not blocks:
        led.unreached(TAPE_ACT, "`netsync.battle.act.guest` was never published (an engine before s134: fails closed)")
        return
    led.check("S134T-P0", True, f"{len(blocks)} sample(s) with act.guest")
    booted = [s["guest"] for s in samples if s.get("booted") and isinstance(s.get("guest"), dict)]
    b5 = [b for b in booted if b.get("bit5") is True and (_num(b.get("host_caps")) or 0) & BW.CAP_ACTION_STARTS]
    led.check("S134T-B5", bool(b5), f"{len(b5)} of {len(booted)} booted sample(s) with bit5 + host_caps & 0x20")
    last = blocks[-1]
    g = {k: _num(last.get(k)) or 0 for k in ("starts_rx", "ends_rx", "started", "declined", "queued", "waiting",
                                              "running", "stale", "backlog", "superseded", "noop", "dropped", "ended",
                                              "aborted", "faulted", "hits", "paired", "swing_skipped")}
    aborts = last.get("aborts") if isinstance(last.get("aborts"), dict) else None
    disc = last.get("discarded") if isinstance(last.get("discarded"), dict) else {}
    # [s134 review harness-05] the guest's transport is this run's own (IniGuard's config), so its inbound type-6 drop
    # counter starts at 0: judged ABSOLUTE (max 0), never against the first booted read -- a boot backlog's drops (frames
    # queued until PHASE_NORMAL, the oldest dropped at the 64-frame cap) are already in that read. -1 = not read yet.
    rx = [_num(b.get("rx_dropped")) for b in blocks]
    drops = [v for v in rx if v is not None and v >= 0]
    if drops:
        dtxt = f"{drops[:1]}..{drops[-1:]} (max {max(drops)}" + ("; a nonzero FIRST read = drops during the boot "
                                                                "backlog" if drops[0] else "") + ")"
    else:
        dtxt = "never read (no steady drain)"
    led.check("S134T-RX", 1 <= g["starts_rx"] <= act.get("starts", 0) and g["ends_rx"] >= 1
              and last.get("old_host") is False and bool(drops) and max(drops) == 0,
              f"starts_rx {g['starts_rx']} of the tape's {act.get('starts')}, ends_rx {g['ends_rx']}, old_host "
              f"{last.get('old_host')!r}, rx_dropped {dtxt}")
    led.check("S134T-RUN", g["started"] >= 1 and g["queued"] == g["waiting"] == g["running"] == 0
              and BW.act_guest_invariant(last),
              f"started {g['started']}, declined {g['declined']}, queued/waiting/running {g['queued']}/{g['waiting']}/"
              f"{g['running']}")
    acting = sum(1 for s in samples for _slot, a, _anim in s.get("units") or [] if a)
    led.check("S134T-ACT", acting > 0, f"{acting} acting unit-sample(s)")
    led.check("S134T-PAIR", g["paired"] >= 1 and g["hits"] >= 1 and g["swing_skipped"] >= 1,
              f"paired {g['paired']}, hits {g['hits']}, swing_skipped {g['swing_skipped']}")
    # [s134 review harness-9] a START parked at the end, dropped by the end's abort-all (`dropped`), is no defect
    led.check("S134T-DECL", g["declined"] == g["stale"] + g["backlog"] + g["superseded"] + g["noop"] + g["dropped"],
              f"declined {g['declined']} (stale {g['stale']}, backlog {g['backlog']}, superseded {g['superseded']}, noop "
              f"{g['noop']}, dropped at the end {g['dropped']}; last {last.get('declined_why')!r})")
    # [s134 review timing-04] EVERY abort judged by its reason (act.guest.aborts), never the last one: an early `pending` /
    # `host-end` / `cap` is not masked by the end's R8. A block without `aborts` fails closed.
    by = {k: (_num(aborts.get(k)) or 0) for k in BW.ACT_ABORTS_KEYS} if aborts is not None else {}
    ends = sum(by.get(k, 0) for k in END_ABORTS)
    other = {k: v for k, v in by.items() if v and k not in END_ABORTS}
    led.check("S134T-END", aborts is not None and g["ended"] >= 1 and BW.act_guest_ends_balance(last)
              and g["faulted"] == 0 and not other and ends == g["aborted"],
              (f"ended {g['ended']} + aborted {g['aborted']} + discarded.running {_num(disc.get('running')) or 0} vs "
               f"started {g['started']}; faulted {g['faulted']}; aborts by reason {by or None} (an end's: {ends}; any "
               f"other: {other or 'none'}; last {last.get('abort_why')!r})")
              if aborts is not None else "no act.guest.aborts on the last sample (an s134 build before the review pass): "
                                         "every abort cannot be judged -- fails closed")
    fired = [_num(b.get("calc_while_booted")) for b in blocks if _num(b.get("calc_while_booted"))]
    led.check("S134T-TRIP", not fired, f"calc_while_booted nonzero on {len(fired)} sample(s)")
    started_lines = [m for m in messages if m.startswith(BW.LOG_REPLAY_STARTED)]
    bad = [m for m in messages if FAULTED in m or m.startswith(BW.LOG_REPLAY_TICK_FAILED.rstrip())
           or m.startswith(BW.LOG_REPLAY_TRIPWIRE)]
    summary = [m for m in messages if m.startswith(BW.LOG_REPLAY_SUMMARY + "teardown)")]
    led.check("S134T-LOG", bool(started_lines) and not bad and any(f"-- {g['starts_rx']} START(s) received" in m
                                                                    for m in summary),
              f"{len(started_lines)} started line(s); bad {[m[:120] for m in bad[:2]]}; summary "
              f"{[m[:160] for m in summary[:1]]}")
