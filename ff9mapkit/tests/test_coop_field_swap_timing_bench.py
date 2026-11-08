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
  * the whole solo bench runs green on the stand-in with COOP_LEGS=KAB (the legs it models; a C, P, L, F or G leg there proves nothing,
    P8), and the stamps / delay / orphan calibrations calibrate exactly there too;
  * [ff9mapkit netsync s164] THE ARRIVAL GUARD (studies/field-coop/ARRIVAL-GUARD-S164.md rev 2): the solo's leg G judged from state on
    a frame-by-frame run of battlewire's guard twins (each part red alone, P8 extended, the setup misses VOID, the `arrive` word), the
    K legs' `arrive` / `arrivebench` parts; the duo's DA-ARRIVE as the guard's calibration (the reach fix, the attributable green, the
    named reds), DA-GUARD with its floor, the `arrive` word, the `life` scope, an empty BASELINE_RED, ARRIVE's entry_settle 64;
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
# [s164] THE ARRIVAL GUARD: a LIVE engine's `netsync.swap` -- `levers.arrive` null and the `arrive` block at rest with K published
# (AppendSwapArrive; the catch line's sentinel reads arrival_lead_ms -1)
ARRIVE_REST = {"arrival_lead_ms": BW.ARRIVAL_LEAD_MS, "armed": False, "field": -1, "land_t": -1, "lead_ms": None, "late": False,
               "host": {"field": -1, "nonce": -1, "seen_t": -1, "age_ms": -1, "bench": False},
               "episode": {"on": False, "held": False, "base_ms": None, "dwell_ms": None, "shift_ms": None},
               "last": {"field": -1, "lead_ms": None, "end": None, "base_ms": None, "dwell_ms": None, "shift_ms": None},
               "arms": 0, "late_arms": 0, "unanchored": 0, "world": 0, "held": 0,
               "ends": {"spared": 0, "delayed": 0, "line": 0, "ate": 0}, "spends": {"control": 0, "field": 0, "out": 0, "session": 0},
               "bench": {"armed": False, "lead_ms": None}, "faults": 0}
SENT = copy.deepcopy(FG.NETSYNC_SWAP_SENTINELS)
SENT["levers"]["arrive"] = None
SENT["arrive"] = copy.deepcopy(ARRIVE_REST)
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
PROOF = L("[NetSync] " + BW.swap_proof_text(FG.FAKE_SWAP_SELFTEST_ROWS, FG.FAKE_SWAP_MUTANTS, "qpc", 10000000, True))
DLG_OK = L("[NetSync] dialogue authority selftest: OK (98 rows)")
REFUSE = {"delay": "the game refused a step: " + BW.SWAP_USAGE, "word": BW.SWAP_USAGE,
          "arrivebench": "the game refused a step: netsync: " + BW.SWAP_USAGE,
          "bench": "the game refused a step: netsync: " + BW.swap_refusal_bench("intent") + " (steps=[...])",
          "off": "the game refused a step: netsync: " + BW.SWAP_REFUSAL_COOP_OFF}
REST = {"stamps": None, "delay_ms": 0, "orphan": None, "own": None, "pin": None, "life": None, "fade": None, "hostctl_off": False,
        "arrive": None}
BENCH_REST = {"armed": False, "lead_ms": None}


def lever_steps():
    """K-LEVER's steps as the engine answers them: each ack line, `levers` read back ([s164] `arrivebench` reads the bench's arm)."""
    out, lv, bench = [], dict(REST), dict(BENCH_REST)
    for op, w in so.K_LEVER_SEQ:
        if op == "arrivebench":
            bench = {"armed": True, "lead_ms": int(w)}
        else:
            key, vals = so.lever_want(op, w)
            lv = dict(lv, **{key: vals[0]})
        out.append({"op": op, "word": w, "ok": True, "why": "", "lines": [L(so.lever_line(op, w))], "levers": dict(lv),
                    "bench": dict(bench)})
    return out


CLEAR = [L(BW.swap_harness_clear(False))]
RELEASE = [L(BW.swap_harness_release(False))]
K_REC = rec(id=1, due_t=5000, commit_t=5000, delay_ms=0, follow_t=4100)


def k_rows():
    return {"K-PROOF": so.judge_proof([PROOF, DLG_OK], "ok"), "K-REFUSE": so.judge_refuse(REFUSE),
            "K-LEVER": so.judge_levers(lever_steps(), REST, CLEAR, BENCH_REST),
            "K-RELEASE": so.judge_release(RELEASE, REST, [], K_REC, 33.0, BENCH_REST, False)}


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


# ---- G: THE ARRIVAL GUARD on one ARRIVE landing, a frame at a time through battlewire's twins (swap_arrive_holds / _dwell_age /
# _held / _end / _spend / _count) -- the engine's order on the selftest role: ServiceStepOut (the base, ArriveDwellAge, StartRule),
# then GuestTick's ArriveTick (the late bench write first, the episode's end, the spend)
G_T0, G_BIND, G_A = 60000, 66, 2200          # my landing (arrive.land_t), B - G, my control back at G + A (64 ticks + O)
G_BASE = {"arms": 2, "late_arms": 1, "unanchored": 1, "held": 4, "ends": {"spared": 3, "delayed": 1, "line": 0, "ate": 0},
          "spends": {"control": 3, "field": 1, "out": 2, "session": 0}}
G_DWELL0 = 5                                 # stepout.out_why.dwell before the row


def gsim(row, word=None, lead=Ellipsis, A=G_A, bind=G_BIND, k_pub=None, field_pub=None, host_bench=True, episode_pub=True,
         bench_write=True):
    """One leg-G row as the engine runs it: my landing at G_T0, my control off until G + A (lockt2-arrive's hold), the bench host's
    control off throughout (`hostscene 1`), the base from G + bind; R by the row's bench lead (>= 0: Hs = G - lead, anchored at the
    landing; < 0: written at the first tick >= G + |lead| -- the late form, through the late edge) or, with none, the previous row's
    stale bench record (host.field 30611, never anchoring); armed unless the `arrive` word's lever is old at this landing. R as the
    row starts (b0, and every sample before the write): G-HOLD (the first row) has none (ARRIVE_REST's host, nonce -1); every later
    row starts on the previous row's bench record -- nothing clears R between G rows -- host.field 30611, nonce 8, bench true, seen
    before HOME's landing. A bench write takes R's nonce + 1 (ArriveBenchRecord: 8 -> 9; none -> 0). The knobs (``k_pub``,
    ``field_pub``, ``host_bench``, ``episode_pub``) break one published key for the P8 tests; ``bench_write`` False is an acked
    `arrivebench` the engine never ran (no write, no anchor: the stale record stands). -> (samples, b0, step0)."""
    lead = so.G_LEADS[row] if lead is Ellipsis else lead
    K, D = BW.ARRIVAL_LEAD_MS, BW.ARRIVE_DWELL_MS
    old = word == "arrive" and row in so.WORDS["arrive"][1]
    live = not old
    last = {"field": 30602, "lead_ms": None, "end": "spared", "base_ms": 1600, "dwell_ms": 900, "shift_ms": 700}
    prior = None if row == so.G_ROWS[0] else {"field": so.ARRIVE_ID, "nonce": 8, "seen_t": 10, "tick": G_T0 - 99999, "bench": True}
    wnonce = ((prior["nonce"] if prior is not None else -1) + 1) & 0xFF
    anchored, hs, lead_ms, late, arm_c, late_c = False, 0, None, False, False, False
    rtick, rseen, wrote = None, None, False                  # this row's bench write (none yet)

    def host_at(now):
        if wrote:
            return {"field": so.ARRIVE_ID, "nonce": wnonce, "seen_t": rseen, "age_ms": now - rtick, "bench": host_bench}
        if prior is None:
            return copy.deepcopy(ARRIVE_REST["host"])
        return {"field": prior["field"], "nonce": prior["nonce"], "seen_t": prior["seen_t"], "age_ms": now - prior["tick"],
                "bench": prior["bench"]}

    b0 = block(levers__arrive="old" if old else None)
    b0["arrive"] = dict(copy.deepcopy(ARRIVE_REST), **copy.deepcopy(G_BASE), last=dict(last), host=host_at(G_T0 - DT))
    step0 = {"out_why": {"line": 0, "dwell": G_DWELL0, "ate": 0}}
    cnt = copy.deepcopy(G_BASE)
    if bench_write and lead is not None and lead >= 0:       # ArriveLanding writes the bench's R first, then the anchor reads it
        anchored, hs, lead_ms, rtick, rseen, wrote = True, G_T0 - lead, lead, G_T0 - lead, G_T0, True
    c = BW.swap_arrive_count(BW.ARRIVE_EV_LANDING, live, anchored, lead_ms if lead_ms is not None else BW.ARRIVE_LEAD_NONE, False, False)
    if c & BW.ARRIVE_COUNT_ARM:
        cnt["arms"], arm_c = cnt["arms"] + 1, True
    ep = {"on": False, "held": False, "base": 0, "dwell": 0, "frame": 0, "lead": None}
    # the bench as published: a negative lead waits for ArriveTick's late write; an unrun write (``bench_write`` False) stays armed
    active, out_t, dwells, back_since, bench_armed = False, None, 0, None, lead is not None and (lead < 0 or not bench_write)
    samples = [S(G_T0 - DT, field=HM, sw={"levers.arrive": "old" if old else None})]
    k = 0
    while True:
        t = k * DT
        now = G_T0 + t
        my_ctl = t >= A
        base = t - bind if (not my_ctl and t >= bind and not active) else -1
        if base >= 0:                                        # ServiceStepOut: StartRule(line F, ArriveDwellAge(...), landing F)
            holds = BW.swap_arrive_holds(live, anchored, so.ARRIVE_ID, so.ARRIVE_ID)
            dwell = BW.swap_arrive_dwell_age(holds, base, now - hs) if holds else base
            if holds:
                if not ep["on"]:
                    ep.update(on=True, held=False)
                ep.update(base=base, dwell=dwell, frame=k, lead=lead_ms)
                if BW.swap_arrive_held(ep["held"], base, dwell):
                    ep["held"] = True
                    cnt["held"] += 1
            if dwell >= D:
                active, out_t, dwells = True, now, dwells + 1
        if bench_write and bench_armed and not wrote and t >= -lead:   # ArriveTick's late write: tick = seenTick = now, this landing
            wrote, bench_armed = True, False
            anchored, hs, lead_ms, late, rtick, rseen = True, now, G_T0 - now, True, now, now
            c = BW.swap_arrive_count(BW.ARRIVE_EV_LATE_EDGE, live, True, lead_ms, arm_c, late_c)
            if c & BW.ARRIVE_COUNT_ARM:
                cnt["arms"], arm_c = cnt["arms"] + 1, True
            if c & BW.ARRIVE_COUNT_LATE_ARM:
                cnt["late_arms"], late_c = cnt["late_arms"] + 1, True
        if ep["on"]:                                         # ArriveTick: the episode's end
            frames = k - ep["frame"]
            end = BW.swap_arrive_end(ep["held"], frames, False, active, BW.ARRIVE_OUT_DWELL if active else BW.ARRIVE_OUT_NONE)
            if end != BW.ARRIVE_END_NONE or active or frames > 2:
                ep["on"] = False
                last = {"field": so.ARRIVE_ID, "lead_ms": ep["lead"], "end": BW.ARRIVE_END_NAMES[end], "base_ms": ep["base"],
                        "dwell_ms": ep["dwell"], "shift_ms": ep["base"] - ep["dwell"]}
                if end != BW.ARRIVE_END_NONE:
                    cnt["ends"][BW.ARRIVE_END_NAMES[end]] += 1
        if live:                                             # ...then the spend
            back_since = (back_since if back_since is not None else now) if my_ctl else None
            sp = BW.swap_arrive_spend(live, so.ARRIVE_ID, so.ARRIVE_ID, my_ctl, now - back_since if back_since is not None else -1, active)
            if sp != BW.ARRIVE_SPEND_NONE:
                if BW.swap_arrive_count(BW.ARRIVE_EV_SPEND, live, anchored, lead_ms if lead_ms is not None else BW.ARRIVE_LEAD_NONE,
                                        arm_c, late_c) & BW.ARRIVE_COUNT_UNANCHORED:
                    cnt["unanchored"] += 1
                live = False
                cnt["spends"][BW.ARRIVE_SPEND_NAMES[sp]] += 1
        epub = episode_pub and ep["on"] and k - ep["frame"] <= 2
        arr = dict(copy.deepcopy(cnt), arrival_lead_ms=K if k_pub is None else k_pub, armed=live,
                   field=so.ARRIVE_ID if field_pub is None else field_pub, land_t=G_T0, lead_ms=lead_ms, late=late,
                   host=host_at(now),
                   episode={"on": epub, "held": epub and ep["held"], "base_ms": ep["base"] if epub else None,
                            "dwell_ms": ep["dwell"] if epub else None, "shift_ms": ep["base"] - ep["dwell"] if epub else None},
                   last=dict(last), world=0, bench={"armed": bench_armed, "lead_ms": lead if bench_armed else None}, faults=0)
        s = S(now, field=so.ARRIVE_ID, ctl=my_ctl, sw={"levers.arrive": "old" if old else None})
        s["netsync"]["swap"]["arrive"] = arr
        # HarnessBaseAgeMs reads -1 while a step-out is active: an OUT frame publishes no base (the peak sits a frame under 1500)
        s["netsync"]["stepout"] = {"active": active, "why": "dwell" if active else None, "age_ms": now - out_t if active else -1,
                                   "base": {"age_ms": -1 if active else base}, "out_why": {"line": 0, "dwell": G_DWELL0 + dwells, "ate": 0}}
        samples.append(s)
        if my_ctl and active and now - (G_T0 + A) >= BW.ARRIVE_STEP_IN_MS:
            active = False                                   # s158's step-in: my control back for StepInMs
        if t >= A + so.G_CTL_BACK_MS + 2 * DT:
            break
        k += 1
    return samples, b0, step0


def g_rows(word=None):
    rows, marks, record = {}, {}, False
    for r in so.G_ROWS:
        s, b0, step0 = gsim(r, word)
        gx = so.g_reads(s, b0, step0)
        if r == "G-INERT":
            record = gx["bench_seen"]
        why = so.g_void(r, gx, record)
        rows[r] = (False, "VOID: " + why) if why else so.judge_g(r, gx, True if so.G_LEADS[r] is not None else None)
        marks[r] = {"gx": gx}
    return rows, marks


def solo_rows(word=None):
    rows, marks = dict(k_rows()), {}
    for fn in (a_rows, b_rows, c_rows, p_rows, l_rows, f_rows, g_rows):
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
    """K-REFUSE (the usage line three times -- [s164] `arrivebench 30602` out of range among them --, the bench refusal, co-op off),
    K-LEVER (each op's ack line and read-back; act reads null; [s164] `arrive old|act` in levers.arrive, `arrivebench L` in the bench's
    arm; `clear`, its CLEAR line and the bench forgotten), K-RELEASE (one release line, every lever back, the bench forgotten, a silent
    second reset, no leaked delay, no bench record at the next landing): each part alone red."""
    out = _child(_FIX + r'''
rf = lambda **kw: so.judge_refuse(dict(REFUSE, **kw))[0]
steps = lever_steps()
lv = lambda S_=steps, rest=REST, cl=CLEAR, bench=BENCH_REST: so.judge_levers(S_, rest, cl, bench)[0]
mut = lambda i, **kw: steps[:i] + [dict(steps[i], **kw)] + steps[i + 1:]
rl = lambda rel=RELEASE, after=REST, second=[], r=K_REC, f=33.0, bench=BENCH_REST, hb=False: so.judge_release(rel, after, second, r, f, bench, hb)[0]
at = {(s["op"], s["word"]): i for i, s in enumerate(steps)}
OUT = {"refuse": rf(), "lever": lv(), "release": rl(), "act_word": so.judge_levers(
           [dict(s, levers=dict(s["levers"], fade="act")) if s["op"] == "fade" and s["word"] == "act" else s for s in steps], REST, CLEAR,
           BENCH_REST)[0],
       "seq": [list(x) for x in so.K_LEVER_SEQ[-4:]], "set_all": [list(x) for x in so.K_SET_ALL[-2:]],
       "lines": [so.lever_line("arrive", "old"), so.lever_line("arrive", "act"), so.lever_line("arrivebench", "600")],
       "bad": {"r_delay_acted": rf(delay=""), "r_word": rf(word="netsync swap orphan: something else"), "r_bench": rf(bench=""),
               "r_off": rf(off=BW.swap_refusal_selftest("orphan")), "r_arrivebench_acted": rf(arrivebench=""),
               "r_arrivebench_role": rf(arrivebench=BW.swap_refusal_selftest("arrivebench")),
               "l_refused": lv(mut(4, ok=False, why="x")), "l_no_line": lv(mut(4, lines=[])), "l_wrong_line": lv(mut(6, lines=[L(so.lever_line("own", "act"))])),
               "l_readback": lv(mut(2, levers=dict(steps[2]["levers"], delay_ms=0))), "l_stamps": lv(mut(0, levers=dict(REST))),
               "l_hostctl": lv(mut(19, levers=dict(REST))), "l_rest": lv(rest=dict(REST, fade="long")), "l_rest_hostctl": lv(rest=dict(REST, hostctl_off=True)),
               "l_no_clear": lv(cl=[]), "l_clear_mirror": lv(cl=[L(BW.swap_harness_clear(True))]), "l_empty": lv(S_=[]),
               "l_arrive_old": lv(mut(at[("arrive", "old")], levers=dict(REST))),
               "l_arrive_act": lv(mut(at[("arrive", "act")], levers=dict(REST, arrive="old"))),
               "l_arrive_refused": lv(mut(at[("arrive", "old")], ok=False, why=BW.SWAP_USAGE)),
               "l_arrive_line": lv(mut(at[("arrive", "old")], lines=[L(so.lever_line("arrive", "act"))])),
               "l_bench_unarmed": lv(mut(at[("arrivebench", "600")], bench=dict(BENCH_REST))),
               "l_bench_lead": lv(mut(at[("arrivebench", "-400")], bench={"armed": True, "lead_ms": 600})),
               "l_bench_line": lv(mut(at[("arrivebench", "600")], lines=[L(so.lever_line("arrivebench", "-400"))])),
               "l_rest_arrive": lv(rest=dict(REST, arrive="old")), "l_rest_arrive_absent": lv(rest={k: v for k, v in REST.items() if k != "arrive"}),
               "l_rest_bench": lv(bench={"armed": True, "lead_ms": 600}), "l_rest_bench_absent": lv(bench=None),
               "x_two": rl(rel=RELEASE * 2), "x_none": rl(rel=[]), "x_mirror": rl(rel=[L(BW.swap_harness_release(True))]),
               "x_after": rl(after=dict(REST, orphan="old")), "x_second": rl(second=RELEASE),
               "x_leaked": rl(r=dict(K_REC, commit_t=5300)), "x_delay_ms": rl(r=dict(K_REC, delay_ms=500)), "x_never": rl(r=rec()),
               "x_arrive": rl(after=dict(REST, arrive="old")), "x_bench": rl(bench={"armed": True, "lead_ms": 1500}),
               "x_bench_wrote": rl(hb=True), "x_bench_unread": rl(hb=None)}}
''')
    assert out["refuse"] and out["lever"] and out["release"] and out["act_word"], out
    assert out["seq"] == [["arrive", "old"], ["arrive", "act"], ["arrivebench", "600"], ["arrivebench", "-400"]], out["seq"]
    assert out["set_all"] == [["arrive", "old"], ["arrivebench", "1500"]], out["set_all"]
    assert out["lines"] == ["[NetSync] harness: swap arrive OLD -- CALIBRATION: s158's dwell from the base start at every landing, no "
                            "arrival guard (released with the harness)", "[NetSync] harness: swap arrive ACT",
                            "[NetSync] harness: swap arrivebench 600 -- my next landing gets a bench host that landed 600 ms before me (the "
                            "selftest role; released with the harness)"], out["lines"]
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
    hiding behind its own stamp reds on the anchor alone, an end before the body reds on the bound). Guard-round live fix (run
    s164g-act, gap -15): the bound's floor is one TickCount step, -16 -- last_life_ms and body_ms ride two emit-tick baselines, so
    a life one tick short of its body is green and two ticks short (-17) is red."""
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
                land([ed(s, sw={"intent.landing": None}) for s in ls]), stands(lb), stands(lrun),
                stands(lb[:-1] + [ed(lb[-1], sw={"intent.last_life_ms": so.sget(lb[-1], "intent.body_ms") - 15})])],
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
               "stands_past_one_tick": stands(lb[:-1] + [ed(lb[-1], sw={"intent.last_life_ms": so.sget(lb[-1], "intent.body_ms") - 17})]),
               "stands_body_unread": stands([ed(s, sw={"intent.body_ms": -1}) for s in ls]),
               "stands_harness_unread": stands([ed(s, top={"player.uid": None}) for s in ls]),
               "stands_harness_home_only": stands([ed(s, top={"player.uid": None}) if s["field"]["id"] == AW else s for s in ls])}}
''')
    assert all(out["good"]), out
    # the body term: lsim(body_at=land + 1700) ends on the body, gap 0, the harness reading it in the same Update
    assert "body 2112 ms, harness_body 2112 ms, gap 0" in out["lb"], out["lb"]
    # the masking class reds ONLY on the independent anchor: its 3-term bound alone reads green (gap 0 behind the step's own stamp)
    sl = out["step_late"]
    assert "the engine saw my body no later than the harness) NO" in sl and "in [-16, 400] ok" in sl and "gap 0" in sl, sl
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


# ------------------------------------------------------------------------------------------------ G [ff9mapkit netsync s164]
def test_g_judges_are_green_on_the_guard_and_time_every_row_from_state():
    """Leg G (THE ARRIVAL GUARD, ARRIVAL-GUARD-S164.md "### Solo") on the engine's evidence, a frame at a time through battlewire's
    twins: every row green; each timed from STATE (arrive.land_t, clock.now_ms - stepout.age_ms, the episode's own base) at the values
    the rule gives -- G-HOLD's guarded peak ~A - K, G-DELAY's OUT at G + 1940 with shift 440 - (B - G), G-LATE's shift 1040 exactly
    (the cap), G-INERT's OUT at B + D with shift 0, G-OFF's OUT at the base start + D with lead_ms null on G-INERT's stale record."""
    out = _child(_FIX + r'''
rows, marks = g_rows()
gx = {r: m["gx"] for r, m in marks.items()}
lt = lambda r: gx[r]["out_t"] - gx[r]["land_t"]
# a base that flickered before the episode (s158 re-arms on a one-frame miss): B - G is the episode's own base, never the first one
s_re, b0_re, st_re = gsim("G-DELAY")
i_re = next(i for i, x in enumerate(s_re) if x["field"]["id"] == so.ARRIVE_ID)
s_re[i_re] = copy.deepcopy(s_re[i_re])
s_re[i_re]["netsync"]["stepout"]["base"]["age_ms"] = 0
gre = so.g_reads(s_re, b0_re, st_re)
OUT = {"rows": {r: list(v) for r, v in rows.items()}, "order": list(so.G_ROWS), "leads": so.G_LEADS,
       "rearm": [gre["b_minus_g"], so.judge_g("G-DELAY", gre, True)[0], gre["base_peak"] == gx["G-DELAY"]["base_peak"],
                 so.sget(s_re[i_re], "arrive.episode.on") is False],
       "hold": [gx["G-HOLD"]["dwell_peak"], gx["G-HOLD"]["base_peak"], gx["G-HOLD"]["out"], gx["G-HOLD"]["spend_t"] - gx["G-HOLD"]["back_t"]],
       "delay": [lt("G-DELAY"), gx["G-DELAY"]["last"]["shift_ms"], gx["G-DELAY"]["b_minus_g"], gx["G-DELAY"]["last"]["end"]],
       "late": [sorted(set(gx["G-LATE"]["shifts"])), gx["G-LATE"]["lead0"], gx["G-LATE"]["lead"], gx["G-LATE"]["late_arms"], gx["G-LATE"]["out"]],
       "inert": [lt("G-INERT"), gx["G-INERT"]["last"]["shift_ms"], gx["G-INERT"]["last"]["end"], gx["G-INERT"]["held"]],
       "off": [gx["G-OFF"]["out_t"] - gx["G-OFF"]["base_t"], gx["G-OFF"]["leads_null"], gx["G-OFF"]["unanchored"], gx["G-OFF"]["host_field"]],
       "rule": [so.arrive_shift_rule(66, 600), so.arrive_shift_rule(66, -429), so.arrive_shift_rule(66, 1500), so.arrive_shift_rule(None, 0)],
       "consts": [so.ARRIVE_ID, so.K_LEAD_MS, so.DWELL_MS, so.STEP_IN_MS, list(so.G_DELAY_OUT_MS), list(so.G_INERT_OUT_MS), so.LEGS]}
''')
    assert out["order"] == ["G-HOLD", "G-DELAY", "G-LATE", "G-INERT", "G-OFF"], out["order"]
    assert out["leads"] == {"G-HOLD": 0, "G-DELAY": 600, "G-LATE": -400, "G-INERT": 1500, "G-OFF": None}, out["leads"]
    assert all(v[0] for v in out["rows"].values()), {r: v[1] for r, v in out["rows"].items() if not v[0]}
    dp, bp, outd, spend = out["hold"]
    assert 1090 <= dp < 1500 and bp >= 1500 and outd is False and 500 <= spend <= 800, out["hold"]
    assert out["delay"] == [1947, 440 - 66, 66, "delayed"], out["delay"]
    assert out["late"][0] == [1040] and out["late"][1] is None and out["late"][2] < -400 and out["late"][3] == 1 and out["late"][4] is False, out["late"]
    assert 1500 <= out["inert"][0] <= 1700 and out["inert"][1:] == [0, None, 0], out["inert"]
    assert 1500 <= out["off"][0] <= 1500 + 33 + 16 and out["off"][1:] == [True, 1, 30611], out["off"]
    assert out["rule"] == [374, 1040, 0, None], out["rule"]
    assert out["consts"] == [30611, 1040, 1500, 500, [1880, 2090], [1500, 1700], "KABCPLFG"], out["consts"]
    # the re-armed base: the first (episode-less) base sample would read B - G 0 and the rule 440 -- 66 off the shift, a false red
    assert out["rearm"] == [66, True, True, True], out["rearm"]


def test_g_judges_can_go_red_on_each_part_and_p8_names_the_guard():
    """Each G row's every part alone red (a mutated measure); P8 extended to G -- an acked `arrivebench` with arrive.host.bench never
    true, arrive.field never 30611, no episode.on on G-HOLD / G-DELAY / G-LATE at act, a refused `arrivebench`, and an acked
    `arrivebench` the engine never ran on G-DELAY / G-LATE / G-INERT (the previous row's record still stands: bench true for 30611, the
    nonce unchanged -- only a FRESH nonce counts) -- reds the row 'the engine never ran the guard' (a foreign K is a plain red); the
    setup misses are VOID (never green, never a predicted red): no landing, a hold that never took my control, my control never back,
    G-HOLD short of DwellMs with no OUT, G-OFF without G-INERT's record (also through the real path: G-INERT's unrun write)."""
    out = _child(_FIX + r'''
rows, marks = g_rows()
gx = {r: m["gx"] for r, m in marks.items()}
j = lambda r, x=None, acked=True, **kw: so.judge_g(r, dict(x or gx[r], **kw), acked if so.G_LEADS[r] is not None else None)
def jl(r, **kw):
    x = dict(gx[r])
    x["last"] = dict(x["last"], **kw)
    return so.judge_g(r, x, True if so.G_LEADS[r] is not None else None)[0]
def sim(r, **kw):
    s, b0, step0 = gsim(r, **kw)
    return so.g_reads(s, b0, step0)
p8 = {"bench_never": j("G-HOLD", sim("G-HOLD", host_bench=False)), "field_never": j("G-DELAY", sim("G-DELAY", field_pub=-1)),
      "no_episode": j("G-LATE", sim("G-LATE", episode_pub=False)), "refused": j("G-INERT", acked=False),
      # an acked `arrivebench` the engine never ran, on the previous row's record (nothing clears R between G rows)
      "delay_unwritten": j("G-DELAY", sim("G-DELAY", bench_write=False)), "late_unwritten": j("G-LATE", sim("G-LATE", bench_write=False)),
      "inert_unwritten": j("G-INERT", sim("G-INERT", bench_write=False))}
def stale_stood(r):
    s, _b0, _st = gsim(r, bench_write=False)
    mine = [x for x in s if so.ival(so.sget(x, "arrive.field")) == so.ARRIVE_ID]
    return bool(mine) and all(so.sget(x, "arrive.host.bench") is True and so.ival(so.sget(x, "arrive.host.field")) == so.ARRIVE_ID
                              for x in mine)
fresh = {"stale_stood": [stale_stood(r) for r in ("G-DELAY", "G-LATE", "G-INERT")],
         "unwritten_seen": [sim(r, bench_write=False)["bench_seen"] for r in ("G-DELAY", "G-LATE", "G-INERT")],
         "written_seen": [gx[r]["bench_seen"] for r in so.G_ROWS], "pure_present": so.g_reads(gsim("G-DELAY")[0], None, None)["bench_seen"],
         "unread_b0_present": so.g_reads(gsim("G-DELAY", bench_write=False)[0], None, None)["bench_seen"]}
bad = {"hold_out": j("G-HOLD", out=True, out_why="dwell")[0], "hold_spared": j("G-HOLD", spared=0)[0], "hold_end": jl("G-HOLD", end="delayed"),
       "hold_field": jl("G-HOLD", field=30602), "hold_peak": j("G-HOLD", dwell_peak=1500)[0], "hold_spend": j("G-HOLD", spends_control=0)[0],
       "hold_spend_late": j("G-HOLD", spend_t=gx["G-HOLD"]["back_t"] + 801)[0],
       "delay_no_out": j("G-DELAY", out=False, out_why=None)[0], "delay_two": j("G-DELAY", dwell_outs=2)[0],
       "delay_line": j("G-DELAY", out_why="line")[0], "delay_early": j("G-DELAY", out_t=gx["G-DELAY"]["land_t"] + 1879)[0],
       "delay_late": j("G-DELAY", out_t=gx["G-DELAY"]["land_t"] + 2091)[0], "delay_count": j("G-DELAY", delayed=0)[0],
       "delay_end": jl("G-DELAY", end="spared"), "delay_shift": jl("G-DELAY", shift_ms=374 + 50),
       "late_not_late": j("G-LATE", late=False)[0], "late_arms": j("G-LATE", late_arms=0)[0], "late_twice": j("G-LATE", late_arms=2)[0],
       "late_uncapped": j("G-LATE", shifts=[1040, 1390])[0], "late_no_shift": j("G-LATE", shifts=[])[0],
       "late_out": j("G-LATE", out=True, out_why="dwell", out_before_back=True)[0],
       "inert_early": j("G-INERT", out_t=gx["G-INERT"]["land_t"] + 1499)[0], "inert_late": j("G-INERT", out_t=gx["G-INERT"]["land_t"] + 1701)[0],
       "inert_shift": j("G-INERT", shifts=[0, 40])[0], "inert_held": j("G-INERT", held=1)[0], "inert_no_out": j("G-INERT", out=False)[0],
       "off_host": j("G-OFF", host_field=30602)[0], "off_live": j("G-OFF", host_bench=False)[0], "off_lead": j("G-OFF", leads_null=False)[0],
       "off_early": j("G-OFF", out_t=gx["G-OFF"]["base_t"] + 1483)[0], "off_late": j("G-OFF", out_t=gx["G-OFF"]["base_t"] + 1550)[0],
       "off_unanchored": j("G-OFF", unanchored=0)[0], "off_spend": j("G-OFF", spends_out=0)[0],
       "k": j("G-HOLD", sim("G-HOLD", k_pub=1000))[0], "k_off": j("G-OFF", k=None)[0]}
void = {"no_landing": so.g_void("G-HOLD", so.g_reads([S(1000, field=HM)], None, None)),
        "never_off": so.g_void("G-DELAY", sim("G-DELAY", A=0)),
        "never_back": so.g_void("G-HOLD", dict(gx["G-HOLD"], back_t=None)),
        "hold_short": so.g_void("G-HOLD", sim("G-HOLD", A=1400)), "off_no_record": so.g_void("G-OFF", gx["G-OFF"], False),
        # through the real path: G-INERT's unrun write reads no fresh record, so G-OFF has no record of its own to refuse
        "off_inert_unwritten": so.g_void("G-OFF", gx["G-OFF"], sim("G-INERT", bench_write=False)["bench_seen"] is True),
        "hold_word_reached": so.g_void("G-HOLD", sim("G-HOLD", word="arrive")), "plain": [so.g_void(r, gx[r]) for r in so.G_ROWS]}
OUT = {"p8": {k: list(v) for k, v in p8.items()}, "bad": bad, "void": void, "word_peak": sim("G-HOLD", word="arrive")["base_peak"],
       "fresh": fresh}
''')
    for k, (ok, detail) in out["p8"].items():
        assert ok is False and detail.startswith("the engine never ran the guard: "), (k, detail)
    # THE FRESH-RECORD RULE: the stale record stood on every unrun row (the old presence test read it green), and only a fresh nonce
    # counts -- the bench part itself is what reds those rows; G-OFF (no write) never reads fresh; a pure caller (b0 None) keeps presence
    for k in ("delay_unwritten", "late_unwritten", "inert_unwritten"):
        assert "the bench wrote R (a fresh arrive.host.nonce for 30611) NO" in out["p8"][k][1], (k, out["p8"][k][1])
    fr = out["fresh"]
    assert fr["stale_stood"] == [True, True, True] and fr["unwritten_seen"] == [False, False, False], fr
    assert fr["written_seen"] == [True, True, True, True, False] and fr["pure_present"] is True and fr["unread_b0_present"] is True, fr
    assert not any(out["bad"].values()), {k: v for k, v in out["bad"].items() if v}
    v = out["void"]
    assert v.pop("plain") == [None] * 5, v
    assert "never landed" in v["no_landing"] and "never went off" in v["never_off"] and "never came back" in v["never_back"], v
    assert v["hold_short"].startswith("not reached: the raw base peaked at") and "G-INERT's bench record" in v["off_no_record"], v
    assert "G-INERT's bench record" in v["off_inert_unwritten"], v
    # the reach fix: under `arrive old` the published raw peak sits a frame UNDER 1500 (HarnessBaseAgeMs reads -1 once OUT), and the
    # dwell OUT itself is the reach -- never "not reached" on frame phase
    assert v["hold_word_reached"] is None and out["word_peak"] < 1500, (v, out["word_peak"])


def test_g_ctlback_stops_a_row_only_after_the_hold_and_one_second_of_control():
    """CtlBack (the watch's stop): never on HOME, never before my control went OFF on 30611 (the hold), and only once control has been
    back G_CTL_BACK_MS on the swap clock -- a control-off sample in between restarts the count."""
    out = _child(_FIX + r'''
def run(seq):
    cb_ = so.CtlBack(so.ARRIVE_ID)
    return [cb_(S(t, field=f, ctl=c)) for t, f, c in seq]
OUT = {"home": run([(0, HM, True), (2000, HM, True)]), "no_hold": run([(0, 30611, True), (1500, 30611, True)]),
       "hold": run([(0, 30611, False), (100, 30611, True), (1099, 30611, True), (1100, 30611, True)]),
       "restart": run([(0, 30611, False), (100, 30611, True), (900, 30611, False), (1000, 30611, True), (1999, 30611, True), (2000, 30611, True)])}
''')
    assert out == {"home": [False, False], "no_hold": [False, False], "hold": [False, False, False, True],
                   "restart": [False, False, False, False, False, True]}, out


# ------------------------------------------------------------------------------------------------ the calibrations
_REGISTERED = {
    "stamps": ["A-STAMP"], "delay": ["A-DELAY"], "orphan": ["B-HOLD", "B-RELEASE", "B-BLIP", "B-BLIP2", "B-SCENE"],
    "own": ["C-CACHE", "C-PEND"], "nocache": ["C-CACHE"], "pin": ["P-PIN", "P-PARTY"], "life": ["L-STANDS"],
    "fade": ["F-FAST", "F-3X", "F-BLACK", "F-JOIN", "F-HURRY", "F-OPEN", "F-AHEAD", "F-AGED", "F-RECHECK", "F-REASSERT", "F-KEY"],
    "long": ["F-FAST", "F-3X", "F-HURRY"], "nogate": ["F-OPEN", "F-AHEAD", "F-RECHECK", "F-KEY"], "norecheck": ["F-RECHECK"],
    "nohurry": ["F-HURRY"], "arrive": ["G-HOLD", "G-DELAY", "G-LATE"]}


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
    assert {"K-PROOF", "K-REFUSE", "K-LEVER", "K-RELEASE"} <= set(out["rows"]) and len(out["rows"]) == 43, out["rows"]
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
    assert c["{}"]["cal"] is None and c["{}"]["legs"] == "KABCPLFG" and c["{}"]["rows"] == 43 and c["{}"]["finals"] == []
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


def test_the_solo_leg_g_has_the_registered_shape():
    """Leg G's shape (source, [s164] THE ARRIVAL GUARD): run after F; refused before any warp when the engine publishes no
    `netsync.swap.arrive` or ARRIVE_ID 30611 is not registered (its explicit-id deploy command in the reason; a warp to an unregistered
    id hangs the game); each row from HOME: `hostscene 1`, then `swap arrivebench L`, then the warp as the step's ack only (Session.warp
    waits for control), sampled until my control has been back 1 s (CtlBack), `hostscene 0` in a finally; NO `swap clear` between
    rows; the `arrive` word's lever set before G-HOLD and back to act before G-INERT; G-OFF reads G-INERT's record (a FRESH one: g_reads
    keys it on arrive.host.nonce); a setup miss VOIDs; HOME's own guard spent (arrive.armed false) before the row's counter block b0,
    with no arrive.field term (a faulted guard leaves it stale: that must read P8 red, never UNREACHED)."""
    out = _child(r'''
import inspect
src = {n: inspect.getsource(getattr(so, n)) for n in ("run", "_leg_g", "_g_one", "_g_lever", "arrive_deploy_command", "g_reads")}
g1, lg = src["_g_one"], src["_leg_g"]
poll = g1[g1.index("_home(g)"):g1.index("b0 = _block(g)")]
OUT = {"after_f": src["run"].index('("F", _leg_f)') < src["run"].index('("G", _leg_g)'),
       "refused": "_unreached(led, ctx, G_ROWS" in lg and "netsync.swap.arrive" in lg and lg.index("ARRIVE_KEY") < lg.index("_g_one"),
       "registered": "g.registered_fields()" in lg and "arrive_deploy_command()" in lg and lg.index("registered_fields") < lg.index("_g_one"),
       "deploy": so.arrive_deploy_command(),
       "no_clear": '"clear"' not in lg and '"clear"' not in g1,
       "order": g1.index('_must(g, "hostscene", 1)') < g1.index('"arrivebench", lead') < g1.index('g.send(f"warp {ARRIVE_ID} 0 -1")'),
       "ack_only": "g.warp(" not in g1 and "until=CtlBack(ARRIVE_ID)" in g1,
       "scene_down": g1.index("finally:") < g1.index('_ns(g, "hostscene", 0)'),
       "home_first": g1.index("_home(g)") < g1.index('_must(g, "hostscene", 1)'),
       "word": 'want = "old" if word and row in WORDS["arrive"][1] else "act"' in lg and "ctx.lever_taken = True" in lg,
       "inert_record": 'if row == "G-INERT":' in g1 and "ctx.g_record" in g1 and "g_void(row, gx, ctx.g_record)" in g1
       and '"arrive.host.nonce"' in src["g_reads"],
       # HOME's own guard spent before the row's counter block (no `arrive.field` term: a faulted guard must read P8 red)
       "home_spent": g1.index("_home(g)") < g1.index('"arrive.armed"') < g1.index("b0 = _block(g)")
       and 'sget(s, "arrive.armed") is False' in poll and "raise HarnessError(" in poll and '"arrive.field"' not in poll,
       "void_wired": g1.index("g_void(") < g1.index("judge_g(") and "_void(led, ctx, [row], why)" in g1,
       "word_rows": list(so.WORDS["arrive"][1]), "catalog": [r for r in so.catalog(None, so.LEGS) if r.startswith("G-")],
       "standin_doc": "a C, P, L, F or G leg's sentinel keys" in so.__doc__}
''')
    assert out.pop("deploy") == ("py tools/deploy_field.py studies/movement/bench/lockt2-arrive.field.toml --id 30611 --mod-folder "
                                 "FF9CustomMap-msgs")
    assert out.pop("word_rows") == ["G-HOLD", "G-DELAY", "G-LATE"]
    assert out.pop("catalog") == ["G-HOLD", "G-DELAY", "G-LATE", "G-INERT", "G-OFF"]
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


#: [s164 hardening] THE STAND-IN RUNS ABOVE THE WORKERS. It drives a FakeGame on WALL time, so under `-n 6` the other workers could
#: preempt its frames: the s164 domain runs missed by a hair -- A-DELAY's commit-due 332 ms against 300 +- 17, B-CTLON's orphan at
#: 1915 ms against a 1920 bound -- and both passed alone. Every bound stays the bench's own (they are the REAL bench's judges:
#: widening them here would loosen what the stand-in proves); the stand-in children instead run at above-normal priority, so a
#: normal-priority worker's load cannot take their CPU. 0 off Windows (no such class; POSIX refuses a nonzero creationflags).
STAND_IN_PRIORITY = getattr(subprocess, "ABOVE_NORMAL_PRIORITY_CLASS", 0)

#: [s164 hardening] ...AND A MISS IS RE-RUN, NEVER RE-JUDGED. The priority alone did not hold: the next `-n 6` domain run missed
#: B-BLIP2's "closed at t0 + AutoReadMs (+0.3 s)" by load (its counters all read right) and it passed alone. So a child whose reds
#: are not the expected set is run AGAIN, whole and fresh, up to STAND_IN_TRIES in all, on the same bounds: the stand-in is a
#: deterministic model whose only nondeterminism is the scheduler, so a real defect reds on EVERY try and still fails the test,
#: while a scheduling miss clears. Each miss's detail is kept (`missed`), so a flake is visible, not silent.
STAND_IN_TRIES = 3


def _stand_in_launch(extra: dict, popen):
    env = {k: v for k, v in os.environ.items() if k not in ("COOP_CALIBRATE", "COOP_LEGS")}
    env.update(extra)
    return popen([sys.executable, "-X", "utf8", "-c", _STAND_IN], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                 text=True, cwd=str(SCEN), env=env, creationflags=STAND_IN_PRIORITY)


def _stand_in_read(name: str, p) -> dict:
    so_, se = p.communicate(timeout=480)
    assert p.returncode == 0, (name, se[-3000:])
    doc = json.loads(next(ln for ln in so_.splitlines() if ln.startswith("@@"))[2:])
    return {"red": sorted(c for c, ok, _d in doc["rows"] if not ok), "all": [c for c, _ok, _d in doc["rows"]],
            "detail": {c: d for c, _ok, d in doc["rows"]}, "notes": doc["notes"]}


def _stand_in(runs: dict, popen=subprocess.Popen, want: dict | None = None) -> dict:
    """Run each stand-in child (concurrently); with ``want`` (name -> its expected sorted reds), re-run a child whose reds differ,
    up to STAND_IN_TRIES runs in all. Each result carries ``tries`` and ``missed`` (the earlier tries' unexpected reds + detail)."""
    want = want or {}
    procs = {name: _stand_in_launch(extra, popen) for name, extra in runs.items()}
    out = {}
    for name, p in procs.items():
        missed = []
        for n in range(1, STAND_IN_TRIES + 1):
            res = _stand_in_read(name, p)
            if name not in want or res["red"] == want[name] or n == STAND_IN_TRIES:
                break
            missed.append({k: res["detail"].get(k) for k in sorted(set(res["red"]) ^ set(want[name]))})
            p = _stand_in_launch(runs[name], popen)
        out[name] = {**res, "tries": n, "missed": missed}
    return out


def test_the_stand_in_runs_above_the_xdist_workers_priority():
    """[s164 hardening] Each stand-in child is launched at STAND_IN_PRIORITY (above normal on Windows), the load-tolerance that
    keeps every wall-clock bound the bench's own -- break it (drop the creationflags) and this goes red."""
    seen = []

    class _P:
        returncode = 0

        def communicate(self, timeout=None):
            return '@@{"rows": [["K-PROOF", true, "ok"]], "notes": []}\n', ""

    def popen(argv, **kw):
        seen.append(kw)
        return _P()

    out = _stand_in({"a": {"COOP_LEGS": "K"}, "b": {"COOP_LEGS": "K"}}, popen=popen)
    assert sorted(out) == ["a", "b"] and out["a"]["all"] == ["K-PROOF"], out
    assert len(seen) == 2 and all(kw.get("creationflags") == STAND_IN_PRIORITY for kw in seen), seen
    if os.name == "nt":
        assert STAND_IN_PRIORITY == subprocess.ABOVE_NORMAL_PRIORITY_CLASS != 0


def test_a_stand_in_miss_is_rerun_whole_but_a_steady_red_still_fails():
    """[s164 hardening] A child whose reds are not the expected set is launched AGAIN (fresh, same env, same bounds), up to
    STAND_IN_TRIES runs: a one-off miss clears and is kept in `missed`; a red on every try comes back red after exactly
    STAND_IN_TRIES launches; without ``want`` nothing is re-run. Break it (STAND_IN_TRIES = 1, or drop the re-launch) -> red."""
    green = '@@{"rows": [["B-BLIP2", true, "ok"]], "notes": []}\n'
    red = '@@{"rows": [["B-BLIP2", false, "closed at t0 + AutoReadMs (+0.3 s) NO"]], "notes": []}\n'

    def popen_of(script):
        launched = []

        class _P:
            returncode = 0

            def __init__(self, text):
                self.text = text

            def communicate(self, timeout=None):
                return self.text, ""

        def popen(argv, **kw):
            launched.append(kw["env"].get("COOP_LEGS"))
            return _P(script[min(len(launched), len(script)) - 1])
        return popen, launched

    popen, launched = popen_of([red, green])
    out = _stand_in({"plain": {"COOP_LEGS": "KAB"}}, popen=popen, want={"plain": []})["plain"]
    assert out["red"] == [] and out["tries"] == 2 and launched == ["KAB", "KAB"], (out, launched)
    assert out["missed"] == [{"B-BLIP2": "closed at t0 + AutoReadMs (+0.3 s) NO"}], out["missed"]

    popen, launched = popen_of([red])
    out = _stand_in({"plain": {"COOP_LEGS": "KAB"}}, popen=popen, want={"plain": []})["plain"]
    assert out["red"] == ["B-BLIP2"] and out["tries"] == STAND_IN_TRIES == 3 and len(launched) == 3, (out, launched)

    popen, launched = popen_of([red, green])
    out = _stand_in({"plain": {"COOP_LEGS": "KAB"}}, popen=popen)["plain"]
    assert out["red"] == ["B-BLIP2"] and out["tries"] == 1 and len(launched) == 1, (out, launched)


def test_the_solo_bench_runs_green_on_the_stand_in_with_legs_kab():
    """The WHOLE solo bench (coop_field_swap_timing.run) on the s164 stand-in with COOP_LEGS=KAB -- the legs it models (P8): every row
    green, in the run's order; K-CLOCK GREEN on the stand-in's clock seam on Windows (its note; SKIP off Windows), never a ledger row."""
    out = _stand_in({"plain": {"COOP_LEGS": "KAB"}}, want={"plain": []})["plain"]
    assert out["red"] == [], ({k: out["detail"][k] for k in out["red"]}, out["missed"])
    assert out["all"] == _KAB, out["all"]
    clock = [n for n in out["notes"] if n.startswith("K-CLOCK (a load-time precondition")]
    assert len(clock) == 1 and ("GREEN: src qpc" in clock[0] if os.name == "nt" else "SKIP:" in clock[0]), out["notes"]
    assert "every lever at rest ok" in out["detail"]["K-LEVER"] and "closed by line or window ok" in out["detail"]["A-FOLLOW"]


def test_the_stand_in_calibrates_stamps_delay_and_orphan_exactly():
    """On the stand-in, the three words it can carry calibrate EXACTLY: `stamps` (COOP_LEGS=KA) reds A-STAMP alone, `delay` (KA)
    A-DELAY alone, `orphan` (KB) B-HOLD, B-RELEASE, B-BLIP, B-BLIP2 and B-SCENE -- each with K-CAL-M (the marker) and K-CAL green."""
    want = {"stamps": ["A-STAMP"], "delay": ["A-DELAY"], "orphan": sorted(["B-HOLD", "B-RELEASE", "B-BLIP", "B-BLIP2", "B-SCENE"])}
    out = _stand_in({"stamps": {"COOP_LEGS": "KA", "COOP_CALIBRATE": "stamps"}, "delay": {"COOP_LEGS": "KA", "COOP_CALIBRATE": "delay"},
                     "orphan": {"COOP_LEGS": "KB", "COOP_CALIBRATE": "orphan"}}, want=want)
    for w, reds in want.items():
        o = out[w]
        assert o["red"] == reds, (w, {k: o["detail"][k] for k in o["red"]}, o["missed"])
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


def Sx(t, field, ctl=True, sw=None, step=None, want=-1, leader=-1, texts=None, ui="FieldHUD", scene="FieldMap", eff=-1, **kw):
    """A duo sample: the solo's S() plus the keys the duo reads (stepout, dress.self / guard -- [s164] guard.effective, DP-DRESS's
    section-8 pick --, dialog, ui_state, scene)."""
    s = S(t=t, field=field, ctl=ctl, sw=sw, **kw)
    s["netsync"]["stepout"] = {"active": False, "base": {"age_ms": -1}, "out_why": {"line": 0, "dwell": 0, "ate": 0}}
    for k, v in (step or {}).items():
        _put(s["netsync"]["stepout"], k, v)
    s["netsync"]["dress"]["self"] = {"want_char": want}
    s["netsync"]["dress"]["guard"] = {"leader": leader, "effective": eff}
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


def cal_arrive(sub, kind, word, life, land, hland, ov, bp):
    """[s164] THE ARRIVAL GUARD at one CAL landing (arrive_evidence's shape): R from the host's landed frame -- none under `life old`
    (no landed frame is sent); lead_ms the landing gap (~0.5 s at act, ~1.04 s on fade old); an episode with its rule's shift on a
    base (the gate and the controls); the gate under the `arrive` word unarmed (levers.arrive old: no episode)."""
    old = kind == "gate" and word == "arrive"
    lead = None if life else (1040 if cal_shape(sub, word)[0] == "old" else 500)
    episode = kind in ("gate", "control") and lead is not None and not old
    shift = du.arrive_shift_rule(60, lead) if episode else None
    return {"lever": "old" if old else None, "armed": not old, "lead": lead, "lead_ep": lead, "late": False, "shift": shift,
            "dwell_peak": bp - shift if shift is not None else None, "b_minus_g": 60, "land_t": land,
            "seen_t": hland + 70 if lead is not None else None, "base_end_t": land + ov + 100}


def cal_tr(i, sub, dest, word=None, kind=None, on=True):
    T0 = 100000 * (i + 1)
    frm = du.HOME if dest != du.HOME else du.AWAY
    path, action, frames, by, due_after, ticks, delay = cal_shape(sub, word)
    life = word == "life" and du.cal_life(sub) == "old"          # [s164] the `life` scope: the ARRIVE runs keep `life act`
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
    out_ = kind == "gate" and word == "arrive"                  # [s164] the guard off: round 1's dwell OUT at ~1.5 s of base
    if out_:
        gl.append(DWELL_OUT(dest))
    ov = {"gate": 1800, "control": 1250, "watch": 1300}.get(kind, 600)
    bp = 1485 if out_ else ov - 100                              # an OUT run publishes its peak a frame under 1500 (then -1)
    arr = cal_arrive(sub, kind, word, life, land, hland, ov, bp)
    g0 = block(last__id=10 + i - 1, counts__landings=i, arrive__ends__spared=3, arrive__last__field=du.HOME)
    if arr["shift"] is not None and kind == "gate":              # the guard's held episode, classified spared
        g["arrive"] = dict(g["arrive"], ends=dict(g["arrive"]["ends"], spared=4),
                           last=dict(g["arrive"]["last"], field=dest, end="spared", lead_ms=arr["lead"], shift_ms=arr["shift"]))
    else:
        g["arrive"] = dict(g["arrive"], ends=dict(g["arrive"]["ends"], spared=3), last=dict(g0["arrive"]["last"]))
    return {"lane": "CAL", "sub": sub, "kind": kind, "dest": dest, "from": frm, "h": h, "g": g, "hi": hi,
            "h0": block(last__id=20 + i - 1), "g0": g0, "g_land_t": land, "h_land_t": hland,
            "h_ctl_t": land + ov, "overlap": ov, "base_peak": bp, "dwell_count": 1 if out_ else 0, "active": out_, "dressed": False,
            "party_emit": [0, 1, 2, 3], "party_land": [0, 1, 2, 3], "mirror_after": [0, 1, 2, 3], "arrive": arr, "hl": hl, "gl": gl}


def cal_trs(word=None, on=True):
    out, i = {}, 0
    for name, _fade, _delay, _speed, dest, k_out, k_home in du.cal_subs(word):
        for to, kind in ((dest, k_out), (du.HOME, k_home)):
            out.setdefault(name, []).append(cal_tr(i, name, to, word, kind, on))
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
        # [s164] review round 2: FF9Wipe_FadeOutEx forces the screen visible (the flash) BEFORE NoteFollow stamps follow_t, so the
        # engine's window opens on the rise (the act run's REST-OLD wipe, follow_t 233024817): DF-FLASH reds it by its action
        cur = [0, 10, 21, 31, 42, 52, 63]
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
        lead = None if life else land - hland                # [s164] the guard's anchor: R from the host's landed frame (none under life)
        arr = {"lever": None, "armed": True, "lead": lead, "lead_ep": lead, "late": lead is not None and lead < 0, "shift": None,
               "dwell_peak": None, "b_minus_g": None, "land_t": land, "seen_t": hland + 60 if lead is not None else None, "base_end_t": None}
        return {"lane": lane, "sub": f"D{D}", "kind": kind, "dest": dest, "from": frm, "h": h, "g": g, "hi": hi_(t), "h0": {}, "g0": {},
                "g_land_t": land, "h_land_t": hland, "h_ctl_t": land + 200, "overlap": 200, "base_peak": 150, "dwell_count": 0,
                "active": False, "dressed": True, "party_emit": [0, 1, 2, 3], "party_land": [0, 1, 2, 3], "mirror_after": [0, 1, 2, 3],
                "arrive": arr, "hl": [], "gl": []}
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
            g3["counts"] = dict(g3["counts"], bounces=1)   # s163's rule: the bounce reloads 351, then the follow loads 352 once
        else:
            g3["last"] = dict(g3["last"], own_verdict="pass", own_why="pending")
            g3["own"] = dict(g3["own"], passes=1, converted=1, last=dict(g3["own"]["last"], term="pending"))
    else:
        g3["last"] = dict(g3["last"], own_verdict="pass", own_why="pending")
        g3["own"] = dict(g3["own"], passes=1, converted=1, last=dict(g3["own"]["last"], term="pending"))
    pre = Sx(T + 120000 + 150, 351, pending=352, sw={"own.host_lane": 351})
    commit_t = t351["g"]["last"]["commit_t"]
    return {"D": D, "old": old, "t359": t359, "t351": t351, "t352": t352,
            "fade": {"D": D, "old": old, "fade": fl, "cur": cur, "commit_t": commit_t if commit_t >= 0 else None,
                     "last_close_t": (commit_t - 300) if commit_t >= 0 else None,
                     # [s164] fix round 3: the 351 record's own edges (desk_evidence's `last`): the follow, then the copy's own jump
                     "last": {k: t351["g"]["last"].get(k) for k in du.DESK_REC_KEYS}},
            "rest": {"D": D, "g": g3, "g0": g0, "maps": maps, "pre": pre, "l139": 150, "g_land_t": t352["g_land_t"],
                     "h_land_t": t352["h_land_t"]},
            "halt": {"g0": block(pin__pre_frames=4), "g": block(pin__pre_frames=6, pin__max_pre_diff=0)},
            # [s164] the first duo run's 352 shape: the host walks as Garnet (2), the guest owns Steiner's slot (GuestSlots 0x2), so
            # section 8 -- and want_char -- name Steiner (3), never the leader
            "dress": {"want": 3, "expect": 3, "leader": 2}, "lines": lines_run(T + 60000, on), "won": {"desk": (0, {}), "rest": (0, {})}}


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
MENU_RID, MENU_SEEN = 45, MC - 1200
MENU_F0 = 500000                                         # [s164] fix round 3 review: the last Pause sample's frame in menu_ring


def menu_ring(rid=MENU_RID, seen=MENU_SEEN, last_on=MC - 10, close=MC + 7, follow=MC + 60, step=17, paused_follow=False,
              close_frames=None):
    """[s164] Fix round 3: the guest's ring across the MENU Pause as DL-DEFER reads it (ring_since from before the Pause press, slimmed):
    the record before (rid - 1) on Pause with ITS follow_t >= 0 (the guarded duo's #44: an unkeyed check reds falsely), record ``rid``
    seen at ``seen`` while paused, the last Pause sample at ``last_on``, the first off it at ``close`` (FieldHUD), then this record's
    follow at ``follow`` (follow_t -1 on every sample before it; ``paused_follow`` stamps it on this record's Pause samples too).
    [s164] Fix round 3 review: every sample carries its frame on the ``step`` clock (S() would derive t // 33): the last Pause sample
    is frame MENU_F0, the first off it ``close_frames`` later (default: the bracket's width in steps, at least 1)."""
    xs = []
    cf = close_frames if close_frames is not None else max(1, round((close - last_on) / step))
    for t in range(last_on - ((last_on - (seen - 300)) // step) * step, last_on + 1, step):
        mine = t >= seen
        sw = {"last.id": rid if mine else rid - 1, "last.seen_t": seen if mine else seen - 3000,
              "last.follow_t": (follow if paused_follow else -1) if mine else seen - 3000}
        xs.append(du.slim(Sx(t, du.HOME, ui="Pause", sw=sw, frame=MENU_F0 + (t - last_on) // step)))
    t, k = close, 0
    while t <= max(close, follow) + 2 * step:
        xs.append(du.slim(Sx(t, du.HOME, frame=MENU_F0 + cf + k,
                             sw={"last.id": rid, "last.seen_t": seen, "last.follow_t": follow if t >= follow else -1})))
        t, k = t + step, k + 1
    return xs


def menu_ev(word=None, aged=False):
    """[s164] Fix round 3: the record (last.id 45, seen while paused) and the guest's ring (menu_ring) DL-DEFER / DP-DEFER bracket the
    close off (the watch's menu_close_t is no longer evidence)."""
    if aged:
        return {"g": block(last__follow_via="intent", last__follow_t=MC + 3550, pin__last_use="aged", pin__last_use_quality="pre",
                           pin__last_use_age_ms=3100), "menu_close_t": MC + 3500, "flag": True}
    if word == "life":
        g = block(last__id=MENU_RID, last__seen_t=MENU_SEEN, last__open_t=MENU_SEEN, last__follow_via="serial", last__follow_t=MC + 1300,
                  pin__last_use="none", pin__last_use_quality="none")
        return {"g": g, "ring": menu_ring(follow=MC + 1300), "flag": True}
    lever = word == "pin"
    g = block(last__id=MENU_RID, last__seen_t=MENU_SEEN, last__open_t=MENU_SEEN, last__follow_via="intent", last__follow_t=MC + 60,
              last__land_t=MC + 600, pin__last_use="lever" if lever else "pin", pin__last_use_quality="pre", pin__last_use_age_ms=1300,
              pin__last_diff=1, pin__late=0)
    return {"g": g, "ring": menu_ring(), "flag": lever}


def mark_ev(word=None, on=True):
    LT = 9500000
    lever = word == "pin"
    g = block(last__land_t=LT, pin__last_use="lever" if lever else "pin", pin__last_use_quality="pre", pin__last_diff=1)
    gl = [] if lever else [L(BW.pin_log_stages(on, du.AWAY, 5, 900, 1, LT))]
    return {"g": g, "flag": lever, "host_flag_t": LT - 700, "gl": gl, "dest": du.AWAY}


def left_ev(on=True):
    """[s164] LEFT on HOME: intent 7 live at the battle's send (pre), ended Left at its swirl (the host's first sample off FieldMap
    30 ms later), the guest's last copy 60 ms after that."""
    S0 = 9800000
    return {"n": 7, "pre": {"active": True, "nonce": 7, "now_ms": S0 - 400, "end_t": -1, "last_end": "stands"},
            "h": block(intent__nonce=7, intent__active=False, intent__last_end="left", intent__end_t=S0),
            "g": block(seen__nonce=7, seen__last_t=S0 + 90),
            "hl": [L(BW.life_log_ended(on, 7, du.HOME, 1100, BW.INTENT_END_LEFT, S0))], "dest": du.HOME, "swirl_t": S0 + 30}


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
       "guest_hostctl": "the game refused a step: netsync: " + BW.swap_refusal_selftest("hostctl"),
       "host_arrive": "the game refused a step: netsync: " + BW.swap_refusal_guest_side("arrive"),
       "guest_arrivebench": "the game refused a step: netsync: " + BW.swap_refusal_selftest("arrivebench")}


def duo_rows(word=None, clock_ok=True):
    """Every duo row's (status, detail) on the engine's evidence under ``word`` (None: the plain run), and each row's marker evidence.
    [s164] THE ARRIVAL GUARD is on: the plain ARRIVE gate is the guard's green (no dwell OUT); the `arrive` word turns it off there."""
    on = word != "stamps"
    cal = cal_trs(word, on)
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
        "DA-ARRIVE": du.judge_da_arrive(arrivals, clock_ok, "", 33.0),
        "DA-GUARD": du.judge_da_guard(lane, life_word=word == "life", clock_ok=clock_ok),
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
             "DF-FLASH": {"fades": fades}, "DF-PACE": {"fades": pace}, "DF-OPEN": {"fades": [{"fade": open_ev(word)["fade"]}]},
             "DA-ARRIVE": {"gate": next(a for a in arrivals if a["kind"] == "gate")}}
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
    for v in ("", "0") + tuple(["stamps", "delay", "orphan", "own", "nocache", "pin", "life", "fade", "long", "nogate", "arrive"]):
        cases[v] = _duo_child(r'''
OUT = {"mode": du.CAL_MODE, "rows": sorted(k for k in du.catalog(du.CAL_MODE, du.LEGS_SEL) if k.startswith("D-CAL")),
       "solo_mode": so.CAL_MODE, "solo_legs": so.LEGS_SEL}
''', {"COOP_CALIBRATE": v}, fix=False)
    assert cases[""]["mode"] is None and cases["0"]["mode"] is None and cases[""]["rows"] == []
    for v, c in cases.items():
        assert c["solo_mode"] is None and c["solo_legs"] == "KABCPLFG", (v, c)
        if v not in ("", "0"):
            assert c["mode"] == v and c["rows"] == ["D-CAL", "D-CAL-M"], (v, c)
    for env in ({"COOP_CALIBRATE": "s163"}, {"COOP_CALIBRATE": "1"}, {"COOP_CALIBRATE": "norecheck"}, {"COOP_CALIBRATE": "nohurry"},
                {"COOP_LEGS": "CAL,BOGUS"}, {"COOP_LEGS": "K"}, {"COOP_CALIBRATE": "fade", "COOP_LEGS": "CAT"},
                {"COOP_CALIBRATE": "orphan", "COOP_LEGS": "CAL,DESK"}, {"COOP_CALIBRATE": "own", "COOP_LEGS": "CAL"},
                {"COOP_CALIBRATE": "arrive", "COOP_LEGS": "DESK,LEVERS"}):
        r = _run_duo_child("OUT = {}", env, fix=False)
        assert r.returncode == 1 and "coop_field_swap_timing_duo: COOP_" in r.stderr and "before the pair boots" in r.stderr, (env, r.stderr[-600:])
        assert "@@" not in r.stdout
    ok = _duo_child(r'''OUT = {"legs": du.LEGS_SEL, "cat": sorted(du.catalog(du.CAL_MODE, du.LEGS_SEL))}''',
                    {"COOP_LEGS": "rest, cat", "COOP_CALIBRATE": "orphan"}, fix=False)
    assert ok["legs"] == "DESK,CAT" and "DB-HOLD" in ok["cat"] and "DA-LANE" in ok["cat"] and "DA-CAL" not in ok["cat"], ok


def test_duo_catalog_words_and_the_arrive_field_are_the_registered_ones():
    """The catalog is the design's duo table (every row id, DK-CLOCK / DC-WON / DA-PROBE-X reported as notes, never rows; [s164]
    DA-GUARD beside DA-LANE), the eleven words red exactly the design's rows ([s164] `arrive`: DA-ARRIVE, the guard's calibration),
    BASELINE_RED is empty and DA-ARRIVE has left CROSS_GAME, and the ARRIVE field is a scratch copy of LOCKT2 with `[camera]
    entry_settle = 64` (retuned from 68, ARRIVE_SETTLE_TICKS) at a dev-scratch id outside 30602 and the world-map hole, deployed with
    that explicit id (deploy_argv) and never inside a run."""
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
       "legs_rows": sorted(r for rows in du.LEG_ROWS.values() for r in rows) + ["DA-LANE", "DA-GUARD", "DP-PARTY"],
       "baseline": list(du.BASELINE_RED), "cross": list(du.CROSS_GAME), "prob": "DA-GUARD" in du.PROBABILISTIC,
       "word_legs": list(du.WORD_LEGS["arrive"]), "ticks": du.ARRIVE_SETTLE_TICKS,
       "life_word": du.WORDS["life"][0], "life_doc": "both ARRIVE runs keep `life" in du.__doc__}
''')
    want_rows = ["DA-ARRIVE", "DA-CAL", "DA-GUARD", "DA-JOIN", "DA-LANE", "DA-LINES", "DA-PROBE", "DB-BIT", "DB-HOLD", "DB-ORDER", "DB-SHAPE",
                 "DC-B(a)", "DC-B(b)", "DC-FE", "DC-OWN", "DF-3X", "DF-FAST", "DF-FLASH", "DF-GRACE", "DF-OPEN", "DF-PACE", "DL-DEFER",
                 "DL-LEFT", "DL-LIFE", "DL-NOREG", "DP-AGED", "DP-DEFER", "DP-DRESS", "DP-HALT", "DP-MARK", "DP-PARTY", "LVD-LIFE",
                 "LVD-ROLE"]
    assert out["rows"] == want_rows and sorted(out["legs_rows"]) == want_rows, out["rows"]
    assert out["reported"] == ["DK-CLOCK", "DC-WON", "DA-PROBE-X"]
    assert out["words"] == {"stamps": [["DA-LINES"], []], "delay": [["DA-CAL"], []], "orphan": [["DB-HOLD", "DB-ORDER"], []],
                            "own": [["DC-B(b)"], []], "nocache": [[], []], "pin": [["DP-MARK", "DP-DEFER"], []],
                            "life": [["DL-LIFE", "DL-DEFER"], []], "fade": [["DF-FAST", "DF-3X", "DF-FLASH", "DF-OPEN"], ["DF-PACE"]],
                            "long": [["DF-FAST", "DF-3X"], []], "nogate": [["DF-OPEN"], ["DF-PACE"]], "arrive": [["DA-ARRIVE"], []]}, out["words"]
    assert out["baseline"] == [] and out["cross"] == ["DA-LANE", "DB-BIT", "DP-MARK", "DL-LEFT"] and out["prob"], out
    assert out["word_legs"] == ["CAL"] and out["ticks"] == 64, out
    assert "both ARRIVE runs keep `life act`" in out["life_word"] and out["life_doc"], out["life_word"]
    assert out["id"] == out["toml_id"] and 30000 <= out["id"] <= 32767 and out["id"] != 30602, out
    assert out["settle"] == 64 == out["ticks"] and out["base_settle"] == "auto" and all(out["same_rest"].values()), out
    assert out["argv"] == [str(REPO / "studies/movement/bench/lockt2-arrive.field.toml"), "--id", str(out["id"]), "--mod-folder",
                           "FF9CustomMap-msgs"], out["argv"]
    assert f"--id {out['id']}" in out["cmd"] and out["no_deploy_in_run"], out


def test_dk_clock_voids_every_cross_game_row_and_rows_inside_one_game_still_judge():
    """DK-CLOCK unfit (K-CLOCK failing on either game): DA-LANE, DB-BIT, DP-MARK and DL-LEFT read VOID with the reason, never red;
    DF-FAST and DC-B(a) lose only their cross-game gap clause, DA-LINES only its host-tap clause, [s164] DA-ARRIVE only its overlap
    clause and its cross-game reports (it left CROSS_GAME: its in-game clauses still judge) and DA-GUARD only its seen - landing report;
    every row inside one game judges as before. On a fit clock the plain evidence is all green (THE ARRIVAL GUARD: no baseline red)."""
    out = _duo_child(r'''
fit, _m = duo_rows()
unfit, _m2 = duo_rows(clock_ok=False)
OUT = {"fit": {r: v[0] for r, v in fit.items()}, "unfit": {r: v[0] for r, v in unfit.items()},
       "why": unfit["DA-LANE"][1], "fast": unfit["DF-FAST"][1], "arrive": unfit["DA-ARRIVE"][1], "guard": unfit["DA-GUARD"][1]}
''')
    fit, unfit = out["fit"], out["unfit"]
    assert not [r for r, s in fit.items() if s in ("red", "void")], fit
    assert sorted(r for r, s in unfit.items() if s == "void") == ["DA-LANE", "DB-BIT", "DL-LEFT", "DP-MARK"], unfit
    for r in ("DF-FAST", "DC-B(a)", "DA-LINES", "DA-CAL", "DB-HOLD", "DP-DEFER", "DA-ARRIVE", "DA-GUARD"):
        assert unfit[r] == fit[r], (r, unfit[r], fit[r])
    assert "DK-CLOCK" in out["why"] and "never red" in out["why"] and "VOID: DK-CLOCK unfit (the gap clause)" in out["fast"], out
    assert "the overlap clause and the cross-game reports VOID" in out["arrive"] and "overlap VOID" in out["arrive"], out["arrive"]
    assert "retune check VOID" in out["arrive"] and "seen - host landing VOID" in out["guard"], out


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


_DA_A = r'''
def A(kind="gate", ov=1800, bp=1700, lines=0, cnt=0, active=False, dressed=False, sub="ARRIVE", **kw):
    """One arrival as arrival_of shapes it; a gate defaults to THE ARRIVAL GUARD's green (lead 500 in time, B - G 60, its rule's
    shift 480, the episode spared on 30611)."""
    a = {"kind": kind, "sub": sub, "dest": 30611, "overlap": ov, "base_peak": bp, "dwell_lines": lines, "dwell_count": cnt,
         "active": active, "dressed": dressed, "lever": None, "armed": True, "lead": 500, "lead_ep": 500, "late": False, "shift": 480,
         "dwell_peak": bp - 480 if bp is not None else None, "b_minus_g": 60, "last_field": 30611, "last_end": "spared", "spared": 1,
         "gap": 500, "A": 2200, "dx": 70, "d7": 100}
    a.update(kw)
    return a
CTL = A("control", 1250, 1200, sub="ARRIVE-OLD", lead=1040, lead_ep=1040, shift=0, last_end=None, spared=0)
j = lambda *a, ok=True: du.judge_da_arrive(list(a), ok, "unfit for the test", 33.0)
'''


def test_da_arrive_must_reach_its_exposure_and_judges_every_arrival_kind():
    """DA-ARRIVE, THE ARRIVAL GUARD's calibration ([s164]): the ARRIVE gate must REACH its exposure -- the overlap >= DwellMs + 100 AND
    (the raw base peak >= DwellMs OR a dwell OUT: the reach fix -- an OUT run's published peak sits within a frame of 1500); short of
    it red 'not reached', never green. A reached gate with no dwell OUT whose green is attributable to the guard (last 30611 spared,
    spared +1, levers.arrive null, the shift its rule's) is green; a fade-old control's OUT is red (a control-desk's dwell OUT too; its
    OUT by line is lawful). [s164] The dressed WATCHES (CAL2, DESK) are listed apart and REPORTED, never folded into the verdict: a
    watch's dwell OUT names itself under "watches (reported apart, never judged)" and the row stays green; an undressed watch is not
    even listed. An unfit clock drops only the overlap clause."""
    out = _duo_child(_DA_A + r'''
OUT = {"guard": j(A(), CTL)[0], "overlap_short": list(j(A(ov=1599), CTL)), "base_short": j(A(bp=1499), CTL)[0], "no_gate": j(CTL)[0],
       "base_absent": j(A(bp=None), CTL)[0],
       "control_out": j(A(), dict(CTL, dwell_count=1))[0],
       "watch_undressed": j(A(), CTL, A("watch", cnt=1, sub="CAL2"))[0],
       "watch_dressed": j(A(), CTL, A("watch", cnt=1, dressed=True, sub="CAL2"))[0],
       "desk_line_out": j(A(), CTL, A("watch-desk", active=True, dressed=True, sub="D0.3"))[0],
       "desk_dwell": j(A(), CTL, A("watch-desk", lines=1, dressed=True, sub="D0.3"))[0],
       "control_desk_line": j(A(), CTL, A("control-desk", active=True, sub="D0.3"))[0],
       "control_desk_dwell": j(A(), CTL, A("control-desk", cnt=1, sub="D0.3"))[0],
       "watch_rep": j(A(), CTL, A("watch", cnt=1, dressed=True, sub="CAL2"), A("watch-desk", cnt=1, dressed=True, sub="D1.0"),
                      A("watch-desk", dressed=True, sub="D2.5"), A("watch", cnt=1, sub="CAL3"))[1],
       "unfit_short_overlap": j(A(ov=900), CTL, ok=False)[0], "unfit_short_base": j(A(ov=900, bp=1499), CTL, ok=False)[0],
       "reached": [du.arrive_reached(A()), du.arrive_reached(A(ov=1600, bp=1500)), du.arrive_reached(A(ov=1599)),
                   du.arrive_reached(A(bp=1499)), du.arrive_reached(A(bp=1485, lines=1, cnt=1)), du.arrive_reached(A(bp=-1, cnt=1)),
                   du.arrive_reached(A(ov=900), clock_ok=False), du.arrive_reached(A(ov=900, bp=1499), clock_ok=False)],
       "constants": [du.DWELL_MS, du.ARRIVE_MARGIN_MS, du.ARRIVE_SETTLE_TICKS, du.K_LEAD_MS, du.ARRIVE_THIN_MS],
       "rep": j(A(), CTL)[1]}
''')
    assert out.pop("constants") == [1500, 100, 64, 1040, 1450], out
    assert out.pop("reached") == [True, True, False, False, True, True, True, False], out
    rep = out.pop("rep")
    assert "the guard's green: arrive.last.field 30611 ok, last.end spared ok, ends.spared +>= 1 ok, levers.arrive null ok" in rep, rep
    assert "cross-check (reported only): ARRIVE's guarded peak 1220 vs ARRIVE-OLD's raw base peak 1200" in rep and "retune check" in rep, rep
    assert "lead 500 (in time)" in rep and "A 2200, dx 70, d7 100" in rep and "(control shift <= 100)" in rep, rep
    wrep = out.pop("watch_rep")
    assert "controls judged 1, dwell OUTs 0 (none)" in wrep, wrep
    assert "watches (reported apart, never judged): dressed 3, OUTs 2 (watch/CAL2, watch-desk/D1.0)" in wrep, wrep
    # [s164] the watches are reported, never folded: a dressed watch's dwell OUT leaves the gate's green standing
    for k in ("guard", "watch_undressed", "watch_dressed", "desk_line_out", "desk_dwell", "control_desk_line", "unfit_short_overlap"):
        assert out.pop(k) == "green", (k, out)
    assert out["overlap_short"][0] == "red" and out["overlap_short"][1].startswith("not reached: ARRIVE at act"), out
    out.pop("overlap_short")
    assert all(v == "red" for v in out.values()), out


def test_da_arrive_names_its_reds_and_the_green_is_attributable():
    """DA-ARRIVE's named reds on a REACHED gate, each read from the guest alone: the guard off at the landing (levers.arrive old -- the
    `arrive` word: a dwell OUT with armed false), "the guard never anchored" (lead_ms null), "guard defect" (the shift off
    min(K, max(0, K - (B - Hs))) by more than a frame + 16 ms, or no episode on an anchored landing), "margin miss" (a dwell OUT -- or
    any step-out -- with the guard anchored and its shift right: retune ARRIVE, not the guard). A late read (lead < 0) owes the cap
    (shift K). The green must be attributable (last.field 30611, last.end spared, spared +>= 1); a green guarded peak past 1450 ms is
    reported "margin thin"."""
    out = _duo_child(_DA_A + r'''
d = lambda **kw: j(A(**kw), CTL)
OUT = {"old": list(d(lever="old", armed=False, shift=None, bp=1485, lines=1, cnt=1, active=True)),
       "unanchored": list(d(lead=None, lead_ep=None, shift=None)), "defect": list(d(shift=300)), "no_episode": list(d(shift=None)),
       "margin": list(d(lines=1, cnt=1, active=True)), "margin_active": list(d(active=True)),
       "tol_in": d(shift=480 + 49)[0], "tol_out": d(shift=480 + 50)[0], "tol_low": d(shift=480 - 50)[0],
       "late": list(d(lead=-200, lead_ep=-200, late=True, shift=1040)), "late_wrong": d(lead=-200, lead_ep=-200, shift=840)[0],
       "lead_ep": d(lead=500, lead_ep=-200, shift=1040)[0],
       "end": d(last_end=None)[0], "field": d(last_field=30602)[0], "spared": d(spared=0)[0], "spared_none": d(spared=None)[0],
       "thin": list(d(bp=1700, dwell_peak=1460)), "rule": [du.arrive_shift_rule(60, 500), du.arrive_shift_rule(60, -200),
                                                            du.arrive_shift_rule(60, 1040), du.arrive_shift_rule(None, 500)]}
''')
    assert out["old"][0] == "red" and "the guard was off at this landing (levers.arrive 'old', armed False)" in out["old"][1], out["old"]
    assert out["unanchored"][0] == "red" and "the guard never anchored: no landed frame seen" in out["unanchored"][1], out
    assert out["defect"][0] == "red" and "guard defect: shift 300 ms, the rule gives 480 ms" in out["defect"][1], out
    assert out["no_episode"][0] == "red" and "guard defect: no episode ran on an anchored landing" in out["no_episode"][1], out
    for k in ("margin", "margin_active"):
        assert out[k][0] == "red" and "margin miss: the guard shifted 480 ms as its rule says" in out[k][1] and "not a guard defect" in out[k][1], out[k]
    assert out["tol_in"] == "green" and out["tol_out"] == "red" and out["tol_low"] == "red", out
    assert out["late"][0] == "green" and out["late_wrong"] == "red" and out["lead_ep"] == "green", out
    assert [out["end"], out["field"], out["spared"], out["spared_none"]] == ["red"] * 4, out
    assert out["thin"][0] == "green" and "margin thin: the guarded dwell peaked 1460 ms (> 1450)" in out["thin"][1], out["thin"]
    assert out["rule"] == [480, 1040, 0, None], out["rule"]


def test_da_guard_holds_the_anchor_across_ordinary_landings():
    """DA-GUARD ([s164], probabilistic, one game): each act intent landing in CAL2, CAL3, DESK and REST whose host transition sent a
    landed frame (the host's intent.landed_frames >= 1) must read a non-null arrive.lead_ms before the guest's control returns; any other
    landing is UNREACHED, never red; at least one reached landing (DA-LANE's floor) else red "not reached: no landing sent a landed
    frame" -- UNREACHED instead under `life` (its declared unreach). Landings out of scope (CAL0, CAL1, the ARRIVE runs) never count;
    host.seen_t - the host's landing is reported, VOID under an unfit clock."""
    out = _duo_child(r'''
import copy
rows, _m = duo_rows()
cal = [t for v in cal_trs().values() for t in v]
desk = [desk_run(k, D, old) for k, (D, old) in enumerate(du.desk_runs(None))]
lane = cal + [t for r in desk for t in (r["t359"], r["t351"], r["t352"])]
def edit(pred, hi=None, arr=None):
    out = []
    for t in lane:
        t = copy.deepcopy(t)
        if pred(t):
            t["hi"].update(hi or {})
            t["arrive"].update(arr or {})
        out.append(t)
    return out
j = lambda L, **kw: list(du.judge_da_guard(L, **kw))
OUT = {"plain": rows["DA-GUARD"][0], "fresh": j(lane)[0], "scope": [du.guard_scope(t) for t in cal if t["sub"] in ("CAL0", "ARRIVE", "CAL2")],
       "one_unanchored": j(edit(lambda t: t["lane"] == "REST" and t["sub"] == "D1.0", arr={"lead": None}))[0],
       "unreached_unanchored": j(edit(lambda t: t["lane"] == "REST", hi={"landed_frames": 0}, arr={"lead": None}))[0],
       "out_of_scope": j(edit(lambda t: t["sub"] in ("CAL0", "CAL1", "ARRIVE", "ARRIVE-OLD"), arr={"lead": None}))[0],
       "none": j(edit(lambda t: True, hi={"landed_frames": 0})), "none_life": j(edit(lambda t: True, hi={"landed_frames": 0}), life_word=True),
       "late_ok": j(edit(lambda t: t["lane"] == "REST", arr={"lead": -150, "late": True}))[0],
       "unfit": j(lane, clock_ok=False), "fit_detail": j(lane)[1]}
''')
    assert out["plain"] == "green" and out["fresh"] == "green" and out["late_ok"] == "green" and out["out_of_scope"] == "green", out
    assert out["scope"] == [False, False, True, True, False, False], out["scope"]          # CAL0 x2, CAL2 x2, ARRIVE x2
    assert out["one_unanchored"] == "red" and out["unreached_unanchored"] == "green", out
    assert out["none"][0] == "red" and out["none"][1].startswith("not reached: no landing sent a landed frame"), out["none"]
    assert out["none_life"][0] == "unreached" and "the `life` word's declared unreach" in out["none_life"][1], out["none_life"]
    assert out["unfit"][0] == "green" and "seen - host landing VOID" in out["unfit"][1] and "seen - host landing 70" in out["fit_detail"], out


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
    DC-B(b), DP-HALT, DP-DRESS. [s164] The first duo run's two DESK reds, re-registered: DF-FLASH's lawful HURRY (heading with more
    than FastFrames left, ended by black) is GREEN -- a wipe stays red whatever ends it (review round 2: by own, on the engine's
    window that opens on the rise, was green under the old `or by own` escape) and a hurry a 0.9 s cut ended (fallback, the realistic
    risk-18 verdict; recheck; timer, Due's fail-open) stays red; DP-DRESS wants the latest frame's section-8 pick (want 3 = expect 3,
    leader 2 is the green), each part red alone (a stale dress, the double), VOID when the pick is unread."""
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
                du.judge_da_lines(shifted, clock_ok=False)[0],
                du.judge_df_flash(fl(fades, action="hurry", by="black"))[0]],   # [s164] the first duo run's D 0.3 shape: lawful
       "unreached": [du.judge_df_flash(fl(fades, view_start="visible"))[0], du.judge_df_grace(fl(fades, action="hurry"))[0],
                     du.judge_df_pace(fl(pace, backlog_start="none"))[0], du.judge_dc_b_b(last(rold, own_t=-1))[0],
                     du.judge_dp_halt([{"g0": block(pin__pre_frames=3), "g": block(pin__pre_frames=3, pin__max_pre_diff=0)}])[0],
                     du.judge_df_grace(fl(fades, left_start=13, view_start="heading"))[0]],
       "void": [du.judge_dc_b_a(last(rest, seen_t=10 ** 9))[0], du.judge_dc_b_a([dict(r, l139=None) for r in rest])[0],
                du.judge_dp_dress([{"want": -1, "leader": 2}])[0], du.judge_dp_dress([{"want": 3, "expect": None, "leader": 2}])[0],
                du.judge_dp_dress([{"want": 3, "expect": 3, "leader": -1}])[0]],
       "life_ok": du.judge_da_probe(hi(probe, last_end="old", landed_frames=0), life_old=True)[0],
       "flash_claim": du.CLAIMS["DF-FLASH"], "flash_by": sorted({f["fade"]["by"] for f in fades if f["fade"]["view_start"] in ("heading", "black")}),
       "bad": {"lines_unstamped": du.judge_da_lines(unstamped)[0], "lines_tap_after_queue": du.judge_da_lines(shifted)[0],
               "lines_waited": du.judge_da_lines(waited)[0], "lines_shown": du.judge_da_lines(shown)[0],
               "lines_none": du.judge_da_lines([{"hl": [], "gl": []}])[0],
               "flash_dip": du.judge_df_flash([dict(f, cur=[200, 0, 248]) for f in fades])[0],
               "flash_wipe": du.judge_df_flash(fl(fades, action="wipe", path="old", by="timer"))[0],
               # [s164] review round 2: a wipe C's own pass ended, on the engine-shaped window (the act run's REST-OLD wipe)
               "flash_wipe_own": du.judge_df_flash([dict(f, cur=[0, 10, 10, 21]) for f in fl(fades, action="wipe", path="old", by="own")])[0],
               "flash_wipe_own_black": du.judge_df_flash([dict(f, cur=[0, 10, 10, 21]) for f in fl(fades, action="wipe", path="old", by="own",
                                                                                                   view_start="black")])[0],
               "flash_hurry_timer": du.judge_df_flash(fl(fades, action="hurry", by="timer"))[0],
               "flash_hurry_fallback": du.judge_df_flash(fl(fades, action="hurry", by="fallback"))[0],     # risk 18's real cut
               "flash_hurry_recheck": du.judge_df_flash(fl(fades, action="hurry", by="recheck"))[0],
               "flash_hurry_dip": du.judge_df_flash([dict(f, cur=[200, 0, 248]) for f in fl(fades, action="hurry", by="black")])[0],
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
               # [s164] fix round 3 review: one run's unread L139 never hides another run's red (the old early VOID did)
               "b_a_unread_hides": du.judge_dc_b_a([dict(rest[0], l139=None)] + [dict(r, maps=2) for r in rest[1:]])[0],
               "b_b_bounce": du.judge_dc_b_b(last(rold, own_verdict="bounce", own_why="not-host"))[0],
               "b_b_conv": du.judge_dc_b_b([dict(r, g=dict(r["g"], own=dict(r["g"]["own"], converted=0))) for r in rold])[0],
               "b_b_loads": du.judge_dc_b_b([dict(r, maps=2) for r in rold])[0],
               "halt": du.judge_dp_halt([{"g0": block(pin__pre_frames=3), "g": block(pin__pre_frames=4, pin__max_pre_diff=2)}])[0],
               "dress_double": du.judge_dp_dress([{"want": 2, "expect": 3, "leader": 2}])[0],
               "dress_stale": du.judge_dp_dress([{"want": 0, "expect": 3, "leader": 2}])[0],
               "dress_pick_is_leader": du.judge_dp_dress([{"want": 2, "expect": 2, "leader": 2}])[0],
               "dress_one_of_six": du.judge_dp_dress([r["dress"] for r in desk[:5]] + [{"want": 1, "expect": 3, "leader": 2}])[0]}}
''')
    assert out["good"] == ["green"] * 11, out["good"]
    assert out["unreached"] == ["unreached"] * 6, out["unreached"]
    assert out["void"] == ["void"] * 5, out["void"]
    assert out["life_ok"] == "green", out
    assert all(v == "red" for v in out["bad"].values()), out["bad"]
    assert out["flash_by"] == ["own"], out["flash_by"]          # the plain green is a JOIN C's own pass ended: still green
    claim = out["flash_claim"]                                  # [s164] review round 2: no by-own escape; the 0.9 s cuts named
    assert "or ended by own" not in claim and "a wipe is red whatever ends it" in claim, claim
    assert all(w in claim for w in ("fallback", "recheck", "timer")), claim


def test_desk_fade_rows_reach_only_a_follow_whose_copy_could_still_exit():
    """[s164] Fix round 3 (the guarded duo's DF-GRACE reds: act D 2.5 by recheck, `arrive` D 1.0 by timer twice and D 2.5 by recheck --
    every one a follow that started on 359 AFTER a bounce reload, Joining the reloaded field's idle load-black, which own can never
    end). DF-GRACE and DF-FLASH reach only a follow whose copy could still exit (desk_follow_reach): the record followed, fade.last names
    351, and its own jump was not spent before the follow (last.own_t unset or >= last.follow_t) -- the TEMPORAL test only. A post-bounce
    black Join by recheck is UNREACHED for both rows, listed apart in the s158-shape words; a genuine black Join by recheck or timer (no
    own jump, or one at or after the follow) is RED; a Join whose own jump bounced AFTER follow_t, with a second follow, is RED (no
    own_verdict / bounces clause: refuter 2's case); own at the follow's own ms by own is green; a record with no follow is never judged
    and a follow whose fade.last names another field is VOID. DC-B(a) shares the one definition (own_spent_before, at last.seen_t: its
    reach is unchanged). The guarded runs' six DESK follows each, rebuilt from the guest Memoria.log close lines: act reaches 4 of 6
    and `arrive` 1 of 6, every reached one by own -- both rows green, the post-bounce follows listed apart. [s164] Fix round 3 review:
    the stale VOID yields to a judged red -- a genuine DF-GRACE red (a black Join by recheck) or DF-FLASH red (a wipe) next to a stale
    run stays RED with the stale run named in its detail; a green run next to a stale one is still VOID."""
    out = _duo_child(r'''
def F(D=2.5, old=False, view="black", path="fast", action="join", by="recheck", left=0, field=351, follow=1558, own=1000, follows=1,
      bounces=1, verdict="bounce", reload=1188, seen=None, cur=None):
    """One DESK fade dict in desk_evidence's shape: the guest's fade.last and the 351 record's own edges (-1 = never)."""
    return {"D": D, "old": old, "cur": list(cur or []),
            "fade": {"field": field, "view_start": view, "path": path, "action": action, "by": by, "left_start": left},
            "last": {"id": 30, "seen_t": follow if seen is None else seen, "follow_t": follow, "follows": follows, "own_t": own,
                     "own_verdict": verdict, "bounces": bounces, "reload_t": reload}}
post = F()                                           # the guarded act D 2.5: own Field(351) bounced 558 ms before the follow
genuine = F(own=-1, verdict=None, bounces=0, reload=-1)               # a black Join with no own jump: the copy could still exit
late_bounce = F(follow=1000, own=1050, follows=2, verdict="bounce", reload=1400, by="timer")    # refused own pass bounced AFTER follow_t
T = 10000
def run(rows):
    return [F(D=D, old=old, view=view, path=path, action=action, left=left, by=by, follow=follow, own=own, bounces=b,
              verdict="bounce" if b else ("pass" if own >= 0 else None), reload=own + 325 if b else -1)
            for D, old, view, path, action, left, by, follow, own, b in rows]
# the guarded duo's DESK follows (guest Memoria.log close lines: seen / follow / own after the first edge, bounces)
ACT = run([(0.3, False, "black", "fast", "join", 0, "own", T, T, 0), (0.3, True, "heading", "fast", "join", 6, "own", T, T + 250, 0),
           (1.0, False, "visible", "backlog", "fade", -1, "timer", T + 1167, T, 1),
           (1.0, True, "black", "fast", "join", 0, "own", T, T + 32, 0),
           (2.5, False, "black", "fast", "join", 0, "recheck", T + 558, T, 1),
           (2.5, True, "heading", "fast", "join", 9, "own", T, T + 351, 0)])
ARRIVE = run([(0.3, False, "visible", "fast", "fade", -1, "black", T, -1, 0), (0.3, True, "visible", "fast", "fade", -1, "black", T, -1, 0),
              (1.0, False, "black", "backlog", "join", 0, "timer", T + 659, T, 1),
              (1.0, True, "black", "backlog", "join", 0, "timer", T + 557, T, 1),
              (2.5, False, "black", "fast", "join", 0, "recheck", T + 542, T, 1),
              (2.5, True, "heading", "fast", "join", 9, "own", T, T + 351, 0)])
cases = [(-1, -1), (5, -1), (5, 5), (5, 6), (6, 5)]
OUT = {"post": [list(du.judge_df_grace([post])), list(du.judge_df_flash([post]))],
       "red": {"genuine_recheck": du.judge_df_grace([genuine])[0], "genuine_timer": du.judge_df_grace([F(own=-1, verdict=None, bounces=0,
               reload=-1, path="backlog", by="timer")])[0],
               "own_after_follow_timer": du.judge_df_grace([F(follow=1000, own=1100, verdict="pass", bounces=0, reload=-1, by="timer")])[0],
               "late_bounce": du.judge_df_grace([late_bounce])[0],
               "one_of_three": du.judge_df_grace([post, F(follow=1000, own=1000, by="own", verdict="pass", bounces=0, reload=-1), genuine])[0]},
       "late_bounce_why": du.judge_df_grace([late_bounce])[1],
       "at_follow_own": du.judge_df_grace([F(follow=1000, own=1000, by="own", verdict="pass", bounces=0, reload=-1)])[0],
       "nofollow": list(du.judge_df_grace([F(follow=-1, field=359, by="own")])),
       "stale": [list(du.judge_df_grace([F(follow=1000, own=-1, field=359, by="own")])),
                 du.judge_df_flash([F(follow=1000, own=-1, field=359, by="own"), genuine])[0]],
       "reach": [du.desk_follow_reach(f)[0] for f in (post, genuine, late_bounce, F(follow=-1), F(follow=1000, own=-1, field=359))],
       "shared": [[du.dcb_a_reached(block(last__own_t=o, last__seen_t=s)) for o, s in cases],
                  [o < 0 or (s >= 0 and s <= o) for o, s in cases],
                  [du.own_spent_before(block(last__own_t=o, last__follow_t=s), "last.follow_t") for o, s in cases]],
       "act": [list(du.judge_df_grace(ACT)), list(du.judge_df_flash(ACT))],
       "arrive": [list(du.judge_df_grace(ARRIVE)), list(du.judge_df_flash(ARRIVE))],
       # [s164] fix round 3 review: a judged red beside a stale run stands; a green beside one is VOID
       "stale_red": [list(du.judge_df_grace([genuine, F(follow=1000, own=-1, field=359, by="own")])),
                     list(du.judge_df_flash([F(own=-1, verdict=None, bounces=0, reload=-1, action="wipe", by="timer"),
                                             F(follow=1000, own=-1, field=359, by="own")]))],
       "stale_green": du.judge_df_grace([F(follow=1000, own=1000, by="own", verdict="pass", bounces=0, reload=-1),
                                         F(follow=1000, own=-1, field=359, by="own")])[0],
       "claims": [du.CLAIMS["DF-GRACE"], du.CLAIMS["DF-FLASH"]]}
''')
    apart = "post-bounce join on the reload's load-black (s158 shape, risk 8): by recheck"
    for st, why in out["post"]:
        assert st == "unreached" and f"listed apart, never judged: D 2.5: {apart}" in why, (st, why)
    assert all(v == "red" for v in out["red"].values()), out["red"]
    assert out["late_bounce_why"] == "1 of 1 reached; D 2.5: black left 0, by timer", out["late_bounce_why"]
    assert out["at_follow_own"] == "green", out
    assert out["nofollow"][0] == "unreached" and "D 2.5: no follow on this record (fade.last names field 359" in out["nofollow"][1], out
    assert out["stale"][0][0] == "void" and "fade.last names field 359, not 351" in out["stale"][0][1] and out["stale"][1] == "void", out
    assert out["reach"] == ["s158", "judge", "judge", "nofollow", "stale"], out["reach"]
    dcb, old_formula, spent = out["shared"]
    assert dcb == old_formula == [True, False, True, False, True] and spent == [False, True, False, True, False], out["shared"]
    (ga, gad), (fa, fad) = out["act"]
    assert ga == fa == "green" and gad.startswith("4 of 6 reached;") and fad.startswith("4 of 6 reached;"), out["act"]
    assert f"D 2.5: {apart}" in gad and "D 1.0: post-bounce fade from a visible reload (s158 shape, risk 8): by timer" in gad, gad
    assert "D 0.3 REST-OLD: heading left 6, by own" in gad and "D 1.0 REST-OLD: black left 0, by own" in gad, gad
    (ga, gad), (fa, fad) = out["arrive"]
    assert ga == fa == "green" and gad.startswith("1 of 6 reached; D 2.5 REST-OLD: heading left 9, by own;"), out["arrive"]
    assert fad.startswith("1 of 6 reached; D 2.5 REST-OLD: heading/fast/join by own, dip False;"), fad
    assert "D 1.0: post-bounce join on the reload's load-black (s158 shape, risk 8): by timer" in gad, gad
    assert "D 1.0 REST-OLD: post-bounce join on the reload's load-black (s158 shape, risk 8): by timer" in gad and f"D 2.5: {apart}" in gad, gad
    for st, why in out["stale_red"]:
        assert st == "red" and why.startswith("1 of 2 reached; D 2.5: "), (st, why)
        assert "; fade.last is not this record's follow on 1 run(s): D 2.5: the record followed but fade.last names field 359" in why, why
    assert out["stale_green"] == "void", out["stale_green"]
    grace, flash = out["claims"]
    assert "last.own_t unset or >= last.follow_t" in grace and "fade.last names 351" in grace and "s158 shape" in grace, grace
    assert "DF-GRACE's follow whose copy could still exit" in flash, flash


def test_cat_judges_read_the_orphan_steppers_hold():
    """DB-SHAPE / DB-BIT / DB-HOLD / DB-ORDER on the guest's 113 out of KIT-1's orphan stepper (the host's control off on 351 with no
    scene until its 113 rises 5.2 s later): green under act (one hold line, its end at the host's claim, no orphaned line, every close
    by the host's seq), red under s163's rule (the line orphans and auto-closes: DB-HOLD and DB-ORDER). Text 118 first is the else path
    (VOID); each other part alone is red. [s164] The anchor is the b0 RISE on 351 (cat_t0): the first duo run's shape -- the guest's
    first 351 samples carrying the host's sticky 350 scene (host_flags 9, no 113 listed yet) -- stays green with tb0 pinned at the real
    rise (5200; the first-b0 anchor read the tail, -2598 ms); a rise armed only by a clear AFTER 113 (an early real rise that fell and
    rose again) is red, and a rise before 113 is DB-BIT's named red "rise precedes 113"."""
    out = _duo_child(r'''
act, old = cat_ev(), cat_ev("orphan")
ev = cat_ev()
j = lambda e: [du.judge_db_shape(e)[0], du.judge_db_bit(e)[0], du.judge_db_hold(e)[0], du.judge_db_order(e)[0]]
# the clock moved on by 1 s (113 at 1000, the rise at 6200) so the guest can stand on 351 BEFORE its 113 opens (the swap clock is >= 0)
sh = lambda xs: [ed(x, sw={"clock.now_ms": so.now_ms(x) + 1000}) for x in xs]
ev1 = dict(ev, gs=sh(ev["gs"]), hs=sh(ev["hs"]))
on351 = lambda t, hf: ed(Sx(t, 351, ctl=False), sw={"own.host_lane": 351}, ns={"host_flags": hf})
# the field-350 scene's sticky tail: guest samples already on 351 before its 113 opens, b0|b3 set, no window listed (never a 113 copy)
tail = [on351(t, 9) for t in range(400, 1000, 100)]
stale = dict(ev1, gs=tail + ev1["gs"])
# an early REAL rise: b0 set from before 113 (the tail shape, then 113 opens under it), falls at 3000 (after 113), rises again at 6200
refall = dict(ev1, gs=tail + [ed(x, ns={"host_flags": 9}) if so.now_ms(x) < 3000 else x for x in ev1["gs"]])
# a rise BEFORE 113: an arming clear at 600 and a b0 sample at 800, then 113 at 1000
pre113 = dict(ev1, gs=[on351(600, 8), on351(800, 9)] + ev1["gs"])
early = dict(ev, gs=[x if so.now_ms(x) < 1000 else ed(x, ns={"host_flags": 9}) for x in ev["gs"]])
bit_lane = dict(ev, gs=[ed(x, sw={"own.host_lane": 0}) for x in ev["gs"]])
bit_host = dict(ev, hs=ev["hs"] + [Sx(1000, 351, ctl=True)])
bit_ctl = dict(ev, gs=[ed(x, ns={"host_flags": 10}) if so.now_ms(x) < 5200 else x for x in ev["gs"]])
two_holds = dict(ev, gl=ev["gl"] + [L(du.so.hold_words(du.CAT_FIRST))])
order_seq = dict(ev, gl=[ln.replace("(host seq 42)", "(host seq 49)") for ln in ev["gl"]])
order_drop = dict(ev, gl=ev["gl"] + [L("[NetSync] dialogue: host seq 45 (win 7 text 117) dropped -- it is for field 351")])
OUT = {"act": j(act), "old": j(old), "else": j(cat_ev(else_path=True)), "unstamped": j(cat_ev(on=False)),
       "end_why": du.so.end_lines(act["gl"], du.CAT_FIRST),
       "rise": next(so.now_ms(x) for x in ev1["gs"] if so.nget(x, "host_flags") & 1),     # the stepper's scene-rise sample
       "stale": j(stale), "t0": [list(du.cat_t0(ev1["gs"])), list(du.cat_t0(stale["gs"])), list(du.cat_t0(refall["gs"]))],
       "pre113_bit": list(du.judge_db_bit(pre113)), "shape_detail": du.judge_db_shape(stale)[1],
       "bad": {"shape_early": du.judge_db_shape(early)[0], "shape_no_pass": du.judge_db_shape(dict(ev, gl=ev["gl"][1:]))[0],
               "shape_refall": du.judge_db_shape(refall)[0], "bit_refall": du.judge_db_bit(refall)[0],
               "shape_pre113": du.judge_db_shape(pre113)[0], "bit_pre113": du.judge_db_bit(pre113)[0],
               "bit_lane": du.judge_db_bit(bit_lane)[0], "bit_host": du.judge_db_bit(bit_host)[0], "bit_ctl": du.judge_db_bit(bit_ctl)[0],
               "hold_two": du.judge_db_hold(two_holds)[0], "hold_closes": du.judge_db_hold(dict(ev, closes1=1))[0],
               "order_seq": du.judge_db_order(order_seq)[0], "order_drop": du.judge_db_order(order_drop)[0]}}
''')
    assert out["act"] == ["green"] * 4 and out["unstamped"] == ["green"] * 4, out
    assert out["stale"] == ["green"] * 4, out["stale"]                     # the first duo run's shape: the tail never anchors
    rise = out["rise"]
    assert 6200 <= rise < 6200 + 33, rise                                  # the stepper's 5.2 s scene event, a tick late at most
    assert out["t0"] == [[1000, rise, False], [1000, rise, False], [1000, None, False]], out["t0"]
    assert f"113 at 1000, b0 rise at {rise} ({rise - 1000} ms)" in out["shape_detail"], out["shape_detail"]
    assert out["pre113_bit"][0] == "red" and out["pre113_bit"][1].startswith("rise precedes 113: the host's b0 rise at 800"), out
    assert out["old"] == ["green", "green", "red", "red"], out["old"]
    assert out["else"] == ["void"] * 4, out["else"]
    assert len(out["end_why"]) == 1 and out["end_why"][0][1] in ("a host event claims it", "the host is busy (a scene or a line)"), out
    assert all(v == "red" for v in out["bad"].values()), out["bad"]


def test_the_other_duo_judges_can_go_red_on_each_part():
    """DC-OWN, DL-DEFER, DP-DEFER (a late capture UNREACHED; VOID under `life`; reach needs the host's mark in the latest frame), DP-AGED,
    DP-MARK (VOID unless the mark leads the landing by 300 ms; a late capture UNREACHED), DL-LEFT, DF-OPEN (a refused warp VOID: DF-PACE
    stands in), DP-PARTY (REACHED only on a party change), LVD-ROLE, LVD-LIFE. [s164] DL-LEFT's reach gate (the first duo run): VOID
    when the host's pre-send sample was not intent n live (that run's shape: ended "stands" before the send -- red on the old
    judge), RED when intent n is still active once the battle is up (the swirl never ended section 4: never VOID). Review round 2,
    THE RACE: a "stands" end after the pre-send read and no later than the swirl is VOID (P8) -- after the swirl, another end, or an
    unread swirl_t stays red. Judged past both VOIDs and the red: the host's 'ended ... I left it' line for n, intent.last_end left,
    the guest's seen.nonce n, and its seen.last_t no later than 300 ms past the battle start (the host's first sample off FieldMap;
    intent.end_t on a Left end when that sample is unread)."""
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
PT = lf["pre"]["now_ms"]                                 # the host's pre-send read (intent 7 live; P is the log prefix)
def race(end_t=PT + 200, last_end="stands", nonce=7):
    return block(intent__nonce=nonce, intent__active=False, intent__last_end=last_end, intent__end_t=end_t)
own = {"g": block(last__own_verdict="ate", last__own_why="ate"), "gl": [L("Map: 450 (Dali/Field)")]}
party = [{"sub": "x", "dest": 1, "party_emit": [0, 1, 2, 3], "party_land": [0, 4, 2, 3], "mirror_after": [0, 4, 2, 3]}]
OUT = {"good": [du.judge_dc_own(own)[0], du.judge_dl_defer(m)[0], du.judge_dp_defer(m)[0], du.judge_dp_aged(a)[0], du.judge_dp_mark(k)[0],
                du.judge_dl_left(lf)[0], du.judge_df_open(op)[0], du.judge_dp_party(party)[0], du.judge_lvd_role(LVD)[0],
                du.judge_lvd_life(True, {"life": "old"}, {"life": "act"})[0]],
       "unreached": [du.judge_dp_defer(g(m, pin__last_use_quality="late"))[0], du.judge_dp_defer(g(m, pin__last_diff=0))[0],
                     du.judge_dp_defer(g(m, last__follow_via="serial"))[0], du.judge_dp_mark(g(k, pin__last_use_quality="late"))[0],
                     du.judge_dp_party([dict(party[0], party_land=[0, 1, 2, 3])])[0]],
       "void": [du.judge_dp_defer(m, life_word=True)[0], du.judge_dp_mark(dict(k, host_flag_t=k["g"]["last"]["land_t"] - 299))[0],
                du.judge_df_open(dict(op, refused="the game refused a step: warp"))[0],
                # [s164] the first duo run's LEFT: intent 7 had ended "stands" before the send -- a setup miss, never red
                du.judge_dl_left(dict(lf, pre=dict(lf["pre"], active=False),
                                      h=block(intent__nonce=7, intent__active=False, intent__last_end="stands", intent__end_t=lf["swirl_t"] - 1700)))[0],
                du.judge_dl_left(dict(lf, pre=dict(lf["pre"], nonce=6)))[0], du.judge_dl_left(dict(lf, n=None))[0]],
       "left_void_why": du.judge_dl_left(dict(lf, pre=dict(lf["pre"], active=False),
                                              h=block(intent__nonce=7, intent__last_end="stands", intent__end_t=lf["pre"]["now_ms"] - 800)))[1],
       "left_active": list(du.judge_dl_left(dict(lf, h=block(intent__nonce=7, intent__active=True, intent__last_end="stands", intent__end_t=-1)))),
       "left_detail": du.judge_dl_left(lf)[1],
       "left_end_t_fallback": du.judge_dl_left(dict(lf, swirl_t=None))[0],
       # [s164] review round 2, THE RACE: intent 7 ended "stands" 200 ms after the pre-send read and 100 ms before the swirl
       "left_race": list(du.judge_dl_left(dict(lf, h=race(), swirl_t=PT + 300, hl=[]))),
       "bad": {"own_two_maps": du.judge_dc_own(dict(own, gl=own["gl"] * 2))[0], "own_unrecorded": du.judge_dc_own(dict(own, g=block()))[0],
               "defer_late": du.judge_dl_defer(g(m, last__follow_t=MC + 260))[0],
               "defer_serial": du.judge_dl_defer(g(m, last__follow_via="serial"))[0],
               "defer_flag": du.judge_dp_defer(dict(m, flag=True))[0], "aged_flag": du.judge_dp_aged(dict(a, flag=False))[0],
               "aged_why": du.judge_dp_aged(g(a, pin__last_use="pin"))[0], "mark_flag": du.judge_dp_mark(dict(k, flag=True))[0],
               "mark_line": du.judge_dp_mark(dict(k, gl=[]))[0], "mark_diff": du.judge_dp_mark(g(k, pin__last_diff=0))[0],
               "left_line": du.judge_dl_left(dict(lf, hl=[]))[0], "left_late": du.judge_dl_left(dict(lf, swirl_t=lf["swirl_t"] - 400))[0],
               "left_late_end_t": du.judge_dl_left(dict(lf, swirl_t=None, h=block(intent__nonce=7, intent__last_end="left",
                                                                                  intent__end_t=lf["swirl_t"] - 400)))[0],
               "left_end": du.judge_dl_left(dict(lf, h=block(intent__nonce=7, intent__last_end="stands")))[0],
               # [s164] the race VOID is narrow: a "stands" AFTER the swirl (off the field), any other end at the race's time, a
               # "stands" before the pre-send read, an unread swirl_t, or the race on another nonce stay red
               "left_stands_after_swirl": du.judge_dl_left(dict(lf, h=race(end_t=PT + 350), swirl_t=PT + 300, hl=[]))[0],
               "left_elsewhere_in_race": du.judge_dl_left(dict(lf, h=race(last_end="elsewhere"), swirl_t=PT + 300, hl=[]))[0],
               "left_stands_at_pre": du.judge_dl_left(dict(lf, h=race(end_t=PT), swirl_t=PT + 300, hl=[]))[0],
               "left_race_no_swirl": du.judge_dl_left(dict(lf, h=race(), swirl_t=None, hl=[]))[0],
               "left_race_other_nonce": du.judge_dl_left(dict(lf, h=race(nonce=6), swirl_t=PT + 300, hl=[]))[0],
               "left_nonce": du.judge_dl_left(dict(lf, g=block(seen__nonce=8, seen__last_t=lf["swirl_t"])))[0],
               "left_line_away": du.judge_dl_left(dict(lf, hl=[L(BW.life_log_ended(True, 7, du.AWAY, 1100, BW.INTENT_END_LEFT, 1))]))[0],
               "open_path": du.judge_df_open(dict(op, fade=dict(op["fade"], path="fast")))[0],
               "open_short": du.judge_df_open(dict(op, fade=dict(op["fade"], ms=600)))[0],
               "open_bk": du.judge_df_open(dict(op, fade=dict(op["fade"], backlog_start="line")))[0],
               "party": du.judge_dp_party([dict(party[0], mirror_after=[0, 1, 2, 3])])[0],
               "role": du.judge_lvd_role(dict(LVD, host_orphan=""))[0], "life_unacked": du.judge_lvd_life(False, {"life": "old"}, {"life": None})[0],
               "role_arrive_acked": du.judge_lvd_role(dict(LVD, host_arrive=""))[0],
               "role_arrive_usage": du.judge_lvd_role(dict(LVD, host_arrive=BW.SWAP_USAGE))[0],
               "role_arrivebench_acked": du.judge_lvd_role(dict(LVD, guest_arrivebench=""))[0],
               "role_arrivebench_guest_side": du.judge_lvd_role(dict(LVD, guest_arrivebench=BW.swap_refusal_guest_side("arrivebench")))[0],
               "life_held": du.judge_lvd_life(True, {"life": "old"}, {"life": "old"})[0]}}
''')
    assert out["good"] == ["green"] * 10, out["good"]
    assert out["unreached"] == ["unreached"] * 5, out["unreached"]
    assert out["void"] == ["void"] * 6, out["void"]
    assert out["left_void_why"].startswith("setup miss (P8): the host's pre-send (active False, nonce 7, t 9799600) is not intent 7 live"), out
    assert "section 4 ended 'stands' at 9798800, 800 ms before the send" in out["left_void_why"], out["left_void_why"]
    assert out["left_active"][0] == "red" and out["left_active"][1].startswith("the swirl never ended section 4: intent 7 still active"), out
    assert "battle start 9800030 (off FieldMap)" in out["left_detail"] and "last_end 'left' at 9800000" in out["left_detail"], out
    assert out["left_end_t_fallback"] == "green", out
    assert out["left_race"][0] == "void", out["left_race"]
    assert out["left_race"][1].startswith("race (P8): section 4 ended 'stands' at 9799800, 200 ms after the host's pre-send"), out
    assert "100 ms before the battle start (off FieldMap)" in out["left_race"][1], out["left_race"]
    assert all(v == "red" for v in out["bad"].values()), out["bad"]


def test_dl_defer_brackets_the_pause_close_off_the_guests_ring():
    """[s164] Fix round 3 (the guarded duo's DL-DEFER reds, -131 / -132 ms): the MENU hook's awaited cancel starved the watch for its
    accept-to-ack span, so the watch's "first sample off Pause" came at the ack. DL-DEFER now brackets the close off the guest's ring
    (ring_since from the frame before the Pause press): the last Pause sample and the first off it. Re-judged on the two guarded runs'
    saved rings (record 45 seen while paused; act 255529460 / 255529488 with the follow at 255529472, `arrive` 256473056 / 256473089
    with 256473090): green, follow - close -16 / +1 ms, brackets 28 / 33 ms (2 frames each). Green on the follow by the intent, no
    Pause sample of THIS record (rec_block's last.id) with follow_t >= 0 -- the record before reads Pause with its own follow_t and is
    never read -- follow_t >= the last Pause sample, and follow_t - the last Pause sample <= 200 ms (the lag's upper bound): each part
    red alone. VOID on a ring with no Pause sample (both rows) or, by the intent, a bracket with no close or wider than 3 frames + 1 ms
    -- the awaited press's hole reads VOID, never a false red; by the serial follow a wide bracket is red. The hook's cancel goes out
    without waiting (its 0.6 s re-press guard kept), the ring is read after the watch's until and before its hold, and the false "the
    watch keeps sampling" comment is gone. [s164] Fix round 3 review: (F1) a guest that never lands on AWAY (_menu_run's `landed`) is
    RED -- its Pause samples aged out of the ring, or the Pause closed and no follow came -- and VOID when its ring ends on Pause or is
    empty (DP-DEFER VOID too); (P8) a record not seen while paused (seen after the last Pause sample, or unset) is RED "not reached" for
    DL-DEFER, which leaves PROBABILISTIC, and stays UNREACHED for DP-DEFER; (F2) the width VOIDs only a verdict the close's place
    decides -- a paused follow, an unset follow, one before the last Pause sample or more than 200 ms past the first sample off it are
    red on any bracket, a follow past the close within 200 ms of the last Pause sample green, and a follow inside the bracket or a lag
    the width leaves open VOID; (F3) the cap's frame is DA-CAL's measured one (cal_frame: never the 1/30 s fallback), else the ring's
    own median step -- an 80 ms bracket is VOID on the ring's 17 ms and judged on CAL's 33.3 -- and a follow INSIDE the bracket is
    placed by the ring's frame counter (at most 2 frames apart: a 3-frame bracket is VOID even under the cap, a 2-frame bracket whose
    close frame ran long is green), by ms within the close sample's own frame only when a frame counter is unread."""
    out = _duo_child(r'''
import copy
import inspect
m = menu_ev()
ring = m["ring"]
def ev(rg, **kw):
    e = dict(m, ring=rg, g=copy.deepcopy(m["g"]))
    e["g"]["last"].update(kw)
    return e
def dead(rg):                                            # [s164] fix round 3 review: the watch timed out with the guest off AWAY
    return dict(ev(rg), g={}, landed=False)
# the guarded duo's two MENU runs, off their saved guest rings (guest/states-FAILED-2.jsonl): record 45 seen while paused, the last
# Pause sample, the first sample off it, the follow (act: in the unsampled frame between them; `arrive`: 1 ms after the close)
ACT = {"seen": 255528237, "last_on": 255529460, "close": 255529488, "follow": 255529472}
ARR = {"seen": 256471839, "last_on": 256473056, "close": 256473089, "follow": 256473090}
act = ev(menu_ring(**ACT), seen_t=ACT["seen"], follow_t=ACT["follow"])
arr = ev(menu_ring(**ARR), seen_t=ARR["seen"], follow_t=ARR["follow"])
def starve(rg, follow=MC + 60):                          # an awaited press's ~134 ms hole after the last Pause: 8 frames of 17 ms
    return ([x for x in rg if not (MC - 10 < so.now_ms(x) < MC + 121)]
            + [du.slim(Sx(MC + 126, du.HOME, frame=MENU_F0 + 8,
                          sw={"last.id": MENU_RID, "last.seen_t": MENU_SEEN, "last.follow_t": follow}))])
starved = starve(ring)
three = menu_ring(close=MC + 41)                         # the review's 3-frame bracket: 51 ms, under the ring's 52 ms cap
long_close = menu_ring(close=MC + 30, close_frames=2)    # a 2-frame bracket whose close frame ran 23 ms
wide80 = menu_ring(close=MC + 70, follow=MC + 195)       # an 80 ms bracket: inside the old 1/30 s cap (101), past the ring's (52)
def unframed(rg):
    return [dict(x, frame=None) for x in rg]
FakeG = type("FakeG", (), {"states_since": lambda self, f: [Sx(100, du.HOME, ui="Pause"), Sx(117, du.HOME)]})
mr = inspect.getsource(du._menu_run)
lm = inspect.getsource(du._leg_menu)
hook = mr.split("def step(", 1)[1].split("w.hooks.append(step)", 1)[0]
b = du.pause_bracket(ring, MENU_RID)
ba = du.pause_bracket(act["ring"], MENU_RID)
OUT = {"good": [du.judge_dl_defer(m)[0], du.judge_dl_defer(act, 17.0)[0], du.judge_dl_defer(arr, 17.0)[0], du.judge_dp_defer(m)[0],
                du.judge_dp_defer(act)[0], du.judge_dp_defer(arr)[0]],
       "act": du.judge_dl_defer(act, 17.0)[1], "arr": du.judge_dl_defer(arr, 17.0)[1],
       "bracket": [b["last_on_t"] - MC, b["close_t"] - MC, b["width"], b["paused_follow"], b["paused"] > b["mine"] > 0],
       "frames": [b["on_frame"], b["close_frame"] - b["on_frame"], ba["close_frame"] - ba["on_frame"], du.pause_bracket([], 45)["on_frame"],
                  du.pause_bracket([x for x in ring if x["ui_state"] == "Pause"], 45)["close_frame"]],
       "keyed": [du.pause_bracket(ring, MENU_RID - 1)["paused_follow"], du.pause_bracket(ring, MENU_RID)["paused_follow"]],
       # placed past the close within 200 ms of the last Pause sample: green on any bracket (the starved one included)
       "edge": [du.judge_dl_defer(ev(ring, follow_t=MC + 190))[0], du.judge_dl_defer(ev(ring, follow_t=MC - 10))[0],
                du.judge_dl_defer(ev(starved, follow_t=MC + 130))[0]],
       "placed": [du.judge_dl_defer(ev(long_close, follow_t=MC + 10))[0], du.judge_dl_defer(ev(unframed(long_close), follow_t=MC + 15))[0],
                  du.judge_dl_defer(dict(m, landed=True))[0]],
       "bad": {"paused_follow": du.judge_dl_defer(ev(menu_ring(follow=MC - 100, paused_follow=True), follow_t=MC - 100))[0],
               "paused_follow_alone": du.judge_dl_defer(ev(menu_ring(follow=MC - 100, paused_follow=True), follow_t=MC + 60))[0],
               "before_last_on": du.judge_dl_defer(ev(ring, follow_t=MC - 50))[0],
               "late": du.judge_dl_defer(ev(ring, follow_t=MC + 191))[0],
               "serial": du.judge_dl_defer(ev(ring, follow_via="serial"))[0],
               "wide_serial": du.judge_dl_defer(ev(starved, follow_via="serial"))[0],
               "dp_flag": du.judge_dp_defer(dict(m, flag=True))[0],
               # [s164] fix round 3 review (F2): the reds the ring decides, on the starved bracket
               "wide_paused_follow": du.judge_dl_defer(ev(starve(menu_ring(follow=MC - 100, paused_follow=True), MC - 100),
                                                          follow_t=MC - 100))[0],
               "wide_before_last_on": du.judge_dl_defer(ev(starved, follow_t=MC - 50))[0],
               "wide_past_close": du.judge_dl_defer(ev(starved, follow_t=MC + 126 + 201))[0],
               "wide_unset": du.judge_dl_defer(ev(starved, follow_t=-1))[0],
               # (P8) the old judge's verdict pinned; (F3) the 80 ms bracket judged on CAL's 33.3 ms frame; (F1) never landed
               "unseen_serial": du.judge_dl_defer(ev(ring, seen_t=-1, follow_via="serial"))[0],
               "cap_judged": du.judge_dl_defer(ev(wide80, follow_t=MC + 195), 33.3)[0],
               "landed_aged_out": du.judge_dl_defer(dead([x for x in ring if x["ui_state"] != "Pause"]))[0],
               "landed_closed": du.judge_dl_defer(dead(ring))[0]},
       "unseen": [du.judge_dl_defer(ev(ring, seen_t=MC - 9))[0], du.judge_dl_defer(ev(ring, seen_t=-1))[0]],
       "unreached": [du.judge_dp_defer(ev(ring, seen_t=MC - 9))[0], du.judge_dp_defer(ev(ring, seen_t=-1))[0]],
       "unreached_why": [du.judge_dl_defer(ev(ring, seen_t=MC - 9))[1], du.judge_dp_defer(ev(ring, seen_t=MC - 9))[1]],
       "void": [du.judge_dl_defer(ev([]))[0], du.judge_dl_defer(ev([x for x in ring if x["ui_state"] == "Pause"]))[0],
                du.judge_dl_defer(ev(starved))[0], du.judge_dl_defer(ev(starved), 17.0)[0], du.judge_dp_defer(ev([]))[0],
                du.judge_dp_defer(m, life_word=True)[0]],
       "wide_void": [du.judge_dl_defer(ev(starved, follow_t=MC + 100))[0], du.judge_dl_defer(ev(starved, follow_t=MC + 126 + 150))[0],
                     du.judge_dl_defer(ev(three, follow_t=MC - 5))[0], du.judge_dl_defer(ev(wide80, follow_t=MC + 195))[0],
                     du.judge_dl_defer(ev(wide80, follow_t=MC + 195), 17.0)[0],
                     du.judge_dl_defer(ev(unframed(long_close), follow_t=MC + 10))[0]],
       "landed_void": [du.judge_dl_defer(dead([x for x in ring if x["ui_state"] == "Pause"]))[0], du.judge_dl_defer(dead([]))[0],
                       du.judge_dp_defer(dead(ring))[0]],
       "void_why": [du.judge_dl_defer(ev([]))[1], du.judge_dl_defer(ev(starved))[1],
                    du.judge_dl_defer(ev(starved, follow_t=MC + 126 + 150))[1], du.judge_dl_defer(ev(three, follow_t=MC - 5))[1],
                    du.judge_dl_defer(ev(wide80, follow_t=MC + 195))[1], du.judge_dl_defer(ev(wide80, follow_t=MC + 195), 17.0)[1],
                    du.judge_dl_defer(dead([x for x in ring if x["ui_state"] == "Pause"]))[1],
                    du.judge_dl_defer(ev(unframed(long_close), follow_t=MC + 10))[1]],
       "landed_why": du.judge_dl_defer(dead(ring))[1],
       "cal_frame": [du.cal_frame({}), du.cal_frame({"DA-CAL": {"frame": du.FRAME_MS_DEFAULT}}), du.cal_frame({"DA-CAL": {"frame": 17.0}}),
                     du.cal_frame({"DA-CAL": {"cal1": []}}), du.cal_frame(None)],
       "ring_since": [du.ring_since(object(), 5), du.ring_since(FakeG(), None),
                      [x["ui_state"] for x in du.ring_since(FakeG(), 0)], "slot" in du.ring_since(FakeG(), 0)[0]["netsync"]["swap"]],
       "src": ["f0 = guest.state.frame" in mr, mr.index("f0 = guest.state.frame") < mr.index('guest.press("pause", 6)'),
               'guest.send("press cancel 6", wait=False)' in hook, 'press("cancel"' not in hook, "keeps sampling" not in mr,
               'time.time() - state["pressed"] >= 0.6' in hook,
               mr.index("w.until(") < mr.index("ring = ring_since(guest, f0)") < mr.index("w.hold(1.0)"), '"ring": ring' in mr,
               '"landed": gi is not None' in mr, "judge_dl_defer(ev, cal_frame(ctx.marks))" in lm, "ctx.fms" not in lm],
       "claims": [du.CLAIMS["DL-DEFER"], du.CLAIMS["DP-DEFER"]], "consts": [du.DL_DEFER_MS, du.DL_BRACKET_FRAMES, du.DL_PLACE_FRAMES],
       "prob": ["DL-DEFER" in du.PROBABILISTIC, "DP-DEFER" in du.PROBABILISTIC]}
''')
    assert out["good"] == ["green"] * 6, out["good"]
    act, arr = out["act"], out["arr"]
    assert "the last Pause sample 255529460, the first off it 255529488 (28 ms wide)" in act, act
    assert "follow - last Pause 12 ms, follow - close -16 ms" in act and "record 45 seen 255528237" in act, act
    assert "the last Pause sample 256473056, the first off it 256473089 (33 ms wide)" in arr, arr
    assert "follow - last Pause 34 ms, follow - close 1 ms" in arr, arr
    assert out["bracket"] == [-10, 7, 17, False, True], out["bracket"]
    assert out["frames"] == [500000, 1, 2, None, None], out["frames"]
    assert out["keyed"] == [True, False], out["keyed"]       # the record before reads Pause with its own follow_t: never read
    assert out["edge"] == ["green"] * 3 and out["placed"] == ["green"] * 3, (out["edge"], out["placed"])
    assert all(v == "red" for v in out["bad"].values()), out["bad"]
    assert out["unseen"] == ["red", "red"] and out["unreached"] == ["unreached"] * 2, (out["unseen"], out["unreached"])
    assert out["unreached_why"][0].startswith("not reached: record 45 was not seen while paused (seen 8999991, the last Pause sample "
                                              "8999990): the intent is live across the Pause by construction (the cancel goes 1.2 s "
                                              "after the emit)"), out["unreached_why"]
    assert "-- the engine never ran the defer (P8); " in out["unreached_why"][0], out["unreached_why"]
    assert out["unreached_why"][1].startswith("not reached: record 45 was not seen while paused (seen 8999991, the last Pause sample "
                                              "8999990)"), out["unreached_why"]
    assert out["void"] == ["void"] * 6 and out["wide_void"] == ["void"] * 6, (out["void"], out["wide_void"])
    assert out["landed_void"] == ["void"] * 3, out["landed_void"]
    vw = out["void_why"]
    assert vw[0].startswith("the guest's ring holds no Pause sample: the bracket is unread"), vw
    assert vw[1].startswith("the bracket cannot decide the never-while-paused term (136 ms wide; the cap 52 ms is 3 frames of 17.0 ms "
                            "(the ring's) + 1)"), vw
    assert vw[2].startswith("the bracket cannot decide the lag term (136 ms wide; the cap 52 ms is 3 frames of 17.0 ms (the ring's) "
                            "+ 1)"), vw
    assert vw[3].startswith("the bracket cannot decide the never-while-paused term (the follow falls inside it: 2 unsampled frames "
                            "between frames 500000 and 500003; at most 1 is placed)"), vw
    assert vw[4].startswith("the bracket cannot decide the lag term (80 ms wide; the cap 52 ms is 3 frames of 17.0 ms (the ring's) "
                            "+ 1)"), vw
    assert vw[5].startswith("the bracket cannot decide the lag term (80 ms wide; the cap 52 ms is 3 frames of 17.0 ms (CAL's) + 1)"), vw
    assert vw[6].startswith("the guest never landed on AWAY and its ring ends on Pause: the Pause never closed (a setup miss)"), vw
    assert vw[7].startswith("the bracket cannot decide the never-while-paused term (the follow falls inside it: 20 ms before the "
                            "first sample off Pause, past its own frame of 17.0 ms (the ring's); a frame unread)"), vw
    assert out["landed_why"].startswith("the guest never landed on AWAY after its Pause closed: the deferred follow never came"), out
    assert out["cal_frame"] == [None, None, 17.0, None, None], out["cal_frame"]
    assert out["ring_since"] == [[], [], ["Pause", "FieldHUD"], False], out["ring_since"]
    assert all(out["src"]), out["src"]
    dl, dp = out["claims"]
    assert dl.startswith("the record seen while paused (else red 'not reached': the cancel goes 1.2 s after the emit"), dl
    assert "landed on AWAY (else red; VOID when its Pause never closed or its ring is empty)" in dl and "REACHED" not in dl, dl
    assert "bracketed off the guest's ring" in dl and "no Pause sample of this record with follow_t >= 0" in dl, dl
    assert "VOID wider than 3 frames + 1 ms" in dl and "only where the close's place inside it decides the verdict" in dl, dl
    assert "by the intent VOID with no sample after the last Pause sample" in dl and "1 unsampled frame" in dl, dl
    assert "DA-CAL's measured frame, else the ring's own median step" in dl, dl
    assert dp.startswith("REACHED when the record was seen while paused and that landing came by the intent"), dp
    assert out["consts"] == [200, 3, 2] and out["prob"] == [False, True], out


def test_each_duo_calibration_word_reds_exactly_its_rows_with_its_marker():
    """THE DUO ORACLE: the plain evidence reds nothing ([s164] THE ARRIVAL GUARD on: BASELINE_RED is empty and the ARRIVE gate green);
    each word's evidence (the engine under that lever, through the same twins) reds EXACTLY its registered rows -- its "if reached"
    DF-PACE when reached -- each with its marker, VOID / UNREACHED rows (DP-DEFER under `life`, DF-GRACE under `fade`, DA-GUARD under
    `life`) kept out of the count, and D-CAL passes; the `nocache` control reds nothing; `arrive` reds DA-ARRIVE alone, and `life`
    leaves DA-ARRIVE green (its scope correction: both ARRIVE runs keep `life act`)."""
    out = _duo_child(r'''
res = {}
for word in [None] + list(du.WORDS):
    rows, marks = duo_rows(word)
    failed, void, unreached, reds = sets(rows)
    entry = {"reds": reds, "void": sorted(void), "unreached": sorted(unreached), "arrive": rows["DA-ARRIVE"][0]}
    if word is not None:
        pred = du.predicted_now(word, void, unreached, du.LEGS_SEL)
        entry["pred"] = sorted(pred)
        entry["marks"] = {r: du.marker(word, r, marks.get(r))[0] for r in pred}
        entry["cal"] = list(du.judge_cal(word, failed, void, unreached, du.LEGS_SEL))
    res[str(word)] = entry
OUT = {"res": res, "arrive_detail": duo_rows("arrive")[0]["DA-ARRIVE"][1][:300]}
''')
    res = out["res"]
    assert res["None"]["reds"] == [] and res["None"]["void"] == [] and res["None"]["arrive"] == "green", res["None"]
    assert res["None"]["unreached"] == ["DP-PARTY"], res["None"]
    assert all(e["arrive"] == "green" for w, e in res.items() if w != "arrive"), {w: e["arrive"] for w, e in res.items()}
    assert "the guard was off at this landing (levers.arrive 'old', armed False)" in out["arrive_detail"], out["arrive_detail"]
    want = {"stamps": ["DA-LINES"], "delay": ["DA-CAL"], "orphan": ["DB-HOLD", "DB-ORDER"], "own": ["DC-B(b)"], "nocache": [],
            "pin": ["DP-DEFER", "DP-MARK"], "life": ["DL-DEFER", "DL-LIFE"], "fade": ["DF-3X", "DF-FAST", "DF-FLASH", "DF-OPEN", "DF-PACE"],
            "long": ["DF-3X", "DF-FAST"], "nogate": ["DF-OPEN", "DF-PACE"], "arrive": ["DA-ARRIVE"]}
    for word, rows in want.items():
        e = res[word]
        assert e["reds"] == rows == e["pred"], (word, e)
        assert e["cal"][0] is True, (word, e["cal"])
        assert all(v == "green" for v in e["marks"].values()), (word, e["marks"])
    assert res["life"]["void"] == ["DP-DEFER"] and "DF-GRACE" in res["fade"]["unreached"], (res["life"], res["fade"])
    assert "DA-GUARD" in res["life"]["unreached"] and "DA-GUARD" not in res["None"]["unreached"], res["life"]


def test_the_duo_markers_and_d_cal_can_fail():
    """Each word's marker is red on the plain evidence (the lever's signature absent); D-CAL is red on a predicted red that stayed green,
    on an unpredicted red, on a predicted red read UNREACHED / VOID, and VOID when every predicted red is out; VOID rows elsewhere never
    count; an "if reached" row joins only when reached. [s164] BASELINE_RED is empty: an unpredicted DA-ARRIVE red COUNTS; the `arrive`
    marker needs all three of its parts (the dwell OUT on 30611, levers.arrive old, armed false); an unregistered ARRIVE_ID's DA-ARRIVE
    is VOID -- D-CAL under `arrive` reads VOID (never exact), and under another word it is VOID elsewhere (never an unpredicted red)."""
    out = _duo_child(r'''
rows, marks = duo_rows()
plain = {}
for word in du.WORDS:
    for r in du.WORDS[word][1] + du.WORDS[word][2]:
        plain[f"{word}:{r}"] = du.marker(word, r, marks.get(r))[0]
L_ = du.LEGS_SEL
jc = lambda w, failed, void=(), unr=(): du.judge_cal(w, set(failed), set(void), set(unr), L_)[0]
OUT = {"plain": plain, "nocache": du.marker("nocache", "x", {})[0],
       "arrive_parts": [du.marker("arrive", "DA-ARRIVE", {"gate": dict(g, **kw)})[0] for g in [duo_rows("arrive")[1]["DA-ARRIVE"]["gate"]]
                        for kw in ({}, {"dwell_lines": 0, "dwell_count": 0}, {"lever": None}, {"armed": True}, {"dest": 30602})],
       "cal": {"exact": jc("orphan", ["DB-HOLD", "DB-ORDER"]), "arrive_counts": jc("orphan", ["DB-HOLD", "DB-ORDER", "DA-ARRIVE"]),
               "arrive_exact": jc("arrive", ["DA-ARRIVE"]), "arrive_extra": jc("arrive", ["DA-ARRIVE", "DA-GUARD"]),
               "arrive_green": jc("arrive", []),
               "void_elsewhere": jc("orphan", ["DB-HOLD", "DB-ORDER", "DB-SHAPE"], ["DB-SHAPE"]),
               "missing": jc("orphan", ["DB-HOLD"]), "extra": jc("orphan", ["DB-HOLD", "DB-ORDER", "DA-CAL"]),
               "lost": jc("orphan", ["DB-HOLD", "DB-ORDER"], ["DB-ORDER"]), "all_out": jc("own", ["DC-B(b)"], [], ["DC-B(b)"]),
               "cond_reached_red": jc("nogate", ["DF-OPEN", "DF-PACE"]), "cond_reached_green": jc("nogate", ["DF-OPEN"]),
               "cond_unreached": jc("nogate", ["DF-OPEN"], [], ["DF-PACE"]), "nocache_clean": jc("nocache", []),
               "nocache_red": jc("nocache", ["DC-B(b)"])},
       "all_out_why": du.judge_cal("own", {"DC-B(b)"}, set(), {"DC-B(b)"}, L_)[1],
       # an unregistered ARRIVE_ID is a setup miss: _leg_cal VOIDs DA-ARRIVE (_lost) -- never the `arrive` word's predicted red, and
       # under any other word reported as VOID elsewhere, never an unpredicted red (the plain-R record read "exact": arrive_exact)
       "unreg": list(du.judge_cal("arrive", {"DA-ARRIVE"}, {"DA-ARRIVE"}, set(), L_)),
       "unreg_other": jc("orphan", ["DB-HOLD", "DB-ORDER", "DA-ARRIVE"], ["DA-ARRIVE"])}
''')
    assert all(v == "red" for v in out["plain"].values()) and out["nocache"] == "red", out
    c = out["cal"]
    assert out["arrive_parts"] == ["green", "red", "red", "red", "red"], out["arrive_parts"]
    for k in ("exact", "void_elsewhere", "cond_reached_red", "cond_unreached", "nocache_clean", "arrive_exact"):
        assert c[k] is True, (k, c)
    for k in ("missing", "extra", "lost", "all_out", "cond_reached_green", "nocache_red", "arrive_counts", "arrive_extra", "arrive_green"):
        assert c[k] is False, (k, c)
    assert out["all_out_why"].startswith("VOID: every predicted red"), out
    assert out["unreg"][0] is False and out["unreg"][1].startswith("VOID: every predicted red read UNREACHED or VOID"), out["unreg"]
    assert out["unreg_other"] is True and c["arrive_exact"] is True, out      # the VOID record is the mutant-killer: R read exact


def test_the_duo_reads_its_evidence_off_the_engines_samples():
    """tr_evidence / arrival_of / desk_evidence / host_close_t / fade_left_start off sample streams in the engine's state shape: the
    records at their most advanced sample, the overlap and the step-out window on the swap clock, the party at the emit and at the
    landing, the host's close found by its TEXT (a host's `netsync.windows` lists nothing: window tracking is guest-only), and the
    per-follow left_start read while the follow ran. [s164] THE ARRIVAL GUARD's evidence (arrive_evidence) off the guest's
    `netsync.swap.arrive`: the lever and the arm at the landing, the first non-null lead_ms (DA-GUARD's anchor), the episode's last
    shift with the lead it was made with, the guarded peak, B - G from the episode's own base (a base re-armed before the episode never
    reads as a guard defect; with no episode, the first base sample, 0 ms old included), R's seen_t (dx) and the base's end (d7)."""
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
    ep = on and 1500 <= t <= 2850
    sw.update({"arrive.field": D if on else -1, "arrive.land_t": 1400 if on else -1, "arrive.armed": on,
               "arrive.lead_ms": 500 if on and t >= 1450 else None, "arrive.host.seen_t": 970 if on else -1,
               "arrive.episode.on": ep, "arrive.episode.shift_ms": 540 if ep else None,
               "arrive.episode.dwell_ms": (t - 1400 - 540) if ep else None})
    gs.append(Sx(t, D if on else 250, ctl=t >= 3300 or t < 430, sw=sw, step=step, want=2 if on else -1, mirror=[0, 4, 2, 3] if on else None))
tr = du.tr_evidence("CAL", "ARRIVE", D, 250, hs, gs, [], [DWELL_OUT(D)], "gate")
a = du.arrival_of(tr, "gate")
# a base that flickered (t 1450) before the episode re-armed it at 1500: one episode = one base, so the engine's shift is made from
# the NEW base (K - (100 + 500) = 440) -- B - G must come from the episode's own base, never the first base sample (0: a false
# "guard defect"); with no episode the first base sample stands, and a base 0 ms old counts as one
gs2 = copy.deepcopy(gs)
for x in gs2:
    t = so.now_ms(x)
    if t == 1450:
        x["netsync"]["stepout"]["base"]["age_ms"] = -1
    elif 1500 <= t <= 3200:
        x["netsync"]["stepout"]["base"]["age_ms"] = t - 1500
    if x["netsync"]["swap"]["arrive"]["episode"]["on"]:
        x["netsync"]["swap"]["arrive"]["episode"]["shift_ms"] = 440
tr2 = du.tr_evidence("CAL", "ARRIVE", D, 250, hs, gs2, [], [DWELL_OUT(D)], "gate")
gs3 = copy.deepcopy(gs2)
for x in gs3:
    x["netsync"]["swap"]["arrive"]["episode"]["on"] = False
tr3 = du.tr_evidence("CAL", "ARRIVE", D, 250, hs, gs3, [], [DWELL_OUT(D)], "gate")
host_txt = [Sx(t, 351, texts=["Text 139"] if 100 <= t < 700 else (["Next"] if t >= 900 else None)) for t in range(0, 1200, 50)]
guest_txt = [Sx(t, 351, wins=[(3, 139, "locked")] if 300 <= t < 1000 else (), texts=["Text 139"] if 300 <= t < 1000 else None)
             for t in range(0, 1200, 50)]
OUT = {"h_id": tr["h"]["last"]["id"], "g_id": tr["g"]["last"]["id"], "g_land": tr["g_land_t"], "h_land": tr["h_land_t"],
       "h_ctl": tr["h_ctl_t"], "overlap": tr["overlap"], "base_peak": tr["base_peak"], "dwell": tr["dwell_count"], "active": tr["active"],
       "dressed": tr["dressed"], "party": [tr["party_emit"], tr["party_land"], tr["mirror_after"]], "emit": tr["hi"].get("emit_t"),
       "arrival": [a["dwell_lines"], du.arrive_reached(a)], "verdict": du.judge_da_arrive([a, du.arrival_of(dict(tr, gl=[], dwell_count=0, active=False), "control")]),
       "guard": [tr["arrive"][k] for k in ("lever", "armed", "lead", "lead_ep", "shift", "dwell_peak", "b_minus_g", "seen_t", "base_end_t")],
       "view": [a[k] for k in ("lead", "shift", "dx", "d7", "A", "gap")],
       "rearm": [tr2["arrive"]["b_minus_g"], du.arrive_gate_verdict(du.arrival_of(tr2, "gate"))[1], tr3["arrive"]["b_minus_g"]],
       "none": du.arrive_evidence(gs, None, None, D),
       "host_close": du.host_close_t(host_txt, guest_txt, (3, 139)), "guest_close": du.close_t(guest_txt, (3, 139)),
       "left": du.fade_left_start(gs, 430, D), "cur": du.fade_cur_window(gs, 430, 900, D)[:2],
       "dip": [du.dipped([200, 216, 210, 248]), du.dipped([200, 190, 248]), du.dipped([200, None, 0])]}
''')
    assert (out["h_id"], out["g_id"], out["g_land"], out["h_land"], out["h_ctl"]) == (6, 9, 1400, 900, 3200), out
    assert out["overlap"] == 1800 and out["base_peak"] == 1800 and out["dwell"] == 1 and out["active"] and out["dressed"], out
    assert out["party"] == [[0, 1, 2, 3], [0, 4, 2, 3], [0, 4, 2, 3]] and out["emit"] == 400, out
    assert out["arrival"] == [1, True] and out["verdict"][0] == "red", out
    assert "margin miss: the guard shifted 540 ms as its rule says" in out["verdict"][1], out["verdict"]
    assert out["guard"] == [None, True, 500, 500, 540, 2850 - 1400 - 540, 0, 970, 3300], out["guard"]
    assert out["view"] == [500, 540, 70, 100, 2300, 500] and out["none"] == {}, out
    bmg2, why2, bmg3 = out["rearm"]
    assert bmg2 == 100 and why2.startswith("margin miss: the guard shifted 440 ms as its rule says") and bmg3 == 0, out["rearm"]
    assert out["host_close"] == 700 and out["guest_close"] == 1000 and out["left"] == 7, out
    assert out["dip"] == [False, True, True], out


def test_desk_evidence_ends_the_351_window_at_352_and_reads_the_section8_pick():
    """[s164] desk_evidence off sample streams (the first duo run's DESK shape): HOME -> 359 -> 351, where the desk scene never gives
    control back (it runs straight into the 352 MAPJUMP, a bounce reload of 351 in between), then 352's lawful dwell OUT 1.7 s into its
    7.9 s wordless scene. The 351 arrival's step-out window ends at the 352 landing: dwell_count 0, its base peak 351's alone -- the
    window "to control" blamed 352's OUT on 351 (five false DESK watch OUTs). A GENUINE 351 dwell OUT still counts (a watch lists it; a
    control-desk under `fade` reds DA-ARRIVE). DP-DRESS's expect is the host's section-8 pick off its last 352 sample: guard.effective
    over dress.party through ResolveAuto's twin -- 3 (Steiner, the run's), 0 when the guard names Zidane's slot (the falsy-zero trap),
    255 for no owned member, None unread; and slim() keeps guard.effective (a slimmed live sample reads the same pick)."""
    out = _duo_child(_DA_A + r'''
def streams(genuine=False, eff=2, party=(0, 3, 1, 2)):
    hs, gs = [], []
    for t in range(0, 14000, 50):
        if 4000 <= t < 4150:
            continue                                     # a bounce reload of 351: no publish while it loads, then 351 again
        f = 250 if t < 1000 else 359 if t < 3000 else 351 if t < 6000 else 352
        ctl = t < 1000
        on352 = t >= 6000
        hs.append(Sx(t, f, ctl=ctl, party=list(party), leader=2 if on352 else 0, eff=eff if on352 else 2))
        dwell = 0
        base = -1
        if genuine and 3100 <= t < 4650 and f == 351:
            base = t - 3100                              # a wordless 351 hold: the base reaches 1500 and steps out by dwell
        if genuine and t >= 4650:
            dwell = 1
        if on352 and 6200 <= t < 7750:
            base = t - 6200                              # 352's wordless lead: base armed ~+200, OUT by dwell at ~1.55 s
        if on352 and t >= 7750:
            dwell += 1
        gs.append(Sx(t, f, ctl=ctl, want=3 if t >= 3000 else -1, party=[0, 3, 1, 2],
                     step={"base.age_ms": base, "out_why.dwell": dwell, "active": on352 and t >= 7750}))
    return hs, gs
ev = du.desk_evidence(1.0, False, *streams(), [], [])
evg = du.desk_evidence(1.0, False, *streams(genuine=True), [], [])
evf = du.desk_evidence(1.0, False, *streams(genuine=True), [], [], "fade")
a, ag, af = (du.arrival_of(e["t351"], e["t351"]["kind"]) for e in (ev, evg, evf))
hs0, gs0 = streams()
slimmed = [du.slim(x) for x in hs0]
OUT = {"plain": [ev["t351"]["dwell_count"], ev["t351"]["base_peak"], ev["t351"]["kind"], du._out(a), a["dressed"]],
       "genuine": [evg["t351"]["dwell_count"], evg["t351"]["base_peak"], du._out(ag)],
       "rest_out": ev["t352"]["dwell_count"],
       "fade": [evf["t351"]["kind"], du._out(af)],
       "verdict": [du.judge_da_arrive([A(), CTL, a])[0], du.judge_da_arrive([A(), CTL, ag])[0], du.judge_da_arrive([A(), CTL, af])[0]],
       "watch_rep": du.judge_da_arrive([A(), CTL, ag])[1],
       "dress": [ev["dress"], du.desk_evidence(1.0, False, *streams(eff=1), [], [])["dress"],
                 du.desk_evidence(1.0, False, *streams(eff=0), [], [])["dress"],
                 du.desk_evidence(1.0, False, *streams(eff=-1), [], [])["dress"],
                 du.desk_evidence(1.0, False, slimmed, gs0, [], [])["dress"]],
       "judged": du.judge_dp_dress([ev["dress"]])[0],
       "pick": [du.section8_pick([0, 3, 1, 2], 2), du.section8_pick([0, 3, 1, 2], 1), du.section8_pick([0, 3, 1, 2], 0x8),
                du.section8_pick([-1, 3, 1, 2], 0x3), du.section8_pick([0, -2, 1, 2], 0x2), du.section8_pick([0, 13, 1, 2], 0x2),
                du.section8_pick([0, 3, 1, 2], 0), du.section8_pick(None, 2), du.section8_pick([0, 3, 1, 2], None),
                du.section8_pick([0, 3, 1, 2], -1)],
       "slim_guard": slimmed[-1]["netsync"]["dress"]["guard"]}
''')
    assert out["plain"] == [0, -1, "watch-desk", False, True], out["plain"]      # the old window read [1, 1500, ..., True, ...]
    assert out["genuine"][0] == 1 and out["genuine"][1] >= 1500 and out["genuine"][2] is True, out["genuine"]
    assert out["rest_out"] == 1, out                                               # the 352 OUT is still 352's own
    assert out["fade"] == ["control-desk", True], out["fade"]
    assert out["verdict"] == ["green", "green", "red"], out["verdict"]
    assert "watches (reported apart, never judged): dressed 1, OUTs 1 (watch-desk/D1.0)" in out["watch_rep"], out["watch_rep"]
    assert out["dress"] == [{"want": 3, "expect": 3, "leader": 2}, {"want": 3, "expect": 0, "leader": 2},
                            {"want": 3, "expect": 255, "leader": 2}, {"want": 3, "expect": None, "leader": 2},
                            {"want": 3, "expect": 3, "leader": 2}], out["dress"]
    assert out["judged"] == "green", out
    assert out["pick"] == [3, 0, 2, 3, 255, 255, 255, None, None, None], out["pick"]
    assert out["slim_guard"] == {"leader": 2, "effective": 2}, out["slim_guard"]


def test_desk_evidence_holds_the_351_window_across_a_real_bounce_reload():
    """[s164] Fix round 2 (refuter 2's second required case, refuter 1's edge), with a REAL bounce reload of 351 inside the 351 window
    rather than a publish gap: the guest's field.id flips to 0 and then None (refuter 1's edge: a reload publishing either) and back to
    351, its step-out base re-arms (-1 through the reload, then counting again on the reloaded copy), and in run 6's shape a
    control-true sample lands on the reloaded 351. The 351 slice still ends at the 352 landing -- 352's lawful dwell OUT (its 7.9 s
    wordless lead) never reaches the 351 arrival, and dwell_count is 351's own. A field.id of 0 or None ends neither the slice nor the
    step-out window (only control back ON 351 does, even with a control-true read off the field), so a genuine dwell OUT on the
    reloaded copy still counts -- reported as a watch at act, red on the control-desk under `fade`; run 6's control-true sample ends
    the window there (its base peak the landing's alone). The window before fix round 1 (the whole tail) reads 352's OUT on the plain
    reload: the fixture can catch the old defect. Report only: the DESK fade dict carries `old`, and DF-FLASH's detail names REST-OLD.
    [s164] Fix round 3: the fade dict carries the 351 record's own edges (`last`, DESK_REC_KEYS); a record that never followed is never
    judged, whatever fade.last reads (one global last-follow block: an earlier follow's)."""
    out = _duo_child(_DA_A + r'''
def reload_streams(case):
    hs, gs = [], []
    for t in range(0, 9000, 50):
        f = 250 if t < 1000 else 359 if t < 3000 else 351 if t < 6000 else 352
        hs.append(Sx(t, f, ctl=t < 1000))
        gf, ctl, base, dwell, active = f, t < 1000, -1, 0, False
        if 4000 <= t < 4150:
            gf = 0 if t < 4100 else None                 # the reload publishes field.id 0, then None, then 351 again
            ctl = case == "genuine"                      # a control-true read OFF the field never ends the window
        if f == 351 and 3100 <= t < 4000:
            base = t - 3100                              # the landing's base, re-armed by the reload
        if case == "genuine":
            if f == 351 and 4150 <= t < 5700:
                base = t - 4150                          # the reloaded copy's wordless hold: 1500 at 5650, OUT by dwell at 5700
            if t >= 5700:
                dwell = 1
            active = 5700 <= t < 6000
        elif f == 351 and 4600 <= t < 6000:
            base = t - 4600                              # re-armed after the reload: peaks 1350 on the last 351 sample, no OUT
        if case == "ctl" and t == 4200:
            ctl = True                                   # run 6's escape: control-true on the reloaded 351 ends the window there
        if f == 352 and 6200 <= t < 7750:
            base = t - 6200                              # 352's lawful wordless lead: base armed ~+200, OUT by dwell at ~1.55 s
        if f == 352 and t >= 7750:
            dwell, active = dwell + 1, True
        s = Sx(t, 351 if gf is None else gf, ctl=ctl, want=3 if t >= 3000 else -1, party=[0, 3, 1, 2],
               step={"base.age_ms": base, "out_why.dwell": dwell, "active": active})
        if gf is None:
            s["field"]["id"] = None
        gs.append(s)
    return hs, gs
ev = {c: du.desk_evidence(1.0, False, *reload_streams(c), [], []) for c in ("flip", "genuine", "ctl")}
evf = du.desk_evidence(1.0, False, *reload_streams("genuine"), [], [], "fade")
evo = du.desk_evidence(0.3, True, *reload_streams("flip"), [], [])
arr = {c: du.arrival_of(e["t351"], e["t351"]["kind"]) for c, e in ev.items()}
af = du.arrival_of(evf["t351"], evf["t351"]["kind"])
hs0, gs0 = reload_streams("flip")
g359 = du.land_idx(gs0, du.DESK_FIELD)
join = {"field": 351, "view_start": "black", "action": "join", "by": "own"}
FOLLOWED = {"follow_t": 3000, "own_t": 3000, "follows": 1}      # [s164] fix round 3: a record that followed, its own pass at the follow
OUT = {c: [e["t351"]["g_land_t"], e["t351"]["dwell_count"], e["t351"]["base_peak"], e["t351"]["active"], e["t351"]["kind"],
           e["t352"]["g_land_t"], e["t352"]["dwell_count"], du._out(arr[c])] for c, e in ev.items()}
OUT.update({"fade": [evf["t351"]["kind"], evf["t351"]["dwell_count"], du._out(af)],
            "verdict": [du.judge_da_arrive([A(), CTL, arr[c]])[0] for c in ("flip", "genuine", "ctl")] + [du.judge_da_arrive([A(), CTL, af])[0]],
            "watch": [du.judge_da_arrive([A(), CTL, arr[c]])[1].split("watches (reported apart, never judged): ")[1].split(";")[0]
                      for c in ("flip", "genuine", "ctl")],
            "whole_tail": du.tr_evidence("DESK", "D1.0", du.REST_FROM, du.DESK_FIELD, hs0[g359:], gs0[g359:])["dwell_count"],
            "old": [ev["flip"]["fade"]["old"], evo["fade"]["old"]],
            "flash": du.judge_df_flash([dict(evo["fade"], fade=join, cur=[], last=FOLLOWED)])[1],
            "flash_act": du.judge_df_flash([dict(ev["flip"]["fade"], fade=join, cur=[], last=FOLLOWED)])[1],
            "flash_nofollow": list(du.judge_df_flash([dict(ev["flip"]["fade"], fade=join, cur=[])])),
            "last_keys": [sorted(ev["flip"]["fade"]["last"]), ev["flip"]["fade"]["last"]["follow_t"]]})
''')
    # [the 351 landing, its dwell_count, its base peak, stepout.active, kind, the 352 landing, 352's dwell_count, _out]
    assert out["flip"] == [3000, 0, 1350, False, "watch-desk", 6000, 1, False], out["flip"]      # the re-armed peak, never 352's 1500
    assert out["genuine"] == [3000, 1, 1500, True, "watch-desk", 6000, 1, True], out["genuine"]  # the reloaded copy's OUT counts once
    assert out["ctl"] == [3000, 0, 850, False, "watch-desk", 6000, 1, False], out["ctl"]          # ended at run 6's control sample
    assert out["fade"] == ["control-desk", 1, True], out["fade"]
    assert out["verdict"] == ["green", "green", "green", "red"], out["verdict"]
    assert out["watch"] == ["dressed 1, OUTs 0 (none)", "dressed 1, OUTs 1 (watch-desk/D1.0)", "dressed 1, OUTs 0 (none)"], out["watch"]
    assert out["whole_tail"] == 1, out                   # the pre-fix window folds 352's OUT into the 351 arrival
    assert out["old"] == [False, True], out["old"]
    assert out["flash"].endswith("D 0.3 REST-OLD: black/None/join by own, dip False"), out["flash"]
    assert "D 1.0: black/None/join by own" in out["flash_act"] and "REST-OLD" not in out["flash_act"], out["flash_act"]
    # [s164] fix round 3: the streams' record never followed (follow_t -1): listed apart, never judged
    assert out["flash_nofollow"][0] == "unreached", out["flash_nofollow"]
    assert "listed apart, never judged: D 1.0: no follow on this record" in out["flash_nofollow"][1], out["flash_nofollow"]
    assert out["last_keys"] == [sorted(["id", "seen_t", "follow_t", "follows", "own_t", "own_verdict", "bounces", "reload_t"]), -1], out


def test_the_menu_mark_and_left_legs_read_the_engines_timing():
    """[s164] The first duo run's MENU / MARK / LEFT / OPEN setup misses, fixed in the bench: MENU holds PAUSE (a mirroring guest's MAIN
    menu is refused by design: s38 spectator-field, s121) -- menu_close_t keys on Pause, the pre-guard VOIDs only a key that cannot
    reach the scene branch ("audible" is a mirroring guest's normal FieldHUD read, never a VOID), a Pause that never opens is a VOID
    setup miss, the close is a cancel (Pause toggles); MARK and MENU mark 8720 at the host's LANDING HOOK (intent.landed_ms >= 0 for the
    new intent -- field.id flips before the hook; the body / control trigger came ~1 s after the guest's landing); LEFT exits to HOME,
    waits for the guest's landing and holds 0.8 s past the landing hook on the swap clock, pumps the watch through the battle start
    and always ends its battle (fix round 2: escapes first -- _left_escape, Zidane's Flee at a host prompt, else the bumper roll,
    re-rolled while left_may_reroll -- and fights last with finish=False and leave_battle(stop_on_field=True), then waits for the
    guest back from its diorama); a battle left up on the host makes _seat raise after its SEAT_FIELD_S grace (OPEN reads the true
    cause, not SEAT_S burned)."""
    out = _duo_child(r'''
import inspect
gs = [Sx(t, 250, ui="Pause" if 200 <= t < 900 else ("MainMenu" if 1000 <= t < 1200 else "FieldHUD")) for t in range(0, 1500, 50)]
h = lambda t, f, lm, e=5000, n=4: Sx(t, f, sw={"intent.landed_ms": lm, "intent.emit_t": e, "intent.nonce": n, "intent.active": True,
                                               "intent.end_t": -1, "intent.last_end": "stands"})
src = {f.__name__: inspect.getsource(f) for f in (du._menu_run, du._leg_mark, du._leg_left, du._end_left_battle, du._seat,
                                                  du._left_escape)}
mr, mk, lf, eb, st, es = (src[k] for k in ("_menu_run", "_leg_mark", "_leg_left", "_end_left_battle", "_seat", "_left_escape"))
OUT = {"close": du.menu_close_t(gs), "close_none": du.menu_close_t([Sx(t, 250, ui="MainMenu") for t in (0, 50)] + [Sx(100, 250)]),
       "pre": [du.menu_pre_void(v) for v in ("open", "audible", None)],
       "pre_void": [bool(du.menu_pre_void(v)) for v in ("dialog", "off", "silent", "")],
       "pre_why": du.menu_pre_void("dialog"),
       "pre_s168": [bool(du.menu_pre_void("guest")), du.menu_pre_void("guest", True), bool(du.menu_pre_void("dialog", True))],
       "landed": [du.host_landed_on(h(0, 30602, -1), 30602, 4000), du.host_landed_on(h(0, 30602, 322), 30602, 4000),
                  du.host_landed_on(h(0, 250, 322), 30602, 4000), du.host_landed_on(h(0, 30602, 0), 30602, 4000),
                  du.host_landed_on(h(0, 30602, 322, e=4000), 30602, 4000), du.host_landed_on(h(0, 30602, 322), 30602),
                  du.host_landed_on(h(0, 30602, None), 30602)],
       "probe": du.intent_probe(h(700, 250, 300)), "probe_none": du.intent_probe(None),
       "off_field": [du.first_off_field_t([Sx(t, 250, scene="FieldMap" if t < 300 else "BattleMap") for t in range(0, 500, 100)]),
                     du.first_off_field_t([Sx(0, 250)])],
       "menu_src": ['guest.press("pause", 6)' in mr, "open_menu" not in mr, '"MainMenu"' not in mr, 'guest.press("cancel", 6)' in mr,
                    'press("pause", 6)' not in mr.split('guest.press("pause", 6)', 1)[1], "raise HarnessError(why)" in mr,
                    "host_landed_on(x, AWAY, e0)" in mr, "menu_pre_void(" in mr, "the guest's Pause never opened" in mr,
                    mr.index("menu_pre_void(") < mr.index('guest.press("pause", 6)') < mr.index("w = _Watch(d)")],
       "mark_src": ["host_landed_on(x, AWAY, e0)" in mk, "body_ms" not in mk, "_ctl(x)" not in mk,
                    '_lever(guest, ctx, "fade", "long")' in mk],
       "left_src": ["_seat(d, AWAY)" in lf, 'warp {HOME} -1 -1' in lf, "host_landed_on(w.last(\"host\"), HOME, e0)" in lf,
                    "_fid(w.last(\"guest\")) == HOME" in lf, "land_at + LEFT_BATTLE_MS" in lf, "intent_probe(w.last(\"host\"))" in lf,
                    "first_off_field_t(w.s[\"host\"][k:])" in lf, '"dest": HOME' in lf, "finally:" in lf and "_end_left_battle(d)" in lf,
                    "w.s[\"host\"] if cb.raw(x).get(\"scene\")" not in lf,
                    lf.index("_fid(w.last(\"guest\")) == HOME") < lf.index("host.send(f\"battle")],
       "end_src": ['host.act("Flee", slot=slot)' in es, 'host.act("Defend", slot=slot)' in es,
                   "host.flee(timeout=LEFT_ROLL_S)" in es,
                   es.index('host.act("Flee", slot=slot)') < es.index("host.flee(timeout=LEFT_ROLL_S)"),
                   "host.flee(" not in eb, "for attempt in range(LEFT_FLEE_TRIES):" in eb, "left_may_reroll(st)" in eb,
                   eb.index("_left_escape(d, tried)") < eb.index("host.fight(timeout=LEFT_FIGHT_S, finish=False)"),
                   "host.leave_battle(stop_on_field=True)" in eb, "if not host.state.in_battle:" in eb,
                   eb.index("not s.in_battle and s.on_field and s.control") < eb.index("guest_back_on(s, fld)")],
       "seat_src": st.index("if host.state.in_battle and cb.poll(") < st.index("if _settled(d, field):") and "raise HarnessError" in st,
       "consts": [du.PAUSE_UI, list(du.MENU_PRE_OK), du.LEFT_BATTLE_MS]}
''')
    assert out["close"] == 900 and out["close_none"] is None, out           # keyed on Pause: the MainMenu stretch never reads
    assert out["pre"] == [None, None, None] and out["pre_void"] == [True] * 4, out
    # [ff9mapkit netsync s168] decision 32's re-key BY STAGE: `guest` goes on only when the probe shows `netsync.guestmenu` (a VOID on s167)
    assert out["pre_s168"] == [True, None, True], out["pre_s168"]
    assert out["pre_why"].startswith("VOID (a setup miss): the guest's menu_refusal.now reads 'dialog'"), out["pre_why"]
    assert out["landed"] == [False, True, False, True, False, True, False], out["landed"]
    assert out["probe"] == {"active": True, "nonce": 4, "now_ms": 700, "end_t": -1, "last_end": "stands"}, out["probe"]
    assert out["probe_none"] == {"active": None, "nonce": None, "now_ms": None, "end_t": None, "last_end": None}, out
    assert out["off_field"] == [300, None], out["off_field"]
    for k in ("menu_src", "mark_src", "left_src", "end_src"):
        assert all(out[k]), (k, out[k])
    assert out["seat_src"] is True and out["consts"] == ["Pause", ["open", "audible"], 800], out


# [s164] LEFT's stand-ins (review round 2's F1 cluster; fix round 2's escape order and warm return): each state read is one published
# frame, 1/30 s of a virtual clock
_LEFT_STANDIN = r'''
from types import SimpleNamespace as NS
class Clock:
    def __init__(self):
        self.t = 1000.0
    def time(self):
        return self.t
    def sleep(self, s):
        self.t += max(0.0, s)
clk = Clock()
du.time = clk                                            # swap the NAME (a module-global patch is process-wide)
def smp(batt, ui, ctl, fid=du.HOME, raw=None):
    return NS(in_battle=batt, ui_state=ui, on_field=ui == "FieldHUD", control=ctl, field_id=fid, dialog_open=False, raw=raw or {})
def party(*hp):
    """battle.units: the players' (hp, hp_max), alive while hp > 0, and the Goblin."""
    us = [{"slot": i, "player": True, "hp": a, "hp_max": m, "alive": a > 0} for i, (a, m) in enumerate(hp)]
    return {"battle": {"active": True, "units": us + [{"slot": 4, "player": False, "hp": 33, "hp_max": 33, "alive": True}]}}
BATT, GONE, FLD = smp(True, "BattleMap", False), smp(False, "BattleResult", False), smp(False, "FieldHUD", True)
BATT_OK = smp(True, "BattleMap", False, raw=party((105, 105), (100, 120), (31, 60), (7, 70)))   # the first run after its lost roll
BATT_LOW = smp(True, "BattleMap", False, raw=party((105, 105), (40, 120), (0, 60), (7, 70)))   # 152 of 355: under half
class Host:
    """Reads walk ``script`` and stall at ``hold`` until an escape lands (``escape_at``: Flee taken at a prompt, or a flee() that
    answers True) or fight() (``fight_at``) moves them on; ``fled`` flee()'s answers in turn (the last repeats), ``turns`` the host's
    prompts in order (none left: wait_turn raises), ``flee_slots`` the slots whose menu has Flee; a warp sent off FieldHUD is dropped.
    ``waits`` the timeout each wait_turn was given, in order."""
    def __init__(self, script, hold=None, fled=True, fight_at=None, escape_at=None, turns=(), flee_slots=(0,)):
        self.script, self.hold, self.fight_at, self.escape_at = script, len(script) - 1 if hold is None else hold, fight_at, escape_at
        self.fled = list(fled) if isinstance(fled, (list, tuple)) else [fled]
        self.turns, self.flee_slots = list(turns), tuple(flee_slots)
        self.k, self.cur, self.calls, self.sent, self.to = 0, None, [], [], None
        self.waits = []
    @property
    def state(self):
        s = self.script[self.k]
        self.k = min(self.k + 1, self.hold)
        clk.sleep(1 / 30)
        self.cur = s if self.to is None else NS(**dict(vars(s), field_id=self.to))
        return self.cur
    def wait_for(self, pred, *, timeout=20.0, what="condition"):
        end = clk.t + timeout
        while clk.t < end:
            s = self.state
            if pred(s):
                return s
        raise du.HarnessError(f"timed out waiting for {what}")
    def _escape(self):
        if self.escape_at is not None:
            self.k, self.hold = self.escape_at, len(self.script) - 1
    def wait_turn(self, *, timeout=90.0):
        self.waits.append(timeout)
        self.state
        if not self.turns:
            raise du.HarnessError("timed out waiting for a party member to be asked for a command")
        return self.turns.pop(0)
    def act(self, command="Attack", *, slot=None, target=None, timeout=20.0):
        self.calls.append(f"{command} {slot}")
        if command == "Flee":
            if slot not in self.flee_slots:
                raise du.HarnessError(f"slot {slot} has no move called 'Flee'")
            self._escape()
        return {}
    def flee(self, **kw):
        self.calls.append("flee")
        ok = self.fled.pop(0) if len(self.fled) > 1 else self.fled[0]
        if ok:
            self._escape()
        return ok
    def fight(self, **kw):
        self.calls.append("fight")
        self.k, self.hold = self.fight_at, len(self.script) - 1
        return 1
    def leave_battle(self, **kw):
        self.calls.append("leave")
        return "BattleResult"
    def send(self, cmd, wait=True):
        self.sent.append([cmd, self.cur.ui_state])
        if cmd.startswith("warp") and self.cur.on_field:
            self.to = int(cmd.split()[1])
    def press(self, *a, **kw):
        pass
HOME_G, DIO = (False, "FieldHUD", True), (True, "BattleHUD", True)     # a booted diorama publishes control true on BattleHUD
class Guest:
    """The guest's reads walk ``script`` [(diorama booted, ui_state, control)] and hold at its last (default: home on its field HUD
    with control); its field is the host's (the warp target once sent), as a diorama keeps its boot field."""
    def __init__(self, host, script=None):
        self.host, self.script, self.k = host, list(script or [HOME_G]), 0
    @property
    def state(self):
        booted, ui, ctl = self.script[min(self.k, len(self.script) - 1)]
        self.k += 1
        clk.sleep(1 / 30)
        h = self.host
        fid = h.to if h.to is not None else (h.cur or h.script[0]).field_id
        return NS(field_id=fid, control=ctl, dialog_open=False, ui_state=ui,
                  raw={"ui_state": ui, "field": {"id": fid}, "player": {"control": ctl}, "netsync": {"diorama": {"booted": booted}}})
    def wait_for(self, pred, *, timeout=20.0, what="condition"):
        end = clk.t + timeout
        while clk.t < end:
            s = self.state
            if pred(s):
                return s
        raise du.HarnessError(f"timed out waiting for {what}")
    def send(self, cmd, wait=True):
        pass
def pair(host, gscript=None):
    notes = []
    return NS(host=host, guest=Guest(host, gscript), note=notes.append, notes=notes)
def end(host, gscript=None):
    d = pair(host, gscript)
    du._end_left_battle(d)
    return d, {"last": [host.cur.in_battle, host.cur.ui_state, host.cur.control], "calls": host.calls, "notes": d.notes,
               "guest_k": d.guest.k}
def seat(host, field=du.AWAY):
    d = pair(host)
    try:
        du._seat(d, field)
        err = None
    except du.HarnessError as e:
        err = str(e)
    return {"err": err, "sent": host.sent, "notes": d.notes}
'''


def test_left_ends_its_battle_on_the_field_hud_and_open_seats_behind_it():
    """[s164] Review round 2 (the F1 cluster), on the stand-in host: a True escape is the SysEscape QUEUED, so _end_left_battle waits for
    the battle scene to go AND the field HUD with control (ui_state lags as BattleResult) before returning, and OPEN's _seat right
    behind it neither raises the false "leftover" (DF-OPEN VOID on the likelier branch) nor sends its warp off FieldHUD (the engine
    refuses it, and a wait=False send never says so). An escape queued but never run is re-rolled (fix round 2: LEFT_FLEE_TRIES of
    them) before the fight; the fight path's scene-gone stop waits for the field HUD too; a field HUD that never comes is noted, never
    raised, and then the guest is not waited for. _seat: a battle that ends inside SEAT_FIELD_S is no leftover; one that never ends,
    or a host never back on its field HUD, raises with its cause."""
    out = _duo_child(_LEFT_STANDIN + r'''
# the likelier branch: the roll lands, four frames of run-off and BattleResult, then the field
d, fled = end(Host([BATT] * 3 + [GONE] * 4 + [FLD] * 3, hold=2, escape_at=3))
du._seat(d, du.AWAY)                                     # OPEN's first statement, straight behind LEFT
fled["open_sent"] = d.host.sent
fled["open_notes"] = d.notes
_, stuck = end(Host([BATT] * 20 + [GONE] * 3 + [FLD] * 3, hold=19, fight_at=20))
_, never = end(Host([BATT] * 3 + [GONE] * 2, hold=2, escape_at=3))
OUT = {"fled": fled, "stuck": stuck, "never": never,
       "seat_hud": seat(Host([GONE] * 4 + [FLD] * 3)), "seat_grace": seat(Host([BATT] * 3 + [FLD] * 3)),
       "seat_leftover": seat(Host([BATT])), "seat_no_hud": seat(Host([GONE])),
       "consts": [du.LEFT_ESCAPE_S, du.LEFT_FIELD_S, du.SEAT_FIELD_S]}
''')
    field = [False, "FieldHUD", True]
    warp = [["warp 30602 -1 -1", "FieldHUD"]]
    fled = out["fled"]
    assert fled["last"] == field and fled["calls"] == ["flee"] and fled["notes"] == [], fled
    assert fled["open_sent"] == warp and fled["open_notes"] == [], fled          # OPEN seats: no false leftover, no refused warp
    stuck = out["stuck"]
    assert stuck["last"] == field and stuck["calls"] == ["flee"] * 4 + ["fight", "leave"], stuck
    assert len(stuck["notes"]) == 1 and stuck["notes"][0].startswith("LEFT: no escape ended it in 4 attempt(s) ("), stuck
    assert "queued, but the battle never ended in 45 s" in stuck["notes"][0], stuck
    assert stuck["notes"][0].endswith(") -- fighting it out, the last resort"), stuck
    never = out["never"]
    assert never["last"] == [False, "BattleResult", False] and never["calls"] == ["flee"] and never["guest_k"] == 0, never
    assert len(never["notes"]) == 1 and never["notes"][0].startswith("LEFT: the host never came back to its field HUD"), never
    assert out["seat_hud"] == {"err": None, "sent": warp, "notes": []}, out["seat_hud"]
    assert out["seat_grace"] == {"err": None, "sent": warp, "notes": []}, out["seat_grace"]
    lo = out["seat_leftover"]
    assert lo["sent"] == [] and lo["err"].startswith("a battle is still up on the host (a prior leg's leftover)"), lo
    nh = out["seat_no_hud"]
    assert nh["sent"] == [] and nh["err"].startswith("the host is on 'BattleResult', not FieldHUD, after 10 s"), nh
    assert out["consts"] == [45.0, 45.0, 10.0], out


def test_left_escapes_before_it_ever_fights_and_rerolls_only_while_the_party_can_take_it():
    """[s164] Fix round 2, ESCAPE FIRST, THE FIGHT LAST (refuter 1's correction, cluster 7): scene_info.no_gameover is false, so a wipe
    in LEFT's fallback fight Game-Overs BOTH games -- and the first run's one lost 60 s bumper roll had cost 112 of the Lv1 party's 355
    HP (Dagger at 7). On the stand-in host: each attempt takes Flee at a host prompt first (coop_battle_flee_defeat's H1 shape:
    Zidane's skill queues the SysEscape outright, no roll), a slot without Flee Defends while the prompts come round, and no prompt or
    none that took Flee falls to the bumper roll; a lost roll is re-rolled -- up to LEFT_FLEE_TRIES attempts -- only while the living
    members' HP is LEFT_REROLL_PCT of every player's max (left_may_reroll, left_party_hp: the living members' HP against every
    player's max -- a dead member's HP never counts but its max does; the enemy never counts; an unread roster re-rolls); the fight
    comes only after, with its reason noted. [s164] Fix round 3 (LEFT-FIRST-PROMPT): wait_battle returns before the intro and the
    s114 start hold, so an attempt's FIRST prompt wait is LEFT_FIRST_TURN_S (H1 waits 60 s) and only the later ones LEFT_TURN_S --
    20 s from the send fell to the dice hold whenever a long start hold met a slow ATB fill."""
    out = _duo_child(_LEFT_STANDIN + r'''
SC = lambda u: [u] * 3 + [GONE] * 4 + [FLD] * 3          # three battle reads (held at the third), the run-off, the field
H = {"skill": Host(SC(BATT), hold=2, escape_at=3, fight_at=3, turns=[2, 0]),
     "noflee": Host(SC(BATT), hold=2, escape_at=3, fight_at=3, turns=[2, 3], flee_slots=()),
     "reroll": Host(SC(BATT_OK), hold=2, escape_at=3, fight_at=3, fled=[False, True]),
     "lost": Host(SC(BATT_OK), hold=2, fight_at=3, fled=False),
     "worn": Host(SC(BATT_LOW), hold=2, fight_at=3, fled=False)}
R = {k: end(h)[1] for k, h in H.items()}
dead = {"battle": {"units": [{"player": True, "hp": 50, "hp_max": 100, "alive": False}, {"player": True, "hp": 30, "hp_max": 100, "alive": True}]}}
OUT = dict(R, waits={k: h.waits for k, h in H.items()},
       hp=[du.left_party_hp(BATT_OK), du.left_party_hp(BATT_LOW), du.left_party_hp(dead), du.left_party_hp(BATT),
           du.left_party_hp({"battle": {"units": [{"player": False, "hp": 33, "hp_max": 33}]}})],
       rule=[du.left_may_reroll(BATT_OK), du.left_may_reroll(BATT_LOW), du.left_may_reroll(BATT),
             du.left_may_reroll(party((100, 200))), du.left_may_reroll(party((99, 200))),
             du.left_may_reroll(party((60, 100), (0, 100)))],    # 60 of 200: 60% of the living max, but a dead max still counts
       consts=[du.LEFT_FLEE_TRIES, du.LEFT_PROMPTS, du.LEFT_TURN_S, du.LEFT_ROLL_S, du.LEFT_REROLL_PCT, du.LEFT_FIGHT_S,
               du.LEFT_FIRST_TURN_S])
''')
    field = [False, "FieldHUD", True]
    skill = out["skill"]                                 # the prompted slot 2 has no Flee: it Defends, then Zidane's Flee lands
    assert skill["calls"] == ["Flee 2", "Defend 2", "Flee 0"] and skill["notes"] == [] and skill["last"] == field, skill
    noflee = out["noflee"]                               # no prompted slot has Flee: the bumper roll, still no fight
    assert noflee["calls"] == ["Flee 2", "Defend 2", "Flee 3", "Defend 3", "flee"] and noflee["notes"] == [], noflee
    reroll = out["reroll"]                               # a lost roll re-rolled (the party holds 243 of 355): it lands, no fight
    assert reroll["calls"] == ["flee", "flee"] and reroll["notes"] == [] and reroll["last"] == field, reroll
    lost = out["lost"]                                   # every roll lost on a healthy party: four attempts, THEN the fight
    assert lost["calls"] == ["flee"] * 4 + ["fight", "leave"] and lost["last"] == field, lost
    assert len(lost["notes"]) == 1 and lost["notes"][0].startswith("LEFT: no escape ended it in 4 attempt(s) (no prompt ("), lost
    assert "bumper roll lost" in lost["notes"][0] and lost["notes"][0].endswith("-- fighting it out, the last resort"), lost
    worn = out["worn"]                                   # under half its HP after one lost roll: no re-roll, the fight now
    assert worn["calls"] == ["flee", "fight", "leave"] and worn["last"] == field, worn
    assert len(worn["notes"]) == 1, worn
    assert worn["notes"][0].startswith("LEFT: the party is down to 152 of 355 HP after 1 attempt(s): no re-roll ("), worn
    assert out["hp"] == [[243, 355], [152, 355], [30, 200], [None, None], [None, None]], out["hp"]
    assert out["rule"] == [True, False, True, True, False, False], out["rule"]
    assert out["consts"] == [4, 4, 20.0, 60.0, 50, 120.0, 45.0], out["consts"]
    w = out["waits"]                                     # each attempt's first prompt wait covers the intro and the start hold
    assert w["skill"] == [45.0, 20.0] and w["noflee"] == [45.0, 20.0, 20.0], w
    assert w["reroll"] == [45.0] * 2 and w["lost"] == [45.0] * 4 and w["worn"] == [45.0], w


def test_left_returns_only_once_the_guest_is_back_from_its_diorama():
    """[s164] Fix round 2, THE WARM RETURN (refuter 1 #4, refuter 2 #5): _end_left_battle used to wait for the HOST alone, and OPEN's
    _seat warps the host off HOME at once -- a guest still in its diorama Leave defers that follow (DF-OPEN VOID). It now also waits
    LEFT_GUEST_S for the GUEST back on the host's field with control (guest_back_on), noted on a timeout, never raised. Control alone is
    no return: a booted diorama publishes player.control true on BattleHUD with field.id still its boot field (the first duo run's
    guest, BattleMapDebug on 30602), and a field HUD with the diorama still booted, or without control, is not back either. Nor is a
    guest with no diorama booted, control and the right field but off its field HUD (BattleResult): the FieldHUD term is pinned."""
    out = _duo_child(_LEFT_STANDIN + r'''
SC = lambda: Host([BATT] * 3 + [GONE] * 4 + [FLD] * 3, hold=2, escape_at=3, fight_at=3)
d, late = end(SC(), [DIO] * 30 + [HOME_G])               # one second of diorama, then home
du._seat(d, du.AWAY)
late["open_sent"] = d.host.sent
_, never = end(SC(), [DIO])
_, half = end(SC(), [(True, "FieldHUD", True)] * 5 + [(False, "FieldHUD", False)] * 5 + [HOME_G])
dio = {"ui_state": "BattleHUD", "scene": "BattleMapDebug", "field": {"id": 30602}, "player": {"control": True},
       "netsync": {"diorama": {"booted": True, "boot": "warm", "returns": 0}}}
home = {"ui_state": "FieldHUD", "field": {"id": 250}, "player": {"control": True}, "netsync": {"diorama": {"booted": False, "returns": 1}}}
OUT = {"late": late, "never": never, "half": half,
       "back": [du.guest_back_on(home, 250), du.guest_back_on(dio, 30602), du.guest_back_on(dict(dio, ui_state="FieldHUD"), 30602),
                du.guest_back_on(dict(home, player={"control": False}), 250), du.guest_back_on(home, 30602),
                du.guest_back_on({k: v for k, v in home.items() if k != "netsync"}, 250), du.guest_back_on({}, 250),
                du.guest_back_on(dict(home, ui_state="BattleResult"), 250)],
       "consts": [du.LEFT_GUEST_S]}
''')
    field = [False, "FieldHUD", True]
    late = out["late"]
    assert late["calls"] == ["flee"] and late["notes"] == [] and late["last"] == field, late
    assert late["guest_k"] == 31, late                   # 30 diorama reads, then the first home read: it returned right there
    assert late["open_sent"] == [["warp 30602 -1 -1", "FieldHUD"]], late
    never = out["never"]
    assert never["calls"] == ["flee"] and never["last"] == field and len(never["notes"]) == 1, never
    assert never["notes"][0].startswith("LEFT: the guest was not back on 250 with control in 45 s after the host's return"), never
    assert "(diorama booted True, ui 'BattleHUD', field 250) -- OPEN seats from there" in never["notes"][0], never
    assert out["half"]["guest_k"] == 11 and out["half"]["notes"] == [], out["half"]
    assert out["back"] == [True, False, False, False, False, True, False, False], out["back"]
    assert out["consts"] == [45.0], out


def test_dl_left_texts_say_exactly_what_the_judge_judges():
    """[s164] Fix round 2 (the completeness critic): DL-LEFT's claim, its judge's docstring, the design row and the judge test's docstring
    still said "VOID only when the pre-send sample did not read intent.active" after review round 2 added the race VOID, and the claim
    and the row put the host's Left end AT the battle's swirl, which the judge never compares. Each text now names both VOIDs, the red
    and the judged clauses, and none claims the swirl timing. The judge itself is unchanged: a Left end stamped after the swirl stays
    green (no unproven end_t <= swirl_t clause), the race and the setup miss VOID, an intent still active red."""
    out = _duo_child(r'''
lf = left_ev()
PT = lf["pre"]["now_ms"]
OUT = {"claim": du.CLAIMS["DL-LEFT"], "jdoc": " ".join(du.judge_dl_left.__doc__.split()),
       "left_after_swirl": du.judge_dl_left(dict(lf, h=block(intent__nonce=7, intent__active=False, intent__last_end="left",
                                                              intent__end_t=lf["swirl_t"] + 500)))[0],
       "race": du.judge_dl_left(dict(lf, h=block(intent__nonce=7, intent__active=False, intent__last_end="stands", intent__end_t=PT + 200),
                                     swirl_t=PT + 300, hl=[]))[0],
       "setup_miss": du.judge_dl_left(dict(lf, pre=dict(lf["pre"], active=False)))[0],
       "active": du.judge_dl_left(dict(lf, h=block(intent__nonce=7, intent__active=True, intent__last_end="stands", intent__end_t=-1)))[0]}
''')
    claim, jdoc = out["claim"], out["jdoc"]
    duo = (REPO / "studies" / "field-coop" / "SWAP-TIMING-S164.md").read_text(encoding="utf-8").split("### Duo:", 1)[1]
    row = next(ln for ln in duo.splitlines() if ln.startswith("| DL-LEFT |"))
    tdoc = " ".join(test_the_other_duo_judges_can_go_red_on_each_part.__doc__.split())
    for text in (claim, jdoc, row, tdoc):
        assert "VOID only" not in text, text
    for text in (claim, row):
        assert "battle's swirl" not in text, text        # the old "at its battle's swirl" / "at the battle's swirl"
        assert "(the race)" in text and "no later than 300 ms past the battle start" in text, text
    assert "(else VOID)" in claim and "an intent still active once the battle came up is red" in claim, claim
    assert "'ended ... I left it' line for that nonce and intent.last_end left" in claim, claim
    assert "else VOID (a setup miss, P8)" in row and "`intent.last_end` `left`" in row and "is not compared" in row, row
    assert "VOID when the pre-send sample did not read intent.active for nonce n" in jdoc and "THE RACE" in jdoc, jdoc
    assert "is not compared (no end_t <= swirl_t clause" in jdoc, jdoc
    # [s164] Fix round 3 (R2-4): the judged clauses checked per text -- the jdoc words them its own way ("THE RACE", DL_LEFT_MS)
    assert "battle's swirl" not in jdoc and "battle's swirl" not in tdoc, (jdoc, tdoc)
    assert "'ended ... I left it' line for n" in tdoc and "intent.last_end left" in tdoc and "seen.nonce n" in tdoc, tdoc
    assert "no later than 300 ms past the battle start" in tdoc and "intent.end_t on a Left end when that sample is unread" in tdoc, tdoc
    assert '"ended ... I left it" line for n' in jdoc and 'intent.last_end "left"' in jdoc and "seen.nonce n" in jdoc, jdoc
    assert "no later than DL_LEFT_MS past the battle start" in jdoc and "falling back to intent.end_t on a Left end" in jdoc, jdoc
    assert [out["left_after_swirl"], out["race"], out["setup_miss"], out["active"]] == ["green", "void", "void", "red"], out


def test_the_design_doc_carries_fix_round_2():
    """[s164] Fix round 2's doc half (SWAP-TIMING-S164.md, the Duo bench): the MENU leg's exit is the bench's harness `warp`
    (SetNextMap from the debug-warp site), never a MAPJUMP; the LEFT leg escapes first and waits for both games; DF-FLASH notes that
    its join clause was rev 2's grace-INFER role (V6 moved it to DF-GRACE) and that its detail names REST-OLD; the first duo run's five
    side observations are listed for the owner, one line each."""
    duo = (REPO / "studies" / "field-coop" / "SWAP-TIMING-S164.md").read_text(encoding="utf-8").split("### Duo:", 1)[1]
    duo = duo.split("\n---\n", 1)[0]
    rows = {ln.split("|")[1].strip(): ln for ln in duo.splitlines() if ln.startswith("| ")}
    menu, left, flash = rows["MENU"], rows["LEFT"], rows["DF-FLASH"]
    assert "MAPJUMP and closes" not in menu and "harness `warp`" in menu and "`SetNextMap`" in menu, menu
    assert "Zidane's Flee" in left and "last resort" in left and "up to 4 attempts" in left, left
    assert "the guest back from its diorama" in left and "Then it flees" not in left, left
    assert "grace-INFER" in flash and "moved to DF-GRACE" in flash and "REST-OLD" in flash, flash
    items = [ln for ln in duo.split("**Open items from the first duo run", 1)[1].splitlines()[1:] if ln.startswith("- ")]
    assert len(items) == 5, items
    for i, word in enumerate(("7.9 s wordless", "bounce reload", "Garnet ghost", "239 ms", "DC-B/DF-PACE")):
        assert word in items[i], (word, items[i])


def test_the_design_doc_carries_fix_round_3():
    """[s164] Fix round 3's doc half (SWAP-TIMING-S164.md): the DF-GRACE row states its precondition (a follow whose copy could still
    exit: the record followed, fade.last.field 351, last.own_t unset or >= last.follow_t, the temporal test only), names the reload's
    idle load-black and cross-references DC-WON; DF-FLASH takes that reach; DL-DEFER is the ring bracket with the seen-while-paused
    reach, no lower bound and the 3-frame VOID; DP-DEFER takes the reach; DC-WON names the post-bounce follow; the copy-ahead 359 bounce
    item is UPDATED with the traced mechanism, not closed (still five items, the noticeability still referred to DC-B/DF-PACE); the
    rev-4 change table carries both fixes. [s164] Fix round 3 review: DL-DEFER reds a record not seen while paused (P8, never
    UNREACHED) and a guest that never lands on AWAY, places a follow inside the bracket by the ring's frame counter (at most 2 frames:
    the old "No lower bound" is gone), names its cap's frame and VOIDs a wide bracket only where the close's place decides; DP-DEFER
    names the term DL-DEFER reds without; the Probabilistic list drops DL-DEFER; DF-GRACE's stale VOID yields to a judged red."""
    doc = (REPO / "studies" / "field-coop" / "SWAP-TIMING-S164.md").read_text(encoding="utf-8")
    duo = doc.split("### Duo:", 1)[1].split("\n---\n", 1)[0]
    rows = {ln.split("|")[1].strip(): ln for ln in duo.splitlines() if ln.startswith("| ")}
    grace, flash, defer, pdefer = rows["DF-GRACE"], rows["DF-FLASH"], rows["DL-DEFER"], rows["DP-DEFER"]
    assert "`last.own_t` unset or >= `last.follow_t`" in grace and "`fade.last.field` is 351" in grace, grace
    assert "never `last.own_verdict` or `last.bounces`" in grace and "idle load-black" in grace, grace
    assert "DC-WON" in grace and "(s158 shape, risk 8)" in grace and "listed apart, never judged" in grace, grace
    assert "DF-GRACE's precondition admits" in flash and "grace-INFER" in flash and "REST-OLD" in flash, flash
    assert defer.split("|")[2].strip().startswith("The record must be seen while paused"), defer
    assert "`Session.states_since`" in defer and "No lower bound" not in defer and "3 frames + 1 ms" in defer, defer
    assert "first sample with its Pause closed" not in defer and "-16 / +1 ms" in defer, defer
    assert 'else red "not reached"' in defer and "never UNREACHED" in defer and "never lands on AWAY is red" in defer, defer
    assert "at most 2 frames on the ring's frame counter" in defer and "never the 1/30 s default" in defer, defer
    assert "the verdict depends on where the close falls" in defer and "the bracket has no close" in defer, defer
    assert "REACHED only when the record was seen while paused (the term DL-DEFER reds without" in pdefer, pdefer
    assert "unless a judged run is red" in grace, grace
    prob = next(ln for ln in doc.splitlines() if ln.startswith("- **Probabilistic duo rows**"))
    assert "DL-DEFER" not in prob and "DP-MARK and DP-DEFER; from fix round 3, DP-DEFER needs the record seen while paused" in prob, prob
    won = next(ln for ln in duo.splitlines() if ln.startswith("- **DC-WON"))
    assert "an own jump that bounced before the follow started" in won and "never `own`" in won, won
    items = [ln for ln in duo.split("**Open items from the first duo run", 1)[1].splitlines()[1:] if ln.startswith("- ")]
    assert len(items) == 5 and "untriaged" not in items[4], items
    assert "idle load-black" in items[4] and "DC-B/DF-PACE" in items[4] and "still open" in items[4], items[4]
    changed = doc.split("## What changed from rev 3", 1)[1].split("\n## ", 1)[0]
    assert "| DF-GRACE, DF-FLASH | Fix round 3" in changed and "| DL-DEFER, DP-DEFER | Fix round 3" in changed, changed[-1500:]


def test_the_duo_run_has_the_registered_shape():
    """The run's shape (source): DK-CLOCK before any leg; the `stamps` lever on BOTH games; the legs in order with LEVERS last (its
    `reset`); DA-ARRIVE judged after DESK (its DESK watch) and DA-LANE / DP-PARTY after the legs; CAL's sub-legs and levers as
    registered (the word's fade lever on CAL2 / CAL3 only); six DESK runs (each D, act and REST-OLD), REST-OLD's `fade old` before text
    139 closes, the `own` words on REST-OLD only; the orphan lever before the CAT pick; the pin lever on MARK and the short MENU run only;
    an unregistered ARRIVE_ID refused with its deploy command (VOID, via _lost). [s164] THE ARRIVAL GUARD: DA-GUARD judged after
    DA-LANE; DA-ARRIVE with
    the run's measured frame; the `arrive` word's `swap arrive old` before the ARRIVE act run only and `act` after; the `life` scope
    (the ARRIVE runs keep `life act`); LVD-ROLE's two new sends."""
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
       "arrive_refused": "deploy_command()" in src["_leg_cal"] and "not registered on both roots" in src["_leg_cal"]
       and '_lost(led, ctx, ("DA-ARRIVE",)' in src["_leg_cal"] and '(R, f"not reached: ARRIVE_ID' not in src["_leg_cal"],
       "reset": "cb.release(host)" in src["_leg_levers"],
       "finals": "predicted_now(cal, ctx.void, ctx.unreached, ctx.legs)" in src["run_duo"] and "judge_cal(cal, led.failed()" in src["run_duo"],
       "guard_row": r.index("DA-LANE") < r.index('"DA-GUARD", judge_da_guard(ctx.lane, life_word=ctx.cal == "life"') < r.index("DP-PARTY"),
       "arrive_fms": "judge_da_arrive(ctx.arrivals, ctx.clock_ok, ctx.clock_why, ctx.fms)" in r,
       "arrive_lever": '_lever(guest, ctx, "arrive", arrive_word, word_lever=arrive_word == "old")' in src["_leg_cal"]
       and src["_leg_cal"].index("cal_arrive(name, ctx.cal)") < src["_leg_cal"].index("_transition(d,")
       and '_ns(guest, "swap", "arrive", "act")' in src["_leg_cal"],
       "life_scope": "cal_life(name) != life_now" in src["_leg_cal"] and src["_leg_cal"].index("cal_life(name)") < src["_leg_cal"].index("_transition(d,"),
       "gate_mark": 'ctx.marks["DA-ARRIVE"] = {"gate": ctx.arrivals[-1]}' in src["_leg_cal"],
       "lvd": '"swap", "arrive", "old"' in src["_leg_levers"] and '"swap", "arrivebench", 0' in src["_leg_levers"],
       "cal_arrive": [du.cal_arrive(n, w) for n, w in (("ARRIVE", "arrive"), ("ARRIVE-OLD", "arrive"), ("CAL2", "arrive"), ("ARRIVE", None),
                                                       ("ARRIVE", "life"))],
       "cal_life": [du.cal_life(s[0]) for s in du.cal_subs("life")]}
''')
    assert out.pop("cal_arrive") == ["old", "act", None, None, None], out
    assert out.pop("cal_life") == ["old", "old", "old", "old", "act", "act"], out
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


# ------------------------------------------------------------------------------------------------ [s164 hardening] the instruments
def test_dp_defer_voids_an_unwritten_last_diff():
    """[s164 hardening] DP-DEFER's `last_diff` term: an UNWRITTEN diff (the -1 sentinel, or the key absent) on a landing by the intent
    with a young pre pin is VOID -- it used to read UNREACHED, which records GREEN: a vacuous pass. A written 0 (the latest frame
    carried no difference) stays UNREACHED, and a written >= 1 judges."""
    out = _duo_child(r'''
import copy
m = menu_ev()
def g(ev, **kw):
    ev = copy.deepcopy(ev)
    for path, v in kw.items():
        d = ev["g"]
        ks = path.split("__")
        for x in ks[:-1]:
            d = d[x]
        d[ks[-1]] = v
    return ev
absent = copy.deepcopy(m)
absent["g"]["pin"].pop("last_diff", None)
OUT = {"good": du.judge_dp_defer(m)[0] == G_, "unwritten": list(du.judge_dp_defer(g(m, pin__last_diff=-1))),
       "absent": du.judge_dp_defer(absent)[0] == V_, "zero": du.judge_dp_defer(g(m, pin__last_diff=0))[0] == U_,
       "late_unwritten": du.judge_dp_defer(g(m, pin__last_diff=-1, pin__last_use_quality="late"))[0] == U_, "V": V_}
''')
    assert out["good"] and out["absent"] and out["zero"] and out["late_unwritten"], out
    assert out["unwritten"][0] == out["V"] and "pin.last_diff unwritten (-1)" in out["unwritten"][1], out["unwritten"]


def test_df_flash_sees_a_flash_on_the_follows_first_frame():
    """[s164 hardening] DF-FLASH's first-frame blind spot: the cur window opens AT follow_t, so a flash already on the follow's first
    sampled frame (black 255 before Begin, 40 on the first frame, then rising) had nothing before it to dip against and read green.
    The guest's last pre-follow read (fade_cur_base: off the destination, <= FLASH_BASE_MS before follow_t, -1 is no read) now
    leads the series. desk_evidence carries it."""
    out = _duo_child(r'''
F0 = {"D": 1.0, "old": False, "fade": {"field": du.REST_FROM, "view_start": "black", "action": "join", "by": "own", "path": "fast"},
      "cur": [40, 90, 160, 255], "last": {"follow_t": 5000, "own_t": -1}}
gs = [S(t=4900, field=du.DESK_FIELD, sw={"fade.cur_now": 250}), S(t=4967, field=du.DESK_FIELD, sw={"fade.cur_now": 255}),
      S(t=5010, field=du.DESK_FIELD, sw={"fade.cur_now": 40}), S(t=5043, field=du.DESK_FIELD, sw={"fade.cur_now": 90})]
unread = gs[:1] + [S(t=4967, field=du.DESK_FIELD, sw={"fade.cur_now": -1})]
OUT = {"base": du.fade_cur_base(gs, 5000, du.REST_FROM), "too_old": du.fade_cur_base(gs, 5200, du.REST_FROM),
       "unread": du.fade_cur_base(unread, 5000, du.REST_FROM), "none": du.fade_cur_base(gs, None, du.REST_FROM),
       "flash": list(du.judge_df_flash([dict(F0, cur_base=255)])), "blind": du.judge_df_flash([F0])[0] == G_,
       "steady": du.judge_df_flash([dict(F0, cur=[255, 255, 255], cur_base=250)])[0] == G_, "R": R_,
       "wired": "cur_base" in du.desk_evidence(1.0, False, [], [], [], [])["fade"]}
''')
    assert out["base"] == 255 and out["too_old"] is None and out["unread"] is None and out["none"] is None, out
    assert out["flash"][0] == out["R"] and "dip True (base 255)" in out["flash"][1], out["flash"]
    assert out["blind"] and out["steady"] and out["wired"], out


def test_the_watch_backfills_an_awaited_hooks_hole_from_the_ring():
    """[s164 hardening] AN AWAITED HOOK STARVES THE WATCH: a hook's synchronous call reads frames into the session's ring while the
    pump is held, and the next `.state` lands frames later. _Watch.pump backfills from Session.states_since, so a "first sample
    off X" edge (close_t of text 139 here) is the ring's, a frame after the last on-sample -- not the read after the ack."""
    out = _duo_child(r'''
class St:
    def __init__(self, raw):
        self.raw, self.frame = raw, raw["frame"]
class G:
    def __init__(self, xs):
        self.xs, self.i, self.ring = xs, 0, []
    @property
    def state(self):
        x = self.xs[self.i]
        self.ring.append(x)
        return St(x)
    def held(self, n):                                   # an awaited call's own polls, while the pump waits on it
        for _ in range(n):
            self.i += 1
            self.ring.append(self.xs[self.i])
    def states_since(self, f):
        return [x for x in self.ring if x["frame"] > f]
key = du.DESK_LAST
gx = [S(t=33 * k, frame=k, field=du.REST_FROM, wins=((key[0], key[1], "locked"),) if k < 5 else ()) for k in range(10)]
hx = [S(t=33 * k, frame=k, field=du.REST_FROM) for k in range(10)]
class D:
    pass
d = D()
d.host, d.guest = G(hx), G(gx)
w = du._Watch(d)
w.pump()
d.guest.held(7)                                          # the hook's press: frames 1..7 read inside its ack wait
w.pump()
ring_less = type("NoRing", (), {})()
OUT = {"frames": [x["frame"] for x in w.s["guest"]], "close": du.close_t(w.s["guest"], key),
       "between": [x["frame"] for x in du.ring_backfill(d.guest, 0, 7)], "backwards": du.ring_backfill(d.guest, 7, 3),
       "no_ring": du.ring_backfill(ring_less, 0, 7)}
''')
    assert out["frames"] == list(range(8)), out["frames"]
    assert out["close"] == 165, out                       # frame 5 (33 ms frames), never frame 7's 231
    assert out["between"] == [1, 2, 3, 4, 5, 6] and out["backwards"] == [] and out["no_ring"] == [], out


def test_every_transitions_fade_is_kept_in_duo_json():
    """[s164 hardening] The final s164 duo's 359 follows committed short of black on the 0.9 s fallback (darkest 237-247 against the
    248 floor) and none of their samples survived the run. tr_evidence keeps each transition's fade (fade_record), fade_report
    reads it -- the verdict, the cur window's peak, the darkest channel the due line names, `short` -- and _keep_fades writes it
    (with the DF rows' evidence) through Duo.keep, noting the short count; a stale fade.last (no follow) keeps no verdict."""
    out = _duo_child(r'''
due = ("[NetSync] follow fade: field 359 due after 900 ms / 27 ticks -- the 0.9 s fallback: the fade never read black (heading, "
       "darkest channel 241)")
short = {"lane": "DESK", "sub": "D1.0", "from": 30801, "dest": 359,
         "fade_rec": {"last": {"field": 359, "path": "fast", "action": "join", "by": "fallback", "view_start": "heading", "ms": 900,
                               "ticks": 27}, "follow_t": 100, "due_t": 1000, "commit_t": 1000, "cur": [200, 230, 241],
                      "cur_base": 190, "lines": [due]}}
fine = {"lane": "CAL", "sub": "CAL2", "from": 30801, "dest": 30602,
        "fade_rec": {"last": {"field": 30602, "by": "black", "action": "fade"}, "follow_t": 10, "cur": [0, 255], "lines": []}}
stale = {"lane": "OWN", "sub": "OWN", "from": 351, "dest": 450, "fade_rec": {"last": {"field": 359, "by": "fallback"}, "follow_t": None}}
rows = du.fade_report([short, fine, stale])
kept, notes = {}, []
class D:
    def keep(self, k, v):
        kept[k] = v
    def note(self, m):
        notes.append(m)
class C:
    all_trs = [short, fine, stale]
    marks = {"DF-FLASH": {"fades": [1]}, "DA-LINES": {"runs": []}}
du._keep_fades(D(), C())
gs = [S(t=0, field=30801, sw={"fade.cur_now": 0, "last.follow_t": 0})]
OUT = {"rows": [[r["short"], r["darkest"], r["cur_peak"], r["stale"], r["by"]] for r in rows], "kept": sorted(kept),
       "marks": sorted(kept["fade_marks"]), "n": len(kept["fades"]), "note": notes,
       "tr_has": "fade_rec" in du.tr_evidence("CAL", "CAL2", 30602, 30801, gs, gs),
       "called": "_keep_fades(d, ctx)" in __import__("inspect").getsource(du.run_duo)}
''')
    assert out["rows"] == [[True, 241, 241, False, "fallback"], [False, None, 255, False, "black"], [False, None, None, True, None]], out
    assert out["kept"] == ["fade_marks", "fades"] and out["marks"] == ["DF-FLASH"] and out["n"] == 3, out
    assert len(out["note"]) == 1 and "1 of 2 follows committed on the 0.9 s fallback short of black" in out["note"][0], out["note"]
    assert "darkest 241" in out["note"][0] and out["tr_has"] and out["called"], out
