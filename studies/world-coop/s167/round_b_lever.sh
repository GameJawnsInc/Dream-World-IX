#!/usr/bin/env bash
# s167 ROUND B -- LEVER, on the s167 build: each calibration lever ALONE reproduces OLD (one change per test by lever), in the design's
# Order. COOP_CALIBRATE=1 + the leg + its lever: exactly the leg's LEVER_PREDICTED red, each red row MEASURING its lever's shape (the
# lever restores s166, so the shape is OLD's) -- every launch's CAL row is the verdict ("no predicted red stayed green, no unpredicted
# red, every shape measured"). `fullmap` is s166 exactly only beside `minimap old` (under `fullmap old` alone a walker is unlawful and
# decision 27 closes its minimap instead): the map leg's and the duo's `fullmap` lever pull both. The tps leg has no lever (the W1
# review's R4: no lever silences the WorldTPS line) -- its calibration runs with none and reds nothing.
#   bash studies/world-coop/s167/round_b_lever.sh
ROUND_B_KIND=lever
. "$(dirname "$0")/round_b_lib.sh"
preflight new t2
solo() {   # solo <leg> <lever or ->
  local l="$1" v="$2"
  if [ "$v" = "-" ]; then
    leg "LEVER solo $l (none: every row green)" solo "lever_solo_$l.log" -- env COOP_CALIBRATE=1 COOP_WW_LEG=$l \
        $SOLO s167-b-lever-$l -- py tools/play.py $SC/coop_world_walk.py --field 6603
  else
    leg "LEVER solo $l $v" solo "lever_solo_${l}_$v.log" -- env COOP_CALIBRATE=1 COOP_WW_LEG=$l COOP_WW_LEVER=$v \
        $SOLO s167-b-lever-$l-$v -- py tools/play.py $SC/coop_world_walk.py --field 6603
  fi
}
t2() {     # t2 <leg> <lever>
  leg "LEVER T2 $1 $2" t2 "lever_t2_$1_$2.log" -- env COOP_CALIBRATE=1 COOP_WWT_LEG=$1 COOP_WWT_LEVER=$2 \
      py tools/play.py $SC/coop_world_walk_t2.py
}

# 1. the walk (`walk off`: frozen, why 'lever', s166's raw why byte) and its stall hold
solo free walk
solo stale walk
# 2. the refusal (`refuse silent`: masked, no buzz, no line)
solo entry refuse
# 3. pairing / fingerprint / the walk's other refusals (`walk off`: every case frozen by the lever)
solo refuse walk
# 4. the stall hole (`stallhold old`: the freeze lifts in a stall) and its pairing row (`walk off`)
t2 stallhole stallhold
t2 stallhole walk
# 5. decline (`decline old`: once per process), TPS (no lever)
solo decline decline
solo tps -
# 6. the minimap close (`minimap old`: s166's stranded cycle)
solo minimap minimap
# 7. decision 8 (`fullmap old` + `minimap old`: s166's refusal)
solo map fullmap
# 8. T2-B and T2-HB (`walk off` on the guest / on the host)
t2 walk walk
t2 hostb walk
# 9. the duo's levers, on the GUEST, any role (THE DUO CANNOT PULL A SELFTEST-ROLE LEVER -- these are any-role)
for v in walk fullmap; do
  leg "LEVER duo b $v" duo "lever_duo_b_$v.log" -- env COOP_CALIBRATE=1 COOP_WWT_DUO=b COOP_WWT_LEVER=$v $DUO $SC/coop_world_walk_t2.py
done
say "== all done (LEVER). Next: round_b_regress.sh"
