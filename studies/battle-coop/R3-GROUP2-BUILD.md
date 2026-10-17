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
| s138-s141 | s127-s130 | the guest's own field model (shows its party character, or a moogle) | next |

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
