"""R3 GROUP 2, s136 -- FALLBACK A, ONE STOCK CLIP PER UNCOVERED ACTION (memoria-patch s136), the solo bench and its T2 tape
leg, run unattended.

THE GAP (studies/battle-coop/R3-DESIGN.md 3.3.5 and 6.10 as amended by R3-ACTION-REPLAY-AUDIT.md 2.4 -- amendments 1-6,
decisions D-a / D-b / D-c -- 3.5 and 4.8; the design's and the audit's "s125": group 2 was renumbered s133-s141). Since s134
the guest REPLAYS the host's actions, but an impact NO replay covers -- an old host without header bit 5, a declined /
stale / dropped / never-received START, ActionReplay=0, a guest without SFXRework -- still shows only the s110 player-only
MP_ATTACK swing, and an enemy's nothing at all. s136 plays ONE stock clip chosen by the ACTION, at most once per action: a
player's Item / AutoPotion / Throw -> MP_ITEM1, magic (category & 16) -> MP_MAGIC, Defend / Change -> none, any other command
-> MP_ATTACK; an ENEMY -> the first NON-IDLE caster PlayAnimation of its scene sequence (parsed, never executed; played by
name). Keyed (nonce, actId), or for an old host / id 0 by (caster, cmd, sub) within 500 ms of BATTLE time between arrivals.
The guards are the call site's (amendment 6): not lethal, not a revive, not hidden, a self-cast only without a DmgMot (D-b),
a unit free to move, the caster not acting in a replay, no end / Leave; no clip for an impact drained in a BACKLOG Update
(D-c). COVERED (no clip): an impact whose action id names a replay that launched, may still launch, a NOOP, a START a newer
one replaced or an abort-all dropped. THE CONTAINMENT LAW holds: a clip is presentation only. Read back:
`netsync.battle.act.guest.fallback` (every role): `on`, `clips`, `deduped`, `covered`, `none`, `guarded`, `backlog`,
`collapsed`, `parse_failed`, `last{actor, clip, cmd, sub, keyed_by, kind, id, via, ms}`. Bench verb (selftest role):
`netsync actbench fallback on|off` (off = the pre-s136 guest), plus s134's `feed` / `feedat` / `replay on|off`.
[fix pass] The engine also: DEFERS an id-keyed impact refused only because its caster acts in a running replay (cover-2:
it plays via "deferred" when that replay ends, or drops `guarded`); slides the old-host window with each deduped sibling
(cover-5 / timing-5 / timing-6); blocks every clip while the run-away hold waits and inside an abort-all (timing-1);
refuses a slave part, a frozen or a bi.disappear unit (stock-2) and a clip the unit lacks after stock's attach (stock-1:
`none`); and keeps a bystander's fallback clip through an abort's busy-window restore (timing-2). [fix pass 2] It also
makes an impact covered only by a still-PENDING START wait for that START's decision -- a decline plays its clip, a launch
covers it (rcover-2) --, reads the enemy AI's Loop moves (ScriptCounter1-3) and a script's scripted sequence (cmd None) as
scene sequences (rstock-1), and keeps a clip written AFTER its unit's replay aborted through the window's restore
(rtiming-1, order-aware).

THREE LEGS, one per launch (COOP_FB_LEG):
  solo (the default) -- the desktop in the forced selftest role: every fabricated leg and the lever calibration.
  tape -- THE T2 TAPE BENCH (audit 4.9): the RECORDED s133 host tape (coop_action_replay's: .harness-runs/coop-tapes/act-s133)
          replayed into this desktop as the GUEST by tools/harness/coop_peer.py `replay-host` with [Netsync] ActionReplay=0
          -- every START declines `knob`, so EVERY impact is uncovered: one clip per action through the real transport.
  arc  -- [fix pass: harness-01] THE OLD-HOST PATH THROUGH THE REAL INTAKE (audit 4.9: "the existing s117 arc tape already
          drives the old-host path"): coop_cut_hold's s117 arc tape (_coop_peer_bench.ARC_TAPE_NAME) replayed the same way --
          an old host's battle, NO START, every impact 46 bytes with no id: fallback A keyed by (caster, cmd, sub) inside
          the 500 ms window, through ActionTick (the solo OLD leg's inbox is ActionTickBench, not the real intake).

PRECONDITIONS -- THE OPERATOR'S JOB:
  * solo: Memoria.ini [Netsync] Enabled = 0 (or absent) -- the selftest role is refused on a live-configured install; the
    bench never edits Memoria.ini (S136-INI reads it READ-ONLY and, when it reads 1, records itself red and runs NOTHING).
  * tape / arc: the game CLOSED before the launch (play.py launches it), no production bridge on 49201, [SaveFile]
    AutoSaveOnlyAtMoogle 0; the leg writes [Netsync] (backed up first, restored byte-exact in the `finally`) exactly as
    coop_action_replay's tape leg does -- ActionReplay 0 (1 under COOP_CALIBRATE: its inverse knob, below); the arc leg
    writes ActionReplay 1 (an old host sends no START: nothing for the knob to decline).
  * The DLL under test deployed and the game launched on it (the orchestrator's: this bench deploys nothing).
  * COOPPARTY (studies/battle-coop/bench/coopparty.field.toml, 30604) registered: Zidane / Vivi / Garnet / Steiner (PRE).
  * UnityPy and the kit (ff9mapkit) importable: THE ORACLE reads the scene's sequences off the install, READ-ONLY.

THE ORACLE (an enemy's clip): derived OFFLINE from the scene's own sequence data -- the install's btlseq raw17 for the
boot's scene (306, BSC_EF_R004; the tape and arc legs: the tape's scene) read through the kit's seqcodec
(ff9mapkit.battle.seqcodec) and the AnimationDB name table (ff9mapkit._animdb_all), mirroring
BattleActionThread.LoadFromBtlSeq: each case-5 op's anim id through seqBaseAnim[sub] + its code, byte 255 the literal
"Idle", END's appended Idle -- then battlewire's own first-clip twin (act_fallback_first_clip, pinned against
ActFallbackSelfTest's rows). Never read from the engine under test, never from a replay of the taped START (design 6.10
named one): a replay's first VISIBLE clip cannot show a clip equal to the idle and rides the publish cadence. The taped
enemy START (battle 1) names the sub ENEMY plays; the oracle names an Idle-only sub for IDLE (scene 306's END-only
sequences). [fix pass: harness-05] It reads the BASE install's p0data2 only, so it FAILS CLOSED (ORACLE / ENEMY red, the
override's path named) when a Memoria.ini [Mod] FolderNames folder carries a loose override of that scene's raw17 or its
own p0data2.bin -- the engine would parse the override; the detail names the source actually read. (btlseq's
FixBuggedAnimations remap touches only Geo 149, which neither bench scene seats.)

THE SOLO BENCH. Field 30602 (cb.FIELD), `stateevery 1`. Battle 1 (the TAPE) is coop_action_hold's: s133's in-engine tape over
`battle 306 <COOP_ACT_GROUP, default 4>` (Fang x2) with the plan that cannot end the fight early (s134 LESSON 3: Zidane
Attacks the sturdiest standing ally once, Garnet Potions herself, every other prompt Defends until both are done and two more
prompts have passed, then `fight` to the victory) -- its result screen cleared with Session.leave_battle(stop_on_field=True)
(s134 LESSON 4) -- read offline: Zidane's Attack START (its num), Garnet's Potion START, a Defend START and an enemy START
(kind 2, num == sub). Then THE INVARIANTS (cb.fingerprint) and three diorama boots, each `dioboot 306 <group>` on 30602. Every
fed frame carries the bench's own nonce byte (0x5E, MARKER: s134's bench is 0x5C, s135's 0x5D) and every impact a figure
5161-5178 (MARKER). "ZIDANE" IN A DIORAMA (s134 LESSON 1): every selftest `dioboot` seats the selftest mirror's stand-in
("BENCH", another character's model -- Freya's at writing) at Zidane's battle-1 wire: every leg's "Zidane" is THAT seat
(coop_action_replay._who), never a unit named Zidane. THE CASTERS BY WIRE SLOT AND MODEL: Item legs -- GARNET's seat (her own
model: every Garnet row of BattleParameters.csv names a distinct MP_ITEM1 clip); Magic -- VIVI's (her own model: MP_MAGIC
distinct); Attack -- Zidane's seat (the BENCH stand-in's model: its MP_ATTACK clip distinct from its idle -- a knife Garnet's
is NOT, never an Attack caster here); the enemy -- Fang 1 (the first enemy by slot). No leg sends a `dioleave` mid-swirl (s134
LESSON 2): BACKLOG FEEDS during its boot's swirl (batched into the boot's own request) and leaves only after a steady boot.
THE ORDER (s134 LESSON 3): boot 1 kills nothing; LETHAL (a caster killed by its own blow) and BACKLOG (a fresh boot's intro)
each have their own boot. A follow-up that must land inside a dedupe window or before a boot's steady latch rides the feed's
OWN request (the agent runs a request's next step Block(2) frames on) -- never a second request after a poll (s135 LESSON).

WHAT IS PROVEN (S136-*):
  INI    precondition: [Netsync] Enabled reads 0 / absent (READ-ONLY) -- else NOTHING runs.
  S0     the harness forced the selftest role (Memoria.ini untouched).
  P0     the probe: `netsync.battle.act.guest.fallback` is published WHOLE -- exactly the agent's keys -- with `on` true
         (no lever stranded) -- else no fallback op is EVER sent (fails closed). [fix pass: harness-07]
  PROOF  the selftest proof block's line reads exactly 'action fallback selftest: OK (30 rows)' -- no FAIL line.
  PRE    precondition: battle 1 seats Zidane, Vivi and Garnet and 2+ enemies.
  TAPE   battle 1's s133 tape carries Zidane's Attack START, Garnet's Potion START and an enemy START (kind 2, num == sub).
  ORACLE scene 306's sequences read OFFLINE (above): the taped enemy sub's first non-Idle caster clip, and an Idle-only sub.
  BOOT   boot 1 steady with `act.guest.fallback` at rest: every counter 0, `last` null -- and `on` true (false under
         COOP_CALIBRATE's lever: a lever that did not land reds BOOT, so CAL names its cause).
  -- boot 1: `actbench replay off` (every START declines `lever`: every impact UNCOVERED); nothing dies --
  ITEM   Garnet's Potion on HERSELF (the self target: no DmgMot -- D-b, amendment 4) -- START + impact in ONE feed: clips +1,
         `last` {actor Garnet's wire, kind item, cmd 14, sub 236, keyed_by id, id the START's, via arrival}; her `mot` reads
         MP_ITEM1 (31) and her `anim` last.clip on a publish of the write.
  ITEMA  Garnet's Potion on VIVI (an ally target): the same, MP_ITEM1 (31).
  MAGIC  Vivi's Fire (BlackMagic / Fire, category 19: & 16) on Fang 1: kind magic, her `mot` MP_MAGIC (28).
  ATTACK Zidane's seat's Attack on Fang 1: kind attack, its `mot` MP_ATTACK (23).
  ENEMY  Fang 1's EnemyAtk sub k (the taped sub; the oracle's) on Zidane's seat, then -- the SAME request, Block(2) frames
         on: another frame, so no collapse -- [fix pass 2: rstock-1] Fang 1's LOOP move (ScriptCounter1, cmd 63) sub k, its
         own action id (fabricated: scene 306's Fangs have no Loop move; the guest reads the frame alone): clips +2, none
         +0; each write kind enemy, sub k, clip == THE ORACLE's clip of sequence k (the EnemyAtk one in a sampled `last` or
         its clip line, the LOOP one `last` at the end, cmd 63), and Fang 1's `anim` that clip on a publish of the write.
         (Before the fix the LOOP move named no scene sequence: none +1.)
  IDLE   Fang 1's EnemyAtk sub j (an Idle-only sequence, the oracle's): none +1, clips +0, parse_failed +0, `last` not its id.
         ITS IN-RUN RED: the same predicate on THIS leg's own delta with ONE CLIP INJECTED (in_run_red) must read False --
         the "no clip written" conjunct shown failing on the leg's real bucket move, every run.
  DEF    Zidane's seat's Defend and Vivi's Change (each on itself, no DmgMot) in ONE feed: none +2, clips +0.
  SELF   Vivi's Attack on HERSELF WITH a DmgMot (a confused self-hit, non-lethal): guarded +1, clips +0 (D-b's other half).
  OLD    an OLD HOST: Vivi's Fire as FIVE impacts with no action id, on ONE request (each step Block(2) agent frames on --
         33-133 ms at 60-15 fps -- and a drain at most a frame late): A, a 46-byte frame (`feed`); B and C, an id-0 extension
         and a 46-byte frame on ONE verb (`feedat 250 <B>,<C>`: one Due, so the two drain in ONE Update -- [fix pass:
         timing-4] never two `feedat`s whose spacing rides the frame rate), 267-450 ms after A; D (`feedat 500`), 550+ ms
         after A but at most 450 after B / C; E (`feedat 1100`), 600+ ms after D. [fix pass 2: rharness-03] D is the one only
         THE SLIDE dedupes: a window ANCHORED at the decision (A) would clip it, the sliding one (moved to B / C) dedupes it.
         clips +2 (A and E), deduped +3, keyed_by caster, id 0, kind magic, Vivi's `mot` MP_MAGIC; exactly TWO writes'
         battle ms (`last.ms` over every publish -- the ENGINE's clock) at least OLD_E_GAP (1000) apart: the second is E
         (D lands at most ~833 ms after A); `old_host` true.
  BURST1 one action id, THREE impacts within 100 ms (feed START + A, then -- the same request -- B and C): clips +1, deduped
         +2, keyed_by id.
  BURSTD three distinct action ids on Zidane's seat, three drains (three feeds in one request, Block(2) frames apart): clips
         +3, collapsed +0.
  BURSTC three distinct action ids on Zidane's seat in ONE drain (one feed): clips +1, collapsed +2 (counted when WRITTEN:
         a later clip on one actor in one frame overwrites the first).
  (THE PER-BOOT LOG CAP: ActFallbackWrite logs at most 8 clip lines a boot -- boot 1 writes about sixteen clips: every
  boot-1 verdict reads the counters and `last`; the lines are reported.)
  -- boot 1, `actbench replay on` (the replays run) --
  COV    a COVERED impact: Zidane's seat's Attack START + its impact on Fang 1: held, released at the replay's hit -- covered
         +1, clips +0, swing_skipped +1 (s134's path), `last` unchanged. ITS IN-RUN RED: in_run_red on its own delta.
  DECL   a held impact whose START then DECLINES: Garnet's Potion START + her self impact + its END in ONE feed -- held, the
         START declined `stale`, released `declined`: clips +1, last.via "declined", kind item, hold.rel_declined +1.
  NOOP   a kind-NONE START (Vivi's Defend, no vfx) + its impact: covered +1 (a NOOP: nothing to show), clips +0, none +0.
  -- boot 2 --
  LETHAL a LETHAL caster: Fang 2's EnemyAtk sub k (a real clip) whose own caster lane is lethal (raw HP 0: killed by its own
         move) on Zidane's seat, no START: guarded +1, clips +0. ITS IN-RUN RED: in_run_red on its own delta.
  -- boot 3 --
  BACKLOG an uncovered impact (Zidane's seat's Attack, no START) fed DURING the boot's intro -- batched into the `dioboot`'s
         own request -- drained in the first steady (BACKLOG) Update: backlog +1, clips +0 for the boot, none later (D-c).
         ITS IN-RUN RED: in_run_red on its own delta.
  INV    THE INVARIANTS after the last leave: gil, the bag, levels, exp, AP, kill counters == the pre-boot snapshot.
  R      `reset` with `fallback off` left set: the 'fallback lever back' line; RE-READ WITH THE ROLE: `on` true.
NOT PROVEN HERE: a REPLACED START's held impact (covered by the rule -- ActFallbackSelfTest's covered rows and the stand-in's
lane tests pin it; s135's REP leg shapes it), an abort-all's drop (r8 / w3 / leave / clear: rows), the hidden guard (a
selftest diorama hides no enemy), a monster-transformed caster (none: the stand-in's test), a kind-1 text sequence (mod data),
the defensive clip attach and its refusal of a clip the unit lacks (a cross-folder or unregistered clip: none in scene 306;
ActFallbackClipPlayable's row), the slave / afFreeze / bi.disappear guard (a selftest diorama has none), a fault (the
'faulted' line), the queued sibling's window (a stand-in ordering test), and the fix pass's other rules -- THE DEFERRAL
(cover-2: a guest-lag declined START's impact waiting for its caster's replay), the abort-all and run-away-hold end blocks
(timing-1) and the busy window's kept pose (timing-2) -- and the second fix pass's RECORD DEFERRAL (rcover-2: an impact
covered only by a still-pending START -- a `target` decline above all -- waiting for its decision) and its ORDER-aware kept
pose (rtiming-1: a clip written after its unit's abort kept through the restore), plus a script's scripted sequence (cmd
None: rstock-1's other half) -- pinned by ActFallbackSelfTest's rows and the stand-in's lane tests, not by a solo leg. The
OLD HOST through the REAL transport intake is the ARC leg's (the solo OLD leg feeds the selftest inbox: ActionTickBench).

CALIBRATION -- a check that cannot fail is not a check.
  * THE DEPLOYED DLL AT WRITING (s135) -- and any engine before s136: `act.guest.fallback` is absent, so P0 is RED and no
    fallback op is ever sent; battle 1 still runs. RED, exactly: every check but INI, S0, PRE, TAPE, ORACLE, INV (nothing
    booted, nothing to change). COOP_CALIBRATE=1 there judges exactly that red set as S136-CAL.
  * IN-RUN, on the s136 DLL: IDLE's, DEF's, SELF's, COV's, LETHAL's and BACKLOG's "no clip" predicates are each judged
    False on the leg's OWN delta with one clip injected (in_run_red) -- each check's own red, every run, on the bucket move
    it really saw. [fix pass 2: rharness-02] (A sibling leg's delta, used before, read False through its bucket alone -- its
    bucket never moved -- so the "no clip written" conjunct was never shown failing in game.)
    COOP_CALIBRATE=1 also pulls `actbench fallback off` (the pre-s136 guest) BEFORE boot 1 -- the s110 swing for an uncovered
    player impact (Item and Magic play MP_ATTACK), an enemy nothing, no fallback counter moves. Predicted reds, exactly:
    ITEM, ITEMA, MAGIC, ATTACK, ENEMY, IDLE, DEF, SELF, BURST1, BURSTD, BURSTC, OLD, COV, DECL, NOOP, LETHAL, BACKLOG (each
    reads its counter's move; GREEN: INI, S0, P0, PROOF, PRE, TAPE, ORACLE, BOOT, INV, R. S136-CAL judges that set (the run
    is red by design).
  * THE STAND-IN (tools/harness/fakegame.py, cap `actfallback`) models fallback A through battlewire.ActFallbackLane -- not
    the scene data, not this plan: never read S136-CAL offline. Its tests (ff9mapkit/tests/test_harness_netsync.py) evaluate
    ActFallbackSelfTest's 30 rows off the stack against the twins, pin the verb, the keys and these tables; the engine is
    the calibration.

THE TAPE LEG (COOP_FB_LEG=tape). The tape: coop_action_replay's (COOP_ACT_TAPE, else COOP_ACT_TAPE_DIR's or <main
repo>/.harness-runs/coop-tapes/act-s133's latest.json, else its newest *.f9tape) -- an s133+ host's action lane on its first
battle (>= 1 START), and coop_cut_hold's CAL leg passed on it (its sha256 sidecar); else the leg refuses cleanly ("no s133
tape"). The guest config is coop_action_replay's tape leg's with ActionReplay 0: every START declines `knob`, every impact is
UNCOVERED. The recorded tape (scene 67, BSC_EF_R007, a Goblin): 13 STARTs -- Defends (kind 4: none), two Attacks (attack
clips), the Goblin's sub 0 and sub 2 (enemy clips) -- no Item and no Magic on it (those kinds are the solo bench's). The whole
tape replays (no cut); every publish is sampled until the end-leave's RETURN. Checks (S136T-*):
  I      the instrument: 'paired', 'state-mirror ARMED', 'diorama BOOT scene=M', 'diorama LIVE ... nonce N' logged.
  P0     `netsync.battle.act.guest.fallback` published on the guest during the battle (else every check fails closed).
  UNCOV  the knob held: started 0, every START declined (`knob`) and covered 0 -- nothing replayed, nothing covered.
  CLIP   clips >= 1; over every sample's `last` and the engine's clip lines: an attack clip AND an enemy clip, each keyed by
         id (an s133 host's impacts carry ids), via arrival, a real name (never empty, never "Idle").
  ENEMY  every enemy clip seen (`last` and the clip lines) is THE ORACLE's first non-Idle caster clip of its sub, for the
         tape's scene (read offline as above).
  NONE   none >= 1: the Defends chose nothing.
  ACCT   [fix pass: harness-03] THE BUCKET IDENTITY, bounded by what the run measures: every impact that reaches the motion
         step counts exactly one bucket, so the guest's PAIRED impacts (each names a declined START, each reaches the motion
         step) <= clips + collapsed + none + deduped + covered + guarded + backlog <= the tape's impacts -- a dropped
         bucket reads under `paired`, a double count over the impacts -- and no parse failure. (ONCE PER ACTION is the solo
         BURST1 / OLD legs' proof: this tape holds ONE impact per START, so no tape count can tell a dedupe from none -- a
         multi-impact tape (a multi-target spell) would add deduped >= impacts - STARTs.)
  LOG    >= 1 'action fallback: ... clip' line, the 'action fallback: boot summary (teardown)' line, no 'action fallback
         faulted' line.
  plus coop_cut_hold's COMMON T2-TAPE, T2-CAL, T2-PEER (its config line names ' actionReplay=0' exactly when the knob is
  written 0), T2-SAVE and T2-INI.
  CALIBRATION: on an s135 GUEST `act.guest.fallback` is absent: RED exactly P0, UNCOV, CLIP, ENEMY, NONE, ACCT, LOG (fails
  closed) -- the T2-* and I GREEN. No knob turns fallback A off on a real client (its lever is selftest-only), so on s136
  COOP_CALIBRATE=1 writes the INVERSE knob, ActionReplay=1: the replays COVER their impacts -- RED exactly UNCOV, CLIP, ENEMY,
  LOG (nothing uncovered plays a clip); NONE is a maybe (a Defend whose START and END share a drain declines `stale`: its
  impact stays uncovered and still chooses none). S136T-CAL judges the set the engine FOUND.

THE ARC LEG (COOP_FB_LEG=arc) [fix pass: harness-01]. The tape: COOP_FB_ARC_TAPE, else coop_cut_hold's s117 arc tape
(_coop_peer_bench.ARC_TAPE_NAME in <main repo>/.harness-runs/coop-tapes) -- an OLD host's battle: >= 1 impact and NO START
(the tape leg's >= 1-START gate is skipped; a START on it refuses the leg: not an old host's tape), and coop_cut_hold's
CAL leg passed on it (its sha256 sidecar); else the leg refuses cleanly ("no arc tape"). The guest config is the tape
leg's with ActionReplay 1. The whole tape replays; every publish is sampled until the end-leave's RETURN. Checks
(S136A-*):
  I      the instrument, as S136T-I.
  P0     `netsync.battle.act.guest.fallback` published on the guest during the battle (else every check fails closed).
  OLD    the guest saw an OLD host: `old_host` true, no START received or started, covered 0.
  CLIP   clips >= 1; every `last` record and every clip line keyed by "caster" with id 0 and a real clip name (never empty,
         never "Idle") -- the (caster, cmd, sub) window through the REAL intake.
  ENEMY  >= 1 enemy clip seen, each THE ORACLE's first non-Idle caster clip of its sub for the arc tape's scene.
  ACCT   every bucket's impacts <= the tape's impacts; no parse failure.
  LOG    >= 1 clip line, the boot summary (teardown) line, no 'action fallback faulted' line.
  plus T2-TAPE, T2-CAL, T2-PEER, T2-SAVE and T2-INI.
  CALIBRATION: on an s135 GUEST `act.guest.fallback` is absent: RED exactly P0, OLD, CLIP, ENEMY, ACCT, LOG (fails closed)
  -- the T2-* and I GREEN. On s136 COOP_CALIBRATE=1 has no inverse for an old host (no START for a replay to cover, and
  the fallback lever is selftest-only): it judges the plain run, predicting no red.

RUN:
    py tools/play.py studies/test-harness/scenarios/coop_action_fallback.py --field 30602
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_action_fallback.py --field 30602
    COOP_FB_LEG=tape py tools/play.py studies/test-harness/scenarios/coop_action_fallback.py
    COOP_FB_LEG=arc py tools/play.py studies/test-harness/scenarios/coop_action_fallback.py
  PowerShell has no per-launch form: a `$env:` value PERSISTS in that shell -- clear them after each run:
    Remove-Item Env:COOP_CALIBRATE, Env:COOP_FB_LEG, Env:COOP_ACT_TAPE, Env:COOP_FB_ARC_TAPE -ErrorAction SilentlyContinue
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
import coop_action_hold as hd                              # noqa: E402 - s135's bench: its boots and battle-1 plan

BW = ar.BW
HarnessError = cb.HarnessError

LEG = (os.environ.get("COOP_FB_LEG", "solo").strip().lower() or "solo")
LEGS = ("solo", "tape", "arc")
PROBE = cb.R3_PROBES[136]                  # netsync.battle.act.guest.fallback: absent = s135 or older (fails closed)
HOLD_PROBE = cb.R3_PROBES[135]             # netsync.battle.act.guest.hold
GUEST_PROBE = cb.R3_PROBES[134]            # netsync.battle.act.guest
HOST_PROBE = cb.R3_PROBES[133]             # netsync.battle.act.host: the in-engine tape (battle 1)
SCENE, GROUP = ar.SCENE, ar.GROUP          # 306 / 4 (Fang x2): the s133-s135 benches' scene
NONCE = 0x5E                               # MARKER: this bench's nonce byte (s134's 0x5C, s135's 0x5D)
FIG = {"ITEM": 5161, "ITEMA": 5162, "MAGIC": 5163, "ATTACK": 5164, "ENEMY": 5165, "IDLE": 5166, "DEF": 5167,
       "CHG": 5168, "SELF": 5169, "BURST1": 5170, "BURSTD": 5171, "BURSTC": 5172, "OLD": 5173, "COV": 5174,
       "DECL": 5175, "NOOP": 5176, "LETHAL": 5177, "BACKLOG": 5178}   # MARKER: the impacts' figures (never judged)
INFO_HP = 1                                # Param.FIG_INFO_DISP_HP
CLIP_S = 4.0                               # a write's publish, at most (the drain runs every Update)
OLD_E_GAP = 1000                           # [fix pass 2: rharness-03] OLD's two writes: A and E (D lands <= ~833 ms after A)
REPLAY_S = 20.0                            # a fabricated replay's end, at most
DEFEND_SUB = 179                           # BattleAbilityId of the stock Defend (the tape's, when it names none)
PROOF = "action fallback selftest:"
PROOF_OK = BW.proof_ok(BW.PROOF_FALLBACK, BW.FALLBACK_SELFTEST_ROWS).rstrip()
LEG_FAULTS = ar.LEG_FAULTS
_IDS = itertools.count(1)                  # bench ids: unique per process, so unique per boot (no `duplicate`)
_SEQS = itertools.count(3000)              # impact seqs: ascending


# ================================================================================================ the catalogs
def _solo_catalog(calibrate: bool) -> dict:
    c = {
        "S136-INI": "precondition: Memoria.ini [Netsync] Enabled reads 0 (or absent), READ-ONLY -- else NOTHING runs",
        "S136-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
        "S136-P0": f"the engine publishes `{PROBE}` (memoria-patch s136) whole -- exactly the agent's keys, `on` true -- "
                   "else no fallback op is ever sent (fails closed)",
        "S136-PROOF": f"the selftest proof block's line reads exactly '{PROOF_OK}' -- no FAIL line",
        "S136-PRE": f"precondition: battle 1 (`battle {SCENE} {GROUP}`) seats Zidane, Vivi and Garnet and 2+ enemies",
        "S136-TAPE": "battle 1's s133 tape carries Zidane's Attack START, Garnet's Potion START and an enemy START (kind 2, "
                     "num == sub)",
        "S136-ORACLE": f"scene {SCENE}'s sequences read OFFLINE: the taped enemy sub's first non-Idle caster clip, and an "
                       "Idle-only sub",
        "S136-BOOT": "boot 1 steady with act.guest.fallback at rest: every counter 0, `last` null, `on` true (false under "
                     "COOP_CALIBRATE's lever)",
        "S136-ITEM": "Garnet's Potion on HERSELF (no DmgMot), uncovered: clips +1, last item / id / arrival, her mot MP_ITEM1",
        "S136-ITEMA": "Garnet's Potion on Vivi, uncovered: clips +1, last item, her mot MP_ITEM1",
        "S136-MAGIC": "Vivi's Fire, uncovered: clips +1, last magic, her mot MP_MAGIC",
        "S136-ATTACK": "Zidane's seat's Attack, uncovered: clips +1, last attack, its mot MP_ATTACK",
        "S136-ENEMY": "Fang 1's EnemyAtk sub k, then its LOOP move (ScriptCounter1) sub k, uncovered: clips +2, each clip == "
                      "the oracle's first non-Idle caster clip of k, Fang 1's anim that clip",
        "S136-IDLE": "an Idle-only enemy sequence: none +1, clips +0, parse_failed +0 -- the same predicate reads False on "
                     "its own delta with one clip injected (its in-run red)",
        "S136-DEF": "Defend and Change (each on itself): none +2, clips +0",
        "S136-SELF": "a self-hit WITH a DmgMot: guarded +1, clips +0",
        "S136-BURST1": "one action id, three impacts within 100 ms: clips +1, deduped +2, keyed by id",
        "S136-BURSTD": "three distinct ids on one actor over three drains: clips +3, collapsed +0",
        "S136-BURSTC": "three distinct ids on one actor in ONE drain: clips +1, collapsed +2",
        "S136-OLD": "an old host's (no id / id 0) impacts: A; B, C on ONE feedat verb; D past the window from A but inside "
                    "it from B / C (only THE SLIDE dedupes it); E past it -- clips +2, deduped +3, keyed by caster, the two "
                    "writes >= 1000 battle ms apart (A and E)",
        "S136-COV": "a COVERED impact (its replay runs): covered +1, clips +0, swing_skipped +1 -- the predicate reads False "
                    "on its own delta with one clip injected",
        "S136-DECL": "a held impact whose START declines `stale`: released `declined` -- clips +1, last.via 'declined'",
        "S136-NOOP": "a kind-NONE START's impact: covered +1, clips +0, none +0",
        "S136-LETHAL": "a caster killed by its own blow: guarded +1, clips +0 -- the predicate reads False on its own delta "
                       "with one clip injected",
        "S136-BACKLOG": "an uncovered impact drained in the boot's backlog Update: backlog +1, clips +0 -- the predicate "
                        "reads False on its own delta with one clip injected",
        "S136-INV": "the invariants after the last leave: gil, bag, levels, exp, AP, kill counters == the pre-boot snapshot",
        "S136-R": "`reset` with the fallback lever set: the 'fallback lever back' line; RE-READ WITH THE ROLE `on` true",
    }
    if calibrate:
        c["S136-CAL"] = ("CALIBRATION: exactly the predicted checks are red -- on an engine without `act.guest.fallback` "
                         "every check but INI/S0/PRE/TAPE/ORACLE/INV; on the s136 DLL under `fallback off` the LEVER set")
    return c


#: the checks that need `act.guest.fallback` (not reached together when the probe fails closed)
FALLBACK_CHECKS = ("S136-PROOF", "S136-BOOT", "S136-ITEM", "S136-ITEMA", "S136-MAGIC", "S136-ATTACK", "S136-ENEMY",
                   "S136-IDLE", "S136-DEF", "S136-SELF", "S136-OLD", "S136-BURST1", "S136-BURSTD", "S136-BURSTC",
                   "S136-COV", "S136-DECL", "S136-NOOP", "S136-LETHAL", "S136-BACKLOG", "S136-R")
#: COOP_CALIBRATE=1 on an engine without `act.guest.fallback` (the deployed s135, or older): all but INI, S0, PRE, TAPE,
#: ORACLE, INV
OLD_PREDICTED = tuple(c for c in _solo_catalog(True) if c not in ("S136-INI", "S136-S0", "S136-PRE", "S136-TAPE",
                                                                    "S136-ORACLE", "S136-INV", "S136-CAL"))
#: COOP_CALIBRATE=1 on the s136 DLL: `fallback off` before boot 1 -- no fallback counter ever moves
LEVER_PREDICTED = ("S136-ITEM", "S136-ITEMA", "S136-MAGIC", "S136-ATTACK", "S136-ENEMY", "S136-IDLE", "S136-DEF",
                   "S136-SELF", "S136-OLD", "S136-BURST1", "S136-BURSTD", "S136-BURSTC", "S136-COV", "S136-DECL",
                   "S136-NOOP", "S136-LETHAL", "S136-BACKLOG")
LEVER_MAYBE: tuple = ()
#: boot 1's legs, in their order (nothing kills; the replay-on legs last)
BOOT_1_LEGS = ("S136-BOOT", "S136-ITEM", "S136-ITEMA", "S136-MAGIC", "S136-ATTACK", "S136-ENEMY", "S136-IDLE", "S136-DEF",
               "S136-SELF", "S136-OLD", "S136-BURST1", "S136-BURSTD", "S136-BURSTC", "S136-COV", "S136-DECL",
               "S136-NOOP")

TAPE_CHECKS = {
    "S136T-I": "the instrument: 'paired', 'state-mirror ARMED', 'diorama BOOT scene=M', 'diorama LIVE ... nonce N' logged",
    "S136T-P0": f"`{PROBE}` published on the guest during the battle (else every fallback check fails closed)",
    "S136T-UNCOV": "the knob held: started 0, every START declined `knob`, covered 0",
    "S136T-CLIP": "clips >= 1; an attack AND an enemy clip seen, keyed by id, via arrival, real names",
    "S136T-ENEMY": "every enemy clip seen is the oracle's first non-Idle caster clip of its sub (the tape's scene)",
    "S136T-NONE": "none >= 1 (the Defends chose nothing)",
    "S136T-ACCT": "the bucket identity: paired <= every bucket's sum <= the tape's impacts; no parse failure",
    "S136T-LOG": "a clip line, the 'boot summary (teardown)' line, no 'action fallback faulted' line",
}
TAPE_FALLBACK = ("S136T-P0", "S136T-UNCOV", "S136T-CLIP", "S136T-ENEMY", "S136T-NONE", "S136T-ACCT", "S136T-LOG")
#: the tape leg on an s135 GUEST (no `act.guest.fallback`): every fallback check fails closed
TAPE_OLD_PREDICTED = TAPE_FALLBACK
#: the tape leg on s136 under COOP_CALIBRATE=1 (the INVERSE knob, ActionReplay=1 written): the replays cover the impacts
TAPE_REPLAY_PREDICTED = ("S136T-UNCOV", "S136T-CLIP", "S136T-ENEMY", "S136T-LOG")
TAPE_REPLAY_MAYBE = ("S136T-NONE",)


def _tape_catalog(calibrate: bool) -> dict:
    cat = {"T2-TAPE": ar.TAPE_COMMON["T2-TAPE"], "T2-CAL": ar.TAPE_COMMON["T2-CAL"], "T2-PEER": ar.TAPE_COMMON["T2-PEER"]}
    cat.update(TAPE_CHECKS)
    if calibrate:
        cat["S136T-CAL"] = ("CALIBRATION: exactly the predicted checks are red for the engine found -- s135: every fallback "
                            "check; s136 under ActionReplay=1: UNCOV, CLIP, ENEMY, LOG (NONE a maybe)")
    cat["T2-SAVE"] = ar.TAPE_COMMON["T2-SAVE"]
    cat["T2-INI"] = ar.TAPE_COMMON["T2-INI"]
    return cat


#: [fix pass: harness-01] THE ARC LEG -- an old host's tape (no START) through the REAL intake
ARC_TAPE_NAME = pb.ARC_TAPE_NAME
ARC_CHECKS = {
    "S136A-I": "the instrument: 'paired', 'state-mirror ARMED', 'diorama BOOT scene=M', 'diorama LIVE ... nonce N' logged",
    "S136A-P0": f"`{PROBE}` published on the guest during the battle (else every fallback check fails closed)",
    "S136A-OLD": "the guest saw an OLD host: old_host true, no START received or started, covered 0",
    "S136A-CLIP": "clips >= 1; every `last` record and clip line keyed by caster, id 0, a real clip name",
    "S136A-ENEMY": ">= 1 enemy clip seen, each the oracle's first non-Idle caster clip of its sub (the arc tape's scene)",
    "S136A-ACCT": "every bucket's sum <= the tape's impacts; no parse failure",
    "S136A-LOG": "a clip line, the 'boot summary (teardown)' line, no 'action fallback faulted' line",
}
ARC_FALLBACK = ("S136A-P0", "S136A-OLD", "S136A-CLIP", "S136A-ENEMY", "S136A-ACCT", "S136A-LOG")
#: the arc leg on an s135 GUEST: every fallback check fails closed; on s136 COOP_CALIBRATE has no inverse (no red)
ARC_OLD_PREDICTED = ARC_FALLBACK


def _arc_catalog(calibrate: bool) -> dict:
    cat = {"T2-TAPE": ar.TAPE_COMMON["T2-TAPE"], "T2-CAL": ar.TAPE_COMMON["T2-CAL"], "T2-PEER": ar.TAPE_COMMON["T2-PEER"]}
    cat.update(ARC_CHECKS)
    if calibrate:
        cat["S136A-CAL"] = ("CALIBRATION: exactly the predicted checks are red for the engine found -- s135: every fallback "
                            "check; s136: none (an old host has no inverse knob)")
    cat["T2-SAVE"] = ar.TAPE_COMMON["T2-SAVE"]
    cat["T2-INI"] = ar.TAPE_COMMON["T2-INI"]
    return cat


def _catalog(calibrate: bool, leg: str = "solo") -> dict:
    if leg == "arc":
        return _arc_catalog(calibrate)
    return _tape_catalog(calibrate) if leg == "tape" else _solo_catalog(calibrate)


def _tape_predicted(has_fallback: bool) -> tuple:
    """The tape leg's predicted reds for the engine FOUND (its `act.guest.fallback` key) under COOP_CALIBRATE=1, and the
    maybes: (predicted, maybe)."""
    return (TAPE_REPLAY_PREDICTED, TAPE_REPLAY_MAYBE) if has_fallback else (TAPE_OLD_PREDICTED, ())


def _arc_predicted(has_fallback: bool) -> tuple:
    """The arc leg's predicted reds for the engine FOUND under COOP_CALIBRATE=1: s135 every fallback check (fails
    closed); s136 none -- the plain run is judged (no knob inverts an old host's path). (predicted, maybe)."""
    return ((), ()) if has_fallback else (ARC_OLD_PREDICTED, ())


# ================================================================================================ THE ORACLE (offline)
def _kit():
    """The kit (ff9mapkit) -- THIS checkout's when nothing imported one yet (its package root put first)."""
    root = str(cb.REPO / "ff9mapkit")
    if "ff9mapkit" not in sys.modules and root not in sys.path:
        sys.path.insert(0, root)
    import ff9mapkit                                       # noqa: F401 - the package itself
    from ff9mapkit.battle import seqcodec
    from ff9mapkit import _animdb_all
    return sys.modules["ff9mapkit"], seqcodec, _animdb_all


def kit_file() -> str:
    """The kit module the oracle reads with (its __file__): the run's notes name it (a main-repo editable install could
    shadow this checkout's -- the files the oracle uses are the same either way)."""
    return str(getattr(_kit()[0], "__file__", ""))


def btlseq_clips(raw17: bytes, names: dict) -> dict:
    """THE ORACLE, PURE: a scene's btlseq raw17 -> {sub: its first non-Idle caster clip, or None} for every sub with a
    sequence, read as BattleActionThread.LoadFromBtlSeq parses it (each case-5 op's anim id = animList[seqBaseAnim[sub] +
    code], the code 255 the literal "Idle", then END's appended Idle) and picked by battlewire's first-clip twin. ``names``
    = AnimationDB (id -> name). {} for a raw17 the kit cannot parse."""
    try:
        sc = _kit()[1]
        model = sc.parse(bytes(raw17))
    except Exception:                                      # noqa: BLE001 -- an unreadable raw17 is the caller's "none"
        return {}
    out = {}
    for sub in range(model.seq_count):
        body = model.body_for(sub)
        if body is None:
            continue
        base = model.seq_base_anim[sub] if sub < len(model.seq_base_anim) else 0
        anims = []
        for ins in body.instrs:
            if ins.op != 0x05:
                continue
            code = int(ins.operands[0])
            if code == 255:
                anims.append(None)
                continue
            at = base + code
            anim_id = model.anim_list[at] if 0 <= at < len(model.anim_list) else None
            anims.append(names.get(anim_id, f"?{anim_id}"))
        out[sub] = BW.act_fallback_first_clip(BW.act_seq_threads(anims))
    return out


def idle_only_subs(clips: dict) -> list:
    """The subs whose sequence plays only Idle (none)."""
    return sorted(s for s, c in clips.items() if c is None)


def scene_name(scene: int) -> str | None:
    """A battle scene id -> its name after `BSC_` / `EVT_BATTLE_` (the kit's scene table), or None."""
    try:
        from ff9mapkit import _scenedb
    except ImportError:
        _kit()
        from ff9mapkit import _scenedb
    return next((k[4:] for k, v in _scenedb.SCENES.items() if v == int(scene) and k.startswith("BSC_")), None)


def oracle_overrides(game_path, name: str) -> list:
    """[fix pass: harness-05] Every loose file a Memoria.ini [Mod] FolderNames folder carries that the ENGINE would read
    for EVT_BATTLE_<name>'s sequences instead of the base p0data2 (READ-ONLY): the scene's raw17 (any name under a
    battlescene/evt_battle_<name> directory) or a folder's own p0data2.bin. [] = the base install's is the one."""
    try:
        from ff9mapkit.deploystack import parse_folder_names
        folders = parse_folder_names((Path(game_path) / "Memoria.ini").read_text(encoding="utf-8", errors="replace"))
    except Exception:                                      # noqa: BLE001 -- no ini / no kit: nothing stacked is known
        return []
    needle = f"battlescene/evt_battle_{name.lower()}/"
    out = []
    for folder in folders:
        sa = Path(game_path) / str(folder) / "StreamingAssets"
        if not sa.is_dir():
            continue
        if (sa / "p0data2.bin").is_file():
            out.append(str(sa / "p0data2.bin"))
        try:
            out += [str(f) for f in sa.rglob("*.raw17*") if needle in f.as_posix().lower()]
        except OSError:
            continue
    return out


def scene_oracle(scene: int, game_path) -> tuple:
    """(clips | None, why): the scene's sequences off the install's p0data2 (READ-ONLY, UnityPy), through
    :func:`btlseq_clips` -- [fix pass: harness-05] None (fails closed, the path named) when a stacked mod folder overrides
    them (:func:`oracle_overrides`: the engine would parse the override); the detail names the source read."""
    try:
        _mod, _sc, animdb = _kit()
        import UnityPy
        from ff9mapkit.extract import _raw_bytes
    except Exception as err:                               # noqa: BLE001 -- the reason is the check's detail
        return None, f"the oracle cannot load the kit / UnityPy ({type(err).__name__}: {err})"
    name = scene_name(scene)
    if name is None:
        return None, f"scene {scene} is not in the kit's scene table"
    over = oracle_overrides(game_path, name)
    if over:
        return None, (f"EVT_BATTLE_{name}'s sequences are OVERRIDDEN by a stacked mod folder ({over[:3]}): the engine parses "
                      "the override, the oracle reads only the base p0data2 -- fails closed")
    p0 = Path(game_path) / "StreamingAssets" / "p0data2.bin"
    needle = f"battlescene/evt_battle_{name.lower()}/"
    try:
        env = UnityPy.load(str(p0))
        raw = None
        for o in env.objects:
            if o.type.name != "TextAsset":
                continue
            c = (getattr(o, "container", None) or "").lower()
            if needle in c and c.endswith(".raw17.bytes"):
                raw = _raw_bytes(o.read())
                break
    except Exception as err:                               # noqa: BLE001
        return None, f"{p0} did not read ({type(err).__name__}: {err})"
    if raw is None:
        return None, f"no raw17 for EVT_BATTLE_{name} in {p0.name}"
    clips = btlseq_clips(raw, animdb.ANIMATIONS)
    if not clips:
        return None, f"EVT_BATTLE_{name}'s raw17 did not parse"
    return clips, (f"EVT_BATTLE_{name} read from {p0} (no stacked override): {len(clips)} sequence(s), Idle-only "
                   f"{idle_only_subs(clips)} (kit {kit_file()})")


# ================================================================================================ reads
_num = ar._num
_sub = ar._sub
_guest = ar._guest
_gv = ar._gv
_n = hd._n


def _fb(x) -> dict:
    return _sub(_guest(x), "fallback")


def _fv(x, key: str) -> int:
    return _num(_fb(x).get(key)) or 0


def _flast(x) -> dict:
    v = _fb(x).get("last")
    return v if isinstance(v, dict) else {}


def _fbrief(x) -> str:
    return "act.guest.fallback=" + str(cb.pick(_fb(x), "on", *BW.ACT_FALLBACK_BUCKETS, "parse_failed", "last"))


def _fbase(x) -> dict:
    out = {k: _fv(x, k) for k in (*BW.ACT_FALLBACK_BUCKETS, "parse_failed")}
    out["last_id"] = _num(_flast(x).get("id"))
    out["swing_skipped"], out["declined"], out["stale"] = _gv(x, "swing_skipped"), _gv(x, "declined"), _gv(x, "stale")
    out["noop"], out["rel_declined"] = _gv(x, "noop"), _num(_sub(_guest(x), "hold").get("rel_declined")) or 0
    return out


def _delta(x, base: dict) -> dict:
    """Each bucket's move since ``base``."""
    return {k: _fv(x, k) - base.get(k, 0) for k in (*BW.ACT_FALLBACK_BUCKETS, "parse_failed")}


# ================================================================================================ the pure judges
def no_clip_pred(delta: dict, bucket: str, n: int = 1) -> bool:
    """A "no clip" check's predicate (PURE): ``bucket`` moved by ``n`` and NO clip was written (clips and collapsed +0).
    Its in-run red: :func:`in_run_red` on the leg's own delta must read False."""
    return delta.get(bucket) == n and delta.get("clips") == 0 and delta.get("collapsed") == 0


def in_run_red(delta: dict, bucket: str, n: int = 1) -> bool:
    """A "no clip" check's IN-RUN RED (PURE) -- [fix pass 2: rharness-02] :func:`no_clip_pred` on the leg's OWN delta with
    ONE CLIP INJECTED: it must read False, so the "no clip written" conjunct is shown failing on the bucket move the leg
    really saw (a sibling leg's delta, whose bucket never moved, read False through the bucket conjunct alone)."""
    d = dict(delta or {})
    d["clips"] = int(d.get("clips") or 0) + 1
    return no_clip_pred(d, bucket, n)


def judge_clip(last: dict, *, want_id: int | None, kind: str, cmd: int, sub: int, actor: int | None, keyed_by: str,
               via: str = BW.ACT_VIA_ARRIVAL, clip: str | None = None) -> tuple:
    """`act.guest.fallback.last` names THIS write (PURE): its kind, cmd, sub, caster, key, via (and its clip when the oracle
    names one); ``want_id`` None = keyed by caster (id 0). (ok, detail)."""
    want = {"kind": kind, "cmd": cmd, "sub": sub, "keyed_by": keyed_by, "via": via,
            "id": 0 if want_id is None else want_id}
    if actor is not None:
        want["actor"] = actor
    if clip is not None:
        want["clip"] = clip
    bad = {k: (last.get(k), v) for k, v in want.items() if last.get(k) != v}
    name = last.get("clip")
    if not name or name == "Idle":
        bad["clip"] = (name, "a real clip name")
    return not bad, (f"last {cb.pick(last, *BW.ACT_FALLBACK_LAST_KEYS)}" + (f"; WRONG {bad}" if bad else ""))


def judge_window(records: list, slot: int, cmd: int, sub: int, min_gap: int = BW.ACT_FALLBACK_WINDOW_MS) -> tuple:
    """OLD's timing, on the ENGINE's own clock (PURE): ``records`` -- the distinct `act.guest.fallback.last` records seen
    (:func:`lasts_union`) or the engine's clip lines parsed (battlewire.parse_fallback_clip; both carry actor / slot, cmd,
    sub, keyed_by, id, ms) -- name exactly TWO writes for the old host's (caster, cmd, sub), both keyed by caster with id 0,
    at battle ms >= ``min_gap`` apart (the window by default; OLD passes OLD_E_GAP: its second write is E, never D --
    [fix pass 2: rharness-03] an ANCHORED window would write A, D and E: three). (ok, detail)."""
    got = [r for r in records or [] if (r.get("actor") if "actor" in r else r.get("slot")) == slot and r.get("cmd") == cmd
           and r.get("sub") == sub]
    if len(got) != 2:
        return False, f"{len(got)} write(s) for wire slot {slot} cmd {cmd} sub {sub} (want TWO): {got[:3]}"
    gap = int(got[1].get("ms") or 0) - int(got[0].get("ms") or 0)
    ok = all(r.get("keyed_by") == "caster" and r.get("id") == 0 for r in got) and gap >= int(min_gap)
    return ok, (f"two writes at battle ms {got[0].get('ms')} and {got[1].get('ms')} (gap {gap}, want >= {int(min_gap)}); "
                f"keyed {[r.get('keyed_by') for r in got]}, ids {[r.get('id') for r in got]}")


def lasts_union(blocks) -> list:
    """Every distinct `last` record over the samples' `act.guest.fallback` blocks, oldest first (PURE)."""
    out, seen = [], set()
    for b in blocks:
        last = b.get("last") if isinstance(b, dict) else None
        if not isinstance(last, dict):
            continue
        key = tuple(last.get(k) for k in BW.ACT_FALLBACK_LAST_KEYS)
        if key in seen:
            continue
        seen.add(key)
        out.append(last)
    return out


def judge_fallback_tape(led, samples: list, messages: list, act: dict, oracle: dict | None, why_oracle: str = "") -> None:
    """THE TAPE LEG'S JUDGE (PURE: the samples -- each {booted, guest} -- the engine's messages since the start, the tape's
    act facts {starts, impacts}, and the oracle {sub: clip}; test_harness_netsync.py runs it on synthetic runs): P0,
    UNCOV, CLIP, ENEMY, NONE, ONCE, LOG."""
    guests = [s["guest"] for s in samples if isinstance(s.get("guest"), dict)]
    blocks = [g.get("fallback") for g in guests if isinstance(g.get("fallback"), dict)]
    if not blocks:
        led.unreached(TAPE_FALLBACK, "`netsync.battle.act.guest.fallback` was never published (an engine before s136: "
                                     "fails closed)")
        return
    led.check("S136T-P0", True, f"{len(blocks)} sample(s) with act.guest.fallback")
    last, g = blocks[-1], guests[-1]
    n = {k: _num(last.get(k)) or 0 for k in (*BW.ACT_FALLBACK_BUCKETS, "parse_failed")}
    gv = {k: _num(g.get(k)) or 0 for k in ("starts_rx", "started", "declined")}
    led.check("S136T-UNCOV", gv["started"] == 0 and gv["declined"] == gv["starts_rx"] >= 1 and g.get("declined_why") == "knob"
              and n["covered"] == 0,
              f"starts_rx {gv['starts_rx']}, started {gv['started']}, declined {gv['declined']} (last "
              f"{g.get('declined_why')!r}); covered {n['covered']}")
    lines = [p for p in (BW.parse_fallback_clip(m) for m in messages or []) if p is not None]
    lasts = lasts_union(blocks)
    seen = [dict(x, source="last") for x in lasts] + [dict(p, source="line") for p in lines]
    kinds = sorted({str(x.get("kind")) for x in seen})
    bad = [x for x in seen if x.get("keyed_by") != "id" or x.get("via") != BW.ACT_VIA_ARRIVAL or not x.get("clip")
           or x.get("clip") == "Idle"]
    led.check("S136T-CLIP", n["clips"] >= 1 and {"attack", "enemy"} <= set(kinds) and not bad,
              f"clips {n['clips']} (collapsed {n['collapsed']}); kinds seen {kinds} over {len(lasts)} `last` record(s) and "
              f"{len(lines)} clip line(s); off-shape {bad[:2]}")
    enemy = [x for x in seen if x.get("kind") == "enemy"]
    if oracle is None:
        led.check("S136T-ENEMY", False, f"not reached: no oracle ({why_oracle})")
    else:
        wrong = [(x.get("sub"), x.get("clip"), oracle.get(x.get("sub"))) for x in enemy
                 if oracle.get(x.get("sub")) != x.get("clip")]
        led.check("S136T-ENEMY", bool(enemy) and not wrong,
                  f"{len(enemy)} enemy clip(s) seen, subs {sorted({x.get('sub') for x in enemy})}; off the oracle "
                  f"(sub, seen, oracle) {wrong[:3]}")
    led.check("S136T-NONE", n["none"] >= 1, f"none {n['none']}")
    impacts, paired = int(act.get("impacts") or 0), _num(g.get("paired")) or 0
    total = sum(n[k] for k in BW.ACT_FALLBACK_BUCKETS)
    # [fix pass: harness-03] THE BUCKET IDENTITY the run can measure: each paired impact (it names a declined START) reaches
    # the motion step and counts ONE bucket, as does any other impact there -- never more than the tape holds
    led.check("S136T-ACCT", 1 <= paired <= total <= impacts and n["parse_failed"] == 0,
              f"paired {paired} <= every bucket {total} <= the tape's {impacts} impact(s) "
              f"({ {k: n[k] for k in BW.ACT_FALLBACK_BUCKETS} }); parse_failed {n['parse_failed']} (once per action: the "
              f"solo BURST1 / OLD legs' proof -- one impact per START here)")
    clip_lines = [m for m in messages if BW.parse_fallback_clip(m) is not None]
    summary = [m for m in messages if BW.LOG_FALLBACK_SUMMARY + "teardown)" in m]
    faulted = [m for m in messages if BW.LOG_FALLBACK_FAULTED.split(" (", 1)[0] in m]
    led.check("S136T-LOG", bool(clip_lines) and bool(summary) and not faulted,
              f"{len(clip_lines)} clip line(s), summary {[m[-160:] for m in summary[:1]]}, faulted "
              f"{[m[:120] for m in faulted[:2]]}")


def judge_fallback_arc(led, samples: list, messages: list, act: dict, oracle: dict | None, why_oracle: str = "") -> None:
    """[fix pass: harness-01] THE ARC LEG'S JUDGE (PURE, as :func:`judge_fallback_tape`): an OLD host's tape through the
    REAL intake -- P0, OLD, CLIP (every write keyed by caster, id 0), ENEMY (the oracle's), ACCT, LOG."""
    guests = [s["guest"] for s in samples if isinstance(s.get("guest"), dict)]
    blocks = [g.get("fallback") for g in guests if isinstance(g.get("fallback"), dict)]
    if not blocks:
        led.unreached(ARC_FALLBACK, "`netsync.battle.act.guest.fallback` was never published (an engine before s136: "
                                    "fails closed)")
        return
    led.check("S136A-P0", True, f"{len(blocks)} sample(s) with act.guest.fallback")
    last, g = blocks[-1], guests[-1]
    n = {k: _num(last.get(k)) or 0 for k in (*BW.ACT_FALLBACK_BUCKETS, "parse_failed")}
    gv = {k: _num(g.get(k)) or 0 for k in ("starts_rx", "started")}
    old = any(x.get("old_host") is True for x in guests)
    led.check("S136A-OLD", old and gv["starts_rx"] == 0 and gv["started"] == 0 and n["covered"] == 0,
              f"old_host seen {old}; starts_rx {gv['starts_rx']}, started {gv['started']}; covered {n['covered']}")
    lines = [p for p in (BW.parse_fallback_clip(m) for m in messages or []) if p is not None]
    lasts = lasts_union(blocks)
    seen = [dict(x, source="last") for x in lasts] + [dict(p, source="line") for p in lines]
    bad = [x for x in seen if x.get("keyed_by") != "caster" or x.get("id") != 0 or not x.get("clip")
           or x.get("clip") == "Idle"]
    led.check("S136A-CLIP", n["clips"] >= 1 and bool(seen) and not bad,
              f"clips {n['clips']} (collapsed {n['collapsed']}, deduped {n['deduped']}); kinds seen "
              f"{sorted({str(x.get('kind')) for x in seen})} over {len(lasts)} `last` record(s) and {len(lines)} clip "
              f"line(s); off-shape (not keyed by caster with id 0, or no real clip) {bad[:2]}")
    enemy = [x for x in seen if x.get("kind") == "enemy"]
    if oracle is None:
        led.check("S136A-ENEMY", False, f"not reached: no oracle ({why_oracle})")
    else:
        wrong = [(x.get("sub"), x.get("clip"), oracle.get(x.get("sub"))) for x in enemy
                 if oracle.get(x.get("sub")) != x.get("clip")]
        led.check("S136A-ENEMY", bool(enemy) and not wrong,
                  f"{len(enemy)} enemy clip(s) seen, subs {sorted({x.get('sub') for x in enemy})}; off the oracle "
                  f"(sub, seen, oracle) {wrong[:3]}")
    impacts = int(act.get("impacts") or 0)
    total = sum(n[k] for k in BW.ACT_FALLBACK_BUCKETS)
    led.check("S136A-ACCT", 1 <= total <= impacts and n["parse_failed"] == 0,
              f"every bucket {total} <= the tape's {impacts} impact(s) ({ {k: n[k] for k in BW.ACT_FALLBACK_BUCKETS} }); "
              f"parse_failed {n['parse_failed']}")
    clip_lines = [m for m in messages if BW.parse_fallback_clip(m) is not None]
    summary = [m for m in messages if BW.LOG_FALLBACK_SUMMARY + "teardown)" in m]
    faulted = [m for m in messages if BW.LOG_FALLBACK_FAULTED.split(" (", 1)[0] in m]
    led.check("S136A-LOG", bool(clip_lines) and bool(summary) and not faulted,
              f"{len(clip_lines)} clip line(s), summary {[m[-160:] for m in summary[:1]]}, faulted "
              f"{[m[:120] for m in faulted[:2]]}")


def arc_tape_facts(act: dict) -> tuple:
    """[fix pass: harness-01] The arc leg's tape gate (PURE, over :func:`coop_action_replay.tape_act_facts`): an OLD host's
    battle -- >= 1 impact, NO START. (ok, why)."""
    starts, impacts = int(act.get("starts") or 0), int(act.get("impacts") or 0)
    if starts:
        return False, f"not an old host's tape: {starts} START(s) on it (the arc leg replays an s117 host's battle)"
    if impacts < 1:
        return False, "no arc tape: no impact on its battle"
    return True, f"an old host's battle: {impacts} impact(s) ({int(act.get('ext') or 0)} with an id), no START"


def arc_tape() -> Path:
    """COOP_FB_ARC_TAPE, else coop_cut_hold's s117 arc tape in <main repo>/.harness-runs/coop-tapes."""
    env = os.environ.get("COOP_FB_ARC_TAPE", "").strip()
    return Path(env).expanduser().resolve() if env else pb.main_repo() / ".harness-runs" / "coop-tapes" / ARC_TAPE_NAME


# ================================================================================================ frames
def _start(actor: int, *, player: bool, cmd: int, sub: int, tar: int, kind: int = BW.VFX_KIND_SPECIAL, num: int = 0,
           speed: int = 5, cursor: int = 0) -> tuple:
    """A fresh bench START (s133's 76-byte record, this bench's nonce) -> (id, bytes)."""
    act_id = next(_IDS)
    flags = (BW.ACTOR_IS_PLAYER if player else 0) | BW.ACTOR_HOST_REWORK | (BW.ACTOR_HOST_FAST if speed >= 3 else 0)
    return act_id, BW.encode_action_start(NONCE, 1, act_id, actor, flags, cmd, sub, tar, cursor, 0, 0, kind, num, -1, speed)


def _end(act_id: int, cmd: int, sub: int) -> bytes:
    return BW.encode_action_end(NONCE, 2, act_id, cmd, sub)


def _impact(caster: int, target: int, *, act_id: int | None, fig: int, tgt_raw: tuple, cast_raw: tuple,
            player_caster: bool, player_target: bool, cmd: int, sub: int, dmg: bool) -> bytes:
    """A bench impact naming ``act_id`` (None = an OLD HOST's 46-byte frame; 0 = the extension with id 0), an HP figure
    (a MARKER, never judged), the host's raws, DmgMot when ``dmg``."""
    flags = (1 if dmg else 0) | (32 if player_target else 0) | (64 if player_caster else 0)
    return BW.encode_action_impact(NONCE, next(_SEQS), caster, target, fig_t=(INFO_HP, fig, 0),
                                   raws=(tgt_raw[0], tgt_raw[1], cast_raw[0], cast_raw[1]), flags=flags, cmd_no=cmd,
                                   sub_no=sub, act_id=act_id)


def _raws(u: dict | None, hp: int | None = None, dent: int = 0) -> tuple:
    """(raw hp, mp) of a published unit -- ``hp`` replaces it (0 = lethal), ``dent`` takes that much off (never to 0)."""
    u = u or {}
    have = int(u.get("hp_raw") or 0)
    return (int(hp) if hp is not None else max(1, have - int(dent)), int(u.get("mp") or 0))


def _act_verb(g, *args) -> tuple:
    return ar._act_verb(g, *args)


def _feed(g, frames, at_ms: int | None = None) -> tuple:
    return ar._feed(g, frames, at_ms)


def _feed_arg(frames) -> str:
    return BW.act_feed_arg([frames] if isinstance(frames, (bytes, bytearray)) else list(frames))


# ================================================================================================ the run
def run(g, field: int = cb.FIELD):
    if LEG not in LEGS:
        led = cb.Ledger(g, {"S136-LEG": f"COOP_FB_LEG is one of {LEGS}"})
        led.check("S136-LEG", False, f"COOP_FB_LEG={LEG!r} is no leg: one of {LEGS}")
        return
    if LEG in ("tape", "arc"):
        _run_tape(g, arc=LEG == "arc")
        return
    calibrate = cb.CALIBRATE
    led = cb.Ledger(g, _solo_catalog(calibrate), finals=("S136-R", "S136-INV", "S136-CAL"))
    ctx = ar._ctx_new()
    try:
        _run(g, led, field, calibrate, ctx)
    except HarnessError as err:
        g.note(f"the run raised: {str(err)[:400]}")
        led.close(f"not reached: the run raised ({str(err)[:200]})")
    finally:
        g.note(f"logs archived: {ar._archive_logs(g, 'action-fallback')}")
        led.close()
        if ctx["ini_ok"]:
            _release(g, led, ctx)
        else:
            led.unreached(("S136-R", "S136-INV"), "the precondition refused the run (S136-INI): nothing was set")
        if calibrate:
            led.judge_calibration("S136-CAL", LEVER_PREDICTED if ctx["probe"] else OLD_PREDICTED,
                                  LEVER_MAYBE if ctx["probe"] else ())
        led.close(final=True)


def _run(g, led: cb.Ledger, field: int, calibrate: bool, ctx: dict) -> None:
    ok, why = ar._ini_guard(g)
    led.check("S136-INI", ok, why)
    if not ok:
        led.close(f"refused to run: {why}")
        return
    ctx["ini_ok"] = True
    ctx["field"] = field
    ok, why = cb.setup(g, field, label=f"R3 s136: fallback A, solo (scene {SCENE} group {GROUP})"
                                       + (" -- CALIBRATION (actbench fallback off)" if calibrate else ""))
    led.check("S136-S0", ok, why)
    if not ok:
        led.close(f"the selftest role was refused -- {why}")
        return
    st = g.state
    have = ctx["probe"] = cb.has(st, PROBE)
    # [fix pass: harness-07] the block WHOLE (exactly the agent's keys: `_fv` reads a missing one as 0) and `on` true (a
    # lever stranded off would red every leg, each blaming itself)
    diff = sorted(set(_fb(st)) ^ set(BW.ACT_GUEST_FALLBACK_SENTINELS))
    keys_ok = not diff
    led.check("S136-P0", have and keys_ok and _fb(st).get("on") is True,
              f"act.guest.fallback keys {sorted(_fb(st))} (the keys that differ from the agent's: {diff}), on "
              f"{_fb(st).get('on')!r}" if have else
              f"no `{PROBE}` (an engine before s136: no fallback op will be sent)")
    g.note(f"probe stage: {cb.stage_note(st)}; act.guest.fallback {'present' if have else 'ABSENT'}; act.guest.hold "
           f"{'present' if cb.has(st, HOLD_PROBE) else 'ABSENT'}")
    _leg_proof(g, led)
    try:
        g.state_every(1)
    except (HarnessError, AttributeError) as err:
        g.note(f"stateevery 1 refused ({str(err)[:120]})")
    _battle_1(g, led, field, ctx)
    _oracle(g, led, ctx)
    fp, fwhy = cb.fingerprint(g, field=field)
    ctx["fp0"] = fp
    g.note(f"the invariants before boot 1: {'read' if fp else 'UNREADABLE: ' + fwhy}")
    if not have:
        led.unreached([c for c in FALLBACK_CHECKS if c != "S136-R"],
                      f"`{PROBE}` is absent: an engine before s136 (the probe fails closed; no fallback op was sent)")
        return
    if calibrate:
        _act_verb(g, "fallback", "off")
        ctx["levers_set"] = True
        g.note("CALIBRATION: `actbench fallback off` -- the pre-s136 guest for every leg below")
    _boot_1(g, led, field, ctx)
    hd._boot_one(g, led, field, ctx, ("S136-LETHAL",), _leg_lethal)
    _boot_backlog(g, led, field, ctx)
    if calibrate:
        _act_verb(g, "fallback", "on")


def _leg_proof(g, led: cb.Ledger) -> None:
    proof = cb.poll(g, lambda s: cb.count(cb.log_lines(g), PROOF) >= 1, 8.0, "the proof block's action-fallback line")
    lines = [ln for ln in cb.log_lines(g) if PROOF in ln]
    last = lines[-1] if lines else ""
    failed = [ln for ln in lines if "action fallback selftest: FAIL" in ln]
    led.check("S136-PROOF", proof is not None and PROOF_OK in last and not failed,
              (last.split("|", 2)[-1].strip()[-300:] if last else "no 'action fallback selftest' line (an engine before "
                                                                  "s136 has no ActFallbackSelfTest)")
              + (f"; FAIL lines: {len(failed)}" if failed else "") + f"; want '{PROOF_OK}'")


# ------------------------------------------------------------------------------------------------ battle 1 and the oracle
def _battle_1(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    """coop_action_hold's battle 1 (`actbench tape rec` + `battle 306 <group>`, the plan that cannot end the fight early),
    its result screen cleared with Session.leave_battle(stop_on_field=True) (s134 LESSON 4), the tape paged out and read
    offline (coop_action_hold.read_tape: Zidane's Attack, Garnet's Potion, an enemy START, a Defend)."""
    host = cb.has(g.state, HOST_PROBE)
    if host:
        _act_verb(g, "tape", "rec")
    if cb.poll(g, lambda s: cb.free(s) and s.ui_state == "FieldHUD" and not s.in_battle, 30.0, "a playable field") is None:
        led.unreached(("S136-PRE", "S136-TAPE"), f"not on a playable field before battle 1 (ui {g.state.ui_state!r})")
        return
    try:
        g.start_battle(SCENE, group=GROUP)
    except HarnessError as err:
        led.unreached(("S136-PRE", "S136-TAPE"), f"`battle {SCENE} {GROUP}` did not start: {str(err)[:200]}")
        return
    _samples, en = cb.watch(g, lambda s: s.commands_enabled, ar.INTRO_S)
    st = en or g.state
    names = {k: ar._unit_named(st, k) for k in ("zidane", "vivi", "garnet")}
    foes = cb.units(st, player=False)
    led.check("S136-PRE", all(names.values()) and len(foes) >= 2,
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
        led.check("S136-TAPE", False, f"no `{HOST_PROBE}`: an engine before s133 records no action tape")
        return
    _act_verb(g, "tape", "stop")
    t = _sub(ar._host(cb.poll(g, lambda s: _sub(ar._host(s), "tape").get("state") == "stopped", 3.0, "the tape stopped")
                      or g.state), "tape")
    frames, why = ar._dump_all(g, _num(t.get("frames")) or 0)
    ctx["tape"] = hd.read_tape(frames, ctx)
    tp = ctx["tape"]
    led.check("S136-TAPE", not why and tp.get("attack") is not None and tp.get("potion") is not None
              and tp.get("enemy") is not None,
              why or f"{len(frames)} frame(s); Zidane's Attack START {tp.get('attack')}; Garnet's Potion START "
                     f"{tp.get('potion')}; an enemy START {tp.get('enemy')}; a Defend START {tp.get('defend')}; the plan "
                     f"{ctx.get('plan')}")


def _oracle(g, led: cb.Ledger, ctx: dict) -> None:
    """THE ORACLE, offline: scene 306's sequences -> the ENEMY leg's sub (the taped one; else the lowest with a clip) and
    its clip, and the IDLE leg's Idle-only sub."""
    clips, why = scene_oracle(SCENE, g.game_path)
    ctx["oracle"] = clips
    if clips is None:
        led.check("S136-ORACLE", False, why)
        return
    en = (ctx.get("tape") or {}).get("enemy")
    k = en["sub"] if en and clips.get(en["sub"]) else next((s for s in sorted(clips) if clips[s]), None)
    idle = idle_only_subs(clips)
    ctx["enemy_sub"], ctx["enemy_clip"], ctx["idle_sub"] = k, clips.get(k) if k is not None else None, (
        idle[0] if idle else None)
    led.check("S136-ORACLE", k is not None and ctx["enemy_clip"] is not None and ctx["idle_sub"] is not None,
              f"{why}; ENEMY plays sub {k} ({'the taped one' if en and k == en['sub'] else 'the taped sub ' + str(en and en['sub']) + ' had no clip: the lowest with one'}) "
              f"-> {ctx['enemy_clip']!r}; IDLE plays sub {ctx['idle_sub']}; every sub {clips}")


# ------------------------------------------------------------------------------------------------ boot 1
def _cast(x, ctx: dict) -> dict:
    """The diorama's cast by WIRE (coop_action_replay._who: Zidane's seat is the selftest stand-in -- s134 LESSON 1)."""
    return ar._who(x, ctx)


def _boot_1(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    st, why = hd._boot(g, field)
    if st is None:
        led.unreached(BOOT_1_LEGS, f"boot 1 failed: {why}")
        return
    fb = _fb(st)
    want_on = not ctx.get("levers_set")                     # [fix pass: harness-07] COOP_CALIBRATE pulled the lever
    led.check("S136-BOOT", fb != {} and all(_fv(st, k) == 0 for k in (*BW.ACT_FALLBACK_BUCKETS, "parse_failed"))
              and fb.get("last") is None and fb.get("on") is want_on,
              _fbrief(st) + f" (want on {want_on}: {'the lever pulled' if not want_on else 'no lever'})")
    try:
        s1, w1 = _act_verb(g, "replay", "off")              # every START declines `lever`: every impact UNCOVERED
        if s1 is None:
            led.unreached(BOOT_1_LEGS, f"`actbench replay off` was refused: {w1}")
            return
        for ids, leg in ((("S136-ITEM",), _leg_item), (("S136-ITEMA",), _leg_itema), (("S136-MAGIC",), _leg_magic),
                         (("S136-ATTACK",), _leg_attack), (("S136-ENEMY",), _leg_enemy), (("S136-IDLE",), _leg_idle),
                         (("S136-DEF",), _leg_def), (("S136-SELF",), _leg_self), (("S136-OLD",), _leg_old),
                         (("S136-BURST1",), _leg_burst1), (("S136-BURSTD",), _leg_burstd), (("S136-BURSTC",), _leg_burstc)):
            hd._guard(led, ids, leg, g, led, ctx)
        s2, w2 = _act_verb(g, "replay", "on")               # the replays run: COVERED, DECLINED, NOOP
        if s2 is None:
            led.unreached(("S136-COV", "S136-DECL", "S136-NOOP"), f"`actbench replay on` was refused: {w2}")
            return
        for ids, leg in ((("S136-COV",), _leg_cov), (("S136-DECL",), _leg_decl), (("S136-NOOP",), _leg_noop)):
            hd._guard(led, ids, leg, g, led, ctx)
    finally:
        led.unreached(BOOT_1_LEGS, "boot 1 ended before this leg")
        hd._out(g, field)


def _settle_mot(g, slot: int, mot: int, timeout: float = 3.0) -> None:
    """Wait (bounded) until the unit's `mot` is NOT ``mot`` -- an earlier leg's clip played out -- so a leg's read of that
    motion is its own write's."""
    cb.poll(g, lambda s: ar._unit(s, slot).get("mot") != mot, timeout, f"slot {slot}'s mot to leave {mot}")


def _write_seen(g, st0, act_id: int | None, base: dict, timeout: float = CLIP_S) -> tuple:
    """Every publish from the feed's own state until `last` names THIS write (id ``act_id``; None = an old host's: the
    clips counter moved). (the publish of the write or None, the samples)."""
    def until(s):
        if act_id is None:
            return _fv(s, "clips") + _fv(s, "collapsed") > base["clips"] + base["collapsed"]
        return _num(_flast(s).get("id")) == act_id and _fv(s, "clips") + _fv(s, "collapsed") > base["clips"] + base["collapsed"]
    samples, hit = cb.watch_from(g, st0, until, timeout)
    return hit, samples


def _player_clip_leg(g, led: cb.Ledger, ctx: dict, cid: str, *, caster: str, target: str, cmd: int, sub: int,
                     kind: str, mot: int, dmg: bool, start_kind: int = BW.VFX_KIND_SPECIAL, start_num: int = 0) -> dict:
    """One uncovered PLAYER action: its START (declined `lever`) + its impact in ONE feed; judged on `last` (this write),
    the clips counter and the caster's `mot` / `anim` on the publish of the write. Returns the leg's delta."""
    st = g.state
    cast = _cast(st, ctx)
    cu, cw = cast[caster]
    tu, tw = cast[target]
    if cu is None or tu is None or cw is None or tw is None:
        led.check(cid, False, f"not reached: no {caster} ({cw}) or {target} ({tw}) here")
        return {}
    slot = int(cu["slot"])
    _settle_mot(g, slot, mot)
    st = g.state
    base = _fbase(st)
    act_id, start = _start(cw, player=True, cmd=cmd, sub=sub, tar=ar._bit(tw), kind=start_kind, num=start_num)
    self_cast = caster == target
    imp = _impact(cw, tw, act_id=act_id, fig=FIG[cid.split("-", 1)[1]], tgt_raw=_raws(tu, dent=3 if dmg else 0),
                  cast_raw=_raws(cu), player_caster=True, player_target=bool(tu.get("player")), cmd=cmd, sub=sub,
                  dmg=dmg)
    st1, why = _feed(g, [start, imp])
    if st1 is None:
        led.check(cid, False, f"not reached: the feed was refused: {why}")
        return {}
    hit, samples = _write_seen(g, st1, act_id, base)
    x = hit or g.state
    mots = [ar._unit(s, slot).get("mot") for s in samples]
    ok, detail = judge_clip(_flast(x), want_id=act_id, kind=kind, cmd=cmd, sub=sub, actor=cw, keyed_by="id")
    u = ar._unit(x, slot)
    d = _delta(x, base)
    led.check(cid, hit is not None and ok and d["clips"] == 1 and u.get("mot") == mot and u.get("anim") == _flast(x).get("clip")
              and _gv(x, "declined") == base["declined"] + 1,
              f"{detail}; {caster}'s seat (slot {slot}, {u.get('name')!r}) mot {u.get('mot')!r} (want {mot}) anim "
              f"{u.get('anim')!r}; the mots seen {sorted({m for m in mots if m is not None})} (MP_ATTACK {BW.MP_ATTACK} = "
              f"the s110 swing); self-target {self_cast}, DmgMot {dmg}; delta {d}; declined "
              f"{base['declined']} -> {_gv(x, 'declined')} (`lever`)")
    return d


def _leg_item(g, led: cb.Ledger, ctx: dict) -> None:
    pot = (ctx.get("tape") or {}).get("potion") or {}
    pcmd, psub = ctx.get("potion_sent") or (BW.CMD_ITEM_ID, BW.ITEM_POTION_ID)
    _player_clip_leg(g, led, ctx, "S136-ITEM", caster="garnet", target="garnet", cmd=pcmd, sub=psub, kind="item",
                     mot=BW.MP_ITEM1, dmg=False, start_kind=pot.get("kind", BW.VFX_KIND_SPECIAL), start_num=pot.get("num", 0))


def _leg_itema(g, led: cb.Ledger, ctx: dict) -> None:
    pot = (ctx.get("tape") or {}).get("potion") or {}
    pcmd, psub = ctx.get("potion_sent") or (BW.CMD_ITEM_ID, BW.ITEM_POTION_ID)
    _player_clip_leg(g, led, ctx, "S136-ITEMA", caster="garnet", target="vivi", cmd=pcmd, sub=psub, kind="item",
                     mot=BW.MP_ITEM1, dmg=False, start_kind=pot.get("kind", BW.VFX_KIND_SPECIAL), start_num=pot.get("num", 0))


def _leg_magic(g, led: cb.Ledger, ctx: dict) -> None:
    _player_clip_leg(g, led, ctx, "S136-MAGIC", caster="vivi", target="fang1", cmd=BW.CMD_BLACK_MAGIC_ID,
                     sub=BW.ABILITY_FIRE_ID, kind="magic", mot=BW.MP_MAGIC, dmg=True)


def _leg_attack(g, led: cb.Ledger, ctx: dict) -> None:
    att = (ctx.get("tape") or {}).get("attack") or {}
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    _player_clip_leg(g, led, ctx, "S136-ATTACK", caster="zidane", target="fang1", cmd=acmd, sub=asub, kind="attack",
                     mot=BW.MP_ATTACK, dmg=True, start_num=att.get("num", 0))


def _enemy_frames(x, ctx: dict, *, sub: int, fig: int, foe: str = "fang1", lethal_caster: bool = False,
                  start: bool = True, cmd: int | None = None) -> tuple:
    """Fang's EnemyAtk ``sub`` on Zidane's seat (a non-lethal hit): (id, frames, the Fang's unit, its wire) or (None, why,
    None, None). ``cmd`` replaces the taped enemy command ([fix pass 2: rstock-1] ScriptCounter1: a Loop move)."""
    cast = _cast(x, ctx)
    (fu, fw), (zu, zw) = cast[foe], cast["zidane"]
    en = (ctx.get("tape") or {}).get("enemy") or {"cmd": BW.CMD_ENEMY_ATK}
    if cmd is not None:
        en = dict(en, cmd=cmd)
    if fu is None or zu is None or fw is None or zw is None:
        return None, f"no {foe} ({fw}) or Zidane's seat ({zw}) here", None, None
    frames = []
    act_id = None
    if start:
        act_id, s = _start(fw, player=False, cmd=en["cmd"], sub=sub, tar=ar._bit(zw), kind=BW.VFX_KIND_ENEMY, num=sub)
        frames.append(s)
    else:
        act_id = next(_IDS)
    frames.append(_impact(fw, zw, act_id=act_id, fig=fig, tgt_raw=_raws(zu, dent=2),
                          cast_raw=_raws(fu, hp=0 if lethal_caster else None), player_caster=False, player_target=True,
                          cmd=en["cmd"], sub=sub, dmg=True))
    return act_id, frames, fu, fw


def _leg_enemy(g, led: cb.Ledger, ctx: dict) -> None:
    """Fang 1's EnemyAtk sub k, then -- [fix pass 2: rstock-1] the SAME request, Block(2) frames on (another frame: no
    collapse) -- its LOOP move (ScriptCounter1) sub k under its own id: two enemy clips, each THE ORACLE's."""
    k, want = ctx.get("enemy_sub"), ctx.get("enemy_clip")
    if k is None or want is None:
        led.check("S136-ENEMY", False, "not reached: no oracle clip (S136-ORACLE)")
        return
    st = g.state
    base = _fbase(st)
    act_id, frames, fu, fw = _enemy_frames(st, ctx, sub=k, fig=FIG["ENEMY"])
    loop_id, loop_frames, _lu, _lw = _enemy_frames(st, ctx, sub=k, fig=FIG["ENEMY"], cmd=BW.CMD_SCRIPT_COUNTER1)
    if act_id is None or loop_id is None:
        led.check("S136-ENEMY", False, f"not reached: {frames if act_id is None else loop_frames}")
        return
    at = cb.mark(g)
    st0 = g.state
    try:
        g.send(f"netsync actbench feed {_feed_arg(frames)}", f"netsync actbench feed {_feed_arg(loop_frames)}", timeout=20.0)
    except HarnessError as err:
        led.check("S136-ENEMY", False, f"not reached: the feeds were refused: {str(err)[:300]}")
        return
    hit, samples = _write_seen(g, st0, loop_id, base)
    x = hit or g.state
    samples.append(x)
    en = (ctx.get("tape") or {}).get("enemy") or {"cmd": BW.CMD_ENEMY_ATK}
    ok, detail = judge_clip(_flast(x), want_id=loop_id, kind="enemy", cmd=BW.CMD_SCRIPT_COUNTER1, sub=k, actor=fw,
                            keyed_by="id", clip=want)
    # the EnemyAtk write: a sampled `last` or its clip line (the lines are capped at 8 a boot: ENEMY's are its 5th and 6th)
    seen = [dict(r, actor=r.get("actor", r.get("slot"))) for r in
            lasts_union(_fb(s) for s in samples) + [p for p in (BW.parse_fallback_clip(ln) for ln in cb.new(g, at))
                                                     if p is not None]]
    first = next((r for r in seen if r.get("id") == act_id), None)
    fok, fdetail = judge_clip(first or {}, want_id=act_id, kind="enemy", cmd=en["cmd"], sub=k, actor=fw, keyed_by="id",
                              clip=want)
    anim = ar._unit(x, int(fu["slot"])).get("anim")
    d = _delta(x, base)
    led.check("S136-ENEMY", hit is not None and ok and fok and d["clips"] == 2 and d["none"] == 0 and anim == want,
              f"the LOOP write: {detail}; the EnemyAtk write: {fdetail if first else 'NOT SEEN (no `last`, no line)'}; THE "
              f"ORACLE's sub {k}: {want!r}; Fang 1 (slot {fu['slot']}) anim {anim!r}; delta {d}")


def _no_clip_leg(g, led: cb.Ledger, ctx: dict, cid: str, frames: list, bucket: str, n: int, extra=None) -> None:
    """A leg whose action plays NO clip: ``frames`` in ONE feed; ``bucket`` +``n``, clips +0 -- judged after the drain (a
    bounded wait for the bucket, then a few frames for any late write) -- and ITS IN-RUN RED ([fix pass 2: rharness-02]):
    the same predicate on THIS leg's own delta with one clip injected (:func:`in_run_red`) must read False."""
    st = g.state
    base = _fbase(st)
    st1, why = _feed(g, frames)
    if st1 is None:
        led.check(cid, False, f"not reached: the feed was refused: {why}")
        return
    cb.poll(g, lambda s: _fv(s, bucket) >= base[bucket] + n, CLIP_S, f"{cid}'s {bucket}")
    g.wait_frames(10)
    x = g.state
    d = _delta(x, base)
    red = in_run_red(d, bucket, n)
    more = extra(x, base) if extra else (True, "")
    led.check(cid, no_clip_pred(d, bucket, n) and red is False and more[0],
              f"delta {d} (want {bucket} +{n}, clips +0); the in-run red (the predicate on this delta with one clip "
              f"injected) read {red!r} (want False); {more[1]}; {_fbrief(x)}")


def _leg_idle(g, led: cb.Ledger, ctx: dict) -> None:
    j = ctx.get("idle_sub")
    if j is None:
        led.check("S136-IDLE", False, "not reached: the oracle names no Idle-only sub (S136-ORACLE)")
        return
    act_id, frames, _fu, _fw = _enemy_frames(g.state, ctx, sub=j, fig=FIG["IDLE"])
    if act_id is None:
        led.check("S136-IDLE", False, f"not reached: {frames}")
        return
    _no_clip_leg(g, led, ctx, "S136-IDLE", frames, "none", 1,
                 extra=lambda x, base: (_num(_flast(x).get("id")) != act_id and _fv(x, "parse_failed") == base["parse_failed"],
                                        f"last {cb.pick(_flast(x), 'id', 'sub', 'clip')} (not id {act_id}); parse_failed "
                                        f"+{_fv(x, 'parse_failed') - base['parse_failed']}"))


def _leg_def(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    cast = _cast(st, ctx)
    (zu, zw), (vu, vw) = cast["zidane"], cast["vivi"]
    if zw is None or vw is None:
        led.check("S136-DEF", False, f"not reached: Zidane's seat {zw}, Vivi {vw}")
        return
    dsub = ((ctx.get("tape") or {}).get("defend") or {}).get("sub", DEFEND_SUB)
    d_id, d_start = _start(zw, player=True, cmd=BW.CMD_DEFEND_ID, sub=dsub, tar=ar._bit(zw), kind=BW.VFX_KIND_COMMON, num=4)
    c_id, c_start = _start(vw, player=True, cmd=BW.CMD_CHANGE_ID, sub=0, tar=ar._bit(vw), kind=BW.VFX_KIND_COMMON,
                           num=BW.CMD_CHANGE_ID)
    frames = [d_start, _impact(zw, zw, act_id=d_id, fig=FIG["DEF"], tgt_raw=_raws(zu), cast_raw=_raws(zu),
                               player_caster=True, player_target=True, cmd=BW.CMD_DEFEND_ID, sub=dsub, dmg=False),
              c_start, _impact(vw, vw, act_id=c_id, fig=FIG["CHG"], tgt_raw=_raws(vu), cast_raw=_raws(vu),
                               player_caster=True, player_target=True, cmd=BW.CMD_CHANGE_ID, sub=0, dmg=False)]
    _no_clip_leg(g, led, ctx, "S136-DEF", frames, "none", 2)


def _leg_self(g, led: cb.Ledger, ctx: dict) -> None:
    st = g.state
    vu, vw = _cast(st, ctx)["vivi"]
    if vw is None:
        led.check("S136-SELF", False, "not reached: no Vivi")
        return
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    s_id, s_start = _start(vw, player=True, cmd=acmd, sub=asub, tar=ar._bit(vw))
    hit = _raws(vu, dent=4)
    frames = [s_start, _impact(vw, vw, act_id=s_id, fig=FIG["SELF"], tgt_raw=hit, cast_raw=hit, player_caster=True,
                               player_target=True, cmd=acmd, sub=asub, dmg=True)]
    _no_clip_leg(g, led, ctx, "S136-SELF", frames, "guarded", 1)


def _zidane_attack_impacts(x, ctx: dict, ids, fig: int) -> tuple:
    """Zidane's seat's Attack impacts on Fang 1, one per id in ``ids`` (None = an old host's; 0 = id 0): (frames, its
    unit, its wire) or (None, why, None)."""
    cast = _cast(x, ctx)
    (zu, zw), (fu, fw) = cast["zidane"], cast["fang1"]
    if zw is None or fw is None:
        return None, f"no Zidane seat ({zw}) or Fang 1 ({fw})", None
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    return [_impact(zw, fw, act_id=i, fig=fig, tgt_raw=_raws(fu, dent=1), cast_raw=_raws(zu), player_caster=True,
                    player_target=False, cmd=acmd, sub=asub, dmg=True) for i in ids], zu, zw


def _leg_burst1(g, led: cb.Ledger, ctx: dict) -> None:
    """ONE action id, three impacts within 100 ms: the START + impact A in one feed, then -- the SAME request, Block(2)
    frames on -- B and C in one feed (s135 LESSON: never a second request after a poll)."""
    st = g.state
    cast = _cast(st, ctx)
    zw, fw = cast["zidane"][1], cast["fang1"][1]
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    if zw is None or fw is None:
        led.check("S136-BURST1", False, "not reached: no Zidane seat or Fang 1")
        return
    act_id, start = _start(zw, player=True, cmd=acmd, sub=asub, tar=ar._bit(fw))
    frames, _zu, _zw = _zidane_attack_impacts(st, ctx, (act_id, act_id, act_id), FIG["BURST1"])
    base = _fbase(st)
    at = cb.mark(g)
    try:
        g.send(f"netsync actbench feed {_feed_arg([start, frames[0]])}", f"netsync actbench feed {_feed_arg(frames[1:])}",
               timeout=20.0)
    except HarnessError as err:
        led.check("S136-BURST1", False, f"not reached: the feeds were refused: {str(err)[:300]}")
        return
    cb.poll(g, lambda s: _fv(s, "deduped") >= base["deduped"] + 2, CLIP_S, "the burst's dedupe")
    g.wait_frames(10)
    x = g.state
    d = _delta(x, base)
    lines = [p for p in (BW.parse_fallback_clip(ln) for ln in cb.new(g, at)) if p is not None and p["id"] == act_id]
    led.check("S136-BURST1", d["clips"] == 1 and d["deduped"] == 2 and d["collapsed"] == 0
              and _flast(x).get("keyed_by") == "id" and _num(_flast(x).get("id")) == act_id,
              f"delta {d}; last {cb.pick(_flast(x), 'id', 'keyed_by', 'kind', 'ms')}; the two later impacts drained Block(2) "
              f"frames on -- well inside 100 ms; {len(lines)} clip line(s) for id {act_id} (reported: the lines stop at "
              f"{BW.ACT_FALLBACK_LOG_MAX} a boot)")


def _leg_burstd(g, led: cb.Ledger, ctx: dict) -> None:
    """Three distinct ids on Zidane's seat, three drains: three feeds in ONE request (Block(2) frames apart)."""
    st = g.state
    ids = [next(_IDS) for _ in range(3)]
    frames, _zu, _zw = _zidane_attack_impacts(st, ctx, ids, FIG["BURSTD"])
    if frames is None:
        led.check("S136-BURSTD", False, f"not reached: {_zu}")
        return
    base = _fbase(st)
    try:
        g.send(*[f"netsync actbench feed {_feed_arg(f)}" for f in frames], timeout=20.0)
    except HarnessError as err:
        led.check("S136-BURSTD", False, f"not reached: the feeds were refused: {str(err)[:300]}")
        return
    cb.poll(g, lambda s: _fv(s, "clips") + _fv(s, "collapsed") >= base["clips"] + base["collapsed"] + 3, CLIP_S,
            "three writes")
    g.wait_frames(10)
    x = g.state
    d = _delta(x, base)
    led.check("S136-BURSTD", d["clips"] == 3 and d["collapsed"] == 0 and d["deduped"] == 0
              and _num(_flast(x).get("id")) == ids[-1],
              f"delta {d}; last {cb.pick(_flast(x), 'id', 'keyed_by', 'kind')} (want id {ids[-1]})")
    ctx["burstd_delta"] = d


def _leg_burstc(g, led: cb.Ledger, ctx: dict) -> None:
    """Three distinct ids on Zidane's seat in ONE feed (one drain, one frame): one clip shows, two collapse."""
    st = g.state
    ids = [next(_IDS) for _ in range(3)]
    frames, _zu, _zw = _zidane_attack_impacts(st, ctx, ids, FIG["BURSTC"])
    if frames is None:
        led.check("S136-BURSTC", False, f"not reached: {_zu}")
        return
    base = _fbase(st)
    st1, why = _feed(g, frames)
    if st1 is None:
        led.check("S136-BURSTC", False, f"not reached: the feed was refused: {why}")
        return
    cb.poll(g, lambda s: _fv(s, "clips") + _fv(s, "collapsed") >= base["clips"] + base["collapsed"] + 3, CLIP_S,
            "three writes")
    g.wait_frames(10)
    x = g.state
    d = _delta(x, base)
    led.check("S136-BURSTC", d["clips"] == 1 and d["collapsed"] == 2 and d["deduped"] == 0
              and _num(_flast(x).get("id")) == ids[-1],
              f"delta {d} (want clips +1, collapsed +2: counted when WRITTEN); last "
              f"{cb.pick(_flast(x), 'id', 'keyed_by')} (the last written: id {ids[-1]})")


def _leg_old(g, led: cb.Ledger, ctx: dict) -> None:
    """An OLD HOST: Vivi's Fire with no action id, FIVE impacts on ONE request -- A (a 46-byte frame, `feed`); B and C (an
    id-0 extension and a 46-byte frame on ONE verb, `feedat 250`: one Due, so the two drain in ONE Update whatever the
    frame rate -- [fix pass: timing-4]); D (`feedat 500`); E (`feedat 1100`). [fix pass 2: rharness-03] With each step
    Block(2) agent frames on (33-133 ms) and a drain at most a frame late: B / C land 267-450 ms after A (deduped); D
    550+ ms after A but at most 450 after B / C -- deduped ONLY by THE SLIDE (an anchored window would clip it); E 600+ ms
    after D (the second clip). Judged on the counters, `last` and the ENGINE's own clock (`last.ms` over every publish)."""
    st = g.state
    cast = _cast(st, ctx)
    (vu, vw), (fu, fw) = cast["vivi"], cast["fang1"]
    if vu is None or vw is None or fw is None:
        led.check("S136-OLD", False, f"not reached: Vivi {vw}, Fang 1 {fw}")
        return
    vslot = int(vu["slot"])
    _settle_mot(g, vslot, BW.MP_MAGIC)
    st = g.state
    base = _fbase(st)
    old = [_impact(vw, fw, act_id=i, fig=FIG["OLD"], tgt_raw=_raws(fu, dent=1), cast_raw=_raws(vu), player_caster=True,
                   player_target=False, cmd=BW.CMD_BLACK_MAGIC_ID, sub=BW.ABILITY_FIRE_ID, dmg=True)
           for i in (None, 0, None, None, None)]
    at = cb.mark(g)
    try:
        g.send(f"netsync actbench feed {_feed_arg(old[0])}", f"netsync actbench feedat 250 {_feed_arg(old[1:3])}",
               f"netsync actbench feedat 500 {_feed_arg(old[3])}", f"netsync actbench feedat 1100 {_feed_arg(old[4])}",
               timeout=20.0)
    except HarnessError as err:
        led.check("S136-OLD", False, f"not reached: the feeds were refused: {str(err)[:300]}")
        return
    samples, _end_st = cb.watch(g, lambda s: _fv(s, "clips") >= base["clips"] + 2 and _fv(s, "deduped") >= base["deduped"] + 3,
                                CLIP_S)
    g.wait_frames(10)
    x = g.state
    samples.append(x)
    d = _delta(x, base)
    mots = {ar._unit(s, vslot).get("mot") for s in samples}
    # the timing on `last` over every publish (the clip LINES are capped at ActFallbackLogMax a boot: reported, not judged)
    ok, detail = judge_window(lasts_union(_fb(s) for s in samples), vw, BW.CMD_BLACK_MAGIC_ID, BW.ABILITY_FIRE_ID,
                              min_gap=OLD_E_GAP)
    lines = [p for p in (BW.parse_fallback_clip(ln) for ln in cb.new(g, at)) if p is not None]
    lok, ldetail = judge_clip(_flast(x), want_id=None, kind="magic", cmd=BW.CMD_BLACK_MAGIC_ID, sub=BW.ABILITY_FIRE_ID,
                              actor=vw, keyed_by="caster")
    led.check("S136-OLD", d["clips"] == 2 and d["deduped"] == 3 and d["collapsed"] == 0 and ok and lok
              and BW.MP_MAGIC in mots and _guest(x).get("old_host") is True,
              f"delta {d}; {detail}; {ldetail}; Vivi's mots {sorted(m for m in mots if m is not None)} (want "
              f"{BW.MP_MAGIC} among them); old_host {_guest(x).get('old_host')!r}; the clip lines (reported) "
              f"{[(p['ms'], p['keyed_by']) for p in lines if p['slot'] == vw]}")


# ---- boot 1, `replay on`
def _leg_cov(g, led: cb.Ledger, ctx: dict) -> None:
    """A COVERED impact: Zidane's seat's Attack START (the taped num) + its impact on Fang 1 -- held, released at the
    replay's hit (covered there); s134's swing_skipped counts it at arrival."""
    st = g.state
    cast = _cast(st, ctx)
    zw, fw = cast["zidane"][1], cast["fang1"][1]
    att = (ctx.get("tape") or {}).get("attack")
    if zw is None or fw is None or att is None:
        led.check("S136-COV", False, f"not reached: Zidane's seat {zw}, Fang 1 {fw}, the taped Attack {att}")
        return
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    speed = att.get("speed") if isinstance(att.get("speed"), int) else 5
    act_id, start = _start(zw, player=True, cmd=acmd, sub=asub, tar=ar._bit(fw), kind=BW.VFX_KIND_SPECIAL, num=att["num"],
                           speed=speed)                    # (the taped num and host Speed: the replay the host taped)
    frames, _zu, _zw = _zidane_attack_impacts(st, ctx, (act_id,), FIG["COV"])
    base = _fbase(st)
    st1, why = _feed(g, [start, *frames])
    if st1 is None:
        led.check("S136-COV", False, f"not reached: the feed was refused: {why}")
        return
    end = cb.poll(g, lambda s: _fv(s, "covered") >= base["covered"] + 1 and _gv(s, "running") == 0, REPLAY_S,
                  "the covered release and the replay's end")
    g.wait_frames(5)
    x = g.state
    d = _delta(x, base)
    red = in_run_red(d, "covered")                         # [fix pass 2: rharness-02] its own delta, one clip injected
    led.check("S136-COV", end is not None and no_clip_pred(d, "covered") and red is False
              and _gv(x, "swing_skipped") == base["swing_skipped"] + 1 and _num(_flast(x).get("id")) == base["last_id"],
              f"delta {d}; swing_skipped {base['swing_skipped']} -> {_gv(x, 'swing_skipped')}; last id "
              f"{_flast(x).get('id')!r} (unchanged {base['last_id']!r}); the in-run red (this delta, one clip injected) "
              f"read {red!r}; {ar._brief(x)}")


def _leg_decl(g, led: cb.Ledger, ctx: dict) -> None:
    """A held impact whose START then DECLINES: Garnet's Potion START + her self impact + its END in ONE feed -- the impact
    HELD for the replay, the START declined `stale` at the decide, the impact released `declined`: its clip then."""
    st = g.state
    gu, gw = _cast(st, ctx)["garnet"]
    if gu is None or gw is None:
        led.check("S136-DECL", False, "not reached: no Garnet")
        return
    pot = (ctx.get("tape") or {}).get("potion") or {}
    pcmd, psub = ctx.get("potion_sent") or (BW.CMD_ITEM_ID, BW.ITEM_POTION_ID)
    gslot = int(gu["slot"])
    _settle_mot(g, gslot, BW.MP_ITEM1)
    st = g.state
    base = _fbase(st)
    act_id, start = _start(gw, player=True, cmd=pcmd, sub=psub, tar=ar._bit(gw), kind=pot.get("kind", BW.VFX_KIND_SPECIAL),
                           num=pot.get("num", 0))
    imp = _impact(gw, gw, act_id=act_id, fig=FIG["DECL"], tgt_raw=_raws(gu), cast_raw=_raws(gu), player_caster=True,
                  player_target=True, cmd=pcmd, sub=psub, dmg=False)
    st1, why = _feed(g, [start, imp, _end(act_id, pcmd, psub)])
    if st1 is None:
        led.check("S136-DECL", False, f"not reached: the feed was refused: {why}")
        return
    hit, _samples = _write_seen(g, st1, act_id, base)
    x = hit or g.state
    ok, detail = judge_clip(_flast(x), want_id=act_id, kind="item", cmd=pcmd, sub=psub, actor=gw, keyed_by="id",
                            via="declined")
    d = _delta(x, base)
    rel = _num(_sub(_guest(x), "hold").get("rel_declined")) or 0
    led.check("S136-DECL", hit is not None and ok and d["clips"] == 1 and _gv(x, "stale") == base["stale"] + 1
              and rel == base["rel_declined"] + 1 and ar._unit(x, gslot).get("mot") == BW.MP_ITEM1,
              f"{detail}; delta {d}; stale +{_gv(x, 'stale') - base['stale']}; hold.rel_declined +"
              f"{rel - base['rel_declined']}; Garnet's mot {ar._unit(x, gslot).get('mot')!r}")


def _leg_noop(g, led: cb.Ledger, ctx: dict) -> None:
    """A kind-NONE START (Vivi's Defend, no vfx) + its impact: a NOOP -- nothing to show, covered."""
    st = g.state
    vu, vw = _cast(st, ctx)["vivi"]
    if vu is None or vw is None:
        led.check("S136-NOOP", False, "not reached: no Vivi")
        return
    dsub = ((ctx.get("tape") or {}).get("defend") or {}).get("sub", DEFEND_SUB)
    act_id, start = _start(vw, player=True, cmd=BW.CMD_DEFEND_ID, sub=dsub, tar=ar._bit(vw), kind=BW.VFX_KIND_NONE, num=0)
    imp = _impact(vw, vw, act_id=act_id, fig=FIG["NOOP"], tgt_raw=_raws(vu), cast_raw=_raws(vu), player_caster=True,
                  player_target=True, cmd=BW.CMD_DEFEND_ID, sub=dsub, dmg=False)
    base = _fbase(st)

    def extra(x, b):
        return _gv(x, "noop") == b["noop"] + 1, f"noop +{_gv(x, 'noop') - b['noop']}"
    st1, why = _feed(g, [start, imp])
    if st1 is None:
        led.check("S136-NOOP", False, f"not reached: the feed was refused: {why}")
        return
    cb.poll(g, lambda s: _fv(s, "covered") >= base["covered"] + 1, CLIP_S, "the NOOP's covered impact")
    g.wait_frames(10)
    x = g.state
    d = _delta(x, base)
    ok, why2 = extra(x, base)
    led.check("S136-NOOP", no_clip_pred(d, "covered") and d["none"] == 0 and ok, f"delta {d}; {why2}; {_fbrief(x)}")


# ---- boot 2
def _leg_lethal(g, led: cb.Ledger, ctx: dict) -> None:
    """Fang 2's EnemyAtk sub k (a real clip: the oracle's) whose own caster lane is lethal -- no START (no record: an
    uncovered impact) -- on Zidane's seat: guarded, no clip; Fang 2 dies (its own boot)."""
    k = ctx.get("enemy_sub")
    if k is None or not ctx.get("enemy_clip"):
        led.check("S136-LETHAL", False, "not reached: no oracle clip (S136-ORACLE)")
        return
    act_id, frames, fu, _fw = _enemy_frames(g.state, ctx, sub=k, fig=FIG["LETHAL"], foe="fang2", lethal_caster=True,
                                            start=False)
    if act_id is None:
        led.check("S136-LETHAL", False, f"not reached: {frames}")
        return
    _no_clip_leg(g, led, ctx, "S136-LETHAL", frames, "guarded", 1,
                 extra=lambda x, base: (ar._unit(x, int(fu["slot"])).get("alive") is False,
                                        f"Fang 2 alive {ar._unit(x, int(fu['slot'])).get('alive')!r} (want False: its "
                                        f"lethal caster lane applied)"))


# ---- boot 3
def _boot_backlog(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    """BACKLOG: `dioboot` and an uncovered impact's `actbench feed` in ONE request (the feed lands Block(2) frames after the
    boot, inside its swirl -- a feed is no Leave: s134 LESSON 2 stands) -- drained in the first steady Update, a BACKLOG
    drain: backlog +1, clips +0 for the boot. The impact names battle 1's wires (no unit is published yet)."""
    cb.try_ns(g, "endbench", "clear")
    zw, fw = ctx.get("zidane_wire"), ctx.get("fang1_wire")
    acmd, asub = ctx.get("attack_sent") or (BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID)
    if zw is None or fw is None:
        led.check("S136-BACKLOG", False, f"not reached: no battle-1 wires (Zidane {zw}, Fang 1 {fw})")
        return
    imp = _impact(zw, fw, act_id=next(_IDS), fig=FIG["BACKLOG"], tgt_raw=(9000, 0), cast_raw=(600, 30), player_caster=True,
                  player_target=False, cmd=acmd, sub=asub, dmg=True)
    try:
        try:
            g.send(f"netsync dioboot {SCENE} {GROUP}", f"netsync actbench feed {_feed_arg(imp)}", timeout=30.0)
            sent, swhy = True, ""
        except HarnessError as err:
            sent, swhy = False, str(err)[:300]
        fed = g.state
        early = (_n(cb.path(fed, "netsync.diorama.intro.normal_ms"), -1)) < 0
        st = cb.poll(g, lambda s: cb.steady(s) and _n(cb.path(s, "netsync.diorama.intro.normal_ms"), -1) >= 0, cb.STEADY_S,
                     "the boot's steady latch")
        x = cb.poll(g, lambda s: _fv(s, "backlog") >= 1, 5.0, "the backlog impact") or g.state
        g.wait_frames(30)                                   # any late write would show by now
        x = g.state
        d = {k: _fv(x, k) for k in (*BW.ACT_FALLBACK_BUCKETS, "parse_failed")}     # (the boot's counters start at 0)
        red = in_run_red(d, "backlog")                     # [fix pass 2: rharness-02] its own delta, one clip injected
        led.check("S136-BACKLOG", sent and early and st is not None and no_clip_pred(d, "backlog") and red is False,
                  (swhy and f"the request was refused: {swhy}; ") + f"fed during the intro {early}; steady "
                  f"{st is not None}; the boot's counters {d}; the in-run red (this delta, one clip injected) read "
                  f"{red!r}; {_fbrief(x)}")
    except LEG_FAULTS as err:
        ar._faulted(led, ("S136-BACKLOG",), err)
    finally:
        led.unreached(("S136-BACKLOG",), "boot 3 ended before this leg")
        hd._out(g, field)


# ------------------------------------------------------------------------------------------------ the release
def _release(g, led: cb.Ledger, ctx: dict) -> None:
    """INV first (the last leave is behind us), then the fallback lever left SET on purpose and `reset`: the 'fallback lever
    back' line, and `on` at rest when re-read WITH the role."""
    fp0 = ctx.get("fp0")
    if ctx["probe"]:
        fp1, why = cb.fingerprint(g, field=ctx.get("field", cb.FIELD))
        diff = cb.fp_diff(fp0, fp1) if fp0 and fp1 else None
        led.check("S136-INV", fp0 is not None and fp1 is not None and not diff,
                  why or f"changed: {diff}; battle_no {fp0.get('_battle_no') if fp0 else None} -> "
                         f"{fp1.get('_battle_no') if fp1 else None} (a diorama's InitBattle bumps it: not judged)")
        _act_verb(g, "fallback", "off")
    else:
        led.check("S136-INV", True, "nothing was booted (the probe failed closed): nothing to compare")
    at = cb.mark(g)
    cb.release(g)
    lines = cb.new(g, at)
    if not ctx["probe"]:
        led.check("S136-R", False, f"`{PROBE}` absent: nothing was set")
        return
    rr, rwhy = cb.reread_with_role(g)
    f = _fb(rr) if rr is not None else {}
    led.check("S136-R", rr is not None and cb.count(lines, BW.LOG_FALLBACK_LEVER_BACK.split("] ", 1)[1]) == 1
              and f.get("on") is True,
              (f"re-read WITH the role: on {f.get('on')!r}" if rr is not None else f"no re-read with the role ({rwhy})")
              + f"; {cb.grep(lines, 'released with the harness')}")


# ================================================================================================ THE TAPE LEG
def _run_tape(g, arc: bool = False) -> None:
    """The tape leg -- or, ``arc`` ([fix pass: harness-01]), the arc leg: the same instrument on an OLD host's tape."""
    calibrate = cb.CALIBRATE
    cal = "S136A-CAL" if arc else "S136T-CAL"
    led = cb.Ledger(g, _arc_catalog(calibrate) if arc else _tape_catalog(calibrate), finals=("T2-SAVE", "T2-INI", cal))
    ctx = ar._TapeCtx()
    try:
        _tape_leg(g, led, ctx, calibrate, arc=arc)
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
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'action-fallback-arc' if arc else 'action-fallback-tape')}")
        if calibrate:
            led.close("not reached: the leg ended before this check")
            predicted, maybe = (_arc_predicted if arc else _tape_predicted)(_has_fallback(ctx))
            led.judge_calibration(cal, predicted, maybe)
        led.close(final=True)


def _has_fallback(ctx) -> bool:
    return any(isinstance(s.get("guest"), dict) and isinstance(s["guest"].get("fallback"), dict) for s in ctx.samples)


def _tape_leg(g, led: cb.Ledger, ctx, calibrate: bool, arc: bool = False) -> None:
    """coop_action_hold's tape leg, step for step (its tape, its CAL sidecar, its guest config, its replay-host), with
    ActionReplay 0 (1 under COOP_CALIBRATE: the inverse knob), judged on `act.guest.fallback` (:func:`judge_fallback_tape`).
    [fix pass: harness-01] ``arc``: THE ARC LEG -- the s117 arc tape (:func:`arc_tape`), its gate an OLD host's battle
    (:func:`arc_tape_facts`: no START -- the >= 1-START gate skipped), ActionReplay 1, judged by
    :func:`judge_fallback_arc`."""
    ids = list(ARC_CHECKS if arc else TAPE_CHECKS)
    what = "arc tape" if arc else "s133 tape"
    ctx.tape = arc_tape() if arc else ar.act_tape()
    if ctx.tape is None or not ctx.tape.exists():
        led.check("T2-TAPE", False, f"no {what} ({ctx.tape or ar.act_tape_dir()}): "
                                    + ("run coop_cut_hold's RECORDING steps (or set COOP_FB_ARC_TAPE)" if arc else
                                       "record one first (coop_action_replay's RECORDING steps)"))
        led.close(f"not reached: no {what}")
        return
    try:
        cp = pb.coop_peer_module()
        _header, records, torn = cp.read_tape(ctx.tape)
    except Exception as err:                               # noqa: BLE001 -- the reason is the check's detail
        led.check("T2-TAPE", False, f"no {what}: {ctx.tape} does not read back ({err})")
        led.close(f"not reached: no {what}")
        return
    ctx.facts = pb.tape_facts(records, cp, field=None)
    f1, f3 = ctx.facts["f1"], ctx.facts["f3"]
    ctx.field = f1.get("field") or pb.BENCH_FIELD
    ctx.scene, ctx.nonce = f3.get("map"), f3.get("nonce")
    ctx.act = ar.tape_act_facts(records, cp, ctx.nonce)
    act_ok, act_why = arc_tape_facts(ctx.act) if arc else (ctx.act["ok"], ctx.act["why"])
    plan = pb.plan_leg("cal", ctx.facts, ar.GRACE_MS / 1000.0)
    ok = act_ok and plan["ok"]
    led.check("T2-TAPE", ok, f"{ctx.tape.name} ({len(records)} records{', torn ' + str(torn) + ' B' if torn else ''}): "
                             f"field {ctx.field}, scene {ctx.scene}, nonce {ctx.nonce}; {act_why}"
                             + ("" if plan["ok"] else f"; the five facts: {plan['why'][:200]}"))
    if not ok:
        led.close(f"not reached: no {what}" if not act_ok else "not reached: the tape lacks a CAL fact")
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
    ctx.oracle, ctx.oracle_why = scene_oracle(ctx.scene, g.game_path) if ctx.scene is not None else (None, "no scene")
    g.note(f"the oracle for scene {ctx.scene}: {ctx.oracle_why}")
    cb.provenance(g)
    knob_off = not calibrate and not arc                 # the knob written 0 (the tape leg, not calibrating)
    g.note(f"R3 s136 {'arc' if arc else 'tape'} leg: {ctx.tape.name}, ActionReplay {0 if knob_off else 1}"
           + (" -- CALIBRATION (the inverse knob: the replays cover)" if calibrate and not arc else "")
           + (" -- CALIBRATION: an old host has no inverse knob (the plain run is judged)" if calibrate and arc else ""))
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
    values = dict(ar.GUEST_VALUES, ActionReplay="0" if knob_off else "1")
    rd = Path(getattr(g, "scenario_dir", None) or g.run_dir)
    ctx.guard = pb.IniGuard(Path(g.game_path) / "Memoria.ini", values,
                            label="coop-action-fallback-arc" if arc else "coop-action-fallback-tape", run_dir=rd)
    try:
        g.note(ctx.guard.apply())
    except (OSError, RuntimeError) as err:
        led.check("T2-PEER", False, f"the Memoria.ini edit failed: {err}")
        led.close("not reached: Memoria.ini could not be edited")
        return
    cfg = ar._tape_config(g, ctx, knob_off)                 # (the knob written 0 exactly when knob_off)
    if not cfg:
        led.check("T2-PEER", False, f"the engine never logged the guest config (config lines: "
                                    f"{pb.show(pb.hits(ctx.eng.lines(), 'config'))})")
        led.close("not reached: the guest config never applied")
        return
    tag = "arc" if arc else "fallback"
    ctx.peer = pb.PeerProc("replay-host", [ctx.tape, *pb.plan_args(plan, port=ar.PORT, code=ar.CODE)],
                           log_path=rd / f"coop_peer-replay-{tag}.log", out_path=rd / f"coop_peer-replay-{tag}.out")
    g.note(f"starting: {ctx.peer.command_text()}")
    ctx.peer.start()
    up = ctx.peer.wait_for(pb.PEER["listening"], 15.0, tick=lambda: ar._tape_sample(g, ctx))
    conn = ctx.peer.wait_for(pb.PEER["guest_connected"], 25.0, tick=lambda: ar._tape_sample(g, ctx)) if up else None
    start = ctx.peer.wait_for(pb.PEER["replay_start"], 10.0, tick=lambda: ar._tape_sample(g, ctx)) if conn else None
    relay = pb.hits(ctx.eng.lines(), "relay_up", pred=lambda m: m.group(3) == "guest" and m.group(2) == ar.CODE)
    knob_ok, knob_why = ar._tape_knob(cfg, knob_off, cb.has(g.state, GUEST_PROBE))
    ok = up is not None and conn is not None and start is not None and bool(relay) and knob_ok
    led.check("T2-PEER", ok, f"config: {pb.show(cfg, 1)}; {knob_why}; peer: {up[1] if up else 'never listened'} / "
                             f"{conn[1] if conn else 'no guest'} / {start[1] if start else 'no replay start'}; engine: "
                             f"{pb.show(relay, 1)}")
    if not ok:
        led.unreached(ids, "the instrument never started (T2-PEER)")
        return
    ctx.anchors["start"] = start[0]
    _tape_run(g, led, ctx, arc=arc)


def _tape_run(g, led: cb.Ledger, ctx, arc: bool = False) -> None:
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
    led.check("S136A-I" if arc else "S136T-I", not missing, f"missing {missing}" if missing else
              "paired, ARMED, BOOT, LIVE logged")
    g.note(f"{'arc' if arc else 'tape'} leg at {_dt.datetime.now():%H:%M:%S}: {len(ctx.samples)} sample(s)")
    (judge_fallback_arc if arc else judge_fallback_tape)(led, ctx.samples, [m for _t, _l, m in e], ctx.act,
                                                         getattr(ctx, "oracle", None), getattr(ctx, "oracle_why", ""))
