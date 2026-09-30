"""THE STORY-WRITE TRACE, O2 -- ALEXANDRIA: Vivi's segment, from a raw warp into Main Street (entrance 102, the
scenario at 1000) to the rooftop's Field(61), stock Alexandria against the alxt zone's verbatim fork, both sides
played by one beat-table driver (studies/story-trace/PLAN.md, "O2"; the design: research/o2_design.md).

    py tools/play.py studies/story-trace/o2_alexandria.py --label story-o2 --timeout 240
    py studies/story-trace/o2_alexandria.py --offline-check     # the build, its text, the keys, the regions, the goals
    py studies/story-trace/o2_alexandria.py --preflight         # the live install (read-only)
    py studies/story-trace/o2_alexandria.py --draft             # the draft predictions, as JSON
    py studies/story-trace/o2_alexandria.py --freeze            # write o2_predictions_v1.json (once: the lead, after
                                                                # the stock rehearsals)
    py studies/story-trace/o2_alexandria.py --analyse <run dir> # the analysis alone, on saved traces
    py studies/story-trace/o2_alexandria.py --rehearsal-report <run dir>   # an o2_rehearse.py launch, stage by stage

THE SIDES (o2_forks.json; built offline, NOT deployed):
  S  stock: the install's scripts. Start: 100 (Main Street), entrance 102, SC 1000.
  F  `import-chain 100 --verbatim --ids 100-117 --fresh-ids --id-base 31220 --name-prefix O2`: 18 members,
     31220-31237, sharing text block 33. Start: 31220 (its 100). Field 61 is no member, so member(116)'s `Field(61)`
     stays real: that is the seam, and the segment's end on both sides.

THE ENTRY: New Game, the trace armed, then a raw `warp <100 | 31220> 102 1000` (research/o2_design.md 0.1). The warp
writes FieldEntrance and the scenario into gEventGlobal before the map changes: exactly three residue rows in field 70,
which the front cut sets aside and O2-START requires.

THE ROUTE: segment_drive.drive, the beat-table driver, on the predictions' table (cells keyed by the donor place and
the published SC; research/o2_design.md 2). It acts only on what the game shows; anything the table cannot answer is a
VOID with its class (V1-V14), and a forbidden write its own log backs is one too (V12).

THE ANALYSIS: each run is cut at its start row (the first write in 100) and at its first row in 61, digested and
compared as O1's; the O2 checks (research/o2_design.md 5.3) judge the ladder and the chain by byte span, the residue,
the registered writes, the seam, the masked regions and the state handed to 61, and read every run's forbidden
writes and VOID classes per side. The predictions are frozen by the lead after the stock rehearsals (o2_rehearse.py);
until then --offline-check and --preflight read the draft.
"""
from __future__ import annotations

import hashlib
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
import segment_drive as SD                                              # noqa: E402
import segment_trace as ST                                              # noqa: E402
from segment_trace import (SIDES, cut_at_end, cut_at_start, is_noise, key_of, members_of, place,  # noqa: E402
                           row_keys, wkey)

PREDICTIONS = HERE / "o2_predictions_v1.json"
MANIFEST = HERE / "o2_forks.json"
SESSION_FILE = "o2_session.json"
REPORT_FILE = "o2_report.txt"
REHEARSAL_FILE = "o2_rehearsal.json"
CHAIN_DIR = Path(r"C:\gd\_ns_playtest\o2\fork")
BUILD_DIR = Path(r"C:\gd\_ns_playtest\o2\build")
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
TEXT_BLOCK = 33
#: The language the session runs in, and the name the engine logs for it (FF9TextTool.cs:395, LanguageName.cs).
SESSION_LANG = "us"
ENGINE_LANG = {"us": "English(US)", "uk": "English(UK)", "jp": "Japanese", "gr": "German", "fr": "French",
               "it": "Italian", "es": "Spanish"}
#: 4.5's scope line: what the start-dependence claim covers, and what it does not.
SCOPE_LINE = ("start dependence of gEventGlobal values only: party data, cards and field 70's override state are "
              "not covered")
#: The raw sites the rehearsal report names present or absent (research/o2_design.md 7.2).
WATCH_SITES = {"hippaul_254": (103, 18, 1, 254), "ilia_165": (106, 5, 1, 165)}
_MODULE_DOC = __doc__


def _sha(b: bytes | None) -> str | None:
    return None if b is None else hashlib.sha256(b).hexdigest()


def _sha10(b: bytes | None) -> str:
    return "none" if b is None else hashlib.sha256(b).hexdigest()[:10]


def _s16(v) -> int:
    return ((int(v) + 0x8000) & 0xFFFF) - 0x8000


def label(k: dict) -> str:
    return k.get("what") or k.get("why") or f"{k['donor']} e{k['sid']} t{k['tag']} ip{k['ip']}"


def site_of(k: dict) -> str:
    """A registered key's site as a compound key's ``prior`` names it: ``donor/sid/tag/ip``."""
    return f"{k['donor']}/{k['sid']}/{k['tag']}/{k['ip']}"


# ======================================================================== the predictions (draft v1)
def chain_from_campaign(campaign: Path = CHAIN_DIR / "campaign.toml") -> tuple:
    """``({fork id: donor}, {fork id: member name})`` of the built alxt chain, which must be exactly
    ``{31220 + i: 100 + i for i in range(18)}`` (research/o2_design.md 1.5)."""
    members, names = ST.chain_from_campaign(campaign)
    want = {31220 + i: 100 + i for i in range(18)}
    if members != want:
        raise AssertionError(f"{campaign}: the chain is {members}, not the design's {want}")
    return members, names


def _key(donor, sid, tag, ip, off, target, value, op, what, prior=None) -> dict:
    k = {"donor": donor, "m": T.FIELD_MODE, "src": "eb", "sid": sid, "tag": tag, "ip": ip, "off": off,
         "target": target, "value": value, "op": op, "what": what}
    if prior is not None:
        k["prior"] = prior
    return k


def _region(points, role, **kw) -> dict:
    return {"points": [list(p) for p in points], "role": role, **kw}


def _exit(points, to, entrance, face_gate=None, **kw) -> dict:
    return _region(points, "exit", to=to, entrance=entrance, face_gate=face_gate, **kw)


def _hotspots() -> dict:
    """2.5's hot-spots: each tag 1's own ``Int16[220]``/``[222]`` store constants and its ``Instance.Int24[0] const(n)
    B_LT`` compare; the reach is ``32 * sqrt(n)``, rounded down."""
    raw = {100: [(12, -658, 4843, 77), (13, -758, 1121, 77)],
           101: [(11, -540, -979, 60), (12, -1011, -2327, 60), (13, 998, -2356, 60), (14, 2434, 492, 40)],
           102: [(7, 1477, 4748, 80)],
           103: [(19, 2239, 1114, 300), (20, 600, -272, 50), (21, -891, 4413, 50)],
           105: [(9, -1561, 447, 60)],
           106: [(11, -155, 1205, 120)],
           115: [(11, 1800, -323, 90), (12, -547, -1739, 90)],
           116: [(17, -1124, -98, 40), (18, -291, 10894, 80), (19, 4200, 2762, 90)]}
    return {str(d): [{"sid": s, "x": x, "z": z, "n": n, "reach": int(32 * math.sqrt(n))} for s, x, z, n in spots]
            for d, spots in raw.items()}


def _regions() -> dict:
    """2.5's regions: each the FIRST SetRegion of its (donor, entry) in the stock bytes, in the engine's point order
    (O2-REGIONS re-decodes each), with its role."""
    gate = [48, 208]
    return {
        "100.e11": _region([(300, 166), (-300, 166), (-300, 3555), (-50, 6333), (70, 6333)], "benign",
                           why="the street: its tag 2 writes Map.Byte[36] only (100 e11 t2 ip138); the control spot "
                               "(0,850) stands inside it"),
        "100.e15": _exit([(-365, 7708), (295, 7708), (355, 6538), (-371, 6532)], 101, 200),
        "100.e16": _exit([(-1019, -439), (961, -439), (704, 104), (-860, 191)], 107, 200),
        "100.e17": _exit([(1224, 1225), (1252, 923), (777, 893), (677, 1074), (777, 1253)], 114, 200),
        "101.e15": _exit([(3295, -65), (3326, -987), (2238, -1444), (2872, 261)], 100, 201),
        "101.e16": _exit([(-3500, -600), (-3500, -200), (-2621, 444), (-2254, -1444)], 102, 201),
        "101.e17": _exit([(110, 233), (-100, 233), (-183, -855), (206, -855)], 112, 201, gate),
        "102.e8": _exit([(858, 6987), (468, 6987), (404, 5142), (1134, 5019)], 103, 203),
        "102.e9": _exit([(175, 663), (2190, 999), (1607, 2186), (941, 2429), (191, 2361)], 101, 203),
        "102.e10": _exit([(2753, 4854), (2804, 4832), (2220, 4436), (2130, 4617)], 108, 203),
        "103.e22": _exit([(-4263, -1798), (-4605, -734), (-3611, -119), (-3150, -2777)], 105, 205),
        "103.e23": _exit([(333, -4477), (-555, -4477), (-888, -3430), (666, -3411)], 102, 205),
        "103.e24": _exit([(2537, 3762), (2792, 3650), (2440, 2476), (2160, 2641)], 109, 205),
        "103.e25": _exit([(4999, 400), (4999, 999), (3848, 999), (3868, 400)], 110, 205),
        "103.e26": _exit([(-3351, 2611), (-3656, 2216), (-2835, 1505), (-2480, 1977)], 111, 205),
        "103.e27": _exit([(-3351, 2611), (-3656, 2216), (-2835, 1505), (-2480, 1977)], 111, 206,
                         why="the same quad as e26"),
        "103.e28": _region([(-500, -111), (550, -111), (250, -1000), (-200, -1000)], "confirm",
                           tag3={"ip": 95, "does": "Map.Byte[24] const(1) B_LET"},
                           why="the ticket booth: its tag 3 sets the stage (Map.Byte[24] := 1, ip95), whose "
                               "choice 215 follows"),
        "105.e10": _exit([(1138, 3845), (1098, 4226), (-292, 4577), (264, 2527)], 103, 111),
        "105.e11": _exit([(-185, -770), (-1223, -895), (-1327, -167), (-220, 195)], 106, 111),
        "105.e12": _region([(-964, 1677), (-1055, 2300), (55, 2000), (-122, 1203)], "walkin", live=[1150, 1152],
                           why="its tag 2 takes control while 1150 <= SC < 1152 (guard ip38, DisableMove ip75); dead "
                               "at SC 1152, where it lies across the exit line"),
        "106.e12": _exit([(-1048, 4163), (-1048, 3623), (-262, 3319), (-364, 4135)], 105, 211),
        "106.e13": _exit([(-487, 156), (-487, -84), (180, -196), (180, 164)], 113, 211, gate),
        "106.e14": _exit([(-327, -1240), (-317, -1462), (151, -1458), (151, -1188)], 115, 211,
                         why="its first edge is the west edge: ExitField's walk ends before the fade"),
        "115.e13": _exit([(-124, -3597), (984, -3546), (745, -2881), (633, -2741), (-34, -2783)], 106, 212),
        "115.e14": _region([(150, 144), (-150, 144), (-150, -40), (150, -40)], "dormant", entrances=[213, 214, 215],
                           why="the ladder's twin quad: InitRegion(14) only in Main_Init's default branch (e0 t0 "
                               "ip406); its tag 3 calls 115 e17 t12, a card event"),
        "115.e15": _region([(150, 144), (-150, 144), (-150, -40), (150, -40)], "confirm",
                           tag3={"ip": 65, "does": "Map.Byte[49] const(1) B_LET"},
                           why="the ladder: its tag 3 ip65, and the climb at ip125 when Map.Byte[24] == 10"),
    }


def _table() -> list:
    """2.4's beat table: cells keyed by (donor place, published SC), each its steps in order. ``start`` is the
    control spot the step begins from (the offline route check's, O2-GOALS; the live walk plans from where he
    stands)."""
    exits103 = ["103.e23", "103.e24", "103.e25", "103.e26", "103.e27"]
    return [
        {"donor": 100, "sc": 1000, "steps": [
            {"kind": "cross", "name": "Main Street's north exit (e15)", "target": "100.e15", "to": 101,
             "goal": [0, 7000], "start": [0, 850], "avoid": ["100.e16", "100.e17"], "npcs": False,
             "interrupts": 1, "closed_floors": [3]}]},
        {"donor": 101, "sc": 1000, "steps": [
            {"kind": "cross", "name": "Main Street B's west exit (e16)", "target": "101.e16", "to": 102,
             "goal": [-2936, -400], "start": [1939, -883], "avoid": ["101.e15", "101.e17"]}]},
        {"donor": 102, "sc": 1000, "steps": [
            {"kind": "cross", "name": "Main Street C's north exit (e8)", "target": "102.e8", "to": 103,
             "goal": [752, 5415], "start": [865, 2525], "avoid": ["102.e9", "102.e10"]}]},
        {"donor": 103, "sc": 1000, "steps": [
            {"kind": "confirm", "name": "the ticket booth (e28)", "target": "103.e28", "expect": "choice",
             "goal": [50, -800], "start": [-75, -2210], "avoid": ["103.e22", *exits103]}]},
        {"donor": 103, "sc": 1150, "steps": [
            {"kind": "cross", "name": "the square's west exit (e22)", "target": "103.e22", "to": 105,
             "goal": [-3993, -965], "start": [45, -950], "avoid": exits103}]},
        {"donor": 105, "sc": 1150, "steps": [
            {"kind": "trigger", "name": "the alley's walk-in (e12)", "target": "105.e12", "goal": [-500, 1750],
             "start": [-51, 2986], "avoid": ["105.e10", "105.e11"], "closed_floors": [2]}]},
        {"donor": 105, "sc": 1152, "no_pages": True,
         "watch": [{"sid": 7, "name": "Alleyway Jack", "radius": "range_r"}],
         "steps": [
            {"kind": "leave_now", "name": "leave the lookout by the south exit (e11)", "target": "105.e11",
             "to": 106, "goal": [-667, -403], "start": [-244, 2562], "avoid": ["105.e10"], "immediate": True,
             "lunge_ticks": 10, "settle": 0, "npcs": False, "attempts": 1, "interrupts": 0}]},
        {"donor": 106, "sc": 1152, "no_pages": True, "steps": [
            {"kind": "wait_sc", "name": "wait for Puck's SC 1153", "sc": 1153, "wait_s": 90, "goal": [550, 2000],
             "start": [-123, 3494], "avoid": ["106.e12", "106.e13", "106.e14"], "overlay_ok": True}]},
        {"donor": 106, "sc": 1153, "no_pages": True, "steps": [
            {"kind": "cross", "name": "the steeple's south exit (e14)", "target": "106.e14", "to": 115,
             "goal": [-123, -1306], "start": [550, 2000], "avoid": ["106.e12", "106.e13"], "overlay_ok": True}]},
        {"donor": 115, "sc": 1154, "steps": [
            {"kind": "confirm", "name": "the ladder (e15)", "target": "115.e15", "expect": "control_lost",
             "goal": [0, 50], "start": [206, -1911], "avoid": ["115.e13"]}]},
        {"donor": 115, "sc": 1155, "steps": [
            {"kind": "confirm", "name": "the ladder, then the climb (e15)", "target": "115.e15",
             "expect": "control_lost", "then": "climb", "beat": "climbed", "goal": [0, 50], "start": [50, -968],
             "avoid": ["115.e13"], "attempts": 2, "climb": {"top": -2431}}]},
        {"donor": 116, "sc": 1155, "steps": [
            {"kind": "trigger", "name": "the rooftop, west to x <= 900", "until": {"x_le": 900}, "goal": [630, 190],
             "start": [2718, -137]},
            {"kind": "trigger", "name": "the rooftop, north to z >= 2300", "until": {"z_ge": 2300},
             "goal": [-750, 2690], "start": [-339, 244], "closed_tris": [217]},
            {"kind": "trigger", "name": "the rooftop, to Puck's corner", "until": {"x_gt": 3000, "z_gt": 10300},
             "goal": [3410, 10700], "start": [-750, 2690], "closed_tris": [217]}]},
    ]


def draft_predictions() -> dict:
    """The registered claims (research/o2_design.md section 4). Every number was read off the stock bytes (the
    offline check re-derives each: O2-KEYS, O2-REGIONS, O2-GOALS) or the chain's campaign.toml; nothing is read from
    a run. The rehearsals (o2_rehearse.py) settle the driver's numbers before the lead freezes them."""
    members, names = chain_from_campaign()
    key = _key
    ladder = [
        key(104, 7, 1, 1046, 546, "Global.UInt16[0]", 1150, ":=", "SC 1000 -> 1150: 104 stage 4, after 254 opens"),
        key(105, 3, 1, 511, 362, "Global.UInt16[0]", 1151, ":=", "SC -> 1151: 105 stage 4, after choice 305"),
        key(105, 14, 1, 2818, 2274, "Global.UInt16[0]", 1152, ":=", "SC -> 1152: 105 stage 14, before control"),
        key(106, 2, 1, 312, 221, "Global.UInt16[0]", 1153, ":=", "SC -> 1153: Puck at his stop, Vivi within 1400"),
        key(115, 1, 1, 462, 244, "Global.UInt16[0]", 1154, ":=", "SC -> 1154: 115 stage 1, after 353"),
        key(115, 1, 1, 1683, 1465, "Global.UInt16[0]", 1155, ":=", "SC -> 1155: 115 stage 9, after 383"),
    ]
    chain = [
        key(100, 15, 2, 255, 225, "Global.Int16[2]", 200, ":=", "FieldEntrance 200: 100's north exit"),
        key(101, 0, 0, 291, 281, "Global.Int16[2]", 202, ":=", "FieldEntrance 202: 101's Main_Init (first visit)"),
        key(101, 16, 2, 255, 225, "Global.Int16[2]", 201, ":=", "FieldEntrance 201: 101's west exit"),
        key(102, 8, 2, 255, 225, "Global.Int16[2]", 203, ":=", "FieldEntrance 203: 102's north exit"),
        key(103, 30, 1, 972, 257, "Global.Int16[2]", 205, ":=", "FieldEntrance 205: 215 answered, to 104"),
        key(104, 2, 1, 558, 547, "Global.Int16[2]", 209, ":=", "FieldEntrance 209: 104 back to 103"),
        key(103, 22, 2, 261, 231, "Global.Int16[2]", 205, ":=", "FieldEntrance 205: 103's west exit"),
        key(105, 11, 2, 227, 197, "Global.Int16[2]", 111, ":=", "FieldEntrance 111: 105's south exit"),
        key(106, 14, 2, 222, 192, "Global.Int16[2]", 211, ":=", "FieldEntrance 211: 106's south exit"),
        key(115, 0, 0, 249, 235, "Global.Int16[2]", 213, ":=", "FieldEntrance 213: 115's Main_Init at SC 1153"),
        key(115, 1, 1, 1951, 1733, "Global.Int16[2]", 0, ":=", "FieldEntrance 0: 115 to 116"),
        key(116, 2, 1, 1694, 1575, "Global.Int16[2]", 0, ":=", "FieldEntrance 0: 116 to 61"),
    ]
    uint19 = key(100, 19, 1, 1531, 848, "Global.UInt16[19]", 2, "|=", "UInt16[19] |= 2 (START-DEPENDENT, 4.5)",
                 prior="newgame0")
    byte6 = key(116, 2, 1, 765, 646, "Global.Byte[6]", 2, "|=", "Byte[6] |= 2 after Menu(1,1) (START-DEPENDENT, 4.5)",
                prior="newgame0")
    writes = [
        key(100, 19, 1, 834, 151, "Global.Byte[8]", 125, ":=", "100 Byte[8] := 125"),
        key(100, 19, 1, 981, 298, "Global.UInt16[21]", 2, ":=", "100 UInt16[21] := 2 (party: Vivi only)"),
        key(100, 19, 1, 1066, 383, "Global.Byte[303]", 0, ":=", "100 Byte[303] := 0"),
        key(100, 19, 1, 1100, 417, "Global.Byte[303]", 1, "++", "100 Byte[303]++", prior="100/19/1/1066"),
        key(100, 19, 1, 1497, 814, "Global.Byte[4]", 0, ":=", "100 Byte[4] := 0 (ip1497)"),
        uint19,
        key(100, 19, 1, 1562, 879, "Global.Byte[4]", 0, ":=", "100 Byte[4] := 0 (ip1562)"),
        key(100, 19, 1, 1570, 887, "Global.Byte[17]", 0, ":=", "100 Byte[17] := 0"),
        key(100, 19, 1, 1578, 895, "Global.Byte[18]", 1, ":=", "100 Byte[18] := 1"),
        key(100, 1, 18, 579, 143, "Global.Bit[3718]", 1, ":=", "100 Bit[3718] := 1 (the Rat Kid)"),
        key(101, 7, 1, 319, 152, "Global.Bit[3717]", 1, ":=", "101 Bit[3717] := 1 (the Herald)"),
        key(103, 0, 0, 367, 357, "Global.Byte[8]", 125, ":=", "103 Byte[8] := 125 (both visits: one key)"),
        key(103, 18, 1, 218, 15, "Global.Byte[472]", 1, ":=", "103 Byte[472] := 1 (Hippaul, first visit)"),
        key(104, 7, 0, 313, 299, "Global.Int16[469]", 1042, ":=", "104 Int16[469] := 1042"),
        key(104, 7, 0, 333, 319, "Global.Int16[469]", 1043, "|=", "104 Int16[469] |= 1 (SC < 1150)",
            prior="104/7/0/313"),
        key(104, 7, 1, 613, 113, "Global.Int16[469]", 1042, "&=", "104 Int16[469] &= 8190 (the ticket pick)",
            prior="104/7/0/333"),
        key(104, 7, 1, 955, 455, "Global.Byte[472]", 4, ":=", "104 Byte[472] := 4 (guard < 4)"),
        key(103, 22, 2, 205, 175, "Global.Byte[13]", 3, ":=", "103 Byte[13] := 3 (the west exit's music)"),
        key(103, 22, 2, 244, 214, "Global.Byte[14]", 3, ":=", "103 Byte[14] := 3 (the west exit)"),
        key(106, 5, 0, 109, 91, "Global.Bit[3712]", 0, ":=", "106 Bit[3712] := 0 (Ilia's init)"),
        key(106, 14, 2, 194, 164, "Global.Byte[13]", 3, ":=", "106 Byte[13] := 3 (the south exit)"),
        key(115, 0, 0, 467, 453, "Global.Byte[8]", 125, ":=", "115 Byte[8] := 125"),
        key(116, 0, 0, 335, 321, "Global.Byte[8]", 125, ":=", "116 Byte[8] := 125"),
        byte6,
        key(116, 2, 1, 1469, 1350, "Global.Byte[8]", 0, ":=", "116 Byte[8] := 0"),
        key(116, 2, 1, 1666, 1547, "Global.Byte[13]", 3, ":=", "116 Byte[13] := 3"),
    ]
    start_dependent = [
        dict(uint19, after_o1=1799, why="UInt16[19] |= 2 on New Game's 0; after O1 it holds 1797 (bits 1, 4, 256, "
                                        "512, 1024)"),
        dict(byte6, after_o1=3, why="Byte[6] |= 2 on New Game's 0; after O1 it holds 1 (50 e17 ip3240)"),
    ]
    return {
        "version": 1,
        "what": "O2: 100@1000 (warp, entrance 102) -> 101 -> 102 -> 103 -> 104 -> 103 -> 105 -> 106 -> 115 -> 116 "
                "-> Field(61), stock vs the alxt zone's verbatim fork (PLAN.md, O2)",
        "rehearsals": [],
        "order": ["S", "F", "S", "F", "S", "F"],
        "min_covered": 2,
        "rerun": {"max": 2},
        "budget": {"run_s": 1800, "run_min_s": 1200, "session_s": 14400, "settle_s": 1.0, "no_progress_s": 120},
        "start": {"S": 100, "F": 31220},
        "entrance": 102,
        "scenario": 1000,
        "lang": SESSION_LANG,
        "end_field": 61,
        "end_fields": [61],
        "route": [100, 101, 102, 103, 104, 105, 106, 115, 116],
        # the ORDER the route visits them in (segment_drive rule 2 holds every new visit to it; O2-GOALS every
        # crossing's `to`): 103 twice, 104 between
        "visits": [100, 101, 102, 103, 104, 103, 105, 106, 115, 116],
        "stock_fields": [100, 101, 102, 103, 104, 105, 106, 115, 116, 61],
        "members": {str(f): d for f, d in sorted(members.items())},
        "names": {str(f): n for f, n in sorted(names.items())},
        "text_block": TEXT_BLOCK,
        "recovery": 4600,
        "seam": {"donor": 116, "to": 61, "why": "member(116)'s Field(61) (116 e2 t1 ip1702) stays real: the end"},
        "cut_start": True,
        "start_first": key(100, 0, 0, 30, 16, "Global.Bit[191]", 0, ":=", "100's Main_Init: its first store"),
        "start_residue": [[0, 0, 232], [1, 0, 3], [2, 0, 102]],
        "residue_after_start": [],
        "ladder": ladder,
        "sc_bytes": [0, 1],
        "sc_order": True,
        "chain": chain,
        "entrance_bytes": [2, 3],
        "writes": writes,
        "start_dependent": start_dependent,
        "noise": [{"donor": 103, "m": T.FIELD_MODE, "src": "eb", "sid": 18, "tag": 1, "off": 51,
                   "target": "Global.Byte[472]", "value": 2, "ip": 254, "op": ":=",
                   "why": "Hippaul's :=2 (103 e18 t1 ip254) runs only if his three legs at speed 15 (about 6600u) "
                          "end before 103 unloads; 104 writes :=4 either way (e7 t1 ip955, guard < 4), so it never "
                          "propagates"}],
        "forbidden": [
            {"donor": 105, "sid": 7, "tag": 2, "cause": "contact", "object": 7,
             "why": "Alleyway Jack's contact ran (the mugging or the card tutorial)"},
            {"target": "Global.Bit[3714]", "cause": "contact", "object": 7,
             "why": "Jack's card branch (105 e7 t2 ip729)"},
            {"target": "Global.Bit[3715]", "cause": "contact", "object": 7,
             "why": "Jack's mugging branch (105 e7 t2 ip945)"},
            {"target": "Global.Int16[220]", "cause": "confirm_hotspot", "why": "a hot-spot pickup: a stray Confirm"},
            {"target": "Global.Int16[222]", "cause": "confirm_hotspot", "why": "a hot-spot pickup: a stray Confirm"},
            {"target": "Global.Int16[224]", "cause": "confirm_hotspot", "why": "a hot-spot pickup: a stray Confirm"},
            {"target": "Global.Int16[228]", "cause": "confirm_hotspot",
             "why": "a hot-spot pickup (the player's pickup function)"},
            {"target": "Global.Byte[226]", "cause": "confirm_hotspot",
             "why": "a hot-spot pickup (the player's pickup function)"},
            {"donor": 115, "sid": 2, "tag": 3, "cause": "confirm_talk", "object": 2,
             "why": "Kupo's talk (Mognet/save/shop): a stray Confirm"},
            {"donor": 104, "sid": 7, "tag": 1, "target": "Global.Int16[469]", "ip_range": [646, 863],
             "cause": "choice", "why": "a 104 info option was chosen (e7 t1 ip646-863)"},
            {"off_route": True, "cause": "walk",
             "why": "a write off the route: S, a place outside route + end_fields; F, a field that is neither a "
                    "member whose donor is on the route nor an end field"},
        ],
        # the two concrete forbidden stores O2-KEYS proves (the patterns above name targets, not sites)
        "forbidden_sites": [
            key(105, 7, 2, 729, 175, "Global.Bit[3714]", 1, ":=", "Jack's card branch (105 e7 t2 ip729)"),
            key(105, 7, 2, 945, 391, "Global.Bit[3715]", 1, ":=", "Jack's mugging branch (105 e7 t2 ip945)"),
        ],
        "end_state": {"Global.UInt16[0]": 1155, "Global.Int16[2]": 0, "Global.UInt16[19]": 2,
                      "Global.UInt16[21]": 2, "Global.Byte[6]": 2, "Global.Byte[472]": 4, "Global.Int16[469]": 1042,
                      "Global.Bit[3717]": 1, "Global.Bit[3718]": 1},
        "regions": _regions(),
        "hotspots": _hotspots(),
        "table": _table(),
        # every O2 pick is option 0, the game's own default cursor (ETb.cs:100-103): take "default", never move it
        "choices": [
            {"donor": 103, "sc": [1000], "match": "ticket booth", "pick": "ticket booth", "once": True,
             "beat": "booth", "take": "default"},
            {"donor": 104, "sc": [1000], "match": "ticket", "pick": "ticket", "once": True, "beat": "ticket",
             "take": "default"},
            {"donor": 105, "sc": [1150], "match": "fake", "pick": "Yeah", "once": True, "beat": "fake",
             "take": "default"},
            {"donor": 105, "sc": [1151], "match": "want to", "pick": "right", "once": True, "beat": "alright",
             "take": "default"},
            {"donor": 105, "sc": [1151], "match": "someone", "pick": "clear", "once": True, "beat": "clear",
             "take": "default"},
            {"donor": 115, "sc": [1154], "match": "Once more", "pick": "understand", "once": True,
             "beat": "understand", "take": "default"},
            {"donor": None, "sc": None, "match": "want to skip", "pick": "default", "once": False, "beat": None},
        ],
        "naming": [{"donor": 116, "sc": 1155, "beat": "named"}],
        "beats": ["booth", "ticket", "fake", "alright", "clear", "understand", "named", "climbed"],
        "steps_default": {"attempts": 2, "interrupts": 1, "timeout_s": 20, "confirm_s": 4.0, "npcs": True,
                          "overlay_ok": False, "immediate": False, "settle": None, "lunge_ticks": 0,
                          "tolerance": 45, "min_depth": 40, "exit_wait_s": 8.0, "exit_slack": 40,
                          "climb": {"burst_frames": 30, "max_bursts": 80, "stall_bursts": 3}},
    }


# ======================================================================== the text rule (the lead's ruling)
def text_rule(stock: dict, shipped: dict, session_lang: str = SESSION_LANG) -> tuple:
    """The lead's ruling on the uk text mis-pick (research/o2_design.md 0.1, 6.1), one pure function O2-TEXT and
    P-TEXT share: ``(ok, lines)``.

    ``stock`` is each language's stock ``field/<block>.mes`` read through the engine's own ResourceManager path
    (:func:`stock_text_assets`), never through ``dialogue.extract_field_mes``; ``shipped`` the bytes a build or a mod
    folder ships, per language. Each shipped language reads one line:
      - byte-equal to its own stock asset: ``"<lang> ok: ..."``;
      - otherwise, the session language: ``"FAIL <lang>: ..."`` -- the session reads it;
      - otherwise, byte-equal to ANOTHER language's stock asset: ``"KNOWN-KIT-DEFECT <lang>: ships stock <other>
        ..."`` -- named and counted, never silent, never a pass by omission;
      - any other difference (or no stock asset to compare with): ``"FAIL <lang>: ..."``.
    ``ok`` is no FAIL line."""
    lines, ok = [], True
    langs = [L for L in ("us", "uk", "fr", "gr", "it", "es", "jp") if L in shipped] + \
            sorted(L for L in shipped if L not in ("us", "uk", "fr", "gr", "it", "es", "jp"))
    for L in langs:
        got, want = shipped[L], stock.get(L)
        if want is not None and got == want:
            lines.append(f"{L} ok: byte-equal to stock {L} ({_sha10(want)})")
            continue
        other = next((M for M in stock if M != L and stock[M] is not None and stock[M] == got), None)
        if want is None:
            ok = False
            lines.append(f"FAIL {L}: no stock {L} asset to compare with (ships {_sha10(got)})")
        elif L == session_lang:
            ok = False
            lines.append(f"FAIL {L}: the session language ships {_sha10(got)}"
                         + (f" (stock {other})" if other else "") + f", not stock {L} ({_sha10(want)})")
        elif other is not None:
            cause = (f"dialogue._lang_score aliases {L} to {other} (dialogue.py:374) -- the lead's kit fix"
                     if {L, other} == {"us", "uk"} else "another language's stock text: the kit's language pick")
            lines.append(f"KNOWN-KIT-DEFECT {L}: ships stock {other} ({_sha10(got)}; stock {L} {_sha10(want)}): "
                         f"{cause}")
        else:
            ok = False
            lines.append(f"FAIL {L}: ships {_sha10(got)}, which is no language's stock asset (stock {L} "
                         f"{_sha10(want)})")
    return ok, lines


def text_detail(lines: list, *, where: str = "") -> str:
    """A text check's detail, one line: the KNOWN-KIT-DEFECT count first, then every non-ok line, " | "-separated
    (:func:`defect_lines` reads them back)."""
    defects = [ln for ln in lines if ln.startswith("KNOWN-KIT-DEFECT")]
    fails = [ln for ln in lines if ln.startswith("FAIL")]
    equal = [ln for ln in lines if " ok: " in ln]
    head = (f"{where}KNOWN-KIT-DEFECT {len(defects)}, FAIL {len(fails)}, {len(equal)} byte-equal of "
            f"{len(lines)} languages")
    return " | ".join([head, *fails, *defects])


def defect_lines(detail: str) -> list:
    """The ``KNOWN-KIT-DEFECT <lang>: ...`` lines inside a text check's detail (:func:`text_detail`)."""
    return [seg for seg in str(detail).split(" | ") if re.match(r"KNOWN-KIT-DEFECT [a-z]{2}: ", seg)]


_STOCK_TEXT: dict = {}


def stock_text_assets(block: int = TEXT_BLOCK, game=None) -> dict:
    """``{lang: bytes | None}``: each language's stock ``field/<block>.mes`` read the way the ENGINE reads it -- the
    ResourceManager's ``m_Container`` entry ``embeddedasset/text/<lang>/field/<block>.mes`` in ``mainData``, its PPtr
    resolved into ``resources.assets`` (battle.extract._read_battle_text's read, for field text). Read-only; cached
    per block. Never ``dialogue.extract_field_mes*``: that is the tool whose us/uk pick is under test."""
    if block in _STOCK_TEXT:
        return _STOCK_TEXT[block]
    from ff9mapkit import config
    from ff9mapkit.battle.extract import _ff9_data_dir, _unitypy
    from ff9mapkit.extract import _raw_bytes
    unitypy = _unitypy()
    d = _ff9_data_dir(game)
    env = unitypy.load(str(d / "mainData"), str(d / "resources.assets"))
    rm = next((o.read() for o in env.objects
               if getattr(getattr(o, "type", None), "name", "") == "ResourceManager"), None)
    if rm is None:
        raise RuntimeError("no ResourceManager in mainData: the engine's text paths cannot be read")
    index = {str(p).lower(): ptr for p, ptr in rm.m_Container}
    out = {}
    for L in config.LANGS:
        ptr = index.get(f"embeddedasset/text/{L}/field/{block}.mes")
        out[L] = _raw_bytes(ptr.read()) if ptr is not None else None
    _STOCK_TEXT[block] = out
    return out


def shipped_text(root, block: int = TEXT_BLOCK) -> dict:
    """``{lang: bytes}`` of every ``FF9_Data/embeddedasset/text/<lang>/field/<block>.mes`` a build or mod folder
    ships (only the languages present)."""
    from ff9mapkit import config
    out = {}
    for L in config.LANGS:
        p = Path(root) / "FF9_Data" / "embeddedasset" / "text" / L / "field" / f"{block}.mes"
        if p.is_file():
            out[L] = p.read_bytes()
    return out


# ======================================================================== P-LANG
def ini_force_language(ini_text: str | None) -> int:
    """Memoria.ini ``[VoiceActing] ForceLanguage`` as the engine takes it: the LAST assignment wins
    (IniFile.Init), a missing or unreadable value is its default -1, and anything outside 0..6 reads as -1
    (Configuration/Access/VoiceActing.cs:16)."""
    value, section = None, None
    for line in (ini_text or "").splitlines():
        t = line.strip()
        if not t or t[0] in ";#":
            continue
        if t.startswith("[") and "]" in t:
            section = t[1:t.index("]")].strip().lower()
            continue
        if section == "voiceacting" and "=" in t:
            k, v = t.split("=", 1)
            if k.strip().lower() == "forcelanguage":
                value = v.strip()
    try:
        n = int(value) if value is not None else -1
    except ValueError:
        n = -1
    return n if 0 <= n <= 6 else -1


def log_language(log_text: str | None) -> tuple:
    """``(the LAST "Updating text localization [<name>]" name, how many there were)`` in a Memoria.log
    (FF9TextTool.cs:395): the language this launch's text was last loaded in."""
    names = re.findall(r"Updating text localization \[([^\]]*)\]", log_text or "")
    return (names[-1] if names else None), len(names)


def p_lang(log_text: str | None, ini_text: str | None, want: str = ENGINE_LANG[SESSION_LANG]) -> tuple:
    """P-LANG as one pure function (research/o2_design.md 6.2): ``(ok, detail, {"log", "force"})``. The launch's
    Memoria.log (rewritten at launch) must name ``want`` as its LAST localization line, and ``ForceLanguage`` must be
    -1 (the in-game setting) or 0 (English(US))."""
    name, n = log_language(log_text)
    force = ini_force_language(ini_text)
    ok = name == want and force in (-1, 0)
    detail = (f"last localization line {name!r} (of {n}), want {want!r}; [VoiceActing] ForceLanguage {force}"
              + ("" if force in (-1, 0) else " (forces another language)"))
    return ok, detail, {"log": name, "force": force}


def install_lang(game: Path = GAME) -> dict:
    """``{"log", "force"}`` of the install as it stands: the newest Memoria.log (the game root's or x64's --
    Session.engine_log's rule) and Memoria.ini."""
    logs = [p for p in (Path(game) / "Memoria.log", Path(game) / "x64" / "Memoria.log") if p.is_file()]
    log = max(logs, key=lambda p: p.stat().st_mtime) if logs else None
    log_text = log.read_text(encoding="utf-8", errors="replace") if log else None
    try:
        ini_text = (Path(game) / "Memoria.ini").read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        ini_text = None
    return p_lang(log_text, ini_text)[2]


# ======================================================================== pure helpers the checks share
def span_rows(rows: list, span) -> list:
    """The ``w`` rows whose bytes overlap ``span`` -- any width, target, mode or source (LADDER's and CHAIN's byte-span
    selector: a store to SC through another width is counted too)."""
    span = set(span)
    return [x for x in rows if x.k == "w" and set(x.span) & span]


def span_sequence(rows: list, rk: dict, span, want: list, first_old: int) -> list:
    """The problems with one run's writes over the bytes ``span`` against the registered sequence ``want``
    (research/o2_design.md 5.3 LADDER / CHAIN): exactly those keys, in line order, each row's ``old`` the previous
    rung (the first ``first_old``). Each row is read on its JOINED key (``rk``: :func:`segment_trace.row_keys`), never
    its raw ip; a row with no key fails by name, and so does a ``c`` row over those bytes (a suppressed repeat)."""
    span = set(span)
    bad = []
    for x in rows:
        if x.k == "c" and set(x.span) & span:
            bad.append(f"line {x.line}: {x.n} suppressed store(s) of {x.target} at {x.fld} e{x.sid} t{x.tag} "
                       f"ip{x.ip} (a repeat the engine only counted)")
    sel = span_rows(rows, span)
    keys = []
    for x in sel:
        k = key_of(rk, x)
        if k is None:
            bad.append(f"line {x.line}: {x.target}={x.new} at {x.fld} e{x.sid} t{x.tag} ip{x.ip} has no key "
                       f"(a join failure, a harness poke or a masked site)")
        keys.append(k)
    wk = [wkey(k) for k in want]
    if keys != wk:
        got = [f"{k.donor}:{k.target}={k.value}" if k is not None else "?" for k in keys]
        at = next((i for i, (a, b) in enumerate(zip(keys, wk)) if a != b), min(len(keys), len(wk)))
        bad.append(f"{len(keys)} writes, want {len(wk)}; first difference at #{at + 1}: got "
                   f"{got[at] if at < len(got) else 'nothing'}, want "
                   f"{label(want[at]) if at < len(want) else 'nothing'}")
    prev = first_old
    for x, k in zip(sel, want):
        if x.old != prev:
            bad.append(f"line {x.line}: {x.target} old {x.old}, want {prev} (the previous rung)")
        prev = k["value"]
    return bad


def fold_pages(pages: list, timed=()) -> list:
    """A transcript for comparing: the timed (self-closing) pages removed, consecutive duplicates collapsed (O1's
    lesson: self-closing windows stack and are sampled at varying moments)."""
    out = []
    skip = set(timed or ())
    for i, p in enumerate(pages or ()):
        if i in skip or (out and out[-1] == p):
            continue
        out.append(p)
    return out


def _row_text(x) -> str:
    return f"{x.fld} e{x.sid} t{x.tag} ip{x.ip} {x.target}={x.new}"


def _fmt_key(k: T.WriteKey) -> str:
    return f"{k.donor} e{k.sid} t{k.tag} {k.off:+d} {k.target}={k.value}" + ("" if k.aligned else " [unaligned]")


def trace_summary(rows: list, pred: dict, *, side: str = "S", start_place: int | None = None, end_fields=None,
                  stock=None, scripts=None, log: list | None = None) -> dict:
    """One trace, summarised for a reader (research/o2_design.md 7.2; the rehearsal report and the dry run): the
    run cut at its start row (``start_place``, default the predictions' start) and its end (``end_fields``), then
    the SC sequence and the FieldEntrance sequence (raw rows over their bytes, each with its joined key), every
    registered key present or absent, every UNREGISTERED key, the residue before and after the start, the masked
    counts, the join failures, the two watched raw sites, and -- given the run's driver ``log`` -- its forbidden
    hits with their backing."""
    members = members_of(pred) if side == "F" else {}
    sp = start_place if start_place is not None else place(pred["start"][side], members)
    ends = list(end_fields if end_fields is not None else (pred.get("end_fields") or [pred["end_field"]]))
    kept, at, pre = cut_at_start(rows, sp, members)
    kept, end = cut_at_end(kept, ends, members)
    stock = stock or T.stock_script_source()
    d = T.digest("summary", kept, scripts=scripts or stock, donor_scripts=stock, members=members or None)
    rk = row_keys(d)

    def seq(span) -> list:
        out = []
        for x in span_rows(kept, span):
            k = key_of(rk, x)
            out.append({"line": x.line, "f": x.f, "fld": x.fld, "site": f"e{x.sid} t{x.tag} ip{x.ip}",
                        "target": x.target, "old": x.old, "new": x.new, "key": None if k is None else _fmt_key(k)})
        return out
    registered, reg = {}, set()
    for name in ("ladder", "chain", "writes", "start_dependent", "noise", "forbidden_sites"):
        for k in pred.get(name) or ():
            wk = wkey(k)
            reg.add(wk)
            registered.setdefault(name, []).append({"what": label(k), "present": wk in d.keys or wk in d.seam_keys})
    watched = {name: any(x.k == "w" and place(x.fld, members) == dn and (x.sid, x.tag, x.ip) == (sid, tag, ip)
                         for x in kept)
               for name, (dn, sid, tag, ip) in WATCH_SITES.items()}
    hits = []
    if log is not None:
        for h in SD.forbidden_hits(kept, pred, members, sp, end_fields=ends):
            b = SD.backing(h, log, pred)
            hits.append({"row": SD._hit_row(h), "why": h["why"], "cause": h["cause"], "hotspot": h.get("hotspot"),
                         "backed": b is not None, "by": None if b is None else b["what"]})
    return {"start": at, "end": end, "rows": len(kept),
            "residue_before": [[x.fld, x.byte, x.old, x.new] for x in pre if x.k == "r"],
            "pre_other": [_row_text(x) for x in pre if x.k == "w"],
            "residue_after": [[x.fld, x.byte, x.old, x.new, bool(T.noise_regions(x))] for x in kept if x.k == "r"],
            "sc": seq(pred.get("sc_bytes") or (0, 1)), "entrance": seq(pred.get("entrance_bytes") or (2, 3)),
            "registered": registered,
            "unregistered": [_fmt_key(k) for k in sorted(d.keys, key=T.WriteKey.sort_key) if k not in reg],
            "seam_keys": [_fmt_key(k) for k in sorted(d.seam_keys, key=T.WriteKey.sort_key)],
            "masked": dict(d.masked), "residue_masked": d.residue_masked,
            "failures": [[_row_text(r), why[:160]] for r, why in d.failures], "watched": watched, "forbidden": hits}


# ======================================================================== O2 on the shared engine
class O2Segment(ST.Segment):
    """O2 on :class:`segment_trace.Segment` (research/o2_design.md 1.5): its constants and check texts, the draft
    predictions, the offline checks (O2-TEXT, O2-KEYS extended, O2-REGIONS, O2-GOALS), the preflight extras (P-TEXT,
    P-RECOVERY) and in-game capabilities (P-OBJECTS, P-LANG), the fingerprint extras, and O2's analysis: the all-run
    checks (O2-FORBIDDEN, O2-VOID-ASYM), the core checks, the extra VOID reasons and the report sections. The
    session loop, the cuts, the digest, the comparison and the verdict are the shared engine's."""

    tag = "O2"
    doc = _MODULE_DOC
    predictions = PREDICTIONS
    manifest = MANIFEST
    session_file = SESSION_FILE
    report_file = REPORT_FILE
    chain_dir = CHAIN_DIR
    build_dir = BUILD_DIR
    accept_us_build = False               # the build is the own-language remap, all 126 files (0.2 #1)
    recovery = 4600
    core_ids = ("START", "LADDER", "CHAIN", "RESIDUE", "WRITES", "NULL", "STABLE", "SEAM", "MASKED", "STATE",
                "JOIN")
    titles = {
        "P-CAP": "P-CAP: the engine advertises the story trace at proto 1",
        "P-OBJECTS": "P-OBJECTS: the engine publishes the field's objects (s89): npcs, V6 and the presses' near "
                     "evidence read them",
        "P-LANG": "P-LANG: the running game's text is English(US), the language the keys, joins and text were "
                  "checked in",
        "P-MANIFEST": "P-MANIFEST: the frozen members are the deployed chain's (o2_forks.json, deployed)",
        "P-DEPLOY": "P-DEPLOY: every member registered once under its name, and mapped once to its donor",
        "P-EB": "P-EB: every member's live .eb (7 languages) is the offline-checked build's",
        "P-FLOOR": "P-FLOOR: every member's deployed walkmesh is its donor's",
        "P-STOCK": "P-STOCK: no mod folder overrides stock 100-106, 115, 116 or 61",
        "P-TEXT": "P-TEXT: every mod folder's text block 33 is each language's stock asset, read by its resource "
                  "path (another language's copy a named KNOWN-KIT-DEFECT)",
        "P-RECOVERY": "P-RECOVERY: the recovery field 4600 is registered in a mod folder",
        "BUILD": "O2-BUILD: every member's .eb, in all 7 languages, is its donor's in that language with only in-chain "
                 "Field() literals remapped",
        "TEXT": "O2-TEXT: the build's text block 33 is each language's stock asset, read by its resource path (the "
                "session language exactly; another language's copy a named KNOWN-KIT-DEFECT)",
        "KEYS": "O2-KEYS: every registered key is a store of its variable at its ip in the donor's stock bytes, its op "
                "in the statement, its value computed",
        "REGIONS": "O2-REGIONS: every frozen region and hot-spot is the stock bytes' own, each role as registered, and "
                   "every gateway of a route field is a registered exit",
        "GOALS": "O2-GOALS: every step is one its executor can run, its goal on the floor, in its target (or past its "
                 "line), clear of every hot-spot, with a route from its start; every crossing leads where the route's "
                 "order goes next",
        "FROZEN": "O2-FROZEN: the predictions are the file the session recorded, unchanged",
        "COVER": "O2-COVER: at least {min_covered} covered runs a side",
        "FORBIDDEN": "O2-FORBIDDEN: no run carries a forbidden write its own driver log does not explain",
        "VOID-ASYM": "O2-VOID-ASYM: no game-caused VOID class on one side only, and no side VOID in one class in "
                     "every run",
        "START": "O2-START: every covered run starts at 100's Main_Init after only the warp's own residue",
        "LADDER": "O2-LADDER: bytes 0-1 (SC) carry exactly the six rungs, in order, each from the last",
        "CHAIN": "O2-CHAIN: bytes 2-3 (FieldEntrance) carry exactly the chain, in order, each from the last",
        "RESIDUE": "O2-RESIDUE: no unmasked residue after the start beyond the registered",
        "WRITES": "O2-WRITES: every covered run of both sides writes every registered story key",
        "NULL": "O2-NULL: STOCK ONLY and FORK ONLY are empty outside the registered noise",
        "STABLE": "O2-STABLE: no key outside the registered noise is written in some runs of a side and not others",
        "SEAM": "O2-SEAM: the fork side never left its members before member(116)'s Field(61)",
        "MASKED": "O2-MASKED: the story-noise regions written are the same on both sides",
        "STATE": "O2-STATE: the state handed to 61 is the same: each target's emitted write history in order (its "
                 "suppressed stores as a set), and the end state read live",
        "JOIN": "O2-JOIN: every script row joins a store in the bytes its field ran",
        "THROW": "O2-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
    }

    def __init__(self):
        self._run_dir: Path | None = None

    # -- the predictions --------------------------------------------------------------------------------------
    def draft(self) -> dict:
        return draft_predictions()

    def current(self, path=None) -> tuple:
        """``(predictions, what)`` for the offline check and the preflight: ``path``, else the frozen file, else the
        DRAFT -- the offline check must be green before any rehearsal ends in a freeze, so it reads the draft until
        the lead freezes it."""
        if path is not None:
            return self.load(path)[0], str(path)
        if Path(self.predictions).is_file():
            pred, sha = self.load()
            return pred, f"{Path(self.predictions).name} (frozen, sha {sha[:8]})"
        return self.draft(), f"the draft ({Path(self.predictions).name} is not frozen yet)"

    # -- offline ------------------------------------------------------------------------------------------------
    def offline_extra(self, pred: dict, build=None) -> list:
        stock = self.stock_source()
        return [self.text_check(pred, build), self.regions_check(pred, stock), self.goals_check(pred)]

    def text_check(self, pred: dict, build=None, stock_text=None) -> tuple:
        """O2-TEXT (6.1): the build's ``field/<block>.mes`` per language against each language's stock asset read by
        its ResourceManager path, judged by :func:`text_rule`. The build must ship every language (it writes all 7)."""
        from ff9mapkit import config
        block = int(pred.get("text_block", TEXT_BLOCK))
        stock = stock_text if stock_text is not None else stock_text_assets(block)
        shipped = shipped_text(build or self.build_dir, block)
        ok, lines = text_rule(stock, shipped, pred.get("lang", SESSION_LANG))
        missing = [L for L in config.LANGS if L not in shipped]
        lines += [f"FAIL {L}: the build ships no {L}/field/{block}.mes" for L in missing]
        return ok and not missing, self.title("TEXT"), text_detail(lines)

    def keys_check(self, pred: dict, stock, lists=None) -> tuple:
        """O2-KEYS (6.1): every key of the ladder, the chain, the writes, the start-dependent keys, the noise,
        ``start_first`` and the two concrete forbidden sites is a store of its variable at ``(sid, tag, ip)`` with its
        function offset ``off``; its MANDATORY ``op`` is the statement's, anchored on the target (``const(c) B_LET``,
        ``B_OR_LET``, ``B_AND_LET``, ``B_POST_PLUS``); a ``:=`` value is the constant, a compound value is COMPUTED from
        its ``prior`` (a registered key's value, or 0 for ``newgame0``) and the constant -- never trusted as typed;
        and no key but ``start_first`` lies in the story-noise mask (``start_first``'s Bit[191] is boot_scratch:
        O2-START reads it on the raw rows)."""
        keys = [(name, k) for name in ("ladder", "chain", "writes", "start_dependent", "noise", "forbidden_sites")
                for k in pred.get(name) or ()] + [("start_first", pred["start_first"])]
        by_site = {site_of(k): k for _name, k in keys}
        bad, sites, computed = [], set(), 0
        for name, k in keys:
            lab = f"{name}: {label(k)}"
            sites.add(site_of(k))
            width, index = k["target"].split(".", 1)[1].rstrip("]").split("[")
            bit = int(index) if width in T.BIT_WIDTHS else -1
            row = T.Row(k="w", f=0, p=0, m=k["m"], fld=k["donor"], don=k["donor"], sc=0, src=k["src"], sid=k["sid"],
                        uid=0, lvl=0, ip=k["ip"], tag=k["tag"], add=0, byte=int(index) >> 3 if bit >= 0 else int(index),
                        width=width, bit=bit, old=0, new=k["value"], same=0)
            idx = stock(k["donor"])
            j = idx.join(row) if idx is not None else None
            if j is None or j.status != "store" or j.tag != k["tag"] or j.rel != k["off"]:
                bad.append(f"{lab}: {None if j is None else (j.status, j.tag, j.rel, j.reason)}")
                continue
            op = k.get("op")
            text = j.text or ""
            anchor = re.escape(k["target"])
            if op == ":=":
                m = re.search(anchor + r" const\((-?\d+)\) B_LET\b", text)
                got = None if m is None else self._as_width(width, int(m.group(1)))
            elif op in ("|=", "&="):
                m = re.search(anchor + r" const\((-?\d+)\) " + ("B_OR_LET" if op == "|=" else "B_AND_LET"), text)
                prior = self._prior_value(k, by_site)
                if m is None or prior is None:
                    got = None
                else:
                    c = self._as_width(width, int(m.group(1)))
                    got = (prior | c) if op == "|=" else (prior & c)
                    computed += 1
            elif op == "++":
                m = re.search(anchor + r" B_POST_PLUS\b", text)
                prior = self._prior_value(k, by_site)
                got = None if m is None or prior is None else prior + 1
                computed += 1 if got is not None else 0
            else:
                bad.append(f"{lab}: op {op!r} is not one of :=, |=, &=, ++ (op is mandatory)")
                continue
            if m is None:
                bad.append(f"{lab}: the statement at +{k['off']} is not {k['target']} {op} ...: {text[:100]!r}")
            elif got is None:
                bad.append(f"{lab}: {op} names no registered prior ({k.get('prior')!r})")
            elif got != k["value"]:
                bad.append(f"{lab}: the bytes give {got}, the key says {k['value']} ({text[:80]!r})")
            if name != "start_first" and T.noise_regions(row):
                bad.append(f"{lab}: {k['target']} lies in the story-noise mask {T.noise_regions(row)}")
        return (not bad, self.title("KEYS"),
                "; ".join(bad[:6]) or f"{len(sites)} sites ({len(keys)} keys), every op in its statement, "
                                      f"{computed} compound values computed from their priors, none masked "
                                      f"(start_first's Bit[191] is boot_scratch: O2-START reads it raw)")

    @staticmethod
    def _as_width(width: str, c: int) -> int:
        """A statement's constant as the variable reads it back (a const is an unsigned operand)."""
        if width in ("Int16",):
            return _s16(c)
        if width in ("SByte",):
            return ((c + 0x80) & 0xFF) - 0x80
        if width in ("Byte",):
            return c & 0xFF
        if width in ("UInt16",):
            return c & 0xFFFF
        return c

    @staticmethod
    def _prior_value(k: dict, by_site: dict):
        p = k.get("prior")
        if p == "newgame0":
            return 0
        other = by_site.get(p) if isinstance(p, str) else None
        return None if other is None or other is k else other["value"]

    # -- O2-REGIONS ---------------------------------------------------------------------------------------------
    @staticmethod
    def _items(idx, sid: int, tag: int) -> list:
        """``[(ip, rel, text)]`` of entry ``sid``'s function ``tag`` as eb-src prints it (ip entry-relative)."""
        from ff9mapkit.eb import cmdasm
        fa = idx.function(sid, tag)
        if fa is None:
            return []
        e, _f, start, end = fa
        return [(start + o - e.abs_start, o, t) for o, t in cmdasm.disassemble_items(idx.data, start, end)
                if o is not None]

    @staticmethod
    def _first_region(idx, sid: int):
        from ff9mapkit.eventscan import SETREGION_OP, _region_points
        e = idx.eb.entries[sid] if 0 <= sid < len(idx.eb.entries) else None
        if e is None or e.empty:
            return None
        for f in e.funcs:
            for ins in idx.eb.instrs(f):
                if ins.op == SETREGION_OP:
                    pts = _region_points(ins)
                    if len(pts) >= 3:
                        return [list(p) for p in pts]
        return None

    @staticmethod
    def hotspot_census(idx) -> dict:
        """``{sid: {"tag", "x", "z", "n"}}``: every function that stores its own position into ``Int16[220]`` /
        ``[222]`` as constants (0.2 #9) and compares ``Instance.Int24[0] const(n) B_LT``."""
        from ff9mapkit.eb import cmdasm
        rx = re.compile(r"Global\.Int16\[220\] const\((\d+)\) B_LET")
        rz = re.compile(r"Global\.Int16\[222\] const\((\d+)\) B_LET")
        rn = re.compile(r"Instance\.Int24\[0\] const\((\d+)\) B_LT")
        out = {}
        for e in idx.eb.entries:
            if e.empty:
                continue
            for f in e.funcs:
                start, end = f.abs_start, idx._end(e, f)
                texts = [t for o, t in cmdasm.disassemble_items(idx.data, start, end) if o is not None]
                xs = [int(m.group(1)) for t in texts for m in [rx.search(t)] if m]
                zs = [int(m.group(1)) for t in texts for m in [rz.search(t)] if m]
                ns = [int(m.group(1)) for t in texts for m in [rn.search(t)] if m]
                if xs or zs:
                    out[e.index] = {"tag": f.tag, "x": _s16(xs[0]) if xs else None, "z": _s16(zs[0]) if zs else None,
                                    "n": ns[0] if ns else None}
        return out

    def _dormant_problems(self, idx, sid: int, entrances) -> list:
        """A dormant region (115.e14): Main_Init's entrance SWITCH (the one on ``Global.Int16[2]``) sends every route
        entrance to a straight-line case block with no ``InitRegion(sid)``, the join after them holds none, and every
        ``InitRegion(sid)`` of the whole script lies in the SWITCH's default block."""
        items = self._items(idx, 0, 0)
        bad = []
        k = next((i for i, (_ip, _rel, t) in enumerate(items) if t.startswith("SWITCH(")
                  and i > 0 and items[i - 1][2] == "SET({Global.Int16[2] B_EXPR_END})"), None)
        if k is None:
            return ["Main_Init has no SWITCH on Global.Int16[2]"]
        m = re.match(r"SWITCH\((\d+), L(\d+)((?:, L\d+)*)\)", items[k][2])
        if m is None:
            return [f"the SWITCH does not parse: {items[k][2]!r}"]
        base, default = int(m.group(1)), int(m.group(2))
        cases = [int(x) for x in re.findall(r"L(\d+)", m.group(3))]
        by_rel = {rel: i for i, (_ip, rel, _t) in enumerate(items)}
        want = re.compile(rf"^InitRegion\({sid}\b")

        def block(rel):
            """The straight-line block from ``rel``: its texts and the label its JMP goes to."""
            i, texts = by_rel.get(rel), []
            while i is not None and i < len(items):
                t = items[i][2]
                if t.startswith(("JMP_IF", "SWITCH")):
                    return texts, None, f"a branch inside the block at L{items[i][1]}"
                texts.append(t)
                if t.startswith("JMP("):
                    return texts, int(re.match(r"JMP\(L(\d+)\)", t).group(1)), None
                if t.startswith("RET"):
                    return texts, None, None
                i += 1
            return texts, None, None
        joins = set()
        for ent in entrances:
            n = ent - base
            target = cases[n] if 0 <= n < len(cases) else default
            texts, join, why = block(target)
            if why:
                bad.append(f"entrance {ent}: {why}")
            if any(want.match(t) for t in texts):
                bad.append(f"entrance {ent}: InitRegion({sid}) in its case block (L{target})")
            if join is not None:
                joins.add(join)
        for join in joins:
            i = by_rel.get(join)
            tail = [t for _ip, _rel, t in items[i:]] if i is not None else []
            if any(want.match(t) for t in tail):
                bad.append(f"InitRegion({sid}) after the join L{join}, on every entrance's path")
        dtexts, _j, _w = block(default)
        drange = set()
        i = by_rel.get(default)
        while i is not None and i < len(items):
            drange.add(items[i][1])
            if items[i][2].startswith(("JMP(", "RET")):
                break
            i += 1
        for e in idx.eb.entries:
            if e.empty:
                continue
            for f in e.funcs:
                for ip, rel, t in self._items(idx, e.index, f.tag):
                    if want.match(t) and not (e.index == 0 and f.tag == 0 and rel in drange):
                        bad.append(f"InitRegion({sid}) at e{e.index} t{f.tag} ip{ip}, outside Main_Init's default "
                                   f"block")
        return bad

    def regions_check(self, pred: dict, stock) -> tuple:
        """O2-REGIONS (6.1): every frozen region's points are the first SetRegion of its (donor, entry) in the stock
        bytes, and its role holds -- ``exit``: scan_gateways has its (to, entrance) and its facing gate as frozen;
        ``walkin``: its tag 2 opens with the ``lo <= SC < hi`` guard before it takes control; ``dormant``: no
        InitRegion on Main_Init's path for the route's entrances; ``confirm``: its tag 3 holds its registered
        statement; ``benign``: no gEventGlobal store and no Field() anywhere in it, no DisableMove in its tag 2.
        Every frozen hot-spot is its tag 1's own (x, z, n, and reach = 32 sqrt n), and the census of the route
        fields finds no hot-spot the predictions lack -- nor any GATEWAY (scan_gateways) they do not register as an
        exit: the driver's landing judge (segment_drive.exit_regions) reads a loss of control in a registered exit as
        that door's, so the list must be complete."""
        from ff9mapkit.eventscan import FIELD_OP, scan_gateways
        bad, n, ng = [], 0, 0
        gws = {}
        for key, reg in sorted(pred["regions"].items()):
            n += 1
            donor, e = int(key.split(".")[0]), int(key.split(".e")[1])
            idx = stock(donor)
            if idx is None:
                bad.append(f"{key}: no stock script for {donor}")
                continue
            pts = self._first_region(idx, e)
            if pts != reg["points"]:
                bad.append(f"{key}: the bytes' first SetRegion is {pts}, frozen {reg['points']}")
            role = reg["role"]
            if role == "exit":
                rows = gws.setdefault(donor, scan_gateways(idx.data))
                hit = [g for g in rows if g["entry"] == e]
                if not any(g["to"] == reg["to"] and g["entrance"] == reg["entrance"]
                           and g["face_gate"] == reg.get("face_gate") for g in hit):
                    bad.append(f"{key}: scan_gateways gives {[(g['to'], g['entrance'], g['face_gate']) for g in hit]}, "
                               f"frozen ({reg['to']}, {reg['entrance']}, {reg.get('face_gate')})")
            elif role == "walkin":
                lo, hi = reg["live"]
                guard = f"Global.UInt16[0] const({lo}) B_GE Global.UInt16[0] const({hi}) B_LT B_ANDAND"
                texts = [t for _ip, _rel, t in self._items(idx, e, 2)]
                gi = next((i for i, t in enumerate(texts) if guard in t), None)
                di = next((i for i, t in enumerate(texts) if t.startswith("DisableMove")), None)
                first_sc = next((i for i, t in enumerate(texts) if "Global.UInt16[0]" in t), None)
                if gi is None or gi != first_sc or di is None or not gi < di \
                        or not texts[gi + 1].startswith("JMP_IFNOT("):
                    bad.append(f"{key}: its tag 2 does not open with the guard {lo} <= SC < {hi} before DisableMove")
            elif role == "dormant":
                bad += [f"{key}: {p}" for p in self._dormant_problems(idx, e, reg["entrances"])]
            elif role == "confirm":
                t3 = {ip: t for ip, _rel, t in self._items(idx, e, 3)}
                want = reg["tag3"]
                if not t3 or want["does"] not in t3.get(want["ip"], ""):
                    bad.append(f"{key}: its tag 3 at ip{want['ip']} is {t3.get(want['ip'])!r}, not {want['does']!r}")
            elif role == "benign":
                ent = idx.eb.entries[e]
                for f in ent.funcs:
                    for ins in idx.eb.instrs(f):
                        if ins.op == FIELD_OP or any(s[0] == "global" for s in T.instruction_stores(idx.data, ins)):
                            bad.append(f"{key}: e{e} t{f.tag} stores to gEventGlobal or warps (+{ins.off})")
                if any(t.startswith("DisableMove") for _ip, _rel, t in self._items(idx, e, 2)):
                    bad.append(f"{key}: its tag 2 takes control")
            else:
                bad.append(f"{key}: role {role!r} is not one of exit, walkin, dormant, confirm, benign")
        nh = 0
        for donor in pred["route"]:
            idx = stock(donor)
            census = self.hotspot_census(idx) if idx is not None else {}
            frozen = {h["sid"]: h for h in SD.hotspots_of(pred, donor)}
            for sid, got in sorted(census.items()):
                h = frozen.get(sid)
                if h is None:
                    bad.append(f"hot-spot {donor} e{sid} ({got['x']}, {got['z']}) n {got['n']}: in the bytes, not in "
                               f"the predictions")
                    continue
                nh += 1
                if (got["tag"], got["x"], got["z"], got["n"]) != (1, h["x"], h["z"], h["n"]) \
                        or h.get("reach", int(32 * math.sqrt(h["n"]))) != int(32 * math.sqrt(h["n"])):
                    bad.append(f"hot-spot {donor} e{sid}: the bytes give t{got['tag']} ({got['x']}, {got['z']}) n "
                               f"{got['n']}, frozen ({h['x']}, {h['z']}) n {h['n']} reach {h.get('reach')}")
            for sid in sorted(set(frozen) - set(census)):
                bad.append(f"hot-spot {donor} e{sid}: frozen, but no such hot-spot in the bytes")
            if idx is None:
                continue
            if donor not in gws:
                gws[donor] = scan_gateways(idx.data)
            for gw in gws[donor]:
                ng += 1
                key = f"{donor}.e{gw['entry']}"
                if (pred["regions"].get(key) or {}).get("role") != "exit":
                    bad.append(f"{key}: a gateway (-> {gw['to']}, entrance {gw['entrance']}) in the bytes, not "
                               f"registered as an exit")
        return (not bad, self.title("REGIONS"),
                "; ".join(bad[:6]) or f"{n} regions, {nh} hot-spots, {ng} gateways all registered, every role as "
                                      f"registered")

    # -- O2-GOALS -----------------------------------------------------------------------------------------------
    def goals_check(self, pred: dict, walkmesh=None) -> tuple:
        """O2-GOALS (6.1): for every table step, on the donor's floor as the player walks it with the step's closed
        triangles (H5): the goal is on the floor at least COLLISION_RADIUS_W from a wall; a ``target`` step's goal is
        inside the target (IsInQuad) at depth >= 80, a confirm's ``depth - tolerance >= min_depth``; an ``until``
        step's goal satisfies its predicate; the goal and the step's ``start`` stand farther than reach + tolerance +
        64 from every hot-spot of the field; and route_avoiding finds a route from ``start`` to the goal round the
        step's ``avoid`` set. ``walkmesh(donor)`` is the raw mesh (default: the install's).

        Before any of it, every step must be one its executor can run (segment_drive.step_of: a malformed step is a
        FAIL naming it, never a run that dies mid-walk), and the table must agree with the route's ORDER the driver's
        rule 2 holds each visit to: ``visits`` (default ``route``) starts at the start place and lies on the route, and
        every crossing's ``to`` is where the order goes next from its place (the last visit's next is an end field)."""
        from ff9mapkit import extract
        from ff9mapkit.content import pathfind
        from ff9mapkit.scene import cam
        walkmesh = walkmesh or extract.stock_walkmesh
        radius = float(cam.COLLISION_RADIUS_W)
        bad, lines, n, raws = [], [], 0, {}
        order = list(pred.get("visits") or pred["route"])
        ends = list(pred.get("end_fields") or [pred["end_field"]])
        if not order or order[0] != pred["start"]["S"] or any(p not in pred["route"] for p in order):
            bad.append(f"visits {order}: not a walk on the route {pred['route']} from the start place "
                       f"{pred['start']['S']}")
        nexts = set(zip(order, order[1:])) | {(order[-1], e) for e in ends if order}
        for c in pred["table"]:
            donor = c["donor"]
            raw = raws.setdefault(donor, walkmesh(donor))
            for i, s0 in enumerate(c["steps"]):
                n += 1
                lab = f"({donor}, {c['sc']}) #{i + 1}"
                try:
                    s = SD.step_of(pred, s0)
                except ValueError as err:
                    bad.append(f"{lab}: {err}")
                    continue
                if s["kind"] in ("cross", "leave_now") and (donor, s["to"]) not in nexts:
                    bad.append(f"{lab}: its crossing leads to {s['to']}, where the route's order {order} never goes "
                               f"next from {donor}")
                wm = pathfind.PlayerWalkmesh(raw, closed=SD.closed_tris(pred, s, raw))
                gx, gz = (float(v) for v in s["goal"])
                start = s.get("start")
                if start is None:
                    bad.append(f"{lab}: no start")
                    continue
                sx, sz = (float(v) for v in start)
                wall = wm.distance_to_boundary(gx, gz) if wm.point_on_walkmesh(gx, gz) is not None else None
                if wall is None or wall < radius:
                    bad.append(f"{lab}: goal ({gx:.0f}, {gz:.0f}) {'off the floor' if wall is None else f'{wall:.0f}u from a wall'}")
                depth = None
                if s.get("target"):
                    depth = SD.depth_in(SD.region(pred, s["target"])["points"], gx, gz)
                    if depth is None or depth < radius:
                        bad.append(f"{lab}: goal depth {depth} in {s['target']} (want >= {radius:.0f})")
                    elif s["kind"] == "confirm" and depth - float(s["tolerance"]) < float(s["min_depth"]):
                        bad.append(f"{lab}: depth {depth:.0f} - tolerance {s['tolerance']} < min_depth "
                                   f"{s['min_depth']}")
                elif s.get("until") is not None and not SD.until_ok(s["until"], gx, gz):
                    bad.append(f"{lab}: goal ({gx:.0f}, {gz:.0f}) fails its until {s['until']}")
                clear = None
                for h in SD.hotspots_of(pred, donor):
                    for px, pz in ((gx, gz), (sx, sz)):
                        d = math.hypot(px - h["x"], pz - h["z"]) - SD.hotspot_reach(h)
                        clear = d if clear is None else min(clear, d)
                        if d <= float(s["tolerance"]) + SD.HOTSPOT_SLACK:
                            bad.append(f"{lab}: ({px:.0f}, {pz:.0f}) is {d:.0f}u beyond hot-spot e{h['sid']}'s reach")
                route = pathfind.route_avoiding(wm, (sx, sz), (gx, gz), SD.polys(pred, s.get("avoid")),
                                                leave_wall=True)
                if route is None:
                    bad.append(f"{lab}: no route from ({sx:.0f}, {sz:.0f}) avoiding {s.get('avoid')}")
                    continue
                pts = [(sx, sz)] + [tuple(p) for p in route]
                length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
                lines.append(f"{lab} wall " + ("off the floor" if wall is None else f"{wall:.0f}")
                             + ("" if depth is None else f" depth {depth:.0f}")
                             + f" route {len(route)} legs {length:.0f}u"
                             + ("" if clear is None else f" hot-spot clear {clear:.0f}"))
        return not bad, self.title("GOALS"), "; ".join(bad[:6]) or f"{n} steps: " + "; ".join(lines)

    # -- the live install (read-only) ---------------------------------------------------------------------------
    def preflight_extra(self, pred: dict, roots: list) -> list:
        """P-TEXT (every mod folder's text block judged by :func:`text_rule`; none shipped passes) and P-RECOVERY."""
        block = int(pred.get("text_block", TEXT_BLOCK))
        found = [(Path(r).name, shipped_text(r, block)) for r in roots]
        found = [(n, s) for n, s in found if s]
        if not found:
            text = (True, self.title("P-TEXT"), f"no mod folder ships block {block}")
        else:
            stock = stock_text_assets(block)
            ok_all, parts = True, []
            for name, shipped in found:
                ok, lines = text_rule(stock, shipped, pred.get("lang", SESSION_LANG))
                ok_all = ok_all and ok
                parts.append(text_detail(lines, where=f"{name}: "))
            text = (ok_all, self.title("P-TEXT"), " | ".join(parts))
        rec = int(pred.get("recovery", self.recovery))
        hits = [Path(r).name for r in roots if rec in T.mod_registrations(r)]
        recovery = (bool(hits), self.title("P-RECOVERY"),
                    f"{rec} registered in {', '.join(hits)}" if hits else f"{rec} is registered in no mod folder")
        return [text, recovery]

    def fingerprint_extra(self, roots: list, pred: dict) -> dict:
        """6.3: field 70's override .eb (us) per folder that ships one, every folder's text block per language, and
        the game's language (its last localization line and ForceLanguage)."""
        block = int(pred.get("text_block", TEXT_BLOCK))
        over, text = {}, {}
        for r in roots:
            p = T._override_path(r, 70, "us")
            if p is not None and p.is_file():
                over[Path(r).name] = _sha(p.read_bytes())
            t = {L: _sha(b) for L, b in shipped_text(r, block).items()}
            if t:
                text[Path(r).name] = t
        return {"override70": over, f"text{block}": text, "lang": install_lang()}

    # -- the session --------------------------------------------------------------------------------------------
    def capabilities(self, g) -> list:
        """P-CAP, then P-OBJECTS (s89's objects: ``npcs``, V6 and the ``near`` evidence need them) and P-LANG (this
        launch's Memoria.log and Memoria.ini, :func:`p_lang`)."""
        from harness.logs import MEMORIA_LOG
        out = super().capabilities(g)
        st = g.state
        out.append((st.objects_status != "cannot", self.title("P-OBJECTS"), f"objects_status {st.objects_status!r}"))
        log = next((p for name, p in g._log_paths() if name == MEMORIA_LOG), None)
        try:
            log_text = log.read_text(encoding="utf-8", errors="replace") if log is not None else None
        except OSError:
            log_text = None
        try:
            ini_text = (Path(g.game_path) / "Memoria.ini").read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            ini_text = None
        ok, detail, _info = p_lang(log_text, ini_text)
        out.append((ok, self.title("P-LANG"), detail))
        return out

    def drive(self, g, pred: dict, side: str, log: list, *, deadline: float, progress: dict | None = None) -> dict:
        return SD.drive(g, pred, side, log, deadline=deadline, progress=progress)

    # -- reading a session ---------------------------------------------------------------------------------------
    def read_session(self, run_dir, pred: dict, *, session: dict | None = None, stock=None) -> list:
        """The shared reading, with :meth:`why_void` able to read each run's driver log (its evidence)."""
        self._run_dir = Path(run_dir)
        return super().read_session(run_dir, pred, session=session, stock=stock)

    def _run_log(self, rec: dict) -> tuple:
        path = (self._run_dir or Path(".")) / rec.get("log", "")
        if not rec.get("log") or not path.is_file():
            return [], {}
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return [], {}
        return list(doc.get("log") or []), dict(doc.get("outcome") or {})

    def why_void(self, rec: dict, r: dict, pred: dict) -> list:
        """5.1's extra reasons, each ``(reason, class, "driver")``: no start row in the start place (A-NOSTART); a
        forbidden hit the run's own log BACKS (A-FORBIDDEN, one per hit); the engine's donor mapping disagreeing
        with the frozen members (A-MISMATCH). Also keeps the run's log, outcome and every forbidden hit with its
        backing on ``r`` for the all-run checks and the report."""
        log, outcome = self._run_log(rec)
        r["log"], r["outcome"] = log, outcome
        members = members_of(pred) if r["side"] == "F" else {}
        ends = pred.get("end_fields") or [pred["end_field"]]
        hits = []
        if r["rows"]:
            sp = place(pred["start"][r["side"]], members)
            hits = [(h, SD.backing(h, log, pred)) for h in SD.forbidden_hits(r["rows"], pred, members, sp,
                                                                             end_fields=ends)]
        r["hits"] = hits
        out = []
        if r["digest"] is not None and r["start"] is None:
            out.append((f"never reached the start field: no write in place {pred['start']['S']}", "A-NOSTART",
                        "driver"))
        for h, b in hits:
            if b is not None:
                out.append((f"walk divergence: {h['why']} ({h['fld']} e{h['sid']} t{h['tag']} ip{h['ip']} "
                            f"{h['target']}={h['new']}), backed by {b['what']}", "A-FORBIDDEN", "driver"))
        d = r["digest"]
        if d is not None:
            for m, dn in sorted(d.mismatched.items()):
                out.append((f"member {m}'s rows name donor {dn}, the frozen members say {members.get(m)}",
                            "A-MISMATCH", "driver"))
        return out

    # -- the checks ---------------------------------------------------------------------------------------------
    def all_run_checks(self, runs: list, pred: dict) -> list:
        return [self.forbidden_check(runs, pred), self.void_asym_check(runs, pred)]

    def forbidden_check(self, runs: list, pred: dict) -> tuple:
        """O2-FORBIDDEN (5.3): over EVERY run with a readable trace, covered or not -- no forbidden hit its own driver
        log does not back. A backed hit uncovers its run (A-FORBIDDEN); an unbacked one is a finding, listed here."""
        bad, backed = [], 0
        for r in runs:
            for h, b in r.get("hits") or ():
                if b is not None:
                    backed += 1
                    continue
                why_not = ("its hot-spot position is no registered hot-spot" if h["cause"] == "confirm_hotspot"
                           and h.get("hotspot") is None else f"no {h['cause']} evidence in the run's log before it")
                bad.append(f"{r['side']}#{r['i']} line {h['line']}: {h['fld']} (place {h['place']}) e{h['sid']} "
                           f"t{h['tag']} ip{h['ip']} {h['target']}={h['new']} -- {h['why']}; unbacked: {why_not}")
        n = sum(1 for r in runs if r.get("rows"))
        return (not bad, self.title("FORBIDDEN"),
                f"{len(bad)} unbacked: " + "; ".join(bad[:5]) if bad
                else f"{n} readable runs, no unbacked hit ({backed} backed, each uncovering its run)")

    @staticmethod
    def _void_ids(r: dict) -> set:
        return {(v.get("class"), tuple(v["cell"]) if v.get("cell") else None, v.get("by")) for v in r.get("void")
                or ()}

    def void_asym_check(self, runs: list, pred: dict) -> tuple:
        """O2-VOID-ASYM (5.3): the VOID classes read per side -- each a class with its cell. It FAILS when (a) a
        game-attributed one occurs in some run of one side and in no run of the other, or (b) every run of one side
        is VOID in one class while the other side has at least min_covered covered runs: a structural fork deviation
        must read NOT PROVEN, never hide as a VOID."""
        per = {s: [self._void_ids(r) for r in runs if r["side"] == s] for s in SIDES}
        game = {s: {(c, cell) for ids in per[s] for c, cell, by in ids if by == "game"} for s in SIDES}
        bad = []
        for s, o in (("S", "F"), ("F", "S")):
            for c, cell in sorted(game[s] - game[o], key=str):
                where = [f"{s}#{r['i']}" for r in runs if r["side"] == s
                         and any(v[:2] == (c, cell) for v in self._void_ids(r))]
                bad.append(f"(a) {c}{'' if cell is None else f' at {list(cell)}'} (game) on {s} only: "
                           f"{', '.join(where)}")
            covered_o = sum(1 for r in runs if r["side"] == o and r["covered"])
            if per[s] and all(per[s]) and covered_o >= pred["min_covered"]:
                common = set.intersection(*[{(c, cell) for c, cell, _by in ids} for ids in per[s]])
                for c, cell in sorted(common, key=str):
                    bad.append(f"(b) every {s} run VOID in {c}{'' if cell is None else f' at {list(cell)}'} while "
                               f"{o} has {covered_o} covered")
        seen = {s: sorted({f"{c}{'' if cell is None else list(cell)}:{by}" for ids in per[s] for c, cell, by in ids})
                for s in SIDES}
        return (not bad, self.title("VOID-ASYM"),
                "; ".join(bad[:5]) if bad else f"S {seen['S'] or 'none'}; F {seen['F'] or 'none'}")

    def core_checks(self, runs: list, cov: dict, pred: dict) -> list:
        covered = cov["S"] + cov["F"]
        c = self.comparison(cov, pred)
        return [self.start_check(covered, pred), self.span_check("LADDER", covered, pred, "sc_bytes", "ladder",
                                                                 pred["scenario"]),
                self.span_check("CHAIN", covered, pred, "entrance_bytes", "chain", pred["entrance"]),
                self.residue_check(covered, pred), self.writes_check(covered, pred), self.null_check(c, pred),
                self.stable_check(c, pred), self.seam_check(cov, c, pred), self.masked_check(cov, pred),
                self.state_check(covered, pred), self.join_check(cov)]

    def start_check(self, covered: list, pred: dict) -> tuple:
        """O2-START: (a) the rows before the start are EXACTLY the warp's residue (``start_residue``: kind ``r``,
        ``(byte, old, new)``, as a multiset); (b) the first ``w`` row in the start place is ``start_first``, read on
        the RAW row (its Bit[191] is masked in the digest)."""
        want = Counter(tuple(x) for x in pred["start_residue"])
        sf = pred["start_first"]
        bad = []
        for r in covered:
            lab = f"{r['side']}#{r['i']}"
            others = [x for x in r["pre"] if x.k != "r"]
            if others:
                bad.append(f"{lab}: {len(others)} other row(s) before the start, first line {others[0].line} "
                           f"({others[0].k} in {others[0].fld})")
            got = Counter((x.byte, x.old, x.new) for x in r["pre"] if x.k == "r")
            if got != want:
                bad.append(f"{lab}: residue before the start {sorted(got.elements())}, want {sorted(want.elements())}")
            at = next((x for x in r["rows"] if x.line == r["start"]), None)
            if at is None or (at.m, at.src, at.sid, at.tag, at.ip, at.target, at.new) != (
                    sf["m"], sf["src"], sf["sid"], sf["tag"], sf["ip"], sf["target"], sf["value"]):
                bad.append(f"{lab}: the first write in the start place is "
                           f"{_row_text(at) if at is not None else None}, not {label(sf)} (e{sf['sid']} t{sf['tag']} "
                           f"ip{sf['ip']} {sf['target']}={sf['value']})")
        return (not bad, self.title("START"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: 3 residue rows, then {sf['target']} at e{sf['sid']} "
                                      f"t{sf['tag']} ip{sf['ip']}")

    def span_check(self, cid: str, covered: list, pred: dict, span_key: str, keys_key: str, first_old: int) -> tuple:
        """O2-LADDER / O2-CHAIN: every covered run's writes over the bytes, by :func:`span_sequence`."""
        bad = []
        for r in covered:
            rk = row_keys(r["digest"])
            bad += [f"{r['side']}#{r['i']} {p}" for p in span_sequence(r["rows"], rk, pred[span_key], pred[keys_key],
                                                                     first_old)]
        return (not bad, self.title(cid),
                "; ".join(bad[:6]) or f"{len(covered)} runs x {len(pred[keys_key])} writes, in order, each from the "
                                      f"last (the first from {first_old})")

    def residue_check(self, covered: list, pred: dict) -> tuple:
        """O2-RESIDUE: every covered run's residue rows from the start on, outside the story-noise mask, are
        ``residue_after_start`` -- ``(byte, new)`` as a set (registered empty)."""
        want = {tuple(x) for x in pred.get("residue_after_start") or ()}
        bad, masked = [], 0
        for r in covered:
            got = {(x.byte, x.new) for x in r["rows"] if x.k == "r" and not T.noise_regions(x)}
            masked += sum(1 for x in r["rows"] if x.k == "r" and T.noise_regions(x))
            if got != want:
                bad.append(f"{r['side']}#{r['i']}: {sorted(got)}, want {sorted(want)}")
        return (not bad, self.title("RESIDUE"),
                "; ".join(bad[:6]) or f"{len(covered)} runs as registered {sorted(want)}; {masked} masked residue "
                                      f"row(s)")

    def writes_check(self, covered: list, pred: dict) -> tuple:
        """O2-WRITES: each registered write (4.4) is a key of every covered run of both sides (a seam key is not)."""
        bad = []
        for r in covered:
            keys = r["digest"].keys
            for k in pred["writes"]:
                if wkey(k) not in keys:
                    bad.append(f"{r['side']}#{r['i']} lacks {label(k)}")
        return (not bad, self.title("WRITES"),
                "; ".join(bad[:6]) or f"{len(covered)} runs x {len(pred['writes'])} keys")

    def seam_check(self, cov: dict, c: T.Comparison, pred: dict) -> tuple:
        """O2-SEAM: every covered fork digest has no seam key, the comparison no across-seam or seam-only key, and
        every recorded Seam is member(``seam.donor``) -> ``seam.to`` (NULL cannot see a seam leak)."""
        members = members_of(pred)
        seam = pred.get("seam") or {"donor": pred["route"][-1], "to": pred["end_field"]}
        frm = next((f for f, d in members.items() if d == seam["donor"]), None)
        bad = []
        for r in cov["F"]:
            d = r["digest"]
            if d.seam_keys:
                bad.append(f"F#{r['i']}: {len(d.seam_keys)} seam key(s): {ST._show(d.seam_keys, 3)}")
            for s in d.seams:
                if (s.frm, s.to) != (frm, seam["to"]):
                    bad.append(f"F#{r['i']}: a seam {s.origin} -> {s.to} (fields {s.fields}), want member("
                               f"{seam['donor']}) [{frm}] -> {seam['to']}")
        if c.across_seam:
            bad.append(f"across the seam: {ST._show(c.across_seam, 3)}")
        if c.seam_only:
            bad.append(f"seam only: {ST._show(c.seam_only, 3)}")
        return (not bad, self.title("SEAM"),
                "; ".join(bad[:6]) or f"{len(cov['F'])} fork runs: every seam member({seam['donor']}) [{frm}] -> "
                                      f"{seam['to']}, no seam key")

    def masked_check(self, cov: dict, pred: dict) -> tuple:
        """O2-MASKED: the story-noise region names written per side (``digest.masked``); FAILS on a region some
        covered run of one side writes and no covered run of the other does. The counts are always reported."""
        per = {s: Counter() for s in SIDES}
        for s in SIDES:
            for r in cov[s]:
                per[s].update(r["digest"].masked)
        only = {s: sorted(set(per[s]) - set(per[o])) for s, o in (("S", "F"), ("F", "S"))}
        detail = f"S {dict(sorted(per['S'].items()))}; F {dict(sorted(per['F'].items()))}"
        bad = [f"{s} only: {only[s]}" for s in SIDES if only[s]]
        return not bad, self.title("MASKED"), ("; ".join(bad) + "; " if bad else "") + detail

    @staticmethod
    def _state_rows(r: dict, pred: dict) -> list:
        """``[(row, key)]``: the ``w`` and ``c`` rows O2-STATE reads, in line order -- unmasked, keyed (JOIN's are
        not), neither the registered noise nor the harness's pokes."""
        rk = row_keys(r["digest"])
        out = []
        for x in r["rows"]:
            if x.k not in ("w", "c") or x.src == "harness" or T.noise_regions(x):
                continue
            k = key_of(rk, x)
            if k is None or is_noise(k, pred):
                continue
            out.append((x, k))
        return out

    @classmethod
    def history(cls, r: dict, pred: dict) -> dict:
        """``{target: [key, ...]}``: each unmasked target's EMITTED writes at the cut (``w`` rows), their keys in line
        order -- the order the engine wrote them in, so the last is the last value it emitted. A suppressed store (a
        ``c`` row) is left out: the engine writes the count at the epoch's close, so its place among the writes is
        unknown (:meth:`suppressed` reads those). The registered noise and the harness's pokes are left out too."""
        out: dict = {}
        for x, k in cls._state_rows(r, pred):
            if x.k == "w":
                out.setdefault(x.target, []).append(k)
        return out

    @classmethod
    def suppressed(cls, r: dict, pred: dict) -> dict:
        """``{target: [key, ...]}`` (sorted): the suppressed stores' ``last`` keys that no emitted row of the run
        carries -- as NULL and STABLE dedupe a count into the matching ``w`` key. A same-value repeat's count carries
        its site's emitted key and drops out, so whether a site repeats once or twice (timing) is never read; a count
        that hid a value never emitted stays, as a set (its time is unknown). The counts themselves are never read."""
        rows = cls._state_rows(r, pred)
        emitted = {k for x, k in rows if x.k == "w"}
        out: dict = {}
        for x, k in rows:
            if x.k == "c" and k not in emitted:
                out.setdefault(x.target, set()).add(k)
        return {t: sorted(v, key=T.WriteKey.sort_key) for t, v in out.items()}

    def state_check(self, covered: list, pred: dict) -> tuple:
        """O2-STATE: (a) each unmasked target's EMITTED write history (:meth:`history`) is identical across every
        covered run of both sides -- the ORDER the writes were emitted in, which NULL's sets cannot see, and the last
        value emitted -- and so are its suppressed stores' keys (:meth:`suppressed`, a set: a count's place in time is
        unknown); (b) every covered run's ``end_state``, read live on arrival in 61, is the frozen one -- the values
        actually handed to 61."""
        bad = []
        hs = [(r, self.history(r, pred), self.suppressed(r, pred)) for r in covered]
        if hs:
            r0, h0, s0 = hs[0]
            for r, h, s in hs[1:]:
                diff = sorted(t for t in set(h) | set(h0) if h.get(t) != h0.get(t))
                if diff:
                    t = diff[0]
                    bad.append(f"(a) {r['side']}#{r['i']} vs {r0['side']}#{r0['i']}: {len(diff)} target(s) differ, "
                               f"first {t}: {[_fmt_key(k) for k in h.get(t, [])][:4]} vs "
                               f"{[_fmt_key(k) for k in h0.get(t, [])][:4]}")
                diff = sorted(t for t in set(s) | set(s0) if s.get(t) != s0.get(t))
                if diff:
                    t = diff[0]
                    bad.append(f"(a) {r['side']}#{r['i']} vs {r0['side']}#{r0['i']}: suppressed stores of "
                               f"{len(diff)} target(s) differ, first {t}: {[_fmt_key(k) for k in s.get(t, [])][:4]} "
                               f"vs {[_fmt_key(k) for k in s0.get(t, [])][:4]}")
        want = pred.get("end_state") or {}
        for r in covered:
            got = (r.get("outcome") or {}).get("end_state")
            if got != want:
                diff = sorted(t for t in set(got or {}) | set(want) if (got or {}).get(t) != want.get(t))
                bad.append(f"(b) {r['side']}#{r['i']} end state "
                           + (f"differs at {', '.join(f'{t} {(got or {}).get(t)} (want {want.get(t)})' for t in diff[:4])}"
                              if got is not None else "was never read"))
        n = len(hs[0][1]) if hs else 0
        ns = sum(len(v) for v in hs[0][2].values()) if hs else 0
        return (not bad, self.title("STATE"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: {n} targets' emitted histories identical, in order; "
                                      f"{ns} suppressed store key(s) beyond them, identical; the end state as frozen "
                                      f"({len(want)} variables)")

    # -- the report ---------------------------------------------------------------------------------------------
    def report_extra(self, run_dir: Path, session: dict, pred: dict, runs: list, checks: list) -> list:
        """Report-only (5.3): the start-dependent keys under 4.5's scope line; the SC timeline per covered run; the
        steps per run; the VOID reasons per side; the masked counts; the forbidden hits with their backing; the
        KNOWN-KIT-DEFECT lines P-TEXT recorded; the folded transcripts."""
        L = ["", "Start dependence (4.5) -- " + SCOPE_LINE + ":"]
        for k in pred.get("start_dependent") or ():
            vals = {s: sorted({x.value for r in runs if r["side"] == s and r["covered"] for x in r["digest"].keys
                               if (x.donor, x.sid, x.tag, x.off, x.target) == (k["donor"], k["sid"], k["tag"],
                                                                              k["off"], k["target"])})
                    for s in SIDES}
            L.append(f"  {k['target']} {k['op']} at {k['donor']} e{k['sid']} t{k['tag']} ip{k['ip']}: S {vals['S']}, "
                     f"F {vals['F']} (registered {k['value']}); after O1 it would write {k['after_o1']} -- {k['why']}")
        L.append("")
        L.append("SC timeline (frame of each rung; delta from the previous):")
        for r in runs:
            if not r["covered"]:
                continue
            rows = span_rows(r["rows"], pred["sc_bytes"])
            parts, prev = [], None
            for x in rows:
                parts.append(f"{x.new}@{x.f}" + ("" if prev is None else f" (+{x.f - prev})"))
                prev = x.f
            L.append(f"  {r['side']}#{r['i']}: " + ", ".join(parts))
        L.append("")
        L.append("Steps (cell, step, attempt, outcome, seconds, lost, id-flip latency, lunge, climb):")
        for r in runs:
            steps = [x for x in r.get("log") or () if x.get("k") == "step"]
            if not steps:
                continue
            L.append(f"  {r['side']}#{r['i']}:")
            for x in steps:
                lost = x.get("lost") or {}
                flip = (x["flip_frame"] - lost["frame"]) if x.get("flip_frame") is not None and lost.get("frame") \
                    is not None else None
                lunge = x.get("lunge") or {}
                climb = x.get("climb") or {}
                L.append(f"    ({x.get('donor')}, {x.get('sc')}) #{x.get('n')} {x.get('name')!s:.40} try "
                         f"{x.get('attempt')} {x.get('outcome')} {(x.get('t1') or 0) - (x.get('t0') or 0):.1f}s"
                         + (f" lost ({lost.get('x')}, {lost.get('z')})" if lost else "")
                         + (f" flip +{flip}f" if flip is not None else "")
                         + (f" lunge {lunge.get('pad')} {lunge.get('frames')}f" if lunge.get("pressed") else "")
                         + (f" climb {climb.get('ended')} {climb.get('bursts')} bursts" if climb else "")
                         + (f" -- {x.get('why')}" if x.get("why") else ""))
        L.append("")
        L.append("VOID reasons per side (class, cell, by, why):")
        for s in SIDES:
            rows = [(r, v) for r in runs if r["side"] == s for v in r.get("void") or ()]
            L.append(f"  {s}: " + ("none" if not rows else ""))
            for r, v in rows:
                L.append(f"    {s}#{r['i']} {v.get('class')} {v.get('cell') or ''} {v.get('by')}: {v.get('why')}"[:240])
        L.append("")
        per = {s: Counter() for s in SIDES}
        rmask = {s: 0 for s in SIDES}
        for r in runs:
            if r["covered"]:
                per[r["side"]].update(r["digest"].masked)
                rmask[r["side"]] += r["digest"].residue_masked
        L.append(f"Masked (story-noise) rows: S {dict(sorted(per['S'].items()))}, F {dict(sorted(per['F'].items()))}; "
                 f"masked residue S {rmask['S']}, F {rmask['F']}")
        L.append("")
        L.append("Forbidden hits (backing):")
        any_hit = False
        for r in runs:
            for h, b in r.get("hits") or ():
                any_hit = True
                L.append(f"  {r['side']}#{r['i']} line {h['line']}: {h['fld']} e{h['sid']} t{h['tag']} ip{h['ip']} "
                         f"{h['target']}={h['new']} -- {h['why']}: "
                         + (f"BACKED by {b['what']}" if b is not None else "unbacked (a finding)"))
        if not any_hit:
            L.append("  none")
        defects = [d for ok, what, detail in session.get("preflight") or () if str(what).startswith("P-TEXT")
                   for d in defect_lines(detail)]
        L.append("")
        L.append("Text (P-TEXT, recorded at the preflight):")
        L += [f"  {d}" for d in defects] or ["  no KNOWN-KIT-DEFECT line recorded"]
        L.append("")
        L.append("Dialogue (timed pages removed, consecutive duplicates collapsed):")
        cov_s = next((r for r in runs if r["side"] == "S" and r["covered"]), None)
        s0 = fold_pages((cov_s.get("outcome") or {}).get("pages"), (cov_s.get("outcome") or {}).get("timed")) \
            if cov_s is not None else None
        for r in runs:
            if r["side"] != "F" or not r["covered"] or s0 is None:
                continue
            f0 = fold_pages((r.get("outcome") or {}).get("pages"), (r.get("outcome") or {}).get("timed"))
            first = next((i for i, (a, b) in enumerate(zip(f0, s0)) if a != b), None)
            L.append(f"  F#{r['i']} {'==' if f0 == s0 else '!='} S#{cov_s['i']} ({len(f0)} vs {len(s0)} pages)"
                     + ("" if f0 == s0 or first is None else f"; first difference at page {first + 1}: "
                                                            f"{f0[first][:60]!r} vs {s0[first][:60]!r}"))
        return L

    # -- the CLI ------------------------------------------------------------------------------------------------
    def add_arguments(self, ap) -> None:
        ap.add_argument("--draft", action="store_true", help="print the draft predictions as JSON")
        ap.add_argument("--rehearsal-report", metavar="RUN_DIR",
                        help="print an o2_rehearse.py launch's record, stage by stage and run by run")

    def handle(self, args) -> int | None:
        if args.draft:
            print(json.dumps(self.draft(), indent=1, sort_keys=True))
            return 0
        if args.rehearsal_report:
            print(rehearsal_report(args.rehearsal_report))
            return 0
        if args.offline_check or args.preflight:
            pred, what = self.current(args.predictions)
            print(f"predictions: {what}")
            checks = self.offline_check(pred) if args.offline_check else self.preflight(pred, self.roots())
            for ok, w, detail in checks:
                print(f"{'PASS' if ok else 'FAIL'}  {w}\n      {detail}")
                for d in defect_lines(detail):
                    print(d)
            return 0 if all(ok for ok, _w, _d in checks) else 1
        return None


O2 = O2Segment()


# ======================================================================== the rehearsal report
def rehearsal_report(run_dir) -> str:
    """``--rehearsal-report``: an o2_rehearse.py launch's ``o2_rehearsal.json`` (research/o2_design.md 7.2), stage by
    stage and run by run -- what each freeze item (7.3) is read from."""
    run_dir = Path(run_dir)
    doc = json.loads((run_dir / REHEARSAL_FILE).read_text(encoding="utf-8"))
    L = [f"O2 rehearsals -- {run_dir.name}  (draft sha {str(doc.get('draft_sha256'))[:8]}; stages "
         f"{doc.get('stages_run')})"]
    L += [f"  {'PASS' if ok else 'FAIL'}  {what} -- {detail}" for ok, what, detail in doc.get("capabilities") or ()]
    if doc.get("stopped"):
        L.append(f"  STOPPED: {doc['stopped']}")
    L.append("")
    for name, recs in doc.get("stages", {}).items():
        stage = (doc.get("stage_defs") or {}).get(name, {})
        L.append(f"== {name}: warp {stage.get('field')} {stage.get('entrance')} {stage.get('sc')} -> "
                 f"{stage.get('end')}  ({len(recs)} run(s)) -- settles: {stage.get('settles')}")
        for rec in recs:
            out = rec.get("outcome") or {}
            L.append(f"  run {rec.get('n')}: {out.get('end')} -- {out.get('why')}"
                     + (f" [{out.get('v')} {out.get('cell')} {out.get('by')}]" if out.get("v") else "")
                     + f"; {rec.get('t1', 0) - rec.get('t0', 0):.0f}s; trace {rec.get('trace_file')}")
            for gr in rec.get("grants") or ():
                L.append(f"    grant: field {gr.get('field')} SC {gr.get('sc')} frame {gr.get('frame')} at "
                         f"({gr.get('x')}, {gr.get('z')}) y {gr.get('y')} fps {gr.get('fps')}")
            for s in rec.get("steps") or ():
                lost = s.get("lost") or {}
                L.append(f"    step ({s.get('donor')}, {s.get('sc')}) #{s.get('n')} {s.get('kind')} try "
                         f"{s.get('attempt')}: {s.get('outcome')}"
                         + (f"; lost at frame {lost.get('frame')} ({lost.get('x')}, {lost.get('z')})" if lost else "")
                         + (f"; id flip frame {s.get('flip_frame')}" if s.get("flip_frame") is not None else "")
                         + (f"; lunge {s['lunge']}" if s.get("lunge") else "")
                         + (f"; climb {s['climb'].get('ended')} {s['climb'].get('bursts')} bursts ys "
                            f"{(s['climb'].get('ys') or [])[:6]}" if s.get("climb") else "")
                         + (f"; {s.get('why')}" if s.get("why") else ""))
            for c in rec.get("choices") or ():
                L.append(f"    choice at frame {c.get('frame')}: {c.get('options')} active {c.get('active')} "
                         f"selected {c.get('selected')} count {c.get('count')} -> rule {c.get('rule')} index "
                         f"{c.get('index')}")
            L.append(f"    published choices: {len(rec.get('published_choices') or [])} distinct snapshot(s)")
            pages = rec.get("pages") or []
            L.append(f"    pages: {len(pages)} ({sum(1 for p in pages if p.get('timed'))} timed)")
            ev = rec.get("evidence") or {}
            L.append(f"    evidence: {len(ev.get('press') or [])} press row(s), {len(ev.get('watch') or [])} watch "
                     f"row(s), {len(ev.get('forbidden') or [])} forbidden row(s)")
            for key, summ in (rec.get("track_summary") or {}).items():
                L.append(f"    track {key}: {summ}")
            for lat in rec.get("latency") or ():
                L.append(f"    leave-now latency: {lat}")
            npg = rec.get("no_progress") or {}
            L.append(f"    longest no-progress stretch: {npg.get('longest_s')}s at {npg.get('where')}")
            if rec.get("mbg101") is not None:
                L.append(f"    mbg101: {rec['mbg101']}")
            end = rec.get("end") or {}
            L.append(f"    end: state {end.get('end_state')}; end_run {end.get('end_run')}")
            tr = rec.get("trace") or {}
            if tr:
                L.append(f"    trace: start line {tr.get('start')}, end line {tr.get('end')}, {tr.get('rows')} rows; "
                         f"SC {[x['new'] for x in tr.get('sc') or ()]}; FieldEntrance "
                         f"{[x['new'] for x in tr.get('entrance') or ()]}")
                L.append(f"      residue before the start {tr.get('residue_before')}; after "
                         f"{tr.get('residue_after')}; other rows before it {tr.get('pre_other')}")
                for name2, keys in (tr.get("registered") or {}).items():
                    absent = [k["what"] for k in keys if not k["present"]]
                    L.append(f"      {name2}: {len(keys) - len(absent)}/{len(keys)} present"
                             + (f"; absent: {absent[:6]}" if absent else ""))
                L.append(f"      unregistered keys ({len(tr.get('unregistered') or [])}): "
                         f"{(tr.get('unregistered') or [])[:12]}")
                L.append(f"      watched: {tr.get('watched')}; masked {tr.get('masked')}; join failures "
                         f"{len(tr.get('failures') or [])}")
                for h in tr.get("forbidden") or ():
                    L.append(f"      forbidden: {h['row']} {h['why']} -- "
                             + (f"backed by {h['by']}" if h["backed"] else "unbacked"))
        L.append("")
    return "\n".join(L)


# ======================================================================== the session and the CLI
def run(g) -> None:
    """The session (tools/play.py's entry): O2Segment.run."""
    return O2.run(g)


def main(argv=None) -> int:
    return O2.main(argv)


if __name__ == "__main__":
    sys.exit(main())
