#!/bin/bash
# s144 proof on the deployed s144 (after cal144.example.sh was green on s143 and the owner said yes to the deploy):
# WORLD-MAP CO-OP, WAIT THEN REJOIN (studies/test-harness/scenarios/coop_world_wait.py), then the regression the patch owes
# -- every bench that walks a guest onto the world map, reads the overlay, RedirectGuestFieldJump or section 7's flags:
#   1. the SOLO bench (selftest role, 6603 -> world 9011): every row green -- the freeze (F1 on the x / z witness, F1K the
#      keys), the Ice Cavern tile's Confirm (F2), the full map (F3), a second world load's edge (F6), the lever (F4), the
#      control (F5: `bench 0` walks and enters 300), the world battle verb (B1-B3: `battle 67 0 rand` from WorldHUD and the
#      warm return), the release (R)
#   2. the lever: COOP_CALIBRATE=1 pulls `bench worldfreeze off` at P1 -> exactly LEVER_PREDICTED red, S144-CAL green
#   3. BLOCK A (selftest role): full143's list (s144 touched FilterScriptButtons, the decline lines' place, the ENCOUNT
#      gate, the proof block, the harness release) + the s143 leader-guard bench (its release now also releases the
#      world freeze lever)
#   4. the s139-s141 dress bench, every leg, and legs I + G + S + F with GhostAs blank (s144 adds keys after `dress`)
#   5. an s144 HOST-ON-WORLD tape (COOP_TAPE_WORLD=1, its own dir): `coop_peer.py where --want world` exit 0 (b6 rides) and
#      `--want none` exit 1 -- cal144's STEP 3 read the opposite on s143
#   6. the T2 world legs: world-rejoin on the field-250 tape (green; and under COOP_CALIBRATE=1 RJ-CAL green, s144
#      predicting no red), world-wait on THIS tape (green: 'host_world') and on cal144's s143 world tape (green: the
#      old-host fallback 'host_away' -- a mixed-build row)
#   7. the tape legs and the T2 cut legs (cal readopt s119 s120-battle s121: s121's refusal reads FieldHUD / WorldHUD, the
#      grace's 'reconnecting' still precedes the world chain)
#   8. the duo G9 (coop_dress_wire.py) and the s144 duo (coop_world_wait.py: D1 the line on 6603, D2 frozen on 9011, D3 the
#      rejoin into 300)
# Nothing here deploys or touches the engine DLL. Every output goes OUTSIDE the repo ($OUT); the selftest blocks snapshot
# and restore Memoria.ini; the T2 legs and the recorder restore it byte-exact through IniGuard.
# PREREQUISITE (the operator): the game running on the deployed s144 DLL for the selftest blocks and CLOSED for the T2 /
# recorder / duo steps -- S144_DLL=<its Assembly-CSharp.dll sha256, first 16> in the environment (the runner STOPs when
# unset, when the live DLL differs, or when it is still s143's be01339d49f6a87b) --,
# controllers OFF and nobody at the keyboard (THE UNATTENDED LAW), FF9 unfocused; 6603 registered in FF9CustomMap-world; 30602 / 30604 / 30605 / 30606 / 30607
# / 30608 / 30609 registered in FF9CustomMap-msgs; the s144 legs' private port 49231 free (49201 never bound) and the
# owner's own bridge on 49201 DOWN for the T2 legs (the guest launches on the owner's ini; the legs refuse it, T2-PEER);
# [SaveFile] AutoSaveOnlyAtMoogle 0; cal144's s143 world tape in .harness-runs/coop-tapes/world-s143.
set -u
D="$(dirname "$0")"; WT="${WT:-$(cd "$D/../../../.." && pwd)}"      # the checkout this runner lives in (WT= overrides)
G="/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
OUT=/c/gd/Dream-World-IX/.harness-runs/s144
D="$(cd "$D" && pwd)"; SB="$D/selftest_block.sh"; NB="$D/selftest_block_noghost.sh"     # absolute: the runner cds
export SELFTEST_WT="$WT"                                               # the blocks run THIS checkout's scenarios
TAPEW=$(cygpath -m "$(ls -t /c/gd/Dream-World-IX/.harness-runs/coop-tapes/act-s133/*.f9tape | head -1)")
WDIR=/c/gd/Dream-World-IX/.harness-runs/coop-tapes/world-s144
ODIR=/c/gd/Dream-World-IX/.harness-runs/coop-tapes/world-s143
cd "$WT" || { echo "STOP: WT=$WT is missing -- point WT= at your checkout"; exit 1; }
mkdir -p "$OUT/s1" "$OUT/s2" "$OUT/a" "$OUT/d" "$OUT/t" "$OUT/c" "$WDIR"
DLL=$(sha256sum "$G/x64/FF9_Data/Managed/Assembly-CSharp.dll" | cut -c1-16)
echo "INI at start $(sha256sum "$G/Memoria.ini" | cut -c1-16); DLL $DLL (want S144_DLL=${S144_DLL:-unset})"
if [ -z "${S144_DLL:-}" ]; then
  echo "STOP: set S144_DLL=<the deployed s144 Assembly-CSharp.dll's sha256, first 16> -- this runner PROVES s144"; exit 1
fi
if [ "$DLL" = be01339d49f6a87b ] || [ "$DLL" != "$S144_DLL" ]; then
  echo "STOP: the live DLL is $DLL, not the s144 build S144_DLL=$S144_DLL (be01339d49f6a87b is s143's)"; exit 1
fi
if ! grep -qE "^FieldScene 6603 " "$G/FF9CustomMap-world/DictionaryPatch.txt"; then
  echo "STOP: 6603 (FARSHORE) is not registered in FF9CustomMap-world -- the route's door"; exit 1
fi
for f in 30602 30604 30605 30606 30607 30608 30609; do
  if ! grep -qE "^FieldScene $f " "$G/FF9CustomMap-msgs/DictionaryPatch.txt"; then
    echo "STOP: $f is not registered in FF9CustomMap-msgs (the regression benches' fields)"; exit 1
  fi
done
PYTHONIOENCODING=utf-8 py -X utf8 -c "
import sys; sys.path.insert(0, 'tools'); sys.path.insert(0, 'studies/test-harness/scenarios')
import coop_world_wait as cw
o = cw.read_oracle(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX')
print('exits', o['facts'].get('exits'), 'world eb', o['facts'].get('world_eb'), '->', 'CLEAN' if not o['problems'] else o['problems'])
sys.exit(0 if not o['problems'] else 1)" || { echo "STOP: the oracle is not CLEAN -- the route or a target moved"; exit 1; }
echo "######## STEP 1: the solo bench, every row (want all green) $(date +%T)"
bash "$SB" "$OUT/s1" "worldwait:6603:coop_world_wait"
echo "######## STEP 2: the lever (want S144-CAL green: exactly LEVER_PREDICTED red) $(date +%T)"
bash "$SB" "$OUT/s2" "worldwait_lever:6603:coop_world_wait:COOP_CALIBRATE=1"
echo "######## STEP 3: BLOCK A (selftest role) + the s143 leader guard $(date +%T)"
bash "$SB" "$OUT/a" \
  "leaderguard:30602:coop_leader_guard" \
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
echo "######## STEP 4: the s139-s141 dress bench, every leg (GhostAs auto), then I + G + S + F with GhostAs blank $(date +%T)"
bash "$SB" "$OUT/d" "selfdress:250:coop_self_dress"
bash "$NB" "$OUT/d" "selfdress_noghost:250:coop_self_dress:COOP_DRESS_LEGS=I+G+S+F"
echo "######## STEP 5: an s144 host-on-world tape (its own dir) -- b6 rides $(date +%T)"
env COOP_TAPE_WORLD=1 COOP_TAPE_DIR="$(cygpath -w "$WDIR")" PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_tape_record.py > "$OUT/t/tape_world.txt" 2>&1
grep -E "checks passed|^  FAIL|REC-W" "$OUT/t/tape_world.txt" | cut -c1-220
WTAPE=$(ls -t "$WDIR"/*-world-*.f9tape 2>/dev/null | head -1)
OTAPE=$(ls -t "$ODIR"/*-world-*.f9tape 2>/dev/null | head -1)
echo "s144 world tape: $WTAPE; s143 world tape (cal144): $OTAPE"
if [ -n "$WTAPE" ]; then
  T="$(cygpath -m "$WTAPE")"
  PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py where "$T" --want world > "$OUT/t/where_world.txt" 2>&1; echo "where --want world exit $? (want 0: b6 on the world map)"
  PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py where "$T" --want none > "$OUT/t/where_none.txt" 2>&1; echo "where --want none exit $? (want 1)"
  tail -n 3 "$OUT/t/where_world.txt" | cut -c1-240
fi
echo "######## STEP 6: the T2 world legs $(date +%T)"
env COOP_WORLD_LEG=rejoin PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_world_wait.py > "$OUT/t/rejoin.txt" 2>&1
grep -E "checks passed|^  FAIL  " "$OUT/t/rejoin.txt" | cut -c1-220
env COOP_WORLD_LEG=rejoin COOP_CALIBRATE=1 PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_world_wait.py > "$OUT/t/rejoin_cal.txt" 2>&1
grep -E "checks passed|^  FAIL  |PASS  S144-RJ-CAL" "$OUT/t/rejoin_cal.txt" | cut -c1-220
if [ -n "$WTAPE" ]; then
  env COOP_WORLD_LEG=wait "COOP_TAPE=$(cygpath -m "$WTAPE")" PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_world_wait.py > "$OUT/t/wait.txt" 2>&1
  grep -E "checks passed|^  FAIL  " "$OUT/t/wait.txt" | cut -c1-220
fi
if [ -n "$OTAPE" ]; then
  env COOP_WORLD_LEG=wait "COOP_TAPE=$(cygpath -m "$OTAPE")" PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_world_wait.py > "$OUT/t/wait_oldhost.txt" 2>&1
  grep -E "checks passed|^  FAIL  " "$OUT/t/wait_oldhost.txt" | cut -c1-220
else
  echo "no s143 world tape (cal144 STEP 3): the old-host wait leg is not run"
fi
echo "INI after the T2 legs $(sha256sum "$G/Memoria.ini" | cut -c1-16)"
echo "######## STEP 7: TAPE + the T2 cut legs $(date +%T)"
for leg in replaytape holdtape; do
  echo "=== $leg $(date +%T)"
  if [ "$leg" = replaytape ]; then
    env COOP_ACT_LEG=tape "COOP_TAPE=$TAPEW" PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_action_replay.py > "$OUT/t/$leg.txt" 2>&1
  else
    env COOP_HOLD_LEG=tape PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_action_hold.py > "$OUT/t/$leg.txt" 2>&1
  fi
  grep -E "checks passed|^  FAIL" "$OUT/t/$leg.txt" | cut -c1-200
done
for l in cal readopt s119 s120-battle s121; do
  echo "=== $l $(date +%T)"
  env COOP_CUT_LEG=$l PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py > "$OUT/c/$l.txt" 2>&1
  grep -E "checks passed|^  FAIL  " "$OUT/c/$l.txt" | cut -c1-200
  if [ "$l" = cal ] && { ! grep -qE "checks passed" "$OUT/c/cal.txt" || grep -qE "^  FAIL  " "$OUT/c/cal.txt"; }; then echo "STOP: cal not clean"; break; fi
done
echo "######## STEP 8: the duo G9, then the s144 duo $(date +%T)"
PYTHONIOENCODING=utf-8 py tools/harness/duo.py studies/test-harness/scenarios/coop_dress_wire.py > "$OUT/t/duo_g9.txt" 2>&1; echo "duo G9 exit $?"
grep -E "^duo .*checks passed|\[duo\] (PASS|FAIL)  S1(39|4[01])" "$OUT/t/duo_g9.txt" | cut -c1-300
PYTHONIOENCODING=utf-8 py tools/harness/duo.py studies/test-harness/scenarios/coop_world_wait.py > "$OUT/t/duo_world.txt" 2>&1; echo "duo world exit $?"
grep -E "^duo .*checks passed|\[duo\] (PASS|FAIL)  S144-D" "$OUT/t/duo_world.txt" | cut -c1-300
echo "INI at end $(sha256sum "$G/Memoria.ini" | cut -c1-16)"
echo "ALL DONE $(date +%T) -- outputs in $OUT"
