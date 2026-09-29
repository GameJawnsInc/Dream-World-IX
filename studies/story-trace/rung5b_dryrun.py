"""F5b'S ANALYSIS, DRY-RUN OFFLINE -- every check of rung5b_hub.analyse5b shown able to PASS, to FAIL and -- every one
with a VOID branch -- to go VOID as the frozen predictions (rung5b_predictions_v1.json) register it, THE FROZEN VERDICT
shown to come out PROVEN / NOT PROVEN: <half> / FAILED: <check> as registered, and every frozen number RE-DERIVED from
real rows and real bytes, before any F5b deploy or run. A case registered for one clause of a check names that clause
(a ``need`` on the check's detail, ``also_need`` on another check's), never the verdict alone.

    py studies/story-trace/rung5b_dryrun.py [--build DIR] [--members DIR] [--keep DIR] [--session5 DIR] [--session3 DIR]

THE BYTES. The two hubs are built here, offline, from the frozen tomls the predictions name (C:\\gd\\_ns_playtest\\f5b
\\{hub,ctl}\\hub.field.toml; ``--build DIR`` reads a build already made the same way, <DIR>/<id>/), and each US .eb is
held to its frozen sha256 first: the hubs' rows are joined against the bytes the session will deploy. The twelve
members are F5's deployed chain, reused whole: their bytes are session 5's own scripts/ snapshot, each held to
rung5_forks.json's frozen sha256; they are also BUILT from rung5b_forks.json's tomls (the durable f5b copy) for the
hermetic pre-flight, and the build must equal the snapshot byte for byte.

THE BASE is session 5 (story-rung5, archived in the main checkout's .harness-runs; read only, every file this reads is
copied into a temp session): its three stock runs S#1, S#3 and S#5 as F5b's S#1, S#4 and S#7. Each fork run is
CONSTRUCTED from its round's S, as the engine would write it (design section 6, "the rev1 construction"):
  * New Game's field-70 residue as the partner's; then the HUB's rows -- its Main_Init prologue (359's own idiom on
    the same state: the partner's first 359 prologue rows at the hub's own sites) and its frozen stamps (e2 t3, the
    hub's real entry ips), fld = don = the hub id;
  * the partner's segment (359, the pre-wake 351 and 352, the night, the wake, the exit's step-1 rows) LOST on the
    fork side -- the pick replaces it;
  * the partner's rows from its first post-wake 351 row on, relabelled into the 12 members (450 is member 31112);
  * the stores the partner COUNTED there but a fresh fork EMITS (a site whose same-value store the partner had
    emitted before its wake emits again the first time the fork runs it): at the landing the story-noise bits
    (184/191, masked) and the three 351 SUPP keys, at the fork's first 352 visit the noise bits and the five 352 SUPP
    keys, at its first 352.0 -> 351 crossing the step-1 key 352 e14 t2 +116 Bit[2103] = 0 -- each where the donor's
    own code order puts it;
  * CTL (today's pre-phase row): no latch stamps, so 351 takes the ATE(0) branch (+791/+799 for +734/+742/+770), the
    lobby exit's 2078 consumer (e16 t2 ip105) does not fire, 350's arrival computes mask 8 (241 := 8, 251 := 8 where
    stock's is 12 / 14), and the run is cut after that arrival (the prefix replayed);
  * every row's ``old`` RE-SEATED on the state the rows leave (rung5_dryrun.reseat), so the reconstructor finds 0
    contradictions;
  * its log: the hub leg's record, the landing record (dali_tour-free: rung5b_hub.enter_past's shape), the replay
    of the partner's walk SLICE (walk[1:] F5B, walk[1:2] CTL; rung3_dryrun.replay_log), the autosave reads;
  * the session record as rung5b_hub.run leaves one: the static pre-flight lines (computed HERE, hermetically, over
    the offline builds merged into one mod root), both P-HUBLEG records, P-PARTYREMOVE (its four reads judged by
    rung5b_hub.partyremove_verdict), NC-THROW, every autosave read (freshness judged as party_read judges it).
THE BASE MUST PASS EVERY CHECK AND OUTPUT "VERDICT: PROVEN".

THE FROZEN NUMBERS are re-derived (== the frozen file, printed): the stamp sites and entry ips off the built hubs'
bytes; the pick's party ops off the bytes and the four P-PARTYREMOVE slots off them (the engine's first-empty-slot
fill); LAND (53 bits F5B, 55 CTL), HAND-BACK (R, 34 bits; 41 CTL) off the constructed pairs' reconstructed states;
SUPP's split off the evidence in S's own windows (3 PROVEN with 13/13/17, 3/3/3, 2/2/2 dominated rows; 5 BLIND with
none); the arrival burst (8 stock keys, 11 F5B) and CTL's FORK ONLY / STOCK ONLY; the echo and step-1 rows off S's
windows; class (iii)'s UInt16[251].

Then MUTANTS, one per way the world could differ, each registered twice -- in :data:`REGISTERED` (the key, check and
verdict the dry-run holds it to) and in the predictions (checks.<check>.mutants, written from REGISTERED by the
freeze) -- and each must come out AS REGISTERED: the check's verdict, and where registered the note it must carry,
the other checks' verdicts, the stop class, THE HALT, the re-run plan, the verdict line. A registered mutant that
comes out otherwise is a defect of the analysis or of the construction, never a reason to weaken the mutant. The
registry and the frozen file must agree case for case, and every registered case must run. And the OFFLINE
PRE-FLIGHT cases (design section 6): the built hubs PASS P-HUB, P-PARTYOPS and P-ENTRY; a hub built with entrance 2
FAILs P-ENTRY's value clause, one with its entrance store before a stamp its order clause; the CTL hub read as F5B's
FAILs P-HUB and P-PARTYOPS; the hub's option and row text edited FAIL P-HUB's text clauses; F5's hub in the manifest
FAILs P-MANIFEST; a ForkDonorPatch row for 31113 FAILs P-DEPLOY's per-hub clause; P-PINS FAILs when the real pins
SKIP; a Memoria.ini with the removes inert FAILs P-INI; the static pre-flight PASSes hermetically (its own Memoria.ini
holds the frozen switches); v3's carried P-HUB / P-PURE cases FAIL. The clauses that read only STOCK bytes (P-ENTRY's
exit_fold over 352 and 351's entrance dispatch) and rung3_trace.preflight's own (P-FLOOR, P-EXITS, P-STOCK, P-DEPLOY's
member clauses) are shown to PASS here only: their FAIL cases are the dry-runs that own them (rung3's, rung5's).

This proves the ANALYSIS, not the prediction: the base construction encodes the predicted world, so it passing says
only that the checks read what they claim to. The session decides the prediction. Exit 0 only when the base passes
every check with VERDICT PROVEN, every number re-derives, and every case comes out as registered; one line per case.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dali_tour as D  # noqa: E402
import rung3_dryrun as RD  # noqa: E402
import rung3_trace as R  # noqa: E402
import rung5_dryrun as RD5  # noqa: E402
import rung5_hub as H5  # noqa: E402
import rung5b_hub as M  # noqa: E402
from dali_tour import T  # noqa: E402

SESSION5 = RD.main_repo() / ".harness-runs" / "20260928-153015-story-rung5"
SESSION3 = RD.main_repo() / ".harness-runs" / "20260926-101447-story-rung3c"
WORD = M.WORD
FORKS = M.FORKS
S_OF = {1: 1, 4: 3, 7: 5}                                 # F5b's stock run i <- session 5's S#k
NG_SLOT = [0, 255, 255, 255]                              # New Game's party slots (E20; Memoria ff9play.cs:74-78)
CLOCK = 1_790_000_000_000_000_000                         # the constructed autosave clock (ns): only its order is read
NOISE_BITS = ("Global.Bit[191]", "Global.Bit[184]")      # the prologue's story-noise bits (flags.story_noise_bits)

#: EVERY registered case: ``key -> (check, verdict, why)``. The freeze writes each into the predictions (the check's
#: "mutants", ``[why, verdict]``); the dry-run runs each exactly once and holds it to its verdict. Keys prefixed
#: ``pf-`` are the offline pre-flight cases, ``pass-`` the cases that must PASS.
REGISTERED = {
    # -- carried from v3 (rung5_dryrun), each re-cast for an entry past the wake --------------------------------------
    "reach-all-break": ("R5-REACH", "FAIL", "all 3 F5B runs break at replay step 14 of walk[1:] (350.6 -> 450, "
                                            "entered 355): THE HALT"),
    "reach-all-landing": ("R5-REACH", "FAIL", "all 3 F5B landings soft-lock in member(351) (FORK-STOP landing@351): "
                                              "THE HALT"),
    "reach-rerun-halt": ("R5-REACH", "FAIL", "F5B#2 FORK-STOPs at replay step 14, its re-run on S#1 at the same "
                                             "point (R5-RUNS VOID, no structural fault)"),
    "runs-after-halt": ("R5-RUNS", "FAIL", "a re-run after THE HALT"),
    "reach-one-stop": ("R5-REACH", "VOID", "one F5B FORK-STOP (F5B#2 at replay step 14) reproduced nowhere: its "
                                           "re-run on S#1 covered; VERDICT NOT PROVEN: walk"),
    "reach-landing-norow": ("R5-REACH", "FAIL", "(guard, the landing) F5B#2 and its re-run: the leg returned in 31101 "
                                                "and a live soft-lock stopped each before member(351) wrote a row -- "
                                                "FORK-STOP landing@351, never DRIVE"),
    "reach-budget-norow": ("R5-REACH", "PASS", "(guard, the hub leg's budget) F5B#2's own hub_s ran out after its "
                                               "stamps, no row in 31101: DRIVE; its re-run covered"),
    "reach-budget-rows": ("R5-REACH", "PASS", "(guard, the hub leg's budget) the same with member(351)'s first 20 rows "
                                              "traced: DRIVE, never UNCLASSED"),
    "reach-landing-wait": ("R5-REACH", "PASS", "(guard, the landing wait) F5B#2's wait for 31101 timed out though its "
                                               "trace has 20 rows there: DRIVE (the harness's view)"),
    "reach-poll-ack": ("R5-REACH", "VOID", "(guard, the hub FORK-STOP's text) the stamps landed, no row in 31101, and "
                                           "the stop is a poll's ack: UNCLASSED"),
    "prefix-truncated": ("R5-PREFIX", "FAIL", "a truncated F5B run (a DRIVE stop, the session budget, at replay step "
                                              "15) carrying one key its partner's window lacks"),
    "reach-door": ("R5-REACH", "PASS", "F5B#2 stops on 'the gated door was never faced' (DRIVE), its re-run covered"),
    "reach-soft-lock": ("R5-REACH", "FAIL", "(guard, the frozen stop-class table) F5B#2 and its re-run raise a live "
                                            "soft-lock in the replay in member(350) at 2600: FORK-STOP scene@350@2600"),
    "reach-unclassed": ("R5-REACH", "VOID", "(guard) F5B#2 stops for a reason no pattern names: UNCLASSED keeps "
                                            "R5-REACH from PASS"),
    "join-hub-raised": ("R5-JOIN", "PASS", "F5B#2's hub leg raised before the pick (prologue rows only): DRIVE, never "
                                           "digested; its re-run covered"),
    "prefix-all-hub-raised": ("R5-PREFIX", "VOID", "(guard, the VOID branch) every F5B hub leg raised before the "
                                                   "pick: none reached 31101"),
    "join-all-skipped": ("R5-JOIN", "VOID", "(guard, the VOID branch) every run skipped -- the session budget spent "
                                            "before run 1"),
    "reach-hub-died": ("R5-REACH", "PASS", "(guard, the frozen stop-class rule) F5B#2's game died in the hub AFTER its "
                                           "stamps (the trace never closed): DRIVE, never FORK-STOP hub"),
    "stamp-wrong-entry": ("R5-STAMP", "FAIL", "F5B#2's stamps landed, then its first member row is in 31104, never "
                                              "31101 (FORK-STOP hub)"),
    "stamp-source-pre": ("R5-STAMP", "FAIL", "R5-STAMP fed r['pre'] (from_start's FIELD list) as its rows: the base "
                                             "(the STAMP_SOURCE guard)"),
    "stamp-297-dropped": ("R5-STAMP", "FAIL", "the F5B hub's 297 stamp dropped"),
    "stamp-bit-write": ("R5-STAMP", "FAIL", "an extra F5B hub Bit write (e2 t3 ip 180 Bit[2065] := 1)"),
    "stamp-don-351": ("R5-STAMP", "FAIL", "the F5B hub's rows carry don 351"),
    "stamp-ip-off": ("R5-STAMP", "FAIL", "an F5B hub stamp's ip off by one (SC at 137)"),
    "stamp-width": ("R5-STAMP", "FAIL", "an F5B hub UInt16[296] := 192 after its 297 stamp: the exact list AND the "
                                        "width clause"),
    "stockstate-297": ("R5-STOCKSTATE", "FAIL", "stock 359 +220 UInt16[297] := 3 in every stock run"),
    "stockstate-extra-byte": ("R5-STOCKSTATE", "FAIL", "S#1 changes one more byte before the wake"),
    "stockstate-contradiction": ("R5-STOCKSTATE", "VOID", "S#1's 352 +2096 Bit[2078] := 1 row dropped, not "
                                                          "re-seated: a named contradiction (R5B-LAND/STATE VOID too)"),
    "noseam-450-real": ("R5-NOSEAM", "FAIL", "F5B rows from 450 on left in the real fields (F0-style)"),
    "partial-drop-one": ("R5-PARTIAL", "FAIL", "a stock key dropped from F5B#5 alone"),
    "mirror-drop-all": ("R5-MIRROR", "FAIL", "the same stock key dropped from every F5B run (STOCK ONLY)"),
    "mirror-extra-all": ("R5-MIRROR", "FAIL", "an extra key in every F5B run (FORK ONLY, not SUPP)"),
    "mirror-clobber": ("R5-MIRROR", "FAIL", "a member word store clobbering 297 (member(351) e4 SByte[296] run as "
                                            "UInt16[296] := 65472)"),
    "advance-moved": ("R5-ADVANCE", "FAIL", "the 2610 row moved to member(356) in every F5B run"),
    "advance-never": ("R5-ADVANCE", "FAIL", "F5B#8 replays its whole slice and never advances (passes exhausted)"),
    "latch-2085": ("R5-LATCH", "FAIL", "Bit[2085] := 1 (450 e19) dropped from every F5B run"),
    "join-ip-off": ("R5-JOIN", "FAIL", "one member row's ip off by one (F5B#2)"),
    "donor-999": ("R5-DONOR", "FAIL", "one member row with don 999 (F5B#2)"),
    "runs-order": ("R5-RUNS", "FAIL", "the wrong order (S F5B F5B CTL S CTL ...)"),
    "runs-partner": ("R5-RUNS", "FAIL", "the wrong partner (F5B#5 partners S#1)"),
    "runs-twins": ("R5-RUNS", "FAIL", "two covered F5B runs on one partner (a re-run F5B on S#1)"),
    "frozen-edited": ("P-FROZEN", "FAIL", "(guard) the predictions edited after the session recorded them"),
    "reach-two-walks": ("R5-REACH", "VOID", "(guard, the replay point) F5B#2 breaks at replay step 14 of S#1's walk, "
                                            "F5B#5 at step 14 of session 3's S#7 walk: two points, no halt"),
    "pass-walks-differ": ("R5-PARTIAL", "PASS", "pairs whose walks differ between pairs (session 3's S#7 as S#4, "
                                                "F5B#5 and CTL#6 on it) and agree within each: listed"),
    # -- new in F5b (design section 6's table) --------------------------------------------------------------------
    "replay-whole-walk": ("R5-RUNS", "VOID", "an F5B log replaying the WHOLE walk (352.0 -> 351 included): F5B#2 VOID, "
                                             "named by replay_why5b"),
    "ctl-gate-skip": ("R5-RUNS", "PASS", "CTL partnered with a walk whose step 2 is 351.1 -> 352: skipped, not run; "
                                         "the plan picks another S (CTL on S#7), and that re-run is recorded"),
    "ctl-gate-rerun-wrong": ("R5-RUNS", "FAIL", "the same, but the CTL re-run is driven on S#4, whose walk fails the "
                                                "CTL gate"),
    "f5b-gate-skip": ("R5-RUNS", "VOID", "F5B partnered with a walk whose step 1 is not 352.0 -> 351: VOID, named, "
                                         "not driven; the plan names a fresh S"),
    "supp-proven-no-evidence": ("R5-MIRROR", "FAIL", "a SUPP-PROVEN key (351 e0 +132) with S#1's dominated evidence "
                                                     "rows removed"),
    "supp-blind-value": ("R5-MIRROR", "FAIL", "a SUPP-BLIND key (351 e0 +1377 Byte[8]) written with another value in "
                                              "every F5B run"),
    "supp-proven-stock-value": ("R5-MIRROR", "FAIL", "STOCK's own value at the SUPP-PROVEN site moves: S#1/#4/#7 emit "
                                                     "351 e0 +132 Int16[11] = -2 before the wake and count it -2 "
                                                     "after, re-seated, while every F5B writes the frozen -1: the "
                                                     "S-side value check refuses it (and 352 +132, re-seated off "
                                                     "same:1); CTL's (c) FAILs by the same supp_ok"),
    "supp-blind-stock-value": ("R5-MIRROR", "FAIL", "STOCK's own value at a SUPP-BLIND site moves: S#1/#4/#7 emit 351 "
                                                    "e0 +1377 Byte[8] = 124 before the wake and count it 124 after, "
                                                    "re-seated, while every F5B writes the frozen 125: the blind "
                                                    "tier's value check -- its only guard -- refuses it (and 352 "
                                                    "+646); CTL's (c) FAILs by the same supp_ok"),
    "step1-no-crossing": ("R5-MIRROR", "PASS", "every partner's walk[1:] never crosses 352.0 -> 351 (that exit "
                                               "renumbered in S's logs) and no F5B runs 352 e14 t2: both stock "
                                               "step-1 keys EXCUSED (R5-PARTIAL PASS too)"),
    "step1-dropped": ("R5-MIRROR", "FAIL", "every F5B's fresh 352 e14 t2 +116 Bit[2103] = 0 row dropped while its walk "
                                           "still crosses 352.0 -> 351: STOCK ONLY, not excused"),
    "party-stale-landing": ("R5B-PARTY", "VOID", "every F5B landing read with an unchanged mtime; VERDICT NOT PROVEN: "
                                                 "party"),
    "partyremove-inert": ("R5B-PARTY", "FAIL", "P-PARTYREMOVE r3 = [0,2,3,1] (the removes inert); VERDICT FAILED"),
    "partyremove-uncalibrated": ("R5B-PARTY", "VOID", "the party instrument never calibrates -- the CTL pick's adds do "
                                                      "not show in the autosave: P-PARTYREMOVE r1 AND every CTL "
                                                      "landing read [0,255,255,255] (one cause, read twice): "
                                                      "P-PARTYREMOVE, R5B-CONTROL (e) and R5B-PARTY VOID; VERDICT NOT "
                                                      "PROVEN: party"),
    "partyremove-stale-r3": ("P-PARTYREMOVE", "VOID", "r3 re-reads r2's file (the F5B pick's landing wrote no "
                                                      "autosave): not fresh -- VOID, never the FAIL its stale "
                                                      "[0,2,3,1] would fake; R5B-PARTY VOID"),
    "party-unstable-landing": ("R5B-PARTY", "VOID", "every F5B landing read's sha changed between its two reads 10 "
                                                    "frames apart (stable False): not fresh"),
    "party-end-entrance": ("R5B-PARTY", "VOID", "F5B#2's run-end read names Int16[2] 99, not the trace's last entry: "
                                                "that read VOID"),
    "party-hubleg-save": ("R5B-PARTY", "VOID", "latches pass, party VOID (both P-HUBLEG autosave clauses failed "
                                               "twice): VERDICT NOT PROVEN: party"),
    "one-ctl": ("R5B-CONTROL", "VOID", "every other check PASS but only 1 covered CTL: VERDICT NOT PROVEN: state, "
                                       "latches, party (uncalibrated)"),
    # -- the R5B checks, each shown able to PASS, FAIL and go VOID -----------------------------------------------------
    "nowake-entrance-4": ("R5B-NOWAKE", "FAIL", "F5B#2's pick entered member(352) at entrance 4: the wake replays"),
    "nowake-none-reached": ("R5B-NOWAKE", "VOID", "every fork hub leg raised before the pick: no fork run reached a "
                                                  "member"),
    "control-no-recompute": ("R5B-CONTROL", "FAIL", "the rooms do not recompute the ATE state from the latches as "
                                                    "read (CTL's 351 arrival runs stock's ATE(1) burst): clauses (a) "
                                                    "and (c) FAIL, R5B-STATE and R5B-ARRIVAL VOID"),
    "land-latches-missing": ("R5B-LAND", "FAIL", "the reverse half-fixed seed: the F5B hub without its 2078/2086 "
                                                 "stamps (the removes kept) -- 351 takes ATE(0) as CTL does, the "
                                                 "lobby exit's ip105 and 450's ip338 do not fire, 350's mask is 8: "
                                                 "the latch-half checks catch it"),
    "land-contradiction": ("R5B-LAND", "VOID", "F5B#2's SC stamp row lost, not re-seated: bytes 0/1 were known (the "
                                               "field-70 residue), so the 2610 advance's old contradicts -- a "
                                               "reconstruction contradiction, named"),
    "land-first-value": ("R5B-LAND", "VOID", "F5B#2's Bit[2078] stamp row lost, not re-seated: its first-seen old "
                                             "is 1 where stock's is 0 -- the New Game values disagree, named"),
    "land-uncalibrated": ("R5B-LAND", "VOID", "(guard, the uncalibrated rule) stock 359 +220 UInt16[297] := 3: "
                                              "R5B-LAND sees byte 297 differ, but R5B-CONTROL (b) FAILs on the same "
                                              "byte, so it is VOID -- an uncalibrated difference is never a FAIL"),
    "state-byte-19": ("R5B-STATE", "FAIL", "the F5B hub also stamps UInt16[19] := 15 (R's byte 19 no longer "
                                           "differs)"),
    "state-short-pairs": ("R5B-STATE", "VOID", "F5B#8 VOID (a DRIVE stop, no re-run): 2 covered pairs"),
    "echo-2086-missing": ("R5B-ECHO", "FAIL", "450 e0 ip338 Bit[2086] 1 -> 0 lost from every F5B run"),
    "echo-uncalibrated": ("R5B-ECHO", "VOID", "CTL's step-1 crossing has an ip105 row: R5B-CONTROL (d) FAIL"),
    "arrival-extra": ("R5B-ARRIVAL", "FAIL", "every F5B landing burst also writes 351 e0 +791 SByte[238] = 0"),
    "arrival-uncalibrated": ("R5B-ARRIVAL", "VOID", "CTL's landing burst lacks +791: R5B-CONTROL (c) FAIL"),
    "party-slot": ("R5B-PARTY", "FAIL", "every F5B landing and run-end slot reads [0,2,3,1], fresh"),
    "party-footprint": ("R5B-PARTY", "VOID", "a party-footprint row (350 e33 Byte[303] := 0) in S#1's and F5B#2's "
                                             "windows"),
    "party-control-e": ("R5B-PARTY", "VOID", "every CTL landing slot reads [0,255,255,255]: R5B-CONTROL (e) FAIL -- "
                                             "the party instrument uncalibrated, so R5B-CONTROL is VOID (never "
                                             "FAIL) and the verdict NOT PROVEN: party"),
    "reach-ctl-stops": ("R5-REACH", "PASS", "(guard) CTL#3 and CTL#6 FORK-STOP at landing@351: listed, never THE "
                                            "HALT (F5B's alone)"),
    "nc-throw": ("NC-THROW", "FAIL", "(guard) NC-THROW recorded a throw: VERDICT FAILED: NC-THROW"),
    "hubleg-failed": ("P-HUBLEG", "FAIL", "the recorded F5B leg FAILED (the session would have stopped there): "
                                          "VERDICT FAILED: P-HUBLEG"),
    "hubleg-missing": ("P-HUBLEG", "VOID", "no CTL leg recorded: P-HUBLEG VOID, the verdict NOT PROVEN"),
    # -- the offline pre-flight ---------------------------------------------------------------------------------------
    "pf-built-hubs": ("P-HUB", "PASS", "the built hubs PASS P-HUB (both), P-PARTYOPS and P-ENTRY"),
    "pf-entrance-2": ("P-ENTRY", "FAIL", "the F5B hub built with entrance 2"),
    "pf-ctl-as-f5b": ("P-PARTYOPS", "FAIL", "the CTL hub's bytes read as F5B's (P-HUB FAILs too)"),
    "pf-f5-hub-manifest": ("P-MANIFEST", "FAIL", "F5's hub (31100) listed as F5B's in the manifest"),
    "pf-pins-skip": ("P-PINS", "FAIL", "the census locator pointed at an empty directory: the real pins SKIP"),
    "pf-pins": ("P-PINS", "PASS", "the seven F5b resolver pins, each PASSED"),
    "pf-static": ("P-DEPLOY", "PASS", "preflight5b over the offline builds merged into one mod root: every static "
                                      "check PASS, in the frozen order"),
    "pf-hub-2610": ("P-HUB", "FAIL", "(carried) the F5B hub built with set_scenario 2610"),
    "pf-pure-450": ("P-PURE", "FAIL", "(carried) 31103 built with 450 left unremapped"),
    "pf-pure-seeded": ("P-PURE", "FAIL", "(carried) a chain seeded by story-seed without --hub (a prepend)"),
    "pf-ini": ("P-INI", "FAIL", "a Memoria.ini with AllCharactersAvailable = 2 (RemoveParty a no-op) and "
                                "DisableAutoSave = 1"),
    "pf-entry-order": ("P-ENTRY", "FAIL", "the F5B hub with its Int16[2] := 6 store swapped with the UInt16[208] "
                                          "stamp (the entrance stored before a stamp): the order clause"),
    "pf-hub-texts": ("P-HUB", "FAIL", "the F5B hub's menu option and a row data line changed in its hub.field.toml "
                                      "and journeys.toml (the bytes as frozen): the text clauses"),
    "pf-deploy-hub-fork": ("P-DEPLOY", "FAIL", "the merged root with a ForkDonorPatch row for 31113: the per-hub "
                                               "install clause"),
}

#: THE VERDICT LINE each case registers (predictions checks.VERDICT.mutants, written from here by the freeze): the
#: line must START with the first text and hold every later one. "base" is the base construction.
NP_PARTY = ("NOT PROVEN: party (", "-- proven: state, latches, walk")
VERDICT_LINES = {
    "base": ("PROVEN: every check PASS",),
    "reach-all-break": ("FAILED: R5-REACH",),
    "reach-one-stop": ("NOT PROVEN: walk (R5-REACH: VOID", "-- proven: state, latches, party"),
    "party-stale-landing": NP_PARTY,
    "party-end-entrance": NP_PARTY,
    "party-hubleg-save": NP_PARTY,
    "partyremove-inert": ("FAILED: P-PARTYREMOVE, R5B-PARTY -- P-PARTYREMOVE:",),
    "partyremove-uncalibrated": ("NOT PROVEN: party (P-PARTYREMOVE: VOID", "R5B-CONTROL(e): not PASS",
                                 "-- proven: state, latches, walk"),
    "partyremove-stale-r3": ("NOT PROVEN: party (P-PARTYREMOVE: VOID", "-- proven: state, latches, walk"),
    "party-unstable-landing": NP_PARTY,
    "party-control-e": ("NOT PROVEN: party (", "R5B-CONTROL(e): not PASS", "-- proven: state, latches, walk"),
    "hubleg-failed": ("FAILED: P-HUBLEG -- ",),
    "land-latches-missing": ("FAILED: R5-PREFIX, R5-STAMP, R5B-LAND, R5B-STATE, R5B-ECHO, R5B-ARRIVAL, R5-MIRROR, "
                             "R5-PARTIAL, R5-LATCH -- ",),
    "hubleg-missing": ("NOT PROVEN: party, other (", "P-HUBLEG: VOID", "-- proven: state, latches, walk"),
    "one-ctl": ("NOT PROVEN: state, latches, party (", "-- proven: walk"),
    "control-no-recompute": ("FAILED: R5B-CONTROL -- ",),
    "land-uncalibrated": ("FAILED: R5-STOCKSTATE, R5B-CONTROL -- ",),
    "nc-throw": ("FAILED: NC-THROW -- ",),
}
VERDICT_WHY = {"base": "the base construction (session 5's stock runs; F5B and CTL on the built hubs' bytes)"}


def registered_mutants() -> dict:
    """``{check: [[why, outcome]]}`` -- every registered case as the predictions freeze it: REGISTERED's verdicts
    under their checks, and VERDICT_LINES under VERDICT (the line's texts joined by " ... ")."""
    out: dict = {}
    for _key, (cid, verdict, why) in REGISTERED.items():
        out.setdefault(cid, []).append([why, verdict])
    for key, texts in VERDICT_LINES.items():
        out.setdefault("VERDICT", []).append([VERDICT_WHY.get(key) or REGISTERED[key][2], " ... ".join(texts)])
    return out


# ======================================================================== the bytes
def built_bytes(build: Path, want: dict) -> tuple:
    """``(ok, detail, {id: US .eb bytes})`` of an offline build (``<build>/<id>/``) against ``{id: frozen sha}``."""
    got, bad = {}, []
    for fid, sha in sorted(want.items()):
        data = H5.built_eb(build, fid)
        if data is None:
            bad.append(f"{fid}: no US .eb")
            continue
        got[fid] = data
        if hashlib.sha256(data).hexdigest() != sha:
            bad.append(f"{fid}: sha {hashlib.sha256(data).hexdigest()[:12]}, frozen {sha[:12]}")
    return not bad, "; ".join(bad) or f"{len(got)} US .eb files, each its frozen sha", got


def merged_root(out: Path, dirs: dict) -> Path:
    """ONE mod root holding the offline builds ``{id: <build dir>/<id>}`` (rung5_dryrun.merged_root over two build
    trees) -- the stand-in for FF9CustomMap after the deploy, so the static pre-flight runs hermetically."""
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    dp, fdp = [], []
    for fid, src in sorted(dirs.items()):
        shutil.copytree(src / "StreamingAssets", out / "StreamingAssets", dirs_exist_ok=True)
        dp += [ln for ln in (src / "DictionaryPatch.txt").read_text(encoding="utf-8").splitlines() if ln.strip()]
        if (src / "ForkDonorPatch.txt").is_file():
            fdp += [ln for ln in (src / "ForkDonorPatch.txt").read_text(encoding="utf-8").splitlines()
                    if ln.strip() and not ln.startswith("#")]
    (out / "DictionaryPatch.txt").write_text("\n".join(dp) + "\n", encoding="utf-8")
    (out / "ForkDonorPatch.txt").write_text("# merged offline builds\n" + "\n".join(fdp) + "\n", encoding="utf-8")
    return out


def party_after(slots: list, ops: list) -> list:
    """The four party slots after a pick's ops (rung5b_hub.party_ops' ``[[op, arg, off]]``), as the engine applies
    them (EventEngine.cs:875-915): RemoveParty empties the slot that holds the member, B_PARTYADD puts one not in the
    party into the first empty slot."""
    out = list(slots)
    for op, arg, _off in ops:
        if op == "remove" and arg in out:
            out[out.index(arg)] = 255
        elif op == "add" and arg not in out and 255 in out:
            out[out.index(255)] = arg
    return out


# ======================================================================== the fork sides, constructed
def _w(like: dict, fld: int, don: int, sid: int, tag: int, ip: int, tgt: str, value: int) -> dict:
    """A same-value ``w`` row at a real store site (its old re-seated after)."""
    w, byte, bit = RD5.parse_target(tgt)
    return {"k": "w", "f": like["f"], "p": like["p"], "m": 1, "fld": fld, "don": don, "sc": like["sc"], "src": "eb",
            "sid": sid, "uid": sid, "lvl": 0, "ip": ip, "tag": tag, "add": 0, "byte": byte, "w": w, "bit": bit,
            "old": value, "new": value, "same": 1}


def _place_at(entries: list, lo: int, hi: int, row: dict, template: list) -> int:
    """Where one visit (``entries[lo:hi]``) runs ``row``: after the last row of the SAME function with a smaller ip,
    else before the first with a larger one (straight-line code order); with none of its function in the visit,
    after the last row the donor's own first visit ran before it (``template``: its ``(sid, tag, ip)`` order)."""
    fn = (row["sid"], row["tag"])
    same = [j for j in range(lo, hi) if entries[j][0] != "s" and entries[j][2]["k"] == "w"
            and (entries[j][2]["sid"], entries[j][2]["tag"]) == fn]
    if same:
        before = [j for j in same if entries[j][2]["ip"] < row["ip"]]
        return before[-1] + 1 if before else min(j for j in same if entries[j][2]["ip"] > row["ip"])
    n = template.index((row["sid"], row["tag"], row["ip"]))
    before = [j for j in range(lo, hi) if entries[j][0] != "s" and entries[j][2]["k"] == "w"
              and (entries[j][2]["sid"], entries[j][2]["tag"], entries[j][2]["ip"]) in template
              and template.index((entries[j][2]["sid"], entries[j][2]["tag"], entries[j][2]["ip"])) < n]
    return before[-1] + 1 if before else lo


def _visit(entries: list, at: int, fld: int, *, tag0: bool = True) -> int:
    """The end of the visit starting at ``entries[at]``: the first later row of this side outside ``fld`` (or, with
    ``tag0``, a store with tag != 0 -- the arrival is all tag 0)."""
    return next((j for j in range(at + 1, len(entries)) if entries[j][0] != "s" and entries[j][2]["k"] in ("w", "r")
                 and (entries[j][2]["fld"] != fld or (tag0 and entries[j][2]["k"] == "w"
                                                      and entries[j][2]["tag"] != 0))), len(entries))


def fork_entries(s_rows: list, pred: dict, side: str, hub_sites: list, *, hub: list | None = None,
                 latches: bool | None = None) -> list:
    """A fork run (F5B or CTL) as re-seat entries, built from its partner's rows (the module docstring): the lead-in
    kept, the hub's rows (``hub``, default rung5_dryrun.hub_rows on the side's hub view), the partner's segment LOST,
    its rows from its first post-wake 351 row on relabelled into the members, the fresh emissions inserted, and on
    CTL the pre-phase row's own arrival. ``latches`` False on F5B: a hub WITHOUT its 2078/2086 stamps -- CTL's own
    351 arrival and first 350 mask, 450's ip338 consumer never firing, and every ATE mask the rooms recompute while
    stock's 2086 is still set (up to that ip338) losing its 4 (:func:`_no_latch_masks`). Not yet re-seated (a
    mutant edits the world first)."""
    latches = side != "CTL" if latches is None else latches
    members = M.chain(pred)
    fork_of = {d: f for f, d in members.items()}
    E = pred["entry"]
    donor, m_entry = E["donor"], E["member"]
    rel = RD.relabel(s_rows, members, until=None)
    wake = next(i for i, o in enumerate(s_rows) if RD5.is_wake(o, pred, {}))
    land = next(i for i, o in enumerate(s_rows) if i > wake and o["k"] in ("w", "r") and o["fld"] == donor)
    i359 = next(i for i, o in enumerate(s_rows) if o["k"] in ("w", "r") and o["fld"] == pred["start"]["S"])
    hub = RD5.hub_rows(s_rows, M.hub_view(pred, side), hub_sites) if hub is None else hub
    entries = [["both", s, f] for s, f in zip(s_rows[:i359], rel[:i359])]
    entries += [["new", None, h] for h in hub]
    entries += [["s", s, None] for s in s_rows[i359:land] if s["k"] in ("w", "r")]
    entries += [["both", s, f] for s, f in zip(s_rows[land:], rel[land:])]

    def pre_wake(fld):
        """The partner's pre-wake w rows in ``fld``, and its first visit's site order (the donor's own code order)."""
        rows = [o for o in s_rows[:wake] if o["k"] == "w" and o["fld"] == fld]
        first = next(i for i, o in enumerate(s_rows) if o["k"] in ("w", "r") and o["fld"] == fld)
        end = next((i for i in range(first + 1, wake) if s_rows[i]["k"] in ("w", "r") and s_rows[i]["fld"] != fld),
                   wake)
        return rows, [(o["sid"], o["tag"], o["ip"]) for o in s_rows[first:end] if o["k"] == "w"]

    def fresh(fld: int, keys: list, at: int, *, noise: bool = True) -> None:
        """Insert, into the visit at ``entries[at]``, the stores the partner counted there but a fresh fork emits:
        each registered key (its value the partner's own pre-wake same:1 row there) and the noise bits."""
        rows, template = pre_wake(fld)
        idx = H5.chain_map(pred)
        want = [(k["sid"], k["tag"], k["ip"], k["target"], k["value"]) for k in keys]
        if noise:
            want += [(o["sid"], o["tag"], o["ip"], RD5.target(o), o["new"]) for o in rows
                     if RD5.target(o) in NOISE_BITS and o["same"]]
        for sid, tag, ip, tgt, value in sorted(want, key=lambda x: (x[0], x[1], x[2])):
            src = [o for o in rows if (o["sid"], o["tag"], o["ip"]) == (sid, tag, ip) and RD5.target(o) == tgt
                   and o["same"] and o["new"] == value]
            assert src, f"{fld} e{sid} t{tag} ip{ip} {tgt}={value}: no pre-wake same:1 row -- the SUPP site moved"
            end = _visit(entries, at, idx[fld])
            row = _w(entries[at][2], idx[fld], fld, sid, tag, ip, tgt, value)
            entries.insert(_place_at(entries, at, end, row, template), ["new", None, row])

    supp = pred["supp"]["proven"] + pred["supp"]["blind"]
    at = next(i for i, e in enumerate(entries) if e[0] != "s" and e[2]["k"] == "w" and e[2]["fld"] == m_entry)
    if not latches:                   # the pre-phase row's own arrival: CTL's, or an F5B hub without its latches
        stock_only = {k["ip"] for k in pred["control"]["stock_only"]}
        end = _visit(entries, at, m_entry)
        for j in range(at, end):
            k_, s, f = entries[j]
            if k_ == "both" and f["k"] == "w" and (f["sid"], f["tag"]) == (0, 0) and f["ip"] in stock_only:
                entries[j] = ["s", s, None]
        fresh(donor, [k for k in supp if k["donor"] == donor] + pred["control"]["fork_only"], at)
        ab = pred["control"]["step1"]["absent"]
        entries = [["s", e[1], None] if e[0] == "both" and e[2]["k"] == "w" and e[2]["fld"] == m_entry
                   and (e[2]["sid"], e[2]["tag"], e[2]["ip"]) == (ab["sid"], ab["tag"], ab["ip"]) else e
                   for e in entries]
        # 350's arrival computes the ATE mask from the latches as read: with 2086 unset its mask loses 4 (12 -> 8),
        # and 251 (never set on CTL) becomes 8 -- the partner's 241 := 12 / 251 := 14 as CTL runs them
        m350 = fork_of[350]
        a350 = next(i for i, e in enumerate(entries) if e[0] != "s" and e[2]["k"] in ("w", "r")
                    and e[2]["fld"] == m350)
        visit = range(a350, _visit(entries, a350, m350))
        mask = next(entries[j][2]["new"] for j in visit if entries[j][0] == "both" and entries[j][2]["k"] == "w"
                    and RD5.target(entries[j][2]) == "Global.Int16[241]") & ~4        # (2087, 2086) is the mask's 4
        for j in visit:
            k_, s, f = entries[j]
            if k_ == "both" and f["k"] == "w" and RD5.target(f) in ("Global.Int16[241]", "Global.UInt16[251]"):
                entries[j] = [k_, s, dict(f, new=mask)]            # 241 := mask; 251 := 0 | mask (never set on CTL)
    else:
        fresh(donor, [k for k in supp if k["donor"] == donor], at)
    if side != "CTL":
        adv = pred["wake"]["donor"]
        m_adv = fork_of[adv]
        a352 = next(i for i, e in enumerate(entries) if i > at and e[0] != "s" and e[2]["k"] == "w"
                    and e[2]["fld"] == m_adv)
        fresh(adv, [k for k in supp if k["donor"] == adv], a352)
        s1 = pred["step1_keys"][0]
        x = next(i for i, e in enumerate(entries) if i > a352 and e[0] != "s" and e[2]["k"] == "w"
                 and e[2]["fld"] == m_adv and (e[2]["sid"], e[2]["tag"]) == (s1["sid"], s1["tag"]))
        end = next((j for j in range(x + 1, len(entries)) if entries[j][0] != "s" and entries[j][2]["k"] == "w"
                    and (entries[j][2]["fld"], entries[j][2]["sid"], entries[j][2]["tag"])
                    != (m_adv, s1["sid"], s1["tag"])), len(entries))
        src = next(o for o in s_rows[wake:land] if o["k"] == "w" and (o["sid"], o["tag"], o["ip"]) ==
                   (s1["sid"], s1["tag"], s1["ip"]) and o["same"] and o["new"] == s1["value"])
        row = _w(entries[x][2], m_adv, adv, s1["sid"], s1["tag"], s1["ip"], s1["target"], s1["value"])
        assert RD5.target(src) == s1["target"]
        entries.insert(_place_at(entries, x, end, row, []), ["new", None, row])
        if not latches:
            return _no_latch_masks(entries, pred, fork_of, at)
    return RD5.lose(entries, lambda f: False)


def _no_latch_masks(entries: list, pred: dict, fork_of: dict, at: int) -> list:
    """An F5B hub without its latches, after the landing (``entries[at]``): 450's Main_Init ip338 (the 2086
    consumer, pred echo[1]) never fires, and every ATE mask a room recomputes while stock's 2086 is still set --
    every Int16[241] store up to that ip338 -- loses its 4 (the bit 2086 gives it: 12 -> 8, as CTL's 350 arrival);
    each UInt16[251] store is the running OR of the masks written (251 |= 241, which stock's own rows obey), from 0
    (the hub stamps no 251, and 351's ATE(0) writes none). Count rows keep stock's last values."""
    e = pred["echo"][1]
    m450 = fork_of[e["donor"]]

    def is338(f) -> bool:
        return (f["k"] in ("w", "c") and f["fld"] == m450
                and (f["sid"], f["tag"], f["ip"]) == (e["sid"], e["tag"], e["ip"]))

    end338 = next((j for j, x in enumerate(entries) if j > at and x[0] != "s" and is338(x[2])), len(entries))
    last241, or251, out = 0, 0, []
    for j, (k_, s, f) in enumerate(entries):
        if j >= at and k_ != "s" and f["k"] == "w":
            t = RD5.target(f)
            if t == "Global.Int16[241]":
                last241 = f["new"] & ~4 if j < end338 else f["new"]
                f = dict(f, new=last241)
            elif t == "Global.UInt16[251]":
                or251 |= last241
                f = dict(f, new=or251)
        out.append([k_, s, f])
    return RD5.lose(out, lambda f: f["k"] == "w" and is338(f))


def fork_rows(s_rows: list, pred: dict, side: str, hub_sites: list, xform=None, **kw) -> list:
    """A fork run's rows: :func:`fork_entries`, the world edited by ``xform(entries)``, re-seated; CTL cut after its
    350 arrival (PrefixTour replays walk[1:2] and nothing after it)."""
    e = fork_entries(s_rows, pred, side, hub_sites, **kw)
    rows = RD5.reseat(xform(e) if xform else e)
    if side == "CTL":
        m350 = H5.chain_map(pred)[350]
        j = next(i for i, o in enumerate(rows) if o["k"] in ("w", "r") and o["fld"] == m350)
        k = next((i for i in range(j + 1, len(rows)) if rows[i]["k"] in ("w", "r")
                  and (rows[i]["fld"] != m350 or (rows[i]["k"] == "w" and rows[i]["tag"] != 0))), len(rows))
        rows = RD5.cut(rows, k)
    return rows


#: the hub leg's log record (hub_leg's keys; a constructed leg's numbers, the options the frozen ones)
HUB_REC = dict(RD5.HUB_REC, r=152, talk_r=338, approach=[304, 127, 176], at=[314, 127])
LANDING = {"k": "landing", "entry": 31101, "entrance": 6, "field": 31101, "place": 351, "sc": 2600, "control": True,
           "woke": False, "ok": True, "t": 1.2}


def fork_log(pred: dict, side: str, walk: list, *, steps=None, moved_at=None, diverge_at=None, stop=None,
             entered=None, landing: dict | None = None, pre: list | None = None) -> dict:
    """A fork run's log as rung5b_hub.run leaves one: the hub leg's record, the landing record, then
    rung3_dryrun.replay_log over the partner's walk SLICE (its keywords; ``entered`` the place a diverging step
    entered), the stop -- CTL's PrefixTour stop by default. ``pre`` replaces the hub + landing records."""
    lo, hi = pred["replay"][side]
    sl = walk[lo:hi]
    if side == "CTL" and stop is None and steps is None:
        lg = RD.replay_log(pred, sl, moved_at=len(sl) + 1, stop=f"{M.PREFIX_STOP} ({len(sl)} crossings, 4s)")
    else:
        lg = RD.replay_log(pred, sl, steps=steps, moved_at=moved_at, diverge_at=diverge_at, stop=stop)
    cross = lg["log"][1:]
    if entered is not None and cross:
        cross[-1].update(entered=entered, landed=entered, now=entered, verdict=f"diverged: entered {entered}")
    head = [dict(HUB_REC), dict(LANDING if landing is None else landing)] if pre is None else pre
    return dict(lg, log=[*head, *cross])


def replay_stop(pred: dict, walk: list, n: int, *, entered: int | None = None, why: str | None = None) -> dict:
    """An F5B log whose replay of ``walk[1:]`` broke at slice step ``n``: it ENTERED ``entered`` there, or -- ``why``
    -- stopped before entering anything."""
    sl = walk[pred["replay"]["F5B"][0]:]
    where = f"replay broke at step {n} ({D.step_name(sl[n - 1])})"
    if entered is None:
        return fork_log(pred, "F5B", walk, steps=n - 1, moved_at=len(sl) + 1, stop=f"{where}: {why}")
    return fork_log(pred, "F5B", walk, steps=n, moved_at=len(sl) + 1, diverge_at=n, entered=entered,
                    stop=f"{where}: entered {entered}")


def fork_step_at(rows: list, pred: dict, walk: list, n: int, side: str = "F5B") -> int:
    """The row where step ``n`` (1-based) of the REPLAYED SLICE lands, off the rows themselves: from the landing in
    the entry member, every change of place but one OUT of a room in rung3_dryrun.BOUNCERS is a step; checked
    against the slice step for step."""
    members = M.chain(pred)
    lo, hi = pred["replay"][side]
    sl = walk[lo:hi]
    start = next(i for i, o in enumerate(rows) if o["k"] in ("w", "r") and o["fld"] == pred["entry"]["member"])
    here, steps = pred["entry"]["donor"], []
    for i, o in enumerate(rows[start:], start):
        if o["k"] not in ("w", "r"):
            continue
        place = members.get(o["fld"], o["fld"])
        if place != here:
            if here not in RD.BOUNCERS:
                steps.append((i, here, place))
            here = place
    got = [[a, b] for _i, a, b in steps[:len(sl)]]
    assert got == [[a, b] for a, _e, b in sl], f"the rows' walk {got} is not the slice's"
    return steps[n - 1][0]


# ======================================================================== the autosave reads, constructed
def read_at(n: int, slot: list, sc: int, entrance: int, field: int, *, baseline: dict | None = None,
            want: dict | None = None, reserve=(0,), stable: bool = True) -> dict:
    """One autosave read as rung5b_hub.party_read records it (its fresh/why judged by the frozen rule against
    ``baseline`` / ``want``); ``n`` orders it on the constructed clock."""
    sha = hashlib.sha256(f"read {n} {slot} {sc} {entrance}".encode()).hexdigest()
    r = {"mtime_ns": CLOCK + n * 10 ** 9, "sha": sha,
         "time": round(100.0 + n, 1), "slot": list(slot), "sc": sc, "entrance": entrance, "reserve": list(reserve),
         "hp": [105, None, None, None], "status": [0, None, None, None], "field": field, "stable": stable}
    r["fresh"], r["why"] = M.freshness(r, baseline, want)
    return r


def parsed(rows: list) -> list:
    """Row dicts as the analysis reads their file (T.Row, lines 1-based)."""
    return [T.parse_row(o, line=n) for n, o in enumerate(rows, 1)]


# ======================================================================== a constructed session
def write_session(d: Path, plan: list, *, snap: dict, pred_path: Path, sha: str | None = None,
                  session: dict | None = None) -> None:
    """A session dir as rung5b_hub.run leaves one: ``plan`` = ``[{side, rows, log, rec}]`` in run order (``rows`` /
    ``log`` None: no file), the session record (the predictions file and its sha256, the pre-flight lines, the legs,
    P-PARTYREMOVE, NC-THROW -- ``session`` overriding any of them), the scripts snapshot."""
    pred, real_sha = M.load_predictions(pred_path)
    if d.exists():
        shutil.rmtree(d)
    (d / "scripts").mkdir(parents=True)
    for fid, data in snap.items():
        (d / "scripts" / f"{fid}.eb").write_bytes(data)
    recs = []
    for i, run in enumerate(plan, 1):
        tn, ln = R.run_names(i, run["side"])
        rec = {"i": i, "side": run["side"], "start": pred["start"][run["side"]], "trace": tn, "log": ln, "t0": 0,
               "t1": 0, **run.get("rec", {})}
        if not (rec.get("skipped") or str(rec.get("install", "")).startswith("before")):
            if run.get("rows") is not None:
                (d / tn).write_text("".join(json.dumps(o, separators=(",", ":")) + "\n" for o in run["rows"]),
                                    encoding="utf-8")
            if run.get("log") is not None:
                (d / ln).write_text(json.dumps(run["log"]), encoding="utf-8")
                rec.setdefault("stop", run["log"]["stop"])
        recs.append(rec)
    base = {"label": d.name, "predictions": str(pred_path), "predictions_sha256": sha or real_sha,
            "predictions_version": pred.get("version"), "lane": pred.get("lane"), "order": pred["order"],
            "budget": pred["budget"], "started": "dry-run", "finished": "dry-run", "runs": recs}
    (d / M.SESSION_FILE).write_text(json.dumps({**base, **(session or {})}), encoding="utf-8")


# ======================================================================== the construction, whole
class World:
    """Everything the base and every mutant are made of: the frozen predictions, the bytes, session 5's stock runs,
    the constructed fork runs, their reads and logs, and the session record's pre-flight parts."""

    def __init__(self, pred: dict, pred_path: Path, hub_eb: dict, snap: dict, s5: Path, preflight: list):
        self.pred, self.pred_path, self.hub_eb, self.snap, self.preflight = pred, pred_path, hub_eb, snap, preflight
        self.order = pred["order"]
        self.members = M.chain(pred)
        self.cmap = H5.chain_map(pred)
        self.sites = {s: H5.global_stores(hub_eb[s], field_id=pred["hubs"][s]["id"]) for s in FORKS}
        sess5 = json.loads((s5 / H5.SESSION_FILE).read_text(encoding="utf-8"))
        self.s_rows, self.s_logs, self.s_recs = {}, {}, {}
        for i, k in S_OF.items():
            rec = next(r for r in sess5["runs"] if r["i"] == k)
            self.s_rows[i] = RD5.rows_of(s5 / rec["trace"])
            self.s_logs[i] = json.loads((s5 / rec["log"]).read_text(encoding="utf-8"))
            self.s_recs[i] = {x: v for x, v in rec.items()
                              if x in ("segment", "traced", "crossings", "landed", "fields")}
        self.walks = {i: D.entered_walk(self.s_logs[i]["log"]) for i in S_OF}
        self.partner = {i: R.round_partner(self.order, i) for i, s in enumerate(self.order, 1) if s in FORKS}
        ops = {s: M.party_ops(hub_eb[s], pred["hubs"][s]["stamp"][0]["sid"], pred["hubs"][s]["stamp"][0]["tag"])
               for s in FORKS}
        self.ops = ops
        self.slot = {s: party_after(NG_SLOT, ops[s]) for s in FORKS}
        self.base = {s: {p: self.rows(s, p) for p in S_OF} for s in FORKS}

    # -- rows ---------------------------------------------------------------------------------------------------
    def rows(self, side: str, p: int, xform=None, *, s_rows=None, **kw) -> list:
        """``side``'s rows partnering stock run ``p`` (``s_rows``: that partner's rows), the world edited by
        ``xform(entries)`` before the re-seat."""
        return fork_rows(self.s_rows[p] if s_rows is None else s_rows, self.pred, side, self.sites[side], xform, **kw)

    def s_side(self, p: int, xform) -> list:
        """Stock run ``p``'s rows with the world edited by ``xform(entries)`` (its olds re-seated)."""
        return RD5.reseat(xform([["both", o, dict(o)] for o in self.s_rows[p]]))

    def hub_rows(self, side: str, p: int, fn=None) -> list:
        """``side``'s hub rows for S#p's partner, edited by ``fn``."""
        h = RD5.hub_rows(self.s_rows[p], M.hub_view(self.pred, side), self.sites[side])
        return fn(h) if fn else h

    # -- reads --------------------------------------------------------------------------------------------------
    def s_party(self, i: int, rows: list) -> dict:
        """S#i's two reads: right after its segment (the wake's room, entered at SC 2540 with 4) and at its end
        (the trace's last field entry)."""
        n = 100 * i
        base = read_at(n + 1, NG_SLOT, 2540, 4, 352)
        le = M.last_entry(parsed(rows), self.pred) or {"field": None, "sc": None, "entrance": None}
        return {"baseline": base, "end": read_at(n + 3, NG_SLOT, le["sc"], le["entrance"], le["field"], baseline=base,
                                                 want=le, reserve=(0, 1, 2, 3))}

    def fork_party(self, side: str, i: int, rows: list, *, slot=None, end_slot=None) -> dict:
        """A fork run's three reads: the pre-leg baseline (New Game's field-70 entry), the landing (31101 at SC 2600
        through entrance 6) and the run end (the trace's last field entry)."""
        n = 100 * i
        E = self.pred["entry"]
        slot = self.slot[side] if slot is None else slot
        base = read_at(n + 1, NG_SLOT, 0, 0, 70)
        want = {"sc": self.pred["beat"], "entrance": E["entrance"], "field": E["member"]}
        land = read_at(n + 2, slot, self.pred["beat"], E["entrance"], E["member"], baseline=base, want=want)
        le = M.last_entry(parsed(rows), self.pred) or {"field": None, "sc": None, "entrance": None}
        end = read_at(n + 3, slot if end_slot is None else end_slot, le["sc"], le["entrance"], le["field"],
                      baseline=land, want=le)
        return {"baseline": base, "landing": land, "end": end}

    # -- runs ---------------------------------------------------------------------------------------------------
    def s_run(self, i: int, rows=None, log=None, **rec) -> dict:
        rows = self.s_rows[i] if rows is None else rows
        return {"side": "S", "rows": rows, "log": self.s_logs[i] if log is None else log,
                "rec": {**self.s_recs[i], "phase": "settle", "party": self.s_party(i, rows), **rec}}

    def fork_run(self, side: str, i: int, p: int, rows=None, log=None, *, walk=None, party=None, **rec) -> dict:
        """Run ``i`` of ``side`` partnering S#p (``rows``/``log`` default the base's; ``walk`` the partner's)."""
        rows = self.base[side][p] if rows is None else rows
        walk = self.walks[p] if walk is None else walk
        log = fork_log(self.pred, side, walk) if log is None else log
        crosses = [x for x in log["log"] if x.get("k") == "cross"]
        out = {"partner": p, "walk": walk, "slice": list(self.pred["replay"][side]), "phase": "settle", "traced": 1,
               "landing": next((x for x in log["log"] if x.get("k") == "landing"), None),
               "crossings": len(crosses), "replayed": sum(1 for x in crosses if x.get("verdict") == "replayed"),
               "party": self.fork_party(side, i, rows) if party is None else party}
        return {"side": side, "rows": rows, "log": log, "rec": {**out, **rec}}

    def skipped(self, i: int, side: str, why: str | None = None) -> dict:
        """Run ``i`` recorded and not driven (the session's budget spent, or the walk gate)."""
        rec = {"skipped": why or f"session budget: under {self.pred['budget']['run_min_s'][side]}s of the "
                                 f"{self.pred['budget']['session_s']}s left"}
        if side in FORKS:
            rec["partner"] = self.partner.get(i)
        return {"side": side, "rows": None, "log": None, "rec": rec}

    def plan(self, runs=None, extra=()) -> list:
        """The frozen nine ([S F5B CTL] x3, each fork on its round's S), ``runs`` ``{i: run}`` overriding slot i,
        then the re-runs ``extra`` (each marked a re-run, as the session marks one)."""
        out = []
        for i, s in enumerate(self.order, 1):
            got = (runs or {}).get(i)
            out.append(got if got is not None else self.s_run(i) if s == "S" else
                       self.fork_run(s, i, self.partner[i]))
        n = len(out)
        return out + [dict(r, rec=dict(r["rec"], rerun=True), i=n + k) for k, r in enumerate(extra, 1)]

    def every(self, side: str, fn) -> dict:
        """``{i: fn(i, partner)}`` for the three ``side`` runs of the frozen order."""
        return {i: fn(i, p) for i, p in self.partner.items() if self.order[i - 1] == side}

    # -- the session record's parts ----------------------------------------------------------------------------
    def hubleg(self, ok_save: bool = True, *, failed: str | None = None, missing: str | None = None) -> dict:
        """Both P-HUBLEG records as the session keeps them: the leg passed, its hub-arrival read fresh against the
        pre-warp read and the New Game baseline (``ok_save`` False: the clause failed twice). ``failed``: that side's
        leg FAILED (a record the session stops on); ``missing``: no record for that side."""
        out = {}
        for k, side in enumerate(FORKS):
            if side == missing:
                continue
            H = self.pred["hubs"][side]
            pre = read_at(10 + 2 * k, NG_SLOT, 0, 0, 70)
            fid, entrance, sc = H["lead_in"]
            arr = read_at(11 + 2 * k, NG_SLOT if ok_save else NG_SLOT, sc if ok_save else 0, entrance, fid,
                          baseline=pre, want={"sc": sc, "entrance": entrance, "field": fid})
            save = dict(arr, ok=bool(arr["fresh"]) and arr["slot"] == self.pred["party"]["hubleg"],
                        why=arr["why"] + ([] if arr["slot"] == self.pred["party"]["hubleg"] else ["slot"]))
            out[side] = {"k": "hub", "hub": H["id"], "pre": pre, "save": save, "ok": True, "tries": 1 if ok_save else 2,
                         "detail": f"{H['name']}: Stiltzkin r 152, talk_r 338, 1 tries, options {H['options']}, stay "
                                   f"row stayed (1 presses); hub-arrival autosave "
                                   + ("OK" if save["ok"] else "NOT OK: " + "; ".join(save["why"]))}
            if side == failed:
                out[side].update(ok=False, detail="HarnessError: hub leg: no dialogue after 3 tries at [314, 127] "
                                                  "(Stiltzkin at [480, 127], r 152, talk_r 338)")
        return out

    def partyremove(self, *, stale_r3: bool = False, **slots) -> dict:
        """P-PARTYREMOVE's record: its four reads (``slots`` overriding r1/r2/r3), judged by the frozen rule.
        ``stale_r3``: the F5B pick's landing wrote no autosave, so r3 re-reads r2's file (its bytes, its mtime) in
        31101."""
        P = self.pred["party"]["partyremove"]
        E = self.pred["entry"]
        H = self.pred["hubs"]["F5B"]
        at_entry = {"sc": self.pred["beat"], "entrance": E["entrance"], "field": E["member"]}
        reads = {"r0": read_at(20, NG_SLOT, 0, 0, 70)}
        reads["r1"] = read_at(21, slots.get("r1", party_after(NG_SLOT, self.ops["CTL"])), self.pred["beat"],
                              E["entrance"], E["member"], baseline=reads["r0"], want=at_entry)
        fid, e0, sc0 = H["lead_in"]
        reads["r2"] = read_at(22, slots.get("r2", reads["r1"]["slot"]), sc0, e0, fid, baseline=reads["r1"],
                              want={"sc": sc0, "entrance": e0, "field": fid})
        reads["r3"] = read_at(23, slots.get("r3", party_after(reads["r2"]["slot"], self.ops["F5B"])),
                              self.pred["beat"], E["entrance"], E["member"], baseline=reads["r2"], want=at_entry)
        if stale_r3:
            r3 = dict(reads["r2"], field=E["member"])
            r3["fresh"], r3["why"] = M.freshness(r3, reads["r2"], at_entry)
            reads["r3"] = r3
        verdict, why = M.partyremove_verdict(reads, P)
        return {"k": "partyremove", "verdict": verdict, "why": why,
                "attempts": [{"k": "partyremove", "reads": reads, "verdict": verdict, "why": why}]}

    def session(self, **over) -> dict:
        """The session record's recorded parts (rung5b_hub.run's): the static pre-flight, both legs, P-PARTYREMOVE,
        NC-THROW -- ``over`` replacing any."""
        return {"preflight": [list(x) for x in self.preflight], "hubleg": self.hubleg(),
                "partyremove": self.partyremove(), "nc_throw": {"ok": True, "detail": "[]"}, **over}


# ======================================================================== the numbers (re-derived)
def derive(world: World, runs: list, stock) -> dict:
    """Every frozen number, off the constructed base session's judged runs (rung5b_hub.read_session5b) and the
    bytes: ``{name: value}`` -- what the freeze writes and what the dry-run holds the frozen file to."""
    pred = world.pred
    by_i = {r["i"]: r for r in runs}
    out = {}
    skip = {pred["timing_site"]["byte"]}

    def state(r, line):
        return H5.reconstruct(r["raw"], line, saturate=pred["stockstate"]["saturate"])

    def diff(f, s, which):
        cf, cs = M.cuts(f, pred), M.cuts(s, pred)
        rf, rs = state(f, cf[f"{which}_cut"]), state(s, cs[f"{which}_cut"])
        assert not rf["contradictions"] and not rs["contradictions"], "the base has a contradiction"
        sd = M.state_diff(rs, rf, skip)
        assert not sd["uncertain"] and not sd["first"], (sd["uncertain"], sd["first"])
        return {str(b): list(v) for b, v in sorted(sd["diff"].items())}

    pairs = {side: [(by_i[i], by_i[p]) for i, p in world.partner.items() if world.order[i - 1] == side]
             for side in FORKS}
    for name, side, which in (("land", "F5B", "land"), ("control_land", "CTL", "land"), ("residual", "F5B", "hand"),
                              ("control_hand", "CTL", "hand")):
        got = [diff(f, s, which) for f, s in pairs[side]]
        assert all(g == got[0] for g in got), f"{name}: the three pairs disagree"
        out[name] = got[0]
    # class (iii): UInt16[251] at the landing and after the arrival, both sides -- with the New-Game fallback
    # (state_diff's: a bit the side never touched before the cut reads its first-seen old)
    def byte_at(rc, b):
        vals = [rc["known"].get(b * 8 + j, rc["first"].get(b * 8 + j)) for j in range(8)]
        return None if any(v is None for v in vals) else sum(v << j for j, v in enumerate(vals))

    c251 = {}
    for f, s in pairs["F5B"]:
        for lab, r, which in (("stock", s, "land"), ("F5B", f, "land"), ("stock_after", s, "hand"),
                              ("F5B_after", f, "hand")):
            v = byte_at(state(r, M.cuts(r, pred)[f"{which}_cut"]), 251)
            c251.setdefault(lab, set()).add(v)
    out["class_iii_251"] = {k: sorted(v) for k, v in c251.items()}
    # SUPP: the fork-only keys of the base comparison, split by the evidence in S's own windows
    s_win = [by_i[i] for i in S_OF]
    fk = set.intersection(*[M.keyset5b(f["digest"], pred) for f, _s in pairs["F5B"]])
    sk = set.union(*[M.keyset5b(s["window"], pred) for s in s_win])
    fork_only = sorted(fk - sk)
    ev = {}
    for k in fork_only:
        ev[k] = []
        for s in s_win:
            ok, why = M.supp_ok({**pred, "supp": {"proven": [dict(zip(("donor", "sid", "tag", "off", "target",
                                                                       "value"), k))], "blind": []}}, k, s, stock)
            m = re.search(r"proven: (\d+) dominated", why)
            ev[k].append(int(m.group(1)) if ok and m else 0)
    out["supp_evidence"] = {"|".join(map(str, k)): v for k, v in ev.items()}
    out["supp_proven"] = sorted(k for k, v in ev.items() if all(v))
    out["supp_blind"] = sorted(k for k, v in ev.items() if not any(v))
    assert all(all(v) or not any(v) for v in ev.values()), "a SUPP key with evidence in some S runs only"
    # the arrival bursts: stock's step-1 arrival (8), F5B's (11), CTL's FORK ONLY / STOCK ONLY
    burst = {}
    for r in list(by_i.values()):
        c = M.cuts(r, pred)
        d = r["window"]
        burst[r["i"]] = M.burst_keys(d, c["land"].line, c["hand"].line if c["hand"] is not None else None)
    out["arrival_stock"] = sorted(set.intersection(*[burst[i] for i in S_OF]))
    assert all(burst[i] == burst[1] for i in S_OF), "the stock bursts differ"
    f_b = [burst[f["i"]] for f, _s in pairs["F5B"]]
    assert all(b == f_b[0] for b in f_b)
    out["arrival_f5b"] = sorted(f_b[0])
    c_b = [burst[f["i"]] for f, _s in pairs["CTL"]]
    out["ctl_fork_only"] = sorted(c_b[0] - burst[1])
    out["ctl_stock_only"] = sorted(burst[1] - c_b[0])
    # the echo rows, the step-1 keys, the hand-back cut: off S's windows
    echo = []
    for tgt in ("Global.Bit[2078]", "Global.Bit[2086]"):
        hits = {(x.fld, x.sid, x.tag, x.ip) for s in s_win for x in s["window_rows"]
                if x.k == "w" and x.target == tgt and x.old == 1 and x.new == 0 and not x.same}
        echo.append(sorted(hits))
    out["echo"] = echo
    step1 = []
    for s in s_win:
        w = H5.wake_row(s["raw"], pred, {})
        nxt = [x for x in s["raw"] if x.k == "w" and x.line > w.line][:2]
        step1.append([(x.fld, x.sid, x.tag, x.ip, x.target, x.new) for x in nxt])
    assert all(x == step1[0] for x in step1)
    out["step1"] = step1[0]
    out["hand_cut"] = sorted({(r["label"][:3], M.cuts(r, pred)["hand"].fld, M.cuts(r, pred)["hand"].sid,
                               M.cuts(r, pred)["hand"].tag, M.cuts(r, pred)["hand"].ip) for r in by_i.values()})
    # the bytes: the stamps, the stores, the party ops and the slots they leave
    out["stamps"] = {s: [(x["off"], x["ip"], x["target"], x["value"]) for x in world.sites[s]
                         if (x["sid"], x["tag"]) == (2, 3)] for s in FORKS}
    out["n_stores"] = {s: len(world.sites[s]) for s in FORKS}
    out["party_ops"] = world.ops
    r1 = party_after(NG_SLOT, world.ops["CTL"])
    out["partyremove"] = {"r1": r1, "r2": r1, "r3": party_after(r1, world.ops["F5B"])}
    out["landing_slots"] = dict(world.slot)
    return out


def check_numbers(pred: dict, got: dict) -> list:
    """``[(name, frozen, derived, ok)]``: every frozen number against its re-derivation."""
    kt = M.ktuple
    rows = []

    def add(name, frozen, derived):
        rows.append((name, frozen, derived, frozen == derived))

    add("LAND (R5B-LAND): bits", M.registered(pred["land"]["bits"]), M.registered(got["land"]))
    add("LAND: n_bits / bytes", (pred["land"]["n_bits"], pred["land"]["bytes"]),
        (len(got["land"]), sorted({int(b) >> 3 for b in got["land"]})))
    add("CTL LAND (R5B-CONTROL b): bits", M.registered(pred["control"]["land_bits"]),
        M.registered(got["control_land"]))
    add("CTL LAND: n_bits", pred["control"]["n_land"], len(got["control_land"]))
    add("HAND-BACK R (R5B-STATE): bits", M.registered(pred["residual"]["bits"]), M.registered(got["residual"]))
    add("HAND-BACK R: n_bits", pred["residual"]["n_bits"], len(got["residual"]))
    add("CTL HAND-BACK (R5B-CONTROL a): bits", M.registered(pred["control"]["handback_bits"]),
        M.registered(got["control_hand"]))
    add("CTL HAND-BACK: n_bits", pred["control"]["n_handback"], len(got["control_hand"]))
    add("SUPP-PROVEN keys", sorted(kt(k) for k in pred["supp"]["proven"]), got["supp_proven"])
    add("SUPP-BLIND keys", sorted(kt(k) for k in pred["supp"]["blind"]), got["supp_blind"])
    add("SUPP evidence (dominated rows per S run)", pred["supp"].get("evidence"), got["supp_evidence"])
    supp351 = {kt(k) for k in pred["supp"]["proven"] + pred["supp"]["blind"] if k["donor"] == pred["entry"]["donor"]}
    add("arrival: stock's step-1 burst (8 keys, every S window)",
        sorted({kt(k) for k in pred["arrival"]["keys"]} - supp351), got["arrival_stock"])
    add("arrival: F5B burst (R5B-ARRIVAL, 11 keys = the 8 + the three 351 SUPP)",
        sorted(kt(k) for k in pred["arrival"]["keys"]), got["arrival_f5b"])
    add("CTL burst: FORK ONLY (clause c)", sorted([kt(k) for k in pred["control"]["fork_only"]]
                                                  + [kt(k) for k in pred["supp"]["proven"] + pred["supp"]["blind"]
                                                     if k["donor"] == pred["entry"]["donor"]]),
        got["ctl_fork_only"])
    add("CTL burst: STOCK ONLY (clause c)", sorted(kt(k) for k in pred["control"]["stock_only"]),
        got["ctl_stock_only"])
    add("echo rows (R5B-ECHO)", [[(e["donor"], e["sid"], e["tag"], e["ip"])] for e in pred["echo"]], got["echo"])
    add("step-1 keys (R5-MIRROR's excusal)", [(k["donor"], k["sid"], k["tag"], k["ip"], k["target"], k["value"])
                                             for k in pred["step1_keys"]], got["step1"])
    add("stamps: F5B (off, ip, target, value)", [(s["off"], s["ip"], s["target"], s["value"])
                                                 for s in pred["hubs"]["F5B"]["stamp"]], got["stamps"]["F5B"])
    add("stamps: CTL (off, ip, target, value)", [(s["off"], s["ip"], s["target"], s["value"])
                                                 for s in pred["hubs"]["CTL"]["stamp"]], got["stamps"]["CTL"])
    add("store sites: F5B / CTL",
        (len(pred["hubs"]["F5B"]["static_stores"]), len(pred["hubs"]["CTL"]["static_stores"])),
        (got["n_stores"]["F5B"], got["n_stores"]["CTL"]))
    add("party ops: F5B", pred["hubs"]["F5B"]["party_ops"], got["party_ops"]["F5B"])
    add("party ops: CTL", pred["hubs"]["CTL"]["party_ops"], got["party_ops"]["CTL"])
    add("P-PARTYREMOVE slots r1/r2/r3", pred["party"]["partyremove"], got["partyremove"])
    add("landing slots F5B / CTL", pred["party"]["landing"], got["landing_slots"])
    add("class (iii) UInt16[251]: stock 6 / F5B 0 at the landing, 6 / 6 after the arrival",
        {"stock": [pred["class_iii"]["251"]["stock_at_landing"]], "F5B": [pred["class_iii"]["251"]["F5B_at_landing"]],
         "stock_after": [pred["class_iii"]["251"]["after_arrival"]],
         "F5B_after": [pred["class_iii"]["251"]["after_arrival"]]}, got["class_iii_251"])
    return rows


# ======================================================================== main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", help="an offline build of the two hubs (<DIR>/<id>/ each); default: built here from "
                                    "the predictions' tomls into a temp dir")
    ap.add_argument("--members", help="an offline build of the 12 members (<DIR>/<id>/ each); default: built here "
                                      "from rung5b_forks.json's tomls")
    ap.add_argument("--keep", help="write the constructed sessions and builds here (default: a temp dir, removed)")
    ap.add_argument("--session5", default=str(SESSION5), help="F5's session 5 (story-rung5) run dir; read only")
    ap.add_argument("--session3", default=str(SESSION3), help="session 3's run dir (story-rung3c); read only")
    ap.add_argument("--predictions", default=str(M.PREDICTIONS), help="the frozen predictions (default the v1 file)")
    ap.add_argument("--only", help="run only the cases whose key matches this regex (the base always runs)")
    a = ap.parse_args(argv)
    pred_path = Path(a.predictions)
    pred, _sha = M.load_predictions(pred_path)
    holes = M.missing_numbers(pred)
    if pred.get("lane") != "F5b" or holes:
        print(f"the predictions are not frozen F5b predictions: lane {pred.get('lane')}, holes {holes}")
        return 1
    root = Path(a.keep) if a.keep else Path(tempfile.mkdtemp(prefix="rung5bdry-"))
    root.mkdir(parents=True, exist_ok=True)
    stock = T.stock_script_source()
    roots: list = []                       # hermetic: the analysis reads the snapshot and stock, never the mod folders
    man = json.loads(M.MANIFEST.read_text(encoding="utf-8"))
    man5 = json.loads(M.F5_MANIFEST.read_text(encoding="utf-8"))
    bad, n_cases, seen = 0, 0, Counter()
    only = re.compile(a.only) if a.only else None

    def run_case(key: str) -> bool:
        return only is None or bool(only.search(key))

    def tally(key: str, ok: bool, line: str) -> None:
        nonlocal bad, n_cases
        seen[key] += 1
        n_cases += 1
        bad += not ok
        print(line, flush=True)

    # -- the bytes -----------------------------------------------------------------------------------------------
    print("== THE BYTES")
    hdir = Path(a.build) if a.build else root / "hubs"
    if not a.build:
        M.build_hubs(hdir, pred)
    ok_h, d_h, hub_bytes = built_bytes(hdir, {pred["hubs"][s]["id"]: pred["hubs"][s]["eb_sha256"] for s in FORKS})
    hub_eb = {s: hub_bytes.get(pred["hubs"][s]["id"]) for s in FORKS}
    tally("bytes", ok_h, f"  {'as registered' if ok_h else '!! BROKEN'}  the hubs {hdir}: {d_h}")
    s5 = Path(a.session5)
    want5 = {int(f): sha for f, sha in man5["chains"]["F5"]["eb_sha256"].items()}
    snap = {}
    for fid, sha in sorted(want5.items()):
        p = s5 / "scripts" / f"{fid}.eb"
        snap[fid] = p.read_bytes() if p.is_file() else b""
    bad_m = [f for f, sha in want5.items() if hashlib.sha256(snap[f]).hexdigest() != sha]
    tally("bytes", not bad_m, f"  {'as registered' if not bad_m else '!! BROKEN'}  session 5's member snapshot: "
                              f"{len(want5) - len(bad_m)}/{len(want5)} each rung5_forks.json's sha" +
          (f" -- differ {bad_m}" if bad_m else ""))
    mdir = Path(a.members) if a.members else root / "members"
    if not a.members:
        for fid, toml in sorted(man["chains"]["F5"]["tomls"].items()):
            RD5.kit(["build", toml, "--out", mdir / str(fid)], log=root / f"member-{fid}.log")
    ok_mb, d_mb, built_m = built_bytes(mdir, want5)
    same = all(built_m.get(f) == snap[f] for f in want5)
    tally("bytes", ok_mb and same, f"  {'as registered' if ok_mb and same else '!! BROKEN'}  the members built from "
                                   f"rung5b_forks.json's tomls: {d_mb}; byte-equal to the snapshot: {same}")
    if not (ok_h and not bad_m and ok_mb and same):
        print("\nthe bytes are not the frozen ones: nothing below would test what the session deploys")
        return 1
    for s in FORKS:
        snap[pred["hubs"][s]["id"]] = hub_eb[s]

    # -- the offline pre-flight (its static lines are the base session's recorded pre-flight) --------------------
    print("\n== THE OFFLINE PRE-FLIGHT")
    merged = merged_root(root / "merged", {**{f: mdir / str(f) for f in want5},
                                           **{pred["hubs"][s]["id"]: hdir / str(pred["hubs"][s]["id"]) for s in FORKS}})
    ran_m = T.mod_script_source([merged], fallback=stock)
    sides = H5.tours5(pred, ran=ran_m, stock=stock)
    # hermetic: a Memoria.ini holding the install's frozen switches (P-INI), never the shared live file
    ini_ok = root / "Memoria.ini"
    ini_text = ("[Hacks]\nEnabled = 1\nAllCharactersAvailable = 1\n[SaveFile]\nDisableAutoSave = 0\n"
                "AutoSaveOnlyAtMoogle = 0\n[Netsync]\nEnabled = 0\nRole = host\n")
    ini_ok.write_text(ini_text, encoding="utf-8")
    static = M.preflight5b(pred, [merged], stock, sides, ran=T.mod_script_source([merged]), pins=False, ini=ini_ok)
    ok_n, d_n, _st = M.p_pins()
    static.append((ok_n, "P-PINS: the resolver's seven F5b regression pins ran and PASSED", d_n))
    frozen_order = ["P-MANIFEST", "P-DEPLOY", "P-HUB", "P-HUB", "P-PARTYOPS", "P-ENTRY", "P-PURE", "P-FLOOR", "P-EXITS",
                    "P-STOCK", "P-INI", "P-PINS"]
    names = [M.check_id(w) for _ok, w, _d in static]
    pre_cases = []

    def pf(key, check, st, detail, need=()):
        pre_cases.append((key, check, st, detail, need))

    fails = [f"{M.check_id(w)}: {d[:160]}" for ok, w, d in static if not ok]
    pf("pf-static", "P-DEPLOY", "PASS" if not fails and names == frozen_order else "FAIL",
       f"{names}" + (f" -- {fails}" if fails else ""))
    pf("pf-pins", "P-PINS", WORD[ok_n], d_n, ["7/7 PASSED"])
    off = M.offline_check5b(pred, hdir, stock, pins=False)
    pf("pf-built-hubs", "P-HUB", "PASS" if all(ok for ok, _w, _d in off) else "FAIL",
       " || ".join(f"{M.check_id(w)} {WORD[ok]}" for ok, w, _d in off))
    empty = root / "no-census"
    empty.mkdir(exist_ok=True)
    env = {**os.environ, "FF9_STORY_CENSUS": str(empty), "FF9_F5_DIR": str(empty)}
    ok_x, d_x, _st = M.p_pins(env=env)
    pf("pf-pins-skip", "P-PINS", WORD[ok_x], d_x, ["test_real_f5_row_is_unchanged", "test_real_dali_post_wake_row"])
    ok_c, d_c = M.hub_check(M.hub_view(pred, "F5B"), hub_eb["CTL"], texts=False)
    ok_o, d_o = M.partyops_check(M.hub_view(pred, "F5B"), hub_eb["CTL"])
    pf("pf-ctl-as-f5b", "P-PARTYOPS", WORD[ok_o], f"{d_o} || P-HUB {WORD[ok_c]}: {d_c}",
       ["not the frozen [['remove', 2, 66]", "P-HUB FAIL"])
    man_bad = root / "manifest-f5-hub.json"
    man_bad.write_text(json.dumps({**man, "hubs": {**man["hubs"], "F5B": {**man5["hub"]}}}), encoding="utf-8")
    ok_mm, d_mm = M.manifest_check(pred, man_bad)
    pf("pf-f5-hub-manifest", "P-MANIFEST", WORD[ok_mm], d_mm, ["F5's hub 31100 is listed"])

    def hub_variant(name: str, old: str, new: str) -> bytes | None:
        """The F5B hub rebuilt from a copy of its journeys.toml with one line changed (gen-hub, then build)."""
        d = root / name
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        src = Path(pred["hubs"]["F5B"]["journeys"]).parent
        shutil.copy2(src / "camera_hub.bgx", d / "camera_hub.bgx")
        jt = (src / "journeys.toml").read_text(encoding="utf-8")
        assert jt.count(old) == 1, f"{old!r} is not in the frozen row once"
        (d / "journeys.toml").write_text(jt.replace(old, new), encoding="utf-8")
        RD5.kit(["gen-hub", d / "journeys.toml"], log=d / "gen-hub.log")
        RD5.kit(["build", d / "hub.field.toml", "--out", d / "build" / str(pred["hubs"]["F5B"]["id"])],
                log=d / "build.log")
        return H5.built_eb(d / "build", pred["hubs"]["F5B"]["id"])

    e2 = hub_variant("hub-entrance-2", "entrance = 6\n", "entrance = 2\n")
    ok_e, d_e = M.entry_check(pred, stock, {"F5B": e2})
    pf("pf-entrance-2", "P-ENTRY", WORD[ok_e], d_e, ["T5B_HUB: its entrance stores [(95, 2)], want one := 6"])
    h2610 = hub_variant("hub-2610", "set_scenario = 2600\n", "set_scenario = 2610\n")
    ok_s, d_s = M.hub_check(M.hub_view(pred, "F5B"), h2610, texts=False)
    pf("pf-hub-2610", "P-HUB", WORD[ok_s], d_s, ["2610"])
    from ff9mapkit.content.verbatim import remap_fields
    cmap = H5.chain_map(pred)
    unremapped = remap_fields(stock(350).data, {d: f for d, f in cmap.items() if d != 450})
    ok_u, d_u = H5.pure_check(pred, lambda f: unremapped if f == cmap[350] else snap.get(f), stock)
    pf("pf-pure-450", "P-PURE", WORD[ok_u], d_u, [f"{cmap[350]}: not remap(stock 350)",
                                                  f"{cmap[350]}: Field() targets outside the members [450"])
    seeded = root / "seeded"
    if seeded.exists():
        shutil.rmtree(seeded)
    chain_dir = Path(man["chains"]["F5"]["dir"])
    shutil.copytree(chain_dir, seeded / "chain")
    RD5.kit(["story-seed", "--chain", seeded / "chain", "--beat", pred["beat"], "--census",
             Path(man5["dir"]) / "research" / "dominance_census.json"], log=seeded / "story-seed.log")
    for fid, toml in sorted(man["chains"]["F5"]["tomls"].items()):
        RD5.kit(["build", seeded / "chain" / Path(toml).relative_to(chain_dir), "--out", seeded / "build" / str(fid)],
                log=seeded / f"build-{fid}.log")
    ok_d, d_d = H5.pure_check(pred, lambda f: H5.built_eb(seeded / "build", f), stock)
    pf("pf-pure-seeded", "P-PURE", WORD[ok_d], d_d, ["not remap(stock"])
    # P-INI: the shared Memoria.ini with the removes inert and the autosave off
    ini_bad = root / "Memoria-bad.ini"
    ini_bad.write_text(ini_text.replace("AllCharactersAvailable = 1", "AllCharactersAvailable = 2")
                       .replace("DisableAutoSave = 0", "DisableAutoSave = 1"), encoding="utf-8")
    ok_i, d_i, _v = M.ini_check(ini_bad)
    pf("pf-ini", "P-INI", WORD[ok_i], d_i, ["[Hacks] AllCharactersAvailable 2", "[SaveFile] DisableAutoSave 1"])
    # P-ENTRY's order clause: the entrance store swapped with an 8-byte stamp before it (the UInt16[208] one)
    H_f = pred["hubs"]["F5B"]
    s0 = H_f["stamp"][0]
    fn = T.ScriptIndex(hub_eb["F5B"], field_id=H_f["id"]).function(s0["sid"], s0["tag"])
    st_of = {s["target"]: s["off"] for s in H_f["stamp"]}
    a_, b_ = fn[2] + st_of["Global.UInt16[208]"], fn[2] + st_of["Global.Int16[2]"]
    swap = bytearray(hub_eb["F5B"])
    assert swap[a_] == swap[b_] == 0x05 and swap[a_ + 7] == swap[b_ + 7] == 0x7F, "the two 8-byte stores moved"
    swap[a_:a_ + 8], swap[b_:b_ + 8] = hub_eb["F5B"][b_:b_ + 8], hub_eb["F5B"][a_:a_ + 8]
    ok_eo, d_eo = M.entry_check(pred, stock, {"F5B": bytes(swap)})
    pf("pf-entry-order", "P-ENTRY", WORD[ok_eo], d_eo,
       [f"T5B_HUB: Int16[2] := 6 at +{st_of['Global.UInt16[208]']} is not after every stamp and before Field()"])
    # P-HUB's text clauses: the frozen bytes, with the menu option and a row data line edited in the sources
    txt = root / "hub-texts"
    if txt.exists():
        shutil.rmtree(txt)
    txt.mkdir(parents=True)
    src_toml, src_jt = Path(H_f["toml"]), Path(H_f["journeys"])
    opt = H_f["options"][0]
    toml_t = src_toml.read_text(encoding="utf-8")
    assert toml_t.count(f'"{opt}"') == 1, "the frozen option text is not in the hub toml once"
    (txt / "hub.field.toml").write_text(toml_t.replace(f'"{opt}"', f'"{opt}!"'), encoding="utf-8")
    jt_t = src_jt.read_text(encoding="utf-8")
    words_line = next(ln for ln in H_f["row_text"] if ln.startswith("set_words"))
    assert jt_t.count(words_line) == 1, "the frozen set_words line is not in journeys.toml once"
    (txt / "journeys.toml").write_text(jt_t.replace(words_line, words_line.replace("value = 1 }", "value = 3 }")),
                                       encoding="utf-8")
    view_t = M.hub_view(pred, "F5B")
    view_t["hub"] = dict(view_t["hub"], toml=str(txt / "hub.field.toml"), journeys=str(txt / "journeys.toml"))
    ok_t, d_t = M.hub_check(view_t, hub_eb["F5B"], texts=True)
    pf("pf-hub-texts", "P-HUB", WORD[ok_t], d_t, [f"options ['{opt}!'", "data lines ["])
    # P-DEPLOY's per-hub clause: a ForkDonorPatch row names the F5B hub
    forked = root / "merged-hub-fork"
    if forked.exists():
        shutil.rmtree(forked)
    shutil.copytree(merged, forked)
    with (forked / "ForkDonorPatch.txt").open("a", encoding="utf-8") as fh:
        fh.write(f"{H_f['id']} 950\n")
    static_f = M.preflight5b(pred, [forked], stock, H5.tours5(pred, ran=T.mod_script_source([forked], fallback=stock),
                                                               stock=stock),
                             ran=T.mod_script_source([forked]), pins=False, ini=ini_ok)
    dep = next((ok, d) for ok, w, d in static_f if M.check_id(w) == "P-DEPLOY")
    pf("pf-deploy-hub-fork", "P-DEPLOY", WORD[dep[0]], dep[1], [f"ForkDonorPatch rows [('merged-hub-fork', 950)]"])
    for key, check, st, detail, need in pre_cases:
        want = REGISTERED[key][1]
        probs = ([] if st == want else [st]) + [f"the detail does not say {s!r}" for s in need if s not in detail]
        tally(key, not probs, f"  {'as registered' if not probs else '!! WRONG'}  {check:<13} {want:<4}  "
                              f"{REGISTERED[key][2]}" + (f" -- !! {'; '.join(probs)}" if probs else "")
              + f" || {detail[:200]}")

    # -- the BASE ---------------------------------------------------------------------------------------------------
    world = World(pred, pred_path, hub_eb, snap, s5, static)
    W = world

    def case(name: str, plan_: list, *, snap_=None, sha=None, **session) -> tuple:
        """One constructed session, analysed: ``({check: (word, detail)}, reports, judged runs)``."""
        d = root / name
        write_session(d, plan_, snap=snap_ or snap, pred_path=pred_path, sha=sha, session=W.session(**session))
        checks, reports = M.analyse5b(d, stock=stock, roots=roots)
        sess = json.loads((d / M.SESSION_FILE).read_text(encoding="utf-8"))
        runs = M.read_session5b(d, pred, stock=stock, roots=roots, session=sess)
        got = {}
        for ok, what, detail in checks:
            got.setdefault(M.check_id(what), []).append((WORD[ok], detail))
        flat = {c: (("FAIL" if any(w_ == "FAIL" for w_, _d in v) else "VOID" if any(w_ == "VOID" for w_, _d in v)
                     else "PASS"), " | ".join(d_ for _w, d_ in v)) for c, v in got.items()}
        return flat, reports, runs

    got, reports, base_runs = case("base", W.plan())
    print("\n== BASE (S = session 5's S#1/S#3/S#5 as S#1/S#4/S#7; F5B and CTL constructed from each round's S on the "
          "built hubs' real bytes, re-seated)")
    base_ok = (all(st == "PASS" for st, _d in got.values())
               and got["VERDICT"][1].startswith(VERDICT_LINES["base"][0]))
    for k, (st, detail) in got.items():
        print(f"  {st}  {k:<14} {detail[:260]}")
    by = {r["i"]: r for r in base_runs}
    f5b = {i: r for i, r in by.items() if r["side"] == "F5B"}
    chains = R.chain_members(pred)
    rw5 = [H5.replay_why5(r, by, pred, chains) for r in f5b.values()]
    rw5b = [M.replay_why5b(r, by, pred, chains, *pred["replay"]["F5B"]) for r in f5b.values()]
    rwok = all(rw5) and not any(rw5b)
    print(f"  the base F5B logs pass replay_why5b and FAIL H5.replay_why5 (the frozen whole-walk rule): {rwok} "
          f"({rw5[0][:1]})")
    stamps_ok = all([(o["old"], o["new"]) for o in W.base[s][p] if o["fld"] == pred["hubs"][s]["id"] and o["sid"] == 2]
                    == [(x["old"], x["new"]) for x in pred["hubs"][s]["stamp"]] for s in FORKS for p in S_OF)
    print(f"  the re-seated stamp rows read the frozen old/new values: {stamps_ok}")
    base_ok = base_ok and rwok and stamps_ok
    if a.keep:
        for name, text in reports.items():
            (root / "base" / name).write_text(text, encoding="utf-8")

    # -- the numbers -------------------------------------------------------------------------------------------------
    print("\n== THE FROZEN NUMBERS, RE-DERIVED")
    nums = derive(W, base_runs, stock)
    for name, frozen, derived, ok in check_numbers(pred, nums):
        n_cases += 1
        bad += not ok
        shown = derived if len(str(derived)) < 180 else f"{str(derived)[:170]}..."
        print(f"  {'as frozen' if ok else '!! DIFFERS'}  {name}: {shown}" + ("" if ok else f" -- frozen {frozen}"))
    print(f"  (class (iii) UInt16[251]: {nums['class_iii_251']}; the hand-back cut: {nums['hand_cut']})")

    # -- rows the mutants are made of ---------------------------------------------------------------------------------
    members, m_of = W.members, (lambda donor: W.cmap[donor])
    hid = {s: pred["hubs"][s]["id"] for s in FORKS}
    in_members = lambda f: f["fld"] in members                                 # noqa: E731
    walks = W.walks
    sl = {p: walks[p][pred["replay"]["F5B"][0]:] for p in S_OF}
    p14 = f"replay@14({D.step_name(sl[1][13])})"
    f14 = ("FORK-STOP", p14)

    def at_step(p: int, n: int, rows=None) -> int:
        return fork_step_at(W.base["F5B"][p] if rows is None else rows, pred, walks[p], n)

    def f5b(i: int, p: int, rows=None, log=None, **rec) -> dict:
        return W.fork_run("F5B", i, p, rows, log, **rec)

    def ctl(i: int, p: int, rows=None, log=None, **rec) -> dict:
        return W.fork_run("CTL", i, p, rows, log, **rec)

    def stop14(i: int, p: int) -> dict:
        """F5B on S#p whose replay DIVERGED at slice step 14 -- it entered member(355) where S#p entered 450."""
        return f5b(i, p, RD5.cut(W.base["F5B"][p], at_step(p, 14)), replay_stop(pred, walks[p], 14, entered=355),
                   phase="replay")

    def landing_lock(i: int, p: int, n_rows: int, side: str = "F5B") -> dict:
        """``side`` on S#p whose landing soft-locked: the leg returned in 31101, member(351) wrote ``n_rows`` rows,
        then control never came (enter_past raised 'landing: ...'): FORK-STOP landing@351."""
        rows = W.base[side][p]
        j = next(k for k, o in enumerate(rows) if o["k"] in ("w", "r") and o["fld"] == pred["entry"]["member"])
        err = (f"landing: control never returned within 60s in 31101 (timed out after 60s waiting for control in "
               f"place 351 at SC 2600 (the landing))")
        land = dict(LANDING, ok=False, control=False, error=err[9:], t=60.0)
        log = {"stop": f"STOPPED: HarnessError: {err}", "choices": [], "log": [dict(HUB_REC), land]}
        return W.fork_run(side, i, p, RD5.cut(rows, j + n_rows), log, phase="landing",
                          at={"field": m_of(351), "place": 351, "sc": pred["beat"]}, landing=land)

    def hub_late(i: int, p: int, stop: str, extra: int) -> dict:
        """The stamps landed and the hub leg then RAISED ``stop`` (phase hub), the trace cut ``extra`` rows into
        31101 (0: before any row there)."""
        rows = W.base["F5B"][p]
        j = next(k for k, o in enumerate(rows) if o["k"] in ("w", "r") and o["fld"] == pred["entry"]["member"])
        log = {"stop": stop, "choices": [], "log": [dict(HUB_REC, error=stop.split("STOPPED: ", 1)[1], t=179.9)]}
        return f5b(i, p, RD5.cut(rows, j + extra), log, phase="hub",
                   at={"field": hid["F5B"], "place": hid["F5B"], "sc": pred["beat"]}, landing=None)

    def hub_raised(i: int, p: int, side: str = "F5B") -> dict:
        """The hub leg raised before the pick (no dialogue): New Game's residue and the hub's PROLOGUE only."""
        rows = W.rows(side, p, hub=[h for h in W.hub_rows(side, p) if h["sid"] == 0])
        log = {"stop": "STOPPED: HarnessError: hub leg: no dialogue after 3 tries at [314, 127] (Stiltzkin at "
                       "[480, 127], r 152, talk_r 338)", "choices": [], "log": []}
        cut = next(k for k, o in enumerate(rows) if in_members(o))
        return W.fork_run(side, i, p, RD5.cut(rows, cut), log, phase="hub",
                          at={"field": hid[side], "place": hid[side], "sc": pred["start_sc"]}, landing=None)

    def hub_died(i: int, p: int) -> dict:
        """The game died in the hub AFTER the stamps (the pick's warp never landed): no ``off``."""
        rows = W.base["F5B"][p]
        keep = [o for o in rows[:next(k for k, o in enumerate(rows) if in_members(o))] if o["k"] != "c"]
        log = {"stop": "STOPPED: HarnessError: press confirm 4 not acknowledged within 60s", "choices": [], "log": []}
        return f5b(i, p, keep, log, phase="hub", at={}, landing=None)

    def wrong_entry(i: int, p: int) -> dict:
        """The stamps landed, then the pick's Field() led to member(352) (31104), never 31101: the hub leg's wait
        for 31101 timed out there. Its rows: New Game's, the hub's, then 352's post-wake arrival rows in 31104."""
        e = fork_entries(W.s_rows[p], pred, "F5B", W.sites["F5B"])
        at = RD5.find(e, in_members)
        j = RD5.find(e, lambda f: f["fld"] == m_of(352), after=at)
        visit = []
        for k_, _s, f in e[j:]:
            if f["k"] == "c" or f["fld"] != m_of(352):
                break
            visit.append(dict(f))
        e = e[:at] + [["new", None, r] for r in visit] + [["s", s, None] for k_, s, f in e[at:]
                                                          if k_ == "both" and s["k"] in ("w", "r")]
        rows = RD5.reseat(e)
        log = {"stop": "STOPPED: HarnessError: timed out after 60s waiting for the pick to land in 31101 over 812 "
                       "live samples", "choices": [], "log": [dict(HUB_REC)]}
        return f5b(i, p, RD5.cut(rows, len(rows)), log, phase="hub",
                   at={"field": m_of(352), "place": 352, "sc": pred["beat"]}, landing=None)

    def entrance4(i: int, p: int) -> dict:
        """The pick entered member(352) at entrance 4 (a wrong entry id and entrance): 352's reload runs the night's
        wake again -- the partner's rows from its entrance-4 reload through the wake and the exit's step 1,
        relabelled into 31104, between the hub and the landing; the hub's entrance stamp := 4."""
        s = W.s_rows[p]
        wake = next(k for k, o in enumerate(s) if RD5.is_wake(o, pred, {}))
        k4 = max(k for k, o in enumerate(s[:wake]) if o["k"] == "w" and o["fld"] == 352
                 and RD5.target(o) == "Global.Int16[2]" and o["new"] == 4)
        land = next(k for k, o in enumerate(s) if k > wake and o["k"] in ("w", "r") and o["fld"] == 351)
        seg = [dict(o, fld=m_of(352)) for o in s[k4 + 1:land] if o["k"] in ("w", "r")]
        hub = W.hub_rows("F5B", p, lambda h: [dict(o, new=4) if RD5.target(o) == "Global.Int16[2]" and o["sid"] == 2
                                              else o for o in h])

        def x(e):
            at = RD5.find(e, in_members)
            return RD5.insert(e, at, seg)

        return f5b(i, p, W.rows("F5B", p, x, hub=hub))

    def extra_key(e: list) -> list:
        """One value no donor writes: member(350)'s first Int16 store after the landing written again, +7."""
        at = RD5.find(e, lambda f: f["fld"] == pred["entry"]["member"])
        j = RD5.find(e, lambda f: f["k"] == "w" and f["fld"] == m_of(350) and f["w"] == "Int16", after=at)
        f = e[j][2]
        return RD5.insert(e, j + 1, [dict(f, old=0, new=f["new"] + 7, same=0)])

    # a stock key every S window writes once, at a site with one row and no count, that no pattern or registered set
    # reads: the key a mutant drops from F5B
    pats = [*pred["coverage"]["ran"], pred["coverage"]["flip"], pred["wake"], pred["checks"]["R5-PING"]["pattern"],
            pred["checks"]["R5-ADVANCE"]["pattern"], *pred["checks"]["R5-LATCH"]["patterns"]]
    reg = {M.ktuple(k) for k in pred["arrival"]["keys"] + pred["step1_keys"] + pred["supp"]["proven"]
           + pred["supp"]["blind"] + pred["echo"]}
    s_win = {i: by[i]["window"] for i in S_OF}

    def one_row_site(i: int, o) -> bool:
        st = [x for x in W.s_rows[i] if x["k"] in ("w", "c") and RD.site(x)[1:] == o.row.site[1:]
              and x["fld"] == o.row.fld]
        return len(st) == 1 and st[0]["k"] == "w"

    common = set.intersection(*(set(d.keys) for d in s_win.values()))
    land1 = M.cuts(by[1], pred)["hand"].line
    drop_key = next(k for k, o in sorted(s_win[1].keys.items(), key=lambda ko: ko[1].at)
                    if k in common and o.at > land1 + 30 and o.row.src == "eb" and not o.counted
                    and 350 <= o.row.fld <= 358 and k.target != "Global.UInt16[0]" and not H5._is_timing(k, pred)
                    and M.ktuple(k) not in reg and not any(R._matches(p_, k) for p_ in pats)
                    and all(one_row_site(i, s_win[i].keys[k]) for i in S_OF))
    drop_site = s_win[1].keys[drop_key].row.site

    def at_drop_site(f: dict) -> bool:
        return f["k"] in ("w", "c") and (members.get(f["fld"], f["fld"]), *RD.site(f)[1:]) == drop_site

    # member(351)'s e4 Main_Init store Global.SByte[296] := 65472, made a WORD store: the clobber mutant's site
    clob = (m_of(351), 4, 0, 22)
    snap_clob = dict(snap)
    e4 = T.ScriptIndex(snap[clob[0]]).eb.entries[clob[1]]
    at_tok = e4.abs_start + clob[3] + 1
    assert snap[clob[0]][at_tok] == 0xF0, "member(351) e4 +12: the SByte[296] token moved"
    snap_clob[clob[0]] = snap[clob[0]][:at_tok] + bytes([0xFC]) + snap[clob[0]][at_tok + 1:]

    def clobber(e: list) -> list:
        out = []
        for k_, s, f in e:
            if k_ != "s" and f["k"] in ("w", "c") and (f["fld"], f["sid"], f["tag"], f["ip"]) == clob \
                    and RD5.target(f) == "Global.SByte[296]":
                if f["k"] == "w":
                    out += ([["s", s, None]] if k_ == "both" else []) + [["new", None, dict(f, w="UInt16", old=0,
                                                                                          new=65472, same=0)]]
                else:
                    out.append([k_, s, dict(f, w="UInt16", last=65472)])
                continue
            out.append([k_, s, f])
        return out

    adv = pred["checks"]["R5-ADVANCE"]["pattern"]
    is_adv = lambda f: (f["k"] == "w" and f["fld"] == m_of(adv["donor"])  # noqa: E731
                        and (f["sid"], f["tag"], RD5.target(f)) == (adv["sid"], adv["tag"], adv["target"])
                        and f["new"] in adv["value"])
    is_2085 = lambda f: f["k"] in ("w", "c") and f["fld"] == m_of(450) and RD5.target(f) == "Global.Bit[2085]"  # noqa
    echo2086 = pred["echo"][1]
    is_2086 = lambda f: (f["k"] in ("w", "c") and f["fld"] == m_of(echo2086["donor"])  # noqa: E731
                         and (f["sid"], f["tag"], f["ip"]) == (echo2086["sid"], echo2086["tag"], echo2086["ip"]))

    def lone_member_row(rows: list) -> int:
        """A member store after the landing burst whose site has that one row and no count."""
        at = next(k for k, o in enumerate(rows) if o["k"] == "w" and o["fld"] == pred["entry"]["member"])
        sites = Counter(RD.site(o) for o in rows if o["k"] in ("w", "c"))
        return next(k for k, o in enumerate(rows) if k > at + 20 and o["k"] == "w" and in_members(o)
                    and sites[RD.site(o)] == 1)

    lone = lone_member_row(W.base["F5B"][1])
    frozen21 = set(pred["stockstate"]["changed_from_new_game"])
    stamp_b = {int(b) for b in pred["stockstate"]["stamp_bytes"]}

    def extra_byte(e: list) -> list:
        rows = [f for _k, _s, f in e]
        w = next(k for k, o in enumerate(rows) if RD5.is_wake(o, pred, {}))
        touched = Counter(b >> 3 for o in rows[:w] if o["k"] in ("w", "r") for b in RD5.span_bits(o))
        j = next(k for k, o in enumerate(rows[:w]) if o["k"] == "w" and o["w"] == "Byte" and o["same"]
                 and o["byte"] not in frozen21 | stamp_b | {299} and touched[o["byte"]] == 8)
        e[j][2] = dict(e[j][2], new=(e[j][2]["new"] + 5) & 0xFF)
        return e

    s1_2078 = RD.drop_rows(W.s_rows[1], lambda k, o: o["k"] == "w" and o["fld"] == 352 and o["sid"] == 17
                           and o["tag"] == 1 and RD5.target(o) == "Global.Bit[2078]" and o["new"] == 1)
    s297 = lambda f: (f["k"] == "w" and members.get(f["fld"], f["fld"]) == 359  # noqa: E731
                      and (f["sid"], f["tag"]) == (0, 0) and RD5.target(f) == "Global.UInt16[297]")

    def hub_store(like: dict, sid: int, tag: int, ip: int, tgt: str, new: int) -> dict:
        w, byte, bit = RD5.parse_target(tgt)
        return dict(like, sid=sid, uid=sid, tag=tag, ip=ip, w=w, byte=byte, bit=bit, old=0, new=new, same=0)

    def last_stamp(h: list) -> dict:
        return [o for o in h if o["sid"] == 2][-1]

    def all_side(side: str, xform=None, **kw) -> dict:
        """``{i: run}`` for the three ``side`` runs, each world edited by ``xform``."""
        return W.every(side, lambda i, p: W.fork_run(side, i, p, W.rows(side, p, xform, **kw)))

    def hub_mut(fn, side: str = "F5B") -> list:
        """The frozen nine, every ``side`` run's hub rows edited by ``fn``."""
        return W.plan(W.every(side, lambda i, p: W.fork_run(side, i, p, W.rows(side, p, hub=W.hub_rows(side, p, fn)))))

    # the evidence rows of SUPP-PROVEN 351 +132 in S#1's window (rung5b_hub.supp_ok's own dominance test)
    k132 = next(k for k in pred["supp"]["proven"] if k["donor"] == 351)
    fl = M._flow(stock, k132["donor"], k132["sid"], k132["tag"])
    flow, ea, fa = fl
    kb = flow.block_at(fa + k132["off"])
    w1 = H5.wake_row(by[1]["raw"], pred, {})
    ev_lines = {x.line for x in by[1]["raw"] if x.k == "w" and x.line > w1.line and x.src == "eb"
                and (x.fld, x.sid, x.tag) == (k132["donor"], k132["sid"], k132["tag"])
                and flow.block_at(ea + x.ip) is not None and (flow._dom[flow.block_at(ea + x.ip)] >> kb) & 1
                and (flow.block_at(ea + x.ip) != kb or ea + x.ip > fa + k132["off"])}
    assert ev_lines, "no evidence rows for 351 +132 in S#1"
    s1_no_ev = RD5.reseat([["s", o, None] if n in ev_lines and o["k"] == "w" else ["both", o, dict(o)]
                           for n, o in enumerate(W.s_rows[1], 1)])
    s1_no_ev = [o for o in s1_no_ev if o["k"] != "c" or RD.site(o) in {RD.site(x) for x in s1_no_ev if x["k"] == "w"}]

    blind1387 = next(k for k in pred["supp"]["blind"] if k["ip"] == 1387)
    is_1387 = lambda f: (f["k"] == "w" and f["fld"] == m_of(351) and (f["sid"], f["tag"], f["ip"])  # noqa: E731
                         == (blind1387["sid"], blind1387["tag"], blind1387["ip"]))
    fo791 = pred["control"]["fork_only"][0]
    is_801 = lambda f: (f["k"] == "w" and f["fld"] == m_of(351) and (f["sid"], f["tag"], f["ip"])  # noqa: E731
                        == (fo791["sid"], fo791["tag"], fo791["ip"]))
    ab = pred["control"]["step1"]["absent"]

    def add_791(e: list) -> list:
        """F5B's landing burst also runs 351 e0 +791 SByte[238] := 0 (an ATE(0) store beside ATE(1))."""
        at = RD5.find(e, lambda f: f["k"] == "w" and f["fld"] == m_of(351))
        j = RD5.find(e, lambda f: f["k"] == "w" and f["fld"] == m_of(351) and f["ip"] > fo791["ip"], after=at)
        return RD5.insert(e, j, [_w(e[j][2], m_of(351), 351, fo791["sid"], fo791["tag"], fo791["ip"],
                                    fo791["target"], fo791["value"])])

    def ctl_ip105(e: list) -> list:
        """CTL's step-1 crossing runs the 2078 consumer (e16 t2 ip105) as though 2078 were set."""
        j = RD5.find(e, lambda f: f["k"] == "w" and f["fld"] == m_of(351) and (f["sid"], f["tag"]) == (ab["sid"],
                                                                                                      ab["tag"]))
        return RD5.insert(e, j, [dict(_w(e[j][2], m_of(351), 351, ab["sid"], ab["tag"], ab["ip"], "Global.Bit[2078]",
                                         0))])

    def ctl_no_recompute(i: int, p: int) -> dict:
        """CTL whose 351 arrival runs stock's ATE(1) burst (+734/+742/+770) though its latches are unset -- the rooms
        NOT recomputing the ATE state from the latches as read: CTL's hub rows, then F5B's arrival (no +791/+799,
        251 := 6); the lobby exit's 2078 consumer still does not fire (2078 unset); cut after 350's arrival."""
        f = fork_entries(W.s_rows[p], pred, "F5B", W.sites["CTL"], hub=W.hub_rows("CTL", p))
        f = [["s", s, None] if k_ == "both" and f_["k"] == "w" and f_["fld"] == m_of(351)
             and (f_["sid"], f_["tag"], f_["ip"]) == (ab["sid"], ab["tag"], ab["ip"]) else [k_, s, f_]
             for k_, s, f_ in f]
        rows = RD5.reseat(f)
        m350 = m_of(350)
        j = next(k for k, o in enumerate(rows) if o["k"] in ("w", "r") and o["fld"] == m350)
        k = next((k for k in range(j + 1, len(rows)) if rows[k]["k"] in ("w", "r")
                  and (rows[k]["fld"] != m350 or (rows[k]["k"] == "w" and rows[k]["tag"] != 0))), len(rows))
        return ctl(i, p, RD5.cut(rows, k))

    footprint_site = next(s for s in H5.global_stores(stock(350).data, field_id=350)
                          if s["target"] == "Global.Byte[303]" and s["value"] == 0)

    def footprint(e: list) -> list:
        """A party-footprint store (350's own Byte[303] := 0 site) written in 350 after the landing."""
        at = RD5.find(e, lambda f: f["k"] == "w" and members.get(f["fld"], f["fld"]) == 350)
        f = e[at][2]
        w, byte, bit = RD5.parse_target(footprint_site["target"])
        return RD5.insert(e, at + 1, [dict(f, sid=footprint_site["sid"], uid=footprint_site["sid"],
                                           tag=footprint_site["tag"], ip=footprint_site["ip"], w=w, byte=byte, bit=bit,
                                           old=0, new=0, same=1)])

    def edit_log_step(log: dict, n: int, step: list) -> dict:
        """A stock log whose n-th entered crossing (1-based) entered ``step`` instead."""
        lg = json.loads(json.dumps(log))
        k = 0
        for x in lg["log"]:
            if x.get("k") == "cross" and D.entered(x) is not None:
                k += 1
                if k == n:
                    x.update({"from": step[0], "place": step[0], "exit": step[1], "to": step[2], "landed": step[2],
                              "changed_to": step[2], "entered": step[2]})
                    x.pop("to_place", None)
                    break
        return lg

    # -- the MUTANTS ----------------------------------------------------------------------------------------------
    fork_side_checks = ["R5B-LAND", "R5B-STATE", "R5B-ECHO", "R5B-ARRIVAL", "R5B-PARTY", "R5-MIRROR", "R5-PARTIAL",
                        "R5-PING", "R5-NOSEAM", "R5-ADVANCE", "R5-LATCH", "R5-PREEMPT"]
    mutants = []

    def mut(key, plan_, **kw):
        mutants.append(dict(key=key, plan=plan_, **kw))

    def lazy(key, fn, **kw):
        """A case whose plan is built only if it runs (``--only`` skips it, and the registry check then says so)."""
        if run_case(key):
            mut(key, fn(), **kw)

    lazy("reach-all-break", lambda: W.plan(W.every("F5B", stop14)),
         stops={2: f14, 5: f14, 8: f14}, halt=p14, void=fork_side_checks, verdict=("FAILED: R5-REACH",))
    lazy("reach-all-landing", lambda: W.plan(W.every("F5B", lambda i, p: landing_lock(i, p, 12))),
         stops={i: ("FORK-STOP", "landing@351") for i in (2, 5, 8)}, halt="landing@351")
    lazy("reach-rerun-halt", lambda: W.plan({2: stop14(2, 1)}, [stop14(10, 1)]), stops={2: f14, 10: f14}, halt=p14,
         also={"R5-RUNS": "VOID"}, no_faults=True)
    lazy("runs-after-halt", lambda: W.plan({2: stop14(2, 1)}, [stop14(10, 1), f5b(11, 1)]), need=["HALTED"])
    lazy("reach-one-stop", lambda: W.plan({2: stop14(2, 1)}, [f5b(10, 1)]), stops={2: f14, 10: None}, halt=None,
         need=[f"F5B#2 FORK-STOP @{p14}"], rest="PASS",
         verdict=("NOT PROVEN: walk (R5-REACH: VOID", "-- proven: state, latches, party"))
    lazy("reach-landing-norow", lambda: W.plan({2: landing_lock(2, 1, 0)}, [landing_lock(10, 1, 0)]),
         stops={2: ("FORK-STOP", "landing@351"), 10: ("FORK-STOP", "landing@351")}, halt="landing@351",
         need=["F5B#2 FORK-STOP @landing@351: STOPPED: HarnessError: landing: control never returned"],
         also={"R5-RUNS": "VOID"}, no_faults=True, undigested=[2, 10])
    budget = "STOPPED: HarnessError: hub leg: budget -- the leg's hub_s ran out"
    lazy("reach-budget-norow", lambda: W.plan({2: hub_late(2, 1, budget, 0)}, [f5b(10, 1)]),
         stops={2: ("DRIVE", None)}, need=["F5B#2 DRIVE: stop ", "STOPPED: HarnessError: hub leg: budget"],
         undigested=[2])
    lazy("reach-budget-rows", lambda: W.plan({2: hub_late(2, 1, budget, 20)}, [f5b(10, 1)]),
         stops={2: ("DRIVE", None)}, need=["F5B#2 DRIVE: stop ", "STOPPED: HarnessError: hub leg: budget"])
    wait_stop = ("STOPPED: HarnessError: timed out after 60s waiting for the pick to land in 31101 over 3412 live "
                 "samples (last state: State(field_id=31113))")
    lazy("reach-landing-wait", lambda: W.plan({2: hub_late(2, 1, wait_stop, 20)}, [f5b(10, 1)]),
         stops={2: ("DRIVE", None)}, need=["F5B#2 DRIVE: the hub leg raised though the trace has rows in 31101"])
    poll = ("STOPPED: HarnessError: steps ['wait 4'] were not acknowledged within 60s (the agent is alive; last "
            "state: None)")
    lazy("reach-poll-ack", lambda: W.plan({2: hub_late(2, 1, poll, 0)}, [f5b(10, 1)]),
         stops={2: ("UNCLASSED", None)},
         need=["F5B#2 UNCLASSED: the stamps landed and 31101 was never reached, but the stop is not the landing's"],
         undigested=[2])

    def prefix_truncated():
        rows = W.rows("F5B", 1, extra_key)
        lg = fork_log(pred, "F5B", walks[1], steps=14, moved_at=len(sl[1]) + 1,
                      stop=f"session budget spent (replay step 15 of {len(sl[1])}, crossings 14, 900s)")
        return W.plan({2: f5b(2, 1, RD5.cut(rows, fork_step_at(rows, pred, walks[1], 15)), lg, phase="replay")})

    lazy("prefix-truncated", prefix_truncated, stops={2: ("DRIVE", None)}, need=["F5B#2 (partner S#1, DRIVE)"])
    lazy("reach-door", lambda: W.plan({2: f5b(2, 1, RD5.cut(W.base["F5B"][1], at_step(1, 8)),
                                             replay_stop(pred, walks[1], 8, why="the gated door was never faced "
                                                                                "(2 times)"), phase="replay")},
                                      [f5b(10, 1)]), stops={2: ("DRIVE", None)})

    def soft_lock(i, p):
        log = fork_log(pred, "F5B", walks[p], steps=10, moved_at=len(sl[p]) + 1,
                       stop=f"STOPPED: HarnessError: control never returned within 900 live frames in field "
                            f"{m_of(350)}")
        return f5b(i, p, RD5.cut(W.base["F5B"][p], at_step(p, 11)), log, phase="replay",
                   at={"field": m_of(350), "place": 350, "sc": pred["beat"]})

    lazy("reach-soft-lock", lambda: W.plan({2: soft_lock(2, 1)}, [soft_lock(10, 1)]),
         stops={2: ("FORK-STOP", "scene@350@2600"), 10: ("FORK-STOP", "scene@350@2600")}, halt="scene@350@2600")
    lazy("reach-unclassed", lambda: W.plan({2: f5b(2, 1, RD5.cut(W.base["F5B"][1], at_step(1, 11)), fork_log(
        pred, "F5B", walks[1], steps=10, moved_at=len(sl[1]) + 1,
        stop="STOPPED: HarnessError: watch_cutscene timed out after 300s"), phase="replay",
        at={"field": m_of(350), "place": 350, "sc": pred["beat"]})}, [f5b(10, 1)]),
         stops={2: ("UNCLASSED", None)}, need=["F5B#2 UNCLASSED"])
    lazy("join-hub-raised", lambda: W.plan({2: hub_raised(2, 1)}, [f5b(10, 1)]), stops={2: ("DRIVE", None)},
         need=["notes []"], also={"R5-DONOR": "PASS", "R5-STAMP": "PASS"}, undigested=[2])
    lazy("prefix-all-hub-raised", lambda: W.plan(W.every("F5B", hub_raised)), need=["no such F5B run"],
         stops={i: ("DRIVE", None) for i in (2, 5, 8)},
         also={"R5-STAMP": "VOID", "R5-DONOR": "PASS", "R5-JOIN": "PASS"},
         also_need={"R5-STAMP": ["'F5B': 0"], "R5-DONOR": ["6 fork runs read"]}, undigested=[2, 5, 8])
    lazy("join-all-skipped", lambda: [W.skipped(i, s) for i, s in enumerate(W.order, 1)], need=["0 runs digested"],
         also={"R5-DONOR": "VOID", "R5-PREFIX": "VOID", "R5-STAMP": "VOID", "R5B-NOWAKE": "VOID"},
         also_need={"R5-DONOR": ["no fork run read"]})
    lazy("reach-hub-died", lambda: W.plan({2: hub_died(2, 1)}, [f5b(10, 1)]), stops={2: ("DRIVE", None)},
         need=["F5B#2 DRIVE: the trace never closed"], undigested=[2])
    lazy("stamp-wrong-entry", lambda: W.plan({2: wrong_entry(2, 1)}), stops={2: ("FORK-STOP", "hub")},
         need=["F5B#2: entry: the first row after the hub stands in 31104"])
    lazy("stamp-source-pre", lambda: W.plan(), stamp_source="pre", need=["list: the stamps are []"])
    lazy("stamp-297-dropped", lambda: hub_mut(lambda h: [o for o in h if RD5.target(o) != "Global.UInt16[297]"]),
         need=["list: the stamps are [(23, 'Global.UInt16[0]', 2540, 2600), (31, 'Global.Bit[2078]', 0, 1), "
               "(40, 'Global.Bit[2086]', 0, 1), (49, 'Global.UInt16[208]', 0, 0), (95, 'Global.Int16[2]', 0, 6)], "
               "not the frozen"])
    lazy("stamp-bit-write", lambda: hub_mut(lambda h: h + [hub_store(last_stamp(h), 2, 3, 180, "Global.Bit[2065]",
                                                                     1)]),
         need=["list: the stamps are [", "(None, 'Global.Bit[2065]', 0, 1)], not the frozen"])
    lazy("stamp-don-351", lambda: hub_mut(lambda h: [dict(o, don=351) for o in h]), need=["don 351"],
         also={"R5-DONOR": "FAIL"})
    lazy("stamp-ip-off", lambda: hub_mut(lambda h: [dict(o, ip=o["ip"] + 1) if RD5.target(o) == "Global.UInt16[0]"
                                                    else o for o in h]), need=["not an instruction boundary"])
    lazy("stamp-width", lambda: hub_mut(lambda h: h + [hub_store(last_stamp(h), 2, 3, 180, "Global.UInt16[296]",
                                                                 192)]),
         need=["width: Global.UInt16[296] = 192 changed byte 297", "list: the stamps are"])
    lazy("stockstate-297", lambda: W.plan({i: W.s_run(i, W.s_side(i, lambda e: RD5.edit(e, s297, new=3)))
                                           for i in S_OF}), need=["stamp bytes"])
    lazy("stockstate-extra-byte", lambda: W.plan({1: W.s_run(1, W.s_side(1, extra_byte))}),
         need=["changed from New Game gains"])
    lazy("stockstate-contradiction", lambda: W.plan({1: W.s_run(1, s1_2078)}),
         need=["S#1: 1 contradictions", "Global.Bit[2078]"],
         also={"R5B-LAND": "VOID", "R5B-STATE": "VOID"},
         also_need={"R5B-LAND": ["calibration contradictions"], "R5B-STATE": ["calibration contradictions"]})
    lazy("noseam-450-real", lambda: W.plan(W.every("F5B", lambda i, p: f5b(i, p, W.rows("F5B", p, lambda e: [
        [k_, s, dict(f, fld=450) if k_ != "s" and f["fld"] == m_of(450) else f] for k_, s, f in e])))),
         also={"R5-PING": "FAIL"},
         need=["rows outside the members in [450]", "450 never entered as member 31112"])
    lazy("partial-drop-one", lambda: W.plan({5: f5b(5, 4, W.rows("F5B", 4, lambda e: RD5.lose(e, at_drop_site)))}),
         need=["F5B#5/S#4"])
    lazy("mirror-drop-all", lambda: W.plan(all_side("F5B", lambda e: RD5.lose(e, at_drop_site))),
         need=["1 STOCK ONLY", f"left ['{drop_key.donor} e{drop_key.sid} t{drop_key.tag} {drop_key.off:+d}"])
    lazy("mirror-extra-all", lambda: W.plan(all_side("F5B", extra_key)),
         need=["9 FORK ONLY (8 SUPP-admitted", "not admitted ['350 e"])
    lazy("mirror-clobber", lambda: W.plan({**all_side("F5B", clobber), **all_side("CTL", clobber)}), snap=snap_clob,
         need=["1 clobbers"],
         also={"R5-LATCH": "FAIL"})
    lazy("advance-moved", lambda: W.plan(all_side("F5B", lambda e: RD5.edit(e, is_adv, fld=m_of(356), don=356))),
         need=[f"is w in {m_of(356)} (don 356)"])
    lazy("advance-never", lambda: W.plan({8: f5b(8, 7, RD5.cut(W.base["F5B"][7], next(
        k for k, o in enumerate(W.base["F5B"][7]) if is_adv(o))), fork_log(
        pred, "F5B", walks[7], moved_at=len(sl[7]) + 1, stop=f"passes exhausted (3) without the story moving on"))}),
         need=["F5B#8: never reached SC 2610"], stops={8: None})
    lazy("latch-2085", lambda: W.plan(all_side("F5B", lambda e: RD5.lose(e, is_2085))), need=["Bit[2085]"])
    lazy("join-ip-off", lambda: W.plan({2: f5b(2, 1, [dict(o, ip=o["ip"] + 1) if n == lone else o
                                                      for n, o in enumerate(W.base["F5B"][1])])}),
         need=["1 failures"])
    lazy("donor-999", lambda: W.plan({2: f5b(2, 1, [dict(o, don=999) if n == lone else o
                                                    for n, o in enumerate(W.base["F5B"][1])])}),
         need=["don 999 (want"])
    lazy("runs-order", lambda: W.plan({3: f5b(3, 1), 4: ctl(4, 1)}), need=["not the frozen order"])
    lazy("runs-partner", lambda: W.plan({5: f5b(5, 1)}), need=["F5B#5 partners S#1, not its round's S#4"])
    lazy("runs-twins", lambda: W.plan(extra=[f5b(10, 1)]), need=["S#1 is partnered by 2 covered F5B runs"])
    lazy("frozen-edited", lambda: W.plan(), sha="0" * 64)

    # new in F5b ----------------------------------------------------------------------------------------------------
    def whole_walk():
        lg = fork_log(pred, "F5B", walks[1])
        first = RD.replay_log(pred, walks[1][:1], moved_at=2)["log"][1]
        head = [x for x in lg["log"] if x.get("k") != "cross"]
        cross = [dict(first, step=1)] + [dict(x, step=x["step"] + 1) for x in lg["log"] if x.get("k") == "cross"]
        return W.plan({2: f5b(2, 1, None, dict(lg, log=head + cross))})

    lazy("replay-whole-walk", whole_walk, need=["F5B 2 covered"],
         run_why={2: "its replay of S#1's walk[1:] diverged at step 1: 352.0 -> 351, not 351.0 -> 350"},
         no_faults=True)
    bad2 = edit_log_step(W.s_logs[4], 2, [351, 1, 352])
    walk_bad2 = D.entered_walk(bad2["log"])

    def ctl_gate(rerun_on: int):
        return W.plan({4: W.s_run(4, log=bad2),
                       5: f5b(5, 4, walk=walk_bad2, log=fork_log(pred, "F5B", walk_bad2)),
                       6: dict(W.skipped(6, "CTL", M.walk_gate(pred, "CTL", walk_bad2)), rec={
                           "partner": 4, "walk": walk_bad2, "skipped": M.walk_gate(pred, "CTL", walk_bad2)}),
                       9: ctl(9, 7, RD5.cut(W.base["CTL"][7], 10), fork_log(
                           pred, "CTL", walks[7], steps=0, stop="STOPPED: HarnessError: control never returned "
                                                                "within 300s -- the game holds it"),
                           phase="replay")},
                      [ctl(10, rerun_on, walk=walks[rerun_on] if rerun_on != 4 else walk_bad2,
                           log=fork_log(pred, "CTL", walks[rerun_on] if rerun_on != 4 else walk_bad2))])

    lazy("ctl-gate-skip", lambda: ctl_gate(7), need=["CTL 2 covered"], plan_before={10: ("CTL", 7)},
         run_why={6: "skipped: partner step 2 is not 351.0 -> 350 (it is 351.1 -> 352)"}, no_faults=True)
    lazy("ctl-gate-rerun-wrong", lambda: ctl_gate(4),
         need=["CTL#10 re-ran CTL on S#4, where the plan named CTL on S#7",
               "CTL#10 was driven on S#4, whose walk fails its gate"])
    bad1 = edit_log_step(W.s_logs[4], 1, [352, 0, 355])
    walk_bad1 = D.entered_walk(bad1["log"])
    gate1 = M.walk_gate(pred, "F5B", walk_bad1)
    lazy("f5b-gate-skip", lambda: W.plan({4: W.s_run(4, log=bad1),
                                          5: {"side": "F5B", "rows": None, "log": None,
                                              "rec": {"partner": 4, "walk": walk_bad1, "skipped": gate1}},
                                          6: {"side": "CTL", "rows": None, "log": None,
                                              "rec": {"partner": 4, "walk": walk_bad1,
                                                      "skipped": M.walk_gate(pred, "CTL", walk_bad1)}}}),
         need=["F5B 2 covered"], plan_after=("S", None), no_faults=True,
         run_why={5: "partner's first step is not the wake room's exit 352.0 -> 351 (it is 352.0 -> 355)"})
    lazy("supp-proven-no-evidence", lambda: W.plan({1: W.s_run(1, s1_no_ev)}),
         need=["not admitted ['351 e0 t0 +132 Global.Int16[11]=-1']"])
    lazy("supp-blind-value", lambda: W.plan(all_side("F5B", lambda e: RD5.edit(e, is_1387, new=124))),
         need=["not admitted ['351 e0 t0 +1377 Global.Byte[8]=124']"])

    def stock_site_value(key: dict, value: int) -> list:
        """The frozen nine with STOCK's own value at a SUPP site moved: every S run's rows at the key's site -- its
        pre-wake same:1 emission and its count row -- carry ``value`` (re-seated); the F5B runs are the base's,
        built on the unedited partners, so they write the frozen value."""
        site = (key["donor"], key["sid"], key["tag"], key["ip"])

        def x(e):
            return [[k_, s, (dict(f, new=value) if f["k"] == "w" else dict(f, last=value))
                     if k_ != "s" and f["k"] in ("w", "c") and (f["fld"], f["sid"], f["tag"], f["ip"]) == site
                     and RD5.target(f) == key["target"] else f] for k_, s, f in e]
        return W.plan({i: W.s_run(i, W.s_side(i, x)) for i in S_OF})

    # the S-side value check refuses the key (and the same variable's 352 key, whose S row the move re-seats off
    # same:1); CTL's burst admits 2 of its 3 SUPP keys by the same supp_ok -- clause (c) FAILs, ARRIVAL uncalibrated
    supp_moved = {"R5-PREFIX": "FAIL", "R5B-CONTROL": "FAIL", "R5B-ARRIVAL": "VOID", "R5-PARTIAL": "FAIL"}
    lazy("supp-proven-stock-value", lambda: stock_site_value(k132, -2),
         need=["not admitted ['351 e0 t0 +132 Global.Int16[11]=-1', '352 e0 t0 +132 Global.Int16[11]=-1']"],
         also=supp_moved, also_need={"R5B-CONTROL": ["(c) FAIL", "SUPP 3 (2 admitted)"]}, rest="PASS")
    lazy("supp-blind-stock-value", lambda: stock_site_value(blind1387, 124),
         need=["not admitted ['351 e0 t0 +1377 Global.Byte[8]=125', '352 e0 t0 +646 Global.Byte[8]=125']"],
         also=supp_moved, also_need={"R5B-CONTROL": ["(c) FAIL", "SUPP 3 (2 admitted)"]}, rest="PASS")

    # the step-1 excusal: a partner whose walk[1:] never crosses 352.0 -> 351 (its exit renumbered 352.9 in S's log)
    # and F5B runs that never run that exit (352 e14 t2) -- versus the base with only F5B's fresh +116 row lost
    s1k = pred["step1_keys"][0]
    in_exit = lambda f: (f["k"] in ("w", "c") and f["fld"] == m_of(s1k["donor"])  # noqa: E731
                         and (f["sid"], f["tag"]) == (s1k["sid"], s1k["tag"]))
    at_116 = lambda f: in_exit(f) and f["ip"] == s1k["ip"]  # noqa: E731

    def no_exit_log(log: dict) -> dict:
        lg, n = json.loads(json.dumps(log)), 0
        for x in lg["log"]:
            if x.get("k") == "cross" and D.entered(x) is not None:
                n += 1
                if n > 1 and [x.get("place", x.get("from")), x.get("exit"), D.entered(x)] == [352, 0, 351]:
                    x["exit"] = 9
        return lg

    def step1_none() -> list:
        runs = {}
        for i, p in W.partner.items():
            lg = no_exit_log(W.s_logs[p])
            wk = D.entered_walk(lg["log"])
            assert [352, 0, 351] not in wk[1:] and wk[0] == [352, 0, 351], wk
            runs[p] = W.s_run(p, log=lg)
            side = W.order[i - 1]
            rows = W.rows("F5B", p, lambda e: RD5.lose(e, in_exit)) if side == "F5B" else None
            runs[i] = W.fork_run(side, i, p, rows, fork_log(pred, side, wk), walk=wk)
        return W.plan(runs)

    lazy("step1-no-crossing", step1_none, need=["(2 step-1 excused; left [])"], rest="PASS")
    lazy("step1-dropped", lambda: W.plan(all_side("F5B", lambda e: RD5.lose(e, at_116))),
         need=["(0 step-1 excused; left ['352 e14 t2 +116 Global.Bit[2103]=0'])"], also={"R5-PARTIAL": "FAIL"})

    def stale_landing(i, p):
        run = f5b(i, p)
        pr = run["rec"]["party"]
        land = dict(pr["landing"], mtime_ns=pr["baseline"]["mtime_ns"])
        land["fresh"], land["why"] = M.freshness(land, pr["baseline"], {"sc": 2600, "entrance": 6, "field": 31101})
        return dict(run, rec=dict(run["rec"], party=dict(pr, landing=land)))

    lazy("party-stale-landing", lambda: W.plan(W.every("F5B", stale_landing)),
         need=["not fresh: landing (st_mtime_ns"], rest="PASS", verdict=NP_PARTY)
    lazy("partyremove-inert", lambda: W.plan(), partyremove=W.partyremove(r3=[0, 2, 3, 1]),
         need=["P-PARTYREMOVE FAIL: r3 reads [0, 2, 3, 1]"], also={"P-PARTYREMOVE": "FAIL"},
         verdict=("FAILED: P-PARTYREMOVE, R5B-PARTY -- P-PARTYREMOVE:",))
    lazy("partyremove-stale-r3", lambda: W.plan(), partyremove=W.partyremove(stale_r3=True),
         need=["r3 not fresh: st_mtime_ns"], also={"R5B-PARTY": "VOID"}, also_need={"R5B-PARTY": [
             "P-PARTYREMOVE VOID: r3 not fresh"]}, rest="PASS", verdict=VERDICT_LINES["partyremove-stale-r3"])

    def unstable_landing(i, p):
        run = f5b(i, p)
        pr = run["rec"]["party"]
        land = dict(pr["landing"], stable=False)
        land["fresh"], land["why"] = M.freshness(land, pr["baseline"], {"sc": 2600, "entrance": 6, "field": 31101})
        return dict(run, rec=dict(run["rec"], party=dict(pr, landing=land)))

    lazy("party-unstable-landing", lambda: W.plan(W.every("F5B", unstable_landing)),
         need=["not fresh: landing (its sha changed between two reads 10 frames apart"], rest="PASS",
         verdict=NP_PARTY)

    def end_entrance(i, p):
        run = f5b(i, p)
        pr = run["rec"]["party"]
        end = dict(pr["end"], entrance=99)
        return dict(run, rec=dict(run["rec"], party=dict(pr, end=end)))

    lazy("party-end-entrance", lambda: W.plan({2: end_entrance(2, 1)}),
         need=["F5B#2/S#1: not fresh: F5B end (entrance 99, not the arrival's"], verdict=NP_PARTY)
    lazy("party-hubleg-save", lambda: W.plan(), hubleg=W.hubleg(ok_save=False),
         need=["the P-HUBLEG (F5B) autosave baseline is not [0, 255, 255, 255] fresh"], rest="PASS", verdict=NP_PARTY)
    lazy("one-ctl", lambda: W.plan({6: W.skipped(6, "CTL"), 9: W.skipped(9, "CTL")}),
         need=["1 covered CTL runs (want >= 2)"],
         also={"R5-RUNS": "VOID", "R5B-LAND": "VOID", "R5B-STATE": "VOID", "R5B-ECHO": "VOID", "R5B-ARRIVAL": "VOID",
               "R5B-PARTY": "VOID"},
         also_need={"R5B-LAND": ["R5B-CONTROL (b) VOID: uncalibrated"]}, rest="PASS",
         verdict=("NOT PROVEN: state, latches, party (", "-- proven: walk"))
    lazy("nowake-entrance-4", lambda: W.plan({2: entrance4(2, 1)}),
         need=["F5B#2: the wake's SC store is in its trace", "F5B#2: rows in 31104 before its first 31101 row",
               "F5B#2: its first member row stands in 31104"], also={"R5-STAMP": "FAIL"})
    lazy("nowake-none-reached", lambda: W.plan({**W.every("F5B", hub_raised),
                                                **W.every("CTL", lambda i, p: hub_raised(i, p, "CTL"))}),
         need=["no fork run reached a member"], also={"R5-STAMP": "VOID"})
    lazy("control-no-recompute", lambda: W.plan(W.every("CTL", ctl_no_recompute)),
         need=["(a) FAIL", "(b) PASS", "(c) FAIL", "(d) PASS", "(e) PASS"],
         also={"R5B-STATE": "VOID", "R5B-ARRIVAL": "VOID", "R5B-LAND": "PASS", "R5B-ECHO": "PASS", "R5B-PARTY": "PASS"},
         also_need={"R5B-STATE": ["R5B-CONTROL (a) FAIL: uncalibrated"]}, verdict=("FAILED: R5B-CONTROL -- ",))
    no_latch = lambda h: [o for o in h if RD5.target(o) not in ("Global.Bit[2078]", "Global.Bit[2086]")]  # noqa
    lazy("land-latches-missing", lambda: W.plan(W.every("F5B", lambda i, p: f5b(i, p, W.rows(
        "F5B", p, hub=W.hub_rows("F5B", p, no_latch), latches=False)))),
         need=["unregistered bits differ in bytes [259, 260]"],
         also={c: "FAIL" for c in ("R5-PREFIX", "R5-STAMP", "R5B-STATE", "R5B-ECHO", "R5B-ARRIVAL", "R5-MIRROR",
                                   "R5-PARTIAL", "R5-LATCH")},
         also_need={"R5B-STATE": ["unregistered bits differ in bytes [238, 241, 251, 259, 260]"],
                    "R5B-ARRIVAL": ["extra ['351 e0 t0 +791 Global.SByte[238]=0', "
                                    "'351 e0 t0 +799 Global.Int16[241]=0']"],
                    "R5B-ECHO": ["ip105: Bit[2078] 1 -> 0 missing", "ip338: Bit[2086] 1 -> 0 missing"]},
         rest="PASS", verdict=VERDICT_LINES["land-latches-missing"])

    def lost_stamp(i, p, tgt):
        """F5B on S#p with its hub's ``tgt`` stamp row lost and NOTHING re-seated (a tracer that dropped a row)."""
        rows = W.base["F5B"][p]
        return f5b(i, p, [o for o in rows if not (o["k"] == "w" and o["fld"] == hid["F5B"]
                                                  and RD5.target(o) == tgt)])

    lazy("land-contradiction", lambda: W.plan({2: lost_stamp(2, 1, "Global.UInt16[0]")}),
         need=["F5B#2/S#1: calibration contradictions"], also={"R5B-STATE": "VOID", "R5-STAMP": "FAIL"},
         also_need={"R5B-STATE": ["F5B#2/S#1: calibration contradictions"]})
    lazy("land-first-value", lambda: W.plan({2: lost_stamp(2, 1, "Global.Bit[2078]")}),
         need=["F5B#2/S#1: New Game values disagree at bits [2078]"], also={"R5B-STATE": "VOID", "R5-STAMP": "FAIL"})
    lazy("land-uncalibrated", lambda: W.plan({i: W.s_run(i, W.s_side(i, lambda e: RD5.edit(e, s297, new=3)))
                                              for i in S_OF}),
         need=["unregistered bits differ in bytes [297]", "R5B-CONTROL (b) FAIL: uncalibrated"],
         also={"R5B-CONTROL": "FAIL", "R5B-STATE": "VOID", "R5-STOCKSTATE": "FAIL"},
         also_need={"R5B-CONTROL": ["(b) FAIL"], "R5B-STATE": ["R5B-CONTROL (a) FAIL: uncalibrated"]},
         verdict=("FAILED: R5-STOCKSTATE, R5B-CONTROL -- ",))
    lazy("state-byte-19", lambda: hub_mut(lambda h: h + [hub_store(last_stamp(h), 2, 3, 180, "Global.UInt16[19]",
                                                                   15)]),
         need=["registered bits do not differ in bytes [19]"], also={"R5B-LAND": "FAIL", "R5-STAMP": "FAIL"})
    lazy("state-short-pairs", lambda: W.plan({8: f5b(8, 7, RD5.cut(W.base["F5B"][7], at_step(7, 8)),
                                                     replay_stop(pred, walks[7], 8, why="the gated door was never "
                                                                                        "faced (2 times)"),
                                                     phase="replay")}),
         need=["2 covered pairs (want >= 3)"], also={"R5B-LAND": "VOID", "R5B-PARTY": "VOID"})
    lazy("echo-2086-missing", lambda: W.plan(all_side("F5B", lambda e: RD5.lose(e, is_2086))),
         need=["450 Main_Init e0 t0 ip338: Bit[2086] 1 -> 0 missing"],
         also={"R5-MIRROR": "FAIL", "R5-LATCH": "FAIL"})
    lazy("echo-uncalibrated", lambda: W.plan(all_side("CTL", ctl_ip105)),
         need=["R5B-CONTROL (d) FAIL"], also={"R5B-CONTROL": "FAIL"}, also_need={"R5B-CONTROL": ["(d) FAIL"]})
    lazy("arrival-extra", lambda: W.plan(all_side("F5B", add_791)),
         need=["extra ['351 e0 t0 +791 Global.SByte[238]=0']"], also={"R5-MIRROR": "FAIL"})
    lazy("arrival-uncalibrated", lambda: W.plan(all_side("CTL", lambda e: RD5.lose(e, is_801))),
         need=["R5B-CONTROL (c) FAIL"], also={"R5B-CONTROL": "FAIL"}, also_need={"R5B-CONTROL": ["(c) FAIL"]})

    def slot_run(i, p):
        run = f5b(i, p)
        return dict(run, rec=dict(run["rec"], party=W.fork_party("F5B", i, run["rows"], slot=[0, 2, 3, 1])))

    lazy("party-slot", lambda: W.plan(W.every("F5B", slot_run)),
         need=["F5B#2/S#1: landing [0, 2, 3, 1], end [0, 2, 3, 1], partner end [0, 255, 255, 255]"])
    lazy("party-footprint", lambda: W.plan({1: W.s_run(1, W.s_side(1, footprint)),
                                            2: f5b(2, 1, W.rows("F5B", 1, footprint))}),
         need=["S#1: party-footprint rows", "F5B#2: party-footprint rows"])

    def ctl_slot(i, p):
        run = ctl(i, p)
        return dict(run, rec=dict(run["rec"], party=W.fork_party("CTL", i, run["rows"], slot=NG_SLOT)))

    lazy("party-control-e", lambda: W.plan(W.every("CTL", ctl_slot)), need=["R5B-CONTROL (e) FAIL: uncalibrated"],
         also={"R5B-CONTROL": "VOID"}, also_need={"R5B-CONTROL": ["(a) PASS", "(e) FAIL"]}, rest="PASS",
         verdict=VERDICT_LINES["party-control-e"])
    # the party instrument that never calibrates, ONE cause read twice: the CTL pick's adds do not show in the
    # autosave -- P-PARTYREMOVE's r1 (and so r2, r3) and every CTL landing read [0,255,255,255]
    lazy("partyremove-uncalibrated", lambda: W.plan(W.every("CTL", ctl_slot)),
         partyremove=W.partyremove(r1=NG_SLOT),
         need=["P-PARTYREMOVE VOID: r1 reads [0, 255, 255, 255], not [0, 2, 3, 1] -- the instrument is uncalibrated",
               "R5B-CONTROL (e) FAIL: uncalibrated"],
         also={"P-PARTYREMOVE": "VOID", "R5B-CONTROL": "VOID"}, rest="PASS",
         verdict=VERDICT_LINES["partyremove-uncalibrated"])
    lazy("hubleg-failed", lambda: W.plan(), hubleg=W.hubleg(failed="F5B"),
         need=["HarnessError: hub leg: no dialogue after 3 tries"], rest="PASS", verdict=VERDICT_LINES["hubleg-failed"])
    lazy("hubleg-missing", lambda: W.plan(), hubleg=W.hubleg(missing="CTL"), need=["the session recorded no leg"],
         also={"R5B-PARTY": "VOID"}, rest="PASS", verdict=VERDICT_LINES["hubleg-missing"])

    lazy("reach-ctl-stops", lambda: W.plan({3: landing_lock(3, 1, 12, "CTL"), 6: landing_lock(6, 4, 12, "CTL")}),
         stops={3: ("FORK-STOP", "landing@351"), 6: ("FORK-STOP", "landing@351")}, halt=None,
         need=["CTL#3 FORK-STOP @landing@351", "CTL#6 FORK-STOP @landing@351"])
    lazy("nc-throw", lambda: W.plan(), nc_throw={"ok": False, "detail": "[('NullReferenceException', 'EventEngine')]"},
         verdict=("FAILED: NC-THROW -- ",))

    # session 3's S#7: a 23-step walk of its own, as S#4
    s3 = Path(a.session3)
    if (s3 / R.SESSION_FILE).is_file():
        sess3 = json.loads((s3 / R.SESSION_FILE).read_text(encoding="utf-8"))
        rec3 = next(r for r in sess3["runs"] if r["i"] == 7)
        r3 = RD5.rows_of(s3 / rec3["trace"])
        l3 = json.loads((s3 / rec3["log"]).read_text(encoding="utf-8"))
        w3 = D.entered_walk(l3["log"])
        s3_run = {"side": "S", "rows": r3, "log": l3,
                  "rec": {**{x: v for x, v in rec3.items() if x in ("segment", "traced", "crossings", "landed",
                                                                    "fields")}, "phase": "settle",
                          "party": W.s_party(4, r3)}}
        f3 = W.rows("F5B", 4, s_rows=r3)
        c3 = W.rows("CTL", 4, s_rows=r3)
        name3 = D.step_name(w3[1:][13])
        assert name3 != D.step_name(sl[1][13]), "the two walks' slice step 14 is one crossing: no case"
        lazy("pass-walks-differ", lambda: W.plan({4: s3_run, 5: f5b(5, 4, f3, fork_log(pred, "F5B", w3), walk=w3),
                                                  6: ctl(6, 4, c3, fork_log(pred, "CTL", w3), walk=w3)}),
             rest="PASS", need=["keys differ between pairs and agree within each"], listed=True)
        lazy("reach-two-walks", lambda: W.plan({2: stop14(2, 1), 4: s3_run, 5: f5b(
            5, 4, RD5.cut(f3, fork_step_at(f3, pred, w3, 14)),
            fork_log(pred, "F5B", w3, steps=13, moved_at=len(w3), stop=f"replay broke at step 14 ({name3}): bounce, "
                                                                       f"bounce"), walk=w3, phase="replay"),
                                                 6: ctl(6, 4, c3, fork_log(pred, "CTL", w3), walk=w3)}),
             stops={2: f14, 5: ("FORK-STOP", f"replay@14({name3})")}, halt=None,
             need=[f"F5B#2 FORK-STOP @{p14}", f"F5B#5 FORK-STOP @replay@14({name3})"])
    else:
        for key in ("pass-walks-differ", "reach-two-walks"):
            tally(key, False, f"  !! MISSING  {key}: no session 3 at {s3} (--session3 DIR)")

    print("\n== MUTANTS (each must come out as registered: the verdict, and where registered the note, the other "
          "checks, the stop class, the halt, the re-run plan, the verdict line)")
    for spec in mutants:
        key = spec["key"]
        chk, want, why = REGISTERED[key]
        if spec.get("stamp_source"):
            H5.STAMP_SOURCE = spec["stamp_source"]
        try:
            sess_over = {k: spec[k] for k in ("hubleg", "partyremove", "nc_throw") if k in spec}
            got_m, _rep, runs_m = case(f"mut-{key}", spec["plan"], snap_=spec.get("snap"), sha=spec.get("sha"),
                                       **sess_over)
        finally:
            H5.STAMP_SOURCE = "raw"
        st, detail = got_m.get(chk, (None, ""))
        probs = [] if st == want else [f"{chk} {st}"]
        probs += [f"the detail does not say {s!r}" for s in spec.get("need", ()) if s not in detail]
        probs += [f"{c} {got_m[c][0]} (registered {v})" for c, v in spec.get("also", {}).items() if got_m[c][0] != v]
        probs += [f"{c}'s detail does not say {s!r}" for c, ss in spec.get("also_need", {}).items() for s in ss
                  if s not in got_m[c][1]]
        probs += [f"{c} {got_m[c][0]} (registered VOID)" for c in spec.get("void", ()) if got_m[c][0] != "VOID"]
        if spec.get("rest"):
            named = {chk, "VERDICT", *spec.get("also", {}), *spec.get("void", ())}
            probs += [f"{c} {w_} (registered {spec['rest']})" for c, (w_, _d) in got_m.items()
                      if c not in named and w_ != spec["rest"]]
        vline = got_m["VERDICT"][1]
        assert spec.get("verdict") in (None, VERDICT_LINES.get(key)), f"{key}: its verdict is not VERDICT_LINES'"
        for n, s in enumerate(VERDICT_LINES.get(key, ())):
            if (n == 0 and not vline.startswith(s)) or (n > 0 and s not in vline):
                probs.append(f"the verdict line {vline[:120]!r} does not {'start with' if n == 0 else 'say'} {s!r}")
        byr = {r["i"]: r for r in runs_m}
        for i, cls in spec.get("stops", {}).items():
            sc = byr[i].get("stop_class")
            have = None if sc is None else (sc["cls"], sc["point"])
            if have != cls:
                probs.append(f"{byr[i]['label']} stop class {have} (registered {cls})")
        if "halt" in spec:
            h, nxt = M.halted5b(runs_m), M.rerun_plan5b(runs_m, pred)
            if h != spec["halt"] or (h is not None and nxt is not None):
                probs.append(f"halted {h}, next {nxt} (registered halt {spec['halt']})")
        if spec.get("no_faults") and M.pairing_faults5b(runs_m, pred):
            probs.append(f"pairing faults {M.pairing_faults5b(runs_m, pred)[:2]}")
        for i, text in spec.get("run_why", {}).items():
            if not any(text in w_ for w_ in byr[i]["why_void"]):
                probs.append(f"{byr[i]['label']} is not VOID {text!r}: {byr[i]['why_void'][:2]}")
        for i, plan_want in spec.get("plan_before", {}).items():
            before = M.judge5b([dict(x) for x in runs_m if x["i"] < i], pred)
            if M.rerun_plan5b(before, pred) != plan_want:
                probs.append(f"the plan before run {i} is {M.rerun_plan5b(before, pred)}, not {plan_want}")
        if "plan_after" in spec and M.rerun_plan5b(runs_m, pred) != spec["plan_after"]:
            probs.append(f"the plan after the nine is {M.rerun_plan5b(runs_m, pred)}, not {spec['plan_after']}")
        if spec.get("listed") and re.search(r"\b0 keys differ between pairs", detail):
            probs.append("R5-PARTIAL lists no key: the walks do not differ in what they wrote")
        probs += [f"{byr[i]['label']} was digested" for i in spec.get("undigested", ()) if byr[i]["digest"] is not None]
        others = [f"{c} {w_}" for c, (w_, _d) in got_m.items() if w_ != "PASS" and c not in (chk, "VERDICT")]
        tally(key, not probs, f"  {'caught' if not probs else '!! MISSED'}  {chk:<13} {want:<4}  {why}"
                              + (f" -- !! {'; '.join(probs)}" if probs else "") + f" || {detail[:150]}"
              + (f" || also not PASS: {', '.join(others)}" if others else "") + f" || {vline[:110]}")

    # -- the registry, the frozen file and the cases run agree --------------------------------------------------------
    print("\n== THE REGISTRY")
    frozen = {(c, why, v) for c, spec in pred["checks"].items() for why, v in spec.get("mutants", [])}
    mine = {(c, why, v) for c, lst in registered_mutants().items() for why, v in lst}
    missing = sorted(k for k in REGISTERED if seen[k] != 1)
    ok_r = frozen == mine and not missing
    n_cases += 1
    bad += not ok_r and only is None
    if only is not None:
        print(f"  (--only {a.only!r}: {len(REGISTERED) - len(missing)} of {len(REGISTERED)} cases ran -- NOT a full "
              f"dry-run)")
    print(f"  {'as registered' if ok_r else '!! WRONG'}  {len(REGISTERED)} registered cases, the frozen file's "
          f"checks.*.mutants the same {len(mine & frozen)}; each run once: {not missing}"
          + (f" -- only in the file {sorted(frozen - mine)[:2]}, only here {sorted(mine - frozen)[:2]}, not run once "
             f"{missing[:4]}" if not ok_r else ""))

    n_cases += 1
    bad += not base_ok
    print(f"\nbase passes every check with {got['VERDICT'][1][:60]!r}: {base_ok}; cases as registered: "
          f"{n_cases - bad}/{n_cases}")
    if not a.keep:
        shutil.rmtree(root, ignore_errors=True)
    return 0 if base_ok and not bad else 1


if __name__ == "__main__":
    sys.exit(main())
