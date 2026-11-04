#!/usr/bin/env bash
# s166 ROUND A -- LEVER, on the W1+W2 build: each calibration lever ALONE (one change per test by lever), in the design's Order.
# COOP_CALIBRATE=1 + the leg + its lever: exactly the leg's LEVER_PREDICTED red, each red row MEASURING its lever's shape -- every
# launch's *-CAL row is the verdict ("no predicted red stayed green, no unpredicted red, every shape measured").
#   bash studies/world-coop/s166-handoff/round_a_lever.sh
ROUND_A_KIND=lever
. "$(dirname "$0")/round_a_lib.sh"
preflight new t2
solo() {   # solo <leg> <lever or ->
  local l="$1" v="$2"
  if [ "$v" = "-" ]; then
    leg "LEVER solo $l (none: every row green)" solo "lever_solo_$l.log" -- env COOP_CALIBRATE=1 COOP_WW_LEG=$l \
        $SOLO s166-a-lever-$l -- py tools/play.py $SC/coop_world_walk.py --field 6603
  else
    leg "LEVER solo $l $v" solo "lever_solo_${l}_$v.log" -- env COOP_CALIBRATE=1 COOP_WW_LEG=$l COOP_WW_LEVER=$v \
        $SOLO s166-a-lever-$l-$v -- py tools/play.py $SC/coop_world_walk.py --field 6603
  fi
}
t2() {     # t2 <leg> [lever]
  leg "LEVER T2 $1 ${2:-(its own)}" t2 "lever_t2_$1_${2:-own}.log" -- env COOP_CALIBRATE=1 COOP_WWT_LEG=$1 ${2:+COOP_WWT_LEVER=$2} \
      py tools/play.py $SC/coop_world_walk_t2.py
}

# 1-2. A-TX's two levers; A-WIRE's `--wire 15`; the restamp's (s165's own `worldfollow off`: S165-WK-CAL inside the old leg)
solo tx pose
solo tx worldfreeze
t2 wire wire15
t2 old
# 3. the ghost rows' levers (each leg still pulls its quiet lines)
solo ghost ghost
solo wrap place
solo dot dot
solo body -
# 4. the stall rows' lever
solo stall lanegap
# 5. T2's levers
t2 roam ghost
t2 roam lanegap
t2 freeze lanegap
t2 freeze ghost
t2 host hostlines
t2 host ghost
leg "LEVER T2 pair (its own)" t2 lever_t2_pair.log -- env COOP_CALIBRATE=1 COOP_WW_LEG=pair py tools/play.py $SC/coop_world_walk.py
# 6. the duo's levers (any role: THE DUO CANNOT PULL A SELFTEST-ROLE LEVER)
for v in ghost sticky dot; do
  leg "LEVER duo $v" duo "lever_duo_$v.log" -- env COOP_CALIBRATE=1 COOP_WWT_LEVER=$v $DUO $SC/coop_world_walk_t2.py
done
say "== all done (LEVER)"
