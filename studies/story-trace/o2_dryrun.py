"""O2's analysis, driven on SYNTHETIC sessions (research/o2_design.md section 8): every registered check must read
PASS on the null pair and FAIL (or VOID) on the mutant built to break it -- a check that cannot fail is not a check.

    py studies/story-trace/o2_dryrun.py [--predictions studies/story-trace/o2_predictions_v1.json]

Without --predictions it writes the DRAFT (o2_alexandria.draft_predictions) to a temporary predictions file -- nothing
is frozen until the lead's rehearsals -- and runs every case against that.

Each case writes a session directory the way the session does (o2_session.json, the members' scripts, one trace and
one driver log per run) and runs :meth:`o2_alexandria.O2Segment.analyse` on it. The rows are real store sites of the
stock bytes of 100-106, 115, 116 and 61 (every one joins but the join-failure case's), shifted onto the fork's ids on
the F side (``fld`` = member, ``don`` = donor, as the engine writes them), and EMITTED as the engine emits them: a
same-value store once per site, a value change up to 64 times, the rest counted into a ``c`` row at the epoch's
close (StoryTrace.cs:383-400). A run's driver log carries its visit rows and whatever evidence a case gives it (the
``press`` / ``watch`` / ``step`` rows 4.7's backing rule reads).

The OFFLINE checks get the same treatment without a session (:data:`OFFLINE_MUTANTS`): O2-KEYS, O2-REGIONS and
O2-GOALS read PASS on the draft and FAIL -- by the clause each mutant breaks -- on every one-change copy of it; O2-TEXT
FAILs a build missing a language, P-RECOVERY a recovery field no folder registers.

Nothing here touches the game or the install's mod folders: it reads the stock scripts and, for O2-GOALS, the stock
walkmeshes, read-only; the text and the mod folders the units read are synthetic.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import o2_alexandria as A                                                  # noqa: E402
from ff9mapkit import storytrace as T                                      # noqa: E402
from segment_trace import members_of, place, verdict                       # noqa: E402

# ======================================================================== real store sites (donor, sid, tag, ip)
START = (100, 0, 0, 30)                       # Bit[191] := 0, 100's Main_Init: start_first
BIT184 = (100, 0, 0, 57)                      # Bit[184] := 0, the next Main_Init store
SC1150, SC1151, SC1152 = (104, 7, 1, 1046), (105, 3, 1, 511), (105, 14, 1, 2818)
SC1153, SC1154, SC1155 = (106, 2, 1, 312), (115, 1, 1, 462), (115, 1, 1, 1683)
CH1, CH6, CH7 = (100, 15, 2, 255), (104, 2, 1, 558), (103, 22, 2, 261)
HERALD, HIPPAUL1, ILIA0, UINT19 = (101, 7, 1, 319), (103, 18, 1, 218), (106, 5, 0, 109), (100, 19, 1, 1531)
EXIT101 = (101, 16, 2, 255)

#: The route's registered rows (4.2-4.4), in route order: (donor, sid, tag, ip, target, value).
ROUTE = [
    (100, 19, 1, 834, "Global.Byte[8]", 125), (100, 19, 1, 981, "Global.UInt16[21]", 2),
    (100, 19, 1, 1066, "Global.Byte[303]", 0), (100, 19, 1, 1100, "Global.Byte[303]", 1),
    (100, 19, 1, 1497, "Global.Byte[4]", 0), (100, 19, 1, 1531, "Global.UInt16[19]", 2),
    (100, 19, 1, 1562, "Global.Byte[4]", 0), (100, 19, 1, 1570, "Global.Byte[17]", 0),
    (100, 19, 1, 1578, "Global.Byte[18]", 1), (100, 1, 18, 579, "Global.Bit[3718]", 1),
    (100, 15, 2, 255, "Global.Int16[2]", 200),
    (101, 0, 0, 291, "Global.Int16[2]", 202), (101, 7, 1, 319, "Global.Bit[3717]", 1),
    (101, 16, 2, 255, "Global.Int16[2]", 201),
    (102, 8, 2, 255, "Global.Int16[2]", 203),
    (103, 0, 0, 367, "Global.Byte[8]", 125), (103, 18, 1, 218, "Global.Byte[472]", 1),
    (103, 30, 1, 972, "Global.Int16[2]", 205),
    (104, 7, 0, 313, "Global.Int16[469]", 1042), (104, 7, 0, 333, "Global.Int16[469]", 1043),
    (104, 7, 1, 613, "Global.Int16[469]", 1042), (104, 7, 1, 955, "Global.Byte[472]", 4),
    (104, 7, 1, 1046, "Global.UInt16[0]", 1150), (104, 2, 1, 558, "Global.Int16[2]", 209),
    (103, 0, 0, 367, "Global.Byte[8]", 125),      # the second visit's store: a same-value repeat, only counted
    (103, 22, 2, 205, "Global.Byte[13]", 3), (103, 22, 2, 244, "Global.Byte[14]", 3),
    (103, 22, 2, 261, "Global.Int16[2]", 205),
    (105, 3, 1, 511, "Global.UInt16[0]", 1151), (105, 14, 1, 2818, "Global.UInt16[0]", 1152),
    (105, 11, 2, 227, "Global.Int16[2]", 111),
    (106, 5, 0, 109, "Global.Bit[3712]", 0), (106, 2, 1, 312, "Global.UInt16[0]", 1153),
    (106, 14, 2, 194, "Global.Byte[13]", 3), (106, 14, 2, 222, "Global.Int16[2]", 211),
    (115, 0, 0, 249, "Global.Int16[2]", 213), (115, 0, 0, 467, "Global.Byte[8]", 125),
    (115, 1, 1, 462, "Global.UInt16[0]", 1154), (115, 1, 1, 1683, "Global.UInt16[0]", 1155),
    (115, 1, 1, 1951, "Global.Int16[2]", 0),
    (116, 0, 0, 335, "Global.Byte[8]", 125), (116, 2, 1, 765, "Global.Byte[6]", 2),
    (116, 2, 1, 1469, "Global.Byte[8]", 0), (116, 2, 1, 1666, "Global.Byte[13]", 3),
    (116, 2, 1, 1694, "Global.Int16[2]", 0),
]
#: Rows off the route, each a real store: the plaque hot-spot (103 e20 t1: its own position into Int16[220]/[222]);
#: Jack's mugging branch; 115 e17 t12, the card event behind the DORMANT e14; Kupo's talk on masked bytes only;
#: Ilia's :=1; 100's ambient-9 branch; the debug SC overwrite; 112's Main_Init (a field off the route).
PLAQUE = [(103, 20, 1, 174, "Global.Int16[220]", 600), (103, 20, 1, 182, "Global.Int16[222]", -272)]
JACK = (105, 7, 2, 945, "Global.Bit[3715]", 1)
CARD = [(115, 17, 12, 2150, "Global.Byte[472]", 4), (115, 17, 12, 2205, "Global.Bit[7202]", 1),
        (115, 17, 12, 2268, "Global.Int16[224]", -480)]
KUPO_MASKED = [(115, 2, 3, 2050, "Global.Bit[189]", 1), (115, 2, 3, 2728, "Global.Byte[1034]", 0)]
ILIA1 = (106, 5, 1, 165, "Global.Bit[3712]", 1)
AMBIENT9 = (100, 0, 0, 105, "Global.Byte[13]", 9)
SC_DEBUG = (105, 3, 1, 497, "Global.UInt16[0]", 1151)
IN_112 = [(112, 0, 0, 26, "Global.Bit[191]", 0), (112, 0, 0, 53, "Global.Bit[184]", 0),
          (112, 0, 0, 61, "Global.Int16[9]", 355)]
AFTER_61 = [(61, 0, 0, 49, "Global.Bit[184]", 0), (61, 0, 0, 57, "Global.Int16[9]", -1)]
TEXT_DEFECT = ("KNOWN-KIT-DEFECT 1, FAIL 0, 6 byte-equal of 7 languages | KNOWN-KIT-DEFECT uk: ships stock us "
               "(4751874951; stock uk 8c94536b6c): dialogue._lang_score aliases uk to us (dialogue.py:374) -- the "
               "lead's kit fix")


# ======================================================================== events and their rendering
def w(site, value=None, target=None, **opt) -> tuple:
    """A store event: ``site`` = (donor, sid, tag, ip[, target, value]); ``opt``: fld/don (overrides), old, m, src."""
    donor, sid, tag, ip = site[:4]
    return ("w", donor, sid, tag, ip, target or site[4], site[5] if value is None else value, opt)


def r(donor, byte, old, new, **opt) -> tuple:
    return ("r", donor, byte, old, new, opt)


def e(why, donor) -> tuple:
    return ("e", why, donor)


def base_events(*, residue=((0, 0, 232), (1, 0, 3), (2, 0, 102))) -> list:
    """A base run (research/o2_design.md 8): ``arm`` in field 70; the warp's residue there; ``start_first``, then
    100's Bit[184] := 0; the route's registered rows in route order; 61's first row; ``off`` in 61."""
    ev = [e("arm", 70)] + [r(70, b, o, n) for b, o, n in residue]
    ev += [w((*START, "Global.Bit[191]", 0)), w((*BIT184, "Global.Bit[184]", 0))]
    ev += [w(s) for s in ROUTE]
    ev += [w((61, 0, 0, 22, "Global.Bit[191]", 0)), e("off", 61)]
    return ev


def _parse(target: str) -> tuple:
    width, index = target.split(".", 1)[1].rstrip("]").split("[")
    return width, int(index)


def render(events: list, side: str, members: dict) -> list:
    """The rows the engine would write for ``events`` on ``side``: F-side donors on their member ids; each store's
    ``old`` the variable's value so far (the warp leaves SC 1000 and FieldEntrance 102); a same-value store emitted
    once per site, a change up to 64 times per site, the rest counted into ``c`` rows just before ``off``."""
    fork = {d: f for f, d in members.items()}

    def fld_of(donor):
        return fork.get(donor, donor) if side == "F" else donor
    rows, sites = [], {}
    values = {"Global.UInt16[0]": 1000, "Global.Int16[2]": 102}
    f, sc = 1000, 0
    for ev in events:
        f += 10
        kind = ev[0]
        if kind == "e":
            _k, why, donor = ev
            if why == "off":
                for key, s in sites.items():
                    if s["n"]:
                        fld, m, src, sid, tag, ip, byte, width, bit = key
                        rows.append({"k": "c", "f": f, "p": 0, "m": m, "fld": fld, "don": s["don"], "sc": sc,
                                     "src": src, "sid": sid, "tag": tag, "ip": ip, "byte": byte, "w": width,
                                     "bit": bit, "n": s["n"], "last": s["last"]})
                f += 1
            rows.append({"k": "e", "f": f, "p": 0, "m": 1, "fld": fld_of(donor), "don": donor, "sc": sc, "why": why})
        elif kind == "r":
            _k, donor, byte, old, new, opt = ev
            rows.append({"k": "r", "f": f, "p": 0, "m": 1, "fld": opt.get("fld", fld_of(donor)),
                         "don": opt.get("don", donor), "sc": sc, "byte": byte, "old": old, "new": new, "why": "frame"})
        else:
            _k, donor, sid, tag, ip, target, value, opt = ev
            width, index = _parse(target)
            bit = index if width in T.BIT_WIDTHS else -1
            byte = index >> 3 if bit >= 0 else index
            fld, don = opt.get("fld", fld_of(donor)), opt.get("don", donor)
            m, src = opt.get("m", 1), opt.get("src", "eb")
            old = opt.get("old", values.get(target, 0))
            values[target] = value
            key = (fld, m, src, sid, tag, ip, byte, width, bit)
            s = sites.setdefault(key, {"same": False, "changes": 0, "n": 0, "last": None, "don": don})
            if old == value:
                emit, s["same"] = not s["same"], True
            else:
                emit = s["changes"] < 64
                s["changes"] += int(emit)
            if not emit:
                s["n"] += 1
                s["last"] = value
                continue
            if target == "Global.UInt16[0]":
                sc = value
            rows.append({"k": "w", "f": f, "p": 0, "m": m, "fld": fld, "don": don, "sc": sc, "src": src, "sid": sid,
                         "uid": sid, "lvl": 0, "ip": ip, "tag": tag, "add": 0, "byte": byte, "w": width, "bit": bit,
                         "old": old, "new": value, "same": int(old == value)})
    return rows


def visits(rows: list, members: dict) -> list:
    """The driver's ``visit`` rows for a rendered run: one each time the written field changes after the arm (field
    70's rows are the warp's, before any visit), at the frame of the visit's first row."""
    out, cur = [], None
    for x in rows:
        if x["k"] not in ("w", "r") or x["fld"] == 70 or x["fld"] == cur:
            continue
        cur = x["fld"]
        out.append({"k": "visit", "field": cur, "donor": place(cur, members), "visit": len(out) + 1,
                    "frame": x["f"], "sc": x["sc"]})
    return out


# ======================================================================== event edits
def _is(ev, site) -> bool:
    return ev[0] == "w" and tuple(ev[1:5]) == tuple(site[:4])


def drop(ev: list, *sites) -> list:
    return [x for x in ev if not any(_is(x, s) for s in sites)]


def after(ev: list, site, *new, nth: int = 0) -> list:
    """``new`` inserted after the ``nth`` event of ``site``."""
    hits = [i for i, x in enumerate(ev) if _is(x, site)]
    i = hits[nth] + 1
    return ev[:i] + list(new) + ev[i:]


def before(ev: list, site, *new) -> list:
    i = next(i for i, x in enumerate(ev) if _is(x, site))
    return ev[:i] + list(new) + ev[i:]


def edit(ev: list, test, fn) -> list:
    """Every event ``test`` accepts replaced by ``fn(event)``."""
    return [fn(x) if test(x) else x for x in ev]


def with_opt(x: tuple, **opt) -> tuple:
    return (*x[:-1], {**x[-1], **opt})


def upto(ev: list, site, *tail) -> list:
    """The run cut off after ``site``'s event (a drive that stopped there), then ``tail``."""
    i = next(i for i, x in enumerate(ev) if _is(x, site))
    return ev[:i + 1] + list(tail)


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


def make_session(tmp: Path, pred_path: Path, runs: list, scripts: dict) -> Path:
    """A session directory as O2Segment.run writes one. Each run: ``{side, events | rows, end?, why?, beats?, v?,
    cell?, by?, install?, end_state?, log?}`` -- ``log`` extra driver-log rows, or ``fn(rows, visits)`` giving them."""
    pred, sha = A.O2.load(pred_path)
    members = members_of(pred)
    d = tmp / f"s{len(list(tmp.iterdir()))}"
    (d / "scripts").mkdir(parents=True)
    for fid, data in scripts.items():
        (d / "scripts" / f"{fid}.eb").write_bytes(data)
    session = {"label": d.name, "predictions": str(pred_path), "predictions_sha256": sha,
               "predictions_version": pred["version"], "order": pred["order"], "budget": pred["budget"],
               "preflight": [[True, A.O2.title("P-TEXT"), TEXT_DEFECT]], "runs": []}
    beats_all = {b: True for b in pred["beats"]}
    for i, run in enumerate(runs, 1):
        side = run["side"]
        m = members if side == "F" else {}
        rows = run.get("rows") if run.get("rows") is not None else render(run["events"], side, members)
        name, log_name = f"run{i}_{side}.jsonl", f"run{i}_{side}_log.json"
        (d / name).write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
        vis = visits(rows, m)
        extra = run.get("log") or []
        extra = extra(rows, vis) if callable(extra) else extra
        end = run.get("end", "reached")
        beats = run.get("beats", dict(beats_all))
        outcome = {"end": end, "why": run.get("why", "field 61" if end == "reached" else "route: stopped"),
                   "void": None, "beats": beats, "pages": run.get("pages", ["p1", "p2"]), "timed": [],
                   "choices": [], "steps": [x for x in extra if x.get("k") == "step"], "overlays": [],
                   "forbidden": [], "end_state": run.get("end_state", dict(pred["end_state"]) if end == "reached"
                                                        else None)}
        (d / log_name).write_text(json.dumps({"outcome": outcome, "log": vis + extra}), encoding="utf-8")
        rec = {"i": i, "side": side, "start": pred["start"][side], "trace": name, "log": log_name, "end": end,
               "why": outcome["why"], "beats": beats}
        for k in ("v", "cell", "by", "install"):
            if run.get(k) is not None:
                rec[k] = run[k]
        session["runs"].append(rec)
    (d / A.SESSION_FILE).write_text(json.dumps(session), encoding="utf-8")
    return d


def result(checks) -> dict:
    return {w.split(":")[0]: ok for ok, w, _d in checks}


def _hit_frame(rows: list, site) -> int:
    """The frame of the first rendered row of ``site`` (the hit the evidence must precede)."""
    return next(x["f"] for x in rows if x["k"] == "w" and (x["sid"], x["tag"], x["ip"]) == tuple(site[1:4]))


# ======================================================================== the cases
CASES = []


def case(name, want_verdict, *, report_has=(), void=None, covered=None, **want):
    """Register a case: ``want_verdict`` the verdict's prefix, ``want`` checks by id (True PASS, False FAIL, None
    VOID), ``report_has`` substrings of the report, ``void`` ``{run index: [classes its VOID reasons must include]}``,
    ``covered`` ``{run index: bool}``."""
    def deco(fn):
        CASES.append((name, fn, want_verdict, want, tuple(report_has), void or {}, covered or {}))
        return fn
    return deco


def F(name):
    return {"O2-" + k.replace("_", "-"): v for k, v in name.items()}


@case("null-pair", "PROVEN")
def _(pred):
    return six(pred)


@case("fork-drops-SC1153", "NOT PROVEN", **F({"LADDER": False, "NULL": False, "STATE": False}))
def _(pred):
    return six(pred, f=lambda ev, n: drop(ev, SC1153))


@case("SC-out-of-order", "NOT PROVEN", **F({"LADDER": False, "NULL": True}))
def _(pred):
    def swap(ev, n):
        row = next(x for x in ev if _is(x, SC1151))
        return before(drop(ev, SC1151), SC1150, row)
    return six(pred, s=swap, f=swap)


@case("SC-seventh-write", "NOT PROVEN", **F({"LADDER": False}))
def _(pred):
    add = lambda ev, n: after(ev, SC1151, w(SC_DEBUG))                     # noqa: E731
    return six(pred, s=add, f=add)


@case("SC-wrong-site", "NOT PROVEN", **F({"LADDER": False, "NULL": True}))
def _(pred):
    """The 1151 rung written at the debug overwrite's site (105 e3 t1 ip497) instead of ip511, both sides: every
    value and every ``old`` as registered, only the JOINED key differs -- so only LADDER's key sequence can catch it
    (a reorder or a drop also breaks the olds). Not in 8's table."""
    moved = lambda ev, n: edit(ev, lambda x: _is(x, SC1151), lambda x: w(SC_DEBUG))      # noqa: E731
    return six(pred, s=moved, f=moved)


@case("SC-old-not-1000", "NOT PROVEN", **F({"LADDER": False}))
def _(pred):
    zero = lambda ev, n: edit(ev, lambda x: _is(x, SC1150), lambda x: with_opt(x, old=0))   # noqa: E731
    return six(pred, s=zero, f=zero)


@case("chain-out-of-order", "NOT PROVEN", **F({"CHAIN": False}))
def _(pred):
    def swap(ev, n):
        row = next(x for x in ev if _is(x, CH7))
        return before(drop(ev, CH7), CH6, row)
    return six(pred, s=swap, f=swap)


@case("chain-old-not-102", "NOT PROVEN", **F({"CHAIN": False}))
def _(pred):
    zero = lambda ev, n: edit(ev, lambda x: _is(x, CH1), lambda x: with_opt(x, old=0))      # noqa: E731
    return six(pred, s=zero, f=zero)


@case("chain-extra", "NOT PROVEN", **F({"CHAIN": False, "STATE": False}))
def _(pred):
    again = (103, 30, 1, 972, "Global.Int16[2]", 205)                      # 215 answered on the second visit too
    return six(pred, s=lambda ev, n: after(ev, CH6, w(again)))


@case("fork-extra-key", "NOT PROVEN", **F({"NULL": False, "LADDER": True, "CHAIN": True}))
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, BIT184, w(AMBIENT9)))


@case("stock-extra-key", "NOT PROVEN", **F({"NULL": False, "LADDER": True, "CHAIN": True}))
def _(pred):
    return six(pred, s=lambda ev, n: after(ev, BIT184, w(AMBIENT9)))


@case("writes-missing", "NOT PROVEN", **F({"WRITES": False, "NULL": True}))
def _(pred):
    gone = lambda ev, n: drop(ev, HERALD)                                   # noqa: E731
    return six(pred, s=gone, f=gone)


@case("unstable-outside-noise", "NOT PROVEN", **F({"STABLE": False, "STATE": False}))
def _(pred):
    return six(pred, s=lambda ev, n: after(ev, ILIA0, w(ILIA1)) if n == 0 else ev)


@case("hippaul-noise-only", "PROVEN", **F({"NULL": True, "STABLE": True, "STATE": True}))
def _(pred):
    hip = (103, 18, 1, 254, "Global.Byte[472]", 2)
    return six(pred, s=lambda ev, n: after(ev, HIPPAUL1, w(hip)) if n == 0 else ev,
               f=lambda ev, n: after(ev, HIPPAUL1, w(hip)) if n < 2 else ev)


@case("noise-wrong-site", "NOT PROVEN", **F({"STABLE": False, "STATE": False}))
def _(pred):
    at15 = (103, 18, 1, 218, "Global.Byte[472]", 2)                       # Hippaul's :=1 site, off 15, value 2
    return six(pred, f=lambda ev, n: after(ev, HIPPAUL1, w(at15)) if n < 2 else ev)


@case("noise-wrong-value", "NOT PROVEN", **F({"STABLE": False, "STATE": False}))
def _(pred):
    three = (103, 18, 1, 254, "Global.Byte[472]", 3)
    return six(pred, f=lambda ev, n: after(ev, HIPPAUL1, w(three)) if n < 2 else ev)


@case("start-dependent-equal", "PROVEN",
      report_has=(A.SCOPE_LINE, "Global.UInt16[19] |= at 100 e19 t1 ip1531: S [2], F [2]",
                  "after O1 it would write 1799", "Global.Byte[6] |= at 116 e2 t1 ip765: S [2], F [2]",
                  "after O1 it would write 3", "KNOWN-KIT-DEFECT uk: ships stock us"))
def _(pred):
    return six(pred)


@case("start-dependent-differs", "NOT PROVEN", **F({"NULL": False, "WRITES": False, "STATE": False}))
def _(pred):
    runs = six(pred, f=lambda ev, n: edit(ev, lambda x: _is(x, UINT19), lambda x: (*x[:6], 1799, x[7])))
    for run in runs:
        if run["side"] == "F":
            run["end_state"] = dict(pred["end_state"], **{"Global.UInt16[19]": 1799})
    return runs


@case("front-cut-residue", "PROVEN", **F({"START": True}))
def _(pred):
    return six(pred)


@case("start-residue-wrong", "NOT PROVEN", **F({"START": False}))
def _(pred):
    return six(pred, s=lambda ev, n: edit(ev, lambda x: x[0] == "r" and x[2] == 2, lambda x: r(70, 2, 0, 101)))


@case("front-cut-write", "NOT PROVEN", **F({"START": False, "NULL": True}))
def _(pred):
    in70 = ("w", 70, 3, 1, 40, "Global.Byte[13]", 2, {})                   # a store in field 70, before the start
    return six(pred, f=lambda ev, n: before(ev, START, in70))


@case("start-first-missing", "NOT PROVEN", **F({"START": False, "NULL": True}))
def _(pred):
    gone = lambda ev, n: drop(ev, START)                                    # noqa: E731
    return six(pred, s=gone, f=gone)


@case("residue-after-start", "NOT PROVEN", **F({"RESIDUE": False}))
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, START, r(100, 0, 232, 7)))


@case("end-cut", "PROVEN")
def _(pred):
    return six(pred, s=lambda ev, n: ev[:-1] + [w(x) for x in AFTER_61] + [ev[-1]])      # 61's rows, then off


@case("suppressed-new-value", "NOT PROVEN", **F({"STATE": False, "STABLE": False, "NULL": True, "LADDER": True,
                                                  "CHAIN": True}))
def _(pred):
    """O2-STATE (a)'s suppressed clause: in one F run, a count row (``c``) at 100's Byte[303]++ site whose ``last``
    is a value that site never emitted -- a counter whose changes ran past the 64 the engine emits. The emitted
    histories are all alike; only the suppressed set tells the runs apart. (A review finding moved the counts out of the
    history, where they sat after every write in line order; this proves the set that replaced them can fail.) It
    cannot be isolated: a count's never-emitted key is a digest key too, so STABLE reads the same run apart."""
    runs = six(pred)
    rows = render(runs[1]["events"], "F", members_of(pred))
    site = next(x for x in rows if x["k"] == "w" and (x["don"], x["sid"], x["tag"], x["ip"]) == (100, 19, 1, 1100))
    count = {"k": "c", "f": rows[-1]["f"] - 1, "p": 0, "sc": 1155, "n": 65, "last": 66,
             **{k: site[k] for k in ("m", "fld", "don", "src", "sid", "tag", "ip", "byte", "w", "bit")}}
    runs[1]["rows"] = rows[:-1] + [count, rows[-1]]
    return runs


@case("end-state-differs", "NOT PROVEN", **F({"STATE": False}))
def _(pred):
    runs = six(pred)
    runs[3]["end_state"] = dict(pred["end_state"], **{"Global.Byte[472]": 2})
    return runs


@case("seam-leak", "NOT PROVEN", **F({"SEAM": False, "WRITES": False, "NULL": True, "LADDER": True,
                                      "CHAIN": True}))
def _(pred):
    real = lambda ev, n: edit(ev, lambda x: x[0] == "w" and x[1] in (115, 116),              # noqa: E731
                              lambda x: with_opt(x, fld=x[1], don=x[1]))
    return six(pred, f=real)


@case("seam-masked-only", "NOT PROVEN", **F({"SEAM": False, "NULL": True}), covered={2: True})
def _(pred):
    """SEAM's seam record alone: one F run steps from member(103) into REAL 103, whose only write there is its
    MASKED Main_Init store (Bit[191] := 0, 103 e0 t0 ip26), then back into its member -- a Seam other than
    member(116) -> 61 with no seam key (a masked site is never keyed), so only the seam record shows the chain was
    left. (Not in 8's table: seam-leak and forbidden-on-seam both write seam keys as well.)"""
    real103 = (103, 0, 0, 26, "Global.Bit[191]", 0)
    return six(pred, f=lambda ev, n: after(ev, HIPPAUL1, w(real103, fld=103, don=103)) if n == 0 else ev)


def _jack(pred, *, backed_runs: tuple, rows_runs: tuple) -> list:
    """F runs (by index within the side) with Jack's mugging row in 105; ``backed_runs`` also carry a watch sample
    of him within his range_r before it."""
    runs = six(pred, f=lambda ev, n: after(ev, SC1152, w(JACK)) if n in rows_runs else ev)
    k = 0
    for run in runs:
        if run["side"] != "F":
            continue
        if k in backed_runs:
            def log(rows, vis):
                f = _hit_frame(rows, JACK)
                return [{"k": "watch", "frame": f - 4, "control": True, "x": -244.0, "z": 2562.0, "field": 31225,
                         "donor": 105, "objects": [{"sid": 7, "x": -250.0, "z": 2800.0, "range_r": 299.0,
                                                    "talk_r": None, "dist": 238.1}]}]
            run["log"] = log
        k += 1
    return runs


@case("jack-one-backed", "PROVEN", **F({"COVER": True, "FORBIDDEN": True}), void={2: ["A-FORBIDDEN"]},
      covered={2: False, 4: True, 6: True})
def _(pred):
    return _jack(pred, backed_runs=(0,), rows_runs=(0,))


@case("jack-one-unbacked", "NOT PROVEN", **F({"FORBIDDEN": False}), covered={2: True})
def _(pred):
    return _jack(pred, backed_runs=(), rows_runs=(0,))


@case("jack-two-backed", "VOID", **F({"COVER": None, "FORBIDDEN": True, "VOID_ASYM": True}),
      void={2: ["A-FORBIDDEN"], 4: ["A-FORBIDDEN"]})
def _(pred):
    return _jack(pred, backed_runs=(0, 1), rows_runs=(0, 1))


def _plaque_log(rows, vis, *, fld):
    """A Confirm with control 122u from the plaque hot-spot (600, -272), in its place and visit, before its rows."""
    f = _hit_frame(rows, PLAQUE[0])
    visit = [v for v in vis if v["field"] == fld and v["frame"] <= f][-1]["visit"]
    at = {"frame": f - 6, "control": True, "x": 600.0, "z": -150.0}
    return [{"k": "press", "why": "confirm", "field": fld, "donor": 103, "visit": visit, "sc": 1000, "pre": at,
             "post": dict(at, frame=f - 4), "near": []}]


@case("hotspot-backed", "PROVEN", **F({"FORBIDDEN": True}), void={1: ["A-FORBIDDEN"]}, covered={1: False})
def _(pred):
    runs = six(pred, s=lambda ev, n: after(ev, HIPPAUL1, *[w(p) for p in PLAQUE]) if n == 0 else ev)
    runs[0]["log"] = lambda rows, vis: _plaque_log(rows, vis, fld=103)
    return runs


@case("hotspot-unbacked", "NOT PROVEN", **F({"FORBIDDEN": False}), covered={2: True})
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, HIPPAUL1, *[w(p) for p in PLAQUE]) if n == 0 else ev)


@case("dormant-card", "NOT PROVEN", **F({"FORBIDDEN": False, "NULL": False}))
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, SC1154, *[w(c) for c in CARD]))


@case("forbidden-masked", "NOT PROVEN", **F({"FORBIDDEN": False, "MASKED": False, "NULL": True}))
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, SC1154, *[w(k) for k in KUPO_MASKED]) if n == 0 else ev)


@case("forbidden-on-seam", "NOT PROVEN", **F({"FORBIDDEN": False, "SEAM": False}), covered={2: True})
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, HIPPAUL1, *[w(p, fld=103, don=103) for p in PLAQUE]) if n == 0
               else ev)


@case("off-route-by-a-step", "PROVEN", void={1: ["A-FORBIDDEN", "V11"]}, covered={1: False})
def _(pred):
    runs = six(pred, s=lambda ev, n: upto(ev, EXIT101, *[w(x) for x in IN_112], e("off", 112)) if n == 0 else ev)

    def log(rows, vis):
        f = _hit_frame(rows, IN_112[0])
        return [{"k": "step", "field": 101, "donor": 101, "sc": 1000, "visit": 2, "n": 0, "kind": "cross",
                 "name": "Main Street B's west exit (e16)", "attempt": 1, "outcome": "void", "frame0": f - 60,
                 "frame": f - 2, "landed": 112, "lost": None, "flip_frame": f - 20, "v": "V11", "by": "driver",
                 "why": "the crossing to 102 landed in 112 (place 112)"}]
    runs[0].update(end="void", why="route: the crossing to 102 landed in 112 (place 112)", v="V11",
                   cell=[101, 1000], by="driver", log=log)
    return runs


@case("off-route-scripted", "NOT PROVEN", **F({"FORBIDDEN": False, "VOID_ASYM": False}))
def _(pred):
    runs = six(pred, f=lambda ev, n: upto(ev, SC1152, *[w(x, fld=112, don=112) for x in IN_112], e("off", 112))
               if n == 0 else ev)
    runs[1].update(end="void", why="route: left the route: entered 112 (place 112)", v="V11", cell=[112, 1152],
                   by="game")
    return runs


@case("void-asym-all", "NOT PROVEN", **F({"VOID_ASYM": False, "COVER": None}))
def _(pred):
    runs = six(pred, f=lambda ev, n: upto(ev, ILIA0, e("off", 106)))
    for run in runs:
        if run["side"] == "F":
            run.update(end="void", why="route: SC never reached 1153 within 90s (it reads 1152)", v="V8",
                       cell=[106, 1152], by="game")
    return runs


@case("void-asym-one", "NOT PROVEN", **F({"VOID_ASYM": False, "COVER": True}))
def _(pred):
    runs = six(pred, f=lambda ev, n: upto(ev, SC1150, e("off", 104)) if n == 0 else ev)
    runs[1].update(end="void", why="route: control held in 31224 (place 104) at SC 1150, where the table has no "
                                   "entry", v="V4", cell=[104, 1150], by="game")
    return runs


@case("void-asym-driver-all", "NOT PROVEN", **F({"VOID_ASYM": False, "COVER": None}))
def _(pred):
    """VOID-ASYM's rule (b) alone: every F run VOID in ONE driver class (a lost race at the lookout, V7), the S runs
    covered -- rule (a) reads game classes only, so only (b) can fail this. (Not in 8's table: its void-asym-all is
    game-attributed, so (a) fails it too, and (b) went unproven.)"""
    runs = six(pred, f=lambda ev, n: upto(ev, SC1152, e("off", 105)))
    for run in runs:
        if run["side"] == "F":
            run.update(end="void", why="route: step leave the lookout by the south exit (e11) (leave_now) "
                                       "interrupted 1 times, over its 0", v="V7", cell=[105, 1152], by="driver")
    return runs


@case("void-asym-stock-one", "NOT PROVEN", **F({"VOID_ASYM": False, "COVER": True}))
def _(pred):
    """VOID-ASYM's rule (a) in the other direction: one S run VOID in a game class (215 re-offered at SC 1150, V1)
    that no F run shows. (Not in 8's table, which tests (a) on the F side only.)"""
    runs = six(pred, s=lambda ev, n: upto(ev, CH6, e("off", 103)) if n == 0 else ev)
    runs[0].update(end="void", why="route: choice in 103 with no rule: ['', 'eek into the ticket booth', 'Cancel']",
                   v="V1", cell=[103, 1150], by="game")
    return runs


@case("mismatched", "PROVEN", void={2: ["A-MISMATCH"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    return six(pred, f=lambda ev, n: edit(ev, lambda x: x[0] == "w" and x[1] == 101,
                                          lambda x: with_opt(x, don=31221)) if n == 0 else ev)


@case("beat-missing", "VOID", **F({"COVER": None, "VOID_ASYM": True}), void={1: ["A-BEATS"], 3: ["A-BEATS"]})
def _(pred):
    runs = six(pred)
    for run in (runs[0], runs[2]):
        run["beats"] = dict({b: True for b in pred["beats"]}, climbed=False)
    return runs


@case("no-start-row", "PROVEN", void={1: ["A-NOSTART"]}, covered={1: False})
def _(pred):
    runs = six(pred)
    runs[0]["events"] = base_events()[:4] + [e("off", 70)]
    return runs


@case("trace-without-off", "VOID", **F({"COVER": None}))
def _(pred):
    runs = six(pred)
    for run in (runs[0], runs[2]):
        run["events"] = run["events"][:-1]
    return runs


@case("install-changed", "VOID", **F({"COVER": None}))
def _(pred):
    runs = six(pred)
    for run in (runs[1], runs[3]):
        run["install"] = "during the run: 1 changed: override70"
    return runs


@case("join-failure", "NOT PROVEN", **F({"JOIN": False}))
def _(pred):
    off = (100, 19, 1, 1579, "Global.Byte[18]", 1)                         # one byte into the ip1578 store
    add = lambda ev, n: after(ev, (100, 19, 1, 1578), w(off))               # noqa: E731
    return six(pred, s=add, f=add)


# ======================================================================== the unit cases (no session)
def unit_span_selector() -> tuple:
    """LADDER's byte-span selector: a Global.Byte[1] store is selected (it overlaps SC's bytes 0-1) and fails the
    ladder by name; a Byte[4] store is not selected. No real route site writes bytes 0-3 through another width."""
    rows = T.parse_text("".join(json.dumps(x) + "\n" for x in render(
        [e("arm", 70), ("w", 100, 0, 0, 30, "Global.Byte[1]", 7, {}), ("w", 100, 0, 0, 57, "Global.Byte[4]", 7, {}),
         e("off", 100)], "S", {})))
    sel = A.span_rows(rows, [0, 1])
    bad = A.span_sequence(rows, {}, [0, 1], [], 1000)
    ok = [x.target for x in sel] == ["Global.Byte[1]"] and any("Global.Byte[1]=7" in b and "has no key" in b
                                                              for b in bad)
    return ok, f"selected {[x.target for x in sel]}; {bad[:1]}"


def unit_span_count_row(pred: dict, stock) -> tuple:
    """LADDER on a run whose six rungs are emitted exactly as registered, plus a ``c`` row at the epoch's close
    counting a SUPPRESSED store at the 1154 rung's site (the engine counts a site's stores past its 64 value changes
    and its first same-value row: StoryTrace.cs:383-400): visible only there, so it fails the ladder by name, alone.
    No real route rung repeats, so this is no session case (not in 8's table)."""
    rows = render(base_events(), "S", {})
    sc = next(x for x in rows if x["k"] == "w" and (x["sid"], x["tag"], x["ip"]) == SC1154[1:])
    count = {"k": "c", "f": rows[-1]["f"] - 1, "p": 0, "sc": 1155, "n": 1, "last": 1154,
             **{k: sc[k] for k in ("m", "fld", "don", "src", "sid", "tag", "ip", "byte", "w", "bit")}}
    rows = T.parse_text("".join(json.dumps(x) + "\n" for x in rows[:-1] + [count, rows[-1]]))
    kept, _at, _pre = A.cut_at_start(rows, 100, {})
    kept, _end = A.cut_at_end(kept, [61], {})
    d = T.digest("S#1", kept, scripts=stock)
    bad = A.span_sequence(kept, A.row_keys(d), pred["sc_bytes"], pred["ladder"], pred["scenario"])
    clean = A.span_sequence([x for x in kept if x.k != "c"], A.row_keys(d), pred["sc_bytes"], pred["ladder"],
                            pred["scenario"])
    ok = len(bad) == 1 and "suppressed" in bad[0] and clean == []
    return ok, f"{bad[:1]}; without the count row: {clean}"


def _stock7() -> dict:
    return {L: f"[{L}] block 33".encode("utf-8") for L in ("us", "uk", "fr", "gr", "it", "es", "jp")}


def unit_text_defect() -> tuple:
    s = _stock7()
    ok, lines = A.text_rule(s, dict(s, uk=s["us"]), "us")
    good = ok and sum(1 for x in lines if x.startswith("KNOWN-KIT-DEFECT")) == 1
    return good, A.text_detail(lines)


def unit_text_session() -> tuple:
    s = _stock7()
    ok, lines = A.text_rule(s, dict(s, us=s["uk"]), "us")
    return (not ok and any(x.startswith("FAIL us") for x in lines)), A.text_detail(lines)


def unit_text_garbage() -> tuple:
    s = _stock7()
    ok, lines = A.text_rule(s, dict(s, fr=b"no language's text"), "us")
    return (not ok and any(x.startswith("FAIL fr") for x in lines)
            and not any(x.startswith("KNOWN-KIT-DEFECT") for x in lines)), A.text_detail(lines)


def unit_state_history(pred: dict, stock, scripts: dict, tmp: Path, path: Path) -> tuple:
    """O2-STATE (a)'s reading of a base run: Byte[8]'s history is its EMITTED writes in line order and ends with 116's
    := 0, the value handed to 61 -- 103's second-visit := 125, a same-value repeat the engine only COUNTS (a ``c`` row
    written at the epoch's close), is no write after it -- and that count's key is its site's emitted one, so it drops
    out of the suppressed set too. Break: fold the count rows into the history in line order (it then ends 125)."""
    d = make_session(tmp, path, six(pred)[:1], scripts)
    run = A.O2.read_session(d, pred, stock=stock)[0]
    h, s = A.O2.history(run, pred), A.O2.suppressed(run, pred)
    counted = [x for x in run["rows"] if x.k == "c" and x.target == "Global.Byte[8]"]
    got = [(k.donor, k.value) for k in h.get("Global.Byte[8]", [])]
    ok = got == [(100, 125), (103, 125), (115, 125), (116, 125), (116, 0)] and len(counted) == 1 and s == {}
    return ok, f"Byte[8] {got}; {len(counted)} count row(s); suppressed {s}"


def _synthetic_text(tmp: Path, langs) -> tuple:
    """``(stock, build root)``: seven distinct stock texts, and a build shipping ``langs`` of them, each its own."""
    stock = {L: f"[{L}] block {A.TEXT_BLOCK}".encode("utf-8") for L in ("us", "uk", "fr", "gr", "it", "es", "jp")}
    root = tmp / ("text-" + "-".join(langs))
    for L in langs:
        p = root / "FF9_Data" / "embeddedasset" / "text" / L / "field" / f"{A.TEXT_BLOCK}.mes"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(stock[L])
    return stock, root


def _registering(tmp: Path, name: str, fids) -> Path:
    root = tmp / name
    root.mkdir(parents=True, exist_ok=True)
    (root / "DictionaryPatch.txt").write_text("".join(f"FieldScene {f} 11 X_{f} X_{f} {f}\n" for f in fids),
                                              encoding="utf-8")
    return root


def _memo(fn):
    got: dict = {}

    def read(key):
        if key not in got:
            got[key] = fn(key)
        return got[key]
    return read


def _step(p: dict, donor: int, sc: int, n: int = 0) -> dict:
    return next(c for c in p["table"] if (c["donor"], c["sc"]) == (donor, sc))["steps"][n]


def _key(p: dict, name: str, what: str) -> dict:
    return next(k for k in p[name] if what in k["what"])


#: The offline checks' mutants (research/o2_design.md 6.1; the review's finding: KEYS, REGIONS, GOALS, TEXT's
#: missing-language clause and P-RECOVERY had none). Each is ``(name, check, mutate, clause)``: the DRAFT, deep-copied,
#: one thing changed; ``check`` must then read FAIL -- after every check has read PASS on the unchanged draft -- and its
#: detail must hold ``clause``, the words of the clause the mutant breaks (so it cannot pass by tripping another).
OFFLINE_MUTANTS = [
    ("keys-ladder-value", "KEYS", lambda p: p["ladder"][0].update(value=1151), "the bytes give 1150, the key says 1151"),
    ("keys-wrong-op", "KEYS", lambda p: _key(p, "writes", "100 Byte[8] := 125").update(op="|="),
     "is not Global.Byte[8] |= ..."),
    ("keys-or-value", "KEYS", lambda p: _key(p, "writes", "UInt16[19] |= 2").update(value=3),
     "the bytes give 2, the key says 3"),
    ("keys-and-value", "KEYS", lambda p: _key(p, "writes", "&= 8190").update(value=1043),
     "the bytes give 1042, the key says 1043"),
    ("keys-post-plus-value", "KEYS", lambda p: _key(p, "writes", "Byte[303]++").update(value=2),
     "the bytes give 1, the key says 2"),
    ("keys-prior-unknown", "KEYS", lambda p: _key(p, "writes", "Byte[303]++").update(prior="100/19/1/9999"),
     "names no registered prior"),
    ("keys-noise-ip", "KEYS", lambda p: p["noise"][0].update(ip=255), "noise: Hippaul's :=2"),
    ("keys-masked-key", "KEYS", lambda p: p["writes"].append(dict(p["start_first"], what="a masked key")),
     "lies in the story-noise mask"),
    ("keys-forbidden-site", "KEYS", lambda p: p["forbidden_sites"][0].update(ip=730), "forbidden_sites: Jack's card"),
    ("regions-point", "REGIONS", lambda p: p["regions"]["100.e15"]["points"][0].__setitem__(0, -366),
     "100.e15: the bytes' first SetRegion is"),
    ("regions-exit-to", "REGIONS", lambda p: p["regions"]["100.e15"].update(to=102), "100.e15: scan_gateways gives"),
    ("regions-exit-entrance", "REGIONS", lambda p: p["regions"]["100.e15"].update(entrance=201),
     "100.e15: scan_gateways gives"),
    ("regions-exit-gate", "REGIONS", lambda p: p["regions"]["101.e17"].update(face_gate=None),
     "101.e17: scan_gateways gives"),
    ("regions-walkin-live", "REGIONS", lambda p: p["regions"]["105.e12"].update(live=[1150, 1153]),
     "105.e12: its tag 2 does not open with the guard"),
    ("regions-dormant", "REGIONS",
     lambda p: p["regions"]["115.e15"].update(role="dormant", entrances=[213, 214, 215]), "115.e15: "),
    ("regions-benign", "REGIONS", lambda p: p["regions"]["100.e15"].update(role="benign"),
     "stores to gEventGlobal or warps"),
    ("regions-confirm-tag3", "REGIONS", lambda p: p["regions"]["103.e28"]["tag3"].update(ip=96),
     "103.e28: its tag 3 at ip96"),
    ("regions-hotspot-dropped", "REGIONS", lambda p: p["hotspots"]["103"].pop(1),
     "hot-spot 103 e20 (600, -272) n 50: in the bytes, not in the predictions"),
    ("regions-hotspot-moved", "REGIONS", lambda p: p["hotspots"]["103"][1].update(x=601),
     "hot-spot 103 e20: the bytes give"),
    ("regions-exit-unregistered", "REGIONS", lambda p: p["regions"].pop("106.e13"),
     "106.e13: a gateway (-> 113, entrance 211) in the bytes, not registered as an exit"),
    ("goals-off-floor", "GOALS", lambda p: _step(p, 100, 1000).update(goal=[0, 9000]), "off the floor"),
    ("goals-outside-target", "GOALS", lambda p: _step(p, 102, 1000).update(goal=[865, 2525]),
     "goal depth None in 102.e8"),
    ("goals-start-on-hotspot", "GOALS", lambda p: _step(p, 103, 1000).update(start=[600, -150]),
     "beyond hot-spot e20's reach"),
    ("goals-until", "GOALS", lambda p: _step(p, 116, 1155).update(until={"x_le": 500}), "fails its until"),
    ("goals-confirm-depth", "GOALS", lambda p: _step(p, 115, 1154).update(min_depth=60), "< min_depth 60"),
    ("goals-malformed-step", "GOALS", lambda p: _step(p, 100, 1000).pop("to"), "a cross step needs ['to']"),
    ("goals-visit-order", "GOALS", lambda p: p.update(visits=[100, 101, 102, 103, 104, 103, 106, 105, 115, 116]),
     "never goes next from 103"),
]


def unit_offline_mutants(pred: dict, stock, tmp: Path) -> list:
    """``[(name, ok, detail)]``: O2-KEYS, O2-REGIONS and O2-GOALS read PASS on the draft, then FAIL on each of
    :data:`OFFLINE_MUTANTS`; O2-TEXT reads PASS with all seven languages shipped and FAILS with one missing (its
    missing-language clause: the rule itself passes on the six that are there); P-RECOVERY passes with 4600 registered
    in a folder and FAILS with it registered in none. The text and the folders are synthetic; KEYS and REGIONS read
    the stock scripts, GOALS the install's stock walkmeshes (read-only), both memoised."""
    from ff9mapkit import extract
    walkmesh = _memo(extract.stock_walkmesh)
    checks = {"KEYS": lambda p: A.O2.keys_check(p, stock), "REGIONS": lambda p: A.O2.regions_check(p, stock),
              "GOALS": lambda p: A.O2.goals_check(p, walkmesh=walkmesh)}
    out = []
    base = {cid: fn(pred) for cid, fn in checks.items()}
    out.append(("offline-draft-passes", all(r[0] is True for r in base.values()),
                "; ".join(f"{cid} {'PASS' if r[0] else 'FAIL: ' + r[2][:80]}" for cid, r in base.items())))
    for name, cid, mutate, clause in OFFLINE_MUTANTS:
        p = copy.deepcopy(pred)
        mutate(p)
        ok, _what, detail = checks[cid](p)
        caught = ok is False and clause in detail
        out.append((name, caught, f"{cid} {'FAIL' if ok is False else 'PASS (not caught)'}"
                                  + ("" if caught or ok is not False else f" -- not by {clause!r}")
                                  + f": {detail[:120]}"))
    stock_text, root7 = _synthetic_text(tmp, ("us", "uk", "fr", "gr", "it", "es", "jp"))
    ok7 = A.O2.text_check(pred, root7, stock_text=stock_text)
    _s, root6 = _synthetic_text(tmp, ("us", "uk", "fr", "gr", "it", "es"))
    ok6 = A.O2.text_check(pred, root6, stock_text=stock_text)
    rule6 = A.text_rule(stock_text, A.shipped_text(root6))[0]
    out.append(("text-missing-language", ok7[0] is True and rule6 is True and ok6[0] is False
                and "ships no jp/field" in ok6[2], f"all 7 {ok7[0]}; 6 by the rule {rule6}, by O2-TEXT {ok6[0]}: "
                                                   f"{ok6[2][:100]}"))
    rec = [A.O2.preflight_extra(pred, roots)[1] for roots in ([_registering(tmp, "has4600", [30000, 4600])],
                                                              [_registering(tmp, "no4600", [30000, 4601])])]
    out.append(("p-recovery-unregistered", rec[0][0] is True and rec[1][0] is False,
                f"registered: {rec[0][0]} ({rec[0][2]}); not: {rec[1][0]} ({rec[1][2]})"))
    return out


def unit_trace_summary(pred: dict, stock) -> tuple:
    """trace_summary (research/o2_design.md 7.2) on a base S run: the six rungs and the twelve entrances in order,
    every registered route key present (the noise and the forbidden sites absent), no unregistered key, no join
    failure, the warp's three residue rows before the start."""
    rows = T.parse_text("".join(json.dumps(x) + "\n" for x in render(base_events(), "S", {})))
    t = A.trace_summary(rows, pred, stock=stock)
    reg = {k: (sum(1 for x in v if x["present"]), len(v)) for k, v in t["registered"].items()}
    want = {"ladder": (6, 6), "chain": (12, 12), "writes": (26, 26), "start_dependent": (2, 2), "noise": (0, 1),
            "forbidden_sites": (0, 2)}
    ok = ([x["new"] for x in t["sc"]] == [k["value"] for k in pred["ladder"]]
          and [x["new"] for x in t["entrance"]] == [k["value"] for k in pred["chain"]]
          and reg == want and t["unregistered"] == [] and t["failures"] == []
          and [x[1:] for x in t["residue_before"]] == [[0, 0, 232], [1, 0, 3], [2, 0, 102]]
          and t["watched"] == {"hippaul_254": False, "ilia_165": False})
    return ok, f"registered {reg}; unregistered {len(t['unregistered'])}; failures {len(t['failures'])}"


# ======================================================================== the run
def _prepare(pred_path: Path | None, tmp: Path) -> Path:
    if pred_path is not None:
        return Path(pred_path)
    path = tmp / "o2_predictions_draft.json"
    path.write_bytes((json.dumps(A.draft_predictions(), indent=1, sort_keys=True) + "\n").encode("utf-8"))
    return path


def run_cases(pred_path: Path | None = None) -> int:
    from ff9mapkit.content.verbatim import remap_fields
    stock = T.stock_script_source()
    fails, total = 0, 0
    cols = ("O2-FROZEN", "O2-COVER", "O2-FORBIDDEN", "O2-VOID-ASYM", "O2-START", "O2-LADDER", "O2-CHAIN",
            "O2-RESIDUE", "O2-WRITES", "O2-NULL", "O2-STABLE", "O2-SEAM", "O2-MASKED", "O2-STATE", "O2-JOIN")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pdir = tmp / "pred"
        pdir.mkdir()
        sdir = tmp / "sessions"
        sdir.mkdir()
        path = _prepare(pred_path, pdir)
        pred, _sha = A.O2.load(path)
        members = members_of(pred)
        retarget = {dn: f for f, dn in members.items()}
        scripts = {fid: remap_fields(stock(dn).data, retarget) for fid, dn in members.items()}
        for name, fn, want_verdict, want, report_has, want_void, want_cov in CASES:
            total += 1
            d = make_session(sdir, path, fn(copy.deepcopy(pred)), scripts)
            checks, report = A.O2.analyse(d, stock=stock)
            got = result(checks)
            v = verdict(checks)
            ok = v.startswith(want_verdict) and all(got.get(k) is x for k, x in want.items())
            missing = [s for s in report_has if s not in report]
            ok = ok and not missing
            runs = A.O2.read_session(d, pred, stock=stock) if (want_void or want_cov) else []
            bad_runs = []
            for i, classes in want_void.items():
                have = {x["class"] for x in runs[i - 1]["void"]}
                if not set(classes) <= have:
                    bad_runs.append(f"run {i} VOID classes {sorted(have)}, want {classes}")
            for i, cov in want_cov.items():
                if runs[i - 1]["covered"] is not cov:
                    bad_runs.append(f"run {i} covered {runs[i - 1]['covered']}, want {cov}")
            ok = ok and not bad_runs
            fails += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name:26} {v[:52]:52} "
                  + " ".join(f"{k[3:]}={'P' if got.get(k) is True else 'F' if got.get(k) is False else 'V'}"
                             for k in cols[1:]))
            if not ok:
                if missing:
                    print(f"     report lacks: {missing}")
                for b in bad_runs:
                    print(f"     {b}")
                print("     " + "\n     ".join(f"{w} :: {dd[:260]}" for _ok, w, dd in checks))
        # O2-FROZEN: the predictions changed after the session recorded them
        total += 1
        copy_path = pdir / "pred_copy.json"
        copy_path.write_bytes(path.read_bytes())
        d = make_session(sdir, copy_path, six(pred), scripts)
        copy_path.write_bytes(path.read_bytes() + b" ")
        checks, _rep = A.O2.analyse(d, stock=stock)
        v = verdict(checks)
        ok = result(checks).get("O2-FROZEN") is False and v.startswith("NOT PROVEN")
        fails += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {'predictions-changed':26} {v[:52]}")
        for name, fn in (("span-selector", unit_span_selector),
                         ("span-count-row", lambda: unit_span_count_row(pred, stock)),
                         ("text-rule-defect", unit_text_defect),
                         ("text-rule-session", unit_text_session), ("text-rule-garbage", unit_text_garbage),
                         ("trace-summary", lambda: unit_trace_summary(pred, stock)),
                         ("state-history", lambda: unit_state_history(pred, stock, scripts, sdir, path))):
            total += 1
            ok, detail = fn()
            fails += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name:26} (unit) {detail[:150]}")
        for name, ok, detail in unit_offline_mutants(pred, stock, tmp):
            total += 1
            fails += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name:26} (unit) {detail[:150]}")
    print(f"\n{total - fails}/{total} cases as registered")
    return 1 if fails else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--predictions", type=Path, default=None,
                    help="a frozen predictions file (default: the draft, written to a temporary file)")
    sys.exit(run_cases(ap.parse_args().predictions))
