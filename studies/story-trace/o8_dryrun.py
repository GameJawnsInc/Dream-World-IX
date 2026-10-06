"""O8's analysis, driven on SYNTHETIC sessions (research/o8_design.md section 8): every registered check must read PASS
on the null pair and FAIL (or VOID) on the mutant built to break it -- a check that cannot fail is not a check.

    py studies/story-trace/o8_dryrun.py [--predictions studies/story-trace/o8_predictions_v1.json] [--as-if-frozen]

Without --predictions it reads the frozen o8_predictions_v1.json once the lead has frozen it, else it writes the DRAFT
(o8_west_tower.draft_predictions: O4's chain's campaign.toml) to a temporary predictions file -- nothing is frozen until
the lead's rehearsals -- and runs every case against that. ``--as-if-frozen`` runs every case on :func:`as_if_frozen`
of those predictions instead: every value the lead's freeze changes changed (every budget x1.5, ``rehearsals`` and
``rehearsal_fps`` named, ``rehearsed`` filled, each step's ``start`` moved 20 u) -- no case may read a freeze-time
literal, so both readings give the same N/N (G45 runs both).

Each case writes a session directory the way the session does (o8_session.json, the members' scripts, one trace and
one driver log per run) and runs :meth:`o8_west_tower.O8Segment.analyse` on it. The rows are real store sites of the
stock bytes of 164, 165, 166 and 55 (every field row joins but the join-failure case's), shifted onto the members on the
F side (``fld`` = member, ``don`` = donor: 164 -> 31256, 165 -> 31257, 166 -> 31258) -- 55 is REAL on both sides, so
every F run crosses ONE seam, 31258 -> 55, read through the kept ``e off fld 55`` row -- and EMITTED as the engine's sink
emits them (StoryTrace.cs:374-401): a same-value store only while its SITE has emitted no same-value row, a change up to
64 times, the rest counted into a ``c`` row at the epoch's close -- over O8's start values (the raw warp's SC 1190 and
FieldEntrance 342 over field 70's prologue: Byte[13] 1, Int16[9] 643, Int16[11] -1, Byte[14] 0, Byte[8] 125, every other
target 0), so no site of the base run is stored twice and nothing is counted: 29 ``w`` rows before the cut, 4.16's
pattern. A run's driver log carries its visit rows, the four step rows (164's WALK to P1 with its at_y and THE KNIGHT
WAIT read, then its TRIGGER on path A -- the loss with its height in e2, landed None, the walk-out's frames -- 165's walk
and trigger the same way, each seeded visit's first row judged), THE KNIGHT's seat and start1 readings, 166's six page
presses, FMV004's clock rows (31 fps, each with its write time), the end row and the rate row; its outcome the beats,
the pages, the end state.

O8's ``case()`` is O3's, EXACT: every check a case does not name must read PASS -- a case naming COVER V expects every
core check VOID -- so each NOT PROVEN row names EVERY check it fails, and "alone" is a registered fact. A multi-clause
check (LANDING, SEAM, WALK, ORDER, KNIGHT, MOVIE, PATTERN, STATE, VOID-ASYM) also registers the clause its detail must
name.

THE STORY-O3 SEAM FIXTURE (research/o8_design.md 8; critique #3): story-o3's archived session (the MAIN repo's
``.harness-runs``, read-only; missing FAILS, never skips) read by O3's own ``read_session`` with O3's FROZEN predictions
-- the new seam, landing and raced-state code tried on a REAL traced fork seam (31213 -> 64) before O8's freeze.

EVERY GLOB IS CLOSED AT ITS SEGMENT: the study's predictions files are read only through ``frozen_through(8)``
(o7_dryrun's), so a later freeze cannot move this output, which the regression gate (G45) compares.
"""
from __future__ import annotations

import argparse
import copy
import datetime as _dt
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import o8_west_tower as O                                                  # noqa: E402
import o7_castle_walk as C7                                                # noqa: E402
import o7_dryrun as D7                                                     # noqa: E402
import o6_steiner as C6                                                    # noqa: E402
import o5_hallway as C5                                                    # noqa: E402
import o5_dryrun as D5                                                     # noqa: E402
import o4_castle as C4                                                     # noqa: E402
import o4_dryrun as D4                                                     # noqa: E402
import o3_prima_vista as P                                                 # noqa: E402
import segment_drive as SD                                                 # noqa: E402
import segment_trace as ST                                                 # noqa: E402
from ff9mapkit import storytrace as T                                      # noqa: E402
from o3_dryrun import _is, after, before, e, edit, r, w, with_opt          # noqa: E402  (O3's event helpers)
from o7_dryrun import _all, _edit_log, _side, _void, drop_nth, edit_nth, move, upto_nth   # noqa: E402
from segment_trace import members_of, place, verdict                       # noqa: E402

#: The study's predictions files a segment-8 dry run reads: rungs and O1-O8 (o7_dryrun.frozen_through, closed at 8).
frozen_through = D7.frozen_through


# ======================================================================== real store sites (donor, sid, tag, ip, target, value)
def _pro(place_, ips, i9, b13) -> list:
    """Main_Init's prologue at ``ips``: Bit[191] := 0, Bit[184] := 0, Int16[9] := ``i9``, Byte[13] := ``b13``, Int16[11]
    := -1, Byte[14] := 0 (4.16)."""
    return [(place_, 0, 0, ips[0], "Global.Bit[191]", 0), (place_, 0, 0, ips[1], "Global.Bit[184]", 0),
            (place_, 0, 0, ips[2], "Global.Int16[9]", i9), (place_, 0, 0, ips[3], "Global.Byte[13]", b13),
            (place_, 0, 0, ips[4], "Global.Int16[11]", -1), (place_, 0, 0, ips[5], "Global.Byte[14]", 0)]


P130 = (22, 49, 57, 130, 138, 200)
P119 = (22, 49, 57, 119, 138, 200)
PRO = {164: _pro(164, P130, 385, 1), 165: _pro(165, P130, 385, 1), 166: _pro(166, P119, -1, 0)}
I22_164, I49_164, I57_164, I130_164, I138_164, I200_164 = PRO[164]
I22_165, I49_165, I57_165, I130_165, I138_165, I200_165 = PRO[165]
I22_166, I49_166, I57_166, I119_166, I138_166, I200_166 = PRO[166]
B13_164 = (164, 0, 0, 764, "Global.Byte[13]", 2)
KN230 = (164, 1, 1, 230, "Global.Bit[3811]", 1)
CH164 = (164, 2, 2, 243, "Global.Int16[2]", 343)
B13_165 = (165, 0, 0, 844, "Global.Byte[13]", 2)
E2_165 = (165, 2, 2, 205, "Global.Byte[13]", 3)
CH165 = (165, 2, 2, 233, "Global.Int16[2]", 344)
B8_166 = (166, 0, 0, 255, "Global.Byte[8]", 125)
M345 = (166, 6, 1, 345, "Global.Byte[208]", 0)
M380 = (166, 6, 1, 380, "Global.Byte[208]", 1)
M502 = (166, 6, 1, 502, "Global.Byte[8]", 0)
CH166 = (166, 6, 1, 863, "Global.Int16[2]", 110)
#: 55 e0 t0 (REAL on both sides): ip22 the cut, then its prologue past the cut -- ip255 rewrites Int16[2] 110 -> 106 and
#: ip342 Byte[8] 0 -> 125 (THE RACED SET: end_race8's stores over the arrival's values).
END55 = (55, 0, 0, 22, "Global.Bit[191]", 0)
POST55 = [(55, 0, 0, 49, "Global.Bit[184]", 0), (55, 0, 0, 57, "Global.Int16[9]", -1),
          (55, 0, 0, 119, "Global.Byte[13]", 0), (55, 0, 0, 138, "Global.Int16[11]", -1),
          (55, 0, 0, 200, "Global.Byte[14]", 0), (55, 0, 0, 255, "Global.Int16[2]", 106),
          (55, 0, 0, 342, "Global.Byte[8]", 125)]
#: Off the route, each a real store: the error paths (164 ip178 Byte[14] := 9 then window 56's ip607 reset; 165's ip178
#: and ip687); 164 e2 t2 ip215 (dead: behind Map.Bit[162] == 0); the knight's talk (164 e1 t3 ip308 / ip627) and its
#: script (e7 t11 ip399); the back doors (164 e3 t2 ip243 -> 163, 165 e3 t2 ip243 -> 164) and 163's prologue.
ERR164_178 = (164, 0, 0, 178, "Global.Byte[14]", 9)
ERR164_607 = (164, 0, 0, 607, "Global.Byte[13]", 0)
ERR165_178 = (165, 0, 0, 178, "Global.Byte[14]", 9)
ERR165_687 = (165, 0, 0, 687, "Global.Byte[13]", 0)
DEAD164_215 = (164, 2, 2, 215, "Global.Byte[13]", 3)
TALK164_308 = (164, 1, 3, 308, "Global.Bit[3851]", 1)
TALK164_627 = (164, 1, 3, 627, "Global.Bit[7211]", 1)
TALK164_399 = (164, 7, 11, 399, "Global.Byte[208]", 0)
BACK164 = (164, 3, 2, 243, "Global.Int16[2]", 343)
BACK165 = (165, 3, 2, 243, "Global.Int16[2]", 344)
S163 = [(163, 0, 0, 22, "Global.Bit[191]", 0), (163, 0, 0, 49, "Global.Bit[184]", 0),
        (163, 0, 0, 57, "Global.Int16[9]", 385)]
SC_CS = (165, -1, -1, -1, "Global.UInt16[0]", 1190)
#: Field 70's two raced stores (4.5): ip249 Byte[8] := 125 (the early edge) and ip475 Byte[13] := 2 (the late edge).
RACE249 = (70, 0, 0, 249, "Global.Byte[8]", 125)
RACE475 = (70, 0, 0, 475, "Global.Byte[13]", 2)
#: The checks, in the order the analysis reports them.
CHECKS = ("O8-FROZEN", "O8-COVER", "O8-FORBIDDEN", "O8-VOID-ASYM", "O8-START", "O8-NO-SC", "O8-CHAIN", "O8-RESIDUE",
          "O8-WRITES", "O8-NULL", "O8-STABLE", "O8-LANDING", "O8-SEAM", "O8-WALK", "O8-ORDER", "O8-KNIGHT", "O8-MOVIE",
          "O8-PATTERN", "O8-MASKED", "O8-STATE", "O8-JOIN")
CORE = CHECKS[4:]
#: The frame layout of a base run (Time.frameCount: the trace's ``f`` and the log's frames alike): each place's
#: prologue at F_PRO; 164's walk from F_W0 to its arrival F_ARRIVE, THE KNIGHT's ip230 at F_KNIGHT, the wait read at
#: F_READ (the step-0 row's frame), its trigger from F_X0 to its loss F_LOST, the door's rows from F_DOOR (after the
#: loss), the flip and the landing after them; 166's pages from F_PAGE, ip502 at F_502, ip863 at F_863 (1411 frames: 45.5
#: s at 31 fps), the cut (55 ip22) at F_END.
F_PRO = {164: 1100, 165: 5000, 166: 7000}
F_POST = {164: 1170, 165: 5070, 166: 7070}
F_W0 = {164: 1500, 165: 5200}
F_ARRIVE = {164: 2400, 165: 5800}
F_KNIGHT = 2650
F_READ = 2700
F_X0 = {164: 3000, 165: 5900}
F_LOST = {164: 4400, 165: 6700}
F_DOOR = {164: 4410, 165: 6710}
F_PAGE = 7100
F_345 = 7210
F_502 = 8000
F_863 = 9411
F_END = 9420
MOVIE_FPS = 31.0
#: Where each walk arrived (P1s: within tolerance of the goal) at its published height, each trigger's loss with its
#: height (inside its door: e2 fires there), each grant.
ARRIVE = {164: (1340.0, 2250.0, 8958.0), 165: (1510.0, 4700.0, 11251.0)}
LOST = {164: (24.5, 2270.8, 13008.0), 165: (2419.6, 3130.0, 15169.0)}
GRANT = {164: (2040.0, 3335.0), 165: (2055.0, 3411.0)}
SEAT_AT = (-586.0, 3884.0)
#: The first-move check each seeded visit's first row carries (S19's basis_check, degrees).
ANGLE = {164: 0.4, 165: 1.1}
#: 166's six pages as the agent publishes them (block 3's US sources; text only, never judged).
PAGES166 = ["[STNR] 307", "[STNR] 308", "[STNR] 309", "[STNR] 311", "[STNR] 312", "[STNR] 313"]


# ======================================================================== events and their rendering
def at(frame: int) -> tuple:
    """A frame anchor: the next event's row lands at ``frame`` (later rows go on 10 frames apart)."""
    return ("at", int(frame))


def render(events: list, side: str, members: dict) -> list:
    """The rows the engine would write for ``events`` on ``side`` (o7_dryrun.render's rule, O8's start values:
    :data:`o8_west_tower.START_VALUES8`): F-side donors on their member ids (55 has none: REAL on both sides); each
    store's ``old`` the variable's value so far; THE SINK'S RULE per SITE. A store's ``opt``: ``fld`` / ``don``
    (overrides), ``old``, ``m``, ``src``, ``add``, ``f`` (its row's frame, the sequence kept), ``emit``, ``count``. An
    ``e`` event may carry a fourth item, ``{"fld"}``: an ``off`` in another field."""
    fork = {d: f for f, d in sorted(members.items(), reverse=True)}

    def fld_of(donor):
        return fork.get(donor, donor) if side == "F" else donor
    rows, sites = [], {}
    values = dict(O.START_VALUES8)
    f, sc = 1000, 1190
    for ev in events:
        kind = ev[0]
        if kind == "at":
            f = max(f, ev[1] - 10)
            continue
        f += 10
        if kind == "e":
            why, donor = ev[1], ev[2]
            eopt = ev[3] if len(ev) > 3 else {}
            if why == "off":
                for key, s in sites.items():
                    if s["n"]:
                        fld, m, src, sid, tag, ip, byte, width, bit = key
                        rows.append({"k": "c", "f": f, "p": 0, "m": m, "fld": fld, "don": s["don"], "sc": sc,
                                     "src": src, "sid": sid, "tag": tag, "ip": ip, "byte": byte, "w": width,
                                     "bit": bit, "n": s["n"], "last": s["last"]})
                f += 1
            rows.append({"k": "e", "f": eopt.get("f", f), "p": 0, "m": 1, "fld": eopt.get("fld", fld_of(donor)),
                         "don": eopt.get("don", eopt.get("fld", donor)), "sc": sc, "why": why})
        elif kind == "r":
            _k, donor, byte, old, new, opt = ev
            rows.append({"k": "r", "f": opt.get("f", f), "p": 0, "m": 1, "fld": opt.get("fld", fld_of(donor)),
                         "don": opt.get("don", donor), "sc": sc, "byte": byte, "old": old, "new": new, "why": "frame"})
        else:
            _k, donor, sid, tag, ip, target, value, opt = ev
            width, index = target.split(".", 1)[1].rstrip("]").split("[")
            index = int(index)
            bit = index if width in T.BIT_WIDTHS else -1
            byte = index >> 3 if bit >= 0 else index
            fld, don = opt.get("fld", fld_of(donor)), opt.get("don", donor)
            m, src, add = opt.get("m", 1), opt.get("src", "eb"), opt.get("add", 0)
            old = opt.get("old", values.get(target, 0))
            values[target] = value
            key = (fld, m, src, sid, tag, ip, byte, width, bit)
            s = sites.setdefault(key, {"same": False, "changes": 0, "n": 0, "last": None, "don": don})
            if old == value:
                emit, s["same"] = not s["same"], True
            else:
                emit = s["changes"] < 64
                s["changes"] += int(emit)
            if opt.get("emit"):
                emit = True
            if opt.get("count"):
                emit = False
            if not emit:
                s["n"] += 1
                s["last"] = value
                continue
            if target == "Global.UInt16[0]":
                sc = value
            script = src == "eb"
            rows.append({"k": "w", "f": opt.get("f", f), "p": 0, "m": m, "fld": fld, "don": don, "sc": sc, "src": src,
                         "sid": sid if script else -1, "uid": sid if script else -1, "lvl": 0 if script else -1,
                         "ip": ip if script else -1, "tag": tag if script else -1, "add": add, "byte": byte,
                         "w": width, "bit": bit, "old": old, "new": value, "same": int(old == value)})
    return rows


#: The raw warp's four residue rows in field 70 (SC 1190 = 0x04A6's two bytes, FieldEntrance 342 = 0x0156's two).
RESIDUE = [r(70, 0, 0, 166), r(70, 1, 0, 4), r(70, 2, 0, 86), r(70, 3, 0, 1)]


def base_events() -> list:
    """A base run (research/o8_design.md 8): ``arm`` in field 70; the warp's FOUR residue rows there; 164's prologue
    and its ip764 (the grant's pass), THE KNIGHT's ip230 during the wait (inside THE EXEMPT SPAN), the door's ip243 after
    the trigger's loss; 165's prologue, ip844 and its door's ip205 / ip233; 166's prologue, ip255, ip345 / ip380 under
    page 309, ip502 (FMV004's span opens), ip863 (1411 frames later: the movie played out); 55's ip22 (THE CUT) and its
    post-cut prologue; ``off`` in REAL 55 -- on F the kept ``e off fld 55`` row the seam is read through."""
    ev = [e("arm", 70)] + list(RESIDUE)
    ev += [at(F_PRO[164])] + [w(s) for s in PRO[164]] + [at(F_POST[164]), w(B13_164)]
    ev += [at(F_KNIGHT), w(KN230), at(F_DOOR[164]), w(CH164)]
    ev += [at(F_PRO[165])] + [w(s) for s in PRO[165]] + [at(F_POST[165]), w(B13_165)]
    ev += [at(F_DOOR[165]), w(E2_165), w(CH165)]
    ev += [at(F_PRO[166])] + [w(s) for s in PRO[166]] + [at(F_POST[166]), w(B8_166)]
    ev += [at(F_345), w(M345), w(M380), at(F_502), w(M502), at(F_863), w(CH166)]
    ev += [at(F_END), w(END55)] + [w(s) for s in POST55] + [e("off", 55)]
    return ev


def _fld(members: dict, side: str, donor: int) -> int:
    inv = {d: f for f, d in sorted(members.items(), reverse=True)}
    return inv.get(donor, donor) if side == "F" else donor


def visits(rows: list, members: dict, route) -> list:
    """The driver's ``visit`` rows for a rendered run: one each time the written field changes after the arm, in the
    route's places only (a real route field on F too), at the frame of the visit's first row."""
    out, cur = [], None
    for x in rows:
        if x["k"] not in ("w", "r") or x["fld"] == 70 or x["fld"] == cur:
            continue
        p = place(x["fld"], members)
        if p not in route:
            continue
        cur = x["fld"]
        out.append({"k": "visit", "field": cur, "donor": p, "visit": len(out) + 1, "frame": x["f"], "sc": 1190})
    return out


# ======================================================================== the run's driver log
def route_rec(*, basis=None, angle=None, clearance=None, frame=None, fps=60.0) -> dict:
    """A step row's trimmed route record (segment_drive.trim_route): the legs and the ladder's counters; S19's ``basis``
    and ``basis_check`` when given; S18's ``clearance``."""
    rec = {"route": 12, "travelled": 3000.0, "replans": 0, "pushes": 0, "waits": 0, "blockers": [], "landed": None,
           "changed_to": None, "handoff": True, "frozen": False, "boxed": False, "fps": {"fps": fps}}
    if clearance is not None:
        rec["clearance"] = clearance
    if basis is not None:
        rec["basis"] = basis
    if angle is not None:
        rec["basis_check"] = {"angle": angle, "moved": 58.0, "frame": frame, "pressed": "left"}
    return rec


def step_row(fld: int, place_: int, visit: int, n: int, kind: str, name: str, *, outcome="done", attempt=1,
             frame0: int, frame: int, frm=(0.0, 0.0), to=None, lost=None, lost_field=None, landed=None, flip=None,
             landed_frame=None, door=None, route=None, clearance=None, basis=None, npcs=None, unstick=None, at_y=None,
             wait_flag=None, v=None, by=None, why=None) -> dict:
    """A step's row as run_step writes it (segment_drive._Drive.run_step): its ``from`` sample (control held), its
    ``to`` sample (``to``: (x, z, control); default the loss), its ``lost`` sample (``lost``: (frame, x, z, y) -- y
    None: no height -- read in ``lost_field``, the walk's field by default, or None), ``landed``, ``flip_frame``,
    ``door``, the trimmed route record, and the opt-in keys only when given: ``clearance``, ``basis``, ``unstick``
    (S18/S19/S23), ``at_y``, ``wait_flag`` (S20/S21); a path-A trigger (``landed`` None) carries S14b's walk-out record
    (``flip_late`` True, ``landed_frame``)."""
    lo = None if lost is None else {"frame": lost[0], "control": False, "x": lost[1], "z": lost[2],
                                    "field": fld if lost_field is None else lost_field}
    if lo is not None and len(lost) > 3:
        lo["y"] = lost[3]
    tx, tz, tc = to if to is not None else ((lo or {}).get("x"), (lo or {}).get("z"), False)
    row = {"k": "step", "field": fld, "donor": place_, "sc": 1190, "visit": visit, "n": n, "kind": kind, "name": name,
           "attempt": attempt, "outcome": outcome, "t0": frame0 / 60.0, "t1": frame / 60.0, "frame0": frame0,
           "frame": frame, "from": {"frame": frame0, "control": True, "x": frm[0], "z": frm[1]},
           "to": {"frame": frame, "control": tc, "x": tx, "z": tz}, "lost": lo, "landed": landed,
           "flip_frame": flip, "door": door, "route": route if route is not None else route_rec(), "lunge": None,
           "climb": None, "depth": None, "v": v, "by": by, "why": why}
    for key, val in (("clearance", clearance), ("basis", basis), ("unstick", unstick), ("at_y", at_y),
                     ("wait_flag", wait_flag)):
        if val is not None:
            row[key] = val
    if kind == "trigger" and outcome == "done" and landed is None:
        row.update(walkout=[[lost[0] + 2, lost[1], lost[2], False]] if lost else [], flip_late=True,
                   landed_frame=landed_frame)
    return row


def press(fld, donor, visit, frame, raw, seq, *, why="page") -> dict:
    """A page press as the drive logs it (rule 7)."""
    return {"k": "press", "why": why, "field": fld, "donor": donor, "visit": visit, "sc": 1190,
            "pre": {"frame": frame, "control": False, "x": None, "z": None}, "post": None, "near": [], "seq": seq,
            "ack_frame": frame + 5, "button": "confirm", "raws": [raw], "texts": [raw], "accepted_frame": frame + 1,
            "down_frame": frame + 2}


def knight_row(what: str, fld: int, frame: int, *, visit: int = 1, x=SEAT_AT[0], z=SEAT_AT[1], frm="poll",
               sid: int = 1) -> dict:
    """THE KNIGHT's reading as knight_watch writes it: its field and place the READING's."""
    return {"k": "knight", "what": what, "donor": 164, "sid": sid, "field": fld, "visit": visit, "frame": frame,
            "x": x, "z": z, "from": frm}


def clock_rows(fld: int, lo: int = F_PRO[166], hi: int = F_END, *, fps: float = MOVIE_FPS, every: int = 30,
               mtime0: float = 1000.0) -> list:
    """movie_clock's rows over 166's visit: one every ``every`` frames, each with its write time at ``fps``."""
    return [{"k": "clock", "frame": f, "mtime": round(mtime0 + (f - lo) / fps, 4), "field": fld, "ui": "FieldHUD",
             "control": False, "windows": 0} for f in range(lo, hi, every)]


def wait_rec(frame0: int = F_ARRIVE[164], frame: int = F_READ, *, read=True) -> dict:
    """S21's wait record on the step-0 row."""
    return {"flag": 3811, "value": 1, "read": read, "frame0": frame0, "frame": frame if read else None,
            "s": round((frame - frame0) / 60.0, 2), "game_s": round((frame - frame0) / 30.0, 2), "published": 40,
            "last": 1 if read else 0}


def cell_log(pred: dict, c: dict, fld_of) -> list:
    """One table cell's step rows as a covered run writes them (research/o8_design.md 8's base run): the WALK done at
    its goal with control held, its ``at_y`` read, 164's with THE KNIGHT WAIT read after ip230; the TRIGGER done on PATH
    A -- its loss with its height inside its door, ``landed`` None, the walk-out's flip and landing frames. The visit's
    FIRST row carries the seeded basis "prior" and its first-move check."""
    p, visit = c["donor"], c["visit"]
    fld = fld_of(p)
    rows = []
    for n, s in enumerate(c["steps"]):
        first = n == 0
        rb = dict(basis="prior", angle=ANGLE.get(p, 1.0)) if first else dict(basis="cached")
        frm = GRANT.get(p, (0.0, 0.0)) if first else tuple(map(float, s.get("start") or (0, 0)))
        cl = s.get("clearance")
        if s["kind"] == "walk":
            ax, az, ay = ARRIVE[p]
            band = s.get("at_y")
            rows.append(step_row(fld, p, visit, n, "walk", s.get("name"), frame0=F_W0[p],
                                 frame=F_READ if s.get("wait_flag") else F_ARRIVE[p], frm=frm, to=(ax, az, True),
                                 route=route_rec(clearance=cl, frame=F_W0[p] + 50, **rb), clearance=cl,
                                 basis=s.get("basis"), at_y=None if band is None else
                                 {"band": [float(band[0]), float(band[1])], "y": ay},
                                 wait_flag=wait_rec() if s.get("wait_flag") else None))
            continue
        lx, lz, ly = LOST[p]
        rows.append(step_row(fld, p, visit, n, "trigger", s.get("name"), frame0=F_X0[p], frame=F_LOST[p] + 5, frm=frm,
                             lost=(F_LOST[p], lx, lz, ly), landed=None, flip=F_LOST[p] + 20,
                             landed_frame=F_LOST[p] + 40, route=route_rec(clearance=cl, frame=F_X0[p] + 50, **rb),
                             clearance=cl, basis=s.get("basis"), unstick=s.get("unstick")))
    return rows


def standard_log(pred: dict, side: str, rows: list) -> tuple:
    """A run's driver log as the drive writes it (research/o8_design.md 2.2): each route visit's ``visit`` row; 164's
    and 165's step rows (:func:`cell_log`), THE KNIGHT's ``seat`` row after 164's step-0 row and its ``start1`` row after
    its step-1 row (knight_watch: the reading's field); 166's six page presses (313 decided on its last sample before
    ip502) and FMV004's clock rows; the ``rate`` row last. ``(log, ctx)``: ``ctx`` the handles a case edits -- ``steps``
    ``{(place, n, attempt): row}``, ``visits``, ``fld`` ``{place: field}``, ``presses``, ``knight`` ``{what: row}``,
    ``clocks``."""
    members = members_of(pred) if side == "F" else {}
    mem_all = members_of(pred)

    def fld_of(p):
        return _fld(mem_all, side, p)
    vis = visits(rows, members, set(pred["route"]))
    log, steps, presses, knight, clocks = [], {}, [], {}, []
    cells = {c["donor"]: c for c in pred.get("table") or ()}
    sw = pred.get("seat_watch") or {}
    for v in vis:
        log.append(v)
        p = v["donor"]
        if p == 166:
            presses = [press(v["field"], 166, v["visit"], F_PAGE + 150 * i, PAGES166[i], 400 + i) for i in range(5)]
            presses.append(press(v["field"], 166, v["visit"], F_502 - 10, PAGES166[5], 405))
            clocks = clock_rows(v["field"])
            log += presses + clocks
        c = cells.pop(p, None)                       # each cell's rows once: at its place's first visit row
        if c is None:
            continue
        for row in cell_log(pred, c, fld_of):
            steps[(p, row["n"], row["attempt"])] = row
            log.append(row)
            if p == sw.get("donor") and row["n"] == 0:
                knight["seat"] = knight_row("seat", fld_of(p), F_READ, visit=v["visit"], frm="ring")
                log.append(knight["seat"])
            elif p == sw.get("donor") and row["n"] == 1:
                knight["start1"] = knight_row("start1", fld_of(p), F_X0[p], visit=v["visit"])
                log.append(knight["start1"])
    return log, {"steps": steps, "visits": vis, "fld": {p: fld_of(p) for p in pred["route"]}, "presses": presses,
                 "knight": knight, "clocks": clocks}


# ======================================================================== sessions
def six(pred: dict, *, s=None, f=None) -> list:
    """S F S F S F: each run's base events, ``s`` / ``f`` applied per side as ``fn(events, n)`` (``n`` = 0, 1, 2 within
    the side)."""
    counts = {"S": 0, "F": 0}
    out = []
    for side in pred["order"]:
        n = counts[side]
        counts[side] += 1
        ev = base_events()
        fn = s if side == "S" else f
        out.append({"side": side, "events": fn(ev, n) if fn else ev})
    return out


def preflight_rows() -> list:
    """The preflight a session on the live install records (6.2): P-TEXT for block 3 (each language its own stock text:
    7 byte-equal of 7) and P-ENGINE on the pinned DLLs -- each detail from its own reader."""
    langs = ("us", "uk", "fr", "gr", "it", "es", "jp")
    text = {L: f"stock {L}".encode() for L in langs}
    eng = {"x64": O.ENGINE["x64"], "x86": O.ENGINE["x86"]}
    rows = []
    ok, detail = C4.p_text(3, [("FF9CustomMap", dict(text))], text, o1_block2=None, o4_registered=True)
    rows.append([ok, O.O8.title("P-TEXT3"), detail])
    ok, detail = C4.p_engine(dict(eng), O.ENGINE)
    rows.append([ok, O.O8.title("P-ENGINE"), detail])
    assert all(x[0] for x in rows), rows
    return rows


def make_session(tmp: Path, pred_path: Path, runs: list, scripts: dict, *, stopped: str | None = None) -> Path:
    """A session directory as O8Segment.run writes one. Each run: ``{side, events | rows, end?, why?, beats?, v?, cell?,
    by?, install?, end_state?, end_field?, skipped?, stopped?, log? (fn(log, ctx) -> log, editing the standard log),
    pages? (fn(pages)), rate?}``; ``stopped``: the session's S15 stop."""
    pred, sha = O.O8.load(pred_path)
    members = members_of(pred)
    d = tmp / f"s{len(list(tmp.iterdir()))}"
    (d / "scripts").mkdir(parents=True)
    for fid, data in scripts.items():
        (d / "scripts" / f"{fid}.eb").write_bytes(data)
    session = {"label": d.name, "predictions": str(pred_path), "predictions_sha256": sha,
               "predictions_version": pred["version"], "order": pred["order"], "budget": pred["budget"],
               "preflight": preflight_rows(),
               "install": {"settings": pred["settings"], "engine": {"x64": O.ENGINE["x64"], "x86": O.ENGINE["x86"]}},
               "runs": [], "ended": {"log": [{"k": "recover-warp", "field": 4600}], "ok": True, "why": ""}}
    if stopped is not None:
        session["stopped"] = stopped
    for i, run in enumerate(runs, 1):
        side = run["side"]
        name, log_name = f"run{i}_{side}.jsonl", f"run{i}_{side}_log.json"
        rec = {"i": i, "side": side, "start": pred["start"][side], "trace": name, "log": log_name}
        if run.get("skipped"):
            rec.update(skipped=run["skipped"], stopped=run.get("stopped"), end="void", why="not driven", beats=None)
            session["runs"].append(rec)
            continue
        rows = run.get("rows") if run.get("rows") is not None else render(run["events"], side, members)
        (d / name).write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
        log, ctx = standard_log(pred, side, rows)
        if callable(run.get("log")):
            log = run["log"](log, ctx)
        end = run.get("end", "reached")
        end_state = run.get("end_state", dict(pred["end_state"]) if end == "reached" else None)
        if end == "reached":
            last = max((x["f"] for x in rows), default=0)
            log.append({"k": "end", "field": run.get("end_field", ST.side_ends(pred, side)[0]), "frame": last,
                        "sc": 1190, "end_state": end_state, "t": 150.0, "end_row": {"seen": True, "f": last, "s": 0.1}})
        log.append(dict({"k": "rate", "fps": 31.0, "tick_hz": 30.0, "source": "fake"}, **(run.get("rate") or {})))
        pages = list(PAGES166)
        if callable(run.get("pages")):
            pages = run["pages"](pages)
        beats = run.get("beats", {b: True for b in pred["beats"]})
        outcome = {"end": end, "why": run.get("why", f"field {ST.side_ends(pred, side)[0]}" if end == "reached"
                                              else "route: stopped"),
                   "void": None, "beats": beats, "pages": pages, "timed": [], "choices": [],
                   "steps": [x for x in log if x.get("k") == "step"], "overlays": [], "forbidden": [],
                   "end_state": end_state, "t": 150.0}
        (d / log_name).write_text(json.dumps({"outcome": outcome, "log": log}), encoding="utf-8")
        rec.update(end=end, why=outcome["why"], beats=beats)
        for k in ("v", "cell", "by", "install", "stopped"):
            if run.get(k) is not None:
                rec[k] = run[k]
        session["runs"].append(rec)
    (d / O.SESSION_FILE).write_text(json.dumps(session), encoding="utf-8")
    return d


def result(checks) -> dict:
    return {w_.split(":")[0]: ok for ok, w_, _d in checks}


def details(checks) -> dict:
    return {w_.split(":")[0]: d_ for _ok, w_, d_ in checks}


# ======================================================================== the cases
CASES = []


def case(name, want_verdict, *, fail=(), clauses=None, cover_void=False, report_has=(), void=None, covered=None,
         lacks=None, detail_has=None, stopped=None, reasons=None):
    """Register a case, EXACT (O3's ``case()``): ``fail`` the checks that must read FAIL, ``clauses`` ``{check:
    [markers]}`` the clauses its detail must name (each such check FAILS too), ``cover_void`` -- COVER VOID and every core
    check VOID ("too few covered runs"); every other check must read PASS. ``report_has`` substrings of the report,
    ``void`` ``{run index: [classes its VOID reasons must include]}``, ``lacks`` ``{run index: [classes they must NOT
    include]}``, ``covered`` ``{run index: bool}``, ``detail_has`` ``{check: [substrings]}``, ``stopped`` the session's
    S15 stop, ``reasons`` ``{run index: [substrings one of its VOID reasons must hold]}``."""
    want = {c: True for c in CHECKS}
    if cover_void:
        want["O8-COVER"] = None
        want.update({c: None for c in CORE})
    clauses = {("O8-" + k): v for k, v in (clauses or {}).items()}
    for c in list(fail) + list(clauses):
        cid = c if c.startswith("O8-") else "O8-" + c
        want[cid] = False
    dh = {("O8-" + k): v for k, v in (detail_has or {}).items()}

    def deco(fn):
        CASES.append((name, fn, want_verdict, want, clauses, tuple(report_has), void or {}, covered or {}, lacks or {},
                      dh, stopped, reasons or {}))
        return fn
    return deco


def _log_upto(place_: int, kind: str = "step"):
    """A log cut before its first ``kind`` row of place ``place_`` (a drive that stopped there)."""
    def apply(log, ctx):
        i = next((j for j, x in enumerate(log) if x.get("k") == kind and x.get("donor") == place_), len(log))
        return log[:i]
    return apply


def _steps(fn):
    """A log edit replacing the step rows of the cells ``fn(rows, ctx)`` maps: ``fn`` gets ``{(place, n): [rows]}`` and
    returns the new mapping for the places it changes; every other row kept in place."""
    def apply(log, ctx):
        by = {}
        for x in log:
            if x.get("k") == "step":
                by.setdefault((x["donor"], x["n"]), []).append(x)
        new = fn({k: [dict(x) for x in v] for k, v in by.items()}, ctx)
        out, done = [], set()
        for x in log:
            if x.get("k") == "step" and (x["donor"], x["n"]) in new:
                k = (x["donor"], x["n"])
                if k not in done:
                    out += new[k]
                    done.add(k)
                continue
            out.append(x)
        return out
    return apply


def _both(**kw):
    """A run edit for every run of both sides."""
    def fn(runs):
        for run in runs:
            run.update(kw)
        return runs
    return fn


SCOPE_REPORT = ("a US session", "block 3: 7 byte-equal of 7",
                "start dependence -- none in value or path: a raw warp into 164@342 at SC 1190",
                "164 ip57 Int16[9] 643 -> 385 here, 385 -> 385 after", "164 ip130 Byte[13] 1 -> 1 here, 2 -> 1 after",
                "166 e6 t1 ip345 Byte[208] 0 -> 0 here, 1 -> 0 after", "after the O1-O7 routes as driven",
                "Bit[3796] 0 (1 after)", "UInt16[19] 0 (1807 after)",
                "166 ip255 read Byte[8] 125; 164 ip130 read Byte[13] 1",
                "the end and the seam -- the arrival in REAL 55 on both sides; on F one seam",
                "166 e6 t1 ip502 (0), 166 e6 t1 ip863 (110)",
                "164 #1 at 64", "the movie -- FMV004 played out",
                "The session's end (end_run, warp first): the title came back")


@case("null-pair", "PROVEN", report_has=SCOPE_REPORT)
def _(pred):
    return six(pred)


# -- log edits ----------------------------------------------------------------------------------------------------------
def _step(place_, n, attempt=1, **kw):
    """A log edit: the base log's step row ``(place, n, attempt)`` updated with ``kw`` (a value ``...`` pops the key; a
    dict value for ``to`` / ``lost`` / ``route`` / ``at_y`` / ``wait_flag`` is merged into the row's own)."""
    def apply(log, ctx):
        row = ctx["steps"][(place_, n, attempt)]
        for k, v in kw.items():
            if v is ...:
                row.pop(k, None)
            elif isinstance(v, dict) and isinstance(row.get(k), dict):
                row[k] = {**row[k], **v}
                for kk in [kk for kk, vv in v.items() if vv is ...]:
                    row[k].pop(kk, None)
            else:
                row[k] = v
        return log
    return apply


def _chain(*edits):
    """Several log edits, in order."""
    def apply(log, ctx):
        for ed in edits:
            log = ed(log, ctx)
        return log
    return apply


def _knight(what, **kw):
    """A log edit: THE KNIGHT's ``seat`` / ``start1`` row updated."""
    def apply(log, ctx):
        ctx["knight"][what].update(kw)
        return log
    return apply


def _no_knight(what):
    """A log edit: THE KNIGHT's ``seat`` / ``start1`` row gone (the hook read no published sid there)."""
    def apply(log, ctx):
        row = ctx["knight"].get(what)
        return [x for x in log if x is not row]
    return apply


def _add(*rows):
    """A log edit: ``rows`` appended (the movie span's rows are read by frame, never by place in the log)."""
    def apply(log, ctx):
        return log + [copy.deepcopy(x) for x in rows]
    return apply


def _moved_knight(frame: int):
    """The events with THE KNIGHT's ip230 row at ``frame`` (its line kept: before ip243's)."""
    return lambda ev, n: edit(ev, lambda x: _is(x, KN230), lambda x: with_opt(x, f=frame))


def _one(runs: list, i: int, **kw) -> list:
    """Run ``i`` (1-based) updated with ``kw``."""
    runs[i - 1].update(kw)
    return runs


# -- the cases -------------------------------------------------------------------------------------------------------
@case("fork-drops-a-write", "NOT PROVEN", fail=("WRITES", "NULL", "STATE"), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """No 165 e2 t2 ip205 on F (165's e2 sets Byte[13] 3 before its chain row)."""
    return six(pred, f=lambda ev, n: drop_nth(ev, E2_165))


@case("knight-row-missing-F", "NOT PROVEN", fail=("WRITES", "NULL", "STATE"), clauses={"ORDER": ["(a)"],
                                                                                    "PATTERN": ["(b)"]})
def _(pred):
    """Every F run: the wait read (the bit published), no ip230 row in the trace."""
    return six(pred, f=lambda ev, n: drop_nth(ev, KN230))


@case("knight-after-exit-both", "NOT PROVEN", clauses={"ORDER": ["(b)", "(c)"], "PATTERN": ["(b)"], "LANDING": ["(b)"]})
def _(pred):
    """ip230 after e2's ip243 in every run (frame 4420, past the loss): ORDER (b) and (c), PATTERN (b) (visit 1's
    order), LANDING (b) (the row after ip243 is no 165 entry row) -- re-registered as rendered: (c) too, the row lying
    past THE EXEMPT SPAN as any row after the door does."""
    mv = lambda ev, n: move(ev, KN230, after_site=CH164)                  # noqa: E731
    return six(pred, s=mv, f=mv)


@case("knight-in-step1-both", "NOT PROVEN", clauses={"ORDER": ["(c)"], "WALK": ["(b)"]})
def _(pred):
    """ip230 at frame 3500, inside step 1 (past THE EXEMPT SPAN's right end, step 1's first frame0 3000), every run:
    ORDER (c) and WALK (b) (a row inside the visit's window, outside the span)."""
    return six(pred, s=_moved_knight(3500), f=_moved_knight(3500))


@case("knight-twice-both", "NOT PROVEN", clauses={"ORDER": ["(a)"], "PATTERN": ["(b)"]})
def _(pred):
    """A second ip230 row (1 -> 1, emitted same: the site's first same-value store) in every run: ORDER (a), PATTERN
    (b)."""
    again = lambda ev, n: after(ev, KN230, w(KN230))                     # noqa: E731
    return six(pred, s=again, f=again)


@case("knight-at-real-164-F", "NOT PROVEN", fail=("FORBIDDEN", "WRITES"),
      clauses={"ORDER": ["(a)"], "LANDING": ["(a)"], "SEAM": ["(a)", "(c)"], "WALK": ["(a)"]})
def _(pred):
    """Every F run: ip230 written at REAL 164 (fld 164, don 164) between 31256's rows -- ORDER (a), LANDING (a); and,
    re-registered as rendered: the row is across a second seam (31256 -> 164: SEAM (a) two seams, (c) its key), off the
    route on F (FORBIDDEN, unbacked), so the run's keys lack ip230 (WRITES; the comparison sets the seam key aside, so
    NULL, STATE and PATTERN -- which read places -- pass); and the driver's visit rows read the real field as a visit of
    164, so 164 #1's path-A landing finds the next visit row in 164 (WALK (a))."""
    real = lambda ev, n: edit(ev, lambda x: _is(x, KN230), lambda x: with_opt(x, fld=164, don=164))  # noqa: E731
    return six(pred, f=real)


@case("knight-fast-both", "PROVEN")
def _(pred):
    """ip230 at frame 2000, during step 0's walk before P1 (the knight released early): inside THE EXEMPT SPAN."""
    return six(pred, s=_moved_knight(2000), f=_moved_knight(2000))


def _slow(log, ctx):
    """THE KNIGHT WAIT 12 s long: the step-0 row's wait read at 3150, step 1 from 3200 (the seat and start1 rows with
    them)."""
    s0, s1 = ctx["steps"][(164, 0, 1)], ctx["steps"][(164, 1, 1)]
    s0.update(frame=3150, wait_flag=dict(s0["wait_flag"], frame=3150, s=12.5, game_s=12.5))
    s1.update(frame0=3200, **{"from": dict(s1["from"], frame=3200)})
    ctx["knight"]["seat"].update(frame=3150)
    ctx["knight"]["start1"].update(frame=3200)
    return log


@case("knight-slow-both", "PROVEN")
def _(pred):
    """THE KNIGHT WAIT 12 s long (ip230 at 3100, the wait read at 3150, step 1 from 3200): ip230 inside the span."""
    return _all(six(pred, s=_moved_knight(3100), f=_moved_knight(3100)), log=_slow)


def _failed_first(place_, n, *, until=1950, again=2000):
    """A log edit: step ``(place_, n)``'s first attempt FAILED (from its frame0 to ``until``, ended short of its goal),
    the done row attempt 2 from ``again``."""
    def fn(by, ctx):
        done = by[(place_, n)][-1]
        failed = dict(done, outcome="failed", attempt=1, frame=until, to=dict(done["to"], x=1100.0, z=2900.0),
                      why="the walk ended 200u from its goal", at_y=..., wait_flag=..., lost=None)
        failed = {k: v for k, v in failed.items() if v is not ...}
        failed.pop("flip_late", None)
        failed.pop("landed_frame", None)
        failed.pop("walkout", None)
        done.update(attempt=2, frame0=again, **{"from": dict(done["from"], frame=again)})
        done["route"] = dict(done["route"], basis="cached")
        done["route"].pop("basis_check", None)
        return {(place_, n): [failed, done]}
    return _steps(fn)


@case("knight-in-failed-attempt-both", "PROVEN")
def _(pred):
    """Step 0's first attempt failed (1500-1950), the done attempt from 2000; ip230 at 1900, INSIDE the failed attempt's
    row: inside THE EXEMPT SPAN (a done-row window would FAIL it: the unit knight-span-done-row)."""
    return _all(six(pred, s=_moved_knight(1900), f=_moved_knight(1900)), log=_failed_first(164, 0))


@case("knight-seat-off-F", "NOT PROVEN", clauses={"KNIGHT": ["(b)"]})
def _(pred):
    return _side(six(pred), "F", log=_knight("seat", x=-400.0, z=3900.0))


@case("knight-start1-moved-both", "NOT PROVEN", clauses={"KNIGHT": ["(b)"]})
def _(pred):
    return _all(six(pred), log=_knight("start1", z=3600.0))


@case("knight-seat-real-164-F", "NOT PROVEN", clauses={"KNIGHT": ["(a)"]})
def _(pred):
    """Every F run's seat reading in REAL 164 (its field 164): not the side's own field of the place."""
    return _side(six(pred), "F", log=_knight("seat", field=164))


@case("knight-unread-one-S", "PROVEN", void={1: ["A-KNIGHT"]}, covered={1: False, 3: True, 5: True},
      reasons={1: [O.KNIGHT_UNREAD]})
def _(pred):
    return _one(six(pred), 1, log=_no_knight("seat"))


def _start1_in_165(log, ctx):
    """Each start1 row written on a poll in 165 (path B: 164 #1's route_to returned after the switch): the row moves
    after 165's visit row, its field the 164 reading's."""
    row = ctx["knight"]["start1"]
    log = [x for x in log if x is not row]
    i = next(j for j, x in enumerate(log) if x.get("k") == "visit" and x.get("donor") == 165)
    return log[:i + 1] + [row] + log[i + 1:]


@case("knight-start1-path-b-both", "PROVEN")
def _(pred):
    return _all(six(pred), log=_start1_in_165)


@case("knight-unread-all-F", "NOT PROVEN", cover_void=True, clauses={"VOID-ASYM": ["(b)"]},
      void={2: ["A-KNIGHT"], 4: ["A-KNIGHT"], 6: ["A-KNIGHT"]})
def _(pred):
    """Every F run without its start1 row: A-KNIGHT on a whole side -- NOT set aside (VOID-ASYM (b)), COVER V."""
    return _side(six(pred), "F", log=_no_knight("start1"))


def _wait_void(v, by, why, *, field=None):
    """A run stopped in THE KNIGHT WAIT (164 #0): its trace to 164's ip764 then ``off`` in 164 (or ``field``), its step
    row void in class ``v``."""
    def edit_run(run):
        ev = upto_nth(run["events"], B13_164, 0, e("off", 164))
        _void(run, v, [164, 1190, 1], by, why, events=ev,
              log=_chain(_step(164, 0, outcome="void", v=v, by=by, why=why,
                               wait_flag=dict(wait_rec(read=False), published=0 if v == "V13" else 40)),
                         lambda lg, c: [x for x in lg if not (x.get("k") == "step" and x.get("n") == 1)
                                        and x.get("k") != "knight" and x.get("donor") != 165]))
        return run
    return edit_run


@case("wait-v8-one-S", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={1: False}, void={1: ["V8"]})
def _(pred):
    runs = six(pred)
    _wait_void("V8", "game", "the flag wait for Bit[3811] == 1 ran out on both clocks: the knight never sat")(runs[0])
    return runs


@case("wait-v11-game-one-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={2: False}, void={2: ["V11"]})
def _(pred):
    runs = six(pred)
    _wait_void("V11", "game", "the field left 31256 during the flag wait, nothing pressed: landed in 31255")(runs[1])
    return runs


@case("wait-unpublished-one-S", "PROVEN", covered={1: False, 3: True, 5: True}, void={1: ["V13"]})
def _(pred):
    runs = six(pred)
    _wait_void("V13", "driver", "the watch never published Bit[3811] at the wait's end (0 sample(s) carried it): the "
                                "instrument's")(runs[0])
    return runs


@case("v13-wait-deadline-one-F", "PROVEN", covered={2: False, 4: True, 6: True}, void={2: ["V13"]})
def _(pred):
    runs = six(pred)
    _wait_void("V13", "driver", "the run's budget ran out during the flag wait for Bit[3811] == 1: the budget")(runs[1])
    return runs


@case("chain-dropped-fork", "NOT PROVEN", fail=("CHAIN", "WRITES", "NULL", "STATE"),
      clauses={"LANDING": ["(b)"], "PATTERN": ["(b)"], "SEAM": ["(b)"]})
def _(pred):
    """No 165 e2 t2 ip233 on F: CHAIN, LANDING (b), WRITES, NULL, STATE, PATTERN (b); re-registered as rendered: SEAM (b)
    too -- the exit row ip863's old is 343, not the chain's 344."""
    return six(pred, f=lambda ev, n: drop_nth(ev, CH165))


@case("chain-first-old-wrong", "NOT PROVEN", fail=("CHAIN",))
def _(pred):
    old = lambda ev, n: edit(ev, lambda x: _is(x, CH164), lambda x: with_opt(x, old=315))   # noqa: E731
    return six(pred, s=old, f=old)


@case("chain-back-door-site-both", "NOT PROVEN", fail=("CHAIN", "WRITES"),
      clauses={"PATTERN": ["(b)"], "LANDING": ["(b)"], "ORDER": ["(b)"]})
def _(pred):
    """164's 343 written at e3 t2 ip243 (the back door's), not e2's, in every run: the value right, the site wrong --
    CHAIN (its key's site), WRITES, PATTERN (b); re-registered as rendered: LANDING (b)'s crossing and ORDER (b) both
    name e2's chain row, which no run holds. FORBIDDEN passes: the forbidden rules read writes off the route and the
    knight's talk -- a store in 164 itself is WRITES' to judge."""
    door = lambda ev, n: edit(ev, lambda x: _is(x, CH164), lambda x: w(BACK164))      # noqa: E731
    return six(pred, s=door, f=door)


@case("start-residue-three", "NOT PROVEN", fail=("START",))
def _(pred):
    """Byte 3's row missing (S): O6's three-row contract would pass it; O8's four rows fail it."""
    return six(pred, s=lambda ev, n: [x for x in ev if not (x[0] == "r" and x[1] == 70 and x[2] == 3)])


@case("start-residue-315", "NOT PROVEN", fail=("START",))
def _(pred):
    """Byte 2's row 0 -> 59 (O7's entrance 315) on S: the warp's entrance is not 342."""
    return six(pred, s=lambda ev, n: edit(ev, lambda x: x[0] == "r" and x[1] == 70 and x[2] == 2,
                                          lambda x: r(70, 2, 0, 59)))


@case("start-first-missing", "NOT PROVEN", fail=("START",), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """164's ip22 dropped on both sides: 164's first write is ip49 (START (b)) and visit 1's sequence is one row short
    (PATTERN (b)); 165's and 166's ip22 still write boot_scratch on both sides, so MASKED passes."""
    gone = lambda ev, n: drop_nth(ev, I22_164)                          # noqa: E731
    return six(pred, s=gone, f=gone)


@case("front-cut-write", "NOT PROVEN", fail=("START",))
def _(pred):
    """F: field 70's ip57 (Int16[9] := 643) as a row before the start -- no raced pin's row, so START (a) judges it."""
    in70 = ("w", 70, 0, 0, 57, "Global.Int16[9]", 643, {})
    return six(pred, f=lambda ev, n: before(ev, I22_164, in70))


@case("error-path-start-S", "PROVEN", void={1: ["V5", "A-START"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    """One S run: the warp's Byte[14] took 164's error path (ip178 := 9, window 56, ip607's reset): V5 by the driver at
    [164, 1190, 1], A-START -- the start's, the run uncovered."""
    runs = six(pred)
    _void(runs[0], "V5", [164, 1190, 1], "driver", "a stop page (164's error window 56), nothing pressed",
          events=upto_nth(runs[0]["events"], I138_164, 0, w(ERR164_178), w(ERR164_607), e("off", 164)),
          log=_log_upto(164))
    return runs


def _b8_old0(ev, n):
    return edit_nth(ev, B8_166, 0, lambda x: with_opt(x, old=0))


def _b13_old2(ev, n):
    return edit_nth(ev, I130_164, 0, lambda x: with_opt(x, old=2))


@case("byte8-early-warp-one-F", "PROVEN", void={2: ["A-START"]}, covered={2: False, 4: True, 6: True},
      reasons={2: [O.START_READ, "before its e0 t0 ip249"]})
def _(pred):
    """One F run: the warp left field 70 before its ip249, so 166 ip255 -- the route's first store of Byte[8] -- reads
    old 0: A-START by the start read, the run uncovered -- never PATTERN."""
    runs = six(pred)
    runs[1]["events"] = _b8_old0(runs[1]["events"], 0)
    return runs


@case("byte8-early-warp-all-F", "VOID", cover_void=True, void={2: ["A-START"], 4: ["A-START"], 6: ["A-START"]})
def _(pred):
    """Every F run reads old 0 at 166 ip255: the start's problem on a whole side -- COVER VOID, never NOT PROVEN."""
    return six(pred, f=_b8_old0)


@case("byte13-late-warp-all-F", "VOID", cover_void=True, void={2: ["A-START"], 4: ["A-START"], 6: ["A-START"]})
def _(pred):
    """Every F run's 164 ip130 reads old 2 (the warp after 70's ip475): COVER VOID, never NOT PROVEN by START (c) or
    PATTERN (critique #2)."""
    return six(pred, f=_b13_old2)


@case("byte13-late-warp-one-F", "PROVEN", void={2: ["A-START"]}, covered={2: False, 4: True, 6: True},
      reasons={2: [O.START_READ, "after its e0 t0 ip475"]})
def _(pred):
    """One F run: 164 ip130 reads old 2 -- the warp came after 70's ip475 (Byte[13] := 2), 164 taking no error path (K
    385): A-START naming ip475 (O7's race_site would name 70 ip130: the unit race-site8)."""
    runs = six(pred)
    runs[1]["events"] = _b13_old2(runs[1]["events"], 0)
    return runs


def _armed(site, old):
    """The run's field-70 store at ``site`` written after the arm, before the warp's residue rows."""
    return lambda ev, n: ev[:1] + [w(site, old=old)] + ev[1:]


@case("byte8-race-armed-one-F", "PROVEN", void={2: ["A-START"]}, covered={2: False, 4: True, 6: True},
      reasons={2: [O.START_READ, "ran after the trace was armed, before the warp"]})
def _(pred):
    runs = six(pred)
    runs[1]["events"] = _armed(RACE249, 0)(runs[1]["events"], 0)
    return runs


@case("byte13-race-armed-one-F", "PROVEN", void={2: ["A-START"]}, covered={2: False, 4: True, 6: True},
      reasons={2: [O.START_READ, "the warp came after the window's late edge"]})
def _(pred):
    runs = six(pred)
    runs[1]["events"] = _armed(RACE475, 1)(runs[1]["events"], 0)
    return runs


@case("byte13-explained-F", "NOT PROVEN", fail=("RESIDUE",), clauses={"START": ["(c)"], "PATTERN": ["(b)"]},
      lacks={2: ["A-START"], 4: ["A-START"], 6: ["A-START"]})
def _(pred):
    """Every F run: a harness ``r`` row on byte 13 (1 -> 2) after 164's ip22, then 164 ip130 reads old 2 -- EXPLAINED by
    the run's own earlier row, so no A-START: the run is covered and judged -- START (c), RESIDUE; re-registered as
    rendered: PATTERN (b) too (ip130 emitted as a change, same 0)."""
    return six(pred, f=lambda ev, n: _b13_old2(after(ev, I22_164, r(164, 13, 1, 2)), n))


@case("v5-error-165-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={2: False}, void={2: ["V5"]},
      lacks={2: ["A-START"]})
def _(pred):
    """165 takes the error path (an F run): V5 by the GAME at [165, 1190, 2] -- VOID-ASYM (a) -- and NO A-START: 164 is
    the start place."""
    runs = six(pred)
    _void(runs[1], "V5", [165, 1190, 2], "game", "a stop page (165's error window 56)",
          events=upto_nth(runs[1]["events"], I138_165, 0, w(ERR165_178), w(ERR165_687), e("off", 165)),
          log=_log_upto(165))
    return runs


@case("residue-after-start", "NOT PROVEN", fail=("RESIDUE",))
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, I22_164, r(164, 300, 0, 7)))


@case("writes-extra-symmetric", "NOT PROVEN", fail=("WRITES",), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """164 e2 t2 ip215's dead store (Byte[13] := 3) on both sides, right before its door's ip243 (after the loss): an
    extra key and an extra emitted tuple; STATE's histories symmetric; NULL symmetric."""
    add = lambda ev, n: before(ev, CH164, w(DEAD164_215))               # noqa: E731
    return six(pred, s=add, f=add)


@case("forbidden-row-both", "NOT PROVEN", fail=("WRITES", "FORBIDDEN"), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """164 e7 t11 ip399 (Byte[208] := 0: the talk's script) in every run, before the walk: an extra key, a forbidden
    site unbacked."""
    add = lambda ev, n: after(ev, B13_164, w(TALK164_399))              # noqa: E731
    return six(pred, s=add, f=add)


@case("talk-unbacked-both", "NOT PROVEN", fail=("WRITES", "FORBIDDEN"), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """The knight's talk (164 e1 t3 ip308 Bit[3851] := 1) in every run, no press near him: FORBIDDEN, unbacked."""
    add = lambda ev, n: after(ev, B13_164, w(TALK164_308))              # noqa: E731
    return six(pred, s=add, f=add)


@case("extra-key-one-F", "NOT PROVEN", fail=("STABLE", "WRITES", "STATE", "FORBIDDEN"), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """STABLE's mutant: one F run of three holds 164 e1 t3 ip627 (the talk's Bit[7211])."""
    return six(pred, f=lambda ev, n: after(ev, B13_164, w(TALK164_627)) if n == 0 else ev)


@case("sc-write-fork", "NOT PROVEN", fail=("NO-SC", "WRITES", "NULL", "STATE"))
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, B13_165, w(SC_CS, src="cs")))


@case("sc-harness-poke-both", "NOT PROVEN", fail=("NO-SC",))
def _(pred):
    poke = lambda ev, n: after(ev, B13_165, w((165, -1, -1, -1, "Global.Byte[0]", 7), src="harness"))  # noqa: E731
    return six(pred, s=poke, f=poke)


@case("c-row-165-F", "NOT PROVEN", clauses={"PATTERN": ["(a)"]})
def _(pred):
    """Every F run: a ``c`` row of 165 ip57 (n 1) -- its prologue ran twice: PATTERN (a) alone."""
    return six(pred, f=lambda ev, n: after(ev, I57_165, w(I57_165, count=True)))


@case("byte13-repeat-both", "NOT PROVEN", clauses={"PATTERN": ["(b)"]})
def _(pred):
    """A second 164 ip764 store 2 -> 2, emitted (``same`` 1), before the walk: symmetric, so STATE (a) cannot see it;
    visit 1's frozen sequence does."""
    again = lambda ev, n: after(ev, B13_164, w(B13_164))                # noqa: E731
    return six(pred, s=again, f=again)


@case("byte208-order-swap-both", "NOT PROVEN", clauses={"PATTERN": ["(b)"]})
def _(pred):
    """ip380 before ip345 in EVERY run: visit 3's frozen sequence differs -- PATTERN (b). Re-registered as rendered (the
    design named STATE (a) too): STATE (a) compares the covered runs' histories with each other, and a swap made in every
    run of both sides leaves them identical; the live end state is the log's."""
    swap = lambda ev, n: move(ev, M380, before_site=M345)               # noqa: E731
    return six(pred, s=swap, f=swap)


@case("visit-split-both", "NOT PROVEN", clauses={"PATTERN": ["(b)"], "LANDING": ["(b)"], "WALK": ["(a)"]})
def _(pred):
    """A row of 164 (its ip200 again, emitted) between 165's prologue rows on both sides: visit 2 split in two (PATTERN
    (b)), and place 164 written again after 165 loaded (LANDING (b)); re-registered as rendered: the driver's visit rows
    read a visit of 164 there, so 165 #1's path-A landing finds the next visit row in 164 (WALK (a))."""
    add = lambda ev, n: after(ev, I49_165, w(I200_164, emit=True))      # noqa: E731
    return six(pred, s=add, f=add)


@case("lands-real-165-covered", "NOT PROVEN", fail=("FORBIDDEN", "WRITES"),
      clauses={"LANDING": ["(a)", "(b)"], "SEAM": ["(a)", "(c)"], "WALK": ["(a)"]})
def _(pred):
    """Every F run's 165 rows at REAL 165: LANDING (a)(b), FORBIDDEN (off the route on F), WRITES; re-registered as
    rendered: the rows are across a second seam (31256 -> 165: SEAM (a), (c)) -- the comparison sets the seam keys aside,
    so NULL, STATE and PATTERN pass -- and the walks ran in real 165, not 31257 (WALK (a))."""
    real = lambda ev, n: edit(ev, lambda x: x[0] == "w" and x[1] == 165,  # noqa: E731
                              lambda x: with_opt(x, fld=165, don=165))
    return six(pred, f=real)


@case("harness-after-exit165-both", "NOT PROVEN", clauses={"LANDING": ["(b)"]})
def _(pred):
    """A harness row of place 165 between its ip233 and 166's ip22: (b)'s next row -- PATTERN reads script rows only."""
    poke = lambda ev, n: after(ev, CH165, w((165, -1, -1, -1, "Global.Byte[300]", 9), src="harness"))  # noqa: E731
    return six(pred, s=poke, f=poke)


@case("last-place-harness-S", "NOT PROVEN", clauses={"LANDING": ["(c)"], "SEAM": ["(e)"]})
def _(pred):
    """A harness row of place 166 after ip863 (before 55's ip22) on S: LANDING (c) -- the last field row before the cut
    is not ip863 -- and, re-registered as rendered, SEAM (e), which reads the same last row (nothing between the exit and
    the landing). S ONLY (the design's -both): on F that row would be the seam's exit, and storytrace.digest RAISES
    joining a harness row to a script position (_locate, ValueError) -- a kit defect O8's route cannot reach (O8 pokes
    nothing; research/o8_design.md 11.4, PART C as built)."""
    poke = lambda ev, n: after(ev, CH166, w((166, -1, -1, -1, "Global.Byte[300]", 9), src="harness"))  # noqa: E731
    return six(pred, s=poke)


@case("end-boundary-residue-both", "NOT PROVEN", clauses={"LANDING": ["(d)"], "SEAM": ["(d)"]})
def _(pred):
    """An ``r`` row in 55 before its ip22: the end cut lands on it -- LANDING (d) and, re-registered as rendered, SEAM (d)
    (the cut row is no ``w`` ip22 row)."""
    add = lambda ev, n: before(ev, END55, r(55, 300, 0, 1))            # noqa: E731
    return six(pred, s=add, f=add)


@case("end-row-missing-one-S", "PROVEN", void={1: ["A-NOEND"]}, covered={1: False, 3: True, 5: True},
      report_has=("A-NOEND",))
def _(pred):
    runs = six(pred)
    runs[0]["events"] = [x for x in runs[0]["events"] if not (x[0] == "w" and x[1] == 55)]
    return runs


@case("v19-one-F", "NOT PROVEN", fail=("FORBIDDEN",), clauses={"VOID-ASYM": ["(a)", "(c)"]}, covered={2: False})
def _(pred):
    """One F run lands in REAL 166 from member(165) (an un-retargeted Field()): V19 by the game at [166, 1190, 2]; the
    trace ends in real 166 after its first store -- off the route on F, unbacked: FORBIDDEN too."""
    runs = six(pred)
    ev = edit(runs[1]["events"], lambda x: x[0] == "w" and x[1] == 166, lambda x: with_opt(x, fld=166, don=166))
    _void(runs[1], "V19", [166, 1190, 2], "game", "the fork run entered REAL 166, where member(166) 31258 was due",
          events=upto_nth(ev, I22_166, 0, ("e", "off", 166, {"fld": 166})), log=_log_upto(166, "visit"))
    return runs


def _back_e3(run: dict, side: str, *, backed: bool) -> None:
    """164 #1 strays into the back door 164.e3: its store (e3 t2 ip243 := 343, Field(163)), then 163's prologue
    (member(163) 31255 on F) -- backed by the trigger's row V11 ``door`` 164.e3 ``landed`` 163 / 31255 when ``backed``."""
    ev = upto_nth(run["events"], KN230, 0, at(F_DOOR[164]), w(BACK164), *[w(s) for s in S163], e("off", 163))
    land = 163 if side == "S" else 31255

    def log(lg, c):
        st = c["steps"][(164, 1, 1)]
        i = lg.index(st)
        st.update(outcome="void", v="V11", by="driver", door="164.e3", landed=land, flip_frame=None,
                  lost={"frame": F_LOST[164], "control": False, "x": 1700.0, "z": 3000.0, "y": 6200.0,
                        "field": c["fld"][164]},
                  why=f"the trigger to 165 landed in {land} (place 163): control went in 164.e3, not 164.e2")
        for k in ("flip_late", "landed_frame", "walkout"):
            st.pop(k, None)
        return lg[:i + 1] if backed else lg[:i]
    if backed:
        _void(run, "V11", [164, 1190, 1], "driver", f"the trigger to 165 landed in {land}", events=ev, log=log)
    else:
        _void(run, "V11", [163, 1190, 2], "game", f"left the route: entered {land} (place 163)", events=ev, log=log)


@case("back-door-e3-S", "PROVEN", void={1: ["V11", "A-FORBIDDEN"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    """One S run's 164 #1 takes the back door e3: its store, then rows in 163 -- off the route, BACKED by the trigger's
    V11 landing in 163: A-FORBIDDEN, never a finding."""
    runs = six(pred)
    _back_e3(runs[0], "S", backed=True)
    return runs


@case("back-door-unbacked-F", "NOT PROVEN", fail=("FORBIDDEN",), clauses={"VOID-ASYM": ["(a)"]}, covered={2: False})
def _(pred):
    """One F run holds e3 t2 ip243's row and rows in 31255 that no step row explains: FORBIDDEN's finding; its drive VOID
    V11 by the game (rule 2, no walk behind it) on F only -- VOID-ASYM (a)."""
    runs = six(pred)
    _back_e3(runs[1], "F", backed=False)
    return runs


@case("back-door-165-S", "PROVEN", void={1: ["V11"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    """One S run takes 165's back door: e3's store (ip243 Int16[2] := 344), then 164's prologue out of order -- rule 3's
    V11 by the driver on the walked row: the run uncovered."""
    runs = six(pred)
    ev = upto_nth(runs[0]["events"], B13_165, 0, at(F_LOST[165] + 10), w(BACK165),
                  *[w(s, emit=True) for s in PRO[164]], e("off", 164))

    def log(lg, c):
        st = c["steps"][(165, 0, 1)]
        i = lg.index(st)
        st.update(outcome="interrupted", landed=None, door="165.e3",
                  lost={"frame": F_LOST[165], "control": False, "x": 1700.0, "z": 2700.0, "y": 10600.0,
                        "field": c["fld"][165]}, why="control went in 165.e3 and the field held 5s")
        return lg[:i + 1]
    _void(runs[0], "V11", [165, 1190, 2], "driver", "the walked row's landing: 164 out of the route's order", events=ev,
          log=log)
    return runs


def _stall_pinch(run: dict) -> None:
    """A run stopped in THE PINCH: 164 #1 failed 3 of its 3 attempts (V7 by the driver at [164, 1190, 1])."""
    ev = upto_nth(run["events"], KN230, 0, e("off", 164))
    _void(run, "V7", [164, 1190, 1], "driver", "step 164 #1: the second spiral (trigger) failed 3 of its 3 attempts",
          events=ev, log=_log_upto(164))


@case("v7-pinch-one-S", "PROVEN", void={1: ["V7"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    runs = six(pred)
    _stall_pinch(runs[0])
    return runs


@case("v7-pinch-all-F", "NOT PROVEN", cover_void=True, clauses={"VOID-ASYM": ["(b)"]})
def _(pred):
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            _stall_pinch(run)
    return runs


def _v13(run: dict, why: str, cell=(164, 1190, 1), *, at_site=B13_164, where=164) -> None:
    """A run stopped by the driver's instrument (V13 by the driver) after ``at_site``'s row, ``off`` in ``where``."""
    _void(run, "V13", list(cell), "driver", why, events=upto_nth(run["events"], at_site, 0, e("off", where)),
          log=_log_upto(where))


V13_PRIOR = "the prior basis disagreed with the first move: 164's seeded basis 31 deg off"
V13_LOSS_Y = "the loss's height unread off the ring: the y-until cannot be judged"


@case("v13-prior-one-F", "PROVEN", void={2: ["V13"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    runs = six(pred)
    _v13(runs[1], V13_PRIOR)
    return runs


@case("v13-prior-all-F", "NOT PROVEN", cover_void=True, clauses={"VOID-ASYM": ["(b)"]})
def _(pred):
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            _v13(run, V13_PRIOR)
    return runs


@case("v13-loss-y-one-F", "PROVEN", void={2: ["V13"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    runs = six(pred)
    _v13(runs[1], V13_LOSS_Y, at_site=KN230)
    return runs


@case("v13-loss-y-all-F", "NOT PROVEN", cover_void=True, clauses={"VOID-ASYM": ["(b)"]})
def _(pred):
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            _v13(run, V13_LOSS_Y, at_site=KN230)
    return runs


@case("v13-input-one-F", "PROVEN", void={2: ["V13"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    runs = six(pred)
    _v13(runs[1], "outside input: an input row (a key the driver never sent)", (165, 1190, 2), at_site=B13_165,
         where=165)
    return runs


@case("v14-one-S", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={1: False}, void={1: ["V14"]})
def _(pred):
    """One S run VOID V14 by the GAME in 166 (a dialog the net could not answer): a game class on one side."""
    runs = six(pred)
    _void(runs[0], "V14", [166, 1190, 3], "game", "a dialog no rule answers, its options unread",
          events=upto_nth(runs[0]["events"], M502, 0, e("off", 166)), log=_log_upto(166, "visit"))
    return runs


def _off_at(fld: int):
    return lambda ev, n: edit(ev, lambda x: x[0] == "e" and x[1] == "off", lambda x: ("e", "off", 55, {"fld": fld}))


@case("seam-zero-F", "NOT PROVEN", clauses={"SEAM": ["(a) no seam"]})
def _(pred):
    """Every F run's ``e off`` row renumbered to fld 31258: the trace never stands in a real field after the members --
    SEAM (a) "no seam: the run never left the members", never a vacuous pass."""
    return six(pred, f=_off_at(31258))


@case("seam-two-F", "NOT PROVEN", clauses={"SEAM": ["(a)", "2 seams"]})
def _(pred):
    """Every F run: an ``e`` row stamped at REAL 164 between 31257's and 31258's rows (an epoch opened there): two
    seams, 31257 -> 164 and 31258 -> 55 -- SEAM (a)."""
    return six(pred, f=lambda ev, n: before(ev, I22_166, ("e", "swap", 164, {"fld": 164})))


@case("seam-exit-wrong-F", "NOT PROVEN", fail=("CHAIN", "WRITES", "NULL", "STATE"),
      clauses={"SEAM": ["(b)", "(e)"], "LANDING": ["(c)"], "MOVIE": ["(b)"], "PATTERN": ["(b)"]})
def _(pred):
    """Every F run without ip863: the seam's exit row is 31258's ip502 -- SEAM (b); re-registered as rendered: the chain
    and the writes lack ip863 (CHAIN, WRITES, NULL, STATE), LANDING (c) and SEAM (e) read ip502 as the last row, PATTERN
    (b) visit 3 one short, and FMV004's span has no closing row (MOVIE (b))."""
    return six(pred, f=lambda ev, n: drop_nth(ev, CH166))


@case("seam-key-F", "NOT PROVEN", fail=("FORBIDDEN", "STATE"), clauses={"SEAM": ["(a)", "(c)", "(e)"],
                                                                     "LANDING": ["(a)"]})
def _(pred):
    """Every F run: a ``w`` row at REAL 163 after ip863 (163's ip57 Int16[9] := 385, a key): across the seam -- SEAM (a) (31258 -> 163, not 55),
    (c) its key, (e) the last row before the cut; re-registered as rendered: FORBIDDEN (off the route, unbacked), LANDING
    (a) (a row in a place off the route) and STATE (Int16[9]'s emitted history one write longer on F)."""
    return six(pred, f=lambda ev, n: after(ev, CH166, w(S163[2], fld=163, don=163)))


@case("cut-row-don-wrong-F", "NOT PROVEN", clauses={"SEAM": ["(d)"]})
def _(pred):
    """Every F run's cut row at fld 55 names don 31205 (O1's member(55)): SEAM (d) alone -- REAL 55 is don 55."""
    return six(pred, f=lambda ev, n: edit(ev, lambda x: _is(x, END55), lambda x: with_opt(x, don=31205)))


@case("seam-residue-before-cut-F", "NOT PROVEN", fail=("RESIDUE",), clauses={"SEAM": ["(e)"]})
def _(pred):
    """Every F run: an ``r`` row at 31258 after ip863, before 55's ip22 -- SEAM (e) (something between the exit and the
    landing) with RESIDUE."""
    return six(pred, f=lambda ev, n: after(ev, CH166, r(166, 300, 0, 5)))


@case("cut-row-not-ip22-both", "NOT PROVEN", clauses={"SEAM": ["(d)"], "LANDING": ["(d)"]})
def _(pred):
    """55's ip22 dropped in every run: the cut lands on ip49 -- SEAM (d), LANDING (d)."""
    gone = lambda ev, n: drop_nth(ev, END55)                            # noqa: E731
    return six(pred, s=gone, f=gone)


# -- O8-WALK's mutants (5.3: (a)'s nine, (b)'s three, (c)'s three) and its PASS cases -------------------------------
@case("walk-no-step-both", "NOT PROVEN", clauses={"WALK": ["(a) (165, 2) #1: 0 done row(s)"]})
def _(pred):
    """165 #1's step row absent from every run's log: its step not done -- WALK (a)."""
    return _all(six(pred), log=_steps(lambda by, ctx: {(165, 1): []}))


@case("walk-short-both", "NOT PROVEN", clauses={"WALK": ["(a) (164, 1) #0", "from the goal"]})
def _(pred):
    return _all(six(pred), log=_step(164, 0, to={"x": 1142.0, "z": 2252.0}))


@case("walk-wrong-level-both", "NOT PROVEN", clauses={"WALK": ["(a) (164, 1) #0", "not the goal's level"]})
def _(pred):
    """164 #0's arrival read at published y 13893 (tri 98's level, over P1): outside at_y."""
    return _all(six(pred), log=_step(164, 0, at_y={"y": 13893.0}))


@case("walk-wait-unread-both", "NOT PROVEN", clauses={"WALK": ["(a) (164, 1) #0", "wait_flag"]})
def _(pred):
    return _all(six(pred), log=_step(164, 0, wait_flag={"read": False}))


@case("trigger-lost-low-both", "NOT PROVEN", clauses={"WALK": ["(a) (164, 1) #1", "does not satisfy its until"]})
def _(pred):
    """164 #1's loss read at y 11500: under its until y > 12000 (the door cannot fire there)."""
    return _all(six(pred), log=_step(164, 1, lost={"y": 11500.0}))


@case("trigger-lost-no-y-both", "NOT PROVEN", clauses={"WALK": ["(a) (164, 1) #1", "has no height"]})
def _(pred):
    """164 #1's loss without a ``y``: "no height" -- never until_ok's raise (THROW stays clean)."""
    return _all(six(pred), log=_step(164, 1, lost={"y": ...}))


def _landed_164(log, ctx):
    ctx["steps"][(165, 1, 1)].update(landed=ctx["fld"][164])
    return log


@case("trigger-landed-wrong-both", "NOT PROVEN", clauses={"WALK": ["(a) (165, 2) #1", "landed"]})
def _(pred):
    """165 #1's done row ``landed`` in 164's field (the side's own): not 166's."""
    return _all(six(pred), log=_landed_164)


@case("trigger-landed-none-no-frame-both", "NOT PROVEN", clauses={"WALK": ["(a) (164, 1) #1", "no landed_frame"]})
def _(pred):
    return _all(six(pred), log=_step(164, 1, landed_frame=None))


@case("trigger-lost-in-e3-both", "NOT PROVEN", clauses={"WALK": ["(a) (164, 1) #1", "beyond exit_slack"]})
def _(pred):
    """164 #1's loss read inside 164.e3 at y 13008 (its until holds): not in or near its door 164.e2."""
    return _all(six(pred), log=_step(164, 1, lost={"x": 1700.0, "z": 3000.0}))


@case("walk-window-row-both", "NOT PROVEN", clauses={"WALK": ["(b)"]})
def _(pred):
    """164 ip764's row stamped at frame 2000, inside 164's window (its walk): WALK (b)."""
    stamp = lambda ev, n: edit(ev, lambda x: _is(x, B13_164), lambda x: with_opt(x, f=2000))   # noqa: E731
    return six(pred, s=stamp, f=stamp)


@case("door-row-before-step-both", "NOT PROVEN", clauses={"WALK": ["(b)"]})
def _(pred):
    """164 e2 t2 ip243's row stamped at frame 2800, inside step 0's window before step 1's first frame0 (3000): a door
    site is exempt only after its trigger began -- WALK (b) (its line still after ip230's, so ORDER passes)."""
    stamp = lambda ev, n: edit(ev, lambda x: _is(x, CH164), lambda x: with_opt(x, f=2800))    # noqa: E731
    return six(pred, s=stamp, f=stamp)


@case("knight-outside-span-both", "NOT PROVEN", clauses={"WALK": ["(b)"], "ORDER": ["(c)"]})
def _(pred):
    """ip230 at frame 4000 (step 1's walk, past the span): WALK (b) and ORDER (c)."""
    return six(pred, s=_moved_knight(4000), f=_moved_knight(4000))


@case("basis-check-missing-both", "NOT PROVEN", clauses={"WALK": ["(c)", "carry basis_check"]})
def _(pred):
    return _all(six(pred), log=_step(164, 0, route={"basis_check": ...}))


@case("basis-check-30deg-both", "NOT PROVEN", clauses={"WALK": ["(c)", "deg off the prior"]})
def _(pred):
    return _all(six(pred), log=_step(164, 0, route={"basis_check": {"angle": 30.0, "moved": 58.0, "frame": 1550,
                                                                    "pressed": "left"}}))


@case("basis-cached-run3-S", "NOT PROVEN", clauses={"WALK": ["(c)", "S#3", "not 'prior'"]})
def _(pred):
    """Run 3 (S)'s 164 #0 route basis "cached": the per-run forget missed -- that run judged no first move of its own."""
    return _one(six(pred), 3, log=_step(164, 0, route={"basis": "cached"}))


@case("walk-failed-once-164-both", "PROVEN")
def _(pred):
    """164 #0's first attempt failed (ended short), the second done: within its attempts (3)."""
    return _all(six(pred), log=_failed_first(164, 0))


def _trigger_failed_twice(by, ctx):
    rows = by[(164, 1)]
    done = rows[-1]
    out = []
    for k, (f0, f1) in enumerate(((3000, 3300), (3400, 3700))):
        out.append({**{x: v for x, v in done.items() if x not in ("flip_late", "landed_frame", "walkout")},
                    "outcome": "failed", "attempt": k + 1, "frame0": f0, "frame": f1, "lost": None, "landed": None,
                    "flip_frame": None, "why": "the walk ended 150u from its goal",
                    "to": {"frame": f1, "control": True, "x": 900.0, "z": 4500.0},
                    "route": dict(done["route"], basis="cached")})
        out[-1]["route"].pop("basis_check", None)
    done.update(attempt=3, frame0=3800, **{"from": dict(done["from"], frame=3800)})
    return {(164, 1): out + [done]}


@case("trigger-failed-twice-164-both", "PROVEN")
def _(pred):
    """164 #1 failed twice (THE PINCH), the third attempt done: two failed rows under its attempts 3."""
    return _all(six(pred), log=_steps(_trigger_failed_twice))


def _interrupted_165(by, ctx):
    done = by[(165, 0)][-1]
    inter = {**{x: v for x, v in done.items() if x not in ("at_y",)}, "outcome": "interrupted", "attempt": 1,
             "frame": 5400, "lost": {"frame": 5395, "control": False, "x": 1800.0, "z": 4000.0, "y": 10900.0,
                                     "field": done["field"]},
             "why": "control went outside every exit"}
    done.update(attempt=2, frame0=5450, **{"from": dict(done["from"], frame=5450)})
    done["route"] = dict(done["route"], basis="cached")
    done["route"].pop("basis_check", None)
    return {(165, 0): [inter, done]}


@case("interrupted-once-165-both", "PROVEN")
def _(pred):
    """165 #0 interrupted once (control went outside every exit), then done: within its interrupts (1)."""
    return _all(six(pred), log=_steps(_interrupted_165))


def _path_b(log, ctx):
    for p, q in ((164, 165), (165, 166)):
        st = ctx["steps"][(p, 1, 1)]
        st.update(landed=ctx["fld"][q], flip_frame=F_LOST[p] + 20)
        for k in ("flip_late", "landed_frame", "walkout"):
            st.pop(k, None)
    return log


@case("trigger-path-b-both", "PROVEN")
def _(pred):
    """Both doors' done rows ``landed`` the next place's field (path B: the switch waited out in the executor)."""
    return _all(six(pred), log=_path_b)


@case("door-row-late-loss-both", "PROVEN")
def _(pred):
    """164 #1's loss read late (frame 4440, 30 frames after the door's ip243 row at 4410): ip243 inside the window --
    exempt by SITE after the trigger's first frame0, never bounded by the read loss."""
    return _all(six(pred), log=_step(164, 1, lost={"frame": 4440}))


# -- O8-MOVIE's cases -----------------------------------------------------------------------------------------------
SKIP_TEXT = {"options": ["Do you want to skip the movie?", "Yes", "No"], "active": [0, 1], "selected": 1, "count": 2}
SKIP_EMPTY = {"options": ["", "Yes", "No"], "active": [0, 1], "selected": 1, "count": 2}
SCRIPT_CHOICE = {"options": ["Which way?", "Up", "Down", "Stay"], "active": [0, 1, 2], "selected": 0, "count": 3}


def _movie_rows(*rows):
    """A log edit: rows laid into 166's visit (their field the side's own of 166)."""
    def apply(log, ctx):
        fld = ctx["fld"][166]
        return log + [dict(copy.deepcopy(x), field=fld) for x in rows]
    return apply


def _choice_row(frame: int, ch: dict, *, rule="movie_skip_default", index="default") -> dict:
    return {"k": "choice", "donor": 166, "sc": 1190, "frame": frame, **ch, "index": index, "rule": rule,
            "took": {"index": index}}


def _stray(frame: int = 8500, *, why="movie_poke") -> dict:
    return press(0, 166, 3, frame, "", 900, why=why)


@case("movie-script-choice-F", "NOT PROVEN", clauses={"MOVIE": ["(a)", "of another shape"]})
def _(pred):
    """Every F run's movie span holds a three-line choice row (cursor on 0, the net's default taken): a script's choice
    where stock has none -- covered (no skip shape), MOVIE (a) FAILS it."""
    return _side(six(pred), "F", log=_movie_rows(_choice_row(8500, SCRIPT_CHOICE, rule=1)))


@case("movie-short-F", "NOT PROVEN", clauses={"MOVIE": ["(b)", "under file_s - slack_s"]})
def _(pred):
    """Every F run's ip863 930 frames after ip502 (30 s at its clocked 31 fps): MOVIE (b)."""
    return six(pred, f=lambda ev, n: edit(ev, lambda x: _is(x, CH166), lambda x: with_opt(x, f=F_502 + 930)))


@case("movie-press-in-span-one-S", "PROVEN", void={1: ["A-MOVIE"]}, covered={1: False, 3: True, 5: True},
      reasons={1: [O.MOVIE_SPAN, "the driver's press at frame 8500"]})
def _(pred):
    return _one(six(pred), 1, log=_movie_rows(_stray(why="page")))


@case("movie-stray-answered-one-S", "PROVEN", void={1: ["A-MOVIE"]}, covered={1: False, 3: True, 5: True},
      reasons={1: [O.MOVIE_SPAN, "answered at its default"]})
def _(pred):
    return _one(six(pred), 1, log=_movie_rows(_stray(), _choice_row(8520, SKIP_TEXT)))


@case("movie-skip-unbacked-one-F", "PROVEN", void={2: ["A-MOVIE"]}, covered={2: False, 4: True, 6: True},
      reasons={2: [O.MOVIE_SPAN, "outside input"]})
def _(pred):
    """One F run: a skip dialog seen in the span with no press of the driver's behind it -- the instrument's (only a
    Confirm opens it), never the fork's."""
    return _one(six(pred), 2, log=_movie_rows({"k": "skip_seen", "frame": 8500, "options": SKIP_TEXT["options"],
                                               "prompt_empty": False}))


@case("movie-skip-empty-prompt-one-S", "PROVEN", void={1: ["A-MOVIE"]}, covered={1: False, 3: True, 5: True},
      reasons={1: [O.MOVIE_SPAN, "a skip dialog at frame 8520"]})
def _(pred):
    """One S run: a stray press, then the skip dialog published with an EMPTY prompt -- read by its SHAPE."""
    return _one(six(pred), 1, log=_movie_rows(_stray(), _choice_row(8520, SKIP_EMPTY)))


def _unclocked(log, ctx):
    keep = [x for x in ctx["clocks"] if not F_502 < x["frame"] <= F_863]
    one = next(x for x in ctx["clocks"] if F_502 < x["frame"] <= F_863)
    return [x for x in log if x.get("k") != "clock" or x in keep or x is one]


@case("movie-unclocked-one-S", "PROVEN", void={1: ["A-MOVIE"]}, covered={1: False, 3: True, 5: True},
      reasons={1: [O.MOVIE_SPAN, "unclocked (1 clock rows with a write time)"]})
def _(pred):
    return _one(six(pred), 1, log=_unclocked)


@case("movie-stray-answered-all-S", "VOID", cover_void=True, void={1: ["A-MOVIE"], 3: ["A-MOVIE"], 5: ["A-MOVIE"]})
def _(pred):
    """Every S run: a stray press and the skip dialog answered No -- A-MOVIE on a whole side, set aside by VOID-ASYM (b):
    COVER VOID, never NOT PROVEN."""
    return _side(six(pred), "S", log=_movie_rows(_stray(), _choice_row(8520, SKIP_TEXT)))


def _reanchor(*pairs):
    """The events with each ``at(old)`` anchor moved to ``at(new)``."""
    m = dict(pairs)
    return lambda ev, n: [("at", m.get(x[1], x[1])) if x[0] == "at" else x for x in ev]


def _clocked(fps: float, hi: int):
    def apply(log, ctx):
        new = clock_rows(ctx["fld"][166], hi=hi, fps=fps)
        return [x for x in log if x.get("k") != "clock"] + new
    return apply


@case("movie-fps-60-both", "PROVEN")
def _(pred):
    """FMV004 at 60 fps: 2730 frames from ip502 to ip863, clocked at 60 -- 45.5 s."""
    ev = _reanchor((F_863, F_502 + 2730), (F_END, F_502 + 2740))
    return _all(six(pred, s=ev, f=ev), log=_clocked(60.0, F_502 + 2740))


@case("movie-fps-31-both", "PROVEN")
def _(pred):
    """FMV004 at 31 fps: 1411 frames, clocked at 31 -- 45.5 s (the base run's rate, re-clocked from its own rows)."""
    return _all(six(pred), log=_clocked(31.0, F_END))


def _mtime_none(log, ctx):
    hits = [x for x in ctx["clocks"] if F_502 < x["frame"] <= F_863][3:5]
    for x in hits:
        x["mtime"] = None
    return log


@case("movie-clock-mtime-none-both", "PROVEN")
def _(pred):
    """Two clock rows in the span with no write time (state.json's mtime None): skipped, enough others."""
    return _all(six(pred), log=_mtime_none)


def _press_at_502(log, ctx):
    ctx["presses"][-1]["pre"]["frame"] = F_502
    return log


@case("movie-press-at-f502-both", "PROVEN")
def _(pred):
    """The 313 page press decided at frame f502 itself: outside the half-open span (f502, f863]."""
    return _all(six(pred), log=_press_at_502)


# -- coverage beats, the end, the end state ---------------------------------------------------------------------------
@case("w164-beat-missing", "VOID", cover_void=True, void={1: ["A-BEATS"], 3: ["A-BEATS"]})
def _(pred):
    runs = six(pred)
    for run in (runs[0], runs[2]):
        run["beats"] = dict({b: True for b in pred["beats"]}, w164_p1=False)
    return runs


@case("t165-beat-missing", "VOID", cover_void=True, void={1: ["A-BEATS"], 3: ["A-BEATS"]})
def _(pred):
    runs = six(pred)
    for run in (runs[0], runs[2]):
        run["beats"] = dict({b: True for b in pred["beats"]}, t165_e2=False)
    return runs


@case("end-cut", "PROVEN")
def _(pred):
    """More rows in 55 past the end (S): 55's prologue stored a second time -- all cut."""
    return six(pred, s=lambda ev, n: ev[:-1] + [w(x) for x in [END55] + POST55] + [ev[-1]])


def _end_state(pred: dict, **kv) -> dict:
    return dict(pred["end_state"], **{f"Global.{k}": v for k, v in kv.items()})


@case("end-state-differs", "NOT PROVEN", clauses={"STATE": ["(b)"]})
def _(pred):
    runs = six(pred)
    runs[3]["end_state"] = _end_state(pred, **{"Bit[3811]": 0})
    return runs


@case("int16-2-live-race-both", "PROVEN")
def _(pred):
    """Every run's arrival with Int16[2] 106 live (55's ip255 raced it): never compared -- Int16[2] is not in
    ``end_state`` (segment_drive.read_end_state reads its variables alone); its value is the trace's (STATE (c))."""
    return _all(six(pred), end_state=dict(pred["end_state"]), pages=lambda pg: pg + ["Int16[2] live 106"])


@case("byte8-live-race-both", "PROVEN")
def _(pred):
    """Every run's arrival with Byte[8] 125 live (55's ip342 raced it): never compared, as Int16[2]'s."""
    return _all(six(pred), end_state=dict(pred["end_state"]), pages=lambda pg: pg + ["Byte[8] live 125"])


@case("int16-2-trace-end-F", "NOT PROVEN", fail=("RESIDUE",), clauses={"STATE": ["(c)"], "SEAM": ["(e)"]})
def _(pred):
    """Every F run: a C# ``r`` row on Int16[2]'s low byte (byte 2: 110 -> 111) at 31258 after ip863: STATE (c) (its last
    pre-cut row is not ip863), RESIDUE; re-registered as rendered: SEAM (e) (a row between the exit and the landing).
    CHAIN passes: it reads the script writes over bytes 2-3, and a residue row is RESIDUE's."""
    return six(pred, f=lambda ev, n: after(ev, CH166, r(166, 2, 110, 111)))


@case("byte8-trace-wrong-site-both", "NOT PROVEN", fail=("WRITES",),
      clauses={"STATE": ["(c)"], "PATTERN": ["(b)"], "MOVIE": ["(b)"]})
def _(pred):
    """ip502 dropped in every run: Byte[8]'s last pre-cut row is ip255's 125 -- STATE (c); re-registered as rendered:
    WRITES, PATTERN (b), and FMV004's span has no opening row (MOVIE (b))."""
    gone = lambda ev, n: drop_nth(ev, M502)                             # noqa: E731
    return six(pred, s=gone, f=gone)


@case("masked-differs", "NOT PROVEN", fail=("MASKED",), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """Every F run without its Bit[184] rows: MASKED reads the region gone on F; PATTERN reads every visit short."""
    return six(pred, f=lambda ev, n: [x for x in ev if not (x[0] == "w" and x[5] == "Global.Bit[184]")])


@case("join-failure", "NOT PROVEN", fail=("JOIN",))
def _(pred):
    """An extra row at 166 e6 t1 ip346 (one byte into ip345's store) in every run: JOIN alone -- PATTERN reads only rows
    that join, STATE only keyed rows."""
    off = (166, 6, 1, 346, "Global.Byte[208]", 0)
    add = lambda ev, n: after(ev, M345, w(off))                         # noqa: E731
    return six(pred, s=add, f=add)


@case("mismatched", "PROVEN", void={2: ["A-MISMATCH"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    return six(pred, f=lambda ev, n: edit(ev, lambda x: x[0] == "w" and x[1] == 165,
                                          lambda x: with_opt(x, don=31244)) if n == 0 else ev)


@case("no-start-row", "PROVEN", void={1: ["A-NOSTART"]}, covered={1: False})
def _(pred):
    runs = six(pred)
    runs[0]["events"] = base_events()[:5] + [e("off", 70)]
    runs[0]["log"] = lambda lg, c: []
    return runs


@case("trace-without-off", "VOID", cover_void=True)
def _(pred):
    runs = six(pred)
    for run in (runs[0], runs[2]):
        run["events"] = run["events"][:-1]
    return runs


@case("install-changed", "VOID", cover_void=True)
def _(pred):
    runs = six(pred)
    for run in (runs[1], runs[3]):
        run["install"] = "during the run: 1 changed: engine"
    return runs



# ======================================================================== the story-o3 seam fixture
#: story-o3's archived session (research/o8_design.md 8): the MAIN repo's archive, read-only -- missing FAILS, never skips.
O3_SESSION = Path(r"C:\gd\Dream-World-IX\.harness-runs\20261001-095552-story-o3")
O3_FROZEN = "o3_predictions_v1.json"
#: The fixture's STATE (c) registration -- typed here as the check's INPUT, never derived and never a claim of O3's.
O3_TRACE_REG = {"Global.Int16[2]": {"value": 100, "site": {"place": 63, "sid": 4, "tag": 1, "ip": 820}},
                "Global.Byte[8]": {"value": 125, "site": {"place": 63, "sid": 14, "tag": 1, "ip": 805}}}


def o3_frozen() -> dict:
    """O3's frozen predictions, read through :func:`frozen_through` (closed at 8)."""
    path = next(f for f in frozen_through(8) if f.name == O3_FROZEN)
    return json.loads(path.read_text(encoding="utf-8"))


def entry_of(stock):
    """A place's ENTRY row off its stock bytes (research/o8_design.md 8, 0.2 #14): its Main_Init's first global store --
    62's ip26 Bit[191] := 0, not ip22 -- as a landing site."""
    def entry(p):
        ip, _rel, t = next(x for x in O._items8(stock(p), 0, 0) if x[2].startswith("SET({Global.") and "B_LET" in x[2])
        m = O.re.match(r"^SET\(\{(Global\.\w+\[\d+\]) const\((\d+)\) B_LET B_EXPR_END\}\)$", t)
        return {"place": p, "sid": 0, "tag": 0, "ip": ip, "target": m.group(1), "value": O._const8(int(m.group(2)))}
    return entry


def o3_seam(pred3: dict) -> dict:
    """seam3, READ off O3's frozen chain (:func:`o8_west_tower.seam_spec`): its last key member(63) 31213 e4 t1 ip820
    Int16[2] 0 -> 100, to 64, fields [64], the cut row O3's landing's end row."""
    return O.seam_spec({"seam": {"donor": pred3["seam"]["donor"], "to": pred3["seam"]["to"]},
                        "chain": pred3["chain"], "landing": {"end_row": pred3["landing"]["end_row"]},
                        "entrance": pred3["entrance"]})


def o3_landing_pred(pred3: dict, stock, *, entry=None) -> dict:
    """O3's predictions with an O8 landing spec built from O3's frozen chain the way :func:`o8_west_tower._landing8`
    builds O8's (end 64; each place's entry row read off the stock bytes)."""
    p = copy.deepcopy(pred3)
    p["landing"] = O._landing8(pred3["chain"], end=int(pred3["end_field"]), entry=entry or entry_of(stock))
    return p


def _o3_copy(tmp: Path, mutate=None) -> Path:
    """A copy of the archived session (its session file, scripts and every run's trace and log), each F run's trace rows
    passed through ``mutate(rows) -> rows`` (raw dicts) -- the archive itself never written."""
    d = tmp / f"o3s{len(list(tmp.iterdir()))}"
    (d / "scripts").mkdir(parents=True)
    for f in (O3_SESSION / "scripts").iterdir():
        (d / "scripts" / f.name).write_bytes(f.read_bytes())
    session = json.loads((O3_SESSION / "o3_session.json").read_text(encoding="utf-8"))
    (d / "o3_session.json").write_text(json.dumps(session), encoding="utf-8")
    for rec in session["runs"]:
        for key in ("trace", "log"):
            if rec.get(key) and (O3_SESSION / rec[key]).is_file():
                data = (O3_SESSION / rec[key]).read_bytes()
                if key == "trace" and rec["side"] == "F" and mutate is not None:
                    rows = [json.loads(ln) for ln in data.decode("utf-8").splitlines() if ln.strip()]
                    data = "".join(json.dumps(x) + "\n" for x in mutate(rows)).encode("utf-8")
                (d / rec[key]).write_bytes(data)
    return d


def _o3_runs(stock, tmp: Path, pred3: dict, mutate=None) -> list:
    return P.O3.read_session(_o3_copy(tmp, mutate) if mutate is not None else O3_SESSION, pred3, stock=stock)


def o3_seam_check(runs: list, seam: dict, pred3: dict) -> list:
    """o3-seam-F: every read F run through :func:`o8_west_tower.seam_problems` -- ``[problem]``."""
    members = members_of(pred3)
    return [f"F#{r['i']} {p}" for r in runs if r["side"] == "F" and r["rows"]
            for p in O.seam_problems(r, seam, members, side="F")]


def o3_landing_check(runs: list, pred: dict) -> tuple:
    cov = {s: [r for r in runs if r["side"] == s and r["covered"]] for s in ("S", "F")}
    return O.O8.landing_check(cov, pred)


def o3_state_c(runs: list, pred3: dict, reg: dict) -> tuple:
    """STATE (c) over the fixture registration on every read F run, by place."""
    p = dict(pred3, end_state_trace=reg)
    return O.O8.state_check([r for r in runs if r["side"] == "F" and r["rows"]], p)


def o3_raced(stock, pred3: dict, *, byte8=None) -> dict:
    """end_race8 over stock 64 from story-o3's arrival values (O3's frozen end state: SC 1155, Int16[2] 100, Byte[8]
    125, ...) -- ``byte8`` overrides the arrival's Byte[8] (the mutant)."""
    vals = dict(pred3["end_state"])
    if byte8 is not None:
        vals["Global.Byte[8]"] = byte8
    # every other global as the raw start left it: New Game's 0 (O3's frozen writes are its end state's)
    return O.end_race8(stock(int(pred3["end_field"])), vals, globals0=0)


def fixture_cases(stock, sdir: Path) -> list:
    """THE STORY-O3 SEAM FIXTURE (research/o8_design.md 8): ``[(name, ok, detail)]`` -- o3-seam-F, o3-landing,
    o3-state-c (its raced set asserted EMPTY first), then each mutant FAILING by name. A missing archive FAILS every
    entry, never skips."""
    names = ("o3-seam-F", "o3-landing", "o3-state-c", "o3-seam-zero", "o3-seam-exit-moved", "o3-cut-don",
             "o3-landing-entry-ip22", "o3-state-c-renumbered", "o3-race-arrival-byte8-0")
    if not (O3_SESSION / "o3_session.json").is_file():
        return [(n, False, f"the story-o3 archive is missing: {O3_SESSION} (the MAIN repo's .harness-runs)")
                for n in names]
    tmp = sdir / "o3fix"
    tmp.mkdir(exist_ok=True)
    pred3 = o3_frozen()
    seam = o3_seam(pred3)
    runs = _o3_runs(stock, tmp, pred3)
    out = []
    bad = o3_seam_check(runs, seam, pred3)
    nf = sum(1 for r in runs if r["side"] == "F" and r["covered"])
    out.append(("o3-seam-F", not bad and nf == 3,
                "; ".join(bad[:3]) or f"{nf} covered F runs: one seam a run, member(63) 31213 -> 64 [64], its exit "
                                      f"31213 e4 t1 ip820 Int16[2] 0 -> 100, the cut row 64 e0 t0 ip22 at don 64, "
                                      f"nothing between"))
    lp = o3_landing_pred(pred3, stock)
    ok, _w, det = o3_landing_check(runs, lp)
    out.append(("o3-landing", ok is True and "62 e0 t0 ip26" not in det, det[:200]))
    raced = o3_raced(stock, pred3)
    ok_c, _w, det_c = o3_state_c(runs, pred3, O3_TRACE_REG)
    out.append(("o3-state-c", raced["raced"] == {} and raced["ret"] is not None and ok_c is True,
                f"end_race8 over stock 64 from story-o3's arrival: {raced['raced'] or 'EMPTY'} (RET ip{raced['ret']}); "
                f"STATE (c) over the fixture registration: {det_c[-160:]}"))
    # -- the mutants: each must FAIL by its clause
    def renumber_off(rows):
        return [dict(x, fld=31213, don=31213) if x.get("k") == "e" and x.get("why") == "off" else x for x in rows]
    bad = o3_seam_check(_o3_runs(stock, tmp, pred3, renumber_off), seam, pred3)
    out.append(("o3-seam-zero", any("(a) no seam" in b for b in bad), "; ".join(bad[:2])[:200]))

    def drop820(rows):
        return [x for x in rows if not (x.get("k") == "w" and x.get("fld") == 31213 and x.get("sid") == 4
                                        and x.get("tag") == 1 and x.get("ip") == 820)]
    bad = o3_seam_check(_o3_runs(stock, tmp, pred3, drop820), seam, pred3)
    out.append(("o3-seam-exit-moved", any(b.split(" ", 1)[1].startswith("(b)") for b in bad), "; ".join(bad[:2])[:200]))

    def cut_don(rows):
        i = next(j for j, x in enumerate(rows) if x.get("k") in ("w", "r") and x.get("fld") == 64)
        return rows[:i] + [dict(rows[i], don=31205)] + rows[i + 1:]
    bad = o3_seam_check(_o3_runs(stock, tmp, pred3, cut_don), seam, pred3)
    out.append(("o3-cut-don", any(b.split(" ", 1)[1].startswith("(d)") for b in bad), "; ".join(bad[:2])[:200]))
    real_entry = entry_of(stock)

    def entry22(p):
        e_ = real_entry(p)
        return dict(e_, ip=22) if p == 62 else e_
    ok, _w, det = o3_landing_check(runs, o3_landing_pred(pred3, stock, entry=entry22))
    out.append(("o3-landing-entry-ip22", ok is False and "(b)" in det, det[:200]))

    def real63(rows):
        return [dict(x, fld=63) if x.get("k") in ("w", "r") and x.get("fld") == 31213 else x for x in rows]
    ok, _w, det = o3_state_c(_o3_runs(stock, tmp, pred3, real63), pred3, O3_TRACE_REG)
    out.append(("o3-state-c-renumbered", ok is False and "(c)" in det, det[:200]))
    r0 = o3_raced(stock, pred3, byte8=0)
    out.append(("o3-race-arrival-byte8-0", r0["raced"] == {"Global.Byte[8]": [0, 125]},
                f"the arrival's Byte[8] 0: end_race8 -> {r0['raced']} (the empty-set assertion FAILS)"))
    return out


# ======================================================================== the units (no session)
def _rows(events, side="S", members=None) -> list:
    return T.parse_text("".join(json.dumps(x) + "\n" for x in render(events, side, members or {})))


def _raises(fn, match: str, exc=ValueError) -> bool:
    try:
        fn()
    except exc as err:
        return match in str(err)
    return False


def _ok(got: dict, done: str = "all as registered") -> tuple:
    return all(got.values()), str({k: v for k, v in got.items() if not v} or done)


def unit_step_of(pred: dict) -> tuple:
    """step-of-o8 (S20-S22's refusals): ``at_y`` / ``wait_flag`` on a trigger refused, an ``at_y`` band upside down
    refused, a ``wait_flag`` flag over MAX_FLAG_BIT refused, an until with an unknown axis refused; the draft's steps
    round-trip EXACTLY (``step_of(pred, raw) == {**steps_default, **raw}``, the climb merged); every frozen predictions
    file through :func:`frozen_through` (8) passes unchanged."""
    s0, s1 = pred["table"][0]["steps"]
    got = {"at_y-on-trigger": _raises(lambda: SD.step_of(pred, dict(s1, at_y=[1, 2])), "at_y"),
           "wait-on-trigger": _raises(lambda: SD.step_of(pred, dict(s1, wait_flag=s0["wait_flag"])), "wait_flag"),
           "at_y-upside-down": _raises(lambda: SD.step_of(pred, dict(s0, at_y=[9150, 8800])), "at_y"),
           "flag-over-max": _raises(lambda: SD.step_of(pred, dict(s0, wait_flag=dict(s0["wait_flag"],
                                                                                     flag=SD.MAX_FLAG_BIT + 1))),
                                    "wait_flag"),
           "until-axis": _raises(lambda: SD.step_of(pred, dict(s1, until={"w_gt": 1})), "until")}
    dflt = pred["steps_default"]
    for c in pred["table"]:
        for n, raw in enumerate(c["steps"]):
            want = {**dflt, **raw}
            if "climb" in raw:
                want["climb"] = {**dflt["climb"], **raw["climb"]}
            got[f"round-trip-{c['donor']}-{n}"] = SD.step_of(pred, raw) == want
    for f in frozen_through(8):
        p = json.loads(f.read_text(encoding="utf-8"))
        try:
            ok = all(SD.step_of(p, st) is not None for c in p.get("table") or () for st in c["steps"])
        except (ValueError, KeyError):
            ok = False
        got[f.name] = ok
    return _ok(got, f"all as registered ({len(got)})")


def unit_until_ok_y() -> tuple:
    """until-ok-y (S22): the y axis (``y_gt`` 12000 holds at 13008, not at 11500); a y term with y None RAISES; every key
    checked BEFORE the None rule (an unknown key raises even with x None); x None with x/z terms only is False."""
    got = {"y-holds": SD.until_ok({"y_gt": 12000}, 0.0, 0.0, 13008.0) is True,
           "y-fails": SD.until_ok({"y_gt": 12000}, 0.0, 0.0, 11500.0) is False,
           "y-none-raises": _raises(lambda: SD.until_ok({"y_gt": 12000}, 0.0, 0.0, None), "y"),
           "key-first": _raises(lambda: SD.until_ok({"w_gt": 1}, None, None), "w_gt"),
           "x-none": SD.until_ok({"x_lt": 5}, None, 0.0) is False,
           "has-y": SD.has_y({"y_gt": 1}) and not SD.has_y({"x_gt": 1})}
    return _ok(got)


def unit_walk_kw_unstick(pred: dict) -> tuple:
    """walk-kw-unstick (S23): the step's ``unstick`` replaces route_to's literal True only when the step carries it;
    the draft's steps carry none."""
    from types import SimpleNamespace
    stub = SimpleNamespace(pred=pred, floor=lambda closed=None: "mesh", prior_for=lambda d: {"v": (0, 1), "h": (1, 0)},
                           donor=164)
    s1 = pred["table"][0]["steps"][1]
    with_ = SD._Drive.walk_kw(stub, SD.step_of(pred, dict(s1, unstick=False)))
    plain = SD._Drive.walk_kw(stub, SD.step_of(pred, s1))
    got = {"carried": with_.get("unstick") is False, "literal": plain.get("unstick") is True,
           "draft-none": not any("unstick" in s for c in pred["table"] for s in c["steps"])}
    return _ok(got)


def unit_instanced_at8(stock) -> tuple:
    """instanced-at8 (0.2 #3): 164@342 -> {object 1, 7; region 2, 3}; 165@343 -> {code 1; object 7; region 2, 3};
    166@344 -> {object 3, 5, 6} -- no dispatch, every Init of each Main_Init."""
    a, b, c = (O.instanced_at8(stock(164), 342), O.instanced_at8(stock(165), 343), O.instanced_at8(stock(166), 344))
    got = {"164": a == {("object", 1), ("object", 7), ("region", 2), ("region", 3)},
           "165": b == {("code", 1), ("object", 7), ("region", 2), ("region", 3)},
           "166": c == {("object", 3), ("object", 5), ("object", 6)}}
    return _ok(got, f"all as registered: 164 {sorted(a)}; 165 {sorted(b)}; 166 {sorted(c)}")


def unit_talk_reach(stock) -> tuple:
    """talk-reach (0.2 #11): 164 -> {e1 t3, e7 t11, e7 t12}; 165 and 166 -> their tag 3s alone (none instanced: none);
    on synthetic texts a function a non-talk function also calls stays out."""
    i164 = stock(164)
    ents = C7.instanced_entries(i164, 342)
    t164 = O.talk_reach(i164, O.player_sid_of(i164, 342), entries=ents)
    out = {}
    for f, ent in ((165, 343), (166, 344)):
        idx = stock(f)
        out[f] = O.talk_reach(idx, O.player_sid_of(idx, ent), entries=C7.instanced_entries(idx, ent))
    texts = [(1, 3, 10, "RunScriptSync(4, 250, 11)"), (7, 11, 0, "SET({Global.Byte[208] const(0) B_LET B_EXPR_END})"),
             (2, 1, 5, "RunScriptSync(4, 250, 11)")]
    syn = O.talk_reach(None, 7, entries={1, 2, 7}, texts=texts)
    got = {"164": t164 == {(1, 3), (7, 11), (7, 12)},
           "165-166-no-talk-beyond-tag3": all(all(t == 3 for _s, t in v) for v in out.values()),
           "shared-call-stays-out": (7, 11) not in syn}
    return _ok(got, f"all as registered: 164 {sorted(t164)}")


def unit_band_closures() -> tuple:
    """band-closures: 93 / 99 / 64 / 16 on the stock meshes, each the typed CLOSURES8; a bound moved 1000 changes the
    count."""
    from ff9mapkit import extract
    from ff9mapkit.content import pathfind
    got = {}
    for (d, n), band in O.BANDS8.items():
        wm = pathfind.PlayerWalkmesh(extract.stock_walkmesh(d))
        cl = O.band_closures(wm, *band)
        got[f"{d}#{n}"] = cl == list(O.CLOSURES8[(d, n)])
        if (d, n) == (164, 0):
            got["moved-1000"] = len(O.band_closures(wm, band[0] - 1000, band[1])) != len(cl)
    counts = [len(O.CLOSURES8[k]) for k in sorted(O.CLOSURES8)]
    got["counts"] = counts == [93, 99, 64, 16]
    return _ok(got, f"all as registered: {counts}")


def unit_height_gate(pred: dict) -> tuple:
    """height-gate (0.2 #24): the four gates and the knight's release off the pinned tests AND jumps; a mutated constant
    changes a gate; a door's ip51 as JMP_IF inverts it (164.e2 -> {y_le: 12000}); the knight's ip187 as JMP_IFNOT makes
    the release {y_lt: 8400}; another shape None."""
    gates = {}
    for key in ("164.e2", "164.e3", "165.e2", "165.e3"):
        d, e_ = int(key.split(".")[0]), int(key.split(".e")[1])
        _t, tt, _j, jt = O.door_gate_pins(pred, d, e_)
        gates[key] = O.height_gate(tt, jt)
    _t, tt, _j, jt = O.door_gate_pins(pred, 164, 2)
    got = {"gates": gates == {"164.e2": {"y_gt": 12000}, "164.e3": {"y_lt": 6000}, "165.e2": {"y_gt": 15000},
                              "165.e3": {"y_lt": 11000}},
           "release": O.knight_release(pred) == {"y_ge": 8400},
           "mutated": O.height_gate(tt.replace("53536", "53000"), jt) == {"y_gt": 12536},
           "inverted": O.height_gate(tt, jt.replace("JMP_IFNOT", "JMP_IF")) == {"y_le": 12000},
           "knight-ifnot": O.height_gate("SET({obj(uid=250).f[1] const(57136) B_GT B_EXPR_END})", "JMP_IFNOT(L15)")
           == {"y_lt": 8400},
           "other-shape": O.height_gate("SET({obj(uid=250).f[1] const(57136) B_LE B_EXPR_END})", "JMP_IF(L15)") is None
           and O.height_gate(tt, "JMP(L221)") is None}
    return _ok(got, f"all as registered: {gates}")


def _synthetic_55(items: list, *, tail: list) -> list:
    """Stock 55 e0 t0's items with ``tail`` inserted after its first long yield (ip387) -- the post-yield code."""
    i = next(j for j, x in enumerate(items) if x[0] == 387)
    return items[:i + 1] + tail + items[i + 1:]


def unit_end_race(pred: dict, stock) -> tuple:
    """end-race (0.2 #5, #26): stock 55 from the arrival's values -> {Int16[2], Byte[8]}, the walk through ip387's yield
    to its RET (ip565); a synthetic listing with a post-yield Byte[208] := 9 behind a test true on the arrival's values
    -> {Int16[2], Byte[8], Byte[208]} (the tail counts -- the design's Byte[13] := 9 is reset by 55's own ip393/ip419
    error path after the yield, so the walk reads it back to 0: as built); stock 64 from story-o3's arrival values ->
    {}."""
    vals = O.arrival_values8(pred)
    r0 = O.end_race8(stock(55), vals)
    items = O._items8(stock(55), 0, 0)
    rel0 = max(x[1] for x in items) + 1000
    tail = [(10000, rel0, "SET({Global.UInt16[0] const(1400) B_LT B_EXPR_END})"),
            (10001, rel0 + 1, f"JMP_IFNOT(L{rel0 + 3})"),
            (10002, rel0 + 2, "SET({Global.Byte[208] const(9) B_LET B_EXPR_END})"),
            (10003, rel0 + 3, "NOP()")]
    r1 = O.end_race8(stock(55), vals, items=_synthetic_55(items, tail=tail))
    r64 = o3_raced(stock, o3_frozen())
    got = {"55": set(r0["raced"]) == {"Global.Int16[2]", "Global.Byte[8]"} and (r0["yield"], r0["ret"]) == (387, 565),
           "tail-counts": set(r1["raced"]) == {"Global.Int16[2]", "Global.Byte[8]", "Global.Byte[208]"},
           "64-empty": r64["raced"] == {}}
    return _ok(got, f"all as registered: {r0['raced']} (yield ip{r0['yield']}, RET ip{r0['ret']})")


def unit_reach8(stock) -> tuple:
    """reach8 (claim review #9): 55 e10 t1 ip568 / ip582 unreachable at Map.Byte[24] 1, reachable at 3; 164's and 165's e0
    t0 ip97 unreachable from any arrival value, 166's reachable; 164 e2 t2 ip215 unreachable; a revisit loop terminates."""
    i55 = stock(55)
    loop = [(0, 0, "SET({Map.Byte[1] const(1) B_LET B_EXPR_END})"), (8, 8, "JMP(L0)"), (11, 11, "RET()")]
    got = {"55-at-1": not any(O.reach8(i55, 10, 1, ip, {"Map.Byte[24]": 1}) for ip in (568, 582)),
           "55-at-3": all(O.reach8(i55, 10, 1, ip, {"Map.Byte[24]": 3}) for ip in (568, 582)),
           "164-97": not O.reach8(stock(164), 0, 0, 97, {}), "165-97": not O.reach8(stock(165), 0, 0, 97, {}),
           "166-97": O.reach8(stock(166), 0, 0, 97, {}), "164-215": not O.reach8(stock(164), 2, 2, 215, {}),
           "loop-ends": O.reach8(None, 0, 0, 999, {}, items=loop) is False}
    return _ok(got)


def unit_race_site8(pred: dict) -> tuple:
    """race-site8 (critique #2): both races resolve to their pinned field-70 stores; ``race_value`` 2 at ip249 -> None;
    O7's race_site on 164 ip130's read -> (70, 0, 0, 130), the wrong store (why O8 types its races)."""
    b8, b13 = pred["start_reads"]
    got = {"byte8": O.race_site8(pred, b8) == (70, 0, 0, 249), "byte13": O.race_site8(pred, b13) == (70, 0, 0, 475),
           "wrong-value": O.race_site8(pred, dict(b8, race_value=2)) is None,
           "o7-wrong-store": C7.race_site(pred, b13) == (70, 0, 0, 130)}
    return _ok(got)


def unit_scoped8(pred: dict) -> tuple:
    """scoped-derivation8: exactly 164 ip57, 164 ip130 and 166 e6 t1 ip345 differ between the raw start and O1-O7."""
    olds, bad = O.scoped_derivation8(pred, O.o7_frozen(), O.prior_segments8())
    need = sorted(s for s, (_t, a, b) in olds.items() if a != b)
    return need == [(164, 0, 0, 57), (164, 0, 0, 130), (166, 6, 1, 345)] and not bad, str(need)


def unit_carried8(pred: dict) -> tuple:
    """carried-derivation8 (4.5): the fifteen over the repo's seven frozen files, Bit[3796] among them, no segment
    disagreeing with its own end_state, equal to the draft's typed ones."""
    segs = O.prior_segments8()
    derived, problems = O.carried8(pred, segs)
    got = {"fifteen": len(derived) == 15 and derived == pred["carried"]["values"],
           "bit3796": derived.get("Global.Bit[3796]") == [0, 1], "segments": len(segs) == 7, "agree": problems == []}
    return _ok(got, f"all as registered: {len(derived)} from {len(segs)}")


def _base_run(pred: dict, side: str = "S", events=None, log_edit=None) -> dict:
    """A covered run's ``rows`` (cut at its start and end places) and its standard ``log``, pure -- with its digest (its
    seams) and its cut row."""
    members = members_of(pred)
    m = members if side == "F" else {}
    ev = events if events is not None else base_events()
    rows = _rows(ev, side, members)
    kept, _at, pre = ST.cut_at_start(rows, 164, m)
    kept, end = ST.cut_at_end(kept, [55], m)
    log, ctx = standard_log(pred, side, render(ev, side, members))
    if log_edit is not None:
        log = log_edit(log, ctx) or log
    stock = T.stock_script_source()
    d = T.digest(f"{side}#1", kept, scripts=(lambda f: stock(members.get(f, f))) if side == "F" else stock,
                 donor_scripts=stock, members=members if side == "F" else None)
    return {"side": side, "i": 1 if side == "S" else 2, "rows": kept, "log": log, "pre": pre, "cut": end,
            "cut_row": next((x for x in rows if x.line == end), None), "digest": d}


def unit_exempt_span(pred: dict) -> tuple:
    """exempt-span (critique #1): from step 0's FIRST row's frame0 to step 1's FIRST row's frame0 -- a failed first
    attempt inside it; none without a step-1 row."""
    base = _base_run(pred)["log"]
    failed = _base_run(pred, log_edit=_failed_first(164, 0))["log"]
    no1 = [x for x in base if not (x.get("k") == "step" and x.get("donor") == 164 and x.get("n") == 1)]
    got = {"base": O.exempt_span(base, 164) == (F_W0[164], F_X0[164]),
           "failed-first": O.exempt_span(failed, 164) == (F_W0[164], F_X0[164]),
           "no-step-1": O.exempt_span(no1, 164) == (F_W0[164], None)}
    return _ok(got)


def unit_knight_span_done_row(pred: dict) -> tuple:
    """knight-span-done-row (critique #1's scenario): ip230 inside a FAILED first attempt -- a done-row window (the done
    row's frame0 to step 1's) FAILS it; THE EXEMPT SPAN passes it (O8-ORDER (c) on the run)."""
    run = _base_run(pred, events=_moved_knight(1900)(base_events(), 0), log_edit=_failed_first(164, 0))
    k = next(x for x in run["rows"] if x.k == "w" and (x.sid, x.tag, x.ip) == (1, 1, 230))
    done0 = next(x["frame0"] for x in run["log"] if x.get("k") == "step" and x.get("donor") == 164 and x.get("n") == 0
                 and x.get("outcome") == "done")
    ok, _w, det = O.O8.order_check([run], pred)
    got = {"done-row-window-fails": not done0 <= k.f < F_X0[164], "span-passes": ok is True}
    return _ok(got, f"all as registered: ip230 at {k.f}, the done row from {done0}")


def unit_visit_windows8(pred: dict) -> tuple:
    """visit-windows8 (5.3 WALK (b)): one window per visit -- 164's from step 0's frame0 to the trigger's loss, its door
    (164.e2 from ``to``) with its tag-2 sites (ip215, ip243) exempt after step 1's first frame0, the knight's ip230 with
    THE EXEMPT SPAN; 165's door 165.e2 (ip205, ip233). Then WALK (b) PASSES the base and a door row late before a late
    loss; FAILS ip764 inside the window, the door row before its trigger began, ip230 outside the span."""
    base = _base_run(pred)
    ws = {w_["donor"]: w_ for w_ in O.visit_windows8(base["log"], pred)}
    got = {"164": (ws[164]["lo"], ws[164]["hi"]) == (F_W0[164], F_LOST[164])
           and ws[164]["doors"] == [{"key": "164.e2", "sites": [(2, 2, 215), (2, 2, 243)], "after": F_X0[164]}]
           and ws[164]["knight"] == {"site": (1, 1, 230), "lo": F_W0[164], "hi": F_X0[164]},
           "165": ws[165]["doors"][0]["key"] == "165.e2" and ws[165]["doors"][0]["sites"] == [(2, 2, 205), (2, 2, 233)]
           and ws[165]["knight"] is None}

    def walk(events=None, log_edit=None):
        ok, _w, det = O.O8.walk_check([_base_run(pred, events=events, log_edit=log_edit)], pred)
        return ok, det
    got["pass"] = walk()[0] is True
    got["late-loss-exempt"] = walk(log_edit=_step(164, 1, lost={"frame": F_LOST[164] + 40}))[0] is True
    for name, ev in (("ip764-inside", edit_nth(base_events(), B13_164, 0, lambda x: with_opt(x, f=2000))),
                     ("door-before-trigger", edit_nth(base_events(), CH164, 0, lambda x: with_opt(x, f=2800))),
                     ("knight-outside-span", _moved_knight(3500)(base_events(), 0))):
        ok, det = walk(events=ev)
        got[name] = ok is False and "(b)" in det
    return _ok(got)


def unit_walk_check(pred: dict) -> tuple:
    """O8-WALK, pure, every clause: the base PASSES on S and on F; (a) a short walk, an arrival off its level, the wait
    unread, a loss under its until, a loss with no height ("no height", never a raise), a landing elsewhere, path A with
    no landed_frame, a loss in e3; path B PASSES; (c) no check, a 30-degree check, a cached first row -- each FAILS by its
    clause. On F, 164 #1's loss read at real 164 FAILS."""
    def walk(side="S", log_edit=None):
        ok, _w, det = O.O8.walk_check([_base_run(pred, side, log_edit=log_edit)], pred)
        return ok, det
    got = {"pass-S": walk()[0] is True, "pass-F": walk("F")[0] is True,
           "path-b": walk(log_edit=_path_b)[0] is True}
    for name, fn, clause in (
            ("short", _step(164, 0, to={"x": 1142.0}), "from the goal"),
            ("level", _step(164, 0, at_y={"y": 13893.0}), "not the goal's level"),
            ("wait", _step(164, 0, wait_flag={"read": False}), "wait_flag"),
            ("low", _step(164, 1, lost={"y": 11500.0}), "does not satisfy its until"),
            ("no-y", _step(164, 1, lost={"y": ...}), "no height"),
            ("landed", _landed_164, "landed"),
            ("no-landed-frame", _step(164, 1, landed_frame=None), "no landed_frame"),
            ("in-e3", _step(164, 1, lost={"x": 1700.0, "z": 3000.0}), "beyond exit_slack"),
            ("no-check", _step(164, 0, route={"basis_check": ...}), "(c)"),
            ("30deg", _step(164, 0, route={"basis_check": {"angle": 30.0}}), "(c)"),
            ("cached", _step(165, 0, route={"basis": "cached"}), "not 'prior'")):
        try:
            ok, det = walk(log_edit=fn)
        except Exception as err:                                  # noqa: BLE001 -- a raise is the unit's failure
            ok, det = None, f"raised {type(err).__name__}: {err}"
        got[name] = ok is False and clause in det
    ok, det = walk("F", log_edit=_step(164, 1, lost={"field": 164}))
    got["f-loss-at-164"] = ok is False and "not the walk's field" in det
    return _ok(got)


def unit_order_knight(pred: dict) -> tuple:
    """O8-ORDER and O8-KNIGHT, pure, every clause: the base PASSES on S and F; ORDER (a) no ip230 / two / at real 164 on
    F, (b) after ip243, (c) outside the span; KNIGHT (a) no seat / a reading at real 164 on F, (b) off the seat -- KNIGHT
    judges readings only (its row's ``from`` and the poll that wrote it never read)."""
    def order(side="S", events=None):
        ok, _w, det = O.O8.order_check([_base_run(pred, side, events=events)], pred)
        return ok, det

    def knight(side="S", log_edit=None):
        ok, _w, det = O.O8.knight_check([_base_run(pred, side, log_edit=log_edit)], pred)
        return ok, det
    ev = base_events()
    got = {"order-S": order()[0] is True, "order-F": order("F")[0] is True,
           "knight-S": knight()[0] is True, "knight-F": knight("F")[0] is True,
           "knight-from-ignored": knight(log_edit=_knight("seat", **{"from": "a poll in 165"}))[0] is True}
    for name, side, e_, clause in (("none", "S", drop_nth(ev, KN230), "(a)"),
                                   ("two", "S", after(ev, KN230, w(KN230)), "(a)"),
                                   ("real-164", "F", edit(ev, lambda x: _is(x, KN230),
                                                          lambda x: with_opt(x, fld=164, don=164)), "(a)"),
                                   ("after-243", "S", move(ev, KN230, after_site=CH164), "(b)"),
                                   ("outside", "S", _moved_knight(3500)(ev, 0), "(c)")):
        ok, det = order(side, e_)
        got[f"order-{name}"] = ok is False and clause in det
    for name, side, fn, clause in (("no-seat", "S", _no_knight("seat"), "(a)"),
                                   ("real-164", "F", _knight("seat", field=164), "(a)"),
                                   ("off-seat", "S", _knight("start1", x=-400.0), "(b)")):
        ok, det = knight(side, fn)
        got[f"knight-{name}"] = ok is False and clause in det
    return _ok(got)


def unit_landing_seam(pred: dict) -> tuple:
    """O8-LANDING (O7's (a)-(d) over seam-free COPIES -- the run dicts untouched) and O8-SEAM (a)-(f), pure: the base
    PASSES on S and F; LANDING FAILS (b) on a dropped chain row, (c) on a harness row after ip863, (d) on a cut at ip49;
    SEAM FAILS (a) with zero seams (never vacuously), (b) with the exit row ip502, (d) with the cut row's don 31205,
    (e) with a residue row before the cut; the F run's digest keeps its seam after LANDING read it; (f) S counted never."""
    def runs(side="S", events=None):
        r_ = _base_run(pred, side, events=events)
        r_["log"].append({"k": "end", "field": 55})
        return r_

    def land(side="S", events=None):
        r_ = runs(side, events)
        before_ = list(r_["digest"].seams)
        ok, _w, det = O.O8.landing_check({"S": [r_] if side == "S" else [], "F": [r_] if side == "F" else []}, pred)
        return ok, det, list(r_["digest"].seams) == before_

    def seam(side="F", events=None):
        r_ = runs(side, events)
        ok, _w, det = O.O8.seam_check({"S": [r_] if side == "S" else [], "F": [r_] if side == "F" else []}, None, pred)
        return ok, det
    ev = base_events()
    ls, lf = land(), land("F")
    got = {"landing-S": ls[0] is True, "landing-F": lf[0] is True and lf[2], "seam-F": seam()[0] is True,
           "seam-S": seam("S")[0] is True and "(f) S: no members" in seam("S")[1]}
    for name, e_, clause in (("b", drop_nth(ev, CH165), "(b)"),
                             ("c", after(ev, CH166, w((166, -1, -1, -1, "Global.Byte[300]", 9), src="harness")), "(c)"),
                             ("d", drop_nth(ev, END55), "(d)")):
        ok, det, _same = land("S", e_)
        got[f"landing-{name}"] = ok is False and clause in det
    for name, e_, clause in (("a-zero", _off_at(31258)(ev, 0), "(a) no seam"),
                             ("b-exit", drop_nth(ev, CH166), "(b)"),
                             ("d-don", edit(ev, lambda x: _is(x, END55), lambda x: with_opt(x, don=31205)), "(d)"),
                             ("e-residue", after(ev, CH166, r(166, 300, 0, 5)), "(e)")):
        ok, det = seam("F", e_)
        got[f"seam-{name}"] = ok is False and clause in det
    return _ok(got)


def unit_landing_e_dropped(pred: dict) -> tuple:
    """landing-e-dropped: a covered F run with its ONE seam (31258 -> 55): O7's LANDING FAILS (e) on it, O8's PASSES --
    (e) is O8-SEAM's."""
    r_ = _base_run(pred, "F")
    r_["log"].append({"k": "end", "field": 55})
    cov = {"S": [], "F": [r_]}
    ok7, _w, det7 = C7.O7Segment.landing_check(O.O8, cov, pred)
    ok8, _w, det8 = O.O8.landing_check(cov, pred)
    got = {"o7-fails-e": ok7 is False and "(e)" in det7, "o8-passes": ok8 is True and "(e): O8-SEAM's" in det8}
    return _ok(got)


def unit_state_c_by_place(pred: dict, stock, scripts: dict, tmp: Path, path: Path) -> tuple:
    """STATE (c) BY PLACE, on a session's own reading: an F run's last Int16[2] and Byte[8] rows at 31258 match the
    registered sites (place 166, member(166)'s field); renumbered to fld 166 (on F, real 166: no member's) they do not;
    on S at real 166 they do."""
    real = lambda ev, n: edit(ev, lambda x: _is(x, CH166) or _is(x, M502),     # noqa: E731
                              lambda x: with_opt(x, fld=166, don=166))
    runs = six(pred)[:2] + six(pred, f=real)[1:2]
    rs = O.O8.read_session(make_session(tmp, path, runs, scripts), pred, stock=stock)

    def c(r_):
        ok, _w, det = O.O8.state_check([r_], pred)
        return ok, det
    got = {"s-166": c(rs[0])[0] is True, "member-31258": c(rs[1])[0] is True}
    ok, det = c(rs[2])
    got["renumbered-166"] = ok is False and "(c)" in det and "at fld 166" in det
    return _ok(got)


class _St:
    """A published state for the observe hooks: frame, objects, mtime, ui, control, texts, choice."""

    def __init__(self, frame, objects=None, *, mtime=None, ui="FieldHUD", control=False, texts=(), choice=None):
        self.frame, self.objects, self.mtime, self.ui_state = frame, objects, mtime, ui
        self.control, self.texts, self.choice = control, list(texts), choice


class _G:
    """A session for knight_watch: ``states_since`` over a list of raw samples (no ring: segment_drive.ring_since reads
    it)."""

    def __init__(self, raws):
        self.raws = raws

    def states_since(self, frame):
        return [x for x in self.raws if int(x["frame"]) > frame]


def _raw(frame, fld, objs):
    return {"frame": frame, "field": {"id": fld}, "objects": objs}


def unit_knight_watch(pred: dict) -> tuple:
    """knight-watch (1.3; the reviews' A2, B8): cached by PLACE (31256 reads as 164); the seat off the RING at the wait's
    frame, start1 off the poll of step 1's frame0; PATH B -- the step-1 row first seen on a poll in 31257 -- and a LOAD
    poll (fid -1) still write start1, its field the READING's; one row each per visit; sid 1 unpublished: no rows; an
    injected exception: one observe_error row, no raise."""
    me = [{"sid": 1, "x": -586.0, "z": 3884.0}]
    s0 = {"k": "step", "donor": 164, "n": 0, "outcome": "done", "wait_flag": {"read": True, "frame": 100}}
    s1 = {"k": "step", "donor": 164, "n": 1, "frame0": 120}

    def drive(polls, raws, *, path_b=False):
        log: list = []
        hook = O.knight_watch(_G(raws), pred, log)
        for frame, fld, donor, objs in polls:
            if frame == 101:
                log.append(dict(s0))
            if frame == (130 if path_b else 121):
                log.append(dict(s1))
            hook(_St(frame, objs), {"field": fld, "donor": donor})
        return [x for x in log if x.get("k") in ("knight", "observe_error")]
    raws = [_raw(100, 31256, me), _raw(101, 31256, me)]
    polls = [(f, 31256, 164, me) for f in (90, 100, 101, 110, 120, 121, 125)]
    rows = drive(polls, raws)
    got = {"seat-ring": [(x["what"], x["frame"], x["field"], x["donor"], x["from"]) for x in rows] ==
           [("seat", 100, 31256, 164, "ring"), ("start1", 120, 31256, 164, "poll")]}
    pb = drive([(f, 31256, 164, me) for f in (90, 100, 101, 110, 120)] + [(130, 31257, 165, [{"sid": 7, "x": 0,
                                                                                              "z": 0}])], raws,
               path_b=True)
    got["path-b"] = [(x["what"], x["field"], x["donor"]) for x in pb] == [("seat", 31256, 164), ("start1", 31256, 164)]
    load = drive([(f, 31256, 164, me) for f in (90, 100, 101, 110, 120)] + [(130, -1, None, None)], raws, path_b=True)
    got["load-poll"] = [x["what"] for x in load] == ["seat", "start1"]
    got["unpublished"] = drive([(f, 31256, 164, []) for f in (90, 100, 101, 120, 121)], [_raw(100, 31256, [])]) == []

    class _Boom:
        frame = 5

        @property
        def objects(self):
            raise RuntimeError("a published sample the hook cannot read")
    log: list = []
    hook = O.knight_watch(_G([]), pred, log)
    for _ in range(3):
        hook(_Boom(), {"field": 31256, "donor": 164})
    got["no-raise"] = [x["k"] for x in log] == ["observe_error"] and log[0]["n"] == 3
    return _ok(got, f"all as registered: {[(x['what'], x['frame'], x['from']) for x in rows]}")


def unit_movie_clock(pred: dict) -> tuple:
    """movie-clock: rows every ``clock_every`` frames in 166 only, an mtime None kept on the row; one ``skip_seen`` an
    opening, by text AND by shape (a prompt published empty, a localized one); an injected exception: one observe_error
    row, no raise."""
    log: list = []
    hook = O.movie_clock(pred, log)
    for f in range(0, 100, 10):
        hook(_St(f, mtime=None if f == 30 else 1000.0 + f / 30.0), {"field": 31258, "donor": 166})
    hook(_St(105), {"field": 31257, "donor": 165})
    clocks = [(x["frame"], x["mtime"] is None) for x in log if x["k"] == "clock"]
    log2: list = []
    h2 = O.movie_clock(pred, log2)
    loc = {"options": ["Zwischensequenz?", "Ja", "Nein"], "active": [0, 1], "selected": 1}
    for f, ch in ((200, SKIP_TEXT), (201, SKIP_TEXT), (202, None), (203, SKIP_EMPTY), (204, None), (205, loc),
                  (206, SCRIPT_CHOICE)):
        h2(_St(f, choice=ch), {"field": 31258, "donor": 166})
    seen = [(x["frame"], x["prompt_empty"]) for x in log2 if x["k"] == "skip_seen"]

    class _Boom:
        frame = 9

        @property
        def mtime(self):
            raise RuntimeError("boom")
    log3: list = []
    h3 = O.movie_clock(pred, log3)
    h3(_Boom(), {"field": 31258, "donor": 166})
    h3(_Boom(), {"field": 31258, "donor": 166})
    got = {"clocks": clocks == [(0, False), (30, True), (60, False), (90, False)],
           "skip-seen": seen == [(200, False), (203, True), (205, False)],
           "no-raise": [x["k"] for x in log3] == ["observe_error"] and log3[0]["n"] == 2}
    return _ok(got, f"all as registered: {clocks}; {seen}")


def unit_movie_span(pred: dict) -> tuple:
    """movie-span: the clocked rate over rows with a write time; one such row -> unclocked; the half-open span (f502,
    f863]: a press at f502 outside, at f502 + 1 inside."""
    base = _base_run(pred)
    sp = O.movie_span(base, pred, {})
    one = _base_run(pred, log_edit=_unclocked)
    at502 = _base_run(pred, log_edit=_movie_rows(_stray(F_502, why="page")))
    in1 = _base_run(pred, log_edit=_movie_rows(_stray(F_502 + 1, why="page")))
    got = {"rate": (sp["f502"], sp["f863"], sp["fps"]) == (F_502, F_863, 31.0) and sp["s"] >= 40.4,
           "unclocked": O.movie_span(one, pred, {})["unclocked"] is True,
           "at-f502-outside": O.movie_span(at502, pred, {})["presses"] == [],
           "f502+1-inside": len(O.movie_span(in1, pred, {})["presses"]) == 1}
    return _ok(got, f"all as registered: {sp['fps']} fps, {sp['s']} s")


def unit_movie_recheck(pred: dict) -> tuple:
    """movie-recheck: O8-MOVIE (a) and (c) FAIL on runs the COVER code was bypassed for (a press, a skip-shaped choice, a
    skip_seen row in the span), and (b) on a short span; a non-skip-shaped choice FAILS (a) by its shape."""
    def movie(log_edit=None, events=None):
        ok, _w, det = O.O8.movie_check([_base_run(pred, events=events, log_edit=log_edit)], pred)
        return ok, det
    got = {"pass": movie()[0] is True}
    for name, fn, clause in (("press", _movie_rows(_stray(why="page")), "(a): a press"),
                             ("skip-choice", _movie_rows(_choice_row(8500, SKIP_TEXT)), "the skip dialog's"),
                             ("script-choice", _movie_rows(_choice_row(8500, SCRIPT_CHOICE, rule=1)), "of another shape"),
                             ("skip-seen", _movie_rows({"k": "skip_seen", "frame": 8500}), "(c)")):
        ok, det = movie(log_edit=fn)
        got[name] = ok is False and clause in det
    ok, det = movie(events=edit(base_events(), lambda x: _is(x, CH166), lambda x: with_opt(x, f=F_502 + 930)))
    got["short"] = ok is False and "(b)" in det
    return _ok(got)


def unit_void_ids() -> tuple:
    """void-ids (1.3): reasons opening with START_READ and MOVIE_SPAN set aside, KNIGHT_UNREAD kept."""
    r_ = {"void": [{"class": "A-START", "why": f"{O.START_READ} Global.Byte[8] ...", "by": "driver"},
                   {"class": "A-MOVIE", "why": f"{O.MOVIE_SPAN} (frames 1-2): ...", "by": "driver"},
                   {"class": "A-KNIGHT", "why": f"{O.KNIGHT_UNREAD}: no seat row", "by": "driver"},
                   {"class": "V8", "why": "the wait ran out", "by": "game", "cell": [164, 1190, 1]}]}
    got = O.O8._void_ids(r_)
    return got == {("A-KNIGHT", None, "driver"), ("V8", (164, 1190, 1), "game")}, str(sorted(map(str, got)))


def unit_seam_problems(pred: dict) -> tuple:
    """seam-problems (pure, parameterised by the registration): the base F run PASSES; each clause FAILS by name -- (a)
    no seam, two seams; (b) the exit row moved; (c) a seam key; (d) the cut row's don; (e) a row before the cut; S
    (d)/(e) on its own runs."""
    seam = O.seam_spec(pred)
    members = members_of(pred)

    def probs(side="F", events=None):
        r_ = _base_run(pred, side, events=events)
        return O.seam_problems(r_, seam, members if side == "F" else {}, side=side)
    ev = base_events()
    got = {"pass-F": probs() == [], "pass-S": probs("S") == []}
    for name, side, e_, clause in (
            ("a-zero", "F", _off_at(31258)(ev, 0), "(a) no seam"),
            ("a-two", "F", before(ev, I22_166, ("e", "swap", 164, {"fld": 164})), "(a) 2 seams"),
            ("b", "F", drop_nth(ev, CH166), "(b)"),
            ("c", "F", after(ev, CH166, w(S163[2], fld=163, don=163)), "(c)"),
            ("d", "F", edit(ev, lambda x: _is(x, END55), lambda x: with_opt(x, don=31205)), "(d)"),
            ("e", "F", after(ev, CH166, r(166, 300, 0, 5)), "(e)"),
            ("d-S", "S", drop_nth(ev, END55), "(d)"),
            ("e-S", "S", after(ev, CH166, r(166, 300, 0, 5)), "(e)")):
        got[name] = any(p.startswith(clause) for p in probs(side, e_))
    return _ok(got)


def unit_render(pred: dict, tmp: Path) -> tuple:
    """THE SINK, one model, two implementations: the base run's rows before the cut are 29 ``w`` rows (23 unmasked) and
    no ``c`` row, on S and F; the SAME events through the FakeGame's H13 knob give the same ``(k, fld, sid, tag, ip, new,
    same, n, last)`` sequence, on S and F; the cut row 55 ip22 ``same`` 1 (a new site), REAL 55 on both sides."""
    members = members_of(pred)
    got = {}
    for side in ("S", "F"):
        rows = render(base_events(), side, members)
        fk = _fake_rows(base_events(), side, members, tmp)
        got[f"fake-{side}"] = D5._shape(rows) == D5._shape(fk)
        cut = next(i for i, x in enumerate(rows) if x["k"] in ("w", "r") and x["fld"] == 55)
        before_ = [x for x in rows[:cut] if x["k"] == "w" and x["fld"] != 70]
        unmasked = [x for x in before_ if x["bit"] not in (191, 184)]
        got[f"counts-{side}"] = (len(before_), len(unmasked), sum(1 for x in rows if x["k"] == "c")) == (29, 23, 0)
        got[f"cut-{side}"] = (rows[cut]["ip"], rows[cut]["same"], rows[cut]["fld"], rows[cut]["don"]) == (22, 1, 55, 55)
    return _ok(got)


def _fake_rows(events: list, side: str, members: dict, tmp: Path) -> list:
    """The SAME event list through the FakeGame's sink with H13 on (``story_suppress``): field 70's prologue values
    poked first, the trace armed in 70, the raw warp's residue, each store at its field (and, on F, its donor)."""
    from harness.fakegame import FakeGame
    game = tmp / f"h13-{side}-{len(list(tmp.iterdir()))}"
    (game / "x64" / "ff9harness").mkdir(parents=True)
    fake = FakeGame(game)
    fake.story_suppress = True
    fork = {d: f for f, d in sorted(members.items(), reverse=True)}
    b = fake.story_bytes
    b[9:11] = (643).to_bytes(2, "little")
    b[11:13] = b"\xff\xff"
    b[13], b[8] = 1, 125
    fake.field_id = 70
    for ev in events:
        if ev[0] == "e" and ev[1] == "arm":
            fake._story_start()
        elif ev[0] == "e" and ev[1] == "off":
            fake.field_id = fork.get(ev[2], ev[2]) if side == "F" else ev[2]
            fake._story_stop()
        elif ev[0] == "r":
            if ev[2] == 0 and ev[1] == 70:                     # the warp's residue, its bytes at once
                fake._warp_writes(342, 1190)
        elif ev[0] == "w":
            _k, donor, sid, tag, ip, target, value, _opt = ev
            fake.field_id = fork.get(donor, donor) if side == "F" else donor
            fake.donor = donor if side == "F" else None
            width, index = target.split(".", 1)[1].rstrip("]").split("[")
            bit = int(index) if width in T.BIT_WIDTHS else -1
            fake.script_store(sid, tag, ip, int(index) >> 3 if bit >= 0 else int(index), width, value, bit=bit)
    text = (game / "x64" / "ff9harness" / "story.jsonl").read_text(encoding="utf-8")
    return [json.loads(ln) for ln in text.splitlines() if ln.strip()]


def unit_pattern(pred: dict, stock, tmp: Path) -> tuple:
    """O8-PATTERN's reading (4.16): :func:`o6_steiner.pattern_diff6` (``floating`` []) on the base run, joined on the
    stock bytes -- none, on S and F, render and the FakeGame alike, 9 + 9 + 11 rows; ip380 before ip345, a repeat of 164
    ip764, a row of 164 inside visit 2, a missing door row each (b); a ``c`` row (a)."""
    members = members_of(pred)
    got = {}

    def diff(events, side="S", src="render"):
        m = members if side == "F" else {}
        rows = render(events, side, members) if src == "render" else _fake_rows(events, side, members, tmp)
        parsed = T.parse_text("".join(json.dumps(x) + "\n" for x in rows))
        kept, _at, _pre = ST.cut_at_start(parsed, 164, m)
        kept, _end = ST.cut_at_end(kept, [55], m)
        g = C5.pattern_of(kept, pred, m, C5.stock_join(stock, m))
        return C6.pattern_diff6(g, pred["pattern"]), g
    for side in ("S", "F"):
        for src in ("render", "fake"):
            d, g = diff(base_events(), side, src=src)
            got[f"{src}-{side}"] = d == [] and g["unjoined"] == 0 and [len(v) for v in g["visits"]] == [9, 9, 11]
    for name, ev in (("swap", move(base_events(), M380, before_site=M345)),
                     ("repeat", after(base_events(), B13_164, w(B13_164))),
                     ("split", after(base_events(), I49_165, w(I200_164, emit=True))),
                     ("door-missing", drop_nth(base_events(), CH165))):
        d = diff(ev)[0]
        got[name] = bool(d) and all(x.startswith("(b)") for x in d)
    d = diff(after(base_events(), I57_165, w(I57_165, count=True)))[0]
    got["c-row"] = bool(d) and all(x.startswith("(a)") for x in d)
    return _ok(got)


def unit_trace_summary(pred: dict, stock) -> tuple:
    """O8's trace summary (7.2) of a base run: the knight's ip230 (frame 2650) before the chain row ip243; the movie's
    rows ip502 and ip863; the cut row REAL 55 e0 t0 ip22; on F the digest's ONE seam 31258 -> 55 [55]; the four start
    residue rows. An F stage given its end PLACES is cut at 55's first row -- O3's summary given end FIELDS [31205] (O1's
    member(55): the mutant) is not cut at all."""
    members = members_of(pred)
    t = O.trace_summary8(_rows(base_events()), pred, stock=stock)
    frows = _rows(base_events(), "F", members)
    tf = O.trace_summary8(frows, pred, side="F", stock=stock)
    got = {"knight": (t["knight"]["ip230"] or {}).get("f") == F_KNIGHT
           and (t["knight"]["ip230"]["line"] < t["knight"]["chain"]["line"]),
           "movie": (t["movie"]["ip502"] or {}).get("f") == F_502 and (t["movie"]["ip863"] or {}).get("f") == F_863,
           "cut-row": (t["cut_row"] or {}).get("fld") == 55 and "e0 t0 ip22" in (t["cut_row"] or {}).get("text", ""),
           "s-no-seam": t["seams"] == [],
           "f-one-seam": [(s["frm"], s["to"], s["fields"]) for s in tf["seams"]] == [(31258, 55, [55])],
           "residue": [x[1:] for x in t["residue_before"]] == [[0, 0, 166], [1, 0, 4], [2, 0, 86], [3, 0, 1]],
           "o3-fields-uncut": P.trace_summary(frows, pred, side="F", end_fields=[31205], stock=stock)["end"] is None}
    return _ok(got)


def unit_why_void(pred: dict, stock, scripts: dict, tmp: Path, path: Path) -> tuple:
    """why-void (5.1), on a session's own reading: both START READS and both branches -- 166 ip255 old 0 naming ip249,
    164 ip130 old 2 naming ip475, 70 ip249 / ip475 in ``pre`` -- each reason led by START_READ; none at 125 / 1; none when
    an earlier row of the run touched the target; with the race neutralised (its race_value off the pin) the raced row
    is START (a)'s, no A-START; A-MOVIE's four reasons (a press, a dialog answered, outside input, unclocked) each led by
    MOVIE_SPAN, a non-skip-shaped choice giving none; A-KNIGHT led by KNIGHT_UNREAD."""
    def classes(runs, p_path=path):
        rs = O.O8.read_session(make_session(tmp, p_path, runs, scripts), json.loads(p_path.read_text("utf-8")),
                               stock=stock)
        return rs
    s = six(pred)
    runs = [dict(s[0], events=_b8_old0(base_events(), 0)), dict(s[1], events=_b13_old2(base_events(), 0)),
            dict(s[0], events=_armed(RACE249, 0)(base_events(), 0)), dict(s[1], events=_armed(RACE475, 1)(base_events(),
                                                                                                           0)),
            dict(s[0]), dict(s[0], events=_b13_old2(after(base_events(), I22_164, r(164, 13, 1, 2)), 0)),
            dict(s[0], log=_movie_rows(_stray(why="page"))),
            dict(s[0], log=_movie_rows(_stray(), _choice_row(8520, SKIP_TEXT))),
            dict(s[1], log=_movie_rows({"k": "skip_seen", "frame": 8500, "options": SKIP_TEXT["options"]})),
            dict(s[0], log=_unclocked), dict(s[0], log=_movie_rows(_choice_row(8500, SCRIPT_CHOICE, rule=1))),
            dict(s[0], log=_no_knight("seat"))]
    rs = classes(runs)

    def reasons(r_, cls):
        return [v["why"] for v in r_["void"] if v["class"] == cls]
    led = lambda r_, cls, head: bool(reasons(r_, cls)) and all(x.startswith(head) for x in reasons(r_, cls))  # noqa
    got = {"byte8-read": led(rs[0], "A-START", O.START_READ) and "ip249" in reasons(rs[0], "A-START")[0],
           "byte13-read": led(rs[1], "A-START", O.START_READ) and "ip475" in reasons(rs[1], "A-START")[0],
           "byte8-raced": led(rs[2], "A-START", O.START_READ), "byte13-raced": led(rs[3], "A-START", O.START_READ),
           "none-125-1": rs[4]["void"] == [], "explained": reasons(rs[5], "A-START") == [],
           "movie-press": led(rs[6], "A-MOVIE", O.MOVIE_SPAN), "movie-answered": led(rs[7], "A-MOVIE", O.MOVIE_SPAN),
           "movie-outside": led(rs[8], "A-MOVIE", O.MOVIE_SPAN) and "outside input" in reasons(rs[8], "A-MOVIE")[0],
           "movie-unclocked": led(rs[9], "A-MOVIE", O.MOVIE_SPAN),
           "movie-script-choice-none": reasons(rs[10], "A-MOVIE") == [],
           "knight": led(rs[11], "A-KNIGHT", O.KNIGHT_UNREAD)}
    neut = copy.deepcopy(json.loads(path.read_text("utf-8")))
    neut["start_reads"][0]["race_value"] = 124
    npath = tmp / "o8_neutralised.json"
    npath.write_bytes((json.dumps(neut, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    rn = classes([dict(s[0], events=_armed(RACE249, 0)(base_events(), 0))], npath)
    got["neutralised"] = reasons(rn[0], "A-START") == [] and rn[0]["covered"]
    return _ok(got)


def unit_as_if_frozen(draft: dict) -> tuple:
    """:func:`as_if_frozen` of the DRAFT changes ``budget``, ``rehearsals``, ``rehearsal_fps``, ``rehearsed`` and
    ``table`` (the steps' starts) and nothing else, and the freeze's refusals read it clean (its engine the draft's, as a
    live one) where they refuse the draft while it names no rehearsals."""
    p = as_if_frozen(draft)
    changed = sorted(k for k in set(p) | set(draft) if p.get(k) != draft.get(k))
    probs = O.O8.freeze_problems(p, live_engine=dict(draft["engine"]))
    starts = all(s2.get("start") == ([s1["start"][0] + 20, s1["start"][1]] if s1.get("start") is not None else None)
                 for c1, c2 in zip(draft["table"], p["table"]) for s1, s2 in zip(c1["steps"], c2["steps"]))
    got = {"changed": changed == ["budget", "rehearsal_fps", "rehearsals", "rehearsed", "table"], "starts": starts,
           "freezable": probs == [],
           "draft-not": bool(O.O8.freeze_problems(draft, live_engine=dict(draft["engine"])))
           == (not draft.get("rehearsals"))}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or f"all as registered: {changed}") \
        + ("" if not probs else f" {probs[:2]}")


_LOG_HEAD = "05.10.2026 19:27:42 |M| [WindowManager] Moving window to (2045,33)\n"
_LOG_351 = ("05.10.2026 19:27:44 |W| [DataPatchers] ForkDonorPatch: donor field 351 is forked by both 30831 and 30842 "
            "-> remap DISABLED (ambiguous)\n")
_LOG_DONE = "05.10.2026 19:27:44 |M| [DataPatchers] Initialized\n"


def unit_p_donor_log() -> tuple:
    """P-DONOR-LOG over [164, 165, 166, 55]: today's shape PASS; 55 forked twice FAIL naming it; no "Initialized" FAIL."""
    a = P.p_donor_log(_LOG_HEAD + _LOG_351 + _LOG_DONE, O.LOG_DONORS)
    w55 = _LOG_351.replace("351", "55").replace("30831 and 30842", "31205 and 31299")
    b = P.p_donor_log(_LOG_HEAD + _LOG_351 + w55 + _LOG_DONE, O.LOG_DONORS)
    c = P.p_donor_log(_LOG_HEAD + _LOG_351, O.LOG_DONORS)
    ok = a[0] and not b[0] and "donor field 55 is forked by both 31205 and 31299" in b[1] and not c[0]
    return ok, f"today {a[0]}; 55 twice {b[0]}; no Initialized {c[0]}"


def unit_p_donor(pred: dict, tmp: Path) -> tuple:
    """p-donor (6.2): over the route donors PASS with the ``31205 55`` line named OUTSIDE; O5-O7's call over route + end
    FAILS on that row (the research's harness gap 8)."""
    root = tmp / "pdonor8" / "FF9CustomMap"
    root.mkdir(parents=True)
    rows = [f"{f} {d}" for f, d in sorted(members_of(pred).items())] + ["31205 55"]
    (root / "ForkDonorPatch.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
    out = [x for x in O.O8.preflight_extra(pred, [root], pads=None, live_engine=dict(O.ENGINE), game=tmp,
                                           stock_text={3: {}}) if x[1].startswith("P-DONOR")]
    ok8, det8 = out[0][0], out[0][2]
    okx, detx = P.p_donor({**pred, "route": list(O.ROUTE_DONORS) + [55]}, [root])
    got = {"route-pass": ok8 is True and "outside the set: FF9CustomMap line 21 `31205 55`" in det8,
           "with-end-fails": okx is False}
    return _ok(got, f"all as registered: {det8[-120:]}")


def unit_p_settings(tmp: Path) -> tuple:
    """P-SETTINGS on O8's 32 keys (4.13): equal PASS; [Graphics] VSync "0" FAILS; VSync missing FAILS."""
    want = O.SETTINGS8
    game = tmp / "psettings8"
    game.mkdir()

    def judge(settings):
        lines = []
        for sec, kv in settings.items():
            lines += [f"[{sec}]"] + [f"{k} = {v}" for k, v in kv.items()] + [""]
        (game / "Memoria.ini").write_text("\n".join(lines), encoding="utf-8")
        return P.p_settings(want, P.install_settings(game, [], want))
    s0 = json.loads(json.dumps(want))
    s0["Graphics"]["VSync"] = "0"
    gone = json.loads(json.dumps(want))
    gone["Graphics"].pop("VSync")
    v0 = judge(s0)
    got = {"equal": judge(want)[0] and sum(len(v) for v in want.values()) == 32,
           "vsync-0": (not v0[0]) and "[Graphics] VSync = '0'" in v0[1], "vsync-gone": not judge(gone)[0]}
    return _ok(got)


def unit_p_launch(tmp: Path) -> tuple:
    """P-LAUNCH with the engine (O5's unit, O8's ForkDonorPatch rows): older PASS; ForkDonorPatch.txt touched after the
    launch FAIL ("relaunch"); another live engine FAIL; no stamp FAIL."""
    launched = P.launch_time(_LOG_HEAD + _LOG_DONE)
    game = tmp / "plaunch8"
    root = game / "FF9CustomMap"
    root.mkdir(parents=True)
    old = _dt.datetime(2026, 10, 5, 19, 27, 4)
    files = {game / "Memoria.ini": "[Battle]\nSpeed = 5\n", root / "DictionaryPatch.txt": "FieldScene 31256 11 X X 3\n",
             root / "ForkDonorPatch.txt": "31256 164\n31257 165\n31258 166\n"}
    for arch in ("x64", "x86"):
        files[game / arch / "FF9_Data" / "Managed" / "Assembly-CSharp.dll"] = "dll"
    for p_, text in files.items():
        p_.parent.mkdir(parents=True, exist_ok=True)
        p_.write_text(text, encoding="utf-8")
        D4._touch(p_, old)
    pinned = {"x64": O.ENGINE["x64"], "x86": O.ENGINE["x86"]}

    def check(live=pinned, stamp=launched):
        return C4.launch_engine_check(P.launch_files(game, [root]), C4.engine_files(game), stamp, live, O.ENGINE)
    got = {"older": check()[0]}
    fdp = root / "ForkDonorPatch.txt"
    D4._touch(fdp, _dt.datetime(2026, 10, 5, 19, 27, 50))
    ok, d = check()
    got["fdp-after"] = (not ok) and "ForkDonorPatch.txt" in d and "relaunch" in d
    D4._touch(fdp, old)
    got["other-engine"] = not check(live={"x64": "6" * 64, "x86": "6" * 64})[0]
    got["no-stamp"] = not check(stamp=None)[0]
    got["older-again"] = check()[0]
    return _ok(got)


def units(pred: dict, stock, scripts: dict, sdir: Path, path: Path, tmp: Path) -> list:
    """Every single unit, in order: ``[(name, fn)]``, each ``fn()`` -> ``(ok, detail)``."""
    return [("step-of-o8", lambda: unit_step_of(pred)),
            ("until-ok-y", unit_until_ok_y),
            ("walk-kw-unstick", lambda: unit_walk_kw_unstick(pred)),
            ("instanced-at8", lambda: unit_instanced_at8(stock)),
            ("talk-reach", lambda: unit_talk_reach(stock)),
            ("band-closures", unit_band_closures),
            ("height-gate", lambda: unit_height_gate(pred)),
            ("end-race", lambda: unit_end_race(pred, stock)),
            ("reach8", lambda: unit_reach8(stock)),
            ("race-site8", lambda: unit_race_site8(pred)),
            ("scoped-derivation8", lambda: unit_scoped8(pred)),
            ("carried-derivation8", lambda: unit_carried8(pred)),
            ("exempt-span", lambda: unit_exempt_span(pred)),
            ("knight-span-done-row", lambda: unit_knight_span_done_row(pred)),
            ("visit-windows8", lambda: unit_visit_windows8(pred)),
            ("walk-check", lambda: unit_walk_check(pred)),
            ("order-knight", lambda: unit_order_knight(pred)),
            ("landing-seam", lambda: unit_landing_seam(pred)),
            ("landing-e-dropped", lambda: unit_landing_e_dropped(pred)),
            ("state-c-by-place", lambda: unit_state_c_by_place(pred, stock, scripts, sdir, path)),
            ("knight-watch", lambda: unit_knight_watch(pred)),
            ("movie-clock", lambda: unit_movie_clock(pred)),
            ("movie-span", lambda: unit_movie_span(pred)),
            ("movie-recheck", lambda: unit_movie_recheck(pred)),
            ("void-ids", unit_void_ids),
            ("seam-problems", lambda: unit_seam_problems(pred)),
            ("render", lambda: unit_render(pred, tmp)),
            ("pattern", lambda: unit_pattern(pred, stock, tmp)),
            ("trace-summary", lambda: unit_trace_summary(pred, stock)),
            ("why-void", lambda: unit_why_void(pred, stock, scripts, sdir, path)),
            ("as-if-frozen", lambda: unit_as_if_frozen(O.draft_predictions())),
            ("p-donor-log", unit_p_donor_log),
            ("p-donor", lambda: unit_p_donor(pred, tmp)),
            ("p-launch", lambda: unit_p_launch(tmp)),
            ("p-settings", lambda: unit_p_settings(tmp)),
            ("p-pad", D4.unit_p_pad),
            ("p-override", D4.unit_p_override),
            ("p-engine", D4.unit_p_engine),
            ("text-strict", D4.unit_text_strict),
            ("input-witness", D4.unit_input_witness)]


# ======================================================================== the listed units (offline checks' mutants)
CENSUS_LINE = ("164: 25 (writes 6, chain 1, masked 2, error 3, forbidden 6, dead 7, inert 0); 165: 18 (writes 6, chain 1, "
               "masked 2, error 3, forbidden 1, dead 5, inert 0); 166: 18 (writes 8, chain 1, masked 2, error 4, "
               "forbidden 0, dead 3, inert 0); 0 unresolved; every error-path guard reachable (10 of 10; 164 and 165 "
               "ip97 dead behind ip57's 385); every forbidden site reachable (7 of 7); 164, 165, 166 hold no entrance "
               "dispatch (every Init reachable); 166 e2 "
               "shared from e6 t1 ip489, storeless; 166 e1 not instanced, storeless")
REGIONS_LINE = ("4 regions (4 exit: 164.e2 y > 12000, 164.e3 y < 6000, 165.e2 y > 15000, 165.e3 y < 11000), 0 hot-spots, "
                "4 gateway rows all registered; 166 none")


def _check_mutants(name0: str, check, pred: dict, line_ok, muts) -> list:
    """``[(name, ok, detail)]``: ``check(pred)`` PASSES (``line_ok(detail)``), then FAILS on each mutant by its clause."""
    out = []
    ok, _w, detail = check(pred)
    out.append((name0, ok is True and line_ok(detail), detail[:150]))
    for name, mutate, clause in muts:
        p = copy.deepcopy(pred)
        mutate(p)
        ok, _w, detail = check(p)
        at_ = detail.find(clause)
        out.append((name, ok is False and at_ >= 0, f"{'FAIL' if ok is False else 'PASS'}: "
                                                     + (detail[max(0, at_ - 40):at_ + 110] if at_ >= 0 else detail[:150])))
    return out


def _move(name_from: str, name_to: str, test):
    def mutate(p):
        ks = [k for k in p[name_from] if test(k)]
        p[name_from] = [k for k in p[name_from] if not test(k)]
        p[name_to] = list(p[name_to]) + ks
    return mutate


def _drop(name, test):
    def mutate(p):
        p[name] = [k for k in p[name] if not test(k)]
    return mutate


def _site(donor, sid, tag, ip):
    return lambda k: (k["donor"], k["sid"], k["tag"], k["ip"]) == (donor, sid, tag, ip)


def unit_store_census(pred: dict, stock) -> list:
    """O8-CENSUS on the install PASSES with 6.1's line; each mutant FAILS by name: 164 e3 t2 ip215 moved to
    ``forbidden_sites`` (dead: its own ip54 -- the census class is the bytes', the reach proof keeps error paths only, so
    the move reads as a class not the census's); 166 e6 t1 ip502 out of the writes; 164 e1 t3 ip308 out of
    ``forbidden_sites``; 166 e2 given a store (a live shared entry holding a global store); 164 e0 t0 ip97 moved back to
    ``error_path`` (its guard cannot hold: ip57's 385)."""
    muts = [
        ("census-164-e3-215-forbidden", _move("dead", "forbidden_sites", _site(164, 3, 2, 215)),
         "164 e3 t2 ip215 (164 e3 t2 Byte[13] := 3 (dead: behind Map.Bit[162] == 0 at ip193, which its own ip54 set 1 "
         "first)): a forbidden site no arrival value reaches"),
        ("census-166-502", _drop("writes", _site(166, 6, 1, 502)), "166 e6 t1 ip502 Global.Byte[8]: in no list"),
        ("census-164-308", _drop("forbidden_sites", _site(164, 1, 3, 308)),
         "164 e1 t3 ip308 Global.Bit[3851]: in no list"),
        ("census-164-97-error", _move("dead", "error_path", lambda k: (k["donor"], k["sid"], k["ip"]) == (164, 0, 97)),
         "164 e0 t0 ip97 (164 Byte[13] := 9 (dead: ip57 just set Int16[9] 385, so ip79's Int16[9] < 0 never holds)): "
         "an error_path site no arrival value reaches")]
    out = _check_mutants("store-census", lambda p: O.O8.census_check(p, stock), pred, lambda d: d == CENSUS_LINE, muts)
    # 166 e2 given a store: the bytes' every site, and one global store in 166's e2 (the shared clank loop)
    i166 = stock(166)

    def sites(idx):
        found, und = P.store_sites(idx)
        if idx is i166:
            found = found + [{"sid": 2, "tag": 1, "ip": 40, "kind": "global", "target": "Global.Byte[300]",
                              "text": "a mutant"}]
        return found, und
    bad, _counts, _proof = O.store_census8(list(pred["route"]), stock, pred, sites=sites)
    hit = [b for b in bad if b.startswith("166 e2: a live shared entry that holds a global store")]
    out.append(("census-166-e2-store", bool(hit), "; ".join(hit or bad)[:150]))
    return out


def unit_regions(pred: dict, stock) -> list:
    """O8-REGIONS on the install PASSES with 6.1's line; each mutant FAILS naming its clause: 164.e2's points shifted,
    164.e3's gate y_lt 7000, 165.e2 missing, 165.e3 with role hazard."""
    def shift(p):
        p["regions"]["164.e2"]["points"][0][0] += 10
    return _check_mutants("regions", lambda p: O.O8.regions_check(p, stock), pred, lambda d: d == REGIONS_LINE, [
        ("regions-164-e2-points", shift, "164.e2 (a): the bytes' first SetRegion is"),
        ("regions-164-e3-gate", lambda p: p["regions"]["164.e3"].__setitem__("gate", {"y_lt": 7000}),
         "164.e3 (c): its gate {'y_lt': 7000}"),
        ("regions-165-e2-missing", lambda p: p["regions"].pop("165.e2"), "165.e2 (b): a gateway"),
        ("regions-165-e3-hazard", lambda p: p["regions"]["165.e3"].__setitem__("role", "hazard"),
         "165.e3: role 'hazard' is not exit")])


def goals_lines() -> tuple:
    """6.1's O8-GOALS lines, as substrings of the detail: those no step's ``start`` moves (the goals' walls, the pinned
    heights, the gates, the release). A start-dependent number -- a route's legs and length, the seat's and the knight's
    start's distances off the planned routes, the pinch point on the plan -- is never pinned (F1 may move a start)."""
    return ("(164, 1190, 1) #0 walk wall 118 route ", "(164, 1190, 1) #1 trigger wall 79 route ",
            "(165, 1190, 2) #0 walk wall 186 route ", "(165, 1190, 2) #1 trigger wall 107 (its door fires ",
            "(164, 1190, 1) #1 (g1') no route at 80, its 64 the plan",
            "(164, 1190, 1) #0 (g2') 164.e2 dead on its floor", "(164, 1190, 1) #1 (g2') 164.e3 dead on its floor",
            "(165, 1190, 2) #1 (g2') 165.e3 dead on its floor",
            "(164, 1190, 1) #0 (g3') the goal disc (253 points) on its level only", "other levels at [3961, 13893]",
            "(164, 1190, 1) #1 (g4') fires 164.e2 at ", "(165, 1190, 2) #1 (g4') fires 165.e2 at ",
            "(164, 1190, 1) #0 (g5') the wait point 335.2u from 164.e2, 293.5u from 164.e3",
            "(164, 1190, 1) (g6') release y >= 8400 <= 8800; seat ", "u off #1 (> 252); start ",
            "(164, 1190, 1) (g7') the pinch (", "inside the window, no loop-1 sample in it")


def unit_goals(pred: dict, stock) -> list:
    """O8-GOALS on the install PASSES with 6.1's lines; each mutant FAILS by its clause: a step key "hold" (g0); 164
    #0's closures from another band (g0); 164 #1 at 80 (g1': no route, the step's own (g0)); 165 #0 at 110 (g1': a route
    exists at 120); 165 #0 without 165.e3 in ``avoid`` (g2'); 164 #0's at_y [13000, 14500] (g3': tri 98's level); 164
    #1's until y_gt 14000 (g4': the door fires before the evidence holds); 164 #1's until y_gt 9000 and 165 #1's y_gt
    11000 (g4': looser than the door's gate -- the review's #4); 164 #0's exit_slack 300 (g5': 335u from
    164.e2 under 300 + 80 -- as built: the design's "P1 moved 200 u toward e2" lands 40u from a wall, so the step plans
    nothing and (g5') is never read); at_y [8000,
    9150] (g6': under the release 8400 -- a mutant (g3') fails too); the window's y band [5000, 6000] (g7')."""
    def step(c, n, **kw):
        def fn(p):
            s = p["table"][c]["steps"][n]
            for k, v in kw.items():
                if v is ...:
                    s.pop(k, None)
                else:
                    s[k] = v
        return fn

    def other_band(p):
        p["table"][0]["steps"][0]["closed_tris"] = list(O.CLOSURES8[(164, 1)])

    def no_e3(p):
        s = p["table"][1]["steps"][0]
        s["avoid"] = [k for k in s["avoid"] if k != "165.e3"]

    def window(p):
        p["_window"] = {"place": 164, "x": [900.0, 1310.0], "z": [4460.0, 4600.0], "y": [5000.0, 6000.0]}

    def check(p):
        w_ = p.pop("_window", None)
        return O.O8.goals_check(p, stock=stock, window=w_)
    return _check_mutants("goals", check, pred, lambda d: all(x in d for x in goals_lines()), [
        ("goals-hold-key", step(0, 0, hold=1), "(164, 1190, 1) #0 (g0): unknown step key(s) ['hold']"),
        ("goals-164-0-band", other_band, "(164, 1190, 1) #0 (g0): its 99 closures are not band_closures"),
        ("goals-164-1-at-80", step(0, 1, clearance=80), "(164, 1190, 1) #1 (g0): no route from"),
        ("goals-165-0-at-110", step(1, 0, clearance=110), "(165, 1190, 2) #0 (g1'): clearance 110 under the engine"),
        ("goals-165-0-no-e3", no_e3, "(165, 1190, 2) #0 (g2'): the registered exit 165.e3 is not in its avoid"),
        ("goals-164-0-at-y", step(0, 0, at_y=[13000, 14500]), "(164, 1190, 1) #0 (g3')"),
        ("goals-164-1-until", step(0, 1, until={"y_gt": 14000}), "(164, 1190, 1) #1 (g4'): the door 164.e2 fires"),
        ("goals-164-1-until-loose", step(0, 1, until={"y_gt": 9000}),
         "(164, 1190, 1) #1 (g4'): its until {'y_gt': 9000} is looser than its door 164.e2's gate (y > 12000)"),
        ("goals-165-1-until-loose", step(1, 1, until={"y_gt": 11000}),
         "(165, 1190, 2) #1 (g4'): its until {'y_gt': 11000} is looser than its door 165.e2's gate (y > 15000)"),
        ("goals-wait-slack", step(0, 0, exit_slack=300), "(164, 1190, 1) #0 (g5'): within 45 of the wait point"),
        ("goals-release", step(0, 0, at_y=[8000, 9150]), "(164, 1190, 1) #0 (g6')"),
        ("goals-window-y", window, "(164, 1190, 1) #1 (g7')")])


def unit_route_pins(pred: dict, stock) -> list:
    """O8-KEYS (e), THE ROUTE PINS and their scans (4.14), and O8-TEXT's route_mes, on the install PASS; each mutant FAILS
    by its clause: 164 e2 t2 ip42's constant; 164 e1 t1 ip178's; 164 e2 t2 ip51 as JMP_IF(L221); 164 e1 t1 ip187 as
    JMP_IFNOT(L15); 166 e6 t1 ip871 as Field(31205); a second DefinePlayerCharacter; 70 ip475's constant; mes 313 without
    its marker."""
    mes = D5.block3_us()
    out = []
    ok, detail = O.O8.route_pins_check(pred, stock)
    n = len(pred["route_pins"])
    out.append(("route-pins", ok is True and detail.startswith(f"{n} route pins equal; per field one "
                                                                "DefinePlayerCharacter instanced"), detail[:150]))
    for name, site, old, new in (("route-pins-164-ip42", [164, 2, 2, 42], "const(53536)", "const(53535)"),
                                 ("route-pins-164-ip178", [164, 1, 1, 178], "const(57136)", "const(57135)"),
                                 ("route-pins-164-ip51", [164, 2, 2, 51], "JMP_IFNOT(L221)", "JMP_IF(L221)"),
                                 ("route-pins-164-ip187", [164, 1, 1, 187], "JMP_IF(L15)", "JMP_IFNOT(L15)"),
                                 ("route-pins-166-ip871", [166, 6, 1, 871], "Field(55)", "Field(31205)"),
                                 ("route-pins-70-ip475", [70, 0, 0, 475], "const(2)", "const(3)")):
        p = copy.deepcopy(pred)
        pin = next(x for x in p["route_pins"] if x[:4] == site)
        pin[4] = pin[4].replace(old, new)
        ok, detail = O.O8.route_pins_check(p, stock)
        out.append((name, ok is False and f"{site[0]} e{site[1]} t{site[2]} ip{site[3]}" in detail, detail[:150]))
    base = C7.instanced_texts(stock(165), 343)
    ok, detail = O.O8.route_pins_check(pred, stock, scans={165: base + [(9, 0, 999, "DefinePlayerCharacter()")]})
    out.append(("route-pins-two-players", ok is False and "2 DefinePlayerCharacter" in detail, detail[:150]))
    mm = dict(mes)
    mm[313] = str(mm[313]).replace("[STNR]", "[ZDNE]")
    ok, _w, detail = O.O8.text_check8(pred, mes=mm)
    out.append(("route-mes-313", ok is False and "mes 313 does not hold '[STNR]'" in detail, detail[:150]))
    return out


def unit_build_pins(pred: dict, tmp: Path) -> list:
    """O8-BUILD's route pins and THE RAW EXIT on a synthetic build through a ``stock_lang`` seam (the three route
    members, every language): the clean build PASSES; each mutant FAILS by its clause -- 31258 with one byte changed (a
    statement's byte, jp); 31258's Field(55) remapped to 31205 (us); 31256 differing outside its operands (uk)."""
    from ff9mapkit.config import LANGS, ModLayout
    from ff9mapkit.content.verbatim import remap_fields
    from ff9mapkit.eb import EbScript
    real = ST.stock_lang()
    cache: dict = {}

    def stock_lang(fid, lang):
        if (fid, lang) not in cache:
            cache[(fid, lang)] = real(fid, lang)
        return cache[(fid, lang)]
    chain = members_of(pred)
    names = {int(f): n for f, n in pred["names"].items()}
    members = {f: d for f, d in chain.items() if d in O.ROUTE_DONORS}
    retarget = {d: f for f, d in chain.items()}

    def instr(donor, lang, sid, tag, ip):
        eb = EbScript.from_bytes(stock_lang(donor, lang))
        e_ = next(x for x in eb.entries if x.index == sid)
        f_ = next(f for f in e_.funcs if f.tag == tag)
        return next(i for i in eb.instrs(f_) if i.off - e_.abs_start == ip)

    def build(name, mutate=None) -> Path:
        root = tmp / name
        lay = ModLayout(root)
        for fid, dn in members.items():
            for L in LANGS:
                data = bytearray(remap_fields(stock_lang(dn, L), retarget))
                if mutate is not None:
                    mutate(fid, L, data)
                p_ = lay.eb_path(L, f"EVT_{names[fid]}.eb.bytes")
                p_.parent.mkdir(parents=True, exist_ok=True)
                p_.write_bytes(bytes(data))
        return root
    m166 = next(f for f, d in members.items() if d == 166)
    m164 = next(f for f, d in members.items() if d == 164)

    def flip(fid, L, data):
        if fid == m166 and L == "jp":
            ins = instr(166, L, 6, 1, 345)
            data[ins.off + 3] ^= 0x01

    def remap55(fid, L, data):
        if fid == m166 and L == "us":
            ins = instr(166, L, 6, 1, 871)
            assert ins.imm(0) == 55, ins
            data[ins.off + 2:ins.off + 4] = (31205).to_bytes(2, "little")

    def outside(fid, L, data):
        if fid == m164 and L == "uk":
            ins = instr(164, L, 0, 0, 57)
            data[ins.off + 3] ^= 0x01

    def check(root):
        ok, d1 = O.O8.build_pins(pred, root, stock_lang=stock_lang)
        rok, d2 = O.O8.raw_exits_check(pred, root, stock_lang=stock_lang)
        return ok and rok, f"{d1}; {d2}"
    out = []
    ok, detail = check(build("bp8-clean"))
    out.append(("build-pins-clean", ok is True and "21 member files (3 route members x 7 languages)" in detail
                and "is 166 byte for byte with e6 t1 ip871 Field(55) raw (7 member files)" in detail, detail[:150]))
    for name, mutate, clause in (("build-pins-166-byte", flip, "not its donor byte for byte"),
                                 ("build-pins-166-field-31205", remap55, "not a raw Field(55)"),
                                 ("build-pins-164-outside", outside, "differ outside the in-chain Field() operands")):
        ok, detail = check(build(name, mutate))
        at_ = detail.find(clause)
        out.append((name, ok is False and at_ >= 0,
                    f"{'FAIL' if ok is False else 'PASS'}: " + (detail[max(0, at_ - 60):at_ + 90] if at_ >= 0
                                                                else detail[:150])))
    return out


def _key(p: dict, name: str, donor: int, ip: int, sid: int | None = None) -> dict:
    return next(k for k in p[name] if (k["donor"], k["ip"]) == (donor, ip) and (sid is None or k["sid"] == sid))


#: A synthetic 55 e10 t1 for KEYS (g)'s other-function proof: a UInt16[0] store under Map.Byte[24]'s case 1 -- the
#: arrival's -- reachable on this arrival, so the live read could see it.
SYNTH55_E10 = [(0, 0, "SET({Map.Byte[24] B_EXPR_END})"), (5, 5, "SWITCH(0, L40, L30, L20)"),
               (20, 20, "SET({Global.UInt16[0] const(1400) B_LET B_EXPR_END})"), (28, 28, "JMP(L40)"),
               (30, 30, "JMP(L40)"), (40, 40, "RET()")]
SYNTH55_SITES = [{"sid": 10, "tag": 1, "ip": 20, "kind": "global", "target": "Global.UInt16[0]"}]


#: O8-KEYS's offline mutants (section 8): the DRAFT, deep-copied, one thing changed (or one seam given); the check must
#: then read FAIL -- after it has read PASS on the unchanged draft -- and its detail hold the clause. Each entry:
#: ``(name, mutate(p), clause, keys_check keywords | None)``.
OFFLINE_MUTANTS = [
    ("keys-write-value", lambda p: _key(p, "writes", 165, 844).update(value=3), "the bytes give 2, the key says 3", None),
    ("keys-chain-off", lambda p: p["chain"][0].update(off=210), "FieldEntrance 343", None),
    ("keys-start-first-target", lambda p: p["start_first"].update(target="Global.Bit[192]"),
     "164's Main_Init: its first store", None),
    ("keys-start-music-138", lambda p: p["start_music"].update(ip=138, off=132), "is 0 writes keys, not one", None),
    ("keys-scoped-old-7", lambda p: p["start_scoped"][0]["after"].update(old=7), "after.old 7, O7's frozen pattern",
     None),
    ("keys-after-run", lambda p: p["start_scoped"][0]["after"].update(run="O1-O6"),
     "after.run 'O1-O6' is not the class's AFTER_RUN 'O1-O7'", None),
    ("keys-prior-removed", lambda p: _key(p, "writes", 166, 380).pop("prior"), "names no registered prior", None),
    ("keys-start-read-race-130", lambda p: p["start_reads"][1].update(race=[70, 0, 0, 130]),
     "its race [70, 0, 0, 130] := 2 is no pinned field-70 store", None),
    ("keys-carried-no-3796", lambda p: p["carried"]["values"].pop("Global.Bit[3796]"),
     "carried: the typed values differ from the derivation", None),
    ("keys-carried-3811", lambda p: p["carried"]["values"].__setitem__("Global.Bit[3811]", [0, 1]),
     "extra ['Global.Bit[3811]']", None),
    ("keys-carried-in-end-state", lambda p: p["end_state"].__setitem__("Global.Bit[3796]", 0),
     "carried: ['Global.Bit[3796]'] in end_state", None),
    ("keys-carried-route-store", lambda p: None, "read or stored by a function the route runs", "carried-scan"),
    ("keys-trace-no-byte8", lambda p: p["end_state_trace"].pop("Global.Byte[8]"),
     "is not end_state_trace's", None),
    ("keys-55-case-1", lambda p: None, "is reachable on this arrival", "synthetic-55"),
    ("keys-movie-cinematic-711", lambda p: p["movie"].update(cinematic=[166, 6, 1, 711]),
     "the movie's cinematic [166, 6, 1, 711]", None),
    ("keys-seam-exit-502", lambda p: p["seam"].update(exit=[166, 6, 1, 502]), "the seam's exit [166, 6, 1, 502]", None),
]


def unit_offline_mutants(pred: dict, stock) -> list:
    """``[(name, ok, detail)]``: O8-KEYS reads PASS on the draft, then FAILS on each of :data:`OFFLINE_MUTANTS` by its
    clause (a seam named by the entry: ``carried-scan`` -- 165's scan given a function reading Bit[3796], the carried
    target given a route store; ``synthetic-55`` -- a 55 whose e10 t1 stores UInt16[0] in case 1)."""
    base = O.O8.keys_check(pred, stock)
    out = [("offline-draft-passes", base[0] is True, base[2][:120])]
    for name, mutate, clause, seam in OFFLINE_MUTANTS:
        p = copy.deepcopy(pred)
        mutate(p)
        kw = {}
        if seam == "carried-scan":
            kw["scans"] = {165: O.route_run_texts(stock(165), 343)
                           + [(7, 1, 900, "SET({Global.Bit[3796] const(1) B_LET B_EXPR_END})")]}
        elif seam == "synthetic-55":
            kw["items55"] = lambda s, t: SYNTH55_E10 if (s, t) == (10, 1) else None
            kw["sites55"] = SYNTH55_SITES
        ok, _what, detail = O.O8.keys_check(p, stock, **kw)
        caught = ok is False and clause in detail
        out.append((name, caught, f"KEYS {'FAIL' if ok is False else 'PASS (not caught)'}"
                                  + ("" if caught or ok is not False else f" -- not by {clause!r}") + f": {detail[:150]}"))
    return out


def listed_units(pred: dict, stock, tmp: Path) -> list:
    return (unit_store_census(pred, stock) + unit_regions(pred, stock) + unit_goals(pred, stock)
            + unit_route_pins(pred, stock) + unit_build_pins(pred, tmp) + unit_offline_mutants(pred, stock))


# ======================================================================== the run
def as_if_frozen(pred: dict) -> dict:
    """The predictions as the lead's freeze would leave them (research/o8_design.md 8; G45): every budget x1.5
    (rounded), ``rehearsals`` two run dirs, ``rehearsal_fps`` the rates they met, ``rehearsed`` filled with plausible
    values, each table step's ``start`` moved 20 u east -- nothing else changed."""
    p = copy.deepcopy(pred)
    p["budget"] = {k: (v if v is None else int(round(v * 1.5)) if isinstance(v, int) and not isinstance(v, bool)
                       else round(float(v) * 1.5, 2)) for k, v in p["budget"].items()}
    p["rehearsals"] = ["20261006-000001-o8-rh", "20261006-000002-o8-rh-fmv"]
    p["rehearsal_fps"] = [31.0, 60.0]
    p["rehearsed"] = {"stretch_s": 60.0, "wait_s": 4.5,
                      "steps_s": {"164 #0": 70.0, "164 #1": 90.0, "165 #0": 25.0, "165 #1": 95.0},
                      "movie_span_s": 45.4, "narrowest_pinch": 70.5}
    for c in p["table"]:
        for s in c["steps"]:
            if s.get("start") is not None:
                s["start"] = [s["start"][0] + 20, s["start"][1]]
    return p


def prepare(pred_path: Path | None, tmp: Path, *, as_if: bool = False) -> tuple:
    """``(path, what)``: the predictions the run reads -- ``pred_path``; else the frozen file once it exists; else the
    DRAFT, written to a temporary file; with ``as_if`` their :func:`as_if_frozen`, written to a temporary file."""
    if pred_path is not None:
        path, what = Path(pred_path), f"the file {Path(pred_path).name}"
    elif O.PREDICTIONS.is_file():
        path, what = O.PREDICTIONS, f"the frozen {O.PREDICTIONS.name}"
    else:
        path = tmp / "o8_predictions_draft.json"
        path.write_bytes((json.dumps(O.draft_predictions(), indent=1, sort_keys=True) + "\n").encode("utf-8"))
        what = "the draft"
    if not as_if:
        return path, what
    p = as_if_frozen(json.loads(path.read_text(encoding="utf-8")))
    out = tmp / "o8_predictions_as_if_frozen.json"
    out.write_bytes((json.dumps(p, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    return out, f"as_if_frozen({what})"


def _clauses_named(clauses: dict, det: dict) -> list:
    return [f"{cid} detail lacks {m}" for cid, marks in clauses.items() for m in marks if m not in det.get(cid, "")]


def _mark(ok) -> str:
    return "P" if ok is True else "F" if ok is False else "V"


def fork_scripts(pred: dict, stock) -> dict:
    """The members' scripts a session snapshots: each donor's stock bytes with the chain's Field() literals remapped
    (31258 is 166's, byte for byte: its Field(55) names no member)."""
    from ff9mapkit.content.verbatim import remap_fields
    members = members_of(pred)
    retarget = {dn: f for f, dn in members.items()}
    return {fid: remap_fields(stock(dn).data, retarget) for fid, dn in members.items()}


def judge_case(entry, pred: dict, path: Path, sdir: Path, scripts: dict, stock) -> tuple:
    """One registered case: ``(ok, verdict, got, misses, checks)``."""
    (_name, fn, want_verdict, want, clauses, report_has, want_void, want_cov, want_lacks, detail_has, stopped,
     reasons) = entry
    d = make_session(sdir, path, fn(copy.deepcopy(pred)), scripts, stopped=stopped)
    checks, report = O.O8.analyse(d, stock=stock)
    got, det = result(checks), details(checks)
    v = verdict(checks)
    miss = [f"{k} {_mark(got.get(k))}, want {_mark(x)}" for k, x in want.items() if got.get(k) is not x]
    miss += [f"check {k} not registered" for k in got if k not in want]
    if not v.startswith(want_verdict):
        miss.append(f"verdict {v!r}, want {want_verdict}")
    miss += _clauses_named(clauses, det)
    miss += [f"{k} detail lacks {s!r}" for k, ss in detail_has.items() for s in ss if s not in det.get(k, "")]
    miss += [f"report lacks {s!r}" for s in report_has if s not in report]
    runs = O.O8.read_session(d, pred, stock=stock) if (want_void or want_cov or want_lacks or reasons) else []
    for i, classes in want_void.items():
        have = {x["class"] for x in runs[i - 1]["void"]}
        if not set(classes) <= have:
            miss.append(f"run {i} VOID classes {sorted(have)}, want {classes}")
    for i, classes in want_lacks.items():
        have = {x["class"] for x in runs[i - 1]["void"]}
        if set(classes) & have:
            miss.append(f"run {i} VOID classes {sorted(have)} hold {sorted(set(classes) & have)}")
    for i, cov in want_cov.items():
        if runs[i - 1]["covered"] is not cov:
            miss.append(f"run {i} covered {runs[i - 1]['covered']}, want {cov}")
    for i, subs in reasons.items():
        whys = [str(x["why"]) for x in runs[i - 1]["void"]]
        for sub in subs:
            if not any(sub in y for y in whys):
                miss.append(f"run {i} VOID reasons lack {sub!r}: {[y[:90] for y in whys]}")
    return not miss, v, got, miss, checks


def run_cases(pred_path: Path | None = None, *, as_if: bool = False, only=None) -> int:
    """Every case, the story-o3 fixture and every unit, each printed with its marks; ``N/N cases as registered``; 1 on
    any miss. ``only`` (a set of names, a seam for a quick look) runs those alone."""
    stock = T.stock_script_source()
    fails, total = 0, 0
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pdir = tmp / "pred"
        pdir.mkdir()
        sdir = tmp / "sessions"
        sdir.mkdir()
        udir = tmp / "units"
        udir.mkdir()
        path, what = prepare(pred_path, pdir, as_if=as_if)
        print(f"predictions: {what}")
        pred, _sha = O.O8.load(path)
        scripts = fork_scripts(pred, stock)
        for entry in CASES:
            name = entry[0]
            if only and name not in only:
                continue
            total += 1
            ok, v, got, miss, checks = judge_case(entry, pred, path, sdir, scripts, stock)
            fails += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name:40} {v[:44]:44} "
                  + " ".join(f"{k[3:]}={_mark(got.get(k))}" for k in CHECKS[1:]))
            if not ok:
                for m in miss:
                    print(f"     {m}")
                ST.say("     " + "\n     ".join(f"{w_} :: {dd[:300]}" for _ok, w_, dd in checks))
        if not only or "predictions-changed" in only:
            # O8-FROZEN: the predictions changed after the session recorded them
            total += 1
            copy_path = pdir / "pred_copy.json"
            copy_path.write_bytes(path.read_bytes())
            d = make_session(sdir, copy_path, six(pred), scripts)
            copy_path.write_bytes(path.read_bytes() + b" ")
            checks, _rep = O.O8.analyse(d, stock=stock)
            v = verdict(checks)
            got = result(checks)
            ok = got.get("O8-FROZEN") is False and v.startswith("NOT PROVEN") and all(
                got.get(k) is True for k in CHECKS if k != "O8-FROZEN")
            fails += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {'predictions-changed':40} {v[:44]}")
        for name, ok, detail in fixture_cases(stock, sdir) if (not only or "o3-fixture" in only) else ():
            total += 1
            fails += not ok
            ST.say(f"{'ok  ' if ok else 'FAIL'} {name:40} (story-o3) {detail[:150]}")
        for name, fn in units(pred, stock, scripts, sdir, path, udir):
            if only and name not in only:
                continue
            total += 1
            ok, detail = fn()
            fails += not ok
            ST.say(f"{'ok  ' if ok else 'FAIL'} {name:40} (unit) {detail[:150]}")
        if not only or "listed" in only:
            for name, ok, detail in listed_units(pred, stock, udir):
                total += 1
                fails += not ok
                ST.say(f"{'ok  ' if ok else 'FAIL'} {name:40} (unit) {detail[:150]}")
    print(f"\n{total - fails}/{total} cases as registered")
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--predictions", type=Path, default=None,
                    help="a predictions file (default: the frozen o8_predictions_v1.json once it exists, else the "
                         "draft, written to a temporary file)")
    ap.add_argument("--as-if-frozen", action="store_true",
                    help="run every case on as_if_frozen(the predictions): every freeze-time value changed")
    ap.add_argument("--only", nargs="*", default=None, help="run only these cases / units (a quick look; never the gate)")
    args = ap.parse_args(argv)
    return run_cases(args.predictions, as_if=args.as_if_frozen, only=set(args.only) if args.only else None)


if __name__ == "__main__":
    sys.exit(main())
