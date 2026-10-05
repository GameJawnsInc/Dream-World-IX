"""THE STORY-WRITE TRACE, O7 -- STEINER'S WALK THROUGH THE CASTLE, A US SESSION: from a raw warp into 154 (the castle
hallway's balcony, entrance 315, the scenario at 1190; EVT_ALEX1_AC_ENT_2F) down the west flight to the ground and
through the south door, 158 (the courtyard south hall), 159 (the guardhouse court: THE FORCED MONOLOGUE on the way to
the west door), 160 (the west tower foot), 162 (the west tower hall) and 163 (the west tower stair: the stair foot's
squeeze) to the arrival in 164 at 342 -- stock against the alxc disc-1 chain O4 deployed, both sides played by one
driver (studies/story-trace/PLAN.md, "O7"; the design: research/o7_design.md).

    py tools/play.py studies/story-trace/o7_castle_walk.py --label story-o7 --timeout 240
    py studies/story-trace/o7_castle_walk.py --offline-check     # O4's build and its route pins per language, the keys
                                                                 # (the start-scoped olds, the start read, the carried
                                                                 # values DERIVED from O1-O6's frozen keys), the route
                                                                 # pins and their scans, block 3's text (strict) and the
                                                                 # monologue's pages, the store census, the regions (the
                                                                 # hazard's role), the walks' goals
    py studies/story-trace/o7_castle_walk.py --preflight         # the live install (read-only): all green, O4 deployed it
    py studies/story-trace/o7_castle_walk.py --draft             # the draft predictions, as JSON
    py studies/story-trace/o7_castle_walk.py --freeze            # write o7_predictions_v1.json (once: the lead, after
                                                                 # the stock rehearsals)
    py studies/story-trace/o7_castle_walk.py --analyse <run dir> # the analysis alone, on saved traces
    py studies/story-trace/o7_castle_walk.py --rehearsal-report <run dir>   # an o7_rehearse.py launch, stage by stage

THE SIDES (o7_forks.json: O4's chain, reused -- nothing imported, built or deployed for O7):
  S  stock. Start: 154, entrance 315, SC 1190. End: the arrival in REAL 164.
  F  O4's twenty members 31240-31259 as deployed: member(154) 31246, member(158) 31250, member(159) 31251, member(160)
     31252, member(162) 31254, member(163) 31255 and the end in member(164) 31256 -- read from O4's campaign.toml, never
     assumed. Every route Field() is retargeted, so the chain is closed (no seam), and a landing in a REAL donor field on
     F is V19, a finding.

THE ENTRY: New Game, the trace armed, then in field 70 a raw `warp <154 | 31246> 315 1190`: FOUR residue rows in field 70
(SC's two bytes, FieldEntrance's two: 315 is 0x013B), which the front cut sets aside and O7-START requires. Every run
first FORGETS the basis of every field it seeds (research/o7_design.md 0.2 #20), so each judges its own first moves.

THE ROUTE: segment_drive.drive with six visit-scoped cells -- 154's WALK (S17: the balcony, the west flight, the ground,
at clearance 120 on the exact PRIOR basis, Dojebon's hazard avoided) and its cross of e8 on the ground, then one cross a
field (158, 159 -- interrupted once by the monologue, its pages Confirmed, re-run -- 160, 162, and 163 at clearance 110:
the stair foot) -- the run-wide input witness, the stop page, the static watch on Dojebon; no battle, movie, choice or
naming. Control anywhere else is V4 (game) at its [place, sc, visit] cell.

THE ANALYSIS: each run cut at its start row (154's first write) and at its first row in an end PLACE (164: member(164) on
F), digested and compared as O1-O6's; the O7 checks (research/o7_design.md 5.3) read the start (four residue rows), no
SC rung, the chain, the residue, the writes EXACTLY, the landing per side (every crossing), THE WALKS (THE PAIRED-WALK
LAW per visit window, the monologue's rows only in their gap, every seeded field's first move judged), the sink's
emitted row pattern EXACTLY, the masked regions, the state handed to 164 (Byte[13] read from the trace: 164's prologue
races it), and every run's VOID classes by [place, sc, visit]. The predictions are frozen by the lead after the stock
rehearsals (o7_rehearse.py); until then --offline-check and --preflight read the draft.
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
import o6_steiner as C6                                                 # noqa: E402
import segment_drive as SD                                              # noqa: E402
import segment_trace as ST                                              # noqa: E402
from segment_trace import cut_at_end, cut_at_start, members_of, place         # noqa: E402

PREDICTIONS = HERE / "o7_predictions_v1.json"
MANIFEST = HERE / "o7_forks.json"
SESSION_FILE = "o7_session.json"
REPORT_FILE = "o7_report.txt"
REHEARSAL_FILE = "o7_rehearsal.json"
#: O4's chain and build, reused (research/o7_design.md 0.1 #2, 6.4): nothing is imported, built or deployed for O7.
CHAIN_DIR = C4.CHAIN_DIR
BUILD_DIR = C4.BUILD_DIR
GAME = A.GAME
SESSION_LANG = "us"
#: The text block the route's members carry (EVENT_ID_TO_MES): block 3 for 150-167. O7 reads no other.
TEXT_BLOCK, TEXT_BLOCKS = 3, (3,)
#: THE CASTLE WALK, every place in visit order, the end last (research/o7_design.md 4.1).
CASTLE = (154, 158, 159, 160, 162, 163, 164)
#: THE ONE SWITCH (4.17): the end place. 164 is the design's; R-STAIR's NO-GO sets 163 here, and the draft filters every
#: list to the places before it -- the route, the chain, the writes, the census, the regions, the table, the pattern,
#: the landing's crossings, the route donors -- and recomputes the end state.
END_FIELD = 164


def route_of(end: int = END_FIELD) -> tuple:
    """The places a run visits before ``end`` (the castle walk's order): (154, 158, 159, 160, 162, 163) for 164."""
    return CASTLE[:CASTLE.index(int(end))]


ROUTE = route_of(END_FIELD)
VISITS = ROUTE
#: The donors P-DONOR and P-DONOR-LOG read, and the route members derived from the chain: the route's and the end's.
ROUTE_DONORS = ROUTE + (END_FIELD,)
#: 4.13: O4's frozen settings PLUS what S19 and the walk numbers rest on -- [AnalogControl] (keys read twist.y: the prior
#: basis, session.py:2848-2866) and [Control] PSXMovementMethod (the slope-scaled run the budgets and walks rest on).
SETTINGS = json.loads(json.dumps(C4.SETTINGS))
SETTINGS["Control"]["PSXMovementMethod"] = "1"
SETTINGS["AnalogControl"] = {"Enabled": "1", "UseAbsoluteOrientation": "3"}
OVERRIDE70 = C4.OVERRIDE70
ENGINE = C4.ENGINE
DERIVED = C4.DERIVED
#: 1.3: Steiner's controller radius -- SetObjectLogicalSize(30, 35, 50)'s size x 4 (DoEventCode.cs:1531 ``component1.radius
#: = size * 4``), every O7 player entry's (4.14): the wall push-out's radius. ``collRad`` 35 is the actor-pair radius.
ENGINE_RADIUS = 120
#: 4.5: the span O7-KEYS requires of every start-scoped old's ``after.run`` and the report renders from the predictions.
AFTER_RUN = "O1-O6"
#: The frozen predictions O7-KEYS composes THE CARRIED VALUES from, in segment order (4.5; 0.2 #18).
PRIOR_SEGMENTS = ("o1_predictions_v4.json", "o2_predictions_v1.json", "o3_predictions_v1.json",
                  "o4_predictions_v1.json", "o5_predictions_v1.json", "o6_predictions_v1.json")
#: O6's frozen predictions: the start-scoped olds' ``after.old`` is read off its ``pattern`` (4.5; claim review #3).
O6_FROZEN = "o6_predictions_v1.json"
#: 4.12: the evidence's slack, DERIVED (O6's): his run per tick times the ticks a published sample may trail.
RUN_U_PER_TICK = C6.RUN_U_PER_TICK
STALE_TICKS = C6.STALE_TICKS
#: 2.1 (S12): the run-wide input witness.
WITNESS = {"input_every_s": 0.05,
           "why": "a walk is the driver's own input: outside input would move him where the walk did not (a step's "
                  "evidence, a door) -- the run-wide witness VOIDs a run that sees input (V13)"}
#: The keys a rehearsal stage may lay over a table step, each refused by the freeze (7.1 R-WALK-VOID's stops).
REHEARSAL_OVERLAYS = frozenset({"hold_stop", "page_stop"})
#: 4.9: the end-state targets untouched since New Game AND by O1-O6 -- the talk and scene bits of 154/159/160 and O8's
#: knight (none is in the composition of 0.2 #18): 0 on arrival in 164.
UNTOUCHED = ("Global.Bit[3811]", "Global.Bit[3798]", "Global.Bit[3799]", "Global.Bit[3849]", "Global.Bit[3850]",
             "Global.Bit[3851]", "Global.Bit[3852]", "Global.Bit[3792]", "Global.Bit[7211]", "Global.Int16[224]")
#: 4.9: the end-state target 164's prologue rewrites at once (ip130 2 -> 1): read from the TRACE, never live.
RACED = "Global.Byte[13]"
#: O6's start values (field 70's prologue; the warp's residue sets SC and FieldEntrance): what the raw start holds.
START_VALUES = {"Global.UInt16[0]": 1190, "Global.Int16[2]": 315, "Global.Byte[13]": 1, "Global.Int16[9]": 643,
                "Global.Int16[11]": -1, "Global.Byte[14]": 0, "Global.Byte[8]": 125}
#: The prologue's story-noise rows (each visit's e0 t0 Bit[191] := 0 and Bit[184] := 0): masked, every one emitted.
MASKED_TARGETS = ("Global.Bit[191]", "Global.Bit[184]")
#: The party ops O7-KEYS's scan refuses in an instanced entry of a route field (4.14).
PARTY_OPS = ("B_PARTYCHK", "B_PARTYADD", "SetPartyReserve", "RemoveParty", "AddParty")
SCOPE_END_STATE = ("read live on arrival in 164 but Byte[13], which 164's prologue rewrites at once (ip130 2 -> 1): taken "
                   "from the trace's last pre-cut write")
#: The words an A-START by THE START READ opens with (why_void): VOID-ASYM (b) sets that reason aside (_void_ids).
START_READ = "the start read"
_MODULE_DOC = __doc__


# ======================================================================== the chain (O4's campaign.toml)
def chain_from_campaign(campaign=None) -> tuple:
    """``({fork id: donor}, {fork id: member name})`` of O4's built alxc chain (its ``campaign.toml``; default O4's):
    its donors exactly O4's twenty (o4_castle.chain_from_campaign refuses another chain)."""
    return C4.chain_from_campaign(Path(campaign) if campaign is not None else CHAIN_DIR / "campaign.toml")


def route_members(members: dict, donors=ROUTE_DONORS) -> dict:
    """``{donor: fork id}`` for each route donor (the route's and the end's): the members the route runs and ends in
    (derived, each donor forked by exactly one member)."""
    out = {}
    for donor in donors:
        hits = sorted(f for f, d in members.items() if d == donor)
        if len(hits) != 1:
            raise AssertionError(f"donor {donor} is forked by {hits}, not exactly one member")
        out[donor] = hits[0]
    return out


def route_members_line(members: dict, donors=ROUTE_DONORS) -> str:
    """The line --offline-check and --draft print: ``member(154) 31246, ..., member(164) 31256``."""
    rm = route_members(members, donors)
    return ", ".join(f"member({d}) {rm[d]}" for d in donors)


def route_donors(pred: dict) -> tuple:
    """The predictions' route donors: the route's places and the end fields."""
    return tuple(pred["route"]) + tuple(pred.get("end_fields") or [pred["end_field"]])


# ======================================================================== the predictions (draft v1)
def _key(donor, sid, tag, ip, off, target, value, op, what, prior=None) -> dict:
    return A._key(donor, sid, tag, ip, off, target, value, op, what, prior)


def _site(place_, sid, tag, ip, target, value, **kw) -> dict:
    return C4._site(place_, sid, tag, ip, target, value, **kw)


#: Each route place's environment sound (Main_Init's ``Int16[9] := K``: -1 in 154 and 159, 385 in the others) and its
#: Main_Init's offset base (e0 t0 starts at ip10 in 154, ip6 elsewhere) -- the prologue's ips (4.16; the listings).
AMBIENT = {154: -1, 158: 385, 159: -1, 160: 385, 162: 385, 163: 385, 164: 385}


def _prologue_ips(donor: int) -> tuple:
    """Main_Init's prologue ips: Bit[191], Bit[184], Int16[9], the taken Byte[13] branch (ip123/119 under K -1, ip130
    under K 385), Int16[11], Byte[14] -- 154's own (ip26 ...), every other field's (ip22 ...)."""
    if donor == 154:
        return 26, 53, 61, 123, 142, 204
    return 22, 49, 57, (119 if AMBIENT[donor] < 0 else 130), 138, 200


def _ambient7(donor: int) -> list:
    """Each Main_Init's ambient four (e0 t0): Int16[9] := K, the Byte[13] branch it takes (:= 0 under K -1, := 1 under K
    385), Int16[11] := -1, Byte[14] := 0 (research/o7_design.md 4.4)."""
    _i191, _i184, i9, b13, i11, b14 = _prologue_ips(donor)
    base = 10 if donor == 154 else 6
    k9 = AMBIENT[donor]
    v13 = 0 if k9 < 0 else 1
    return [_key(donor, 0, 0, i9, i9 - base, "Global.Int16[9]", k9, ":=", f"{donor} Int16[9] := {k9} (ambient)"),
            _key(donor, 0, 0, b13, b13 - base, "Global.Byte[13]", v13, ":=",
                 f"{donor} Byte[13] := {v13} (ambient: Int16[9] {'<' if k9 < 0 else '>='} 0)"),
            _key(donor, 0, 0, i11, i11 - base, "Global.Int16[11]", -1, ":=", f"{donor} Int16[11] := -1 (ambient)"),
            _key(donor, 0, 0, b14, b14 - base, "Global.Byte[14]", 0, ":=", f"{donor} Byte[14] := 0 (ambient)")]


def _writes() -> list:
    """4.4's registered writes, in route order, every place's (the draft filters them to its route): 33 keys."""
    key = _key
    return (_ambient7(154)
            + _ambient7(158) + [
                key(158, 0, 0, 445, 439, "Global.Byte[13]", 2, ":=", "158 Byte[13] := 2 (the grant's pass)"),
                key(158, 2, 2, 194, 164, "Global.Byte[13]", 3, ":=", "158 e2 Byte[13] := 3 (the south door, LIVE: no "
                                                                     "Map.Bit[162] before it)")]
            + _ambient7(159) + [
                key(159, 0, 0, 290, 284, "Global.Byte[8]", 125, ":=", "159 Byte[8] := 125 (same: field 70 left 125 -- "
                                                                       "THE START READ, 4.5)"),
                key(159, 16, 1, 613, 223, "Global.Byte[208]", 0, ":=", "159 e16 t1 Byte[208] := 0 (the monologue)"),
                key(159, 16, 1, 648, 258, "Global.Byte[208]", 1, "++", "159 e16 t1 Byte[208] ++ (the monologue, one "
                                                                       "loop pass)", "159/16/1/613"),
                key(159, 16, 1, 672, 282, "Global.Bit[3796]", 1, ":=", "159 e16 t1 Bit[3796] := 1 (the monologue's "
                                                                       "guard set)")]
            + _ambient7(160) + [
                key(160, 0, 0, 465, 459, "Global.Byte[13]", 2, ":=", "160 Byte[13] := 2 (the grant's pass)")]
            + _ambient7(162) + [
                key(162, 0, 0, 932, 926, "Global.Byte[13]", 2, ":=", "162 Byte[13] := 2 (the grant's pass)")]
            + _ambient7(163) + [
                key(163, 0, 0, 684, 678, "Global.Byte[13]", 2, ":=", "163 Byte[13] := 2 (the grant's pass -- the end "
                                                                     "state's Byte[13], 4.9)")])


#: 4.3: THE FIELDENTRANCE CHAIN, each place's door store before its Field() (every place's; the draft filters).
CHAIN_SITES = {154: (8, 2, 355, 325, 300, "the south door's ground branch, then Field(158) ip363"),
               158: (2, 2, 222, 192, 331, "e2, then Field(159) ip230"),
               159: (11, 2, 193, 163, 332, "e11, then Field(160) ip201"),
               160: (5, 2, 227, 197, 333, "e5, then Field(162) ip235"),
               162: (3, 2, 227, 197, 341, "e3, then Field(163) ip235"),
               163: (2, 2, 227, 197, 342, "e2, then Field(164) ip235")}


def _chain(route) -> list:
    return [_key(p, sid, tag, ip, off, "Global.Int16[2]", v, ":=", f"FieldEntrance {v}: {p} {why}")
            for p in route for sid, tag, ip, off, v, why in [CHAIN_SITES[p]]]


def _error_path() -> list:
    """4.6: each field's four error-path stores -- Byte[13] := 9 / Byte[14] := 9 on an incoming 2 with Int16[9] < 0, and
    window 56's two resets (:= 0)."""
    rows = {154: (101, 182, 497, 531), 158: (97, 178, 288, 322), 159: (97, 178, 574, 608),
            160: (97, 178, 308, 342), 162: (97, 178, 775, 809), 163: (97, 178, 527, 561)}
    out = []
    for donor, (a, b, c, d) in rows.items():
        base = 10 if donor == 154 else 6
        for ip, target, value in ((a, "Global.Byte[13]", 9), (b, "Global.Byte[14]", 9), (c, "Global.Byte[13]", 0),
                                  (d, "Global.Byte[14]", 0)):
            out.append(_key(donor, 0, 0, ip, ip - base, target, value, ":=",
                            f"{donor} e0 t0 ip{ip}: the error path ({target} := {value})"))
    return out


def _forbidden_sites() -> list:
    """4.6: what a wrong door, a back door, a talk or a talk's scene writes: 22 sites."""
    key = _key
    return [key(154, 8, 2, 195, 165, "Global.Int16[2]", 301, ":=", "154 e8 Int16[2] := 301 (the balcony branch -> 153)"),
            key(154, 9, 2, 195, 165, "Global.Int16[2]", 302, ":=", "154 e9 Int16[2] := 302 (the balcony branch -> 156)"),
            key(154, 9, 2, 355, 325, "Global.Int16[2]", 300, ":=", "154 e9 Int16[2] := 300 (the ground branch -> 155)"),
            key(154, 10, 2, 195, 165, "Global.Int16[2]", 303, ":=", "154 e10 Int16[2] := 303 (the balcony branch -> "
                                                                    "156)"),
            key(154, 10, 2, 355, 325, "Global.Int16[2]", 300, ":=", "154 e10 Int16[2] := 300 (the ground branch -> "
                                                                    "167)"),
            key(154, 5, 3, 675, 8, "Global.Bit[3852]", 1, ":=", "154 e5 t3 Bit[3852] := 1 (Dojebon's talk)"),
            key(158, 1, 2, 193, 163, "Global.Byte[13]", 3, ":=", "158 e1 Byte[13] := 3 (the back door)"),
            key(158, 1, 2, 221, 191, "Global.Int16[2]", 331, ":=", "158 e1 Int16[2] := 331 (the back door -> 154)"),
            key(159, 5, 3, 636, 8, "Global.Bit[3849]", 1, ":=", "159 e5 t3 Bit[3849] := 1 (Haagen's talk)"),
            key(159, 5, 1, 311, 83, "Global.Bit[3798]", 1, ":=", "159 e5 t1 Bit[3798] := 1 (Haagen's scene)"),
            key(159, 10, 2, 193, 163, "Global.Int16[2]", 332, ":=", "159 e10 Int16[2] := 332 (the wrong door -> 158)"),
            key(159, 12, 2, 193, 163, "Global.Int16[2]", 332, ":=", "159 e12 Int16[2] := 332 (the wrong door -> 161)"),
            key(160, 2, 3, 298, 8, "Global.Bit[3850]", 1, ":=", "160 e2 t3 Bit[3850] := 1 (Weimar's talk)"),
            key(160, 2, 1, 230, 130, "Global.Bit[3799]", 1, ":=", "160 e2 t1 Bit[3799] := 1 (Weimar's scene)"),
            key(160, 9, 1, 380, 43, "Global.Byte[208]", 0, ":=", "160 e9 t1 Byte[208] := 0 (Weimar's scene)"),
            key(160, 9, 1, 415, 78, "Global.Byte[208]", 1, "++", "160 e9 t1 Byte[208] ++ (Weimar's scene)",
                "160/9/1/380"),
            key(160, 9, 1, 450, 113, "Global.Byte[208]", 0, ":=", "160 e9 t1 Byte[208] := 0 (Weimar's scene)"),
            key(160, 9, 1, 485, 148, "Global.Byte[208]", 1, "++", "160 e9 t1 Byte[208] ++ (Weimar's scene)",
                "160/9/1/450"),
            key(160, 4, 2, 194, 164, "Global.Byte[13]", 3, ":=", "160 e4 Byte[13] := 3 (the back door)"),
            key(160, 4, 2, 222, 192, "Global.Int16[2]", 333, ":=", "160 e4 Int16[2] := 333 (the back door -> 159)"),
            key(162, 2, 2, 227, 197, "Global.Int16[2]", 341, ":=", "162 e2 Int16[2] := 341 (the back door -> 160)"),
            key(163, 3, 2, 227, 197, "Global.Int16[2]", 342, ":=", "163 e3 Int16[2] := 342 (the back door -> 162)")]


def _dead() -> list:
    """4.6: the dead sites, each with why -- Int16[2] := 10000 behind Bit[184] == 1 (0), the prologue's untaken Byte[13]
    and Byte[14] branches, 154's 304 branch, and the door stores behind Map.Bit[162] == 0 (ip177), which each door's own
    ip38 sets 1 first: 24 sites."""
    key = _key
    out = []
    for donor in (154, 158, 159, 160, 162, 163):
        base = 10 if donor == 154 else 6
        ip10k = 45 if donor == 154 else 41
        out.append(key(donor, 0, 0, ip10k, ip10k - base, "Global.Int16[2]", 10000, ":=",
                       f"{donor} Int16[2] := 10000 (dead: Bit[184] == 1, it is 0)"))
        if AMBIENT[donor] < 0:
            ip13 = 134 if donor == 154 else 130
            out.append(key(donor, 0, 0, ip13, ip13 - base, "Global.Byte[13]", 1, ":=",
                           f"{donor} Byte[13] := 1 (dead: Int16[9] just set -1)"))
        else:
            out.append(key(donor, 0, 0, 119, 113, "Global.Byte[13]", 0, ":=",
                           f"{donor} Byte[13] := 0 (dead: Int16[9] 385 is not < 0)"))
        ip14 = 215 if donor == 154 else 211
        out.append(key(donor, 0, 0, ip14, ip14 - base, "Global.Byte[14]", 1, ":=",
                       f"{donor} Byte[14] := 1 (dead: Int16[11] just set -1)"))
        if donor == 154:
            out.append(key(154, 0, 0, 279, 269, "Global.Byte[8]", 125, ":=",
                           "154 Byte[8] := 125 (dead: the 304 branch L232)"))
    for donor, sid in ((160, 5), (162, 2), (162, 3), (163, 2), (163, 3)):
        out.append(key(donor, sid, 2, 199, 169, "Global.Byte[13]", 3, ":=",
                       f"{donor} e{sid} Byte[13] := 3 (dead: behind Map.Bit[162] == 0, which ip38 set 1 first)"))
    return out


def _filtered(keys: list, route) -> list:
    places = set(route)
    return [k for k in keys if k["donor"] in places]


def start_scoped() -> list:
    """4.5: the START-SCOPED olds -- three writes keys whose VALUE is the start's and a true O1-O6 run's alike, whose
    ``old`` / ``same`` differ: ``here`` [old, new] from the raw start, ``after`` from a true run (``after.old`` the new of
    the LAST tuple on the target in O6's FROZEN pattern -- O7-KEYS reads it off the file, :func:`olds_from_pattern`)."""
    src = ("old: the last pre-cut tuple on the target in o6_predictions_v1.json's pattern ({}); story-o6's six runs "
           "read {} past the cut")
    return [{"site": [154, 0, 0, 61], "target": "Global.Int16[9]", "here": [643, -1],
             "after": {"run": AFTER_RUN, "old": -1, "value": -1,
                       "source": src.format("153 e0 t0 ip57, -1", "154 ip61 -1 -> -1")}},
            {"site": [154, 0, 0, 123], "target": "Global.Byte[13]", "here": [1, 0],
             "after": {"run": AFTER_RUN, "old": 0, "value": 0,
                       "source": src.format("153 e0 t0 ip119, 0", "154 ip123 0 -> 0")}},
            {"site": [159, 16, 1, 613], "target": "Global.Byte[208]", "here": [0, 0],
             "after": {"run": AFTER_RUN, "old": 1, "value": 0,
                       "source": src.format("153 e32 t1 ip1632, 1", "no 159 row (O6 ends in 154)")}}]


def start_reads() -> list:
    """4.5 (rev. 2, claim review #7): the START READ -- 159 ip290, the route's first store of Byte[8], reads the start's
    Byte[8]: field 70's ip249 := 125 lies INSIDE the warp window, so a warp before it leaves 0 there."""
    return [{"site": [159, 0, 0, 290], "target": "Global.Byte[8]", "old": 125,
             "why": "field 70 e0 t0 ip249 Byte[8] := 125 lies inside the warp window (after ip130, behind ip229-246's "
                    "SYSVAR[3] wait, before ip475): a warp before it leaves 0, and this store -- the route's first on "
                    "Byte[8] -- would read 0 (0.2 #19). The trace is armed after 70's prologue: this old is the only "
                    "reading"}]


def carried() -> dict:
    """4.5: THE CARRIED VALUES -- a true O1-O6 run's value where the raw start holds 0 (typed here; O7-KEYS DERIVES them
    from the frozen O1-O6 keys, :func:`carried_from_segments`, and refuses a typed set that differs), neither written
    nor read on O7; and the party, typed and labelled, never derived (no gEventGlobal target)."""
    return {"why": "a true O1-O6 run's value (composed over the frozen O1-O6 keys in segment order: 4.5's derivation) "
                   "where the raw start holds 0; neither written nor read on O7 (154-163)",
            "values": {"Global.Bit[3717]": [0, 1], "Global.Bit[3718]": [0, 1], "Global.Byte[472]": [0, 4],
                       "Global.Int16[469]": [0, 1042], "Global.Bit[3815]": [0, 1], "Global.Byte[475]": [0, 100],
                       "Global.Bit[3795]": [0, 1], "Global.Bit[3854]": [0, 1], "Global.Bit[3855]": [0, 1],
                       "Global.UInt16[21]": [0, 8], "Global.Byte[303]": [0, 1], "Global.Byte[18]": [0, 1],
                       "Global.Byte[6]": [0, 11], "Global.UInt16[19]": [0, 1807]},
            "party": {"values": ["[Zidane]", "[Steiner]"],
                      "source": "not a gEventGlobal target: New Game's party; 153 e32 t1's rebuild (O6, UInt16[21] := 8) "
                                "-- typed, labelled, never derived"}}


#: 4.15: the route's regions, each the FIRST SetRegion of its (donor, entry) in the engine's point order.
E8 = [[2222, -5555], [-2222, -5555], [-2222, -4080], [2222, -4080]]
E9 = [[-3777, -999], [-3777, -3111], [-1888, -3111], [-1888, -999]]
E10 = [[3777, -999], [3777, -3111], [1888, -3111], [1888, -999]]
#: Decision 4(d): Dojebon's hazard, east of the spawn on the balcony -- a synthetic ``hazard`` role (no bytes pin, never
#: an exit), REQUIRED in 154 step 0's avoid.
HAZARD154 = [[150, -4080], [2222, -4080], [2222, -2950], [150, -2950]]


def _regions(route) -> dict:
    """4.15's regions on the route's places: every exit (14 at 164's end -- 154's three with their balcony branches,
    read off each tag 2's pinned ip38) and Dojebon's hazard. A ``hazard`` key is ``<donor>.hazard.<name>``, its
    ``object`` an entry instanced at the place's route entrance whose pinned guard it protects, its ``guards`` the
    (donor, sc, visit, step) whose ``avoid`` must hold it."""
    ex = A._exit
    regs = {
        "154.e8": ex(E8, 158, 300, None, branches=[{"y_gt": 100, "to": 153, "entrance": 301}],
                     why="the south door: tag 2 ip38 f[1] < -100 (the balcony: ip195 Int16[2] := 301, Field(153)), else "
                         "the ground (ip355 := 300, ip363 Field(158))"),
        "154.e9": ex(E9, 155, 300, None, branches=[{"y_gt": 100, "to": 156, "entrance": 302}],
                     why="the west door: the balcony -> 156 @302, the ground -> 155 @300"),
        "154.e10": ex(E10, 167, 300, None, branches=[{"y_gt": 100, "to": 156, "entrance": 303}],
                      why="the east door: the balcony -> 156 @303, the ground -> 167 @300"),
        "154.hazard.dojebon": A._region(HAZARD154, "hazard", object={"sid": 5, "guard": [154, 5, 1, 263]},
                                        guards=[[154, 1190, 1, 0]],
                                        why="Dojebon (e5) waits at ip263 while B_DISTANCEA < 3600 or Map.Byte[30] == 1: "
                                            "east of the spawn a probe or a hold could take Steiner out of his circle "
                                            "on the balcony and release him head-on up the west flight (decision 4(d); "
                                            "0.2 #11)"),
        "158.e1": ex([[-612, -8797], [588, -8797], [618, -12487], [-642, -12487]], 154, 331, None,
                     why="the back door, 300 u north: ip193 Byte[13] := 3, ip221 Int16[2] := 331, Field(154)"),
        "158.e2": ex([[480, -17752], [-450, -17752], [-1061, -15641], [1009, -15641]], 159, 331, None,
                     why="the south door: ip194 Byte[13] := 3 (live), ip222 := 331, Field(159)"),
        "159.e10": ex([[1120, 6590], [-1130, 6590], [-1160, 4910], [1150, 4910]], 158, 332, None,
                      why="the north door -> 158: ip193 Int16[2] := 332"),
        "159.e11": ex([[-3498, 955], [-3498, -888], [-2208, -888], [-2569, 1039]], 160, 332, None,
                      why="the west door: ip193 Int16[2] := 332, Field(160); wholly at x <= -2208, inside the "
                          "monologue's box test"),
        "159.e12": ex([[3410, 901], [3403, -631], [2254, -623], [2550, 941]], 161, 332, None,
                      why="the east door -> 161: ip193 Int16[2] := 332"),
        "160.e4": ex([[3018, -4012], [3018, -4792], [1459, -4463], [1371, -3599]], 159, 333, None,
                     why="the back door, 61 u east of the spawn: ip194 Byte[13] := 3 (live), ip222 := 333"),
        "160.e5": ex([[-561, -127], [-111, -127], [-49, -1065], [-589, -1065]], 162, 333, None,
                     why="the stair door: ip38 Map.Bit[162] := 1 (ip199 dead), ip227 Int16[2] := 333, Field(162)"),
        "162.e2": ex([[575, -5321], [1385, -5321], [1415, -3850], [-205, -3850]], 160, 341, None,
                     why="the back door, 50 u south of the spawn: ip227 Int16[2] := 341, Field(160)"),
        "162.e3": ex([[755, 3730], [1265, 3730], [1265, 130], [725, 130]], 163, 341, None,
                     why="the north door: ip227 Int16[2] := 341, Field(163)"),
        "163.e2": ex([[721, 4803], [866, 5202], [1432, 5013], [1300, 4705]], 164, 342, None,
                     why="the stair top: ip227 Int16[2] := 342, Field(164) -- THE O7 EXIT"),
        "163.e3": ex([[1210, 1307], [437, 1254], [377, 2244], [1238, 1892]], 162, 342, None,
                     why="the back door, 73 u from the spawn: ip227 Int16[2] := 342, Field(162)"),
    }
    places = {str(p) for p in route}
    return {k: v for k, v in regs.items() if k.split(".", 1)[0] in places}


def _table(route, closures=None) -> list:
    """2.4's six visit-scoped cells (the draft filters them to its route). ``closures``: 154's two lists (step 0's 119,
    step 1's 134), default the typed ones (:data:`CLOSURES154`; O7-GOALS (g4) derives them from their definitions)."""
    c0, c1 = closures if closures is not None else CLOSURES154
    order = {p: i + 1 for i, p in enumerate(route)}
    cells = {
        154: [{"kind": "walk", "name": "154: the balcony, the west flight, to the ground", "goal": [0, -600],
               "start": [-58, -3758], "avoid": ["154.e8", "154.e9", "154.e10", "154.hazard.dojebon"],
               "closed_tris": list(c0), "clearance": ENGINE_RADIUS, "basis": "prior", "attempts": 3,
               "beat": "w154_ground"},
              {"kind": "cross", "name": "154: the south door, ground branch", "goal": [0, -4500], "target": "154.e8",
               "to": 158, "start": [0, -600], "avoid": ["154.e9", "154.e10"], "closed_tris": list(c1),
               "clearance": ENGINE_RADIUS, "beat": "x154_e8"}],
        158: [{"kind": "cross", "name": "158: the south door", "goal": [-17, -16444], "target": "158.e2", "to": 159,
               "start": [0, -12787], "avoid": ["158.e1"], "clearance": ENGINE_RADIUS, "basis": "prior",
               "beat": "x158_e2"}],
        159: [{"kind": "cross", "name": "159: the west door (the forced monologue on the way)", "goal": [-2910, -300],
               "target": "159.e11", "to": 160, "start": [7, 3870], "avoid": ["159.e10", "159.e12"], "interrupts": 1,
               "clearance": ENGINE_RADIUS, "beat": "x159_e11"}],
        160: [{"kind": "cross", "name": "160: the stair door", "goal": [-313, -813], "target": "160.e5", "to": 162,
               "start": [1357, -4063], "avoid": ["160.e4"], "clearance": ENGINE_RADIUS, "basis": "prior",
               "beat": "x160_e5"}],
        162: [{"kind": "cross", "name": "162: the north door", "goal": [1001, 406], "target": "162.e3", "to": 163,
               "start": [957, -3800], "avoid": ["162.e2"], "clearance": ENGINE_RADIUS, "basis": "prior",
               "beat": "x162_e3"}],
        163: [{"kind": "cross", "name": "163: the stair top", "goal": [997, 4957], "target": "163.e2", "to": 164,
               "start": [690, 2195], "avoid": ["163.e3"], "clearance": 110, "basis": "prior", "attempts": 3,
               "beat": "x163_e2"}],
    }
    return [{"donor": p, "sc": 1190, "visit": order[p], "steps": copy.deepcopy(cells[p])} for p in route]


#: 2.4: 154's two closure lists as typed (O7-GOALS (g4) and the dry run's closures154 unit DERIVE them from their
#: definitions on stock 154's open triangles, :func:`closures154`): step 0 -- every ground triangle whose XZ overlaps a
#: non-ground one, plus every non-ground one east of x 450 and north of z -3250 (the east flight: forbidden on any
#: replan); step 1 -- every non-ground triangle. 119 and 134 (the research's reconcile/closures154.json).
CLOSURES154 = (
    [26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 60, 61, 62, 63, 69, 70, 71, 72, 74, 75, 76, 77, 78,
     79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105,
     106, 107, 108, 109, 110, 111, 116, 117, 118, 119, 120, 121, 130, 131, 132, 133, 134, 135, 136, 163, 165, 177, 178,
     179, 185, 189, 190, 191, 192, 193, 196, 197, 198, 199, 200, 201, 202, 203, 204, 206, 208, 211, 212, 213, 214, 215,
     216, 218, 221, 235, 239, 251, 252, 253, 254, 273, 274, 275, 276, 277, 281, 285, 287],
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33,
     34, 35, 36, 37, 38, 39, 40, 41, 174, 175, 176, 177, 178, 179, 185, 189, 190, 191, 192, 193, 196, 197, 205, 206,
     207, 208, 209, 210, 211, 212, 213, 217, 219, 220, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234,
     235, 237, 238, 239, 240, 241, 242, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259,
     260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282,
     283, 284, 285, 286, 287, 288, 289, 290, 291, 292])


def route_pins() -> list:
    """4.14's route pins: ``[donor, sid, tag, ip, eb-src text]`` -- the bytes the driver, the walks, the monologue, the
    hazard, the start and the FakeGame rest on, each compared EXACTLY with the stock US script's instruction text
    (O7-KEYS (b)); each player entry's spawn SETs read the same way. Every place's (the draft filters by donor; 70's,
    the warp window's, always kept)."""
    sw = "SET({Global.Int16[2] const(%d) B_LET B_EXPR_END})"
    ht = "SET({obj(uid=250).f[1] const(65436) B_LT B_EXPR_END})"
    pins = [[154, 0, 0, 26, "SET({Global.Bit[191] const(0) B_LET B_EXPR_END})"],
            [154, 0, 0, 223, "SetControlDirection(246, 0)"], [154, 0, 0, 234, "SWITCH(304, L392, L232)"],
            [154, 0, 0, 539, "SET({Map.Bit[159] const(1) B_LET B_EXPR_END})"],
            [154, 0, 0, 547, "SET({Map.Bit[158] const(1) B_EQ B_EXPR_END})"],
            [154, 0, 0, 566, "SET({Map.Bit[159] const(1) B_EQ B_EXPR_END})"],
            [154, 0, 0, 577, "SET({Map.Bit[156] const(0) B_EQ B_EXPR_END})"], [154, 0, 0, 588, "EnableMove()"],
            [154, 15, 0, 14, "SWITCHEX(L2028, 331, L28, 310, L204, 311, L380, 312, L556, 313, L1292)"],
            [154, 15, 0, 2038, "SET({Map.Int16[0] const(65478) B_LET B_EXPR_END})"],
            [154, 15, 0, 2046, "SET({Map.Int16[4] const(61778) B_LET B_EXPR_END})"],
            [154, 15, 0, 2054, "SET({Map.Int16[6] const(128) B_LET B_EXPR_END})"],
            [154, 15, 0, 2062, "SET({Map.Int16[2] const(63795) B_LET B_EXPR_END})"],
            [154, 15, 0, 2070, "SET({Map.Bit[158] const(1) B_LET B_EXPR_END})"],
            [154, 15, 0, 2116, "SET({Map.Byte[30] const(2) B_LET B_EXPR_END})"],
            [154, 15, 0, 2127, "SetControlDirection(250, 0)"], [154, 15, 0, 2774, "SetModel(5489, 104)"],
            [154, 15, 0, 2812, "SetObjectLogicalSize(30, 35, 50)"],
            [154, 15, 0, 2827, "MoveInstantXZY({obj(uid=255).f[0] B_EXPR_END}, {Map.Int16[2] B_EXPR_END}, "
                               "{obj(uid=255).f[2] B_EXPR_END})"],
            [154, 15, 0, 3003, "DefinePlayerCharacter()"],
            [154, 8, 2, 30, "SET({B_SYSVAR[2] B_EXPR_END})"], [154, 8, 2, 38, ht], [154, 8, 2, 51, "ExitField()"],
            [154, 8, 2, 211, "ExitField()"], [154, 8, 2, 195, sw % 301], [154, 8, 2, 203, "Field(153)"],
            [154, 8, 2, 305, "op_22(25)"], [154, 8, 2, 355, sw % 300], [154, 8, 2, 363, "Field(158)"],
            [154, 9, 2, 38, ht], [154, 9, 2, 195, sw % 302], [154, 9, 2, 203, "Field(156)"], [154, 9, 2, 355, sw % 300],
            [154, 9, 2, 363, "Field(155)"],
            [154, 10, 2, 38, ht], [154, 10, 2, 195, sw % 303], [154, 10, 2, 203, "Field(156)"],
            [154, 10, 2, 355, sw % 300], [154, 10, 2, 363, "Field(167)"],
            [154, 5, 0, 14, "SET({Map.Int16[0] const(62836) B_LET B_EXPR_END})"],
            [154, 5, 0, 22, "SET({Map.Int16[4] const(63836) B_LET B_EXPR_END})"],
            [154, 5, 1, 263, "SET({B_PTR(250) B_DISTANCEA const(3600) B_LT Map.Byte[30] const(1) B_EQ B_OROR "
                             "B_EXPR_END})"],
            [154, 5, 1, 486, "SET({B_PTR(250) B_DISTANCEA const(3600) B_LT Map.Byte[30] const(1) B_EQ B_OROR "
                             "B_EXPR_END})"],
            [154, 11, 1, 14, "SET({Map.Byte[30] const(2) B_EQ obj(uid=250).f[1] const(64936) B_GT B_ANDAND "
                             "B_EXPR_END})"],
            [154, 11, 1, 33, "SET({Map.Byte[30] const(1) B_LET B_EXPR_END})"],
            [154, 11, 1, 128, "SET({Map.Byte[30] const(1) B_EQ obj(uid=250).f[1] const(65036) B_LT B_ANDAND "
                              "B_EXPR_END})"],
            [154, 11, 1, 147, "SET({Map.Byte[30] const(2) B_LET B_EXPR_END})"]]
    pins += [[158, 0, 0, 57, "SET({Global.Int16[9] const(385) B_LET B_EXPR_END})"],
             [158, 0, 0, 130, "SET({Global.Byte[13] const(1) B_LET B_EXPR_END})"], [158, 0, 0, 379, "EnableMove()"],
             [158, 0, 0, 445, "SET({Global.Byte[13] const(2) B_LET B_EXPR_END})"],
             [158, 0, 0, 219, "SetControlDirection(0, 0)"],
             [158, 6, 0, 14, "SWITCH(300, L47, L12)"], [158, 6, 0, 22, "SET({Map.Int16[0] const(0) B_LET B_EXPR_END})"],
             [158, 6, 0, 30, "SET({Map.Int16[4] const(52749) B_LET B_EXPR_END})"],
             [158, 6, 0, 38, "SET({Map.Int16[6] const(0) B_LET B_EXPR_END})"],
             [158, 6, 0, 130, "SetObjectLogicalSize(30, 35, 50)"], [158, 6, 0, 301, "DefinePlayerCharacter()"],
             [158, 2, 2, 30, "SET({B_SYSVAR[2] B_EXPR_END})"], [158, 2, 2, 50, "ExitField()"],
             [158, 2, 2, 144, "op_22(25)"], [158, 2, 2, 194, "SET({Global.Byte[13] const(3) B_LET B_EXPR_END})"],
             [158, 2, 2, 222, sw % 331], [158, 2, 2, 230, "Field(159)"],
             [158, 1, 2, 193, "SET({Global.Byte[13] const(3) B_LET B_EXPR_END})"], [158, 1, 2, 221, sw % 331],
             [158, 1, 2, 229, "Field(154)"]]
    pins += [[159, 0, 0, 119, "SET({Global.Byte[13] const(0) B_LET B_EXPR_END})"],
             [159, 0, 0, 219, "SetControlDirection(0, 0)"],
             [159, 0, 0, 290, "SET({Global.Byte[8] const(125) B_LET B_EXPR_END})"], [159, 0, 0, 665, "EnableMove()"],
             [159, 16, 0, 14, "SWITCH(333, L84, L49, L14)"],
             [159, 16, 0, 94, "SET({Map.Int16[0] const(7) B_LET B_EXPR_END})"],
             [159, 16, 0, 102, "SET({Map.Int16[4] const(3870) B_LET B_EXPR_END})"],
             [159, 16, 0, 110, "SET({Map.Int16[6] const(0) B_LET B_EXPR_END})"],
             [159, 16, 0, 167, "SetObjectLogicalSize(30, 35, 50)"], [159, 16, 0, 338, "DefinePlayerCharacter()"],
             [159, 16, 1, 390, "SET({Global.Bit[3796] const(0) B_EQ obj(uid=255).f[0] const(63936) B_LT "
                               "obj(uid=255).f[0] const(1600) B_GT B_OROR obj(uid=255).f[2] const(800) B_LT B_OROR "
                               "B_ANDAND B_EXPR_END})"],
             [159, 16, 1, 445, "DisableMove()"], [159, 16, 1, 508, "WindowAsync(4, 128, 296)"],
             [159, 16, 1, 537, "WindowSync(4, 128, 297)"], [159, 16, 1, 543, "WindowAsync(4, 128, 298)"],
             [159, 16, 1, 561, "WindowAsync(4, 128, 299)"], [159, 16, 1, 602, "WindowAsync(4, 128, 300)"],
             [159, 16, 1, 613, "SET({Global.Byte[208] const(0) B_LET B_EXPR_END})"],
             [159, 16, 1, 648, "SET({Global.Byte[208] B_POST_PLUS B_EXPR_END})"],
             [159, 16, 1, 653, "SET({Global.Byte[208] const(1) B_LT B_EXPR_END})"],
             [159, 16, 1, 672, "SET({Global.Bit[3796] const(1) B_LET B_EXPR_END})"], [159, 16, 1, 711, "EnableMove()"],
             [159, 11, 2, 30, "SET({B_SYSVAR[2] B_EXPR_END})"], [159, 11, 2, 49, "ExitField()"],
             [159, 11, 2, 143, "op_22(25)"], [159, 11, 2, 193, sw % 332], [159, 11, 2, 201, "Field(160)"],
             [159, 10, 2, 201, "Field(158)"], [159, 12, 2, 201, "Field(161)"]]
    pins += [[160, 0, 0, 219, "SetControlDirection(246, 0)"],
             [160, 0, 0, 232, "SET({Global.Bit[3799] const(0) B_EQ B_EXPR_END})"], [160, 0, 0, 399, "EnableMove()"],
             [160, 0, 0, 465, "SET({Global.Byte[13] const(2) B_LET B_EXPR_END})"],
             [160, 9, 0, 14, "SWITCH(341, L39, L12)"],
             [160, 9, 0, 49, "SET({Map.Int16[0] const(1357) B_LET B_EXPR_END})"],
             [160, 9, 0, 57, "SET({Map.Int16[4] const(61473) B_LET B_EXPR_END})"],
             [160, 9, 0, 65, "SET({Map.Int16[6] const(60) B_LET B_EXPR_END})"],
             [160, 9, 0, 114, "SetObjectLogicalSize(30, 35, 50)"], [160, 9, 0, 285, "DefinePlayerCharacter()"],
             [160, 5, 2, 38, "SET({Map.Bit[162] const(1) B_LET B_EXPR_END})"],
             [160, 5, 2, 177, "SET({Map.Bit[162] const(0) B_EQ B_EXPR_END})"],
             [160, 5, 2, 199, "SET({Global.Byte[13] const(3) B_LET B_EXPR_END})"], [160, 5, 2, 227, sw % 333],
             [160, 5, 2, 235, "Field(162)"],
             [160, 4, 2, 194, "SET({Global.Byte[13] const(3) B_LET B_EXPR_END})"], [160, 4, 2, 222, sw % 333],
             [160, 4, 2, 230, "Field(159)"]]
    pins += [[162, 0, 0, 219, "SetControlDirection(244, 0)"], [162, 0, 0, 866, "EnableMove()"],
             [162, 0, 0, 932, "SET({Global.Byte[13] const(2) B_LET B_EXPR_END})"],
             [162, 7, 0, 14, "SWITCH(342, L39, L12)"],
             [162, 7, 0, 49, "SET({Map.Int16[0] const(957) B_LET B_EXPR_END})"],
             [162, 7, 0, 57, "SET({Map.Int16[4] const(61736) B_LET B_EXPR_END})"],
             [162, 7, 0, 65, "SET({Map.Int16[6] const(128) B_LET B_EXPR_END})"],
             [162, 7, 0, 114, "SetObjectLogicalSize(30, 35, 50)"], [162, 7, 0, 285, "DefinePlayerCharacter()"],
             [162, 3, 2, 38, "SET({Map.Bit[162] const(1) B_LET B_EXPR_END})"], [162, 3, 2, 227, sw % 341],
             [162, 3, 2, 235, "Field(163)"],
             [162, 2, 2, 38, "SET({Map.Bit[162] const(1) B_LET B_EXPR_END})"], [162, 2, 2, 227, sw % 341],
             [162, 2, 2, 235, "Field(160)"]]
    pins += [[163, 0, 0, 219, "SetControlDirection(16, 16)"], [163, 0, 0, 618, "EnableMove()"],
             [163, 0, 0, 684, "SET({Global.Byte[13] const(2) B_LET B_EXPR_END})"],
             [163, 7, 0, 14, "SWITCH(343, L47, L12)"],
             [163, 7, 0, 57, "SET({Map.Int16[0] const(690) B_LET B_EXPR_END})"],
             [163, 7, 0, 65, "SET({Map.Int16[4] const(2195) B_LET B_EXPR_END})"],
             [163, 7, 0, 73, "SET({Map.Int16[6] const(128) B_LET B_EXPR_END})"],
             [163, 7, 0, 122, "SetObjectLogicalSize(30, 35, 50)"], [163, 7, 0, 293, "DefinePlayerCharacter()"],
             [163, 2, 2, 30, "SET({B_SYSVAR[2] B_EXPR_END})"],
             [163, 2, 2, 38, "SET({Map.Bit[162] const(1) B_LET B_EXPR_END})"], [163, 2, 2, 55, "ExitField()"],
             [163, 2, 2, 149, "op_22(25)"], [163, 2, 2, 227, sw % 342], [163, 2, 2, 235, "Field(164)"],
             [163, 3, 2, 38, "SET({Map.Bit[162] const(1) B_LET B_EXPR_END})"], [163, 3, 2, 227, sw % 342],
             [163, 3, 2, 235, "Field(162)"]]
    pins += [[164, 0, 0, 22, "SET({Global.Bit[191] const(0) B_LET B_EXPR_END})"]]
    pins += [[70, 0, 0, 130, "SET({Global.Byte[13] const(1) B_LET B_EXPR_END})"],
             [70, 0, 0, 238, "SET({B_SYSVAR[3] const(0) B_NE B_EXPR_END})"], [70, 0, 0, 246, "JMP_IF(L229)"],
             [70, 0, 0, 249, "SET({Global.Byte[8] const(125) B_LET B_EXPR_END})"],
             [70, 0, 0, 475, "SET({Global.Byte[13] const(2) B_LET B_EXPR_END})"]]
    return pins


#: 6.1 / C0: O7-BUILD's route pins, measured read-only on O4's build (every language, each decoded on its own): each
#: route member's in-chain ``Field()`` sites ``[sid, tag, ip, literal]`` (US ips; the same in all 7 languages) -- the ONLY
#: bytes it differs from its donor in are these operands.
BUILD_FIELDS = {"154": [[2, 1, 1528, 153], [8, 2, 203, 153], [8, 2, 363, 158], [9, 2, 203, 156], [9, 2, 363, 155],
                        [10, 2, 203, 156], [10, 2, 363, 167]],
                "158": [[1, 2, 229, 154], [2, 2, 230, 159]],
                "159": [[10, 2, 201, 158], [11, 2, 201, 160], [12, 2, 201, 161]],
                "160": [[4, 2, 230, 159], [5, 2, 235, 162]],
                "162": [[2, 2, 235, 160], [3, 2, 235, 163]],
                "163": [[2, 2, 235, 164], [3, 2, 235, 162]],
                "164": [[2, 2, 251, 165], [3, 2, 251, 163]]}


def route_build(donors=ROUTE_DONORS) -> dict:
    """O7-BUILD's route pins (6.1): C0's measurement on O4's build, filtered to the route donors."""
    return {"fields": {str(d): copy.deepcopy(BUILD_FIELDS[str(d)]) for d in donors},
            "why": "C0 (research/o7_design.md 9 PART C), read-only on O4's build C:/gd/_ns_playtest/o4/build: per "
                   "language, each route member differs from its donor in exactly these operands (154: 14 bytes, 158: "
                   "4, 159: 6, 160: 4, 162: 4, 163: 4, 164: 4 -- 20 sites, 40 bytes; o7_forks.json built.measured)"}


def route_mes() -> dict:
    """4.14's ``route_mes`` (block 3, US: the asset the engine reads): the monologue's five pages and the stop page
    (O7-TEXT reads them)."""
    return {"block": TEXT_BLOCK,
            "monologue": [{"mes": 296, "holds": "What!?"}, {"mes": 297, "holds": "[STNR]"},
                          {"mes": 298, "holds": "[STNR]"}, {"mes": 299, "holds": "[STNR]"},
                          {"mes": 300, "holds": "I must hurry!"}],
            "stop_page": {"mes": 56, "holds": "Env Play()"}}


def monologue_pages(pages, pred: dict, reg: dict) -> list:
    """The registered interruption ``reg``'s pages among a run's listed ``pages`` (its outcome's texts, in listing order;
    the --analyse report's, never judged): from the first page holding the pinned text of ``reg``'s FIRST page
    (``route_mes``' monologue by mes: 296 "What!?") through the first after it holding its LAST page's (300 "I must
    hurry!") -- or to the run's last page when that never came (a stop mid-monologue). The pages between are bounded by
    the two ends: their pinned text is the speaker tag [STNR] alone, which the agent publishes rendered as the name.
    ``[]`` when no page holds the first page's text."""
    holds = {m.get("mes"): str(m.get("holds") or "") for m in (pred.get("route_mes") or {}).get("monologue") or ()}
    mes = list(reg.get("pages") or ())
    texts = [str(p) for p in pages or ()]
    first, last = (holds.get(mes[0], ""), holds.get(mes[-1], "")) if mes else ("", "")
    i = next((k for k, p in enumerate(texts) if first and first in p), None)
    if i is None:
        return []
    j = next((k for k in range(i, len(texts)) if last and last in texts[k]), len(texts) - 1)
    return texts[i:j + 1]


def _rows_of_visit(donor: int, writes: list, chain: list) -> list:
    """One visit's emitted row pattern (4.16): its prologue P(...) -- the masked pair and the ambient four, each with
    ``same`` from the start values and the visits before -- then its post rows in the bytes' order: the writes after
    the ambient four (in their listed order), then the door's chain row. Tuples ``[place, sid, tag, off, target, new,
    same]``; the ``same`` flags are filled by :func:`_pattern`."""
    amb = {(k["sid"], k["tag"], k["ip"]) for k in _ambient7(donor)}
    i191, i184 = _prologue_ips(donor)[:2]
    base = 10 if donor == 154 else 6
    rows = [[donor, 0, 0, i191 - base, "Global.Bit[191]", 0], [donor, 0, 0, i184 - base, "Global.Bit[184]", 0]]
    rows += [[donor, k["sid"], k["tag"], k["off"], k["target"], k["value"]] for k in _ambient7(donor)]
    rows += [[donor, k["sid"], k["tag"], k["off"], k["target"], k["value"]] for k in writes
             if k["donor"] == donor and (k["sid"], k["tag"], k["ip"]) not in amb]
    rows += [[donor, k["sid"], k["tag"], k["off"], k["target"], k["value"]] for k in chain if k["donor"] == donor]
    return rows


def _pattern(route, writes: list, chain: list) -> dict:
    """4.16: THE EMITTED ROW PATTERN over this start (field 70's prologue values, the raw warp): no site is stored twice
    before the cut, so the sink emits every store (StoryTrace.cs:374-401) and no ``c`` row arises -- each visit's
    emitted ``w`` rows in order, ``[place, sid, tag, off, target, new, same]``, ``same`` 1 when the store left its
    target's value as it was (the start values, then each row in route order). No floating row: every order is the
    bytes'."""
    values = dict(START_VALUES)
    visits = []
    for donor in route:
        out = []
        for p_, sid, tag, off, target, new in _rows_of_visit(donor, writes, chain):
            old = values.get(target, 0)
            out.append([p_, sid, tag, off, target, new, int(old == new)])
            values[target] = new
        visits.append(out)
    n = sum(len(v) for v in visits)
    return {"visits": visits, "floating": [], "counts": [],
            "why": f"StoryTrace.cs:374-401 over the raw warp's start values (Int16[9] 643, Byte[13] 1, Int16[11] -1, "
                   f"Byte[14] 0, Byte[8] 125, Bit[191] 0, Bit[184] 0): no site is stored twice before the cut, so every "
                   f"store is emitted -- same-value ones too, each the first at its site in the epoch -- and no c row "
                   f"arises; {n} w rows ({2 * len(route)} masked) before the cut, then {route[-1] if route else '?'}'s "
                   f"door and the end place's ip22, the cut"}


def _end_state(pred_pattern: dict, scenario: int, keys: list) -> tuple:
    """4.9, COMPUTED (never typed): ``(end_state, end_state_trace)`` -- every target the pattern writes, its last value
    in route order, with SC the scenario (no rung), Byte[13] taken OUT of the live read (164's prologue races it) and
    put in ``end_state_trace`` at its last pre-cut site (its ip the registered key's, ``keys``); plus
    :data:`UNTOUCHED`, 0."""
    last, site = {}, {}
    for visit in pred_pattern["visits"]:
        for p_, sid, tag, off, target, new, _same in visit:
            last[target] = new
            site[target] = (p_, sid, tag, off)
    live = {"Global.UInt16[0]": int(scenario)}
    live.update({t: v for t, v in last.items() if t != RACED})
    live.update({t: 0 for t in UNTOUCHED})
    trace = {}
    if RACED in last:
        p_, sid, tag, off = site[RACED]
        ip = next(k["ip"] for k in keys if (k["donor"], k["sid"], k["tag"], k["off"], k["target"]) == (
            p_, sid, tag, off, RACED))
        trace[RACED] = {"value": last[RACED], "site": {"place": p_, "sid": sid, "tag": tag, "ip": ip},
                        "why": f"the end field's prologue rewrites Byte[13] at once (ip130 2 -> 1) and again at its "
                               f"grant: the live read races; the last pre-cut write is {p_} e{sid} t{tag} ip{ip}'s "
                               f"{last[RACED]}"}
    return live, trace


def _landing(route, chain: list, end: int) -> dict:
    """4.3/5.3's landing: the route places, each crossing (a place's chain row, then the next place's entry row ip22),
    the last chain row (the last compared row), and the end row (the end place's e0 t0 ip22, the cut)."""
    by = {k["donor"]: k for k in chain}
    crossings = [{"from": p, "exit": _site(p, by[p]["sid"], by[p]["tag"], by[p]["ip"], by[p]["target"],
                                           by[p]["value"]),
                  "to": q, "enter": _site(q, 0, 0, 22, "Global.Bit[191]", 0)}
                 for p, q in zip(route, route[1:])]
    lastp = route[-1]
    return {"route_places": list(route), "crossings": crossings,
            "last": _site(lastp, by[lastp]["sid"], by[lastp]["tag"], by[lastp]["ip"], by[lastp]["target"],
                          by[lastp]["value"]),
            "end_row": _site(end, 0, 0, 22, "Global.Bit[191]", 0)}


def _interruptions(pins: list) -> list:
    """4.10: the registered interruption -- 159's forced monologue, its ``test`` READ off ip390's pinned text
    (:func:`monologue_test`), never typed."""
    text = next((p[4] for p in pins if p[:4] == [159, 16, 1, 390]), None)
    return [{"donor": 159, "visit": 3, "step": 0, "name": "the forced monologue", "test": monologue_test(text),
             "rows": [[159, 16, 1, 613], [159, 16, 1, 648], [159, 16, 1, 672]], "pages": [296, 297, 298, 299, 300],
             "why": "159 e16 t1 ip390 takes control the first tick he leaves |x| <= 1600 && z >= 800 (e11 lies wholly at "
                    "x <= -2208); its three stores are fixed values written with control off, after the step's first "
                    "loss and before its re-run (ip711 re-grants in place)"}]


def draft_predictions(campaign=None, *, end: int = END_FIELD) -> dict:
    """The registered claims (research/o7_design.md section 4). Every number was read off the stock bytes (the offline
    check re-derives each: O7-BUILD's pins, O7-KEYS with the start-scoped olds, the start read, the carried values, the
    route pins and their scans, O7-TEXT, O7-CENSUS at each entrance, O7-REGIONS, O7-GOALS), O4's build (C0), the live
    install or O4's campaign.toml (``campaign``); nothing is read from a run. ``end`` is THE ONE SWITCH (4.17): 164, or
    the fallback 163 -- every list filtered to the places before it, the end state recomputed. The rehearsals
    (o7_rehearse.py) settle the driver's numbers before the lead freezes them (7.3)."""
    members, names = chain_from_campaign(campaign)
    route = route_of(end)
    donors = route + (int(end),)
    rm = route_members(members, donors)
    writes = _filtered(_writes(), route)
    chain = _chain(route)
    pins = [p for p in route_pins() if p[0] in set(donors) | {70}]
    pattern = _pattern(route, writes, chain)
    end_state, end_trace = _end_state(pattern, 1190, writes + chain)
    start_music = dict(_key(154, 0, 0, 123, 113, "Global.Byte[13]", 0, ":=",
                            "154's ambient branch (Int16[9] < 0) from the warp's Byte[13] 1 (field 70's prologue :=1 at "
                            "ip130; the warp leaves 70 before ip475's :=2, which would take ip101 and window 56)"),
                       old=1)
    scoped = [x for x in start_scoped() if x["site"][0] in set(route)]
    reads = [x for x in start_reads() if x["site"][0] in set(route)]
    return {
        "version": 1,
        "what": f"O7: 154@1190 (warp, entrance 315; EVT_ALEX1_AC_ENT_2F) -> the balcony, the west flight, the ground, "
                f"the south door -> 158@300 -> 159@331 (the forced monologue) -> 160@332 -> 162@333 -> 163@341 (the "
                f"stair foot) -> the arrival in {end} at {CHAIN_SITES[route[-1]][4]}, SC 1190; stock vs the alxc disc-1 "
                f"chain as O4 deployed it (route members {rm[route[0]]}-{rm[int(end)]}; PLAN.md, O7) -- a US session",
        "rehearsals": [],                                   # 7.3: the lead's freeze names the rehearsal run dirs
        "rehearsal_fps": [],                                # 7.3 F14: the render rates the rehearsals met
        "order": ["S", "F", "S", "F", "S", "F"],
        "min_covered": 2,
        "rerun": {"max": 2, "stop_on": ["V19"]},
        # 4.12: estimates (~1.8 min a run); F8 replaces every number from R-FULL
        "budget": {"run_s": 600, "run_min_s": 300, "session_s": 3600, "settle_s": 1.0, "no_progress_s": 60,
                   "end_row_s": 10.0},
        "start": {"S": route[0], "F": rm[route[0]]},
        "entrance": 315,
        "scenario": 1190,
        "lang": SESSION_LANG,
        "end_field": int(end),
        "end_fields": [int(end)],
        "side_ends": {"S": [int(end)], "F": [rm[int(end)]]},
        "route": list(route),
        "visits": list(route),
        "stock_fields": list(donors),
        "members": {str(f): d for f, d in sorted(members.items())},
        "names": {str(f): n for f, n in sorted(names.items())},
        "text_block": TEXT_BLOCK,
        "text_blocks": list(TEXT_BLOCKS),
        "recovery": 4600,
        "cut_start": True,
        "start_first": _key(154, 0, 0, 26, 16, "Global.Bit[191]", 0, ":=",
                            "154's Main_Init: its first store (emitted same: a new site)"),
        "start_music": start_music,
        "start_scoped": scoped,
        "start_reads": reads,
        "carried": carried(),
        # SC 1190 = 0x04A6 (bytes 0 and 1); FieldEntrance 315 = 0x013B (bytes 2 and 3): FOUR rows (0.2 #1)
        "start_residue": [[0, 0, 166], [1, 0, 4], [2, 0, 59], [3, 0, 1]],
        "residue_after_start": [],
        "sc_bytes": [0, 1],
        "ladder": [],
        "entrance_bytes": [2, 3],
        "chain": chain,
        "writes": writes,
        "start_dependent": [],
        "naming": [],
        "error_path": _filtered(_error_path(), route),
        "forbidden_sites": _filtered(_forbidden_sites(), route),
        "dead": _filtered(_dead(), route),
        "inert": [{"donor": 154, "sid": 2, "tags": "*",
                   "why": "InitObject(2) only on the 304 branch L232: not instanced at 315 (its ip1520 Int16[2] := 316)"}]
        if 154 in route else [],
        "live_shared": [],
        "noise": [],
        "forbidden": [{"off_route": True, "cause": "walk",
                       "why": f"a write off the route: S, a place outside {list(route)} + [{end}]; F, a field that is "
                              f"neither a member whose donor is on the route nor F's own end field (real 154/158-{end} "
                              f"on F: an un-retargeted Field() or an engine id leak; 153/155/156/161/167 or "
                              f"31245/31247/31248/31253/31259 after a wrong door, backed by its V11 step row)"}],
        "landing": _landing(route, chain, int(end)),
        "end_state": end_state,
        "end_state_trace": end_trace,
        "interruptions": _interruptions(pins) if 159 in route else [],
        "static_objects": [{"donor": 154, "sid": 5, "name": "Dojebon", "tol": 30,
                            "why": "154 e5 t1 ip263 holds him while B_DISTANCEA < 3600 or Map.Byte[30] == 1; released, "
                                   "he patrols head-on along the west flight the walk takes. He stores nothing (e5 t1 "
                                   "holds no store), so a release moves no key: it is watched (O7Segment.drive's "
                                   "observe, keyed by PLACE -- 154 on S, member(154) on F: one 'seen' row per visit, "
                                   "his first published reading, and one 'moved' row the first time a reading leaves "
                                   "it by more than tol) and reported; a visit with no reading is UNOBSERVED, never "
                                   "'static'; in rehearsal a 'moved' row or an UNOBSERVED visit stops the freeze "
                                   "(F2)"}] if 154 in route else [],
        "beats": [s["beat"] for c in _table(route) for s in c["steps"]],
        "battles": [],
        "stop_pages": [{"match": "Env Play()",
                        "why": "window 56 of 154 (e0 t0 ip487), 158, 159, 160, 162, 163: Byte[13]/[14] arrived 2 or 9"}],
        "regions": _regions(route),
        "hotspots": {},
        "table": _table(route),
        "steps_default": {"attempts": 2, "interrupts": 1, "timeout_s": 20, "confirm_s": 4.0, "npcs": True,
                          "overlay_ok": False, "immediate": False, "settle": None, "lunge_ticks": 0, "tolerance": 45,
                          "min_depth": 40, "exit_wait_s": 5.0, "exit_slack": 40,
                          "climb": {"burst_frames": 30, "max_bursts": 80, "stall_bursts": 8}},
        "choices": [{"donor": None, "sc": None, "match": "want to skip", "pick": "default", "once": False,
                     "beat": None}],
        "witness": dict(WITNESS),
        "route_pins": pins,
        "route_mes": route_mes(),
        "route_build": route_build(donors),
        "pattern": pattern,
        "settings": json.loads(json.dumps(SETTINGS)),
        "override70": dict(OVERRIDE70),
        "derived": json.loads(json.dumps(DERIVED)),
        "engine": dict(ENGINE),
    }


# ======================================================================== the bytes' readers (pure)
_S16 = A._s16
_MONOLOGUE = re.compile(r"^SET\(\{Global\.Bit\[(\d+)\] const\(0\) B_EQ obj\(uid=255\)\.f\[0\] const\((\d+)\) B_LT "
                        r"obj\(uid=255\)\.f\[0\] const\((\d+)\) B_GT B_OROR obj\(uid=255\)\.f\[2\] const\((\d+)\) B_LT "
                        r"B_OROR B_ANDAND B_EXPR_END\}\)$")
_DOJEBON = re.compile(r"^SET\(\{B_PTR\(250\) B_DISTANCEA const\((\d+)\) B_LT (Map\.Byte\[\d+\]) const\((\d+)\) B_EQ "
                      r"B_OROR B_EXPR_END\}\)$")
_HEIGHT = re.compile(r"obj\(uid=250\)\.f\[1\] const\((\d+)\) B_LT\b")
_RELEASE = re.compile(r"(Map\.Byte\[\d+\]) const\((\d+)\) B_EQ obj\(uid=250\)\.f\[1\] const\((\d+)\) B_LT B_ANDAND")
_PLACE_SET = re.compile(r"^SET\(\{Map\.Int16\[(0|4)\] const\((\d+)\) B_LET B_EXPR_END\}\)$")


def monologue_test(text):
    """159's forced monologue, READ off e16 t1 ip390's pinned text (research/o7_design.md 0.2 #10, 4.10): ``Bit[n] == 0
    && (x < a || x > b || z < c)`` -> ``{"any_of": {"x_lt": a, "x_gt": b, "z_lt": c}, "unless_bit": n}``, the 2-byte
    constants signed (63936 -> -1600); None for any other shape."""
    m = _MONOLOGUE.match(text or "")
    if m is None:
        return None
    bit, a, b, c = (int(v) for v in m.groups())
    return {"any_of": {"x_lt": _S16(a), "x_gt": _S16(b), "z_lt": _S16(c)}, "unless_bit": bit}


def test_holds(test: dict, x, z, slack: float = 0.0) -> bool:
    """Whether (``x``, ``z``) satisfies a registered interruption's ``any_of`` test, each bound WIDENED by ``slack``
    toward the box (5.3 WALK (b): x < x_lt + slack, x > x_gt - slack, z < z_lt + slack); a missing position is False."""
    if x is None or z is None:
        return False
    a = (test or {}).get("any_of") or {}
    return (("x_lt" in a and float(x) < a["x_lt"] + slack) or ("x_gt" in a and float(x) > a["x_gt"] - slack)
            or ("z_lt" in a and float(z) < a["z_lt"] + slack))


def dojebon_test(text):
    """Dojebon's wait, READ off 154 e5 t1 ip263's pinned text (0.2 #11): ``B_PTR(250) B_DISTANCEA < r || Map.Byte[n]
    == v`` -> ``{"within": r, "latch": "Map.Byte[n] == v"}``; None for any other shape."""
    m = _DOJEBON.match(text or "")
    if m is None:
        return None
    return {"within": int(m.group(1)), "latch": f"{m.group(2)} == {int(m.group(3))}"}


def height_test(text):
    """A door's height branch, READ off its tag 2's pinned test (0.2 #8): ``obj(uid=250).f[1] const(c) B_LT`` -- f[1]
    < c, the published y (-f[1]) over -c -- -> ``{"y_gt": -c}`` (c signed: 65436 -> ``y_gt`` 100); None without one."""
    m = _HEIGHT.search(text or "")
    return None if m is None else {"y_gt": -_S16(int(m.group(1)))}


def release_height(pins, donor: int):
    """The PSX y above which (y < it) the camera code may set its latch back to 2 -- 154 e11 t1 ip128 ``Map.Byte[30] ==
    1 && obj(uid=250).f[1] < -500`` (then ip147 := 2: Dojebon's wait reads the distance alone) -- READ off the place's
    pins; None without one."""
    for p in pins or ():
        if p[0] == donor:
            m = _RELEASE.search(p[4])
            if m is not None:
                return float(_S16(int(m.group(3))))
    return None


def placement_of(pins, donor: int, sid: int):
    """An object's placement ``(x, z)``, READ off its t0's pinned ``Map.Int16[0]`` / ``[4]`` stores (154 e5 t0 ip14 /
    ip22: Dojebon at (-2700, -1700)); None without both."""
    got = {}
    for p in pins or ():
        if (p[0], p[1], p[2]) == (donor, sid, 0):
            m = _PLACE_SET.match(p[4])
            if m is not None:
                got[int(m.group(1))] = _S16(int(m.group(2)))
    return (float(got[0]), float(got[4])) if 0 in got and 4 in got else None


def pin_text(pred: dict, site) -> str | None:
    """The pinned text of ``[donor, sid, tag, ip]``, or None."""
    return next((p[4] for p in pred.get("route_pins") or () if list(p[:4]) == list(site)), None)


def seeded_places(pred: dict) -> list:
    """The PLACES whose table cell holds a step with ``basis`` "prior" (S19): 154, 158, 160, 162, 163 -- never 159."""
    return sorted({int(c["donor"]) for c in pred.get("table") or () for s in c["steps"] if s.get("basis") == "prior"})


def seeded_fields(pred: dict) -> list:
    """The fields whose basis a run SEEDS (S19, research/o7_design.md 1.3): every seeded place and each member whose
    donor is one -- 154, 158, 160, 162, 163 and 31246, 31250, 31252, 31254, 31255; never 159 or 31251 (calibrated).
    O7's ``start_run`` forgets every one at each run's start (0.2 #20)."""
    places = seeded_places(pred)
    members = {int(f): int(d) for f, d in (pred.get("members") or {}).items()}
    return places + sorted(f for f, d in members.items() if d in places)


def closures154(mesh) -> tuple:
    """154's two closure lists DERIVED from their definitions (research/o7_design.md 1.3, 2.4) on the OPEN triangles of
    ``mesh`` (stock 154's raw walkmesh, or a PlayerWalkmesh of it): step 0 -- every GROUND triangle (centroid PSX y >
    -150) whose XZ overlaps a non-ground one (each shrunk 2% toward its centroid, so a shared edge is no overlap), plus
    every non-ground one with centroid x > 450 and z > -3250 (the east flight: shut to every replan); step 1 -- every
    non-ground triangle. ``(step0, step1)``, sorted: 119 and 134 on stock 154 (the research's closures154.json)."""
    from ff9mapkit.content import pathfind
    pw = mesh if isinstance(mesh, pathfind.PlayerWalkmesh) else pathfind.PlayerWalkmesh(mesh)
    raw = pw.mesh
    wv, tris = raw.world_verts(), raw.tris
    live = [i for i in range(len(tris)) if i not in pw.closed]
    cent = {i: tuple(sum(wv[k][d] for k in tris[i].vtx) / 3 for d in range(3)) for i in live}
    ground = [i for i in live if cent[i][1] > -150]
    upper = [i for i in live if cent[i][1] <= -150]
    shrunk = {i: [(cent[i][0] + (wv[k][0] - cent[i][0]) * 0.98, cent[i][2] + (wv[k][2] - cent[i][2]) * 0.98)
                  for k in tris[i].vtx] for i in live}
    step0 = sorted({t for t in ground if any(_convex_overlap(shrunk[t], shrunk[u], touch=True) for u in upper)}
                   | {u for u in upper if cent[u][0] > 450 and cent[u][2] > -3250})
    return step0, sorted(upper)


def _convex(poly) -> bool:
    """Whether ``poly`` (``[(x, z)]``, 3 points or more) is convex: every turn the same way (collinear points allowed)."""
    n, turns = len(poly), set()
    for a in range(n):
        (ax, az), (bx, bz), (cx, cz) = poly[a], poly[(a + 1) % n], poly[(a + 2) % n]
        v = (bx - ax) * (cz - bz) - (bz - az) * (cx - bx)
        if v:
            turns.add(v > 0)
    return n >= 3 and len(turns) <= 1


def _convex_overlap(p, q, *, touch: bool = False) -> bool:
    """Whether two convex polygons ``p`` and ``q`` (``[(x, z)]``) overlap in XZ: no edge normal of either separates
    them. ``touch``: a shared edge or corner counts as overlap too."""
    for poly in (p, q):
        n = len(poly)
        for a in range(n):
            b = (a + 1) % n
            nx, nz = poly[a][1] - poly[b][1], poly[b][0] - poly[a][0]
            pa, qa = [nx * x + nz * z for x, z in p], [nx * x + nz * z for x, z in q]
            if (max(pa) < min(qa) or max(qa) < min(pa)) if touch else (max(pa) <= min(qa) or max(qa) <= min(pa)):
                return False
    return True


# ======================================================================== instancing without a dispatch (0.2 #3)
def instanced_at7(idx, entrance: int, *, items=None) -> set:
    """The entries Main_Init (e0 t0) instances at ``entrance`` -- ``{(kind, n)}`` (research/o7_design.md 0.2 #3): its
    entrance dispatch when it has one (:func:`o6_steiner.instanced_at6`: a SWITCH / SWITCHEX on ``Global.Int16[2]`` or
    an Int16[2] compare -- 154's ``SWITCH(304, L392, L232)``), else the SAME sound over-approximation with no case
    taken (158, 159, 160, 162 and 163 hold no entrance dispatch): every item reachable from the function's start, every
    branch and switch followed both ways -- so 160's ``Bit[3799] == 0``-gated InitObject(2) counts instanced (its
    stores forbidden sites, never inert). ``items`` (``[(ip, rel, eb-src text)]``, a seam) replaces the decode."""
    items = items if items is not None else A.O2Segment._items(idx, 0, 0)
    try:
        return C6.instanced_at6(idx, entrance, items=items)
    except ValueError:
        pass
    by_rel = {rel: i for i, (_ip, rel, _t) in enumerate(items)}
    seen, todo, out = set(), [0], set()
    while todo:
        i = todo.pop()
        while i is not None and 0 <= i < len(items) and i not in seen:
            seen.add(i)
            _ip, _rel, t = items[i]
            m = C4._INIT.match(t)
            if m:
                out.add((m.group(1).lower(), int(m.group(2))))
            if t.startswith("RET"):
                break
            if t.startswith("JMP("):
                i = by_rel.get(int(C4._LABEL.search(t).group(1)))
                continue
            if t.startswith(("JMP_IF(", "JMP_IFNOT(", "SWITCH(", "SWITCHEX(")):
                todo += [by_rel[int(x)] for x in C4._LABEL.findall(t) if int(x) in by_rel]
            i += 1
    return out


def has_dispatch(idx) -> bool:
    """Whether Main_Init dispatches on its entrance (:func:`o6_steiner.instanced_at6` reads one): only 154 on O7's route
    (0.2 #3)."""
    try:
        C6.instanced_at6(idx, 0)
        return True
    except ValueError:
        return False


def instanced_entries(idx, entrance: int, *, instanced=None) -> set:
    """Every entry that runs at ``entrance``: Main_Init's (0) and each one :func:`instanced_at7` instances."""
    return {0} | {n for _kind, n in (instanced or instanced_at7)(idx, entrance)}


def instanced_texts(idx, entrance: int, *, instanced=None) -> list:
    """``[(sid, tag, ip, text)]`` of every function of every entry instanced at ``entrance`` (4.14's scans)."""
    ents = instanced_entries(idx, entrance, instanced=instanced)
    return [x for x in C6.O6Segment._all_texts(idx) if x[0] in ents]


# ======================================================================== THE CARRIED VALUES and the olds (4.5)
def carried_from_segments(preds: list, *, writes=(), raw=None) -> tuple:
    """4.5's derivation (rev. 2, claim review #1; 0.2 #18): ``(carried {target: [raw start value, composed]},
    problems)`` over the FROZEN keys of ``preds`` (``[(name, predictions)]``, in segment order), each list (ladder,
    writes, chain) in its frozen order -- every frozen file lists a target's keys in route order:
      ``:=``, ``:=var`` and a key with no ``op`` (O1's v4 ladder) set; ``++``, ``&=`` and a ``|=`` on an in-segment
      ``prior`` take the key's value (computed in its segment); a ``|=`` on the ``newgame0`` prior OR-composes onto the
      running value; a ``start_dependent`` key carrying ``after.old`` (O6's two) first sets the running value to
      ``after.old`` -- refused unless it holds every bit of the running value (a ``|=`` target only gains bits) -- then
      composes. A registered noise key (``segment_trace.is_noise``) is skipped.
    Each segment is also REPLAYED ALONE from the raw start (``raw``, default :data:`START_VALUES`, every other target
    0) and checked against its own ``end_state`` for every target it writes and its end_state holds: a disagreement (a
    list order that contradicts the end_state) refuses. Then the targets ``writes`` names (O7's writes, chain and masked
    targets) are subtracted, and a target whose composed value equals the raw start's is not carried."""
    raw = dict(START_VALUES if raw is None else raw)
    values, problems = {}, []
    for name, p in preds:
        local = dict(raw)
        afters = {(k["donor"], k["sid"], k["tag"], k["ip"]): k["after"] for k in p.get("start_dependent") or ()
                  if isinstance(k.get("after"), dict) and "old" in k["after"]}
        touched = set()
        for lst in ("ladder", "writes", "chain"):
            for k in p.get(lst) or ():
                if not isinstance(k, dict) or not k.get("target"):
                    continue
                if ST.is_noise(ST.wkey(k), {"noise": p.get("noise") or []}):
                    continue
                t, op, v = k["target"], k.get("op"), int(k["value"])
                touched.add(t)
                compose = op == "|=" and k.get("prior") == "newgame0"
                local[t] = (int(local.get(t, 0)) | v) if compose else v
                if not compose:
                    values[t] = v
                    continue
                after = afters.get((k["donor"], k["sid"], k["tag"], k["ip"]))
                if after is not None:
                    old, cur = int(after["old"]), int(values.get(t, raw.get(t, 0)))
                    if (old | cur) != old:
                        problems.append(f"{name}: {A.label(k)}: after.old {old} does not hold every bit of the running "
                                        f"value {cur} (a |= target only gains bits)")
                    values[t] = old
                values[t] = int(values.get(t, raw.get(t, 0))) | v
        es = p.get("end_state") or {}
        for t in sorted(touched & set(es)):
            if local.get(t) != es[t]:
                problems.append(f"{name}: replayed alone from the raw start {t} reads {local.get(t)}, its end_state "
                                f"{es[t]}: its frozen list order contradicts its end_state")
    drop = set(writes)
    out = {t: [int(raw.get(t, 0)), v] for t, v in sorted(values.items())
           if t not in drop and v != int(raw.get(t, 0))}
    return out, problems


def prior_segments(here: Path = HERE) -> list:
    """``[(name, predictions)]`` of :data:`PRIOR_SEGMENTS`, read from the repo (the frozen O1-O6 files)."""
    return [(n, json.loads((Path(here) / n).read_text(encoding="utf-8"))) for n in PRIOR_SEGMENTS]


def o6_frozen(here: Path = HERE) -> dict:
    """O6's frozen predictions (:data:`O6_FROZEN`): the start-scoped olds are read off its ``pattern``."""
    return json.loads((Path(here) / O6_FROZEN).read_text(encoding="utf-8"))


def o7_targets(pred: dict) -> set:
    """The targets O7 writes -- its writes, its chain and the masked prologue pair -- subtracted from the carried."""
    return {k["target"] for k in list(pred.get("writes") or ()) + list(pred.get("chain") or ())} | set(MASKED_TARGETS)


def last_tuples(pred6: dict, targets) -> dict:
    """``{target: the LAST tuple on it in O6's frozen pattern}`` (its visits, in order; None when none). A target
    with a FLOATING tuple raises ValueError: its last place among the rows is not fixed (4.5)."""
    pat = pred6.get("pattern") or {}
    floating = {fl["tuple"][4] for fl in pat.get("floating") or ()}
    out = {}
    for t in targets:
        if t in floating:
            raise ValueError(f"{t}: a floating tuple in O6's pattern -- its last place is not fixed")
        last = None
        for v in pat.get("visits") or ():
            for tup in v:
                if tup[4] == t:
                    last = list(tup)
        out[t] = last
    return out


def olds_from_pattern(pred6: dict, targets) -> dict:
    """``{target: after.old}`` read off O6's FROZEN ``pattern`` (research/o7_design.md 4.5; claim review #3): the
    ``new`` of the LAST tuple on each target in its visits, in order -- what a true run leaves before O7's start (153
    ip57 Int16[9] -1, ip119 Byte[13] 0, e32 t1 ip1632 Byte[208] 1). A floating tuple on a target raises ValueError; a
    target the pattern never writes reads None."""
    return {t: (None if tup is None else tup[5]) for t, tup in last_tuples(pred6, targets).items()}


# ======================================================================== (h4): the release zone and its residual
def release_zone(mesh, closures, placement, within: float, *, above: float = -500.0, step: int = 16) -> list:
    """(h4)'s RELEASE ZONE (rev. 2, claim review #5): every point of a ``step``-u grid (multiples of ``step``) on the
    step's OPEN floor (``mesh`` raw or a PlayerWalkmesh of it, ``closures`` shut) where an open triangle stands above
    ``above`` (PSX y < it: the latch may read 2 there) and at least ``within`` from ``placement`` -- where ip263's test
    lets him go. Sorted ``[(x, z)]``."""
    from ff9mapkit.content import pathfind
    raw = getattr(mesh, "mesh", mesh)
    pw = pathfind.PlayerWalkmesh(raw, closed=list(closures))
    wv = raw.world_verts()
    px, pz = placement
    pts = set()
    for ti, t in enumerate(raw.tris):
        if ti in pw.closed:
            continue
        a, b, c = (wv[k] for k in t.vtx)
        tri = [(a[0], a[2]), (b[0], b[2]), (c[0], c[2])]
        x0, x1 = min(p[0] for p in tri), max(p[0] for p in tri)
        z0, z1 = min(p[1] for p in tri), max(p[1] for p in tri)
        for x in range(int(math.ceil(x0 / step)) * step, int(math.floor(x1 / step)) * step + 1, step):
            for z in range(int(math.ceil(z0 / step)) * step, int(math.floor(z1 / step)) * step + 1, step):
                if (x, z) in pts or not _in_tri(x, z, tri) or math.hypot(x - px, z - pz) < within:
                    continue
                if C5._tri_height(wv, t, x, z) < above:
                    pts.add((x, z))
    return sorted(pts)


def _in_tri(x, z, tri) -> bool:
    """(x, z) inside or on a triangle ``[(x, z)] * 3``."""
    s = [(tri[(i + 1) % 3][0] - tri[i][0]) * (z - tri[i][1]) - (tri[(i + 1) % 3][1] - tri[i][1]) * (x - tri[i][0])
         for i in range(3)]
    return not (min(s) < -1e-9 and max(s) > 1e-9)


def hazard_residual(points, polys, margin: float) -> list:
    """``[(x, z, gap)]``: the ``points`` farther than ``margin`` from every polygon of ``polys`` (the hazard and the
    step's avoided exits) -- (h4)'s residual, printed, its largest gap judged against :func:`h4_tolerance`."""
    from ff9mapkit.content import pathfind
    rings = [[(float(a), float(b)) for a, b in poly] for poly in polys]
    out = []
    for x, z in points:
        g = min((pathfind.poly_gap(x, z, ring) for ring in rings), default=math.inf)
        if g > margin:
            out.append((x, z, round(g, 1)))
    return out


def h4_tolerance() -> float:
    """H4_TOLERANCE (research/o7_design.md 1.3): KEEPOUT_MARGIN_W (no plan comes nearer an avoided region) +
    PROBE_HAZARD_PAD (a probe's own pad) -- 86 u."""
    from ff9mapkit.content import pathfind
    from harness.session import Session
    return float(pathfind.KEEPOUT_MARGIN_W + Session.PROBE_HAZARD_PAD)


def prior_agree_deg() -> float:
    """The first-move check's acceptance, acos(PRIOR_AGREE) in degrees (16.3: the calibration's own one-sided rule)."""
    from harness.session import Session
    return math.degrees(math.acos(Session.PRIOR_AGREE))


def route_chunk_half() -> float:
    """ROUTE_CHUNK_MAX / 2 (180 u): a hold's drift off its leg -- (h1)'s margin under Dojebon's circle."""
    from harness.session import Session
    return float(Session.ROUTE_CHUNK_MAX) / 2.0


# ======================================================================== a run's own rows (pure)
def cell_rows(log: list, c: dict) -> list:
    """The ``step`` rows of cell ``c`` in a run's driver log (its place and its visit), in order."""
    return [r for r in log or () if r.get("k") == "step" and r.get("donor") == c["donor"]
            and r.get("visit") == c.get("visit")]


def _row_end(r: dict):
    """A step row's END (5.3 WALK (c)): a ``walk`` row's ``frame``; another's ``lost.frame`` when its loss was read in
    the walk's field, else its ``flip_frame``, else its ``frame``."""
    if r.get("kind") == "walk":
        return r.get("frame")
    lost = r.get("lost") or {}
    if lost.get("frame") is not None and lost.get("field") == r.get("field"):
        return lost["frame"]
    return r.get("flip_frame") if r.get("flip_frame") is not None else r.get("frame")


def visit_windows(log: list, pred: dict) -> list:
    """WALK (c)'s windows (research/o7_design.md 5.3; claim review #4), ONE PER VISIT (each table cell): ``{"donor",
    "visit", "lo", "hi", "doors", "gaps"}`` -- ``lo`` its first step row's ``frame0``; ``hi`` its last done row's end
    (:func:`_row_end`; a visit with no done row, its last row's ``frame``); ``doors`` the exempt ``(sid, tag)`` -- each
    cross's target door's tag 2 (its rows follow its ExitField); ``gaps`` its registered interruption's -- ``{"lo": the
    interrupted row's lost.frame, "hi": the next attempt's frame0, "sites": the interruption's rows}``. A cell with no
    step row gives none. 154's window spans both its steps and the gap between them."""
    out = []
    regs = {(x["donor"], x["visit"], x["step"]): x for x in pred.get("interruptions") or ()}
    for c in pred.get("table") or ():
        rows = cell_rows(log, c)
        if not rows:
            continue
        done = [r for r in rows if r.get("outcome") == "done"]
        doors = sorted({(int(str(s["target"]).split(".e")[1]), 2) for s in c["steps"] if s.get("target")
                        and ".e" in str(s["target"])})
        gaps = []
        for n, _s in enumerate(c["steps"]):
            reg = regs.get((c["donor"], c.get("visit"), n))
            if reg is None:
                continue
            srows = [r for r in rows if r.get("n") == n]
            for i, r in enumerate(srows):
                if r.get("outcome") != "interrupted":
                    continue
                nxt = srows[i + 1] if i + 1 < len(srows) else None
                gaps.append({"lo": (r.get("lost") or {}).get("frame"), "hi": None if nxt is None else nxt.get("frame0"),
                             "sites": [tuple(s) for s in reg["rows"]]})
        out.append({"donor": c["donor"], "visit": c.get("visit"), "lo": rows[0].get("frame0"),
                    "hi": _row_end(done[-1]) if done else rows[-1].get("frame"), "doors": doors, "gaps": gaps})
    return out


def static_watch(pred: dict, log: list):
    """4.11's report-only WATCH (decision 4(d); claim review #6), the driver's ``observe`` hook: for each
    ``static_objects`` entry, keyed by PLACE (the poll's ``donor``: member(154) 31246 reads as 154 on F), one ``seen``
    row a visit -- the watched sid's first published reading (frame, x, z) -- and one ``moved`` row the first time a
    later reading of that visit leaves it by more than ``tol``. A visit is each arrival in a field of the place. A visit
    with no reading writes no row: the report reads it UNOBSERVED, never static. Rows ``{"k": "static", "what",
    "donor", "sid", "name", "field", "visit", "frame", "x", "z"}`` (``moved``: ``from`` and ``dist`` too), appended to
    ``log``."""
    objs = list(pred.get("static_objects") or ())
    state: dict = {}

    def observe(st, ctx) -> None:
        here = ctx.get("donor")
        for o in objs:
            s = state.setdefault((o["donor"], o["sid"]), {"field": None, "seen": None, "moved": False, "visit": 0})
            if here != o["donor"]:
                s["field"] = None                       # left the place: the next arrival is a new visit
                continue
            if s["field"] != ctx.get("field"):
                s.update(field=ctx.get("field"), seen=None, moved=False, visit=s["visit"] + 1)
            b = next((x for x in st.objects or () if x.get("sid") == o["sid"]), None)
            if b is None or b.get("x") is None or b.get("z") is None:
                continue
            x, z = round(float(b["x"]), 1), round(float(b["z"]), 1)
            row = {"k": "static", "donor": o["donor"], "sid": o["sid"], "name": o.get("name"),
                   "field": ctx.get("field"), "visit": s["visit"], "frame": st.frame, "x": x, "z": z}
            if s["seen"] is None:
                s["seen"] = (x, z)
                log.append({**row, "what": "seen"})
            elif not s["moved"]:
                d = math.hypot(x - s["seen"][0], z - s["seen"][1])
                if d > float(o.get("tol", 30)):
                    s["moved"] = True
                    log.append({**row, "what": "moved", "from": list(s["seen"]), "dist": round(d, 1)})
    return observe


def static_lines(log: list, pred: dict) -> list:
    """The static watch of one run as the report reads it: for each ``static_objects`` entry, each driver ``visit``
    row of its place in order (the k-th the watch's visit k), with that visit's ``seen`` row (None: UNOBSERVED) and its
    ``moved`` row (None: none). ``[(entry, visit row, seen, moved)]``; an entry whose place the run never reached gives
    ``(entry, None, None, None)``."""
    out = []
    rows = [x for x in log or () if x.get("k") == "static"]
    for o in pred.get("static_objects") or ():
        visits = [x for x in log or () if x.get("k") == "visit" and x.get("donor") == o["donor"]]
        if not visits:
            out.append((o, None, None, None))
            continue
        for k, v in enumerate(visits, 1):
            mine = [x for x in rows if x.get("donor") == o["donor"] and x.get("sid") == o["sid"] and x.get("visit") == k]
            out.append((o, v, next((x for x in mine if x.get("what") == "seen"), None),
                        next((x for x in mine if x.get("what") == "moved"), None)))
    return out


# ======================================================================== O7-CENSUS (pure but for the stock reader)
def store_census7(fields, stock, pred: dict, *, sites=None, classify=None, instanced=None) -> tuple:
    """O7-CENSUS's reader (research/o7_design.md 6.1): ``(problems, {field: Counter(class)}, proof)`` --
    :func:`o6_steiner.store_census6` (every gEventGlobal store site of each field registered, masked, start_first or in
    an inert function; THE INERT PROOF at each entrance the route enters the field by) with :func:`instanced_at7` as
    its instancing seam, then NO SHARED SCRIPT ON THE ROUTE: no ``RunSharedScript`` in an entry instanced at a route
    entrance (``live_shared`` is []). ``proof[field]`` gains ``dispatch`` (whether Main_Init dispatches on its
    entrance)."""
    instanced = instanced or instanced_at7
    bad, counts, proof = C6.store_census6(fields, stock, pred, sites=sites, classify=classify, instanced=instanced)
    try:
        ents = C5.visit_entrances(pred)
    except ValueError:
        return bad, counts, proof
    for fid in fields:
        idx = stock(fid)
        if idx is None:
            continue
        for ent in ents.get(fid) or ():
            try:
                texts = instanced_texts(idx, ent, instanced=instanced)
            except ValueError:
                continue
            for sid, tag, ip, t in texts:
                if t.startswith("RunSharedScript("):
                    bad.append(f"{fid} e{sid} t{tag} ip{ip}: {t} in an entry instanced at {ent} -- a shared script on "
                               f"the route (live_shared is [])")
        proof.setdefault(fid, {})["dispatch"] = has_dispatch(idx)
    return bad, counts, proof


# ======================================================================== O7-REGIONS (pure but for the stock reader)
def regions_problems7(pred: dict, stock, *, instanced=None) -> tuple:
    """O7-REGIONS's reader (research/o7_design.md 6.1, 4.15): ``(problems, roles Counter, gateway rows, hot-spots,
    hazards)``. An ``exit`` (key ``<donor>.e<sid>``): its points the first SetRegion of its (donor, entry); every
    ``scan_gateways`` row of that entry its (to, entrance) or one of its ``branches``' -- each branch's ``y_gt`` the
    height test read off the entry's pinned tag 2 (:func:`height_test`) -- its face gate as registered; instanced at the
    place's route entrance. A ``hazard`` (key ``<donor>.hazard.<name>``, never an ``e<sid>`` key, never an exit): a
    polygon of >= 3 points, its ``object`` an entry instanced at the place's route entrance whose ``guard`` site is
    pinned, and it lies in the ``avoid`` of every (donor, sc, visit, step) its ``guards`` name. Any other role FAILS.
    Every gateway row of the route fields and every region an entrance instances is registered; no hot-spot."""
    from ff9mapkit.eventscan import scan_gateways
    instanced = instanced or instanced_at7
    try:
        ents = C5.visit_entrances(pred)
    except ValueError as err:
        return [str(err)], Counter(), 0, 0, []
    regions = pred.get("regions") or {}
    table = {(c["donor"], c["sc"], c.get("visit")): c for c in pred.get("table") or ()}
    pins = pred.get("route_pins") or []
    bad, roles, hazards = [], Counter(), []
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
        idx = stock(donor)
        if idx is None:
            bad.append(f"{key}: no stock script for {donor}")
            continue
        route_ents = list(ents.get(donor) or ())
        if role == "hazard":
            if re.fullmatch(r"hazard\.\w+", rest) is None:
                bad.append(f"{key}: a hazard's key is <donor>.hazard.<name>, never an e<sid> key (no bytes pin it)")
                continue
            if len(reg.get("points") or ()) < 3:
                bad.append(f"{key}: a hazard is a polygon of at least 3 points")
            obj = reg.get("object") or {}
            at = [ent for ent in route_ents if ("object", obj.get("sid")) in inst(donor, ent)]
            if not at:
                bad.append(f"{key}: its object e{obj.get('sid')} is instanced at no route entrance of {donor} "
                           f"({route_ents})")
            if not obj.get("guard") or pin_text(pred, obj["guard"]) is None:
                bad.append(f"{key}: its object's guard {obj.get('guard')} is no route pin")
            if not reg.get("guards"):
                bad.append(f"{key}: guards no step")
            for g in reg.get("guards") or ():
                d, sc, visit, n = g
                steps = (table.get((d, sc, visit)) or {}).get("steps") or []
                if not 0 <= int(n) < len(steps):
                    bad.append(f"{key}: guards {g}, no such table step")
                elif key not in (steps[int(n)].get("avoid") or ()):
                    bad.append(f"{key}: not in the avoid of ({d}, {sc}, {visit}) step {n}")
            hazards.append((key, obj, list(reg.get("guards") or ())))
            continue
        if role != "exit":
            bad.append(f"{key}: role {role!r} is not one of exit, hazard (O7 registers no other)")
            continue
        m = re.fullmatch(r"e(\d+)", rest)
        if m is None:
            bad.append(f"{key}: an exit's key is <donor>.e<sid>")
            continue
        e = int(m.group(1))
        pts = A.O2Segment._first_region(idx, e)
        if pts != reg["points"]:
            bad.append(f"{key}: the bytes' first SetRegion is {pts}, frozen {reg['points']}")
        rows = gws.setdefault(donor, scan_gateways(idx.data))
        hit = [g for g in rows if g["entry"] == e]
        want = {(reg.get("to"), reg.get("entrance"))} | {(b.get("to"), b.get("entrance")) for b in reg.get("branches")
                                                          or ()}
        got = {(g["to"], g["entrance"]) for g in hit}
        if got != want:
            bad.append(f"{key}: scan_gateways gives {sorted(got)}, registered {sorted(want, key=str)}")
        if any(g["face_gate"] != reg.get("face_gate") for g in hit):
            bad.append(f"{key}: a face gate {[g['face_gate'] for g in hit]}, registered {reg.get('face_gate')}")
        if reg.get("branches"):
            ht = next((height_test(p[4]) for p in pins if (p[0], p[1], p[2]) == (donor, e, 2) and height_test(p[4])),
                      None)
            for b in reg["branches"]:
                if ht is None or ht["y_gt"] != b.get("y_gt"):
                    bad.append(f"{key}: the branch to {b.get('to')} at y_gt {b.get('y_gt')}, but the pinned tag 2 reads "
                               f"{ht}")
        if not [ent for ent in route_ents if ("region", e) in inst(donor, ent)]:
            bad.append(f"{key}: an exit no route entrance of {donor} ({route_ents}) instances")
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
                bad.append(f"{donor}.e{e}: a gateway (-> {[g['to'] for g in rows if g['entry'] == e]}) in the bytes, "
                           f"not registered")
        for ent in ents.get(donor) or ():
            for kind, n in sorted(inst(donor, ent)):
                if kind == "region" and f"{donor}.e{n}" not in regions:
                    bad.append(f"{donor}.e{n}: a region entrance {ent} instances, not registered")
        hs = A.O2Segment.hotspot_census(idx)
        nhot += len(hs)
        for sid, h in sorted(hs.items()):
            bad.append(f"hot-spot {donor} e{sid} ({h['x']}, {h['z']}): in the bytes; O7 registers none")
    return bad, roles, ngw, nhot, hazards


# ======================================================================== O7-GOALS (pure but for the mesh reader)
def _samples(pts: list, every: float = 5.0):
    """The polyline ``pts`` (``[(x, z)]``) sampled every ``every`` u, its ends included: ``(x, z)``."""
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        n = max(1, int(math.dist(a, b) // every))
        for k in range(n + (1 if i == len(pts) - 2 else 0)):
            yield a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n
    if len(pts) == 1:
        yield pts[0]


def _raw(cache: dict, walkmesh, donor: int):
    """The raw mesh of ``donor`` (``walkmesh(donor)``), read once per ``cache``."""
    key = ("raw", donor)
    if key not in cache:
        cache[key] = walkmesh(donor)
    return cache[key]


def _open_heights(wm, x, z) -> list:
    """The PSX heights of every OPEN triangle of PlayerWalkmesh ``wm`` under (x, z)."""
    raw = wm.mesh
    wv = raw.world_verts()
    return [C5._tri_height(wv, raw.tris[ti], x, z) for ti in raw.tris_at(x, z) if ti not in wm.closed]


def _plan(pred: dict, s: dict, raw, start, clearance: float, cache: dict):
    """route_to's own plan (0.2 #5): ``(PlayerWalkmesh, waypoints | None)`` -- route_avoiding from ``start`` to the
    step's goal round its ``avoid``, KEEPOUT_MARGIN_W, leave_wall, at ``clearance``, on the step's floor (its closures);
    memoised in ``cache`` per (start, goal, avoid, closures, clearance)."""
    from ff9mapkit.content import pathfind
    closed = SD.closed_tris(pred, s, raw)
    key = (id(raw), tuple(map(float, start)), tuple(map(float, s["goal"])), tuple(s.get("avoid") or ()), tuple(closed),
           float(clearance), json.dumps(SD.polys(pred, s.get("avoid"))))
    if key not in cache:
        wm = pathfind.PlayerWalkmesh(raw, closed=closed)
        wps = pathfind.route_avoiding(wm, tuple(map(float, start)), tuple(map(float, s["goal"])),
                                      SD.polys(pred, s.get("avoid")), pathfind.KEEPOUT_MARGIN_W, leave_wall=True,
                                      clearance=float(clearance))
        cache[key] = (wm, wps)
    return cache[key]


def goals_base7(pred: dict, walkmesh=None, *, cache: dict | None = None) -> tuple:
    """O7-GOALS' base (research/o7_design.md 6.1): O2's ``goals_check`` AT EACH STEP'S CLEARANCE -- ``(problems,
    lines)``: ``visits`` a walk on the route from the start place, every crossing's ``to`` where the order goes next;
    every step runnable (``segment_drive.step_of``); each goal on the step's floor (its closures) at least the step's
    clearance from a wall; a ``target``'s goal inside it at depth >= COLLISION_RADIUS_W; and a route from ``start`` to
    the goal round ``avoid`` at the step's clearance. Lines name each step ``(donor, sc, visit) #n`` (n 0-based, the
    hazards' ``guards`` index)."""
    from ff9mapkit import extract
    from ff9mapkit.scene import cam
    walkmesh = walkmesh or extract.stock_walkmesh
    cache = {} if cache is None else cache
    radius = float(cam.COLLISION_RADIUS_W)
    bad, lines = [], []
    order = list(pred.get("visits") or pred["route"])
    ends = list(pred.get("end_fields") or [pred["end_field"]])
    if not order or order[0] != pred["start"]["S"] or any(p not in pred["route"] for p in order):
        bad.append(f"visits {order}: not a walk on the route {pred['route']} from the start place {pred['start']['S']}")
    nexts = set(zip(order, order[1:])) | {(order[-1], e) for e in ends if order}
    for c in pred.get("table") or ():
        donor = c["donor"]
        raw = _raw(cache, walkmesh, donor)
        for n, s0 in enumerate(c["steps"]):
            lab = f"({donor}, {c['sc']}, {c.get('visit')}) #{n}"
            try:
                s = SD.step_of(pred, s0)
            except ValueError as err:
                bad.append(f"{lab}: {err}")
                continue
            if s["kind"] in ("cross", "leave_now") and (donor, s["to"]) not in nexts:
                bad.append(f"{lab}: its crossing leads to {s['to']}, where the route's order {order} never goes next "
                           f"from {donor}")
            if s.get("start") is None:
                bad.append(f"{lab}: no start")
                continue
            clear = float(s.get("clearance") or radius)
            wm, route = _plan(pred, s, raw, s["start"], clear, cache)
            gx, gz = (float(v) for v in s["goal"])
            wall = wm.distance_to_boundary(gx, gz) if wm.point_on_walkmesh(gx, gz) is not None else None
            if wall is None or wall < clear:
                bad.append(f"{lab}: goal ({gx:.0f}, {gz:.0f}) "
                           + ("off the floor" if wall is None else f"{wall:.0f}u from a wall, under its clearance "
                                                                   f"{clear:.0f}"))
            depth = None
            if s.get("target"):
                depth = SD.depth_in(SD.region(pred, s["target"])["points"], gx, gz)
                if depth is None or depth < radius:
                    bad.append(f"{lab}: goal depth {depth} in {s['target']} (want >= {radius:.0f})")
            elif s.get("until") is not None and not SD.until_ok(s["until"], gx, gz):
                bad.append(f"{lab}: goal ({gx:.0f}, {gz:.0f}) fails its until {s['until']}")
            if route is None:
                bad.append(f"{lab}: no route from ({float(s['start'][0]):.0f}, {float(s['start'][1]):.0f}) avoiding "
                           f"{s.get('avoid')} at clearance {clear:.0f}")
                continue
            pts = [tuple(map(float, s["start"]))] + [tuple(p) for p in route]
            length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
            lines.append(f"{lab} {s['kind']} wall " + ("off the floor" if wall is None else f"{wall:.0f}")
                         + ("" if depth is None else f" depth {depth:.0f}")
                         + f" route {len(route)} legs {length:.0f}u at {clear:.0f}")
    return bad, lines


def goals_extra7(pred: dict, walkmesh=None, *, cache: dict | None = None) -> tuple:
    """O7-GOALS (g1)-(g5) and (h1)-(h4) (research/o7_design.md 6.1), per step: ``(problems, lines)``.
      (g1) THE CLEARANCE: every step carries ``clearance``; one below ENGINE_RADIUS only where the plan at the radius
           fails (163: none at 120, a route at 110);
      (g2) THE EXITS: every OTHER registered exit of the place is in the step's ``avoid``; for a cross, each lies wholly
           outside its target -- the two convex polygons' interiors disjoint (:func:`_convex_overlap`, a shared edge or
           corner no overlap): crossing edges and either one inside the other fail, not only a vertex inside; the
           cross's goal stands inside its target (IsInQuad) on an open tri of the step's floor, and so does the planned
           route's first sample inside the target;
      (g3) THE WALK'S ARRIVAL: every point within ``tolerance`` of a walk's goal stands on open triangles of one level
           only, all ground (PSX y > the next step's door's ground bound, read off its pinned height test), and on an
           open triangle of the NEXT step's floor;
      (g4) THE BRANCH: every open triangle of a cross's floor touching its branched target is ground; on 154 the
           closure lists equal :func:`closures154`'s derivation;
      (g5) THE INTERRUPTION: the registered ``test`` fails at the step's ``start``, holds at every vertex of its target,
           and from the planned line's first point satisfying it a route to the goal exists at the step's clearance;
      (h1)-(h4) each hazard's guarded step: every sample of its planned route above the latch's release height lies
           within the wait's ``within`` - ROUTE_CHUNK_MAX / 2 of the object's placement; the step's basis "prior"; the
           hazard in its avoid; THE RELEASE ZONE (:func:`release_zone`) inside, or within H4_TOLERANCE of, the hazard or
           another avoided exit -- the residual beyond KEEPOUT_MARGIN_W printed (a regression pin of the polygon's
           coverage, never a reachability proof)."""
    from ff9mapkit import extract
    from ff9mapkit.content import doorface, pathfind
    walkmesh = walkmesh or extract.stock_walkmesh
    cache = {} if cache is None else cache
    pins = pred.get("route_pins") or []
    regs = pred.get("regions") or {}
    bad, lines = [], []
    hazards = {k: r for k, r in regs.items() if r.get("role") == "hazard"}
    guarded = {(g[0], g[1], g[2], g[3]): k for k, r in hazards.items() for g in r.get("guards") or ()}
    inter = {(x["donor"], x["visit"], x["step"]): x for x in pred.get("interruptions") or ()}

    def ground_bound(target):
        if not target or ".e" not in str(target):
            return None
        donor, e = int(str(target).split(".")[0]), int(str(target).split(".e")[1])
        ht = next((height_test(p[4]) for p in pins if (p[0], p[1], p[2]) == (donor, e, 2) and height_test(p[4])), None)
        return None if ht is None else -float(ht["y_gt"])
    for c in pred.get("table") or ():
        donor, visit = c["donor"], c.get("visit")
        raw = _raw(cache, walkmesh, donor)
        exits = [k for k, _p in SD.exit_regions(pred, donor)]
        steps = []
        for s0 in c["steps"]:
            try:
                steps.append(SD.step_of(pred, s0))
            except ValueError:
                steps.append(None)
        for n, s in enumerate(steps):
            if s is None:
                continue
            raw_step = c["steps"][n]
            lab = f"({donor}, {c['sc']}, {visit}) #{n}"
            clear = raw_step.get("clearance")
            # (g1)
            if clear is None:
                bad.append(f"{lab} (g1): no clearance")
                continue
            if float(clear) < ENGINE_RADIUS:
                _wm, at_r = _plan(pred, s, raw, s["start"], float(ENGINE_RADIUS), cache)
                if at_r is not None:
                    bad.append(f"{lab} (g1): clearance {clear} under the engine radius {ENGINE_RADIUS}, yet a route "
                               f"exists at {ENGINE_RADIUS}")
                else:
                    lines.append(f"{lab} (g1) no route at {ENGINE_RADIUS}, its {clear} the plan")
            wm, route = _plan(pred, s, raw, s["start"], float(clear), cache)
            pts = None if route is None else [tuple(map(float, s["start"]))] + [tuple(p) for p in route]
            # (g2)
            others = [k for k in exits if k != s.get("target")]
            miss = [k for k in others if k not in (s.get("avoid") or ())]
            if miss:
                bad.append(f"{lab} (g2): the registered exit(s) {miss} not in its avoid")
            if s["kind"] == "cross":
                tpts = SD.region(pred, s["target"])["points"]
                tring = [(float(a), float(b)) for a, b in tpts]
                for k in others:
                    ring = [(float(a), float(b)) for a, b in regs[k]["points"]]
                    if not (_convex(ring) and _convex(tring)):
                        bad.append(f"{lab} (g2): {k} or its target {s['target']} is not a convex polygon: wholly "
                                   f"outside is judged by separating edges, exact for convex regions alone")
                    elif _convex_overlap(ring, tring, touch=False):
                        inside = [p for p in regs[k]["points"] if pathfind._in_poly(float(p[0]), float(p[1]), tring)]
                        bad.append(f"{lab} (g2): {k} overlaps its target {s['target']} (no edge of either separates "
                                   f"them; its vertices inside the target {inside})")
                gx, gz = (float(v) for v in s["goal"])
                if not doorface.region_contains(gx, gz, tpts) or wm.point_on_walkmesh(gx, gz) is None:
                    bad.append(f"{lab} (g2): the goal ({gx:.0f}, {gz:.0f}) is not inside {s['target']} on an open tri "
                               f"of its floor")
                if pts is not None:
                    first = next(((x, z) for x, z in _samples(pts) if doorface.region_contains(x, z, tpts)), None)
                    if first is None or wm.point_on_walkmesh(first[0], first[1]) is None:
                        bad.append(f"{lab} (g2): the planned route's first sample inside {s['target']} {first} stands on "
                                   f"no open tri of its floor")
                # (g4)
                gb = ground_bound(s["target"])
                if (regs.get(s["target"]) or {}).get("branches") and gb is not None:
                    wv = raw.world_verts()
                    touch = [ti for ti, t in enumerate(raw.tris) if ti not in wm.closed and _convex_overlap(
                        [(wv[k][0], wv[k][2]) for k in t.vtx], tring, touch=True)]
                    high = [ti for ti in touch if any(wv[k][1] <= gb for k in raw.tris[ti].vtx)]
                    if high:
                        bad.append(f"{lab} (g4): {len(high)} of the {len(touch)} open tris touching {s['target']} stand "
                                   f"off the ground (PSX y <= {gb:.0f}): {high[:6]}")
                    else:
                        lines.append(f"{lab} (g4) {len(touch)} open tris of its floor touch {s['target']}, all ground")
            # (g3)
            if s["kind"] == "walk":
                nxt = steps[n + 1] if n + 1 < len(steps) else None
                gb = ground_bound((nxt or {}).get("target"))
                tol = float(s["tolerance"])
                gx, gz = (float(v) for v in s["goal"])
                disc = [(gx + dx, gz + dz) for dx in range(-int(tol), int(tol) + 1, 5)
                        for dz in range(-int(tol), int(tol) + 1, 5) if math.hypot(dx, dz) <= tol]
                wm_next = pathfind.PlayerWalkmesh(raw, closed=SD.closed_tris(pred, nxt, raw)) if nxt else None
                off, high, two, out_next = [], [], [], []
                for x, z in disc:
                    hs = _open_heights(wm, x, z)
                    if not hs:
                        off.append((x, z))
                        continue
                    if max(hs) - min(hs) > 1.0:
                        two.append((x, z))
                    if gb is not None and any(h <= gb for h in hs):
                        high.append((x, z))
                    if wm_next is not None and wm_next.point_on_walkmesh(x, z) is None:
                        out_next.append((x, z))
                probs = ([f"{len(off)} point(s) off its floor"] if off else []) \
                    + ([f"{len(two)} point(s) on two levels"] if two else []) \
                    + ([f"{len(high)} point(s) off the ground (PSX y <= {gb:.0f})"] if high else []) \
                    + ([f"{len(out_next)} point(s) off the next step's floor"] if out_next else []) \
                    + (["no ground bound: its next step's door holds no pinned height test"] if gb is None else [])
                if probs:
                    bad.append(f"{lab} (g3): within {tol:.0f} of the goal ({gx:.0f}, {gz:.0f}): " + "; ".join(probs))
                else:
                    lines.append(f"{lab} (g3) the goal disc ({len(disc)} points) single-level ground (PSX y > "
                                 f"{gb:.0f}), inside #{n + 1}'s floor")
            # (g4) the closure lists, from their definitions
            if donor == 154 and s.get("closed_tris"):
                derived = closures154(raw)
                if n < 2 and sorted(int(t) for t in s["closed_tris"]) != list(derived[n]):
                    bad.append(f"{lab} (g4): its {len(s['closed_tris'])} closures are not closures154's step {n} "
                               f"({len(derived[n])})")
            # (g5)
            reg = inter.get((donor, visit, n))
            if reg is not None:
                test = reg.get("test") or {}
                sx, sz = (float(v) for v in s["start"])
                tpts = SD.region(pred, s["target"])["points"] if s.get("target") else []
                miss = [p for p in tpts if not test_holds(test, p[0], p[1])]
                if test_holds(test, sx, sz):
                    bad.append(f"{lab} (g5): the test {test.get('any_of')} holds at the start ({sx:.0f}, {sz:.0f}): the "
                               f"spawn is outside the box")
                if miss or not tpts:
                    bad.append(f"{lab} (g5): the test {test.get('any_of')} fails at {s.get('target')}'s vertices {miss}")
                if pts is None:
                    bad.append(f"{lab} (g5): no planned line")
                else:
                    first = next(((x, z) for x, z in _samples(pts) if test_holds(test, x, z)), None)
                    redo = None if first is None else _plan(pred, s, raw, first, float(clear), cache)[1]
                    if redo is None:
                        bad.append(f"{lab} (g5): no route to the goal at {clear} from the line's first point past the "
                                   f"test {first}")
                    else:
                        lines.append(f"{lab} (g5) the test fails at ({sx:.0f}, {sz:.0f}), holds at {s.get('target')}'s "
                                     f"{len(tpts)} vertices; the re-run from ({first[0]:.0f}, {first[1]:.0f}) plans "
                                     f"{len(redo)} legs")
            # (h1)-(h4)
            hz = guarded.get((donor, c["sc"], visit, n))
            if hz is not None:
                obj = hazards[hz].get("object") or {}
                wait = dojebon_test(pin_text(pred, obj.get("guard")) or "")
                place_ = placement_of(pins, donor, int(obj.get("sid", -1)))
                above = release_height(pins, donor)
                if wait is None or place_ is None or above is None:
                    bad.append(f"{lab} (h): the wait {wait}, the placement {place_} or the release height {above} not "
                               f"read off the pins")
                    continue
                within = float(wait["within"])
                lim = within - route_chunk_half()
                far = None
                if pts is not None:
                    for x, z in _samples(pts):
                        if any(h < above for h in _open_heights(wm, x, z)):
                            d = math.hypot(x - place_[0], z - place_[1])
                            far = d if far is None or d > far else far
                if pts is None or far is None or far > lim:
                    bad.append(f"{lab} (h1): the planned route above PSX {above:.0f} reaches {far if far is None else round(far)} "
                               f"from the placement {place_}, over {lim:.0f}")
                else:
                    lines.append(f"{lab} (h1) {far:.0f} <= {lim:.0f}")
                if raw_step.get("basis") != "prior":
                    bad.append(f"{lab} (h2): basis {raw_step.get('basis')!r}, not 'prior' (a probe could release him)")
                else:
                    lines.append(f"{lab} (h2) basis prior")
                if hz not in (raw_step.get("avoid") or ()):
                    bad.append(f"{lab} (h3): {hz} not in its avoid")
                else:
                    lines.append(f"{lab} (h3) the hazard avoided")
                zone = release_zone(raw, SD.closed_tris(pred, s, raw), place_, within, above=above)
                polys = [regs[k]["points"] for k in (raw_step.get("avoid") or ()) if k in regs]
                res = hazard_residual(zone, polys, pathfind.KEEPOUT_MARGIN_W)
                worst = max((g for _x, _z, g in res), default=0.0)
                tol = h4_tolerance()
                span = (f"x {min(x for x, _z, _g in res)}..{max(x for x, _z, _g in res)}, z "
                        f"{min(z for _x, z, _g in res)}..{max(z for _x, z, _g in res)}") if res else "none"
                if worst > tol:
                    bad.append(f"{lab} (h4): the release zone ({len(zone)} points) leaves {len(res)} point(s) beyond "
                               f"{pathfind.KEEPOUT_MARGIN_W:.0f} of the hazard and its avoided exits ({span}), the largest "
                               f"gap {worst} > {tol:.0f}")
                else:
                    lines.append(f"{lab} (h4) the release zone ({len(zone)} points) covered but {len(res)} residual "
                                 f"point(s) ({span}), largest gap {worst} <= {tol:.0f}")
    return bad, lines


# ======================================================================== a trace, summarised (end PLACES)
def trace_summary(rows: list, pred: dict, *, side: str = "S", start_place: int | None = None, end_fields=None,
                  stock=None, scripts=None, log: list | None = None) -> dict:
    """One trace, summarised for a reader (research/o7_design.md 7.2; the rehearsal report and the dry run): O5's shape
    -- cut at its start row and at its first row in an END PLACE (``end_fields``, a stage's raw ids, turned into places
    through the members on F) -- with O7's crossings (each route place's chain row -> the next field row; the last
    place's -> the cut), the registered interruption's rows (their frames, in order), Byte[13]'s last pre-cut row (the
    end state's raced target) and each start read's row (159 ip290's ``old``)."""
    out = C5.trace_summary(rows, pred, side=side, start_place=start_place, end_fields=end_fields, stock=stock,
                           scripts=scripts, log=log)
    members = members_of(pred) if side == "F" else {}
    sp = start_place if start_place is not None else place(pred["start"][side], members)
    ends = list(end_fields) if end_fields is not None else ST.side_ends(pred, side)
    places = sorted({place(f, members) for f in ends})
    kept, _at, _pre = cut_at_start(rows, sp, members)
    kept, end = cut_at_end(kept, places, members)
    fm = T.FIELD_MODE

    def at(x, spec) -> bool:
        return (x.k == "w" and x.m == fm and place(x.fld, members) == spec["place"]
                and (x.sid, x.tag, x.ip, x.target, x.new) == (spec["sid"], spec["tag"], spec["ip"], spec["target"],
                                                              spec["value"]))
    lnd = pred.get("landing") or {}
    cut_row = next((x for x in rows if x.line == end), None) if end is not None else None
    crossings = []
    specs = [(cr["from"], cr["exit"]) for cr in lnd.get("crossings") or ()]
    if lnd.get("last"):
        specs.append((lnd["last"]["place"], lnd["last"]))
    for frm, ex in specs:
        i = next((j for j, x in enumerate(kept) if at(x, ex)), None)
        if i is None:
            crossings.append({"from": frm, "exit": None, "next": None})
            continue
        nxt = next((x for x in kept[i + 1:] if x.k == "w" and x.m == fm), None)
        crossings.append({"from": frm, "exit": A._row_text(kept[i]), "frame": kept[i].f,
                          "next": None if nxt is None else A._row_text(nxt),
                          "cut": None if nxt is not None or cut_row is None else
                          (A._row_text(cut_row) if cut_row.k == "w" else f"{cut_row.fld} byte {cut_row.byte}")})
    out["crossings"] = crossings
    mono = []
    for reg in pred.get("interruptions") or ():
        sites = [tuple(s) for s in reg.get("rows") or ()]
        for x in kept:
            if x.k == "w" and (place(x.fld, members), x.sid, x.tag, x.ip) in sites:
                mono.append({"site": f"{place(x.fld, members)} e{x.sid} t{x.tag} ip{x.ip}", "fld": x.fld, "f": x.f,
                             "old": x.old, "new": x.new})
    out["interruption_rows"] = mono
    raced = {}
    for t in (pred.get("end_state_trace") or {}):
        span = C6._span(t)
        hits = [x for x in kept if x.k in ("w", "r") and C6._row_span(x) & span]
        x = hits[-1] if hits else None
        raced[t] = None if x is None else {"row": (A._row_text(x) if x.k == "w" else f"r {x.fld} byte {x.byte}"),
                                           "fld": x.fld, "place": place(x.fld, members), "old": x.old, "new": x.new,
                                           "f": x.f}
    out["raced"] = raced
    reads = []
    for sr in pred.get("start_reads") or ():
        d, sid, tag, ip = sr["site"]
        x = next((x for x in kept if x.k == "w" and place(x.fld, members) == d and (x.sid, x.tag, x.ip, x.target)
                  == (sid, tag, ip, sr["target"])), None)
        reads.append({"site": f"{d} e{sid} t{tag} ip{ip}", "target": sr["target"], "want": sr["old"],
                      "old": None if x is None else x.old, "new": None if x is None else x.new})
    out["start_reads"] = reads
    return out


def _trace_report7(tr: dict) -> list:
    """The trace summary's lines (7.2): O5's, with O7's crossings, the interruption's rows, the raced target's last
    pre-cut row and the start reads."""
    if not tr:
        return ["    trace: none (untraced, or no rows)"]
    L = C5._trace_report(tr)
    for cr in tr.get("crossings") or ():
        L.append(f"      crossing from {cr.get('from')}: {cr.get('exit')} -> {cr.get('next') or cr.get('cut')}")
    L.append(f"      the interruption's rows {[(x['site'], x['f']) for x in tr.get('interruption_rows') or ()]}")
    for t, x in (tr.get("raced") or {}).items():
        L.append(f"      {t}'s last pre-cut row: " + ("none" if x is None else f"{x['row']} at fld {x['fld']} "
                                                                                 f"({x['old']} -> {x['new']})"))
    for x in tr.get("start_reads") or ():
        L.append(f"      start read {x['site']} {x['target']}: old {x['old']} (want {x['want']})")
    return L


# ======================================================================== O7 on the shared engine
class O7Segment(C6.O6Segment):
    """O7 on O6's segment (research/o7_design.md 1.3): its constants and check texts, the draft predictions (THE ONE
    SWITCH: :data:`END_FIELD`), the offline checks (O7-BUILD with the seven route members' pins, O7-KEYS with the
    start-scoped olds, the start read, THE CARRIED VALUES derived from O1-O6's frozen keys, the route pins and their
    scans, O7-TEXT strict on block 3 with route_mes, O7-CENSUS by :func:`instanced_at7`, O7-REGIONS with the hazard's
    role, O7-GOALS (g1)-(g5) and (h1)-(h4)), the preflight extras (O5's: no P-NAME) and in-game capabilities (over the
    seven route donors), the drive with its input witness and the static watch, every run reseeded (S19's forget), A-START
    scoped to visit 1 plus the start read, the all-run checks (FORBIDDEN, VOID-ASYM (a)-(d) over [place, sc, visit]
    cells), the core checks (START, NO-SC, CHAIN, RESIDUE, WRITES exact, NULL, STABLE, LANDING (a)-(e) over every
    crossing, WALK (a)-(d), PATTERN (a)-(b), MASKED, STATE (a)-(c), JOIN) and O7's report. The session loop, the cuts, the
    digest, the comparison and the verdict are the shared engine's."""

    tag = "O7"
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
    RUN_U_PER_TICK = RUN_U_PER_TICK
    STALE_TICKS = STALE_TICKS
    ENGINE_RADIUS = ENGINE_RADIUS
    PRIOR_SEGMENTS = PRIOR_SEGMENTS
    core_ids = ("START", "NO-SC", "CHAIN", "RESIDUE", "WRITES", "NULL", "STABLE", "LANDING", "WALK", "PATTERN", "MASKED",
                "STATE", "JOIN")
    titles = {
        "P-CAP": "P-CAP: the engine advertises the story trace at proto 1",
        "P-OBJECTS": "P-OBJECTS: the engine publishes the field's objects (s89): the walks plan with npcs on -- Dojebon "
                     "and the balcony soldiers in 154, the soldiers and Haagen in 159, Weimar and the soldier in 160",
        "P-LANG": "P-LANG: the running game's text is English(US), the language the keys, joins and text were checked "
                  "in (a US session)",
        "P-DONOR-LOG": "P-DONOR-LOG: this launch's Memoria.log shows the patchers ran and logged no ForkDonorPatch "
                       "collision for 154, 158, 159, 160, 162, 163 or 164",
        "P-LAUNCH": "P-LAUNCH: every stacked patch file, Memoria.ini and the engine DLLs are older than this launch, "
                    "and the DLLs are the pinned engine",
        "P-MANIFEST": "P-MANIFEST: the frozen members are the deployed chain's (o7_forks.json: O4's, deployed)",
        "P-DEPLOY": "P-DEPLOY: every member registered once under its name, and mapped once to its donor",
        "P-EB": "P-EB: every member's live .eb (7 languages) is the offline-checked build's (O4's)",
        "P-FLOOR": "P-FLOOR: every member's deployed walkmesh is its donor's (the walks' floors)",
        "P-STOCK": "P-STOCK: no mod folder overrides stock 154, 158, 159, 160, 162, 163 or 164",
        "P-TEXT3": "P-TEXT (block 3): every mod folder's text block 3 is each language's stock asset (strict)",
        "P-RECOVERY": "P-RECOVERY: the recovery field 4600 is registered in a mod folder",
        "P-DONOR": "P-DONOR: each of 154, 158, 159, 160, 162, 163 and 164 is forked by exactly one ForkDonorPatch row "
                   "in the stack, its member's",
        "P-SETTINGS": "P-SETTINGS: the battle, cheat, hack, control (PSXMovementMethod 1) and graphics settings and "
                      "[AnalogControl] (UseAbsoluteOrientation 3: the keys' basis) are the frozen ones (Memoria.ini read "
                      "the engine's way)",
        "P-PAD": "P-PAD: no XInput pad reads non-neutral (AlwaysCaptureGamepad = 1 reads a pad even unfocused)",
        "P-OVERRIDE": "P-OVERRIDE: field 70's New-Game override is the pinned one, shipped by one folder",
        "P-ENGINE": "P-ENGINE: the live x64 and x86 Assembly-CSharp.dll are the pinned engine",
        "BUILD": "O7-BUILD: every member's .eb, in all 7 languages, is its donor's in that language with only in-chain "
                 "Field() literals remapped; per language, the seven route members (154, 158, 159, 160, 162, 163, 164) "
                 "differ from their donors in exactly their in-chain Field() operands",
        "KEYS": "O7-KEYS: every registered key -- chain, writes, error path, forbidden and dead sites, start_first -- is "
                "a store of its variable at its ip in the donor's stock bytes, its op in the statement, its value "
                "computed; the start-scoped olds read off O6's frozen pattern, the start read, THE CARRIED VALUES "
                "derived from O1-O6's frozen keys, the route pins and their scans, the monologue's and Dojebon's tests "
                "read off their pins",
        "TEXT": "O7-TEXT: the build's text block 3 is each language's stock asset, read by its resource path -- STRICT: "
                "another language's copy fails -- and route_mes holds the monologue's pages and the stop page",
        "CENSUS": "O7-CENSUS: every gEventGlobal store site of 154, 158, 159, 160, 162 and 163 is registered (writes, "
                  "chain, masked, start_first, error path, forbidden, dead) or lies in an inert function proven not "
                  "instanced at the route's entrance (instanced_at7: 154's dispatch, the others' every Init), and no "
                  "shared script runs on the route",
        "REGIONS": "O7-REGIONS: every frozen region is the stock bytes' own (an exit with its height branches) or a "
                   "registered hazard guarding a pinned wait in its step's avoid, each instanced at the route's "
                   "entrances; every gateway row and every instanced region of the route registered, no hot-spot",
        "GOALS": "O7-GOALS: every step plans at its stated clearance (one under the engine radius only where the radius "
                 "plans nothing), every other exit avoided and outside its target, the walk's arrival single-level "
                 "ground, the cross's branch on the ground, the monologue before e11, and Dojebon's circle, basis, "
                 "hazard and release zone",
        "FROZEN": "O7-FROZEN: the predictions are the file the session recorded, unchanged",
        "COVER": "O7-COVER: at least {min_covered} covered runs a side",
        "FORBIDDEN": "O7-FORBIDDEN: no run carries a forbidden write its own driver log does not explain",
        "VOID-ASYM": "O7-VOID-ASYM: no game-caused VOID class on one side only, no side VOID in one class in every run, "
                     "no run VOID in a finding class (V19), and no game-observed V17 cause on one side only -- every "
                     "cell [place, sc, visit]",
        "START": "O7-START: every covered run starts at 154's Main_Init after only the warp's four residue rows, and 154 "
                 "takes its ambient branch from the warp's Byte[13] 1",
        "NO-SC": "O7-NO-SC: no row touches bytes 0-1 (SC) after the start: SC holds 1190 throughout",
        "CHAIN": "O7-CHAIN: bytes 2-3 (FieldEntrance) carry exactly the chain, in order, each from the last (the first "
                 "from 315)",
        "RESIDUE": "O7-RESIDUE: no unmasked residue after the start beyond the registered",
        "WRITES": "O7-WRITES: every covered run's story keys are EXACTLY the registered writes and chain",
        "NULL": "O7-NULL: STOCK ONLY and FORK ONLY are empty",
        "STABLE": "O7-STABLE: no key is written in some runs of a side and not others",
        "LANDING": "O7-LANDING: every row ran in its place's own field, each place loaded by the one before's chain "
                   "Field() with its first emitted row, 163's door's chain row the last, the end cut 164's first row "
                   "at the side's own end field, and no fork run left its members",
        "WALK": "O7-WALK: THE PAIRED-WALK LAW over the seven steps -- each done once with its evidence, 159's one "
                "interruption at the monologue's test, no row inside a visit's window but its door's and the "
                "monologue's three in their gap, and every seeded field's first move judged within acos(PRIOR_AGREE)",
        "PATTERN": "O7-PATTERN: the sink's emitted row pattern EXACTLY -- each of the six visits' emitted rows in "
                   "order, no c row",
        "MASKED": "O7-MASKED: the story-noise regions written are the same on both sides",
        "STATE": "O7-STATE: the state handed to 164 is the same: each target's emitted write history in order, the end "
                 "state read live (Byte[13] aside: 164's prologue races it), and Byte[13]'s last pre-cut row 163's "
                 "ip684 by place",
        "JOIN": "O7-JOIN: every script row joins a store in the bytes its field ran",
        "THROW": "O7-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
    }

    # -- the predictions --------------------------------------------------------------------------------------
    def draft(self) -> dict:
        return draft_predictions(Path(self.chain_dir) / "campaign.toml", end=END_FIELD)

    def freeze_problems(self, pred: dict, *, live_engine=None, path=None, prior=None) -> list:
        """7.3's refusals, pure but for the live engine read (``live_engine``, default the live DLLs') and the frozen
        O1-O6 files (``prior``, a seam): ``[problem]`` -- no ``witness``; a table step carrying a rehearsal overlay
        (``hold_stop``, ``page_stop``) or a typed ``stale_slack``; a step without ``clearance``; a hazard's guarded step
        (154 #0) without the hazard in its ``avoid`` or without ``basis`` "prior"; ``side_ends`` failing
        :func:`segment_trace.side_ends_of`; a non-empty ``battles``, ``naming``, ``start_dependent`` or
        ``pattern.floating``; Byte[13] (:data:`RACED`) in ``end_state``; a carried target in ``end_state``, or a
        ``carried`` that differs from :func:`carried_from_segments`; no ``start_reads``; an ``interruptions`` test that is
        not :func:`monologue_test`'s reading of its pinned text; an empty ``rehearsals`` or ``rehearsal_fps``; an
        ``engine`` that is not the live DLLs'; an existing file at ``path``."""
        bad = []
        try:
            if SD.witness_of(pred) is None:
                bad.append("no witness: a walk is the driver's own input (4.11)")
        except ValueError as err:
            bad.append(str(err))
        for c in pred.get("table") or ():
            for s in c.get("steps") or ():
                over = sorted(set(s) & REHEARSAL_OVERLAYS)
                if over:
                    bad.append(f"the table step {s.get('name')!r} carries a rehearsal overlay {over}")
                if "stale_slack" in s:
                    bad.append(f"the table step {s.get('name')!r} carries a typed stale_slack: the evidence's slack is "
                               f"DERIVED (4.10)")
                if s.get("clearance") is None:
                    bad.append(f"the table step {s.get('name')!r} carries no clearance (S18: every O7 step states it)")
        table = {(c["donor"], c["sc"], c.get("visit")): c for c in pred.get("table") or ()}
        for key, reg in (pred.get("regions") or {}).items():
            if reg.get("role") != "hazard":
                continue
            for d, sc, visit, n in reg.get("guards") or ():
                steps = (table.get((d, sc, visit)) or {}).get("steps") or []
                s = steps[int(n)] if 0 <= int(n) < len(steps) else None
                if s is None or key not in (s.get("avoid") or ()):
                    bad.append(f"({d}, {sc}, {visit}) step {n} does not avoid {key} (decision 4(d))")
                if s is None or s.get("basis") != "prior":
                    bad.append(f"({d}, {sc}, {visit}) step {n} carries no basis 'prior': a calibration probe could "
                               f"release the hazard's object (0.2 #11)")
        try:
            if ST.side_ends_of(pred) is None:
                bad.append("no side_ends: O7's F side ends in member(164)")
        except ValueError as err:
            bad.append(str(err))
        for name in ("battles", "naming", "start_dependent"):
            if pred.get(name):
                bad.append(f"{len(pred[name])} {name} row(s): O7 registers none")
        if (pred.get("pattern") or {}).get("floating"):
            bad.append("pattern.floating is not empty: every O7 order is the bytes' (4.16)")
        if RACED in (pred.get("end_state") or {}):
            bad.append(f"{RACED} in end_state: 164's prologue races it -- end_state_trace holds it (4.9)")
        car = (pred.get("carried") or {}).get("values") or {}
        held = sorted(set(car) & set(pred.get("end_state") or {}))
        if held:
            bad.append(f"carried target(s) {held} in end_state: a raw-start value claimed as an end state (4.5)")
        try:
            derived, problems = carried_from_segments(prior if prior is not None else prior_segments(),
                                                      writes=o7_targets(pred))
            if problems:
                bad.append("the carried derivation refuses: " + "; ".join(problems[:3]))
            elif derived != car:
                bad.append(f"carried differs from the derivation over the frozen O1-O6 keys: "
                           f"{_dict_diff(car, derived)}")
        except (OSError, ValueError, KeyError) as err:
            bad.append(f"the carried derivation could not run: {err}")
        if not pred.get("start_reads"):
            bad.append("no start_reads: 159 ip290's old is the start's Byte[8] (4.5)")
        for x in pred.get("interruptions") or ():
            want = monologue_test(pin_text(pred, [x["donor"], 16, 1, 390]) or "") if x.get("donor") == 159 else None
            if x.get("test") != want or want is None:
                bad.append(f"the interruption {x.get('name')!r}: its test {x.get('test')} is not monologue_test's "
                           f"reading of its pinned text ({want})")
        if not pred.get("rehearsals"):
            bad.append("no rehearsals: the freeze reads the lead's in-game rehearsal runs (7.3), none named")
        if not pred.get("rehearsal_fps"):
            bad.append("no rehearsal_fps: the render rates the rehearsals met (F14)")
        live = live_engine if live_engine is not None else C4.engine_shas(GAME)
        eng = pred.get("engine") or {}
        if any(eng.get(a) != live.get(a) for a in ("x64", "x86")):
            bad.append(f"the engine {str(eng.get('x64'))[:12]} is not the live DLLs' {str(live.get('x64'))[:12]}: the "
                       f"rehearsals ran another engine")
        if path is not None and Path(path).exists():
            bad.append(f"{Path(path).name} exists: the predictions are frozen. A new version is a new file")
        return bad

    def freeze(self, path=None, *, live_engine=None) -> str:
        """The freeze, once (research/o7_design.md 7.3): :meth:`freeze_problems` empty before anything is written --
        an existing file among them -- then the base's: LF, sorted keys, never over an existing file."""
        pred = self.draft()
        bad = self.freeze_problems(pred, live_engine=live_engine, path=Path(path or self.predictions))
        if bad:
            raise SystemExit("!! the draft is not freezable: " + "; ".join(bad))
        return ST.Segment.freeze(self, path)

    # -- offline ------------------------------------------------------------------------------------------------
    def offline_extra(self, pred: dict, build=None) -> list:
        stock = self.stock_source()
        return [self.text_check7(pred, build), self.census_check(pred, stock), self.regions_check(pred, stock),
                self.goals_check(pred, stock=stock)]

    def build_check(self, pred: dict, build=None, stock_lang=None) -> tuple:
        """O7-BUILD (6.1): the base rule (every member's .eb, every language its own donor's with only in-chain Field()
        literals remapped), then THE ROUTE MEMBERS' PINS per language (O5's machinery over O7's ``route_build``: the
        seven), then the chain's route members (derived) in the route's order."""
        stock_lang = stock_lang or ST.stock_lang()
        ok, what, detail = ST.Segment.build_check(self, pred, build, stock_lang)
        pok, pdetail = self.build_pins(pred, build, stock_lang)
        if not (ok and pok):
            return False, what, "; ".join(d for good, d in ((ok, detail), (pok, pdetail)) if not good)
        members = members_of(pred)
        donors = route_donors(pred)
        line = route_members_line(members, donors) if all(d in members.values() for d in donors) else ""
        return True, what, f"{detail}; {pdetail}" + (f"; {line}" if line else "")

    def keys_check(self, pred: dict, stock, lists=None, *, prior=None, o6=None, texts=None, scans=None) -> tuple:
        """O7-KEYS (6.1): (a) O2's machinery on a filtered copy -- the chain, the writes, ``error_path`` +
        ``forbidden_sites`` + ``dead``, ``start_first``; no ladder, noise or start-dependent key -- every key a store of
        its variable at its ip, its op in the statement, a compound value computed from its prior; (b) ``start_music``
        exactly one writes key; (c) each START-SCOPED old -- a writes key at its site, ``here`` [the start's value, the
        key's], ``after.run`` the class's :attr:`AFTER_RUN`, ``after.source`` present, ``after.old`` what
        :func:`olds_from_pattern` reads off O6's frozen pattern (``o6``, a seam) and ``after.value`` computed from it;
        (d) each START READ -- a writes key at its site of its target, its ``old`` the start's value, and no store of the
        target before it on the route; (e) THE CARRIED VALUES -- :func:`carried_from_segments` over the frozen O1-O6
        keys (``prior``, a seam) less O7's targets, no segment disagreeing with its own end_state, equal to the typed
        ``values``; none in ``end_state``; none with a registered store site; none stored or read in an entry instanced
        at a route entrance; the party typed and labelled; (f) THE ROUTE PINS and their scans
        (:meth:`route_pins_check`; ``texts`` / ``scans`` its seams); (g) the registered interruption's ``test`` equal to
        :func:`monologue_test` of its pinned ip390 and its ``rows`` writes keys; each hazard's guard read by
        :func:`dojebon_test`."""
        filtered = {**pred, "ladder": [], "noise": [], "start_dependent": [],
                    "forbidden_sites": list(pred["forbidden_sites"]) + list(pred["error_path"]) + list(pred["dead"])}
        ok, _what, detail = A.O2Segment.keys_check(self, filtered, stock)
        bad = [] if ok else [detail]
        writes = list(pred["writes"])
        site4 = {(k["donor"], k["sid"], k["tag"], k["ip"]): k for k in writes}
        sm = pred.get("start_music")
        if sm is not None:
            same = [k for k in writes if all(k[f] == sm[f] for f in ("donor", "m", "src", "sid", "tag", "ip", "off",
                                                                      "target", "value", "op"))]
            if len(same) != 1:
                bad.append(f"start_music ({sm['donor']} e{sm['sid']} t{sm['tag']} ip{sm['ip']} {sm['target']} := "
                           f"{sm['value']}) is {len(same)} writes keys, not one")
        # (c) the start-scoped olds
        olds_txt = []
        scoped = list(pred.get("start_scoped") or ())
        try:
            pred6 = o6 if o6 is not None else o6_frozen()
            tups = last_tuples(pred6, sorted({x["target"] for x in scoped}))
        except (OSError, ValueError) as err:
            pred6, tups = None, {}
            bad.append(f"the start-scoped olds: O6's frozen pattern unreadable: {err}")
        for x in scoped:
            site, t, here, after = tuple(x["site"]), x["target"], x.get("here") or [], x.get("after") or {}
            lab = f"start-scoped {site[0]} e{site[1]} t{site[2]} ip{site[3]} {t}"
            k = site4.get(site)
            if k is None or k["target"] != t:
                bad.append(f"{lab}: no writes key at its site")
                continue
            if list(here) != [START_VALUES.get(t, 0), k["value"]]:
                bad.append(f"{lab}: here {here}, the start gives [{START_VALUES.get(t, 0)}, {k['value']}]")
            if after.get("run") != self.AFTER_RUN:
                bad.append(f"{lab}: after.run {after.get('run')!r} is not the class's AFTER_RUN {self.AFTER_RUN!r}")
            if not after.get("source"):
                bad.append(f"{lab}: after carries no source (after.old is READ: say from where)")
            tup = tups.get(t)
            if pred6 is not None and (tup is None or after.get("old") != tup[5]):
                bad.append(f"{lab}: after.old {after.get('old')}, O6's frozen pattern's last tuple on {t} gives "
                           f"{None if tup is None else tup[5]} ({tup})")
            got = self._after_value({**k, "after": after}, stock)
            if got is None or got != after.get("value"):
                bad.append(f"{lab}: after.value {after.get('value')}, the bytes give {got} from after.old "
                           f"{after.get('old')}")
            if tup is not None:
                olds_txt.append(f"{tup[0]} e{tup[1]} t{tup[2]} +{tup[3]} {tup[5]}")
        # (d) the start reads
        order = [k for p in pred["route"] for k in writes + list(pred["chain"]) if k["donor"] == p]
        reads_txt = []
        for x in pred.get("start_reads") or ():
            site, t = tuple(x["site"]), x["target"]
            lab = f"start read {site[0]} e{site[1]} t{site[2]} ip{site[3]} {t}"
            k = site4.get(site)
            if k is None or k["target"] != t:
                bad.append(f"{lab}: no writes key of {t} at its site")
                continue
            if x.get("old") != START_VALUES.get(t, 0):
                bad.append(f"{lab}: old {x.get('old')}, the start leaves {START_VALUES.get(t, 0)}")
            i = next(j for j, y in enumerate(order) if y is k)
            before = [y for y in order[:i] if y["target"] == t]
            if before:
                bad.append(f"{lab}: {A.label(before[0])} stores {t} before it on the route: the start does not decide "
                           f"its old")
            reads_txt.append(f"{site[0]} ip{site[3]} {t.split('.', 1)[1]} old {x.get('old')}")
        # (e) THE CARRIED VALUES
        car = pred.get("carried") or {}
        typed = car.get("values") or {}
        try:
            segs = prior if prior is not None else prior_segments()
            derived, problems = carried_from_segments(segs, writes=o7_targets(pred))
        except (OSError, ValueError, KeyError) as err:
            segs, derived, problems = [], {}, [f"unreadable: {err}"]
        bad += [f"carried: the derivation refuses: {p}" for p in problems[:3]]
        if derived != typed:
            bad.append(f"carried: the typed values differ from the derivation over the frozen O1-O6 keys: "
                       f"{_dict_diff(typed, derived)}")
        held = sorted(set(typed) & set(pred.get("end_state") or {}))
        if held:
            bad.append(f"carried: {held} in end_state (a raw-start value claimed as an end state)")
        reg_sites = sorted({k["target"] for name in ("writes", "chain", "error_path", "forbidden_sites", "dead")
                            for k in pred.get(name) or ()} & set(typed))
        if reg_sites:
            bad.append(f"carried: {reg_sites} hold a registered store site on the route (neither written nor read)")
        try:
            ents = C5.visit_entrances(pred)
        except ValueError as err:
            ents = {}
            bad.append(str(err))
        used = []
        for fid in pred["route"]:
            idx = stock(fid)
            if idx is None:
                continue
            for ent in ents.get(fid) or ():
                for sid, tag, ip, t in ((scans or {}).get(fid) if scans is not None and fid in scans
                                        else instanced_texts(idx, ent)):
                    for tgt in typed:
                        if re.search(re.escape(tgt) + r"(?![\d\]])", t):
                            used.append(f"{fid} e{sid} t{tag} ip{ip} {tgt}")
        if used:
            bad.append(f"carried: read or stored in an entry instanced at a route entrance: {used[:4]}")
        party = car.get("party") or {}
        if not party.get("values") or not party.get("source"):
            bad.append("carried: the party is typed and labelled (values and source), never derived")
        # (f) the route pins and their scans
        pok, pdetail = self.route_pins_check(pred, stock, texts=texts, scans=scans)
        if not pok:
            bad.append(pdetail)
        # (g) the interruption's test and the hazard's wait, read off their pins
        tests = []
        for x in pred.get("interruptions") or ():
            want = monologue_test(pin_text(pred, [x["donor"], 16, 1, 390]) or "")
            if want is None or x.get("test") != want:
                bad.append(f"the interruption {x.get('name')!r}: its test {x.get('test')} is not its pinned ip390's "
                           f"reading {want}")
            for s in x.get("rows") or ():
                if tuple(s) not in site4:
                    bad.append(f"the interruption {x.get('name')!r}: its row {s} is no writes key")
            if want is not None:
                a = want["any_of"]
                tests.append(f"x < {a['x_lt']} || x > {a['x_gt']} || z < {a['z_lt']}, unless Bit[{want['unless_bit']}]")
        waits = []
        for key, reg in (pred.get("regions") or {}).items():
            if reg.get("role") != "hazard":
                continue
            w = dojebon_test(pin_text(pred, (reg.get("object") or {}).get("guard") or []) or "")
            if w is None:
                bad.append(f"{key}: its object's guard {(reg.get('object') or {}).get('guard')} is not a pinned wait "
                           f"(B_DISTANCEA < r || latch)")
            else:
                waits.append(f"{w['within']}, {w['latch']}")
        if bad:
            return False, self.title("KEYS"), "; ".join(bad)[:1600]
        m = re.match(r"(\d+) sites \((\d+) keys\), every op in its statement, (\d+) compound values", detail)
        nsites, nkeys, ncomp = (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (0, 0, 0)
        comp = [k for name in ("writes", "forbidden_sites", "error_path", "dead") for k in pred.get(name) or ()
                if k.get("op") in ("|=", "&=", "++")]
        return (True, self.title("KEYS"),
                f"{nkeys} keys over {nsites} distinct sites, every op in its statement, {ncomp} compound value(s) "
                f"computed from their priors (" + ", ".join(f"{k['donor']} e{k['sid']} t{k['tag']} ip{k['ip']} "
                                                          f"{k['op']} after {k.get('prior')}" for k in comp)
                + f"), none masked but start_first; start_music one writes key ({sm['donor']} ip{sm['ip']} from "
                  f"{sm.get('old')}); {len(scoped)} start-scoped olds, each a writes key, after.run "
                  f"{self.AFTER_RUN} (AFTER_RUN), after.old from O6's frozen pattern ({', '.join(olds_txt)}); "
                  f"{len(reads_txt)} start read(s) ({'; '.join(reads_txt)}, no earlier store on the route); "
                  f"{len(derived)} carried values derived from {len(segs)} frozen segments (no end-state "
                  f"disagreement), equal to the typed ones, none in end_state, none stored or read on the route; "
                  f"{pdetail}; the monologue's test read ({'; '.join(tests) or 'none registered'}); the hazard's wait "
                  f"read ({'; '.join(waits) or 'none registered'})")

    def route_pins_check(self, pred: dict, stock, *, texts=None, scans=None, mes=None) -> tuple:
        """O7-KEYS (f), THE ROUTE PINS (4.14): ``(ok, detail)`` -- every pin's instruction text EXACTLY the stock US
        script's (``texts``: ``{donor: {(sid, tag): {ip: text}}}``, a seam); then THE SCANS over each route field at its
        entrance, instanced entries only (:func:`instanced_texts`; ``scans``: ``{donor: [(sid, tag, ip, text)]}``, a
        seam): exactly one ``DefinePlayerCharacter``, a pinned one; no party op (:data:`PARTY_OPS`); every
        ``SetControlDirection``'s operand 1 the pinned ones' (one key basis: keys read twist.y); no ``Map.Bit[144]``
        store. ``route_mes`` is O7-TEXT's (:meth:`text_check7`)."""
        bad, n = [], 0
        cache: dict = {}
        for donor, sid, tag, ip, text in pred.get("route_pins") or ():
            n += 1
            if texts is not None and donor in texts:
                items = texts[donor].get((sid, tag)) or {}
            else:
                idx = stock(donor)
                if idx is None:
                    bad.append(f"{donor}: no stock script")
                    continue
                items = cache.setdefault((donor, sid, tag), {i: t for i, _rel, t in A.O2Segment._items(idx, sid, tag)})
            got = items.get(ip)
            if got != text:
                bad.append(f"{donor} e{sid} t{tag} ip{ip}: {got!r}, pinned {text!r}")
        try:
            ents = C5.visit_entrances(pred)
        except ValueError as err:
            return False, str(err)
        pins = pred.get("route_pins") or []
        for donor in pred["route"]:
            idx = stock(donor)
            for ent in ents.get(donor) or ():
                if scans is not None and donor in scans:
                    rows = list(scans[donor])
                elif idx is None:
                    continue
                else:
                    rows = instanced_texts(idx, ent)
                players = [(s, t, ip) for s, t, ip, x in rows if x == "DefinePlayerCharacter()"]
                pinned = {(p[1], p[2], p[3]) for p in pins if p[0] == donor and p[4] == "DefinePlayerCharacter()"}
                if len(players) != 1 or players[0] not in pinned:
                    bad.append(f"{donor} at {ent}: {len(players)} DefinePlayerCharacter in instanced entries "
                               f"{players[:3]}, want exactly the pinned one {sorted(pinned)}")
                party = [(s, t, ip, x) for s, t, ip, x in rows if any(op in x for op in PARTY_OPS)]
                if party:
                    bad.append(f"{donor} at {ent}: a party op in an instanced entry: e{party[0][0]} t{party[0][1]} "
                               f"ip{party[0][2]} {party[0][3][:60]!r}")
                want = {m.group(2) for p in pins if p[0] == donor
                        for m in [re.match(r"SetControlDirection\((\d+), (\d+)\)$", p[4])] if m}
                got = {m.group(2) for _s, _t, _ip, x in rows for m in [re.match(r"SetControlDirection\((\d+), (\d+)\)$",
                                                                               x)] if m}
                if not want or got - want:
                    bad.append(f"{donor} at {ent}: SetControlDirection operand 1 {sorted(got)}, the pinned "
                               f"{sorted(want)}: more than one key basis")
                stores = [(s, t, ip) for s, t, ip, x in rows
                          if x.startswith("SET({Map.Bit[144] ") and re.search(r"\bB_\w*LET\b", x)]
                if stores:
                    bad.append(f"{donor} at {ent}: a Map.Bit[144] store {stores[:2]} (the doors' op_22(1) skip)")
        return (not bad, "; ".join(bad[:6]) if bad else
                f"{n} route pins equal; per field one DefinePlayerCharacter instanced (Steiner's), no party op, one key "
                f"basis, no Map.Bit[144] store")

    def text_check7(self, pred: dict, build=None, stock_text=None, *, mes=None) -> tuple:
        """O7-TEXT (6.1): O4's ``text_check`` on block 3, STRICT, then ``route_mes`` on block 3's US source (``mes``,
        ``{mes id: source}``, a seam): each monologue page holds its text, and the stop page's mes holds every stop
        page's match."""
        ok, what, detail = self.text_check(pred, build, stock_text)
        rm = pred.get("route_mes") or {}
        if mes is None:
            from ff9mapkit import dialogue
            body = A.stock_text_assets(int(rm.get("block", TEXT_BLOCK)))[pred.get("lang", SESSION_LANG)]
            body = body.decode("utf-8", errors="replace") if isinstance(body, (bytes, bytearray)) else str(body)
            mes = {i: x.text for i, x in dialogue.parse_mes(body).items()}
        bad, parts = [], []
        for p in rm.get("monologue") or ():
            if str(p.get("holds")) not in str(mes.get(p.get("mes")) or ""):
                bad.append(f"mes {p.get('mes')} does not hold {p.get('holds')!r}")
            else:
                parts.append(f"{p['mes']} {p['holds']!r}")
        sp = rm.get("stop_page") or {}
        for p in pred.get("stop_pages") or ():
            if p["match"] not in str(mes.get(sp.get("mes")) or ""):
                bad.append(f"mes {sp.get('mes')} does not hold the stop page {p['match']!r}")
        if sp and str(sp.get("holds")) not in str(mes.get(sp.get("mes")) or ""):
            bad.append(f"mes {sp.get('mes')} does not hold {sp.get('holds')!r}")
        if bad:
            return False, what, "; ".join(([detail] if not ok else []) + bad)
        return ok, what, detail + "; mes " + ", ".join(parts) + f", {sp.get('mes')} {sp.get('holds')!r}"

    def census_check(self, pred: dict, stock, *, sites=None, classify=None, instanced=None) -> tuple:
        """O7-CENSUS (6.1): :func:`store_census7` over the route's stock fields -- each field's total and per-class
        counts printed as the census found them, the inert proof at each route entrance, the fields that hold no
        entrance dispatch named -- or each failure named."""
        fields = list(pred["route"])
        bad, counts, proof = store_census7(fields, stock, pred, sites=sites, classify=classify, instanced=instanced)
        if bad:
            return False, self.title("CENSUS"), f"{len(bad)} problem(s): " + "; ".join(bad[:8])
        short = {"error_path": "error", "forbidden_sites": "forbidden"}
        names = [nm for nm in CENSUS_LISTS7]
        per = []
        for f in fields:
            tot = sum(v for k, v in counts[f].items() if k != "unresolved")
            per.append(f"{f}: {tot} (" + ", ".join(f"{short.get(nm, nm)} {counts[f].get(nm, 0)}" for nm in names)
                       + ")")
        unres = sum(counts[f].get("unresolved", 0) for f in fields)
        parts = []
        for f in fields:
            x = sorted((i for i in pred.get("inert") or () if int(i["donor"]) == f), key=lambda i: int(i["sid"]))
            ents = (proof.get(f) or {}).get("entrances") or []
            if x:
                parts.append(f"{f} " + ", ".join("e" + str(i["sid"]) for i in x) + " not instanced at "
                             + " or ".join(str(e) for e in ents))
        plain = [f for f in fields if not (proof.get(f) or {}).get("dispatch")]
        gated = ""
        if 160 in fields:
            inst = (proof.get(160) or {}).get("instanced") or {}
            if any(("object", 2) in [tuple(v) for v in vs] for vs in inst.values()):
                gated = "; 160's Bit[3799]-gated InitObject(2) instanced"
        return (True, self.title("CENSUS"),
                "; ".join(per) + f"; {unres} unresolved; inert " + ("; ".join(parts) or "none")
                + (f"; {', '.join(map(str, plain))} hold no entrance dispatch (every Init reachable{gated})"
                   if plain else "") + "; no shared script instanced on the route")

    def regions_check(self, pred: dict, stock, *, instanced=None) -> tuple:
        """O7-REGIONS (6.1): :func:`regions_problems7`."""
        bad, roles, ngw, nhot, hazards = regions_problems7(pred, stock, instanced=instanced)
        if bad:
            return False, self.title("REGIONS"), "; ".join(bad[:6])
        n = sum(roles.values())
        branched = sorted(k for k, r in (pred.get("regions") or {}).items() if r.get("branches"))
        hz = "; ".join(f"{k} guarding {k.split('.')[0]} e{(o or {}).get('sid')}'s wait, in "
                       + ", ".join(f"({d}, {sc}, {v}) step {s}'s" for d, sc, v, s in g) + " avoid"
                       for k, o, g in hazards)
        return (True, self.title("REGIONS"),
                f"{n} regions ({roles['exit']} exit -- {len(branched)} with their balcony branches "
                f"({', '.join(branched)}) -- {roles['hazard']} hazard: {hz or 'none'}), {nhot} hot-spots, {ngw} "
                f"gateway rows all registered")

    def goals_check(self, pred: dict, walkmesh=None, *, stock=None) -> tuple:
        """O7-GOALS (6.1): :func:`goals_base7` (O2's base at each step's clearance), then :func:`goals_extra7` -- (g1)
        to (g5), (h1) to (h4) -- on one plan cache."""
        cache: dict = {}
        bad, lines = goals_base7(pred, walkmesh, cache=cache)
        xbad, xlines = goals_extra7(pred, walkmesh, cache=cache)
        if bad or xbad:
            return False, self.title("GOALS"), "; ".join(bad + xbad)[:1600]
        n = sum(len(c["steps"]) for c in pred.get("table") or ())
        return True, self.title("GOALS"), f"{n} steps: " + "; ".join(lines + xlines)

    # -- the live install (read-only) ---------------------------------------------------------------------------
    def preflight_extra(self, pred: dict, roots: list, *, manifest=None, pads=..., live_engine=None, game=None,
                        stock_text=None) -> list:
        """O5's extras (decision 7: no P-NAME, O7 registers no naming) -- P-TEXT (block 3, STRICT), P-RECOVERY,
        P-DONOR (the route's and the end's), P-SETTINGS (4.13's keys, [AnalogControl] among them), P-PAD, P-OVERRIDE,
        P-ENGINE. The seams are O5's."""
        return C5.O5Segment.preflight_extra(self, pred, roots, manifest=manifest, pads=pads, live_engine=live_engine,
                                            game=game, stock_text=stock_text)

    # -- the session --------------------------------------------------------------------------------------------
    def capabilities(self, g, *, pads=..., engine=None, live_engine=None) -> list:
        """O6's -- P-CAP, P-OBJECTS, P-LANG, P-DONOR-LOG, P-LAUNCH with the engine, P-PAD -- with P-DONOR-LOG over
        O7's :data:`ROUTE_DONORS` (154, 158, 159, 160, 162, 163, 164). ``pads``, ``engine`` and ``live_engine`` are
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

    def reseed(self, g, pred: dict) -> None:
        """S19's per-run forget (research/o7_design.md 0.2 #20): every seeded field's basis dropped
        (``g.forget_basis(*seeded_fields(pred))``), S and F, so each run seeds and judges its own first moves; a
        calibrated field (159, 31251) keeps its basis."""
        g.forget_basis(*seeded_fields(pred))

    def start_run(self, g, side: str, pred: dict, marks: dict | None = None) -> tuple:
        """Rev. 2: :meth:`reseed`, then the Segment's -- New Game, the trace armed, the raw warp."""
        self.reseed(g, pred)
        return ST.Segment.start_run(self, g, side, pred, marks)

    def drive(self, g, pred: dict, side: str, log: list, *, deadline: float, progress: dict | None = None) -> dict:
        """O4's drive -- the run-wide input witness -- plus the static watch (:func:`static_watch`, 4.11) as the
        driver's ``observe`` hook, keyed by place."""
        return SD.drive(g, pred, side, log, deadline=deadline, progress=progress, witness=C4.input_witness(g),
                        observe=static_watch(pred, log))

    # -- reading a session ---------------------------------------------------------------------------------------
    def why_void(self, rec: dict, r: dict, pred: dict) -> list:
        """O5's reasons through O6's (A-START scoped to visit 1: 154 is visited once; no naming), then THE START READ
        (research/o7_design.md 4.5, 5.1; rev. 2): a run's row at a ``start_reads`` site read with another ``old`` --
        159 ip290's Byte[8] not 125, the warp having left field 70 before its ip249 -- is A-START, by the driver: the
        start's problem, the run uncovered, never a failed PATTERN or STATE. Only when NOTHING in the run since its start
        touched the target's bytes before that row: an earlier row explains the old (a store of the run itself, which
        WRITES and PATTERN then judge on a covered run), never the start."""
        out = super().why_void(rec, r, pred)
        members = members_of(pred) if r["side"] == "F" else {}
        for sr in pred.get("start_reads") or ():
            d, sid, tag, ip = sr["site"]
            hit = next((x for x in r["rows"] if x.k == "w" and place(x.fld, members) == d
                        and (x.sid, x.tag, x.ip, x.target) == (sid, tag, ip, sr["target"])), None)
            if hit is None or hit.old == sr["old"]:
                continue
            span = C6._span(sr["target"])
            if any(x.line < hit.line and x.k in ("w", "r") and C6._row_span(x) & span for x in r["rows"]):
                continue
            out.append((f"{START_READ} {sr['target']} at {d} e{sid} t{tag} ip{ip} (fld {hit.fld}) reads old "
                        f"{hit.old}, not {sr['old']}, nothing earlier in the run touching it: the warp left field 70 "
                        f"before its store -- the start's", "A-START", "driver"))
        return out

    @staticmethod
    def _void_ids(r: dict) -> set:
        """The VOID classes VOID-ASYM reads (O2's), less the START READ's A-START (5.1; the dry run's
        byte8-early-warp-all-F): the instrument's start -- the warp's timing in field 70, the same harness on both sides
        -- never a structural fork deviation, so a side VOID in it in every run is VOID by COVER, never NOT PROVEN by
        (b). Every other class, A-START on 154's error path among them, reads as before."""
        return {(v.get("class"), tuple(v["cell"]) if v.get("cell") else None, v.get("by")) for v in r.get("void") or ()
                if not str(v.get("why") or "").startswith(START_READ)}

    # -- the checks ---------------------------------------------------------------------------------------------
    def core_checks(self, runs: list, cov: dict, pred: dict) -> list:
        covered = cov["S"] + cov["F"]
        c = self.comparison(cov, pred)
        return [self.start_check(covered, pred), self.no_sc_check(covered, pred),
                self.span_check("CHAIN", covered, pred, "entrance_bytes", "chain", pred["entrance"]),
                self.residue_check(covered, pred), self.writes_check(covered, pred), self.null_check(c, pred),
                self.stable_check(c, pred), self.landing_check(cov, pred), self.walk_check(covered, pred),
                self.pattern_check(covered, pred), self.masked_check(cov, pred), self.state_check(covered, pred),
                self.join_check(cov)]

    def landing_check(self, cov: dict, pred: dict) -> tuple:
        """O7-LANDING (5.3), over every covered run, each clause named in the detail:
          (a) every field-mode ``w``/``c`` row ran in its place's own field (member(place) on F, the place on S) and
              stands in a route place;
          (b) THE CROSSINGS: for each consecutive pair (P, Q) of the visits, the run holds P's chain row at P's field
              and the next field-mode ``w`` row after it is Q's entry row (Q e0 t0 ip22 ``Bit[191] := 0``) at Q's
              field; no row of P after Q's entry row;
          (c) the last field-mode ``w`` row before the end cut is ``landing.last`` (163 e2 t2 ip227), by place, and the
              run's ``end`` log row names the side's end field;
          (d) the end cut is a raw ``w`` row ``landing.end_row`` (164 e0 t0 ip22) at the side's end field;
          (e) every F digest records no seam and no seam key."""
        L = pred["landing"]
        route = set(L["route_places"])
        fm = T.FIELD_MODE
        bad = []

        def is_at(x, spec, members) -> bool:
            return (x.k == "w" and x.m == fm and place(x.fld, members) == spec["place"]
                    and (x.sid, x.tag, x.ip, x.target, x.new) == (spec["sid"], spec["tag"], spec["ip"], spec["target"],
                                                                   spec["value"]))

        def where(spec) -> str:
            return f"{spec['place']} e{spec['sid']} t{spec['tag']} ip{spec['ip']} {spec['target']}={spec['value']}"
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
            for cr in L.get("crossings") or ():
                ex, en = cr["exit"], cr["enter"]
                i = next((j for j, x in enumerate(ws) if is_at(x, ex, members) and x.fld == fld_of(ex["place"])), None)
                if i is None:
                    bad.append(f"{lab} (b): no {where(ex)} row at fld {fld_of(ex['place'])}")
                    continue
                nxt = next((x for x in ws[i + 1:] if x.m == fm), None)
                if nxt is None or not (is_at(nxt, en, members) and nxt.fld == fld_of(en["place"])):
                    bad.append(f"{lab} (b): the next field row after {ex['place']} ip{ex['ip']} is "
                               f"{A._row_text(nxt) if nxt is not None else 'none'}, not {where(en)} at fld "
                               f"{fld_of(en['place'])}")
                k = next((j for j, x in enumerate(ws) if is_at(x, en, members)), None)
                back = None if k is None else next((x for x in ws[k + 1:] if x.m == fm
                                                    and place(x.fld, members) == ex["place"]), None)
                if back is not None:
                    bad.append(f"{lab} (b): line {back.line} {A._row_text(back)}: place {ex['place']} written again "
                               f"after {en['place']} loaded")
            fws = [x for x in ws if x.m == fm]
            last = fws[-1] if fws else None
            if last is None or not is_at(last, L["last"], members):
                bad.append(f"{lab} (c): the last field row before the end cut is "
                           f"{A._row_text(last) if last is not None else 'none'}, not {where(L['last'])}")
            want_end = ST.side_ends(pred, r["side"])
            endrow = [x for x in r.get("log") or () if x.get("k") == "end"]
            if not endrow or endrow[-1].get("field") not in want_end:
                bad.append(f"{lab} (c): the run's end row names field "
                           f"{endrow[-1].get('field') if endrow else None}, not the side's end field {want_end}")
            cr = r.get("cut_row")
            lend = L["end_row"]
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
        crs = L.get("crossings") or []
        return (not bad, self.title("LANDING"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) every field row in its place's own field; (b) "
                                      f"{len(crs)} crossings ("
                                      + ", ".join(f"{c['from']} ip{c['exit']['ip']} -> {c['to']}" for c in crs)
                                      + f" e0 t0 ip22), no place written again; (c) {L['last']['place']} "
                                        f"ip{L['last']['ip']} last, the end row the side's own; (d) the cut at "
                                        f"{L['end_row']['place']} e0 t0 ip{L['end_row']['ip']} (S "
                                        f"{ST.side_ends(pred, 'S')}, F {ST.side_ends(pred, 'F')}); (e) no seam")

    def walk_check(self, covered: list, pred: dict) -> tuple:
        """O7-WALK (5.3; THE PAIRED-WALK LAW), over every covered run, each clause named:
          (a) per table step (its donor, visit and index): exactly one ``done`` row, the last of its rows, its EVIDENCE
              -- a ``walk``: in the side's field of the place, its ``to`` sample with control, within ``tolerance`` of
              the goal; a ``cross``: ``landed`` the side's field of ``to``'s place and its ``lost``, when read, in the
              walk's field within ``exit_slack`` of the target -- before it at most ``interrupts`` ``interrupted`` rows
              (none in a door) and at most ``attempts`` - 1 ``failed`` rows (none landed, none in a door);
          (b) THE REGISTERED INTERRUPTION: its step holds EXACTLY one ``interrupted`` row before the done row, its loss
              read in the side's field of its place, satisfying the ``test`` widened by the derived slack
              (STALE_TICKS x RUN_U_PER_TICK), no door;
          (c) THE VISIT WINDOW (:func:`visit_windows`): per visit, no ``w`` row from its first step row's ``frame0`` to
              its last done row's end but its target doors' own tag-2 rows and the registered interruption's rows --
              which must ALL lie, in order, inside the gap from the interrupted row's loss to the next attempt;
          (d) THE FIRST MOVES: per visit to a seeded place (:func:`seeded_places`), the visit's first step row's route
              ``basis`` "prior", exactly one of its rows carrying ``basis_check``, its angle at most
              acos(PRIOR_AGREE)."""
        from ff9mapkit.content import pathfind
        slack = float(self.STALE_TICKS * self.RUN_U_PER_TICK)
        agree = prior_agree_deg()
        regs = {(x["donor"], x["visit"], x["step"]): x for x in pred.get("interruptions") or ()}
        seeded = set(seeded_places(pred))
        bad = []
        for r in covered:
            lab = f"{r['side']}#{r['i']}"
            members = members_of(pred) if r["side"] == "F" else {}
            inv = {d: f for f, d in sorted(members.items(), reverse=True)}

            def fld_of(p):
                return inv.get(p, p) if members else p
            log = r.get("log") or []
            for c in pred.get("table") or ():
                fld = fld_of(c["donor"])
                rows_c = cell_rows(log, c)
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
                        else:
                            want = fld_of(step["to"])
                            if d.get("landed") != want:
                                probs.append(f"landed {d.get('landed')}, not {want}")
                            lost = d.get("lost")
                            if lost is not None:
                                pts = SD.region(pred, step["target"])["points"]
                                if lost.get("field") != fld:
                                    probs.append(f"its loss read in {lost.get('field')}, not the walk's field {fld}")
                                elif lost.get("x") is None or pathfind.poly_gap(
                                        float(lost["x"]), float(lost["z"]), [(float(a), float(b)) for a, b in pts]) \
                                        > float(step["exit_slack"]):
                                    probs.append(f"its loss at ({lost.get('x')}, {lost.get('z')}) beyond exit_slack "
                                                 f"{step['exit_slack']} of {step['target']}")
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
                    reg = regs.get((c["donor"], c.get("visit"), n))
                    if reg is not None:
                        probs = []
                        inter = [x for x in (rows[:done[0]] if len(done) == 1 else rows)
                                 if x.get("outcome") == "interrupted"]
                        if len(inter) != 1:
                            probs.append(f"{len(inter)} interrupted row(s) before the done row, want exactly one")
                        else:
                            lost = inter[0].get("lost") or {}
                            if lost.get("field") != fld:
                                probs.append(f"its loss read in {lost.get('field')}, not {fld}")
                            if not test_holds(reg.get("test"), lost.get("x"), lost.get("z"), slack):
                                probs.append(f"its loss at ({lost.get('x')}, {lost.get('z')}) outside the test "
                                             f"{(reg.get('test') or {}).get('any_of')} widened by {slack:.0f}")
                            if inter[0].get("door"):
                                probs.append(f"in a door {inter[0].get('door')}")
                        if probs:
                            bad.append(f"{lab} (b) {reg.get('name')}: " + "; ".join(probs))
            for w in visit_windows(log, pred):
                if w["lo"] is None or w["hi"] is None:
                    continue
                gaps = [g for g in w["gaps"] if g["lo"] is not None and g["hi"] is not None]
                sites = {s for g in w["gaps"] for s in g["sites"]}
                reg_rows = [x for x in r["rows"] if x.k == "w" and (place(x.fld, members), x.sid, x.tag, x.ip) in sites]
                for x in reg_rows:
                    if not any(g["lo"] <= x.f <= g["hi"] for g in gaps):
                        bad.append(f"{lab} (c): line {x.line} {A._row_text(x)} at frame {x.f}, the registered "
                                   f"interruption's, outside its gap {[(g['lo'], g['hi']) for g in gaps]}")
                        break
                order = [tuple(s) for s in next((g["sites"] for g in w["gaps"]), [])]
                seen_order = [(place(x.fld, members), x.sid, x.tag, x.ip) for x in reg_rows]
                if order and seen_order and [s for s in order if s in seen_order] != seen_order:
                    bad.append(f"{lab} (c): the registered interruption's rows out of order {seen_order}")
                hit = next((x for x in r["rows"] if x.k == "w" and w["lo"] <= x.f <= w["hi"]
                            and not (place(x.fld, members) == w["donor"] and (x.sid, x.tag) in set(map(tuple, w["doors"])))
                            and (place(x.fld, members), x.sid, x.tag, x.ip) not in sites), None)
                if hit is not None:
                    bad.append(f"{lab} (c): line {hit.line} {A._row_text(hit)} at frame {hit.f}, inside visit "
                               f"{w['visit']}'s window [{w['lo']}, {w['hi']}] ({w['donor']})")
            for c in pred.get("table") or ():
                if c["donor"] not in seeded:
                    continue
                rows = cell_rows(log, c)
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
                    bad.append(f"{lab} (d) ({c['donor']}, {c.get('visit')}): " + "; ".join(probs))
        nsteps = sum(len(c["steps"]) for c in pred.get("table") or ())
        return (not bad, self.title("WALK"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) the {nsteps} steps each done once with its evidence, "
                                      f"within its attempts and interruptions, none in a door; (b) "
                                      + ", ".join(f"{x['donor']}'s one interruption at its test (widened {slack:.0f}u)"
                                                  for x in pred.get("interruptions") or ())
                                      + f"; (c) no row inside a visit's window but its doors' and the interruption's, "
                                        f"in its gap; (d) every seeded visit ({', '.join(map(str, sorted(seeded)))}) "
                                        f"judged its first move within {agree:.1f} deg")

    def pattern_check(self, covered: list, pred: dict) -> tuple:
        """O7-PATTERN (5.3): the suppression model's prediction, EXACT, every covered run --
        :func:`o5_hallway.pattern_of` over the joined script rows of the route places before the cut, against
        ``pattern`` (:func:`o6_steiner.pattern_diff6` with ``floating`` []): (a) no ``c`` row, (b) each visit's
        emitted sequence in order."""
        pat = pred["pattern"]
        stock = self._stock_src()
        bad = []
        for r in covered:
            members = members_of(pred) if r["side"] == "F" else {}
            got = C5.pattern_of(r["rows"], pred, members, C5.stock_join(stock, members))
            bad += [f"{r['side']}#{r['i']} {p}" for p in C6.pattern_diff6(got, pat)]
        nv = [len(v) for v in pat["visits"]]
        return (not bad, self.title("PATTERN"),
                "; ".join(bad[:6]) or f"{len(covered)} runs: (a) {len(pat.get('counts') or ())} c rows, as frozen; (b) "
                                      f"{len(nv)} visits' emitted rows ({'+'.join(map(str, nv))} = {sum(nv)}) in order, "
                                      f"as frozen")

    def state_check(self, covered: list, pred: dict) -> tuple:
        """O7-STATE (5.3): O2's (a) -- each unmasked target's emitted history identical across covered runs, in order
        -- and (b) -- every covered run's live ``end_state`` the frozen one (Byte[13] not among it) -- then (c): for each
        ``end_state_trace`` target, the run's LAST pre-cut row on its bytes (``w`` or ``r``) is the registered site
        with the registered value, matched by PLACE at the side's own field of it (163 e0 t0 ip684 at real 163 on S, at
        member(163) 31255 on F -- a row at real 163 on F is no member's, so it does not match)."""
        ok, what, detail = A.O2Segment.state_check(self, covered, pred)
        bad = [] if ok else [detail]
        trace = pred.get("end_state_trace") or {}
        for r in covered:
            members = members_of(pred) if r["side"] == "F" else {}
            inv = {d: f for f, d in sorted(members.items(), reverse=True)}
            for t, spec in trace.items():
                s = spec["site"]
                span = C6._span(t)
                hits = [x for x in r["rows"] if x.k in ("w", "r") and C6._row_span(x) & span]
                x = hits[-1] if hits else None
                want_fld = inv.get(s["place"], s["place"]) if members else s["place"]
                if x is None or not (x.k == "w" and place(x.fld, members) == s["place"] and x.fld == want_fld
                                     and x.target == t and (x.sid, x.tag, x.ip) == (s["sid"], s["tag"], s["ip"])
                                     and x.new == spec["value"]):
                    got = ("none" if x is None else
                           (A._row_text(x) if x.k == "w" else f"r {x.fld} byte {x.byte} {x.old}->{x.new}")
                           + f" at fld {x.fld}")
                    bad.append(f"(c) {r['side']}#{r['i']}: {t}'s last pre-cut row is {got}, not {s['place']} e{s['sid']} "
                               f"t{s['tag']} ip{s['ip']} := {spec['value']}")
        if bad:
            return False, self.title("STATE"), "; ".join(bad[:6])
        return (True, self.title("STATE"),
                detail + "; (c) " + ", ".join(f"{t} last {s['site']['place']} e{s['site']['sid']} t{s['site']['tag']} "
                                              f"ip{s['site']['ip']} {s['value']} by place" for t, s in trace.items()))

    # -- the report ---------------------------------------------------------------------------------------------
    def scope_start7(self, pred: dict) -> str:
        """5.4's start-dependence line, RENDERED from the predictions (``start_scoped``, ``start_reads``, ``carried``,
        ``AFTER_RUN``), never a literal."""
        parts = []
        for x in pred.get("start_scoped") or ():
            d, sid, tag, ip = x["site"]
            a = x.get("after") or {}
            parts.append(f"{d} {'' if (sid, tag) == (0, 0) else f'e{sid} t{tag} '}ip{ip} {x['target'].split('.', 1)[1]} "
                         f"{x['here'][0]} -> {x['here'][1]} here, {a.get('old')} -> {a.get('value')} after")
        car = pred.get("carried") or {}
        vals = car.get("values") or {}
        carried = ", ".join(f"{t.split('.', 1)[1]} {v[0]}" for t, v in vals.items())
        after = ", ".join(str(v[1]) for v in vals.values())
        party = car.get("party") or {}
        reads = "; ".join(f"{x['site'][0]} ip{x['site'][3]} read {x['target'].split('.', 1)[1]} {x['old']} in every "
                          f"covered run (a warp before field 70's store would leave another: A-START, the run uncovered "
                          f"and named)" for x in pred.get("start_reads") or ())
        return (f"none in value or path: a raw warp into {pred['start']['S']}@{pred['entrance']} at SC "
                f"{pred['scenario']} from New Game, the same on both sides. START-SCOPED olds only (the value equal, "
                f"old/same not): " + "; ".join(parts) + f" the {self.AFTER_RUN} routes as driven. Carried, not claimed "
                f"(neither written nor read on O7; derived from the frozen {self.AFTER_RUN} keys): {carried} ({after} "
                f"after them), party {party.get('values', ['?'])[0]} ({', '.join(party.get('values') or [])}): "
                f"Steiner is the controlled character in every walked field whatever the party (each field's own "
                f"DefinePlayerCharacter). THE START READ: {reads or 'none'}. THE EMITTED PATTERN: each run is a fresh "
                f"epoch -- in a single-epoch chained run the earlier segments had emitted these sites, so they would be "
                f"c counts there: every frozen sequence, count and the cut are this start's")

    def report_extra(self, run_dir: Path, session: dict, pred: dict, runs: list, checks: list) -> list:
        """Report-only (research/o7_design.md 5.4): the scope (start dependence, the end state, the walks, settings and
        engine, the language), the walks per run per step, the monologue per run, Dojebon per run (UNOBSERVED when a
        visit holds no reading), the pattern per run, the end state (live and the trace's), the session's end and
        ``stopped``, O2's sections (VOID reasons per side, masked counts, forbidden hits, P-TEXT), the re-runs held."""
        trace = pred.get("end_state_trace") or {}
        L = ["", "Scope (a US session):", "  start dependence -- " + self.scope_start7(pred),
             "  the end state -- " + SCOPE_END_STATE + "".join(
                 f", {s['site']['place']} e{s['site']['sid']} t{s['site']['tag']} ip{s['site']['ip']} ({s['value']})"
                 for s in trace.values())]
        clears = sorted({(c["donor"], s.get("clearance")) for c in pred.get("table") or () for s in c["steps"]})
        under = [f"{d}'s {cl}" for d, cl in clears if cl is not None and float(cl) < ENGINE_RADIUS]
        checks_ = [((x.get("route") or {}).get("basis_check") or {}).get("angle") for r in runs for x in r.get("log") or ()
                   if x.get("k") == "step" and (x.get("route") or {}).get("basis_check")]
        worst = max((float(a) for a in checks_ if a is not None), default=None)
        L.append(f"  the walks -- every step planned at its stated clearance ({ENGINE_RADIUS}; "
                 + (", ".join(under) or "none under") + ": no route at the engine radius) and, in "
                 + ", ".join(map(str, seeded_places(pred))) + ", on the exact prior basis, seeded afresh every run (no "
                 f"calibration probe; every run's first move in each checked within {prior_agree_deg():.1f} deg: O7-WALK "
                 f"(d); the worst read {worst if worst is None else round(worst, 2)}); the others calibrated once a "
                 f"launch per side")
        st = (session.get("install") or {}).get("settings")
        eng = [d for _ok, _w, d in self._recorded(session, "P-ENGINE")]
        L.append("  settings and engine -- " + (json.dumps(st, sort_keys=True) if st is not None else "not recorded")
                 + "; derived -- " + "; ".join(f"{k} {v.get('value')} ({v.get('why')})"
                                               for k, v in (pred.get("derived") or {}).items())
                 + "; engine -- " + (eng[-1] if eng else json.dumps((session.get("install") or {}).get("engine"))))
        L.append("  language -- " + self.scope_lang(session))
        L.append("")
        L.append("The walks, per run, per step (outcome, the grant sample, basis and basis_check, clearance, the route "
                 "record, the loss, the landing and flip):")
        for r in runs:
            L += self._walk_lines7(r)
        L.append("")
        L.append("The monologue, per run (the interrupted row's loss, the pages, the three rows' frames, the re-run):")
        stock = self._stock_src()
        for r in runs:
            L += self._monologue_lines(r, pred)
        L.append("")
        L.append("The static watch, per run (the seen row -- the first reading in the place's field -- and any moved "
                 "row; UNOBSERVED when a visit holds no reading):")
        for r in runs:
            L += self._static_lines(r, pred)
        L.append("")
        L.append("The pattern, per run (emitted rows per visit, the c rows; O7-PATTERN's first difference):")
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
            L.append(f"  {r['side']}#{r['i']}: live {json.dumps(live, sort_keys=True) if live is not None else 'not read'};"
                     f" trace {'; '.join(parts) or 'none'} (its live read raced: never compared)")
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
    def _walk_lines7(r: dict) -> list:
        lab = f"  {r['side']}#{r['i']}:"
        rows = [x for x in r.get("log") or () if x.get("k") == "step"]
        if not rows:
            v = (r.get("rec") or {}).get("v")
            return [f"{lab} no step row" + (f" (the run VOID {v})" if v else "")]
        out = []
        for s in rows:
            fr, lost, rt = s.get("from") or {}, s.get("lost") or {}, s.get("route") or {}
            bc = rt.get("basis_check") or {}
            out.append(f"{lab} ({s.get('donor')}, visit {s.get('visit')}) #{s.get('n')} {s.get('kind')} attempt "
                       f"{s.get('attempt')} {s.get('outcome')}: from frame {fr.get('frame')} ({fr.get('x')}, "
                       f"{fr.get('z')}); basis {rt.get('basis') or 'calibrated'}"
                       + (f", basis_check {bc.get('angle')} deg moved {bc.get('moved')}" if bc else "")
                       + f"; clearance {s.get('clearance')}; legs {rt.get('route')} replans {rt.get('replans')} waits "
                         f"{rt.get('waits')} pushes {rt.get('pushes')} blockers {rt.get('blockers')} frozen "
                         f"{rt.get('frozen')} boxed {rt.get('boxed')}; loss frame {lost.get('frame')} in "
                         f"{lost.get('field')} ({lost.get('x')}, {lost.get('z')}); landed {s.get('landed')} flip "
                         f"{s.get('flip_frame')}; fps {(rt.get('fps') or {}).get('fps') if isinstance(rt.get('fps'), dict) else rt.get('fps')}"
                       + (f"; door {s.get('door')}" if s.get("door") else "")
                       + (f" -- {s.get('why')}" if s.get("why") else ""))
        return out

    @staticmethod
    def _monologue_lines(r: dict, pred: dict) -> list:
        lab = f"  {r['side']}#{r['i']}:"
        out = []
        members = members_of(pred) if r["side"] == "F" else {}
        for reg in pred.get("interruptions") or ():
            c = {"donor": reg["donor"], "visit": reg["visit"]}
            rows = [x for x in cell_rows(r.get("log") or [], c) if x.get("n") == reg["step"]]
            inter = [x for x in rows if x.get("outcome") == "interrupted"]
            sites = [tuple(s) for s in reg.get("rows") or ()]
            tr = [(x.ip, x.f) for x in r.get("rows") or () if x.k == "w"
                  and (place(x.fld, members), x.sid, x.tag, x.ip) in sites]
            pages = monologue_pages((r.get("outcome") or {}).get("pages"), pred, reg)
            want = list(reg.get("pages") or ())
            if not rows:
                out.append(f"{lab} {reg['name']}: no step row")
                continue
            lost = (inter[0].get("lost") or {}) if inter else {}
            redo = rows[rows.index(inter[0]) + 1] if inter and rows.index(inter[0]) + 1 < len(rows) else None
            out.append(f"{lab} {reg['name']}: {len(inter)} interrupted row(s); the loss frame {lost.get('frame')} at "
                       f"({lost.get('x')}, {lost.get('z')}) in {lost.get('field')}; its rows (ip, frame) {tr}; the "
                       f"re-run from frame {None if redo is None else redo.get('frame0')} at "
                       f"{None if redo is None else (redo.get('from') or {}).get('x')}, "
                       f"{None if redo is None else (redo.get('from') or {}).get('z')} -> "
                       f"{None if redo is None else redo.get('outcome')}"
                       + (f"; its pages ({len(pages)} of {len(want)}) {[p[:24] for p in pages]}" if pages
                          else f"; none of its pages {want} listed"))
        return out or [f"{lab} no interruption registered"]

    @staticmethod
    def _static_lines(r: dict, pred: dict) -> list:
        lab = f"  {r['side']}#{r['i']}:"
        out = []
        for o, v, seen, moved in static_lines(r.get("log") or [], pred):
            if v is None:
                out.append(f"{lab} {o.get('name')} (e{o['sid']}): its place {o['donor']} never visited")
                continue
            out.append(f"{lab} {o.get('name')} (e{o['sid']}) visit {v.get('visit')} in {v.get('field')}: "
                       + ("UNOBSERVED (no reading: the watch could not have seen a release)" if seen is None else
                          f"seen at frame {seen['frame']} ({seen['x']}, {seen['z']})")
                       + ("" if moved is None else f"; MOVED at frame {moved['frame']} to ({moved['x']}, {moved['z']}), "
                                                   f"{moved['dist']}u from its first reading"))
        return out or [f"{lab} no static object registered"]

    @staticmethod
    def _pattern_lines(r: dict, pred: dict, stock) -> list:
        lab = f"  {r['side']}#{r['i']}:"
        if not r.get("rows"):
            return [f"{lab} no trace rows"]
        members = members_of(pred) if r["side"] == "F" else {}
        got = C5.pattern_of(r["rows"], pred, members, C5.stock_join(stock, members))
        out = [f"{lab} emitted per visit {[f'{x[0][0]}x{len(x)}' for x in got['visits']]}; c rows "
               f"{[(c[0], f'e{c[1]} t{c[2]} +{c[3]}', c[4], c[5], c[6]) for c in got['counts']]}"]
        diff = C6.pattern_diff6(got, pred["pattern"])
        if diff:
            out.append(f"{lab} O7-PATTERN's first difference: {diff[0]}")
        return out

    # -- the CLI ------------------------------------------------------------------------------------------------
    def add_arguments(self, ap) -> None:
        ap.add_argument("--draft", action="store_true", help="print the draft predictions as JSON")
        ap.add_argument("--rehearsal-report", metavar="RUN_DIR",
                        help="print an o7_rehearse.py launch's record, stage by stage and run by run")

    def handle(self, args) -> int | None:
        """``--rehearsal-report`` (printed through segment_trace.say: it quotes the game's pages); ``--offline-check``
        (which predictions, then the chain's route members, then each check through segment_trace.say); then O2's
        (``--draft``, ``--preflight``)."""
        if args.rehearsal_report:
            ST.say(rehearsal_report(args.rehearsal_report))
            return 0
        if args.offline_check:
            pred, what = self.current(args.predictions)
            print(f"predictions: {what}")
            members = members_of(pred)
            donors = route_donors(pred)
            if all(d in members.values() for d in donors):
                print(f"chain: {route_members_line(members, donors)}")
            checks = self.offline_check(pred)
            for ok, w, detail in checks:
                ST.say(f"{'PASS' if ok else 'FAIL'}  {w}\n      {detail}")
                for d in A.defect_lines(detail):
                    print(d)
            return 0 if all(ok for ok, _w, _d in checks) else 1
        return A.O2Segment.handle(self, args)


#: O7-CENSUS's classes in the order the detail prints them (no ladder, no start_first column: 154's ip26 counts masked).
CENSUS_LISTS7 = ("writes", "chain", "masked", "error_path", "forbidden_sites", "dead", "inert")


def _dict_diff(have: dict, want: dict) -> str:
    """A short diff of two ``{target: value}`` dicts: missing, extra and wrong targets."""
    miss = sorted(set(want) - set(have))
    extra = sorted(set(have) - set(want))
    wrong = sorted(t for t in set(have) & set(want) if have[t] != want[t])
    return "; ".join(x for x in (f"missing {miss}" if miss else "", f"extra {extra}" if extra else "",
                                 ", ".join(f"{t} {have[t]} (derived {want[t]})" for t in wrong)) if x) or "equal"


O7 = O7Segment()


# ======================================================================== the rehearsal report
def _grants_lines(rec: dict) -> list:
    out = []
    for gr in rec.get("grants") or ():
        out.append(f"    grant in {gr.get('field')} frame {gr.get('frame')} at ({gr.get('x')}, {gr.get('z')}) y "
                   f"{gr.get('y')}; objects (sid, x, z) "
                   f"{[(o.get('sid'), o.get('x'), o.get('z')) for o in gr.get('objects') or ()]}")
    return out or ["    grants: none recorded"]


def _stock_floor(fid):
    """Stock field ``fid``'s player walkmesh from the install (read-only), or None (no install, no such field)."""
    try:
        from ff9mapkit import extract
        from ff9mapkit.content import pathfind
        return pathfind.PlayerWalkmesh(extract.stock_walkmesh(int(fid)))
    except Exception:                                          # noqa: BLE001 -- a report, never a failure
        return None


def foot_gap(samples, wmesh):
    """THE MEASURED SQUEEZE (research/o7_design.md 7.1 R-STAIR, F5), pure but for the mesh: the narrowest wall gap among
    a foot hold's samples (``[frame, x, y, z]``, his published y up positive) on ``wmesh`` -- LEVEL-AWARE, as foot163.py
    measured it: harness.fakegame.Levels.wall_gap, the walls of his level at his PSX height -y -- rounded, or None (no
    sample on a level of the mesh). The radius less it is SQUEEZE_SLACK_W's evidence."""
    from harness.fakegame import Levels
    lv = Levels(wmesh)
    best = None
    for s in samples or ():
        _f, x, y, z = s
        if x is None or y is None or z is None:
            continue
        gap = lv.wall_gap(float(x), float(z), -float(y))
        if gap is None or math.isinf(gap):
            continue
        best = gap if best is None else min(best, gap)
    return None if best is None else round(best, 1)


def _squeeze_lines(sq: dict, floor) -> list:
    """THE SQUEEZE of one run (7.2, F5): its holds, the foot window's with the narrowest wall gap each passed --
    measured here on ``floor(place)`` (:func:`foot_gap`) -- every rung after a hold elsewhere (recorded, never judged)
    and F5's verdict."""
    if not sq:
        return []
    feet = list(sq.get("foot_holds") or ())
    mesh = floor(sq.get("place")) if feet else None
    gaps = [None if mesh is None else foot_gap(h.get("samples"), mesh) for h in feet]
    measured = [x for x in gaps if x is not None]
    narrowest = (min(measured) if measured else "none (no foot hold)" if not feet else
                 "unmeasured (no stock mesh here)" if mesh is None else "unmeasured (no sample on a level)")
    win = sq.get("window") or {}
    L = [f"    squeeze in {sq.get('place')}: {len(sq.get('holds') or [])} hold(s), {len(feet)} in THE FOOT WINDOW (x "
         f"{win.get('x')}, z {win.get('z')}); the narrowest wall gap a foot hold passed {narrowest} (the stock mesh, "
         f"level-aware: SQUEEZE_SLACK_W's evidence); F5 {sq.get('f5')}"]
    for h, gap in zip(feet, gaps):
        L.append(f"      foot hold frame {h.get('frame')}: {h.get('from')} -> {h.get('to')} pressed {h.get('pressed')} "
                 f"travelled {h.get('moved')} slide {h.get('slide')} stall {h.get('stall')}; narrowest gap {gap}")
    for x in sq.get("elsewhere") or ():
        L.append(f"      a rung elsewhere on the stair at frame {x.get('frame')} ({x.get('x')}, {x.get('z')}): "
                 f"{x.get('rungs')} ({x.get('outcome')}) -- recorded, never judged")
    return L


def _monologue_lines7(mono: dict) -> list:
    """THE MONOLOGUE of one run (7.2, F3)."""
    if not mono:
        return []
    inter = [(r.get("attempt"), (r.get("lost") or {}).get("frame"), (r.get("lost") or {}).get("x"),
              (r.get("lost") or {}).get("z")) for r in mono.get("interrupted") or ()]
    pages = [(p.get("text", "")[:24], p.get("frame"), p.get("gone_frame")) for p in mono.get("pages") or ()]
    confirms = [(c.get("seq"), c.get("decision_frame"), c.get("accepted_frame"), c.get("down_frame"))
                for c in mono.get("confirms") or ()]
    return [f"    monologue in {mono.get('place')}: interrupted (attempt, loss frame, x, z) {inter}",
            f"      pages (text, first, gone) {pages}",
            f"      Confirms (seq, decided, accepted, down) {confirms}",
            f"      rows {[(x.get('site'), x.get('f')) for x in mono.get('rows') or ()]}; re-grant {mono.get('regrant')}; "
            f"re-run {mono.get('rerun')}"]


def _stop_lines(rec: dict) -> list:
    """A run's stop (7.1 R-WALK-VOID, F9): where it fired and what was sent around it."""
    L = []
    st = rec.get("hold_stop", ...)
    if st is not ...:
        L.append("    hold stop: never fired" if st is None else
                 f"    hold stop: frame {st.get('frame')} in {st.get('field')} at ({st.get('x')}, {st.get('z')}) y "
                 f"{st.get('y')} -- {st.get('why')}; walk holds of {st.get('place')} #{st.get('n')} before it "
                 f"{st.get('walk_holds_before')}; after it {st.get('holds_after')} hold(s) and {st.get('presses_after')} "
                 f"press(es) (there must be none)")
    st = rec.get("page_stop", ...)
    if st is not ...:
        L.append("    page stop: never fired" if st is None else
                 f"    page stop: frame {st.get('frame')} in {st.get('field')} (ui {st.get('ui')}) at ({st.get('x')}, "
                 f"{st.get('z')}), {len(st.get('texts') or [])} window(s) listed -- {st.get('why')}; Confirms before it "
                 f"{st.get('presses_before')}; after it {st.get('holds_after')} hold(s) and {st.get('presses_after')} "
                 f"press(es) (there must be none)")
    return L


def _warp_text(stage: dict) -> str:
    """A stage's warp as the report heads it: one, or -- a stage with ``each`` -- each run's with its stop."""
    each = stage.get("each")
    if not each:
        return f"warp {stage.get('field')} {stage.get('entrance')} {stage.get('sc')} -> {stage.get('end')}"
    return "; ".join(f"run {k}: warp {e.get('field')} {e.get('entrance')} {stage.get('sc')} -> {e.get('end')}"
                     + "".join(f", {key} {e[key]}" for key in ("hold_stop", "page_stop") if e.get(key))
                     for k, e in enumerate(each, 1))


def rehearsal_report(run_dir, *, walkmesh=None) -> str:
    """``--rehearsal-report``: an o7_rehearse.py launch's ``o7_rehearsal.json`` (research/o7_design.md 7.2), stage by
    stage and run by run -- what each freeze item (7.3) is read from: the capabilities and the launch's readings (F10);
    per run its warp, outcome and render rate (F14), the grants with their published y (F1), THE LEVELS, the bases,
    every ``basis_check`` and the calibration (F2, F4), the step rows and THE WALKS' holds (F4), THE DESCENT and THE
    LADDER's rungs with the holds they followed (F2, F5), THE SQUEEZE in THE FOOT WINDOW -- the narrowest wall gap a foot hold passed MEASURED HERE on the stock mesh,
    level-aware (:func:`foot_gap`) -- and F5's verdict for the run, Dojebon (seen / moved / UNOBSERVED: F2), the
    monologue (F3), the evidence (F11), the trace summary (F6, F7), the stops (F9) and an untraced run's exceptions
    (F13); F-SMOKE's warps and twins (F12). ``walkmesh`` (a place -> its walkmesh; default the install's stock player
    walkmesh, read-only) is a seam for the fake."""
    run_dir = Path(run_dir)
    floor = walkmesh or _stock_floor
    doc = json.loads((run_dir / REHEARSAL_FILE).read_text(encoding="utf-8"))
    L = [f"O7 rehearsals -- {run_dir.name}  (draft sha {str(doc.get('draft_sha256'))[:8]}; stages "
         f"{doc.get('stages_run')}; THE FOOT WINDOW {doc.get('foot')})"]
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
        L.append(f"== {name}: {_warp_text(stage)}" + (" UNTRACED" if stage.get("untraced") else "")
                 + f"  ({len(recs)} run(s)) -- settles: {stage.get('settles')}")
        for rec in recs:
            out = rec.get("outcome") or {}
            rate = rec.get("rate") or {}
            w = rec.get("warp") or {}
            L.append(f"  run {rec.get('n')} ({rec.get('side', 'S')}): warp {w.get('field')} {w.get('entrance')} "
                     f"{w.get('sc')}: {out.get('end')} -- {out.get('why')}"
                     + (f" [{out.get('v')} {out.get('cell')} {out.get('by')}]" if out.get("v") else "")
                     + f"; beats {rec.get('beats')}; {rec.get('t1', 0) - rec.get('t0', 0):.0f}s; render rate "
                     f"{rate.get('fps')} fps ({rate.get('tick_hz')} Hz ticks, {rate.get('source')}); trace "
                     f"{rec.get('trace_file')}")
            L += _grants_lines(rec)
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
                         f"{s.get('attempt')} {s.get('outcome')}: to {s.get('to')}, loss {s.get('lost')}, landed "
                         f"{s.get('landed')}, flip {s.get('flip_frame')}, clearance {s.get('clearance')}, route fps "
                         f"{((s.get('route') or {}).get('fps') or {}).get('fps')}"
                         + (f", door {s.get('door')}" if s.get("door") else "")
                         + (f" -- {s.get('why')}" if s.get("why") else ""))
            for w in rec.get("walks") or ():
                hs = w.get("holds") or []
                L.append(f"    walk ({w.get('donor')}, visit {w.get('visit')}) #{w.get('n')} attempt {w.get('attempt')} "
                         f"{w.get('outcome')}: {len(hs)} hold(s), {sum(1 for h in hs if h.get('slide'))} slide(s), "
                         f"{sum(1 for h in hs if h.get('stall'))} stall(s), {len(w.get('waypoints') or [])} "
                         f"waypoint(s); the first hold {hs[0].get('from') if hs else None} -> "
                         f"{hs[0].get('to') if hs else None}")
            for h in (rec.get("descent") or {}).get("holds") or ():
                L.append(f"    descent hold frame {h.get('frame')}: {h.get('from')} -> {h.get('to')} predicted reach "
                         f"{h.get('reach')} travelled {h.get('moved')} off the leg {h.get('off_leg')} slide "
                         f"{h.get('slide')} y {h.get('y0')} -> {h.get('y1')}")
            for x in rec.get("ladder") or ():
                L.append(f"    ladder at frame {x.get('frame')} in {x.get('field')} ({x.get('x')}, {x.get('z')}): rungs "
                         f"{x.get('rungs')} ({x.get('outcome')}) after the hold from {x.get('after_hold')}; step "
                         f"{x.get('step')}" + (" -- IN THE FOOT WINDOW" if x.get("foot") else ""))
            L += _squeeze_lines(rec.get("squeeze") or {}, floor)
            dj = rec.get("dojebon") or {}
            if dj:
                L.append(f"    {dj.get('name') or 'the static object'}: "
                         + ("UNOBSERVED (no reading in its place)" if not dj.get("seen") else f"seen {dj.get('seen')}")
                         + f"; moved {dj.get('moved') or 'none'}; {len(dj.get('polls') or [])} poll reading(s), distinct "
                         f"positions {sorted({tuple(p[1:]) for p in dj.get('polls') or ()})[:4]}")
            L += _monologue_lines7(rec.get("monologue") or {})
            ev = rec.get("evidence") or {}
            L.append(f"    evidence: {len(ev.get('press') or [])} press row(s), {len(ev.get('forbidden') or [])} "
                     f"forbidden row(s), {len(ev.get('observed') or [])} observed row(s), {len(ev.get('input') or [])} "
                     f"input row(s)")
            npg = rec.get("no_progress") or {}
            L.append(f"    longest no-progress stretch: {npg.get('longest_s')}s at {npg.get('where')}")
            L += _stop_lines(rec)
            if not rec.get("traced", True):
                L.append(f"    untraced: exceptions since the warp {rec.get('exceptions')}; Memoria.log lines "
                         f"{len(rec.get('log_lines') or [])}")
            end = rec.get("end") or {}
            er = end.get("end_run") or {}
            L.append(f"    end: state {end.get('end_state')}; end_run " + ("ok" if er.get("ok") else f"FAILED {er.get('why')}")
                     + f", title {er.get('title')}, rows {[x.get('k') for x in er.get('how') or ()]}"
                     + (f", {er.get('s')} s" if er.get("s") is not None else ""))
            L += _trace_report7(rec.get("trace") or {})
        L.append("")
    return "\n".join(L)


# ======================================================================== the session and the CLI
def run(g) -> None:
    """The session (tools/play.py's entry): O7Segment.run."""
    return O7.run(g)


def main(argv=None) -> int:
    return O7.main(argv)


if __name__ == "__main__":
    sys.exit(main())
