"""O5's analysis, driven on SYNTHETIC sessions (research/o5_design.md section 8): every registered check must read PASS
on the null pair and FAIL (or VOID) on the mutant built to break it -- a check that cannot fail is not a check.

    py studies/story-trace/o5_dryrun.py [--predictions studies/story-trace/o5_predictions_v1.json]

Without --predictions it reads the frozen o5_predictions_v1.json once the lead has frozen it, else it writes the DRAFT
(o5_hallway.draft_predictions: O4's chain's campaign.toml) to a temporary predictions file -- nothing is frozen until
the lead's rehearsals -- and runs every case against that.

Each case writes a session directory the way the session does (o5_session.json, the members' scripts, one trace and
one driver log per run) and runs :meth:`o5_hallway.O5Segment.analyse` on it. The rows are real store sites of the stock
bytes of 153, 154 and 151 (every field row joins but the join-failure case's), shifted onto the members on the F side
(``fld`` = member, ``don`` = donor: 153 -> 31245, 154 -> 31246, 151 -> 31244), and EMITTED as the engine's sink emits
them (StoryTrace.cs:383-401): a same-value store only while its SITE -- the field id in it -- has emitted no same-value
row (a change does not close that), a change up to 64 times, the rest counted into a ``c`` row at the epoch's close. So
153's revisit at 316 suppresses its ip22/ip49/ip138/ip200 exactly as 4.16 predicts. The start values are the raw warp's
over field 70's prologue: SC 1190, FieldEntrance 325, Byte[13] 1, Int16[9] 643, Int16[11] -1, Byte[8] 125, every other
target 0. A run's driver log carries its visit rows; 153@325's pages before the walk; THE STAIR STEP's row (``done``,
its ``frame0`` and ``lost`` bracketing no trace row, the loss at (-1479, 529)); 126 and 127 pressed under the guard (127
twice, page-once: the second its closing press); the quiet window; ``choose_landed``'s rowed presses (select's Down,
the answer's Confirm with ``selected_before`` 1); the choice row (index 1, ``took.landed``); the ``guard`` row the
driver writes at the first page after the answer (141: armed, open before 128's first sample, no stray, the pick's
branch, verdict "ok"); 141's press; the end row. Its outcome: the beats, the pages, the end state.

O5's ``case()`` is O3's, EXACT: every check a case does not name must read PASS -- a case naming COVER V expects every
core check VOID -- so each NOT PROVEN row names EVERY check it fails, and "alone" is a registered fact. A LANDING,
CHOICE, WALK, PATTERN or VOID-ASYM case also registers the clause its detail must name.

The units read the install read-only (the stock scripts, the stock walkmesh, block 3's US text): the guard's, the
witness's and the visit-scoped cell's strict readers, the guard's stray window, A-START's visit scope, the sink's
suppression as the renderer and the FakeGame's H13 implement it (one model, two implementations), O5-PATTERN's reading,
the trace summary on end places, the state history, the entrances per visit, O5-CENSUS, O5-REGIONS and O5-GOALS with
their mutants, the route pins and route_mes with theirs, O5-BUILD's route pins on a synthetic build, the offline
mutants of O5-KEYS, and the launch's and the preflight's readers (O4's units on O5's pinned values).
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
import o5_hallway as C5                                                    # noqa: E402
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
PRO153 = [(153, 0, 0, 22, "Global.Bit[191]", 0), (153, 0, 0, 49, "Global.Bit[184]", 0),
          (153, 0, 0, 57, "Global.Int16[9]", -1), (153, 0, 0, 119, "Global.Byte[13]", 0),
          (153, 0, 0, 138, "Global.Int16[11]", -1), (153, 0, 0, 200, "Global.Byte[14]", 0)]
CHOICE1741 = (153, 3, 1, 1741, "Global.Bit[3795]", 1)
B8_2953 = (153, 3, 1, 2953, "Global.Byte[8]", 0)
CH153 = (153, 3, 1, 3150, "Global.Int16[2]", 304)
PRO154 = [(154, 0, 0, 26, "Global.Bit[191]", 0), (154, 0, 0, 53, "Global.Bit[184]", 0),
          (154, 0, 0, 61, "Global.Int16[9]", -1), (154, 0, 0, 123, "Global.Byte[13]", 0),
          (154, 0, 0, 142, "Global.Int16[11]", -1), (154, 0, 0, 204, "Global.Byte[14]", 0)]
B8_279 = (154, 0, 0, 279, "Global.Byte[8]", 125)
CH154 = (154, 2, 1, 1520, "Global.Int16[2]", 316)
B8_890 = (153, 18, 1, 890, "Global.Byte[8]", 0)
CH153B = (153, 18, 1, 1077, "Global.Int16[2]", 110)
END151 = (151, 0, 0, 22, "Global.Bit[191]", 0)
AFTER151 = [(151, 0, 0, 49, "Global.Bit[184]", 0), (151, 0, 0, 57, "Global.Int16[9]", -1),
            (151, 0, 0, 119, "Global.Byte[13]", 0), (151, 0, 0, 138, "Global.Int16[11]", -1),
            (151, 0, 0, 200, "Global.Byte[14]", 0), (151, 0, 0, 315, "Global.Byte[8]", 125)]
I22, I49, I57, I119, I138, I200 = PRO153
#: Off the route, each a real store: 153's and 154's error path (Byte[13] := 9: window 56's branch); the back door's
#: two stores (153 e28 t2); 153's dead flashback store (e3 t1 ip3168); an INERT function's store (153 e32 t0 ip718,
#: instanced at 328 only); 150's prologue (the back door's landing).
ERR153_97 = (153, 0, 0, 97, "Global.Byte[13]", 9)
ERR154_101 = (154, 0, 0, 101, "Global.Byte[13]", 9)
DOOR_B8 = (153, 28, 2, 38, "Global.Byte[8]", 25)
DOOR_CH = (153, 28, 2, 227, "Global.Int16[2]", 5)
DEAD_3168 = (153, 3, 1, 3168, "Global.Byte[8]", 0)
INERT_718 = (153, 32, 0, 718, "Global.Bit[3855]", 1)
S150 = [(150, 0, 0, 26, "Global.Bit[191]", 0), (150, 0, 0, 53, "Global.Bit[184]", 0),
        (150, 0, 0, 61, "Global.Int16[9]", -1)]
SC_CS = (154, -1, -1, -1, "Global.UInt16[0]", 1190)
#: The checks, in the order the analysis reports them.
CHECKS = ("O5-FROZEN", "O5-COVER", "O5-FORBIDDEN", "O5-VOID-ASYM", "O5-START", "O5-NO-SC", "O5-CHAIN", "O5-RESIDUE",
          "O5-WRITES", "O5-NULL", "O5-STABLE", "O5-LANDING", "O5-CHOICE", "O5-WALK", "O5-PATTERN", "O5-MASKED",
          "O5-STATE", "O5-JOIN")
CORE = CHECKS[4:]
#: The frame layout of a base run (Time.frameCount, the trace's ``f`` and the log's frames alike): visit 1's prologue
#: rows near 1060-1110; the pages before the walk; THE WALK in [2000, 2400]; 126, 127 pressed; the quiet window; 128;
#: the answer; ip1741's row at 5000 (the "at" event); 141's page after it.
F_WALK0, F_LOST = 2000, 2400
F_126, F_127A, F_127B = 4300, 4500, 4650
F_OPEN, F_MARKER_LAST, F_FIRST, F_READY, F_DOWN_SEL, F_DOWN_ANS, F_CLOSE = 4720, 4700, 4750, 4760, 4790, 4800, 4810
F_1741, F_141 = 5000, 5100
#: 128 as the agent publishes it at readiness (its prompt, then its two [CHOO] lines; active the absolute indexes).
OPTIONS128 = ["Zidane\n“Hmm...”", "Let her pass", "Examine her face"]
P141, P129 = "“Let’s see...”", "“Wait.  Hold on a sec!”"
P127 = "Hooded Girl\n“Umm...\n Would you please let me pass?”"


# ======================================================================== events and their rendering
#: O5's start values (research/o5_design.md 0.2 #2, section 8): the raw warp's SC and FieldEntrance over field 70's
#: prologue (70 e0 t0 ip57/130/138/200/249; the warp leaves 70 before ip475).
START_VALUES = {"Global.UInt16[0]": 1190, "Global.Int16[2]": 325, "Global.Byte[13]": 1, "Global.Int16[9]": 643,
                "Global.Int16[11]": -1, "Global.Byte[8]": 125}


def at(frame: int) -> tuple:
    """A frame anchor: the next event's row lands at ``frame`` (later rows go on 10 frames apart)."""
    return ("at", int(frame))


def render(events: list, side: str, members: dict) -> list:
    """The rows the engine would write for ``events`` on ``side``: F-side donors on their member ids; each store's
    ``old`` the variable's value so far (:data:`START_VALUES`, every other target 0); THE SINK'S RULE per SITE (the
    field id in it, StoryTrace.cs:101-140): a same-value store emitted only while its site has emitted no same-value
    row (a change does not close that), a change up to 64 times, the rest counted into ``c`` rows just before ``off``
    in site-creation order. A store's ``opt``: ``fld``/``don`` (overrides), ``old``, ``m``, ``src``, ``add``, ``f`` (its
    row's frame, the sequence kept), ``emit`` (True: emitted whatever the rule says -- an engine that does not
    suppress at that site). An ``e`` event may carry a fourth item, ``{"fld"}``: an ``off`` in a REAL field on F."""
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
    """A base run (research/o5_design.md 8): ``arm`` in field 70; the warp's FOUR residue rows there (SC 1190's two
    bytes, FieldEntrance 325's two); 153@325's prologue; the walk and the guarded choice in the frame gap; ip1741 (0 ->
    1) at 5000, stage 30's Byte[8] and the chain; 154@304's prologue, ip279 and the chain; 153@316's prologue (four of
    its six suppressed) and its two; 151's ip22 (THE CUT), then its post-cut rows; ``off`` in 151 (member(151) on F)."""
    ev = [e("arm", 70), r(70, 0, 0, 166), r(70, 1, 0, 4), r(70, 2, 0, 69), r(70, 3, 0, 1)]
    ev += [w(s) for s in PRO153] + [at(F_1741), w(CHOICE1741), w(B8_2953), w(CH153)]
    ev += [w(s) for s in PRO154] + [w(B8_279), w(CH154)]
    ev += [w(s) for s in PRO153] + [w(B8_890), w(CH153B)]
    ev += [w(END151)] + [w(s) for s in AFTER151] + [e("off", 151)]
    return ev


def _nth(ev: list, site, n: int) -> int:
    hits = [i for i, x in enumerate(ev) if _is(x, site)]
    return hits[n]


def drop_nth(ev: list, site, n: int = 0) -> list:
    """``ev`` without the ``n``-th event of ``site`` (visit 3's prologue shares visit 1's sites)."""
    i = _nth(ev, site, n)
    return ev[:i] + ev[i + 1:]


def upto_nth(ev: list, site, n: int, *tail) -> list:
    """The run cut off after the ``n``-th event of ``site`` (a drive that stopped there), then ``tail``."""
    i = _nth(ev, site, n)
    return ev[:i + 1] + list(tail)


def edit_nth(ev: list, site, n: int, fn) -> list:
    i = _nth(ev, site, n)
    return ev[:i] + [fn(ev[i])] + ev[i + 1:]


def _fld(members: dict, side: str, donor: int) -> int:
    inv = {d: f for f, d in sorted(members.items(), reverse=True)}
    return inv.get(donor, donor) if side == "F" else donor


def visits(rows: list, members: dict) -> list:
    """The driver's ``visit`` rows for a rendered run: one each time the written field changes after the arm, in the
    route's places only (field 70's rows are the warp's; an end field is rule 1's, never a visit; a field off the
    route raises before rule 3 counts one), at the frame of the visit's first row."""
    out, cur = [], None
    for x in rows:
        if x["k"] not in ("w", "r") or x["fld"] == 70 or x["fld"] == cur:
            continue
        p = place(x["fld"], members)
        if p not in (153, 154) or (members and x["fld"] not in members):
            continue
        cur = x["fld"]
        out.append({"k": "visit", "field": cur, "donor": p, "visit": len(out) + 1, "frame": x["f"], "sc": 1190})
    return out


# ======================================================================== the run's driver log
def step_row(fld: int, *, outcome="done", attempt=1, frame0=F_WALK0, lost=(F_LOST, -1479.0, 529.0), landed=None,
             door=None, v=None, by=None, why=None) -> dict:
    """THE STAIR STEP's row as run_step writes it (2.4): its walk from the grant at (1105, -78), its loss sample
    (``lost``: frame, x, z, or None for a ``failed`` walk), the route record trimmed."""
    lo = None if lost is None else {"frame": lost[0], "control": False, "x": lost[1], "z": lost[2]}
    end = lost[0] + 10 if lost is not None else frame0 + 300
    return {"k": "step", "field": fld, "donor": 153, "sc": 1190, "visit": 1, "n": 0, "kind": "trigger",
            "name": "the stairs", "attempt": attempt, "outcome": outcome, "t0": 30.0, "t1": 34.0, "frame0": frame0,
            "frame": end, "from": {"frame": frame0, "control": True, "x": 1105.0, "z": -78.0},
            "to": {"frame": end, "control": False, "x": None if lo is None else lo["x"],
                   "z": None if lo is None else lo["z"]},
            "lost": lo, "landed": landed, "flip_frame": None, "door": door,
            "route": {"route": 3, "travelled": 3196.0, "replans": 0, "pushes": 0, "waits": 0, "blockers": []},
            "lunge": None, "climb": None, "depth": None, "v": v, "by": by, "why": why}


def standard_log(pred: dict, side: str, rows: list) -> tuple:
    """A run's driver log as the drive writes it (research/o5_design.md 2.2), and the handles a case edits: ``(log,
    ctx)``. Visit 1 (153@325): its visit row, 113-117's presses, THE STAIR STEP, 126's press, 127's two (page-once: the
    first dropped in its opening, the second its CLOSING press, down before 127's last listed sample), the quiet row,
    ``choose_landed``'s rowed presses (Down; the answer's Confirm, ``selected_before`` 1), the choice row, the ``guard``
    row written at the first page after the answer (141), 141's press; visit 2's and visit 3's visit rows; every press
    under the guard a row with its ``seq``. ``ctx``: ``presses`` (by name), ``step``, ``choice``, ``guard``."""
    members = members_of(pred) if side == "F" else {}
    fld153 = _fld(members, side, 153)
    vis = visits(rows, members)
    base = {"field": fld153, "donor": 153, "visit": 1, "sc": 1190}
    seqs = iter(range(101, 100000))

    def press(why, frame, texts, *, marker=False, accepted=None):
        acc = frame + 1 if accepted is None else accepted
        return {"k": "press", "why": why, **base, "pre": {"frame": frame, "control": False, "x": 1105.0, "z": -78.0},
                "post": None, "near": [], "seq": next(seqs), "ack_frame": frame + 5, "button": "confirm",
                "raws": [f"[STRT=0,0]{t}" for t in texts], "marker": marker, "texts": list(texts),
                "accepted_frame": acc, "down_frame": acc + 1}
    presses = {f"p{m}": press("page", 1300 + 50 * i, [f"153 mes {m}"]) for i, m in enumerate((113, 114, 115, 116, 117))}
    presses["p126"] = press("page", F_126, ["153 mes 126"])
    presses["p127a"] = press("page", F_127A, [P127], marker=True)
    presses["p127b"] = press("page", F_127B, [P127], marker=True, accepted=F_MARKER_LAST - 14)
    sel = {"k": "press", "why": "choose", "button": "down", "seq": next(seqs), **base, "pre": None, "post": None,
           "near": [], "accepted_frame": F_DOWN_SEL - 1, "down_frame": F_DOWN_SEL, "selected_before": 0,
           "answer": False}
    ans = {"k": "press", "why": "choose", "button": "confirm", "seq": next(seqs), **base, "pre": None, "post": None,
           "near": [], "accepted_frame": F_DOWN_ANS - 1, "down_frame": F_DOWN_ANS, "selected_before": 1,
           "answer": True}
    presses.update(sel=sel, ans=ans)
    took = {"index": 1, "text": OPTIONS128[2], "prompt": OPTIONS128[0], "count": 2, "field": fld153,
            "frame": F_DOWN_ANS, "landed": True, "confirms": 1, "why": "landed: the choice stopped taking answers"}
    choice = {"k": "choice", "field": fld153, "donor": 153, "sc": 1190, "frame": F_READY, "options": list(OPTIONS128),
              "active": [0, 1], "selected": 0, "count": 2, "index": 1, "rule": 0, "took": took}
    quiet = {"k": "quiet", "field": fld153, "visit": 1, "armed_frame": F_127A, "open_frame": F_OPEN,
             "open_game": ["mtime", 77.5], "rearms": 0}
    order = ["p113", "p114", "p115", "p116", "p117", "p126", "p127a", "p127b"]
    guard_presses = [{"seq": presses[n]["seq"], "why": presses[n]["why"], "marker": presses[n].get("marker", False),
                      "accepted_frame": presses[n]["accepted_frame"], "down_frame": presses[n]["down_frame"],
                      "decision_frame": (presses[n].get("pre") or {}).get("frame"), "raws": presses[n].get("raws")}
                     for n in order + ["sel", "ans"]]
    guard = {"k": "guard", "field": fld153, "visit": 1, "armed_frame": F_127A, "open_frame": F_OPEN, "rearms": 0,
             "marker_last": F_MARKER_LAST, "choice_first": F_FIRST, "choice_ready": F_READY, "choice_close": F_CLOSE,
             "answer": [presses["p127b"]["seq"], ans["seq"]], "closing_seq": presses["p127b"]["seq"],
             "presses": guard_presses, "strays": [], "branch": "pick", "branch_frame": F_141,
             "branch_raw": [f"[ZDNE]\n{P141}"], "verdict": "ok"}
    p141 = press("page", F_141, [P141])
    step = step_row(fld153)
    log = vis[:1] + [presses[n] for n in order[:5]] + [step, presses["p126"], presses["p127a"], presses["p127b"],
                                                       quiet, sel, ans, choice, guard, p141] + vis[1:]
    return log, {"presses": presses, "step": step, "choice": choice, "guard": guard, "quiet": quiet, "p141": p141,
                 "visits": vis}


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
    eng = {"x64": C5.ENGINE["x64"], "x86": C5.ENGINE["x86"]}
    rows = []
    ok, detail = C4.p_text(3, [("FF9CustomMap", dict(text))], text, o1_block2=None, o4_registered=True)
    rows.append([ok, C5.O5.title("P-TEXT3"), detail])
    ok, detail = C4.p_engine(dict(eng), C5.ENGINE)
    rows.append([ok, C5.O5.title("P-ENGINE"), detail])
    assert all(x[0] for x in rows), rows
    return rows


def make_session(tmp: Path, pred_path: Path, runs: list, scripts: dict) -> Path:
    """A session directory as O5Segment.run writes one. Each run: ``{side, events | rows, end?, why?, beats?, v?, cell?,
    by?, install?, end_state?, end_field?, log? (fn(log, ctx) -> log, editing the standard log), pages? (fn(pages))}``."""
    pred, sha = C5.O5.load(pred_path)
    members = members_of(pred)
    d = tmp / f"s{len(list(tmp.iterdir()))}"
    (d / "scripts").mkdir(parents=True)
    for fid, data in scripts.items():
        (d / "scripts" / f"{fid}.eb").write_bytes(data)
    session = {"label": d.name, "predictions": str(pred_path), "predictions_sha256": sha,
               "predictions_version": pred["version"], "order": pred["order"], "budget": pred["budget"],
               "preflight": preflight_rows(),
               "install": {"settings": pred["settings"], "engine": {"x64": C5.ENGINE["x64"], "x86": C5.ENGINE["x86"]}},
               "runs": [], "ended": {"log": [{"k": "recover-warp", "field": 4600}], "ok": True, "why": ""}}
    for i, run in enumerate(runs, 1):
        side = run["side"]
        rows = run.get("rows") if run.get("rows") is not None else render(run["events"], side, members)
        name, log_name = f"run{i}_{side}.jsonl", f"run{i}_{side}_log.json"
        (d / name).write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
        log, ctx = standard_log(pred, side, rows)
        if callable(run.get("log")):
            log = run["log"](log, ctx)
        end = run.get("end", "reached")
        end_state = run.get("end_state", dict(pred["end_state"]) if end == "reached" else None)
        if end == "reached":
            last = max((x["f"] for x in rows), default=0)
            log.append({"k": "end", "field": run.get("end_field", ST.side_ends(pred, side)[0]), "frame": last,
                        "sc": 1190, "end_state": end_state, "t": 280.0, "end_row": {"seen": True, "f": last, "s": 0.1}})
        pages = [f"153 mes {m}" for m in (113, 114, 115, 116, 117, 126)] + [P127, P141]
        if callable(run.get("pages")):
            pages = run["pages"](pages)
        beats = run.get("beats", {"stairs": True, "choice128": True})
        outcome = {"end": end, "why": run.get("why", f"field {ST.side_ends(pred, side)[0]}" if end == "reached"
                                              else "route: stopped"),
                   "void": None, "beats": beats, "pages": pages, "timed": [],
                   "choices": [x for x in log if x.get("k") == "choice"],
                   "steps": [x for x in log if x.get("k") == "step"], "overlays": [], "forbidden": [],
                   "end_state": end_state, "t": 280.0}
        (d / log_name).write_text(json.dumps({"outcome": outcome, "log": log}), encoding="utf-8")
        rec = {"i": i, "side": side, "start": pred["start"][side], "trace": name, "log": log_name, "end": end,
               "why": outcome["why"], "beats": beats}
        for k in ("v", "cell", "by", "install"):
            if run.get(k) is not None:
                rec[k] = run[k]
        session["runs"].append(rec)
    (d / C5.SESSION_FILE).write_text(json.dumps(session), encoding="utf-8")
    return d


def result(checks) -> dict:
    return {w_.split(":")[0]: ok for ok, w_, _d in checks}


def details(checks) -> dict:
    return {w_.split(":")[0]: d_ for _ok, w_, d_ in checks}


# ======================================================================== the cases
CASES = []


def case(name, want_verdict, *, fail=(), clauses=None, cover_void=False, report_has=(), void=None, covered=None,
         lacks=None):
    """Register a case, EXACT (O3's ``case()``): ``fail`` the checks that must read FAIL, ``clauses`` ``{check:
    [markers]}`` the clauses its detail must name (each such check FAILS too), ``cover_void`` -- COVER VOID and every
    core check VOID ("too few covered runs"); every other check must read PASS. ``report_has`` substrings of the
    report, ``void`` ``{run index: [classes its VOID reasons must include]}``, ``lacks`` ``{run index: [classes they
    must NOT include]}``, ``covered`` ``{run index: bool}``."""
    want = {c: True for c in CHECKS}
    if cover_void:
        want["O5-COVER"] = None
        want.update({c: None for c in CORE})
    clauses = {("O5-" + k): v for k, v in (clauses or {}).items()}
    for c in list(fail) + list(clauses):
        cid = c if c.startswith("O5-") else "O5-" + c
        want[cid] = False

    def deco(fn):
        CASES.append((name, fn, want_verdict, want, clauses, tuple(report_has), void or {}, covered or {}, lacks or {}))
        return fn
    return deco


def _void(run: dict, v: str, cell, by: str, why: str, *, events=None, log=None) -> None:
    """A run stopped: its events replaced (``events``), its drive VOID in class ``v`` at ``cell``, its log edited."""
    if events is not None:
        run["events"] = events
    run.update(end="void", why=f"route: {why}", v=v, cell=cell, by=by)
    if log is not None:
        run["log"] = log


def _stop_v1(ev: list, *, tail=()) -> list:
    """A run stopped in visit 1 after the guarded choice (its ip1741 row the last), then ``tail`` and ``off``."""
    return upto_nth(ev, CHOICE1741, 0, *tail, e("off", 153))


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


@case("null-pair", "PROVEN", report_has=("a US session", "block 3: 7 byte-equal of 7", "start dependence -- under the "
                                         "raw warp", "suppressed stores -- the four suppressed stores",
                                         "the stored choice -- the stored value", "the end state -- Byte[8] is read",
                                         "RACE MARGIN 60 frames", "attempt 1 done", "visit 3's first (153, 0, 0, 51",
                                         "The session's end (end_run, warp first): the title came back"))
def _(pred):
    return six(pred)


@case("fork-drops-a-write", "NOT PROVEN", fail=("WRITES", "NULL", "STATE"), clauses={"PATTERN": ["(b)"]})
def _(pred):
    return six(pred, f=lambda ev, n: drop_nth(ev, B8_279))


@case("chain-dropped-fork", "NOT PROVEN", fail=("CHAIN", "WRITES", "NULL", "STATE"),
      clauses={"LANDING": ["(b)"], "PATTERN": ["(b)"]})
def _(pred):
    return six(pred, f=lambda ev, n: drop_nth(ev, CH154))


@case("chain-first-old-wrong", "NOT PROVEN", fail=("CHAIN",))
def _(pred):
    old = lambda ev, n: edit(ev, lambda x: _is(x, CH153), lambda x: with_opt(x, old=326))   # noqa: E731
    return six(pred, s=old, f=old)


@case("start-residue-three", "NOT PROVEN", fail=("START",))
def _(pred):
    return six(pred, s=lambda ev, n: [x for x in ev if not (x[0] == "r" and x[2] == 3)])


@case("start-residue-wrong", "NOT PROVEN", fail=("START",))
def _(pred):
    return six(pred, s=lambda ev, n: edit(ev, lambda x: x[0] == "r" and x[2] == 3, lambda x: r(70, 3, 0, 2)))


@case("start-first-missing", "NOT PROVEN", fail=("START",), clauses={"LANDING": ["(b)"], "PATTERN": ["(a)", "(b)"]})
def _(pred):
    """Visit 1's ip22 dropped on both sides: 153's first write is ip49 (START (b)); the ip22 SITE then first stores at
    visit 3 -- a new site in the epoch, so the sink EMITS it (same 1) instead of counting it: visit 3's first emitted row
    is ip22, not ip57 (LANDING (b)), the c rows lack ip22's count and the visits' sequences differ (PATTERN (a)(b)).
    MASKED reads region names, and both sides still write Bit[191]: it passes."""
    gone = lambda ev, n: drop_nth(ev, I22)                                 # noqa: E731
    return six(pred, s=gone, f=gone)


@case("start-music-old-wrong", "NOT PROVEN", fail=("START",))
def _(pred):
    old = lambda ev, n: edit_nth(ev, I119, 0, lambda x: with_opt(x, old=3))   # noqa: E731
    return six(pred, s=old, f=old)


@case("front-cut-write", "NOT PROVEN", fail=("START",))
def _(pred):
    in70 = ("w", 70, 3, 1, 40, "Global.Byte[13]", 1, {})              # a store in field 70, before the start
    return six(pred, f=lambda ev, n: before(ev, I22, in70))


@case("error-path-start-S", "PROVEN", void={1: ["V5", "A-START"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    runs = six(pred)
    ev = drop_nth(runs[0]["events"], I119)
    _void(runs[0], "V5", [153, 1190, 1], "driver", "a stop page (153's ambient error window 56), nothing pressed",
          events=upto_nth(ev, I57, 0, w(ERR153_97), e("off", 153)))
    return runs


@case("error-path-154-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={2: False})
def _(pred):
    runs = six(pred)
    ev = drop_nth(runs[1]["events"], PRO154[3])
    _void(runs[1], "V5", [154, 1190, 2], "game", "a stop page (154's ambient error window 56), nothing pressed",
          events=upto_nth(ev, PRO154[2], 0, w(ERR154_101), e("off", 154)))
    return runs


@case("error-path-316-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={2: False}, void={2: ["V5"]},
      lacks={2: ["A-START"]})
def _(pred):
    """Visit 3's 153 takes the error path (an F run): V5 by the GAME at [153, 1190, 3] -- VOID-ASYM (a) -- and NO A-START:
    its error row lies after the run's first row of 154 (the claim critique #7)."""
    runs = six(pred)
    ev = drop_nth(runs[1]["events"], I119, 1)
    _void(runs[1], "V5", [153, 1190, 3], "game", "a stop page (153's ambient error window 56 at the revisit)",
          events=upto_nth(ev, I57, 1, w(ERR153_97), e("off", 153)))
    return runs


@case("residue-after-start", "NOT PROVEN", fail=("RESIDUE",))
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, I22, r(153, 300, 0, 7)))


@case("writes-extra-symmetric", "NOT PROVEN", fail=("WRITES",), clauses={"PATTERN": ["(b)"]})
def _(pred):
    add = lambda ev, n: after(ev, B8_2953, w(DEAD_3168))               # noqa: E731
    return six(pred, s=add, f=add)


@case("inert-row-both", "NOT PROVEN", fail=("WRITES",), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """An inert function's row in every covered run (153 e32 t0 ip718 Bit[3855] := 1: e32 is instanced at 328 only) is
    an extra key, and an extra entry of visit 1's emitted sequence."""
    add = lambda ev, n: after(ev, B8_2953, w(INERT_718))               # noqa: E731
    return six(pred, s=add, f=add)


@case("extra-key-one-F", "NOT PROVEN", fail=("STABLE", "WRITES", "STATE"), clauses={"PATTERN": ["(b)"]})
def _(pred):
    """STABLE's mutant (the claim critique #9): one F run of three holds 153 e3 t1 ip3168's store."""
    return six(pred, f=lambda ev, n: after(ev, B8_2953, w(DEAD_3168)) if n == 0 else ev)


@case("sc-write-fork", "NOT PROVEN", fail=("NO-SC", "WRITES", "NULL", "STATE"))
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, B8_279, w(SC_CS, src="cs")))


@case("sc-harness-poke-both", "NOT PROVEN", fail=("NO-SC",))
def _(pred):
    poke = lambda ev, n: after(ev, B8_2953, w((153, -1, -1, -1, "Global.Byte[0]", 7), src="harness"))  # noqa: E731
    return six(pred, s=poke, f=poke)


@case("bit3795-zero-F", "NOT PROVEN", fail=("WRITES", "NULL", "STATE"), clauses={"CHOICE": ["(c)"],
                                                                               "PATTERN": ["(b)"]})
def _(pred):
    """"A fork that stores a constant": every F run's ip1741 := 0 (its branch page still the pick's -- SYSVAR[9] was 1),
    the end state's Bit[3795] 0; the log unchanged (index 1)."""
    runs = six(pred, f=lambda ev, n: edit(ev, lambda x: _is(x, CHOICE1741), lambda x: ("w", *x[1:6], 0, x[7])))
    for run in runs:
        if run["side"] == "F":
            run["end_state"] = dict(pred["end_state"], **{"Global.Bit[3795]": 0})
    return runs


@case("choice-second-1741-both", "NOT PROVEN", clauses={"CHOICE": ["(a)"], "PATTERN": ["(b)"]})
def _(pred):
    """A second ip1741 store 1 -> 1: the site's first SAME-VALUE store, so EMITTED (``same`` 1) -- the second ``w``
    row CHOICE (a) counts (the claim critique #8)."""
    again = lambda ev, n: after(ev, CHOICE1741, w(CHOICE1741))         # noqa: E731
    return six(pred, s=again, f=again)


@case("choice-third-1741-both", "NOT PROVEN", clauses={"CHOICE": ["(a)"], "PATTERN": ["(a)", "(b)"]})
def _(pred):
    again = lambda ev, n: after(ev, CHOICE1741, w(CHOICE1741), w(CHOICE1741))   # noqa: E731
    return six(pred, s=again, f=again)


@case("choice-index-0-both", "NOT PROVEN", fail=("WRITES",), clauses={"CHOICE": ["(b)"], "PATTERN": ["(b)"]})
def _(pred):
    """The log's index 0 and the trace's 0 (a symmetric pick of the other line): NULL and STATE cannot see it."""
    runs = six(pred, s=lambda ev, n: edit(ev, lambda x: _is(x, CHOICE1741), lambda x: ("w", *x[1:6], 0, x[7])),
               f=lambda ev, n: edit(ev, lambda x: _is(x, CHOICE1741), lambda x: ("w", *x[1:6], 0, x[7])))
    return _all(runs, log=_edit_log(lambda c: c["choice"].update(index=0)))


@case("choice-unlanded-both", "NOT PROVEN", clauses={"CHOICE": ["(b)"]})
def _(pred):
    return _all(six(pred), log=_edit_log(lambda c: c["choice"]["took"].update(landed=False)))


@case("choice-cursor-off-pick-both", "NOT PROVEN", clauses={"CHOICE": ["(b)"]})
def _(pred):
    return _all(six(pred), log=_edit_log(lambda c: c["presses"]["ans"].update(selected_before=0)))


@case("choice-branch-other-both", "NOT PROVEN", clauses={"CHOICE": ["(b)"]})
def _(pred):
    """The guard row's ``branch`` "other" with ``verdict`` "ok": only a bypassed judgment could cover such a run."""
    return _all(six(pred), log=_edit_log(lambda c: c["guard"].update(branch="other")))


@case("choice-store-before-answer-both", "NOT PROVEN", clauses={"CHOICE": ["(c)"]})
def _(pred):
    early = lambda ev, n: edit(ev, lambda x: _is(x, CHOICE1741), lambda x: with_opt(x, f=F_DOWN_ANS - 50))  # noqa: E731
    return six(pred, s=early, f=early)


def _stray_press(c: dict) -> None:
    """A page press of the driver's down inside [marker_last, choice_close), the guard row's ``strays`` [] and its
    verdict "ok" (a bypassed judgment)."""
    g = c["guard"]
    g["presses"].insert(-2, {"seq": 999, "why": "page", "marker": False, "accepted_frame": F_FIRST + 4,
                             "down_frame": F_FIRST + 5, "decision_frame": F_FIRST - 2, "raws": [f"[STRT=0,0]{P127}"]})


@case("choice-stray-press-both", "NOT PROVEN", clauses={"CHOICE": ["(d)"]})
def _(pred):
    return _all(six(pred), log=_edit_log(_stray_press))


@case("choice-no-quiet-both", "NOT PROVEN", clauses={"CHOICE": ["(d)"]})
def _(pred):
    return _all(six(pred), log=_edit_log(lambda c: c["guard"].update(open_frame=None)))


@case("choice-never-armed-both", "NOT PROVEN", clauses={"CHOICE": ["(d)"]})
def _(pred):
    return _all(six(pred), log=_edit_log(lambda c: c["guard"].update(armed_frame=None)))


@case("choice-open-at-first-both", "PROVEN")
def _(pred):
    """128's first sample was the first without 127 (the agent publishes every 2 frames, 128 opens ~2 ticks after 127
    is gone): ``open_frame`` == ``choice_first`` -- correct, never a stray (the driver critique #2)."""
    return _all(six(pred), log=_edit_log(lambda c: c["guard"].update(open_frame=F_FIRST)))


@case("choice-closing-press-late-both", "PROVEN")
def _(pred):
    """127's closing press goes down AFTER ``marker_last`` -- the ring held no sample of 127's close tween (O4's
    rehearsal 2229/2237 shape) -- inside the window: excluded as the closing press, by proof (S10)."""
    def late(c):
        g = c["guard"]
        p = next(x for x in g["presses"] if x["seq"] == g["closing_seq"])
        p.update(accepted_frame=F_MARKER_LAST + 4, down_frame=F_MARKER_LAST + 5)
        assert F_MARKER_LAST <= p["down_frame"] < F_CLOSE
    return _all(six(pred), log=_edit_log(late))


def _path0(ev: list) -> list:
    """Path 0's rows: ip1741 := 0 (the game took the other answer), the run stopped at the judgment."""
    ev = edit(ev, lambda x: _is(x, CHOICE1741), lambda x: ("w", *x[1:6], 0, x[7]))
    return _stop_v1(ev)


@case("v17-stray-one-S", "PROVEN", void={1: ["V17"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    runs = six(pred)
    _void(runs[0], "V17", [153, 1190, 1], "driver", "a press of the driver's own (seq 999, page) went down in [the "
                                                     "marker page's last sample, the guarded choice's close) before "
                                                     "its answer", events=_path0(runs[0]["events"]))
    return runs


@case("v17-unlanded-one-F", "PROVEN", void={2: ["V17"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    runs = six(pred)
    _void(runs[1], "V17", [153, 1190, 1], "driver", "the answer 1 did not land: did not land",
          events=upto_nth(runs[1]["events"], I200, 0, e("off", 153)))
    return runs


@case("v17-never-armed-one-F", "PROVEN", void={2: ["V17"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    runs = six(pred)
    _void(runs[1], "V17", [153, 1190, 1], "driver", "the marker page was closed by a press page-once did not make",
          events=_stop_v1(runs[1]["events"]))
    return runs


@case("v17-unplaceable-one-S", "PROVEN", void={1: ["V17"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    runs = six(pred)
    _void(runs[0], "V17", [153, 1190, 1], "driver", "the answer's Confirm could not be placed: no accepted event",
          events=upto_nth(runs[0]["events"], I200, 0, e("off", 153)))
    return runs


@case("v13-input-one-F", "PROVEN", void={2: ["V13"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    runs = six(pred)
    _void(runs[1], "V13", [153, 1190, 1], "driver", "outside input: XInput slot 0: buttons 0x1000",
          events=upto_nth(runs[1]["events"], I200, 0, e("off", 153)))
    return runs


@case("v13-choice-gone-one-F", "PROVEN", void={2: ["V13"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    """128 gone with no press of the driver's in its window: unattributed input, the driver's V13 -- no ``observed``
    row (the claim critique #4), so VOID-ASYM (d) does not read it."""
    runs = six(pred)
    _void(runs[1], "V13", [153, 1190, 1], "driver", "the guarded choice left with no press of the driver's in [the "
                                                     "marker page's last sample, its close): unattributed input",
          events=_stop_v1(runs[1]["events"]))
    return runs


@case("v13-other-branch-one-S", "PROVEN", void={1: ["V13"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    runs = six(pred)
    _void(runs[0], "V13", [153, 1190, 1], "driver", "the game took the other branch (its first page holds 'Hold on a "
                                                     "sec'): the answer it took is not the pick",
          events=_path0(runs[0]["events"]))
    return runs


@case("v13-cap-all-F", "NOT PROVEN", cover_void=True, clauses={"VOID-ASYM": ["(b)"]})
def _(pred):
    """Every F run VOID V13 "no choice read within the cap" at [153, 1190, 1]: a fork that never asks 128 -- VOID-ASYM
    (b) reads it, never a VOID."""
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            _void(run, "V13", [153, 1190, 1], "driver", "no choice read within 4 s of the quiet window's opening",
                  events=upto_nth(run["events"], I200, 0, e("off", 153)))
    return runs


@case("v2-reask-one-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={2: False})
def _(pred):
    runs = six(pred)
    _void(runs[1], "V2", [153, 1190, 1], "game", "the guarded choice was asked again after its verified answer",
          events=_stop_v1(runs[1]["events"]))
    return runs


@case("v4-control-154-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={2: False})
def _(pred):
    runs = six(pred)
    _void(runs[1], "V4", [154, 1190, 2], "game", "control held in 31246 (place 154) at SC 1190, where the table has no "
                                                  "entry", events=upto_nth(runs[1]["events"], B8_279, 0,
                                                                           e("off", 154)))
    return runs


@case("v4-control-316-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={2: False})
def _(pred):
    runs = six(pred)
    _void(runs[1], "V4", [153, 1190, 3], "game", "control held in 31245 (place 153) at SC 1190, where the table has no "
                                                  "entry", events=upto_nth(runs[1]["events"], I57, 1, e("off", 153)))
    return runs


@case("v4-visit1-S-visit3-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(a) V4 at [153, 1190, 1] (game) on S only",
                                                                  "(a) V4 at [153, 1190, 3] (game) on F only"]},
      covered={1: False, 2: False})
def _(pred):
    """One S run V4 at [153, 1190, 1] (control after the stair step), one F run V4 at [153, 1190, 3]: under
    ``[donor, sc]`` cells they would cancel (the claim critique #5); visit-scoped, each side's is its own."""
    runs = six(pred)
    _void(runs[0], "V4", [153, 1190, 1], "game", "control held in 153 (place 153) at SC 1190 after the cell's last step",
          events=upto_nth(runs[0]["events"], I200, 0, e("off", 153)))
    _void(runs[1], "V4", [153, 1190, 3], "game", "control held in 31245 (place 153) at SC 1190, where the table has no "
                                                  "entry", events=upto_nth(runs[1]["events"], I57, 1, e("off", 153)))
    return runs


@case("v19-one-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)", "(c)"]}, covered={2: False})
def _(pred):
    """One F run lands in REAL 151 (an un-retargeted Field()): V19 by the game at [151, 1190, 3] (rule 2 runs before the
    visit counts); the drive stops there, its trace ending in real 151 after 151's first store -- cut away as place 151,
    the run uncovered, and VOID-ASYM reads the finding."""
    runs = six(pred)
    ev = edit(runs[1]["events"], lambda x: x[0] == "w" and x[1] == 151, lambda x: with_opt(x, fld=151, don=151))
    _void(runs[1], "V19", [151, 1190, 3], "game", "the fork run entered REAL 151, where member(151) 31244 was due",
          events=upto_nth(ev, END151, 0, ("e", "off", 151, {"fld": 151})))
    return runs


@case("leak-real-154-F", "NOT PROVEN", fail=("FORBIDDEN",), clauses={"VOID-ASYM": ["(a)", "(c)"]}, covered={2: False})
def _(pred):
    """One F run enters REAL 154 from member(153) (an engine id leak): V19 by the game at [154, 1190, 1] -- rule 2 runs
    before rule 3 counts the visit; its rows at fld 154 are off the route on F and nothing in its log backs them."""
    runs = six(pred)
    real = edit(runs[1]["events"], lambda x: x[0] == "w" and x[1] == 154, lambda x: with_opt(x, fld=154, don=154))
    _void(runs[1], "V19", [154, 1190, 1], "game", "the fork run entered REAL 154, where member(154) 31246 was due",
          events=upto_nth(real, PRO154[5], 0, ("e", "off", 154, {"fld": 154})))
    return runs


def _door(run: dict, side: str, *, backed: bool) -> None:
    """The back door (153 e28): the stair walk strays into its quad -- its two stores (300 frames into the walk), then
    150's prologue (member(150) 31243 on F) -- backed by the stair step's row V11 ``door`` 153.e28 ``landed`` 150 /
    31243, its walk begun before the hits (SD.backing's ``frame0`` rule), when ``backed``."""
    ev = upto_nth(run["events"], I200, 0, at(F_WALK0 + 300), w(DOOR_B8), w(DOOR_CH), *[w(s) for s in S150],
                  e("off", 150))
    land = 150 if side == "S" else 31243

    def log(lg, c):
        st = c["step"]
        i = lg.index(st)
        st.update(outcome="void", v="V11", by="driver", door="153.e28", landed=land,
                  why=f"the trigger's walk left 153: landed in {land} (place 150)",
                  lost={"frame": F_WALK0 + 295, "control": False, "x": 2300.0, "z": 150.0})
        return lg[:i + 1] if backed else lg[:i]
    if backed:
        _void(run, "V11", [153, 1190, 1], "driver", "the trigger's walk left 153: landed in 150", events=ev, log=log)
    else:
        _void(run, "V11", [150, 1190, 1], "game", f"left the route: entered {land} (place 150)", events=ev, log=log)


@case("back-door-S", "PROVEN", void={1: ["V11", "A-FORBIDDEN"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    """One S run walks into the back door (e28): its two stores in 153, then rows in 150 -- off the route, BACKED by
    the step row's V11 landing in 150 (4.7's walk backing): A-FORBIDDEN, never a finding."""
    runs = six(pred)
    _door(runs[0], "S", backed=True)
    return runs


@case("back-door-unbacked-F", "NOT PROVEN", fail=("FORBIDDEN",), clauses={"VOID-ASYM": ["(a)"]}, covered={2: False})
def _(pred):
    """One F run holds e28's rows and rows in 31243 that no step row explains (the fork walked him there): FORBIDDEN's
    finding; its drive VOID V11 by the game (rule 2, no walk behind it) is on F only -- VOID-ASYM (a)."""
    runs = six(pred)
    _door(runs[1], "F", backed=False)
    return runs


@case("v7-walk-all-F", "NOT PROVEN", cover_void=True, clauses={"VOID-ASYM": ["(b)"]})
def _(pred):
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            _void(run, "V7", [153, 1190, 1], "driver", "step the stairs (trigger) failed 2 of its 2 attempts",
                  events=upto_nth(run["events"], I200, 0, e("off", 153)))
    return runs


@case("walk-never-contour-one-S", "PROVEN", void={1: ["V7"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    runs = six(pred)

    def log(lg, c):
        i = lg.index(c["step"])
        a = step_row(c["step"]["field"], outcome="failed", lost=None, frame0=F_WALK0,
                     why="the walk ended with control held and nothing took it")
        b = step_row(c["step"]["field"], outcome="failed", attempt=2, lost=None, frame0=F_WALK0 + 500,
                     why="the walk ended with control held and nothing took it")
        return lg[:i] + [a, b]
    _void(runs[0], "V7", [153, 1190, 1], "driver", "step the stairs (trigger) failed 2 of its 2 attempts",
          events=upto_nth(runs[0]["events"], I200, 0, e("off", 153)), log=log)
    return runs


def _walk(steps_fn):
    """A log edit replacing the stair step's row by ``steps_fn(field)``'s rows, in order."""
    def log(lg, c):
        i = lg.index(c["step"])
        return lg[:i] + steps_fn(c["step"]["field"]) + lg[i + 1:]
    return log


@case("walk-interrupted-once-both", "PROVEN")
def _(pred):
    return _all(six(pred), log=_walk(lambda fld: [
        step_row(fld, outcome="interrupted", frame0=F_WALK0, lost=(F_WALK0 + 150, 120.0, 1500.0),
                 why="control went at (120, 1500) without the step's evidence"),
        step_row(fld, attempt=2, frame0=F_WALK0 + 200)]))


@case("walk-failed-once-both", "PROVEN")
def _(pred):
    """A first walk that ended with control held (``failed``: no ``lost``, ``landed`` None) then ``done``: admitted by
    WALK (a) (the driver critique #3)."""
    return _all(six(pred), log=_walk(lambda fld: [
        step_row(fld, outcome="failed", frame0=F_WALK0, lost=None,
                 why="the walk ended with control held and nothing took it"),
        step_row(fld, attempt=2, frame0=F_WALK0 + 320)]))


@case("walk-no-step-both", "NOT PROVEN", clauses={"WALK": ["(a)"]})
def _(pred):
    return _all(six(pred), log=_walk(lambda fld: []))


@case("walk-lost-east-both", "NOT PROVEN", clauses={"WALK": ["(a)"]})
def _(pred):
    return _all(six(pred), log=_walk(lambda fld: [step_row(fld, lost=(F_LOST, -900.0, 529.0))]))


@case("walk-two-interrupts-both", "NOT PROVEN", clauses={"WALK": ["(a)"]})
def _(pred):
    return _all(six(pred), log=_walk(lambda fld: [
        step_row(fld, outcome="interrupted", frame0=F_WALK0, lost=(F_WALK0 + 60, 120.0, 1500.0)),
        step_row(fld, outcome="interrupted", attempt=2, frame0=F_WALK0 + 100, lost=(F_WALK0 + 160, 0.0, -1200.0)),
        step_row(fld, attempt=3, frame0=F_WALK0 + 200)]))


@case("walk-interrupt-in-door-both", "NOT PROVEN", clauses={"WALK": ["(a)"]})
def _(pred):
    return _all(six(pred), log=_walk(lambda fld: [
        step_row(fld, outcome="interrupted", frame0=F_WALK0, lost=(F_WALK0 + 150, 2300.0, 150.0), door="153.e28"),
        step_row(fld, attempt=2, frame0=F_WALK0 + 200)]))


@case("walk-two-failed-both", "NOT PROVEN", clauses={"WALK": ["(a)"]})
def _(pred):
    return _all(six(pred), log=_walk(lambda fld: [
        step_row(fld, outcome="failed", frame0=F_WALK0, lost=None),
        step_row(fld, outcome="failed", attempt=2, frame0=F_WALK0 + 100, lost=None),
        step_row(fld, attempt=3, frame0=F_WALK0 + 200)]))


@case("walk-failed-in-door-both", "NOT PROVEN", clauses={"WALK": ["(a)"]})
def _(pred):
    return _all(six(pred), log=_walk(lambda fld: [
        step_row(fld, outcome="failed", frame0=F_WALK0, lost=None, door="153.e28"),
        step_row(fld, attempt=2, frame0=F_WALK0 + 320)]))


@case("walk-window-late-row-both", "NOT PROVEN", clauses={"WALK": ["(b)"]})
def _(pred):
    """Visit 1's ip200 row stamped INSIDE the walk window, its order kept: WRITES, MASKED and PATTERN (which read keys,
    names and order) cannot see it; WALK (b) reads frames."""
    late = lambda ev, n: edit_nth(ev, I200, 0, lambda x: with_opt(x, f=F_WALK0 + 200))   # noqa: E731
    return six(pred, s=late, f=late)


@case("walk-window-masked-write-both", "NOT PROVEN", clauses={"WALK": ["(b)"], "PATTERN": ["(b)"]})
def _(pred):
    """An extra Bit[191] row inside the walk window (153 e0 t0 ip22 := 1, a change: emitted) -- masked, so no key:
    WALK (b) reads it (any target, masked or not), and PATTERN (b) does (masked rows in)."""
    add = lambda ev, n: after(ev, I200, at(F_WALK0 + 100), w(I22, value=1))   # noqa: E731
    return six(pred, s=add, f=add)


@case("lands-real-154-covered", "NOT PROVEN", fail=("FORBIDDEN", "WRITES"),
      clauses={"LANDING": ["(a)", "(b)", "(e)"]})
def _(pred):
    real = lambda ev, n: edit(ev, lambda x: x[0] == "w" and x[1] == 154,  # noqa: E731
                              lambda x: with_opt(x, fld=154, don=154))
    return six(pred, f=real)


@case("enter153b-unsuppressed-both", "NOT PROVEN", clauses={"LANDING": ["(b)"], "PATTERN": ["(a)", "(b)"]})
def _(pred):
    """Visit 3 rendered WITHOUT suppression (an engine that emits every same-value store): its first row ip22, not ip57
    (LANDING (b)); no c rows, visit 3's sequence six rows longer (PATTERN (a)(b)). STATE (a) compares runs: symmetric."""
    def un(ev, n):
        for s in PRO153:
            ev = edit_nth(ev, s, 1, lambda x: with_opt(x, emit=True))
        return ev
    return six(pred, s=un, f=un)


@case("154-after-153b-both", "NOT PROVEN", clauses={"LANDING": ["(b)"]})
def _(pred):
    """A harness row in 154 after visit 3's first row: (b)'s "no row of place 154 after enter153b" alone -- PATTERN
    reads script rows only."""
    poke = lambda ev, n: after(ev, I57, w((154, -1, -1, -1, "Global.Byte[300]", 9), src="harness"), nth=1)  # noqa
    return six(pred, s=poke, f=poke)


@case("last-place-harness-both", "NOT PROVEN", clauses={"LANDING": ["(c)"]})
def _(pred):
    poke = lambda ev, n: after(ev, CH153B, w((153, -1, -1, -1, "Global.Byte[300]", 9), src="harness"))  # noqa: E731
    return six(pred, s=poke, f=poke)


@case("end-log-row-real-151-F", "NOT PROVEN", clauses={"LANDING": ["(c)"]})
def _(pred):
    """A SYNTHETIC log (O4's claim critique #15): every F run's ``end`` row names field 151 while its trace cuts at
    member(151) -- the live rule 1 writes that row only for a field in the side's own end list."""
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            run["end_field"] = 151
    return runs


@case("end-real-151-F", "NOT PROVEN", clauses={"LANDING": ["(d)"]})
def _(pred):
    real = lambda ev, n: edit(ev, lambda x: _is(x, END151), lambda x: with_opt(x, fld=151, don=151))   # noqa: E731
    return six(pred, f=real)


@case("end-boundary-residue-both", "NOT PROVEN", clauses={"LANDING": ["(d)"]})
def _(pred):
    add = lambda ev, n: before(ev, END151, r(151, 300, 0, 1))          # noqa: E731
    return six(pred, s=add, f=add)


@case("end-row-missing-one-S", "PROVEN", void={1: ["A-NOEND"]}, covered={1: False, 3: True, 5: True},
      report_has=("A-NOEND",))
def _(pred):
    runs = six(pred)
    runs[0]["events"] = [x for x in runs[0]["events"] if not (x[0] == "w" and x[1] == 151)]
    return runs


@case("suppressed-pattern-differs-F", "NOT PROVEN", fail=("STATE",), clauses={"PATTERN": ["(a)", "(b)"]})
def _(pred):
    """Every F run's visit-3 ip138 EMITTED -- an engine that does not suppress at that site: NULL's sets are equal, the
    ordered history is not (STATE (a)), and PATTERN (a)(b) reads the count gone and the row there."""
    return six(pred, f=lambda ev, n: edit_nth(ev, I138, 1, lambda x: with_opt(x, emit=True)))


@case("c-n2-F", "NOT PROVEN", clauses={"PATTERN": ["(a)"]})
def _(pred):
    """Every F run's visit-3 ip138 count n 2 -- a revisit whose prologue stored it twice: PATTERN (a) alone (STATE (a)'s
    suppressed set drops a count whose last value an emitted key carries)."""
    return six(pred, f=lambda ev, n: after(ev, I138, w(I138), nth=1))


@case("c-missing-ip138-F", "NOT PROVEN", clauses={"PATTERN": ["(a)"]})
def _(pred):
    return six(pred, f=lambda ev, n: drop_nth(ev, I138, 1))


@case("byte8-repeat-both", "NOT PROVEN", clauses={"PATTERN": ["(b)"]})
def _(pred):
    """A second visit-3 ip890 store 0 -> 0, emitted (``same`` 1: the site's first same-value store) -- symmetric, so
    STATE (a) (runs against run 0) cannot see it; Byte[8]'s frozen history does (the claim critique #10)."""
    again = lambda ev, n: after(ev, B8_890, w(B8_890))                 # noqa: E731
    return six(pred, s=again, f=again)


@case("byte8-race-both", "PROVEN")
def _(pred):
    """151 e0 t0 ip315 Byte[8] := 125 races the live end-state read (4.9): in the base every run's ip315 store lands
    before its end row is read (the end row's frame is the trace's last); here the race goes BOTH ways on each side --
    the second run of each side is collected before ip315 runs (its trace holds no ip315 row). Byte[8] is out of
    ``end_state`` and 151's rows lie past the cut, so neither outcome can reach a check: PROVEN."""
    race = lambda ev, n: drop_nth(ev, AFTER151[5]) if n == 1 else ev   # noqa: E731
    return six(pred, s=race, f=race)


def _observed(run: dict, kind: str) -> None:
    obs = {"k": "observed", "kind": kind, "cell": [153, 1190, 1], "frame": F_FIRST - 5,
           "texts": ["153 mes 999"], "phrase_raw": ["[STRT=0,0]153 mes 999"]}
    _void(run, "V17", [153, 1190, 1], "driver", f"a game-observed V17 ({kind}), nothing pressed",
          events=upto_nth(run["events"], I200, 0, e("off", 153)), log=lambda lg, c: lg + [dict(obs)])


@case("observed-quiet-page-one-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(d)"]}, covered={2: False})
def _(pred):
    runs = six(pred)
    _observed(runs[1], "quiet_page")
    return runs


@case("observed-quiet-page-each-side", "PROVEN", covered={1: False, 2: False, 3: True, 4: True})
def _(pred):
    runs = six(pred)
    _observed(runs[0], "quiet_page")
    _observed(runs[1], "quiet_page")
    return runs


@case("observed-after-answer-one-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(d)"]}, covered={2: False})
def _(pred):
    runs = six(pred)
    _observed(runs[1], "after_answer")
    return runs


@case("control-S", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={1: False})
def _(pred):
    runs = six(pred)
    _void(runs[0], "V4", [154, 1190, 2], "game", "control held in 154 (place 154) at SC 1190, where the table has no "
                                                  "entry", events=upto_nth(runs[0]["events"], B8_279, 0, e("off", 154)))
    return runs


@case("stairs-beat-missing", "VOID", cover_void=True, void={1: ["A-BEATS"], 3: ["A-BEATS"]})
def _(pred):
    runs = six(pred)
    for run in (runs[0], runs[2]):
        run["beats"] = {"stairs": False, "choice128": True}
    return runs


@case("choice-beat-missing", "VOID", cover_void=True, void={1: ["A-BEATS"], 3: ["A-BEATS"]})
def _(pred):
    runs = six(pred)
    for run in (runs[0], runs[2]):
        run["beats"] = {"stairs": True, "choice128": False}
    return runs


@case("end-cut", "PROVEN")
def _(pred):
    """More rows in 151 past the end (S): 151's post-cut prologue stored a second time (real sites; a re-entry's) --
    all cut."""
    return six(pred, s=lambda ev, n: ev[:-1] + [w(x) for x in [END151] + AFTER151] + [ev[-1]])


@case("end-state-differs", "NOT PROVEN", fail=("STATE",))
def _(pred):
    runs = six(pred)
    runs[3]["end_state"] = dict(pred["end_state"], **{"Global.Bit[3795]": 0})
    return runs


@case("masked-differs", "NOT PROVEN", fail=("MASKED",), clauses={"PATTERN": ["(a)", "(b)"]})
def _(pred):
    """Every F run without its Bit[184] rows (153 ip49, 154 ip53, 151 ip49): MASKED reads the region gone on F; PATTERN
    reads visit 1's and 2's sequences short and visit 3's ip49 count gone (the Bit[184] rows and count are frozen
    tuples)."""
    return six(pred, f=lambda ev, n: [x for x in ev if not (x[0] == "w" and x[5] == "Global.Bit[184]")])


@case("mismatched", "PROVEN", void={2: ["A-MISMATCH"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    return six(pred, f=lambda ev, n: edit(ev, lambda x: x[0] == "w" and x[1] == 154,
                                          lambda x: with_opt(x, don=31243)) if n == 0 else ev)


@case("no-start-row", "PROVEN", void={1: ["A-NOSTART"]}, covered={1: False})
def _(pred):
    runs = six(pred)
    runs[0]["events"] = base_events()[:5] + [e("off", 70)]
    runs[0]["log"] = lambda lg, c: []
    return runs


@case("join-failure", "NOT PROVEN", fail=("JOIN",))
def _(pred):
    """An extra row at 153 e3 t1 ip1742 (one byte into ip1741's store): JOIN alone -- PATTERN reads only rows that
    join, CHOICE reads ip1741's site."""
    off = (153, 3, 1, 1742, "Global.Bit[3795]", 1)
    add = lambda ev, n: after(ev, CHOICE1741, w(off))                  # noqa: E731
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


def unit_guard_of(pred: dict) -> tuple:
    """segment_drive.guard_of (S10): the draft's guard passes (a copy); each refusal raises, naming its cause -- an
    unknown key, a missing one, a bool donor, markers empty, branch one string and two equal ones, page_once_ticks 3
    and 31, quiet_cap_s 0 and 11, an empty why, a chanbara policy beside it, a choice matching no rule, one matching a
    rule that takes the default."""
    g = pred["guard"]

    def of(**over):
        p = copy.deepcopy(pred)
        p["guard"] = {**copy.deepcopy(g), **over}
        for k, v in over.items():
            if v is ...:
                p["guard"].pop(k)
        return lambda: SD.guard_of(p)
    got = {"draft": SD.guard_of(pred) == g}
    for name, fn, match in (("unknown", of(extra=1), "unknown key"), ("missing", of(branch=...), "missing"),
                            ("bool-donor", of(donor=True), "donor"), ("markers-empty", of(markers=[]), "markers"),
                            ("branch-one", of(branch=["Let"]), "branch"), ("branch-equal", of(branch=["a", "a"]), "branch"),
                            ("once-3", of(page_once_ticks=3), "page_once_ticks"),
                            ("once-31", of(page_once_ticks=31), "page_once_ticks"),
                            ("cap-0", of(quiet_cap_s=0), "quiet_cap_s"), ("cap-11", of(quiet_cap_s=11), "quiet_cap_s"),
                            ("why-empty", of(why=""), "why"), ("no-rule", of(choice="nothing"), "the match of 0 rules")):
        got[name] = _raises(fn, match)
    p = copy.deepcopy(pred)
    p["chanbara"] = {"policy": "fast"}
    got["chanbara"] = _raises(lambda: SD.guard_of(p), "one input policy")
    p = copy.deepcopy(pred)
    p["choices"][0]["take"] = "default"
    got["default-rule"] = _raises(lambda: SD.guard_of(p), "takes the game's default")
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_witness_of(pred: dict) -> tuple:
    """segment_drive.witness_of (S12): the draft's witness passes; a list, an unknown key, no input_every_s, 0, 0.2, a
    bool and an empty why each refused, naming the cause; no witness reads None."""
    def of(raw):
        return lambda: SD.witness_of({"witness": raw})
    got = {"draft": SD.witness_of(pred) == pred["witness"], "none": SD.witness_of({}) is None}
    for name, raw, match in (("list", [0.05], "a dict"), ("unknown", {"input_every_s": 0.05, "x": 1}, "unknown key"),
                             ("missing", {"why": "w"}, "missing"), ("zero", {"input_every_s": 0}, "positive number"),
                             ("slow", {"input_every_s": 0.2}, "at most 0.1"),
                             ("bool", {"input_every_s": True}, "positive number"),
                             ("why", {"input_every_s": 0.05, "why": ""}, "why")):
        got[name] = _raises(of(raw), match)
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_cell_visit(pred: dict) -> tuple:
    """S13: the draft's visit-scoped cell answers (153, 1190) at visit 1 only (visit 3, the revisit, gets none); a table
    without ``visit`` answers every visit; and THE VOID CELL -- under a visit-scoped table ``[place, sc, visit]`` (the
    revisit's position in ``visits``), without one ``[place, sc]``."""
    c1 = SD.cell(pred, 153, 1190, 1)
    flat = dict(pred, table=[{k: v for k, v in pred["table"][0].items() if k != "visit"}])
    d = object.__new__(SD._Drive)
    d.at = 2
    d.visit_cells = True
    scoped = d.vcell(153, 1190)
    d.visit_cells = False
    got = {"visit-1": c1 is pred["table"][0], "visit-3-none": SD.cell(pred, 153, 1190, 3) is None,
           "flat-any": SD.cell(flat, 153, 1190, 3) is not None, "void-scoped": scoped == [153, 1190, 3],
           "void-flat": d.vcell(153, 1190) == [153, 1190]}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_guard_strays() -> tuple:
    """guard_strays and guard_exclude (S10, 2.5.4), pure, in [marker_last 2230, choice_close 2300): 127's CLOSING press
    (seq 7, decided at 2229, down at 2237 -- after ``marker_last``: O4's 2229/2237 shape) excluded by ``closing_seq``;
    a stray page press down at 2241 (seq 8) counts; a page press with no accepted event (seq 9) counts by its decision
    frame 2248 (fail-closed, ``placed`` False); select's Down and both Confirms of a two-Confirm answer (seqs 10-12)
    excluded by the answer's whole seq span (9, 12]; a press down before the window (seq 3) never counts. The window
    without ``closing_seq`` counts the closing press; with only the rowed answer excluded, select's Down and the first
    Confirm count; with the strays gone, nothing does."""
    events = [{"kind": "accepted", "seq": s, "frame": f} for s, f in ((3, 2000), (7, 2236), (8, 2240), (10, 2260),
                                                                      (11, 2270), (12, 2275))]
    log = [{"k": "press", "seq": s, "why": why, "pre": None if f is None else {"frame": f}}
           for s, why, f in ((3, "page", 1999), (7, "page", 2229), (8, "page", 2239), (9, "page", 2248),
                             (10, "choose", None), (11, "choose", None), (12, "choose", None))]

    def strays(rows, excl):
        return [(s["seq"], s["placed"]) for s in SD.guard_strays(rows, events, [], 2230, 2300, exclude=excl)]
    full = SD.guard_exclude([9, 12], 7)
    got = {"exclude": full == {7, 10, 11, 12},
           "strays": strays(log, full) == [(8, True), (9, False)],
           "closing-kept": strays(log, SD.guard_exclude([9, 12], None)) == [(7, True), (8, True), (9, False)],
           "answer-only": strays(log, {7, 12}) == [(8, True), (9, False), (10, True), (11, True)],
           "clean": strays([x for x in log if x["seq"] not in (8, 9)], full) == []}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or f"all as registered: excluded "
                                                                               f"{sorted(full)}")


def unit_why_void_start(pred: dict, stock, scripts: dict, tmp: Path, path: Path) -> tuple:
    """A-START scoped to visit 1 (1.3; the claim critique #7), on a session's own reading: an S run stopped at visit 1's
    error path (153 ip97, V5 at [153, 1190, 1]) holds A-START and withdraws nothing; an F run stopped at visit 3's (V5
    at [153, 1190, 3]) holds no A-START, its withdrawn reason kept for the report -- while O3's rule, which the mutant
    restores (O4's why_void alone), would give it A-START."""
    runs = six(pred)[:2]
    ev = drop_nth(runs[0]["events"], I119)
    _void(runs[0], "V5", [153, 1190, 1], "driver", "a stop page (153's ambient error window 56), nothing pressed",
          events=upto_nth(ev, I57, 0, w(ERR153_97), e("off", 153)))
    ev = drop_nth(runs[1]["events"], I119, 1)
    _void(runs[1], "V5", [153, 1190, 3], "game", "a stop page (153's ambient error window 56 at the revisit)",
          events=upto_nth(ev, I57, 1, w(ERR153_97), e("off", 153)))
    d = make_session(tmp, path, runs, scripts)
    rs = C5.O5.read_session(d, pred, stock=stock)
    cls = [{v["class"] for v in r["void"]} for r in rs]
    o4 = [cls_ for _w, cls_, _b in C4.O4Segment.why_void(C5.O5, rs[1]["rec"], dict(rs[1]), pred)]
    got = {"v1-start": "A-START" in cls[0] and not rs[0].get("start_withdrawn"),
           "v3-none": "A-START" not in cls[1] and "V5" in cls[1] and bool(rs[1].get("start_withdrawn")),
           "o4-rule-would": "A-START" in o4}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or f"all as registered: S {sorted(cls[0])}, "
                                                                               f"F {sorted(cls[1])}")


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
            if ev[2] == 0:                                   # the warp's residue, its four bytes at once
                fake._warp_writes(325, 1190)
        elif ev[0] == "w":
            _k, donor, sid, tag, ip, target, value, _opt = ev
            fake.field_id = fork.get(donor, donor) if side == "F" else donor
            fake.donor = donor if side == "F" else None
            width, index = target.split(".", 1)[1].rstrip("]").split("[")
            bit = int(index) if width in T.BIT_WIDTHS else -1
            fake.script_store(sid, tag, ip, int(index) >> 3 if bit >= 0 else int(index), width, value, bit=bit)
    text = (game / "x64" / "ff9harness" / "story.jsonl").read_text(encoding="utf-8")
    return [json.loads(ln) for ln in text.splitlines() if ln.strip()]


def _shape(rows: list) -> list:
    return [(x["k"], x.get("fld"), x.get("sid"), x.get("tag"), x.get("ip"), x.get("new"), x.get("same"), x.get("n"),
             x.get("last")) for x in rows]


def unit_render_suppression(pred: dict, tmp: Path) -> tuple:
    """THE SINK'S SUPPRESSION, one model, two implementations (research/o5_design.md 0.2 #2-#3, 3.1): the base run's
    rendered rows before the cut are 21 ``w`` rows (17 unmasked) and 4 ``c`` rows, visit 3's first row ip57 (``same``
    1); the SAME events through the FakeGame's H13 knob give the same ``(k, fld, sid, tag, ip, new, same, n, last)``
    sequence, on S and on F; and at one site a change then two same-value stores: the change and the first same-value
    one emitted, the third counted (ip1741's shape)."""
    members = members_of(pred)
    got = {}
    for side in ("S", "F"):
        rows = render(base_events(), side, members)
        fk = _fake_rows(base_events(), side, members, tmp)
        got[f"fake-{side}"] = _shape(rows) == _shape(fk)
        end151 = 151 if side == "S" else 31244
        cut = next(i for i, x in enumerate(rows) if x["k"] in ("w", "r") and x["fld"] == end151)
        before_ = [x for x in rows[:cut] if x["k"] == "w"]
        unmasked = [x for x in before_ if x["bit"] not in (191, 184)]
        got[f"counts-{side}"] = (len(before_), len(unmasked), sum(1 for x in rows if x["k"] == "c")) == (21, 17, 4)
        v3 = next(x for x in rows if x["k"] == "w" and x["ip"] == 1520)
        nxt = rows[rows.index(v3) + 1]
        got[f"visit3-first-{side}"] = (nxt["ip"], nxt["same"]) == (57, 1)
    triple = [e("arm", 70), w(CHOICE1741, value=1), w(CHOICE1741), w(CHOICE1741), e("off", 153)]
    rows = render(triple, "S", {})
    got["change-then-two"] = [(x["k"], x.get("same"), x.get("n")) for x in rows if x["k"] in ("w", "c")] == [
        ("w", 0, None), ("w", 1, None), ("c", None, 1)]
    got["change-then-two-fake"] = _shape(rows) == _shape(_fake_rows(triple, "S", {}, tmp))
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_pattern(pred: dict, stock, tmp: Path) -> tuple:
    """O5-PATTERN's reading (4.16): :func:`o5_hallway.pattern_of` on the base run, joined on the stock bytes, is the
    draft's ``pattern`` on both sides; on the FakeGame's H13 trace of the same events, the same."""
    members = members_of(pred)
    got = {}
    for side in ("S", "F"):
        m = members if side == "F" else {}
        for src, rows in (("render", render(base_events(), side, members)),
                          ("fake", _fake_rows(base_events(), side, members, tmp))):
            parsed = T.parse_text("".join(json.dumps(x) + "\n" for x in rows))
            kept, _at, _pre = ST.cut_at_start(parsed, 153, m)
            kept, _end = ST.cut_at_end(kept, [151], m)
            pat = C5.pattern_of(kept, pred, m, C5.stock_join(stock, m))
            got[f"{src}-{side}"] = C5.pattern_diff(pat, pred["pattern"]) == [] and pat["unjoined"] == 0
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_trace_summary(pred: dict, stock) -> tuple:
    """O5's trace summary (7.2; O4's lesson, the claim critique #14 there) of a base S run: the chain 3/3, writes 12/12,
    the error path, forbidden and dead sites absent, the crossings 153 ip3150 -> 154 e0 t0 ip26 and 154 ip1520 -> 153 e0
    t0 ip57, visit 3's first emitted row ip57, the end cut's row 151 e0 t0 ip22 at its end place, the four c rows, no
    unregistered key, no join failure, the four start residue rows. An R-STAIRS stage ending in 154 is cut at 154's
    first row (visit 1's pattern alone); an F stage ending in member(154) is cut at 31246's first row by its end
    PLACES -- while O3's summary given the same end FIELDS (the unit's mutant) is not cut at all."""
    members = members_of(pred)
    t = C5.trace_summary(_rows(base_events()), pred, stock=stock)
    reg = {k: (sum(1 for x in v if x["present"]), len(v)) for k, v in t["registered"].items()}
    want = {"chain": (3, 3), "writes": (12, 12), "error_path": (0, 8), "forbidden_sites": (0, 2), "dead": (0, 11)}
    got = {"registered": reg == want,
           "crossings": t["crossings"] == {"exit153": {"exit": "153 e3 t1 ip3150 Global.Int16[2]=304",
                                                       "next": "154 e0 t0 ip26 Global.Bit[191]=0"},
                                           "exit154": {"exit": "154 e2 t1 ip1520 Global.Int16[2]=316",
                                                       "next": "153 e0 t0 ip57 Global.Int16[9]=-1"}},
           "visit3": t["visit3_first"] == [153, 0, 0, 51, "Global.Int16[9]", -1, 1],
           "end-row": t["end_row"] == "w 151 e0 t0 ip22 Global.Bit[191]=0" and t["end_places"] == [151],
           "counts": len(t["pattern"]["counts"]) == 4,
           "clean": t["unregistered"] == [] and t["failures"] == [],
           "residue": [x[1:] for x in t["residue_before"]] == [[0, 0, 166], [1, 0, 4], [2, 0, 69], [3, 0, 1]]}
    ts = C5.trace_summary(_rows(base_events()), pred, end_fields=[154], stock=stock)
    first154 = next(x.line for x in _rows(base_events()) if x.k in ("w", "r") and x.fld == 154)
    got["stage-154"] = ts["end"] == first154 and len(ts["pattern"]["visits"]) == 1
    frows = _rows(base_events(), "F", members)
    tf = C5.trace_summary(frows, pred, side="F", end_fields=[31246], stock=stock)
    first = next(x.line for x in frows if x.k in ("w", "r") and x.fld == 31246)
    got["f-cut-at-member"] = tf["end"] == first and tf["end_places"] == [154] and tf["end_row_fld"] == 31246
    got["o3-fields-uncut"] = P.trace_summary(frows, pred, side="F", end_fields=[31246], stock=stock)["end"] is None
    return all(got.values()), str({k: v for k, v in got.items() if not v} or f"all as registered: {reg}")


def unit_state_history(pred: dict, stock, scripts: dict, tmp: Path, path: Path) -> tuple:
    """O5-STATE (a)'s reading of a base run: Byte[8]'s history [(153, 0), (154, 125), (153, 0)] (its last pre-cut write
    visit 3's ip890: 4.9); Int16[11]'s [(153, -1), (154, -1)] (visit 3's ip138 suppressed); Bit[3795]'s [(153, 1)]."""
    d = make_session(tmp, path, six(pred)[:1], scripts)
    run = C5.O5.read_session(d, pred, stock=stock)[0]
    h = C5.O5.history(run, pred)
    got = {t: [(k.donor, k.value) for k in h.get(t, [])] for t in ("Global.Byte[8]", "Global.Int16[11]",
                                                                    "Global.Bit[3795]")}
    ok = got == {"Global.Byte[8]": [(153, 0), (154, 125), (153, 0)], "Global.Int16[11]": [(153, -1), (154, -1)],
                 "Global.Bit[3795]": [(153, 1)]}
    return ok, str(got)


def unit_visit_entrances(pred: dict) -> tuple:
    """The entrances per VISIT (0.2 #10): {153: [325, 316], 154: [304]}; O4's ``route_entrances`` on the same
    predictions gives 154 the entrance 110 (153's ip1077) -- the reason O5 has its own; a chain key standing in the
    wrong visit's place refuses."""
    bad = copy.deepcopy(pred)
    bad["chain"] = [bad["chain"][1], bad["chain"][0], bad["chain"][2]]
    got = {"o5": C5.visit_entrances(pred) == {153: [325, 316], 154: [304]},
           "o4": C4.route_entrances(pred) == {153: 325, 154: 110},
           "refused": _raises(lambda: C5.visit_entrances(bad), "not the exit of visit 1")}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


_LOG_HEAD = "03.10.2026 19:27:42 |M| [WindowManager] Moving window to (2045,33)\n"
_LOG_351 = ("03.10.2026 19:27:44 |W| [DataPatchers] ForkDonorPatch: donor field 351 is forked by both 30831 and 30842 "
            "-> remap DISABLED (ambiguous)\n")
_LOG_DONE = "03.10.2026 19:27:44 |M| [DataPatchers] Initialized\n"


def unit_p_donor_log() -> tuple:
    """P-DONOR-LOG over 151, 153 and 154 (O4's unit, O5's donors): today's shape (another donor's collision only) PASS;
    151 forked twice FAIL naming it; no "Initialized" FAIL."""
    a = P.p_donor_log(_LOG_HEAD + _LOG_351 + _LOG_DONE, C5.ROUTE_DONORS)
    w151 = _LOG_351.replace("351", "151").replace("30831 and 30842", "31244 and 31299")
    b = P.p_donor_log(_LOG_HEAD + _LOG_351 + w151 + _LOG_DONE, C5.ROUTE_DONORS)
    c = P.p_donor_log(_LOG_HEAD + _LOG_351, C5.ROUTE_DONORS)
    ok = a[0] and not b[0] and "donor field 151 is forked by both 31244 and 31299" in b[1] and not c[0]
    return ok, f"today {a[0]}; 151 twice {b[0]}; no Initialized {c[0]}"


def unit_p_launch(tmp: Path) -> tuple:
    """P-LAUNCH with the engine (O4's unit, O5's ForkDonorPatch rows): every patch file, Memoria.ini and both engine
    DLLs older than the launch, the DLLs the pinned engine: PASS; the ForkDonorPatch.txt holding 151/153/154's rows
    touched after the launch FAIL ("relaunch"); an engine DLL touched after it FAIL; another live engine FAIL; no stamp
    FAIL."""
    launched = P.launch_time(_LOG_HEAD + _LOG_DONE)
    game = tmp / "plaunch5"
    root = game / "FF9CustomMap"
    root.mkdir(parents=True)
    old = _dt.datetime(2026, 10, 3, 19, 27, 4)
    files = {game / "Memoria.ini": "[Battle]\nSpeed = 5\n", root / "DictionaryPatch.txt": "FieldScene 31245 11 X X 3\n",
             root / "ForkDonorPatch.txt": "31244 151\n31245 153\n31246 154\n"}
    for arch in ("x64", "x86"):
        files[game / arch / "FF9_Data" / "Managed" / "Assembly-CSharp.dll"] = "dll"
    for p, text in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        D4._touch(p, old)
    pinned = {"x64": C5.ENGINE["x64"], "x86": C5.ENGINE["x86"]}

    def check(live=pinned, stamp=launched):
        return C4.launch_engine_check(P.launch_files(game, [root]), C4.engine_files(game), stamp, live, C5.ENGINE)
    got = {"older": check()[0]}
    fdp = root / "ForkDonorPatch.txt"
    D4._touch(fdp, _dt.datetime(2026, 10, 3, 19, 27, 50))
    ok, d = check()
    got["fdp-after"] = (not ok) and "ForkDonorPatch.txt" in d and "relaunch" in d
    D4._touch(fdp, old)
    dll = game / "x86" / "FF9_Data" / "Managed" / "Assembly-CSharp.dll"
    D4._touch(dll, _dt.datetime(2026, 10, 3, 19, 28))
    ok, d = check()
    got["dll-after"] = (not ok) and "Assembly-CSharp.dll" in d and "relaunch" in d
    D4._touch(dll, old)
    got["other-engine"] = not check(live={"x64": "6" * 64, "x86": "6" * 64})[0]
    got["no-stamp"] = not check(stamp=None)[0]
    got["older-again"] = check()[0]
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def units(pred: dict, stock, scripts: dict, sdir: Path, path: Path, tmp: Path) -> list:
    """Every single unit, in order: ``[(name, fn)]``, each ``fn()`` -> ``(ok, detail)``."""
    return [("guard-of", lambda: unit_guard_of(pred)),
            ("witness-of", lambda: unit_witness_of(pred)),
            ("cell-visit", lambda: unit_cell_visit(pred)),
            ("guard-strays", unit_guard_strays),
            ("why-void-start", lambda: unit_why_void_start(pred, stock, scripts, sdir, path)),
            ("render-suppression", lambda: unit_render_suppression(pred, tmp)),
            ("pattern", lambda: unit_pattern(pred, stock, tmp)),
            ("trace-summary", lambda: unit_trace_summary(pred, stock)),
            ("state-history", lambda: unit_state_history(pred, stock, scripts, sdir, path)),
            ("visit-entrances", lambda: unit_visit_entrances(pred)),
            ("p-donor-log", unit_p_donor_log),
            ("p-launch", lambda: unit_p_launch(tmp)),
            ("p-settings", lambda: D4.unit_p_settings(tmp)),
            ("p-pad", D4.unit_p_pad),
            ("p-override", D4.unit_p_override),
            ("p-engine", D4.unit_p_engine),
            ("text-strict", D4.unit_text_strict),
            ("input-witness", D4.unit_input_witness)]


# ======================================================================== the listed units (offline checks' mutants)
def unit_store_census(pred: dict, stock) -> list:
    """O5-CENSUS on the install PASSES with 6.1's line; each mutant FAILS naming the site: ``dead`` without 153 ip41;
    ``inert`` without 32 -- e15's only caller e32 made non-inert, so the shared proof fails first (e15 runs from a
    function of no inert entry), then e32's own sites stand in no list; e15's ``shared_by`` naming another caller (the
    shared proof's second half); ``error_path`` without 154 ip497; an ``inert`` entry 3 (instanced at 325: the proof
    fails); a registered key inside an inert function."""
    out = []
    ok, _w, detail = C5.O5.census_check(pred, stock)
    want = ("153: 51, 154: 22 store sites -- all classified (writes 7/5, chain 2/1, masked 2/2 (153's ip22 is "
            "start_first), error_path 4/4, forbidden 2/0, dead 8/3, inert 26/7); 0 unresolved; inert 153 e15 (shared, "
            "run only from e32), e23, e24, e25, e32 not instanced at 325 or 316; 154 e5, e8, e9, e10 not instanced at "
            "304")
    out.append(("store-census", ok is True and detail == want, detail[:150]))

    def without(name, test):
        def mutate(p):
            p[name] = [k for k in p[name] if not test(k)]
        return mutate
    muts = [("census-dead-153-41", without("dead", lambda k: (k["donor"], k["ip"]) == (153, 41)),
             "153 e0 t0 ip41 Global.Int16[2]: in no list"),
            ("census-inert-32", without("inert", lambda k: (k["donor"], k["sid"]) == (153, 32)),
             "153 e15: shared, run by RunSharedScript(15) at e32 t1 ip866"),
            ("census-shared-by", lambda p: next(i for i in p["inert"] if (i["donor"], i["sid"]) == (153, 15))
             .__setitem__("shared_by", [31]), "153 e15: registered shared_by [31], but its callers are [32]"),
            ("census-error-154-497", without("error_path", lambda k: (k["donor"], k["ip"]) == (154, 497)),
             "154 e0 t0 ip497 Global.Byte[13]: in no list"),
            ("census-inert-3", lambda p: p["inert"].append({"donor": 153, "sid": 3, "tags": "*", "why": "a mutant"}),
             "inert entry 3 of 153 is instanced at entrance 325"),
            ("census-key-in-inert", lambda p: p["writes"].append(dict(C5._key(153, 32, 0, 718, 712, "Global.Bit[3855]",
                                                                              1, ":=", "a mutant key"))),
             "registered in ['writes'] AND in inert function e32")]
    for name, mutate, clause in muts:
        p = copy.deepcopy(pred)
        mutate(p)
        ok, _w, detail = C5.O5.census_check(p, stock)
        out.append((name, ok is False and clause in detail, f"{'FAIL' if ok is False else 'PASS'}: {detail[:150]}"))
    return out


def unit_regions(pred: dict, stock) -> list:
    """O5-REGIONS on the install PASSES with 6.1's line; each mutant FAILS naming its clause: 153.e28 registered dormant
    (instanced at 325); 153.e23 an exit (instanced at no route entrance); 153.e26's role exit; 154.e9 missing; a dormant
    region whose entrances omit 316."""
    out = []
    ok, _w, detail = C5.O5.regions_check(pred, stock)
    out.append(("regions", ok is True and detail == "9 regions (1 exit, 2 scene, 6 dormant), 0 hot-spots, 7 gateway "
                                                   "entries all registered", detail[:150]))

    def role(key, **kw):
        def fn(p):
            r_ = p["regions"][key]
            for k in ("to", "entrance", "face_gate", "stage", "entrances"):
                r_.pop(k, None)
            r_.update(kw)
        return fn
    for name, mutate, clause in (
            ("regions-e28-dormant", role("153.e28", role="dormant", entrances=[325, 316]),
             "153.e28: dormant, but instanced at route entrance(s) [325"),
            ("regions-e23-exit", role("153.e23", role="exit", to=154, entrance=315, face_gate=None),
             "153.e23: an exit no route entrance of 153"),
            ("regions-e26-exit", role("153.e26", role="exit", to=150, entrance=5, face_gate=None),
             "153.e26: scan_gateways gives []"),
            ("regions-e9-missing", lambda p: p["regions"].pop("154.e9"), "154.e9: a gateway"),
            ("regions-dormant-316", lambda p: p["regions"]["153.e25"].__setitem__("entrances", [325]),
             "153.e25: its entrances [325] are not the route's entrances of 153 [325, 316]")):
        p = copy.deepcopy(pred)
        mutate(p)
        ok, _w, detail = C5.O5.regions_check(p, stock)
        at_ = detail.find(clause)
        out.append((name, ok is False and at_ >= 0, f"{'FAIL' if ok is False else 'PASS'}: "
                                                   + (detail[max(0, at_ - 20):at_ + 120] if at_ >= 0 else detail[:150])))
    return out


def _cliff():
    """A synthetic floor (the goals unit's): a strip z 0..600 from x 1200 down to -1800 (columns 300 u apart), flat
    to x -900, then 900 u lower from x -1200 on -- a triangle whose ONLY vertex at PSX y <= -450 lies at x -1200, its
    edges crossing -450 at x -1050."""
    from ff9mapkit.scene import bgi
    xs = [1200 - 300 * i for i in range(11)]
    heights = {-1200: -900, -1500: -900, -1800: -900}
    verts = [(x, heights.get(x, 0), z) for x in xs for z in (0, 600)]
    faces = [f for c in range(10) for f in ((2 * c, 2 * c + 1, 2 * c + 3), (2 * c, 2 * c + 3, 2 * c + 2))]
    return bgi.BgiWalkmesh.from_bytes(bgi.build(verts, faces).to_bytes())


def unit_goals(pred: dict) -> list:
    """O5-GOALS on the install PASSES with the contour line (c) and the evidence on the contour (d); each mutant FAILS:
    ``closed_tris`` empty (no route on the plain mesh: the corridor over the hall is the first triangle a point
    answers), the goal at (-1700, 900) (off the floor), ``until`` x_le -1800 (false at the goal), no ``start``, the
    contour required at x <= -1500 (the route crosses it at ~-1480), and on a synthetic mesh the edge-crossing triangle
    -- (d) FAILS by the crossing at x -1050, which the vertex-and-centroid rule passed (the claim critique #11)."""
    out = []
    ok, _w, detail = C5.O5.goals_check(pred)
    out.append(("goals", ok is True and "(c) the contour crossed at (-14" in detail
                and "(d) the evidence sound ON THE CONTOUR: tris 53 and 56, x -1722..-1403" in detail, detail[-220:]))

    def step(**kw):
        def fn(p):
            s = p["table"][0]["steps"][0]
            for k, v in kw.items():
                if v is ...:
                    s.pop(k, None)
                else:
                    s[k] = v
        return fn
    for name, mutate, clause in (("goals-no-closed-tris", step(closed_tris=[]), "no route from"),
                                 ("goals-goal-off-floor", step(goal=[-1700, 900]), "off the floor"),
                                 ("goals-until-1800", step(until={"x_le": -1800}), "fails its until"),
                                 ("goals-no-start", step(start=...), "no start"),
                                 ("goals-contour-1500", step(until={"x_le": -1500}),
                                  "(c): the route first stands at PSX y <= -450 at")):
        p = copy.deepcopy(pred)
        mutate(p)
        ok, _w, detail = C5.O5.goals_check(p)
        at_ = detail.find(clause)
        out.append((name, ok is False and at_ >= 0, f"{'FAIL' if ok is False else 'PASS'}: "
                                                   + (detail[max(0, at_ - 40):at_ + 120] if at_ >= 0 else detail[:150])))
    syn = copy.deepcopy(pred)
    s = syn["table"][0]["steps"][0]
    s.update(start=[1105, 300], closed_tris=[], avoid=[])
    syn["regions"] = {}
    cliff = _cliff()
    bad, _lines = C5.goals_extra(syn, walkmesh=lambda d: cliff)
    hit = next((b for b in bad if "(d): the contour PSX y -450 is crossed where until" in b and "(-1050," in b), None)
    wv = cliff.world_verts()
    cents = [[sum(wv[k][a] for k in t.vtx) / 3 for a in range(3)] for t in cliff.tris]
    rule = all(p[0] <= -1100 for p in [v for v in wv if v[1] <= -450] + [c for c in cents if c[1] <= -450])
    out.append(("goals-edge-crossing", hit is not None and rule,
                f"the vertex-and-centroid rule passes {rule}; "
                + (hit[:150] if hit else f"no (d) crossing failure: {bad[:2]}")))
    return out


def block3_us() -> dict:
    """Block 3's US messages as the engine reads them (``{mes id: source}``)."""
    from ff9mapkit import dialogue
    body = A.stock_text_assets(3)["us"]
    body = body.decode("utf-8", errors="replace") if isinstance(body, (bytes, bytearray)) else str(body)
    return {i: x.text for i, x in dialogue.parse_mes(body).items()}


def unit_route_pins(pred: dict, stock) -> list:
    """O5-KEYS (b), THE ROUTE PINS and route_mes (4.14), on the install PASS; each mutant FAILS by its clause: a pin's
    text changed (the height test's -450 as 65085), mes 127 without the marker, 127 with a [TIME=, 128 without
    [IMME], 128's pick on both lines, 141 without the pick's branch marker, 129 holding it."""
    mes = block3_us()
    out = []
    ok, detail = C5.O5.route_pins_check(pred, stock, mes=mes)
    out.append(("route-pins", ok is True and detail.startswith("53 route pins equal"), detail[:150]))
    p = copy.deepcopy(pred)
    pin = next(x for x in p["route_pins"] if x[:4] == [153, 3, 1, 859])
    pin[4] = pin[4].replace("const(65086)", "const(65085)")
    ok, detail = C5.O5.route_pins_check(p, stock, mes=mes)
    out.append(("route-pins-height", ok is False and "153 e3 t1 ip859" in detail, detail[:150]))
    m128 = mes[128]
    for name, fn, clause in (
            ("route-mes-127-marker", lambda m: m.__setitem__(127, m[127].replace("let me pass", "let me by")),
             "does not hold the marker 'let me pass'"),
            ("route-mes-127-time", lambda m: m.__setitem__(127, m[127] + "[TIME=60]"), "holds a [TIME="),
            ("route-mes-128-imme", lambda m: m.__setitem__(128, m128.replace("[IMME]", "")), "does not hold '[IMME]'"),
            ("route-mes-128-both", lambda m: m.__setitem__(128, m128.replace("Let her pass", "Let her face pass")),
             "on line(s) [0, 1]"),
            ("route-mes-141", lambda m: m.__setitem__(141, m[141].replace("Let’s see", "Let me see")),
             "mes 141 does not hold its branch marker"),
            ("route-mes-129", lambda m: m.__setitem__(129, m[129] + "Let’s see"),
             "mes 129 holds the other branch's marker")):
        mm = dict(mes)
        fn(mm)
        ok, detail = C5.O5.route_pins_check(pred, stock, mes=mm)
        out.append((name, ok is False and clause in detail, f"{'FAIL' if ok is False else 'PASS'}: {detail[:150]}"))
    return out


def _operand(ins, i: int) -> int:
    return D4._operand(ins, i)


def unit_build_pins(pred: dict, tmp: Path) -> list:
    """O5-BUILD's route pins (6.1, :meth:`o5_hallway.O5Segment.build_pins`) on a synthetic three-member build through a
    ``stock_lang`` seam: the ROUTE members alone -- member(151) 31244, member(153) 31245, member(154) 31246 -- each
    language its own stock donor remapped by content.verbatim.remap_fields over THE WHOLE CHAIN's map (the route
    members' in-chain Field()s also name 64, 150, 155, 156, 158 and 167, so a three-donor map would not be O4's build).
    The clean build PASSES; each mutant FAILS by its clause: an extra byte changed in member(153)'s e3 t1 (ip1741's
    statement, jp); a PreloadField operand remapped (153 e3 t1 ip3048's 154 -> 31246, fr); an in-chain Field() left
    unremapped (member(153) e3 t1 ip3158's Field(154), us)."""
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
    members = {f: d for f, d in chain.items() if d in C5.ROUTE_DONORS}
    assert sorted(members.values()) == [151, 153, 154], members
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
                p = lay.eb_path(L, f"EVT_{names[fid]}.eb.bytes")
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(bytes(data))
        return root

    m153 = next(f for f, d in members.items() if d == 153)
    m154 = next(f for f, d in members.items() if d == 154)

    def flip(fid, L, data):
        if fid == m153 and L == "jp":
            ins = instr(153, L, 3, 1, 1741)
            data[ins.off + 3] ^= 0x01

    def remap_preload(fid, L, data):
        if fid == m153 and L == "fr":
            ins = instr(153, L, 3, 1, 3048)
            assert ins.imm(1) == 154, ins
            o = _operand(ins, 1)
            data[o:o + 2] = m154.to_bytes(2, "little")

    def unremap(fid, L, data):
        if fid == m153 and L == "us":
            ins = instr(153, L, 3, 1, 3158)
            assert ins.imm(0) == 154, ins
            data[ins.off + 2:ins.off + 4] = (154).to_bytes(2, "little")
    out = []
    ok, detail = C5.O5.build_pins(pred, build("bp5-clean"), stock_lang=stock_lang)
    out.append(("build-pins-clean", ok is True and detail == "the route members' pins hold in 21 member files (3 route "
                                                            "members x 7 languages): the only byte diffs are their 16 "
                                                            "in-chain Field() operands", detail[:150]))
    for name, mutate, clause in (("build-pins-extra-byte", flip, "differ outside the in-chain Field() operands"),
                                 ("build-pins-preload", remap_preload, "differ outside the in-chain Field() operands"),
                                 ("build-pins-unremapped", unremap, "left unremapped")):
        ok, detail = C5.O5.build_pins(pred, build(name, mutate), stock_lang=stock_lang)
        at_ = detail.find(clause)
        out.append((name, ok is False and at_ >= 0,
                    f"{'FAIL' if ok is False else 'PASS'}: " + (detail[max(0, at_ - 60):at_ + 90] if at_ >= 0
                                                                else detail[:150])))
    return out


def _key(p: dict, name: str, donor: int, ip: int) -> dict:
    return next(k for k in p[name] if (k["donor"], k["ip"]) == (donor, ip))


#: O5-KEYS's offline mutants (section 8): the DRAFT, deep-copied, one thing changed; the check must then read FAIL --
#: after it has read PASS on the unchanged draft -- and its detail hold the clause.
OFFLINE_MUTANTS = [
    ("keys-write-value", lambda p: _key(p, "writes", 154, 279).update(value=126), "the bytes give 125, the key says 126"),
    ("keys-var-rvalue", lambda p: _key(p, "writes", 153, 1741).update(rvalue="B_SYSVAR[8]"),
     "the statement is not Global.Bit[3795] := B_SYSVAR[8]"),
    ("keys-chain-off", lambda p: p["chain"][1].update(off=1410), "chain: FieldEntrance 316"),
    ("keys-start-first-target", lambda p: p["start_first"].update(target="Global.Bit[192]"),
     "start_first: 153's Main_Init: its first store"),
    ("keys-dead-value", lambda p: _key(p, "dead", 153, 130).update(value=2), "the bytes give 1, the key says 2"),
    ("keys-start-music", lambda p: p["start_music"].update(ip=138, off=132), "is 0 writes keys, not one"),
]


def unit_offline_mutants(pred: dict, stock) -> list:
    """``[(name, ok, detail)]``: O5-KEYS reads PASS on the draft, then FAILS on each of :data:`OFFLINE_MUTANTS` by its
    clause."""
    base = C5.O5.keys_check(pred, stock)
    out = [("offline-draft-passes", base[0] is True, base[2][:120])]
    for name, mutate, clause in OFFLINE_MUTANTS:
        p = copy.deepcopy(pred)
        mutate(p)
        ok, _what, detail = C5.O5.keys_check(p, stock)
        caught = ok is False and clause in detail
        out.append((name, caught, f"KEYS {'FAIL' if ok is False else 'PASS (not caught)'}"
                                  + ("" if caught or ok is not False else f" -- not by {clause!r}") + f": {detail[:120]}"))
    return out


def listed_units(pred: dict, stock, tmp: Path) -> list:
    return (unit_store_census(pred, stock) + unit_regions(pred, stock) + unit_goals(pred)
            + unit_route_pins(pred, stock) + unit_build_pins(pred, tmp) + unit_offline_mutants(pred, stock))


# ======================================================================== the run
def prepare(pred_path: Path | None, tmp: Path) -> tuple:
    """``(path, what)``: the predictions the run reads -- ``pred_path``; else the frozen file once it exists; else the
    DRAFT, written to a temporary file."""
    if pred_path is not None:
        return Path(pred_path), f"the file {Path(pred_path).name}"
    if C5.PREDICTIONS.is_file():
        return C5.PREDICTIONS, f"the frozen {C5.PREDICTIONS.name}"
    path = tmp / "o5_predictions_draft.json"
    path.write_bytes((json.dumps(C5.draft_predictions(), indent=1, sort_keys=True) + "\n").encode("utf-8"))
    return path, "the draft"


def _clauses_named(clauses: dict, det: dict) -> list:
    return [f"{cid} detail lacks {m}" for cid, marks in clauses.items() for m in marks if m not in det.get(cid, "")]


def _mark(ok) -> str:
    return "P" if ok is True else "F" if ok is False else "V"


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
        udir = tmp / "units"
        udir.mkdir()
        path, what = prepare(pred_path, pdir)
        print(f"predictions: {what}")
        pred, _sha = C5.O5.load(path)
        members = members_of(pred)
        retarget = {dn: f for f, dn in members.items()}
        scripts = {fid: remap_fields(stock(dn).data, retarget) for fid, dn in members.items()}
        for name, fn, want_verdict, want, clauses, report_has, want_void, want_cov, want_lacks in CASES:
            total += 1
            d = make_session(sdir, path, fn(copy.deepcopy(pred)), scripts)
            checks, report = C5.O5.analyse(d, stock=stock)
            got, det = result(checks), details(checks)
            v = verdict(checks)
            miss = [f"{k} {_mark(got.get(k))}, want {_mark(x)}" for k, x in want.items() if got.get(k) is not x]
            miss += [f"check {k} not registered" for k in got if k not in want]
            if not v.startswith(want_verdict):
                miss.append(f"verdict {v!r}, want {want_verdict}")
            miss += _clauses_named(clauses, det)
            miss += [f"report lacks {s!r}" for s in report_has if s not in report]
            runs = C5.O5.read_session(d, pred, stock=stock) if (want_void or want_cov or want_lacks) else []
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
            print(f"{'ok  ' if ok else 'FAIL'} {name:34} {v[:44]:44} "
                  + " ".join(f"{k[3:]}={_mark(got.get(k))}" for k in CHECKS[1:]))
            if not ok:
                for m in miss:
                    print(f"     {m}")
                print("     " + "\n     ".join(f"{w_} :: {dd[:260]}" for _ok, w_, dd in checks))
        # O5-FROZEN: the predictions changed after the session recorded them
        total += 1
        copy_path = pdir / "pred_copy.json"
        copy_path.write_bytes(path.read_bytes())
        d = make_session(sdir, copy_path, six(pred), scripts)
        copy_path.write_bytes(path.read_bytes() + b" ")
        checks, _rep = C5.O5.analyse(d, stock=stock)
        v = verdict(checks)
        got = result(checks)
        ok = got.get("O5-FROZEN") is False and v.startswith("NOT PROVEN") and all(
            got.get(k) is True for k in CHECKS if k != "O5-FROZEN")
        fails += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {'predictions-changed':34} {v[:44]}")
        for name, fn in units(pred, stock, scripts, sdir, path, udir):
            total += 1
            ok, detail = fn()
            fails += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name:34} (unit) {detail[:150]}")
        for name, ok, detail in listed_units(pred, stock, udir):
            total += 1
            fails += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name:34} (unit) {detail[:150]}")
    print(f"\n{total - fails}/{total} cases as registered")
    return 1 if fails else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--predictions", type=Path, default=None,
                    help="a predictions file (default: the frozen o5_predictions_v1.json once it exists, else the "
                         "draft, written to a temporary file)")
    sys.exit(run_cases(ap.parse_args().predictions))
