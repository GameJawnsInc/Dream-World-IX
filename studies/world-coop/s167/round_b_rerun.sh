#!/usr/bin/env bash
# s167 ROUND B -- re-run named legs after a kit fix, through round_b_lib.sh's guards (one leg per launch).
#   ROUND_B_RERUN="lever:t2:stallhole:walk lever:duo:fullmap new:t2:stallhole" bash studies/world-coop/s167/round_b_rerun.sh
# Each item is kind:route:leg[:lever] (kind new | lever; route solo | t2 | duo). Logs: .harness-runs/s167-round-b/<stamp>-rerun/.
ROUND_B_KIND=rerun
. "$(dirname "$0")/round_b_lib.sh"
preflight new t2
for item in ${ROUND_B_RERUN:?set ROUND_B_RERUN}; do
  IFS=: read -r kind route l v <<<"$item"
  cal=""; lev=""
  if [ "$kind" = "lever" ]; then cal="COOP_CALIBRATE=1"; fi
  case "$route" in
    solo) [ -n "$v" ] && lev="COOP_WW_LEVER=$v"
          leg "$kind solo $l ${v:-}" solo "${kind}_solo_${l}_${v:-none}.log" -- env $cal COOP_WW_LEG=$l $lev \
              $SOLO s167-b-rerun-$l -- py tools/play.py $SC/coop_world_walk.py --field 6603 ;;
    t2)   [ -n "$v" ] && lev="COOP_WWT_LEVER=$v"
          leg "$kind T2 $l ${v:-}" t2 "${kind}_t2_${l}_${v:-none}.log" -- env $cal COOP_WWT_LEG=$l $lev \
              py tools/play.py $SC/coop_world_walk_t2.py ;;
    duo)  [ -n "$l" ] && lev="COOP_WWT_LEVER=$l"
          leg "$kind duo b ${l:-}" duo "${kind}_duo_b_${l:-none}.log" -- env $cal COOP_WWT_DUO=b $lev $DUO $SC/coop_world_walk_t2.py ;;
  esac
done
say "== rerun done"
