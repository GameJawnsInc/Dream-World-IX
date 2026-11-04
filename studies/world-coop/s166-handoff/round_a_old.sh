#!/usr/bin/env bash
# s166 ROUND A -- OLD, measured on the DEPLOYED A0b (9e4365349fab02b1), BEFORE the W1+W2 build (the design's Order: OLD first).
# Every round-A row's OLD prediction, one leg per launch, COOP_CALIBRATE=1: an engine without a row's key gets NO A3/A4 op (the benches
# probe first) and reds exactly the leg's *_OLD_PREDICTED -- the CAL row of each launch is the verdict.
#   bash studies/world-coop/s166-handoff/round_a_old.sh            (logs: .harness-runs/s166-round-a/<stamp>-old/, summary.log there)
ROUND_A_KIND=old
. "$(dirname "$0")/round_a_lib.sh"
preflight old t2

# 1. the solo rows (coop_world_walk.py round A, the forced selftest role): exactly a_old_predicted per leg (A-FROZEN green)
for l in tx ghost wrap dot body stall; do
  leg "OLD solo $l" solo "old_solo_$l.log" -- env COOP_CALIBRATE=1 COOP_WW_LEG=$l $SOLO s166-a-old-$l -- \
      py tools/play.py $SC/coop_world_walk.py --field 6603
done
# 2. A-WIRE: a v14 guest pairs with the v14 tape (`--wire tape` = its own wire): NOPAIR / REJECT / CLEAR red (WIRE_OLD_PREDICTED)
leg "OLD A-WIRE" t2 old_wire.log -- env COOP_CALIBRATE=1 COOP_WWT_LEG=wire py tools/play.py $SC/coop_world_walk_t2.py
# 3. T2-A old: GREEN on v14 (s165's walk rows + S166-OLD-WIRE 'as recorded' + S166-OLD-DORMANT dormant by construction)
leg "OLD T2-A old (green on v14)" t2 old_old.log -- env COOP_WWT_LEG=old py tools/play.py $SC/coop_world_walk_t2.py
# 4. roam / freeze: the v15 ROAM tape (or THE INSTRUMENT) is never restamped down -- T2-PEER red, every row unreached
leg "OLD T2-A roam" t2 old_roam.log -- env COOP_CALIBRATE=1 COOP_WWT_LEG=roam py tools/play.py $SC/coop_world_walk_t2.py
leg "OLD T2-A freeze" t2 old_freeze.log -- env COOP_CALIBRATE=1 COOP_WWT_LEG=freeze py tools/play.py $SC/coop_world_walk_t2.py
# 5. T2-H: an A0b host shows nothing (every TH row 'absent')
leg "OLD T2-H" t2 old_host.log -- env COOP_CALIBRATE=1 COOP_WWT_LEG=host py tools/play.py $SC/coop_world_walk_t2.py
# 6. the duo: an A0b pair draws nothing (every D row but D-SHARED red)
leg "OLD duo" duo old_duo.log -- env COOP_CALIBRATE=1 $DUO $SC/coop_world_walk_t2.py
say "== all done (OLD). Next: build + deploy W1+W2 (the owner's go), then round_a_new.sh"
