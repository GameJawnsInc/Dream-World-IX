#!/usr/bin/env bash
# s167 ROUND B -- THE REGRESSION SET (after round_b_new.sh / round_b_lever.sh), on the s167 build: round A's own legs (they are regression
# now: round_a_new.sh's, the pull, the round-A duo) + round A's regression set (round_a_regress.sh: A0 / A0b, s165, s144, s145, the party
# duo, every coop_peer-based scenario), each AS IT IS. Round B changes a FROZEN guest's world map (decisions 13-28: the walk, the entrance
# buzz, the decline re-arm, the fingerprint and caps 0x0003, the minimap close, the lawful full map), so EVERY LEG HERE THAT JUDGES A
# FROZEN GUEST pulls round B's whole s166 lever set itself when its probe shows `netsync.world.walk` -- `worldwalk walk off`, `refuse
# silent`, `stallhold old`, `decline old`, `fp off`, `minimap old`, `fullmap old` (W1's set that reads s166 exactly) -- read back and
# folded into its instrument row, and re-keys BY STAGE (never weakened) the rows whose meaning moves: on s167 `freeze.on` stays true
# while a guest walks, so a frozen-guest row also reads the walk frozen BY THE LEVER (coop_world_wait.judge_walk_key), a refusal row
# reads round B's counters unmoved (walk_quiet), and every P0 wants the s167 key list (+ 'overlay text selftest: OK (58 rows)').
#   round A's solo legs and A0       coop_world_walk.py P1 (S166_LEVER_SET)        round A's T2 legs + duo   coop_world_walk_t2.py
#   A0b's T2 pair                    before the replay (T2-PEER)                    s165 follow solo/T2/duo   coop_world_follow.py
#   s144 wait solo/T2 wait/duo       coop_world_wait.py (P1, follow_off)            s145 solo/T2/held/duo     coop_world_battle.py
#   the party duo (mirror)           follow_off + the host's walk_off               the duos: BOTH games get the set
# The rejoin leg (its guest never frozen by a host on the world map) and the field-only coop_peer scenarios need none. The WorldTPS
# mismatch line and the missing-caps line still speak under the set (the W1 review's R4): no leg asserts their absence. The tapes are
# restamped as round A's were (replay-host `--wire auto`); a v14 / v15 tape's host has no caps b1, so a guest there is frozen 'older'
# anyway -- the set still pulls (s166's edge line, its raw why byte). Round A's roam leg keeps S166-RM-GATE red (the owner-gated tape).
#   bash studies/world-coop/s167/round_b_regress.sh
ROUND_B_KIND=regress
. "$(dirname "$0")/round_b_lib.sh"
preflight new t2
WS144=C:/gd/Dream-World-IX/.harness-runs/coop-tapes/world-s144/20261021-010037-host6603-world-s144.f9tape

# ---- round A's own legs (round_a_new.sh's order), now regression for round B
leg "A: the proof + A-TX" solo reg_a_tx.log -- env COOP_WW_LEG=tx $SOLO s167-reg-a-tx -- py tools/play.py $SC/coop_world_walk.py --field 6603
leg "A: A-WIRE" t2 reg_a_wire.log -- env COOP_WWT_LEG=wire py tools/play.py $SC/coop_world_walk_t2.py
leg "A: T2-A old (the restamp; coop_world_follow's walk leg)" t2 reg_a_old.log -- env COOP_WWT_LEG=old py tools/play.py $SC/coop_world_walk_t2.py
for l in ghost wrap dot body stall; do
  leg "A: solo $l" solo "reg_a_$l.log" -- env COOP_WW_LEG=$l $SOLO s167-reg-a-$l -- py tools/play.py $SC/coop_world_walk.py --field 6603
done
leg "A: T2-A roam" t2 reg_a_roam.log -- env COOP_WWT_LEG=roam py tools/play.py $SC/coop_world_walk_t2.py
leg "A: T2-A freeze" t2 reg_a_freeze.log -- env COOP_WWT_LEG=freeze py tools/play.py $SC/coop_world_walk_t2.py
leg "A: T2-H" t2 reg_a_host.log -- env COOP_WWT_LEG=host py tools/play.py $SC/coop_world_walk_t2.py
leg "A: duo (round A)" duo reg_a_duo.log -- $DUO $SC/coop_world_walk_t2.py

# ---- round A's regression set (round_a_regress.sh's list, unchanged)
# A0 / A0b
leg "A0 solo kitoff + ferryoff" solo reg_a0.log -- $SOLO s167-reg-a0 -- py tools/play.py $SC/coop_world_walk.py --field 6603
leg "A0b T2 pair" t2 reg_a0b_pair.log -- env COOP_WW_LEG=pair py tools/play.py $SC/coop_world_walk.py
# s165 (the follow-out, the dot, the save guard)
for s in out dot save; do
  leg "s165 follow solo $s" solo "reg_follow_$s.log" -- env COOP_WF_SOLO=$s $SOLO s167-reg-$s -- py tools/play.py $SC/coop_world_follow.py --field 6603
done
leg "s165 follow T2 walk" t2 reg_follow_walk.log -- env COOP_WF_LEG=walk py tools/play.py $SC/coop_world_follow.py
leg "s165 follow duo" duo reg_follow_duo.log -- $DUO $SC/coop_world_follow.py
# s144 (the world wait)
leg "s144 wait solo" solo reg_wait_solo.log -- env SOLO_INI_FOLLOW=0 $SOLO s167-reg-wait-solo -- py tools/play.py $SC/coop_world_wait.py --field 6603
leg "s144 wait T2 rejoin" t2 reg_wait_rejoin.log -- env COOP_WORLD_LEG=rejoin py tools/play.py $SC/coop_world_wait.py
leg "s144 wait T2 wait" t2 reg_wait_wait.log -- env COOP_TAPE=$WS144 COOP_WORLD_LEG=wait py tools/play.py $SC/coop_world_wait.py
leg "s144 wait duo" duo reg_wait_duo.log -- $DUO $SC/coop_world_wait.py
# s145 (world battles)
leg "s145 battle solo" solo reg_battle_solo.log -- env SOLO_INI_FOLLOW=0 $SOLO s167-reg-battle-solo -- py tools/play.py $SC/coop_world_battle.py --field 6603
leg "s145 battle T2 battle" t2 reg_battle_t2.log -- env COOP_WB_LEG=battle py tools/play.py $SC/coop_world_battle.py
leg "s145 battle T2 decline" t2 reg_battle_decline.log -- env COOP_WB_LEG=decline py tools/play.py $SC/coop_world_battle.py
# [round B adds] the held leg (not in round A's set): its guest waits FROZEN on the world map while the host fights on 6603 -- the
# round-B re-key reaches it on its own (HF-I), so it joins the set here (its plain host tape: coop-tapes/held-6603)
leg "s145 battle T2 held" t2 reg_battle_held.log -- env COOP_WB_LEG=held py tools/play.py $SC/coop_world_battle.py
leg "s145 battle duo" duo reg_battle_duo.log -- $DUO $SC/coop_world_battle.py
leg "s144 party duo mirror" duo reg_party_mirror.log -- env COOP_WP_LEG=mirror $DUO $SC/coop_world_party_duo.py --no-pair
# every coop_peer-based scenario (restamped tapes: replay-host --wire auto) -- field-only: no frozen guest, nothing to re-key
leg "coop_action_fallback tape" t2 reg_fb_tape.log -- env COOP_FB_LEG=tape py tools/play.py $SC/coop_action_fallback.py
leg "coop_action_hold tape" t2 reg_hold_tape.log -- env COOP_HOLD_LEG=tape py tools/play.py $SC/coop_action_hold.py
leg "coop_action_replay tape" t2 reg_act_tape.log -- env COOP_ACT_LEG=tape py tools/play.py $SC/coop_action_replay.py
leg "coop_cut_hold cal" t2 reg_cut_cal.log -- py tools/play.py $SC/coop_cut_hold.py
leg "coop_dress_wire duo" duo reg_dress_wire.log -- $DUO $SC/coop_dress_wire.py
# the selftest role refuses a live-configured install (S138-INI): solo_ini flips Enabled to 0 ONLY (SOLO_INI_FOLLOW=0) and restores it
leg "coop_self_dress" solo reg_self_dress.log -- env SOLO_INI_FOLLOW=0 $SOLO s167-reg-self-dress -- py tools/play.py $SC/coop_self_dress.py --field 250
# the peer's bench port through ROUND_B_PEER_PORT (else ROUND_A_PEER_PORT): THE EXCLUDED PORT RANGE --
# `netsh int ipv4 show excludedportrange protocol=tcp` before picking one
leg "coop_climb_anim_peer" t2 reg_climb_peer.log -- env ${PEER_PORT:+COOP_PEER_PORT=$PEER_PORT} py tools/play.py $SC/coop_climb_anim_peer.py --instance C:/gd/ff9-inst/host
leg "coop_host_code" t2 reg_host_code.log -- py tools/play.py $SC/coop_host_code.py --instance C:/gd/ff9-inst/host
leg "coop_ramp_title p17-ownwalk" t2 reg_ramp_title.log -- env COOP_LEG=p17-ownwalk py tools/play.py $SC/coop_ramp_title.py --instance C:/gd/ff9-inst/host
say "== all done (REGRESSION). Next: W3 (the whole-diff review, the s167 patch, the laptop package), then the owner's two-PC look"
