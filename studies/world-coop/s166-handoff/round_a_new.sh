#!/usr/bin/env bash
# s166 ROUND A -- NEW, on the W1+W2 build, in the design's Order (S166-DESIGN.md "Order"): the proof; A-WIRE and the restamp; A-TX; the
# ghost rows with `lanegap off` + `hostlines off`; the stall rows; T2; the duo -- then the regression set (round_a_regress.sh, W3's).
# One leg per launch; every row green is the verdict (each launch's "checks passed" line in summary.log).
#   bash studies/world-coop/s166-handoff/round_a_new.sh            (ROUND_A_DLL=<sha16> pins the build under test)
# OWNER-GATED, NOT HERE: COOP_TAPE_WORLD_ROAM's recording (ROAM-TAPE.md) -- until it exists the roam / freeze legs run THE INSTRUMENT
# (S166-RM-GATE stays red); the two-PC look (the owner's). D-PAIR is deferred (both duo games start on 6603).
ROUND_A_KIND=new
. "$(dirname "$0")/round_a_lib.sh"
preflight new t2

# 1. THE PROOF: 'world walk selftest: OK (N rows, M mutants)' on a field -- A-PROOF rides the tx leg's launch (A-TX + A-FROZEN with it)
leg "the proof + A-TX" solo new_solo_tx.log -- env COOP_WW_LEG=tx $SOLO s166-a-tx -- py tools/play.py $SC/coop_world_walk.py --field 6603
# 2. A-WIRE (an unrestamped v14 tape never pairs; `--wire 15` clears the words) and THE RESTAMP (T2-A old: every s165 row on a capless host)
leg "A-WIRE" t2 new_wire.log -- env COOP_WWT_LEG=wire py tools/play.py $SC/coop_world_walk_t2.py
leg "T2-A old (the restamp)" t2 new_old.log -- env COOP_WWT_LEG=old py tools/play.py $SC/coop_world_walk_t2.py
# 3. the ghost rows -- each leg pulls `lanegap off` + `hostlines off` itself and reads them back (its instrument)
for l in ghost wrap dot body; do
  leg "solo $l (quiet lines)" solo "new_solo_$l.log" -- env COOP_WW_LEG=$l $SOLO s166-a-$l -- py tools/play.py $SC/coop_world_walk.py --field 6603
done
# 4. the stall rows (the lines on: they judge them)
leg "solo stall" solo new_solo_stall.log -- env COOP_WW_LEG=stall $SOLO s166-a-stall -- py tools/play.py $SC/coop_world_walk.py --field 6603
# 5. T2: roam (the ROAM tape, else THE INSTRUMENT), freeze, the host
leg "T2-A roam" t2 new_roam.log -- env COOP_WWT_LEG=roam py tools/play.py $SC/coop_world_walk_t2.py
leg "T2-A freeze" t2 new_freeze.log -- env COOP_WWT_LEG=freeze py tools/play.py $SC/coop_world_walk_t2.py
leg "T2-H" t2 new_host.log -- env COOP_WWT_LEG=host py tools/play.py $SC/coop_world_walk_t2.py
# 6. the duo: round A's, then the s144 / s145 duo rows UNDER AN ACTIVE TRAILER (both games s166: D-TRAILER witnesses it)
leg "duo (round A)" duo new_duo.log -- py tools/harness/duo.py $SC/coop_world_walk_t2.py
leg "duo s144 (trailer active)" duo new_duo_s144.log -- py tools/harness/duo.py $SC/coop_world_wait.py
leg "duo s145 (trailer active)" duo new_duo_s145.log -- py tools/harness/duo.py $SC/coop_world_battle.py
say "== all done (NEW). Next: round_a_lever.sh (each lever alone), then round_a_regress.sh (W3), then the owner's two-PC look"
