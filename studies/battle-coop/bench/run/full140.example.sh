#!/bin/bash
# s140 proof on the deployed s140 (after cal140.example.sh was green on s139 and the owner said yes to the deploy): the
# acceptance steps (coop_self_dress.py's docstring, "s140 ACCEPTANCE"), then BLOCK A (the regression set: the host's ghost
# now dresses CharacterId 8-11 and every field SetModel / anim setter grew a hook), the tape legs and the T2 cut legs.
#   1. the bench, every leg, GhostAs auto (the owner's ini): green
#   2. each s140 lever on legs S / W / X / N / T: exactly LEVER_PREDICTED[<lever>] red, S138-CAL green each
#   3. legs I + G + S again with GhostAs blank (s139's acceptance step 2), and the s139 duo G9 (coop_dress_wire.py)
#   4. a fresh host tape's section 8 (coop_tape_record + `coop_peer.py dress`): still 08 00 01 for the COOPPARTY party
set -u
D="$(dirname "$0")"; WT=/c/gd/Dream-World-IX/.claude/worktrees/gallant-easley-04ab74
G="/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
SB="$D/selftest_block.sh"; NB="$D/selftest_block_noghost.sh"
TAPEW=$(cygpath -m "$(ls -t /c/gd/Dream-World-IX/.harness-runs/coop-tapes/act-s133/*.f9tape | head -1)")
DRESSDIR=/c/gd/Dream-World-IX/.harness-runs/coop-tapes/dress-s140
S140="S+W+X+N+T"
cd "$WT" || { echo "STOP: WT=$WT is missing -- point WT= at your checkout"; exit 1; }
mkdir -p "$D/s1" "$D/s2" "$D/s3" "$D/t" "$D/c" "$DRESSDIR"
echo "INI at start $(sha256sum "$G/Memoria.ini" | cut -c1-16); DLL $(sha256sum "$G/x64/FF9_Data/Managed/Assembly-CSharp.dll" | cut -c1-16)"
if ! grep -qE "^FieldScene 30606 " "$G/FF9CustomMap-msgs/DictionaryPatch.txt"; then
  echo "STOP: 30606 is not registered in FF9CustomMap-msgs -- deploy it (selfdress_bench.py deploy) and relaunch first"; exit 1
fi
if ! grep -qE "^FieldScene 30605 " "$G/FF9CustomMap-msgs/DictionaryPatch.txt"; then
  echo "STOP: 30605 (COOPSUB, the 8-11 seed: S7 / S8) is not registered in FF9CustomMap-msgs -- py tools/deploy_field.py studies/battle-coop/bench/coopsub.field.toml --id 30605 --mod-folder FF9CustomMap-msgs, then relaunch"; exit 1
fi
echo "######## STEP 1: the bench, every leg (GhostAs auto) $(date +%T)"
bash "$SB" "$D/s1" "selfdress:250:coop_self_dress"
echo "######## STEP 2: each s140 lever (want S138-CAL green each: exactly its LEVER_PREDICTED row red) $(date +%T)"
bash "$SB" "$D/s2" \
  "lever_self_off:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_CAL=self-off,COOP_DRESS_LEGS=$S140" \
  "lever_gate_0:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_CAL=gate-0,COOP_DRESS_LEGS=$S140" \
  "lever_law_bframe:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_CAL=law-bframe,COOP_DRESS_LEGS=$S140" \
  "lever_law_attach:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_CAL=law-attach,COOP_DRESS_LEGS=$S140" \
  "lever_law_alias:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_CAL=law-alias,COOP_DRESS_LEGS=$S140" \
  "lever_law_timeline:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_CAL=law-timeline,COOP_DRESS_LEGS=$S140"
echo "######## STEP 2b: leg G's own lever on s140 (rule-s138: G_LEVER_REDS, G7e among them) $(date +%T)"
bash "$SB" "$D/s2" "lever_rule_s138:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_CAL=rule-s138,COOP_DRESS_LEGS=I+G"
echo "######## STEP 3: legs I + G + S with GhostAs blank $(date +%T)"
bash "$NB" "$D/s3" "selfdress_noghost:250:coop_self_dress:COOP_DRESS_LEGS=I+G+S"
echo "######## STEP 3b: the s139 duo G9 (the host's transport site; GuestSlots 2 / 4 / 0) $(date +%T)"
PYTHONIOENCODING=utf-8 py tools/harness/duo.py studies/test-harness/scenarios/coop_dress_wire.py > "$D/t/duo_g9.txt" 2>&1; echo "duo exit $?"
grep -E "^duo .*checks passed|\[duo\] (PASS|FAIL)  S139" "$D/t/duo_g9.txt" | cut -c1-300
echo "######## STEP 4: an s140 host tape (its own dir: latest.json of the default home untouched) $(date +%T)"
env COOP_TAPE_DIR="$(cygpath -w "$DRESSDIR")" PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_tape_record.py > "$D/t/tape_record.txt" 2>&1
grep -E "checks passed|^  FAIL|REC-F" "$D/t/tape_record.txt" | cut -c1-220
NEWTAPE=$(ls -t "$DRESSDIR"/*.f9tape 2>/dev/null | head -1)
echo "tape: $NEWTAPE"
if [ -n "$NEWTAPE" ]; then
  PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py dress "$(cygpath -m "$NEWTAPE")" --ghost-as auto --guest-slots 2 > "$D/t/tape_dress.txt" 2>&1; echo "dress check exit $?"
  tail -5 "$D/t/tape_dress.txt" | cut -c1-240
fi
echo "INI after the recording $(sha256sum "$G/Memoria.ini" | cut -c1-16)"
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
