#!/usr/bin/env bash
# s166 A0b deployed: NEW + LEVER (T2-A pair), D-PAIR on the duo, then the A0 solo legs and s165's follow set + s144's wait legs as regression.
cd /c/gd/Dream-World-IX/.claude/worktrees/dreamy-allen-a2375f || exit 9
S="/c/Users/skaki/AppData/Local/Temp/claude/C--gd-Dream-World-IX--claude-worktrees-dreamy-allen-a2375f/3f9e72b5-f0f3-488a-a7a3-4b0fc4406058/scratchpad"
SC=studies/test-harness/scenarios
summ() { echo "== $1 exit $2"; grep -E "checks passed|CAL|restore (OK|FAILED)" "$S/$3" | cut -c1-260 | tail -4; grep -E "^\s+FAIL  " "$S/$3" | cut -c1-220 | head -12; }
COOP_WW_LEG=pair py tools/play.py $SC/coop_world_walk.py > "$S/a0b_new_t2.log" 2>&1; summ "NEW T2 pair" $? a0b_new_t2.log
COOP_CALIBRATE=1 COOP_WW_LEG=pair py tools/play.py $SC/coop_world_walk.py > "$S/a0b_lever_t2.log" 2>&1; summ "LEVER T2 pair" $? a0b_lever_t2.log
py "$S/solo_ini.py" s166-a0b-reg-a0 -- py tools/play.py $SC/coop_world_walk.py --field 6603 > "$S/a0b_reg_a0.log" 2>&1; summ "A0 solo legs" $? a0b_reg_a0.log
for solo in out dot save; do
  COOP_WF_SOLO=$solo py "$S/solo_ini.py" s166-a0b-reg-$solo -- py tools/play.py $SC/coop_world_follow.py --field 6603 > "$S/a0b_reg_follow_$solo.log" 2>&1
  summ "s165 follow solo $solo" $? a0b_reg_follow_$solo.log
done
COOP_WF_LEG=walk py tools/play.py $SC/coop_world_follow.py > "$S/a0b_reg_follow_walk.log" 2>&1; summ "s165 follow T2 walk" $? a0b_reg_follow_walk.log
py tools/harness/duo.py $SC/coop_world_follow.py > "$S/a0b_reg_follow_duo.log" 2>&1; summ "s165 follow duo" $? a0b_reg_follow_duo.log
COOP_TAPE=C:/gd/Dream-World-IX/.harness-runs/coop-tapes/world-s144/20261021-010037-host6603-world-s144.f9tape COOP_WORLD_LEG=wait py tools/play.py $SC/coop_world_wait.py > "$S/a0b_reg_wait_wait.log" 2>&1; summ "s144 wait T2 wait" $? a0b_reg_wait_wait.log
COOP_WORLD_LEG=rejoin py tools/play.py $SC/coop_world_wait.py > "$S/a0b_reg_wait_rejoin.log" 2>&1; summ "s144 wait T2 rejoin" $? a0b_reg_wait_rejoin.log
py tools/harness/duo.py $SC/coop_world_wait.py > "$S/a0b_reg_wait_duo.log" 2>&1; summ "s144 wait duo" $? a0b_reg_wait_duo.log
echo "== all done"
