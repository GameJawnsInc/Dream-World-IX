#!/usr/bin/env bash
# s167 ROUND B -- NEW, on the s167 build, in the design's Order (S166-DESIGN.md "Order", round B): the walk with `refuse silent`; the
# refusal; pairing, stall hole, decline, fingerprint, TPS; the minimap close (decisions 27-28); decision 8 last; T2; the duo -- then the
# regression set (round_b_regress.sh). One leg per launch; every row green is the verdict (each launch's "checks passed" line in
# summary.log). Every solo leg's setup carries S167-W-PROOF ('world walk selftest: OK (N rows, M mutants)' with the s167 source's tallies,
# FF9_S167_CLONE; 'overlay text selftest: OK (58 rows)').
#   bash studies/world-coop/s167/round_b_new.sh            (ROUND_B_DLL=<sha16> pins the build under test)
# THE ORDER, as legs: "the walk with `refuse silent`" -- the free leg presses no Confirm, so decision 18's refusal is INERT in it by
# construction (no lever needed), and the stall hold (decision 16, the stale leg) is the walk's own; "the refusal" -- the entry leg
# (decision 18: the buzz, the line, the readers); "pairing ... fingerprint" -- the refuse leg (W-REFUSE-x: NOB6 / OTHER / RIDE / SCENE /
# OWNMODE / PAIR / FP, each alone); "stall hole" -- T2's stallhole leg (decision 17 needs a real client's session: WR-PAIR rides it);
# decline (20), TPS (22: report; `tps apply` the owner's trial), the minimap close (27-28: a FROZEN guest under `walk off`), decision 8
# LAST (the map leg); then T2-B (the walk leg) and T2-HB (the s167 host's lines), then the duo.
# OWNER-GATED, NOT HERE: COOP_TAPE_WORLD_ROAM's recording on an s167 host (studies/world-coop/s166-handoff/ROAM-TAPE.md "Round B") --
# until it exists the walk leg runs THE INSTRUMENT (calibrated to this guest's own 9011 fingerprint) and S167-WR-GATE stays RED, as
# round A's S166-RM-GATE did; the two-PC look (the owner's).
ROUND_B_KIND=new
. "$(dirname "$0")/round_b_lib.sh"
preflight new t2

# 1. THE WALK (W-FREE + W-CAM; THE PROOF rides its setup), then its stall hold (W-STALE)
leg "the walk + the proof" solo new_solo_free.log -- env COOP_WW_LEG=free $SOLO s167-b-free -- py tools/play.py $SC/coop_world_walk.py --field 6603
leg "solo stale (the stall hold)" solo new_solo_stale.log -- env COOP_WW_LEG=stale $SOLO s167-b-stale -- \
    py tools/play.py $SC/coop_world_walk.py --field 6603
# 2. THE REFUSAL (decision 18: W-OPEN, W-ENTRY, W-KITCELL on KIT_6603_TRIGGER -- THE TRIGGER IS NOT THE CELL -- W-KITBOAT, W-FERRY)
leg "solo entry (the refusal)" solo new_solo_entry.log -- env COOP_WW_LEG=entry $SOLO s167-b-entry -- \
    py tools/play.py $SC/coop_world_walk.py --field 6603
# 3. PAIRING + FINGERPRINT (+ the walk's other refusals, each alone)
leg "solo refuse (pairing, fingerprint, ...)" solo new_solo_refuse.log -- env COOP_WW_LEG=refuse $SOLO s167-b-refuse -- \
    py tools/play.py $SC/coop_world_walk.py --field 6603
# 4. THE STALL HOLE (decision 17) on a world-paired real client: WR-PAIR, W-STALLHOLE, W-STALLHOLE-KEYS
leg "T2 stallhole" t2 new_t2_stallhole.log -- env COOP_WWT_LEG=stallhole py tools/play.py $SC/coop_world_walk_t2.py
# 5. DECLINE (the re-arm at a NEW visit, never a warm return), TPS (report; the apply trial)
leg "solo decline" solo new_solo_decline.log -- env COOP_WW_LEG=decline $SOLO s167-b-decline -- \
    py tools/play.py $SC/coop_world_walk.py --field 6603
leg "solo tps" solo new_solo_tps.log -- env COOP_WW_LEG=tps $SOLO s167-b-tps -- py tools/play.py $SC/coop_world_walk.py --field 6603
# 6. THE MINIMAP CLOSE (decisions 27-28: a frozen guest; the hint's re-show needs a NEW visit -- a field round trip, R9)
leg "solo minimap" solo new_solo_minimap.log -- env COOP_WW_LEG=minimap $SOLO s167-b-minimap -- \
    py tools/play.py $SC/coop_world_walk.py --field 6603
# 7. DECISION 8 LAST (the lawful walker's full map, the full-map dot, stock's close)
leg "solo map (decision 8)" solo new_solo_map.log -- env COOP_WW_LEG=map $SOLO s167-b-map -- py tools/play.py $SC/coop_world_walk.py --field 6603
# 8. T2: T2-B on THE INSTRUMENT (S167-WR-GATE red until the owner's s167 ROAM tape), T2-HB (this desktop an s167 host)
leg "T2 walk (T2-B)" t2 new_t2_walk.log -- env COOP_WWT_LEG=walk py tools/play.py $SC/coop_world_walk_t2.py
leg "T2 hostb (T2-HB)" t2 new_t2_hostb.log -- env COOP_WWT_LEG=hostb py tools/play.py $SC/coop_world_walk_t2.py
# 9. the duo: ghosts both ways while walking, the refusal named on both sides, the boot / rejoin co-op closes, the waited rejoin
leg "duo b" duo new_duo_b.log -- env COOP_WWT_DUO=b $DUO $SC/coop_world_walk_t2.py
say "== all done (NEW). Next: round_b_lever.sh (each lever alone), then round_b_regress.sh, then the owner's two-PC look"
