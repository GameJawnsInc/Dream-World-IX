"""O6's analysis, driven on SYNTHETIC sessions (research/o6_design.md section 8): every registered check must read PASS
on the null pair and FAIL (or VOID) on the mutant built to break it -- a check that cannot fail is not a check.

    py studies/story-trace/o6_dryrun.py [--predictions studies/story-trace/o6_predictions_v1.json] [--as-if-frozen]

Without --predictions it reads the frozen o6_predictions_v1.json once the lead has frozen it, else it writes the DRAFT
(o6_steiner.draft_predictions: O4's chain's campaign.toml) to a temporary predictions file -- nothing is frozen until
the lead's rehearsals -- and runs every case against that. ``--as-if-frozen`` runs every case on :func:`as_if_frozen`
of those predictions instead: every value the lead's freeze changes changed (the floating row's ``measured`` set inside
its window, every budget x1.5, ``rehearsals`` named) -- the claim critic's #9: no case may read a freeze-time literal,
so both readings give the same N/N (G33 runs both).

Each case writes a session directory the way the session does (o6_session.json, the members' scripts, one trace and
one driver log per run) and runs :meth:`o6_steiner.O6Segment.analyse` on it. The rows are real store sites of the stock
bytes of 151, 153 and 154 (every field row joins but the join-failure case's), shifted onto the members on the F side
(``fld`` = member, ``don`` = donor: 151 -> 31244, 153 -> 31245, 154 -> 31246), and EMITTED as the engine's sink emits
them (StoryTrace.cs:374-401): a same-value store only while its SITE has emitted no same-value row, a change up to 64
times, the rest counted into a ``c`` row at the epoch's close -- over O6's start values (the raw warp's SC 1190 and
FieldEntrance 110 over field 70's prologue: Byte[13] 1, Int16[9] 643, Int16[11] -1, Byte[8] 125, every other target 0),
so no site of the base run is stored twice and nothing is counted. A run's driver log carries its visit rows, the page
presses, THE NAMING (the ``named`` row at 3000 with ``before`` holding 198's raw; the ``name_on_page`` row at 3200
listing 199 alone, "Steiner" rendered, ``verdict`` "ok"), THE NORTH DOOR step's row (``done``, ``frame0`` 6000, its loss
at (-50, 1340) in 153's field at 6050, path A with S14b's flip 6100 and landing 6150 and its walk-out samples) and the
end row; its outcome the beats, the pages, the end state.

O6's ``case()`` is O3's, EXACT: every check a case does not name must read PASS -- a case naming COVER V expects every
core check VOID -- so each NOT PROVEN row names EVERY check it fails, and "alone" is a registered fact. A LANDING,
NAMING, WALK, PATTERN, START-DEPENDENT or VOID-ASYM case also registers the clause its detail must name.

The units read the install read-only (the stock scripts, the stock walkmesh, block 3's US text, O4's build): S14's and
S16's strict readers and S14's pure verdict, instanced_at6, the sink as the renderer and the FakeGame's H13 implement it,
O6-PATTERN's floating reading, the trace summary on end places, the state history, O6-NAMING and O6-START-DEPENDENT pure,
LANDING (e) alone, A-START and A-NAMING, as_if_frozen, door_test, O6-CENSUS, O6-REGIONS, O6-GOALS and the route pins with
their mutants, O6-BUILD's pins on a synthetic build, O6-KEYS's offline mutants, and the launch's and the preflight's
readers (O4's and O5's units on O6's pinned values; P-NAME's own, the review's: research/o6_design.md 11.7 #1).
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
import o6_steiner as O                                                     # noqa: E402
import o5_hallway as C5                                                    # noqa: E402
import o5_dryrun as D5                                                     # noqa: E402
import o4_castle as C4                                                     # noqa: E402
import o4_dryrun as D4                                                     # noqa: E402
import o3_prima_vista as P                                                 # noqa: E402
import o2_alexandria as A                                                  # noqa: E402
import segment_drive as SD                                                 # noqa: E402
import segment_trace as ST                                                 # noqa: E402
from ff9mapkit import storytrace as T                                      # noqa: E402
from o3_dryrun import _is, after, before, e, edit, r, w, with_opt          # noqa: E402  (O3's event helpers)
from segment_trace import members_of, place, verdict                       # noqa: E402

# ======================================================================== real store sites (donor, sid, tag, ip, target, value)
PRO151 = [(151, 0, 0, 22, "Global.Bit[191]", 0), (151, 0, 0, 49, "Global.Bit[184]", 0),
          (151, 0, 0, 57, "Global.Int16[9]", -1), (151, 0, 0, 119, "Global.Byte[13]", 0),
          (151, 0, 0, 138, "Global.Int16[11]", -1), (151, 0, 0, 200, "Global.Byte[14]", 0)]
B8_315 = (151, 0, 0, 315, "Global.Byte[8]", 125)
B6_610 = (151, 3, 1, 610, "Global.Byte[6]", 8)
B8_735 = (151, 2, 1, 735, "Global.Byte[8]", 0)
CH151 = (151, 2, 1, 932, "Global.Int16[2]", 328)
PRO153 = [(153, 0, 0, 22, "Global.Bit[191]", 0), (153, 0, 0, 49, "Global.Bit[184]", 0),
          (153, 0, 0, 57, "Global.Int16[9]", -1), (153, 0, 0, 119, "Global.Byte[13]", 0),
          (153, 0, 0, 138, "Global.Int16[11]", -1), (153, 0, 0, 200, "Global.Byte[14]", 0)]
BIT3855 = (153, 32, 0, 718, "Global.Bit[3855]", 1)
BIT3854 = (153, 32, 0, 727, "Global.Bit[3854]", 1)
E15 = (153, 15, 0, 32, "Global.Byte[8]", 125)
I971 = (153, 32, 1, 971, "Global.Byte[208]", 0)
I1006 = (153, 32, 1, 1006, "Global.Byte[208]", 1)
I1656 = (153, 32, 1, 1656, "Global.UInt16[21]", 8)
I1741 = (153, 32, 1, 1741, "Global.Byte[303]", 0)
I2172 = (153, 32, 1, 2172, "Global.Byte[4]", 0)
I2206 = (153, 32, 1, 2206, "Global.UInt16[19]", 8)
I2248 = (153, 32, 1, 2248, "Global.Byte[18]", 1)
REST153 = [I971, I1006, (153, 32, 1, 1041, "Global.Byte[208]", 0), (153, 32, 1, 1076, "Global.Byte[208]", 1),
           (153, 32, 1, 1597, "Global.Byte[208]", 0), (153, 32, 1, 1632, "Global.Byte[208]", 1), I1656, I1741,
           (153, 32, 1, 1775, "Global.Byte[303]", 1), I2172, I2206, (153, 32, 1, 2232, "Global.Byte[4]", 0),
           (153, 32, 1, 2240, "Global.Byte[17]", 0), I2248]
CH153 = (153, 23, 2, 203, "Global.Int16[2]", 315)
END154 = (154, 0, 0, 26, "Global.Bit[191]", 0)
AFTER154 = [(154, 0, 0, 53, "Global.Bit[184]", 0), (154, 0, 0, 61, "Global.Int16[9]", -1),
            (154, 0, 0, 123, "Global.Byte[13]", 0), (154, 0, 0, 142, "Global.Int16[11]", -1),
            (154, 0, 0, 204, "Global.Byte[14]", 0)]
I22_151, I49_151, I57_151, I119_151, I138_151, I200_151 = PRO151
I22_153, I49_153, I57_153, I119_153, I138_153, I200_153 = PRO153
#: Off the route, each a real store: 151's and 153's error path (Byte[13] := 9: window 56's branch); 153's dead store
#: behind PARTYCHK(5) (e32 t1 ip2161); an INERT function's store (153 e3 t1 ip2953, e3 not instanced at 328); 151's
#: dead talk handler (e3 t3 ip909); e25's door store (ip195) and 64's prologue (its landing); 150's prologue.
ERR151_97 = (151, 0, 0, 97, "Global.Byte[13]", 9)
ERR153_97 = (153, 0, 0, 97, "Global.Byte[13]", 9)
DEAD_2161 = (153, 32, 1, 2161, "Global.Byte[4]", 1)
INERT_2953 = (153, 3, 1, 2953, "Global.Byte[8]", 0)
DEAD_909 = (151, 3, 3, 909, "Global.Bit[3793]", 1)
E25_195 = (153, 25, 2, 195, "Global.Int16[2]", 315)
S64 = [(64, 0, 0, 22, "Global.Bit[191]", 0), (64, 0, 0, 49, "Global.Bit[184]", 0),
       (64, 0, 0, 57, "Global.Int16[9]", -1)]
S150 = [(150, 0, 0, 26, "Global.Bit[191]", 0), (150, 0, 0, 53, "Global.Bit[184]", 0),
        (150, 0, 0, 61, "Global.Int16[9]", -1)]
SC_CS = (153, -1, -1, -1, "Global.UInt16[0]", 1190)
#: The checks, in the order the analysis reports them.
CHECKS = ("O6-FROZEN", "O6-COVER", "O6-FORBIDDEN", "O6-VOID-ASYM", "O6-START", "O6-NO-SC", "O6-CHAIN", "O6-RESIDUE",
          "O6-WRITES", "O6-NULL", "O6-STABLE", "O6-LANDING", "O6-NAMING", "O6-WALK", "O6-PATTERN",
          "O6-START-DEPENDENT", "O6-MASKED", "O6-STATE", "O6-JOIN")
CORE = CHECKS[4:]
#: The frame layout of a base run (Time.frameCount, the trace's ``f`` and the log's frames alike): 151's prologue near
#: 1050-1120; THE NAMING at 3000 (``before`` at 2990), ip610's row at 3100, the page row at 3200; 151's exit at 3300;
#: 153's prologue from 3320; the e15 row at 4300, before ip971 at 4600; THE WALK in [6000, 6050]; ip203 at 6100 (the
#: flip, path A's S14b), the landing at 6150, the cut row 154 ip26 at 6200.
F_BEFORE, F_NAMED, F_610, F_PAGE, F_EXIT151 = 2990, 3000, 3100, 3200, 3300
F_E15, F_971 = 4300, 4600
F_WALK0, F_LOST, F_203, F_FLIP, F_LANDED, F_END = 6000, 6050, 6100, 6100, 6150, 6200
#: 198, 199 and 200 as the agent publishes them (block 3's US sources, research/o6_design.md 0.2 #8, 4.11).
RAW198 = "[STRT=0,0]Queen Brahne\n“And, Captain[SPED=2]...[SPED=-1]uh[SPED=2]...[SPED=-1]”"
RAW199 = "[STRT=0,0][WDTH=0,65,19,-1]Queen Brahne\n“Captain [STNR]!”[INCS][TIME=-1]"
RAW200 = "[STRT=0,0][STNR]\n“Yes, Your Majesty!”[INCS][TIME=-1]"
RAW203 = "[STRT=0,0][STNR]\n“151 mes 203”[INCS][TIME=-1]"


def page_window(mes: int, name: str = "Steiner") -> dict:
    """A ``name_on_page`` row's window as the page witness lists it (S16): 199's or 200's raw, its text rendered with
    ``name``, its line and the frozen text."""
    raw = {199: RAW199, 200: RAW200, 203: RAW203}[mes]
    text = O.O6Segment._strip_tags(raw.replace("[STNR]", name))
    want = next((x["text"] for x in O.ON_PAGE_WINDOWS if x["mes"] == mes), None)
    line_no = next((x["line"] for x in O.ON_PAGE_WINDOWS if x["mes"] == mes), 1)
    lines = text.split("\n")
    line = lines[line_no] if line_no < len(lines) else ""
    return {"mes": mes, "raw": raw, "text": text, "line": line, "want": want, "ok": line == want}


# ======================================================================== events and their rendering
#: O6's start values (research/o6_design.md 0.2 #1, #4, section 8): the raw warp's SC and FieldEntrance over field 70's
#: prologue (70 e0 t0 ip57/130/138/200/249; the warp leaves 70 before ip475).
START_VALUES = {"Global.UInt16[0]": 1190, "Global.Int16[2]": 110, "Global.Byte[13]": 1, "Global.Int16[9]": 643,
                "Global.Int16[11]": -1, "Global.Byte[8]": 125}


def at(frame: int) -> tuple:
    """A frame anchor: the next event's row lands at ``frame`` (later rows go on 10 frames apart)."""
    return ("at", int(frame))


def render(events: list, side: str, members: dict) -> list:
    """The rows the engine would write for ``events`` on ``side`` (o5_dryrun.render's rule, O6's start values):
    F-side donors on their member ids; each store's ``old`` the variable's value so far; THE SINK'S RULE per SITE (the
    field id in it, StoryTrace.cs:101-140): a same-value store emitted only while its site has emitted no same-value
    row, a change up to 64 times, the rest counted into ``c`` rows just before ``off``. A store's ``opt``: ``fld`` /
    ``don`` (overrides), ``old``, ``m``, ``src``, ``add``, ``f`` (its row's frame, the sequence kept), ``emit`` (True:
    emitted whatever the rule says), ``count`` (True: counted whatever the rule says -- a ``c`` row of the site). An
    ``e`` event may carry a fourth item, ``{"fld"}``: an ``off`` in a REAL field on F."""
    fork = {d: f for f, d in sorted(members.items(), reverse=True)}

    def fld_of(donor):
        return fork.get(donor, donor) if side == "F" else donor
    rows, sites = [], {}
    values = dict(START_VALUES)
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
            rows.append({"k": "r", "f": f, "p": 0, "m": 1, "fld": opt.get("fld", fld_of(donor)),
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


def base_events() -> list:
    """A base run (research/o6_design.md 8): ``arm`` in field 70; the warp's THREE residue rows there (SC 1190's two
    bytes, FieldEntrance 110's low byte); 151@110's ten rows (ip610 at 3100, after the naming; its exit at 3300); 153@328's
    24 rows -- the prologue, Steiner's t0 pair, the e15 row at 4300, ip971 at 4600 and the rebuild, nothing in the walk
    window, ip203 at 6100; 154's ip26 (THE CUT) at 6200, then its post-cut prologue; ``off`` in 154 (member(154) on F)."""
    ev = [e("arm", 70), r(70, 0, 0, 166), r(70, 1, 0, 4), r(70, 2, 0, 110)]
    ev += [w(s) for s in PRO151] + [w(B8_315), at(F_610), w(B6_610), at(F_EXIT151), w(B8_735), w(CH151)]
    ev += [w(s) for s in PRO153] + [w(BIT3855), w(BIT3854), at(F_E15), w(E15), at(F_971)] + [w(s) for s in REST153]
    ev += [at(F_203), w(CH153), at(F_END), w(END154)] + [w(s) for s in AFTER154] + [e("off", 154)]
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
    """``ev`` with ``site``'s event moved after ``after_site``'s (or before ``before_site``'s), its own frame anchor
    dropped -- the row then takes the frame of where it lands."""
    i = _nth(ev, site, 0)
    x = with_opt(ev[i], **{k: v for k, v in ev[i][-1].items() if k != "f"})
    rest = ev[:i] + ev[i + 1:]
    j = (_nth(rest, after_site, 0) + 1) if after_site is not None else _nth(rest, before_site, 0)
    return rest[:j] + [x] + rest[j:]


def _fld(members: dict, side: str, donor: int) -> int:
    inv = {d: f for f, d in sorted(members.items(), reverse=True)}
    return inv.get(donor, donor) if side == "F" else donor


def visits(rows: list, members: dict) -> list:
    """The driver's ``visit`` rows for a rendered run: one each time the written field changes after the arm, in the
    route's places only (151, 153), at the frame of the visit's first row."""
    out, cur = [], None
    for x in rows:
        if x["k"] not in ("w", "r") or x["fld"] == 70 or x["fld"] == cur:
            continue
        p = place(x["fld"], members)
        if p not in (151, 153) or (members and x["fld"] not in members):
            continue
        cur = x["fld"]
        out.append({"k": "visit", "field": cur, "donor": p, "visit": len(out) + 1, "frame": x["f"], "sc": 1190})
    return out


# ======================================================================== the run's driver log
def step_row(fld: int, *, outcome="done", attempt=1, frame0=F_WALK0, lost=(F_LOST, -50.0, 1340.0), lost_field=None,
             landed=None, door=None, v=None, by=None, why=None, path="A", end_fld=None, misroute=None) -> dict:
    """THE NORTH DOOR step's row as run_step writes it (2.5; S14, S14b): its walk from the grant at (-245, 42), its
    loss sample (``lost``: frame, x, z -- with its ``field``, the walk's unless ``lost_field`` -- or None for a
    ``failed`` walk), the route record trimmed; on a done row S14b's record: path A (route_to returned before the
    switch: ``route.landed`` None, ``flip_frame`` from the ring at rule 1, ``flip_late`` True) or path B (``route.landed``
    and ``landed`` the end field ``end_fld``, ``flip_frame`` the executor's), ``landed_frame``, the walk-out samples."""
    lo = None if lost is None else {"frame": lost[0], "control": False, "x": lost[1], "z": lost[2],
                                    "field": fld if lost_field is None else lost_field}
    end = lost[0] + 10 if lost is not None else frame0 + 300
    route = {"route": 1, "travelled": 1310.0, "replans": 0, "pushes": 0, "waits": 0, "blockers": [], "landed": None,
             "changed_to": None, "handoff": True}
    row = {"k": "step", "field": fld, "donor": 153, "sc": 1190, "visit": 2, "n": 0, "kind": "trigger",
           "name": "the north door", "attempt": attempt, "outcome": outcome, "t0": 60.0, "t1": 61.5, "frame0": frame0,
           "frame": end, "from": {"frame": frame0, "control": True, "x": -245.0, "z": 42.0},
           "to": {"frame": end, "control": False, "x": None if lo is None else lo["x"],
                  "z": None if lo is None else lo["z"]},
           "lost": lo, "landed": landed, "flip_frame": None, "door": door, "route": route, "lunge": None, "climb": None,
           "depth": None, "v": v, "by": by, "why": why}
    if misroute is not None:
        row["misroute"] = misroute
    if outcome == "done" and lo is not None:
        if path == "B":
            row.update(landed=end_fld, flip_frame=F_FLIP, flip_late=False)
            row["route"].update(landed=end_fld, changed_to=end_fld)
        else:
            row.update(flip_frame=F_FLIP, flip_late=True)
        row["landed_frame"] = F_LANDED
        row["walkout"] = [[lo["frame"] + 2 * k, lo["x"], min(lo["z"] + 120.0 * k, 2065.0), False] for k in range(1, 9)]
    return row


def standard_log(pred: dict, side: str, rows: list) -> tuple:
    """A run's driver log as the drive writes it (research/o6_design.md 2.2), and the handles a case edits: ``(log,
    ctx)``. Visit 1 (151@110): its visit row, a few page presses (198 the last), THE NAMING -- the ``named`` row (its
    ``before`` 198's raw) and the ``name_on_page`` row (199 alone, "Steiner", ``verdict`` "ok") --; visit 2 (153@328): its
    visit row, its page presses, THE NORTH DOOR step's row. ``ctx``: ``named``, ``page``, ``step``, ``visits``,
    ``fld151``, ``fld153``."""
    members = members_of(pred) if side == "F" else {}
    fld151, fld153 = _fld(members, side, 151), _fld(members, side, 153)
    vis = visits(rows, members)
    seqs = iter(range(101, 100000))

    def press(fld, donor, visit, frame, raw):
        return {"k": "press", "why": "page", "field": fld, "donor": donor, "visit": visit, "sc": 1190,
                "pre": {"frame": frame, "control": False, "x": None, "z": None}, "post": None, "near": [],
                "seq": next(seqs), "ack_frame": frame + 5, "button": "confirm", "raws": [raw],
                "texts": [O.O6Segment._strip_tags(raw)], "accepted_frame": frame + 1, "down_frame": frame + 2}
    p151 = [press(fld151, 151, 1, 1500 + 60 * i, f"[STRT=0,0]151 mes {m}") for i, m in enumerate((177, 178, 179))]
    p151.append(press(fld151, 151, 1, F_BEFORE - 20, RAW198))
    named = {"k": "named", "field": fld151, "donor": 151, "sc": 1190, "frame": F_NAMED,
             "before": {"frame": F_BEFORE, "raws": [RAW198]}}
    page = {"k": "name_on_page", "field": fld151, "donor": 151, "visit": 1, "frame": F_PAGE, "tag": "[STNR]",
            "windows": [page_window(199)], "verdict": "ok"}
    p153 = [press(fld153, 153, 2, 3600 + 60 * i, f"[STRT=0,0][STNR]\n“153 mes {m}”") for i, m in
            enumerate((211, 212, 213))]
    step = step_row(fld153)
    log = vis[:1] + p151 + [named, page] + vis[1:] + p153 + [step]
    return log, {"named": named, "page": page, "step": step, "visits": vis, "fld151": fld151, "fld153": fld153}


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
    rows.append([ok, O.O6.title("P-TEXT3"), detail])
    ok, detail = C4.p_engine(dict(eng), O.ENGINE)
    rows.append([ok, O.O6.title("P-ENGINE"), detail])
    assert all(x[0] for x in rows), rows
    return rows


def make_session(tmp: Path, pred_path: Path, runs: list, scripts: dict, *, stopped: str | None = None) -> Path:
    """A session directory as O6Segment.run writes one. Each run: ``{side, events | rows, end?, why?, beats?, v?,
    cell?, by?, install?, end_state?, end_field?, skipped?, stopped?, log? (fn(log, ctx) -> log, editing the standard
    log), pages? (fn(pages))}``; ``stopped``: the session's S15 stop (``session["stopped"]``)."""
    pred, sha = O.O6.load(pred_path)
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
            rec.update(skipped=run["skipped"], stopped=run.get("stopped"), end="void", why="not driven",
                       beats=None)
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
                        "sc": 1190, "end_state": end_state, "t": 120.0, "end_row": {"seen": True, "f": last, "s": 0.1}})
        pages = ["151 mes 177", "151 mes 178", "151 mes 179", O.O6Segment._strip_tags(RAW198),
                 page_window(199)["text"], "Steiner\n“153 mes 211”"]
        if callable(run.get("pages")):
            pages = run["pages"](pages)
        beats = run.get("beats", {"named": True, "name_on_page": True, "steiner_door": True})
        outcome = {"end": end, "why": run.get("why", f"field {ST.side_ends(pred, side)[0]}" if end == "reached"
                                              else "route: stopped"),
                   "void": None, "beats": beats, "pages": pages, "timed": [],
                   "choices": [], "steps": [x for x in log if x.get("k") == "step"], "overlays": [], "forbidden": [],
                   "end_state": end_state, "t": 120.0}
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
    [markers]}`` the clauses its detail must name (each such check FAILS too), ``cover_void`` -- COVER VOID and every
    core check VOID ("too few covered runs"); every other check must read PASS. ``report_has`` substrings of the
    report, ``void`` ``{run index: [classes its VOID reasons must include]}``, ``lacks`` ``{run index: [classes they
    must NOT include]}``, ``covered`` ``{run index: bool}``, ``detail_has`` ``{check: [substrings]}`` (a check that may
    PASS or FAIL as registered, its detail holding each), ``stopped`` the session's S15 stop."""
    want = {c: True for c in CHECKS}
    if cover_void:
        want["O6-COVER"] = None
        want.update({c: None for c in CORE})
    clauses = {("O6-" + k): v for k, v in (clauses or {}).items()}
    for c in list(fail) + list(clauses):
        cid = c if c.startswith("O6-") else "O6-" + c
        want[cid] = False
    dh = {("O6-" + k): v for k, v in (detail_has or {}).items()}

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


def _edit_log(fn):
    """A log edit applied to the standard log's handles: ``fn(ctx)`` changes them in place."""
    def apply(log, ctx):
        fn(ctx)
        return log
    return apply


def _stop_151(ev: list) -> list:
    """A run stopped in 151 after the naming (its ip610 row the last), then ``off`` in 151."""
    return upto_nth(ev, B6_610, 0, e("off", 151))


def _stop_153(ev: list) -> list:
    """A run stopped in 153 at the grant (its ip2248 row the last), then ``off`` in 153."""
    return upto_nth(ev, I2248, 0, e("off", 153))


def _upto_log(kind: str):
    """A log cut before its first row of ``kind`` (a drive that stopped there)."""
    def apply(log, ctx):
        i = next((j for j, x in enumerate(log) if x.get("k") == kind), len(log))
        return log[:i]
    return apply


SCOPE_REPORT = ("a US session", "block 3: 7 byte-equal of 7", "start dependence -- values: 2 keys' VALUES depend",
                "the name -- Steiner's name is PLAYER.Name", "the end state -- read live on arrival in 154",
                "after the O1-O5 routes as driven it would write 11 (from 3,",
                "after the O1-O5 routes as driven it would write 1807 (from 1799,",
                "landing path A", "name_on_page at frame 3200", "The session's end (end_run, warp first): the title "
                                                                 "came back")


@case("null-pair", "PROVEN", report_has=SCOPE_REPORT)
def _(pred):
    return six(pred)


@case("fork-drops-a-write", "NOT PROVEN", fail=("WRITES", "NULL", "STATE"), clauses={"PATTERN": ["(b)"]})
def _(pred):
    return six(pred, f=lambda ev, n: drop_nth(ev, I2248))


@case("chain-dropped-fork", "NOT PROVEN", fail=("CHAIN", "WRITES", "NULL", "STATE"),
      clauses={"LANDING": ["(c)"], "PATTERN": ["(b)"]})
def _(pred):
    return six(pred, f=lambda ev, n: drop_nth(ev, CH153))


@case("chain-first-old-wrong", "NOT PROVEN", fail=("CHAIN",))
def _(pred):
    old = lambda ev, n: edit(ev, lambda x: _is(x, CH151), lambda x: with_opt(x, old=111))   # noqa: E731
    return six(pred, s=old, f=old)


@case("start-residue-four", "NOT PROVEN", fail=("START",))
def _(pred):
    """A byte-3 row 0 -> 1 (FieldEntrance 366, say) beside the three: O5's four-row contract would pass it; O6's three
    rows fail it."""
    return six(pred, s=lambda ev, n: before(ev, I22_151, r(70, 3, 0, 1)))


@case("start-residue-two", "NOT PROVEN", fail=("START",))
def _(pred):
    return six(pred, s=lambda ev, n: [x for x in ev if not (x[0] == "r" and x[2] == 2)])


@case("start-residue-wrong", "NOT PROVEN", fail=("START",))
def _(pred):
    return six(pred, s=lambda ev, n: edit(ev, lambda x: x[0] == "r" and x[2] == 2, lambda x: r(70, 2, 0, 109)))


@case("start-first-missing", "NOT PROVEN", fail=("START",), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """151's ip22 dropped on both sides: 151's first write is ip49 (START (b)) and visit 1's sequence is one row short
    (PATTERN (b)); 153's ip22 still writes boot_scratch on both sides, so MASKED passes."""
    gone = lambda ev, n: drop_nth(ev, I22_151)                         # noqa: E731
    return six(pred, s=gone, f=gone)


@case("start-music-old-wrong", "NOT PROVEN", fail=("START",))
def _(pred):
    old = lambda ev, n: edit_nth(ev, I119_151, 0, lambda x: with_opt(x, old=2))   # noqa: E731
    return six(pred, s=old, f=old)


@case("front-cut-write", "NOT PROVEN", fail=("START",))
def _(pred):
    in70 = ("w", 70, 3, 1, 40, "Global.Byte[13]", 1, {})              # a store in field 70, before the start
    return six(pred, f=lambda ev, n: before(ev, I22_151, in70))


@case("error-path-start-S", "PROVEN", void={1: ["V5", "A-START"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    runs = six(pred)
    ev = drop_nth(runs[0]["events"], I119_151)
    _void(runs[0], "V5", [151, 1190, 1], "driver", "a stop page (151's ambient error window 56), nothing pressed",
          events=upto_nth(ev, I57_151, 0, w(ERR151_97), e("off", 151)), log=_upto_log("named"))
    return runs


@case("v5-error-153-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={2: False}, void={2: ["V5"]},
      lacks={2: ["A-START"]})
def _(pred):
    """153 takes the error path (an F run): V5 by the GAME at [153, 1190, 2] -- VOID-ASYM (a) -- and NO A-START: 151 is
    the start place, and 153's error row is no start state's."""
    runs = six(pred)
    ev = drop_nth(runs[1]["events"], I119_153)
    _void(runs[1], "V5", [153, 1190, 2], "game", "a stop page (153's ambient error window 56)",
          events=upto_nth(ev, I57_153, 0, w(ERR153_97), e("off", 153)), log=_upto_log("step"))
    return runs


@case("residue-after-start", "NOT PROVEN", fail=("RESIDUE",))
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, I22_151, r(151, 300, 0, 7)))


@case("writes-extra-symmetric", "NOT PROVEN", fail=("WRITES",), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """153 e32 t1 ip2161's dead store (Byte[4] := 1) on both sides, before ip2172 where the script would run it: the end
    value stays 4.10's (ip2172 := 0 after it), so STATE (b) passes; NULL is symmetric."""
    add = lambda ev, n: before(ev, I2172, w(DEAD_2161))                # noqa: E731
    return six(pred, s=add, f=add)


@case("inert-row-both", "NOT PROVEN", fail=("WRITES",), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """An inert function's row (153 e3 t1 ip2953 Byte[8] := 0: e3 is not instanced at 328) in every run, before the e15
    row: an extra key and an extra emitted tuple; Byte[8]'s end value stays 125 (e15 after it)."""
    add = lambda ev, n: before(ev, E15, w(INERT_2953))                 # noqa: E731
    return six(pred, s=add, f=add)


@case("extra-key-one-F", "NOT PROVEN", fail=("STABLE", "WRITES", "STATE"), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """STABLE's mutant: one F run of three holds 151 e3 t3 ip909's store (Brahne's dead talk handler)."""
    return six(pred, f=lambda ev, n: after(ev, B6_610, w(DEAD_909)) if n == 0 else ev)


@case("sc-write-fork", "NOT PROVEN", fail=("NO-SC", "WRITES", "NULL", "STATE"))
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, BIT3854, w(SC_CS, src="cs")))


@case("sc-harness-poke-both", "NOT PROVEN", fail=("NO-SC",))
def _(pred):
    poke = lambda ev, n: after(ev, BIT3854, w((153, -1, -1, -1, "Global.Byte[0]", 7), src="harness"))  # noqa: E731
    return six(pred, s=poke, f=poke)


@case("e15-missing-F", "NOT PROVEN", fail=("WRITES", "NULL", "STATE"), clauses={"PATTERN": ["(b)"]})
def _(pred):
    return six(pred, f=lambda ev, n: drop_nth(ev, E15))


@case("e15-after-971-both", "PROVEN")
def _(pred):
    """The e15 row after ip971 and ip1006 in every run -- "the e15/e32 order flipped" (decision 6): inside the bytes'
    window, never compared there."""
    late = lambda ev, n: move(ev, E15, after_site=I1006)               # noqa: E731
    return six(pred, s=late, f=late)


@case("e15-twice-both", "NOT PROVEN", clauses={"PATTERN": ["(b)"]})
def _(pred):
    """A second e15 store 125 -> 125: the site's first SAME-VALUE store, emitted (``same`` 1) -- symmetric, so STATE (a)
    cannot see it; PATTERN (b) does."""
    again = lambda ev, n: after(ev, E15, w(E15))                       # noqa: E731
    return six(pred, s=again, f=again)


@case("e15-before-window-both", "NOT PROVEN", clauses={"PATTERN": ["(b) the floating row"]})
def _(pred):
    """The e15 row before e32 t0 ip727's -- the bytes' lower bound (ip866 follows e32 t0's ip727)."""
    early = lambda ev, n: move(ev, E15, before_site=BIT3854)            # noqa: E731
    return six(pred, s=early, f=early)


@case("e15-after-rebuild-both", "NOT PROVEN", clauses={"PATTERN": ["(b) the floating row"]})
def _(pred):
    """The e15 row after ip1656's, before ip203 -- the bytes' upper bound, which the first design's window admitted."""
    late = lambda ev, n: move(ev, E15, after_site=I1656)                # noqa: E731
    return six(pred, s=late, f=late)


@case("e15-outside-window-both", "NOT PROVEN", clauses={"PATTERN": ["(b)"], "LANDING": ["(c)"]})
def _(pred):
    """The e15 row after ip203: outside the window (PATTERN (b)), and the last field row before the cut no longer the
    door's chain row (LANDING (c))."""
    out = lambda ev, n: move(ev, E15, after_site=CH153)                 # noqa: E731
    return six(pred, s=out, f=out)


@case("byte8-repeat-both", "NOT PROVEN", clauses={"PATTERN": ["(b)"]})
def _(pred):
    """A second 151 ip735 store 0 -> 0, emitted (``same`` 1): symmetric, so STATE (a) cannot see it; Byte[8]'s frozen
    sequence does."""
    again = lambda ev, n: after(ev, B8_735, w(B8_735))                 # noqa: E731
    return six(pred, s=again, f=again)


@case("c-row-151-F", "NOT PROVEN", clauses={"PATTERN": ["(a)"]})
def _(pred):
    """Every F run: a ``c`` row of 151 ip57 (n 1) -- the prologue ran twice: PATTERN (a) alone (STATE's suppressed set
    drops a count whose last value an emitted key carries)."""
    return six(pred, f=lambda ev, n: after(ev, I57_151, w(I57_151, count=True)))


@case("rebuild-swap-F", "NOT PROVEN", clauses={"PATTERN": ["(b)"]})
def _(pred):
    """Every F run: ip1656 and ip1741 swapped -- two targets, so STATE (a)'s per-target histories cannot see it."""
    return six(pred, f=lambda ev, n: move(ev, I1656, after_site=I1741))


def _sd_edit(ev: list, site, *, old, value) -> list:
    return edit(ev, lambda x: _is(x, site), lambda x: ("w", *x[1:6], value, {**x[7], "old": old}))


def _end_state(pred: dict, **kv) -> dict:
    return dict(pred["end_state"], **{f"Global.{k}": v for k, v in kv.items()})


@case("start-drift-F", "NOT PROVEN", fail=("WRITES", "NULL", "STATE"),
      clauses={"START-DEPENDENT": ["START DRIFT on F", "the instrument's start"], "PATTERN": ["(b)"]})
def _(pred):
    """Every F run's ip610 old 1, new 9, no earlier row on byte 6: START DRIFT on F -- the instrument's start, never a
    fork finding (the claim critic's #3)."""
    runs = six(pred, f=lambda ev, n: _sd_edit(ev, B6_610, old=1, value=9))
    for run in runs:
        if run["side"] == "F":
            run["end_state"] = _end_state(pred, **{"Byte[6]": 9})
    return runs


@case("start-dependent-new-differs-F", "NOT PROVEN", fail=("WRITES", "NULL", "STATE"),
      clauses={"START-DEPENDENT": ["FINDING", "the store itself wrote another value"], "PATTERN": ["(b)"]})
def _(pred):
    """Every F run's ip610 old 0, new 9 -- ``store_override``'s shape: a FINDING (the store wrote another value)."""
    runs = six(pred, f=lambda ev, n: _sd_edit(ev, B6_610, old=0, value=9))
    for run in runs:
        if run["side"] == "F":
            run["end_state"] = _end_state(pred, **{"Byte[6]": 9})
    return runs


@case("start-drift-both", "NOT PROVEN", fail=("WRITES",),
      clauses={"START-DEPENDENT": ["START DRIFT on S", "START DRIFT on F", "the O1-O5 continuation"],
               "STATE": ["(b)"], "PATTERN": ["(b)"]})
def _(pred):
    """Both sides: ip610 3 -> 11 and ip2206 1799 -> 1807, the end state 11 / 1807 -- START DRIFT on both, the O1-O5
    continuation ((old, new) = after's): never a finding; NULL is symmetric."""
    def drift(ev, n):
        return _sd_edit(_sd_edit(ev, B6_610, old=3, value=11), I2206, old=1799, value=1807)
    runs = six(pred, s=drift, f=drift)
    return _all(runs, end_state=_end_state(pred, **{"Byte[6]": 11, "UInt16[19]": 1807}))


@case("start-dependent-twice-both", "NOT PROVEN", clauses={"START-DEPENDENT": ["2 rows"], "PATTERN": ["(b)"]})
def _(pred):
    again = lambda ev, n: after(ev, I2206, w(I2206))                   # noqa: E731
    return six(pred, s=again, f=again)


@case("start-dependent-missing-both", "NOT PROVEN", fail=("WRITES",),
      clauses={"START-DEPENDENT": ["0 rows"], "PATTERN": ["(b)"], "NAMING": ["(a)", "anchor is missing"]})
def _(pred):
    """No ip610 row on either side (the end state 4.10's): START-DEPENDENT's count, WRITES, PATTERN, and NAMING (a) --
    its anchor gone; NULL is symmetric."""
    gone = lambda ev, n: drop_nth(ev, B6_610)                          # noqa: E731
    return six(pred, s=gone, f=gone)


@case("naming-two-rows-both", "NOT PROVEN", clauses={"NAMING": ["(a)", "2 named row(s)"]})
def _(pred):
    def two(log, ctx):
        i = log.index(ctx["named"])
        return log[:i + 1] + [dict(ctx["named"], frame=F_NAMED + 5)] + log[i + 1:]
    return _all(six(pred), log=two)


@case("naming-none-both", "NOT PROVEN", clauses={"NAMING": ["(a)", "0 named row(s)"]})
def _(pred):
    """The beat ``named`` True, no ``named`` row: only a bypassed rule 4 could cover such a run."""
    return _all(six(pred), log=lambda lg, c: [x for x in lg if x is not c["named"]])


@case("naming-after-610-both", "NOT PROVEN", clauses={"NAMING": ["(a)", "is not before ip610"]})
def _(pred):
    return _all(six(pred), log=_edit_log(lambda c: c["named"].update(frame=F_610 + 50)))


@case("naming-before-missing-both", "VOID", cover_void=True, void={1: ["V13"], 2: ["V13"]})
def _(pred):
    """``before``'s raws without "And, Captain" (the ring missed 198) on every run: A-NAMING -- V13 by the driver, the
    run UNCOVERED, never a failed check."""
    def miss(c):
        c["named"]["before"] = {"frame": F_BEFORE, "raws": ["[STRT=0,0]151 mes 197"]}
    return _all(six(pred), log=_edit_log(miss))


@case("naming-real-151-F", "NOT PROVEN", clauses={"NAMING": ["(a)", "the named row in 151"]})
def _(pred):
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            run["log"] = _edit_log(lambda c: c["named"].update(field=151))
    return runs


def _typed(run: dict) -> None:
    """A run whose page witness read 199 rendering "Rusty" (a name typed at the screen): its row ``verdict`` "V13", the
    drive VOID V13 by the driver at [151, 1190, 1], stopped there."""
    def log(lg, c):
        c["page"].update(windows=[page_window(199, "Rusty")], verdict="V13")
        return lg[:lg.index(c["page"]) + 1]
    _void(run, "V13", [151, 1190, 1], "driver", "the name on the page is not the default: mes 199 renders "
                                                "'“Captain Rusty!”', registered '“Captain Steiner!”' "
                                                "-- input at the naming screen", events=_stop_151(run["events"]),
          log=log)


@case("name-typed-one-F", "PROVEN", void={2: ["V13"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    runs = six(pred)
    _typed(runs[1])
    return runs


@case("name-typed-F", "NOT PROVEN", cover_void=True, clauses={"VOID-ASYM": ["(b)"]})
def _(pred):
    """Every F run VOID V13 at the page: a typed name on every fork run is structural -- VOID-ASYM (b), never re-run
    away."""
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            _typed(run)
    return runs


@case("name-typed-both", "VOID", cover_void=True)
def _(pred):
    runs = six(pred)
    for run in runs:
        _typed(run)
    return runs


@case("name-wrong-covered-F", "NOT PROVEN", clauses={"NAMING": ["(b)", "renders"]})
def _(pred):
    """Every F run COVERED with 199 rendering "Captain Rusty!" and ``verdict`` "ok" -- a bypassed V13."""
    def wrong(c):
        win = dict(page_window(199, "Rusty"), ok=True)
        c["page"].update(windows=[win], verdict="ok")
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            run["log"] = _edit_log(wrong)
    return runs


@case("name-on-page-twice-both", "NOT PROVEN", clauses={"NAMING": ["(b)", "2 name_on_page row(s)"]})
def _(pred):
    def two(log, ctx):
        i = log.index(ctx["page"])
        return log[:i + 1] + [dict(ctx["page"], frame=F_PAGE + 5)] + log[i + 1:]
    return _all(six(pred), log=two)


@case("name-on-page-other-field-both", "NOT PROVEN", clauses={"NAMING": ["(b)", "not the naming's field"]})
def _(pred):
    """The row's field 153 / 31245 -- the driver disarms at a new visit, so only a bypass writes it."""
    return _all(six(pred), log=_edit_log(lambda c: c["page"].update(field=c["fld153"])))


@case("name-on-page-before-named-both", "NOT PROVEN", clauses={"NAMING": ["(b)", "is not after the named row"]})
def _(pred):
    return _all(six(pred), log=_edit_log(lambda c: c["page"].update(frame=F_NAMED - 100)))


@case("name-on-page-other-window-covered-both", "NOT PROVEN", clauses={"NAMING": ["(b)", "no frozen window names it"]})
def _(pred):
    """The row lists only window 203 (a [STNR] page no frozen entry names), ``verdict`` "ok", the beat True -- a
    bypassed rule."""
    return _all(six(pred), log=_edit_log(lambda c: c["page"].update(windows=[page_window(203)], verdict="ok")))


@case("name-on-page-both-windows-both", "PROVEN")
def _(pred):
    """The row lists 199 and 200 (the pair caught together), both lines right."""
    return _all(six(pred), log=_edit_log(lambda c: c["page"].update(windows=[page_window(199), page_window(200)])))


def _stuck(run: dict) -> None:
    """A run STOPPED with the naming screen up: rule 4's accept_name raised (a plain HarnessError), the trace ending at
    151's prologue."""
    run.update(events=upto_nth(run["events"], B8_315, 0, e("off", 151)), end="void",
               why="STOPPED: the naming screen stayed up through 4 Confirms", log=_upto_log("named"))


@case("naming-stuck-session", "VOID", cover_void=True, stopped="the naming screen stayed up through accept_name",
      report_has=("The session STOPPED (S15)",))
def _(pred):
    """S15: run 3 (S) STOPPED with the screen up, run 4's end_run could not close it -- ``skipped`` "the session
    stopped" -- no runs 5-6, ``session["stopped"]``: S 1 and F 1 covered, VOID (never NOT PROVEN by a run never driven)."""
    runs = six(pred)[:4]
    _stuck(runs[2])
    runs[3] = {"side": "F", "skipped": "the session stopped: the naming screen stayed up through accept_name",
               "stopped": "the naming screen stayed up through accept_name"}
    return runs


@case("naming-stuck-after-four", "PROVEN", stopped="the naming screen stayed up through accept_name",
      report_has=("The session STOPPED (S15)",), covered={5: False, 6: False})
def _(pred):
    """S15 (the claim critic's #5): runs 1-4 covered, run 5 (S) STOPPED, run 6 ``skipped``: a stopped session judged
    on the runs it covered -- PROVEN on 2 + 2, ``stopped`` reported."""
    runs = six(pred)
    _stuck(runs[4])
    runs[5] = {"side": "F", "skipped": "the session stopped: the naming screen stayed up through accept_name",
               "stopped": "the naming screen stayed up through accept_name"}
    return runs


@case("lands-real-153-covered", "NOT PROVEN", fail=("FORBIDDEN", "WRITES"),
      clauses={"LANDING": ["(a)", "(b)", "(e)"]})
def _(pred):
    real = lambda ev, n: edit(ev, lambda x: x[0] == "w" and x[1] == 153,  # noqa: E731
                              lambda x: with_opt(x, fld=153, don=153))
    return six(pred, f=real)


@case("harness-after-exit151-both", "NOT PROVEN", clauses={"LANDING": ["(b)"]})
def _(pred):
    """A harness row of place 151 between ip932 and 153's ip22: (b)'s next row -- PATTERN reads script rows only."""
    poke = lambda ev, n: after(ev, CH151, w((151, -1, -1, -1, "Global.Byte[300]", 9), src="harness"))  # noqa: E731
    return six(pred, s=poke, f=poke)


@case("last-place-harness-both", "NOT PROVEN", clauses={"LANDING": ["(c)"]})
def _(pred):
    poke = lambda ev, n: after(ev, CH153, w((153, -1, -1, -1, "Global.Byte[300]", 9), src="harness"))  # noqa: E731
    return six(pred, s=poke, f=poke)


@case("end-log-row-real-154-F", "NOT PROVEN", clauses={"LANDING": ["(c)"]})
def _(pred):
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            run["end_field"] = 154
    return runs


@case("end-real-154-F", "NOT PROVEN", clauses={"LANDING": ["(d)"]})
def _(pred):
    real = lambda ev, n: edit(ev, lambda x: _is(x, END154), lambda x: with_opt(x, fld=154, don=154))   # noqa: E731
    return six(pred, f=real)


@case("end-boundary-residue-both", "NOT PROVEN", clauses={"LANDING": ["(d)"]})
def _(pred):
    add = lambda ev, n: before(ev, END154, r(154, 300, 0, 1))          # noqa: E731
    return six(pred, s=add, f=add)


@case("seam-key-F", "NOT PROVEN", fail=("FORBIDDEN",), clauses={"LANDING": ["(a)", "(e)"]})
def _(pred):
    """Every F run holds one script row in REAL 64 (e0 t0 ip22 Bit[191] := 0) between 153's ip2248 and ip203: a seam
    crossing and a seam key -> LANDING (e), with (a) (a field row off the route) and FORBIDDEN (unbacked)."""
    real64 = w(S64[0], fld=64, don=64)
    return six(pred, f=lambda ev, n: after(ev, I2248, real64))


@case("end-row-missing-one-S", "PROVEN", void={1: ["A-NOEND"]}, covered={1: False, 3: True, 5: True},
      report_has=("A-NOEND",))
def _(pred):
    runs = six(pred)
    runs[0]["events"] = [x for x in runs[0]["events"] if not (x[0] == "w" and x[1] == 154)]
    return runs


@case("v19-one-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)", "(c)"]}, covered={2: False})
def _(pred):
    """One F run lands in REAL 154 (an un-retargeted Field()): V19 by the game at [154, 1190, 2]; the drive stops there,
    its trace ending in real 154 after its first store -- cut away as place 154."""
    runs = six(pred)
    ev = edit(runs[1]["events"], lambda x: x[0] == "w" and x[1] == 154, lambda x: with_opt(x, fld=154, don=154))
    _void(runs[1], "V19", [154, 1190, 2], "game", "the fork run entered REAL 154, where member(154) 31246 was due",
          events=upto_nth(ev, END154, 0, ("e", "off", 154, {"fld": 154})))
    return runs


@case("leak-real-153-F", "NOT PROVEN", fail=("FORBIDDEN",), clauses={"VOID-ASYM": ["(a)", "(c)"]}, covered={2: False})
def _(pred):
    """One F run enters REAL 153 from member(151) (an engine id leak): V19 by the game at [153, 1190, 1] -- rule 2 runs
    before rule 3 counts the visit; its rows at fld 153 are off the route on F and nothing in its log backs them."""
    runs = six(pred)
    real = edit(runs[1]["events"], lambda x: x[0] == "w" and x[1] == 153, lambda x: with_opt(x, fld=153, don=153))
    _void(runs[1], "V19", [153, 1190, 1], "game", "the fork run entered REAL 153, where member(153) 31245 was due",
          events=upto_nth(real, I200_153, 0, ("e", "off", 153, {"fld": 153})), log=_upto_log("step"))
    return runs


@case("v4-control-151-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={2: False})
def _(pred):
    runs = six(pred)
    _void(runs[1], "V4", [151, 1190, 1], "game", "control held in 31244 (place 151) at SC 1190, where the table has no "
                                                  "entry", events=upto_nth(runs[1]["events"], B8_315, 0,
                                                                           e("off", 151)), log=_upto_log("named"))
    return runs


@case("control-151-each-side", "PROVEN", covered={1: False, 2: False, 3: True, 4: True})
def _(pred):
    runs = six(pred)
    for run in runs[:2]:
        _void(run, "V4", [151, 1190, 1], "game", "control held in 151 at SC 1190, where the table has no entry",
              events=upto_nth(run["events"], B8_315, 0, e("off", 151)), log=_upto_log("named"))
    return runs


@case("v10-naming-153-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={2: False})
def _(pred):
    runs = six(pred)
    _void(runs[1], "V10", [153, 1190, 2], "game", "a naming screen in 31245 (place 153) at SC 1190, where the route "
                                                   "registers none", events=_stop_153(runs[1]["events"]),
          log=_upto_log("step"))
    return runs


@case("v14-one-S", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={1: False})
def _(pred):
    runs = six(pred)
    _void(runs[0], "V14", [153, 1190, 2], "game", "no progress for 60 s in 153 (place 153) at SC 1190",
          events=_stop_153(runs[0]["events"]), log=_upto_log("step"))
    return runs


@case("v7-door-all-F", "NOT PROVEN", cover_void=True, clauses={"VOID-ASYM": ["(b)"]})
def _(pred):
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            _void(run, "V7", [153, 1190, 2], "driver", "step the north door (trigger) failed 2 of its 2 attempts",
                  events=_stop_153(run["events"]))
    return runs


@case("v11-door-all-F", "NOT PROVEN", cover_void=True, clauses={"VOID-ASYM": ["(b)"]})
def _(pred):
    """Every F run V11 by the driver at [153, 1190, 2] -- a loss without the evidence that lands, every run: one side VOID
    in one class in every run (VOID-ASYM (b))."""
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            _void(run, "V11", [153, 1190, 2], "driver", "the trigger's walk left 31245 without the step's evidence",
                  events=_stop_153(run["events"]))
    return runs


@case("v13-input-one-F", "PROVEN", void={2: ["V13"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    runs = six(pred)
    _void(runs[1], "V13", [153, 1190, 2], "driver", "outside input: XInput slot 0: buttons 0x1000",
          events=_stop_153(runs[1]["events"]))
    return runs


@case("v13-loss-unseen-one-F", "PROVEN", void={2: ["V13"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    runs = six(pred)

    def log(lg, c):
        c["step"].update(outcome="void", v="V13", by="driver", landed=31246,
                         lost={"frame": F_LOST + 30, "control": False, "x": 0.0, "z": -4000.0, "field": 31246},
                         why="the loss of control went unseen in 31245 (read only in 31246; the run in 31246)")
        for k in ("walkout", "flip_late", "landed_frame"):
            c["step"].pop(k, None)
        return lg
    _void(runs[1], "V13", [153, 1190, 2], "driver", "the loss of control went unseen in 31245 (read only in 31246)",
          events=upto_nth(runs[1]["events"], CH153, 0, e("off", 153)), log=log)
    return runs


def _door(run: dict, side: str, *, backed: bool) -> None:
    """The south door e25 (153@328): the walk strays into its quad -- its store (ip195), then 64's prologue
    (member(64) 31240 on F) -- backed by the door step's row V11 ``door`` 153.e25 ``landed`` 64 / 31240, its walk begun
    before the hits, when ``backed``."""
    ev = upto_nth(run["events"], I2248, 0, at(F_WALK0 + 40), w(E25_195), *[w(s) for s in S64], e("off", 64))
    land = 64 if side == "S" else 31240

    def log(lg, c):
        st = c["step"]
        i = lg.index(st)
        st.update(outcome="void", v="V11", by="driver", door="153.e25", landed=land,
                  why=f"the trigger's walk left 153: landed in {land} (place 64)",
                  lost={"frame": F_WALK0 + 35, "control": False, "x": 0.0, "z": -1200.0,
                        "field": c["fld153"]})
        for k in ("walkout", "flip_late", "landed_frame", "flip_frame"):
            st.pop(k, None)
        return lg[:i + 1] if backed else lg[:i]
    if backed:
        _void(run, "V11", [153, 1190, 2], "driver", "the trigger's walk left 153: landed in 64", events=ev, log=log)
    else:
        _void(run, "V11", [64, 1190, 2], "game", f"left the route: entered {land} (place 64)", events=ev, log=log)


@case("v11-wrong-door-S", "PROVEN", void={1: ["V11", "A-FORBIDDEN"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    """One S run walks into e25: its store in 153, then rows in 64 -- off the route, BACKED by the step row's V11
    landing in 64 (4.9's walk backing): A-FORBIDDEN, never a finding."""
    runs = six(pred)
    _door(runs[0], "S", backed=True)
    return runs


@case("wrong-door-unbacked-F", "NOT PROVEN", fail=("FORBIDDEN",), clauses={"VOID-ASYM": ["(a)"]}, covered={2: False})
def _(pred):
    """One F run holds e25's row and rows in 31240 that no step row explains (the fork walked him there): FORBIDDEN's
    finding; its drive VOID V11 by the game (rule 2, no walk behind it) is on F only -- VOID-ASYM (a)."""
    runs = six(pred)
    _door(runs[1], "F", backed=False)
    return runs


@case("misroute-one-F", "NOT PROVEN", fail=("FORBIDDEN",), clauses={"VOID-ASYM": ["(a)"]}, covered={2: False})
def _(pred):
    """S14's ``left`` (the claim critic's #1): one F run -- the door's evidence held, its loss at (-50, 1340) in 31245,
    e23's ip203 row, then rows in 31243 (member(150): a misrouted operand's landing); the step row ``left``,
    ``misroute`` {fld 31243, place 150}, ``landed`` None; the drive VOID V11 by the GAME at rule 2's cell [150, 1190, 2].
    The 31243 rows are UNBACKED -- no V11 step row landed there -- so FORBIDDEN reads them as the fork's."""
    runs = six(pred)
    ev = upto_nth(runs[1]["events"], CH153, 0, *[w(s) for s in S150], e("off", 150))

    def log(lg, c):
        st = c["step"]
        st.update(outcome="left", landed=None, misroute={"fld": 31243, "place": 150},
                  why="the door's evidence held at (-50.0, 1340.0) in 31245 and the run landed in 31243 (place 150), "
                      "not 154: rule 2's")
        for k in ("walkout", "flip_late", "landed_frame", "flip_frame"):
            st.pop(k, None)
        return lg
    _void(runs[1], "V11", [150, 1190, 2], "game", "left the route: entered 31243 (place 150)", events=ev, log=log)
    return runs


@case("walk-path-b-both", "PROVEN")
def _(pred):
    """Every done row ``landed`` the end field (154 / 31246), ``route.landed`` set, ``flip_frame`` the executor's: S14's
    path B, done all the same."""
    def b(lg, c):
        i = lg.index(c["step"])
        end = ST.side_ends(pred, "S" if c["fld153"] == 153 else "F")[0]
        return lg[:i] + [step_row(c["fld153"], path="B", end_fld=end)] + lg[i + 1:]
    return _all(six(pred), log=b)


def _walk(steps_fn):
    """A log edit replacing the door step's row by ``steps_fn(field)``'s rows, in order."""
    def log(lg, c):
        i = lg.index(c["step"])
        return lg[:i] + steps_fn(c["step"]["field"]) + lg[i + 1:]
    return log


@case("walk-interrupted-once-both", "PROVEN")
def _(pred):
    return _all(six(pred), log=_walk(lambda fld: [
        step_row(fld, outcome="interrupted", frame0=F_WALK0 - 300, lost=(F_WALK0 - 200, -200.0, 400.0),
                 why="control went at (-200, 400) without the step's evidence"),
        step_row(fld, attempt=2, frame0=F_WALK0)]))


@case("walk-failed-once-both", "PROVEN")
def _(pred):
    return _all(six(pred), log=_walk(lambda fld: [
        step_row(fld, outcome="failed", frame0=F_WALK0 - 400, lost=None,
                 why="the walk ended with control held and nothing took it"),
        step_row(fld, attempt=2, frame0=F_WALK0)]))


@case("walk-no-step-both", "NOT PROVEN", clauses={"WALK": ["(a)"]})
def _(pred):
    return _all(six(pred), log=_walk(lambda fld: []))


@case("walk-lost-south-both", "NOT PROVEN", clauses={"WALK": ["(a)", "fails until"]})
def _(pred):
    """The done row's loss at z 1100: the walk failing its evidence (only a bypassed executor could call it done)."""
    return _all(six(pred), log=_walk(lambda fld: [step_row(fld, lost=(F_LOST, -50.0, 1100.0))]))


@case("walk-lost-other-field-both", "NOT PROVEN", clauses={"WALK": ["(a)", "read in"]})
def _(pred):
    """The done row's loss read in the end field (154 / 31246): a bypassed V13 (S14's unseen loss)."""
    def rows(fld):
        end = 154 if fld == 153 else 31246
        return [step_row(fld, lost_field=end)]
    return _all(six(pred), log=_walk(rows))


@case("walk-landed-wrong-both", "NOT PROVEN", clauses={"WALK": ["(a)", "landed in"]})
def _(pred):
    """The done row's ``landed`` 150 / 31243: a bypassed ``left`` (rule 2's verdict)."""
    def rows(fld):
        st = step_row(fld)
        st["landed"] = 150 if fld == 153 else 31243
        return [st]
    return _all(six(pred), log=_walk(rows))


@case("walk-two-interrupts-both", "NOT PROVEN", clauses={"WALK": ["(a)"]})
def _(pred):
    return _all(six(pred), log=_walk(lambda fld: [
        step_row(fld, outcome="interrupted", frame0=F_WALK0 - 500, lost=(F_WALK0 - 450, -200.0, 400.0)),
        step_row(fld, outcome="interrupted", attempt=2, frame0=F_WALK0 - 300, lost=(F_WALK0 - 250, -150.0, 600.0)),
        step_row(fld, attempt=3, frame0=F_WALK0)]))


@case("walk-interrupt-in-door-both", "NOT PROVEN", clauses={"WALK": ["(a)"]})
def _(pred):
    return _all(six(pred), log=_walk(lambda fld: [
        step_row(fld, outcome="interrupted", frame0=F_WALK0 - 300, lost=(F_WALK0 - 200, 0.0, -1200.0),
                 door="153.e25"),
        step_row(fld, attempt=2, frame0=F_WALK0)]))


@case("walk-two-failed-both", "NOT PROVEN", clauses={"WALK": ["(a)"]})
def _(pred):
    return _all(six(pred), log=_walk(lambda fld: [
        step_row(fld, outcome="failed", frame0=F_WALK0 - 600, lost=None),
        step_row(fld, outcome="failed", attempt=2, frame0=F_WALK0 - 300, lost=None),
        step_row(fld, attempt=3, frame0=F_WALK0)]))


@case("walk-failed-in-door-both", "NOT PROVEN", clauses={"WALK": ["(a)"]})
def _(pred):
    return _all(six(pred), log=_walk(lambda fld: [
        step_row(fld, outcome="failed", frame0=F_WALK0 - 400, lost=None, door="153.e25"),
        step_row(fld, attempt=2, frame0=F_WALK0)]))


@case("walk-window-late-row-both", "NOT PROVEN", clauses={"WALK": ["(b)"]})
def _(pred):
    """153 ip2248's row stamped INSIDE the walk window, its order kept: WRITES, MASKED and PATTERN (which read keys,
    names and order) cannot see it; WALK (b) reads frames."""
    late = lambda ev, n: edit_nth(ev, I2248, 0, lambda x: with_opt(x, f=F_WALK0 + 20))   # noqa: E731
    return six(pred, s=late, f=late)


@case("named-beat-missing", "VOID", cover_void=True, void={1: ["A-BEATS"], 3: ["A-BEATS"]})
def _(pred):
    runs = six(pred)
    for run in (runs[0], runs[2]):
        run["beats"] = {"named": False, "name_on_page": True, "steiner_door": True}
    return runs


@case("on-page-beat-missing", "VOID", cover_void=True, void={1: ["A-BEATS"], 3: ["A-BEATS"]})
def _(pred):
    """Two S runs: no ``name_on_page`` row, the beat False -- the ring held no parsed frozen window before 151's visit
    ended: the instrument's miss, the runs UNCOVERED, never failed."""
    runs = six(pred)
    for run in (runs[0], runs[2]):
        run["beats"] = {"named": True, "name_on_page": False, "steiner_door": True}
        run["log"] = lambda lg, c: [x for x in lg if x is not c["page"]]
    return runs


@case("door-beat-missing", "VOID", cover_void=True, void={1: ["A-BEATS"], 3: ["A-BEATS"]})
def _(pred):
    runs = six(pred)
    for run in (runs[0], runs[2]):
        run["beats"] = {"named": True, "name_on_page": True, "steiner_door": False}
    return runs


@case("end-cut", "PROVEN")
def _(pred):
    """More rows in 154 past the end (S): 154's post-cut prologue stored a second time -- all cut."""
    return six(pred, s=lambda ev, n: ev[:-1] + [w(x) for x in [END154] + AFTER154] + [ev[-1]])


@case("end-state-differs", "NOT PROVEN", clauses={"STATE": ["(b)"]})
def _(pred):
    runs = six(pred)
    runs[3]["end_state"] = _end_state(pred, **{"Bit[3855]": 0})
    return runs


@case("masked-differs", "NOT PROVEN", fail=("MASKED",), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """Every F run without its Bit[184] rows (151 ip49, 153 ip49, 154 ip53): MASKED reads the region gone on F; PATTERN
    reads both visits' sequences short (the masked rows are frozen tuples)."""
    return six(pred, f=lambda ev, n: [x for x in ev if not (x[0] == "w" and x[5] == "Global.Bit[184]")])


@case("mismatched", "PROVEN", void={2: ["A-MISMATCH"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    return six(pred, f=lambda ev, n: edit(ev, lambda x: x[0] == "w" and x[1] == 153,
                                          lambda x: with_opt(x, don=31243)) if n == 0 else ev)


@case("no-start-row", "PROVEN", void={1: ["A-NOSTART"]}, covered={1: False})
def _(pred):
    runs = six(pred)
    runs[0]["events"] = base_events()[:4] + [e("off", 70)]
    runs[0]["log"] = lambda lg, c: []
    return runs


@case("join-failure", "NOT PROVEN", fail=("JOIN",))
def _(pred):
    """An extra row at 153 e32 t1 ip2207 (one byte into ip2206's store): JOIN alone -- PATTERN reads only rows that
    join; START-DEPENDENT reads ip2206's site."""
    off = (153, 32, 1, 2207, "Global.UInt16[19]", 8)
    add = lambda ev, n: after(ev, I2206, w(off))                       # noqa: E731
    return six(pred, s=add, f=add)


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


def unit_step_of_to(pred: dict) -> tuple:
    """S14's refusals (segment_drive.step_of): the draft's door step passes with ``to`` 154; a bool, a str and a float
    ``to`` each refused; a cross's ``to`` keeps its own rule."""
    s = pred["table"][0]["steps"][0]
    got = {"draft": SD.step_of(pred, s)["to"] == 154}
    for name, to in (("bool", True), ("str", "154"), ("float", 154.0)):
        got[name] = _raises(lambda to=to: SD.step_of(pred, dict(s, to=to)), "a trigger's to is a place")
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_trigger_to_verdict() -> tuple:
    """S14's verdict, pure (segment_drive.trigger_to_verdict): path A (in-field loss, the evidence, no landing) done;
    path B (landing in ``to``) done; another place after the evidence ``left`` (rev. 2); a loss read in another field
    and no loss with a landing v13; an in-field loss without the evidence and a landing v11; the same with no landing
    judge."""
    lost = {"frame": 1, "x": -50.0, "z": 1340.0, "field": 153}
    got = {"path-a": SD.trigger_to_verdict(lost, 153, True, None, None, 154)[0] == "done",
           "path-b": SD.trigger_to_verdict(lost, 153, True, 154, 154, 154) == ("done", 154),
           "left": SD.trigger_to_verdict(lost, 153, True, 150, 150, 154) == ("left", 150),
           "other-field": SD.trigger_to_verdict(dict(lost, field=154), 153, True, 154, 154, 154)[0] == "v13",
           "none-landed": SD.trigger_to_verdict(None, 153, False, 154, 154, 154)[0] == "v13",
           "v11": SD.trigger_to_verdict(lost, 153, False, 150, 150, 154)[0] == "v11",
           "judge": SD.trigger_to_verdict(lost, 153, False, None, None, 154) == ("judge", None)}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_naming_of(pred: dict) -> tuple:
    """S16's strict reader (segment_drive.naming_of): the draft's registration passes; O2's passes; a window with a
    missing key, a ``text`` holding the tag, ``raw_holds`` without it and an ``on_page`` with an unknown key each
    refused; every frozen predictions file of the study passes (globbed, never pinned)."""
    regs = pred["naming"]
    got = {"draft": SD.naming_of(pred) == regs,
           "o2": SD.naming_of({"naming": [{"donor": 116, "sc": 1155, "beat": "named"}]}) is not None}

    def win(**kw):
        p = copy.deepcopy(pred)
        p["naming"][0]["on_page"]["windows"][0].update(kw)
        for k, v in kw.items():
            if v is ...:
                p["naming"][0]["on_page"]["windows"][0].pop(k)
        return lambda: SD.naming_of(p)
    got["no-line"] = _raises(win(line=...), "exactly keys")
    got["text-tag"] = _raises(win(text="Captain [STNR]!"), "text is the line")
    got["raw-no-tag"] = _raises(win(raw_holds="Captain Steiner!"), "raw_holds is")
    p = copy.deepcopy(pred)
    p["naming"][0]["on_page"]["extra"] = 1
    got["page-key"] = _raises(lambda: SD.naming_of(p), "exactly keys")
    for f in sorted(HERE.glob("*predictions*.json")):
        try:
            SD.naming_of(json.loads(f.read_text(encoding="utf-8")))
            got[f.name] = True
        except ValueError:
            got[f.name] = False
    return all(got.values()), str({k: v for k, v in got.items() if not v} or f"all as registered ({len(got)})")


def unit_instanced_at6(stock) -> tuple:
    """instanced_at6 (0.2 #2): 151 at 110 -> {object 3, 4, 5, 12, 17; code 1, 2}; at 327 (the default branch) ->
    {object 3, 6, 7, 12; region 8; code 1, 2}; 153 at 328 equal to O4's walker's; O4's raises on 151 -- the reason O6 has
    its own."""
    i151, i153 = stock(151), stock(153)
    a = O.instanced_at6(i151, 110)
    b = O.instanced_at6(i151, 327)
    got = {"151@110": a == {("object", 3), ("object", 4), ("object", 5), ("object", 12), ("object", 17), ("code", 1),
                            ("code", 2)},
           "151@327": b == {("object", 3), ("object", 6), ("object", 7), ("object", 12), ("region", 8), ("code", 1),
                            ("code", 2)},
           "153@328": O.instanced_at6(i153, 328) == C4.instanced_at(i153, 328),
           "o4-raises": _raises(lambda: C4.instanced_at(i151, 110), "no SWITCH")}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or f"all as registered: 151@110 {sorted(a)}")


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
            if ev[2] == 0:                                   # the warp's residue, its bytes at once
                fake._warp_writes(110, 1190)
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
    """THE SINK, one model, two implementations (0.2 #4): the base run's rows before the cut are 34 ``w`` rows (30
    unmasked) and no ``c`` row, on S and F; the SAME events through the FakeGame's H13 knob give the same ``(k, fld,
    sid, tag, ip, new, same, n, last)`` sequence, on S and F; the cut row 154 ip26 ``same`` 1 (a new site)."""
    members = members_of(pred)
    got = {}
    for side in ("S", "F"):
        rows = render(base_events(), side, members)
        fk = _fake_rows(base_events(), side, members, tmp)
        got[f"fake-{side}"] = D5._shape(rows) == D5._shape(fk)
        end154 = 154 if side == "S" else 31246
        cut = next(i for i, x in enumerate(rows) if x["k"] in ("w", "r") and x["fld"] == end154)
        before_ = [x for x in rows[:cut] if x["k"] == "w" and x["fld"] != 70]
        unmasked = [x for x in before_ if x["bit"] not in (191, 184)]
        got[f"counts-{side}"] = (len(before_), len(unmasked), sum(1 for x in rows if x["k"] == "c")) == (34, 30, 0)
        got[f"cut-{side}"] = (rows[cut]["ip"], rows[cut]["same"]) == (26, 1)
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_pattern(pred: dict, stock, tmp: Path) -> tuple:
    """O6-PATTERN's reading (4.18): :func:`o6_steiner.pattern_diff6` on the base run, joined on the stock bytes -- none,
    on S and F, render and the FakeGame alike; the e15 row anywhere in its window (after ip727 ... before ip1656):
    none; before ip727, after ip1656, twice, or missing: (b); a ``measured`` value never changes the result."""
    members = members_of(pred)
    got = {}

    def diff(events, side="S", pat=None, src="render"):
        m = members if side == "F" else {}
        rows = render(events, side, members) if src == "render" else _fake_rows(events, side, members, tmp)
        parsed = T.parse_text("".join(json.dumps(x) + "\n" for x in rows))
        kept, _at, _pre = ST.cut_at_start(parsed, 151, m)
        kept, _end = ST.cut_at_end(kept, [154], m)
        g = C5.pattern_of(kept, pred, m, C5.stock_join(stock, m))
        return O.pattern_diff6(g, pat or pred["pattern"]), g["unjoined"]
    for side in ("S", "F"):
        for src in ("render", "fake"):
            d, un = diff(base_events(), side, src=src)
            got[f"{src}-{side}"] = d == [] and un == 0
    for name, ev in (("after-971", move(base_events(), E15, after_site=I971)),
                     ("after-1006", move(base_events(), E15, after_site=I1006)),
                     ("before-1656", move(base_events(), E15, before_site=I1656))):
        got[name] = diff(ev)[0] == []
    for name, ev in (("before-727", move(base_events(), E15, before_site=BIT3854)),
                     ("after-1656", move(base_events(), E15, after_site=I1656)),
                     ("twice", after(base_events(), E15, w(E15))), ("missing", drop_nth(base_events(), E15))):
        d = diff(ev)[0]
        got[name] = bool(d) and all(x.startswith("(b)") for x in d)
    p = copy.deepcopy(pred["pattern"])
    p["floating"][0]["measured"] = {"index": [99], "frames_to_971": [1]}
    got["measured-unread"] = diff(base_events(), pat=p)[0] == [] and bool(
        diff(move(base_events(), E15, after_site=I1656), pat=p)[0])
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_trace_summary(pred: dict, stock) -> tuple:
    """O6's trace summary (7.2; O4's lesson) of a base S run: the chain 2/2, writes 28/28, the error path, forbidden and
    dead sites absent, the crossings 151 ip932 -> 153 e0 t0 ip22 and 153 ip203 -> the cut (154 e0 t0 ip26), the e15 row
    (index 8 inside its window, 300 frames to ip971), the start-dependent rows ok, the end cut's row 154 ip26 at its end
    place, no c row, no unregistered key, no join failure, the three start residue rows. An F stage ending in member(154)
    31246 is cut at 31246's first row by its end PLACES -- while O3's summary given the same end FIELDS (the unit's
    mutant) is not cut at all."""
    members = members_of(pred)
    t = O.trace_summary(_rows(base_events()), pred, stock=stock)
    reg = {k: (sum(1 for x in v if x["present"]), len(v)) for k, v in t["registered"].items()}
    want = {"chain": (2, 2), "writes": (28, 28), "error_path": (0, 8), "forbidden_sites": (0, 4), "dead": (0, 15)}
    got = {"registered": reg == want,
           "crossings": t["crossings"] == {"exit151": {"exit": "151 e2 t1 ip932 Global.Int16[2]=328",
                                                       "next": "153 e0 t0 ip22 Global.Bit[191]=0", "cut": None},
                                           "exit153": {"exit": "153 e23 t2 ip203 Global.Int16[2]=315", "next": None,
                                                       "cut": "154 e0 t0 ip26 Global.Bit[191]=0"}},
           "e15": (t["e15"] or {}).get("index") == 8 and (t["e15"] or {}).get("inside") is True
           and (t["e15"] or {}).get("frames_to_971") == F_971 - F_E15,
           "start-dependent": [x["class"] for x in t["start_dependent"]] == ["ok", "ok"],
           "end-row": t["end_row"] == "w 154 e0 t0 ip26 Global.Bit[191]=0" and t["end_places"] == [154],
           "counts": t["pattern"]["counts"] == [],
           "clean": t["unregistered"] == [] and t["failures"] == [],
           "residue": [x[1:] for x in t["residue_before"]] == [[0, 0, 166], [1, 0, 4], [2, 0, 110]]}
    frows = _rows(base_events(), "F", members)
    tf = O.trace_summary(frows, pred, side="F", end_fields=[31246], stock=stock)
    first = next(x.line for x in frows if x.k in ("w", "r") and x.fld == 31246)
    got["f-cut-at-member"] = tf["end"] == first and tf["end_places"] == [154] and tf["end_row_fld"] == 31246
    got["o3-fields-uncut"] = P.trace_summary(frows, pred, side="F", end_fields=[31246], stock=stock)["end"] is None
    return all(got.values()), str({k: v for k, v in got.items() if not v} or f"all as registered: {reg}")


def unit_state_history(pred: dict, stock, scripts: dict, tmp: Path, path: Path) -> tuple:
    """O6-STATE (a)'s reading of a base run: Byte[8]'s history [(151, 125), (151, 0), (153, 125)] (the e15 row's float
    never reorders Byte[8]'s own history); Byte[208] six entries; Byte[6] [(151, 8)]."""
    d = make_session(tmp, path, six(pred)[:1], scripts)
    run = O.O6.read_session(d, pred, stock=stock)[0]
    h = O.O6.history(run, pred)
    got = {t: [(k.donor, k.value) for k in h.get(t, [])] for t in ("Global.Byte[8]", "Global.Byte[208]",
                                                                    "Global.Byte[6]")}
    ok = got == {"Global.Byte[8]": [(151, 125), (151, 0), (153, 125)],
                 "Global.Byte[208]": [(153, 0), (153, 1), (153, 0), (153, 1), (153, 0), (153, 1)],
                 "Global.Byte[6]": [(151, 8)]}
    return ok, str(got)


def _run(rows, log, side="S", i=1, pre=()):
    return {"side": side, "i": i, "rows": rows, "log": log, "pre": list(pre)}


def unit_naming_check(pred: dict) -> tuple:
    """O6-NAMING, pure, over synthetic runs (the base run's rows and log): PASS; then each clause's FAIL -- (b)'s
    ``verdict`` V13, an unparsed window listed, a window no entry names, a line that differs, two page rows, the row
    in another field; (a)'s two named rows."""
    rows = _rows(base_events())
    seg = O.O6Segment()

    def judge(edit_fn):
        log, ctx = standard_log(pred, "S", render(base_events(), "S", {}))
        edit_fn(log, ctx)
        ok, _w, det = seg.naming_check([_run(rows, log)], pred)
        return ok, det
    got = {"pass": judge(lambda lg, c: None)[0] is True}
    unparsed = dict(page_window(199), text="Queen Brahne\n“Captain [STNR]!”")
    for name, fn, clause in (
            ("verdict", lambda lg, c: c["page"].update(verdict="V13"), "its verdict 'V13'"),
            ("unparsed", lambda lg, c: c["page"].update(windows=[unparsed]), "unparsed"),
            ("no-entry", lambda lg, c: c["page"].update(windows=[page_window(203)]), "no frozen window names it"),
            ("line", lambda lg, c: c["page"].update(windows=[dict(page_window(199, "Rusty"), ok=True)]), "renders"),
            ("two-pages", lambda lg, c: lg.append(dict(c["page"])), "2 name_on_page row(s)"),
            ("field", lambda lg, c: c["page"].update(field=153), "not the naming's field"),
            ("two-named", lambda lg, c: lg.append(dict(c["named"])), "2 named row(s)")):
        ok, det = judge(fn)
        got[name] = ok is False and clause in det
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_start_dependent_check(pred: dict, stock) -> tuple:
    """O6-START-DEPENDENT, pure (the claim critic's #3, #4): PASS on the base; FINDING (old 0, new 9); EXPLAINED (an
    earlier ``w`` row on byte 6, named); START DRIFT on one side (old 1, new 9) and on both (3 -> 11: "the O1-O5
    continuation" only at (after.old, after.value)); the zero-row and two-row counts; the report line rendered from the
    predictions -- an ``after.run`` "O1-O6" renders "after the O1-O6 routes as driven", O6-KEYS FAILS it unless the
    class's AFTER_RUN is "O1-O6" (a subclass's); never "after O1"."""
    seg = O.O6Segment()

    def check(events, side="S"):
        m = members_of(pred) if side == "F" else {}
        rows = _rows(events, side, members_of(pred))
        kept, _at, pre = ST.cut_at_start(rows, 151, m)
        ok, _w, det = seg.start_dependent_check([_run(kept, [], side=side, pre=pre)], pred)
        return ok, det
    got = {"pass": check(base_events())[0] is True}
    ok, det = check(_sd_edit(base_events(), B6_610, old=0, value=9))
    got["finding"] = ok is False and "FINDING" in det
    early = before(base_events(), B6_610, w((151, 2, 1, 735, "Global.Byte[6]", 1), target="Global.Byte[6]"))
    ok, det = check(early)
    got["explained"] = ok is False and "EXPLAINED" in det and "explained by line" in det
    ok, det = check(_sd_edit(base_events(), B6_610, old=1, value=9), side="F")
    got["drift-one"] = ok is False and "START DRIFT on F" in det and "FINDING" not in det and "continuation" not in det
    ok, det = check(_sd_edit(base_events(), B6_610, old=3, value=11))
    got["drift-continuation"] = ok is False and "START DRIFT on S" in det and "the O1-O5 continuation" in det
    ok, det = check(drop_nth(base_events(), B6_610))
    got["zero"] = ok is False and "0 rows" in det
    ok, det = check(after(base_events(), B6_610, w(B6_610)))
    got["two"] = ok is False and "2 rows" in det
    k = pred["start_dependent"][0]
    line = O.start_dependent_line(k, {"S": [8], "F": [8]}, [0])
    got["line"] = "after the O1-O5 routes as driven it would write 11 (from 3," in line and "after O1 " not in line
    o16 = copy.deepcopy(pred)
    for x in o16["start_dependent"]:
        x["after"]["run"] = "O1-O6"
    got["line-o1-o6"] = "after the O1-O6 routes as driven" in O.start_dependent_line(o16["start_dependent"][0], {}, [])
    got["keys-refuse"] = seg.keys_check(o16, stock)[0] is False

    class O7(O.O6Segment):
        AFTER_RUN = "O1-O6"
    got["keys-subclass"] = O7().keys_check(o16, stock)[0] is True
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_landing_e(pred: dict) -> tuple:
    """LANDING (e) ALONE (the claim critic's #10): a covered F run whose digest carries one seam and nothing else --
    LANDING F, the detail naming (e) alone."""
    from types import SimpleNamespace
    seg = O.O6Segment()
    m = members_of(pred)
    rows = _rows(base_events(), "F", m)
    kept, _at, pre = ST.cut_at_start(rows, 151, m)
    kept, end = ST.cut_at_end(kept, [154], m)
    cut_row = next(x for x in rows if x.line == end)
    log, _ctx = standard_log(pred, "F", render(base_events(), "F", m))
    log.append({"k": "end", "field": 31246})
    seam = SimpleNamespace(origin="31245 -> 64", to=64, frm=31245, fields=[31245, 64])
    r_ = {"side": "F", "i": 2, "rows": kept, "log": log, "pre": pre, "cut": end, "cut_row": cut_row,
          "digest": SimpleNamespace(seams=[seam], seam_keys={})}
    ok, _w, det = seg.landing_check({"S": [], "F": [r_]}, pred)
    return (ok is False and "(e)" in det and not any(f"({c})" in det for c in "abcd")), det[:150]


def unit_why_void(pred: dict, stock, scripts: dict, tmp: Path, path: Path) -> tuple:
    """A-START and A-NAMING (5.1), on a session's own reading: an S run stopped at 151's error path (ip97) holds
    A-START; an F run stopped at 153's holds none; a covered run whose named row's ``before`` lacks "And, Captain" holds
    A-NAMING (V13, the driver, cell [151, 1190, 1]); one with it, none."""
    runs = six(pred)[:3]
    ev = drop_nth(runs[0]["events"], I119_151)
    _void(runs[0], "V5", [151, 1190, 1], "driver", "a stop page", events=upto_nth(ev, I57_151, 0, w(ERR151_97),
                                                                                    e("off", 151)))
    ev = drop_nth(runs[1]["events"], I119_153)
    _void(runs[1], "V5", [153, 1190, 2], "game", "a stop page", events=upto_nth(ev, I57_153, 0, w(ERR153_97),
                                                                                  e("off", 153)))
    runs[2]["log"] = _edit_log(lambda c: c["named"].update(before={"frame": 1, "raws": ["[STRT=0,0]151 mes 197"]}))
    d = make_session(tmp, path, runs, scripts)
    rs = O.O6.read_session(d, pred, stock=stock)
    cls = [{v["class"] for v in r_["void"]} for r_ in rs]
    nam = [v for v in rs[2]["void"] if str(v.get("why")).startswith(O.A_NAMING)]
    d2 = make_session(tmp, path, six(pred)[:1], scripts)
    clean = O.O6.read_session(d2, pred, stock=stock)[0]
    got = {"start-151": "A-START" in cls[0], "none-153": "A-START" not in cls[1],
           "naming": len(nam) == 1 and nam[0]["class"] == "V13" and nam[0]["by"] == "driver"
           and nam[0].get("cell") == [151, 1190, 1],
           "naming-none": clean["covered"] and not clean["void"]}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def as_if_frozen(pred: dict) -> dict:
    """The predictions as the lead's freeze would leave them (research/o6_design.md 1.4 G33; the claim critic's #9):
    the floating row's ``measured`` set INSIDE its window (its first slot, one per R-DOOR run, with frames to ip971),
    every budget x1.5 (rounded), ``rehearsals`` two R-DOOR run dirs -- nothing else changed."""
    p = copy.deepcopy(pred)
    for fl, win in zip(p["pattern"]["floating"], O.float_window(p["pattern"])):
        fl["measured"] = {"index": [win[0], win[0]], "frames_to_971": [300, 310],
                          "why": "as if frozen: R-DOOR's measured position, inside the bytes' window"}
    p["budget"] = {k: (v if v is None else int(round(v * 1.5)) if isinstance(v, int) and not isinstance(v, bool)
                       else round(float(v) * 1.5, 2)) for k, v in p["budget"].items()}
    p["rehearsals"] = ["20261005-000001-o6-rh-door", "20261005-000002-o6-rh-door"]
    return p


def unit_as_if_frozen(draft: dict) -> tuple:
    """:func:`as_if_frozen` of the DRAFT (whatever predictions the run reads: the draft is its input) changes
    ``measured``, every budget and ``rehearsals`` and nothing else, and the freeze's refusals read it clean (its engine
    the draft's, as a live one) where they refuse the draft."""
    pred = draft
    p = as_if_frozen(pred)
    changed = sorted(k for k in set(p) | set(pred) if p.get(k) != pred.get(k))
    pat_ok = ({k: v for k, v in p["pattern"].items() if k != "floating"}
              == {k: v for k, v in pred["pattern"].items() if k != "floating"}
              and [{k: v for k, v in f.items() if k != "measured"} for f in p["pattern"]["floating"]]
              == [{k: v for k, v in f.items() if k != "measured"} for f in pred["pattern"]["floating"]])
    every = all(p["budget"][k] != pred["budget"][k] for k in pred["budget"] if pred["budget"][k])
    probs = O.O6.freeze_problems(p, live_engine=dict(pred["engine"]))
    got = {"changed": changed == ["budget", "pattern", "rehearsals"], "pattern": pat_ok, "every-budget": every,
           "freezable": probs == [],
           # the draft as the lead leaves it: refused while it names no rehearsals (the build's state), freezable
           # once the lead has filled it from R-DOOR (never pin the unfilled state: O2, O4 and O5's lesson)
           "draft-not": bool(O.O6.freeze_problems(pred, live_engine=dict(pred["engine"])))
           == (not pred.get("rehearsals"))}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or f"all as registered: {changed}") \
        + ("" if not probs else f" {probs[:2]}")


def unit_door_test(pred: dict) -> tuple:
    """door_test (4.12): (-100, 1333) off e23's pinned text; None off e24's (SYSVAR alone) and e25's (no z term)."""
    pins = {(p[0], p[1], p[2], p[3]): p[4] for p in pred["route_pins"]}
    got = {"e23": O.door_test(pins[(153, 23, 2, 38)]) == (-100, 1333),
           "e24": O.door_test(pins[(153, 24, 2, 30)]) is None,
           "e25": O.door_test(pins[(153, 25, 2, 38)]) is None}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


_LOG_HEAD = "04.10.2026 19:27:42 |M| [WindowManager] Moving window to (2045,33)\n"
_LOG_351 = ("04.10.2026 19:27:44 |W| [DataPatchers] ForkDonorPatch: donor field 351 is forked by both 30831 and 30842 "
            "-> remap DISABLED (ambiguous)\n")
_LOG_DONE = "04.10.2026 19:27:44 |M| [DataPatchers] Initialized\n"


def unit_p_donor_log() -> tuple:
    """P-DONOR-LOG over 151, 153 and 154 (O5's unit, O6's donors): today's shape PASS; 153 forked twice FAIL naming it;
    no "Initialized" FAIL."""
    a = P.p_donor_log(_LOG_HEAD + _LOG_351 + _LOG_DONE, O.ROUTE_DONORS)
    w153 = _LOG_351.replace("351", "153").replace("30831 and 30842", "31245 and 31299")
    b = P.p_donor_log(_LOG_HEAD + _LOG_351 + w153 + _LOG_DONE, O.ROUTE_DONORS)
    c = P.p_donor_log(_LOG_HEAD + _LOG_351, O.ROUTE_DONORS)
    ok = a[0] and not b[0] and "donor field 153 is forked by both 31245 and 31299" in b[1] and not c[0]
    return ok, f"today {a[0]}; 153 twice {b[0]}; no Initialized {c[0]}"


def unit_p_launch(tmp: Path) -> tuple:
    """P-LAUNCH with the engine (O5's unit, O6's ForkDonorPatch rows): older PASS; ForkDonorPatch.txt touched after the
    launch FAIL ("relaunch"); an engine DLL touched after it FAIL; another live engine FAIL; no stamp FAIL."""
    launched = P.launch_time(_LOG_HEAD + _LOG_DONE)
    game = tmp / "plaunch6"
    root = game / "FF9CustomMap"
    root.mkdir(parents=True)
    old = _dt.datetime(2026, 10, 4, 19, 27, 4)
    files = {game / "Memoria.ini": "[Battle]\nSpeed = 5\n", root / "DictionaryPatch.txt": "FieldScene 31244 11 X X 3\n",
             root / "ForkDonorPatch.txt": "31244 151\n31245 153\n31246 154\n"}
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
    D4._touch(fdp, _dt.datetime(2026, 10, 4, 19, 27, 50))
    ok, d = check()
    got["fdp-after"] = (not ok) and "ForkDonorPatch.txt" in d and "relaunch" in d
    D4._touch(fdp, old)
    dll = game / "x86" / "FF9_Data" / "Managed" / "Assembly-CSharp.dll"
    D4._touch(dll, _dt.datetime(2026, 10, 4, 19, 28))
    ok, d = check()
    got["dll-after"] = (not ok) and "Assembly-CSharp.dll" in d and "relaunch" in d
    D4._touch(dll, old)
    got["other-engine"] = not check(live={"x64": "6" * 64, "x86": "6" * 64})[0]
    got["no-stamp"] = not check(stamp=None)[0]
    got["older-again"] = check()[0]
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_p_settings(tmp: Path) -> tuple:
    """P-SETTINGS (O4's unit), plus decision 4's pin: DisableNameChoice 1 FAILS (the naming screen would be skipped)."""
    ok4, det4 = D4.unit_p_settings(tmp)
    want = O.SETTINGS
    game = tmp / "psettings6"
    game.mkdir()
    s = json.loads(json.dumps(want))
    s["Hacks"]["DisableNameChoice"] = "1"
    lines = []
    for sec, kv in s.items():
        lines += [f"[{sec}]"] + [f"{k} = {v}" for k, v in kv.items()] + [""]
    (game / "Memoria.ini").write_text("\n".join(lines), encoding="utf-8")
    ok, detail = P.p_settings(want, P.install_settings(game, [], want))
    nc = (not ok) and "[Hacks] DisableNameChoice = '1'" in detail
    return ok4 and nc, f"O4's {ok4} ({det4[:60]}); DisableNameChoice 1 FAILS {nc}"


def unit_p_name(tmp: Path) -> tuple:
    """P-NAME (the review, research/o6_design.md 11.7 #1) on a synthetic install (the live one's shape: [Import]
    Enabled 0, Text 1): no CharacterDefaultName line PASS; ``CharacterDefaultName 3 US Adelbert`` in a stacked folder
    FAILS naming the folder and the line; the default itself, another language's and another character's lines PASS,
    listed; [Import] Enabled 1 and Text 1 FAILS -- in the root's Memoria.ini, or a stacked folder's Enabled 1 over the
    root's Text 1; Enabled 1 with Text 0 PASSES; an unparsed Enabled FAILS (never guessed)."""
    game = tmp / "pname6"
    root = game / "FF9CustomMap"
    root.mkdir(parents=True)
    today = "[Import]\nEnabled = 0\nPath = %StreamingAssets%\nText = 1\n"

    def check(lines: str = "", ini: str = today, mod_ini: str | None = None) -> tuple:
        (game / "Memoria.ini").write_text(ini, encoding="utf-8")
        (root / "DictionaryPatch.txt").write_text("FieldScene 4600 11 HUB HUB 4600\n" + lines, encoding="utf-8")
        mi = root / "Memoria.ini"
        if mod_ini is None:
            mi.unlink(missing_ok=True)
        else:
            mi.write_text(mod_ini, encoding="utf-8")
        return O.p_name(game, [root], char=3, lang="US", default="Steiner")
    got = {"today": check()[0]}
    ok, d = check("CharacterDefaultName 3 US Adelbert\n")
    got["patched"] = (not ok) and "FF9CustomMap/DictionaryPatch.txt 'CharacterDefaultName 3 US Adelbert'" in d
    ok, d = check("CharacterDefaultName 3 US Steiner\nCharacterDefaultName 3 UK Adelbert\nCharacterDefaultName 12 US "
                  "Ruby Rose\n")
    got["listed"] = ok and "3 US 'Steiner'" in d and "3 UK 'Adelbert'" in d and "12 US 'Ruby Rose'" in d
    ok, d = check(ini="[Import]\nEnabled = 1\nText = 1\n")
    got["import-root"] = (not ok) and "[Import] Enabled 1 and Text 1" in d
    ok, d = check(mod_ini="[Import]\nEnabled = 1\n")
    got["import-stacked"] = (not ok) and "[Import] Enabled 1 and Text 1" in d
    got["import-no-text"] = check(ini="[Import]\nEnabled = 1\nText = 0\n")[0]
    ok, d = check(ini="[Import]\nEnabled = yes\nText = 1\n")
    got["unparsed"] = (not ok) and "[Import] Enabled = 'yes'" in d
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def units(pred: dict, stock, scripts: dict, sdir: Path, path: Path, tmp: Path) -> list:
    """Every single unit, in order: ``[(name, fn)]``, each ``fn()`` -> ``(ok, detail)``."""
    return [("step-of-to", lambda: unit_step_of_to(pred)),
            ("trigger-to-verdict", unit_trigger_to_verdict),
            ("naming-of", lambda: unit_naming_of(pred)),
            ("instanced-at6", lambda: unit_instanced_at6(stock)),
            ("render", lambda: unit_render(pred, tmp)),
            ("pattern", lambda: unit_pattern(pred, stock, tmp)),
            ("trace-summary", lambda: unit_trace_summary(pred, stock)),
            ("state-history", lambda: unit_state_history(pred, stock, scripts, sdir, path)),
            ("naming-check", lambda: unit_naming_check(pred)),
            ("start-dependent-check", lambda: unit_start_dependent_check(pred, stock)),
            ("landing-e", lambda: unit_landing_e(pred)),
            ("why-void", lambda: unit_why_void(pred, stock, scripts, sdir, path)),
            ("as-if-frozen", lambda: unit_as_if_frozen(O.draft_predictions())),
            ("door-test", lambda: unit_door_test(pred)),
            ("p-donor-log", unit_p_donor_log),
            ("p-launch", lambda: unit_p_launch(tmp)),
            ("p-settings", lambda: unit_p_settings(tmp)),
            ("p-name", lambda: unit_p_name(tmp)),
            ("p-pad", D4.unit_p_pad),
            ("p-override", D4.unit_p_override),
            ("p-engine", D4.unit_p_engine),
            ("text-strict", D4.unit_text_strict),
            ("input-witness", D4.unit_input_witness)]


# ======================================================================== the listed units (offline checks' mutants)
def _census_line() -> str:
    return ("151: 21, 153: 51 store sites -- all classified (writes 7/21, chain 1/1, masked 2/2 (151's ip22 is "
            "start_first), error_path 4/4, forbidden 0/4, dead 5/10, inert 2/9); 0 unresolved; inert 151 e8 not "
            "instanced at 110, 153 e3, e18, e28 not instanced at 328; LIVE shared 153 e15 (run by e32 t1 ip866, e32 "
            "instanced at 328); 153's other shared entries 4, 5, 6, 8, 10, 12, 19 hold no store, their callers in "
            "e3/e7/e9/e11/e18 (not instanced at 328)")


def unit_store_census(pred: dict, stock) -> list:
    """O6-CENSUS on the install PASSES with 6.1's line; each mutant FAILS by name: e15 registered ``inert``
    ``shared_by`` [32] (O5's registration replayed at 328: its caller e32 instanced there); e15's key removed from the
    writes ("in no list"); 151 e3 registered ``inert`` (instanced at 110); 151 e3 t3 ip909 removed from ``dead``; 151 e8
    removed from ``inert``; 153 e23 registered ``inert`` (instanced at 328, its ip203 a chain key); ``live_shared``
    callers naming e3."""
    out = []
    ok, _w, detail = O.O6.census_check(pred, stock)
    out.append(("store-census", ok is True and detail == _census_line(), detail[:150]))

    def without(name, test):
        def mutate(p):
            p[name] = [k for k in p[name] if not test(k)]
        return mutate

    def o5_e15(p):
        p["live_shared"] = []
        p["writes"] = [k for k in p["writes"] if (k["donor"], k["sid"]) != (153, 15)]
        p["inert"].append({"donor": 153, "sid": 15, "tags": "*", "shared_by": [32], "why": "O5's registration"})
    muts = [("census-e15-inert", o5_e15, "153 e15: registered inert, run by RunSharedScript(15) at e32 t1 ip866 -- "
                                         "e32 instanced at 328"),
            ("census-e15-unregistered", lambda p: (without("writes", lambda k: (k["donor"], k["sid"]) == (153, 15))(p),
                                                   p.__setitem__("live_shared", [])),
             "153 e15 t0 ip32 Global.Byte[8]: in no list"),
            ("census-151-e3-inert", lambda p: p["inert"].append({"donor": 151, "sid": 3, "tags": "*", "why": "mut"}),
             "inert entry 3 of 151 is instanced at entrance 110"),
            ("census-dead-909", without("dead", lambda k: (k["donor"], k["ip"]) == (151, 909)),
             "151 e3 t3 ip909 Global.Bit[3793]: in no list"),
            ("census-151-e8", without("inert", lambda k: (k["donor"], k["sid"]) == (151, 8)),
             "151 e8 t2 ip38"),
            ("census-153-e23-inert", lambda p: p["inert"].append({"donor": 153, "sid": 23, "tags": "*", "why": "mut"}),
             "inert entry 23 of 153 is instanced at entrance 328"),
            ("census-live-callers", lambda p: p["live_shared"][0].__setitem__("callers", [[3, 1, 1021]]),
             "153 e15: live_shared callers [[3, 1, 1021]]")]
    for name, mutate, clause in muts:
        p = copy.deepcopy(pred)
        mutate(p)
        ok, _w, detail = O.O6.census_check(p, stock)
        out.append((name, ok is False and clause in detail, f"{'FAIL' if ok is False else 'PASS'}: {detail[:150]}"))
    return out


def unit_regions(pred: dict, stock) -> list:
    """O6-REGIONS on the install PASSES with 6.1's line; each mutant FAILS naming its clause: 153.e23 registered dormant
    (instanced at 328); 153.e26 an exit (instanced at no route entrance); 151.e8 an exit (not instanced at 110); 153.e25
    missing (a gateway not registered); 153.e24's points shifted; a dormant region whose entrances omit 328."""
    out = []
    ok, _w, detail = O.O6.regions_check(pred, stock)
    out.append(("regions", ok is True and detail == "7 regions (3 exit, 4 dormant), 0 hot-spots, 5 gateway entries "
                                                   "all registered", detail[:150]))

    def role(key, **kw):
        def fn(p):
            r_ = p["regions"][key]
            for k in ("to", "entrance", "face_gate", "stage", "entrances"):
                r_.pop(k, None)
            r_.update(kw)
        return fn

    def shift(p):
        p["regions"]["153.e24"]["points"][0][0] += 10
    for name, mutate, clause in (
            ("regions-e23-dormant", role("153.e23", role="dormant", entrances=[328]),
             "153.e23: dormant, but instanced at route entrance(s) [328]"),
            ("regions-e26-exit", role("153.e26", role="exit", to=154, entrance=315, face_gate=None),
             "153.e26: an exit no route entrance of 153"),
            ("regions-151-e8-exit", role("151.e8", role="exit", to=153, entrance=327, face_gate=None),
             "151.e8: an exit no route entrance of 151"),
            ("regions-e25-missing", lambda p: p["regions"].pop("153.e25"), "153.e25: a gateway"),
            ("regions-e24-points", shift, "153.e24: the bytes' first SetRegion is"),
            ("regions-dormant-328", lambda p: p["regions"]["153.e27"].__setitem__("entrances", []),
             "153.e27: its entrances [] are not the route's entrances of 153 [328]")):
        p = copy.deepcopy(pred)
        mutate(p)
        ok, _w, detail = O.O6.regions_check(p, stock)
        at_ = detail.find(clause)
        out.append((name, ok is False and at_ >= 0, f"{'FAIL' if ok is False else 'PASS'}: "
                                                   + (detail[max(0, at_ - 20):at_ + 120] if at_ >= 0 else detail[:150])))
    return out


GOALS_LINES = ("1 steps: (153, 1190) #1 wall 195 route 1 legs 1600u",
               "(c') the start (-245, 42) on open ground tri 114; the route first past z 1333 at (-29, 1333), tri 79 "
               "(PSX y -1), inside 153.e23",
               "(c'') the door's test (ground > -100, z > 1333) and until z_gt 1200: 133 u of its non-firing band "
               "admitted (<= 180: 3 ticks x 60 u, derived)",
               "(d') 153.e24, 153.e25 wholly outside the until and avoided; the start's open component (118 tris): its "
               "14 tris past z 1200 all ground",
               "(e) to 154: 153's live Field(154) at 328 is e23 t2 ip211 alone")


def unit_goals(pred: dict, stock) -> list:
    """O6-GOALS on the install PASSES with 6.1's lines; each mutant FAILS by its clause: ``until`` z_gt 900 ((c''): 433
    u of the non-firing band, over the derived 180); a typed ``walk.stale_slack`` 500 ((c''): refused by name -- under
    the first design it let the 900 mutant pass); e25 dropped from ``avoid`` ((d')); ``start`` (-226, 1086) on the upper
    corridor ((c'): no open tri under it); ``walk.door`` 153.e24 ((c''): no z term); ``to`` 150 ((e)); ``closed_tris``
    empty (O2's: no route); the goal at (19, 2500) (O2's: off the floor)."""
    out = []
    ok, _w, detail = O.O6.goals_check(pred, stock=stock)
    out.append(("goals", ok is True and all(x in detail for x in GOALS_LINES), detail[-200:]))

    def step(**kw):
        def fn(p):
            s = p["table"][0]["steps"][0]
            for k, v in kw.items():
                if v is ...:
                    s.pop(k, None)
                else:
                    s[k] = v
        return fn
    for name, mutate, clause in (
            ("goals-until-900", step(until={"z_gt": 900}), "(c''): until z_gt 900 admits 433 u"),
            ("goals-stale-slack", lambda p: (step(until={"z_gt": 900})(p), p["walk"].__setitem__("stale_slack", 500)),
             "a typed stale_slack 500"),
            ("goals-e25-avoid", step(avoid=["153.e24"]), "(d'): the registered exit(s) ['153.e25'] are not in"),
            ("goals-start-upper", step(start=[-226, 1086]), "(c'): the start (-226.0, 1086.0) stands on no open tri"),
            ("goals-door-e24", lambda p: p["walk"].__setitem__("door", "153.e24"), "(c''): the door's test"),
            ("goals-to-150", step(to=150), "(e): its to 150 is not where the route's order goes next"),
            ("goals-no-closed-tris", step(closed_tris=[]), "no route from"),
            ("goals-goal-off-floor", step(goal=[19, 2500]), "off the floor")):
        p = copy.deepcopy(pred)
        mutate(p)
        ok, _w, detail = O.O6.goals_check(p, stock=stock)
        at_ = detail.find(clause)
        out.append((name, ok is False and at_ >= 0, f"{'FAIL' if ok is False else 'PASS'}: "
                                                   + (detail[max(0, at_ - 40):at_ + 120] if at_ >= 0 else detail[:150])))
    return out


def unit_route_pins(pred: dict, stock) -> list:
    """O6-KEYS (b), THE ROUTE PINS and route_mes (4.16), on the install PASS; each mutant FAILS by its clause: a pin's
    text changed (the door's threshold, and e23 t2 ip80's test); a ``Map.Bit[144] := 1`` store added to 153's script;
    mes 198 without "And, Captain"; mes 199 without its source; mes 200 without its source; a ``naming`` window text not
    the computed line; mes 56 without "Env Play()"."""
    mes = D5.block3_us()
    texts = O.O6Segment._all_texts(stock(153))
    out = []
    ok, detail = O.O6.route_pins_check(pred, stock, mes=mes, texts=texts)
    out.append(("route-pins", ok is True and detail.startswith("74 route pins equal; 153 never writes Map.Bit[144] "
                                                               "(26 references, all tests)"), detail[:150]))
    for name, ip, old, new in (("route-pins-threshold", 38, "const(1333)", "const(1332)"),
                               ("route-pins-ip80", 80, "const(0) B_EQ", "const(1) B_EQ")):
        p = copy.deepcopy(pred)
        pin = next(x for x in p["route_pins"] if x[:4] == [153, 23, 2, ip])
        pin[4] = pin[4].replace(old, new)
        ok, detail = O.O6.route_pins_check(p, stock, mes=mes, texts=texts)
        out.append((name, ok is False and f"153 e23 t2 ip{ip}" in detail, detail[:150]))
    ok, detail = O.O6.route_pins_check(pred, stock, mes=mes, texts=texts + [(30, 1, 99, "SET({Map.Bit[144] const(1) "
                                                                                       "B_LET B_EXPR_END})")])
    out.append(("route-pins-bit144-store", ok is False and "153 stores Map.Bit[144]" in detail, detail[:150]))
    m198, m199, m200 = mes[198], mes[199], mes[200]
    for name, fn, clause in (
            ("route-mes-198", lambda m: m.__setitem__(198, m198.replace("And, Captain", "And, Knight")),
             "does not hold the marker 'And, Captain'"),
            ("route-mes-199", lambda m: m.__setitem__(199, m199.replace("Captain [STNR]", "Captain [ZDNE]")),
             "mes 199 does not hold its source"),
            ("route-mes-200", lambda m: m.__setitem__(200, m200.replace("[STNR]", "[ZDNE]")),
             "mes 200 does not hold its source"),
            ("route-mes-56", lambda m: m.__setitem__(56, m[56].replace("Env Play()", "Env Stop()")),
             "mes 56 does not hold the stop page")):
        mm = dict(mes)
        fn(mm)
        ok, detail = O.O6.route_pins_check(pred, stock, mes=mm, texts=texts)
        out.append((name, ok is False and clause in detail, f"{'FAIL' if ok is False else 'PASS'}: {detail[:150]}"))
    p = copy.deepcopy(pred)
    p["naming"][0]["on_page"]["windows"][0]["text"] = "“Captain Steiner”"
    ok, detail = O.O6.route_pins_check(p, stock, mes=mes, texts=texts)
    out.append(("route-mes-window-text", ok is False and "is not the computed line" in detail, detail[:150]))
    return out


def unit_build_pins(pred: dict, tmp: Path) -> list:
    """O6-BUILD's route pins (O5's unit, :meth:`o5_hallway.O5Segment.build_pins`) on O6's predictions, a synthetic
    three-member build through a ``stock_lang`` seam: the clean build PASSES; each mutant FAILS by its clause: an extra
    byte changed in member(153)'s e32 t1 (ip2206's statement, jp); a PreloadField operand remapped (153 e23 t2 ip101's
    154 -> 31246, fr); an in-chain Field() left unremapped (member(153) e23 t2 ip211's Field(154), us)."""
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
    m153 = next(f for f, d in members.items() if d == 153)
    m154 = next(f for f, d in members.items() if d == 154)

    def flip(fid, L, data):
        if fid == m153 and L == "jp":
            ins = instr(153, L, 32, 1, 2206)
            data[ins.off + 3] ^= 0x01

    def remap_preload(fid, L, data):
        if fid == m153 and L == "fr":
            ins = instr(153, L, 23, 2, 101)
            assert ins.imm(1) == 154, ins
            o = D4._operand(ins, 1)
            data[o:o + 2] = m154.to_bytes(2, "little")

    def unremap(fid, L, data):
        if fid == m153 and L == "us":
            ins = instr(153, L, 23, 2, 211)
            assert ins.imm(0) == 154, ins
            data[ins.off + 2:ins.off + 4] = (154).to_bytes(2, "little")
    out = []
    ok, detail = O.O6.build_pins(pred, build("bp6-clean"), stock_lang=stock_lang)
    out.append(("build-pins-clean", ok is True and detail == "the route members' pins hold in 21 member files (3 route "
                                                            "members x 7 languages): the only byte diffs are their 16 "
                                                            "in-chain Field() operands", detail[:150]))
    for name, mutate, clause in (("build-pins-extra-byte", flip, "differ outside the in-chain Field() operands"),
                                 ("build-pins-preload", remap_preload, "differ outside the in-chain Field() operands"),
                                 ("build-pins-unremapped", unremap, "left unremapped")):
        ok, detail = O.O6.build_pins(pred, build(name, mutate), stock_lang=stock_lang)
        at_ = detail.find(clause)
        out.append((name, ok is False and at_ >= 0,
                    f"{'FAIL' if ok is False else 'PASS'}: " + (detail[max(0, at_ - 60):at_ + 90] if at_ >= 0
                                                                else detail[:150])))
    return out


def _key(p: dict, name: str, donor: int, ip: int) -> dict:
    return next(k for k in p[name] if (k["donor"], k["ip"]) == (donor, ip))


#: O6-KEYS's offline mutants (section 8): the DRAFT, deep-copied, one thing changed; the check must then read FAIL --
#: after it has read PASS on the unchanged draft -- and its detail hold the clause.
OFFLINE_MUTANTS = [
    ("keys-write-value", lambda p: _key(p, "writes", 153, 2248).update(value=0), "the bytes give 1, the key says 0"),
    ("keys-chain-off", lambda p: p["chain"][0].update(off=922), "chain: FieldEntrance 328"),
    ("keys-start-first-target", lambda p: p["start_first"].update(target="Global.Bit[192]"),
     "start_first: 151's Main_Init: its first store"),
    ("keys-dead-value", lambda p: _key(p, "dead", 151, 130).update(value=2), "the bytes give 1, the key says 2"),
    ("keys-start-music", lambda p: p["start_music"].update(ip=138, off=132), "is 0 writes keys, not one"),
    ("keys-after-value", lambda p: p["start_dependent"][0]["after"].update(value=12),
     "after.value 12 -- the bytes give 11"),
    ("keys-after-run", lambda p: p["start_dependent"][0]["after"].update(run="O1-O4"),
     "after.run 'O1-O4' is not the class's AFTER_RUN 'O1-O5'"),
    ("keys-after-source", lambda p: p["start_dependent"][1]["after"].pop("source"), "after carries no source"),
    ("keys-e15-sid", lambda p: _key(p, "writes", 153, 32).update(sid=32), "153 e15 Byte[8] := 125"),
    ("keys-prior-removed", lambda p: _key(p, "writes", 153, 1006).pop("prior"), "names no registered prior"),
]


def unit_offline_mutants(pred: dict, stock) -> list:
    """``[(name, ok, detail)]``: O6-KEYS reads PASS on the draft, then FAILS on each of :data:`OFFLINE_MUTANTS` by its
    clause."""
    base = O.O6.keys_check(pred, stock)
    out = [("offline-draft-passes", base[0] is True, base[2][:120])]
    for name, mutate, clause in OFFLINE_MUTANTS:
        p = copy.deepcopy(pred)
        mutate(p)
        ok, _what, detail = O.O6.keys_check(p, stock)
        caught = ok is False and clause in detail
        out.append((name, caught, f"KEYS {'FAIL' if ok is False else 'PASS (not caught)'}"
                                  + ("" if caught or ok is not False else f" -- not by {clause!r}") + f": {detail[:120]}"))
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
        path = tmp / "o6_predictions_draft.json"
        path.write_bytes((json.dumps(O.draft_predictions(), indent=1, sort_keys=True) + "\n").encode("utf-8"))
        what = "the draft"
    if not as_if:
        return path, what
    p = as_if_frozen(json.loads(path.read_text(encoding="utf-8")))
    out = tmp / "o6_predictions_as_if_frozen.json"
    out.write_bytes((json.dumps(p, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    return out, f"as_if_frozen({what})"


def _clauses_named(clauses: dict, det: dict) -> list:
    return [f"{cid} detail lacks {m}" for cid, marks in clauses.items() for m in marks if m not in det.get(cid, "")]


def _mark(ok) -> str:
    return "P" if ok is True else "F" if ok is False else "V"


def run_cases(pred_path: Path | None = None, *, as_if: bool = False) -> int:
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
        pred, _sha = O.O6.load(path)
        members = members_of(pred)
        retarget = {dn: f for f, dn in members.items()}
        scripts = {fid: remap_fields(stock(dn).data, retarget) for fid, dn in members.items()}
        for (name, fn, want_verdict, want, clauses, report_has, want_void, want_cov, want_lacks, detail_has,
             stopped) in CASES:
            total += 1
            d = make_session(sdir, path, fn(copy.deepcopy(pred)), scripts, stopped=stopped)
            checks, report = O.O6.analyse(d, stock=stock)
            got, det = result(checks), details(checks)
            v = verdict(checks)
            miss = [f"{k} {_mark(got.get(k))}, want {_mark(x)}" for k, x in want.items() if got.get(k) is not x]
            miss += [f"check {k} not registered" for k in got if k not in want]
            if not v.startswith(want_verdict):
                miss.append(f"verdict {v!r}, want {want_verdict}")
            miss += _clauses_named(clauses, det)
            miss += [f"{k} detail lacks {s!r}" for k, ss in detail_has.items() for s in ss if s not in det.get(k, "")]
            miss += [f"report lacks {s!r}" for s in report_has if s not in report]
            runs = O.O6.read_session(d, pred, stock=stock) if (want_void or want_cov or want_lacks) else []
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
        # O6-FROZEN: the predictions changed after the session recorded them
        total += 1
        copy_path = pdir / "pred_copy.json"
        copy_path.write_bytes(path.read_bytes())
        d = make_session(sdir, copy_path, six(pred), scripts)
        copy_path.write_bytes(path.read_bytes() + b" ")
        checks, _rep = O.O6.analyse(d, stock=stock)
        v = verdict(checks)
        got = result(checks)
        ok = got.get("O6-FROZEN") is False and v.startswith("NOT PROVEN") and all(
            got.get(k) is True for k in CHECKS if k != "O6-FROZEN")
        fails += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {'predictions-changed':40} {v[:44]}")
        for name, fn in units(pred, stock, scripts, sdir, path, udir):
            total += 1
            ok, detail = fn()
            fails += not ok
            ST.say(f"{'ok  ' if ok else 'FAIL'} {name:40} (unit) {detail[:150]}")
        for name, ok, detail in listed_units(pred, stock, udir):
            total += 1
            fails += not ok
            ST.say(f"{'ok  ' if ok else 'FAIL'} {name:40} (unit) {detail[:150]}")
    print(f"\n{total - fails}/{total} cases as registered")
    return 1 if fails else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--predictions", type=Path, default=None,
                    help="a predictions file (default: the frozen o6_predictions_v1.json once it exists, else the "
                         "draft, written to a temporary file)")
    ap.add_argument("--as-if-frozen", action="store_true",
                    help="run every case on as_if_frozen(the predictions): every freeze-time value changed")
    args = ap.parse_args()
    sys.exit(run_cases(args.predictions, as_if=args.as_if_frozen))
