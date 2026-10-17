"""R3 GROUP 2, s135 -- THE REPLAY HIT HOLD (memoria-patch s135), the solo bench and its T2 tape leg, run unattended.

THE GAP (studies/battle-coop/R3-DESIGN.md 3.3.4 as amended by R3-ACTION-REPLAY-AUDIT.md 2.3 -- amendments 1-15, decisions
D01-D12 -- and section 3; the audit's "s124": group 2 was renumbered s133-s141). Since s134 the guest REPLAYS the host's
actions on its battle diorama, but the host's impact frame still lands when it ARRIVES: the number, the flinch and a death
show before (or after) the replay's swing reaches its target. s135 HOLDS a paired impact for the replay's own hit: its
figures are written into the unit's fig inside EffectPoint's zero/collect bracket and shown at the sequence's Figure point,
then the flinch, then the kill or revive. The owner's rule (2026-10-13): the NUMBERS wait for the replay's hit; the HP and MP
BARS still follow the host (a held frame's non-life lanes apply at arrival). THE CONTAINMENT LAW holds: the hold only DELAYS
applying the host's own values. A held kill or revive also masks its slot from the reconciler (THE LIFE MASK: ApplyUnit
skips the whole record). Other releases take the legacy path: `late` (the replay hit first: a credit), `end` (it ended
without hitting that target), `hostdone` (the host's END + 1500 ms), `timeout` (2500 ms after arrival), `abort`, `replaced`
(a newer START took its pending slot), `declined`, `end-inject` (EndTick's injection branch, BEFORE AllPlayersDown). Read
back: `netsync.battle.act.guest.hold` (every role). Bench verbs (selftest role): `netsync actbench hold on|off` (off = the
pre-s135 guest), `lifeskip on|off` (off = the reconciler ignores the life mask), `unit <slot 0-7> dead|alive|trance0|trance1`
(one post-horizon type-1 record through the reconciler's own ApplyUnit), plus s134's `feed` / `feedat`.

TWO LEGS, one per launch (COOP_HOLD_LEG):
  solo (the default) -- the desktop in the forced selftest role, every fabricated leg and the lever calibration.
  tape -- THE T2 TAPE BENCH (audit 4.9): the RECORDED s133 host tape coop_action_replay's tape leg uses
          (.harness-runs/coop-tapes/act-s133) replayed into this desktop as the GUEST by tools/harness/coop_peer.py
          `replay-host` -- the real transport intake, the watcher's boot, ActionTick's nonce gate -- judged on
          `act.guest.hold`: impacts held for their replay's hit, every one released, figures released BY THE HIT, and the
          REAL-LINK LAG key populated (audit amendment 10: the host's impact vs the guest's own hit).

PRECONDITIONS -- THE OPERATOR'S JOB:
  * solo: Memoria.ini [Netsync] Enabled = 0 (or absent) -- the selftest role is refused on a live-configured install; the
    bench never edits Memoria.ini (S135-INI reads it READ-ONLY and, when it reads 1, records itself red and runs NOTHING).
  * tape: the game CLOSED before the launch (play.py launches it), no production bridge on 49201, [SaveFile]
    AutoSaveOnlyAtMoogle 0; the leg writes [Netsync] (backed up first, restored byte-exact in the `finally`) exactly as
    coop_action_replay's tape leg does (ActionReplay 1; 0 under COOP_CALIBRATE).
  * The DLL under test deployed and the game launched on it (the orchestrator's: this bench deploys nothing).
  * COOPPARTY (studies/battle-coop/bench/coopparty.field.toml, 30604) registered: Zidane / Vivi / Garnet / Steiner (PRE).

THE SOLO BENCH. Field 30602 (cb.FIELD), `stateevery 1`. Battle 1 (the TAPE) is coop_action_replay's: s133's in-engine
tape over `battle 306 <COOP_ACT_GROUP, default 4>` (Fang x2) with the plan that cannot end the fight early (s134 LESSON 3:
Zidane Attacks the sturdiest standing ally once, Garnet Potions herself, every other prompt Defends until both are done and
two more prompts have passed, then `fight` to the victory) -- its result screen cleared with Session.leave_battle(
stop_on_field=True) (s134 LESSON 4) -- read offline: Zidane's Attack START (its vfx num, its host Speed), a Defend START
(kind 4) and an enemy START (kind 2, num == sub). Then THE INVARIANTS (cb.fingerprint) and seven diorama boots, each
`dioboot 306 <group>` on 30602, each boot reached steady before anything is fed. Every fed frame carries the bench's own
nonce byte (0x5D, MARKER: s134's bench is 0x5C) and every figure a value 5135-5151 (MARKER: nothing else in the process
shows one). "ZIDANE" IN A DIORAMA (s134 LESSON 1): every selftest `dioboot` seats the selftest mirror's stand-in ("BENCH",
another character's model) at Zidane's battle-1 wire -- every leg's Zidane is THAT seat (coop_action_replay._who), never a
unit named Zidane. No leg sends a `dioleave` mid-swirl (s134 LESSON 2: a Leave accepted in SwirlScene's not-fading window
strands a selftest diorama -- a pre-existing engine defect): every leave here comes after a steady boot. THE ORDER (s134
LESSON 3): boot 1 kills nothing (its last legs, L8 and TD, are ordered so a defect there cannot starve the legs before
them); every leg that kills an enemy or a player has its own boot. A follow-up that must land before a replay's own hit
rides the feed's OWN request (the agent runs a request's next step Block(2) frames on) -- never a second request after a
poll, which races the hit (the fix pass: DEF).

WHAT IS PROVEN (S135-*):
  INI   precondition: [Netsync] Enabled reads 0 / absent (READ-ONLY) -- else NOTHING runs.
  S0    the harness forced the selftest role (Memoria.ini untouched).
  P0    the probe: `netsync.battle.act.guest.hold` is published -- else no hold op is EVER sent (fails closed).
  PROOF the selftest proof block's line reads exactly 'action hold selftest: OK (28 rows)' -- no FAIL line.
  PRE   precondition: battle 1 seats Zidane, Vivi and Garnet and 2+ enemies.
  TAPE  battle 1's s133 tape carries Zidane's Attack START (kind 3), a Defend START (kind 4) and an enemy START (kind 2,
        num == sub): the nums the fabricated legs replay. (A short fight can leave it red: named.)
  BOOT  boot 1 steady with `act.guest.hold` at rest: held_now 0, queued_now 0, life_mask 0 (and `act.guest` running 0).
  -- boot 1: nothing dies --
  L1    Leg 1 (audit amendment 8): an ENEMY replay (Fang 1, kind 2, the taped sub) on Zidane's seat + a non-lethal impact
        naming it (figure 5135) in ONE request, the impact `feedat 700` (s137 proof-block fix: a slow taped Fang move
        outran the 2500 ms timeout when fed WITH its START): the seat's hp_raw follows the host on a publish taken BEFORE the replay's hit
        (the bars follow at arrival, never at the hit), the impact HELD (held_now 1); NO figure 5135 on any publish before
        the replay's first_hit_ms; then exactly ONE figure 5135 -- via "hit", displayed at or after first_hit_ms (figs[] is
        recorded at the DISPLAY); rel_hit +1; lag n +1 and >= 0.
  L1F   ...the flinch only after the hit: the seat's `mot` never MP_DAMAGE1/2 before first_hit_ms, then MP_DAMAGE1/2.
  L5    Leg 5, late: Zidane's seat's Attack on Fang 1, its hit seen (hits +1), THEN its impact (figure 5136): released
        "late" at once (rel_late +1, a figure 5136 via "late"), the lag's min negative (the replay's hit came first).
  L3    Leg 3, end (review F7): a DEFEND START for Zidane's seat (short; it hits only its caster) + an impact for Fang 2
        (figure 5137): released "end" -- before 2500 ms (rel_end +1, its figure via "end").
  L4    Leg 4, timeout: a LONG summon (Garnet, SummonGarnet / Leviathan, Leviathan__Full) on the Fangs + an impact on Vivi
        (figure 5138; a target that summon never hits): released "timeout" at 2500 ms of battle time (+ <= 250 ms) --
        judged on rel_timeout +1 and the engine's OWN release line ('held impact of id N on wire slot S released via
        timeout after M ms of battle time': ActHoldLog writes it whether or not the figure showed); figure 5138 is
        REPORTED, never judged (THE HIDE WINDOW, under TIMING RISKS).
  L4N   ...the feedat variant (design 6.9), fed only once L4's summon is at rest (no sequence in flight can hide Vivi): an
        impact naming NO START (an id nothing registered: figure 5139) applies on ARRIVAL (a figure via "arrival", held +0)
        -- the hold never holds what no replay will hit. ITS IN-RUN RED (the fix pass): the same predicate on L4's own
        state (figure 5138, held +1) must read False -- else the check could not fail (on `hold off` L4's figure pops on
        arrival, before the summon's PlaySFX hides anyone, with held +0 -- so L4N is red there: it never showed it can fail).
  L7    Leg 7, host END: the long summon + an impact on Vivi (figure 5140) + its END `feedat 100`: released "hostdone" at
        ~1600 ms of battle time (1550-1850) -- judged on rel_hostdone +1 and its release line; the figure REPORTED.
  REP   amendment 9, replaced: Zidane's seat's Attack (A) running, a second START (B) of the same seat parked behind it
        with an impact naming B (figure 5141; HELD while B waits), then a third START (C): B is superseded and its held
        impact released "replaced" at once (rel_replaced +1, its figure via "replaced").
  DSK   audit 4.8, a Darkside-shaped CASTER TRIPLE: Zidane's seat's Attack on Fang 1 + an impact carrying BOTH figures (the
        target's 5142, the caster's recoil 5143, both non-lethal): the caster's hp_raw follows on a publish BEFORE the hit
        (the whole frame held, its non-life lanes applied at arrival), NO 5142 / 5143 figure before first_hit_ms, the
        target's 5142 via "hit" after it. The caster's 5143 is shown only at a Figure point that names the caster -- an
        Attack's does not, so it is REPORTED, never judged: DSK does NOT prove the triple's caster figure (NOT PROVEN below).
  L8    Leg 8 as audit amendment 6 rewrote it, SUPERSEDED: an older held KILL (A: the long summon on Fang 1, its lethal
        impact on Fang 2 -- a target A never hits) and a newer held change on Fang 2 (B: Zidane's seat's Attack on Fang 2,
        a non-lethal impact, a LATER seq) in one feed: B's hit applies first, then A's timeout release is SKIPPED as
        superseded (superseded +1; A's release line via "timeout", marked SUPERSEDED; its figure 5144 REPORTED -- Fang 2
        is one of the summon's non-targets, THE HIDE WINDOW) -- Fang 2 stays alive.
  TD    the teardown discards (review F2): the long summon on Fang 1 ONLY (L8 never touches it: a defect there cannot
        starve TD) + a held LETHAL impact on Vivi (figure 5145), then `actbench teardown` (ActDiscardAll, no Leave first):
        discarded +1, life_mask 0, Vivi alive, no figure 5145 -- nothing applied, nothing shown. Then a normal leave.
  -- boot 2 --
  L2    Leg 2, lethal (review F5): Zidane's seat's Attack on Fang 1 + a LETHAL impact (figure 5146), batched in ONE request
        with `actbench unit <Fang 1's wire> dead` (a post-horizon type-1 record, two frames on): the record MEETS THE LIFE
        MASK (mask_skips +1, the 'met the life mask: SKIPPED' line) -- Fang 1 alive, life_mask with its bit, until the hit;
        after it Fang 1 dead (die_seq > 0), the mask 0, rel_hit +1.
  -- boot 3 --
  L2R   THE LIFE-SKIP'S OWN RED (every run): `lifeskip off`, then L2's shape on Fang 1 (figure 5147): the batched dead
        record KILLS AT THE OP -- dead on the request's own state while the impact is still held (before first_hit_ms),
        mask_skips +0, the 'went through the reconciler' line -- and (the fix pass: the reconciler STAMPS THE SUPERSEDED
        GUARD) the held kill, released later, counts superseded +1 (that record already applied the slot); `lifeskip on`.
  -- boot 4 --
  LOST  audit 3.3 / 4.8, a LOST lethal impact (a held kill with no paired lethal impact): Zidane's seat's Attack on Fang 1
        with NO impact, then `unit <Fang 1> dead` -- nothing is held, so the mask cannot protect it: the record kills at
        once (mask_skips +0), BEFORE the replay's hit. The documented v1 behaviour (the mask guards only what arrived). ITS
        IN-RUN RED (the fix pass): the same predicate on L2's at-the-op state (where the mask DID protect Fang 1: alive,
        mask_skips +1) must read False -- else the check could not fail (L2 unreached, or `hold off`: LOST is red).
  L6    Leg 6, abort: the long summon on Fang 2 + a held LETHAL impact on Vivi (figure 5148), then `dioleave` (a steady
        boot, never mid-swirl): released "abort" (rel_abort +1 and its release line; the figure REPORTED: a slow leave can
        land inside THE HIDE WINDOW), the mask 0, discarded +0 -- read after the leave (the counters stay until the next
        boot).
  -- boot 5 --
  QSUP  the fix pass (life-1 / timing-2), a QUEUED frame never stands up a corpse: Zidane's seat's Attack on Fang 1 + a
        held LETHAL impact (figure 5150; the mask has Fang 1's bit) + an impact naming NO START from Garnet on Fang 1 (Fang
        1's slot is busy: the whole frame QUEUES; Garnet's caster lane is no life lane, so her slot stays unmasked), batched
        with `unit <Garnet's wire> dead` (the reconciler kills her -- Doom, a script, a lost lethal impact -- and stamps her
        slot). The hit releases the kill and the queue drains (the next tick: never inside EffectPoint's bracket): the
        queued caster lane, older than the record and no life lane when it queued, is SUPERSEDED (superseded +1, the
        queued release's line says so) -- Garnet stays dead on every publish from the op on (an engine without the fix
        revives her with the frame's stale HP, then the next sample kills her again).
  -- boot 6 --
  DEF   amendment 2, a held lethal impact on the LAST player, then the defeat: every seated player but Garnet killed by an
        impact naming no START (the arrival path -- NEVER `endbench kill`: amendment 15, it bypasses the mask), then -- ONE
        request (the fix pass: a second request after a poll raced the replay's own hit on Garnet) -- Fang 1's attack
        replay on Garnet + a LETHAL impact (figure 5149), held (the mask has Garnet's bit), and `endbench phase-defeat` two
        frames on: the END-INJECT RELEASE fires BEFORE AllPlayersDown (held +1, rel_end_inject +1, the 'end injection
        released' line) -- "annihilate" WITH the settle (inject_phase MENU_OFF, no 'settle skipped' line).
  -- boot 7 --
  CATCH the fix pass (life-2), the end-inject flush re-applies what the mask SKIPPED: every seated player killed on
        arrival, then ONE request -- Fang 1's attack replay on Garnet + a held REVIVE (a non-lethal impact on dead Garnet,
        figure 5151: a life lane, the mask has her bit), `unit <Garnet> dead` (the host killed her again; SKIPPED:
        mask_skips +1) and `endbench phase-defeat`: the flush revives her (end-inject), then re-applies the skipped dead
        record (the 'skipped record ... re-applied at the end injection' line) BEFORE AllPlayersDown -- "annihilate" WITH
        the settle, Garnet dead (an engine that drops the skipped record reads her standing: blocker 4 for a masked slot).
  INV   THE INVARIANTS after the last leave: gil, the bag, levels, exp, AP, kill counters == the pre-boot snapshot.
  R     `reset` with `hold off` and `lifeskip off` left set: the 'hold levers back' line; RE-READ WITH THE ROLE: the hold
        on, the life-mask skip on.
NOT PROVEN HERE: the hidden guard at a release (amendment 3: a selftest diorama hides no enemy -- the reconciler's Hidden
lane is not a bench seam; the selftest row pins the rule), THE FREEZE (amendment 14 as built, the fix pass rlife-1: a slot
is in the life mask for its own held kill or revive AND for any frame held or queued behind an older life change or queued
frame on it -- a LIVING unit included; while it is, the reconciler skips its WHOLE record, so current and max HP/MP, hide,
trance and ATB do not follow the host until the last such change releases -- each at most 2.5 s of battle time from its
own arrival, overlapping frames chain it -- and then the last skipped record is re-applied at once (ActHoldCatchUp) or at
the end-inject flush; no bench seam reads the max HP/MP, hide or ATB lanes -- the README row records it), the caster lane's
figure on a hit release (amendment 4: an Attack's Figure point never names the caster, so DSK reports 5143 and never
judges it -- a sequence whose Figure point names its caster, Darkside's, is not on the tape), a cut replay's pending hit
figure shown at once (the fix pass, timing-1: a `clear` landing between a hit's Effect and Figure points is a frame race
no request can aim at -- the selftest row pins the rule: shown at any cut, never at a natural end), the queued frame's own
release order on a real link (FIFO behind a held life change: the stand-in's tests and the selftest row pin it), a slave
part's master key (no multi-part enemy at scene 306), WhiteDraw / DragonBreath's extra CalcResults (amendment 7), the crit
shove of a hit's flinch (amendment 13: stock's own), a pause holding a release (audit 3.5: battle time -- s134's PAUSE leg
pins the clock), and a hit release outside PHASE_NORMAL (D12).

TIMING RISKS -- what a run's timing can do to a check, and how each leg stays judgeable:
  * THE HIDE WINDOW (the fix pass: rtiming-1). Leviathan__Full's PlaySFX hides every NON-target (ef179 Sequence.seq:6
    `ShowMesh: Char=AllNonTargets ; Enable=False ; IsDisappear=True`; its targets too, from about frame 16 to 339) and
    shows them again only AFTER its Figure point; btl2d drops a figure on a disappeared unit (bi.disappear) and
    ActShowFigure records none in figs[]. PlayerSequence reaches PlaySFX about 2.2-3.8 s after the START (the stance
    wait, the step forward, the chant, Wait 13, WaitSFXLoaded, MP_MAGIC) -- a window that straddles the 2500 ms timeout
    and moves EARLIER once the boot has cached the SFX (L7 and L8 run after L4). So a correct engine may show NO figure
    for a release on a unit the summon does not hit (L4 and L7 on Vivi, L8 on Fang 2, L6 on Vivi): those legs judge the
    release by its counter and the engine's own per-release line (`judge_timer_release` over ActHoldLog's 'released via'
    line, written whether or not the figure showed) and only REPORT the figure; L4N is fed with no summon in flight. TD's
    "no figure 5145" is a weak witness for the same reason (its discard is judged on `discarded`, the mask, Vivi alive).
  * THE SUMMON'S LENGTH: L4, L7 and L8 need the summon still RUNNING at their release (else it reads `end`):
    Leviathan__Full outlives W3's 4 s (s134's E3 replay), the 2500 ms timeout and the ~1600 ms host-done alike.
  * THE PER-BOOT LOG CAP: ActHoldLog writes at most 48 release lines a boot; boot 1 releases about ten.

CALIBRATION -- a check that cannot fail is not a check.
  * THE DEPLOYED DLL AT WRITING (s134) -- and any engine before s135: `act.guest.hold` is absent, so P0 is RED and no hold
    op is ever sent; battle 1 still runs (s133's tape is there). RED, exactly: every check but INI, S0, PRE, TAPE, INV
    (nothing booted, nothing to change). COOP_CALIBRATE=1 there judges exactly that red set as S135-CAL.
  * IN-RUN, on the s135 DLL: L2R is the life-mask skip's own red every run (judged GREEN when the record kills at the op);
    L4N's and LOST's predicates are each judged False on a sibling leg's state where the hold DID act (L4's timeout
    figure, L2's protected op) -- each check's own red, every run.
    COOP_CALIBRATE=1 also pulls `actbench hold off` (the pre-s135 guest) BEFORE boot 1 -- every impact takes the arrival
    path. Predicted reds, exactly: L1, L1F, L5, L3, L4, L4N, L7, REP, DSK, L8, TD, L2, L2R, LOST, L6, QSUP, DEF, CATCH
    (nothing is ever held: each reads its hold counter, its figure's reason, its held or queued precondition -- or, L4N
    and LOST, an in-run red that never came); GREEN: INI, S0, P0, PROOF, PRE, TAPE, BOOT, INV, R. S135-CAL judges that set
    (the run is red by design).
  * THE STAND-IN (tools/harness/fakegame.py, cap `acthold`) models the hold through battlewire.ActHoldLane -- not the
    sequencer, not this plan: never read S135-CAL offline. Its tests (ff9mapkit/tests/test_harness_netsync.py) evaluate
    ActHoldSelfTest's 28 rows off the stack against the twins, pin the verb, the keys and these tables; the engine is the
    calibration.

THE TAPE LEG (COOP_HOLD_LEG=tape). The tape: coop_action_replay's (COOP_ACT_TAPE, else COOP_ACT_TAPE_DIR's or
<main repo>/.harness-runs/coop-tapes/act-s133's latest.json, else its newest *.f9tape) -- it must carry an s133+ host's
action lane on its first battle (>= 1 START), and coop_cut_hold's CAL leg must have passed on it (its sha256 sidecar);
else the leg refuses cleanly ("no s133 tape": every check "not reached" but T2-INI). The guest config is coop_action_
replay's tape leg's (ActionReplay 1; 0 under COOP_CALIBRATE). The whole tape replays (no cut); every publish is sampled
until the end-leave's RETURN. Checks (S135T-*):
  I     the instrument: 'paired', 'state-mirror ARMED', 'diorama BOOT scene=M', 'diorama LIVE ... nonce N' logged.
  P0    `netsync.battle.act.guest.hold` published on the guest during the battle (else every hold check fails closed).
  HELD  held >= 1 and a PAIRED release (rel_hit + rel_late >= 1): the real intake held the host's impacts for the replay.
  REST  at rest (the last sample): held_now 0, queued_now 0, life_mask 0, and every held impact released by exactly one
        reason (held == the sum of rel_*; queued == rel_queued) -- with a teardown's discard, the whole account: held +
        queued == the sum of rel_* + rel_queued + discarded (every frame leaves the hold exactly once).
  LAG   THE REAL-LINK LAG (amendment 10): lag.n >= 1, min <= p50 <= max, none missing (n >= 1 already rules out the -1
        sentinel: a real lag of -1 ms is a credit, never a red) -- the values reported.
  FIG   a figure released BY THE HIT: >= 1 figs entry via "hit", each displayed at or after its arrival; every via one the
        engine writes -- judged on the UNION of every sample's figs[] (deduped by slot, value, via, arrival, release: the
        ring keeps only the last 16 displays, so a long tape's early hits would fall out of the last sample).
  LOG   the 'an impact HELD for its replay's hit' line, >= 1 'released via' line, no 'action replay hold faulted' line.
  plus coop_cut_hold's COMMON T2-TAPE, T2-CAL, T2-PEER (its config line names ' actionReplay=0' exactly when the knob is
  written 0), T2-SAVE and T2-INI.
  CALIBRATION: on an s134 GUEST `act.guest.hold` is absent: RED exactly P0, HELD, REST, LAG, FIG, LOG (fails closed) --
  the T2-* and I GREEN. On s135 under COOP_CALIBRATE=1 (ActionReplay=0: every START declines `knob`, nothing to hold;
  the hold's own levers are selftest-only and this guest is a real client): RED exactly HELD, LAG, FIG, LOG (REST is green:
  0 held, 0 released). S135T-CAL judges the set the engine FOUND.

RUN:
    py tools/play.py studies/test-harness/scenarios/coop_action_hold.py --field 30602
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_action_hold.py --field 30602
    COOP_HOLD_LEG=tape py tools/play.py studies/test-harness/scenarios/coop_action_hold.py
  PowerShell has no per-launch form: a `$env:` value PERSISTS in that shell -- clear them after each run:
    Remove-Item Env:COOP_CALIBRATE, Env:COOP_HOLD_LEG, Env:COOP_ACT_TAPE -ErrorAction SilentlyContinue
"""
from __future__ import annotations

import datetime as _dt
import itertools
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import _coop_peer_bench as pb                              # noqa: E402 - the T2 two-role bench helpers
import coop_action_replay as ar                            # noqa: E402 - s134's bench: its reads, cast and tape leg helpers

BW = ar.BW
HarnessError = cb.HarnessError

LEG = (os.environ.get("COOP_HOLD_LEG", "solo").strip().lower() or "solo")
LEGS = ("solo", "tape")
PROBE = cb.R3_PROBES[135]                  # netsync.battle.act.guest.hold: absent = s134 or older (fails closed)
GUEST_PROBE = cb.R3_PROBES[134]            # netsync.battle.act.guest: the replay the hold waits for
HOST_PROBE = cb.R3_PROBES[133]             # netsync.battle.act.host: the in-engine tape (battle 1)
SCENE, GROUP = ar.SCENE, ar.GROUP          # 306 / 4 (Fang x2): the s133 / s134 benches' scene
NONCE = 0x5D                               # MARKER: this bench's nonce byte (s134's bench is 0x5C)
FIG = {"L1": 5135, "L5": 5136, "L3": 5137, "L4": 5138, "L4N": 5139, "L7": 5140, "REP": 5141, "DSK": 5142,
       "DSK_C": 5143, "L8": 5144, "TD": 5145, "L2": 5146, "L2R": 5147, "L6": 5148, "DEF": 5149,
       "QSUP": 5150, "CATCH": 5151}       # MARKER: the figures (5150-5151: the fix pass's legs)
INFO_HP = 1                                # Param.FIG_INFO_DISP_HP: an HP figure (EffectPoint collects info != 0 only)
#: [s137 proof-block fix] Leg 1's impact rides the START's OWN request this many ms later (`feedat`): which Fang move
#: battle 1 tapes varies -- sub 3 hit 1437 ms after an impact fed WITH its START, sub 5 2156 and 2560 ms -- and the slow
#: one outran the hold's 2500 ms timeout, so a correct engine released the number via `timeout` (red L1 / L1F)
L1_IMPACT_AFTER_MS = 700
REPLAY_S = 20.0                            # a fabricated replay's end, at most
LONG_S = 30.0                              # the long summon's natural end, at most (it is cleared past it)
FIGURE_SLACK_MS = 250                      # a timer release's lateness, at most (ActTick runs every Update)
HOSTDONE_MS = BW.ACT_HOLD_HOST_DONE_MS + 100   # the END is fed 100 ms after its impact
PROOF = "action hold selftest:"
PROOF_OK = BW.proof_ok(BW.PROOF_HOLD, BW.HOLD_SELFTEST_ROWS).rstrip()
LEG_FAULTS = ar.LEG_FAULTS
_IDS = itertools.count(1)                  # bench ids: unique per process, so unique per boot (no `duplicate`)
_SEQS = itertools.count(1000)              # impact seqs: ascending (the superseded guard reads their order)


# ================================================================================================ the catalogs
def _solo_catalog(calibrate: bool) -> dict:
    c = {
        "S135-INI": "precondition: Memoria.ini [Netsync] Enabled reads 0 (or absent), READ-ONLY -- else NOTHING runs",
        "S135-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
        "S135-P0": f"the engine publishes `{PROBE}` (memoria-patch s135) -- else no hold op is ever sent (fails closed)",
        "S135-PROOF": f"the selftest proof block's line reads exactly '{PROOF_OK}' -- no FAIL line",
        "S135-PRE": f"precondition: battle 1 (`battle {SCENE} {GROUP}`) seats Zidane, Vivi and Garnet and 2+ enemies",
        "S135-TAPE": "battle 1's s133 tape carries Zidane's Attack START (kind 3), a Defend START (kind 4) and an enemy "
                     "START (kind 2, num == sub)",
        "S135-BOOT": "boot 1 steady with act.guest.hold at rest: held_now 0, queued_now 0, life_mask 0 (running 0)",
        "S135-L1": "Leg 1: an enemy replay + a non-lethal impact on Zidane's seat -- hp_raw follows at arrival, HELD; no "
                   "figure before first_hit_ms, then ONE figure via 'hit' at/after it; rel_hit +1, lag >= 0",
        "S135-L1F": "Leg 1: the seat's flinch (MP_DAMAGE1/2) only after first_hit_ms",
        "S135-L5": "Leg 5: the impact after the replay's hit -- released 'late' at once, its figure via 'late', the lag's "
                   "min negative",
        "S135-L3": "Leg 3: a Defend START + an impact for Fang 2 -- released 'end' before 2500 ms",
        "S135-L4": "Leg 4: a long summon + an impact on a target it never hits -- released 'timeout' at 2500 ms (+250): "
                   "rel_timeout +1 and the engine's release line (the figure reported)",
        "S135-L4N": "Leg 4 (feedat variant, no summon in flight): an impact naming no START applies on arrival (via "
                    "'arrival', held +0) -- the same predicate reads False on L4's held state (its in-run red)",
        "S135-L7": "Leg 7: a long summon + an impact it never hits + its END at +100 ms -- released 'hostdone' ~1600 ms: "
                   "rel_hostdone +1 and the engine's release line (the figure reported)",
        "S135-REP": "amendment 9: a parked START's held impact released 'replaced' when a newer START supersedes it",
        "S135-DSK": "a Darkside-shaped caster triple: the caster's hp_raw follows at arrival; no figure before the hit; the "
                    "target's via 'hit'",
        "S135-L8": "Leg 8: an older held kill overtaken by a newer held change -- superseded +1, its release line via "
                   "'timeout' marked SUPERSEDED (the figure reported), Fang 2 alive",
        "S135-TD": "the teardown DISCARDS a held kill: discarded +1, the mask 0, Vivi alive, no figure",
        "S135-L2": "Leg 2: a held lethal impact + `unit dead` in one request -- the record SKIPPED (mask_skips +1), alive "
                   "until the hit, then dead, the mask 0",
        "S135-L2R": "the life-skip's own red: `lifeskip off` -- the batched dead record kills at the op, before the hit "
                    "(mask_skips +0); the held kill, released later, superseded +1 (the reconciler stamped the slot)",
        "S135-LOST": "a lost lethal impact: nothing held, so `unit dead` kills at once, before the replay's hit (v1) -- the "
                     "same predicate reads False on L2's protected op (its in-run red)",
        "S135-L6": "Leg 6: a held kill, then `dioleave` -- released 'abort' (rel_abort +1 and its release line; the "
                   "figure reported), the mask 0, discarded +0",
        "S135-QSUP": "the fix pass: a queued frame's free caster lane after `unit <caster> dead` -- superseded +1 at the "
                     "drain, the caster dead on every publish (never stood up)",
        "S135-DEF": "amendment 2: a held kill on the last player + `endbench phase-defeat` in ONE request -- released "
                    "'end-inject' before AllPlayersDown: 'annihilate' WITH the settle",
        "S135-CATCH": "the fix pass: a held revive on the last player, its dead record SKIPPED, then the defeat -- the "
                      "flush re-applies the record before AllPlayersDown: 'annihilate' WITH the settle, the player dead",
        "S135-INV": "the invariants after the last leave: gil, bag, levels, exp, AP, kill counters == the pre-boot snapshot",
        "S135-R": "`reset` with the hold levers set: the 'hold levers back' line; RE-READ WITH THE ROLE both levers at rest",
    }
    if calibrate:
        c["S135-CAL"] = ("CALIBRATION: exactly the predicted checks are red -- on an engine without `act.guest.hold` every "
                         "check but INI/S0/PRE/TAPE/INV; on the s135 DLL under `hold off` the LEVER set")
    return c


#: the checks that need `act.guest.hold` (not reached together when the probe fails closed)
HOLD_CHECKS = ("S135-PROOF", "S135-BOOT", "S135-L1", "S135-L1F", "S135-L5", "S135-L3", "S135-L4", "S135-L4N", "S135-L7",
               "S135-REP", "S135-DSK", "S135-L8", "S135-TD", "S135-L2", "S135-L2R", "S135-LOST", "S135-L6", "S135-QSUP",
               "S135-DEF", "S135-CATCH", "S135-R")
#: COOP_CALIBRATE=1 on an engine without `act.guest.hold` (the deployed s134, or older): all but INI, S0, PRE, TAPE, INV.
OLD_PREDICTED = tuple(c for c in _solo_catalog(True) if c not in ("S135-INI", "S135-S0", "S135-PRE", "S135-TAPE",
                                                                    "S135-INV", "S135-CAL"))
#: COOP_CALIBRATE=1 on the s135 DLL: `hold off` before boot 1 -- nothing is ever held (L4N and LOST: their in-run reds
#: never come, so neither check showed it can fail -- red)
LEVER_PREDICTED = ("S135-L1", "S135-L1F", "S135-L5", "S135-L3", "S135-L4", "S135-L4N", "S135-L7", "S135-REP", "S135-DSK",
                   "S135-L8", "S135-TD", "S135-L2", "S135-L2R", "S135-LOST", "S135-L6", "S135-QSUP", "S135-DEF",
                   "S135-CATCH")
LEVER_MAYBE: tuple = ()

TAPE_CHECKS = {
    "S135T-I": "the instrument: 'paired', 'state-mirror ARMED', 'diorama BOOT scene=M', 'diorama LIVE ... nonce N' logged",
    "S135T-P0": f"`{PROBE}` published on the guest during the battle (else every hold check fails closed)",
    "S135T-HELD": "held >= 1 and a paired release (rel_hit + rel_late >= 1): the real intake held impacts for the replay",
    "S135T-REST": "at rest: held_now 0, queued_now 0, life_mask 0; held == sum(rel_*), queued == rel_queued",
    "S135T-LAG": "the real-link lag key: lag.n >= 1, min <= p50 <= max, none -1",
    "S135T-FIG": ">= 1 figure via 'hit' (displayed at or after its arrival); every via one the engine writes",
    "S135T-LOG": "the 'impact HELD' line, a 'released via' line, no 'action replay hold faulted' line",
}
TAPE_HOLD = ("S135T-P0", "S135T-HELD", "S135T-REST", "S135T-LAG", "S135T-FIG", "S135T-LOG")
#: the tape leg on an s134 GUEST (no `act.guest.hold`): every hold check fails closed
TAPE_OLD_PREDICTED = TAPE_HOLD
#: the tape leg on s135 under COOP_CALIBRATE=1 (ActionReplay=0 written): no replay, nothing held
TAPE_KNOB_PREDICTED = ("S135T-HELD", "S135T-LAG", "S135T-FIG", "S135T-LOG")


def _tape_catalog(calibrate: bool) -> dict:
    cat = {"T2-TAPE": ar.TAPE_COMMON["T2-TAPE"], "T2-CAL": ar.TAPE_COMMON["T2-CAL"], "T2-PEER": ar.TAPE_COMMON["T2-PEER"]}
    cat.update(TAPE_CHECKS)
    if calibrate:
        cat["S135T-CAL"] = ("CALIBRATION: exactly the predicted checks are red for the engine found -- s134: every hold "
                            "check; s135 under ActionReplay=0: HELD, LAG, FIG, LOG")
    cat["T2-SAVE"] = ar.TAPE_COMMON["T2-SAVE"]
    cat["T2-INI"] = ar.TAPE_COMMON["T2-INI"]
    return cat


def _catalog(calibrate: bool, leg: str = "solo") -> dict:
    return _tape_catalog(calibrate) if leg == "tape" else _solo_catalog(calibrate)


def _tape_predicted(has_hold: bool) -> tuple:
    """The tape leg's predicted reds for the engine FOUND (its `act.guest.hold` key) under COOP_CALIBRATE=1."""
    return TAPE_KNOB_PREDICTED if has_hold else TAPE_OLD_PREDICTED


# ================================================================================================ reads
_num = ar._num
_sub = ar._sub
_guest = ar._guest
_gv = ar._gv


def _hold(x) -> dict:
    return _sub(_guest(x), "hold")


def _hv(x, key: str) -> int:
    return _num(_hold(x).get(key)) or 0


def _figs(x) -> list:
    f = _hold(x).get("figs")
    return [e for e in f if isinstance(e, dict)] if isinstance(f, list) else []


def _lag(x) -> dict:
    return _sub(_hold(x), "lag")


def _last(x) -> dict:
    v = _guest(x).get("last")
    return v if isinstance(v, dict) else {}


def _first_hit(x) -> int:
    v = _num(_last(x).get("first_hit_ms"))
    return v if v is not None else -1


def _hbrief(x) -> str:
    return "act.guest.hold=" + str(cb.pick(_hold(x), "on", "lifeskip", "held_now", "held", "queued_now", *BW.ACT_HOLD_REL_KEYS,
                                           "rel_queued", "superseded", "discarded", "life_mask", "mask_skips", "lag"))


def _hbase(x) -> dict:
    out = {k: _hv(x, k) for k in ("held", "queued", "rel_queued", "superseded", "discarded", "mask_skips",
                                   *BW.ACT_HOLD_REL_KEYS)}
    out["lag_n"] = _num(_lag(x).get("n")) or 0
    out["hits"] = _gv(x, "hits")
    out["ended"], out["aborted"], out["started"] = _gv(x, "ended"), _gv(x, "aborted"), _gv(x, "started")
    return out


def _alive(x, slot: int | None) -> bool | None:
    u = ar._unit(x, slot)
    return u.get("alive") if u else None


def _sample(x) -> dict:
    """One publish, as the pure judges read it."""
    return {"figs": _figs(x), "first_hit_ms": _first_hit(x), "battle_ms": _gv(x, "battle_ms"),
            "held_now": _hv(x, "held_now"), "life_mask": _hv(x, "life_mask")}


# ================================================================================================ the pure judges
def figs_of(figs, value: int) -> list:
    """The figs[] entries showing ``value`` (a bench MARKER figure)."""
    return [e for e in figs or [] if isinstance(e, dict) and e.get("value") == value]


def judge_figure_waits(samples: list, value: int, slot: int | None = None, via: str = "hit") -> tuple:
    """Audit amendment 8's rule, PURE (test_harness_netsync.py runs it on synthetic runs): ``samples`` are the publishes
    from the feed on (each {figs, first_hit_ms, ...}); NO figure ``value`` on any publish before the replay's first hit,
    then EXACTLY ONE display of it -- via ``via``, its release at or after the first hit (and in ``slot`` when named).
    (ok, detail)."""
    if not samples:
        return False, "no publish read"
    early = [s for s in samples if (s.get("first_hit_ms") if s.get("first_hit_ms") is not None else -1) < 0
             and figs_of(s.get("figs"), value)]
    last = samples[-1]
    hit = last.get("first_hit_ms") if last.get("first_hit_ms") is not None else -1
    shown = figs_of(last.get("figs"), value)
    if early:
        e = figs_of(early[0].get("figs"), value)[0]
        return False, (f"figure {value} shown BEFORE the replay's hit (via {e.get('via')!r} at {e.get('release_ms')} ms; "
                       f"first_hit_ms then {early[0].get('first_hit_ms')})")
    if hit < 0:
        return False, f"the replay never hit (first_hit_ms -1); figure {value} shown {len(shown)} time(s)"
    if len(shown) != 1:
        return False, f"figure {value} shown {len(shown)} time(s) (want ONE): {shown}"
    e = shown[0]
    if e.get("via") != via or (e.get("release_ms") if e.get("release_ms") is not None else -1) < hit or (
            slot is not None and e.get("slot") != slot):
        return False, f"figure {value}: {e} (want via {via!r}, released at/after first_hit_ms {hit}" + (
            f", slot {slot})" if slot is not None else ")")
    return True, f"no figure {value} before first_hit_ms {hit}; then one, via {via!r}: {e}"


def judge_release(figs, value: int, via: str, lo_ms: int, hi_ms: int) -> tuple:
    """A figure ``value`` released via ``via`` with release_ms - arrival_ms in [lo_ms, hi_ms] (PURE). (ok, detail)."""
    shown = figs_of(figs, value)
    if len(shown) != 1:
        return False, f"figure {value} shown {len(shown)} time(s) (want ONE): {shown}"
    e = shown[0]
    held = (e.get("release_ms") or 0) - (e.get("arrival_ms") or 0)
    ok = e.get("via") == via and lo_ms <= held <= hi_ms
    return ok, f"figure {value} via {e.get('via')!r} after {held} ms of battle time (want {via!r} in [{lo_ms}, {hi_ms}])"


def release_needle(act_id: int, slot: int) -> str:
    """The head of ActHoldLog's release line for the held impact naming ``act_id`` on wire slot ``slot``."""
    return f"{BW.LOG_HOLD_HELD_IMPACT} of id {act_id} on wire slot {slot}{BW.LOG_HOLD_RELEASED_VIA}"


def judge_timer_release(lines, act_id: int, slot: int, via: str, lo_ms: int, hi_ms: int,
                        superseded: bool | None = None) -> tuple:
    """A held impact's release judged on the ENGINE'S OWN line (ActHoldLog, via battlewire.parse_hold_release), never on
    figs[] (the fix pass: rtiming-1 -- the line is written at the release whether or not the figure showed, and a long
    summon's PlaySFX hides every non-target, whose figure btl2d then drops): exactly ONE 'held impact of id ``act_id`` on
    wire slot ``slot`` released via' line among ``lines``, via ``via``, held ``lo_ms``-``hi_ms`` ms of battle time, and
    marked SUPERSEDED exactly when ``superseded`` says so (None: not judged). PURE. (ok, detail)."""
    rel = [p for p in (BW.parse_hold_release(ln) for ln in lines or []) if p is not None and not p["queued"]
           and p["id"] == act_id and p["slot"] == slot]
    if len(rel) != 1:
        return False, f"{len(rel)} release line(s) for the held impact of id {act_id} on wire slot {slot} (want ONE)"
    p = rel[0]
    ok = p["via"] == via and lo_ms <= p["held_ms"] <= hi_ms and (superseded is None or p["superseded"] is superseded)
    return ok, (f"id {act_id} on wire slot {slot} released via {p['via']!r} after {p['held_ms']} ms of battle time"
                + (", SUPERSEDED" if p["superseded"] else "") + f" (want {via!r} in [{lo_ms}, {hi_ms}]"
                + ("" if superseded is None else f", superseded {superseded}") + ")")


def lost_pred(alive, first_hit: int, held_now: int, mask_skips: int, base_skips: int) -> bool:
    """LOST's predicate (PURE): the dead record killed at once -- the unit dead before the replay's hit, nothing held, the
    mask skipped nothing. Its in-run red: L2's at-the-op state (the mask protected the unit) must read False."""
    return alive is False and first_hit < 0 and held_now == 0 and mask_skips == base_skips


def arrival_pred(figs, value: int, held0: int, held1: int) -> bool:
    """L4N's predicate (PURE): the figure ``value`` shown ONCE, via "arrival", and nothing held for it. Its in-run red:
    L4's own timeout figure (held +1) must read False."""
    shown = figs_of(figs, value)
    return len(shown) == 1 and shown[0].get("via") == BW.ACT_VIA_ARRIVAL and held1 == held0


def figs_union(blocks) -> list:
    """Every figs[] entry over the samples, oldest first, deduped by (slot, value, via, arrival_ms, release_ms) -- the ring
    keeps the last ACT_HOLD_FIGS_MAX displays only, so the last sample alone loses a long run's early figures (PURE)."""
    out, seen = [], set()
    for b in blocks:
        for e in (b.get("figs") or []) if isinstance(b, dict) else []:
            if not isinstance(e, dict):
                continue
            key = tuple(e.get(k) for k in BW.ACT_HOLD_FIG_KEYS)
            if key in seen:
                continue
            seen.add(key)
            out.append(e)
    return out


def judge_flinch(mots: list, first_hit_ms: int) -> tuple:
    """L1F (PURE): ``mots`` = [(battle_ms, first_hit_ms, mot)] from the feed on -- no MP_DAMAGE1/2 before the hit, one
    after it. (ok, detail)."""
    dmg = (BW.MP_DAMAGE1, BW.MP_DAMAGE2)
    early = [(bm, m) for bm, fh, m in mots if m in dmg and (fh if fh is not None else -1) < 0]
    late = [(bm, m) for bm, fh, m in mots if m in dmg and (fh if fh is not None else -1) >= 0]
    return (not early and bool(late) and first_hit_ms >= 0,
            f"flinch samples before the hit {early[:3]}, after it {late[:3]} (first_hit_ms {first_hit_ms})")


def judge_hold_tape(led, samples: list, messages: list) -> None:
    """THE TAPE LEG'S JUDGE (PURE: the samples -- each {booted, guest} -- and the engine's messages since the start;
    test_harness_netsync.py runs it on synthetic runs): P0, HELD, REST, LAG, FIG, LOG."""
    blocks = [s["guest"].get("hold") for s in samples if isinstance(s.get("guest"), dict)
              and isinstance(s["guest"].get("hold"), dict)]
    if not blocks:
        led.unreached(TAPE_HOLD, "`netsync.battle.act.guest.hold` was never published (an engine before s135: fails closed)")
        return
    led.check("S135T-P0", True, f"{len(blocks)} sample(s) with act.guest.hold")
    last = blocks[-1]
    n = {k: _num(last.get(k)) or 0 for k in ("held", "held_now", "queued", "queued_now", "rel_queued", "life_mask",
                                              "discarded", "superseded", "mask_skips", *BW.ACT_HOLD_REL_KEYS)}
    paired = n["rel_hit"] + n["rel_late"]
    led.check("S135T-HELD", n["held"] >= 1 and paired >= 1,
              f"held {n['held']}, paired releases {paired} (hit {n['rel_hit']}, late {n['rel_late']})")
    rel = BW.act_hold_released(last)
    by = {k: n[k] for k in BW.ACT_HOLD_REL_KEYS if n[k]}
    led.check("S135T-REST", BW.act_hold_at_rest(last),
              f"held_now {n['held_now']}, queued_now {n['queued_now']}, life_mask {n['life_mask']}; held {n['held']} vs "
              f"released {rel} ({by}); queued {n['queued']} vs rel_queued {n['rel_queued']}; discarded {n['discarded']}; "
              f"superseded {n['superseded']}; mask_skips {n['mask_skips']}")
    lag = last.get("lag") if isinstance(last.get("lag"), dict) else {}
    lv = {k: _num(lag.get(k)) for k in BW.ACT_HOLD_LAG_KEYS}
    # (n >= 1 rules out the -1 sentinel: a real lag of -1 ms -- a credit 1 ms before the impact -- is never a red)
    ok = (lv["n"] or 0) >= 1 and None not in lv.values() and lv["min"] <= lv["p50"] <= lv["max"]
    led.check("S135T-LAG", ok, f"lag {lv} (battle ms of the replay's hit minus the host impact's arrival; negative = "
                               f"the hit came first) -- THE REAL-LINK MEASURE (amendment 10)")
    figs = figs_union(blocks)                     # every sample's ring, deduped: never the last 16 displays alone
    hits = [e for e in figs if e.get("via") == "hit"]
    bad_order = [e for e in hits if (e.get("release_ms") or 0) < (e.get("arrival_ms") or 0)]
    unknown = sorted({str(e.get("via")) for e in figs} - set(BW.ACT_FIG_VIAS))
    vias = {}
    for e in figs:
        vias[e.get("via")] = vias.get(e.get("via"), 0) + 1
    led.check("S135T-FIG", bool(hits) and not bad_order and not unknown,
              f"{len(figs)} figure(s) shown over {len(blocks)} sample(s), {len(hits)} via 'hit' (released before arrival: "
              f"{bad_order[:2]}); unknown vias {unknown}; by via {vias}")
    held_line = [m for m in messages if m.startswith(BW.LOG_HOLD_FIRST_HELD)]
    released = [m for m in messages if BW.LOG_HOLD_RELEASED_VIA in m and m.startswith(BW.LOG_HOLD)]
    faulted = [m for m in messages if m.startswith(BW.LOG_HOLD_FAULTED.split(" (", 1)[0])]
    led.check("S135T-LOG", bool(held_line) and bool(released) and not faulted,
              f"{len(held_line)} HELD line(s), {len(released)} release line(s), faulted {[m[:120] for m in faulted[:2]]}")


# ================================================================================================ frames
def _start(actor: int, *, player: bool, cmd: int, sub: int, tar: int, kind: int, num: int, speed: int = 5,
           cursor: int = 0) -> tuple:
    """A fresh bench START (s133's 76-byte record, this bench's nonce) -> (id, bytes)."""
    act_id = next(_IDS)
    flags = (BW.ACTOR_IS_PLAYER if player else 0) | BW.ACTOR_HOST_REWORK | (BW.ACTOR_HOST_FAST if speed >= 3 else 0)
    return act_id, BW.encode_action_start(NONCE, 1, act_id, actor, flags, cmd, sub, tar, cursor, 0, 0, kind, num, -1, speed)


def _end(act_id: int, cmd: int, sub: int) -> bytes:
    return BW.encode_action_end(NONCE, 2, act_id, cmd, sub)


def _impact(caster: int, target: int, *, act_id: int | None, fig_t: int = 0, fig_c: int = 0, tgt_raw: tuple,
            cast_raw: tuple, player_caster: bool, player_target: bool, cmd: int, sub: int, dmg: bool = True,
            seq: int | None = None) -> bytes:
    """A bench impact: ``fig_t`` / ``fig_c`` HP figures (FIG_INFO_DISP_HP: a host figure's own info, so EffectPoint
    collects it), the raws the host's frame would carry, DmgMot (the flinch) when ``dmg``; ``seq`` the horizon (fresh and
    ascending by default -- the superseded guard reads it)."""
    flags = (1 if dmg else 0) | (32 if player_target else 0) | (64 if player_caster else 0)
    return BW.encode_action_impact(NONCE, next(_SEQS) if seq is None else seq, caster, target,
                                   fig_t=(INFO_HP if fig_t else 0, fig_t, 0), fig_c=(INFO_HP if fig_c else 0, fig_c, 0),
                                   raws=(tgt_raw[0], tgt_raw[1], cast_raw[0], cast_raw[1]), flags=flags, cmd_no=cmd,
                                   sub_no=sub, act_id=act_id)


def _raws(u: dict | None, hp: int | None = None) -> tuple:
    """(raw hp, mp) of a published unit -- ``hp`` replaces its hp (0 = lethal)."""
    u = u or {}
    return (int(u.get("hp_raw") or 0) if hp is None else int(hp), int(u.get("mp") or 0))


def _act_verb(g, *args) -> tuple:
    return ar._act_verb(g, *args)


def _feed(g, frames, at_ms: int | None = None) -> tuple:
    return ar._feed(g, frames, at_ms)


def _feed_arg(frames) -> str:
    return BW.act_feed_arg([frames] if isinstance(frames, (bytes, bytearray)) else list(frames))


# ================================================================================================ the run
def run(g, field: int = cb.FIELD):
    if LEG not in LEGS:
        led = cb.Ledger(g, {"S135-LEG": f"COOP_HOLD_LEG is one of {LEGS}"})
        led.check("S135-LEG", False, f"COOP_HOLD_LEG={LEG!r} is no leg: one of {LEGS}")
        return
    if LEG == "tape":
        _run_tape(g)
        return
    calibrate = cb.CALIBRATE
    led = cb.Ledger(g, _solo_catalog(calibrate), finals=("S135-R", "S135-INV", "S135-CAL"))
    ctx = ar._ctx_new()
    try:
        _run(g, led, field, calibrate, ctx)
    except HarnessError as err:
        g.note(f"the run raised: {str(err)[:400]}")
        led.close(f"not reached: the run raised ({str(err)[:200]})")
    finally:
        g.note(f"logs archived: {ar._archive_logs(g, 'action-hold')}")
        led.close()
        if ctx["ini_ok"]:
            _release(g, led, ctx)
        else:
            led.unreached(("S135-R", "S135-INV"), "the precondition refused the run (S135-INI): nothing was set")
        if calibrate:
            led.judge_calibration("S135-CAL", LEVER_PREDICTED if ctx["probe"] else OLD_PREDICTED,
                                  LEVER_MAYBE if ctx["probe"] else ())
        led.close(final=True)


def _run(g, led: cb.Ledger, field: int, calibrate: bool, ctx: dict) -> None:
    ok, why = ar._ini_guard(g)
    led.check("S135-INI", ok, why)
    if not ok:
        led.close(f"refused to run: {why}")
        return
    ctx["ini_ok"] = True
    ctx["field"] = field                     # (the legs read the RUN's field: never cb.FIELD)
    ok, why = cb.setup(g, field, label=f"R3 s135: the replay hit hold, solo (scene {SCENE} group {GROUP})"
                                       + (" -- CALIBRATION (actbench hold off)" if calibrate else ""))
    led.check("S135-S0", ok, why)
    if not ok:
        led.close(f"the selftest role was refused -- {why}")
        return
    st = g.state
    have = ctx["probe"] = cb.has(st, PROBE)
    led.check("S135-P0", have, f"act.guest.hold keys: {sorted(_hold(st))}" if have else
              f"no `{PROBE}` (an engine before s135: no hold op will be sent)")
    g.note(f"probe stage: {cb.stage_note(st)}; act.guest.hold {'present' if have else 'ABSENT'}; act.guest "
           f"{'present' if cb.has(st, GUEST_PROBE) else 'ABSENT'}")
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
        led.unreached([c for c in HOLD_CHECKS if c != "S135-R"],
                      f"`{PROBE}` is absent: an engine before s135 (the probe fails closed; no hold op was sent)")
        return
    if calibrate:
        _act_verb(g, "hold", "off")
        ctx["levers_set"] = True
        g.note("CALIBRATION: `actbench hold off` -- the pre-s135 guest for every leg below")
    _boot_1(g, led, field, ctx)
    _boot_one(g, led, field, ctx, ("S135-L2",), _leg_l2)
    _boot_one(g, led, field, ctx, ("S135-L2R",), _leg_l2r)
    _boot_one(g, led, field, ctx, ("S135-LOST", "S135-L6"), _legs_lost_l6)
    _boot_one(g, led, field, ctx, ("S135-QSUP",), _leg_qsup)
    _boot_one(g, led, field, ctx, ("S135-DEF",), _leg_def)
    _boot_one(g, led, field, ctx, ("S135-CATCH",), _leg_catch)
    if calibrate:
        _act_verb(g, "hold", "on")


def _leg_proof(g, led: cb.Ledger) -> None:
    proof = cb.poll(g, lambda s: cb.count(cb.log_lines(g), PROOF) >= 1, 8.0, "the proof block's action-hold line")
    lines = [ln for ln in cb.log_lines(g) if PROOF in ln]
    last = lines[-1] if lines else ""
    failed = [ln for ln in lines if "action hold selftest: FAIL" in ln]
    led.check("S135-PROOF", proof is not None and PROOF_OK in last and not failed,
              (last.split("|", 2)[-1].strip()[-300:] if last else "no 'action hold selftest' line (an engine before s135 "
                                                                  "has no ActHoldSelfTest)")
              + (f"; FAIL lines: {len(failed)}" if failed else "") + f"; want '{PROOF_OK}'")


# ------------------------------------------------------------------------------------------------ battle 1 (the tape)
def _battle_1(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    """coop_action_replay's battle 1 (`actbench tape rec` + `battle 306 <group>`, the plan that cannot end the fight
    early), its result screen cleared with Session.leave_battle(stop_on_field=True) (s134 LESSON 4), the tape paged out
    and read offline -- plus the taped Defend START this bench's Leg 3 replays."""
    host = cb.has(g.state, HOST_PROBE)
    if host:
        _act_verb(g, "tape", "rec")
    if cb.poll(g, lambda s: cb.free(s) and s.ui_state == "FieldHUD" and not s.in_battle, 30.0, "a playable field") is None:
        led.unreached(("S135-PRE", "S135-TAPE"), f"not on a playable field before battle 1 (ui {g.state.ui_state!r})")
        return
    try:
        g.start_battle(SCENE, group=GROUP)
    except HarnessError as err:
        led.unreached(("S135-PRE", "S135-TAPE"), f"`battle {SCENE} {GROUP}` did not start: {str(err)[:200]}")
        return
    _samples, en = cb.watch(g, lambda s: s.commands_enabled, ar.INTRO_S)
    st = en or g.state
    names = {k: ar._unit_named(st, k) for k in ("zidane", "vivi", "garnet")}
    foes = cb.units(st, player=False)
    led.check("S135-PRE", all(names.values()) and len(foes) >= 2,
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
    _finish(g)
    if not host:
        led.check("S135-TAPE", False, f"no `{HOST_PROBE}`: an engine before s133 records no action tape")
        return
    _act_verb(g, "tape", "stop")
    t = _sub(ar._host(cb.poll(g, lambda s: _sub(ar._host(s), "tape").get("state") == "stopped", 3.0, "the tape stopped")
                      or g.state), "tape")
    frames, why = ar._dump_all(g, _num(t.get("frames")) or 0)
    ctx["tape"] = read_tape(frames, ctx)
    tp = ctx["tape"]
    led.check("S135-TAPE", not why and tp.get("attack") is not None and tp.get("defend") is not None
              and tp.get("enemy") is not None,
              why or f"{len(frames)} frame(s); Zidane's Attack START {tp.get('attack')}; a Defend START "
                     f"{tp.get('defend')}; an enemy START {tp.get('enemy')}; the plan {ctx.get('plan')}")


def _finish(g) -> None:
    """The result screen cleared the way s134 LESSON 4 says: Session.leave_battle(stop_on_field=True), then the field."""
    try:
        if g.state.in_battle or g.state.ui_state in ("BattleHUD", "BattleResult"):
            g.leave_battle(stop_on_field=True)
    except (HarnessError, AttributeError) as err:
        g.note(f"leave_battle: {str(err)[:200]}")
    cb.poll(g, lambda s: s.on_field and s.ui_state == "FieldHUD", 30.0, "the field after the battle")


def read_tape(frames: list, ctx: dict) -> dict:
    """coop_action_replay._read_tape's facts (Zidane's Attack START, Garnet's Potion START, an enemy START) + a player's
    DEFEND START (cmd 4: its kind, num, sub -- Leg 3's short replay that hits only its caster). PURE over the paged
    frames [(i, ms, bytes)]."""
    out = ar._read_tape(frames, ctx)
    for _i, _ms, b in frames:
        d = BW.decode_action(b)
        if d is None or BW.classify_action(d) != "start" or not d["actor_flags"] & BW.ACTOR_IS_PLAYER:
            continue
        if d["act_cmd_no"] == BW.CMD_DEFEND_ID and d["vfx_kind"] != BW.VFX_KIND_NONE:
            out["defend"] = {"kind": d["vfx_kind"], "num": d["vfx_num"], "sub": d["act_sub_no"]}
            break
    else:
        out["defend"] = None
    return out


# ------------------------------------------------------------------------------------------------ boots
def _boot(g, field: int) -> tuple:
    """coop_action_replay._boot's steps (`endbench clear`, `dioboot <scene> <group>`, the steady phase AND the steady
    latch) -- its latch read as a NUMBER (a normal_ms of 0 is a latch: s134's `or -1` read it as none). (state or None,
    why)."""
    cb.try_ns(g, "endbench", "clear")
    ok, why = cb.boot(g, SCENE, GROUP)
    if not ok:
        cb.back_to_field(g, field)
        return None, why
    st = cb.poll(g, lambda s: cb.steady(s) and _n(cb.path(s, "netsync.diorama.intro.normal_ms"), -1) >= 0,
                 cb.STEADY_S, "the steady phase and its latch")
    if st is None:
        cb.leave(g, field)
        return None, "the diorama never reached its steady latch"
    g.wait_frames(5)
    return g.state, ""


def _out(g, field: int) -> None:
    ar._out(g, field)


def _guard(led: cb.Ledger, ids, leg, *args) -> None:
    ar._guard(led, ids, leg, *args)


def _boot_one(g, led: cb.Ledger, field: int, ctx: dict, ids: tuple, leg) -> None:
    """One boot for legs that END something (a death, a leave, a defeat): boot, steady, the leg, then out (a leg that
    left already -- L6's `dioleave` -- makes `_out` a plain arrival on the field)."""
    st, why = _boot(g, field)
    if st is None:
        led.unreached(ids, f"the boot failed: {why}")
        return
    try:
        _guard(led, ids, leg, g, led, ctx)
    finally:
        led.unreached(ids, "the boot ended before this leg")
        _out(g, field)


def _cast(x, ctx: dict) -> dict:
    """The diorama's cast by WIRE (coop_action_replay._who: Zidane's seat is the selftest stand-in -- s134 LESSON 1)."""
    return ar._who(x, ctx)


def _attack_start(x, ctx: dict, target_wire: int) -> tuple:
    """Zidane's seat's Attack on ``target_wire`` (kind 3, the TAPED num and host Speed). (id, bytes) or (None, why)."""
    zu, zw = _cast(x, ctx)["zidane"]
    zw = zw if zw is not None else ctx.get("zidane_wire")
    att = (ctx.get("tape") or {}).get("attack")
    if zw is None or att is None or target_wire is None:
        return None, f"no Zidane seat ({zw}), taped Attack ({att}) or target wire ({target_wire})"
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    speed = att.get("speed") if isinstance(att.get("speed"), int) else 5
    return _start(zw, player=True, cmd=acmd, sub=asub, tar=ar._bit(target_wire), kind=BW.VFX_KIND_SPECIAL,
                  num=att["num"], speed=speed)


def _summon_start(x, ctx: dict, tar: int) -> tuple:
    """Garnet's LONG summon (SummonGarnet / Leviathan, Leviathan__Full: s134's E3 replay -- it outlives W3's 4 s) on the
    wire mask ``tar``. (id, bytes) or (None, why)."""
    _gu, gw = _cast(x, ctx)["garnet"]
    if gw is None or not tar:
        return None, f"no Garnet seat ({gw}) or no target ({tar})"
    return _start(gw, player=True, cmd=BW.CMD_SUMMON_GARNET, sub=BW.ABILITY_LEVIATHAN_ID, tar=tar,
                  kind=BW.VFX_KIND_SPECIAL, num=BW.SPECIAL_LEVIATHAN_FULL, cursor=2)


def _enemy_start(x, ctx: dict, target_wire: int) -> tuple:
    """Fang 1's taped enemy attack (kind 2, num == sub) on ``target_wire``. (id, bytes, the Fang's wire) or (None, why,
    None)."""
    fu, fw = _cast(x, ctx)["fang1"]
    en = (ctx.get("tape") or {}).get("enemy")
    if fw is None or en is None or target_wire is None:
        return None, f"no Fang 1 ({fw}), taped enemy START ({en}) or target ({target_wire})", None
    act_id, frame = _start(fw, player=False, cmd=en["cmd"], sub=en["sub"], tar=ar._bit(target_wire),
                           kind=BW.VFX_KIND_ENEMY, num=en["sub"])
    return act_id, frame, fw


def _wait_rest(g, base: dict, timeout: float = LONG_S):
    """Every replay ended (running 0) after the leg -- a long summon past ``timeout`` is cleared (`actbench clear`)."""
    st = cb.poll(g, lambda s: _gv(s, "running") == 0 and _gv(s, "inbox") == 0, timeout, "the leg's replays at rest")
    if st is None:
        _act_verb(g, "clear")
        st = cb.poll(g, lambda s: _gv(s, "running") == 0, 5.0, "the clear")
    return st or g.state


def _watch_leg(g, until, timeout: float = REPLAY_S) -> tuple:
    """Every publish until ``until`` -> (the judges' samples, the raw states, the state that ended it or None)."""
    states, end = cb.watch(g, until, timeout)
    return [_sample(s) for s in states], states, end


# ---- boot 1
BOOT_1_LEGS = ("S135-BOOT", "S135-L1", "S135-L1F", "S135-L5", "S135-L3", "S135-L4", "S135-L4N", "S135-L7", "S135-REP",
               "S135-DSK", "S135-L8", "S135-TD")


def _boot_1(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    st, why = _boot(g, field)
    if st is None:
        led.unreached(BOOT_1_LEGS, f"boot 1 failed: {why}")
        return
    hs = _hold(st)
    led.check("S135-BOOT", hs != {} and _hv(st, "held_now") == 0 and _hv(st, "queued_now") == 0
              and _hv(st, "life_mask") == 0 and _gv(st, "running") == 0, _hbrief(st))
    try:
        # THE ORDER (s134 LESSON 3): nothing here kills; L8 (a superseded kill: a defect would kill Fang 2) and TD (the
        # teardown) run last
        for ids, leg in ((("S135-L1", "S135-L1F"), _leg_l1), (("S135-L5",), _leg_l5), (("S135-L3",), _leg_l3),
                         (("S135-L4", "S135-L4N"), _leg_l4), (("S135-L7",), _leg_l7), (("S135-REP",), _leg_rep),
                         (("S135-DSK",), _leg_dsk), (("S135-L8",), _leg_l8), (("S135-TD",), _leg_td)):
            _guard(led, ids, leg, g, led, ctx)
    finally:
        led.unreached(BOOT_1_LEGS, "boot 1 ended before this leg")
        _out(g, field)


def _leg_l1(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    cast = _cast(st, ctx)
    (zu, zw) = cast["zidane"]
    act_id, frame, fw = _enemy_start(st, ctx, zw)
    if act_id is None or zu is None:
        led.unreached(("S135-L1", "S135-L1F"), f"{frame} (Zidane seat {zw})")
        return
    fu = cast["fang1"][0]
    zslot = int(zu["slot"])
    base = _hbase(st)
    hp1 = max(1, int(zu.get("hp_raw") or 0) - 7)
    hit = _impact(fw, zw, act_id=act_id, fig_t=FIG["L1"], tgt_raw=_raws(zu, hp1), cast_raw=_raws(fu),
                  player_caster=False, player_target=True, cmd=(ctx["tape"]["enemy"])["cmd"],
                  sub=ctx["tape"]["enemy"]["sub"])
    try:                                     # ONE request: the impact L1_IMPACT_AFTER_MS after the START (still before its hit)
        g.send(f"netsync actbench feed {_feed_arg(frame)}",
               f"netsync actbench feedat {L1_IMPACT_AFTER_MS} {_feed_arg(hit)}", timeout=20.0)
    except HarnessError as err:
        led.unreached(("S135-L1", "S135-L1F"), f"the feeds were refused: {str(err)[:300]}")
        return
    states, end = cb.watch_from(g, g.state, _replay_over(base), REPLAY_S)
    samples = [_sample(s) for s in states]
    g.wait_frames(5)
    x = g.state
    # the owner's rule: the BARS follow the host at arrival -- on a publish taken BEFORE the replay's hit (a defect that
    # deferred the lane to the release would only show it after the hit)
    follows = [s for s in states if ar._unit(s, zslot).get("hp_raw") == hp1 and _first_hit(s) < 0]
    held = [s for s in states if _hv(s, "held_now") >= 1 and _first_hit(s) < 0]
    ok, detail = judge_figure_waits(samples, FIG["L1"], slot=zw)
    lag = _lag(x)
    led.check("S135-L1", ok and bool(follows) and bool(held) and _hv(x, "rel_hit") == base["rel_hit"] + 1
              and _n(lag.get("n"), 0) == base["lag_n"] + 1 and _n(lag.get("max"), -1) >= 0,
              f"{detail}; hp_raw {hp1} before the hit on {len(follows)} publish(es); held while unhit on {len(held)} "
              f"publish(es); "
              f"{_hbrief(x)}")
    mots = [(_gv(s, "battle_ms"), _first_hit(s), ar._unit(s, zslot).get("mot")) for s in states]
    tail, _ = cb.watch(g, lambda s: False, 1.5) if not any(m in (BW.MP_DAMAGE1, BW.MP_DAMAGE2) and fh >= 0
                                                          for _b, fh, m in mots) else ([], None)
    mots += [(_gv(s, "battle_ms"), _first_hit(s), ar._unit(s, zslot).get("mot")) for s in tail]
    fok, fdetail = judge_flinch(mots, _first_hit(x))
    led.check("S135-L1F", fok, fdetail)


def _n(v, default: int) -> int:
    """A published int (a 0 stays 0), else ``default``."""
    v = _num(v)
    return default if v is None else v


def _replay_over(base: dict):
    """until: the fed replay ended (or aborted) and nothing runs -- past its Figure point (a hit's figure is shown before
    the sequence ends), whatever the hold did."""
    return lambda s: (_gv(s, "ended") > base["ended"] or _gv(s, "aborted") > base["aborted"]) and _gv(s, "running") == 0


def _watch_after_feed(g, frames, until, timeout: float = REPLAY_S) -> tuple:
    """Feed ``frames`` (ONE drain) and read every publish from the feed's own state on until ``until``."""
    st, why = _feed(g, frames)
    if st is None:
        return [], [], None
    states, end = cb.watch_from(g, st, until, timeout)
    return [_sample(s) for s in states], states, end


def _leg_l5(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    cast = _cast(st, ctx)
    (zu, zw), (fu, fw) = cast["zidane"], cast["fang1"]
    act_id, frame = _attack_start(st, ctx, fw)
    if act_id is None:
        led.check("S135-L5", False, f"not reached: {frame}")
        return
    base = _hbase(st)
    st1, why = _feed(g, frame)
    hit = cb.poll(g, lambda s: _gv(s, "hits") > base["hits"], 5.0, "the replay's hit")
    if st1 is None or hit is None:
        led.check("S135-L5", False, f"not reached: {why or 'the replay never hit'}; {ar._brief(g.state)}")
        return
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    imp = _impact(zw, fw, act_id=act_id, fig_t=FIG["L5"], tgt_raw=_raws(fu, max(1, int(fu.get("hp_raw") or 0) - 5)),
                  cast_raw=_raws(zu), player_caster=True, player_target=False, cmd=acmd, sub=asub)
    _samples, _states, end = _watch_after_feed(g, imp, lambda s: figs_of(_figs(s), FIG["L5"]) != [], 5.0)
    x = end or g.state
    shown = figs_of(_figs(x), FIG["L5"])
    lag = _lag(x)
    led.check("S135-L5", _hv(x, "rel_late") == base["rel_late"] + 1 and len(shown) == 1 and shown[0].get("via") == "late"
              and _n(lag.get("min"), 0) < 0,
              f"figure {shown}; lag {lag}; {_hbrief(x)}")
    _wait_rest(g, base, REPLAY_S)


def _leg_l3(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    cast = _cast(st, ctx)
    (zu, zw), (fu2, fw2) = cast["zidane"], cast["fang2"]
    dfd = (ctx.get("tape") or {}).get("defend")
    if zw is None or fw2 is None or dfd is None:
        led.check("S135-L3", False, f"not reached: Zidane seat {zw}, Fang 2 {fw2}, taped Defend {dfd}")
        return
    base = _hbase(st)
    act_id, frame = _start(zw, player=True, cmd=BW.CMD_DEFEND_ID, sub=dfd["sub"], tar=ar._bit(zw), kind=dfd["kind"],
                           num=dfd["num"])
    imp = _impact(zw, fw2, act_id=act_id, fig_t=FIG["L3"], tgt_raw=_raws(fu2), cast_raw=_raws(zu), player_caster=True,
                  player_target=False, cmd=BW.CMD_DEFEND_ID, sub=dfd["sub"], dmg=False)
    _samples, _states, end = _watch_after_feed(g, [frame, imp], lambda s: figs_of(_figs(s), FIG["L3"]) != [], 6.0)
    x = end or g.state
    ok, detail = judge_release(_figs(x), FIG["L3"], "end", 0, BW.ACT_HOLD_TIMEOUT_MS - 1)
    led.check("S135-L3", ok and _hv(x, "rel_end") == base["rel_end"] + 1,
              f"{detail}; last {cb.pick(_last(x), 'id', 'state', 'why', 'hits')}; {_hbrief(x)}")
    _wait_rest(g, base, REPLAY_S)


def _leg_l4(g, led: cb.Ledger, ctx: dict) -> None:
    """Leg 4 (timeout) judged on rel_timeout and the engine's release line -- its figure REPORTED (THE HIDE WINDOW: the
    summon's PlaySFX hides Vivi, a non-target, and btl2d drops a figure on a hidden unit); then L4N, fed only once the
    summon is at rest (no sequence in flight hides Vivi), on the arrival path's FIGURE (the fix pass: rtiming-1)."""
    st = g.state
    cast = _cast(st, ctx)
    (gu, gw), (vu, vw) = cast["garnet"], cast["vivi"]
    fw1, fw2 = cast["fang1"][1], cast["fang2"][1]
    act_id, frame = _summon_start(st, ctx, ar._bit(fw1) | ar._bit(fw2))
    if act_id is None or vw is None or vu is None:
        led.unreached(("S135-L4", "S135-L4N"), f"{frame} (Vivi {vw})")
        return
    base = _hbase(st)
    imp = _impact(gw, vw, act_id=act_id, fig_t=FIG["L4"], tgt_raw=_raws(vu), cast_raw=_raws(gu), player_caster=True,
                  player_target=True, cmd=BW.CMD_SUMMON_GARNET, sub=BW.ABILITY_LEVIATHAN_ID, dmg=False)
    at = cb.mark(g)
    _samples, _states, end = _watch_after_feed(g, [frame, imp], lambda s: _hv(s, "rel_timeout") > base["rel_timeout"],
                                               BW.ACT_HOLD_TIMEOUT_MS / 1000.0 + 5.0)
    x = end or g.state
    lines = cb.wait_log(g, at, release_needle(act_id, vw), 3.0)
    ok, detail = judge_timer_release(lines, act_id, vw, "timeout", BW.ACT_HOLD_TIMEOUT_MS,
                                     BW.ACT_HOLD_TIMEOUT_MS + FIGURE_SLACK_MS)
    led.check("S135-L4", ok and _hv(x, "rel_timeout") == base["rel_timeout"] + 1,
              f"{detail}; figure {FIG['L4']} {figs_of(_figs(x), FIG['L4'])} (REPORTED, never judged: the summon's "
              f"PlaySFX may hide Vivi); {_hbrief(x)}")
    # L4N's IN-RUN RED: its predicate on L4's own state (figure 5138 if shown, held +1) must read False
    l4n_red = arrival_pred(_figs(x), FIG["L4"], base["held"], _hv(x, "held"))
    # the feedat variant, with NO summon in flight (the fix pass: rtiming-1): an impact naming NO START (an id nothing
    # registered) -- the arrival path, never held -- on a Vivi no sequence hides
    y0 = _wait_rest(g, base)
    held0 = _hv(y0, "held")
    orphan = _impact(gw, vw, act_id=next(_IDS), fig_t=FIG["L4N"], tgt_raw=_raws(ar._unit(y0, int(vu["slot"]))),
                     cast_raw=_raws(gu), player_caster=True, player_target=True, cmd=BW.CMD_SUMMON_GARNET,
                     sub=BW.ABILITY_LEVIATHAN_ID, dmg=False)
    _s, _st, end2 = _watch_after_feed(g, orphan, lambda s: figs_of(_figs(s), FIG["L4N"]) != [], 3.0)
    y = end2 or g.state
    shown = figs_of(_figs(y), FIG["L4N"])
    led.check("S135-L4N", arrival_pred(_figs(y), FIG["L4N"], held0, _hv(y, "held")) and l4n_red is False,
              f"figure {shown} (fed with running {_gv(y0, 'running')}); held {held0} -> {_hv(y, 'held')}; the in-run red "
              f"(the predicate on L4's state: figure {figs_of(_figs(x), FIG['L4'])}, held {base['held']} -> "
              f"{_hv(x, 'held')}) read {l4n_red!r} (want False)")


def _leg_l7(g, led: cb.Ledger, ctx: dict) -> None:
    """Leg 7 (host-done) judged on rel_hostdone and the engine's release line; the figure REPORTED (THE HIDE WINDOW)."""
    st = g.state
    cast = _cast(st, ctx)
    (gu, gw), (vu, vw) = cast["garnet"], cast["vivi"]
    fw1, fw2 = cast["fang1"][1], cast["fang2"][1]
    act_id, frame = _summon_start(st, ctx, ar._bit(fw1) | ar._bit(fw2))
    if act_id is None or vw is None:
        led.check("S135-L7", False, f"not reached: {frame} (Vivi {vw})")
        return
    base = _hbase(st)
    imp = _impact(gw, vw, act_id=act_id, fig_t=FIG["L7"], tgt_raw=_raws(vu), cast_raw=_raws(gu), player_caster=True,
                  player_target=True, cmd=BW.CMD_SUMMON_GARNET, sub=BW.ABILITY_LEVIATHAN_ID, dmg=False)
    at = cb.mark(g)
    try:                                                 # ONE request: the END due 100 ms after the step two frames on
        g.send(f"netsync actbench feed {_feed_arg([frame, imp])}",
               f"netsync actbench feedat 100 {_feed_arg(_end(act_id, BW.CMD_SUMMON_GARNET, BW.ABILITY_LEVIATHAN_ID))}",
               timeout=20.0)
    except HarnessError as err:
        led.check("S135-L7", False, f"not reached: the feeds were refused: {str(err)[:300]}")
        return
    end = cb.poll(g, lambda s: _hv(s, "rel_hostdone") > base["rel_hostdone"], BW.ACT_HOLD_TIMEOUT_MS / 1000.0 + 5.0,
                  "the host-done release")
    x = end or g.state
    lines = cb.wait_log(g, at, release_needle(act_id, vw), 3.0)
    ok, detail = judge_timer_release(lines, act_id, vw, "hostdone", HOSTDONE_MS - 50, HOSTDONE_MS + FIGURE_SLACK_MS)
    led.check("S135-L7", ok and _hv(x, "rel_hostdone") == base["rel_hostdone"] + 1,
              f"{detail}; figure {FIG['L7']} {figs_of(_figs(x), FIG['L7'])} (REPORTED, never judged); {_hbrief(x)}")
    _wait_rest(g, base)


def _leg_rep(g, led: cb.Ledger, ctx: dict) -> None:
    """Amendment 9: three STARTs of Zidane's seat in ONE request, two frames apart (the agent runs a request's next step
    Block(2) frames after a `netsync` verb): A launches, B parks behind it with its held impact, C supersedes B."""
    st = g.state
    cast = _cast(st, ctx)
    (zu, zw), (fu, fw), (fu2, fw2) = cast["zidane"], cast["fang1"], cast["fang2"]
    a_id, a = _attack_start(st, ctx, fw)
    b_id, b = _attack_start(st, ctx, fw)
    c_id, c = _attack_start(st, ctx, fw)
    if a_id is None or fw2 is None:
        led.check("S135-REP", False, f"not reached: {a} (Fang 2 {fw2})")
        return
    base = _hbase(st)
    sup0 = _gv(st, "superseded")
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    imp = _impact(zw, fw2, act_id=b_id, fig_t=FIG["REP"], tgt_raw=_raws(fu2), cast_raw=_raws(zu), player_caster=True,
                  player_target=False, cmd=acmd, sub=asub)
    try:
        g.send(f"netsync actbench feed {_feed_arg(a)}", f"netsync actbench feed {_feed_arg([b, imp])}",
               f"netsync actbench feed {_feed_arg(c)}", timeout=20.0)
    except HarnessError as err:
        led.check("S135-REP", False, f"not reached: the batched feeds were refused: {str(err)[:300]}")
        return
    end = cb.poll(g, lambda s: figs_of(_figs(s), FIG["REP"]) != [] or _gv(s, "superseded") > sup0, 5.0,
                  "the supersede")
    x = end or g.state
    g.wait_frames(3)
    x = g.state
    shown = figs_of(_figs(x), FIG["REP"])
    led.check("S135-REP", _gv(x, "superseded") == sup0 + 1 and _hv(x, "rel_replaced") == base["rel_replaced"] + 1
              and len(shown) == 1 and shown[0].get("via") == "replaced",
              f"superseded {sup0} -> {_gv(x, 'superseded')}; figure {shown}; {_hbrief(x)}")
    _wait_rest(g, base, REPLAY_S)


def _leg_dsk(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    cast = _cast(st, ctx)
    (zu, zw), (fu, fw) = cast["zidane"], cast["fang1"]
    act_id, frame = _attack_start(st, ctx, fw)
    if act_id is None or zu is None:
        led.check("S135-DSK", False, f"not reached: {frame}")
        return
    base = _hbase(st)
    zslot = int(zu["slot"])
    recoil = max(1, int(zu.get("hp_raw") or 0) - 11)
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    imp = _impact(zw, fw, act_id=act_id, fig_t=FIG["DSK"], fig_c=FIG["DSK_C"],
                  tgt_raw=_raws(fu, max(1, int(fu.get("hp_raw") or 0) - 3)), cast_raw=_raws(zu, recoil),
                  player_caster=True, player_target=False, cmd=acmd, sub=asub)
    samples, states, end = _watch_after_feed(g, [frame, imp], _replay_over(base))
    g.wait_frames(5)
    x = g.state
    follows = [s for s in states if ar._unit(s, zslot).get("hp_raw") == recoil and _first_hit(s) < 0]   # before the hit
    ok, detail = judge_figure_waits(samples, FIG["DSK"], slot=fw)
    early_c = [s for s in samples if s["first_hit_ms"] < 0 and figs_of(s["figs"], FIG["DSK_C"])]
    caster = figs_of(_figs(x), FIG["DSK_C"])
    led.check("S135-DSK", ok and bool(follows) and not early_c,
              f"{detail}; the caster's hp_raw {recoil} before the hit on {len(follows)} publish(es); its recoil figure "
              f"{FIG['DSK_C']} before the hit {len(early_c)}, shown {caster} (an Attack's Figure point names the target "
              f"only: reported, NOT PROVEN); {_hbrief(x)}")
    _wait_rest(g, base, REPLAY_S)


def _leg_l8(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    cast = _cast(st, ctx)
    (zu, zw), (gu, gw), (fu2, fw2) = cast["zidane"], cast["garnet"], cast["fang2"]
    fw1 = cast["fang1"][1]
    a_id, a = _summon_start(st, ctx, ar._bit(fw1))                     # A: the long summon on Fang 1 ONLY
    b_id, b = _attack_start(st, ctx, fw2)                               # B: Zidane's seat's Attack on Fang 2
    if a_id is None or b_id is None or fu2 is None:
        led.check("S135-L8", False, f"not reached: {a if a_id is None else b} (Fang 2 {fw2})")
        return
    base = _hbase(st)
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    seq_a = next(_SEQS)
    seq_b = next(_SEQS)                                                 # B is NEWER
    kill = _impact(gw, fw2, act_id=a_id, fig_t=FIG["L8"], tgt_raw=_raws(fu2, 0), cast_raw=_raws(gu),
                   player_caster=True, player_target=False, cmd=BW.CMD_SUMMON_GARNET, sub=BW.ABILITY_LEVIATHAN_ID,
                   seq=seq_a)
    change = _impact(zw, fw2, act_id=b_id, tgt_raw=_raws(fu2, max(1, int(fu2.get("hp_raw") or 0) - 2)),
                     cast_raw=_raws(zu), player_caster=True, player_target=False, cmd=acmd, sub=asub, dmg=False,
                     seq=seq_b)
    at = cb.mark(g)
    # (until A's timeout release -- never its figure: Fang 2 is a non-target of A's summon, THE HIDE WINDOW)
    _samples, states, end = _watch_after_feed(g, [a, b, kill, change],
                                              lambda s: _hv(s, "rel_timeout") > base["rel_timeout"],
                                              BW.ACT_HOLD_TIMEOUT_MS / 1000.0 + 5.0)
    g.wait_frames(10)
    x = g.state
    shown = figs_of(_figs(x), FIG["L8"])
    lines = cb.wait_log(g, at, release_needle(a_id, fw2), 3.0)
    ok, detail = judge_timer_release(lines, a_id, fw2, "timeout", BW.ACT_HOLD_TIMEOUT_MS,
                                     BW.ACT_HOLD_TIMEOUT_MS + FIGURE_SLACK_MS, superseded=True)
    dead = [cb.frame_of(s) for s in states if _alive(s, int(fu2["slot"])) is False]
    led.check("S135-L8", ok and _hv(x, "superseded") == base["superseded"] + 1 and _alive(x, int(fu2["slot"])) is True
              and not dead and _hv(x, "rel_hit") >= base["rel_hit"] + 1,
              f"A: {detail}; superseded {base['superseded']} -> {_hv(x, 'superseded')}; Fang 2 alive "
              f"{_alive(x, int(fu2['slot']))!r} (dead on {dead[:3]}); figure {FIG['L8']} {shown} (REPORTED, never "
              f"judged); {_hbrief(x)}")
    _wait_rest(g, base)


def _leg_td(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    cast = _cast(st, ctx)
    (gu, gw), (vu, vw) = cast["garnet"], cast["vivi"]
    fw1 = cast["fang1"][1]
    act_id, frame = _summon_start(st, ctx, ar._bit(fw1))     # Fang 1 ONLY: L8 (right before) never touches it
    if act_id is None or vu is None:
        led.check("S135-TD", False, f"not reached: {frame} (Vivi {vw})")
        return
    base = _hbase(st)
    kill = _impact(gw, vw, act_id=act_id, fig_t=FIG["TD"], tgt_raw=_raws(vu, 0), cast_raw=_raws(gu), player_caster=True,
                   player_target=True, cmd=BW.CMD_SUMMON_GARNET, sub=BW.ABILITY_LEVIATHAN_ID)
    st1, why = _feed(g, [frame, kill])
    held = cb.poll(g, lambda s: _hv(s, "life_mask") & ar._bit(vw), 3.0, "the held kill")
    if st1 is None or held is None:
        led.check("S135-TD", False, f"not reached: {why or 'the kill was never held'}; {_hbrief(g.state)}")
        return
    s1, w1 = _act_verb(g, "teardown")
    g.wait_frames(90)                                    # past any hit the dropped action could still land
    x = g.state
    led.check("S135-TD", s1 is not None and _hv(x, "discarded") == base["discarded"] + 1 and _hv(x, "life_mask") == 0
              and _alive(x, int(vu["slot"])) is True and not figs_of(_figs(x), FIG["TD"]),
              w1 or f"Vivi alive {_alive(x, int(vu['slot']))!r}; figure {figs_of(_figs(x), FIG['TD'])}; {_hbrief(x)}")


# ---- boots 2-5
def _held_kill_with_unit(g, ctx: dict, fig: int) -> tuple:
    """Zidane's seat's Attack on Fang 1 + a LETHAL impact, batched in ONE request with `actbench unit <Fang 1> dead`
    (two frames on: the drain has held the impact, the replay is in its run-out). (the request's state or None, Fang 1's
    unit, its wire, the base, why)."""
    st = g.state
    cast = _cast(st, ctx)
    (zu, zw), (fu, fw) = cast["zidane"], cast["fang1"]
    act_id, frame = _attack_start(st, ctx, fw)
    if act_id is None or fu is None:
        return None, fu, fw, {}, f"not reached: {frame}"
    base = _hbase(st)
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    kill = _impact(zw, fw, act_id=act_id, fig_t=fig, tgt_raw=_raws(fu, 0), cast_raw=_raws(zu), player_caster=True,
                   player_target=False, cmd=acmd, sub=asub)
    try:
        g.send(f"netsync actbench feed {_feed_arg([frame, kill])}", f"netsync actbench unit {fw} dead", timeout=20.0)
    except HarnessError as err:
        return None, fu, fw, base, f"the batched request was refused: {str(err)[:300]}"
    return g.state, fu, fw, base, ""


def _leg_l2(g, led: cb.Ledger, ctx: dict) -> None:
    at = cb.mark(g)
    x0, fu, fw, base, why = _held_kill_with_unit(g, ctx, FIG["L2"])
    if x0 is None:
        led.check("S135-L2", False, why)
        return
    fslot = int(fu["slot"])
    # (LOST's in-run red: this op, where the mask DID protect the unit, must read False under LOST's predicate)
    ctx["l2_op"] = {"alive": _alive(x0, fslot), "first_hit": _first_hit(x0), "held_now": _hv(x0, "held_now"),
                    "mask_skips": _hv(x0, "mask_skips"), "base_skips": base["mask_skips"]}
    lines = cb.wait_log(g, at, BW.LOG_HOLD_UNIT_SKIPPED, 2.0)
    skipped = cb.count(lines, BW.LOG_HOLD_UNIT_SKIPPED) == 1
    before = _alive(x0, fslot) is True and bool(_hv(x0, "life_mask") & ar._bit(fw)) and _first_hit(x0) < 0
    states, after = cb.watch(g, lambda s: _alive(s, fslot) is False and (_num(ar._unit(s, fslot).get("die_seq")) or 0) > 0,
                             REPLAY_S)
    x = after or g.state
    early = [cb.frame_of(s) for s in states if _alive(s, fslot) is False and _first_hit(s) < 0]
    led.check("S135-L2", before and skipped and _hv(x0, "mask_skips") == base["mask_skips"] + 1 and after is not None
              and not early and _first_hit(x) >= 0 and _hv(x, "life_mask") == 0
              and _hv(x, "rel_hit") == base["rel_hit"] + 1,
              f"at the op: alive {_alive(x0, fslot)!r}, mask 0x{_hv(x0, 'life_mask'):02X}, first_hit {_first_hit(x0)}, "
              f"mask_skips +{_hv(x0, 'mask_skips') - base.get('mask_skips', 0)}, the SKIPPED line {skipped}; dead before "
              f"the hit on {early[:3]}; after: die_seq {ar._unit(x, fslot).get('die_seq')!r}; {_hbrief(x)}")


def _leg_l2r(g, led: cb.Ledger, ctx: dict) -> None:
    at = cb.mark(g)
    s1, w1 = _act_verb(g, "lifeskip", "off")
    try:
        x0, fu, fw, base, why = _held_kill_with_unit(g, ctx, FIG["L2R"])
        if x0 is None or s1 is None:
            led.check("S135-L2R", False, why or f"`lifeskip off` was refused: {w1}")
            return
        fslot = int(fu["slot"])
        lines = cb.wait_log(g, at, BW.LOG_HOLD_UNIT_APPLIED, 2.0)
        held = bool(_hv(x0, "held_now")) or bool(_hv(x0, "life_mask") & ar._bit(fw))
        # the fix pass (life-1): that record STAMPED the slot, so the held kill -- released later, by its hit or the
        # replay's end -- counts superseded (its life change already applied by a newer state)
        rel = cb.poll(g, lambda s: _hv(s, "held_now") == 0, REPLAY_S, "the held kill's release")
        x = rel or g.state
        led.check("S135-L2R", held and _alive(x0, fslot) is False and _first_hit(x0) < 0
                  and _hv(x0, "mask_skips") == base["mask_skips"] and cb.count(lines, BW.LOG_HOLD_UNIT_APPLIED) == 1
                  and cb.count(lines, BW.LOG_LIFESKIP_OFF.split("] ", 1)[1]) == 1
                  and rel is not None and _hv(x, "superseded") == base["superseded"] + 1,
                  f"at the op: held {held} (held_now {_hv(x0, 'held_now')}, mask 0x{_hv(x0, 'life_mask'):02X}), alive "
                  f"{_alive(x0, fslot)!r}, first_hit {_first_hit(x0)}, mask_skips +"
                  f"{_hv(x0, 'mask_skips') - base['mask_skips']}; {cb.grep(lines, 'life-mask skip', 'type-1 record')}; "
                  f"released {rel is not None}, superseded {base['superseded']} -> {_hv(x, 'superseded')} (want +1)")
    finally:
        _act_verb(g, "lifeskip", "on")


def _legs_lost_l6(g, led: cb.Ledger, ctx: dict) -> None:
    field = ctx.get("field", cb.FIELD)
    st = g.state
    cast = _cast(st, ctx)
    (fu, fw) = cast["fang1"]
    act_id, frame = _attack_start(st, ctx, fw)
    if act_id is None or fu is None:
        led.check("S135-LOST", False, f"not reached: {frame}")
    else:
        base = _hbase(st)
        fslot = int(fu["slot"])
        try:
            g.send(f"netsync actbench feed {_feed_arg(frame)}", f"netsync actbench unit {fw} dead", timeout=20.0)
            x0 = g.state
            # ITS IN-RUN RED: the same predicate on L2's at-the-op state (the mask protected Fang 1) must read False
            l2 = ctx.get("l2_op")
            red = lost_pred(**l2) if l2 else None
            led.check("S135-LOST", lost_pred(_alive(x0, fslot), _first_hit(x0), _hv(x0, "held_now"), _hv(x0, "mask_skips"),
                                             base["mask_skips"]) and red is False,
                      f"no impact arrived (none held: held_now {_hv(x0, 'held_now')}, mask 0x{_hv(x0, 'life_mask'):02X}): "
                      f"the dead record killed at once -- alive {_alive(x0, fslot)!r} before the hit (first_hit "
                      f"{_first_hit(x0)}) -- the v1 behaviour (the mask guards only what arrived); the in-run red (the "
                      f"predicate on L2's protected op {l2}) read {red!r} (want False)")
        except HarnessError as err:
            led.check("S135-LOST", False, f"not reached: the batched request was refused: {str(err)[:300]}")
        _wait_rest(g, base, REPLAY_S)
    # Leg 6: a held kill on Vivi, then a Leave (a steady boot: never mid-swirl -- s134 LESSON 2)
    st = g.state
    cast = _cast(st, ctx)
    (gu, gw), (vu, vw) = cast["garnet"], cast["vivi"]
    fw2 = cast["fang2"][1]
    act_id, frame = _summon_start(st, ctx, ar._bit(fw2))
    if act_id is None or vu is None:
        led.check("S135-L6", False, f"not reached: {frame} (Vivi {vw})")
        _out(g, field)
        return
    base = _hbase(st)
    kill = _impact(gw, vw, act_id=act_id, fig_t=FIG["L6"], tgt_raw=_raws(vu, 0), cast_raw=_raws(gu), player_caster=True,
                   player_target=True, cmd=BW.CMD_SUMMON_GARNET, sub=BW.ABILITY_LEVIATHAN_ID)
    at = cb.mark(g)
    st1, why = _feed(g, [frame, kill])
    held = cb.poll(g, lambda s: _hv(s, "life_mask") & ar._bit(vw), 3.0, "the held kill")
    if st1 is None or held is None:
        led.check("S135-L6", False, f"not reached: {why or 'the kill was never held'}; {_hbrief(g.state)}")
        _out(g, field)
        return
    ok, lwhy = cb.leave(g, field)
    x = g.state
    shown = figs_of(_figs(x), FIG["L6"])
    # the release judged on its counter and the engine's line -- the figure REPORTED (a slow leave can land inside THE
    # HIDE WINDOW: Vivi is a non-target of the summon, and the abort shows the figure before ActWindowCheck restores her)
    lines = cb.wait_log(g, at, release_needle(act_id, vw), 3.0)
    rok, rdetail = judge_timer_release(lines, act_id, vw, "abort", 0, BW.ACT_HOLD_TIMEOUT_MS)
    led.check("S135-L6", ok and rok and _hv(x, "rel_abort") == base["rel_abort"] + 1 and _hv(x, "life_mask") == 0
              and _hv(x, "discarded") == base["discarded"],
              lwhy or f"{rdetail}; figure {FIG['L6']} {shown} (REPORTED, never judged); {_hbrief(x)}")


#: the s117 lines DEF reads (coop_battle_flee_defeat's own): the settle-skipped tail -- absent on a settled annihilation
SETTLE_SKIPPED = "its per-unit settle skipped"


def _leg_def(g, led: cb.Ledger, ctx: dict) -> None:
    """Amendment 2: every seated player but Garnet killed by an impact naming NO START (the arrival path -- never `endbench
    kill`: amendment 15), then ONE request: Fang 1's attack replay on Garnet + a held LETHAL impact, and `endbench
    phase-defeat` two frames on (the fix pass, timing-3)."""
    st = g.state
    cast = _cast(st, ctx)
    (gu, gw), (fu, fw) = cast["garnet"], cast["fang1"]
    if gu is None or fu is None or gw is None:
        led.check("S135-DEF", False, "not reached: no Garnet or no Fang 1")
        return
    en = (ctx.get("tape") or {}).get("enemy") or {"cmd": BW.CMD_ENEMY_ATK, "sub": 0}
    others = [u for u in cb.units(st, player=True) if u.get("alive") and int(u["slot"]) != int(gu["slot"])]
    kills = [_impact(fw, ar._wire_of(st, u), act_id=next(_IDS), tgt_raw=_raws(u, 0), cast_raw=_raws(fu),
                     player_caster=False, player_target=True, cmd=en["cmd"], sub=en["sub"]) for u in others]
    if kills:
        _feed(g, kills)
        down = cb.poll(g, lambda s: all(_alive(s, int(u["slot"])) is False for u in others), 5.0, "the others down")
        if down is None:
            led.check("S135-DEF", False, f"not reached: the other players never went down "
                                         f"{[(u['slot'], _alive(g.state, int(u['slot']))) for u in others]}")
            return
    act_id, frame, _fw = _enemy_start(g.state, ctx, gw)
    if act_id is None:
        led.check("S135-DEF", False, f"not reached: {frame}")
        return
    base = _hbase(g.state)
    gu = ar._unit(g.state, int(gu["slot"]))
    kill = _impact(fw, gw, act_id=act_id, fig_t=FIG["DEF"], tgt_raw=_raws(gu, 0), cast_raw=_raws(fu),
                   player_caster=False, player_target=True, cmd=en["cmd"], sub=en["sub"])
    at = cb.mark(g)
    # ONE request (the fix pass: timing-3): the feed, then `endbench phase-defeat` Block(2) frames on -- the drain has held
    # the kill, and no replay hit can come in between (a second request after a poll raced the replay's own hit on Garnet)
    ok, ewhy = True, ""
    try:
        g.send(f"netsync actbench feed {_feed_arg([frame, kill])}", "netsync endbench phase-defeat", timeout=20.0)
    except HarnessError as err:
        ok, ewhy = False, f"not reached: the batched request was refused: {str(err)[:300]}"
    inj = cb.poll(g, lambda s: cb.bend(s).get("injected") is True, 8.0, "the injection") if ok else None
    x = inj or g.state
    lines = cb.new(g, at)
    e = cb.bend(x)
    # HELD is judged from the counters (no publish lands between the request's two steps): the kill entered the hold
    # (held +1) and left it by the end injection (rel_end_inject +1) -- nothing else releases it there
    led.check("S135-DEF", ok and inj is not None and _hv(x, "held") == base["held"] + 1
              and _hv(x, "rel_end_inject") == base["rel_end_inject"] + 1
              and e.get("action") == "annihilate" and e.get("inject_phase") == cb.PHASE_MENU_OFF
              and cb.count(lines, BW.LOG_HOLD_FLUSH.split("] ", 1)[1]) == 1 and cb.count(lines, SETTLE_SKIPPED) == 0,
              ewhy or f"end {cb.pick(e, 'injected', 'action', 'inject_phase', 'inject_seq', 'follow_msg')}; held "
                      f"{base['held']} -> {_hv(x, 'held')}; "
                      f"{cb.grep(lines, 'end injection released', 'diorama END', limit=400)}; {_hbrief(x)}")


def _leg_qsup(g, led: cb.Ledger, ctx: dict) -> None:
    """The fix pass (life-1 / timing-2): a QUEUED frame's free lane never stands up a unit the reconciler killed while it
    waited. ONE request: Zidane's seat's Attack on Fang 1 + a held LETHAL impact (figure 5150: the mask has Fang 1's bit)
    + an impact naming NO START from Garnet on Fang 1 (Fang 1's slot is busy: the whole frame QUEUES; Garnet's caster
    lane -- alive, not lethal, her slot not busy -- is no life lane), then `unit <Garnet> dead` two frames on (her slot is
    not masked: the record kills her and stamps her slot). The hit releases the kill; the queue drains on the next tick:
    the queued caster lane (older than the record, no life lane when it queued) is SUPERSEDED -- Garnet never stands up."""
    st = g.state
    cast = _cast(st, ctx)
    (zu, zw), (gu, gw), (fu, fw) = cast["zidane"], cast["garnet"], cast["fang1"]
    act_id, frame = _attack_start(st, ctx, fw)
    if act_id is None or gu is None or fu is None or gw is None:
        led.check("S135-QSUP", False, f"not reached: {frame if act_id is None else 'no Garnet or no Fang 1'}")
        return
    base = _hbase(st)
    gslot = int(gu["slot"])
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    kill = _impact(zw, fw, act_id=act_id, fig_t=FIG["QSUP"], tgt_raw=_raws(fu, 0), cast_raw=_raws(zu), player_caster=True,
                   player_target=False, cmd=acmd, sub=asub)
    free = _impact(gw, fw, act_id=next(_IDS), tgt_raw=_raws(fu, 0),
                   cast_raw=_raws(gu, max(1, int(gu.get("hp_raw") or 0) - 1)), player_caster=True, player_target=False,
                   cmd=acmd, sub=asub, dmg=False)
    at = cb.mark(g)
    try:
        g.send(f"netsync actbench feed {_feed_arg([frame, kill, free])}", f"netsync actbench unit {gw} dead", timeout=20.0)
    except HarnessError as err:
        led.check("S135-QSUP", False, f"not reached: the batched request was refused: {str(err)[:300]}")
        return
    x0 = g.state
    # at the op: the kill held (Fang 1 masked), the free frame QUEUED, Garnet dead and NOT masked (the record applied)
    queued = _hv(x0, "queued_now") == 1 and _hv(x0, "queued") == base["queued"] + 1
    masked = _hv(x0, "life_mask")
    at_op = queued and _alive(x0, gslot) is False and bool(masked & ar._bit(fw)) and not masked & ar._bit(gw)
    states, end = cb.watch(g, lambda s: _hv(s, "rel_queued") > base["rel_queued"] and _hv(s, "queued_now") == 0,
                           BW.ACT_HOLD_TIMEOUT_MS / 1000.0 + 5.0)
    g.wait_frames(10)
    x = g.state
    stood = [cb.frame_of(s) for s in [x0, *states, x] if _alive(s, gslot) is not False]
    lines = cb.new(g, at)
    sup_lines = [ln for ln in lines if BW.LOG_HOLD_QUEUED_FRAME.split("] ", 1)[1] in ln and BW.LOG_HOLD_SUPERSEDED in ln]
    led.check("S135-QSUP", at_op and end is not None and not stood
              and _hv(x, "superseded") == base["superseded"] + 1 and _hv(x, "rel_queued") == base["rel_queued"] + 1
              and len(sup_lines) == 1,
              f"at the op: queued_now {_hv(x0, 'queued_now')}, mask 0x{masked:02X}, Garnet alive {_alive(x0, gslot)!r}; "
              f"drained {end is not None}; Garnet stood up on {stood[:3]} (want none); superseded {base['superseded']} -> "
              f"{_hv(x, 'superseded')} (want +1); the queued release's SUPERSEDED line {len(sup_lines)}; {_hbrief(x)}")


def _leg_catch(g, led: cb.Ledger, ctx: dict) -> None:
    """The fix pass (life-2): the end-inject flush re-applies what the life mask SKIPPED. Every seated player killed by an
    impact naming no START (the arrival path), then ONE request: Fang 1's attack replay on Garnet + a held REVIVE (a
    non-lethal impact on dead Garnet, figure 5151 -- a life lane: the mask has her bit), `unit <Garnet> dead` (the host
    killed her again -- Doom, say: the record MEETS THE MASK, mask_skips +1) and `endbench phase-defeat`: the flush
    revives her (end-inject), then re-applies the skipped record BEFORE AllPlayersDown -- 'annihilate' WITH the settle."""
    st = g.state
    cast = _cast(st, ctx)
    (gu, gw), (fu, fw) = cast["garnet"], cast["fang1"]
    if gu is None or fu is None or gw is None:
        led.check("S135-CATCH", False, "not reached: no Garnet or no Fang 1")
        return
    gslot = int(gu["slot"])
    hp0 = max(1, int(gu.get("hp_raw") or 0))
    en = (ctx.get("tape") or {}).get("enemy") or {"cmd": BW.CMD_ENEMY_ATK, "sub": 0}
    party = [u for u in cb.units(st, player=True) if u.get("alive")]
    kills = [_impact(fw, ar._wire_of(st, u), act_id=next(_IDS), tgt_raw=_raws(u, 0), cast_raw=_raws(fu),
                     player_caster=False, player_target=True, cmd=en["cmd"], sub=en["sub"]) for u in party]
    if kills:
        _feed(g, kills)
    down = cb.poll(g, lambda s: all(_alive(s, int(u["slot"])) is False for u in party), 5.0, "every player down")
    if down is None or not party:
        led.check("S135-CATCH", False, f"not reached: the party never went down "
                                       f"{[(u['slot'], _alive(g.state, int(u['slot']))) for u in party]}")
        return
    act_id, frame, _fw = _enemy_start(g.state, ctx, gw)
    if act_id is None:
        led.check("S135-CATCH", False, f"not reached: {frame}")
        return
    base = _hbase(g.state)
    gu = ar._unit(g.state, gslot)
    revive = _impact(fw, gw, act_id=act_id, fig_t=FIG["CATCH"], tgt_raw=_raws(gu, hp0), cast_raw=_raws(fu),
                     player_caster=False, player_target=True, cmd=en["cmd"], sub=en["sub"], dmg=False)
    at = cb.mark(g)
    ok, ewhy = True, ""
    try:
        g.send(f"netsync actbench feed {_feed_arg([frame, revive])}", f"netsync actbench unit {gw} dead",
               "netsync endbench phase-defeat", timeout=20.0)
    except HarnessError as err:
        ok, ewhy = False, f"not reached: the batched request was refused: {str(err)[:300]}"
    inj = cb.poll(g, lambda s: cb.bend(s).get("injected") is True, 8.0, "the injection") if ok else None
    x = inj or g.state
    lines = cb.new(g, at)
    e = cb.bend(x)
    caught = [ln for ln in lines if BW.LOG_HOLD_CATCH_UP_PIECE in ln and "re-applied at the end injection" in ln]
    shown = figs_of(_figs(x), FIG["CATCH"])
    led.check("S135-CATCH", ok and inj is not None and _hv(x, "held") == base["held"] + 1
              and _hv(x, "rel_end_inject") == base["rel_end_inject"] + 1
              and _hv(x, "mask_skips") == base["mask_skips"] + 1 and len(caught) == 1 and _alive(x, gslot) is False
              and e.get("action") == "annihilate" and e.get("inject_phase") == cb.PHASE_MENU_OFF
              and cb.count(lines, SETTLE_SKIPPED) == 0,
              ewhy or f"end {cb.pick(e, 'injected', 'action', 'inject_phase', 'inject_seq', 'follow_msg')}; Garnet alive "
                      f"{_alive(x, gslot)!r}; mask_skips +{_hv(x, 'mask_skips') - base['mask_skips']}; the catch-up line "
                      f"{len(caught)}; the revive's figure {shown}; "
                      f"{cb.grep(lines, 'skipped record', 'end injection released', 'diorama END', limit=400)}; "
                      f"{_hbrief(x)}")


# ------------------------------------------------------------------------------------------------ the release
def _release(g, led: cb.Ledger, ctx: dict) -> None:
    """INV first (the last leave is behind us), then the hold levers left SET on purpose and `reset`: the 'hold levers
    back' line, and both levers at rest when re-read WITH the role."""
    fp0 = ctx.get("fp0")
    if ctx["probe"]:
        fp1, why = cb.fingerprint(g, field=ctx.get("field", cb.FIELD))
        diff = cb.fp_diff(fp0, fp1) if fp0 and fp1 else None
        led.check("S135-INV", fp0 is not None and fp1 is not None and not diff,
                  why or f"changed: {diff}; battle_no {fp0.get('_battle_no') if fp0 else None} -> "
                         f"{fp1.get('_battle_no') if fp1 else None} (a diorama's InitBattle bumps it: not judged)")
        for args in (("hold", "off"), ("lifeskip", "off")):
            _act_verb(g, *args)
    else:
        led.check("S135-INV", True, "nothing was booted (the probe failed closed): nothing to compare")
    at = cb.mark(g)
    cb.release(g)
    lines = cb.new(g, at)
    if not ctx["probe"]:
        led.check("S135-R", False, f"`{PROBE}` absent: nothing was set")
        return
    rr, rwhy = cb.reread_with_role(g)
    h = _hold(rr) if rr is not None else {}
    led.check("S135-R", rr is not None and cb.count(lines, BW.LOG_HOLD_LEVERS_BACK.split("] ", 1)[1]) == 1
              and h.get("on") is True and h.get("lifeskip") is True,
              (f"re-read WITH the role: on {h.get('on')!r}, lifeskip {h.get('lifeskip')!r}" if rr is not None else
               f"no re-read with the role ({rwhy})") + f"; {cb.grep(lines, 'released with the harness')}")


# ================================================================================================ THE TAPE LEG
def _run_tape(g) -> None:
    calibrate = cb.CALIBRATE
    led = cb.Ledger(g, _tape_catalog(calibrate), finals=("T2-SAVE", "T2-INI", "S135T-CAL"))
    ctx = ar._TapeCtx()
    try:
        _tape_leg(g, led, ctx, calibrate)
    except HarnessError as err:
        g.note(f"the tape leg raised: {str(err)[:400]}")
        led.close(f"not reached: the leg raised ({str(err)[:200]})")
    finally:
        if ctx.peer is not None and ctx.peer.how_ended is None:
            g.note(f"coop_peer replay-host: {ctx.peer.stop()}")
        if "T2-SAVE" not in led.done:
            if ctx.eng is None:
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
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'action-hold-tape')}")
        if calibrate:
            led.close("not reached: the leg ended before this check")
            led.judge_calibration("S135T-CAL", _tape_predicted(_has_hold(ctx)))
        led.close(final=True)


def _has_hold(ctx) -> bool:
    return any(isinstance(s.get("guest"), dict) and isinstance(s["guest"].get("hold"), dict) for s in ctx.samples)


def _tape_leg(g, led: cb.Ledger, ctx, calibrate: bool) -> None:
    """coop_action_replay's tape leg, step for step (its tape, its CAL sidecar, its guest config, its replay-host), judged
    on `act.guest.hold` (:func:`judge_hold_tape`)."""
    ids = list(TAPE_CHECKS)
    ctx.tape = ar.act_tape()
    if ctx.tape is None or not ctx.tape.exists():
        led.check("T2-TAPE", False, f"no s133 tape ({ctx.tape or ar.act_tape_dir()}): record one first "
                                    "(coop_action_replay's RECORDING steps)")
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
    ctx.act = ar.tape_act_facts(records, cp, ctx.nonce)
    plan = pb.plan_leg("cal", ctx.facts, ar.GRACE_MS / 1000.0)
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
    free, why = pb.port_free(ar.PORT)
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
    g.note(f"R3 s135 tape leg: {ctx.tape.name}, ActionReplay {0 if calibrate else 1}"
           + (" -- CALIBRATION (the knob)" if calibrate else ""))
    g.newgame()
    g.note(cb.seed_party(g, back_to=ctx.field))
    if g.state.field_id != ctx.field:
        g.warp(ctx.field)
    try:
        g.no_encounters(True)
    except HarnessError as err:
        g.note(f"noencounter refused ({str(err)[:160]})")
    g.wait_frames(45)
    ctx.eng = pb.EngineLog(g.engine_log())
    values = dict(ar.GUEST_VALUES, ActionReplay="0" if calibrate else "1")
    rd = Path(getattr(g, "scenario_dir", None) or g.run_dir)
    ctx.guard = pb.IniGuard(Path(g.game_path) / "Memoria.ini", values, label="coop-action-hold-tape", run_dir=rd)
    try:
        g.note(ctx.guard.apply())
    except (OSError, RuntimeError) as err:
        led.check("T2-PEER", False, f"the Memoria.ini edit failed: {err}")
        led.close("not reached: Memoria.ini could not be edited")
        return
    cfg = ar._tape_config(g, ctx, calibrate)
    if not cfg:
        led.check("T2-PEER", False, f"the engine never logged the guest config (config lines: "
                                    f"{pb.show(pb.hits(ctx.eng.lines(), 'config'))})")
        led.close("not reached: the guest config never applied")
        return
    ctx.peer = pb.PeerProc("replay-host", [ctx.tape, *pb.plan_args(plan, port=ar.PORT, code=ar.CODE)],
                           log_path=rd / "coop_peer-replay-hold.log", out_path=rd / "coop_peer-replay-hold.out")
    g.note(f"starting: {ctx.peer.command_text()}")
    ctx.peer.start()
    up = ctx.peer.wait_for(pb.PEER["listening"], 15.0, tick=lambda: ar._tape_sample(g, ctx))
    conn = ctx.peer.wait_for(pb.PEER["guest_connected"], 25.0, tick=lambda: ar._tape_sample(g, ctx)) if up else None
    start = ctx.peer.wait_for(pb.PEER["replay_start"], 10.0, tick=lambda: ar._tape_sample(g, ctx)) if conn else None
    relay = pb.hits(ctx.eng.lines(), "relay_up", pred=lambda m: m.group(3) == "guest" and m.group(2) == ar.CODE)
    knob_ok, knob_why = ar._tape_knob(cfg, calibrate, cb.has(g.state, GUEST_PROBE))
    ok = up is not None and conn is not None and start is not None and bool(relay) and knob_ok
    led.check("T2-PEER", ok, f"config: {pb.show(cfg, 1)}; {knob_why}; peer: {up[1] if up else 'never listened'} / "
                             f"{conn[1] if conn else 'no guest'} / {start[1] if start else 'no replay start'}; engine: "
                             f"{pb.show(relay, 1)}")
    if not ok:
        led.unreached(ids, "the instrument never started (T2-PEER)")
        return
    ctx.anchors["start"] = start[0]
    _tape_run(g, led, ctx)


def _tape_run(g, led: cb.Ledger, ctx) -> None:
    start = ctx.anchors["start"]
    span = float((ctx.facts.get("end") or 0.0) - (ctx.facts.get("start") or 0.0))

    def returned():
        e = ctx.eng.lines()
        el = pb.hits(e, "end_leave", after=start)
        return bool(el) and bool(pb.hits(e, "return", after=el[0][0]))
    deadline = time.time() + span + 120.0
    while time.time() < deadline and not returned():
        ar._tape_sample(g, ctx)
        time.sleep(ar.POLL_S)
    for _ in range(20):
        ar._tape_sample(g, ctx)
        time.sleep(ar.POLL_S)
    e = ctx.eng.lines()
    F, M, N = ctx.field, ctx.scene, ctx.nonce
    need = {"paired": pb.hits(e, "paired", after=start, pred=lambda m: int(m.group(1)) == F),
            "armed": pb.hits(e, "armed", after=start),
            "boot": pb.hits(e, "boot", after=start, pred=lambda m: M is None or int(m.group(1)) == M),
            "live": pb.hits(e, "live", after=start, pred=lambda m: N is None or int(m.group(2)) == N)}
    missing = [k for k, v in need.items() if not v]
    led.check("S135T-I", not missing, f"missing {missing}" if missing else "paired, ARMED, BOOT, LIVE logged")
    g.note(f"tape leg at {_dt.datetime.now():%H:%M:%S}: {len(ctx.samples)} sample(s)")
    judge_hold_tape(led, ctx.samples, [m for _t, _l, m in e])
