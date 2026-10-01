"""O3's analysis, driven on SYNTHETIC sessions (research/o3_design.md section 8): every registered check must read
PASS on the null pair and FAIL (or VOID) on the mutant built to break it -- a check that cannot fail is not a check.

    py studies/story-trace/o3_dryrun.py [--predictions studies/story-trace/o3_predictions_v1.json]

Without --predictions it writes the DRAFT (o3_prima_vista.draft_predictions) to a temporary predictions file --
nothing is frozen until the lead's rehearsals -- and runs every case against that.

Each case writes a session directory the way the session does (o3_session.json, the members' scripts, one trace and
one driver log per run) and runs :meth:`o3_prima_vista.O3Segment.analyse` on it. The rows are real store sites of the
stock bytes of 61, 62, 63 and 64 (every field row joins but the join-failure case's), shifted onto O1's member ids on
the F side (``fld`` = member, ``don`` = donor; 64 stays 64: the seam), and EMITTED as the engine emits them: a
same-value store once per site, a value change up to 64 times, the rest counted into a ``c`` row at the epoch's close
(StoryTrace.cs:383-400). Battle 338's rows are King Leo's AI store (m 2, e1 t1 ip267, Byte[206]) at the battle's
field, 70 random values a run -- 64 emitted, the rest counted -- between 62's ip1285 and 63's ip22. A run's driver log
carries its visit rows, its battle row (2.3 step 6: row 0, scene 338, the drive's epoch + 1, result 2, landed 63 /
31213) and its end row; ``battle_epoch0`` and the beats are its outcome's.

O3's ``case()`` is EXACT, which O2's is not: every check a case does not name must read PASS -- a case naming COVER V
expects every core check VOID -- so each NOT PROVEN row names EVERY check it fails, "alone" is a registered fact, and
an unforeseen co-failure is a miss. A LANDING or BATTLE case also registers the clause its detail must name.

The units read the install read-only (the stock scripts and walkmeshes, battle 338's scene, O1's build is not read):
O3-SCENE and O3-CENSUS on the install and on one-change copies of the draft, the battle row's strictness, the legacy
build rule, and the offline mutants of O3-KEYS, O3-REGIONS and P-DONOR. The launch's readers (P-DONOR-LOG, P-LAUNCH),
P-STOCK-BATTLE and P-SETTINGS run on synthetic logs, folders and inis. The movie-skip A/B (``--skip-ab``, PLAN.md "Movie
skip (opt-in)") runs on synthetic stock runs: equal runs read EQUIVALENT; a key dropped, a history reordered and a skip
run that played its movie out each read NOT EQUIVALENT.
"""
from __future__ import annotations

import argparse
import copy
import datetime as _dt
import json
import os
import random
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import o3_prima_vista as P                                                 # noqa: E402
import o2_alexandria as A                                                  # noqa: E402
import segment_drive as SD                                                 # noqa: E402
import segment_trace as ST                                                 # noqa: E402
from ff9mapkit import storytrace as T                                      # noqa: E402
from segment_trace import members_of, place, verdict                       # noqa: E402

# ======================================================================== real store sites (donor, sid, tag, ip, target, value)
S61 = [(61, 0, 0, 22, "Global.Bit[191]", 0), (61, 0, 0, 49, "Global.Bit[184]", 0),
       (61, 0, 0, 57, "Global.Int16[9]", -1), (61, 0, 0, 119, "Global.Byte[13]", 0),
       (61, 0, 0, 138, "Global.Int16[11]", -1), (61, 0, 0, 200, "Global.Byte[14]", 0),
       (61, 2, 1, 752, "Global.Byte[8]", 125), (61, 1, 1, 363, "Global.Int16[2]", 100)]
S62 = [(62, 0, 0, 26, "Global.Bit[191]", 0), (62, 0, 0, 53, "Global.Bit[184]", 0),
       (62, 0, 0, 61, "Global.Int16[9]", -1), (62, 0, 0, 123, "Global.Byte[13]", 0),
       (62, 0, 0, 142, "Global.Int16[11]", -1), (62, 0, 0, 204, "Global.Byte[14]", 0),
       (62, 4, 1, 319, "Global.UInt16[21]", 3585), (62, 4, 1, 603, "Global.Byte[303]", 0),
       (62, 4, 1, 637, "Global.Byte[303]", 1), (62, 4, 1, 659, "Global.Byte[303]", 2),
       (62, 4, 1, 681, "Global.Byte[303]", 3), (62, 4, 1, 703, "Global.Byte[303]", 4),
       (62, 4, 1, 1034, "Global.Byte[4]", 0), (62, 4, 1, 1085, "Global.Byte[4]", 0),
       (62, 4, 1, 1093, "Global.Byte[17]", 0), (62, 4, 1, 1101, "Global.Byte[18]", 1),
       (62, 4, 1, 1285, "Global.Int16[2]", 0)]
S63 = [(63, 0, 0, 22, "Global.Bit[191]", 0), (63, 0, 0, 49, "Global.Bit[184]", 0),
       (63, 0, 0, 57, "Global.Int16[9]", -1), (63, 0, 0, 119, "Global.Byte[13]", 0),
       (63, 0, 0, 138, "Global.Int16[11]", -1), (63, 0, 0, 200, "Global.Byte[14]", 0),
       (63, 14, 1, 805, "Global.Byte[8]", 125), (63, 4, 1, 820, "Global.Int16[2]", 100)]
END64 = (64, 0, 0, 22, "Global.Bit[191]", 0)
AFTER64 = [(64, 0, 0, 49, "Global.Bit[184]", 0), (64, 0, 0, 57, "Global.Int16[9]", -1)]
START61, BIT184_61, MUSIC61, B8_61, CH61 = S61[0], S61[1], S61[3], S61[6], S61[7]
B18_62, CH62 = S62[15], S62[16]
B4_1034 = S62[12]
FRESH63, MAIN63, B8_63, CH63 = S63[0], S63[:6], S63[6], S63[7]
BIT184S = [S61[1], S62[1], S63[1]]
#: Off the route, each a real store: 61's and 63's error path; 61's and 62's dead branches; 62's return from a
#: battle that came back (ip1345).
ERR61_97, ERR61_349 = (61, 0, 0, 97, "Global.Byte[13]", 9), (61, 0, 0, 349, "Global.Byte[13]", 0)
ERR63_97 = (63, 0, 0, 97, "Global.Byte[13]", 9)
DEAD61_130 = (61, 0, 0, 130, "Global.Byte[13]", 1)
DEAD62_1023 = (62, 4, 1, 1023, "Global.Byte[4]", 1)
RET62 = (62, 4, 1, 1345, "Global.Int16[2]", 0)
#: Battle sites (m 2): King Leo's (TH_E002 e1 t1 ip267), TH_E001's other Byte[206] site (e0 t1 ip93) and its
#: Byte[199] (e0 t1 ip213) -- O1's battle's, never 338's.
LEO = (62, 1, 1, 267, "Global.Byte[206]")
E001_93 = (62, 0, 1, 93, "Global.Byte[206]", 77)
E001_199 = (62, 0, 1, 213, "Global.Byte[199]", 2)
#: The drive's battle epoch at its start (any number: only deltas mean anything).
EPOCH0 = 7
TEXT_DEFECT = ("KNOWN-KIT-DEFECT 1, FAIL 0, 6 byte-equal of 7 languages | KNOWN-KIT-DEFECT uk: ships stock us "
               "(3a6f3246c2; stock uk 7ac9f17435): the build predates the per-language text pick (aa627d52): "
               "regenerate it, or repair its sidecars with tools/refresh_verbatim_text.py")
CHECKS = ("O3-FROZEN", "O3-COVER", "O3-FORBIDDEN", "O3-VOID-ASYM", "O3-START", "O3-NO-SC", "O3-CHAIN", "O3-RESIDUE",
          "O3-WRITES", "O3-NULL", "O3-STABLE", "O3-SEAM", "O3-LANDING", "O3-BATTLE", "O3-MASKED", "O3-STATE",
          "O3-JOIN")
CORE = CHECKS[4:]


# ======================================================================== events and their rendering
def w(site, value=None, target=None, **opt) -> tuple:
    """A store event: ``site`` = (donor, sid, tag, ip[, target, value]); ``opt``: fld/don (overrides), old, m, src,
    add."""
    donor, sid, tag, ip = site[:4]
    return ("w", donor, sid, tag, ip, target or site[4], site[5] if value is None else value, opt)


def r(donor, byte, old, new, **opt) -> tuple:
    return ("r", donor, byte, old, new, opt)


def e(why, donor) -> tuple:
    return ("e", why, donor)


def battle_rows(n: int = 70, *, seed=0, site=LEO, **opt) -> list:
    """King Leo's AI store, ``n`` random values (each a change, seeded): 64 emitted, the rest counted."""
    rng = random.Random(f"o3-battle-{seed}")
    out, prev = [], 0
    for _ in range(n):
        v = rng.randrange(1, 256)
        if v == prev:
            v = v % 255 + 1
        out.append(w((*site, v), m=2, **opt))
        prev = v
    return out


def base_events(*, seed=0, battle: int = 70) -> list:
    """A base run (research/o3_design.md 8): ``arm`` in field 70; the warp's residue there (SC 1155's two bytes);
    61's rows; 62's; the battle's; 63's; 64's first row; ``off`` in 64."""
    ev = [e("arm", 70), r(70, 0, 0, 131), r(70, 1, 0, 4)]
    ev += [w(s) for s in S61] + [w(s) for s in S62]
    ev += battle_rows(battle, seed=seed)
    ev += [w(s) for s in S63] + [w(END64), e("off", 64)]
    return ev


def _parse(target: str) -> tuple:
    width, index = target.split(".", 1)[1].rstrip("]").split("[")
    return width, int(index)


def render(events: list, side: str, members: dict) -> list:
    """The rows the engine would write for ``events`` on ``side``: F-side donors on their member ids; each store's
    ``old`` the variable's value so far (the warp leaves SC 1155 and FieldEntrance 0; New Game left Byte[13] 1; every
    other target 0); a same-value store emitted once per site, a change up to 64 times per site, the rest counted
    into ``c`` rows just before ``off``."""
    fork = {d: f for f, d in members.items()}

    def fld_of(donor):
        return fork.get(donor, donor) if side == "F" else donor
    rows, sites = [], {}
    values = {"Global.UInt16[0]": 1155, "Global.Int16[2]": 0, "Global.Byte[13]": 1}
    f, sc = 1000, 1155
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
            if not emit:
                s["n"] += 1
                s["last"] = value
                continue
            if target == "Global.UInt16[0]":
                sc = value
            script = src == "eb"
            rows.append({"k": "w", "f": f, "p": 0, "m": m, "fld": fld, "don": don, "sc": sc, "src": src,
                         "sid": sid if script else -1, "uid": sid if script else -1, "lvl": 0 if script else -1,
                         "ip": ip if script else -1, "tag": tag if script else -1, "add": add, "byte": byte,
                         "w": width, "bit": bit, "old": old, "new": value, "same": int(old == value)})
    return rows


def visits(rows: list, members: dict, ends=(64,)) -> list:
    """The driver's ``visit`` rows for a rendered run: one each time the written field changes after the arm (field
    70's rows are the warp's, before any visit; an end field is rule 1's, never a visit), at the frame of the
    visit's first row. Battle rows stand in the battle's field and start no visit."""
    out, cur = [], None
    for x in rows:
        if x["k"] not in ("w", "r") or x["fld"] == 70 or x["fld"] in ends or x["fld"] == cur:
            continue
        cur = x["fld"]
        out.append({"k": "visit", "field": cur, "donor": place(cur, members), "visit": len(out) + 1,
                    "frame": x["f"], "sc": x["sc"]})
    return out


def battle_log_row(rows: list, side: str, members: dict, **over) -> dict:
    """2.3 step 6's ``battle`` row for a rendered run: frame0 two battle rows in (the AI's first stores can precede
    the driver's first poll), or -- with no battle row -- just after 62's last field row before 63; the flip just
    before 63's first row, the landing just after; result 2 (read in the fade), the flip's 1; landed 63 / 31213."""
    fork = {d: f for f, d in members.items()} if side == "F" else {}
    m = members if side == "F" else {}
    bw = [x for x in rows if x["k"] == "w" and x["m"] != 1]
    first63 = next((x for x in rows if x["k"] == "w" and x["m"] == 1 and place(x["fld"], m) == 63), None)
    if bw:
        frame0 = bw[0]["f"] + 15
    else:                       # the battle begins right after 62's ip1285 (Battle(0,338) is ip1293): just after it
        anchor = next((x for x in rows if x["k"] == "w" and x["m"] == 1 and place(x["fld"], m) == 62
                       and (x["sid"], x["tag"], x["ip"]) == CH62[1:4]), None)
        if anchor is None:
            before63 = [x for x in rows if x["k"] == "w" and x["m"] == 1 and place(x["fld"], m) == 62
                        and (first63 is None or x["f"] < first63["f"])]
            anchor = before63[-1] if before63 else rows[0]
        frame0 = anchor["f"] + 5
    f63 = first63["f"] if first63 is not None else frame0 + 40
    row = {"k": "battle", "field": fork.get(62, 62), "donor": 62, "visit": 2, "sc": 1155, "scene": 338,
           "epoch": EPOCH0 + 1, "row": 0, "beat": "leo", "frame0": frame0, "t0": 120.0, "result": 2, "turns": 3,
           "seconds": 11.5, "tutorials": 0, "timed_out": False,
           "leave": {"presses": 2, "uis": ["BattleHUD", "BattleResult"], "stopped": "scene-gone"},
           "flip_frame": f63 - 6, "flip_result": 1, "landed": fork.get(63, 63), "landed_place": 63,
           "land_frame": f63 + 3, "land_late": None, "t1": 140.0, "v": None, "by": None, "why": None}
    row.update(over)
    return row


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
    return [fn(x) if test(x) else x for x in ev]


def with_opt(x: tuple, **opt) -> tuple:
    return (*x[:-1], {**x[-1], **opt})


def upto(ev: list, site, *tail) -> list:
    """The run cut off after ``site``'s event (a drive that stopped there), then ``tail``."""
    i = next(i for i, x in enumerate(ev) if _is(x, site))
    return ev[:i + 1] + list(tail)


def is_battle(x) -> bool:
    return x[0] == "w" and x[-1].get("m", 1) != 1


def no_battle(ev: list) -> list:
    return [x for x in ev if not is_battle(x)]


def after_battle(ev: list, *new) -> list:
    """``new`` inserted right after the last battle row (or, with none, right after 62's ip1285)."""
    idx = [i for i, x in enumerate(ev) if is_battle(x)]
    i = (idx[-1] if idx else next(i for i, x in enumerate(ev) if _is(x, CH62))) + 1
    return ev[:i] + list(new) + ev[i:]


# ======================================================================== sessions
def six(pred: dict, *, s=None, f=None) -> list:
    """S F S F S F: each run's base events (its battle seeded by its index), ``s`` / ``f`` applied per side as
    ``fn(events, n)`` (``n`` = 0, 1, 2 within the side)."""
    counts = {"S": 0, "F": 0}
    out = []
    for i, side in enumerate(pred["order"]):
        n = counts[side]
        counts[side] += 1
        ev = base_events(seed=i)
        fn = s if side == "S" else f
        out.append({"side": side, "events": fn(ev, n) if fn else ev})
    return out


def make_session(tmp: Path, pred_path: Path, runs: list, scripts: dict) -> Path:
    """A session directory as O3Segment.run writes one. Each run: ``{side, events | rows, end?, why?, beats?, v?,
    cell?, by?, install?, end_state?, battle? (overrides of its battle row, False for none, or a list of rows),
    epoch0?, log? (extra rows, or fn(rows, visits) giving them)}``."""
    pred, sha = P.O3.load(pred_path)
    members = members_of(pred)
    d = tmp / f"s{len(list(tmp.iterdir()))}"
    (d / "scripts").mkdir(parents=True)
    for fid, data in scripts.items():
        (d / "scripts" / f"{fid}.eb").write_bytes(data)
    session = {"label": d.name, "predictions": str(pred_path), "predictions_sha256": sha,
               "predictions_version": pred["version"], "order": pred["order"], "budget": pred["budget"],
               "preflight": [[True, P.O3.title("P-TEXT"), TEXT_DEFECT]], "install": {"settings": pred["settings"]},
               "runs": [], "ended": {"log": [{"k": "recover-warp", "field": 4600}], "ok": True, "why": ""}}
    for i, run in enumerate(runs, 1):
        side = run["side"]
        m = members if side == "F" else {}
        rows = run.get("rows") if run.get("rows") is not None else render(run["events"], side, members)
        name, log_name = f"run{i}_{side}.jsonl", f"run{i}_{side}_log.json"
        (d / name).write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
        vis = visits(rows, m)
        end = run.get("end", "reached")
        battle = run.get("battle", {})
        if battle is False:
            brows = []
        elif isinstance(battle, list):
            brows = battle
        else:
            brows = [battle_log_row(rows, side, members, **battle)]
        log = list(vis)
        for b in brows:
            at = max((n for n, x in enumerate(log) if x.get("frame", 0) <= b["frame0"]), default=-1) + 1
            log.insert(at, b)
        extra = run.get("log") or []
        log += extra(rows, vis) if callable(extra) else extra
        end_state = run.get("end_state", dict(pred["end_state"]) if end == "reached" else None)
        if end == "reached":
            last = max((x["f"] for x in rows), default=0)
            log.append({"k": "end", "field": run.get("end_field", P.END_FIELD), "frame": last, "sc": 1155,
                        "end_state": end_state, "t": 300.0})
        beats = run.get("beats", {"leo": brows[0]["result"] if brows else None})
        outcome = {"end": end, "why": run.get("why", f"field {P.END_FIELD}" if end == "reached" else "route: stopped"),
                   "void": None, "beats": beats, "pages": run.get("pages", ["p72", "p73"]), "timed": [],
                   "choices": [], "steps": [], "overlays": [], "forbidden": [], "end_state": end_state,
                   "battles": brows, "battle_epoch0": run.get("epoch0", EPOCH0)}
        (d / log_name).write_text(json.dumps({"outcome": outcome, "log": log}), encoding="utf-8")
        rec = {"i": i, "side": side, "start": pred["start"][side], "trace": name, "log": log_name, "end": end,
               "why": outcome["why"], "beats": beats}
        for k in ("v", "cell", "by", "install"):
            if run.get(k) is not None:
                rec[k] = run[k]
        session["runs"].append(rec)
    (d / P.SESSION_FILE).write_text(json.dumps(session), encoding="utf-8")
    return d


def result(checks) -> dict:
    return {w_.split(":")[0]: ok for ok, w_, _d in checks}


def details(checks) -> dict:
    return {w_.split(":")[0]: d_ for _ok, w_, d_ in checks}


# ======================================================================== the cases
CASES = []


def case(name, want_verdict, *, fail=(), clauses=None, cover_void=False, report_has=(), void=None, covered=None):
    """Register a case, EXACT: ``fail`` the checks that must read FAIL, ``clauses`` ``{check: [markers]}`` the
    LANDING / BATTLE clauses its detail must name (each such check FAILS too), ``cover_void`` -- COVER VOID and every
    core check VOID ("too few covered runs"); every other check must read PASS. ``report_has`` substrings of the
    report, ``void`` ``{run index: [classes its VOID reasons must include]}``, ``covered`` ``{run index: bool}``."""
    want = {c: True for c in CHECKS}
    if cover_void:
        want["O3-COVER"] = None
        want.update({c: None for c in CORE})
    clauses = {("O3-" + k): v for k, v in (clauses or {}).items()}
    for c in list(fail) + list(clauses):
        cid = c if c.startswith("O3-") else "O3-" + c
        want[cid] = False

    def deco(fn):
        CASES.append((name, fn, want_verdict, want, clauses, tuple(report_has), void or {}, covered or {}))
        return fn
    return deco


@case("null-pair", "PROVEN", report_has=("a US session", "result 2", "landed 63 (place 63)", "landed 31213 (place 63)",
                                        "battle-mode rows 64", "KNOWN-KIT-DEFECT uk: ships stock us",
                                        "The session's end (end_run, warp first): the title came back"))
def _(pred):
    return six(pred)


@case("fork-drops-a-write", "NOT PROVEN", fail=("WRITES", "NULL", "STATE"))
def _(pred):
    return six(pred, f=lambda ev, n: drop(ev, B18_62))


SC_CS = (62, -1, -1, -1, "Global.UInt16[0]", 1190)


@case("sc-write-fork", "NOT PROVEN", fail=("NO-SC", "WRITES", "NULL", "STATE"))
def _(pred):
    return six(pred, f=lambda ev, n: before(ev, CH62, w(SC_CS, src="cs")))


@case("sc-write-both", "NOT PROVEN", fail=("NO-SC", "WRITES"))
def _(pred):
    add = lambda ev, n: before(ev, CH62, w(SC_CS, src="cs"))           # noqa: E731
    return six(pred, s=add, f=add)


@case("sc-harness-poke-both", "NOT PROVEN", fail=("NO-SC",))
def _(pred):
    poke = lambda ev, n: after(ev, B8_61, w((61, -1, -1, -1, "Global.Byte[0]", 7), src="harness"))   # noqa: E731
    return six(pred, s=poke, f=poke)


@case("chain-dropped-fork", "NOT PROVEN", fail=("CHAIN", "WRITES", "NULL", "STATE"), clauses={"LANDING": ["(c)"]})
def _(pred):
    return six(pred, f=lambda ev, n: drop(ev, CH62))


@case("battle-returned-to-62", "NOT PROVEN", fail=("CHAIN", "WRITES"),
      clauses={"LANDING": ["(c)"], "BATTLE": ["(d)"]})
def _(pred):
    back = lambda ev, n: after_battle(ev, w(RET62))                    # noqa: E731
    return six(pred, s=back, f=back)


@case("chain-first-old-wrong", "NOT PROVEN", fail=("CHAIN",))
def _(pred):
    old = lambda ev, n: edit(ev, lambda x: _is(x, CH61), lambda x: with_opt(x, old=102))   # noqa: E731
    return six(pred, s=old, f=old)


@case("byte206-more-rows-fork", "PROVEN")
def _(pred):
    more = lambda ev, n: after_battle(no_battle(ev), *battle_rows(100, seed=50 + n))       # noqa: E731
    return six(pred, f=more)


@case("battle-zero-rows", "PROVEN", report_has=("battle-mode rows 0",))
def _(pred):
    return six(pred, s=lambda ev, n: no_battle(ev), f=lambda ev, n: no_battle(ev))


@case("battle-zero-rows-62-resumed", "NOT PROVEN", fail=("CHAIN", "WRITES"),
      clauses={"LANDING": ["(c)"], "BATTLE": ["(d)"]})
def _(pred):
    back = lambda ev, n: after(no_battle(ev), CH62, w(RET62))           # noqa: E731
    return six(pred, s=back, f=back)


@case("byte199-fork", "NOT PROVEN", fail=("STABLE", "WRITES", "STATE"), clauses={"LANDING": ["(b)"]})
def _(pred):
    """The design registered NULL F here too; it cannot: a key in ONE fork run of three is UNSTABLE, never FORK ONLY
    (storytrace.Comparison.fork_only needs it in every fork run) -- so STABLE reads it, and NULL passes.
    byte199-every-F is the NULL proof (research/o3_design.md 11.6)."""
    return six(pred, f=lambda ev, n: after_battle(ev, w(E001_199, m=2)) if n == 0 else ev)


@case("byte199-every-F", "NOT PROVEN", fail=("NULL", "WRITES", "STATE"), clauses={"LANDING": ["(b)"]})
def _(pred):
    """The same m 2 Byte[199] row in EVERY fork run: FORK ONLY (NULL), stable within the side (STABLE passes) -- O1's
    second noise row is no O3 noise. Not in 8's table (11.6)."""
    return six(pred, f=lambda ev, n: after_battle(ev, w(E001_199, m=2)))


@case("byte199-both", "NOT PROVEN", fail=("WRITES",), clauses={"LANDING": ["(b)"]})
def _(pred):
    add = lambda ev, n: after_battle(ev, w(E001_199, m=2))              # noqa: E731
    return six(pred, s=add, f=add)


@case("other-battle-noise-both", "NOT PROVEN", clauses={"LANDING": ["(b)"]})
def _(pred):
    add = lambda ev, n: after_battle(ev, w(E001_93, m=2))               # noqa: E731
    return six(pred, s=add, f=add)


@case("byte206-field-mode-fork", "NOT PROVEN", fail=("NULL", "WRITES", "STATE"))
def _(pred):
    buf = (62, 4, -1, 1200, "Global.Byte[206]", 9)                     # an addition-buffer row: add 1, tag -1
    return six(pred, f=lambda ev, n: before(ev, CH62, w(buf, add=1)))


@case("lands-real-63-covered", "NOT PROVEN", fail=("SEAM", "FORBIDDEN", "WRITES"),
      clauses={"LANDING": ["(a)", "(c)"]})
def _(pred):
    real = lambda ev, n: edit(ev, lambda x: x[0] == "w" and x[1] == 63,  # noqa: E731
                              lambda x: with_opt(x, fld=63, don=63))
    return six(pred, f=real)


def _v16(run):
    run["events"] = upto(run["events"], S63[5], e("off", 63))
    run.update(end="void", why="route: battle 338 landed in real 63, not member(63) 31213: the s24 redirect did not "
                               "fire", v="V16", cell=[62, 1155], by="game",
               battle={"landed": 63, "v": "V16", "by": "game", "why": "the s24 redirect did not fire"})


@case("v16-all-F", "NOT PROVEN", fail=("FORBIDDEN", "VOID-ASYM"), cover_void=True)
def _(pred):
    runs = six(pred, f=lambda ev, n: edit(ev, lambda x: x[0] == "w" and x[1] == 63,
                                          lambda x: with_opt(x, fld=63, don=63)))
    for run in runs:
        if run["side"] == "F":
            _v16(run)
    return runs


@case("v16-one-F", "NOT PROVEN", fail=("FORBIDDEN", "VOID-ASYM"), covered={2: False, 4: True, 6: True})
def _(pred):
    runs = six(pred, f=lambda ev, n: edit(ev, lambda x: x[0] == "w" and x[1] == 63,
                                          lambda x: with_opt(x, fld=63, don=63)) if n == 0 else ev)
    _v16(runs[1])
    return runs


@case("battle-rows-real-62-fork", "NOT PROVEN", fail=("SEAM", "FORBIDDEN"), clauses={"LANDING": ["(b)"]})
def _(pred):
    real = lambda ev, n: edit(ev, is_battle, lambda x: with_opt(x, fld=62, don=62))    # noqa: E731
    return six(pred, f=real)


@case("fresh-missing", "NOT PROVEN", fail=("WRITES",), clauses={"LANDING": ["(c)"]})
def _(pred):
    gone = lambda ev, n: drop(ev, *MAIN63)                              # noqa: E731
    return six(pred, s=gone, f=gone)


@case("63-main-init-late-both", "NOT PROVEN", clauses={"LANDING": ["(c)"]})
def _(pred):
    def late(ev, n):
        rows = [x for x in ev if any(_is(x, s) for s in MAIN63)]
        return after(drop(ev, *MAIN63), B8_63, *rows)
    return six(pred, s=late, f=late)


@case("last-place-wrong", "NOT PROVEN", fail=("WRITES", "SEAM"), clauses={"LANDING": ["(d)"]})
def _(pred):
    """On F the stray 61 row stands at member(61) 31211, the last field before 64, so the digest's crossing out of
    the members is member(61) -> 64, which O3-SEAM rejects: SEAM is a co-failure the design did not register
    (11.6)."""
    add = lambda ev, n: after(ev, CH63, w(DEAD61_130))                  # noqa: E731
    return six(pred, s=add, f=add)


@case("last-place-61-repeat-both", "NOT PROVEN", fail=("SEAM",), clauses={"LANDING": ["(d)"]})
def _(pred):
    """A registered key again, so WRITES, NULL and STATE pass -- but not LANDING alone, as the design had it: on F the
    run's last field before 64 is member(61), and O3-SEAM reads the same crossing (11.6). last-place-harness-S is
    the (d)-alone fact."""
    add = lambda ev, n: after(ev, CH63, w(MUSIC61))                     # noqa: E731
    return six(pred, s=add, f=add)


@case("last-place-harness-S", "NOT PROVEN", clauses={"LANDING": ["(d)"]})
def _(pred):
    """LANDING (d) ALONE: every S run's last field row before 64 is a harness poke standing in 61 (Byte[300], no SC
    byte). No key, no history and no seam reads a harness row on S -- only (d)'s last field row does. On F the same
    row would be member(61) -> 64, which O3-SEAM reads too, so the alone fact is the S side's (11.6). Not in 8's
    table."""
    poke = lambda ev, n: after(ev, CH63, w((61, -1, -1, -1, "Global.Byte[300]", 9), src="harness"))   # noqa: E731
    return six(pred, s=poke)


@case("end-boundary-residue-both", "NOT PROVEN", clauses={"LANDING": ["(e)"]})
def _(pred):
    add = lambda ev, n: before(ev, END64, r(64, 300, 0, 1))             # noqa: E731
    return six(pred, s=add, f=add)


@case("end-row-missing-one-S", "PROVEN", void={1: ["A-NOEND"]}, covered={1: False, 3: True, 5: True},
      report_has=("A-NOEND",))
def _(pred):
    """The end-collection race (story-o1e's run 3 S, covered there with its cut None): one S run reached 64, and its
    trace closed before 64's first store -- an ``off`` row in 64, no ``w`` or ``r`` row there, so no end cut. The run
    is the driver's A-NOEND (the review, research/o3_design.md 11.7 #3), never O3-LANDING (e)'s finding: S 2 of 3,
    PROVEN on the rest."""
    runs = six(pred)
    runs[0]["events"] = drop(runs[0]["events"], END64)
    return runs


@case("battle-scene-336", "NOT PROVEN", clauses={"BATTLE": ["(a)"]})
def _(pred):
    runs = six(pred)
    for run in runs:
        run["battle"] = {"scene": 336}
    return runs


@case("battle-two-rows", "NOT PROVEN", clauses={"BATTLE": ["(a)"]})
def _(pred):
    runs = six(pred)
    for run in runs:
        run["log"] = lambda rows, vis, side=run["side"]: [battle_log_row(rows, side, members_of(pred), row=1,
                                                                         epoch=EPOCH0 + 2)]
    return runs


@case("battle-epoch-skip", "NOT PROVEN", clauses={"BATTLE": ["(b)"]})
def _(pred):
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            run["battle"] = {"epoch": EPOCH0 + 2}
    return runs


@case("battle-frame0-late", "NOT PROVEN", clauses={"BATTLE": ["(d)"]})
def _(pred):
    runs = six(pred)
    for i, run in enumerate(runs):
        rows = render(run["events"], run["side"], members_of(pred))
        fresh = next(x for x in rows if x["k"] == "w" and x["m"] == 1 and (x["sid"], x["tag"], x["ip"]) == (0, 0, 22)
                     and place(x["fld"], members_of(pred) if run["side"] == "F" else {}) == 63)
        run["battle"] = {"frame0": fresh["f"] + 3}
    return runs


@case("battle-landed-real-63-log-F", "NOT PROVEN", clauses={"BATTLE": ["(c)"]})
def _(pred):
    """O3-BATTLE (c) ALONE, the F side: every F run's battle row says it landed in REAL 63 (place 63) while its trace
    stays in member(63) 31213 -- only (c) reads the log's landing; LANDING, SEAM and FORBIDDEN read the trace, which is
    the base run's."""
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            run["battle"] = {"landed": 63}
    return runs


@case("battle-landed-member-log-S", "NOT PROVEN", clauses={"BATTLE": ["(c)"]})
def _(pred):
    """O3-BATTLE (c) ALONE, the S side: every S run's battle row says it landed in 31213 (the F side's member, place
    63) -- on S the landing must be 63 itself, which no members map turns into anything else."""
    runs = six(pred)
    for run in runs:
        if run["side"] == "S":
            run["battle"] = {"landed": 31213}
    return runs


@case("battle-beat-true-one-S", "PROVEN", report_has=("leo result True",), void={1: ["A-BEATS"]},
      covered={1: False, 3: True, 5: True})
def _(pred):
    runs = six(pred)
    runs[0]["beats"] = {"leo": True}
    return runs


@case("land-late-fork", "PROVEN", report_has=("land_late {'frames': 2400, 's': 80}",))
def _(pred):
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            run["battle"] = {"land_late": {"frames": 2400, "s": 80}}
    return runs


def _v15(run, side):
    run["events"] = upto(run["events"], CH62, *battle_rows(5, seed=99), e("off", 62))
    run.update(end="void", why="route: battle 338 reached no result within 180 s / 40 turns", v="V15", cell=[62, 1155],
               by="driver", battle={"result": None, "timed_out": True, "flip_frame": None, "flip_result": None,
                                    "landed": None, "landed_place": None, "land_frame": None, "v": "V15",
                                    "by": "driver", "why": "battle 338 reached no result within 180 s / 40 turns"})


@case("v15-one-S", "PROVEN", void={1: ["V15"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    runs = six(pred)
    _v15(runs[0], "S")
    return runs


@case("v15-all-F", "NOT PROVEN", fail=("VOID-ASYM",), cover_void=True)
def _(pred):
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            _v15(run, "F")
    return runs


@case("unregistered-battle-F", "NOT PROVEN", fail=("VOID-ASYM",), covered={2: False})
def _(pred):
    runs = six(pred)
    runs[1]["events"] = upto(runs[1]["events"], CH62, *battle_rows(5, seed=98), e("off", 62))
    runs[1].update(end="void", why="route: an unregistered battle: scene 337 (epoch 8) in 31212 (place 62) at SC 1155",
                   v="V10", cell=[62, 1155], by="game", battle=False)
    return runs


@case("control-S", "NOT PROVEN", fail=("VOID-ASYM",), covered={1: False})
def _(pred):
    runs = six(pred)
    runs[0]["events"] = upto(runs[0]["events"], S63[5], e("off", 63))
    runs[0].update(end="void", why="route: control held in 63 (place 63) at SC 1155, where the table has no entry",
                   v="V4", cell=[63, 1155], by="game")
    return runs


@case("error-path-start-S", "PROVEN", void={1: ["V5", "A-START"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    runs = six(pred)
    runs[0]["events"] = upto(drop(runs[0]["events"], MUSIC61), S61[2], w(ERR61_97), e("off", 61))
    runs[0].update(end="void", why="route: a stop page (61-63's ambient error window 3), nothing pressed", v="V5",
                   cell=[61, 1155], by="driver", battle=False)
    return runs


@case("error-path-start-covered-S", "PROVEN", void={1: ["A-START"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    runs = six(pred)
    runs[0]["events"] = after(drop(runs[0]["events"], MUSIC61), S61[2], w(ERR61_97), w(ERR61_349))
    return runs


@case("error-path-63-F", "NOT PROVEN", fail=("VOID-ASYM",), covered={2: False})
def _(pred):
    runs = six(pred)
    runs[1]["events"] = upto(drop(runs[1]["events"], S63[3]), S63[2], w(ERR63_97), e("off", 63))
    runs[1].update(end="void", why="route: a stop page (61-63's ambient error window 3), nothing pressed", v="V5",
                   cell=[63, 1155], by="game")
    return runs


@case("start-residue-wrong", "NOT PROVEN", fail=("START",))
def _(pred):
    return six(pred, s=lambda ev, n: edit(ev, lambda x: x[0] == "r" and x[2] == 0, lambda x: r(70, 0, 0, 132)))


@case("start-first-missing", "NOT PROVEN", fail=("START",))
def _(pred):
    gone = lambda ev, n: drop(ev, START61)                              # noqa: E731
    return six(pred, s=gone, f=gone)


@case("start-music-old-wrong", "NOT PROVEN", fail=("START",))
def _(pred):
    old = lambda ev, n: edit(ev, lambda x: _is(x, MUSIC61), lambda x: with_opt(x, old=3))  # noqa: E731
    return six(pred, s=old, f=old)


@case("front-cut-write", "NOT PROVEN", fail=("START",))
def _(pred):
    in70 = ("w", 70, 3, 1, 40, "Global.Byte[13]", 1, {})               # a store in field 70, before the start
    return six(pred, f=lambda ev, n: before(ev, START61, in70))


@case("residue-after-start", "NOT PROVEN", fail=("RESIDUE",))
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, START61, r(61, 300, 0, 7)))


@case("writes-extra-symmetric", "NOT PROVEN", fail=("WRITES",))
def _(pred):
    add = lambda ev, n: before(ev, B4_1034, w(DEAD62_1023))             # noqa: E731
    return six(pred, s=add, f=add)


@case("end-cut", "PROVEN")
def _(pred):
    return six(pred, s=lambda ev, n: ev[:-1] + [w(x) for x in AFTER64] + [ev[-1]])


@case("end-state-differs", "NOT PROVEN", fail=("STATE",))
def _(pred):
    runs = six(pred)
    runs[3]["end_state"] = dict(pred["end_state"], **{"Global.Byte[303]": 3})
    return runs


@case("battle-result-1", "PROVEN")
def _(pred):
    runs = six(pred)
    for run in runs:
        run["battle"] = {"result": 1}
    return runs


@case("battle-result-3-one-S", "PROVEN", void={1: ["A-BEATS"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    runs = six(pred)
    runs[0]["battle"] = {"result": 3}
    return runs


@case("beat-missing", "VOID", cover_void=True, void={1: ["A-BEATS"], 3: ["A-BEATS"]})
def _(pred):
    runs = six(pred)
    for run in (runs[0], runs[2]):
        run["beats"] = {"leo": None}
    return runs


@case("masked-differs", "NOT PROVEN", fail=("MASKED",))
def _(pred):
    return six(pred, f=lambda ev, n: drop(ev, *BIT184S))


@case("mismatched", "PROVEN", void={2: ["A-MISMATCH"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    return six(pred, f=lambda ev, n: edit(ev, lambda x: x[0] == "w" and x[1] == 62 and x[-1].get("m", 1) == 1,
                                          lambda x: with_opt(x, don=31212)) if n == 0 else ev)


@case("no-start-row", "PROVEN", void={1: ["A-NOSTART"]}, covered={1: False})
def _(pred):
    runs = six(pred)
    runs[0]["events"] = base_events()[:3] + [e("off", 70)]
    runs[0]["battle"] = False
    return runs


@case("join-failure", "NOT PROVEN", fail=("JOIN",))
def _(pred):
    off = (62, 4, 1, 1102, "Global.Byte[18]", 1)                       # one byte into the ip1101 store
    add = lambda ev, n: after(ev, B18_62, w(off))                       # noqa: E731
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
        run["install"] = "during the run: 1 changed: settings"
    return runs


# ======================================================================== the unit cases (no session)
def _rows(events, side="S", members=None) -> list:
    return T.parse_text("".join(json.dumps(x) + "\n" for x in render(events, side, members or {})))


def unit_no_sc_span() -> tuple:
    """NO-SC's byte-span selector: a Global.Byte[1] row is selected (it overlaps SC's bytes 0-1) and fails by name
    against the EMPTY sequence; a Byte[4] row is not selected."""
    rows = _rows([e("arm", 70), ("w", 61, 0, 0, 22, "Global.Byte[1]", 7, {}), ("w", 61, 0, 0, 49, "Global.Byte[4]", 7, {}),
                  e("off", 61)])
    sel = A.span_rows(rows, [0, 1])
    bad = A.span_sequence(rows, {}, [0, 1], [], 1155)
    ok = ([x.target for x in sel] == ["Global.Byte[1]"] and any("Global.Byte[1]=7" in b and "has no key" in b
                                                                for b in bad)
          and any(b.startswith("1 writes, want 0") for b in bad))
    return ok, f"selected {[x.target for x in sel]}; {bad[:2]}"


def unit_trace_summary(pred: dict, stock) -> tuple:
    """O3's trace_summary (research/o3_design.md 7.2) of a base S run: chain 3/3, writes 24/24, the error path,
    forbidden and dead sites absent, no SC row, the battle's rows (64 emitted, the rest in one count row), the first
    field row after 62 ip1285 = 63 e0 t0 ip22, the end cut's row = 64 e0 t0 ip22, no unregistered key, no join
    failure, the two start residue rows; of a battle-zero-rows run: the count 0, the rest the same."""
    out = []
    for n_battle in (70, 0):
        rows = _rows(base_events(battle=n_battle))
        t = P.trace_summary(rows, pred, stock=stock)
        reg = {k: (sum(1 for x in v if x["present"]), len(v)) for k, v in t["registered"].items()}
        want = {"chain": (3, 3), "writes": (24, 24), "error_path": (0, 14), "forbidden_sites": (0, 1), "dead": (0, 10)}
        bt = t["battle"]
        ok = (reg == want and t["sc"] == [] and [x["new"] for x in t["entrance"]] == [100, 0, 100]
              and t["unregistered"] == [] and t["failures"] == []
              and [x[1:] for x in t["residue_before"]] == [[0, 0, 131], [1, 0, 4]]
              and t["after_before"] == "63 e0 t0 ip22 Global.Bit[191]=0"
              and t["end_row"] == "w 64 e0 t0 ip22 Global.Bit[191]=0"
              and (bt["w"], len(bt["c"])) == ((64, 1) if n_battle else (0, 0))
              and (not n_battle or (bt["c"][0][1] == 6 and bt["sites"] == ["m2 e1 t1 ip267 Global.Byte[206]"]))
              and (t["noise_keys"] > 0) == bool(n_battle))
        out.append((ok, f"battle {n_battle}: registered {reg}; battle {bt['w']} w, c {bt['c']}; noise keys "
                        f"{t['noise_keys']}; after 1285 {t['after_before']}; end {t['end_row']}"))
    return all(ok for ok, _d in out), " | ".join(d for _ok, d in out)


def unit_state_history(pred: dict, stock, scripts: dict, tmp: Path, path: Path) -> tuple:
    """O3-STATE (a)'s reading of a base run: Byte[8]'s history is 61's then 63's := 125; the battle's noise is in
    neither the history nor the suppressed set."""
    d = make_session(tmp, path, six(pred)[:1], scripts)
    run = P.O3.read_session(d, pred, stock=stock)[0]
    h, s = P.O3.history(run, pred), P.O3.suppressed(run, pred)
    got = [(k.donor, k.value) for k in h.get("Global.Byte[8]", [])]
    ok = got == [(61, 125), (63, 125)] and "Global.Byte[206]" not in h and "Global.Byte[206]" not in s
    return ok, f"Byte[8] {got}; Byte[206] in history {'Global.Byte[206]' in h}, suppressed {sorted(s)}"


_LOG_HEAD = "30.09.2026 19:27:42 |M| [WindowManager] Moving window to (2045,33)\n"
_LOG_351 = ("30.09.2026 19:27:44 |W| [DataPatchers] ForkDonorPatch: donor field 351 is forked by both 30831 and 30842 "
            "-> remap DISABLED (ambiguous)\n")
_LOG_DONE = "30.09.2026 19:27:44 |M| [DataPatchers] Initialized\n"


def unit_p_donor_log() -> tuple:
    route = (61, 62, 63)
    a = P.p_donor_log(_LOG_HEAD + _LOG_351 + _LOG_DONE, route)
    w63 = _LOG_351.replace("351", "63").replace("30831 and 30842", "31213 and 31299")
    b = P.p_donor_log(_LOG_HEAD + _LOG_351 + w63 + _LOG_DONE, route)
    c = P.p_donor_log(_LOG_HEAD + _LOG_351, route)
    ok = a[0] and not b[0] and "donor field 63 is forked by both 31213 and 31299" in b[1] and not c[0]
    return ok, f"today {a[0]}; 63 twice {b[0]}; no Initialized {c[0]}: {c[1][:60]}"


def _touch(p: Path, when: _dt.datetime, frac: float = 0.0) -> None:
    ts = when.timestamp() + frac
    os.utime(p, (ts, ts))


def unit_p_launch(tmp: Path) -> tuple:
    """P-LAUNCH's cases (section 8 p-launch): all older PASS; a ForkDonorPatch.txt that holds `31213 63` touched at
    19:27:50 FAIL naming it; the same second FAIL; Memoria.ini after FAIL; a TextPatch.txt after FAIL; no stamp FAIL; a
    folder with no patch file PASS."""
    launched = P.launch_time(_LOG_HEAD + _LOG_DONE)
    game = tmp / "plaunch"
    root, bare = game / "FF9CustomMap", game / "MoguriVideo"
    root.mkdir(parents=True)
    bare.mkdir()
    old = _dt.datetime(2026, 9, 30, 19, 27, 4)
    files = {game / "Memoria.ini": "[Battle]\nSpeed = 5\n", root / "DictionaryPatch.txt": "FieldScene 31213 11 X X 2\n",
             root / "ForkDonorPatch.txt": "31211 61\n31212 62\n31213 63\n"}
    for p, text in files.items():
        p.write_text(text, encoding="utf-8")
        _touch(p, old)
    roots = [root, bare]

    def ok_now():
        return P.launch_check(P.launch_files(game, roots), launched)
    got = {"older": ok_now()[0]}
    fdp = root / "ForkDonorPatch.txt"
    _touch(fdp, _dt.datetime(2026, 9, 30, 19, 27, 50))
    v, d = ok_now()
    got["fdp-after"] = (not v) and "ForkDonorPatch.txt" in d and "relaunch" in d
    got["fdp-holds-the-row"] = P.p_donor({"route": [61, 62, 63], "members": {"31211": 61, "31212": 62,
                                                                            "31213": 63}}, roots)[0]
    _touch(fdp, launched, 0.4)
    got["same-second"] = not ok_now()[0]
    _touch(fdp, old)
    _touch(game / "Memoria.ini", _dt.datetime(2026, 9, 30, 19, 30))
    got["ini-after"] = not ok_now()[0]
    _touch(game / "Memoria.ini", old)
    tp = root / "TextPatch.txt"
    tp.write_text("x\n", encoding="utf-8")
    _touch(tp, _dt.datetime(2026, 9, 30, 19, 28))
    got["textpatch-after"] = not ok_now()[0]
    tp.unlink()
    got["no-stamp"] = not P.launch_check(P.launch_files(game, roots), P.launch_time("no stamp here\n"))[0]
    got["no-patch-file"] = P.launch_check(P.launch_files(tmp / "nowhere", [bare]), launched)[0]
    return all(got.values()), str(got)


_338_NAMES = ["King Leo", "Zenero", "Benero", "Taste steel!", "Poly", "Clamp Pinch", "Pyro", "Clamp Pinch", "Pyro"]


#: FF9CustomMap's DictionaryPatch BattleScene lines as today's install holds them (the fight ledger's four scenes).
_BATTLE_SCENES = ("BattleScene 30871 LEDGER_A BBG_B251", "BattleScene 30872 LEDGER_B BBG_B252",
                  "BattleScene 30881 LEDGER1W BBG_B253", "BattleScene 30882 LEDGER1S BBG_B254")


def unit_p_stock_battle(tmp: Path) -> tuple:
    """P-STOCK-BATTLE's cases (section 8 p-stock-battle): today's live shape PASS, its four BattleScene lines listed; a
    scene override of TH_E002, its fr .eb, `Battle: 338`, `Battle: BSC_TH_E002`, `AnyEnemyByName: King Leo` each FAIL;
    `AnyEnemyByName: Goblin` PASS, listed; a DictionaryPatch `BattleScene 338 ...` (the battle rebound) and
    `BattleScene 30999 TH_E002 ...` (its forward entry repointed) each FAIL (c); a `FieldScene 338 ...` PASSES (the
    battle never reads EventDB[338]: the review, 11.7 #4)."""
    res = "StreamingAssets/assets/resources"
    n = {"k": 0}

    def judge(paths=(), lines=(), dict_lines=()):
        n["k"] += 1
        base = tmp / f"pstock{n['k']}"
        custom, msgs = base / "FF9CustomMap", base / "FF9CustomMap-msgs"
        for scene in ("LEDGER1S", "LEDGER1W", "LEDGER_A", "LEDGER_B"):
            for rel in (f"{res}/BattleMap/BattleScene/EVT_BATTLE_{scene}/dbfile0000.raw16.bytes",
                        f"{res}/commonasset/eventengine/eventbinary/Battle/us/EVT_BATTLE_{scene}.eb.bytes", *paths):
                (custom / rel).parent.mkdir(parents=True, exist_ok=True)
                (custom / rel).write_bytes(b"x")
        (custom / "BattlePatch.txt").write_text("".join(f"Battle: {b}\nMusic: 0\n" for b in (67, 67, 336, 337, 334, 335))
                                                + "".join(f"{x}\n" for x in lines), encoding="utf-8")
        (custom / "DictionaryPatch.txt").write_text("".join(f"{x}\n" for x in ("FieldScene 31213 11 O1_TSHP_TH_STG "
                                                                               "O1_TSHP_TH_STG 2",
                                                                               *_BATTLE_SCENES, *dict_lines)),
                                                    encoding="utf-8")
        msgs.mkdir(parents=True)
        (msgs / "BattlePatch.txt").write_text("Battle: 67\nMusic: 0\n", encoding="utf-8")
        return P.battle_stock([custom, msgs], 338, _338_NAMES)[:2]
    ok, detail = judge()
    got = {"today": ok and "FF9CustomMap 30871 LEDGER_A, 30872 LEDGER_B, 30881 LEDGER1W, 30882 LEDGER1S" in detail,
           "scene-dir": not judge(paths=[f"{res}/BattleMap/BattleScene/EVT_BATTLE_TH_E002/dbfile0000.raw16.bytes"])[0],
           "fr-eb": not judge(paths=[f"{res}/commonasset/eventengine/eventbinary/Battle/fr/EVT_BATTLE_TH_E002.eb.bytes"])[0],
           "battle-338": not judge(lines=["Battle: 338", "MaxHP: 1"])[0],
           "battle-name": not judge(lines=["Battle: BSC_TH_E002", "MaxHP: 1"])[0],
           "king-leo": not judge(lines=["AnyEnemyByName: King Leo", "MaxHP: 1"])[0]}
    ok, detail = judge(lines=["AnyEnemyByName: Goblin", "MaxHP: 1"])
    got["goblin-listed"] = ok and "AnyEnemyByName: Goblin" in detail
    for case, line in (("dictionary-battlescene-338", "BattleScene 338 LEDGER_A BBG_B251"),
                       ("dictionary-battlescene-th_e002", "BattleScene 30999 TH_E002 BBG_B065")):
        ok, detail = judge(dict_lines=[line])
        got[case] = (not ok) and f"(c) FF9CustomMap/DictionaryPatch.txt '{line}'" in detail
    got["dictionary-fieldscene-338"] = judge(dict_lines=["FieldScene 338 11 X X 2"])[0]
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_p_settings(tmp: Path) -> tuple:
    """P-SETTINGS' cases (section 8 p-settings): an ini equal to 4.13 PASS; `Speed = 0` FAIL naming it; a later
    duplicate assignment wins."""
    want = P.SETTINGS
    game = tmp / "psettings"
    game.mkdir()

    def judge(settings, extra=""):
        lines = []
        for sec, kv in settings.items():
            lines += [f"[{sec}]"] + [f"{k} = {v}" for k, v in kv.items()] + [""]
        (game / "Memoria.ini").write_text("\n".join(lines) + extra, encoding="utf-8")
        return P.p_settings(want, P.install_settings(game, [], want))
    slow = {**want, "Battle": dict(want["Battle"], Speed="0")}
    a, b = judge(want), judge(slow)
    got = {"equal": a[0], "speed-0": (not b[0]) and "[Battle] Speed = '0' (frozen '5')" in b[1],
           "later-wins": (not judge(want, "\n[Battle]\nSpeed = 0\n")[0]) and judge(slow, "\n[Battle]\nSpeed = 5\n")[0]}
    return all(got.values()), str(got)


def unit_scene_census(pred: dict) -> list:
    """O3-SCENE on the install PASSES; each one-change copy of the draft FAILS by its clause: ``lands`` 64, ``won``
    [1] (WinPose off allows exactly [1, 2]), ``won`` [1, 2, 3] (a defeat counted as covered), ``landing.battle.ip``
    268, the noise target Byte[199]; an ``lvalue_class`` that classifies nothing FAILS each of the 24 unresolved
    stores by name."""
    out = []
    ok, _w, detail = P.O3.scene_check(pred)
    out.append(("scene-census", ok is True, detail[:150]))
    muts = [("scene-lands-64", lambda p: p["battles"][0].update(lands=64), "gives [63], the row lands 64"),
            ("scene-won-1", lambda p: p["battles"][0].update(won=[1]), "won [1], but flags 0x1839 (WinPose off) allow "
                                                                       "exactly [1, 2]"),
            ("scene-won-123", lambda p: p["battles"][0].update(won=[1, 2, 3]), "won [1, 2, 3], but flags 0x1839"),
            ("scene-site-ip268", lambda p: p["landing"]["battle"].update(ip=268), "landing.battle names e1 t1 ip268"),
            ("scene-noise-199", lambda p: p["noise"][0].update(target="Global.Byte[199]"),
             "the noise names ['Global.Byte[199]']")]
    for name, mutate, clause in muts:
        p = copy.deepcopy(pred)
        mutate(p)
        ok, _w, detail = P.O3.scene_check(p)
        out.append((name, ok is False and clause in detail, f"{'FAIL' if ok is False else 'PASS'}: {detail[:120]}"))
    ok, _w, detail = P.O3.scene_check(pred, classify=lambda tok: None)
    c = P.scene_census(P.scene_name(338))
    named = [f"e{u['sid']} t{u['tag']} ip{u['ip']} (B_SYSLIST[0])" for u in c["unresolved"]]
    out.append(("scene-classify-nothing", ok is False and len(named) == 24 and all(x in detail for x in named)
                and "24 unresolved store(s) no class covers" in detail, f"{len(named)} named: {detail[:100]}"))
    return out


def unit_store_census(pred: dict, stock) -> list:
    """O3-CENSUS on the install PASSES, "61: 15, 62: 28, 63: 15 store sites ... 0 unresolved"; each mutant FAILS naming
    the site: ``dead`` without 61 ip130; ``error_path`` without 62 e0 t10 ip580; ``forbidden_sites`` empty (62 ip1345
    unclassified); an injected unresolved store whose lvalue token no class covers."""
    out = []
    ok, _w, detail = P.O3.census_check(pred, stock)
    out.append(("store-census", ok is True and detail.startswith("61: 15, 62: 28, 63: 15 store sites -- all classified")
                and detail.endswith("0 unresolved"), detail[:150]))

    def without(name, site):
        def mutate(p):
            p[name] = [k for k in p[name] if (k["donor"], k["sid"], k["tag"], k["ip"]) != site]
        return mutate
    muts = [("census-dead-61-130", without("dead", (61, 0, 0, 130)), "61 e0 t0 ip130 Global.Byte[13]: in no list"),
            ("census-error-62-580", without("error_path", (62, 0, 10, 580)),
             "62 e0 t10 ip580 Global.Byte[13]: in no list"),
            ("census-forbidden-empty", lambda p: p.update(forbidden_sites=[]),
             "62 e4 t1 ip1345 Global.Int16[2]: in no list")]
    for name, mutate, clause in muts:
        p = copy.deepcopy(pred)
        mutate(p)
        ok, _w, detail = P.O3.census_check(p, stock)
        out.append((name, ok is False and clause in detail, f"{'FAIL' if ok is False else 'PASS'}: {detail[:120]}"))

    def sites(idx):
        found, undecoded = P.store_sites(idx)
        if idx.field_id == 62:
            found = found + [{"sid": 9, "tag": 1, "ip": 999, "kind": "unknown", "why": "injected",
                              "token": "B_PTR(3)", "text": "SET({B_PTR(3) const(1) B_LET B_EXPR_END})"}]
        return found, undecoded
    ok, _w, detail = P.O3.census_check(pred, stock, sites=sites)
    out.append(("census-unresolved-injected", ok is False and "62 e9 t1 ip999: an unresolved store (lvalue 'B_PTR(3)'"
                in detail, f"{'FAIL' if ok is False else 'PASS'}: {detail[:120]}"))
    return out


def unit_battle_row(pred: dict) -> tuple:
    """segment_drive.battle_of on 2.1's row: passes (a copy); raises on ``won`` [1, 2, 3], [2] and []; on a beat not
    in ``beats``; on a beat a naming rule, a table step or a choice rule also names; on ``max_turns`` -1 and True; on
    ``land_s`` above ``land_cap_s``; ``max_turns`` 0 passes (R-BATTLE-VOID's row)."""
    row = pred["battles"][0]
    got = {"passes": SD.battle_of(pred, row) == row, "max_turns-0": SD.battle_of(pred, dict(row, max_turns=0))
           ["max_turns"] == 0}

    def refuses(change, match, p=None):
        try:
            SD.battle_of(p or pred, {**row, **change})
        except ValueError as err:
            return match in str(err)
        return False
    for won in ([1, 2, 3], [2], []):
        got[f"won-{won}"] = refuses({"won": won}, "won is")
    got["beat-unknown"] = refuses({"beat": "garnet"}, "is not one of the predictions' beats")
    got["max_turns--1"] = refuses({"max_turns": -1}, "max_turns is an int >= 0")
    got["max_turns-True"] = refuses({"max_turns": True}, "max_turns is an int >= 0")
    got["land_s-above-cap"] = refuses({"land_s": 200}, "is above land_cap_s")
    for where, extra in (("naming", {"naming": [{"donor": 62, "sc": 1155, "beat": "leo"}]}),
                         ("choice", {"choices": pred["choices"] + [{"donor": 62, "sc": None, "match": "x", "pick": "y",
                                                                    "beat": "leo"}]}),
                         ("step", {"table": [{"donor": 62, "sc": 1155, "steps": [{"kind": "trigger", "goal": [0, 0],
                                                                                    "until": {"x_le": 1},
                                                                                    "beat": "leo"}]}]})):
        got[f"named-by-{where}"] = refuses({}, "is also named by", {**pred, **extra})
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_build_legacy(tmp: Path) -> tuple:
    """Segment.build_check on a synthetic two-member build (61 and 62 as 31211 and 31212) with an injected stock_lang
    and accept_us_build: a member whose other-language .eb is the us build reads PASS, counted "us-build"; one whose
    is neither its own donor language remapped nor the us build FAILS by name; the same build without accept_us_build
    FAILS the us-build copy -- the legacy acceptance is the opt-in, never a blanket pass."""
    from ff9mapkit.config import LANGS, ModLayout
    from ff9mapkit.content.verbatim import remap_fields
    real = ST.stock_lang()
    cache: dict = {}

    def stock_lang(fid, lang):
        if (fid, lang) not in cache:
            cache[(fid, lang)] = real(fid, lang)
        return cache[(fid, lang)]
    members, names = {31211: 61, 31212: 62}, {31211: "O3_BL_BST", 31212: "O3_BL_STG"}
    retarget = {d: f for f, d in members.items()}
    other = next(L for L in LANGS if L != "us" and stock_lang(61, L) != stock_lang(61, "us"))
    pred = {"members": {str(f): d for f, d in members.items()}, "names": {str(f): n for f, n in names.items()}}

    def build(name, garbage: bool) -> Path:
        root = tmp / name
        lay = ModLayout(root)
        for fid, dn in members.items():
            us = remap_fields(stock_lang(dn, "us"), retarget)
            for L in LANGS:
                data = us if L == "us" else (us if L == other else remap_fields(stock_lang(dn, L), retarget))
                if garbage and fid == 31212 and L == other:
                    data = b"neither its donor's nor the us build"
                p = lay.eb_path(L, f"EVT_{names[fid]}.eb.bytes")
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
        return root
    legacy = P.O3Segment()
    strict = P.O3Segment()
    strict.accept_us_build = False
    good, bad = build("bl-good", False), build("bl-bad", True)
    a = legacy.build_check(pred, good, stock_lang=stock_lang)
    b = legacy.build_check(pred, bad, stock_lang=stock_lang)
    c = strict.build_check(pred, good, stock_lang=stock_lang)
    ok = (a[0] is True and "2 us-build" in a[2]
          and b[0] is False and f"31212 (62) {other}: neither its own donor language nor the us build" in b[2]
          and c[0] is False and f"31211 (61) {other}: not its own donor language" in c[2])
    return ok, f"legacy {a[0]} ({a[2][:60]}); garbage {b[0]} ({b[2][:70]}); strict {c[0]} ({c[2][:60]})"


def _key(p: dict, name: str, donor: int, ip: int) -> dict:
    return next(k for k in p[name] if (k["donor"], k["ip"]) == (donor, ip))


#: The offline checks' mutants (research/o3_design.md 8): the DRAFT, deep-copied, one thing changed; the check must
#: then read FAIL -- after every check has read PASS on the unchanged draft -- and its detail hold the clause.
OFFLINE_MUTANTS = [
    ("keys-write-value", "KEYS", lambda p: _key(p, "writes", 62, 319).update(value=3586),
     "the bytes give 3585, the key says 3586"),
    ("keys-prior-unknown", "KEYS", lambda p: _key(p, "writes", 62, 637).update(prior="62/4/1/9999"),
     "names no registered prior"),
    ("keys-error-path-ip", "KEYS", lambda p: _key(p, "error_path", 61, 97).update(ip=98),
     "forbidden_sites: 61 e0 t0 ip97: the error path"),
    ("keys-chain-off", "KEYS", lambda p: p["chain"][0].update(off=353), "chain: FieldEntrance 100: 61's exit"),
    ("keys-start-first-target", "KEYS", lambda p: p["start_first"].update(target="Global.Bit[192]"),
     "start_first: 61's Main_Init: its first store"),
    ("keys-dead-value", "KEYS", lambda p: _key(p, "dead", 61, 130).update(value=2),
     "the bytes give 1, the key says 2"),
    ("keys-start-music", "KEYS", lambda p: p["start_music"].update(ip=138, off=132),
     "is 0 writes keys, not one"),
    ("regions-hotspot-62-e9", "REGIONS", lambda p: p["hotspots"].update({"62": [{"sid": 9, "x": 0, "z": 0, "n": 100}]}),
     "hot-spot 62 e9: frozen, but no such hot-spot in the bytes"),
]


def _donor_roots(tmp: Path, name: str, rows: dict) -> list:
    out = []
    for folder, text in rows.items():
        root = tmp / name / folder
        root.mkdir(parents=True, exist_ok=True)
        (root / "ForkDonorPatch.txt").write_text(text, encoding="utf-8")
        out.append(root)
    return out


def unit_offline_mutants(pred: dict, stock, tmp: Path) -> list:
    """``[(name, ok, detail)]``: O3-KEYS, O3-REGIONS and P-DONOR read PASS on the draft (P-DONOR on a synthetic stack
    holding today's three route rows), then FAIL on each of :data:`OFFLINE_MUTANTS` and on two P-DONOR stacks -- a
    second row `31299 63` in another folder, and none for 61."""
    checks = {"KEYS": lambda p: P.O3.keys_check(p, stock), "REGIONS": lambda p: P.O3.regions_check(p, stock)}
    base = {cid: fn(pred) for cid, fn in checks.items()}
    today = _donor_roots(tmp, "donor-today", {"FF9CustomMap": "31211 61\n31212 62\n31213 63\n31214 65\n"})
    base["P-DONOR"] = P.p_donor(pred, today)
    out = [("offline-draft-passes", all(r[0] is True for r in base.values()),
            "; ".join(f"{cid} {'PASS' if r[0] else 'FAIL: ' + r[-1][:80]}" for cid, r in base.items()))]
    for name, cid, mutate, clause in OFFLINE_MUTANTS:
        p = copy.deepcopy(pred)
        mutate(p)
        ok, _what, detail = checks[cid](p)
        caught = ok is False and clause in detail
        out.append((name, caught, f"{cid} {'FAIL' if ok is False else 'PASS (not caught)'}"
                                  + ("" if caught or ok is not False else f" -- not by {clause!r}") + f": {detail[:120]}"))
    twice = _donor_roots(tmp, "donor-twice", {"FF9CustomMap": "31211 61\n31212 62\n31213 63\n",
                                              "FF9CustomMap-other": "31299 63\n"})
    ok, detail = P.p_donor(pred, twice)
    out.append(("p-donor-63-twice", ok is False and "donor 63:" in detail and "31299" in detail, detail[:120]))
    none61 = _donor_roots(tmp, "donor-none61", {"FF9CustomMap": "31212 62\n31213 63\n"})
    ok, detail = P.p_donor(pred, none61)
    out.append(("p-donor-61-missing", ok is False and "donor 61:" in detail, detail[:120]))
    return out


# ======================================================================== the movie-skip A/B on synthetic runs
def ab_run(pred: dict, events: list, side: str, n: int, *, skipped: bool = True, t: float | None = None) -> dict:
    """A STOCK rehearsal run as o3_prima_vista.skip_ab_runs reads one (PLAN.md "Movie skip (opt-in)"): the rows the
    engine would write for ``events``, its driver log -- its visits, its battle row, its end row with the frozen end
    state -- and, on the skip side, the movie row of 61's visit: ``skipped`` 10.4 s in after one press, or (``skipped``
    False) given up. ``side`` is "no-skip" (R-FULL) or "skip" (R-FULL-SKIP); ``t`` the drive's seconds. ``raw``
    keeps the rows as the trace file holds them (a launch written to disk)."""
    raw = render(events, "S", {})
    log = visits(raw, {}) + [battle_log_row(raw, "S", {})]
    log.append({"k": "end", "field": P.END_FIELD, "frame": max(x["f"] for x in raw), "sc": 1155,
                "end_state": dict(pred["end_state"]), "t": 200.0})
    if side == "skip":
        log.insert(1, {"k": "movie", "field": 61, "donor": 61, "sc": 1155, "visit": 1, "cell": 0,
                       "presses": [{"frame": 1612, "t": 10.1}], "refused": [], "outcome": "skipped" if skipped
                       else "missed", "frame": 1700 if skipped else None, "t": 10.4 if skipped else None,
                       "dialog": {"options": ["Do you want to skip\nthe movie?", "Yes", "No"], "active": [0, 1],
                                  "selected": 1, "count": 2} if skipped else None,
                       "saved_s": 79.9 if skipped else None,
                       "missed": None if skipped else "movie-skip missed: no skip dialog after 3 press(es) 5 s apart"})
    return {"side": side, "stage": "R-FULL" if side == "no-skip" else "R-FULL-SKIP", "n": n, "raw": raw,
            "rows": T.parse_text("".join(json.dumps(x) + "\n" for x in raw)), "log": log,
            "outcome": {"end": "reached", "why": f"field {P.END_FIELD}", "battle_epoch0": EPOCH0,
                        "t": t if t is not None else (230.0 if side == "no-skip" else 140.0)},
            "start_place": 61, "end_fields": [P.END_FIELD]}


def _swap(ev: list, a, b) -> list:
    """``ev`` with the events of sites ``a`` and ``b`` trading places."""
    i = next(k for k, x in enumerate(ev) if _is(x, a))
    j = next(k for k, x in enumerate(ev) if _is(x, b))
    out = list(ev)
    out[i], out[j] = out[j], out[i]
    return out


def unit_skip_ab(pred: dict, stock) -> list:
    """``[(name, ok, detail)]``: the movie-skip A/B (o3_prima_vista.skip_ab_runs) on synthetic stock runs. Two no-skip
    runs and two skip runs of the base events -- each its own battle noise -- read EQUIVALENT; a skip run that lacks
    61's ``Byte[8] := 125`` (a key dropped) is NOT EQUIVALENT on writes and history; one whose two 62 ``Byte[4] := 0``
    stores came in the other order (the same keys, a REORDERED history) on history alone; one that played its movie
    out (its skip missed) is NOT EQUIVALENT naming it."""
    def runs(b1=None, skipped=True):
        a = [ab_run(pred, base_events(seed=0), "no-skip", 1), ab_run(pred, base_events(seed=1), "no-skip", 2)]
        b = [ab_run(pred, b1 if b1 is not None else base_events(seed=2), "skip", 1, skipped=skipped),
             ab_run(pred, base_events(seed=3), "skip", 2)]
        return P.skip_ab_runs(a, b, pred, stock=stock)

    def diffs(lines) -> list:
        return [ln.strip() for ln in lines if ln.startswith("  skip R-FULL-SKIP#1 ")]
    out = []
    ok, lines = runs()
    out.append(("skip-ab-equal", ok and lines[-1].startswith("VERDICT: EQUIVALENT"), lines[-1][:150]))
    ok, lines = runs(drop(base_events(seed=2), B8_61))
    d = diffs(lines)
    out.append(("skip-ab-key-dropped", not ok and lines[-1] == "VERDICT: NOT EQUIVALENT"
                and [x.split(":")[0] for x in d] == ["skip R-FULL-SKIP#1 writes", "skip R-FULL-SKIP#1 history"]
                and "Global.Byte[8]" in d[1], "; ".join(d)[:150]))
    ok, lines = runs(_swap(base_events(seed=2), S62[12], S62[13]))
    d = diffs(lines)
    out.append(("skip-ab-history-reordered", not ok and [x.split(":")[0] for x in d] == ["skip R-FULL-SKIP#1 history"]
                and "Global.Byte[4]" in d[0], "; ".join(d)[:150]))
    ok, lines = runs(skipped=False)
    d = diffs(lines)
    out.append(("skip-ab-not-skipped", not ok and len(d) == 1 and "skipped no movie" in d[0], "; ".join(d)[:150]))
    return out


# ======================================================================== the run
def _prepare(pred_path: Path | None, tmp: Path) -> Path:
    if pred_path is not None:
        return Path(pred_path)
    path = tmp / "o3_predictions_draft.json"
    path.write_bytes((json.dumps(P.draft_predictions(), indent=1, sort_keys=True) + "\n").encode("utf-8"))
    return path


def _clauses_named(clauses: dict, det: dict) -> list:
    return [f"{cid} detail lacks {m}" for cid, marks in clauses.items() for m in marks if m not in det.get(cid, "")]


def run_cases(pred_path: Path | None = None) -> int:
    from ff9mapkit.content.verbatim import remap_fields
    stock = T.stock_script_source()
    fails, total = 0, 0
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pdir = tmp / "pred"
        pdir.mkdir()
        sdir = tmp / "sessions"
        sdir.mkdir()
        path = _prepare(pred_path, pdir)
        pred, _sha = P.O3.load(path)
        members = members_of(pred)
        retarget = {dn: f for f, dn in members.items()}
        scripts = {fid: remap_fields(stock(dn).data, retarget) for fid, dn in members.items()}
        for name, fn, want_verdict, want, clauses, report_has, want_void, want_cov in CASES:
            total += 1
            d = make_session(sdir, path, fn(copy.deepcopy(pred)), scripts)
            checks, report = P.O3.analyse(d, stock=stock)
            got, det = result(checks), details(checks)
            v = verdict(checks)
            miss = [f"{k} {'P' if got.get(k) is True else 'F' if got.get(k) is False else 'V'}, want "
                    f"{'P' if x is True else 'F' if x is False else 'V'}" for k, x in want.items() if got.get(k) is not x]
            miss += [f"check {k} not registered" for k in got if k not in want]
            if not v.startswith(want_verdict):
                miss.append(f"verdict {v!r}, want {want_verdict}")
            miss += _clauses_named(clauses, det)
            miss += [f"report lacks {s!r}" for s in report_has if s not in report]
            runs = P.O3.read_session(d, pred, stock=stock) if (want_void or want_cov) else []
            for i, classes in want_void.items():
                have = {x["class"] for x in runs[i - 1]["void"]}
                if not set(classes) <= have:
                    miss.append(f"run {i} VOID classes {sorted(have)}, want {classes}")
            for i, cov in want_cov.items():
                if runs[i - 1]["covered"] is not cov:
                    miss.append(f"run {i} covered {runs[i - 1]['covered']}, want {cov}")
            ok = not miss
            fails += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name:30} {v[:52]:52} "
                  + " ".join(f"{k[3:]}={'P' if got.get(k) is True else 'F' if got.get(k) is False else 'V'}"
                             for k in CHECKS[1:]))
            if not ok:
                for m in miss:
                    print(f"     {m}")
                print("     " + "\n     ".join(f"{w_} :: {dd[:260]}" for _ok, w_, dd in checks))
        # O3-FROZEN: the predictions changed after the session recorded them
        total += 1
        copy_path = pdir / "pred_copy.json"
        copy_path.write_bytes(path.read_bytes())
        d = make_session(sdir, copy_path, six(pred), scripts)
        copy_path.write_bytes(path.read_bytes() + b" ")
        checks, _rep = P.O3.analyse(d, stock=stock)
        v = verdict(checks)
        got = result(checks)
        ok = got.get("O3-FROZEN") is False and v.startswith("NOT PROVEN") and all(
            got.get(k) is True for k in CHECKS if k != "O3-FROZEN")
        fails += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {'predictions-changed':30} {v[:52]}")
        units = [("no-sc-span", unit_no_sc_span),
                 ("trace-summary", lambda: unit_trace_summary(pred, stock)),
                 ("state-history", lambda: unit_state_history(pred, stock, scripts, sdir, path)),
                 ("p-donor-log", unit_p_donor_log),
                 ("p-launch", lambda: unit_p_launch(tmp)),
                 ("p-stock-battle", lambda: unit_p_stock_battle(tmp)),
                 ("p-settings", lambda: unit_p_settings(tmp)),
                 ("battle-row", lambda: unit_battle_row(pred)),
                 ("build-legacy", lambda: unit_build_legacy(tmp))]
        for name, fn in units:
            total += 1
            ok, detail = fn()
            fails += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name:30} (unit) {detail[:150]}")
        for name, ok, detail in unit_scene_census(pred) + unit_store_census(pred, stock) + \
                unit_offline_mutants(pred, stock, tmp) + unit_skip_ab(pred, stock):
            total += 1
            fails += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name:30} (unit) {detail[:150]}")
    print(f"\n{total - fails}/{total} cases as registered")
    return 1 if fails else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--predictions", type=Path, default=None,
                    help="a frozen predictions file (default: the draft, written to a temporary file)")
    sys.exit(run_cases(ap.parse_args().predictions))
