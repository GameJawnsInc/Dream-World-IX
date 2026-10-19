#!/bin/bash
# s141 calibration on the deployed s140, BEFORE deploying s141 (R3-FIELD-MODEL-AUDIT.md 4.5 as derived honestly by the
# orchestrator's O11: on s140 `polish` is refused and no s141 key exists, so EVERY leg-F row reads red -- F3 too: s140
# publishes no footstep table and no fired count, so the audit's "F3 green on s140" cannot hold). The bench field 30606
# must carry the s141 SEAT first (its caller gained F5's two conductors and F2d's, its player F2d's function: the live s140
# seat reads STALE in the s141 preflight and every 30606 row would read "not reached"), its preflight must read CLEAN, then
# the solo bench with EVERY leg under
# COOP_CALIBRATE=1: leg F red in exactly its `old` row (coop_self_dress.S141_OLD_PREDICTED -- each a JUDGED red on the keys
# s140 lacks; F5 reads meshflags 2), legs I / G / S / W / X / N / T GREEN on their own engine, INI / OR / S0 / P0 / PRE /
# PF / R green -> S138-CAL green. Then legs I + G + S + F with GhostAs blank (the selftest mirror's other dress: F4g).
#
# STEP 0's RE-SEAT IS A DEPLOY (the bench field into FF9CustomMap-msgs, through `selfdress_bench.py deploy` ->
# deploy_field.py --id 30606): it runs ONLY under RESEAT=yes (the owner's yes, given for that deploy); without it the runner
# deploys nothing and STOPs on a preflight that is not CLEAN, naming the re-seat. 30606 is registered since s140, so it
# re-deploys IN PLACE (no relaunch: every leg warps into it fresh). Nothing here touches the engine DLL or launches the game.
# PREREQUISITE (the operator): the game running on the s140 DLL (Assembly-CSharp 2be623db3bb2ecb5 -- the runner STOPs on any
# other), controllers OFF (THE UNATTENDED LAW), FF9 unfocused; 30606 and the 8-11 seed 30605 (COOPSUB) registered in
# FF9CustomMap-msgs.
# Every output goes OUTSIDE the repo ($OUT); the selftest blocks snapshot and restore the owner's Memoria.ini.
set -u
D="$(dirname "$0")"; WT=/c/gd/Dream-World-IX/.claude/worktrees/dreamy-allen-a2375f
G="/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
OUT=/c/gd/Dream-World-IX/.harness-runs/s141
D="$(cd "$D" && pwd)"; SB="$D/selftest_block.sh"; NB="$D/selftest_block_noghost.sh"     # absolute: the runner cds
cd "$WT" || { echo "STOP: WT=$WT is missing -- point WT= at your checkout"; exit 1; }
mkdir -p "$OUT/c140"
DLL=$(sha256sum "$G/x64/FF9_Data/Managed/Assembly-CSharp.dll" | cut -c1-16)
echo "INI at start $(sha256sum "$G/Memoria.ini" | cut -c1-16); DLL $DLL (want s140 2be623db3bb2ecb5)"
if [ "$DLL" != 2be623db3bb2ecb5 ]; then
  echo "STOP: the live DLL is $DLL, not s140's 2be623db3bb2ecb5 -- this runner CALIBRATES s141 on s140"; exit 1
fi
if ! grep -qE "^FieldScene 30606 " "$G/FF9CustomMap-msgs/DictionaryPatch.txt"; then
  echo "STOP: 30606 is not registered in FF9CustomMap-msgs -- deploy it (selfdress_bench.py deploy) and relaunch first"; exit 1
fi
if ! grep -qE "^FieldScene 30605 " "$G/FF9CustomMap-msgs/DictionaryPatch.txt"; then
  echo "STOP: 30605 (COOPSUB, the 8-11 seed: S7 / S8) is not registered in FF9CustomMap-msgs -- py tools/deploy_field.py studies/battle-coop/bench/coopsub.field.toml --id 30605 --mod-folder FF9CustomMap-msgs, then relaunch"; exit 1
fi
echo "######## STEP 0: the bench field 30606 on the s141 seat (+ F5's HideObject / ShowObject, F2d's RunScript) $(date +%T)"
if [ "${RESEAT:-}" = yes ]; then
  echo "RESEAT=yes: re-seating -- a DEPLOY of the bench field into FF9CustomMap-msgs (the owner said yes)"
  PYTHONIOENCODING=utf-8 py -X utf8 studies/battle-coop/bench/selfdress_bench.py deploy > "$OUT/c140/reseat.txt" 2>&1 \
    || { echo "STOP: the re-seat failed -- see $OUT/c140/reseat.txt"; exit 1; }
  tail -3 "$OUT/c140/reseat.txt" | cut -c1-220
else
  echo "RESEAT unset: NOTHING deployed -- the deployed seat must already read CLEAN below"
fi
echo "######## the bench field's preflight on the DEPLOYED .eb (offline, read-only: CLEAN, never STALE) $(date +%T)"
PYTHONIOENCODING=utf-8 py -X utf8 -c "
import sys; sys.path.insert(0, 'studies/test-harness/scenarios')
import _selfdress_field as sf
eb, where = sf.deployed_eb(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX')
why = sf.preflight(eb) if eb is not None else 'absent'
print(where, '->', 'CLEAN' if why is None else why)
sys.exit(0 if why is None else 1)" || { echo "STOP: the deployed bench field fails its preflight -- re-seat it (a DEPLOY: needs the owner's yes): RESEAT=yes bash $0   (it runs py -X utf8 studies/battle-coop/bench/selfdress_bench.py deploy)"; exit 1; }
echo "######## STEP 1: every leg under COOP_CALIBRATE=1 on s140 (want S138-CAL green: exactly S141_OLD_PREDICTED red) $(date +%T)"
bash "$SB" "$OUT/c140" "selfdress_cal140:250:coop_self_dress:COOP_CALIBRATE=1"
echo "######## STEP 2: legs I + G + S + F with GhostAs blank on s140 (I / G / S green, F red in its old row) $(date +%T)"
bash "$NB" "$OUT/c140" "selfdress_cal140_noghost:250:coop_self_dress:COOP_CALIBRATE=1,COOP_DRESS_LEGS=I+G+S+F"
echo "INI at end $(sha256sum "$G/Memoria.ini" | cut -c1-16)"
echo "ALL DONE $(date +%T) -- outputs in $OUT/c140"
