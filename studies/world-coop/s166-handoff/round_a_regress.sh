#!/usr/bin/env bash
# s166 ROUND A -- THE REGRESSION SET (W3 runs it, after round_a_new.sh / round_a_lever.sh): round A changes no lawful guest behaviour, so
# every earlier rung's legs run AS THEY ARE on the s166 build, their tapes RESTAMPED (replay-host `--wire auto`, the default: a v14 tape
# to a v15 guest = a capless v15 host) -- s165's regress.sh list + A0 / A0b + every coop_peer-based scenario (S166-DESIGN.md
# "Regression"). The duo legs there run under an ACTIVE trailer (both games s166); every T2 leg asserts the live header first.
# W3 ALSO OWES, IN THE SAME COMMIT AS THE PATCH (or the nightly gate goes red): the s157 "39 B" judges re-keyed to ">= 39 B carrying the
# s157 bytes" (_climb_anim_judges.py, coop_climb_anim_peer.py), test_harness_netsync's `== 14` pin, test_coop_peer's v14 vectors and
# fakegame's `wire` moved to 15.
#   bash studies/world-coop/s166-handoff/round_a_regress.sh
ROUND_A_KIND=regress
. "$(dirname "$0")/round_a_lib.sh"
preflight new t2
WS144=C:/gd/Dream-World-IX/.harness-runs/coop-tapes/world-s144/20261021-010037-host6603-world-s144.f9tape

# A0 / A0b (round A's own earlier pieces)
leg "A0 solo kitoff + ferryoff" solo reg_a0.log -- $SOLO s166-reg-a0 -- py tools/play.py $SC/coop_world_walk.py --field 6603
leg "A0b T2 pair" t2 reg_a0b_pair.log -- env COOP_WW_LEG=pair py tools/play.py $SC/coop_world_walk.py
# s165 (the follow-out, the dot, the save guard)
for s in out dot save; do
  leg "s165 follow solo $s" solo "reg_follow_$s.log" -- env COOP_WF_SOLO=$s $SOLO s166-reg-$s -- py tools/play.py $SC/coop_world_follow.py --field 6603
done
leg "s165 follow T2 walk" t2 reg_follow_walk.log -- env COOP_WF_LEG=walk py tools/play.py $SC/coop_world_follow.py
leg "s165 follow duo" duo reg_follow_duo.log -- py tools/harness/duo.py $SC/coop_world_follow.py
# s144 (the world wait) -- s165's regress.sh
leg "s144 wait solo" solo reg_wait_solo.log -- env SOLO_INI_FOLLOW=0 $SOLO s166-reg-wait-solo -- py tools/play.py $SC/coop_world_wait.py --field 6603
leg "s144 wait T2 rejoin" t2 reg_wait_rejoin.log -- env COOP_WORLD_LEG=rejoin py tools/play.py $SC/coop_world_wait.py
leg "s144 wait T2 wait" t2 reg_wait_wait.log -- env COOP_TAPE=$WS144 COOP_WORLD_LEG=wait py tools/play.py $SC/coop_world_wait.py
leg "s144 wait duo" duo reg_wait_duo.log -- py tools/harness/duo.py $SC/coop_world_wait.py
# s145 (world battles) -- s165's regress.sh
leg "s145 battle solo" solo reg_battle_solo.log -- env SOLO_INI_FOLLOW=0 $SOLO s166-reg-battle-solo -- py tools/play.py $SC/coop_world_battle.py --field 6603
leg "s145 battle T2 battle" t2 reg_battle_t2.log -- env COOP_WB_LEG=battle py tools/play.py $SC/coop_world_battle.py
leg "s145 battle T2 decline" t2 reg_battle_decline.log -- env COOP_WB_LEG=decline py tools/play.py $SC/coop_world_battle.py
leg "s145 battle duo" duo reg_battle_duo.log -- py tools/harness/duo.py $SC/coop_world_battle.py
leg "s144 party duo mirror" duo reg_party_mirror.log -- env COOP_WP_LEG=mirror py tools/harness/duo.py $SC/coop_world_party_duo.py --no-pair
# every coop_peer-based scenario (restamped tapes: replay-host --wire auto)
leg "coop_action_fallback tape" t2 reg_fb_tape.log -- env COOP_FB_LEG=tape py tools/play.py $SC/coop_action_fallback.py
leg "coop_action_hold tape" t2 reg_hold_tape.log -- env COOP_HOLD_LEG=tape py tools/play.py $SC/coop_action_hold.py
leg "coop_action_replay tape" t2 reg_act_tape.log -- env COOP_ACT_LEG=tape py tools/play.py $SC/coop_action_replay.py
leg "coop_cut_hold cal" t2 reg_cut_cal.log -- py tools/play.py $SC/coop_cut_hold.py
leg "coop_dress_wire duo" duo reg_dress_wire.log -- py tools/harness/duo.py $SC/coop_dress_wire.py
leg "coop_self_dress" plain reg_self_dress.log -- py tools/play.py $SC/coop_self_dress.py --field 250
leg "coop_climb_anim_peer" t2 reg_climb_peer.log -- py tools/play.py $SC/coop_climb_anim_peer.py --instance C:/gd/ff9-inst/host
leg "coop_host_code" t2 reg_host_code.log -- py tools/play.py $SC/coop_host_code.py --instance C:/gd/ff9-inst/host
leg "coop_ramp_title p17-ownwalk" t2 reg_ramp_title.log -- env COOP_LEG=p17-ownwalk py tools/play.py $SC/coop_ramp_title.py --instance C:/gd/ff9-inst/host
say "== all done (REGRESSION)"
