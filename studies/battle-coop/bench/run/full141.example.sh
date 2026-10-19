#!/bin/bash
# s141 proof on the deployed s141 (after cal141.example.sh was green on s140 and the owner said yes to the deploy): the
# acceptance steps (coop_self_dress.py's docstring, "s141 ACCEPTANCE"), then BLOCK A (the regression set: s141 grew a hook
# at CHRFX, MESHSHOW / MESHHIDE, ATTACH, fldmcf's actor row, FF9Snd's match and the field load's table reset), the tape
# legs and the T2 cut legs.
#   0. the bench field 30606 re-seated (idempotent: the s141 caller) and its preflight CLEAN
#   1. the bench, every leg (I, G, S, W, X, N, T, F), GhostAs auto (the owner's ini): green
#   2. leg F's lever (polish-off on F): exactly S141_LEVER_PREDICTED red, S138-CAL green
#   2b. each s140 lever on legs S / W / X / N / T: exactly LEVER_PREDICTED[<lever>] red, S138-CAL green each
#   2c. leg G's own lever (rule-s138 on I + G)
#   3. legs I + G + S + F again with GhostAs blank, and the s139 / s140 duo G9 (coop_dress_wire.py)
#   4. a fresh host tape's section 8 (coop_tape_record + `coop_peer.py dress`): still 08 00 01 for the COOPPARTY party
#      (s141 adds NO wire byte: the wire stays v14)
# STEP 0 IS A DEPLOY of the bench field (FF9CustomMap-msgs): covered by the owner's yes to the s141 run. Nothing here
# touches the engine DLL. Every output goes OUTSIDE the repo ($OUT); the selftest blocks snapshot and restore Memoria.ini.
set -u
D="$(dirname "$0")"; WT=/c/gd/Dream-World-IX/.claude/worktrees/dreamy-allen-a2375f
G="/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
OUT=/c/gd/Dream-World-IX/.harness-runs/s141
D="$(cd "$D" && pwd)"; SB="$D/selftest_block.sh"; NB="$D/selftest_block_noghost.sh"     # absolute: the runner cds
TAPEW=$(cygpath -m "$(ls -t /c/gd/Dream-World-IX/.harness-runs/coop-tapes/act-s133/*.f9tape | head -1)")
DRESSDIR=/c/gd/Dream-World-IX/.harness-runs/coop-tapes/dress-s141
S140="S+W+X+N+T"
cd "$WT" || { echo "STOP: WT=$WT is missing -- point WT= at your checkout"; exit 1; }
mkdir -p "$OUT/s0" "$OUT/s1" "$OUT/s2" "$OUT/s3" "$OUT/t" "$OUT/c" "$OUT/a" "$DRESSDIR"
echo "INI at start $(sha256sum "$G/Memoria.ini" | cut -c1-16); DLL $(sha256sum "$G/x64/FF9_Data/Managed/Assembly-CSharp.dll" | cut -c1-16)"
if ! grep -qE "^FieldScene 30606 " "$G/FF9CustomMap-msgs/DictionaryPatch.txt"; then
  echo "STOP: 30606 is not registered in FF9CustomMap-msgs -- deploy it (selfdress_bench.py deploy) and relaunch first"; exit 1
fi
if ! grep -qE "^FieldScene 30605 " "$G/FF9CustomMap-msgs/DictionaryPatch.txt"; then
  echo "STOP: 30605 (COOPSUB, the 8-11 seed: S7 / S8) is not registered in FF9CustomMap-msgs -- py tools/deploy_field.py studies/battle-coop/bench/coopsub.field.toml --id 30605 --mod-folder FF9CustomMap-msgs, then relaunch"; exit 1
fi
echo "######## STEP 0: re-seat the bench field 30606 (the s141 caller) and its preflight $(date +%T)"
PYTHONIOENCODING=utf-8 py -X utf8 studies/battle-coop/bench/selfdress_bench.py deploy > "$OUT/s0/reseat.txt" 2>&1 \
  || { echo "STOP: the re-seat failed -- see $OUT/s0/reseat.txt"; exit 1; }
PYTHONIOENCODING=utf-8 py -X utf8 -c "
import sys; sys.path.insert(0, 'studies/test-harness/scenarios')
import _selfdress_field as sf
eb, where = sf.deployed_eb(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX')
why = sf.preflight(eb) if eb is not None else 'absent'
print(where, '->', 'CLEAN' if why is None else why)
sys.exit(0 if why is None else 1)" || { echo "STOP: the deployed bench field fails its preflight -- re-run selfdress_bench.py deploy"; exit 1; }
echo "######## STEP 1: the bench, every leg (GhostAs auto) $(date +%T)"
bash "$SB" "$OUT/s1" "selfdress:250:coop_self_dress"
echo "######## STEP 2: leg F's lever (want S138-CAL green: exactly S141_LEVER_PREDICTED red, F3 and FP green) $(date +%T)"
bash "$SB" "$OUT/s2" "lever_polish_off:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_CAL=polish-off,COOP_DRESS_LEGS=F"
echo "######## STEP 2b: each s140 lever (want S138-CAL green: exactly its LEVER_PREDICTED row red) $(date +%T)"
bash "$SB" "$OUT/s2" \
  "lever_self_off:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_CAL=self-off,COOP_DRESS_LEGS=$S140" \
  "lever_gate_0:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_CAL=gate-0,COOP_DRESS_LEGS=$S140" \
  "lever_law_bframe:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_CAL=law-bframe,COOP_DRESS_LEGS=$S140" \
  "lever_law_attach:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_CAL=law-attach,COOP_DRESS_LEGS=$S140" \
  "lever_law_alias:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_CAL=law-alias,COOP_DRESS_LEGS=$S140" \
  "lever_law_timeline:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_CAL=law-timeline,COOP_DRESS_LEGS=$S140"
echo "######## STEP 2c: leg G's own lever (rule-s138: G_LEVER_REDS) $(date +%T)"
bash "$SB" "$OUT/s2" "lever_rule_s138:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_CAL=rule-s138,COOP_DRESS_LEGS=I+G"
echo "######## STEP 3: legs I + G + S + F with GhostAs blank $(date +%T)"
bash "$NB" "$OUT/s3" "selfdress_noghost:250:coop_self_dress:COOP_DRESS_LEGS=I+G+S+F"
echo "######## STEP 3b: the s139 / s140 duo G9 (the host's transport site; GuestSlots 2 / 4 / 0; an s140+ guest dresses itself) $(date +%T)"
PYTHONIOENCODING=utf-8 py tools/harness/duo.py studies/test-harness/scenarios/coop_dress_wire.py > "$OUT/t/duo_g9.txt" 2>&1; echo "duo exit $?"
grep -E "^duo .*checks passed|\[duo\] (PASS|FAIL)  S139" "$OUT/t/duo_g9.txt" | cut -c1-300
echo "######## STEP 4: an s141 host tape (its own dir: latest.json of the default home untouched) $(date +%T)"
env COOP_TAPE_DIR="$(cygpath -w "$DRESSDIR")" PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_tape_record.py > "$OUT/t/tape_record.txt" 2>&1
grep -E "checks passed|^  FAIL|REC-F" "$OUT/t/tape_record.txt" | cut -c1-220
NEWTAPE=$(ls -t "$DRESSDIR"/*.f9tape 2>/dev/null | head -1)
echo "tape: $NEWTAPE"
if [ -n "$NEWTAPE" ]; then
  PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py dress "$(cygpath -m "$NEWTAPE")" --ghost-as auto --guest-slots 2 > "$OUT/t/tape_dress.txt" 2>&1; echo "dress check exit $?"
  tail -5 "$OUT/t/tape_dress.txt" | cut -c1-240
fi
echo "INI after the recording $(sha256sum "$G/Memoria.ini" | cut -c1-16)"
echo "######## BLOCK A (selftest role) $(date +%T)"
bash "$SB" "$OUT/a" \
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
    env COOP_ACT_LEG=tape "COOP_TAPE=$TAPEW" PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_action_replay.py > "$OUT/t/$leg.txt" 2>&1
  else
    env COOP_HOLD_LEG=tape PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_action_hold.py > "$OUT/t/$leg.txt" 2>&1
  fi
  grep -E "checks passed|^  FAIL" "$OUT/t/$leg.txt" | cut -c1-200
done
for l in cal readopt s119 s120-battle; do
  echo "=== $l $(date +%T)"
  env COOP_CUT_LEG=$l PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py > "$OUT/c/$l.txt" 2>&1
  grep -E "checks passed|^  FAIL  " "$OUT/c/$l.txt" | cut -c1-200
  grep -h -oE "hold [0-9]+ - outage [0-9]+ = [-+0-9]+ ms against tail [0-9.]+ ms" "$OUT/c/$l.txt" | head -1
  if [ "$l" = cal ] && { ! grep -qE "checks passed" "$OUT/c/cal.txt" || grep -qE "^  FAIL  " "$OUT/c/cal.txt"; }; then echo "STOP: cal not clean"; break; fi
done
echo "INI at end $(sha256sum "$G/Memoria.ini" | cut -c1-16)"
echo "ALL DONE $(date +%T) -- outputs in $OUT"
