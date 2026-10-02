"""O4's analysis, driven on SYNTHETIC sessions (research/o4_design.md section 8): every registered check must read PASS
on the null pair and FAIL (or VOID) on the mutant built to break it -- a check that cannot fail is not a check.

    py studies/story-trace/o4_dryrun.py [--predictions studies/story-trace/o4_predictions_v1.json]

Without --predictions it reads the frozen o4_predictions_v1.json once the lead has frozen it, else it writes the DRAFT
(o4_castle.draft_predictions: the O4 build's campaign.toml) to a temporary predictions file -- nothing is frozen until
the lead's rehearsals -- and runs every case against that.

Each case writes a session directory the way the session does (o4_session.json, the members' scripts, one trace and
one driver log per run) and runs :meth:`o4_castle.O4Segment.analyse` on it. The rows are real store sites of the stock
bytes of 64, 150 and 153 (every field row joins but the join-failure case's), shifted onto the members on the F side
(``fld`` = member, ``don`` = donor: 64 -> 31240, 150 -> 31243, 153 -> 31245), and EMITTED as the engine emits them: a
same-value store once per site, a value change up to 64 times, the rest counted into a ``c`` row at the epoch's close
(StoryTrace.cs:383-400). The start values are the raw warp's: SC 1155, FieldEntrance 100, Byte[13] 1 (New Game's),
every other target 0. A run's driver log carries its visit rows; the 64 visit's fight as the Chanbara policy logs it
(the KEYON pair's and 111's page presses; 49 prompt rows drawn with e20's filters (seeded per run), each with its
press -- at 60 fps prev = seen - 2, accepted = seen + 3, down = seen + 4, ack = seen + 7, so every j lies in [1, 5] and
raw in [119, 126]; every evidence "closed"; every LEFT/RIGHT slide measured between the prev samples and ok, the tail
jointly --; the zone row; the score page's press, 123's two, the encore choice answered No by ``g.choose(1)`` and
``choose``'s rowed presses, the gil page's press); 150's page presses; the end row. Its outcome: the pages (111, 122,
123, 128 and 150's), the beats, the zones and the prompts.

O4's ``case()`` is O3's, EXACT: every check a case does not name must read PASS -- a case naming COVER V expects every
core check VOID -- so each NOT PROVEN row names EVERY check it fails, and "alone" is a registered fact. A LANDING, SWORD
or VOID-ASYM case also registers the clause its detail must name.

The units read the install read-only (the stock scripts, block 2's US text): the Chanbara policy's pure half (the
strict reader, the recognizers, the j and raw bounds against the true j, the judge, the slides, the encore
attribution), R-GATE's verdict, O4's trace summary on end places, the state history, the launch's readers
(P-DONOR-LOG, P-LAUNCH with the engine), P-PAD, P-OVERRIDE, P-SETTINGS, P-GATE, P-ENGINE, strict text, the input
witness, O4-CENSUS and its mutants, O4-BUILD's fork-gate pins on a synthetic route build, O4-KEYS's fight pins, and
the offline mutants of O4-KEYS.
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
import o4_castle as C                                                      # noqa: E402
import o3_prima_vista as P                                                 # noqa: E402
import o2_alexandria as A                                                  # noqa: E402
import segment_drive as SD                                                 # noqa: E402
import segment_trace as ST                                                 # noqa: E402
from ff9mapkit import storytrace as T                                      # noqa: E402
from o3_dryrun import _is, after, before, drop, e, edit, r, upto, w, with_opt  # noqa: E402  (O3's event helpers)
from segment_trace import members_of, place, verdict                       # noqa: E402

# ======================================================================== real store sites (donor, sid, tag, ip, target, value)
S64 = [(64, 0, 0, 22, "Global.Bit[191]", 0), (64, 0, 0, 49, "Global.Bit[184]", 0),
       (64, 0, 0, 57, "Global.Int16[9]", -1), (64, 0, 0, 119, "Global.Byte[13]", 0),
       (64, 0, 0, 138, "Global.Int16[11]", -1), (64, 0, 0, 200, "Global.Byte[14]", 0),
       (64, 0, 0, 416, "Global.Bit[3815]", 0), (64, 0, 0, 425, "Global.Byte[475]", 0),
       (64, 0, 0, 475, "Global.Byte[8]", 125)]
SCORE = (64, 4, 1, 338, "Global.Byte[475]", 100)
COMBO = (64, 4, 1, 390, "Global.Bit[3815]", 1)
B8_64 = (64, 2, 1, 331, "Global.Byte[8]", 0)
CH64 = (64, 2, 1, 528, "Global.Int16[2]", 325)
S150 = [(150, 0, 0, 26, "Global.Bit[191]", 0), (150, 0, 0, 53, "Global.Bit[184]", 0),
        (150, 0, 0, 61, "Global.Int16[9]", -1), (150, 0, 0, 123, "Global.Byte[13]", 0),
        (150, 0, 0, 142, "Global.Int16[11]", -1), (150, 0, 0, 204, "Global.Byte[14]", 0),
        (150, 0, 0, 331, "Global.Byte[8]", 25), (150, 3, 1, 1136, "Global.UInt16[21]", 1),
        (150, 3, 1, 1221, "Global.Byte[303]", 0), (150, 3, 1, 1255, "Global.Byte[303]", 1),
        (150, 3, 1, 1652, "Global.Byte[4]", 0), (150, 3, 1, 1667, "Global.Byte[4]", 0),
        (150, 3, 1, 1675, "Global.Byte[17]", 0), (150, 3, 1, 1683, "Global.Byte[18]", 1),
        (150, 3, 1, 1966, "Global.UInt16[0]", 1190), (150, 3, 1, 1974, "Global.Byte[8]", 75),
        (150, 3, 1, 2161, "Global.Int16[2]", 325)]
END153 = (153, 0, 0, 22, "Global.Bit[191]", 0)
AFTER153 = [(153, 0, 0, 49, "Global.Bit[184]", 0), (153, 0, 0, 57, "Global.Int16[9]", -1)]
START64, I9_64, MUSIC64 = S64[0], S64[2], S64[3]
ENTER150, I9_150 = S150[0], S150[2]
B303_1255, B18_150, SC1966, CH150 = S150[9], S150[13], S150[14], S150[16]
BIT184S = [S64[1], S150[1]]
#: Off the route, each a real store: 64's and 150's error path (Byte[13] := 9: the stop window's branch); 150's dead
#: `++` behind const(0); an INERT function's store -- 150 e10 t3 ip2304 Bit[8511] := 1, the moogle's MOGNET talk,
#: never instanced at entrance 325 and UNMASKED (the design's pick, ip2119's Byte[1034] := 0, lies in the
#: mognet_mailbox story-noise region: masked, never a key, so WRITES could not fail on it).
ERR64_97 = (64, 0, 0, 97, "Global.Byte[13]", 9)
ERR150_101 = (150, 0, 0, 101, "Global.Byte[13]", 9)
DEAD150_1277 = (150, 3, 1, 1277, "Global.Byte[303]", 2)
INERT150 = (150, 10, 3, 2304, "Global.Bit[8511]", 1)
SC_CS = (64, -1, -1, -1, "Global.UInt16[0]", 1190)
#: e20's Byte[46] -> its prompt (mes 112-119).
DBTNS = ("LEFT", "RIGHT", "TRIANGLE", "DOWN", "CROSS", "UP", "CIRCLE", "SQUARE")
MOBI = {"LEFT": 267, "RIGHT": 269, "TRIANGLE": 272, "DOWN": 270, "CROSS": 274, "UP": 268, "CIRCLE": 273, "SQUARE": 271}
#: The checks, in the order the analysis reports them.
CHECKS = ("O4-FROZEN", "O4-COVER", "O4-FORBIDDEN", "O4-VOID-ASYM", "O4-START", "O4-LADDER", "O4-CHAIN", "O4-RESIDUE",
          "O4-WRITES", "O4-NULL", "O4-STABLE", "O4-LANDING", "O4-SWORD", "O4-MASKED", "O4-STATE", "O4-JOIN")
CORE = CHECKS[4:]
#: A measured 60 fps rate (the fight rows' clock).
RATE60 = {"fps": 59.9, "fps_lo": 59.5, "fps_hi": 60.4, "tick_hz": 30.0, "source": "mtime", "samples": 24,
          "frame": 4000, "stale": False}
#: The fight's frames: 111 first seen; its first sample without (the driver's T0, 15 ticks on); the first prompt seen
#: 13 ticks after T0; a prompt every PASS frames (30 ticks).
F111 = 4880
T0 = F111 + 30
FIRST = T0 + 26
PASS = 60
#: The pages (US; the score, 123 and gil pages are the policy's).
P105, P106 = "Blank\n“En garde!”", "Zidane\n“Expect no quarter from me!”"
P111 = "To follow Blank’s lead, enter the correct\ncommands from the following choices:"
P107, P108 = "Blank\n“We shall finish this later!”", "Zidane\n“Come back here!”"
P120, P121 = "Of the 100 nobles watching,\n100 were impressed.", "Queen Brahne was\nnot impressed."
P150 = ["Blank\n“Ouch!”", "Zidane\n“Heh.”", "Blank\n“A package!”", "Zidane\n“For me?”"]
ENCORE = ["They demand an encore!\nPerform the fight scene again?", "es", "No"]
OBSERVED = {"k": "observed", "kind": "unclaimed_dialog", "cell": [64, 1155], "frame": 5200,
            "texts": ["Blank\n“Hold!”"], "phrase_raw": ["[STRT=60,2][TAIL=LORF]Blank\n“Hold!”"]}


# ======================================================================== events and their rendering
def render(events: list, side: str, members: dict) -> list:
    """The rows the engine would write for ``events`` on ``side``: F-side donors on their member ids; each store's
    ``old`` the variable's value so far (the warp leaves SC 1155 and FieldEntrance 100; New Game left Byte[13] 1; every
    other target 0); a same-value store emitted once per site, a change up to 64 times per site, the rest counted into
    ``c`` rows just before ``off``."""
    fork = {d: f for f, d in sorted(members.items(), reverse=True)}

    def fld_of(donor):
        return fork.get(donor, donor) if side == "F" else donor
    rows, sites = [], {}
    values = {"Global.UInt16[0]": 1155, "Global.Int16[2]": 100, "Global.Byte[13]": 1}
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


def base_events() -> list:
    """A base run (research/o4_design.md 8): ``arm`` in field 70; the warp's residue there (SC 1155's two bytes,
    FieldEntrance 100's low byte); 64's Main_Init rows; after the fight the score (ip338 0 -> 100), the 50-combo (ip390
    0 -> 1, after 123), stage 9's Byte[8] and FieldEntrance; 150's prologue and its 325 branch, stage 10's rebuild, SC
    1155 -> 1190, Byte[8] and the chain; 153's first row; ``off`` in 153 (member(153) on F)."""
    ev = [e("arm", 70), r(70, 0, 0, 131), r(70, 1, 0, 4), r(70, 2, 0, 100)]
    ev += [w(s) for s in S64] + [w(SCORE), w(COMBO), w(B8_64), w(CH64)]
    ev += [w(s) for s in S150] + [w(END153), e("off", 153)]
    return ev


def visits(rows: list, members: dict) -> list:
    """The driver's ``visit`` rows for a rendered run: one each time the written field changes after the arm (field
    70's rows are the warp's, before any visit; an end field -- 153, member(153) -- is rule 1's, never a visit), at the
    frame of the visit's first row."""
    out, cur = [], None
    ends = {153} | {f for f, d in members.items() if d == 153}
    for x in rows:
        if x["k"] not in ("w", "r") or x["fld"] == 70 or x["fld"] in ends or x["fld"] == cur:
            continue
        cur = x["fld"]
        out.append({"k": "visit", "field": cur, "donor": place(cur, members), "visit": len(out) + 1,
                    "frame": x["f"], "sc": x["sc"]})
    return out


# ======================================================================== the fight, as the policy logs it
def dbtn_sequence(seed: int = 0, n: int = 49) -> list:
    """``n`` prompts as e20 t1 rolls them on a PERFECT run (ip451-707, the fake's ``_arm``): Byte[46] := SYSVAR[0] & 7
    (seeded) until it passes the filters -- LEFT barred at SByte[38] -1/0, RIGHT at 1/2, DOWN/UP while the max combo is
    under 10, CIRCLE -> TRIANGLE and SQUARE -> CROSS under 15, never the prompt just shown. Every prompt a hit: the max
    combo before prompt k is k - 1, and a LEFT/RIGHT hit moves SByte[38] in the pass AFTER its own (the reaction that
    arms the next prompt runs after that prompt's roll)."""
    rng = random.Random(f"o4-prompts-{seed}")
    out, prev, sb38, pending = [], None, 0, 0
    for k in range(n):
        while True:
            b = rng.randrange(256) & 7
            if (b == 0 and sb38 in (-1, 0)) or (b == 1 and sb38 in (1, 2)) or (b in (3, 5) and k < 10):
                continue
            if k < 15 and b == 6:
                b = 2
            if k < 15 and b == 7:
                b = 4
            if b == prev:
                continue
            break
        out.append(DBTNS[b])
        sb38 += pending
        pending = -1 if b == 0 else 1 if b == 1 else 0
        prev = b
    return out


def prompt_raw(dbtn: str) -> str:
    return f"[STRT=54,1][TAIL=UPRF][IMME]Press [DBTN={dbtn}][MOBI={MOBI[dbtn]}] ![TIME=-1]"


def _fld(members: dict, side: str, donor: int) -> int:
    inv = {d: f for f, d in sorted(members.items(), reverse=True)}
    return inv.get(donor, donor) if side == "F" else donor


def end_sample(prompts: list, zone_end_frame: int) -> dict:
    """The zone end's first sample for the tail's joint slide: instance 49's prev sample plus the last two L/R wants."""
    last = prompts[-1]
    tail = sum(SD.LR_WANT.get(p["dbtn"], 0.0) for p in prompts[-2:])
    return {"frame": zone_end_frame, "x_player": last["x_prev"]["player"] + tail,
            "x_blank": last["x_prev"]["blank"] + tail}


def slides_again(fl: dict, pol: dict) -> None:
    """Every prompt row's ``slide`` re-measured from its rows (:func:`segment_drive.measure_slides`)."""
    slides = SD.measure_slides(fl["prompts"], end_sample(fl["prompts"], fl["zone"]["end"]["frame"]),
                               int(pol["prompts"]))
    for p in fl["prompts"]:
        p["slide"] = slides.get(p["n"]) if p["dbtn"] in SD.LR_WANT else None


def fight_log(pred: dict, side: str, *, seed: int = 0) -> dict:
    """The 64 visit as the Chanbara policy logs it (research/o4_design.md 2.4.6, 8): ``{"pre", "prompts",
    "presses", "zone", "post", "pages"}`` -- the KEYON pair's and 111's page presses (each with its seq, frames and
    texts); 49 prompt rows and their presses; the zone row; then the end pair's press, the score page's, 123's two (the
    first dropped in its opening, 0.3 #1), the encore choice (No, by ``g.choose(1)``) after ``choose``'s rowed
    presses, the gil page's press; the pages the outcome lists (111, 122, 123, 128)."""
    pol = pred["chanbara"]
    members = members_of(pred) if side == "F" else {}
    fld = _fld(members, side, 64)
    seqs = iter(range(100, 10000))
    base = {"field": fld, "donor": 64, "visit": 1, "sc": 1155}

    def page(frame, texts):
        return {"k": "press", "why": "page", **base, "pre": {"frame": frame, "control": False, "x": 0.0, "z": 0.0},
                "post": None, "near": [], "seq": next(seqs), "ack_frame": frame + 5, "button": "confirm",
                "texts": list(texts), "accepted_frame": frame + 1, "down_frame": frame + 2}
    pre = [page(4700, [P105]), page(4740, [P105, P106]), page(F111 + 4, [P111])]
    seq_d = dbtn_sequence(seed)
    prompts, presses = [], []
    for n, d in enumerate(seq_d, 1):
        seen = FIRST + PASS * (n - 1)
        moved = sum(SD.LR_WANT.get(seq_d[k - 1], 0.0) for k in range(1, n - 1))   # slides of prompts 1..n-2
        xp = {"player": moved, "blank": 600.0 + moved}
        s = next(seqs)
        row = {"k": "prompt", "n": n, "dbtn": d, "button": pol["buttons"][d], **base, "prev_frame": seen - 2,
               "prev_kind": "none", "seen_frame": seen, "seen_t": round(seen / 60.0, 3),
               "published": {"texts": ["Press  !"], "phrase_raw": [prompt_raw(d)]},
               "x_prev": dict(xp), "x_seen": dict(xp), "seq": s, "pressed_t": round(seen / 60.0, 3),
               "ack_frame": seen + 7, "ack_t": round((seen + 7) / 60.0, 3), "accepted_frame": seen + 3,
               "down_frame": seen + 4, "last_listed_frame": seen + 12, "gone_frame": seen + 14, "gone_kind": "none",
               "evidence": "closed", "read_gap": {"frames": 2, "ticks": 1, "s": 0.05}, "rate": dict(RATE60),
               "excess": 0.0, "j_lo": None, "j_hi": None, "regime": "60", "slide": None, "v": None, "why": None}
        row["j_lo"], row["j_hi"] = SD.j_bounds(row)
        prompts.append(row)
        presses.append({"k": "press", "why": "prompt", "n": n, "button": pol["buttons"][d], **base,
                        "pre": {"frame": seen, "control": False, "x": xp["player"], "z": 0.0}, "post": None,
                        "near": [], "seq": s, "ack_frame": seen + 7, "accepted_frame": seen + 3,
                        "down_frame": seen + 4})
    end_frame = FIRST + PASS * 49 + 60
    zone = {"k": "zone", **base, "policy": pol["policy"],
            "start_page": {"seen_frame": F111, "presses": [pre[-1]["seq"]], "last_with_frame": F111 + 26,
                           "first_without_frame": T0},
            "first_prompt": {"seen_frame": FIRST, "t0_frame": T0, "after_t0_ticks": [13, 13]},
            "end": {"frame": end_frame, "text": P107}, "instances": 49, "presses": 49, "samples": 1600,
            "max_read_gap": {"frames": 2, "ticks": 1, "s": 0.05}, "input": [], "rate": dict(RATE60),
            "raw": list(SD.raw_bounds(prompts)), "slides": None,
            "judge": {"v": None, "by": None, "why": None, "faults": [], "raw": list(SD.raw_bounds(prompts))},
            "t0": 30.0, "t1": 81.0, "v": None, "by": None, "why": None}
    fl = {"pre": pre, "prompts": prompts, "presses": presses, "zone": zone}
    slides_again(fl, pol)
    seen_s = list({id(p["slide"]): p["slide"] for p in prompts if p["slide"]}.values())
    zone["slides"] = {"ok": sum(1 for s in seen_s if s["ok"] is True),
                      "unmeasured": sum(1 for s in seen_s if s["ok"] == "unmeasured"),
                      "not_ok": sum(1 for s in seen_s if s["ok"] is False)}
    post = [page(end_frame + 40, [P107, P108]), page(end_frame + 300, [pol["score_page"]]),
            page(end_frame + 340, [C.PAGE_123]), page(end_frame + 362, [C.PAGE_123]),
            {"k": "quiet", "field": fld, "visit": 1, "open_frame": end_frame + 372, "armed_frame": end_frame + 340}]
    cf = end_frame + 400
    sd, sc_ = next(seqs), next(seqs)
    post += [{"k": "press", "why": "choose", "button": "down", "seq": sd, **base, "pre": None, "post": None,
              "near": [], "accepted_frame": cf + 3, "down_frame": cf + 4, "selected_before": 0, "answer": False},
             {"k": "press", "why": "choose", "button": "confirm", "seq": sc_, **base, "pre": None, "post": None,
              "near": [], "accepted_frame": cf + 20, "down_frame": cf + 21, "selected_before": 1, "answer": True},
             {"k": "choice", "field": fld, "donor": 64, "sc": 1155, "frame": cf, "options": list(ENCORE),
              "active": [0, 1], "selected": 0, "count": 2, "index": 1, "rule": 0, "took": {"index": 1}},
             page(cf + 100, [pol["gil_page"]])]
    fl.update(post=post, pages=[P111, pol["score_page"], C.PAGE_123, pol["gil_page"]])
    return fl


def fight_rows_in_order(fl: dict) -> list:
    """A fight's log rows in the order the driver writes them: the pre-zone presses, each prompt row then its press,
    the zone row, then the rows after the zone."""
    out = list(fl["pre"])
    by_n = {p["n"]: p for p in fl["presses"]}
    for row in fl["prompts"]:
        out.append(row)
        if row["n"] in by_n:
            out.append(by_n[row["n"]])
    return out + [fl["zone"]] + list(fl["post"])


def p150_presses(side: str, members: dict) -> list:
    """150's page presses (visit 2), with their seqs: outside the fight's visit."""
    fld = _fld(members, side, 150)
    return [{"k": "press", "why": "page", "field": fld, "donor": 150, "visit": 2, "sc": 1155,
             "pre": {"frame": 20000 + 50 * n, "control": False, "x": 0.0, "z": 0.0}, "post": None, "near": [],
             "seq": 500 + n, "ack_frame": 20005 + 50 * n, "button": "confirm", "texts": [t],
             "accepted_frame": 20001 + 50 * n, "down_frame": 20002 + 50 * n} for n, t in enumerate(P150)]


# ======================================================================== sessions
def six(pred: dict, *, s=None, f=None) -> list:
    """S F S F S F: each run's base events (its fight seeded by its index), ``s`` / ``f`` applied per side as
    ``fn(events, n)`` (``n`` = 0, 1, 2 within the side)."""
    counts = {"S": 0, "F": 0}
    out = []
    for i, side in enumerate(pred["order"]):
        n = counts[side]
        counts[side] += 1
        ev = base_events()
        fn = s if side == "S" else f
        out.append({"side": side, "events": fn(ev, n) if fn else ev, "seed": i})
    return out


def preflight_rows() -> list:
    """The preflight a post-deploy session records (6.2): P-TEXT for blocks 2 and 3 (each language its own stock text:
    7 byte-equal of 7), P-ENGINE on the pinned DLLs, and P-GATE's witness (R-GATE WITNESSED on the pinned engine and
    4.13's settings) -- each detail from its own reader."""
    langs = ("us", "uk", "fr", "gr", "it", "es", "jp")
    text = {L: f"stock {L}".encode() for L in langs}
    eng = {"x64": C.ENGINE["x64"], "x86": C.ENGINE["x86"]}
    witness = {"run_dir": "C:/gd/Dream-World-IX/.harness-runs/20261003-000000-o4-rh-R-GATE", "verdict": "WITNESSED",
               "cause": None, "engine": dict(eng), "settings": json.loads(json.dumps(C.SETTINGS)), "s_run": 0,
               "f_run": 1, "detail": "S run 0 and F run 1 both show 100"}
    rows = []
    for block, cid in ((2, "P-TEXT2"), (3, "P-TEXT3")):
        ok, detail = C.p_text(block, [("FF9CustomMap", dict(text))], text, o1_block2=None, o4_registered=True)
        rows.append([ok, C.O4.title(cid), detail])
    ok, detail = C.p_engine(dict(eng), C.ENGINE)
    rows.append([ok, C.O4.title("P-ENGINE"), detail])
    ok, detail = C.p_gate({"gate_witness": witness}, eng, C.SETTINGS, exists=lambda p: True)
    rows.append([ok, C.O4.title("P-GATE"), detail])
    assert all(x[0] for x in rows), rows
    return rows


def make_session(tmp: Path, pred_path: Path, runs: list, scripts: dict) -> Path:
    """A session directory as O4Segment.run writes one. Each run: ``{side, events | rows, seed?, end?, why?, beats?,
    v?, cell?, by?, install?, end_state?, end_field?, fight? (fn(fight log), changing it; False: no fight rows),
    pages? (fn(pages) -> pages), log? (extra rows, or fn(rows, visits) giving them)}``."""
    pred, sha = C.O4.load(pred_path)
    members = members_of(pred)
    d = tmp / f"s{len(list(tmp.iterdir()))}"
    (d / "scripts").mkdir(parents=True)
    for fid, data in scripts.items():
        (d / "scripts" / f"{fid}.eb").write_bytes(data)
    session = {"label": d.name, "predictions": str(pred_path), "predictions_sha256": sha,
               "predictions_version": pred["version"], "order": pred["order"], "budget": pred["budget"],
               "preflight": preflight_rows(),
               "install": {"settings": pred["settings"], "engine": {"x64": C.ENGINE["x64"], "x86": C.ENGINE["x86"]}},
               "runs": [], "ended": {"log": [{"k": "recover-warp", "field": 4600}], "ok": True, "why": ""}}
    for i, run in enumerate(runs, 1):
        side = run["side"]
        m = members if side == "F" else {}
        rows = run.get("rows") if run.get("rows") is not None else render(run["events"], side, members)
        name, log_name = f"run{i}_{side}.jsonl", f"run{i}_{side}_log.json"
        (d / name).write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
        vis = visits(rows, m)
        end = run.get("end", "reached")
        log = list(vis[:1])
        fl = None
        if run.get("fight", True) is not False:
            fl = fight_log(pred, side, seed=run.get("seed", 0))
            if callable(run.get("fight")):
                run["fight"](fl)
            log += fight_rows_in_order(fl)
        log += vis[1:]
        if len(vis) > 1:
            log += p150_presses(side, m)
        extra = run.get("log") or []
        log += extra(rows, vis) if callable(extra) else extra
        end_state = run.get("end_state", dict(pred["end_state"]) if end == "reached" else None)
        if end == "reached":
            last = max((x["f"] for x in rows), default=0)
            log.append({"k": "end", "field": run.get("end_field", ST.side_ends(pred, side)[0]), "frame": last,
                        "sc": 1190, "end_state": end_state, "t": 200.0, "end_row": {"seen": True, "f": last, "s": 0.1}})
        pages = list((fl or {}).get("pages") or []) + (list(P150) if len(vis) > 1 else [])
        if callable(run.get("pages")):
            pages = run["pages"](pages)
        beats = run.get("beats", {"sword": True, "encore": True})
        outcome = {"end": end, "why": run.get("why", f"field {ST.side_ends(pred, side)[0]}" if end == "reached"
                                              else "route: stopped"),
                   "void": None, "beats": beats, "pages": pages, "timed": [],
                   "choices": [x for x in log if x.get("k") == "choice"], "steps": [], "overlays": [], "forbidden": [],
                   "end_state": end_state, "t": 200.0, "zones": [x for x in log if x.get("k") == "zone"],
                   "prompts": [x for x in log if x.get("k") == "prompt"]}
        (d / log_name).write_text(json.dumps({"outcome": outcome, "log": log}), encoding="utf-8")
        rec = {"i": i, "side": side, "start": pred["start"][side], "trace": name, "log": log_name, "end": end,
               "why": outcome["why"], "beats": beats}
        for k in ("v", "cell", "by", "install"):
            if run.get(k) is not None:
                rec[k] = run[k]
        session["runs"].append(rec)
    (d / C.SESSION_FILE).write_text(json.dumps(session), encoding="utf-8")
    return d


def result(checks) -> dict:
    return {w_.split(":")[0]: ok for ok, w_, _d in checks}


def details(checks) -> dict:
    return {w_.split(":")[0]: d_ for _ok, w_, d_ in checks}


# ======================================================================== the cases
CASES = []


def case(name, want_verdict, *, fail=(), clauses=None, cover_void=False, report_has=(), void=None, covered=None):
    """Register a case, EXACT (O3's ``case()``): ``fail`` the checks that must read FAIL, ``clauses`` ``{check:
    [markers]}`` the clauses its detail must name (each such check FAILS too), ``cover_void`` -- COVER VOID and every
    core check VOID ("too few covered runs"); every other check must read PASS. ``report_has`` substrings of the
    report, ``void`` ``{run index: [classes its VOID reasons must include]}``, ``covered`` ``{run index: bool}``."""
    want = {c: True for c in CHECKS}
    if cover_void:
        want["O4-COVER"] = None
        want.update({c: None for c in CORE})
    clauses = {("O4-" + k): v for k, v in (clauses or {}).items()}
    for c in list(fail) + list(clauses):
        cid = c if c.startswith("O4-") else "O4-" + c
        want[cid] = False

    def deco(fn):
        CASES.append((name, fn, want_verdict, want, clauses, tuple(report_has), void or {}, covered or {}))
        return fn
    return deco


def _void(run: dict, v: str, cell, by: str, why: str, *, upto_site=None, tail=(), fight=None) -> None:
    """A run stopped: its events cut after ``upto_site`` (then ``tail``), its drive VOID in class ``v``."""
    if upto_site is not None:
        run["events"] = upto(run["events"], upto_site, *tail)
    run.update(end="void", why=f"route: {why}", v=v, cell=cell, by=by)
    if fight is not None:
        run["fight"] = fight


def _stop_fight(n: int, *, v: str = "V17", by: str = "driver", observed: dict | None = None):
    """A fight stopped at instance ``n`` (its zone VOID): prompts past it never opened, the zone's end None, nothing
    after the zone but the ``observed`` row a game-observed V17 logs (2.4.6)."""
    def fn(fl):
        fl["prompts"] = [p for p in fl["prompts"] if p["n"] <= n]
        fl["presses"] = [p for p in fl["presses"] if p["n"] <= n]
        fl["zone"].update(end=None, instances=n, presses=n, v=v, by=by, why="stopped")
        fl["post"] = [dict(observed)] if observed else []
        fl["pages"] = [P111]
    return fn


def _all(runs: list, **kw) -> list:
    for run in runs:
        run.update(kw)
    return runs


@case("null-pair", "PROVEN", report_has=("a US session", "block 2: 7 byte-equal of 7", "block 3: 7 byte-equal of 7",
                                        "R-GATE WITNESSED", "a FAST play", "Encore achievement",
                                        "49 instances / 49 presses",
                                        "The session's end (end_run, warp first): the title came back"))
def _(pred):
    return six(pred)


@case("fork-drops-a-write", "NOT PROVEN", fail=("WRITES", "NULL", "STATE"))
def _(pred):
    return six(pred, f=lambda ev, n: drop(ev, B18_150))


@case("ladder-missing-fork", "NOT PROVEN", fail=("LADDER", "WRITES", "NULL", "STATE"))
def _(pred):
    return six(pred, f=lambda ev, n: drop(ev, SC1966))


@case("ladder-old-wrong", "NOT PROVEN", fail=("LADDER",))
def _(pred):
    old = lambda ev, n: edit(ev, lambda x: _is(x, SC1966), lambda x: with_opt(x, old=1154))   # noqa: E731
    return six(pred, s=old, f=old)


@case("sc-write-fork", "NOT PROVEN", fail=("LADDER", "WRITES", "NULL", "STATE"))
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, S64[8], w(SC_CS, src="cs")))


@case("sc-write-both", "NOT PROVEN", fail=("LADDER", "WRITES"))
def _(pred):
    add = lambda ev, n: after(ev, S64[8], w(SC_CS, src="cs"))           # noqa: E731
    return six(pred, s=add, f=add)


@case("sc-harness-poke-both", "NOT PROVEN", fail=("LADDER",))
def _(pred):
    poke = lambda ev, n: after(ev, SC1966, w((150, -1, -1, -1, "Global.Byte[0]", 7), src="harness"))   # noqa: E731
    return six(pred, s=poke, f=poke)


@case("chain-dropped-fork", "NOT PROVEN", fail=("CHAIN", "WRITES", "NULL", "STATE"), clauses={"LANDING": ["(b)"]})
def _(pred):
    return six(pred, f=lambda ev, n: drop(ev, CH64))


@case("chain-first-old-wrong", "NOT PROVEN", fail=("CHAIN",))
def _(pred):
    old = lambda ev, n: edit(ev, lambda x: _is(x, CH64), lambda x: with_opt(x, old=101))   # noqa: E731
    return six(pred, s=old, f=old)


@case("start-residue-wrong", "NOT PROVEN", fail=("START",))
def _(pred):
    return six(pred, s=lambda ev, n: edit(ev, lambda x: x[0] == "r" and x[2] == 2, lambda x: r(70, 2, 0, 101)))


@case("start-first-missing", "NOT PROVEN", fail=("START",))
def _(pred):
    gone = lambda ev, n: drop(ev, START64)                             # noqa: E731
    return six(pred, s=gone, f=gone)


@case("start-music-old-wrong", "NOT PROVEN", fail=("START",))
def _(pred):
    old = lambda ev, n: edit(ev, lambda x: _is(x, MUSIC64), lambda x: with_opt(x, old=3))   # noqa: E731
    return six(pred, s=old, f=old)


@case("front-cut-write", "NOT PROVEN", fail=("START",))
def _(pred):
    in70 = ("w", 70, 3, 1, 40, "Global.Byte[13]", 1, {})               # a store in field 70, before the start
    return six(pred, f=lambda ev, n: before(ev, START64, in70))


@case("error-path-start-S", "PROVEN", void={1: ["V5", "A-START"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    runs = six(pred)
    runs[0]["events"] = drop(runs[0]["events"], MUSIC64)
    _void(runs[0], "V5", [64, 1155], "driver", "a stop page (64's ambient error window 3), nothing pressed",
          upto_site=I9_64, tail=(w(ERR64_97), e("off", 64)), fight=False)
    return runs


@case("error-path-150-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={2: False})
def _(pred):
    runs = six(pred)
    runs[1]["events"] = drop(runs[1]["events"], S150[3])
    _void(runs[1], "V5", [150, 1155], "game", "a stop page (150's ambient error window 56), nothing pressed",
          upto_site=I9_150, tail=(w(ERR150_101), e("off", 150)))
    return runs


@case("residue-after-start", "NOT PROVEN", fail=("RESIDUE",))
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, START64, r(64, 300, 0, 7)))


@case("writes-extra-symmetric", "NOT PROVEN", fail=("WRITES",))
def _(pred):
    add = lambda ev, n: after(ev, B303_1255, w(DEAD150_1277))           # noqa: E731
    return six(pred, s=add, f=add)


@case("inert-row-both", "NOT PROVEN", fail=("WRITES",))
def _(pred):
    """An inert function's row in every covered run is an extra key. 150 e10 t3 ip2304's Bit[8511] := 1 (unmasked):
    the design's ip2119 Byte[1034] := 0 lies in the mognet_mailbox story-noise region, so its row would be masked,
    never a key, and WRITES could not fail on it (research/o4_design.md 11.4, PART C)."""
    add = lambda ev, n: after(ev, B303_1255, w(INERT150))               # noqa: E731
    return six(pred, s=add, f=add)


def _score_93(fl: dict) -> None:
    def sub(t):
        return t.replace("\n100 were", "\n93 were") if t.startswith("Of 100 nobles") else t
    fl["pages"] = [sub(p) for p in fl["pages"]]
    for x in fl["post"]:
        if x.get("texts"):
            x["texts"] = [sub(t) for t in x["texts"]]


@case("byte475-93-every-F", "NOT PROVEN", fail=("WRITES", "NULL", "STATE"), clauses={"SWORD": ["(a)", "(b)"]})
def _(pred):
    runs = six(pred, f=lambda ev, n: edit(ev, lambda x: _is(x, SCORE), lambda x: ("w", *x[1:6], 93, x[7])))
    for run in runs:
        if run["side"] == "F":
            run["fight"] = _score_93
            run["end_state"] = dict(pred["end_state"], **{"Global.Byte[475]": 93})
    return runs


@case("bit3815-missing-F", "NOT PROVEN", fail=("WRITES", "NULL", "STATE"), clauses={"SWORD": ["(a)"]})
def _(pred):
    runs = six(pred, f=lambda ev, n: drop(ev, COMBO))
    for run in runs:
        if run["side"] == "F":
            run["end_state"] = dict(pred["end_state"], **{"Global.Bit[3815]": 0})
    return runs


@case("sword-second-390-both", "NOT PROVEN", clauses={"SWORD": ["(a)"]})
def _(pred):
    again = lambda ev, n: after(ev, COMBO, w(COMBO))                    # noqa: E731 -- 1 -> 1, a same-value store
    return six(pred, s=again, f=again)


@case("sword-page-120-both", "NOT PROVEN", clauses={"SWORD": ["(b)"]})
def _(pred):
    def fn(fl):
        fl["pages"] = [P120 if p == pred["chanbara"]["score_page"] else P121 if p == C.PAGE_123 else p
                       for p in fl["pages"]]
    return _all(six(pred), fight=fn)


@case("sword-yes-both", "NOT PROVEN", clauses={"SWORD": ["(c)"]})
def _(pred):
    def fn(fl):
        next(x for x in fl["post"] if x.get("k") == "choice")["index"] = 0
    return _all(six(pred), fight=fn)


@case("sword-gil-page-both", "NOT PROVEN", clauses={"SWORD": ["(d)"]})
def _(pred):
    gil = pred["chanbara"]["gil_page"]
    bad = gil.replace("10000", "9999")

    def fn(fl):
        fl["pages"] = [bad if p == gil else p for p in fl["pages"]]
        for x in fl["post"]:
            if x.get("texts"):
                x["texts"] = [bad if t == gil else t for t in x["texts"]]
    return _all(six(pred), fight=fn)


@case("sword-48-prompts-both", "NOT PROVEN", clauses={"SWORD": ["(e)"]})
def _(pred):
    def fn(fl):
        fl["prompts"], fl["presses"] = fl["prompts"][:48], fl["presses"][:48]
    return _all(six(pred), fight=fn)


@case("sword-circle-alias-both", "NOT PROVEN", clauses={"SWORD": ["(e)"]})
def _(pred):
    def fn(fl):
        row = next(p for p in fl["prompts"] if p["dbtn"] == "CIRCLE")
        row["button"] = "circle"
        next(p for p in fl["presses"] if p["n"] == row["n"])["button"] = "circle"
    return _all(six(pred), fight=fn)


def _with_prompt(n: int, **kw):
    """Instance ``n``'s row (and its press) changed, its j bounds re-read from its frames."""
    def fn(fl):
        row = fl["prompts"][n - 1]
        row.update(kw)
        row["j_lo"], row["j_hi"] = SD.j_bounds(row)
        p = next(x for x in fl["presses"] if x["n"] == n)
        for k in ("accepted_frame", "down_frame"):
            if k in kw:
                p[k] = kw[k]
    return fn


@case("sword-j-over-cap-both", "NOT PROVEN", clauses={"SWORD": ["(e)"]})
def _(pred):
    seen = FIRST + PASS * 4                     # instance 5 goes down 57 frames after its prev sample: j_hi 30
    return _all(six(pred), fight=_with_prompt(5, accepted_frame=seen + 54, down_frame=seen + 55))


@case("sword-j-unbounded-both", "NOT PROVEN", clauses={"SWORD": ["(e)"]})
def _(pred):
    """Instance 1 with no prev frame -- a zone entered on a prompt that nothing gave a prev: its row has no j bounds and
    the complete zone's raw is unbounded, so raw_floor cannot be judged. The judge's V17, never a SWORD pass with the
    floor unjudged (the review, research/o4_design.md 11.5)."""
    return _all(six(pred), fight=_with_prompt(1, prev_frame=None))


@case("sword-evidence-before-both", "NOT PROVEN", clauses={"SWORD": ["(e)"]})
def _(pred):
    return _all(six(pred), fight=_with_prompt(7, evidence="before"))


@case("sword-evidence-lingered-both", "NOT PROVEN", clauses={"SWORD": ["(e)"]})
def _(pred):
    seen = FIRST + PASS * 6
    return _all(six(pred), fight=_with_prompt(7, evidence="lingered", last_listed_frame=seen + 4 + 30))


@case("sword-evidence-unobserved-both", "NOT PROVEN", clauses={"SWORD": ["(e)"]})
def _(pred):
    seen = FIRST + PASS * 8                     # samples jump from down + 2 to down + 40: none lists it after
    return _all(six(pred), fight=_with_prompt(9, evidence="unobserved", last_listed_frame=seen + 6,
                                              gone_frame=None, read_gap={"frames": 38, "ticks": 19, "s": 0.64}))


@case("sword-slide-not-ok-both", "NOT PROVEN", clauses={"SWORD": ["(e)"]})
def _(pred):
    """An L/R instance (not in the tail) MEASURED with dx 0: its slide is missing from every later sample (the game
    read the key as a miss), so only its own slide reads 0 -- left out, V18."""
    def fn(fl):
        n = next(p["n"] for p in fl["prompts"] if p["dbtn"] in SD.LR_WANT and p["n"] <= 40)
        dx = SD.LR_WANT[fl["prompts"][n - 1]["dbtn"]]
        for p in fl["prompts"]:
            if p["n"] >= n + 2:
                p["x_prev"] = {k: v - dx for k, v in p["x_prev"].items()}
                p["x_seen"] = {k: v - dx for k, v in p["x_seen"].items()}
        slides_again(fl, pred["chanbara"])
        assert fl["prompts"][n - 1]["slide"]["left_out"] == [n], fl["prompts"][n - 1]["slide"]
    return _all(six(pred), fight=fn)


@case("sword-slide-unmeasured-both", "PROVEN")
def _(pred):
    """Two L/R instances' successors seen 12 frames after them: their base samples 10 frames (4 sure ticks) after the
    predecessor's seen frame, under the 7 a slide needs -- "unmeasured", counted, no fault."""
    def fn(fl):
        lr = [p["n"] for p in fl["prompts"] if p["dbtn"] in SD.LR_WANT and p["n"] <= 40][:2]
        for n in lr:
            nxt = fl["prompts"][n]
            seen = fl["prompts"][n - 1]["seen_frame"] + 12
            nxt.update(seen_frame=seen, prev_frame=seen - 2, accepted_frame=seen + 3, down_frame=seen + 4,
                       ack_frame=seen + 7, last_listed_frame=seen + 12, gone_frame=seen + 14)
            nxt["j_lo"], nxt["j_hi"] = SD.j_bounds(nxt)
            p = next(x for x in fl["presses"] if x["n"] == nxt["n"])
            p.update(accepted_frame=seen + 3, down_frame=seen + 4)
        slides_again(fl, pred["chanbara"])
        assert all(fl["prompts"][n - 1]["slide"]["ok"] == "unmeasured" for n in lr), lr
        assert not any(p["slide"] and p["slide"]["ok"] is False for p in fl["prompts"])
    return _all(six(pred), fight=fn)


@case("sword-input-noise-both", "NOT PROVEN", clauses={"SWORD": ["(e)"]})
def _(pred):
    def fn(fl):
        fl["zone"]["input"] = [{"t": 40.2, "frame": 6000, "what": "XInput slot 0: buttons 0x1000"}]
    return _all(six(pred), fight=fn)


@case("sword-stray-press-both", "NOT PROVEN", clauses={"SWORD": ["(f)"]})
def _(pred):
    def fn(fl):
        f0 = fl["prompts"][0]["prev_frame"]
        fl["post"].insert(0, {"k": "press", "why": "page", "field": fl["zone"]["field"], "donor": 64, "visit": 1,
                              "sc": 1155, "pre": {"frame": f0 + 300}, "post": None, "near": [], "seq": 9999,
                              "ack_frame": f0 + 305, "button": "confirm", "texts": ["Press  !"],
                              "accepted_frame": f0 + 301, "down_frame": f0 + 302})
    return _all(six(pred), fight=fn)


@case("sword-111-closing-press-late-both", "PROVEN")
def _(pred):
    """111's press goes down AFTER ``start_page.last_with_frame`` (the press that closes 111 lands in its close tween,
    before 111 leaves the list) and before instance 1's ``prev_frame``: rev. 1's window (from last_with) flagged it;
    the fight's window, from the first prompt's prev, does not."""
    def fn(fl):
        last_with = fl["zone"]["start_page"]["last_with_frame"]
        p111 = fl["pre"][-1]
        p111.update(accepted_frame=last_with + 3, down_frame=last_with + 4)
        assert last_with < p111["down_frame"] < fl["prompts"][0]["prev_frame"]
    return _all(six(pred), fight=fn)


@case("v17-one-S", "PROVEN", void={1: ["V17"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    runs = six(pred)
    _void(runs[0], "V17", [64, 1155], "driver", "instance 12's j_hi 18 is over j_cap 16", upto_site=S64[8],
          tail=(e("off", 64),), fight=_stop_fight(12))
    return runs


@case("v17-all-F", "NOT PROVEN", cover_void=True, clauses={"VOID-ASYM": ["(b)"]})
def _(pred):
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            _void(run, "V17", [64, 1155], "driver", "instance 12's j_hi 18 is over j_cap 16", upto_site=S64[8],
                  tail=(e("off", 64),), fight=_stop_fight(12))
    return runs


def _v18(run: dict) -> None:
    _void(run, "V18", [64, 1155], "game", "instance 7 was still listed at or past its mark: the game read no key",
          upto_site=S64[8], tail=(e("off", 64),), fight=_stop_fight(7, v="V18", by="game"))


@case("v18-one-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)", "(c)"]}, covered={2: False})
def _(pred):
    runs = six(pred)
    _v18(runs[1])
    return runs


@case("v18-one-each-side", "NOT PROVEN", clauses={"VOID-ASYM": ["(c)"]}, covered={1: False, 2: False})
def _(pred):
    runs = six(pred)
    _v18(runs[0])
    _v18(runs[1])
    return runs


@case("v19-one-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)", "(c)"]}, covered={2: False})
def _(pred):
    """One F run lands in REAL 153 (an un-retargeted Field()): V19 by the game at [153, 1190]; its real-153 rows are
    cut away as place 153 -- the run is uncovered, and VOID-ASYM reads the finding."""
    runs = six(pred)
    ev = edit(runs[1]["events"], lambda x: _is(x, END153), lambda x: with_opt(x, fld=153, don=153))
    runs[1]["events"] = ev[:-1] + [w(s, fld=153, don=153) for s in AFTER153] + [ev[-1]]
    _void(runs[1], "V19", [153, 1190], "game", "the fork run entered REAL 153, where member(153) 31245 was due")
    return runs


@case("leak-real-150-F", "NOT PROVEN", fail=("FORBIDDEN",), clauses={"VOID-ASYM": ["(a)", "(c)"]}, covered={2: False})
def _(pred):
    runs = six(pred)
    real = edit(runs[1]["events"], lambda x: x[0] == "w" and x[1] == 150, lambda x: with_opt(x, fld=150, don=150))
    _void(runs[1], "V19", [150, 1155], "game", "the fork run entered REAL 150, where member(150) 31243 was due")
    runs[1]["events"] = upto(real, S150[6], e("off", 150))
    return runs


@case("control-S", "NOT PROVEN", clauses={"VOID-ASYM": ["(a)"]}, covered={1: False})
def _(pred):
    runs = six(pred)
    _void(runs[0], "V4", [150, 1155], "game", "control held in 150 (place 150) at SC 1155, where the table has no "
                                               "entry", upto_site=S150[6], tail=(e("off", 150),))
    return runs


def _observed(run: dict) -> None:
    _void(run, "V17", [64, 1155], "driver", "a dialog the prompt rule does not claim in the fight zone",
          upto_site=S64[8], tail=(e("off", 64),), fight=_stop_fight(5, observed=OBSERVED))


@case("observed-unclaimed-one-F", "NOT PROVEN", clauses={"VOID-ASYM": ["(d)"]}, covered={2: False})
def _(pred):
    runs = six(pred)
    _observed(runs[1])
    return runs


@case("observed-unclaimed-one-each-side", "PROVEN", covered={1: False, 2: False, 3: True, 4: True})
def _(pred):
    runs = six(pred)
    _observed(runs[0])
    _observed(runs[1])
    return runs


@case("v13-input-one-F", "PROVEN", void={2: ["V13"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    runs = six(pred)
    _void(runs[1], "V13", None, "driver", "outside input during the fight: XInput slot 0: buttons 0x1000",
          upto_site=S64[8], tail=(e("off", 64),), fight=_stop_fight(20))
    runs[1]["why"] = "STOPPED: outside input during the fight: XInput slot 0: buttons 0x1000"
    return runs


@case("stray-yes-driver-S", "PROVEN", void={1: ["V17"]}, covered={1: False, 3: True, 5: True})
def _(pred):
    """One S run's own page Confirm went down after 127's first frame (2.4.11): the replay is the driver's -- V17,
    never a V2 the game owns."""
    runs = six(pred)

    def fn(fl):
        ch = next(x for x in fl["post"] if x.get("k") == "choice")
        at = fl["post"].index(ch)
        fl["post"] = fl["post"][:at + 1] + [{"k": "press", "why": "page", "field": fl["zone"]["field"], "donor": 64,
                                             "visit": 1, "sc": 1155, "pre": {"frame": ch["frame"] - 2}, "post": None,
                                             "near": [], "seq": 777, "ack_frame": ch["frame"] + 4,
                                             "button": "confirm", "texts": [C.PAGE_123],
                                             "accepted_frame": ch["frame"] + 1, "down_frame": ch["frame"] + 2}]
        fl["pages"] = fl["pages"][:3]
    _void(runs[0], "V17", [64, 1155], "driver", "a Confirm of the driver's own (seq 777, page) landed on choice 127 "
                                                "before its answer", upto_site=COMBO, tail=(e("off", 64),), fight=fn)
    return runs


@case("extra-key-one-F", "NOT PROVEN", fail=("STABLE", "WRITES", "STATE"))
def _(pred):
    return six(pred, f=lambda ev, n: after(ev, B303_1255, w(DEAD150_1277)) if n == 0 else ev)


@case("lands-real-150-covered", "NOT PROVEN", fail=("FORBIDDEN", "WRITES"), clauses={"LANDING": ["(a)", "(b)", "(e)"]})
def _(pred):
    real = lambda ev, n: edit(ev, lambda x: x[0] == "w" and x[1] == 150,  # noqa: E731
                              lambda x: with_opt(x, fld=150, don=150))
    return six(pred, f=real)


@case("64-after-150-both", "NOT PROVEN", clauses={"LANDING": ["(b)"]})
def _(pred):
    add = lambda ev, n: after(ev, ENTER150, w(MUSIC64))                # noqa: E731
    return six(pred, s=add, f=add)


@case("last-place-harness-both", "NOT PROVEN", clauses={"LANDING": ["(c)"]})
def _(pred):
    poke = lambda ev, n: after(ev, CH150, w((150, -1, -1, -1, "Global.Byte[300]", 9), src="harness"))  # noqa: E731
    return six(pred, s=poke, f=poke)


@case("end-log-row-real-153-F", "NOT PROVEN", clauses={"LANDING": ["(c)"]})
def _(pred):
    """A SYNTHETIC log (the claim critique #15): every F run's ``end`` row names field 153 while its trace cuts at
    member(153) -- the live rule 1 writes that row only for a field in the side's own end list, so no session produces
    it; the clause guards the per-side end lists S6 configures."""
    runs = six(pred)
    for run in runs:
        if run["side"] == "F":
            run["end_field"] = 153
    return runs


@case("end-real-153-F", "NOT PROVEN", clauses={"LANDING": ["(d)"]})
def _(pred):
    real = lambda ev, n: edit(ev, lambda x: _is(x, END153), lambda x: with_opt(x, fld=153, don=153))   # noqa: E731
    return six(pred, f=real)


@case("end-boundary-residue-both", "NOT PROVEN", clauses={"LANDING": ["(d)"]})
def _(pred):
    add = lambda ev, n: before(ev, END153, r(153, 300, 0, 1))          # noqa: E731
    return six(pred, s=add, f=add)


@case("end-row-missing-one-S", "PROVEN", void={1: ["A-NOEND"]}, covered={1: False, 3: True, 5: True},
      report_has=("A-NOEND",))
def _(pred):
    runs = six(pred)
    runs[0]["events"] = drop(runs[0]["events"], END153)
    return runs


@case("sword-beat-missing", "VOID", cover_void=True, void={1: ["A-BEATS"], 3: ["A-BEATS"]})
def _(pred):
    runs = six(pred)
    for run in (runs[0], runs[2]):
        run["beats"] = {"sword": False, "encore": True}
    return runs


@case("end-cut", "PROVEN")
def _(pred):
    return six(pred, s=lambda ev, n: ev[:-1] + [w(x) for x in AFTER153] + [ev[-1]])


@case("end-state-differs", "NOT PROVEN", fail=("STATE",))
def _(pred):
    runs = six(pred)
    runs[3]["end_state"] = dict(pred["end_state"], **{"Global.Byte[303]": 0})
    return runs


@case("masked-differs", "NOT PROVEN", fail=("MASKED",))
def _(pred):
    return six(pred, f=lambda ev, n: drop(ev, *BIT184S))


@case("mismatched", "PROVEN", void={2: ["A-MISMATCH"]}, covered={2: False, 4: True, 6: True})
def _(pred):
    return six(pred, f=lambda ev, n: edit(ev, lambda x: x[0] == "w" and x[1] == 150,
                                          lambda x: with_opt(x, don=31243)) if n == 0 else ev)


@case("no-start-row", "PROVEN", void={1: ["A-NOSTART"]}, covered={1: False})
def _(pred):
    runs = six(pred)
    runs[0]["events"] = base_events()[:4] + [e("off", 70)]
    runs[0]["fight"] = False
    return runs


@case("join-failure", "NOT PROVEN", fail=("JOIN",))
def _(pred):
    off = (150, 3, 1, 1684, "Global.Byte[18]", 1)                      # one byte into the ip1683 store
    add = lambda ev, n: after(ev, B18_150, w(off))                      # noqa: E731
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


def _policy(pred: dict, **over) -> dict:
    p = copy.deepcopy(pred["chanbara"])
    for k, v in over.items():
        if v is ...:
            p.pop(k, None)
        else:
            p[k] = v
    return p


def _paced(pred: dict, **over) -> dict:
    return _policy(pred, **{**C.PACED, "raw_floor": ..., **over})


def unit_chanbara_policy(pred: dict) -> tuple:
    """segment_drive.chanbara_of (2.4.4, 4.10): 4.10's draft and the paced overlay pass (a copy); each refusal raises,
    naming its cause -- an unknown key, a missing one, ``circle`` for CIRCLE (named Control.Confirm), any other map,
    ``j_cap`` 17 under fast, a ``raw_floor`` under paced, a ``pace`` under fast, ``press_frames`` 0, ``stop_after``
    49, a bool for an int."""
    def of(p):
        return lambda: SD.chanbara_of({"chanbara": p})
    draft, paced = _policy(pred), _paced(pred)
    got = {"draft": SD.chanbara_of({"chanbara": draft}) == draft, "paced": SD.chanbara_of({"chanbara": paced}) == paced}
    btn = dict(pred["chanbara"]["buttons"])
    for name, p, match in (("unknown", _policy(pred, extra=1), "unknown key"),
                           ("missing", _policy(pred, gone_ticks=...), "missing"),
                           ("circle", _policy(pred, buttons=dict(btn, CIRCLE="circle")),
                            "CIRCLE -> 'circle' is Control.Confirm"),
                           ("other-map", _policy(pred, buttons=dict(btn, UP="down")), "where the map is 'up'"),
                           ("j_cap-17", _policy(pred, j_cap=17), "j_cap"),
                           ("raw_floor-paced", _paced(pred, raw_floor=100), "raw_floor under the paced"),
                           ("pace-fast", _policy(pred, pace=dict(C.PACED["pace"])), "a pace under the fast"),
                           ("press_frames-0", _policy(pred, press_frames=0), "press_frames"),
                           ("stop_after-49", _policy(pred, stop_after=49), "stop_after"),
                           ("bool", _policy(pred, prompts=True), "prompts")):
        got[name] = _raises(of(p), match)
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_prompt_shape(pred: dict, mes: dict) -> tuple:
    """The recognizers (2.4.1): each of the eight prompt forms -- the published form and block 2's source (mes
    112-119, as the engine reads them) -- is its DBTN; 111 (eight tags) is no prompt and is the zone start; 150's
    window 55 (two tags, no "Press") is neither; a prompt without [TIME=-1] is none; the rendered "Press  !" alone is
    none."""
    pol = pred["chanbara"]
    got = {f"raw-{d}": SD.prompt_dbtn(prompt_raw(d)) == d and not SD.is_zone_start([prompt_raw(d)], pol)
           for d in DBTNS}
    got.update({f"mes-{m}": SD.prompt_dbtn(mes.get(int(m))) == d for m, d in pred["fight"]["prompt_mes"].items()})
    t111 = mes.get(111)
    got["111"] = SD.prompt_dbtn(t111) is None and SD.is_zone_start([t111], pol)
    w55 = "[STRT=180,3][TAIL=DEFT]Set Scenario Counter()\n[DBTN=START] OK  [DBTN=SELECT] Cancel"
    got["w55"] = SD.prompt_dbtn(w55) is None and not SD.is_zone_start([w55], pol)
    got["no-time"] = SD.prompt_dbtn(prompt_raw("LEFT").replace("[TIME=-1]", "")) is None
    got["rendered"] = SD.prompt_dbtn("Press  !") is None
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def _jrow(n: int, dbtn: str, *, seen=None, prev=-2, down=4, excess=0.0, rate=None, **kw) -> dict:
    """A prompt row as the executor completes it (2.4.6): ``seen`` its first frame (default 100 n), ``prev`` / ``down``
    offsets from it, the press and its accepted event, the j bounds from those frames, evidence "closed"."""
    seen = 100 * n if seen is None else seen
    row = {"k": "prompt", "n": n, "dbtn": dbtn, "button": SD.DBTN_CONTROL[dbtn], "seq": 10 + n,
           "prev_frame": seen + prev, "prev_kind": "none", "seen_frame": seen, "accepted_frame": seen + down - 1,
           "down_frame": seen + down, "ack_frame": seen + down + 3, "rate": dict(rate or RATE60), "excess": excess,
           "evidence": "closed", "read_gap": {"frames": 2, "ticks": 1, "s": 0.03}, "slide": None,
           "x_prev": {"player": 0.0, "blank": 600.0}, "x_seen": {"player": 0.0, "blank": 600.0}}
    row.update(kw)
    row["j_lo"], row["j_hi"] = SD.j_bounds(row)
    return row


def _jrows(n: int = 49, **kw) -> list:
    seq = ["CROSS", "TRIANGLE", "RIGHT", "TRIANGLE", "LEFT", "CROSS", "TRIANGLE"]
    return [_jrow(i, seq[(i - 1) % len(seq)], **kw) for i in range(1, n + 1)]


def _jzone(rows: list, **kw) -> dict:
    zone = {"k": "zone", "end": {"frame": (rows[-1]["seen_frame"] + 60) if rows else 0, "text": P107},
            "max_read_gap": {"frames": 2, "ticks": 1, "s": 0.03}}
    zone.update(kw)
    return zone


def _jpresses(rows: list) -> list:
    return [{"k": "press", "why": "prompt", "n": x["n"], "seq": x["seq"], "button": x["button"],
             "down_frame": x["down_frame"]} for x in rows]


def unit_j_bounds() -> tuple:
    """j_bounds and raw_bounds (2.4.7): [1, 5] at 60 fps from a row's frames (prev = seen - 2, down = seen + 4) and at
    31 (prev = seen - 1, down = seen + 3); a hitch's excess 2.3 raises j_hi to 8; raw_bounds on uniform j reproduces
    the plan's table (1 -> 126, 5 -> 119, 10 -> 111, 16 -> 100, 17 -> 99, 20 -> 93, 28 -> 80, 29 -> 78) and the SA 1
    display (79 -> 100, 78 -> 99). Then against the TRUE j, both publication orders: synthetic frame/tick schedules at
    31 and 60 fps (+-5% frame jitter, the engine's accumulator, a +-2% band; one sample every 2nd frame; the arm in the
    frame the order lets its first listing sample show; the key down 1-8 frames after) -- the true j lies in [j_lo,
    j_hi] every time, while the unit's two mutants, each unsound (research/o4_design.md 11.4 PART B #17), are caught:
    j_hi counted from ``seen`` (the true j exceeds it) and j_lo counted from ``prev`` (it overstates)."""
    from harness.tickrate import Rate, TickAccumulator
    r31 = {"fps": 31.2, "fps_lo": 30.5, "fps_hi": 31.9, "tick_hz": 30.0, "source": "mtime"}
    j60, j31 = _jrow(1, "LEFT", seen=1000), _jrow(1, "LEFT", seen=1000, prev=-1, down=3, rate=r31)
    got = {"60": (j60["j_lo"], j60["j_hi"]) == (1, 5), "31": (j31["j_lo"], j31["j_hi"]) == (1, 5),
           "excess": SD.j_bounds(dict(j60, excess=2.3))[1] == 8,
           "table": all(SD.raw_bounds([{"j_lo": j, "j_hi": j}] * 49) == (raw, raw) for j, raw in (
               (1, 126), (5, 119), (10, 111), (16, 100), (17, 99), (20, 93), (28, 80), (29, 78))),
           "rows": SD.raw_bounds(_jrows()) == (119, 126),
           "sa1": [min(100, x + x // 10 * 3) for x in (79, 78)] == [100, 99]}
    rng = random.Random(11)
    n = bad = hi_seen = lo_prev = 0
    for fps in (31.0, 60.0):
        acc, first_tick, tick_frame, t = TickAccumulator(30.0), {}, {}, 0
        for f in range(1, 3001):
            k = acc.advance((1.0 / fps) * (1 + rng.uniform(-0.05, 0.05)))
            first_tick[f] = t + 1 if k else None
            for _ in range(k):
                t += 1
                tick_frame[t] = f
        rate = Rate(fps=fps, fps_lo=fps * 0.98, fps_hi=fps * 1.02, tick_hz=30.0, source="rt", samples=20, frame=1)
        for order in ("agent_first", "agent_last"):
            for _ in range(500):
                s = rng.randint(200, t - 400)
                arm, phase = tick_frame[s], rng.randrange(2)
                pubs = [f for f in range(arm - 20, arm + 40) if f % 2 == phase]
                seen = next(f for f in pubs if (f - 1 if order == "agent_first" else f) >= arm)
                prev = max(f for f in pubs if f < seen)
                down = seen + rng.randint(1, 8)
                edge = next(first_tick[f] for f in range(down, down + 50) if first_tick.get(f))
                lo, hi = SD.j_bounds({"prev_frame": prev, "seen_frame": seen, "down_frame": down, "excess": 0.0,
                                      "rate": rate.as_dict()})
                j = edge - s
                n += 1
                bad += not (lo <= j <= hi)
                hi_seen += j > rate.ticks_most(max(0, down - seen)) + 1
                lo_prev += j < max(1, rate.ticks_sure(max(0, down - prev - 1)))
    got["true-j"] = bad == 0
    got["mutant-hi-from-seen"] = hi_seen > 0
    got["mutant-lo-from-prev"] = lo_prev > 0
    return (all(got.values()), str({k: v for k, v in got.items() if not v} or
                                    f"all as registered ({n} schedules; the mutants miss {hi_seen} / {lo_prev})"))


def unit_judge(pred: dict) -> tuple:
    """chanbara_judge (2.4.8), each line of section 8's unit: proper rows -> None (raw [119, 126]); one instance at j_hi
    45 -> V17; a score page "99 were impressed." in two samples -> V18; "[NUMB=0]" then "100" -> None; "lingered" ->
    V18; "unobserved" -> V17, never V18; "before" -> V17; a measured slide of 0 (left out) -> V18; -240 -> V17; a wrong
    name, a double press, a missing event -> V17 each; 48 instances with a 60-tick gap -> V17, with none above 50 ->
    V18; 50 instances -> V18; paced raw [80, 92] -> None, [76, 85] -> V17 "uninformative"; a fast raw_floor 110 with
    every j_hi 12 (raw_lo 107) -> V17; instance 1 with no prev frame (no j bounds: the raw unbounded) -> V17 under the
    fast policy and the paced one alike, "raw unbounded" among the faults (the review, 11.5)."""
    pol = pred["chanbara"]

    def jv(rows=None, *, zone=None, presses=None, policy=pol, page=None):
        rows = _jrows() if rows is None else rows
        return SD.chanbara_judge(_jzone(rows) if zone is None else zone, rows,
                                 _jpresses(rows) if presses is None else presses, policy, page=page)

    def with_row(i, **kw):
        rows = _jrows()
        rows[i] = dict(rows[i], **kw)
        return rows
    rows45 = _jrows()
    rows45[6] = _jrow(7, rows45[6]["dbtn"], prev=-82)
    score99 = pol["score_page"].replace("\n100 ", "\n99 ")
    unsub = pol["score_page"].replace("\n100 ", "\n[NUMB=0] ")
    r48 = _jrows(48)
    rows = _jrows()
    nop = _jrows()
    nop[0] = _jrow(1, nop[0]["dbtn"], prev_frame=None)
    band = [dict(x, j_lo=21, j_hi=28) for x in _jrows()]
    band[0] = dict(nop[0])

    def unbounded(got):
        return (got["v"] == "V17" and got["why"].startswith("instance 1 (CROSS) has no j bounds (no prev frame)")
                and any(f.startswith("raw unbounded") for f in got["faults"]))
    got = {"proper": jv() == {"v": None, "by": None, "why": None, "faults": [], "raw": [119, 126]},
           "unbounded-fast": nop[0]["j_hi"] is None and unbounded(jv(nop)),
           "unbounded-paced": unbounded(jv(band, policy=_paced(pred))),
           "j45": rows45[6]["j_hi"] == 45 and jv(rows45)["v"] == "V17",
           "score99": jv(page={"kind": "score", "want": pol["score_page"], "texts": [score99, score99]})["v"] == "V18",
           "unsub": jv(page={"kind": "score", "want": pol["score_page"], "texts": [unsub, pol["score_page"]]})["v"]
           is None,
           "lingered": jv(with_row(4, evidence="lingered"))["v"] == "V18",
           "unobserved": jv(with_row(8, evidence="unobserved", read_gap={"frames": 30, "ticks": 15, "s": 0.5}))["v"]
           == "V17",
           "before": jv(with_row(2, evidence="before"))["v"] == "V17",
           "slide-0": jv(with_row(2, slide={"want": 300.0, "dx_player": 0.0, "dx_blank": 0.0, "ok": False,
                                            "left_out": [3]}))["v"] == "V18",
           "slide-240": jv(with_row(4, slide={"want": -300.0, "dx_player": -240.0, "dx_blank": -240.0, "ok": False,
                                              "left_out": None}))["v"] == "V17",
           "wrong-name": jv(with_row(0, button="x"))["v"] == "V17",
           "double": jv(rows, presses=_jpresses(rows) + _jpresses(rows)[:1])["v"] == "V17",
           "no-event": jv(with_row(1, accepted_frame=None))["v"] == "V17",
           "48-gap60": jv(r48, zone=_jzone(r48, max_read_gap={"frames": 120, "ticks": 60, "s": 2.0}))["v"] == "V17",
           "48-gap50": jv(r48, zone=_jzone(r48, max_read_gap={"frames": 100, "ticks": 50, "s": 1.7}))["v"] == "V18",
           "50": jv(_jrows(50))["v"] == "V18",
           "paced-in": jv([dict(x, j_lo=21, j_hi=28) for x in _jrows()], policy=_paced(pred))
           == {"v": None, "by": None, "why": None, "faults": [], "raw": [80, 92]},
           "paced-out": jv([dict(x, j_lo=25, j_hi=30) for x in _jrows()], policy=_paced(pred))["why"]
           == "uninformative: raw [76, 85] is outside the band [79, 99]",
           "floor": jv([dict(x, j_lo=1, j_hi=12) for x in _jrows()], policy=_policy(pred, raw_floor=110))["why"]
           == "raw_lo 107 is under raw_floor 110"}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_slides() -> tuple:
    """measure_slides (2.4.6), at ~31 fps with the agent-first publication: a synthetic L/R run -- a LEFT / RIGHT hit
    on prompt n slides Blank -60 a tick from S_{n+1}+1 and Zidane a tick behind -- whose first sample listing each
    prompt already shows a step. Between the PREV samples every L/R slide reads its want; rev. 1's baseline (the next
    instance's ``x_seen``, the unit's mutant) reads otherwise on some; a base sample under 7 sure ticks after its
    predecessor's seen frame is "unmeasured"; the tail (48 LEFT, 49 LEFT) reads -600 jointly from instance 49's prev
    sample to the zone end; (48 RIGHT, 49 LEFT) is "unmeasured"."""
    r31 = {"fps": 31.0, "fps_lo": 30.4, "fps_hi": 31.6, "tick_hz": 30.0, "source": "mtime", "samples": 30}

    def track(dbtns):
        arm = {n: 100 + 30 * n + n % 2 for n in range(1, len(dbtns) + 2)}         # the last: the phantom pass
        moves = []
        for n, d in enumerate(dbtns, 1):
            step = {"LEFT": -60.0, "RIGHT": 60.0}.get(d)
            if step:
                s = arm[n + 1]
                moves += [(s + k, "blank", step) for k in range(1, 6)] + [(s + 1 + k, "player", step) for k in range(1, 6)]

        def pos(tick):
            return {"player": 0.0 + sum(dx for t, b, dx in moves if b == "player" and t <= tick),
                    "blank": 600.0 + sum(dx for t, b, dx in moves if b == "blank" and t <= tick)}
        rows = []
        for n, d in enumerate(dbtns, 1):
            seen = arm[n] + 1 if (arm[n] + 1) % 2 == 0 else arm[n] + 2           # agent first, a sample every 2nd frame
            rows.append(_jrow(n, d, seen=seen, rate=r31, x_prev=pos(seen - 3), x_seen=pos(seen - 1)))
        end = arm[len(dbtns) + 1] + 40
        return rows, {"frame": end, "x_player": pos(end - 1)["player"], "x_blank": pos(end - 1)["blank"]}
    seq = (["CROSS", "LEFT", "TRIANGLE", "RIGHT", "LEFT", "CROSS", "RIGHT", "TRIANGLE"] * 6)[:47] + ["LEFT", "LEFT"]
    rows, end = track(seq)
    lr = [x["n"] for x in rows if x["dbtn"] in SD.LR_WANT]
    slides = SD.measure_slides(rows, end, 49)
    got = {"prev-samples": all(slides[n]["ok"] is True and slides[n]["dx_blank"] == slides[n]["want"]
                               for n in lr[:-2])}
    rev1 = [round(rows[n + 1]["x_seen"]["blank"] - rows[n]["x_seen"]["blank"], 1) for n in lr[:-2]]
    got["rev1-reads-otherwise"] = any(abs(dx - SD.LR_WANT[rows[n - 1]["dbtn"]]) > 1.0 for n, dx in zip(lr, rev1))
    tail = slides[48]
    got["tail"] = tail is slides[49] and tail["joint"] == [48, 49] and tail["want"] == -600.0 and tail["ok"] is True
    near = [dict(x) for x in rows]
    n0 = lr[0]
    near[n0] = dict(near[n0], prev_frame=near[n0 - 1]["seen_frame"] + 3)
    got["unmeasured"] = SD.measure_slides(near, end, 49)[n0]["ok"] == "unmeasured"
    rows2, end2 = track(seq[:47] + ["RIGHT", "LEFT"])
    got["tail-opposite"] = SD.measure_slides(rows2, end2, 49)[48]["ok"] == "unmeasured"
    return all(got.values()), str({k: v for k, v in got.items() if not v} or f"all as registered ({len(lr)} L/R; "
                                                                               f"rev. 1 reads {rev1[:4]})")


def unit_stray_answer() -> tuple:
    """stray_answer (2.4.11): a page press whose down frame lies in [127's first frame, its close): V17; ``choose``'s
    Confirm with the cursor on Yes: V17; on No: excluded, V2; a prompt press long before 127: ignored, V2; none: V2."""
    first, close = 5000, 5040
    events = [{"frame": f, "kind": "accepted", "seq": str(s), "steps": "1"}
              for s, f in ((1, 100), (2, 5001), (3, 5010), (4, 5020))]
    steps = [{"kind": "step", "seq": 3, "steps": ["press down 4"]}, {"kind": "step", "seq": 4, "steps": ["press confirm 4"]}]
    page = {"k": "press", "why": "page", "seq": 2, "button": "confirm", "pre": {"frame": 4996}}
    prompt = {"k": "press", "why": "prompt", "seq": 1, "button": "confirm", "pre": {"frame": 98}}
    down = {"k": "press", "why": "choose", "seq": 3, "pre": None}

    def answer(sel):
        return {"k": "press", "why": "choose", "seq": 4, "answer": True, "selected_before": sel, "pre": None}
    got = {"page": SD.stray_answer([page], events, steps, first, close)["v"] == "V17",
           "yes": SD.stray_answer([prompt, down, answer(0)], events, steps, first, close)["v"] == "V17",
           "no": SD.stray_answer([prompt, down, answer(1)], events, steps, first, close)["v"] == "V2",
           "prompt": SD.stray_answer([prompt], events, steps, first, close)["v"] == "V2",
           "none": SD.stray_answer([], events, steps, first, close)["v"] == "V2"}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def _reading(side: str, *, informative=True, number=100, byte475=100, combo=False, v18=False, sa="1",
             engine=None) -> dict:
    settings = json.loads(json.dumps(C.SETTINGS))
    settings["Hacks"]["SwordplayAssistance"] = sa
    return {"side": side, "informative": informative, "why": "synthetic", "raw": [80, 92],
            "judge": {"v": "V18" if v18 else None, "why": "instance 9 was still listed at or past its mark"},
            "page": f"Of 100 nobles watching,\n{number} were impressed.", "number": number, "combo": combo,
            "byte475": byte475, "settings": settings,
            "engine": engine or {"x64": C.ENGINE["x64"], "x86": C.ENGINE["x86"]}, "v": None}


def unit_gate_verdict(pred: dict) -> tuple:
    """gate_verdict (7.4 G2): S 100 + F 100 WITNESSED; F Byte[475] 90 with page "90 were impressed." BROKEN, cause
    bonus; F pages 120/121, or an informative F run whose judge reads V18 (a lingered press), BROKEN, cause combo; S
    page 93 INVALID; an out-of-band run and one with an "unobserved" instance (gate_reading on paced rows: each
    uninformative), three attempts on a side, UNINFORMATIVE; a run whose launch recorded SwordplayAssistance 2 or
    another engine is no witness. And gate_reading's informative rule (the review, research/o4_design.md 11.5): a
    complete in-band fight with its score page and Byte[475] informative; uninformative a fight stopped mid-way (a
    V14 stall, a live V17) with proper rows, a V13 run whose readings are all present, a complete fight with an
    unbounded row (no prev frame), no score page, an S fight's V18 (mid-fight or at Z3) -- an F one's informative; so
    three mid-fight S stops read UNINFORMATIVE, never INVALID, and a stop then proper runs WITNESSED."""
    v = C.gate_verdict
    pol = _paced(pred)
    band = [dict(x, j_lo=25, j_hi=30) for x in _jrows()]
    stall = [dict(x, j_lo=21, j_hi=28) for x in _jrows()]
    stall[8] = dict(stall[8], evidence="unobserved")
    settings, engine = json.loads(json.dumps(C.SETTINGS)), {"x64": C.ENGINE["x64"], "x86": C.ENGINE["x86"]}

    def gate_read(rows, side="S", zone=None, *, pages=(), byte475=100, run_v=None):
        return C.gate_reading(side, zone=_jzone(rows) if zone is None else zone, prompts=rows,
                              presses=_jpresses(rows), pages=list(pages), page_judge=[], byte475=byte475, pol=pol,
                              settings=settings, engine=engine, v=run_v)
    oob, unobs = gate_read(band), gate_read(stall)
    page = pred["chanbara"]["score_page"]
    proper = [dict(x, j_lo=21, j_hi=28) for x in _jrows()]
    good = gate_read(proper, pages=(page,))
    part = proper[:20]
    stops = [gate_read(part, zone=_jzone(part, end=None, v=zv, why="a live stop"), run_v=zv, byte475=None)
             for zv in ("V14", "V17")]
    nop = list(proper)
    nop[0] = dict(_jrow(1, proper[0]["dbtn"], prev_frame=None), j_lo=None, j_hi=None)
    lingered = list(proper)
    lingered[4] = dict(lingered[4], evidence="lingered")
    mid = lingered[:5]
    zmid = _jzone(mid, end=None, v="V18", why="instance 5 was still listed at or past its mark")
    got = {"witnessed": v([_reading("S"), _reading("F")])["verdict"] == "WITNESSED",
           "reading-informative": good["informative"],
           "reading-stopped": not any(x["informative"] for x in stops),
           "reading-v13": not gate_read(proper, pages=(page,), run_v="V13")["informative"],
           "reading-unbounded": not gate_read(nop, pages=(page,))["informative"],
           "reading-no-page": not gate_read(proper)["informative"],
           "reading-v18-S": not gate_read(mid, zone=zmid, run_v="V18", byte475=None)["informative"],
           "reading-v18-F": gate_read(mid, "F", zmid, run_v="V18", byte475=None)["informative"],
           "stops-uninformative": v(stops + stops[:1] + [good, dict(good, side="F")])["verdict"] == "UNINFORMATIVE",
           "stop-then-witnessed": (lambda x: (x["verdict"], x["s_run"]))(v([stops[0], good, dict(good, side="F")]))
           == ("WITNESSED", 1),
           "bonus": (lambda x: (x["verdict"], x["cause"]))(v([_reading("S"), _reading("F", number=90, byte475=90)]))
           == ("BROKEN", "bonus"),
           "combo-pages": (lambda x: (x["verdict"], x["cause"]))(v([_reading("S"), _reading("F", combo=True)]))
           == ("BROKEN", "combo"),
           "combo-v18": (lambda x: (x["verdict"], x["cause"]))(v([_reading("S"), _reading("F", v18=True)]))
           == ("BROKEN", "combo"),
           "invalid": v([_reading("S", number=93, byte475=93), _reading("F")])["verdict"] == "INVALID",
           "readers-uninformative": not oob["informative"] and not unobs["informative"],
           "uninformative-S": v([oob, unobs, oob, _reading("F")])["verdict"] == "UNINFORMATIVE",
           "uninformative-F": v([_reading("S")] + [dict(x, side="F") for x in (oob, unobs, oob)])["verdict"]
           == "UNINFORMATIVE"}
    for name, odd in (("no-witness-sa2", _reading("S", sa="2")),
                      ("no-witness-engine", _reading("S", engine={"x64": "5" * 64, "x86": "5" * 64}))):
        x = v([odd, _reading("F")])
        got[name] = x["verdict"] == "UNINFORMATIVE" and len(x["no_witness"]) == 1
    return all(got.values()), str({k: v_ for k, v_ in got.items() if not v_} or "all as registered")


def unit_trace_summary(pred: dict, stock) -> tuple:
    """O4's trace_summary (7.2; rev. 2, the claim critique #14) of a base S run: the ladder 1/1, the chain 2/2, writes
    23/23, the error path, forbidden and dead sites absent, the sword rows one each, the crossing 64 ip528 -> 150 e0 t0
    ip26, the end cut's row 153 e0 t0 ip22, no unregistered key, no join failure, the three start residue rows. An F
    stage ending in member(150) (R-GATE's shape) is cut at member(150)'s first row by its end PLACES; O3's summary given
    the same end FIELDS (rev. 1's call, the unit's mutant) is not cut at all."""
    members = members_of(pred)
    t = C.trace_summary(_rows(base_events()), pred, stock=stock)
    reg = {k: (sum(1 for x in v if x["present"]), len(v)) for k, v in t["registered"].items()}
    want = {"ladder": (1, 1), "chain": (2, 2), "writes": (23, 23), "error_path": (0, 8), "forbidden_sites": (0, 2),
            "dead": (0, 19)}
    got = {"registered": reg == want,
           "sword": {k: v["count"] for k, v in t["sword"].items()} == {"score": 1, "combo": 1},
           "crossing": t["crossing"] == {"exit": "64 e2 t1 ip528 Global.Int16[2]=325",
                                         "next": "150 e0 t0 ip26 Global.Bit[191]=0"},
           "end-row": t["end_row"] == "w 153 e0 t0 ip22 Global.Bit[191]=0" and t["end_places"] == [153],
           "clean": t["unregistered"] == [] and t["failures"] == [],
           "residue": [x[1:] for x in t["residue_before"]] == [[0, 0, 131], [1, 0, 4], [2, 0, 100]]}
    m150 = next(f for f, d in members.items() if d == 150)
    frows = _rows(base_events(), "F", members)
    tf = C.trace_summary(frows, pred, side="F", end_fields=[m150], stock=stock)
    first150 = next(x.line for x in frows if x.k in ("w", "r") and x.fld == m150)
    got["f-cut-at-member"] = tf["end"] == first150 and tf["end_places"] == [150] and tf["end_row_fld"] == m150
    t3 = P.trace_summary(frows, pred, side="F", end_fields=[m150], stock=stock)
    got["o3-fields-uncut"] = t3["end"] is None
    return all(got.values()), str({k: v for k, v in got.items() if not v} or f"all as registered: {reg}")


def unit_state_history(pred: dict, stock, scripts: dict, tmp: Path, path: Path) -> tuple:
    """O4-STATE (a)'s reading of a base run: Byte[8]'s history [(64, 125), (64, 0), (150, 25), (150, 75)]; Byte[475]'s
    [(64, 0), (64, 100)]; Bit[3815]'s [(64, 0), (64, 1)]."""
    d = make_session(tmp, path, six(pred)[:1], scripts)
    run = C.O4.read_session(d, pred, stock=stock)[0]
    h = C.O4.history(run, pred)
    got = {t: [(k.donor, k.value) for k in h.get(t, [])] for t in ("Global.Byte[8]", "Global.Byte[475]",
                                                                    "Global.Bit[3815]")}
    ok = got == {"Global.Byte[8]": [(64, 125), (64, 0), (150, 25), (150, 75)],
                 "Global.Byte[475]": [(64, 0), (64, 100)], "Global.Bit[3815]": [(64, 0), (64, 1)]}
    return ok, str(got)


_LOG_HEAD = "02.10.2026 19:27:42 |M| [WindowManager] Moving window to (2045,33)\n"
_LOG_351 = ("02.10.2026 19:27:44 |W| [DataPatchers] ForkDonorPatch: donor field 351 is forked by both 30831 and 30842 "
            "-> remap DISABLED (ambiguous)\n")
_LOG_DONE = "02.10.2026 19:27:44 |M| [DataPatchers] Initialized\n"


def unit_p_donor_log() -> tuple:
    """P-DONOR-LOG over 64, 150 and 153 (O3's unit, O4's donors): today's shape (another donor's collision only) PASS;
    153 forked twice FAIL naming it; no "Initialized" FAIL."""
    a = P.p_donor_log(_LOG_HEAD + _LOG_351 + _LOG_DONE, C.ROUTE_DONORS)
    w153 = _LOG_351.replace("351", "153").replace("30831 and 30842", "31245 and 31299")
    b = P.p_donor_log(_LOG_HEAD + _LOG_351 + w153 + _LOG_DONE, C.ROUTE_DONORS)
    c = P.p_donor_log(_LOG_HEAD + _LOG_351, C.ROUTE_DONORS)
    ok = a[0] and not b[0] and "donor field 153 is forked by both 31245 and 31299" in b[1] and not c[0]
    return ok, f"today {a[0]}; 153 twice {b[0]}; no Initialized {c[0]}"


def _touch(p: Path, when: _dt.datetime) -> None:
    ts = when.timestamp()
    os.utime(p, (ts, ts))


def unit_p_launch(tmp: Path) -> tuple:
    """P-LAUNCH with the engine (O3's unit, O4's files; rev. 2): every patch file, Memoria.ini and both engine DLLs
    older than the launch, the DLLs the pinned engine: PASS; a ForkDonorPatch.txt holding the route rows touched after
    the launch FAIL naming it ("relaunch"); an engine DLL touched after the launch FAIL ("relaunch"); a live engine
    other than the pinned one FAIL; no stamp FAIL."""
    launched = P.launch_time(_LOG_HEAD + _LOG_DONE)
    game = tmp / "plaunch4"
    root = game / "FF9CustomMap"
    root.mkdir(parents=True)
    old = _dt.datetime(2026, 10, 2, 19, 27, 4)
    files = {game / "Memoria.ini": "[Battle]\nSpeed = 5\n", root / "DictionaryPatch.txt": "FieldScene 31240 11 X X 2\n",
             root / "ForkDonorPatch.txt": "31240 64\n31243 150\n31245 153\n"}
    for arch in ("x64", "x86"):
        files[game / arch / "FF9_Data" / "Managed" / "Assembly-CSharp.dll"] = "dll"
    for p, text in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        _touch(p, old)
    pinned = {"x64": C.ENGINE["x64"], "x86": C.ENGINE["x86"]}

    def check(live=pinned, stamp=launched):
        return C.launch_engine_check(P.launch_files(game, [root]), C.engine_files(game), stamp, live, C.ENGINE)
    got = {"older": check()[0]}
    fdp = root / "ForkDonorPatch.txt"
    _touch(fdp, _dt.datetime(2026, 10, 2, 19, 27, 50))
    ok, d = check()
    got["fdp-after"] = (not ok) and "ForkDonorPatch.txt" in d and "relaunch" in d
    _touch(fdp, old)
    dll = game / "x64" / "FF9_Data" / "Managed" / "Assembly-CSharp.dll"
    _touch(dll, _dt.datetime(2026, 10, 2, 19, 28))
    ok, d = check()
    got["dll-after"] = (not ok) and "Assembly-CSharp.dll" in d and "relaunch" in d
    _touch(dll, old)
    got["other-engine"] = not check(live={"x64": "6" * 64, "x86": "6" * 64})[0]
    got["no-stamp"] = not check(stamp=None)[0]
    got["older-again"] = check()[0]
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def _pad(**over) -> dict:
    return {"buttons": 0, "lt": 0, "rt": 0, "lx": 0, "ly": 0, "rx": 0, "ry": 0, **over}


def unit_p_pad() -> tuple:
    """P-PAD (6.2) over a stub reader: no pad PASS; an idle pad at slot 2 PASS with the WARN line; a pressed A FAIL; a
    trigger at 40 FAIL; a thumb at 4000 FAIL; no XInput runtime PASS."""
    def pad(slots):
        return C.p_pad(C.xinput_slots(lambda slot: slots.get(slot), sleep=lambda s: None))
    ok2, d2 = pad({2: _pad()})
    got = {"none": pad({})[0], "idle-2": ok2 and d2.startswith("WARN: an XInput pad is connected at slot 2"),
           "A": not pad({0: _pad(buttons=0x1000)})[0], "trigger": not pad({1: _pad(lt=40)})[0],
           "thumb": not pad({3: _pad(ry=4000)})[0], "no-runtime": C.p_pad(C.xinput_slots(None))[0]}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_p_override() -> tuple:
    """P-OVERRIDE (6.2): the pinned sha PASS; another sha, two folders shipping field 70, none: FAIL each."""
    pinned = dict(C.OVERRIDE70)
    sha = pinned["FF9CustomMap-world"]
    got = {"pinned": C.p_override(dict(pinned), pinned)[0],
           "other": not C.p_override({"FF9CustomMap-world": "7" * 64}, pinned)[0],
           "two": not C.p_override({"FF9CustomMap-world": sha, "FF9CustomMap": sha}, pinned)[0],
           "none": not C.p_override({}, pinned)[0]}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_p_settings(tmp: Path) -> tuple:
    """P-SETTINGS (6.2): an ini equal to 4.13 PASS; SwordplayAssistance 2, FieldTPS 60, SwapConfirmCancel 1,
    AlwaysCaptureGamepad 0 each FAIL naming the key; a later duplicate assignment wins."""
    want = C.SETTINGS
    game = tmp / "psettings4"
    game.mkdir()

    def judge(settings, extra=""):
        lines = []
        for sec, kv in settings.items():
            lines += [f"[{sec}]"] + [f"{k} = {v}" for k, v in kv.items()] + [""]
        (game / "Memoria.ini").write_text("\n".join(lines) + extra, encoding="utf-8")
        return P.p_settings(want, P.install_settings(game, [], want))

    def one(sec, key, value):
        s = json.loads(json.dumps(want))
        s[sec][key] = value
        ok, detail = judge(s)
        return (not ok) and f"[{sec}] {key} = '{value}'" in detail
    got = {"equal": judge(want)[0], "sa2": one("Hacks", "SwordplayAssistance", "2"),
           "tps60": one("Graphics", "FieldTPS", "60"), "swap": one("Control", "SwapConfirmCancel", "1"),
           "capture0": one("Control", "AlwaysCaptureGamepad", "0"),
           "later-wins": (not judge(want, "\n[Hacks]\nSwordplayAssistance = 2\n")[0])}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_p_gate(tmp: Path) -> tuple:
    """P-GATE (6.2; rev. 2): no gate_witness, UNINFORMATIVE, INVALID, a missing run dir, BROKEN with cause combo, an
    engine other than the live DLLs', settings with SwordplayAssistance 2 FAIL each; WITNESSED, or BROKEN with cause
    bonus, with its run dir, the live engine and 4.13's settings PASS -- the detail opening with the verdict."""
    eng = {"x64": C.ENGINE["x64"], "x86": C.ENGINE["x86"]}
    run_dir = tmp / "rgate"
    run_dir.mkdir(exist_ok=True)
    base = {"run_dir": str(run_dir), "verdict": "WITNESSED", "cause": None, "engine": dict(eng),
            "settings": json.loads(json.dumps(C.SETTINGS)), "s_run": 0, "f_run": 1, "detail": "both 100"}
    sa2 = json.loads(json.dumps(C.SETTINGS))
    sa2["Hacks"]["SwordplayAssistance"] = "2"

    def gate(**over):
        return C.p_gate({"gate_witness": {**base, **over}}, eng, C.SETTINGS)
    ok, detail = gate()
    got = {"witnessed": ok and detail.startswith("R-GATE WITNESSED (cause none)"),
           "bonus": gate(verdict="BROKEN", cause="bonus")[0],
           "none": not C.p_gate({"gate_witness": None}, eng, C.SETTINGS)[0],
           "uninformative": not gate(verdict="UNINFORMATIVE")[0], "invalid": not gate(verdict="INVALID")[0],
           "no-dir": not gate(run_dir=str(tmp / "nowhere"))[0],
           "combo": not gate(verdict="BROKEN", cause="combo")[0],
           "engine": not gate(engine={"x64": "8" * 64, "x86": "8" * 64})[0], "sa2": not gate(settings=sa2)[0]}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_p_engine() -> tuple:
    """P-ENGINE (6.2; rev. 2): the pinned sha on both DLLs PASS; another sha, or x86 differing from x64, FAIL each."""
    eng = {"x64": C.ENGINE["x64"], "x86": C.ENGINE["x86"]}
    got = {"pinned": C.p_engine(dict(eng), C.ENGINE)[0],
           "other": not C.p_engine({"x64": "9" * 64, "x86": "9" * 64}, C.ENGINE)[0],
           "x86-differs": not C.p_engine(dict(eng, x86="a" * 64), C.ENGINE)[0]}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_text_strict() -> tuple:
    """strict_text and P-TEXT (6.1, 6.2; rev. 2, the claim critique #12): block 3's uk equal to stock us -- text_rule
    alone reads it a KNOWN-KIT-DEFECT and passes, strict_text FAILS; P-TEXT on block 2 with O1's copy (its shas
    o1_block2) and no O4 member registered PASS with the named line; the same copy with an O4 member registered FAIL;
    another defect copy before the deploy FAIL."""
    langs = ("us", "uk", "fr", "gr", "it", "es", "jp")
    stock = {L: f"stock {L}".encode() for L in langs}
    defect = dict(stock, uk=stock["us"])
    ok, lines = A.text_rule(stock, defect, "us")
    o1 = {L: C._sha(b) for L, b in defect.items()}
    a = C.p_text(2, [("FF9CustomMap", defect)], stock, o1_block2=o1, o4_registered=False)
    got = {"rule-passes": ok, "strict-fails": not C.strict_text(lines)[0],
           "o1-before": a[0] and "KNOWN-KIT-DEFECT uk: ships stock us" in a[1],
           "o1-after": not C.p_text(2, [("FF9CustomMap", defect)], stock, o1_block2=o1, o4_registered=True)[0],
           "other-before": not C.p_text(2, [("FF9CustomMap", dict(stock, fr=stock["it"]))], stock, o1_block2=o1,
                                        o4_registered=False)[0]}
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_input_witness() -> tuple:
    """The input witness's readers (2.4.3 step 0; rev. 2): neutral pads and no key read None; a pad button at slot 1, a
    trigger at 40, a thumb at 4000 read non-neutral; a key down with the game focused non-neutral, unfocused neutral;
    F1 focused non-neutral; a slot found disconnected polled at most once a second."""
    pads, keys, focus, clock, calls = {}, {"down": []}, {"on": False}, {"t": 100.0}, []

    def reader(slot):
        calls.append(slot)
        return pads.get(slot)
    w_ = C.input_witness(None, pads=reader, keys=lambda: keys["down"], focus=lambda: focus["on"],
                         clock=lambda: clock["t"])
    got = {"neutral": w_() is None and calls == [0, 1, 2, 3]}
    clock["t"] = 100.5
    got["once-a-second"] = w_() is None and calls == [0, 1, 2, 3]
    clock["t"] = 101.0
    pads[1] = _pad(buttons=0x2000)
    got["button"] = w_() == "XInput slot 1: buttons 0x2000"
    pads[1] = _pad(rt=40)
    got["trigger"] = "trigger rt 40" in (w_() or "")
    pads[1] = _pad(lx=4000)
    got["thumb"] = "thumb lx 4000" in (w_() or "")
    pads[1] = _pad()
    keys["down"] = [0x41]
    got["unfocused"] = w_() is None
    focus["on"] = True
    got["focused"] = w_() == "key(s) down while the game has focus: 0x41"
    keys["down"] = [0x70]
    got["f1"] = w_() == "key(s) down while the game has focus: 0x70"
    return all(got.values()), str({k: v for k, v in got.items() if not v} or "all as registered")


def unit_store_census(pred: dict, stock) -> list:
    """O4-CENSUS on the install PASSES with 6.1's line; each mutant FAILS naming the site: ``dead`` without 64 ip41;
    ``inert`` without 23; ``error_path`` without 150 ip1009; an ``inert`` entry 3 (instanced at 325: the proof
    fails)."""
    out = []
    ok, _w, detail = C.O4.census_check(pred, stock)
    want = ("64: 25, 150: 273 store sites -- all classified (writes 10/13, ladder 0/1, chain 1/1, masked 2/2 (64's ip22 "
            "is start_first), error_path 4/4, forbidden 0/2, dead 8/11, inert 0/239); 0 unresolved; inert 10, 15, 16, "
            "19, 23 not instanced at 325")
    out.append(("store-census", ok is True and detail == want, detail[:150]))

    def without(name, test):
        def mutate(p):
            p[name] = [k for k in p[name] if not test(k)]
        return mutate
    muts = [("census-dead-64-41", without("dead", lambda k: (k["donor"], k["ip"]) == (64, 41)),
             "64 e0 t0 ip41 Global.Int16[2]: in no list"),
            ("census-inert-23", without("inert", lambda k: k["sid"] == 23), "150 e23 t"),
            ("census-error-150-1009", without("error_path", lambda k: (k["donor"], k["ip"]) == (150, 1009)),
             "150 e0 t0 ip1009 Global.Byte[13]: in no list"),
            ("census-inert-3", lambda p: p["inert"].append({"donor": 150, "sid": 3, "tags": "*", "why": "a mutant"}),
             "inert entry 3 of 150 is instanced at entrance 325")]
    for name, mutate, clause in muts:
        p = copy.deepcopy(pred)
        mutate(p)
        ok, _w, detail = C.O4.census_check(p, stock)
        out.append((name, ok is False and clause in detail, f"{'FAIL' if ok is False else 'PASS'}: {detail[:150]}"))
    return out


def _operand(ins, i: int) -> int:
    """The absolute offset of immediate operand ``i`` of a decoded instruction: after the op and the flags byte, each
    operand at its width (disasm.argsize)."""
    from ff9mapkit.eb.disasm import argsize
    return ins.off + 2 + sum(argsize(ins.op, j) for j in range(i))


def unit_build_pins(pred: dict, tmp: Path) -> list:
    """O4-BUILD's fork-gate pins (6.1) on a synthetic route build through a ``stock_lang`` seam -- members 31240 (64),
    31243 (150) and 31245 (153), every language its own stock donor remapped by content.verbatim.remap_fields. Three
    members, not the design's two: the pinned in-chain sites retarget Field(153), so 153 must be in the chain. The
    clean build PASSES; each mutant FAILS by the pins' clause: an extra byte changed in member(64)'s e4 t1 inside the
    score-to-store range (jp); a PreloadField operand remapped (64 e2 t1 ip426's 150 -> 31243, fr); an in-chain
    Field() left unremapped (member(64) e11 t2 ip201's Field(153), us)."""
    from ff9mapkit.config import LANGS, ModLayout
    from ff9mapkit.content.verbatim import remap_fields
    from ff9mapkit.eb import EbScript
    real = ST.stock_lang()
    cache: dict = {}

    def stock_lang(fid, lang):
        if (fid, lang) not in cache:
            cache[(fid, lang)] = real(fid, lang)
        return cache[(fid, lang)]
    members = {31240: 64, 31243: 150, 31245: 153}
    names = {31240: "O4_BP_STANDS", 31243: "O4_BP_HALL", 31245: "O4_BP_END"}
    sub = dict(pred, members={str(f): d for f, d in members.items()}, names={str(f): n for f, n in names.items()})
    retarget = {d: f for f, d in members.items()}

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

    def flip_score(fid, L, data):
        if fid == 31240 and L == "jp":
            ins = instr(64, L, 4, 1, 222)
            data[ins.off + 3] ^= 0x01

    def remap_preload(fid, L, data):
        if fid == 31240 and L == "fr":
            ins = instr(64, L, 2, 1, 426)
            assert ins.imm(1) == 150, ins
            o = _operand(ins, 1)
            data[o:o + 2] = (31243).to_bytes(2, "little")

    def unremap(fid, L, data):
        if fid == 31240 and L == "us":
            ins = instr(64, L, 11, 2, 201)
            assert ins.imm(0) == 153, ins
            data[ins.off + 2:ins.off + 4] = (153).to_bytes(2, "little")
    out = []
    ok, _w, detail = C.O4.build_check(sub, build("bp-clean"), stock_lang=stock_lang)
    out.append(("build-pins-clean", ok is True and "the only byte diffs the six in-chain Field() operands" in detail,
                detail[:150]))
    for name, mutate, clause in (("build-pins-score-byte", flip_score, "the score-to-store bytes differ"),
                                 ("build-pins-preload", remap_preload, "differ outside the in-chain Field() operands"),
                                 ("build-pins-unremapped", unremap, "left unremapped")):
        ok, _w, detail = C.O4.build_check(sub, build(name, mutate), stock_lang=stock_lang)
        at = detail.find(clause)
        out.append((name, ok is False and at >= 0,
                    f"{'FAIL' if ok is False else 'PASS'}: " + (detail[max(0, at - 60):at + 90] if at >= 0
                                                                else detail[:150])))
    return out


def unit_fight_pins(pred: dict, stock) -> list:
    """O4-KEYS (b), the fight pins (4.14): on the install PASS; a pin's text changed (``const(51)`` for TimeLeft)
    FAIL; ``prompt_mes`` 118 -> "CROSS" FAIL."""
    out = []
    ok, detail = C.O4.fight_pins_check(pred, stock)
    out.append(("fight-pins", ok is True and detail.startswith("56 fight pins equal"), detail[:150]))
    p = copy.deepcopy(pred)
    pin = next(x for x in p["fight"]["pins"] if x[:4] == [64, 20, 1, 736])
    pin[4] = pin[4].replace("const(50)", "const(51)")
    ok, detail = C.O4.fight_pins_check(p, stock)
    out.append(("fight-pins-timeleft", ok is False and "64 e20 t1 ip736" in detail, detail[:150]))
    p = copy.deepcopy(pred)
    p["fight"]["prompt_mes"]["118"] = "CROSS"
    ok, detail = C.O4.fight_pins_check(p, stock)
    out.append(("fight-pins-mes-118", ok is False and "mes 118: prompt_dbtn reads 'CIRCLE', pinned 'CROSS'" in detail,
                detail[:150]))
    return out


def _key(p: dict, name: str, donor: int, ip: int) -> dict:
    return next(k for k in p[name] if (k["donor"], k["ip"]) == (donor, ip))


#: O4-KEYS's offline mutants (section 8): the DRAFT, deep-copied, one thing changed; the check must then read FAIL --
#: after it has read PASS on the unchanged draft -- and its detail hold the clause.
OFFLINE_MUTANTS = [
    ("keys-write-value", lambda p: _key(p, "writes", 150, 1136).update(value=2), "the bytes give 1, the key says 2"),
    ("keys-prior-unknown", lambda p: _key(p, "writes", 150, 1255).update(prior="150/3/1/9999"),
     "names no registered prior"),
    ("keys-var-rvalue", lambda p: _key(p, "writes", 64, 338).update(rvalue="Map.Int16[47]"),
     "the statement is not Global.Byte[475] := Map.Int16[47]"),
    ("keys-chain-off", lambda p: p["chain"][0].update(off=518), "chain: FieldEntrance 325: 64 stage 9"),
    ("keys-start-first-target", lambda p: p["start_first"].update(target="Global.Bit[192]"),
     "start_first: 64's Main_Init: its first store"),
    ("keys-dead-value", lambda p: _key(p, "dead", 64, 130).update(value=2), "the bytes give 1, the key says 2"),
    ("keys-start-music", lambda p: p["start_music"].update(ip=138, off=132), "is 0 writes keys, not one"),
]


def unit_offline_mutants(pred: dict, stock) -> list:
    """``[(name, ok, detail)]``: O4-KEYS reads PASS on the draft, then FAILS on each of :data:`OFFLINE_MUTANTS` by its
    clause."""
    base = C.O4.keys_check(pred, stock)
    out = [("offline-draft-passes", base[0] is True, base[2][:120])]
    for name, mutate, clause in OFFLINE_MUTANTS:
        p = copy.deepcopy(pred)
        mutate(p)
        ok, _what, detail = C.O4.keys_check(p, stock)
        caught = ok is False and clause in detail
        out.append((name, caught, f"KEYS {'FAIL' if ok is False else 'PASS (not caught)'}"
                                  + ("" if caught or ok is not False else f" -- not by {clause!r}") + f": {detail[:120]}"))
    return out


def block2_us() -> dict:
    """Block 2's US messages as the engine reads them (``{mes id: source}``)."""
    from ff9mapkit import dialogue
    body = A.stock_text_assets(2)["us"]
    body = body.decode("utf-8", errors="replace") if isinstance(body, (bytes, bytearray)) else str(body)
    return {i: x.text for i, x in dialogue.parse_mes(body).items()}


def units(pred: dict, stock, scripts: dict, sdir: Path, path: Path, tmp: Path) -> list:
    """Every single unit, in order: ``[(name, fn)]``, each ``fn()`` -> ``(ok, detail)``."""
    mes = block2_us()
    return [("chanbara-policy", lambda: unit_chanbara_policy(pred)),
            ("prompt-shape", lambda: unit_prompt_shape(pred, mes)),
            ("j-bounds", unit_j_bounds),
            ("judge", lambda: unit_judge(pred)),
            ("slides", unit_slides),
            ("stray-answer", unit_stray_answer),
            ("gate-verdict", lambda: unit_gate_verdict(pred)),
            ("trace-summary", lambda: unit_trace_summary(pred, stock)),
            ("state-history", lambda: unit_state_history(pred, stock, scripts, sdir, path)),
            ("p-donor-log", unit_p_donor_log),
            ("p-launch", lambda: unit_p_launch(tmp)),
            ("p-pad", unit_p_pad),
            ("p-override", unit_p_override),
            ("p-settings", lambda: unit_p_settings(tmp)),
            ("p-gate", lambda: unit_p_gate(tmp)),
            ("p-engine", unit_p_engine),
            ("text-strict", unit_text_strict),
            ("input-witness", unit_input_witness)]


def listed_units(pred: dict, stock, tmp: Path) -> list:
    return (unit_store_census(pred, stock) + unit_build_pins(pred, tmp) + unit_fight_pins(pred, stock)
            + unit_offline_mutants(pred, stock))


# ======================================================================== the run
def prepare(pred_path: Path | None, tmp: Path) -> tuple:
    """``(path, what)``: the predictions the run reads -- ``pred_path``; else the frozen file once it exists; else the
    DRAFT, written to a temporary file."""
    if pred_path is not None:
        return Path(pred_path), f"the file {Path(pred_path).name}"
    if C.PREDICTIONS.is_file():
        return C.PREDICTIONS, f"the frozen {C.PREDICTIONS.name}"
    path = tmp / "o4_predictions_draft.json"
    path.write_bytes((json.dumps(C.draft_predictions(), indent=1, sort_keys=True) + "\n").encode("utf-8"))
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
        path, what = prepare(pred_path, pdir)
        print(f"predictions: {what}")
        pred, _sha = C.O4.load(path)
        members = members_of(pred)
        retarget = {dn: f for f, dn in members.items()}
        scripts = {fid: remap_fields(stock(dn).data, retarget) for fid, dn in members.items()}
        for name, fn, want_verdict, want, clauses, report_has, want_void, want_cov in CASES:
            total += 1
            d = make_session(sdir, path, fn(copy.deepcopy(pred)), scripts)
            checks, report = C.O4.analyse(d, stock=stock)
            got, det = result(checks), details(checks)
            v = verdict(checks)
            miss = [f"{k} {_mark(got.get(k))}, want {_mark(x)}" for k, x in want.items() if got.get(k) is not x]
            miss += [f"check {k} not registered" for k in got if k not in want]
            if not v.startswith(want_verdict):
                miss.append(f"verdict {v!r}, want {want_verdict}")
            miss += _clauses_named(clauses, det)
            miss += [f"report lacks {s!r}" for s in report_has if s not in report]
            runs = C.O4.read_session(d, pred, stock=stock) if (want_void or want_cov) else []
            for i, classes in want_void.items():
                have = {x["class"] for x in runs[i - 1]["void"]}
                if not set(classes) <= have:
                    miss.append(f"run {i} VOID classes {sorted(have)}, want {classes}")
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
        # O4-FROZEN: the predictions changed after the session recorded them
        total += 1
        copy_path = pdir / "pred_copy.json"
        copy_path.write_bytes(path.read_bytes())
        d = make_session(sdir, copy_path, six(pred), scripts)
        copy_path.write_bytes(path.read_bytes() + b" ")
        checks, _rep = C.O4.analyse(d, stock=stock)
        v = verdict(checks)
        got = result(checks)
        ok = got.get("O4-FROZEN") is False and v.startswith("NOT PROVEN") and all(
            got.get(k) is True for k in CHECKS if k != "O4-FROZEN")
        fails += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {'predictions-changed':34} {v[:44]}")
        for name, fn in units(pred, stock, scripts, sdir, path, tmp):
            total += 1
            ok, detail = fn()
            fails += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name:34} (unit) {detail[:150]}")
        for name, ok, detail in listed_units(pred, stock, tmp):
            total += 1
            fails += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name:34} (unit) {detail[:150]}")
    print(f"\n{total - fails}/{total} cases as registered")
    return 1 if fails else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--predictions", type=Path, default=None,
                    help="a predictions file (default: the frozen o4_predictions_v1.json once it exists, else the "
                         "draft, written to a temporary file)")
    sys.exit(run_cases(ap.parse_args().predictions))
