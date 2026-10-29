"""[ff9mapkit netsync s162] THE ATE RELAY BENCHES' REPO HALF -- studies/test-harness/scenarios/coop_ate_relay.py (solo) and
coop_ate_relay_duo.py (two games), as s162 (THE LANDING START, GUEST-TRAVERSAL-TWO-PC.md Finding 9) re-cut them.

s162 starts the guest's step-out AT its own-jump DEST landing (reason `ate`), right after 'my copy's own Field(350) landed' and
before the ATE's first line -- and possibly before 'Map: 350', which Memoria logs at LateUpdate. These tests pin, offline, with
fixtures in the ENGINE's log and state shapes:

  * THE HUB SLICE: S1 / D8 judge only the menu and the title on 352 -- cut at the FIRST of the landed line and 'Map: 350' -- so an
    s162 landing OUT never reds them, while an OUT over the menu still does (and the old Map-only cut WOULD have red an s162 run);
  * the noexempt calibration's marker can still FAIL: an OUT at the landing (on 350) never stands in for an OUT over the menu;
  * S-LAND (solo) / D10 (duo) can go red on every part: no landed line, no first line, no OUT by `ate`, two of them, one after 321
    or before the landing, a waited OUT first, a counter that is absent (an s161 engine) or never rose, no landing_wire sample;
  * the noland marker needs the s161 shape (no `ate` OUT, a waited OUT on 350 after the landing) and refuses the s162 one;
  * D11 (duo) is green only on 'mask0' hides through the guest's first line: an option-C hide, a shown ghost, a vacuous window, a
    window that never started or never reached the first line are each red; D12 (the guest's screen) only on 'landing' /
    'step_out' hides, by the same judge; both windows start at the title's close and end WATCH_TAIL_S past the first line;
  * each calibration's predicted reds; the duo REFUSES `noland` at load (a selftest-role lever on a client guest: never a
    calibration), and the solo bench refuses any word it does not know (never `ate off` by default).

Every scenario-touching test runs in a CHILD process (the scenario puts its own dir on sys.path -- never this process's).
"""
import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
SCEN = REPO / "studies" / "test-harness" / "scenarios"


def _run_child(code: str, env_cal: str | None = None, duo: bool | None = None) -> subprocess.CompletedProcess:
    """``duo``: import the duo bench too (default: when the code names ``du.``) -- it refuses COOP_CALIBRATE=noland at load."""
    duo = ("du." in code) if duo is None else duo
    full = ("import json, os, sys\nsys.path.insert(0, %r)\nsys.path.insert(0, %r)\n" % (str(SCEN), str(REPO / "tools"))
            + "import coop_ate_relay as so\n" + ("import coop_ate_relay_duo as du\n" if duo else "") + code
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


_FIX = r'''
P = "28.10.2026 20:48:2%d |M| [NetSync] "
def ln(text, t=4):
    return (P % t) + text
MENU = [ln("ATE relay: host seq 3 queued (field 352 uid 2 win 1 text 98)"), ln("ATE relay: host seq 3 served to uid 2's Select read"),
        ln("ATE relay: host seq 3 opened my copy's ATE menu (win 1 text 98, uid 2, 1 key tick(s) served)"),
        ln("dialogue lock: win 1 text 98 opened locked"), ln("dialogue: win 1 text 98 closed (host seq 4, choice 1)"),
        ln("dialogue lock: win 0 text 100 opened locked"), ln("dialogue: win 0 text 100 closed (host seq 5)"),
        ln("ATE relay: my copy's own Field(350) passes -- the host's pick (choice 1) on field 352")]
LANDED = ln("ATE relay: my copy's own Field(350) landed -- the ATE plays here; the follow waits while my copy's control is off", 5)
def out(field, why, t=5):
    return ln("step-out: OUT on field %d (uid 34, undressed: the body stays; the host's ghost hides, my wire mask is 0) -- %s"
              % (field, why), t)
MAP = (P % 5).replace("[NetSync] ", "") + "Map: 350 (Dali/Village Road)"
FIRST = ln("dialogue lock: win 4 text 321 opened locked", 6)
S162 = MENU + [LANDED, out(350, "ate"), MAP, FIRST]            # the s162 order: the landing OUT before 'Map: 350'
S162_LATE_MAP = MENU + [LANDED, MAP, out(350, "ate"), FIRST]
S161 = MENU + [MAP, LANDED, FIRST, out(350, "line", 6)]        # s161 / noland: the OUT waits for 321's line
NOEX = MENU[:4] + [out(352, "line", 4)] + MENU[4:] + [LANDED, out(350, "ate"), MAP, FIRST]   # noexempt: an OUT over the menu
def smp(field, ate=None, wire=None):
    so_ = {}
    if ate is not None:
        so_["out_why"] = {"line": 0, "dwell": 0, "ate": ate}
    if wire is not None:
        so_["landing_wire"] = wire
    return {"field": {"id": field}, "netsync": {"stepout": so_}}
GOOD = [smp(352, 0, False), smp(350, 1, True), smp(350, 1, True)]
'''


def test_the_hub_slice_cuts_at_the_landing_and_keeps_s1_honest():
    """S1 / D8's slice ends at the FIRST of the landed line and 'Map: 350': an s162 landing OUT (even ahead of 'Map: 350') never
    enters it, an OUT over the menu does; the OLD Map-only cut would have taken the s162 landing OUT in."""
    out = _child(_FIX + r'''
term = [{"netsync": {"stepout": {"base": {"why_not": so.STEP_TERM}}, "ate": {"stepout_exempt": True}}}]
old_cut = lambda L: L[:next((i for i, x in enumerate(L) if "Map: 350 " in x), len(L))]
OUT = {"end": so.hub_end(S162), "end_late": so.hub_end(S162_LATE_MAP), "end_161": so.hub_end(S161), "none": so.hub_end(MENU),
       "s1_162": so.judge_s1(so.hub_slice(S162), term)[0], "s1_late": so.judge_s1(so.hub_slice(S162_LATE_MAP), term)[0],
       "s1_161": so.judge_s1(so.hub_slice(S161), term)[0], "s1_menu_out": so.judge_s1(so.hub_slice(NOEX), term)[0],
       "s1_no_term": so.judge_s1(so.hub_slice(S162), [])[0], "old_cut_red": so.judge_s1(old_cut(S162), term)[0],
       "duo_uses_it": "solo.hub_end(gm)" in __import__("inspect").getsource(du._run)}
''')
    n = 8                                               # len(MENU)
    assert out["end"] == n and out["end_late"] == n and out["end_161"] == n and out["none"] == n, out
    assert out["s1_162"] and out["s1_late"] and out["s1_161"], out
    assert not out["s1_menu_out"] and not out["s1_no_term"], out
    assert not out["old_cut_red"], out                  # the reason for the re-slice: the Map-only cut reds a correct s162 run
    assert out["duo_uses_it"], out


def test_the_noexempt_marker_still_discriminates_the_menu_from_the_landing():
    """The noexempt marker needs an OUT on 352 inside the hub slice while the menu was up: s162's landing OUT on 350 alone never
    satisfies it (the marker can FAIL), nor does an OUT on 352 logged after the landing."""
    out = _child(_FIX + r'''
late_352 = MENU + [LANDED, out(352, "line"), MAP, FIRST]
OUT = {"noex": so.noexempt_marker(NOEX)[0], "landing_only": so.noexempt_marker(S162)[0], "late_352": so.noexempt_marker(late_352)[0],
       "no_menu": so.noexempt_marker([out(352, "line"), LANDED])[0]}
''')
    assert out == {"noex": True, "landing_only": False, "late_352": False, "no_menu": False}, out


def test_s_land_is_green_only_on_the_landing_start_and_can_go_red_on_each_part():
    """S-LAND: ONE OUT by `ate` on 350, the first OUT on 350 after the landing, between the landed line and 321; out_why.ate rose
    from its pre-replay value (absent = red); a 350 sample read landing_wire true."""
    out = _child(_FIX + r'''
j = lambda L, a0=0, S=GOOD: so.judge_landing(L, a0, S)[0]
OUT = {"s162": j(S162), "late_map": j(S162_LATE_MAP), "s161": j(S161, None, [smp(350)]), "noland": j(S161, 0, [smp(350, 0, False)]),
       "no_landed": j([x for x in S162 if x != LANDED]), "no_first": j([x for x in S162 if x != FIRST]),
       "two_ates": j(MENU + [LANDED, out(350, "ate"), out(350, "ate"), FIRST]),
       "ate_after_321": j(MENU + [LANDED, FIRST, out(350, "ate", 6)]),
       "ate_before_landed": j(MENU + [out(350, "ate"), LANDED, FIRST]),
       "waited_first": j(MENU + [LANDED, out(350, "dwell"), out(350, "ate"), FIRST]),
       "ate_on_352": j(MENU + [LANDED, out(352, "ate"), FIRST]),
       "absent_counter": j(S162, None), "never_rose": j(S162, 1), "bool_counter": j(S162, True),
       "no_wire": j(S162, 0, [smp(350, 1, False)]), "wire_on_352": j(S162, 0, [smp(352, 1, True), smp(350, 1, False)])}
''')
    assert out.pop("s162") and out.pop("late_map"), out
    assert not any(out.values()), out


def test_the_noland_marker_needs_the_s161_shape():
    """The noland marker: no OUT by `ate` anywhere and a WAITED OUT on 350 (line / dwell) after the landed line."""
    out = _child(_FIX + r'''
OUT = {"s161": so.noland_marker(S161)[0], "dwell": so.noland_marker(MENU + [LANDED, out(350, "dwell"), FIRST])[0],
       "s162": so.noland_marker(S162)[0], "none": so.noland_marker(MENU + [LANDED, FIRST])[0],
       "before_landing": so.noland_marker(MENU + [out(350, "line"), LANDED, FIRST])[0],
       "no_landed": so.noland_marker(MENU + [FIRST, out(350, "line")])[0]}
''')
    assert out == {"s161": True, "dwell": True, "s162": False, "none": False, "before_landing": False, "no_landed": False}, out


def test_the_solo_calibrations_and_their_predicted_reds():
    """COOP_CALIBRATE: off (1 / off / true / yes / on) / noexempt / noland; each one's lever, predicted reds and catalog rows; `ate
    off` reds S-LAND too (no episode, no landing); the s161 DLL's prediction is S-LAND alone; no calibration -> no K-CAL rows; any
    other word (the duo's "s161", a typo) is refused, never mapped to `ate off`."""
    cases = {}
    for v in ("", "0", "1", "off", "yes", "noexempt", "noland", "NOLAND"):
        cases[v] = _child(r'''
cal = so.calibration()
cat = so.catalog(cal)
OUT = {"cal": cal, "rows": sorted(k for k in cat if k.startswith("K-CAL")), "lever": list(so.LEVERS[cal]) if cal else None,
       "pred": list(so.predicted_of(cal)) if cal else None, "kcal": cat.get("K-CAL"),
       "in_cat": all(p in cat for p in (so.predicted_of(cal) if cal else ())), "s161": list(so.PREDICTED_S161),
       "claims": "S-LAND" in so.CLAIMS}
''', env_cal=v)
    assert cases[""]["cal"] is None and cases["0"]["cal"] is None and cases[""]["rows"] == []
    assert cases["1"]["cal"] == cases["off"]["cal"] == cases["yes"]["cal"] == "off" and cases["1"]["lever"] == ["ate", "off"]
    assert "S-LAND" in cases["off"]["pred"] and cases["off"]["pred"][-1] == "S-LAND"
    assert cases["noexempt"]["pred"] == ["S1"] and cases["noexempt"]["lever"] == ["ate", "noexempt"]
    for v in ("noland", "NOLAND"):
        c = cases[v]
        assert c["cal"] == "noland" and c["lever"] == ["stepout", "noland"] and c["pred"] == ["S-LAND"], c
        assert c["rows"] == ["K-CAL", "K-CAL-M"] and c["kcal"] == "the `stepout noland` calibration: exactly S-LAND red", c
    assert all(c["in_cat"] and c["claims"] and c["s161"] == ["S-LAND"] for c in cases.values())
    for v in ("s161", "nolnad", "2"):
        refused = _child(r'''
try:
    so.calibration()
    OUT = {"refused": False, "why": ""}
except so.HarnessError as err:
    OUT = {"refused": True, "why": str(err)}
''', env_cal=v)
        assert refused["refused"] and repr(v) in refused["why"] and "noland" in refused["why"], (v, refused)


def test_the_solo_k_cal_m_needs_the_lever_taken_and_k_r_reads_the_held_levers_block():
    """K-CAL-M is red when the lever was refused (an s161 engine refuses `stepout noland` before the step); K-R reads the STEP-OUT's
    lever and its release line when the noland lever was held."""
    out = _child(r'''
import inspect
run, kr, rp = inspect.getsource(so.run), inspect.getsource(so._k_r), inspect.getsource(so._replay)
OUT = {"held": "marks_ok = ctx.lever_held and all(" in run, "sub": "ok, why = _ns(g, sub, op)" in run,
       "kr_lever": 'cb.path(st, f"netsync.{ctx.lever_sub}.lever")' in kr, "kr_line": "LOG_RELEASE_STEPOUT if ctx.lever_sub == \"stepout\"" in kr,
       "s_land": '("S-LAND", judge_landing(lines, ate0, samples))' in rp, "slice": "judge_s1(hub_slice(lines), caption_samples)" in rp,
       "ate0_first": rp.index("ate0 = ") < rp.index('_must(g, "replay")'), "marks": '"S1", "S-LAND"):' in rp,
       "release_line": so.LOG_RELEASE_STEPOUT}
''')
    assert out.pop("release_line") == "[NetSync] harness: step-out lever released (act)"
    assert all(out.values()), out


def test_d11_is_green_only_on_mask0_hides_through_the_first_line():
    """D11: the host's samples on 350 from the title's close to WATCH_TAIL_S past the guest's first ATE line: >= 3 drove the ghost,
    each by 'mask0', none shown; an option-C hide ('host_scene' -- the s161 host after its own line), a shown ghost, too few driven
    samples, no landing, no first line, each red; samples off 350 or past the tail are not judged, and a bad sample BEFORE the landed
    line was seen still counts (the window starts at the title's close: a late log flush cannot hide the s161 double)."""
    out = _child(r'''
h = lambda hide, shown=0, field=350, t=10.5: {"t": t, "field": field, "hide": hide, "shown": shown, "plain": False}
good = [h("mask0")] * 4 + [h(None, -1, 352)]
j = lambda S, tl=10.0, tf=11.0: du.judge_host_ghost(S, tl, tf)[0]
OUT = {"good": j(good), "off_field_shown_ignored": j(good + [h(None, 6, 352)]),
       "past_tail_ignored": j(good + [h("host_scene", 6, t=11.0 + du.WATCH_TAIL_S + 0.5)]),
       "option_c": j(good + [h("host_scene")]), "shown": j(good + [h(None, 6)]), "shown_and_masked": j(good + [h("mask0", 6)]),
       "shown_before_landing_seen": j(good + [h(None, 6, t=9.0)]), "landing_word": j(good + [h("landing")]),
       "vacuous": j([h("mask0")] * 2 + [h(None, -1)] * 5), "no_landing": j(good, None, 11.0), "no_first": j(good, 10.0, None),
       "min": du.MIN_DRIVEN, "tail": du.WATCH_TAIL_S}
''')
    assert out.pop("min") == 3 and out.pop("tail") == 2.0
    assert out.pop("good") and out.pop("off_field_shown_ignored") and out.pop("past_tail_ignored"), out
    assert not any(out.values()), out


def test_d12_is_green_only_on_landing_or_step_out_hides_on_the_guest():
    """D12, D11's mirror on the guest's screen: >= 3 samples on 350 drove the host's ghost, each by 'landing' or 'step_out', none
    shown. The s161 shape (the host's ghost SHOWN until the 321 OUT, hide null) and a 'mask0' / 'host_scene' hide are red; a
    despawned ghost (hide null, shown -1: the body not yet bound, or the host not here) is not judged."""
    out = _child(r'''
h = lambda hide, shown=0, field=350, t=10.5: {"t": t, "field": field, "hide": hide, "shown": shown, "plain": False}
good = [h(None, -1)] * 3 + [h("landing")] * 2 + [h("step_out")] * 3
j = lambda S, tl=10.0, tf=11.0: du.judge_guest_ghost(S, tl, tf)[0]
OUT = {"good": j(good), "all_step_out": j([h("step_out")] * 3), "all_landing": j([h("landing")] * 3),
       "s161": j([h(None, 6)] * 4 + [h("step_out")] * 4), "mask0": j(good + [h("mask0")]), "option_c": j(good + [h("host_scene")]),
       "shown_and_hidden": j(good + [h("landing", 6)]), "vacuous": j([h("landing")] * 2 + [h(None, -1)] * 9),
       "no_landing": j(good, None, 11.0), "no_first": j(good, 10.0, None)}
''')
    assert out.pop("good") and out.pop("all_step_out") and out.pop("all_landing"), out
    assert not any(out.values()), out


def test_the_duo_rows_calibrations_and_the_noland_refusal():
    """The duo: D10-D12 in its claims; COOP_CALIBRATE 1 (or anything else) = the s160 DLL (+ D10-D12), s161 = the s161 DLL (D10-D12
    alone); noland is REFUSED AT LOAD -- the module exits with the refusal before duo.py boots the pair (a selftest-role lever on a
    client guest could never be taken); D10 reuses the solo log judge, D11 / D12 the shared ghost judge over the watch's samples."""
    cases = {}
    for v in ("", "1", "s160", "s161"):
        cases[v] = _child(r'''
import inspect
mode = du.calibration()
cat = du.catalog(mode)
OUT = {"mode": mode, "cal": cat.get(du.CAL_ID), "pred": list(du.CAL_PREDICTED[mode][0]) if mode else None,
       "maybe": list(du.CAL_PREDICTED[mode][1]) if mode else None, "rows": [k for k in ("D10", "D11", "D12") if k in cat],
       "legacy_true": du.catalog(True).get(du.CAL_ID), "src_run": inspect.getsource(du._run), "src_end": inspect.getsource(du.run_duo),
       "modes": sorted(du.CAL_PREDICTED)}
''', env_cal=v)
    assert cases[""]["mode"] is None and cases[""]["cal"] is None
    assert cases["1"]["mode"] == cases["s160"]["mode"] == "s160"
    assert cases["1"]["pred"] == ["D1", "D2", "D3", "D4", "D7", "D9", "D10", "D11", "D12"] and cases["1"]["maybe"] == ["D6", "D8"]
    assert cases["1"]["legacy_true"] == cases["1"]["cal"]
    assert cases["s161"]["mode"] == "s161" and cases["s161"]["pred"] == ["D10", "D11", "D12"] and cases["s161"]["maybe"] == []
    run, end = cases["s161"]["src_run"], cases["s161"]["src_end"]
    assert "solo.landing_out(gm)" in run and "judge_host_ghost(" in run and "judge_guest_ghost(" in run
    assert "_landing_watch(d, host, guest, g1, LAND_WATCH_S)" in run and "noland" not in run and "noland" not in end
    assert "led.judge_calibration(CAL_ID, predicted, maybe=maybe)" in end
    assert all(c["rows"] == ["D10", "D11", "D12"] and c["modes"] == ["s160", "s161"] for c in cases.values())
    for v in ("noland", "NOLAND"):
        r = _run_child("OUT = {}", env_cal=v, duo=True)
        assert r.returncode == 1 and "COOP_CALIBRATE=noland is refused" in r.stderr and "COOP_CALIBRATE=s161" in r.stderr, r.stderr[-800:]
        assert "@@" not in r.stdout


def test_the_benches_match_the_engines_words():
    """The words the two benches match: the landed line (s161's NetSyncAte.OnLanding), the OUT line's ' -- ' + OutNames[why] tail
    (s158's StepOut) whose s162 word is the stand-in's last out_why key, the ATE's first locked line, the step-out release."""
    out = _child(r'''
from harness import fakegame as FG
pat = lambda n: (__import__("pathlib").Path(%r) / n).read_text(encoding="utf-8", errors="replace")
s161, s158 = pat("s161-netsync-ate-relay.patch"), pat("s158-netsync-step-out.patch")
OUT = {"landed": 'Log.Message("[NetSync] ATE relay: my copy\'s own Field(" + landed + ") landed -- the ATE plays here"' in s161,
       "bench_landed": so.LANDED == "ATE relay: my copy's own Field(350) landed",
       "out_tail": '"; the host\'s ghost hides, my wire mask is 0) -- " + OutNames[why]);' in s158,
       "ate_word": FG.NETSYNC_STEPOUT_OUT_WHY[-1] == "ate", "first": so.FIRST_LINE_LOCKED == "dialogue lock: win 4 text 321 opened locked",
       "release": FG.STEPOUT_LOG_RELEASE == so.LOG_RELEASE_STEPOUT}
''' % str(REPO / "memoria-patches"))
    assert all(out.values()), out
