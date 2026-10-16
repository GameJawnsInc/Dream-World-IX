# Battle co-op round 3, group 2: build log (s133-s141)

Group 2 is the design's action replay plus the guest's own field model (`R3-DESIGN.md` sections 3.3 and 3.4). The owner
renumbered it on 2026-10-15 from s122-s130 to **s133-s141**, because s131 and s132 were captured first and the patch
stack replays by number:

| Patch | Was | What it does | Status |
|---|---|---|---|
| s133 | s122 | host action-start lane (START/END records, impact ids, header bit 5) | ★ deployed, solo-proven |
| s134 | s123 | guest action replay | next |
| s135 | s124 | numbers, flinch and death wait for the replay's hit | |
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
