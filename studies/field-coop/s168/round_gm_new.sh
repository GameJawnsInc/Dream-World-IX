#!/usr/bin/env bash
# s168 ROUND GM -- NEW, on the s168 build (deployed after the owner's s167 two-PC look), in the design's Order (S168-DESIGN.md "The bench",
# Order step 3, then step 5): GM0-PROOF (GM0-OFFLINE is the offline suite, run by the session before this, not a launch); GM0-HOLE and
# GM0-STALL-WHO; the key and seat rows; the census and restore rows; the close rows ONE TRIGGER AT A TIME (each leg fires one trigger;
# `close old` is their lever, round_gm_lever.sh); the measuring rows (GM0-BW, GM0-TIMING, GM0-STSCENE, GM0-HUDSTRIP, GM0-DIALOG-PATH);
# the T rows; GM0-QUIT-EXIT LAST (destructive: the process exits). Then round_gm_lever.sh, then round_gm_regress.sh. One leg per launch;
# every row green is the verdict (each launch's "checks passed" line in summary.log), but for the rows each scenario names unrun: the
# solo bench's in-game unknowns read "not reached" (never a pass), the duo's configuration rows "not run (configuration)" out of the CAL.
#   bash studies/field-coop/s168/round_gm_new.sh            (ROUND_GM_DLL=<sha16> pins the build under test)
# OWNER-GATED, NOT HERE: COOP_TAPE_GUEST_MENU's recording (coop_tape_record.py's GUEST-MENU variant, COOP_TAPE_GUEST_MENU=1 with
# COOP_TAPE_GUEST_MENU_OWNER=1 -- the owner's go, never set by a runner; the Order's step 4) -- until it exists the T `tape` legs are NOT
# RUN (S168-GMT-GATE stays red, named below) and their rows run on the duo (FREEZE-D, STALL-VIEW-D, RAMP-FIELD-D, RAMP-WORLD-D); the
# two-PC look (the owner's). NAMED, NOT REACHED BY ANY LEG: GM0-LOAD (no Alt+F9 verb), GM0-DEATH (a kill + relaunch), GM0-CUT-NOBOOT, the
# guest's quit prompt on a duo past the WM_CLOSE fallback (GM0-CUT-QUIT, GM0-QUIT-D run on that fallback in the cut / rampquit legs,
# proven in game by the 2026-11-08 reruns; no any-role verb, so a "not run" there is an OPEN ITEM said after the duo closes), the RAMP
# press legs (a FadeDuration above the 2 s config poll).
# FadeDuration 300: GM0-KEY-DOUBLE and GM0-FADE's 300 half need [Interface] FadeDuration >= 300 on BOTH instance roots -- at 40 ms those
# rows read "not run (configuration)"; the 300 pass is a second `key` / `leave` launch:
# ROUND_GM_FADE=300 ROUND_GM_RERUN="new:duo:key new:duo:leave" bash studies/field-coop/s168/round_gm_rerun.sh (a hand edit of a root is
# regenerated away by Instance.ensure at every duo start; ROUND_GM_FADE rides every duo as duo.py --root-ini). GM0-DOOR-D has its own
# `door` leg at FadeDuration >= 800 (S168-DESIGN R5): ROUND_GM_FADE=800 ROUND_GM_RERUN="new:duo:door". Step 6b says which ran.
ROUND_GM_KIND=new
. "$(dirname "$0")/round_gm_lib.sh"
preflight new t2 duo
solo() {   # solo <leg>: one solo leg on the bench field (the world leg on 6603)
  local f=$GM_FIELD
  [ "$1" = "world" ] && f=$FARSHORE
  leg "solo $1" solo "new_solo_$1.log" -- env COOP_GM_LEG=$1 $SOLO s168-gm-$1 -- py tools/play.py $SC/coop_guest_menu.py --field $f
}
duo() {    # duo <leg> [label] [duo.py options...]
  local l="$1" tag="${2:-$1}"; shift 2 2>/dev/null || shift
  leg "duo $tag" duo "new_duo_$tag.log" -- env COOP_GMD_LEG=$l $DUO "$@" $SC/coop_guest_menu_duo.py
}
t2() {     # t2 <leg> [env...]
  local l="$1"; shift
  leg "T2 $l${*:+ $*}" t2 "new_t2_$l${1:+_${1##*=}}.log" -- env COOP_GMT_LEG=$l "$@" py tools/play.py $SC/coop_guest_menu_duo.py
}

# 1. THE PROOF (GM0-PROOF: the three lines in order, MenuRefusalSelfTest at 14; the probe) -- every solo leg's setup carries it too
solo proof
# 2. THE HOLE (an unmirrored world-paired guest refused 'not_mirroring'; still refused in a 3 s stall)
t2 hole
# 3. THE KEY AND THE SEAT (the duo's key path on a MIRRORING guest; the solo bench's seat from a two-marker frame)
duo key
solo seat
# 4. THE CENSUS AND THE RESTORE (refuse, the in-game deep sites, the whys, the witness / seat faults, the doors), the holds and release
for l in refuse deep why witness door held master diorama release; do
  solo $l
done
# 5. THE CLOSES, ONE TRIGGER AT A TIME: the solo actions (fireclose, the quit prompt, the config edge, the soft reset), then each real
#    trigger on the duo, then the world (the solo settle stamp and the duo's walking / frozen / aboard legs)
solo close
solo quit
solo cfg
if softreset_ok; then
  solo softreset
else
  skip_leg "solo softreset" "the install lacks [Control] SoftReset 1 / [Cheats] Enabled 1 (GM0-SOFTRESET's precondition: set them by hand, then rerun it)"
fi
for l in leave door out rejoin ramp rampquit cut title scene chest stall; do   # rampquit before cut: the first WM_CLOSE runs alone
  duo $l
done
say "   GM0-QUIT-D (and GM0-CUT-QUIT's prompt half): no any-role quit-prompt verb (\`endbench quit on\` is the selftest role's), so the legs ride the WM_CLOSE"
say "   fallback (proven in game by the 2026-11-08 reruns) -- a 'not run (configuration)' there is an OPEN ITEM, never a pass; its two-PC route is B32"
solo world
duo world
# 6. THE CAPS AND THE MEASURING ROWS (GM0-CAPS-a, the paired line, GM0-BW on LAN and on the relay; the dialogue path, the HUD strip)
duo caps
duo caps caps_relay --topology relay
duo dialog
duo hudstrip
# 6b. FadeDuration: every duo leg above ran at ROUND_GM_FADE (duo.py --root-ini on both roots) or, unset, the roots' own fade; the other
#     half is a SECOND pass of `key` and `leave`, and GM0-DOOR-D's own pass is the `door` leg at 800
if fade_ok; then
  say "   ROUND_GM_FADE=$ROUND_GM_FADE (>= 300, on both roots through duo.py --root-ini): this run is the 300 pass (GM0-KEY-DOUBLE and"
  say "   GM0-FADE's 300 half ran); the 40 half: ROUND_GM_RERUN=\"new:duo:key new:duo:leave\" bash studies/field-coop/s168/round_gm_rerun.sh"
  say "   with ROUND_GM_FADE unset"
else
  say "   the duos ran below FadeDuration 300 (ROUND_GM_FADE ${ROUND_GM_FADE:-unset}): GM0-KEY-DOUBLE and GM0-FADE's 300 half read"
  say "   'not run (configuration)'. The 300 pass: ROUND_GM_FADE=300 ROUND_GM_RERUN=\"new:duo:key new:duo:leave\" bash"
  say "   studies/field-coop/s168/round_gm_rerun.sh (a hand edit of a root is regenerated away by Instance.ensure at every duo start)"
fi
if fade_door_ok; then
  say "   GM0-DOOR-D ran on its own door leg (ROUND_GM_FADE=$ROUND_GM_FADE >= 800)"
else
  say "   GM0-DOOR-D read 'not run (configuration)' (its door leg needs FadeDuration >= 800). The door pass: ROUND_GM_FADE=800"
  say "   ROUND_GM_RERUN=\"new:duo:door\" bash studies/field-coop/s168/round_gm_rerun.sh"
fi
# 7. THE T ROWS: the older hosts (s166's / s167's tape or THE INSTRUMENT of that caps word); the b3 tape's legs only once it exists
t2 older166
t2 older167
TAPE="$(gm_tape)"
if [ -n "$TAPE" ]; then
  say "   COOP_TAPE_GUEST_MENU: $TAPE"
  t2 tape COOP_GMT_RAMP=field
  t2 tape COOP_GMT_RAMP=world
else
  for r in field world; do
    skip_leg "T2 tape COOP_GMT_RAMP=$r" "S168-GMT-GATE: no COOP_TAPE_GUEST_MENU yet -- OWNER-GATED (coop_tape_record.py's GUEST-MENU variant on this s168 host, the Order's step 4); the duo ran its rows"
  done
fi
# 8. LAST: GM0-QUIT-EXIT (destructive: Quit confirmed, the process exits; the sandbox saves unchanged)
solo quitexit
proof_report new
say "== all done (NEW). Next: round_gm_lever.sh (each lever alone), then round_gm_regress.sh, then the owner's s168 two-PC look"
