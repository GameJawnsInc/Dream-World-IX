"""THE STORY-WRITE TRACE, O6 -- STEINER'S NAMING, THE KNIGHTS OF PLUTO AND HIS FIRST DOOR, A US SESSION: from a raw warp
into 151 (the royal seat box, entrance 110, the scenario at 1190; EVT_ALEX1_AC_SEAT_R) through Brahne's scene and
STEINER'S NAMING (Menu(1, 3): the default "Steiner" accepted, never typed; Byte[6] |= 8), Field(153) at 328 (the Knights
of Pluto; EVT_ALEX1_AC_H2F) -- the shared script's Byte[8] row, the party rebuild, UInt16[19] |= 8 -- to Steiner's first
control, ONE walk north to the e23 door, and the arrival in 154 at 315 (EVT_ALEX1_AC_ENT_2F) -- stock against the alxc
disc-1 chain O4 deployed, both sides played by one driver (studies/story-trace/PLAN.md, "O6"; the design:
research/o6_design.md).

    py tools/play.py studies/story-trace/o6_steiner.py --label story-o6 --timeout 240
    py studies/story-trace/o6_steiner.py --offline-check     # O4's build and its route pins per language, the keys
                                                             # (the start-dependent ones' after values computed), the
                                                             # route pins and route_mes, block 3's text (strict), the
                                                             # store census (e15 LIVE at 328), the regions, the door's
                                                             # goals and the evidence's soundness
    py studies/story-trace/o6_steiner.py --preflight         # the live install (read-only): all green, O4 deployed it
    py studies/story-trace/o6_steiner.py --draft             # the draft predictions, as JSON
    py studies/story-trace/o6_steiner.py --freeze            # write o6_predictions_v1.json (once: the lead, after the
                                                             # stock rehearsals)
    py studies/story-trace/o6_steiner.py --analyse <run dir> # the analysis alone, on saved traces
    py studies/story-trace/o6_steiner.py --rehearsal-report <run dir>   # an o6_rehearse.py launch, stage by stage

THE SIDES (o6_forks.json: O4's chain, reused -- nothing imported, built or deployed for O6):
  S  stock. Start: 151, entrance 110, SC 1190. End: the arrival in REAL 154.
  F  O4's twenty members 31240-31259 as deployed: member(151) 31244, member(153) 31245 and the end in member(154) 31246
     -- read from O4's campaign.toml, never assumed. Every route Field() is retargeted, so the chain is closed (no seam),
     and a landing in a REAL donor field on F is V19, a finding.

THE ENTRY: New Game, the trace armed, then in field 70 a raw `warp <151 | 31244> 110 1190`: THREE residue rows in field
70 (SC's two bytes and FieldEntrance's low byte: 110 is 0x006E), which the front cut sets aside and O6-START requires.

THE ROUTE: segment_drive.drive with the naming registration (151 at SC 1190: rule 4 + accept_name, the page witness
S16 judging the first parsed [STNR] page), ONE visit-scoped cell (153, 1190, visit 2: the north door, a trigger step
whose evidence is z > 1200 and whose landing is 154: S14's ``to``), the run-wide input witness, the stop page; no battle,
no movie, no choice. Control anywhere else -- 151 at any point, 153 before the grant -- is V4 (game) at its [place, sc,
visit] cell.

THE ANALYSIS: each run cut at its start row (151's first write) and at its first row in an end PLACE (154: member(154)
on F), digested and compared as O1-O5's; the O6 checks (research/o6_design.md 5.3) read the start, no SC rung, the
chain, the residue, the writes EXACTLY, the landing per side, THE NAMING (one named row before ip610's store, one
name_on_page row rendering the default), the walk (THE PAIRED-WALK LAW, S14's landing), the sink's emitted row pattern
EXACTLY with the shared script's e15 row FLOATING inside the bytes' window, THE START-DEPENDENT keys (each deviation
classified per run: FINDING / EXPLAINED / START DRIFT), the masked regions, the state handed to 154, and every run's
VOID classes by [place, sc, visit]. The predictions are frozen by the lead after the stock rehearsals (o6_rehearse.py);
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
import o5_hallway as C5                                                 # noqa: E402
import segment_drive as SD                                              # noqa: E402
import segment_trace as ST                                              # noqa: E402
from segment_trace import (SIDES, cut_at_end, cut_at_start, is_noise, key_of, members_of, place,  # noqa: E402
                           row_keys, wkey)

PREDICTIONS = HERE / "o6_predictions_v1.json"
MANIFEST = HERE / "o6_forks.json"
SESSION_FILE = "o6_session.json"
REPORT_FILE = "o6_report.txt"
REHEARSAL_FILE = "o6_rehearsal.json"
#: O4's chain and build, reused (research/o6_design.md 0.1 #2, 6.4): nothing is imported, built or deployed for O6.
CHAIN_DIR = C4.CHAIN_DIR
BUILD_DIR = C4.BUILD_DIR
GAME = A.GAME
SESSION_LANG = "us"
#: The text block the route's members carry (EVENT_ID_TO_MES): block 3 for 150-167. O6 reads no other.
TEXT_BLOCK, TEXT_BLOCKS = 3, (3,)
#: The route's places, the order it visits them in, and the end place.
ROUTE = (151, 153)
VISITS = (151, 153)
END_FIELD = 154
#: The donors P-DONOR and P-DONOR-LOG read, and the route members derived from the chain: the route's and the end's --
#: O5's set, in O6's order (research/o6_design.md 1.3).
ROUTE_DONORS = (151, 153, 154)
#: 4.15: O4's frozen settings, override, engine and derived facts, unchanged (DisableNameChoice 0 among the settings).
SETTINGS = C4.SETTINGS
OVERRIDE70 = C4.OVERRIDE70
ENGINE = C4.ENGINE
DERIVED = C4.DERIVED
#: 2.5: stock 153's 33 floor-0 upper triangles the walk closes (O5's): the corridor over the hall.
CLOSED_TRIS = list(C5.CLOSED_TRIS)
#: 2.5: THE NORTH DOOR (153, 1190, visit 2) -- the research's walk plan with the critic's corrections and decision 3:
#: a trigger (never a cross: its zone would end the walk at e23's south edge, where e23 cannot fire), its evidence z >
#: 1200 (the door fires past z 1333, the slack derived: 4.12), its landing 154 (S14's ``to``), e24 and e25 avoided, no NPC
#: planned round (the corridor soldiers stand on another floor; the knights walk through).
NORTH_DOOR = {"kind": "trigger", "name": "the north door", "goal": [19, 1620], "until": {"z_gt": 1200}, "to": 154,
              "avoid": ["153.e24", "153.e25"], "closed_tris": list(CLOSED_TRIS), "npcs": False,
              "beat": "steiner_door", "start": [-245, 42]}
#: The keys a rehearsal stage may lay over a table step and the freeze refuses (7.1 R-WALK-VOID's stops; O5's x stop).
REHEARSAL_OVERLAYS = frozenset({"walk_stop_z", "walk_stop_hold", "walk_stop_x"})
#: 4.5: the span O6-KEYS requires of every start-dependent key's ``after.run`` and the report renders from the
#: predictions, never a literal (O7's subclass overrides the class attribute: the claim critic's #4).
AFTER_RUN = "O1-O5"
#: 4.12: the evidence's slack, DERIVED -- his run under control (HonoUpdate's speed, FieldMapActorController.cs:210-211)
#: times the ticks the published position may trail the engine's (two) plus the tick the fire takes control in.
RUN_U_PER_TICK = 60
STALE_TICKS = 3
#: 4.13: the run-wide input witness (S12).
WITNESS = {"input_every_s": 0.05,
           "why": "the naming screen keeps what a keyboard types and PLAYER.Name is no gEventGlobal store: outside input "
                  "would save another name while the driver accepts the default -- the run-wide witness VOIDs a run "
                  "that sees input between blocking calls (V13), and S16's page witness VOIDs one whose page renders "
                  "another name (V13): a key typed during accept_name's blocking call"}
#: 4.11: the page witness's frozen windows -- block 3's sources and each line as the default name renders it (computed
#: by O6-KEYS from the source: [STNR] the default, every tag gone).
ON_PAGE_WINDOWS = [{"mes": 199, "raw_holds": "\u201cCaptain [STNR]!\u201d", "line": 1,
                    "text": "\u201cCaptain Steiner!\u201d"},
                   {"mes": 200, "raw_holds": "[STNR]\n\u201cYes, Your Majesty!\u201d", "line": 0, "text": "Steiner"}]
PAIR_TEXT = C4.PAIR_TEXT
#: 5.4's scope lines that are constants; the start dependence is rendered from the predictions (``after.run``), the
#: settings, the engine and the language are read from the session's record.
SCOPE_NAME = (
    "Steiner's name is PLAYER.Name, no gEventGlobal store: the trace cannot see it. The DRIVER judged the name the GAME "
    "renders on the first parsed [STNR] page after the screen (199's 'Captain Steiner!', 200's speaker line when listed) "
    "against the default, on both sides, and VOIDed any run whose page showed another (V13: input at the naming screen, "
    "which accept_name's blocking call keeps from the run-wide witness); O6-NAMING (b) re-checks every covered run's "
    "row. The screen itself has no field key (Menu(1,3), EventService.StartMenu; the default is CharacterDefaultName, "
    "whose sources P-NAME read before the session: no stacked DictionaryPatch.txt line patches it in US, [Import] Text "
    "off), so S and F open the same one: a non-default name is input or the engine, never the fork. What remains: a "
    "name typed on either side makes that run VOID (re-run); typed on every run of a side it is VOID-ASYM (b), on every "
    "run of both sides the session reads VOID -- never PROVEN, and never a fork finding. A page the instrument never "
    "caught parsed leaves its run uncovered")
SCOPE_END_STATE = ("read live on arrival in 154: 154@315 stores only same-value prologue keys (ip279 is the 304 "
                   "branch's), so Byte[8] is read live too")
#: A-NAMING's reason (5.1): the named row's ``before`` without 198's marker -- the instrument's miss, never a failure.
A_NAMING = "A-NAMING"
_MODULE_DOC = __doc__


# ======================================================================== the chain (O4's campaign.toml)
def chain_from_campaign(campaign=None) -> tuple:
    """``({fork id: donor}, {fork id: member name})`` of O4's built alxc chain (its ``campaign.toml``; default O4's):
    its donors exactly O4's twenty (o4_castle.chain_from_campaign refuses another chain)."""
    return C4.chain_from_campaign(Path(campaign) if campaign is not None else CHAIN_DIR / "campaign.toml")


def route_members(members: dict) -> dict:
    """``{151: fork id, 153: fork id, 154: fork id}``: the members the route runs and ends in (derived, each donor
    forked by exactly one member)."""
    out = {}
    for donor in ROUTE_DONORS:
        hits = sorted(f for f, d in members.items() if d == donor)
        if len(hits) != 1:
            raise AssertionError(f"donor {donor} is forked by {hits}, not exactly one member")
        out[donor] = hits[0]
    return out


def route_members_line(members: dict) -> str:
    """The line --offline-check and --draft print: ``member(151) 31244, member(153) 31245, member(154) 31246``."""
    rm = route_members(members)
    return ", ".join(f"member({d}) {rm[d]}" for d in ROUTE_DONORS)


# ======================================================================== the predictions (draft v1)
def _key(donor, sid, tag, ip, off, target, value, op, what, prior=None) -> dict:
    return A._key(donor, sid, tag, ip, off, target, value, op, what, prior)


def _site(place_, sid, tag, ip, target, value, **kw) -> dict:
    return C4._site(place_, sid, tag, ip, target, value, **kw)


def route_pins() -> list:
    """4.16's route pins: ``[donor, sid, tag, ip, eb-src text]`` -- the bytes the driver, the naming, the walk and the
    FakeGame rest on, each compared EXACTLY with the stock US script's instruction text (O6-KEYS (b)): 74 sites."""
    pins = [[151, 0, 0, 232, "SET({Global.Int16[2] const(110) B_EQ B_EXPR_END})"], [151, 0, 0, 240, "JMP_IFNOT(L340)"],
            [151, 0, 0, 461, "SET({Global.UInt16[0] const(12000) B_LT B_EXPR_END})"],
            [151, 0, 0, 1010, "SET({Map.Bit[158] const(1) B_EQ B_EXPR_END})"],
            [151, 3, 0, 171, "DefinePlayerCharacter()"], [151, 12, 0, 149, "SWITCH(110, L159, L147)"]]
    pins += [[151, 4, 1, 516, PAIR_TEXT], [151, 4, 1, 693, PAIR_TEXT], [151, 3, 1, 475, PAIR_TEXT],
             [151, 3, 1, 742, PAIR_TEXT], [151, 12, 1, 935, PAIR_TEXT]]
    pins += [[151, 3, 1, 576, "WindowAsync(0, 128, 198)"], [151, 3, 1, 590, "WaitWindow(0)"],
             [151, 3, 1, 593, "SetCharacterData(3, 0, 3, 5, 3)"], [151, 3, 1, 603, "Menu(1, 3)"],
             [151, 3, 1, 610, "SET({Global.Byte[6] const(8) B_OR_LET B_EXPR_END})"],
             [151, 3, 1, 693, "WindowAsync(0, 128, 199)"], [151, 12, 1, 803, "WindowSync(4, 128, 200)"],
             [151, 2, 1, 932, "SET({Global.Int16[2] const(328) B_LET B_EXPR_END})"], [151, 2, 1, 940, "Field(153)"]]
    pins += [[153, 0, 0, 232, "SET({Global.UInt16[0] const(1900) B_GT B_EXPR_END})"],
             [153, 0, 0, 255, "SWITCHEX(L1098, 325, L273, 5, L438, 328, L603, 316, L799, 3, L951)"],
             [153, 0, 0, 626, "InitRegion(23, 0)"], [153, 0, 0, 629, "InitRegion(24, 0)"],
             [153, 0, 0, 632, "InitRegion(25, 0)"], [153, 0, 0, 802, "JMP(L1288)"],
             [153, 32, 0, 22, "SWITCH(324, L383, L140, L383, L383, L59, L24, L221, L302)"],
             [153, 32, 0, 520, "SetObjectLogicalSize(30, 35, 50)"], [153, 32, 0, 717, "DefinePlayerCharacter()"],
             [153, 32, 0, 548, "SetPathing(1)"],
             [153, 32, 1, 866, "RunSharedScript(15)"], [153, 15, 0, 6, "op_22(45)"],
             [153, 15, 0, 32, "SET({Global.Byte[8] const(125) B_LET B_EXPR_END})"],
             [153, 32, 1, 1160, "SetWalkSpeed(60)"], [153, 32, 1, 1360, "Walk(64961, 807)"],
             [153, 32, 1, 1367, "Walk(65291, 42)"],
             [153, 32, 1, 2152, "SET({const(5) B_PARTYCHK B_EXPR_END})"],
             [153, 32, 1, 2180, "SET({Global.UInt16[19] const(3) B_SHIFT_RIGHT const(1) B_AND const(0) B_EQ "
                                "B_EXPR_END})"],
             [153, 32, 1, 2206, "SET({Global.UInt16[19] const(8) B_OR_LET B_EXPR_END})"],
             [153, 32, 1, 2382, "SET({Map.Bit[158] const(1) B_LET B_EXPR_END})"],
             [153, 32, 1, 2390, "SET({Map.Bit[159] const(1) B_EQ B_EXPR_END})"],
             [153, 32, 1, 2401, "SET({Map.Bit[156] const(0) B_EQ B_EXPR_END})"], [153, 32, 1, 2412, "EnableMove()"]]
    pins += [[153, 23, 2, 30, "SET({B_SYSVAR[2] B_EXPR_END})"],
             [153, 23, 2, 38, "SET({obj(uid=250).f[1] const(65436) B_GT obj(uid=250).f[2] const(1333) B_GT B_ANDAND "
                              "B_EXPR_END})"],
             [153, 23, 2, 58, "CalculateExitPosition()"], [153, 23, 2, 59, "ExitField()"],
             [153, 23, 2, 95, "op_22(1)"], [153, 23, 2, 153, "op_22(25)"],
             [153, 23, 2, 203, "SET({Global.Int16[2] const(315) B_LET B_EXPR_END})"], [153, 23, 2, 211, "Field(154)"],
             [153, 23, 2, 68, "SET({Map.Bit[159] const(1) B_EQ B_EXPR_END})"], [153, 23, 2, 76, "JMP_IFNOT(L68)"],
             [153, 23, 2, 79, "DisableMove()"], [153, 23, 2, 80, "SET({Map.Bit[144] const(0) B_EQ B_EXPR_END})"],
             [153, 23, 2, 88, "JMP_IFNOT(L65)"], [153, 23, 2, 91, "DisableMenu()"], [153, 23, 2, 92, "JMP(L68)"],
             [153, 0, 0, 2356, "SET({Map.Bit[159] const(1) B_LET B_EXPR_END})"]]
    pins += [[153, 24, 2, 30, "SET({B_SYSVAR[2] B_EXPR_END})"],
             [153, 24, 2, 183, "SET({Global.Int16[2] const(315) B_LET B_EXPR_END})"], [153, 24, 2, 191, "Field(150)"],
             [153, 25, 2, 30, "SET({B_SYSVAR[2] B_EXPR_END})"],
             [153, 25, 2, 38, "SET({obj(uid=250).f[1] const(65436) B_GT B_EXPR_END})"],
             [153, 25, 2, 195, "SET({Global.Int16[2] const(315) B_LET B_EXPR_END})"], [153, 25, 2, 203, "Field(64)"],
             [153, 25, 2, 210, "SET({obj(uid=250).f[2] const(64136) B_LT B_EXPR_END})"],
             [153, 25, 2, 222, "SET({Global.Byte[8] const(0) B_LET B_EXPR_END})"],
             [153, 25, 2, 421, "SET({Global.Int16[2] const(315) B_LET B_EXPR_END})"], [153, 25, 2, 429, "Field(151)"],
             [153, 3, 1, 3158, "Field(154)"],
             [154, 0, 0, 234, "SWITCH(304, L392, L232)"],
             [154, 0, 0, 26, "SET({Global.Bit[191] const(0) B_LET B_EXPR_END})"], [154, 0, 0, 588, "EnableMove()"]]
    return pins


def route_build() -> dict:
    """O6-BUILD's route pins (6.1): O5's, unchanged -- the same three route members, measured by O6's C0 on O4's build in
    every language (each language's script decoded on its own): the only bytes each differs from its donor in are the
    operands of its in-chain ``Field()`` sites."""
    out = C5.route_build()
    out["why"] = ("C0 (research/o6_design.md 9 PART C), re-measured on O4's build C:/gd/_ns_playtest/o4/build: per "
                  "language, each route member differs from its donor in exactly these operands (151: 4 bytes, 153: 14, "
                  "154: 14) -- O5's C0 (o5_forks.json built.measured) found the same")
    return out


def route_mes() -> dict:
    """4.16's ``route_mes`` (block 3, US: the asset the engine reads): 198 holds the naming's marker; 199 and 200 hold the
    [STNR] sources the page witness reads; 56 holds the stop page."""
    return {"block": TEXT_BLOCK, "before": {"mes": 198, "holds": "And, Captain"},
            "on_page": [{"mes": 199, "holds": "\u201cCaptain [STNR]!\u201d"},
                        {"mes": 200, "holds": "[STNR]\n\u201cYes, Your Majesty!\u201d"}],
            "stop_page": {"mes": 56, "holds": "Env Play()"}}


def _regions() -> dict:
    """4.17's regions: each the FIRST SetRegion of its (donor, entry) in the stock bytes, in the engine's point order
    (O6-REGIONS re-decodes each), with its role -- 153's three live exits at 328, its three side regions dormant there
    (instanced at 325 only), and 151's region 8 (instanced on the default entrance's branch only)."""
    e23 = [[-227, 3000], [200, 3000], [212, 935], [-264, 924]]
    e25 = [[-777, -2348], [777, -2348], [777, -900], [-777, -900]]
    e24 = [[2850, 347], [2850, -13], [1739, -74], [1739, 406]]
    return {
        "153.e23": A._exit(e23, 154, 315, None,
                           why="the north door: tag 2 needs SYSVAR[2], the ground (f[1] > -100) and z > 1333 (ip38); "
                               "ExitField ip59, ip203 Int16[2] := 315, ip211 Field(154)"),
        "153.e24": A._exit(e24, 150, 315, None,
                           why="tag 2 needs SYSVAR[2] alone: ip183 Int16[2] := 315, ip191 Field(150)"),
        "153.e25": A._exit(e25, 64, 315, None,
                           why="on the ground ip195/ip203 -> 64; upstairs with z < -1400 ip222 Byte[8] := 0, ip421/ip429 "
                               "-> 151 (unreachable after the grant)"),
        "153.e26": A._region(e23, "dormant", entrances=[328], why="side scene A (325)"),
        "153.e27": A._region(e25, "dormant", entrances=[328], why="side scene B (325)"),
        "153.e28": A._region(e24, "dormant", entrances=[328], why="the back door (325)"),
        "151.e8": A._region([[-187, -7057], [173, -7000], [173, -8914], [-187, -8914]], "dormant", entrances=[110],
                            why="InitRegion(8) only on the default branch L340: -> 153 @327"),
    }


def _pattern() -> dict:
    """4.18: THE EMITTED ROW PATTERN over this start (field 70's prologue values, the raw warp): no site is stored twice
    before the cut, so the sink emits every store and no ``c`` row arises -- each visit's emitted ``w`` rows in order,
    ``[place, sid, tag, off, target, new, same]``, with the shared script's e15 row FLOATING: present exactly once in
    visit 2, after e32 t0 ip727 and before e32 t1 ip1656 (the bytes' window), its place among the rows between not
    compared. ``measured`` is R-DOOR's (F4, report-only), written by the freeze."""
    def pro(place_, same9, same13):
        return [[place_, 0, 0, 16, "Global.Bit[191]", 0, 1], [place_, 0, 0, 43, "Global.Bit[184]", 0, 1],
                [place_, 0, 0, 51, "Global.Int16[9]", -1, same9], [place_, 0, 0, 113, "Global.Byte[13]", 0, same13],
                [place_, 0, 0, 132, "Global.Int16[11]", -1, 1], [place_, 0, 0, 194, "Global.Byte[14]", 0, 1]]
    v1 = pro(151, 0, 0) + [[151, 0, 0, 309, "Global.Byte[8]", 125, 1], [151, 3, 1, 426, "Global.Byte[6]", 8, 0],
                           [151, 2, 1, 724, "Global.Byte[8]", 0, 0], [151, 2, 1, 921, "Global.Int16[2]", 328, 0]]
    v2 = pro(153, 1, 1) + [[153, 32, 0, 700, "Global.Bit[3855]", 1, 0], [153, 32, 0, 709, "Global.Bit[3854]", 1, 0],
                           [153, 32, 1, 234, "Global.Byte[208]", 0, 1], [153, 32, 1, 269, "Global.Byte[208]", 1, 0],
                           [153, 32, 1, 304, "Global.Byte[208]", 0, 0], [153, 32, 1, 339, "Global.Byte[208]", 1, 0],
                           [153, 32, 1, 860, "Global.Byte[208]", 0, 0], [153, 32, 1, 895, "Global.Byte[208]", 1, 0],
                           [153, 32, 1, 919, "Global.UInt16[21]", 8, 0], [153, 32, 1, 1004, "Global.Byte[303]", 0, 1],
                           [153, 32, 1, 1038, "Global.Byte[303]", 1, 0], [153, 32, 1, 1435, "Global.Byte[4]", 0, 1],
                           [153, 32, 1, 1469, "Global.UInt16[19]", 8, 0], [153, 32, 1, 1495, "Global.Byte[4]", 0, 1],
                           [153, 32, 1, 1503, "Global.Byte[17]", 0, 1], [153, 32, 1, 1511, "Global.Byte[18]", 1, 0],
                           [153, 23, 2, 173, "Global.Int16[2]", 315, 0]]
    floating = [{"visit": 2, "tuple": [153, 15, 0, 26, "Global.Byte[8]", 125, 0],
                 "after": [153, 32, 0, 709, "Global.Bit[3854]", 1, 0],
                 "before": [153, 32, 1, 919, "Global.UInt16[21]", 8, 0], "measured": None,
                 "why": "153 e15 t0 ip32, the Seq e32 t1 ip866 starts: op_22(45) and a sound sync before it, against at "
                        "least 40 ticks of waits and five pages before ip971 -- in order unless the sync stalls (0.2 "
                        "#11); the window is the bytes': it cannot precede ip866, which follows e32 t0's ip727, and "
                        "ip1656 (the rebuild) comes >= 351 ticks of op_22, the stair walks and four pages after ip971; "
                        "its place among the e32 t1 rows between is not compared"}]
    return {"visits": [v1, v2], "floating": floating, "counts": [],
            "why": "StoryTrace.cs:374-401 over the raw warp's start values (Int16[9] 643, Byte[13] 1, Int16[11] -1, "
                   "Byte[14] 0, Byte[8] 125, Bit[191] 0, Bit[184] 0): no site is stored twice before the cut, so every "
                   "store is emitted and no c row arises; 151's prologue changes Int16[9] and Byte[13], 153's prologue "
                   "is all same-value but EMITTED (new sites in the epoch); 34 w rows (30 unmasked)"}


def start_dependent() -> list:
    """4.5: the two START-DEPENDENT keys (O2's 4.5 shape; decision 5), the same on S and F: each a ``|=`` whose value
    is 8 on New Game's 0 here, and -- ``after`` -- what it writes after the O1-O5 routes as driven: ``after.old`` READ
    from the archives at design time (``after.source``), ``after.value`` computed by O6-KEYS from it and the
    statement, ``after.run`` the class's AFTER_RUN (O6-KEYS requires it)."""
    k610 = _key(151, 3, 1, 610, 426, "Global.Byte[6]", 8, "|=",
                "151 Byte[6] |= 8 after Menu(1,3) (Steiner's naming): 0 -> 8 on New Game's 0", "newgame0")
    k2206 = _key(153, 32, 1, 2206, 1469, "Global.UInt16[19]", 8, "|=",
                 "153 UInt16[19] |= 8 in Steiner's rebuild: 0 -> 8 on New Game's 0", "newgame0")
    src = ("old READ at design time from the story-o1e (all six runs) and story-o2 S traces, the routes as driven "
           "(o6_design.md 0.2 #9); story-o3/-o4/-o5 hold no row on ")
    return [dict(k610, after={"run": AFTER_RUN, "old": 3, "value": 11, "source": src + "byte 6",
                              "why": "Byte[6] |= 1 at 50 e17 t1 ip3240 (O1, Zidane's naming) and |= 2 at 116 e2 t1 ip765 "
                                     "(O2, Vivi's); O3-O5 write it nowhere (their traces hold no row on byte 6)"}),
            dict(k2206, after={"run": AFTER_RUN, "old": 1799, "value": 1807, "source": src + "bytes 19-20",
                               "why": "O1 leaves 1797 (50 e17 t1 ip1629/1667, e13 t1 ip1149/1187/1225: 0 -> 1 -> 5 -> "
                                      "261 -> 773 -> 1797), O2 |= 2 at 100 e19 t1 ip1531 -> 1799; O3-O5 write it "
                                      "nowhere; bit 3 is clear in both, so ip2180's guard takes the same branch"})]


def draft_predictions(campaign=None) -> dict:
    """The registered claims (research/o6_design.md section 4). Every number was read off the stock bytes (the offline
    check re-derives each: O6-BUILD's pins, O6-KEYS with the route pins and route_mes, O6-TEXT, O6-CENSUS at each
    entrance, O6-REGIONS, O6-GOALS), O4's build (C0), the live install or O4's campaign.toml (``campaign``); nothing is
    read from a run. The rehearsals (o6_rehearse.py) settle the driver's numbers before the lead freezes them (7.3)."""
    members, names = chain_from_campaign(campaign)
    rm = route_members(members)
    key = _key
    sd = start_dependent()
    writes = P._ambient(151, (57, 119, 138, 200)) + [
        key(151, 0, 0, 315, 309, "Global.Byte[8]", 125, ":=", "151 Byte[8] := 125 after the BGM wait (same: field 70 "
                                                               "left 125)"),
        key(151, 3, 1, 610, 426, "Global.Byte[6]", 8, "|=", "151 Byte[6] |= 8 after Menu(1, 3): START-DEPENDENT (4.5)",
            "newgame0"),
        key(151, 2, 1, 735, 724, "Global.Byte[8]", 0, ":=", "151 Byte[8] := 0 (stage 23)")] \
        + P._ambient(153, (57, 119, 138, 200)) + [
        key(153, 32, 0, 718, 700, "Global.Bit[3855]", 1, ":=", "153 Bit[3855] := 1 (Steiner's t0 at 328)"),
        key(153, 32, 0, 727, 709, "Global.Bit[3854]", 1, ":=", "153 Bit[3854] := 1 (Steiner's t0 at 328)"),
        key(153, 15, 0, 32, 26, "Global.Byte[8]", 125, ":=", "153 e15 Byte[8] := 125 (the shared script: the Seq e32 t1 "
                                                             "ip866 runs)"),
        key(153, 32, 1, 971, 234, "Global.Byte[208]", 0, ":=", "153 Byte[208] := 0 (stage 43, 217's loop)"),
        key(153, 32, 1, 1006, 269, "Global.Byte[208]", 1, "++", "153 Byte[208] ++ (stage 43)", "153/32/1/971"),
        key(153, 32, 1, 1041, 304, "Global.Byte[208]", 0, ":=", "153 Byte[208] := 0 (218's loop)"),
        key(153, 32, 1, 1076, 339, "Global.Byte[208]", 1, "++", "153 Byte[208] ++ (218's loop)", "153/32/1/1041"),
        key(153, 32, 1, 1597, 860, "Global.Byte[208]", 0, ":=", "153 Byte[208] := 0 (stage 48, 222's loop)"),
        key(153, 32, 1, 1632, 895, "Global.Byte[208]", 1, "++", "153 Byte[208] ++ (222's loop)", "153/32/1/1597"),
        key(153, 32, 1, 1656, 919, "Global.UInt16[21]", 8, ":=", "153 UInt16[21] := 8 (the rebuild: the party mask, "
                                                                 "Steiner)"),
        key(153, 32, 1, 1741, 1004, "Global.Byte[303]", 0, ":=", "153 Byte[303] := 0 (the rebuild)"),
        key(153, 32, 1, 1775, 1038, "Global.Byte[303]", 1, "++", "153 Byte[303] ++ (the rebuild)", "153/32/1/1741"),
        key(153, 32, 1, 2172, 1435, "Global.Byte[4]", 0, ":=", "153 Byte[4] := 0 (PARTYCHK(5) false)"),
        key(153, 32, 1, 2206, 1469, "Global.UInt16[19]", 8, "|=", "153 UInt16[19] |= 8 (ip2180's bit-3 guard true): "
                                                                  "START-DEPENDENT (4.5)", "newgame0"),
        key(153, 32, 1, 2232, 1495, "Global.Byte[4]", 0, ":=", "153 Byte[4] := 0 (the rebuild)"),
        key(153, 32, 1, 2240, 1503, "Global.Byte[17]", 0, ":=", "153 Byte[17] := 0 (the rebuild)"),
        key(153, 32, 1, 2248, 1511, "Global.Byte[18]", 1, ":=", "153 Byte[18] := 1 (the rebuild)")]
    chain = [key(151, 2, 1, 932, 921, "Global.Int16[2]", 328, ":=", "FieldEntrance 328: 151 stage 23, then Field(153)"),
             key(153, 23, 2, 203, 173, "Global.Int16[2]", 315, ":=", "FieldEntrance 315: the north door (e23 t2), then "
                                                                     "Field(154)")]
    error_path = [key(donor, 0, 0, ip, off, target, value, ":=", f"{donor} e0 t0 ip{ip}: the error path ({target} := "
                                                                  f"{value})")
                  for donor, ip, off, target, value in (
        (151, 97, 91, "Global.Byte[13]", 9), (151, 178, 172, "Global.Byte[14]", 9),
        (151, 960, 954, "Global.Byte[13]", 0), (151, 994, 988, "Global.Byte[14]", 0),
        (153, 97, 91, "Global.Byte[13]", 9), (153, 178, 172, "Global.Byte[14]", 9),
        (153, 2314, 2308, "Global.Byte[13]", 0), (153, 2348, 2342, "Global.Byte[14]", 0))]
    forbidden_sites = [
        key(153, 24, 2, 183, 153, "Global.Int16[2]", 315, ":=", "153 e24 Int16[2] := 315 (the door to 150)"),
        key(153, 25, 2, 195, 165, "Global.Int16[2]", 315, ":=", "153 e25 Int16[2] := 315 (on the ground, the door to "
                                                                "64)"),
        key(153, 25, 2, 222, 192, "Global.Byte[8]", 0, ":=", "153 e25 Byte[8] := 0 (upstairs with z < -1400)"),
        key(153, 25, 2, 421, 391, "Global.Int16[2]", 315, ":=", "153 e25 Int16[2] := 315 (upstairs, the door to 151)")]
    dead = [
        key(151, 0, 0, 41, 35, "Global.Int16[2]", 10000, ":=", "151 Int16[2] := 10000 (dead: Bit[184] == 1)"),
        key(151, 0, 0, 130, 124, "Global.Byte[13]", 1, ":=", "151 Byte[13] := 1 (dead: Int16[9] just set -1)"),
        key(151, 0, 0, 211, 205, "Global.Byte[14]", 1, ":=", "151 Byte[14] := 1 (dead: Int16[11] just set -1)"),
        key(151, 0, 0, 410, 404, "Global.Byte[8]", 125, ":=", "151 Byte[8] := 125 (dead: the default entrance's "
                                                               "branch, L340)"),
        key(151, 3, 3, 909, 61, "Global.Bit[3793]", 1, ":=", "151 e3 t3 Bit[3793] := 1 (dead: Brahne's talk handler; "
                                                             "she is the defined player at 110, no control exists)"),
        key(153, 0, 0, 41, 35, "Global.Int16[2]", 10000, ":=", "153 Int16[2] := 10000 (dead: Bit[184] == 1)"),
        key(153, 0, 0, 130, 124, "Global.Byte[13]", 1, ":=", "153 Byte[13] := 1 (dead: Int16[9] just set -1)"),
        key(153, 0, 0, 211, 205, "Global.Byte[14]", 1, ":=", "153 Byte[14] := 1 (dead: Int16[11] just set -1)"),
        key(153, 0, 0, 243, 237, "Global.Int16[2]", 3, ":=", "153 Int16[2] := 3 (dead: ip232 SC > 1900 false)"),
        key(153, 0, 0, 1188, 1182, "Global.Byte[8]", 125, ":=", "153 Byte[8] := 125 (dead: L1098, skipped by ip802 at "
                                                                 "328)"),
        key(153, 0, 0, 1260, 1254, "Global.Byte[8]", 125, ":=", "153 Byte[8] := 125 (dead: L1098, skipped by ip802 at "
                                                                 "328)"),
        key(153, 32, 1, 1797, 1060, "Global.Byte[303]", 2, "++", "153 Byte[303] ++ (dead: behind a const(0) test)",
            "153/32/1/1775"),
        key(153, 32, 1, 1819, 1082, "Global.Byte[303]", 3, "++", "153 Byte[303] ++ (dead: behind a const(0) test)",
            "153/32/1/1797"),
        key(153, 32, 1, 1841, 1104, "Global.Byte[303]", 4, "++", "153 Byte[303] ++ (dead: behind a const(0) test)",
            "153/32/1/1819"),
        key(153, 32, 1, 2161, 1424, "Global.Byte[4]", 1, ":=", "153 Byte[4] := 1 (dead: behind PARTYCHK(5), false "
                                                               "after the rebuild)")]
    inert = ([{"donor": 151, "sid": 8, "tags": "*", "why": "region 8: InitRegion(8) only on the default branch L340"}]
             + [{"donor": 153, "sid": s, "tags": "*", "why": why} for s, why in (
                 (3, "instanced at 325 and the default only"), (18, "instanced at 316 only"),
                 (28, "instanced at 325 only"))])
    live_shared = [{"donor": 153, "sid": 15, "callers": [[32, 1, 866]],
                    "why": "entry 15 is a shared script with no instance of its own: e32 t1 ip866 RunSharedScript(15) "
                           "runs it (STARTSEQ, DoEventCode.cs:1414-1421), and e32 IS instanced at 328 -- so its ip32 "
                           "Byte[8] := 125 is a writes key, its row sid 15, uid 96, tag 0, ip 32, add 0"}]
    start_music = dict(key(151, 0, 0, 119, 113, "Global.Byte[13]", 0, ":=",
                           "151's ambient branch from the warp's Byte[13] 1 (field 70's prologue :=1 at ip130; the warp "
                           "leaves 70 before ip475's :=2)"), old=1)
    naming = [{"donor": 151, "sc": 1190, "beat": "named",
               "on_page": {"tag": "[STNR]", "beat": "name_on_page", "windows": copy.deepcopy(ON_PAGE_WINDOWS),
                           "why": "PLAYER.Name is no gEventGlobal store: the first parsed page rendering [STNR] after the "
                                  "screen is the name's only witness (0.2 #8); the driver judges it (V13 on another "
                                  "name), O6-NAMING (b) re-checks it"}}]
    return {
        "version": 1,
        "what": f"O6: 151@1190 (warp, entrance 110; EVT_ALEX1_AC_SEAT_R) -> Steiner's naming -> 153@328 "
                f"(EVT_ALEX1_AC_H2F; the Knights of Pluto) -> Steiner's first control, the walk to the north door -> "
                f"Field(154) at 315 (EVT_ALEX1_AC_ENT_2F), SC 1190; stock vs the alxc disc-1 chain as O4 deployed it "
                f"(route members {rm[151]}-{rm[154]}; PLAN.md, O6) -- a US session",
        "rehearsals": [],                                       # 7.3: the lead names R-DOOR's runs at the freeze
        "order": ["S", "F", "S", "F", "S", "F"],
        "min_covered": 2,
        "rerun": {"max": 2, "stop_on": ["V19"]},
        # F6 replaces every number from R-DOOR (4.14)
        "budget": {"run_s": 600, "run_min_s": 300, "session_s": 3600, "settle_s": 1.0, "no_progress_s": 60,
                   "end_row_s": 10.0},
        "start": {"S": ROUTE[0], "F": rm[ROUTE[0]]},
        "entrance": 110,
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
        "start_first": key(151, 0, 0, 22, 16, "Global.Bit[191]", 0, ":=",
                           "151's Main_Init: its first store (emitted same: a new site)"),
        "start_music": start_music,
        # SC 1190 = 0x04A6 (bytes 0 and 1); FieldEntrance 110 = 0x006E (byte 2; byte 3 stays 0): THREE rows (0.2 #1)
        "start_residue": [[0, 0, 166], [1, 0, 4], [2, 0, 110]],
        "residue_after_start": [],
        "sc_bytes": [0, 1],
        "ladder": [],
        "entrance_bytes": [2, 3],
        "chain": chain,
        "writes": writes,
        "start_dependent": sd,
        "error_path": error_path,
        "forbidden_sites": forbidden_sites,
        "dead": dead,
        "inert": inert,
        "live_shared": live_shared,
        "noise": [],
        "forbidden": [{"off_route": True, "cause": "walk",
                       "why": "a write off the route: S, a place outside [151, 153] + [154]; F, a field that is neither "
                              "a member whose donor is on the route nor F's own end field (real 151/153/154 on F: an "
                              "un-retargeted Field() or an engine id leak; 150/31243 or 64/31240 after a walk into "
                              "e24/e25, backed by its V11 step row)"}],
        "landing": {"route_places": list(ROUTE),
                    "exit151": _site(151, 2, 1, 932, "Global.Int16[2]", 328),
                    "enter153": _site(153, 0, 0, 22, "Global.Bit[191]", 0),
                    "exit153": _site(153, 23, 2, 203, "Global.Int16[2]", 315),
                    "end_row": _site(END_FIELD, 0, 0, 26, "Global.Bit[191]", 0)},
        "end_state": {"Global.UInt16[0]": 1190, "Global.Int16[2]": 315, "Global.Byte[6]": 8, "Global.Byte[8]": 125,
                      "Global.Bit[3855]": 1, "Global.Bit[3854]": 1, "Global.Byte[208]": 1, "Global.UInt16[21]": 8,
                      "Global.Byte[303]": 1, "Global.Byte[4]": 0, "Global.UInt16[19]": 8, "Global.Byte[17]": 0,
                      "Global.Byte[18]": 1, "Global.Byte[13]": 0, "Global.Byte[14]": 0, "Global.Int16[9]": -1,
                      "Global.Int16[11]": -1, "Global.Bit[191]": 0, "Global.Bit[184]": 0,
                      "Global.Bit[3795]": 0, "Global.Bit[3793]": 0, "Global.Byte[475]": 0, "Global.Bit[3815]": 0,
                      "Global.Bit[3717]": 0, "Global.Bit[3718]": 0, "Global.Int16[469]": 0, "Global.Byte[472]": 0,
                      "Global.Byte[206]": 0, "Global.Bit[3796]": 0, "Global.Bit[3811]": 0, "Global.Bit[3852]": 0},
        "naming": naming,
        "name": {"place": 151, "char": 3, "default": "Steiner", "before": {"mes": 198, "marker": "And, Captain"},
                 "store": {"place": 151, "sid": 3, "tag": 1, "ip": 610, "target": "Global.Byte[6]"},
                 "why": "151 e3 t1: 198 (WaitWindow ip590), ip603 Menu(1,3), ip610 Byte[6] |= 8; stage 21 opens 199, "
                        "then 200 ~6 ticks later"},
        "walk": {"name": "the north door", "donor": 153, "visit": 2, "door": "153.e23",
                 "why": "153 e23 t2 ip38: on the ground (f[1] > -100) and past z 1333 takes control (ExitField ip59); "
                        "the loss sample is read at or north of the line (the walk-out walks north); THE PAIRED-WALK "
                        "LAW: nothing stores between ip2412 and the loss"},
        "beats": ["named", "name_on_page", "steiner_door"],
        "battles": [],
        "stop_pages": [{"match": "Env Play()",
                        "why": "151's and 153's ambient error window 56 ('Error Env Play() Slot=n': 151 e0 t0 "
                               "ip950/984, 153 e0 t0 ip2304/2338): Byte[13]/[14] arrived as 2 or 9"}],
        "regions": _regions(),
        "hotspots": {},
        "table": [{"donor": 153, "sc": 1190, "visit": 2, "steps": [copy.deepcopy(NORTH_DOOR)]}],
        "steps_default": {"attempts": 2, "interrupts": 1, "timeout_s": 20, "confirm_s": 4.0, "npcs": True,
                          "overlay_ok": False, "immediate": False, "settle": None, "lunge_ticks": 0, "tolerance": 45,
                          "min_depth": 40, "exit_wait_s": 5.0, "exit_slack": 40,
                          "climb": {"burst_frames": 30, "max_bursts": 80, "stall_bursts": 8}},
        "choices": [{"donor": None, "sc": None, "match": "want to skip", "pick": "default", "once": False,
                     "beat": None}],
        "witness": dict(WITNESS),
        "route_pins": route_pins(),
        "route_mes": route_mes(),
        "route_build": route_build(),
        "pattern": _pattern(),
        "settings": json.loads(json.dumps(SETTINGS)),
        "override70": dict(OVERRIDE70),
        "derived": json.loads(json.dumps(DERIVED)),
        "engine": dict(ENGINE),
    }


# ======================================================================== the bytes: instancing at an entrance
_INIT = C4._INIT
_LABEL = C4._LABEL
_COMPARE = re.compile(r"^SET\(\{Global\.Int16\[2\] const\((\d+)\) B_EQ B_EXPR_END\}\)$")


def instanced_at6(idx, entrance: int, *, items=None) -> set:
    """The entries Main_Init (e0 t0) instances at ``entrance`` -- ``{(kind, n)}`` -- by its control flow (research/
    o6_design.md 0.2 #2): O4's walker (o4_castle.instanced_at: every item reachable from the function's start, every
    other branch and switch followed both ways, a SOUND over-approximation), its entrance dispatch EITHER the SWITCH /
    SWITCHEX on ``Global.Int16[2]`` (taken only to ``entrance``'s case) OR -- 151's form, which O4's raises on -- every
    ``SET({Global.Int16[2] const(N) B_EQ B_EXPR_END})`` followed by ``JMP_IFNOT(L)`` / ``JMP_IF(L)``, the entrance
    deciding the branch (equal: JMP_IFNOT falls through, JMP_IF jumps; else the other way). ``items`` (``[(ip, rel,
    eb-src text)]``, a seam) replaces the decode of ``idx``'s e0 t0. ValueError when Main_Init holds neither form."""
    items = items if items is not None else A.O2Segment._items(idx, 0, 0)
    by_rel = {rel: i for i, (_ip, rel, _t) in enumerate(items)}
    k = next((i for i, (_ip, _rel, t) in enumerate(items) if t.startswith(("SWITCH(", "SWITCHEX("))
              and i > 0 and items[i - 1][2] == "SET({Global.Int16[2] B_EXPR_END})"), None)
    compares = {}
    for i, (_ip, _rel, t) in enumerate(items):
        m = _COMPARE.match(t)
        if m and i + 1 < len(items) and items[i + 1][2].startswith(("JMP_IFNOT(", "JMP_IF(")):
            compares[i] = int(m.group(1))
    if k is None and not compares:
        raise ValueError("Main_Init holds no SWITCH / SWITCHEX on Global.Int16[2] and no Int16[2] compare (const(N) "
                         "B_EQ, then JMP_IFNOT / JMP_IF): no entrance dispatch")

    def entrance_target(text: str):
        if text.startswith("SWITCHEX("):
            args = [a.strip() for a in text[len("SWITCHEX("):-1].split(",")]
            default, pairs = args[0], args[1:]
            for v, lab in zip(pairs[0::2], pairs[1::2]):
                if int(v) == int(entrance):
                    return int(lab[1:])
            return int(default[1:])
        m = re.match(r"SWITCH\((\d+), L(\d+)((?:, L\d+)*)\)", text)
        base, default = int(m.group(1)), int(m.group(2))
        cases = [int(x) for x in _LABEL.findall(m.group(3))]
        n = int(entrance) - base
        return cases[n] if 0 <= n < len(cases) else default
    seen, todo, out = set(), [0], set()
    while todo:
        i = todo.pop()
        while i is not None and 0 <= i < len(items) and i not in seen:
            seen.add(i)
            _ip, _rel, t = items[i]
            m = _INIT.match(t)
            if m:
                out.add((m.group(1).lower(), int(m.group(2))))
            if i == k:
                i = by_rel.get(entrance_target(t))
                continue
            if i in compares:                                   # the compare form: the entrance decides the branch
                jmp = items[i + 1][2]
                seen.add(i + 1)
                label = int(_LABEL.search(jmp).group(1))
                equal = int(entrance) == compares[i]
                jumps = (not equal) if jmp.startswith("JMP_IFNOT(") else equal
                i = by_rel.get(label) if jumps else i + 2
                continue
            if t.startswith("RET"):
                break
            if t.startswith("JMP("):
                i = by_rel.get(int(_LABEL.search(t).group(1)))
                continue
            if t.startswith(("JMP_IF(", "JMP_IFNOT(", "SWITCH(", "SWITCHEX(")):
                todo += [by_rel[int(x)] for x in _LABEL.findall(t) if int(x) in by_rel]
            i += 1
    return out


# ======================================================================== O6-CENSUS (pure but for the stock reader)
#: O6-CENSUS's classes in the order the detail prints them (O5's).
CENSUS_LISTS = C5.CENSUS_LISTS
CENSUS_PRECEDENCE = C4.CENSUS_PRECEDENCE
CENSUS_REGISTERED = C4.CENSUS_REGISTERED


def _holds_store(idx, sid: int, sites=None) -> bool:
    """Whether entry ``sid`` of a script holds any gEventGlobal store site (decoded or not)."""
    found, _und = (sites or P.store_sites)(idx)
    return any(s["sid"] == sid for s in found)


def store_census6(fields, stock, pred: dict, *, sites=None, classify=None, instanced=None) -> tuple:
    """O6-CENSUS's reader (research/o6_design.md 6.1; 0.2 #2-#3): ``(problems, {field: Counter(class)}, proof)`` -- O5's
    census (every gEventGlobal store site of each stock field registered, masked, start_first or in an ``inert``
    FUNCTION; an unresolved store classified by its lvalue token; a function that does not decode FAILS; a registered
    key inside an inert function FAILS by name) with ``instanced`` (default :func:`instanced_at6`: 151's compare
    dispatch) as its instancing seam. THE INERT PROOF at each entrance the route enters the field by
    (o5_hallway.visit_entrances: 151 at 110, 153 at 328): every instancing op of the field in e0 t0, no inert entry
    instanced there; O5's shared-entry proof for an inert entry carrying ``shared_by``. THE LIVE SHARED PROOF (the
    critic's #3): for each ``live_shared`` entry, its ``RunSharedScript(n)`` sites are exactly ``callers`` and every
    caller's entry IS instanced at the entrance; an entry registered ``inert`` whose caller is instanced there FAILS by
    name; and every OTHER ``RunSharedScript`` site of the field lies in an entry not instanced at the entrance, or its
    shared entry holds no store. ``proof``: ``{field: {"entrances", "instanced", "outside_e0", "shared", "live",
    "others"}}``."""
    sites = sites or P.store_sites
    classify = classify or P.lvalue_class
    instanced = instanced or instanced_at6
    reg: dict = {}
    for name in ("writes", "ladder", "chain", "start_first", "error_path", "forbidden_sites", "dead"):
        for k in ([pred[name]] if name == "start_first" else pred.get(name) or ()):
            reg.setdefault((k["donor"], k["sid"], k["tag"], k["ip"], k["target"]), set()).add(name)
    inert, shared, live = {}, {}, {}
    for x in pred.get("inert") or ():
        inert.setdefault(int(x["donor"]), {})[int(x["sid"])] = x.get("tags", "*")
        if x.get("shared_by") is not None:
            shared.setdefault(int(x["donor"]), {})[int(x["sid"])] = sorted(int(s) for s in x["shared_by"])
    for x in pred.get("live_shared") or ():
        live.setdefault(int(x["donor"]), {})[int(x["sid"])] = sorted([int(v) for v in c] for c in x.get("callers")
                                                                    or ())
    try:
        ents = C5.visit_entrances(pred)
    except ValueError as err:
        return [str(err)], {}, {}
    bad, counts, proof = [], {}, {}
    for fid in fields:
        idx = stock(fid)
        c = counts.setdefault(fid, Counter())
        if idx is None:
            bad.append(f"{fid}: no stock script")
            continue
        route_ents = list(ents.get(fid) or ())
        callers = C5.shared_sites(idx)
        per = {}
        for ent in route_ents:
            try:
                per[ent] = instanced(idx, ent)
            except ValueError as err:
                per[ent] = None
                bad.append(f"{fid} at {ent}: {err}")

        def inst_at(entry: int) -> list:
            return [ent for ent, v in per.items() if v is not None and any(n == entry for _kind, n in v)]
        outside = [s for s in C4.instancing_sites(idx) if (s[0], s[1]) != (0, 0)]
        pf = {"entrances": route_ents, "instanced": {ent: sorted(v or ()) for ent, v in per.items()},
              "outside_e0": outside, "shared": {}, "live": {}, "others": {}}
        if fid in inert or fid in live:
            for s in outside:
                bad.append(f"{fid} e{s[0]} t{s[1]} ip{s[2]}: an instancing op outside Main_Init (Init{s[3].title()}"
                           f"({s[4]})): the inert proof needs every one in e0 t0")
            if not route_ents:
                bad.append(f"{fid}: no entrance the route enters it by: the inert proof cannot run")
        for sid in sorted(inert.get(fid) or {}):
            for ent in inst_at(sid):
                bad.append(f"inert entry {sid} of {fid} is instanced at entrance {ent} "
                           f"({sorted(k for k, n in per[ent] if n == sid)}): the proof fails")
            for e, t, ip in callers.get(sid, []):               # a caller that runs: the entry is no inert one
                for ent in inst_at(e):
                    bad.append(f"{fid} e{sid}: registered inert, run by RunSharedScript({sid}) at e{e} t{t} ip{ip} -- "
                               f"e{e} instanced at {ent}")
        for sid, by in sorted((shared.get(fid) or {}).items()):  # O5's shared-entry proof, kept
            runs = callers.get(sid, [])
            pf["shared"][sid] = runs
            for e, t, ip in [r for r in runs if r[0] not in (inert.get(fid) or {})]:
                bad.append(f"{fid} e{sid}: shared, run by RunSharedScript({sid}) at e{e} t{t} ip{ip} -- a function "
                           f"of no inert entry: the shared proof fails")
            if sorted({r[0] for r in runs}) != by:
                bad.append(f"{fid} e{sid}: registered shared_by {by}, but its callers are "
                           f"{sorted({r[0] for r in runs})}: the shared proof fails")
        for sid, want in sorted((live.get(fid) or {}).items()):  # THE LIVE SHARED PROOF
            runs = sorted(list(r) for r in callers.get(sid, []))
            pf["live"][sid] = runs
            if runs != want:
                bad.append(f"{fid} e{sid}: live_shared callers {want}, but RunSharedScript({sid}) runs at {runs}: the "
                           f"live proof fails")
            for e, t, ip in want:
                for ent in route_ents:
                    if ent not in inst_at(e):
                        bad.append(f"{fid} e{sid}: live_shared, its caller e{e} t{t} ip{ip} is not instanced at "
                                   f"entrance {ent}: the live proof fails")
            if sid in (inert.get(fid) or {}):
                bad.append(f"{fid} e{sid}: registered both live_shared and inert")
        for sid, runs in sorted(callers.items()):                 # every OTHER shared entry: not run, or storeless
            if sid in (live.get(fid) or {}):
                continue
            stores = _holds_store(idx, sid, sites)
            pf["others"][sid] = {"callers": runs, "stores": stores,
                                 "instanced": sorted({ent for e, _t, _ip in runs for ent in inst_at(e)})}
            for e, t, ip in runs:
                for ent in inst_at(e):
                    if stores:
                        bad.append(f"{fid} e{sid}: shared, run by RunSharedScript({sid}) at e{e} t{t} ip{ip} -- e{e} "
                                   f"instanced at {ent} -- and it holds a store: a live shared entry, unregistered")
        proof[fid] = pf
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


# ======================================================================== O6-REGIONS (pure but for the stock reader)
def regions_problems6(pred: dict, stock, *, instanced=None) -> tuple:
    """O6-REGIONS's reader (research/o6_design.md 6.1): O5's (o5_hallway.regions_problems) with ``instanced`` (default
    :func:`instanced_at6`) as its instancing seam -- 151 dispatches by an Int16[2] compare, which O4's walker refuses.
    ``(problems, roles Counter, gateway entries, hot-spots)``: every frozen region's points are the first SetRegion of
    its (donor, entry); ``exit``: scan_gateways has its (to, entrance, face_gate) AND a route entrance of its place
    instances it; ``dormant``: no route entrance instances it, its ``entrances`` exactly the place's route entrances;
    every gateway of a route place and every region a route entrance instances registered; no hot-spot."""
    from ff9mapkit.eventscan import scan_gateways
    instanced = instanced or instanced_at6
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
            if not any(g["to"] == reg.get("to") and g["entrance"] == reg.get("entrance")
                       and g["face_gate"] == reg.get("face_gate") for g in hit):
                bad.append(f"{key}: scan_gateways gives {[(g['to'], g['entrance'], g['face_gate']) for g in hit]}, "
                           f"frozen ({reg.get('to')}, {reg.get('entrance')}, {reg.get('face_gate')})")
            if not at:
                bad.append(f"{key}: an exit no route entrance of {donor} ({route_ents}) instances")
        elif role == "dormant":
            if sorted(int(x) for x in reg.get("entrances") or ()) != sorted(route_ents):
                bad.append(f"{key}: its entrances {reg.get('entrances')} are not the route's entrances of {donor} "
                           f"{route_ents}")
            if at:
                bad.append(f"{key}: dormant, but instanced at route entrance(s) {at}")
        else:
            bad.append(f"{key}: role {role!r} is not one of exit, dormant (O6 registers no scene)")
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
            bad.append(f"hot-spot {donor} e{sid} ({h['x']}, {h['z']}): in the bytes; O6 registers none")
    return bad, roles, ngw, nhot


# ======================================================================== O6-GOALS: the door's evidence (pure)
_ZTERM = re.compile(r"\.f\[2\] const\((\d+)\) B_GT\b")
_YTERM = re.compile(r"\.f\[1\] const\((\d+)\) B_GT\b")


def door_test(text: str):
    """A door's tag-2 test read off its pinned text (research/o6_design.md 1.3, 4.12): ``(ground_y, threshold_z)`` --
    ``obj(uid=250).f[1] const(65436) B_GT`` the ground half (PSX y > -100) and ``obj(uid=250).f[2] const(1333) B_GT`` the
    threshold (z > 1333), 2-byte constants signed; ``ground_y`` None when the test holds no y term. None for a test with
    no z term (e24's SYSVAR test, e25's ground-only test)."""
    z = _ZTERM.search(text or "")
    if z is None:
        return None
    y = _YTERM.search(text or "")
    return (None if y is None else A._s16(int(y.group(1)))), A._s16(int(z.group(1)))


def open_component(wm, start) -> list:
    """The start's OPEN component of a PlayerWalkmesh (O5's reading): every open triangle linked to the one under
    ``start`` through open neighbours, sorted."""
    raw = wm.mesh
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
    return sorted(comp)


def first_past(wm, pts: list, threshold: float, *, every: float = 5.0) -> dict | None:
    """O6-GOALS (c')'s reading: the route ``pts`` (``[(x, z)]``, its start first) sampled every ``every`` u on the open
    floor ``wm`` -- the FIRST sample whose z passes ``threshold`` (z > threshold): ``{"x", "z", "tri", "y", "leg",
    "along", "length"}`` with the first OPEN triangle under it and its interpolated PSX height (``tri``/``y`` None when
    no open triangle lies under it), or None (the route never passes it)."""
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
            if not z > threshold:
                continue
            tis = [ti for ti in raw.tris_at(x, z) if ti not in wm.closed]
            y = C5._tri_height(wv, raw.tris[tis[0]], x, z) if tis else None
            return {"x": round(x, 1), "z": round(z, 1), "tri": tis[0] if tis else None,
                    "y": None if y is None else round(y, 1), "leg": i + 1, "along": round(along + seg * k / n, 1),
                    "length": round(length)}
        along += seg
    return None


def _door_test_of(pred: dict, door: str):
    """The door's test from its PINNED texts (``route_pins``): the first tag-2 pin of the door's entry that
    :func:`door_test` reads, ``(text, (ground, threshold))``; ``(the first tag-2 pin's text or None, None)`` when no pin
    holds a z term."""
    donor, sid = int(door.split(".")[0]), int(door.split(".e")[1])
    pins = [p for p in pred.get("route_pins") or () if (p[0], p[1], p[2]) == (donor, sid, 2)]
    for p in pins:
        t = door_test(p[4])
        if t is not None:
            return p[4], t
    return (pins[0][4] if pins else None), None


def goals_extra6(pred: dict, walkmesh=None, *, stock=None, stale_ticks: int = STALE_TICKS,
                 run_u: int = RUN_U_PER_TICK) -> tuple:
    """O6-GOALS (c'), (c''), (d') and (e) (research/o6_design.md 6.1; the critic's #2; decision 6), for the table's
    WALK step (``walk.name``): ``(problems, lines)``.
      (c') THE FIRING LINE ON THE ROUTE: the ``start`` stands on an OPEN tri of the step's floor at ground height (PSX y
           > the door's ground bound); the planner's route (route_avoiding, the step's floor, round its ``avoid``; at
           its ``clearance`` when it carries one), sampled every 5 u, first passes the door's threshold at a point INSIDE
           the door's quad on an open tri at ground height.
      (c'') THE EVIDENCE'S THRESHOLD: the door's own test read from its pinned text (:func:`door_test`; no z term
           FAILS), and the step's ``until`` exactly one ``z_gt`` t with threshold - slack <= t <= threshold, the slack
           DERIVED (``stale_ticks`` x ``run_u``: 3 x 60 = 180 u) -- a ``walk`` carrying a typed ``stale_slack`` FAILS.
      (d') THE EVIDENCE'S SOUNDNESS: every OTHER registered exit of the place lies wholly outside the ``until`` and is
           in the step's ``avoid``; on the start's open component every tri with a vertex past the ``until`` is ground
           (every vertex at PSX y > the ground bound).
      (e) THE LANDING'S DOOR: the step's ``to`` is where the route's order goes next from its visit, and the place's
           only ``Field(<to>)`` site in an entry instanced at its route entrance is the door's.
    ``walkmesh(donor)`` is the raw mesh (default the install's); ``stock`` the stock scripts (default the install's)."""
    from ff9mapkit import extract
    from ff9mapkit.content import doorface, pathfind
    from ff9mapkit.eventscan import FIELD_OP
    walkmesh = walkmesh or extract.stock_walkmesh
    stock = stock or T.stock_script_source()
    walk = pred.get("walk") or {}
    slack = int(stale_ticks) * int(run_u)
    bad, lines, found = [], [], 0
    if "stale_slack" in walk:
        bad.append(f"(c''): the walk carries a typed stale_slack {walk['stale_slack']!r} -- the slack is DERIVED "
                   f"({stale_ticks} ticks x {run_u} u = {slack} u), never typed")
    door = walk.get("door")
    regions = pred.get("regions") or {}
    order = list(pred.get("visits") or pred["route"])
    ends = list(pred.get("end_fields") or [pred["end_field"]])
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
            if s.get("until") is None or s.get("start") is None or door not in regions:
                bad.append(f"{lab}: the walk's evidence needs an until, a start and a registered door ({door!r})")
                continue
            raw = walkmesh(c["donor"])
            wm = pathfind.PlayerWalkmesh(raw, closed=SD.closed_tris(pred, s, raw))
            wv = raw.world_verts()
            start = tuple(float(v) for v in s["start"])
            goal = tuple(float(v) for v in s["goal"])
            dpts = regions[door]["points"]
            text, test = _door_test_of(pred, door)
            ground, thr = test if test is not None else (None, None)
            gb = -100 if ground is None else ground
            # (c') the start, and the firing line on the planned route
            tis = [ti for ti in raw.tris_at(*start) if ti not in wm.closed]
            sy = C5._tri_height(wv, raw.tris[tis[0]], *start) if tis else None
            if not tis:
                bad.append(f"{lab} (c'): the start {start} stands on no open tri of the step's floor")
            elif not sy > gb:
                bad.append(f"{lab} (c'): the start {start} stands on tri {tis[0]} at PSX y {sy:.0f}, not ground (> {gb})")
            kw = {} if s.get("clearance") is None else {"clearance": float(s["clearance"])}
            route = pathfind.route_avoiding(wm, start, goal, SD.polys(pred, s.get("avoid")), leave_wall=True, **kw)
            first = None
            if route is None:
                bad.append(f"{lab} (c'): no route from {start} to {goal} avoiding {s.get('avoid')}")
            elif thr is not None:
                pts = [start] + [tuple(float(v) for v in p) for p in route]
                first = first_past(wm, pts, thr)
                if first is None:
                    bad.append(f"{lab} (c'): the route ({len(route)} legs) never passes z {thr}")
                elif first["tri"] is None or not first["y"] > gb:
                    bad.append(f"{lab} (c'): the route first passes z {thr} at ({first['x']:.0f}, {first['z']:.0f}) "
                               + ("on no open tri" if first["tri"] is None else
                                  f"on tri {first['tri']} at PSX y {first['y']:.0f}, not ground (> {gb})"))
                elif not doorface.region_contains(first["x"], first["z"], dpts):
                    bad.append(f"{lab} (c'): the route first passes z {thr} at ({first['x']:.0f}, {first['z']:.0f}), "
                               f"outside {door}")
            if tis and sy is not None and sy > gb and first is not None and first["tri"] is not None \
                    and first["y"] > gb and doorface.region_contains(first["x"], first["z"], dpts):
                lines.append(f"(c') the start ({start[0]:.0f}, {start[1]:.0f}) on open ground tri {tis[0]}; the route "
                             f"first past z {thr} at ({first['x']:.0f}, {first['z']:.0f}), tri {first['tri']} (PSX y "
                             f"{first['y']:.0f}), inside {door}" + (f" (clearance {kw['clearance']:g})" if kw else ""))
            # (c'') the evidence's threshold, the slack derived
            until = s["until"]
            if thr is None:
                bad.append(f"{lab} (c''): the door's test {text!r} holds no z term ({door})")
            elif set(until) != {"z_gt"}:
                bad.append(f"{lab} (c''): until {until} is not exactly one z_gt")
            else:
                t = float(until["z_gt"])
                if not thr - slack <= t <= thr:
                    bad.append(f"{lab} (c''): until z_gt {t:g} admits {thr - t:g} u of the door's non-firing band (z "
                               f"<= {thr}), over the derived slack {slack} ({stale_ticks} ticks x {run_u} u)"
                               if t < thr - slack else f"{lab} (c''): until z_gt {t:g} is stricter than the door's own "
                                                       f"z > {thr}")
                elif "stale_slack" not in walk:
                    lines.append(f"(c'') the door's test (ground > {gb}, z > {thr}) and until z_gt {t:g}: {thr - t:g} u "
                                 f"of its non-firing band admitted (<= {slack}: {stale_ticks} ticks x {run_u} u, "
                                 f"derived)")
            # (d') every other exit outside the evidence and avoided; no open floor past it off the ground
            others = [(k, r) for k, r in regions.items() if str(k).split(".", 1)[0] == str(c["donor"])
                      and r.get("role") == "exit" and k != door]
            inside = [k for k, r in others if any(SD.until_ok(until, px, pz) for px, pz in r["points"])]
            unavoided = [k for k, _r in others if k not in (s.get("avoid") or ())]
            comp = open_component(wm, start)
            past = [ti for ti in comp if any(SD.until_ok(until, wv[v][0], wv[v][2]) for v in raw.tris[ti].vtx)]
            off = [ti for ti in past if any(not wv[v][1] > gb for v in raw.tris[ti].vtx)]
            if inside:
                bad.append(f"{lab} (d'): the registered exit(s) {sorted(inside)} reach where until {until} holds: a loss "
                           f"there would read as the door's")
            if unavoided:
                bad.append(f"{lab} (d'): the registered exit(s) {sorted(unavoided)} are not in the step's avoid")
            if off:
                bad.append(f"{lab} (d'): open tri(s) {off[:6]} of the start's component lie past until {until} off the "
                           f"ground (a vertex at PSX y <= {gb}), where the door cannot fire")
            if not (inside or unavoided or off):
                lines.append(f"(d') {', '.join(sorted(k for k, _r in others))} wholly outside the until and avoided; the "
                             f"start's open component ({len(comp)} tris): its {len(past)} tris past "
                             f"{'z ' + str(until['z_gt']) if set(until) == {'z_gt'} else until} all ground")
            # (e) the landing's door
            to = s.get("to")
            v = c.get("visit")
            if v is not None and 1 <= int(v) <= len(order):
                nxt = [order[int(v)]] if int(v) < len(order) else ends
            else:
                nxt = sorted({order[j + 1] if j + 1 < len(order) else e for j, p in enumerate(order) if p == c["donor"]
                              for e in ([None] if j + 1 < len(order) else ends)} - {None})
            if to not in nxt:
                bad.append(f"{lab} (e): its to {to} is not where the route's order goes next from {c['donor']} "
                           f"({nxt})")
                continue
            idx = stock(c["donor"])
            if idx is None:
                bad.append(f"{lab} (e): no stock script for {c['donor']}")
                continue
            try:
                ents = C5.visit_entrances(pred).get(c["donor"]) or []
            except ValueError as err:
                bad.append(f"{lab} (e): {err}")
                continue
            sites = []
            for e_ in idx.eb.entries:
                if e_.empty:
                    continue
                for f in e_.funcs:
                    for ins in idx.eb.instrs(f):
                        if ins.op == FIELD_OP and ins.imm(0) == to:
                            sites.append((e_.index, f.tag, ins.off - e_.abs_start))
            live = []
            for e_, tg, ip in sites:
                try:
                    if any(any(n == e_ for _k, n in instanced_at6(idx, ent)) for ent in ents):
                        live.append((e_, tg, ip))
                except ValueError as err:
                    bad.append(f"{lab} (e): {err}")
            dsid = int(door.split(".e")[1])
            if [x[0] for x in live] != [dsid] or live[0][1] != 2:
                bad.append(f"{lab} (e): {c['donor']}'s live Field({to}) at {ents} is "
                           + (", ".join(f"e{a} t{b} ip{d}" for a, b, d in live) or "nowhere")
                           + f", not the door's ({door}) alone")
            else:
                lines.append(f"(e) to {to}: {c['donor']}'s live Field({to}) at {', '.join(map(str, ents))} is "
                             f"e{live[0][0]} t{live[0][1]} ip{live[0][2]} alone")
    if not found:
        bad.append(f"no table step is the walk {walk.get('name')!r}")
    return bad, lines


# ======================================================================== O6-PATTERN's reading (pure)
pattern_of6 = C5.pattern_of


def _tuples(xs) -> list:
    return [tuple(x) for x in xs or ()]


def pattern_diff6(got: dict, pat: dict) -> list:
    """O6-PATTERN's verdict on one run's :func:`o5_hallway.pattern_of` against the frozen ``pattern``, pure (research/
    o6_design.md 4.18, 5.3): ``[problem]`` -- (a) the ``c`` multiset (here none); (b) each FLOATING row present EXACTLY
    ONCE in its visit, after its ``after`` tuple and before its ``before`` tuple (the bytes' window; its place among the
    rows between is not compared, and ``measured`` is never read), then -- the floating rows taken out -- each visit's
    sequence equal to the frozen one in order (a visit more or fewer, or the first differing tuple)."""
    bad = []
    want_c = Counter(_tuples(pat.get("counts")))
    got_c = Counter(got["counts"])
    if got_c != want_c:
        miss, extra = sorted((want_c - got_c).elements()), sorted((got_c - want_c).elements())
        bad.append("(a) the c rows differ: " + "; ".join(x for x in (
            f"missing {miss[:2]}" if miss else "", f"extra {extra[:2]}" if extra else "") if x))
    got_v = [list(v) for v in got["visits"]]
    for fl in pat.get("floating") or ():
        v, t = int(fl["visit"]) - 1, tuple(fl["tuple"])
        a, b = tuple(fl["after"]), tuple(fl["before"])
        if v >= len(got_v):
            bad.append(f"(b) no visit {v + 1} for the floating row {t}")
            continue
        seq = got_v[v]
        at = [i for i, x in enumerate(seq) if x == t]
        if len(at) != 1:
            bad.append(f"(b) the floating row {t} is in visit {v + 1} {len(at)} time(s), want exactly once")
        else:
            ia = next((i for i, x in enumerate(seq) if x == a), None)
            ib = next((i for i, x in enumerate(seq) if x == b), None)
            if ia is None or ib is None or not ia < at[0] < ib:
                bad.append(f"(b) the floating row {t} at #{at[0] + 1} of visit {v + 1}, outside its window (after {a} "
                           f"at #{None if ia is None else ia + 1}, before {b} at #{None if ib is None else ib + 1})")
        got_v[v] = [x for x in seq if x != t]
    want_v = [_tuples(v) for v in pat.get("visits") or ()]
    if got_v != want_v:
        if len(got_v) != len(want_v):
            bad.append(f"(b) {len(got_v)} visit(s) of emitted rows, want {len(want_v)}: "
                       + " / ".join(f"{v[0][0]}x{len(v)}" for v in got_v if v))
        else:
            i = next(i for i, (x, y) in enumerate(zip(got_v, want_v)) if x != y)
            x, y = got_v[i], want_v[i]
            j = next((j for j, (p, q) in enumerate(zip(x, y)) if p != q), min(len(x), len(y)))
            bad.append(f"(b) visit {i + 1}'s emitted rows differ at #{j + 1}: got {x[j] if j < len(x) else 'nothing'}, "
                       f"want {y[j] if j < len(y) else 'nothing'} ({len(x)} vs {len(y)} rows, the floating rows out)")
    return bad


def float_window(pat: dict) -> list:
    """``[(lo, hi)]`` per floating row: the 0-based indexes its position may take among its visit's emitted rows (the
    row in), from the frozen sequence -- after its ``after`` tuple, at or before the slot its ``before`` tuple holds
    (research/o6_design.md 4.18; the freeze refuses a ``measured`` index outside it)."""
    out = []
    for fl in pat.get("floating") or ():
        seq = _tuples((pat.get("visits") or [])[int(fl["visit"]) - 1])
        a = seq.index(tuple(fl["after"])) if tuple(fl["after"]) in seq else None
        b = seq.index(tuple(fl["before"])) if tuple(fl["before"]) in seq else None
        out.append(None if a is None or b is None else (a + 1, b))
    return out


def measured_indexes(measured) -> list:
    """A floating row's ``measured`` index(es) as a list (an int, or a list of ints one per R-DOOR run), or [] when it
    names none."""
    if not isinstance(measured, dict):
        return []
    idx = measured.get("index")
    vals = idx if isinstance(idx, list) else [idx]
    return [v for v in vals if isinstance(v, int) and not isinstance(v, bool)]


def _ranges(ns) -> str:
    """``[56, 57, 58, 175, 176]`` -> ``"56-58, 175-176"``."""
    out, ns = [], sorted(set(ns))
    i = 0
    while i < len(ns):
        j = i
        while j + 1 < len(ns) and ns[j + 1] == ns[j] + 1:
            j += 1
        out.append(str(ns[i]) if i == j else f"{ns[i]}-{ns[j]}")
        i = j + 1
    return ", ".join(out)


# ======================================================================== the run's own rows (pure)
def naming_rows(log: list, pred: dict) -> tuple:
    """``(named rows, name_on_page rows)`` of a run's driver log: the registration's ``named`` rows (its place) and
    every ``name_on_page`` row."""
    nm = pred.get("name") or {}
    named = [x for x in log or () if x.get("k") == "named" and x.get("donor") == nm.get("place")]
    pages = [x for x in log or () if x.get("k") == "name_on_page"]
    return named, pages


def on_page_lines(row: dict, pred: dict) -> list:
    """O6-NAMING (b)'s re-reading of one ``name_on_page`` row, pure: per listed window ``(mes, ok, why)`` -- a frozen
    entry names it (its ``raw_holds`` in the window's raw), it is PARSED (no tag in its text) and its line -- RE-READ
    from its text, never the row's own ``line`` -- is the frozen ``text`` exactly."""
    reg = (pred.get("naming") or [{}])[0]
    page = reg.get("on_page") or {}
    tag = page.get("tag") or "[STNR]"
    out = []
    for w in row.get("windows") or ():
        raw, text = str(w.get("raw") or ""), str(w.get("text") or "")
        entry = next((e for e in page.get("windows") or () if e["raw_holds"] in raw), None)
        if entry is None:
            out.append((w.get("mes"), False, "no frozen window names it"))
            continue
        if tag in text:
            out.append((w.get("mes"), False, f"unparsed (its text holds {tag})"))
            continue
        lines = text.split("\n")
        line = lines[entry["line"]] if entry["line"] < len(lines) else ""
        if line != entry["text"]:
            out.append((w.get("mes"), False, f"line {entry['line']} renders {line!r}, frozen {entry['text']!r}"))
            continue
        out.append((w.get("mes"), True, f"mes {entry['mes']} line {entry['line']} {line!r}"))
    return out


def _span(target: str) -> set:
    """The bytes a target occupies (``Global.UInt16[19]``: {19, 20}; ``Global.Bit[3855]``: {481})."""
    width, index = target.split(".", 1)[1].rstrip("]").split("[")
    index = int(index)
    if width in T.BIT_WIDTHS:
        return {index >> 3}
    size = {"Byte": 1, "SByte": 1, "Int16": 2, "UInt16": 2, "Int24": 3, "UInt24": 3, "Int32": 4, "UInt32": 4}.get(width,
                                                                                                                    1)
    return set(range(index, index + size))


def _row_span(x) -> set:
    if x.k == "r":
        return {x.byte}
    if x.width in T.BIT_WIDTHS:
        return {x.byte}
    size = {"Byte": 1, "SByte": 1, "Int16": 2, "UInt16": 2, "Int24": 3, "UInt24": 3, "Int32": 4, "UInt32": 4}.get(
        x.width, 1)
    return set(range(x.byte, x.byte + size))


def start_dependent_rows(rows: list, pred: dict, members: dict, *, pre=(), side: str = "S") -> list:
    """O6-START-DEPENDENT's reading of one run, pure (research/o6_design.md 4.5, 5.3; the claim critic's #3): per
    ``start_dependent`` key ``{"key", "rows": [(old, new, line)], "class", "why"}`` -- exactly ONE raw ``w`` row at its
    site (place, sid, tag, ip, target) with ``old`` the prior's value (newgame0: 0) and ``new`` the key's value is
    ``ok``; else each run's deviation CLASSIFIED on the fields: ``FINDING`` (old the prior, new another value: the store
    wrote another value); ``EXPLAINED`` (old not the prior, an EARLIER row of the run -- any ``w`` or ``r`` row after the
    arm, ``pre`` included -- touches the target's bytes: named); ``START DRIFT`` on ``side`` (nothing earlier explains
    it: the instrument's start, never the fork's) -- with "the <after.run> continuation" only when (old, new) is
    (``after.old``, ``after.value``) exactly; ``count`` when not exactly one row."""
    out = []
    every = list(pre) + list(rows)
    for k in pred.get("start_dependent") or ():
        hits = [x for x in rows if x.k == "w" and place(x.fld, members) == k["donor"]
                and (x.sid, x.tag, x.ip, x.target) == (k["sid"], k["tag"], k["ip"], k["target"])]
        prior = 0 if k.get("prior") == "newgame0" else None
        after = k.get("after") or {}
        rec = {"key": k, "rows": [(x.old, x.new, x.line) for x in hits], "class": "ok", "why": ""}
        if len(hits) != 1:
            rec.update({"class": "count", "why": f"{len(hits)} rows at the site, want exactly one"})
        else:
            x = hits[0]
            if x.old == prior and x.new == k["value"]:
                pass
            elif x.old == prior:
                rec.update({"class": "FINDING", "why": f"old {x.old} (the prior), new {x.new}, registered "
                                                       f"{k['value']}: the store itself wrote another value"})
            else:
                span = _span(k["target"])
                earlier = [y for y in every if y.line < x.line and y.k in ("w", "r") and _row_span(y) & span
                           and y is not x]
                if earlier:
                    y = earlier[-1]
                    what = (f"{y.k} {A._row_text(y)}" if y.k == "w" else f"r {y.fld} byte {y.byte} {y.old}->{y.new}")
                    rec.update({"class": "EXPLAINED", "why": f"old {x.old}, new {x.new}: explained by line {y.line} "
                                                             f"{what}"})
                else:
                    cont = (x.old, x.new) == (after.get("old"), after.get("value"))
                    rec.update({"class": "START DRIFT",
                                "why": f"old {x.old}, new {x.new}, nothing earlier explains it: START DRIFT on {side} -- "
                                       f"the instrument's start (New Game, field 70 or the warp), never the fork's"
                                       + (f"; the {after.get('run')} continuation" if cont else "")})
        out.append(rec)
    return out


def start_dependent_line(k: dict, vals: dict, olds: list) -> str:
    """5.4's start-dependence line for one key (O2's 4.5 report, PORTED): every span and number from the predictions,
    never a literal -- ``<target> <op> at <donor> e<sid> t<tag> ip<ip>: S [values], F [values] (registered <value>, old
    [olds]); after the <after.run> routes as driven it would write <after.value> (from <after.old>, <after.source>) --
    <after.why>``."""
    a = k.get("after") or {}
    return (f"{k['target']} {k['op']} at {k['donor']} e{k['sid']} t{k['tag']} ip{k['ip']}: S {vals.get('S', [])}, F "
            f"{vals.get('F', [])} (registered {k['value']}, old {olds}); after the {a.get('run')} routes as driven it "
            f"would write {a.get('value')} (from {a.get('old')}, {a.get('source')}) -- {a.get('why')}")


def scope_start(pred: dict) -> str:
    """5.4's start-dependence scope line, its span RENDERED from the keys' ``after.run`` (the claim critic's #4)."""
    sd = pred.get("start_dependent") or []
    runs = sorted({(k.get("after") or {}).get("run") for k in sd} - {None})
    span = runs[0] if len(runs) == 1 else "/".join(map(str, runs)) or "a true"
    parts = []
    for k in sd:
        a = k.get("after") or {}
        parts.append(f"{k['donor']} e{k['sid']} t{k['tag']} ip{k['ip']} {k['target'].split('.', 1)[1]} {k['op']} "
                     f"{'8' if k['value'] == 8 else k['value']} writes {k['value']} here and {a.get('value')} after the "
                     f"{a.get('run')} routes as driven (from {a.get('old')}, read from the archives at design time)")
    return (f"values: {len(sd)} keys' VALUES depend on this start (a raw warp into 151@110 at SC 1190 from New Game), "
            f"the same on both sides: " + "; ".join(parts) + " -- 153's guard ip2180 reads bit 3, clear in both, so its "
            "branch is the same. OLD/SAME only (the value equal): 151 ip57 (Int16[9] 643 here, -1 after), ip119 "
            "(Byte[13] 1 vs 0), ip315 (Byte[8] same-value 125 here, a change 0 -> 125 after), 153 e32 t1 ip1656 "
            "(UInt16[21] old 0 vs 1), ip1741 (Byte[303] same-value here, a change 1 -> 0 after), ip2248 (Byte[18] a "
            "change here, same-value after). The EMITTED ROW PATTERN: each run is a fresh epoch, so 151's start row ip22, "
            "153@328's six prologue rows and 154's end row ip26 are emitted here, but would be suppressed c counts in a "
            f"single-epoch chained O1-O6 run (O4 and O5 emitted those sites first): O6-PATTERN's frozen sequences, "
            f"LANDING (b)'s re-entry row, the end cut and every row count are this start's -- never reuse them against "
            f"a chained trace. Not covered: party data (the rebuild's SetPartyReserve / RemoveParty / PARTYADD), gil, "
            f"Map variables, the camera, field 70's override state, and the untouched targets' values after the {span} "
            f"routes")


# ======================================================================== a trace, summarised (end PLACES)
def trace_summary(rows: list, pred: dict, *, side: str = "S", start_place: int | None = None, end_fields=None,
                  stock=None, scripts=None, log: list | None = None) -> dict:
    """One trace, summarised for a reader (research/o6_design.md 7.2; the rehearsal report and the dry run): O5's shape
    -- cut at its start row and at its first row in an END PLACE (``end_fields``, a stage's raw ids, turned into places
    through the members on F) -- with O6's crossings (151 ip932 -> the next field row; 153 ip203 -> the cut), the e15
    row (its frame, its index among visit 2's emitted rows, its gap in frames to ip971's row, its sid/uid/tag/ip/add
    as written) and the start-dependent rows (old, new)."""
    out = C5.trace_summary(rows, pred, side=side, start_place=start_place, end_fields=end_fields, stock=stock,
                           scripts=scripts, log=log)
    members = members_of(pred) if side == "F" else {}
    sp = start_place if start_place is not None else place(pred["start"][side], members)
    ends = list(end_fields) if end_fields is not None else ST.side_ends(pred, side)
    places = sorted({place(f, members) for f in ends})
    kept, _at, pre = cut_at_start(rows, sp, members)
    kept, end = cut_at_end(kept, places, members)
    lnd = pred.get("landing") or {}
    crossings = {}
    for name in ("exit151", "exit153"):
        ex = lnd.get(name)
        if not ex:
            continue
        i = next((j for j, x in enumerate(kept) if x.k == "w" and x.m == T.FIELD_MODE
                  and place(x.fld, members) == ex["place"]
                  and (x.sid, x.tag, x.ip, x.target, x.new) == (ex["sid"], ex["tag"], ex["ip"], ex["target"],
                                                                ex["value"])), None)
        if i is None:
            continue
        nxt = next((x for x in kept[i + 1:] if x.k == "w" and x.m == T.FIELD_MODE), None)
        cut_row = next((x for x in rows if x.line == end), None) if end is not None else None
        crossings[name] = {"exit": A._row_text(kept[i]), "next": None if nxt is None else A._row_text(nxt),
                           "cut": None if cut_row is None or nxt is not None else
                           (A._row_text(cut_row) if cut_row.k == "w" else f"{cut_row.fld} byte {cut_row.byte}")}
    out["crossings"] = crossings
    fl = ((pred.get("pattern") or {}).get("floating") or [None])[0]
    e15 = None
    if fl is not None:
        visits = out["pattern"]["visits"]
        v = int(fl["visit"]) - 1
        t = list(fl["tuple"])
        hit = next((x for x in kept if x.k == "w" and x.m == T.FIELD_MODE and place(x.fld, members) == t[0]
                    and (x.sid, x.tag, x.target, x.new) == (t[1], t[2], t[4], t[5])), None)
        r971 = next((x for x in kept if x.k == "w" and place(x.fld, members) == t[0] and (x.sid, x.tag, x.ip) == (32, 1,
                                                                                                                   971)),
                    None)
        idx = next((i for i, x in enumerate(visits[v]) if x == t), None) if v < len(visits) else None
        win = float_window(pred.get("pattern") or {})[0]
        e15 = None if hit is None else {
            "frame": hit.f, "fld": hit.fld, "sid": hit.sid, "uid": hit.uid, "tag": hit.tag, "ip": hit.ip, "add": hit.add,
            "index": idx, "window": None if win is None else list(win),
            "inside": None if idx is None or win is None else win[0] <= idx <= win[1],
            "frames_to_971": None if r971 is None else r971.f - hit.f}
    out["e15"] = e15
    out["start_dependent"] = [{"site": f"{k['key']['donor']} e{k['key']['sid']} t{k['key']['tag']} ip{k['key']['ip']}",
                               "rows": [[o, n] for o, n, _l in k["rows"]], "class": k["class"]}
                              for k in start_dependent_rows(kept, pred, members, pre=pre, side=side)]
    return out


# ======================================================================== P-NAME: the default name's sources (read-only)
def character_default_name_lines(text) -> list:
    """``[(id, lang, name, line)]``: every ``CharacterDefaultName`` line of one DictionaryPatch.txt as the engine reads
    it (DataPatchers.PatchDictionaries, DataPatchers.cs:249-257 and :584-603): the file's lines (File.ReadAllLines),
    each split on single spaces; ``entry[0]`` exactly "CharacterDefaultName" with at least four entries and ``entry[1]``
    an Int32 (Int32.TryParse) -- its language ``entry[2]`` (DefaultNamesByLang's key, which CharacterDefaultNames reads
    at Localization.CurrentSymbol), its name the rest re-joined by single spaces. Any other line is skipped, as the
    engine skips it."""
    out = []
    for line in re.split(r"\r\n|\r|\n", text or ""):
        entry = line.split(" ")
        if len(entry) < 4 or entry[0] != "CharacterDefaultName":
            continue
        cid = P._int32(entry[1])
        if cid is not None:
            out.append((cid, entry[2], " ".join(entry[3:]), line))
    return out


def p_name(game, roots, *, char: int = 3, lang: str = "US", default: str = "Steiner") -> tuple:
    """P-NAME (the review, research/o6_design.md 11.7 #1): ``(ok, detail)`` -- the name New Game gives character
    ``char`` and the naming screen pre-fills (ff9play.cs:141, NameSettingUI.cs:151: FF9TextTool.CharacterDefaultName)
    is the engine's built-in ``default``, the one the page witness's frozen lines render (``ON_PAGE_WINDOWS``). The
    stack can patch it two ways, each read the engine's way:
      (a) the TEXT IMPORTER: [Import] Enabled 1 AND Text 1 in the merged Memoria.ini -- the root's, then each stacked
          folder's over it, the first folder's winning (P-SETTINGS' reading, o3_prima_vista.install_settings) --
          runs it (Configuration.Import.Text = Enabled && Text), character names among what it imports, over any
          DictionaryPatch line (DataPatchers.cs:587-588): FAILS, the import path unread; a raw value that is not the
          engine's 0 or 1 FAILS too (IniValue.ParseValue keeps an earlier value: never guessed). Unset reads 0 (the
          section's defaults);
      (b) a ``CharacterDefaultName <char> <lang> <name>`` line in a stacked folder's DictionaryPatch.txt
          (:func:`character_default_name_lines`; every mod folder's is applied, DataPatchers.Initialize) in the
          session's language ``lang`` whose name is not ``default``: FAILS naming the folder and the line. A line naming
          ``default`` itself, another character's or another language's passes, listed.
    A patched default would make every run's 199 render the patched name: the page witness VOIDs each as V13 -- never
    covered, the cause read as typed input. P-NAME refuses it before the session; P-LAUNCH then proves the launch read
    these very files (each older than the launch)."""
    imp = P.install_settings(game, roots, {"Import": ["Enabled", "Text"]})["Import"]
    raw = {k: imp.get(k) for k in ("Enabled", "Text")}
    bad = [f"(a) [Import] {k} = {v!r} is not the engine's 0 or 1 (it keeps an earlier value): unread"
           for k, v in raw.items() if v is not None and v not in ("0", "1")]
    if raw["Enabled"] == "1" and raw["Text"] == "1":
        bad.append("(a) [Import] Enabled 1 and Text 1: the text importer runs -- character names among it, over any "
                   "DictionaryPatch line -- from a path P-NAME does not read")
    lines = []
    for r in roots:
        try:
            text = (Path(r) / "DictionaryPatch.txt").read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        for cid, lg, nm, ln in character_default_name_lines(text):
            lines.append(f"{Path(r).name} {cid} {lg} {nm!r}")
            if cid == int(char) and lg == lang and nm != default:
                bad.append(f"(b) {Path(r).name}/DictionaryPatch.txt '{ln.strip()}' patches character {char}'s default "
                           f"name to {nm!r} in {lang}: the screen pre-fills it, and every [STNR] page renders it")
    if bad:
        return False, "; ".join(bad[:4])
    return True, (f"character {char}'s default name is the engine's {default!r} in {lang}: [Import] Enabled "
                  f"{raw['Enabled'] or '0 (unset)'}, Text {raw['Text'] or '0 (unset)'} (the importer off); no stacked "
                  f"DictionaryPatch.txt patches it (CharacterDefaultName lines: {'; '.join(lines) or 'none'})")


# ======================================================================== O6 on the shared engine
class O6Segment(C5.O5Segment):
    """O6 on O5's segment (research/o6_design.md 1.3): its constants and check texts, the draft predictions, the offline
    checks (O6-BUILD with the route members' pins, O6-KEYS with the start-dependent keys' after values, the route pins
    and route_mes, O6-TEXT strict on block 3, O6-CENSUS with 151's compare dispatch and e15 LIVE at 328, O6-REGIONS,
    O6-GOALS with the door's evidence), the preflight extras (O5's, with P-NAME after P-SETTINGS) and in-game
    capabilities (O5's over 151/153/154), the drive with its input witness (O4's), A-START (151 is visited once) and
    A-NAMING, the all-run checks (FORBIDDEN, VOID-ASYM (a)-(d) over [place, sc, visit] cells), the core checks (START,
    NO-SC, CHAIN, RESIDUE, WRITES exact, NULL, STABLE, LANDING (a)-(e), NAMING (a)-(b), WALK (a)-(b), PATTERN (a)-(b)
    with the floating e15 row, START-DEPENDENT, MASKED, STATE, JOIN) and O6's report. The session loop, the cuts, the
    digest, the comparison and the verdict are the shared engine's."""

    tag = "O6"
    doc = _MODULE_DOC
    predictions = PREDICTIONS
    manifest = MANIFEST
    session_file = SESSION_FILE
    report_file = REPORT_FILE
    chain_dir = CHAIN_DIR
    build_dir = BUILD_DIR
    accept_us_build = False               # O4's build: every member's other languages are its own donor's
    recovery = 4600
    end_session_warps = True              # S5: a last run stopped mid-walk or at the screen must not leave the game there
    #: 4.5: the span every start-dependent key's ``after.run`` must equal (O7's subclass overrides it).
    AFTER_RUN = AFTER_RUN
    #: 4.12: the evidence's slack, derived (never typed).
    RUN_U_PER_TICK = RUN_U_PER_TICK
    STALE_TICKS = STALE_TICKS
    core_ids = ("START", "NO-SC", "CHAIN", "RESIDUE", "WRITES", "NULL", "STABLE", "LANDING", "NAMING", "WALK",
                "PATTERN", "START-DEPENDENT", "MASKED", "STATE", "JOIN")
    titles = {
        "P-CAP": "P-CAP: the engine advertises the story trace at proto 1",
        "P-OBJECTS": "P-OBJECTS: the engine publishes the field's objects (s89): the walk plans with npcs off -- the "
                     "corridor soldiers e13/e14 and the knights e16/e17 publish, none is planned round",
        "P-LANG": "P-LANG: the running game's text is English(US), the language the keys, joins and text were checked "
                  "in (a US session)",
        "P-DONOR-LOG": "P-DONOR-LOG: this launch's Memoria.log shows the patchers ran and logged no ForkDonorPatch "
                       "collision for 151, 153 or 154",
        "P-LAUNCH": "P-LAUNCH: every stacked patch file, Memoria.ini and the engine DLLs are older than this launch, "
                    "and the DLLs are the pinned engine",
        "P-MANIFEST": "P-MANIFEST: the frozen members are the deployed chain's (o6_forks.json: O4's, deployed)",
        "P-DEPLOY": "P-DEPLOY: every member registered once under its name, and mapped once to its donor",
        "P-EB": "P-EB: every member's live .eb (7 languages) is the offline-checked build's (O4's)",
        "P-FLOOR": "P-FLOOR: every member's deployed walkmesh is its donor's (member(153)'s is the north door walk's "
                   "floor)",
        "P-STOCK": "P-STOCK: no mod folder overrides stock 151, 153 or 154",
        "P-TEXT3": "P-TEXT (block 3): every mod folder's text block 3 is each language's stock asset (strict)",
        "P-RECOVERY": "P-RECOVERY: the recovery field 4600 is registered in a mod folder",
        "P-DONOR": "P-DONOR: each of 151, 153 and 154 is forked by exactly one ForkDonorPatch row in the stack, its "
                   "member's",
        "P-SETTINGS": "P-SETTINGS: the battle, cheat, hack (DisableNameChoice 0), control and graphics settings are the "
                      "frozen ones (O4's; Memoria.ini read the engine's way)",
        "P-NAME": "P-NAME: Steiner's default name is the engine's 'Steiner' -- no stacked DictionaryPatch.txt "
                  "CharacterDefaultName line patches it in US, and [Import] Text is off (the name the screen pre-fills "
                  "and the page witness's frozen lines render)",
        "P-PAD": "P-PAD: no XInput pad reads non-neutral (AlwaysCaptureGamepad = 1 reads a pad even unfocused)",
        "P-OVERRIDE": "P-OVERRIDE: field 70's New-Game override is the pinned one, shipped by one folder",
        "P-ENGINE": "P-ENGINE: the live x64 and x86 Assembly-CSharp.dll are the pinned engine",
        "BUILD": "O6-BUILD: every member's .eb, in all 7 languages, is its donor's in that language with only in-chain "
                 "Field() literals remapped; per language, the route members (151, 153, 154) differ from their donors "
                 "in exactly their in-chain Field() operands",
        "KEYS": "O6-KEYS: every registered key -- chain, writes, start-dependent keys (their after values computed), "
                "error path, forbidden and dead sites, start_first -- is a store of its variable at its ip in the "
                "donor's stock bytes, its op in the statement, its value computed; the 74 route pins and route_mes as "
                "pinned, the on-page lines computed",
        "TEXT": "O6-TEXT: the build's text block 3 is each language's stock asset, read by its resource path -- STRICT: "
                "another language's copy fails",
        "CENSUS": "O6-CENSUS: every gEventGlobal store site of 151 and 153 is registered (writes, chain, masked, "
                  "start_first, error path, forbidden, dead) or lies in an inert function proven not instanced at the "
                  "route's entrance (151 by its Int16[2] compare), and the shared script e15 is LIVE at 328 (its caller "
                  "instanced)",
        "REGIONS": "O6-REGIONS: every frozen region is the stock bytes' own, each role proven by instancing at the "
                   "route's entrances, every gateway and every instanced region of 151 and 153 registered, no hot-spot",
        "GOALS": "O6-GOALS: the north door step runs on its floor from its start to its goal; the planned route first "
                 "passes the door's line inside its quad on open ground; the until within the door's threshold less "
                 "the derived slack; every other exit outside the evidence and avoided, no open floor past it off the "
                 "ground; the landing's door the place's only live Field(to)",
        "FROZEN": "O6-FROZEN: the predictions are the file the session recorded, unchanged",
        "COVER": "O6-COVER: at least {min_covered} covered runs a side",
        "FORBIDDEN": "O6-FORBIDDEN: no run carries a forbidden write its own driver log does not explain",
        "VOID-ASYM": "O6-VOID-ASYM: no game-caused VOID class on one side only, no side VOID in one class in every run, "
                     "no run VOID in a finding class (V19), and no game-observed V17 cause on one side only -- every "
                     "cell [place, sc, visit]",
        "START": "O6-START: every covered run starts at 151's Main_Init after only the warp's three residue rows, and "
                 "151 takes its ambient branch from the warp's Byte[13] 1",
        "NO-SC": "O6-NO-SC: no row touches bytes 0-1 (SC) after the start: SC holds 1190 throughout",
        "CHAIN": "O6-CHAIN: bytes 2-3 (FieldEntrance) carry exactly the chain, in order, each from the last",
        "RESIDUE": "O6-RESIDUE: no unmasked residue after the start beyond the registered",
        "WRITES": "O6-WRITES: every covered run's story keys are EXACTLY the registered writes and chain",
        "NULL": "O6-NULL: STOCK ONLY and FORK ONLY are empty",
        "STABLE": "O6-STABLE: no key is written in some runs of a side and not others",
        "LANDING": "O6-LANDING: every row ran in its place's own field, 153 loaded by 151's Field(153), 153 the last "
                   "place with the north door's chain row last, the end cut 154's first row at the side's own end "
                   "field, and no fork run left its members",
        "NAMING": "O6-NAMING: Steiner named once in 151 before ip610's store, and the first parsed [STNR] page after it "
                  "renders the default name 'Steiner' (the driver judged it; re-checked here)",
        "WALK": "O6-WALK: the north door -- one done step whose loss was read in 153 past the evidence and whose landing "
                "is none or the side's end field, at most one interruption and one failed attempt, none in a door -- "
                "wrote nothing (THE PAIRED-WALK LAW)",
        "PATTERN": "O6-PATTERN: the sink's emitted row pattern EXACTLY -- each visit's emitted rows in order, the shared "
                   "script's e15 row once inside the bytes' window (after e32 t0 ip727, before e32 t1 ip1656), no c row",
        "START-DEPENDENT": "O6-START-DEPENDENT: each start-dependent key written once, from its prior to its value on "
                           "both sides -- any deviation classified per run (FINDING / EXPLAINED / START DRIFT)",
        "MASKED": "O6-MASKED: the story-noise regions written are the same on both sides",
        "STATE": "O6-STATE: the state handed to 154 is the same: each target's emitted write history in order, and the "
                 "end state read live (Byte[8] included: nothing at 315 races the read)",
        "JOIN": "O6-JOIN: every script row joins a store in the bytes its field ran (the e15 row included)",
        "THROW": "O6-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
    }

    # -- the predictions --------------------------------------------------------------------------------------
    def draft(self) -> dict:
        return draft_predictions(Path(self.chain_dir) / "campaign.toml")

    def freeze_problems(self, pred: dict, *, live_engine=None) -> list:
        """7.3's refusals, pure but for the live engine read (``live_engine``, default the live DLLs'): ``[problem]``
        -- no ``witness`` (or one its strict reader refuses); a naming registration without ``on_page`` or without its
        ``windows`` (or one ``naming_of`` refuses); a table step carrying a rehearsal overlay (``walk_stop_z``,
        ``walk_stop_hold``, ``walk_stop_x``); a ``walk`` carrying a typed ``stale_slack``; ``side_ends`` failing
        :func:`segment_trace.side_ends_of`; a non-empty ``battles``; a ``start_dependent`` key without ``after`` or
        without ``after.source``; ``pattern.floating`` with ``measured`` null, or with a measured index outside its
        window (after e32 t0 ip727, before e32 t1 ip1656); an empty ``rehearsals``; an ``engine`` that is not the live
        DLLs'."""
        bad = []
        try:
            if SD.witness_of(pred) is None:
                bad.append("no witness: the naming screen keeps what a keyboard types (4.13)")
        except ValueError as err:
            bad.append(str(err))
        try:
            regs = SD.naming_of(pred)
            if not regs:
                bad.append("no naming registration: Steiner's naming is rule 4's (decision 4)")
            for r in regs:
                if not r.get("on_page") or not (r["on_page"] or {}).get("windows"):
                    bad.append(f"the naming registration {r.get('donor')} carries no on_page windows: the name's "
                               f"only witness is the page (S16)")
        except ValueError as err:
            bad.append(str(err))
        for c in pred.get("table") or ():
            for s in c.get("steps") or ():
                over = sorted(set(s) & REHEARSAL_OVERLAYS)
                if over:
                    bad.append(f"the table step {s.get('name')!r} carries a rehearsal overlay {over}")
        if "stale_slack" in (pred.get("walk") or {}):
            bad.append("the walk carries a typed stale_slack: the evidence's slack is DERIVED (4.12)")
        try:
            if ST.side_ends_of(pred) is None:
                bad.append("no side_ends: O6's F side ends in member(154)")
        except ValueError as err:
            bad.append(str(err))
        if pred.get("battles"):
            bad.append(f"{len(pred['battles'])} battle row(s): O6's registry is empty (any battle is V10)")
        for k in pred.get("start_dependent") or ():
            a = k.get("after")
            if not isinstance(a, dict):
                bad.append(f"the start-dependent key {A.label(k)} carries no after")
            elif not a.get("source"):
                bad.append(f"the start-dependent key {A.label(k)}'s after carries no source (after.old is READ)")
        pat = pred.get("pattern") or {}
        wins = float_window(pat)
        for fl, win in zip(pat.get("floating") or (), wins):
            idx = measured_indexes(fl.get("measured"))
            if fl.get("measured") is None or not idx:
                bad.append(f"the floating row {fl.get('tuple')}: measured is null -- R-DOOR's measured position "
                           f"(its index among visit {fl.get('visit')}'s emitted rows) goes there (F4)")
            elif win is None:
                bad.append(f"the floating row {fl.get('tuple')}: its window's tuples are not in its visit")
            else:
                out = [i for i in idx if not win[0] <= i <= win[1]]
                if out:
                    bad.append(f"the floating row {fl.get('tuple')}: measured index {out} outside its window "
                               f"{list(win)} (after e32 t0 ip727, before e32 t1 ip1656): an order the bytes cannot "
                               f"produce")
        if not pred.get("rehearsals"):
            bad.append("no rehearsals: the freeze reads the lead's in-game rehearsal runs (7.3), none named")
        live = live_engine if live_engine is not None else C4.engine_shas(GAME)
        eng = pred.get("engine") or {}
        if any(eng.get(a) != live.get(a) for a in ("x64", "x86")):
            bad.append(f"the engine {str(eng.get('x64'))[:12]} is not the live DLLs' {str(live.get('x64'))[:12]}: the "
                       f"rehearsals ran another engine")
        return bad

    def freeze(self, path=None, *, live_engine=None) -> str:
        """The freeze, once (research/o6_design.md 1.3, 7.3): :meth:`freeze_problems` empty before anything is
        written, then the base's -- LF, sorted keys, never over an existing file."""
        pred = self.draft()
        bad = self.freeze_problems(pred, live_engine=live_engine)
        if bad:
            raise SystemExit("!! the draft is not freezable: " + "; ".join(bad))
        return ST.Segment.freeze(self, path)

    # -- offline ------------------------------------------------------------------------------------------------
    def offline_extra(self, pred: dict, build=None) -> list:
        stock = self.stock_source()
        return [self.text_check(pred, build), self.census_check(pred, stock), self.regions_check(pred, stock),
                self.goals_check(pred)]

    def build_check(self, pred: dict, build=None, stock_lang=None) -> tuple:
        """O6-BUILD (6.1): the base rule (every member's .eb, every language its own donor's with only in-chain Field()
        literals remapped), then O5's ROUTE MEMBERS' PINS per language (the same three members), then the chain's route
        members (derived) in O6's order."""
        stock_lang = stock_lang or ST.stock_lang()
        ok, what, detail = ST.Segment.build_check(self, pred, build, stock_lang)
        pok, pdetail = self.build_pins(pred, build, stock_lang)
        if not (ok and pok):
            return False, what, "; ".join(d for good, d in ((ok, detail), (pok, pdetail)) if not good)
        members = members_of(pred)
        line = route_members_line(members) if all(d in members.values() for d in ROUTE_DONORS) else ""
        return True, what, f"{detail}; {pdetail}" + (f"; {line}" if line else "")

    @staticmethod
    def _word(n: int) -> str:
        return ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")[n] \
            if 0 <= n <= 10 else str(n)

    def keys_check(self, pred: dict, stock, lists=None, *, mes=None, texts=None) -> tuple:
        """O6-KEYS (6.1): (a) O2's machinery on a filtered copy -- the chain, the writes, the START-DEPENDENT keys,
        ``forbidden_sites`` + ``error_path`` + ``dead``, ``start_first``; no ladder, no noise -- every key a store of its
        variable at its ip, its op in the statement, a compound value computed from its prior; then ``start_music``
        exactly one writes key; every start-dependent key's ``after.value`` COMPUTED from ``after.old`` and its
        statement, its ``after.run`` the class's :attr:`AFTER_RUN` (never a literal) and its ``after.source`` present
        (``after.old`` is read, not computed: 4.5); each ``live_shared`` entry's store a writes key; (b) THE ROUTE PINS
        and route_mes (:meth:`route_pins_check`; ``mes`` and ``texts`` its seams)."""
        filtered = {**pred, "ladder": [], "noise": [],
                    "forbidden_sites": list(pred["forbidden_sites"]) + list(pred["error_path"]) + list(pred["dead"])}
        ok, _what, detail = A.O2Segment.keys_check(self, filtered, stock)
        bad = [] if ok else [detail]
        sm = pred.get("start_music")
        if sm is not None:
            same = [k for k in pred["writes"] if all(k[f] == sm[f] for f in ("donor", "m", "src", "sid", "tag", "ip",
                                                                               "off", "target", "value", "op"))]
            if len(same) != 1:
                bad.append(f"start_music ({sm['donor']} e{sm['sid']} t{sm['tag']} ip{sm['ip']} {sm['target']} := "
                           f"{sm['value']}) is {len(same)} writes keys, not one")
        afters = []
        for k in pred.get("start_dependent") or ():
            a = k.get("after") or {}
            lab = A.label(k)
            if a.get("run") != self.AFTER_RUN:
                bad.append(f"{lab}: after.run {a.get('run')!r} is not the class's AFTER_RUN {self.AFTER_RUN!r}")
            if not a.get("source"):
                bad.append(f"{lab}: after carries no source (after.old is READ, never computed: say from where)")
            got = self._after_value(k, stock)
            if got is None:
                bad.append(f"{lab}: after.value cannot be computed from after.old {a.get('old')!r} and the statement")
            elif got != a.get("value"):
                bad.append(f"{lab}: after.value {a.get('value')} -- the bytes give {got} from after.old {a.get('old')}")
            else:
                afters.append(got)
        writes = {(k["donor"], k["sid"], k["tag"], k["ip"]) for k in pred["writes"]}
        for x in pred.get("live_shared") or ():
            if not any((d, s) == (x["donor"], x["sid"]) for d, s, _t, _i in writes):
                bad.append(f"live_shared {x['donor']} e{x['sid']}: its store is no writes key")
        pok, pdetail = self.route_pins_check(pred, stock, mes=mes, texts=texts)
        if not pok:
            bad.append(pdetail)
        if bad:
            return False, self.title("KEYS"), "; ".join(bad)[:1400]
        m = re.match(r"(\d+) sites \((\d+) keys\), every op in its statement, (\d+) compound values", detail)
        nsites, nkeys, ncomp = (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (0, 0, 0)
        sd = pred.get("start_dependent") or []
        n_or = sum(1 for k in pred["writes"] if k.get("op") in ("|=", "&="))
        n_pp = sum(1 for k in pred["writes"] if k.get("op") == "++")
        n_dpp = sum(1 for k in pred.get("dead") or () if k.get("op") == "++")
        runs = sorted({(k.get("after") or {}).get("run") for k in sd})
        w = self._word
        head = (f"{nkeys} keys over {nsites} distinct sites (the {w(len(sd))} start-dependent keys repeat "
                f"{w(nkeys - nsites)} writes), every op in its statement, {ncomp} compound values computed from their "
                f"priors (the writes' {w(n_or)} |= and {w(n_pp)} ++, the {w(len(sd))} start-dependent repeats, the "
                f"{w(n_dpp)} dead ++ stores), none masked but start_first (boot_scratch: O6-START reads it raw); "
                f"start_music one writes key; the after values {' and '.join(map(str, afters))} computed, after.run "
                f"{'/'.join(map(str, runs))} (AFTER_RUN), their olds read (after.source)")
        return True, self.title("KEYS"), f"{head}; {pdetail}"

    @staticmethod
    def _after_value(k: dict, stock):
        """A start-dependent key's ``after.value`` computed from ``after.old`` and the statement at its site (``|=`` /
        ``&=`` a constant, ``++``, ``:=`` a constant), or None."""
        a = k.get("after") or {}
        old = a.get("old")
        if not isinstance(old, int) or isinstance(old, bool):
            return None
        width, index = k["target"].split(".", 1)[1].rstrip("]").split("[")
        bit = int(index) if width in T.BIT_WIDTHS else -1
        row = T.Row(k="w", f=0, p=0, m=k["m"], fld=k["donor"], don=k["donor"], sc=0, src=k["src"], sid=k["sid"], uid=0,
                    lvl=0, ip=k["ip"], tag=k["tag"], add=0, byte=int(index) >> 3 if bit >= 0 else int(index),
                    width=width, bit=bit, old=0, new=k["value"], same=0)
        idx = stock(k["donor"])
        j = idx.join(row) if idx is not None else None
        if j is None or j.status != "store":
            return None
        text, anchor = j.text or "", re.escape(k["target"])
        op = k.get("op")
        if op in ("|=", "&="):
            m = re.search(anchor + r" const\((-?\d+)\) " + ("B_OR_LET" if op == "|=" else "B_AND_LET"), text)
            if m is None:
                return None
            c = A.O2Segment._as_width(width, int(m.group(1)))
            return (old | c) if op == "|=" else (old & c)
        if op == "++":
            return old + 1 if re.search(anchor + r" B_POST_PLUS\b", text) else None
        if op == ":=":
            m = re.search(anchor + r" const\((-?\d+)\) B_LET\b", text)
            return None if m is None else A.O2Segment._as_width(width, int(m.group(1)))
        return None

    @staticmethod
    def _strip_tags(text: str) -> str:
        return re.sub(r"\[[^\]]*\]", "", text)

    @staticmethod
    def _all_texts(idx) -> list:
        """Every instruction text of a script, in every function: ``[(sid, tag, ip, text)]``."""
        out = []
        for e in idx.eb.entries:
            if e.empty:
                continue
            for f in e.funcs:
                out += [(e.index, f.tag, ip, t) for ip, _rel, t in A.O2Segment._items(idx, e.index, f.tag)]
        return out

    def route_pins_check(self, pred: dict, stock, *, mes=None, texts=None) -> tuple:
        """O6-KEYS (b), THE ROUTE PINS (4.16): ``(ok, detail)`` -- every pin's instruction text EXACTLY the stock US
        script's; the door's place (153) holds NO store to ``Map.Bit[144]`` anywhere (e23 t2 ip80's test then holds:
        ip95's op_22(1) is skipped, the fade 25 ticks) -- ``texts`` (``[(sid, tag, ip, text)]`` of that script, a seam)
        replaces the scan; then ``route_mes`` on block 3's US source (``mes``, ``{mes id: source}``, a seam): mes 198
        holds the naming's marker and no [STNR]; 199 and 200 hold their sources; no window the start place's script
        opens before the first on-page mes holds [STNR]; every ``naming[0].on_page.windows`` entry's ``raw_holds`` in its
        source and its ``text`` the COMPUTED line ([STNR] the default, every tag removed); the stop page's mes holds the
        stop page."""
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
        door = (pred.get("walk") or {}).get("donor", 153)
        if texts is None:
            idx = stock(door)
            texts = self._all_texts(idx) if idx is not None else []
        var = "Map.Bit[144]"
        refs = [(s, t, ip, x) for s, t, ip, x in texts if var in x]
        stores = [(s, t, ip, x) for s, t, ip, x in refs if x.startswith("SET({" + var + " ") and re.search(r"\bB_\w*LET\b",
                                                                                                        x)]
        tests = [r for r in refs if re.search(re.escape(var) + r" const\(-?\d+\) B_(EQ|NE)\b", r[3])]
        if stores:
            s, t, ip, x = stores[0]
            bad.append(f"{door} stores {var} ({len(stores)} store(s), first e{s} t{t} ip{ip} {x!r}): e23 t2 ip80's test "
                       f"may fail, and the fade would not be 25 ticks")
        rm = pred.get("route_mes") or {}
        if mes is None:
            from ff9mapkit import dialogue
            body = A.stock_text_assets(int(rm.get("block", TEXT_BLOCK)))[pred.get("lang", SESSION_LANG)]
            body = body.decode("utf-8", errors="replace") if isinstance(body, (bytes, bytearray)) else str(body)
            mes = {i: x.text for i, x in dialogue.parse_mes(body).items()}
        nm = pred.get("name") or {}
        reg = (pred.get("naming") or [{}])[0]
        page = reg.get("on_page") or {}
        tag = page.get("tag") or "[STNR]"
        bf = rm.get("before") or {}
        src = str(mes.get(bf.get("mes")) or "")
        if str(bf.get("holds")) not in src:
            bad.append(f"mes {bf.get('mes')} (before the naming) does not hold the marker {bf.get('holds')!r}")
        if tag in src:
            bad.append(f"mes {bf.get('mes')} (before the naming) holds {tag}")
        if (nm.get("before") or {}).get("marker") != bf.get("holds"):
            bad.append(f"name.before.marker {(nm.get('before') or {}).get('marker')!r} is not route_mes's "
                       f"{bf.get('holds')!r}")
        for op in rm.get("on_page") or ():
            if str(op.get("holds")) not in str(mes.get(op.get("mes")) or ""):
                bad.append(f"mes {op.get('mes')} does not hold its source {op.get('holds')!r}")
        first_on = min((int(op["mes"]) for op in rm.get("on_page") or ()), default=None)
        sp_place = pred["start"]["S"] if isinstance(pred.get("start"), dict) else None
        sidx = stock(sp_place) if sp_place is not None else None
        opened = sorted({int(m.group(1)) for _s, _t, _ip, x in (self._all_texts(sidx) if sidx is not None else [])
                         for m in [re.match(r"^Window\w*\(\d+, \d+, (\d+)\)$", x)] if m})
        earlier = [m for m in opened if first_on is not None and m < first_on]
        tagged = [m for m in earlier if tag in str(mes.get(m) or "")]
        if tagged:
            bad.append(f"mes {tagged} -- windows {sp_place}'s script opens before {first_on} -- hold {tag}")
        default = nm.get("default", "Steiner")
        for w in page.get("windows") or ():
            s = str(mes.get(w.get("mes")) or "")
            if w.get("raw_holds") not in s:
                bad.append(f"naming window mes {w.get('mes')}: its source does not hold raw_holds {w.get('raw_holds')!r}")
                continue
            lines = self._strip_tags(s.replace(tag, default)).split("\n")
            line = lines[w["line"]] if 0 <= w["line"] < len(lines) else None
            if line != w.get("text"):
                bad.append(f"naming window mes {w.get('mes')}: text {w.get('text')!r} is not the computed line {line!r}")
        stop = rm.get("stop_page") or {}
        for p in pred.get("stop_pages") or ():
            if p["match"] not in str(mes.get(stop.get("mes")) or ""):
                bad.append(f"mes {stop.get('mes')} does not hold the stop page {p['match']!r}")
        rng = _ranges(earlier) if earlier else "none"
        return (not bad, "; ".join(bad[:6]) if bad else
                f"{n} route pins equal; {door} never writes {var} ({len(refs)} references, all tests)"
                + ("" if len(tests) == len(refs) else f" [{len(refs) - len(tests)} not a const test]")
                + f"; mes {bf.get('mes')} holds the marker, "
                + " and ".join(str(op.get("mes")) for op in rm.get("on_page") or ())
                + f" their sources, no earlier {sp_place} window {tag} ({len(earlier)} windows its script opens before "
                  f"{first_on}: {rng}), the on-page lines computed, mes {stop.get('mes')} the stop page")

    def census_check(self, pred: dict, stock, *, sites=None, classify=None, instanced=None) -> tuple:
        """O6-CENSUS (6.1): :func:`store_census6` over the route's stock fields -- every site classified, the inert
        functions proven not instanced at the route's entrance of their field, e15 LIVE at 328 (its caller instanced),
        every other shared entry not run there or storeless -- or each failure named."""
        fields = list(pred["route"])
        bad, counts, proof = store_census6(fields, stock, pred, sites=sites, classify=classify, instanced=instanced)
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
        parts, lives, others = [], [], []
        for f in fields:
            x = sorted((i for i in pred.get("inert") or () if int(i["donor"]) == f), key=lambda i: int(i["sid"]))
            ents = (proof.get(f) or {}).get("entrances") or []
            if x:
                sids = ", ".join("e" + str(i["sid"]) for i in x)
                parts.append(f"{f} {sids} not instanced at {' or '.join(str(e) for e in ents)}")
            for sid, runs in sorted(((proof.get(f) or {}).get("live") or {}).items()):
                lives.append(f"{f} e{sid} (run by " + ", ".join(f"e{e} t{t} ip{ip}" for e, t, ip in runs)
                             + f", e{'/e'.join(str(e) for e in sorted({r[0] for r in runs}))} instanced at "
                               f"{' or '.join(str(e) for e in ents)})")
            oth = (proof.get(f) or {}).get("others") or {}
            if oth:
                sids = sorted(oth)
                callers = sorted({e for v in oth.values() for e, _t, _ip in v["callers"]})
                quiet = all(not v["stores"] for v in oth.values())
                unrun = all(not v["instanced"] for v in oth.values())
                others.append(f"{f}'s other shared entries {', '.join(map(str, sids))} "
                              + ("hold no store" if quiet else "run nowhere at the route's entrance")
                              + (f", their callers in {'/'.join(f'e{e}' for e in callers)} (not instanced at "
                                 f"{' or '.join(str(e) for e in ents)})" if unrun else ""))
        return (True, self.title("CENSUS"),
                ", ".join(f"{f}: {tot[f]}" for f in fields) + f" store sites -- all classified ({cols}); {unres} "
                f"unresolved; inert " + ", ".join(parts)
                + ("; LIVE shared " + "; ".join(lives) if lives else "")
                + ("; " + "; ".join(others) if others else ""))

    def regions_check(self, pred: dict, stock, *, instanced=None) -> tuple:
        """O6-REGIONS (6.1): :func:`regions_problems6`."""
        bad, roles, ngw, nhot = regions_problems6(pred, stock, instanced=instanced)
        n = sum(roles.values())
        return (not bad, self.title("REGIONS"),
                "; ".join(bad[:6]) if bad else
                f"{n} regions (" + ", ".join(f"{roles[r]} {r}" for r in ("exit", "scene", "dormant") if roles[r])
                + f"), {nhot} hot-spots, {ngw} gateway entries all registered")

    def goals_check(self, pred: dict, walkmesh=None, *, stock=None) -> tuple:
        """O6-GOALS (6.1): O2's ``goals_check`` on the table (the step runnable, ``visits`` a walk on the route from the
        start place, the goal on the floor >= 80 from a wall with the 33 triangles closed, its ``until`` true at the
        goal, a route from ``start`` round the ``avoid`` set), then :func:`goals_extra6` -- (c'), (c''), (d'), (e) -- with
        the class's derived slack. O5's (c)/(d) are withdrawn (critique #2: e23 lies inside the until by design)."""
        ok, what, detail = A.O2Segment.goals_check(self, pred, walkmesh)
        bad, lines = goals_extra6(pred, walkmesh, stock=stock, stale_ticks=self.STALE_TICKS, run_u=self.RUN_U_PER_TICK)
        if not ok or bad:
            return False, self.title("GOALS"), "; ".join(([detail] if not ok else []) + bad)[:1400]
        return True, self.title("GOALS"), detail + "; " + "; ".join(lines)

    # -- the live install (read-only) ---------------------------------------------------------------------------
    def preflight_extra(self, pred: dict, roots: list, *, manifest=None, pads=..., live_engine=None, game=None,
                        stock_text=None) -> list:
        """O5's extras -- P-TEXT (block 3, STRICT), P-RECOVERY, P-DONOR (151, 153 and 154), P-SETTINGS, P-PAD,
        P-OVERRIDE, P-ENGINE -- with :func:`p_name` right after P-SETTINGS (the review, research/o6_design.md 11.7 #1):
        P-SETTINGS pins the screen (``DisableNameChoice`` 0), P-NAME the name it pre-fills, for the predictions'
        ``name`` (its ``char`` and ``default``) in the session's language. The seams are O5's; ``game`` is also the
        install whose Memoria.ini P-NAME reads."""
        out = super().preflight_extra(pred, roots, manifest=manifest, pads=pads, live_engine=live_engine, game=game,
                                      stock_text=stock_text)
        nm = pred.get("name") or {}
        ok, detail = p_name(Path(game) if game is not None else GAME, roots, char=int(nm.get("char", 3)),
                            lang=str(pred.get("lang", SESSION_LANG)).upper(), default=str(nm.get("default", "Steiner")))
        at = next((i + 1 for i, (_ok, w, _d) in enumerate(out) if w == self.title("P-SETTINGS")), len(out))
        out.insert(at, (ok, self.title("P-NAME"), detail))
        return out

    # -- the session --------------------------------------------------------------------------------------------
    def capabilities(self, g, *, pads=..., engine=None, live_engine=None) -> list:
        """O5's -- P-CAP, P-OBJECTS, P-LANG, P-DONOR-LOG, P-LAUNCH with the engine, P-PAD -- with P-DONOR-LOG over O6's
        ROUTE_DONORS (151, 153, 154: O5's set, in O6's order). ``pads``, ``engine`` and ``live_engine`` are seams for
        the fake."""
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
        """The shared reading (O5's: the stock scripts kept), with each A-NAMING reason given its cell -- ``[151, 1190,
        1]``, the naming's place, SC and visit (5.1) -- and each run's ``stopped`` reason (S15) on the run."""
        runs = super().read_session(run_dir, pred, session=session, stock=stock)
        cell = self.naming_cell(pred)
        for r in runs:
            for v in r.get("void") or ():
                if str(v.get("why") or "").startswith(A_NAMING) and v.get("cell") is None:
                    v["cell"] = cell
        return runs

    @staticmethod
    def naming_cell(pred: dict) -> list:
        nm = pred.get("name") or {}
        order = list(pred.get("visits") or pred.get("route") or [])
        visit = order.index(nm.get("place")) + 1 if nm.get("place") in order else None
        return [nm.get("place"), pred.get("scenario"), visit]

    def why_void(self, rec: dict, r: dict, pred: dict) -> list:
        """O5's reasons (O3's A-NOSTART, A-FORBIDDEN, A-MISMATCH, A-START -- 151 is visited once, so an error-path row
        of 151 is always the start's; 153's error path is the game's V5 at [153, 1190, 2] -- A-NOEND, the cut row),
        then A-NAMING (5.1; the claim critic's #2): a ``named`` row of the registration whose ``before`` holds no raw
        with ``name.before.marker`` ("And, Captain") -- the ring held no sample of 198 before the screen, or a screen
        came before 198 -- class V13, by the driver (its cell [151, 1190, 1] given by :meth:`read_session`): the run
        UNCOVERED, re-run, never a failed check."""
        out = super().why_void(rec, r, pred)
        nm = pred.get("name") or {}
        marker = (nm.get("before") or {}).get("marker")
        if marker:
            for x in r.get("log") or ():
                if x.get("k") == "named" and x.get("donor") == nm.get("place") and "before" in x:
                    raws = ((x.get("before") or {}).get("raws")) or []
                    if not any(marker in str(raw) for raw in raws):
                        out.append((f"{A_NAMING}: the named row's before (frame "
                                    f"{(x.get('before') or {}).get('frame')}) lists no raw holding {marker!r}: the ring "
                                    f"held no sample of mes {(nm.get('before') or {}).get('mes')} before the screen, or "
                                    f"the screen came before it -- the instrument's miss", "V13", "driver"))
                    break
        return out

    # -- the checks ---------------------------------------------------------------------------------------------
    def core_checks(self, runs: list, cov: dict, pred: dict) -> list:
        covered = cov["S"] + cov["F"]
        c = self.comparison(cov, pred)
        return [self.start_check(covered, pred), self.no_sc_check(covered, pred),
                self.span_check("CHAIN", covered, pred, "entrance_bytes", "chain", pred["entrance"]),
                self.residue_check(covered, pred), self.writes_check(covered, pred), self.null_check(c, pred),
                self.stable_check(c, pred), self.landing_check(cov, pred), self.naming_check(covered, pred),
                self.walk_check(covered, pred), self.pattern_check(covered, pred),
                self.start_dependent_check(covered, pred), self.masked_check(cov, pred),
                self.state_check(covered, pred), self.join_check(cov)]

    def landing_check(self, cov: dict, pred: dict) -> tuple:
        """O6-LANDING (5.3), over every covered run, each clause named in the detail:
          (a) every field-mode ``w``/``c`` row ran in its place's own field (member(place) on F, the place on S), and
              none stands in a place off ``route_places`` [151, 153];
          (b) the crossing, on field-mode ``w`` rows at their places' own fields: the run holds ``landing.exit151``
              (151 e2 t1 ip932) and the next field-mode ``w`` row after it is ``landing.enter153`` (153 e0 t0 ip22, a
              new site: 153 loaded by 151's Field(153)); no row of place 151 after it;
          (c) the last field-mode ``w`` row before the end cut is ``landing.exit153`` (153 e23 t2 ip203), by PLACE, and
              the run's ``end`` log row names the side's end field (154 on S, member(154) on F);
          (d) THE END PER SIDE: the end cut (``cut_row``) is a raw ``w`` row that is ``landing.end_row`` (154 e0 t0
              ip26) at ``fld`` the side's end field;
          (e) every F digest records no seam and no seam key (the chain is closed from member(151) to member(154))."""
        L = pred["landing"]
        ex151, en153, ex153, lend = L["exit151"], L["enter153"], L["exit153"], L["end_row"]
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
            i = next((j for j, x in enumerate(ws) if is_at(x, ex151, members) and x.fld == fld_of(ex151["place"])), None)
            if i is None:
                bad.append(f"{lab} (b): no {where(ex151)} row at fld {fld_of(ex151['place'])}")
            else:
                nxt = next((x for x in ws[i + 1:] if x.m == fm), None)
                if nxt is None or not (is_at(nxt, en153, members) and nxt.fld == fld_of(en153["place"])):
                    bad.append(f"{lab} (b): the next field row after {ex151['place']} ip{ex151['ip']} is "
                               f"{A._row_text(nxt) if nxt is not None else 'none'}, not {where(en153)} at fld "
                               f"{fld_of(en153['place'])}")
            k = next((j for j, x in enumerate(ws) if is_at(x, en153, members)), None)
            back = None if k is None else next((x for x in ws[k + 1:] if x.m == fm
                                                and place(x.fld, members) == ex151["place"]), None)
            if back is not None:
                bad.append(f"{lab} (b): line {back.line} {A._row_text(back)}: place {ex151['place']} written again "
                           f"after 153 loaded")
            fws = [x for x in ws if x.m == fm]
            last = fws[-1] if fws else None
            if last is None or not is_at(last, ex153, members):
                bad.append(f"{lab} (c): the last field row before the end cut is "
                           f"{A._row_text(last) if last is not None else 'none'}, not {where(ex153)}")
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
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) every field row in its place's own field; (b) 151 "
                                      f"ip{ex151['ip']} -> 153 e0 t0 ip{en153['ip']}, 151 never written again; (c) 153 "
                                      f"ip{ex153['ip']} last, the end row the side's own; (d) the cut at 154 e0 t0 "
                                      f"ip{lend['ip']} (S {ST.side_ends(pred, 'S')}, F {ST.side_ends(pred, 'F')}); (e) "
                                      f"no seam")

    def naming_check(self, covered: list, pred: dict) -> tuple:
        """O6-NAMING (5.3; decision 4; the claim critic's #2 -- the driver ENFORCES, this RE-CHECKS), every covered run
        of both sides, each clause named:
          (a) exactly ONE ``named`` row of the registration: its ``donor`` 151 and ``field`` the side's 151 field; its
              ``frame`` before the frame ``f`` of the run's ``name.store`` row (151 e3 t1 ip610 Global.Byte[6], the raw
              ``w`` row) -- the screen before the store its closing releases; no such row fails (a): its anchor is gone;
          (b) exactly ONE ``name_on_page`` row, after the ``named`` row (its frame greater), in the same field, with
              ``verdict`` "ok" and at least one window -- every listed window one a frozen entry names, PARSED, its line
              RE-READ from its text the frozen ``text`` exactly (:func:`on_page_lines`)."""
        nm = pred.get("name") or {}
        store = nm.get("store") or {}
        bad = []
        for r in covered:
            lab = f"{r['side']}#{r['i']}"
            members = members_of(pred) if r["side"] == "F" else {}
            inv = {d: f for f, d in sorted(members.items(), reverse=True)}
            fld151 = inv.get(nm.get("place"), nm.get("place")) if members else nm.get("place")
            named, pages = naming_rows(r.get("log") or [], pred)
            anchor = [x for x in r["rows"] if x.k == "w" and place(x.fld, members) == store.get("place")
                      and (x.sid, x.tag, x.ip, x.target) == (store.get("sid"), store.get("tag"), store.get("ip"),
                                                             store.get("target"))]
            probs = []
            if len(named) != 1:
                probs.append(f"{len(named)} named row(s)")
            else:
                n = named[0]
                if (n.get("donor"), n.get("field")) != (nm.get("place"), fld151):
                    probs.append(f"the named row in {n.get('field')} (place {n.get('donor')}), not {fld151}")
                if not anchor:
                    probs.append(f"no {store.get('place')} e{store.get('sid')} t{store.get('tag')} ip{store.get('ip')} "
                                 f"{store.get('target')} row: its anchor is missing")
                elif n.get("frame") is None or not n["frame"] < anchor[0].f:
                    probs.append(f"the named row's frame {n.get('frame')} is not before ip{store.get('ip')}'s row "
                                 f"(frame {anchor[0].f})")
            if probs:
                bad.append(f"{lab} (a): " + "; ".join(probs))
            probs = []
            if len(pages) != 1:
                probs.append(f"{len(pages)} name_on_page row(s)")
            else:
                p = pages[0]
                if len(named) == 1 and (p.get("frame") is None or named[0].get("frame") is None
                                        or not p["frame"] > named[0]["frame"]):
                    probs.append(f"the page row's frame {p.get('frame')} is not after the named row's "
                                 f"{named[0].get('frame') if named else None}")
                if p.get("field") != fld151:
                    probs.append(f"the page row in {p.get('field')}, not the naming's field {fld151}")
                if p.get("verdict") != "ok":
                    probs.append(f"its verdict {p.get('verdict')!r}")
                lines = on_page_lines(p, pred)
                if not lines:
                    probs.append("no window listed")
                probs += [f"window {mes}: {why}" for mes, ok, why in lines if not ok]
            if probs:
                bad.append(f"{lab} (b): " + "; ".join(probs))
        windows = ((pred.get("naming") or [{}])[0].get("on_page") or {}).get("windows") or []
        return (not bad, self.title("NAMING"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) one named row in 151's field before ip"
                                      f"{store.get('ip')}'s row; (b) one name_on_page row after it, verdict ok, every "
                                      f"window frozen, parsed, its line the default's ("
                                      + ", ".join(f"{w['mes']} {w['text']!r}" for w in windows) + ")")

    def walk_check(self, covered: list, pred: dict) -> tuple:
        """O6-WALK (5.3; S14's landing; THE PAIRED-WALK LAW), over every covered run, each clause named:
          (a) exactly one ``step`` row of the door step (``walk.name``, ``walk.donor``, ``walk.visit``) with ``outcome``
              "done", its ``lost`` sample satisfying the step's ``until`` (re-checked) AND read in the side's own field
              of the walk's place (``lost.field``), its ``landed`` None or the side's end field (path A or B); before it
              at most ``interrupts`` ``interrupted`` rows, each with no ``door``, and at most ``attempts`` - 1
              ``failed`` rows, each with ``landed`` None and no ``door``; nothing after it;
          (b) no ``w`` row (any target, masked or not) whose frame lies inside a walk window (O5's
              :func:`o5_hallway.walk_windows`)."""
        w = pred["walk"]
        steps = [step for c in pred.get("table") or () for step in c["steps"] if step.get("name") == w["name"]]
        step = SD.step_of(pred, steps[0]) if steps else {}
        bad = []
        for r in covered:
            lab = f"{r['side']}#{r['i']}"
            members = members_of(pred) if r["side"] == "F" else {}
            inv = {d: f for f, d in sorted(members.items(), reverse=True)}
            fld = inv.get(w["donor"], w["donor"]) if members else w["donor"]
            ends = ST.side_ends(pred, r["side"])
            rows = C5.walk_rows(r.get("log") or [], pred)
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
                if lost.get("field") != fld:
                    probs.append(f"the done row's loss was read in {lost.get('field')}, not the walk's field {fld}")
                if d.get("landed") is not None and d.get("landed") not in ends:
                    probs.append(f"the done row landed in {d.get('landed')}, not the side's end field {ends}")
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
            for lo, hi, what in C5.walk_windows(rows):
                hit = next((x for x in r["rows"] if x.k == "w" and lo <= x.f <= hi), None)
                if hit is not None:
                    bad.append(f"{lab} (b): line {hit.line} {A._row_text(hit)} at frame {hit.f}, inside the walk "
                               f"window {what} [{lo}, {hi}]")
                    break
        return (not bad, self.title("WALK"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) the north door done past {step.get('until')}, its loss "
                                      f"read in 153's field, its landing none or the end field (S14), no door; (b) no "
                                      f"row inside a walk window")

    def pattern_check(self, covered: list, pred: dict) -> tuple:
        """O6-PATTERN (5.3; critique #5): the suppression model's prediction, EXACT, every covered run --
        :func:`o5_hallway.pattern_of` over the joined script rows of the route places before the cut, against
        ``pattern`` (:func:`pattern_diff6`): (a) the ``c`` multiset (none), (b) each visit's emitted sequence with the
        floating e15 row once inside the bytes' window. ``measured`` is never read here (report-only)."""
        pat = pred["pattern"]
        stock = self._stock_src()
        bad = []
        for r in covered:
            members = members_of(pred) if r["side"] == "F" else {}
            got = C5.pattern_of(r["rows"], pred, members, C5.stock_join(stock, members))
            bad += [f"{r['side']}#{r['i']} {p}" for p in pattern_diff6(got, pat)]
        nv = [len(v) for v in pat["visits"]]
        nf = len(pat.get("floating") or ())
        return (not bad, self.title("PATTERN"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) {len(pat['counts'])} counted stores, as frozen; (b) "
                                      f"{len(nv)} visits' emitted rows ({'+'.join(map(str, nv))}) in order, as frozen, "
                                      f"and {nf} floating row(s) once inside the bytes' window")

    def start_dependent_check(self, covered: list, pred: dict) -> tuple:
        """O6-START-DEPENDENT (5.3; decision 5; the claim critic's #3), every covered run of both sides, for each
        ``start_dependent`` key: exactly ONE raw ``w`` row at its site, its ``old`` the prior's value and its ``new``
        the key's value (computed by O6-KEYS). Any other row FAILS, the detail naming each run's class
        (:func:`start_dependent_rows`): FINDING, EXPLAINED (by the row named), START DRIFT on that side (with "the
        <after.run> continuation" only at (after.old, after.value)), or the count."""
        groups: dict = {}                       # (site, side, class, why) -> the runs: both sides always named
        for r in covered:
            members = members_of(pred) if r["side"] == "F" else {}
            for x in start_dependent_rows(r["rows"], pred, members, pre=r.get("pre") or (), side=r["side"]):
                if x["class"] != "ok":
                    k = x["key"]
                    site = f"{k['donor']} e{k['sid']} t{k['tag']} ip{k['ip']} {k['target']}"
                    groups.setdefault((site, r["side"], x["class"], x["why"]), []).append(f"{r['side']}#{r['i']}")
        bad = [f"{site}: {cls} in {', '.join(runs)} -- {why}" for (site, _s, cls, why), runs in groups.items()]
        sd = pred.get("start_dependent") or []
        return (not bad, self.title("START-DEPENDENT"),
                "; ".join(bad[:6]) or f"{len(covered)} runs x {len(sd)} keys: "
                                      + ", ".join(f"{k['donor']} ip{k['ip']} {k['target'].split('.', 1)[1]} 0 -> "
                                                  f"{k['value']}" for k in sd)
                                      + " once each, as registered")

    # -- the report ---------------------------------------------------------------------------------------------
    def report_extra(self, run_dir: Path, session: dict, pred: dict, runs: list, checks: list) -> list:
        """Report-only (5.4): the scope (five lines: start dependence, rendered from the keys' ``after.run``; the name;
        the end state; the settings, the derived facts and the engine, as recorded; the language, read from the
        recorded P-TEXT rows), the start-dependent keys (O2's 4.5 report, ported) with each run's deviation and its
        class, the naming per run, the walk per run (the landing path, S14b's walk-out), the e15 row per run, the
        pattern per run, the session's end and ``stopped`` (S15), O5's sections (copied) and the re-runs held."""
        L = ["", "Scope (a US session):", "  start dependence -- " + scope_start(pred), "  the name -- " + SCOPE_NAME,
             "  the end state -- " + SCOPE_END_STATE]
        st = (session.get("install") or {}).get("settings")
        eng = [d for _ok, _w, d in self._recorded(session, "P-ENGINE")]
        L.append("  settings and engine -- " + (json.dumps(st, sort_keys=True) if st is not None else "not recorded")
                 + "; derived -- " + "; ".join(f"{k} {v.get('value')} ({v.get('why')})"
                                               for k, v in (pred.get("derived") or {}).items())
                 + "; engine -- " + (eng[-1] if eng else json.dumps((session.get("install") or {}).get("engine"))))
        L.append("  language -- " + self.scope_lang(session))
        L.append("")
        L.append("Start dependence (4.5, O2's report ported):")
        for k in pred.get("start_dependent") or ():
            vals, olds = {s: [] for s in SIDES}, []
            for r in runs:
                if not r["covered"]:
                    continue
                members = members_of(pred) if r["side"] == "F" else {}
                for x in start_dependent_rows(r["rows"], pred, members, pre=r.get("pre") or (), side=r["side"]):
                    if x["key"] is k or (x["key"]["donor"], x["key"]["ip"]) == (k["donor"], k["ip"]):
                        vals[r["side"]] += [n for _o, n, _l in x["rows"]]
                        olds += [o for o, _n, _l in x["rows"]]
            L.append("  " + start_dependent_line(k, {s: sorted(set(v)) for s, v in vals.items()}, sorted(set(olds))))
        for r in runs:
            if not r["covered"]:
                continue
            members = members_of(pred) if r["side"] == "F" else {}
            for x in start_dependent_rows(r["rows"], pred, members, pre=r.get("pre") or (), side=r["side"]):
                if x["class"] != "ok":
                    L.append(f"    {r['side']}#{r['i']} ip{x['key']['ip']}: {x['class']} -- {x['why']}")
        L.append("")
        L.append("The naming, per run (the named row: frame, field, before; the name_on_page row: frame, windows, "
                 "verdict; frames from the screen to ip610's row):")
        for r in runs:
            L += self._naming_lines(r, pred)
        L.append("")
        L.append("The walk, per run (attempt, outcome, from -> loss (frame, field, x, z), frames, route; THE LANDING "
                 "PATH: A route_to returned before the switch, B after it; flip, landing, the walk-out):")
        for r in runs:
            L += self._walk_lines(r, pred)
        L.append("")
        L.append("The e15 row, per run (frame, its index among visit 2's emitted rows, the frames to ip971's row -- "
                 "report-only; sid/uid/tag/ip/add as written):")
        stock = self._stock_src()
        for r in runs:
            L += self._e15_lines(r, pred, stock)
        L.append("")
        L.append("The pattern, per run (emitted rows per visit, the c rows; O6-PATTERN's first difference):")
        for r in runs:
            L += self._pattern_lines(r, pred, stock)
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
    def _naming_lines(r: dict, pred: dict) -> list:
        lab = f"  {r['side']}#{r['i']}:"
        named, pages = naming_rows(r.get("log") or [], pred)
        if not named and not pages:
            v = r["rec"].get("v")
            return [f"{lab} no named row" + (f" (the run VOID {v})" if v else "")]
        out = []
        store = (pred.get("name") or {}).get("store") or {}
        f610 = next((x.f for x in r.get("rows") or () if x.k == "w" and (x.sid, x.tag, x.ip) == (
            store.get("sid"), store.get("tag"), store.get("ip"))), None)
        for n in named:
            b = n.get("before") or {}
            out.append(f"{lab} named at frame {n.get('frame')} in {n.get('field')}; before frame {b.get('frame')} raws "
                       f"{[str(x)[:60] for x in b.get('raws') or ()]}; screen -> ip{store.get('ip')}'s row "
                       f"{None if f610 is None or n.get('frame') is None else f610 - n['frame']} frames")
        for p in pages:
            ws = [(w.get("mes"), w.get("line"), w.get("want"), w.get("ok")) for w in p.get("windows") or ()]
            out.append(f"{lab} name_on_page at frame {p.get('frame')} in {p.get('field')}: windows (mes, line, want, ok) "
                       f"{ws}; verdict {p.get('verdict')}")
        return out

    @staticmethod
    def _walk_lines(r: dict, pred: dict) -> list:
        lab = f"  {r['side']}#{r['i']}:"
        rows = C5.walk_rows(r.get("log") or [], pred)
        if not rows:
            v = r["rec"].get("v")
            return [f"{lab} no north door step row" + (f" (the run VOID {v})" if v else "")]
        out = []
        for s in rows:
            fr, lost = s.get("from") or {}, s.get("lost") or {}
            rt = s.get("route") or {}
            frames = (lost["frame"] - s["frame0"]) if lost.get("frame") is not None and s.get("frame0") is not None \
                else None
            path = "A" if rt.get("landed") is None else "B"
            wo = s.get("walkout") or []
            stop = f"({wo[-1][1]}, {wo[-1][2]}) at frame {wo[-1][0]}" if wo else "not recorded"
            out.append(f"{lab} attempt {s.get('attempt')} {s.get('outcome')}: from frame {fr.get('frame')} "
                       f"({fr.get('x')}, {fr.get('z')}) -> loss frame {lost.get('frame')} in {lost.get('field')} "
                       f"({lost.get('x')}, {lost.get('z')}), {frames} frames; route legs {rt.get('route')} travelled "
                       f"{rt.get('travelled')} replans {rt.get('replans')} pushes {rt.get('pushes')} waits "
                       f"{rt.get('waits')}; landing path {path} (route.landed {rt.get('landed')}, changed_to "
                       f"{rt.get('changed_to')}); flip {s.get('flip_frame')} (late {s.get('flip_late')}), landed frame "
                       f"{s.get('landed_frame')}; walk-out {len(wo)} samples, stopped {stop}"
                       + (f"; door {s.get('door')}" if s.get("door") else "")
                       + (f"; landed {s.get('landed')}" if s.get("landed") is not None else "")
                       + (f"; misroute {s.get('misroute')}" if s.get("misroute") else "")
                       + (f" -- {s.get('why')}" if s.get("why") else ""))
        return out

    @staticmethod
    def _e15_lines(r: dict, pred: dict, stock) -> list:
        lab = f"  {r['side']}#{r['i']}:"
        if not r.get("rows"):
            return [f"{lab} no trace rows"]
        members = members_of(pred) if r["side"] == "F" else {}
        fl = ((pred.get("pattern") or {}).get("floating") or [None])[0]
        if fl is None:
            return [f"{lab} no floating row registered"]
        t = list(fl["tuple"])
        hit = next((x for x in r["rows"] if x.k == "w" and place(x.fld, members) == t[0]
                    and (x.sid, x.tag, x.target, x.new) == (t[1], t[2], t[4], t[5])), None)
        if hit is None:
            return [f"{lab} no e15 row"]
        got = C5.pattern_of(r["rows"], pred, members, C5.stock_join(stock, members))
        v = int(fl["visit"]) - 1
        idx = next((i for i, x in enumerate(got["visits"][v]) if x == tuple(t)), None) if v < len(got["visits"]) \
            else None
        r971 = next((x for x in r["rows"] if x.k == "w" and place(x.fld, members) == 153
                     and (x.sid, x.tag, x.ip) == (32, 1, 971)), None)
        win = float_window(pred["pattern"])[0]
        return [f"{lab} frame {hit.f}, index {idx} of visit {v + 1} (window {None if win is None else list(win)}), "
                f"{None if r971 is None else r971.f - hit.f} frames to ip971's row; sid {hit.sid} uid {hit.uid} tag "
                f"{hit.tag} ip {hit.ip} add {hit.add}"]

    @staticmethod
    def _pattern_lines(r: dict, pred: dict, stock) -> list:
        lab = f"  {r['side']}#{r['i']}:"
        if not r.get("rows"):
            return [f"{lab} no trace rows"]
        members = members_of(pred) if r["side"] == "F" else {}
        got = C5.pattern_of(r["rows"], pred, members, C5.stock_join(stock, members))
        v = got["visits"]
        out = [f"{lab} emitted per visit {[f'{x[0][0]}x{len(x)}' for x in v]}; c rows "
               f"{[(c[0], f'e{c[1]} t{c[2]} +{c[3]}', c[4], c[5], c[6]) for c in got['counts']]}"]
        diff = pattern_diff6(got, pred["pattern"])
        if diff:
            out.append(f"{lab} O6-PATTERN's first difference: {diff[0]}")
        return out

    # -- the CLI ------------------------------------------------------------------------------------------------
    def handle(self, args) -> int | None:
        """``--rehearsal-report`` (O6's, printed through segment_trace.say: it quotes the game's pages);
        ``--offline-check`` (with the chain's route members printed first); then O2's (``--draft``,
        ``--preflight``)."""
        if args.rehearsal_report:
            ST.say(rehearsal_report(args.rehearsal_report))
            return 0
        if args.offline_check:
            pred, what = self.current(args.predictions)
            print(f"predictions: {what}")
            members = members_of(pred)
            if all(d in members.values() for d in ROUTE_DONORS):
                print(f"chain: {route_members_line(members)}")
            checks = self.offline_check(pred)
            for ok, w, detail in checks:
                ST.say(f"{'PASS' if ok else 'FAIL'}  {w}\n      {detail}")
                for d in A.defect_lines(detail):
                    print(d)
            return 0 if all(ok for ok, _w, _d in checks) else 1
        return A.O2Segment.handle(self, args)


O6 = O6Segment()


# ======================================================================== the rehearsal report
def _naming_report(nr: dict) -> list:
    """The naming record's lines (7.2; F3): NameSetting's first sample and the last 198 sample before it, every Confirm
    between it and the close, the named row and its before, the page row and its verdict, every [STNR] window's
    rendered lines, the frames 199 -> 200, ip610's frame."""
    if not nr:
        return ["    naming: not recorded"]
    L = [f"    naming: the screen's first sample {nr.get('screen_first')}, the last 198 sample before it "
         f"{nr.get('last_198')}; closed {nr.get('close_frame')}; Confirms (seq, why, down) "
         f"{[(c.get('seq'), c.get('why'), c.get('down_frame')) for c in nr.get('confirms') or ()]}"]
    n = nr.get("named")
    L.append(f"    named row: " + (f"frame {n.get('frame')} in {n.get('field')}, before {n.get('before')}" if n else
                                   "none"))
    p = nr.get("page")
    L.append("    name_on_page row: " + (f"frame {p.get('frame')}, verdict {p.get('verdict')}, windows "
                                         f"{[(w.get('mes'), w.get('line')) for w in p.get('windows') or ()]}" if p
                                         else "none"))
    for w in nr.get("stnr") or ():
        L.append(f"    [STNR] window mes {w.get('mes')}: first frame {w.get('first')}, lines {w.get('lines')}, unparsed "
                 f"samples {w.get('unparsed')}")
    L.append(f"    199 -> 200: {nr.get('lag_199_200')} frames; ip610's row at frame {nr.get('f610')}")
    return L


def _door_report(wr: dict) -> list:
    """The walk record's lines (7.2; F1, F2, F12, F15): the grant, each attempt's walk -- hold 1's end and the corner,
    the walk holds in [walk_stop_z, 1333) and the hold-2 starts -- the loss, THE LANDING PATH, S14b's walk-out."""
    L = []
    gr = wr.get("grant")
    if gr is None:
        L.append("    walk: no grant before the north door step")
    else:
        objs = [(o.get("sid"), o.get("shown"), o.get("coll"), o.get("solid"), o.get("r")) for o in gr.get("objects")
                or ()]
        L.append(f"    grant: frame {gr.get('frame')} at ({gr.get('x')}, {gr.get('z')}) y {gr.get('y')}; "
                 f"{gr.get('from_last_page_frames')} frames from the last page's going ({gr.get('last_page')!r}); "
                 f"objects (sid, shown, coll, solid, r) {objs}")
    for a in wr.get("attempts") or ():
        L.append(f"    door attempt {a.get('attempt')}: {a.get('outcome')}; loss {a.get('lost')}; door {a.get('door')}; "
                 f"landed {a.get('landed')}; LANDING PATH {a.get('path')} (route.landed {a.get('route_landed')}, "
                 f"changed_to {a.get('changed_to')}); flip {a.get('flip_frame')} (late {a.get('flip_late')}), landed "
                 f"frame {a.get('landed_frame')}; walk-out stopped {a.get('walkout_stop')}")
        w = a.get("walk")
        if w is None:
            L.append("      no walk tapped for it")
            continue
        L.append(f"      route {w.get('legs')} legs {w.get('waypoints')}; {len(w.get('holds') or [])} hold(s); hold 1 "
                 f"ended {w.get('hold1_end')}; corner {w.get('corner')}; pushes {w.get('pushes')}")
        for h in w.get("holds") or ():
            L.append(f"      hold seq {h.get('seq')} {h.get('steps')}: from {h.get('from')} to {h.get('to')}, moved "
                     f"{h.get('moved')}, off the pressed {h.get('off_pressed')} deg"
                     + (" SLIDE" if h.get("slide") else "") + (" STALL" if h.get("stall") else ""))
        L.append(f"      walk holds sent in [walk_stop_z, 1333): {w.get('in_band')}; hold-2 starts {w.get('hold2')}")
    L.append(f"    calibration: {wr.get('calibration')}")
    return L


def _trace_report(tr: dict) -> list:
    """The trace summary's lines (7.2; F4): O5's, with O6's crossings, the e15 row and the start-dependent rows."""
    if not tr:
        return ["    trace: none (untraced, or no rows)"]
    L = C5._trace_report(tr)
    L.append(f"      e15 row {tr.get('e15')}")
    L.append(f"      start-dependent rows {tr.get('start_dependent')}")
    return L


def rehearsal_report(run_dir) -> str:
    """``--rehearsal-report``: an o6_rehearse.py launch's ``o6_rehearsal.json`` (research/o6_design.md 7.2), stage by
    stage and run by run -- what each freeze item (7.3) is read from: the capabilities and the launch's readings
    (F10); per run its outcome, the naming (F3), the walk and the landing path (F1, F2, F12, F15), the KEYON pairs and
    the timed windows (F8), the evidence (F11), the trace with the e15 row and the start-dependent rows (F4), the end
    (F5, F7), the stops (R-NAMING-VOID, R-WALK-VOID: F7) and an untraced run's exceptions (F14); F-SMOKE's warps and
    twins (F13)."""
    run_dir = Path(run_dir)
    doc = json.loads((run_dir / REHEARSAL_FILE).read_text(encoding="utf-8"))
    L = [f"O6 rehearsals -- {run_dir.name}  (draft sha {str(doc.get('draft_sha256'))[:8]}; stages "
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
            L += C5._smoke_lines(name, stage, recs, (doc.get("twins") or {}).get(name))
            L.append("")
            continue
        L.append(f"== {name}: warp {stage.get('field')} {stage.get('entrance')} {stage.get('sc')} -> {stage.get('end')}"
                 + (" UNTRACED" if stage.get("untraced") else "")
                 + (f", walk_stop_z {stage.get('walk_stop_z')}" if stage.get("walk_stop_z") is not None else "")
                 + (", walk_stop_hold" if stage.get("walk_stop_hold") else "")
                 + (", naming_stop" if stage.get("naming_stop") else "")
                 + f"  ({len(recs)} run(s)) -- settles: {stage.get('settles')}")
        for rec in recs:
            out = rec.get("outcome") or {}
            rate = rec.get("rate") or {}
            L.append(f"  run {rec.get('n')} ({rec.get('side', 'S')}): {out.get('end')} -- {out.get('why')}"
                     + (f" [{out.get('v')} {out.get('cell')} {out.get('by')}]" if out.get("v") else "")
                     + f"; beats {rec.get('beats')}; {rec.get('t1', 0) - rec.get('t0', 0):.0f}s; "
                     f"{rate.get('fps')} fps; trace {rec.get('trace_file')}")
            L.append(f"    grants: {len(rec.get('grants') or [])} (the north door's alone)")
            L += _naming_report(rec.get("naming") or {})
            L += _door_report(rec.get("walk") or {})
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
                                              f"frame {ws.get('frame')} at ({ws.get('x')}, {ws.get('z')}) by "
                                              f"{ws.get('by')}, the held-back steps {ws.get('steps')}; direction holds "
                                              f"before it {ws.get('holds_before')} (the walk had begun), after it "
                                              f"{ws.get('holds_after')} (there must be none)"))
            ns = rec.get("naming_stop", ...)
            if ns is not ...:
                L.append("    naming stop: " + ("never fired" if ns is None else
                                                f"frame {ns.get('frame')} ui {ns.get('ui')} -- {ns.get('why')}; "
                                                f"recovery {ns.get('recovery_s')} s"))
            if not rec.get("traced", True):
                L.append(f"    untraced: exceptions since the warp {rec.get('exceptions')}; Memoria.log lines "
                         f"{len(rec.get('log_lines') or [])}")
            end = rec.get("end") or {}
            er = end.get("end_run") or {}
            L.append(f"    end: state {end.get('end_state')}; end_run " + ("ok" if er.get("ok") else f"FAILED {er.get('why')}")
                     + f", title {er.get('title')}, rows {[x.get('k') for x in er.get('how') or ()]}"
                     + (f", {er.get('s')} s" if er.get("s") is not None else ""))
            L += _trace_report(rec.get("trace") or {})
        L.append("")
    return "\n".join(L)


# ======================================================================== the session and the CLI
def run(g) -> None:
    """The session (tools/play.py's entry): O6Segment.run."""
    return O6.run(g)


def main(argv=None) -> int:
    return O6.main(argv)


if __name__ == "__main__":
    sys.exit(main())
