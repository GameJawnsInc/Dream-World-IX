#!/bin/bash
# s143 proof on the deployed s143 (after cal143.example.sh was green on s141 and the owner said yes to the deploy): THE GUEST
# NEVER COMMANDS THE HOST'S LEADER (studies/test-harness/scenarios/coop_leader_guard.py), then the regression the patch
# owes -- every bench whose battle ownership or field dress reads GuestSlots:
#   1. the bench (GuestSlots 2: COOPPARTY's negative control, the forest-exit seat, the Plant Brain seat + battle 303 --
#      LAST, left running): every row green
#   2. the lever: COOP_CALIBRATE=1 pulls `bench leaderguard off` -> exactly LEVER_PREDICTED red, S143-CAL green
#   3. BLOCK A (selftest role): s143 converted every host ownership lane -- the HUD hooks, the intake, the roster, G6 / G3,
#      Wait, the refusal count -- and the header byte; wait_parity is RE-KEYED (its `guestslots 15` premise needs the
#      positional rule: it pulls `bench leaderguard off` on an s143 engine and wants the release line)
#   4. the s139-s141 dress bench, every leg (the selftest mirror's site now guards `auto` first: leg G seats no leader in a
#      guest bit -- a guard no-op, which these runs PROVE), and legs I + G + S + F with GhostAs blank
#   5. the s139-s141 duo G9 (GuestSlots 2 / 4 / 0 on COOPPARTY: the leader at position 0 is never a guest bit)
#   6. a fresh host tape's section 8 (coop_tape_record + `coop_peer.py dress --leader 0`): still 08 00 01 on COOPPARTY
#   6b. a host tape on the PLANT BRAIN SEAT (COOP_TAPE_SEAT=30607: the leader in the guest's bit on a REAL host's wire):
#      the header offers 0x4 from each battle's first Ready frame (`coop_peer.py offer --want 4`) and section 8 names Vivi
#      (`dress --ghost-as auto --guest-slots 2 --leader 0`: 08 00 01) -- and the positional twins read RED (cal143's STEP 2
#      showed them green on s141)
#   7. the tape legs and the T2 cut legs (GuestSlots 0: unchanged)
# Nothing here deploys or touches the engine DLL. Every output goes OUTSIDE the repo ($OUT); the selftest blocks snapshot
# and restore Memoria.ini.
# PREREQUISITE (the operator): the game running on the deployed s143 DLL -- S143_DLL=<its Assembly-CSharp.dll sha256, first
# 16> in the environment (the runner STOPs when unset, when the live DLL differs, or when it is still s141's
# 0293cb46ffa176f6) --, controllers OFF (THE UNATTENDED LAW: the bench drives battles, duo G9 and every walk inject harness
# input), FF9 unfocused; 30602 / 30604 / 30605 / 30606 / 30607 / 30608 / 30609 registered in FF9CustomMap-msgs (cal143's
# STEP 0 put 30607 / 30608 / 30609 there; the seats' preflight must read CLEAN).
set -u
D="$(dirname "$0")"; WT="${WT:-$(cd "$D/../../../.." && pwd)}"      # the checkout this runner lives in (WT= overrides)
G="/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
OUT=/c/gd/Dream-World-IX/.harness-runs/s143
D="$(cd "$D" && pwd)"; SB="$D/selftest_block.sh"; NB="$D/selftest_block_noghost.sh"     # absolute: the runner cds
export SELFTEST_WT="$WT"                                               # the blocks run THIS checkout's scenarios
TAPEW=$(cygpath -m "$(ls -t /c/gd/Dream-World-IX/.harness-runs/coop-tapes/act-s133/*.f9tape | head -1)")
DRESSDIR=/c/gd/Dream-World-IX/.harness-runs/coop-tapes/dress-s143
cd "$WT" || { echo "STOP: WT=$WT is missing -- point WT= at your checkout"; exit 1; }
mkdir -p "$OUT/s1" "$OUT/s2" "$OUT/a" "$OUT/d" "$OUT/t" "$OUT/c" "$DRESSDIR"
DLL=$(sha256sum "$G/x64/FF9_Data/Managed/Assembly-CSharp.dll" | cut -c1-16)
echo "INI at start $(sha256sum "$G/Memoria.ini" | cut -c1-16); DLL $DLL (want S143_DLL=${S143_DLL:-unset})"
if [ -z "${S143_DLL:-}" ]; then
  echo "STOP: set S143_DLL=<the deployed s143 Assembly-CSharp.dll's sha256, first 16> -- this runner PROVES s143"; exit 1
fi
if [ "$DLL" = 0293cb46ffa176f6 ] || [ "$DLL" != "$S143_DLL" ]; then
  echo "STOP: the live DLL is $DLL, not the s143 build S143_DLL=$S143_DLL (0293cb46ffa176f6 is s141's)"; exit 1
fi
for f in 30602 30604 30605 30606 30607 30608 30609; do
  if ! grep -qE "^FieldScene $f " "$G/FF9CustomMap-msgs/DictionaryPatch.txt"; then
    echo "STOP: $f is not registered in FF9CustomMap-msgs -- cal143.example.sh's STEP 0 deploys 30607 / 30608 / 30609 (DEPLOY=yes), then relaunch"; exit 1
  fi
done
PYTHONIOENCODING=utf-8 py -X utf8 -c "
import sys; sys.path.insert(0, 'tools'); sys.path.insert(0, 'studies/test-harness/scenarios')
import coop_leader_guard as lg
o = lg.read_oracle(r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX')
clean = not o['problems'] and len(o['seats']) == 3 and bool(o['body'])
print('seats', sorted(o['seats']), 'leader', o['leader'], 'body', (o['body'] or {}).get('leader'), '->', 'CLEAN' if clean else o['problems'])
sys.exit(0 if clean else 1)" || { echo "STOP: the deployed seats fail the preflight -- re-deploy them (cal143.example.sh, DEPLOY=yes: the owner's yes)"; exit 1; }
echo "######## STEP 1: the bench, every row (want all green) $(date +%T)"
bash "$SB" "$OUT/s1" "leaderguard:30602:coop_leader_guard"
echo "######## STEP 2: the lever (want S143-CAL green: exactly LEVER_PREDICTED red) $(date +%T)"
bash "$SB" "$OUT/s2" "leaderguard_lever:30602:coop_leader_guard:COOP_CALIBRATE=1"
echo "######## STEP 3: BLOCK A (selftest role) $(date +%T)"
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
echo "######## STEP 4: the s139-s141 dress bench, every leg (GhostAs auto), then I + G + S + F with GhostAs blank $(date +%T)"
bash "$SB" "$OUT/d" "selfdress:250:coop_self_dress"
bash "$NB" "$OUT/d" "selfdress_noghost:250:coop_self_dress:COOP_DRESS_LEGS=I+G+S+F"
echo "######## STEP 5: the s139-s141 duo G9 (the host's transport site; GuestSlots 2 / 4 / 0 on COOPPARTY) $(date +%T)"
PYTHONIOENCODING=utf-8 py tools/harness/duo.py studies/test-harness/scenarios/coop_dress_wire.py > "$OUT/t/duo_g9.txt" 2>&1; echo "duo exit $?"
grep -E "^duo .*checks passed|\[duo\] (PASS|FAIL)  S1(39|4[01])" "$OUT/t/duo_g9.txt" | cut -c1-300
echo "######## STEP 6: an s143 host tape (its own dir: latest.json of the default home untouched) $(date +%T)"
env COOP_TAPE_DIR="$(cygpath -w "$DRESSDIR")" PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_tape_record.py > "$OUT/t/tape_record.txt" 2>&1
grep -E "checks passed|^  FAIL|REC-F" "$OUT/t/tape_record.txt" | cut -c1-220
NEWTAPE=$(ls -t "$DRESSDIR"/*.f9tape 2>/dev/null | head -1)
echo "tape: $NEWTAPE"
if [ -n "$NEWTAPE" ]; then
  PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py dress "$(cygpath -m "$NEWTAPE")" --ghost-as auto --guest-slots 2 --leader 0 > "$OUT/t/tape_dress.txt" 2>&1; echo "dress check exit $?"
  tail -5 "$OUT/t/tape_dress.txt" | cut -c1-240
fi
echo "######## STEP 6b: an s143 host tape on the PLANT BRAIN SEAT (its own dir) $(date +%T)"
SEATDIR=/c/gd/Dream-World-IX/.harness-runs/coop-tapes/seat-s143
mkdir -p "$SEATDIR"
env COOP_TAPE_SEAT=30607 COOP_TAPE_DIR="$(cygpath -w "$SEATDIR")" PYTHONIOENCODING=utf-8 py tools/play.py studies/test-harness/scenarios/coop_tape_record.py > "$OUT/t/tape_seat.txt" 2>&1
grep -E "checks passed|^  FAIL|REC-F|party seat" "$OUT/t/tape_seat.txt" | cut -c1-220
SEATTAPE=$(ls -t "$SEATDIR"/*-seat30607-*.f9tape 2>/dev/null | head -1)
echo "seat tape: $SEATTAPE"
if [ -n "$SEATTAPE" ]; then
  T="$(cygpath -m "$SEATTAPE")"
  PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py offer "$T" --want 4 > "$OUT/t/offer4.txt" 2>&1; echo "offer --want 4 exit $? (want 0: the guarded offer)"
  PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py offer "$T" --want 2 > "$OUT/t/offer2.txt" 2>&1; echo "offer --want 2 exit $? (want 1)"
  PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py dress "$T" --ghost-as auto --guest-slots 2 --leader 0 > "$OUT/t/dress_leader.txt" 2>&1; echo "dress --leader 0 exit $? (want 0: 08 00 01, Vivi)"
  PYTHONIOENCODING=utf-8 py tools/harness/coop_peer.py dress "$T" --ghost-as auto --guest-slots 2 > "$OUT/t/dress_raw.txt" 2>&1; echo "dress (positional) exit $? (want 1)"
  tail -3 "$OUT/t/offer4.txt" "$OUT/t/dress_leader.txt" | cut -c1-240
fi
echo "INI after the recordings $(sha256sum "$G/Memoria.ini" | cut -c1-16)"
echo "######## STEP 7: TAPE + BLOCK C $(date +%T)"
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
