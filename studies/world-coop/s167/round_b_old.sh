#!/usr/bin/env bash
# s167 ROUND B -- OLD, measured on the DEPLOYED s166 (b24e0123ac93960c), BEFORE the s167 build (the design's Order: OLD first).
# Every round-B row's OLD prediction, one leg per launch, COOP_CALIBRATE=1: each leg reads the STAGE off the probe (`netsync.world.walk` /
# `netsync.world.fp` / `netsync.world.walk.map`), so an s166 engine is sent NO round-B op (the session refuses them before the step) and
# every row MEASURES s166's shape (frozen 0.00 u, the camera still, silent, once per process, stranded, refused, absent) -- the CAL row of
# each launch (S167-CAL / S167-<LEG>-CAL / S167-D-CAL) is the verdict: exactly the leg's OLD-predicted rows red, each measured.
# S167-WR-GATE is never part of a calibration (the owner-gated ROAM tape: ROAM-TAPE.md "Round B").
#   bash studies/world-coop/s167/round_b_old.sh            (logs: .harness-runs/s167-round-b/<stamp>-old/, summary.log there)
ROUND_B_KIND=old
. "$(dirname "$0")/round_b_lib.sh"
preflight old t2

# 1. the solo rows (coop_world_walk.py round B, the forced selftest role): exactly b_old_predicted per leg (W-OPEN green: its OLD is its NEW)
for l in free refuse stale entry decline tps minimap map; do
  leg "OLD solo $l" solo "old_solo_$l.log" -- env COOP_CALIBRATE=1 COOP_WW_LEG=$l $SOLO s167-b-old-$l -- \
      py tools/play.py $SC/coop_world_walk.py --field 6603
done
# 2. T2: the walk on THE INSTRUMENT (the ROAM tape is owner-gated), the stall hole on a world-paired guest, the s166 host's lines
for l in walk stallhole hostb; do
  leg "OLD T2 $l" t2 "old_t2_$l.log" -- env COOP_CALIBRATE=1 COOP_WWT_LEG=$l py tools/play.py $SC/coop_world_walk_t2.py
done
# 3. the duo: an s166 pair walks nothing (every round-B row but D-SHARED red)
leg "OLD duo b" duo old_duo_b.log -- env COOP_CALIBRATE=1 COOP_WWT_DUO=b $DUO $SC/coop_world_walk_t2.py
say "== all done (OLD). Next: build + deploy s167 (py tools/build_memoria.py, FF9 closed, the owner's go), then round_b_new.sh"
