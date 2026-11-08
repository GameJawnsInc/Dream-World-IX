#!/usr/bin/env bash
# s168 ROUND GM -- THE GUEST'S MAIN MENU, RUNG 0 (view only): the runners' shared preconditions, leg launcher and summary (sourced by
# round_gm_old.sh / round_gm_new.sh / round_gm_lever.sh / round_gm_regress.sh / round_gm_rerun.sh). s167's round-B library
# (studies/world-coop/s167/round_b_lib.sh), copied and re-keyed for s168: one leg per launch, each to its own log in ONE named folder, a
# summary log beside them. WRITTEN, NOT RUN by its builder: the bench runs on the operator's word (studies/field-coop/S168-DESIGN.md "The
# bench", its Order) -- OLD before any s168-family deploy, BRACKET on the pinned W1a/b build, NEW / LEVER / REGRESS after the s168 deploy.
# THE LAWS IT ENFORCES (S166-HANDOFF.md "Preconditions for any bench" and round B's, kept):
#   * NEVER BENCH UNDER A RUNNING TEST SUITE: harness.benchguard (no pytest / xdist, no nightly-gate lock) before the script and every leg
#   * FF9 CLOSED before every launch (a launch after a build: the build auto-deploys over the install a running game holds)
#   * THE OWNER'S BRIDGE (127.0.0.1:49201) DOWN for every T2 leg -- the script REFUSES; it never stops the owner's bridge
#   * SOLO legs under solo_ini.py (Enabled 0 + FollowHost 1 written BEFORE launch, restored byte-exact: THE FORCED-ROLE PIN; THE SELFTEST
#     ROLE REFUSES A LIVE INI) -- round A's script, which resolves its own worktree
#   * THE DLL PIN, by kind (the live x64 Assembly-CSharp.dll's sha256, first 16):
#       old      the deployed s167 12be3220520813a6 (ROUND_GM_DLL overrides) -- every OLD row is MEASURED there, before s168 replaces it
#       bracket  the pinned W1a/b build 532486364ec05354 (label pin-s168w1ab: GM0-BRACKET, the Order's step 2; ROUND_GM_DLL overrides)
#       new      the s168 build: neither of those (ROUND_GM_DLL pins it exactly)
#   * A CUTOFF BEFORE THE NIGHTLY GATE: no leg STARTS from ROUND_GM_NOT_AFTER until ROUND_GM_NOT_BEFORE (default 0230 -> 0700, wrapping
#     midnight: THE s159 LAW's 03:00 and the scheduled task's 04:00 run, tools/nightly_gate.md; `off` disables); the refusal names the leg
#     to resume from (ROUND_GM_FROM)
#   * DUO PORTS CLEAR OF THE EXCLUDED RANGE: before any launch, every port a leg of this run binds -- the duo's bridge ports, its relay
#     port, the regression peer port, the T2 world port, and on REGRESS coop_ramp_title's 49243 and coop_host_code's 49245 / 49246 -- is
#     checked against `netsh int ipv4 show excludedportrange protocol=tcp` and a 127.0.0.1 probe (a bind with no listen, a connect; never
#     Any): Parsec held 49211 on 11-04, Windows excluded 49252-49351
#   * THE PROOF BLOCK: every solo leg's Memoria.log proof block is kept beside its log (<log>.proofs); OLD records s167's as the reference
#     (ROUND_GM_REF); BRACKET / NEW / REGRESS judge theirs against it at the end (round_gm_guard.py proofdiff: only the round's movers --
#     the seat bracket line, and on s168 the guest menu and world walk lines -- may move; the diorama seat / containment lines and the
#     main menu refusal selftest's 14 rows must be identical)
#   * THE STAGE'S SOURCES: FF9_S168_CLONE (default the shared clone) names the s168 source every s168 judge derives its tallies from;
#     FF9_S167_CLONE is NEVER defaulted -- the shared clone carries s168 now, so the s167 source is the s167 patch's post-image -- and a
#     FF9_S167_CLONE that names an s168 source is refused
# THE OPTIONS, all on the leg counter [N] the summary prints:
#   ROUND_GM_FROM=N          skip legs 1..N-1 (resume a stopped run; each skipped leg is said in the summary)
#   ROUND_GM_NOT_AFTER=HHMM  ROUND_GM_NOT_BEFORE=HHMM   the gate window (default 0230 / 0700; `off` disables)
#   ROUND_GM_DLL=<sha16>     pin the build under test (OLD / BRACKET: overrides their pin)
#   ROUND_GM_DUO_PORTS=H,G   the duo's two bridge ports (duo.py --bridge-ports; default its 49211,49212); round B's ROUND_B_DUO_PORTS and
#                            round A's ROUND_A_DUO_PORTS are honoured when it is unset
#   ROUND_GM_RELAY_PORT=P    the duo's relay port (duo.py --relay-port; default its 7787)
#   ROUND_GM_PEER_PORT=P     the regression runner's coop_climb_anim_peer port (COOP_PEER_PORT; default 49257); ROUND_B_ / ROUND_A_ honoured
#   ROUND_GM_ROOTS=<dir>     the duo's instance roots' home (default /c/gd/ff9-inst: host/, guest/) -- read only, for FadeDuration
#   ROUND_GM_REF=<file>      the s167 proof block (default .harness-runs/s168-round-gm/s167-proof-block.txt; OLD writes it)
#   ROUND_GM_LOGS=<dir>      the run folder (default .harness-runs/s168-round-gm/<stamp>-<kind>)
#   ROUND_GM_PLAN=1          THE PLAN: print every leg's [N], name, route and command and launch NOTHING -- no guard, no DLL read, no
#                            install read (GM0-SOFTRESET's precondition assumed met, the roots at 40 ms, no b3 tape unless
#                            ROUND_GM_PLAN_TAPE names one); the run folder a fresh temp dir unless ROUND_GM_LOGS names one. The offline
#                            tests read the runners through it (tests/test_coop_guest_menu_runners.py)
set -u
WT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$WT" || exit 9
SC=studies/test-harness/scenarios
GUARD="py studies/field-coop/s168/round_gm_guard.py"
SOLO="py studies/world-coop/s166-handoff/solo_ini.py"
DUO_PORTS="${ROUND_GM_DUO_PORTS:-${ROUND_B_DUO_PORTS:-${ROUND_A_DUO_PORTS:-}}}"
PEER_PORT="${ROUND_GM_PEER_PORT:-${ROUND_B_PEER_PORT:-${ROUND_A_PEER_PORT:-}}}"
RELAY_PORT="${ROUND_GM_RELAY_PORT:-}"
DUO="py tools/harness/duo.py${DUO_PORTS:+ --bridge-ports $DUO_PORTS}${RELAY_PORT:+ --relay-port $RELAY_PORT}"
GAME="${FF9_GAME:-/c/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX}"
ROOTS="${ROUND_GM_ROOTS:-/c/gd/ff9-inst}"
S167_DLL=12be3220520813a6
W1AB_DLL=532486364ec05354
NOT_AFTER="${ROUND_GM_NOT_AFTER:-0230}"
NOT_BEFORE="${ROUND_GM_NOT_BEFORE:-0700}"
GM_FIELD=30801
FARSHORE=6603
DIO_FIELD=30602
RUNS=/c/gd/Dream-World-IX/.harness-runs/s168-round-gm
REF="${ROUND_GM_REF:-$RUNS/s167-proof-block.txt}"
# THE STAGE'S SOURCES: GM0-PROOF, S167-W-PROOF and S166-A-PROOF on an s168 build want the s168 SOURCE's tallies (534 / 198, 19 / 7,
# 420 / 249 as built); the clone the build came from is named here (an explicit FF9_S168_CLONE wins). FF9_S167_CLONE stays as the caller
# set it (unset = the s167 patch's post-image: 532 / 196) -- preflight refuses one that names the s168 clone.
export FF9_S168_CLONE="${FF9_S168_CLONE:-C:/gd/FFIX/Memoria/Assembly-CSharp}"
STAMP="$(date +%Y%m%d-%H%M%S)"
PLAN="${ROUND_GM_PLAN:-0}"
if [ "$PLAN" = 1 ]; then
  RUN="${ROUND_GM_LOGS:-$(mktemp -d)}"
else
  RUN="${ROUND_GM_LOGS:-$RUNS/$STAMP-$ROUND_GM_KIND}"
fi
mkdir -p "$RUN" || exit 9
SUMMARY="$RUN/summary.log"
N=0
PROOF_LOGS=""

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

ini_of() {        # ini_of <Memoria.ini> <section> <key>: the value the engine obeys (READ-ONLY), or empty
  $GUARD ini "$1" "$2" "$3" 2>/dev/null | tr -d '\r'
}

gm_tape() {       # the COOP_TAPE_GUEST_MENU the T tape legs would replay, or empty (OWNER-GATED: recorded on an s168 host, Order step 4)
  if [ "$PLAN" = 1 ]; then echo "${ROUND_GM_PLAN_TAPE:-}"; return 0; fi
  $GUARD tape 2>/dev/null | tr -d '\r'
}

refuse() { say "!!! REFUSED: $*"; say "== stopped (nothing further launched)"; exit 3; }

bench_ports() {   # bench_ports <duo 0|1> <t2 0|1> <peer 0|1> [regress 0|1]: the ports this run's legs bind -- the duo's bridges and
  local d="${DUO_PORTS:-49211,49212}" out=""          # relay, the T2 world port (pb.WORLD_PORT), the regression's coop_climb_anim_peer port
  [ "$1" = 1 ] && out="${d//,/ } ${RELAY_PORT:-7787}"
  [ "$2" = 1 ] && out="$out 49231"
  [ "$3" = 1 ] && out="$out ${PEER_PORT:-49257}"
  # the regression's coop_ramp_title (COOP_PEER_PORT default 49243: the runner sets none for it) and coop_host_code (PORT_A 49245,
  # PORT_B 49246): each self-checks at run time too, but a shifted excluded range should refuse HERE, not hours into the run
  [ "$4" = 1 ] && out="$out 49243 49245 49246"
  echo $out
}

preflight() {   # preflight <old|bracket|new> [t2] [duo] [peer] [regress] -- t2 / duo / peer (coop_climb_anim_peer) / regress
  local kind="$1"; shift                              # (coop_ramp_title + coop_host_code's ports) when any such leg follows
  local t2=0 duo=0 peer=0 regress=0 a
  for a in "$@"; do
    [ "$a" = "t2" ] && t2=1
    [ "$a" = "duo" ] && duo=1
    [ "$a" = "peer" ] && peer=1
    [ "$a" = "regress" ] && regress=1
  done
  if [ "$PLAN" = 1 ]; then
    case "$kind" in old|bracket|new) ;; *) refuse "preflight: no kind '$kind' (old, bracket, new)" ;; esac
    say "== PLAN (nothing launched, nothing checked): s168 round GM $ROUND_GM_KIND; preflight $kind t2=$t2 duo=$duo peer=$peer regress=$regress"
    say "   PLAN: the port check would probe: $(bench_ports $duo $t2 $peer $regress)"
    return 0
  fi
  say "== s168 round GM $ROUND_GM_KIND -- $WT (branch $(git -C "$WT" rev-parse --abbrev-ref HEAD) $(git -C "$WT" rev-parse --short HEAD)); logs $RUN"
  local src rc
  src="$($GUARD sources 2>&1)"; rc=$?
  say "$src"
  [ "$rc" = 0 ] || refuse "FF9_S167_CLONE names the s168 clone (see above): unset it -- the s167 patch's post-image is the s167 source"
  say "   ports: duo ${DUO_PORTS:-49211,49212 (the duo.py default)}; relay ${RELAY_PORT:-7787 (the duo.py default)}; peer ${PEER_PORT:-49257 (the coop_climb_anim_peer default)}"
  guard_suite >>"$SUMMARY" 2>&1 || refuse "a test suite / the nightly gate is running (benchguard: see above)"
  $GUARD window "$(date +%H%M)" "$NOT_AFTER" "$NOT_BEFORE" >>"$SUMMARY" 2>&1 || refuse "inside the nightly gate's window (see above): start after ROUND_GM_NOT_BEFORE=$NOT_BEFORE"
  ff9_closed || refuse "FF9 is running -- close it first (a launch after a build must not race the install)"
  if [ "$t2" = 1 ]; then
    bridge_down || refuse "the owner's Workspace bridge is UP on 127.0.0.1:49201 -- a T2 guest launched on the owner's Memoria.ini dials it. Ask the owner to stop it; never stop it from a bench"
  fi
  if [ "$duo" = 1 ] || [ "$t2" = 1 ] || [ "$peer" = 1 ] || [ "$regress" = 1 ]; then
    # shellcheck disable=SC2046
    $GUARD ports $(bench_ports $duo $t2 $peer $regress) >>"$SUMMARY" 2>&1 || refuse "a bench port is excluded or held (THE EXCLUDED PORT RANGE: see above) -- pick others with ROUND_GM_DUO_PORTS / ROUND_GM_RELAY_PORT / ROUND_GM_PEER_PORT"
  fi
  local dll; dll="$(live_dll)"
  say "   the live DLL: $dll"
  case "$kind" in
    old)     [ "$dll" = "${ROUND_GM_DLL:-$S167_DLL}" ] || refuse "OLD runs on the deployed s167 ($S167_DLL; ROUND_GM_DLL overrides) -- the live DLL is $dll: OLD can no longer be measured once an s168-family DLL replaced it" ;;
    bracket) [ "$dll" = "${ROUND_GM_DLL:-$W1AB_DLL}" ] || refuse "BRACKET runs on the pinned W1a/b build ($W1AB_DLL, label pin-s168w1ab: py tools/restore_memoria_dll.py pin-s168w1ab after tools/backup_memoria_dll.py, FF9 closed, the owner's go) -- the live DLL is $dll" ;;
    new)     [ "$dll" != "$S167_DLL" ] || refuse "the live DLL is still s167's ($S167_DLL): deploy s168 first (after the owner's s167 two-PC look; FF9 closed, the owner's go)"
             [ "$dll" != "$W1AB_DLL" ] || refuse "the live DLL is the pinned W1a/b build ($W1AB_DLL): GM0-BRACKET's (ROUND_GM_SET=bracket), not s168's -- deploy the s168 build first"
             if [ -n "${ROUND_GM_DLL:-}" ] && [ "$dll" != "$ROUND_GM_DLL" ]; then refuse "the live DLL $dll is not ROUND_GM_DLL=$ROUND_GM_DLL"; fi ;;
    *)       refuse "preflight: no kind '$kind' (old, bracket, new)" ;;
  esac
}

summ() {   # name exit log
  say "== $1 exit $2"
  grep -E "checks passed|-CAL|S168-INI|S168-GMT-GATE|S168T-LEG|S168D-LEG|REFUSED|restore (OK|FAILED)|T2H?-INI|refusing to start|SWIRL-HANG" \
       "$RUN/$3" | cut -c1-300 | tail -6 | tee -a "$SUMMARY"
  grep -E "^\s+FAIL  " "$RUN/$3" | cut -c1-260 | head -14 | tee -a "$SUMMARY"
}

skip_leg() {   # skip_leg <name> <why>: a leg this run cannot launch, counted (the resume numbers stay stable) and NAMED, never hidden
  N=$((N + 1))
  say "-- [$N] $1: NOT RUN -- $2"
}

leg() {   # leg <name> <kind: solo|t2|duo> <log> -- <command...> (env set by the caller with `env A=B`)
  local name="$1" kind="$2" log="$3"; shift 4
  N=$((N + 1))
  if [ "$N" -lt "${ROUND_GM_FROM:-1}" ]; then say "-- [$N] $name: skipped (ROUND_GM_FROM=$ROUND_GM_FROM)"; return 0; fi
  if [ "$PLAN" = 1 ]; then say "-- [$N] $name ($kind): $*"; return 0; fi
  $GUARD window "$(date +%H%M)" "$NOT_AFTER" "$NOT_BEFORE" >/dev/null 2>&1 || \
    refuse "it is $(date +%H:%M), inside the nightly gate's window $NOT_AFTER-$NOT_BEFORE (ROUND_GM_NOT_AFTER / ROUND_GM_NOT_BEFORE) -- resume with ROUND_GM_FROM=$N"
  guard_suite >/dev/null 2>&1 || refuse "a test suite started under the run (before leg $N: $name)"
  ff9_closed || refuse "FF9 is still running before leg $N ($name) -- the previous launch did not close it"
  if [ "$kind" = "t2" ]; then bridge_down || refuse "the owner's bridge came UP before leg $N ($name)"; fi
  say "-- [$N] $name ($kind): $*"
  local t0; t0="$(date +%s)"
  "$@" >"$RUN/$log" 2>&1
  local rc=$?
  summ "[$N] $name" $rc "$log"
  if [ "$kind" = "solo" ]; then
    $GUARD proofs "$GAME" "$t0" "$RUN/$log.proofs" >>"$SUMMARY" 2>&1 && PROOF_LOGS="$PROOF_LOGS $log.proofs"
  fi
}

fade_ok() {   # 0 = both instance roots read [Interface] FadeDuration >= 300 (the FadeDuration-300 duo rows; READ-ONLY -- no writer exists)
  [ "$PLAN" = 1 ] && return 1
  local h g
  h="$(ini_of "$ROOTS/host/Memoria.ini" Interface FadeDuration)"
  g="$(ini_of "$ROOTS/guest/Memoria.ini" Interface FadeDuration)"
  [ -n "$h" ] && [ -n "$g" ] && [ "${h//[!0-9]/}" = "$h" ] && [ "${g//[!0-9]/}" = "$g" ] && [ "$h" -ge 300 ] && [ "$g" -ge 300 ]
}

softreset_ok() {   # 0 = the install obeys [Control] SoftReset 1 and [Cheats] Enabled 1 (GM0-SOFTRESET's precondition; READ-ONLY)
  [ "$PLAN" = 1 ] && return 0
  [ "$(ini_of "$GAME/Memoria.ini" Control SoftReset)" = "1" ] && [ "$(ini_of "$GAME/Memoria.ini" Cheats Enabled)" = "1" ]
}

proof_reference() {   # OLD: the first solo leg's proof block becomes s167's reference (only on the deployed s167: preflight old pinned it)
  if [ "$PLAN" = 1 ]; then say "== PLAN: proof_reference (the first solo leg's block -> $REF)"; return 0; fi
  local first
  first="$(echo "$PROOF_LOGS" | awk '{print $1}')"
  if [ -z "$first" ] || [ ! -s "$RUN/$first" ]; then say "== NO s167 proof block captured (no solo leg wrote one): the reference $REF is unchanged"; return 0; fi
  mkdir -p "$(dirname "$REF")" && cp "$RUN/$first" "$REF" && say "== s167's proof block ($first) recorded as the reference: $REF"
}

proof_report() {   # proof_report <bracket|new>: every solo leg's block against s167's reference -- only the round's movers may move
  if [ "$PLAN" = 1 ]; then say "== PLAN: proof_report $1 (every solo leg's block against $REF)"; return 0; fi
  local p red=0
  [ -n "$PROOF_LOGS" ] || { say "== proof blocks: none captured (no solo leg ran)"; return 0; }
  say "== THE PROOF BLOCK against s167's ($REF), kind $1:"
  for p in $PROOF_LOGS; do
    $GUARD proofdiff "$REF" "$RUN/$p" "$1" >>"$SUMMARY" 2>&1 || red=$((red + 1))
  done
  tail -n 200 "$SUMMARY" | grep -E "^   proof block " | tail -n 40
  say "== proof blocks: $red RED of $(echo $PROOF_LOGS | wc -w) (each RED line names its head; NOTE lines are read, not judged)"
}
