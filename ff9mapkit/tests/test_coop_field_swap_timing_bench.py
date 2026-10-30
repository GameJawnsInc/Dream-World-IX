"""[ff9mapkit netsync s164] THE FIELD-SWAP TIMING BENCHES' REPO HALF -- studies/test-harness/scenarios/coop_field_swap_timing.py (the
SOLO bench, the selftest role). The duo's half (coop_field_swap_timing_duo.py) is added beside these by its own part.

s164 (studies/field-coop/SWAP-TIMING-S164.md rev 3) is five items in one engine round behind one lever scheme (`netsync swap`): A the
instrument (QPC swap stamps, one swap record per transition), B Finding 11's orphan hold, C the guest's own Field() passing on the host's
announced field, PIN and LIFE, D+E the fade-aware follow. These tests pin, offline, with fixtures in the ENGINE's log and state shapes:

  * every solo judge can go red on each of its parts. The fixtures are built by battlewire's twins: B's sample streams come out of KIT-1's
    orphan stepper (battlewire.swap_orphan_window_tick) on its settle clock (DialogSettleClock), the F streams out of the D+E rules
    (fade_path_rule / fade_action_rule / fade_black_ticks_rule / fade_due_rule / fade_reassert_rule), C's verdicts out of
    own_field_pass_rule, P's out of pin_use_rule, L's out of intent_landing_step / intent_life_rule, and every log line out of
    battlewire's builders;
  * each solo calibration word reds EXACTLY its registered rows offline, each with its marker, and every other row stays green (the
    lever's evidence comes out of the same twins with the lever set);
  * the solo bench refuses an unknown COOP_CALIBRATE word (and an unknown COOP_LEGS leg, and a word whose rows the legs leave out) AT
    LOAD, before a game boots;
  * K-CLOCK's three outcomes: GREEN on the stand-in's clock seam, UNFIT (cross-game rows VOID) on `src stopwatch`, SKIP with its reason
    when the kit's qpc_ms() is None -- never a ledger row;
  * the whole solo bench runs green on the stand-in with COOP_LEGS=KAB (the legs it models; a C, P, L or F leg there proves nothing,
    P8), and the stamps / delay / orphan calibrations calibrate exactly there too;
  * the source tests: literals the engine build must keep (R8, R9, I2, V1, V3, G2, P8). They read the captured s164 patch under
    memoria-patches/ (s163's precedent); with no s164 patch on the stack yet they SKIP with that reason, and with one they FAIL on a
    missing literal -- re-run them after the engine build.

Every scenario-touching test runs in a CHILD process (the scenario puts its own dir on sys.path -- never this process's).
"""
import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCEN = REPO / "studies" / "test-harness" / "scenarios"
PATCHES = REPO / "memoria-patches"


def _run_child(code: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    full = ("import json, os, sys\nsys.path.insert(0, %r)\nsys.path.insert(0, %r)\n" % (str(SCEN), str(REPO / "tools"))
            + "import coop_field_swap_timing as so\nfrom harness import battlewire as BW\nfrom harness import fakegame as FG\n" + code
            + "\nprint('@@' + json.dumps(OUT))\n")
    env = {k: v for k, v in os.environ.items() if k not in ("COOP_CALIBRATE", "COOP_LEGS")}
    env.update(env_extra or {})
    # the script rides STDIN (`-`), not `-c`: a few children sit near Windows' 32767-character command line (WinError 206)
    return subprocess.run([sys.executable, "-X", "utf8", "-"], input=full, capture_output=True, text=True, cwd=str(SCEN), timeout=180,
                          env=env)


def _child(code: str, env_extra: dict | None = None) -> dict:
    r = _run_child(code, env_extra)
    assert r.returncode == 0, r.stderr[-3000:]
    line = next(ln for ln in r.stdout.splitlines() if ln.startswith("@@"))
    return json.loads(line[2:])


# ------------------------------------------------------------------------------------------------ the fixtures (in the child)
_FIX = r'''
import copy
P = "29.10.2026 21:10:00 |M| "
L = lambda text: P + text
SENT = FG.NETSYNC_SWAP_SENTINELS
HM, AW = so.HOME, so.AWAY
DT = 33


def _put(d, dotted, v):
    ks = dotted.split(".")
    for k in ks[:-1]:
        d = d[k]
    d[ks[-1]] = v


def S(t=0, frame=None, field=None, ctl=True, wins=(), closes=0, settled=-1, hf=-1, flags=None, mirror=None, party=None, pending=-1,
      sw=None, src="qpc", utc=None):
    """A state sample in the engine's shape: `netsync.swap` at the catch line's sentinels plus ``sw`` (dotted keys)."""
    b = copy.deepcopy(SENT)
    b["clock"].update(now_ms=t, utc_ms=t if utc is None else utc, ticks=t * 10000, hz=10000000, src=src, hires=True, fps=30,
                      target_fps=-1)
    for k, v in (sw or {}).items():
        _put(b, k, v)
    return {"_t": t / 1000.0, "frame": t // DT if frame is None else frame, "field": {"id": HM if field is None else field},
            "player": {"control": ctl}, "flags": {} if flags is None else {str(so.P_FLAG): flags},
            "netsync": {"windows": [{"win": w, "text": x, "cls": c} for (w, x, c) in wins], "orphan_closes": closes,
                        "host_settled_ms": settled, "host_flags": hf, "session": {"follow": {"pending": pending}},
                        "dress": {"party": list(party or [0, -1, -1, -1]), "mirror_party": mirror}, "swap": b}}


def ed(s, sw=None, ns=None, top=None):
    s = copy.deepcopy(s)
    for k, v in (sw or {}).items():
        _put(s["netsync"]["swap"], k, v)
    for k, v in (ns or {}).items():
        _put(s["netsync"], k, v)
    for k, v in (top or {}).items():
        _put(s, k, v)
    return s


def rec(**kw):
    r = copy.deepcopy(SENT["last"])
    r.update(kw)
    return r


def block(**kw):
    b = copy.deepcopy(SENT)
    for k, v in kw.items():
        _put(b, k.replace("__", "."), v)
    return b


def stamp(line):
    return so.stamp_of(line)


# ---- K
PROOF = L("[NetSync] " + BW.swap_proof_text(425, 146, "qpc", 10000000, True))
DLG_OK = L("[NetSync] dialogue authority selftest: OK (98 rows)")
REFUSE = {"delay": "the game refused a step: " + BW.SWAP_USAGE, "word": BW.SWAP_USAGE,
          "bench": "the game refused a step: netsync: " + BW.swap_refusal_bench("intent") + " (steps=[...])",
          "off": "the game refused a step: netsync: " + BW.SWAP_REFUSAL_COOP_OFF}
REST = {"stamps": None, "delay_ms": 0, "orphan": None, "own": None, "pin": None, "life": None, "fade": None, "hostctl_off": False}


def lever_steps():
    out, lv = [], dict(REST)
    for op, w in so.K_LEVER_SEQ:
        key, vals = so.lever_want(op, w)
        lv = dict(lv, **{key: vals[0]})
        out.append({"op": op, "word": w, "ok": True, "why": "", "lines": [L(so.lever_line(op, w))], "levers": dict(lv)})
    return out


CLEAR = [L(BW.swap_harness_clear(False))]
RELEASE = [L(BW.swap_harness_release(False))]
K_REC = rec(id=1, due_t=5000, commit_t=5000, delay_ms=0, follow_t=4100)


def k_rows():
    return {"K-PROOF": so.judge_proof([PROOF, DLG_OK], "ok"), "K-REFUSE": so.judge_refuse(REFUSE),
            "K-LEVER": so.judge_levers(lever_steps(), REST, CLEAR), "K-RELEASE": so.judge_release(RELEASE, REST, [], K_REC, 33.0)}


# ---- A
REC1 = rec(id=2, role="guest", dest=AW, state="done", open_by="seen", open_t=1000, nonce=1, seen_t=1000, seen_copies=1, follow_t=1001,
           follow_via="intent", follows=1, due_t=1300, commit_t=1300, commit_field=AW, commit_why="black", delay_ms=0, land_t=1340,
           land_field=AW, land_via="follow", close_t=11340, close_why="window", **{"from": HM})
REC2 = dict(REC1, id=3, open_t=40000, seen_t=40000, follow_t=40001, due_t=40300, commit_t=40600, delay_ms=300, land_t=40640,
            close_t=50640)


def a_lines(r, on=True):
    k = r["id"]
    rel = lambda t: t - r["open_t"] if t >= 0 else -1
    edges = {"seen": rel(r["seen_t"]), "follow": rel(r["follow_t"]), "own": -1, "due": rel(r["due_t"]), "commit": rel(r["commit_t"]),
             "landed": rel(r["land_t"]), "first line": -1}
    out = [L(BW.swap_harness_intent(AW, r["nonce"])), L(FG.SWAP_INTENT_BENCH_FABRICATED.format(field=AW, nonce=r["nonce"])),
           L(f"[NetSync] intent: following the peer to field {AW} (parallel)" + BW.swap_stamp_text(on, r["follow_t"]))]
    for x in (BW.swap_log_commit(on, AW, r["commit_t"] - r["follow_t"], r["commit_why"], r["delay_ms"], k, r["commit_t"]),
              BW.swap_log_landed(on, AW, BW.SWAP_VIA_FOLLOW, k, r["land_t"]),
              BW.swap_log_closed_guest(on, k, AW, HM, BW.SWAP_CLOSE_WINDOW, BW.SWAP_VIA_FOLLOW, edges, "seen", 1, 0, 0, r["close_t"])):
        if x is not None:
            out.append(L(x))
    return out


def a_rows(word=None):
    on = word != "stamps"
    lines1 = a_lines(REC1, on)
    rec2 = dict(REC2, commit_t=REC2["due_t"], delay_ms=0) if word == "delay" else REC2
    rows = {"A-FOLLOW": so.judge_follow(REC1, 1), "A-STAMP": so.judge_stamp(lines1, REC1), "A-DELAY": so.judge_delay(REC1, rec2, 33.0, 300),
            "A-WORD": so.judge_word(lines1)}
    return rows, {"A-STAMP": {"lines": lines1, "rec": REC1}, "A-DELAY": {"rec": rec2, "frame": 33.0}}


# ---- B: KIT-1's orphan stepper on the settle clock, one window per line
def bsim(key, events, T, old=False, base=None, rules=None):
    """One relayed line from t 0 under hostscene 1 with the bench host's control on; ``events`` [(t, "scene"|"ctl"|"adv", v)].
    -> (samples, lines, the counters at the end). Each tick (DT ms): the settle clock, the bench host's section 7, then the window's s164
    step (battlewire.swap_orphan_window_tick) and its lines as NetSyncDialog prints them (stamped)."""
    base = dict(base or {"closes": 0, "holds": 0, "relocks": 0})
    clock = BW.DialogSettleClock()
    w = BW.swap_orphan_window(BW.DIALOG_CLS_LOCKED, 0, 0)
    present, scene, ctl_on, adv = True, True, True, False
    closes, last_ms, last_end, seq = base["closes"], -1, None, 40
    names = {BW.DIALOG_CLS_LOCKED: "locked", BW.DIALOG_CLS_ORPHANED: "orphaned", BW.DIALOG_CLS_LOCAL: "local"}
    ev = sorted(events)
    head = f"[NetSync] dialogue orphan: win {key[0]} text {key[1]}"
    samples, lines = [], []
    for now in range(0, T + 1, DT):
        while ev and ev[0][0] <= now:
            _t, kind, v = ev.pop(0)
            if kind == "scene":
                scene = bool(v)
            elif kind == "ctl":
                ctl_on = bool(v)
            else:
                adv = True
        clock.step(not scene, False, True, False, False, now)
        holds_in = not ctl_on
        st = lambda text: L(BW.swap_place_stamp(text, True, now))
        if present:
            h0 = w["holds"]
            if adv:
                out = BW.swap_orphan_window_tick(w, settled_long=clock.long, host_holds=holds_in, now=now, lever_old=old, present=False,
                                                 rules=rules)
                present = False
                lines.append(st(f"[NetSync] dialogue: win {key[0]} text {key[1]} closed (host seq {seq})"))
            else:
                out = BW.swap_orphan_window_tick(w, settled_long=clock.long, host_holds=holds_in, now=now, lever_old=old, rules=rules)
            if w["holds"] > h0:
                lines.append(L(BW.swap_log_orphan_hold(True, key[0], key[1], now)))
            if out["end"] != BW.SWAP_HOLD_END_NONE:
                last_ms, last_end = out["held_ms"], BW.SWAP_HOLD_END_NAMES[out["end"]]
                lines.append(L(BW.swap_log_orphan_hold_end(True, key[0], key[1], out["held_ms"], out["end"], now)))
            act = out["act"]
            if present and act == BW.DIALOG_ORPH_TO_ORPHANED:
                lines.append(st(f"{head} is not on the host's screen (host idle {clock.settled_ms // 1000}s) -- closing it at reading pace"))
            elif present and act == BW.DIALOG_ORPH_TO_LOCKED and out["kind"] == BW.SWAP_CTL_RELOCK:
                lines.append(L(BW.swap_log_orphan_hold(True, key[0], key[1], now)))
            elif present and act == BW.DIALOG_ORPH_CONFIRM:
                present = False
                closes += 1
                lines.append(st(f"{head} auto-closed (host idle {clock.settled_ms // 1000}s, choice -1)"))
        hf = 8 | (1 if scene else 0) | (2 if ctl_on else 0)
        samples.append(S(now, wins=[(key[0], key[1], names[w["cls"]])] if present else [], closes=closes, settled=clock.settled_ms, hf=hf,
                         ctl=not present,
                         sw={"orphan.host_holds": holds_in, "orphan.holding": 1 if present and w["ctl_held"] else 0,
                             "orphan.holds": base["holds"] + w["holds"], "orphan.relocks": base["relocks"] + w["relocks"],
                             "orphan.last_hold_ms": last_ms, "orphan.last_end": last_end, "levers.hostctl_off": not ctl_on,
                             "levers.orphan": "old" if old else None}))
    return samples, lines, so.bcount(samples[-1])


def span(samples, lines, t0, t1=10 ** 9):
    return ([s for s in samples if t0 <= so.now_ms(s) < t1], [ln for ln in lines if t0 <= stamp(ln) < t1])


def before(samples, t):
    return [s for s in samples if so.now_ms(s) < t][-1]


K1, K2, K3, K4 = (3, 21), (3, 22), (3, 23), (3, 24)
ON1 = 6200
B1_EV = [(100, "ctl", 0), (200, "scene", 0), (ON1, "ctl", 1)]
B2_EV = [(100, "ctl", 0), (200, "scene", 0), (2700, "ctl", 1), (3700, "ctl", 0), (7000, "scene", 1), (7600, "adv", 1)]


def b2_t0(old=False):
    s, _l, _c = bsim(K3, [(200, "scene", 0)], 4000, old)
    return so.now_ms(next(x for x in s if so.cls_of(x, K3) == "orphaned"))


def b3_ev(t0):
    out = [(200, "scene", 0)]
    for off in so.BLIP2_OFFS:
        out += [(t0 + int(off * 1000), "ctl", 0), (t0 + int((off + so.BLIP2_OFF_S) * 1000), "ctl", 1)]
    return out


def b_ev(old=False):
    """Every B sub-leg's evidence: {row: args} for its judge, and the marks."""
    ev, marks, base = {}, {}, None
    s, ln, base = bsim(K1, B1_EV, ON1 + 3500, old, base)
    hold, lh = span(s, ln, 200, ON1)
    rel, lr = span(s, ln, ON1)
    b0, b1 = so.bcount(before(s, 200)), so.bcount(hold[-1])
    ev["B-HOST"] = (hold, so.frame_of(hold[0]), K1)
    ev["B-HOLD"] = (hold, lh, K1, b0)
    ev["B-RELEASE"] = (rel, lr, K1, b1, so.now_ms(hold[-1]), so.held_t0(hold))
    marks["B-HOLD"] = {"samples": hold, "lines": lh, "key": K1, "b0": b0}
    marks["B-RELEASE"] = {"samples": hold + rel, "lines": lh + lr, "key": K1, "b0": b0}
    s, ln, base = bsim(K2, B2_EV, 9000, old, base)
    on, lo = span(s, ln, 2700, 7000)
    sc, lsc = span(s, ln, 7000)
    b_pre = so.bcount(before(s, 200))
    ev["B-BLIP"] = (on, lo, K2, so.bcount(before(s, 2700)))
    ev["B-SCENE"] = (sc, lsc, K2, so.bcount(before(s, 7000)))
    pre, lpre = span(s, ln, 0, 7000)
    marks["B-BLIP"] = {"samples": pre, "lines": lpre, "key": K2, "b0": b_pre}
    marks["B-SCENE"] = {"samples": s, "lines": ln, "key": K2, "b0": b_pre}
    t0 = b2_t0(old)
    s3, ln3, base3 = bsim(K3, b3_ev(t0), t0 + 6800, old, base)
    ev["B-BLIP2"] = (s3, ln3, K3, base)
    marks["B-BLIP2"] = {"samples": s3, "lines": ln3, "key": K3, "b0": base}
    s4, _ln4, _b4 = bsim(K4, [(200, "scene", 0)], 6400, old, base3)
    ev["B-CTLON"] = (s4, K4, base3, so.now_ms(before(s4, 200)))
    return ev, marks


B_JUDGE = {"B-HOST": so.judge_b_host, "B-HOLD": so.judge_b_hold, "B-RELEASE": so.judge_b_release, "B-BLIP": so.judge_b_blip,
           "B-SCENE": so.judge_b_scene, "B-BLIP2": so.judge_b_blip2, "B-CTLON": so.judge_b_ctlon}


def b_rows(word=None):
    ev, marks = b_ev(word == "orphan")
    return {r: B_JUDGE[r](*a) for r, a in ev.items()}, marks


# ---- C: own_field_pass_rule decides; battlewire's builders print
OWN_T, LOAD_T = 23000, 23400


def c_ev(mode, cal=None):
    """One desk-scene attempt's evidence for ``mode`` (dry / cache / pend / age / src) under the word's lever (the bench's
    c_own_word): the term own_field_pass_rule finds, the lines NoteOwnJump and the cache print, the record, the blocks."""
    word = so.c_own_word(mode, cal)
    lever = BW.OWN_LEVER_NAMES.index(word)
    pending = so.C_DEST if mode == "pend" else -1
    cache = so.C_DEST if mode in ("cache", "age") else -1
    stands = mode == "cache"
    term = BW.own_field_pass_rule(lever, True, so.C_FIELD, so.C_DEST, True, pending, False, -1, -1, cache, stands, False, False)
    verdict, why = ("pass", BW.OWN_TERM_NAMES[term]) if term > 0 else ("bounce", "not-host")
    k = 5
    lines = [L(BW.swap_harness_lever_line("fade", "old")), L(BW.swap_harness_lever_line("own", word)), L("Map: 351 (Dali/Inn)"),
             L("[NetSync] dialogue lock: win 3 text 129 opened locked (the host drives it)" + BW.swap_stamp_text(True, 4000))]
    if mode == "src":
        lines = ([L(BW.swap_harness_cache(so.C_DEST, 1, HM)), L(BW.intent_cache_log_write(True, so.C_DEST, 1, HM, -1, 900))] + lines
                 + [L(BW.intent_cache_log_clear(True, so.C_DEST, BW.intent_cache_left_reason(HM, so.C_FIELD, so.C_DEST), 3000))])
    if mode in ("cache", "age"):
        lines += [L(BW.swap_harness_cache(so.C_DEST, 2, so.C_FIELD)), L(BW.intent_cache_log_write(True, so.C_DEST, 2, so.C_FIELD, -1, 20000))]
    if mode == "age":
        lines.append(L(BW.intent_cache_log_clear(True, so.C_DEST, "aged 2000 ms", 22000)))
    if mode == "pend":
        lines.append(L(FG.SWAP_INTENT_FOLLOW_LINE.format(field=so.C_DEST) + BW.swap_stamp_text(True, 22550)))
    jump = BW.swap_log_own_jump(True, term if term > 0 else 0, so.C_DEST, so.C_FIELD, verdict, why, -1, k, OWN_T, term=term,
                                announced_ms=1000)
    if jump is not None:
        lines.append(L(jump))
    if verdict == "pass":
        lines.append(L("Map: 352 (Dali/Inn)"))
        if mode == "cache":
            lines.append(L(BW.intent_cache_log_clear(True, so.C_DEST, BW.intent_cache_left_reason(so.C_FIELD, so.C_DEST, so.C_DEST), LOAD_T)))
        last = rec(id=k, dest=so.C_DEST, state="landed", open_by="own", open_t=OWN_T, own_t=OWN_T, own_dest=so.C_DEST,
                   own_verdict=verdict, own_why=why, owns=1, land_t=LOAD_T, land_field=so.C_DEST, land_via="own", **{"from": so.C_FIELD})
    else:
        lines += [L(BW.swap_log_landed(True, so.C_FIELD, BW.SWAP_VIA_BOUNCE, k, LOAD_T)), L("Map: 351 (Dali/Inn)")]
        last = rec(id=k, dest=so.C_DEST, state="open", open_by="own", open_t=OWN_T, own_t=OWN_T, own_dest=so.C_DEST,
                   own_verdict=verdict, own_why=why, owns=1, bounces=1, reloads=1, reload_t=LOAD_T, **{"from": so.C_FIELD})
    b0 = block(counts__bounces=2, own__passes=3, own__by__cache=1, own__converted=1, fade__ends__own=1)
    b1 = block(counts__bounces=2 + (verdict == "bounce"), own__passes=3 + (verdict == "pass"),
               own__by__cache=1 + (term == BW.OWN_TERM_CACHE), own__converted=1 + (term == BW.OWN_TERM_PENDING),
               fade__ends__own=1 + (term == BW.OWN_TERM_PENDING))
    samples = [S(22900, field=so.C_FIELD, pending=pending, sw={"last.id": 4}), S(OWN_T + 50, field=so.C_FIELD, sw={"last": last})]
    return {"lines": lines, "last": last, "b0": b0, "b1": b1, "samples": samples, "pending": pending}


def c_rows(word=None):
    d, c, p, a, s = (c_ev(m, word) for m in ("dry", "cache", "pend", "age", "src"))
    rows = {"C-BOUNCE": so.judge_c_bounce(d["last"], d["lines"], d["b0"], d["b1"]),
            "C-CACHE": so.judge_c_cache(c["lines"], c["last"], c["b0"], c["b1"]),
            "C-PEND": so.judge_c_pend(p["lines"], p["last"], p["b0"], p["b1"]),
            "C-AGE": so.judge_c_age(a["lines"], a["last"], a["b0"], a["b1"]),
            "C-SRC": so.judge_c_src(s["lines"], s["last"], s["b0"], s["b1"], HM)}
    return rows, {"C-CACHE": c, "C-PEND": p}


# ---- P: pin_use_rule decides; the landing stages section 0 from the pin or the latest frame (flag 8720: pin 0, latest 1)
def p_ev(sub, word=None):
    lever_old = word == "pin" and sub in ("pin", "party")
    quality = BW.PIN_LATE if sub == "late" else BW.PIN_PRE
    fld = so.P_OTHER if sub == "other" else AW
    age = so.P_AGE_MS if sub == "aged" else 400
    verdict, why = BW.pin_use_rule(lever_old, False, quality, AW, age, fld)
    use = "pin" if verdict == BW.PIN_USE_PIN else why
    pin = copy.deepcopy(SENT["pin"])
    pin.update(last_use=use, last_use_quality=BW.PIN_QUALITY_NAMES[quality], last_use_field=fld, last_party="latest", other=2 + (why == "other"),
               held=[{"field": AW, "nonce": 7, "quality": "pre", "land_seen": True, "age_ms": 600, "capture_ms": 1200}] if sub == "other" else [])
    lines = [L(BW.swap_harness_pinbench(7, AW, so.P_FLAG, 0, 1))]
    if verdict == BW.PIN_USE_PIN:
        lines.append(L(BW.pin_log_stages(True, AW, 7, age, 1, 5000)))
    elif fld == AW:
        lines.append(L(BW.pin_log_latest(True, AW, BW.pin_latest_why_words(why, age, 7), 5000)))
    return {"flag": verdict != BW.PIN_USE_PIN, "pin": pin, "last": rec(story="pin" if verdict == BW.PIN_USE_PIN else "latest"),
            "lines": lines, "other0": 2}


def p_rows(word=None):
    e = {s: p_ev(s, word) for s in ("pin", "aged", "other", "late", "party")}
    c = 2
    rows = {"P-PIN": so.judge_p_pin(e["pin"]["flag"], e["pin"]["pin"], e["pin"]["last"], e["pin"]["lines"]),
            "P-AGED": so.judge_p_guard(e["aged"]["flag"], e["aged"]["pin"], "aged"),
            "P-OTHER": so.judge_p_other(e["other"]["flag"], e["other"]["pin"], e["other"]["other0"]),
            "P-LATE": so.judge_p_guard(e["late"]["flag"], e["late"]["pin"], "late", "late"),
            "P-PARTY": so.judge_p_party(e["party"]["flag"], e["party"]["pin"], [0, c, -1, -1], c, None, [L(BW.swap_harness_clear(True))])}
    return rows, {"P-PIN": e["pin"], "P-PARTY": e["party"]}


# ---- L: intent_landing_step at the hook, intent_life_rule every Update
def lsim(old=False, land_at=400, body_at=500, T=4000, step_at=0):
    """One lifebench intent emitted at t 0 (intent.emit_t 0 on the swap clock). ``body_at`` the control char's binding on AW: the
    harness's own `player.uid` reads 1 from then (and on HM before the landing: the old field's body), None between; ``step_at`` the
    first Update the engine's life step runs (a LATE step: its body stamp and its end both wait for it). The step stamps
    intent.body_ms as IntentLifeStepCore does -- the first step with the landing on_intent, on the field and the body there."""
    samples, lines = [], []
    active, landing, landed_ms, end, life, end_t, body_ms = True, BW.INTENT_LANDING_PENDING, -1, None, -1, -1, -1

    def put(now, fld, sw):
        s = S(now, field=fld, sw=dict(sw, **{"intent.emit_t": 0, "intent.body_ms": body_ms}))
        s["player"]["uid"] = 1 if now < land_at or now >= body_at else None
        samples.append(s)
    for now in range(0, T + 1, DT):
        if active and landing == BW.INTENT_LANDING_PENDING and now >= land_at:
            landing = BW.intent_landing_step(landing, True, AW, AW)
            landed_ms = now
            lines.append(L(BW.life_log_landed(True, 1, AW, now, now)))
            put(now, AW, {"intent.active": True, "intent.landing": BW.INTENT_LANDING_NAMES[landing], "intent.landed_ms": landed_ms,
                          "intent.field": AW})
        if active and now >= step_at:
            on_intent, there = landing != 0 and now >= land_at, now >= body_at
            if landing == BW.INTENT_LANDING_ON_INTENT and body_ms < 0 and on_intent and there:
                body_ms = now
            v = BW.intent_life_rule(old, now, now - landed_ms if landed_ms >= 0 else -1, landing, on_intent, there)
            if v != BW.INTENT_LIFE_KEEP:
                active, end, life, end_t = False, BW.INTENT_END_NAMES[v], now, now
                lines.append(L(BW.life_log_ended(True, 1, AW, now, v, now)))
        put(now, AW if now >= land_at else HM,
            {"intent.active": active, "intent.landing": BW.INTENT_LANDING_NAMES[landing], "intent.landed_ms": landed_ms,
             "intent.last_end": end, "intent.last_life_ms": life, "intent.end_t": end_t})
    return samples, lines


def l_rows(word=None):
    s, ln = lsim(word == "life")
    return {"L-LAND": so.judge_l_land(s, ln), "L-STANDS": so.judge_l_stands(s)}, {"L-STANDS": {"intent": so.sget(s[-1], "intent")}}


# ---- F: the D+E rules, an Update at a time
F_SETUP = {"F-FAST": dict(), "F-3X": dict(speed=3), "F-BLACK": dict(view="black"), "F-JOIN": dict(view="heading", left=7),
           "F-HURRY": dict(view="heading", left=60), "F-OPEN": dict(backlog="open"), "F-AHEAD": dict(backlog="ahead"),
           "F-AGED": dict(), "F-RECHECK": dict(mid="ahead"), "F-REASSERT": dict(reassert_at=3), "F-KEY": dict(backlog="key")}


def fsim(row, lever_name="act", t0=50000):
    """One follow on the D+E twins: PathRule and ActionRule at the start, then each Update the fade slot (cur: 0 visible, 255 black),
    BlackTicksRule on the game ticks, ReassertRule, DueRule with the prime -- to the first commit verdict. -> (samples, lines, b0)."""
    cfg = dict(view="visible", left=0, backlog="none", mid="none", speed=1, reassert_at=None)
    cfg.update(F_SETUP[row])
    lever = BW.FADE_LEVER_NAMES.index(lever_name)
    view0 = BW.FADE_VIEW_NAMES.index(cfg["view"])
    bk0 = BW.FADE_BK_NAMES.index(cfg["backlog"])
    path = BW.fade_path_rule(False, lever, False, view0, bk0)
    action, frames = BW.fade_action_rule(path, view0, cfg["left"], lever)
    cur0 = 255 if cfg["view"] == "black" else 0
    slot = {"from": cur0, "at": 0, "len": cfg["left"] if cfg["view"] == "heading" else 0}       # cur heads to 255 over len ticks
    if action in (BW.FADE_ACT_FADE, BW.FADE_ACT_HURRY):
        slot = {"from": cur0, "at": 0, "len": frames}
    elif action == BW.FADE_ACT_WIPE:
        slot = {"from": 0, "at": 0, "len": BW.FADE_OLD_FRAMES}                  # FF9Wipe_FadeOutEx forces visible first: the flash
    grace = BW.fade_grace_rule(action)

    def cur_at(k):
        if slot["len"] <= 0:
            return 255 if slot["from"] >= 255 else slot["from"]
        f = min(1.0, max(0.0, (k - slot["at"]) / slot["len"]))
        return int(round(slot["from"] + (255 - slot["from"]) * f))
    armed, since, bt, primed, reasserted, reasserts, held_any = False, 0, -1, False, False, 0, False
    lines, samples, ticks, due, prev_prime = [], [], 0, BW.FADE_DUE_WAIT, False
    b0 = block(fade__reasserts=4, fade__last__due_t=10, last__commit_t=10)
    u = 0
    while True:
        ms = u * DT
        if u > 0:
            ticks += cfg["speed"]
            if cfg["reassert_at"] is not None and ticks >= cfg["reassert_at"] and slot.get("off") is None:
                slot = {"from": 0, "at": ticks, "len": 0, "off": True}           # `swap blackout off`: the slot back to visible
        cur = cur_at(ticks)
        black = cur >= BW.FADE_BLACK_FLOOR
        view = BW.FADE_VIEW_BLACK if black else (BW.FADE_VIEW_HEADING if slot["len"] > 0 and ticks < slot["at"] + slot["len"]
                                                   else BW.FADE_VIEW_VISIBLE)
        timer_out = ms >= BW.FADE_OLD_WAIT_MS
        if u > 0 and BW.fade_reassert_rule(path, reasserted, timer_out, view):
            reasserted, reasserts = True, reasserts + 1
            lines.append(L(BW.fade_log_reassert(True, view, cur, frames, t0 + ms)))
            slot = {"from": cur, "at": ticks, "len": frames, "off": True}
            cur = cur_at(ticks)
            view = BW.FADE_VIEW_HEADING
        armed, since, bt = BW.fade_black_ticks_rule(view == BW.FADE_VIEW_BLACK, armed, since, ticks)
        bk_now = BW.FADE_BK_NAMES.index(cfg["mid"]) if u > 0 else bk0
        if path == BW.FADE_PATH_FAST:
            bk_now = BW.FADE_BK_NAMES.index(cfg["mid"]) if u > 0 else BW.FADE_BK_NONE
        held = path == BW.FADE_PATH_FAST and bk_now != BW.FADE_BK_NONE and lever not in (BW.FADE_LEVER_NOGATE, BW.FADE_LEVER_NORECHECK)
        held_any = held_any or held
        due = BW.fade_due_rule(path, timer_out, view, bt, grace, bk_now, prev_prime, lever) if u > 0 else BW.FADE_DUE_WAIT
        samples.append(S(t0 + ms, field=HM, ctl=False,
                         sw={"fade.cur_now": cur, "fade.black_ticks": bt, "fade.held": held, "fade.left_start": cfg["left"] if cfg["view"] == "heading" else -1,
                             "fade.path": BW.FADE_PATH_NAMES[path], "fade.action": BW.FADE_ACT_NAMES[action], "fade.reasserts": 4 + reasserts,
                             "fade.last.due_t": 10, "last.commit_t": 10}))
        if due not in (BW.FADE_DUE_WAIT, BW.FADE_DUE_PRIME):
            break
        prev_prime = due == BW.FADE_DUE_PRIME
        u += 1
        if u > 200:
            raise AssertionError("the fade never came due")
    due_t = t0 + u * DT
    last = {"field": AW, "path": BW.FADE_PATH_NAMES[path], "action": BW.FADE_ACT_NAMES[action], "by": BW.FADE_DUE_NAMES[due],
            "due_t": due_t, "ms": u * DT, "ticks": ticks, "frames": frames, "view_start": BW.FADE_VIEW_NAMES[view0], "mode_start": "sub",
            "backlog_start": BW.FADE_BK_NAMES[bk0], "primed": due == BW.FADE_DUE_BLACK and prev_prime}
    samples.append(S(due_t + 40, field=AW, sw={"fade.last": last, "fade.reasserts": 4 + reasserts, "last.commit_t": due_t,
                                                 "last.land_t": due_t + 40, "last.follow_t": t0}))
    return samples, lines, b0, {"held": held_any, "left": cfg["left"] if cfg["view"] == "heading" else None}


F_LEVER = {"fade": "old", "long": "long", "nogate": "nogate", "norecheck": "norecheck", "nohurry": "nohurry"}


def f_rows(word=None):
    rows, marks = {}, {}
    for r in so.F_ROWS:
        if word == "long" and r == "F-REASSERT":
            continue
        s, ln, b0, extra = fsim(r, F_LEVER.get(word, "act"))
        rows[r] = so.judge_fade(r, s, ln, b0)
        marks[r] = {"fade": so.sget(s[-1], "fade.last"), **extra}
    return rows, marks


def solo_rows(word=None):
    rows, marks = dict(k_rows()), {}
    for fn in (a_rows, b_rows, c_rows, p_rows, l_rows, f_rows):
        r, m = fn(word)
        rows.update(r)
        marks.update(m)
    return rows, marks
'''


# ------------------------------------------------------------------------------------------------ K
def test_k_proof_reads_the_one_proof_line_and_the_dialogue_selftest():
    """K-PROOF: the OK line (battlewire.SWAP_PROOF_RE: every constant pinned) once, no FAIL, the verdict 'ok', the dialogue selftest's OK
    line and no dialogue FAIL. N, M, the clock source and its resolution never fail it."""
    out = _child(_FIX + r'''
j = lambda lines=[PROOF, DLG_OK], v="ok": so.judge_proof(lines, v)[0]
other = L("[NetSync] " + BW.swap_proof_text(400, 120, "stopwatch", 1000, False))
OUT = {"good": j(), "other_counts_stopwatch": j([other, DLG_OK]),
       "no_line": j([DLG_OK]), "two_lines": j([PROOF, PROOF, DLG_OK]),
       "fail_line": j([PROOF, DLG_OK, L("[NetSync] " + BW.swap_proof_fail_text(row="clock.tsc_40_days"))]),
       "constant": j([PROOF.replace("line window 10000 ms", "line window 9000 ms"), DLG_OK]),
       "verdict": j(v="fail: row clock.zero"), "verdict_none": j(v=None), "no_dialogue": j([PROOF]),
       "dialogue_fail": j([PROOF, DLG_OK, L("[NetSync] dialogue authority selftest: FAIL (key: row 3)")])}
''')
    assert out.pop("good") and out.pop("other_counts_stopwatch"), out
    assert not any(out.values()), out


def test_k_proof_reports_the_proof_cost_line_and_never_judges_it():
    """Review fix F09's `[NetSync] field swap proof cost: ...` line (once per SelfTest call, before the proof line) is reported in
    K-PROOF's detail -- the Unity Mono figure on the bench's record -- and never judged: green with or without it, and it is no proof
    or FAIL line (no `selftest: ` text, no class)."""
    out = _child(_FIX + r'''
cost = L("[NetSync] field swap proof cost: 41 ms on this thread (quiet_equals_loud on 104 rule sets: verdict grid swept 1x, live "
         "hold grid 2x)")
with_cost, without = so.judge_proof([cost, PROOF, DLG_OK], "ok"), so.judge_proof([PROOF, DLG_OK], "ok")
OUT = {"with": list(with_cost), "without": list(without), "red_still_red": so.judge_proof([cost, DLG_OK], "ok")[0],
       "cls": BW.swap_line_class(so.unstamped(cost.split("|M| ", 1)[-1]))}
''')
    assert out["with"][0] is True and out["without"][0] is True and out["red_still_red"] is False, out
    assert "; proof cost 41 ms on this thread (quiet_equals_loud on 104 rule sets: verdict grid swept 1x, live hold grid 2x)" in out["with"][1]
    assert "no proof cost line" in out["without"][1] and out["cls"] is None, out


def test_k_clock_has_three_outcomes_and_is_never_a_ledger_row():
    """K-CLOCK: GREEN on the stand-in's clock seam (FG.swap_clock_read over channel.qpc_read: the kit's qpc_ms() a few ms ahead of each
    sample, within its age + 100 ms); UNFIT on `src stopwatch` (the seam with no QPC: every cross-game row VOID in the duo), on a sample
    outside the band either way, on fewer than 20 samples, on hz / hires unpublished; SKIP with its reason when qpc_ms() is None (the
    bench's own wiring, `_k_clock`). It is not in any catalog: a precondition, never a red row."""
    out = _child(_FIX + r'''
import time
from harness import channel
def reads_from(qpc, n=25, skew_ms=0):
    out = []
    for i in range(n):
        now, ticks, hz, src, hires = FG.swap_clock_read(qpc, time.time())
        s = S(now, src=src, utc=int(time.time() * 1000))
        s["netsync"]["swap"]["clock"].update(ticks=ticks, hz=hz, hires=hires)
        time.sleep(0.002)
        q = channel.qpc_ms()
        out.append((None if q is None else q + skew_ms, int(time.time() * 1000), s))
    return out
have = channel.qpc_ms() is not None
seam = so.judge_clock(reads_from(channel.qpc_read), have) if have else ("n/a", "")
stopwatch = so.judge_clock(reads_from(None), True) if have else ("n/a", "")
fake = [(1000 + 5, 2000, S(1000, utc=2000)) for _ in range(25)]
behind = [(990, 2000, S(1000, utc=2000)) for _ in range(25)]
late = [(1000 + 200, 2000, S(1000, utc=2000)) for _ in range(25)]
old_sample = [(1000 + 200, 2150, S(1000, utc=2000)) for _ in range(25)]   # the sample 150 ms old: 200 <= 150 + 100
no_hz = [(1005, 2000, so_ed) for so_ed in [ed(S(1000, utc=2000), sw={"clock.hz": -1})] * 25]
class G:
    def __init__(self): self.notes = []
    def note(self, t): self.notes.append(t)
ctx = so.Ctx(None, "K")
so._qpc_ms = lambda: None
g = G()
so._k_clock(g, ctx)
OUT = {"have": have, "seam": seam[0], "stopwatch": stopwatch[0], "stopwatch_why": stopwatch[1][:200],
       "fake": so.judge_clock(fake, True)[0], "behind": so.judge_clock(behind, True)[0], "late": so.judge_clock(late, True)[0],
       "old_sample": so.judge_clock(old_sample, True)[0], "few": so.judge_clock(fake[:19], True)[0], "no_hz": so.judge_clock(no_hz, True)[0],
       "skip": so.judge_clock([], False), "wired_skip": ctx.clock[0], "wired_note": g.notes,
       "in_catalog": any("K-CLOCK" in so.catalog(w, so.LEGS) for w in [None] + list(so.WORDS))}
''')
    if out["have"]:
        assert out["seam"] == "green" and out["stopwatch"] == "unfit" and "stopwatch" in out["stopwatch_why"], out
    assert out["fake"] == "green" and out["old_sample"] == "green", out
    assert out["behind"] == out["late"] == out["few"] == out["no_hz"] == "unfit", out
    assert out["skip"][0] == "skip" and out["skip"][1].startswith("SKIP:") and "qpc_ms() is None" in out["skip"][1], out
    assert out["wired_skip"] == "skip" and any("never a red row" in n and "SKIP" in n for n in out["wired_note"]), out
    assert out["in_catalog"] is False


def test_k_refuse_lever_and_release_can_go_red_on_each_part():
    """K-REFUSE (the usage line twice, the bench refusal, co-op off), K-LEVER (each op's ack line and read-back; act reads null; `clear`
    and its CLEAR line), K-RELEASE (one release line, every lever back, a silent second reset, no leaked delay): each part alone red."""
    out = _child(_FIX + r'''
rf = lambda **kw: so.judge_refuse(dict(REFUSE, **kw))[0]
steps = lever_steps()
lv = lambda S_=steps, rest=REST, cl=CLEAR: so.judge_levers(S_, rest, cl)[0]
mut = lambda i, **kw: steps[:i] + [dict(steps[i], **kw)] + steps[i + 1:]
rl = lambda rel=RELEASE, after=REST, second=[], r=K_REC, f=33.0: so.judge_release(rel, after, second, r, f)[0]
OUT = {"refuse": rf(), "lever": lv(), "release": rl(), "act_word": so.judge_levers(
           [dict(s, levers=dict(s["levers"], fade="act")) if s["op"] == "fade" and s["word"] == "act" else s for s in steps], REST, CLEAR)[0],
       "bad": {"r_delay_acted": rf(delay=""), "r_word": rf(word="netsync swap orphan: something else"), "r_bench": rf(bench=""),
               "r_off": rf(off=BW.swap_refusal_selftest("orphan")),
               "l_refused": lv(mut(4, ok=False, why="x")), "l_no_line": lv(mut(4, lines=[])), "l_wrong_line": lv(mut(6, lines=[L(so.lever_line("own", "act"))])),
               "l_readback": lv(mut(2, levers=dict(steps[2]["levers"], delay_ms=0))), "l_stamps": lv(mut(0, levers=dict(REST))),
               "l_hostctl": lv(mut(19, levers=dict(REST))), "l_rest": lv(rest=dict(REST, fade="long")), "l_rest_hostctl": lv(rest=dict(REST, hostctl_off=True)),
               "l_no_clear": lv(cl=[]), "l_clear_mirror": lv(cl=[L(BW.swap_harness_clear(True))]), "l_empty": lv(S_=[]),
               "x_two": rl(rel=RELEASE * 2), "x_none": rl(rel=[]), "x_mirror": rl(rel=[L(BW.swap_harness_release(True))]),
               "x_after": rl(after=dict(REST, orphan="old")), "x_second": rl(second=RELEASE),
               "x_leaked": rl(r=dict(K_REC, commit_t=5300)), "x_delay_ms": rl(r=dict(K_REC, delay_ms=500)), "x_never": rl(r=rec())}}
''')
    assert out["refuse"] and out["lever"] and out["release"] and out["act_word"], out
    assert not any(out["bad"].values()), {k: v for k, v in out["bad"].items() if v}


# ------------------------------------------------------------------------------------------------ A
def test_a_judges_can_go_red_on_each_part():
    """A-FOLLOW (id +1, open_by seen, the edge order, follow_via, land_via, land_field, the close), A-STAMP (each edge line's stamp ==
    its record key: follow, L-COMMIT, L-LAND, L-CLOSE), A-DELAY (each leg within one frame of its delay, leg 2's delay_ms, two records),
    A-WORD (a stamped s163 line that strips to no form, a stamp inside the line, no s163 line at all)."""
    out = _child(_FIX + r'''
fo = lambda r=REC1, id0=1: so.judge_follow(r, id0)[0]
lines = a_lines(REC1)
st = lambda ls=lines, r=REC1: so.judge_stamp(ls, r)[0]
swap = lambda i, new: lines[:i] + [new] + lines[i + 1:]
idx = lambda needle: next(i for i, ln in enumerate(lines) if needle in ln)
de = lambda r1=REC1, r2=REC2, f=33.0, w=300: so.judge_delay(r1, r2, f, w)[0]
wd = lambda ls=lines: so.judge_word(ls)[0]
follow_core = f"[NetSync] intent: following the peer to field {AW} (parallel)"
OUT = {"good": [fo(), st(), de(), wd(), wd([L(follow_core)])],
       "bad": {"f_id": fo(id0=2), "f_open_by": fo(dict(REC1, open_by="follow")), "f_order": fo(dict(REC1, due_t=1400)),
               "f_missing_edge": fo(dict(REC1, seen_t=-1)), "f_via": fo(dict(REC1, follow_via="serial")), "f_land_via": fo(dict(REC1, land_via="other")),
               "f_field": fo(dict(REC1, land_field=HM)), "f_stale": fo(dict(REC1, close_why="stale")), "f_open": fo(dict(REC1, state="landed", close_why=None)),
               "s_follow": st(swap(idx("(parallel)"), L(follow_core + " (t 1002 ms)"))),
               "s_commit": st(r=dict(REC1, commit_t=1301)), "s_land": st(swap(idx("swap: landed"), L(BW.swap_log_landed(True, AW, BW.SWAP_VIA_FOLLOW, 2, 1341)))),
               "s_close": st(r=dict(REC1, close_t=11341)), "s_twice": st(lines + [lines[idx("swap: landed")]]),
               "s_missing": st([ln for ln in lines if "swap #2 to field" not in ln]), "s_unstamped": st(a_lines(REC1, False)),
               "d_leg1": de(r1=dict(REC1, commit_t=1340)), "d_leg2": de(r2=dict(REC2, commit_t=40300)), "d_leg2_late": de(r2=dict(REC2, commit_t=40640)),
               "d_delay_ms": de(r2=dict(REC2, delay_ms=0)), "d_same_record": de(r2=dict(REC2, id=2)), "d_never": de(r2=rec()),
               "w_noform": wd(lines + [L(follow_core + ", again (t 5 ms)")]), "w_inside": wd(lines + [L(f"[NetSync] following the peer to field {AW} (t 5 ms) now")]),
               "w_vacuous": wd([ln for ln in lines if "(parallel)" not in ln])}}
''')
    assert all(out["good"]), out
    assert not any(out["bad"].values()), {k: v for k, v in out["bad"].items() if v}


# ------------------------------------------------------------------------------------------------ B
def test_b_judges_are_green_on_the_act_rule_stream():
    """The B streams come out of battlewire.swap_orphan_window_tick on DialogSettleClock (the design's own rules, KIT-1's twins): under
    act every B judge is green -- the hold, its release by control, the relock that keeps the read clock (B-BLIP2 closes at t0 +
    AutoReadMs, one relock), the busy end and the host's ADV, the plain orphan with control on."""
    out = _child(_FIX + r'''
rows, _m = b_rows(None)
OUT = {r: [ok, d] for r, (ok, d) in rows.items()}
''')
    assert all(v[0] for v in out.values()), {k: v[1] for k, v in out.items() if not v[0]}
    assert sorted(out) == sorted(["B-HOST", "B-HOLD", "B-RELEASE", "B-BLIP", "B-SCENE", "B-BLIP2", "B-CTLON"])


def test_b_judges_can_go_red_on_each_part():
    """Each B judge's parts, each red alone on an edit of the act stream: B-HOST (no sample within 2 frames, a flag bit, host_holds,
    the lever read-back, the settle clock, the line); B-HOLD (span, a non-locked sample, the settle, a close, the holds count, the
    hold line, an orphan line); B-RELEASE (late orphan, the end line's words and N, last_end, the auto-close's timing, the count);
    B-BLIP (no relock, two relock lines, a close); B-SCENE (the busy words, no host close, the order, last_end); B-BLIP2 (THE REJECTED
    RESTART RULE -- two relocks, a late close -- and nothing counted after the close); B-CTLON (an early orphan, a hold counted)."""
    out = _child(_FIX + r'''
ev, _m = b_ev(False)
J = B_JUDGE
def run(r, i=None, v=None):
    a = list(ev[r])
    if i is not None:
        a[i] = v
    return J[r](*a)[0]
hold, lh, key, b0 = ev["B-HOLD"]
rel, lr, _k, b1, t_on, h0 = ev["B-RELEASE"]
on, lo, _k2, bb = ev["B-BLIP"]
sc, lsc, _k3, b2 = ev["B-SCENE"]
s3, ln3, _k4, base = ev["B-BLIP2"]
s4, _k5, base3, ts = ev["B-CTLON"]
first_held = next(i for i, s in enumerate(hold) if so.sget(s, "orphan.holding") == 1)
end_i = next(i for i, ln in enumerate(lr) if "control hold ends" in ln)
orph_i = next(i for i, s in enumerate(rel) if so.cls_of(s, key) == "orphaned")
close_i = next(i for i, s in enumerate(rel) if s["netsync"]["orphan_closes"] > b1["closes"])
relock_line = next(ln for ln in lo if "held -- the host's control" in ln)
blip_close = on[:-3] + [ed(s, ns={"orphan_closes": bb["closes"] + 1, "windows": []}) for s in on[-3:]]
scene_end = next(ln for ln in lsc if "control hold ends" in ln)
k3c = next(i for i, s in enumerate(s3) if s["netsync"]["orphan_closes"] > base["closes"])
c4 = next(i for i, s in enumerate(s4) if so.cls_of(s, K4) == "orphaned")
OUT = {
 "host_late": run("B-HOST", 1, -10), "host_flags": run("B-HOST", 0, [ed(s, ns={"host_flags": 10}) for s in hold]),
 "host_holds": run("B-HOST", 0, [ed(s, sw={"orphan.host_holds": False}) for s in hold]),
 "host_lever": run("B-HOST", 0, [ed(s, sw={"levers.hostctl_off": False}) for s in hold]),
 "host_settle": run("B-HOST", 0, [ed(s, ns={"host_settled_ms": -1}) for s in hold]),
 "host_line": run("B-HOST", 0, [ed(s, ns={"windows": []}) for s in hold]),
 "hold_short": run("B-HOLD", 0, hold[:len(hold) // 2]), "hold_orphaned": run("B-HOLD", 0, hold[:50] + [ed(hold[50], ns={"windows": [{"win": 3, "text": 21, "cls": "orphaned"}]})] + hold[51:]),
 "hold_settle": run("B-HOLD", 0, hold[:-1] + [ed(hold[-1], ns={"host_settled_ms": 1500})]),
 "hold_close": run("B-HOLD", 0, hold[:-1] + [ed(hold[-1], ns={"orphan_closes": b0["closes"] + 1})]),
 "hold_no_count": run("B-HOLD", 3, dict(b0, holds=b0["holds"] + 1)), "hold_no_line": run("B-HOLD", 1, [ln for ln in lh if "held --" not in ln]),
 "hold_two_lines": run("B-HOLD", 1, lh + [ln for ln in lh if "held --" in ln]),
 "hold_orphan_line": run("B-HOLD", 1, lh + [L(f"[NetSync] dialogue orphan: win 3 text 21 is not on the host's screen (host idle 2s) -- closing it at reading pace")]),
 "rel_late": run("B-RELEASE", 4, t_on - 600),
 "rel_words": run("B-RELEASE", 1, lr[:end_i] + [lr[end_i].replace("(the host's control is back)", "(the host left my field)")] + lr[end_i + 1:]),
 "rel_n": run("B-RELEASE", 5, h0 - 500), "rel_no_end": run("B-RELEASE", 1, [ln for ln in lr if "control hold ends" not in ln]),
 "rel_last_end": run("B-RELEASE", 0, rel[:-1] + [ed(rel[-1], sw={"orphan.last_end": "busy"})]),
 "rel_close_early": run("B-RELEASE", 0, rel[:orph_i + 5] + [ed(s, ns={"orphan_closes": b1["closes"] + 1, "windows": []}) for s in rel[orph_i + 5:]]),
 "rel_close_never": run("B-RELEASE", 0, [ed(s, ns={"orphan_closes": b1["closes"]}) for s in rel]),
 "blip_no_relock": run("B-BLIP", 0, [ed(s, ns={"windows": [{"win": 3, "text": 22, "cls": "orphaned"}]}) if so.cls_of(s, K2) == "locked" else s for s in on]),
 "blip_two_lines": run("B-BLIP", 1, lo + [relock_line]), "blip_count": run("B-BLIP", 3, dict(bb, relocks=bb["relocks"] + 1)),
 "blip_close": run("B-BLIP", 0, blip_close), "blip_short": run("B-BLIP", 0, on[:45]),
 "scene_words": run("B-SCENE", 1, [scene_end.replace("(the host is busy (a scene or a line))", "(the host's control is back)") if ln == scene_end else ln for ln in lsc]),
 "scene_no_close": run("B-SCENE", 1, [ln for ln in lsc if "closed (host seq" not in ln]),
 "scene_order": run("B-SCENE", 1, [ln for ln in lsc if "closed (host seq" in ln] + [ln for ln in lsc if "closed (host seq" not in ln]),
 "scene_last_end": run("B-SCENE", 0, [ed(s, sw={"orphan.last_end": "control"}) for s in sc]),
 "scene_orphan_close": run("B-SCENE", 0, sc[:-1] + [ed(sc[-1], ns={"orphan_closes": b2["closes"] + 1})]),
 "blip2_restart_two": run("B-BLIP2", 0, s3[:k3c] + [ed(s, sw={"orphan.relocks": base["relocks"] + 2}) for s in s3[k3c:]]),
 "blip2_late": run("B-BLIP2", 0, [ed(s, ns={"orphan_closes": base["closes"]}) for s in s3[:k3c + 25]] + s3[k3c + 25:]),
 "blip2_two_lines": run("B-BLIP2", 1, ln3 + [ln for ln in ln3 if "held --" in ln]),
 "blip2_after": run("B-BLIP2", 0, s3[:-1] + [ed(s3[-1], sw={"orphan.relocks": base["relocks"] + 2})]),
 "blip2_no_orphan": run("B-BLIP2", 0, [ed(s, ns={"windows": []}) if so.cls_of(s, K3) == "orphaned" else s for s in s3]),
 "ctlon_early": run("B-CTLON", 3, ts + 1000), "ctlon_holds": run("B-CTLON", 0, s4[:-1] + [ed(s4[-1], sw={"orphan.holds": base3["holds"] + 1})]),
 "ctlon_close_never": run("B-CTLON", 0, [ed(s, ns={"orphan_closes": base3["closes"]}) for s in s4]),
}
''')
    assert not any(out.values()), {k: v for k, v in out.items() if v}


def test_b_blip2_catches_the_rejected_restart_rule():
    """R5 / V4: B-BLIP2 is the falsifier of `relock_restarts_read` -- the same schedule run through the orphan stepper with the REJECTED
    rule (every re-orphan restarts the read clock) shows two or more relocks or a close past t0 + AutoReadMs + 0.8 s, and the judge
    is red; the shipped rule closes at t0 + AutoReadMs after exactly one relock."""
    out = _child(_FIX + r'''
from types import SimpleNamespace
restart = SimpleNamespace(**dict(vars(BW.SWAP_ORPHAN_RULES), since=lambda keep, kept, now: now))
t0 = b2_t0()
good = bsim(K3, b3_ev(t0), t0 + 6800)
bad = bsim(K3, b3_ev(t0), t0 + 6800, rules=restart)
base = {"closes": 0, "holds": 0, "relocks": 0}
gs, gl, gc = good
bs, bl, bc = bad
k = lambda ss: next((so.now_ms(x) for x in ss if x["netsync"]["orphan_closes"] > 0), None)
OUT = {"good": so.judge_b_blip2(gs, gl, K3, base)[0], "bad": so.judge_b_blip2(bs, bl, K3, base)[0], "bad_relocks": bc["relocks"],
       "good_close": k(gs) - t0, "bad_close": (k(bs) - t0) if k(bs) is not None else None}
''')
    assert out["good"] and out["good_close"] <= 2000 + 300, out
    assert not out["bad"] and (out["bad_relocks"] >= 2 or out["bad_close"] is None or out["bad_close"] > 2000 + 800), out


# ------------------------------------------------------------------------------------------------ C / P / L
def test_c_judges_can_go_red_on_each_part():
    """C-BOUNCE / C-CACHE / C-PEND / C-AGE / C-SRC on own_field_pass_rule's verdicts and battlewire's lines (green under act), each part
    red alone; C-PEND's REACH (the own-jump edge with session.follow.pending 352 in the sample before it) is VOID-making, never a red."""
    out = _child(_FIX + r'''
d, c, p, a, s = (c_ev(m) for m in ("dry", "cache", "pend", "age", "src"))
drop = lambda ls, needle: [ln for ln in ls if needle not in ln]
bounce_last = dict(d["last"])
cb_ = lambda last=d["last"], lines=d["lines"], b1=d["b1"]: so.judge_c_bounce(last, lines, d["b0"], b1)[0]
cc = lambda lines=c["lines"], b1=c["b1"]: so.judge_c_cache(lines, c["last"], c["b0"], b1)[0]
cp = lambda lines=p["lines"], b1=p["b1"]: so.judge_c_pend(lines, p["last"], p["b0"], b1)[0]
ca = lambda lines=a["lines"], last=a["last"], b1=a["b1"]: so.judge_c_age(lines, last, a["b0"], b1)[0]
cs = lambda lines=s["lines"], last=s["last"], b1=s["b1"], src=HM: so.judge_c_src(lines, last, s["b0"], b1, src)[0]
write_i = next(i for i, ln in enumerate(c["lines"]) if "cached on field" in ln)
pass_i = next(i for i, ln in enumerate(c["lines"]) if "passes on field" in ln)
reach = so.pend_reach(p["samples"], p["last"])
OUT = {"good": [cb_(), cc(), cp(), ca(), cs(), reach[0]],
       "bad": {"b_pass": cb_(last=dict(bounce_last, own_verdict="pass", own_why="host-field")), "b_count": cb_(b1=d["b0"]),
               "b_reloads": cb_(last=dict(bounce_last, reloads=0, reload_t=-1)), "b_no_land": cb_(lines=drop(d["lines"], "via a bounce reload")),
               "b_closed": cb_(last=dict(bounce_last, state="done")), "b_passes": cb_(b1=dict(d["b1"], own=dict(d["b1"]["own"], passes=9))),
               "c_no_write": cc(drop(c["lines"], "cached on field")), "c_no_pass": cc(drop(c["lines"], "passes on field")),
               "c_order": cc(c["lines"][:write_i] + [c["lines"][pass_i]] + c["lines"][write_i + 1:pass_i] + [c["lines"][write_i]] + c["lines"][pass_i + 1:]),
               "c_by": cc(b1=c["b0"]), "c_two_loads": cc(c["lines"] + [L("Map: 352 (Dali/Inn)")]),
               "c_bounce": cc(b1=dict(c["b1"], counts=dict(c["b1"]["counts"], bounces=9))), "c_no_left": cc(drop(c["lines"], "(the cached field)")),
               "c_loaded": cc(c["lines"] + [L(BW.intent_cache_log_clear(True, 352, BW.intent_cache_loaded_reason(352), 23500))]),
               "p_no_pass": cp(drop(p["lines"], "passes on field")), "p_converted": cp(b1=dict(p["b1"], own=dict(p["b1"]["own"], converted=1))),
               "p_loads": cp(p["lines"] + [L("Map: 352 (Dali/Inn)")]), "p_fade_end": cp(b1=dict(p["b1"], fade=dict(p["b1"]["fade"], ends=dict(p["b1"]["fade"]["ends"], own=1)))),
               "p_cancelled": cp(p["lines"] + [L("[NetSync] follow-warp to field 352 cancelled: this load already landed on it (no second load)")]),
               "a_no_clear": ca(drop(a["lines"], "aged 2000 ms")), "a_passed": ca(last=dict(a["last"], own_verdict="pass", own_why="cache")),
               "a_count": ca(b1=a["b0"]), "s_wrong_src": cs(src=4003), "s_no_clear": cs(drop(s["lines"], "I left field")),
               "s_passed": cs(last=dict(s["last"], own_verdict="pass", own_why="host-field")),
               "reach_no_jump": so.pend_reach(p["samples"], dict(p["last"], own_t=-1))[0],
               "reach_not_pending": so.pend_reach([ed(x, ns={"session.follow.pending": -1}) for x in p["samples"]], p["last"])[0],
               "reach_other_dest": so.pend_reach(p["samples"], dict(p["last"], own_dest=351))[0]}}
''')
    assert all(out["good"]), out
    assert not any(out["bad"].values()), {k: v for k, v in out["bad"].items() if v}


def test_c_done_waits_for_this_attempts_own_jump():
    """c_done (the leg C watch's stop): only THIS attempt's record (last.id past the id before the warp) with an own Field(352) that
    stood on 352 or reloaded after it. Second-run fix (run 20261030-040045): the previous attempt's record (still `last`, own_t /
    own_dest 352 / reload_t all set) ended every later watch at its first sample, before any injection."""
    out = _child(_FIX + r'''
jumped = {"last.own_t": 5000, "last.own_dest": 352, "last.reload_t": 5400}
w = lambda **kw: dict(jumped, **{"last." + k: v for k, v in kw.items()})
OUT = {"own_jump_reloaded": so.c_done(S(5500, field=351, sw=w(id=5)), 4),
       "own_jump_on_352": so.c_done(S(5500, field=352, sw=w(id=5, reload_t=-1)), 4),
       "stale_record": so.c_done(S(100, field=351, sw=w(id=4)), 4),
       "no_own_jump": so.c_done(S(5500, field=351, sw=w(id=5, own_t=-1, own_dest=-1, reload_t=-1)), 4),
       "other_dest": so.c_done(S(5500, field=351, sw=w(id=5, own_dest=351)), 4),
       "before_reload": so.c_done(S(5100, field=351, sw=w(id=5, reload_t=-1)), 4),
       "wired": "c_done(s, id0)" in __import__("inspect").getsource(so._c_attempt)}
''')
    assert out["own_jump_reloaded"] and out["own_jump_on_352"] and out["wired"], out
    assert not any(out[k] for k in ("stale_record", "no_own_jump", "other_dest", "before_reload")), out


def test_p_and_l_judges_can_go_red_on_each_part():
    """P-PIN (the flag from the pin, the stages line at 1 story byte, last_use, last.story), P-AGED / P-LATE (the latest frame's flag and
    the pin's why / quality), P-OTHER (the held entry, the count), P-PARTY (the story from the pin AND the party from the latest frame,
    then the clear: G2); L-LAND (the 'I landed' line and landed_ms >= 0, the evidence that outlives the intent's end; the on_intent
    sample with the intent active is reported, not required, so `life old` ending the intent in the hook's own frame stays green; the
    R1 hole under `life` is VOID, never red) and L-STANDS (stands, body_ms read, the harness's own body read, body_ms no later than
    it + 100 ms, and the life's bound with the body term -- the first-run fix: a body 1.7 s past the landing is green, a late step
    hiding behind its own stamp reds on the anchor alone, an end before the body reds on the bound)."""
    out = _child(_FIX + r'''
e = {k: p_ev(k) for k in ("pin", "aged", "other", "late", "party")}
pp = lambda flag=False, pin=e["pin"]["pin"], last=e["pin"]["last"], lines=e["pin"]["lines"]: so.judge_p_pin(flag, pin, last, lines)[0]
pin2 = lambda d, **kw: dict(d, **kw)
stage_b2 = [ln.replace("differs at 1 story bytes", "differs at 2 story bytes") for ln in e["pin"]["lines"]]
pa = lambda flag=True, pin=e["aged"]["pin"]: so.judge_p_guard(flag, pin, "aged")[0]
pl = lambda flag=True, pin=e["late"]["pin"]: so.judge_p_guard(flag, pin, "late", "late")[0]
po = lambda flag=True, pin=e["other"]["pin"], o0=2: so.judge_p_other(flag, pin, o0)[0]
CL = [L(BW.swap_harness_clear(True))]
pr = lambda flag=False, mb=[0, 2, -1, -1], c=2, ma=None, cl=CL, pin=e["party"]["pin"]: so.judge_p_party(flag, pin, mb, c, ma, cl)[0]
ls, ll = lsim(False)
lo, llo = lsim(True)
land = lambda S_=ls, lines=ll: so.judge_l_land(S_, lines)[0]
stands = lambda S_=ls: so.judge_l_stands(S_)[0]
hookless = [s for s in lo if not (so.sget(s, "intent.landing") == "on_intent" and so.sget(s, "intent.active") is True)]
r1 = [ed(s, sw={"intent.landed_ms": -1}) for s in lo]
r1_lines = [ln for ln in llo if "I landed" not in ln]
lb, _lbl = lsim(body_at=400 + 1700)                      # the body binds 1.7 s past the landing (30602's auto entry_settle hold)
lrun, _lrl = lsim(land_at=1172, body_at=2891)            # run 20261030-024220's shape: landed 1172, body 2891
step_late, _sll = lsim(body_at=2200, step_at=2891)       # the masking class: the harness sees the body at 2200, the step runs late
OUT = {"good": [pp(), pa(), pl(), po(), pr(), land(), stands(), land(lo, llo),
                land(hookless, llo), land([ed(s, sw={"intent.active": False}) for s in ls]),
                land([ed(s, sw={"intent.landing": None}) for s in ls]), stands(lb), stands(lrun)],
       "lb": so.judge_l_stands(lb)[1], "step_late": so.judge_l_stands(step_late)[1],
       "void": [so.l_land_void(r1, r1_lines, "life"), so.l_land_void(r1, r1_lines, None), so.l_land_void(r1, r1_lines, "fade"),
                so.l_land_void(lo, llo, "life"), so.l_land_void(r1, llo, "life"), so.l_land_void(lo, r1_lines, "life"),
                so.l_land_void(ls, ll, "life")],
       "hookless": [len(hookless) < len(lo), so.judge_l_land(hookless, llo)[1]],
       "bad": {"p_flag": pp(flag=True), "p_flag_unread": pp(flag=None), "p_no_line": pp(lines=e["pin"]["lines"][:1]), "p_bytes": pp(lines=stage_b2),
               "p_use": pp(pin=pin2(e["pin"]["pin"], last_use="aged")), "p_story": pp(last=rec(story="latest")),
               "a_flag": pa(flag=False), "a_why": pa(pin=pin2(e["aged"]["pin"], last_use="pin")),
               "l_flag": pl(flag=False), "l_why": pl(pin=pin2(e["late"]["pin"], last_use="pin")), "l_quality": pl(pin=pin2(e["late"]["pin"], last_use_quality="pre")),
               "o_flag": po(flag=False), "o_held": po(pin=pin2(e["other"]["pin"], held=[])), "o_count": po(o0=3),
               "r_flag": pr(flag=True), "r_party_from_pin": pr(mb=[0, 1, -1, -1]), "r_no_mirror": pr(mb=None), "r_last_party": pr(pin=pin2(e["party"]["pin"], last_party="pin")),
               "r_mirror_kept": pr(ma=[0, 2, -1, -1]), "r_clear_line": pr(cl=[L(BW.swap_harness_clear(False))]),
               "land_unlanded": land([ed(s, sw={"intent.landed_ms": -1}) for s in ls]), "land_no_samples": land([]),
               "land_no_line": land(lines=[ln for ln in ll if "I landed" not in ln]), "land_r1": land(r1, r1_lines),
               "land_other_field": land(lines=[ln.replace(f"field {AW} after", f"field {HM} after") for ln in ll]),
               "stands_old": stands(lo), "stands_late": stands(ls[:-1] + [ed(ls[-1], sw={"intent.last_life_ms": 2600})]),
               "stands_early": stands(ls[:-1] + [ed(ls[-1], sw={"intent.last_life_ms": 1300})]),
               "stands_unlanded": stands([ed(s, sw={"intent.landed_ms": -1}) for s in ls]),
               "stands_step_late": stands(step_late),
               "stands_before_body": stands(lb[:-1] + [ed(lb[-1], sw={"intent.last_life_ms": so.sget(lb[-1], "intent.body_ms") - 60})]),
               "stands_body_unread": stands([ed(s, sw={"intent.body_ms": -1}) for s in ls]),
               "stands_harness_unread": stands([ed(s, top={"player.uid": None}) for s in ls]),
               "stands_harness_home_only": stands([ed(s, top={"player.uid": None}) if s["field"]["id"] == AW else s for s in ls])}}
''')
    assert all(out["good"]), out
    # the body term: lsim(body_at=land + 1700) ends on the body, gap 0, the harness reading it in the same Update
    assert "body 2112 ms, harness_body 2112 ms, gap 0" in out["lb"], out["lb"]
    # the masking class reds ONLY on the independent anchor: its 3-term bound alone reads green (gap 0 behind the step's own stamp)
    sl = out["step_late"]
    assert "the engine saw my body no later than the harness) NO" in sl and "in [0, 400] ok" in sl and "gap 0" in sl, sl
    assert not any(out["bad"].values()), {k: v for k, v in out["bad"].items() if v}
    v = out["void"]
    assert isinstance(v[0], str) and "R1 hole" in v[0] and "before the landing hook" in v[0], v      # only `life`, only the R1 shape
    assert v[1:] == [None] * 6, v
    assert out["hookless"][0] and "not seen (reported, not required)" in out["hookless"][1], out["hookless"]


# ------------------------------------------------------------------------------------------------ F
def test_f_judges_are_green_on_the_act_rules_and_can_go_red_on_each_part():
    """Every F row on the D+E twins under act is green; each row's parts red alone: the sentinel ("the engine never ran the follow
    fade"), another field, path / action / frames / by / primed, ticks and ms bounds, F-BLACK's black_ticks and its cur_now dip, F-JOIN's
    left and grace, F-HURRY's drop, F-RECHECK's hold, F-REASSERT's line and count. The first-run fixes (run 20261030-024220): the timer
    rows' floor is 900 - the measured start frame (900 - 2 frames with no start pair), so the run's F-KEY (882 ms on a 37 ms start
    frame) is green and 859 red; F-JOIN on a black start is a setup miss (fade_void: VOID), never on a heading one."""
    out = _child(_FIX + r'''
ev = {r: fsim(r) for r in so.F_ROWS}
def jf(r, samples=None, lines=None, b0=None):
    s, ln, b, _x = ev[r]
    return so.judge_fade(r, s if samples is None else samples, ln if lines is None else lines, b if b0 is None else b0)[0]
def fl(r, **kw):
    s = ev[r][0]
    last = dict(so.sget(s[-1], "fade.last"), **kw)
    return s[:-1] + [ed(s[-1], sw={"fade.last": last})]
def mid(r, key, v, i=1):
    s = ev[r][0]
    return s[:i] + [ed(s[i], sw={key: v})] + s[i + 1:]
good = {r: [jf(r), so.judge_fade(r, *ev[r][:3])[1]] for r in so.F_ROWS}
bad = {"sentinel": jf("F-FAST", ev["F-FAST"][0][:-1] + [ed(ev["F-FAST"][0][-1], sw={"fade.last": SENT["fade"]["last"]})]),
       "field": jf("F-FAST", fl("F-FAST", field=HM)), "fast_path": jf("F-FAST", fl("F-FAST", path="old")), "fast_action": jf("F-FAST", fl("F-FAST", action="join")),
       "fast_frames": jf("F-FAST", fl("F-FAST", frames=24)), "fast_by": jf("F-FAST", fl("F-FAST", by="fallback")), "fast_primed": jf("F-FAST", fl("F-FAST", primed=False)),
       "fast_ticks": jf("F-FAST", fl("F-FAST", ticks=15)), "fast_ms": jf("F-FAST", fl("F-FAST", ms=600)),
       "3x_ms": jf("F-3X", fl("F-3X", ms=250)), "3x_ticks": jf("F-3X", fl("F-3X", ticks=18)), "3x_low": jf("F-3X", fl("F-3X", ticks=11)),
       "black_view": jf("F-BLACK", fl("F-BLACK", view_start="heading")), "black_action": jf("F-BLACK", fl("F-BLACK", action="wipe")),
       "black_ticks": jf("F-BLACK", [ed(s, sw={"fade.black_ticks": min(2, s["netsync"]["swap"]["fade"]["black_ticks"])}) for s in ev["F-BLACK"][0]]),
       "black_dip": jf("F-BLACK", mid("F-BLACK", "fade.cur_now", 120)), "black_ms": jf("F-BLACK", fl("F-BLACK", ms=250)),
       "join_view": jf("F-JOIN", fl("F-JOIN", view_start="visible")), "join_left": jf("F-JOIN", [ed(s, sw={"fade.left_start": 9}) for s in ev["F-JOIN"][0]]),
       "join_action": jf("F-JOIN", fl("F-JOIN", action="hurry")), "join_late": jf("F-JOIN", fl("F-JOIN", ticks=14)),
       "hurry_action": jf("F-HURRY", fl("F-HURRY", action="join")), "hurry_frames": jf("F-HURRY", fl("F-HURRY", frames=24)),
       "hurry_ticks": jf("F-HURRY", fl("F-HURRY", ticks=15)), "hurry_drop": jf("F-HURRY", mid("F-HURRY", "fade.cur_now", 0, 5)),
       "open_backlog": jf("F-OPEN", fl("F-OPEN", backlog_start="none")), "open_path": jf("F-OPEN", fl("F-OPEN", path="fast")),
       "open_by": jf("F-OPEN", fl("F-OPEN", by="black")), "open_ms": jf("F-OPEN", fl("F-OPEN", ms=800)),
       "ahead_backlog": jf("F-AHEAD", fl("F-AHEAD", backlog_start="open")), "ahead_by": jf("F-AHEAD", fl("F-AHEAD", by="black")),
       "ahead_path": jf("F-AHEAD", fl("F-AHEAD", path="old")),
       "aged_path": jf("F-AGED", fl("F-AGED", path="backlog")),
       "recheck_path": jf("F-RECHECK", fl("F-RECHECK", path="backlog")), "recheck_by": jf("F-RECHECK", fl("F-RECHECK", by="black")),
       "recheck_held": jf("F-RECHECK", [ed(s, sw={"fade.held": False}) for s in ev["F-RECHECK"][0]]), "recheck_ms": jf("F-RECHECK", fl("F-RECHECK", ms=800)),
       "reassert_no_line": jf("F-REASSERT", lines=[]), "reassert_two": jf("F-REASSERT", lines=ev["F-REASSERT"][1] * 2),
       "reassert_count": jf("F-REASSERT", b0=block(fade__reasserts=5)), "reassert_by": jf("F-REASSERT", fl("F-REASSERT", by="timer")),
       "key_backlog": jf("F-KEY", fl("F-KEY", backlog_start="ahead")), "key_path": jf("F-KEY", fl("F-KEY", path="fast")), "key_ms": jf("F-KEY", fl("F-KEY", ms=100)),
       "join_black_judged": jf("F-JOIN", fl("F-JOIN", view_start="black")),
       # THE REACH RULE: a record left over from the previous row (due_t not past the pre-intent block's) never passes -- each row
       # whose other terms a stale record could satisfy
       "stale_aged": jf("F-AGED", b0=block(fade__reasserts=4, fade__last__due_t=so.ival(so.sget(ev["F-AGED"][0][-1], "fade.last.due_t")))),
       "stale_fast": jf("F-FAST", b0=block(fade__reasserts=4, fade__last__due_t=so.ival(so.sget(ev["F-FAST"][0][-1], "fade.last.due_t")) + 1)),
       "stale_key": jf("F-KEY", b0=block(fade__reasserts=4, fade__last__due_t=so.ival(so.sget(ev["F-KEY"][0][-1], "fade.last.due_t"))))}
# the frame-aware floor (first-run fix): the start sample (fade.path set, age <= 2) and the one before it give the start frame dt0
def started(r, dt0, age=1, ms=None):
    s = ev[r][0] if ms is None else fl(r, ms=ms)
    return [S(so.now_ms(s[0]) - dt0, field=HM)] + [ed(s[0], sw={"fade.age_ms": age})] + s[1:]
floor = {"fallback": so.fade_timer_min_ms(ev["F-OPEN"][0]), "pair": so.fade_timer_min_ms(started("F-KEY", 37)),
         "late_start": so.fade_timer_min_ms(started("F-KEY", 37, age=60)), "no_samples": so.fade_timer_min_ms([])}
# run 20261030-024220's F-KEY: Begin on a 37 ms start frame, due after 882 ms -- green on the new floor (860), red under it
key_run = [jf("F-KEY", started("F-KEY", 37, ms=882)), jf("F-KEY", started("F-KEY", 37, ms=859)), jf("F-RECHECK", started("F-RECHECK", 37, ms=885)),
           jf("F-OPEN", started("F-OPEN", 30, ms=894))]
void = {"black": so.fade_void("F-JOIN", fl("F-JOIN", view_start="black")), "heading": so.fade_void("F-JOIN", ev["F-JOIN"][0]),
        "f_black": so.fade_void("F-BLACK", ev["F-BLACK"][0]), "empty": so.fade_void("F-JOIN", []),
        "unset": so.fade_void("F-JOIN", ev["F-JOIN"][0][:-1] + [ed(ev["F-JOIN"][0][-1], sw={"fade.last": SENT["fade"]["last"]})])}
OUT = {"good": good, "bad": bad, "edge": [jf("F-3X", fl("F-3X", ticks=v)) for v in (12, 17)],
       "ticks_3x": so.sget(ev["F-3X"][0][-1], "fade.last.ticks"), "floor": floor, "key_run": key_run, "void": void,
       "join_left": ev["F-JOIN"][3]["left"]}
''')
    assert all(v[0] for v in out["good"].values()), {k: v[1] for k, v in out["good"].items() if not v[0]}
    assert not any(out["bad"].values()), {k: v for k, v in out["bad"].items() if v}
    assert out["edge"] == [True, True] and out["ticks_3x"] == 15, out          # F-3X 12-17 (== duo DF-3X); the Prime at 3x reads 15
    # 900 - dt0 - 3 on a start pair; 900 - 2 measured frames (fsim DT 33) with no pair, or a first path sample past age 2
    assert out["floor"] == {"fallback": 900 - 66, "pair": 900 - 37 - 3, "late_start": 900 - 66, "no_samples": int(900 - 2 * 1000.0 / 30)}, out["floor"]
    assert out["key_run"] == [True, False, True, True], out["key_run"]
    # F-JOIN's setup miss: a black start VOIDs (judge_fade alone reds it: join_black_judged); a heading start, F-BLACK's lawful black
    # start and an unset fade.last never VOID (the last stays a red: "the engine never ran the follow fade")
    v = out["void"]
    assert isinstance(v["black"], str) and v["black"].startswith("the blackout finished before the follow began (left 0)"), v
    assert v["heading"] is None and v["f_black"] is None and v["empty"] is None and v["unset"] is None, v
    assert out["join_left"] == 7, out                                          # the one-request start: Block(2) frames after the blackout


def test_the_first_run_anchors_read_only_their_own_evidence():
    """The first-run fixes' evidence (run 20261030-024220), each read off its OWN record. L-STANDS' harness anchor skips the flip
    samples -- field.id already 30602 with the OLD field's player still published before the landing hook (landed_ms -1; the run's F
    legs show three) -- or the old body would read as mine at the flip. F-JOIN's VOID needs THIS follow's record (fade.last.due_t past
    the block's before the intent): F-BLACK's record left over means the engine never ran the follow, judge_fade's red, never a setup
    miss. (Its own child: the L and F judge tests' command lines sit near Windows' 32767-character limit.)"""
    out = _child(_FIX + r'''
ls, _ll = lsim(False)
flipped = [ed(s, top={"field.id": AW}) if s["field"]["id"] == HM and so.now_ms(s) >= 400 - 3 * DT else s for s in ls]
ev = fsim("F-JOIN")
due0 = so.ival(so.cb.path(ev[2], "fade.last.due_t"))
def black(**kw):
    s = ev[0]
    return s[:-1] + [ed(s[-1], sw={"fade.last": dict(so.sget(s[-1], "fade.last"), view_start="black", **kw)})]
OUT = {"stands": so.judge_l_stands(flipped)[0],
       "hb": [so.l_harness_body_ms(ls), so.l_harness_body_ms(flipped),
              sum(1 for s in flipped if s["field"]["id"] == AW and s["player"]["uid"] is not None and so.sget(s, "intent.landed_ms") == -1)],
       "void": [so.fade_void("F-JOIN", black(), ev[2]), so.fade_void("F-JOIN", black(due_t=due0), ev[2]),
                so.fade_void("F-JOIN", black(due_t=due0), None)],
       "stale_judged": so.judge_fade("F-JOIN", black(due_t=due0), ev[1], ev[2])[0]}
''')
    assert out["stands"] is True, out
    assert out["hb"] == [528, 528, 3], out["hb"]                 # three pre-hook flip samples; the anchor reads the first post-hook body
    v = out["void"]
    assert isinstance(v[0], str) and v[0].startswith("the blackout finished before the follow began (left 0)"), v
    assert v[1] is None and isinstance(v[2], str), v             # a stale record never VOIDs; with no block the record is taken as read
    assert out["stale_judged"] is False, out                     # ...and stays judge_fade's red


# ------------------------------------------------------------------------------------------------ the calibrations
_REGISTERED = {
    "stamps": ["A-STAMP"], "delay": ["A-DELAY"], "orphan": ["B-HOLD", "B-RELEASE", "B-BLIP", "B-BLIP2", "B-SCENE"],
    "own": ["C-CACHE", "C-PEND"], "nocache": ["C-CACHE"], "pin": ["P-PIN", "P-PARTY"], "life": ["L-STANDS"],
    "fade": ["F-FAST", "F-3X", "F-BLACK", "F-JOIN", "F-HURRY", "F-OPEN", "F-AHEAD", "F-AGED", "F-RECHECK", "F-REASSERT", "F-KEY"],
    "long": ["F-FAST", "F-3X", "F-HURRY"], "nogate": ["F-OPEN", "F-AHEAD", "F-RECHECK", "F-KEY"], "norecheck": ["F-RECHECK"],
    "nohurry": ["F-HURRY"]}


def test_each_solo_calibration_word_reds_exactly_its_rows_with_its_marker():
    """THE ORACLE (SWAP-TIMING-S164.md "Solo calibrations, pre-registered"): with every leg's evidence built by the twins, the plain run
    is green on every solo row; each word's lever, applied where the bench applies it (stamps / delay on leg A, orphan on B, own /
    nocache on C's attempts, pin around P-PIN and P-PARTY only, life on L, the fade words on F), reds EXACTLY its registered rows -- every
    other row stays green -- each predicted red carries the word's marker, and K-CAL's exactness judge passes. `long` drops F-REASSERT
    (not run under it)."""
    out = _child(_FIX + r'''
plain, _m = solo_rows(None)
res = {}
for w in so.WORDS:
    rows, marks = solo_rows(w)
    reds = sorted(r for r, (ok, _d) in rows.items() if not ok)
    pred = list(so.predicted(w, so.LEGS))
    res[w] = {"reds": reds, "pred": sorted(pred), "table": list(so.WORDS[w][1]),
              "marks": {r: so.marker(w, r, marks.get(r))[0] for r in pred},
              "mark_detail": {r: so.marker(w, r, marks.get(r))[1] for r in pred},
              "cal": so.judge_cal(w, set(reds), set(), pred)[0], "reasserted": "F-REASSERT" in rows,
              "detail": {r: rows[r][1] for r in reds if r not in pred}}
OUT = {"plain_red": sorted(r for r, (ok, d) in plain.items() if not ok), "plain_detail": {r: d for r, (ok, d) in plain.items() if not ok},
       "rows": sorted(plain), "res": res}
''')
    assert out["plain_red"] == [], out["plain_detail"]
    assert {"K-PROOF", "K-REFUSE", "K-LEVER", "K-RELEASE"} <= set(out["rows"]) and len(out["rows"]) == 38, out["rows"]
    for w, want in _REGISTERED.items():
        r = out["res"][w]
        assert r["table"] == want, (w, r["table"])
        exp = sorted(x for x in want if not (w == "long" and x == "F-REASSERT"))
        assert r["reds"] == r["pred"] == exp, (w, r["reds"], r["detail"])
        assert all(r["marks"].values()), (w, r["mark_detail"])
        assert r["cal"], w
    assert out["res"]["long"]["reasserted"] is False and out["res"]["fade"]["reasserted"] is True


def test_the_markers_can_fail():
    """A marker is falsifiable: the plain (act) evidence of each predicted row fails its word's marker (the lever's signature is absent),
    and a marker with no evidence fails."""
    out = _child(_FIX + r'''
_r, plain = solo_rows(None)
res = {}
for w in so.WORDS:
    for r in so.predicted(w, so.LEGS):
        res[f"{w}:{r}"] = so.marker(w, r, plain.get(r))[0]
OUT = {"plain": res, "empty": [so.marker(w, so.WORDS[w][1][0], None)[0] for w in so.WORDS]}
''')
    assert not any(out["plain"].values()), {k: v for k, v in out["plain"].items() if v}
    assert not any(out["empty"]), out["empty"]


def test_k_cal_judges_exactness_unreached_and_void():
    """K-CAL: green only when exactly the predicted rows are red; a predicted row that stayed green, an unpredicted red, or a predicted
    row that read UNREACHED (VOID) fails it; every predicted row UNREACHED is VOID, never a pass; a VOID row elsewhere is reported, not
    counted as a red."""
    out = _child(r'''
p = ("C-CACHE", "C-PEND")
j = lambda failed, void=(): so.judge_cal("own", set(failed), set(void), p)
OUT = {"exact": j(p)[0], "missing": j(["C-CACHE"])[0], "extra": j(list(p) + ["B-HOLD"])[0], "unreached": j(["C-CACHE", "C-PEND"], ["C-PEND"])[0],
       "void_all": j(p, p), "void_elsewhere": j(list(p) + ["F-KEY"], ["F-KEY"])[0], "finals_ignored": j(list(p) + ["K-CAL", "K-CAL-M"])[0]}
''')
    assert out["exact"] and out["void_elsewhere"] and out["finals_ignored"], out
    assert not out["missing"] and not out["extra"] and not out["unreached"], out
    assert out["void_all"][0] is False and out["void_all"][1].startswith("VOID:"), out


def test_the_solo_bench_refuses_unknown_words_and_legs_at_load():
    """COOP_CALIBRATE and COOP_LEGS are read AT LOAD (tools/play.py imports the scenario before its Session launches FF9): '' / 0 none;
    each registered word adds K-CAL-M and K-CAL naming exactly its rows; any other word -- the duo's words included only where the solo
    registers them, a typo, '1' -- exits the IMPORT with the word named (code 1, nothing run); an unknown leg, and a word whose rows the
    selected legs leave out, are refused the same way. Leg K always runs."""
    cases = {}
    for env in ({}, {"COOP_CALIBRATE": "0"}, {"COOP_CALIBRATE": "orphan"}, {"COOP_CALIBRATE": "FADE", "COOP_LEGS": "f"},
                {"COOP_LEGS": "KAB"}, {"COOP_LEGS": "ab"}, {"COOP_LEGS": "a, b"}, {"COOP_CALIBRATE": "stamps", "COOP_LEGS": "A"}):
        cases[json.dumps(env, sort_keys=True)] = _child(r'''
import inspect
cat = so.catalog(so.CAL_MODE, so.LEGS_SEL)
OUT = {"cal": so.CAL_MODE, "legs": so.LEGS_SEL, "kcal": cat.get("K-CAL"), "rows": len(cat), "finals": sorted(k for k in cat if k.startswith("K-CAL")),
       "run_reads_load": "cal, legs = CAL_MODE, LEGS_SEL" in inspect.getsource(so.run) and "calibration()" not in inspect.getsource(so.run)}
''', env)
    c = {k: v for k, v in cases.items()}
    assert c["{}"]["cal"] is None and c["{}"]["legs"] == "KABCPLF" and c["{}"]["rows"] == 38 and c["{}"]["finals"] == []
    assert c['{"COOP_CALIBRATE": "0"}']["cal"] is None
    o = c['{"COOP_CALIBRATE": "orphan"}']
    assert o["cal"] == "orphan" and o["finals"] == ["K-CAL", "K-CAL-M"] and o["kcal"] == (
        "the `orphan` calibration: exactly B-HOLD, B-RELEASE, B-BLIP, B-BLIP2, B-SCENE red"), o
    f = c['{"COOP_CALIBRATE": "FADE", "COOP_LEGS": "f"}']
    assert f["cal"] == "fade" and f["legs"] == "KF" and f["rows"] == 4 + 11 + 2, f
    assert c['{"COOP_LEGS": "KAB"}']["legs"] == c['{"COOP_LEGS": "ab"}']["legs"] == c['{"COOP_LEGS": "a, b"}']["legs"] == "KAB"
    assert c['{"COOP_CALIBRATE": "stamps", "COOP_LEGS": "A"}']["legs"] == "KA"
    assert all(v["run_reads_load"] for v in c.values())
    for env, needle in (({"COOP_CALIBRATE": "1"}, "COOP_CALIBRATE='1' is refused"), ({"COOP_CALIBRATE": "off"}, "COOP_CALIBRATE='off' is refused"),
                        ({"COOP_CALIBRATE": "orphn"}, "COOP_CALIBRATE='orphn' is refused"), ({"COOP_CALIBRATE": "stepout"}, "is refused"),
                        ({"COOP_LEGS": "KAX"}, "unknown leg(s) X"), ({"COOP_CALIBRATE": "pin", "COOP_LEGS": "KAB"}, "leaves out")):
        r = _run_child("OUT = {}", env)
        assert r.returncode == 1 and needle in r.stderr and "before the game boots" in r.stderr, (env, r.stderr[-600:])
        assert "@@" not in r.stdout


def test_the_solo_run_has_the_registered_shape():
    """The run's shape (source): K-REFUSE before the field-gate bench is armed; each A follow waits out the last record's span (JoinRule
    joins a same-destination edge to any live record inside RecordSpanMs); each C attempt starts from HOME on `fade old` with the word's
    own lever (`own old` on the dry run); the pin lever only around P-PIN and P-PARTY (`pin act` before the guards); P ends with `swap
    clear`; the F sub-legs' lock states as registered (P11); leg C's setup misses VOID its rows, never red; an engine without
    `netsync.swap` is refused before any leg. The first-run fixes (run 20261030-024220): leg C's warp is the step's ack only (Session.warp
    waits for control, which the desk scene keeps off to its own Field(352)); B-CTLON waits out RelayOwnMs under hostscene 1 before the
    settle; F-JOIN sends its blackout and the intent in ONE request (F-HURRY keeps its own setup) and a black start VOIDs it."""
    out = _child(r'''
import inspect, re
src = {n: inspect.getsource(getattr(so, n)) for n in ("run", "_leg_k", "_k_refuse", "_leg_a", "_c_attempt", "_leg_c", "_leg_p", "_leg_f",
                                                      "_setup", "c_own_word", "_b_ctlon", "_f_follow", "_f_one")}
ct = src["_b_ctlon"]
f = src["_leg_f"]
locks = dict(re.findall(r'\("(F-[A-Z0-9]+)", dict\(lock=(True|False)', f))
OUT = {"refuse_first": src["_leg_k"].index("_k_refuse") < src["_leg_k"].index("_k_lever") and "_arm(g)" in src["_k_refuse"]
       and src["_k_refuse"].index('"bench", ("intent", AWAY)') < src["_k_refuse"].index("_arm(g)"),
       "setup_no_bench": '"bench"' not in src["_setup"],
       "span_a": src["_leg_a"].count("_span_clear(g)") == 2, "span_c": "_span_clear(g)" in src["_c_attempt"],
       "c_fade_old": '_swap(g, "fade", "old")' in src["_c_attempt"], "c_own": '_swap(g, "own", c_own_word(mode, ctx.cal))' in src["_c_attempt"],
       "c_warp_ack_only": "g.warp(" not in src["_c_attempt"],
       "ctlon_relay_own": "watch(g, (RELAY_OWN_MS + 300) / 1000.0)" in ct and so.RELAY_OWN_MS == BW.DIALOG_RELAY_OWN_MS == 3000
       and ct.index("_open_line(g, ctx)") < ct.index("RELAY_OWN_MS") < ct.index("t_settle = ") < ct.index('_must(g, "hostscene", 0)'),
       "f_join_lead": '("F-JOIN", dict(lock=False, lead=(("blackout", 8),), teardown=off))' in f and "blackout(8)" not in f,
       "f_hurry_kept": '("F-HURRY", dict(lock=False, setup=blackout(60), teardown=off))' in f,
       "f_lead_one_request": 'g.send(*(f"netsync swap ' in src["_f_follow"] and 'f"netsync swap intent {AWAY}")' in src["_f_follow"],
       "f_void_wired": src["_f_one"].index("fade_void(row, samples, b0)") < src["_f_one"].index("judge_fade(") and "_void(led, ctx, [row], why)" in src["_f_one"],
       "own_words": [so.c_own_word(m, w) for m, w in (("dry", None), ("dry", "nocache"), ("cache", None), ("cache", "own"), ("pend", "nocache"))],
       "c_void": "_void(led, ctx, LEG_ROWS[\"C\"]" in src["_leg_c"],
       "pin_scope": src["_leg_p"].count('_swap(g, "pin", "old")') == 2 and src["_leg_p"].count('_swap(g, "pin", "act")') == 1,
       "p_clear": '_swap(g, "clear")' in src["_leg_p"], "refused": "publishes no `netsync.swap`" in src["run"],
       "locks": locks}
''')
    locks = out.pop("locks")
    assert locks == {"F-FAST": "False", "F-3X": "False", "F-BLACK": "False", "F-JOIN": "False", "F-HURRY": "False", "F-OPEN": "True",
                     "F-AHEAD": "True", "F-AGED": "True", "F-RECHECK": "True", "F-REASSERT": "False", "F-KEY": "True"}, locks
    assert out.pop("own_words") == ["old", "old", "act", "old", "nocache"]
    assert all(out.values()), out


def test_the_bench_reads_the_engines_words():
    """The words the bench matches are battlewire's (the engine's twins): the probe key is in the stand-in's block, the hold / end /
    stages / cache / L-OWN lines parse through the bench's matchers, the refusals are the lever's, the proof regex is battlewire's."""
    out = _child(r'''
k = (3, 21)
hold = BW.swap_log_orphan_hold(True, 3, 21, 77)
end = BW.swap_log_orphan_hold_end(True, 3, 21, 1500, BW.SWAP_HOLD_END_BUSY, 80)
OUT = {"probe": so.PROBE == "netsync.swap.clock" and "clock" in FG.NETSYNC_SWAP_KEYS,
       "hold": so.unstamped(hold) == so.hold_words(k), "hold_off": so.unstamped(BW.swap_log_orphan_hold(False, 3, 21, 77)) == so.hold_words(k),
       "end": so.end_lines([end], k) == [(1500, BW.SWAP_HOLD_END_WORDS[BW.SWAP_HOLD_END_BUSY])],
       "stages": len(so.stages_lines([BW.pin_log_stages(True, so.AWAY, 3, 400, 1, 9)])) == 1,
       "cache": len(so.cache_write_lines([BW.intent_cache_log_write(True, 352, 4, 351, 0, 9)])) == 1,
       "lane_word": "bounced to a reload of 351" in BW.swap_log_own_jump(True, 0, 352, 351, "bounce", "not-host", -1, 5, 9),
       "pass": len(so.pass_lines([BW.own_log_pass(True, 352, 351, BW.OWN_TERM_CACHE, 5, 9, 900)], "cache")) == 1,
       "usage": BW.SWAP_USAGE == FG.NETSYNC_SWAP_USAGE, "proof": FG.SWAP_PROOF_RE == BW.SWAP_PROOF_RE,
       "grace": [so.GRACE_MS, so.AUTO_READ_MS] == [2000, 2000], "fields": [so.HOME, so.AWAY, so.C_FIELD, so.C_DEST, so.P_FLAG] == [30801, 30602, 351, 352, 8720],
       "flag_safe": so.P_FLAG >= 8712}
''')
    assert all(out.values()), out


# ------------------------------------------------------------------------------------------------ the whole solo bench on the stand-in
_STAND_IN = r'''
import json, os, pathlib, sys, tempfile
sys.path.insert(0, %r)
sys.path.insert(0, %r)
from harness import Session
from harness import fakegame as FG
import coop_field_swap_timing as so
KEEPER_UID = 7
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
    t = pathlib.Path(d)
    (t / "x64").mkdir()
    (t / "x64" / "FF9.exe").write_bytes(b"MZ")
    (t / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (t / "FF9CustomMap").mkdir()
    (t / "FF9CustomMap" / "DictionaryPatch.txt").write_text(
        f"FieldScene {so.HOME} 31 JOURNAL JOURNAL {so.HOME}\nFieldScene {so.AWAY} 31 LOCKT2 LOCKT2 {so.AWAY}\n", encoding="utf-8")
    # REAL TIME (publish "mtime"): B compares its TickCount durations with swap-clock deltas (KIT-2's deviation 4)
    f = FG.FakeGame(t, walkmesh=(-2000.0, -3000.0, 2000.0, 2000.0), publish=("rt", "mtime"))
    # the keeper (a talk object near KEEPER_AT: `objects` names its uid) -- and the three stand-in gaps this child fills, in the engine's
    # words: a relayed talk opens the keeper's single-page line (`netsync talk` is a receipt there), the host's applied close logs
    # "closed (host seq N)" (NetSyncDialog :1410), and the proof block carries the dialogue selftest's OK line
    f.blockers[so.HOME] = [{"x": so.KEEPER_AT[0], "z": so.KEEPER_AT[1] - 90.0, "r": 30.0, "talk_r": 120.0, "coll": False, "uid": KEEPER_UID}]
    _ns0 = f._netsync
    def _ns_hook(args):
        _ns0(args)
        if args and str(args[0]).lower() == "talk" and f.field_id == so.HOME and f.last_talk_uid == KEEPER_UID:
            f.scene("The keeper's journal: a single page.")
    f._netsync = _ns_hook
    _hc0 = f._host_confirm
    def _hc_hook(index=None):
        w = f._guest.win
        e = f._guest.earliest(w["key"]) if w is not None else None
        key = (f.dialog_id, f.dialog_text_id)
        ok = _hc0(index)
        if ok and e is not None and not f._dialog_open():
            f._mlog(f"[NetSync] dialogue: win {key[0]} text {key[1]} closed (host seq {e.get('seq', 0)})")
        return ok
    f._host_confirm = _hc_hook
    _pf0 = f._step_selftest_proof
    def _pf_hook():
        if f._nb_role() and not f._proof_logged and f._selftest_in_scope():
            f._mlog("[NetSync] dialogue authority selftest: OK (the stand-in)")
        _pf0()
    f._step_selftest_proof = _pf_hook
    g = Session(game_path=t, run_dir=t / "run", save_dir=t / "player-saves", pid_probe=lambda: [], launcher=lambda exe: f.start(),
                boot_timeout=15.0, verbose=False)
    rows, notes = [], []
    g.check = lambda ok, what, detail="": (rows.append([what.split(":", 1)[0], bool(ok), str(detail)[:900]]), ok)[1]
    g.note = lambda text: notes.append(str(text)[:400])
    with g:
        so.run(g)
    print("@@" + json.dumps({"rows": rows, "notes": notes}))
''' % (str(REPO / "tools"), str(SCEN))

_KAB = ["K-PROOF", "K-REFUSE", "K-LEVER", "K-RELEASE", "A-FOLLOW", "A-STAMP", "A-WORD", "A-DELAY", "B-HOST", "B-HOLD", "B-RELEASE",
        "B-BLIP", "B-SCENE", "B-BLIP2", "B-CTLON"]


def _stand_in(runs: dict) -> dict:
    procs = {}
    for name, extra in runs.items():
        env = {k: v for k, v in os.environ.items() if k not in ("COOP_CALIBRATE", "COOP_LEGS")}
        env.update(extra)
        procs[name] = subprocess.Popen([sys.executable, "-X", "utf8", "-c", _STAND_IN], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, cwd=str(SCEN), env=env)
    out = {}
    for name, p in procs.items():
        so_, se = p.communicate(timeout=480)
        assert p.returncode == 0, (name, se[-3000:])
        doc = json.loads(next(ln for ln in so_.splitlines() if ln.startswith("@@"))[2:])
        out[name] = {"red": sorted(c for c, ok, _d in doc["rows"] if not ok), "all": [c for c, _ok, _d in doc["rows"]],
                     "detail": {c: d for c, _ok, d in doc["rows"]}, "notes": doc["notes"]}
    return out


def test_the_solo_bench_runs_green_on_the_stand_in_with_legs_kab():
    """The WHOLE solo bench (coop_field_swap_timing.run) on the s164 stand-in with COOP_LEGS=KAB -- the legs it models (P8): every row
    green, in the run's order; K-CLOCK GREEN on the stand-in's clock seam on Windows (its note; SKIP off Windows), never a ledger row."""
    out = _stand_in({"plain": {"COOP_LEGS": "KAB"}})["plain"]
    assert out["red"] == [], {k: out["detail"][k] for k in out["red"]}
    assert out["all"] == _KAB, out["all"]
    clock = [n for n in out["notes"] if n.startswith("K-CLOCK (a load-time precondition")]
    assert len(clock) == 1 and ("GREEN: src qpc" in clock[0] if os.name == "nt" else "SKIP:" in clock[0]), out["notes"]
    assert "every lever at rest ok" in out["detail"]["K-LEVER"] and "closed by line or window ok" in out["detail"]["A-FOLLOW"]


def test_the_stand_in_calibrates_stamps_delay_and_orphan_exactly():
    """On the stand-in, the three words it can carry calibrate EXACTLY: `stamps` (COOP_LEGS=KA) reds A-STAMP alone, `delay` (KA)
    A-DELAY alone, `orphan` (KB) B-HOLD, B-RELEASE, B-BLIP, B-BLIP2 and B-SCENE -- each with K-CAL-M (the marker) and K-CAL green."""
    out = _stand_in({"stamps": {"COOP_LEGS": "KA", "COOP_CALIBRATE": "stamps"}, "delay": {"COOP_LEGS": "KA", "COOP_CALIBRATE": "delay"},
                     "orphan": {"COOP_LEGS": "KB", "COOP_CALIBRATE": "orphan"}})
    want = {"stamps": ["A-STAMP"], "delay": ["A-DELAY"], "orphan": sorted(["B-HOLD", "B-RELEASE", "B-BLIP", "B-BLIP2", "B-SCENE"])}
    for w, reds in want.items():
        o = out[w]
        assert o["red"] == reds, (w, {k: o["detail"][k] for k in o["red"]})
        assert o["all"][-2:] == ["K-CAL-M", "K-CAL"] and "unpredicted reds: none" in o["detail"]["K-CAL"], (w, o["detail"].get("K-CAL"))


# ------------------------------------------------------------------------------------------------ the source tests (the engine build)
def _s164_patch() -> str:
    """The captured s164 patch text (every `memoria-patches/s164-*.patch`), or SKIP when none is on the stack yet."""
    found = sorted(PATCHES.glob("s164-*.patch"))
    if not found:
        pytest.skip("no memoria-patches/s164-*.patch captured yet (the engine side of s164 is built concurrently) -- re-run these "
                    "source tests after the engine build")
    return "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in found)


_HUNK = "\x00HUNK "                       # a hunk header in the post-image (git's function context after it)
_FILE = "\x00FILE "                       # a file header in the post-image (its path after it)


def _post(patch: str) -> list:
    """The patch's post-image lines (context and additions, the leading marker cut; removals dropped). Each file header is a sentinel
    ``_FILE + <path>`` and each hunk header ``_HUNK + <git's function context>``, so a method lookup never crosses into another hunk or
    file (both start with NUL: :func:`_boundary`)."""
    out = []
    for ln in patch.splitlines():
        if ln.startswith("@@"):
            out.append(_HUNK + (ln.split("@@", 2)[2].strip() if ln.count("@@") >= 2 else ""))
        elif ln.startswith("+++ "):
            out.append(_FILE + ln[4:].strip().removeprefix("b/"))
        elif ln.startswith(("---", "diff ", "index ", "new file", "deleted file", "similarity", "rename ")):
            out.append(_HUNK)
        elif ln.startswith("+") or ln.startswith(" "):
            out.append(ln[1:])
        elif ln == "":
            out.append("")
    return out


def _boundary(ln: str) -> bool:
    return ln.startswith("\x00")


def _section(lines: list, filename: str) -> list:
    """The post-image lines of the file(s) whose path ends with ``filename`` (another class's same-named method never answers)."""
    out, on = [], False
    for ln in lines:
        if ln.startswith(_FILE):
            on = ln[len(_FILE):].replace("\\", "/").endswith("/" + filename) or ln[len(_FILE):] == filename
        if on:
            out.append(ln)
    return out


_DECL = re.compile(r"^\s*(?:(?:public|internal|private|protected|static|override|unsafe|sealed|extern)\s+)+[\w<>\[\],.]+\s+(\w+)\s*\(")
_CTX = re.compile(r"\b(\w+)\s*\(")
_SELFTEST_HINTS = ("SelfTest", "Rows", "Row", "Mutant", "Test", "Lines", "Exemplar")


def _is_decl(ln: str):
    m = _DECL.match(ln)
    return m if m and not ln.rstrip().endswith(";") else None


def _method_body(lines: list, name: str) -> str | None:
    """The body of the C# method ``name`` in the post-image (its declaration line through its closing brace), or None."""
    for i, ln in enumerate(lines):
        m = _is_decl(ln)
        if m and m.group(1) == name:
            depth, body, started = 0, [], False
            for ln2 in lines[i:]:
                if _boundary(ln2) and started:
                    break
                body.append(ln2)
                depth += ln2.count("{") - ln2.count("}")
                started = started or "{" in ln2
                if started and depth <= 0:
                    break
            return "\n".join(body)
    return None


def _uncommented(body: str) -> str:
    """``body`` without its `//` comments (a comment's words are no literal)."""
    out = []
    for ln in body.splitlines():
        cut, in_str, i = len(ln), False, 0
        while i < len(ln):
            c = ln[i]
            if c == "\\" and in_str:
                i += 2
                continue
            if c == '"':
                in_str = not in_str
            elif not in_str and ln.startswith("//", i):
                cut = i
                break
            i += 1
        out.append(ln[:cut])
    return "\n".join(out)


def _gated_clear(lines: list, name: str, depth: int = 2) -> bool:
    """G2's shape: ``name``'s body -- or a method it calls, ``depth`` levels down -- runs `NetSyncParty.Clear()` under `_pinBenchMirror`
    (the flag read before the clear)."""
    body = _method_body(lines, name)
    if body is None:
        return False
    code = _uncommented(body)
    if "_pinBenchMirror" in code and "NetSyncParty.Clear()" in code and code.index("_pinBenchMirror") < code.index("NetSyncParty.Clear()"):
        return True
    if depth <= 0:
        return False
    callees = {m for m in _CTX.findall("\n".join(code.splitlines()[1:])) if m != name}
    return any(_gated_clear(lines, m, depth - 1) for m in sorted(callees) if _method_body(lines, m) is not None)


def _enclosing(lines: list, idx: int) -> str | None:
    """The method a post-image line sits in: the nearest declaration above it INSIDE its hunk, else the hunk header's git function
    context, else None (not determinable from the patch)."""
    for j in range(idx, -1, -1):
        if lines[j].startswith(_FILE):
            return None
        if lines[j].startswith(_HUNK):
            ctx = lines[j][len(_HUNK):]
            m = _is_decl(ctx) or _CTX.search(ctx)
            return m.group(1) if m else None
        m = _is_decl(lines[j])
        if m:
            return m.group(1)
    return None


def test_source_r8_the_host_holds_line_is_an_addition():
    """R8: the :7780 hunk ADDS `NetSyncSwap.HostHoldsNow = v.HostHoldsInput;` after the untouched `_glHostHoldsInput =
    v.HostHoldsInput;` (it feeds s156's GuestHostSceneWhy, s158's hostCtlOff and s163's hostHolds) -- never a replacement."""
    patch = _s164_patch()
    assert not any(ln.startswith("-") and "_glHostHoldsInput = v.HostHoldsInput;" in ln for ln in patch.splitlines()), "R8: removed"
    post = _post(patch)
    i = next((k for k, ln in enumerate(post) if "NetSyncSwap.HostHoldsNow = v.HostHoldsInput;" in ln), None)
    assert i is not None, "R8: the NetSyncSwap.HostHoldsNow line is missing"
    assert any("_glHostHoldsInput = v.HostHoldsInput;" in ln for ln in post[max(0, i - 3):i]), post[max(0, i - 3):i + 1]


def test_source_r9_i2_the_refusal_literal_and_its_one_printer():
    """R9: the refusal line's literal starts `[NetSync] own Field(` (no doubled prefix). I2: OwnFieldPass prints no own-jump line (its
    once-per-site fault line aside); NoteOwnJump is the single printer, and the refusal builder is called from NoteOwnJump (or the
    SelfTest's builder rows) only."""
    patch = _s164_patch()
    post = _post(patch)
    text = "\n".join(post)
    assert ('"[NetSync] own Field(" +' in text or '$"[NetSync] own Field({' in text), "R9: the refusal literal's head"
    assert " matches the host's announced field (" in text, "R9: the refusal literal"
    assert "[NetSync] [NetSync]" not in text and '"[NetSync] " + "[NetSync]' not in text, "R9: a doubled prefix"
    k_lit = next(k for k, ln in enumerate(post) if "matches the host's announced field (" in ln)
    builder = _enclosing(post, k_lit)
    assert builder, "I2: no method builds the refusal line"
    body = _method_body(post, "OwnFieldPass")
    assert body is not None, "I2: no OwnFieldPass in the patch"
    code = _uncommented(body)
    assert '"[NetSync] own Field(' not in code and not re.search(rf"\b{builder}\s*\(", code), "I2: OwnFieldPass must print no own-jump line"
    assert all("fault" in ln.lower() for ln in code.splitlines() if "Log.Message" in ln), "I2: OwnFieldPass logs only its fault"
    if builder != "NoteOwnJump":                     # the literal inside NoteOwnJump itself is the single printer by construction
        calls = [k for k, ln in enumerate(post) if re.search(rf"\b{builder}\s*\(", ln) and not _is_decl(ln)]
        where = {_enclosing(post, k) for k in calls}
        assert "NoteOwnJump" in where, (builder, where)
        assert all(w == "NoteOwnJump" or (w and any(h in w for h in _SELFTEST_HINTS)) for w in where), (builder, where)


def test_source_v1_v3_g2_the_split_the_selftest_tick_and_the_release():
    """V1: the :929 hunk reads `NetSyncState.ApplyStorySplit(story, party)`. V3: the selftest branch's `NetSyncSwap.GuestTick(fld, -1)`
    sits right after ServiceSpeed and before the branch's `if (!inScope)` return. G2: NetSyncSwap.HarnessRelease calls
    NetSyncParty.Clear() under `_pinBenchMirror`."""
    patch = _s164_patch()
    post = _post(patch)
    assert any("NetSyncState.ApplyStorySplit(story, party)" in ln for ln in post), "V1"
    i = next((k for k, ln in enumerate(post) if "NetSyncSwap.GuestTick(fld, -1)" in ln), None)
    assert i is not None, "V3: no selftest GuestTick(fld, -1)"
    hunk_start = max((k for k in range(i) if _boundary(post[k])), default=0)
    hunk = [ln for ln in post[hunk_start + 1:i] if ln.strip()]
    assert any("ServiceSpeed" in ln for ln in hunk[-3:]), ("V3: not right after ServiceSpeed", hunk[-3:])
    assert not any("if (!inScope)" in ln for ln in hunk), "V3: the inScope return precedes it"
    swap = _section(post, "NetSyncSwap.cs")
    assert _method_body(swap, "HarnessRelease") is not None, "G2: no NetSyncSwap.HarnessRelease in the patch"
    assert _gated_clear(swap, "HarnessRelease"), "G2: HarnessRelease (or its helper) must clear the party mirror under _pinBenchMirror"


def test_source_p8_the_call_sites_the_solo_legs_depend_on():
    """P8: the three call sites the solo legs C, P and L depend on exist: `NetSyncFollowFade.Ended(` (ServiceFollowWarp),
    `BenchPinLanding()` (ApplyStoryImpl) and the landing hook `NoteIntentLanding(<the loaded field>)` (ApplyStoryBeforeEvents: the design
    writes `fldMapNo`; the engine may pass a helper's read of it) -- each in its method when the patch shows it -- and the solo bench's
    matched words are the stack's (the proof head, the hold / end words, the cache / pin / life lines)."""
    patch = _s164_patch()
    post = _post(patch)
    text = "\n".join(post)
    for frag, method in (("NetSyncFollowFade.Ended(", "ServiceFollowWarp"), ("BenchPinLanding()", "ApplyStoryImpl"),
                         ("NoteIntentLanding(", "ApplyStoryBeforeEvents")):
        hits = [k for k, ln in enumerate(post) if frag in _uncommented(ln) and not _is_decl(ln)]
        assert hits, f"P8: no call {frag}"
        where = {_enclosing(post, k) for k in hits}
        assert method in where or None in where, (frag, method, where)
    for frag in ("field swap selftest: ", "held -- the host's control is off on my field", " -- the control hold ends after ",
                 "the host's control is back", "the host is busy (a scene or a line)", "[NetSync] intent cache: field ",
                 "[NetSync] story pin: field ", "[NetSync] transition intent ", "[NetSync] follow fade: ", "[NetSync] swap: "):
        assert frag in text, frag


# ================================================================================================ THE DUO (KIT-4)
# studies/test-harness/scenarios/coop_field_swap_timing_duo.py: two games through duo.py. Its children import the DUO first (it masks
# COOP_CALIBRATE / COOP_LEGS while it imports the solo bench as its `so`: a duo leg name is no solo leg), then bind `so = du.so` so the
# solo fixtures above (_FIX: S, ed, rec, block, bsim, L, P ...) build the duo's evidence in the engine's log and state shapes too.
def _run_duo_child(code: str, env_extra: dict | None = None, fix: bool = True) -> subprocess.CompletedProcess:
    full = ("import json, os, sys\nsys.path.insert(0, %r)\nsys.path.insert(0, %r)\n" % (str(SCEN), str(REPO / "tools"))
            + "import coop_field_swap_timing_duo as du\nso = du.so\nfrom harness import battlewire as BW\nfrom harness import fakegame as FG\n"
            + (_FIX + _DUO if fix else "") + code + "\nprint('@@' + json.dumps(OUT))\n")
    env = {k: v for k, v in os.environ.items() if k not in ("COOP_CALIBRATE", "COOP_LEGS")}
    env.update(env_extra or {})
    import tempfile                                      # the solo and duo fixtures together pass Windows' 32 KB command line:
    fd, path = tempfile.mkstemp(suffix=".py", prefix="duo_child_")   # the child runs from a file
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(full)
        return subprocess.run([sys.executable, "-X", "utf8", path], capture_output=True, text=True, cwd=str(SCEN), timeout=180, env=env)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _duo_child(code: str, env_extra: dict | None = None, fix: bool = True) -> dict:
    r = _run_duo_child(code, env_extra, fix)
    assert r.returncode == 0, r.stderr[-3000:]
    line = next(ln for ln in r.stdout.splitlines() if ln.startswith("@@"))
    return json.loads(line[2:])


_DUO = r'''
G_, R_, U_, V_ = du.G, du.R, du.U, du.V
STP = lambda on, t: BW.swap_stamp_text(on, t)


def Sx(t, field, ctl=True, sw=None, step=None, want=-1, leader=-1, texts=None, ui="FieldHUD", scene="FieldMap", **kw):
    """A duo sample: the solo's S() plus the keys the duo reads (stepout, dress.self / guard, dialog, ui_state, scene)."""
    s = S(t=t, field=field, ctl=ctl, sw=sw, **kw)
    s["netsync"]["stepout"] = {"active": False, "base": {"age_ms": -1}, "out_why": {"line": 0, "dwell": 0, "ate": 0}}
    for k, v in (step or {}).items():
        _put(s["netsync"]["stepout"], k, v)
    s["netsync"]["dress"]["self"] = {"want_char": want}
    s["netsync"]["dress"]["guard"] = {"leader": leader}
    s["dialog"] = {"open": bool(texts), "texts": list(texts or []), "choice": None}
    s["ui_state"], s["scene"] = ui, scene
    return s


def strip_all(lines):
    """A log as `stamps off` prints it: no stamp, no waited / shown tail (every builder's text otherwise)."""
    return [P + BW.swap_strip_line(so.core(ln))[0] for ln in lines]


DWELL_OUT = lambda f: L(f"[NetSync] step-out: OUT on field {f} (uid 1, undressed: the body stays; the host's ghost hides, my wire mask is 0) -- dwell")


# ---- CAL: one transition (the engine's blocks for each copy), the levers' effect on its fade
def cal_shape(sub, word):
    """(path, action, frames, by, due after the follow, ticks, delay) for a CAL sub-leg under ``word`` (the D+E twins' outputs)."""
    act = du.FADE_WORDS.get(word, "act")
    lever = {"CAL0": "old", "CAL1": "old", "ARRIVE": "act", "ARRIVE-OLD": "old"}.get(sub, act)
    speed = sub == "CAL3"
    delay = (0 if word == "delay" else du.CAL_DELAY_MS) if sub == "CAL1" else 0
    lv = {"act": BW.FADE_LEVER_ACT, "old": BW.FADE_LEVER_OLD, "long": BW.FADE_LEVER_LONG, "nogate": BW.FADE_LEVER_NOGATE}[lever]
    path = BW.fade_path_rule(False, lv, False, BW.FADE_VIEW_VISIBLE, BW.FADE_BK_NONE)
    action, frames = BW.fade_action_rule(path, BW.FADE_VIEW_VISIBLE, -1, lv)
    if path == BW.FADE_PATH_OLD:
        return "old", "wipe", frames, "timer", (300 if speed else 900), 27, delay
    # the D+E Prime: the first Update that reads black only primes, the next commits. At 1x (one tick a frame) black reads at
    # `frames` and the commit one tick later; at 3x (three ticks a frame) black reads at the first batch end >= `frames` (12) and
    # the commit one batch later (15), the solo F-3X fixture's value
    step = 3 if speed else 1
    ticks = -(-frames // step) * step + step
    return "fast", BW.FADE_ACT_NAMES[action], frames, "black", round((ticks * 1000 / 30) / step) + 10, ticks, delay


def cal_tr(i, sub, dest, word=None, kind=None, on=True, gate_out=True):
    T0 = 100000 * (i + 1)
    frm = du.HOME if dest != du.HOME else du.AWAY
    path, action, frames, by, due_after, ticks, delay = cal_shape(sub, word)
    life = word == "life"
    n = i % 256
    follow = T0 + 26
    due = follow + due_after
    commit = due + delay
    land = commit + 500
    hland = T0 + 450
    life_ms = 380 if life else 2150
    hi = {"active": False, "field": dest, "nonce": n, "site": None, "emit_t": T0, "first_sent_t": T0 + 5, "last_site": "debugwarp",
          "frames": 3 if life else 20, "landed_frames": 0 if life else 10, "updates": 2 if life else 60, "sends": 9 if life else 60,
          "oob": "sent", "end_t": T0 + life_ms, "last_end": "old" if life else "stands", "last_life_ms": life_ms}
    h = block(last__id=20 + i, last__nonce=n, last__state="done", last__close_why="window", last__land_via="host", last__emit_t=T0,
              last__land_t=hland, last__dest=dest, intent=hi)
    g = block(last__id=10 + i, last__nonce=n, last__state="done", last__close_why="window", last__land_via="follow", last__dest=dest,
              last__arrived_t=T0 + 20, last__seen_t=T0 + 25, last__follow_t=follow, last__follow_via="intent", last__due_t=due,
              last__commit_t=commit, last__land_t=land, last__follows=1, last__seen_copies=8 if life else 55, last__delay_ms=delay,
              seen__nonce=n, seen__first_t=T0 + 25, seen__last_t=T0 + 25 + (life_ms - 30 if life else 2100), counts__landings=i + 1,
              fade__last__field=dest, fade__last__path=path, fade__last__action=action, fade__last__frames=frames, fade__last__by=by,
              fade__last__ticks=ticks, fade__last__due_t=due, fade__last__ms=due_after)
    why = BW.INTENT_END_OLD if life else BW.INTENT_END_STANDS
    hl = [L(BW.life_log_ended(on, n, dest, life_ms, why, T0 + life_ms))]
    gl = [L(f"[NetSync] intent: following the peer to field {dest} (parallel)" + STP(on, follow))]
    out_ = kind == "gate" and gate_out
    if out_:
        gl.append(DWELL_OUT(dest))
    ov = {"gate": 1800, "control": 1250, "watch": 1300}.get(kind, 600)
    return {"lane": "CAL", "sub": sub, "kind": kind, "dest": dest, "from": frm, "h": h, "g": g, "hi": hi,
            "h0": block(last__id=20 + i - 1), "g0": block(last__id=10 + i - 1, counts__landings=i), "g_land_t": land, "h_land_t": hland,
            "h_ctl_t": land + ov, "overlap": ov, "base_peak": ov - 100, "dwell_count": 1 if out_ else 0, "active": out_, "dressed": False,
            "party_emit": [0, 1, 2, 3], "party_land": [0, 1, 2, 3], "mirror_after": [0, 1, 2, 3], "hl": hl, "gl": gl}


def cal_trs(word=None, on=True, gate_out=True):
    out, i = {}, 0
    for name, _fade, _delay, _speed, dest, k_out, k_home in du.cal_subs(word):
        for to, kind in ((dest, k_out), (du.HOME, k_home)):
            out.setdefault(name, []).append(cal_tr(i, name, to, word, kind, on, gate_out))
            i += 1
    return out


# ---- DESK + REST: one run's evidence (desk_evidence's shape)
def lines_run(t0, on=True):
    """DA-LINES' logs for one run: the host's taps for the desk lines, the guest's opened / queued / applied lines (waited and shown
    from the same stamps), plus an instrument and an s163 edge line on each."""
    hl, gl = [L("[NetSync] transition intent -> field 351 (nonce 3)" + STP(on, t0 - 3500))], []
    for k, text in enumerate(range(129, 140)):
        seq = 50 + k
        to = t0 + k * 2000
        th = to + 900
        tq = th + 40
        tc = tq + 400
        hl.append(L(f"[NetSync] dialog tap: win 3 text {text} kind 0 idx -1 page 0 closes seq {seq}" + STP(on, th)))
        gl.append(L(f"[NetSync] dialogue lock: win 3 text {text} opened locked (the host drives it)" + STP(on, to)))
        gl.append(L(f"[NetSync] dialogue: host seq {seq} queued (field 351 win 3 text {text} kind 0 page 0 closes)" + STP(on, tq)))
        gl.append(L(f"[NetSync] dialogue: win 3 text {text} closed (host seq {seq})" + BW.swap_waited_shown_text(on, tc, tq, to) + STP(on, tc)))
    gl.append(L("[NetSync] intent: following the peer to field 351 (parallel)" + STP(on, t0 - 3000)))
    x = BW.swap_log_landed(on, 351, BW.SWAP_VIA_OWN, 5, t0 - 2000)
    if x:
        gl.append(L(x))
    return {"hl": hl, "gl": gl}


def desk_fade(D, word):
    """The guest's fade.last on the 359 -> 351 follow (the copy's own FadeFilter(6,24) heading to black, or -- at D = 0.3 -- the copy
    lagging with a host close queued for its open line), through the D+E twins."""
    lv = {"act": BW.FADE_LEVER_ACT, "old": BW.FADE_LEVER_OLD, "long": BW.FADE_LEVER_LONG, "nogate": BW.FADE_LEVER_NOGATE}[du.FADE_WORDS.get(word, "act")]
    lag = D == du.PACE_D
    view, left, bk = (BW.FADE_VIEW_VISIBLE, -1, BW.FADE_BK_LINE) if lag else (BW.FADE_VIEW_HEADING, 10, BW.FADE_BK_NONE)
    path = BW.fade_path_rule(False, lv, False, view, bk)
    action, frames = BW.fade_action_rule(path, view, left, lv)
    pname, aname = BW.FADE_PATH_NAMES[path], BW.FADE_ACT_NAMES[action]
    if pname in ("old", "backlog"):
        by, ms = ("own" if not lag else "timer"), 905
    else:
        by, ms = ("own" if not lag else "black"), 410
    cur = ([0, 10, 20, 40, 60] if lag else [200, 216, 232, 248, 255])
    if aname == "wipe" and not lag:
        cur = [200, 0, 40, 80, 120, 160, 200, 248]              # FF9Wipe_FadeOutEx forces the screen visible first: the flash
    fl = {"field": 351, "path": pname, "action": aname, "frames": frames, "by": by, "due_t": -1, "ms": ms, "ticks": -1,
          "view_start": BW.FADE_VIEW_NAMES[view], "mode_start": "sub", "backlog_start": BW.FADE_BK_NAMES[bk], "primed": False,
          "left_start": left}
    return fl, cur


def desk_run(k, D, old, word=None, on=True):
    T = 5000000 + k * 1000000
    life = word == "life"
    fl, cur = desk_fade(D, word)
    lag = D == du.PACE_D
    hi_ = lambda t: {"field": 351, "nonce": 3, "site": None, "emit_t": t, "first_sent_t": t + 5, "last_site": "mapjump",
                     "frames": 3 if life else 30, "landed_frames": 0 if life else 20, "updates": 2 if life else 70,
                     "sends": 9 if life else 66, "oob": "sent", "last_end": "old" if life else "stands", "last_life_ms": 400 if life else 2200}
    def tr(lane, dest, frm, t, via="follow", own_t=-1, kind=None, copies=60):
        follow, due = t + 26, (t + 26 + 905 if via == "follow" else -1)
        commit = due
        land = (commit + 500) if via == "follow" else t + 700
        hland = t + 450
        h = block(last__id=40 + k, last__nonce=3, last__state="done", last__close_why="line", last__land_via="host", last__emit_t=t,
                  last__land_t=hland, last__dest=dest, intent=hi_(t))
        g = block(last__id=30 + k, last__nonce=3, last__state="done", last__close_why="line", last__land_via=via, last__dest=dest,
                  last__arrived_t=t + 20, last__seen_t=t + 25, last__follow_t=follow, last__due_t=due, last__commit_t=commit,
                  last__land_t=land, last__follows=1, last__seen_copies=8 if life else copies, last__own_t=own_t, last__own_dest=dest if own_t >= 0 else -1,
                  pin__last_use_quality="pre")
        return {"lane": lane, "sub": f"D{D}", "kind": kind, "dest": dest, "from": frm, "h": h, "g": g, "hi": hi_(t), "h0": {}, "g0": {},
                "g_land_t": land, "h_land_t": hland, "h_ctl_t": land + 200, "overlap": 200, "base_peak": 150, "dwell_count": 0,
                "active": False, "dressed": True, "party_emit": [0, 1, 2, 3], "party_land": [0, 1, 2, 3], "mirror_after": [0, 1, 2, 3],
                "hl": [], "gl": []}
    t359 = tr("DESK", 359, du.HOME, T)
    t359["hi"]["last_site"] = "debugwarp"
    t351 = tr("DESK", 351, 359, T + 60000, via="follow" if lag else "own", own_t=-1 if lag else T + 60000 + 60,
              kind="control-desk" if du.FADE_WORDS.get(word) == "old" else "watch-desk")
    t351["g"]["fade"]["last"] = dict(fl)
    t352 = tr("REST", 352, 351, T + 120000, via="own", own_t=T + 120000 + 200)
    g3, g0 = t352["g"], block(counts__bounces=0, own__passes=0, own__converted=0)
    maps = 1
    if old:
        if word == "own":
            g3 = dict(g3, last=dict(g3["last"], own_verdict="bounce", own_why="not-host", land_via="bounce"))
            g3["counts"] = dict(g3["counts"], bounces=1)
            maps = 2
        else:
            g3["last"] = dict(g3["last"], own_verdict="pass", own_why="pending")
            g3["own"] = dict(g3["own"], passes=1, converted=1, last=dict(g3["own"]["last"], term="pending"))
    else:
        g3["last"] = dict(g3["last"], own_verdict="pass", own_why="pending")
        g3["own"] = dict(g3["own"], passes=1, converted=1, last=dict(g3["own"]["last"], term="pending"))
    pre = Sx(T + 120000 + 150, 351, pending=352, sw={"own.host_lane": 351})
    commit_t = t351["g"]["last"]["commit_t"]
    return {"D": D, "old": old, "t359": t359, "t351": t351, "t352": t352,
            "fade": {"D": D, "fade": fl, "cur": cur, "commit_t": commit_t if commit_t >= 0 else None,
                     "last_close_t": (commit_t - 300) if commit_t >= 0 else None},
            "rest": {"D": D, "g": g3, "g0": g0, "maps": maps, "pre": pre, "l139": 150, "g_land_t": t352["g_land_t"],
                     "h_land_t": t352["h_land_t"]},
            "halt": {"g0": block(pin__pre_frames=4), "g": block(pin__pre_frames=6, pin__max_pre_diff=0)},
            "dress": {"want": 2, "leader": 2}, "lines": lines_run(T + 60000, on), "won": {"desk": (0, {}), "rest": (0, {})}}


# ---- CAT: the guest's 113 out of KIT-1's orphan stepper (bsim), the host's taps, the guest's later closes
def cat_ev(word=None, on=True, else_path=False):
    old = word == "orphan"
    key = du.CAT_FIRST
    s, gl, _c = bsim(key, [(0, "ctl", 0), (0, "scene", 0), (5200, "scene", 1), (5300, "adv", 1)], 6000, old)
    gs = [ed(x, sw={"own.host_lane": 351}, top={"field.id": 351}) for x in s]
    if else_path:                                        # 350's else path: text 118 listed before 113
        gs = [ed(x, ns={"windows": [{"win": 7, "text": 118, "cls": "locked"}]}) if so.now_ms(x) < 300 else x for x in gs]
    gl = [L("[NetSync] ATE relay: my copy's own Field(351) passes -- the host's pick (choice 3) on field 350 (my copy's own entrance)"
            + STP(on, 0))] + gl
    hl = []
    for k, text in enumerate(du.CAT_TEXTS):
        hl.append(L(f"[NetSync] dialog tap: win 7 text {text} kind 0 idx -1 page 0 closes seq {40 + k}" + STP(on, 5250 + 2000 * k)))
        if k:
            gl.append(L(f"[NetSync] dialogue: win 7 text {text} closed (host seq {40 + k})" + STP(on, 5300 + 2000 * k)))
    hs = [Sx(t, 351, ctl=False) for t in range(0, 6000, 200)]
    if not on:
        gl, hl = strip_all(gl), strip_all(hl)
    return {"gs": gs, "hs": hs, "gl": gl, "hl": hl, "closes0": so.nget(gs[0], "orphan_closes"), "closes1": so.nget(gs[-1], "orphan_closes"),
            "holds0": so.sget(gs[0], "orphan.holds"), "holds1": so.sget(gs[-1], "orphan.holds")}


# ---- MENU / MARK / LEFT / OPEN / OWN / LEVERS
MC = 9000000


def menu_ev(word=None, aged=False):
    if aged:
        return {"g": block(last__follow_via="intent", last__follow_t=MC + 3550, pin__last_use="aged", pin__last_use_quality="pre",
                           pin__last_use_age_ms=3100), "menu_close_t": MC + 3500, "flag": True}
    if word == "life":
        g = block(last__follow_via="serial", last__follow_t=MC + 1300, pin__last_use="none", pin__last_use_quality="none")
        return {"g": g, "menu_close_t": MC, "flag": True}
    lever = word == "pin"
    g = block(last__follow_via="intent", last__follow_t=MC + 60, last__land_t=MC + 600, pin__last_use="lever" if lever else "pin",
              pin__last_use_quality="pre", pin__last_use_age_ms=1300, pin__last_diff=1, pin__late=0)
    return {"g": g, "menu_close_t": MC, "flag": lever}


def mark_ev(word=None, on=True):
    LT = 9500000
    lever = word == "pin"
    g = block(last__land_t=LT, pin__last_use="lever" if lever else "pin", pin__last_use_quality="pre", pin__last_diff=1)
    gl = [] if lever else [L(BW.pin_log_stages(on, du.AWAY, 5, 900, 1, LT))]
    return {"g": g, "flag": lever, "host_flag_t": LT - 700, "gl": gl, "dest": du.AWAY}


def left_ev(on=True):
    S0 = 9800000
    return {"h": block(intent__nonce=7, intent__last_end="left", intent__end_t=S0), "g": block(seen__nonce=7, seen__last_t=S0 + 90),
            "hl": [L(BW.life_log_ended(on, 7, du.AWAY, 1100, BW.INTENT_END_LEFT, S0))], "dest": du.AWAY, "start_t": S0}


def open_ev(word=None):
    lever = du.FADE_WORDS.get(word, "act")
    fl = {"backlog_start": "open", "path": "backlog", "by": "timer", "ms": 905}
    if lever == "old":
        fl = dict(fl, path="old")
    elif lever == "nogate":
        fl = dict(fl, path="fast", by="black", ms=410)
    return {"refused": None, "fade": fl}


LVD = {"guest_life": "the game refused a step: netsync: " + BW.swap_refusal_host_side("life"),
       "host_orphan": "the game refused a step: netsync: " + BW.swap_refusal_guest_side("orphan"),
       "host_hostctl": "the game refused a step: netsync: " + BW.swap_refusal_selftest("hostctl"),
       "guest_hostctl": "the game refused a step: netsync: " + BW.swap_refusal_selftest("hostctl")}


def duo_rows(word=None, clock_ok=True, gate_out=True):
    """Every duo row's (status, detail) on the engine's evidence under ``word`` (None: the plain run), and each row's marker evidence."""
    on = word != "stamps"
    cal = cal_trs(word, on, gate_out)
    flat = [t for k in ("CAL0", "CAL1", "CAL2", "CAL3") for t in cal[k]]
    allc = [t for k in cal for t in cal[k]]
    desk = [desk_run(k, D, old, word, on) for k, (D, old) in enumerate(du.desk_runs(word))]
    arrivals = [du.arrival_of(t, t["kind"]) for t in allc if t["kind"]] + [du.arrival_of(r["t351"], r["t351"]["kind"]) for r in desk]
    lane = allc + [t for r in desk for t in (r["t359"], r["t351"], r["t352"])]
    cat, menu, mark = cat_ev(word, on), menu_ev(word), mark_ev(word, on)
    fades = [r["fade"] for r in desk]
    pace = [r["fade"] for r in desk if r["D"] == du.PACE_D]
    restold = [r["rest"] for r in desk if r["old"]]
    rows = {
        "DA-LANE": du.judge_da_lane(lane, du.LANE_LABELS, clock_ok),
        "DA-CAL": du.judge_da_cal([t["g"] for t in cal["CAL0"]], [t["g"] for t in cal["CAL1"]], 33.0),
        "DA-JOIN": du.judge_da_join(flat), "DL-LIFE": du.judge_dl_life(flat), "DL-NOREG": du.judge_dl_noreg(flat),
        "DC-FE": du.judge_dc_fe([ln for t in flat for ln in t["gl"]], block(own__passes=0), block(own__passes=0)),
        "DF-FAST": du.judge_df_fast(cal["CAL2"], cal["CAL0"], clock_ok), "DF-3X": du.judge_df_3x(cal["CAL3"]),
        "DA-ARRIVE": du.judge_da_arrive(arrivals, clock_ok),
        "DA-LINES": du.judge_da_lines([r["lines"] for r in desk], clock_ok), "DF-FLASH": du.judge_df_flash(fades),
        "DF-GRACE": du.judge_df_grace(fades), "DF-PACE": du.judge_df_pace(pace),
        "DA-PROBE": du.judge_da_probe([t for r in desk for t in (r["t351"], r["t352"])], life_old=word == "life"),
        "DC-B(a)": du.judge_dc_b_a([r["rest"] for r in desk if not r["old"]], clock_ok), "DC-B(b)": du.judge_dc_b_b(restold),
        "DP-HALT": du.judge_dp_halt([r["halt"] for r in desk]), "DP-DRESS": du.judge_dp_dress([r["dress"] for r in desk]),
        "DB-SHAPE": du.judge_db_shape(cat), "DB-BIT": du.judge_db_bit(cat, clock_ok), "DB-HOLD": du.judge_db_hold(cat),
        "DB-ORDER": du.judge_db_order(cat),
        "DC-OWN": du.judge_dc_own({"g": block(last__own_verdict="ate", last__own_why="ate"), "gl": [L("Map: 450 (Dali/Field)")]}),
        "DL-DEFER": du.judge_dl_defer(menu, 33.0), "DP-DEFER": du.judge_dp_defer(menu, life_word=word == "life"),
        "DP-AGED": du.judge_dp_aged(menu_ev(word, aged=True)), "DP-MARK": du.judge_dp_mark(mark, clock_ok),
        "DL-LEFT": du.judge_dl_left(left_ev(on), clock_ok), "DF-OPEN": du.judge_df_open(open_ev(word)),
        "DP-PARTY": du.judge_dp_party(lane), "LVD-ROLE": du.judge_lvd_role(LVD),
        "LVD-LIFE": du.judge_lvd_life(True, {"life": "old"}, {"life": None}),
    }
    marks = {"DA-LINES": {"runs": [r["lines"] for r in desk]}, "DA-CAL": {"cal1": [t["g"] for t in cal["CAL1"]], "frame": 33.0},
             "DB-HOLD": cat, "DB-ORDER": cat, "DC-B(b)": {"runs": restold}, "DP-MARK": mark, "DP-DEFER": menu,
             "DL-LIFE": {"intents": [t["hi"] for t in flat]}, "DL-DEFER": menu,
             "DF-FAST": {"fades": [{"fade": t["g"]["fade"]["last"]} for t in cal["CAL2"]]},
             "DF-3X": {"fades": [{"fade": t["g"]["fade"]["last"]} for t in cal["CAL3"]]},
             "DF-FLASH": {"fades": fades}, "DF-PACE": {"fades": pace}, "DF-OPEN": {"fades": [{"fade": open_ev(word)["fade"]}]}}
    return rows, marks


def sets(rows):
    st = {r: v[0] for r, v in rows.items()}
    return ({r for r, s in st.items() if s in (R_, V_)}, {r for r, s in st.items() if s == V_}, {r for r, s in st.items() if s == U_},
            sorted(r for r, s in st.items() if s == R_ and r not in du.BASELINE_RED))
'''


def test_duo_refuses_unknown_words_and_legs_at_load():
    """The duo reads COOP_CALIBRATE and COOP_LEGS AT LOAD (duo.py imports the scenario before it boots the pair): '' / 0 none, each
    registered duo word itself; an unknown word, an unknown leg, or a word whose legs COOP_LEGS leaves out exits the IMPORT (code 1,
    nothing run) with the refusal -- never mapped to a lever. REST is DESK's alias; the solo bench's own load checks never see the duo's
    environment (a duo leg name is no solo leg)."""
    cases = {}
    for v in ("", "0") + tuple(["stamps", "delay", "orphan", "own", "nocache", "pin", "life", "fade", "long", "nogate"]):
        cases[v] = _duo_child(r'''
OUT = {"mode": du.CAL_MODE, "rows": sorted(k for k in du.catalog(du.CAL_MODE, du.LEGS_SEL) if k.startswith("D-CAL")),
       "solo_mode": so.CAL_MODE, "solo_legs": so.LEGS_SEL}
''', {"COOP_CALIBRATE": v}, fix=False)
    assert cases[""]["mode"] is None and cases["0"]["mode"] is None and cases[""]["rows"] == []
    for v, c in cases.items():
        assert c["solo_mode"] is None and c["solo_legs"] == "KABCPLF", (v, c)
        if v not in ("", "0"):
            assert c["mode"] == v and c["rows"] == ["D-CAL", "D-CAL-M"], (v, c)
    for env in ({"COOP_CALIBRATE": "s163"}, {"COOP_CALIBRATE": "1"}, {"COOP_CALIBRATE": "norecheck"}, {"COOP_CALIBRATE": "nohurry"},
                {"COOP_LEGS": "CAL,BOGUS"}, {"COOP_LEGS": "K"}, {"COOP_CALIBRATE": "fade", "COOP_LEGS": "CAT"},
                {"COOP_CALIBRATE": "orphan", "COOP_LEGS": "CAL,DESK"}, {"COOP_CALIBRATE": "own", "COOP_LEGS": "CAL"}):
        r = _run_duo_child("OUT = {}", env, fix=False)
        assert r.returncode == 1 and "coop_field_swap_timing_duo: COOP_" in r.stderr and "before the pair boots" in r.stderr, (env, r.stderr[-600:])
        assert "@@" not in r.stdout
    ok = _duo_child(r'''OUT = {"legs": du.LEGS_SEL, "cat": sorted(du.catalog(du.CAL_MODE, du.LEGS_SEL))}''',
                    {"COOP_LEGS": "rest, cat", "COOP_CALIBRATE": "orphan"}, fix=False)
    assert ok["legs"] == "DESK,CAT" and "DB-HOLD" in ok["cat"] and "DA-LANE" in ok["cat"] and "DA-CAL" not in ok["cat"], ok


def test_duo_catalog_words_and_the_arrive_field_are_the_registered_ones():
    """The catalog is the design's duo table (every row id, DK-CLOCK / DC-WON / DA-PROBE-X reported as notes, never rows), the ten words
    red exactly the design's rows, and the ARRIVE field is a scratch copy of LOCKT2 with `[camera] entry_settle = 68` at a dev-scratch
    id outside 30602 and the world-map hole, deployed with that explicit id (deploy_argv) and never inside a run."""
    out = _duo_child(r'''
import inspect, tomllib
cat = du.catalog(None, du.LEGS_SEL)
arr = tomllib.loads((du.REPO / du.ARRIVE_TOML).read_text(encoding="utf-8"))
base = tomllib.loads((du.REPO / "studies/movement/bench/lockt2.field.toml").read_text(encoding="utf-8"))
argv = du.deploy_argv("py")
run_src = "".join(inspect.getsource(f) for f in (du.run_duo, du._run, du._leg_cal, du._leg_desk, du._desk_run, du._leg_cat,
                                                du._leg_own, du._leg_menu, du._menu_run, du._leg_mark, du._leg_left, du._leg_open,
                                                du._leg_levers))
OUT = {"rows": sorted(cat), "words": {w: [list(v[1]), list(v[2])] for w, v in du.WORDS.items()}, "reported": list(du.REPORTED),
       "id": du.ARRIVE_ID, "toml_id": arr["field"]["id"], "settle": arr["camera"].get("entry_settle"),
       "base_settle": base["camera"].get("entry_settle", "auto"),
       "same_rest": {k: arr[k] == base[k] for k in ("walkmesh", "player", "event", "prop", "cutscene", "npc", "encounter")},
       "argv": argv[2:], "cmd": du.deploy_command(), "no_deploy_in_run": "deploy_argv(" not in run_src and "subprocess" not in run_src,
       "legs_rows": sorted(r for rows in du.LEG_ROWS.values() for r in rows) + ["DA-LANE", "DP-PARTY"]}
''')
    want_rows = ["DA-ARRIVE", "DA-CAL", "DA-JOIN", "DA-LANE", "DA-LINES", "DA-PROBE", "DB-BIT", "DB-HOLD", "DB-ORDER", "DB-SHAPE",
                 "DC-B(a)", "DC-B(b)", "DC-FE", "DC-OWN", "DF-3X", "DF-FAST", "DF-FLASH", "DF-GRACE", "DF-OPEN", "DF-PACE", "DL-DEFER",
                 "DL-LEFT", "DL-LIFE", "DL-NOREG", "DP-AGED", "DP-DEFER", "DP-DRESS", "DP-HALT", "DP-MARK", "DP-PARTY", "LVD-LIFE",
                 "LVD-ROLE"]
    assert out["rows"] == want_rows and sorted(out["legs_rows"]) == want_rows, out["rows"]
    assert out["reported"] == ["DK-CLOCK", "DC-WON", "DA-PROBE-X"]
    assert out["words"] == {"stamps": [["DA-LINES"], []], "delay": [["DA-CAL"], []], "orphan": [["DB-HOLD", "DB-ORDER"], []],
                            "own": [["DC-B(b)"], []], "nocache": [[], []], "pin": [["DP-MARK", "DP-DEFER"], []],
                            "life": [["DL-LIFE", "DL-DEFER"], []], "fade": [["DF-FAST", "DF-3X", "DF-FLASH", "DF-OPEN"], ["DF-PACE"]],
                            "long": [["DF-FAST", "DF-3X"], []], "nogate": [["DF-OPEN"], ["DF-PACE"]]}, out["words"]
    assert out["id"] == out["toml_id"] and 30000 <= out["id"] <= 32767 and out["id"] != 30602, out
    assert out["settle"] == 68 and out["base_settle"] == "auto" and all(out["same_rest"].values()), out
    assert out["argv"] == [str(REPO / "studies/movement/bench/lockt2-arrive.field.toml"), "--id", str(out["id"]), "--mod-folder",
                           "FF9CustomMap-msgs"], out["argv"]
    assert f"--id {out['id']}" in out["cmd"] and out["no_deploy_in_run"], out


def test_dk_clock_voids_every_cross_game_row_and_rows_inside_one_game_still_judge():
    """DK-CLOCK unfit (K-CLOCK failing on either game): DA-LANE, DB-BIT, DP-MARK, DL-LEFT and DA-ARRIVE read VOID with the reason, never
    red; DF-FAST and DC-B(a) lose only their cross-game gap clause, DA-LINES only its host-tap clause; every row inside one game judges
    as before. On a fit clock the plain evidence is green but for the pre-registered DA-ARRIVE defect."""
    out = _duo_child(r'''
fit, _m = duo_rows()
unfit, _m2 = duo_rows(clock_ok=False)
OUT = {"fit": {r: v[0] for r, v in fit.items()}, "unfit": {r: v[0] for r, v in unfit.items()},
       "why": unfit["DA-LANE"][1], "fast": unfit["DF-FAST"][1]}
''')
    fit, unfit = out["fit"], out["unfit"]
    assert sorted(r for r, s in fit.items() if s == "red") == ["DA-ARRIVE"], fit
    assert not [r for r, s in fit.items() if s == "void"], fit
    assert sorted(r for r, s in unfit.items() if s == "void") == ["DA-ARRIVE", "DA-LANE", "DB-BIT", "DL-LEFT", "DP-MARK"], unfit
    for r in ("DF-FAST", "DC-B(a)", "DA-LINES", "DA-CAL", "DB-HOLD", "DP-DEFER"):
        assert unfit[r] == fit[r], (r, unfit[r], fit[r])
    assert "DK-CLOCK" in out["why"] and "never red" in out["why"] and "VOID: DK-CLOCK unfit (the gap clause)" in out["fast"], out


def test_da_lane_reads_each_transition_and_holds_its_reach_floor():
    """DA-LANE: the order per transition (an own pass that won needs no commit), a transition with arrived_t -1 or no first send is
    UNREACHED for itself, and each of CAL, DESK and REST needs one reached transition -- else red 'not reached: arrived_t was -1 on every
    transition', with reached / total in the detail (P8). Each part alone is red."""
    out = _duo_child(r'''
rows, _m = duo_rows()
cal = [t for v in cal_trs().values() for t in v]
desk = [desk_run(k, D, old) for k, (D, old) in enumerate(du.desk_runs(None))]
lane = cal + [t for r in desk for t in (r["t359"], r["t351"], r["t352"])]
import copy
def edit(trs, pred, **kw):
    out = []
    for t in trs:
        t = copy.deepcopy(t)
        if pred(t):
            for k, v in kw.items():
                (t["hi"] if k == "first_sent_t" else t["g"]["last"])[k] = v
        out.append(t)
    return out
j = lambda L: du.judge_da_lane(L, du.LANE_LABELS)
one_unreached = edit(lane, lambda t: t["lane"] == "CAL" and t["sub"] == "CAL0" and t["dest"] == du.AWAY, arrived_t=-1)
no_rest = edit(lane, lambda t: t["lane"] == "REST", arrived_t=-1)
no_send = edit(lane, lambda t: t["lane"] == "DESK", first_sent_t=-1)
order = edit(lane, lambda t: t["lane"] == "CAL" and t["sub"] == "CAL2", seen_t=10 ** 9)
no_commit = edit(lane, lambda t: t["lane"] == "CAL" and t["sub"] == "CAL1", commit_t=-1)
OUT = {"plain": [rows["DA-LANE"][0], j(lane)[0]], "one_unreached": j(one_unreached)[0], "no_rest": list(j(no_rest)),
       "no_send": j(no_send)[0], "order": j(order)[0], "no_commit": j(no_commit)[0],
       "own_pass_no_commit": [t["g"]["last"]["commit_t"] for t in lane if t["g"]["last"]["land_via"] == "own"][:1]}
''')
    assert out["plain"] == ["green", "green"] and out["one_unreached"] == "green", out
    assert out["no_rest"][0] == "red" and out["no_rest"][1].startswith("not reached: arrived_t was -1 on every transition of REST"), out
    assert "REST 0/6" in out["no_rest"][1], out
    assert out["no_send"] == "red" and out["order"] == "red" and out["no_commit"] == "red", out
    assert out["own_pass_no_commit"] == [-1], out


def test_da_arrive_must_reach_its_exposure_and_judges_every_arrival_kind():
    """DA-ARRIVE: the ARRIVE gate must REACH its exposure -- the overlap >= DwellMs + 100 AND the guest's peak
    netsync.stepout.base.age_ms >= DwellMs (each alone falls short: red 'not reached', never green); a reached gate with no dwell OUT is
    green (the arrival guard), with one red (round 1's pre-registered defect); a fade-old control's OUT is red; an undressed watch is not
    judged, a dressed one is; on DESK an OUT by line (stepout.active) is lawful, a dwell OUT is not."""
    out = _duo_child(r'''
A = lambda kind, ov=1800, bp=1700, lines=0, cnt=0, active=False, dressed=False: {"kind": kind, "sub": "x", "dest": 1, "overlap": ov,
    "base_peak": bp, "dwell_lines": lines, "dwell_count": cnt, "active": active, "dressed": dressed}
j = lambda *a: du.judge_da_arrive(list(a))
ctl = A("control", 1250, 1200)
OUT = {"guard": j(A("gate"), ctl)[0], "defect": j(A("gate", lines=1, cnt=1, active=True), ctl)[0],
       "overlap_short": list(j(A("gate", ov=1599), ctl)), "base_short": j(A("gate", bp=1499), ctl)[0], "no_gate": j(ctl)[0],
       "base_absent": j(A("gate", bp=None), ctl)[0],
       "control_out": j(A("gate"), A("control", 1250, 1200, cnt=1))[0],
       "watch_undressed": j(A("gate"), ctl, A("watch", cnt=1))[0], "watch_dressed": j(A("gate"), ctl, A("watch", cnt=1, dressed=True))[0],
       "desk_line_out": j(A("gate"), ctl, A("watch-desk", active=True, dressed=True))[0],
       "desk_dwell": j(A("gate"), ctl, A("watch-desk", lines=1, dressed=True))[0],
       "control_desk_line": j(A("gate"), ctl, A("control-desk", active=True))[0],
       "reached": [du.arrive_reached(A("gate")), du.arrive_reached(A("gate", ov=1600, bp=1500)), du.arrive_reached(A("gate", ov=1599))],
       "constants": [du.DWELL_MS, du.ARRIVE_MARGIN_MS, du.ARRIVE_SETTLE_TICKS]}
''')
    assert out.pop("constants") == [1500, 100, 68] and out.pop("reached") == [True, True, False], out
    assert out.pop("guard") == "green" and out.pop("watch_undressed") == "green" and out.pop("desk_line_out") == "green", out
    assert out.pop("control_desk_line") == "green", out
    assert out["overlap_short"][0] == "red" and out["overlap_short"][1].startswith("not reached: ARRIVE at act"), out
    out.pop("overlap_short")
    assert all(v == "red" for v in out.values()), out


def test_cal_judges_can_go_red_on_each_part():
    """DA-CAL (CAL1's +200 within a frame), DA-JOIN (ids, nonce, vias, closes), DL-LIFE (the seen span and the host's 'I stand on it'),
    DL-NOREG (one follow line / commit / landing, no cancel), DC-FE (no own Field() line, passes +0), DF-FAST (fast / fade / 12 by
    black, 0.35-0.60 s, the landing-gap gain) and DF-3X (ticks 12-17, <= 0.22 s; CAL3 reads 15 at 3x, the Prime's one 3-tick frame):
    green on the plain evidence, each part alone red."""
    out = _duo_child(r'''
import copy
cal = cal_trs()
flat = [t for k in ("CAL0", "CAL1", "CAL2", "CAL3") for t in cal[k]]
def mod(trs, i, path, v, where="g"):
    trs = copy.deepcopy(trs)
    d = trs[i][where]
    ks = path.split(".")
    for k in ks[:-1]:
        d = d[k]
    d[ks[-1]] = v
    return trs
g1 = [t["g"] for t in cal["CAL1"]]
c0 = [t["g"] for t in cal["CAL0"]]
OUT = {"good": [du.judge_da_cal(c0, g1, 33.0)[0], du.judge_da_join(flat)[0], du.judge_dl_life(flat)[0], du.judge_dl_noreg(flat)[0],
                du.judge_df_fast(cal["CAL2"], cal["CAL0"])[0], du.judge_df_3x(cal["CAL3"])[0],
                du.judge_dc_fe([], block(own__passes=2), block(own__passes=2))[0]],
       "bad": {
           "cal_off_frame": du.judge_da_cal(c0, [mod(cal["CAL1"], 0, "last.commit_t", g1[0]["last"]["commit_t"] + 40)[0]["g"]] + g1[1:], 33.0)[0],
           "cal_none": du.judge_da_cal(c0, [], 33.0)[0],
           "join_id": du.judge_da_join(mod(flat, 2, "last.id", 99))[0],
           "join_nonce": du.judge_da_join(mod(flat, 2, "last.nonce", 200))[0],
           "join_via": du.judge_da_join(mod(flat, 2, "last.land_via", "same"))[0],
           "join_host_via": du.judge_da_join(mod(flat, 2, "last.land_via", "follow", "h"))[0],
           "join_close": du.judge_da_join(mod(flat, 2, "last.close_why", "next"))[0],
           "join_open": du.judge_da_join(mod(flat, 2, "last.state", "landed"))[0],
           "life_span": du.judge_dl_life(mod(flat, 1, "seen.last_t", flat[1]["g"]["seen"]["first_t"] + 500))[0],
           "life_nonce": du.judge_dl_life(mod(flat, 1, "seen.nonce", 201))[0],
           "life_line": du.judge_dl_life([dict(flat[0], hl=[])] + flat[1:])[0],
           "noreg_two_lines": du.judge_dl_noreg([dict(flat[0], gl=flat[0]["gl"] * 2)] + flat[1:])[0],
           "noreg_follows": du.judge_dl_noreg(mod(flat, 0, "last.follows", 2))[0],
           "noreg_cancel": du.judge_dl_noreg([dict(flat[0], gl=flat[0]["gl"] + [L("[NetSync] follow-warp to field 30602 cancelled: this load already landed on it (no second load)")])] + flat[1:])[0],
           "noreg_landings": du.judge_dl_noreg(mod(flat, 0, "counts.landings", 5))[0],
           "fe_line": du.judge_dc_fe([L("[NetSync] own Field(30602) passes on field 250 -- the host's announced field (intent)")], block(), block())[0],
           "fe_passes": du.judge_dc_fe([], block(own__passes=0), block(own__passes=1))[0],
           "fast_path": du.judge_df_fast(mod(cal["CAL2"], 0, "fade.last.path", "backlog"), cal["CAL0"])[0],
           "fast_frames": du.judge_df_fast(mod(cal["CAL2"], 0, "fade.last.frames", 24), cal["CAL0"])[0],
           "fast_by": du.judge_df_fast(mod(cal["CAL2"], 0, "fade.last.by", "fallback"), cal["CAL0"])[0],
           "fast_slow": du.judge_df_fast(mod(cal["CAL2"], 0, "last.commit_t", cal["CAL2"][0]["g"]["last"]["follow_t"] + 700), cal["CAL0"])[0],
           "fast_gain": du.judge_df_fast(cal["CAL2"], cal["CAL2"])[0],
           "3x_ticks": du.judge_df_3x(mod(cal["CAL3"], 0, "fade.last.ticks", 24))[0],
           "3x_high": du.judge_df_3x(mod(cal["CAL3"], 0, "fade.last.ticks", 18))[0],
           "3x_low": du.judge_df_3x(mod(cal["CAL3"], 0, "fade.last.ticks", 11))[0],
           "3x_slow": du.judge_df_3x(mod(cal["CAL3"], 1, "last.commit_t", cal["CAL3"][1]["g"]["last"]["follow_t"] + 300))[0],
           "3x_none": du.judge_df_3x([])[0],
           # THE REACH RULE: a transition whose fade.last is not past its first guest sample's (a leftover record) is never green
           "fast_stale": du.judge_df_fast(mod(cal["CAL2"], 0, "fade.last.due_t", cal["CAL2"][0]["g"]["fade"]["last"]["due_t"], where="g0"), cal["CAL0"])[0],
           "3x_stale": du.judge_df_3x(mod(cal["CAL3"], 0, "fade.last.due_t", cal["CAL3"][0]["g"]["fade"]["last"]["due_t"], where="g0"))[0]},
       "cal3_ticks": [t["g"]["fade"]["last"]["ticks"] for t in cal["CAL3"]], "window": list(du.DF_3X_TICKS),
       "edge": [du.judge_df_3x(mod(cal["CAL3"], 0, "fade.last.ticks", v))[0] for v in (12, 17)]}
''')
    assert out["good"] == ["green"] * 7, out
    assert all(v == "red" for v in out["bad"].values()), out["bad"]
    assert out["cal3_ticks"] == [15, 15] and out["window"] == [12, 17], out        # the real 3x value, inside DF-3X (== solo F-3X)
    assert out["edge"] == ["green", "green"], out


def test_desk_judges_can_go_red_on_each_part_and_read_unreached_as_never_red():
    """DA-LINES (every edge line stamped; tap <= queued <= closed; waited; shown), DF-FLASH / DF-GRACE / DF-PACE (each REACHED by its
    own clause and UNREACHED -- never red -- otherwise), DA-PROBE (a non-mapjump site refused; each consistency clause; the life
    clauses recorded, not judged, under `life`), DC-B(a) (the C2 shape not judged; an unread L139 VOID; loads, bounces, the gap),
    DC-B(b), DP-HALT, DP-DRESS."""
    out = _duo_child(r'''
import copy
desk = [desk_run(k, D, old) for k, (D, old) in enumerate(du.desk_runs(None))]
runs = [r["lines"] for r in desk]
fades = [r["fade"] for r in desk]
pace = [r["fade"] for r in desk if r["D"] == du.PACE_D]
probe = [t for r in desk for t in (r["t351"], r["t352"])]
rest = [r["rest"] for r in desk if not r["old"]]
rold = [r["rest"] for r in desk if r["old"]]
def fl(F, **kw):
    return [dict(f, fade=dict(f["fade"], **kw)) for f in F]
def hi(T, **kw):
    return [dict(t, hi=dict(t["hi"], **kw)) for t in T]
def last(R, **kw):
    out = copy.deepcopy(R)
    for r in out:
        r["g"]["last"].update(kw)
    return out
r0 = runs[0]
unstamped = [{"hl": r0["hl"], "gl": r0["gl"][:-2] + strip_all(r0["gl"][-2:])}]
shifted = [{"hl": [ln.replace("(t ", "(t 9") if "dialog tap" in ln else ln for ln in r0["hl"]], "gl": r0["gl"]}]
waited = [{"hl": r0["hl"], "gl": [ln.replace(" -- waited 400 ms", " -- waited 407 ms") for ln in r0["gl"]]}]
shown = [{"hl": r0["hl"], "gl": [ln for ln in r0["gl"] if "opened locked" not in ln]}]
OUT = {"good": [du.judge_da_lines(runs)[0], du.judge_df_flash(fades)[0], du.judge_df_grace(fades)[0], du.judge_df_pace(pace)[0],
                du.judge_da_probe(probe)[0], du.judge_dc_b_a(rest)[0], du.judge_dc_b_b(rold)[0],
                du.judge_dp_halt([r["halt"] for r in desk])[0], du.judge_dp_dress([r["dress"] for r in desk])[0],
                du.judge_da_lines(shifted, clock_ok=False)[0]],
       "unreached": [du.judge_df_flash(fl(fades, view_start="visible"))[0], du.judge_df_grace(fl(fades, action="hurry"))[0],
                     du.judge_df_pace(fl(pace, backlog_start="none"))[0], du.judge_dc_b_b(last(rold, own_t=-1))[0],
                     du.judge_dp_halt([{"g0": block(pin__pre_frames=3), "g": block(pin__pre_frames=3, pin__max_pre_diff=0)}])[0],
                     du.judge_df_grace(fl(fades, left_start=13, view_start="heading"))[0]],
       "void": [du.judge_dc_b_a(last(rest, seen_t=10 ** 9))[0], du.judge_dc_b_a([dict(r, l139=None) for r in rest])[0],
                du.judge_dp_dress([{"want": -1, "leader": 2}])[0]],
       "life_ok": du.judge_da_probe(hi(probe, last_end="old", landed_frames=0), life_old=True)[0],
       "bad": {"lines_unstamped": du.judge_da_lines(unstamped)[0], "lines_tap_after_queue": du.judge_da_lines(shifted)[0],
               "lines_waited": du.judge_da_lines(waited)[0], "lines_shown": du.judge_da_lines(shown)[0],
               "lines_none": du.judge_da_lines([{"hl": [], "gl": []}])[0],
               "flash_dip": du.judge_df_flash([dict(f, cur=[200, 0, 248]) for f in fades])[0],
               "flash_hurry": du.judge_df_flash(fl(fades, action="hurry", by="black"))[0],
               "grace_black": du.judge_df_grace(fl(fades, by="black"))[0],
               "pace_path": du.judge_df_pace(fl(pace, path="fast"))[0], "pace_by": du.judge_df_pace(fl(pace, by="recheck"))[0],
               "pace_late": du.judge_df_pace([dict(f, last_close_t=f["commit_t"] + 50) for f in pace])[0],
               "probe_sends": du.judge_da_probe(hi(probe, sends=0))[0], "probe_oob": du.judge_da_probe(hi(probe, oob=None))[0],
               "probe_copies": du.judge_da_probe(hi(probe, sends=5))[0], "probe_end": du.judge_da_probe(hi(probe, last_end="cap"))[0],
               "probe_landed": du.judge_da_probe(hi(probe, landed_frames=0))[0],
               "probe_refused": du.judge_da_probe(hi(probe, last_site="debugwarp"))[0],
               "life_still_consistent": du.judge_da_probe(hi(probe, last_end="old", landed_frames=0, frames=0), life_old=True)[0],
               "b_a_loads": du.judge_dc_b_a([dict(r, maps=2) for r in rest])[0],
               "b_a_gap": du.judge_dc_b_a([dict(r, g_land_t=r["h_land_t"] + 150 + 301) for r in rest])[0],
               "b_a_bounce": du.judge_dc_b_a([dict(r, g0=block(counts__bounces=0), g=dict(r["g"], counts=dict(r["g"]["counts"], bounces=1))) for r in rest])[0],
               "b_b_bounce": du.judge_dc_b_b(last(rold, own_verdict="bounce", own_why="not-host"))[0],
               "b_b_conv": du.judge_dc_b_b([dict(r, g=dict(r["g"], own=dict(r["g"]["own"], converted=0))) for r in rold])[0],
               "b_b_loads": du.judge_dc_b_b([dict(r, maps=2) for r in rold])[0],
               "halt": du.judge_dp_halt([{"g0": block(pin__pre_frames=3), "g": block(pin__pre_frames=4, pin__max_pre_diff=2)}])[0],
               "dress": du.judge_dp_dress([{"want": 0, "leader": 2}])[0]}}
''')
    assert out["good"] == ["green"] * 10, out["good"]
    assert out["unreached"] == ["unreached"] * 6, out["unreached"]
    assert out["void"] == ["void"] * 3, out["void"]
    assert out["life_ok"] == "green", out
    assert all(v == "red" for v in out["bad"].values()), out["bad"]


def test_cat_judges_read_the_orphan_steppers_hold():
    """DB-SHAPE / DB-BIT / DB-HOLD / DB-ORDER on the guest's 113 out of KIT-1's orphan stepper (the host's control off on 351 with no
    scene until its 113 rises 5.2 s later): green under act (one hold line, its end at the host's claim, no orphaned line, every close
    by the host's seq), red under s163's rule (the line orphans and auto-closes: DB-HOLD and DB-ORDER). Text 118 first is the else path
    (VOID); each other part alone is red."""
    out = _duo_child(r'''
act, old = cat_ev(), cat_ev("orphan")
ev = cat_ev()
j = lambda e: [du.judge_db_shape(e)[0], du.judge_db_bit(e)[0], du.judge_db_hold(e)[0], du.judge_db_order(e)[0]]
early = dict(ev, gs=[x if so.now_ms(x) < 1000 else ed(x, ns={"host_flags": 9}) for x in ev["gs"]])
bit_lane = dict(ev, gs=[ed(x, sw={"own.host_lane": 0}) for x in ev["gs"]])
bit_host = dict(ev, hs=ev["hs"] + [Sx(1000, 351, ctl=True)])
bit_ctl = dict(ev, gs=[ed(x, ns={"host_flags": 10}) if so.now_ms(x) < 5200 else x for x in ev["gs"]])
two_holds = dict(ev, gl=ev["gl"] + [L(du.so.hold_words(du.CAT_FIRST))])
order_seq = dict(ev, gl=[ln.replace("(host seq 42)", "(host seq 49)") for ln in ev["gl"]])
order_drop = dict(ev, gl=ev["gl"] + [L("[NetSync] dialogue: host seq 45 (win 7 text 117) dropped -- it is for field 351")])
OUT = {"act": j(act), "old": j(old), "else": j(cat_ev(else_path=True)), "unstamped": j(cat_ev(on=False)),
       "end_why": du.so.end_lines(act["gl"], du.CAT_FIRST),
       "bad": {"shape_early": du.judge_db_shape(early)[0], "shape_no_pass": du.judge_db_shape(dict(ev, gl=ev["gl"][1:]))[0],
               "bit_lane": du.judge_db_bit(bit_lane)[0], "bit_host": du.judge_db_bit(bit_host)[0], "bit_ctl": du.judge_db_bit(bit_ctl)[0],
               "hold_two": du.judge_db_hold(two_holds)[0], "hold_closes": du.judge_db_hold(dict(ev, closes1=1))[0],
               "order_seq": du.judge_db_order(order_seq)[0], "order_drop": du.judge_db_order(order_drop)[0]}}
''')
    assert out["act"] == ["green"] * 4 and out["unstamped"] == ["green"] * 4, out
    assert out["old"] == ["green", "green", "red", "red"], out["old"]
    assert out["else"] == ["void"] * 4, out["else"]
    assert len(out["end_why"]) == 1 and out["end_why"][0][1] in ("a host event claims it", "the host is busy (a scene or a line)"), out
    assert all(v == "red" for v in out["bad"].values()), out["bad"]


def test_the_other_duo_judges_can_go_red_on_each_part():
    """DC-OWN, DL-DEFER, DP-DEFER (a late capture UNREACHED; VOID under `life`; reach needs the host's mark in the latest frame), DP-AGED,
    DP-MARK (VOID unless the mark leads the landing by 300 ms; a late capture UNREACHED), DL-LEFT, DF-OPEN (a refused warp VOID: DF-PACE
    stands in), DP-PARTY (REACHED only on a party change), LVD-ROLE, LVD-LIFE."""
    out = _duo_child(r'''
m, a, k, lf, op = menu_ev(), menu_ev(aged=True), mark_ev(), left_ev(), open_ev()
def g(ev, **kw):
    import copy
    ev = copy.deepcopy(ev)
    for path, v in kw.items():
        d = ev["g"]
        ks = path.split("__")
        for x in ks[:-1]:
            d = d[x]
        d[ks[-1]] = v
    return ev
own = {"g": block(last__own_verdict="ate", last__own_why="ate"), "gl": [L("Map: 450 (Dali/Field)")]}
party = [{"sub": "x", "dest": 1, "party_emit": [0, 1, 2, 3], "party_land": [0, 4, 2, 3], "mirror_after": [0, 4, 2, 3]}]
OUT = {"good": [du.judge_dc_own(own)[0], du.judge_dl_defer(m)[0], du.judge_dp_defer(m)[0], du.judge_dp_aged(a)[0], du.judge_dp_mark(k)[0],
                du.judge_dl_left(lf)[0], du.judge_df_open(op)[0], du.judge_dp_party(party)[0], du.judge_lvd_role(LVD)[0],
                du.judge_lvd_life(True, {"life": "old"}, {"life": "act"})[0]],
       "unreached": [du.judge_dp_defer(g(m, pin__last_use_quality="late"))[0], du.judge_dp_defer(g(m, pin__last_diff=0))[0],
                     du.judge_dp_defer(g(m, last__follow_via="serial"))[0], du.judge_dp_mark(g(k, pin__last_use_quality="late"))[0],
                     du.judge_dp_party([dict(party[0], party_land=[0, 1, 2, 3])])[0]],
       "void": [du.judge_dp_defer(m, life_word=True)[0], du.judge_dp_mark(dict(k, host_flag_t=k["g"]["last"]["land_t"] - 299))[0],
                du.judge_df_open(dict(op, refused="the game refused a step: warp"))[0]],
       "bad": {"own_two_maps": du.judge_dc_own(dict(own, gl=own["gl"] * 2))[0], "own_unrecorded": du.judge_dc_own(dict(own, g=block()))[0],
               "defer_late": du.judge_dl_defer(g(m, last__follow_t=MC + 260))[0],
               "defer_serial": du.judge_dl_defer(g(m, last__follow_via="serial"))[0],
               "defer_flag": du.judge_dp_defer(dict(m, flag=True))[0], "aged_flag": du.judge_dp_aged(dict(a, flag=False))[0],
               "aged_why": du.judge_dp_aged(g(a, pin__last_use="pin"))[0], "mark_flag": du.judge_dp_mark(dict(k, flag=True))[0],
               "mark_line": du.judge_dp_mark(dict(k, gl=[]))[0], "mark_diff": du.judge_dp_mark(g(k, pin__last_diff=0))[0],
               "left_line": du.judge_dl_left(dict(lf, hl=[]))[0], "left_late": du.judge_dl_left(dict(lf, start_t=lf["start_t"] - 400))[0],
               "left_end": du.judge_dl_left(dict(lf, h=block(intent__nonce=7, intent__last_end="stands")))[0],
               "left_nonce": du.judge_dl_left(dict(lf, g=block(seen__nonce=8, seen__last_t=lf["start_t"])))[0],
               "open_path": du.judge_df_open(dict(op, fade=dict(op["fade"], path="fast")))[0],
               "open_short": du.judge_df_open(dict(op, fade=dict(op["fade"], ms=600)))[0],
               "open_bk": du.judge_df_open(dict(op, fade=dict(op["fade"], backlog_start="line")))[0],
               "party": du.judge_dp_party([dict(party[0], mirror_after=[0, 1, 2, 3])])[0],
               "role": du.judge_lvd_role(dict(LVD, host_orphan=""))[0], "life_unacked": du.judge_lvd_life(False, {"life": "old"}, {"life": None})[0],
               "life_held": du.judge_lvd_life(True, {"life": "old"}, {"life": "old"})[0]}}
''')
    assert out["good"] == ["green"] * 10, out["good"]
    assert out["unreached"] == ["unreached"] * 5, out["unreached"]
    assert out["void"] == ["void"] * 3, out["void"]
    assert all(v == "red" for v in out["bad"].values()), out["bad"]


def test_each_duo_calibration_word_reds_exactly_its_rows_with_its_marker():
    """THE DUO ORACLE: the plain evidence reds nothing but the pre-registered DA-ARRIVE defect (BASELINE_RED); each word's evidence (the
    engine under that lever, through the same twins) reds EXACTLY its registered rows -- its "if reached" DF-PACE when reached -- each
    with its marker, VOID / UNREACHED rows (DP-DEFER under `life`, DF-GRACE under `fade`) kept out of the count, and D-CAL passes; the
    `nocache` control reds nothing. With the arrival guard (no dwell OUT at the gate) the plain run is all green."""
    out = _duo_child(r'''
res = {}
for word in [None] + list(du.WORDS):
    rows, marks = duo_rows(word)
    failed, void, unreached, reds = sets(rows)
    entry = {"reds": reds, "void": sorted(void), "unreached": sorted(unreached), "baseline": rows["DA-ARRIVE"][0]}
    if word is not None:
        pred = du.predicted_now(word, void, unreached, du.LEGS_SEL)
        entry["pred"] = sorted(pred)
        entry["marks"] = {r: du.marker(word, r, marks.get(r))[0] for r in pred}
        entry["cal"] = list(du.judge_cal(word, failed, void, unreached, du.LEGS_SEL))
    res[str(word)] = entry
guard, _m = duo_rows(gate_out=False)
OUT = {"res": res, "guard_reds": sorted(r for r, v in guard.items() if v[0] == R_)}
''')
    res = out["res"]
    assert res["None"]["reds"] == [] and res["None"]["void"] == [] and res["None"]["baseline"] == "red", res["None"]
    assert res["None"]["unreached"] == ["DP-PARTY"], res["None"]
    assert out["guard_reds"] == [], out
    want = {"stamps": ["DA-LINES"], "delay": ["DA-CAL"], "orphan": ["DB-HOLD", "DB-ORDER"], "own": ["DC-B(b)"], "nocache": [],
            "pin": ["DP-DEFER", "DP-MARK"], "life": ["DL-DEFER", "DL-LIFE"], "fade": ["DF-3X", "DF-FAST", "DF-FLASH", "DF-OPEN", "DF-PACE"],
            "long": ["DF-3X", "DF-FAST"], "nogate": ["DF-OPEN", "DF-PACE"]}
    for word, rows in want.items():
        e = res[word]
        assert e["reds"] == rows == e["pred"], (word, e)
        assert e["cal"][0] is True, (word, e["cal"])
        assert all(v == "green" for v in e["marks"].values()), (word, e["marks"])
    assert res["life"]["void"] == ["DP-DEFER"] and "DF-GRACE" in res["fade"]["unreached"], (res["life"], res["fade"])


def test_the_duo_markers_and_d_cal_can_fail():
    """Each word's marker is red on the plain evidence (the lever's signature absent); D-CAL is red on a predicted red that stayed green,
    on an unpredicted red, on a predicted red read UNREACHED / VOID, and VOID when every predicted red is out; the baseline DA-ARRIVE and
    VOID rows elsewhere never count; an "if reached" row joins only when reached."""
    out = _duo_child(r'''
rows, marks = duo_rows()
plain = {}
for word in du.WORDS:
    for r in du.WORDS[word][1] + du.WORDS[word][2]:
        plain[f"{word}:{r}"] = du.marker(word, r, marks.get(r))[0]
L_ = du.LEGS_SEL
jc = lambda w, failed, void=(), unr=(): du.judge_cal(w, set(failed), set(void), set(unr), L_)[0]
OUT = {"plain": plain, "nocache": du.marker("nocache", "x", {})[0],
       "cal": {"exact": jc("orphan", ["DB-HOLD", "DB-ORDER"]), "baseline": jc("orphan", ["DB-HOLD", "DB-ORDER", "DA-ARRIVE"]),
               "void_elsewhere": jc("orphan", ["DB-HOLD", "DB-ORDER", "DB-SHAPE"], ["DB-SHAPE"]),
               "missing": jc("orphan", ["DB-HOLD"]), "extra": jc("orphan", ["DB-HOLD", "DB-ORDER", "DA-CAL"]),
               "lost": jc("orphan", ["DB-HOLD", "DB-ORDER"], ["DB-ORDER"]), "all_out": jc("own", ["DC-B(b)"], [], ["DC-B(b)"]),
               "cond_reached_red": jc("nogate", ["DF-OPEN", "DF-PACE"]), "cond_reached_green": jc("nogate", ["DF-OPEN"]),
               "cond_unreached": jc("nogate", ["DF-OPEN"], [], ["DF-PACE"]), "nocache_clean": jc("nocache", []),
               "nocache_red": jc("nocache", ["DC-B(b)"])},
       "all_out_why": du.judge_cal("own", {"DC-B(b)"}, set(), {"DC-B(b)"}, L_)[1]}
''')
    assert all(v == "red" for v in out["plain"].values()) and out["nocache"] == "red", out
    c = out["cal"]
    for k in ("exact", "baseline", "void_elsewhere", "cond_reached_red", "cond_unreached", "nocache_clean"):
        assert c[k] is True, (k, c)
    for k in ("missing", "extra", "lost", "all_out", "cond_reached_green", "nocache_red"):
        assert c[k] is False, (k, c)
    assert out["all_out_why"].startswith("VOID: every predicted red"), out


def test_the_duo_reads_its_evidence_off_the_engines_samples():
    """tr_evidence / arrival_of / desk_evidence / host_close_t / fade_left_start off sample streams in the engine's state shape: the
    records at their most advanced sample, the overlap and the step-out window on the swap clock, the party at the emit and at the
    landing, the host's close found by its TEXT (a host's `netsync.windows` lists nothing: window tracking is guest-only), and the
    per-follow left_start read while the follow ran."""
    out = _duo_child(r'''
D = 30611
hs, gs = [], []
for t in range(0, 4000, 50):
    on = t >= 900
    sw = {"last.id": 6 if t >= 400 else 5, "last.dest": D if t >= 400 else 250, "last.emit_t": 400 if t >= 400 else -1,
          "last.land_t": 900 if on else -1, "last.state": "landed" if on else ("open" if t >= 400 else "done"),
          "intent.emit_t": 400 if t >= 400 else -1, "intent.first_sent_t": 405 if t >= 400 else -1, "intent.sends": t // 100}
    hs.append(Sx(t, D if on else 250, ctl=t >= 3200 or t < 400, sw=sw, party=[0, 1, 2, 3] if t < 600 else [0, 4, 2, 3]))
for t in range(0, 4000, 50):
    on = t >= 1400
    sw = {"last.id": 9 if t >= 430 else 8, "last.dest": D if t >= 430 else 250, "last.seen_t": 430 if t >= 430 else -1,
          "last.arrived_t": 425 if t >= 430 else -1, "last.land_t": 1400 if on else -1, "fade.left_start": 7 if 431 <= t < 1400 else -1}
    step = {"base.age_ms": (t - 1400) if on and t <= 3200 else -1, "out_why.dwell": 1 if t >= 2900 else 0, "active": 2900 <= t < 3300}
    gs.append(Sx(t, D if on else 250, ctl=t >= 3300 or t < 430, sw=sw, step=step, want=2 if on else -1, mirror=[0, 4, 2, 3] if on else None))
tr = du.tr_evidence("CAL", "ARRIVE", D, 250, hs, gs, [], [DWELL_OUT(D)], "gate")
a = du.arrival_of(tr, "gate")
host_txt = [Sx(t, 351, texts=["Text 139"] if 100 <= t < 700 else (["Next"] if t >= 900 else None)) for t in range(0, 1200, 50)]
guest_txt = [Sx(t, 351, wins=[(3, 139, "locked")] if 300 <= t < 1000 else (), texts=["Text 139"] if 300 <= t < 1000 else None)
             for t in range(0, 1200, 50)]
OUT = {"h_id": tr["h"]["last"]["id"], "g_id": tr["g"]["last"]["id"], "g_land": tr["g_land_t"], "h_land": tr["h_land_t"],
       "h_ctl": tr["h_ctl_t"], "overlap": tr["overlap"], "base_peak": tr["base_peak"], "dwell": tr["dwell_count"], "active": tr["active"],
       "dressed": tr["dressed"], "party": [tr["party_emit"], tr["party_land"], tr["mirror_after"]], "emit": tr["hi"].get("emit_t"),
       "arrival": [a["dwell_lines"], du.arrive_reached(a)], "verdict": du.judge_da_arrive([a, du.arrival_of(dict(tr, gl=[], dwell_count=0, active=False), "control")])[0],
       "host_close": du.host_close_t(host_txt, guest_txt, (3, 139)), "guest_close": du.close_t(guest_txt, (3, 139)),
       "left": du.fade_left_start(gs, 430, D), "cur": du.fade_cur_window(gs, 430, 900, D)[:2],
       "dip": [du.dipped([200, 216, 210, 248]), du.dipped([200, 190, 248]), du.dipped([200, None, 0])]}
''')
    assert (out["h_id"], out["g_id"], out["g_land"], out["h_land"], out["h_ctl"]) == (6, 9, 1400, 900, 3200), out
    assert out["overlap"] == 1800 and out["base_peak"] == 1800 and out["dwell"] == 1 and out["active"] and out["dressed"], out
    assert out["party"] == [[0, 1, 2, 3], [0, 4, 2, 3], [0, 4, 2, 3]] and out["emit"] == 400, out
    assert out["arrival"] == [1, True] and out["verdict"] == "red", out
    assert out["host_close"] == 700 and out["guest_close"] == 1000 and out["left"] == 7, out
    assert out["dip"] == [False, True, True], out


def test_the_duo_run_has_the_registered_shape():
    """The run's shape (source): DK-CLOCK before any leg; the `stamps` lever on BOTH games; the legs in order with LEVERS last (its
    `reset`); DA-ARRIVE judged after DESK (its DESK watch) and DA-LANE / DP-PARTY after the legs; CAL's sub-legs and levers as
    registered (the word's fade lever on CAL2 / CAL3 only); six DESK runs (each D, act and REST-OLD), REST-OLD's `fade old` before text
    139 closes, the `own` words on REST-OLD only; the orphan lever before the CAT pick; the pin lever on MARK and the short MENU run only;
    an unregistered ARRIVE_ID refused with its deploy command."""
    out = _duo_child(r'''
import inspect
src = {f.__name__: inspect.getsource(f) for f in (du._run, du._leg_cal, du._desk_run, du._leg_cat, du._menu_run, du._leg_mark,
                                                  du._leg_levers, du.run_duo)}
r = src["_run"]
subs = {s[0]: list(s[1:]) for s in du.cal_subs(None)}
subs_fade = {s[0]: s[1] for s in du.cal_subs("fade")}
OUT = {"clock_first": r.index("_dk_clock(d, ctx)") < r.index("for leg, fn in"),
       "stamps_both": '_lever(host, ctx, "stamps", "off")' in r and '_lever(guest, ctx, "stamps", "off")' in r,
       "levers_last": r.index("_leg_levers") > r.index("DA-ARRIVE") > r.index("for leg, fn in") and r.index("DP-PARTY") < r.index("_leg_levers"),
       "late_rows": list(du.LATE_ROWS), "subs": subs, "subs_fade": subs_fade, "delay_word": du.cal_subs("delay")[1][2],
       "desk_runs": du.desk_runs(None), "rest_old_at": [list(k) for k in du.REST_OLD_AT],
       "rest_old_lever": 'if ctx.cal in ("own", "nocache"):' in src["_desk_run"] and '_lever(guest, ctx, "fade", "old")' in src["_desk_run"],
       "orphan_before_pick": src["_leg_cat"].index('"orphan", "old"') < src["_leg_cat"].index("host.choose_landed(CAT_PICK)"),
       "pin_short_only": "pin_old = short and ctx.cal == \"pin\"" in src["_menu_run"] and '"pin", "old"' in src["_leg_mark"],
       "mark_long": '_lever(guest, ctx, "fade", "long")' in src["_leg_mark"],
       "arrive_refused": "deploy_command()" in src["_leg_cal"] and "not registered on both roots" in src["_leg_cal"],
       "reset": "cb.release(host)" in src["_leg_levers"],
       "finals": "predicted_now(cal, ctx.void, ctx.unreached, ctx.legs)" in src["run_duo"] and "judge_cal(cal, led.failed()" in src["run_duo"]}
''')
    assert out.pop("late_rows") == ["DA-ARRIVE"]
    assert out.pop("subs") == {"CAL0": ["old", 0, False, 30602, "control", "control"], "CAL1": ["old", 200, False, 30602, None, None],
                               "CAL2": ["act", 0, False, 30602, "watch", "watch"], "CAL3": ["act", 0, True, 30602, None, None],
                               "ARRIVE": ["act", 0, False, 30611, "gate", "watch"],
                               "ARRIVE-OLD": ["old", 0, False, 30611, "control", "control"]}
    assert out.pop("subs_fade") == {"CAL0": "old", "CAL1": "old", "CAL2": "old", "CAL3": "old", "ARRIVE": "act", "ARRIVE-OLD": "old"}
    assert out.pop("delay_word") == 0
    assert out.pop("desk_runs") == [[0.3, False], [0.3, True], [1.0, False], [1.0, True], [2.5, False], [2.5, True]]
    assert out.pop("rest_old_at") == [[3, 139], [3, 138]]
    assert all(out.values()), out


# ------------------------------------------------------------------------------------------------ the follow race and the evidence scripts
def test_the_follow_race_takes_the_stamp_tail_and_runs_fe_and_fd_on_fade_old():
    """coop_follow_race_duo.py (s164's kit side): MINE["intent"] takes an s164 stamp tail (and an s163 line without one); FE1, FE2 and
    FD run with the guest on `swap fade old` when the engine publishes `netsync.swap` (they model a commit 0.9 game-seconds after the
    start) and `act` again after; FS runs at act (D's own-warp term); the restore sends `act`."""
    r = subprocess.run([sys.executable, "-X", "utf8", "-c", (
        "import json, sys, inspect\nsys.path.insert(0, %r)\nsys.path.insert(0, %r)\nimport coop_follow_race_duo as fr\n"
        "rx = fr.MINE['intent']\n"
        "plain = rx.search('[NetSync] intent: following the peer to field 30602 (parallel)')\n"
        "st = rx.search('[NetSync] intent: following the peer to field 30602 (parallel) (t 123456 ms)')\n"
        "inside = rx.search('[NetSync] intent: following the peer to field 30602 (t 12 ms) (parallel)')\n"
        "run, rest, sf = inspect.getsource(fr._run), inspect.getsource(fr._restore), inspect.getsource(fr._swap_fade)\n"
        "i = lambda s: run.index(s)\n"
        "OUT = {'plain': [plain.group(1), plain.group(2)] if plain else None, 'stamped': [st.group(1), st.group(2)] if st else None,\n"
        "       'inside': inside is None,\n"
        "       'fe_old': i('_swap_fade(d, \"old\")') < i('_leg_follow(d, led, \"FE1\", AWAY)'),\n"
        "       'fs_act': i('_leg_follow(d, led, \"FE2\", HOME)') < run.index('_swap_fade(d, \"act\")') < i('_leg_race(d, led, ctx, \"FS\")'),\n"
        "       'fd_old': run.rindex('_swap_fade(d, \"old\")', 0, i('_leg_race(d, led, ctx, \"FD\")')) > i('_leg_race(d, led, ctx, \"FS\")'),\n"
        "       'fd_act': run.index('_swap_fade(d, \"act\")', i('_leg_race(d, led, ctx, \"FD\")')) > 0,\n"
        "       'restore': '_swap_fade(d, \"act\")' in rest, 'gated': 'cb.has(d.guest.state, \"netsync.swap\")' in sf\n"
        "       and 'cb.try_ns(d.guest, \"swap\", \"fade\", word)' in sf}\n"
        "print('@@' + json.dumps(OUT))\n") % (str(SCEN), str(REPO / "tools"))], capture_output=True, text=True, cwd=str(SCEN), timeout=120,
        env={k: v for k, v in os.environ.items() if k != "COOP_CALIBRATE"})
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(next(ln for ln in r.stdout.splitlines() if ln.startswith("@@"))[2:])
    assert out.pop("plain") == ["30602", None] and out.pop("stamped") == ["30602", "123456"], out
    assert all(out.values()), out


def test_the_swap_timing_evidence_scripts_take_the_tolerant_stamp_tail():
    """studies/field-coop/swap-timing/final.py, conv.py and drift.py (they run at import: read as text): each anchored tap regex gains
    `(?: \\(t (\\d+) ms\\))?$` -- so an s164 line still matches and its stamp is captured -- and each prefers the stamp over the
    whole-second prefix only when both lines of a comparison carry one (never mixing QPC ms with the time-of-day THETA)."""
    base = REPO / "studies" / "field-coop" / "swap-timing"
    tail = r"(?: \(t (\d+) ms\))?$"
    want = {"final.py": r"dialog tap: win (\d+) text (\d+) .* seq (\d+)" + tail,
            "conv.py": r"dialog tap: win (\d+) text (\d+) kind (\d) .* page (\d+)( closes)? seq (\d+)" + tail,
            "drift.py": r"dialog tap: .* seq (\d+)" + tail}
    plain = "[NetSync] dialog tap: win 3 text 129 kind 0 idx -1 page 0 closes seq 50"
    for name, rx in want.items():
        src = (base / name).read_text(encoding="utf-8")
        assert rx in src, (name, rx)
        assert "seq (\\d+)$" not in src.replace(tail, ""), name             # no tap regex left anchored without the tail
        m0, m1 = re.search(rx, plain), re.search(rx, plain + " (t 4321 ms)")
        assert m0 and m1 and m0.groups()[-1] is None and m1.groups()[-1] == "4321", name
        assert "STAMP = re.compile(r' \\(t (\\d+) ms\\)$')" in src, name
    for name in ("final.py", "conv.py"):
        src = (base / name).read_text(encoding="utf-8")
        assert "THETA_QPC.get(sess, 0.0)" in src and "is not None and" in src, name
