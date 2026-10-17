#!/bin/bash
# s139 calibration on the deployed s138, BEFORE deploying s139: the solo bench (leg G's old row), the offline tape check's
# red (an s117 host's tape has no section 8), and the duo leg G9 (both roots junction the live Managed -> s138).
set -u
D="$(dirname "$0")"; WT=/c/gd/Dream-World-IX/.claude/worktrees/zealous-dubinsky-016505
G="/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
SB=/c/Users/skaki/AppData/Local/Temp/claude/C--gd-Dream-World-IX--claude-worktrees-zealous-dubinsky-016505/883d1915-40bc-4044-93a4-4c19f7c00ecb/scratchpad/s133run/selftest_block.sh
cd "$WT"; mkdir -p "$D/c138"
echo "INI at start $(sha256sum "$G/Memoria.ini" | cut -c1-16); DLL $(sha256sum "$G/x64/FF9_Data/Managed/Assembly-CSharp.dll" | cut -c1-16)"
echo "######## solo bench calibration (leg G old row) $(date +%T)"
bash "$SB" "$D/c138" "selfdress_cal138:250:coop_self_dress:COOP_CALIBRATE=1"
echo "######## step 3: the s117 tape has no section 8 (want exit 1) $(date +%T)"
PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py dress C:/gd/Dream-World-IX/.harness-runs/coop-tapes/20261014-224827-host250-s117.f9tape > "$D/c138/tape117.txt" 2>&1; echo "exit $?"; tail -4 "$D/c138/tape117.txt" | cut -c1-240
echo "######## duo G9 calibration on s138 $(date +%T)"
env COOP_CALIBRATE=1 PYTHONIOENCODING=utf-8 py tools/harness/duo.py studies/test-harness/scenarios/coop_dress_wire.py > "$D/c138/duo_cal138.txt" 2>&1; echo "exit $?"
grep -E "checks passed|PASS  G9|FAIL  G9|CAL" "$D/c138/duo_cal138.txt" | cut -c1-300 | tail -14
echo "INI at end $(sha256sum "$G/Memoria.ini" | cut -c1-16)"
echo "ALL DONE $(date +%T)"
