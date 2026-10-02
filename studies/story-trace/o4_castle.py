"""THE STORY-WRITE TRACE, O4 -- THE SWORD FIGHT, A US SESSION: from a raw warp into 64 (A. Castle/Public Seats,
entrance 100, the scenario at 1155) through the sword fight -- played by the driver to the owner's displayed 100/100
-- the encore declined, 150's guardhouse and the party rebuilt, SC := 1190, to the arrival in 153 -- stock against the
alxc disc-1 chain, both sides played by one driver (studies/story-trace/PLAN.md, "O4"; the design:
research/o4_design.md).

    py tools/play.py studies/story-trace/o4_castle.py --label story-o4 --timeout 240
    py studies/story-trace/o4_castle.py --offline-check     # the build and its fork-gate pins, the keys and the fight
                                                            # pins, blocks 2 and 3's text (strict), the store census
    py studies/story-trace/o4_castle.py --preflight         # the live install (read-only): RED until the deploy
    py studies/story-trace/o4_castle.py --draft             # the draft predictions, as JSON
    py studies/story-trace/o4_castle.py --freeze            # write o4_predictions_v1.json (once: the lead, after the
                                                            # stock rehearsals)
    py studies/story-trace/o4_castle.py --analyse <run dir> # the analysis alone, on saved traces
    py studies/story-trace/o4_castle.py --rehearsal-report <run dir>   # an o4_rehearse.py launch, stage by stage,
                                                            # R-GATE's verdict and its cause

THE SIDES (o4_forks.json):
  S  stock. Start: 64, entrance 100, SC 1155. End: the arrival in REAL 153.
  F  `import-chain 64 --verbatim --ids 64,68-69,150-151,153-167 --fresh-ids --id-base 31240 --name-prefix O4`:
     twenty members 31240-31259 -- member(64) 31240, member(150) 31243, member(153) 31245, read from the build's
     campaign.toml -- every language its own donor's (today's kit), NOT deployed until the lead's owner-gated deploy.
     Both route Field()s are retargeted, so the F side ENDS IN member(153): each side has its own end list (S6:
     ``side_ends``), and a landing in a REAL donor field on F is V19, a finding.

THE ENTRY: New Game, the trace armed, then in field 70 a raw `warp <64 | 31240> 100 1155` (O2's form): three residue
rows in field 70 (SC's two bytes, FieldEntrance's low byte), which the front cut sets aside and O4-START requires.

THE ROUTE: segment_drive.drive with no beat table (64@100 and 150@325 never grant control: control anywhere is V4), no
battle, no movie, the Chanbara policy (``chanbara``: rule 6b's executor plays the 49 prompts, one mapped press each,
fast), the encore rule (127 answered No by ``g.choose(1)``), the stop pages, and the input witness (outside input
anywhere in the run is V13). V17 is the driver's (its input not proven the frozen play), V18 the game's (a sample
SHOWED it deviate from a proven play: a finding), V19 a real donor field on F (a finding).

THE ANALYSIS: each run cut at its start row (64's first write) and at its first row in an end PLACE (153: member(153)
on F), digested and compared as O1-O3's; the O4 checks (research/o4_design.md 5.3) read the start, the one SC rung,
the chain, the residue, the writes EXACTLY, the landing per side, the sword fight from the trace and the driver's own
rows, the masked regions, the state handed to 153, and every run's VOID classes -- a finding class (V18, V19) or a
game-observed V17 cause on one side is NOT PROVEN, never a VOID. The predictions are frozen by the lead after the
stock rehearsals (o4_rehearse.py); until then --offline-check and --preflight read the draft. R-GATE, the +30% bonus's
witness on member(64), runs after the deploy, outside the frozen claim: P-GATE carries its verdict into the session.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import statistics
import sys
import time
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
import segment_drive as SD                                              # noqa: E402
import segment_trace as ST                                              # noqa: E402
from segment_trace import (SIDES, cut_at_end, cut_at_start, is_noise, key_of, members_of, place,  # noqa: E402
                           row_keys, wkey)

PREDICTIONS = HERE / "o4_predictions_v1.json"
MANIFEST = HERE / "o4_forks.json"
SESSION_FILE = "o4_session.json"
REPORT_FILE = "o4_report.txt"
REHEARSAL_FILE = "o4_rehearsal.json"
CHAIN_DIR = Path(r"C:\gd\_ns_playtest\o4\fork")
BUILD_DIR = Path(r"C:\gd\_ns_playtest\o4\build")
GAME = A.GAME
SESSION_LANG = "us"
#: The text blocks the chain's members carry (EVENT_ID_TO_MES): block 2 for 64/68/69, block 3 for 150-167. Block 2
#: is the one O2's single-block readers read (``text_block``); member(64) MUST stay on it (TextOpCodeModifier keys
#: 111's layout on FieldZoneId 2).
TEXT_BLOCK, TEXT_BLOCKS = 2, (2, 3)
#: The twenty donors of the alxc disc-1 chain (research/o4_design.md 0.1 #3): exactly these, never more or fewer.
DONORS = (64, 68, 69, 150, 151) + tuple(range(153, 168))
#: The route's places, in order, and the end place.
ROUTE = (64, 150)
END_FIELD = 153
#: The donors P-DONOR and P-DONOR-LOG read: the route's and the end's.
ROUTE_DONORS = ROUTE + (END_FIELD,)
#: 4.13: the settings the stock truth runs under, raw ini values as the engine takes them -- O3's, plus the control
#: and graphics keys the fight rests on (AlwaysCaptureGamepad: a pad is read unfocused; SwapConfirmCancel; FieldTPS).
SETTINGS = {
    "Battle": {"Enabled": "1", "SFXRework": "1", "Speed": "5", "CustomBattleFlagsMeaning": "0"},
    "Cheats": {"Enabled": "1", "AutoBattle": "1", "SpeedMode": "1", "SpeedFactor": "3", "SpeedTimer": "0",
               "BattleAssistance": "1", "Attack9999": "1", "NoRandomEncounter": "1", "MasterSkill": "0", "LvMax": "0",
               "GilMax": "0"},
    "Hacks": {"Enabled": "1", "AllCharactersAvailable": "1", "SwordplayAssistance": "1", "DisableNameChoice": "0"},
    "Control": {"Enabled": "1", "SoftReset": "1", "TurboDialog": "1", "BattleAutoConfirm": "1",
                "DialogProgressButtons": "\"Confirm\"", "AlwaysCaptureGamepad": "1", "SwapConfirmCancel": "0"},
    "Graphics": {"Enabled": "1", "FieldTPS": "30"},
}
#: 4.13: field 70's New-Game override, per stacked folder that ships it (the us copy's sha; all seven languages are
#: one file): the warp window and Byte[13] = 1 are proven under it (critique minor #9).
OVERRIDE70 = {"FF9CustomMap-world": "2ce8887ea969db6b6518bd33151b1a8805af10a6c9c96a0f59b49bad9ffc9215"}
#: 4.13 (rev. 2, the claim critique #9): the Assembly-CSharp.dll every fork gate, EMinigame line and harness behaviour
#: in the design was read from (= C:\gd\FFIX\Memoria\Output).
ENGINE = {"x64": "ba9762423da8f3d749a41a9988ef951d2a4fa62c296acc5aa44054439b45dcfc",
          "x86": "ba9762423da8f3d749a41a9988ef951d2a4fa62c296acc5aa44054439b45dcfc",
          "why": "0.3 #8: the Assembly-CSharp.dll every fork gate, EMinigame line and harness behaviour in this design "
                 "was read from (= C:\\gd\\FFIX\\Memoria\\Output, Sep 26 17:10); an engine rebuild auto-deploys over "
                 "the shared install"}
#: 4.13's DERIVED facts: recorded and reported, never checked live (the agent publishes neither).
DERIVED = {
    "cfg_control": {"value": 0, "why": "0.2 #6: New Game -> SettingsState.Initial -> cfg = new FF9CFG() (control 0) -> "
                                       "SetPrimaryKeys: identity logicalToButton (HonoInputManager.cs:967-975); only a "
                                       "save load restores cfg"},
    "tick_hz": {"value": 30, "why": "FieldTPS 30 (Memoria.ini:53, [Graphics] Enabled 1); FastForwardFactor 1: Initial "
                                    "rebuilds IsBoosterButtonActive with [1] (IsFastForward, SettingsState.cs:55) false, "
                                    "and the factor is 1 outside a Movie scene (:66-74); mid-run only F1 or a pad sets "
                                    "it (0.3 #7), which the input witness catches"}}
#: 4.10: the Chanbara policy's draft (F3-F5 and F12 re-size it from the rehearsals).
POLICY = {"policy": "fast", "donor": 64, "sc": 1155, "buttons": dict(SD.DBTN_CONTROL), "press_frames": 2,
          "prompts": 49, "j_cap": 14, "raw_floor": 100, "gone_ticks": 10,
          "zone_start": {"match": "To follow Blank", "dbtns": 8},
          "zone_end": ["We shall finish this later!", "Come back here!"],
          "first_prompt_s": 2.0, "zone_stall_s": 3.5, "page_once_ticks": 10,
          "quiet": ["Queen Brahne was"], "quiet_cap_s": 4.2,
          "score_page": "Of 100 nobles watching,\n100 were impressed.",
          "gil_page": "They shower you with 10000 Gil!",
          "encore_match": "encore", "poll_s": 0.005, "state_every": None, "input_every_s": 0.05, "ring_every_s": 2.0,
          "why": "64 stage 3, the sword fight: e20 t1 ip440-1554 arms 49 prompts over 50 passes and e3 t1 ip23-509 polls "
                 "the eight KEYON bits once a tick; one mapped press per prompt, fast -- raw >= 100 shows 100 with or "
                 "without the +30%"}
#: R-GATE's paced overlay (2.4.10): no raw_floor, j_cap 40, the pace (F14 sizes lead_ticks per regime).
PACED = {"policy": "paced", "j_cap": 40, "pace": {"target_ticks": 22, "lead_ticks": 3, "raw_band": [79, 99]}}
#: 123's text, the page the 50-combo writes Bit[3815] after (0.2 #3); a page holding a COMBO-page marker is 120/121's.
PAGE_123 = "Queen Brahne was\nquite impressed."
COMBO_MARKS = ("Of the 100 nobles watching", "not impressed")
#: 64 e4 t1's score statement, the hook's statement (EMinigame.ChanbaraBonusPoints fires at its first token, sid 4 ip
#: 223, EMinigame.cs:14) and the Byte[475] store (O4-BUILD's pins, per language; O4-KEYS's fight pins, US).
SCORE_TEXT = "SET({Map.Int16[48] Map.Int16[30] Map.Int16[32] B_PLUS const(29) B_DIV B_LET B_EXPR_END})"
HOOK_TEXT = "SET({Map.Int16[48] const(100) B_GT B_EXPR_END})"
STORE_TEXT = "SET({Global.Byte[475] Map.Int16[48] B_LET B_EXPR_END})"
PAIR_TEXT = "SET({const4(131072) B_KEYON B_NOT const4(524288) B_KEYON B_NOT B_ANDAND B_EXPR_END})"
#: The scope lines (5.4) that are constants; the language, settings, engine and fight lines are read from the record.
SCOPE_START = ("under the raw warp no key on the route is start-dependent: 64 zeroes Byte[475] (ip425) and Bit[3815] "
               "(ip416) before reading either; 64 reads Byte[13]/[14]/Bit[184] before writing them and takes ip119/ip200 "
               "from the warp's (1, 0, 0) as from a true O3 end's (0, 0, 0); 150 writes UInt16[21] and Byte[303] before "
               "reading them; Byte[4]/[17]/[18] have no reader on the route. Not covered: party data, items, gil "
               "(+10000 at a score of 100), AP, field 70's override state, and the seven untouched targets' values after "
               "a true O1-O3 run")
SCOPE_ACHIEVEMENT = ("every run that scored >= 75 reported Steam's Encore achievement (EMinigame.cs:20, 34-38): outside "
                     "gEventGlobal, not suppressed")
#: The XInput thresholds P-PAD and the input witness read (6.2): any button bit; a trigger at or past
#: XINPUT_GAMEPAD_TRIGGER_THRESHOLD; a thumb axis past 0.10 of full scale (the engine's [AnalogControl] StickThreshold
#: 10, stricter than XInput's deadzone).
PAD_TRIGGER, PAD_THUMB = 30, 3277
#: P-PAD's sample: this many reads, this far apart.
PAD_READS, PAD_EVERY_S = 25, 0.02
#: The input witness re-reads a slot it found disconnected at most this often (the empty slot is the slow call).
PAD_EMPTY_S = 1.0
#: R-GATE's verdicts (7.4 G2) and the causes a BROKEN carries (rev. 2, the claim critique #10).
GATE_VERDICTS = ("WITNESSED", "BROKEN", "INVALID", "UNINFORMATIVE")
GATE_CAUSES = ("bonus", "combo")
#: A side's informative R-GATE run must come within this many attempts (7.4 G2).
GATE_ATTEMPTS = 3
#: The run VOID classes an R-GATE reading can stand beside (7.4 G2; the review, research/o4_design.md 11.5): none (the
#: run reached its end fields) and V18 -- the reading's own evidence (the fight judge's, or the score or gil page read
#: in two samples with another number). Any other class stopped a run whose reading is not proven -- V13 (the
#: instrument's: outside input, the budget, a refused press, any HarnessError), V17 (the driver's), V14, V4, V11,
#: V19 ...: that run is uninformative, re-run within R-GATE's attempts; it never reaches the verdict's INVALID.
GATE_RUN_VOIDS = (None, "V18")
_MODULE_DOC = __doc__


def _sha(b: bytes | None) -> str | None:
    return None if b is None else hashlib.sha256(b).hexdigest()


def _sha_file(path) -> str | None:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


# ======================================================================== the chain (campaign.toml)
def chain_from_campaign(campaign=None) -> tuple:
    """``({fork id: donor}, {fork id: member name})`` of the built alxc chain (its ``campaign.toml``,
    research/o4_design.md 1.3): its donors must be EXACTLY :data:`DONORS`, each once -- a missing or an extra donor is
    refused (the draft would register another chain). member(64), member(150) and member(153) are derived from it
    (:func:`route_members`), never assumed."""
    path = Path(campaign) if campaign is not None else CHAIN_DIR / "campaign.toml"
    members, names = ST.chain_from_campaign(path)
    donors = sorted(members.values())
    if donors != sorted(DONORS):
        missing = sorted(set(DONORS) - set(donors))
        extra = sorted(d for d, n in Counter(donors).items() if d not in DONORS or n > 1)
        raise AssertionError(f"{path}: the chain's donors are not the alxc disc-1 twenty: missing {missing}, extra "
                             f"{extra} -- the draft would register another chain")
    return members, names


def route_members(members: dict) -> dict:
    """``{64: fork id, 150: fork id, 153: fork id}``: the members the route runs and ends in (derived)."""
    out = {}
    for donor in ROUTE_DONORS:
        hits = sorted(f for f, d in members.items() if d == donor)
        if len(hits) != 1:
            raise AssertionError(f"donor {donor} is forked by {hits}, not exactly one member")
        out[donor] = hits[0]
    return out


def route_members_line(members: dict) -> str:
    """The line the offline check and --draft print: ``member(64) 31240, member(150) 31243, member(153) 31245``."""
    rm = route_members(members)
    return ", ".join(f"member({d}) {f}" for d, f in rm.items())


# ======================================================================== the predictions (draft v1)
def _key(donor, sid, tag, ip, off, target, value, op, what, prior=None) -> dict:
    return A._key(donor, sid, tag, ip, off, target, value, op, what, prior)


def _site(place_, sid, tag, ip, target, value, **kw) -> dict:
    return {"place": place_, "sid": sid, "tag": tag, "ip": ip, "target": target, "value": value, **kw}


def fight_pins() -> list:
    """4.14's fight pins: ``[donor, sid, tag, ip, eb-src text]`` -- the bytes the policy and the FakeGame model rest
    on, each compared EXACTLY with the stock US script's instruction text (O4-KEYS (b))."""
    pins = [[64, 20, 1, 462, "SET({Map.Byte[46] B_SYSVAR[0] const(7) B_AND B_LET B_EXPR_END})"],
            [64, 20, 1, 681, "SET({Map.Byte[46] Map.Byte[44] B_EQ B_EXPR_END})"],
            [64, 20, 1, 710, "SET({Map.Int16[34] const(49) B_LT B_EXPR_END})"],
            [64, 20, 1, 721, "SET({Map.Byte[47] const(1) B_LET B_EXPR_END})"],
            [64, 20, 1, 736, "SET({Map.Byte[52] const(50) B_LET B_EXPR_END})"]]
    pins += [[64, 20, 1, 789 + 9 * n, f"WindowAsync(1, 160, {112 + n})"] for n in range(8)]
    pins += [[64, 20, 1, 1379, "SET({Map.Byte[52] const(0) B_GT Map.Byte[47] const(1) B_EQ B_ANDAND B_EXPR_END})"],
             [64, 20, 1, 1438, "SET({Map.Int16[30] Map.Byte[52] B_PLUS_LET B_EXPR_END})"],
             [64, 20, 1, 1456, "SET({Map.Int16[32] Map.Int16[40] B_PLUS_LET B_EXPR_END})"],
             [64, 20, 1, 1546, "SET({Map.Int16[34] const(50) B_LT B_EXPR_END})"],
             [64, 3, 1, 23, "SET({Map.Byte[47] const(1) B_EQ B_EXPR_END})"]]
    keys = ((34, "const(128)"), (81, "const(32)"), (128, "const(4096)"), (175, "const(64)"), (222, "const(16384)"),
            (269, "const(16)"), (316, "const(8192)"), (363, "const4(32768)"))
    pins += [[64, 3, 1, ip, f"SET({{{c} B_KEYON B_EXPR_END}})"] for ip, c in keys]
    pins += [[64, 3, 1, ip, f"SET({{Map.Byte[46] const({n}) B_EQ B_EXPR_END}})"]
             for n, ip in enumerate((43, 90, 137, 184, 231, 278, 325, 374))]
    pins += [[64, 3, 1, 412, "SET({const(8) B_KEY B_EXPR_END})"],
             [64, 3, 1, 487, "SET({Map.Byte[52] const(0) B_GT B_EXPR_END})"],
             [64, 3, 1, 498, "SET({Map.Byte[52] B_POST_MINUS B_EXPR_END})"],
             [64, 4, 1, 208, SCORE_TEXT], [64, 4, 1, 222, HOOK_TEXT],
             [64, 4, 1, 233, "SET({Map.Int16[48] const(100) B_LET B_EXPR_END})"],
             [64, 4, 1, 346, "SET({Map.Int16[42] const(50) B_LT B_EXPR_END})"]]
    pins += [[64, 4, 1, ip, f"WindowSync(5, 0, {mes})"] for ip, mes in ((357, 120), (366, 121), (375, 122), (384, 123))]
    pins += [[64, 4, 1, 462, "WindowSync(5, 0, 127)"], [64, 4, 1, 476, "SET({B_SYSVAR[9] const(0) B_EQ B_EXPR_END})"],
             [64, 4, 1, 531, "WindowSync(5, 0, 128)"], [64, 13, 1, 900, "WindowSync(6, 0, 111)"],
             [64, 13, 1, 868, PAIR_TEXT], [64, 13, 1, 1404, PAIR_TEXT], [150, 2, 1, 538, PAIR_TEXT],
             [64, 2, 1, 536, "Field(150)"], [150, 3, 1, 2169, "Field(153)"],
             [150, 3, 1, 1884, "SET({Global.UInt16[0] const(1190) B_GT B_EXPR_END})"],
             [150, 3, 1, 1632, "SET({const(5) B_PARTYCHK B_EXPR_END})"]]
    return pins


def draft_predictions(campaign=None) -> dict:
    """The registered claims (research/o4_design.md section 4). Every number was read off the stock bytes (the offline
    check re-derives each: O4-BUILD's pins, O4-KEYS with the fight pins, O4-TEXT, O4-CENSUS), the live install or the
    chain's campaign.toml (``campaign``; default the build's); nothing is read from a run. The rehearsals
    (o4_rehearse.py) settle the driver's numbers before the lead freezes them (7.3)."""
    members, names = chain_from_campaign(campaign)
    rm = route_members(members)
    key = _key
    writes = P._ambient(64, (57, 119, 138, 200)) + [
        key(64, 0, 0, 416, 410, "Global.Bit[3815]", 0, ":=",
            "64 Bit[3815] := 0 (the 50-combo flag zeroed on every entrance-100 arrival)"),
        key(64, 0, 0, 425, 419, "Global.Byte[475]", 0, ":=", "64 Byte[475] := 0 (the best score zeroed)"),
        key(64, 0, 0, 475, 469, "Global.Byte[8]", 125, ":=", "64 Byte[8] := 125 (after the sound-sync loop)"),
        dict(key(64, 4, 1, 338, 316, "Global.Byte[475]", 100, ":=var",
                 "64 Byte[475] := Map.Int16[48] (THE SCORE: 0 -> 100, ip327 Byte[475] < Int16[48])"),
             rvalue="Map.Int16[48]"),
        key(64, 4, 1, 390, 368, "Global.Bit[3815]", 1, ":=", "64 Bit[3815] := 1 (THE 50-COMBO, after page 123)"),
        key(64, 2, 1, 331, 320, "Global.Byte[8]", 0, ":=", "64 Byte[8] := 0 (stage 9)")] \
        + P._ambient(150, (61, 123, 142, 204)) + [
        key(150, 0, 0, 331, 321, "Global.Byte[8]", 25, ":=", "150 Byte[8] := 25 (the 325 branch)"),
        key(150, 3, 1, 1136, 878, "Global.UInt16[21]", 1, ":=", "150 UInt16[21] := 1 (the party reserve: Zidane)"),
        key(150, 3, 1, 1221, 963, "Global.Byte[303]", 0, ":=", "150 Byte[303] := 0 (the party count)"),
        key(150, 3, 1, 1255, 997, "Global.Byte[303]", 1, "++", "150 Byte[303]++ (1)", prior="150/3/1/1221"),
        key(150, 3, 1, 1652, 1394, "Global.Byte[4]", 0, ":=", "150 Byte[4] := 0 (PARTYCHK(5) false: ip1641 not taken)"),
        key(150, 3, 1, 1667, 1409, "Global.Byte[4]", 0, ":=", "150 Byte[4] := 0 (ip1667)"),
        key(150, 3, 1, 1675, 1417, "Global.Byte[17]", 0, ":=", "150 Byte[17] := 0"),
        key(150, 3, 1, 1683, 1425, "Global.Byte[18]", 1, ":=", "150 Byte[18] := 1"),
        key(150, 3, 1, 1974, 1716, "Global.Byte[8]", 75, ":=", "150 Byte[8] := 75 (after SC := 1190)")]
    ladder = [key(150, 3, 1, 1966, 1708, "Global.UInt16[0]", 1190, ":=",
                  "SC 1155 -> 1190: 150 stage 10, after the rebuild and Wait(90); the guard ip1884 SC > 1190 false")]
    chain = [key(64, 2, 1, 528, 517, "Global.Int16[2]", 325, ":=", "FieldEntrance 325: 64 stage 9, then Field(150)"),
             key(150, 3, 1, 2161, 1903, "Global.Int16[2]", 325, ":=",
                 "FieldEntrance 325: 150 stage 10, then Field(153) (a same-value store)")]
    error_path = [key(donor, 0, 0, ip, off, target, value, ":=", f"{donor} e0 t0 ip{ip}: the error path ({target} := "
                                                                  f"{value})")
                  for donor, ip, off, target, value in (
        (64, 97, 91, "Global.Byte[13]", 9), (64, 178, 172, "Global.Byte[14]", 9),
        (64, 845, 839, "Global.Byte[13]", 0), (64, 879, 873, "Global.Byte[14]", 0),
        (150, 101, 91, "Global.Byte[13]", 9), (150, 182, 172, "Global.Byte[14]", 9),
        (150, 1009, 999, "Global.Byte[13]", 0), (150, 1043, 1033, "Global.Byte[14]", 0))]
    forbidden_sites = [
        key(150, 3, 1, 1641, 1383, "Global.Byte[4]", 1, ":=", "150 Byte[4] := 1 (PARTYCHK(5) true: Quina in the party)"),
        key(150, 3, 1, 1952, 1694, "Global.UInt16[0]", 1190, ":=",
            "150 SC := 1190 (the debug overwrite behind ip1884, window 55 and a Start press)")]
    dead = [
        key(64, 0, 0, 41, 35, "Global.Int16[2]", 10000, ":=", "64 Int16[2] := 10000 (dead: Bit[184] == 1, ip30)"),
        key(64, 0, 0, 130, 124, "Global.Byte[13]", 1, ":=", "64 Byte[13] := 1 (dead: Int16[9] >= 0, ip108)"),
        key(64, 0, 0, 211, 205, "Global.Byte[14]", 1, ":=", "64 Byte[14] := 1 (dead: Int16[11] >= 0, ip189)"),
        key(64, 0, 0, 295, 289, "Global.Byte[8]", 125, ":=", "64 Byte[8] := 125 (dead: entrance 327's branch)"),
        key(64, 0, 0, 380, 374, "Global.Byte[8]", 125, ":=", "64 Byte[8] := 125 (dead: entrances 315/322's branch)"),
        key(64, 2, 1, 893, 882, "Global.Int16[2]", 0, ":=", "64 Int16[2] := 0 (dead: the 327 visit's exit to 67)"),
        key(64, 11, 2, 193, 163, "Global.Int16[2]", 330, ":=", "64 e11 Int16[2] := 330 (dead: region 11 never runs)"),
        key(64, 12, 2, 193, 163, "Global.Int16[2]", 329, ":=", "64 e12 Int16[2] := 329 (dead: region 12 never runs)"),
        key(150, 0, 0, 45, 35, "Global.Int16[2]", 10000, ":=", "150 Int16[2] := 10000 (dead: Bit[184] == 1, ip34)"),
        key(150, 0, 0, 134, 124, "Global.Byte[13]", 1, ":=", "150 Byte[13] := 1 (dead: Int16[9] >= 0, ip112)"),
        key(150, 0, 0, 215, 205, "Global.Byte[14]", 1, ":=", "150 Byte[14] := 1 (dead: Int16[11] >= 0, ip193)"),
        key(150, 0, 0, 497, 487, "Global.Byte[8]", 125, ":=", "150 Byte[8] := 125 (dead: another entrance's branch)"),
        key(150, 0, 0, 609, 599, "Global.Byte[8]", 125, ":=", "150 Byte[8] := 125 (dead: the default branch)"),
        key(150, 3, 1, 1277, 1019, "Global.Byte[303]", 2, "++", "150 Byte[303]++ (2; dead: behind const(0))",
            prior="150/3/1/1255"),
        key(150, 3, 1, 1299, 1041, "Global.Byte[303]", 3, "++", "150 Byte[303]++ (3; dead: behind const(0))",
            prior="150/3/1/1277"),
        key(150, 3, 1, 1321, 1063, "Global.Byte[303]", 4, "++", "150 Byte[303]++ (4; dead: behind const(0))",
            prior="150/3/1/1299"),
        key(150, 18, 2, 90, 60, "Global.Byte[8]", 0, ":=", "150 e18 Byte[8] := 0 (dead: region 18 RETs without control)"),
        key(150, 18, 2, 242, 212, "Global.Byte[8]", 75, ":=", "150 e18 Byte[8] := 75 (dead: no control)"),
        key(150, 18, 2, 378, 348, "Global.Int16[2]", 5, ":=", "150 e18 Int16[2] := 5 (dead: no control)")]
    start_music = dict(key(64, 0, 0, 119, 113, "Global.Byte[13]", 0, ":=",
                           "64's ambient branch from the warp's Byte[13] 1 (field 70's prologue :=1 at ip130; the warp "
                           "leaves 70 before ip475's :=2)"), old=1)
    return {
        "version": 1,
        "what": f"O4: 64@1155 (warp, entrance 100) -> the sword fight -> 150 -> Field(153), SC 1190; stock vs the alxc "
                f"disc-1 chain (members {min(members)}-{max(members)}; PLAN.md, O4) -- a US session",
        "rehearsals": ["20261002-082739-o4-rh-chanbara", "20261002-083322-o4-rh-full",   # 7.3's evidence (F1-F15)
                       "20261002-083808-o4-rh-void"],
        "order": ["S", "F", "S", "F", "S", "F"],
        "min_covered": 2,
        "rerun": {"max": 2, "stop_on": ["V18", "V19"]},
        # F10 replaces every number from the rehearsals (4.12)
        "budget": {"run_s": 252, "run_min_s": 150, "session_s": 2760, "settle_s": 1.0, "no_progress_s": 60,
                   "end_row_s": 10.0},
        "start": {"S": ROUTE[0], "F": rm[ROUTE[0]]},
        "entrance": 100,
        "scenario": 1155,
        "lang": SESSION_LANG,
        "end_field": END_FIELD,
        "end_fields": [END_FIELD],
        "side_ends": {"S": [END_FIELD], "F": [rm[END_FIELD]]},
        "route": list(ROUTE),
        "visits": list(ROUTE),
        "stock_fields": [64, 150, 153],
        "members": {str(f): d for f, d in sorted(members.items())},
        "names": {str(f): n for f, n in sorted(names.items())},
        "text_block": TEXT_BLOCK,
        "text_blocks": list(TEXT_BLOCKS),
        "recovery": 4600,
        "cut_start": True,
        "start_first": key(64, 0, 0, 22, 16, "Global.Bit[191]", 0, ":=", "64's Main_Init: its first store"),
        "start_music": start_music,
        "start_residue": [[0, 0, 131], [1, 0, 4], [2, 0, 100]],     # SC 1155 = 0x0483; entrance 100's low byte
        "residue_after_start": [],
        "sc_bytes": [0, 1],
        "ladder": ladder,
        "entrance_bytes": [2, 3],
        "chain": chain,
        "writes": writes,
        "error_path": error_path,
        "forbidden_sites": forbidden_sites,
        "dead": dead,
        "inert": [{"donor": 150, "sid": s, "tags": "*", "why": "not instanced at entrance 325"}
                  for s in (10, 15, 16, 19, 23)],
        "start_dependent": [],
        "noise": [],
        "forbidden": [{"off_route": True, "cause": "walk",
                       "why": "a write off the route: S, a place outside route + end_fields; F, a field that is neither "
                              "a member whose donor is on the route nor F's own end field (real 64/150 on F: an "
                              "un-retargeted Field() or an engine id leak)"}],
        "landing": {"route_places": list(ROUTE),
                    "exit64": _site(64, 2, 1, 528, "Global.Int16[2]", 325),
                    "enter150": _site(150, 0, 0, 26, "Global.Bit[191]", 0),
                    "exit150": _site(150, 3, 1, 2161, "Global.Int16[2]", 325),
                    "end_row": _site(END_FIELD, 0, 0, 22, "Global.Bit[191]", 0)},
        "sword": {"score": _site(64, 4, 1, 338, "Global.Byte[475]", 100, old=0),
                  "combo": _site(64, 4, 1, 390, "Global.Bit[3815]", 1, old=0),
                  "page_123": PAGE_123, "combo_marks": list(COMBO_MARKS)},
        "end_state": {"Global.UInt16[0]": 1190, "Global.Int16[2]": 325, "Global.UInt16[21]": 1, "Global.Byte[303]": 1,
                      "Global.Byte[4]": 0, "Global.Byte[17]": 0, "Global.Byte[18]": 1, "Global.Byte[8]": 75,
                      "Global.Byte[475]": 100, "Global.Bit[3815]": 1,
                      "Global.Byte[13]": 0, "Global.Byte[14]": 0, "Global.Int16[9]": -1, "Global.Int16[11]": -1,
                      "Global.Bit[191]": 0, "Global.Bit[184]": 0,
                      "Global.Byte[6]": 0, "Global.UInt16[19]": 0, "Global.Byte[206]": 0, "Global.Int16[469]": 0,
                      "Global.Byte[472]": 0, "Global.Bit[3717]": 0, "Global.Bit[3718]": 0},
        "battles": [],
        "stop_pages": [{"match": "Env Play()",
                        "why": "64's and 150's ambient error window ('Error Env Play()  Slot=n': 64 e0 t0 ip835/869 "
                               "window 3, 150 e0 t0 ip999/1033 window 56): Byte[13]/[14] arrived as 2 or 9"},
                       {"match": "Set Scenario Counter()",
                        "why": "150's debug window 55 (e3 t1 ip1915, behind SC > 1190 at ip1884): waits for "
                               "Start/Select"}],
        "regions": {},
        "hotspots": {},
        "table": [],
        "choices": [{"donor": 64, "sc": [1155], "match": "encore", "pick": "No", "once": True, "beat": "encore"},
                    {"donor": None, "sc": None, "match": "want to skip", "pick": "default", "once": False,
                     "beat": None}],
        "naming": [],
        "beats": ["sword", "encore"],
        "chanbara": json.loads(json.dumps(POLICY)),
        "fight": {"pins": fight_pins(),
                  "prompt_mes": {str(112 + n): d for n, d in enumerate(("LEFT", "RIGHT", "TRIANGLE", "DOWN", "CROSS",
                                                                         "UP", "CIRCLE", "SQUARE"))},
                  "zone_start_mes": 111,
                  "page_sources": {"122": "Of 100 nobles watching,", "123": "quite impressed.",
                                   "128": "They shower you with"},
                  # O4-BUILD's fork-gate pins (6.1, per language): member(64)'s e4 t1 from the score through the
                  # Byte[475] store byte-equal to its donor's, the hook's statement at ip222; and the only bytes a
                  # route member differs from its donor in are its in-chain Field() operands, at these sites
                  "build": {"score": {"donor": 64, "sid": 4, "tag": 1, "from": SCORE_TEXT, "through": STORE_TEXT,
                                      "hook_ip": 222, "hook": HOOK_TEXT},
                            "fields": {"64": [[2, 1, 536, 150], [11, 2, 201, 153], [12, 2, 201, 153]],
                                       "150": [[3, 1, 2169, 153], [18, 2, 386, 153], [19, 2, 342, 153]]}}},
        "settings": json.loads(json.dumps(SETTINGS)),
        "override70": dict(OVERRIDE70),
        "derived": json.loads(json.dumps(DERIVED)),
        "engine": dict(ENGINE),
    }


# ======================================================================== the bytes: instancing, the census
_INIT = re.compile(r"^Init(Object|Region|Code)\((\d+)\b")
_LABEL = re.compile(r"L(\d+)")


def instancing_sites(idx) -> list:
    """Every instancing op of a script -- ``InitObject(n)``, ``InitRegion(n)``, ``InitCode(n)`` -- in every function:
    ``[(sid, tag, ip, kind, n)]`` (kind "object" | "region" | "code")."""
    out = []
    for e in idx.eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ip, _rel, t in A.O2Segment._items(idx, e.index, f.tag):
                m = _INIT.match(t)
                if m:
                    out.append((e.index, f.tag, ip, m.group(1).lower(), int(m.group(2))))
    return out


def instanced_at(idx, entrance: int, *, items=None) -> set:
    """The entries Main_Init (e0 t0) instances at ``entrance`` -- ``{(kind, n)}`` -- by its control flow: every item
    reachable from the function's start, the entrance dispatch (the SWITCH / SWITCHEX on ``Global.Int16[2]``) taken
    ONLY to ``entrance``'s case (its default when no case names it), every other branch and switch followed both ways
    (a SOUND over-approximation of what that entrance runs). The InitObject / InitRegion / InitCode ops among them.
    ``items`` (``[(ip, rel, eb-src text)]``, a seam) replaces the decode of ``idx``'s e0 t0. ValueError when Main_Init
    holds no entrance dispatch."""
    items = items if items is not None else A.O2Segment._items(idx, 0, 0)
    by_rel = {rel: i for i, (_ip, rel, _t) in enumerate(items)}
    k = next((i for i, (_ip, _rel, t) in enumerate(items) if t.startswith(("SWITCH(", "SWITCHEX("))
              and i > 0 and items[i - 1][2] == "SET({Global.Int16[2] B_EXPR_END})"), None)
    if k is None:
        raise ValueError("Main_Init holds no SWITCH / SWITCHEX on Global.Int16[2]: no entrance dispatch")

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
                tgt = entrance_target(t)
                i = by_rel.get(tgt)
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


def route_entrances(pred: dict) -> dict:
    """``{route place: the entrance it is entered by}``: the start place by ``entrance``; every later place by the
    value of the last ``chain`` key of the place before it (FieldEntrance before its Field())."""
    route = list(pred["route"])
    out = {route[0]: int(pred["entrance"])}
    for prev, cur in zip(route, route[1:]):
        keys = [k for k in pred.get("chain") or () if k["donor"] == prev]
        if keys:
            out[cur] = int(keys[-1]["value"])
    return out


#: O4-CENSUS's classes, in the order the detail prints them.
CENSUS_LISTS = ("writes", "ladder", "chain", "masked", "start_first", "error_path", "forbidden_sites", "dead", "inert")
#: ... and in the order a site is read against them: an ``inert`` FUNCTION never runs, so its sites count inert before
#: the story-noise mask (150 e10 t3's MOGNET stores are masked too: masked first, they would hide 212 of its 239 sites
#: from the inert claim); a masked site counts masked, 64's start_first too. A REGISTERED key in an inert function is
#: a contradiction (the key says it runs) and FAILS by name.
CENSUS_PRECEDENCE = ("writes", "ladder", "chain", "inert", "masked", "start_first", "error_path", "forbidden_sites",
                     "dead")
CENSUS_REGISTERED = ("writes", "ladder", "chain", "start_first", "error_path", "forbidden_sites", "dead")


def store_census(fields, stock, pred: dict, *, sites=None, classify=None) -> tuple:
    """O4-CENSUS's reader (research/o4_design.md 6.1): ``(problems, {field: Counter(class)}, proof)``. Every
    gEventGlobal store site of each stock field (``sites(idx)`` -> :func:`o3_prima_vista.store_sites`) must be one the
    predictions classify -- a ``writes``, ``ladder`` or ``chain`` key's, a story-noise-masked one, ``start_first``, an
    ``error_path``, ``forbidden_sites`` or ``dead`` key's (matched on donor, sid, tag, ip, target) -- or lie in an
    ``inert`` FUNCTION (``{"donor", "sid", "tags": "*" | [tags]}``, O4's own class: 0.2 #4). The inert claim is PROVEN
    from the bytes, never trusted: every instancing op of the field sits in e0 t0 (:func:`instancing_sites`), and the
    entrance the route enters it by (:func:`route_entrances`) instances none of the inert entries
    (:func:`instanced_at`). An unresolved store must be classified by its lvalue token (``classify``); a function that
    does not decode FAILS. ``proof``: ``{field: {"entrance", "instanced", "outside_e0"}}``."""
    sites = sites or P.store_sites
    classify = classify or P.lvalue_class
    reg: dict = {}
    for name in ("writes", "ladder", "chain", "start_first", "error_path", "forbidden_sites", "dead"):
        for k in ([pred[name]] if name == "start_first" else pred.get(name) or ()):
            reg.setdefault((k["donor"], k["sid"], k["tag"], k["ip"], k["target"]), set()).add(name)
    inert = {}
    for x in pred.get("inert") or ():
        inert.setdefault(int(x["donor"]), {})[int(x["sid"])] = x.get("tags", "*")
    entrances = route_entrances(pred)
    bad, counts, proof = [], {}, {}
    for fid in fields:
        idx = stock(fid)
        c = counts.setdefault(fid, Counter())
        if idx is None:
            bad.append(f"{fid}: no stock script")
            continue
        if fid in inert:
            ent = entrances.get(fid)
            outside = [s for s in instancing_sites(idx) if (s[0], s[1]) != (0, 0)]
            try:
                inst = instanced_at(idx, ent) if ent is not None else None
            except ValueError as err:
                inst = None
                bad.append(f"{fid}: {err}")
            proof[fid] = {"entrance": ent, "instanced": sorted(inst or ()), "outside_e0": outside}
            for s in outside:
                bad.append(f"{fid} e{s[0]} t{s[1]} ip{s[2]}: an instancing op outside Main_Init (Init{s[3].title()}"
                           f"({s[4]})): the inert proof needs every one in e0 t0")
            if ent is None:
                bad.append(f"{fid}: no entrance the route enters it by: the inert proof cannot run")
            for sid in sorted(inert[fid]):
                if inst is not None and any(n == sid for _kind, n in inst):
                    bad.append(f"inert entry {sid} of {fid} is instanced at entrance {ent} "
                               f"({sorted(k for k, n in inst if n == sid)}): the proof fails")
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


# ======================================================================== text: strict, and P-TEXT's two phases
def strict_text(lines: list) -> tuple:
    """O4-TEXT's verdict (rev. 2, the claim critique #12) over :func:`o2_alexandria.text_rule`'s lines, pure: ``(ok,
    detail)`` -- FAIL on any FAIL line AND on any KNOWN-KIT-DEFECT line. text_rule only NAMES another language's copy
    (it passes it); O4 claims per-language text, so a defect is a failure here."""
    defects = [ln for ln in lines if ln.startswith("KNOWN-KIT-DEFECT")]
    fails = [ln for ln in lines if ln.startswith("FAIL")]
    return not defects and not fails, A.text_detail(lines)


def p_text(block: int, found: list, stock: dict, *, o1_block2: dict | None, o4_registered: bool,
           lang: str = SESSION_LANG) -> tuple:
    """P-TEXT for one block (6.2; rev. 2), pure: ``(ok, detail)``. ``found`` is ``[(folder name, {lang: bytes})]`` of
    every stacked folder that ships the block. Block 3 is STRICT always (:func:`strict_text`): a KNOWN-KIT-DEFECT line
    FAILs; none shipped passes. Block 2, while no O4 member is registered (``o4_registered`` False): the ONE tolerated
    defect is O1's known copy -- FF9CustomMap's block 2 whose per-language shas equal ``o1_block2`` exactly -- and its
    line is printed, named; any other defect FAILs. Once an O4 member is registered: strict (O4's deploy rewrote it)."""
    if not found:
        return True, f"no mod folder ships block {block}"
    ok_all, parts = True, []
    for name, shipped in found:
        ok, lines = A.text_rule(stock, shipped, lang)
        defects = [ln for ln in lines if ln.startswith("KNOWN-KIT-DEFECT")]
        shas = {L: _sha(b) for L, b in shipped.items()}
        tolerated = (block == 2 and not o4_registered and name == "FF9CustomMap" and o1_block2 is not None
                     and shas == o1_block2)
        note = ""
        if defects and tolerated:
            note = " (O1's copy, o4_forks.json text_effects.o1_block2: tolerated before O4's deploy)"
        elif defects:
            ok = False
            note = (" (strict: block 3 has no tolerated copy)" if block != 2 else
                    " (strict: an O4 member is registered -- O4's deploy rewrites block 2 per language)" if o4_registered
                    else " (not O1's copy: no other defect is tolerated)")
        ok_all = ok_all and ok
        parts.append(A.text_detail(lines, where=f"{name}: ") + note)
    return ok_all, " | ".join(parts)


# ======================================================================== the pads, the keys: P-PAD and the witness
def _xinput_lib():
    import ctypes
    for name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
        try:
            return ctypes.WinDLL(name)
        except (OSError, AttributeError):
            continue
    return None


def xinput_reader():
    """P-PAD's reader (6.2), the ctypes default of every seam: ``read(slot) -> None | {"buttons", "lt", "rt", "lx",
    "ly", "rx", "ry"}`` -- ``XInputGetState(slot, &state)``: 0 = connected, anything else (1167 ERROR_DEVICE_NOT_
    CONNECTED) is not -- from ``xinput1_4`` (else ``xinput1_3``, ``xinput9_1_0``). None when the host has no XInput
    runtime (nothing can be connected)."""
    import ctypes
    from ctypes import wintypes
    lib = _xinput_lib()
    if lib is None:
        return None

    class _Pad(ctypes.Structure):
        _fields_ = [("wButtons", wintypes.WORD), ("bLeftTrigger", ctypes.c_ubyte), ("bRightTrigger", ctypes.c_ubyte),
                    ("sThumbLX", ctypes.c_short), ("sThumbLY", ctypes.c_short), ("sThumbRX", ctypes.c_short),
                    ("sThumbRY", ctypes.c_short)]

    class _State(ctypes.Structure):
        _fields_ = [("dwPacketNumber", wintypes.DWORD), ("Gamepad", _Pad)]
    get = lib.XInputGetState
    get.argtypes = [wintypes.DWORD, ctypes.POINTER(_State)]
    get.restype = wintypes.DWORD

    def read(slot: int):
        s = _State()
        if get(int(slot), ctypes.byref(s)) != 0:
            return None
        p = s.Gamepad
        return {"buttons": int(p.wButtons), "lt": int(p.bLeftTrigger), "rt": int(p.bRightTrigger),
                "lx": int(p.sThumbLX), "ly": int(p.sThumbLY), "rx": int(p.sThumbRX), "ry": int(p.sThumbRY)}
    return read


def pad_nonneutral(state: dict | None) -> str | None:
    """What makes one pad reading NON-NEUTRAL (6.2's thresholds), or None: a button bit, a trigger at or past
    :data:`PAD_TRIGGER`, a thumb axis past :data:`PAD_THUMB`."""
    if not state:
        return None
    what = []
    if int(state.get("buttons", 0)):
        what.append(f"buttons 0x{int(state['buttons']):04X}")
    for k in ("lt", "rt"):
        if int(state.get(k, 0)) >= PAD_TRIGGER:
            what.append(f"trigger {k} {int(state[k])}")
    for k in ("lx", "ly", "rx", "ry"):
        if abs(int(state.get(k, 0))) > PAD_THUMB:
            what.append(f"thumb {k} {int(state[k])}")
    return ", ".join(what) or None


def xinput_slots(reader=..., *, reads: int = PAD_READS, every: float = PAD_EVERY_S, sleep=time.sleep) -> dict:
    """P-PAD's sample (6.2): ``reads`` readings of XInput slots 0-3, ``every`` s apart -- ``{"runtime": bool,
    "samples": [[slot 0..3 reading | None], ...]}``. ``reader`` (a seam) is ``read(slot)``; ``...`` (the default)
    takes :func:`xinput_reader`'s, and None means the host has no XInput runtime."""
    if reader is ...:
        reader = xinput_reader()
    if reader is None:
        return {"runtime": False, "samples": []}
    out = []
    for n in range(int(reads)):
        out.append([reader(slot) for slot in range(4)])
        if n + 1 < reads:
            sleep(float(every))
    return {"runtime": True, "samples": out}


def p_pad(sampled: dict) -> tuple:
    """P-PAD (6.2; critique minor #7), pure: ``(ok, detail)`` over :func:`xinput_slots`' sample. FAIL on any reading of
    any slot that is non-neutral (:func:`pad_nonneutral`); a connected IDLE pad PASSES with the WARN line (unplug it
    for the session: AlwaysCaptureGamepad = 1 ORs its input in even unfocused); no pad PASSES; no XInput runtime
    PASSES ("nothing can be connected")."""
    if not sampled.get("runtime"):
        return True, "no XInput runtime on this host: nothing can be connected"
    samples = sampled.get("samples") or []
    bad, connected = [], set()
    for n, row in enumerate(samples):
        for slot, st in enumerate(row):
            if st is None:
                continue
            connected.add(slot)
            what = pad_nonneutral(st)
            if what:
                bad.append(f"slot {slot}, read {n + 1}: {what}")
    if bad:
        return False, (f"a pad is NOT neutral ({len(bad)} reading(s)): " + "; ".join(bad[:4])
                       + " -- AlwaysCaptureGamepad = 1 ORs it in even unfocused: a press during the fight")
    if connected:
        return True, "; ".join(f"WARN: an XInput pad is connected at slot {s} (idle over the sample) -- unplug it for "
                               f"the session: AlwaysCaptureGamepad = 1 ORs its input in even unfocused"
                               for s in sorted(connected))
    return True, f"no XInput pad connected at slots 0-3 ({len(samples)} reads {int(PAD_EVERY_S * 1000)} ms apart)"


def keys_down() -> list:
    """The virtual keys and mouse buttons down now (``GetAsyncKeyState`` 0x01-0xFE, the high bit): the witness's key
    reader, read only while the game has focus."""
    import ctypes
    user32 = ctypes.windll.user32
    return [vk for vk in range(0x01, 0xFF) if user32.GetAsyncKeyState(vk) & 0x8000]


def foreground_pid() -> int:
    """The pid of the process owning the foreground window (``GetForegroundWindow``, ``GetWindowThreadProcessId``): 0
    when no window has the foreground. Two user32 calls -- microseconds."""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(pid))
    return int(pid.value)


def focus_reader(g, *, probe=None, foreground=None):
    """The input witness's FOCUS reader (2.4.3 step 0; the review, research/o4_design.md 11.5 #8): ``focused() ->
    bool`` -- whether the foreground window belongs to the game's process (the keyboard needs focus,
    HonoInputManager.cs:561). The game's pids are resolved ONCE, here, when the witness is made (before the drive),
    through ``probe`` (default the session's ``_pid_probe``, else harness.session.ff9_pids: a ``tasklist`` spawn, 0.1 s
    and more -- never on the witness's hot path, which the fight's 5 ms loop polls every 50 ms); each read is then one
    ``foreground()`` (:func:`foreground_pid`, a seam). FAIL-CLOSED: with no pid resolved (none, or the probe raised)
    ``focused()`` raises, and so does a ``foreground()`` that fails -- the witness reports either as a reading (V13),
    never as "unfocused": the keyboard is never silently unwitnessed."""
    if probe is None:
        probe = getattr(g, "_pid_probe", None)
    if probe is None:
        from harness.session import ff9_pids as probe
    foreground = foreground or foreground_pid
    try:
        pids = frozenset(int(p) for p in (probe() or ()))
        why = None if pids else "the probe found no FF9.exe"
    except Exception as err:                       # noqa: BLE001 -- reported by every read, never swallowed
        pids, why = frozenset(), f"the probe raised {type(err).__name__}: {str(err)[:120]}"

    def focused() -> bool:
        if why is not None:
            raise RuntimeError(f"the game's pid is unknown ({why})")
        return int(foreground()) in pids
    return focused


def input_witness(g, *, pads=None, keys=None, focus=None, clock=None):
    """THE INPUT WITNESS (2.4.3 step 0; rev. 2, the claim critique #4): a callable the driver polls -- every
    ``input_every_s`` in the fight's tight loop, and between the main loop's blocking calls through the whole run --
    returning None while everything is neutral, else what it read. XInput slots 0-3 through P-PAD's reader (``pads``:
    ``read(slot)``; a slot found disconnected is re-read at most once a second, ``clock`` the seam), then -- only while
    the game window has focus (``focus()``) -- every key and mouse button down (``keys()``: F1, the booster, among
    them). The harness's own presses are injected below the OS and never read here. Each reader defaults to the ctypes
    one; ``pads`` None with no XInput runtime reads no pad. The default ``focus`` is :func:`focus_reader`'s: the game's
    pids resolved once, as the witness is made -- never a process spawned on a poll (the review, 11.5 #8) -- and a
    focus that cannot be read is a reading, never "unfocused" (fail-closed: V13)."""
    pads = pads if pads is not None else (xinput_reader() or (lambda slot: None))
    keys = keys if keys is not None else keys_down
    focus = focus if focus is not None else focus_reader(g)
    clock = clock or time.monotonic
    empty: dict = {}

    def witness():
        now = clock()
        for slot in range(4):
            t = empty.get(slot)
            if t is not None and now - t < PAD_EMPTY_S:
                continue
            st = pads(slot)
            if st is None:
                empty[slot] = now
                continue
            empty.pop(slot, None)
            what = pad_nonneutral(st)
            if what:
                return f"XInput slot {slot}: {what}"
        try:
            focused = focus()
        except Exception as err:                    # noqa: BLE001 -- fail-closed: an unread focus is a reading
            return (f"the focus could not be read ({type(err).__name__}: {str(err)[:160]}): the keyboard is "
                    f"unwitnessed")
        if focused:
            down = list(keys() or ())
            if down:
                return (f"key(s) down while the game has focus: "
                        + ", ".join(f"0x{int(k):02X}" for k in down[:6]))
        return None
    return witness


# ======================================================================== the engine, the override, the gate
def engine_shas(game=GAME) -> dict:
    """``{"x64", "x86"}``: the sha256 of each live ``FF9_Data/Managed/Assembly-CSharp.dll`` (None when absent)."""
    return {arch: _sha_file(Path(game) / arch / "FF9_Data" / "Managed" / "Assembly-CSharp.dll")
            for arch in ("x64", "x86")}


def engine_files(game=GAME) -> dict:
    """``{path: mtime}`` of the two live engine DLLs (P-LAUNCH dates them against the launch, rev. 2)."""
    out = {}
    for arch in ("x64", "x86"):
        p = Path(game) / arch / "FF9_Data" / "Managed" / "Assembly-CSharp.dll"
        try:
            out[str(p)] = p.stat().st_mtime
        except OSError:
            pass
    return out


def p_engine(live: dict, pinned: dict) -> tuple:
    """P-ENGINE (6.2; rev. 2, the claim critique #9), pure: ``(ok, detail)`` -- the live x64 and x86
    Assembly-CSharp.dll sha256 each equal the pinned ``engine``'s. Another sha, or x86 differing from x64, FAILS."""
    bad = [f"{arch} {str(live.get(arch))[:12]} (pinned {str(pinned.get(arch))[:12]})" for arch in ("x64", "x86")
           if live.get(arch) is None or live.get(arch) != pinned.get(arch)]
    if bad:
        return False, "the live engine is not the pinned one: " + "; ".join(bad) + " -- a session on another engine is " \
                                                                                   "no session of this claim"
    return True, f"x64 and x86 Assembly-CSharp.dll = {pinned['x64'][:12]} (pinned)"


def override70_of(roots) -> dict:
    """``{folder name: sha256}`` of field 70's override .eb (us) in every stacked folder that ships one -- O2's
    fingerprint's ``override70``."""
    out = {}
    for r in roots:
        p = T._override_path(r, 70, "us")
        if p is not None and p.is_file():
            out[Path(r).name] = _sha(p.read_bytes())
    return out


def p_override(fp: dict, pinned: dict) -> tuple:
    """P-OVERRIDE (6.2; critique minor #9), pure: ``(ok, detail)`` -- the fingerprint's ``override70`` (``{folder:
    sha}``) equals the pinned one: exactly one stacked folder ships field 70's override, with that sha. Another sha, a
    second folder, none: FAIL each."""
    if fp == pinned:
        (name, sha), = pinned.items()
        return True, f"field 70's override ships in {name} only, sha {sha[:12]} (pinned)"
    return False, (f"field 70's override is {({n: str(s)[:12] for n, s in fp.items()} or 'shipped by no folder')}, "
                   f"pinned {({n: s[:12] for n, s in pinned.items()})}: the warp window (4.6) is proven under the pinned "
                   f"one only")


def member_eb(root, name: str) -> dict:
    """``{lang: sha256 | None}``: a member's .eb in every language under one mod root -- a build's or a stacked
    folder's (``ModLayout``) -- None where absent."""
    from ff9mapkit.config import LANGS, ModLayout
    lay = ModLayout(Path(root))
    return {L: _sha_file(lay.eb_path(L, f"EVT_{name}.eb.bytes")) for L in LANGS}


def live_member(game, fid: int, name: str, *, roots=None) -> dict:
    """``{"id", "name", "folder", "eb"}``: a member as the live install holds it -- the first stacked folder that
    registers it (P-EB's reading) and its .eb's sha256 per language (:func:`member_eb`; None with no such folder).
    R-GATE records it for its F side (the review, research/o4_design.md 11.5 #4): P-GATE ties the witness to it."""
    if roots is None:
        import dali_tour as D
        try:
            roots = D.mod_roots(Path(game))
        except OSError:
            roots = []
    live = [r for r in roots if int(fid) in T.mod_registrations(r)]
    return {"id": int(fid), "name": name, "folder": Path(live[0]).name if live else None,
            "eb": member_eb(live[0], name) if live else None}


def gate_record(run_dir) -> dict | None:
    """R-GATE's launch record -- ``<run_dir>/o4_rehearsal.json`` -- or None when it cannot be read."""
    try:
        return json.loads((Path(run_dir) / REHEARSAL_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None


def gate_backing(w: dict, rec: dict | None, member64: dict | None) -> list:
    """What R-GATE's own launch record does NOT back in a hand-filled ``gate_witness`` (the review,
    research/o4_design.md 11.5 #4), pure: ``[problem]``. The record (``<run_dir>/o4_rehearsal.json``) must be an R-GATE
    launch (``stages_run`` exactly ["R-GATE"]) whose recorded verdict -- its verdict, cause, S run and F run -- is the
    witness's, whose launch recorded the witness's engine and settings, and whose F side ran ``member64``: the
    session's member(64), by its id and its offline-checked build (each language's .eb sha256 -- P-EB pins the live
    files to that build). A witness copied wrong, another stage's, or another build's is no witness."""
    if rec is None:
        return [f"its run dir {w.get('run_dir')!r} holds no readable {REHEARSAL_FILE}: no launch record backs it"]
    bad = []
    if rec.get("stages_run") != ["R-GATE"]:
        bad.append(f"its record ran {rec.get('stages_run')}, not R-GATE alone")
    gv = (rec.get("gate") or {}).get("R-GATE")
    if not isinstance(gv, dict):
        return bad + ["its record holds no R-GATE verdict"]
    bad += [f"its {k} {w.get(k)!r} is not the record's {gv.get(k)!r}" for k in ("verdict", "cause", "s_run", "f_run")
            if w.get(k) != gv.get(k)]
    launch = rec.get("launch") or {}
    if any((launch.get("engine") or {}).get(a) != (w.get("engine") or {}).get(a) for a in ("x64", "x86")):
        bad.append(f"its engine is not the one its launch recorded "
                   f"({str((launch.get('engine') or {}).get('x64'))[:12]})")
    if launch.get("settings") != w.get("settings"):
        bad.append("its settings are not the ones its launch recorded")
    m = gv.get("member")
    if member64 is None:
        bad.append("the session's member(64) is unknown: the witness cannot be tied to its build")
    elif not isinstance(m, dict):
        bad.append("its record names no member(64) its F side ran: re-run R-GATE")
    elif m.get("id") != member64.get("id"):
        bad.append(f"its F side ran {m.get('id')}, the session's member(64) is {member64.get('id')}")
    elif m.get("eb") != member64.get("eb"):
        diff = [L for L in sorted(member64.get("eb") or {}) if (m.get("eb") or {}).get(L) != member64["eb"].get(L)]
        bad.append(f"its F side ran another build of member(64) {m.get('id')} ({', '.join(diff) or 'its .eb'} differ "
                   f"from the build P-EB checks): re-run R-GATE on this build")
    return bad


def p_gate(manifest: dict, live_engine: dict, settings: dict, *, pinned_engine: dict | None = None,
           member64: dict | None = None, read=None) -> tuple:
    """P-GATE (6.2; decision 5; rev. 2, the claim critique #9, #10; the review, 11.5 #4), pure but for ``read``
    (:func:`gate_record`, a seam): ``(ok, detail)``. ``o4_forks.json``'s ``gate_witness`` must name a run dir, a
    verdict, a cause, the ``engine`` its launch ran and the ``settings`` it recorded -- and its run dir's own launch
    record must BACK it (:func:`gate_backing`: R-GATE alone, its recorded verdict, cause and runs, its launch's engine
    and settings, and its F side's member(64) the session's ``member64`` in the build P-EB checks): the witness is
    hand-filled, the record is what ran. PASS only when, too, that engine is the live DLLs' and the pinned one, the
    settings are the frozen ones (``SwordplayAssistance`` 1 above all: at 2 stock shows 100 without the +30%), and the
    verdict is WITNESSED -- or BROKEN with cause "bonus" (the wrap did not fire: a finding the fast session survives).
    BROKEN with cause "combo" FAILS (the fork did not credit proper presses: diagnose it first), and so do INVALID,
    UNINFORMATIVE and no witness. The detail carries the whole witness, so the session's recorded preflight holds it
    (5.4): it opens with ``R-GATE <verdict> (cause <cause>)``."""
    read = read or gate_record
    pinned_engine = pinned_engine or ENGINE
    w = (manifest or {}).get("gate_witness")
    if not w:
        return False, "R-GATE none (cause none): no gate_witness in o4_forks.json -- R-GATE has not run (7.4 G2)"
    verdict, cause = w.get("verdict"), w.get("cause")
    head = f"R-GATE {verdict} (cause {cause or 'none'})"
    bad = gate_backing(w, read(w["run_dir"]) if w.get("run_dir") else None, member64)
    if verdict not in GATE_VERDICTS:
        bad.append(f"verdict {verdict!r} is not one of {GATE_VERDICTS}")
    eng = w.get("engine") or {}
    for arch in ("x64", "x86"):
        if eng.get(arch) is None or eng.get(arch) != live_engine.get(arch) or eng.get(arch) != pinned_engine.get(arch):
            bad.append(f"its engine {arch} {str(eng.get(arch))[:12]} is not the live and pinned "
                       f"{str(live_engine.get(arch))[:12]}")
    if w.get("settings") != settings:
        sa = ((w.get("settings") or {}).get("Hacks") or {}).get("SwordplayAssistance")
        bad.append(f"its launch's settings are not the frozen ones (SwordplayAssistance {sa!r})")
    if verdict == "BROKEN" and cause == "combo":
        bad.append("BROKEN with cause combo: the fork did not credit proper presses -- the +30% was never witnessed; "
                   "diagnose it before the session")
    elif verdict == "BROKEN" and cause != "bonus":
        bad.append(f"BROKEN with cause {cause!r}: not one of {GATE_CAUSES}")
    elif verdict in ("INVALID", "UNINFORMATIVE"):
        bad.append(f"{verdict}: no witness of the +30% (7.4 G2: STOP)")
    witness = json.dumps(w, sort_keys=True)
    backed = f"; its launch record backs it (R-GATE alone; member(64) {(member64 or {}).get('id')}, this build)"
    return (not bad, head + (": " + "; ".join(bad) if bad else
                             (": the EMinigame +30% fires on member(64)" if verdict == "WITNESSED" else
                              ": the wrap did not fire on member(64) -- a finding; the fast session's raw >= 100 is "
                              "clamp-proof") + backed)
            + f" | witness {witness}")


def gate_reading(side: str, *, zone: dict | None, prompts: list, presses: list, pages: list, page_judge: list,
                 byte475, pol: dict, settings=None, engine=None, v: str | None = None) -> dict:
    """One R-GATE run as its verdict reads it (7.4 G2; the review, 11.5), pure: ``{"side", "informative", "why", "raw",
    "judge", "page", "number", "combo", "byte475", "zone_v", "settings", "engine", "v"}``; ``v`` is the run's own VOID
    class (o4_rehearse records V13 for an instrument stop). INFORMATIVE only when, in this order: the fight was entered
    (a zone row); the zone row's own verdict is none or V18 (never a V13, V14, V4, V11, V19 or live V17 stop); the
    run's class is none or V18 (:data:`GATE_RUN_VOIDS`); the judge over the rows finds no V17 fault; then EITHER the fight
    reads V18 (the zone's verdict or the judge's: a lingered press, a slide's miss, a prompt too many) -- on F the
    fork's answer, BROKEN with cause "combo", mid-fight too; on S the stock game deviating from the paced play, which
    witnesses nothing of the stock bonus: re-run it -- OR the fight is COMPLETE (its end seen) under a paced policy
    with its raw BOUNDED and ``[raw_lo, raw_hi]`` inside ``pace.raw_band``, the score page was read, and -- but for a
    combo page -- the trace holds Byte[475]. ``why`` names the first that fails. ``page``: the score page as read in
    two samples (a ``page_judge`` row's, else the first page holding "nobles watching"); ``number`` its number;
    ``combo``: a COMBO page (120/121) was shown; ``byte475``: the trace's 64 e4 t1 ip338 row's new value; ``zone_v``
    the zone row's own verdict."""
    if zone is None:
        judge = {"v": "V17", "by": "driver", "why": "no zone row: the fight was never entered", "faults": [],
                 "raw": [None, None]}
    else:
        judge = SD.chanbara_judge(zone, prompts, presses, pol)
    reading = None
    for row in page_judge or ():                    # the score page the run STOPPED at, as two samples read it
        if row.get("kind") == "score":
            reading = SD.page_reading(list(row.get("texts") or []), pol["score_page"])[1] or reading
    if reading is None:                             # else the score page the run pressed (read in two samples)
        reading = next((p for p in pages or () if SD.SCORE_MARK in p), None)
    combo = any(m in p for p in list(pages or ()) + ([reading] if reading else []) for m in COMBO_MARKS)
    m = re.search(r"(\d+) were impressed", reading or "")
    zv = (zone or {}).get("v")
    raw = list(judge.get("raw") or [None, None])[:2]
    band = (pol.get("pace") or {}).get("raw_band")
    if zone is None:
        why = judge["why"]
    elif zv not in (None, "V18"):
        why = f"the zone's verdict {zv}: {zone.get('why')}"
    elif v not in GATE_RUN_VOIDS:
        why = "an instrument stop (V13)" if v == "V13" else f"the run VOID {v}" + (" (the driver's)" if v == "V17"
                                                                                    else "")
    elif judge["v"] == "V17":
        why = judge["why"]
    elif zv == "V18" or judge["v"] == "V18":
        why = None if side == "F" else (f"the stock game deviated from the paced play (V18: "
                                        f"{judge.get('why') or zone.get('why')}): it witnesses nothing of the stock "
                                        f"bonus -- re-run")
    elif zone.get("end") is None:
        why = "the fight stopped before its end"
    elif not band:
        why = "not a paced run: no pace.raw_band to judge the raw by"
    elif raw[0] is None or raw[1] is None:
        why = "the raw is unbounded"
    elif not band[0] <= raw[0] <= raw[1] <= band[1]:
        why = f"raw [{raw[0]}, {raw[1]}] is outside the band {list(band)}"
    elif reading is None:
        why = "no score page was read: the run stopped before it"
    elif byte475 is None and not combo:
        why = "the trace holds no Byte[475] row (64 e4 t1 ip338)"
    else:
        why = None
    return {"side": side, "informative": why is None, "why": "informative" if why is None else f"uninformative: {why}",
            "raw": judge.get("raw"), "judge": judge, "page": reading, "number": int(m.group(1)) if m else None,
            "combo": combo, "byte475": byte475, "zone_v": zv, "settings": settings, "engine": engine, "v": v}


def gate_verdict(runs: list, *, settings: dict | None = None, engine: dict | None = None,
                 attempts: int = GATE_ATTEMPTS) -> dict:
    """R-GATE's VERDICT (7.4 G2; rev. 2), pure: ``{"verdict", "cause", "s_run", "f_run", "detail", "no_witness"}`` over
    its runs' :func:`gate_reading`'s, in run order. A run whose launch recorded settings other than ``settings``
    (SwordplayAssistance 2 above all) or an engine other than ``engine`` is NO WITNESS (re-run on a corrected launch):
    it is set aside, never counted. Of the rest, each side's first INFORMATIVE run among its first ``attempts``
    (:func:`gate_reading`: a run stopped by the instrument, the driver or mid-fight, or an S run whose fight the stock
    game deviated from, is never informative -- it is re-run, and never reaches INVALID):
    - none on a side: UNINFORMATIVE (STOP: re-tune the pace from the attempts' j, or read the attempts' whys);
    - the S run must show page 122 with 100 and Byte[475] 100 (the stock +30% lifted a raw 79-99 to 100), else
      INVALID (STOP: the settings or the stock bonus are not what 0.2 #11 reads -- or, with a combo page on a proven
      play, cfg.control or the input path is not what 0.2 #6 reads, F2);
    - the F run: Byte[475] 100 and page 122 with 100 -> WITNESSED ("the EMinigame +30% fires on member(64)"); a COMBO
      page (120/121) or a V18 of the fight (the judge's or the zone's) -> BROKEN, cause "combo" (the fork did not credit
      49 proper presses); Byte[475] the raw (inside the run's raw bounds) and page 122 with that number -> BROKEN, cause
      "bonus" (the wrap does not fire: a finding); anything else -> INVALID (the page and the store disagree: the
      instrument's)."""
    settings = settings if settings is not None else SETTINGS
    engine = engine if engine is not None else ENGINE
    no_witness, valid = [], []
    for i, r in enumerate(runs):
        eng = r.get("engine") or {}
        if r.get("settings") != settings or any(eng.get(a) != engine.get(a) for a in ("x64", "x86")):
            sa = ((r.get("settings") or {}).get("Hacks") or {}).get("SwordplayAssistance")
            no_witness.append(f"run {i} ({r.get('side')}): its launch recorded SwordplayAssistance {sa!r} / engine "
                              f"{str(eng.get('x64'))[:12]} -- no witness (re-run on a corrected launch)")
            continue
        valid.append((i, r))

    def first(side):
        tried = [(i, r) for i, r in valid if r["side"] == side][:attempts]
        return next(((i, r) for i, r in tried if r["informative"]), None), len(tried)
    out = {"verdict": None, "cause": None, "s_run": None, "f_run": None, "detail": "", "no_witness": no_witness}
    (s, ns), (f, nf) = first("S"), first("F")
    if s is None:
        out.update(verdict="UNINFORMATIVE", detail=f"no informative S run in {ns} attempt(s) (of {attempts})"
                   + (f"; {'; '.join(no_witness)}" if no_witness else ""))
        return out
    si, sr = s
    out["s_run"] = si
    if sr["combo"]:
        out.update(verdict="INVALID", detail=f"the S run (run {si}) shows a combo page (120/121) on a proven paced play: "
                                             f"stock did not credit 49 proper presses -- STOP, cfg.control or the "
                                             f"input path is not what 0.2 #6 reads (F2)")
        return out
    if not (sr["number"] == 100 and sr["byte475"] == 100):
        out.update(verdict="INVALID", detail=f"the S run (run {si}) shows {sr['page']!r} and Byte[475] {sr['byte475']}: "
                                             f"not 100 through the stock +30% -- STOP, the settings or the stock bonus "
                                             f"are not what 0.2 #11 reads")
        return out
    if f is None:
        out.update(verdict="UNINFORMATIVE", detail=f"no informative F run in {nf} attempt(s) (of {attempts})"
                   + (f"; {'; '.join(no_witness)}" if no_witness else ""))
        return out
    fi, fr = f
    out["f_run"] = fi
    lo, hi = (fr.get("raw") or [None, None])[:2]
    if fr["combo"] or fr["judge"].get("v") == "V18" or fr.get("zone_v") == "V18":
        out.update(verdict="BROKEN", cause="combo",
                   detail=f"the F run (run {fi}) " + ("shows a combo page (120/121)" if fr["combo"] else
                                                      f"reads V18: {fr['judge'].get('why') or 'the zone stopped V18'}")
                          + ": a combo page, not the +30% -- the fork did not credit 49 proper presses")
    elif fr["byte475"] == 100 and fr["number"] == 100:
        out.update(verdict="WITNESSED", detail=f"S run {si} and F run {fi} both show 100 from a raw in "
                                               f"[{lo}, {hi}]: the EMinigame +30% fires on member(64)")
    elif fr["byte475"] is not None and fr["byte475"] == fr["number"] and lo is not None and lo <= fr["byte475"] <= hi:
        out.update(verdict="BROKEN", cause="bonus",
                   detail=f"the F run (run {fi}) shows {fr['number']} and Byte[475] {fr['byte475']}, its raw bounds "
                          f"[{lo}, {hi}]: the wrap does not fire on member(64) -- a finding")
    else:
        out.update(verdict="INVALID", detail=f"the F run (run {fi}) shows page {fr['page']!r} and Byte[475] "
                                             f"{fr['byte475']} (raw [{lo}, {hi}]): they disagree -- the instrument's")
    return out


# ======================================================================== a trace, summarised (end PLACES)
def trace_summary(rows: list, pred: dict, *, side: str = "S", start_place: int | None = None, end_fields=None,
                  stock=None, scripts=None, log: list | None = None) -> dict:
    """One trace, summarised for a reader (7.2; the rehearsal report and the dry run): cut at its start row and at its
    first row in an END PLACE -- ``end_fields`` (a stage's raw ids, default the side's) turned into places through the
    members on F (rev. 2, the claim critique #14: O2's and O3's summaries pass end FIELDS to the place-comparing cut,
    so an F stage ending in a member would never be cut). Then the SC and FieldEntrance rows (raw, with their joined
    keys), every registered key present or absent, every UNREGISTERED key, the sword rows (ip338 / ip390: count, old,
    new, fld), the 64 -> 150 crossing, the end cut's raw row, the residue before and after the start, the masked
    counts, the join failures, and -- given the run's driver ``log`` -- its forbidden hits with their backing."""
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
    for name in ("ladder", "chain", "writes", "error_path", "forbidden_sites", "dead"):
        for k in pred.get(name) or ():
            wk = wkey(k)
            reg.add(wk)
            registered.setdefault(name, []).append({"what": A.label(k), "present": wk in d.keys or wk in d.seam_keys})
    sword = {}
    for name, s in (pred.get("sword") or {}).items():
        if not isinstance(s, dict):
            continue
        hit = [x for x in kept if x.k == "w" and place(x.fld, members) == s["place"]
               and (x.sid, x.tag, x.ip, x.target) == (s["sid"], s["tag"], s["ip"], s["target"])]
        sword[name] = {"count": len(hit), "rows": [[x.fld, x.old, x.new, x.f] for x in hit]}
    crossing = None
    lnd = pred.get("landing") or {}
    ex = lnd.get("exit64")
    if ex:
        i = next((j for j, x in enumerate(kept) if x.k == "w" and x.m == T.FIELD_MODE
                  and place(x.fld, members) == ex["place"]
                  and (x.sid, x.tag, x.ip, x.target, x.new) == (ex["sid"], ex["tag"], ex["ip"], ex["target"],
                                                                ex["value"])), None)
        if i is not None:
            nxt = next((x for x in kept[i + 1:] if x.k == "w" and x.m == T.FIELD_MODE), None)
            crossing = {"exit": A._row_text(kept[i]), "next": None if nxt is None else A._row_text(nxt)}
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
            "registered": registered, "sword": sword, "crossing": crossing,
            "unregistered": [A._fmt_key(k) for k in keys if k not in reg and not is_noise(k, pred)],
            "end_row": None if cut_row is None else (f"{cut_row.k} " + (A._row_text(cut_row) if cut_row.k == "w"
                                                                       else f"{cut_row.fld} byte {cut_row.byte}")),
            "end_row_fld": None if cut_row is None else cut_row.fld,
            "seam_keys": [A._fmt_key(k) for k in sorted(d.seam_keys, key=T.WriteKey.sort_key)],
            "masked": dict(d.masked), "residue_masked": d.residue_masked,
            "failures": [[A._row_text(r), why[:160]] for r, why in d.failures], "forbidden": hits}


# ======================================================================== the fight, read off a run's own rows
def _rows(log, k: str, **match) -> list:
    return [r for r in log or () if r.get("k") == k and all(r.get(a) == b for a, b in match.items())]


def zone_of(log: list) -> dict | None:
    """The run's (first) ``zone`` row, or None."""
    return next((r for r in log or () if r.get("k") == "zone"), None)


def fight_rows(log: list) -> tuple:
    """``(zone, prompts, prompt presses, other presses)`` of a run's driver log: the zone row, its prompt rows (the
    zone's visit), the ``press`` rows of the prompts, and every other ``press`` row with a ``seq`` of that visit."""
    z = zone_of(log)
    visit = None if z is None else z.get("visit")
    prompts = [r for r in log or () if r.get("k") == "prompt" and (visit is None or r.get("visit") == visit)]
    presses = [r for r in log or () if r.get("k") == "press" and r.get("seq") is not None
               and (visit is None or r.get("visit") == visit)]
    return z, prompts, [p for p in presses if p.get("why") == "prompt"], [p for p in presses if p.get("why") != "prompt"]


def fight_line(log: list, outcome: dict | None = None) -> dict:
    """The fight of one run as the report and the rehearsal record print it (5.4, 7.2): instances, presses, the first
    prompt's ticks after T0, j_hi min / median / max, raw, the regimes, the merged stream's samples and its longest
    read gap, the evidence counts, the gone latency (median ticks from the down frame to the first sample without),
    the slides, the input witness, the prompt forms seen, the judge."""
    z, prompts, _pp, _op = fight_rows(log)
    if z is None:
        return {"zone": None}
    js = sorted(r["j_hi"] for r in prompts if r.get("j_hi") is not None)
    gone = []
    for r in prompts:
        if r.get("gone_frame") is not None and r.get("down_frame") is not None and r.get("rate"):
            gone.append(SD.rate_of(r["rate"]).ticks_most(max(0, r["gone_frame"] - r["down_frame"])))
    forms = sorted({re.sub(r"\[(DBTN|MOBI)=[^\]]*\]", lambda m: f"[{m.group(1)}=*]", p)
                    for r in prompts for p in ((r.get("published") or {}).get("phrase_raw") or ()) if SD.prompt_dbtn(p)})
    return {"zone": {"instances": z.get("instances"), "presses": z.get("presses"), "first_prompt": z.get("first_prompt"),
                     "j_hi": [js[0], statistics.median(js), js[-1]] if js else None, "raw": z.get("raw"),
                     "regimes": sorted({r.get("regime") for r in prompts if r.get("regime")}),
                     "samples": z.get("samples"), "max_read_gap": z.get("max_read_gap"),
                     "evidence": dict(Counter(r.get("evidence") for r in prompts)),
                     "gone_ticks_median": statistics.median(gone) if gone else None, "slides": z.get("slides"),
                     "input": z.get("input"), "forms": forms, "judge": (z.get("judge") or {}).get("v"),
                     "v": z.get("v"), "why": z.get("why"), "start_page": z.get("start_page")}}


# ======================================================================== O4 on the shared engine
class O4Segment(P.O3Segment):
    """O4 on O3's segment (research/o4_design.md 1.3): its constants and check texts, the draft predictions, the
    offline checks (O4-BUILD with the fork-gate pins, O4-KEYS with the fight pins, O4-TEXT strict on blocks 2 and 3,
    O4-CENSUS with the proven inert functions), the preflight extras (P-TEXT x2, P-RECOVERY, P-DONOR, P-SETTINGS,
    P-PAD, P-OVERRIDE, P-ENGINE, P-GATE) and in-game capabilities (P-CAP, P-OBJECTS, P-LANG, P-DONOR-LOG, P-LAUNCH with
    the engine, P-PAD), the drive with its input witness, the all-run checks (FORBIDDEN, VOID-ASYM (a)-(d)), the core
    checks (START, LADDER, CHAIN, RESIDUE, WRITES exact, NULL, STABLE, LANDING (a)-(e), SWORD (a)-(f), MASKED, STATE,
    JOIN) and O4's report. The session loop, the cuts (at the side's end PLACES, S6), the digest, the comparison and the
    verdict are the shared engine's."""

    tag = "O4"
    doc = _MODULE_DOC
    predictions = PREDICTIONS
    manifest = MANIFEST
    session_file = SESSION_FILE
    report_file = REPORT_FILE
    chain_dir = CHAIN_DIR
    build_dir = BUILD_DIR
    accept_us_build = False               # today's kit: every member's other languages are its own donor's (0.1 #3)
    recovery = 4600
    end_session_warps = True              # S5: a last run stopped mid-fight must not leave the game there
    core_ids = ("START", "LADDER", "CHAIN", "RESIDUE", "WRITES", "NULL", "STABLE", "LANDING", "SWORD", "MASKED",
                "STATE", "JOIN")
    titles = {
        "P-CAP": "P-CAP: the engine advertises the story trace at proto 1",
        "P-OBJECTS": "P-OBJECTS: the engine publishes the field's objects (s89): the slides read Blank's (sid 20)",
        "P-LANG": "P-LANG: the running game's text is English(US), the language the keys, joins and text were checked "
                  "in (a US session)",
        "P-DONOR-LOG": "P-DONOR-LOG: this launch's Memoria.log shows the patchers ran and logged no ForkDonorPatch "
                       "collision for 64, 150 or 153",
        "P-LAUNCH": "P-LAUNCH: every stacked patch file, Memoria.ini and the engine DLLs are older than this launch, "
                    "and the DLLs are the pinned engine",
        "P-MANIFEST": "P-MANIFEST: the frozen members are the deployed chain's (o4_forks.json, deployed)",
        "P-DEPLOY": "P-DEPLOY: every member registered once under its name, and mapped once to its donor",
        "P-EB": "P-EB: every member's live .eb (7 languages) is the offline-checked build's",
        "P-FLOOR": "P-FLOOR: every member's deployed walkmesh is its donor's",
        "P-STOCK": "P-STOCK: no mod folder overrides stock 64, 150 or 153",
        "P-TEXT2": "P-TEXT (block 2): every mod folder's text block 2 is each language's stock asset (before O4's "
                   "deploy O1's named uk copy is tolerated; after it, strict)",
        "P-TEXT3": "P-TEXT (block 3): every mod folder's text block 3 is each language's stock asset (strict)",
        "P-RECOVERY": "P-RECOVERY: the recovery field 4600 is registered in a mod folder",
        "P-DONOR": "P-DONOR: each of 64, 150 and 153 is forked by exactly one ForkDonorPatch row in the stack, its "
                   "member's",
        "P-SETTINGS": "P-SETTINGS: the battle, cheat, hack, control and graphics settings are the frozen ones "
                      "(SwordplayAssistance 1, FieldTPS 30, AlwaysCaptureGamepad 1; Memoria.ini read the engine's way)",
        "P-PAD": "P-PAD: no XInput pad reads non-neutral (AlwaysCaptureGamepad = 1 reads a pad even unfocused)",
        "P-OVERRIDE": "P-OVERRIDE: field 70's New-Game override is the pinned one, shipped by one folder",
        "P-ENGINE": "P-ENGINE: the live x64 and x86 Assembly-CSharp.dll are the pinned engine",
        "P-GATE": "P-GATE: R-GATE witnessed the +30% on member(64) (or found it BROKEN by the bonus) on this engine "
                  "and these settings",
        "BUILD": "O4-BUILD: every member's .eb, in all 7 languages, is its donor's in that language with only in-chain "
                 "Field() literals remapped; per language, member(64)'s e4 t1 score-to-store bytes are the donor's and "
                 "the route members differ from their donors in exactly their in-chain Field() operands",
        "KEYS": "O4-KEYS: every registered key -- ladder, chain, writes, error path, forbidden and dead sites, "
                "start_first -- is a store of its variable at its ip in the donor's stock bytes, its op in the "
                "statement, its value computed (the score's :=var key in its statement); and the 56 fight pins",
        "TEXT": "O4-TEXT: the build's text blocks 2 and 3 are each language's stock asset, read by its resource path "
                "-- STRICT: another language's copy fails",
        "CENSUS": "O4-CENSUS: every gEventGlobal store site of 64 and 150 is registered (writes, ladder, chain, masked, "
                  "start_first, error path, forbidden, dead) or lies in an inert function, proven not instanced at "
                  "its entrance",
        "FROZEN": "O4-FROZEN: the predictions are the file the session recorded, unchanged",
        "COVER": "O4-COVER: at least {min_covered} covered runs a side",
        "FORBIDDEN": "O4-FORBIDDEN: no run carries a forbidden write its own driver log does not explain",
        "VOID-ASYM": "O4-VOID-ASYM: no game-caused VOID class on one side only, no side VOID in one class in every run, "
                     "no run VOID in a finding class (V18, V19), and no game-observed V17 cause on one side only",
        "START": "O4-START: every covered run starts at 64's Main_Init after only the warp's own residue, and 64 takes "
                 "its ambient branch from the warp's Byte[13] 1",
        "LADDER": "O4-LADDER: bytes 0-1 (SC) carry exactly the one rung 1155 -> 1190 (150 e3 t1 ip1966)",
        "CHAIN": "O4-CHAIN: bytes 2-3 (FieldEntrance) carry exactly the chain, in order, each from the last",
        "RESIDUE": "O4-RESIDUE: no unmasked residue after the start beyond the registered",
        "WRITES": "O4-WRITES: every covered run's story keys are EXACTLY the registered writes, chain and ladder",
        "NULL": "O4-NULL: STOCK ONLY and FORK ONLY are empty",
        "STABLE": "O4-STABLE: no key is written in some runs of a side and not others",
        "LANDING": "O4-LANDING: every row ran in its place's own field, 150 loaded by 64's Field(150), 150 is the last "
                   "place, the end cut is 153's first row at the side's own end field, and no fork run left its "
                   "members",
        "SWORD": "O4-SWORD: the displayed 100/100 -- one ip338 Byte[475] 0 -> 100 and one ip390 Bit[3815] 0 -> 1, "
                 "pages 122 then 123, the encore answered No once, the gil page, the fight proven the frozen play "
                 "(49 proper presses, every window closed on its press) and no stray press in the fight",
        "MASKED": "O4-MASKED: the story-noise regions written are the same on both sides",
        "STATE": "O4-STATE: the state handed to 153 is the same: each target's emitted write history in order (its "
                 "suppressed stores as a set), and the end state read live",
        "JOIN": "O4-JOIN: every script row joins a store in the bytes its field ran",
        "THROW": "O4-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
    }

    # -- the predictions --------------------------------------------------------------------------------------
    def draft(self) -> dict:
        return draft_predictions(Path(self.chain_dir) / "campaign.toml")

    def freeze(self, path=None, *, live_engine=None) -> str:
        """The freeze, once (research/o4_design.md 1.3, 7.3): before anything is written the draft's policy passes
        :func:`segment_drive.chanbara_of` and is ``fast`` with no ``pace`` and no ``stop_after`` (those are R-GATE's and
        R-CHANBARA-VOID's); its ``side_ends`` pass :func:`segment_trace.side_ends_of`; ``battles`` is empty; and its
        ``engine`` is the live DLLs' (``live_engine``, default :func:`engine_shas`: the rehearsals' engine). Then the
        base's: LF, sorted keys, never over an existing file."""
        pred = self.draft()
        bad = []
        try:
            pol = SD.chanbara_of(pred)
        except ValueError as err:                  # a policy the strict reader refuses (a pace under fast...)
            pol = False
            bad.append(str(err))
        if pol is None:
            bad.append("no chanbara policy")
        elif pol:
            if pol["policy"] != "fast":
                bad.append(f"the policy is {pol['policy']!r}: the frozen session plays fast (paced is R-GATE's)")
            if "pace" in pol:
                bad.append("a pace: R-GATE's alone (2.4.10)")
            if "stop_after" in pol:
                bad.append("a stop_after: R-CHANBARA-VOID's alone")
        try:
            if ST.side_ends_of(pred) is None:
                bad.append("no side_ends: O4's F side ends in member(153)")
        except ValueError as err:
            bad.append(str(err))
        if pred.get("battles"):
            bad.append(f"{len(pred['battles'])} battle row(s): O4's registry is empty (any battle is V10)")
        live = live_engine if live_engine is not None else engine_shas(GAME)
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
        return [self.text_check(pred, build), self.census_check(pred, stock)]

    def build_check(self, pred: dict, build=None, stock_lang=None) -> tuple:
        """O4-BUILD (6.1): the base's rule (every member's .eb, every language its own donor's with only in-chain
        Field() literals remapped), then THE FORK-GATE PINS per language (critique minor #11; :meth:`build_pins`)."""
        stock_lang = stock_lang or ST.stock_lang()
        ok, what, detail = super().build_check(pred, build, stock_lang)
        pok, pdetail = self.build_pins(pred, build, stock_lang)
        if not (ok and pok):
            return False, what, "; ".join(d for good, d in ((ok, detail), (pok, pdetail)) if not good)
        members = members_of(pred)
        line = route_members_line(members) if all(d in members.values() for d in ROUTE_DONORS) else ""
        return True, what, f"{detail}; {pdetail}" + (f"; {line}" if line else "")

    def build_pins(self, pred: dict, build=None, stock_lang=None) -> tuple:
        """THE FORK-GATE PINS (6.1), per language, each language's script decoded on its own: (1) member(64)'s e4 t1
        bytes from the score statement through the Byte[475] store's whole instruction are byte-equal to its donor's AT
        THE SAME offsets, and the hook's statement (EMinigame fires at its first token, sid 4 ip 223) sits at e4 t1
        ``hook_ip``; (2) every byte in which a route member (64, 150) differs from its donor lies in the operand of one
        of its in-chain ``Field()`` instructions -- exactly the registered sites ``fight.build.fields`` (US ips; their
        literal a chain donor, retargeted to that donor's member) -- and every such operand differs: no other byte
        (a PreloadField operand, the hook's ip) moves. ``(ok, detail)``."""
        from ff9mapkit.config import LANGS, ModLayout
        from ff9mapkit.eb import EbScript
        from ff9mapkit.eventscan import FIELD_OP
        stock_lang = stock_lang or ST.stock_lang()
        spec = (pred.get("fight") or {}).get("build") or {}
        members, names = members_of(pred), {int(f): n for f, n in pred["names"].items()}
        retarget = {d: f for f, d in members.items()}
        lay = ModLayout(Path(build or self.build_dir))
        bad, n = [], 0
        sc = spec.get("score") or {}
        for donor_s, sites in sorted((spec.get("fields") or {}).items()):
            donor = int(donor_s)
            fid = next((f for f, d in sorted(members.items()) if d == donor), None)
            if fid is None:
                bad.append(f"no member forks {donor}")
                continue
            want = sorted(tuple(int(v) for v in s) for s in sites)
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
                if donor == int(sc.get("donor", -1)):
                    bad += [f"{fid} ({donor}) {L}: {p_}" for p_ in self._score_pin(src, built, sc)]
        return not bad, ("; ".join(bad[:6]) if bad else
                         f"the fork-gate pins hold in {n} member files (2 route members x 7 languages): member(64)'s e4 "
                         f"t1 score-to-store bytes its donor's and the hook at ip{sc.get('hook_ip')}; the only byte "
                         f"diffs the six in-chain Field() operands")

    @staticmethod
    def _score_pin(src: bytes, built: bytes, sc: dict) -> list:
        """The score pin of one language: the e4 t1 range from the instruction reading ``from`` through the end of the
        one reading ``through`` -- byte-equal in ``built`` and ``src`` -- and ``hook`` at ip ``hook_ip``."""
        idx = T.ScriptIndex(src, label="donor")
        items = A.O2Segment._items(idx, int(sc["sid"]), int(sc["tag"]))
        fa = idx.function(int(sc["sid"]), int(sc["tag"]))
        if fa is None or not items:
            return [f"e{sc['sid']} t{sc['tag']} does not decode"]
        e, _f, start, end = fa
        a = next((i for i, (_ip, _rel, t) in enumerate(items) if t == sc["from"]), None)
        b = next((i for i, (_ip, _rel, t) in enumerate(items) if t == sc["through"]), None)
        if a is None or b is None or b < a:
            return [f"e{sc['sid']} t{sc['tag']} holds no score ({a}) / store ({b}) instruction in order"]
        lo = e.abs_start + items[a][0]
        hi = (e.abs_start + items[b + 1][0]) if b + 1 < len(items) else end
        out = []
        if built[lo:hi] != src[lo:hi]:
            out.append(f"e{sc['sid']} t{sc['tag']} ip{items[a][0]}-ip{items[b][0]}: the score-to-store bytes differ from "
                       f"the donor's")
        hook = next((ip for ip, _rel, t in items if t == sc["hook"]), None)
        if hook != int(sc["hook_ip"]):
            out.append(f"the hook's statement sits at ip{hook}, not ip{sc['hook_ip']} (EMinigame's sid 4 ip 223)")
        return out

    def keys_check(self, pred: dict, stock, lists=None) -> tuple:
        """O4-KEYS (6.1): (a) O2's machinery on a filtered copy -- the ladder, the chain, the writes but the score's
        ``:=var`` key, ``forbidden_sites`` + ``error_path`` + ``dead``, ``start_first``; no noise, no start-dependent
        keys -- then the ``:=var`` key itself (its joined store's statement ``<target> Map.Int16[48] B_LET``: its value
        100 rests on the clamp pin and O4-SWORD (a), never computed here) and ``start_music`` as exactly one writes key
        (O3's); (b) THE FIGHT PINS (4.14): every pin's instruction text EXACTLY the stock US script's, ``prompt_mes``
        each its DBTN by :func:`segment_drive.prompt_dbtn` on block 2's US source, mes 111 a zone start, and the three
        page sources holding their texts. A ``:=var`` key names its ``rvalue`` (the variable its store takes), read
        from the key, never assumed: a key without one FAILS."""
        var = [k for k in pred["writes"] if k.get("op") == ":=var"]
        filtered = {**pred, "writes": [k for k in pred["writes"] if k.get("op") != ":=var"], "start_dependent": [],
                    "noise": [], "forbidden_sites": (list(pred["forbidden_sites"]) + list(pred["error_path"])
                                                     + list(pred["dead"]))}
        ok, what, detail = A.O2Segment.keys_check(self, filtered, stock)
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
        fok, fdetail = self.fight_pins_check(pred, stock)
        if not fok:
            bad.append(fdetail)
        if bad:
            return False, self.title("KEYS"), "; ".join(bad)[:1200]
        return (True, self.title("KEYS"),
                detail.replace("O2-START", "O4-START") + "; the score's :=var key ("
                + ", ".join(f"{k['donor']} e{k['sid']} t{k['tag']} ip{k['ip']}, rvalue {k['rvalue']}" for k in var)
                + f") in its statement; start_music one writes key; {fdetail}")

    def fight_pins_check(self, pred: dict, stock, *, mes=None) -> tuple:
        """O4-KEYS (b), the fight pins (4.14): ``(ok, detail)``. ``mes`` (``{mes id: source}``, block 2's US) replaces
        the install read -- a seam for the dry run."""
        fight = pred.get("fight") or {}
        bad, n = [], 0
        cache: dict = {}
        for donor, sid, tag, ip, text in fight.get("pins") or ():
            n += 1
            idx = stock(donor)
            if idx is None:
                bad.append(f"{donor}: no stock script")
                continue
            items = cache.setdefault((donor, sid, tag), {i: t for i, _rel, t in A.O2Segment._items(idx, sid, tag)})
            got = items.get(ip)
            if got != text:
                bad.append(f"{donor} e{sid} t{tag} ip{ip}: {got!r}, pinned {text!r}")
        if mes is None:
            from ff9mapkit import dialogue
            body = A.stock_text_assets(int(pred.get("text_block", TEXT_BLOCK)))[SESSION_LANG]
            body = body.decode("utf-8", errors="replace") if isinstance(body, (bytes, bytearray)) else str(body)
            mes = {i: x.text for i, x in dialogue.parse_mes(body).items()}
        pol = pred.get("chanbara") or POLICY
        for m, want in sorted((fight.get("prompt_mes") or {}).items()):
            got = SD.prompt_dbtn(mes.get(int(m)))
            if got != want:
                bad.append(f"mes {m}: prompt_dbtn reads {got!r}, pinned {want!r}")
        zs = fight.get("zone_start_mes")
        if zs is not None and not SD.is_zone_start([mes.get(int(zs))], pol):
            bad.append(f"mes {zs} is no zone start ({pol['zone_start']})")
        for m, text in sorted((fight.get("page_sources") or {}).items()):
            if text not in str(mes.get(int(m)) or ""):
                bad.append(f"mes {m}'s source does not hold {text!r}")
        return (not bad, "; ".join(bad[:6]) if bad else
                f"{n} fight pins equal, prompt_mes 112-119 each its DBTN, mes {zs} a zone start, the three page "
                f"sources as pinned")

    def text_check(self, pred: dict, build=None, stock_text=None) -> tuple:
        """O4-TEXT (6.1; rev. 2, the claim critique #12): O2's :func:`o2_alexandria.text_rule` on block 2 AND block 3
        against the O4 build, each language against the asset the engine reads -- STRICT (:func:`strict_text`): a
        KNOWN-KIT-DEFECT line FAILS too. The build must ship every language of both. ``stock_text``: ``{block: {lang:
        bytes}}`` (a seam)."""
        from ff9mapkit import config
        ok_all, lines_all, parts = True, [], []
        for block in pred.get("text_blocks") or [pred.get("text_block", TEXT_BLOCK)]:
            stock = (stock_text or {}).get(block) if stock_text is not None else A.stock_text_assets(block)
            shipped = A.shipped_text(build or self.build_dir, block)
            _ok, lines = A.text_rule(stock, shipped, pred.get("lang", SESSION_LANG))
            lines += [f"FAIL {L}: the build ships no {L}/field/{block}.mes" for L in config.LANGS if L not in shipped]
            ok, _d = strict_text(lines)
            ok_all = ok_all and ok
            lines_all += lines
            equal = sum(1 for ln in lines if " ok: " in ln)
            parts.append(f"block {block}: {equal} byte-equal of {len(lines)}")
        defects = [ln for ln in lines_all if ln.startswith("KNOWN-KIT-DEFECT")]
        fails = [ln for ln in lines_all if ln.startswith("FAIL")]
        head = "; ".join(parts) + f"; KNOWN-KIT-DEFECT {len(defects)}, FAIL {len(fails)}"
        return ok_all, self.title("TEXT"), " | ".join([head, *fails, *defects])

    def census_check(self, pred: dict, stock, *, sites=None, classify=None) -> tuple:
        """O4-CENSUS (6.1): :func:`store_census` over the route's stock fields -- every site classified, the inert
        functions proven not instanced at the route's entrance, or each failure named."""
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
        inert = sorted({int(x["sid"]) for x in pred.get("inert") or ()})
        ents = sorted({v["entrance"] for v in proof.values()})
        return (True, self.title("CENSUS"),
                ", ".join(f"{f}: {tot[f]}" for f in fields) + f" store sites -- all classified ({cols}); {unres} "
                f"unresolved; inert {', '.join(map(str, inert))} not instanced at {', '.join(map(str, ents))}")

    # -- the live install (read-only) ---------------------------------------------------------------------------
    def o4_registered(self, pred: dict, roots) -> bool:
        """Whether any O4 member is registered in a stacked folder (the deploy began)."""
        members = set(members_of(pred))
        return any(members & set(T.mod_registrations(r)) for r in roots)

    def preflight_extra(self, pred: dict, roots: list, *, manifest=None, pads=..., live_engine=None) -> list:
        """6.2's extras, in order: P-TEXT (block 2), P-TEXT (block 3) (:func:`p_text`), P-RECOVERY, P-DONOR (64, 150 and
        153), P-SETTINGS, P-PAD, P-OVERRIDE, P-ENGINE, P-GATE. ``manifest`` (o4_forks.json's dict), ``pads`` (P-PAD's
        reader) and ``live_engine`` are seams."""
        try:
            man = manifest if manifest is not None else json.loads(Path(self.manifest).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            man = {}
        o1 = (man.get("text_effects") or {}).get("o1_block2")
        registered = self.o4_registered(pred, roots)
        out = []
        for block, cid in ((2, "P-TEXT2"), (3, "P-TEXT3")):
            found = [(Path(r).name, A.shipped_text(r, block)) for r in roots]
            found = [(nm, s) for nm, s in found if s]
            stock = A.stock_text_assets(block) if found else {}
            ok, detail = p_text(block, found, stock, o1_block2=o1, o4_registered=registered,
                                lang=pred.get("lang", SESSION_LANG))
            out.append((ok, self.title(cid), detail))
        rec = int(pred.get("recovery", self.recovery))
        hits = [Path(r).name for r in roots if rec in T.mod_registrations(r)]
        out.append((bool(hits), self.title("P-RECOVERY"),
                    f"{rec} registered in {', '.join(hits)}" if hits else f"{rec} is registered in no mod folder"))
        ok, detail = P.p_donor({**pred, "route": list(pred["route"]) + list(pred.get("end_fields") or [])}, roots)
        out.append((ok, self.title("P-DONOR"), detail))
        want = pred.get("settings") or SETTINGS
        ok, detail = P.p_settings(want, P.install_settings(GAME, roots, want))
        out.append((ok, self.title("P-SETTINGS"), detail))
        ok, detail = p_pad(xinput_slots(pads))
        out.append((ok, self.title("P-PAD"), detail))
        ok, detail = p_override(override70_of(roots), pred.get("override70") or OVERRIDE70)
        out.append((ok, self.title("P-OVERRIDE"), detail))
        live = live_engine if live_engine is not None else engine_shas(GAME)
        ok, detail = p_engine(live, pred.get("engine") or ENGINE)
        out.append((ok, self.title("P-ENGINE"), detail))
        ok, detail = p_gate(man, live, want, pinned_engine=pred.get("engine") or ENGINE,
                            member64=self.member64(pred))
        out.append((ok, self.title("P-GATE"), detail))
        return out

    def member64(self, pred: dict, build=None) -> dict | None:
        """The session's member(64) as P-GATE ties R-GATE's witness to it (the review, 11.5 #4): ``{"id", "name",
        "eb"}`` -- its id DERIVED from the chain (:func:`route_members`), its .eb's sha256 per language in the
        offline-checked build (P-EB pins the live files to it); None when the predictions name no single member(64)."""
        try:
            fid = route_members(members_of(pred))[64]
            name = pred["names"][str(fid)]
        except (AssertionError, KeyError):
            return None
        return {"id": fid, "name": name, "eb": member_eb(Path(build or self.build_dir), name)}

    def fingerprint_extra(self, roots: list, pred: dict) -> dict:
        """6.3: O3's (field 70's override, block 2's text per folder, the language, the settings, the battle data), then
        ``text3`` (block 3 per folder per language) and ``engine`` (rev. 2: the x64 and x86 DLLs' sha256) -- an engine
        rebuild mid-session (it auto-deploys) is A-INSTALL."""
        out = super().fingerprint_extra(roots, pred)
        text3 = {}
        for r in roots:
            t = {L: _sha(b) for L, b in A.shipped_text(r, 3).items()}
            if t:
                text3[Path(r).name] = t
        out["text3"] = text3
        out["engine"] = engine_shas(GAME)
        return out

    # -- the session --------------------------------------------------------------------------------------------
    def capabilities(self, g, *, pads=..., engine=None, live_engine=None) -> list:
        """O2's (P-CAP, P-OBJECTS, P-LANG), then P-DONOR-LOG for 64, 150 and 153, P-LAUNCH (every stacked patch file,
        Memoria.ini and -- rev. 2 -- the x64 and x86 engine DLLs older than the launch's first log stamp, the DLLs the
        pinned engine) and P-PAD re-sampled on this launch. ``pads`` (P-PAD's reader), ``engine`` (the pinned DLLs'
        shas, default :data:`ENGINE`) and ``live_engine`` (default the live DLLs') are seams for the fake."""
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
        ok, detail = launch_engine_check(P.launch_files(game, roots), engine_files(game), P.launch_time(text),
                                         live_engine if live_engine is not None else engine_shas(game),
                                         engine or ENGINE)
        out.append((ok, self.title("P-LAUNCH"), detail))
        ok, detail = p_pad(xinput_slots(pads))
        out.append((ok, self.title("P-PAD"), detail))
        return out

    def drive(self, g, pred: dict, side: str, log: list, *, deadline: float, progress: dict | None = None) -> dict:
        """The base's drive, plus the input witness (2.4.3 step 0; rev. 2): outside input anywhere in the run is V13."""
        return SD.drive(g, pred, side, log, deadline=deadline, progress=progress, witness=input_witness(g))

    # -- the checks ---------------------------------------------------------------------------------------------
    def void_asym_check(self, runs: list, pred: dict) -> tuple:
        """O4-VOID-ASYM (5.3): O2's (a) -- a game-attributed class (with its cell) on one side only -- and (b) -- every
        run of one side VOID in one class while the other has ``min_covered`` covered; (c) any run of either side VOID
        in a FINDING class (``rerun.stop_on``: V18, V19) -- a finding is never a VOID, whichever side holds it; (d)
        (rev. 2, the claim critique #5) a GAME-OBSERVED V17 cause on one side only: the uncovered runs' ``observed``
        rows, keyed ``(kind, cell)``, held by some run of one side and by no run of the other."""
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
        stop_on = set((pred.get("rerun") or {}).get("stop_on") or ())
        for r in runs:
            for c, cell, by in sorted(self._void_ids(r), key=str):
                if c in stop_on:
                    bad.append(f"(c) {r['side']}#{r['i']} VOID {c}{'' if cell is None else f' at {list(cell)}'} ({by}): "
                               f"a finding class, never a VOID")
        obs = {s: {} for s in SIDES}
        for r in runs:
            if r["covered"]:
                continue
            for x in r.get("log") or ():
                if x.get("k") == "observed":
                    k = (x.get("kind"), tuple(x["cell"]) if x.get("cell") else None)
                    obs[r["side"]].setdefault(k, []).append(f"{r['side']}#{r['i']}")
        for s, o in (("S", "F"), ("F", "S")):
            for (kind, cell), where in sorted(obs[s].items(), key=str):
                if (kind, cell) not in obs[o]:
                    bad.append(f"(d) the game showed {kind}{'' if cell is None else f' at {list(cell)}'} (V17, "
                               f"game-observed) on {s} only: {', '.join(where)}")
        seen = {s: sorted({f"{c}{'' if cell is None else list(cell)}:{by}" for ids in per[s] for c, cell, by in ids})
                for s in SIDES}
        nobs = {s: sorted(f"{k}{'' if c is None else list(c)}" for k, c in obs[s]) for s in SIDES}
        return (not bad, self.title("VOID-ASYM"),
                "; ".join(bad[:6]) if bad else f"S {seen['S'] or 'none'}; F {seen['F'] or 'none'}; observed S "
                                               f"{nobs['S'] or 'none'}, F {nobs['F'] or 'none'}")

    def core_checks(self, runs: list, cov: dict, pred: dict) -> list:
        covered = cov["S"] + cov["F"]
        c = self.comparison(cov, pred)
        return [self.start_check(covered, pred),
                self.span_check("LADDER", covered, pred, "sc_bytes", "ladder", pred["scenario"]),
                self.span_check("CHAIN", covered, pred, "entrance_bytes", "chain", pred["entrance"]),
                self.residue_check(covered, pred), self.writes_check(covered, pred), self.null_check(c, pred),
                self.stable_check(c, pred), self.landing_check(cov, pred), self.sword_check(covered, pred),
                self.masked_check(cov, pred), self.state_check(covered, pred), self.join_check(cov)]

    def writes_check(self, covered: list, pred: dict) -> tuple:
        """O4-WRITES, EXACT (4.4, 5.3): every covered run's keys ARE the writes, the chain and the ladder -- a missing
        key and an extra one (a dead branch firing, an inert function's store, an error path, a C# write) each fail by
        name. Exactness rests on O4-CENSUS and O4-KEYS."""
        reg = list(pred["writes"]) + list(pred["chain"]) + list(pred.get("ladder") or ())
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
                "; ".join(bad[:6]) or f"{len(covered)} runs x exactly {len(want)} keys ({len(pred['writes'])} writes + "
                                      f"{len(pred['chain'])} chain + {len(pred.get('ladder') or ())} ladder)")

    def landing_check(self, cov: dict, pred: dict) -> tuple:
        """O4-LANDING (5.3; decision 4), over every covered run, each clause named in the detail:
          (a) every field-mode ``w``/``c`` row ran in its place's own field (member(place) on F, the place on S), and
              none stands in a place off ``route_places`` [64, 150] (O3's clause);
          (b) the 64 -> 150 crossing, on ``w`` rows: the run holds ``landing.exit64`` (64 e2 t1 ip528); the next
              field-mode ``w`` row after it is ``landing.enter150`` (150 e0 t0 ip26) -- 150 loaded by 64's Field(150);
              no field-mode ``w`` row of place 64 after it -- each at its place's own field (member(place) on F): the
              crossing is the member's Field();
          (c) the last field-mode ``w`` row before the end cut is ``landing.exit150`` (150 e3 t1 ip2161), read by
              PLACE (which field the row ran in is (a)'s), and the run's ``end`` log row names the side's end field
              (153 on S, member(153) on F: ``side_ends``);
          (d) THE END PER SIDE: the end cut (``cut_row``) is a raw ``w`` row that is ``landing.end_row`` (153 e0 t0
              ip22) at ``fld`` the side's end field -- a real-153 cut row on F fails here;
          (e) every F digest records no seam and no seam key (the chain is closed from member(64) to member(153))."""
        L = pred["landing"]
        ex64, en150, ex150, lend = L["exit64"], L["enter150"], L["exit150"], L["end_row"]
        route = set(L["route_places"])
        fm = T.FIELD_MODE
        bad = []

        def is_at(x, spec, members) -> bool:
            return (x.k == "w" and x.m == fm and place(x.fld, members) == spec["place"]
                    and (x.sid, x.tag, x.ip, x.target, x.new) == (spec["sid"], spec["tag"], spec["ip"], spec["target"],
                                                                   spec["value"]))
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
            i = next((j for j, x in enumerate(ws) if is_at(x, ex64, members) and x.fld == fld_of(ex64["place"])), None)
            if i is None:
                bad.append(f"{lab} (b): no landing.exit64 row ({ex64['place']} e{ex64['sid']} t{ex64['tag']} "
                           f"ip{ex64['ip']} {ex64['target']}={ex64['value']} at fld {fld_of(ex64['place'])})")
            else:
                later = [x for x in ws[i + 1:] if x.m == fm]
                nxt = later[0] if later else None
                if nxt is None or not (is_at(nxt, en150, members) and nxt.fld == fld_of(en150["place"])):
                    bad.append(f"{lab} (b): the next field row after 64 ip{ex64['ip']} is "
                               f"{A._row_text(nxt) if nxt is not None else 'none'}, not landing.enter150 "
                               f"({en150['place']} e{en150['sid']} t{en150['tag']} ip{en150['ip']} at fld "
                               f"{fld_of(en150['place'])}: 150 loaded by 64's Field(150))")
                j = next((n for n, x in enumerate(later) if is_at(x, en150, members)), None)
                back = None if j is None else next((x for x in later[j + 1:] if place(x.fld, members) == ex64["place"]),
                                                   None)
                if back is not None:
                    bad.append(f"{lab} (b): line {back.line} {A._row_text(back)}: place {ex64['place']} written again "
                               f"after 150 loaded")
            fws = [x for x in ws if x.m == fm]
            last = fws[-1] if fws else None
            if last is None or not is_at(last, ex150, members):          # by PLACE: the row's own field is (a)'s
                bad.append(f"{lab} (c): the last field row before the end cut is "
                           f"{A._row_text(last) if last is not None else 'none'}, not landing.exit150 "
                           f"({ex150['place']} e{ex150['sid']} t{ex150['tag']} ip{ex150['ip']})")
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
                bad.append(f"{lab} (d): the end cut (line {r.get('cut')}) is {desc}, not landing.end_row "
                           f"({lend['place']} e{lend['sid']} t{lend['tag']} ip{lend['ip']} {lend['target']}="
                           f"{lend['value']}) at the side's end field {want_end}")
            if r["side"] == "F":
                d = r["digest"]
                if d.seams or d.seam_keys:
                    bad.append(f"{lab} (e): {len(d.seams)} seam crossing(s) "
                               + ", ".join(f"{s.origin} -> {s.to}" for s in d.seams[:3])
                               + f", {len(d.seam_keys)} seam key(s): the chain must be closed")
        return (not bad, self.title("LANDING"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) every field row in its place's own field; (b) 64 "
                                      f"ip{ex64['ip']} -> 150 e0 t0 ip{en150['ip']}, 64 never resumed; (c) 150 "
                                      f"ip{ex150['ip']} last, the end row the side's own; (d) the cut at 153 e0 t0 "
                                      f"ip{lend['ip']} (S 153, F {ST.side_ends(pred, 'F')}); (e) no seam")

    def sword_check(self, covered: list, pred: dict) -> tuple:
        """O4-SWORD (5.3; the 100 plan item 6), over every covered run, each clause named:
          (a) exactly ONE raw ``w`` row of ``sword.score`` (64 e4 t1 ip338 Byte[475], old 0, new 100) and exactly ONE
              of ``sword.combo`` (ip390 Bit[3815], old 0, new 1), each at fld member(64) on F / 64 on S, the score
              row before the combo row;
          (b) the transcript holds ``score_page`` then 123's text in order, and no page holding a combo-page marker;
          (c) exactly one ``choice`` row whose options hold ``encore_match``, answered absolute 1 by the encore rule;
          (d) the transcript holds ``gil_page`` exactly once, after that choice: the press row holding it decided on a
              sample after the choice row's frame (the transcript has no frames; a gil page no press row holds cannot
              be placed: fail-closed);
          (e) :func:`segment_drive.chanbara_judge` over the run's zone, prompt rows and their presses reads None, 49
              prompt rows, every evidence "closed", no measured slide not ok, the zone's ``input`` empty;
          (f) no press row other than the prompts' whose down frame lies AT OR AFTER the first prompt's ``prev_frame``
              and before the zone end (one with no down frame is read by its decision sample: fail-closed).
        The trace cannot say which presses made the score (Map variables): (e)/(f) re-read the driver's own record."""
        sw, pol = pred["sword"], pred["chanbara"]
        sc_, cb_ = sw["score"], sw["combo"]
        choices = pred.get("choices") or []
        enc_n = next((n for n, c in enumerate(choices) if c.get("match") == pol["encore_match"]), None)
        bad = []
        for r in covered:
            lab = f"{r['side']}#{r['i']}"
            members = members_of(pred) if r["side"] == "F" else {}
            inv = {d: f for f, d in sorted(members.items(), reverse=True)}
            fld64 = inv.get(sc_["place"], sc_["place"]) if members else sc_["place"]
            rows, log, out = r["rows"], r.get("log") or [], r.get("outcome") or {}

            def at(spec):
                return [x for x in rows if x.k == "w" and place(x.fld, members) == spec["place"]
                        and (x.sid, x.tag, x.ip, x.target) == (spec["sid"], spec["tag"], spec["ip"], spec["target"])]
            s_rows, c_rows = at(sc_), at(cb_)
            for name, spec, hits in (("score", sc_, s_rows), ("combo", cb_, c_rows)):
                if len(hits) != 1 or (hits[0].fld, hits[0].old, hits[0].new) != (fld64, spec["old"], spec["value"]):
                    bad.append(f"{lab} (a): {len(hits)} {name} row(s) "
                               + ", ".join(f"{x.fld} {x.old}->{x.new}" for x in hits[:3])
                               + f", want one {fld64} {spec['old']}->{spec['value']} ({spec['target']} e{spec['sid']} "
                                 f"t{spec['tag']} ip{spec['ip']})")
            if len(s_rows) == 1 and len(c_rows) == 1 and not s_rows[0].line < c_rows[0].line:
                bad.append(f"{lab} (a): the combo row (line {c_rows[0].line}) precedes the score row "
                           f"(line {s_rows[0].line})")
            pages = list(out.get("pages") or [])
            i122 = next((i for i, p in enumerate(pages) if p == pol["score_page"]), None)
            i123 = next((i for i, p in enumerate(pages) if p == sw["page_123"] and (i122 is None or i > i122)), None)
            combo = [p for p in pages if any(m in p for m in sw["combo_marks"])]
            if i122 is None or i123 is None or combo:
                bad.append(f"{lab} (b): " + (f"a combo page {combo[0][:40]!r}" if combo else
                                             f"no score page then 123 (score page at {i122}, 123 at {i123})"))
            enc = [c for c in log if c.get("k") == "choice"
                   and any(pol["encore_match"] in str(o or "") for o in (c.get("options") or ()))]
            if len(enc) != 1 or enc[0].get("index") != 1 or enc[0].get("rule") != enc_n:
                bad.append(f"{lab} (c): {len(enc)} encore choice row(s)"
                           + (f", index {enc[0].get('index')} by rule {enc[0].get('rule')}" if enc else "")
                           + f", want one answered 1 (No) by rule {enc_n}")
            ngil = pages.count(pol["gil_page"])
            gpress = [p for p in log if p.get("k") == "press" and pol["gil_page"] in (p.get("texts") or ())]
            cf = enc[0].get("frame") if len(enc) == 1 else None          # (c) reads a missing or second choice
            gf = (gpress[0].get("pre") or {}).get("frame") if gpress else None
            late = cf is None or (gf is not None and gf > cf)
            if ngil != 1 or not late:
                bad.append(f"{lab} (d): the gil page {ngil} time(s) in the transcript"
                           + ("" if late else ", no press row holds it" if gf is None else
                              f", its press decided at frame {gf}, not after the encore choice's frame {cf}"))
            zone, prompts, ppress, other = fight_rows(log)
            if zone is None:
                bad.append(f"{lab} (e): no zone row: the fight was never driven by the policy")
                continue
            j = SD.chanbara_judge(zone, prompts, ppress, pol)
            notc = [p["n"] for p in prompts if p.get("evidence") != "closed"]
            slid = [p["n"] for p in prompts if isinstance(p.get("slide"), dict) and p["slide"].get("ok") is False]
            if j["v"] is not None or len(prompts) != int(pol["prompts"]) or notc or slid or zone.get("input"):
                bad.append(f"{lab} (e): " + "; ".join(x for x in (
                    f"the judge reads {j['v']} ({j['why']})" if j["v"] else "",
                    f"{len(prompts)} prompt rows" if len(prompts) != int(pol["prompts"]) else "",
                    f"evidence not closed at {notc[:4]}" if notc else "",
                    f"slides not ok at {slid[:4]}" if slid else "",
                    f"outside input {zone['input'][:1]}" if zone.get("input") else "") if x))
            first = prompts[0].get("prev_frame") if prompts else None
            endf = (zone.get("end") or {}).get("frame")
            for p in other:
                d = p.get("down_frame")
                d = d if d is not None else (p.get("pre") or {}).get("frame")
                if d is not None and first is not None and d >= first and (endf is None or d < endf):
                    bad.append(f"{lab} (f): a {p.get('why')} press (seq {p.get('seq')}) "
                               + ("went down" if p.get("down_frame") is not None else "was decided")
                               + f" at frame {d}, inside the fight [{first}, {endf})")
                    break
        return (not bad, self.title("SWORD"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) one ip338 0 -> 100 and one ip390 0 -> 1 each; (b) "
                                      f"122 then 123; (c) 127 answered No once; (d) the gil page once; (e) 49 proven "
                                      f"presses each; (f) no stray press in the fight")

    # -- the report ---------------------------------------------------------------------------------------------
    @staticmethod
    def _recorded(session: dict, prefix: str) -> list:
        return [(ok, what, detail) for ok, what, detail in session.get("preflight") or ()
                if str(what).startswith(prefix)]

    def scope_lang(self, session: dict) -> str:
        """5.4's language clause, DERIVED from the session's recorded P-TEXT rows (rev. 2, the claim critique #12):
        each block's byte-equal count, every recorded non-ok line quoted."""
        parts, odd = [], []
        for _ok, what, detail in self._recorded(session, "P-TEXT"):
            block = re.search(r"block (\d+)", str(what))
            eq = re.findall(r"(\d+) byte-equal of (\d+)", str(detail))
            parts.append(f"block {block.group(1) if block else '?'}: "
                         + (", ".join(f"{a} byte-equal of {b}" for a, b in eq) if eq else "none shipped"))
            odd += [seg for seg in str(detail).split(" | ") if seg.startswith(("FAIL", "KNOWN-KIT-DEFECT"))]
        if not parts:
            return "a US session (P-LANG): no P-TEXT row recorded"
        return ("a US session (P-LANG): the members' other languages are their own donors' (today's kit); "
                + "; ".join(parts) + ("; recorded: " + " | ".join(odd) if odd else ""))

    def gate_line(self, session: dict) -> tuple:
        """``(verdict, cause, detail)`` of R-GATE AS THE SESSION RECORDED IT (P-GATE's detail; rev. 2, the claim
        critique #9) -- never a fresh read of o4_forks.json."""
        rows = self._recorded(session, "P-GATE")
        if not rows:
            return None, None, "not recorded"
        detail = str(rows[-1][2])
        m = re.match(r"R-GATE (\S+) \(cause (\S+)\)", detail)
        return (m.group(1) if m else None, (m.group(2) if m and m.group(2) != "none" else None), detail)

    def report_extra(self, run_dir: Path, session: dict, pred: dict, runs: list, checks: list) -> list:
        """Report-only (5.4): the scope (six lines: start dependence; the settings and the derived facts; the engine;
        the language, read from the recorded P-TEXT rows; the fight, with R-GATE's recorded verdict; the
        achievement), the fight per run, the encore per run, R-GATE as recorded, the session's end, O2's sections
        (copied) and the re-runs held."""
        L = ["", "Scope (a US session):", "  start dependence -- " + SCOPE_START]
        st = (session.get("install") or {}).get("settings")
        L.append("  settings -- " + (json.dumps(st, sort_keys=True) if st is not None else "not recorded")
                 + "; derived -- " + "; ".join(f"{k} {v.get('value')} ({v.get('why')})"
                                               for k, v in (pred.get("derived") or {}).items()))
        eng = [d for _ok, _w, d in self._recorded(session, "P-ENGINE")]
        L.append("  engine -- " + (eng[-1] if eng else json.dumps((session.get("install") or {}).get("engine"))))
        L.append("  language -- " + self.scope_lang(session))
        verdict, cause, _gd = self.gate_line(session)
        L.append(f"  the fight -- a FAST play: raw >= 100, so the +30% is hidden by the clamp; the bonus on member(64) "
                 f"is R-GATE's: {verdict or 'not recorded'} ({cause or 'no cause'})")
        L.append("  the achievement -- " + SCOPE_ACHIEVEMENT)
        L.append("")
        L.append("The fight, per run (instances / presses, the first prompt after T0 in ticks, j_hi min/median/max, raw, "
                 "regimes, samples and the longest read gap, evidence, gone latency, slides, input, prompt forms, the "
                 "judge; the score and gil pages; the trace's ip338 / ip390 rows):")
        for r in runs:
            L += self._fight_lines(r, pred)
        L.append("")
        L.append("The encore, per run (127 as published at readiness, the pick, its frame, choose's rowed presses):")
        for r in runs:
            ch = [c for c in r.get("log") or () if c.get("k") == "choice"
                  and any(pred["chanbara"]["encore_match"] in str(o or "") for o in (c.get("options") or ()))]
            cp = [p for p in r.get("log") or () if p.get("k") == "press" and p.get("why") == "choose"]
            L.append(f"  {r['side']}#{r['i']}: " + ("no encore choice" if not ch else
                                                   "; ".join(f"options {c.get('options')} active {c.get('active')} "
                                                             f"selected {c.get('selected')} -> {c.get('index')} at frame "
                                                             f"{c.get('frame')}" for c in ch))
                     + (f"; choose presses {[(p.get('button'), p.get('seq'), p.get('down_frame')) for p in cp]}"
                        if cp else ""))
        L.append("")
        L.append(f"R-GATE (the +30% on member(64), outside the frozen claim; as P-GATE recorded it): {_gd}"[:600])
        L.append("")
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
    def _fight_lines(r: dict, pred: dict) -> list:
        lab = f"  {r['side']}#{r['i']}:"
        log, out = r.get("log") or [], r.get("outcome") or {}
        fl = fight_line(log, out).get("zone")
        if fl is None:
            v = r["rec"].get("v")
            return [f"{lab} no zone row" + (f" (the run VOID {v})" if v else "")]
        pol = pred["chanbara"]
        pages = list(out.get("pages") or [])
        score = next((p for p in pages if SD.SCORE_MARK in p), None)
        gil = next((p for p in pages if SD.GIL_MARK in p), None)
        members = members_of(pred) if r["side"] == "F" else {}
        sw = []
        for name, s in (pred.get("sword") or {}).items():
            if isinstance(s, dict):
                sw += [f"{name} {x.fld} {x.old}->{x.new}" for x in r["rows"] if x.k == "w"
                       and place(x.fld, members) == s["place"]
                       and (x.sid, x.tag, x.ip, x.target) == (s["sid"], s["tag"], s["ip"], s["target"])]
        fp = fl.get("first_prompt") or {}
        return [f"{lab} {fl['instances']} instances / {fl['presses']} presses; first prompt "
                f"{fp.get('after_t0_ticks')} ticks after T0; j_hi {fl['j_hi']}; raw {fl['raw']}; regimes "
                f"{fl['regimes']}; samples {fl['samples']}, longest read gap {fl['max_read_gap']}; evidence "
                f"{fl['evidence']}; gone latency median {fl['gone_ticks_median']} ticks; slides {fl['slides']}; input "
                f"{fl['input'] or 'none'}; forms {fl['forms']}; judge {fl['judge']}"
                + (f" (zone VOID {fl['v']}: {fl['why']})" if fl.get("v") else ""),
                f"{lab} score page {score!r} ({'as frozen' if score == pol['score_page'] else 'NOT as frozen'}); gil "
                f"page {gil!r}; trace {sw or 'no sword rows'}"]

    # -- the CLI ------------------------------------------------------------------------------------------------
    def add_arguments(self, ap) -> None:
        ap.add_argument("--draft", action="store_true", help="print the draft predictions as JSON")
        ap.add_argument("--rehearsal-report", metavar="RUN_DIR",
                        help="print an o4_rehearse.py launch's record, stage by stage and run by run, and R-GATE's "
                             "verdict with its cause")

    def handle(self, args) -> int | None:
        """``--rehearsal-report`` (O4's); ``--offline-check`` (O2's, with the chain's route members printed first);
        then O2's (``--draft``, ``--preflight``). O3's ``--skip-ab`` is not O4's: O4 registers no movie."""
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


def launch_engine_check(files: dict, engine: dict, launched, live: dict, pinned: dict) -> tuple:
    """P-LAUNCH with the engine (6.2; rev. 2), pure: ``(ok, detail)`` -- O3's :func:`o3_prima_vista.launch_check` over
    the stacked patch files, Memoria.ini AND the two engine DLLs (``engine``: ``{path: mtime}``), each older than the
    launch's first log stamp, and the DLLs' sha256 the pinned engine (:func:`p_engine`)."""
    ok, detail = P.launch_check({**files, **engine}, launched)
    eok, edetail = p_engine(live, pinned)
    return ok and eok, detail + "; " + edetail


O4 = O4Segment()


# ======================================================================== the rehearsal report
def rehearsal_report(run_dir) -> str:
    """``--rehearsal-report``: an o4_rehearse.py launch's ``o4_rehearsal.json`` (research/o4_design.md 7.2), stage by
    stage and run by run -- what each freeze item (7.3) is read from -- and R-GATE's verdict with its cause."""
    run_dir = Path(run_dir)
    doc = json.loads((run_dir / REHEARSAL_FILE).read_text(encoding="utf-8"))
    L = [f"O4 rehearsals -- {run_dir.name}  (draft sha {str(doc.get('draft_sha256'))[:8]}; stages "
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
            L.append(f"== {name}: the load smoke, pairs {stage.get('pairs')}  ({len(recs)} warp(s)) -- settles: "
                     f"{stage.get('settles')}")
            for rec in recs:
                reach = rec.get("reached") or {}
                er = rec.get("end_run") or {}
                L.append(f"  warp {rec.get('n')}: {rec.get('field')} at {rec.get('entrance')} SC {rec.get('sc')} -> "
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
            L.append(f"  run {rec.get('n')} ({rec.get('side', 'S')}): {out.get('end')} -- {out.get('why')}"
                     + (f" [{out.get('v')} {out.get('cell')} {out.get('by')}]" if out.get("v") else "")
                     + f"; {rec.get('t1', 0) - rec.get('t0', 0):.0f}s; trace {rec.get('trace_file')}")
            L.append(f"    grants: {len(rec.get('grants') or [])} (there must be none)")
            fz = (rec.get("fight") or {}).get("zone")
            if fz:
                fp = fz.get("first_prompt") or {}
                L.append(f"    fight: {fz.get('instances')} instances / {fz.get('presses')} presses; T0 -> first prompt "
                         f"{fp.get('after_t0_ticks')} ticks; j_hi {fz.get('j_hi')}; raw {fz.get('raw')}; regimes "
                         f"{fz.get('regimes')}; samples {fz.get('samples')}, longest read gap {fz.get('max_read_gap')};"
                         f" evidence {fz.get('evidence')}; gone latency {fz.get('gone_ticks_median')} ticks; slides "
                         f"{fz.get('slides')}; input {fz.get('input') or 'none'}; judge {fz.get('judge')}"
                         + (f"; zone VOID {fz.get('v')}: {fz.get('why')}" if fz.get("v") else ""))
                L.append(f"    prompt forms: {fz.get('forms')}; start page {fz.get('start_page')}")
            for p in rec.get("prompts") or ():
                L.append(f"    prompt {p.get('n')} {p.get('dbtn')}: j [{p.get('j_lo')}, {p.get('j_hi')}] regime "
                         f"{p.get('regime')} evidence {p.get('evidence')} listed+{p.get('listed_ticks')} gone+"
                         f"{p.get('gone_ticks')} read_gap {p.get('read_gap')} pass {p.get('pass_ticks')} lead "
                         f"{p.get('lead_ticks')} slide {(p.get('slide') or {}).get('ok') if p.get('slide') else '-'}")
            for pair in rec.get("pairs") or ():
                L.append(f"    pair {pair.get('texts')}: first seen -> gone {pair.get('s')} s, Confirms "
                         f"{pair.get('presses')}")
            for pg in rec.get("page_presses") or ():
                L.append(f"    page {pg.get('text')!r:.50}: {pg.get('presses')} press(es), frames to down "
                         f"{pg.get('to_down')}")
            for c in rec.get("choices") or ():
                L.append(f"    choice at frame {c.get('frame')}: {c.get('options')} active {c.get('active')} "
                         f"selected {c.get('selected')} -> rule {c.get('rule')} index {c.get('index')}")
            L.append(f"    published choices: {len(rec.get('published_choices') or [])} distinct snapshot(s)")
            pages = rec.get("pages") or []
            L.append(f"    pages: {len(pages)} ({sum(1 for p in pages if p.get('timed'))} timed); score page "
                     f"{rec.get('score_page')!r}; gil page {rec.get('gil_page')!r}")
            ev = rec.get("evidence") or {}
            L.append(f"    evidence: {len(ev.get('press') or [])} press row(s), {len(ev.get('forbidden') or [])} "
                     f"forbidden row(s), {len(ev.get('observed') or [])} observed row(s), {len(ev.get('input') or [])} "
                     f"input row(s)")
            npg = rec.get("no_progress") or {}
            L.append(f"    longest no-progress stretch: {npg.get('longest_s')}s at {npg.get('where')}")
            if rec.get("gate"):
                g_ = rec["gate"]
                L.append(f"    R-GATE reading: {g_.get('why')}; raw {g_.get('raw')}; page {g_.get('page')!r}; "
                         f"Byte[475] {g_.get('byte475')}; combo page {g_.get('combo')}")
            end = rec.get("end") or {}
            er = end.get("end_run") or {}
            L.append(f"    end: state {end.get('end_state')}; end_run "
                     + ("ok" if er.get("ok") else f"FAILED {er.get('why')}")
                     + f", title {er.get('title')}, rows {[x.get('k') for x in er.get('how') or ()]}")
            tr = rec.get("trace") or {}
            if tr:
                L.append(f"    trace: start line {tr.get('start')}, end line {tr.get('end')} (end places "
                         f"{tr.get('end_places')}), {tr.get('rows')} rows; SC {[x['new'] for x in tr.get('sc') or ()]}; "
                         f"FieldEntrance {[x['new'] for x in tr.get('entrance') or ()]}")
                L.append(f"      residue before the start {tr.get('residue_before')}; after {tr.get('residue_after')};"
                         f" other rows before it {tr.get('pre_other')}")
                for name2, keys in (tr.get("registered") or {}).items():
                    present = [k["what"] for k in keys if k["present"]]
                    L.append(f"      {name2}: {len(present)}/{len(keys)} present"
                             + (f"; present: {present[:4]}" if name2 in ("error_path", "forbidden_sites", "dead")
                                and present else ""))
                L.append(f"      sword rows {tr.get('sword')}; the crossing {tr.get('crossing')}; the end cut's row "
                         f"{tr.get('end_row')}")
                L.append(f"      unregistered keys ({len(tr.get('unregistered') or [])}): "
                         f"{(tr.get('unregistered') or [])[:12]}")
                L.append(f"      masked {tr.get('masked')}; join failures {len(tr.get('failures') or [])}")
                for h in tr.get("forbidden") or ():
                    L.append(f"      forbidden: {h['row']} {h['why']} -- "
                             + (f"backed by {h['by']}" if h["backed"] else "unbacked"))
        gv = (doc.get("gate") or {}).get(name)
        if gv:
            m = gv.get("member") or {}
            L.append(f"  R-GATE VERDICT: {gv.get('verdict')} (cause {gv.get('cause') or 'none'}) -- {gv.get('detail')}"
                     f"; S run {gv.get('s_run')}, F run {gv.get('f_run')}; no witness {gv.get('no_witness') or 'none'}"
                     f"; F ran member(64) {m.get('id')} in {m.get('folder')} (us .eb "
                     f"{str((m.get('eb') or {}).get('us'))[:12]}: P-GATE ties the witness to that build)")
        L.append("")
    return "\n".join(L)


# ======================================================================== the session and the CLI
def run(g) -> None:
    """The session (tools/play.py's entry): O4Segment.run."""
    return O4.run(g)


def main(argv=None) -> int:
    return O4.main(argv)


if __name__ == "__main__":
    sys.exit(main())
