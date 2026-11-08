#!/usr/bin/env bash
# s168 ROUND GM -- OLD, measured on the DEPLOYED s167 (12be3220520813a6), BEFORE any s168-family deploy (the design's Order, step 1: the
# first s168 deploy -- the W1a/b pin included -- replaces s167, and OLD can no longer be measured after it). Every GM0 row's OLD
# prediction, one leg per launch, COOP_CALIBRATE=1: each leg reads the STAGE off the probe (`netsync.guestmenu` absent = s167), so no
# `guestmenu` op is ever sent (the scenarios gate it themselves), every leg row reads "not reached", and each launch MEASURES s167's shape
# -- the selftest role's s121 reading (`menu_refusal.now` 'open', its own menu opening on a press) on the solo bench, a mirroring guest's
# press refused as s121 (audible, count +1) on the duo, an unmirrored world-paired guest's own menu opening (GM0-HOLE) on T2. The CAL row
# of each launch (S168-CAL / S168D-CAL / S168T-CAL) is the verdict: exactly the leg's OLD-predicted rows red, each measured.
# K1's launch is the solo `proof` leg (the probe and the proof lines); GM0-STSCENE / GM0-HUDSTRIP / GM0-DIALOG-PATH measure on OLD and NEW
# alike (the duo `world`, `hudstrip` and `dialog` legs).
# NOT HERE: the T `tape` leg (COOP_TAPE_GUEST_MENU is recorded on an s168 HOST, the Order's step 4: it cannot exist before the deploy);
# GM0-BRACKET (round_gm_regress.sh with ROUND_GM_SET=bracket, on the pinned W1a/b build, the Order's step 2).
# Last, the first solo leg's proof block is recorded as s167's reference (ROUND_GM_REF): BRACKET / NEW / REGRESS judge theirs against it.
#   bash studies/field-coop/s168/round_gm_old.sh            (logs: .harness-runs/s168-round-gm/<stamp>-old/, summary.log there)
ROUND_GM_KIND=old
. "$(dirname "$0")/round_gm_lib.sh"
preflight old t2 duo

# 1. the solo rows (coop_guest_menu.py, the forced selftest role): exactly old_predicted per leg ('proof' first: K1's launch)
for l in proof seat refuse deep why witness door close quit held master diorama release softreset cfg quitexit; do
  leg "OLD solo $l" solo "old_solo_$l.log" -- env COOP_CALIBRATE=1 COOP_GM_LEG=$l $SOLO s168-gm-old-$l -- \
      py tools/play.py $SC/coop_guest_menu.py --field $GM_FIELD
done
leg "OLD solo world" solo old_solo_world.log -- env COOP_CALIBRATE=1 COOP_GM_LEG=world $SOLO s168-gm-old-world -- \
    py tools/play.py $SC/coop_guest_menu.py --field $FARSHORE
# 2. T2 (the owner's bridge down): the hole on a world-paired unmirrored guest, the older hosts (s166's 0x0001, s167's 0x0003)
for l in hole older166 older167; do
  leg "OLD T2 $l" t2 "old_t2_$l.log" -- env COOP_CALIBRATE=1 COOP_GMT_LEG=$l py tools/play.py $SC/coop_guest_menu_duo.py
done
# 3. the duo: a MIRRORING guest's press refused as s121 on every leg (the measuring rows read the same on OLD and NEW)
for l in key caps world leave door out rejoin cut title scene chest ramp rampquit stall dialog hudstrip; do
  leg "OLD duo $l" duo "old_duo_$l.log" -- env COOP_CALIBRATE=1 COOP_GMD_LEG=$l $DUO $SC/coop_guest_menu_duo.py
done
proof_reference
say "== all done (OLD). Next (after the owner's s167 two-PC look): the W1a/b pin + ROUND_GM_SET=bracket round_gm_regress.sh, then the"
say "   s168 deploy + round_gm_new.sh"
