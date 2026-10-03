"""THE STORY-WRITE TRACE, O5 -- THE STAIR WALK AND THE STORED CHOICE, A US SESSION: from a raw warp into 153 (the castle
hallway, entrance 325, the scenario at 1190; EVT_ALEX1_AC_H2F) up the west stair -- the segment's one control grant,
walked by the driver -- to choice 128 answered "Examine her face" (stored in Global.Bit[3795]), through 154@304 (Zorn &
Thorn; EVT_ALEX1_AC_ENT_2F) and 153@316 to the arrival in 151 (EVT_ALEX1_AC_SEAT_R) -- stock against the alxc disc-1
chain O4 deployed, both sides played by one driver (studies/story-trace/PLAN.md, "O5"; the design:
research/o5_design.md).

    py tools/play.py studies/story-trace/o5_hallway.py --label story-o5 --timeout 240
    py studies/story-trace/o5_hallway.py --offline-check     # O4's build and the route pins, the keys, block 3's text
                                                             # (strict), the store census per entrance, the regions,
                                                             # the stair's goals and its contour
    py studies/story-trace/o5_hallway.py --preflight         # the live install (read-only): all green, O4 deployed it
    py studies/story-trace/o5_hallway.py --draft             # the draft predictions, as JSON
    py studies/story-trace/o5_hallway.py --freeze            # write o5_predictions_v1.json (once: the lead, after the
                                                             # stock rehearsals)
    py studies/story-trace/o5_hallway.py --analyse <run dir> # the analysis alone, on saved traces
    py studies/story-trace/o5_hallway.py --rehearsal-report <run dir>   # an o5_rehearse.py launch, stage by stage

THE SIDES (o5_forks.json: O4's chain, reused -- nothing imported, built or deployed for O5):
  S  stock. Start: 153, entrance 325, SC 1190. End: the arrival in REAL 151.
  F  O4's twenty members 31240-31259 as deployed: member(153) 31245 (visits 1 and 3), member(154) 31246, and the end in
     member(151) 31244 -- read from O4's campaign.toml, never assumed. Every route Field() is retargeted, so the chain is
     closed (no seam), and a landing in a REAL donor field on F is V19, a finding.

THE ENTRY: New Game, the trace armed, then in field 70 a raw `warp <153 | 31245> 325 1190`: FOUR residue rows in field
70 (SC's two bytes and FieldEntrance's two: 325 is 0x0145), which the front cut sets aside and O5-START requires.

THE ROUTE: segment_drive.drive with ONE visit-scoped cell (153, 1190, visit 1: the stair walk, a trigger step whose
evidence is the PSX y -450 contour's side, x <= -1100), the pre-choice guard (127's page-once, the quiet window, 128
answered "Examine her face" by the VERIFIED landing, the game's own branch page judged), the run-wide input witness, the
stop page; no battle, no movie, no naming. Control anywhere else -- 154@304, 153@316 -- is V4 (game) at its [place, sc,
visit] cell.

THE ANALYSIS: each run cut at its start row (153's first write) and at its first row in an end PLACE (151: member(151)
on F), digested and compared as O1-O4's; the O5 checks (research/o5_design.md 5.3) read the start, no SC rung, the
chain, the residue, the writes EXACTLY, the landing per side (the revisit's first EMITTED row, start-scoped), the stored
choice against the driver's verified pick and the game's own branch page, the walk (THE PAIRED-WALK LAW), the sink's
emitted row pattern EXACTLY (its same-value suppression), the masked regions, the state handed to 151, and every run's
VOID classes by [place, sc, visit]. The predictions are frozen by the lead after the stock rehearsals (o5_rehearse.py);
until then --offline-check and --preflight read the draft.
"""
from __future__ import annotations

import copy
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))

from ff9mapkit import storytrace as T                                   # noqa: E402
import o2_alexandria as A                                               # noqa: E402
import o3_prima_vista as P                                              # noqa: E402
import o4_castle as C4                                                  # noqa: E402
import segment_drive as SD                                              # noqa: E402
import segment_trace as ST                                              # noqa: E402
from segment_trace import (SIDES, cut_at_end, cut_at_start, is_noise, key_of, members_of, place,  # noqa: E402
                           row_keys, wkey)

PREDICTIONS = HERE / "o5_predictions_v1.json"
MANIFEST = HERE / "o5_forks.json"
SESSION_FILE = "o5_session.json"
REPORT_FILE = "o5_report.txt"
REHEARSAL_FILE = "o5_rehearsal.json"
#: O4's chain and build, reused (research/o5_design.md 0.1 #2, 6.4): nothing is imported, built or deployed for O5.
CHAIN_DIR = C4.CHAIN_DIR
BUILD_DIR = C4.BUILD_DIR
GAME = A.GAME
SESSION_LANG = "us"
#: The text block the route's members carry (EVENT_ID_TO_MES): block 3 for 150-167. O5 reads no other.
TEXT_BLOCK, TEXT_BLOCKS = 3, (3,)
#: The route's places, the order it visits them in (153 twice: 325, then 316), and the end place.
ROUTE = (153, 154)
VISITS = (153, 154, 153)
END_FIELD = 151
#: The donors P-DONOR and P-DONOR-LOG read, and the route members derived from the chain: the route's and the end's.
ROUTE_DONORS = (153, 154, 151)
#: 4.13: O4's frozen settings, override, engine and derived facts, unchanged (research/o5_design.md 4.13).
SETTINGS = C4.SETTINGS
OVERRIDE70 = C4.OVERRIDE70
ENGINE = C4.ENGINE
DERIVED = C4.DERIVED
#: 2.4: stock 153's 33 floor-0 upper triangles the stair walk closes -- the corridor over the hall, which would otherwise
#: be the first triangle a point on the hall answers (no route at all on the plain mesh: the research's route153.out).
CLOSED_TRIS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 14, 15, 16, 17, 18, 19, 20, 21, 23, 24, 28, 32, 33, 34, 35, 38, 39, 41,
               42, 43, 45, 46]
#: 2.4: THE STAIR STEP (153, 1190, visit 1) -- the walk plan with the critic's corrections, O2's steps_default under it.
STAIRS = {"kind": "trigger", "name": "the stairs", "goal": [-1700, 300], "until": {"x_le": -1100},
          "avoid": ["153.e26", "153.e27", "153.e28"], "closed_tris": list(CLOSED_TRIS), "npcs": True, "interrupts": 1,
          "beat": "stairs", "start": [1105, -78]}
#: 153 e3 t1 ip859's stage-6 height test, ``obj(uid=255).f[1] const(65086) B_GT``: f[1] is -pos[1] and a 2-byte
#: constant is signed, so the stair's goal is PSX y <= -450 (0.2 #9).
CONTOUR_Y = -450
#: The keys a rehearsal stage may lay over a table step and the freeze refuses (7.1 R-WALK-VOID's stop).
REHEARSAL_OVERLAYS = frozenset({"walk_stop_x"})
#: 4.10: the pre-choice guard and the run-wide witness (F2, F6 and F9 re-size them from the rehearsals).
GUARD = {"donor": 153, "sc": 1190, "markers": ["let me pass"], "choice": "her face",
         "branch": ["Let\u2019s see", "Hold on a sec"], "page_once_ticks": 10, "quiet_cap_s": 2.7,
         "why": "153 e31 t1 ip663 WindowSync(2,128,127) -> ip669 WaitAnimation (RunAnimation(3387) ip648) -> ip670 "
                "Map.Bit[231] := 1 -> e2 t1 Map.Byte[24] := 20 (the next tick) -> e3 t1 ip1724 WindowSync(0,128,128) "
                "[IMME], ~2 ticks after 127 is gone plus the animation's rest: a Confirm decided on a stale or closing "
                "127 can land on 128 at its cursor (0); 128's answer -> Map.Byte[27] (ip1749) -> e2 t1 ip844: 141 (path "
                "1, the pick) or 129 (path 0) first"}
WITNESS = {"input_every_s": 0.05,
           "why": "Bit[3795] stores the player's answer: outside input at the choice would store another value while "
                  "the driver logs its pick (critic #10)"}
PAIR_TEXT = C4.PAIR_TEXT
#: 5.4's scope lines that are constants; the settings, the engine and the language are read from the session's record.
SCOPE_START = (
    "under the raw warp no key's VALUE on the route is start-dependent (constants and the frozen pick; Byte[6] |= 8 is "
    "after the cut); the EMITTED ROW PATTERN is: the sink emits the first same-value store per site per epoch "
    "(StoryTrace.cs:383-401), so after this start visit 1's ip57/ip119 are changes and visit 3's are emitted (same 1) "
    "while its ip22/ip49/ip138/ip200 are suppressed; after a true O1-O4 run visit 1's would be same-value and visit 3's "
    "first emitted row would be e18 t1 ip890; the old values differ too (Int16[9] 643 vs -1, Byte[13] 1 vs 0, Byte[8] "
    "125 vs 75 at ip2953). O5-PATTERN's frozen sequences and counts, LANDING (b)'s re-entry row, STATE (a)'s ordered "
    "histories and every row count are this start's: never reuse them against a chained true-run trace. Not covered: "
    "party data, names, gil, Map variables (Map.Byte[27] is READ, as the branch witness's page, never compared), the "
    "camera, field 70's override state, and the fifteen untouched targets' values after a true O1-O4 run")
SCOPE_SUPPRESSED = (
    "the four suppressed stores before the cut, 153's visit-3 ip22/ip49 (masked) and ip138/ip200, are COMPARED by "
    "O5-PATTERN (a): each present, each counted once (n 1), each with its last value, as a multiset -- their TIME is "
    "not compared (the engine writes a count at the epoch's close) and neither is their order among the w rows. Nothing "
    "else compares them: MASKED compares region names (its counts are reported), and STATE (a)'s suppressed set drops a "
    "count whose last value an emitted key carries -- all four here. The end place 151's c rows are cut and hold only "
    "stores after the cut (its first store IS the cut)")
SCOPE_CHOICE = (
    "the stored value is compared with the driver's verified index and with the GAME's own branch page after the "
    "answer (141 for 1, 129 for 0: Map.Byte[27] := SYSVAR[9] at ip1749, read by e2 t1 ip844), so outside input that "
    "moved the cursor after the last sample before the answer's down frame -- invisible to selected_before -- VOIDs the "
    "run (the other branch's page: V13) instead of reading as 'a fork that stores a constant'; what remains is a fork "
    "that stores SYSVAR[9] and branches on something else -- both bytes are pinned, O5-KEYS")
SCOPE_END_STATE = ("Byte[8] is read from the trace (153 e18 t1 ip890 := 0, the last pre-cut write; frozen by "
                   "O5-PATTERN (b)), not live: 151 e0 t0 ip315 races the read")
_MODULE_DOC = __doc__


# ======================================================================== the chain (O4's campaign.toml)
def chain_from_campaign(campaign=None) -> tuple:
    """``({fork id: donor}, {fork id: member name})`` of O4's built alxc chain (its ``campaign.toml``; default O4's):
    its donors exactly O4's twenty (o4_castle.chain_from_campaign refuses another chain)."""
    return C4.chain_from_campaign(Path(campaign) if campaign is not None else CHAIN_DIR / "campaign.toml")


def route_members(members: dict) -> dict:
    """``{153: fork id, 154: fork id, 151: fork id}``: the members the route runs and ends in (derived, each donor
    forked by exactly one member)."""
    out = {}
    for donor in ROUTE_DONORS:
        hits = sorted(f for f, d in members.items() if d == donor)
        if len(hits) != 1:
            raise AssertionError(f"donor {donor} is forked by {hits}, not exactly one member")
        out[donor] = hits[0]
    return out


def route_members_line(members: dict) -> str:
    """The line --offline-check and --draft print: ``member(153) 31245, member(154) 31246, member(151) 31244``."""
    rm = route_members(members)
    return ", ".join(f"member({d}) {rm[d]}" for d in ROUTE_DONORS)


# ======================================================================== the predictions (draft v1)
def _key(donor, sid, tag, ip, off, target, value, op, what, prior=None) -> dict:
    return A._key(donor, sid, tag, ip, off, target, value, op, what, prior)


def _site(place_, sid, tag, ip, target, value, **kw) -> dict:
    return C4._site(place_, sid, tag, ip, target, value, **kw)


def route_pins() -> list:
    """4.14's route pins: ``[donor, sid, tag, ip, eb-src text]`` -- the bytes the driver, the guard and the FakeGame rest
    on, each compared EXACTLY with the stock US script's instruction text (O5-KEYS (b)): 53 instruction sites."""
    pins = [[153, 0, 0, 255, "SWITCHEX(L1098, 325, L273, 5, L438, 328, L603, 316, L799, 3, L951)"],
            [153, 0, 0, 232, "SET({Global.UInt16[0] const(1900) B_GT B_EXPR_END})"],
            [153, 0, 0, 302, "InitRegion(26, 0)"], [153, 0, 0, 305, "InitRegion(27, 0)"],
            [153, 0, 0, 308, "InitRegion(28, 0)"],
            [153, 3, 1, 752, "WaitWindow(1)"], [153, 3, 1, 755, "SET({Map.Bit[158] const(1) B_LET B_EXPR_END})"],
            [153, 3, 1, 785, "EnableMove()"],
            [153, 3, 1, 859, "SET({obj(uid=255).f[1] const(65086) B_GT B_EXPR_END})"],
            [153, 3, 1, 874, "SET({Map.Bit[158] const(0) B_LET B_EXPR_END})"], [153, 3, 1, 893, "DisableMove()"],
            [153, 3, 1, 1466, "CreateObject(64371, 856)"],
            [153, 31, 1, 663, "WindowSync(2, 128, 127)"],
            [153, 31, 1, 670, "SET({Map.Bit[231] const(1) B_LET B_EXPR_END})"],
            [153, 31, 1, 648, "RunAnimation(3387)"], [153, 31, 1, 669, "WaitAnimation()"],
            [153, 3, 1, 1713, "SET({Global.Int16[2] const(3) B_NE B_EXPR_END})"],
            [153, 3, 1, 1724, "WindowSync(0, 128, 128)"],
            [153, 3, 1, 1741, "SET({Global.Bit[3795] B_SYSVAR[9] B_LET B_EXPR_END})"],
            [153, 3, 1, 1749, "SET({Map.Byte[27] B_SYSVAR[9] B_LET B_EXPR_END})"],
            [153, 2, 1, 840, "SET({Map.Byte[27] B_EXPR_END})"], [153, 2, 1, 844, "SWITCH(0, L865, L843, L854)"],
            [153, 3, 1, 1899, "WindowAsync(0, 128, 129)"], [153, 3, 1, 3430, "WindowAsync(0, 128, 141)"]]
    pins += [[153, 3, 1, 2336, PAIR_TEXT], [153, 3, 1, 2711, PAIR_TEXT], [154, 2, 1, 215, PAIR_TEXT],
             [154, 2, 1, 392, PAIR_TEXT], [154, 2, 1, 1265, PAIR_TEXT], [153, 18, 1, 444, PAIR_TEXT],
             [153, 20, 1, 883, PAIR_TEXT]]
    pins += [[153, 3, 1, 2443, "RunVibrationTrack(0, 0, 1)"], [153, 3, 1, 2448, "RunVibrationTrack(0, 1, 0)"],
             [153, 3, 1, 2453, "ActivateVibration(1)"],
             [153, 26, 2, 38, "SET({obj(uid=250).f[1] const(65436) B_GT obj(uid=250).f[2] const(1333) B_GT B_ANDAND "
                              "B_EXPR_END})"],
             [153, 26, 2, 58, "SET({Map.Byte[24] const(6) B_EQ B_EXPR_END})"], [153, 26, 2, 88, "DisableMove()"],
             [153, 26, 2, 110, "SET({Map.Byte[24] const(7) B_LET B_EXPR_END})"],
             [153, 27, 2, 38, "SET({Map.Byte[24] const(6) B_EQ B_EXPR_END})"], [153, 27, 2, 68, "DisableMove()"],
             [153, 27, 2, 90, "SET({Map.Byte[24] const(14) B_LET B_EXPR_END})"],
             [153, 28, 2, 30, "SET({B_SYSVAR[2] B_EXPR_END})"],
             [153, 28, 2, 38, "SET({Global.Byte[8] const(25) B_LET B_EXPR_END})"], [153, 28, 2, 83, "ExitField()"],
             [153, 28, 2, 227, "SET({Global.Int16[2] const(5) B_LET B_EXPR_END})"], [153, 28, 2, 235, "Field(150)"],
             [153, 3, 1, 3158, "Field(154)"], [154, 2, 1, 1528, "Field(153)"], [153, 18, 1, 1085, "Field(151)"],
             [154, 0, 0, 234, "SWITCH(304, L392, L232)"],
             [151, 0, 0, 22, "SET({Global.Bit[191] const(0) B_LET B_EXPR_END})"],
             [151, 0, 0, 232, "SET({Global.Int16[2] const(110) B_EQ B_EXPR_END})"],
             [151, 0, 0, 315, "SET({Global.Byte[8] const(125) B_LET B_EXPR_END})"]]
    return pins


def route_build() -> dict:
    """O5-BUILD's route pins (6.1), measured by C0 on O4's build (every language): each route member's in-chain
    ``Field()`` sites ``[sid, tag, ip, literal]`` (US ips; the same in all 7 languages) -- the ONLY bytes it differs from
    its donor in are these operands. member(153)'s e3 t1 ip3296 ``Field(204)`` stays the donor's (204 is no chain
    donor)."""
    return {"fields": {"153": [[3, 1, 3158, 154], [18, 1, 1085, 151], [23, 2, 211, 154], [24, 2, 191, 150],
                               [25, 2, 203, 64], [25, 2, 429, 151], [28, 2, 235, 150]],
                       "154": [[2, 1, 1528, 153], [8, 2, 203, 153], [8, 2, 363, 158], [9, 2, 203, 156],
                               [9, 2, 363, 155], [10, 2, 203, 156], [10, 2, 363, 167]],
                       "151": [[2, 1, 940, 153], [8, 2, 245, 153]]},
            "why": "C0 (research/o5_design.md 9 PART C) on O4's build C:/gd/_ns_playtest/o4/build: per language, each "
                   "route member differs from its donor in exactly these operands (153: 14 bytes, 154: 14, 151: 4)"}


def _regions() -> dict:
    """4.15's regions: each the FIRST SetRegion of its (donor, entry) in the stock bytes, in the engine's point order
    (O5-REGIONS re-decodes each), with its role. e23/e24/e25 are e26/e28/e27's twin quads, instanced at 328 and the
    default only: registered ``exit``, they would mislabel a side-scene loss as a door (the research's dispute 13)."""
    e26 = [[-227, 3000], [200, 3000], [212, 935], [-264, 924]]
    e27 = [[-777, -2348], [777, -2348], [777, -900], [-777, -900]]
    e28 = [[2850, 347], [2850, -13], [1739, -74], [1739, 406]]
    return {
        "153.e28": A._exit(e28, 150, 5, None,
                           why="the back door: its tag 2 tests SYSVAR[2] alone (control), ip38 Byte[8] := 25, ip83 "
                               "ExitField(), ip227 Int16[2] := 5, ip235 Field(150)"),
        "153.e26": A._region(e26, "scene", stage=6,
                             why="side scene A: tag 2 on the ground and z > 1333 at stage 6, Map.Byte[24] := 7; no "
                                 "global store; re-grant e3 t1 ip1266"),
        "153.e27": A._region(e27, "scene", stage=6, why="side scene B: Map.Byte[24] := 14"),
        "153.e23": A._region(e26, "dormant", entrances=[325, 316], why="e26's twin quad (-> 154 @315): instanced at "
                                                                       "328 and the default only"),
        "153.e24": A._region(e28, "dormant", entrances=[325, 316], why="e28's twin quad (-> 150 @315)"),
        "153.e25": A._region(e27, "dormant", entrances=[325, 316], why="e27's twin quad (-> 64 / 151 @315)"),
        "154.e8": A._region([[2222, -5555], [-2222, -5555], [-2222, -4080], [2222, -4080]], "dormant",
                            entrances=[304], why="-> 153 @301, 158 @300: instanced at 315 only"),
        "154.e9": A._region([[-3777, -999], [-3777, -3111], [-1888, -3111], [-1888, -999]], "dormant",
                            entrances=[304], why="-> 156, 155: instanced at 315 only"),
        "154.e10": A._region([[3777, -999], [3777, -3111], [1888, -3111], [1888, -999]], "dormant",
                             entrances=[304], why="-> 156, 167: instanced at 315 only"),
    }


def _pattern() -> dict:
    """4.16: THE EMITTED ROW PATTERN, the suppression model's prediction over this start (field 70's prologue values,
    the raw warp): each visit's emitted ``w`` rows in order, ``[place, sid, tag, off, target, new, same]`` -- visit 1's
    ip57/ip119 changes, visit 2's eight new sites, visit 3's first EMITTED row 153 e0 t0 ip57 (``same`` 1) with its
    ip22/ip49/ip138/ip200 suppressed -- and the epoch's four ``c`` rows of place 153, ``[place, sid, tag, off, target, n,
    last]``. Offsets are the join's (0.2 #4). R-FULL measures every tuple before the freeze (F4)."""
    def pro(place_, same):
        rows = [[place_, 0, 0, 16, "Global.Bit[191]", 0, 1], [place_, 0, 0, 43, "Global.Bit[184]", 0, 1],
                [place_, 0, 0, 51, "Global.Int16[9]", -1, same], [place_, 0, 0, 113, "Global.Byte[13]", 0, same],
                [place_, 0, 0, 132, "Global.Int16[11]", -1, 1], [place_, 0, 0, 194, "Global.Byte[14]", 0, 1]]
        return rows
    v1 = pro(153, 0) + [[153, 3, 1, 1333, "Global.Bit[3795]", 1, 0], [153, 3, 1, 2545, "Global.Byte[8]", 0, 0],
                        [153, 3, 1, 2742, "Global.Int16[2]", 304, 0]]
    v2 = pro(154, 1) + [[154, 0, 0, 269, "Global.Byte[8]", 125, 0], [154, 2, 1, 1409, "Global.Int16[2]", 316, 0]]
    v3 = [[153, 0, 0, 51, "Global.Int16[9]", -1, 1], [153, 0, 0, 113, "Global.Byte[13]", 0, 1],
          [153, 18, 1, 766, "Global.Byte[8]", 0, 0], [153, 18, 1, 953, "Global.Int16[2]", 110, 0]]
    counts = [[153, 0, 0, 16, "Global.Bit[191]", 1, 0], [153, 0, 0, 43, "Global.Bit[184]", 1, 0],
              [153, 0, 0, 132, "Global.Int16[11]", 1, -1], [153, 0, 0, 194, "Global.Byte[14]", 1, 0]]
    return {"visits": [v1, v2, v3], "counts": counts,
            "why": "StoryTrace.cs:383-401 over the raw warp's start values (Int16[9] 643, Byte[13] 1, Int16[11] -1, "
                   "Byte[14] 0, Byte[8] 125, Bit[191] 0, Bit[184] 0): a site emits its first same-value store and up to "
                   "64 changes per epoch; the revisit of 153 at 316 suppresses ip22/ip49/ip138/ip200 (their visit-1 "
                   "stores were same-value) and emits ip57/ip119 (their visit-1 stores were changes)"}


def draft_predictions(campaign=None) -> dict:
    """The registered claims (research/o5_design.md section 4). Every number was read off the stock bytes (the offline
    check re-derives each: O5-BUILD's pins, O5-KEYS with the route pins, O5-TEXT, O5-CENSUS per entrance, O5-REGIONS,
    O5-GOALS), O4's build (C0), the live install or O4's campaign.toml (``campaign``); nothing is read from a run. The
    rehearsals (o5_rehearse.py) settle the driver's numbers before the lead freezes them (7.3)."""
    members, names = chain_from_campaign(campaign)
    rm = route_members(members)
    key = _key
    writes = P._ambient(153, (57, 119, 138, 200)) + [
        dict(key(153, 3, 1, 1741, 1333, "Global.Bit[3795]", 1, ":=var",
                 "153 Bit[3795] := SYSVAR[9] (THE STORED CHOICE: 'Examine her face', 0 -> 1)"), rvalue="B_SYSVAR[9]"),
        key(153, 3, 1, 2953, 2545, "Global.Byte[8]", 0, ":=", "153 Byte[8] := 0 (stage 30; old 125 after the raw "
                                                               "warp)")] \
        + P._ambient(154, (61, 123, 142, 204)) + [
        key(154, 0, 0, 279, 269, "Global.Byte[8]", 125, ":=", "154 Byte[8] := 125 (the 304 branch, after the sound "
                                                               "wait)"),
        key(153, 18, 1, 890, 766, "Global.Byte[8]", 0, ":=", "153 Byte[8] := 0 (stage 114, visit 3)")]
    chain = [key(153, 3, 1, 3150, 2742, "Global.Int16[2]", 304, ":=", "FieldEntrance 304: 153 stage 30, then "
                                                                      "Field(154)"),
             key(154, 2, 1, 1520, 1409, "Global.Int16[2]", 316, ":=", "FieldEntrance 316: 154 stage 6, then "
                                                                      "Field(153)"),
             key(153, 18, 1, 1077, 953, "Global.Int16[2]", 110, ":=", "FieldEntrance 110: 153 stage 114 (visit 3), "
                                                                      "then Field(151)")]
    error_path = [key(donor, 0, 0, ip, off, target, value, ":=", f"{donor} e0 t0 ip{ip}: the error path ({target} := "
                                                                  f"{value})")
                  for donor, ip, off, target, value in (
        (153, 97, 91, "Global.Byte[13]", 9), (153, 178, 172, "Global.Byte[14]", 9),
        (153, 2314, 2308, "Global.Byte[13]", 0), (153, 2348, 2342, "Global.Byte[14]", 0),
        (154, 101, 91, "Global.Byte[13]", 9), (154, 182, 172, "Global.Byte[14]", 9),
        (154, 497, 487, "Global.Byte[13]", 0), (154, 531, 521, "Global.Byte[14]", 0))]
    forbidden_sites = [
        key(153, 28, 2, 38, 8, "Global.Byte[8]", 25, ":=", "153 e28 Byte[8] := 25 (the back door to 150)"),
        key(153, 28, 2, 227, 197, "Global.Int16[2]", 5, ":=", "153 e28 Int16[2] := 5 (the back door's entrance)")]
    dead = [
        key(153, 0, 0, 41, 35, "Global.Int16[2]", 10000, ":=", "153 Int16[2] := 10000 (dead: Bit[184] == 1)"),
        key(153, 0, 0, 130, 124, "Global.Byte[13]", 1, ":=", "153 Byte[13] := 1 (dead: Int16[9] just set -1)"),
        key(153, 0, 0, 211, 205, "Global.Byte[14]", 1, ":=", "153 Byte[14] := 1 (dead: Int16[11] just set -1)"),
        key(153, 0, 0, 243, 237, "Global.Int16[2]", 3, ":=", "153 Int16[2] := 3 (dead: ip232 SC > 1900 false)"),
        key(153, 0, 0, 1188, 1182, "Global.Byte[8]", 125, ":=", "153 Byte[8] := 125 (dead: the default entrance's "
                                                                 "branch, L1098)"),
        key(153, 0, 0, 1260, 1254, "Global.Byte[8]", 125, ":=", "153 Byte[8] := 125 (dead: the default entrance's "
                                                                 "branch, L1098)"),
        key(153, 3, 1, 3168, 2760, "Global.Byte[8]", 0, ":=", "153 e3 Byte[8] := 0 (dead: the flashback, ip2942 "
                                                               "Int16[2] != 3 false only at entrance 3)"),
        key(153, 3, 1, 3288, 2880, "Global.Int16[2]", 0, ":=", "153 e3 Int16[2] := 0 (dead: the flashback)"),
        key(154, 0, 0, 45, 35, "Global.Int16[2]", 10000, ":=", "154 Int16[2] := 10000 (dead: Bit[184] == 1)"),
        key(154, 0, 0, 134, 124, "Global.Byte[13]", 1, ":=", "154 Byte[13] := 1 (dead: Int16[9] just set -1)"),
        key(154, 0, 0, 215, 205, "Global.Byte[14]", 1, ":=", "154 Byte[14] := 1 (dead: Int16[11] just set -1)")]
    inert = ([{"donor": 153, "sid": s, "tags": "*", "why": "instanced at 328 and the default entrance only"}
              for s in (23, 24, 25, 32)]
             + [{"donor": 153, "sid": 15, "tags": "*", "shared_by": [32],
                 "why": "a shared entry (Byte[8] := 125 ip32): run only by e32 t1 ip866 RunSharedScript(15)"}]
             + [{"donor": 154, "sid": s, "tags": "*", "why": "instanced at 315 / the default only"}
                for s in (5, 8, 9, 10)])
    start_music = dict(key(153, 0, 0, 119, 113, "Global.Byte[13]", 0, ":=",
                           "153's ambient branch from the warp's Byte[13] 1 (field 70's prologue :=1 at ip130; the warp "
                           "leaves 70 before ip475's :=2)"), old=1)
    return {
        "version": 1,
        "what": f"O5: 153@1190 (warp, entrance 325; EVT_ALEX1_AC_H2F) -> the stairs -> choice 128 'Examine her face' "
                f"-> 154@304 (EVT_ALEX1_AC_ENT_2F) -> 153@316 -> Field(151) (EVT_ALEX1_AC_SEAT_R), SC 1190; stock vs "
                f"the alxc disc-1 chain as O4 deployed it (route members {rm[151]}-{rm[154]}; PLAN.md, O5) -- a US "
                f"session",
        "rehearsals": ["20261003-090247-o5-rh-stairs", "20261003-090534-o5-rh-full",     # 7.3 (F1-F15)
                       "20261003-090932-o5-rh-r-walk-void", "20261003-091010-o5-rh-f-smoke",
                       "20261003-091153-o5-rh-f-pass"],
        "order": ["S", "F", "S", "F", "S", "F"],
        "min_covered": 2,
        "rerun": {"max": 2, "stop_on": ["V19"]},
        # F6 replaces every number from the rehearsals (4.12)
        "budget": {"run_s": 224, "run_min_s": 132, "session_s": 2644, "settle_s": 1.0, "no_progress_s": 60,
                   "end_row_s": 10.0},
        "start": {"S": ROUTE[0], "F": rm[ROUTE[0]]},
        "entrance": 325,
        "scenario": 1190,
        "lang": SESSION_LANG,
        "end_field": END_FIELD,
        "end_fields": [END_FIELD],
        "side_ends": {"S": [END_FIELD], "F": [rm[END_FIELD]]},
        "route": list(ROUTE),
        "visits": list(VISITS),
        "stock_fields": [151, 153, 154],
        "members": {str(f): d for f, d in sorted(members.items())},
        "names": {str(f): n for f, n in sorted(names.items())},
        "text_block": TEXT_BLOCK,
        "text_blocks": list(TEXT_BLOCKS),
        "recovery": 4600,
        "cut_start": True,
        "start_first": key(153, 0, 0, 22, 16, "Global.Bit[191]", 0, ":=",
                           "153's Main_Init: its first store (emitted same: a new site)"),
        "start_music": start_music,
        # SC 1190 = 0x04A6 (bytes 0 and 1); FieldEntrance 325 = 0x0145 (bytes 2 AND 3): FOUR rows (StoryTrace.cs Diff)
        "start_residue": [[0, 0, 166], [1, 0, 4], [2, 0, 69], [3, 0, 1]],
        "residue_after_start": [],
        "sc_bytes": [0, 1],
        "ladder": [],
        "entrance_bytes": [2, 3],
        "chain": chain,
        "writes": writes,
        "error_path": error_path,
        "forbidden_sites": forbidden_sites,
        "dead": dead,
        "inert": inert,
        "start_dependent": [],
        "noise": [],
        "forbidden": [{"off_route": True, "cause": "walk",
                       "why": "a write off the route: S, a place outside [153, 154] + [151]; F, a field that is "
                              "neither a member whose donor is on the route nor F's own end field (real 151/153/154 on "
                              "F: an un-retargeted Field() or an engine id leak; 150/31243 after the back door, backed "
                              "by its V11 step row)"}],
        "landing": {"route_places": list(ROUTE),
                    "exit153": _site(153, 3, 1, 3150, "Global.Int16[2]", 304),
                    "enter154": _site(154, 0, 0, 26, "Global.Bit[191]", 0),
                    "exit154": _site(154, 2, 1, 1520, "Global.Int16[2]", 316),
                    "enter153b": _site(153, 0, 0, 57, "Global.Int16[9]", -1, old=-1),
                    "exit153b": _site(153, 18, 1, 1077, "Global.Int16[2]", 110),
                    "end_row": _site(END_FIELD, 0, 0, 22, "Global.Bit[191]", 0)},
        "choice": {"store": _site(153, 3, 1, 1741, "Global.Bit[3795]", 1, old=0), "rule": "her face", "index": 1,
                   "beat": "choice128",
                   "why": "128 answered 'Examine her face' (absolute 1, the second [CHOO] line): Bit[3795] := SYSVAR[9] "
                          "at ip1741 in the tick 128's WindowSync returns"},
        "walk": {"name": "the stairs", "donor": 153, "visit": 1, "contour_y": CONTOUR_Y,
                 "why": "153 e3 t1 ip859: the stage-6 height test (obj(uid=255).f[1] > -450: PSX y <= -450 takes "
                        "control); THE PAIRED-WALK LAW: the walk stores nothing"},
        "end_state": {"Global.UInt16[0]": 1190, "Global.Int16[2]": 110, "Global.Bit[3795]": 1,
                      "Global.Byte[13]": 0, "Global.Byte[14]": 0, "Global.Int16[9]": -1, "Global.Int16[11]": -1,
                      "Global.Bit[191]": 0, "Global.Bit[184]": 0,
                      "Global.Byte[6]": 0, "Global.UInt16[19]": 0, "Global.UInt16[21]": 0, "Global.Byte[303]": 0,
                      "Global.Byte[4]": 0, "Global.Byte[17]": 0, "Global.Byte[18]": 0, "Global.Byte[475]": 0,
                      "Global.Bit[3815]": 0, "Global.Bit[3793]": 0, "Global.Bit[3717]": 0, "Global.Bit[3718]": 0,
                      "Global.Int16[469]": 0, "Global.Byte[472]": 0, "Global.Byte[206]": 0},
        "battles": [],
        "stop_pages": [{"match": "Env Play()",
                        "why": "153's and 154's ambient error window 56 ('Error Env Play() Slot=n': 153 e0 t0 "
                               "ip2304/2338, 154 e0 t0 ip487/521): Byte[13]/[14] arrived as 2 or 9"}],
        "regions": _regions(),
        "hotspots": {},
        "table": [{"donor": 153, "sc": 1190, "visit": 1, "steps": [copy.deepcopy(STAIRS)]}],
        "steps_default": {"attempts": 2, "interrupts": 1, "timeout_s": 20, "confirm_s": 4.0, "npcs": True,
                          "overlay_ok": False, "immediate": False, "settle": None, "lunge_ticks": 0, "tolerance": 45,
                          "min_depth": 40, "exit_wait_s": 5.0, "exit_slack": 40,
                          "climb": {"burst_frames": 30, "max_bursts": 80, "stall_bursts": 8}},
        "choices": [{"donor": 153, "sc": [1190], "match": "her face", "pick": "her face", "once": True,
                     "beat": "choice128"},
                    {"donor": None, "sc": None, "match": "want to skip", "pick": "default", "once": False,
                     "beat": None}],
        "naming": [],
        "beats": ["stairs", "choice128"],
        "guard": json.loads(json.dumps(GUARD)),
        "witness": dict(WITNESS),
        "route_pins": route_pins(),
        "route_mes": {"block": TEXT_BLOCK, "marker": 127, "choice": {"mes": 128, "opens": "[PCHC=2,1]",
                                                                    "holds": "[IMME]", "pick_line": 1},
                      "branch": [141, 129], "stop_page": 56},
        "route_build": route_build(),
        "pattern": _pattern(),
        "settings": json.loads(json.dumps(SETTINGS)),
        "override70": dict(OVERRIDE70),
        "derived": json.loads(json.dumps(DERIVED)),
        "engine": dict(ENGINE),
    }


# ======================================================================== the visits, the census, the regions (pure)
def visit_entrances(pred: dict) -> dict:
    """``{place: [entrances, in visit order]}`` (research/o5_design.md 0.2 #10): the start place by ``entrance``; each
    later visit by the ``chain`` key before it -- the k-th chain key is the k-th visit's exit, so it must stand in that
    visit's place: {153: [325, 316], 154: [304]}. O4's ``route_entrances`` maps a PLACE to one entrance, the place
    before it's LAST chain value -- for 154 it gives 110 (153's ip1077): the reason O5 has its own. ValueError on a chain
    whose k-th key is not the k-th visit's place."""
    visits = list(pred.get("visits") or pred["route"])
    chain = list(pred.get("chain") or ())
    out = {visits[0]: [int(pred["entrance"])]}
    for i in range(1, len(visits)):
        k = chain[i - 1] if i - 1 < len(chain) else None
        if k is None or k["donor"] != visits[i - 1]:
            raise ValueError(f"visit {i + 1} ({visits[i]}): the chain key before it is "
                             f"{'none' if k is None else A.label(k)}, not the exit of visit {i} ({visits[i - 1]})")
        ent = int(k["value"])
        out.setdefault(visits[i], [])
        if ent not in out[visits[i]]:
            out[visits[i]].append(ent)
    return out


def shared_sites(idx) -> dict:
    """``{n: [(sid, tag, ip)]}``: every ``RunSharedScript(n)`` of a script, in every function -- who runs shared entry
    n (a shared entry is never instanced: it runs only where a caller runs it)."""
    out: dict = {}
    for e in idx.eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ip, _rel, t in A.O2Segment._items(idx, e.index, f.tag):
                m = re.match(r"RunSharedScript\((\d+)\)", t)
                if m:
                    out.setdefault(int(m.group(1)), []).append((e.index, f.tag, ip))
    return out


#: O5-CENSUS's classes in the order the detail prints them (no ladder: O5 has no SC rung) ...
CENSUS_LISTS = ("writes", "chain", "masked", "start_first", "error_path", "forbidden_sites", "dead", "inert")
#: ... and in the order a site is read against them -- O4's precedence (an inert FUNCTION never runs, so its sites
#: count inert before the noise mask; a masked site counts masked, 153's start_first too).
CENSUS_PRECEDENCE = C4.CENSUS_PRECEDENCE
CENSUS_REGISTERED = C4.CENSUS_REGISTERED


def store_census(fields, stock, pred: dict, *, sites=None, classify=None) -> tuple:
    """O5-CENSUS's reader (research/o5_design.md 6.1): ``(problems, {field: Counter(class)}, proof)`` -- O4's census
    (every gEventGlobal store site of each stock field registered, masked, start_first or in an ``inert`` FUNCTION; an
    unresolved store classified by its lvalue token; a function that does not decode FAILS; a registered key inside an
    inert function FAILS by name) with THE INERT PROOF PER ENTRANCE: every instancing op of the field in e0 t0
    (o4_castle.instancing_sites), and NO entrance the route enters the field by (:func:`visit_entrances`: 153 at 325 AND
    316, 154 at 304) instances an inert entry (o4_castle.instanced_at). A SHARED inert entry (``shared_by``) needs, besides,
    that every ``RunSharedScript(n)`` of the field lies in a function of an inert entry, and that its callers are exactly
    ``shared_by`` (:func:`shared_sites`). ``proof``: ``{field: {"entrances", "instanced", "outside_e0", "shared"}}``."""
    sites = sites or P.store_sites
    classify = classify or P.lvalue_class
    reg: dict = {}
    for name in ("writes", "ladder", "chain", "start_first", "error_path", "forbidden_sites", "dead"):
        for k in ([pred[name]] if name == "start_first" else pred.get(name) or ()):
            reg.setdefault((k["donor"], k["sid"], k["tag"], k["ip"], k["target"]), set()).add(name)
    inert, shared = {}, {}
    for x in pred.get("inert") or ():
        inert.setdefault(int(x["donor"]), {})[int(x["sid"])] = x.get("tags", "*")
        if x.get("shared_by") is not None:
            shared.setdefault(int(x["donor"]), {})[int(x["sid"])] = sorted(int(s) for s in x["shared_by"])
    try:
        ents = visit_entrances(pred)
    except ValueError as err:
        return [str(err)], {}, {}
    bad, counts, proof = [], {}, {}
    for fid in fields:
        idx = stock(fid)
        c = counts.setdefault(fid, Counter())
        if idx is None:
            bad.append(f"{fid}: no stock script")
            continue
        if fid in inert:
            route_ents = list(ents.get(fid) or ())
            outside = [s for s in C4.instancing_sites(idx) if (s[0], s[1]) != (0, 0)]
            per = {}
            for ent in route_ents:
                try:
                    per[ent] = C4.instanced_at(idx, ent)
                except ValueError as err:
                    per[ent] = None
                    bad.append(f"{fid} at {ent}: {err}")
            callers = shared_sites(idx)
            proof[fid] = {"entrances": route_ents, "instanced": {ent: sorted(v or ()) for ent, v in per.items()},
                          "outside_e0": outside,
                          "shared": {sid: callers.get(sid, []) for sid in sorted(shared.get(fid) or ())}}
            for s in outside:
                bad.append(f"{fid} e{s[0]} t{s[1]} ip{s[2]}: an instancing op outside Main_Init (Init{s[3].title()}"
                           f"({s[4]})): the inert proof needs every one in e0 t0")
            if not route_ents:
                bad.append(f"{fid}: no entrance the route enters it by: the inert proof cannot run")
            for sid in sorted(inert[fid]):
                for ent, inst in per.items():
                    if inst is not None and any(n == sid for _kind, n in inst):
                        bad.append(f"inert entry {sid} of {fid} is instanced at entrance {ent} "
                                   f"({sorted(k for k, n in inst if n == sid)}): the proof fails")
            for sid, by in sorted((shared.get(fid) or {}).items()):
                runs = callers.get(sid, [])
                stray = [r for r in runs if r[0] not in inert[fid]]
                for e, t, ip in stray:
                    bad.append(f"{fid} e{sid}: shared, run by RunSharedScript({sid}) at e{e} t{t} ip{ip} -- a function "
                               f"of no inert entry: the shared proof fails")
                if sorted({r[0] for r in runs}) != by:
                    bad.append(f"{fid} e{sid}: registered shared_by {by}, but its callers are "
                               f"{sorted({r[0] for r in runs})}: the shared proof fails")
        found, undecoded = sites(idx)
        bad += [f"{fid} {u}: does not decode" for u in undecoded]
        for s in found:
            where = f"{fid} e{s['sid']} t{s['tag']} ip{s['ip']}"
            if s["kind"] == "unknown":
                if classify(s.get("token")) is None:
                    bad.append(f"{where}: an unresolved store (lvalue {s.get('token')!r}: {s.get('why')}) no class "
                               f"covers")
                else:
                    c["unresolved"] += 1
                continue
            names = reg.get((fid, s["sid"], s["tag"], s["ip"], s["target"]), set())
            if T.noise_regions(P._site_row(s["target"])):
                names = names | {"masked"}
            tags = (inert.get(fid) or {}).get(s["sid"])
            if tags is not None and (tags == "*" or s["tag"] in tags):
                clash = sorted(names & set(CENSUS_REGISTERED))
                if clash:
                    bad.append(f"{where} {s['target']}: registered in {clash} AND in inert function e{s['sid']}: the "
                               f"key says it runs, the census says it never does")
                    continue
                names = names | {"inert"}
            cls = next((n for n in CENSUS_PRECEDENCE if n in names), None)
            if cls is None:
                bad.append(f"{where} {s['target']}: in no list ({s.get('text', '')[:60]})")
            else:
                c[cls] += 1
    return bad, counts, proof


def regions_problems(pred: dict, stock) -> tuple:
    """O5-REGIONS's reader (research/o5_design.md 6.1; 0.2 #11): ``(problems, roles Counter, gateway entries,
    hot-spots)``. Every frozen region's points are the first SetRegion of its (donor, entry); its role holds by
    o4_castle.instanced_at at the route's entrances (:func:`visit_entrances`) -- ``exit``: scan_gateways has its (to,
    entrance, face_gate) AND some route entrance of its place instances it; ``scene``: some route entrance instances it,
    its tag 2 holds ``DisableMove()`` after the ``Map.Byte[24] const(<stage>) B_EQ`` test, and its entry holds no
    gEventGlobal store, no Field() and no ExitField(); ``dormant``: no route entrance of its place instances it, and its
    ``entrances`` are exactly the place's route entrances. Then completeness: every gateway entry of a route place
    (scan_gateways) and every region a route entrance instances is registered (any role); no hot-spot."""
    from ff9mapkit.eventscan import FIELD_OP, scan_gateways
    try:
        ents = visit_entrances(pred)
    except ValueError as err:
        return [str(err)], Counter(), 0, 0
    regions = pred.get("regions") or {}
    bad, roles = [], Counter()
    cache: dict = {}

    def inst(donor, ent):
        if (donor, ent) not in cache:
            try:
                cache[(donor, ent)] = C4.instanced_at(stock(donor), ent)
            except ValueError as err:
                bad.append(f"{donor} at {ent}: {err}")
                cache[(donor, ent)] = set()
        return cache[(donor, ent)]
    gws: dict = {}
    for key, reg in sorted(regions.items()):
        donor, e = int(key.split(".")[0]), int(key.split(".e")[1])
        idx = stock(donor)
        if idx is None:
            bad.append(f"{key}: no stock script for {donor}")
            continue
        pts = A.O2Segment._first_region(idx, e)
        if pts != reg["points"]:
            bad.append(f"{key}: the bytes' first SetRegion is {pts}, frozen {reg['points']}")
        role = reg.get("role")
        roles[role] += 1
        route_ents = list(ents.get(donor) or ())
        at = [ent for ent in route_ents if ("region", e) in inst(donor, ent)]
        if role == "exit":
            rows = gws.setdefault(donor, scan_gateways(idx.data))
            hit = [g for g in rows if g["entry"] == e]
            if not any(g["to"] == reg["to"] and g["entrance"] == reg["entrance"]
                       and g["face_gate"] == reg.get("face_gate") for g in hit):
                bad.append(f"{key}: scan_gateways gives {[(g['to'], g['entrance'], g['face_gate']) for g in hit]}, "
                           f"frozen ({reg['to']}, {reg['entrance']}, {reg.get('face_gate')})")
            if not at:
                bad.append(f"{key}: an exit no route entrance of {donor} ({route_ents}) instances")
        elif role == "scene":
            if not at:
                bad.append(f"{key}: a scene no route entrance of {donor} ({route_ents}) instances")
            texts = [t for _ip, _rel, t in A.O2Segment._items(idx, e, 2)]
            test = f"SET({{Map.Byte[24] const({reg.get('stage')}) B_EQ B_EXPR_END}})"
            si = next((i for i, t in enumerate(texts) if t == test), None)
            di = None if si is None else next((i for i, t in enumerate(texts) if i > si and t.startswith("DisableMove")),
                                              None)
            if si is None or di is None:
                bad.append(f"{key}: its tag 2 holds no DisableMove() after {test!r}")
            ent_ = idx.eb.entries[e]
            for f in ent_.funcs:
                for ins in idx.eb.instrs(f):
                    if ins.op == FIELD_OP or any(s[0] == "global" for s in T.instruction_stores(idx.data, ins)):
                        bad.append(f"{key}: e{e} t{f.tag} stores to gEventGlobal or warps (+{ins.off - f.abs_start})")
                if any(t.startswith("ExitField") for _ip, _rel, t in A.O2Segment._items(idx, e, f.tag)):
                    bad.append(f"{key}: e{e} t{f.tag} holds ExitField()")
        elif role == "dormant":
            if sorted(int(x) for x in reg.get("entrances") or ()) != sorted(route_ents):
                bad.append(f"{key}: its entrances {reg.get('entrances')} are not the route's entrances of {donor} "
                           f"{route_ents}")
            if at:
                bad.append(f"{key}: dormant, but instanced at route entrance(s) {at}")
        else:
            bad.append(f"{key}: role {role!r} is not one of exit, scene, dormant")
    ngw = nhot = 0
    for donor in pred["route"]:
        idx = stock(donor)
        if idx is None:
            bad.append(f"{donor}: no stock script")
            continue
        rows = gws.setdefault(donor, scan_gateways(idx.data))
        entries = sorted({g["entry"] for g in rows})
        ngw += len(entries)
        for e in entries:
            if f"{donor}.e{e}" not in regions:
                bad.append(f"{donor}.e{e}: a gateway (-> {[g['to'] for g in rows if g['entry'] == e]}) in the bytes, "
                           f"not registered")
        for ent in ents.get(donor) or ():
            for kind, n in sorted(inst(donor, ent)):
                if kind == "region" and f"{donor}.e{n}" not in regions:
                    bad.append(f"{donor}.e{n}: a region entrance {ent} instances, not registered")
        hs = A.O2Segment.hotspot_census(idx)
        nhot += len(hs)
        for sid, h in sorted(hs.items()):
            bad.append(f"hot-spot {donor} e{sid} ({h['x']}, {h['z']}): in the bytes; O5 registers none")
    return bad, roles, ngw, nhot


# ======================================================================== the stair: the contour and the evidence (pure)
def _tri_height(wv, tri, x: float, z: float) -> float:
    """The PSX height (world y) of a triangle's plane at (``x``, ``z``): barycentric over its three world verts."""
    a, b, c = (wv[k] for k in tri.vtx)
    den = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
    if den == 0:
        return float(a[1])
    wa = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / den
    wb = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / den
    return wa * a[1] + wb * b[1] + (1 - wa - wb) * c[1]


def contour_on_route(wm, pts: list, contour_y: float, *, every: float = 5.0) -> dict | None:
    """O5-GOALS (c)'s reading: the route ``pts`` (``[(x, z)]``, its start first) sampled every ``every`` u on the open
    floor ``wm`` (a PlayerWalkmesh: the first OPEN triangle under each point, its interpolated height) -- the FIRST
    sample at PSX y <= ``contour_y``: ``{"x", "z", "tri", "y", "leg", "into", "along", "length"}``, or None (the route
    never stands that high)."""
    raw = wm.mesh
    wv = raw.world_verts()
    length = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    along = 0.0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        seg = math.dist(a, b)
        n = max(1, int(seg // every))
        for k in range(n + 1):
            x, z = a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n
            tis = [ti for ti in raw.tris_at(x, z) if ti not in wm.closed]
            if not tis:
                continue
            y = _tri_height(wv, raw.tris[tis[0]], x, z)
            if y <= contour_y:
                return {"x": round(x, 1), "z": round(z, 1), "tri": tis[0], "y": round(y, 1), "leg": i + 1,
                        "into": round(seg * k / n, 1), "along": round(along + seg * k / n, 1), "length": round(length)}
        along += seg
    return None


def contour_crossings(wm, start, contour_y: float) -> tuple:
    """O5-GOALS (d)'s reading (0.2 #22): ``(crossings, component)`` -- on the start's OPEN component (every open
    triangle of ``wm`` linked to the one under ``start`` through open neighbours: the script-closed triangles and the
    mask's door strips shut), every point where an open triangle's EDGE crosses PSX y ``contour_y`` and every vertex
    lying exactly on it, ``[(tri, x, z)]``. Heights are continuous across shared edges, so a walk first stands at y <=
    contour_y ON one of them; a triangle's y <= contour_y part is a convex polygon whose extreme x lies at one of its
    vertices or edge crossings, so these points are the complete sample too (the vertex-and-centroid rule was not)."""
    raw = wm.mesh
    wv = raw.world_verts()
    todo = [ti for ti in raw.tris_at(*start) if ti not in wm.closed]
    comp: set = set()
    while todo:
        t = todo.pop()
        if t in comp:
            continue
        comp.add(t)
        for nb in raw.tris[t].nbr:
            if 0 <= nb < len(raw.tris) and nb not in wm.closed and nb not in comp:
                todo.append(nb)
    out = []
    for ti in sorted(comp):
        vs = [wv[k] for k in raw.tris[ti].vtx]
        for i, j in ((0, 1), (1, 2), (2, 0)):
            a, b = vs[i], vs[j]
            if (a[1] - contour_y) * (b[1] - contour_y) < 0:
                s = (contour_y - a[1]) / (b[1] - a[1])
                out.append((ti, round(a[0] + s * (b[0] - a[0]), 1), round(a[2] + s * (b[2] - a[2]), 1)))
        for v in vs:
            if v[1] == contour_y:
                out.append((ti, float(v[0]), float(v[2])))
    return out, sorted(comp)


def goals_extra(pred: dict, walkmesh=None) -> tuple:
    """O5-GOALS (c) and (d) (research/o5_design.md 6.1; 0.2 #21-#22), for the table's WALK step (``walk.name``):
    ``(problems, lines)``. (c) THE CONTOUR ON THE ROUTE: the planner's route (route_avoiding on the step's floor -- its
    closed triangles shut -- round its ``avoid``, from its ``start`` to its goal; at the step's ``clearance`` when it
    carries F15's) sampled every 5 u (:func:`contour_on_route`) reaches PSX y <= ``walk.contour_y`` before its end, at a
    point its ``until`` holds; (d) THE EVIDENCE'S SOUNDNESS, ON THE CONTOUR: every point of the start's open component
    where an edge crosses the contour, and every vertex on it (:func:`contour_crossings`), satisfies ``until`` -- so the
    first point a walk stands at y <= contour_y does -- and every registered ``scene`` and ``exit`` region of the place
    lies wholly outside ``until`` (no vertex of its quad satisfies it: ``until`` is one half-plane, x <= -1100), so a loss
    satisfying ``until`` is the stair's and nothing else's. ``walkmesh(donor)`` is the raw mesh (default the install's)."""
    from ff9mapkit import extract
    from ff9mapkit.content import pathfind
    walkmesh = walkmesh or extract.stock_walkmesh
    walk = pred.get("walk") or {}
    cy = float(walk.get("contour_y", CONTOUR_Y))
    bad, lines, found = [], [], 0
    for c in pred.get("table") or ():
        for i, s0 in enumerate(c["steps"]):
            if s0.get("name") != walk.get("name"):
                continue
            found += 1
            lab = f"({c['donor']}, {c['sc']}) #{i + 1} {walk.get('name')!r}"
            try:
                s = SD.step_of(pred, s0)
            except ValueError as err:
                bad.append(f"{lab}: {err}")
                continue
            if s.get("until") is None or s.get("start") is None:
                bad.append(f"{lab}: the walk's evidence needs an until and a start")
                continue
            raw = walkmesh(c["donor"])
            wm = pathfind.PlayerWalkmesh(raw, closed=SD.closed_tris(pred, s, raw))
            start = tuple(float(v) for v in s["start"])
            goal = tuple(float(v) for v in s["goal"])
            kw = {} if s.get("clearance") is None else {"clearance": float(s["clearance"])}
            route = pathfind.route_avoiding(wm, start, goal, SD.polys(pred, s.get("avoid")), leave_wall=True, **kw)
            if route is None:
                bad.append(f"{lab} (c): no route from {start} to {goal} avoiding {s.get('avoid')}")
            else:
                pts = [start] + [tuple(float(v) for v in p) for p in route]
                first = contour_on_route(wm, pts, cy)
                if first is None:
                    bad.append(f"{lab} (c): the route ({len(route)} legs) never stands at PSX y <= {cy:g}")
                elif not SD.until_ok(s["until"], first["x"], first["z"]):
                    bad.append(f"{lab} (c): the route first stands at PSX y <= {cy:g} at ({first['x']:.0f}, "
                               f"{first['z']:.0f}), tri {first['tri']}, where its until {s['until']} is false")
                else:
                    lines.append(f"(c) the contour crossed at ({first['x']:.0f}, {first['z']:.0f}) (tri {first['tri']}, "
                                 f"y {first['y']:.0f}), {first['into']:.0f} u into leg {first['leg']} of {len(route)}, "
                                 f"{first['along']:.0f} of {first['length']} u"
                                 + (f" (clearance {kw['clearance']:g})" if kw else ""))
            crossings, comp = contour_crossings(wm, start, cy)
            off = [p for p in crossings if not SD.until_ok(s["until"], p[1], p[2])]
            if not crossings:
                bad.append(f"{lab} (d): no edge of the start's open component ({len(comp)} tris) crosses PSX y {cy:g}")
            elif off:
                bad.append(f"{lab} (d): the contour PSX y {cy:g} is crossed where until {s['until']} is false: "
                           + ", ".join(f"tri {t} ({x:.0f}, {z:.0f})" for t, x, z in off[:4]))
            else:
                xs = [x for _t, x, _z in crossings]
                lines.append(f"(d) the evidence sound ON THE CONTOUR: tris "
                             + " and ".join(str(t) for t in sorted({t for t, _x, _z in crossings}))
                             + f", x {min(xs):.0f}..{max(xs):.0f} (the start's open component, {len(comp)} tris)")
            regs = [(k, r) for k, r in (pred.get("regions") or {}).items()
                    if str(k).split(".", 1)[0] == str(c["donor"]) and r.get("role") in ("scene", "exit")]
            inside = [k for k, r in regs if any(SD.until_ok(s["until"], px, pz) for px, pz in r["points"])]
            if inside:
                bad.append(f"{lab} (d): the registered scene/exit region(s) {inside} reach where until {s['until']} "
                           f"holds: a loss there would read as the stair's")
            else:
                lines.append(f"every scene and exit region of {c['donor']} ({', '.join(sorted(k for k, _r in regs))}) "
                             f"wholly outside until {s['until']}")
    if not found:
        bad.append(f"no table step is the walk {walk.get('name')!r}")
    return bad, lines


# ======================================================================== O5-PATTERN's reading (pure)
def stock_join(stock, members: dict):
    """``join(row) -> function offset | None``: a script row joined on its PLACE's stock bytes (``ScriptIndex.join``:
    a member's bytes are its donor's but for its Field() operands, so the donor's offsets are its own)."""
    def join(x):
        idx = stock(place(x.fld, members))
        if idx is None:
            return None
        try:
            j = idx.join(x)
        except ValueError:
            return None
        return j.rel if j.status == "store" else None
    return join


def pattern_of(rows: list, pred: dict, members: dict, join) -> dict:
    """O5-PATTERN's reading of one run (research/o5_design.md 4.16, 5.3): over the SCRIPT's rows (``src`` "eb", no
    addition buffer) of the route places before the cut (``rows``: the kept rows) that JOIN (``join(row)`` -> the
    function offset; a row that does not join is JOIN's, counted in ``unjoined``), masked rows in: ``visits`` -- the
    field-mode ``w`` rows split into visits (maximal runs of one place), each ``(place, sid, tag, off, target, new,
    same)`` in order -- and ``counts`` -- the ``c`` rows as a sorted multiset ``(place, sid, tag, off, target, n,
    last)``."""
    route = set((pred.get("landing") or {}).get("route_places") or pred["route"])
    visits, counts, unjoined = [], [], 0
    for x in rows:
        if x.k not in ("w", "c") or x.src != "eb" or x.add or place(x.fld, members) not in route:
            continue
        off = join(x)
        if off is None:
            unjoined += 1
            continue
        p = place(x.fld, members)
        if x.k == "c":
            counts.append((p, x.sid, x.tag, off, x.target, x.n, x.last))
            continue
        if x.m != T.FIELD_MODE:
            continue
        t = (p, x.sid, x.tag, off, x.target, x.new, x.same)
        if visits and visits[-1][-1][0] == p:
            visits[-1].append(t)
        else:
            visits.append([t])
    return {"visits": visits, "counts": sorted(counts), "unjoined": unjoined}


def _tuples(xs) -> list:
    return [tuple(x) for x in xs or ()]


def pattern_diff(got: dict, pat: dict) -> list:
    """O5-PATTERN's verdict on one run's :func:`pattern_of` against the frozen ``pattern``, pure: ``[problem]`` -- (a)
    the ``c`` multiset first (a count missing, extra or with another n or last), then (b) each visit's sequence (a
    visit more or fewer, or the first differing tuple of the first differing visit)."""
    bad = []
    want_c = Counter(_tuples(pat.get("counts")))
    got_c = Counter(got["counts"])
    if got_c != want_c:
        miss, extra = sorted((want_c - got_c).elements()), sorted((got_c - want_c).elements())
        bad.append("(a) the c rows differ: " + "; ".join(x for x in (
            f"missing {miss[:2]}" if miss else "", f"extra {extra[:2]}" if extra else "") if x))
    want_v = [_tuples(v) for v in pat.get("visits") or ()]
    got_v = got["visits"]
    if got_v != want_v:
        if len(got_v) != len(want_v):
            bad.append(f"(b) {len(got_v)} visit(s) of emitted rows, want {len(want_v)}: "
                       + " / ".join(f"{v[0][0]}x{len(v)}" for v in got_v))
        else:
            i = next(i for i, (a, b) in enumerate(zip(got_v, want_v)) if a != b)
            a, b = got_v[i], want_v[i]
            j = next((j for j, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
            bad.append(f"(b) visit {i + 1}'s emitted rows differ at #{j + 1}: got {a[j] if j < len(a) else 'nothing'}, "
                       f"want {b[j] if j < len(b) else 'nothing'} ({len(a)} vs {len(b)} rows)")
    return bad


# ======================================================================== a trace, summarised (end PLACES)
def trace_summary(rows: list, pred: dict, *, side: str = "S", start_place: int | None = None, end_fields=None,
                  stock=None, scripts=None, log: list | None = None) -> dict:
    """One trace, summarised for a reader (research/o5_design.md 7.2; the rehearsal report and the dry run): cut at its
    start row and at its first row in an END PLACE -- ``end_fields`` (a stage's raw ids, default the side's) turned
    into places through the members on F (O4's lesson, the claim critique #14 there). Then the SC and FieldEntrance
    rows, every registered key present or absent, every UNREGISTERED key, the two crossings (153 ip3150 -> the next
    field row, 154 ip1520 -> the next), the emitted rows per visit and the ``c`` rows (:func:`pattern_of`), visit 3's
    first emitted row, the end cut's raw row, the residue before and after the start, the masked counts, the join
    failures, and -- given the run's driver ``log`` -- its forbidden hits with their backing."""
    members = members_of(pred) if side == "F" else {}
    sp = start_place if start_place is not None else place(pred["start"][side], members)
    ends = list(end_fields) if end_fields is not None else ST.side_ends(pred, side)
    places = sorted({place(f, members) for f in ends})
    kept, at, pre = cut_at_start(rows, sp, members)
    kept, end = cut_at_end(kept, places, members)
    stock = stock or T.stock_script_source()
    d = T.digest("summary", kept, scripts=scripts or stock, donor_scripts=stock, members=members or None)
    rk = row_keys(d)

    def seq(span) -> list:
        out = []
        for x in A.span_rows(kept, span):
            k = key_of(rk, x)
            out.append({"line": x.line, "f": x.f, "fld": x.fld, "site": f"e{x.sid} t{x.tag} ip{x.ip}",
                        "target": x.target, "old": x.old, "new": x.new, "key": None if k is None else A._fmt_key(k)})
        return out
    registered, reg = {}, set()
    for name in ("chain", "writes", "error_path", "forbidden_sites", "dead"):
        for k in pred.get(name) or ():
            wk = wkey(k)
            reg.add(wk)
            registered.setdefault(name, []).append({"what": A.label(k), "present": wk in d.keys or wk in d.seam_keys})
    lnd = pred.get("landing") or {}
    crossings = {}
    for name in ("exit153", "exit154"):
        ex = lnd.get(name)
        if not ex:
            continue
        i = next((j for j, x in enumerate(kept) if x.k == "w" and x.m == T.FIELD_MODE
                  and place(x.fld, members) == ex["place"]
                  and (x.sid, x.tag, x.ip, x.target, x.new) == (ex["sid"], ex["tag"], ex["ip"], ex["target"],
                                                                ex["value"])), None)
        if i is not None:
            nxt = next((x for x in kept[i + 1:] if x.k == "w" and x.m == T.FIELD_MODE), None)
            crossings[name] = {"exit": A._row_text(kept[i]), "next": None if nxt is None else A._row_text(nxt)}
    pat = pattern_of(kept, pred, members, stock_join(stock, members))
    v3 = pat["visits"][2][0] if len(pat["visits"]) > 2 else None
    cut_row = next((x for x in rows if x.line == end), None) if end is not None else None
    hits = []
    if log is not None:
        for h in SD.forbidden_hits(kept, pred, members, sp, end_fields=ends):
            bk = SD.backing(h, log, pred)
            hits.append({"row": SD._hit_row(h), "why": h["why"], "cause": h["cause"], "backed": bk is not None,
                         "by": None if bk is None else bk["what"]})
    keys = sorted(d.keys, key=T.WriteKey.sort_key)
    return {"start": at, "end": end, "end_places": places, "rows": len(kept),
            "residue_before": [[x.fld, x.byte, x.old, x.new] for x in pre if x.k == "r"],
            "pre_other": [A._row_text(x) for x in pre if x.k == "w"],
            "residue_after": [[x.fld, x.byte, x.old, x.new, bool(T.noise_regions(x))] for x in kept if x.k == "r"],
            "sc": seq(pred.get("sc_bytes") or (0, 1)), "entrance": seq(pred.get("entrance_bytes") or (2, 3)),
            "registered": registered, "crossings": crossings,
            "pattern": {"visits": [[list(t) for t in v] for v in pat["visits"]],
                        "counts": [list(t) for t in pat["counts"]], "unjoined": pat["unjoined"]},
            "visit3_first": None if v3 is None else list(v3),
            "unregistered": [A._fmt_key(k) for k in keys if k not in reg and not is_noise(k, pred)],
            "end_row": None if cut_row is None else (f"{cut_row.k} " + (A._row_text(cut_row) if cut_row.k == "w"
                                                                       else f"{cut_row.fld} byte {cut_row.byte}")),
            "end_row_fld": None if cut_row is None else cut_row.fld,
            "seam_keys": [A._fmt_key(k) for k in sorted(d.seam_keys, key=T.WriteKey.sort_key)],
            "masked": dict(d.masked), "residue_masked": d.residue_masked,
            "failures": [[A._row_text(r), why[:160]] for r, why in d.failures], "forbidden": hits}


# ======================================================================== the run's own rows
def _rows(log, k: str, **match) -> list:
    return [r for r in log or () if r.get("k") == k and all(r.get(a) == b for a, b in match.items())]


def walk_rows(log: list, pred: dict) -> list:
    """The stair step's ``step`` rows of a run's driver log (``walk.name``, ``walk.donor``, ``walk.visit``), in order."""
    w = pred.get("walk") or {}
    return [r for r in log or () if r.get("k") == "step" and r.get("name") == w.get("name")
            and r.get("donor") == w.get("donor") and r.get("visit") == w.get("visit")]


def walk_windows(steps: list) -> list:
    """WALK (b)'s windows (research/o5_design.md 5.3; the driver critique #3), from the stair step's rows in order:
    each attempt's ``[frame0, its end]`` -- the end ``lost.frame`` for "done" and "interrupted", the step row's own
    ``frame`` for "failed" (it carries no ``lost``) -- and each gap from an attempt's end to the next attempt's
    ``frame0`` (a side scene and its re-grant; a failed walk's standing wait). ``[(lo, hi, what)]``; an end it cannot
    read is the row's ``frame``."""
    out, prev = [], None
    for s in steps:
        lo = s.get("frame0")
        lost = s.get("lost") or {}
        hi = s.get("frame") if s.get("outcome") == "failed" or lost.get("frame") is None else lost["frame"]
        if prev is not None and lo is not None:
            out.append((prev, lo, "between attempts"))
        if lo is not None and hi is not None:
            out.append((lo, hi, f"attempt {s.get('attempt')} ({s.get('outcome')})"))
        prev = hi
    return out


def choice_rows(log: list, pred: dict) -> list:
    """The ``choice`` rows of the guarded rule (``choice.rule``: the rule whose ``match`` it is)."""
    n = next((i for i, r in enumerate(pred.get("choices") or ()) if r.get("match") == (pred.get("choice") or {})
              .get("rule")), None)
    return [r for r in log or () if r.get("k") == "choice" and n is not None and r.get("rule") == n]


def guard_derived(row: dict) -> list:
    """CHOICE (d)'s re-derivation (research/o5_design.md 5.3), pure: :func:`segment_drive.guard_strays` over the
    ``guard`` row's own ``presses`` -- each placed by its accepted frame, else its decision frame (fail-closed) -- in
    [``marker_last``, ``choice_close``), excluding the answer's seq span and ``closing_seq``
    (:func:`segment_drive.guard_exclude`)."""
    log = [{"k": "press", "seq": p.get("seq"), "why": p.get("why"), "pre": {"frame": p.get("decision_frame")}}
           for p in row.get("presses") or ()]
    events = [{"kind": "accepted", "seq": p["seq"], "frame": p["accepted_frame"]} for p in row.get("presses") or ()
              if p.get("accepted_frame") is not None]
    return SD.guard_strays(log, events, [], row.get("marker_last"), row.get("choice_close"),
                           exclude=SD.guard_exclude(row.get("answer"), row.get("closing_seq")))


# ======================================================================== O5 on the shared engine
class O5Segment(C4.O4Segment):
    """O5 on O4's segment (research/o5_design.md 1.3): its constants and check texts, the draft predictions, the
    offline checks (O5-BUILD with the route members' pins, O5-KEYS with the route pins and route_mes, O5-TEXT strict on
    block 3, O5-CENSUS per entrance with the shared-entry proof, O5-REGIONS, O5-GOALS with the contour), the preflight
    extras (P-TEXT3, P-RECOVERY, P-DONOR, P-SETTINGS, P-PAD, P-OVERRIDE, P-ENGINE; no P-GATE, no P-TEXT2) and in-game
    capabilities (P-CAP, P-OBJECTS, P-LANG, P-DONOR-LOG and P-LAUNCH over 151/153/154, P-PAD), the drive with its input
    witness (O4's), A-START scoped to visit 1, the all-run checks (FORBIDDEN, VOID-ASYM (a)-(d) over [place, sc, visit]
    cells), the core checks (START, NO-SC, CHAIN, RESIDUE, WRITES exact, NULL, STABLE, LANDING (a)-(e), CHOICE (a)-(d),
    WALK (a)-(b), PATTERN (a)-(b), MASKED, STATE, JOIN) and O5's report. The session loop, the cuts, the digest, the
    comparison and the verdict are the shared engine's."""

    tag = "O5"
    doc = _MODULE_DOC
    predictions = PREDICTIONS
    manifest = MANIFEST
    session_file = SESSION_FILE
    report_file = REPORT_FILE
    chain_dir = CHAIN_DIR
    build_dir = BUILD_DIR
    accept_us_build = False               # O4's build: every member's other languages are its own donor's
    recovery = 4600
    end_session_warps = True              # S5: a last run stopped mid-walk must not leave the game there
    core_ids = ("START", "NO-SC", "CHAIN", "RESIDUE", "WRITES", "NULL", "STABLE", "LANDING", "CHOICE", "WALK",
                "PATTERN", "MASKED", "STATE", "JOIN")
    titles = {
        "P-CAP": "P-CAP: the engine advertises the story trace at proto 1",
        "P-OBJECTS": "P-OBJECTS: the engine publishes the field's objects (s89): the walk's npcs plans round Blank, the "
                     "floor's one body; e9/e11/e31 publish walk-through",
        "P-LANG": "P-LANG: the running game's text is English(US), the language the keys, joins and text were checked "
                  "in (a US session)",
        "P-DONOR-LOG": "P-DONOR-LOG: this launch's Memoria.log shows the patchers ran and logged no ForkDonorPatch "
                       "collision for 151, 153 or 154",
        "P-LAUNCH": "P-LAUNCH: every stacked patch file, Memoria.ini and the engine DLLs are older than this launch, "
                    "and the DLLs are the pinned engine",
        "P-MANIFEST": "P-MANIFEST: the frozen members are the deployed chain's (o5_forks.json: O4's, deployed)",
        "P-DEPLOY": "P-DEPLOY: every member registered once under its name, and mapped once to its donor",
        "P-EB": "P-EB: every member's live .eb (7 languages) is the offline-checked build's (O4's)",
        "P-FLOOR": "P-FLOOR: every member's deployed walkmesh is its donor's (member(153)'s is the stair walk's floor)",
        "P-STOCK": "P-STOCK: no mod folder overrides stock 151, 153 or 154",
        "P-TEXT3": "P-TEXT (block 3): every mod folder's text block 3 is each language's stock asset (strict)",
        "P-RECOVERY": "P-RECOVERY: the recovery field 4600 is registered in a mod folder",
        "P-DONOR": "P-DONOR: each of 151, 153 and 154 is forked by exactly one ForkDonorPatch row in the stack, its "
                   "member's",
        "P-SETTINGS": "P-SETTINGS: the battle, cheat, hack, control and graphics settings are the frozen ones (O4's; "
                      "Memoria.ini read the engine's way)",
        "P-PAD": "P-PAD: no XInput pad reads non-neutral (AlwaysCaptureGamepad = 1 reads a pad even unfocused)",
        "P-OVERRIDE": "P-OVERRIDE: field 70's New-Game override is the pinned one, shipped by one folder",
        "P-ENGINE": "P-ENGINE: the live x64 and x86 Assembly-CSharp.dll are the pinned engine",
        "BUILD": "O5-BUILD: every member's .eb, in all 7 languages, is its donor's in that language with only in-chain "
                 "Field() literals remapped; per language, the route members (153, 154, 151) differ from their donors "
                 "in exactly their in-chain Field() operands",
        "KEYS": "O5-KEYS: every registered key -- chain, writes, error path, forbidden and dead sites, start_first -- is "
                "a store of its variable at its ip in the donor's stock bytes, its op in the statement, its value "
                "computed (the choice's :=var key in its statement); the 53 route pins and route_mes as pinned",
        "TEXT": "O5-TEXT: the build's text block 3 is each language's stock asset, read by its resource path -- STRICT: "
                "another language's copy fails",
        "CENSUS": "O5-CENSUS: every gEventGlobal store site of 153 and 154 is registered (writes, chain, masked, "
                  "start_first, error path, forbidden, dead) or lies in an inert function, proven not instanced at ANY "
                  "entrance the route enters its field by (a shared entry by its callers)",
        "REGIONS": "O5-REGIONS: every frozen region is the stock bytes' own, each role proven by instancing at the "
                   "route's entrances (an exit and a scene instanced, a dormant one not), every gateway and every "
                   "instanced region of 153 and 154 registered, no hot-spot",
        "GOALS": "O5-GOALS: the stair step runs on its floor from its start to its goal; the planned route crosses the "
                 "PSX y -450 contour on the until's side, and the evidence is sound ON THE CONTOUR",
        "FROZEN": "O5-FROZEN: the predictions are the file the session recorded, unchanged",
        "COVER": "O5-COVER: at least {min_covered} covered runs a side",
        "FORBIDDEN": "O5-FORBIDDEN: no run carries a forbidden write its own driver log does not explain",
        "VOID-ASYM": "O5-VOID-ASYM: no game-caused VOID class on one side only, no side VOID in one class in every run, "
                     "no run VOID in a finding class (V19), and no game-observed V17 cause on one side only -- every "
                     "cell [place, sc, visit]",
        "START": "O5-START: every covered run starts at 153's Main_Init after only the warp's four residue rows, and 153 "
                 "takes its ambient branch from the warp's Byte[13] 1",
        "NO-SC": "O5-NO-SC: no row touches bytes 0-1 (SC) after the start: SC holds 1190 throughout",
        "CHAIN": "O5-CHAIN: bytes 2-3 (FieldEntrance) carry exactly the chain, in order, each from the last",
        "RESIDUE": "O5-RESIDUE: no unmasked residue after the start beyond the registered",
        "WRITES": "O5-WRITES: every covered run's story keys are EXACTLY the registered writes and chain",
        "NULL": "O5-NULL: STOCK ONLY and FORK ONLY are empty",
        "STABLE": "O5-STABLE: no key is written in some runs of a side and not others",
        "LANDING": "O5-LANDING: every row ran in its place's own field, 154 loaded by 153's Field(154), 153 re-entered "
                   "by 154's Field(153) with its first EMITTED row, 153 the last place, the end cut 151's first row at "
                   "the side's own end field, and no fork run left its members",
        "CHOICE": "O5-CHOICE: the stored choice -- one ip1741 Bit[3795] 0 -> 1 and no count of it, the guarded rule "
                  "answered once with index 1 through a verified landing (selected_before 1), the game's own branch "
                  "page the pick's, the store after the answer, and no stray press in [127's last sample, 128's close)",
        "WALK": "O5-WALK: the stair walk -- one done step at the contour's side, at most one interruption and one "
                "failed attempt, none in a door -- wrote nothing (THE PAIRED-WALK LAW)",
        "PATTERN": "O5-PATTERN: the sink's emitted row pattern EXACTLY -- each visit's emitted rows in order and the "
                   "four counted stores of 153's revisit",
        "MASKED": "O5-MASKED: the story-noise regions written are the same on both sides",
        "STATE": "O5-STATE: the state handed to 151 is the same: each target's emitted write history in order (its "
                 "suppressed stores as a set), and the end state read live (Byte[8] aside: it races the read)",
        "JOIN": "O5-JOIN: every script row joins a store in the bytes its field ran",
        "THROW": "O5-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
    }

    def __init__(self):
        super().__init__()
        self._stock = None

    # -- the predictions --------------------------------------------------------------------------------------
    def draft(self) -> dict:
        return draft_predictions(Path(self.chain_dir) / "campaign.toml")

    def freeze(self, path=None, *, live_engine=None) -> str:
        """The freeze, once (research/o5_design.md 1.3, 7.3): before anything is written the draft must carry a
        ``guard`` its strict reader passes (a ``guard: null`` overlay is no guard) and a ``witness``; no table step may
        carry a rehearsal overlay (``walk_stop_x``); its ``side_ends`` pass :func:`segment_trace.side_ends_of`;
        ``battles`` is empty; ``rehearsals`` names the lead's runs; and its ``engine`` is the live DLLs' (``live_engine``,
        default the live install's). Then the base's: LF, sorted keys, never over an existing file."""
        pred = self.draft()
        bad = []
        try:
            if SD.guard_of(pred) is None:
                bad.append("no guard: O5's choice 128 is answered under the pre-choice guard (decision 3)")
        except ValueError as err:
            bad.append(str(err))
        try:
            if SD.witness_of(pred) is None:
                bad.append("no witness: Bit[3795] stores the player's answer (decision 4)")
        except ValueError as err:
            bad.append(str(err))
        for c in pred.get("table") or ():
            for s in c.get("steps") or ():
                over = sorted(set(s) & REHEARSAL_OVERLAYS)
                if over:
                    bad.append(f"the table step {s.get('name')!r} carries a rehearsal overlay {over}")
        try:
            if ST.side_ends_of(pred) is None:
                bad.append("no side_ends: O5's F side ends in member(151)")
        except ValueError as err:
            bad.append(str(err))
        if pred.get("battles"):
            bad.append(f"{len(pred['battles'])} battle row(s): O5's registry is empty (any battle is V10)")
        if not pred.get("rehearsals"):
            bad.append("no rehearsals: the freeze reads the lead's in-game rehearsal runs (7.3), none named")
        live = live_engine if live_engine is not None else C4.engine_shas(GAME)
        eng = pred.get("engine") or {}
        if any(eng.get(a) != live.get(a) for a in ("x64", "x86")):
            bad.append(f"the engine {str(eng.get('x64'))[:12]} is not the live DLLs' {str(live.get('x64'))[:12]}: the "
                       f"rehearsals ran another engine")
        if bad:
            raise SystemExit("!! the draft is not freezable: " + "; ".join(bad))
        return ST.Segment.freeze(self, path)

    # -- offline ------------------------------------------------------------------------------------------------
    def offline_extra(self, pred: dict, build=None) -> list:
        stock = self.stock_source()
        return [self.text_check(pred, build), self.census_check(pred, stock), self.regions_check(pred, stock),
                self.goals_check(pred)]

    def build_check(self, pred: dict, build=None, stock_lang=None) -> tuple:
        """O5-BUILD (6.1): the base rule (every member's .eb, every language its own donor's with only in-chain
        Field() literals remapped), then THE ROUTE MEMBERS' PINS per language (:meth:`build_pins`), then the chain's
        route members (derived)."""
        stock_lang = stock_lang or ST.stock_lang()
        ok, what, detail = ST.Segment.build_check(self, pred, build, stock_lang)
        pok, pdetail = self.build_pins(pred, build, stock_lang)
        if not (ok and pok):
            return False, what, "; ".join(d for good, d in ((ok, detail), (pok, pdetail)) if not good)
        members = members_of(pred)
        line = route_members_line(members) if all(d in members.values() for d in ROUTE_DONORS) else ""
        return True, what, f"{detail}; {pdetail}" + (f"; {line}" if line else "")

    def build_pins(self, pred: dict, build=None, stock_lang=None) -> tuple:
        """THE ROUTE MEMBERS' PINS (6.1), per language, each language's script decoded on its own: every byte in which a
        route member (``route_build.fields``: 153, 154, 151) differs from its donor lies in the operand of one of its
        in-chain ``Field()`` instructions -- exactly the registered sites (US ips; their literal a chain donor,
        retargeted to that donor's member) -- and every such operand differs: no other byte (a PreloadField operand, a
        Field() to a donor no member forks) moves. ``(ok, detail)``."""
        from ff9mapkit.config import LANGS, ModLayout
        from ff9mapkit.eb import EbScript
        from ff9mapkit.eventscan import FIELD_OP
        stock_lang = stock_lang or ST.stock_lang()
        spec = (pred.get("route_build") or {}).get("fields") or {}
        members, names = members_of(pred), {int(f): n for f, n in pred["names"].items()}
        retarget = {d: f for f, d in members.items()}
        lay = ModLayout(Path(build or self.build_dir))
        bad, n, nsites = [], 0, 0
        for donor_s, sites in sorted(spec.items(), key=lambda kv: int(kv[0])):
            donor = int(donor_s)
            fid = next((f for f, d in sorted(members.items()) if d == donor), None)
            if fid is None:
                bad.append(f"no member forks {donor}")
                continue
            want = sorted(tuple(int(v) for v in s) for s in sites)
            nsites += len(want)
            for L in LANGS:
                p = lay.eb_path(L, f"EVT_{names[fid]}.eb.bytes")
                src = stock_lang(donor, L)
                if src is None or not p.is_file():
                    bad.append(f"{fid} ({donor}) {L}: {'no stock donor' if src is None else 'no built file'}")
                    continue
                built = p.read_bytes()
                n += 1
                if len(built) != len(src):
                    bad.append(f"{fid} ({donor}) {L}: {len(built)} bytes, its donor {len(src)}: an ip shifted")
                    continue
                eb = EbScript.from_bytes(src)
                inchain, operand = [], set()
                for e in eb.entries:
                    if e.empty:
                        continue
                    for f in e.funcs:
                        for ins in eb.instrs(f):
                            if ins.op == FIELD_OP and ins.imm(0) in retarget:
                                inchain.append((e.index, f.tag, ins.off - e.abs_start, ins.imm(0)))
                                operand |= {ins.off + 2, ins.off + 3}
                                got = int.from_bytes(built[ins.off + 2:ins.off + 4], "little")
                                if got != retarget[ins.imm(0)] & 0xFFFF:
                                    bad.append(f"{fid} ({donor}) {L} e{e.index} t{f.tag} ip{ins.off - e.abs_start}: "
                                               f"Field({ins.imm(0)}) reads {got} in the build, not member "
                                               f"{retarget[ins.imm(0)]}")
                if sorted(inchain) != want:
                    bad.append(f"{fid} ({donor}) {L}: the in-chain Field() sites are {sorted(inchain)}, pinned {want}")
                diff = {i for i, (a, b) in enumerate(zip(built, src)) if a != b}
                if diff - operand:
                    bad.append(f"{fid} ({donor}) {L}: {len(diff - operand)} byte(s) differ outside the in-chain Field() "
                               f"operands, first at {min(diff - operand)}")
                if operand - diff:
                    bad.append(f"{fid} ({donor}) {L}: {len(operand - diff)} in-chain Field() operand byte(s) left "
                               f"unremapped, first at {min(operand - diff)}")
        nm = len(spec)
        return not bad, ("; ".join(bad[:6]) if bad else
                         f"the route members' pins hold in {n} member files ({nm} route members x {len(LANGS)} "
                         f"languages): the only byte diffs are their {nsites} in-chain Field() operands")

    def keys_check(self, pred: dict, stock, lists=None) -> tuple:
        """O5-KEYS (6.1): (a) O2's machinery on a filtered copy -- the chain, the writes but the choice's ``:=var`` key,
        ``forbidden_sites`` + ``error_path`` + ``dead``, ``start_first``; no ladder, noise or start-dependent key --
        then the ``:=var`` key itself (its joined store's statement ``<target> <rvalue> B_LET``: its value 1 rests on
        O5-CHOICE, never computed here) and ``start_music`` as exactly one writes key; (b) THE ROUTE PINS
        (:meth:`route_pins_check`). A ``:=var`` key names its ``rvalue``, read from the key, never assumed: a key without
        one FAILS."""
        var = [k for k in pred["writes"] if k.get("op") == ":=var"]
        filtered = {**pred, "writes": [k for k in pred["writes"] if k.get("op") != ":=var"], "ladder": [],
                    "start_dependent": [], "noise": [],
                    "forbidden_sites": list(pred["forbidden_sites"]) + list(pred["error_path"]) + list(pred["dead"])}
        ok, _what, detail = A.O2Segment.keys_check(self, filtered, stock)
        bad = [] if ok else [detail]
        for k in var:
            width, index = k["target"].split(".", 1)[1].rstrip("]").split("[")
            bit = int(index) if width in T.BIT_WIDTHS else -1
            row = T.Row(k="w", f=0, p=0, m=k["m"], fld=k["donor"], don=k["donor"], sc=0, src=k["src"], sid=k["sid"],
                        uid=0, lvl=0, ip=k["ip"], tag=k["tag"], add=0, byte=int(index) >> 3 if bit >= 0 else int(index),
                        width=width, bit=bit, old=0, new=k["value"], same=0)
            idx = stock(k["donor"])
            j = idx.join(row) if idx is not None else None
            rv = k.get("rvalue")
            if j is None or j.status != "store" or j.tag != k["tag"] or j.rel != k["off"]:
                bad.append(f"{A.label(k)}: {None if j is None else (j.status, j.tag, j.rel, j.reason)}")
            elif not rv:
                bad.append(f"{A.label(k)}: a :=var key names no rvalue (the variable its store takes)")
            elif not re.search(re.escape(k["target"]) + " " + re.escape(rv) + r" B_LET\b", j.text or ""):
                bad.append(f"{A.label(k)}: the statement is not {k['target']} := {rv}: {(j.text or '')[:100]!r}")
        sm = pred.get("start_music")
        if sm is not None:
            same = [k for k in pred["writes"] if all(k[f] == sm[f] for f in ("donor", "m", "src", "sid", "tag", "ip",
                                                                               "off", "target", "value", "op"))]
            if len(same) != 1:
                bad.append(f"start_music ({sm['donor']} e{sm['sid']} t{sm['tag']} ip{sm['ip']} {sm['target']} := "
                           f"{sm['value']}) is {len(same)} writes keys, not one")
        pok, pdetail = self.route_pins_check(pred, stock)
        if not pok:
            bad.append(pdetail)
        if bad:
            return False, self.title("KEYS"), "; ".join(bad)[:1200]
        return (True, self.title("KEYS"),
                detail.replace("O2-START", "O5-START") + "; the choice's :=var key ("
                + ", ".join(f"{k['donor']} e{k['sid']} t{k['tag']} ip{k['ip']}, rvalue {k['rvalue']}" for k in var)
                + f") in its statement; start_music one writes key; {pdetail}")

    def route_pins_check(self, pred: dict, stock, *, mes=None) -> tuple:
        """O5-KEYS (b), THE ROUTE PINS (4.14): ``(ok, detail)`` -- every pin's instruction text EXACTLY the stock US
        script's, then ``route_mes`` on block 3's US source (``mes``, ``{mes id: source}``, a seam): the marker page
        holds every guard marker and no ``[TIME=`` (only a Confirm closes it, 2.5.5); the choice opens with its
        ``opens`` and holds ``holds`` (``[IMME]``: no type-out, 0.2 #14), and its ``[CHOO]`` lines hold the guarded
        rule's pick on exactly one line, the ``pick_line``-th; the pick's branch page holds ``branch[0]`` and the
        other's ``branch[1]``, neither holding the other's; the stop page holds the stop page's match."""
        bad, n = [], 0
        cache: dict = {}
        for donor, sid, tag, ip, text in pred.get("route_pins") or ():
            n += 1
            idx = stock(donor)
            if idx is None:
                bad.append(f"{donor}: no stock script")
                continue
            items = cache.setdefault((donor, sid, tag), {i: t for i, _rel, t in A.O2Segment._items(idx, sid, tag)})
            got = items.get(ip)
            if got != text:
                bad.append(f"{donor} e{sid} t{tag} ip{ip}: {got!r}, pinned {text!r}")
        rm = pred.get("route_mes") or {}
        if mes is None:
            from ff9mapkit import dialogue
            body = A.stock_text_assets(int(rm.get("block", TEXT_BLOCK)))[pred.get("lang", SESSION_LANG)]
            body = body.decode("utf-8", errors="replace") if isinstance(body, (bytes, bytearray)) else str(body)
            mes = {i: x.text for i, x in dialogue.parse_mes(body).items()}
        g = pred.get("guard") or {}
        marker = str(mes.get(rm.get("marker")) or "")
        for m in g.get("markers") or ():
            if m not in marker:
                bad.append(f"mes {rm.get('marker')} (the marker page) does not hold the marker {m!r}")
        if "[TIME=" in marker:
            bad.append(f"mes {rm.get('marker')} (the marker page) holds a [TIME=: it would close itself")
        ch = rm.get("choice") or {}
        src = str(mes.get(ch.get("mes")) or "")
        if not src.startswith(str(ch.get("opens"))):
            bad.append(f"mes {ch.get('mes')} does not open with {ch.get('opens')!r}: {src[:40]!r}")
        if str(ch.get("holds")) not in src:
            bad.append(f"mes {ch.get('mes')} does not hold {ch.get('holds')!r} (a type-out the margin never assumed)")
        rule = next((r for r in pred.get("choices") or () if r.get("match") == g.get("choice")), {})
        lines = src.split("[CHOO]", 1)[1].split("\n") if "[CHOO]" in src else []
        hits = [i for i, ln in enumerate(lines) if rule.get("pick") and rule["pick"] in ln]
        if hits != [ch.get("pick_line")]:
            bad.append(f"mes {ch.get('mes')}'s [CHOO] lines hold the pick {rule.get('pick')!r} on line(s) {hits}, "
                       f"want exactly [{ch.get('pick_line')}]")
        br = rm.get("branch") or []
        marks = g.get("branch") or []
        if len(br) == 2 and len(marks) == 2:
            for page, mine, other in ((br[0], marks[0], marks[1]), (br[1], marks[1], marks[0])):
                text = str(mes.get(page) or "")
                if mine not in text:
                    bad.append(f"mes {page} does not hold its branch marker {mine!r}")
                if other in text:
                    bad.append(f"mes {page} holds the other branch's marker {other!r}")
        else:
            bad.append(f"route_mes branch {br} / guard branch {marks}: two pages, two markers")
        sp = rm.get("stop_page")
        for p in pred.get("stop_pages") or ():
            if p["match"] not in str(mes.get(sp) or ""):
                bad.append(f"mes {sp} does not hold the stop page {p['match']!r}")
        return (not bad, "; ".join(bad[:6]) if bad else
                f"{n} route pins equal; mes {rm.get('marker')} holds the marker and no [TIME=, mes {ch.get('mes')} "
                f"opens {ch.get('opens')}, holds {ch.get('holds')} and the pick on its "
                f"{'second' if ch.get('pick_line') == 1 else 'line ' + str(ch.get('pick_line'))} line, mes {br[0]} "
                f"holds the pick's branch marker and {br[1]} the other's, mes {sp} the stop page")

    def census_check(self, pred: dict, stock, *, sites=None, classify=None) -> tuple:
        """O5-CENSUS (6.1): :func:`store_census` over the route's stock fields -- every site classified, the inert
        functions proven not instanced at any route entrance of their field (a shared entry by its callers), or each
        failure named."""
        fields = list(pred["route"])
        bad, counts, proof = store_census(fields, stock, pred, sites=sites, classify=classify)
        if bad:
            return False, self.title("CENSUS"), f"{len(bad)} problem(s): " + "; ".join(bad[:8])
        tot = {f: sum(v for k, v in counts[f].items() if k != "unresolved") for f in fields}
        sf = pred["start_first"]
        sf_masked = bool(T.noise_regions(P._site_row(sf["target"])))
        short = {"forbidden_sites": "forbidden"}
        cols = ", ".join(f"{short.get(n, n)} " + "/".join(str(counts[f].get(n, 0)) for f in fields)
                         + (f" ({sf['donor']}'s ip{sf['ip']} is start_first)" if n == "masked" and sf_masked else "")
                         for n in CENSUS_LISTS if n != "start_first" or any(counts[f].get(n) for f in fields))
        unres = sum(counts[f].get("unresolved", 0) for f in fields)
        parts = []
        for f in fields:
            x = [i for i in pred.get("inert") or () if int(i["donor"]) == f]
            if not x:
                continue
            ents = (proof.get(f) or {}).get("entrances") or []
            sids = sorted(x, key=lambda i: int(i["sid"]))
            names = [f"e{i['sid']}" + (f" (shared, run only from {', '.join(f'e{s}' for s in i['shared_by'])})"
                                      if i.get("shared_by") else "") for i in sids]
            parts.append(f"{f} {', '.join(names)} not instanced at {' or '.join(str(e) for e in ents)}")
        return (True, self.title("CENSUS"),
                ", ".join(f"{f}: {tot[f]}" for f in fields) + f" store sites -- all classified ({cols}); {unres} "
                f"unresolved; inert " + "; ".join(parts))

    def regions_check(self, pred: dict, stock) -> tuple:
        """O5-REGIONS (6.1): :func:`regions_problems`."""
        bad, roles, ngw, nhot = regions_problems(pred, stock)
        n = sum(roles.values())
        return (not bad, self.title("REGIONS"),
                "; ".join(bad[:6]) if bad else
                f"{n} regions (" + ", ".join(f"{roles[r]} {r}" for r in ("exit", "scene", "dormant") if roles[r])
                + f"), {nhot} hot-spots, {ngw} gateway entries all registered")

    def goals_check(self, pred: dict, walkmesh=None) -> tuple:
        """O5-GOALS (6.1): O2's ``goals_check`` on the table (the step runnable, ``visits`` a walk on the route from the
        start place, the goal on the floor >= 80 from a wall with the 33 triangles closed, its ``until`` true at the
        goal, a route from ``start`` round the ``avoid`` set), then :func:`goals_extra`: (c) the contour on the planned
        route, (d) the evidence's soundness on the contour."""
        ok, what, detail = A.O2Segment.goals_check(self, pred, walkmesh)
        bad, lines = goals_extra(pred, walkmesh)
        if not ok or bad:
            return False, self.title("GOALS"), "; ".join(([detail] if not ok else []) + bad)[:1200]
        return True, self.title("GOALS"), detail + "; " + "; ".join(lines)

    # -- the live install (read-only) ---------------------------------------------------------------------------
    def preflight_extra(self, pred: dict, roots: list, *, manifest=None, pads=..., live_engine=None, game=None,
                        stock_text=None) -> list:
        """6.2's extras, in order: P-TEXT (block 3, STRICT: :func:`o4_castle.p_text`, no tolerated copy), P-RECOVERY,
        P-DONOR (151, 153 and 154), P-SETTINGS, P-PAD, P-OVERRIDE, P-ENGINE -- O4's set but P-GATE and P-TEXT for block
        2 (research/o5_design.md 11.2 #1). ``manifest`` is unread here (P-MANIFEST is the base's); ``pads`` (P-PAD's
        reader), ``live_engine``, ``game`` (the install whose Memoria.ini P-SETTINGS reads) and ``stock_text``
        (``{block: {lang: bytes}}``) are seams."""
        game = Path(game) if game is not None else GAME
        out = []
        for block in pred.get("text_blocks") or [TEXT_BLOCK]:
            found = [(Path(r).name, A.shipped_text(r, block)) for r in roots]
            found = [(nm, s) for nm, s in found if s]
            stock = ((stock_text or {}).get(block) if stock_text is not None
                     else A.stock_text_assets(block)) if found else {}
            ok, detail = C4.p_text(block, found, stock, o1_block2=None, o4_registered=True,
                                   lang=pred.get("lang", SESSION_LANG))
            out.append((ok, self.title(f"P-TEXT{block}"), detail))
        rec = int(pred.get("recovery", self.recovery))
        hits = [Path(r).name for r in roots if rec in T.mod_registrations(r)]
        out.append((bool(hits), self.title("P-RECOVERY"),
                    f"{rec} registered in {', '.join(hits)}" if hits else f"{rec} is registered in no mod folder"))
        ok, detail = P.p_donor({**pred, "route": list(pred["route"]) + list(pred.get("end_fields") or [])}, roots)
        out.append((ok, self.title("P-DONOR"), detail))
        want = pred.get("settings") or SETTINGS
        ok, detail = P.p_settings(want, P.install_settings(game, roots, want))
        out.append((ok, self.title("P-SETTINGS"), detail))
        ok, detail = C4.p_pad(C4.xinput_slots(pads))
        out.append((ok, self.title("P-PAD"), detail))
        ok, detail = C4.p_override(C4.override70_of(roots), pred.get("override70") or OVERRIDE70)
        out.append((ok, self.title("P-OVERRIDE"), detail))
        live = live_engine if live_engine is not None else C4.engine_shas(game)
        ok, detail = C4.p_engine(live, pred.get("engine") or ENGINE)
        out.append((ok, self.title("P-ENGINE"), detail))
        return out

    # -- the session --------------------------------------------------------------------------------------------
    def capabilities(self, g, *, pads=..., engine=None, live_engine=None) -> list:
        """O2's (P-CAP, P-OBJECTS, P-LANG), then P-DONOR-LOG for 151, 153 and 154, P-LAUNCH (every stacked patch file,
        Memoria.ini and the x64 and x86 engine DLLs older than the launch's first log stamp, the DLLs the pinned engine)
        and P-PAD re-sampled on this launch -- O4's, over O5's donors. ``pads``, ``engine`` and ``live_engine`` are
        seams for the fake."""
        import dali_tour as D
        from harness.logs import MEMORIA_LOG
        out = A.O2Segment.capabilities(self, g)
        log = next((p for name, p in g._log_paths() if name == MEMORIA_LOG), None)
        try:
            text = log.read_text(encoding="utf-8", errors="replace") if log is not None else None
        except OSError:
            text = None
        ok, detail = P.p_donor_log(text, ROUTE_DONORS)
        out.append((ok, self.title("P-DONOR-LOG"), detail))
        game = Path(g.game_path)
        try:
            roots = D.mod_roots(game)
        except OSError:
            roots = []
        ok, detail = C4.launch_engine_check(P.launch_files(game, roots), C4.engine_files(game), P.launch_time(text),
                                            live_engine if live_engine is not None else C4.engine_shas(game),
                                            engine or ENGINE)
        out.append((ok, self.title("P-LAUNCH"), detail))
        ok, detail = C4.p_pad(C4.xinput_slots(pads))
        out.append((ok, self.title("P-PAD"), detail))
        return out

    # -- reading a session ---------------------------------------------------------------------------------------
    def read_session(self, run_dir, pred: dict, *, session: dict | None = None, stock=None) -> list:
        """The shared reading, with the stock scripts kept for O5-PATTERN's join and the report."""
        self._stock = stock or self.stock_source()
        return super().read_session(run_dir, pred, session=session, stock=self._stock)

    def _stock_src(self):
        if self._stock is None:
            self._stock = self.stock_source()
        return self._stock

    def why_void(self, rec: dict, r: dict, pred: dict) -> list:
        """O4's reasons (O3's: A-NOSTART, A-FORBIDDEN, A-MISMATCH, A-START, A-NOEND, the cut row), with A-START SCOPED
        TO VISIT 1 (research/o5_design.md 1.3; the claim critique #7): O3's rule reads any error-path row of the start
        place, and O5 revisits its start place -- an A-START whose row lies after the run's first row of the second
        visit's place (154) is withdrawn: a visit-3 error path is the game's V5 at [153, 1190, 3], which VOID-ASYM (a)
        reads, never "the start state took 153's error path". The withdrawn reason is kept on ``r``
        (``start_withdrawn``) for the report."""
        out = super().why_void(rec, r, pred)
        if not any(cls == "A-START" for _w, cls, _b in out):
            return out
        members = members_of(pred) if r["side"] == "F" else {}
        sp = place(pred["start"][r["side"]], members)
        errs = {(k["sid"], k["tag"], k["ip"], k["target"]) for k in pred.get("error_path") or () if k["donor"] == sp}
        hit = next((x for x in r["rows"] if x.k == "w" and x.m == T.FIELD_MODE and place(x.fld, members) == sp
                    and (x.sid, x.tag, x.ip, x.target) in errs), None)
        order = list(pred.get("visits") or pred["route"])
        nxt = next((p for p in order[1:] if p != order[0]), None)
        first = next((x.line for x in r["rows"] if x.k in ("w", "r") and nxt is not None
                      and place(x.fld, members) == nxt), None)
        if hit is None or first is None or hit.line < first:
            return out
        r["start_withdrawn"] = [w for w, cls, _b in out if cls == "A-START"]
        return [(w, cls, b) for w, cls, b in out if cls != "A-START"]

    # -- the checks ---------------------------------------------------------------------------------------------
    def core_checks(self, runs: list, cov: dict, pred: dict) -> list:
        covered = cov["S"] + cov["F"]
        c = self.comparison(cov, pred)
        return [self.start_check(covered, pred), self.no_sc_check(covered, pred),
                self.span_check("CHAIN", covered, pred, "entrance_bytes", "chain", pred["entrance"]),
                self.residue_check(covered, pred), self.writes_check(covered, pred), self.null_check(c, pred),
                self.stable_check(c, pred), self.landing_check(cov, pred), self.choice_check(covered, pred),
                self.walk_check(covered, pred), self.pattern_check(covered, pred), self.masked_check(cov, pred),
                self.state_check(covered, pred), self.join_check(cov)]

    def landing_check(self, cov: dict, pred: dict) -> tuple:
        """O5-LANDING (5.3), over every covered run, each clause named in the detail:
          (a) every field-mode ``w``/``c`` row ran in its place's own field (member(place) on F, the place on S), and
              none stands in a place off ``route_places`` [153, 154];
          (b) the crossings, on field-mode ``w`` rows at their places' own fields: the run holds ``landing.exit153``
              (153 e3 t1 ip3150) and the next field-mode ``w`` row after it is ``landing.enter154`` (154 e0 t0 ip26: 154
              loaded by 153's Field(154)); it holds ``landing.exit154`` (154 e2 t1 ip1520) and the next after it is
              ``landing.enter153b`` (153 e0 t0 ip57, old -1: the revisit's first EMITTED row under this start's
              suppression pattern -- start-scoped, 5.4); no row of place 154 after ``enter153b``;
          (c) the last field-mode ``w`` row before the end cut is ``landing.exit153b`` (153 e18 t1 ip1077), read by
              PLACE, and the run's ``end`` log row names the side's end field (151 on S, member(151) on F);
          (d) THE END PER SIDE: the end cut (``cut_row``) is a raw ``w`` row that is ``landing.end_row`` (151 e0 t0
              ip22) at ``fld`` the side's end field;
          (e) every F digest records no seam and no seam key (the chain is closed from member(153) to member(151))."""
        L = pred["landing"]
        ex153, en154, ex154, en153b = L["exit153"], L["enter154"], L["exit154"], L["enter153b"]
        ex153b, lend = L["exit153b"], L["end_row"]
        route = set(L["route_places"])
        fm = T.FIELD_MODE
        bad = []

        def is_at(x, spec, members) -> bool:
            return (x.k == "w" and x.m == fm and place(x.fld, members) == spec["place"]
                    and (x.sid, x.tag, x.ip, x.target, x.new) == (spec["sid"], spec["tag"], spec["ip"], spec["target"],
                                                                   spec["value"])
                    and ("old" not in spec or x.old == spec["old"]))

        def where(spec) -> str:
            return (f"{spec['place']} e{spec['sid']} t{spec['tag']} ip{spec['ip']} {spec['target']}={spec['value']}"
                    + (f" (old {spec['old']})" if "old" in spec else ""))
        covered = cov["S"] + cov["F"]
        for r in covered:
            lab = f"{r['side']}#{r['i']}"
            members = members_of(pred) if r["side"] == "F" else {}
            inv = {d: f for f, d in sorted(members.items(), reverse=True)}

            def fld_of(p):
                return inv.get(p, p) if members else p
            rows = r["rows"]
            off = next((x for x in rows if x.k in ("w", "c") and x.m == fm
                        and (place(x.fld, members) not in route or x.fld != fld_of(place(x.fld, members)))), None)
            if off is not None:
                p = place(off.fld, members)
                bad.append(f"{lab} (a): line {off.line} {off.k} {A._row_text(off)} stands in place {p} at fld "
                           f"{off.fld}" + (f", not {fld_of(p)}" if p in route else f", off {sorted(route)}"))
            ws = [x for x in rows if x.k == "w"]
            for ex, en in ((ex153, en154), (ex154, en153b)):
                i = next((j for j, x in enumerate(ws) if is_at(x, ex, members) and x.fld == fld_of(ex["place"])), None)
                if i is None:
                    bad.append(f"{lab} (b): no {where(ex)} row at fld {fld_of(ex['place'])}")
                    continue
                nxt = next((x for x in ws[i + 1:] if x.m == fm), None)
                if nxt is None or not (is_at(nxt, en, members) and nxt.fld == fld_of(en["place"])):
                    bad.append(f"{lab} (b): the next field row after {ex['place']} ip{ex['ip']} is "
                               f"{A._row_text(nxt) if nxt is not None else 'none'}"
                               + ("" if nxt is None else f" (old {nxt.old})")
                               + f", not {where(en)} at fld {fld_of(en['place'])}")
            k = next((j for j, x in enumerate(ws) if is_at(x, en153b, members)), None)
            back = None if k is None else next((x for x in ws[k + 1:] if x.m == fm
                                                and place(x.fld, members) == en154["place"]), None)
            if back is not None:
                bad.append(f"{lab} (b): line {back.line} {A._row_text(back)}: place {en154['place']} written again "
                           f"after 153's revisit began")
            fws = [x for x in ws if x.m == fm]
            last = fws[-1] if fws else None
            if last is None or not is_at(last, ex153b, members):
                bad.append(f"{lab} (c): the last field row before the end cut is "
                           f"{A._row_text(last) if last is not None else 'none'}, not {where(ex153b)}")
            want_end = ST.side_ends(pred, r["side"])
            endrow = [x for x in r.get("log") or () if x.get("k") == "end"]
            if not endrow or endrow[-1].get("field") not in want_end:
                bad.append(f"{lab} (c): the run's end row names field "
                           f"{endrow[-1].get('field') if endrow else None}, not the side's end field {want_end}")
            cr = r.get("cut_row")
            if cr is None or not (cr.k == "w" and cr.m == fm and cr.fld in want_end
                                  and (cr.sid, cr.tag, cr.ip, cr.target, cr.new) == (
                                      lend["sid"], lend["tag"], lend["ip"], lend["target"], lend["value"])):
                desc = ("no row" if cr is None else
                        f"{cr.k} " + (A._row_text(cr) if cr.k == "w" else f"{cr.fld} byte {cr.byte} {cr.old}->{cr.new}"))
                bad.append(f"{lab} (d): the end cut (line {r.get('cut')}) is {desc}, not {where(lend)} at the side's "
                           f"end field {want_end}")
            if r["side"] == "F":
                d = r["digest"]
                if d.seams or d.seam_keys:
                    bad.append(f"{lab} (e): {len(d.seams)} seam crossing(s) "
                               + ", ".join(f"{s.origin} -> {s.to}" for s in d.seams[:3])
                               + f", {len(d.seam_keys)} seam key(s): the chain must be closed")
        return (not bad, self.title("LANDING"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) every field row in its place's own field; (b) 153 "
                                      f"ip{ex153['ip']} -> 154 e0 t0 ip{en154['ip']}, 154 ip{ex154['ip']} -> 153 e0 t0 "
                                      f"ip{en153b['ip']} (the revisit's first emitted row), 154 never written again; "
                                      f"(c) 153 ip{ex153b['ip']} last, the end row the side's own; (d) the cut at 151 "
                                      f"e0 t0 ip{lend['ip']} (S 151, F {ST.side_ends(pred, 'F')}); (e) no seam")

    def choice_check(self, covered: list, pred: dict) -> tuple:
        """O5-CHOICE (5.3; decision 3), over every covered run, each clause named:
          (a) exactly ONE store at ``choice.store``'s site (153 e3 t1 ip1741, Global.Bit[3795]): one raw ``w`` row, old
              0, new 1, at fld member(153) / 153, and NO ``c`` row of that site -- the sink emits a site's first
              SAME-VALUE store and counts only later ones, so after the change a second 1 -> 1 store is a second ``w``
              row and only a third is counted;
          (b) exactly one ``choice`` row of the guarded rule: ``index`` ``choice.index``, ``took.landed`` True; its
              answer's ``press`` row (``why`` "choose", ``answer``, its seq in the guard row's answer span) with
              ``selected_before`` the index and a ``down_frame``; the visit's ``guard`` row with ``verdict`` "ok" and
              ``branch`` "pick" (the game's own branch page after the answer, 0.2 #20); no second guard row;
          (c) the store's value equals that ``index``, and its row's frame ``f`` is at or after the answer's
              ``down_frame`` (both Time.frameCount);
          (d) THE BACKSTOP (S10's judgment VOIDs a run first): the guard row's ``armed_frame`` set, ``open_frame`` set
              and <= ``choice_first`` (the window opens at the first sample without the marker page, which can be the
              choice's own first sample), ``marker_last`` set, and :func:`guard_derived` -- guard_strays re-derived
              from the row's ``presses`` -- empty and equal to its ``strays``."""
        ch = pred["choice"]
        sp = ch["store"]
        bad = []
        for r in covered:
            lab = f"{r['side']}#{r['i']}"
            members = members_of(pred) if r["side"] == "F" else {}
            inv = {d: f for f, d in sorted(members.items(), reverse=True)}
            want_fld = inv.get(sp["place"], sp["place"]) if members else sp["place"]
            rows, log = r["rows"], r.get("log") or []
            site = [x for x in rows if x.k in ("w", "c") and place(x.fld, members) == sp["place"]
                    and (x.sid, x.tag, x.ip, x.target) == (sp["sid"], sp["tag"], sp["ip"], sp["target"])]
            ws, cs = [x for x in site if x.k == "w"], [x for x in site if x.k == "c"]
            if len(ws) != 1 or cs or (ws[0].fld, ws[0].old, ws[0].new) != (want_fld, sp["old"], sp["value"]):
                bad.append(f"{lab} (a): {len(ws)} w row(s) "
                           + ", ".join(f"{x.fld} {x.old}->{x.new}" for x in ws[:3])
                           + (f" and {len(cs)} c row(s) n {[x.n for x in cs]}" if cs else "")
                           + f" at {sp['place']} e{sp['sid']} t{sp['tag']} ip{sp['ip']}, want one {want_fld} "
                             f"{sp['old']}->{sp['value']} and no count")
            crow = choice_rows(log, pred)
            grows = [x for x in log if x.get("k") == "guard"]
            g = grows[0] if len(grows) == 1 else None
            ans = []
            if g is not None and g.get("answer"):
                lo, hi = g["answer"]
                ans = [p for p in log if p.get("k") == "press" and p.get("why") == "choose" and p.get("answer")
                       and p.get("seq") is not None and lo < int(p["seq"]) <= hi]
            took = (crow[0].get("took") or {}) if len(crow) == 1 else {}
            probs = []
            if len(crow) != 1:
                probs.append(f"{len(crow)} choice row(s) of the guarded rule")
            elif crow[0].get("index") != ch["index"] or took.get("landed") is not True:
                probs.append(f"the choice row's index {crow[0].get('index')}, took.landed {took.get('landed')!r}")
            if len(ans) != 1:
                probs.append(f"{len(ans)} answer press row(s) in the guard row's answer span")
            elif ans[0].get("selected_before") != ch["index"] or ans[0].get("down_frame") is None:
                probs.append(f"the answer's Confirm selected_before {ans[0].get('selected_before')!r}, down frame "
                             f"{ans[0].get('down_frame')}")
            if g is None:
                probs.append(f"{len(grows)} guard row(s)")
            elif g.get("verdict") != "ok" or g.get("branch") != "pick":
                probs.append(f"the guard row's verdict {g.get('verdict')!r}, branch {g.get('branch')!r}")
            if probs:
                bad.append(f"{lab} (b): " + "; ".join(probs) + f" -- want one answered {ch['index']} by a verified "
                                                               f"landing, the pick's branch page, verdict ok")
            idx = crow[0].get("index") if len(crow) == 1 else None
            down = ans[0].get("down_frame") if len(ans) == 1 else None
            if len(ws) == 1 and (ws[0].new != idx or down is None or ws[0].f < down):
                bad.append(f"{lab} (c): the stored value {ws[0].new} at frame {ws[0].f}, the answer index {idx} down at "
                           f"frame {down}: the store must equal the pick and follow its Confirm")
            if g is not None:
                gp = []
                if g.get("armed_frame") is None:
                    gp.append("never armed (armed_frame None)")
                if g.get("open_frame") is None:
                    gp.append("no quiet window (open_frame None)")
                elif g.get("choice_first") is None or g["open_frame"] > g["choice_first"]:
                    gp.append(f"the quiet window opened at {g['open_frame']}, after the choice's first sample "
                              f"{g.get('choice_first')}")
                if g.get("marker_last") is None:
                    gp.append("no marker_last")
                derived = guard_derived(g)
                if derived:
                    s = derived[0]
                    gp.append(f"a press (seq {s['seq']}, {s['why']}) "
                              + ("went down" if s["placed"] else "was decided")
                              + f" at frame {s['down_frame'] if s['placed'] else s['decision_frame']}, inside "
                                f"[{g.get('marker_last')}, {g.get('choice_close')})")
                if [s["seq"] for s in derived] != [s.get("seq") for s in g.get("strays") or ()]:
                    gp.append(f"the row's strays {[s.get('seq') for s in g.get('strays') or ()]} are not the "
                              f"re-derived {[s['seq'] for s in derived]}")
                if gp:
                    bad.append(f"{lab} (d): " + "; ".join(gp))
        return (not bad, self.title("CHOICE"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) one ip{sp['ip']} {sp['target']} {sp['old']} -> "
                                      f"{sp['value']} each, no count; (b) the guarded rule answered {ch['index']} once "
                                      f"by a verified landing, the pick's branch page, verdict ok; (c) the store = the "
                                      f"pick, after its Confirm; (d) armed, the quiet window open by the choice's first "
                                      f"sample, no stray")

    def walk_check(self, covered: list, pred: dict) -> tuple:
        """O5-WALK (5.3; THE PAIRED-WALK LAW), over every covered run, each clause named:
          (a) exactly one ``step`` row of the stair step (``walk.name``, ``walk.donor``, ``walk.visit``) with ``outcome``
              "done", its ``lost`` sample satisfying the step's ``until`` (re-checked), its ``landed`` None; before it
              at most ``interrupts`` ``interrupted`` rows, each with no ``door`` (a side scene, never an exit), and at
              most ``attempts`` - 1 ``failed`` rows, each with ``landed`` None and no ``door`` (the driver critique
              #3); nothing after it;
          (b) no ``w`` row (any target, masked or not) whose frame lies inside a walk window (:func:`walk_windows`):
              the walk wrote nothing, so no key can depend on its path."""
        w = pred["walk"]
        steps = [step for c in pred.get("table") or () for step in c["steps"] if step.get("name") == w["name"]]
        step = SD.step_of(pred, steps[0]) if steps else {}
        bad = []
        for r in covered:
            lab = f"{r['side']}#{r['i']}"
            rows = walk_rows(r.get("log") or [], pred)
            done = [i for i, s in enumerate(rows) if s.get("outcome") == "done"]
            probs = []
            if len(done) != 1 or done[0] != len(rows) - 1:
                probs.append(f"{len(done)} done row(s) of {len(rows)} step rows"
                             + ("" if not rows else f" (outcomes {[s.get('outcome') for s in rows]})"))
            else:
                d = rows[done[0]]
                lost = d.get("lost") or {}
                if not SD.until_ok(step.get("until") or {}, lost.get("x"), lost.get("z")):
                    probs.append(f"the done row's loss at ({lost.get('x')}, {lost.get('z')}) fails until "
                                 f"{step.get('until')}")
                if d.get("landed") is not None:
                    probs.append(f"the done row landed in {d.get('landed')}")
                before = rows[:done[0]]
                inter = [s for s in before if s.get("outcome") == "interrupted"]
                failed = [s for s in before if s.get("outcome") == "failed"]
                other = [s for s in before if s.get("outcome") not in ("interrupted", "failed")]
                if len(inter) > int(step.get("interrupts", 0)):
                    probs.append(f"{len(inter)} interrupted row(s), over its {step.get('interrupts')}")
                if any(s.get("door") for s in inter):
                    probs.append(f"an interrupted row in a door ({[s.get('door') for s in inter if s.get('door')]})")
                if len(failed) > int(step.get("attempts", 1)) - 1:
                    probs.append(f"{len(failed)} failed row(s), over its {int(step.get('attempts', 1)) - 1}")
                if any(s.get("door") or s.get("landed") is not None for s in failed):
                    probs.append("a failed row in a door or landed")
                if other:
                    probs.append(f"step row(s) {[s.get('outcome') for s in other]} before the done one")
            if probs:
                bad.append(f"{lab} (a): " + "; ".join(probs))
            for lo, hi, what in walk_windows(rows):
                hit = next((x for x in r["rows"] if x.k == "w" and lo <= x.f <= hi), None)
                if hit is not None:
                    bad.append(f"{lab} (b): line {hit.line} {A._row_text(hit)} at frame {hit.f}, inside the walk "
                               f"window {what} [{lo}, {hi}]")
                    break
        return (not bad, self.title("WALK"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) the stairs done at the contour's side "
                                      f"({step.get('until')}), no door; (b) no row inside a walk window")

    def pattern_check(self, covered: list, pred: dict) -> tuple:
        """O5-PATTERN (5.3; the claim critique #1, #10): the suppression model's prediction, EXACT, every covered run
        -- :func:`pattern_of` over the joined script rows of the route places before the cut, against ``pattern``
        (:func:`pattern_diff`): (a) the ``c`` multiset, (b) each visit's emitted sequence. Byte[8]'s whole history is in
        (b), its last row before the cut visit 3's ip890 := 0 (4.9)."""
        pat = pred["pattern"]
        stock = self._stock_src()
        bad = []
        for r in covered:
            members = members_of(pred) if r["side"] == "F" else {}
            got = pattern_of(r["rows"], pred, members, stock_join(stock, members))
            bad += [f"{r['side']}#{r['i']} {p}" for p in pattern_diff(got, pat)]
        nv = [len(v) for v in pat["visits"]]
        return (not bad, self.title("PATTERN"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) the {len(pat['counts'])} counted stores as frozen; (b) "
                                      f"{len(nv)} visits' emitted rows ({'+'.join(map(str, nv))}) in order, as frozen")

    # -- the report ---------------------------------------------------------------------------------------------
    def report_extra(self, run_dir: Path, session: dict, pred: dict, runs: list, checks: list) -> list:
        """Report-only (5.4): the scope (six lines: start dependence; the suppressed stores; the stored choice; the end
        state; the settings, the derived facts and the engine, as recorded; the language, read from the recorded P-TEXT
        rows), the walk per run, the guard and the choice per run, the pattern per run, the session's end, O4's
        sections (copied) and the re-runs held."""
        L = ["", "Scope (a US session):", "  start dependence -- " + SCOPE_START,
             "  suppressed stores -- " + SCOPE_SUPPRESSED, "  the stored choice -- " + SCOPE_CHOICE,
             "  the end state -- " + SCOPE_END_STATE]
        st = (session.get("install") or {}).get("settings")
        eng = [d for _ok, _w, d in self._recorded(session, "P-ENGINE")]
        L.append("  settings and engine -- " + (json.dumps(st, sort_keys=True) if st is not None else "not recorded")
                 + "; derived -- " + "; ".join(f"{k} {v.get('value')} ({v.get('why')})"
                                               for k, v in (pred.get("derived") or {}).items())
                 + "; engine -- " + (eng[-1] if eng else json.dumps((session.get("install") or {}).get("engine"))))
        L.append("  language -- " + self.scope_lang(session))
        L.append("")
        L.append("The walk, per run (attempt, outcome, from -> loss (frame, x, z), frames, route; door, landed, why):")
        for r in runs:
            L += self._walk_lines(r, pred)
        L.append("")
        L.append("The guard and the choice, per run (armed / opened / re-arms; 127's last sample, 128's first, ready and "
                 "close; THE RACE MARGIN 127's last sample -> 128's readiness in frames; the presses; the answer; "
                 "strays; the branch page; the verdict):")
        for r in runs:
            L += self._guard_lines(r, pred)
        L.append("")
        L.append("The pattern, per run (emitted rows per visit, the c rows, visit 3's first emitted row; O5-PATTERN's "
                 "first difference):")
        stock = self._stock_src()
        for r in runs:
            L += self._pattern_lines(r, pred, stock)
        L.append("")
        for r in runs:
            if r.get("start_withdrawn"):
                L.append(f"A-START withdrawn (visit 1 only): {r['side']}#{r['i']}: {r['start_withdrawn']}")
        ended = session.get("ended")
        if ended is None:
            L.append("The session's end: not recorded")
        else:
            L.append("The session's end (end_run, warp first): "
                     + ("the title came back" if ended.get("ok") else f"the title did NOT come back: {ended.get('why')}")
                     + f"; rows {[x.get('k') for x in ended.get('log') or ()]}")
        L += self._o2_sections(session, runs)
        if session.get("rerun_held"):
            L += ["", f"Re-runs held (rerun.stop_on): {session['rerun_held']}"]
        return L

    @staticmethod
    def _walk_lines(r: dict, pred: dict) -> list:
        lab = f"  {r['side']}#{r['i']}:"
        rows = walk_rows(r.get("log") or [], pred)
        if not rows:
            v = r["rec"].get("v")
            return [f"{lab} no stair step row" + (f" (the run VOID {v})" if v else "")]
        out = []
        for s in rows:
            fr, lost = s.get("from") or {}, s.get("lost") or {}
            rt = s.get("route") or {}
            frames = (lost["frame"] - s["frame0"]) if lost.get("frame") is not None and s.get("frame0") is not None \
                else None
            out.append(f"{lab} attempt {s.get('attempt')} {s.get('outcome')}: from frame {fr.get('frame')} "
                       f"({fr.get('x')}, {fr.get('z')}) -> loss frame {lost.get('frame')} ({lost.get('x')}, "
                       f"{lost.get('z')}), {frames} frames; route legs {rt.get('route')} travelled "
                       f"{rt.get('travelled')} replans {rt.get('replans')} pushes {rt.get('pushes')} waits "
                       f"{rt.get('waits')} blockers {rt.get('blockers')}"
                       + (f"; door {s.get('door')}" if s.get("door") else "")
                       + (f"; landed {s.get('landed')}" if s.get("landed") is not None else "")
                       + (f" -- {s.get('why')}" if s.get("why") else ""))
        return out

    @staticmethod
    def _guard_lines(r: dict, pred: dict) -> list:
        lab = f"  {r['side']}#{r['i']}:"
        log = r.get("log") or []
        g = next((x for x in log if x.get("k") == "guard"), None)
        strays = [x for x in log if x.get("k") == "guard_stray"]
        if g is None:
            v = r["rec"].get("v")
            return [f"{lab} no guard row" + (f" (the run VOID {v})" if v else "")]
        margin = (g["choice_ready"] - g["marker_last"]) if g.get("choice_ready") is not None \
            and g.get("marker_last") is not None else None
        ch = choice_rows(log, pred)
        took = (ch[0].get("took") or {}) if ch else {}
        out = [f"{lab} armed {g.get('armed_frame')}, opened {g.get('open_frame')}, re-arms {g.get('rearms')}; 127 last "
               f"{g.get('marker_last')}, 128 first {g.get('choice_first')} ready {g.get('choice_ready')} close "
               f"{g.get('choice_close')}; RACE MARGIN {margin} frames; answer seqs {g.get('answer')}, closing seq "
               f"{g.get('closing_seq')}; strays {[s.get('seq') for s in g.get('strays') or ()]}; branch "
               f"{g.get('branch')} ({g.get('branch_raw')}); verdict {g.get('verdict')}"
               + (f" -- {g.get('why')}" if g.get("why") else "")]
        if ch:
            c = ch[0]
            out.append(f"{lab} 128 as published: {c.get('options')} active {c.get('active')} selected "
                       f"{c.get('selected')} -> {c.get('index')}; took landed {took.get('landed')} confirms "
                       f"{took.get('confirms')}")
        presses = [(p.get("seq"), p.get("why"), p.get("marker"), p.get("down_frame")) for p in g.get("presses") or ()]
        out.append(f"{lab} presses (seq, why, marker, down): {presses[-8:]}")
        out += [f"{lab} guard_stray {s.get('kind')}: {s.get('v')} ({s.get('by')}) in [{s.get('lo')}, {s.get('hi')})"
                for s in strays]
        return out

    @staticmethod
    def _pattern_lines(r: dict, pred: dict, stock) -> list:
        lab = f"  {r['side']}#{r['i']}:"
        if not r.get("rows"):
            return [f"{lab} no trace rows"]
        members = members_of(pred) if r["side"] == "F" else {}
        got = pattern_of(r["rows"], pred, members, stock_join(stock, members))
        v = got["visits"]
        out = [f"{lab} emitted per visit {[f'{x[0][0]}x{len(x)}' for x in v]}; c rows "
               f"{[(c[0], f'e{c[1]} t{c[2]} +{c[3]}', c[4], c[5], c[6]) for c in got['counts']]}; visit 3's first "
               f"{v[2][0] if len(v) > 2 else None}"]
        diff = pattern_diff(got, pred["pattern"])
        if diff:
            out.append(f"{lab} O5-PATTERN's first difference: {diff[0]}")
        return out

    # -- the CLI ------------------------------------------------------------------------------------------------
    def add_arguments(self, ap) -> None:
        ap.add_argument("--draft", action="store_true", help="print the draft predictions as JSON")
        ap.add_argument("--rehearsal-report", metavar="RUN_DIR",
                        help="print an o5_rehearse.py launch's record, stage by stage and run by run")

    def handle(self, args) -> int | None:
        """``--rehearsal-report`` (O5's); ``--offline-check`` (with the chain's route members printed first); then
        O2's (``--draft``, ``--preflight``)."""
        if args.rehearsal_report:
            print(rehearsal_report(args.rehearsal_report))
            return 0
        if args.offline_check:
            pred, what = self.current(args.predictions)
            print(f"predictions: {what}")
            members = members_of(pred)
            if all(d in members.values() for d in ROUTE_DONORS):
                print(f"chain: {route_members_line(members)}")
            checks = self.offline_check(pred)
            for ok, w, detail in checks:
                print(f"{'PASS' if ok else 'FAIL'}  {w}\n      {detail}")
                for d in A.defect_lines(detail):
                    print(d)
            return 0 if all(ok for ok, _w, _d in checks) else 1
        return A.O2Segment.handle(self, args)


O5 = O5Segment()


# ======================================================================== the rehearsal report
def _smoke_lines(name: str, stage: dict, recs: list, twins: list) -> list:
    """F-SMOKE's section (O4's shape): each warp -- field, entrance, SC, what it reached, the object sids, the
    exceptions and Memoria.log lines, end_run -- and each member's sids against its twin's."""
    L = [f"== {name}: the load smoke, pairs {stage.get('pairs')}  ({len(recs)} warp(s)) -- settles: "
         f"{stage.get('settles')}"]
    for rec in recs:
        reach = rec.get("reached") or {}
        er = rec.get("end_run") or {}
        L.append(f"  warp {rec.get('n')}: {rec.get('field')} at {rec.get('entrance')} SC {rec.get('sc')} -> "
                 + (f"field {reach.get('field')} {reach.get('ui')} at frame {reach.get('frame')} after {reach.get('s')}s"
                    f" (control {reach.get('control')})" if reach else f"NOT REACHED: {rec.get('error')}")
                 + f"; objects {rec.get('objects_status')} sids {rec.get('sids')}; exceptions "
                 f"{len(rec.get('exceptions') or [])}; log warnings/errors {len(rec.get('log_lines') or [])}; end_run "
                 f"{'ok' if er.get('ok') else 'FAILED ' + str(er.get('why'))} {[x.get('k') for x in er.get('how') or ()]}")
        for ln in (rec.get("log_lines") or [])[:4]:
            L.append(f"    log: {ln[:160]}")
    for t in twins or ():
        L.append(f"  twin {t.get('member')} vs {t.get('twin')}: " + ("EQUAL" if t.get("equal") else "DIFFERENT")
                 + f" ({t.get('member_sids')} vs {t.get('twin_sids')})")
    return L


def _walk_report(wr: dict) -> list:
    """The walk record's lines (7.2; F1, F12, F15): the grant, each attempt's walk, its holds on the last two legs, the
    loss and teleport samples, the calibration."""
    L = []
    gr = wr.get("grant")
    if gr is None:
        L.append("    walk: no grant before the stair step")
    else:
        objs = [(o.get("sid"), o.get("shown"), o.get("coll"), o.get("solid"), o.get("r"), o.get("talk_r"),
                 o.get("range_r")) for o in gr.get("objects") or ()]
        L.append(f"    grant: frame {gr.get('frame')} at ({gr.get('x')}, {gr.get('z')}) y {gr.get('y')}; "
                 f"{gr.get('from_last_page_frames')} frames from the last page's going ({gr.get('last_page')!r}); "
                 f"objects (sid, shown, coll, solid, r, talk_r, range_r) {objs}")
    for a in wr.get("attempts") or ():
        L.append(f"    stair attempt {a.get('attempt')}: {a.get('outcome')}; loss {a.get('lost')}; door "
                 f"{a.get('door')}; landed {a.get('landed')}")
        w = a.get("walk")
        if w is None:
            L.append("      no walk tapped for it")
            continue
        l2 = w.get("last_two_legs") or {}
        L.append(f"      route {w.get('legs')} legs {w.get('waypoints')}; {len(w.get('holds') or [])} hold(s); last two "
                 f"legs: {l2.get('holds')} hold(s), {l2.get('slides')} slide(s), {l2.get('stalls')} stall(s), pushes "
                 f"{w.get('pushes')} ({w.get('pushed')})")
        for h in w.get("holds") or ():
            if h.get("slide") or h.get("stall"):
                L.append(f"      {'SLIDE' if h['slide'] else ''}{'STALL' if h['stall'] else ''} seq {h.get('seq')} "
                         f"{h.get('steps')}: leg {h.get('leg')} moved {h.get('moved')} from {h.get('from')} to "
                         f"{h.get('to')}, off the pressed {h.get('off_pressed')} deg, off the leg {h.get('off_leg')} deg")
        lc, fw, tp = w.get("last_control"), w.get("first_without"), w.get("teleport")
        L.append(f"      last control sample {lc}; first without {fw}; teleport "
                 + (f"frame {tp.get('frame')} at ({tp.get('x')}, {tp.get('z')}), {tp.get('ticks_after_loss')} ticks "
                    f"after the loss (from {tp.get('source')})" if tp else "not seen") + f"; {w.get('samples')} samples")
    L.append(f"    calibration: {wr.get('calibration')}")
    return L


def _guard_report(gd: dict) -> list:
    """The guard record's lines (7.2; F2, F3, F9): 127 and its presses, the guard row, 128 as published, the landing,
    the race margin."""
    L = [f"    127 (the marker page): {[(p.get('frame'), p.get('gone_frame')) for p in gd.get('marker_pages') or ()]} "
         f"(first seen, gone); presses (seq, decision, accepted, down, ack) "
         f"{[(p.get('seq'), p.get('decision_frame'), p.get('accepted_frame'), p.get('down_frame'), p.get('ack_frame')) for p in gd.get('marker_presses') or ()]}"]
    g = gd.get("guard")
    if g is None:
        L.append(f"    guard: no guard row ({gd.get('guard_rows')})")
    else:
        L.append(f"    guard: armed {g.get('armed_frame')}, quiet window open {g.get('open_frame')}, re-arms "
                 f"{g.get('rearms')}; 127 last {g.get('marker_last')}; 128 first {g.get('choice_first')} ready "
                 f"{g.get('choice_ready')} close {g.get('choice_close')}; answer {g.get('answer')}, closing seq "
                 f"{g.get('closing_seq')}; strays {[s.get('seq') for s in g.get('strays') or ()]}; branch "
                 f"{g.get('branch')} {g.get('branch_raw')}; verdict {g.get('verdict')}")
    m = gd.get("race_margin")
    L.append("    RACE MARGIN " + (f"{m.get('frames')} frames, {m.get('ticks')} ticks, {m.get('s')} s" if m else
                                   "not measured") + " (127's last listed sample -> 128's readiness"
             + (f"; from {m.get('source')}" if m and m.get("source") else "") + ")")
    race = gd.get("race") or {}
    if race:
        L.append(f"    the ring's timeline: 127 last {race.get('marker_last')}, 128 first {race.get('choice_first')} "
                 f"ready {race.get('choice_ready')} ({race.get('samples')} ring samples read)")
    bp = gd.get("branch_page")
    L.append("    branch page after 128: " + (f"{bp.get('which')} at frame {bp.get('frame')} {bp.get('text')!r}" if bp
                                               else "none seen"))
    pub = gd.get("published") or {}
    c = gd.get("choice")
    L.append(f"    128 published: first at frame {pub.get('first_frame')}, {pub.get('snapshots')} snapshot(s), options "
             f"changed after readiness: {pub.get('changed_after_ready')}"
             + (f"; at readiness (frame {c.get('frame')}): {c.get('options')} active {c.get('active')} selected "
                f"{c.get('selected')} -> index {c.get('index')}, took {c.get('took')}" if c else "; no choice row"))
    for p in gd.get("choose") or ():
        L.append(f"    choose press seq {p.get('seq')} {p.get('button')}: accepted {p.get('accepted_frame')} down "
                 f"{p.get('down_frame')} selected_before {p.get('selected_before')} answer {p.get('answer')}")
    return L


def _trace_report(tr: dict) -> list:
    """The trace summary's lines (7.2; F4): the cuts, the registered keys, the unregistered, the crossings, the emitted
    rows per visit and the c rows, visit 3's first, the end cut's row, the residue, the masked counts, the failures,
    the forbidden hits."""
    if not tr:
        return ["    trace: none (untraced, or no rows)"]
    L = [f"    trace: start line {tr.get('start')}, end line {tr.get('end')} (end places {tr.get('end_places')}), "
         f"{tr.get('rows')} rows; SC {[x['new'] for x in tr.get('sc') or ()]}; FieldEntrance "
         f"{[x['new'] for x in tr.get('entrance') or ()]}",
         f"      residue before the start {tr.get('residue_before')}; after {tr.get('residue_after')}; other rows "
         f"before it {tr.get('pre_other')}"]
    for name, keys in (tr.get("registered") or {}).items():
        present = [k["what"] for k in keys if k["present"]]
        L.append(f"      {name}: {len(present)}/{len(keys)} present"
                 + (f"; present: {present[:4]}" if name in ("error_path", "forbidden_sites", "dead") and present else ""))
    L.append(f"      unregistered keys ({len(tr.get('unregistered') or [])}): {(tr.get('unregistered') or [])[:12]}")
    L.append(f"      crossings {tr.get('crossings')}; the end cut's row {tr.get('end_row')} (fld {tr.get('end_row_fld')})")
    pat = tr.get("pattern") or {}
    for i, v in enumerate(pat.get("visits") or (), 1):
        L.append(f"      visit {i}: {len(v)} emitted row(s) {[tuple(x) for x in v]}")
    L.append(f"      c rows {[tuple(x) for x in pat.get('counts') or ()]}; unjoined {pat.get('unjoined')}; visit 3's first "
             f"{tr.get('visit3_first')}")
    L.append(f"      masked {tr.get('masked')}; join failures {len(tr.get('failures') or [])}")
    for h in tr.get("forbidden") or ():
        L.append(f"      forbidden: {h['row']} {h['why']} -- " + (f"backed by {h['by']}" if h["backed"] else "unbacked"))
    return L


def rehearsal_report(run_dir) -> str:
    """``--rehearsal-report``: an o5_rehearse.py launch's ``o5_rehearsal.json`` (research/o5_design.md 7.2), stage by
    stage and run by run -- what each freeze item (7.3) is read from: the capabilities and the launch's readings
    (F10); per run its outcome, the walk (F1, F12, F15), the guard and 128 (F2, F3, F9), the dialog-section catch
    (F11), the KEYON pairs and the timed windows (F8), the evidence, the trace (F4), the end (F5, F7), R-WALK-VOID's
    stop (F7) and an untraced run's exceptions (F14); F-SMOKE's warps and twins (F13)."""
    run_dir = Path(run_dir)
    doc = json.loads((run_dir / REHEARSAL_FILE).read_text(encoding="utf-8"))
    L = [f"O5 rehearsals -- {run_dir.name}  (draft sha {str(doc.get('draft_sha256'))[:8]}; stages "
         f"{doc.get('stages_run')})"]
    L += [f"  {'PASS' if ok else 'FAIL'}  {what} -- {detail}" for ok, what, detail in doc.get("capabilities") or ()]
    launch = doc.get("launch") or {}
    if launch:
        L.append(f"  launch: settings {json.dumps(launch.get('settings'), sort_keys=True)}; engine "
                 f"{json.dumps(launch.get('engine'), sort_keys=True)}")
        for ok, what, detail in launch.get("checks") or ():
            L.append(f"  {'PASS' if ok else 'FAIL'}  {what} -- {detail}")
    if doc.get("stopped"):
        L.append(f"  STOPPED: {doc['stopped']}")
    L.append("")
    for name, recs in (doc.get("stages") or {}).items():
        stage = (doc.get("stage_defs") or {}).get(name, {})
        if stage.get("pairs"):
            L += _smoke_lines(name, stage, recs, (doc.get("twins") or {}).get(name))
            L.append("")
            continue
        L.append(f"== {name}: warp {stage.get('field')} {stage.get('entrance')} {stage.get('sc')} -> {stage.get('end')}"
                 + (" UNTRACED" if stage.get("untraced") else "")
                 + (f", walk_stop_x {stage.get('walk_stop_x')}" if stage.get("walk_stop_x") is not None else "")
                 + (f", overlay {stage.get('overlay')}" if stage.get("overlay") else "")
                 + f"  ({len(recs)} run(s)) -- settles: {stage.get('settles')}")
        for rec in recs:
            out = rec.get("outcome") or {}
            rate = rec.get("rate") or {}
            L.append(f"  run {rec.get('n')} ({rec.get('side', 'S')}): {out.get('end')} -- {out.get('why')}"
                     + (f" [{out.get('v')} {out.get('cell')} {out.get('by')}]" if out.get("v") else "")
                     + f"; beats {rec.get('beats')}; {rec.get('t1', 0) - rec.get('t0', 0):.0f}s; "
                     f"{rate.get('fps')} fps; trace {rec.get('trace_file')}")
            L.append(f"    grants: {len(rec.get('grants') or [])} (the stair's alone)")
            L += _walk_report(rec.get("walk") or {})
            L += _guard_report(rec.get("guard") or {})
            ct = rec.get("catch") or {}
            L.append(f"    dialog-section catch: {len(ct.get('caught') or [])} of {ct.get('samples')} samples "
                     f"{(ct.get('caught') or [])[:4]}")
            win = rec.get("windows") or {}
            for pair in win.get("pairs") or ():
                L.append(f"    pair {pair.get('texts')}: first seen -> gone {pair.get('s')} s (second -> gone "
                         f"{pair.get('s_after_second')} s), Confirms {pair.get('presses')}")
            for t in win.get("timed") or ():
                L.append(f"    timed window {t.get('text')!r:.60}: {t.get('ticks')} ticks listed, Confirms "
                         f"{t.get('presses')}")
            ev = rec.get("evidence") or {}
            L.append(f"    evidence: {len(ev.get('press') or [])} press row(s), {len(ev.get('forbidden') or [])} "
                     f"forbidden row(s), {len(ev.get('observed') or [])} observed row(s), {len(ev.get('input') or [])} "
                     f"input row(s)")
            npg = rec.get("no_progress") or {}
            L.append(f"    longest no-progress stretch: {npg.get('longest_s')}s at {npg.get('where')}")
            ws = rec.get("walk_stop", ...)
            if ws is not ...:
                L.append("    walk stop: " + ("never fired" if ws is None else
                                              f"frame {ws.get('frame')} at x {ws.get('x')} (<= {ws.get('x_stop')}), the "
                                              f"held-back steps {ws.get('steps')}; direction holds before it "
                                              f"{ws.get('holds_before')} (the walk had begun), after it "
                                              f"{ws.get('holds_after')} (there must be none)"))
            if not rec.get("traced", True):
                L.append(f"    untraced: exceptions since the warp {rec.get('exceptions')}; Memoria.log lines "
                         f"{len(rec.get('log_lines') or [])}")
            end = rec.get("end") or {}
            er = end.get("end_run") or {}
            L.append(f"    end: state {end.get('end_state')}; end_run " + ("ok" if er.get("ok") else f"FAILED {er.get('why')}")
                     + f", title {er.get('title')}, rows {[x.get('k') for x in er.get('how') or ()]}")
            L += _trace_report(rec.get("trace") or {})
        L.append("")
    return "\n".join(L)


# ======================================================================== the session and the CLI
def run(g) -> None:
    """The session (tools/play.py's entry): O5Segment.run."""
    return O5.run(g)


def main(argv=None) -> int:
    return O5.main(argv)


if __name__ == "__main__":
    sys.exit(main())
