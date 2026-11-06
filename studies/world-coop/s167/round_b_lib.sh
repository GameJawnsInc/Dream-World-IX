#!/usr/bin/env bash
# s167 ROUND B -- the runners' shared preconditions, leg launcher and summary (sourced by round_b_old.sh / round_b_new.sh /
# round_b_lever.sh / round_b_regress.sh). Round A's guard library (studies/world-coop/s166-handoff/round_a_lib.sh), copied and re-keyed
# for round B: one leg per launch, each to its own log in ONE named folder, a summary log beside them.
# THE LAWS IT ENFORCES (S166-HANDOFF.md "Preconditions for any bench", unchanged for round B):
#   * NEVER BENCH UNDER A RUNNING TEST SUITE: harness.benchguard (no pytest / xdist, no nightly-gate lock) before the script and every leg
#   * FF9 CLOSED before every launch (a launch after a build: the build auto-deploys over the install a running game holds)
#   * THE OWNER'S BRIDGE (127.0.0.1:49201) DOWN for every T2 leg -- the script REFUSES; it never stops the owner's bridge
#   * SOLO legs under solo_ini.py (Enabled 0 + FollowHost 1 written BEFORE launch, restored byte-exact: THE FORCED-ROLE PIN; THE SELFTEST
#     ROLE REFUSES A LIVE INI) -- round A's script, which resolves its own worktree
#   * the deployed DLL is the one the script is for (OLD: the live s166 b24e0123ac93960c; NEW / LEVER / REGRESS: anything else, or
#     ROUND_B_DLL exactly)
# THE OPTIONS, all on the leg counter [N] the summary prints:
#   ROUND_B_NOT_AFTER=HHMM  start no leg at or after that local time (stay clear of the 03:00 nightly gate: THE s159 LAW); the
#                           refusal names the leg to resume from
#   ROUND_B_FROM=N          skip legs 1..N-1 (resume a stopped run; each skipped leg is said in the summary)
#   ROUND_B_DLL=<sha16>     pin the build under test (OLD: overrides the s166 pin)
#   ROUND_B_DUO_PORTS=H,G   the duo's two bridge ports (duo.py --bridge-ports; default its 49211,49212) -- THE EXCLUDED PORT RANGE: an
#                           OS-assigned ephemeral port of another program (Parsec held 49211 on 11-04) refuses every duo leg at C0.
#                           Round A's ROUND_A_DUO_PORTS is honoured when ROUND_B_DUO_PORTS is unset
#   ROUND_B_PEER_PORT=P     the regress runner's coop_climb_anim_peer bench port (its COOP_PEER_PORT; default 49257) -- Windows excluded
#                           49252-49351 on 11-04 (WinError 10013 at W0); round A's ROUND_A_PEER_PORT is honoured when unset
#   ROUND_B_LOGS=<dir>      the run folder (default .harness-runs/s167-round-b/<stamp>-<kind>)
set -u
WT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$WT" || exit 9
SC=studies/test-harness/scenarios
SOLO="py studies/world-coop/s166-handoff/solo_ini.py"
DUO_PORTS="${ROUND_B_DUO_PORTS:-${ROUND_A_DUO_PORTS:-}}"
PEER_PORT="${ROUND_B_PEER_PORT:-${ROUND_A_PEER_PORT:-}}"
DUO="py tools/harness/duo.py${DUO_PORTS:+ --bridge-ports $DUO_PORTS}"
GAME="${FF9_GAME:-/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX}"
S166_DLL=b24e0123ac93960c
# S167-W-PROOF / round A's A-PROOF on an s167 build want the s167 SOURCE's exact tallies (fakegame.world_walk_engine_source(stage=167):
# $FF9_S167_CLONE carrying the s167 tag, else the s167 patch on this branch's memoria-patches/). Until W3 emits that patch only the clone
# holds it, so the clone the build came from is named here (an explicit FF9_S167_CLONE wins); it must still be the BUILT source. Without
# any source the judges fall back to "above s166's 323 / 110".
export FF9_S167_CLONE="${FF9_S167_CLONE:-C:/gd/FFIX/Memoria/Assembly-CSharp}"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN="${ROUND_B_LOGS:-/c/gd/Dream-World-IX/.harness-runs/s167-round-b/$STAMP-$ROUND_B_KIND}"
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
  say "== s167 round B $ROUND_B_KIND -- $WT (branch $(git -C "$WT" rev-parse --abbrev-ref HEAD) $(git -C "$WT" rev-parse --short HEAD)); logs $RUN"
  say "   the s167 proof's tallies from FF9_S167_CLONE=$FF9_S167_CLONE: $(py -c "import sys; sys.path.insert(0, 'tools'); from harness import battlewire as BW, fakegame as FG; s = FG.world_walk_engine_source(stage=167); print(BW.world_walk_proof_counts(s) if s else 'NO s167 source (the judges fall back to above 323 / 110)')" 2>&1 | tail -1)"
  say "   ports: duo ${DUO_PORTS:-duo.py's default}; peer ${PEER_PORT:-coop_climb_anim_peer's default}"
  guard_suite >>"$SUMMARY" 2>&1 || refuse "a test suite / the nightly gate is running (benchguard: see above)"
  ff9_closed || refuse "FF9 is running -- close it first (a launch after a build must not race the install)"
  if [ "${2:-}" = "t2" ]; then
    bridge_down || refuse "the owner's Workspace bridge is UP on 127.0.0.1:49201 -- a T2 guest launched on the owner's Memoria.ini dials it. Ask the owner to stop it; never stop it from a bench"
  fi
  local dll; dll="$(live_dll)"
  say "   the live DLL: $dll"
  if [ "$1" = "old" ]; then
    [ "$dll" = "${ROUND_B_DLL:-$S166_DLL}" ] || refuse "OLD runs on the deployed s166 ($S166_DLL; ROUND_B_DLL overrides) -- the live DLL is $dll"
  else
    [ "$dll" != "$S166_DLL" ] || refuse "the live DLL is still s166's ($S166_DLL): build + deploy s167 first (py tools/build_memoria.py, FF9 closed, the owner's go)"
    if [ -n "${ROUND_B_DLL:-}" ] && [ "$dll" != "$ROUND_B_DLL" ]; then refuse "the live DLL $dll is not ROUND_B_DLL=$ROUND_B_DLL"; fi
  fi
}

summ() {   # name exit log
  say "== $1 exit $2"
  grep -E "checks passed|-CAL|S16[67]-T2-LEG|S16[67]-T2-LEVER|S167-INI|REFUSED|restore (OK|FAILED)|T2H?-INI|refusing to start|SWIRL-HANG" \
       "$RUN/$3" | cut -c1-300 | tail -6 | tee -a "$SUMMARY"
  grep -E "^\s+FAIL  " "$RUN/$3" | cut -c1-260 | head -14 | tee -a "$SUMMARY"
}

leg() {   # leg <name> <kind: solo|t2|duo|plain> <log> -- <command...> (env set by the caller with `env A=B`)
  local name="$1" kind="$2" log="$3"; shift 4
  N=$((N + 1))
  if [ "$N" -lt "${ROUND_B_FROM:-1}" ]; then say "-- [$N] $name: skipped (ROUND_B_FROM=$ROUND_B_FROM)"; return 0; fi
  if [ -n "${ROUND_B_NOT_AFTER:-}" ] && [ "$((10#$(date +%H%M)))" -ge "$((10#$ROUND_B_NOT_AFTER))" ]; then
    refuse "it is $(date +%H:%M), past ROUND_B_NOT_AFTER=$ROUND_B_NOT_AFTER (the nightly gate's window) -- resume with ROUND_B_FROM=$N"
  fi
  guard_suite >/dev/null 2>&1 || refuse "a test suite started under the run (before leg $N: $name)"
  ff9_closed || refuse "FF9 is still running before leg $N ($name) -- the previous launch did not close it"
  if [ "$kind" = "t2" ]; then bridge_down || refuse "the owner's bridge came UP before leg $N ($name)"; fi
  say "-- [$N] $name ($kind): $*"
  "$@" >"$RUN/$log" 2>&1
  summ "[$N] $name" $? "$log"
}
