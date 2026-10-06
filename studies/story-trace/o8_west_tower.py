"""THE STORY-WRITE TRACE, O8 -- STEINER UP THE WEST TOWER, A US SESSION: from a raw warp into 164 (the west tower's
first spiral, entrance 342, the scenario at 1190; EVT_ALEX1_AC_TOWER_L3) up the first spiral to P1 -- THE KNIGHT WAIT
there -- and up the second through THE PINCH into e2, 165 (the second spiral, its two stretches), 166 (the tower top:
six pages, FMV004 PLAYED OUT, Field(55)) to the arrival in REAL 55 at 110 on both sides -- stock against the alxc disc-1
chain O4 deployed, both sides played by one driver (studies/story-trace/PLAN.md, "O8"; the design:
research/o8_design.md).

    py tools/play.py studies/story-trace/o8_west_tower.py --label story-o8 --timeout 240
    py studies/story-trace/o8_west_tower.py --offline-check     # O4's build (the route members' pins, 31258 166 byte
                                                                # for byte with its RAW Field(55)), the keys (the
                                                                # start-scoped olds, the start reads with their races,
                                                                # the carried values DERIVED from O1-O7's frozen keys,
                                                                # the route pins and their scans, the heights, the raced
                                                                # end-state set from 55's bytes), block 3's text
                                                                # (strict) and 166's pages, the store census, the
                                                                # regions with their gates, the walks' goals (height-
                                                                # aware)
    py studies/story-trace/o8_west_tower.py --preflight         # the live install (read-only): all green, O4 deployed it
    py studies/story-trace/o8_west_tower.py --draft             # the draft predictions, as JSON
    py studies/story-trace/o8_west_tower.py --freeze            # write o8_predictions_v1.json (once: the lead, after
                                                                # the stock rehearsals)
    py studies/story-trace/o8_west_tower.py --analyse <run dir> # the analysis alone, on saved traces
    py studies/story-trace/o8_west_tower.py --rehearsal-report <run dir>   # an o8_rehearse.py launch, stage by stage

THE SIDES (o8_forks.json: O4's chain, reused -- nothing imported, built or deployed for O8):
  S  stock. Start: 164, entrance 342, SC 1190. End: the arrival in REAL 55.
  F  O4's twenty members 31240-31259 as deployed: member(164) 31256, member(165) 31257, member(166) 31258 -- read from
     O4's campaign.toml, never assumed -- and the end in REAL 55 too: 31258 is 166 byte for byte, its only Field() (e6
     t1 ip871) RAW, and MAPJUMP does no remap. So every F run crosses ONE declared SEAM, 31258 -> 55 (O8-SEAM); a real
     164, 165 or 166 on F is V19, a finding. O1's 31205 (member(55) of the tshp chain) is never entered.

THE ENTRY: New Game, the trace armed, then in field 70 a raw `warp <164 | 31256> 342 1190`: FOUR residue rows in field 70
(SC's two bytes, FieldEntrance's two: 342 is 0x0156), which the front cut sets aside and O8-START requires. Every run
first FORGETS the basis of every field it seeds (164, 165, 31256, 31257), so each judges its own first moves.

THE ROUTE: segment_drive.drive with two visit-scoped cells -- 164's WALK up the first spiral to P1, its arrival proven by
its HEIGHT (S20 ``at_y``), then THE KNIGHT WAIT (S21 ``wait_flag``: the watched Bit[3811] read 1, nothing pressed) and its
TRIGGER up the second spiral into e2, the door's evidence his height (S22 ``until {y_gt: 12000}``), at clearance 64 (THE
PINCH); 165's walk and trigger the same way -- then 166 with no control (rule 7 Confirms its six pages, rule 9 sleeps
through FMV004, played out) to the arrival in REAL 55. The run-wide input witness, the stop page, the skip net (O7's row
and the measured line's), and the observe hook (THE KNIGHT'S seat readings, FMV004's clock). No battle, choice or
naming. Control anywhere else is V4 (game) at its [place, sc, visit] cell.

THE ANALYSIS: each run cut at its start row (164's first write) and at its first row in an end PLACE (55, real on both
sides), digested and compared as O1-O7's; the O8 checks (research/o8_design.md 5.3) read the start (four residue rows),
no SC rung, the chain, the residue, the writes EXACTLY, the landing per side, THE SEAM (one, 31258 -> 55, its exit 166
e6 t1 ip863), THE WALKS (THE PAIRED-WALK LAW per visit window, the knight's ip230 exempt only in THE EXEMPT SPAN, every
seeded field's first move judged), THE ORDER (ip230 before e2's ip243, in the span), THE KNIGHT'S SEAT, THE MOVIE (FMV004
played out: no press, no skip dialog, its span at the rate measured inside it), the sink's emitted row pattern EXACTLY,
the masked regions, the state handed to 55 (Int16[2] and Byte[8] read from the trace: 55's prologue races both), and
every run's VOID classes by [place, sc, visit]. The predictions are frozen by the lead after the stock rehearsals
(o8_rehearse.py); until then --offline-check and --preflight read the draft.
"""
from __future__ import annotations

import copy
import json
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))

from ff9mapkit import storytrace as T                                   # noqa: E402
import o2_alexandria as A                                               # noqa: E402
import o3_prima_vista as P                                              # noqa: E402
import o4_castle as C4                                                  # noqa: E402
import o5_hallway as C5                                                 # noqa: E402
import o6_steiner as C6                                                 # noqa: E402
import o7_castle_walk as C7                                             # noqa: E402
import segment_drive as SD                                              # noqa: E402
import segment_trace as ST                                              # noqa: E402
from segment_trace import SIDES, cut_at_end, cut_at_start, members_of, place      # noqa: E402

PREDICTIONS = HERE / "o8_predictions_v1.json"
MANIFEST = HERE / "o8_forks.json"
SESSION_FILE = "o8_session.json"
REPORT_FILE = "o8_report.txt"
REHEARSAL_FILE = "o8_rehearsal.json"
#: O4's chain and build, reused (research/o8_design.md 0.1 #2, 6.4): nothing is imported, built or deployed for O8.
CHAIN_DIR = C4.CHAIN_DIR
BUILD_DIR = C4.BUILD_DIR
GAME = A.GAME
SESSION_LANG = "us"
#: The text block the route's members carry (EVENT_ID_TO_MES): block 3 for 150-167. O8 reads no other (55 is the end).
TEXT_BLOCK, TEXT_BLOCKS = 3, (3,)
#: THE ROUTE (research/o8_design.md 1.3): the three places a run visits, in order, and the end -- REAL 55 on both sides.
ROUTE = (164, 165, 166)
VISITS = ROUTE
END_FIELD = 55
#: The donors P-DONOR reads (6.2): the route's only -- 55 is the end, real on both sides, no member's donor (O7's
#: ``route_members`` raises for it: the research's harness gap 8).
ROUTE_DONORS = ROUTE
#: P-DONOR-LOG's donors (6.2): the route's and the end's.
LOG_DONORS = ROUTE + (END_FIELD,)
#: The stock fields P-STOCK and the fingerprint read (4.1).
STOCK_FIELDS = ROUTE + (END_FIELD,)
#: 4.13: O7's frozen 31 keys PLUS [Graphics] VSync "1" -- FMV004's wall time and the measured stretch rest on it (MBG.cs:217
#: asks SetTargetFPS(30), which vSyncCount 1 overrides: FPSManager.cs:41-48): 32.
SETTINGS = json.loads(json.dumps(C7.SETTINGS))
SETTINGS["Graphics"]["VSync"] = "1"
SETTINGS8 = SETTINGS
OVERRIDE70 = C4.OVERRIDE70
ENGINE = C4.ENGINE
DERIVED = C4.DERIVED
#: 1.3: Steiner's controller radius per place -- 164's 80 (DoEventCode.cs:1507-1508 makes SetObjectLogicalSize's 30 a 20
#: on 164, through EffectiveFieldId: 31256 too), 165's 120 (30 x 4).
ENGINE_RADII = {164: 80, 165: 120}
#: 4.5: the span O8-KEYS requires of every start-scoped old's ``after.run`` and the report renders from the predictions.
AFTER_RUN = "O1-O7"
#: The frozen predictions O8-KEYS composes THE CARRIED VALUES from, in segment order (4.5): O1 v4, O2-O7 v1.
PRIOR_SEGMENTS8 = C7.PRIOR_SEGMENTS + ("o7_predictions_v1.json",)
#: O7's frozen predictions: the start-scoped olds' ``after.old`` is read off its ``pattern`` (4.5).
O7_FROZEN = "o7_predictions_v1.json"
#: The raw warp's start (4.5): field 70's prologue values, the warp's SC and FieldEntrance 342.
START_VALUES8 = dict(C7.START_VALUES, **{"Global.Int16[2]": 342})
START_VALUES = START_VALUES8
#: The keys a rehearsal stage may lay over a table step, each refused by the freeze (7.1).
REHEARSAL_OVERLAYS8 = frozenset({"hold_stop", "page_stop", "flag_stop", "pinch_stop", "movie_stop", "movie_poke"})
#: THE STEP VOCABULARY (0.2 #17): every key a frozen table through O7 or ``steps_default`` carries, plus S20, S21 and
#: S23's -- O8-GOALS (g0) and the freeze refuse any other (``step_of`` passes an unknown key silently).
KNOWN_STEP_KEYS8 = frozenset(
    ("kind name goal start target until to expect sc wait_s then avoid closed_tris closed_floors beat attempts interrupts "
     "timeout_s confirm_s npcs overlay_ok immediate settle lunge_ticks tolerance min_depth exit_wait_s exit_slack climb "
     "clearance basis").split() + ["at_y", "wait_flag", "unstick"])
#: THE PINCH WINDOW (2.5, 7.2): 164 #1's narrowest stretch, in 164's frame, his PUBLISHED y (loop 1 crosses the same XZ
#: at ~5600-5900).
PINCH_WINDOW = {"place": 164, "x": [900.0, 1310.0], "z": [4460.0, 4600.0], "y": [10400.0, 11100.0]}
#: 4.9: the end-state targets 55's prologue rewrites at once -- typed for the draft; O8-KEYS (g) DERIVES them
#: (:func:`end_race8`) and the freeze refuses a draft that differs.
RACED8 = ("Global.Int16[2]", "Global.Byte[8]")
#: 4.9 (O8-KEYS (g); research/o8_design.md 11.4, the review's #3): THE ARRIVAL SCENE's targets -- what 55's own
#: functions store after its Main_Init on this arrival: e10 t1 ip568 / ip582 ``UInt16[0] := 1400`` (case 3; ip582
#: where SC <= 1400), once ``Map.Byte[24]`` reaches 3 -- e1 t1 (ip46 / ip76) advances it on the scene's
#: ``Map.Bit[231]`` handshakes, the first past e8 t1's WindowSync page 129 (case 1). Reachable on this arrival, so
#: never read live: SC 1190 at the cut rests on O8-NO-SC. Typed for the draft; O8-KEYS (g) DERIVES it
#: (:func:`end_proof8`: the candidates' other 55 stores reachable on this arrival, a Map variable held only where no
#: other function stores it) and the freeze refuses a draft that differs.
END_SCENE8 = {"Global.UInt16[0]": {"sites": [[10, 1, 568], [10, 1, 582]],
                                   "why": "55's own arrival scene: e10 t1's case 3 stores SC 1400 once Map.Byte[24] "
                                          "reaches 3 (e1 t1 advances it on the scene's Map.Bit[231] handshakes, the "
                                          "first past e8 t1's WindowSync page 129) -- reachable on this arrival, so "
                                          "never read live: SC 1190 at the cut rests on O8-NO-SC (no SC row through "
                                          "the cut)"}}
#: 4.9: the knight's talk's targets -- 0 since New Game and through O1-O7.
UNTOUCHED8 = ("Global.Bit[3851]", "Global.Bit[3792]", "Global.Bit[7211]", "Global.Int16[224]")
MASKED_TARGETS = C7.MASKED_TARGETS
PARTY_OPS = C7.PARTY_OPS
#: The words an A-START by a START READ opens with (why_void): VOID-ASYM (b) sets that reason aside.
START_READ = C7.START_READ
#: The words every A-MOVIE reason opens with (5.1): set aside by VOID-ASYM (b) -- the instrument's on either side.
MOVIE_SPAN = "the movie span"
#: The words every A-KNIGHT reason opens with (5.1): NOT set aside -- a whole side unread is an asymmetry.
KNIGHT_UNREAD = "the knight's seat unread"
NEWGAME_FIELD = 70
#: Each step's height band (2.4: PSX y, up negative) -- its closures every open triangle whose centroid lies outside it.
BANDS8 = {(164, 0): (-9500, -4700), (164, 1): (-13100, -8700), (165, 0): (-11800, -9500), (165, 1): (-16000, -11000)}
#: 2.4: the four steps' band closures as typed (O8-GOALS (g0) DERIVES each from its band, :func:`band_closures`, on the
#: stock mesh): 93, 99, 64 and 16 (C0).
CLOSURES8 = {
    (164, 0): [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 29, 39, 40, 41,
               42, 44, 54, 55, 56, 57, 58, 59, 73, 74, 75, 80, 81, 84, 85, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104,
               105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125,
               126, 127, 128, 129, 130, 131, 132, 133, 134, 136, 137, 138, 139, 142, 151, 154, 163],
    (164, 1): [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 43, 44, 45, 60, 61,
               62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95, 96, 97,
               98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149,
               150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169],
    (165, 0): [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30,
               31, 34, 35, 36, 38, 39, 40, 44, 45, 46, 47, 49, 51, 52, 53, 55, 60, 61, 64, 65, 66, 67, 68, 69, 70, 71, 72,
               74, 75, 76, 78, 79, 80, 83],
    (165, 1): [20, 27, 32, 33, 37, 41, 42, 43, 48, 54, 55, 56, 57, 58, 59, 63]}
_MODULE_DOC = __doc__


# ======================================================================== the chain (O4's campaign.toml)
def chain_from_campaign(campaign=None) -> tuple:
    """``({fork id: donor}, {fork id: member name})`` of O4's built alxc chain (its ``campaign.toml``; default O4's):
    its donors exactly O4's twenty (o4_castle.chain_from_campaign refuses another chain)."""
    return C4.chain_from_campaign(Path(campaign) if campaign is not None else CHAIN_DIR / "campaign.toml")


def route_members8(members: dict, donors=ROUTE_DONORS) -> dict:
    """``{donor: fork id}`` for each ROUTE donor (164, 165, 166): the members the route runs. Never the end: 55 is real
    on both sides, and O1's 31205 forks it in another chain (O7's ``route_members`` over the route, 1.3)."""
    return C7.route_members(members, donors)


def route_members_line(members: dict, donors=ROUTE_DONORS) -> str:
    """The line --offline-check and --draft print: ``member(164) 31256, member(165) 31257, member(166) 31258``."""
    rm = route_members8(members, donors)
    return ", ".join(f"member({d}) {rm[d]}" for d in donors)


#: The instancing at a route entrance (0.2 #3): no entrance dispatch in 164-166's Main_Init -- O7's over-approximation.
instanced_at8 = C7.instanced_at7


# ======================================================================== the predictions (draft v1)
def _key(donor, sid, tag, ip, off, target, value, op, what, prior=None) -> dict:
    return A._key(donor, sid, tag, ip, off, target, value, op, what, prior)


def _site(place_, sid, tag, ip, target, value, **kw) -> dict:
    return C4._site(place_, sid, tag, ip, target, value, **kw)


def _ambient8(donor: int) -> list:
    """Each Main_Init's ambient four (e0 t0, its function at ip6): Int16[9] := K (385 in 164 and 165, -1 in 166), the
    Byte[13] branch it takes (ip130 := 1 under K 385, ip119 := 0 under K -1), Int16[11] := -1, Byte[14] := 0."""
    k9 = 385 if donor in (164, 165) else -1
    b13 = (130, 1) if k9 >= 0 else (119, 0)
    whys = {164: "ambient (from 643: START-SCOPED old)", 165: "ambient (same)", 166: "ambient (K -1)"}
    return [_key(donor, 0, 0, 57, 51, "Global.Int16[9]", k9, ":=", f"{donor} Int16[9] := {k9} ({whys[donor]})"),
            _key(donor, 0, 0, b13[0], b13[0] - 6, "Global.Byte[13]", b13[1], ":=",
                 f"{donor} Byte[13] := {b13[1]} (ambient: Int16[9] {'<' if k9 < 0 else '>='} 0"
                 + {164: "; from 1: start_music, START-SCOPED old, THE LATE-EDGE START READ)", 165: "; from 2)",
                    166: "; from 3)"}[donor]),
            _key(donor, 0, 0, 138, 132, "Global.Int16[11]", -1, ":=", f"{donor} Int16[11] := -1 (ambient)"),
            _key(donor, 0, 0, 200, 194, "Global.Byte[14]", 0, ":=", f"{donor} Byte[14] := 0 (ambient)")]


def _writes8() -> list:
    """4.4's registered writes, in route order: 20 keys."""
    key = _key
    return (_ambient8(164) + [
        key(164, 0, 0, 764, 758, "Global.Byte[13]", 2, ":=", "164 Byte[13] := 2 (the grant's pass)"),
        key(164, 1, 1, 230, 70, "Global.Bit[3811]", 1, ":=", "164 e1 t1 Bit[3811] := 1 (THE KNIGHT sits: inside THE "
                                                             "EXEMPT SPAN, before ip243 -- O8-ORDER)")]
            + _ambient8(165) + [
        key(165, 0, 0, 844, 838, "Global.Byte[13]", 2, ":=", "165 Byte[13] := 2 (the grant's pass)"),
        key(165, 2, 2, 205, 175, "Global.Byte[13]", 3, ":=", "165 e2 t2 Byte[13] := 3 (e2, LIVE: 165's e2 sets no "
                                                             "Map.Bit[162])")]
            + _ambient8(166) + [
        key(166, 0, 0, 255, 249, "Global.Byte[8]", 125, ":=", "166 Byte[8] := 125 (same: field 70 left 125 -- THE "
                                                              "EARLY-EDGE START READ, 4.5)"),
        key(166, 6, 1, 345, 71, "Global.Byte[208]", 0, ":=", "166 e6 t1 Byte[208] := 0 (under page 309; START-SCOPED "
                                                             "old)"),
        key(166, 6, 1, 380, 106, "Global.Byte[208]", 1, "++", "166 e6 t1 Byte[208] ++ (one loop pass: ip385 Byte[208] < "
                                                              "1)", "166/6/1/345"),
        key(166, 6, 1, 502, 228, "Global.Byte[8]", 0, ":=", "166 e6 t1 Byte[8] := 0 (after page 313: the last store "
                                                            "before FMV004 -- MOVIE's span opens; the end state's "
                                                            "Byte[8])")])


#: 4.3: THE FIELDENTRANCE CHAIN, each place's door store before its Field().
CHAIN_SITES = {164: (2, 2, 243, 209, 343, "e2 at the top, then Field(165) ip251 (31257 on F)"),
               165: (2, 2, 233, 203, 344, "e2 at the top, then Field(166) ip241 (31258 on F)"),
               166: (6, 1, 863, 589, 110, "after FMV004, then Field(55) ip871, RAW on F -- the last compared row, THE "
                                          "SEAM's exit row on F")}


def _chain8() -> list:
    return [_key(p, sid, tag, ip, off, "Global.Int16[2]", v, ":=", f"FieldEntrance {v}: {p} {why}")
            for p in ROUTE for sid, tag, ip, off, v, why in [CHAIN_SITES[p]]]


def _error_path8() -> list:
    """4.6: the error path -- Byte[13] := 9 / Byte[14] := 9 on an incoming 2 with Int16[9] / Int16[11] < 0 WHERE THAT
    GUARD CAN HOLD, and window 56's two resets := 0 on an incoming 9: 10 sites (O8-CENSUS proves each reachable)."""
    rows = [(164, 178, "Global.Byte[14]", 9), (164, 607, "Global.Byte[13]", 0), (164, 641, "Global.Byte[14]", 0),
            (165, 178, "Global.Byte[14]", 9), (165, 687, "Global.Byte[13]", 0), (165, 721, "Global.Byte[14]", 0),
            (166, 97, "Global.Byte[13]", 9), (166, 178, "Global.Byte[14]", 9), (166, 332, "Global.Byte[13]", 0),
            (166, 366, "Global.Byte[14]", 0)]
    return [_key(d, 0, 0, ip, ip - 6, t, v, ":=", f"{d} e0 t0 ip{ip}: the error path ({t} := {v})")
            for d, ip, t, v in rows]


def _forbidden_sites8() -> list:
    """4.6: what the knight's talk, the talk's own scripts and a back door write: 7 sites (as built: 4.6's eighth, the
    talk's e1 t3 ip690 Int16[224] := -761, is DEAD -- :func:`_dead8`)."""
    key = _key
    return [key(164, 1, 3, 308, 49, "Global.Bit[3851]", 1, ":=", "164 e1 t3 Bit[3851] := 1 (the knight's talk)"),
            key(164, 1, 3, 420, 161, "Global.Bit[3792]", 1, ":=", "164 e1 t3 Bit[3792] := 1 (the knight's talk)"),
            key(164, 1, 3, 627, 368, "Global.Bit[7211]", 1, ":=", "164 e1 t3 Bit[7211] := 1 (the knight's talk)"),
            key(164, 7, 11, 399, 16, "Global.Byte[208]", 0, ":=", "164 e7 t11 Byte[208] := 0 (RunScriptSync(4, 250, 11) "
                                                                  "at e1 t3 ip415: the talk's)"),
            key(164, 7, 11, 434, 51, "Global.Byte[208]", 1, "++", "164 e7 t11 Byte[208] ++ (the talk's)",
                "164/7/11/399"),
            key(164, 3, 2, 243, 209, "Global.Int16[2]", 343, ":=", "164 e3 t2 Int16[2] := 343 (the back door -> 163)"),
            key(165, 3, 2, 243, 209, "Global.Int16[2]", 344, ":=", "165 e3 t2 Int16[2] := 344 (the back door -> 164)")]


def _dead8() -> list:
    """4.6: the dead sites, each with why: 15 (as built: 4.6's 14 and the talk's ip690, which O8-CENSUS's reach proof
    finds behind two constant tests -- ip641 / ip663 ``SET({const(1) B_EXPR_END})``, bytes ``05 7d 01 00 7f``: the
    AddGil branch is never taken)."""
    key = _key
    out = []
    for d in ROUTE:
        out.append(key(d, 0, 0, 41, 35, "Global.Int16[2]", 10000, ":=", f"{d} Int16[2] := 10000 (dead: Bit[184] == 1, "
                                                                         f"it is 0)"))
        if d in (164, 165):
            out.append(key(d, 0, 0, 97, 91, "Global.Byte[13]", 9, ":=", f"{d} Byte[13] := 9 (dead: ip57 just set "
                                                                        f"Int16[9] 385, so ip79's Int16[9] < 0 never "
                                                                        f"holds)"))
            out.append(key(d, 0, 0, 119, 113, "Global.Byte[13]", 0, ":=", f"{d} Byte[13] := 0 (dead: Int16[9] 385 is "
                                                                          f"not < 0)"))
        else:
            out.append(key(d, 0, 0, 130, 124, "Global.Byte[13]", 1, ":=", f"{d} Byte[13] := 1 (dead: Int16[9] just set "
                                                                          f"-1)"))
        out.append(key(d, 0, 0, 211, 205, "Global.Byte[14]", 1, ":=", f"{d} Byte[14] := 1 (dead: Int16[11] just set "
                                                                      f"-1)"))
    for d, sid in ((164, 2), (164, 3), (165, 3)):
        out.append(key(d, sid, 2, 215, 181, "Global.Byte[13]", 3, ":=",
                       f"{d} e{sid} t2 Byte[13] := 3 (dead: behind Map.Bit[162] == 0 at ip193, which its own ip54 "
                       f"set 1 first)"))
    out.append(key(164, 1, 3, 690, 431, "Global.Int16[224]", -761, ":=",
                   "164 e1 t3 Int16[224] := -761 (dead: the talk's AddGil branch, behind ip641's and ip663's const(1) "
                   "tests -- never taken)"))
    return out


def start_scoped8() -> list:
    """4.5: THE START-SCOPED OLDS -- three writes keys whose VALUE is the start's and a true O1-O7 run's alike, whose
    ``old`` / ``same`` differ: ``here`` [old, new] from the raw start, ``after`` from a true run (``after.old`` the new of
    the LAST tuple on the target in O7's FROZEN pattern -- O8-KEYS reads it off the file)."""
    src = "old: the last pre-cut tuple on the target in o7_predictions_v1.json's pattern ({}); {}"
    return [{"site": [164, 0, 0, 57], "target": "Global.Int16[9]", "here": [643, 385],
             "after": {"run": AFTER_RUN, "old": 385, "value": 385,
                       "source": src.format("163 e0 t0 ip57, 385", "story-o7's six runs read 164 ip57 385 -> 385 past "
                                                                   "the cut")}},
            {"site": [164, 0, 0, 130], "target": "Global.Byte[13]", "here": [1, 1],
             "after": {"run": AFTER_RUN, "old": 2, "value": 1,
                       "source": src.format("163 e0 t0 ip684, 2", "story-o7: 164 ip130 2 -> 1 past the cut")}},
            {"site": [166, 6, 1, 345], "target": "Global.Byte[208]", "here": [0, 0],
             "after": {"run": AFTER_RUN, "old": 1, "value": 0,
                       "source": src.format("159 e16 t1 ip648, 1", "no 166 row in story-o7 (O7 ends in 164)")}}]


def start_reads8() -> list:
    """4.5 (critique #2): THE START READS, EACH WITH ITS RACE -- ``race`` the field-70 store the warp window races,
    ``race_value`` its stored value, ``edge`` which side of it the warp must fall."""
    return [{"site": [166, 0, 0, 255], "target": "Global.Byte[8]", "old": 125, "race": [70, 0, 0, 249],
             "race_value": 125, "edge": "before",
             "why": "field 70 e0 t0 ip249 Byte[8] := 125 lies inside the warp window (after ip130, behind ip238-246's "
                    "SYSVAR[3] wait, before ip475): a warp before it leaves 0, and this store -- the route's first on "
                    "Byte[8] (164 and 165 neither store nor read it) -- reads 0 (O7's 159 ip290 rule)"},
            {"site": [164, 0, 0, 130], "target": "Global.Byte[13]", "old": 1, "race": [70, 0, 0, 475],
             "race_value": 2, "edge": "after",
             "why": "field 70 e0 t0 ip475 Byte[13] := 2 closes the warp window: a warp after it reaches 164 with "
                    "Byte[13] 2 and 164 takes NO error path (K 385: ip97 needs Int16[9] < 0), so this store reads 2 "
                    "SILENTLY -- registered so the late race is A-START, never NOT PROVEN by START (c) or PATTERN "
                    "(research dispute 9)"}]


def carried8_typed() -> dict:
    """4.5: THE CARRIED VALUES as typed (O8-KEYS DERIVES them from the frozen O1-O7 keys, :func:`carried8`, and refuses
    a typed set that differs); the party typed and labelled, never derived (no gEventGlobal target)."""
    return {"why": "a true O1-O7 run's value (composed over the frozen O1-O7 keys in segment order) where the raw start "
                   "holds 0; neither written nor read by any function the route runs in 164@342, 165@343, 166@344 (the "
                   "knight's TALK -- 164 e1 t3 and what only it reaches, e7 t11/t12 -- set aside: never driven, its "
                   "stores forbidden)",
            "values": {"Global.Bit[3717]": [0, 1], "Global.Bit[3718]": [0, 1], "Global.Bit[3795]": [0, 1],
                       "Global.Bit[3796]": [0, 1], "Global.Bit[3815]": [0, 1], "Global.Bit[3854]": [0, 1],
                       "Global.Bit[3855]": [0, 1], "Global.Byte[18]": [0, 1], "Global.Byte[303]": [0, 1],
                       "Global.Byte[472]": [0, 4], "Global.Byte[475]": [0, 100], "Global.Byte[6]": [0, 11],
                       "Global.Int16[469]": [0, 1042], "Global.UInt16[19]": [0, 1807], "Global.UInt16[21]": [0, 8]},
            "party": {"values": ["[Zidane]", "[Steiner]"],
                      "source": "not a gEventGlobal target: New Game's party; 153 e32 t1's rebuild (O6, UInt16[21] := 8) "
                                "-- typed, labelled, never derived; no party op runs in 164-166, and Steiner is the "
                                "controlled character on both sides (164 e7 ip325, 165 e7 ip317, 166 e6 ip262)"}}


#: 4.15: the route's exits, each the FIRST SetRegion of its (donor, entry) in the engine's point order (IsInQuad: a ring
#: of ears), with the GATE read off its pinned tag 2's height test AND its consuming jump (O8-REGIONS (c)).
E164_2 = [[946, 2249], [1122, 1974], [222, 2039], [-25, 2186], [93, 2401]]
E164_3 = [[938, 3257], [1051, 2471], [2066, 2776], [2233, 2840], [1738, 3462]]
E165_2 = [[3298, 3179], [3241, 2829], [2401, 3074], [2494, 3428]]
E165_3 = [[1209, 2668], [1437, 2069], [2169, 2636], [2395, 3155], [1780, 3363]]


def _regions8() -> dict:
    ex = A._exit
    return {
        "164.e2": ex(E164_2, 165, 343, None, gate={"y_gt": 12000},
                     why="e2 at the top: tag 2 ip42 f[1] < -12000 (y > 12000), ip51 JMP_IFNOT to its RET; ip243 Int16[2] "
                         ":= 343, Field(165) -- a ring of ears, its centroid (472, 2170) dead"),
        "164.e3": ex(E164_3, 163, 343, None, gate={"y_lt": 6000},
                     why="the back door, LIVE 157 u from the spawn on loop 1: tag 2 ip42 f[1] > -6000 (y < 6000); ip243 "
                         ":= 343, Field(163)"),
        "165.e2": ex(E165_2, 166, 344, None, gate={"y_gt": 15000},
                     why="e2 at the top: tag 2 ip38 f[1] < -15000 (y > 15000), ip47 JMP_IFNOT to its RET; ip205 Byte[13] "
                         ":= 3, ip233 Int16[2] := 344, Field(166)"),
        "165.e3": ex(E165_3, 164, 344, None, gate={"y_lt": 11000},
                     why="the back door, LIVE 133.6 u from the spawn: tag 2 ip42 f[1] > -11000 (y < 11000); ip243 := 344, "
                         "Field(164)")}


def _table8(closures=None) -> list:
    """2.4's two visit-scoped cells. ``closures``: the four steps' band closures (default the typed
    :data:`CLOSURES8`; O8-GOALS (g0) derives them from their bands)."""
    cl = closures if closures is not None else CLOSURES8
    cells = {
        164: [{"kind": "walk", "name": "164: the first spiral to P1, then THE KNIGHT WAIT", "goal": [1342, 2252],
               "start": [2040, 3335], "at_y": [8800, 9150], "wait_flag": {"flag": 3811, "value": 1, "timeout_s": 15},
               "avoid": ["164.e3"], "closed_tris": list(cl[(164, 0)]), "clearance": 80, "basis": "prior",
               "npcs": False, "attempts": 3, "beat": "w164_p1"},
              {"kind": "trigger", "name": "164: the second spiral into e2 at the top", "goal": [59, 2214], "to": 165,
               "start": [1342, 2252], "until": {"y_gt": 12000}, "avoid": [], "closed_tris": list(cl[(164, 1)]),
               "clearance": 64, "npcs": True, "attempts": 3, "beat": "t164_e2"}],
        165: [{"kind": "walk", "name": "165: the lower stretch to P1", "goal": [1508, 4698], "start": [2055, 3411],
               "at_y": [11100, 11450], "avoid": ["165.e3"], "closed_tris": list(cl[(165, 0)]), "clearance": 120,
               "basis": "prior", "npcs": True, "beat": "w165_p1"},
              {"kind": "trigger", "name": "165: the upper stretch into e2 at the top", "goal": [2489, 3166], "to": 166,
               "start": [1508, 4698], "until": {"y_gt": 15000}, "avoid": [], "closed_tris": list(cl[(165, 1)]),
               "clearance": 120, "npcs": True, "beat": "t165_e2"}]}
    return [{"donor": p, "sc": 1190, "visit": i + 1, "steps": copy.deepcopy(cells[p])}
            for i, p in enumerate((164, 165))]


def route_pins8() -> list:
    """4.14's route pins: ``[donor, sid, tag, ip, eb-src text]`` -- the bytes the driver, the walks, the knight, the
    movie, the seam, the start and the FakeGame rest on, each compared EXACTLY with the stock US script's instruction
    text (O8-KEYS (e)); every height test pinned WITH its consuming jump (the claim review's #7, 0.2 #24)."""
    sw = "SET({Global.Int16[2] const(%d) B_LET B_EXPR_END})"
    lt = "SET({obj(uid=250).f[1] const(%d) B_LT B_EXPR_END})"
    gt = "SET({obj(uid=250).f[1] const(%d) B_GT B_EXPR_END})"
    win56 = "WindowAsync(6, 0, 56)"
    mxzy = "MoveInstantXZY({obj(uid=255).f[0] B_EXPR_END}, {Map.Int16[2] B_EXPR_END}, {obj(uid=255).f[2] B_EXPR_END})"
    pins = [[164, 0, 0, 22, "SET({Global.Bit[191] const(0) B_LET B_EXPR_END})"],
            [164, 0, 0, 57, "SET({Global.Int16[9] const(385) B_LET B_EXPR_END})"],
            [164, 0, 0, 130, "SET({Global.Byte[13] const(1) B_LET B_EXPR_END})"],
            [164, 0, 0, 219, "SetControlDirection(40, 40)"], [164, 0, 0, 223, "InitObject(7, 0)"],
            [164, 0, 0, 226, "InitObject(1, 0)"], [164, 0, 0, 229, "InitRegion(2, 0)"],
            [164, 0, 0, 232, "InitRegion(3, 0)"], [164, 0, 0, 597, win56], [164, 0, 0, 631, win56],
            [164, 0, 0, 649, "SET({Map.Bit[159] const(1) B_LET B_EXPR_END})"],
            [164, 0, 0, 657, "SET({Map.Bit[158] const(1) B_EQ B_EXPR_END})"],
            [164, 0, 0, 676, "SET({Map.Bit[159] const(1) B_EQ B_EXPR_END})"],
            [164, 0, 0, 687, "SET({Map.Bit[156] const(0) B_EQ B_EXPR_END})"], [164, 0, 0, 698, "EnableMove()"],
            [164, 0, 0, 764, "SET({Global.Byte[13] const(2) B_LET B_EXPR_END})"],
            [164, 7, 0, 22, "SWITCH(344, L47, L12)"],
            [164, 7, 0, 65, "SET({Map.Int16[0] const(2040) B_LET B_EXPR_END})"],
            [164, 7, 0, 73, "SET({Map.Int16[4] const(3335) B_LET B_EXPR_END})"],
            [164, 7, 0, 89, "SET({Map.Int16[2] const(59889) B_LET B_EXPR_END})"],
            [164, 7, 0, 100, "SetModel(5489, 104)"], [164, 7, 0, 138, "SetObjectLogicalSize(30, 35, 50)"],
            [164, 7, 0, 153, mxzy], [164, 7, 0, 325, "DefinePlayerCharacter()"],
            [164, 7, 0, 326, "SET({Map.Bit[158] const(1) B_LET B_EXPR_END})"], [164, 7, 0, 356, "EnableMove()"],
            [164, 1, 0, 14, "SET({Map.Int16[0] const(249) B_LET B_EXPR_END})"],
            [164, 1, 0, 22, "SET({Map.Int16[4] const(4630) B_LET B_EXPR_END})"],
            [164, 1, 0, 46, "SET({Global.Bit[3811] B_EXPR_END})"],
            [164, 1, 0, 124, "SetObjectLogicalSize(20, 20, 30)"],
            [164, 1, 1, 160, "SET({Global.Bit[3811] const(0) B_EQ B_EXPR_END})"], [164, 1, 1, 175, "op_22(1)"],
            [164, 1, 1, 178, gt % 57136], [164, 1, 1, 187, "JMP_IF(L15)"], [164, 1, 1, 190, "SetWalkSpeed(15)"],
            [164, 1, 1, 194, "Walk(65505, 4436)"], [164, 1, 1, 201, "Walk(65290, 4288)"],
            [164, 1, 1, 208, "Walk(65127, 4128)"], [164, 1, 1, 215, "Walk(64950, 3884)"],
            [164, 1, 1, 225, "RunAnimation(9920)"],
            [164, 1, 1, 230, "SET({Global.Bit[3811] const(1) B_LET B_EXPR_END})"],
            [164, 1, 3, 415, "RunScriptSync(4, 250, 11)"], [164, 1, 3, 452, "RunScriptSync(4, 250, 12)"],
            [164, 2, 0, 10, "SetRegion(147391410, 129369186, 133628126, 143327207, 157352029)"],
            [164, 2, 2, 34, "SET({B_SYSVAR[2] B_EXPR_END})"], [164, 2, 2, 42, lt % 53536],
            [164, 2, 2, 51, "JMP_IFNOT(L221)"], [164, 2, 2, 54, "SET({Map.Bit[162] const(1) B_LET B_EXPR_END})"],
            [164, 2, 2, 71, "ExitField()"], [164, 2, 2, 165, "op_22(25)"],
            [164, 2, 2, 193, "SET({Map.Bit[162] const(0) B_EQ B_EXPR_END})"], [164, 2, 2, 243, sw % 343],
            [164, 2, 2, 251, "Field(165)"], [164, 2, 2, 255, "RET()"],
            [164, 3, 0, 10, "SetRegion(213451690, 161940507, 181930002, 186124473, 226887370)"],
            [164, 3, 2, 42, gt % 59536], [164, 3, 2, 51, "JMP_IFNOT(L221)"],
            [164, 3, 2, 54, "SET({Map.Bit[162] const(1) B_LET B_EXPR_END})"],
            [164, 3, 2, 193, "SET({Map.Bit[162] const(0) B_EQ B_EXPR_END})"], [164, 3, 2, 243, sw % 343],
            [164, 3, 2, 251, "Field(163)"], [164, 3, 2, 255, "RET()"]]
    pins += [[165, 0, 0, 130, "SET({Global.Byte[13] const(1) B_LET B_EXPR_END})"],
             [165, 0, 0, 219, "SetControlDirection(24, 24)"], [165, 0, 0, 223, "InitCode(1, 0)"],
             [165, 0, 0, 226, "InitObject(7, 0)"], [165, 0, 0, 229, "InitRegion(2, 0)"],
             [165, 0, 0, 232, "InitRegion(3, 0)"], [165, 0, 0, 677, win56], [165, 0, 0, 711, win56],
             [165, 0, 0, 778, "EnableMove()"], [165, 0, 0, 844, "SET({Global.Byte[13] const(2) B_LET B_EXPR_END})"],
             [165, 7, 0, 14, "SWITCH(345, L47, L12)"],
             [165, 7, 0, 57, "SET({Map.Int16[0] const(2055) B_LET B_EXPR_END})"],
             [165, 7, 0, 65, "SET({Map.Int16[4] const(3411) B_LET B_EXPR_END})"],
             [165, 7, 0, 81, "SET({Map.Int16[2] const(55017) B_LET B_EXPR_END})"],
             [165, 7, 0, 92, "SetModel(5489, 104)"], [165, 7, 0, 130, "SetObjectLogicalSize(30, 35, 50)"],
             [165, 7, 0, 145, mxzy], [165, 7, 0, 317, "DefinePlayerCharacter()"],
             [165, 2, 0, 10, "SetRegion(208342242, 185404585, 201460065, 224659902)"],
             [165, 2, 2, 38, lt % 50536], [165, 2, 2, 47, "JMP_IFNOT(L215)"], [165, 2, 2, 61, "ExitField()"],
             [165, 2, 2, 62, "SET({Map.Bit[158] const(0) B_LET B_EXPR_END})"], [165, 2, 2, 155, "op_22(25)"],
             [165, 2, 2, 183, "SET({Map.Bit[162] const(0) B_EQ B_EXPR_END})"],
             [165, 2, 2, 205, "SET({Global.Byte[13] const(3) B_LET B_EXPR_END})"], [165, 2, 2, 233, sw % 344],
             [165, 2, 2, 241, "Field(166)"], [165, 2, 2, 245, "RET()"],
             [165, 3, 0, 10, "SetRegion(174851257, 135595421, 172755065, 206768475, 220399348)"],
             [165, 3, 2, 42, gt % 54536], [165, 3, 2, 51, "JMP_IFNOT(L221)"],
             [165, 3, 2, 54, "SET({Map.Bit[162] const(1) B_LET B_EXPR_END})"],
             [165, 3, 2, 193, "SET({Map.Bit[162] const(0) B_EQ B_EXPR_END})"], [165, 3, 2, 243, sw % 344],
             [165, 3, 2, 251, "Field(164)"], [165, 3, 2, 255, "RET()"]]
    pins += [[166, 0, 0, 57, "SET({Global.Int16[9] const(65535) B_LET B_EXPR_END})"],
             [166, 0, 0, 119, "SET({Global.Byte[13] const(0) B_LET B_EXPR_END})"],
             [166, 0, 0, 219, "SetControlDirection(64, 64)"], [166, 0, 0, 223, "InitObject(6, 0)"],
             [166, 0, 0, 226, "InitObject(3, 0)"], [166, 0, 0, 229, "InitObject(5, 0)"],
             [166, 0, 0, 244, "SET({B_SYSVAR[3] const(0) B_NE B_EXPR_END})"],
             [166, 0, 0, 255, "SET({Global.Byte[8] const(125) B_LET B_EXPR_END})"],
             [166, 0, 0, 322, win56], [166, 0, 0, 356, win56],
             [166, 0, 0, 382, "SET({Map.Bit[158] const(1) B_EQ B_EXPR_END})"], [166, 0, 0, 423, "EnableMove()"],
             [166, 6, 0, 42, "SetModel(5489, 104)"], [166, 6, 0, 80, "SetObjectLogicalSize(30, 35, 50)"],
             [166, 6, 0, 262, "DefinePlayerCharacter()"],
             [166, 6, 1, 278, "SWITCH(0, L659, L12)"], [166, 6, 1, 310, "WindowSync(0, 128, 307)"],
             [166, 6, 1, 328, "WindowSync(0, 128, 308)"], [166, 6, 1, 334, "WindowAsync(0, 128, 309)"],
             [166, 6, 1, 345, "SET({Global.Byte[208] const(0) B_LET B_EXPR_END})"],
             [166, 6, 1, 380, "SET({Global.Byte[208] B_POST_PLUS B_EXPR_END})"], [166, 6, 1, 401, "WaitWindow(0)"],
             [166, 6, 1, 454, "WindowSync(0, 128, 311)"], [166, 6, 1, 474, "WindowSync(0, 128, 312)"],
             [166, 6, 1, 489, "RunSharedScript(2)"], [166, 6, 1, 492, "WindowSync(0, 128, 313)"],
             [166, 6, 1, 498, "StopSharedScript()"],
             [166, 6, 1, 502, "SET({Global.Byte[8] const(0) B_LET B_EXPR_END})"],
             [166, 6, 1, 609, "SET({B_SYSVAR[15] const(128) B_AND const(0) B_EQ B_EXPR_END})"],
             [166, 6, 1, 633, "Cinematic(0, 9, 1, 1)"], [166, 6, 1, 711, "Cinematic(2, 0, 0, 0)"],
             [166, 6, 1, 756, "SET({B_SYSVAR[15] const(127) B_AND const(1) B_NE B_EXPR_END})"],
             [166, 6, 1, 863, sw % 110], [166, 6, 1, 871, "Field(55)"]]
    pins += [[55, 0, 0, 22, "SET({Global.Bit[191] const(0) B_LET B_EXPR_END})"],
             [55, 0, 0, 229, "SET({Global.UInt16[0] const(1400) B_LT Global.Int16[2] const(106) B_EQ B_OROR "
                             "B_EXPR_END})"],
             [55, 0, 0, 255, "SET({Global.Int16[2] const(106) B_LET B_EXPR_END})"],
             [55, 0, 0, 331, "SET({B_SYSVAR[3] const(0) B_NE B_EXPR_END})"],
             [55, 0, 0, 342, "SET({Global.Byte[8] const(125) B_LET B_EXPR_END})"], [55, 0, 0, 387, "op_22(2)"]]
    pins += [[70, 0, 0, 130, "SET({Global.Byte[13] const(1) B_LET B_EXPR_END})"],
             [70, 0, 0, 238, "SET({B_SYSVAR[3] const(0) B_NE B_EXPR_END})"], [70, 0, 0, 246, "JMP_IF(L229)"],
             [70, 0, 0, 249, "SET({Global.Byte[8] const(125) B_LET B_EXPR_END})"],
             [70, 0, 0, 475, "SET({Global.Byte[13] const(2) B_LET B_EXPR_END})"]]
    return pins


#: 6.1 / C0: O8-BUILD's route pins, measured read-only on O4's build: each route member's in-chain ``Field()`` sites
#: ``[sid, tag, ip, literal]`` (US ips; the same in all 7 languages) -- "166" LISTED with none, so its member must equal
#: it byte for byte (o5_hallway.build_pins: with no in-chain operand every differing byte fails).
BUILD_FIELDS8 = {"164": [[2, 2, 251, 165], [3, 2, 251, 163]], "165": [[2, 2, 241, 166], [3, 2, 251, 164]], "166": []}
#: 6.1: THE RAW EXITS -- each ``[sid, tag, ip, literal]`` a ``Field()`` the member keeps RAW (no member forks it): 31258's
#: e6 t1 ip871 Field(55).
RAW_EXITS8 = {"166": [[6, 1, 871, 55]]}


def route_build8() -> dict:
    """O8-BUILD's route pins (6.1): C0's measurement on O4's build, and the raw exits."""
    return {"fields": copy.deepcopy(BUILD_FIELDS8), "raw_exits": copy.deepcopy(RAW_EXITS8),
            "why": "C0 (research/o8_design.md 9 PART C), read-only on O4's build C:/gd/_ns_playtest/o4/build: per "
                   "language, 31256 and 31257 differ from 164 and 165 only in their 2 in-chain Field() operands each (4 "
                   "bytes a file), 31258 is 166 byte for byte with e6 t1 ip871 Field(55) raw -- 21 member files "
                   "(o8_forks.json built.measured)"}


def route_mes8() -> dict:
    """4.14's ``route_mes`` (block 3, US: the asset the engine reads): 166's six pages and the stop page (O8-TEXT)."""
    return {"block": TEXT_BLOCK, "pages": [{"mes": m, "holds": "[STNR]"} for m in (307, 308, 309, 311, 312, 313)],
            "stop_page": {"mes": 56, "holds": "Env Play()"}}


def _rows_of_visit8(donor: int, writes: list, chain: list) -> list:
    """One visit's emitted row pattern (4.16): its prologue -- the masked pair (ip22, ip49) and the ambient four --
    then its post rows in the bytes' order: the writes after the ambient four (in their listed order), then the door's
    chain row. ``[place, sid, tag, off, target, new]``; ``same`` is filled by :func:`_pattern8`."""
    amb = _ambient8(donor)
    ambs = {(k["sid"], k["tag"], k["ip"]) for k in amb}
    rows = [[donor, 0, 0, 16, "Global.Bit[191]", 0], [donor, 0, 0, 43, "Global.Bit[184]", 0]]
    rows += [[donor, k["sid"], k["tag"], k["off"], k["target"], k["value"]] for k in amb]
    rows += [[donor, k["sid"], k["tag"], k["off"], k["target"], k["value"]] for k in writes
             if k["donor"] == donor and (k["sid"], k["tag"], k["ip"]) not in ambs]
    rows += [[donor, k["sid"], k["tag"], k["off"], k["target"], k["value"]] for k in chain if k["donor"] == donor]
    return rows


def _pattern8(writes: list, chain: list) -> dict:
    """4.16: THE EMITTED ROW PATTERN over this start: no site stored twice before the cut, so no ``c`` row; each visit's
    emitted ``w`` rows in order, ``same`` 1 when the store left its target's value as it was (the start values, then
    each row in route order). No floating row: the knight's ip230 before ip243 by THE KNIGHT WAIT (O8-ORDER), 166's
    ip255 before e6 t1 ip345 by ~2.5 s of scene."""
    values = dict(START_VALUES8)
    visits = []
    for donor in ROUTE:
        out = []
        for p_, sid, tag, off, target, new in _rows_of_visit8(donor, writes, chain):
            old = values.get(target, 0)
            out.append([p_, sid, tag, off, target, new, int(old == new)])
            values[target] = new
        visits.append(out)
    n = sum(len(v) for v in visits)
    return {"visits": visits, "floating": [], "counts": [],
            "why": f"StoryTrace.cs:374-401 over the raw warp's start values (Int16[9] 643, Byte[13] 1, Int16[11] -1, "
                   f"Byte[14] 0, Byte[8] 125, Bit[191] 0, Bit[184] 0): no site is stored twice before the cut, so every "
                   f"store is emitted -- same-value ones too, each the first at its site in the epoch -- and no c row "
                   f"arises; {n} w rows ({2 * len(ROUTE)} masked) before the cut ({' / '.join(str(len(v)) for v in visits)}"
                   f"), then 55 e0 t0 ip22, the cut. No floating row: 164 ip230 before ip243 by THE KNIGHT WAIT "
                   f"(O8-ORDER); 166 ip255 before e6 t1 ip345 by ~2.5 s of scene"}


def last_values8(pattern: dict) -> dict:
    """The value every target holds after the pattern's last tuple, over the raw start (:data:`START_VALUES8`): the
    arrival's values in 55 (with SC; Map variables are 0 at load)."""
    values = dict(START_VALUES8)
    for v in pattern.get("visits") or ():
        for tup in v:
            values[tup[4]] = tup[5]
    return values


def _end_state8(pattern: dict, keys: list, raced=RACED8, scene=END_SCENE8) -> tuple:
    """4.9, COMPUTED (never typed): ``(end_state, end_state_trace)`` -- every target the pattern writes, its last value
    in route order, with SC the scenario, the RACED targets taken OUT of the live read and put in ``end_state_trace`` at
    their last pre-cut site (its ip the registered key's), THE ARRIVAL SCENE's (``scene``: :data:`END_SCENE8`, the
    review's #3) taken out too; plus :data:`UNTOUCHED8`, 0."""
    last, site = {}, {}
    for visit in pattern["visits"]:
        for p_, sid, tag, off, target, new, _same in visit:
            last[target] = new
            site[target] = (p_, sid, tag, off)
    live = {"Global.UInt16[0]": 1190}
    live.update({t: v for t, v in last.items() if t not in raced})
    live.update({t: 0 for t in UNTOUCHED8})
    for t in scene:
        live.pop(t, None)
    whys = {"Global.Int16[2]": "55 e0 t0 ip255 rewrites it 110 -> 106 in the cut's frame (ip229: SC 1190 < 1400): the "
                               "live read races",
            "Global.Byte[8]": "55 e0 t0 ip342 rewrites it 0 -> 125 after its SYSVAR[3] sync, in the prologue's frame by "
                              "precedent (O7's 159 ip290; O3's 64 ip475, same-valued there: 0.2 #26): the live read races"}
    trace = {}
    for t in raced:
        if t not in last:
            continue
        p_, sid, tag, off = site[t]
        ip = next(k["ip"] for k in keys if (k["donor"], k["sid"], k["tag"], k["off"], k["target"]) == (
            p_, sid, tag, off, t))
        trace[t] = {"value": last[t], "site": {"place": p_, "sid": sid, "tag": tag, "ip": ip},
                    "why": whys.get(t, "the end field's prologue rewrites it at once: the live read races")}
    return live, trace


def _landing8(chain: list, end: int = END_FIELD, entry=None) -> dict:
    """4.3/5.3's landing: the route places, each crossing (a place's chain row, then the next place's ENTRY row --
    ``entry(place)``, default e0 t0 ip22 ``Bit[191] := 0``), the last chain row (the last compared row: 166 e6 t1 ip863),
    and the end row (55 e0 t0 ip22, the cut)."""
    entry = entry or (lambda p: _site(p, 0, 0, 22, "Global.Bit[191]", 0))
    by = {k["donor"]: k for k in chain}
    route = [k["donor"] for k in chain]
    crossings = [{"from": p, "exit": _site(p, by[p]["sid"], by[p]["tag"], by[p]["ip"], by[p]["target"],
                                           by[p]["value"]), "to": q, "enter": entry(q)}
                 for p, q in zip(route, route[1:])]
    lastp = route[-1]
    return {"route_places": list(route), "crossings": crossings,
            "last": _site(lastp, by[lastp]["sid"], by[lastp]["tag"], by[lastp]["ip"], by[lastp]["target"],
                          by[lastp]["value"]),
            "end_row": entry(end)}


#: 4.10: THE KNIGHT'S SEAT -- O8-KNIGHT's registration (the hook's ``seat`` and ``start1`` readings). ``start_y`` his
#: placement's LEVEL and ``y`` his seat's (the review's #2): CreateObject at POS_COMMAND_DEFAULTY, so GetTriIdxAtPos takes
#: the highest open triangle under (249, 4630) -- tri 130, PSX -11255 -- and his walk climbs loop 2 to tri 120's -11896;
#: O8-GOALS (g6') derives both off the mesh (:func:`knight_levels`) and keeps loop 1 400 from the whole range.
SEAT = {"donor": 164, "sid": 1, "name": "the knight", "seat": [-586, 3884], "tol": 30, "site": [164, 1, 1, 230],
        "start": [249, 4630], "walk_u": 1131.5, "release": {"y_ge": 8400}, "r": 220, "start_y": 11255, "y": 11896,
        "why": "164 e1 t1 ip215's last Walk(64950, 3884) seats him (tri 120, PSX -11896); step 1 plans with npcs on round "
               "him 300.0 u off its line -- the premise read at the wait's end (the ring at wait_flag.frame) and at "
               "step 1's frame0, keyed by place (31256 reads as 164), every run (O8-KNIGHT)"}
#: 4.10: FMV004 -- O8-MOVIE's registration (no ``movies`` key: played out).
MOVIE = {"donor": 166, "visit": 3, "name": "FMV004", "cinematic": [166, 6, 1, 633], "play": [166, 6, 1, 711],
         "from": [166, 6, 1, 502], "to": [166, 6, 1, 863], "file_s": 45.412, "slack_s": 5.0, "clock_every": 30,
         "why": "Cinematic(0, 9, 1, 1) -> MBGDiscTable[1][9] = MBG_DEF(\"FMV004\", 1, 0), type 0 (fldfmv.cs:56-58, "
                "MBG.cs:830); MoguriVideo's ma/FMV004.bytes, 45.412 s at 29.97 fps, on both sides; PLAYED OUT: no press, "
                "no choice and no skip dialog after the ip502 row's frame through the ip863 row's (a run with one is "
                "uncovered, A-MOVIE: the skip dialog is press-only), the span at least file_s - slack_s at the rate "
                "measured inside it (O8-MOVIE)"}
#: 4.10: THE SEAM -- O8-SEAM's registration.
SEAM = {"donor": 166, "to": 55, "exit": [166, 6, 1, 863], "field": [166, 6, 1, 871], "fields": [55],
        "why": "31258 is 166 byte for byte; its only Field() is e6 t1 ip871 Field(55), RAW, and MAPJUMP does no remap: "
               "every F run crosses from member(166) into REAL 55 -- one seam, read through the kept `e off fld 55` row, "
               "its exit row ip863 (O8-SEAM)"}
#: 2.1: the skip net -- O7's row and the 166-scoped row for the dialog's MEASURED option line (O3's F4 rule).
CHOICES8 = [{"donor": None, "sc": None, "match": "want to skip", "pick": "default", "once": False, "beat": None},
            {"donor": 166, "sc": None, "match": "No", "pick": "default", "once": False, "beat": None}]


def draft_predictions(campaign=None) -> dict:
    """The registered claims (research/o8_design.md section 4). Every number was read off the stock bytes (the offline
    check re-derives each), O4's build (C0), the live install or O4's campaign.toml (``campaign``); nothing is read from
    a run. The rehearsals (o8_rehearse.py) settle the driver's numbers before the lead freezes them (7.3)."""
    members, names = chain_from_campaign(campaign)
    rm = route_members8(members)
    writes, chain = _writes8(), _chain8()
    pattern = _pattern8(writes, chain)
    end_state, end_trace = _end_state8(pattern, writes + chain)
    table = _table8()
    start_music = dict(_key(164, 0, 0, 130, 124, "Global.Byte[13]", 1, ":=",
                            "164's K-385 branch from the warp's Byte[13] 1 (field 70's prologue :=1 at ip130); ip97 and "
                            "ip119 are dead (Int16[9] just set 385)"), old=1)
    return {
        "version": 1,
        "what": "O8: 164@1190 (warp, entrance 342; EVT_ALEX1_AC_TOWER_L3) -> the first spiral and THE KNIGHT WAIT -> "
                "165@343 (the second spiral) -> 166@344 (six pages, FMV004 played out) -> Field(55) -> the arrival in "
                "REAL 55 at 110 on both sides, SC 1190; stock vs the alxc disc-1 chain as O4 deployed it (route members "
                f"{rm[164]}-{rm[166]}; one declared seam, {rm[166]} -> 55; PLAN.md, O8) -- a US session",
        "rehearsals": [], "rehearsal_fps": [], "rehearsed": {},
        "order": ["S", "F", "S", "F", "S", "F"],
        "min_covered": 2,
        "rerun": {"max": 2, "stop_on": ["V19"]},
        # F8 replaces every one from R-FULL (7.3): estimates of ~2.5 min a run, the watchdog sized for FMV004 (2.7)
        "budget": {"run_s": 600, "run_min_s": 300, "session_s": 3600, "settle_s": 1.0, "no_progress_s": 150,
                   "end_row_s": 10.0},
        "start": {"S": 164, "F": rm[164]},
        "entrance": 342,
        "scenario": 1190,
        "lang": SESSION_LANG,
        "end_field": END_FIELD,
        "end_fields": [END_FIELD],
        "side_ends": {"S": [END_FIELD], "F": [END_FIELD]},
        "route": list(ROUTE),
        "visits": list(ROUTE),
        "stock_fields": list(STOCK_FIELDS),
        "members": {str(f): d for f, d in sorted(members.items())},
        "names": {str(f): n for f, n in sorted(names.items())},
        "text_block": TEXT_BLOCK,
        "text_blocks": list(TEXT_BLOCKS),
        "recovery": 4600,
        "cut_start": True,
        "start_first": _key(164, 0, 0, 22, 16, "Global.Bit[191]", 0, ":=",
                            "164's Main_Init: its first store (emitted same: a new site)"),
        "start_music": start_music,
        "start_scoped": start_scoped8(),
        "start_reads": start_reads8(),
        "carried": carried8_typed(),
        # SC 1190 = 0x04A6 (bytes 0 and 1); FieldEntrance 342 = 0x0156 (bytes 2 and 3): FOUR rows
        "start_residue": [[0, 0, 166], [1, 0, 4], [2, 0, 86], [3, 0, 1]],
        "residue_after_start": [],
        "sc_bytes": [0, 1],
        "ladder": [],
        "entrance_bytes": [2, 3],
        "chain": chain,
        "writes": writes,
        "start_dependent": [],
        "naming": [],
        "error_path": _error_path8(),
        "forbidden_sites": _forbidden_sites8(),
        "dead": _dead8(),
        "inert": [],
        "live_shared": [{"donor": 166, "sid": 2, "callers": [[6, 1, 489]],
                         "why": "RunSharedScript(2): the clank loop, run only from e6 t1 ip489 and stopped at ip498; it "
                                "stores no global (0.2 #4)"}],
        "noise": [],
        "forbidden": [{"off_route": True, "cause": "walk",
                       "why": "a write off the route: S, a place outside [164, 165, 166] + [55]; F, a field that is "
                              "neither a member whose donor is on the route nor REAL 55 (a real 164/165/166 on F: an "
                              "un-retargeted Field(); 163/31255 after 164.e3, backed by its V11 step row)"},
                      {"donor": 164, "sid": 1, "tag": 3, "cause": "confirm_talk", "object": 1,
                       "why": "the knight's TALK (164 e1 t3: Bit[3851], Bit[3792], Bit[7211], Int16[224]): a Confirm "
                              "near him with control held -- nothing on the route presses one there"},
                      {"donor": 164, "sid": 7, "tag": 11, "cause": "confirm_talk", "object": 1,
                       "why": "164 e7 t11 (Byte[208]), run only by the knight's talk (RunScriptSync(4, 250, 11) at e1 "
                              "t3 ip415)"}],
        "landing": _landing8(chain),
        "end_state": end_state,
        "end_state_trace": end_trace,
        "end_state_scene": json.loads(json.dumps(END_SCENE8)),
        "interruptions": [],
        "static_objects": [],
        "seat_watch": copy.deepcopy(SEAT),
        "movie": copy.deepcopy(MOVIE),
        "seam": copy.deepcopy(SEAM),
        "beats": [s["beat"] for c in table for s in c["steps"]],
        "battles": [],
        "stop_pages": [{"match": "Env Play()",
                        "why": "window 56 of 164 (e0 t0 ip597/ip631), 165 (ip677/ip711), 166 (ip322/ip356): "
                               "Byte[13]/[14] arrived 9"}],
        "regions": _regions8(),
        "hotspots": {},
        "table": table,
        "steps_default": {"attempts": 2, "interrupts": 1, "timeout_s": 20, "confirm_s": 4.0, "npcs": True,
                          "overlay_ok": False, "immediate": False, "settle": None, "lunge_ticks": 0, "tolerance": 45,
                          "min_depth": 40, "exit_wait_s": 5.0, "exit_slack": 40,
                          "climb": {"burst_frames": 30, "max_bursts": 80, "stall_bursts": 8}},
        "choices": copy.deepcopy(CHOICES8),
        "witness": dict(C7.WITNESS),
        "route_pins": route_pins8(),
        "route_mes": route_mes8(),
        "route_build": route_build8(),
        "pattern": pattern,
        "settings": json.loads(json.dumps(SETTINGS8)),
        "override70": dict(OVERRIDE70),
        "derived": json.loads(json.dumps(DERIVED)),
        "engine": dict(ENGINE),
    }


# ======================================================================== the bytes' readers (pure)
_S16 = A._s16
_HEIGHT8 = re.compile(r"^SET\(\{obj\(uid=250\)\.f\[1\] const\((\d+)\) (B_LT|B_GT) B_EXPR_END\}\)$")
_JUMP8 = re.compile(r"^(JMP_IFNOT|JMP_IF)\(L(\d+)\)$")
_CALL250 = re.compile(r"^RunScript(?:Sync|Async)\((\d+), 250, (\d+)\)$")
_WALK = re.compile(r"^Walk\((\d+), (\d+)\)$")
_FLIP = {"y_gt": "y_le", "y_ge": "y_lt", "y_lt": "y_ge", "y_le": "y_gt"}


def height_gate(test, jump):
    """The condition under which control reaches a height test's GUARDED code (research/o8_design.md 1.3; the claim
    review's #7, 0.2 #24), read off the test's pinned text AND its consuming jump's: ``obj(uid=250).f[1] const(c) B_LT``
    is published y > -s16(c), ``B_GT`` is y < -s16(c) (2-byte constants signed: f[1] is PSX y, up negative); a
    ``JMP_IFNOT`` past the guarded code (a door's, to its RET) passes the test as is, a ``JMP_IF`` back over it (the
    knight's wait loop, to its op_22(1)) passes its NEGATION, the strictness flipped (y < 8400 -> ``{"y_ge": 8400}``).
    Any other shape (another operator, another jump, a missing text) is None."""
    m, j = _HEIGHT8.match(str(test or "")), _JUMP8.match(str(jump or ""))
    if m is None or j is None:
        return None
    h = -_S16(int(m.group(1)))
    gate = {"y_gt": h} if m.group(2) == "B_LT" else {"y_lt": h}
    if j.group(1) == "JMP_IF":
        (k, v), = gate.items()
        gate = {_FLIP[k]: v}
    return gate


def gate_holds(gate: dict, y) -> bool:
    """Whether a published height ``y`` satisfies a height gate (``{"y_gt": h}`` and its kin); a missing y is False."""
    if y is None or not gate:
        return False
    return SD.until_ok(gate, 0.0, 0.0, float(y))


def gate_text(gate: dict) -> str:
    """``y > 12000`` for ``{"y_gt": 12000}``."""
    (k, v), = (gate or {"?": "?"}).items()
    return f"y {dict(y_gt='>', y_ge='>=', y_lt='<', y_le='<=').get(k, k)} {v}"


def y_implies(until: dict, gate: dict) -> bool:
    """Whether an ``until``'s y terms are AT LEAST AS STRICT as a door's height ``gate`` -- every published height the
    until admits satisfies the gate, so a control loss the until accepts as the door's is one the door can cause
    (research/o8_design.md 11.4, the review's #4). Per gate term: ``{"y_gt": g}`` needs a ``y_gt`` term >= g or a
    ``y_ge`` term > g; ``{"y_ge": g}`` a ``y_gt`` or ``y_ge`` term >= g; ``{"y_lt": g}`` a ``y_lt`` term <= g or a
    ``y_le`` term < g; ``{"y_le": g}`` a ``y_lt`` or ``y_le`` term <= g. x and z terms imply no height; an empty gate is
    implied by anything."""
    inf = float("inf")
    t = {k: float(v) for k, v in (until or {}).items() if k.startswith("y_")}
    for k, v in (gate or {}).items():
        g = float(v)
        if k == "y_gt":
            ok = t.get("y_gt", -inf) >= g or t.get("y_ge", -inf) > g
        elif k == "y_ge":
            ok = max(t.get("y_gt", -inf), t.get("y_ge", -inf)) >= g
        elif k == "y_lt":
            ok = t.get("y_lt", inf) <= g or t.get("y_le", inf) < g
        elif k == "y_le":
            ok = min(t.get("y_lt", inf), t.get("y_le", inf)) <= g
        else:
            ok = False
        if not ok:
            return False
    return True


def pin_text(pred: dict, site) -> str | None:
    """The pinned text of ``[donor, sid, tag, ip]``, or None."""
    return C7.pin_text(pred, site)


def door_gate_pins(pred: dict, donor: int, sid: int) -> tuple:
    """A door's height test and its consuming jump among the route pins: ``(test site, test text, jump site, jump
    text)`` -- the pinned tag-2 height test of entry ``sid`` of ``donor`` and the next pinned instruction after it in
    the same function (``(None,) * 4`` without one)."""
    fn = sorted((p for p in pred.get("route_pins") or () if (p[0], p[1], p[2]) == (donor, sid, 2)), key=lambda p: p[3])
    for i, p in enumerate(fn):
        if _HEIGHT8.match(p[4]) and i + 1 < len(fn):
            return list(p[:4]), p[4], list(fn[i + 1][:4]), fn[i + 1][4]
    return None, None, None, None


def knight_release(pred: dict):
    """The knight's release, read off 164 e1 t1 ip178's pinned height test and ip187's consuming ``JMP_IF`` (the wait
    loop: the release is the test's negation) -- ``{"y_ge": 8400}`` -- or None."""
    site = (pred.get("seat_watch") or {}).get("site") or [164, 1, 1, 230]
    d, sid, tag = site[0], site[1], site[2]
    fn = sorted((p for p in pred.get("route_pins") or () if (p[0], p[1], p[2]) == (d, sid, tag)), key=lambda p: p[3])
    for i, p in enumerate(fn):
        if _HEIGHT8.match(p[4]) and i + 1 < len(fn):
            return height_gate(p[4], fn[i + 1][4])
    return None


def knight_walk(pred: dict) -> tuple:
    """``(placement (x, z), the walk's points, its length, the seat)`` read off the knight's pins: e1 t0 ip14 / ip22's
    placement (:func:`o7_castle_walk.placement_of`) and e1 t1's four ``Walk`` operands (2-byte, signed)."""
    site = (pred.get("seat_watch") or {}).get("site") or [164, 1, 1, 230]
    d, sid = site[0], site[1]
    start = C7.placement_of(pred.get("route_pins") or [], d, sid)
    pts = []
    for p in sorted((p for p in pred.get("route_pins") or () if (p[0], p[1], p[2]) == (d, sid, 1)), key=lambda p: p[3]):
        m = _WALK.match(p[4])
        if m:
            pts.append((float(_S16(int(m.group(1)))), float(_S16(int(m.group(2))))))
    if start is None or not pts:
        return start, pts, None, None
    path = [start] + pts
    return start, pts, round(sum(math.dist(a, b) for a, b in zip(path, path[1:])), 1), pts[-1]


def knight_levels(pred: dict, wm, *, step: float = 25.0) -> list:
    """His LEVEL along his walk (research/o8_design.md 2.6; the review's #2): ``[(x, z, published y)]`` every ~``step``
    u of his pinned walk (:func:`knight_walk`) on the place's mesh ``wm`` (a PlayerWalkmesh) -- at his placement the
    HIGHEST open triangle under it (CreateObject at POS_COMMAND_DEFAULTY: GetTriIdxAtPos takes the triangle nearest
    that height), then at each point the open triangle's height NEAREST the last (he walks his level: MoveToward on
    the walkmesh) -- or ``[]`` without his pins or with no floor under a point. Stock 164: 11255 at (249, 4630), 11448,
    11598, 11727 at the three turns, 11896 at the seat."""
    start, pts, _u, _seat = knight_walk(pred)
    if start is None or not pts:
        return []
    path = [tuple(map(float, start))] + [tuple(map(float, p)) for p in pts]
    xs = []
    for (ax, az), (bx, bz) in zip(path, path[1:]):
        n = max(1, int(math.dist((ax, az), (bx, bz)) // step))
        xs += [(ax + (bx - ax) * i / n, az + (bz - az) * i / n) for i in range(n)]
    xs.append(path[-1])
    out, last = [], None
    for x, z in xs:
        hs = [y for _ti, y in _heights(wm, x, z)]
        if not hs:
            return []
        last = max(hs) if last is None else min(hs, key=lambda h: abs(h - last))
        out.append((x, z, last))
    return out


def _y_gap(y: float, lo: float, hi: float) -> float:
    """How far a height ``y`` lies outside [``lo``, ``hi``] (0 inside)."""
    return lo - y if y < lo else y - hi if y > hi else 0.0


def band_closures(mesh, lo: float, hi: float) -> list:
    """A step's floor cut to its one level (research/o8_design.md 1.3): every OPEN triangle of ``mesh`` (a
    PlayerWalkmesh, its mask-closed ones aside, or a raw mesh) whose centroid's PSX y lies outside [``lo``, ``hi``].
    Sorted."""
    raw = getattr(mesh, "mesh", mesh)
    closed = getattr(mesh, "closed", frozenset())
    wv, tris = raw.world_verts(), raw.tris
    return sorted(i for i in range(len(tris)) if i not in closed
                  and not lo <= sum(wv[k][1] for k in tris[i].vtx) / 3 <= hi)


# -- the evaluator (Kleene: a test decided by its known operands takes one branch) ---------------------------------
_TOK8 = re.compile(r"(Global\.\w+\[\d+\]|Map\.\w+\[\d+\]|Instance\.\w+\[\d+\]|B_SYSVAR\[\d+\]|obj\(uid=\d+\)\.f\[\d+\]|"
                   r"B_PTR\(\d+\)|const\(\d+\)|B_\w+)")
_VAR8 = re.compile(r"^(Global|Map|Instance)\.\w+\[\d+\]$")
_STORE_OP8 = re.compile(r"\b(B_LET|B_\w+_LET|B_POST_PLUS|B_POST_MINUS|B_PRE_PLUS|B_PRE_MINUS)\b")
_CMP8 = {"B_EQ": lambda a, b: a == b, "B_NE": lambda a, b: a != b, "B_LT": lambda a, b: a < b,
         "B_GT": lambda a, b: a > b, "B_LE": lambda a, b: a <= b, "B_GE": lambda a, b: a >= b}
_ARITH8 = {"B_PLUS": lambda a, b: a + b, "B_MINUS": lambda a, b: a - b, "B_AND": lambda a, b: a & b,
           "B_OR": lambda a, b: a | b, "B_XOR": lambda a, b: a ^ b, "B_MULT": lambda a, b: a * b,
           "B_SHIFT_LEFT": lambda a, b: a << b, "B_SHIFT_RIGHT": lambda a, b: a >> b}


def _const8(c: int) -> int:
    """A statement's ``const(c)`` as the engine reads it: a 2-byte operand, signed."""
    return _S16(c) if 0x8000 <= c <= 0xFFFF else c


def _as_width8(target: str, v: int) -> int:
    width = target.split(".", 1)[1].split("[")[0]
    if width in T.BIT_WIDTHS:
        return int(v) & 1
    return A.O2Segment._as_width(width, int(v))


class _Env8:
    """The values a walk of a function knows: ``known`` (``{target: value}``), ``unknown`` (targets a statement made
    unknown), and the defaults for the rest -- ``globals0`` (a Global target not given reads that value, None: unknown)
    and ``map0`` (a Map variable not given: 0 at load, or None)."""

    def __init__(self, known=None, *, globals0=None, map0=None):
        self.known, self.unknown = dict(known or {}), set()
        self.globals0, self.map0 = globals0, map0

    def copy(self):
        e = _Env8(self.known, globals0=self.globals0, map0=self.map0)
        e.unknown = set(self.unknown)
        return e

    def get(self, var: str):
        if var in self.unknown:
            return None
        if var in self.known:
            return self.known[var]
        if var.startswith("Global."):
            return self.globals0
        if var.startswith("Map."):
            return self.map0
        return None

    def set(self, var: str, v) -> None:
        if v is None:
            self.known.pop(var, None)
            self.unknown.add(var)
        else:
            self.unknown.discard(var)
            self.known[var] = _as_width8(var, v)

    def key(self) -> tuple:
        return tuple(sorted(self.known.items())), tuple(sorted(self.unknown))


def eval8(text: str, env: _Env8):
    """``(lvalue | None, value | None)`` of one ``SET({...})`` statement under ``env`` (RPN, Kleene logic: an
    ``&&`` with a known-false side is false, an ``||`` with a known-true side true, any other op over an unknown is
    unknown; an op it does not know makes the whole expression unknown). A STORE (an assignment op) returns its lvalue
    -- the first variable token -- and the value it stores (None: unknown); a test returns ``(None, its value)``."""
    inner = text[len("SET({"):-len("})")] if text.startswith("SET({") and text.endswith("})") else ""
    toks = _TOK8.findall(inner)
    store = _STORE_OP8.search(inner) is not None
    lv = next((t for t in toks if _VAR8.match(t)), None) if store else None
    st: list = []

    def val(x):
        return env.get(x[1]) if isinstance(x, tuple) else x
    try:
        for t in toks:
            if t == "B_EXPR_END":
                break
            if t.startswith("const("):
                st.append(_const8(int(t[6:-1])))
            elif _VAR8.match(t):
                st.append(("var", t))
            elif t.startswith(("B_SYSVAR[", "obj(", "B_PTR(")):
                st.append(None)
            elif t in _CMP8 or t in _ARITH8 or t in ("B_ANDAND", "B_OROR"):
                b, a = val(st.pop()), val(st.pop())
                if t == "B_ANDAND":
                    st.append(0 if (a == 0 or b == 0) else None if None in (a, b) else 1)
                elif t == "B_OROR":
                    st.append(1 if ((a is not None and a != 0) or (b is not None and b != 0)) else
                              None if None in (a, b) else 0)
                elif None in (a, b):
                    st.append(None)
                else:
                    st.append(int(_CMP8[t](a, b)) if t in _CMP8 else _ARITH8[t](a, b))
            elif t == "B_LET":
                b, _a = st.pop(), st.pop()
                st.append(val(b))
            elif t in ("B_POST_PLUS", "B_POST_MINUS", "B_PRE_PLUS", "B_PRE_MINUS"):
                v = val(st.pop())
                st.append(None if v is None else v + (1 if "PLUS" in t else -1))
            elif t.endswith("_LET"):
                bv, av = val(st.pop()), val(st.pop())
                op = "B_" + t[2:-4]
                st.append(None if None in (av, bv) or op not in _ARITH8 else _ARITH8[op](av, bv))
            else:
                return lv, None
    except IndexError:
        return lv, None
    if not st:
        return lv, None
    return lv, val(st[-1])


def _labels8(t: str) -> list:
    return [int(x) for x in re.findall(r"L(\d+)", t)]


def _switch_target8(t: str, v):
    """A ``SWITCH(base, Ldefault, Lcase0, ...)`` / ``SWITCHEX(Ldefault, v1, L1, ...)``'s label for value ``v`` -- or,
    ``v`` unknown, every label it can take."""
    if t.startswith("SWITCHEX("):
        args = [a.strip() for a in t[len("SWITCHEX("):-1].split(",")]
        default, pairs = int(args[0][1:]), list(zip(args[1::2], args[2::2]))
        if v is None:
            return [default] + [int(lab[1:]) for _c, lab in pairs]
        return [next((int(lab[1:]) for c, lab in pairs if int(c) == int(v)), default)]
    m = re.match(r"SWITCH\((\d+), L(\d+)((?:, L\d+)*)\)", t)
    base, default = int(m.group(1)), int(m.group(2))
    cases = [int(x) for x in re.findall(r"L(\d+)", m.group(3))]
    if v is None:
        return [default] + cases
    n = int(v) - base
    return [cases[n] if 0 <= n < len(cases) else default]


def _items8(idx, sid: int, tag: int) -> list:
    return A.O2Segment._items(idx, sid, tag)


def reach8(idx, sid: int, tag: int, ip: int, known=None, *, items=None, limit: int = 200000) -> bool:
    """Whether a store site is REACHABLE (research/o8_design.md 1.3; the claim review's #9): a path search over entry
    ``sid``'s function ``tag`` from its start, each ``SET`` of a constant updating the known values (any other store
    making its target unknown), a test decided by its known operands (Kleene: :func:`eval8`; a ``SWITCH`` /
    ``SWITCHEX`` on a known value taking its one label) taken one way, any other test taken BOTH ways (a free arrival
    value, a ``B_SYSVAR``), a revisited (ip, known values) pair cut; True when some path reaches ``ip``. ``known``:
    ``{target: value}`` -- every other Global and Map variable FREE (O8-CENSUS: an ``error_path`` guard must hold from
    SOME arrival; O8-KEYS (g): the Map values :func:`end_map_held8` derives -- never one another function stores, the
    review's #3). ``items`` (``[(ip, rel, text)]``, a seam) replaces the decode."""
    items = items if items is not None else _items8(idx, sid, tag)
    by_rel = {rel: i for i, (_ip, rel, _t) in enumerate(items)}
    todo = [(0, _Env8(known), None)]
    seen: set = set()
    steps = 0
    while todo:
        i, env, cond = todo.pop()
        while i is not None and 0 <= i < len(items):
            steps += 1
            if steps > limit:
                raise ValueError(f"reach8: e{sid} t{tag}: the search ran {limit} steps")
            k = (i, env.key(), cond)
            if k in seen:
                break
            seen.add(k)
            tip, _rel, t = items[i]
            if tip == ip:
                return True
            if t.startswith("RET"):
                break
            if t.startswith("SET("):
                lv, v = eval8(t, env)
                if lv is not None:
                    env.set(lv, v)
                cond = v
                i += 1
                continue
            if t.startswith("JMP("):
                i = by_rel.get(_labels8(t)[0])
                continue
            jm = _JUMP8.match(t)
            if jm:
                target = by_rel.get(int(jm.group(2)))
                if cond is None:
                    todo.append((target, env.copy(), cond))
                    i += 1
                    continue
                take = (cond == 0) if jm.group(1) == "JMP_IFNOT" else (cond != 0)
                i = target if take else i + 1
                continue
            if t.startswith(("SWITCH(", "SWITCHEX(")):
                labs = [by_rel.get(x) for x in _switch_target8(t, cond)]
                for x in labs[1:]:
                    todo.append((x, env.copy(), cond))
                i = labs[0] if labs else None
                continue
            i += 1
    return False


#: An instruction that YIELDS the event loop a tick or more (the walk's "first long yield", 0.2 #5).
_LONG8 = re.compile(r"^(op_22\((\d+)\)|Wait|WindowSync|WindowAsync|RunScriptSync|Field\(|Battle\(|Cinematic|EnableMove)")


def end_race8(idx, values: dict, *, sid: int = 0, tag: int = 0, items=None, globals0=None) -> dict:
    """THE RACED SET (research/o8_design.md 0.2 #5, #26; 4.9): the end field's Main_Init (``sid``/``tag``, default e0
    t0) walked from the arrival's ``values`` (``{target: value}``; Map variables 0 at load, any other Global unknown)
    through its first long yield ON TO ITS RET: a test decided by its known operands takes its branch (Kleene), an
    unresolved BACKWARD branch falls through (the sound-sync loop), an unresolved forward branch or switch RAISES.
    ``{"raced": {target: [the arrival's value, the last stored]} -- every Global target its stores leave at another
    value --, "stores": [[ip, target, old, new]], "yield": the first long yield's ip, "ret": the RET's ip, "map": the
    Map values the walk left at its RET (O8-KEYS (g)'s other-function proof reads them)}``. ``items`` is a seam;
    ``globals0`` the value of a Global target ``values`` does not give (None: unknown -- O8's 55; 0: a raw start's
    untouched targets, New Game's -- the story-o3 fixture's 64)."""
    items = items if items is not None else _items8(idx, sid, tag)
    by_rel = {rel: i for i, (_ip, rel, _t) in enumerate(items)}
    env = _Env8(values, globals0=globals0, map0=0)
    i, cond, steps, stores, yielded, ret = 0, None, 0, [], None, None
    while 0 <= i < len(items):
        steps += 1
        if steps > 20000:
            raise ValueError("end_race8: the walk ran 20000 steps")
        ip, _rel, t = items[i]
        if t.startswith("RET"):
            ret = ip
            break
        if t.startswith("SET("):
            lv, v = eval8(t, env)
            if lv is not None:
                if lv.startswith("Global."):
                    stores.append([ip, lv, env.get(lv), None if v is None else _as_width8(lv, v)])
                env.set(lv, v)
            cond = v
            i += 1
            continue
        if t.startswith("JMP("):
            i = by_rel[_labels8(t)[0]]
            continue
        jm = _JUMP8.match(t)
        if jm:
            target = by_rel[int(jm.group(2))]
            if cond is None:
                if target < i:
                    i += 1
                    continue
                raise ValueError(f"end_race8: an unresolved forward branch at ip{ip}: {t}")
            take = (cond == 0) if jm.group(1) == "JMP_IFNOT" else (cond != 0)
            i = target if take else i + 1
            continue
        if t.startswith(("SWITCH(", "SWITCHEX(")):
            if cond is None:
                raise ValueError(f"end_race8: an unresolved switch at ip{ip}: {t}")
            i = by_rel[_switch_target8(t, cond)[0]]
            continue
        m = _LONG8.match(t)
        if m and yielded is None and not (t.startswith("op_22(") and int(m.group(2)) < 2):
            yielded = ip
        i += 1
    first, last = {}, {}
    for _ip, tgt, old, new in stores:
        first.setdefault(tgt, old)
        last[tgt] = new
    raced = {t: [first[t], last[t]] for t in last if first[t] != last[t]}
    mapv = {t: v for t, v in sorted(env.known.items()) if t.startswith("Map.")}
    return {"raced": raced, "stores": stores, "yield": yielded, "ret": ret, "map": mapv}


def race_site8(pred: dict, sr: dict):
    """A START READ's EXPLICIT raced store (4.5; critique #2): ``sr["race"]`` -- ``(70, 0, 0, ip)`` -- when the field-70
    route pin there is ``SET({<target> const(<race_value>) B_LET B_EXPR_END})``, else None. O7's ``race_site`` keys on
    the read's own ``old`` and resolves 164 ip130's race to 70 ip130 (:= 1), the wrong store."""
    race, rv = sr.get("race"), sr.get("race_value")
    if not isinstance(race, (list, tuple)) or len(race) != 4 or not isinstance(rv, int) or isinstance(rv, bool):
        return None
    want = f"SET({{{sr['target']} const({int(rv) & 0xFFFF}) B_LET B_EXPR_END}})"
    return tuple(race) if race[0] == NEWGAME_FIELD and pin_text(pred, list(race)) == want else None


# -- the talk, set aside (0.2 #11) -------------------------------------------------------------------------------------
def player_sid_of(idx, entrance: int, *, instanced=None) -> int | None:
    """The instanced entry holding ``DefinePlayerCharacter()`` at ``entrance`` (the player's entry: uid 250's)."""
    for sid, _tag, _ip, t in C7.instanced_texts(idx, entrance, instanced=instanced):
        if t == "DefinePlayerCharacter()":
            return sid
    return None


def talk_reach(idx, player_sid, *, entries=None, texts=None) -> set:
    """The functions only a TALK reaches (research/o8_design.md 1.3; 0.2 #11): ``{(sid, tag)}`` -- every tag 3 of the
    ``entries`` (default every entry), and, to a fixpoint, each ``(player_sid, t)`` a function in the set calls by
    ``RunScriptSync`` / ``RunScriptAsync(_, 250, t)`` that no function OUTSIDE the set calls (164: e1 t3, e7 t11, e7
    t12; 165, 166: none). ``texts`` (``[(sid, tag, ip, text)]``, a seam) replaces the decode."""
    texts = texts if texts is not None else C6.O6Segment._all_texts(idx)
    ents = None if entries is None else set(entries)
    talk = {(s, t) for s, t, _ip, _x in texts if t == 3 and (ents is None or s in ents)}
    calls: dict = {}
    for s, t, _ip, x in texts:
        m = _CALL250.match(x)
        if m:
            calls.setdefault((player_sid, int(m.group(2))), set()).add((s, t))
    while True:
        more = {fn for fn, by in calls.items() if fn not in talk and by and by <= talk}
        if not more:
            return talk
        talk |= more


def route_run_texts(idx, entrance: int, *, instanced=None) -> list:
    """``[(sid, tag, ip, text)]`` of every function the route RUNS at ``entrance``: every function of every entry
    instanced there (:func:`o7_castle_walk.instanced_texts`) less :func:`talk_reach` (the carried scan's narrowing,
    decision 3)."""
    ents = C7.instanced_entries(idx, entrance, instanced=instanced)
    texts = C7.instanced_texts(idx, entrance, instanced=instanced)
    talk = talk_reach(idx, player_sid_of(idx, entrance, instanced=instanced), entries=ents)
    return [x for x in texts if (x[0], x[1]) not in talk]


# -- THE CARRIED VALUES and the olds (4.5) --------------------------------------------------------------------------
def prior_segments8(here: Path = HERE) -> list:
    """``[(name, predictions)]`` of :data:`PRIOR_SEGMENTS8`, read from the repo (the frozen O1-O7 files)."""
    return [(n, json.loads((Path(here) / n).read_text(encoding="utf-8"))) for n in PRIOR_SEGMENTS8]


def o7_frozen(here: Path = HERE) -> dict:
    """O7's frozen predictions (:data:`O7_FROZEN`): the start-scoped olds are read off its ``pattern``."""
    return json.loads((Path(here) / O7_FROZEN).read_text(encoding="utf-8"))


def o8_targets(pred: dict) -> set:
    """The targets O8 writes -- its writes, its chain and the masked prologue pair -- subtracted from the carried."""
    return {k["target"] for k in list(pred.get("writes") or ()) + list(pred.get("chain") or ())} | set(MASKED_TARGETS)


def carried8(pred: dict, segs) -> tuple:
    """THE CARRIED VALUES, DERIVED (4.5): :func:`o7_castle_walk.carried_from_segments` over the frozen keys of ``segs``
    (O1-O7, each checked against its own end_state) from the raw warp's start (:data:`START_VALUES8`), less O8's
    targets."""
    return C7.carried_from_segments(segs, writes=o8_targets(pred), raw=START_VALUES8)


def scoped_derivation8(pred: dict, pred7: dict, segs) -> tuple:
    """THE START-SCOPED OLDS, DERIVED (4.5): O7's rule from :data:`START_VALUES8` -- ``({site: (target, raw old, true
    old)} for every writes key on the route, problems)``: the route's writes and chain keys walked in route order, each
    key's ``old`` from the RAW START and from A TRUE O1-O7 RUN (the last values off O7's FROZEN pattern, else the
    composition over the frozen O1-O7 keys ``segs``, else the raw start's), each carried on through the route's own
    earlier keys. A site whose two olds differ is START-SCOPED."""
    writes, chain = list(pred.get("writes") or ()), list(pred.get("chain") or ())
    targets = sorted({k["target"] for k in writes + chain})
    lasts, bad = C7.last_values(pred7, targets)
    composed, _problems = C7.carried_from_segments(segs, writes=(), raw=START_VALUES8)
    raw = {t: int(START_VALUES8.get(t, 0)) for t in targets}
    true = {t: (int(lasts[t]) if lasts.get(t) is not None else int(composed[t][1]) if t in composed else raw[t])
            for t in targets}
    keyed = {id(k) for k in writes}
    out = {}
    for p in pred["route"]:
        for k in writes + chain:
            if k["donor"] != p:
                continue
            t = k["target"]
            if id(k) in keyed:
                out[(k["donor"], k["sid"], k["tag"], k["ip"])] = (t, raw[t], true[t])
            raw[t] = true[t] = int(k["value"])
    return out, bad


# ======================================================================== a run's own rows (pure)
def _fld_of(members: dict, p: int) -> int:
    """The side's field of place ``p``: its member on F (``members`` given), the place itself on S."""
    inv = {d: f for f, d in sorted(members.items(), reverse=True)}
    return inv.get(p, p) if members else p


def exempt_span(log: list, place_: int) -> tuple:
    """THE KNIGHT'S SPAN (research/o8_design.md 1.3, 2.6; critique #1): ``(lo, hi)`` -- ``lo`` the ``frame0`` of the
    place's FIRST step-0 row, ``hi`` the ``frame0`` of its FIRST step-1 row (None when there is none): every attempt of
    step 0, the gaps between them, the wait and the settle before step 1. ip230 is exempt inside ``[lo, hi)`` alone."""
    rows = [x for x in log or () if x.get("k") == "step" and x.get("donor") == place_]
    lo = next((x.get("frame0") for x in rows if x.get("n") == 0), None)
    hi = next((x.get("frame0") for x in rows if x.get("n") == 1), None)
    return lo, hi


def door_sites8(pred: dict, place_: int, to) -> tuple:
    """A trigger's DOOR (5.3 WALK (b); the driver review's #5): ``(the exit's key, {(sid, tag, ip)})`` -- the registered
    exit of ``place_`` whose ``to`` is the step's (never ``target`` only), and every registered store site of its tag
    2 (writes, chain, error path, forbidden and dead sites: 164.e2's ip243 and its dead ip215; 165.e2's ip205 and
    ip233). ``(None, set())`` without one."""
    key = next((k for k, r in sorted((pred.get("regions") or {}).items()) if r.get("role") == "exit"
                and k.split(".", 1)[0] == str(place_) and r.get("to") == to), None)
    if key is None:
        return None, set()
    sid = int(key.split(".e")[1])
    sites = {(k["sid"], k["tag"], k["ip"]) for name in ("writes", "chain", "error_path", "forbidden_sites", "dead")
             for k in pred.get(name) or () if k["donor"] == place_ and (k["sid"], k["tag"]) == (sid, 2)}
    return key, sites


def visit_windows8(log: list, pred: dict) -> list:
    """WALK (b)'s windows (research/o8_design.md 5.3), ONE PER VISIT (each table cell): ``{"donor", "visit", "lo",
    "hi", "doors", "knight"}`` -- ``lo`` its first step row's ``frame0``; ``hi`` its last done row's end
    (o7_castle_walk._row_end; none done: its last row's ``frame``); ``doors`` each trigger's door read from its ``to``
    (:func:`door_sites8`) with ``after`` the trigger step's FIRST ``frame0``: its tag-2 store SITES are exempt anywhere
    after it, matched by site -- never bounded by a read loss frame; ``knight`` the seat watch's site (164 e1 t1 ip230)
    with THE EXEMPT SPAN (:func:`exempt_span`), in the knight's place alone."""
    sw = pred.get("seat_watch") or {}
    out = []
    for c in pred.get("table") or ():
        rows = C7.cell_rows(log, c)
        if not rows:
            continue
        done = [r for r in rows if r.get("outcome") == "done"]
        doors = []
        for n, s in enumerate(c["steps"]):
            if s.get("kind") != "trigger" or s.get("to") is None:
                continue
            key, sites = door_sites8(pred, c["donor"], s["to"])
            doors.append({"key": key, "sites": sorted(sites),
                          "after": next((r.get("frame0") for r in rows if r.get("n") == n), None)})
        knight = None
        if sw and c["donor"] == sw.get("donor"):
            lo, hi = exempt_span(rows, c["donor"])
            knight = {"site": tuple(sw["site"][1:]), "lo": lo, "hi": hi}
        out.append({"donor": c["donor"], "visit": c.get("visit"), "lo": rows[0].get("frame0"),
                    "hi": C7._row_end(done[-1]) if done else rows[-1].get("frame"), "doors": doors, "knight": knight})
    return out


def knight_rows(log: list, pred: dict) -> dict:
    """The seat watch's rows of a run (``{"seat": row | None, "start1": row | None, "errors": [observe_error rows]}``),
    its knight's place's first visit."""
    sw = pred.get("seat_watch") or {}
    ks = [x for x in log or () if x.get("k") == "knight" and x.get("sid") == sw.get("sid")]
    return {"seat": next((x for x in ks if x.get("what") == "seat"), None),
            "start1": next((x for x in ks if x.get("what") == "start1"), None),
            "errors": [x for x in log or () if x.get("k") == "observe_error"]}


def _skip_like(row: dict) -> bool:
    """Whether a ``choice`` row's dialog is the skip dialog, by its text or by its SHAPE (segment_drive.skip_answer /
    skip_shaped over the row's options)."""
    ch = {k: row.get(k) for k in ("options", "active", "selected", "count")}
    return SD.skip_answer(ch) is not None or SD.skip_shaped(ch)


def movie_span(r: dict, pred: dict, members: dict) -> dict:
    """THE MOVIE'S SPAN of one run (research/o8_design.md 5.1, 5.3): ``(f502, f863]`` -- AFTER the 166 e6 t1 ip502 row's
    frame through the ip863 row's, both read by PLACE at the side's own field of 166 -- and what lies in it: the clock
    rows (those with a write time ``timed``; a None ``mtime`` skipped), the movie's fps (the frame difference over the
    write-time difference of the first and last timed rows: the rate measured INSIDE the span) and its seconds, the
    driver's ``press`` rows (by ``pre.frame``), the ``choice`` rows (by ``frame``; each skip-shaped or not), the
    ``skip_seen`` rows, and ``unclocked`` (fewer than two timed rows, or none 300 frames apart)."""
    mv = pred.get("movie") or {}
    d = mv.get("donor")
    fld = _fld_of(members, d)
    rows = r.get("rows") or []
    log = r.get("log") or []

    def frame_of(site):
        x = next((x for x in rows if x.k == "w" and place(x.fld, members) == d and x.fld == fld
                  and (x.sid, x.tag, x.ip) == tuple(site[1:])), None)
        return None if x is None else x.f
    f502, f863 = frame_of(mv.get("from") or [0, 0, 0, 0]), frame_of(mv.get("to") or [0, 0, 0, 0])
    out = {"f502": f502, "f863": f863, "clocks": [], "timed": [], "skipped": 0, "fps": None, "s": None,
           "presses": [], "choices": [], "skips": [], "unclocked": True}
    if f502 is None or f863 is None:
        return out

    def inside(f) -> bool:
        return f is not None and f502 < f <= f863
    clocks = [x for x in log if x.get("k") == "clock" and inside(x.get("frame"))]
    timed = [x for x in clocks if x.get("mtime") is not None]
    out.update(clocks=clocks, timed=timed, skipped=len(clocks) - len(timed))
    if len(timed) >= 2 and timed[-1]["frame"] - timed[0]["frame"] >= 300:
        dt = float(timed[-1]["mtime"]) - float(timed[0]["mtime"])
        if dt > 0:
            out["fps"] = round((timed[-1]["frame"] - timed[0]["frame"]) / dt, 2)
            out["s"] = round((f863 - f502) / out["fps"], 2)
            out["unclocked"] = False
    out["presses"] = [x for x in log if x.get("k") == "press" and inside((x.get("pre") or {}).get("frame"))]
    out["choices"] = [x for x in log if x.get("k") == "choice" and inside(x.get("frame"))]
    out["skips"] = [x for x in log if x.get("k") == "skip_seen" and inside(x.get("frame"))]
    return out


def movie_reasons(span: dict) -> list:
    """A-MOVIE's reasons for one run's span (research/o8_design.md 5.1; the reviews' A1 and B3), each opening with
    :data:`MOVIE_SPAN`: a press of the driver's in it; a skip dialog in it (a ``skip_seen`` row, or a skip-shaped
    ``choice`` row) -- "answered at its default (rule n)" when a press of the driver's in the span precedes it, else
    "outside input"; an UNCLOCKED span. A ``choice`` row of any other shape gives none: O8-MOVIE (a) fails it."""
    if span.get("f502") is None or span.get("f863") is None:
        return []
    head = f"{MOVIE_SPAN} (frames {span['f502']}-{span['f863']})"
    out = [f"{head}: the driver's press at frame {(p.get('pre') or {}).get('frame')} (why {p.get('why')})"
           for p in span["presses"]]
    dialogs = [("seen", x["frame"], x) for x in span["skips"]]
    dialogs += [("choice", x["frame"], x) for x in span["choices"] if _skip_like(x)
                and not any(s["frame"] <= x["frame"] for s in span["skips"])]
    for kind, f, x in sorted(dialogs, key=lambda t: t[1]):
        pressed = any((p.get("pre") or {}).get("frame") is not None and p["pre"]["frame"] <= f for p in span["presses"])
        ans = x if kind == "choice" else next((c for c in span["choices"] if c["frame"] >= f and _skip_like(c)), None)
        how = "" if ans is None else f", answered at its default (rule {ans.get('rule')})"
        if pressed:
            out.append(f"{head}: a skip dialog at frame {f}{how}")
        else:
            out.append(f"{head}: a skip dialog at frame {f} with no press of the driver's behind it{how}: outside input "
                       f"the witness did not catch (only a Confirm opens it, FieldHUD.cs:275-285)")
    if span["unclocked"]:
        out.append(f"{head}: unclocked ({len(span['timed'])} clock rows with a write time)")
    return out


def seam_spec(pred: dict) -> dict:
    """THE SEAM's registration as O8-SEAM reads it (research/o8_design.md 4.10, 5.3): ``seam`` with its exit row's
    target, ``old`` (the chain key before the last; the first's: the warp's entrance) and ``new`` read off the CHAIN --
    its last key, never typed -- its ``fields`` (default ``[to]``) and the cut row (``landing.end_row``)."""
    seam = dict(pred.get("seam") or {})
    chain = list(pred.get("chain") or ())
    last = chain[-1] if chain else None
    if last is not None:
        seam.setdefault("exit", [last["donor"], last["sid"], last["tag"], last["ip"]])
        seam.update(target=last["target"], new=last["value"],
                    old=chain[-2]["value"] if len(chain) > 1 else int(pred.get("entrance", 0)))
    seam.setdefault("fields", [seam.get("to")])
    er = (pred.get("landing") or {}).get("end_row") or {}
    seam.setdefault("cut", {k: er.get(k, v) for k, v in (("sid", 0), ("tag", 0), ("ip", 22),
                                                         ("target", "Global.Bit[191]"), ("value", 0))})
    return seam


def seam_problems(r: dict, seam: dict, members: dict, *, side: str) -> list:
    """O8-SEAM over one covered run (research/o8_design.md 5.3; decision 8; critique #3), pure and parameterised by the
    registration ``seam`` (:func:`seam_spec`: the O3 fixture runs it on story-o3): ``[problem]``, each clause named --
      (a) F: exactly ONE ``Seam`` in the run's digest, ``(frm, donor, to, fields) == (member(donor), donor, to,
          fields)`` -- zero FAILS ("no seam: the run never left the members"), two FAIL;
      (b) F: its ``exit`` row ``(fld, sid, tag, ip, target, old, new)`` the registered exit at member(donor);
      (c) F: no seam key;
      (d) both sides: the cut row is a ``w`` row at ``to`` (fld and don: REAL), the registered cut site and value;
      (e) both sides: the last ``w``/``r`` row before the cut (``c``/``e`` rows aside) is the exit row at the side's
          own field of the donor -- nothing between the exit and the landing.
    (f) S has no members, so no seam can arise there: said by the caller, never counted as a pass."""
    bad = []
    donor, to = seam.get("donor"), seam.get("to")
    frm = _fld_of(members, donor) if members else None
    fld = _fld_of(members, donor) if side == "F" else donor
    ex = list(seam.get("exit") or [donor, 0, 0, 0])
    if side == "F":
        d = r.get("digest")
        seams = list(getattr(d, "seams", None) or ())
        if not seams:
            bad.append("(a) no seam: the run never left the members")
        elif len(seams) > 1:
            bad.append(f"(a) {len(seams)} seams: " + ", ".join(f"{s.frm} -> {s.to} {list(s.fields)}" for s in seams[:3]))
        else:
            s = seams[0]
            if (s.frm, s.donor, s.to, list(s.fields)) != (frm, donor, to, list(seam.get("fields") or [to])):
                bad.append(f"(a) the seam {s.frm} (donor {s.donor}) -> {s.to} {list(s.fields)}, want member({donor}) "
                           f"[{frm}] -> {to} {list(seam.get('fields') or [to])}")
            e = s.exit
            want = (frm, ex[1], ex[2], ex[3], seam.get("target"), seam.get("old"), seam.get("new"))
            got = None if e is None else (e.fld, e.sid, e.tag, e.ip, e.target, e.old, e.new)
            if got != want:
                bad.append(f"(b) the seam's exit row {got}, want {want}")
        if d is not None and getattr(d, "seam_keys", None):
            bad.append(f"(c) {len(d.seam_keys)} seam key(s): {ST._show(d.seam_keys, 3)}")
    cr = r.get("cut_row")
    cut = seam.get("cut") or {"sid": 0, "tag": 0, "ip": 22, "target": "Global.Bit[191]", "value": 0}
    if cr is None or not (cr.k == "w" and cr.fld == to and cr.don == to and (cr.sid, cr.tag, cr.ip, cr.target, cr.new)
                          == (cut["sid"], cut["tag"], cut["ip"], cut["target"], cut["value"])):
        desc = ("no row" if cr is None else f"{cr.k} fld {cr.fld} don {cr.don} "
                + (A._row_text(cr) if cr.k == "w" else f"byte {cr.byte} {cr.old}->{cr.new}"))
        bad.append(f"(d) the cut row is {desc}, not w {to} e{cut['sid']} t{cut['tag']} ip{cut['ip']} {cut['target']}="
                   f"{cut['value']} at fld {to} don {to} (REAL)")
    wr = [x for x in r.get("rows") or () if x.k in ("w", "r")]
    last = wr[-1] if wr else None
    if last is None or not (last.k == "w" and place(last.fld, members if side == "F" else {}) == donor
                            and last.fld == fld and (last.sid, last.tag, last.ip) == tuple(ex[1:])):
        desc = ("none" if last is None else (A._row_text(last) if last.k == "w" else f"r {last.fld} byte {last.byte}"))
        bad.append(f"(e) the last w/r row before the cut is {desc}, not {donor} e{ex[1]} t{ex[2]} ip{ex[3]} at fld {fld}")
    return bad


# ======================================================================== the observe hooks (never raise)
def _guarded(name: str, fn, log: list):
    """``fn(st, ctx)`` wrapped: an exception becomes ONE ``observe_error`` row (``{"k": "observe_error", "hook",
    "frame", "error", "n"}``, its ``n`` counting the repeats) and the hook goes on -- an exception in the drive's
    observe would end the run "STOPPED (unexpected)" (segment_trace.py:719-721; the driver review's #12)."""
    row: dict = {}

    def hook(st, ctx) -> None:
        try:
            fn(st, ctx)
        except Exception as err:                                  # noqa: BLE001 -- a record, never the run
            if row:
                row["n"] += 1
                return
            row.update({"k": "observe_error", "hook": name, "frame": getattr(st, "frame", None),
                        "error": f"{type(err).__name__}: {str(err)[:240]}", "n": 1})
            log.append(row)
    return hook


def _reading(objs, sid):
    b = next((o for o in objs or () if o.get("sid") == sid), None)
    if b is None or b.get("x") is None or b.get("z") is None:
        return None
    return round(float(b["x"]), 1), round(float(b["z"]), 1)


def knight_watch(g, pred: dict, log: list):
    """THE KNIGHT'S SEAT READINGS (research/o8_design.md 1.3; decision 6, critique #9; the reviews' A2, B8), the drive's
    observe hook for ``seat_watch``: it CACHES on PLACE (``ctx["donor"]``: member(164) 31256 reads as 164) and the
    visit (each arrival in a field of the place) -- every poll in the place caches the watched sid's published (x, z)
    by frame (the last 64) with the poll's field and place, the cache KEPT after he leaves the place until both its
    rows are written -- and it WRITES on any poll, whatever its place: a ``seat`` row, once a visit, on the first poll
    whose log holds the visit's step-0 row with ``wait_flag.read`` True -- the watched object's reading in the RING
    sample of ``wait_flag.frame`` (``"from": "ring"``), else the first cached reading at or after it (``"poll"``); a
    ``start1`` row, once a visit, on the first poll whose log holds the visit's first step-1 row -- the cached reading
    of exactly that row's ``frame0`` (the hook read that very sample before ``run_step`` took it). Each row's ``field``
    and ``donor`` are the READING's. ``{"k": "knight", "what", "donor", "sid", "field", "visit", "frame", "x", "z",
    "from"}``; no reading, no row. Never raises (:func:`_guarded`)."""
    sw = pred.get("seat_watch") or {}
    members = members_of(pred)
    st8 = {"visit": 0, "field": None, "inside": False, "cache": {}, "at": 0, "seat": False, "start1": False}

    def poll(st, ctx) -> None:
        if not sw:
            return
        here, fld = ctx.get("donor"), ctx.get("field")
        if here == sw["donor"]:
            if not st8["inside"] or st8["field"] != fld:
                st8.update(visit=st8["visit"] + 1, field=fld, inside=True, cache={}, at=len(log), seat=False,
                           start1=False)
            got = _reading(st.objects, sw["sid"])
            if got is not None:
                cache = st8["cache"]
                cache[st.frame] = (got[0], got[1], fld, here)
                while len(cache) > 64:
                    cache.pop(min(cache))
        else:
            st8["inside"] = False
        if not st8["visit"] or (st8["seat"] and st8["start1"]):
            return
        rows = [x for x in log[st8["at"]:] if x.get("k") == "step" and x.get("donor") == sw["donor"]]

        def write(what, frame, reading, frm) -> None:
            x, z, f, p = reading
            log.append({"k": "knight", "what": what, "donor": p, "sid": sw["sid"], "field": f, "visit": st8["visit"],
                        "frame": frame, "x": x, "z": z, "from": frm})
            st8[what] = True
        if not st8["seat"]:
            done = next((x for x in rows if x.get("n") == 0 and (x.get("wait_flag") or {}).get("read") is True), None)
            f = None if done is None else done["wait_flag"].get("frame")
            if f is not None:
                raw = next((raw for _t, raw in SD.ring_since(g, int(f) - 1) if int(raw.get("frame", -1)) == int(f)),
                           None)
                ring = None if raw is None else _reading(raw.get("objects"), sw["sid"])
                if ring is not None:
                    rf = int((raw.get("field") or {}).get("id", -1))
                    write("seat", int(f), (ring[0], ring[1], rf, place(rf, members)), "ring")
                else:
                    later = sorted(k for k in st8["cache"] if k >= int(f))
                    if later:
                        write("seat", later[0], st8["cache"][later[0]], "poll")
        if not st8["start1"]:
            s1 = next((x for x in rows if x.get("n") == 1), None)
            f0 = None if s1 is None else s1.get("frame0")
            if f0 is not None and f0 in st8["cache"]:
                write("start1", f0, st8["cache"][f0], "poll")
    return _guarded("knight_watch", poll, log)


def movie_clock(pred: dict, log: list):
    """FMV004'S CLOCK (research/o8_design.md 1.3; critique #4; the reviews' A1, A12, B6), the drive's observe hook for
    ``movie``: on every poll in the movie's place whose frame is at least ``movie.clock_every`` (30) past the last clock
    row, ``{"k": "clock", "frame", "mtime" (state.json's write time: it can be None), "field", "ui", "control",
    "windows"}``; and a ``{"k": "skip_seen", "frame", "field", "options", "prompt_empty"}`` row on the first poll of each
    opening of a published choice that IS the skip dialog by its text or by its SHAPE (segment_drive.skip_answer /
    skip_shaped: a prompt published empty or localized keeps its shape), never ``options[0]`` alone. Never raises."""
    mv = pred.get("movie") or {}
    every = int(mv.get("clock_every", 30))
    st8 = {"last": None, "open": False}

    def poll(st, ctx) -> None:
        if not mv or ctx.get("donor") != mv.get("donor"):
            st8["open"] = False
            return
        if st8["last"] is None or st.frame >= st8["last"] + every:
            log.append({"k": "clock", "frame": st.frame, "mtime": getattr(st, "mtime", None), "field": ctx.get("field"),
                        "ui": st.ui_state, "control": bool(st.control), "windows": len(list(st.texts or ()))})
            st8["last"] = st.frame
        ch = st.choice
        skip = bool(ch) and (SD.skip_answer(ch, st.texts) is not None or SD.skip_shaped(ch))
        if skip and not st8["open"]:
            opts = list(ch.get("options") or [])
            log.append({"k": "skip_seen", "frame": st.frame, "field": ctx.get("field"), "options": opts,
                        "prompt_empty": not str((opts or [""])[0] or "").strip()})
        st8["open"] = skip
    return _guarded("movie_clock", poll, log)


def o8_observe(g, pred: dict, log: list, *, extra=None):
    """O8's observe hook (research/o8_design.md 1.3): :func:`knight_watch`'s, :func:`movie_clock`'s -- neither ever
    raises -- then ``extra`` (the rehearsal recorder; only its stops may raise: ``movie_stop``)."""
    hooks = [knight_watch(g, pred, log), movie_clock(pred, log)]

    def observe(st, ctx) -> None:
        for h in hooks:
            h(st, ctx)
        if extra is not None:
            extra(st, ctx)
    return observe


# ======================================================================== O8-CENSUS (pure but for the stock reader)
def store_census8(fields, stock, pred: dict, *, sites=None, classify=None, instanced=None, reach=None) -> tuple:
    """O8-CENSUS's reader (research/o8_design.md 6.1; 0.2 #4): ``(problems, {field: Counter(class)}, proof)`` --
    :func:`o6_steiner.store_census6` (every gEventGlobal store site of each field registered, masked, start_first or in
    an inert function; THE LIVE SHARED PROOF: each ``live_shared`` entry's ``RunSharedScript`` sites exactly its
    ``callers``, each caller instanced at the route's entrance; every OTHER shared entry not run, or storeless) over
    O7's instancing seam (:func:`instanced_at8`), WITHOUT O7's refusal of any ``RunSharedScript`` in an instanced entry
    (166 e6 t1 ip489 runs the storeless e2). Then: every shared entry an instanced entry runs is a registered
    ``live_shared`` one, and holds no global store; and EVERY ``error_path`` SITE REACHABLE from some arrival value
    (:func:`reach8` with no known value: the claim review's #9 -- class membership alone could not tell an error path
    from a dead site). ``reach`` (``reach(donor, key) -> bool``) is a seam. ``proof[field]`` gains ``dispatch``,
    ``shared`` (``{sid: [callers]}`` run from an instanced entry) and ``idle`` (entries not instanced and storeless)."""
    instanced = instanced or instanced_at8
    bad, counts, proof = C6.store_census6(fields, stock, pred, sites=sites, classify=classify, instanced=instanced)
    try:
        ents = C5.visit_entrances(pred)
    except ValueError:
        return bad, counts, proof
    live = {(int(x["donor"]), int(x["sid"])) for x in pred.get("live_shared") or ()}
    for fid in fields:
        idx = stock(fid)
        if idx is None:
            continue
        pf = proof.setdefault(fid, {})
        pf["dispatch"] = C7.has_dispatch(idx)
        callers = C5.shared_sites(idx)
        pf["shared8"], pf["idle"] = {}, []
        insts = set()
        for ent in ents.get(fid) or ():
            try:
                insts |= C7.instanced_entries(idx, ent, instanced=instanced)
            except ValueError:
                continue
        for sid, runs in sorted(callers.items()):
            ran = [list(r) for r in runs if r[0] in insts]
            if not ran:
                continue
            pf["shared8"][sid] = ran
            if (fid, sid) not in live:
                bad.append(f"{fid} e{sid}: run by RunSharedScript({sid}) at {ran}, from an entry instanced at the route's "
                           f"entrance, and no live_shared entry registers it")
            elif C6._holds_store(idx, sid, sites):
                bad.append(f"{fid} e{sid}: a live shared entry that holds a global store")
        for e in idx.eb.entries:
            if e.empty or e.index in insts or e.index in callers:
                continue
            if not C6._holds_store(idx, e.index, sites):
                pf["idle"].append(e.index)
    reach = reach or (lambda d, k: reach8(stock(d), k["sid"], k["tag"], k["ip"], {}))
    ok_n = 0
    for k in pred.get("error_path") or ():
        if k["donor"] not in fields or stock(k["donor"]) is None:
            continue
        if reach(k["donor"], k):
            ok_n += 1
        else:
            bad.append(f"{k['donor']} e{k['sid']} t{k['tag']} ip{k['ip']} ({A.label(k)}): an error_path site no arrival "
                       f"value reaches (reach8): its guard cannot hold -- a dead site, not an error path")
    # a FORBIDDEN site is a store some stray action can make: one no arrival value reaches is dead (as built: the C1
    # list's mutant -- 164 e3 t2 ip215, behind Map.Bit[162] == 0 that its own ip54 set 1 first, moved to forbidden_sites)
    fb_n = 0
    for k in pred.get("forbidden_sites") or ():
        if k["donor"] not in fields or stock(k["donor"]) is None:
            continue
        if reach(k["donor"], k):
            fb_n += 1
        else:
            bad.append(f"{k['donor']} e{k['sid']} t{k['tag']} ip{k['ip']} ({A.label(k)}): a forbidden site no arrival "
                       f"value reaches (reach8): no stray action can make it -- a dead site, not forbidden")
    proof["_reach"] = {"reachable": ok_n, "of": sum(1 for k in pred.get("error_path") or () if k["donor"] in fields),
                       "forbidden": fb_n,
                       "forbidden_of": sum(1 for k in pred.get("forbidden_sites") or () if k["donor"] in fields)}
    return bad, counts, proof


# ======================================================================== O8-REGIONS (pure but for the stock reader)
def regions_problems8(pred: dict, stock, *, instanced=None) -> tuple:
    """O8-REGIONS's reader (research/o8_design.md 6.1, 4.15): ``(problems, roles Counter, gateway rows, hot-spots)`` --
    (a) every ``exit`` region's points are the first SetRegion of its (donor, entry) and every ``scan_gateways`` row of
    that entry is its (``to``, ``entrance``), its face gate as registered; (b) instanced at the place's route entrance;
    every gateway row of the route fields and every region an entrance instances registered; (c) its ``gate`` is
    :func:`height_gate` of its pinned tag 2's height test AND that test's consuming jump (a flipped jump inverts it: the
    claim review's #7; O7's ``height_test`` reads B_LT only and no jump). Any other role FAILS (no hazard, no dormant
    region), and so does a hot-spot."""
    from ff9mapkit.eventscan import scan_gateways
    instanced = instanced or instanced_at8
    try:
        ents = C5.visit_entrances(pred)
    except ValueError as err:
        return [str(err)], Counter(), 0, 0
    regions = pred.get("regions") or {}
    bad, roles = [], Counter()
    cache: dict = {}

    def inst(donor, ent):
        if (donor, ent) not in cache:
            try:
                cache[(donor, ent)] = instanced(stock(donor), ent)
            except ValueError as err:
                bad.append(f"{donor} at {ent}: {err}")
                cache[(donor, ent)] = set()
        return cache[(donor, ent)]
    gws: dict = {}
    for key, reg in sorted(regions.items()):
        head, _, rest = str(key).partition(".")
        if not head.lstrip("-").isdigit():
            bad.append(f"{key}: a region key names its place first")
            continue
        donor, role = int(head), reg.get("role")
        roles[role] += 1
        if role != "exit":
            bad.append(f"{key}: role {role!r} is not exit (O8 registers no other: no hazard, no dormant region)")
            continue
        m = re.fullmatch(r"e(\d+)", rest)
        idx = stock(donor)
        if m is None or idx is None:
            bad.append(f"{key}: an exit's key is <donor>.e<sid> of a stock script")
            continue
        e = int(m.group(1))
        pts = A.O2Segment._first_region(idx, e)
        if pts != reg.get("points"):
            bad.append(f"{key} (a): the bytes' first SetRegion is {pts}, frozen {reg.get('points')}")
        rows = gws.setdefault(donor, scan_gateways(idx.data))
        hit = [g for g in rows if g["entry"] == e]
        got = {(g["to"], g["entrance"]) for g in hit}
        if got != {(reg.get("to"), reg.get("entrance"))}:
            bad.append(f"{key} (a): scan_gateways gives {sorted(got)}, registered {[(reg.get('to'), reg.get('entrance'))]}")
        if any(g["face_gate"] != reg.get("face_gate") for g in hit):
            bad.append(f"{key} (a): a face gate {[g['face_gate'] for g in hit]}, registered {reg.get('face_gate')}")
        if not [ent for ent in ents.get(donor) or () if ("region", e) in inst(donor, ent)]:
            bad.append(f"{key} (b): an exit no route entrance of {donor} ({ents.get(donor)}) instances")
        _t, tt, _j, jt = door_gate_pins(pred, donor, e)
        want = height_gate(tt, jt)
        if want is None or reg.get("gate") != want:
            bad.append(f"{key} (c): its gate {reg.get('gate')}, its pinned tag 2's test and consuming jump read {want} "
                       f"({tt!r}, {jt!r})")
    ngw = nhot = 0
    for donor in pred["route"]:
        idx = stock(donor)
        if idx is None:
            bad.append(f"{donor}: no stock script")
            continue
        rows = gws.setdefault(donor, scan_gateways(idx.data))
        ngw += len(rows)
        for e in sorted({g["entry"] for g in rows}):
            if f"{donor}.e{e}" not in regions:
                bad.append(f"{donor}.e{e} (b): a gateway (-> {[g['to'] for g in rows if g['entry'] == e]}) in the bytes, "
                           f"not registered")
        for ent in ents.get(donor) or ():
            for kind, n in sorted(inst(donor, ent)):
                if kind == "region" and f"{donor}.e{n}" not in regions:
                    bad.append(f"{donor}.e{n} (b): a region entrance {ent} instances, not registered")
        hs = A.O2Segment.hotspot_census(idx)
        nhot += len(hs)
        for sid, h in sorted(hs.items()):
            bad.append(f"hot-spot {donor} e{sid} ({h['x']}, {h['z']}): in the bytes; O8 registers none")
    return bad, roles, ngw, nhot


# ======================================================================== O8-GOALS (height-aware; pure but for the mesh)
def _heights(wm, x, z) -> list:
    """``[(tri, published y)]`` of every OPEN triangle of PlayerWalkmesh ``wm`` under (x, z)."""
    raw = wm.mesh
    wv = raw.world_verts()
    return [(ti, -C5._tri_height(wv, raw.tris[ti], x, z)) for ti in raw.tris_at(x, z) if ti not in wm.closed]


def _y_at(wm, x, z):
    hs = _heights(wm, x, z)
    return None if not hs else hs[0][1]


def _grid_in(points, step: float = 20.0) -> list:
    """The points of a ``step``-u grid inside a region by the engine's rule (IsInQuad: content.doorface.region_contains,
    a ring of ears for 5+ points)."""
    from ff9mapkit.content import doorface
    xs, zs = [p[0] for p in points], [p[1] for p in points]
    out = []
    x = math.floor(min(xs) / step) * step
    while x <= max(xs):
        z = math.floor(min(zs) / step) * step
        while z <= max(zs):
            if doorface.region_contains(x, z, points):
                out.append((x, z))
            z += step
        x += step
    return out


def _polyline_gap(px, pz, pts) -> float:
    """The least distance from (px, pz) to the polyline ``pts``."""
    best = math.inf
    for (ax, az), (bx, bz) in zip(pts, pts[1:]):
        dx, dz = bx - ax, bz - az
        L = dx * dx + dz * dz
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L))
        best = min(best, math.hypot(px - (ax + t * dx), pz - (az + t * dz)))
    return best


def _fires_before(door: dict | None, wm, pts: list, short: float):
    """How far along the plan ``pts`` before its end a trigger's door first fires -- the first sample inside ``door``
    (the exit whose ``to`` is the step's) where its gate holds -- when that is more than ``short`` u (a walker stops
    ``clearance - wall`` short of a goal nearer a wall than his clearance: the door must fire before), else None."""
    from ff9mapkit.content import doorface
    if door is None:
        return None
    samples = list(C7._samples(pts))
    total = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    run = 0.0
    for i, (x, z) in enumerate(samples):
        if i:
            run += math.dist(samples[i - 1], (x, z))
        y = _y_at(wm, x, z)
        if y is not None and doorface.region_contains(x, z, door["points"]) and gate_holds(door.get("gate"), y):
            left = total - run
            return left if left > short else None
    return None


def least_half_width(lv, wm, pts: list, *, every: float = 10.0, reach: float = 160.0, step: float = 4.0):
    """THE PINCH on a plan (research/o8_design.md 2.5; H21's own measure): the plan ``pts`` sampled every ``every`` u on
    the step's floor ``wm``, at each sample the corridor's HALF-WIDTH -- the largest wall gap of his level
    (``lv``: harness.fakegame.Levels over the stock mesh, :meth:`Levels.wall_gap` at his PSX height) across the leg
    through it, each side only as far as his level runs (the midline: where the engine's opposing pushes average out)
    -- and the least of them: ``(half-width, x, z, published y)``, or None. A sample whose scan already passed the
    least so far is cut short."""
    best = None
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b)
        if L < 1e-6:
            continue
        ux, uz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, nz = -uz, ux
        k = 0
        while k * every <= L:
            x, z = a[0] + ux * k * every, a[1] + uz * k * every
            k += 1
            y = _y_at(wm, x, z)
            if y is None or lv.tri_under(x, z, -y) is None:
                continue
            hw, stop = 0.0, False
            for side in (1.0, -1.0):
                t = 0.0
                while t <= reach:
                    g = lv.wall_gap(x + side * t * nx, z + side * t * nz, -y)
                    if g is None:
                        break
                    hw = max(hw, g)
                    if best is not None and hw >= best[0]:
                        stop = True
                        break
                    t += step
                if stop:
                    break
            if not stop and (best is None or hw < best[0]):
                best = (round(hw, 1), x, z, y)
    return best


def goals8(pred: dict, walkmesh=None, *, cache: dict | None = None, window=None) -> tuple:
    """O8-GOALS (research/o8_design.md 6.1; HEIGHT-AWARE throughout, decision 4(c), critique #6 -- never O2-O7's XZ-only
    proofs, whose ``until_ok(until, x, z)`` RAISES on a y term: 0.2 #7), per step: ``(problems, lines)``.
      (g0) THE BASE: every key in :data:`KNOWN_STEP_KEYS8`; the step through ``step_of``; ``visits`` a walk on the
           route; the goal on an open tri of the step's floor (its closures) at least its clearance from a wall; a route
           from ``start`` round ``avoid`` at the clearance; ``closed_tris`` == :func:`band_closures` of its band;
      (g1') THE CLEARANCE: every step carries one; under the place's :data:`ENGINE_RADII` only where the plan at the
           radius fails (164 #1), else the radius;
      (g2') THE EXITS: every OTHER registered exit of the place in ``avoid`` UNLESS its gate holds on no open tri of the
           step's floor inside its polygon (a dead-level crossing); a trigger's own door never avoided;
      (g3') THE ARRIVAL'S HEIGHT (a walk with ``at_y``): every point within ``tolerance`` of the goal on open tris
           whose published heights lie inside ``at_y``, every OTHER level of the stock mesh at the goal's XZ outside it;
      (g4') THE TRIGGER'S HEIGHT (a y-until): the until AT LEAST AS STRICT as its door's gate (:func:`y_implies`: a
           loss the until accepts is one the door can cause -- the review's #4; the first-sample clause alone holds for
           any looser until); the goal inside its door's polygon on an open tri where the until holds; the planned
           route's FIRST sample where the door's gate holds inside its polygon satisfies the until; every sample inside
           ANOTHER exit's polygon stands where that exit's gate fails;
      (g5') THE WAIT POINT (a ``wait_flag``): every point within ``tolerance`` of the goal at least ``exit_slack`` +
           the place's engine radius from every registered exit;
      (g6') THE KNIGHT: ``at_y``'s low end inside his release; his seat more than his planning disc (ROUTE_BODY_MARGIN
           + his r) off step 1's planned route; his start inside it off step 0's -- step 0 then carries ``npcs``
           false -- and HIS LEVEL (the review's #2: the seat watch's ``start_y`` to ``y``, derived off the mesh along
           his walk by :func:`knight_levels` -- 11255 at his placement up to 11896 at his seat) at least 400 from every
           planned sample of loop 1 (the engine never pairs them);
      (g7') THE PINCH WINDOW (``window``, default :data:`PINCH_WINDOW`) holds the least half-width point of 164 #1's
           plan and no planned sample of loop 1."""
    from ff9mapkit import extract
    from ff9mapkit.content import doorface, pathfind
    from harness.session import Session
    walkmesh = walkmesh or extract.stock_walkmesh
    cache = {} if cache is None else cache
    window = dict(PINCH_WINDOW if window is None else window)
    regs = pred.get("regions") or {}
    sw = pred.get("seat_watch") or {}
    release = knight_release(pred)
    bad, lines = [], []
    order = list(pred.get("visits") or pred["route"])
    if not order or order[0] != pred["start"]["S"] or any(p not in pred["route"] for p in order):
        bad.append(f"(g0) visits {order}: not a walk on the route {pred['route']} from the start place "
                   f"{pred['start']['S']}")
    plans: dict = {}
    for c in pred.get("table") or ():
        donor, visit = c["donor"], c.get("visit")
        raw = C7._raw(cache, walkmesh, donor)
        full = pathfind.PlayerWalkmesh(raw)
        exits = [k for k, _p in SD.exit_regions(pred, donor)]
        radius = float(ENGINE_RADII.get(donor, C7.ENGINE_RADIUS))
        for n, s0 in enumerate(c["steps"]):
            lab = f"({donor}, {c['sc']}, {visit}) #{n}"
            unknown = sorted(set(s0) - KNOWN_STEP_KEYS8)
            if unknown:
                bad.append(f"{lab} (g0): unknown step key(s) {unknown} -- step_of passes them silently: a table that "
                           f"drives without them is a check that cannot fail")
            try:
                s = SD.step_of(pred, s0)
            except ValueError as err:
                bad.append(f"{lab} (g0): {err}")
                continue
            if s.get("start") is None:
                bad.append(f"{lab} (g0): no start")
                continue
            if s0.get("clearance") is None:
                bad.append(f"{lab} (g1'): no clearance")
                continue
            clear = float(s0["clearance"])
            band = BANDS8.get((donor, n))
            closed = sorted(int(t) for t in s.get("closed_tris") or ())
            if band is None:
                bad.append(f"{lab} (g0): no band registered for this step")
            else:
                want = band_closures(full, *band)
                if closed != want:
                    bad.append(f"{lab} (g0): its {len(closed)} closures are not band_closures {list(band)}'s "
                               f"({len(want)})")
            wm, route = C7._plan(pred, s, raw, s["start"], clear, cache)
            gx, gz = (float(v) for v in s["goal"])
            wall = wm.distance_to_boundary(gx, gz) if wm.point_on_walkmesh(gx, gz) is not None else None
            fires_first = None
            door_key = door_sites8(pred, donor, s.get("to"))[0] if s.get("to") is not None else None
            if wall is not None and wall < clear and s["kind"] == "trigger" and SD.has_y(s.get("until"))                     and route is not None:
                fires_first = _fires_before(regs.get(door_key), wm,
                                            [tuple(map(float, s["start"]))] + [tuple(p) for p in route], clear - wall)
            if wall is None or (wall < clear and not fires_first):
                bad.append(f"{lab} (g0): goal ({gx:.0f}, {gz:.0f}) "
                           + ("off the floor" if wall is None else f"{wall:.0f}u from a wall, under its clearance "
                                                                   f"{clear:.0f}"
                              + ("" if s["kind"] != "trigger" else ", and its door does not fire that far before it")))
            if route is None:
                bad.append(f"{lab} (g0): no route from ({float(s['start'][0]):.0f}, {float(s['start'][1]):.0f}) avoiding "
                           f"{s.get('avoid')} at clearance {clear:.0f}")
                continue
            pts = [tuple(map(float, s["start"]))] + [tuple(p) for p in route]
            plans[(donor, n)] = (wm, pts, s)
            length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
            lines.append(f"{lab} {s['kind']} wall " + ("off the floor" if wall is None else f"{wall:.0f}")
                         + ("" if not fires_first else f" (its door fires {fires_first:.0f}u of the plan before the "
                                                       f"goal: never reached)")
                         + f" route {len(route)} legs {length:.0f}u at {clear:.0f}")
            # (g1')
            if clear < radius:
                _wm, at_r = C7._plan(pred, s, raw, s["start"], radius, cache)
                if at_r is not None:
                    bad.append(f"{lab} (g1'): clearance {clear:g} under the engine radius {radius:g}, yet a route exists "
                               f"at {radius:g}")
                else:
                    lines.append(f"{lab} (g1') no route at {radius:g}, its {clear:g} the plan")
            elif clear != radius:
                bad.append(f"{lab} (g1'): clearance {clear:g}, not the place's engine radius {radius:g}")
            # (g2')
            avoid = list(s.get("avoid") or ())
            for k in exits:
                if k == door_key:
                    if k in avoid:
                        bad.append(f"{lab} (g2'): its own door {k} in its avoid")
                    continue
                if k in avoid:
                    continue
                gate = regs[k].get("gate")
                live = [(x, z, round(y)) for x, z in _grid_in(regs[k]["points"]) for _ti, y in _heights(wm, x, z)
                        if gate_holds(gate, y)]
                if live or not gate:
                    bad.append(f"{lab} (g2'): the registered exit {k} is not in its avoid, its gate {gate} holding on "
                               f"its floor inside it ({len(live)} grid points, e.g. {live[:2]})")
                else:
                    lines.append(f"{lab} (g2') {k} dead on its floor ({gate_text(gate)} nowhere inside it)")
            # (g3')
            if s["kind"] == "walk" and s.get("at_y") is not None:
                lo_y, hi_y = (float(v) for v in s["at_y"])
                tol = float(s["tolerance"])
                disc = [(gx + dx, gz + dz) for dx in range(-int(tol), int(tol) + 1, 5)
                        for dz in range(-int(tol), int(tol) + 1, 5) if math.hypot(dx, dz) <= tol]
                off, outside, ys = [], [], []
                for x, z in disc:
                    hs = _heights(wm, x, z)
                    if not hs:
                        off.append((x, z))
                        continue
                    ys += [y for _ti, y in hs]
                    if any(not lo_y <= y <= hi_y for _ti, y in hs):
                        outside.append((x, z))
                mine = {ti for ti, _y in _heights(wm, gx, gz)}
                others = sorted(round(y) for ti, y in _heights(full, gx, gz) if ti not in mine)
                inband = [y for y in others if lo_y <= y <= hi_y]
                if off or outside or inband:
                    bad.append(f"{lab} (g3'): within {tol:.0f} of the goal ({gx:.0f}, {gz:.0f}): "
                               + "; ".join(x for x in (f"{len(off)} point(s) off its floor" if off else "",
                                                      f"{len(outside)} point(s) outside at_y {s['at_y']}" if outside
                                                      else "",
                                                      f"another level at y {inband} inside at_y" if inband else "") if x))
                else:
                    lines.append(f"{lab} (g3') the goal disc ({len(disc)} points) on its level only (y {min(ys):.0f}-"
                                 f"{max(ys):.0f}), other levels at {others}")
            # (g4')
            if s["kind"] == "trigger" and SD.has_y(s.get("until")):
                door = regs.get(door_key) if door_key else None
                if door is None:
                    bad.append(f"{lab} (g4'): no registered exit leads to its to {s.get('to')}")
                else:
                    dpts, gate = door["points"], door.get("gate")
                    gy = _y_at(wm, gx, gz)
                    if not doorface.region_contains(gx, gz, dpts) or gy is None or \
                            not SD.until_ok(s["until"], gx, gz, gy):
                        bad.append(f"{lab} (g4'): the goal ({gx:.0f}, {gz:.0f}) y {gy} is not inside {door_key} on an "
                                   f"open tri where its until {s['until']} holds")
                    first, crossed = None, {}
                    for x, z in C7._samples(pts):
                        y = _y_at(wm, x, z)
                        if y is None:
                            continue
                        if first is None and doorface.region_contains(x, z, dpts) and gate_holds(gate, y):
                            first = (x, z, y)
                        for k in exits:
                            if k == door_key or not doorface.region_contains(x, z, regs[k]["points"]):
                                continue
                            if gate_holds(regs[k].get("gate"), y):
                                crossed.setdefault(k, {"live": [], "dead": []})["live"].append(round(y))
                            else:
                                crossed.setdefault(k, {"live": [], "dead": []})["dead"].append(round(y))
                    if first is None or not SD.until_ok(s["until"], first[0], first[1], first[2]):
                        bad.append(f"{lab} (g4'): the door {door_key} fires first at "
                                   + ("no sample of the plan" if first is None else
                                      f"({first[0]:.1f}, {first[1]:.1f}) y {first[2]:.0f}")
                                   + f", where its until {s['until']} does not hold: the door fires before the "
                                     f"evidence holds")
                    if not y_implies(s["until"], gate):
                        bad.append(f"{lab} (g4'): its until {s['until']} is looser than its door {door_key}'s gate "
                                   f"({gate_text(gate) if gate else 'none'}): a loss of control below the door's "
                                   f"height would read as its firing")
                    live = {k: v["live"] for k, v in crossed.items() if v["live"]}
                    if live:
                        bad.append(f"{lab} (g4'): the plan crosses another exit where its gate holds: {live}")
                    if first is not None:
                        dead = "; ".join(f"{k} crossed at y {min(v['dead'])}-{max(v['dead'])} (dead)"
                                         for k, v in sorted(crossed.items()) if v["dead"])
                        lines.append(f"{lab} (g4') fires {door_key} at ({first[0]:.1f}, {first[1]:.1f}) y {first[2]:.0f} "
                                     f"({gate_text(gate)}, its until as strict)" + (f"; {dead}" if dead else ""))
            # (g5')
            if s["kind"] == "walk" and s.get("wait_flag") is not None:
                need = float(s["exit_slack"]) + radius
                tol = float(s["tolerance"])
                disc = [(gx + dx, gz + dz) for dx in range(-int(tol), int(tol) + 1, 5)
                        for dz in range(-int(tol), int(tol) + 1, 5) if math.hypot(dx, dz) <= tol]
                gaps = {}
                for k in exits:
                    ring = [(float(a), float(b)) for a, b in regs[k]["points"]]
                    gaps[k] = min(pathfind.poly_gap(x, z, ring) for x, z in disc)
                near = {k: round(v, 1) for k, v in gaps.items() if v < need}
                if near:
                    bad.append(f"{lab} (g5'): within {tol:.0f} of the wait point, an exit nearer than exit_slack + the "
                               f"engine radius ({need:.0f}): {near}")
                else:
                    centre = {k: round(pathfind.poly_gap(gx, gz, [(float(a), float(b)) for a, b in regs[k]["points"]]),
                                       1) for k in exits}
                    lines.append(f"{lab} (g5') the wait point " + ", ".join(f"{v}u from {k}" for k, v in centre.items())
                                 + f" (every disc point >= {need:.0f})")
        # (g6') and (g7'): the knight's place
        if sw and donor == sw.get("donor"):
            p0, p1 = plans.get((donor, 0)), plans.get((donor, 1))
            disc_r = float(Session.ROUTE_BODY_MARGIN) + float(sw.get("r", 220))
            s0 = c["steps"][0] if c["steps"] else {}
            band = s0.get("at_y")
            if release is None or band is None or not gate_holds(release, float(band[0])):
                bad.append(f"{lab.rsplit(' #', 1)[0]} #0 (g6'): at_y {band}'s low end not inside his release {release}: "
                           f"a proven arrival must prove T0 passed")
            seat, start = sw.get("seat"), sw.get("start")
            if p1 is not None and seat is not None:
                gap1 = _polyline_gap(float(seat[0]), float(seat[1]), p1[1])
                if gap1 <= disc_r:
                    bad.append(f"({donor}, {c['sc']}, {visit}) #1 (g6'): his seat {seat} {gap1:.1f}u off its planned "
                               f"route, inside his planning disc {disc_r:.0f}")
            if p0 is not None and start is not None:
                gap0 = _polyline_gap(float(start[0]), float(start[1]), p0[1])
                if gap0 <= disc_r and p0[2].get("npcs", True):
                    bad.append(f"({donor}, {c['sc']}, {visit}) #0 (g6'): his start {start} {gap0:.1f}u off its planned "
                               f"route, inside his planning disc {disc_r:.0f}, and the step carries npcs true (no route)")
                # HIS LEVEL (the review's #2): placement to seat, read off the mesh along his walk -- never the seat's
                # height alone (his placement stands 641 u under it)
                lv = [y for _x, _z, y in knight_levels(pred, full)]
                sy, ky = sw.get("start_y"), sw.get("y")
                if sy is None or ky is None:
                    bad.append(f"({donor}, {c['sc']}, {visit}) #0 (g6'): the seat watch carries no start_y / y (his level)")
                    lo = hi = None
                else:
                    lo, hi = min(float(sy), float(ky)), max(float(sy), float(ky))
                    if not lv or round(lv[0]) != round(float(sy)) or round(lv[-1]) != round(float(ky)) \
                            or min(lv) < lo - 1 or max(lv) > hi + 1:
                        bad.append(f"({donor}, {c['sc']}, {visit}) #0 (g6'): his level along his walk on the mesh -- "
                                   + (f"placement {lv[0]:.0f}, seat {lv[-1]:.0f}, {min(lv):.0f}-{max(lv):.0f}" if lv
                                      else "unread")
                                   + f" -- is not the seat watch's start_y {sy} to y {ky}")
                dys = [] if lo is None else [_y_gap(y, lo, hi) for x, z in C7._samples(p0[1])
                                             for y in [_y_at(p0[0], x, z)] if y is not None]
                if lo is not None and (not dys or min(dys) < 400):
                    bad.append(f"({donor}, {c['sc']}, {visit}) #0 (g6'): loop 1 comes within "
                               f"{f'{min(dys):.0f}' if dys else '?'} of his level {lo:.0f}-{hi:.0f} (placement to "
                               f"seat) in y (the engine pairs actors at |dy| < 400)")
                if p1 is not None and seat is not None and not [b for b in bad if "(g6')" in b]:
                    lines.append(f"({donor}, {c['sc']}, {visit}) (g6') release {gate_text(release)} <= {band[0]}; seat "
                                 f"{_polyline_gap(float(seat[0]), float(seat[1]), p1[1]):.1f}u off #1 (> {disc_r:.0f}); "
                                 f"start {gap0:.1f}u off #0 (npcs {p0[2].get('npcs')}); loop 1 at least {min(dys):.0f} "
                                 f"below his level {lo:.0f}-{hi:.0f} (placement to seat, read off the mesh)")
            if p1 is not None and window.get("place") == donor:
                from harness.fakegame import Levels
                wm1, pts1, _s1 = p1
                key = ("half-width", donor, tuple(pts1))
                if key not in cache:
                    cache[key] = least_half_width(Levels(full), wm1, pts1)
                best = cache[key]

                def inwin(x, z, y) -> bool:
                    return (window["x"][0] <= x <= window["x"][1] and window["z"][0] <= z <= window["z"][1]
                            and y is not None and window["y"][0] <= y <= window["y"][1])
                loop1 = [] if p0 is None else [(round(x), round(z), round(y)) for x, z in C7._samples(p0[1])
                                               for y in [_y_at(p0[0], x, z)] if inwin(x, z, y)]
                if best is None or not inwin(best[1], best[2], best[3]) or loop1:
                    bad.append(f"({donor}, {c['sc']}, {visit}) #1 (g7'): THE PINCH WINDOW {window} "
                               + ("holds no plan" if best is None else
                                  f"{'holds' if inwin(best[1], best[2], best[3]) else 'misses'} the least half-width "
                                  f"point ({best[1]:.0f}, {best[2]:.0f}) y {best[3]:.0f} ({best[0]:.1f})")
                               + (f"; loop 1's planned samples inside it: {loop1[:3]}" if loop1 else ""))
                else:
                    lines.append(f"({donor}, {c['sc']}, {visit}) (g7') the pinch ({best[1]:.0f}, {best[2]:.0f}) y "
                                 f"{best[3]:.0f} (half-width {best[0]:.1f}) inside the window, no loop-1 sample in it")
    return bad, lines


# ======================================================================== a trace, summarised (end PLACES)
def trace_summary8(rows: list, pred: dict, *, side: str = "S", start_place: int | None = None, end_fields=None,
                   stock=None, scripts=None, log: list | None = None) -> dict:
    """One trace, summarised for a reader (research/o8_design.md 7.2; the rehearsal report and the dry run): O7's (cut
    at its start row and at its first row in an END PLACE; the crossings, the raced targets' last pre-cut rows, the
    start reads' olds) with O8's -- the knight's ip230 row (frame, line) against the chain row 164 e2 t2 ip243's, the
    movie's span rows (166 e6 t1 ip502 and ip863 frames), the cut row, and on F the digest's seams."""
    out = C7.trace_summary(rows, pred, side=side, start_place=start_place, end_fields=end_fields, stock=stock,
                           scripts=scripts, log=log)
    members = members_of(pred) if side == "F" else {}
    sp = start_place if start_place is not None else place(pred["start"][side], members)
    ends = list(end_fields) if end_fields is not None else ST.side_ends(pred, side)
    places = sorted({place(f, members) for f in ends})
    kept, _at, _pre = cut_at_start(rows, sp, members)
    kept, end = cut_at_end(kept, places, members)
    sw, mv = pred.get("seat_watch") or {}, pred.get("movie") or {}

    def row_at(site):
        if not site:
            return None
        x = next((x for x in kept if x.k == "w" and place(x.fld, members) == site[0]
                  and (x.sid, x.tag, x.ip) == tuple(site[1:4])), None)
        return None if x is None else {"f": x.f, "line": x.line, "fld": x.fld, "old": x.old, "new": x.new}
    ch = next((k for k in pred.get("chain") or () if k["donor"] == sw.get("donor")), None)
    out["knight"] = {"ip230": row_at(sw.get("site")),
                     "chain": row_at(None if ch is None else [ch["donor"], ch["sid"], ch["tag"], ch["ip"]])}
    out["movie"] = {"ip502": row_at(mv.get("from")), "ip863": row_at(mv.get("to"))}
    cut_row = next((x for x in rows if x.line == end), None) if end is not None else None
    out["cut_row"] = None if cut_row is None else {"k": cut_row.k, "fld": cut_row.fld, "don": cut_row.don,
                                                   "f": cut_row.f, "text": A._row_text(cut_row) if cut_row.k == "w"
                                                   else f"byte {cut_row.byte}"}
    seams = []
    if side == "F":
        stock_ = stock or T.stock_script_source()
        try:
            d = T.digest("summary8", kept, scripts=scripts or stock_, donor_scripts=stock_, members=members or None)
            seams = [{"frm": s.frm, "donor": s.donor, "to": s.to, "fields": list(s.fields), "line": s.line,
                      "exit": None if s.exit is None else A._row_text(s.exit)} for s in d.seams]
        except T.TraceError:
            seams = []
    out["seams"] = seams
    return out


def _trace_report8(tr: dict) -> list:
    """The trace summary's lines (7.2): O7's, with the knight's row, the movie's span rows, the cut row and the
    seams."""
    if not tr:
        return ["    trace: none (untraced, or no rows)"]
    L = C7._trace_report7(tr)
    kn = tr.get("knight") or {}
    L.append(f"      the knight's ip230 {kn.get('ip230')}; the chain row ip243 {kn.get('chain')}")
    mv = tr.get("movie") or {}
    L.append(f"      the movie's rows: ip502 {mv.get('ip502')}, ip863 {mv.get('ip863')}")
    L.append(f"      the cut row {tr.get('cut_row')}; seams {tr.get('seams')}")
    return L


def arrival_values8(pred: dict) -> dict:
    """The arrival's values in the end field (4.9): the pattern's last values over the raw start
    (:func:`last_values8`), SC the scenario; Map variables 0 at load (end_race8's default)."""
    vals = last_values8(pred.get("pattern") or {})
    vals["Global.UInt16[0]"] = int(pred.get("scenario", 1190))
    return vals


def end_map_held8(idx55, race_map: dict, *, items=None) -> tuple:
    """The Map variables :func:`end_proof8`'s other-function proof may HOLD (research/o8_design.md 4.9; 11.4, the
    review's #3): of the values the arrival's walk of the end field's e0 t0 left at its RET (``race_map``), exactly
    those NO other function of the field stores -- every function but e0 t0, instanced or not (a superset: sound) --
    read off each ``SET``'s lvalue (:func:`eval8`). ``({var: value}, {var: [[sid, tag, ip], ...]})``: the held values, and the
    stores that free each walked variable. Derived, never typed: stock 55's e1 t1 stores ``Map.Byte[24]`` (2 / 3 / 4 at
    ip46 / ip76 / ip106, on the scene's ``Map.Bit[231]`` handshakes) and e7 t2 ``Map.Bit[167]`` -- both free;
    ``Map.Bit[159]`` 1 and ``Map.Byte[17]`` 255 are held. ``items`` (``items(sid, tag) -> [(ip, rel, text)] | None``)
    is a seam."""
    movers: dict = {}
    for e in idx55.eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            if (e.index, f.tag) == (0, 0):
                continue
            its = (items(e.index, f.tag) if items is not None else None) or _items8(idx55, e.index, f.tag)
            for ip, _rel, t in its:
                if not t.startswith("SET("):
                    continue
                lv, _v = eval8(t, _Env8())
                if lv is not None and lv.startswith("Map."):
                    movers.setdefault(lv, []).append([e.index, f.tag, ip])
    held = {k: v for k, v in sorted((race_map or {}).items()) if k.startswith("Map.") and k not in movers}
    return held, {k: movers[k] for k in sorted(movers) if k in (race_map or {})}


def end_candidates8(pred: dict) -> set:
    """The targets the arrival's live read WOULD compare before any race is taken out (4.9): SC, every target the
    pattern writes, and :data:`UNTOUCHED8`."""
    out = {"Global.UInt16[0]"} | set(UNTOUCHED8)
    for visit in (pred.get("pattern") or {}).get("visits") or ():
        for tup in visit:
            out.add(tup[4])
    return out


def end_proof8(idx55, pred: dict, *, items=None, sites=None) -> tuple:
    """O8-KEYS (g)'s reader (research/o8_design.md 4.9; the claim review's #11; 11.4, the review's #3): ``(info,
    problems)`` -- THE RACED SET (:func:`end_race8` over stock 55's e0 t0 from the arrival's values -- the pattern's
    last values over the raw start (:func:`last_values8`), SC the scenario -- to its RET) equal to ``end_state_trace``'s
    targets, each trace site a writes or chain key with the registered value; THE OTHER FUNCTIONS: every store site in
    stock 55 outside e0 t0 of a candidate target (:func:`end_candidates8` less the raced set, with ``end_state``'s and
    ``end_state_scene``'s) tried by :func:`reach8` with ONLY the Map values no other function stores
    (:func:`end_map_held8`: never a variable a running loop moves) -- a reachable store of a LIVE ``end_state`` target
    is a problem naming the site; the targets with a reachable store are THE ARRIVAL SCENE's, ``end_state_scene`` must
    be exactly them with exactly those sites, and every candidate neither raced nor the scene's must be read live.
    ``info``: ``raced``, ``map`` (the held values), ``movers``, ``others`` (``(sid, tag, ip, target, reachable)``),
    ``scene`` (``{target: [[sid, tag, ip], ...]}``), ``yield``, ``ret``. ``items`` (``items(sid, tag) -> [(ip, rel,
    text)] | None``) and ``sites`` (``[{sid, tag, ip, target}]``) are seams (the dry run's synthetic 55)."""
    bad = []
    vals = arrival_values8(pred)
    get_items = (lambda s, t: (items(s, t) if items is not None else None) or _items8(idx55, s, t))
    try:
        race = end_race8(idx55, vals, items=get_items(0, 0))
    except ValueError as err:
        return {"raced": {}, "map": {}, "others": []}, [f"(g) the arrival's walk of 55 e0 t0 refuses: {err}"]
    raced = race["raced"]
    trace = pred.get("end_state_trace") or {}
    if set(raced) != set(trace):
        bad.append(f"(g) the raced set {sorted(raced)} (55 e0 t0 from the arrival to its RET) is not end_state_trace's "
                   f"{sorted(trace)}")
    keys = {(k["donor"], k["sid"], k["tag"], k["ip"]): k for k in list(pred.get("writes") or ())
            + list(pred.get("chain") or ())}
    for t, spec in trace.items():
        s = spec.get("site") or {}
        k = keys.get((s.get("place"), s.get("sid"), s.get("tag"), s.get("ip")))
        if k is None or k["target"] != t or k["value"] != spec.get("value"):
            bad.append(f"(g) end_state_trace {t}: its site {s} is no writes or chain key of {t} at {spec.get('value')}")
    # the Map values the proof HOLDS (the review's #3): of the walk's values at e0 t0's RET, only those no other 55
    # function stores -- derived, never typed. e1 t1 stores Map.Byte[24] on the scene's handshakes, so e10 t1's case 3
    # (UInt16[0] := 1400) is reachable: holding the arrival's 1 assumed away the loop that advances it.
    held, movers = end_map_held8(idx55, race.get("map") or {}, items=items)
    live = set(pred.get("end_state") or {})
    scene_typed = pred.get("end_state_scene") or {}
    cands = end_candidates8(pred) - set(raced)
    targets = cands | live | set(scene_typed)
    found = sites if sites is not None else P.store_sites(idx55)[0]
    others, scene = [], {}
    for s in found:
        if s.get("kind") == "unknown" or s.get("target") not in targets or (s["sid"], s["tag"]) == (0, 0):
            continue
        hit = reach8(idx55, s["sid"], s["tag"], s["ip"], held, items=get_items(s["sid"], s["tag"]))
        others.append((s["sid"], s["tag"], s["ip"], s["target"], hit))
        if hit:
            scene.setdefault(s["target"], []).append([s["sid"], s["tag"], s["ip"]])
            if s["target"] in live:
                bad.append(f"(g) 55 e{s['sid']} t{s['tag']} ip{s['ip']} stores the end_state target {s['target']} and "
                           f"is reachable on this arrival (Map values held: {held or 'none'}): the live read could "
                           f"see it")
    scene = {t: sorted(v) for t, v in sorted(scene.items())}
    typed = {t: sorted([list(x) for x in (spec or {}).get("sites") or ()]) for t, spec in sorted(scene_typed.items())}
    if typed != scene:
        bad.append(f"(g) end_state_scene {typed} is not the derivation {scene}: the targets 55's own arrival scene "
                   f"stores, each with every reachable site (never read live)")
    unread = sorted(cands - live - set(scene))
    if unread:
        bad.append(f"(g) the end state reads none of {unread}: neither raced, nor the arrival scene's, nor live")
    return {"raced": raced, "map": held, "movers": movers, "others": others, "scene": scene,
            "yield": race.get("yield"), "ret": race.get("ret")}, bad


#: O8-CENSUS's classes in the order the detail prints them (no start_first column: 164's ip22 counts masked).
CENSUS_LISTS8 = ("writes", "chain", "masked", "error_path", "forbidden_sites", "dead", "inert")


# ======================================================================== O8 on the shared engine
class O8Segment(C7.O7Segment):
    """O8 on O7's segment (research/o8_design.md 1.3): its constants and check texts, the draft predictions, the
    offline checks (O8-BUILD with the route members' pins and the RAW exit, O8-KEYS (a)-(h), O8-TEXT strict on block 3
    with 166's pages, O8-CENSUS over O7's instancing with every error path reachable, O8-REGIONS with the gates read
    through their jumps, O8-GOALS height-aware), the preflight (P-DONOR over the route donors, the `31205 55` row named
    outside; VSync pinned) and in-game capabilities (P-DONOR-LOG over 164, 165, 166 and 55), the drive with the input
    witness and O8's observe hook (the knight's seat, FMV004's clock) and a ``rate`` row, every run reseeded (164, 165,
    31256, 31257), A-START by the two START READS with their EXPLICIT races, A-MOVIE and A-KNIGHT, the all-run checks
    (FORBIDDEN, VOID-ASYM (a)-(d) over [place, sc, visit] cells), the core checks (START, NO-SC, CHAIN, RESIDUE, WRITES
    exact, NULL, STABLE, LANDING (a)-(d), SEAM (a)-(f), WALK (a)-(c), ORDER, KNIGHT, MOVIE, PATTERN, MASKED, STATE
    (a)-(c), JOIN) and O8's report. The session loop, the cuts, the digest, the comparison and the verdict are the
    shared engine's."""

    tag = "O8"
    doc = _MODULE_DOC
    predictions = PREDICTIONS
    manifest = MANIFEST
    session_file = SESSION_FILE
    report_file = REPORT_FILE
    chain_dir = CHAIN_DIR
    build_dir = BUILD_DIR
    accept_us_build = False
    recovery = 4600
    end_session_warps = True
    AFTER_RUN = AFTER_RUN
    PRIOR_SEGMENTS = PRIOR_SEGMENTS8
    core_ids = ("START", "NO-SC", "CHAIN", "RESIDUE", "WRITES", "NULL", "STABLE", "LANDING", "SEAM", "WALK", "ORDER",
                "KNIGHT", "MOVIE", "PATTERN", "MASKED", "STATE", "JOIN")
    titles = {
        "P-CAP": "P-CAP: the engine advertises the story trace at proto 1",
        "P-OBJECTS": "P-OBJECTS: the engine publishes the field's objects (s89): 164's knight -- O8-KNIGHT's seat and "
                     "step 1's npcs plan read him",
        "P-LANG": "P-LANG: the running game's text is English(US), the language the keys, joins and text were checked "
                  "in (a US session)",
        "P-DONOR-LOG": "P-DONOR-LOG: this launch's Memoria.log shows the patchers ran and logged no ForkDonorPatch "
                       "collision for 164, 165, 166 or 55",
        "P-LAUNCH": "P-LAUNCH: every stacked patch file, Memoria.ini and the engine DLLs are older than this launch, "
                    "and the DLLs are the pinned engine",
        "P-MANIFEST": "P-MANIFEST: the frozen members are the deployed chain's (o8_forks.json: O4's, deployed)",
        "P-DEPLOY": "P-DEPLOY: every member registered once under its name, and mapped once to its donor",
        "P-EB": "P-EB: every member's live .eb (7 languages) is the offline-checked build's (O4's)",
        "P-FLOOR": "P-FLOOR: every member's deployed walkmesh is its donor's (the walks' floors)",
        "P-STOCK": "P-STOCK: no mod folder overrides stock 164, 165, 166 or 55",
        "P-TEXT3": "P-TEXT (block 3): every mod folder's text block 3 is each language's stock asset (strict)",
        "P-RECOVERY": "P-RECOVERY: the recovery field 4600 is registered in a mod folder",
        "P-DONOR": "P-DONOR: each ROUTE donor -- 164, 165 and 166 -- is forked by exactly one ForkDonorPatch row in the "
                   "stack, its member's (55 is the end, real on both sides: a row forking it is named outside)",
        "P-SETTINGS": "P-SETTINGS: the battle, cheat, hack, control (PSXMovementMethod 1), graphics (VSync 1: FMV004's "
                      "wall time) and [AnalogControl] settings are the frozen ones (Memoria.ini read the engine's way)",
        "P-PAD": "P-PAD: no XInput pad reads non-neutral (AlwaysCaptureGamepad = 1 reads a pad even unfocused)",
        "P-OVERRIDE": "P-OVERRIDE: field 70's New-Game override is the pinned one, shipped by one folder",
        "P-ENGINE": "P-ENGINE: the live x64 and x86 Assembly-CSharp.dll are the pinned engine",
        "BUILD": "O8-BUILD: every member's .eb, in all 7 languages, is its donor's in that language with only in-chain "
                 "Field() literals remapped; per language, 31256 and 31257 differ from 164 and 165 in exactly their "
                 "in-chain Field() operands, and 31258 is 166 byte for byte with its e6 t1 ip871 Field(55) RAW",
        "KEYS": "O8-KEYS: every registered key -- chain, writes, error path, forbidden and dead sites, start_first -- is "
                "a store of its variable at its ip in the donor's stock bytes, its op in the statement, its value "
                "computed; THE START-SCOPED OLDS, their set derived and each read off O7's frozen pattern; THE START "
                "READS with their explicit races; THE CARRIED VALUES derived from O1-O7's frozen keys; the route pins "
                "and their scans; THE HEIGHTS read through their jumps; THE RACED SET from 55's bytes; the movie's and "
                "the seam's pins",
        "TEXT": "O8-TEXT: the build's text block 3 is each language's stock asset, read by its resource path -- STRICT: "
                "another language's copy fails -- and route_mes holds 166's six pages and the stop page",
        "CENSUS": "O8-CENSUS: every gEventGlobal store site of 164, 165 and 166 is registered (writes, chain, masked, "
                  "start_first, error path, forbidden, dead), every error-path and forbidden site reachable from some "
                  "arrival value, and the one shared entry run on the route (166 e2) storeless",
        "REGIONS": "O8-REGIONS: every frozen region is the stock bytes' own exit, instanced at the route's entrance, its "
                   "gate read off its tag 2's height test and consuming jump; every gateway row and every instanced "
                   "region of the route registered, no hot-spot",
        "GOALS": "O8-GOALS (height-aware): every step plans at its stated clearance (one under the engine radius only "
                 "where the radius plans nothing), every live exit avoided, the walks' arrivals on their levels, the "
                 "triggers' doors firing where their evidence holds, the wait point clear of every exit, the knight's "
                 "premises, THE PINCH inside its window",
        "FROZEN": "O8-FROZEN: the predictions are the file the session recorded, unchanged",
        "COVER": "O8-COVER: at least {min_covered} covered runs a side",
        "FORBIDDEN": "O8-FORBIDDEN: no run carries a forbidden write its own driver log does not explain",
        "VOID-ASYM": "O8-VOID-ASYM: no game-caused VOID class on one side only, no side VOID in one class in every run, "
                     "no run VOID in a finding class (V19), and no game-observed V17 cause on one side only -- every "
                     "cell [place, sc, visit]",
        "START": "O8-START: every covered run starts at 164's Main_Init after only the warp's four residue rows, and 164 "
                 "takes its ambient branch from the warp's Byte[13] 1",
        "NO-SC": "O8-NO-SC: no row touches bytes 0-1 (SC) after the start: SC holds 1190 throughout",
        "CHAIN": "O8-CHAIN: bytes 2-3 (FieldEntrance) carry exactly the chain, in order, each from the last (the first "
                 "from 342)",
        "RESIDUE": "O8-RESIDUE: no unmasked residue after the start beyond the registered",
        "WRITES": "O8-WRITES: every covered run's story keys are EXACTLY the registered writes and chain",
        "NULL": "O8-NULL: STOCK ONLY and FORK ONLY are empty",
        "STABLE": "O8-STABLE: no key is written in some runs of a side and not others",
        "LANDING": "O8-LANDING: every row ran in its place's own field, each place loaded by the one before's chain "
                   "Field() with its first emitted row, 166's ip863 the last, and the end cut REAL 55's first row",
        "SEAM": "O8-SEAM: every F run crossed ONE seam, member(166) -> REAL 55, its exit 166 e6 t1 ip863, no seam key "
                "and nothing across it; every run's cut row REAL 55 e0 t0 ip22 with nothing between the exit and it",
        "WALK": "O8-WALK: THE PAIRED-WALK LAW over the four steps -- each done once with its evidence (the walks' "
                "arrival heights and the knight's wait, the triggers' losses by height in their doors), no row inside "
                "a visit's window but its door's sites and the knight's ip230 in THE EXEMPT SPAN, and every seeded "
                "field's first move judged within acos(PRIOR_AGREE)",
        "ORDER": "O8-ORDER: the knight's ip230 written once in 164's visit, before e2's chain row, inside THE EXEMPT "
                 "SPAN",
        "KNIGHT": "O8-KNIGHT: the knight read at his seat at the wait's end and at step 1's start, in 164's own field",
        "MOVIE": "O8-MOVIE: FMV004 played out -- no press and no choice in its span, its span at the rate measured "
                 "inside it at least file_s - slack_s, no skip dialog",
        "PATTERN": "O8-PATTERN: the sink's emitted row pattern EXACTLY -- each of the three visits' emitted rows in "
                   "order, no c row",
        "MASKED": "O8-MASKED: the story-noise regions written are the same on both sides",
        "STATE": "O8-STATE: the state handed to 55 is the same: each target's emitted write history in order, the end "
                 "state read live (Int16[2] and Byte[8] aside: 55's prologue races them), and their last pre-cut rows "
                 "166's ip863 and ip502 by place",
        "JOIN": "O8-JOIN: every script row joins a store in the bytes its field ran",
        "THROW": "O8-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
    }

    # -- the predictions --------------------------------------------------------------------------------------
    def draft(self) -> dict:
        return draft_predictions(Path(self.chain_dir) / "campaign.toml")

    def freeze_problems(self, pred: dict, *, live_engine=None, path=None, prior=None, o7=None, raced=None,
                        campaign=None) -> list:
        """7.3's refusals (research/o8_design.md), pure but for the live engine read (``live_engine``), the stock 55
        script :func:`end_race8` walks (``raced``: the set, a seam), O4's campaign.toml (``campaign``) and the frozen
        O1-O7 files (``prior``, ``o7``): ``[problem]`` -- see the design's 7.3 list, every bullet."""
        bad = []
        try:
            if SD.witness_of(pred) is None:
                bad.append("no witness: a walk is the driver's own input (4.11)")
        except ValueError as err:
            bad.append(str(err))
        steps = {}
        for c in pred.get("table") or ():
            for n, s in enumerate(c.get("steps") or ()):
                steps[(c.get("donor"), n)] = s
                over = sorted(set(s) & REHEARSAL_OVERLAYS8)
                if over:
                    bad.append(f"the table step {s.get('name')!r} carries a rehearsal overlay {over}")
                if "stale_slack" in s:
                    bad.append(f"the table step {s.get('name')!r} carries a typed stale_slack")
                unknown = sorted(set(s) - KNOWN_STEP_KEYS8 - REHEARSAL_OVERLAYS8 - {"stale_slack"})
                if unknown:
                    bad.append(f"the table step {s.get('name')!r} carries an unknown key {unknown}")
                if s.get("clearance") is None:
                    bad.append(f"the table step {s.get('name')!r} carries no clearance")
        if (pred.get("choices") or []) != CHOICES8:
            bad.append(f"choices {pred.get('choices')} are not exactly the skip net's two rows (2.1)")
        w0, t0, w1, t1 = (steps.get((164, 0)) or {}, steps.get((164, 1)) or {}, steps.get((165, 0)) or {},
                          steps.get((165, 1)) or {})
        if not (w0.get("at_y") and w0.get("wait_flag") and "164.e3" in (w0.get("avoid") or ())
                and w0.get("basis") == "prior" and w0.get("npcs") is False):
            bad.append("164 #0 must carry at_y, wait_flag, 164.e3 in its avoid, basis 'prior' and npcs false (2.4)")
        fallback = "unstick" in t0
        if not ("y_gt" in (t0.get("until") or {}) and t0.get("to") == 165 and t0.get("clearance") == 64
                and (not fallback or (t0.get("unstick") is False and t0.get("npcs") is False))):
            bad.append("164 #1 must carry an until with a y_gt term, to 165 and clearance 64 (after F5's fallback: unstick "
                       "false AND npcs false) (2.4, 2.5)")
        if not ("165.e3" in (w1.get("avoid") or ()) and w1.get("at_y")):
            bad.append("165 #0 must carry 165.e3 in its avoid and at_y (2.4)")
        if not ("y_gt" in (t1.get("until") or {}) and t1.get("to") == 166):
            bad.append("165 #1 must carry a y_gt until and to 166 (2.4)")
        for donor, trig in ((164, t0), (165, t1)):                # the review's #4: the until is the door's evidence
            key = door_sites8(pred, donor, trig.get("to"))[0] if trig.get("to") is not None else None
            gate = ((pred.get("regions") or {}).get(key) or {}).get("gate") if key else None
            if trig.get("until") and not (gate and y_implies(trig["until"], gate)):
                bad.append(f"{donor} #1's until {trig.get('until')} is looser than its door {key}'s gate {gate}: a loss "
                           f"below the door's height would read as its firing (the review's #4)")
        if pred.get("side_ends") != {"S": [END_FIELD], "F": [END_FIELD]}:
            bad.append(f"side_ends {pred.get('side_ends')} is not exactly {{S: [55], F: [55]}}")
        try:
            ST.side_ends_of(pred)
        except ValueError as err:
            bad.append(str(err))
        try:
            members, _names = chain_from_campaign(campaign)
            if {int(f): int(d) for f, d in (pred.get("members") or {}).items()} != members:
                bad.append("members are not O4's twenty (chain_from_campaign)")
        except (OSError, ValueError, AssertionError) as err:
            bad.append(f"O4's chain unreadable: {err}")
        ids = [int(f) for f in (pred.get("members") or {})] + [int(f) for s in SIDES
                                                               for f in (pred.get("side_ends") or {}).get(s) or ()] \
            + [int(f) for f in pred.get("route") or ()]
        o1 = sorted({f for f in ids if 31200 <= f <= 31219})
        if o1:
            bad.append(f"O1 id(s) {o1} among members, side_ends or route: O8 never enters O1's chain")
        for name in ("battles", "naming", "start_dependent", "inert"):
            if pred.get(name):
                bad.append(f"{len(pred[name])} {name} row(s): O8 registers none")
        if (pred.get("pattern") or {}).get("floating"):
            bad.append("pattern.floating is not empty: every O8 order is the bytes' or the wait's (4.16)")
        if "movies" in pred:
            bad.append("a movies key: FMV004 is PLAYED OUT (decision 7), never skipped")
        info8 = None
        try:
            if raced is None:
                info8 = end_proof8(T.stock_script_source()(END_FIELD), pred)[0]
            rset = set(raced) if raced is not None else set(info8["raced"])
        except Exception as err:                                  # noqa: BLE001 -- a refusal, said
            rset = None
            bad.append(f"the raced set could not be derived: {err}")
        if info8 is not None:                                     # the review's #3: THE ARRIVAL SCENE, derived
            scene = set(info8.get("scene") or {})
            held = sorted(scene & set(pred.get("end_state") or {}))
            if held:
                bad.append(f"arrival-scene target(s) {held} in end_state: 55's own scene stores them after the arrival "
                           f"(4.9; the review's #3)")
            if set(pred.get("end_state_scene") or {}) != scene:
                bad.append(f"end_state_scene's targets {sorted(pred.get('end_state_scene') or {})} are not the derived "
                           f"arrival scene {sorted(scene)}")
        if rset is not None:
            held = sorted(rset & set(pred.get("end_state") or {}))
            if held:
                bad.append(f"raced target(s) {held} in end_state: 55's prologue races them (4.9)")
            if set(pred.get("end_state_trace") or {}) != rset:
                bad.append(f"end_state_trace's targets {sorted(pred.get('end_state_trace') or {})} are not the raced set "
                           f"{sorted(rset)}")
        car = (pred.get("carried") or {}).get("values") or {}
        held = sorted(set(car) & set(pred.get("end_state") or {}))
        if held:
            bad.append(f"carried target(s) {held} in end_state: a raw-start value claimed as an end state (4.5)")
        try:
            segs = prior if prior is not None else prior_segments8()
            derived, problems = carried8(pred, segs)
            if problems:
                bad.append("the carried derivation refuses: " + "; ".join(problems[:3]))
            elif derived != car:
                bad.append(f"carried differs from the derivation over the frozen O1-O7 keys: {C7._dict_diff(car, derived)}")
            olds, sprob = scoped_derivation8(pred, o7 if o7 is not None else o7_frozen(), segs)
            need = {s for s, (_t, a, b) in olds.items() if a != b}
            claimed = {tuple(x["site"]) for x in pred.get("start_scoped") or ()}
            if sprob:
                bad.append("the start-scoped derivation refuses: " + "; ".join(sprob[:3]))
            elif claimed != need:
                bad.append(f"start_scoped differs from the derivation: missing {sorted(need - claimed)}, extra "
                           f"{sorted(claimed - need)}")
        except (OSError, ValueError, KeyError) as err:
            bad.append(f"the carried / start-scoped derivation could not run: {err}")
        if not pred.get("start_reads"):
            bad.append("no start_reads (4.5)")
        for sr in pred.get("start_reads") or ():
            if any(k not in sr for k in ("race", "race_value", "edge")) or sr.get("edge") not in ("before", "after"):
                bad.append(f"the start read {sr.get('site')} carries no race, race_value and edge (critique #2)")
            elif race_site8(pred, sr) is None:
                bad.append(f"the start read {sr.get('site')}: its race {sr.get('race')} := {sr.get('race_value')} is no "
                           f"pinned field-70 store")
        for name in ("seat_watch", "movie", "seam"):
            if not pred.get(name):
                bad.append(f"no {name} (4.10)")
        reh = pred.get("rehearsed") or {}
        miss = [k for k in ("stretch_s", "wait_s", "steps_s", "movie_span_s", "narrowest_pinch") if reh.get(k) is None]
        if miss:
            bad.append(f"rehearsed lacks {miss}: F2-F8's measurements (4.1)")
        b = pred.get("budget") or {}
        if reh.get("stretch_s") is not None and float(b.get("no_progress_s") or 0) < 2 * float(reh["stretch_s"]):
            bad.append(f"no_progress_s {b.get('no_progress_s')} under 2 x the longest stretch {reh['stretch_s']} (F8)")
        if reh.get("wait_s") is not None:
            tmo = float(((w0.get("wait_flag") or {}).get("timeout_s")) or 0)
            if tmo < max(15.0, 3 * float(reh["wait_s"])):
                bad.append(f"the knight wait's timeout_s {tmo} under max(15, 3 x the longest wait {reh['wait_s']}) (F2)")
        mv = pred.get("movie") or {}
        if reh.get("movie_span_s") is not None and mv and \
                float(reh["movie_span_s"]) < float(mv.get("file_s", 0)) - float(mv.get("slack_s", 0)):
            bad.append(f"the shortest movie span {reh['movie_span_s']} s is under file_s - slack_s (F3)")
        if ((pred.get("settings") or {}).get("Graphics") or {}).get("VSync") != "1":
            bad.append("settings without [Graphics] VSync '1' (4.13)")
        if not pred.get("rehearsals"):
            bad.append("no rehearsals: the freeze reads the lead's in-game rehearsal runs (7.3), none named")
        if not pred.get("rehearsal_fps"):
            bad.append("no rehearsal_fps: the render rates the rehearsals met (F14)")
        live = live_engine if live_engine is not None else C4.engine_shas(GAME)
        eng = pred.get("engine") or {}
        if any(eng.get(a) != live.get(a) for a in ("x64", "x86")):
            bad.append(f"the engine {str(eng.get('x64'))[:12]} is not the live DLLs' {str(live.get('x64'))[:12]}")
        if path is not None and Path(path).exists():
            bad.append(f"{Path(path).name} exists: the predictions are frozen. A new version is a new file")
        return bad

    def freeze(self, path=None, *, live_engine=None) -> str:
        """The freeze, once (7.3): :meth:`freeze_problems` empty before anything is written -- an existing file among
        them -- then the base's: LF, sorted keys, never over an existing file."""
        pred = self.draft()
        bad = self.freeze_problems(pred, live_engine=live_engine, path=Path(path or self.predictions),
                                   campaign=Path(self.chain_dir) / "campaign.toml")
        if bad:
            raise SystemExit("!! the draft is not freezable: " + "; ".join(bad))
        return ST.Segment.freeze(self, path)

    # -- offline ------------------------------------------------------------------------------------------------
    def offline_extra(self, pred: dict, build=None) -> list:
        stock = self.stock_source()
        return [self.text_check8(pred, build), self.census_check(pred, stock), self.regions_check(pred, stock),
                self.goals_check(pred, stock=stock)]

    def raw_exits_check(self, pred: dict, build=None, stock_lang=None) -> tuple:
        """THE RAW EXITS (6.1): ``(ok, detail)`` -- in every language, each ``route_build.raw_exits`` member's site
        decodes as ``Field(<literal>)`` with the literal itself (no member's id), and the member's bytes equal its
        donor's (a site-less member: byte for byte)."""
        from ff9mapkit.config import LANGS, ModLayout
        from ff9mapkit.eb import EbScript
        from ff9mapkit.eventscan import FIELD_OP
        stock_lang = stock_lang or ST.stock_lang()
        spec = (pred.get("route_build") or {}).get("raw_exits") or {}
        members, names = members_of(pred), {int(f): n for f, n in pred["names"].items()}
        lay = ModLayout(Path(build or self.build_dir))
        bad, n, parts = [], 0, []
        for donor_s, sites in sorted(spec.items(), key=lambda kv: int(kv[0])):
            donor = int(donor_s)
            fid = next((f for f, d in sorted(members.items()) if d == donor), None)
            if fid is None:
                bad.append(f"no member forks {donor}")
                continue
            for L in LANGS:
                p = lay.eb_path(L, f"EVT_{names[fid]}.eb.bytes")
                src = stock_lang(donor, L)
                if src is None or not p.is_file():
                    bad.append(f"{fid} ({donor}) {L}: {'no stock donor' if src is None else 'no built file'}")
                    continue
                built = p.read_bytes()
                n += 1
                if built != src:
                    bad.append(f"{fid} ({donor}) {L}: not its donor byte for byte")
                eb = EbScript.from_bytes(built)
                for sid, tag, ip, lit in sites:
                    e = next((x for x in eb.entries if x.index == sid and not x.empty), None)
                    f = None if e is None else next((x for x in e.funcs if x.tag == tag), None)
                    ins = None if f is None else next((i for i in eb.instrs(f) if i.off - e.abs_start == ip), None)
                    if ins is None or ins.op != FIELD_OP or ins.imm(0) != int(lit):
                        bad.append(f"{fid} ({donor}) {L} e{sid} t{tag} ip{ip}: "
                                   + ("no instruction" if ins is None else f"op {ins.op} imm {ins.imm(0)}")
                                   + f", not a raw Field({lit})")
            parts.append(f"member({donor}) {fid} is {donor} byte for byte with "
                         + ", ".join(f"e{s} t{t} ip{i} Field({lit}) raw" for s, t, i, lit in sites))
        return not bad, "; ".join(bad[:6]) if bad else f"{'; '.join(parts)} ({n} member files)"

    def build_check(self, pred: dict, build=None, stock_lang=None) -> tuple:
        """O8-BUILD (6.1): the base rule (every member's .eb, every language its own donor's with only in-chain
        Field() literals remapped: 140 files), then THE ROUTE MEMBERS' PINS per language (O5's machinery over
        ``route_build.fields``: "166" LISTED with no site, so its member must equal it byte for byte), then THE RAW
        EXITS (:meth:`raw_exits_check`), then the chain's route members (derived)."""
        stock_lang = stock_lang or ST.stock_lang()
        ok, what, detail = ST.Segment.build_check(self, pred, build, stock_lang)
        pok, pdetail = self.build_pins(pred, build, stock_lang)
        rok, rdetail = self.raw_exits_check(pred, build, stock_lang)
        if not (ok and pok and rok):
            return False, self.title("BUILD"), "; ".join(d for good, d in ((ok, detail), (pok, pdetail), (rok, rdetail))
                                                         if not good)
        members = members_of(pred)
        line = route_members_line(members) if all(d in members.values() for d in ROUTE_DONORS) else ""
        return True, self.title("BUILD"), f"{detail}; {pdetail}; {rdetail}" + (f"; {line}" if line else "")

    def keys_check(self, pred: dict, stock, lists=None, *, prior=None, o7=None, texts=None, scans=None, items55=None,
                   sites55=None) -> tuple:
        """O8-KEYS (6.1): (a) O2's machinery on a filtered copy -- the chain, the writes, ``error_path`` +
        ``forbidden_sites`` + ``dead``, ``start_first``: every key a store of its variable at its ip, its op in the
        statement, a compound value computed from its prior; (b) ``start_music`` one writes key; THE START-SCOPED
        OLDS -- the set derived (:func:`scoped_derivation8`), each entry's ``here`` the start's, ``after.run``
        :data:`AFTER_RUN`, ``after.source`` present, ``after.old`` off O7's frozen pattern, ``after.value`` computed;
        (c) THE START READS -- each a writes key of its target, its old the start's value, no store of its target
        before it on the route, its ``race`` resolving (:func:`race_site8`) to the pinned field-70 store of its target
        with its ``race_value``, its ``edge`` before / after; (d) THE CARRIED VALUES -- :func:`carried8` equal to the
        typed values, none in ``end_state``, none stored or read by a function the route RUNS
        (:func:`route_run_texts`), the party typed and labelled; (e) THE ROUTE PINS and THE SCANS (O7's
        ``route_pins_check``); (f) THE HEIGHTS -- every region's gate its pinned test's AND jump's
        (:func:`height_gate`), the knight's release (ip178 + ip187's JMP_IF) the seat watch's and at or under
        ``at_y``'s low end, his seat and walk read off his pins the seat watch's; (g) THE RACED SET and THE ARRIVAL
        SCENE (:func:`end_proof8`: the Map values held only where no other 55 function stores them);
        (h) THE MOVIE AND THE SEAM -- ``movie.cinematic`` / ``movie.play`` pinned Cinematic(0, 9, 1, 1) / (2, 0, 0, 0),
        ``movie.from`` the ip502 write and ``movie.to`` the chain's last key, ``seam.exit`` the chain's last key and
        ``seam.field`` pinned ``Field(<to>)``. Seams: ``prior`` and ``o7`` (the frozen files), ``texts`` / ``scans``
        (route_pins_check's), ``items55`` / ``sites55`` (:func:`end_proof8`'s)."""
        filtered = {**pred, "ladder": [], "noise": [], "start_dependent": [],
                    "forbidden_sites": list(pred["forbidden_sites"]) + list(pred["error_path"]) + list(pred["dead"])}
        ok, _what, detail = A.O2Segment.keys_check(self, filtered, stock)
        bad = [] if ok else [f"(a) {detail}"]
        writes = list(pred["writes"])
        chain = list(pred["chain"])
        site4 = {(k["donor"], k["sid"], k["tag"], k["ip"]): k for k in writes}
        sm = pred.get("start_music")
        if sm is not None:
            same = [k for k in writes if all(k[f] == sm[f] for f in ("donor", "m", "src", "sid", "tag", "ip", "off",
                                                                      "target", "value", "op"))]
            if len(same) != 1:
                bad.append(f"(b) start_music ({sm['donor']} e{sm['sid']} t{sm['tag']} ip{sm['ip']}) is {len(same)} writes "
                           f"keys, not one")
        # (b) THE START-SCOPED OLDS
        scoped = list(pred.get("start_scoped") or ())
        olds_txt, olds, need = [], {}, {}
        try:
            pred7 = o7 if o7 is not None else o7_frozen()
            tups = C7.last_tuples(pred7, sorted({x["target"] for x in scoped}))
        except (OSError, ValueError) as err:
            pred7, tups = None, {}
            bad.append(f"(b) O7's frozen pattern unreadable: {err}")
        segs = prior if prior is not None else prior_segments8()
        if pred7 is not None:
            try:
                olds, sprob = scoped_derivation8(pred, pred7, segs)
            except (OSError, ValueError, KeyError) as err:
                olds, sprob = {}, [f"unreadable: {err}"]
            bad += [f"(b) the start-scoped olds' derivation: {p}" for p in sprob]
            need = {s: v for s, v in olds.items() if v[1] != v[2]}
            claimed = {tuple(x["site"]) for x in scoped}
            for s, (t, a, b) in sorted(need.items()):
                if s not in claimed:
                    bad.append(f"(b) start-scoped {s[0]} e{s[1]} t{s[2]} ip{s[3]} {t}: its old differs -- {a} at the raw "
                               f"start, {b} after {self.AFTER_RUN} -- and no start_scoped entry claims it")
            for s in sorted(claimed):
                if s in olds and s not in need:
                    t, a, _b = olds[s]
                    bad.append(f"(b) start-scoped {s[0]} e{s[1]} t{s[2]} ip{s[3]} {t}: its olds agree -- {a} at the raw "
                               f"start and after {self.AFTER_RUN} -- so it is not start-scoped")
        for x in scoped:
            site, t, here, after = tuple(x["site"]), x["target"], x.get("here") or [], x.get("after") or {}
            lab = f"(b) start-scoped {site[0]} e{site[1]} t{site[2]} ip{site[3]} {t}"
            k = site4.get(site)
            if k is None or k["target"] != t:
                bad.append(f"{lab}: no writes key at its site")
                continue
            start_old = olds[site][1] if site in olds else START_VALUES8.get(t, 0)
            if list(here) != [start_old, k["value"]]:
                bad.append(f"{lab}: here {here}, the start gives [{start_old}, {k['value']}]")
            if after.get("run") != self.AFTER_RUN:
                bad.append(f"{lab}: after.run {after.get('run')!r} is not the class's AFTER_RUN {self.AFTER_RUN!r}")
            if not after.get("source"):
                bad.append(f"{lab}: after carries no source")
            tup = tups.get(t)
            if pred7 is not None and (tup is None or after.get("old") != tup[5]):
                bad.append(f"{lab}: after.old {after.get('old')}, O7's frozen pattern's last tuple on {t} gives "
                           f"{None if tup is None else tup[5]} ({tup})")
            got = self._after_value({**k, "after": after}, stock)
            if got is None or got != after.get("value"):
                bad.append(f"{lab}: after.value {after.get('value')}, the bytes give {got} from after.old "
                           f"{after.get('old')}")
            if tup is not None:
                olds_txt.append(f"{tup[0]} e{tup[1]} t{tup[2]} +{tup[3]} {tup[5]}")
        # (c) THE START READS
        order = [k for p in pred["route"] for k in writes + chain if k["donor"] == p]
        reads_txt = []
        for x in pred.get("start_reads") or ():
            site, t = tuple(x["site"]), x["target"]
            lab = f"(c) start read {site[0]} e{site[1]} t{site[2]} ip{site[3]} {t}"
            k = site4.get(site)
            if k is None or k["target"] != t:
                bad.append(f"{lab}: no writes key of {t} at its site")
                continue
            if x.get("old") != START_VALUES8.get(t, 0):
                bad.append(f"{lab}: old {x.get('old')}, the start leaves {START_VALUES8.get(t, 0)}")
            i = next(j for j, y in enumerate(order) if y is k)
            before = [y for y in order[:i] if y["target"] == t]
            if before:
                bad.append(f"{lab}: {A.label(before[0])} stores {t} before it on the route")
            race = race_site8(pred, x)
            if race is None:
                bad.append(f"{lab}: its race {x.get('race')} := {x.get('race_value')} is no pinned field-70 store of {t}")
            if x.get("edge") not in ("before", "after"):
                bad.append(f"{lab}: edge {x.get('edge')!r} is not before / after")
            reads_txt.append(f"{site[0]} ip{site[3]} {t.split('.', 1)[1]} old {x.get('old')}"
                             + ("" if race is None else f", race {race[0]} ip{race[3]} := {x.get('race_value')}, "
                                                        f"{x.get('edge')}"))
        # (d) THE CARRIED VALUES
        car = pred.get("carried") or {}
        typed = car.get("values") or {}
        try:
            derived, problems = carried8(pred, segs)
        except (OSError, ValueError, KeyError) as err:
            derived, problems = {}, [f"unreadable: {err}"]
        bad += [f"(d) carried: the derivation refuses: {p}" for p in problems[:3]]
        if derived != typed:
            bad.append(f"(d) carried: the typed values differ from the derivation over the frozen O1-O7 keys: "
                       f"{C7._dict_diff(typed, derived)}")
        held = sorted(set(typed) & set(pred.get("end_state") or {}))
        if held:
            bad.append(f"(d) carried: {held} in end_state (a raw-start value claimed as an end state)")
        try:
            ents = C5.visit_entrances(pred)
        except ValueError as err:
            ents = {}
            bad.append(f"(d) {err}")
        used, talked = [], set()
        for fid in pred["route"]:
            idx = stock(fid)
            if idx is None:
                continue
            for ent in ents.get(fid) or ():
                rows = (scans or {}).get(fid) if scans is not None and fid in scans else route_run_texts(idx, ent)
                talked |= {(fid, s, t) for s, t, _ip, _x in C7.instanced_texts(idx, ent)} - {(fid, s, t)
                                                                                             for s, t, _ip, _x in rows}
                for sid, tag, ip, t in rows:
                    for tgt in typed:
                        if re.search(re.escape(tgt) + r"(?![\d\]])", t):
                            used.append(f"{fid} e{sid} t{tag} ip{ip} {tgt}")
        if used:
            bad.append(f"(d) carried: read or stored by a function the route runs: {used[:4]}")
        party = car.get("party") or {}
        if not party.get("values") or not party.get("source"):
            bad.append("(d) carried: the party is typed and labelled (values and source), never derived")
        # (e) the route pins and their scans
        pok, pdetail = self.route_pins_check(pred, stock, texts=texts, scans=scans)
        if not pok:
            bad.append(f"(e) {pdetail}")
        # (f) THE HEIGHTS
        gates = []
        for key, reg in sorted((pred.get("regions") or {}).items()):
            if reg.get("role") != "exit" or ".e" not in key:
                continue
            d, e = int(key.split(".")[0]), int(key.split(".e")[1])
            _ts, tt, _js, jt = door_gate_pins(pred, d, e)
            want = height_gate(tt, jt)
            if want is None or reg.get("gate") != want:
                bad.append(f"(f) {key}: its gate {reg.get('gate')}, its pinned test and consuming jump read {want}")
            else:
                gates.append(gate_text(want))
        sw = pred.get("seat_watch") or {}
        rel = knight_release(pred)
        w0 = next((c["steps"][0] for c in pred.get("table") or () if c["donor"] == sw.get("donor") and c["steps"]), {})
        if rel is None or rel != sw.get("release"):
            bad.append(f"(f) the knight's release read off ip178 + ip187 is {rel}, the seat watch says {sw.get('release')}")
        elif not w0.get("at_y") or not gate_holds(rel, float(w0["at_y"][0])):
            bad.append(f"(f) the knight's release {rel} does not hold at at_y's low end {w0.get('at_y')}")
        start, _pts, walk_u, seat = knight_walk(pred)
        if start is None or seat is None or [round(v) for v in start] != list(sw.get("start") or []) \
                or [round(v) for v in seat] != list(sw.get("seat") or []) or abs(walk_u - float(sw.get("walk_u", 0))) > 0.05:
            bad.append(f"(f) the knight's pins read start {start}, seat {seat}, walk {walk_u}u -- the seat watch says "
                       f"{sw.get('start')}, {sw.get('seat')}, {sw.get('walk_u')}u")
        # (g) THE RACED SET
        idx55 = stock(END_FIELD)
        if idx55 is None:
            bad.append(f"(g) no stock script for {END_FIELD}")
            info = {"raced": {}, "map": {}, "others": []}
        else:
            info, gbad = end_proof8(idx55, pred, items=items55, sites=sites55)
            bad += gbad
        # (h) THE MOVIE AND THE SEAM
        mv, sm8 = pred.get("movie") or {}, pred.get("seam") or {}
        last = chain[-1] if chain else {}
        lastsite = [last.get("donor"), last.get("sid"), last.get("tag"), last.get("ip")]
        if pin_text(pred, mv.get("cinematic") or []) != "Cinematic(0, 9, 1, 1)" or \
                pin_text(pred, mv.get("play") or []) != "Cinematic(2, 0, 0, 0)":
            bad.append(f"(h) the movie's cinematic {mv.get('cinematic')} / play {mv.get('play')} are not the pinned "
                       f"Cinematic(0, 9, 1, 1) / Cinematic(2, 0, 0, 0)")
        frm = site4.get(tuple(mv.get("from") or ()))
        if frm is None or list(mv.get("to") or []) != lastsite:
            bad.append(f"(h) the movie's from {mv.get('from')} is no writes key, or its to {mv.get('to')} is not the "
                       f"chain's last key {lastsite}")
        if list(sm8.get("exit") or []) != lastsite or pin_text(pred, sm8.get("field") or []) != f"Field({sm8.get('to')})":
            bad.append(f"(h) the seam's exit {sm8.get('exit')} is not the chain's last key {lastsite}, or its field "
                       f"{sm8.get('field')} is not a pinned Field({sm8.get('to')})")
        if bad:
            return False, self.title("KEYS"), "; ".join(bad)[:1800]
        m = re.match(r"(\d+) sites \((\d+) keys\), every op in its statement, (\d+) compound values", detail)
        nsites, nkeys = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
        comp = [k for name in ("writes", "forbidden_sites", "error_path", "dead") for k in pred.get(name) or ()
                if k.get("op") in ("|=", "&=", "++")]
        others = list(info.get("others") or ())
        scene8 = info.get("scene") or {}
        freed = "; ".join(f"{k} by " + ", ".join(sorted({f"e{a} t{b}" for a, b, _i in v}))
                          for k, v in (info.get("movers") or {}).items()) or "none"
        talk = "; ".join(f"{f} " + ", ".join(f"e{s} t{t}" for ff, s, t in sorted(talked) if ff == f)
                         for f in sorted({f for f, _s, _t in talked})) or "none"
        mapv = ", ".join(f"{k} {v}" for k, v in (info.get("map") or {}).items()) or "no Map value"
        livet = set(pred.get("end_state") or {})
        live_sites = [o for o in others if o[3] in livet]
        seat = sw.get("seat") or ["?", "?"]
        return (True, self.title("KEYS"),
                f"{nkeys} keys over {nsites} distinct sites, every op in its statement, {len(comp)} compound values "
                f"computed from their priors (" + "; ".join(f"{k['donor']} e{k['sid']} t{k['tag']} ip{k['ip']} "
                                                          f"{k['op']} after ip{str(k.get('prior')).split('/')[-1]}"
                                                          for k in comp)
                + f"), none masked but start_first; start_music one writes key ({sm['donor']} ip{sm['ip']} from "
                  f"{sm.get('old')}); {len(scoped)} start-scoped olds, derived, after.run {self.AFTER_RUN}, after.old "
                  f"from O7's frozen pattern ({', '.join(olds_txt)}); {len(reads_txt)} start reads ("
                + "; ".join(reads_txt) + f"); {len(derived)} carried values derived from {len(segs)} frozen segments "
                  f"(no end-state disagreement), equal to the typed ones, none in end_state, none stored or read by a "
                  f"function the route runs ({talk} set aside: the knight's talk); {pdetail}; {len(gates)} gates read "
                  f"({', '.join(gates)}); the knight released at {gate_text(rel)} (ip187's loop), seated at "
                  f"({seat[0]}, {seat[1]}) after {walk_u}u; the raced set "
                  f"{{{', '.join(t.split('.', 1)[1] for t in sorted(info.get('raced') or {}))}}} from 55's e0 t0 to "
                  f"its RET (ip{info.get('ret')}); the Map values held {mapv} (freed by another function: {freed}); "
                  f"{len(live_sites)} other 55 store(s) of a live end_state target, none reachable"
                + "".join(f", e{s} t{t} ip{i} {tg.split('.', 1)[1]}" for s, t, i, tg, _h in live_sites)
                + "; the arrival scene's reachable stores, never read live (SC rests on O8-NO-SC through the cut): "
                + ", ".join(f"e{a} t{b} ip{i} {tg.split('.', 1)[1]}" for tg, v in scene8.items() for a, b, i in v)
                + "; FMV004's Cinematic pins; the seam's exit "
                  f"{lastsite[0]} e{lastsite[1]} t{lastsite[2]} ip{lastsite[3]} and its Field({sm8.get('to')})")

    def text_check8(self, pred: dict, build=None, stock_text=None, *, mes=None) -> tuple:
        """O8-TEXT (6.1): O4's ``text_check`` on block 3, STRICT, then ``route_mes`` on block 3's US source (``mes``,
        ``{mes id: source}``, a seam): each of 166's pages holds its text, and the stop page's mes holds every stop
        page's match."""
        ok, what, detail = self.text_check(pred, build, stock_text)
        rm = pred.get("route_mes") or {}
        if mes is None:
            from ff9mapkit import dialogue
            body = A.stock_text_assets(int(rm.get("block", TEXT_BLOCK)))[pred.get("lang", SESSION_LANG)]
            body = body.decode("utf-8", errors="replace") if isinstance(body, (bytes, bytearray)) else str(body)
            mes = {i: x.text for i, x in dialogue.parse_mes(body).items()}
        bad, parts = [], []
        for p in rm.get("pages") or ():
            if str(p.get("holds")) not in str(mes.get(p.get("mes")) or ""):
                bad.append(f"mes {p.get('mes')} does not hold {p.get('holds')!r}")
            else:
                parts.append(str(p["mes"]))
        sp = rm.get("stop_page") or {}
        for p in pred.get("stop_pages") or ():
            if p["match"] not in str(mes.get(sp.get("mes")) or ""):
                bad.append(f"mes {sp.get('mes')} does not hold the stop page {p['match']!r}")
        if sp and str(sp.get("holds")) not in str(mes.get(sp.get("mes")) or ""):
            bad.append(f"mes {sp.get('mes')} does not hold {sp.get('holds')!r}")
        if bad or not ok:
            return False, self.title("TEXT"), "; ".join(([detail] if not ok else []) + bad)
        holds = {str(p.get("holds")) for p in rm.get("pages") or ()}
        return (True, self.title("TEXT"),
                f"{detail}; mes {', '.join(parts)} {' / '.join(sorted(holds))}, {sp.get('mes')} {sp.get('holds')!r}")

    def census_check(self, pred: dict, stock, *, sites=None, classify=None, instanced=None, reach=None) -> tuple:
        """O8-CENSUS (6.1): :func:`store_census8` over the route's stock fields -- each field's total and per-class
        counts as the census found them (DERIVED), every error-path guard reachable, the shared entry run on the route
        storeless, the entries neither instanced nor storeful named -- or each failure named."""
        fields = list(pred["route"])
        bad, counts, proof = store_census8(fields, stock, pred, sites=sites, classify=classify, instanced=instanced,
                                           reach=reach)
        if bad:
            return False, self.title("CENSUS"), f"{len(bad)} problem(s): " + "; ".join(bad[:8])
        short = {"error_path": "error", "forbidden_sites": "forbidden"}
        per = []
        for f in fields:
            tot = sum(v for k, v in counts[f].items() if k != "unresolved")
            per.append(f"{f}: {tot} (" + ", ".join(f"{short.get(nm, nm)} {counts[f].get(nm, 0)}" for nm in CENSUS_LISTS8)
                       + ")")
        unres = sum(counts[f].get("unresolved", 0) for f in fields)
        rr = proof.get("_reach") or {}
        dead97 = [f"{k['donor']}" for k in pred.get("dead") or () if (k["sid"], k["tag"], k["ip"]) == (0, 0, 97)]
        plain = [f for f in fields if not (proof.get(f) or {}).get("dispatch")]
        shared = "; ".join(f"{f} e{sid} shared from " + ", ".join(f"e{e} t{t} ip{i}" for e, t, i in runs)
                           + ", storeless" for f in fields for sid, runs in sorted(((proof.get(f) or {}).get("shared8")
                                                                                     or {}).items()))
        idle = "; ".join(f"{f} e{sid} not instanced, storeless" for f in fields for sid in (proof.get(f) or {}).get(
            "idle") or ())
        return (True, self.title("CENSUS"),
                "; ".join(per) + f"; {unres} unresolved; every error-path guard reachable ({rr.get('reachable')} of "
                f"{rr.get('of')}" + (f"; {' and '.join(dead97)} ip97 dead behind ip57's 385" if dead97 else "") + ")"
                + f"; every forbidden site reachable ({rr.get('forbidden')} of {rr.get('forbidden_of')})"
                + (f"; {', '.join(map(str, plain))} hold no entrance dispatch (every Init reachable)" if plain else "")
                + (f"; {shared}" if shared else "") + (f"; {idle}" if idle else ""))

    def regions_check(self, pred: dict, stock, *, instanced=None) -> tuple:
        """O8-REGIONS (6.1): :func:`regions_problems8`."""
        bad, roles, ngw, nhot = regions_problems8(pred, stock, instanced=instanced)
        if bad:
            return False, self.title("REGIONS"), "; ".join(bad[:6])
        exits = [(k, r) for k, r in sorted((pred.get("regions") or {}).items()) if r.get("role") == "exit"]
        none = [str(p) for p in pred["route"] if not any(k.split(".")[0] == str(p) for k, _r in exits)]
        return (True, self.title("REGIONS"),
                f"{sum(roles.values())} regions ({roles['exit']} exit: "
                + ", ".join(f"{k} {gate_text(r.get('gate'))}" for k, r in exits)
                + f"), {nhot} hot-spots, {ngw} gateway rows all registered"
                + (f"; {', '.join(none)} none" if none else ""))

    def goals_check(self, pred: dict, walkmesh=None, *, stock=None, window=None) -> tuple:
        """O8-GOALS (6.1): :func:`goals8`, height-aware, on one plan cache."""
        bad, lines = goals8(pred, walkmesh, window=window)
        if bad:
            return False, self.title("GOALS"), "; ".join(bad)[:1800]
        n = sum(len(c["steps"]) for c in pred.get("table") or ())
        return True, self.title("GOALS"), f"{n} steps: " + "; ".join(lines)

    # -- the live install (read-only) ---------------------------------------------------------------------------
    def preflight_extra(self, pred: dict, roots: list, *, manifest=None, pads=..., live_engine=None, game=None,
                        stock_text=None) -> list:
        """6.2's extras, in order: P-TEXT (block 3, STRICT), P-RECOVERY, P-DONOR over the ROUTE donors (164, 165, 166:
        each forked by exactly one ForkDonorPatch row, its member's) with a line naming any row that forks the end
        (O1's `31205 55`) as OUTSIDE the set -- 55 is the end, real on both sides, never a member O8 enters --
        P-SETTINGS (:data:`SETTINGS8`: 32 keys, VSync among them), P-PAD, P-OVERRIDE, P-ENGINE. The seams are O5's."""
        from rung3_trace import _fork_donor_rows
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
        ok, detail = P.p_donor({**pred, "route": list(ROUTE_DONORS)}, roots)
        ends = list(pred.get("end_fields") or [pred.get("end_field")])
        outside = []
        for r in roots:
            path = Path(r) / "ForkDonorPatch.txt"
            try:
                lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
            except OSError:
                lines = []
            for n, ln in enumerate(lines, 1):
                parts = ln.split()
                if len(parts) >= 2 and parts[0].lstrip("-").isdigit() and parts[1].lstrip("-").isdigit() \
                        and int(parts[1]) in ends:
                    outside.append(f"{Path(r).name} line {n} `{parts[0]} {parts[1]}`")
        _ = _fork_donor_rows
        detail += ("; outside the set: " + (", ".join(outside) if outside else "no row forks the end")
                   + f" -- {', '.join(map(str, ends))} is the end, real on both sides: no O8 run can enter its member "
                     f"(raw Field(55), no remap)")
        out.append((ok, self.title("P-DONOR"), detail))
        want = pred.get("settings") or SETTINGS8
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
        """O7's -- P-CAP, P-OBJECTS, P-LANG, P-DONOR-LOG, P-LAUNCH with the engine, P-PAD -- with P-DONOR-LOG over
        :data:`LOG_DONORS` (164, 165, 166, 55). ``pads``, ``engine`` and ``live_engine`` are seams for the fake."""
        import dali_tour as D
        from harness.logs import MEMORIA_LOG
        out = A.O2Segment.capabilities(self, g)
        log = next((p for name, p in g._log_paths() if name == MEMORIA_LOG), None)
        try:
            text = log.read_text(encoding="utf-8", errors="replace") if log is not None else None
        except OSError:
            text = None
        ok, detail = P.p_donor_log(text, LOG_DONORS)
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

    def drive(self, g, pred: dict, side: str, log: list, *, deadline: float, progress: dict | None = None) -> dict:
        """O4's drive -- the run-wide input witness -- with O8's observe hook (:func:`o8_observe`: the knight's seat,
        FMV004's clock) and, in a ``finally``, a ``{"k": "rate", ...}`` row: the launch's measured render rate."""
        try:
            return SD.drive(g, pred, side, log, deadline=deadline, progress=progress, witness=C4.input_witness(g),
                            observe=o8_observe(g, pred, log))
        finally:
            try:
                log.append({"k": "rate", **g.rate().as_dict()})
            except Exception:                                          # noqa: BLE001 -- a record, never the run
                log.append({"k": "rate", "fps": None})

    # -- reading a session ---------------------------------------------------------------------------------------
    def why_void(self, rec: dict, r: dict, pred: dict) -> list:
        """O6's reasons (O5's A-START on 164's error path, O3's A-NOEND and the cut row), then THE START READS with
        their EXPLICIT races (4.5; critique #2) -- each read's two branches, each A-START by the driver, each reason led
        by :data:`START_READ`: THE RACED ROW (the race's own ``w`` row among the pre-start rows: before -- the trace armed
        before it ran, the warp after; after -- the warp came after the window's late edge) and THE READ (the run's row
        at the site reading another ``old`` with nothing earlier in the run touching the target's bytes) -- never O7's
        ``race_site``, which keys on the read's own old (164 ip130 -> 70 ip130, the wrong store); then A-MOVIE (5.1;
        :func:`movie_reasons`: a press, a skip dialog or an unclocked span in FMV004's span, each led by
        :data:`MOVIE_SPAN`) and A-KNIGHT (a run that reached its end without a ``seat`` or ``start1`` reading, led by
        :data:`KNIGHT_UNREAD`)."""
        out = C6.O6Segment.why_void(self, rec, r, pred)
        members = members_of(pred) if r["side"] == "F" else {}
        for sr in pred.get("start_reads") or ():
            race = race_site8(pred, sr)
            short = sr["target"].split(".", 1)[1]
            raced = None if race is None else next(
                (x for x in r.get("pre") or () if x.k == "w" and x.fld == race[0]
                 and (x.sid, x.tag, x.ip, x.target) == (race[1], race[2], race[3], sr["target"])), None)
            if raced is not None:
                where = f"field {race[0]} e{race[1]} t{race[2]} ip{race[3]} := {raced.new}"
                why = (f"{START_READ} {sr['target']}: {where} ran before the warp (line {raced.line}): the warp came "
                       f"after the window's late edge -- the start's" if sr.get("edge") == "after" else
                       f"{START_READ} {sr['target']}: {where} ran after the trace was armed, before the warp (line "
                       f"{raced.line}): the warp window's race, one window later -- the start's")
                out.append((why, "A-START", "driver"))
                continue
            d, sid, tag, ip = sr["site"]
            hit = next((x for x in r["rows"] if x.k == "w" and place(x.fld, members) == d
                        and (x.sid, x.tag, x.ip, x.target) == (sid, tag, ip, sr["target"])), None)
            if hit is None or hit.old == sr["old"]:
                continue
            span = C6._span(sr["target"])
            if any(x.line < hit.line and x.k in ("w", "r") and C6._row_span(x) & span for x in r["rows"]):
                continue
            rip = "?" if race is None else race[3]
            head = (f"{START_READ} {sr['target']} at {d} e{sid} t{tag} ip{ip} (fld {hit.fld}) reads old {hit.old}, not "
                    f"{sr['old']}, nothing earlier in the run touching it: ")
            why = (head + f"the warp left field 70 after its e0 t0 ip{rip} ({short} := {sr.get('race_value')}) -- the "
                          f"warp window's late edge -- the start's" if sr.get("edge") == "after" else
                   head + f"the warp left field 70 before its e0 t0 ip{rip} ({short} := {sr.get('race_value')}) -- the "
                          f"start's")
            out.append((why, "A-START", "driver"))
        if pred.get("movie"):
            span = movie_span(r, pred, members)
            r["movie_span"] = span
            out += [(w, "A-MOVIE", "driver") for w in movie_reasons(span)]
        sw = pred.get("seat_watch") or {}
        if sw and rec.get("end") == "reached":
            kr = knight_rows(r.get("log") or [], pred)
            miss = [w for w in ("seat", "start1") if kr[w] is None]
            if miss:
                errs = "; ".join(f"observe_error {x.get('hook')}: {x.get('error')}" for x in kr["errors"])
                out.append((f"{KNIGHT_UNREAD}: no {' and no '.join(miss)} row in {sw['donor']}'s visit -- the hook read "
                            f"no published sid {sw['sid']} at that frame" + (f" ({errs})" if errs else ""),
                            "A-KNIGHT", "driver"))
        return out

    @staticmethod
    def _void_ids(r: dict) -> set:
        """The VOID classes VOID-ASYM reads, less every reason opening with :data:`START_READ` or :data:`MOVIE_SPAN`
        (1.3): each the instrument's on either side -- the warp's timing; a press, a dialog only a press opens, or an
        unclocked span -- so a side VOID in one in every run is VOID by COVER, never NOT PROVEN by (b). A
        :data:`KNIGHT_UNREAD` reason is NOT set aside: a whole side with no published seat is an asymmetry."""
        return {(v.get("class"), tuple(v["cell"]) if v.get("cell") else None, v.get("by")) for v in r.get("void") or ()
                if not str(v.get("why") or "").startswith((START_READ, MOVIE_SPAN))}

    # -- the checks ---------------------------------------------------------------------------------------------
    def core_checks(self, runs: list, cov: dict, pred: dict) -> list:
        covered = cov["S"] + cov["F"]
        c = self.comparison(cov, pred)
        return [self.start_check(covered, pred), self.no_sc_check(covered, pred),
                self.span_check("CHAIN", covered, pred, "entrance_bytes", "chain", pred["entrance"]),
                self.residue_check(covered, pred), self.writes_check(covered, pred), self.null_check(c, pred),
                self.stable_check(c, pred), self.landing_check(cov, pred), self.seam_check(cov, c, pred),
                self.walk_check(covered, pred), self.order_check(covered, pred), self.knight_check(covered, pred),
                self.movie_check(covered, pred), self.pattern_check(covered, pred), self.masked_check(cov, pred),
                self.state_check(covered, pred), self.join_check(cov)]

    def landing_check(self, cov: dict, pred: dict) -> tuple:
        """O8-LANDING (5.3; decision 8): O7's (a)-(d) -- every field row in its place's own field and a route place;
        the crossings 164 ip243 -> 165 e0 t0 ip22 and 165 ip233 -> 166 e0 t0 ip22; 166 e6 t1 ip863 the last field row
        and the end row naming 55; the cut REAL 55 e0 t0 ip22 -- over COPIES of the covered runs whose F digests read
        no seam (O7's (e), the only reader of either, would fail every O8 F run: O8-SEAM owns the seam), its PASS
        detail's "(e) no seam" read as "(e): O8-SEAM's". The run dicts are never touched."""
        copies = {s: [dict(r, digest=SimpleNamespace(seams=[], seam_keys={})) if r.get("digest") is not None else r
                      for r in cov[s]] for s in SIDES}
        ok, _what, detail = C7.O7Segment.landing_check(self, copies, pred)
        return ok, self.title("LANDING"), detail.replace("; (e) no seam", "; (e): O8-SEAM's")

    def seam_check(self, cov: dict, c, pred: dict) -> tuple:
        """O8-SEAM (5.3; decision 8; critique #3), every covered run: :func:`seam_problems` against the registration
        (:func:`seam_spec`), plus the comparison's ``across_seam`` and ``seam_only`` empty ((c)); (f) S holds no members,
        so no seam can arise there -- said in the detail, never counted as a pass. Zero seams FAILS (O2's
        ``seam_check`` passed vacuously with none)."""
        seam = seam_spec(pred)
        members = members_of(pred)
        bad = []
        for side in SIDES:
            for r in cov[side]:
                bad += [f"{side}#{r['i']} {p}" for p in seam_problems(r, seam, members if side == "F" else {},
                                                                      side=side)]
        if c is not None and getattr(c, "across_seam", None):
            bad.append(f"(c) across the seam: {ST._show(c.across_seam, 3)}")
        if c is not None and getattr(c, "seam_only", None):
            bad.append(f"(c) seam only: {ST._show(c.seam_only, 3)}")
        frm = _fld_of(members, seam.get("donor"))
        ex = seam.get("exit") or [0, 0, 0, 0]
        return (not bad, self.title("SEAM"),
                "; ".join(bad[:6]) or f"{len(cov['F'])} F runs: (a) one seam each, member({seam.get('donor')}) [{frm}] -> "
                                      f"{seam.get('to')} {seam.get('fields')}; (b) its exit {frm} e{ex[1]} t{ex[2]} "
                                      f"ip{ex[3]} {seam.get('target')} {seam.get('old')} -> {seam.get('new')}; (c) no "
                                      f"seam key, nothing across; {len(cov['S']) + len(cov['F'])} runs: (d) the cut row "
                                      f"REAL {seam.get('to')} e0 t0 ip{(seam.get('cut') or {}).get('ip')} (don "
                                      f"{seam.get('to')}); (e) the exit row the last before it; (f) S: no members, so no "
                                      f"seam can arise (not counted)")

    def walk_check(self, covered: list, pred: dict) -> tuple:
        """O8-WALK (5.3; THE PAIRED-WALK LAW), over every covered run, each clause named:
          (a) per table step (its donor, visit and index): exactly one ``done`` row, the last of its rows, its EVIDENCE
              -- a ``walk``: its ``to`` sample in the side's field of the place with control, within ``tolerance`` of
              the goal, its ``at_y.y`` inside ``at_y`` and, with ``wait_flag``, ``wait_flag.read`` True for its flag and
              value; a ``trigger`` with ``to``: ``landed`` None (path A: its ``landed_frame`` set and the run's next
              ``visit`` row at the side's field of ``to``'s place) or that field (path B), its ``lost`` read in the
              walk's field WITH a height -- none: "no height", never ``until_ok`` (which raises on it) -- satisfying the
              ``until``, inside or within ``exit_slack`` of the exit whose ``to`` is the step's -- before it at most
              ``interrupts`` ``interrupted`` rows (none in a door) and ``attempts`` - 1 ``failed`` rows (none landed,
              none in a door);
          (b) THE VISIT WINDOW (:func:`visit_windows8`): per visit no ``w`` row from its first step row's ``frame0`` to
              its last done row's end but its doors' tag-2 store SITES after each trigger's first ``frame0`` and the
              knight's ip230 inside THE EXEMPT SPAN;
          (c) THE FIRST MOVES: per visit to a seeded place, its first step row's route ``basis`` "prior", exactly one of
              its rows carrying ``basis_check``, its angle at most acos(PRIOR_AGREE)."""
        from ff9mapkit.content import doorface, pathfind
        agree = C7.prior_agree_deg()
        seeded = set(C7.seeded_places(pred))
        regs = pred.get("regions") or {}
        bad = []
        for r in covered:
            lab = f"{r['side']}#{r['i']}"
            members = members_of(pred) if r["side"] == "F" else {}
            log = r.get("log") or []
            for c in pred.get("table") or ():
                fld = _fld_of(members, c["donor"])
                rows_c = C7.cell_rows(log, c)
                for n, s0 in enumerate(c["steps"]):
                    step = SD.step_of(pred, s0)
                    name = f"({c['donor']}, {c.get('visit')}) #{n}"
                    rows = [x for x in rows_c if x.get("n") == n]
                    done = [i for i, x in enumerate(rows) if x.get("outcome") == "done"]
                    probs = []
                    if len(done) != 1 or done[0] != len(rows) - 1:
                        probs.append(f"{len(done)} done row(s) of {len(rows)} step rows"
                                     + ("" if not rows else f" (outcomes {[x.get('outcome') for x in rows]})"))
                    else:
                        d = rows[done[0]]
                        if step["kind"] == "walk":
                            to = d.get("to") or {}
                            gx, gz = (float(v) for v in step["goal"])
                            dist = (None if to.get("x") is None or to.get("z") is None
                                    else math.hypot(float(to["x"]) - gx, float(to["z"]) - gz))
                            if d.get("field") != fld:
                                probs.append(f"the walk ran in {d.get('field')}, not {fld}")
                            if not to.get("control"):
                                probs.append(f"its to sample {to} without control")
                            if dist is None or dist > float(step["tolerance"]):
                                probs.append(f"its to sample {dist if dist is None else round(dist)}u from the goal "
                                             f"{step['goal']} (tolerance {step['tolerance']})")
                            band = step.get("at_y")
                            if band is not None:
                                ay = (d.get("at_y") or {}).get("y")
                                if ay is None or not float(band[0]) <= float(ay) <= float(band[1]):
                                    probs.append(f"its at_y.y {ay}, outside at_y {list(band)}: not the goal's level")
                            wf = step.get("wait_flag")
                            if wf is not None:
                                rec = d.get("wait_flag") or {}
                                if rec.get("read") is not True or (rec.get("flag"), rec.get("value")) != (
                                        wf["flag"], wf["value"]):
                                    probs.append(f"its wait_flag {rec.get('flag')} == {rec.get('value')} read "
                                                 f"{rec.get('read')}, want Bit[{wf['flag']}] == {wf['value']} read")
                        else:
                            want = _fld_of(members, step["to"])
                            landed = d.get("landed")
                            if landed is None:
                                if d.get("landed_frame") is None:
                                    probs.append("landed None and no landed_frame (path A's walk-out record)")
                                i = next((j for j, x in enumerate(log) if x is d), None)
                                nv = None if i is None else next((x for x in log[i + 1:] if x.get("k") == "visit"), None)
                                if nv is None or nv.get("field") != want:
                                    probs.append(f"landed None and the next visit row is "
                                                 f"{None if nv is None else nv.get('field')}, not {want}")
                            elif landed != want:
                                probs.append(f"landed {landed}, not {want}")
                            lost = d.get("lost")
                            key = door_sites8(pred, c["donor"], step["to"])[0]
                            if lost is None:
                                probs.append("no loss read")
                            elif lost.get("field") != fld:
                                probs.append(f"its loss read in {lost.get('field')}, not the walk's field {fld}")
                            elif SD.has_y(step.get("until")) and lost.get("y") is None:
                                probs.append(f"its loss at frame {lost.get('frame')} has no height")
                            else:
                                if step.get("until") and not SD.until_ok(step["until"], lost.get("x"), lost.get("z"),
                                                                         lost.get("y")):
                                    probs.append(f"its loss at ({lost.get('x')}, {lost.get('z')}) y {lost.get('y')} does "
                                                 f"not satisfy its until {step['until']}")
                                pts = (regs.get(key) or {}).get("points")
                                if pts is None:
                                    probs.append(f"no registered exit leads to its to {step['to']}")
                                elif lost.get("x") is None or (
                                        not doorface.region_contains(float(lost["x"]), float(lost["z"]), pts)
                                        and pathfind.poly_gap(float(lost["x"]), float(lost["z"]),
                                                              [(float(a), float(b)) for a, b in pts])
                                        > float(step["exit_slack"])):
                                    probs.append(f"its loss at ({lost.get('x')}, {lost.get('z')}) beyond exit_slack "
                                                 f"{step['exit_slack']} of {key}")
                        before = rows[:done[0]]
                        inter = [x for x in before if x.get("outcome") == "interrupted"]
                        failed = [x for x in before if x.get("outcome") == "failed"]
                        other = [x for x in before if x.get("outcome") not in ("interrupted", "failed")]
                        if len(inter) > int(step["interrupts"]):
                            probs.append(f"{len(inter)} interrupted row(s), over its {step['interrupts']}")
                        if any(x.get("door") for x in inter):
                            probs.append(f"an interrupted row in a door {[x.get('door') for x in inter if x.get('door')]}")
                        if len(failed) > int(step["attempts"]) - 1:
                            probs.append(f"{len(failed)} failed row(s), over its {int(step['attempts']) - 1}")
                        if any(x.get("door") or x.get("landed") is not None for x in failed):
                            probs.append("a failed row in a door or landed")
                        if other:
                            probs.append(f"step row(s) {[x.get('outcome') for x in other]} before the done one")
                    if probs:
                        bad.append(f"{lab} (a) {name}: " + "; ".join(probs))
            for w in visit_windows8(log, pred):
                if w["lo"] is None or w["hi"] is None:
                    continue

                def exempt(x, w=w) -> bool:
                    if place(x.fld, members) != w["donor"]:
                        return False
                    for dr in w["doors"]:
                        if (x.sid, x.tag, x.ip) in {tuple(s) for s in dr["sites"]} and dr["after"] is not None \
                                and x.f >= dr["after"]:
                            return True
                    kn = w["knight"]
                    return bool(kn and (x.sid, x.tag, x.ip) == kn["site"] and kn["lo"] is not None and kn["lo"] <= x.f
                                and (kn["hi"] is None or x.f < kn["hi"]))
                hit = next((x for x in r["rows"] if x.k == "w" and w["lo"] <= x.f <= w["hi"] and not exempt(x)), None)
                if hit is not None:
                    bad.append(f"{lab} (b): line {hit.line} {A._row_text(hit)} at frame {hit.f}, inside visit "
                               f"{w['visit']}'s window [{w['lo']}, {w['hi']}] ({w['donor']})")
            for c in pred.get("table") or ():
                if c["donor"] not in seeded:
                    continue
                rows = C7.cell_rows(log, c)
                if not rows:
                    continue
                probs = []
                if (rows[0].get("route") or {}).get("basis") != "prior":
                    probs.append(f"its first step row's route basis {(rows[0].get('route') or {}).get('basis')!r}, not "
                                 f"'prior' (seeded in this run)")
                checks = [x for x in rows if (x.get("route") or {}).get("basis_check")]
                if len(checks) != 1:
                    probs.append(f"{len(checks)} step rows carry basis_check, want exactly one")
                else:
                    ang = (checks[0]["route"]["basis_check"] or {}).get("angle")
                    if ang is None or float(ang) > agree:
                        probs.append(f"its first move {ang} deg off the prior, over acos(PRIOR_AGREE) {agree:.1f}")
                if probs:
                    bad.append(f"{lab} (c) ({c['donor']}, {c.get('visit')}): " + "; ".join(probs))
        nsteps = sum(len(c["steps"]) for c in pred.get("table") or ())
        return (not bad, self.title("WALK"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) the {nsteps} steps each done once with its evidence "
                                      f"(the walks' at_y and the knight's wait, the triggers' losses by height in their "
                                      f"doors), within its attempts, none in a door; (b) no row inside a visit's window "
                                      f"but its doors' sites and the knight's ip230 in THE EXEMPT SPAN; (c) every "
                                      f"seeded visit ({', '.join(map(str, sorted(seeded)))}) judged its first move "
                                      f"within {agree:.1f} deg")

    def order_check(self, covered: list, pred: dict) -> tuple:
        """O8-ORDER (5.3; decision 6; critique #1), every covered run's knight place (by place): (a) exactly one ``w``
        row at the seat watch's site (164 e1 t1 ip230 ``Bit[3811] := 1``), at the side's own field of the place; (b)
        its line before the place's chain row's (164 e2 t2 ip243); (c) its frame inside THE EXEMPT SPAN
        (:func:`exempt_span`)."""
        sw = pred.get("seat_watch") or {}
        site = list(sw.get("site") or [164, 1, 1, 230])
        d = site[0]
        key = next((k for k in pred.get("writes") or () if [k["donor"], k["sid"], k["tag"], k["ip"]] == site), None)
        ch = next((k for k in pred.get("chain") or () if k["donor"] == d), None)
        bad, spans = [], []
        for r in covered:
            lab = f"{r['side']}#{r['i']}"
            members = members_of(pred) if r["side"] == "F" else {}
            fld = _fld_of(members, d)
            k = [x for x in r["rows"] if x.k == "w" and place(x.fld, members) == d and (x.sid, x.tag, x.ip) == tuple(site[1:])]
            if len(k) != 1 or k[0].fld != fld or key is None or (k[0].target, k[0].new) != (key["target"], key["value"]):
                bad.append(f"{lab} (a): {len(k)} row(s) at {d} e{site[1]} t{site[2]} ip{site[3]}"
                           + (f" at fld {[x.fld for x in k]}, want one {key and key['target']} := "
                              f"{key and key['value']} at fld {fld}" if k else ""))
                continue
            x = k[0]
            c243 = None if ch is None else next((y for y in r["rows"] if y.k == "w" and place(y.fld, members) == d
                                                 and (y.sid, y.tag, y.ip) == (ch["sid"], ch["tag"], ch["ip"])), None)
            if c243 is None or not x.line < c243.line:
                bad.append(f"{lab} (b): ip{site[3]} at line {x.line}, the chain row ip{ch and ch['ip']} at line "
                           f"{None if c243 is None else c243.line}: not before it")
            lo, hi = exempt_span(r.get("log") or [], d)
            if lo is None or hi is None or not lo <= x.f < hi:
                bad.append(f"{lab} (c): ip{site[3]} at frame {x.f}, outside THE EXEMPT SPAN [{lo}, {hi})")
            spans.append(f"{lab} {x.f} in [{lo}, {hi})")
        return (not bad, self.title("ORDER"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) one ip{site[3]} row each, at the side's own field; (b) "
                                      f"before ip{ch and ch['ip']}; (c) inside THE EXEMPT SPAN ({'; '.join(spans[:6])})")

    def knight_check(self, covered: list, pred: dict) -> tuple:
        """O8-KNIGHT (5.3; decision 6; critique #9), every covered run's knight place: (a) its ``seat`` and ``start1``
        rows (COVER guarantees one of each: an unread one is A-KNIGHT), each the registered sid, each READ at the side's
        own field of the place (the reading's field, whatever poll wrote it); (b) each within ``tol`` of ``seat``."""
        sw = pred.get("seat_watch") or {}
        bad, seen = [], []
        sx, sz = (float(v) for v in sw.get("seat") or (0, 0))
        tol = float(sw.get("tol", 30))
        for r in covered:
            lab = f"{r['side']}#{r['i']}"
            members = members_of(pred) if r["side"] == "F" else {}
            fld = _fld_of(members, sw.get("donor"))
            kr = knight_rows(r.get("log") or [], pred)
            for what in ("seat", "start1"):
                x = kr[what]
                if x is None:
                    bad.append(f"{lab} (a): no {what} row")
                    continue
                if x.get("sid") != sw.get("sid") or x.get("field") != fld:
                    bad.append(f"{lab} (a): the {what} row read sid {x.get('sid')} at fld {x.get('field')}, want sid "
                               f"{sw.get('sid')} at {fld}")
                    continue
                dist = math.hypot(float(x["x"]) - sx, float(x["z"]) - sz)
                if dist > tol:
                    bad.append(f"{lab} (b): the {what} reading ({x['x']}, {x['z']}) {dist:.1f}u off the seat "
                               f"({sx:.0f}, {sz:.0f}), over tol {tol:.0f}")
                else:
                    seen.append(f"{lab} {what} {dist:.1f}u ({x.get('from')})")
        return (not bad, self.title("KNIGHT"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) a seat and a start1 reading each, in the place's own "
                                      f"field; (b) each within {tol:.0f}u of ({sx:.0f}, {sz:.0f}) ({'; '.join(seen[:4])})")

    def movie_check(self, covered: list, pred: dict) -> tuple:
        """O8-MOVIE (5.3; decision 7; critique #4), every covered run's movie span (:func:`movie_span`): (a) no
        ``press`` row and no ``choice`` row in the span -- by COVER no press and no skip-shaped choice can (re-checked
        here); a choice of any OTHER shape FAILS: a script's choice where stock has none, answered by the net's
        default, a finding the net must never hide; (b) the span's length at the fps measured INSIDE it (its clock
        rows with a write time) at least ``file_s`` - ``slack_s`` -- the check a covered run can fail; (c) no
        ``skip_seen`` row in the span."""
        mv = pred.get("movie") or {}
        floor = float(mv.get("file_s", 0)) - float(mv.get("slack_s", 0))
        bad, seen = [], []
        for r in covered:
            lab = f"{r['side']}#{r['i']}"
            members = members_of(pred) if r["side"] == "F" else {}
            span = movie_span(r, pred, members)
            if span["f502"] is None or span["f863"] is None:
                bad.append(f"{lab} (b): no span -- the ip502 row {span['f502']}, the ip863 row {span['f863']}")
                continue
            for p in span["presses"]:
                bad.append(f"{lab} (a): a press at frame {(p.get('pre') or {}).get('frame')} in the span ({p.get('why')})")
            for ch in span["choices"]:
                bad.append(f"{lab} (a): a choice row at frame {ch.get('frame')} in the span -- "
                           + ("the skip dialog's (COVER's)" if _skip_like(ch) else
                              f"of another shape ({len(ch.get('options') or []) - 1} lines, cursor "
                              f"{ch.get('selected')}): a script's choice where stock has none, answered by rule "
                              f"{ch.get('rule')}"))
            if span["fps"] is None:
                bad.append(f"{lab} (b): unclocked ({len(span['timed'])} clock rows with a write time)")
            elif span["s"] < floor:
                bad.append(f"{lab} (b): the span {span['f863'] - span['f502']} frames at {span['fps']} fps = "
                           f"{span['s']} s, under file_s - slack_s {floor:.1f}")
            for x in span["skips"]:
                bad.append(f"{lab} (c): a skip dialog seen at frame {x.get('frame')} in the span")
            if span["fps"] is not None:
                seen.append(f"{lab} {span['f863'] - span['f502']} frames at {span['fps']} fps = {span['s']} s")
        return (not bad, self.title("MOVIE"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) no press, no choice; (b) each span at least "
                                      f"{floor:.1f} s at its own rate ({'; '.join(seen[:6])}); (c) no skip dialog")

    # -- the report ---------------------------------------------------------------------------------------------
    def scope_start8(self, pred: dict) -> str:
        """5.4's start-dependence line, RENDERED from the predictions (``start_scoped``, ``start_reads``,
        ``carried``, :data:`AFTER_RUN`), never a literal."""
        parts = []
        for x in pred.get("start_scoped") or ():
            d, sid, tag, ip = x["site"]
            a = x.get("after") or {}
            parts.append(f"{d} {'' if (sid, tag) == (0, 0) else f'e{sid} t{tag} '}ip{ip} {x['target'].split('.', 1)[1]} "
                         f"{x['here'][0]} -> {x['here'][1]} here, {a.get('old')} -> {a.get('value')} after")
        car = pred.get("carried") or {}
        vals = car.get("values") or {}
        carried = ", ".join(f"{t.split('.', 1)[1]} {v[0]} ({v[1]} after)" for t, v in vals.items())
        party = car.get("party") or {}
        reads = "; ".join(f"{x['site'][0]} ip{x['site'][3]} read {x['target'].split('.', 1)[1]} {x['old']}"
                          for x in pred.get("start_reads") or ())
        edges = " / ".join(f"a warp {x.get('edge')} 70's ip{(x.get('race') or [0, 0, 0, '?'])[3]}"
                           for x in pred.get("start_reads") or ())
        return (f"none in value or path: a raw warp into {pred['start']['S']}@{pred['entrance']} at SC "
                f"{pred['scenario']} from New Game, the same on both sides. START-SCOPED olds only: " + "; ".join(parts)
                + f" (after the {self.AFTER_RUN} routes as driven). Carried, not claimed (neither written nor read by a "
                  f"function the route runs; derived from the frozen {self.AFTER_RUN} keys): {carried}, party "
                  f"{party.get('values', ['?'])[0]} ({', '.join(party.get('values') or [])}). THE START READS: {reads} "
                  f"in every covered run ({edges} is A-START, the run uncovered and named)")

    def report_extra(self, run_dir: Path, session: dict, pred: dict, runs: list, checks: list) -> list:
        """Report-only (research/o8_design.md 5.4): the scope (start dependence, the end and the seam, the walks, the
        movie, settings and engine, the language), the walks per run per step, THE KNIGHT per run, THE PINCH per run
        (164 #1's attempts and route records), 166 per run (the pages, the movie span), the seam per F run, the pattern
        per run, the end state (live and the raced pair's trace values), the render rate, the session's end and O2's
        sections."""
        trace = pred.get("end_state_trace") or {}
        mv, sm8 = pred.get("movie") or {}, seam_spec(pred)
        members_all = members_of(pred)
        L = ["", "Scope (a US session):", "  start dependence -- " + self.scope_start8(pred),
             f"  the end and the seam -- the arrival in REAL {pred['end_field']} on both sides; on F one seam, "
             f"member({sm8.get('donor')}) {_fld_of(members_all, sm8.get('donor'))} -> {sm8.get('to')}, its exit "
             f"{sm8.get('donor')} e{(sm8.get('exit') or [0, 0])[1]} t{(sm8.get('exit') or [0, 0, 0])[2]} "
             f"ip{(sm8.get('exit') or [0, 0, 0, 0])[3]} (O8-SEAM); the end state read live but "
             + " and ".join(t.split(".", 1)[1] for t in trace) + f", which {pred['end_field']}'s prologue rewrites at "
             "once: taken from the trace's last pre-cut writes, "
             + ", ".join(f"{s['site']['place']} e{s['site']['sid']} t{s['site']['tag']} ip{s['site']['ip']} "
                         f"({s['value']})" for s in trace.values())]
        clears = [(c["donor"], n, s.get("clearance")) for c in pred.get("table") or () for n, s in enumerate(c["steps"])]
        L.append("  the walks -- " + ", ".join(f"{d} #{n} at {cl}" for d, n, cl in clears)
                 + f" (the engine radii {ENGINE_RADII}; 164 #1 at 64: no route at 80, THE PINCH); every step's arrival "
                   f"proven by its height (at_y, until y); the first moves on the exact prior basis in "
                 + ", ".join(map(str, C7.seeded_places(pred))) + f", seeded afresh every run, each checked within "
                   f"{C7.prior_agree_deg():.1f} deg")
        L.append(f"  the movie -- {mv.get('name')} played out: no press, no choice, no skip dialog after "
                 f"{mv.get('donor')}'s ip{(mv.get('from') or [0, 0, 0, 0])[3]} through its "
                 f"ip{(mv.get('to') or [0, 0, 0, 0])[3]} in any covered run (a run with one is uncovered, A-MOVIE: the "
                 f"dialog is press-only); each run's span and rate below")
        st = (session.get("install") or {}).get("settings")
        eng = [d for _ok, _w, d in self._recorded(session, "P-ENGINE")]
        L.append("  settings and engine -- " + (json.dumps(st, sort_keys=True) if st is not None else "not recorded")
                 + "; derived -- " + "; ".join(f"{k} {v.get('value')} ({v.get('why')})"
                                               for k, v in (pred.get("derived") or {}).items())
                 + "; engine -- " + (eng[-1] if eng else json.dumps((session.get("install") or {}).get("engine"))))
        L.append("  language -- " + self.scope_lang(session))
        L.append("")
        L.append("The walks, per run, per step (outcome, the grant sample, basis and basis_check, clearance, the route "
                 "record, at_y, the loss with its height, the landing and flip):")
        for r in runs:
            L += self._walk_lines8(r)
        L.append("")
        L.append("THE KNIGHT, per run (step 0's frames, ip230's frame and line, THE EXEMPT SPAN, the wait, the seat "
                 "readings):")
        for r in runs:
            L += self._knight_lines(r, pred)
        L.append("")
        L.append("THE PINCH, per run (164 #1's attempts and their route records; F5's classification is the "
                 "rehearsal's):")
        for r in runs:
            L += self._pinch_lines(r)
        L.append("")
        L.append("166, per run (the pages pressed; FMV004's span: its rows' frames, the clock rows, the rate, the "
                 "seconds; any press, choice or skip dialog in it):")
        for r in runs:
            L += self._movie_lines(r, pred)
        L.append("")
        L.append("The seam, per F run (the Seam, its exit row, the cut row):")
        for r in runs:
            if r["side"] != "F":
                continue
            d = r.get("digest")
            seams = list(getattr(d, "seams", None) or ())
            cr = r.get("cut_row")
            L.append(f"  F#{r['i']}: " + ("no seam" if not seams else "; ".join(
                f"{s.frm} -> {s.to} {list(s.fields)} at frame {s.frame}, exit "
                + ("none" if s.exit is None else A._row_text(s.exit)) for s in seams))
                     + f"; cut row " + ("none" if cr is None else f"{cr.k} fld {cr.fld} don {cr.don} f{cr.f}"))
        L.append("")
        L.append("The pattern, per run (emitted rows per visit, the c rows; O8-PATTERN's first difference):")
        stock = self._stock_src()
        for r in runs:
            L += self._pattern_lines(r, pred, stock)
        L.append("")
        L.append("The end state, per run (live; and each raced target's last pre-cut row from the trace):")
        for r in runs:
            members = members_of(pred) if r["side"] == "F" else {}
            live = (r.get("outcome") or {}).get("end_state")
            parts = []
            for t in trace:
                hits = [x for x in r.get("rows") or () if x.k in ("w", "r") and C6._row_span(x) & C6._span(t)]
                x = hits[-1] if hits else None
                parts.append(f"{t} " + ("none" if x is None else f"{x.new} at {place(x.fld, members)} e{x.sid} t{x.tag} "
                                                                  f"ip{x.ip} (fld {x.fld})"))
            rate = next((x for x in reversed(r.get("log") or []) if x.get("k") == "rate"), None)
            L.append(f"  {r['side']}#{r['i']}: live {json.dumps(live, sort_keys=True) if live is not None else 'not read'};"
                     f" trace {'; '.join(parts) or 'none'} (its live read raced: never compared); render rate "
                     f"{None if rate is None else rate.get('fps')} fps")
        L.append("")
        for r in runs:
            if r.get("start_withdrawn"):
                L.append(f"A-START withdrawn: {r['side']}#{r['i']}: {r['start_withdrawn']}")
        ended = session.get("ended")
        if ended is None:
            L.append("The session's end: not recorded")
        else:
            L.append("The session's end (end_run, warp first): "
                     + ("the title came back" if ended.get("ok") else f"the title did NOT come back: {ended.get('why')}")
                     + f"; rows {[x.get('k') for x in ended.get('log') or ()]}")
        if session.get("stopped"):
            L.append(f"The session STOPPED (S15): {session['stopped']}")
        L += self._o2_sections(session, runs)
        if session.get("rerun_held"):
            L += ["", f"Re-runs held (rerun.stop_on): {session['rerun_held']}"]
        return L

    @staticmethod
    def _walk_lines8(r: dict) -> list:
        lab = f"  {r['side']}#{r['i']}:"
        rows = [x for x in r.get("log") or () if x.get("k") == "step"]
        if not rows:
            v = (r.get("rec") or {}).get("v")
            return [f"{lab} no step row" + (f" (the run VOID {v})" if v else "")]
        out = []
        for s in rows:
            fr, lost, rt = s.get("from") or {}, s.get("lost") or {}, s.get("route") or {}
            bc = rt.get("basis_check") or {}
            fps = rt.get("fps")
            out.append(f"{lab} ({s.get('donor')}, visit {s.get('visit')}) #{s.get('n')} {s.get('kind')} attempt "
                       f"{s.get('attempt')} {s.get('outcome')}: from frame {fr.get('frame')} ({fr.get('x')}, "
                       f"{fr.get('z')}); basis {rt.get('basis') or 'calibrated'}"
                       + (f", basis_check {bc.get('angle')} deg moved {bc.get('moved')}" if bc else "")
                       + f"; clearance {s.get('clearance')}" + (f" unstick {s.get('unstick')}" if "unstick" in s else "")
                       + f"; legs {rt.get('route')} replans {rt.get('replans')} waits {rt.get('waits')} pushes "
                         f"{rt.get('pushes')} blockers {rt.get('blockers')} frozen {rt.get('frozen')} boxed "
                         f"{rt.get('boxed')}" + (f"; at_y {s.get('at_y')}" if s.get("at_y") else "")
                       + f"; loss frame {lost.get('frame')} in {lost.get('field')} ({lost.get('x')}, {lost.get('z')}) "
                         f"y {lost.get('y')}; landed {s.get('landed')} flip {s.get('flip_frame')}; fps "
                       + f"{fps.get('fps') if isinstance(fps, dict) else fps}"
                       + (f"; door {s.get('door')}" if s.get("door") else "")
                       + (f" -- {s.get('why')}" if s.get("why") else ""))
        return out

    @staticmethod
    def _knight_lines(r: dict, pred: dict) -> list:
        lab = f"  {r['side']}#{r['i']}:"
        sw = pred.get("seat_watch") or {}
        members = members_of(pred) if r["side"] == "F" else {}
        log = r.get("log") or []
        s0 = [x for x in log if x.get("k") == "step" and x.get("donor") == sw.get("donor") and x.get("n") == 0]
        if not s0:
            return [f"{lab} no step-0 row in {sw.get('donor')}"]
        lo, hi = exempt_span(log, sw.get("donor"))
        site = tuple((sw.get("site") or [0, 0, 0, 0])[1:])
        k = next((x for x in r.get("rows") or () if x.k == "w" and place(x.fld, members) == sw.get("donor")
                  and (x.sid, x.tag, x.ip) == site), None)
        wf = (s0[-1].get("wait_flag") or {})
        kr = knight_rows(log, pred)
        return [f"{lab} step 0's rows (attempt, frame0, frame) {[(x.get('attempt'), x.get('frame0'), x.get('frame')) for x in s0]};"
                f" ip230 " + ("none" if k is None else f"frame {k.f} line {k.line}") + f"; THE EXEMPT SPAN [{lo}, {hi});"
                f" the wait frame0 {wf.get('frame0')} read {wf.get('read')} at {wf.get('frame')}, {wf.get('s')} s "
                f"(game {wf.get('game_s')} s), published {wf.get('published')}, last {wf.get('last')}; seat "
                f"{kr['seat'] and (kr['seat']['x'], kr['seat']['z'], kr['seat']['frame'], kr['seat']['from'])}; start1 "
                f"{kr['start1'] and (kr['start1']['x'], kr['start1']['z'], kr['start1']['frame'])}"
                + (f"; observe errors {[(x.get('hook'), x.get('error')) for x in kr['errors']]}" if kr["errors"] else "")]

    @staticmethod
    def _pinch_lines(r: dict) -> list:
        lab = f"  {r['side']}#{r['i']}:"
        rows = [x for x in r.get("log") or () if x.get("k") == "step" and x.get("donor") == 164 and x.get("n") == 1]
        if not rows:
            return [f"{lab} 164 #1 never ran"]
        return [f"{lab} 164 #1 attempt {x.get('attempt')} {x.get('outcome')}: waits {(x.get('route') or {}).get('waits')} "
                f"pushes {(x.get('route') or {}).get('pushes')} blockers {(x.get('route') or {}).get('blockers')} frozen "
                f"{(x.get('route') or {}).get('frozen')} boxed {(x.get('route') or {}).get('boxed')}"
                + (f" -- {x.get('why')}" if x.get("why") else "") for x in rows]

    @staticmethod
    def _movie_lines(r: dict, pred: dict) -> list:
        lab = f"  {r['side']}#{r['i']}:"
        members = members_of(pred) if r["side"] == "F" else {}
        mv = pred.get("movie") or {}
        presses = [x for x in r.get("log") or () if x.get("k") == "press" and x.get("donor") == mv.get("donor")]
        span = movie_span(r, pred, members)
        return [f"{lab} pages pressed {[(x.get('texts') or [''])[0][:16] for x in presses]} (frames "
                f"{[(x.get('pre') or {}).get('frame') for x in presses]}); span ({span['f502']}, {span['f863']}] -- "
                f"{len(span['clocks'])} clock rows ({span['skipped']} without a write time), fps {span['fps']}, "
                f"{span['s']} s; presses {len(span['presses'])}, choices {len(span['choices'])}, skip dialogs "
                f"{len(span['skips'])}"
                + "".join(f"; A-MOVIE: {w}" for w in movie_reasons(span))]

    # -- the CLI ------------------------------------------------------------------------------------------------
    def add_arguments(self, ap) -> None:
        ap.add_argument("--draft", action="store_true", help="print the draft predictions as JSON")
        ap.add_argument("--rehearsal-report", metavar="RUN_DIR",
                        help="print an o8_rehearse.py launch's record, stage by stage and run by run")

    def handle(self, args) -> int | None:
        """``--rehearsal-report`` (printed through segment_trace.say: it quotes the game's pages); ``--offline-check``
        (which predictions, then the chain's route members and the end, then each check through segment_trace.say);
        then O2's (``--draft``, ``--preflight``)."""
        if args.rehearsal_report:
            ST.say(rehearsal_report8(args.rehearsal_report))
            return 0
        if args.offline_check:
            pred, what = self.current(args.predictions)
            print(f"predictions: {what}")
            members = members_of(pred)
            if all(d in members.values() for d in ROUTE_DONORS):
                print(f"chain: {route_members_line(members)}; the end REAL {pred.get('end_field')} on both sides")
            checks = self.offline_check(pred)
            for ok, w, detail in checks:
                ST.say(f"{'PASS' if ok else 'FAIL'}  {w}\n      {detail}")
                for d in A.defect_lines(detail):
                    print(d)
            return 0 if all(ok for ok, _w, _d in checks) else 1
        return A.O2Segment.handle(self, args)


O8 = O8Segment()


# ======================================================================== the rehearsal report
def _pinch_lines8(pn: dict, floor) -> list:
    """THE PINCH of one run (7.2, F5): its holds in THE PINCH WINDOW with the narrowest wall gap each passed -- measured
    here on ``floor(place)``, level-aware (o7_castle_walk.foot_gap) --, every stall there CLASSIFIED (rejected,
    blocker-sealed, slid), every rung after a hold elsewhere (recorded, never judged) and F5's verdict."""
    if not pn:
        return []
    feet = list(pn.get("pinch_holds") or ())
    mesh = floor(pn.get("place")) if feet else None
    gaps = [None if mesh is None else C7.foot_gap(h.get("samples"), mesh) for h in feet]
    measured = [x for x in gaps if x is not None]
    narrowest = (min(measured) if measured else "none (no pinch hold)" if not feet else
                 "unmeasured (no stock mesh here)" if mesh is None else "unmeasured (no sample on a level)")
    win = pn.get("window") or {}
    L = [f"    THE PINCH in {pn.get('place')}: {len(pn.get('holds') or [])} hold(s), {len(feet)} in THE PINCH WINDOW (x "
         f"{win.get('x')}, z {win.get('z')}, y {win.get('y')}); the narrowest wall gap a pinch hold passed {narrowest} "
         f"(the stock mesh, level-aware: rehearsed.narrowest_pinch's evidence); F5 {pn.get('f5')}"]
    for h, gap in zip(feet, gaps):
        L.append(f"      pinch hold frame {h.get('frame')}: {h.get('from')} -> {h.get('to')} pressed {h.get('pressed')} "
                 f"travelled {h.get('moved')} slide {h.get('slide')} stall {h.get('stall')}; narrowest gap {gap}")
    for s in pn.get("stalls") or ():
        L.append(f"      stall at frame {s.get('frame')} ({s.get('x')}, {s.get('z')}): {s.get('class')} -- {s.get('why')}")
    for x in pn.get("elsewhere") or ():
        L.append(f"      a rung elsewhere at frame {x.get('frame')} ({x.get('x')}, {x.get('z')}): {x.get('rungs')} "
                 f"({x.get('outcome')}) -- recorded, never judged")
    return L


def _knight_record_lines(kn: dict) -> list:
    """THE KNIGHT of one run (7.2, F2): T0, ip230's frame, the wait, the seat readings, his polls."""
    if not kn:
        return []
    w = kn.get("wait") or {}
    polls = kn.get("polls") or []
    t0 = kn.get("t0")
    if isinstance(t0, dict) and t0.get("evicted"):       # the review's #1: the ring lost the crossing -- never a late T0
        t0 = (f"UNMEASURED (the ring evicted the samples read after frame {t0.get('after')}: it held from frame "
              f"{t0.get('held_from')}, his first sample past the release there {t0.get('first')})")
    return [f"    THE KNIGHT: T0 {t0}; ip230 {kn.get('ip230')}; THE EXEMPT SPAN {kn.get('span')}; the wait "
            f"frame0 {w.get('frame0')} read {w.get('read')} at {w.get('frame')}, {w.get('s')} s (game {w.get('game_s')} "
            f"s), published {w.get('published')}, last {w.get('last')}",
            f"      seat {kn.get('seat')}; start1 {kn.get('start1')}; {len(polls)} poll reading(s), distinct positions "
            f"{sorted({tuple(p[1:]) for p in polls})[:4]}"
            + (f"; observe errors {kn.get('errors')}" if kn.get("errors") else "")]


def _movie_record_lines(mv: dict) -> list:
    """FMV004 of one run (7.2, F3): the 313 press, the span at its clocked rate, the dialogs, the poke, the late edge."""
    if not mv:
        return []
    sp = mv.get("span") or {}
    L = [f"    the movie: 313 pressed at {mv.get('p313')}; span ({sp.get('f502')}, {sp.get('f863')}] -- "
         f"{sp.get('clocks')} clock row(s) ({sp.get('skipped')} without a write time), fps {sp.get('fps')}, "
         f"{sp.get('s')} s; ui during it {mv.get('ui')}; presses {mv.get('presses')}, choices {mv.get('choices')}, "
         f"skip dialogs {mv.get('skips')}; 166's Byte[13] old {mv.get('byte13_old')}"
         + (" -- a LATE-EDGE V5 (re-run, never counted against F3)" if mv.get("late_v5") else "")]
    pk = mv.get("poke")
    if pk:
        L.append(f"      the poke: pressed at frame {pk.get('frame')} ({pk.get('after_s')} s after the ip502 row's poll); "
                 f"the dialog {pk.get('dialog')}; the net's choice rows {pk.get('choices')}; resumed at "
                 f"{pk.get('resumed')}; second dialog {pk.get('second')}")
    return L


def _stop_lines8(rec: dict) -> list:
    """A run's stop (7.1 R-VOID, F9): where it fired and what was sent around it."""
    L = []
    for key in ("flag_stop", "pinch_stop", "movie_stop"):
        st = rec.get(key, ...)
        if st is ...:
            continue
        L.append(f"    {key}: never fired" if st is None else
                 f"    {key}: frame {st.get('frame')} in {st.get('field')} at ({st.get('x')}, {st.get('z')}) y "
                 f"{st.get('y')} -- {st.get('why')}; after it {st.get('holds_after')} hold(s) and "
                 f"{st.get('presses_after')} press(es) (there must be none); the sends after it "
                 f"{st.get('sends_after')}" + (f"; the ip502 row's frame {st.get('f502')}" if key == "movie_stop" else ""))
    return L


def _warp_text8(stage: dict) -> str:
    """A stage's warp as the report heads it: one, or -- a stage with ``each`` -- each run's with its stop, a run's own
    warp and end where its entry lays them (R-VOID's), else the stage's (R-FMV's entries lay only the poke)."""
    each = stage.get("each")
    if not each:
        return f"warp {stage.get('field')} {stage.get('entrance')} {stage.get('sc')} -> {stage.get('end')}"
    return "; ".join(f"run {k}: warp {e.get('field', stage.get('field'))} {e.get('entrance', stage.get('entrance'))} "
                     f"{stage.get('sc')} -> {e.get('end', stage.get('end'))}"
                     + "".join(f", {key} {e[key]}" for key in sorted(REHEARSAL_OVERLAYS8) if e.get(key))
                     for k, e in enumerate(each, 1))


def rehearsal_report8(run_dir, *, walkmesh=None) -> str:
    """``--rehearsal-report``: an o8_rehearse.py launch's ``o8_rehearsal.json`` (research/o8_design.md 7.2), stage by
    stage and run by run -- what each freeze item (7.3) is read from: the capabilities and the launch's readings (F10);
    per run its warp, outcome and render rate (F14), the grants with their published y (F1), THE LEVELS, the bases and
    every ``basis_check`` (F2, F4), the step rows and THE WALKS' holds, THE KNIGHT (F2), THE PINCH -- the narrowest wall
    gap a pinch hold passed MEASURED HERE on the stock mesh, level-aware -- with every stall classified and F5's verdict,
    the dead-level crossings, the movie (F3), the crossing into 55, the evidence (F11), the trace summary (F6, F7), the
    stops (F9) and an untraced run's exceptions (F13); F-SMOKE's warps and twins (F12). ``walkmesh`` (a place -> its
    walkmesh; default the install's stock player walkmesh, read-only) is a seam for the fake."""
    run_dir = Path(run_dir)
    floor = walkmesh or C7._stock_floor
    doc = json.loads((run_dir / REHEARSAL_FILE).read_text(encoding="utf-8"))
    L = [f"O8 rehearsals -- {run_dir.name}  (draft sha {str(doc.get('draft_sha256'))[:8]}; stages "
         f"{doc.get('stages_run')}; THE PINCH WINDOW {doc.get('pinch')})"]
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
            L += C5._smoke_lines(name, stage, recs, (doc.get("twins") or {}).get(name))
            L.append("")
            continue
        L.append(f"== {name}: {_warp_text8(stage)}" + (" UNTRACED" if stage.get("untraced") else "")
                 + f"  ({len(recs)} run(s)) -- settles: {stage.get('settles')}")
        for rec in recs:
            out = rec.get("outcome") or {}
            rate = rec.get("rate") or {}
            w = rec.get("warp") or {}
            L.append(f"  run {rec.get('n')} ({rec.get('side', 'S')}): warp {w.get('field')} {w.get('entrance')} "
                     f"{w.get('sc')}: {out.get('end')} -- {out.get('why')}"
                     + (f" [{out.get('v')} {out.get('cell')} {out.get('by')}]" if out.get("v") else "")
                     + (" (RE-RUN: a late-edge V5)" if rec.get("rerun_of") else "")
                     + ("" if rec.get("counted", True) else " -- SET ASIDE: a late-edge V5, re-run, never counted")
                     + f"; beats {rec.get('beats')}; {rec.get('t1', 0) - rec.get('t0', 0):.0f}s; render rate "
                     f"{rate.get('fps')} fps ({rate.get('tick_hz')} Hz ticks, {rate.get('source')}); trace "
                     f"{rec.get('trace_file')}")
            L += C7._grants_lines(rec)
            lv = rec.get("levels") or {}
            if lv:
                L.append(f"    levels: grants y {[g[2] for g in lv.get('grants') or ()]}; losses y "
                         f"{[x[2] for x in lv.get('losses') or ()]}; walk holds y0 -> y1 "
                         f"{[(h[2], h[3]) for h in lv.get('walk_holds') or ()][:12]}")
            for b in rec.get("bases") or ():
                L.append(f"    basis {b.get('field')} ({b.get('donor')}, visit {b.get('visit')}) #{b.get('n')} attempt "
                         f"{b.get('attempt')}: {b.get('basis')}"
                         + (f", basis_check {b.get('check')}" if b.get("check") else "")
                         + (f", prior_basis {b.get('prior_basis')}" if b.get("prior_basis") else ""))
            if rec.get("calibration"):
                L.append(f"    calibration (each walked field's basis at the drive's end): {rec.get('calibration')}")
            for s in rec.get("steps") or ():
                L.append(f"    step ({s.get('donor')}, visit {s.get('visit')}) #{s.get('n')} {s.get('kind')} attempt "
                         f"{s.get('attempt')} {s.get('outcome')}: to {s.get('to')}, at_y {s.get('at_y')}, wait "
                         f"{s.get('wait_flag')}, loss {s.get('lost')}, landed {s.get('landed')}, flip "
                         f"{s.get('flip_frame')}, clearance {s.get('clearance')}"
                         + (f", unstick {s.get('unstick')}" if "unstick" in s else "")
                         + f", route fps {((s.get('route') or {}).get('fps') or {}).get('fps')}"
                         + (f", door {s.get('door')}" if s.get("door") else "")
                         + (f" -- {s.get('why')}" if s.get("why") else ""))
            for w in rec.get("walks") or ():
                hs = w.get("holds") or []
                L.append(f"    walk ({w.get('donor')}, visit {w.get('visit')}) #{w.get('n')} attempt {w.get('attempt')} "
                         f"{w.get('outcome')}: {len(hs)} hold(s), {sum(1 for h in hs if h.get('slide'))} slide(s), "
                         f"{sum(1 for h in hs if h.get('stall'))} stall(s), {len(w.get('waypoints') or [])} "
                         f"waypoint(s); the first hold {hs[0].get('from') if hs else None} -> "
                         f"{hs[0].get('to') if hs else None}")
            for x in rec.get("ladder") or ():
                L.append(f"    ladder at frame {x.get('frame')} in {x.get('field')} ({x.get('x')}, {x.get('z')}): rungs "
                         f"{x.get('rungs')} ({x.get('outcome')}) after the hold from {x.get('after_hold')}; step "
                         f"{x.get('step')}" + (" -- IN THE PINCH WINDOW" if x.get("pinch") else ""))
            L += _knight_record_lines(rec.get("knight") or {})
            L += _pinch_lines8(rec.get("pinch") or {}, floor)
            for d in rec.get("dead_level") or ():
                L.append(f"    dead-level crossing: {d.get('key')} entered at frame {d.get('frame')} in {d.get('field')} "
                         f"({d.get('x')}, {d.get('z')}) y {d.get('y')} -- its gate {d.get('gate')} fails there: no loss")
            L += _movie_record_lines(rec.get("movie") or {})
            cx = rec.get("crossing") or {}
            if cx:
                L.append(f"    the crossing: 166 ip863 at frame {cx.get('ip863')}, 55 ip22 at {cx.get('ip22')}; rows "
                         f"between {cx.get('between')}")
            ev = rec.get("evidence") or {}
            L.append(f"    evidence: {len(ev.get('press') or [])} press row(s), {len(ev.get('forbidden') or [])} "
                     f"forbidden row(s), {len(ev.get('observed') or [])} observed row(s), {len(ev.get('input') or [])} "
                     f"input row(s)")
            npg = rec.get("no_progress") or {}
            L.append(f"    longest no-progress stretch: {npg.get('longest_s')}s at {npg.get('where')}")
            L += _stop_lines8(rec)
            if not rec.get("traced", True):
                L.append(f"    untraced: exceptions since the warp {rec.get('exceptions')}; Memoria.log lines "
                         f"{len(rec.get('log_lines') or [])}")
            end = rec.get("end") or {}
            er = end.get("end_run") or {}
            L.append(f"    end: state {end.get('end_state')}; end_run " + ("ok" if er.get("ok") else f"FAILED {er.get('why')}")
                     + f", title {er.get('title')}, rows {[x.get('k') for x in er.get('how') or ()]}"
                     + (f", {er.get('s')} s" if er.get("s") is not None else ""))
            L += _trace_report8(rec.get("trace") or {})
        aside = [r for r in recs if r.get("counted") is False]
        if aside:
            L.append(f"  counted (F3 and every freeze item): {len(recs) - len(aside)} run record(s) -- runs "
                     f"{[r.get('n') for r in recs if r.get('counted', True)]}; set aside (a late-edge V5, re-run): runs "
                     f"{[r.get('n') for r in aside]}")
        L.append("")
    return "\n".join(L)


# ======================================================================== the session and the CLI
def run(g) -> None:
    """The session (tools/play.py's entry): O8Segment.run."""
    return O8.run(g)


def main(argv=None) -> int:
    return O8.main(argv)


if __name__ == "__main__":
    sys.exit(main())
