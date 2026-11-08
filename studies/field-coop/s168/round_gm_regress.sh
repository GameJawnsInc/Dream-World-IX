#!/usr/bin/env bash
# s168 ROUND GM -- THE REGRESSION SET (S168-DESIGN.md "The bench", its Regression paragraph; the Order's step 6), judged on the s168 build
# with the guest menu ACT (never under `guestmenu old`: no leg here pulls it). Two sets, by ROUND_GM_SET:
#   full (default, on the s168 build: preflight new)
#     * s167's whole regression set (studies/world-coop/s167/round_b_regress.sh's legs, each AS IT IS): round A's own legs, A0 / A0b --
#       the A0b T2 pair carries coop_world_walk.py PR-SAVEMENU, re-keyed BY STAGE (`guest` accepted only when the probe shows
#       `netsync.guestmenu`) --, s165 / s144 / s145 and the held leg, the party duo, every coop_peer-based scenario, the dress wire duo,
#       coop_self_dress, coop_climb_anim_peer, coop_host_code, coop_ramp_title p17-ownwalk
#     * round B's own legs (round_b_new.sh's, now regression): the world walk solo legs -- S167-P0's lane.caps.own and S167-W-PROOF's
#       tallies re-keyed BY STAGE (0x000B and the s168 source's 534 / 198; 0x0003 under `guestmenu caps off`) --, the T2 legs, the duo
#       (S167-D-WFREE's caps re-keyed to each game's own published word)
#     * THE DIORAMA LEGS (the bracket extract and the builder move): coop_diorama_return, coop_battle_flee_defeat, coop_battle_end_guest,
#       coop_battle_result_replay, coop_leader_guard, coop_stock_menu (its X row: `bmenu mainmenu` still refused) with its _live and
#       _content legs -- SeatSelfTest's line, the containment selftest's and the new seat bracket line judged by the PROOF BLOCK below
#     * the B4-B5 set (coop_dialogue_authority, coop_talk_relay); s164's Pause MENU legs (coop_field_swap_timing_duo.py COOP_LEGS=MENU:
#       DL-DEFER, DP-DEFER, DP-AGED unchanged, MENU_PRE_OK re-keyed BY STAGE); coop_cut_hold.py's s121 leg UNCHANGED (GM0-CAPS-c, the
#       fallback row: a capless v14 peer, G0-G5 and C1 green, no caps line)
#     * the kit's proof pins: every solo leg's PROOF BLOCK against s167's (MenuRefusalSelfTest at 14, the diorama seat / containment
#       lines identical; the world walk line at the s168 source's tallies, the seat bracket and guest menu lines at theirs)
#   bracket (GM0-BRACKET, the Order's step 2, on the pinned W1a/b build 532486364ec05354: preflight bracket) -- the diorama legs alone and
#     their D half (the s145 world-battle duo: a guest's diorama boot across the extracted bracket), then the proof block: identical to
#     s167's but for the NEW 'seat bracket selftest: OK (19 rows, 7 mutants caught)' (s167 had no bracket selftest, decision 11)
# _coop_peer_bench.engine_stage's s168 key is offline (the stage ladder's own self-check rows; tests/test_coop_guest_menu_runners.py).
#   bash studies/field-coop/s168/round_gm_regress.sh                         (the full set, on s168)
#   ROUND_GM_SET=bracket bash studies/field-coop/s168/round_gm_regress.sh    (GM0-BRACKET, on the W1a/b pin)
ROUND_GM_SET="${ROUND_GM_SET:-full}"
case "$ROUND_GM_SET" in
  full|bracket) ;;
  *) echo "ROUND_GM_SET=$ROUND_GM_SET: one of full, bracket"; exit 2 ;;
esac
ROUND_GM_KIND="regress-$ROUND_GM_SET"
. "$(dirname "$0")/round_gm_lib.sh"
WS144=C:/gd/Dream-World-IX/.harness-runs/coop-tapes/world-s144/20261021-010037-host6603-world-s144.f9tape

diorama_legs() {   # the diorama legs on 30602, the selftest role with Enabled 0 only (SOLO_INI_FOLLOW=0: full145's selftest block)
  local s
  for s in coop_diorama_return coop_battle_flee_defeat coop_battle_end_guest coop_battle_result_replay coop_leader_guard \
           coop_stock_menu coop_stock_menu_live coop_stock_menu_content; do
    leg "diorama: $s" solo "reg_dio_$s.log" -- env SOLO_INI_FOLLOW=0 $SOLO s168-reg-$s -- py tools/play.py $SC/$s.py --field $DIO_FIELD
  done
}

if [ "$ROUND_GM_SET" = "bracket" ]; then
  preflight bracket duo
  diorama_legs
  leg "s145 battle duo (GM0-BRACKET's D half)" duo reg_battle_duo.log -- $DUO $SC/coop_world_battle.py
  proof_report bracket
  say "== all done (BRACKET). Next: restore the live DLLs (tools/restore_memoria_dll.py <the pre-pin snapshot>) or deploy s168, then"
  say "   round_gm_new.sh"
  exit 0
fi

preflight new t2 duo peer regress
# ---- s167's regression set (round_b_regress.sh's legs, unchanged) -- round A's own legs first
leg "A: the proof + A-TX" solo reg_a_tx.log -- env COOP_WW_LEG=tx $SOLO s168-reg-a-tx -- py tools/play.py $SC/coop_world_walk.py --field 6603
leg "A: A-WIRE" t2 reg_a_wire.log -- env COOP_WWT_LEG=wire py tools/play.py $SC/coop_world_walk_t2.py
leg "A: T2-A old (the restamp; coop_world_follow's walk leg)" t2 reg_a_old.log -- env COOP_WWT_LEG=old py tools/play.py $SC/coop_world_walk_t2.py
for l in ghost wrap dot body stall; do
  leg "A: solo $l" solo "reg_a_$l.log" -- env COOP_WW_LEG=$l $SOLO s168-reg-a-$l -- py tools/play.py $SC/coop_world_walk.py --field 6603
done
leg "A: T2-A roam" t2 reg_a_roam.log -- env COOP_WWT_LEG=roam py tools/play.py $SC/coop_world_walk_t2.py
leg "A: T2-A freeze" t2 reg_a_freeze.log -- env COOP_WWT_LEG=freeze py tools/play.py $SC/coop_world_walk_t2.py
leg "A: T2-H" t2 reg_a_host.log -- env COOP_WWT_LEG=host py tools/play.py $SC/coop_world_walk_t2.py
leg "A: duo (round A)" duo reg_a_duo.log -- $DUO $SC/coop_world_walk_t2.py
# A0 / A0b (A0b's T2 pair carries PR-SAVEMENU)
leg "A0 solo kitoff + ferryoff" solo reg_a0.log -- $SOLO s168-reg-a0 -- py tools/play.py $SC/coop_world_walk.py --field 6603
leg "A0b T2 pair (PR-SAVEMENU)" t2 reg_a0b_pair.log -- env COOP_WW_LEG=pair py tools/play.py $SC/coop_world_walk.py
# s165 (the follow-out, the dot, the save guard -- P0's netsync tail re-keyed BY STAGE: `guestmenu` after `wire_peer`)
for s in out dot save; do
  leg "s165 follow solo $s" solo "reg_follow_$s.log" -- env COOP_WF_SOLO=$s $SOLO s168-reg-$s -- py tools/play.py $SC/coop_world_follow.py --field 6603
done
leg "s165 follow T2 walk" t2 reg_follow_walk.log -- env COOP_WF_LEG=walk py tools/play.py $SC/coop_world_follow.py
leg "s165 follow duo" duo reg_follow_duo.log -- $DUO $SC/coop_world_follow.py
# s144 (the world wait)
leg "s144 wait solo" solo reg_wait_solo.log -- env SOLO_INI_FOLLOW=0 $SOLO s168-reg-wait-solo -- py tools/play.py $SC/coop_world_wait.py --field 6603
leg "s144 wait T2 rejoin" t2 reg_wait_rejoin.log -- env COOP_WORLD_LEG=rejoin py tools/play.py $SC/coop_world_wait.py
leg "s144 wait T2 wait" t2 reg_wait_wait.log -- env COOP_TAPE=$WS144 COOP_WORLD_LEG=wait py tools/play.py $SC/coop_world_wait.py
leg "s144 wait duo" duo reg_wait_duo.log -- $DUO $SC/coop_world_wait.py
# s145 (world battles) and the held leg
leg "s145 battle solo" solo reg_battle_solo.log -- env SOLO_INI_FOLLOW=0 $SOLO s168-reg-battle-solo -- py tools/play.py $SC/coop_world_battle.py --field 6603
leg "s145 battle T2 battle" t2 reg_battle_t2.log -- env COOP_WB_LEG=battle py tools/play.py $SC/coop_world_battle.py
leg "s145 battle T2 decline" t2 reg_battle_decline.log -- env COOP_WB_LEG=decline py tools/play.py $SC/coop_world_battle.py
leg "s145 battle T2 held" t2 reg_battle_held.log -- env COOP_WB_LEG=held py tools/play.py $SC/coop_world_battle.py
leg "s145 battle duo" duo reg_battle_duo.log -- $DUO $SC/coop_world_battle.py
leg "s144 party duo mirror" duo reg_party_mirror.log -- env COOP_WP_LEG=mirror $DUO $SC/coop_world_party_duo.py --no-pair
# every coop_peer-based scenario (restamped tapes: replay-host --wire auto)
leg "coop_action_fallback tape" t2 reg_fb_tape.log -- env COOP_FB_LEG=tape py tools/play.py $SC/coop_action_fallback.py
leg "coop_action_hold tape" t2 reg_hold_tape.log -- env COOP_HOLD_LEG=tape py tools/play.py $SC/coop_action_hold.py
leg "coop_action_replay tape" t2 reg_act_tape.log -- env COOP_ACT_LEG=tape py tools/play.py $SC/coop_action_replay.py
leg "coop_cut_hold cal" t2 reg_cut_cal.log -- py tools/play.py $SC/coop_cut_hold.py
leg "coop_dress_wire duo" duo reg_dress_wire.log -- $DUO $SC/coop_dress_wire.py
leg "coop_self_dress" solo reg_self_dress.log -- env SOLO_INI_FOLLOW=0 $SOLO s168-reg-self-dress -- py tools/play.py $SC/coop_self_dress.py --field 250
leg "coop_climb_anim_peer" t2 reg_climb_peer.log -- env ${PEER_PORT:+COOP_PEER_PORT=$PEER_PORT} py tools/play.py $SC/coop_climb_anim_peer.py --instance C:/gd/ff9-inst/host
leg "coop_host_code" t2 reg_host_code.log -- py tools/play.py $SC/coop_host_code.py --instance C:/gd/ff9-inst/host
leg "coop_ramp_title p17-ownwalk" t2 reg_ramp_title.log -- env COOP_LEG=p17-ownwalk py tools/play.py $SC/coop_ramp_title.py --instance C:/gd/ff9-inst/host

# ---- round B's own legs (round_b_new.sh's, regression now), in its order
for l in free stale entry refuse; do
  leg "B: solo $l" solo "reg_b_$l.log" -- env COOP_WW_LEG=$l $SOLO s168-reg-b-$l -- py tools/play.py $SC/coop_world_walk.py --field 6603
done
leg "B: T2 stallhole" t2 reg_b_stallhole.log -- env COOP_WWT_LEG=stallhole py tools/play.py $SC/coop_world_walk_t2.py
for l in decline tps minimap map; do
  leg "B: solo $l" solo "reg_b_$l.log" -- env COOP_WW_LEG=$l $SOLO s168-reg-b-$l -- py tools/play.py $SC/coop_world_walk.py --field 6603
done
leg "B: T2 walk (T2-B)" t2 reg_b_walk.log -- env COOP_WWT_LEG=walk py tools/play.py $SC/coop_world_walk_t2.py
leg "B: T2 hostb (T2-HB)" t2 reg_b_hostb.log -- env COOP_WWT_LEG=hostb py tools/play.py $SC/coop_world_walk_t2.py
leg "B: duo b" duo reg_b_duo.log -- env COOP_WWT_DUO=b $DUO $SC/coop_world_walk_t2.py

# ---- the diorama legs (GM0-BRACKET's set, now on s168), the B4-B5 set, s164's Pause MENU, the s121 fallback
diorama_legs
leg "B4-B5: coop_dialogue_authority" solo reg_dialogue_authority.log -- env SOLO_INI_FOLLOW=0 $SOLO s168-reg-dialogue-authority -- \
    py tools/play.py $SC/coop_dialogue_authority.py --field $GM_FIELD
leg "B4-B5: coop_talk_relay" solo reg_talk_relay.log -- env SOLO_INI_FOLLOW=0 $SOLO s168-reg-talk-relay -- \
    py tools/play.py $SC/coop_talk_relay.py --field $GM_FIELD
leg "s164 Pause MENU (DL-DEFER, DP-DEFER, DP-AGED)" duo reg_swap_menu.log -- env COOP_LEGS=MENU $DUO $SC/coop_field_swap_timing_duo.py --keep-going
leg "coop_cut_hold s121 (GM0-CAPS-c, unchanged)" t2 reg_cut_s121.log -- env COOP_CUT_LEG=s121 py tools/play.py $SC/coop_cut_hold.py
proof_report new
say "== all done (REGRESSION). Next: W3 (the whole-diff review, the s168 patch, the laptop package), then the owner's s168 two-PC look"
