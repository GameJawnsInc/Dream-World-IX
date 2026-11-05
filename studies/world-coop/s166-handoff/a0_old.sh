#!/usr/bin/env bash
# s166 A0: OLD measured on the live s165 (e364ca8d) -- each destructive leg in its own launch.
cd /c/gd/Dream-World-IX/.claude/worktrees/dreamy-allen-a2375f || exit 9
S="/c/Users/skaki/AppData/Local/Temp/claude/C--gd-Dream-World-IX--claude-worktrees-dreamy-allen-a2375f/3f9e72b5-f0f3-488a-a7a3-4b0fc4406058/scratchpad"
SC=studies/test-harness/scenarios
summ() { echo "== $1 exit $2"; grep -E "checks passed|S166-[A-Z0-9-]*|restore (OK|FAILED)" "$S/$3" | cut -c1-260 | tail -14; }
for leg in kitoff ferryoff; do
  COOP_CALIBRATE=1 COOP_WW_LEG=$leg py "$S/solo_ini.py" s166-a0-old-$leg -- py tools/play.py $SC/coop_world_walk.py --field 6603 > "$S/a0_old_$leg.log" 2>&1
  summ "OLD $leg" $? a0_old_$leg.log
done
echo "== all done"
