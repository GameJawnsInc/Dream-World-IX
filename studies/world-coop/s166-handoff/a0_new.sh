#!/usr/bin/env bash
# s166 A0 deployed: NEW (both legs, one launch), the two LEVER legs, then s165's solo follow set as regression.
cd /c/gd/Dream-World-IX/.claude/worktrees/dreamy-allen-a2375f || exit 9
S="/c/Users/skaki/AppData/Local/Temp/claude/C--gd-Dream-World-IX--claude-worktrees-dreamy-allen-a2375f/3f9e72b5-f0f3-488a-a7a3-4b0fc4406058/scratchpad"
SC=studies/test-harness/scenarios
summ() { echo "== $1 exit $2"; grep -E "checks passed|restore (OK|FAILED)" "$S/$3" | cut -c1-260 | tail -3; grep -E "^\s+FAIL  " "$S/$3" | cut -c1-260 | head -12; }
py "$S/solo_ini.py" s166-a0-new -- py tools/play.py $SC/coop_world_walk.py --field 6603 > "$S/a0_new.log" 2>&1; summ "NEW both" $? a0_new.log
for leg in kitoff ferryoff; do
  COOP_CALIBRATE=1 COOP_WW_LEVER=kitcell COOP_WW_LEG=$leg py "$S/solo_ini.py" s166-a0-lever-$leg -- py tools/play.py $SC/coop_world_walk.py --field 6603 > "$S/a0_lever_$leg.log" 2>&1
  summ "LEVER $leg" $? a0_lever_$leg.log
done
for solo in out dot save; do
  COOP_WF_SOLO=$solo py "$S/solo_ini.py" s166-a0-reg-$solo -- py tools/play.py $SC/coop_world_follow.py --field 6603 > "$S/a0_reg_follow_$solo.log" 2>&1
  summ "s165 follow solo $solo" $? a0_reg_follow_$solo.log
done
echo "== all done"
