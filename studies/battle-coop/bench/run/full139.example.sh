#!/bin/bash
# s139 proof on the deployed s139: the acceptance steps (bench under GhostAs auto + its lever; the bench under GhostAs blank;
# a fresh s139 host tape's section 8; the duo G9), then BLOCK A (the regression set: the host state frame changed), the
# tape legs and the T2 cut legs.
set -u
D="$(dirname "$0")"; WT=/c/gd/Dream-World-IX/.claude/worktrees/zealous-dubinsky-016505
G="/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
SC=/c/Users/skaki/AppData/Local/Temp/claude/C--gd-Dream-World-IX--claude-worktrees-zealous-dubinsky-016505/883d1915-40bc-4044-93a4-4c19f7c00ecb/scratchpad
SB=$SC/s133run/selftest_block.sh
NB=$SC/s139run/selftest_block_noghost.sh
TAPEW=$(cygpath -m "$(ls -t /c/gd/Dream-World-IX/.harness-runs/coop-tapes/act-s133/*.f9tape | head -1)")
DRESSDIR=/c/gd/Dream-World-IX/.harness-runs/coop-tapes/dress-s139
cd "$WT"; mkdir -p "$D/t" "$D/c" "$DRESSDIR"
echo "INI at start $(sha256sum "$G/Memoria.ini" | cut -c1-16); DLL $(sha256sum "$G/x64/FF9_Data/Managed/Assembly-CSharp.dll" | cut -c1-16)"
echo "######## STEP 1: the bench (GhostAs auto) + its lever $(date +%T)"
bash "$SB" "$D/s1" \
  "selfdress:250:coop_self_dress" \
  "selfdress_lever:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_CAL=rule-s138"
echo "######## STEP 2: the bench with GhostAs blank $(date +%T)"
bash "$NB" "$D/s2" "selfdress_noghost:250:coop_self_dress"
echo "######## STEP 4: an s139 host tape (separate dir: latest.json of the default home untouched) $(date +%T)"
env COOP_TAPE_DIR="$(cygpath -w "$DRESSDIR")" PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_tape_record.py > "$D/t/tape_record.txt" 2>&1
grep -E "checks passed|^  FAIL|REC-F" "$D/t/tape_record.txt" | cut -c1-220
NEWTAPE=$(ls -t "$DRESSDIR"/*.f9tape 2>/dev/null | head -1)
echo "tape: $NEWTAPE"
if [ -n "$NEWTAPE" ]; then
  PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py dress "$(cygpath -m "$NEWTAPE")" --ghost-as auto --guest-slots 2 > "$D/t/tape_dress.txt" 2>&1; echo "dress check exit $?"
  tail -5 "$D/t/tape_dress.txt" | cut -c1-240
fi
echo "INI after the recording $(sha256sum "$G/Memoria.ini" | cut -c1-16)"
echo "######## STEP 5: the duo G9 $(date +%T)"
PYTHONIOENCODING=utf-8 py tools/harness/duo.py studies/test-harness/scenarios/coop_dress_wire.py > "$D/t/duo_g9.txt" 2>&1; echo "duo exit $?"
grep -E "^duo .*checks passed|\[duo\] (PASS|FAIL)  S139" "$D/t/duo_g9.txt" | cut -c1-300
echo "######## BLOCK A (selftest role) $(date +%T)"
bash "$SB" "$D/a" \
  "trance:30602:coop_action_trance" \
  "fallback:30602:coop_action_fallback" \
  "hold:30602:coop_action_hold" \
  "replay:30602:coop_action_replay" \
  "act_host:30602:coop_action_host" \
  "start_hold:30602:coop_battle_start_hold" \
  "handback_live:30602:coop_handback_live" \
  "intro_mirror:30602:coop_battle_intro_mirror" \
  "wait_parity:30602:coop_battle_wait_parity" \
  "flee_defeat:30602:coop_battle_flee_defeat" \
  "host_gates:30602:coop_battle_host_gates" \
  "containment:30602:coop_battle_containment" \
  "stock_menu:30602:coop_stock_menu" \
  "stock_menu_content:30602:coop_stock_menu_content" \
  "stock_menu_live:30602:coop_stock_menu_live" \
  "end_host:30602:coop_battle_end_host" \
  "end_guest:30602:coop_battle_end_guest" \
  "result_replay:30602:coop_battle_result_replay" \
  "handback:30602:coop_battle_handback" \
  "diorama_return:30602:coop_diorama_return" \
  "talk_relay:30801:coop_talk_relay" \
  "dialogue_authority:30801:coop_dialogue_authority"
echo "######## TAPE + BLOCK C $(date +%T)"
for leg in replaytape holdtape; do
  echo "=== $leg $(date +%T)"
  if [ "$leg" = replaytape ]; then
    env COOP_ACT_LEG=tape "COOP_TAPE=$TAPEW" PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_action_replay.py > "$D/t/$leg.txt" 2>&1
  else
    env COOP_HOLD_LEG=tape PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_action_hold.py > "$D/t/$leg.txt" 2>&1
  fi
  grep -E "checks passed|^  FAIL" "$D/t/$leg.txt" | cut -c1-200
done
for l in cal readopt s119 s120-battle; do
  echo "=== $l $(date +%T)"
  env COOP_CUT_LEG=$l PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py > "$D/c/$l.txt" 2>&1
  grep -E "checks passed|^  FAIL  " "$D/c/$l.txt" | cut -c1-200
  grep -h -oE "hold [0-9]+ - outage [0-9]+ = [-+0-9]+ ms against tail [0-9.]+ ms" "$D/c/$l.txt" | head -1
  if [ "$l" = cal ] && { ! grep -qE "checks passed" "$D/c/cal.txt" || grep -qE "^  FAIL  " "$D/c/cal.txt"; }; then echo "STOP: cal not clean"; break; fi
done
echo "INI at end $(sha256sum "$G/Memoria.ini" | cut -c1-16)"
echo "ALL DONE $(date +%T)"
