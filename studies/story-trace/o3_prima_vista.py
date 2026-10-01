"""THE STORY-WRITE TRACE, O3 -- PRIMA VISTA, THE PLAY (a US session): from a raw warp into 61 (entrance 0, the
scenario at 1155) through the play's Act I, battle 338 (King Leo) and the battle's own landing in 63, to 63's
Field(64) -- stock Prima Vista against O1's deployed tshp chain, both sides played by one beat-table driver
(studies/story-trace/PLAN.md, "O3"; the design: research/o3_design.md).

    py tools/play.py studies/story-trace/o3_prima_vista.py --label story-o3 --timeout 240
    py studies/story-trace/o3_prima_vista.py --offline-check     # the build, its text, the keys, the regions, the
                                                                 # battle scene and the store census
    py studies/story-trace/o3_prima_vista.py --preflight         # the live install (read-only)
    py studies/story-trace/o3_prima_vista.py --draft             # the draft predictions, as JSON
    py studies/story-trace/o3_prima_vista.py --freeze            # write o3_predictions_v1.json (once: the lead,
                                                                 # after the rehearsals and the F-side load smoke)
    py studies/story-trace/o3_prima_vista.py --analyse <run dir> # the analysis alone, on saved traces
    py studies/story-trace/o3_prima_vista.py --rehearsal-report <run dir>   # an o3_rehearse.py launch, stage by stage

THE SIDES (o3_forks.json; nothing is imported, built or deployed for O3):
  S  stock: the install's scripts. Start: 61 (Prima Vista/Interior), entrance 0, SC 1155.
  F  O1's tshp chain as deployed (31200-31219, FF9CustomMap). The route runs 31211 (61) -> 31212 (62) -> 31213 (63);
     member(63)'s Field(64) is real 64: the seam, and the segment's end on both sides. A LEGACY build: every member's
     jp/fr/gr/it/es .eb is US bytecode and block 2's uk copy is the US text -- the claim is a US SESSION's.

THE ENTRY: New Game, the trace armed, then a raw `warp <61 | 31211> 0 1155` (O2's form): the warp writes the
scenario's two bytes in field 70, the residue the front cut sets aside and O3-START requires.

THE ROUTE: segment_drive.drive, with no beat table (61-63 never grant control: control anywhere is V4) and ONE
registered battle (rule 1b): 62's Battle(0,338) fought by fight()'s default policy, left with
leave_battle(stop_on_field), landed in 63 by the battle's own RunBattleCode(37,63) -- on F through the s24 redirect
into member(63); real 63 there is V16, a finding. 61-63's error window is a stop page (V5, nothing pressed).

THE ANALYSIS: each run cut at its start row (61's first write) and at its first row in 64, digested and compared as
O1's and O2's; the O3 checks (research/o3_design.md 5.3) read the start, SC by byte span (it must never move), the
chain, the residue, the writes EXACTLY, the seam, the landing (every row in its place's own field, the battle's one
store, 63 loaded fresh, the end cut at 64's first store) and the battle the driver fought, from its own log. The
predictions are frozen by the lead after the stock rehearsals and the F-side load smoke (o3_rehearse.py); until then
--offline-check and --preflight read the draft.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
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
import segment_drive as SD                                              # noqa: E402
import segment_trace as ST                                              # noqa: E402
from segment_trace import (SIDES, cut_at_end, cut_at_start, is_noise, key_of, members_of, place,  # noqa: E402
                           row_keys, wkey)

PREDICTIONS = HERE / "o3_predictions_v1.json"
MANIFEST = HERE / "o3_forks.json"
O1_MANIFEST = HERE / "o1_forks.json"
SESSION_FILE = "o3_session.json"
REPORT_FILE = "o3_report.txt"
REHEARSAL_FILE = "o3_rehearsal.json"
CHAIN_DIR = Path(r"C:\gd\_ns_playtest\o1\fork")
BUILD_DIR = Path(r"C:\gd\_ns_playtest\o1\build")
GAME = A.GAME
TEXT_BLOCK = 2
SESSION_LANG = "us"
#: The route's places, in order, and the members O1's chain gives them (research/o3_design.md 0.1).
ROUTE = (61, 62, 63)
ROUTE_MEMBERS = {31211: 61, 31212: 62, 31213: 63}
END_FIELD = 64
#: The four patch files DataPatchers.Initialize reads from every stacked folder, once a launch (DataPatchers.cs
#: :107-134) -- P-LAUNCH dates them against the launch.
PATCH_FILES = ("DictionaryPatch.txt", "BattlePatch.txt", "TextPatch.txt", "ForkDonorPatch.txt")
#: An unresolved store's lvalue token -> its class (O3-SCENE, O3-CENSUS): only these are classified; any other token
#: FAILS by name -- an unresolved store is never silently skipped.
LVALUE_CLASSES = ((re.compile(r"^B_SYSLIST\[\d+\]$"), "a battle target list, not gEventGlobal"),)
#: 4.13: the settings the stock truth runs under, raw ini values as the engine takes them.
SETTINGS = {
    "Battle": {"Enabled": "1", "SFXRework": "1", "Speed": "5", "CustomBattleFlagsMeaning": "0"},
    "Cheats": {"Enabled": "1", "AutoBattle": "1", "SpeedMode": "1", "SpeedFactor": "3", "SpeedTimer": "0",
               "BattleAssistance": "1", "Attack9999": "1", "NoRandomEncounter": "1", "MasterSkill": "0", "LvMax": "0",
               "GilMax": "0"},
    "Hacks": {"Enabled": "1", "AllCharactersAvailable": "1", "SwordplayAssistance": "1", "DisableNameChoice": "0"},
    "Control": {"SoftReset": "1", "TurboDialog": "1", "BattleAutoConfirm": "1", "DialogProgressButtons": "\"Confirm\""},
}
#: 5.4's scope lines.
SCOPE_START = ("under the raw warp no key on the route is start-dependent: 61 reads Byte[13]/Byte[14]/Bit[184] before "
               "writing them and takes the same branch from the warp's (1, 0, 0) as from a true O2 end's (3, 0, 0); 62 "
               "writes UInt16[21] and Byte[303] before reading them; battle 338 reads Byte[16..18] (0, and 17/18 "
               "written by 62 first); 63 reads nothing global. The party is rebuilt by 62 e4 t1 from [Zidane] (here) "
               "or [Vivi] (after O2) to the same four. Not covered: party data, items, gil, AP, cards, field 70's "
               "override state, and the six untouched targets' values after a real O2 (4.9)")
SCOPE_LANG = ("a US session (P-LANG): the members' jp/fr/gr/it/es .eb are US bytecode (accept_us_build), and block "
              "2's uk copy is the US text (the KNOWN-KIT-DEFECT line below)")
#: Memoria.log's line stamp (``dd.MM.yyyy HH:mm:ss``, local time) -- P-LAUNCH reads the first line's.
LOG_STAMP = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4}) (\d{2}):(\d{2}):(\d{2})(?!\d)")
#: The engine's one ForkDonorPatch collision line (DataPatchers.cs:156-160) -- P-DONOR-LOG reads its absence.
DONOR_WARNING = re.compile(r"\[DataPatchers\] ForkDonorPatch: donor field (\d+) is forked by both (-?\d+) and (\d+)")
DATAPATCHERS_DONE = "[DataPatchers] Initialized"
_MODULE_DOC = __doc__


def _sha_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def _rows_text(xs) -> str:
    return ", ".join(A._row_text(x) for x in xs)


# ======================================================================== the predictions (draft v1)
def chain_from_campaign(campaign: Path = CHAIN_DIR / "campaign.toml", manifest: Path = O1_MANIFEST) -> tuple:
    """``({fork id: donor}, {fork id: member name})`` of O1's built tshp chain (research/o3_design.md 1.3): it must be
    exactly O1's twenty -- ``o1_forks.json``'s members and names, the deployed chain -- and map 31211 -> 61, 31212 ->
    62, 31213 -> 63. Anything else is refused: the draft would register another chain."""
    members, names = ST.chain_from_campaign(campaign)
    o1 = json.loads(Path(manifest).read_text(encoding="utf-8"))
    want = {int(f): int(d) for f, d in o1["members"].items()}
    want_names = {int(f): n for f, n in o1["names"].items()}
    if members != want or names != want_names:
        raise AssertionError(f"{campaign}: the chain is {members} ({names}), not O1's twenty "
                             f"({Path(manifest).name}: {want})")
    wrong = {f: members.get(f) for f, d in ROUTE_MEMBERS.items() if members.get(f) != d}
    if wrong:
        raise AssertionError(f"{campaign}: the route members map {wrong}, not {ROUTE_MEMBERS}")
    return members, names


def _key(donor, sid, tag, ip, off, target, value, op, what, prior=None) -> dict:
    return A._key(donor, sid, tag, ip, off, target, value, op, what, prior)


def _ambient(donor: int, ips: tuple) -> list:
    """Each Main_Init's ambient four (e0 t0): Int16[9] := -1, Byte[13] := 0, Int16[11] := -1, Byte[14] := 0."""
    i9, b13, i11, b14 = ips
    return [_key(donor, 0, 0, i9, 51, "Global.Int16[9]", -1, ":=", f"{donor} Int16[9] := -1 (ambient)"),
            _key(donor, 0, 0, b13, 113, "Global.Byte[13]", 0, ":=", f"{donor} Byte[13] := 0 (ambient)"),
            _key(donor, 0, 0, i11, 132, "Global.Int16[11]", -1, ":=", f"{donor} Int16[11] := -1 (ambient)"),
            _key(donor, 0, 0, b14, 194, "Global.Byte[14]", 0, ":=", f"{donor} Byte[14] := 0 (ambient)")]


def battle_row() -> dict:
    """2.1's registry row: battle 338 in 62 at SC 1155, won [1, 2], landing in 63 (F: member(63), the s24 redirect).
    Its numbers are drafts (4.10): F9 re-sizes them from the rehearsals."""
    return {"donor": 62, "sc": 1155, "scene": 338, "won": [1, 2], "lands": 63, "beat": "leo",
            # F9 from the rehearsals (R-62 + R-FULL, 4 battles: 28.1-41.1 s, 6-10 turns, flip -> landing 36-40
            # frames): timeout_s max(120, 3x 41.1), max_turns max(30, 3x 10), land_s max(10, 3x ~0.7 s),
            # land_cap_s max(120, 10x that)
            "timeout_s": 124, "max_turns": 30, "land_s": 10, "land_cap_s": 120,
            "why": "62 e4 t1 ip1293 Battle(0,338) = BSC_TH_E002 (King Leo, 10186): ends by script once King Leo's own "
                   "cur.hp <= 10000 (>= 186 damage) -- RunBattleCode(33,1), result 2 (WinPose off), folded to 1 at the "
                   "over frame; its own RunBattleCode(37,63) lands the run in 63, fresh (F: ForkSiblingField(63) = "
                   "31213, s24)"}


def draft_predictions() -> dict:
    """The registered claims (research/o3_design.md section 4). Every number was read off the stock bytes (the
    offline check re-derives each: O3-KEYS, O3-REGIONS, O3-SCENE, O3-CENSUS), the battle scene, the live install or
    O1's campaign.toml; nothing is read from a run. The rehearsals (o3_rehearse.py) settle the driver's numbers before
    the lead freezes them (7.3)."""
    members, names = chain_from_campaign()
    key = _key
    writes = (_ambient(61, (57, 119, 138, 200)) + [
        key(61, 2, 1, 752, 637, "Global.Byte[8]", 125, ":=", "61 Byte[8] := 125 (after FMV003 and pages 72-78)")]
        + _ambient(62, (61, 123, 142, 204)) + [
        key(62, 4, 1, 319, 308, "Global.UInt16[21]", 3585, ":=", "62 UInt16[21] := 3585 (the play's party: 0xE01)"),
        key(62, 4, 1, 603, 592, "Global.Byte[303]", 0, ":=", "62 Byte[303] := 0"),
        key(62, 4, 1, 637, 626, "Global.Byte[303]", 1, "++", "62 Byte[303]++ (1)", prior="62/4/1/603"),
        key(62, 4, 1, 659, 648, "Global.Byte[303]", 2, "++", "62 Byte[303]++ (2)", prior="62/4/1/637"),
        key(62, 4, 1, 681, 670, "Global.Byte[303]", 3, "++", "62 Byte[303]++ (3)", prior="62/4/1/659"),
        key(62, 4, 1, 703, 692, "Global.Byte[303]", 4, "++", "62 Byte[303]++ (4)", prior="62/4/1/681"),
        key(62, 4, 1, 1034, 1023, "Global.Byte[4]", 0, ":=", "62 Byte[4] := 0 (PARTYCHK(5) false: ip1023 not taken)"),
        key(62, 4, 1, 1085, 1074, "Global.Byte[4]", 0, ":=", "62 Byte[4] := 0 (ip1085)"),
        key(62, 4, 1, 1093, 1082, "Global.Byte[17]", 0, ":=", "62 Byte[17] := 0"),
        key(62, 4, 1, 1101, 1090, "Global.Byte[18]", 1, ":=", "62 Byte[18] := 1")]
        + _ambient(63, (57, 119, 138, 200)) + [
        key(63, 14, 1, 805, 330, "Global.Byte[8]", 125, ":=", "63 Byte[8] := 125 (stage 5, after 99)")])
    chain = [
        key(61, 1, 1, 363, 352, "Global.Int16[2]", 100, ":=", "FieldEntrance 100: 61's exit, then Field(62)"),
        key(62, 4, 1, 1285, 1274, "Global.Int16[2]", 0, ":=", "FieldEntrance 0: 62 stage 10, before Battle(0,338)"),
        key(63, 4, 1, 820, 809, "Global.Int16[2]", 100, ":=", "FieldEntrance 100: 63's exit, then Field(64)"),
    ]
    error_path = [key(donor, sid, tag, ip, off, target, value, ":=", f"{donor} e{sid} t{tag} ip{ip}: the error path "
                                                                      f"({target} := {value})")
                  for donor, sid, tag, ip, off, target, value in (
        (61, 0, 0, 97, 91, "Global.Byte[13]", 9), (61, 0, 0, 178, 172, "Global.Byte[14]", 9),
        (61, 0, 0, 349, 343, "Global.Byte[13]", 0), (61, 0, 0, 383, 377, "Global.Byte[14]", 0),
        (62, 0, 0, 101, 91, "Global.Byte[13]", 9), (62, 0, 0, 182, 172, "Global.Byte[14]", 9),
        (62, 0, 0, 346, 336, "Global.Byte[13]", 0), (62, 0, 0, 380, 370, "Global.Byte[14]", 0),
        (62, 0, 10, 580, 52, "Global.Byte[13]", 0), (62, 0, 10, 614, 86, "Global.Byte[14]", 0),
        (63, 0, 0, 97, 91, "Global.Byte[13]", 9), (63, 0, 0, 178, 172, "Global.Byte[14]", 9),
        (63, 0, 0, 362, 356, "Global.Byte[13]", 0), (63, 0, 0, 396, 390, "Global.Byte[14]", 0))]
    dead = [
        key(61, 0, 0, 41, 35, "Global.Int16[2]", 10000, ":=", "61 Int16[2] := 10000 (dead: Bit[184] == 1, ip30)"),
        key(61, 0, 0, 130, 124, "Global.Byte[13]", 1, ":=", "61 Byte[13] := 1 (dead: Int16[9] >= 0, ip108)"),
        key(61, 0, 0, 211, 205, "Global.Byte[14]", 1, ":=", "61 Byte[14] := 1 (dead: Int16[11] >= 0, ip189)"),
        key(62, 0, 0, 45, 35, "Global.Int16[2]", 10000, ":=", "62 Int16[2] := 10000 (dead: Bit[184] == 1, ip34)"),
        key(62, 0, 0, 134, 124, "Global.Byte[13]", 1, ":=", "62 Byte[13] := 1 (dead: Int16[9] >= 0, ip112)"),
        key(62, 0, 0, 215, 205, "Global.Byte[14]", 1, ":=", "62 Byte[14] := 1 (dead: Int16[11] >= 0, ip193)"),
        key(62, 4, 1, 1023, 1012, "Global.Byte[4]", 1, ":=", "62 Byte[4] := 1 (dead: PARTYCHK(5), Quina absent)"),
        key(63, 0, 0, 41, 35, "Global.Int16[2]", 10000, ":=", "63 Int16[2] := 10000 (dead: Bit[184] == 1, ip30)"),
        key(63, 0, 0, 130, 124, "Global.Byte[13]", 1, ":=", "63 Byte[13] := 1 (dead: Int16[9] >= 0, ip108)"),
        key(63, 0, 0, 211, 205, "Global.Byte[14]", 1, ":=", "63 Byte[14] := 1 (dead: Int16[11] >= 0, ip189)"),
    ]
    start_music = dict(key(61, 0, 0, 119, 113, "Global.Byte[13]", 0, ":=",
                           "61's ambient branch from the warp's Byte[13] 1 (field 70's prologue :=1 at ip130; the warp "
                           "leaves FMV001 before its tail's :=2)"), old=1)
    return {
        "version": 1,
        "what": "O3: 61@1155 (warp, entrance 0) -> 62 -> battle 338 -> 63 -> Field(64), stock vs O1's tshp chain "
                "(members 31211-31213; PLAN.md, O3) -- a US session",
        "rehearsals": [                         # the rehearsal run dirs this freeze reads (research/o3_design.md 7.3)
            "C:/gd/Dream-World-IX/.harness-runs/20261001-092419-o3-rh-start",
            "C:/gd/Dream-World-IX/.harness-runs/20261001-092947-o3-rh-F-SMOKE",
            "C:/gd/Dream-World-IX/.harness-runs/20261001-093132-o3-rh-R-62",
            "C:/gd/Dream-World-IX/.harness-runs/20261001-093510-o3-rh-R-FULL",
            "C:/gd/Dream-World-IX/.harness-runs/20261001-094318-o3-rh-R-BATTLE-VOID",
        ],
        "order": ["S", "F", "S", "F", "S", "F"],
        "min_covered": 2,
        "rerun": {"max": 2, "stop_on": ["V16"]},
        # F9 from R-FULL (250 s, 230 s): run_s 2x the slowest, run_min_s 1.25x the median, session_s 8x the median
        # + 1800; no_progress_s max(120, 3x the longest stall seen, FMV003's 90.3 s). end_row_s: rule 1 waits for
        # 64's first trace row before the drive returns and the session closes the trace (segment_drive's end row;
        # 11.7 #3) -- every rehearsal's end row was there, so the draft's 10 s stands
        "budget": {"run_s": 500, "run_min_s": 300, "session_s": 3720, "settle_s": 1.0, "no_progress_s": 271,
                   "end_row_s": 10.0},
        "start": {"S": 61, "F": 31211},
        "entrance": 0,
        "scenario": 1155,
        "lang": SESSION_LANG,
        "end_field": END_FIELD,
        "end_fields": [END_FIELD],
        "route": list(ROUTE),
        "visits": list(ROUTE),
        "stock_fields": [61, 62, 63, 64],
        "members": {str(f): d for f, d in sorted(members.items())},
        "names": {str(f): n for f, n in sorted(names.items())},
        "text_block": TEXT_BLOCK,
        "recovery": 4600,
        "seam": {"donor": 63, "to": 64, "why": "member(63) = 31213's Field(64) (63 e4 t1 ip828) stays real: the end, on "
                                               "both sides"},
        "cut_start": True,
        "start_first": key(61, 0, 0, 22, 16, "Global.Bit[191]", 0, ":=", "61's Main_Init: its first store"),
        "start_music": start_music,
        "start_residue": [[0, 0, 131], [1, 0, 4]],          # SC 1155 = 0x0483: bytes 0 and 1; entrance 0 writes none
        "residue_after_start": [],
        "sc_bytes": [0, 1],
        "chain": chain,
        "entrance_bytes": [2, 3],
        "writes": writes,
        "error_path": error_path,
        "forbidden_sites": [key(62, 4, 1, 1345, 1334, "Global.Int16[2]", 0, ":=",
                                "62 e4 t1 ip1345: the battle returned to 62 (never on the route)")],
        "dead": dead,
        "start_dependent": [],
        "noise": [{"not_m": T.FIELD_MODE, "target": "Global.Byte[206]",
                   "why": "battle 338's AI (BSC_TH_E002 e1 t1 ip267): Byte[206] := SYSVAR[0] each frame until ATB "
                          "starts (random value and count)"}],
        "forbidden": [{"off_route": True, "cause": "walk",
                       "why": "a write off the route: S, a place outside route + end_fields; F, a field that is neither "
                              "a member whose donor is on the route nor an end field (real 61/62/63 on F: the s24 "
                              "leak)"}],
        "landing": {"route_places": list(ROUTE), "last_place": 63, "end": END_FIELD,
                    "battle": {"place": 62, "m": 2, "sid": 1, "tag": 1, "ip": 267, "target": "Global.Byte[206]"},
                    "before": {"place": 62, "sid": 4, "tag": 1, "ip": 1285, "target": "Global.Int16[2]", "value": 0},
                    "fresh": {"place": 63, "sid": 0, "tag": 0, "ip": 22, "target": "Global.Bit[191]", "value": 0},
                    "end_row": {"place": END_FIELD, "sid": 0, "tag": 0, "ip": 22, "target": "Global.Bit[191]",
                                "value": 0}},
        "end_state": {"Global.UInt16[0]": 1155, "Global.Int16[2]": 100, "Global.UInt16[21]": 3585,
                      "Global.Byte[303]": 4, "Global.Byte[4]": 0, "Global.Byte[17]": 0, "Global.Byte[18]": 1,
                      "Global.Byte[8]": 125, "Global.Byte[13]": 0, "Global.Byte[14]": 0, "Global.Int16[9]": -1,
                      "Global.Int16[11]": -1, "Global.Bit[191]": 0, "Global.Bit[184]": 0,
                      "Global.Byte[6]": 0, "Global.UInt16[19]": 0, "Global.Byte[472]": 0, "Global.Int16[469]": 0,
                      "Global.Bit[3717]": 0, "Global.Bit[3718]": 0},
        "battles": [battle_row()],
        "stop_pages": [{"match": "Env Play()",
                        "why": "61-63's ambient error window 3 ('Error Env Play()  Slot=n', e0 t0 WindowAsync(6,0,3) + "
                               "WaitWindow): Byte[13]/[14] arrived as 2 or 9"}],
        "regions": {},
        "hotspots": {},
        "table": [],
        "choices": [{"donor": None, "sc": None, "match": "want to skip", "pick": "default", "once": False,
                     "beat": None}],
        "naming": [],
        "beats": ["leo"],
        "settings": json.loads(json.dumps(SETTINGS)),
    }


# ======================================================================== the lvalue walk, the scene, the census
def _token_text(o: int, v) -> str:
    """An operand token as eb-src prints it (exprasm's forms)."""
    if o == 0x79:
        return f"B_SYSLIST[{v}]"
    if o == 0x7A:
        return f"B_SYSVAR[{v}]"
    if o == 0x7D:
        return f"const({v})"
    if o == 0x7E:
        return f"const4({v})"
    if o == 0x29:
        return f"B_MEMBER({v})"
    if o == 0x5F:
        return f"B_PTR({v})"
    if o == 0x78:
        return f"obj(uid={v[0]}).f[{v[1]}]"
    return f"op(0x{o:02X}, {v!r})"


def unresolved_lvalues(raw: bytes, ins) -> list:
    """The lvalue TOKEN of every store :func:`storytrace.instruction_stores` leaves unresolved (``("unknown", ...)``),
    one per such store, in its order: the operand token the store writes through (``B_SYSLIST[0]`` ...), or None (a
    computed lvalue, the member-list walk, an operator with no known arity). The walk mirrors instruction_stores step
    for step -- the same CalcStack arities and lvalue depths -- and only remembers what each operand push was."""
    from ff9mapkit.eb import disasm
    from ff9mapkit.eb._exprtable import EXPR_OP_NAMES
    from ff9mapkit.eb.exprsem import OP_SEMANTICS, WRITE
    out: list = []
    for toks in disasm.instr_expr_tokens(raw, ins):
        if toks is None:
            continue
        stack: list = []
        for o, v in toks:
            if o == T._EXPR_END:
                break
            if o == T._FLEX:
                del stack[max(0, len(stack) - v[1]):]
                stack.append(None)
                continue
            if o >= 0xC0:
                stack.append(("var", o, v))
                continue
            if o in T._OPERAND_PUSHES:
                stack.append(("tok", _token_text(o, v)))
                continue
            name = EXPR_OP_NAMES.get(o)
            sem = OP_SEMANTICS.get(name)
            if sem is None:
                out.append(None)
                break
            arity, effect = sem
            if effect == WRITE and name not in T._NOT_A_VARIABLE_STORE:
                depth = T._LVALUE_DEPTH.get(name)
                lv = stack[-depth] if depth is not None and len(stack) >= depth else None
                if depth is None or lv is None:
                    out.append(None)
                elif lv[0] == "tok":
                    out.append(lv[1])
                # a var token: resolved by instruction_stores (a global or another source), never unresolved
            del stack[max(0, len(stack) - arity):]
            stack.append(None)
    return out


def lvalue_class(token) -> str | None:
    """An unresolved store's lvalue token -> its class (:data:`LVALUE_CLASSES`), or None: ``B_SYSLIST[n]`` is "a
    battle target list, not gEventGlobal"; nothing else is classified today."""
    if not isinstance(token, str):
        return None
    for rx, why in LVALUE_CLASSES:
        if rx.match(token):
            return why
    return None


def store_sites(idx) -> tuple:
    """``(sites, undecoded)`` of one script: every store instruction_stores finds in EVERY function (each entry's
    each tag, the engine's function table), ``{"sid", "tag", "ip" (entry-relative, the trace's), "kind": "global" |
    "unknown", "target" | "why", "token"}``; and ``["e<sid> t<tag>: why"]`` for each function (or instruction) that
    does not decode."""
    from ff9mapkit.eb._exprtable import VAR_TYPE
    sites, undecoded = [], []
    for e in idx.eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            start, end = f.abs_start, idx._end(e, f)
            try:
                ins_list = idx.instrs(start, end)
            except ValueError as err:
                undecoded.append(f"e{e.index} t{f.tag}: {err}")
                continue
            for ins in ins_list:
                ip = ins.off - e.abs_start
                try:
                    stores = T.instruction_stores(idx.data, ins)
                    toks = iter(unresolved_lvalues(idx.data, ins))
                except ValueError as err:
                    undecoded.append(f"e{e.index} t{f.tag} ip{ip}: {err}")
                    continue
                for s in stores:
                    if s[0] == "global":
                        sites.append({"sid": e.index, "tag": f.tag, "ip": ip, "kind": "global",
                                      "target": f"Global.{VAR_TYPE.get(s[1])}[{s[2]}]",
                                      "text": idx.text_at(start, end, ins.off - start)})
                    elif s[0] == "unknown":
                        sites.append({"sid": e.index, "tag": f.tag, "ip": ip, "kind": "unknown", "why": s[1],
                                      "token": next(toks, None), "text": idx.text_at(start, end, ins.off - start)})
    return sites, undecoded


def scene_name(scene_id: int) -> str:
    """A battle scene's name (``BSC_TH_E002``) from its id, by the kit's scene table (``_scenedb.SCENES``)."""
    from ff9mapkit._scenedb import SCENES
    hits = [n for n, v in SCENES.items() if v == int(scene_id)]
    if len(hits) != 1:
        raise ValueError(f"scene {scene_id}: {len(hits)} names in the scene table ({hits})")
    return hits[0]


_SCENES: dict = {}


def scene_census(name: str, *, game=None) -> dict:
    """O3-SCENE's reader (research/o3_design.md 6.1): the BASE install's copy of battle scene ``name`` (``BSC_<x>``),
    read-only -- its raw16 (``battle.extract.read_scene_assets``, ``scene_codec.parse_scene``: the flags, each type's
    MaxHP, the type and attack counts), its US ``.eb`` walked through every function (:func:`store_sites`: the
    gEventGlobal stores and the unresolved ones with their lvalue tokens; each ``RunBattleCode(37, N)``; each end test
    ``B_SYSLIST[1] B_MEMBER(36) const(c) B_LE_E``), and its US battle text's names (the first TypCount strings the
    enemies', the next AtkCount the attacks' -- the names a BattlePatch name selector matches). Cached per name."""
    if name in _SCENES:
        return _SCENES[name]
    from ff9mapkit import dialogue
    from ff9mapkit.battle import extract as BX
    from ff9mapkit.battle import scene_codec as SC
    short = name[4:] if name.upper().startswith("BSC_") else name
    assets = BX.read_scene_assets(short, game)
    sc = SC.parse_scene(assets["raw16"])
    idx = T.ScriptIndex(assets["eb"]["us"], label=f"EVT_BATTLE_{short}")
    sites, undecoded = store_sites(idx)
    run37, ends = [], []
    for e in idx.eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            start, end = f.abs_start, idx._end(e, f)
            try:
                ins_list = idx.instrs(start, end)
            except ValueError:
                continue                                      # store_sites has named it
            for ins in ins_list:
                text = idx.text_at(start, end, ins.off - start)
                ip = ins.off - e.abs_start
                m = re.match(r"RunBattleCode\(37, (\d+)\)", text)
                if m:
                    run37.append({"sid": e.index, "tag": f.tag, "ip": ip, "field": int(m.group(1))})
                m = re.search(r"B_SYSLIST\[1\] B_MEMBER\(36\) const\((\d+)\) B_LE_E", text)
                if m:
                    ends.append({"sid": e.index, "tag": f.tag, "ip": ip, "c": int(m.group(1))})
    mes = assets["mes"]["us"]
    body = mes.decode("utf-8", errors="replace") if isinstance(mes, (bytes, bytearray)) else str(mes)
    strs = [x.text for _i, x in sorted(dialogue.parse_mes(body).items())]
    out = {"name": name, "short": short, "id": assets["donor_id"], "flags": sc.scene_flags,
           "winpose_off": bool(sc.scene_flags & 0x10), "hp": [m.hp for m in sc.monsters],
           "stores": [s for s in sites if s["kind"] == "global"],
           "unresolved": [s for s in sites if s["kind"] == "unknown"], "undecoded": undecoded,
           "run37": run37, "ends": ends, "enemies": strs[:sc.typ_count],
           "attacks": strs[sc.typ_count:sc.typ_count + sc.atk_count]}
    _SCENES[name] = out
    return out


def _site_row(target: str):
    """A synthetic ``w`` row of ``target`` -- for asking the story-noise mask whether a target is masked."""
    width, index = target.split(".", 1)[1].rstrip("]").split("[")
    bit = int(index) if width in T.BIT_WIDTHS else -1
    return T.Row(k="w", f=0, p=0, m=T.FIELD_MODE, fld=0, don=0, sc=0, src="eb", sid=0, uid=0, lvl=0, ip=0, tag=0,
                 add=0, byte=int(index) >> 3 if bit >= 0 else int(index), width=width, bit=bit, old=0, new=0, same=0)


#: O3-CENSUS's classes, in the order a site is read against them (a masked site counts masked, 61's start_first too).
CENSUS_LISTS = ("writes", "chain", "masked", "start_first", "error_path", "forbidden_sites", "dead")


def store_census(fields, stock, pred: dict, *, sites=None, classify=None) -> tuple:
    """O3-CENSUS's reader (research/o3_design.md 6.1, claim integrity #3): ``(problems, {field: Counter(class)})``.
    Every gEventGlobal store site of each stock field (``sites(idx)`` -> :func:`store_sites`) must be one the
    predictions classify -- a ``writes`` or ``chain`` key's, a story-noise-masked one, ``start_first``, or an
    ``error_path``, ``forbidden_sites`` or ``dead`` key's -- matched on (donor, sid, tag, ip, target); an unresolved
    store must be classified by its lvalue token (``classify`` -> :func:`lvalue_class`); a function that does not
    decode FAILS. Every site outside them is named."""
    sites = sites or store_sites
    classify = classify or lvalue_class
    reg: dict = {}
    for name in ("writes", "chain", "start_first", "error_path", "forbidden_sites", "dead"):
        for k in ([pred[name]] if name == "start_first" else pred.get(name) or ()):
            reg.setdefault((k["donor"], k["sid"], k["tag"], k["ip"], k["target"]), set()).add(name)
    bad, counts = [], {}
    for fid in fields:
        idx = stock(fid)
        c = counts.setdefault(fid, Counter())
        if idx is None:
            bad.append(f"{fid}: no stock script")
            continue
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
            if T.noise_regions(_site_row(s["target"])):
                names = names | {"masked"}
            cls = next((n for n in CENSUS_LISTS if n in names), None)
            if cls is None:
                bad.append(f"{where} {s['target']}: in no list ({s.get('text', '')[:60]})")
            else:
                c[cls] += 1
    return bad, counts


# ======================================================================== the live install (pure readers)
def ini_settings(text: str | None, keys: dict | None = None) -> dict:
    """``{section: {key: raw value}}`` of one Memoria.ini read the ENGINE's way (Memoria.Prime/Ini/IniReader.cs): a
    line whose first letter, digit, ``[``, ``;`` or ``#`` is ``;`` or ``#`` is a comment; ``[name]`` opens a section
    (a trailing ``Section`` trimmed, as ReadSection does); ``key = value`` -- the key from its first letter or digit to
    the ``=``, trimmed at its end, the value after it up to its first ``;``, trimmed. A ``;`` right after that one
    adds a literal ``;``, and any other character then ends the value: ReadPair's escape branch has no ``continue``,
    so the ``;`` it appends arms the escape again (IniReader.cs:169-185) -- ``a;;b`` reads ``a;``, ``a;;;;b`` reads
    ``a;;;``. Sections and keys are CASE-SENSITIVE (the reader's dictionaries use the default comparer), and the LAST
    assignment wins. ``keys`` (``{section: [key, ...]}``, e.g. :data:`SETTINGS`) keeps only those keys -- the ones
    the file sets."""
    out = _ini_read(text)
    if keys is None:
        return out
    return {sec: {k: v for k, v in out.get(sec, {}).items() if k in ks} for sec, ks in keys.items()}


def _ini_read(text: str | None) -> dict:
    """:func:`ini_settings`' reader: every section and key of one ini text, the engine's way."""
    out: dict = {}
    section = None
    for line in (text or "").splitlines():
        i, n = 0, len(line)
        while i < n and not (line[i] in ";#[" or line[i].isalnum()):
            i += 1
        if i >= n or line[i] in ";#":
            continue
        if line[i] == "[":
            j = line.find("]", i + 1)
            if j < 0:
                continue
            name = line[i + 1:j]
            section = name[:-len("Section")] if name.endswith("Section") else name
            continue
        eq = line.find("=", i)
        if eq < 0 or section is None:
            continue
        key = line[i:eq].rstrip()
        value, k, escape = [], eq + 1, False
        while k < n:                                # IniReader.ReadPair's loop, statement for statement
            ch = line[k]
            if escape:
                if ch != ";":
                    break
                value.append(";")
                escape = False
            if ch == ";":                           # no `continue` above: the `;` just appended arms the escape again
                escape = True
            else:
                value.append(ch)
            k += 1
        out.setdefault(section, {})[key] = "".join(value).strip()
    return out


def install_settings(game, roots, want: dict | None = None) -> dict:
    """The settings the engine runs under, ``{section: {key: value | None}}`` for ``want``'s keys (default
    :data:`SETTINGS`): the root Memoria.ini, then each stacked folder's own Memoria.ini over it in REVERSE folder
    order, so the first folder's wins (IniReader.Read reads the mod folders' configuration files after the main one,
    IniReader.cs:94-125). A key no file sets reads None."""
    want = want or SETTINGS
    texts = []
    for p in [Path(game) / "Memoria.ini"] + [Path(r) / "Memoria.ini" for r in reversed(list(roots))]:
        try:
            texts.append(p.read_text(encoding="utf-8-sig", errors="replace"))
        except OSError:
            pass
    merged: dict = {}
    for text in texts:
        for sec, kv in ini_settings(text).items():
            merged.setdefault(sec, {}).update(kv)
    return {sec: {k: merged.get(sec, {}).get(k) for k in keys} for sec, keys in want.items()}


def p_settings(want: dict, got: dict) -> tuple:
    """P-SETTINGS (6.2): ``(ok, detail)`` -- every frozen key equal, raw; a FAIL names each difference."""
    diff = [f"[{sec}] {k} = {(got.get(sec) or {}).get(k)!r} (frozen {v!r})" for sec, kv in want.items()
            for k, v in kv.items() if (got.get(sec) or {}).get(k) != v]
    n = sum(len(kv) for kv in want.values())
    return (not diff, "; ".join(diff) if diff else
            f"{n} keys as frozen: " + "; ".join(f"[{sec}] " + ", ".join(f"{k} {v}" for k, v in kv.items())
                                                 for sec, kv in want.items()))


def donor_log(log_text: str | None, donors) -> tuple:
    """P-DONOR-LOG's reader (6.2): ``(initialized, [warning lines naming one of donors])`` in a Memoria.log --
    whether the launch logged "[DataPatchers] Initialized" (the patchers ran) and every "[DataPatchers]
    ForkDonorPatch: donor field <d> is forked by both ..." line for a donor in ``donors`` (DataPatchers.cs:156-160)."""
    text = log_text or ""
    want = {int(d) for d in donors}
    lines = []
    for ln in text.splitlines():
        m = DONOR_WARNING.search(ln)
        if m and int(m.group(1)) in want:
            lines.append(ln.strip())
    return DATAPATCHERS_DONE in text, lines


def p_donor_log(log_text: str | None, donors) -> tuple:
    """P-DONOR-LOG: ``(ok, detail)`` -- the launch's patchers ran, and logged no donor collision for ``donors``
    (the redirect's donor map is fixed at launch; a collision there disables it whatever the files say now)."""
    init, lines = donor_log(log_text, donors)
    others = sorted({int(m.group(1)) for m in DONOR_WARNING.finditer(log_text or "")} - {int(d) for d in donors})
    if not init:
        return False, (f"no '{DATAPATCHERS_DONE}' line: this log does not show the patchers ran (no launch, or "
                       f"another log)")
    if lines:
        return False, (f"{len(lines)} collision line(s) for the route's donors: "
                       + " | ".join(ln[ln.find('[DataPatchers]'):][:120] for ln in lines[:3]))
    return True, (f"the patchers ran; no ForkDonorPatch collision for {sorted(int(d) for d in donors)} (collisions "
                  f"logged for other donors: {others or 'none'})")


def launch_time(log_text: str | None):
    """P-LAUNCH's reader: the launch's first Memoria.log line's stamp (``dd.MM.yyyy HH:mm:ss``, local) as a
    datetime, or None (no stamp: the launch cannot be dated)."""
    lines = (log_text or "").splitlines()
    m = LOG_STAMP.match(lines[0]) if lines else None
    if m is None:
        return None
    d, mo, y, hh, mm, ss = (int(x) for x in m.groups())
    try:
        return _dt.datetime(y, mo, d, hh, mm, ss)
    except ValueError:
        return None


def launch_files(game, roots) -> dict:
    """``{path: mtime}`` of what the launch read and the preflight reads: every stacked folder's four patch files
    (:data:`PATCH_FILES`, those that exist), the root Memoria.ini and any stacked folder's own Memoria.ini (the
    engine's configuration reads those too)."""
    out = {}
    paths = [Path(game) / "Memoria.ini"] + [Path(r) / f for r in roots for f in PATCH_FILES + ("Memoria.ini",)]
    for p in paths:
        try:
            out[str(p)] = p.stat().st_mtime
        except OSError:
            pass
    return out


def launch_check(files: dict, launched) -> tuple:
    """P-LAUNCH (6.2, claim integrity #1): ``(ok, detail)`` -- every file's mtime, truncated to the second, must be
    EARLIER than the launch's stamp: a same-second or later mtime FAILS ("relaunch: ..."), and so does a launch with
    no stamp. A folder with no patch file has nothing to date."""
    if launched is None:
        return False, ("relaunch: the launch cannot be dated -- its first Memoria.log line carries no dd.MM.yyyy "
                       "HH:mm:ss stamp")
    stamp = launched.strftime("%d.%m.%Y %H:%M:%S")
    bad = []
    for path, mtime in sorted(files.items()):
        at = _dt.datetime.fromtimestamp(int(mtime))
        if not at < launched:
            bad.append(f"relaunch: {path} changed at {at.strftime('%d.%m.%Y %H:%M:%S')}, at or after this launch "
                       f"began at {stamp}")
    newest = max(files.values()) if files else None
    return (not bad, "; ".join(bad[:4]) if bad else
            f"{len(files)} file(s) older than the launch at {stamp}"
            + (f" (the newest {_dt.datetime.fromtimestamp(int(newest)).strftime('%d.%m.%Y %H:%M:%S')})"
               if newest is not None else ""))


def battle_selectors(text: str | None) -> list:
    """``[(opcode, oparg)]`` of a BattlePatch.txt's lines read the engine's way (DataPatchers.PatchBattles,
    :690-709): a line starting ``//`` skipped; the rest trimmed of spaces, tabs, line ends and ``=``, split once on a
    space; the opcode's trailing ``:`` dropped."""
    out = []
    for line in (text or "").splitlines():
        if line.startswith("//"):
            continue
        parts = [p for p in line.strip(" \t\r\n=").split(" ", 1) if p]
        if len(parts) != 2:
            continue
        out.append((parts[0].rstrip(":"), parts[1]))
    return out


def battle_overrides(root) -> list:
    """Every path under mod folder ``root`` (relative, ``/``-joined, sorted) a battle-scene override names: each
    ``EVT_BATTLE_*`` directory or file (``BattleMap/BattleScene/EVT_BATTLE_<x>/`` raw16 and raw17,
    ``EventBinary/Battle/<lang>/EVT_BATTLE_<x>.eb.bytes``)."""
    root = Path(root)
    out = []
    for dp, dn, fn in os.walk(root):
        for x in dn + fn:
            if "evt_battle_" in x.lower():
                out.append((Path(dp) / x).relative_to(root).as_posix())
    return sorted(out)


#: Int32.TryParse's default NumberStyles.Integer: white space either side, one leading sign, ASCII digits.
_INT32 = re.compile(r"[ \t\n\v\f\r]*[+-]?[0-9]+[ \t\n\v\f\r]*")


def _int32(text: str):
    """``text`` as Int32.TryParse reads it, or None (it does not parse, or it is out of range)."""
    if not _INT32.fullmatch(text):
        return None
    v = int(text)
    return v if -2 ** 31 <= v < 2 ** 31 else None


def battle_scene_lines(text: str | None) -> list:
    """``[(id, name, line)]``: every ``BattleScene`` line of one DictionaryPatch.txt as the engine reads it
    (DataPatchers.PatchDictionaries, :255-257 and :565-575): the file's lines (File.ReadAllLines), each split on
    single spaces; ``entry[0]`` exactly "BattleScene" with at least four entries and ``entry[1]`` an Int32
    (Int32.TryParse) -- any other line is skipped, as the engine skips it. Such a line sets
    ``SceneData["BSC_" + name] = id`` -- a TwoWayDictionary without duplicate values, so its setter also overwrites
    the reverse entry ``id -> BSC_<name>`` (TwoWayDictionary.cs), the one a battle's scene is looked up by
    (HonoluluBattleMain.cs:198: its raw17, its sequence, its text and ``EVT_BATTLE_<name>``) -- and
    ``MapModel["BSC_" + name]``, its background."""
    out = []
    for line in re.split(r"\r\n|\r|\n", text or ""):
        entry = line.split(" ")
        if len(entry) < 4 or entry[0] != "BattleScene":
            continue
        sid = _int32(entry[1])
        if sid is not None:
            out.append((sid, entry[2], line))
    return out


def dictionary_battle_scenes(root) -> list:
    """``[[id, name], ...]``: the ``BattleScene`` lines of mod folder ``root``'s DictionaryPatch.txt (none when it has
    none), read as :func:`battle_scene_lines` reads them (UTF-8, a BOM dropped as File.ReadAllLines drops it)."""
    try:
        text = (Path(root) / "DictionaryPatch.txt").read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return []
    return [[sid, nm] for sid, nm, _ln in battle_scene_lines(text)]


def battle_stock(roots, scene_id: int, names, *, name: str | None = None) -> tuple:
    """P-STOCK-BATTLE (6.2, claim integrity #4): ``(ok, detail, info)`` -- battle ``scene_id`` is STOCK on both sides,
    over every stacked folder: (a) no file whose path names ``EVT_BATTLE_<x>`` (case-insensitive: its scene
    directory's raw16/raw17, its battle .eb in any language); (b) no BattlePatch.txt selector that reaches it
    (DataPatchers.cs:747-783): ``Battle:`` naming its id, ``BSC_<x>`` or ``<x>``, or a name selector
    (``AnyEnemyByName:`` / ``AnyAttackByName:``) naming one of its enemy or attack names (``names``, its US text: a
    name selector applies to every scene holding the name); (c) no DictionaryPatch.txt ``BattleScene`` line
    (:func:`battle_scene_lines`) whose id is ``scene_id`` -- it rebinds the battle to another scene, script and
    background, with no file under the stock name and no selector -- or whose name is ``<x>`` -- it repoints
    ``BSC_<x>``'s forward entry, which the battle's sequence (btlseq.cs:24) and text (HonoluluBattleMain.cs:202) are
    read by, and its background (``MapModel``). A name selector naming anything else, and every other BattleScene line,
    passes, listed. (A ``FieldScene`` line on the id sets only ``EventDB[id]``, which a battle never reads: its script
    is ``"EVT_BATTLE_" + name``, HonoluluBattleMain.cs:198-215.)"""
    name = name or scene_name(scene_id)
    short = name[4:] if name.upper().startswith("BSC_") else name
    needle = f"evt_battle_{short.lower()}"
    names = set(names)
    bad, over, sels, bsc = [], {}, {}, {}
    for r in roots:
        r = Path(r)
        paths = battle_overrides(r)
        over[r.name] = paths
        for p in paths:
            if any(c.lower() == needle or c.lower().startswith(needle + ".") for c in p.split("/")):
                bad.append(f"(a) {r.name}/{p} overrides {name}")
        try:
            text = (r / "BattlePatch.txt").read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = None
        found = battle_selectors(text)
        sels[r.name] = [[op, arg] for op, arg in found if op in ("Battle", "AnyEnemyByName", "AnyAttackByName")]
        for op, arg in found:
            a = arg.strip()
            if op == "Battle" and a in (str(scene_id), name, short):
                bad.append(f"(b) {r.name}/BattlePatch.txt 'Battle: {a}' selects {name}")
            elif op in ("AnyEnemyByName", "AnyAttackByName") and a in names:
                bad.append(f"(b) {r.name}/BattlePatch.txt '{op}: {a}' names one of {name}'s enemies or attacks")
        try:
            dtext = (r / "DictionaryPatch.txt").read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            dtext = None
        lines = battle_scene_lines(dtext)
        bsc[r.name] = [[sid, nm] for sid, nm, _ln in lines]
        for sid, nm, ln in lines:
            if sid == int(scene_id):
                bad.append(f"(c) {r.name}/DictionaryPatch.txt '{ln.strip()}' rebinds battle {scene_id} to BSC_{nm} "
                           f"(the reverse entry its scene is looked up by)")
            elif nm == short:
                bad.append(f"(c) {r.name}/DictionaryPatch.txt '{ln.strip()}' repoints BSC_{short} to {sid} (battle "
                           f"{scene_id}'s sequence, text and background)")
    scenes = sorted({p.split("/")[-1].split(".")[0] for ps in over.values() for p in ps})
    by = "; ".join(f"{n} " + ", ".join(f"{op}: {arg}" for op, arg in s) for n, s in sels.items() if s)
    named = [f"{n} {op}: {arg}" for n, s in sels.items() for op, arg in s if op != "Battle"]
    dict_lines = "; ".join(f"{n} " + ", ".join(f"{sid} {nm}" for sid, nm in s) for n, s in bsc.items() if s)
    detail = ("; ".join(bad[:6]) if bad else
              f"no stacked folder overrides {name} (the stack's battle-scene overrides: {', '.join(scenes) or 'none'}"
              f"); BattlePatch selectors: {by or 'none'}; "
              + (f"name selectors (none naming {name}'s): {named}" if named else "no name selector")
              + f"; DictionaryPatch BattleScene lines (none on {scene_id} or {short}): {dict_lines or 'none'}")
    return not bad, detail, {"overrides": over, "selectors": sels, "battle_scenes": bsc}


def p_donor(pred: dict, roots) -> tuple:
    """P-DONOR (6.2): ``(ok, detail)`` -- every route donor appears in exactly ONE ForkDonorPatch row across every
    stacked folder, its member's: a donor forked twice sets ``ForkSiblingMap[donor] = -1`` (DataPatchers.cs:156-160)
    and battle 338 would leak a fork run into real 63."""
    from rung3_trace import _fork_donor_rows
    rows = [(Path(r).name, f, d) for r in roots for f, d in _fork_donor_rows(Path(r))]
    members = members_of(pred)
    bad, parts = [], []
    for donor in pred["route"]:
        member = next((f for f, d in sorted(members.items()) if d == donor), None)
        hits = [(n, f) for n, f, d in rows if d == donor]
        if [f for _n, f in hits] != [member]:
            bad.append(f"donor {donor}: ForkDonorPatch rows {[f'{n}: {f} {donor}' for n, f in hits]}, want exactly "
                       f"one, '{member} {donor}'")
        else:
            parts.append(f"{donor} -> {member} ({hits[0][0]})")
    dup = sorted(d for d, n in Counter(d for _n, _f, d in rows).items() if n > 1)
    return (not bad, "; ".join(bad) if bad else
            ", ".join(parts) + f"; donors forked twice elsewhere in the stack: {dup or 'none'} (none on the route)")


# ======================================================================== a trace, summarised
def trace_summary(rows: list, pred: dict, *, side: str = "S", start_place: int | None = None, end_fields=None,
                  stock=None, scripts=None, log: list | None = None) -> dict:
    """One trace, summarised for a reader (research/o3_design.md 7.2; the rehearsal report and the dry run): O2's
    shape for O3's lists -- the run cut at its start row and its end, the SC rows (there must be none) and the
    FieldEntrance chain (raw rows with their joined keys), every registered key present or absent (the chain, the
    writes, the error path, the forbidden and dead sites: those three must be absent), every UNREGISTERED key (the
    battle noise aside, counted), the battle-mode rows (``w`` count -- 0 allowed --, their sites and fields, the
    ``c`` rows), the first field row after 62 ip1285 (``landing.before``), the end cut's raw row, the residue before
    and after the start, the masked counts, the join failures, and -- given the run's driver ``log`` -- its forbidden
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
    bw = [x for x in kept if x.k == "w" and x.m != T.FIELD_MODE]
    bc = [x for x in kept if x.k == "c" and x.m != T.FIELD_MODE]
    landing = pred.get("landing") or {}
    after_before = None
    b = landing.get("before")
    if b:
        i = next((j for j, x in enumerate(kept) if x.k == "w" and x.m == T.FIELD_MODE
                  and place(x.fld, members) == b["place"]
                  and (x.sid, x.tag, x.ip, x.target, x.new) == (b["sid"], b["tag"], b["ip"], b["target"], b["value"])),
                 None)
        if i is not None:
            nxt = next((x for x in kept[i + 1:] if x.k == "w" and x.m == T.FIELD_MODE), None)
            after_before = None if nxt is None else A._row_text(nxt)
    cut_row = next((x for x in rows if x.line == end), None) if end is not None else None
    hits = []
    if log is not None:
        for h in SD.forbidden_hits(kept, pred, members, sp, end_fields=ends):
            bk = SD.backing(h, log, pred)
            hits.append({"row": SD._hit_row(h), "why": h["why"], "cause": h["cause"], "backed": bk is not None,
                         "by": None if bk is None else bk["what"]})
    keys = sorted(d.keys, key=T.WriteKey.sort_key)
    return {"start": at, "end": end, "rows": len(kept),
            "residue_before": [[x.fld, x.byte, x.old, x.new] for x in pre if x.k == "r"],
            "pre_other": [A._row_text(x) for x in pre if x.k == "w"],
            "residue_after": [[x.fld, x.byte, x.old, x.new, bool(T.noise_regions(x))] for x in kept if x.k == "r"],
            "sc": seq(pred.get("sc_bytes") or (0, 1)), "entrance": seq(pred.get("entrance_bytes") or (2, 3)),
            "registered": registered,
            "unregistered": [A._fmt_key(k) for k in keys if k not in reg and not is_noise(k, pred)],
            "noise_keys": sum(1 for k in keys if is_noise(k, pred)),
            "battle": {"w": len(bw), "sites": sorted({f"m{x.m} e{x.sid} t{x.tag} ip{x.ip} {x.target}" for x in bw + bc}),
                       "flds": sorted({x.fld for x in bw + bc}), "c": [[x.fld, x.n, x.last] for x in bc]},
            "after_before": after_before,
            "end_row": None if cut_row is None else (f"{cut_row.k} " + (A._row_text(cut_row) if cut_row.k == "w"
                                                                       else f"{cut_row.fld} byte {cut_row.byte}")),
            "seam_keys": [A._fmt_key(k) for k in sorted(d.seam_keys, key=T.WriteKey.sort_key)],
            "masked": dict(d.masked), "residue_masked": d.residue_masked,
            "failures": [[A._row_text(r), why[:160]] for r, why in d.failures], "forbidden": hits}


# ======================================================================== O3 on the shared engine
class O3Segment(A.O2Segment):
    """O3 on O2's segment (research/o3_design.md 1.3): its constants and check texts, the draft predictions, the
    offline checks (O3-BUILD as a US session's, O3-TEXT, O3-KEYS on a filtered copy, O3-REGIONS, O3-SCENE,
    O3-CENSUS), the preflight extras (P-TEXT, P-RECOVERY, P-DONOR, P-SETTINGS, P-STOCK-BATTLE) and in-game
    capabilities (P-CAP, P-OBJECTS, P-LANG, P-DONOR-LOG, P-LAUNCH), the fingerprint extras, A-START, the core checks
    (START, NO-SC, CHAIN, RESIDUE, WRITES exact, NULL, STABLE, SEAM, LANDING, BATTLE, MASKED, STATE, JOIN) and O3's
    report. The session loop, the cuts, the digest, the comparison, the all-run checks and the verdict are the shared
    engine's; ``end_session_warps`` ends the session through end_run (S5)."""

    tag = "O3"
    doc = _MODULE_DOC
    predictions = PREDICTIONS
    manifest = MANIFEST
    session_file = SESSION_FILE
    report_file = REPORT_FILE
    chain_dir = CHAIN_DIR
    build_dir = BUILD_DIR
    accept_us_build = True                # O1's legacy build: the members' other languages are US bytecode (0.1)
    recovery = 4600
    end_session_warps = True              # S5: a last run stopped in 61 mid-FMV003 must not leave the game there
    core_ids = ("START", "NO-SC", "CHAIN", "RESIDUE", "WRITES", "NULL", "STABLE", "SEAM", "LANDING", "BATTLE",
                "MASKED", "STATE", "JOIN")
    titles = {
        "P-CAP": "P-CAP: the engine advertises the story trace at proto 1",
        "P-OBJECTS": "P-OBJECTS: the engine publishes the field's objects (s89): the presses' near evidence and "
                     "F-SMOKE's object sids read them",
        "P-LANG": "P-LANG: the running game's text is English(US), the language the keys, joins and text were "
                  "checked in (a US session)",
        "P-DONOR-LOG": "P-DONOR-LOG: this launch's Memoria.log shows the patchers ran and logged no ForkDonorPatch "
                       "collision for 61, 62 or 63",
        "P-LAUNCH": "P-LAUNCH: every stacked patch file and Memoria.ini is older than this launch (the launch read "
                    "what the preflight read)",
        "P-MANIFEST": "P-MANIFEST: the frozen members are the deployed chain's (o3_forks.json: O1's, deployed)",
        "P-DEPLOY": "P-DEPLOY: every member registered once under its name, and mapped once to its donor",
        "P-EB": "P-EB: every member's live .eb (7 languages) is the offline-checked build's",
        "P-FLOOR": "P-FLOOR: every member's deployed walkmesh is its donor's",
        "P-STOCK": "P-STOCK: no mod folder overrides stock 61, 62, 63 or 64",
        "P-TEXT": "P-TEXT: every mod folder's text block 2 is each language's stock asset, read by its resource path "
                  "(another language's copy a named KNOWN-KIT-DEFECT)",
        "P-RECOVERY": "P-RECOVERY: the recovery field 4600 is registered in a mod folder",
        "P-DONOR": "P-DONOR: each route donor (61, 62, 63) is forked by exactly one ForkDonorPatch row in the stack, "
                   "its member's",
        "P-SETTINGS": "P-SETTINGS: the battle, cheat, hack and control settings are the frozen ones (Memoria.ini read "
                      "the engine's way)",
        "P-STOCK-BATTLE": "P-STOCK-BATTLE: battle 338 is stock on both sides: no stacked folder overrides its scene or "
                          "script, no BattlePatch selector reaches it, and no DictionaryPatch BattleScene line rebinds "
                          "it",
        "BUILD": "O3-BUILD: a US session's build: every member's US .eb is its donor's with only in-chain Field() "
                 "literals remapped; each other language is its own donor's or the us build (the kit before "
                 "3d8b7f1b), so the claim holds for a US session only",
        "TEXT": "O3-TEXT: the build's text block 2 is each language's stock asset, read by its resource path (the "
                "session language exactly; another language's copy a named KNOWN-KIT-DEFECT)",
        "KEYS": "O3-KEYS: every registered key -- writes, chain, error path, forbidden and dead sites, start_first -- "
                "is a store of its variable at its ip in the donor's stock bytes, its op in the statement, its value "
                "computed",
        "REGIONS": "O3-REGIONS: every gateway and hot-spot of the route fields is registered (61-63 hold none)",
        "SCENE": "O3-SCENE: each registered battle's own scene: won exactly as its WinPose flag allows, its next field "
                 "the row's lands, its one gEventGlobal store the landing's battle site, every unresolved store "
                 "classified, its end test below its leader's HP",
        "CENSUS": "O3-CENSUS: every gEventGlobal store site of 61, 62 and 63 is registered (writes, chain, masked, "
                  "start_first, error path, forbidden, dead) and every unresolved store classified",
        "FROZEN": "O3-FROZEN: the predictions are the file the session recorded, unchanged",
        "COVER": "O3-COVER: at least {min_covered} covered runs a side",
        "FORBIDDEN": "O3-FORBIDDEN: no run carries a forbidden write its own driver log does not explain",
        "VOID-ASYM": "O3-VOID-ASYM: no game-caused VOID class on one side only, and no side VOID in one class in "
                     "every run",
        "START": "O3-START: every covered run starts at 61's Main_Init after only the warp's own residue, and 61 takes "
                 "its ambient branch from the warp's Byte[13] 1",
        "NO-SC": "O3-NO-SC: no row touches bytes 0-1 (SC) after the start: SC holds 1155 throughout",
        "CHAIN": "O3-CHAIN: bytes 2-3 (FieldEntrance) carry exactly the chain, in order, each from the last",
        "RESIDUE": "O3-RESIDUE: no unmasked residue after the start beyond the registered",
        "WRITES": "O3-WRITES: every covered run's story keys are EXACTLY the registered writes and chain (the battle "
                  "noise aside)",
        "NULL": "O3-NULL: STOCK ONLY and FORK ONLY are empty outside the registered noise",
        "STABLE": "O3-STABLE: no key outside the registered noise is written in some runs of a side and not others",
        "SEAM": "O3-SEAM: the fork side never left its members before member(63)'s Field(64)",
        "LANDING": "O3-LANDING: every row ran in its place's own field, the battle's rows are its one store, 63 loaded "
                   "fresh from the battle, 63 is the last place, and the end cut is 64's first store",
        "BATTLE": "O3-BATTLE: the driver fought exactly the registered battle -- scene 338 in 62, the drive's next "
                  "epoch, landed in 63 (member(63) on F) -- at the 62 -> 63 boundary",
        "MASKED": "O3-MASKED: the story-noise regions written are the same on both sides",
        "STATE": "O3-STATE: the state handed to 64 is the same: each target's emitted write history in order (its "
                 "suppressed stores as a set), and the end state read live",
        "JOIN": "O3-JOIN: every script row joins a store in the bytes its field ran",
        "THROW": "O3-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
    }

    # -- the predictions --------------------------------------------------------------------------------------
    def draft(self) -> dict:
        return draft_predictions()

    def freeze(self, path=None) -> str:
        """The freeze, once (the base's: LF, sorted keys, never over an existing file) -- after every registry row
        passes :func:`segment_drive.battle_of` against the draft and every stop page its check (2.1): a row that
        would count a defeat won, or a beat something else sets, is refused before anything is written."""
        pred = self.draft()
        for b in pred.get("battles") or ():
            SD.battle_of(pred, b)
        for p in pred.get("stop_pages") or ():
            SD._check_stop_page(p)
        return super().freeze(path)

    # -- offline ------------------------------------------------------------------------------------------------
    def offline_extra(self, pred: dict, build=None) -> list:
        stock = self.stock_source()
        return [self.text_check(pred, build), self.regions_check(pred, stock), self.scene_check(pred),
                self.census_check(pred, stock)]

    def keys_check(self, pred: dict, stock, lists=None) -> tuple:
        """O3-KEYS (6.1): O2's machinery on a filtered copy -- no ladder, no start-dependent keys, no noise (O3's one
        pattern is O1's legacy battle-mode form, which has no field site to join: O3-SCENE proves it), and the
        error path and the dead sites proven with the forbidden one. ``start_music`` must be the ``writes`` key at
        its site."""
        ok, what, detail = super().keys_check({**pred, "ladder": [], "start_dependent": [], "noise": [],
                                                "forbidden_sites": (list(pred["forbidden_sites"]) + list(pred["error_path"])
                                                                    + list(pred["dead"]))}, stock)
        sm = pred.get("start_music")
        if sm is not None:
            same = [k for k in pred["writes"] if all(k[f] == sm[f] for f in ("donor", "m", "src", "sid", "tag", "ip",
                                                                               "off", "target", "value", "op"))]
            if len(same) != 1:
                ok = False
                detail = (f"start_music ({sm['donor']} e{sm['sid']} t{sm['tag']} ip{sm['ip']} {sm['target']} := "
                          f"{sm['value']}) is {len(same)} writes keys, not one; " + detail)
        return ok, what, detail.replace("O2-START", "O3-START")

    def scene_check(self, pred: dict, *, census=None, classify=None) -> tuple:
        """O3-SCENE (6.1): for every ``battles`` row, its scene as :func:`scene_census` reads the BASE install's
        copy (P-STOCK-BATTLE proves that copy is the one that loads, on both sides): ``won`` is EXACTLY what the
        WinPose flag allows ([1, 2] with it off, flags & 0x10; [1] with it on); entry 0 tag 0's ``RunBattleCode(37,
        N)`` gives N == ``lands``; the scene's gEventGlobal stores are exactly ``landing.battle``'s site, and the
        noise pattern's target is that site's; every unresolved store is classified by its lvalue token
        (``classify`` -> :func:`lvalue_class`), each other one FAILED by name; entry 1 tag 1 holds the end test
        ``B_SYSLIST[1] B_MEMBER(36) const(c) B_LE_E`` with c below type 0's MaxHP. ``census(name)`` replaces the
        install read (a seam for the dry run)."""
        classify = classify or lvalue_class
        bad, lines = [], []
        lb = pred["landing"]["battle"]
        want_site = (lb["sid"], lb["tag"], lb["ip"], lb["target"])
        for n, row in enumerate(pred.get("battles") or ()):
            lab = f"row {n} (scene {row['scene']})"
            try:
                name = scene_name(row["scene"])
                c = census(name) if census is not None else scene_census(name)
            except (OSError, ValueError, KeyError) as err:
                bad.append(f"{lab}: the scene is unreadable: {str(err)[:160]}")
                continue
            allowed = [1, 2] if c["winpose_off"] else [1]
            pose = "off" if c["winpose_off"] else "on"
            if list(row["won"]) != allowed:
                bad.append(f"{lab}: won {row['won']}, but flags {c['flags']:#x} (WinPose {pose}) allow exactly "
                           f"{allowed}")
            lands = [x["field"] for x in c["run37"] if (x["sid"], x["tag"]) == (0, 0)]
            if lands != [row["lands"]]:
                bad.append(f"{lab}: entry 0 tag 0's RunBattleCode(37, N) gives {lands}, the row lands {row['lands']}")
            got = [(s["sid"], s["tag"], s["ip"], s["target"]) for s in c["stores"]]
            if got != [want_site]:
                bad.append(f"{lab}: its gEventGlobal stores are "
                           + (", ".join(f"e{s} t{t} ip{i} {g}" for s, t, i, g in got) or "none")
                           + f"; landing.battle names e{lb['sid']} t{lb['tag']} ip{lb['ip']} {lb['target']}")
            noise = [x.get("target") for x in pred.get("noise") or ()]
            if noise != [lb["target"]]:
                bad.append(f"{lab}: the noise names {noise}, but the battle's one store is {lb['target']}")
            uncl = [u for u in c["unresolved"] if classify(u.get("token")) is None]
            if uncl:
                bad.append(f"{lab}: {len(uncl)} unresolved store(s) no class covers: "
                           + ", ".join(f"e{u['sid']} t{u['tag']} ip{u['ip']} ({u.get('token')})" for u in uncl))
            if c["undecoded"]:
                bad.append(f"{lab}: {len(c['undecoded'])} function(s) do not decode: {c['undecoded'][:2]}")
            hp0 = c["hp"][0] if c["hp"] else None
            ends = [x for x in c["ends"] if (x["sid"], x["tag"]) == (1, 1)]
            if not ends or hp0 is None or not ends[0]["c"] < hp0:
                bad.append(f"{lab}: entry 1 tag 1 holds no end test B_SYSLIST[1] B_MEMBER(36) const(c) B_LE_E below "
                           f"type 0's MaxHP {hp0} (found {[x['c'] for x in ends]})")
                continue
            toks = Counter(u.get("token") for u in c["unresolved"])
            classes = sorted({classify(u.get("token")) or "unclassified" for u in c["unresolved"]})
            lines.append(f"{row['scene']} {name}, the base install's copy (P-STOCK-BATTLE: the one that loads): flags "
                         f"{c['flags']:#x} (WinPose {pose}: won exactly {allowed}); RunBattleCode(37, {lands[0] if lands else '?'}) "
                         f"= lands {row['lands']}; {len(c['stores'])} gEventGlobal store(s): "
                         + ", ".join(f"{s['target']} at e{s['sid']} t{s['tag']} ip{s['ip']}" for s in c["stores"])
                         + f"; {len(c['unresolved'])} unresolved stores, all "
                         + ", ".join(f"{t} x{n}" for t, n in sorted(toks.items(), key=str))
                         + f" ({'; '.join(classes)}); end at cur.hp <= {ends[0]['c']} of {hp0} (>= "
                         f"{hp0 - ends[0]['c']} damage)")
        return not bad, self.title("SCENE"), "; ".join(bad[:6]) or "; ".join(lines) or "no registered battle"

    def census_check(self, pred: dict, stock, *, sites=None, classify=None) -> tuple:
        """O3-CENSUS (6.1): :func:`store_census` over the route's stock fields -- every site classified, or each
        named."""
        fields = list(pred["route"])
        bad, counts = store_census(fields, stock, pred, sites=sites, classify=classify)
        if bad:
            return False, self.title("CENSUS"), f"{len(bad)} site(s) unclassified: " + "; ".join(bad[:8])
        tot = {f: sum(v for k, v in counts[f].items() if k != "unresolved") for f in fields}
        sf = pred["start_first"]
        sf_masked = bool(T.noise_regions(_site_row(sf["target"])))
        short = {"forbidden_sites": "forbidden"}
        cols = ", ".join(f"{short.get(n, n)} " + "/".join(str(counts[f].get(n, 0)) for f in fields)
                         + (f" ({sf['donor']}'s ip{sf['ip']} is start_first)" if n == "masked" and sf_masked else "")
                         for n in CENSUS_LISTS if n != "start_first" or any(counts[f].get(n) for f in fields))
        unres = sum(counts[f].get("unresolved", 0) for f in fields)
        return (True, self.title("CENSUS"),
                ", ".join(f"{f}: {tot[f]}" for f in fields) + f" store sites -- all classified ({cols}); {unres} "
                                                                f"unresolved")

    # -- the live install (read-only) ---------------------------------------------------------------------------
    def preflight_extra(self, pred: dict, roots: list) -> list:
        """O2's (P-TEXT on block 2, P-RECOVERY), then P-DONOR, P-SETTINGS and P-STOCK-BATTLE."""
        out = super().preflight_extra(pred, roots)
        ok, detail = p_donor(pred, roots)
        out.append((ok, self.title("P-DONOR"), detail))
        want = pred.get("settings") or SETTINGS
        ok, detail = p_settings(want, install_settings(GAME, roots, want))
        out.append((ok, self.title("P-SETTINGS"), detail))
        out += [self.stock_battle_check(pred, roots)]
        return out

    def stock_battle_check(self, pred: dict, roots: list, *, census=None) -> tuple:
        """P-STOCK-BATTLE over every registered battle (:func:`battle_stock`), its names from its own US text."""
        bad, parts = [], []
        for row in pred.get("battles") or ():
            try:
                name = scene_name(row["scene"])
                c = census(name) if census is not None else scene_census(name)
            except (OSError, ValueError, KeyError) as err:
                bad.append(f"scene {row['scene']}: unreadable: {str(err)[:160]}")
                continue
            ok, detail, _info = battle_stock(roots, row["scene"], c["enemies"] + c["attacks"], name=name)
            (parts if ok else bad).append(detail)
        return not bad, self.title("P-STOCK-BATTLE"), "; ".join(bad) or "; ".join(parts) or "no registered battle"

    def fingerprint_extra(self, roots: list, pred: dict) -> dict:
        """6.3: O2's (field 70's override, block 2's text per folder, the game's language), then ``settings`` (the
        engine's reading of the frozen keys), ``battle_patch`` (each folder's BattlePatch.txt sha, None when absent),
        ``battle_overrides`` (each folder's battle-scene override paths) and ``battle_scenes`` (each folder's
        DictionaryPatch BattleScene lines, ``[id, name]``: a battle-scene registration deployed mid-session is
        A-INSTALL, as a BattlePatch deploy is)."""
        out = super().fingerprint_extra(roots, pred)
        out["settings"] = install_settings(GAME, roots, pred.get("settings") or SETTINGS)
        out["battle_patch"] = {Path(r).name: _sha_file(Path(r) / "BattlePatch.txt") for r in roots}
        out["battle_overrides"] = {Path(r).name: battle_overrides(r) for r in roots}
        out["battle_scenes"] = {Path(r).name: dictionary_battle_scenes(r) for r in roots}
        return out

    # -- the session --------------------------------------------------------------------------------------------
    def capabilities(self, g) -> list:
        """O2's (P-CAP, P-OBJECTS, P-LANG), then P-DONOR-LOG and P-LAUNCH on this launch's Memoria.log -- the
        launch's own donor map, which no file read alone can show (6.2). The stacked folders are the driven game's
        (its Memoria.ini's ``[Mod] FolderNames``)."""
        import dali_tour as D
        from harness.logs import MEMORIA_LOG
        out = super().capabilities(g)
        log = next((p for name, p in g._log_paths() if name == MEMORIA_LOG), None)
        try:
            text = log.read_text(encoding="utf-8", errors="replace") if log is not None else None
        except OSError:
            text = None
        ok, detail = p_donor_log(text, ROUTE)
        out.append((ok, self.title("P-DONOR-LOG"), detail))
        game = Path(g.game_path)
        try:
            roots = D.mod_roots(game)
        except OSError:
            roots = []
        ok, detail = launch_check(launch_files(game, roots), launch_time(text))
        out.append((ok, self.title("P-LAUNCH"), detail))
        return out

    # -- reading a session ---------------------------------------------------------------------------------------
    def why_void(self, rec: dict, r: dict, pred: dict) -> list:
        """O2's reasons (A-NOSTART, A-FORBIDDEN, A-MISMATCH), then A-START (5.1): the run's rows hold a registered
        ``error_path`` site of the START place -- the warp's incoming Byte[13]/[14] took 61's error path -- and
        A-NOEND (5.1, the review's 11.7 #3): the drive reached the end and its trace reads whole, yet holds no row in
        an end place, so there is no end cut -- the trace was collected before the end field's first store (the
        end-collection race: story-o1e's run 3 S, covered there). Real 64 is the same field on both sides, so the
        missing row says nothing about the fork: the run is the driver's, never O3-LANDING (e)'s finding. Also keeps
        the end cut's raw row on ``r`` (``cut_row``) for O3-LANDING (e)."""
        out = super().why_void(rec, r, pred)
        members = members_of(pred) if r["side"] == "F" else {}
        sp = place(pred["start"][r["side"]], members)
        errs = {(k["sid"], k["tag"], k["ip"], k["target"]) for k in pred.get("error_path") or () if k["donor"] == sp}
        hit = next((x for x in r["rows"] if x.k == "w" and x.m == T.FIELD_MODE and place(x.fld, members) == sp
                    and (x.sid, x.tag, x.ip, x.target) in errs), None)
        if hit is not None:
            out.append((f"the start state took {sp}'s error path: {A._row_text(hit)}", "A-START", "driver"))
        if rec.get("end") == "reached" and r["digest"] is not None and r["cut"] is None:
            ends = list(pred.get("end_fields") or [pred["end_field"]])
            er = next((x.get("end_row") for x in reversed(r.get("log") or []) if x.get("k") == "end"), None)
            waited = f" (the drive waited {er.get('s')} s for it)" if isinstance(er, dict) else ""
            out.append((f"no row in an end place {ends}: the trace was collected before the end field's first "
                        f"store{waited}", "A-NOEND", "driver"))
        r["cut_row"] = None
        if r.get("cut") is not None and rec.get("trace"):
            try:
                rows = T.read_trace((self._run_dir or Path(".")) / rec["trace"])
                r["cut_row"] = next((x for x in rows if x.line == r["cut"]), None)
            except (OSError, T.TraceError):
                pass
        return out

    # -- the checks ---------------------------------------------------------------------------------------------
    def core_checks(self, runs: list, cov: dict, pred: dict) -> list:
        covered = cov["S"] + cov["F"]
        c = self.comparison(cov, pred)
        return [self.start_check(covered, pred), self.no_sc_check(covered, pred),
                self.span_check("CHAIN", covered, pred, "entrance_bytes", "chain", pred["entrance"]),
                self.residue_check(covered, pred), self.writes_check(covered, pred), self.null_check(c, pred),
                self.stable_check(c, pred), self.seam_check(cov, c, pred), self.landing_check(covered, pred),
                self.battle_check(covered, pred), self.masked_check(cov, pred), self.state_check(covered, pred),
                self.join_check(cov)]

    def start_check(self, covered: list, pred: dict) -> tuple:
        """O3-START (5.3): (a) the rows before the start are EXACTLY ``start_residue`` (kind ``r``, ``(byte, old,
        new)``, a multiset), nothing else; (b) the first ``w`` row in the start place is ``start_first``, read RAW
        (Bit[191] is masked in the digest); (c) the first ``start_music`` target row in the start place is
        ``start_music``: e0 t0 ip119 := 0 with ``old`` the warp's Byte[13] (1) -- never the error path's ip97."""
        want = Counter(tuple(x) for x in pred["start_residue"])
        sf, sm = pred["start_first"], pred["start_music"]
        bad = []
        for r in covered:
            lab = f"{r['side']}#{r['i']}"
            members = members_of(pred) if r["side"] == "F" else {}
            sp = place(pred["start"][r["side"]], members)
            others = [x for x in r["pre"] if x.k != "r"]
            if others:
                bad.append(f"{lab} (a): {len(others)} other row(s) before the start, first line {others[0].line} "
                           f"({others[0].k} in {others[0].fld})")
            got = Counter((x.byte, x.old, x.new) for x in r["pre"] if x.k == "r")
            if got != want:
                bad.append(f"{lab} (a): residue before the start {sorted(got.elements())}, want "
                           f"{sorted(want.elements())}")
            at = next((x for x in r["rows"] if x.line == r["start"]), None)
            if at is None or (at.m, at.src, at.sid, at.tag, at.ip, at.target, at.new) != (
                    sf["m"], sf["src"], sf["sid"], sf["tag"], sf["ip"], sf["target"], sf["value"]):
                bad.append(f"{lab} (b): the first write in the start place is "
                           f"{A._row_text(at) if at is not None else None}, not {A.label(sf)} (e{sf['sid']} "
                           f"t{sf['tag']} ip{sf['ip']} {sf['target']}={sf['value']})")
            mus = next((x for x in r["rows"] if x.k == "w" and place(x.fld, members) == sp
                        and x.target == sm["target"]), None)
            if mus is None or (mus.m, mus.src, mus.sid, mus.tag, mus.ip, mus.new, mus.old) != (
                    sm["m"], sm["src"], sm["sid"], sm["tag"], sm["ip"], sm["value"], sm["old"]):
                bad.append(f"{lab} (c): the first {sm['target']} row in the start place is "
                           + (f"{A._row_text(mus)} from old {mus.old}" if mus is not None else "none")
                           + f", not e{sm['sid']} t{sm['tag']} ip{sm['ip']} := {sm['value']} from old {sm['old']}")
        return (not bad, self.title("START"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: {len(pred['start_residue'])} residue rows, then "
                                      f"{sf['target']} at e{sf['sid']} t{sf['tag']} ip{sf['ip']}; the first "
                                      f"{sm['target']} row ip{sm['ip']} := {sm['value']} from old {sm['old']}")

    def no_sc_check(self, covered: list, pred: dict) -> tuple:
        """O3-NO-SC (4.2, 5.3): no kept row over ``sc_bytes`` after the start -- :func:`o2_alexandria.span_sequence`
        against an EMPTY sequence: a ``w`` row of any width or source fails by name, keyed or not (a harness poke
        too), and a ``c`` row over the span as a suppressed repeat. O2's LADDER on an empty ladder could not fail."""
        bad = []
        for r in covered:
            rk = row_keys(r["digest"])
            bad += [f"{r['side']}#{r['i']} {p}" for p in A.span_sequence(r["rows"], rk, pred["sc_bytes"], [],
                                                                         pred["scenario"])]
        return (not bad, self.title("NO-SC"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: no row over bytes {pred['sc_bytes']} after the start (SC "
                                      f"{pred['scenario']} throughout)")

    def writes_check(self, covered: list, pred: dict) -> tuple:
        """O3-WRITES, EXACT (4.4, 5.3): every covered run's keys outside the registered noise ARE the writes and the
        chain -- a missing key and an extra one (a dead branch firing, an error path, a C# write, a battle-mode key
        that is not the noise) each fail by name. Exactness rests on O3-CENSUS and O3-KEYS."""
        reg = list(pred["writes"]) + list(pred["chain"])
        want = {wkey(k) for k in reg}
        labels = {wkey(k): A.label(k) for k in reg}
        bad = []
        for r in covered:
            got = {k for k in r["digest"].keys if not is_noise(k, pred)}
            missing = sorted(want - got, key=T.WriteKey.sort_key)
            extra = sorted(got - want, key=T.WriteKey.sort_key)
            if missing:
                bad.append(f"{r['side']}#{r['i']} lacks {len(missing)}: " + ", ".join(labels[k] for k in missing[:3]))
            if extra:
                bad.append(f"{r['side']}#{r['i']} has {len(extra)} extra: {ST._show(extra, 3)}")
        return (not bad, self.title("WRITES"),
                "; ".join(bad[:6]) or f"{len(covered)} runs x exactly {len(want)} keys ({len(pred['writes'])} writes "
                                      f"+ {len(pred['chain'])} chain), the battle noise aside")

    def landing_check(self, covered: list, pred: dict) -> tuple:
        """O3-LANDING (5.3), over every covered run, each clause named in the detail:
          (a) every field-mode ``w``/``c`` row ran in its place's own field (member(place) on F, the place on S), and
              none stands in a place off ``route_places``;
          (b) every battle-mode row (``m`` != 1, ``w`` and ``c``) is ``landing.battle``'s store at member(62)/62 --
              ZERO such rows allowed, the count reported;
          (c) on ``w`` rows, anchored on registered keys: the run holds ``landing.before`` (62 ip1285); the next
              field-mode ``w`` row after it is ``landing.fresh`` (63 e0 t0 ip22: 63 loaded FRESH); no field-mode ``w``
              row of place 62 follows ``before``; every battle-mode ``w`` row lies between the two;
          (d) the last field-mode ``w`` row before the end cut is in ``last_place`` (63), and the run's ``end`` log
              row names ``end`` (64) itself;
          (e) the end cut is the line of a raw ``w`` row that is ``landing.end_row`` (64 e0 t0 ip22) -- an ``r`` row
              first in 64 would otherwise become the cut unseen.
        (c)-(e) read ``w`` rows only: a ``c`` row is written at the epoch's close, so its place says nothing about
        when its stores ran."""
        L = pred["landing"]
        lb, lbefore, lfresh, lend = L["battle"], L["before"], L["fresh"], L["end_row"]
        route = set(L["route_places"])
        bad, counts = [], []
        fm = T.FIELD_MODE

        def is_at(x, spec, members, field) -> bool:
            return (x.k == "w" and x.m == fm and place(x.fld, members) == spec["place"] and x.fld == field
                    and (x.sid, x.tag, x.ip, x.target, x.new) == (spec["sid"], spec["tag"], spec["ip"],
                                                                   spec["target"], spec["value"]))
        for r in covered:
            lab = f"{r['side']}#{r['i']}"
            members = members_of(pred) if r["side"] == "F" else {}
            inv = {d: f for f, d in sorted(members.items(), reverse=True)}

            def fld_of(p):
                return inv.get(p, p) if members else p
            rows = r["rows"]
            # (a)
            off = next((x for x in rows if x.k in ("w", "c") and x.m == fm
                        and (place(x.fld, members) not in route or x.fld != fld_of(place(x.fld, members)))), None)
            if off is not None:
                p = place(off.fld, members)
                bad.append(f"{lab} (a): line {off.line} {off.k} {A._row_text(off)} stands in place {p} at fld "
                           f"{off.fld}" + (f", not {fld_of(p)}" if p in route else f", off {sorted(route)}"))
            # (b)
            brows = [x for x in rows if x.k in ("w", "c") and x.m != fm]
            wrong = next((x for x in brows if (x.m, x.sid, x.tag, x.ip, x.target, x.fld) != (
                lb["m"], lb["sid"], lb["tag"], lb["ip"], lb["target"], fld_of(lb["place"]))), None)
            nw = sum(1 for x in brows if x.k == "w")
            counts.append(f"{lab} {nw}")
            if wrong is not None:
                bad.append(f"{lab} (b): line {wrong.line} m{wrong.m} {A._row_text(wrong)} is not the battle's store "
                           f"(m{lb['m']} e{lb['sid']} t{lb['tag']} ip{lb['ip']} {lb['target']} at fld "
                           f"{fld_of(lb['place'])})")
            # (c)
            ws = [x for x in rows if x.k == "w"]
            i = next((j for j, x in enumerate(ws) if is_at(x, lbefore, members, fld_of(lbefore["place"]))), None)
            if i is None:
                bad.append(f"{lab} (c): no landing.before row ({lbefore['place']} e{lbefore['sid']} t{lbefore['tag']} "
                           f"ip{lbefore['ip']} {lbefore['target']}={lbefore['value']} at fld "
                           f"{fld_of(lbefore['place'])})")
            else:
                later = [x for x in ws[i + 1:] if x.m == fm]
                nxt = later[0] if later else None
                if nxt is None or not is_at(nxt, lfresh, members, fld_of(lfresh["place"])):
                    bad.append(f"{lab} (c): the next field row after 62 ip{lbefore['ip']} is "
                               f"{A._row_text(nxt) if nxt is not None else 'none'}, not landing.fresh ("
                               f"{lfresh['place']} e{lfresh['sid']} t{lfresh['tag']} ip{lfresh['ip']}: 63 loaded fresh)")
                back = next((x for x in later if place(x.fld, members) == lbefore["place"]), None)
                if back is not None:
                    bad.append(f"{lab} (c): line {back.line} {A._row_text(back)}: place {lbefore['place']} written "
                               f"again after ip{lbefore['ip']} (resumed, never fresh)")
                j = next((n for n, x in enumerate(ws) if is_at(x, lfresh, members, fld_of(lfresh["place"]))
                          and n > i), None)
                lo, hi = ws[i].line, (ws[j].line if j is not None else None)
                stray = next((x for x in ws if x.m != fm and not (lo < x.line and (hi is None or x.line < hi))), None)
                if stray is not None:
                    bad.append(f"{lab} (c): battle row line {stray.line} lies outside 62 ip{lbefore['ip']} (line {lo})"
                               f" .. 63 ip{lfresh['ip']} (line {hi})")
            # (d)
            fws = [x for x in ws if x.m == fm]
            last = fws[-1] if fws else None
            if last is None or place(last.fld, members) != L["last_place"]:
                bad.append(f"{lab} (d): the last field row before the end cut is "
                           f"{A._row_text(last) if last is not None else 'none'} (place "
                           f"{None if last is None else place(last.fld, members)}), not in {L['last_place']}")
            endrow = [x for x in r.get("log") or () if x.get("k") == "end"]
            if not endrow or endrow[-1].get("field") != L["end"]:
                bad.append(f"{lab} (d): the run's end row names field "
                           f"{endrow[-1].get('field') if endrow else None}, not {L['end']} itself")
            # (e)
            cr = r.get("cut_row")
            if cr is None or not (cr.k == "w" and cr.m == fm and cr.fld == lend["place"]
                                  and (cr.sid, cr.tag, cr.ip, cr.target, cr.new) == (
                                      lend["sid"], lend["tag"], lend["ip"], lend["target"], lend["value"])):
                desc = ("no row" if cr is None else
                        f"{cr.k} " + (A._row_text(cr) if cr.k == "w" else f"{cr.fld} byte {cr.byte} {cr.old}->{cr.new}"))
                bad.append(f"{lab} (e): the end cut (line {r.get('cut')}) is {desc}, not landing.end_row "
                           f"({lend['place']} e{lend['sid']} t{lend['tag']} ip{lend['ip']} {lend['target']}"
                           f"={lend['value']})")
        return (not bad, self.title("LANDING"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) every field row in its place's own field; (b) battle "
                                      f"rows only m{lb['m']} e{lb['sid']} t{lb['tag']} ip{lb['ip']} {lb['target']} "
                                      f"(w rows {', '.join(counts)}); (c) 62 ip{lbefore['ip']} -> 63 e0 t0 "
                                      f"ip{lfresh['ip']}, fresh, 62 never resumed; (d) 63 last, the end in "
                                      f"{L['end']}; (e) the cut at {lend['place']} e0 t0 ip{lend['ip']}")

    def battle_check(self, covered: list, pred: dict) -> tuple:
        """O3-BATTLE (5.3, claim integrity #2): the trace cannot say which battle wrote its rows, so every covered
        run's own driver log is re-read: (a) exactly one ``battle`` row per registry row, in order -- its row index,
        scene, donor and beat the registry's, its result an int in ``won`` and the beat's value, no VOID class; (b)
        its ``epoch`` the run's ``battle_epoch0`` + 1 (no other battle began since the drive started); (c)
        ``landed`` ``lands`` on S and member(lands) on F, ``landed_place`` ``lands``; (d) the field-mode ``w`` rows
        nearest its ``frame0`` in the trace's own ``f`` -- the last at or before it, the first after it -- stand in
        the row's donor place and its ``lands``: the battle began at the 62 -> 63 boundary."""
        reg = list(pred.get("battles") or ())
        bad, res = [], Counter()
        for r in covered:
            lab = f"{r['side']}#{r['i']}"
            members = members_of(pred) if r["side"] == "F" else {}
            inv = {d: f for f, d in sorted(members.items(), reverse=True)}
            out = r.get("outcome") or {}
            beats = r["rec"].get("beats") or out.get("beats") or {}
            rows = [x for x in r.get("log") or () if x.get("k") == "battle"]
            if len(rows) != len(reg):
                bad.append(f"{lab} (a): {len(rows)} battle row(s) in the driver's log, want {len(reg)}")
                continue
            e0 = out.get("battle_epoch0")
            fws = [x for x in r["rows"] if x.k == "w" and x.m == T.FIELD_MODE]
            for n, (b, want) in enumerate(zip(rows, reg)):
                result = b.get("result")
                if (b.get("row") != n or b.get("scene") != want["scene"] or b.get("donor") != want["donor"]
                        or type(result) is not int or result not in want["won"] or b.get("beat") != want["beat"]
                        or beats.get(want["beat"]) != result or b.get("v") is not None):
                    bad.append(f"{lab} (a): battle row {b.get('row')} scene {b.get('scene')} donor {b.get('donor')} "
                               f"result {result!r} beat {b.get('beat')!r} (beats {beats.get(want['beat'])!r}) v "
                               f"{b.get('v')}, want row {n} scene {want['scene']} donor {want['donor']}, an int in "
                               f"{want['won']}, beat {want['beat']!r}")
                if e0 is None or b.get("epoch") != e0 + 1 + n:
                    bad.append(f"{lab} (b): epoch {b.get('epoch')}, want battle_epoch0 {e0} + {1 + n}")
                land = inv.get(want["lands"], want["lands"]) if members else want["lands"]
                if b.get("landed") != land or b.get("landed_place") != want["lands"]:
                    bad.append(f"{lab} (c): landed {b.get('landed')} (place {b.get('landed_place')}), want {land} "
                               f"(place {want['lands']})")
                f0 = b.get("frame0")
                before = [x for x in fws if f0 is not None and x.f <= f0]
                after = [x for x in fws if f0 is not None and x.f > f0]
                pb = place(before[-1].fld, members) if before else None
                pa = place(after[0].fld, members) if after else None
                if pb != want["donor"] or pa != want["lands"]:
                    bad.append(f"{lab} (d): frame0 {f0} stands between "
                               f"{A._row_text(before[-1]) if before else 'nothing'} (place {pb}) and "
                               f"{A._row_text(after[0]) if after else 'nothing'} (place {pa}), not "
                               f"{want['donor']} -> {want['lands']}")
                res[result] += 1
        return (not bad, self.title("BATTLE"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: one battle each -- "
                + ", ".join(f"scene {b['scene']} in {b['donor']}" for b in reg)
                + f", epoch battle_epoch0 + 1, results {dict(sorted(res.items()))}, landed in "
                + ", ".join(str(b["lands"]) for b in reg) + " (member on F), frame0 at the boundary")

    # -- the report ---------------------------------------------------------------------------------------------
    def report_extra(self, run_dir: Path, session: dict, pred: dict, runs: list, checks: list) -> list:
        """Report-only (5.4): the scope (start dependence, the settings recorded, a US session); the battle per run;
        the session's end (S5); 61's movie per run; then O2's sections, copied -- the VOID reasons per side, the
        masked counts, the forbidden hits with their backing, the P-TEXT KNOWN-KIT-DEFECT lines, the folded
        transcripts -- and the re-runs held (S2)."""
        L = ["", "Scope (a US session):", "  start dependence -- " + SCOPE_START]
        st = (session.get("install") or {}).get("settings")
        L.append("  settings -- " + (json.dumps(st, sort_keys=True) if st is not None
                                      else "not recorded (no install fingerprint in this session)"))
        L.append("  language -- " + SCOPE_LANG)
        L.append("")
        L.append("The battle, per run (scene, epoch / battle_epoch0, the result fight() read, turns, seconds, "
                 "tutorials; the leave; the flip; the landing; the trace's battle-mode rows):")
        for r in runs:
            L += self._battle_lines(r)
        L.append("")
        ended = session.get("ended")
        if ended is None:
            L.append("The session's end: not recorded")
        else:
            L.append("The session's end (end_run, warp first): "
                     + ("the title came back" if ended.get("ok") else f"the title did NOT come back: {ended.get('why')}")
                     + f"; rows {[x.get('k') for x in ended.get('log') or ()]}")
        L.append("")
        L.append("61's movie, per run (the arrival in the start place; the first page pressed):")
        for r in runs:
            members = members_of(pred) if r["side"] == "F" else {}
            sp = place(pred["start"][r["side"]], members)
            log = r.get("log") or []
            arr = next((x for x in log if x.get("k") == "visit" and x.get("donor") == sp), None)
            first = next((x for x in log if x.get("k") == "press" and x.get("why") == "page" and arr is not None
                          and x.get("visit") == arr.get("visit")), None)
            pf = (first.get("pre") or {}).get("frame") if first else None
            L.append(f"  {r['side']}#{r['i']}: " + ("no arrival in the start place" if arr is None else
                                                   f"arrival frame {arr.get('frame')}; first page press "
                                                   + (f"frame {pf} (+{pf - arr.get('frame', 0)} frames)"
                                                      if pf is not None else "none")))
        L += self._o2_sections(session, runs)
        if session.get("rerun_held"):
            L += ["", f"Re-runs held (rerun.stop_on): {session['rerun_held']}"]
        return L

    @staticmethod
    def _battle_lines(r: dict) -> list:
        lab = f"  {r['side']}#{r['i']}:"
        out = r.get("outcome") or {}
        bw = [x for x in r["rows"] if x.k == "w" and x.m != T.FIELD_MODE]
        bc = [x for x in r["rows"] if x.k == "c" and x.m != T.FIELD_MODE]
        sites = sorted({f"e{x.sid} t{x.tag} ip{x.ip} {x.target} fld {x.fld}" for x in bw + bc})
        rows_line = (f"battle-mode rows {len(bw)}" + (f" at {sites}" if sites else "")
                     + (f", counted {[x.n for x in bc]}" if bc else ""))
        brs = [x for x in r.get("log") or () if x.get("k") == "battle"]
        if not brs:
            v = r["rec"].get("v")
            return [f"{lab} no battle row" + (f" (the run VOID {v})" if v else "") + f"; {rows_line}"]
        L = []
        for b in brs:
            leave = b.get("leave") or {}
            flip = (f"flip frame {b.get('flip_frame')} result {b.get('flip_result')}" if b.get("flip_frame") is not None
                    else "flip not caught")
            gap = (b["land_frame"] - b["flip_frame"]) if b.get("land_frame") is not None and \
                b.get("flip_frame") is not None else None
            land = (f"landed {b.get('landed')} (place {b.get('landed_place')}) at frame {b.get('land_frame')}"
                    + (f", {gap} frames after the flip" if gap is not None else "")
                    if b.get("landed") is not None else "no landing")
            late = b.get("land_late")
            L.append(f"{lab} scene {b.get('scene')} epoch {b.get('epoch')} (battle_epoch0 "
                     f"{out.get('battle_epoch0')}), result {b.get('result')}, turns {b.get('turns')}, seconds "
                     f"{b.get('seconds')}, tutorials {b.get('tutorials')}; leave {leave.get('presses')} press(es) in "
                     f"{leave.get('uis')}, stopped {leave.get('stopped')}; {flip}; {land}; "
                     + (f"land_late {late}" if late else "on time")
                     + (f"; VOID {b.get('v')} ({b.get('by')}): {b.get('why')}" if b.get("v") else "")
                     + f"; {rows_line}")
        return L

    @staticmethod
    def _o2_sections(session: dict, runs: list) -> list:
        """O2's report sections (o2_alexandria.O2Segment.report_extra), copied: VOID reasons per side, the masked
        counts, the forbidden hits with their backing, the P-TEXT KNOWN-KIT-DEFECT lines, the folded transcripts."""
        L = ["", "VOID reasons per side (class, cell, by, why):"]
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
                   for d in A.defect_lines(detail)]
        L.append("")
        L.append("Text (P-TEXT, recorded at the preflight):")
        L += [f"  {d}" for d in defects] or ["  no KNOWN-KIT-DEFECT line recorded"]
        L.append("")
        L.append("Dialogue (timed pages removed, consecutive duplicates collapsed):")
        cov_s = next((r for r in runs if r["side"] == "S" and r["covered"]), None)
        s0 = A.fold_pages((cov_s.get("outcome") or {}).get("pages"), (cov_s.get("outcome") or {}).get("timed")) \
            if cov_s is not None else None
        for r in runs:
            if r["side"] != "F" or not r["covered"] or s0 is None:
                continue
            f0 = A.fold_pages((r.get("outcome") or {}).get("pages"), (r.get("outcome") or {}).get("timed"))
            first = next((i for i, (a, b) in enumerate(zip(f0, s0)) if a != b), None)
            L.append(f"  F#{r['i']} {'==' if f0 == s0 else '!='} S#{cov_s['i']} ({len(f0)} vs {len(s0)} pages)"
                     + ("" if f0 == s0 or first is None else f"; first difference at page {first + 1}: "
                                                            f"{f0[first][:60]!r} vs {s0[first][:60]!r}"))
        return L

    # -- the CLI ------------------------------------------------------------------------------------------------
    def add_arguments(self, ap) -> None:
        ap.add_argument("--draft", action="store_true", help="print the draft predictions as JSON")
        ap.add_argument("--rehearsal-report", metavar="RUN_DIR",
                        help="print an o3_rehearse.py launch's record, stage by stage and run by run")

    def handle(self, args) -> int | None:
        if args.rehearsal_report:
            print(rehearsal_report(args.rehearsal_report))
            return 0
        return super().handle(args)


O3 = O3Segment()


# ======================================================================== the rehearsal report
def rehearsal_report(run_dir) -> str:
    """``--rehearsal-report``: an o3_rehearse.py launch's ``o3_rehearsal.json`` (research/o3_design.md 7.2), stage by
    stage and run by run -- what each freeze item (7.3) is read from."""
    run_dir = Path(run_dir)
    doc = json.loads((run_dir / REHEARSAL_FILE).read_text(encoding="utf-8"))
    L = [f"O3 rehearsals -- {run_dir.name}  (draft sha {str(doc.get('draft_sha256'))[:8]}; stages "
         f"{doc.get('stages_run')})"]
    L += [f"  {'PASS' if ok else 'FAIL'}  {what} -- {detail}" for ok, what, detail in doc.get("capabilities") or ()]
    launch = doc.get("launch") or {}
    if launch:
        L.append(f"  launch: settings {json.dumps(launch.get('settings'), sort_keys=True)}")
        for ok, what, detail in launch.get("checks") or ():
            L.append(f"  {'PASS' if ok else 'FAIL'}  {what} -- {detail}")
    if doc.get("stopped"):
        L.append(f"  STOPPED: {doc['stopped']}")
    L.append("")
    for name, recs in (doc.get("stages") or {}).items():
        stage = (doc.get("stage_defs") or {}).get(name, {})
        if stage.get("pairs"):
            L.append(f"== {name}: the load smoke, pairs {stage.get('pairs')} at entrance {stage.get('entrance')} SC "
                     f"{stage.get('sc')}  ({len(recs)} warp(s)) -- settles: {stage.get('settles')}")
            for rec in recs:
                reach = rec.get("reached") or {}
                er = rec.get("end_run") or {}
                L.append(f"  warp {rec.get('n')}: {rec.get('field')} -> "
                         + (f"field {reach.get('field')} {reach.get('ui')} at frame {reach.get('frame')} after "
                            f"{reach.get('s')}s (control {reach.get('control')})" if reach else
                            f"NOT REACHED: {rec.get('error')}")
                         + f"; objects {rec.get('objects_status')} sids {rec.get('sids')}; exceptions "
                         f"{len(rec.get('exceptions') or [])}; log warnings/errors {len(rec.get('log_lines') or [])}; "
                         f"end_run {'ok' if er.get('ok') else 'FAILED ' + str(er.get('why'))} "
                         f"{[x.get('k') for x in er.get('how') or ()]}")
                for ln in (rec.get("log_lines") or [])[:4]:
                    L.append(f"    log: {ln[:160]}")
            for t in (doc.get("twins") or {}).get(name) or ():
                L.append(f"  twin {t.get('member')} vs {t.get('twin')}: "
                         + ("EQUAL" if t.get("equal") else "DIFFERENT") + f" ({t.get('member_sids')} vs "
                         f"{t.get('twin_sids')})")
            L.append("")
            continue
        L.append(f"== {name}: warp {stage.get('field')} {stage.get('entrance')} {stage.get('sc')} -> "
                 f"{stage.get('end')}  ({len(recs)} run(s)) -- settles: {stage.get('settles')}")
        for rec in recs:
            out = rec.get("outcome") or {}
            L.append(f"  run {rec.get('n')}: {out.get('end')} -- {out.get('why')}"
                     + (f" [{out.get('v')} {out.get('cell')} {out.get('by')}]" if out.get("v") else "")
                     + f"; {rec.get('t1', 0) - rec.get('t0', 0):.0f}s; trace {rec.get('trace_file')}")
            L.append(f"    grants: {len(rec.get('grants') or [])} (there must be none)")
            for c in rec.get("choices") or ():
                L.append(f"    choice at frame {c.get('frame')}: {c.get('options')} active {c.get('active')} "
                         f"selected {c.get('selected')} -> rule {c.get('rule')} index {c.get('index')}")
            L.append(f"    published choices: {len(rec.get('published_choices') or [])} distinct snapshot(s)")
            pages = rec.get("pages") or []
            L.append(f"    pages: {len(pages)} ({sum(1 for p in pages if p.get('timed'))} timed)")
            ev = rec.get("evidence") or {}
            L.append(f"    evidence: {len(ev.get('press') or [])} press row(s), {len(ev.get('forbidden') or [])} "
                     f"forbidden row(s)")
            bt = rec.get("battles") or {}
            for b in bt.get("rows") or ():
                leave = b.get("leave") or {}
                L.append(f"    battle: scene {b.get('scene')} epoch {b.get('epoch')} (battle_epoch0 "
                         f"{bt.get('battle_epoch0')}) result {b.get('result')} turns {b.get('turns')} seconds "
                         f"{b.get('seconds')} tutorials {b.get('tutorials')} timed_out {b.get('timed_out')}; leave "
                         f"{leave.get('presses')} press(es) {leave.get('uis')} stopped {leave.get('stopped')}; flip "
                         f"{b.get('flip_frame')} result {b.get('flip_result')}; landed {b.get('landed')} (place "
                         f"{b.get('landed_place')}) frame {b.get('land_frame')} land_late {b.get('land_late')}"
                         + (f"; VOID {b.get('v')} {b.get('by')}: {b.get('why')}" if b.get("v") else ""))
            if rec.get("skip"):
                L.append(f"    skip press: {rec['skip']}")
            npg = rec.get("no_progress") or {}
            L.append(f"    longest no-progress stretch: {npg.get('longest_s')}s at {npg.get('where')}")
            if rec.get("movie") is not None:
                L.append(f"    movie: {rec['movie']}")
            end = rec.get("end") or {}
            er = end.get("end_run") or {}
            L.append(f"    end: state {end.get('end_state')}; end_run "
                     + ("ok" if er.get("ok") else f"FAILED {er.get('why')}")
                     + f", title {er.get('title')}, rows {[x.get('k') for x in er.get('how') or ()]}")
            for x in er.get("how") or ():
                if x.get("k") in ("recover-in-battle", "recover-battle-ending"):
                    L.append(f"      {x.get('k')}: ui {x.get('ui')} result {x.get('result')} scene {x.get('scene')}")
            tr = rec.get("trace") or {}
            if tr:
                L.append(f"    trace: start line {tr.get('start')}, end line {tr.get('end')}, {tr.get('rows')} rows; "
                         f"SC rows {len(tr.get('sc') or [])} (must be none); FieldEntrance "
                         f"{[x['new'] for x in tr.get('entrance') or ()]}")
                L.append(f"      residue before the start {tr.get('residue_before')}; after "
                         f"{tr.get('residue_after')}; other rows before it {tr.get('pre_other')}")
                for name2, keys in (tr.get("registered") or {}).items():
                    present = [k["what"] for k in keys if k["present"]]
                    L.append(f"      {name2}: {len(present)}/{len(keys)} present"
                             + (f"; present: {present[:4]}" if name2 in ("error_path", "forbidden_sites", "dead")
                                and present else ""))
                bt2 = tr.get("battle") or {}
                L.append(f"      battle-mode w rows {bt2.get('w')} at {bt2.get('sites')} flds {bt2.get('flds')}; "
                         f"counted {bt2.get('c')}")
                L.append(f"      the first field row after 62 ip1285: {tr.get('after_before')}; the end cut's row: "
                         f"{tr.get('end_row')}")
                L.append(f"      unregistered keys ({len(tr.get('unregistered') or [])}): "
                         f"{(tr.get('unregistered') or [])[:12]}; noise keys {tr.get('noise_keys')}")
                L.append(f"      masked {tr.get('masked')}; join failures {len(tr.get('failures') or [])}")
                for h in tr.get("forbidden") or ():
                    L.append(f"      forbidden: {h['row']} {h['why']} -- "
                             + (f"backed by {h['by']}" if h["backed"] else "unbacked"))
        L.append("")
    return "\n".join(L)


# ======================================================================== the session and the CLI
def run(g) -> None:
    """The session (tools/play.py's entry): O3Segment.run."""
    return O3.run(g)


def main(argv=None) -> int:
    return O3.main(argv)


if __name__ == "__main__":
    sys.exit(main())
