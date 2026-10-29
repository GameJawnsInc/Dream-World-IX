"""[ff9mapkit netsync s163] THE SPEED MIRROR BENCHES' REPO HALF -- studies/test-harness/scenarios/coop_speed_mirror.py (solo, the
selftest role) and coop_speed_mirror_duo.py (two games: GUEST-TRAVERSAL-TWO-PC.md Finding 10's "Dagger Tries" with the host at 3x).

s163 mirrors a 3x host's scene on a following guest through a LATCH (studies/field-coop/SPEED-MIRROR.md rev 3): START on my control off
under the host's scene and setting > 1, END on my control back for StepInMs, a landing, the scene left or the lever -- never on the
host's control; the factor APPLIED only while my control is off. These tests pin, offline, with fixtures in the ENGINE's log and state
shapes (the lines built by battlewire's twins of NetSyncSpeed's own):

  * every solo judge can go red on each of its parts (K1 the proof line with no literal row counts, K2 the rest state, S-HOST the bench
    host's codec read-back, S-ON the ON line and the applied factor, S-LATCH the latch, S-BACK the withheld factor and the debounce
    measured from the last control-off sample, S-BATTLE the diorama's factor and the scene end, S-OFF the lever end and its release,
    S-F1 the guest's own F1, S-STALE the null-state cache step (rev 1's "null = setting 1" is red), S-WORLD the field term alone);
  * the solo calibration: under the `speed off` lever's evidence EXACTLY S-ON, S-LATCH, S-BACK, S-BATTLE and S-OFF are red, each with
    its marker, and the lever-aware rows stay green; any other COOP_CALIBRATE word is refused, never mapped to the lever;
  * every duo judge (D1-D9) can go red on each part; under Finding 10's evidence (the guest's `speed off`, same DLL) EXACTLY D4-D8 are
    red with their markers and D0-D3 / D9 are not; the duo refuses an unknown COOP_CALIBRATE word AT LOAD (before duo.py boots);
  * the words both benches match are the engine's: battlewire's twins, the stand-in's harness lines, and the patch stack's literals.

Every scenario-touching test runs in a CHILD process (the scenario puts its own dir on sys.path -- never this process's).
"""
import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
SCEN = REPO / "studies" / "test-harness" / "scenarios"
PATCHES = REPO / "memoria-patches"


def _run_child(code: str, env_cal: str | None = None, duo: bool | None = None, solo: bool = True) -> subprocess.CompletedProcess:
    """``duo``: import the duo bench too (default: when the code names ``du.``); ``solo``: import the solo bench (default yes) --
    BOTH read COOP_CALIBRATE at load and refuse an unknown word there, so a refusal test imports only the bench it judges."""
    duo = ("du." in code) if duo is None else duo
    full = ("import json, os, sys\nsys.path.insert(0, %r)\nsys.path.insert(0, %r)\n" % (str(SCEN), str(REPO / "tools"))
            + ("import coop_speed_mirror as so\n" if solo else "") + ("import coop_speed_mirror_duo as du\n" if duo else "")
            + "from harness import battlewire as BW\nfrom harness import fakegame as FG\n" + code
            + "\nprint('@@' + json.dumps(OUT))\n")
    env = {k: v for k, v in os.environ.items() if k != "COOP_CALIBRATE"}
    if env_cal is not None:
        env["COOP_CALIBRATE"] = env_cal
    return subprocess.run([sys.executable, "-X", "utf8", "-c", full], capture_output=True, text=True, cwd=str(SCEN), timeout=120,
                          env=env)


def _child(code: str, env_cal: str | None = None) -> dict:
    r = _run_child(code, env_cal)
    assert r.returncode == 0, r.stderr[-3000:]
    line = next(ln for ln in r.stdout.splitlines() if ln.startswith("@@"))
    return json.loads(line[2:])


# ------------------------------------------------------------------------------------------------ the solo fixtures
_SOLO = r'''
P = "29.10.2026 21:10:00 |M| "
L = lambda text: P + text
ENDS = list(FG.NETSYNC_SPEED_END_WHY)
def smp(t, ctl=False, mirror=False, applied=False, fac=1, ff=None, raw=False, own=1, mode=None, fast=False, why=None, host=so.HOST,
        tps=30, src="bench", seen=True, stale=False, on=0, off=0, ew=None, last_end=None, scene="FieldMap", ui="FieldHUD",
        field=352, lever=None):
    ff = fac if ff is None else ff
    mode = applied if mode is None else mode
    return {"_t": t, "ui_state": ui, "scene": scene, "ff": ff, "field": {"id": field}, "player": {"control": ctl},
            "netsync": {"speed": {"host_setting": host, "host_tps": tps, "host_seen": seen, "host_stale": stale, "src": src,
                                  "own_factor": own, "mirror": mirror, "applied": applied, "factor_now": fac, "mode_wanted": mode,
                                  "fast_mode": fast, "raw": raw, "why_not": why, "edges_on": on, "edges_off": off,
                                  "last_end": last_end, "faults": 0, "last_fault": None,
                                  "end_why": dict({k: 0 for k in ENDS}, **(ew or {})), "lever": lever, "selftest": "ok"}}}
def edit(s, **kw):
    import copy
    s = copy.deepcopy(s)
    for k, v in kw.items():
        if k in ("ctl",):
            s["player"]["control"] = v
        elif k in ("ff", "scene", "ui_state"):
            s[k] = v
        else:
            s["netsync"]["speed"][k] = v
    return s
ON = L(BW.speed_log_on(352, 3, so.HOST, 30, 3, 30, 1, BW.SPEED_START_WHY_HOST))   # factor 3 = my G, never the bench host's 5
OFF_CTL = L(BW.speed_log_off(352, 1210, 1, BW.speed_end_words(BW.SPEED_END_CONTROL, 352)))
OFF_LEVER = L(BW.speed_log_off(352, 900, 1, BW.speed_end_words(BW.SPEED_END_LEVER, 352)))
OFF_SCENE = L(BW.speed_log_off(352, 700, 1, BW.speed_end_words(BW.SPEED_END_SCENE, 352, "SwirlScene")))
HOSTLINE = L(FG.SPEED_LOG_HOST.format(s=so.HOST, t=30))
WC, WL, WH, WS, WF = BW.SPEED_WHY_CONTROL, BW.SPEED_WHY_LEVER, BW.SPEED_WHY_HOST, BW.SPEED_WHY_STALE, BW.SPEED_WHY_FIELD
# S-ON: my control goes off at 0.02, the latch stands at 0.05, FAST MODE a publish later; the counters rise once
ON_S = ([smp(0.0, ctl=True, why=WC), smp(0.02, why=WC)]
        + [smp(0.05 + 0.02 * i, mirror=True, applied=True, fac=3, fast=i > 0, on=1) for i in range(8)])
LATCH = [smp(0.1 * i, mirror=True, applied=True, fac=3, fast=True, on=1) for i in range(6)]
# S-BACK: the pre-send sample at 0 (off), control back at 0.05 (the Tick a frame later: still applied), withheld at 0.07, the latch
# ends at 0.58 (StepInMs from the flip), by `control`
BACK = ([smp(0.0, mirror=True, applied=True, fac=3, on=1), smp(0.05, ctl=True, mirror=True, applied=True, fac=3, on=1)]
        + [smp(0.07 + 0.05 * i, ctl=True, mirror=True, on=1, why=None) for i in range(10)]
        + [smp(0.6 + 0.1 * i, ctl=True, on=1, off=1, ew={"control": 1}, last_end="control", why=WC) for i in range(5)])
B0 = so.counters(smp(0, on=1))
DIO = [smp(0.2 * i, scene="BattleMapDebug", ui="BattleHUD", on=2, off=2, ew={"control": 1, "scene": 1}, last_end="scene", why=WF)
       for i in range(5)]
'''


def test_k1_parses_the_proof_line_and_judges_no_literal():
    """K1: green on the OK line with step-in 500 and the verdict 'ok' -- whatever its row and mutant counts (never judged against
    literals); red on a step-in other than StepInMs, a FAIL line, a failing verdict, no line. The bench's regex IS the stand-in's."""
    out = _child(r'''
line = lambda r, m, s=500: "[NetSync] " + FG.PROOF_SPEED_MIRROR + f"OK ({r} rows, {m} mutants caught, step-in {s} ms)"
OUT = {"s163": so.judge_proof([line(114, 66)], "ok")[0], "other_counts": so.judge_proof([line(120, 70)], "ok")[0],
       "step_in": so.judge_proof([line(114, 66, 400)], "ok")[0],
       "fail_line": so.judge_proof([line(114, 66), "[NetSync] speed mirror selftest: FAIL (end.order_3)"], "ok")[0],
       "verdict": so.judge_proof([line(114, 66)], "fail: start.lever")[0], "none": so.judge_proof([], "ok")[0],
       "same_rx": so.PROOF_RX.pattern == FG.SPEED_PROOF_RE, "counts": [FG.FAKE_SPEED_SELFTEST_ROWS, FG.FAKE_SPEED_MUTANTS],
       "step_in_ms": [so.STEP_IN_MS, BW.SPEED_STEP_IN_MS, FG.STEPOUT_STEP_IN_MS]}
''')
    assert out.pop("s163") and out.pop("other_counts") and out.pop("same_rx"), out
    assert out.pop("counts") == [114, 66] and out.pop("step_in_ms") == [500, 500, 500]
    assert not any(out.values()), out


def test_k2_the_rest_state_can_go_red_on_each_part():
    """K2: the live engine's rest values on the selftest role with my control on (why_not 'I have control': the role is eligible);
    each part flipped alone is red, an absent block is red."""
    out = _child(_SOLO + r'''
rest = smp(0, ctl=True, host=1, tps=-1, src="none", seen=False, why=WC)
bad = {"lever": edit(rest, lever="off"), "mirror": edit(rest, mirror=True), "applied": edit(rest, applied=True),
       "src": edit(rest, src="bench"), "host": edit(rest, host_setting=3), "raw": edit(rest, raw=True), "own": edit(rest, own_factor=3),
       "factor": edit(rest, factor_now=3), "ff": edit(rest, ff=3), "ff_absent": edit(rest, ff=None), "faults": edit(rest, faults=1),
       "why": edit(rest, why_not=WH), "absent": {"ff": 1, "netsync": {}}}
OUT = {"good": so.judge_rest(rest)[0], **{k: so.judge_rest(v)[0] for k, v in bad.items()}}
''')
    assert out.pop("good"), out
    assert not any(out.values()), out


def test_s_host_reads_the_bench_host_back_and_never_mirrors_with_my_control_on():
    """S-HOST: the bench host's line once (setting HOST, T TPS), host_setting HOST, host_tps T, src 'bench', host_seen, not stale; with my
    control on under hostscene 1 never a mirror, factor 1, why_not 'I have control' -- the lever's words when calibrating (and only
    then). Each part alone is red."""
    out = _child(_SOLO + r'''
st = smp(0, ctl=True, why=WC)
rest = [smp(0.1 * i, ctl=True, why=WC) for i in range(6)]
lever = [edit(s, why_not=WL) for s in rest]
j = lambda st=st, lines=[HOSTLINE], rest=rest, cal=None: so.judge_bench_host(st, lines, rest, cal)[0]
OUT = {"good": j(), "cal": j(rest=lever, cal="off"),
       "no_line": j(lines=[]), "two_lines": j(lines=[HOSTLINE, HOSTLINE]), "line_setting_2": j(lines=[L(FG.SPEED_LOG_HOST.format(s=2, t=30))]),
       "host_2": j(st=edit(st, host_setting=2)), "tps_mismatch": j(st=edit(st, host_tps=60)), "src_wire": j(st=edit(st, src="wire")),
       "unseen": j(st=edit(st, host_seen=False)), "stale": j(st=edit(st, host_stale=True)),
       "a_mirror": j(rest=rest + [smp(0.7, ctl=True, mirror=True, why=None)]), "factor_3": j(rest=rest + [smp(0.7, ctl=True, fac=3, why=WC)]),
       "why_wrong": j(rest=[edit(s, why_not=WH) for s in rest]), "lever_plain": j(rest=lever), "control_cal": j(cal="off"),
       "too_few": j(rest=rest[:2])}
''')
    assert out.pop("good") and out.pop("cal"), out
    assert not any(out.values()), out


def test_s_on_is_green_only_on_the_applied_factor_and_can_go_red_on_each_part():
    """S-ON: one ON line on 352 (factor F = the line's G = the ini's G > 1, the host's HOST, TPS equal, my own factor 1, the host's
    scene), started within ON_S, then applied / factor_now F / ff F / raw false / own 1 / mode_wanted on every live control-off sample,
    FAST MODE a publish after, edges_on +1. Each part alone is red; so is an absent counter. (The review) the bench host is ABOVE G (5 vs
    3), so an engine that applies the HOST's setting (SelfTest's factor_host_rate mutant: 'factor 5 (... covers my 3 x 30 ...)', ff 5)
    is red -- at host 3 = G it read exactly as a correct one."""
    out = _child(_SOLO + r'''
j = lambda S=ON_S, lines=[ON], b0=so.counters(smp(0)), g=3: so.judge_on(S, lines, b0, g, 352)
ok, why, fac = j()
other = lambda **kw: [L(BW.speed_log_on(**dict(dict(fld=352, factor=3, host_setting=so.HOST, host_tps=30, g=3, my_tps=30, own=1,
                                                   why=BW.SPEED_START_WHY_HOST), **kw)))]
host_rate = [edit(s, factor_now=so.HOST, ff=so.HOST) if s["netsync"]["speed"]["mirror"] else s for s in ON_S]
late = [smp(0.0, ctl=True, why=WC), smp(0.02, why=WC), smp(2.5, mirror=True, applied=True, fac=3, on=1),
        smp(2.6, mirror=True, applied=True, fac=3, fast=True, on=1)]
live = lambda **kw: ON_S[:4] + [edit(ON_S[4], **kw)] + ON_S[5:]
OUT = {"good": ok, "fac": fac, "no_line": j(lines=[])[0], "two_lines": j(lines=[ON, ON])[0], "on_351": j(lines=other(fld=351))[0],
       "factor_2": j(lines=other(factor=2))[0], "factor_not_g": j(lines=other(g=2))[0], "ini_g_5": j(g=5)[0],
       "host_2": j(lines=other(host_setting=2))[0], "tps": j(lines=other(my_tps=60))[0], "own_3": j(lines=other(own=3))[0],
       "ate_why": j(lines=other(why=BW.SPEED_START_WHY_ATE))[0], "late": j(S=late)[0],
       "not_applied": j(S=live(applied=False))[0], "factor_now_1": j(S=live(factor_now=1))[0], "ff_1": j(S=live(ff=1))[0],
       "raw": j(S=live(raw=True))[0], "own_factor_3": j(S=live(own_factor=3))[0], "mode": j(S=live(mode_wanted=False))[0],
       "no_fast": j(S=[edit(s, fast_mode=False) for s in ON_S])[0], "edges_0": j(b0=so.counters(smp(0, on=1)))[0],
       "edges_absent": j(b0={"on": None})[0], "never": j(S=ON_S[:2])[0],
       "host_rate": j(S=host_rate, lines=other(factor=so.HOST))[0], "host_is_5": so.HOST == 5 and so.HOST != so.G_DEFAULT}
''')
    assert out.pop("good") and out.pop("fac") == 3 and out.pop("host_is_5"), out
    assert not any(out.values()), out


def test_s_latch_keeps_the_mirror_through_the_hosts_control_back():
    """S-LATCH: hostscene 0 with my control still off -- mirror, applied and the factor on every sample, no OFF line, edges_off +0.
    An end on the host's control (a mirror-false sample), an OFF line, an edges_off rise, my control on, no factor are each red."""
    out = _child(_SOLO + r'''
b = so.counters(smp(0, on=1))
j = lambda S=LATCH, lines=[], b=b, fac=3: so.judge_latch(S, lines, b, fac)[0]
OUT = {"good": j(), "ended": j(S=LATCH[:3] + [smp(0.4, on=1, off=1, ew={"host": 1})] + LATCH[3:]),
       "off_line": j(lines=[OFF_CTL]), "edges_off": j(S=LATCH[:-1] + [edit(LATCH[-1], edges_off=1)]),
       "control_on": j(S=LATCH + [smp(0.7, ctl=True, mirror=True, fac=3, on=1)]), "no_factor": j(fac=None),
       "withheld": j(S=[edit(s, applied=False) for s in LATCH]), "factor_1": j(S=[edit(s, factor_now=1, ff=1) for s in LATCH]),
       "too_few": j(S=LATCH[:2])}
''')
    assert out.pop("good"), out
    assert not any(out.values()), out


def test_s_back_withholds_at_once_and_ends_after_the_debounce():
    """S-BACK: the factor withheld within APPLY_BACK_S of control back and never again (free roam at my own speed), the latch still
    standing at the flip and ending DEBOUNCE_MIN_S-IN_BY_S after it (measured from the last control-off sample: a stall over
    LAND_GAP_MAX_S is red), by `control` with its OFF line. Each part alone is red."""
    out = _child(_SOLO + r'''
j = lambda S=BACK, lines=[OFF_CTL], b0=B0: so.judge_back(S, lines, b0, 352)[0]
shift = lambda S, dt: [dict(s, _t=s["_t"] + dt) if s["_t"] > 0 else s for s in S]
late_w = BACK[:2] + [edit(s, applied=True, factor_now=3, ff=3) if s["_t"] < 0.4 else s for s in BACK[2:]]
OUT = {"good": j(), "withheld_late": j(S=late_w),
       "reapplied": j(S=BACK[:8] + [edit(BACK[8], applied=True)] + BACK[9:]),
       "ff_3_after": j(S=BACK[:8] + [edit(BACK[8], ff=3)] + BACK[9:]),
       "ended_at_once": j(S=BACK[:2] + [edit(s, mirror=False) for s in BACK[2:]]),
       "ended_late": j(S=BACK[:12] + [edit(s, mirror=True) for s in BACK[12:]]),
       "stall": j(S=[BACK[0]] + shift(BACK[1:], 0.4)),
       "no_counter": j(S=BACK[:-5] + [edit(s, end_why={k: 0 for k in ENDS}) for s in BACK[-5:]]),
       "last_end_lever": j(S=BACK[:-5] + [edit(s, last_end="lever") for s in BACK[-5:]]),
       "off_by_lever": j(lines=[OFF_LEVER]), "two_off": j(lines=[OFF_CTL, OFF_CTL]), "no_off": j(lines=[]),
       "never_back": j(S=[edit(s, ctl=False) for s in BACK])}
''')
    assert out.pop("good"), out
    assert not any(out.values()), out


def test_s_battle_reads_factor_1_in_the_diorama_and_ends_by_the_scene():
    """S-BATTLE: raised before the boot; >= DIO_MIN diorama samples, each ff / factor_now 1 and no mirror; nothing off the field scene
    with the mirror or its factor applied; end_why.scene +1, last_end 'scene', its OFF line. Each part alone is red. (The run samples
    only from the diorama up -- cb.boot blocks until BattleMapDebug -- so a swirl sample reaches the judge in a fixture alone.)"""
    out = _child(_SOLO + r'''
b0 = so.counters(smp(0, on=2, off=1, ew={"control": 1}))
j = lambda raised=True, S=DIO, b0=b0, lines=[ON, OFF_SCENE]: so.judge_battle(raised, S, b0, lines, 352)[0]
OUT = {"good": j(), "not_raised": j(raised=False), "few": j(S=DIO[:2]), "ff_3": j(S=DIO[:2] + [edit(DIO[2], ff=3)] + DIO[3:]),
       "factor_3": j(S=DIO[:2] + [edit(DIO[2], factor_now=3)] + DIO[3:]),
       "mirror_in_battle": j(S=DIO[:2] + [edit(DIO[2], mirror=True)] + DIO[3:]),
       "swirl_applied": j(S=[smp(0.0, scene="SwirlScene", mirror=True, applied=True, fac=3, on=2)] + DIO),
       "scene_0": j(S=[edit(s, end_why={k: (1 if k == "control" else 0) for k in ENDS}) for s in DIO]),
       "landing": j(S=[edit(s, last_end="landing") for s in DIO]), "off_by_control": j(lines=[ON, OFF_CTL]), "no_off": j(lines=[ON])}
''')
    assert out.pop("good"), out
    assert not any(out.values()), out


def test_s_off_ends_by_the_lever_and_act_raises_it_again():
    """S-OFF: raised; the lever ends it within OFF_END_S; factor 1 and why_not the lever with my control still off; end_why.lever +1,
    last_end 'lever', its OFF line, the harness's CALIBRATION line; `act` raises it again with edges_on +1. Each part alone is red."""
    out = _child(_SOLO + r'''
b0 = so.counters(smp(0, on=3, off=2))
after = ([smp(0.02, mirror=True, applied=True, fac=3, on=3, off=2, lever="off")]
         + [smp(0.1 + 0.1 * i, on=3, off=3, ew={"lever": 1}, last_end="lever", why=WL, lever="off") for i in range(8)])
b_mid = so.counters(after[-1])
again = [smp(0.0, why=WL), smp(0.05, mirror=True, applied=True, fac=3, on=4, off=3, ew={"lever": 1})]
lines = [ON, L(FG.SPEED_LOG_OFF), OFF_LEVER, L(FG.SPEED_LOG_ACT), ON]
j = lambda raised=True, A=after, b0=b0, lines=lines, G=again, bm=b_mid: so.judge_off(raised, A, b0, lines, G, bm, 352)[0]
OUT = {"good": j(), "not_raised": j(raised=False), "late": j(A=[dict(s, _t=s["_t"] + 0.6) for s in after]),
       "ff_3": j(A=after[:3] + [edit(after[3], ff=3)] + after[4:]), "why_control": j(A=[edit(s, why_not=WC) for s in after]),
       "lever_0": j(A=[edit(s, end_why={k: 0 for k in ENDS}) for s in after]), "last_end": j(A=[edit(s, last_end="host") for s in after]),
       "off_by_host": j(lines=[ON, L(FG.SPEED_LOG_OFF), L(BW.speed_log_off(352, 900, 1, BW.speed_end_words(BW.SPEED_END_HOST, 352)))]),
       "no_cal_line": j(lines=[ON, OFF_LEVER]), "act_never": j(G=[smp(0.0, why=WL)]),
       "act_no_edge": j(G=[smp(0.05, mirror=True, applied=True, fac=3, on=3)]), "no_after": j(A=[])}
''')
    assert out.pop("good"), out
    assert not any(out.values()), out


def test_s_f1_is_the_guests_own_booster_with_no_mirror():
    """S-F1: host 1 with my control off never mirrors (factor 1, why_not 'the host's booster is off' -- the lever's words when
    calibrating); my own `speedmode 1` reads raw true, own_factor / factor_now / ff G, FAST MODE, still no mirror; `speedmode 0` back to
    raw false and 1. Each part alone is red."""
    out = _child(_SOLO + r'''
pre = [smp(0.1 * i, host=1, why=WH) for i in range(5)]
f1 = [smp(0.0, host=1, why=WH)] + [smp(0.05 + 0.1 * i, host=1, raw=True, own=3, fac=3, fast=i > 0, why=WH) for i in range(8)]
post = [smp(0.1 * i, host=1, why=WH) for i in range(5)]
cal = lambda S: [edit(s, why_not=WL) for s in S]
j = lambda P=pre, F=f1, Q=post, c=None, g=3: so.judge_f1(P, F, Q, c, g)[0]
OUT = {"good": j(), "cal": j(cal(pre), cal(f1), cal(post), "off"), "host_3": j(P=[edit(s, host_setting=3) for s in pre]),
       "why": j(P=[edit(s, why_not=WC) for s in pre]), "lever_plain": j(cal(pre), cal(f1), cal(post)),
       "pre_factor_3": j(P=pre[:2] + [edit(pre[2], ff=3)] + pre[3:]), "raw_never": j(F=[edit(s, raw=False) for s in f1]),
       "own_1": j(F=[edit(s, own_factor=1) if s["netsync"]["speed"]["raw"] else s for s in f1]),
       "ff_1": j(F=[edit(s, ff=1) if s["netsync"]["speed"]["raw"] else s for s in f1]), "no_fast": j(F=[edit(s, fast_mode=False) for s in f1]),
       "a_mirror": j(F=f1 + [smp(1.0, host=1, raw=True, own=3, fac=3, mirror=True)]), "post_raw": j(Q=[edit(s, raw=True) for s in post]),
       "g_5": j(g=5), "control_on": j(P=[edit(s, ctl=True) for s in pre])}
''')
    assert out.pop("good") and out.pop("cal"), out
    assert not any(out.values()), out


def test_s_stale_reads_a_null_state_as_no_news():
    """S-STALE: the bench lane with no bench host -- fresh: not stale, setting 1, src none, why_not 'the host's booster is off'; stale 1:
    host_stale with the cache unchanged (absent: setting 1, src none) and why_not 'the host's lane is stale' (StartRule's stale term
    before its host term); stale 0: fresh again. REV 1's shape (a null state read as setting 1, never stale) is red through host_stale
    and why_not; the lever's words pass only when calibrating. NOT a 'cache lost' red: the cache here is already the absent state, so a
    CacheRule that forgot on a null state but marked it stale reads the same values (the keep-on-null law is SelfTest's row
    cache.null_state_keeps_the_host)."""
    out = _child(_SOLO + r'''
F = lambda w=WH, **kw: [smp(0.1 * i, why=w, **dict(dict(host=1, tps=-1, src="none", seen=False), **kw)) for i in range(6)]
fresh, stale, back = F(), F(WS, stale=True), F()
cal = lambda S: [edit(s, why_not=WL) for s in S]
j = lambda a=fresh, b=stale, c=back, cal_=None: so.judge_stale(a, b, c, cal_)[0]
OUT = {"good": j(), "cal": j(cal(fresh), cal(stale), cal(back), "off"), "rev1": j(b=F()),
       "fresh_stale": j(a=F(stale=True)), "stale_why_host": j(b=F(WH, stale=True)),
       "setting_3": j(b=[edit(s, host_setting=3) for s in stale]), "back_stale": j(c=F(WS, stale=True)),
       "a_mirror": j(b=stale + [smp(0.7, host=1, src="none", seen=False, stale=True, mirror=True)]),
       "lever_plain": j(cal(fresh), cal(stale), cal(back)), "control_on": j(b=[edit(s, ctl=True) for s in stale])}
''')
    assert out.pop("good") and out.pop("cal"), out
    assert not any(out.values()), out


def test_s_world_refuses_on_the_field_term_alone():
    """S-WORLD: WorldHUD samples with the bench host 3 and my control witnessed off: never a mirror, ff / factor_now 1, why_not 'not on a
    live field' (the lever's when calibrating), edges_on +0. A field-blind engine (why_not past the field term), a mirror, ff 3, the
    host at 1 (a vacuous leg), no control-off sample, no WorldHUD are each red."""
    out = _child(_SOLO + r'''
W = [smp(0.0, ctl=True, ui="WorldHUD", scene="WorldMap", why=WF)] + [smp(0.1 + 0.1 * i, ui="WorldHUD", scene="WorldMap", why=WF)
                                                                      for i in range(8)]
j = lambda S=W, c=None: so.judge_world(S, c)[0]
OUT = {"good": j(), "cal": j([edit(s, why_not=WL) for s in W], "off"), "field_blind": j([edit(s, why_not=BW.SPEED_WHY_SCENE) for s in W]),
       "mirror": j(W + [edit(W[-1], mirror=True)]), "ff_3": j(W[:-1] + [edit(W[-1], ff=3)]), "host_1": j([edit(s, host_setting=1) for s in W]),
       "control_on": j([edit(s, ctl=True) for s in W]), "no_world": j([edit(s, ui_state="FieldHUD") for s in W]),
       "edges": j(W[:-1] + [edit(W[-1], edges_on=1)]), "lever_plain": j([edit(s, why_not=WL) for s in W])}
''')
    assert out.pop("good") and out.pop("cal"), out
    assert not any(out.values()), out


def test_the_order_skew_drops_one_publish_per_flip_and_no_more():
    """THE ORDER SKEW (the first s163 solo run, S-F1 and S-STALE red on it): HarnessAgent runs a `control` step and publishes its ack in
    the same Update, so that publish shows the new control with the speed block NetSyncSpeed's last Tick decided under the old one.
    Every judge that reads why_not over a control-filtered window drops that ONE publish (and a window's opening one), and two lagging
    publishes in a row stay red. Live, only S-F1 and S-STALE need it; the S-HOST, S-WORLD and marker cases pin that the same filter
    rides every such judge (there an earlier StartRule term names the flip's own publish, so their lag fixtures cannot occur live)."""
    out = _child(_SOLO + r'''
lag = lambda w, n=1, **kw: [smp(0.01 * i, why=w, **kw) for i in range(n)]    # n control-off publishes still reading the old why_not
pre = [smp(0.1 + 0.1 * i, host=1, why=WH) for i in range(5)]
f1 = [smp(0.0, host=1, why=WH)] + [smp(0.05 + 0.1 * i, host=1, raw=True, own=3, fac=3, fast=i > 0, why=WH) for i in range(8)]
post = [smp(0.1 * i, host=1, why=WH) for i in range(5)]
f1j = lambda P: so.judge_f1(P, f1, post, None, 3)[0]
NH = dict(host=1, tps=-1, src="none", seen=False)
F = lambda w=WH, **kw: [smp(0.1 + 0.1 * i, why=w, **dict(NH, **kw)) for i in range(6)]
on_flip = [smp(0.0, ctl=True, why=WC, **NH)]                                 # the window opens on control, then the flip mid-window
stj = lambda a: so.judge_stale(a, F(WS, stale=True), F(), None)[0]
rest = [smp(0.1 + 0.1 * i, ctl=True, why=WC) for i in range(5)]
hostj = lambda R: so.judge_bench_host(smp(0, ctl=True), [HOSTLINE], R, None)[0]
W = [smp(0.1 + 0.1 * i, ui="WorldHUD", scene="WorldMap", why=WF) for i in range(8)]
wl = lambda n: [smp(0.0, ctl=True, ui="WorldHUD", scene="WorldMap", why=WC)] + [smp(0.01 * (i + 1), ui="WorldHUD", scene="WorldMap",
                                                                                     why=WC) for i in range(n)]
wj = lambda S: so.judge_world(S, None)[0]
lev = lambda S: [edit(s, why_not=WL, lever="off") for s in S]
armed = lev([smp(0.1 + 0.1 * i) for i in range(6)])
mj = lambda S: so.off_marker(S, [])[0]
OUT = {"green": {"f1": f1j(lag(WC, host=1) + pre), "stale_head": stj(lag(WC, **NH) + F()), "stale_mid": stj(on_flip + lag(WC, **NH) + F()),
                 "host": hostj([smp(0.0, why=WH), smp(0.02, ctl=True, why=WH)] + rest), "world": wj(wl(1) + W),
                 "marker": mj([smp(0.0, ctl=True, why=WC), smp(0.02, why=WC)] + armed)},
       "red": {"f1": f1j(lag(WC, 2, host=1) + pre), "stale_head": stj(lag(WC, 2, **NH) + F()),
               "stale_mid": stj(on_flip + lag(WC, 2, **NH) + F()),
               "host": hostj([smp(0.0, why=WH), smp(0.02, ctl=True, why=WH), smp(0.04, ctl=True, why=WH)] + rest),
               "world": wj(wl(2) + W), "marker": mj([smp(0.0, ctl=True, why=WC), smp(0.02, why=WC), smp(0.04, why=WC)] + armed)}}
''')
    assert all(out["green"].values()), out
    assert not any(out["red"].values()), out


def test_the_solo_calibration_reds_exactly_the_mirror_rows():
    """Under the `speed off` lever's evidence (the mirror's every other term held, why_not the lever, never a mirror, no ON line) the
    five mirror judges are red and every one carries OFF_MARKER; the lever-aware rows (S-HOST, S-F1, S-STALE, S-WORLD) stay green on the
    same evidence. The marker itself can fail: the host at 1 (nothing armed), another why_not, a mirror sample, an ON line."""
    out = _child(_SOLO + r'''
lev = lambda S: [edit(s, why_not=WL, lever="off") for s in S]
raise_w = lev([smp(0.0, ctl=True, why=WC), smp(0.02)] + [smp(0.05 + 0.02 * i) for i in range(8)])
latch = lev([smp(0.1 * i) for i in range(6)])
back = lev([smp(0.0)] + [smp(0.05 + 0.05 * i, ctl=True) for i in range(12)])
b = so.counters(raise_w[-1])
reds = set()
if not so.judge_on(raise_w, [], b, 3, 352)[0]: reds.add("S-ON")
if not so.judge_latch(latch, [], b, None)[0]: reds.add("S-LATCH")
if not so.judge_back(back, [], b, 352)[0]: reds.add("S-BACK")
if not so.judge_battle(False, lev(DIO), b, [], 352)[0]: reds.add("S-BATTLE")
if not so.judge_off(False, [], b, [], [], {}, 352)[0]: reds.add("S-OFF")
host_rest = lev([smp(0.1 * i, ctl=True) for i in range(6)])
if not so.judge_bench_host(smp(0, ctl=True), [HOSTLINE], host_rest, "off")[0]: reds.add("S-HOST")
pre, post = lev([smp(0.1 * i, host=1) for i in range(5)]), lev([smp(0.1 * i, host=1) for i in range(5)])
f1 = lev([smp(0.05 + 0.1 * i, host=1, raw=True, own=3, fac=3, fast=True) for i in range(6)])
if not so.judge_f1(pre, f1, post, "off", 3)[0]: reds.add("S-F1")
F = lambda **kw: lev([smp(0.1 * i, host=1, tps=-1, src="none", seen=False, **kw) for i in range(6)])
if not so.judge_stale(F(), F(stale=True), F(), "off")[0]: reds.add("S-STALE")
if not so.judge_world(lev([smp(0.1 * i, ui="WorldHUD", scene="WorldMap") for i in range(8)]), "off")[0]: reds.add("S-WORLD")
marks = {"S-ON": (raise_w, []), "S-LATCH": (raise_w + latch, []), "S-BACK": (raise_w + latch + back, []),
         "S-BATTLE": (raise_w, []), "S-OFF": (raise_w, [])}
OUT = {"reds": sorted(reds), "pred": sorted(so.PREDICTED_OFF), "marks": {k: so.off_marker(*v)[0] for k, v in marks.items()},
       "m_host_1": so.off_marker(lev([smp(0.1 * i, host=1) for i in range(4)]), [])[0], "m_why": so.off_marker([smp(0.1 * i, why=WH) for i in range(4)], [])[0],
       "m_mirror": so.off_marker(raise_w + [smp(0.5, mirror=True, applied=True, fac=3)], [])[0], "m_on_line": so.off_marker(raise_w, [ON])[0]}
''')
    assert out["reds"] == out["pred"] == ["S-BACK", "S-BATTLE", "S-LATCH", "S-OFF", "S-ON"], out
    assert all(out["marks"].values()), out
    assert not out["m_host_1"] and not out["m_why"] and not out["m_mirror"] and not out["m_on_line"], out


def test_the_solo_calibration_words_and_the_refusals():
    """COOP_CALIBRATE, read AT LOAD (tools/play.py imports the scenario before its Session launches FF9): '' / 0 -> no calibration (no
    K-CAL rows); 1 / off / true / yes / on -> `speed off` with K-CAL-M and K-CAL naming exactly PREDICTED_OFF, every predicted row in
    the catalog, and run() reads the load's verdict; any other word (the duo's DLL names, a typo, another bench's lever) exits the
    IMPORT with the word named (code 1, nothing run) -- never mapped to the lever, never after a game booted."""
    cases = {}
    for v in ("", "0", "1", "off", "TRUE", "yes", "on"):
        cases[v] = _child(r'''
import inspect
cal = so.calibration()
cat = so.catalog(cal)
OUT = {"cal": cal, "mode": so.CAL_MODE, "rows": sorted(k for k in cat if k.startswith("K-CAL")), "kcal": cat.get("K-CAL"),
       "in_cat": all(p in cat for p in so.PREDICTED_OFF), "run_reads_load": "cal = CAL_MODE" in inspect.getsource(so.run)
       and "calibration()" not in inspect.getsource(so.run)}
''', env_cal=v)
    assert cases[""]["cal"] is None and cases["0"]["cal"] is None and cases[""]["rows"] == [] and cases[""]["mode"] is None
    assert all(c["run_reads_load"] for c in cases.values()), cases
    for v in ("1", "off", "TRUE", "yes", "on"):
        c = cases[v]
        assert c["cal"] == c["mode"] == "off" and c["rows"] == ["K-CAL", "K-CAL-M"] and c["in_cat"], (v, c)
        assert c["kcal"] == "the `speed off` calibration: exactly S-ON, S-LATCH, S-BACK, S-BATTLE, S-OFF red", c
    for v in ("s162", "noland", "2", "offf", "act"):
        r = _run_child("OUT = {}", env_cal=v, duo=False)
        assert r.returncode == 1 and f"COOP_CALIBRATE={v!r} is refused" in r.stderr and "before the game boots" in r.stderr, (
            v, r.stderr[-600:])
        assert "@@" not in r.stdout


def test_the_solo_run_keeps_the_lever_held_and_names_the_release():
    """The run's shape (source): the lever is pulled AFTER K2 and K-CAL-M needs it read back; S-STALE's `speed clear` (which sets the
    lever to act) is followed by a fresh `speed off` when calibrating; S-OFF never sends `act` while calibrating; K-R expects the
    release line exactly when a lever or a bench host was held into the reset, and judges the harness's speedmode released; the world
    leg reuses the s144 walk out; every leg is guarded and settles the latch between legs."""
    out = _child(r'''
import inspect
run, st, off, kr, gd, wo = (inspect.getsource(f) for f in (so.run, so._s_stale, so._s_off, so._k_r, so._guard, so._s_world))
OUT = {"after_k2": run.index("_k1_k2(g, led)") < run.index('_ns(g, "speed", "off")'),
       "marks_need_lever": "marks_ok = ctx.lever_held and all(" in run,
       "stale_retakes": 'if ctx.cal is not None:\n        _speed(g, ctx, "off")' in st and st.index('"clear"') < st.index('_speed(g, ctx, "off")'),
       "off_no_act": "if ctx.cal is None:" in off and off.index("if ctx.cal is None:") < off.index('_speed(g, ctx, "act")'),
       "release_iff": "held = ctx.lever_held or ctx.bench_host" in kr and '("release line iff held", line == held)' in kr,
       "speedmode_released": "g.speedmode(True)" in kr and '("raw false", sget(st, "raw") is False)' in kr,
       "walk_out": "ww.walk_out(g)" in wo and "import coop_world_wait as ww" in wo,
       "settles": "_settle_mirror_off(g)" in gd}
''')
    assert all(out.values()), out


# ------------------------------------------------------------------------------------------------ the duo fixtures
_DUO = r'''
def rd(t, field=450, ctl=False, mirror=False, applied=False, fac=1, ff=None, raw=False, own=1, fast=False, why=None, host=3, tps=30,
       src="wire", seen=True, stale=False, scene="FieldMap", lever=None):
    return {"t": t, "field": field, "ctl": ctl, "scene": scene, "ff": fac if ff is None else ff, "mirror": mirror, "applied": applied,
            "factor_now": fac, "raw": raw, "own": own, "fast_mode": fast, "why_not": why, "host_setting": host, "host_tps": tps,
            "src": src, "seen": seen, "stale": stale, "lever": lever}
P = "[NetSync] "
HOSTON = BW.speed_log_host(3, 30)
PASS = P + du.PASSES
LAND = P + du.LANDED + " -- the ATE plays here; the follow waits while my copy's control is off"
MAP450, MAP351 = "Map: 450 (Dali/Field)", "Map: 351 (Dali/Inn)"
lk = lambda w, t: P + f"dialogue lock: win {w} text {t} opened locked"
cl = lambda w, t, seq: P + f"dialogue: win {w} text {t} closed (host seq {seq})"
ON450 = BW.speed_log_on(450, 3, 3, 30, 3, 30, 1, BW.SPEED_START_WHY_ATE)
ON351 = BW.speed_log_on(351, 3, 3, 30, 3, 30, 1, BW.SPEED_START_WHY_ATE)
HOLD = P + "ATE relay: the follow to field 351 waits -- my copy plays the ATE (until its own exit)"
REL_PROG = (P + "ATE relay: the follow to field 351 stops waiting -- my copy's ATE on field 450 made no progress for 8 s (no line or "
            "window: the tail hold's progress clock)")
REL_CAP = P + "ATE relay: the follow to field 351 stops waiting -- my copy's ATE on field 450 ran past the tail hold's cap"
DROP = lambda seq, t: P + f"dialogue: host seq {seq} (win 3 text {t}) dropped -- it is for field 450"
FOLLOW = P + "following the peer to field 351"
DAGGER = [153, 154, 155, 156, 157, 159, 160, 162, 164, 167, 169, 171, 172, 173, 174, 175]
GM = ([ON351, PASS, P + BW.speed_log_off(351, 3000, 1, "field 450 loaded"), LAND, MAP450, ON450]
      + [x for i, t in enumerate(DAGGER) for x in (lk(3, t), cl(3, t, 40 + i))] + [HOLD, MAP351])
# Finding 10 under the lever: no ON line, cut at 161, the progress clock, drops, the follow
CUT = [153, 154, 155, 156, 157, 159, 160]
GM_CAL = ([PASS, LAND, MAP450] + [x for i, t in enumerate(CUT) for x in (lk(3, t), cl(3, t, 40 + i))] + [HOLD, REL_PROG, FOLLOW,
          MAP351] + [DROP(88 + i, t) for i, t in enumerate((162, 164, 167))])
GS = [rd(0.5 * i, mirror=True, applied=True, fac=3, fast=i > 0) for i in range(10)]
GS_CAL = [rd(0.5 * i, why=BW.SPEED_WHY_LEVER, lever="off") for i in range(10)]
HS = [rd(0.2 * i, fac=3, raw=True, own=3, src=None, host=1) for i in range(30)]
'''


def test_the_duo_refuses_an_unknown_calibration_word_at_load():
    """The duo reads COOP_CALIBRATE AT LOAD (duo.py imports the scenario before it boots the pair): '' / 0 none, 1 / off the guest's
    `speed off` with D-CAL-M and D-CAL naming exactly D4-D8; any other word exits the import with the refusal (code 1, nothing run)."""
    cases = {}
    for v in ("", "0", "1", "off", "ON"):
        cases[v] = _child(r'''
cat = du.catalog(du.CAL_MODE)
OUT = {"mode": du.CAL_MODE, "rows": sorted(k for k in cat if k.startswith("D-CAL")), "cal": cat.get(du.CAL_ID),
       "in_cat": all(p in cat for p in du.PREDICTED_OFF), "claims": sorted(du.CLAIMS)}
''', env_cal=v)
    assert cases[""]["mode"] is None and cases["0"]["mode"] is None and cases[""]["rows"] == []
    for v in ("1", "off", "ON"):
        c = cases[v]
        assert c["mode"] == "off" and c["rows"] == ["D-CAL", "D-CAL-M"] and c["in_cat"], (v, c)
        assert c["cal"] == "the guest's `speed off` calibration (same DLL): exactly D4, D5, D6, D7, D8 red", c
    assert cases[""]["claims"] == [f"D{i}" for i in range(10)]
    for v in ("s162", "noland", "2", "host"):
        r = _run_child("OUT = {}", env_cal=v, duo=True, solo=False)
        assert r.returncode == 1 and f"COOP_CALIBRATE={v!r} is refused" in r.stderr and "before the pair boots" in r.stderr, (v, r.stderr[-600:])
        assert "@@" not in r.stdout


def test_d1_and_d2_judge_the_hosts_booster_and_the_wire():
    """D1: one booster-ON line (S > 1, T > 0), raw / own_factor / ff S on 351, ff S on >= 5 of its own 450 samples, the 450 span within
    HOST_SPAN_MAX_S. D2: a guest sample reads S x T from the wire, seen, not stale. Each part alone is red."""
    out = _child(_DUO + r'''
h351 = rd(0, field=351, fac=3, raw=True, own=3, src=None, host=1)
j1 = lambda H=[HOSTON], a=h351, S=HS, t1=2.0, t2=22.0: du.judge_host(H, a, S, t1, t2)[0]
wire = [rd(0, field=351, host=1, tps=-1, src="none", seen=False), rd(0.1, field=351)]
j2 = lambda W=wire, s=3, t=30: du.judge_wire(W, s, t)[0]
OUT = {"d1": j1(), "no_line": j1(H=[]), "two_lines": j1(H=[HOSTON, HOSTON]), "setting_1": j1(H=[BW.speed_log_host(1, 30)]),
       "raw_false": j1(a=dict(h351, raw=False)), "own_1": j1(a=dict(h351, own=1)), "ff_1_351": j1(a=dict(h351, ff=1)),
       "no_351": j1(a=None), "ff_1_450": j1(S=HS[:5] + [dict(HS[5], ff=1)] + HS[6:]), "few_450": j1(S=HS[:4]),
       "span": j1(t2=2.0 + du.HOST_SPAN_MAX_S + 0.5), "never_back": j1(t2=None),
       "d2": j2(), "bench_src": j2(W=[dict(wire[1], src="bench")]), "setting": j2(W=[dict(wire[1], host_setting=2)]),
       "tps": j2(t=60), "stale": j2(W=[dict(wire[1], stale=True)]), "unseen": j2(W=[dict(wire[1], seen=False)]), "no_host": j2(s=None)}
''')
    assert out.pop("d1") and out.pop("d2"), out
    assert not any(out.values()), out


def test_d3_and_d4_judge_the_own_jump_and_the_mirror_on_450():
    """D3: the own jump passes once on the host's pick (choice 2), lands, one 'Map: 450', 153 locked after the landing. D4: an ON line on
    450 after the landing at F = S = G > 1 (my own factor 1; the 351 ON line never counts) and a control-off 450 sample with the factor
    applied through the real getter (raw false), FAST MODE. Each part alone is red."""
    out = _child(_DUO + r'''
j3 = lambda G=GM: du.judge_jump(G)[0]
j4 = lambda G=GM, S=GS, s=3: du.judge_on(G, S, s)[0]
on = lambda **kw: BW.speed_log_on(**dict(dict(fld=450, factor=3, host_setting=3, host_tps=30, g=3, my_tps=30, own=1,
                                              why=BW.SPEED_START_WHY_ATE), **kw))
swap = lambda new: [new if x == ON450 else x for x in GM]
OUT = {"d3": j3(), "no_pass": j3([x for x in GM if x != PASS]), "two_pass": j3([PASS] + GM), "no_land": j3([x for x in GM if x != LAND]),
       "two_maps": j3(GM + [MAP450]), "first_before_land": j3([lk(3, 153), PASS] + [x for x in GM if x not in (PASS, lk(3, 153))]),
       "d4": j4(), "host_why": j4(swap(on(why=BW.SPEED_START_WHY_HOST))),
       "no_on": j4([x for x in GM if x != ON450]), "only_351": j4([x for x in GM if x != ON450]),
       "before_land": j4([ON450] + [x for x in GM if x != ON450]), "factor_2": j4(swap(on(factor=2, g=2))),
       "factor_not_g": j4(swap(on(g=2))), "own_3": j4(swap(on(own=3))), "s_mismatch": j4(s=4),
       "not_applied": j4(S=[dict(x, applied=False) for x in GS]), "ff_1": j4(S=[dict(x, ff=1) for x in GS]),
       "raw": j4(S=[dict(x, raw=True) for x in GS]), "no_fast": j4(S=[dict(x, fast_mode=False) for x in GS]),
       "control_on": j4(S=[dict(x, ctl=True) for x in GS]), "on_351": j4(S=[dict(x, field=351) for x in GS])}
''')
    assert out.pop("d3") and out.pop("d4") and out.pop("host_why"), out
    assert not any(out.values()), out


def test_d5_to_d8_judge_the_tail_the_drops_the_last_line_and_the_gap():
    """D5: no tail release by either clock (a hold alone is fine). D6: no drop as field 450's (another field's drop is not judged). D7:
    450's last line (win 3 text 175) opened locked AND closed by the host's event (175 in another window does not count). D8: back within
    GAP_MAX_S of the host (a guest that leads is fine) and by its own exit. Each part alone is red."""
    out = _child(_DUO + r'''
OUT = {"d5": du.judge_hold(GM)[0], "d5_prog": du.judge_hold(GM + [REL_PROG])[0], "d5_cap": du.judge_hold(GM + [REL_CAP])[0],
       "d6": du.judge_drops(GM + [P + "dialogue: host seq 9 (win 2 text 324) dropped -- it is for field 350"])[0],
       "d6_drop": du.judge_drops(GM + [DROP(88, 162)])[0],
       "d7": du.judge_last(GM)[0], "d7_unopened": du.judge_last([x for x in GM if x != lk(3, 175)])[0],
       "d7_unclosed": du.judge_last([x for x in GM if "text 175 closed" not in x])[0],
       "d7_other_win": du.judge_last([x.replace("win 3 text 175", "win 6 text 175") for x in GM])[0],
       "d8": du.judge_gap(GM, 22.0, 23.5)[0], "d8_leads": du.judge_gap(GM, 22.0, 20.0)[0],
       "d8_edge": du.judge_gap(GM, 22.0, 22.0 + du.GAP_MAX_S)[0], "d8_late": du.judge_gap(GM, 22.0, 26.5)[0],
       "d8_follow": du.judge_gap(GM + [FOLLOW], 22.0, 23.0)[0], "d8_never": du.judge_gap(GM, 22.0, None)[0],
       "d8_host_never": du.judge_gap(GM, None, 23.0)[0], "gap": du.GAP_MAX_S, "span": du.HOST_SPAN_MAX_S, "page": du.PAGE_S}
''')
    assert (out.pop("gap"), out.pop("span"), out.pop("page")) == (4.0, 24.0, 0.5)
    for k in ("d5", "d6", "d7", "d8", "d8_leads", "d8_edge"):
        assert out.pop(k), (k, out)
    assert not any(out.values()), out


def test_d9_judges_the_guests_free_roam_against_the_hosts_booster():
    """D9: >= ROAM_MIN guest samples on 351, every one with control, ff 1, factor_now 1, no mirror / applied, raw false -- while every
    host sample still reads ff S (the positive control). Each part alone is red."""
    out = _child(_DUO + r'''
G = [rd(0.2 * i, field=351, ctl=True) for i in range(8)]
H = [rd(0.2 * i, field=351, ctl=True, fac=3, raw=True, own=3, src=None, host=1) for i in range(8)]
j = lambda g=G, h=H, s=3: du.judge_roam(g, h, s)[0]
OUT = {"good": j(), "ff_3": j(g=G[:3] + [dict(G[3], ff=3)] + G[4:]), "factor_3": j(g=G[:3] + [dict(G[3], factor_now=3)] + G[4:]),
       "applied": j(g=G + [dict(G[0], applied=True)]), "mirror": j(g=G + [dict(G[0], mirror=True)]),
       "control_off": j(g=G + [dict(G[0], ctl=False)]), "raw": j(g=[dict(x, raw=True) for x in G]), "few": j(g=G[:3]),
       "host_1x": j(h=[dict(x, ff=1) for x in H]), "no_host": j(h=[]), "s_none": j(s=None), "elsewhere": j(g=[dict(x, field=450) for x in G])}
''')
    assert out.pop("good"), out
    assert not any(out.values()), out


def test_the_duo_calibration_reds_exactly_d4_to_d8_with_their_markers():
    """Finding 10 under the guest's `speed off` (the 1x copy: no ON line, cut at 161, the progress clock's release, the rest dropped as
    450's, the follow carrying it late) reds EXACTLY D4-D8, and every marker holds; D3 and D9 (the relay, the guest's own speed in free
    roam) stay green on the same run. The plain s163 evidence reds none of D3-D9, and its markers fail (they can). D-CAL-M also needs
    the BEAT GUARD (the copy not yet past 161 when the host left) and D5's release by the progress clock."""
    out = _child(_DUO + r'''
roam_g = [rd(0.2 * i, field=351, ctl=True, why=BW.SPEED_WHY_LEVER, lever="off") for i in range(8)]
roam_h = [rd(0.2 * i, field=351, ctl=True, fac=3, raw=True, own=3, src=None, host=1) for i in range(8)]
def reds(G, S, t_h, t_g, rg):
    r = set()
    for cid, (ok, _w) in (("D3", du.judge_jump(G)), ("D4", du.judge_on(G, S, 3)), ("D5", du.judge_hold(G)), ("D6", du.judge_drops(G)),
                          ("D7", du.judge_last(G)), ("D8", du.judge_gap(G, t_h, t_g)), ("D9", du.judge_roam(rg, roam_h, 3))):
        if not ok:
            r.add(cid)
    return sorted(r)
mk = du.markers(GM_CAL, GS_CAL)
EXIT_CAL = GM_CAL[:GM_CAL.index(HOLD) + 1]               # the guest's lines by the host's 351 landing: its copy cut at 160
past = EXIT_CAL[:-1] + [lk(3, 162), lk(3, 164), HOLD]  # a copy already past the wordless beat when the host left
cap_only = [x for x in GM_CAL if x != REL_PROG] + [REL_CAP]
OUT = {"cal": reds(GM_CAL, GS_CAL, 21.0, 30.5, roam_g), "plain": reds(GM, GS, 21.0, 22.4, [dict(x, why_not=None, lever=None) for x in roam_g]),
       "pred": list(du.PREDICTED_OFF), "markers": {k: v[0] for k, v in mk.items()},
       "judge_markers": du.judge_markers(True, GM_CAL, GS_CAL, EXIT_CAL)[0],
       "no_lever": du.judge_markers(False, GM_CAL, GS_CAL, EXIT_CAL)[0],
       "beat": [du.beat_guard(EXIT_CAL)[0], du.beat_guard([PASS, LAND, MAP450])[0], du.beat_guard(EXIT_CAL[:-1] + [lk(3, 161)])[0]],
       "past_beat": du.judge_markers(True, GM_CAL, GS_CAL, past)[0], "no_exit": du.judge_markers(True, GM_CAL, GS_CAL, None)[0],
       "past_named": "PAST the wordless beat" in du.judge_markers(True, GM_CAL, GS_CAL, past)[1],
       "d5_cap_only": du.markers(cap_only, GS_CAL)["D5"][0], "d5_cap_still_red": not du.judge_hold(cap_only)[0],
       "plain_markers": {k: v[0] for k, v in du.markers(GM, GS).items()}}
''')
    assert out["cal"] == out["pred"] == ["D4", "D5", "D6", "D7", "D8"], out
    assert out["plain"] == [], out
    assert all(out["markers"].values()) and out["judge_markers"] and not out["no_lever"], out
    assert not any(out["plain_markers"].values()), out
    # (the review) the guest's own timing guard: a copy past 450's wordless beat at the host's exit, or no exit seen, voids D-CAL-M
    # by name; D5's marker is the PROGRESS clock's release (a cap release still reds D5, but is the other timing, not the prediction)
    assert out["beat"] == [True, True, True] and out["past_named"], out
    assert not out["past_beat"] and not out["no_exit"] and not out["d5_cap_only"] and out["d5_cap_still_red"], out


def test_the_duo_drives_the_host_and_calibrates_the_guest():
    """The duo's shape (source): `speedmode 1` on the HOST, the calibration lever `speed off` on the GUEST (same DLL: rev 3) read back
    before the host's press, the host paging at PAGE_S inside the watch, D1 judged off the host's own samples, both levers released in
    the teardown; the 351 gate is the 352 pair with the "Dagger Tries" row (bit 2, choice 2)."""
    out = _child(r'''
import inspect
run, end, watch = inspect.getsource(du._run), inspect.getsource(du.run_duo), inspect.getsource(du._ate_watch)
OUT = {"host_booster": "host.speedmode(True)" in run, "guest_lever": 'cb.try_ns(guest, "speed", "off")' in run,
       "lever_before_press": run.index('cb.try_ns(guest, "speed", "off")') < run.index('host.press("select", 2)'),
       "pace": "now - since >= PAGE_S" in watch and 'host.press("confirm", 2)' in watch,
       "teardown": "d.host.speedmode(False)" in end and '"speed", "act"' in end,
       "d0_armed": run.index("host.poke(B_AVAIL, 1)") < run.index("host.warp(HUB, entrance=0, scenario=SCENARIO)")
       and "armed and host_before == 0" in run,
       "beat_recorded": 'out["g_lines_at_h351"] = len(d.lines("guest"))' in watch and 'ctx["gm_exit"]' in run,
       "gate": [du.B_AVAIL, du.B_ROWS_LO, du.B_ROWS_HI, du.ROWS, du.PICK, du.ROWS == 1 << du.PICK],
       "fields": [du.HUB, du.DEST, du.SCENARIO], "lines": [list(du.FIRST_LINE), list(du.LAST_LINE)]}
''')
    assert out.pop("gate") == [238, 241, 242, 4, 2, True] and out.pop("fields") == [351, 450, 2600]
    assert out.pop("lines") == [[3, 153], [3, 175]]
    assert all(out.values()), out


def test_the_benches_match_the_engines_words():
    """The words both benches match are the engine's: battlewire's twins of NetSyncSpeed (StartRule's why_not, Tick's START reasons,
    EndWords, the ON / OFF / host lines), the stand-in's harness lines (CALIBRATION, release, bench host), and the patch stack's own
    literals for the s163 lines and the s96 / s161 / s162 lines the duo reads (the drop, the follow, the own jump, the tail release)."""
    stack = {p.name: p.read_text(encoding="utf-8", errors="replace") for p in PATCHES.glob("*.patch")}
    s163 = stack.get("s163-netsync-speed-mirror.patch")
    assert s163 is not None, "memoria-patches/s163-netsync-speed-mirror.patch is not captured yet"
    blob = "\n".join(stack.values())
    for frag in ('"[NetSync] speed mirror: ON on field " + fld + " -- factor " + factor + " (the host\'s booster "',
                 '" TPS covers my " + g + " x " + myTps + "; my own factor " + own + ") -- " + why',
                 '"[NetSync] speed mirror: OFF on field " + field + " after " + ms + " ms -- factor back to " + own + " (my own) -- " + why',
                 '"[NetSync] speed mirror (host): my booster is ON (setting " + setting + ", FieldTPS "',
                 '"[NetSync] harness: speed mirror\'s bench host -- section 10 = setting " + setting + " x " + readTps',
                 '" TPS through the real codec (released with the harness)"',
                 '"[NetSync] harness: speed mirror lever released (act; the bench host forgotten)"',
                 '"OFF -- CALIBRATION: s162\'s rule, never mirror (released with the harness)"',
                 '"my control is back (" + NetSyncStepOut.StepInMs + " ms)"', '"I left the field scene (" + SceneNow() + ")"',
                 '"the host plays its scene here (its control is off)"', '"[NetSync] speed mirror selftest: "',
                 '" mutants caught, step-in " + NetSyncStepOut.StepInMs + " ms"', '"FAIL (" + spDetail + ")"'):
        assert frag in s163, frag
    for frag in ('" made no progress for " + (TailHoldMs / 1000) + " s (no line or window: the tail hold\'s progress clock)"',
                 '" stops waiting -- my copy\'s ATE on field "', 'why = "dropped -- it is for field " + e.Fld;',
                 '"[NetSync] following the peer to field " + rs.Field', '") passes -- the host\'s pick (choice " + _pick + ") on field "',
                 '") landed -- the ATE plays here"'):
        assert frag in blob, frag
    out = _child(r'''
OUT = {"why": [so.WHY_LEVER == BW.SPEED_WHY_LEVER, so.WHY_FIELD == BW.SPEED_WHY_FIELD, so.WHY_CONTROL == BW.SPEED_WHY_CONTROL,
               so.WHY_STALE == BW.SPEED_WHY_STALE, so.WHY_HOST == BW.SPEED_WHY_HOST, du.WHY_LEVER == BW.SPEED_WHY_LEVER],
       "start": so.START_WHY_HOST == BW.SPEED_START_WHY_HOST,
       "ends": [so.END_CONTROL == BW.speed_end_words(BW.SPEED_END_CONTROL, 352), so.END_LEVER == BW.speed_end_words(BW.SPEED_END_LEVER, 352),
                BW.speed_end_words(BW.SPEED_END_SCENE, 352, "BattleMapDebug").startswith(so.END_SCENE)],
       "on_rx": bool(so.ON_RX.search(BW.speed_log_on(352, 3, 3, 30, 3, 30, 1, "x"))) and so.ON_RX.pattern == du.ON_RX.pattern,
       "off_rx": bool(so.OFF_RX.search(BW.speed_log_off(352, 512, 1, "y"))),
       "host_rx": bool(du.HOST_ON_RX.search(BW.speed_log_host(3, 30))) and not du.HOST_ON_RX.search(BW.speed_log_host(1, 30)),
       "bench_rx": bool(so.BENCH_HOST_RX.search(FG.SPEED_LOG_HOST.format(s=3, t=30))),
       "harness": [so.LOG_HARNESS_OFF == FG.SPEED_LOG_OFF, so.LOG_RELEASE == FG.SPEED_LOG_RELEASE],
       "step_in": so.STEP_IN_MS == BW.SPEED_STEP_IN_MS, "probe": so.PROBE == "netsync.speed.edges_on" and "edges_on" in FG.NETSYNC_SPEED_KEYS}
''')
    assert all(v if isinstance(v, bool) else all(v) for v in out.values()), out


# ------------------------------------------------------------------------------------------------ the whole solo bench on the stand-in
_STAND_IN = r'''
import json, os, pathlib, sys, tempfile
sys.path.insert(0, %r)
sys.path.insert(0, %r)
from harness import Session
from harness import fakegame as FG
import coop_speed_mirror as so
import coop_world_wait as cw
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
    t = pathlib.Path(d)
    (t / "x64").mkdir()
    (t / "x64" / "FF9.exe").write_bytes(b"MZ")
    (t / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (t / "FF9CustomMap").mkdir()
    (t / "FF9CustomMap" / "DictionaryPatch.txt").write_text("FieldScene 6603 31 FARSHORE FARSHORE 6603\n", encoding="utf-8")
    # REAL TIME (publish "mtime"): the bench's debounce is wall-clock, the engine's TickCount -- the stand-in's virtual clock must
    # follow the wall, however busy the machine (a loop that falls behind catches up; FakeGame._pace_real_time)
    f = FG.FakeGame(t, walkmesh=(-2000.0, -3000.0, 2000.0, 2000.0), publish=("rt", "mtime"))
    if os.environ.get("SM_CAPS"):
        f.netsync_caps = FG.caps_through(os.environ["SM_CAPS"])
    f.regions = {6603: [{"zone": cw.FS_DOOR, "world": cw.WORLD, "world_at": list(cw.FS_LANDING)}]}   # the s144 test's door
    f.exit_frames = 900
    f.overworld = {"speed": 2.0, "turn": 2.8125, "cam": 0.0, "lag": 1}
    g = Session(game_path=t, run_dir=t / "run", save_dir=t / "player-saves", pid_probe=lambda: [], launcher=lambda exe: f.start(),
                boot_timeout=15.0, verbose=False)
    rows = []
    g.check = lambda ok, what, detail="": (rows.append([what.split(":", 1)[0], bool(ok), str(detail)[:600]]), ok)[1]
    g.note = lambda text: None
    with g:
        so.run(g)
    print("@@" + json.dumps(rows))
''' % (str(REPO / "tools"), str(SCEN))


def test_the_solo_bench_runs_green_on_the_s163_stand_in_calibrates_exactly_and_reds_on_s162():
    """The WHOLE solo bench (coop_speed_mirror.run) against the stand-in, which models the bench latch through battlewire's twins:
    every row green on s163 (the world leg through 6603's door, the s144 test's shape); COOP_CALIBRATE=1 reds EXACTLY S-ON, S-LATCH,
    S-BACK, S-BATTLE, S-OFF with K-CAL-M and K-CAL green; the s162 stand-in (no `netsync.speed`: the driver refuses `speed` before the
    step) reds every row but K0. Three child processes in parallel; the stand-in paces itself in real time."""
    runs = {"plain": {}, "cal": {"COOP_CALIBRATE": "1"}, "s162": {"SM_CAPS": "ateland"}}
    procs = {}
    for name, extra in runs.items():
        env = {k: v for k, v in os.environ.items() if k not in ("COOP_CALIBRATE", "SM_CAPS")}
        env.update(extra)
        procs[name] = subprocess.Popen([sys.executable, "-X", "utf8", "-c", _STAND_IN], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, cwd=str(SCEN), env=env)
    out = {}
    for name, p in procs.items():
        so_, se = p.communicate(timeout=420)
        assert p.returncode == 0, (name, se[-3000:])
        rows = json.loads(next(ln for ln in so_.splitlines() if ln.startswith("@@"))[2:])
        out[name] = {"red": sorted(c for c, ok, _d in rows if not ok), "all": [c for c, _ok, _d in rows],
                     "detail": {c: d for c, _ok, d in rows}}
    order = ["K0", "K1", "K2", "S-HOST", "S-ON", "S-LATCH", "S-BACK", "S-BATTLE", "S-OFF", "S-F1", "S-STALE", "S-WORLD", "K-R"]
    p, c, o = out["plain"], out["cal"], out["s162"]
    assert p["red"] == [], {k: p["detail"][k] for k in p["red"]}
    assert p["all"] == order, p["all"]
    assert "my control is back (500 ms)" in p["detail"]["S-BACK"] and "why_not not on a live field ok" in p["detail"]["S-WORLD"]
    assert "held into the reset: lever False, bench host True" in p["detail"]["K-R"], p["detail"]["K-R"]
    assert c["red"] == sorted(["S-ON", "S-LATCH", "S-BACK", "S-BATTLE", "S-OFF"]), {k: c["detail"][k] for k in c["red"]}
    assert c["all"] == order + ["K-CAL-M", "K-CAL"], c["all"]
    assert "unpredicted reds: none" in c["detail"]["K-CAL"] and "held into the reset: lever True" in c["detail"]["K-R"]
    assert o["red"] == [k for k in sorted(order) if k != "K0"], {k: o["detail"][k] for k in order if k not in o["red"]}
    assert "publishes no `netsync.speed`" in o["detail"]["S-HOST"], o["detail"]["S-HOST"]
