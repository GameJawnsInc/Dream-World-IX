# Battle co-op round 3, group 2: build log (s133-s141)

Group 2 is the design's action replay plus the guest's own field model (`R3-DESIGN.md` sections 3.3 and 3.4). The owner
renumbered it on 2026-10-15 from s122-s130 to **s133-s141**, because s131 and s132 were captured first and the patch
stack replays by number:

| Patch | Was | What it does | Status |
|---|---|---|---|
| s133 | s122 | host action-start lane (START/END records, impact ids, header bit 5) | ★ deployed, solo-proven |
| s134 | s123 | guest action replay | ★ deployed, solo-proven (solo + T2 tape leg) |
| s135 | s124 | numbers, flinch and death wait for the replay's hit | ★ deployed, solo-proven, owner-confirmed |
| s136 | s125 | fallback A: one stock clip per uncovered action | ★ deployed, solo-proven (solo + tape + arc legs) |
| s137 | s126 | trance burst timing | ★ deployed, solo-proven |
| s138 | s127 | the dress instrument (keys only) | ★ deployed, solo-proven |
| s139 | s128 | the host's dress rule + wire section 8 | ★ deployed, solo-proven + real-wire duo |
| s140 | s129 | the guest dresses itself (+ rig rows 9-12 for CharacterId 8-11) | ★ deployed, solo-proven + real-wire duo |
| s141 | s130 | polish: footsteps, held props, the mesh-op drop, lighting | ★ deployed, solo-proven + real-wire duo |

Order (owner decision): action replay first, then the field model. Before any building, a 7-lane audit checked the design
against the live s132 stack (`R3-ACTION-REPLAY-AUDIT.md`, which keeps the OLD patch names). Each round is one DLL build,
one calibrated solo bench and one patch; README rows in `memoria-patches/README.md` are authoritative.

## s133: the host action-start lane (2026-10-15)

**Built** by a workflow: an engine agent, a harness agent, a 3-lens review (engine safety, wire compatibility,
harness/test laws) with two skeptics per finding, then a fix agent. 19 review findings were fixed. The patch: 8 files, 36
hunks, +1784/-38. Every capture gate passed and the stack replays 22/22 byte-exact (the `diag` set gained btl_cmd.cs,
btlseq.cs and btl_vfx.cs).

**Calibrated** on the deployed s132 first: `coop_action_host` under `COOP_CALIBRATE=1` went red in exactly the predicted
16 of 20 checks (the `act.host` probe absent, everything after it fails closed).

**Deployed** 2026-10-15 (`build_memoria.py`, backup `20261015-203420`; Assembly-CSharp `69bfa8b6f2c93edb`).

**Proven solo on s133:**
- `coop_action_host` 20/20 on scene 306 group 4 (Fang x2), and RED-only under `COOP_CALIBRATE=1` (the `hoststarts off`
  lever: exactly ON, AT, EN, MT, POT, VFX, PAIR, TAPE, ORDER). 'action lane selftest: OK (30 rows)' in game.
- The 6.1 regression set at baseline: start hold 24/24, handback live 18/18, intro mirror 18/18, Wait parity 12/12, flee
  and defeat 53/53, host gates 20/20, containment 23/23, stock menu 27/27, content 35/35, live 40/40, end host 23/23, end
  guest 49/49, result replay 50/51 (S9-C4L, unreachable solo, as on every engine since s109), handback 21/21, diorama
  return 22/22, talk relay 28/28, dialogue authority 147/147 (one R-B7 flake in the block run -- the vanilla story page
  never opened; it passed on a solo rerun).
- The T2 cut legs on the owner's untouched ini: cal 10/10, readopt 13/13 (hold - outage = +62 ms against tail 67.3),
  s119 12/12 (+0 against 0.0), s120-battle 12/12 (+62 against 67.3), span 9/9.

**The bench needed two fixes in game.** Scene 306's two Fangs (136 HP) died before Zidane's second turn twice: first to
his own attacks plus Vivi's two spells, then to Vivi's many-target spell alone. The plan now has Zidane attack the
sturdiest standing ALLY (an Attack's START does not depend on its target) and casts Vivi's many-target spell LAST, after
both attacks and Garnet's Potion, while both enemies still stand. Lesson for s134-s137's benches: a check that needs N
turns must order the plan so nothing that can end the fight runs before them.

**Known, not chased:** single `SmoothFrameUpdater_Battle.Apply` NREs at diorama ends (stock, predates s111; audit 3.6).

## s134: the guest action replay (2026-10-16)

**What it does.** On a booted diorama whose host latched header bit 5, each s133 START becomes a standalone CMD_DATA run
through the stock SFXRework sequencer as a replay: the guest finally sees attacks, casts, items and enemy actions.
Containment holds by construction: a replay never enters the command queue, and the first statement of
`btl_cmd.ExecVfxCommand` returns for a registered replay, so no damage or state write runs; a tripwire counts any calc
while booted. New file `NetSyncDiorama.Replay.cs`; `[Netsync] ActionReplay` (default 1).

**Built** by a workflow: engine, harness, a 4-lens review (containment, stock-code safety, timing/holds/ends, harness)
with two skeptics per finding, a fix pass, a re-review, a second fix pass. The one blocking finding: an abort never
cancelled the replay's pending SFX loads. 14 files, 60 hunks, +3110/-22; 'action replay selftest: OK (34 rows)'.

**Calibrated on s133 first.** A new host tape was recorded on the s133 host
(`.harness-runs/coop-tapes/act-s133/20261016-011813-host250-s131.f9tape`: 13 STARTs, 13 ENDs, 13 tagged impacts) and
its instrument CAL passed 10/10. Both bench legs went red exactly as predicted on s133 (S134T-CAL, S134-CAL).

**Deployed** 2026-10-16 (backup `20261016-012837`; Assembly-CSharp `c93a249cbb8e596c`).

**Proven solo on s134:**
- The T2 TAPE LEG 16/16: the recorded s133 host replayed into the desktop as a guest through the real transport --
  replays started, units acted, hits paired, everything ended, 0 faults, the tripwire 0. RED-only under ActionReplay=0.
- The solo leg 35/35 and RED-only under `replay off` (S134-CAL: exactly the lever set).
- The 6.1 regression set at baseline (coop_action_host 20/20 included; dialogue authority 147/147; result replay 50/51,
  S9-C4L unreachable solo) and the T2 cut legs (readopt +94 vs tail 67.3, s119 +0, s120-battle +93).

**The solo bench needed two debug rounds in game.** First run 17/35. The root causes (two bench bugs, and the engine
defect one of them exposed):
- In a selftest diorama the selftest party mirror seats an impostor named "BENCH" (Freya's model, Lv 99) in Zidane's
  slot, so every lookup of Zidane by name failed. The bench now takes the unit at Zidane's battle-1 wire only when it is
  that stand-in; Leg M's timing comparison is therefore cross-model, and says so.
- The smoke leg D0 sent `dioleave` as its own request, which landed just after the swirl's fade -- where the engine
  accepts a Leave. It is now batched into the boot's request (Block(2) frames later, inside the fade), judged only on a
  fresh BOOT line with two witnesses of the deferral.
- That accepted Leave exposed a real ENGINE defect, pre-existing since B3.6 and on the selftest/harness path only: a
  selftest Leave accepted in SwirlScene's not-fading window strands the diorama, because the watcher's fence 1 (the only
  other ForceDisarm caller) runs only on the transport path. Every later boot was refused, autosaves were gated off, and
  the harness `reset` held the selftest role -- which is why the levers never released (S134-R). Not an s134
  regression. **Queued as its own engine fix after group 2** (move fence 1 and fence 2's SwirlScene watchdog into a
  static tick called from both the transport and the selftest branches).
- An adversarial review of those fixes found a latent false green in D0 and test conjuncts that could not fail; both
  fixed (four mutants now each turn the D0 test red).

**★ OWNER-CONFIRMED in a two-window duo on the desktop (2026-10-16):** a host instance fought scripted battles
(Steiner's and Zidane's attacks, Garnet's Cure, Vivi's Fire) and the paired guest instance replayed them -- "both
windows had battle animations". The guest seated the host's real party (not the selftest stand-in). The laptop
still needs a package carrying s133-s134 for a two-machine look.

**Known v1 gaps (risk 8):** a Change replay toggles the row (no absolute row on the wire); Defend's pose is not
mirrored; reflect bounces use the guest's statuses; numbers, flinch and death still land at impact ARRIVAL (s135).

## s135: numbers, flinch and death wait for the replay's hit (2026-10-16)

**What it does.** On a booted diorama, an impact that names a running or pending replay's START is HELD. Its HP/MP bars
still follow the host at arrival (the owner's rule), but the number, the flinch and any kill or revive wait for the
replay's own hit (EffectPoint; the figure shows at the sequence's Figure point). Fallback releases: `late` (the hit came
first), `end`, `hostdone` (the host's END + 1500 ms), `timeout` (2.5 s of battle time), `abort`, `replaced`, `declined`,
and `end-inject`, which flushes every held kill BEFORE AllPlayersDown is read (audit amendment 2). Frames behind a held
life change queue on that slot. A per-slot LIFE MASK makes the reconciler skip a held slot's record, so a sample cannot
kill or revive ahead of the hit; the skipped record is re-applied on release and at the end-inject flush. Keys
`netsync.battle.act.guest.hold{...}` (counters, the life mask, the real-link lag key, figs[16]).

**Built** by a workflow: engine, harness, a 4-lens review (life/death, stock-code safety, timing, harness) with two
skeptics per finding, a fix pass (20 findings: among them a queued frame that could stand a corpse up, the end-inject
flush missing the skipped samples, a queue drain inside EffectPoint's bracket, a hit's number lost on an abort), a
re-review and a second fix pass (the timer legs judged on the engine's release line, not a figure the summon can hide;
a stand-in that could never fail the flush-before-AllPlayersDown order). 5 files, 36 hunks, +1744/-25; 'action hold
selftest: OK (28 rows)'; the stack replays 29/29 byte-exact; 762 domain tests pass.

**Calibrated on s134 first** (the live DLL `c93a249cbb8e596c`): the tape leg on the recorded s133 host tape went red in
exactly every hold check (S135T-CAL green, no unpredicted reds), and the solo bench under `COOP_CALIBRATE=1` went red in
exactly the probe-absent set, 22 of 28 (S135-CAL green). The owner's ini came back byte-exact (`efaebbf47c36e752`).

**The amendment-14 freeze, as built** (the one exception to "the bars follow the host"): a slot is in the life mask for
its own held kill or revive, and for any frame held or queued behind an older life change or queued frame on that slot,
so a living unit can be masked too. While masked, the reconciler skips that unit's whole record (current and max HP/MP,
hide, trance, ATB). Each change waits at most 2.5 s of battle time from its own arrival; overlapping frames chain the
wait. On release the last skipped record is re-applied at once.

**Deployed** 2026-10-16 (`build_memoria.py`, backup `20261016-131006`; Assembly-CSharp `8258b7bb3ae0f606`).

**Proven solo on s135:**
- The T2 TAPE LEG 12/12: the recorded s133 host replayed into the desktop as a guest through the real transport --
  impacts held for their replay's hit, every one released by exactly one reason, figures released by the hit, the
  real-link lag key populated. RED-only under ActionReplay=0 (S135T-CAL: exactly HELD, LAG, FIG, LOG).
- The solo bench 27/27 on its first in-game run (seven diorama boots, no debug round needed), and RED-only under
  `hold off` (S135-CAL: exactly the 18-check lever set). 'action hold selftest: OK (28 rows)' in game.
- The 6.1 regression set at baseline, incl. coop_action_replay 35/35 and its tape leg 16/16, coop_action_host 20/20,
  dialogue authority 147/147 and result replay 50/51 (S9-C4L, unreachable solo). The T2 cut legs: cal 10/10, readopt
  13/13 (+63 vs tail 67.3), s119 12/12 (+15 vs 0.0), s120-battle 12/12 (+63 vs 67.3), span 9/9.

**Two first-run flakes, both green on a rerun (neither touches s135's code):**
- s134's Leg M compares the guest's launch -> hit (859-906 ms over five runs) with the HOST's START -> impact for
  Zidane's Attack on battle 1, read off the in-engine tape. That reference read 2063 ms once, against 813-1156 on every
  other run; battle 1 is a normal fight where s135's only sequencer hook is a static `ActLive` read (false). A single
  host sample is a noisy yardstick -- if it flakes again, judge against a median of the taped attacks.
- Stock menu S3-L3: the command root opened with its cursor on Jump instead of Attack, so the walk to Item missed it.
  The rerun opened on Attack.

**Known v1 (README row):** the amendment-14 freeze above; a lost lethal impact is not protected (S135-LOST); anything
still held when the end injects lands at once. Not proven in game: a triple's caster figure, the hidden-target guard, a
held revive's freeze, WhiteDraw/DragonBreath extra CalcResults, slave-part keys.

**★ OWNER-CONFIRMED in a two-window duo on the desktop (2026-10-16):** the same demo as s134's, with the guest's
`act.guest.hold` block printed after each fight -- "looks good". The guest's log for fight 1 (Fang x2, 10 actions): 10
impacts held; both of Garnet's Cures released at the replay's hit (375 ms and 1547 ms after their numbers arrived), the
8 physical attacks released `late` -- the guest's replayed swing landed 15-375 ms (median 297) BEFORE the host's impact
arrived, so those numbers show on arrival, just after the swing. The tape leg showed the same shape (8 of 12 late,
median -234 ms). **Candidate follow-up (after group 2, with s142):** find where the host's ~300 ms goes between its own
hit and the impact frame reaching the guest on a local link (its send point or cadence), or bound-wait the replay's
EffectPoint for its paired impact so every number lands exactly on the swing.

## s136: fallback A, one stock clip per uncovered action (2026-10-16)

**What it does.** On the guest's diorama, an impact that no replay covers (an old host, a START declined, dropped or
never received, ActionReplay=0, no SFXRework) used to get only the s110 player MP_ATTACK swing. It now plays one stock
clip per action: Item/Throw MP_ITEM1, magic MP_MAGIC, Defend/Change none, other commands MP_ATTACK, and an enemy the
first non-Idle caster PlayAnimation of its scene sequence (parsed, never executed, cached per (scene, sub); the Loop
moves and scripted sequences included). Once per action, keyed (nonce, actId), or for an old host (caster, cmd, sub)
inside a 500 ms battle-time window that slides with each sibling. An impact whose START is still pending waits for its
decision; one whose caster is still acting in a replay waits for it (bounded, 4 s). Keys
`netsync.battle.act.guest.fallback{...}`; `actbench fallback on|off`; 'action fallback selftest: OK (30 rows)'.

**Built** by a workflow (engine, harness, a 4-lens review -- coverage/containment, stock safety, timing/dedupe/ends,
harness -- with two skeptics per finding, a fix pass, a re-review, a second fix pass): 9 surviving findings in round 1
(among them a whole action dropped when its caster was still acting, setMotion on a clip the unit lacks, the busy
window's restore cutting a bystander's clip, the end/leave guard missing a Leave's own abort-all) and 5 in round 2
(a pending START judged covered for good, the enemy Loop moves, the restore's order). 4 files, +1418/-19; the stack
replays 29/29 byte-exact; 862 domain tests pass.

**Calibrated on s135 first** (the live DLL `8258b7bb3ae0f606`): the solo bench under `COOP_CALIBRATE=1` red in exactly
the probe-absent set (21 of 28, S136-CAL green); the T2 tape leg (the s133 host, ActionReplay=0) and the new ARC leg (the
s117 old-host tape through the real intake) each red in exactly every fallback check (S136T-CAL, S136A-CAL green). The
first tape and arc runs were disturbed from outside -- the owner had another game and a controller on: one launch left
the title screen by itself, and one guest sat in the Pause menu through the host's fight (its start-hold report: BUSY)
-- and both were green on a clean rerun. LESSON: the UNATTENDED LAW covers single-instance benches too.

**Deployed** 2026-10-16 (`build_memoria.py`, backup `20261016-193358`; Assembly-CSharp `19ab527daa509b56`).

**Proven solo on s136** (one block, nothing rerun):
- The T2 TAPE LEG 13/13: the s133 host with ActionReplay=0 through the real transport -- every START declined `knob`,
  attack and enemy clips keyed by id, every enemy clip equal to the offline btlseq oracle's, the Defends none. RED-only
  under the inverse knob ActionReplay=1 (S136T-CAL: exactly UNCOV, CLIP, ENEMY, LOG).
- The ARC LEG 12/12: the s117 OLD host's tape (no START, 46-byte impacts) through the real intake -- clips keyed by
  caster inside the 500 ms window, enemy clips equal to the oracle's.
- The solo bench 27/27 on its first in-game run and RED-only under `fallback off` (S136-CAL: exactly the 17-check lever
  set). 'action fallback selftest: OK (30 rows)' in game.
- The 6.1 regression set at baseline, incl. coop_action_hold 27/27 + its tape leg 12/12, coop_action_replay 35/35 + its
  tape leg 16/16, coop_action_host 20/20, stock menu 27/27, dialogue authority 147/147 and result replay 50/51 (S9-C4L).
  The T2 cut legs: cal 10/10, readopt 13/13 (+63 vs tail 67.3), s119 12/12 (+0), s120-battle 12/12 (+78), span 9/9.

**What the owner would see:** nothing new on a normal duo -- an s133+ host's actions are all replayed (covered). Fallback
A shows on mixed DLLs (an old host), a guest on the legacy engine, or a guest with `[Netsync] ActionReplay=0`: one stock
clip per action instead of a full replay, and the enemies move.

## s137: the trance burst timing (2026-10-17)

**What it does.** On a booted diorama whose host latched bit 5 and whose guest can replay, a unit's trance model no
longer swaps the moment the host's sample carries the trance bit. ApplyUnit records the change; ActTick resolves it every
frame on both branches -- at the SysTrans replay's own hit (SetTranceModel with the mirrored bit, only when the worn
model differs), else 400 ms of battle time after nothing names the unit (capped at 2500 ms; a unit's own burst in flight
may hold it up to 8500 ms), at once on a decline of its SysTrans START or at its replay's end, and at the end injection.
Old hosts, a guest that cannot replay and the lever keep the immediate swap. Keys `netsync.battle.act.guest.trance{...}`
and `units[].trance_model`; `actbench trancegrace on|off`; 'action trance selftest: OK (21 rows)'.

**Built** by a workflow (engine, harness, a 4-lens review -- model/containment, stock safety, timing/grace/ends,
harness -- with two skeptics per finding, a fix pass, a re-review, a second fix pass). Round 1's one blocking finding:
an End burst on a dead unit would have swapped the corpse INTO its trance model (the corpse's mirrored bit went stale);
now the dead lane mirrors the host's bit and a corpse waits for its own burst. Others fixed: the burst exemption had no
time bound (now 8500 ms), a victory injection swapped ahead of a burst in flight, a swap inside a mesh-flag hide left
renderers off, and the bench gained a PAUSE leg proving the grace counts battle time. 4 files, +1262/-4; the stack
replays 29/29 byte-exact; 962 domain tests pass. **No tape leg:** no recorded host tape carries a trance, and forcing
one (the Battle Assistance booster plus a fight policy) would be a new, nondeterministic instrument needing its own CAL.

**Calibrated on s136 first** (the live DLL `19ab527daa509b56`): the solo bench under `COOP_CALIBRATE=1`, in both its
lever mode and its caps-0x02 mode, red in exactly the probe-absent set (19 of 25, S137-CAL green both times).

**Deployed** 2026-10-17 (`build_memoria.py`, backup `20261017-015533`; Assembly-CSharp `0269771f24b626c1`).

**Proven solo on s137:**
- coop_action_trance 24/24 (after the bench fixes below) and RED-only under COOP_CALIBRATE in both modes (the
  `trancegrace off` lever and caps 0x02: the same lever set). 'action trance selftest: OK (21 rows)' in game. The
  numbers: the grace 406 ms after the record; a SysTrans hit swapping at its first_hit_ms; a START parked 1.5 s behind
  a running Attack still swapping at its own hit, 6.1 s after the op (past the cap); the busy hold swapping 391 ms after
  the Attack's end (it ran 1343 ms past the record); the cap at 2531 ms with the summon still running; the pause leg
  proving battle time.
- The 6.1 regression set at baseline, incl. the s133-s136 benches and every tape/arc leg (fallback tape 13/13, arc
  12/12, hold tape 12/12, replay tape 16/16), dialogue authority 147/147, result replay 50/51 (S9-C4L). The T2 cut legs:
  cal 10/10, readopt 13/13 (+62 vs tail 67.3), s119 12/12 (+0), s120-battle 12/12 (+94), span 9/9.

**The proof block found three bench-instrument problems (all fixed, the engine right every time):**
- S137-BUSY: the BENCH stand-in's Attack ran 2188 ms past a record taken at its feed, so a correct engine swapped by
  the cap (NOT REACHED). The op now rides its own request 800 ms into the Attack.
- S137-CAP: the summon launched in the op's own frame, whose asset-load hitch put the op's publish 203 ms after the
  record (the witness read 2313 ms for a 2516 ms cap swap). The op now rides its own request 600 ms into the summon.
  An adversarial review of that fix (3 lenses) found the deeper flaw both CAP and GRACE shared: the witness's origin was
  the request's acknowledged state, 31-62 ms behind the record against 34 ms of slack (GRACE had passed by 9 ms). It now
  starts at the first publish showing the record; CAP also reports the frame into the swap and reads NOT REACHED if a
  load hitch straddles the cap.
- S135-L1/L1F (the s135 hold bench): which Fang move battle 1 tapes varies -- sub 3 hits 1437 ms after an impact fed with
  its START, sub 5 2156-2560 ms -- and the slow one outran the hold's 2.5 s timeout. The impact now rides the same
  request `feedat 700`. (The rerun taped sub 3; sub 5's arithmetic: 1456-1860 ms, inside the timeout.)
A rerun on s137 after the fixes: trance 24/24 + both calibrations clean, hold 27/27 + its calibration clean.

**OWNER-RATIFIED:** audit amendment 3 said the grace is "capped at 2500 ms"; as built, a unit's own SysTrans burst in
flight is exempt from that cap, bounded at 8500 ms (the 6 s parked-START limit plus the cap). The owner kept it:
"Keep the burst's cap exemption (up to 8.5 s)".

**Action replay (s133-s137) is complete.** Next in the plan order: the guest's own field model, s138-s141.

## s138: the dress instrument (2026-10-17)

**The pre-build audit first.** The field-model design (3.4) was written before s131-s137, so it was audited against the
live clone, the harness and the install before any hunk: `R3-FIELD-MODEL-AUDIT.md` (four lanes, two skeptics per serious
finding, 48 of 50 survived). It decided the dress keys' home (`netsync.dress`, on the one ladder), rewrote leg I so every
check can fail, and found a stock frame-wait (field 2705) that s140's loco mapping would have broken. Two owner questions
gate s139 (the SelfDress=0 opt-out on the host's ghost; a spectating guest's body).

**What s138 does.** Nothing on any role: harness keys only. `player.*` gains model, anim, geo, anim_geo, eye, uid, sid,
body (the root mesh's texture stem -- what is actually worn), clip, clip_playing, frame_n, anim_frame, meshflags;
`objects[].model`; `netsync.dress` = ghost{model, geo, clip, rig, playing, body} (what the peer's ghost really wears,
recorded at EnsureGhost) + party[4] (from FF9.party, never the selftest mirror's BENCH stand-in).

**Built** by a workflow (engine, harness, a 4-lens review with two skeptics per finding, two fix passes; 11 surviving
findings in round 1, among them a blocking one: leg I's walk check counted render-frame publishes while the player moves
on 30 Hz field ticks). 3 files, +284/-6; the stack replays 29/29 byte-exact; 2062 domain tests pass.

**Calibrated on s137 first** (the live DLL `0269771f24b626c1`): coop_self_dress under `COOP_CALIBRATE=1` red in exactly
I1-I9 (the keys absent), S138-CAL green; the oracle, the precondition and the probe green.

**Deployed** 2026-10-17 (`build_memoria.py`, backup `20261017-104630`; Assembly-CSharp `a8b0fd80ecc4013d`).

**Proven solo on s138:** coop_self_dress leg I 15/15 on its first in-game run, every value against the offline oracle:
model 98, body '98', GEO_MAIN_F0_ZDN, eye -372, sid == uid (10 on 250, 1 on 30801); the run clip 38 mid-move and 200 at
rest, judged per field tick; the selftest ghost wearing exactly the player's model, GEO, clip and body; party [0, 1, 2, 3]
after the COOPPARTY seed; 30801's NPCs model 217. The field/ghost regression set at baseline (talk relay 28/28, dialogue
authority 147/147, diorama return 22/22, handback live 18/18, handback 21/21, end guest 49/49, action replay 35/35 + its
tape 16/16) and the T2 cut legs (cal 10/10, readopt +78, s120-battle +63).

**The s137 trance bench's witness, a third time.** GRACE went red on s138 with the engine's own window right (406 ms):
fix 2 took the witness's origin from the first sample the harness READ showing the deferral -- here the request's
acknowledged state, 62 ms after the record (witness 344 ms). Fix 3 makes the origin a BRACKET: the last publish read before
the deferral and the first read showing it, the record inside it, the swap judged not-late from the bracket's end and
not-early from its start; a bracket wider than 170 ms reads NOT REACHED. Rerun on s138: trance 24/24 (brackets 31 and 16 ms
wide), both calibration modes clean. LESSON: a sampled witness needs a bracket, never one edge.

**Next: s139** (the host rule and wire section 8). Before its hunks, the owner answers the audit's two questions (2.2 D1:
the SelfDress=0 opt-out on the host's ghost; D2: a spectating guest's body).

## s139: the host's dress rule and wire section 8 (2026-10-17)

**The owner's two answers first** (R3-FIELD-MODEL-AUDIT.md 2.2): D1 "yes" -- the host's GhostAs is the one knob, a
guest's SelfDress=0 only switches off its own dressing, no wire change; D2 "moogle. 2 zidanes just looks weird, and the
host will never be a moogle" -- a spectating guest (GuestSlots 0) wears the moogle, overriding the audit's recommendation.

**What it does.** On the host, the guest's ghost: the first occupied named slot's member, or the MOOGLE (new rig row 8)
for an empty slot or a spectator; GhostGuard keeps the dress only on a plain-98 wire body or one already dressed; a rest
mask restores CreateModel's field-mode hides (Garnet one hairstyle). Section 8 `[model u16][charId u8]` rides every host
state frame (+6 B, wire v14, old guests skip it). The client keeps the s138 rule. `netsync selfdress ...` (selftest only;
`rule s138` is the lever); 'dress codec selftest: OK (29 rows)'.

**Built** by a workflow (engine, harness, a 4-lens review with two skeptics per finding, two fix passes). 4 engine
files, +1217/-51; 2196 tests pass. Benches: coop_self_dress leg G; `coop_peer.py dress` (a tape's section 8); a duo leg
coop_dress_wire.py (G9: the host's transport site stepped live through GuestSlots 2 / 4 / 0 -- Vivi, Garnet with one
hairstyle, the moogle -- and the relay tap's section 8 in tape order).

**Calibrated on s138 first** (the live DLL `a8b0fd80ecc4013d`): the solo bench red in exactly leg G's old row (S138-CAL
green, leg I green); `coop_peer.py dress` on the s117 host tape: exit 1, no section 8; the duo G9 under COOP_CALIBRATE:
exactly OLD_PREDICTED red (S139-G9-CAL green) -- among them the one behavioural red an old DLL gives: an s138 host
leaves a spectator's ghost plain Zidane.

**Deployed** 2026-10-17 (`build_memoria.py`, backup `20261017-175116`; Assembly-CSharp `1365959f2efca2e7`).

**Proven on s139 -- every acceptance step:**
1. coop_self_dress legs I+G 31/31 on the first in-game run under GhostAs auto, and RED-only under `selfdress rule s138`
   (exactly the lever set). The ghost: the moogle for an empty named slot, every slot empty, a spectator -- walking and
   running on the moogle's own clips; Vivi for slot 1, Garnet when slot 1 is skipped; a Steiner-led wire body shown as
   Steiner, a plain-98 one dressed, Vivi's break clip raw on an already-dressed body; Garnet with ONE hairstyle.
2. The same bench 31/31 with GhostAs blank.
3. `coop_peer.py dress` on the s117 tape: no section 8 (its red).
4. A fresh s139 host tape: section 8 on all 4897 host state frames, right after section 7 and last, `08 00 01` (Vivi)
   each; the old-guest readers identical with it or stripped, every frame.
5. The duo coop_dress_wire G9 18/18: two real games through the relay, GuestSlots stepped live 2 / 4 / 0 -- the host's
   ghost Vivi, Garnet (one hairstyle), the moogle; the guest's own body plain Zidane throughout; its story and party
   mirrors landed past section 8.
The 6.1 regression set at baseline; wait parity (W-A5b 'not reached': every ATB already full) and stock menu content
(the cursor one row off) green on a rerun. The T2 cut legs: readopt +78, s119 +15, s120-battle +93.

**An owner question before s140** (raised by the build's review): in the disc-1 opening the party is Zidane plus Blank /
Marcus / Cinna, and s139 leaves a named slot holding one of them (CharacterId 8-11) undressed -- so the host sees two
Zidanes, the case D2 called weird. Options: real rig rows for the four (they are playable, so their field rigs exist),
or the moogle for them.

## s140: the guest dresses itself, and the 8-11 rigs (2026-10-18)

**The owner's 8-11 decision first** (2026-10-17, after s139): Blank, Marcus, Cinna and Beatrix (CharacterId 8-11) get "their
own models" instead of s139's undressed result. Folded into s140.

**What it does.** A client (and the selftest role) arms at each field load from the host's section 8, read through the real
reader, and dresses its own SetModel(98) PLAYER entry:
- the player gate first (Zidane NPCs stay 98), then a second dressed control body is refused;
- fields 70 and 3000-3012 are skipped at SetModel;
- the rig is keyed on the BODY (`PosObj.netSelfDress`, carried through the warm return) at every hook.

The laws:
- loco families (a closed NAME table) play the rig's native clip, and B_FRAME answers its native length, so field 2705's
  frame-wait ends on every rig;
- gestures play the rig's idle ALIAS on the source timeline;
- the jump slot plays the alias on the source clip's frame count;
- AttachDress attaches the source EventAnimation list plus the rig's set and stores the mapped loco ids, at SetModel and at
  the warm rebuild.

Rig rows 9-12 come from an install census: Cinna 107, Marcus 109, Blank 5467 (his plain body, not the Pluto Knight's 190),
Beatrix 204. CharToRig / RigToChar sit at every party guard, section 8 carries charId 8-11, and the host's ghost wears them
too. `[Netsync] SelfDress` (default 1) is the guest's local knob (owner D1). The wire is unchanged; the guest only READS
section 8.

**Built** by two workflows:
- a census: rows 9-12, the loco-class table (401 ZDN names), and a B_FRAME census over 650 stock frame-threshold sites, 0
  unreachable on all 13 rigs (`dress-census/`);
- three engine stages (the rigs, the self-dress core and its hooks, then the keys / ops / selftest / capture);
- the harness, then the bench and the bench field;
- then a 5-lens review with two skeptics per finding. 9 + 6 findings survived; all were fixed. Among them: the jump slot's
  native-length landing, every hook's rig read unified through `BodyRig`, witnesses for the warm/cold attach, the source
  list, the teardown law and the N legs, and the 8-11 PARTY path seeded live (COOPSUB 30605).

The patch: 9 files, 40 hunks, +2331/-53 (new NetSyncSelfDress.cs). `diag` 34/34. 2289 domain tests pass.

**Two census corrections to the audit:**
- STAND is a gesture, not a loco family: field 2934's RunAnimation(11187) is a 134-frame stand-up.
- An INACTIVE id remaps B_FRAME only when the rig has a break clip.

**The owner's call before the deploy** (2026-10-18): in the disc-1 opening a guest puppeting Cinna / Marcus / Blank stands
beside that member's own NPC (field 63 after battle 338: two Cinnas; fields 50-57 the moogle, the slot empty at load). The
owner: **"Accept it"**. The audit's 2.3 amendment 13 ("the opening fields 50-69 are never dressed") no longer holds.

**Calibrated on s139 first** (the live DLL `1365959f2efca2e7`): coop_self_dress under COOP_CALIBRATE=1 failed exactly the 19
s140 rows, each "not reached" (s139 refuses `self`). Legs I / G and the setup rows were green, and so was S138-CAL. The same
held with GhostAs blank.

**Deployed** 2026-10-18 (`build_memoria.py`, backup `20261018-233617`; Assembly-CSharp `2be623db3bb2ecb5`).

**Proven on s140:**
- coop_self_dress **52/52** on its first in-game run, including:
  - T3: the 2705 loop ends on all 13 rigs;
  - X3: the ladder on stock ticks (frame_n 8, landing 0.03 s);
  - X2: the alias proof (frame_n 50);
  - W1: Steiner's break clip by name after a warm return;
  - S7 / S8: Blank through the live party (`[0, 1, 2, 10]`) on the guest's body and on the host's ghost;
  - N1-N3: the twin, gate 0, and the late 98+CC entry.
- Each of the six levers failed exactly its LEVER_PREDICTED rows, with S138-CAL green each. Under `law bframe off` the
  loop wedges.
- rule-s138 on I+G was exact. GhostAs blank 40/40.
- A fresh host tape: section 8 on all 4817 frames, old readers identical.
- Block A at baseline, after a wait_parity W-A5b rerun (12/12) and with S9-C4L unreachable solo. The tape legs, and the T2
  cut legs (+78, +15, +94 ms).

**The duo G9, rebuilt for s140: 19/19.** Its first run read 16/18. G9c still asserted s139's invariant ("the guest's own
body stays 98"), but an s140 guest correctly DRESSES ITSELF from the host's section 8. And G9f had PASSED on a stale Vivi
body, because its twin judged the guest's real wire. On an s140 guest the bench now:
- re-loads the guest's field after each live GuestSlots step;
- judges G9c as the section-8 dress: Vivi, then Garnet, then the moogle, from 'host';
- adds G9t, the teardown law on the wire: the live body is unchanged until the re-load, and the host shows it as it is;
- requires G9d-f's wire to BE the phase's dress.

This is the first proof of a CLIENT arming off a real host over a real wire. Stub modes `s140_stale` / `s140_eager` turn
exactly their rows red.

**LESSONS:**
- A later patch can turn an earlier bench's invariant into a stage fact. Re-run every earlier duo leg on each new patch,
  and key its expectations by the GUEST's stage.
- A twin that judges the actual wire can pass a stale body. Pin the phase's intended dress as well.
- A census can overturn an audit literal (STAND, the jump windows); trust the bytes.

**Next: s141** (polish, audit 2.4). It owes:
- Cinna walks silently (no stock footstep registration);
- Cinna's and Marcus's hand bones come from the heuristic (read the rig table, not labels_for);
- the bench flag bits 13200-13218 sit in the campaign lane;
- `objects[].body` was deferred.

## s141: the dress polish (2026-10-19)

**What it does.** The guest's self-dressed body (s140) now steps, holds props and is lit like the member it wears. Every
hook is gated on the BODY (`netSelfDress` / `netDressSrc`) first, so host, solo and vanilla behaviour does not change.
- **Footsteps (MapFootstep, at CHRFX).** Codes 16-19 on Zidane's walk 25 {4, 13} / run 38 {0, 8} keys move to the worn
  rig's walk / run clip at the same-ordinal footfall frame, read from the rig table. Steiner puts 925 on codes 16 and 17
  (D4). The moogle, Quina and Cinna DROP all four codes. Any other anim or frame passes through unmapped.
- **The empty-table guard.** A code 19 headed for an EMPTY table is dropped. Stock DeleteChar would index
  `charSoundArray[-1]` and throw inside the VM. Field 2930 reaches this case on a drop rig: its player Init runs 19s on
  190 / 203 right after the 16-18 the rig dropped.
- **Witnesses.** `steps` is the engine's own FF9Snd table for the controlled uid. `steps_fired` / `steps_fired_player` are
  counted in FF9Snd's match branch. Every counter is per field load, reset beside the stock table reset
  (HonoluluFieldMain), so a warm return reads one load.
- **Held props (D3).** A dressed carrier's bone 12 / 13 maps to the rig's R_hand / R_hand_end before geoAttach.
  `attach_last.parent` is the carried object's LIVE transform parent.
- **The mesh-op drop.** MESHSHOW / MESHHIDE on a dressed body are dropped. This defends kit content only: stock never
  mesh-ops a player body (0 of 817).
- **Lighting (D6).** fldmcf falls back to the source (98) row before the default row. The guest-side ghost's stand-in row
  goes through the same pure core. Witnesses: `light_row`, `light_rgb` (read off the BODY's renderer, never a held prop)
  and `light_floor`, plus `ghost.light_row` / `ghost.light_rgb`.
- **The lever (D7).** `selfdress polish on|off` is selftest only. Off bypasses all five paths; the witnesses keep reading.
- **The proof line:** "dress polish selftest: OK (20 rows)".

**Decisions taken here.**
- **Cinna walks silently.** No Cinna body (107, 661) carries a stock footstep registration in any of the 817 scripts, so
  she gets the moogle's and Quina's rule: her 16-19 are dropped. Inventing footfall frames would break verbatim-first. A
  later census row can change it without code. Bench row F2c pins it.
- **Not built:** amendment 7's twin ladder / jump clips (s140's jump slot keeps stock ticks on the idle alias), and the
  shadow size on the 98 fallback (field 250 calls DisableShadow every frame, and kit fields have no MCF, so no bench could
  see it).

**Built** by two workflows. The build workflow had six stages:
- the leg-F census (`dress-census/polish_census.py` -> `polish.json`);
- the bench field's F5 conductors;
- two engine stages (the hooks, then the keys, the lever, the selftest and the capture);
- the harness (rung `dresspolish`);
- leg F.

The review workflow used five lenses with two skeptics per finding. Round 1 had 30 findings; all 14 serious ones were
upheld and fixed, along with the cheap nits. The re-review had 16 findings; 5 of its 6 serious ones were upheld and fixed.
Among the fixes:
- **Steiner's and Amarant's hand bones, s139 rows corrected.** s139's rows had both one bone toward the shoulder (Steiner
  14 / 15, Amarant 15 / 16): a labels_for read, which every check also used, so none could fail on it. They are re-derived
  from the skin and cross-checked against stock's own AttachObject. Stock puts the prop it gives Zidane at bone 13 on
  Steiner's bone 16, 8 of 8 times. Steiner is now 15 / 16 and Amarant 16 / 16, a leaf hand.
- `light_rgb` read a held prop's renderer once a prop sat on the hand. It now reads the body's mesh0.
- F2's "no code-19 fault" could not fail on field 250, which runs no code 19. New bench row F2d replays field 2930's
  `RunModelCode(19, 190, 4, 0)` on the dressed moogle with an empty table.
- F4's floor came from the kit's walkmesh. The engine now publishes `light_floor`, the floor it lit the body by.
- The tests that pin the C# rules to their Python twins were subset checks. They now freeze every s141 member statement
  by statement.

The patch: 8 files, 24 hunks, +1524/-13. `diag` reads 37 of 37 (DEFAULT_FILES gained fldmcf.cs, FF9Snd.cs and
HonoluluFieldMain.cs). A forced recompile gives 0 errors and the 186 baseline warnings. 2392 domain tests pass.

**Audit numbers that did not reproduce** (the verdicts did):
- Freya's footfall frames sit in 40 and 40 fields, not "54 and 44".
- The per-rig sound-reuse counts differ by scope, and no one scope matches all six of the audit's.
- The audit's "F3 green on s140" assumed a key s140 never publishes: there, F3 reads red like every other F row.

**Calibrated on s140 first** (the live DLL `2be623db3bb2ecb5`, after re-seating 30606). coop_self_dress under
COOP_CALIBRATE=1 failed exactly the 13 leg-F rows (FP, F1, F1b, F2, F2c, F2d, F3, F4, F4g, F5, F6, F7, F8), each a judged
red. Every other leg was green, and S138-CAL was green under GhostAs auto and blank. On s140, F5's HideObject really hides
(meshflags 2), and F2d's 19 is stock's no-op on a table still holding Zidane's records.

**Deployed** 2026-10-19 (`build_memoria.py`, backup `20261019-141201`; Assembly-CSharp `0293cb46ffa176f6`).

**Proven on s141:**
- **coop_self_dress 65/65** on its first in-game run. Every leg-F value equals the offline oracle:
  - Freya's four keys;
  - 12 fires in an 86-tick walk;
  - a warm return reading 12 before the boot, 0 at the return, then +12;
  - the moogle and Cinna each dropping 12 with no fault;
  - F2d's guard firing once;
  - Steiner's keys at 925;
  - the body and the ghost on row 98 at (56, 72, 88) on floor 2;
  - the cup on `bone016`;
  - a mesh hide dropped.
- **The polish-off lever** turned exactly its 11 rows red (F1, F1b, F2, F2c, F2d, F4, F4g, F5, F6, F7, F8), with F3 and FP
  green. Each red was behavioural: Zidane's keys on Freya, the default row (104, 104, 96), the cup on `bone013`.
- **The six s140 levers and rule-s138** were each exact, with S138-CAL green on every run.
- GhostAs blank: 54/54.
- **The duo G9: 19/19**, a real host and an s141 guest over the relay.
- A fresh host tape: section 8 on all 4815 frames (`08 00 01`), and the old readers identical with or without it.
- Block A at baseline: trance 24/24, fallback 27/27, hold 27/27, replay 35/35, act host 20/20, start hold 24/24,
  handback live 18/18, intro mirror 18/18, flee/defeat 53/53, host gates 20/20, containment 23/23, stock menu 27/27,
  stock menu live 40/40, end host 23/23, end guest 49/49, handback 21/21, diorama return 22/22, talk relay 28/28,
  dialogue authority 147/147; result replay 50/51 (S9-C4L, unreachable solo); wait parity 12/12 and stock menu content
  35/35 on a rerun (first runs: W-A5b moved after 0.52 s; S7-E2's cursor never reached Fire -- both known flakes).
- The tape legs (replay 16/16, hold 12/12) and the T2 cut legs (cal 10/10; readopt +62, s119 +0, s120-battle +78 ms).

**KNOWN:**
- Footstep keys on Zidane's VARIANT walk / run ids (COLD_ / SWORD_ / POT_ / MBG_ / TKE_ / FRA_WALK, 190 / 203) pass
  unmapped and never fire. Those fields also register the plain 25 / 38 keys, which do fire, so the dressed body steps on
  62-64 and even on 2705's FRA_WALK, where stock Zidane is silent.
- A held prop keeps Zidane's bone-local offset and an identity rotation, so it can sit turned in the rig's hand (about
  90 degrees on Freya, Amarant and the moogle; about 174 degrees on Cinna's bone 12). Cosmetic.
- A kit's whole-body HideObject is dropped along with every other mesh op on a dressed body.
- `steps` publishes only code 16's sound slot. Steiner's slot 1 (925) is proven by the proof's foot row, not in game.

**The duo G9 polish rows (after the deploy): 22/22.** `coop_dress_wire.py` gains G9s / G9w / G9l, run on an s141+ GUEST
only (keyed by the guest's stage: an s140 guest publishes none of these keys). At each phase, on a fresh load at entrance 0,
the guest's own body was judged against the census twin's replay of field 250's ops:
- G9s, the footstep table: Vivi 571@4/14 + 419@0/9 and Garnet 2086@4/15 + 2091@0/9 (919 each), the moogle [] with 12
  dropped.
- G9w, a harness walk on the guest: +12 fires for Vivi and for Garnet over ~86 ticks, the moogle silent (+0 / +0).
- G9l, the light: row 98 at (56, 72, 88) on floor 2 for all three.
The first phase re-loads in the SAME dress, so `attach_cold` growing witnesses that load. Stub modes `s141_unmapped`,
`s141_fired_lost`, `s141_light_default` and `s141_no_echo` turn exactly their rows red. The ghosts' lighting is not judged
on the wire: both ghosts land on a 98 row that s140 gives too.

**LESSONS:**
- A table every check reads from cannot be checked by those checks. Steiner's hand pair was wrong since s139, and the
  census, the selftest and F8 all agreed with it. Only a second source (the skin, plus stock's own AttachObject on that
  body) found it.
- A first-renderer read finds whatever is parented first. Witness the body by name (mesh0), never by order.

**Next: s142** (the selftest Leave-mid-swirl strand fix, queued since s134).

## s143: the guest never commands the host's leader (2026-10-19)

**The report.** The owner, at Plant Brain: "due to Blank being added mid-fight, the host lost control of Zidane". The
read-only diagnosis (two skeptics could not refute it): Blank's appear moves nothing. [Netsync] GuestSlots is a party
POSITION mask, and every battle lane reads its bit n as btl_data index n. Field 257 rebuilds the party [Blank, Zidane,
Vivi, Steiner] right before Battle(1, 303), so GuestSlots 2 handed the guest ZIDANE for the whole fight. Field 261 then
leaves [Garnet, Zidane, Vivi, Steiner] for the stretch after the forest; Pandemonium's Amdusias, Abadon and Shell Dragon
seat the leader the same way.

**The owner's decision.** Positions stay ("by character seems a bit weird since the lineup changes a lot"), but the guest
never gets the character the host walks as: a bit that lands on the host's LEADER moves to the next occupied position
after it (wrapping) that is neither the leader nor already owned; none -> it drops. A battle-start line on both screens.
Other edge cases come from the owner's playtests.

**What it does (the engine half: `memoria-patches/README.md`'s s143 row).**
- ONE PURE RULE (`NetSyncBattle.LeaderGuard`) read by every host ownership lane in battle (`EffectiveGuestSlots`) and by
  the host's field dress sites (`FieldGuardMask`, over the RAW party slots, `auto` only). The guest needs no change: it
  reads the header byte, which now carries the guarded mask.
- THE LEADER: this machine's own controlled field body, off its genuine model (the rig table, or the census's
  playable-character variants: Zidane 532 / 203 / 432, Steiner 658, Garnet 202 / 419 -- `dress-census/leader_census.py`).
  A body that names no character (a chocobo, the gargant, an NPC puppet) KEEPS the last character; the world map latches
  its walker (Zidane's party, or Dagger's status 2); the title forgets the latch. Only "nothing seen since the title" is
  no leader, the positional rule.
- THE LINE: "Partner: Vivi (not Zidane)" on the host's stock battle message window, "You: Vivi" on a live diorama.
- Lever: `netsync bench leaderguard on|off` (selftest role only).

**The repo half.**
- Harness: rung `leaderguard` (`NETSYNC_S143_CAPS`, calibrated on `caps_through("dresspolish")`), `State.coop_leader_guard`
  and the `coop_guard_*` / `coop_peer_guard_*` / `coop_dress_guard_*` accessors, the driver's `bench leaderguard` gate
  (an s141 agent reads it as `bench 1`), `_coop_battle.R3_PROBES[143]`, `coop_peer.py dress --leader`.
- battlewire's twins: LeaderGuard, EffectiveGuestSlots, FieldGuardMask, LeaderForGuard / LeaderGuardOnRule, the leader map,
  GuardCharName and every log line's text; `host_dress_section` and `selftest_dress` take the leader (default none: every
  pre-s143 caller reads as before). The engine's selftest rows are EVALUATED against them, each family failed by a
  mutant twin (tests/test_leader_guard.py, tests/test_coop_leader_guard.py).
- The stand-in models the guard: the field latch, the battle latch over a SEATED party (`battle_seat_party`: InitPlayerData's
  compaction, Plant Brain's hidden Blank and his appear at the head of the list), every lane, the header, the two lines,
  the field site. Nine fault levers (`GUARD_FAULTS`), each pinned to exactly its bench rows.
- The seats: `bench/plantbrain.field.toml` (30607 COOPPBRAIN: RemoveParty x12, then Blank, Zidane, Vivi, Steiner -- field
  257's order, verified on a kit build's disassembled Main_Init), `bench/forestexit.field.toml` (30608 COOPFOREST:
  [Garnet, Zidane, Vivi, Steiner]) and `bench/vivibody.field.toml` (30609 COOPVIVI: no party block, its player the kit's
  Vivi -- the leader-body seat). All three are NEW ids: their first deploy needs a relaunch.

**The bench** (`scenarios/coop_leader_guard.py`, selftest role, GuestSlots 2, every battle from 30602):
- L10, the leader body (30609): the latch reads Vivi off her body (leader 1, leader_model 8); `selfdress wire 98` +
  `ghost 2` moves the bit off HER, so the mirror wears Garnet.
- L7, the negative control on COOPPARTY: nothing moves (field ghost, battle keys, "Partner: Vivi").
- L8, the forest-exit seat, `battle 67 0`: 0x2 -> 0x4, "Partner: Vivi (not Zidane)", the guest's "You: Vivi".
- L0 / L6, the Plant Brain seat: the party [10, 0, 1, 3]; `selfdress ghost 2` wears Vivi (8), not Zidane.
- L1 / L5 / L2 / L9 / L3 / L4, `battle 303 0` (Plant Brain's own script): the keys and the latch line; both lines, the
  host's judged ON SCREEN (`battle.message`); the host's window opens on Zidane and never on Vivi (from the battle's own
  first command phase -- a ring gap reads "not reached"); the loopback roster reads [2] and never holds 1, the G3 hold
  never names 1; a slot-1 `bcmd` refused, a slot-2 one landed (a phase refusal is resent, bounded); Blank's bracketed
  appear leaves the guard unchanged and his window the host's. LAST, left running.
- Calibration: on s141 exactly OLD_PREDICTED (P0, P2, L1-L8; L2 / L3 / L6 behaviourally); on s143 under the lever exactly
  LEVER_PREDICTED (L1, L2, L3, L5, L6, L8, each behaviourally; L0 / L4 / L7 green). Offline the stand-in runs it green,
  both calibrations exact, each fault exact.

**Re-checked benches** (THE PREMISE CENSUS, tests/test_coop_leader_guard.py): every `guestslots` mask a bench sends, over
the party it seats. Neutral (the leader at position 0 is never a guest bit): host gates, handback, handback live, end host
C, start hold, flee/defeat, containment (field and diorama only), coop_self_dress leg G (`ghost 1<<s1` with s1 >= 1, 6, 4,
and G3a's empty slot), coop_dress_wire G9 (2 / 4 / 0), the host tape (2). RE-KEYED by stage: coop_battle_wait_parity and
coop_battle_end_host leg G send `guestslots 15` -- on s143 Zidane's bit would drop and his window open on the host, so
on an engine with `host.guard` they pull `bench leaderguard off` (their premise IS the positional rule) and wait parity's
W-R wants the release line and `off` false on the re-read. The census counts every send route (`try_ns`, `ns_verb`,
`g.netsync`, a raw send) and, since the review, the FIELD levers too (`("ghost", ...)`, `_s_send(... "ghost" ...)`,
`self auto`, G9's phases): a new mask is red until judged, and the dress benches' twins take the engine's leader
(`_coop_battle.guard_leader`: none before s143 or under the lever), so a mask that seats the leader is predicted as the
guard moves it. The `self auto` bench stays UNGUARDED in the engine (it models a pre-s143 host): its masks must be the
guard's no-op over their seats.

**Run recipe** (nothing deployed yet; ask the owner before each step that deploys):
1. `cal143.example.sh` on the live s141 (`0293cb46ffa176f6`): `DEPLOY=yes` deploys 30607 / 30608 / 30609 and STOPs for
   the relaunch; run again: the seats' preflight CLEAN, the bench under COOP_CALIBRATE=1 -> S143-CAL green, then STEP 2's
   seat tape (`COOP_TAPE_SEAT=30607`): `coop_peer.py offer --want 4` and `dress --leader 0` RED on s141, their positional
   twins green.
2. Deploy the s143 DLL (`build_memoria.py`, owner's yes), relaunch, then `S143_DLL=<sha16> full143.example.sh` (STEP 6b:
   the same seat tape on s143 -- the header offers 4 and section 8 names Vivi, the positional twins red).

**The review (2026-10-20; a 5-lens review, two skeptics per finding).** Fixed: the latch now crosses no save (the
title forgets it) and a world-map load latches the walker (a world-map save loads with no field seen: the guest got
Zidane there); a body naming no character keeps the leader (Chocobo's Air Garden walks Chocobo Gold into Ozma -- OWNER'S
NOD PENDING: the design said "none"); Steiner's 658 and Garnet's 202 / 419 are variants too; the guest's line is once per
host battle by nonce AND seq (a >2 s stall re-showed it) and shows LATE once when the diorama comes up after the host's
command phase; the latch keys on the units' slot_no too (an AccessMenus party swap re-latches); FieldGuardMaskCore is the
selftest's subject. The repo half: the guest-side scan sees qualified reads and NetSyncBattle.cs's guest methods, and a
scan across every stack file pins `NetSyncBattle.GuestSlots` reads to the harness key -- each shown able to fail; the
bench's line is judged ON SCREEN, the roster and the hold lanes have witnesses, the leader body varies (30609), the
field-lever census exists, a seat tape puts the header and section 8 on a real wire, the INI gate can fail, the runners
default WT to their own checkout. NOT fixed: `g6_mask` is no ownership witness (G6 withholds whatever the host's window
holds, owned or not -- the review's "g6 bit 1 never set" would be red on a correct engine).

**The second round (2026-10-20, two skeptics per finding).** Fixed: the guest's line latch survived a HOST RELAUNCH -- its
nonce and seq start over, so the new run's battle re-matched the old latch once its climbing seq passed the old one (the
new line never latched, or an old log-only line showed LATE on the new diorama). GuestLineStep now forgets the latch on
an earlier seq of the latched nonce (the battle lane is ordered TCP: only a relaunch runs it backwards) and
NetSyncClient.ResetGuestDedupForEpoch forgets it on a host epoch change; the selftest runs the step over a relaunched and
a resuming host's sequences and a mutant without the forget must fail (44 rows). The tape recorder: the field-250
fallback is back OUTSIDE the seat block (COOPPARTY unregistered left the host on New Game's field), and a seat run fails
closed at REC-SEAT before any ini edit when the seat did not seat its toml's party (a stale seat's `offer --want 4` red
would read exactly like the s141 calibration); a stand-in smoke runs both paths and each was shown to fail on its mutant.

**Known.** The field reads RAW party slots and the battle COMPACTED btl indices (pre-existing): a party hole at or before
a guest bit can still make them name different members. The host's line at priority 1 can be replaced by an enemy's
command title in the same moment, and replace one (it stays in the log and the key; `line_shown` means handed to the
window). A CLIENT's own battles are guarded too while its ghost of the host keeps the s138 rule (cosmetic: that ghost can
wear the client's leader). On the selftest role section 8 always ships the pin (GuestSlots 0): the field guard's
section-8 half is a real host's (the seat tape: `coop_peer.py dress --leader 0` / `offer --want 4`). No solo bench reaches
a world-map battle after a load, nor a real guest's "You:" line (on time or late): the selftest rows, the stand-in and the
owner's two-PC playtest.
