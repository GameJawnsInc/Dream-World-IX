#!/bin/bash
# s145 proof on the deployed s145 (after cal145.example.sh was green on s144 and the owner said yes to the deploy): BATTLES FROM THE
# WORLD MAP (studies/test-harness/scenarios/coop_world_battle.py), then the regression the patch owes -- every bench that reads the
# diorama keys, the boot report, the start hold, the cut hold's over-signals or dioboot's refusal, or walks a guest onto the world map:
#   1. the SOLO bench (selftest role, 6603 -> world 9011, A off the landing): every row green -- the warm world boot (BOOT, AUDIO),
#      the warm return counted on its own load (RET) at A with A's camera, MAP digest, travel mode and song (PLACE CAM MAP MODE
#      MUSIC), still frozen (FROZEN), the host-silent lane (SILENT), `reset` with a world diorama up (RESET), the decline aboard
#      (VEH), the lever (LEVER), the cold reference last (WC), the release (R), no swirl hang (SWIRL)
#   2. the lever: COOP_CALIBRATE=1 pulls `bench worldwarm off` at P1 -> exactly LEVER_PREDICTED red (every boot declined, never a
#      cold return), S145-CAL green
#   3. the T2 BATTLE leg on cal145's s144 world-battle tape: green (BOOTING then LIVE, the stock menu served, the leave on terminal /
#      host_world, warm at A, then the rejoin into 300 with no second return); and under COOP_CALIBRATE=1 S145-WB-CAL green (s145
#      predicts no red)
#   3b. the T2 DECLINE leg on the same tape: green (aboard a chocobo the watcher declines the host's battle -- NONE on the wire,
#      one decline line, no boot, no reload)
#   4. the T2 HELD leg on cal145's held-field tape: green (the host's FIELD battle boots the guest on the world map; host_field;
#      the hold holds after the return)
#   5. the DUO (coop_world_battle.py: D0-D2, the host's world battle -- the guest boots, the host's start hold reads booting then
#      live --, the guest plays, both back warm, D3 into 300)
#   6. THE REGRESSION: BLOCK A (selftest role; full144's list: the F3.3 warm field return -- coop_diorama_return --, wait parity,
#      the start hold, the leader guard, ...), coop_world_wait's solo bench + its lever, its T2 legs (rejoin; wait on the s144 and
#      s143 world tapes) and its duo (the world freeze, the rejoin: unchanged), the T2 cut legs (cal readopt s119 s120-battle s121;
#      s120-world -- now host_world on an s145 guest -- only with S120_WORLD_TAPE=<the hand-recorded world-victory tape>), the duo G9
# SWIRL-HANG (the instrument, decision 11): a leg whose output says SWIRL-HANG is re-run ONCE -- never an engine verdict.
# Nothing here deploys or touches the engine DLL. Every output goes OUTSIDE the repo ($OUT); the selftest blocks snapshot and
# restore Memoria.ini; the T2 legs restore it byte-exact through IniGuard.
# PREREQUISITE (the operator): the game running on the deployed s145 DLL for the selftest blocks and CLOSED for the T2 / duo steps
# -- S145_DLL=<its Assembly-CSharp.dll sha256, first 16> in the environment (the runner STOPs when unset, when the live DLL differs,
# or when it is still s144's be9abacbd7b11d64) --, controllers OFF and nobody at the keyboard (THE UNATTENDED LAW), FF9 unfocused;
# 6603 registered in FF9CustomMap-world; 30602 / 30604 / 30605 / 30606 / 30607 / 30608 / 30609 registered in FF9CustomMap-msgs; the
# private port 49231 free (49201 never bound) and the owner's own bridge on 49201 DOWN for the T2 legs; [SaveFile]
# AutoSaveOnlyAtMoogle 0; cal145's tapes in .harness-runs/coop-tapes/world-battle and held-6603; s144's world tapes in world-s144
# and world-s143.
set -u
D="$(dirname "$0")"; WT="${WT:-$(cd "$D/../../../.." && pwd)}"      # the checkout this runner lives in (WT= overrides)
G="/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
OUT=/c/gd/Dream-World-IX/.harness-runs/s145
D="$(cd "$D" && pwd)"; SB="$D/selftest_block.sh"; NB="$D/selftest_block_noghost.sh"     # absolute: the runner cds
export SELFTEST_WT="$WT"                                               # the blocks run THIS checkout's scenarios
TAPEW=$(cygpath -m "$(ls -t /c/gd/Dream-World-IX/.harness-runs/coop-tapes/act-s133/*.f9tape | head -1)")
WBDIR=/c/gd/Dream-World-IX/.harness-runs/coop-tapes/world-battle
HFDIR=/c/gd/Dream-World-IX/.harness-runs/coop-tapes/held-6603
W144=/c/gd/Dream-World-IX/.harness-runs/coop-tapes/world-s144
W143=/c/gd/Dream-World-IX/.harness-runs/coop-tapes/world-s143
SCN=studies/test-harness/scenarios
cd "$WT" || { echo "STOP: WT=$WT is missing -- point WT= at your checkout"; exit 1; }
mkdir -p "$OUT/s1" "$OUT/s2" "$OUT/t" "$OUT/a" "$OUT/w" "$OUT/c"
# a real hang prints "SWIRL-HANG at <where>" (the SwirlHang row) or "not reached: SWIRL-HANG" -- never the bare word, which a
# GREEN <PFX>-SWIRL row's catalog text carries too (cal145's first run re-ran every clean leg on it)
HANG_RE='SWIRL-HANG at |not reached: SWIRL-HANG'
# run_leg <out.txt> <command...>: run it; on SWIRL-HANG (the instrument) keep that output beside and re-run the leg ONCE
run_leg() {
  local out="$1"; shift
  "$@" > "$out" 2>&1
  if grep -qE "$HANG_RE" "$out"; then
    echo "SWIRL-HANG in $out (the instrument: its logs and a frame are in the run dir) -- re-running the leg ONCE"
    mv "$out" "${out%.txt}.swirl-hang.txt"
    "$@" > "$out" 2>&1
  fi
}
# block_leg <outdir> <label:field:scenario[:ENV]>: one selftest-block bench; on SWIRL-HANG re-run it ONCE
block_leg() {
  local dir="$1" spec="$2" label="${2%%:*}"
  bash "$SB" "$dir" "$spec"
  if grep -qE "$HANG_RE" "$dir/$label.txt"; then
    echo "SWIRL-HANG in $dir/$label.txt (the instrument) -- re-running it ONCE"
    mv "$dir/$label.txt" "$dir/$label.swirl-hang.txt"
    bash "$SB" "$dir" "$spec"
  fi
}
DLL=$(sha256sum "$G/x64/FF9_Data/Managed/Assembly-CSharp.dll" | cut -c1-16)
echo "INI at start $(sha256sum "$G/Memoria.ini" | cut -c1-16); DLL $DLL (want S145_DLL=${S145_DLL:-unset})"
if [ -z "${S145_DLL:-}" ]; then
  echo "STOP: set S145_DLL=<the deployed s145 Assembly-CSharp.dll's sha256, first 16> -- this runner PROVES s145"; exit 1
fi
if [ "$DLL" = be9abacbd7b11d64 ] || [ "$DLL" != "$S145_DLL" ]; then
  echo "STOP: the live DLL is $DLL, not the s145 build S145_DLL=$S145_DLL (be9abacbd7b11d64 is s144's)"; exit 1
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
import coop_world_battle as wb
o = wb.read_oracle(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX')
print('exits', o['facts'].get('exits'), 'world eb', o['facts'].get('world_eb'), '->', 'CLEAN' if not o['problems'] else o['problems'])
sys.exit(0 if not o['problems'] else 1)" || { echo "STOP: the oracle is not CLEAN -- the route or a target moved"; exit 1; }
WBTAPE=""                                                              # the COMPLETE tape latest-world-battle.json names, never the newest
if [ -f "$WBDIR/latest-world-battle.json" ]; then
  WBTAPE=$(PYTHONIOENCODING=utf-8 py -X utf8 -c "import json, sys; print(json.load(open(sys.argv[1], encoding='utf-8'))['tape'])" "$(cygpath -w "$WBDIR/latest-world-battle.json")")
fi
HFTAPE=$(ls -t "$HFDIR"/*-host6603-*.f9tape 2>/dev/null | head -1)
echo "world-battle tape (cal145): $WBTAPE; held tape (cal145): $HFTAPE"
echo "######## STEP 1: the solo bench, every row (want all green) $(date +%T)"
block_leg "$OUT/s1" "worldbattle:6603:coop_world_battle"
echo "######## STEP 2: the lever (want S145-CAL green: exactly LEVER_PREDICTED red) $(date +%T)"
block_leg "$OUT/s2" "worldbattle_lever:6603:coop_world_battle:COOP_CALIBRATE=1"
echo "######## STEP 3: the T2 battle leg (want all green; then S145-WB-CAL green) $(date +%T)"
if [ -n "$WBTAPE" ]; then
  T="$(cygpath -m "$WBTAPE")"
  run_leg "$OUT/t/battle.txt" env COOP_WB_LEG=battle "COOP_TAPE=$T" PYTHONIOENCODING=utf-8 py tools/play.py $SCN/coop_world_battle.py
  grep -E "checks passed|^  FAIL  " "$OUT/t/battle.txt" | cut -c1-220
  run_leg "$OUT/t/battle_cal.txt" env COOP_WB_LEG=battle COOP_CALIBRATE=1 "COOP_TAPE=$T" PYTHONIOENCODING=utf-8 py tools/play.py $SCN/coop_world_battle.py
  grep -E "checks passed|^  FAIL  |PASS  S145-WB-CAL" "$OUT/t/battle_cal.txt" | cut -c1-220
  echo "######## STEP 3b: the T2 decline leg (want all green) $(date +%T)"
  run_leg "$OUT/t/decline.txt" env COOP_WB_LEG=decline "COOP_TAPE=$T" PYTHONIOENCODING=utf-8 py tools/play.py $SCN/coop_world_battle.py
  grep -E "checks passed|^  FAIL  " "$OUT/t/decline.txt" | cut -c1-220
else
  echo "no world-battle tape (cal145 STEP 1): the battle and decline legs are not run"
fi
echo "######## STEP 4: the T2 held leg (want all green) $(date +%T)"
if [ -n "$HFTAPE" ]; then
  run_leg "$OUT/t/held.txt" env COOP_WB_LEG=held "COOP_TAPE=$(cygpath -m "$HFTAPE")" PYTHONIOENCODING=utf-8 py tools/play.py $SCN/coop_world_battle.py
  grep -E "checks passed|^  FAIL  " "$OUT/t/held.txt" | cut -c1-220
else
  echo "no held-field tape (cal145 STEP 2): the held leg is not run"
fi
echo "INI after the T2 legs $(sha256sum "$G/Memoria.ini" | cut -c1-16)"
echo "######## STEP 5: the s145 duo $(date +%T)"
run_leg "$OUT/t/duo_battle.txt" env PYTHONIOENCODING=utf-8 py tools/harness/duo.py $SCN/coop_world_battle.py; echo "duo exit $?"
grep -E "^duo .*checks passed|\[duo\] (PASS|FAIL)  S145-D" "$OUT/t/duo_battle.txt" | cut -c1-300
echo "######## STEP 6: THE REGRESSION -- block A (selftest role) $(date +%T)"
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
echo "######## STEP 6b: coop_world_wait (s144) -- its solo bench and lever, its T2 legs, its duo $(date +%T)"
block_leg "$OUT/w" "worldwait:6603:coop_world_wait"
block_leg "$OUT/w" "worldwait_lever:6603:coop_world_wait:COOP_CALIBRATE=1"
run_leg "$OUT/w/rejoin.txt" env COOP_WORLD_LEG=rejoin PYTHONIOENCODING=utf-8 py tools/play.py $SCN/coop_world_wait.py
grep -E "checks passed|^  FAIL  " "$OUT/w/rejoin.txt" | cut -c1-220
WTAPE=$(ls -t "$W144"/*-world-*.f9tape 2>/dev/null | head -1)
OTAPE=$(ls -t "$W143"/*-world-*.f9tape 2>/dev/null | head -1)
if [ -n "$WTAPE" ]; then
  run_leg "$OUT/w/wait.txt" env COOP_WORLD_LEG=wait "COOP_TAPE=$(cygpath -m "$WTAPE")" PYTHONIOENCODING=utf-8 py tools/play.py $SCN/coop_world_wait.py
  grep -E "checks passed|^  FAIL  " "$OUT/w/wait.txt" | cut -c1-220
fi
if [ -n "$OTAPE" ]; then
  run_leg "$OUT/w/wait_oldhost.txt" env COOP_WORLD_LEG=wait "COOP_TAPE=$(cygpath -m "$OTAPE")" PYTHONIOENCODING=utf-8 py tools/play.py $SCN/coop_world_wait.py
  grep -E "checks passed|^  FAIL  " "$OUT/w/wait_oldhost.txt" | cut -c1-220
fi
run_leg "$OUT/w/duo_world.txt" env PYTHONIOENCODING=utf-8 py tools/harness/duo.py $SCN/coop_world_wait.py; echo "duo world exit $?"
grep -E "^duo .*checks passed|\[duo\] (PASS|FAIL)  S144-D" "$OUT/w/duo_world.txt" | cut -c1-300
echo "######## STEP 6c: TAPE + the T2 cut legs (s120-world: host_world on an s145 guest) $(date +%T)"
for leg in replaytape holdtape; do
  echo "=== $leg $(date +%T)"
  if [ "$leg" = replaytape ]; then
    env COOP_ACT_LEG=tape "COOP_TAPE=$TAPEW" PYTHONIOENCODING=utf-8 py tools/play.py $SCN/coop_action_replay.py > "$OUT/c/$leg.txt" 2>&1
  else
    env COOP_HOLD_LEG=tape PYTHONIOENCODING=utf-8 py tools/play.py $SCN/coop_action_hold.py > "$OUT/c/$leg.txt" 2>&1
  fi
  grep -E "checks passed|^  FAIL" "$OUT/c/$leg.txt" | cut -c1-200
done
for l in cal readopt s119 s120-battle s121; do
  echo "=== $l $(date +%T)"
  env COOP_CUT_LEG=$l PYTHONIOENCODING=utf-8 py tools/play.py $SCN/coop_cut_hold.py > "$OUT/c/$l.txt" 2>&1
  grep -E "checks passed|^  FAIL  " "$OUT/c/$l.txt" | cut -c1-200
  if [ "$l" = cal ] && { ! grep -qE "checks passed" "$OUT/c/cal.txt" || grep -qE "^  FAIL  " "$OUT/c/cal.txt"; }; then echo "STOP: cal not clean"; break; fi
done
if [ -n "${S120_WORLD_TAPE:-}" ]; then
  echo "=== s120-world on $S120_WORLD_TAPE $(date +%T)"
  env COOP_CUT_LEG=s120-world "COOP_TAPE=$S120_WORLD_TAPE" PYTHONIOENCODING=utf-8 py tools/play.py $SCN/coop_cut_hold.py > "$OUT/c/s120-world.txt" 2>&1
  grep -E "checks passed|^  FAIL  " "$OUT/c/s120-world.txt" | cut -c1-200
else
  echo "no S120_WORLD_TAPE (the hand-recorded world-victory tape: coop_tape_record.py THE HAND RECORDING): s120-world is not run"
fi
echo "######## STEP 6d: the duo G9 $(date +%T)"
PYTHONIOENCODING=utf-8 py tools/harness/duo.py $SCN/coop_dress_wire.py > "$OUT/t/duo_g9.txt" 2>&1; echo "duo G9 exit $?"
grep -E "^duo .*checks passed|\[duo\] (PASS|FAIL)  S1(39|4[01])" "$OUT/t/duo_g9.txt" | cut -c1-300
echo "INI at end $(sha256sum "$G/Memoria.ini" | cut -c1-16)"
echo "ALL DONE $(date +%T) -- outputs in $OUT"
