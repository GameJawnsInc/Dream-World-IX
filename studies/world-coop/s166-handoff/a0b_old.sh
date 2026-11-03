#!/usr/bin/env bash
# s166 A0b: OLD measured on the deployed A0 build (af1f9e02): T2-A pair, then D-PAIR on the duo.
cd /c/gd/Dream-World-IX/.claude/worktrees/dreamy-allen-a2375f || exit 9
S="/c/Users/skaki/AppData/Local/Temp/claude/C--gd-Dream-World-IX--claude-worktrees-dreamy-allen-a2375f/3f9e72b5-f0f3-488a-a7a3-4b0fc4406058/scratchpad"
SC=studies/test-harness/scenarios
summ() { echo "== $1 exit $2"; grep -E "checks passed|CAL|restore (OK|FAILED)" "$S/$3" | cut -c1-300 | tail -6; grep -E "^\s+FAIL  " "$S/$3" | cut -c1-200 | head -12; }
COOP_CALIBRATE=1 COOP_WW_LEG=pair py tools/play.py $SC/coop_world_walk.py > "$S/a0b_old_t2.log" 2>&1; summ "OLD T2 pair" $? a0b_old_t2.log
COOP_CALIBRATE=1 py tools/harness/duo.py $SC/coop_world_walk.py --no-pair > "$S/a0b_old_duo.log" 2>&1; summ "OLD duo pair" $? a0b_old_duo.log
echo "== all done"
