#!/bin/bash
# s143 calibration on the deployed s141, BEFORE deploying s143 (THE GUEST NEVER COMMANDS THE HOST'S LEADER --
# studies/test-harness/scenarios/coop_leader_guard.py). On s141 there is no `netsync.battle.host.guard`, so the bench never
# sends `bench leaderguard` (an s141 agent reads it as `bench 1`) and every guard row reads red -- exactly the bench's
# OLD_PREDICTED (P0, P2, L1-L8), each a JUDGED red: L2 / L3 / L6 behaviourally (the host loses Zidane at Plant Brain, the
# ghost wears him), the rest on their absent keys -- while S0, OR, PRE, P1, L0 (the seat: engine-independent) and R stay
# GREEN -> S143-CAL green. STEP 2 then records a HOST TAPE on the Plant Brain seat (coop_tape_record COOP_TAPE_SEAT=30607:
# a real host's wire where the leader sits in the guest's bit) and calibrates the s143 tape checks on it: on s141 the
# header offers the RAW 0x2 and section 8 names Zidane (62 00 00) -- so `coop_peer.py offer --want 4` and `dress --leader 0`
# must read RED here (exit 1), and their s141 twins (`offer --want 2`, `dress` without --leader) green.
#
# STEP 0 IS A DEPLOY + A RELAUNCH: the three NEW seat fields -- 30607 COOPPBRAIN (field 257's [Blank, Zidane, Vivi,
# Steiner]), 30608 COOPFOREST (field 261's [Garnet, Zidane, Vivi, Steiner]) and 30609 COOPVIVI (the leader-body seat: the
# kit's Vivi walks COOPPARTY's party) -- into FF9CustomMap-msgs. It runs ONLY under DEPLOY=yes (the owner's yes, given for
# that deploy); a new id registers at LAUNCH, so after the deploy the runner STOPs: relaunch the game, then run it again
# (without DEPLOY). Re-read every mod folder's DictionaryPatch.txt first: 30607 and 30608 were free in all of them on
# 2026-10-19, 30609 on 2026-10-20. Nothing here touches the engine DLL.
# PREREQUISITE (the operator): the game running on the s141 DLL (Assembly-CSharp 0293cb46ffa176f6 -- the runner STOPs on
# any other), controllers OFF (THE UNATTENDED LAW: the bench drives battles with harness input), FF9 unfocused; 30602,
# 30604 (COOPPARTY) registered in FF9CustomMap-msgs.
# Every output goes OUTSIDE the repo ($OUT); the selftest block snapshots and restores the owner's Memoria.ini.
set -u
D="$(dirname "$0")"; WT="${WT:-$(cd "$D/../../../.." && pwd)}"      # the checkout this runner lives in (WT= overrides)
G="/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
OUT=/c/gd/Dream-World-IX/.harness-runs/s143
D="$(cd "$D" && pwd)"; SB="$D/selftest_block.sh"                    # absolute: the runner cds
export SELFTEST_WT="$WT"                                               # the block runs THIS checkout's scenarios
cd "$WT" || { echo "STOP: WT=$WT is missing -- point WT= at your checkout"; exit 1; }
mkdir -p "$OUT/c141"
DLL=$(sha256sum "$G/x64/FF9_Data/Managed/Assembly-CSharp.dll" | cut -c1-16)
echo "INI at start $(sha256sum "$G/Memoria.ini" | cut -c1-16); DLL $DLL (want s141 0293cb46ffa176f6)"
if [ "$DLL" != 0293cb46ffa176f6 ]; then
  echo "STOP: the live DLL is $DLL, not s141's 0293cb46ffa176f6 -- this runner CALIBRATES s143 on s141"; exit 1
fi
for f in 30602 30604; do
  if ! grep -qE "^FieldScene $f " "$G/FF9CustomMap-msgs/DictionaryPatch.txt"; then
    echo "STOP: $f is not registered in FF9CustomMap-msgs (the B4/B5 bench fields)"; exit 1
  fi
done
echo "######## STEP 0: the seat fields 30607 (COOPPBRAIN), 30608 (COOPFOREST) and 30609 (COOPVIVI) $(date +%T)"
NEW=""
for f in 30607 30608 30609; do
  grep -qE "^FieldScene $f " "$G/FF9CustomMap-msgs/DictionaryPatch.txt" || NEW="$NEW $f"
done
if [ "${DEPLOY:-}" = yes ]; then
  echo "DEPLOY=yes: deploying the three seats into FF9CustomMap-msgs (the owner said yes)"
  PYTHONIOENCODING=utf-8 py -X utf8 tools/deploy_field.py studies/battle-coop/bench/plantbrain.field.toml --id 30607 --mod-folder FF9CustomMap-msgs > "$OUT/c141/deploy30607.txt" 2>&1 \
    || { echo "STOP: the 30607 deploy failed -- see $OUT/c141/deploy30607.txt"; exit 1; }
  PYTHONIOENCODING=utf-8 py -X utf8 tools/deploy_field.py studies/battle-coop/bench/forestexit.field.toml --id 30608 --mod-folder FF9CustomMap-msgs > "$OUT/c141/deploy30608.txt" 2>&1 \
    || { echo "STOP: the 30608 deploy failed -- see $OUT/c141/deploy30608.txt"; exit 1; }
  PYTHONIOENCODING=utf-8 py -X utf8 tools/deploy_field.py studies/battle-coop/bench/vivibody.field.toml --id 30609 --mod-folder FF9CustomMap-msgs > "$OUT/c141/deploy30609.txt" 2>&1 \
    || { echo "STOP: the 30609 deploy failed -- see $OUT/c141/deploy30609.txt"; exit 1; }
  for f in "$OUT/c141/deploy30607.txt" "$OUT/c141/deploy30608.txt" "$OUT/c141/deploy30609.txt"; do tail -n 2 "$f"; done | cut -c1-220
  if [ -n "$NEW" ]; then
    echo "STOP: NEW id(s)$NEW registered by this deploy -- RELAUNCH the game (a new FieldScene registers at launch), then run this again WITHOUT DEPLOY"; exit 0
  fi
elif [ -n "$NEW" ]; then
  echo "STOP: 30607 / 30608 / 30609 not registered ($NEW ) -- the seats are a DEPLOY (needs the owner's yes): DEPLOY=yes bash $0   (py tools/deploy_field.py studies/battle-coop/bench/plantbrain.field.toml --id 30607 --mod-folder FF9CustomMap-msgs; ... forestexit.field.toml --id 30608 ...; ... vivibody.field.toml --id 30609 ...), then relaunch"; exit 1
else
  echo "DEPLOY unset: NOTHING deployed -- the deployed seats must read CLEAN below"
fi
echo "######## the seats' preflight on the DEPLOYED .eb (the bench's own offline oracle, read-only: CLEAN, never STALE) $(date +%T)"
PYTHONIOENCODING=utf-8 py -X utf8 -c "
import sys; sys.path.insert(0, 'tools'); sys.path.insert(0, 'studies/test-harness/scenarios')
import coop_leader_guard as lg
o = lg.read_oracle(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX')
for f, s in sorted(o['seats'].items()): print(f, s['party'], '-> effective', s['effective'], 'moved', s['moved_from'], s['moved_to'], s['where'])
b = o['body'] or {}
print('body seat', b.get('party'), 'leader', b.get('leader'), 'model', b.get('model'), '-> ghost', b.get('ghost'))
clean = not o['problems'] and len(o['seats']) == 3 and bool(b)
print('leader', o['leader'], 'model', o['model'], '->', 'CLEAN' if clean else o['problems'])
sys.exit(0 if clean else 1)" || { echo "STOP: the deployed seats fail the preflight -- re-deploy them (a DEPLOY: needs the owner's yes): DEPLOY=yes bash $0"; exit 1; }
echo "######## STEP 1: the bench under COOP_CALIBRATE=1 on s141 (want S143-CAL green: exactly OLD_PREDICTED red) $(date +%T)"
bash "$SB" "$OUT/c141" "leaderguard_cal141:30602:coop_leader_guard:COOP_CALIBRATE=1"
echo "######## STEP 2: an s141 HOST TAPE on the Plant Brain seat (its own dir) -- the s143 tape checks must read RED $(date +%T)"
SEATDIR=/c/gd/Dream-World-IX/.harness-runs/coop-tapes/seat-s141
mkdir -p "$SEATDIR"
env COOP_TAPE_SEAT=30607 COOP_TAPE_DIR="$(cygpath -w "$SEATDIR")" PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_tape_record.py > "$OUT/c141/tape_seat.txt" 2>&1
grep -E "checks passed|^  FAIL|REC-F|party seat" "$OUT/c141/tape_seat.txt" | cut -c1-220
SEATTAPE=$(ls -t "$SEATDIR"/*-seat30607-*.f9tape 2>/dev/null | head -1)
echo "seat tape: $SEATTAPE"
if [ -n "$SEATTAPE" ]; then
  T="$(cygpath -m "$SEATTAPE")"
  PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py offer "$T" --want 4 > "$OUT/c141/offer4.txt" 2>&1; echo "offer --want 4 exit $? (want 1: s141 offers the raw mask)"
  PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py offer "$T" --want 2 > "$OUT/c141/offer2.txt" 2>&1; echo "offer --want 2 exit $? (want 0)"
  PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py dress "$T" --ghost-as auto --guest-slots 2 --leader 0 > "$OUT/c141/dress_leader.txt" 2>&1; echo "dress --leader 0 exit $? (want 1: s141 ships Zidane 62 00 00)"
  PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py dress "$T" --ghost-as auto --guest-slots 2 > "$OUT/c141/dress_raw.txt" 2>&1; echo "dress (positional) exit $? (want 0)"
  for f in "$OUT/c141/offer2.txt" "$OUT/c141/dress_raw.txt"; do tail -n 3 "$f"; done | cut -c1-240
fi
echo "INI at end $(sha256sum "$G/Memoria.ini" | cut -c1-16)"
echo "ALL DONE $(date +%T) -- outputs in $OUT/c141"
