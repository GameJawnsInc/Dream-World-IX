# Battle co-op round 3, group 2: build log (s133-s141)

Group 2 is the design's action replay plus the guest's own field model (`R3-DESIGN.md` sections 3.3 and 3.4). The owner
renumbered it on 2026-10-15 from s122-s130 to **s133-s141**, because s131 and s132 were captured first and the patch
stack replays by number:

| Patch | Was | What it does | Status |
|---|---|---|---|
| s133 | s122 | host action-start lane (START/END records, impact ids, header bit 5) | ★ deployed, solo-proven |
| s134 | s123 | guest action replay | ★ deployed, solo-proven (solo + T2 tape leg) |
| s135 | s124 | numbers, flinch and death wait for the replay's hit | next |
| s136 | s125 | fallback A: one stock clip per uncovered action | |
| s137 | s126 | trance burst timing | |
| s138-s141 | s127-s130 | the guest's own field model (shows its party character, or a moogle) | after action replay |

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
