#!/usr/bin/env bash
# s166 ROUND A -- the runners' shared preconditions, leg launcher and summary (sourced by round_a_old.sh / round_a_new.sh /
# round_a_lever.sh / round_a_regress.sh). One leg per launch, each to its own log in ONE named folder, a summary log beside them.
# THE LAWS IT ENFORCES (S166-HANDOFF.md "Preconditions for any bench"):
#   * NEVER BENCH UNDER A RUNNING TEST SUITE: harness.benchguard (no pytest / xdist, no nightly-gate lock) before the script and every leg
#   * FF9 CLOSED before every launch (a launch after a build: the build auto-deploys over the install a running game holds)
#   * THE OWNER'S BRIDGE (127.0.0.1:49201) DOWN for every T2 leg -- the script REFUSES; it never stops the owner's bridge
#   * SOLO legs under solo_ini.py (Enabled 0 + FollowHost 1 written BEFORE launch, restored byte-exact: THE FORCED-ROLE PIN)
#   * the deployed DLL is the one the script is for (OLD: A0b 9e4365349fab02b1; NEW / LEVER: anything else, or ROUND_A_DLL exactly)
# TWO OPTIONS, both on the leg counter [N] the summary prints:
#   ROUND_A_NOT_AFTER=HHMM  start no leg at or after that local time (stay clear of the 03:00 nightly gate: THE s159 LAW); the
#                           refusal names the leg to resume from
#   ROUND_A_FROM=N          skip legs 1..N-1 (resume a stopped run; each skipped leg is said in the summary)
set -u
WT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$WT" || exit 9
SC=studies/test-harness/scenarios
SOLO="py studies/world-coop/s166-handoff/solo_ini.py"
GAME="${FF9_GAME:-/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX}"
A0B_DLL=9e4365349fab02b1
# [W2 critic] A-PROOF's EXACT tallies: the solo legs read them off the s166 source (fakegame.world_walk_engine_source: $FF9_S166_CLONE,
# else the s166 patch on this branch's memoria-patches/). Until W3 emits that patch neither is there and the judge falls back to "above
# A0b's 84 / 13" -- a proof of ANY larger table passes. So the clone the W1+W2 build came from is named here (an explicit
# FF9_S166_CLONE wins); it must still be the built source (this session holds the clone per the round queue).
export FF9_S166_CLONE="${FF9_S166_CLONE:-C:/gd/FFIX/Memoria/Assembly-CSharp}"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN="${ROUND_A_LOGS:-/c/gd/Dream-World-IX/.harness-runs/s166-round-a/$STAMP-$ROUND_A_KIND}"
mkdir -p "$RUN" || exit 9
SUMMARY="$RUN/summary.log"
N=0

say() { echo "$*" | tee -a "$SUMMARY"; }

live_dll() {
  py -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest()[:16])" \
     "$GAME/x64/FF9_Data/Managed/Assembly-CSharp.dll" 2>/dev/null || echo unreadable
}

guard_suite() {   # 0 = clear; prints the refusal otherwise
  py - <<'EOF'
import sys
sys.path.insert(0, "tools")
from harness.benchguard import bench_blockers, refuse_message
refusals, notes = bench_blockers()
for n in notes:
    print("  note:", n)
if refusals:
    print(refuse_message(refusals))
    sys.exit(1)
EOF
}

ff9_closed() {
  py -c "import subprocess,sys; o=subprocess.run(['tasklist','/FI','IMAGENAME eq FF9.exe'],capture_output=True,text=True).stdout; sys.exit(1 if 'FF9.exe' in o else 0)"
}

bridge_down() {   # 0 = the owner's bridge is DOWN (nothing accepts on 127.0.0.1:49201)
  py -c "import socket,sys; s=socket.socket(); s.settimeout(0.5); r=s.connect_ex(('127.0.0.1',49201)); s.close(); sys.exit(0 if r!=0 else 1)"
}

refuse() { say "!!! REFUSED: $*"; say "== stopped (nothing further launched)"; exit 3; }

preflight() {   # $1 = old | new ; $2 = "t2" when any T2 leg follows
  say "== s166 round A $ROUND_A_KIND -- $WT (branch $(git -C "$WT" rev-parse --abbrev-ref HEAD) $(git -C "$WT" rev-parse --short HEAD)); logs $RUN"
  say "   A-PROOF's tallies from FF9_S166_CLONE=$FF9_S166_CLONE: $(py -c "import sys; sys.path.insert(0, 'tools'); from harness import battlewire as BW, fakegame as FG; s = FG.world_walk_engine_source(); print(BW.world_walk_proof_counts(s) if s else 'NO s166 source (the judge falls back to above 84 / 13)')" 2>&1 | tail -1)"
  guard_suite >>"$SUMMARY" 2>&1 || refuse "a test suite / the nightly gate is running (benchguard: see above)"
  ff9_closed || refuse "FF9 is running -- close it first (a launch after a build must not race the install)"
  if [ "${2:-}" = "t2" ]; then
    bridge_down || refuse "the owner's Workspace bridge is UP on 127.0.0.1:49201 -- a T2 guest launched on the owner's Memoria.ini dials it. Ask the owner to stop it; never stop it from a bench"
  fi
  local dll; dll="$(live_dll)"
  say "   the live DLL: $dll"
  if [ "$1" = "old" ]; then
    [ "$dll" = "${ROUND_A_DLL:-$A0B_DLL}" ] || refuse "OLD runs on the deployed A0b ($A0B_DLL; ROUND_A_DLL overrides) -- the live DLL is $dll"
  else
    [ "$dll" != "$A0B_DLL" ] || refuse "the live DLL is still A0b's ($A0B_DLL): build + deploy W1+W2 first (py tools/build_memoria.py, the owner's go)"
    if [ -n "${ROUND_A_DLL:-}" ] && [ "$dll" != "$ROUND_A_DLL" ]; then refuse "the live DLL $dll is not ROUND_A_DLL=$ROUND_A_DLL"; fi
  fi
}

summ() {   # name exit log
  say "== $1 exit $2"
  grep -E "checks passed|-CAL|S166-T2-LEG|S166-T2-LEVER|REFUSED|restore (OK|FAILED)|T2H?-INI|refusing to start" "$RUN/$3" | cut -c1-300 | tail -6 | tee -a "$SUMMARY"
  grep -E "^\s+FAIL  " "$RUN/$3" | cut -c1-260 | head -14 | tee -a "$SUMMARY"
}

leg() {   # leg <name> <kind: solo|t2|duo|plain> <log> -- <command...> (env set by the caller with `env A=B`)
  local name="$1" kind="$2" log="$3"; shift 4
  N=$((N + 1))
  if [ "$N" -lt "${ROUND_A_FROM:-1}" ]; then say "-- [$N] $name: skipped (ROUND_A_FROM=$ROUND_A_FROM)"; return 0; fi
  if [ -n "${ROUND_A_NOT_AFTER:-}" ] && [ "$((10#$(date +%H%M)))" -ge "$((10#$ROUND_A_NOT_AFTER))" ]; then
    refuse "it is $(date +%H:%M), past ROUND_A_NOT_AFTER=$ROUND_A_NOT_AFTER (the nightly gate's window) -- resume with ROUND_A_FROM=$N"
  fi
  guard_suite >/dev/null 2>&1 || refuse "a test suite started under the run (before leg $N: $name)"
  ff9_closed || refuse "FF9 is still running before leg $N ($name) -- the previous launch did not close it"
  if [ "$kind" = "t2" ]; then bridge_down || refuse "the owner's bridge came UP before leg $N ($name)"; fi
  say "-- [$N] $name ($kind): $*"
  "$@" >"$RUN/$log" 2>&1
  summ "[$N] $name" $? "$log"
}
