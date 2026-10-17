"""R3 GROUP 2, s137 -- THE TRANCE BURST TIMING (memoria-patch s137), the solo bench, run unattended.

THE GAP (studies/battle-coop/R3-DESIGN.md 3.3.6 and 6.11 as amended by R3-ACTION-REPLAY-AUDIT.md 2.5 -- amendments 1-6,
decisions D1-D6 -- 3.5 and 4.8; the design's and the audit's "s126": group 2 was renumbered s133-s141). Since s134 the guest
REPLAYS the host's SysTrans burst, but its reconciler swapped a player's MODEL the moment the host's type-1 sample carried
the trance stat bit -- so the trance model appeared first and its burst played after it. s137 DEFERS that one change: on a
booted diorama whose host latched header bit 5 and whose guest can replay (ActionReplay=1, SFXRework, no `replay off`
lever, the `trancegrace` lever on), ApplyUnit's model check RECORDS a deferral for the wire slot and ActTick resolves it
every frame: the SysTrans replay's own HIT swaps the model (the host's own swap point; the argument the guest's MIRRORED
stat bit, probe-guarded -- D2); else, while a queued or pending START, a running replay or a held impact NAMES the unit it
waits, then a GRACE of 400 ms of BATTLE time (audit 3.5) swaps it, capped at 2500 ms from the sample -- never while the
unit's own SysTrans burst is in flight (a START of it queued or pending, or its replay running unhit). Any decline of its
SysTrans START (a duplicate excepted, a NOOP included) and its replay's end or abort swap at once; a sample whose burst
already hit, declined or ended within 400 ms swaps on arrival (the START-first order); the end injection flushes every
pending one by the probe; the teardown drops them. THE CONTAINMENT LAW holds: s137 only DELAYS the host's own model
change -- the trance STATUS bit, enable_trance_glow, the gauge and the ATB follow the host at the sample exactly as before,
and nothing writes trance_no. Read back: `netsync.battle.act.guest.trance` (every role): `on`, `gate`, `deferred`,
`pending`, `swaps_by_hit|grace|cap|decline|end|inject`, `moot`, `dropped`, `immediate`, `on_arrival`, `hit_unpaired`,
`hit_untrusted`, `present`, `last{slot, swapped, to, via, id, record_ms, ms}`; and the worn model off the SEATED unit:
`battle.units[].trance_model`. Bench verb (selftest role): `netsync actbench trancegrace on|off` (off = the pre-s137
timing), plus s135's `unit <slot> trance0|trance1` (one post-horizon type-1 record through the reconciler's own ApplyUnit)
and s134's `feed`.

ONE LEG, the solo bench -- NO TAPE LEG (deferred, not impossible). The recorded s133 host tape
(.harness-runs/coop-tapes/act-s133) carries no trance (no SysTrans START, no trance sample). A host-side seam to record one
DOES exist: the stock Battle Assistance booster (SettingsState.IsTranceFull, BoosterType index 0) puts every player into
Trance on a non-diorama host each PHASE_NORMAL frame (SettingsState.SetTranceFull: Trance = 255, then AlterStatus(Trance);
it returns early only while a diorama is active), and the agent already flips a booster the same way for `noencounter`.
It is not used here because (1) it needs a NEW HarnessAgent verb (`booster assist 1|0`, released by `reset`) -- an engine
change with its own gates; (2) the host would EARN a persistent trance achievement on its save (the save-serialised
trance_no behind Trance1 / Trance50: an outward state change this bench must not make); and (3) the booster rewrites the
fight the tape records (every player in Trance every frame), so the tape leg would need its own plan and its own CAL pass.
Queued as a follow-up: that leg would exercise the transport-side ApplyUnit record (a new seq in
PHASE_NORMAL) that no selftest leg reaches. The real-intake gate (bit 5 off a real host's header) is exercised with no
trance by the s134-s136 tape legs of the 6.1 regression set on this DLL.

PRECONDITIONS -- THE OPERATOR'S JOB:
  * Memoria.ini [Netsync] Enabled = 0 (or absent) -- the selftest role is refused on a live-configured install; the bench
    never edits Memoria.ini (S137-INI reads it READ-ONLY and, when it reads 1, records itself red and runs NOTHING).
  * The DLL under test deployed and the game launched on it (the orchestrator's: this bench deploys nothing).
  * COOPPARTY (studies/battle-coop/bench/coopparty.field.toml, 30604) registered: Zidane / Vivi / Garnet / Steiner (PRE).

THE SOLO BENCH. Field 30602 (cb.FIELD), `stateevery 1`. Battle 1 (the TAPE) is coop_action_fallback's: s133's in-engine tape
over `battle 306 <COOP_ACT_GROUP, default 4>` (Fang x2) with the plan that cannot end the fight early (s134 LESSON 3: Zidane
Attacks the sturdiest standing ally once, Garnet Potions herself, every other prompt Defends until both are done and two
more prompts have passed, then `fight` to the victory) -- its result screen cleared with Session.leave_battle(
stop_on_field=True) (s134 LESSON 4) -- read offline for Zidane's Attack START (its num, its host Speed): the PARK and BUSY
legs' running replay. Then THE INVARIANTS (cb.fingerprint) and two diorama boots, each `dioboot 306 <group>` on 30602, each
reached steady, then THE STAGE-8 FEED ARMED (review replay F6, audit 4.8 Leg K): `bbench start 0x01` + `bbench caps 0x22`
(the start op resets caps to 0x02), so the live peer view advertises bit 5 and the guest's per-boot latch reads it
(`act.guest.bit5`); ten frames on (the feed's lane edge marks the next bench drain a backlog) the legs begin, and
`bbench stop` ends each boot. Every fed frame carries this bench's own nonce byte (0x5F, MARKER: s134's 0x5C, s135's 0x5D,
s136's 0x5E). THE SEAT BY WIRE SLOT AND MODEL (s134 LESSON 1): every selftest `dioboot` seats the selftest mirror's stand-in
("BENCH", another character's model -- Freya's at writing, whose trance model is Freya's) at Zidane's battle-1 wire: every
leg's unit is THAT seat at that WIRE slot (coop_action_replay._who -- 0 when Zidane leads), never a unit named Zidane, and
its worn model is READ OFF THE SEATED UNIT (`battle.units[].trance_model`) -- never assumed, never a hard-coded model id.
No leg sends a `dioleave` mid-swirl (s134 LESSON 2): every leave comes after a steady boot. THE ORDER (s134 LESSON 3):
nothing in boot 1 ends the fight (TD, the teardown, is its last leg); the end injection (INJECT) has its own boot. A
follow-up that must land inside a grace or before a replay's hit rides the feed's OWN request (the agent runs a request's
next step Block(2) frames on) -- never a second request after a poll (s135 LESSON). Between legs the seat is brought back
to its normal model (`unit <seat> trance0`) and the bench waits until nothing runs and QUIET_MS = the grace + 200 = 600 ms
of battle time pass (every burst mark then older than the 400 ms on-arrival window): QUIET. THE PUBLISH WITNESS (s136
LESSON 8: a clock the feature does not compute): every timer window (GRACE, BUSY, CAP) is judged twice -- on s137's own
`last.ms - last.record_ms`, and on the publishes: the request's own state's act.guest.battle_ms (x0, never before
last.record_ms) to the first publish whose seat wears the new model, within the window +- one battle frame.

WHAT IS PROVEN (S137-*):
  INI    precondition: [Netsync] Enabled reads 0 / absent (READ-ONLY) -- else NOTHING runs.
  S0     the harness forced the selftest role (Memoria.ini untouched).
  P0     the probe: `netsync.battle.act.guest.trance` is published WHOLE -- exactly the agent's keys -- with `on` true (no
         lever stranded) -- else no trance op is EVER sent (fails closed).
  PROOF  the selftest proof block's line reads exactly 'action trance selftest: OK (21 rows)' -- no FAIL line.
  PRE    precondition: battle 1 seats Zidane, Vivi and Garnet and 2+ enemies.
  TAPE   battle 1's s133 tape carries Zidane's Attack START (kind 3: its num and host Speed).
  BOOT   boot 1 steady, the feed armed: `act.guest.trance` at rest (every counter 0, pending 0, `last` null), `bit5` latched,
         `on` and `gate` what the run wants (true; under COOP_CALIBRATE's lever `on` false, under its caps run `bit5`
         false -- `gate` false either way: a lever that did not land reds BOOT, so CAL names its cause); the seat wears its
         normal model (trance_model false, a bool: the key is there) with no Trance status bit.
  -- boot 1: nothing dies --
  GRACE  6.11's first leg, NO START: `unit <seat> trance1` alone -- on the request's own state the change is HELD (deferred
         +1, the seat's bit in `pending`, trance_model false); then `last` {via grace, swapped, to true, slot the seat's
         wire} at 400-450 ms of battle time after its record (last.ms - last.record_ms: the ENGINE's clock) AND on the
         publish witness, trance_model false on every publish before it and true after.
  STAT   THE CONTAINMENT LAW at the same op: the seat's `status` carries Trance (16384) on the request's own state while its
         model waits -- the status follows the host at the sample, only the model is delayed.
  PAUSE  (fix pass 2: rtiming-1; audit 3.5 names the 400 ms grace a BATTLE-time timer) `unit <seat> trance1` + s134 PAUSE's
         verified press (`press pause 2`) in ONE request -- the press lands Block(2) frames on, inside the grace -- then
         2.5 s paused: on every paused publish (act.guest.paused_ms rising) the seat's bit in `pending`, its normal model,
         swaps_by_grace +0; unpaused (s134's verified retry: the pause key pressed again until battle_ms advances -- a
         swallowed press is PAUSE's red, never a paused diorama left to the legs after it), the swap via grace at 400-450 ms
         of BATTLE time after the record, paused_ms +2000 or more, and the wall span from the op to the swap's publish past
         the battle span by at least 2000 ms. A pause that took hold 400+ ms after the record cannot tell a battle-time
         grace from a wall one: NOT REACHED.
  HIT    6.11's second leg: `unit <seat> trance1` + a SysTrans START (kind 3, Special_Trance_Activate 257, the seat's wire
         bit) in ONE request: HELD at the op; swaps_by_hit +1, `last` {via hit, to true, id the START's} with last.ms ==
         act.guest.last.first_hit_ms (the replay's own hit: the same battle-ms read), trance_model false on every publish
         before that hit, swaps_by_grace +0 (the burst held it past the grace); after the replay's end `present` +1
         (stock's SetPresentColor at a SysTrans finish -- the hit swap itself presents nothing). THE HIT MUST LAND PAST THE
         GRACE (fix pass: harness-hit-not-discriminating): its first_hit_ms more than 450 ms after the op's own battle_ms
         -- a hit inside the grace cannot tell the burst hold from a grace that counts from the record alone, so such a run
         records the leg NOT REACHED (red with that reason), never green.
  END    the trance END: `unit <seat> trance0` + a SysTrans START (Special_Trance_End 489) in ONE request: held at the op
         (the seat still wears its trance model, its bit already clear), then the swap BACK at that replay's hit (via hit,
         to false, last.ms == its first_hit_ms) -- the hit past the grace, as HIT.
  DECL   audit 4.8, a DECLINED START swaps at once: `unit <seat> trance1` + a SysTrans START and its END in ONE feed (one
         drain: the START declines `stale`) in ONE request: swaps_by_decline +1, `last` via declined, at once (last.ms -
         last.record_ms under 400: ahead of any grace), stale +1, trance_model true.
  ARRIVE the START-FIRST order (the design: type 1 and type 6 arrive in either order): a SysTrans START + its END (declined
         `stale`) THEN -- the same request -- `unit <seat> trance1`: the burst already over, the sample swaps ON ARRIVAL
         (on_arrival +1, deferred +0, `last` via on-arrival with record_ms -1, trance_model true on the request's state).
  PARK   audit 4.8, a SysTrans START PARKED past 400 ms behind a running replay of the same unit: the seat's Attack (the
         taped num and Speed) on Fang 1, then `unit <seat> trance1`, then the SysTrans START, in ONE request: the START
         waits in the actor's pending slot (its launch_ms - arrive_ms over 400: parked past the grace), the deferral holds
         through it (its own burst in flight), and the swap comes at ITS hit (via hit, its id, last.ms == its first_hit_ms),
         trance_model false on every publish before it, swaps_by_grace +0 and swaps_by_cap +0.
  PARK-CAP the burst OUTLIVES THE CAP (the engine's refinement of amendment 3, for ratification): the same leg, judged only
         when its burst's hit landed more than 2550 ms after the op (else NOT REACHED: a burst that hit inside the cap cannot
         tell its exemption from the cap) -- the swap still at that hit, swaps_by_cap +0.
  BUSY   THE BUSY HOLD (amendment 3): the seat's Attack + `unit <seat> trance1` in ONE request, NO SysTrans: the deferral
         holds while that replay names the unit, then the grace -- via grace at 350-450 ms of battle time after the
         Attack's end (act.guest.last.end_ms; the last busy frame is one frame before it; the publish witness from that
         end too), trance_model false on every publish while the Attack ran. ITS REACH (fix pass 2: harness-busy-
         unguarded): `ran` = the Attack's end_ms - the record_ms -- at most 100 ms (a grace from the record alone lands in
         this window too) or at least the cap minus the grace, 2100 ms (a CORRECT engine swaps by the cap first) records the
         leg NOT REACHED, never green or red on the shape; `ran` is in its detail either way.
  CAP    THE CAP: a LONG replay naming the seat (Garnet's seat's Leviathan, Leviathan__Full, on the seat's wire bit: it
         outlives W3's 4 s) + `unit <seat> trance1` in ONE request: swaps_by_cap +1, `last` via cap at 2500-2550 ms of
         battle time after the record (and on the publish witness), the summon still running at the swap. (The seat may
         be HIDDEN by the summon then: the cap's swap keeps a hidden unit's new model hidden -- `trance_model` still reads
         the worn model.)
  LVR    THE LEVER'S OWN RED (every run): `trancegrace off`, then `unit <seat> trance1`: the pre-s137 timing -- immediate +1,
         deferred +0, trance_model true on the request's own state; GRACE's hold predicate reads False there (the check
         shown failing on a real move); the lever back (left off under COOP_CALIBRATE's lever).
  CONT   THE CONTAINMENT LAW over boot 1: the tripwire (calc_while_booted) +0 -- the stock SysTrans case, the only writer of
         trance_no and the support-ability triggers on a replay's hit, never ran --, ach_held +0, act.guest.faulted +0, no
         'action trance: a step faulted' line, and the block's identity holds (battlewire.act_trance_accounted: deferred ==
         swaps_by_* + moot + dropped + the bits of `pending`).
  TD     the teardown DROPS a deferral: `unit <seat> trance1` + `actbench teardown` (ActDiscardAll, no Leave first) in ONE
         request: dropped +1, `last` {via teardown, swapped false}, pending 0, trance_model false (nothing applied), the
         'action trance: boot summary' line. Then a normal leave.
  -- boot 2 --
  INJECT the END INJECTION's flush: Garnet's seat's Leviathan on the seat (the unit stays named: no grace can fire) +
         `unit <seat> trance1` + `endbench victory` in ONE request: swaps_by_inject +1, `last` via inject, trance_model true
         after the injection, pending 0 (InjectEnd's head swaps every pending deferral by the probe -- the pre-s137 guest
         already wore it; a deferral whose OWN SysTrans burst already plays would wait for its hit instead -- the stand-in's
         test); and THE CONTAINMENT LAW over boot 2: calc_while_booted +0, faulted +0, no new 'a step faulted' line, the
         block's identity.
  INV    THE INVARIANTS after the last leave: gil, the bag, levels, exp, AP, kill counters == the pre-boot snapshot.
  R      `reset` with `trancegrace off` left set: the 'action trance grace lever back' line; RE-READ WITH THE ROLE: `on` true.
NOT PROVEN HERE: enable_trance_glow and trance_no themselves (no harness key publishes either: the containment is judged
through CONT's tripwire and STAT's status bit; the selftest rows and the stand-in pin the rest), the gate falling mid-grace
(`via gate`: the `replay off` lever -- the stand-in's test, a re-sample then resolving the pending change once), a dead
unit's drop (`dead`: a corpse waits for its own burst, dropped at the cap with nothing of its own), a Leave's drop
(`leave`), a fault, the moot resolutions (a bit flipped back before its swap), an unpaired hit (a corpse's own burst), the
fix passes' rules the stand-in's tests pin -- a dead sample mirroring the host's bit (a corpse's END burst swaps nothing),
a corpse whose own burst passed swapping by its decline or end, on arrival at its dead sample, or at the injection's flush
(fix pass 2: rmodel-1), a slot s135's life mask freezes (it waits; its hit swaps nothing: `hit_untrusted`), the catch-up's
on-arrival window, the burst ceiling (8500 ms), a victory injected while the unit's own burst plays (left to its hit or
its end), an unlinked unit, a hidden unit's swap kept hidden, the renderers a mesh-flag hide disabled turned back on
around every s137 swap (fix pass 2: rstock-1 -- the renderers are not published) -- the present colour itself (counted,
not seen), and a real host's trance through the transport (no tape leg, above).

CALIBRATION -- a check that cannot fail is not a check.
  * THE DEPLOYED DLL AT WRITING (s136) -- and any engine before s137: `act.guest.trance` is absent, so P0 is RED and no
    trance op is ever sent; battle 1 still runs. RED, exactly: every check but INI, S0, PRE, TAPE, INV (nothing booted,
    nothing to change). COOP_CALIBRATE=1 there judges exactly that red set as S137-CAL.
  * IN-RUN, on the s137 DLL: LVR is the lever's own red every run (judged GREEN when the swap is immediate; GRACE's hold
    predicate on its state reads False).
    COOP_CALIBRATE=1 pulls `actbench trancegrace off` (the pre-s137 timing) BEFORE boot 1 -- every model change swaps at
    the sample, a SysTrans hit swaps nothing. Predicted reds, exactly: GRACE, STAT, PAUSE, HIT, END, DECL, ARRIVE, PARK,
    PARK-CAP, BUSY, CAP, TD, INJECT (each reads its swap's reason, or the hold at its op -- PAUSE's swap is immediate, before
    any press); GREEN: INI, S0, P0, PROOF, PRE, TAPE, BOOT, LVR, CONT, INV, R. S137-CAL judges that set (the run is red by
    design).
    COOP_CALIBRATE=1 with COOP_TRANCE_CAL=caps runs 6.11's other red instead: no lever, the feed armed with `bbench caps
    0x02` (bit 5 never latched: an old host) -- the same timing, so it must equal the lever red EXACTLY: S137-CAL judges the
    same predicted set (BOOT wants `bit5` false there).
  * THE STAND-IN (tools/harness/fakegame.py, cap `acttrance`) models the timing through battlewire.ActTranceLane -- not the
    sequencer, not this plan: never read S137-CAL offline. Its tests (ff9mapkit/tests/test_harness_netsync.py) evaluate
    ActTranceSelfTest's 21 rows off the stack against the twins, pin the verb, the keys and these tables; the engine is the
    calibration.

RUN:
    py tools/play.py studies/test-harness/scenarios/coop_action_trance.py --field 30602
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_action_trance.py --field 30602
    COOP_CALIBRATE=1 COOP_TRANCE_CAL=caps py tools/play.py studies/test-harness/scenarios/coop_action_trance.py --field 30602
  PowerShell has no per-launch form: a `$env:` value PERSISTS in that shell -- clear them after each run:
    Remove-Item Env:COOP_CALIBRATE, Env:COOP_TRANCE_CAL -ErrorAction SilentlyContinue
"""
from __future__ import annotations

import itertools
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import coop_action_replay as ar                            # noqa: E402 - s134's bench: its reads, cast and boots
import coop_action_hold as hd                              # noqa: E402 - s135's bench: its boots and battle-1 plan

BW = ar.BW
HarnessError = cb.HarnessError

PROBE = cb.R3_PROBES[137]                  # netsync.battle.act.guest.trance: absent = s136 or older (fails closed)
FALLBACK_PROBE = cb.R3_PROBES[136]         # netsync.battle.act.guest.fallback
GUEST_PROBE = cb.R3_PROBES[134]            # netsync.battle.act.guest
HOST_PROBE = cb.R3_PROBES[133]             # netsync.battle.act.host: the in-engine tape (battle 1)
SCENE, GROUP = ar.SCENE, ar.GROUP          # 306 / 4 (Fang x2): the s133-s136 benches' scene
NONCE = 0x5F                               # MARKER: this bench's nonce byte (s134's 0x5C, s135's 0x5D, s136's 0x5E)
#: COOP_CALIBRATE=1's mode: "lever" (`trancegrace off` before boot 1, the default) or "caps" (6.11's other red: the feed's
#: caps 0x02 -- bit 5 never latched)
CAL_MODE = (os.environ.get("COOP_TRANCE_CAL", "lever").strip().lower() or "lever")
CAL_MODES = ("lever", "caps")
FEED_SLOTS = "0x01"                        # `bbench start <wire mask>`: the feed's guest-slot offer
CAPS_BIT5 = "0x22"                         # `bbench caps`: bit 1 (a command-phase-gated host) + bit 5 (action STARTs)
CAPS_NO_BIT5 = "0x02"                      # ...the caps run's: bit 1 alone (an old host: no bit 5)
GRACE_LO, GRACE_HI = BW.ACT_TRANCE_GRACE_MS, BW.ACT_TRANCE_GRACE_MS + 50       # 6.11: 400 +- 50 (never before 400)
CAP_LO, CAP_HI = BW.ACT_TRANCE_CAP_MS, BW.ACT_TRANCE_CAP_MS + 50
BUSY_LO, BUSY_HI = BW.ACT_TRANCE_GRACE_MS - 50, BW.ACT_TRANCE_GRACE_MS + 50   # from the busy replay's END (a frame early)
QUIET_MS = BW.ACT_TRANCE_GRACE_MS + 200    # battle ms between legs: every burst mark older than the 400 ms window (600)
#: BUSY's REACH (fix pass 2: harness-busy-unguarded) -- `ran`, the Attack's end_ms minus the deferral's record_ms: at most
#: BUSY_RUN_MIN_MS cannot tell the last-busy-frame origin from the record (a grace counted from the record alone lands in the
#: window too); at least the cap minus the grace (2100) a CORRECT engine swaps by the cap first. Either way NOT REACHED.
BUSY_RUN_MIN_MS = 100
BUSY_RUN_MAX_MS = BW.ACT_TRANCE_CAP_MS - BW.ACT_TRANCE_GRACE_MS
#: PAUSE (fix pass 2: rtiming-1, audit 3.5 -- the grace is BATTLE time): the pause held this long (wall), and the engine's
#: paused_ms at least PAUSE_MIN_MS over it; the press is s134 PAUSE's verified one (Session.press's own step), riding the
#: record's request so it lands inside the grace
PAUSE_HOLD_S = 2.5
PAUSE_MIN_MS = 2000
PRESS_PAUSE = "press pause 2"
#: one battle frame (30 fps) + a ms of rounding: THE PUBLISH WITNESS's slack (the first publish after a swap is <= 1 frame on)
FRAME_MS = 34
SWAP_S = 6.0                               # a grace / decline swap's publish, at most
REPLAY_S = 20.0                            # a fabricated replay's end, at most
LONG_S = 30.0                              # the long summon's natural end, at most (cleared past it)
PROOF = "action trance selftest:"
PROOF_OK = BW.proof_ok(BW.PROOF_TRANCE, BW.TRANCE_SELFTEST_ROWS).rstrip()
LEG_FAULTS = ar.LEG_FAULTS
_IDS = itertools.count(1)                  # bench ids: unique per process, so unique per boot (no `duplicate`)


# ================================================================================================ the catalogs
def _solo_catalog(calibrate: bool) -> dict:
    c = {
        "S137-INI": "precondition: Memoria.ini [Netsync] Enabled reads 0 (or absent), READ-ONLY -- else NOTHING runs",
        "S137-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
        "S137-P0": f"the engine publishes `{PROBE}` (memoria-patch s137) whole -- exactly the agent's keys, `on` true -- "
                   "else no trance op is ever sent (fails closed)",
        "S137-PROOF": f"the selftest proof block's line reads exactly '{PROOF_OK}' -- no FAIL line",
        "S137-PRE": f"precondition: battle 1 (`battle {SCENE} {GROUP}`) seats Zidane, Vivi and Garnet and 2+ enemies",
        "S137-TAPE": "battle 1's s133 tape carries Zidane's Attack START (kind 3: its num and host Speed)",
        "S137-BOOT": "boot 1 steady, the feed armed: act.guest.trance at rest, bit5 / on / gate as the run wants, the seat "
                     "in its normal model with no Trance status bit",
        "S137-GRACE": "no START: `unit <seat> trance1` -- held at the op (deferred +1, pending, normal model), then via "
                      "grace 400-450 ms of battle time after the record; the normal model on every publish before it",
        "S137-PAUSE": "the grace is BATTLE time: `unit <seat> trance1` + a pause press in one request, paused 2 s+ inside "
                      "the grace -- pending and the normal model on every paused publish; then via grace 400-450 ms of "
                      "battle time after the record, the wall span past the battle span by the pause",
        "S137-STAT": "the containment law at that op: the seat's status carries Trance while its model waits",
        "S137-HIT": "`unit trance1` + a SysTrans START (Activate) in one request: held, then via hit with last.ms == the "
                    "replay's first_hit_ms, no swap before it, grace +0; present +1 after the replay's end",
        "S137-END": "`unit trance0` + a SysTrans START (End) in one request: held in the trance model, then the swap back "
                    "via hit at its first_hit_ms",
        "S137-DECL": "`unit trance1` + a declined SysTrans START (START + END: stale) in one request: via declined at once "
                     "(under 400 ms), swaps_by_decline +1",
        "S137-ARRIVE": "a declined SysTrans START THEN `unit trance1`: the sample swaps on arrival (on_arrival +1, deferred "
                       "+0, record_ms -1)",
        "S137-PARK": "a SysTrans START parked past 400 ms behind the seat's running Attack: the swap at ITS hit (via hit, "
                     "first_hit_ms), grace +0, cap +0",
        "S137-PARK-CAP": "the parked burst OUTLIVES THE CAP: its hit more than 2550 ms after the op (else not reached), the "
                         "swap still at that hit, cap +0",
        "S137-BUSY": "the seat's Attack + `unit trance1`, no SysTrans: held while the Attack names the unit, then via grace "
                     "350-450 ms after the Attack's end",
        "S137-CAP": "a long summon naming the seat + `unit trance1`: via cap 2500-2550 ms after the record, the summon "
                    "still running",
        "S137-LVR": "the lever's own red: `trancegrace off` -- the swap immediate at the op (immediate +1, deferred +0), "
                    "GRACE's hold predicate False there",
        "S137-CONT": "the containment law over boot 1: calc_while_booted +0, ach_held +0, faulted +0, no fault line, the "
                     "block's identity holds",
        "S137-TD": "`unit trance1` + `actbench teardown` in one request: dropped +1 via teardown, nothing applied, the "
                   "summary line",
        "S137-INJECT": "a held deferral + `endbench victory` in one request: swaps_by_inject +1 via inject, the trance model "
                       "after the injection",
        "S137-INV": "the invariants after the last leave: gil, bag, levels, exp, AP, kill counters == the pre-boot snapshot",
        "S137-R": "`reset` with the trance lever set: the 'lever back' line; RE-READ WITH THE ROLE `on` true",
    }
    if calibrate:
        c["S137-CAL"] = ("CALIBRATION: exactly the predicted checks are red -- on an engine without `act.guest.trance` every "
                         "check but INI/S0/PRE/TAPE/INV; on the s137 DLL under `trancegrace off` (or caps 0x02) the "
                         "LEVER set")
    return c


#: the checks that need `act.guest.trance` (not reached together when the probe fails closed)
TRANCE_CHECKS = ("S137-PROOF", "S137-BOOT", "S137-GRACE", "S137-STAT", "S137-PAUSE", "S137-HIT", "S137-END", "S137-DECL",
                 "S137-ARRIVE", "S137-PARK", "S137-PARK-CAP", "S137-BUSY", "S137-CAP", "S137-LVR", "S137-CONT", "S137-TD",
                 "S137-INJECT", "S137-R")
#: COOP_CALIBRATE=1 on an engine without `act.guest.trance` (the deployed s136, or older): all but INI, S0, PRE, TAPE, INV
OLD_PREDICTED = tuple(c for c in _solo_catalog(True) if c not in ("S137-INI", "S137-S0", "S137-PRE", "S137-TAPE",
                                                                    "S137-INV", "S137-CAL"))
#: COOP_CALIBRATE=1 on the s137 DLL: `trancegrace off` before boot 1 (or caps 0x02: bit 5 never latched) -- every model
#: change at the sample, a SysTrans hit swapping nothing
LEVER_PREDICTED = ("S137-GRACE", "S137-STAT", "S137-PAUSE", "S137-HIT", "S137-END", "S137-DECL", "S137-ARRIVE",
                   "S137-PARK", "S137-PARK-CAP", "S137-BUSY", "S137-CAP", "S137-TD", "S137-INJECT")
LEVER_MAYBE: tuple = ()
#: boot 1's legs, in their order (nothing dies; the teardown last)
BOOT_1_LEGS = ("S137-BOOT", "S137-GRACE", "S137-STAT", "S137-PAUSE", "S137-HIT", "S137-END", "S137-DECL", "S137-ARRIVE",
               "S137-PARK", "S137-PARK-CAP", "S137-BUSY", "S137-CAP", "S137-LVR", "S137-CONT", "S137-TD")


def _catalog(calibrate: bool) -> dict:
    return _solo_catalog(calibrate)


def predicted(has_trance: bool) -> tuple:
    """COOP_CALIBRATE=1's predicted reds for the engine FOUND (its `act.guest.trance` key): (predicted, maybe) -- the lever
    run and the caps run predict the SAME set (6.11: the caps red must equal the lever red)."""
    return (LEVER_PREDICTED, LEVER_MAYBE) if has_trance else (OLD_PREDICTED, ())


# ================================================================================================ reads
_num = ar._num
_sub = ar._sub
_guest = ar._guest
_gv = ar._gv
_n = hd._n


def _tr(x) -> dict:
    return _sub(_guest(x), "trance")


def _tv(x, key: str) -> int:
    return _num(_tr(x).get(key)) or 0


def _tlast(x) -> dict:
    v = _tr(x).get("last")
    return v if isinstance(v, dict) else {}


def _glast(x) -> dict:
    v = _guest(x).get("last")
    return v if isinstance(v, dict) else {}


def _tbrief(x) -> str:
    return "act.guest.trance=" + str(cb.pick(_tr(x), "on", "gate", "deferred", "pending", *BW.ACT_TRANCE_RESOLVED_KEYS,
                                             "immediate", "on_arrival", "hit_unpaired", "hit_untrusted", "present", "last"))


#: the counters a leg reads its moves off
TR_COUNTERS = ("deferred", "pending", *BW.ACT_TRANCE_RESOLVED_KEYS, "immediate", "on_arrival", "hit_unpaired",
               "hit_untrusted", "present")


def _tbase(x) -> dict:
    out = {k: _tv(x, k) for k in TR_COUNTERS}
    for k in ("stale", "declined", "started", "ended", "aborted", "faulted", "calc_while_booted", "running"):
        out[k] = _gv(x, k)
    out["ach"] = cb.bend(x).get("ach_held")
    return out


def _tdelta(x, base: dict) -> dict:
    return {k: _tv(x, k) - base.get(k, 0) for k in TR_COUNTERS if k != "pending"}


def _seat(x, ctx: dict) -> tuple:
    """THE SEAT (s134 LESSON 1): Zidane's battle-1 wire -- the selftest stand-in there (coop_action_replay._who) -- as
    (its unit or None, its wire or None)."""
    return ar._who(x, ctx)["zidane"]


def seat_view(u: dict | None) -> dict:
    """The seat's model witness off ONE publish (PURE): {model (trance_model: True / False / None = no key), status_trance
    (the Trance bit of `status`), name, anim}."""
    u = u or {}
    try:
        bits = int(str(u.get("status") or "0"))
    except ValueError:
        bits = 0
    tm = u.get("trance_model")
    return {"model": tm if isinstance(tm, bool) else None, "status_trance": bool(bits & BW.BATTLE_STATUS_TRANCE),
            "name": u.get("name"), "anim": u.get("anim")}


# ================================================================================================ the pure judges
def held_pred(block: dict, base: dict, wire: int, view: dict, want: bool = True) -> bool:
    """A model change HELD at its op (PURE): one more deferral, the wire's bit in `pending`, and the seat still wearing the
    OTHER model (``want`` = the model it waits for). GRACE / HIT / END / PARK / BUSY / CAP read it on the request's own
    state; LVR's in-run red reads it on its state, where it must be False."""
    if not isinstance(block, dict):
        return False
    deferred = _num(block.get("deferred"))
    pending = _num(block.get("pending"))
    return (deferred is not None and deferred == int(base.get("deferred", 0)) + 1 and pending is not None
            and bool(pending & (1 << int(wire))) and view.get("model") is (not want))


def judge_last(last: dict, *, via: str, wire: int, to: bool | None = True, act_id: int | None = None,
               swapped: bool = True) -> tuple:
    """`act.guest.trance.last` names THIS resolution (PURE): its via, the seat's wire, swapped, to, and (``act_id``) the
    replay's id. (ok, detail)."""
    want = {"via": via, "slot": int(wire), "swapped": bool(swapped)}
    if to is not None:
        want["to"] = bool(to)
    if act_id is not None:
        want["id"] = int(act_id)
    bad = {k: (last.get(k), v) for k, v in want.items() if last.get(k) != v}
    return not bad, f"last {cb.pick(last, *BW.ACT_TRANCE_LAST_KEYS)}" + (f"; WRONG {bad}" if bad else "")


def judge_window(last: dict, lo: int, hi: int, *, since: int | None = None) -> tuple:
    """A timer resolution on the ENGINE's clock (PURE): last.ms - ``since`` (default last.record_ms) in [lo, hi]."""
    ms, at = _num(last.get("ms")), _num(last.get("record_ms")) if since is None else _num(since)
    if ms is None or at is None or at < 0:
        return False, f"no timing (ms {last.get('ms')!r}, from {at!r})"
    took = ms - at
    return lo <= took <= hi, f"{took} ms of battle time (want {lo}-{hi})"


def judge_at_hit(last: dict, glast: dict, act_id: int) -> tuple:
    """A swap AT a replay's hit (PURE): `act.guest.last` is that START (id ``act_id``) and the swap's battle ms IS its
    first_hit_ms (the same _actNowMs read). (ok, detail)."""
    hit = _num(glast.get("first_hit_ms"))
    ok = glast.get("id") == act_id and hit is not None and hit >= 0 and _num(last.get("ms")) == hit
    return ok, (f"swap at battle ms {last.get('ms')!r}, the START {glast.get('id')!r}'s first_hit_ms {glast.get('first_hit_ms')!r} "
                f"(want id {act_id}, equal)")


def early_swaps(samples: list, slot: int, act_id: int, to: bool = True) -> list:
    """The publishes that show the seat ALREADY in model ``to`` before replay ``act_id``'s first hit (PURE): [(frame,
    first_hit_ms)] -- empty = no early swap."""
    out = []
    for s in samples:
        gl = _glast(s)
        before = gl.get("id") != act_id or (_num(gl.get("first_hit_ms")) is None or _num(gl.get("first_hit_ms")) < 0)
        if before and seat_view(cb.unit(s, slot)).get("model") is to:
            out.append((cb.frame_of(s), gl.get("first_hit_ms") if gl.get("id") == act_id else None))
    return out


def judge_waited(origin_ms, glast: dict, act_id: int, more_than: int) -> tuple:
    """A replay's hit landed MORE than ``more_than`` battle ms after ``origin_ms`` (PURE) -- the precondition that lets a
    leg tell a hold from a timer that would have fired first (HIT / END: past the grace; PARK-CAP: past the cap). The
    origin is the op's own publish (act.guest.battle_ms on the request's state: never before the record), the hit the
    s134 record's own first_hit_ms -- neither is s137's clock. (ok, detail)."""
    hit, at = _num(glast.get("first_hit_ms")), _num(origin_ms)
    ok = glast.get("id") == act_id and hit is not None and hit >= 0 and at is not None and hit - at > more_than
    took = None if hit is None or at is None or hit < 0 else hit - at
    return ok, f"the START {glast.get('id')!r}'s hit {took!r} ms of battle time after the op (want id {act_id}, > {more_than})"


def judge_flip(samples: list, slot: int, origin_ms, lo: int, hi: int, *, to: bool = True, record_ms=None) -> tuple:
    """THE PUBLISH WITNESS (PURE; s136 LESSON 8 -- a clock the feature does not compute): the first publish whose seat wears
    model ``to``, its act.guest.battle_ms minus ``origin_ms`` within [lo - FRAME_MS, hi + FRAME_MS]; with ``record_ms`` (the
    engine's own record) the origin must not precede it (a record stamped late would read the window short). (ok, detail)."""
    at = _num(origin_ms)
    if at is None or at < 0:
        return False, f"no origin publish (battle_ms {origin_ms!r})"
    rec = _num(record_ms) if record_ms is not None else None
    if record_ms is not None and (rec is None or rec < 0 or at < rec):
        return False, f"the op's publish (battle ms {at}) precedes the engine's record ({record_ms!r})"
    flip = next((s for s in samples if seat_view(cb.unit(s, slot)).get("model") is to), None)
    if flip is None:
        return False, f"no publish shows the seat in model {to} (of {len(samples)})"
    ms = _num(_guest(flip).get("battle_ms"))
    if ms is None:
        return False, "the flip publish carries no act.guest.battle_ms"
    took = ms - at
    return lo - FRAME_MS <= took <= hi + FRAME_MS, (f"the publish witness: the first publish in model {to} at battle ms "
                                                    f"{ms}, {took} ms after the op's {at} (want {lo}-{hi} +- {FRAME_MS})")


def judge_parked(glast: dict, act_id: int, more_than: int = BW.ACT_TRANCE_GRACE_MS) -> tuple:
    """A START that WAITED in its actor's pending slot past the grace (PURE): launch_ms - arrive_ms > ``more_than``."""
    a, lch = _num(glast.get("arrive_ms")), _num(glast.get("launch_ms"))
    ok = glast.get("id") == act_id and a is not None and lch is not None and lch >= 0 and lch - a > more_than
    return ok, f"START {glast.get('id')!r} arrived {a!r}, launched {lch!r} (parked {None if a is None or lch is None else lch - a} ms, want > {more_than})"


def busy_reach(last: dict, glast: dict, act_id: int) -> tuple:
    """BUSY's REACH (PURE; fix pass 2: harness-busy-unguarded): ``ran`` = the Attack's end_ms (``glast``, the s134 record
    of START ``act_id``) minus the deferral's record_ms -- neither is s137's own swap clock. (state, ran): "ok" inside
    (BUSY_RUN_MIN_MS, BUSY_RUN_MAX_MS); "short" at most BUSY_RUN_MIN_MS (a grace counted from the record alone lands in
    BUSY's window too); "long" at least BUSY_RUN_MAX_MS (a correct engine swaps by the cap before the Attack ends); None
    when either is unread (the leg's own check then judges it)."""
    rec, end = _num(last.get("record_ms")), _num(glast.get("end_ms"))
    if glast.get("id") != act_id or rec is None or end is None or rec < 0 or end < 0:
        return None, None
    ran = end - rec
    if ran <= BUSY_RUN_MIN_MS:
        return "short", ran
    if ran >= BUSY_RUN_MAX_MS:
        return "long", ran
    return "ok", ran


def paused_holds(samples: list, slot: int, wire: int, base_paused: int, base_grace: int) -> tuple:
    """THE PAUSE's hold (PURE): of the publishes taken while the diorama was paused (act.guest.paused_ms past
    ``base_paused``), (how many, [the frames that do NOT show the wire's bit in `pending`, the seat in its normal model and
    swaps_by_grace still ``base_grace``])."""
    paused = [s for s in samples if _gv(s, "paused_ms") > base_paused]
    bad = [cb.frame_of(s) for s in paused
           if not (_tv(s, "pending") & (1 << int(wire))) or seat_view(cb.unit(s, slot)).get("model") is not False
           or _tv(s, "swaps_by_grace") != base_grace]
    return len(paused), bad


def judge_pause_span(wall_ms, took, paused, pause_at) -> tuple:
    """THE PAUSE's spans (PURE): the engine's paused_ms rose at least PAUSE_MIN_MS, the pause took hold INSIDE the grace
    (``pause_at``, battle ms from the record to the first paused publish, under GRACE_LO), and the wall span from the op
    to the swap's publish exceeds the battle span (``took``: last.ms - last.record_ms) by at least the pause. (ok,
    detail)."""
    vals = [_num(v) for v in (wall_ms, took, paused, pause_at)]
    if any(v is None for v in vals):
        return False, f"unread span (wall {wall_ms!r}, battle {took!r}, paused_ms {paused!r}, the pause at {pause_at!r})"
    w, t, p, at = vals
    ok = p >= PAUSE_MIN_MS and 0 <= at < GRACE_LO and w - t >= PAUSE_MIN_MS
    return ok, (f"paused_ms +{p} (want >= {PAUSE_MIN_MS}); the pause took hold {at} ms of battle time after the record "
                f"(want under {GRACE_LO}); wall {w} ms vs battle {t} ms (the excess {w - t}, want >= {PAUSE_MIN_MS})")


# ================================================================================================ frames
def _start(actor: int, *, player: bool, cmd: int, sub: int, tar: int, kind: int = BW.VFX_KIND_SPECIAL, num: int = 0,
           speed: int = 5, cursor: int = 0) -> tuple:
    """A fresh bench START (s133's 76-byte record, this bench's nonce) -> (id, bytes)."""
    act_id = next(_IDS)
    flags = (BW.ACTOR_IS_PLAYER if player else 0) | BW.ACTOR_HOST_REWORK | (BW.ACTOR_HOST_FAST if speed >= 3 else 0)
    return act_id, BW.encode_action_start(NONCE, 1, act_id, actor, flags, cmd, sub, tar, cursor, 0, 0, kind, num, -1, speed)


def _end(act_id: int, cmd: int, sub: int) -> bytes:
    return BW.encode_action_end(NONCE, 2, act_id, cmd, sub)


def _systrans(wire: int, *, end: bool = False) -> tuple:
    """The seat's SysTrans START: kind 3 (special), Special_Trance_Activate (257) or _End (489) -- the host-resolved num --,
    its own wire bit as the target (a target 0 declines `target`)."""
    return _start(wire, player=True, cmd=BW.CMD_SYS_TRANS, sub=0, tar=ar._bit(wire), kind=BW.VFX_KIND_SPECIAL,
                  num=BW.SPECIAL_TRANCE_END if end else BW.SPECIAL_TRANCE_ACTIVATE)


def _feed_arg(frames) -> str:
    return BW.act_feed_arg([frames] if isinstance(frames, (bytes, bytearray)) else list(frames))


def _act_verb(g, *args) -> tuple:
    return ar._act_verb(g, *args)


# ================================================================================================ the run
def run(g, field: int = cb.FIELD):
    calibrate = cb.CALIBRATE
    if calibrate and CAL_MODE not in CAL_MODES:
        led = cb.Ledger(g, {"S137-CALMODE": f"COOP_TRANCE_CAL is one of {CAL_MODES}"})
        led.check("S137-CALMODE", False, f"COOP_TRANCE_CAL={CAL_MODE!r} is no calibration mode: one of {CAL_MODES}")
        return
    led = cb.Ledger(g, _solo_catalog(calibrate), finals=("S137-R", "S137-INV", "S137-CAL"))
    ctx = ar._ctx_new()
    ctx["cal_mode"] = CAL_MODE if calibrate else None
    try:
        _run(g, led, field, calibrate, ctx)
    except HarnessError as err:
        g.note(f"the run raised: {str(err)[:400]}")
        led.close(f"not reached: the run raised ({str(err)[:200]})")
    finally:
        g.note(f"logs archived: {ar._archive_logs(g, 'action-trance')}")
        led.close()
        if ctx["ini_ok"]:
            _release(g, led, ctx)
        else:
            led.unreached(("S137-R", "S137-INV"), "the precondition refused the run (S137-INI): nothing was set")
        if calibrate:
            pred, maybe = predicted(bool(ctx["probe"]))
            led.judge_calibration("S137-CAL", pred, maybe)
        led.close(final=True)


def _run(g, led: cb.Ledger, field: int, calibrate: bool, ctx: dict) -> None:
    ok, why = ar._ini_guard(g)
    led.check("S137-INI", ok, why)
    if not ok:
        led.close(f"refused to run: {why}")
        return
    ctx["ini_ok"] = True
    ctx["field"] = field
    mode = ctx.get("cal_mode")
    ok, why = cb.setup(g, field, label=f"R3 s137: the trance burst timing, solo (scene {SCENE} group {GROUP})"
                                       + (f" -- CALIBRATION ({'actbench trancegrace off' if mode == 'lever' else 'bbench caps 0x02'})"
                                          if calibrate else ""))
    led.check("S137-S0", ok, why)
    if not ok:
        led.close(f"the selftest role was refused -- {why}")
        return
    st = g.state
    have = ctx["probe"] = cb.has(st, PROBE)
    diff = sorted(set(_tr(st)) ^ set(BW.ACT_GUEST_TRANCE_SENTINELS))
    led.check("S137-P0", have and not diff and _tr(st).get("on") is True,
              f"act.guest.trance keys {sorted(_tr(st))} (the keys that differ from the agent's: {diff}), on "
              f"{_tr(st).get('on')!r}" if have else
              f"no `{PROBE}` (an engine before s137: no trance op will be sent)")
    g.note(f"probe stage: {cb.stage_note(st)}; act.guest.trance {'present' if have else 'ABSENT'}; act.guest.fallback "
           f"{'present' if cb.has(st, FALLBACK_PROBE) else 'ABSENT'}")
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
        led.unreached([c for c in TRANCE_CHECKS if c != "S137-R"],
                      f"`{PROBE}` is absent: an engine before s137 (the probe fails closed; no trance op was sent)")
        return
    if calibrate and mode == "lever":
        _act_verb(g, "trancegrace", "off")
        ctx["levers_set"] = True
        g.note("CALIBRATION: `actbench trancegrace off` -- the pre-s137 timing for every leg below")
    elif calibrate:
        g.note("CALIBRATION: the feed armed with `bbench caps 0x02` -- bit 5 never latched (an old host), every leg below")
    _boot_1(g, led, field, ctx)
    _boot_inject(g, led, field, ctx)
    if calibrate and mode == "lever":
        _act_verb(g, "trancegrace", "on")


def _leg_proof(g, led: cb.Ledger) -> None:
    proof = cb.poll(g, lambda s: cb.count(cb.log_lines(g), PROOF) >= 1, 8.0, "the proof block's action-trance line")
    lines = [ln for ln in cb.log_lines(g) if PROOF in ln]
    last = lines[-1] if lines else ""
    failed = [ln for ln in lines if "action trance selftest: FAIL" in ln]
    led.check("S137-PROOF", proof is not None and PROOF_OK in last and not failed,
              (last.split("|", 2)[-1].strip()[-300:] if last else "no 'action trance selftest' line (an engine before "
                                                                  "s137 has no ActTranceSelfTest)")
              + (f"; FAIL lines: {len(failed)}" if failed else "") + f"; want '{PROOF_OK}'")


# ------------------------------------------------------------------------------------------------ battle 1
def _battle_1(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    """coop_action_fallback's battle 1 (`actbench tape rec` + `battle 306 <group>`, the plan that cannot end the fight
    early), its result screen cleared with Session.leave_battle(stop_on_field=True) (s134 LESSON 4), the tape paged out and
    read offline (coop_action_hold.read_tape): Zidane's Attack START -- the PARK and BUSY legs' running replay."""
    host = cb.has(g.state, HOST_PROBE)
    if host:
        _act_verb(g, "tape", "rec")
    if cb.poll(g, lambda s: cb.free(s) and s.ui_state == "FieldHUD" and not s.in_battle, 30.0, "a playable field") is None:
        led.unreached(("S137-PRE", "S137-TAPE"), f"not on a playable field before battle 1 (ui {g.state.ui_state!r})")
        return
    try:
        g.start_battle(SCENE, group=GROUP)
    except HarnessError as err:
        led.unreached(("S137-PRE", "S137-TAPE"), f"`battle {SCENE} {GROUP}` did not start: {str(err)[:200]}")
        return
    _samples, en = cb.watch(g, lambda s: s.commands_enabled, ar.INTRO_S)
    st = en or g.state
    names = {k: ar._unit_named(st, k) for k in ("zidane", "vivi", "garnet")}
    foes = cb.units(st, player=False)
    led.check("S137-PRE", all(names.values()) and len(foes) >= 2,
              f"party {[(u.get('slot'), u.get('name')) for u in cb.units(st, player=True)]}; enemies "
              f"{[(u.get('slot'), u.get('name'), u.get('id')) for u in foes]}")
    ctx["slots"] = {k: (int(u["slot"]) if u else None) for k, u in names.items()}
    for k in ("zidane", "vivi", "garnet"):
        ctx[f"{k}_wire"] = ar._wire_of(st, names[k])
    ctx["fang1_wire"] = ar._who(st)["fang1"][1]
    done, extra = {"attack": False, "potion": False}, 0
    z, gar = ctx["slots"].get("zidane"), ctx["slots"].get("garnet")
    for _turn in range(40):
        if done["attack"] and done["potion"] and extra >= 2:
            break
        try:
            slot = g.wait_turn(timeout=ar.TURN_S)
        except HarnessError as err:
            g.note(f"battle 1 stopped asking: {str(err)[:160]}")
            break
        s = g.state
        try:
            if slot == z and not done["attack"]:
                ally = ar._sturdiest_ally(s, slot)
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
            g.fight(timeout=ar.FIGHT_S, finish=False)
    except HarnessError as err:
        g.note(f"battle 1's fight did not finish: {str(err)[:200]}")
    hd._finish(g)
    if not host:
        led.check("S137-TAPE", False, f"no `{HOST_PROBE}`: an engine before s133 records no action tape")
        return
    _act_verb(g, "tape", "stop")
    t = _sub(ar._host(cb.poll(g, lambda s: _sub(ar._host(s), "tape").get("state") == "stopped", 3.0, "the tape stopped")
                      or g.state), "tape")
    frames, why = ar._dump_all(g, _num(t.get("frames")) or 0)
    ctx["tape"] = hd.read_tape(frames, ctx)
    tp = ctx["tape"]
    led.check("S137-TAPE", not why and tp.get("attack") is not None,
              why or f"{len(frames)} frame(s); Zidane's Attack START {tp.get('attack')}; the plan {ctx.get('plan')}")


# ------------------------------------------------------------------------------------------------ the boots
def _arm(g, ctx: dict) -> tuple:
    """THE STAGE-8 FEED ARMED (6.11 / review replay F6 / audit 4.8 Leg K): `bbench start 0x01` then `bbench caps 0x22`
    (0x02 in the caps calibration: no bit 5) -- the latch read when bit 5 is wanted, then ten frames (the feed's lane edge
    marks the next bench drain a backlog). (ok, why)."""
    caps = CAPS_NO_BIT5 if ctx.get("cal_mode") == "caps" else CAPS_BIT5
    a, wa = cb.try_ns(g, "bbench", "start", FEED_SLOTS)
    b, wb = cb.try_ns(g, "bbench", "caps", caps)
    if not (a and b):
        return False, f"the feed did not arm: bbench start {wa or 'ok'}; bbench caps {wb or 'ok'}"
    if caps == CAPS_BIT5:
        if cb.poll(g, lambda s: _guest(s).get("bit5") is True, 3.0, "the bit-5 latch") is None:
            return False, f"bit 5 never latched (act.guest.bit5 {_guest(g.state).get('bit5')!r}, host_caps " \
                          f"{_guest(g.state).get('host_caps')!r})"
    else:
        g.wait_frames(20)
    g.wait_frames(10)
    return True, f"bbench start {FEED_SLOTS} + caps {caps}"


def _disarm(g) -> None:
    cb.try_ns(g, "bbench", "stop")


def _boot_1(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    st, why = hd._boot(g, field)
    if st is None:
        led.unreached(BOOT_1_LEGS, f"boot 1 failed: {why}")
        return
    try:
        ok, awhy = _arm(g, ctx)
        g.note(f"boot 1: {awhy}")
        st = g.state
        ctx["boot1_base"] = _tbase(st)
        su, sw = _seat(st, ctx)
        view = seat_view(su)
        want_on = ctx.get("cal_mode") != "lever"
        want_bit5 = ctx.get("cal_mode") != "caps"
        tr = _tr(st)
        rest = all(_tv(st, k) == 0 for k in TR_COUNTERS) and tr.get("last") is None
        led.check("S137-BOOT", ok and tr != {} and rest and tr.get("on") is want_on
                  and _guest(st).get("bit5") is want_bit5 and tr.get("gate") is (want_on and want_bit5)
                  and su is not None and view["model"] is False and not view["status_trance"],
                  f"{awhy}; {_tbrief(st)}; bit5 {_guest(st).get('bit5')!r} (want {want_bit5}), on want {want_on}, gate "
                  f"want {want_on and want_bit5}; the seat: wire {sw}, slot {su.get('slot') if su else None}, "
                  f"{view} (a selftest diorama seats the selftest mirror's stand-in here -- its own model, read off the unit)")
        if not ok or su is None or sw is None:
            led.unreached(BOOT_1_LEGS, f"no armed feed or no seat ({awhy}; seat wire {sw})")
            return
        ctx["seat_slot"], ctx["seat_wire"] = int(su["slot"]), int(sw)
        for ids, leg in ((("S137-GRACE", "S137-STAT"), _leg_grace), (("S137-PAUSE",), _leg_pause), (("S137-HIT",), _leg_hit),
                         (("S137-END",), _leg_end),
                         (("S137-DECL",), _leg_decl), (("S137-ARRIVE",), _leg_arrive),
                         (("S137-PARK", "S137-PARK-CAP"), _leg_park),
                         (("S137-BUSY",), _leg_busy), (("S137-CAP",), _leg_cap), (("S137-LVR",), _leg_lvr),
                         (("S137-CONT",), _leg_cont), (("S137-TD",), _leg_td)):
            hd._guard(led, ids, leg, g, led, ctx)
    except LEG_FAULTS as err:
        ar._faulted(led, BOOT_1_LEGS, err)
    finally:
        led.unreached(BOOT_1_LEGS, "boot 1 ended before this leg")
        _disarm(g)
        hd._out(g, field)


def _quiet(g, timeout: float = LONG_S):
    """QUIET: nothing runs, queued or waits, nothing pending -- then QUIET_MS of battle time (every burst mark older than
    the 400 ms on-arrival window). The state or None."""
    st = cb.poll(g, lambda s: _gv(s, "running") == 0 and _gv(s, "queued") == 0 and _gv(s, "waiting") == 0
                 and _gv(s, "inbox") == 0 and _tv(s, "pending") == 0, timeout, "the legs' replays and deferrals at rest")
    if st is None:
        _act_verb(g, "clear")
        st = cb.poll(g, lambda s: _gv(s, "running") == 0 and _tv(s, "pending") == 0, 8.0, "the clear")
        if st is None:
            return None
    at = _gv(st, "battle_ms")
    return cb.poll(g, lambda s: _gv(s, "battle_ms") >= at + QUIET_MS, 5.0, f"{QUIET_MS} ms of battle time")


def _reset_seat(g, ctx: dict) -> None:
    """The seat back to its normal model with no Trance bit (`unit <seat> trance0`; the grace or the lever swaps it), then
    QUIET."""
    slot, wire = ctx["seat_slot"], ctx["seat_wire"]
    v = seat_view(cb.unit(g.state, slot))
    if v["model"] or v["status_trance"]:
        _act_verb(g, "unit", wire, "trance0")
        cb.poll(g, lambda s: seat_view(cb.unit(s, slot))["model"] is False and _tv(s, "pending") == 0, SWAP_S,
                "the seat back in its normal model")
    _quiet(g)


def _batched(g, *steps) -> tuple:
    """ONE request (the agent runs each next step Block(2) frames on): (the request's own state or None, why)."""
    try:
        g.send(*steps, timeout=20.0)
        return g.state, ""
    except HarnessError as err:
        return None, f"the batched request was refused: {str(err)[:300]}"


def _unit_step(ctx: dict, state: str) -> str:
    return f"netsync actbench unit {ctx['seat_wire']} {state}"


def _feed_step(frames) -> str:
    return f"netsync actbench feed {_feed_arg(frames)}"


# ---- boot 1
def _leg_grace(g, led: cb.Ledger, ctx: dict) -> None:
    """GRACE (6.11's no-START leg) + STAT (the status follows at the op)."""
    _quiet(g)
    slot, wire = ctx["seat_slot"], ctx["seat_wire"]
    base = _tbase(g.state)
    x0, why = _batched(g, _unit_step(ctx, "trance1"))
    if x0 is None:
        led.unreached(("S137-GRACE", "S137-STAT"), why)
        return
    v0 = seat_view(cb.unit(x0, slot))
    held = held_pred(_tr(x0), base, wire, v0)
    samples, x = cb.watch_from(g, x0, lambda s: _tv(s, "swaps_by_grace") > base["swaps_by_grace"]
                               or _tv(s, "immediate") > base["immediate"] or _tv(s, "pending") == 0, SWAP_S)
    x = x or g.state
    g.wait_frames(3)
    after = seat_view(cb.unit(g.state, slot))
    last = _tlast(x)
    lok, ldetail = judge_last(last, via="grace", wire=wire, to=True)
    wok, wdetail = judge_window(last, GRACE_LO, GRACE_HI)
    fok, fdetail = judge_flip(list(samples) + [x], slot, _gv(x0, "battle_ms"), GRACE_LO, GRACE_HI,
                              record_ms=last.get("record_ms"))
    before = [cb.frame_of(s) for s in samples if _tv(s, "swaps_by_grace") == base["swaps_by_grace"]
              and seat_view(cb.unit(s, slot)).get("model") is True]
    led.check("S137-GRACE", held and lok and wok and fok and not before and after["model"] is True
              and _tv(x, "swaps_by_grace") == base["swaps_by_grace"] + 1,
              f"held at the op {held} ({_tbrief(x0)}; the seat {v0}); {ldetail}; {wdetail}; {fdetail}; the trance model "
              f"before the swap on {before[:4]}; after {after}; delta {_tdelta(x, base)}")
    led.check("S137-STAT", v0["status_trance"] and v0["model"] is False and after["status_trance"] and after["model"],
              f"at the op: status Trance {v0['status_trance']}, the model {v0['model']!r} (want the bit, the normal model); "
              f"after the swap: {after}")
    _reset_seat(g, ctx)


def _leg_pause(g, led: cb.Ledger, ctx: dict) -> None:
    """PAUSE (fix pass 2: rtiming-1, audit 3.5 -- the grace is BATTLE time): `unit <seat> trance1` + s134 PAUSE's verified
    press in ONE request (the press lands Block(2) frames on: inside the grace), the diorama held paused PAUSE_HOLD_S, then
    unpaused with s134's retry (never a paused diorama left to the legs after it)."""
    _quiet(g)
    slot, wire = ctx["seat_slot"], ctx["seat_wire"]
    base = _tbase(g.state)
    base_paused = _gv(g.state, "paused_ms")
    t0 = time.time()
    x0, why = _batched(g, _unit_step(ctx, "trance1"), PRESS_PAUSE)
    on = off = None
    retries = 0
    flip_at = None
    held_samples: list = []
    try:
        if x0 is None:
            led.check("S137-PAUSE", False, f"not reached: {why}")
            return
        v0 = seat_view(cb.unit(x0, slot))
        held = held_pred(_tr(x0), base, wire, v0)
        on = cb.poll(g, lambda s: _gv(s, "paused_ms") > base_paused, 3.0, "the pause taking effect (paused_ms rising)")
        held_samples = cb.hold_for(g, PAUSE_HOLD_S)
        g.press("pause", 2)
        off = ar._unpaused(g)
        while off is None and retries < 3:                 # [s134 review harness-6] never leave the legs a paused diorama
            retries += 1
            g.press("pause", 2)
            off = ar._unpaused(g)

        def _flipped(s):
            return seat_view(cb.unit(s, slot))["model"] is True or _tv(s, "pending") == 0
        _samples, x = cb.watch_from(g, off, _flipped, SWAP_S) if off is not None else ([], None)
        flip_at = time.time() if x is not None else None
        x = x or g.state
        last = _tlast(x)
        lok, ldetail = judge_last(last, via="grace", wire=wire, to=True)
        wok, wdetail = judge_window(last, GRACE_LO, GRACE_HI)
        n_paused, bad = paused_holds(([on] if on is not None else []) + list(held_samples), slot, wire, base_paused,
                                     base["swaps_by_grace"])
        wall_ms = int((flip_at - t0) * 1000) if flip_at is not None else None
        took = (_num(last.get("ms")) - _num(last.get("record_ms"))) if _num(last.get("ms")) is not None and \
            _num(last.get("record_ms")) is not None else None
        pause_at = (_gv(on, "battle_ms") - _num(last.get("record_ms"))) if on is not None and \
            _num(last.get("record_ms")) is not None else None
        sok, sdetail = judge_pause_span(wall_ms, took, _gv(x, "paused_ms") - base_paused, pause_at)
        presses = ("the first press never paused (paused_ms flat) -- " if on is None else "") + \
            (f"the unpause took {retries} extra press(es) -- " if retries and off is not None else "") + \
            ("the diorama NEVER unpaused (battle_ms flat after 4 presses) -- " if off is None else "")
        after = seat_view(cb.unit(x, slot))
        detail = (f"{presses}held at the op {held} (the seat {v0}); {n_paused} paused publish(es), off the hold on "
                  f"{bad[:4]}; {ldetail}; {wdetail}; {sdetail}; after {after}; delta {_tdelta(x, base)}")
        if held and on is not None and pause_at is not None and pause_at >= GRACE_LO:
            # the pause took hold past the grace's own 400 ms: this run cannot tell a battle-time grace from a wall one
            led.unreached(("S137-PAUSE",), f"the pause took hold after the grace could fire: {detail}")
            return
        led.check("S137-PAUSE", held and on is not None and off is not None and retries == 0 and n_paused >= 10
                  and not bad and lok and wok and sok and after["model"] is True
                  and _tv(x, "swaps_by_grace") == base["swaps_by_grace"] + 1, detail)
    finally:
        if off is None:                                    # never verified unpaused: never leave the legs a paused diorama
            _ensure_unpaused(g)
        _reset_seat(g, ctx)


def _ensure_unpaused(g) -> None:
    """[s134 review harness-6] never leave the legs a paused diorama: when battle_ms does not advance, press pause until it
    does (at most 4 presses, each verified as s134 PAUSE's). A no-op outside a battle."""
    bm = _num(_guest(g.state).get("battle_ms"))
    if not (g.state.in_battle or (bm is not None and bm >= 0)) or ar._unpaused(g) is not None:
        return
    for _ in range(4):
        g.press("pause", 2)
        if ar._unpaused(g) is not None:
            return
    g.note("PAUSE: the diorama never unpaused after 4 more presses (battle_ms flat)")


def _hit_leg(g, led: cb.Ledger, ctx: dict, cid: str, *, to: bool) -> None:
    """HIT (to True: Activate) / END (to False: End): the record + the SysTrans START in ONE request; the swap at ITS hit."""
    slot, wire = ctx["seat_slot"], ctx["seat_wire"]
    base = _tbase(g.state)
    act_id, s = _systrans(wire, end=not to)
    x0, why = _batched(g, _unit_step(ctx, "trance1" if to else "trance0"), _feed_step(s))
    if x0 is None:
        led.check(cid, False, f"not reached: {why}")
        return
    v0 = seat_view(cb.unit(x0, slot))
    held = held_pred(_tr(x0), base, wire, v0, want=to)
    samples, x = cb.watch_from(g, x0, lambda s: _tv(s, "swaps_by_hit") > base["swaps_by_hit"]
                               or _tv(s, "pending") == 0, REPLAY_S)
    x = x or g.state
    last = _tlast(x)
    lok, ldetail = judge_last(last, via="hit", wire=wire, to=to, act_id=act_id)
    hok, hdetail = judge_at_hit(last, _glast(x), act_id)
    early = early_swaps(samples, slot, act_id, to)
    end = cb.poll(g, lambda s: _gv(s, "running") == 0 and _n(_glast(s).get("end_ms"), -1) >= 0, REPLAY_S,
                  "the replay's end")
    y = end or g.state
    g.wait_frames(3)
    y = g.state
    after = seat_view(cb.unit(y, slot))
    present = _tv(y, "present") - base["present"]
    waited, wdetail = judge_waited(_gv(x0, "battle_ms"), _glast(y), act_id, GRACE_HI)
    ok = held and lok and hok and not early and after["model"] is to and _tv(x, "swaps_by_hit") == base["swaps_by_hit"] + 1 \
        and _tv(x, "swaps_by_grace") == base["swaps_by_grace"] and _tv(x, "swaps_by_cap") == base["swaps_by_cap"]
    if to:
        ok = ok and present == 1
    detail = (f"held at the op {held} (the seat {v0}); {ldetail}; {hdetail}; early swaps {early[:4]}; {wdetail} (the grace "
              f"is {BW.ACT_TRANCE_GRACE_MS}); after {after}; present +{present} after the replay's end (want +1 for the "
              f"Activate leg: stock's SysTrans finish); delta {_tdelta(y, base)}; {ar._brief(y)}")
    if ok and not waited:
        # (fix pass: harness-hit-not-discriminating) a hit inside the grace: a grace from the record alone swaps there too
        led.unreached((cid,), f"the hit came inside the grace -- this leg cannot tell the burst hold from the grace: "
                              f"{detail}")
        return
    led.check(cid, ok, detail)


def _leg_hit(g, led: cb.Ledger, ctx: dict) -> None:
    _quiet(g)
    _hit_leg(g, led, ctx, "S137-HIT", to=True)
    _quiet(g)                                              # (END swaps it back at its own hit)


def _leg_end(g, led: cb.Ledger, ctx: dict) -> None:
    slot = ctx["seat_slot"]
    v = seat_view(cb.unit(g.state, slot))
    if not (v["model"] and v["status_trance"]):
        # the seat must wear its trance model with the bit set first (HIT left it there, unless HIT was red): put it there
        _act_verb(g, "unit", ctx["seat_wire"], "trance1")
        cb.poll(g, lambda s: seat_view(cb.unit(s, slot))["model"] is True and _tv(s, "pending") == 0, SWAP_S,
                "the seat in its trance model")
        _quiet(g)
    v = seat_view(cb.unit(g.state, slot))
    if not v["model"]:
        led.check("S137-END", False, f"not reached: the seat never wore its trance model ({v}; {_tbrief(g.state)})")
        _reset_seat(g, ctx)
        return
    _hit_leg(g, led, ctx, "S137-END", to=False)
    _reset_seat(g, ctx)


def _leg_decl(g, led: cb.Ledger, ctx: dict) -> None:
    slot, wire = ctx["seat_slot"], ctx["seat_wire"]
    base = _tbase(g.state)
    act_id, s = _systrans(wire)
    x0, why = _batched(g, _unit_step(ctx, "trance1"), _feed_step([s, _end(act_id, BW.CMD_SYS_TRANS, 0)]))
    if x0 is None:
        led.check("S137-DECL", False, f"not reached: {why}")
        return
    samples, x = cb.watch_from(g, x0, lambda s: _tv(s, "swaps_by_decline") > base["swaps_by_decline"]
                               or _tv(s, "pending") == 0, SWAP_S)
    x = x or g.state
    last = _tlast(x)
    lok, ldetail = judge_last(last, via="declined", wire=wire, to=True)
    wok, wdetail = judge_window(last, 0, BW.ACT_TRANCE_GRACE_MS - 1)
    after = seat_view(cb.unit(x, slot))
    led.check("S137-DECL", lok and wok and _tv(x, "swaps_by_decline") == base["swaps_by_decline"] + 1
              and _gv(x, "stale") == base["stale"] + 1 and after["model"] is True
              and _tv(x, "swaps_by_grace") == base["swaps_by_grace"],
              f"{ldetail}; at once: {wdetail}; stale +{_gv(x, 'stale') - base['stale']} ({_guest(x).get('declined_why')!r}); "
              f"after {after}; delta {_tdelta(x, base)}")
    _reset_seat(g, ctx)


def _leg_arrive(g, led: cb.Ledger, ctx: dict) -> None:
    slot, wire = ctx["seat_slot"], ctx["seat_wire"]
    base = _tbase(g.state)
    act_id, s = _systrans(wire)
    x0, why = _batched(g, _feed_step([s, _end(act_id, BW.CMD_SYS_TRANS, 0)]), _unit_step(ctx, "trance1"))
    if x0 is None:
        led.check("S137-ARRIVE", False, f"not reached: {why}")
        return
    g.wait_frames(3)
    x = g.state
    last = _tlast(x)
    lok, ldetail = judge_last(last, via="on-arrival", wire=wire, to=True)
    v0 = seat_view(cb.unit(x0, slot))
    d = _tdelta(x, base)
    led.check("S137-ARRIVE", lok and last.get("record_ms") == -1 and d["on_arrival"] == 1 and d["deferred"] == 0
              and v0["model"] is True and _gv(x, "stale") == base["stale"] + 1,
              f"{ldetail}; on the request's own state the seat {v0}; delta {d}; stale +{_gv(x, 'stale') - base['stale']}")
    _reset_seat(g, ctx)


def _attack_start(x, ctx: dict) -> tuple:
    """The seat's Attack on Fang 1 (kind 3, the TAPED num and host Speed): (id, bytes) or (None, why)."""
    fw = ar._who(x, ctx)["fang1"][1]
    att = (ctx.get("tape") or {}).get("attack")
    if fw is None or att is None:
        return None, f"no Fang 1 ({fw}) or no taped Attack ({att})"
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    speed = att.get("speed") if isinstance(att.get("speed"), int) else 5
    return _start(ctx["seat_wire"], player=True, cmd=acmd, sub=asub, tar=ar._bit(fw), kind=BW.VFX_KIND_SPECIAL,
                  num=att["num"], speed=speed)


def _leg_park(g, led: cb.Ledger, ctx: dict) -> None:
    slot, wire = ctx["seat_slot"], ctx["seat_wire"]
    a_id, a = _attack_start(g.state, ctx)
    if a_id is None:
        led.check("S137-PARK", False, f"not reached: {a}")
        return
    base = _tbase(g.state)
    s_id, s = _systrans(wire)
    x0, why = _batched(g, _feed_step(a), _unit_step(ctx, "trance1"), _feed_step(s))
    if x0 is None:
        led.check("S137-PARK", False, f"not reached: {why}")
        return
    v0 = seat_view(cb.unit(x0, slot))
    held = held_pred(_tr(x0), base, wire, v0)
    samples, x = cb.watch_from(g, x0, lambda s: _tv(s, "pending") == 0, REPLAY_S)
    x = x or g.state
    last = _tlast(x)
    lok, ldetail = judge_last(last, via="hit", wire=wire, to=True, act_id=s_id)
    hok, hdetail = judge_at_hit(last, _glast(x), s_id)
    pok, pdetail = judge_parked(_glast(x), s_id)
    early = early_swaps(samples, slot, s_id, True)
    park_ok = held and lok and hok and pok and not early and _tv(x, "swaps_by_grace") == base["swaps_by_grace"] \
        and _tv(x, "swaps_by_cap") == base["swaps_by_cap"]
    led.check("S137-PARK", park_ok,
              f"held at the op {held} (the seat {v0}); {pdetail}; {ldetail}; {hdetail}; early swaps {early[:4]}; delta "
              f"{_tdelta(x, base)}; {ar._brief(x)}")
    # PARK-CAP (fix pass: timing-6): the burst's exemption from the cap, judged only when its hit came past the cap -- read
    # the hit off the s134 record even when the swap came earlier (a cap or a grace that cut the burst)
    y = cb.poll(g, lambda s: _glast(s).get("id") == s_id and _n(_glast(s).get("first_hit_ms"), -1) >= 0, REPLAY_S,
                "the parked burst's hit") or g.state
    reached, rdetail = judge_waited(_gv(x0, "battle_ms"), _glast(y), s_id, CAP_HI)
    detail = f"{rdetail}; {ldetail}; cap +{_tv(x, 'swaps_by_cap') - base['swaps_by_cap']}"
    if park_ok and not reached:
        led.unreached(("S137-PARK-CAP",), f"the burst hit inside the cap -- this leg cannot tell its exemption from the cap: "
                                          f"{detail}")
    else:
        led.check("S137-PARK-CAP", park_ok and reached, detail)
    _reset_seat(g, ctx)


def _leg_busy(g, led: cb.Ledger, ctx: dict) -> None:
    slot, wire = ctx["seat_slot"], ctx["seat_wire"]
    a_id, a = _attack_start(g.state, ctx)
    if a_id is None:
        led.check("S137-BUSY", False, f"not reached: {a}")
        return
    base = _tbase(g.state)
    x0, why = _batched(g, _feed_step(a), _unit_step(ctx, "trance1"))
    if x0 is None:
        led.check("S137-BUSY", False, f"not reached: {why}")
        return
    v0 = seat_view(cb.unit(x0, slot))
    held = held_pred(_tr(x0), base, wire, v0)
    samples, x = cb.watch_from(g, x0, lambda s: _tv(s, "pending") == 0, REPLAY_S)
    x = x or g.state
    last, gl = _tlast(x), _glast(x)
    lok, ldetail = judge_last(last, via="grace", wire=wire, to=True)
    wok, wdetail = judge_window(last, BUSY_LO, BUSY_HI, since=gl.get("end_ms") if gl.get("id") == a_id else None)
    fok, fdetail = judge_flip(list(samples) + [x], slot, gl.get("end_ms") if gl.get("id") == a_id else None, BUSY_LO,
                              BUSY_HI)
    while_ran = [cb.frame_of(s) for s in samples if _gv(s, "running") >= 1 and seat_view(cb.unit(s, slot))["model"]]
    reach, ran = busy_reach(last, gl, a_id)
    detail = (f"held at the op {held}; {ldetail}; after the Attack's end (id {gl.get('id')!r}, end_ms {gl.get('end_ms')!r}; "
              f"ran {ran!r} ms of battle time after the record): {wdetail}; {fdetail}; the trance model while it ran on "
              f"{while_ran[:4]}; delta {_tdelta(x, base)}")
    # (fix pass 2: harness-busy-unguarded) BUSY's verdict hangs on how long the Attack ran after the record: too short and a
    # grace from the record alone lands in this window too; too long and a CORRECT engine swaps by the cap first
    if reach == "short":
        led.unreached(("S137-BUSY",), f"the Attack ended too soon after the record to tell the last-busy-frame origin from "
                                      f"the record (ran <= {BUSY_RUN_MIN_MS}): {detail}")
    elif reach == "long":
        led.unreached(("S137-BUSY",), f"the Attack outlived the cap's window -- a correct engine swaps by the cap here "
                                      f"(ran >= {BUSY_RUN_MAX_MS}): {detail}")
    else:
        led.check("S137-BUSY", held and lok and wok and fok and gl.get("id") == a_id and not while_ran
                  and _tv(x, "swaps_by_grace") == base["swaps_by_grace"] + 1, detail)
    _reset_seat(g, ctx)


def _summon_start(x, ctx: dict) -> tuple:
    """Garnet's seat's LONG summon (SummonGarnet / Leviathan, Leviathan__Full: it outlives W3's 4 s) on the seat's wire
    bit: a running replay that NAMES the seat (a target) for longer than the cap. (id, bytes) or (None, why)."""
    gw = ar._who(x, ctx)["garnet"][1]
    if gw is None:
        return None, "no Garnet seat"
    return _start(gw, player=True, cmd=BW.CMD_SUMMON_GARNET, sub=BW.ABILITY_LEVIATHAN_ID, tar=ar._bit(ctx["seat_wire"]),
                  kind=BW.VFX_KIND_SPECIAL, num=BW.SPECIAL_LEVIATHAN_FULL, cursor=0)


def _leg_cap(g, led: cb.Ledger, ctx: dict) -> None:
    slot, wire = ctx["seat_slot"], ctx["seat_wire"]
    l_id, summon = _summon_start(g.state, ctx)
    if l_id is None:
        led.check("S137-CAP", False, f"not reached: {summon}")
        return
    base = _tbase(g.state)
    x0, why = _batched(g, _feed_step(summon), _unit_step(ctx, "trance1"))
    if x0 is None:
        led.check("S137-CAP", False, f"not reached: {why}")
        return
    v0 = seat_view(cb.unit(x0, slot))
    held = held_pred(_tr(x0), base, wire, v0)
    samples, x = cb.watch_from(g, x0, lambda s: _tv(s, "pending") == 0, REPLAY_S)
    x = x or g.state
    last = _tlast(x)
    lok, ldetail = judge_last(last, via="cap", wire=wire, to=True)
    wok, wdetail = judge_window(last, CAP_LO, CAP_HI)
    fok, fdetail = judge_flip(list(samples) + [x], slot, _gv(x0, "battle_ms"), CAP_LO, CAP_HI,
                              record_ms=last.get("record_ms"))
    running = _gv(x, "running") >= 1 and _glast(x).get("id") == l_id and _n(_glast(x).get("end_ms"), -1) < 0
    led.check("S137-CAP", held and lok and wok and fok and running and _tv(x, "swaps_by_cap") == base["swaps_by_cap"] + 1,
              f"held at the op {held}; {ldetail}; {wdetail}; {fdetail}; the summon (id {l_id}) still running at the swap "
              f"{running} ({cb.pick(_glast(x), 'id', 'state', 'launch_ms', 'end_ms')}); delta {_tdelta(x, base)}")
    _reset_seat(g, ctx)


def _leg_lvr(g, led: cb.Ledger, ctx: dict) -> None:
    """THE LEVER'S OWN RED: `trancegrace off`, `unit <seat> trance1` -- immediate; GRACE's hold predicate False there."""
    slot, wire = ctx["seat_slot"], ctx["seat_wire"]
    s1, w1 = _act_verb(g, "trancegrace", "off")
    try:
        base = _tbase(g.state)
        x0, why = _batched(g, _unit_step(ctx, "trance1"))
        if s1 is None or x0 is None:
            led.check("S137-LVR", False, f"not reached: `trancegrace off` {w1 or 'ok'}; {why}")
            return
        v0 = seat_view(cb.unit(x0, slot))
        red = held_pred(_tr(x0), base, wire, v0)
        d = _tdelta(x0, base)
        led.check("S137-LVR", red is False and d["immediate"] == 1 and d["deferred"] == 0 and v0["model"] is True
                  and _tlast(x0).get("via") == "immediate",
                  f"on the op's own state: the seat {v0}; GRACE's hold predicate read {red!r} (want False); delta {d}; "
                  f"last {cb.pick(_tlast(x0), *BW.ACT_TRANCE_LAST_KEYS)}")
    finally:
        _act_verb(g, "trancegrace", "off" if ctx.get("levers_set") else "on")   # (COOP_CALIBRATE's lever stays pulled)
        _reset_seat(g, ctx)


def _leg_cont(g, led: cb.Ledger, ctx: dict) -> None:
    x = g.state
    b = ctx.get("boot1_base") or {}
    lines = [ln for ln in cb.log_lines(g) if BW.LOG_TRANCE_FAULTED.split("] ", 1)[1].split(" (", 1)[0] in ln]
    acct = BW.act_trance_accounted(_tr(x))
    led.check("S137-CONT", _gv(x, "calc_while_booted") == b.get("calc_while_booted") and cb.bend(x).get("ach_held") == b.get("ach")
              and _gv(x, "faulted") == b.get("faulted") and not lines and acct is True,
              f"calc_while_booted {b.get('calc_while_booted')} -> {_gv(x, 'calc_while_booted')}; ach_held {b.get('ach')!r} -> "
              f"{cb.bend(x).get('ach_held')!r}; faulted {b.get('faulted')} -> {_gv(x, 'faulted')}; fault lines "
              f"{[ln[-160:] for ln in lines[:2]]}; the identity {acct!r} ({_tbrief(x)})")


def _leg_td(g, led: cb.Ledger, ctx: dict) -> None:
    slot, wire = ctx["seat_slot"], ctx["seat_wire"]
    base = _tbase(g.state)
    at = cb.mark(g)
    x0, why = _batched(g, _unit_step(ctx, "trance1"), "netsync actbench teardown")
    if x0 is None:
        led.check("S137-TD", False, f"not reached: {why}")
        return
    g.wait_frames(30)                                      # past any grace a kept deferral would have swapped in
    x = g.state
    last = _tlast(x)
    lok, ldetail = judge_last(last, via="teardown", wire=wire, to=None, swapped=False)
    lines = cb.wait_log(g, at, BW.LOG_TRANCE_SUMMARY, 2.0)
    v = seat_view(cb.unit(x, slot))
    d = _tdelta(x, base)
    led.check("S137-TD", lok and d["dropped"] == 1 and d["deferred"] == 1 and _tv(x, "pending") == 0 and v["model"] is False
              and cb.count(lines, BW.LOG_TRANCE_SUMMARY.split("] ", 1)[1]) == 1,
              f"{ldetail}; delta {d}; pending {_tv(x, 'pending')}; the seat {v} (nothing applied); "
              f"{cb.grep(lines, 'action trance: boot summary', limit=300)}")


# ---- boot 2
def _boot_inject(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    st, why = hd._boot(g, field)
    if st is None:
        led.check("S137-INJECT", False, f"not reached: {why}")
        return
    try:
        ok, awhy = _arm(g, ctx)
        st = g.state
        su, sw = _seat(st, ctx)
        l_id, summon = _summon_start(st, dict(ctx, seat_wire=sw)) if sw is not None else (None, "no seat")
        if not ok or su is None or l_id is None:
            led.check("S137-INJECT", False, f"not reached: {awhy}; seat wire {sw}; {summon if l_id is None else ''}")
            return
        slot, wire = int(su["slot"]), int(sw)
        base = _tbase(st)
        at = cb.mark(g)
        x0, bwhy = _batched(g, _feed_step(summon), f"netsync actbench unit {wire} trance1", "netsync endbench victory")
        if x0 is None:
            led.check("S137-INJECT", False, f"not reached: {bwhy}")
            return
        inj = cb.poll(g, lambda s: cb.bend(s).get("injected") is True, 8.0, "the injection")
        x = inj or g.state
        last = _tlast(x)
        lok, ldetail = judge_last(last, via="inject", wire=wire, to=True)
        v = seat_view(cb.unit(x, slot))
        # (fix pass: harness-inject-boot-no-containment) the end path's new writes judged on boot 2's own baseline too
        faults = [ln for ln in cb.new(g, at) if BW.LOG_TRANCE_FAULTED.split("] ", 1)[1].split(" (", 1)[0] in ln]
        acct = BW.act_trance_accounted(_tr(x))
        cont = _gv(x, "calc_while_booted") == base["calc_while_booted"] and _gv(x, "faulted") == base["faulted"] \
            and acct is True and not faults
        led.check("S137-INJECT", inj is not None and lok and _tv(x, "swaps_by_inject") == base["swaps_by_inject"] + 1
                  and _tv(x, "pending") == 0 and v["model"] is True and cont,
                  f"injected {inj is not None} ({cb.pick(cb.bend(x), 'injected', 'action', 'inject_phase')}); {ldetail}; "
                  f"the seat {v}; delta {_tdelta(x, base)}; containment over boot 2: calc_while_booted "
                  f"{base['calc_while_booted']} -> {_gv(x, 'calc_while_booted')}, faulted {base['faulted']} -> "
                  f"{_gv(x, 'faulted')}, the identity {acct!r}, fault lines {[ln[-160:] for ln in faults[:2]]}")
    except LEG_FAULTS as err:
        ar._faulted(led, ("S137-INJECT",), err)
    finally:
        led.unreached(("S137-INJECT",), "boot 2 ended before this leg")
        _disarm(g)
        hd._out(g, field)


# ------------------------------------------------------------------------------------------------ the release
def _release(g, led: cb.Ledger, ctx: dict) -> None:
    """INV first (the last leave is behind us), then the trance lever left SET on purpose and `reset`: the 'lever back'
    line, and `on` at rest when re-read WITH the role."""
    fp0 = ctx.get("fp0")
    if ctx["probe"]:
        fp1, why = cb.fingerprint(g, field=ctx.get("field", cb.FIELD))
        diff = cb.fp_diff(fp0, fp1) if fp0 and fp1 else None
        led.check("S137-INV", fp0 is not None and fp1 is not None and not diff,
                  why or f"changed: {diff}; battle_no {fp0.get('_battle_no') if fp0 else None} -> "
                         f"{fp1.get('_battle_no') if fp1 else None} (a diorama's InitBattle bumps it: not judged)")
        _act_verb(g, "trancegrace", "off")
    else:
        led.check("S137-INV", True, "nothing was booted (the probe failed closed): nothing to compare")
    at = cb.mark(g)
    cb.release(g)
    lines = cb.new(g, at)
    if not ctx["probe"]:
        led.check("S137-R", False, f"`{PROBE}` absent: nothing was set")
        return
    rr, rwhy = cb.reread_with_role(g)
    t = _tr(rr) if rr is not None else {}
    led.check("S137-R", rr is not None and cb.count(lines, BW.LOG_TRANCE_LEVER_BACK.split("] ", 1)[1]) == 1
              and t.get("on") is True,
              (f"re-read WITH the role: on {t.get('on')!r}" if rr is not None else f"no re-read with the role ({rwhy})")
              + f"; {cb.grep(lines, 'released with the harness')}")
