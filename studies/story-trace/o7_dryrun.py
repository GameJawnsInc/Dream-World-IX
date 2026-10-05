"""O7's analysis, driven on SYNTHETIC sessions (research/o7_design.md section 8): every registered check must read PASS
on the null pair and FAIL (or VOID) on the mutant built to break it -- a check that cannot fail is not a check.

    py studies/story-trace/o7_dryrun.py [--predictions studies/story-trace/o7_predictions_v1.json] [--as-if-frozen]

Without --predictions it reads the frozen o7_predictions_v1.json once the lead has frozen it, else it writes the DRAFT
(o7_castle_walk.draft_predictions: O4's chain's campaign.toml) to a temporary predictions file -- nothing is frozen until
the lead's rehearsals -- and runs every case against that. ``--as-if-frozen`` runs every case on :func:`as_if_frozen`
of those predictions instead: every value the lead's freeze changes changed (every budget x1.5, ``rehearsals`` and
``rehearsal_fps`` named, each step's ``start`` moved 20 u) -- no case may read a freeze-time literal, so both readings
give the same N/N (G39 runs both).

Each case writes a session directory the way the session does (o7_session.json, the members' scripts, one trace and
one driver log per run) and runs :meth:`o7_castle_walk.O7Segment.analyse` on it. The rows are real store sites of the
stock bytes of 154, 158, 159, 160, 162, 163 and 164 (every field row joins but the join-failure case's), shifted onto
the members on the F side (``fld`` = member, ``don`` = donor: 154 -> 31246, 158 -> 31250, 159 -> 31251, 160 -> 31252,
162 -> 31254, 163 -> 31255, 164 -> 31256), and EMITTED as the engine's sink emits them (StoryTrace.cs:374-401): a
same-value store only while its SITE has emitted no same-value row, a change up to 64 times, the rest counted into a ``c``
row at the epoch's close -- over O7's start values (the raw warp's SC 1190 and FieldEntrance 315 over field 70's
prologue: Byte[13] 1, Int16[9] 643, Int16[11] -1, Byte[14] 0, Byte[8] 125, every other target 0), so no site of the base
run is stored twice and nothing is counted: 51 ``w`` rows before the cut, 4.16's pattern. A run's driver log carries its
visit rows, the static watch's ``seen`` row for Dojebon in 154, the seven step rows (154's WALK to the ground on the
prior basis with its first-move check, then its cross of e8; 158's cross on the prior basis; 159's cross INTERRUPTED once
by the monologue -- its five page presses, its three rows in the gap -- and re-run; 160's, 162's and 163's crosses, each
seeded visit's first row judged) and the end row; its outcome the beats, the pages, the end state.

O7's ``case()`` is O3's, EXACT: every check a case does not name must read PASS -- a case naming COVER V expects every
core check VOID -- so each NOT PROVEN row names EVERY check it fails, and "alone" is a registered fact. A LANDING, WALK,
PATTERN, STATE or VOID-ASYM case also registers the clause its detail must name.

The units read the install read-only (the stock scripts, the stock walkmeshes, block 3's US text, O4's build): S17's
refusals and S18/S19's walk keywords, instanced_at7, the sink as the renderer and the FakeGame's H13 implement it,
O7-PATTERN's reading, the trace summary on end places, the state history, the visit windows and O7-WALK pure, O7-LANDING
pure (and (e) alone), STATE (c) by place, the static watch, the seeded fields, the monologue's and Dojebon's tests, A-START
(the error path and the start read), as_if_frozen, the fallback end (4.17), closures154, O7-CENSUS, O7-REGIONS, O7-GOALS
and the route pins with their mutants, O7-BUILD's pins on a synthetic build, O7-KEYS's offline mutants, the carried
derivation, and the launch's and the preflight's readers (O4's and O5's units on O7's pinned values).
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
import o7_castle_walk as O                                                 # noqa: E402
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
from segment_trace import members_of, place, verdict                       # noqa: E402


# ======================================================================== real store sites (donor, sid, tag, ip, target, value)
def _pro(place_, ips, i9, b13) -> list:
    """Main_Init's prologue at ``ips``: Bit[191] := 0, Bit[184] := 0, Int16[9] := ``i9``, Byte[13] := ``b13``, Int16[11]
    := -1, Byte[14] := 0 (4.16's P)."""
    return [(place_, 0, 0, ips[0], "Global.Bit[191]", 0), (place_, 0, 0, ips[1], "Global.Bit[184]", 0),
            (place_, 0, 0, ips[2], "Global.Int16[9]", i9), (place_, 0, 0, ips[3], "Global.Byte[13]", b13),
            (place_, 0, 0, ips[4], "Global.Int16[11]", -1), (place_, 0, 0, ips[5], "Global.Byte[14]", 0)]


P130 = (22, 49, 57, 130, 138, 200)
PRO = {154: _pro(154, (26, 53, 61, 123, 142, 204), -1, 0), 158: _pro(158, P130, 385, 1),
       159: _pro(159, (22, 49, 57, 119, 138, 200), -1, 0), 160: _pro(160, P130, 385, 1), 162: _pro(162, P130, 385, 1),
       163: _pro(163, P130, 385, 1), 164: _pro(164, P130, 385, 1)}
CH154 = (154, 8, 2, 355, "Global.Int16[2]", 300)
B13_158 = (158, 0, 0, 445, "Global.Byte[13]", 2)
E2_158 = (158, 2, 2, 194, "Global.Byte[13]", 3)
CH158 = (158, 2, 2, 222, "Global.Int16[2]", 331)
B8_159 = (159, 0, 0, 290, "Global.Byte[8]", 125)
M613 = (159, 16, 1, 613, "Global.Byte[208]", 0)
M648 = (159, 16, 1, 648, "Global.Byte[208]", 1)
M672 = (159, 16, 1, 672, "Global.Bit[3796]", 1)
CH159 = (159, 11, 2, 193, "Global.Int16[2]", 332)
B13_160 = (160, 0, 0, 465, "Global.Byte[13]", 2)
CH160 = (160, 5, 2, 227, "Global.Int16[2]", 333)
B13_162 = (162, 0, 0, 932, "Global.Byte[13]", 2)
CH162 = (162, 3, 2, 227, "Global.Int16[2]", 341)
B13_163 = (163, 0, 0, 684, "Global.Byte[13]", 2)
CH163 = (163, 2, 2, 227, "Global.Int16[2]", 342)
#: Each place's post-grant store (the grant's pass) and its door's rows (its tag 2: stores, then Field()).
POST = {154: [], 158: [B13_158], 159: [B8_159], 160: [B13_160], 162: [B13_162], 163: [B13_163]}
DOOR = {154: [CH154], 158: [E2_158, CH158], 159: [CH159], 160: [CH160], 162: [CH162], 163: [CH163]}
I26_154, I53_154, I61_154, I123_154, I142_154, I204_154 = PRO[154]
I57_158 = PRO[158][2]
I22_159, I49_159, I57_159, I119_159, I138_159, I200_159 = PRO[159]
END164 = PRO[164][0]
AFTER164 = PRO[164][1:]
#: Off the route, each a real store: 154's error path (ip101 Byte[13] := 9: window 56's branch), 158's (ip97); 160 e5
#: t2 ip199 (dead: behind Map.Bit[162] == 0); 159 e5 t3 ip636 (Haagen's talk: a forbidden site); 154 e2 t1 ip1520 (the
#: inert function: e2 not instanced at 315); 160 e2 t3 ip298 (Weimar's talk); 154 e8 t2 ip195 (the balcony branch ->
#: 153), e9 t2 ip355 (the west door's ground branch -> 155); 158 e1 t2 ip193 / ip221 (the back door -> 154); the
#: prologues of 153 and 155 (a wrong door's landing).
ERR154_101 = (154, 0, 0, 101, "Global.Byte[13]", 9)
ERR158_97 = (158, 0, 0, 97, "Global.Byte[13]", 9)
DEAD160_199 = (160, 5, 2, 199, "Global.Byte[13]", 3)
TALK159_636 = (159, 5, 3, 636, "Global.Bit[3849]", 1)
INERT154_1520 = (154, 2, 1, 1520, "Global.Int16[2]", 316)
TALK160_298 = (160, 2, 3, 298, "Global.Bit[3850]", 1)
BAL154_195 = (154, 8, 2, 195, "Global.Int16[2]", 301)
E9_355 = (154, 9, 2, 355, "Global.Int16[2]", 300)
E1_158_193 = (158, 1, 2, 193, "Global.Byte[13]", 3)
E1_158_221 = (158, 1, 2, 221, "Global.Int16[2]", 331)
S153 = [(153, 0, 0, 22, "Global.Bit[191]", 0), (153, 0, 0, 49, "Global.Bit[184]", 0),
        (153, 0, 0, 57, "Global.Int16[9]", -1)]
S155 = [(155, 0, 0, 22, "Global.Bit[191]", 0), (155, 0, 0, 49, "Global.Bit[184]", 0)]
SC_CS = (158, -1, -1, -1, "Global.UInt16[0]", 1190)
#: The checks, in the order the analysis reports them.
CHECKS = ("O7-FROZEN", "O7-COVER", "O7-FORBIDDEN", "O7-VOID-ASYM", "O7-START", "O7-NO-SC", "O7-CHAIN", "O7-RESIDUE",
          "O7-WRITES", "O7-NULL", "O7-STABLE", "O7-LANDING", "O7-WALK", "O7-PATTERN", "O7-MASKED", "O7-STATE",
          "O7-JOIN")
CORE = CHECKS[4:]
#: The frame layout of a base run (Time.frameCount, the trace's ``f`` and the log's frames alike): each place's
#: prologue (and its post-grant store) at F_PRO; Dojebon's first reading at F_SEEN; 154's WALK in [F_W0, F_W1]; each
#: cross from F_X0 to its loss F_LOST, its door's rows from F_DOOR (after the loss), the flip 20 frames after it; 159's
#: first attempt from F_INT0, its loss at F_INT_LOST (the monologue), the five pages from F_PAGES, the three rows from
#: F_MONO (inside the gap), the re-run from F_X0[159]; the cut at F_END (164 e0 t0 ip22).
F_PRO = {154: 1100, 158: 3600, 159: 4400, 160: 5400, 162: 6100, 163: 6800, 164: 7500}
F_SEEN = 1200
F_W0, F_W1 = 2000, 3000
F_X0 = {154: 3100, 158: 3800, 159: 4900, 160: 5600, 162: 6300, 163: 7000}
F_LOST = {154: 3500, 158: 4300, 159: 5300, 160: 6000, 162: 6700, 163: 7400}
F_DOOR = {154: 3510, 158: 4310, 159: 5310, 160: 6010, 162: 6710, 163: 7410}
F_INT0, F_INT_LOST, F_PAGES, F_MONO = 4600, 4700, 4710, 4750
#: Where each cross's loss was read (inside its target), the walk's arrival, the monologue's loss (just past x -1600).
LOST = {154: (0.0, -4080.0), 158: (-17.0, -15700.0), 159: (-2445.0, 365.0), 160: (-313.0, -500.0),
        162: (1000.0, 200.0), 163: (1000.0, 4900.0)}
WALK_TO = (5.0, -610.0)
INT_LOST = (-1601.0, 1572.0)
GRANT = {154: (-58.0, -3758.0), 158: (0.0, -12787.0), 159: (7.0, 3870.0), 160: (1357.0, -4063.0),
         162: (957.0, -3800.0), 163: (690.0, 2195.0)}
#: The first-move check each seeded visit's first row carries (S19's basis_check, degrees).
ANGLE = {154: 1.2, 158: 0.8, 160: 1.0, 162: 1.1, 163: 2.0}
#: The monologue's pages as the agent publishes them (block 3's US sources, 296-300; text only, never judged).
MONO_PAGES = ["What!?", "[STNR]\n“...”", "[STNR]\n“...”", "[STNR]\n“...”", "I must hurry!"]


# ======================================================================== events and their rendering
def at(frame: int) -> tuple:
    """A frame anchor: the next event's row lands at ``frame`` (later rows go on 10 frames apart)."""
    return ("at", int(frame))


def render(events: list, side: str, members: dict) -> list:
    """The rows the engine would write for ``events`` on ``side`` (o6_dryrun.render's rule, O7's start values:
    :data:`o7_castle_walk.START_VALUES`): F-side donors on their member ids; each store's ``old`` the variable's value so
    far; THE SINK'S RULE per SITE: a same-value store emitted only while its site has emitted no same-value row, a change
    up to 64 times, the rest counted into ``c`` rows just before ``off``. A store's ``opt``: ``fld`` / ``don``
    (overrides), ``old``, ``m``, ``src``, ``add``, ``f`` (its row's frame, the sequence kept), ``emit``, ``count``. An
    ``e`` event may carry a fourth item, ``{"fld"}``: an ``off`` in a REAL field on F."""
    fork = {d: f for f, d in sorted(members.items(), reverse=True)}

    def fld_of(donor):
        return fork.get(donor, donor) if side == "F" else donor
    rows, sites = [], {}
    values = dict(O.START_VALUES)
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
            rows.append({"k": "e", "f": f, "p": 0, "m": 1, "fld": eopt.get("fld", fld_of(donor)),
                         "don": eopt.get("fld", donor), "sc": sc, "why": why})
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


def base_events(route=O.ROUTE, end: int = O.END_FIELD) -> list:
    """A base run (research/o7_design.md 8): ``arm`` in field 70; the warp's FOUR residue rows there (SC 1190's two
    bytes, FieldEntrance 315's two); each route place's prologue and post-grant store at F_PRO, 159's three monologue rows
    at F_MONO (inside the interruption's gap), each door's rows at F_DOOR (after its loss); the end place's ip22 (THE CUT)
    at F_PRO[end], then its post-cut prologue; ``off`` in the end place (its member on F)."""
    ev = [e("arm", 70), r(70, 0, 0, 166), r(70, 1, 0, 4), r(70, 2, 0, 59), r(70, 3, 0, 1)]
    for p in route:
        ev += [at(F_PRO[p])] + [w(s) for s in PRO[p]] + [w(s) for s in POST[p]]
        if p == 159:
            ev += [at(F_MONO), w(M613), w(M648), w(M672)]
        ev += [at(F_DOOR[p])] + [w(s) for s in DOOR[p]]
    ev += [at(F_PRO[end]), w(PRO[end][0])] + [w(s) for s in PRO[end][1:]] + [e("off", end)]
    return ev


def _nth(ev: list, site, n: int) -> int:
    hits = [i for i, x in enumerate(ev) if _is(x, site)]
    return hits[n]


def drop_nth(ev: list, site, n: int = 0) -> list:
    i = _nth(ev, site, n)
    return ev[:i] + ev[i + 1:]


def upto_nth(ev: list, site, n: int, *tail) -> list:
    """The run cut off after the ``n``-th event of ``site`` (a drive that stopped there), then ``tail``."""
    i = _nth(ev, site, n)
    return ev[:i + 1] + list(tail)


def edit_nth(ev: list, site, n: int, fn) -> list:
    i = _nth(ev, site, n)
    return ev[:i] + [fn(ev[i])] + ev[i + 1:]


def move(ev: list, site, *, after_site=None, before_site=None) -> list:
    """``ev`` with ``site``'s event moved after ``after_site``'s (or before ``before_site``'s), its own frame dropped --
    the row then takes the frame of where it lands."""
    i = _nth(ev, site, 0)
    x = with_opt(ev[i], **{k: v for k, v in ev[i][-1].items() if k != "f"})
    rest = ev[:i] + ev[i + 1:]
    j = (_nth(rest, after_site, 0) + 1) if after_site is not None else _nth(rest, before_site, 0)
    return rest[:j] + [x] + rest[j:]


def _fld(members: dict, side: str, donor: int) -> int:
    inv = {d: f for f, d in sorted(members.items(), reverse=True)}
    return inv.get(donor, donor) if side == "F" else donor


def visits(rows: list, members: dict, route) -> list:
    """The driver's ``visit`` rows for a rendered run: one each time the written field changes after the arm, in the
    route's places only (a real route field on F too: a mutant's landing there is the place's visit to the driver's
    log), at the frame of the visit's first row."""
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
def route_rec(*, basis=None, angle=None, clearance=None, frame=None) -> dict:
    """A step row's trimmed route record (segment_drive.trim_route): the legs and the ladder's counters; S19's
    ``basis`` ("prior" seeded by this call, "cached" a basis in hand; absent: calibrated) and ``basis_check`` (the
    first-move check: angle, moved, frame, pressed) when given; S18's ``clearance``."""
    rec = {"route": 2, "travelled": 3000.0, "replans": 0, "pushes": 0, "waits": 0, "blockers": [], "landed": None,
           "changed_to": None, "handoff": True, "frozen": False, "boxed": False, "fps": {"fps": 60.0}}
    if clearance is not None:
        rec["clearance"] = clearance
    if basis is not None:
        rec["basis"] = basis
    if angle is not None:
        rec["basis_check"] = {"angle": angle, "moved": 58.0, "frame": frame, "pressed": "up"}
    return rec


def step_row(fld: int, place_: int, visit: int, n: int, kind: str, name: str, *, outcome="done", attempt=1,
             frame0: int, frame: int, frm=(0.0, 0.0), to=None, lost=None, lost_field=None, landed=None, flip=None,
             door=None, route=None, clearance=120, basis=None, v=None, by=None, why=None) -> dict:
    """A step's row as run_step writes it (segment_drive._Drive.run_step): its ``from`` sample (control held), its
    ``to`` sample (``to``: (x, z, control); default the loss), its ``lost`` sample (``lost``: (frame, x, z), read in
    ``lost_field`` -- the walk's field by default -- or None), ``landed``, ``flip_frame``, ``door``, the trimmed route
    record, ``clearance`` and ``basis`` (S18/S19: only when the step carries them)."""
    lo = None if lost is None else {"frame": lost[0], "control": False, "x": lost[1], "z": lost[2],
                                    "field": fld if lost_field is None else lost_field}
    tx, tz, tc = to if to is not None else ((lo or {}).get("x"), (lo or {}).get("z"), False)
    row = {"k": "step", "field": fld, "donor": place_, "sc": 1190, "visit": visit, "n": n, "kind": kind, "name": name,
           "attempt": attempt, "outcome": outcome, "t0": frame0 / 60.0, "t1": frame / 60.0, "frame0": frame0,
           "frame": frame, "from": {"frame": frame0, "control": True, "x": frm[0], "z": frm[1]},
           "to": {"frame": frame, "control": tc, "x": tx, "z": tz}, "lost": lo, "landed": landed,
           "flip_frame": flip, "door": door, "route": route if route is not None else route_rec(), "lunge": None,
           "climb": None, "depth": None, "v": v, "by": by, "why": why}
    if clearance is not None:
        row["clearance"] = clearance
    if basis is not None:
        row["basis"] = basis
    return row


def press(fld, donor, visit, frame, raw, seq) -> dict:
    """A page press as the drive logs it (rule 7)."""
    return {"k": "press", "why": "page", "field": fld, "donor": donor, "visit": visit, "sc": 1190,
            "pre": {"frame": frame, "control": False, "x": None, "z": None}, "post": None, "near": [], "seq": seq,
            "ack_frame": frame + 5, "button": "confirm", "raws": [raw], "texts": [raw], "accepted_frame": frame + 1,
            "down_frame": frame + 2}


def cell_log(pred: dict, c: dict, fld_of) -> tuple:
    """One table cell's step rows as a covered run writes them (research/o7_design.md 8's base run): a ``walk`` done
    within its tolerance of its goal, control held; a ``cross`` done -- its loss in its target in the walk's field, its
    landing the side's field of its ``to``, its flip 20 frames after the loss; 159's cross INTERRUPTED once by the
    monologue (its loss just past x -1600; the five page presses), then re-run. The visit's FIRST row carries the seeded
    basis "prior" and its first-move check; a later row of a seeded visit reads "cached"; 159 (no ``basis``) is
    calibrated (no key). ``(rows, presses)`` in log order."""
    p, visit = c["donor"], c["visit"]
    fld = fld_of(p)
    seeded = any(s.get("basis") == "prior" for s in c["steps"])
    rows, presses = [], []
    for n, s in enumerate(c["steps"]):
        first = n == 0
        rb = (dict(basis="prior", angle=ANGLE.get(p, 1.0)) if seeded and first else
              dict(basis="cached") if seeded else {})
        frm = GRANT.get(p, (0.0, 0.0)) if first else tuple(map(float, s.get("start") or (0, 0)))
        cl = s.get("clearance")
        if s["kind"] == "walk":
            rows.append(step_row(fld, p, visit, n, "walk", s.get("name"), frame0=F_W0, frame=F_W1, frm=frm,
                                 to=(WALK_TO[0], WALK_TO[1], True),
                                 route=route_rec(clearance=cl, frame=F_W0 + 50, **rb), clearance=cl,
                                 basis=s.get("basis")))
            continue
        if p == 159:
            rows.append(step_row(fld, p, visit, n, s["kind"], s.get("name"), outcome="interrupted", frame0=F_INT0,
                                 frame=F_INT_LOST + 5, frm=frm, lost=(F_INT_LOST, *INT_LOST),
                                 route=route_rec(clearance=cl), clearance=cl,
                                 why="control went at (-1601, 1572), outside 159.e11 and every other exit"))
            presses = [press(fld, p, visit, F_PAGES + 8 * i, MONO_PAGES[i], 300 + i) for i in range(5)]
            frm, attempt = INT_LOST, 2
        else:
            attempt = 1
        x0 = F_X0[p] if not (p == 154 and n == 1) else F_X0[154]
        rows.append(step_row(fld, p, visit, n, s["kind"], s.get("name"), attempt=attempt, frame0=x0,
                             frame=F_LOST[p] + 30, frm=frm, lost=(F_LOST[p], *LOST[p]), landed=fld_of(s["to"]),
                             flip=F_LOST[p] + 20, route=route_rec(clearance=cl, frame=x0 + 50,
                                                                  **({} if p == 159 else rb)),
                             clearance=cl, basis=s.get("basis")))
    return rows, presses


def standard_log(pred: dict, side: str, rows: list) -> tuple:
    """A run's driver log as the drive writes it (research/o7_design.md 2.2): each route visit's ``visit`` row, the
    static watch's ``seen`` row for each ``static_objects`` entry in its place's first visit (F_SEEN, at its placement),
    and each table cell's step rows (:func:`cell_log`, 159's page presses between its two attempts). ``(log, ctx)``:
    ``ctx`` the handles a case edits -- ``steps`` ``{(place, n, attempt): row}``, ``seen``, ``visits``, ``fld`` ``{place:
    field}``, ``presses``."""
    members = members_of(pred) if side == "F" else {}
    mem_all = members_of(pred)

    def fld_of(p):
        return _fld(mem_all, side, p)
    vis = visits(rows, members, set(pred["route"]))
    log, steps, seen, presses = [], {}, [], []
    cells = {c["donor"]: c for c in pred.get("table") or ()}
    for v in vis:
        log.append(v)
        p = v["donor"]
        for o in pred.get("static_objects") or ():
            if o["donor"] == p and v["visit"] == 1:
                row = {"k": "static", "what": "seen", "donor": p, "sid": o["sid"], "name": o.get("name"),
                       "field": v["field"], "visit": 1, "frame": F_SEEN, "x": -2700.0, "z": -1700.0}
                seen.append(row)
                log.append(row)
        c = cells.pop(p, None)                       # each cell's rows once: at its place's first visit row
        if c is None:
            continue
        srows, pr = cell_log(pred, c, fld_of)
        for row in srows:
            steps[(p, row["n"], row["attempt"])] = row
            log.append(row)
            if row["outcome"] == "interrupted":
                log += pr
                presses += pr
    return log, {"steps": steps, "seen": seen, "visits": vis, "fld": {p: fld_of(p) for p in pred["route"]},
                 "presses": presses}


# ======================================================================== sessions
def six(pred: dict, *, s=None, f=None) -> list:
    """S F S F S F: each run's base events (on the predictions' route and end), ``s`` / ``f`` applied per side as
    ``fn(events, n)`` (``n`` = 0, 1, 2 within the side)."""
    counts = {"S": 0, "F": 0}
    out = []
    for side in pred["order"]:
        n = counts[side]
        counts[side] += 1
        ev = base_events(tuple(pred["route"]), int(pred["end_field"]))
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
    rows.append([ok, O.O7.title("P-TEXT3"), detail])
    ok, detail = C4.p_engine(dict(eng), O.ENGINE)
    rows.append([ok, O.O7.title("P-ENGINE"), detail])
    assert all(x[0] for x in rows), rows
    return rows


def make_session(tmp: Path, pred_path: Path, runs: list, scripts: dict, *, stopped: str | None = None) -> Path:
    """A session directory as O7Segment.run writes one. Each run: ``{side, events | rows, end?, why?, beats?, v?, cell?,
    by?, install?, end_state?, end_field?, skipped?, stopped?, log? (fn(log, ctx) -> log, editing the standard log),
    pages? (fn(pages))}``; ``stopped``: the session's S15 stop."""
    pred, sha = O.O7.load(pred_path)
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
                        "sc": 1190, "end_state": end_state, "t": 110.0, "end_row": {"seen": True, "f": last, "s": 0.1}})
        pages = list(MONO_PAGES)
        if callable(run.get("pages")):
            pages = run["pages"](pages)
        beats = run.get("beats", {b: True for b in pred["beats"]})
        outcome = {"end": end, "why": run.get("why", f"field {ST.side_ends(pred, side)[0]}" if end == "reached"
                                              else "route: stopped"),
                   "void": None, "beats": beats, "pages": pages, "timed": [], "choices": [],
                   "steps": [x for x in log if x.get("k") == "step"], "overlays": [], "forbidden": [],
                   "end_state": end_state, "t": 110.0}
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
         lacks=None, detail_has=None, stopped=None):
    """Register a case, EXACT (O3's ``case()``): ``fail`` the checks that must read FAIL, ``clauses`` ``{check:
    [markers]}`` the clauses its detail must name (each such check FAILS too), ``cover_void`` -- COVER VOID and every core
    check VOID ("too few covered runs"); every other check must read PASS. ``report_has`` substrings of the report,
    ``void`` ``{run index: [classes its VOID reasons must include]}``, ``lacks`` ``{run index: [classes they must NOT
    include]}``, ``covered`` ``{run index: bool}``, ``detail_has`` ``{check: [substrings]}``, ``stopped`` the session's
    S15 stop."""
    want = {c: True for c in CHECKS}
    if cover_void:
        want["O7-COVER"] = None
        want.update({c: None for c in CORE})
    clauses = {("O7-" + k): v for k, v in (clauses or {}).items()}
    for c in list(fail) + list(clauses):
        cid = c if c.startswith("O7-") else "O7-" + c
        want[cid] = False
    dh = {("O7-" + k): v for k, v in (detail_has or {}).items()}

    def deco(fn):
        CASES.append((name, fn, want_verdict, want, clauses, tuple(report_has), void or {}, covered or {}, lacks or {},
                      dh, stopped))
        return fn
    return deco


def _void(run: dict, v: str, cell, by: str, why: str, *, events=None, log=None) -> None:
    """A run stopped: its events replaced (``events``), its drive VOID in class ``v`` at ``cell``, its log edited."""
    if events is not None:
        run["events"] = events
    run.update(end="void", why=f"route: {why}", v=v, cell=cell, by=by)
    if log is not None:
        run["log"] = log


def _all(runs: list, **kw) -> list:
    for run in runs:
        run.update(kw)
    return runs


def _side(runs: list, side: str, **kw) -> list:
    for run in runs:
        if run["side"] == side:
            run.update(kw)
    return runs


def _edit_log(fn):
    """A log edit applied to the standard log's handles: ``fn(ctx)`` changes them in place."""
    def apply(log, ctx):
        fn(ctx)
        return log
    return apply


def _log_upto(place_: int, kind: str = "step"):
    """A log cut before its first ``kind`` row of place ``place_`` (a drive that stopped there)."""
    def apply(log, ctx):
        i = next((j for j, x in enumerate(log) if x.get("k") == kind and x.get("donor") == place_), len(log))
        return log[:i]
    return apply


def _stop_in(ev: list, site, place_: int) -> list:
    """A run stopped after ``site``'s event (its row the last), then ``off`` in ``place_``."""
    return upto_nth(ev, site, 0, e("off", place_))


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


SCOPE_REPORT = ("a US session", "block 3: 7 byte-equal of 7",
                "start dependence -- none in value or path: a raw warp into 154@315 at SC 1190",
                "154 ip61 Int16[9] 643 -> -1 here, -1 -> -1 after",
                "159 e16 t1 ip613 Byte[208] 0 -> 0 here, 1 -> 0 after",
                "the O1-O6 routes as driven", "Bit[3795] 0", "1807 after them" if False else "UInt16[19] 0",
                "THE START READ: 159 ip290 read Byte[8] 125",
                "the end state -- read live on arrival in 164 but Byte[13]", "163 e0 t0 ip684 (2)",
                "the walks -- every step planned at its stated clearance (120; 163's 110",
                "Dojebon (e5) visit 1", "seen at frame 1200 (-2700.0, -1700.0)",
                "The session's end (end_run, warp first): the title came back")


@case("null-pair", "PROVEN", report_has=SCOPE_REPORT + ("; its pages (5 of 5) ['What!?', ",))
def _(pred):
    return six(pred)


@case("fork-drops-a-write", "NOT PROVEN", fail=("WRITES", "NULL", "STATE"), clauses={"PATTERN": ["(b)"]})
def _(pred):
    return six(pred, f=lambda ev, n: drop_nth(ev, M672))


def _no_monologue(ev, n):
    return [x for x in ev if not any(_is(x, s) for s in (M613, M648, M672))]


def _no_interrupt(log, ctx):
    """The 159 step without its interrupted row and the monologue's page presses: the fork's monologue never ran."""
    return [x for x in log if not (x.get("k") == "step" and x.get("outcome") == "interrupted")
            and x not in ctx["presses"]]


@case("monologue-absent-F", "NOT PROVEN", fail=("WRITES", "NULL", "STATE"), clauses={"WALK": ["(b)"],
                                                                                    "PATTERN": ["(b)"]})
def _(pred):
    return _side(six(pred, f=_no_monologue), "F", log=_no_interrupt)


@case("monologue-absent-one-F", "NOT PROVEN", fail=("STABLE", "WRITES", "STATE"), clauses={"WALK": ["(b)"],
                                                                                          "PATTERN": ["(b)"]})
def _(pred):
    runs = six(pred, f=lambda ev, n: _no_monologue(ev, n) if n == 0 else ev)
    runs[1]["log"] = _no_interrupt
    return runs


@case("chain-dropped-fork", "NOT PROVEN", fail=("CHAIN", "WRITES", "NULL", "STATE"),
      clauses={"LANDING": ["(b)"], "PATTERN": ["(b)"]})
def _(pred):
    return six(pred, f=lambda ev, n: drop_nth(ev, CH160))


@case("chain-first-old-wrong", "NOT PROVEN", fail=("CHAIN",))
def _(pred):
    old = lambda ev, n: edit(ev, lambda x: _is(x, CH154), lambda x: with_opt(x, old=316))   # noqa: E731
    return six(pred, s=old, f=old)


@case("start-residue-three", "NOT PROVEN", fail=("START",))
def _(pred):
    """Byte 3's row missing (S): O6's three-row contract would pass it; O7's four rows fail it."""
    return six(pred, s=lambda ev, n: [x for x in ev if not (x[0] == "r" and x[2] == 3)])


@case("start-residue-wrong", "NOT PROVEN", fail=("START",))
def _(pred):
    return six(pred, s=lambda ev, n: edit(ev, lambda x: x[0] == "r" and x[2] == 2, lambda x: r(70, 2, 0, 58)))


@case("start-first-missing", "NOT PROVEN", fail=("START",), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """154's ip26 dropped on both sides: 154's first write is ip53 (START (b)) and visit 1's sequence is one row short
    (PATTERN (b)); every later place's ip22 still writes boot_scratch on both sides, so MASKED passes."""
    gone = lambda ev, n: drop_nth(ev, I26_154)                          # noqa: E731
    return six(pred, s=gone, f=gone)


@case("start-music-old-wrong", "NOT PROVEN", fail=("START",))
def _(pred):
    old = lambda ev, n: edit_nth(ev, I123_154, 0, lambda x: with_opt(x, old=2))   # noqa: E731
    return six(pred, s=old, f=old)


@case("front-cut-write", "NOT PROVEN", fail=("START",))
def _(pred):
    in70 = ("w", 70, 3, 1, 40, "Global.Byte[13]", 1, {})               # a store in field 70, before the start
    return six(pred, f=lambda ev, n: before(ev, I26_154, in70))


@case("error-path-start-S", "PROVEN", void={1: ["V5", "A-START"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    runs = six(pred)
    ev = drop_nth(runs[0]["events"], I123_154)
    _void(runs[0], "V5", [154, 1190, 1], "driver", "a stop page (154's ambient error window 56), nothing pressed",
          events=upto_nth(ev, I61_154, 0, w(ERR154_101), e("off", 154)), log=_log_upto(154))
    return runs


@case("byte8-early-warp-one-F", "PROVEN", void={2: ["A-START"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    """One F run: the warp left field 70 before its ip249, so 159 ip290 -- the route's first store of Byte[8] -- reads
    old 0 and is EMITTED 0 -> 125 (same 0): A-START by the start read, the run uncovered -- never PATTERN."""
    runs = six(pred)
    runs[1]["events"] = edit_nth(runs[1]["events"], B8_159, 0, lambda x: with_opt(x, old=0))
    return runs


@case("byte8-early-warp-all-F", "VOID", cover_void=True, void={2: ["A-START"], 4: ["A-START"], 6: ["A-START"]})
def _(pred):
    """Every F run reads old 0 at 159 ip290: the start's problem on a whole side -- COVER VOID, never NOT PROVEN (the
    start read's A-START is the instrument's start, which VOID-ASYM (b) sets aside)."""
    return six(pred, f=lambda ev, n: edit_nth(ev, B8_159, 0, lambda x: with_opt(x, old=0)))


@case("byte8-explained-F", "NOT PROVEN", fail=("RESIDUE",), clauses={"PATTERN": ["(b)"]},
      lacks={2: ["A-START"], 4: ["A-START"], 6: ["A-START"]})
def _(pred):
    """Every F run: a C# write of Byte[8] in 158 (an ``r`` row, 125 -> 0) before 159 ip290, which then reads old 0 --
    EXPLAINED by the run's own earlier row, so no A-START (the start read's stricter rule): the run is covered and the
    write is judged -- RESIDUE (an unmasked residue row) and PATTERN (b) (ip290 emitted a change, same 0)."""
    return six(pred, f=lambda ev, n: edit_nth(after(ev, B13_158, r(158, 8, 125, 0)), B8_159, 0,
                                              lambda x: with_opt(x, old=0)))


@case("v5-error-158-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={2: False}, void={2: ["V5"]},
      lacks={2: ["A-START"]})
def _(pred):
    """158 takes the error path (an F run): V5 by the GAME at [158, 1190, 2] -- VOID-ASYM (a) -- and NO A-START: 154 is
    the start place, and 158's error row is no start state's."""
    runs = six(pred)
    ev = drop_nth(runs[1]["events"], PRO[158][3])
    _void(runs[1], "V5", [158, 1190, 2], "game", "a stop page (158's ambient error window 56)",
          events=upto_nth(ev, I57_158, 0, w(ERR158_97), e("off", 158)), log=_log_upto(158))
    return runs


@case("residue-after-start", "NOT PROVEN", fail=("RESIDUE",))
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, I26_154, r(154, 300, 0, 7)))


@case("writes-extra-symmetric", "NOT PROVEN", fail=("WRITES",), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """160 e5 t2 ip199's dead store (Byte[13] := 3) on both sides, right before its door's ip227: an extra key and an
    extra emitted tuple; STATE's histories symmetric; NULL symmetric."""
    add = lambda ev, n: before(ev, CH160, w(DEAD160_199))               # noqa: E731
    return six(pred, s=add, f=add)


@case("forbidden-row-both", "NOT PROVEN", fail=("WRITES",), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """Haagen's talk store (159 e5 t3 ip636 Bit[3849] := 1) in every run, before the step: an extra key on both sides."""
    add = lambda ev, n: after(ev, B8_159, w(TALK159_636))               # noqa: E731
    return six(pred, s=add, f=add)


@case("inert-row-both", "NOT PROVEN", fail=("WRITES", "CHAIN"), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """The inert function's store (154 e2 t1 ip1520 Int16[2] := 316: e2 is not instanced at 315) in every run, after
    154's prologue: an extra key, an extra emitted tuple -- and, being FieldEntrance's, an extra row over bytes 2-3, so
    CHAIN reads it too (re-registered: the design's want named WRITES and PATTERN; the bytes add CHAIN)."""
    add = lambda ev, n: after(ev, I204_154, w(INERT154_1520))           # noqa: E731
    return six(pred, s=add, f=add)


@case("extra-key-one-F", "NOT PROVEN", fail=("STABLE", "WRITES", "STATE"), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """STABLE's mutant: one F run of three holds 160 e2 t3 ip298's store (Weimar's talk)."""
    return six(pred, f=lambda ev, n: after(ev, B13_160, w(TALK160_298)) if n == 0 else ev)


@case("sc-write-fork", "NOT PROVEN", fail=("NO-SC", "WRITES", "NULL", "STATE"))
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, B13_158, w(SC_CS, src="cs")))


@case("sc-harness-poke-both", "NOT PROVEN", fail=("NO-SC",))
def _(pred):
    poke = lambda ev, n: after(ev, B13_158, w((158, -1, -1, -1, "Global.Byte[0]", 7), src="harness"))  # noqa: E731
    return six(pred, s=poke, f=poke)


@case("c-row-158-F", "NOT PROVEN", clauses={"PATTERN": ["(a)"]})
def _(pred):
    """Every F run: a ``c`` row of 158 ip57 (n 1) -- its prologue ran twice: PATTERN (a) alone."""
    return six(pred, f=lambda ev, n: after(ev, I57_158, w(I57_158, count=True)))


@case("byte13-repeat-both", "NOT PROVEN", clauses={"PATTERN": ["(b)"]})
def _(pred):
    """A second 158 ip445 store 2 -> 2, emitted (``same`` 1): symmetric, so STATE (a) cannot see it; visit 2's frozen
    sequence does."""
    again = lambda ev, n: after(ev, B13_158, w(B13_158))                # noqa: E731
    return six(pred, s=again, f=again)


@case("monologue-order-swap-both", "NOT PROVEN", clauses={"PATTERN": ["(b)"], "WALK": ["(c)", "out of order"]})
def _(pred):
    """ip648 before ip613 in EVERY run: visit 3's frozen sequence differs -- PATTERN (b) -- and the registered
    interruption's rows are out of their order in the gap -- WALK (c)'s "in order". Re-registered as rendered (the design
    named PATTERN (b) alone, then STATE (a)): STATE (a) compares the covered runs' histories with each other, and a
    reorder in every run of both sides leaves them identical; the one-side swap below is STATE (a)'s."""
    swap = lambda ev, n: move(ev, M648, before_site=M613)               # noqa: E731
    return six(pred, s=swap, f=swap)


@case("monologue-order-swap-F", "NOT PROVEN", clauses={"PATTERN": ["(b)"], "STATE": ["(a)"],
                                                     "WALK": ["(c)", "out of order"]})
def _(pred):
    """ip648 before ip613 on F alone: PATTERN (b) and WALK (c) on F, and Byte[208]'s emitted history differs between the
    sides -- STATE (a)."""
    return six(pred, f=lambda ev, n: move(ev, M648, before_site=M613))


@case("visit-split-both", "NOT PROVEN", clauses={"PATTERN": ["(b)"], "LANDING": ["(b)"]})
def _(pred):
    """A row of 154 (its ip204 again, a change 0 -> 1 -> 0 kept off by value) between 158's prologue rows on both sides:
    visit 2 split in two (PATTERN (b)), and place 154 written again after 158 loaded (LANDING (b))."""
    add = lambda ev, n: after(ev, PRO[158][1], w(I204_154, emit=True))  # noqa: E731
    return six(pred, s=add, f=add)


@case("lands-real-158-covered", "NOT PROVEN", fail=("FORBIDDEN", "WRITES"), clauses={"LANDING": ["(a)", "(b)", "(e)"]})
def _(pred):
    real = lambda ev, n: edit(ev, lambda x: x[0] == "w" and x[1] == 158,  # noqa: E731
                              lambda x: with_opt(x, fld=158, don=158))
    return six(pred, f=real)


@case("harness-after-exit158-both", "NOT PROVEN", clauses={"LANDING": ["(b)"]})
def _(pred):
    """A harness row of place 158 between its ip222 and 159's ip22: (b)'s next row -- PATTERN reads script rows only."""
    poke = lambda ev, n: after(ev, CH158, w((158, -1, -1, -1, "Global.Byte[300]", 9), src="harness"))  # noqa: E731
    return six(pred, s=poke, f=poke)


def _flip34(ev, n):
    """Visits 3 and 4 swapped: 160's block (its prologue, ip465 and its door) before 159's, the frames kept per row."""
    i159 = next(i for i, x in enumerate(ev) if _is(x, PRO[159][0])) - 1        # its anchor
    i160 = next(i for i, x in enumerate(ev) if _is(x, PRO[160][0])) - 1
    i162 = next(i for i, x in enumerate(ev) if _is(x, PRO[162][0])) - 1
    return ev[:i159] + ev[i160:i162] + ev[i159:i160] + ev[i162:]


@case("field-order-flip-both", "NOT PROVEN", fail=("CHAIN",), clauses={"LANDING": ["(b)"], "PATTERN": ["(b)"],
                                                                       "WALK": ["(c)"]})
def _(pred):
    """Visits 3 and 4 swapped in every run -- 158's door leads into 160, 160's into 159. Re-registered as rendered (the
    design: LANDING (b), CHAIN, PATTERN (b), STATE (a)): CHAIN (FieldEntrance 333 before 332), LANDING (b), PATTERN (b),
    and WALK (c) (159's monologue rows now outside their gap); STATE (a) cannot see a swap made in every run of both sides
    -- it compares the runs with each other."""
    return six(pred, s=_flip34, f=_flip34)


@case("last-place-harness-both", "NOT PROVEN", clauses={"LANDING": ["(c)"]})
def _(pred):
    poke = lambda ev, n: after(ev, CH163, w((163, -1, -1, -1, "Global.Byte[300]", 9), src="harness"))  # noqa: E731
    return six(pred, s=poke, f=poke)


@case("end-real-164-F", "NOT PROVEN", clauses={"LANDING": ["(d)"]})
def _(pred):
    real = lambda ev, n: edit(ev, lambda x: _is(x, END164), lambda x: with_opt(x, fld=164, don=164))   # noqa: E731
    return six(pred, f=real)


@case("end-boundary-residue-both", "NOT PROVEN", clauses={"LANDING": ["(d)"]})
def _(pred):
    add = lambda ev, n: before(ev, END164, r(164, 300, 0, 1))          # noqa: E731
    return six(pred, s=add, f=add)


@case("end-log-row-real-164-F", "NOT PROVEN", clauses={"LANDING": ["(c)"]})
def _(pred):
    return _side(six(pred), "F", end_field=164)


@case("end-row-missing-one-S", "PROVEN", void={1: ["A-NOEND"]}, covered={1: False, 3: True, 5: True},
      report_has=("A-NOEND",))
def _(pred):
    runs = six(pred)
    runs[0]["events"] = [x for x in runs[0]["events"] if not (x[0] == "w" and x[1] == 164)]
    return runs


@case("v19-one-F", "NOT PROVEN", fail=("FORBIDDEN",), clauses={"VOID-ASYM": ["(a)", "(c)"]}, covered={2: False})
def _(pred):
    """One F run lands in REAL 158 from member(154) (an un-retargeted Field()): V19 by the game at [158, 1190, 1] --
    rule 2 runs before rule 3 counts the visit; the trace ends in real 158 after its first store. Real 158 is no end
    place (O6's v19 landed in its END place, cut away), so its row stays and is off the route on F, unbacked:
    FORBIDDEN too (re-registered as rendered: O6's leak-real-153-F's shape)."""
    runs = six(pred)
    ev = edit(runs[1]["events"], lambda x: x[0] == "w" and x[1] == 158, lambda x: with_opt(x, fld=158, don=158))
    _void(runs[1], "V19", [158, 1190, 1], "game", "the fork run entered REAL 158, where member(158) 31250 was due",
          events=upto_nth(ev, PRO[158][0], 0, ("e", "off", 158, {"fld": 158})), log=_log_upto(158))
    return runs


def _balcony(run: dict, side: str, *, backed: bool) -> None:
    """154's cross of e8 ON THE BALCONY: its balcony branch (ip195 Int16[2] := 301, Field(153)), then 153's prologue
    (member(153) 31245 on F) -- backed by the cross's row V11 ``landed`` 153 / 31245 when ``backed``."""
    ev = upto_nth(run["events"], I204_154, 0, at(F_LOST[154] + 10), w(BAL154_195), *[w(s) for s in S153],
                  e("off", 153))
    land = 153 if side == "S" else 31245

    def log(lg, c):
        st = c["steps"][(154, 1, 1)]
        i = lg.index(st)
        st.update(outcome="void", v="V11", by="driver", landed=land, flip_frame=None,
                  why=f"the crossing to 158 landed in {land} (place 153)")
        return lg[:i + 1] if backed else lg[:i]
    if backed:
        _void(run, "V11", [154, 1190, 1], "driver", f"the crossing to 158 landed in {land} (place 153)", events=ev,
              log=log)
    else:
        _void(run, "V11", [153, 1190, 2], "game", f"left the route: entered {land} (place 153)", events=ev, log=log)


@case("walk-into-balcony-branch-S", "PROVEN", void={1: ["V11", "A-FORBIDDEN"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    """One S run crosses e8 on the balcony: its balcony branch's store, then rows in 153 -- off the route, BACKED by the
    cross's V11 landing in 153: A-FORBIDDEN, never a finding."""
    runs = six(pred)
    _balcony(runs[0], "S", backed=True)
    return runs


@case("balcony-branch-unbacked-F", "NOT PROVEN", fail=("FORBIDDEN",), clauses={"VOID-ASYM": ["(a)"]},
      covered={2: False})
def _(pred):
    """One F run holds e8 ip195's row and rows in 31245 that no step row explains: FORBIDDEN's finding; its drive VOID V11
    by the game (rule 2, no walk behind it) on F only -- VOID-ASYM (a)."""
    runs = six(pred)
    _balcony(runs[1], "F", backed=False)
    return runs


@case("v11-balcony-all-F", "NOT PROVEN", cover_void=True, clauses={"VOID-ASYM": ["(b)"]})
def _(pred):
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            _balcony(run, "F", backed=True)
    return runs


def _wrong_e9(run: dict, side: str, *, backed: bool) -> None:
    """154's cross strays into e9 on the ground: its store (ip355 := 300, Field(155)), then 155's prologue (member(155)
    31247 on F) -- backed by the cross's row V11 ``door`` 154.e9 ``landed`` 155 / 31247 when ``backed``."""
    ev = upto_nth(run["events"], I204_154, 0, at(F_LOST[154] + 10), w(E9_355), *[w(s) for s in S155], e("off", 155))
    land = 155 if side == "S" else 31247

    def log(lg, c):
        st = c["steps"][(154, 1, 1)]
        i = lg.index(st)
        st.update(outcome="void", v="V11", by="driver", door="154.e9", landed=land, flip_frame=None,
                  lost={"frame": F_LOST[154], "control": False, "x": -2000.0, "z": -2000.0, "field": c["fld"][154]},
                  why=f"the crossing to 158 landed in {land} (place 155): control went in 154.e9, not 154.e8")
        return lg[:i + 1] if backed else lg[:i]
    if backed:
        _void(run, "V11", [154, 1190, 1], "driver", f"the crossing to 158 landed in {land}", events=ev, log=log)
    else:
        _void(run, "V11", [155, 1190, 2], "game", f"left the route: entered {land} (place 155)", events=ev, log=log)


@case("wrong-door-e9-S", "PROVEN", void={1: ["V11", "A-FORBIDDEN"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    runs = six(pred)
    _wrong_e9(runs[0], "S", backed=True)
    return runs


@case("wrong-door-unbacked-F", "NOT PROVEN", fail=("FORBIDDEN",), clauses={"VOID-ASYM": ["(a)"]}, covered={2: False})
def _(pred):
    runs = six(pred)
    _wrong_e9(runs[1], "F", backed=False)
    return runs


@case("back-door-158-S", "PROVEN", void={1: ["V11"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    """One S run takes 158's back door: e1's two stores (ip193 Byte[13] := 3, ip221 Int16[2] := 331), then 154's prologue
    out of order -- rule 3's V11 by the driver on the walked row: the run uncovered."""
    runs = six(pred)
    ev = upto_nth(runs[0]["events"], B13_158, 0, at(F_LOST[158] + 10), w(E1_158_193), w(E1_158_221),
                  *[w(s, emit=True) for s in PRO[154]], e("off", 154))

    def log(lg, c):
        st = c["steps"][(158, 0, 1)]
        i = lg.index(st)
        st.update(outcome="interrupted", landed=None, door="158.e1",
                  lost={"frame": F_LOST[158], "control": False, "x": 0.0, "z": -10000.0, "field": c["fld"][158]},
                  why="control went in 158.e1 and the field held 5s")
        return lg[:i + 1]
    _void(runs[0], "V11", [158, 1190, 2], "driver", "the walked row's landing: 154 out of the route's order", events=ev,
          log=log)
    return runs


def _stall163(run: dict) -> None:
    """A run stopped at 163's stair foot: its step failed 3 of its 3 attempts (V7 by the driver at [163, 1190, 6])."""
    ev = upto_nth(run["events"], B13_163, 0, e("off", 163))
    _void(run, "V7", [163, 1190, 6], "driver", "step 163: the stair top (cross) failed 3 of its 3 attempts",
          events=ev, log=_log_upto(163))


@case("stall-at-163-one-S", "PROVEN", void={1: ["V7"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    runs = six(pred)
    _stall163(runs[0])
    return runs


@case("v7-stair-all-F", "NOT PROVEN", cover_void=True, clauses={"VOID-ASYM": ["(b)"]})
def _(pred):
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            _stall163(run)
    return runs


@case("v7-monologue-all-F", "NOT PROVEN", cover_void=True, clauses={"VOID-ASYM": ["(b)"]})
def _(pred):
    """Every F run V7 by the driver at [159, 1190, 3]: a second monologue interrupted the re-run, every run."""
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            _void(run, "V7", [159, 1190, 3], "driver", "step 159: the west door (cross) interrupted 2 times, over its 1",
                  events=_stop_in(run["events"], M672, 159))
    return runs


def _prior13(run: dict) -> None:
    """A run stopped at 154's first move: the seeded prior disagreed (V13 by the driver at [154, 1190, 1])."""
    _void(run, "V13", [154, 1190, 1], "driver", "the prior basis disagreed with the first move: 30.0 degrees",
          events=_stop_in(run["events"], I204_154, 154), log=_log_upto(154))


@case("v13-prior-one-F", "PROVEN", void={2: ["V13"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    runs = six(pred)
    _prior13(runs[1])
    return runs


@case("v13-prior-all-F", "NOT PROVEN", cover_void=True, clauses={"VOID-ASYM": ["(b)"]})
def _(pred):
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            _prior13(run)
    return runs


@case("v13-input-one-F", "PROVEN", void={2: ["V13"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    runs = six(pred)
    _void(runs[1], "V13", [160, 1190, 4], "driver", "outside input: XInput slot 0: buttons 0x1000",
          events=_stop_in(runs[1]["events"], B13_160, 160), log=_log_upto(160))
    return runs


@case("v14-one-S", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={1: False})
def _(pred):
    runs = six(pred)
    _void(runs[0], "V14", [162, 1190, 5], "game", "no progress for 60 s in 162 (place 162) at SC 1190",
          events=_stop_in(runs[0]["events"], B13_162, 162), log=_log_upto(162))
    return runs


@case("dojebon-released-S", "PROVEN", report_has=("MOVED at frame 2400 to (-1600.0, -1700.0), 1100.0u",))
def _(pred):
    """One S run's log holds a ``moved`` row for sid 5 (a release: he walked his patrol) -- report-only: he stores
    nothing, so no check reads it; the report names it."""
    def moved(lg, c):
        s = c["seen"][0]
        i = lg.index(s)
        return lg[:i + 1] + [dict(s, what="moved", frame=2400, x=-1600.0, z=-1700.0, **{"from": [-2700.0, -1700.0]},
                                  dist=1100.0)] + lg[i + 1:]
    runs = six(pred)
    runs[0]["log"] = moved
    return runs


@case("dojebon-unobserved-S", "PROVEN", report_has=("UNOBSERVED (no reading: the watch could not have seen a "
                                                      "release)",))
def _(pred):
    """One S run's log holds no ``seen`` row for sid 5 (never published): the report reads UNOBSERVED, never static."""
    runs = six(pred)
    runs[0]["log"] = lambda lg, c: [x for x in lg if x.get("k") != "static"]
    return runs


# -- O7-WALK's mutants (5.3): (a)-(c)'s fourteen, (d)'s three, each alone ----------------------------------------
def _both(edit_fn):
    return lambda pred: _all(six(pred), log=_steps(edit_fn))


@case("walk-no-step-both", "NOT PROVEN", clauses={"WALK": ["(a)", "0 done row(s) of 0"]})
def _(pred):
    return _all(six(pred), log=lambda lg, c: [x for x in lg if not (x.get("k") == "step" and x["donor"] == 154
                                                                    and x["n"] == 0)])


@case("walk-short-both", "NOT PROVEN", clauses={"WALK": ["(a)", "200u from the goal"]})
def _(pred):
    return _all(six(pred), log=_edit_log(lambda c: c["steps"][(154, 0, 1)]["to"].update(x=0.0, z=-800.0)))


@case("walk-done-without-control-both", "NOT PROVEN", clauses={"WALK": ["(a)", "without control"]})
def _(pred):
    return _all(six(pred), log=_edit_log(lambda c: c["steps"][(154, 0, 1)]["to"].update(control=False)))


@case("cross-landed-wrong-both", "NOT PROVEN", clauses={"WALK": ["(a)", "landed 155"]})
def _(pred):
    """158's done row ``landed`` 155 (31247 on F): a bypassed V11."""
    def wrong(c):
        c["steps"][(158, 0, 1)]["landed"] = 155 if c["fld"][158] == 158 else 31247
    return _all(six(pred), log=_edit_log(wrong))


@case("cross-lost-outside-both", "NOT PROVEN", clauses={"WALK": ["(a)", "beyond exit_slack"]})
def _(pred):
    return _all(six(pred), log=_edit_log(lambda c: c["steps"][(160, 0, 1)]["lost"].update(x=-313.0, z=-1500.0)))


@case("two-interrupts-159-both", "NOT PROVEN", clauses={"WALK": ["(a)", "2 interrupted row(s), over its 1"]})
def _(pred):
    def two(log, ctx):
        st = ctx["steps"][(159, 0, 1)]
        i = log.index(st)
        second = dict(st, attempt=2, frame0=F_INT0 + 150, frame=F_INT0 + 180,
                      lost=dict(st["lost"], frame=F_INT0 + 170))
        ctx["steps"][(159, 0, 2)]["attempt"] = 3
        return log[:i + 1] + [second] + log[i + 1:]
    return _all(six(pred), log=two)


@case("interrupt-missing-159-both", "NOT PROVEN", clauses={"WALK": ["(b)", "0 interrupted row(s)"]})
def _(pred):
    def gone(log, ctx):
        ctx["steps"][(159, 0, 2)]["attempt"] = 1
        return [x for x in log if x is not ctx["steps"][(159, 0, 1)]]
    return _all(six(pred), log=gone)


@case("interrupt-inside-box-both", "NOT PROVEN", clauses={"WALK": ["(b)", "outside the test"]})
def _(pred):
    return _all(six(pred), log=_edit_log(lambda c: c["steps"][(159, 0, 1)]["lost"].update(x=7.0, z=3870.0)))


@case("interrupt-loss-real-159-F", "NOT PROVEN", clauses={"WALK": ["(b)", "its loss read in 159, not 31251"]})
def _(pred):
    """The F runs' interrupted row's loss read at fld 159, not 31251: (b) is judged by PLACE, its field the side's."""
    return _side(six(pred), "F", log=_edit_log(lambda c: c["steps"][(159, 0, 1)]["lost"].update(field=159)))


@case("interrupt-in-a-door-both", "NOT PROVEN", clauses={"WALK": ["(a)", "an interrupted row in a door"]})
def _(pred):
    return _all(six(pred), log=_edit_log(lambda c: c["steps"][(159, 0, 1)].update(door="159.e10")))


@case("walk-window-row-both", "NOT PROVEN", clauses={"WALK": ["(c)", "inside visit 2's window"]})
def _(pred):
    """158 ip445's row stamped INSIDE 158's visit window, its order kept: WRITES, MASKED and PATTERN cannot see it."""
    late = lambda ev, n: edit_nth(ev, B13_158, 0, lambda x: with_opt(x, f=F_X0[158] + 20))   # noqa: E731
    return six(pred, s=late, f=late)


@case("monologue-row-outside-gap-both", "NOT PROVEN", clauses={"WALK": ["(c)", "outside its gap"]})
def _(pred):
    """ip672's row stamped after the re-run's frame0 (inside the visit window, outside the gap)."""
    late = lambda ev, n: edit_nth(ev, M672, 0, lambda x: with_opt(x, f=F_X0[159] + 20))     # noqa: E731
    return six(pred, s=late, f=late)


@case("walk-gap-row-154-both", "NOT PROVEN", clauses={"WALK": ["(c)", "inside visit 1's window"]})
def _(pred):
    """A row stamped between 154 #0's done frame and #1's frame0 -- a per-step window would miss it; the VISIT's sees it
    (154's ip204, stamped late, its order kept)."""
    late = lambda ev, n: edit_nth(ev, I204_154, 0, lambda x: with_opt(x, f=F_W1 + 50))     # noqa: E731
    return six(pred, s=late, f=late)


@case("walk-kind-window-row-both", "NOT PROVEN", clauses={"WALK": ["(c)", "inside visit 1's window"]})
def _(pred):
    """A row stamped mid-walk in 154 #0, between its frame0 and its frame (a walk row ends at its ``frame``)."""
    late = lambda ev, n: edit_nth(ev, I204_154, 0, lambda x: with_opt(x, f=F_W0 + 500))     # noqa: E731
    return six(pred, s=late, f=late)


@case("basis-check-missing-both", "NOT PROVEN", clauses={"WALK": ["(d)", "0 step rows carry basis_check"]})
def _(pred):
    return _all(six(pred), log=_edit_log(lambda c: c["steps"][(158, 0, 1)]["route"].pop("basis_check")))


@case("basis-check-30deg-both", "NOT PROVEN", clauses={"WALK": ["(d)", "30.0 deg off the prior"]})
def _(pred):
    return _all(six(pred), log=_edit_log(lambda c: c["steps"][(158, 0, 1)]["route"]["basis_check"].update(angle=30.0)))


@case("basis-cached-run3-S", "NOT PROVEN", clauses={"WALK": ["(d)", "basis 'cached'"]})
def _(pred):
    """Run 3 (S): 154 #0's route ``basis`` "cached" with no check -- the per-run forget missed (only the launch's first
    run to reach a field would judge its first move)."""
    def cached(c):
        rt = c["steps"][(154, 0, 1)]["route"]
        rt["basis"] = "cached"
        rt.pop("basis_check")
    runs = six(pred)
    runs[2]["log"] = _edit_log(cached)
    return runs


# -- O7-WALK's PASS cases --------------------------------------------------------------------------------------------
@case("walk-failed-once-162-both", "PROVEN")
def _(pred):
    def failed(log, ctx):
        st = ctx["steps"][(162, 0, 1)]
        i = log.index(st)
        miss = dict(st, outcome="failed", frame0=F_X0[162] - 100, frame=F_X0[162] - 50, lost=None, landed=None,
                    flip_frame=None, route=dict(st["route"]), why="the walk ended with control held and nothing crossed")
        st["attempt"] = 2
        st["route"] = {k: v for k, v in st["route"].items() if k != "basis_check"}
        st["route"]["basis"] = "cached"
        return log[:i] + [miss] + log[i:]
    return _all(six(pred), log=failed)


@case("walk-failed-twice-163-both", "PROVEN")
def _(pred):
    """163's two ``failed`` rows under its ``attempts`` 3 (the stair foot's snags), then done."""
    def failed(log, ctx):
        st = ctx["steps"][(163, 0, 1)]
        i = log.index(st)
        rows = []
        for k in range(2):
            rows.append(dict(st, outcome="failed", attempt=k + 1, frame0=F_X0[163] - 120 + 60 * k,
                             frame=F_X0[163] - 100 + 60 * k, lost=None, landed=None, flip_frame=None,
                             route=dict(st["route"]) if k == 0 else {kk: v for kk, v in st["route"].items()
                                                                     if kk != "basis_check"},
                             why="the walk ended 300u from its goal"))
        rows[1]["route"]["basis"] = "cached"
        st["attempt"] = 3
        st["route"] = {kk: v for kk, v in st["route"].items() if kk != "basis_check"}
        st["route"]["basis"] = "cached"
        return log[:i] + rows + log[i:]
    return _all(six(pred), log=failed)


@case("walk-interrupted-once-160-both", "PROVEN")
def _(pred):
    """160's cross interrupted once (control gone outside every exit, not in a door), then done: within its default
    ``interrupts`` 1 -- O7-WALK (b) reads only the REGISTERED interruption's step."""
    def inter(log, ctx):
        st = ctx["steps"][(160, 0, 1)]
        i = log.index(st)
        first = dict(st, outcome="interrupted", frame0=F_X0[160] - 100, frame=F_X0[160] - 45, landed=None,
                     flip_frame=None, lost={"frame": F_X0[160] - 50, "control": False, "x": 700.0, "z": -3000.0,
                                            "field": st["field"]})
        st["attempt"] = 2
        st["route"] = {k: v for k, v in st["route"].items() if k != "basis_check"}
        st["route"]["basis"] = "cached"
        return log[:i] + [first] + log[i:]
    return _all(six(pred), log=inter)


@case("cross-lost-unread-both", "PROVEN")
def _(pred):
    """162's done row with no ``lost`` (the call returned before the loss), its ``flip_frame`` set: the evidence is its
    landing; its window ends at the flip."""
    return _all(six(pred), log=_edit_log(lambda c: c["steps"][(162, 0, 1)].update(lost=None)))


@case("basis-check-on-step1-154-both", "PROVEN")
def _(pred):
    """154 #0's rows carry no ``basis_check`` (it pressed no evidence hold), #1's does: one check in the visit."""
    def moved(c):
        bc = c["steps"][(154, 0, 1)]["route"].pop("basis_check")
        c["steps"][(154, 1, 1)]["route"]["basis_check"] = bc
    return _all(six(pred), log=_edit_log(moved))


@case("w154-beat-missing", "VOID", cover_void=True, void={1: ["A-BEATS"], 3: ["A-BEATS"]})
def _(pred):
    runs = six(pred)
    for run in (runs[0], runs[2]):
        run["beats"] = dict({b: True for b in pred["beats"]}, w154_ground=False)
    return runs


@case("x163-beat-missing", "VOID", cover_void=True, void={1: ["A-BEATS"], 3: ["A-BEATS"]})
def _(pred):
    runs = six(pred)
    for run in (runs[0], runs[2]):
        run["beats"] = dict({b: True for b in pred["beats"]}, x163_e2=False)
    return runs


@case("end-cut", "PROVEN")
def _(pred):
    """More rows in 164 past the end (S): 164's post-cut prologue stored a second time -- all cut."""
    return six(pred, s=lambda ev, n: ev[:-1] + [w(x) for x in [END164] + AFTER164] + [ev[-1]])


def _end_state(pred: dict, **kv) -> dict:
    return dict(pred["end_state"], **{f"Global.{k}": v for k, v in kv.items()})


@case("end-state-differs", "NOT PROVEN", clauses={"STATE": ["(b)"]})
def _(pred):
    runs = six(pred)
    runs[3]["end_state"] = _end_state(pred, **{"Bit[3796]": 0})
    return runs


@case("byte13-live-race-both", "PROVEN")
def _(pred):
    """Every run's live end-state read carries Byte[13] 1 (164's prologue raced it): never compared -- Byte[13] is not
    in ``end_state``; its value is the trace's."""
    return _all(six(pred), end_state=dict(pred["end_state"]), pages=lambda pg: pg + ["Byte[13] read live 1"])


@case("byte13-trace-end-F", "NOT PROVEN", fail=("RESIDUE",), clauses={"STATE": ["(c)"]})
def _(pred):
    """Every F run: a C# write of Byte[13] (byte 13: 2 -> 1, an ``r`` row) after 163's ip684, before the door: the last
    pre-cut row on Byte[13]'s bytes is no longer 163 e0 t0 ip684 -- STATE (c), with RESIDUE (an unmasked residue row)."""
    return six(pred, f=lambda ev, n: after(ev, B13_163, r(163, 13, 2, 1)))


@case("masked-differs", "NOT PROVEN", fail=("MASKED",), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """Every F run without its Bit[184] rows: MASKED reads the region gone on F; PATTERN reads every visit short."""
    return six(pred, f=lambda ev, n: [x for x in ev if not (x[0] == "w" and x[5] == "Global.Bit[184]")])


@case("join-failure", "NOT PROVEN", fail=("JOIN",))
def _(pred):
    """An extra row at 159 e16 t1 ip614 (one byte into ip613's store), after ip290 before the step: JOIN alone --
    PATTERN reads only rows that join, STATE only keyed rows, WALK's window opens at the step's frame0."""
    off = (159, 16, 1, 614, "Global.Byte[208]", 0)
    add = lambda ev, n: after(ev, B8_159, w(off))                      # noqa: E731
    return six(pred, s=add, f=add)


@case("mismatched", "PROVEN", void={2: ["A-MISMATCH"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    return six(pred, f=lambda ev, n: edit(ev, lambda x: x[0] == "w" and x[1] == 158,
                                          lambda x: with_opt(x, don=31243)) if n == 0 else ev)


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


# ======================================================================== the units (no session)
def _rows(events, side="S", members=None) -> list:
    return T.parse_text("".join(json.dumps(x) + "\n" for x in render(events, side, members or {})))


def _raises(fn, match: str) -> bool:
    try:
        fn()
    except ValueError as err:
        return match in str(err)
    return False


def unit_step_of_walk(pred: dict) -> tuple:
    """S17's refusals (segment_drive.step_of): the draft's walk step passes; a walk carrying ``target``, ``until``,
    ``to`` or ``expect`` refused; a ``clearance`` of 0, of True and of "120" refused; a ``basis`` "cached" refused; every
    frozen predictions file of the study (O1-O6's tables) passes unchanged (globbed, never pinned)."""
    s = pred["table"][0]["steps"][0]
    got = {"draft": SD.step_of(pred, s)["kind"] == "walk"}
    for key, v in (("target", "154.e8"), ("until", {"z_gt": 0}), ("to", 158), ("expect", "choice")):
        got[f"walk-{key}"] = _raises(lambda key=key, v=v: SD.step_of(pred, dict(s, **{key: v})), "a walk carries no")
    for name, v in (("zero", 0), ("bool", True), ("str", "120")):
        got[f"clearance-{name}"] = _raises(lambda v=v: SD.step_of(pred, dict(s, clearance=v)), "clearance is a positive")
    got["basis-cached"] = _raises(lambda: SD.step_of(pred, dict(s, basis="cached")), "basis is one of")
    for f in sorted(HERE.glob("*predictions*.json")):
        p = json.loads(f.read_text(encoding="utf-8"))
        try:
            ok = all(SD.step_of(p, st) is not None for c in p.get("table") or () for st in c["steps"])
        except (ValueError, KeyError):
            ok = False
        got[f.name] = ok
    return all(got.values()), str({k: v for k, v in got.items() if not v} or f"all as registered ({len(got)})")


def unit_walk_kw(pred: dict) -> tuple:
    """S18/S19's walk keywords (segment_drive._Drive.walk_kw): ``clearance`` and ``basis`` reach route_to ONLY when the
    step carries them -- the draft's walk passes both, a step without them neither (every O1-O6 call as it was)."""
    from types import SimpleNamespace
    stub = SimpleNamespace(pred=pred, floor=lambda closed=None: "mesh", prior_for=lambda d: {"v": (0, 1), "h": (1, 0)},
                           donor=154)
    s = SD.step_of(pred, pred["table"][0]["steps"][0])
    kw = SD._Drive.walk_kw(stub, s)
    plain = SD.step_of(pred, {k: v for k, v in pred["table"][0]["steps"][0].items() if k not in ("clearance", "basis")})
    kw0 = SD._Drive.walk_kw(stub, plain)
    got = {"both": (kw.get("clearance"), kw.get("basis")) == (120.0, "prior"),
           "neither": "clearance" not in kw0 and "basis" not in kw0}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_instanced_at7(stock) -> tuple:
    """instanced_at7 (0.2 #3): 154 at 315 -> {object 5, 6, 7, 15; region 8, 9, 10; code 1, 11} (e2 not: the 304 branch);
    159 at 331 -> every Init of its Main_Init (no dispatch: every branch followed); 160 at 332 -> InitObject(2) included
    (behind Bit[3799] == 0); O4's walker and instanced_at6 raise on 159 -- the reason O7 has its own."""
    i154, i159, i160 = stock(154), stock(159), stock(160)
    a = O.instanced_at7(i154, 315)
    every159 = {(s[3], s[4]) for s in C4.instancing_sites(i159) if (s[0], s[1]) == (0, 0)}
    got = {"154@315": a == {("object", 5), ("object", 6), ("object", 7), ("object", 15), ("region", 8),
                            ("region", 9), ("region", 10), ("code", 1), ("code", 11)},
           "159-every-init": O.instanced_at7(i159, 331) == every159 and bool(every159),
           "160-object-2": ("object", 2) in O.instanced_at7(i160, 332),
           "o4-raises": _raises(lambda: C4.instanced_at(i159, 331), "no SWITCH"),
           "o6-raises": _raises(lambda: C6.instanced_at6(i159, 331), "no entrance dispatch")}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or f"all as registered: 154@315 {sorted(a)}")


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
                fake._warp_writes(315, 1190)
        elif ev[0] == "w":
            _k, donor, sid, tag, ip, target, value, _opt = ev
            fake.field_id = fork.get(donor, donor) if side == "F" else donor
            fake.donor = donor if side == "F" else None
            width, index = target.split(".", 1)[1].rstrip("]").split("[")
            bit = int(index) if width in T.BIT_WIDTHS else -1
            fake.script_store(sid, tag, ip, int(index) >> 3 if bit >= 0 else int(index), width, value, bit=bit)
    text = (game / "x64" / "ff9harness" / "story.jsonl").read_text(encoding="utf-8")
    return [json.loads(ln) for ln in text.splitlines() if ln.strip()]


def unit_render(pred: dict, tmp: Path) -> tuple:
    """THE SINK, one model, two implementations (0.2 #4): the base run's rows before the cut are 51 ``w`` rows (39
    unmasked) and no ``c`` row, on S and F; the SAME events through the FakeGame's H13 knob give the same ``(k, fld, sid,
    tag, ip, new, same, n, last)`` sequence, on S and F; the cut row 164 ip22 ``same`` 1 (a new site)."""
    members = members_of(pred)
    got = {}
    for side in ("S", "F"):
        rows = render(base_events(), side, members)
        fk = _fake_rows(base_events(), side, members, tmp)
        got[f"fake-{side}"] = D5._shape(rows) == D5._shape(fk)
        end164 = 164 if side == "S" else 31256
        cut = next(i for i, x in enumerate(rows) if x["k"] in ("w", "r") and x["fld"] == end164)
        before_ = [x for x in rows[:cut] if x["k"] == "w" and x["fld"] != 70]
        unmasked = [x for x in before_ if x["bit"] not in (191, 184)]
        got[f"counts-{side}"] = (len(before_), len(unmasked), sum(1 for x in rows if x["k"] == "c")) == (51, 39, 0)
        got[f"cut-{side}"] = (rows[cut]["ip"], rows[cut]["same"]) == (22, 1)
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_pattern(pred: dict, stock, tmp: Path) -> tuple:
    """O7-PATTERN's reading (4.16): :func:`o6_steiner.pattern_diff6` (``floating`` []) on the base run, joined on the
    stock bytes -- none, on S and F, render and the FakeGame alike, 7 + 9 + 11 + 8 + 8 + 8 rows; the monologue's order
    swapped, a repeat of 158 ip445, a row of 154 inside visit 2 and a missing door row each (b); a ``c`` row (a)."""
    members = members_of(pred)
    got = {}

    def diff(events, side="S", src="render"):
        m = members if side == "F" else {}
        rows = render(events, side, members) if src == "render" else _fake_rows(events, side, members, tmp)
        parsed = T.parse_text("".join(json.dumps(x) + "\n" for x in rows))
        kept, _at, _pre = ST.cut_at_start(parsed, 154, m)
        kept, _end = ST.cut_at_end(kept, [164], m)
        g = C5.pattern_of(kept, pred, m, C5.stock_join(stock, m))
        return C6.pattern_diff6(g, pred["pattern"]), g
    for side in ("S", "F"):
        for src in ("render", "fake"):
            d, g = diff(base_events(), side, src=src)
            got[f"{src}-{side}"] = d == [] and g["unjoined"] == 0 and [len(v) for v in g["visits"]] == [7, 9, 11, 8,
                                                                                                         8, 8]
    for name, ev in (("swap", move(base_events(), M648, before_site=M613)),
                     ("repeat", after(base_events(), B13_158, w(B13_158))),
                     ("split", after(base_events(), PRO[158][1], w(I204_154, emit=True))),
                     ("door-missing", drop_nth(base_events(), CH160))):
        d = diff(ev)[0]
        got[name] = bool(d) and all(x.startswith("(b)") for x in d)
    d = diff(after(base_events(), I57_158, w(I57_158, count=True)))[0]
    got["c-row"] = bool(d) and all(x.startswith("(a)") for x in d)
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_trace_summary(pred: dict, stock) -> tuple:
    """O7's trace summary (7.2; O4's lesson) of a base S run: the chain 6/6, writes 33/33, the error path, forbidden and
    dead sites absent; the crossings 154 ip355 -> 158 e0 t0 ip22 ... 162 ip227 -> 163 e0 t0 ip22 and 163 ip227 -> the cut
    (164 e0 t0 ip22); the monologue's three rows in order; Byte[13]'s last pre-cut row 163 ip684; 159 ip290's old 125;
    no c row, no unregistered key, no join failure; the four start residue rows. An F stage ending in member(164) 31256
    is cut at 31256's first row by its end PLACES -- while O3's summary given the same end FIELDS (the unit's mutant) is
    not cut at all."""
    members = members_of(pred)
    t = O.trace_summary(_rows(base_events()), pred, stock=stock)
    reg = {k: (sum(1 for x in v if x["present"]), len(v)) for k, v in t["registered"].items()}
    want = {"chain": (6, 6), "writes": (33, 33), "error_path": (0, 24), "forbidden_sites": (0, 22), "dead": (0, 24)}
    cr = t["crossings"]
    got = {"registered": reg == want,
           "crossings": [(c["exit"], c["next"] or c["cut"]) for c in cr] == [
               ("154 e8 t2 ip355 Global.Int16[2]=300", "158 e0 t0 ip22 Global.Bit[191]=0"),
               ("158 e2 t2 ip222 Global.Int16[2]=331", "159 e0 t0 ip22 Global.Bit[191]=0"),
               ("159 e11 t2 ip193 Global.Int16[2]=332", "160 e0 t0 ip22 Global.Bit[191]=0"),
               ("160 e5 t2 ip227 Global.Int16[2]=333", "162 e0 t0 ip22 Global.Bit[191]=0"),
               ("162 e3 t2 ip227 Global.Int16[2]=341", "163 e0 t0 ip22 Global.Bit[191]=0"),
               ("163 e2 t2 ip227 Global.Int16[2]=342", "164 e0 t0 ip22 Global.Bit[191]=0")],
           "monologue": [x["site"] for x in t["interruption_rows"]] == ["159 e16 t1 ip613", "159 e16 t1 ip648",
                                                                         "159 e16 t1 ip672"],
           "raced": (t["raced"]["Global.Byte[13]"] or {}).get("row") == "163 e0 t0 ip684 Global.Byte[13]=2",
           "start-read": [(x["old"], x["new"]) for x in t["start_reads"]] == [(125, 125)],
           "end-row": t["end_row"] == "w 164 e0 t0 ip22 Global.Bit[191]=0" and t["end_places"] == [164],
           "counts": t["pattern"]["counts"] == [],
           "clean": t["unregistered"] == [] and t["failures"] == [],
           "residue": [x[1:] for x in t["residue_before"]] == [[0, 0, 166], [1, 0, 4], [2, 0, 59], [3, 0, 1]]}
    frows = _rows(base_events(), "F", members)
    tf = O.trace_summary(frows, pred, side="F", end_fields=[31256], stock=stock)
    first = next(x.line for x in frows if x.k in ("w", "r") and x.fld == 31256)
    got["f-cut-at-member"] = tf["end"] == first and tf["end_places"] == [164] and tf["end_row_fld"] == 31256
    got["f-crossing-into-cut"] = (tf["crossings"][-1]["next"] or tf["crossings"][-1]["cut"]) == \
        "31256 e0 t0 ip22 Global.Bit[191]=0"
    got["o3-fields-uncut"] = P.trace_summary(frows, pred, side="F", end_fields=[31256], stock=stock)["end"] is None
    return all(got.values()), str({k: v for k, v in got.items() if not v} or f"all as registered: {reg}")


def unit_state_history(pred: dict, stock, scripts: dict, tmp: Path, path: Path) -> tuple:
    """O7-STATE (a)'s reading of a base run: Byte[13]'s eleven entries in route order -- (154, 0), (158, 1), (158, 2),
    (158, 3), (159, 0), (160, 1), (160, 2), (162, 1), (162, 2), (163, 1), (163, 2) -- and Byte[208]'s [(159, 0), (159,
    1)]."""
    d = make_session(tmp, path, six(pred)[:1], scripts)
    run = O.O7.read_session(d, pred, stock=stock)[0]
    h = O.O7.history(run, pred)
    got = {t: [(k.donor, k.value) for k in h.get(t, [])] for t in ("Global.Byte[13]", "Global.Byte[208]")}
    ok = got == {"Global.Byte[13]": [(154, 0), (158, 1), (158, 2), (158, 3), (159, 0), (160, 1), (160, 2), (162, 1),
                                     (162, 2), (163, 1), (163, 2)],
                 "Global.Byte[208]": [(159, 0), (159, 1)]}
    return ok, str(got)


def _run(rows, log, side="S", i=1, pre=()):
    return {"side": side, "i": i, "rows": rows, "log": log, "pre": list(pre)}


def _base_run(pred: dict, side: str = "S", events=None, log_edit=None) -> dict:
    """A covered run's ``rows`` (cut at its start and end places) and its standard ``log``, pure."""
    members = members_of(pred)
    m = members if side == "F" else {}
    ev = events if events is not None else base_events()
    rows = _rows(ev, side, members)
    kept, _at, pre = ST.cut_at_start(rows, 154, m)
    kept, end = ST.cut_at_end(kept, [164], m)
    log, ctx = standard_log(pred, side, render(ev, side, members))
    if log_edit is not None:
        log = log_edit(log, ctx) or log
    return {"side": side, "i": 1 if side == "S" else 2, "rows": kept, "log": log, "pre": pre, "cut": end,
            "cut_row": next((x for x in rows if x.line == end), None)}


def unit_visit_windows(pred: dict) -> tuple:
    """WALK (c)'s windows (5.3; claim review #4), pure: ONE per visit -- 154's from the walk's frame0 to the cross's loss
    (both steps and the gap between them), a ``walk`` row ending at its ``frame``; 159's with the monologue's gap (the
    interrupted row's loss to the re-run's frame0, its three sites); each cross's door (sid, 2) exempt. Then O7-WALK (c)
    PASSES the base and FAILS a row in 154's gap, a row mid-walk, 158 ip445 inside 158's window, and ip672 past the gap;
    a door's own tag-2 row inside the window PASSES."""
    base = _base_run(pred)
    ws = {w_["donor"]: w_ for w_ in O.visit_windows(base["log"], pred)}
    got = {"154": (ws[154]["lo"], ws[154]["hi"], ws[154]["doors"]) == (F_W0, F_LOST[154], [(8, 2)]),
           "159-gap": [(g["lo"], g["hi"]) for g in ws[159]["gaps"]] == [(F_INT_LOST, F_X0[159])]
           and ws[159]["gaps"][0]["sites"] == [(159, 16, 1, 613), (159, 16, 1, 648), (159, 16, 1, 672)],
           "walk-ends-at-frame": O._row_end({"kind": "walk", "frame": 77, "lost": {"frame": 5, "field": 1},
                                             "field": 1}) == 77}
    seg = O.O7Segment()

    def walk(events=None, log_edit=None):
        ok, _w, det = seg.walk_check([_base_run(pred, events=events, log_edit=log_edit)], pred)
        return ok, det
    got["pass"] = walk()[0] is True
    for name, ev, clause in (
            ("gap-154", edit_nth(base_events(), I204_154, 0, lambda x: with_opt(x, f=F_W1 + 50)), "visit 1's window"),
            ("mid-walk", edit_nth(base_events(), I204_154, 0, lambda x: with_opt(x, f=F_W0 + 500)), "visit 1's window"),
            ("158-ip445", edit_nth(base_events(), B13_158, 0, lambda x: with_opt(x, f=F_X0[158] + 20)),
             "visit 2's window"),
            ("past-gap", edit_nth(base_events(), M672, 0, lambda x: with_opt(x, f=F_X0[159] + 20)), "outside its gap")):
        ok, det = walk(ev)
        got[name] = ok is False and "(c)" in det and clause in det
    door = edit_nth(base_events(), E2_158, 0, lambda x: with_opt(x, f=F_LOST[158] - 10))
    got["door-row-exempt"] = walk(door)[0] is True
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_walk_check(pred: dict) -> tuple:
    """O7-WALK, pure, every clause: the base PASSES on S and on F; (a) a missing step, a short walk, no control, a cross
    landed elsewhere; (b) no interruption, two, one inside the box; (d) no check, a 30-degree check, a "cached" first
    row -- each FAILS by its clause. On F, (b)'s loss read at 31251 PASSES, at 159 FAILS."""
    seg = O.O7Segment()

    def walk(side="S", log_edit=None):
        ok, _w, det = seg.walk_check([_base_run(pred, side, log_edit=log_edit)], pred)
        return ok, det
    got = {"pass-S": walk()[0] is True, "pass-F": walk("F")[0] is True}
    for name, fn, clause in (
            ("no-step", lambda lg, c: [x for x in lg if x is not c["steps"][(154, 0, 1)]], "(a)"),
            ("short", _edit_log(lambda c: c["steps"][(154, 0, 1)]["to"].update(z=-800.0)), "from the goal"),
            ("no-control", _edit_log(lambda c: c["steps"][(154, 0, 1)]["to"].update(control=False)), "without control"),
            ("landed", _edit_log(lambda c: c["steps"][(158, 0, 1)].update(landed=155)), "landed 155"),
            ("no-interrupt", lambda lg, c: [x for x in lg if x is not c["steps"][(159, 0, 1)]], "(b)"),
            ("inside-box", _edit_log(lambda c: c["steps"][(159, 0, 1)]["lost"].update(x=7.0, z=3870.0)),
             "outside the test"),
            ("no-check", _edit_log(lambda c: c["steps"][(160, 0, 1)]["route"].pop("basis_check")), "(d)"),
            ("30deg", _edit_log(lambda c: c["steps"][(160, 0, 1)]["route"]["basis_check"].update(angle=30.0)), "(d)"),
            ("cached", _edit_log(lambda c: c["steps"][(162, 0, 1)]["route"].update(basis="cached")), "basis 'cached'")):
        ok, det = walk(log_edit=fn)
        got[name] = ok is False and clause in det
    ok, det = walk("F", log_edit=_edit_log(lambda c: c["steps"][(159, 0, 1)]["lost"].update(field=159)))
    got["f-loss-at-159"] = ok is False and "(b)" in det
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_landing_check(pred: dict) -> tuple:
    """O7-LANDING, pure, every clause: the base PASSES on S and F; (a) a row of 158 at REAL 158 on F; (b) 160's chain
    row missing, a harness row after 158's exit; (c) a harness row after 163's exit, the end row naming real 164 on F;
    (d) the cut row in real 164 on F -- each FAILS naming its clause. LANDING (e) ALONE: a covered F run whose digest
    carries one seam and nothing else."""
    from types import SimpleNamespace
    seg = O.O7Segment()
    members = members_of(pred)

    def land(side="S", events=None, end_field=None):
        r_ = _base_run(pred, side, events=events)
        r_["log"].append({"k": "end", "field": end_field or ST.side_ends(pred, side)[0]})
        r_["digest"] = SimpleNamespace(seams=[], seam_keys={})
        ok, _w, det = seg.landing_check({"S": [r_] if side == "S" else [], "F": [r_] if side == "F" else []}, pred)
        return ok, det
    got = {"pass-S": land()[0] is True, "pass-F": land("F")[0] is True}
    for name, side, ev, end_f, clause in (
            ("a", "F", edit(base_events(), lambda x: x[0] == "w" and x[1] == 158, lambda x: with_opt(x, fld=158)),
             None, "(a)"),
            ("b-chain", "S", drop_nth(base_events(), CH160), None, "(b)"),
            ("b-harness", "S", after(base_events(), CH158, w((158, -1, -1, -1, "Global.Byte[300]", 9), src="harness")),
             None, "(b)"),
            ("c-harness", "S", after(base_events(), CH163, w((163, -1, -1, -1, "Global.Byte[300]", 9), src="harness")),
             None, "(c)"),
            ("c-end-row", "F", None, 164, "(c)"),
            ("d", "F", edit(base_events(), lambda x: _is(x, END164), lambda x: with_opt(x, fld=164, don=164)), None,
             "(d)")):
        ok, det = land(side, ev, end_f)
        got[name] = ok is False and clause in det
    r_ = _base_run(pred, "F")
    r_["log"].append({"k": "end", "field": 31256})
    seam = SimpleNamespace(origin="31255 -> 165", to=165, frm=31255, fields=[31255, 165])
    r_["digest"] = SimpleNamespace(seams=[seam], seam_keys={})
    ok, _w, det = seg.landing_check({"S": [], "F": [r_]}, pred)
    got["e-alone"] = ok is False and "(e)" in det and not any(f"({c})" in det for c in "abcd")
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_state_c_by_place(pred: dict, stock, scripts: dict, tmp: Path, path: Path) -> tuple:
    """O7-STATE (c) BY PLACE (claim review #9), on a session's own reading: an F run's last pre-cut Byte[13] row 163 e0
    t0 ip684 at fld 31255 matches the registered site (place 163, member(163)'s field); the same row renumbered to fld
    163 does not (on F, fld 163 is real 163, no member's); on S at real 163 it does."""
    real = lambda ev, n: edit(ev, lambda x: _is(x, B13_163), lambda x: with_opt(x, fld=163, don=163))  # noqa: E731
    runs = six(pred)[:2] + six(pred, f=real)[1:2]
    rs = O.O7.read_session(make_session(tmp, path, runs, scripts), pred, stock=stock)

    def c(r_):
        ok, _w, det = O.O7.state_check([r_], pred)
        return ok, det
    got = {"s-163": c(rs[0])[0] is True, "member-31255": c(rs[1])[0] is True}
    ok, det = c(rs[2])
    got["renumbered-163"] = ok is False and "(c)" in det and "at fld 163" in det
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


class _St:
    """A published state for the static watch: ``frame`` and ``objects``."""

    def __init__(self, frame, objects):
        self.frame, self.objects = frame, objects


def unit_static_watch(pred: dict) -> tuple:
    """The static watch (4.11; claim review #6), keyed by PLACE: member(154) 31246 on F reads as 154; one ``seen`` row a
    visit (its first reading), one ``moved`` row on a release (and only one, however long he walks), no row while he
    stays within ``tol``; a visit with sid 5 unpublished writes none (the report's UNOBSERVED); a second visit its own
    ``seen``."""
    log: list = []
    obs = O.static_watch(pred, log)
    me = {"sid": 5, "x": -2700.0, "z": -1700.0}
    for f, x in ((10, -2700.0), (11, -2690.0), (12, -2600.0), (13, -2500.0), (14, -2400.0)):
        obs(_St(f, [dict(me, x=x)]), {"field": 31246, "donor": 154})
    obs(_St(15, [{"sid": 6, "x": 0.0, "z": 0.0}]), {"field": 31250, "donor": 158})
    obs(_St(16, []), {"field": 31246, "donor": 154})
    obs(_St(17, None), {"field": 31246, "donor": 154})
    rows = [(x["what"], x["visit"], x["frame"], x["donor"]) for x in log]
    log2: list = []
    obs2 = O.static_watch(pred, log2)
    obs2(_St(1, []), {"field": 154, "donor": 154})
    got = {"rows": rows == [("seen", 1, 10, 154), ("moved", 1, 12, 154)],
           "unobserved": log2 == [] and [o for o, v, s, m in O.static_lines([{"k": "visit", "donor": 154, "visit": 1}],
                                                                             pred) if s is None] != []}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or f"all as registered: {rows}")


def unit_seeded_fields(pred: dict) -> tuple:
    """seeded_fields (0.2 #20): 154, 158, 160, 162, 163 and 31246, 31250, 31252, 31254, 31255 -- never 159 or 31251."""
    got = O.seeded_fields(pred)
    return got == [154, 158, 160, 162, 163, 31246, 31250, 31252, 31254, 31255], str(got)


def unit_monologue_test(pred: dict) -> tuple:
    """monologue_test (0.2 #10): off ip390's pinned text {any_of x_lt -1600, x_gt 1600, z_lt 800; unless_bit 3796}; a
    mutated constant (63936 -> 63900) changes it (x_lt -1636); another shape (ip14's) None. test_holds widened by 180:
    (-1601, 1572) holds, (7, 3870) does not."""
    text = O.pin_text(pred, [159, 16, 1, 390])
    t = O.monologue_test(text)
    got = {"read": t == {"any_of": {"x_lt": -1600, "x_gt": 1600, "z_lt": 800}, "unless_bit": 3796},
           "mutated": (O.monologue_test(text.replace("63936", "63900")) or {}).get("any_of", {}).get("x_lt") == -1636,
           "other-shape": O.monologue_test(O.pin_text(pred, [159, 0, 0, 290])) is None,
           "holds": O.test_holds(t, -1601, 1572, 180.0) and not O.test_holds(t, 7, 3870, 180.0)}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or f"all as registered: {t}")


def unit_monologue_lines(pred: dict) -> tuple:
    """THE --analyse REPORT'S MONOLOGUE LINE (5.4; the review's finding: its page filter was any() over an empty tuple,
    so no page ever printed) on a base run's standard log: the five outcome pages (:data:`MONO_PAGES`) print on it --
    296's "What!?" first, 300's "I must hurry!" last; a run whose only page is the stop page prints that NONE of its
    registered pages was listed; a run stopped after 298 prints the three it listed (from 296, to its last page)."""
    log, _ctx = standard_log(pred, "S", render(base_events(tuple(pred["route"]), int(pred["end_field"])), "S", {}))

    def line(pages):
        return " | ".join(O.O7._monologue_lines({"side": "S", "i": 1, "log": log, "rows": [],
                                                 "outcome": {"pages": list(pages)}}, pred))
    full, stop, part = line(MONO_PAGES), line(["Error Env Play()  Slot=1"]), line(MONO_PAGES[:3])
    got = {"full": "its pages (5 of 5) ['What!?', " in full and "'I must hurry!']" in full,
           "none": "none of its pages [296, 297, 298, 299, 300] listed" in stop,
           "part": "its pages (3 of 5) ['What!?', " in part and "I must hurry" not in part,
           "pure": O.monologue_pages(["Error Env Play()  Slot=1", *MONO_PAGES, "a later page"], pred,
                                     pred["interruptions"][0]) == list(MONO_PAGES)}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or full[full.find("; its pages"):][:150])


def unit_dojebon_test(pred: dict) -> tuple:
    """dojebon_test (0.2 #11): (3600, Map.Byte[30] == 1) off 154 e5 t1 ip263's pinned text; 3600 -> 3000 reads 3000;
    another shape None. The release height -500 off e11 t1 ip128, Dojebon's placement (-2700, -1700) off e5 t0."""
    text = O.pin_text(pred, [154, 5, 1, 263])
    pins = pred["route_pins"]
    got = {"read": O.dojebon_test(text) == {"within": 3600, "latch": "Map.Byte[30] == 1"},
           "mutated": (O.dojebon_test(text.replace("3600", "3000")) or {}).get("within") == 3000,
           "other": O.dojebon_test(O.pin_text(pred, [154, 11, 1, 33])) is None,
           "release": O.release_height(pins, 154) == -500.0,
           "placement": O.placement_of(pins, 154, 5) == (-2700.0, -1700.0)}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_why_void(pred: dict, stock, scripts: dict, tmp: Path, path: Path) -> tuple:
    """A-START (5.1), on a session's own reading: an S run stopped at 154's error path (ip101) holds A-START; an F run
    stopped at 158's (ip97) none; a run whose 159 ip290 reads old 0 holds A-START on S and on F, with 125 none -- and with
    an earlier Byte[8] row of its own (EXPLAINED) none."""
    runs = six(pred)[:2]
    ev = drop_nth(runs[0]["events"], I123_154)
    _void(runs[0], "V5", [154, 1190, 1], "driver", "a stop page", events=upto_nth(ev, I61_154, 0, w(ERR154_101),
                                                                                    e("off", 154)), log=_log_upto(154))
    ev = drop_nth(runs[1]["events"], PRO[158][3])
    _void(runs[1], "V5", [158, 1190, 2], "game", "a stop page", events=upto_nth(ev, I57_158, 0, w(ERR158_97),
                                                                                  e("off", 158)), log=_log_upto(158))
    zero = lambda ev, n: edit_nth(ev, B8_159, 0, lambda x: with_opt(x, old=0))     # noqa: E731
    reads = six(pred, s=zero, f=zero)[:2]
    explained = six(pred, s=lambda ev, n: after(ev, B13_158, r(158, 8, 125, 0)))[:1]
    rs = O.O7.read_session(make_session(tmp, path, runs + reads + explained + six(pred)[:1], scripts), pred,
                           stock=stock)
    cls = [{v["class"] for v in r_["void"]} for r_ in rs]
    got = {"start-154": "A-START" in cls[0], "none-158": "A-START" not in cls[1],
           "byte8-S": "A-START" in cls[2], "byte8-F": "A-START" in cls[3], "explained": "A-START" not in cls[4],
           "125": rs[5]["covered"] and not rs[5]["void"]}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def as_if_frozen(pred: dict) -> dict:
    """The predictions as the lead's freeze would leave them (research/o7_design.md 8; G39): every budget x1.5
    (rounded), ``rehearsals`` two R-FULL run dirs, ``rehearsal_fps`` the rates they met, each table step's ``start``
    moved 20 u east -- nothing else changed."""
    p = copy.deepcopy(pred)
    p["budget"] = {k: (v if v is None else int(round(v * 1.5)) if isinstance(v, int) and not isinstance(v, bool)
                       else round(float(v) * 1.5, 2)) for k, v in p["budget"].items()}
    p["rehearsals"] = ["20261006-000001-o7-rh", "20261006-000002-o7-rh-stair"]
    p["rehearsal_fps"] = [31.0, 60.0]
    for c in p["table"]:
        for s in c["steps"]:
            if s.get("start") is not None:
                s["start"] = [s["start"][0] + 20, s["start"][1]]
    return p


def unit_as_if_frozen(draft: dict) -> tuple:
    """:func:`as_if_frozen` of the DRAFT changes ``budget``, ``rehearsals``, ``rehearsal_fps`` and ``table`` (the steps'
    starts) and nothing else, and the freeze's refusals read it clean (its engine the draft's, as a live one) where they
    refuse the draft while it names no rehearsals."""
    p = as_if_frozen(draft)
    changed = sorted(k for k in set(p) | set(draft) if p.get(k) != draft.get(k))
    probs = O.O7.freeze_problems(p, live_engine=dict(draft["engine"]))
    starts = all(s2.get("start") == ([s1["start"][0] + 20, s1["start"][1]] if s1.get("start") is not None else None)
                 for c1, c2 in zip(draft["table"], p["table"]) for s1, s2 in zip(c1["steps"], c2["steps"]))
    got = {"changed": changed == ["budget", "rehearsal_fps", "rehearsals", "table"], "starts": starts,
           "freezable": probs == [],
           "draft-not": bool(O.O7.freeze_problems(draft, live_engine=dict(draft["engine"])))
           == (not draft.get("rehearsals"))}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or f"all as registered: {changed}") \
        + ("" if not probs else f" {probs[:2]}")


def unit_fallback_end(stock, scripts: dict, tmp: Path) -> tuple:
    """THE ONE SWITCH (4.17): the draft at ``end`` 163 -- route and visits [154, 158, 159, 160, 162], end_fields [163],
    side_ends {S: [163], F: [31255]}, the end row 163 e0 t0 ip22, every list filtered to the route's places, the end
    state recomputed (Int16[2] 341; Byte[13] from 162 ip932) -- reads O7-KEYS, -CENSUS, -REGIONS and -GOALS PASS and a
    null pair PROVEN: the fallback proven before any rehearsal."""
    pred = O.draft_predictions(end=163)
    got = {"route": pred["route"] == [154, 158, 159, 160, 162] and pred["end_fields"] == [163],
           "side-ends": pred["side_ends"] == {"S": [163], "F": [31255]},
           "end-row": (pred["landing"]["end_row"]["place"], pred["landing"]["end_row"]["ip"]) == (163, 22),
           "lists": all(k["donor"] in pred["route"] for name in ("writes", "chain", "error_path", "forbidden_sites",
                                                                  "dead") for k in pred[name])
           and all(k.split(".")[0] != "163" for k in pred["regions"]) and len(pred["table"]) == 5,
           "end-state": pred["end_state"].get("Global.Int16[2]") == 341
           and pred["end_state_trace"]["Global.Byte[13]"]["site"] == {"place": 162, "sid": 0, "tag": 0, "ip": 932}}
    for check in (O.O7.keys_check(pred, stock), O.O7.census_check(pred, stock), O.O7.regions_check(pred, stock),
                  O.O7.goals_check(pred, stock=stock)):
        got[check[1].split(":")[0]] = check[0] is True
    path = tmp / "o7_fallback.json"
    path.write_bytes((json.dumps(pred, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    sdir = tmp / "fallback-sessions"
    sdir.mkdir(exist_ok=True)
    d = make_session(sdir, path, six(pred), scripts)
    checks, _rep = O.O7.analyse(d, stock=stock)
    got["null-pair"] = verdict(checks) == "PROVEN"
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered") \
        + ("" if got["null-pair"] else " " + "; ".join(f"{w_}: {d_[:90]}" for ok, w_, d_ in checks if ok is not True))


def unit_closures154() -> tuple:
    """closures154 (2.4): the derivation from the definitions on stock 154's open triangles equals the typed lists (119
    and 134); the 2% shrink dropped -- shared edges then count as overlaps -- gives another step-0 list."""
    from ff9mapkit import extract
    raw = extract.stock_walkmesh(154)
    a, b = O.closures154(raw)
    got = {"step0": list(a) == list(O.CLOSURES154[0]) and len(a) == 119,
           "step1": list(b) == list(O.CLOSURES154[1]) and len(b) == 134}
    from ff9mapkit.content import pathfind
    pw = pathfind.PlayerWalkmesh(raw)
    wv, tris = raw.world_verts(), raw.tris
    live = [i for i in range(len(tris)) if i not in pw.closed]
    cent = {i: tuple(sum(wv[k][d] for k in tris[i].vtx) / 3 for d in range(3)) for i in live}
    ground = [i for i in live if cent[i][1] > -150]
    upper = [i for i in live if cent[i][1] <= -150]
    flat = {i: [(wv[k][0], wv[k][2]) for k in tris[i].vtx] for i in live}
    unshrunk = sorted({t for t in ground if any(O._convex_overlap(flat[t], flat[u], touch=True) for u in upper)}
                      | {u for u in upper if cent[u][0] > 450 and cent[u][2] > -3250})
    got["unshrunk-differs"] = unshrunk != list(a)
    return all(got.values()), str({k: v for k, v in got.items() if not v} or f"all as registered: {len(a)}, {len(b)}")


def unit_carried(pred: dict) -> tuple:
    """THE CARRIED VALUES, derived (4.5; 0.2 #18) over the repo's six frozen files: the fourteen, no segment disagreeing
    with its own end_state, equal to the draft's typed ones; UInt16[19] 1807 composed from O6's start-dependent
    ``after.old`` 1799 (O1's frozen v4 registers no bit of it), never from absent O1 bits; a frozen O6 with that
    ``after.old`` dropped gives 10 (2 | 8), not 1807."""
    segs = O.prior_segments()
    derived, problems = O.carried_from_segments(segs, writes=O.o7_targets(pred))
    want = pred["carried"]["values"]
    o6 = copy.deepcopy(segs[-1][1])
    for k in o6["start_dependent"]:
        if k["target"] == "Global.UInt16[19]":
            k["after"].pop("old")
    alt, _p = O.carried_from_segments(segs[:-1] + [(segs[-1][0], o6)], writes=O.o7_targets(pred))
    got = {"fourteen": derived == want and len(derived) == 14, "no-disagreement": problems == [],
           "uint19": derived.get("Global.UInt16[19]") == [0, 1807],
           "no-after-old": alt.get("Global.UInt16[19]") == [0, 10]}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


_LOG_HEAD = "05.10.2026 19:27:42 |M| [WindowManager] Moving window to (2045,33)\n"
_LOG_351 = ("05.10.2026 19:27:44 |W| [DataPatchers] ForkDonorPatch: donor field 351 is forked by both 30831 and 30842 "
            "-> remap DISABLED (ambiguous)\n")
_LOG_DONE = "05.10.2026 19:27:44 |M| [DataPatchers] Initialized\n"


def unit_p_donor_log() -> tuple:
    """P-DONOR-LOG over the seven route donors (O5's unit, O7's donors): today's shape PASS; 160 forked twice FAIL naming
    it; no "Initialized" FAIL."""
    a = P.p_donor_log(_LOG_HEAD + _LOG_351 + _LOG_DONE, O.ROUTE_DONORS)
    w160 = _LOG_351.replace("351", "160").replace("30831 and 30842", "31252 and 31299")
    b = P.p_donor_log(_LOG_HEAD + _LOG_351 + w160 + _LOG_DONE, O.ROUTE_DONORS)
    c = P.p_donor_log(_LOG_HEAD + _LOG_351, O.ROUTE_DONORS)
    ok = a[0] and not b[0] and "donor field 160 is forked by both 31252 and 31299" in b[1] and not c[0]
    return ok, f"today {a[0]}; 160 twice {b[0]}; no Initialized {c[0]}"


def unit_p_launch(tmp: Path) -> tuple:
    """P-LAUNCH with the engine (O5's unit, O7's ForkDonorPatch rows): older PASS; ForkDonorPatch.txt touched after the
    launch FAIL ("relaunch"); an engine DLL touched after it FAIL; another live engine FAIL; no stamp FAIL."""
    launched = P.launch_time(_LOG_HEAD + _LOG_DONE)
    game = tmp / "plaunch7"
    root = game / "FF9CustomMap"
    root.mkdir(parents=True)
    old = _dt.datetime(2026, 10, 5, 19, 27, 4)
    files = {game / "Memoria.ini": "[Battle]\nSpeed = 5\n", root / "DictionaryPatch.txt": "FieldScene 31246 11 X X 3\n",
             root / "ForkDonorPatch.txt": "31246 154\n31250 158\n31251 159\n"}
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
    dll = game / "x86" / "FF9_Data" / "Managed" / "Assembly-CSharp.dll"
    D4._touch(dll, _dt.datetime(2026, 10, 5, 19, 28))
    ok, d = check()
    got["dll-after"] = (not ok) and "Assembly-CSharp.dll" in d and "relaunch" in d
    D4._touch(dll, old)
    got["other-engine"] = not check(live={"x64": "6" * 64, "x86": "6" * 64})[0]
    got["no-stamp"] = not check(stamp=None)[0]
    got["older-again"] = check()[0]
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_p_settings(tmp: Path) -> tuple:
    """P-SETTINGS on O7's 31 keys (4.13): an ini equal to them PASS; [AnalogControl] UseAbsoluteOrientation 1 FAILS
    (keys would read operand 0: another basis); [Control] PSXMovementMethod 0 FAILS (the slope-scaled run the budgets and
    walks rest on); [AnalogControl] missing FAILS."""
    want = O.SETTINGS
    game = tmp / "psettings7"
    game.mkdir()

    def judge(settings):
        lines = []
        for sec, kv in settings.items():
            lines += [f"[{sec}]"] + [f"{k} = {v}" for k, v in kv.items()] + [""]
        (game / "Memoria.ini").write_text("\n".join(lines), encoding="utf-8")
        return P.p_settings(want, P.install_settings(game, [], want))

    def one(sec, key, value):
        s = json.loads(json.dumps(want))
        s[sec][key] = value
        ok, detail = judge(s)
        return (not ok) and f"[{sec}] {key} = '{value}'" in detail
    gone = {k: v for k, v in json.loads(json.dumps(want)).items() if k != "AnalogControl"}
    got = {"equal": judge(want)[0] and sum(len(v) for v in want.values()) == 31,
           "orientation-1": one("AnalogControl", "UseAbsoluteOrientation", "1"),
           "psx-0": one("Control", "PSXMovementMethod", "0"), "analog-gone": not judge(gone)[0]}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def units(pred: dict, stock, scripts: dict, sdir: Path, path: Path, tmp: Path) -> list:
    """Every single unit, in order: ``[(name, fn)]``, each ``fn()`` -> ``(ok, detail)``."""
    return [("step-of-walk", lambda: unit_step_of_walk(pred)),
            ("walk-kw", lambda: unit_walk_kw(pred)),
            ("instanced-at7", lambda: unit_instanced_at7(stock)),
            ("render", lambda: unit_render(pred, tmp)),
            ("pattern", lambda: unit_pattern(pred, stock, tmp)),
            ("trace-summary", lambda: unit_trace_summary(pred, stock)),
            ("state-history", lambda: unit_state_history(pred, stock, scripts, sdir, path)),
            ("visit-windows", lambda: unit_visit_windows(pred)),
            ("walk-check", lambda: unit_walk_check(pred)),
            ("landing-check", lambda: unit_landing_check(pred)),
            ("state-c-by-place", lambda: unit_state_c_by_place(pred, stock, scripts, sdir, path)),
            ("static-watch", lambda: unit_static_watch(pred)),
            ("seeded-fields", lambda: unit_seeded_fields(pred)),
            ("monologue-test", lambda: unit_monologue_test(pred)),
            ("monologue-lines", lambda: unit_monologue_lines(pred)),
            ("dojebon-test", lambda: unit_dojebon_test(pred)),
            ("why-void", lambda: unit_why_void(pred, stock, scripts, sdir, path)),
            ("as-if-frozen", lambda: unit_as_if_frozen(O.draft_predictions())),
            ("fallback-end", lambda: unit_fallback_end(stock, scripts, tmp)),
            ("closures154", unit_closures154),
            ("carried-derivation", lambda: unit_carried(pred)),
            ("p-donor-log", unit_p_donor_log),
            ("p-launch", lambda: unit_p_launch(tmp)),
            ("p-settings", lambda: unit_p_settings(tmp)),
            ("p-pad", D4.unit_p_pad),
            ("p-override", D4.unit_p_override),
            ("p-engine", D4.unit_p_engine),
            ("text-strict", D4.unit_text_strict),
            ("input-witness", D4.unit_input_witness)]


# ======================================================================== the listed units (offline checks' mutants)
CENSUS_LINE = ("154: 22 (writes 4, chain 1, masked 2, error 4, forbidden 6, dead 4, inert 1); 158: 18 (writes 6, chain 1, "
               "masked 2, error 4, forbidden 2, dead 3, inert 0); 159: 22 (writes 8, chain 1, masked 2, error 4, "
               "forbidden 4, dead 3, inert 0); 160: 24 (writes 5, chain 1, masked 2, error 4, forbidden 8, dead 4, inert "
               "0); 162: 18 (writes 5, chain 1, masked 2, error 4, forbidden 1, dead 5, inert 0); 163: 18 (writes 5, "
               "chain 1, masked 2, error 4, forbidden 1, dead 5, inert 0); 0 unresolved; inert 154 e2 not instanced at "
               "315; 158, 159, 160, 162, 163 hold no entrance dispatch (every Init reachable; 160's Bit[3799]-gated "
               "InitObject(2) instanced); no shared script instanced on the route")


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


def _drop(name, test):
    def mutate(p):
        p[name] = [k for k in p[name] if not test(k)]
    return mutate


def unit_store_census(pred: dict, stock) -> list:
    """O7-CENSUS on the install PASSES with 6.1's line; each mutant FAILS by name: 154 e2 registered NOT inert (its
    ip1520 store in no list); 160 e2 registered inert (instanced by the flag-gated InitObject); 159 ip672 removed from the
    writes; 162 e2 ip199 removed from ``dead``; 154 ip101 removed from ``error_path``."""
    return _check_mutants("store-census", lambda p: O.O7.census_check(p, stock), pred, lambda d: d == CENSUS_LINE, [
        ("census-154-e2-not-inert", lambda p: p.__setitem__("inert", []), "154 e2 t1 ip1520 Global.Int16[2]: in no list"),
        ("census-160-e2-inert", lambda p: p["inert"].append({"donor": 160, "sid": 2, "tags": "*", "why": "a mutant"}),
         "inert entry 2 of 160 is instanced at entrance 332"),
        ("census-159-672", _drop("writes", lambda k: (k["donor"], k["ip"]) == (159, 672)),
         "159 e16 t1 ip672 Global.Bit[3796]: in no list"),
        ("census-162-e2-199", _drop("dead", lambda k: (k["donor"], k["sid"], k["ip"]) == (162, 2, 199)),
         "162 e2 t2 ip199 Global.Byte[13]: in no list"),
        ("census-154-101", _drop("error_path", lambda k: (k["donor"], k["ip"]) == (154, 101)),
         "154 e0 t0 ip101 Global.Byte[13]: in no list")])


REGIONS_LINE = ("15 regions (14 exit -- 3 with their balcony branches (154.e10, 154.e8, 154.e9) -- 1 hazard: "
                "154.hazard.dojebon guarding 154 e5's wait, in (154, 1190, 1) step 0's avoid), 0 hot-spots, 17 gateway "
                "rows all registered")


def unit_regions(pred: dict, stock) -> list:
    """O7-REGIONS on the install PASSES with 6.1's line; each mutant FAILS naming its clause: 154.e8 without its balcony
    branch; the hazard under an ``e<sid>`` key; the hazard with role exit; the hazard out of step 0's avoid; 159.e11
    missing; 160.e5's points shifted."""
    def rekey(p):
        p["regions"]["154.e99"] = p["regions"].pop("154.hazard.dojebon")

    def shift(p):
        p["regions"]["160.e5"]["points"][0][0] += 10

    def out_of_avoid(p):
        s = p["table"][0]["steps"][0]
        s["avoid"] = [k for k in s["avoid"] if k != "154.hazard.dojebon"]
    return _check_mutants("regions", lambda p: O.O7.regions_check(p, stock), pred, lambda d: d == REGIONS_LINE, [
        ("regions-e8-no-branch", lambda p: p["regions"]["154.e8"].pop("branches"), "154.e8: scan_gateways gives"),
        ("regions-hazard-e-key", rekey, "154.e99: a hazard's key is <donor>.hazard.<name>"),
        ("regions-hazard-exit", lambda p: p["regions"]["154.hazard.dojebon"].__setitem__("role", "exit"),
         "154.hazard.dojebon: an exit's key is <donor>.e<sid>"),
        ("regions-hazard-avoid", out_of_avoid, "154.hazard.dojebon: not in the avoid of (154, 1190, 1) step 0"),
        ("regions-159-e11", lambda p: p["regions"].pop("159.e11"), "159.e11: a gateway"),
        ("regions-160-e5-points", shift, "160.e5: the bytes' first SetRegion is")])


def goals_lines(pred: dict) -> tuple:
    """6.1's O7-GOALS lines, as substrings of the detail: those no step's ``start`` moves (the goals' walls and depths,
    (g1), (g3), (g4), (h2)-(h4): the bytes', pinned) and those it does RENDERED from the predictions given ((g5)'s start;
    (h1) under its bound) -- the lead's freeze may move a start (F1), so no start-dependent number is pinned."""
    s159 = pred["table"][2]["steps"][0]["start"]
    return ("(154, 1190, 1) #0 walk wall 870 route ", "(154, 1190, 1) #1 cross wall 1328 depth 420 route ",
            "(158, 1190, 2) #0 cross wall 681 depth 780 route ", "(159, 1190, 3) #0 cross wall 291 depth 582 route ",
            "(160, 1190, 4) #0 cross wall 196 depth 247 route ", "(162, 1190, 5) #0 cross wall 235 depth 264 route ",
            "(163, 1190, 6) #0 cross wall 165 depth 191 route ", "u at 110",
            "(154, 1190, 1) #0 (h1) ", " <= 3420", "(154, 1190, 1) #0 (h2) basis prior",
            "(154, 1190, 1) #0 (h3) the hazard avoided",
            "(154, 1190, 1) #0 (h4) the release zone (5976 points) covered but 3 residual point(s) (x 64..80, z "
            "-4016..-4000), largest gap 70.0 <= 86",
            "(154, 1190, 1) #1 (g4) 18 open tris of its floor touch 154.e8, all ground",
            f"(159, 1190, 3) #0 (g5) the test fails at ({float(s159[0]):.0f}, {float(s159[1]):.0f}), holds at "
            f"159.e11's 4 vertices",
            "(163, 1190, 6) #0 (g1) no route at 120, its 110 the plan",
            "(154, 1190, 1) #0 (g3) the goal disc (253 points) single-level ground (PSX y > -100), inside #1's floor")


def unit_goals(pred: dict, stock) -> list:
    """O7-GOALS on the install PASSES with 6.1's lines; each mutant FAILS by its clause: 163 at clearance 120 (no route at
    120); 160 at 110 ((g1): a route exists at 120); 158 without e1 in ``avoid`` ((g2)); 154 #0's goal (0, -3700) on the
    balcony ((g3)); 154 #1 without its closures ((g4): balcony tris inside e8); 159's ``test`` x_lt -3600 ((g5): e11
    outside it); 154 #0 without ``basis`` ((h2)); without the hazard ((h3)); its goal pulling the route east past the
    circle on the balcony ((h1)); the hazard shifted 50 u east ((h4): gap 104 > 86); its north edge 300 u south ((h4))."""
    def step(c, n, **kw):
        def fn(p):
            s = p["table"][c]["steps"][n]
            for k, v in kw.items():
                if v is ...:
                    s.pop(k, None)
                else:
                    s[k] = v
        return fn

    def no_hazard(p):
        s = p["table"][0]["steps"][0]
        s["avoid"] = [k for k in s["avoid"] if k != "154.hazard.dojebon"]

    def shift_east(p):
        for pt in p["regions"]["154.hazard.dojebon"]["points"]:
            pt[0] += 50

    def north_south(p):
        for pt in p["regions"]["154.hazard.dojebon"]["points"]:
            if pt[1] == -2950:
                pt[1] = -3250
    return _check_mutants("goals", lambda p: O.O7.goals_check(p, stock=stock), pred,
                          lambda d: all(x in d for x in goals_lines(pred)), [
        ("goals-163-at-120", step(5, 0, clearance=120), "(163, 1190, 6) #0: no route from"),
        ("goals-160-at-110", step(3, 0, clearance=110), "(160, 1190, 4) #0 (g1): clearance 110 under the engine radius"),
        ("goals-158-e1", step(1, 0, avoid=[]), "(158, 1190, 2) #0 (g2): the registered exit(s) ['158.e1']"),
        ("goals-154-balcony-goal", step(0, 0, goal=[0, -3700]), "(154, 1190, 1) #0 (g3)"),
        ("goals-154-no-closures", step(0, 1, closed_tris=[]), "(154, 1190, 1) #1 (g4)"),
        ("goals-159-test", lambda p: p["interruptions"][0]["test"]["any_of"].__setitem__("x_lt", -3600),
         "(159, 1190, 3) #0 (g5)"),
        ("goals-154-no-basis", step(0, 0, basis=...), "(154, 1190, 1) #0 (h2)"),
        ("goals-154-no-hazard", no_hazard, "(154, 1190, 1) #0 (h3)"),
        ("goals-154-east", step(0, 0, goal=[90, -4000]), "(154, 1190, 1) #0 (h1)"),
        ("goals-hazard-east", shift_east, "(154, 1190, 1) #0 (h4)"),
        ("goals-hazard-north", north_south, "(154, 1190, 1) #0 (h4)")])


def unit_route_pins(pred: dict, stock) -> list:
    """O7-KEYS (f), THE ROUTE PINS and their scans (4.14), and O7-TEXT's route_mes, on the install PASS; each mutant
    FAILS by its clause: 154 e8 t2 ip38's constant; 159 e16 t1 ip390's; a second DefinePlayerCharacter in an instanced
    entry; a party op; a Map.Bit[144] store; mes 300 without its text; field 70 e0 t0 ip249's constant."""
    mes = D5.block3_us()
    out = []
    ok, detail = O.O7.route_pins_check(pred, stock)
    n = len(pred["route_pins"])
    out.append(("route-pins", ok is True and detail.startswith(f"{n} route pins equal; per field one "
                                                                "DefinePlayerCharacter instanced"), detail[:150]))
    for name, site, old, new in (("route-pins-e8-ip38", [154, 8, 2, 38], "const(65436)", "const(65435)"),
                                 ("route-pins-ip390", [159, 16, 1, 390], "const(63936)", "const(63935)"),
                                 ("route-pins-70-ip249", [70, 0, 0, 249], "const(125)", "const(124)")):
        p = copy.deepcopy(pred)
        pin = next(x for x in p["route_pins"] if x[:4] == site)
        pin[4] = pin[4].replace(old, new)
        ok, detail = O.O7.route_pins_check(p, stock)
        out.append((name, ok is False and f"{site[0]} e{site[1]} t{site[2]} ip{site[3]}" in detail, detail[:150]))
    base = O.instanced_texts(stock(160), 332)
    for name, extra, clause in (("route-pins-two-players", (9, 0, 999, "DefinePlayerCharacter()"),
                                 "2 DefinePlayerCharacter"),
                                ("route-pins-party-op", (9, 0, 998, "RemoveParty(1)"), "a party op"),
                                ("route-pins-bit144", (5, 2, 997, "SET({Map.Bit[144] const(1) B_LET B_EXPR_END})"),
                                 "a Map.Bit[144] store")):
        ok, detail = O.O7.route_pins_check(pred, stock, scans={160: base + [extra]})
        out.append((name, ok is False and clause in detail, f"{'FAIL' if ok is False else 'PASS'}: {detail[:150]}"))
    mm = dict(mes)
    mm[300] = mm[300].replace("I must hurry!", "I must wait.")
    ok, _w, detail = O.O7.text_check7(pred, mes=mm)
    out.append(("route-mes-300", ok is False and "mes 300 does not hold 'I must hurry!'" in detail, detail[:150]))
    return out


def unit_build_pins(pred: dict, tmp: Path) -> list:
    """O7-BUILD's route pins (O5's unit, :meth:`o5_hallway.O5Segment.build_pins`) on O7's seven route members, a
    synthetic build through a ``stock_lang`` seam: the clean build PASSES ("49 member files ... 20 in-chain Field()
    operands"); each mutant FAILS by its clause: an extra byte changed in member(159) (e16 t1 ip613's statement, jp); an
    in-chain Field() left unremapped (member(163) e2 t2 ip235's Field(164), us)."""
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
    m159 = next(f for f, d in members.items() if d == 159)
    m163 = next(f for f, d in members.items() if d == 163)

    def flip(fid, L, data):
        if fid == m159 and L == "jp":
            ins = instr(159, L, 16, 1, 613)
            data[ins.off + 3] ^= 0x01

    def unremap(fid, L, data):
        if fid == m163 and L == "us":
            ins = instr(163, L, 2, 2, 235)
            assert ins.imm(0) == 164, ins
            data[ins.off + 2:ins.off + 4] = (164).to_bytes(2, "little")
    out = []
    ok, detail = O.O7.build_pins(pred, build("bp7-clean"), stock_lang=stock_lang)
    out.append(("build-pins-clean", ok is True and detail == "the route members' pins hold in 49 member files (7 route "
                                                            "members x 7 languages): the only byte diffs are their 20 "
                                                            "in-chain Field() operands", detail[:150]))
    for name, mutate, clause in (("build-pins-extra-byte", flip, "differ outside the in-chain Field() operands"),
                                 ("build-pins-unremapped", unremap, "left unremapped")):
        ok, detail = O.O7.build_pins(pred, build(name, mutate), stock_lang=stock_lang)
        at_ = detail.find(clause)
        out.append((name, ok is False and at_ >= 0,
                    f"{'FAIL' if ok is False else 'PASS'}: " + (detail[max(0, at_ - 60):at_ + 90] if at_ >= 0
                                                                else detail[:150])))
    return out


def _key(p: dict, name: str, donor: int, ip: int) -> dict:
    return next(k for k in p[name] if (k["donor"], k["ip"]) == (donor, ip))


def _o6_385(p: dict) -> dict:
    """O6's frozen predictions with its 153 Int16[9] tuple's new 385 (the derived after.old 385 against the typed -1)."""
    o6 = copy.deepcopy(O.o6_frozen())
    for v in o6["pattern"]["visits"]:
        for t in v:
            if t[0] == 153 and t[4] == "Global.Int16[9]":
                t[5] = 385
    return o6


def _contradicting() -> list:
    """The six frozen segments with O2's two Int16[469] keys swapped (its &= before its |=): the replay alone then reads
    1043, its own end_state 1042 -- the derivation refuses."""
    segs = copy.deepcopy(O.prior_segments())
    o2 = segs[1][1]
    ks = [i for i, k in enumerate(o2["writes"]) if k["target"] == "Global.Int16[469]"]
    o2["writes"][ks[-2]], o2["writes"][ks[-1]] = o2["writes"][ks[-1]], o2["writes"][ks[-2]]
    return segs


#: O7-KEYS's offline mutants (section 8): the DRAFT, deep-copied, one thing changed (or one seam given); the check
#: must then read FAIL -- after it has read PASS on the unchanged draft -- and its detail hold the clause. Each entry:
#: ``(name, mutate(p), clause, keys_check keywords | None)``.
OFFLINE_MUTANTS = [
    ("keys-write-value", lambda p: _key(p, "writes", 158, 445).update(value=3), "the bytes give 2, the key says 3", None),
    ("keys-chain-off", lambda p: p["chain"][0].update(off=326), "chain: FieldEntrance 300", None),
    ("keys-start-first-target", lambda p: p["start_first"].update(target="Global.Bit[192]"),
     "start_first: 154's Main_Init: its first store", None),
    ("keys-start-music-142", lambda p: p["start_music"].update(ip=142, off=132), "is 0 writes keys, not one", None),
    ("keys-scoped-old-7", lambda p: p["start_scoped"][0]["after"].update(old=7), "after.old 7, O6's frozen pattern",
     None),
    ("keys-after-run", lambda p: p["start_scoped"][0]["after"].update(run="O1-O5"),
     "after.run 'O1-O5' is not the class's AFTER_RUN 'O1-O6'", None),
    ("keys-prior-removed", lambda p: _key(p, "writes", 159, 648).pop("prior"), "names no registered prior", None),
    ("keys-o6-pattern-385", lambda p: None, "after.old -1, O6's frozen pattern's last tuple on Global.Int16[9] gives 385",
     "o6-385"),
    ("keys-start-read-off-writes", lambda p: p["start_reads"][0].update(site=[159, 0, 0, 291]),
     "start read 159 e0 t0 ip291 Global.Byte[8]: no writes key", None),
    ("keys-start-read-earlier",
     lambda p: p["writes"].insert(0, {**_key(p, "dead", 154, 279), "what": "154 Byte[8] := 125 (the 304 branch)"}),
     "stores Global.Byte[8] before it on the route", None),
    ("keys-carried-no-3815", lambda p: p["carried"]["values"].pop("Global.Bit[3815]"),
     "carried: the typed values differ from the derivation", None),
    ("keys-carried-206", lambda p: p["carried"]["values"].__setitem__("Global.Byte[206]", [0, 213]),
     "extra ['Global.Byte[206]']", None),
    ("keys-carried-in-end-state", lambda p: p["end_state"].__setitem__("Global.Bit[3795]", 0),
     "carried: ['Global.Bit[3795]'] in end_state", None),
    ("keys-carried-store-site",
     lambda p: p["forbidden_sites"].append(dict(_key(p, "forbidden_sites", 160, 298), target="Global.Bit[3815]")),
     "carried: ['Global.Bit[3815]'] hold a registered store site", None),
    ("keys-segment-contradicts", lambda p: None, "its frozen list order contradicts its end_state", "contradicting"),
]


def unit_offline_mutants(pred: dict, stock) -> list:
    """``[(name, ok, detail)]``: O7-KEYS reads PASS on the draft, then FAILS on each of :data:`OFFLINE_MUTANTS` by its
    clause."""
    base = O.O7.keys_check(pred, stock)
    out = [("offline-draft-passes", base[0] is True, base[2][:120])]
    for name, mutate, clause, seam in OFFLINE_MUTANTS:
        p = copy.deepcopy(pred)
        mutate(p)
        kw = {"o6": _o6_385(p)} if seam == "o6-385" else {"prior": _contradicting()} if seam == "contradicting" else {}
        ok, _what, detail = O.O7.keys_check(p, stock, **kw)
        caught = ok is False and clause in detail
        out.append((name, caught, f"KEYS {'FAIL' if ok is False else 'PASS (not caught)'}"
                                  + ("" if caught or ok is not False else f" -- not by {clause!r}") + f": {detail[:150]}"))
    return out


def listed_units(pred: dict, stock, tmp: Path) -> list:
    return (unit_store_census(pred, stock) + unit_regions(pred, stock) + unit_goals(pred, stock)
            + unit_route_pins(pred, stock) + unit_build_pins(pred, tmp) + unit_offline_mutants(pred, stock))


# ======================================================================== the run
def prepare(pred_path: Path | None, tmp: Path, *, as_if: bool = False) -> tuple:
    """``(path, what)``: the predictions the run reads -- ``pred_path``; else the frozen file once it exists; else the
    DRAFT, written to a temporary file; with ``as_if`` their :func:`as_if_frozen`, written to a temporary file."""
    if pred_path is not None:
        path, what = Path(pred_path), f"the file {Path(pred_path).name}"
    elif O.PREDICTIONS.is_file():
        path, what = O.PREDICTIONS, f"the frozen {O.PREDICTIONS.name}"
    else:
        path = tmp / "o7_predictions_draft.json"
        path.write_bytes((json.dumps(O.draft_predictions(), indent=1, sort_keys=True) + "\n").encode("utf-8"))
        what = "the draft"
    if not as_if:
        return path, what
    p = as_if_frozen(json.loads(path.read_text(encoding="utf-8")))
    out = tmp / "o7_predictions_as_if_frozen.json"
    out.write_bytes((json.dumps(p, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    return out, f"as_if_frozen({what})"


def _clauses_named(clauses: dict, det: dict) -> list:
    return [f"{cid} detail lacks {m}" for cid, marks in clauses.items() for m in marks if m not in det.get(cid, "")]


def _mark(ok) -> str:
    return "P" if ok is True else "F" if ok is False else "V"


def run_cases(pred_path: Path | None = None, *, as_if: bool = False, only=None) -> int:
    """Every case and unit, each printed with its marks; ``N/N cases as registered``; 1 on any miss. ``only`` (a set of
    names, a seam for a quick look) runs those alone."""
    from ff9mapkit.content.verbatim import remap_fields
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
        pred, _sha = O.O7.load(path)
        members = members_of(pred)
        retarget = {dn: f for f, dn in members.items()}
        scripts = {fid: remap_fields(stock(dn).data, retarget) for fid, dn in members.items()}
        for (name, fn, want_verdict, want, clauses, report_has, want_void, want_cov, want_lacks, detail_has,
             stopped) in CASES:
            if only and name not in only:
                continue
            total += 1
            d = make_session(sdir, path, fn(copy.deepcopy(pred)), scripts, stopped=stopped)
            checks, report = O.O7.analyse(d, stock=stock)
            got, det = result(checks), details(checks)
            v = verdict(checks)
            miss = [f"{k} {_mark(got.get(k))}, want {_mark(x)}" for k, x in want.items() if got.get(k) is not x]
            miss += [f"check {k} not registered" for k in got if k not in want]
            if not v.startswith(want_verdict):
                miss.append(f"verdict {v!r}, want {want_verdict}")
            miss += _clauses_named(clauses, det)
            miss += [f"{k} detail lacks {s!r}" for k, ss in detail_has.items() for s in ss if s not in det.get(k, "")]
            miss += [f"report lacks {s!r}" for s in report_has if s not in report]
            runs = O.O7.read_session(d, pred, stock=stock) if (want_void or want_cov or want_lacks) else []
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
            ok = not miss
            fails += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name:40} {v[:44]:44} "
                  + " ".join(f"{k[3:]}={_mark(got.get(k))}" for k in CHECKS[1:]))
            if not ok:
                for m in miss:
                    print(f"     {m}")
                ST.say("     " + "\n     ".join(f"{w_} :: {dd[:300]}" for _ok, w_, dd in checks))
        if not only or "predictions-changed" in only:
            # O7-FROZEN: the predictions changed after the session recorded them
            total += 1
            copy_path = pdir / "pred_copy.json"
            copy_path.write_bytes(path.read_bytes())
            d = make_session(sdir, copy_path, six(pred), scripts)
            copy_path.write_bytes(path.read_bytes() + b" ")
            checks, _rep = O.O7.analyse(d, stock=stock)
            v = verdict(checks)
            got = result(checks)
            ok = got.get("O7-FROZEN") is False and v.startswith("NOT PROVEN") and all(
                got.get(k) is True for k in CHECKS if k != "O7-FROZEN")
            fails += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {'predictions-changed':40} {v[:44]}")
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


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--predictions", type=Path, default=None,
                    help="a predictions file (default: the frozen o7_predictions_v1.json once it exists, else the "
                         "draft, written to a temporary file)")
    ap.add_argument("--as-if-frozen", action="store_true",
                    help="run every case on as_if_frozen(the predictions): every freeze-time value changed")
    ap.add_argument("--only", nargs="*", default=None, help="run only these cases / units (a quick look; never the gate)")
    args = ap.parse_args()
    sys.exit(run_cases(args.predictions, as_if=args.as_if_frozen, only=set(args.only) if args.only else None))
