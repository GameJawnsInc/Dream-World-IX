#!/bin/bash
# s145 calibration on the deployed s144, BEFORE deploying s145 (BATTLES FROM THE WORLD MAP --
# studies/test-harness/scenarios/coop_world_battle.py). It RECORDS THE T2 TAPES FIRST: they need only s144 host features (the world
# battle verb, b6) and replay into s144 and s145 guests alike. On s144 there is no `netsync.world.dio`: the bench never sends
# `bench worldwarm` (an s144 agent reads it as `bench 1`), `vehicle` nor a world `dioboot` (the driver refuses each before the step),
# and every s145 row reads red -- exactly each leg's predicted set, each a JUDGED red:
#   1. THE WORLD-BATTLE TAPE (coop_tape_record.py COOP_TAPE_WORLD_BATTLE=1, its OWN dir coop-tapes/world-battle: latest.json and
#      latest-world.json untouched): PRE 25 s on 6603, the walk out, a 90 s DWELL, `battle 67 0 rand` on WorldHUD fought and won,
#      back where it fought, a 30 s STAY, then the host enters the Ice Cavern (300) -- `coop_peer.py where --want world-battle`
#      exit 0 (want 0: b6 before and after the battle) -- the tape is the one latest-world-battle.json names (the recorder moves
#      that pointer only when all five facts hold), and only if THIS run moved it; a SWIRL-HANG re-records ONCE
#   2. THE HELD-FIELD TAPE (the plain recorder ON 6603: --field 6603, COOP_TAPE_PRE_S=100, its OWN dir coop-tapes/held-6603, the
#      private COOP_PEER_PORT=49231 -- the plain recorder's default is the owner's 49201): the host stays on 6603, fights
#      `battle 67 -1 rand` there, back on 6603 (the T2 held leg's source-field hold)
#   3. the SOLO bench (selftest role) under COOP_CALIBRATE=1 -> exactly OLD_PREDICTED red (P0 P1 BOOT AUDIO RET PLACE CAM MAP MODE
#      MUSIC FROZEN SILENT RESET VEH LEVER WC), INI / OR / S0 / ROUTE / A / R / SWIRL GREEN -> S145-CAL green
#   4. the T2 BATTLE leg on tape 1 under COOP_CALIBRATE=1 -> WB-BOOT / WB-PLAY / WB-RET red (an s144 guest stays WorldHUD and
#      reports NONE: the digit panel), WB-I / WB-300 green -> S145-WB-CAL green
#   4b. the T2 DECLINE leg on tape 1 under COOP_CALIBRATE=1 -> WD-DECL red (no `vehicle` verb before s145), WD-I green ->
#      S145-WD-CAL green
#   5. the T2 HELD leg on tape 2 under COOP_CALIBRATE=1 -> HF-BOOT / HF-RET red, HF-I / HF-REJOIN green -> S145-HF-CAL green
#   6. the DUO under COOP_CALIBRATE=1 (both roots junction the one s144 Managed) -> DB / DP / DR red -> S145-D-CAL green
# SWIRL-HANG (the instrument, decision 11): a leg whose output says SWIRL-HANG (a game quiet on SwirlScene: its logs and a frame
# archived in the run dir) is re-run ONCE -- never an engine verdict.
# Nothing here deploys or touches the engine DLL. Every output goes OUTSIDE the repo ($OUT); the selftest block snapshots and
# restores the owner's Memoria.ini; the T2 legs and the recorder restore it byte-exact through IniGuard.
# PREREQUISITE (the operator): the game CLOSED for the recorder / T2 / duo steps (play.py and duo.py launch it), the s144 DLL live
# (Assembly-CSharp be9abacbd7b11d64 -- the runner STOPs on any other), controllers OFF and nobody at the keyboard
# (THE UNATTENDED LAW: every walk, Confirm, boot and battle is harness input), FF9 unfocused; 6603 registered in FF9CustomMap-world (re-read:
# other sessions edit that folder); the s145 legs' private port 49231 free (49201, the owner's bridge, is never bound) AND the
# owner's own bridge on 49201 DOWN for the T2 legs (the legs refuse it, T2-PEER); [SaveFile] AutoSaveOnlyAtMoogle 0.
set -u
D="$(dirname "$0")"; WT="${WT:-$(cd "$D/../../../.." && pwd)}"      # the checkout this runner lives in (WT= overrides)
G="/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
OUT=/c/gd/Dream-World-IX/.harness-runs/s145
D="$(cd "$D" && pwd)"; SB="$D/selftest_block.sh"                    # absolute: the runner cds
export SELFTEST_WT="$WT"                                               # the block runs THIS checkout's scenarios
WBDIR=/c/gd/Dream-World-IX/.harness-runs/coop-tapes/world-battle
HFDIR=/c/gd/Dream-World-IX/.harness-runs/coop-tapes/held-6603
SCN=studies/test-harness/scenarios
cd "$WT" || { echo "STOP: WT=$WT is missing -- point WT= at your checkout"; exit 1; }
mkdir -p "$OUT/c144" "$WBDIR" "$HFDIR"
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
DLL=$(sha256sum "$G/x64/FF9_Data/Managed/Assembly-CSharp.dll" | cut -c1-16)
echo "INI at start $(sha256sum "$G/Memoria.ini" | cut -c1-16); DLL $DLL (want s144 be9abacbd7b11d64)"
if [ "$DLL" != be9abacbd7b11d64 ]; then
  echo "STOP: the live DLL is $DLL, not s144's be9abacbd7b11d64 -- this runner CALIBRATES s145 on s144 (and records its tapes there)"; exit 1
fi
if ! grep -qE "^FieldScene 6603 " "$G/FF9CustomMap-world/DictionaryPatch.txt"; then
  echo "STOP: 6603 (FARSHORE) is not registered in FF9CustomMap-world -- the route's door"; exit 1
fi
echo "######## the bench's offline oracle (read-only: the door, 6603's WorldMap(9011), WORLD11's Field(300), block (18,12) stock, scene 359) $(date +%T)"
PYTHONIOENCODING=utf-8 py -X utf8 -c "
import sys; sys.path.insert(0, 'tools'); sys.path.insert(0, 'studies/test-harness/scenarios')
import coop_world_battle as wb
o = wb.read_oracle(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX')
print('exits', o['facts'].get('exits'), 'world eb', o['facts'].get('world_eb'), '->', 'CLEAN' if not o['problems'] else o['problems'])
sys.exit(0 if not o['problems'] else 1)" || { echo "STOP: the oracle is not CLEAN -- the route or a target moved"; exit 1; }
echo "######## STEP 1: the world-battle tape on the s144 host (its own dir) -- FIRST $(date +%T)"
touch "$OUT/c144/.step1-start"                                         # the pointer must move in THIS run
run_leg "$OUT/c144/tape_world_battle.txt" env COOP_TAPE_WORLD_BATTLE=1 COOP_TAPE_DIR="$(cygpath -w "$WBDIR")" PYTHONIOENCODING=utf-8 py tools/play.py $SCN/coop_tape_record.py
grep -E "checks passed|^  FAIL|REC-W" "$OUT/c144/tape_world_battle.txt" | cut -c1-220
WBTAPE=""
if [ "$WBDIR/latest-world-battle.json" -nt "$OUT/c144/.step1-start" ]; then
  WBTAPE=$(PYTHONIOENCODING=utf-8 py -X utf8 -c "import json, sys; print(json.load(open(sys.argv[1], encoding='utf-8'))['tape'])" "$(cygpath -w "$WBDIR/latest-world-battle.json")")
else
  echo "no COMPLETE world-battle tape this run: latest-world-battle.json did not move (a REC-WBF fact is missing -- never the newest partial tape)"
fi
echo "world-battle tape: $WBTAPE"
if [ -n "$WBTAPE" ]; then
  PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py where "$(cygpath -m "$WBTAPE")" --want world-battle > "$OUT/c144/where_world_battle.txt" 2>&1; echo "where --want world-battle exit $? (want 0: b6 before and after the battle)"
  tail -n 4 "$OUT/c144/where_world_battle.txt" | cut -c1-240
fi
echo "######## STEP 2: the held-field tape on the s144 host, ON 6603 (its own dir) $(date +%T)"
env COOP_PEER_PORT=49231 COOP_TAPE_PRE_S=100 COOP_TAPE_DIR="$(cygpath -w "$HFDIR")" PYTHONIOENCODING=utf-8 py tools/play.py $SCN/coop_tape_record.py --field 6603 > "$OUT/c144/tape_held.txt" 2>&1
grep -E "checks passed|^  FAIL|REC-F" "$OUT/c144/tape_held.txt" | cut -c1-220
HFTAPE=$(ls -t "$HFDIR"/*-host6603-*.f9tape 2>/dev/null | head -1)
echo "held tape: $HFTAPE"
echo "######## STEP 3: the solo bench under COOP_CALIBRATE=1 on s144 (want S145-CAL green: exactly OLD_PREDICTED red) $(date +%T)"
bash "$SB" "$OUT/c144" "worldbattle_cal144:6603:coop_world_battle:COOP_CALIBRATE=1"
if grep -qE "$HANG_RE" "$OUT/c144/worldbattle_cal144.txt"; then
  echo "SWIRL-HANG in the solo bench (the instrument) -- re-running it ONCE"
  mv "$OUT/c144/worldbattle_cal144.txt" "$OUT/c144/worldbattle_cal144.swirl-hang.txt"
  bash "$SB" "$OUT/c144" "worldbattle_cal144:6603:coop_world_battle:COOP_CALIBRATE=1"
fi
if [ -n "$WBTAPE" ]; then
  echo "######## STEP 4: the T2 battle leg on the world-battle tape (want S145-WB-CAL green) $(date +%T)"
  run_leg "$OUT/c144/battle_cal.txt" env COOP_WB_LEG=battle COOP_CALIBRATE=1 "COOP_TAPE=$(cygpath -m "$WBTAPE")" PYTHONIOENCODING=utf-8 py tools/play.py $SCN/coop_world_battle.py
  grep -E "checks passed|^  FAIL  |PASS  S145-WB-CAL" "$OUT/c144/battle_cal.txt" | cut -c1-220
  echo "######## STEP 4b: the T2 decline leg on the world-battle tape (want S145-WD-CAL green) $(date +%T)"
  run_leg "$OUT/c144/decline_cal.txt" env COOP_WB_LEG=decline COOP_CALIBRATE=1 "COOP_TAPE=$(cygpath -m "$WBTAPE")" PYTHONIOENCODING=utf-8 py tools/play.py $SCN/coop_world_battle.py
  grep -E "checks passed|^  FAIL  |PASS  S145-WD-CAL" "$OUT/c144/decline_cal.txt" | cut -c1-220
else
  echo "STOP before STEP 4: no world-battle tape was recorded (see $OUT/c144/tape_world_battle.txt)"
fi
if [ -n "$HFTAPE" ]; then
  echo "######## STEP 5: the T2 held leg on the held-field tape (want S145-HF-CAL green) $(date +%T)"
  run_leg "$OUT/c144/held_cal.txt" env COOP_WB_LEG=held COOP_CALIBRATE=1 "COOP_TAPE=$(cygpath -m "$HFTAPE")" PYTHONIOENCODING=utf-8 py tools/play.py $SCN/coop_world_battle.py
  grep -E "checks passed|^  FAIL  |PASS  S145-HF-CAL" "$OUT/c144/held_cal.txt" | cut -c1-220
else
  echo "no held-field tape (STEP 2): the held leg is not run"
fi
echo "######## STEP 6: the duo under COOP_CALIBRATE=1 (want S145-D-CAL green) $(date +%T)"
run_leg "$OUT/c144/duo_cal.txt" env COOP_CALIBRATE=1 PYTHONIOENCODING=utf-8 py tools/harness/duo.py $SCN/coop_world_battle.py; echo "duo exit $?"
grep -E "^duo .*checks passed|\[duo\] (PASS|FAIL)  S145-D" "$OUT/c144/duo_cal.txt" | cut -c1-300
echo "INI at end $(sha256sum "$G/Memoria.ini" | cut -c1-16)"
echo "ALL DONE $(date +%T) -- outputs in $OUT/c144"
