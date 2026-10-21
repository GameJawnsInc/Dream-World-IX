#!/bin/bash
# s144 calibration on the deployed s143, BEFORE deploying s144 (WORLD-MAP CO-OP, WAIT THEN REJOIN --
# studies/test-harness/scenarios/coop_world_wait.py). On s143 there is no `netsync.world`: the bench never sends
# `bench worldfreeze` (an s143 agent reads it as `bench 1`) nor a world `battle` (Session.world_battle refuses it without
# `world.next_mode`), and every s144 row reads red -- exactly each leg's predicted set, each a JUDGED red:
#   1. the SOLO bench (selftest role) under COOP_CALIBRATE=1 -> exactly OLD_PREDICTED red (P0 P1 F0 F1 F1K F2 F3 F6 F4
#      B1 B2 B3: the walker WALKS, the full map OPENS, 'battle: field only'), INI / OR / S0 / ROUTE / F5 / R GREEN ->
#      S144-CAL green
#   2. the T2 WORLD-REJOIN leg on the field-250 tape (latest.json; its coop_cut_hold CAL verdict required) under
#      COOP_CALIBRATE=1 -> RJ-DIAL / RJ-ARM / RJ-LAND / RJ-MIRROR red (an s143 guest's client is never Ensured on the world
#      map, or reads its code there with no dial gate to take it -- the leg parks its config off the field first: it stays
#      on the world map), the instrument rows (RJ-PARK, RJ-I) green -> S144-RJ-CAL green
#   3. an s143 HOST-ON-WORLD tape (coop_tape_record.py COOP_TAPE_WORLD=1, its OWN dir: latest.json untouched) -- the tape
#      check calibrated: `coop_peer.py where --want none` exit 0 (want 0: no b6 rides an s143 host) and `--want world`
#      exit 1 (want 1)
#   4. the T2 WORLD-WAIT leg on THAT tape under COOP_CALIBRATE=1 -> WT-FIELD / WT-FROZEN / WT-WORLD red (s143's bare
#      'waiting', the guest walks, no line on the world map) -> S144-WT-CAL green
#   5. the DUO under COOP_CALIBRATE=1 (both roots junction the one s143 Managed) -> D1 / D2 / D3 red -> S144-D-CAL green
# Nothing here deploys or touches the engine DLL. Every output goes OUTSIDE the repo ($OUT); the selftest block snapshots
# and restores the owner's Memoria.ini; the T2 legs and the recorder restore it byte-exact through IniGuard.
# PREREQUISITE (the operator): the game CLOSED for the T2 / recorder / duo steps (play.py and duo.py launch it), the s143
# DLL live (Assembly-CSharp be01339d49f6a87b -- the runner STOPs on any other), controllers OFF and nobody at the keyboard
# (THE UNATTENDED LAW: every walk, Confirm and battle is harness input), FF9 unfocused; 6603 registered in
# FF9CustomMap-world (re-read: other sessions edit that folder); the s144 legs' private port 49231 free (49201, the
# owner's bridge, is never bound) AND the owner's own bridge on 49201 DOWN for the T2 legs (the guest game launches on the
# owner's Memoria.ini and would join the owner's live session -- the legs refuse it, T2-PEER); [SaveFile]
# AutoSaveOnlyAtMoogle 0; the field-250 tape recorded and its CAL leg passed.
set -u
D="$(dirname "$0")"; WT="${WT:-$(cd "$D/../../../.." && pwd)}"      # the checkout this runner lives in (WT= overrides)
G="/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
OUT=/c/gd/Dream-World-IX/.harness-runs/s144
D="$(cd "$D" && pwd)"; SB="$D/selftest_block.sh"                    # absolute: the runner cds
export SELFTEST_WT="$WT"                                               # the block runs THIS checkout's scenarios
WDIR=/c/gd/Dream-World-IX/.harness-runs/coop-tapes/world-s143
cd "$WT" || { echo "STOP: WT=$WT is missing -- point WT= at your checkout"; exit 1; }
mkdir -p "$OUT/c143" "$WDIR"
DLL=$(sha256sum "$G/x64/FF9_Data/Managed/Assembly-CSharp.dll" | cut -c1-16)
echo "INI at start $(sha256sum "$G/Memoria.ini" | cut -c1-16); DLL $DLL (want s143 be01339d49f6a87b)"
if [ "$DLL" != be01339d49f6a87b ]; then
  echo "STOP: the live DLL is $DLL, not s143's be01339d49f6a87b -- this runner CALIBRATES s144 on s143"; exit 1
fi
if ! grep -qE "^FieldScene 6603 " "$G/FF9CustomMap-world/DictionaryPatch.txt"; then
  echo "STOP: 6603 (FARSHORE) is not registered in FF9CustomMap-world -- the route's door"; exit 1
fi
echo "######## the bench's offline oracle (read-only: the door, 6603's WorldMap(9011), WORLD11's Field(300), block (18,12) stock) $(date +%T)"
PYTHONIOENCODING=utf-8 py -X utf8 -c "
import sys; sys.path.insert(0, 'tools'); sys.path.insert(0, 'studies/test-harness/scenarios')
import coop_world_wait as cw
o = cw.read_oracle(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX')
print('exits', o['facts'].get('exits'), 'world eb', o['facts'].get('world_eb'), '->', 'CLEAN' if not o['problems'] else o['problems'])
sys.exit(0 if not o['problems'] else 1)" || { echo "STOP: the oracle is not CLEAN -- the route or a target moved"; exit 1; }
echo "######## STEP 1: the solo bench under COOP_CALIBRATE=1 on s143 (want S144-CAL green: exactly OLD_PREDICTED red) $(date +%T)"
bash "$SB" "$OUT/c143" "worldwait_cal143:6603:coop_world_wait:COOP_CALIBRATE=1"
echo "######## STEP 2: the T2 world-rejoin leg on the field-250 tape (want S144-RJ-CAL green) $(date +%T)"
env COOP_WORLD_LEG=rejoin COOP_CALIBRATE=1 PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_world_wait.py > "$OUT/c143/rejoin_cal.txt" 2>&1
grep -E "checks passed|^  FAIL  |PASS  S144-RJ-CAL" "$OUT/c143/rejoin_cal.txt" | cut -c1-220
echo "######## STEP 3: an s143 host-on-world tape (its own dir) -- the tape check calibrated $(date +%T)"
env COOP_TAPE_WORLD=1 COOP_TAPE_DIR="$(cygpath -w "$WDIR")" PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_tape_record.py > "$OUT/c143/tape_world.txt" 2>&1
grep -E "checks passed|^  FAIL|REC-W" "$OUT/c143/tape_world.txt" | cut -c1-220
WTAPE=$(ls -t "$WDIR"/*-world-*.f9tape 2>/dev/null | head -1)
echo "world tape: $WTAPE"
if [ -n "$WTAPE" ]; then
  T="$(cygpath -m "$WTAPE")"
  PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py where "$T" --want none > "$OUT/c143/where_none.txt" 2>&1; echo "where --want none exit $? (want 0: an s143 host says no b6)"
  PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py where "$T" --want world > "$OUT/c143/where_world.txt" 2>&1; echo "where --want world exit $? (want 1)"
  tail -n 3 "$OUT/c143/where_none.txt" | cut -c1-240
  echo "######## STEP 4: the T2 world-wait leg on the s143 world tape (want S144-WT-CAL green) $(date +%T)"
  env COOP_WORLD_LEG=wait COOP_CALIBRATE=1 "COOP_TAPE=$T" PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_world_wait.py > "$OUT/c143/wait_cal.txt" 2>&1
  grep -E "checks passed|^  FAIL  |PASS  S144-WT-CAL" "$OUT/c143/wait_cal.txt" | cut -c1-220
else
  echo "STOP before STEP 4: no world tape was recorded (see $OUT/c143/tape_world.txt)"
fi
echo "######## STEP 5: the duo under COOP_CALIBRATE=1 (want S144-D-CAL green) $(date +%T)"
env COOP_CALIBRATE=1 PYTHONIOENCODING=utf-8 py tools/harness/duo.py studies/test-harness/scenarios/coop_world_wait.py > "$OUT/c143/duo_cal.txt" 2>&1; echo "duo exit $?"
grep -E "^duo .*checks passed|\[duo\] (PASS|FAIL)  S144-D" "$OUT/c143/duo_cal.txt" | cut -c1-300
echo "INI at end $(sha256sum "$G/Memoria.ini" | cut -c1-16)"
echo "ALL DONE $(date +%T) -- outputs in $OUT/c143"
