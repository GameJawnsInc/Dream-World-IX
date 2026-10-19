#!/bin/bash
# s140 calibration on the deployed s139, BEFORE deploying s140 (R3-FIELD-MODEL-AUDIT.md 4.4: "On s139, `self` is refused (NOT
# REACHED), and S4 and N1 read NOT REACHED, not green"). The solo bench with EVERY leg under COOP_CALIBRATE=1: legs S / W /
# X / N / T red in exactly their `old` row (coop_self_dress.OLD_PREDICTED -- the `self` op refused before the step, T2's
# proof absent), legs I and G GREEN on the s139 rules (stage-keyed: Cinna..Beatrix undressed, 29 codec rows, nine idle
# frames), INI / OR / S0 / P0 / PRE / PF / R green -> S138-CAL green. Then the same bench with GhostAs blank (legs I + G +
# S: I7 / G0 / S5's other mirror). Nothing here deploys or launches anything.
#
# PREREQUISITE (the operator, once, with the game CLOSED): the bench field 30606 and the 8-11 seed 30605 (COOPSUB)
# deployed and registered --
#   py tools/deploy_field.py studies/battle-coop/bench/coopsub.field.toml --id 30605 --mod-folder FF9CustomMap-msgs
#   py studies/battle-coop/bench/selfdress_bench.py deploy
# which runs
#   py tools/deploy_field.py studies/battle-coop/bench/selfdress.field.toml --id 30606 --mod-folder FF9CustomMap-msgs
# then seats the conductors and re-runs the preflight on every language; then ONE relaunch on the s139 DLL (30606 is a
# NEW id: its DictionaryPatch line registers at launch). deploy_field.py ALONE cannot ship this bench
# (no field.toml block expresses the caller's conductors): the preflight would fail CLOSED and every 30606 row read "not
# reached".
set -u
D="$(dirname "$0")"; WT=/c/gd/Dream-World-IX/.claude/worktrees/gallant-easley-04ab74
G="/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
SB="$D/selftest_block.sh"; NB="$D/selftest_block_noghost.sh"
cd "$WT" || { echo "STOP: WT=$WT is missing -- point WT= at your checkout"; exit 1; }
mkdir -p "$D/c139"
echo "INI at start $(sha256sum "$G/Memoria.ini" | cut -c1-16); DLL $(sha256sum "$G/x64/FF9_Data/Managed/Assembly-CSharp.dll" | cut -c1-16) (want s139 1365959f2efca2e7)"
if ! grep -qE "^FieldScene 30606 " "$G/FF9CustomMap-msgs/DictionaryPatch.txt"; then
  echo "STOP: 30606 is not registered in FF9CustomMap-msgs -- deploy it (selfdress_bench.py deploy) and relaunch first"; exit 1
fi
if ! grep -qE "^FieldScene 30605 " "$G/FF9CustomMap-msgs/DictionaryPatch.txt"; then
  echo "STOP: 30605 (COOPSUB, the 8-11 seed: S7 / S8) is not registered in FF9CustomMap-msgs -- py tools/deploy_field.py studies/battle-coop/bench/coopsub.field.toml --id 30605 --mod-folder FF9CustomMap-msgs, then relaunch"; exit 1
fi
echo "######## the bench field's preflight on the DEPLOYED .eb (offline, read-only) $(date +%T)"
PYTHONIOENCODING=utf-8 py -X utf8 -c "
import sys; sys.path.insert(0, 'studies/test-harness/scenarios')
import _selfdress_field as sf
eb, where = sf.deployed_eb(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX')
why = sf.preflight(eb) if eb is not None else 'absent'
print(where, '->', 'CLEAN' if why is None else why)
sys.exit(0 if why is None else 1)" || { echo "STOP: the deployed bench field fails its preflight -- re-run selfdress_bench.py deploy"; exit 1; }
echo "######## STEP 1: every leg under COOP_CALIBRATE=1 on s139 (want S138-CAL green: exactly OLD_PREDICTED red) $(date +%T)"
bash "$SB" "$D/c139" "selfdress_cal139:250:coop_self_dress:COOP_CALIBRATE=1"
echo "######## STEP 2: legs I + G + S with GhostAs blank on s139 (I / G green, S red in its old row) $(date +%T)"
bash "$NB" "$D/c139" "selfdress_cal139_noghost:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_LEGS=I+G+S"
echo "INI at end $(sha256sum "$G/Memoria.ini" | cut -c1-16)"
echo "ALL DONE $(date +%T)"
