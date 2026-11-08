#!/usr/bin/env bash
# s168 ROUND GM -- LEVER, on the s168 build: each calibration lever ALONE (one change per test by lever), in the design's Order.
# COOP_CALIBRATE=1 + the leg + its lever: exactly the leg's LEVER_PREDICTED red, each red row MEASURING its lever's shape (`old` restores
# s167's -- the solo bench's s121 reading and its own menu, the duo's s121 refusal --; `close old` holds every forced close; the selftest
# mutants -- `seat skip party`, `chip off`, `events on`, `restore skip <c>` once per component, `capture off`, `poke` -- each redden their
# own rows) -- every launch's CAL row is the verdict ("no predicted red stayed green, no unpredicted red, every shape measured").
# The duo pulls ANY-ROLE levers only (THE DUO CANNOT PULL A SELFTEST-ROLE LEVER): `old`, `capture off`, `close old` on the guest. The legs
# with no lever (solo proof / release / quitexit; duo dialog / hudstrip; T older166 / older167) have nothing to calibrate here: their CAL
# rides NEW. The T `tape` leg's lever runs only once COOP_TAPE_GUEST_MENU exists (owner-gated).
#   bash studies/field-coop/s168/round_gm_lever.sh
ROUND_GM_KIND=lever
. "$(dirname "$0")/round_gm_lib.sh"
preflight new t2 duo
solo() {   # solo <leg> <lever>
  local f=$GM_FIELD
  [ "$1" = "world" ] && f=$FARSHORE
  leg "LEVER solo $1 $2" solo "lever_solo_$1_${2//:/-}.log" -- env COOP_CALIBRATE=1 COOP_GM_LEG=$1 COOP_GM_LEVER=$2 \
      $SOLO s168-gm-lever-$1-${2//:/-} -- py tools/play.py $SC/coop_guest_menu.py --field $f
}
duo() {    # duo <leg> <lever>
  leg "LEVER duo $1 $2" duo "lever_duo_$1_$2.log" -- env COOP_CALIBRATE=1 COOP_GMD_LEG=$1 COOP_GMD_LEVER=$2 $DUO $SC/coop_guest_menu_duo.py
}
t2() {     # t2 <leg> <lever>
  leg "LEVER T2 $1 $2" t2 "lever_t2_$1_$2.log" -- env COOP_CALIBRATE=1 COOP_GMT_LEG=$1 COOP_GMT_LEVER=$2 \
      py tools/play.py $SC/coop_guest_menu_duo.py
}

# 1. the hole (`old`: the unmirrored guest's own menu opens again)
t2 hole old
# 2. the key and the seat (`old`: s121; the seat's mutants, each alone; `restore skip` once per fingerprint component)
duo key old
duo key capture
for v in old skip chip events restore:players restore:party restore:bag restore:gil restore:keyitems; do
  solo seat $v
done
# 3. the census and the restore, the holds
solo refuse old
solo refuse capture
solo refuse poke
solo deep old
solo deep capture
for l in why witness door held master diorama; do
  solo $l old
done
# 4. the closes: `old`, then `close old` (every forced close held) -- one leg, one lever, one launch
for l in close quit cfg; do
  solo $l old
  solo $l closeold
done
if softreset_ok; then
  solo softreset old
else
  skip_leg "LEVER solo softreset old" "the install lacks [Control] SoftReset 1 / [Cheats] Enabled 1 (GM0-SOFTRESET's precondition)"
fi
duo rampquit old   # first: the first in-game WM_CLOSE runs alone, ahead of the cut leg's fallback
for l in leave out rejoin cut title scene chest ramp; do
  duo $l old
  duo $l closeold
done
duo stall old
solo world old
solo world poke
duo world old
# 5. the caps leg (`old` on the guest: the press is s121's whatever the host's caps say)
duo caps old
# 6. the b3 tape's T leg, once it exists
if [ -n "$(gm_tape)" ]; then
  t2 tape old
else
  skip_leg "LEVER T2 tape old" "S168-GMT-GATE: no COOP_TAPE_GUEST_MENU yet (owner-gated, the Order's step 4)"
fi
proof_report new
say "== all done (LEVER). Next: round_gm_regress.sh"
