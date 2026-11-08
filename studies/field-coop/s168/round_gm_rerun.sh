#!/usr/bin/env bash
# s168 ROUND GM -- re-run named legs after a kit fix (or the FadeDuration-300 pass), through round_gm_lib.sh's guards (one leg per launch).
#   ROUND_GM_RERUN="lever:solo:seat:restore:bag new:duo:key new:t2:hole" bash studies/field-coop/s168/round_gm_rerun.sh
# Each item is kind:route:leg[:lever] -- kind new | lever | old (lever and old run under COOP_CALIBRATE=1); route solo (coop_guest_menu.py,
# COOP_GM_LEG; the world leg on 6603) | duo (coop_guest_menu_duo.py, COOP_GMD_LEG) | t2 (coop_guest_menu_duo.py, COOP_GMT_LEG). A solo
# lever may carry its own colon (restore:<component>). The pin is ROUND_GM_PIN (new, the default; old on the deployed s167 -- every item
# then `old:...`); one pin per run, so OLD and NEW items never share a run. COOP_GMT_RAMP=world (exported by the caller) re-runs the tape
# leg's world ramp. Logs: .harness-runs/s168-round-gm/<stamp>-rerun/.
ROUND_GM_KIND=rerun
. "$(dirname "$0")/round_gm_lib.sh"
PIN="${ROUND_GM_PIN:-new}"
case "$PIN" in
  new|old) ;;
  *) refuse "ROUND_GM_PIN=$PIN: one of new, old (BRACKET reruns through ROUND_GM_SET=bracket round_gm_regress.sh)" ;;
esac
for item in ${ROUND_GM_RERUN:?set ROUND_GM_RERUN}; do
  k="${item%%:*}"
  if [ "$PIN" = "old" ] && [ "$k" != "old" ]; then refuse "ROUND_GM_PIN=old runs old:... items only (got $item)"; fi
  if [ "$PIN" = "new" ] && [ "$k" = "old" ]; then refuse "an old:... item needs ROUND_GM_PIN=old (the deployed s167): $item"; fi
done
preflight "$PIN" t2 duo
for item in ${ROUND_GM_RERUN}; do
  IFS=: read -r kind route l v w <<<"$item"
  [ -n "${w:-}" ] && v="$v:$w"
  cal=""; lev=""
  case "$kind" in
    new) ;;
    lever|old) cal="COOP_CALIBRATE=1" ;;
    *) skip_leg "rerun $item" "kind '$kind' is none of new, lever, old"; continue ;;
  esac
  case "$route" in
    solo) [ -n "${v:-}" ] && lev="COOP_GM_LEVER=$v"
          f=$GM_FIELD; [ "$l" = "world" ] && f=$FARSHORE
          leg "$kind solo $l ${v:-}" solo "${kind}_solo_${l}_${v//:/-}.log" -- env $cal COOP_GM_LEG=$l $lev \
              $SOLO s168-gm-rerun-$l -- py tools/play.py $SC/coop_guest_menu.py --field $f ;;
    duo)  [ -n "${v:-}" ] && lev="COOP_GMD_LEVER=$v"
          leg "$kind duo $l ${v:-}" duo "${kind}_duo_${l}_${v:-none}.log" -- env $cal COOP_GMD_LEG=$l $lev $DUO $SC/coop_guest_menu_duo.py ;;
    t2)   [ -n "${v:-}" ] && lev="COOP_GMT_LEVER=$v"
          leg "$kind T2 $l ${v:-}" t2 "${kind}_t2_${l}_${v:-none}.log" -- env $cal COOP_GMT_LEG=$l $lev \
              py tools/play.py $SC/coop_guest_menu_duo.py ;;
    *)    skip_leg "rerun $item" "route '$route' is none of solo, duo, t2" ;;
  esac
done
[ "$PIN" = "new" ] && proof_report new
say "== rerun done"
