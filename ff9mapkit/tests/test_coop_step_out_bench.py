"""[ff9mapkit netsync s158] THE PARTY-SCENE STEP-OUT BENCH's REPO HALF -- studies/test-harness/scenarios/coop_step_out.py.

The bench judges s158 by the `netsync.stepout` block, the mirror's visibility and control, over every publish of a stock climb
or a relayed talk. These tests pin, offline:

  * its catalog: the predicted reds of the lever calibration sit in it, the calibration rows appear only under COOP_CALIBRATE;
  * every pure judge CAN go red: an undressed OUT that hides the body, keeps the mask or the mirror, or names another start; a
    dressed OUT whose body still draws, whose shadow went with it, whose stand-in is missing, wears another model, plays a
    non-Zidane clip, trails the body or runs off its time; an IN with no debounce, too late, without its counter, or with the
    stand-in left behind; a negative that stepped out, or that never armed (vacuous), or names another reason; the lever
    marker without each of its parts;
  * the engine's words the bench matches (the base's reasons, the proof line, the release line) are the s158 patch's literals.

Every scenario-touching test runs in a CHILD process (the scenario puts its own dir on sys.path -- never this process's).
"""
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
SCEN = REPO / "studies" / "test-harness" / "scenarios"
PATCH = REPO / "memoria-patches" / "s158-netsync-step-out.patch"


def _child(code: str) -> dict:
    full = ("import json, sys\nsys.path.insert(0, %r)\nsys.path.insert(0, %r)\nimport coop_step_out as so\n" % (str(SCEN), str(REPO / "tools"))
            + code + "\nprint('@@' + json.dumps(OUT))\n")
    r = subprocess.run([sys.executable, "-X", "utf8", "-c", full], capture_output=True, text=True, cwd=str(SCEN), timeout=120)
    assert r.returncode == 0, r.stderr[-3000:]
    line = next(ln for ln in r.stdout.splitlines() if ln.startswith("@@"))
    return json.loads(line[2:])


_FIXTURES = r'''
def st(active=True, control=False, dressed=False, why="scene", wire=0, hidden=True, body=6, shadow=1, standin=None,
       why_not=None, line=False, host_ctl_off=True, my_ctl_off=None, climb=False, host_scene=True, t=None, inc=0):
    my_ctl_off = (not control) if my_ctl_off is None else my_ctl_off
    s = {"player": {"control": control},
         "netsync": {"dress": {"ghost": {"hidden": hidden}},
                     "stepout": {"active": active, "dressed": dressed, "why": why if active else None, "wire_mask": wire,
                                 "body_rends_on": body, "shadow": shadow,
                                 "standin": standin or {"on": False, "shown": False},
                                 "in_why": {"control": inc},
                                 "base": {"why_not": why_not, "line": line, "host_ctl_off": host_ctl_off,
                                          "my_ctl_off": my_ctl_off, "climb": climb, "host_scene": host_scene}}}}
    if t is not None:
        s["_t"] = t
    return s

GOOD_SI = {"on": True, "shown": True, "geo": "GEO_MAIN_F0_ZDN", "clip": "ANH_MAIN_F0_ZDN_LADDER_1_1", "dpos": 0.0,
           "norm": 0.42, "body_norm": 0.43}
def si(**kw):
    d = dict(GOOD_SI); d.update(kw); return d
def und(**kw):
    return [st(control=True, active=False, wire=31, hidden=False)] + [st(**kw) for _ in range(4)]
def drs(**kw):
    base = dict(dressed=True, body=0, standin=si())
    base.update(kw)
    return [st(control=True, active=False, wire=31, hidden=False, dressed=False)] + [st(**base) for _ in range(4)]
'''


def test_the_undressed_out_judge_can_go_red():
    out = _child(_FIXTURES + r'''
OUT = {"good": so.judge_out_undressed(und())[0],
       "never": so.judge_out_undressed(und(active=False))[0],
       "no_climb": so.judge_out_undressed([st(control=True)])[0],
       "dressed": so.judge_out_undressed(und(dressed=True))[0],
       "why_line": so.judge_out_undressed(und(why="line"))[0],
       "mask_kept": so.judge_out_undressed(und(wire=31))[0],
       "mirror_shown": so.judge_out_undressed(und(hidden=False))[0],
       "body_dark": so.judge_out_undressed(und(body=0))[0],
       "standin": so.judge_out_undressed(und(standin=si()))[0]}
''')
    assert out.pop("good") is True, out
    assert not any(out.values()), out


def test_the_dressed_out_judge_can_go_red():
    out = _child(_FIXTURES + r'''
OUT = {"good": so.judge_out_dressed(drs(), 1)[0],
       "good_no_shadow_field": so.judge_out_dressed(drs(shadow=-1), -1)[0],
       "never": so.judge_out_dressed(drs(active=False), 1)[0],
       "not_dressed": so.judge_out_dressed(drs(dressed=False), 1)[0],
       "body_draws": so.judge_out_dressed(drs(body=4), 1)[0],
       "shadow_lost": so.judge_out_dressed(drs(shadow=0), 1)[0],
       "mask_kept": so.judge_out_dressed(drs(wire=31), 1)[0],
       "mirror_shown": so.judge_out_dressed(drs(hidden=False), 1)[0],
       "no_standin": so.judge_out_dressed(drs(standin={"on": False, "shown": False}), 1)[0],
       "standin_hidden": so.judge_out_dressed(drs(standin=si(shown=False)), 1)[0],
       "wrong_geo": so.judge_out_dressed(drs(standin=si(geo="GEO_MAIN_F0_STN")), 1)[0],
       "rig_clip": so.judge_out_dressed(drs(standin=si(clip="ANH_MAIN_F0_STN_IDLE")), 1)[0],
       "trails": so.judge_out_dressed(drs(standin=si(dpos=9.0)), 1)[0],
       "off_time": so.judge_out_dressed(drs(standin=si(norm=0.1, body_norm=0.6)), 1)[0],
       "no_time": so.judge_out_dressed(drs(standin=si(norm=-1)), 1)[0],
       "wraps_ok": so.judge_out_dressed(drs(standin=si(norm=0.98, body_norm=0.02)), 1)[0]}
''')
    assert out.pop("good") is True and out.pop("good_no_shadow_field") is True and out.pop("wraps_ok") is True, out
    assert not any(out.values()), out


def test_the_in_judge_needs_the_debounce_the_counter_and_the_body():
    out = _child(_FIXTURES + r'''
b0 = {"in_why": {"control": 2}}
def after(t_in, inc=3, wire=31, hidden=False, body=6, standin=None):
    return [st(active=True, control=True, t=0.05, inc=2), st(active=True, control=True, t=t_in - 0.05, inc=2),
            st(active=False, control=True, t=t_in, inc=inc, wire=wire, hidden=hidden, body=body,
               standin=standin or {"on": False})]
OUT = {"good": so.judge_in(after(0.55), 1.0, b0, dressed=True)[0],
       "no_debounce": so.judge_in(after(0.1), 1.0, b0, dressed=False)[0],
       "too_late": so.judge_in(after(2.4), 1.0, b0, dressed=False)[0],
       "never_in": so.judge_in([st(active=True, control=True, t=0.2)], 1.0, b0, dressed=False)[0],
       "no_landing": so.judge_in(after(0.55), None, b0, dressed=False)[0],
       "no_counter": so.judge_in(after(0.55, inc=2), 1.0, b0, dressed=False)[0],
       "mask_still_0": so.judge_in(after(0.55, wire=0), 1.0, b0, dressed=False)[0],
       "mirror_hidden": so.judge_in(after(0.55, hidden=True), 1.0, b0, dressed=False)[0],
       "body_dark": so.judge_in(after(0.55, body=0), 1.0, b0, dressed=True)[0],
       "standin_left": so.judge_in(after(0.55, standin={"on": True}), 1.0, b0, dressed=True)[0]}
''')
    assert out.pop("good") is True, out
    assert not any(out.values()), out


def test_a_negative_is_never_vacuous():
    out = _child(_FIXTURES + r'''
armed = lambda s: s["netsync"]["stepout"]["base"]["climb"] is True
ok_s = [st(active=False, climb=True, why_not=so.WHY_NOT_CLIMB) for _ in range(3)]
OUT = {"good": so.judge_never(ok_s, lever=False, why_not=so.WHY_NOT_CLIMB, need=armed)[0],
       "stepped_out": so.judge_never(ok_s + [st(active=True)], lever=False, why_not=so.WHY_NOT_CLIMB, need=armed)[0],
       "vacuous": so.judge_never([st(active=False, climb=False)], lever=False, why_not=so.WHY_NOT_CLIMB, need=armed)[0],
       "other_reason": so.judge_never([st(active=False, climb=True, why_not=so.WHY_NOT_TALK)], lever=False,
                                      why_not=so.WHY_NOT_CLIMB, need=armed)[0],
       "lever_never": so.judge_never([st(active=False)], lever=True, why_not=so.WHY_NOT_CLIMB, need=armed)[0],
       "lever_out": so.judge_never([st(active=True)], lever=True, why_not=so.WHY_NOT_CLIMB, need=armed)[0]}
''')
    assert out.pop("good") is True and out.pop("lever_never") is True, out
    assert not any(out.values()), out


def test_the_lever_marker_needs_every_part():
    out = _child(_FIXTURES + r'''
good = [st(active=False, why_not=so.WHY_NOT_LEVER)]
OUT = {"good": so.off_marker(good)[0],
       "no_climb": so.off_marker([st(active=False, control=True, why_not=so.WHY_NOT_LEVER)])[0],
       "no_scene": so.off_marker([st(active=False, host_scene=False, why_not=so.WHY_NOT_LEVER)])[0],
       "active": so.off_marker(good + [st(active=True)])[0],
       "other_reason": so.off_marker([st(active=False, why_not=so.WHY_NOT_CLIMB)])[0]}
''')
    assert out.pop("good") is True, out
    assert not any(out.values()), out


def test_the_catalog_holds_the_predicted_reds():
    out = _child(r'''
plain, cal = so.catalog(False), so.catalog(True)
OUT = {"pred_in": all(p in plain for p in so.PREDICTED_OFF), "plain_cal": "K-CAL" in plain or "K-CAL-M" in plain,
       "cal_rows": "K-CAL" in cal and "K-CAL-M" in cal, "finals": all(f in cal for f in so.FINALS)}
''')
    assert out == {"pred_in": True, "plain_cal": False, "cal_rows": True, "finals": True}, out


def test_the_bench_matches_the_engines_own_words():
    """The reasons, the proof line and the release line the bench matches are the s158 patch's NetSyncStepOut literals."""
    added = "\n".join(ln[1:] for ln in PATCH.read_text(encoding="utf-8", errors="replace").splitlines()
                      if ln.startswith("+") and not ln.startswith("+++"))
    out = _child(r'''
OUT = {"words": [so.WHY_NOT_HOST_CONTROL, so.WHY_NOT_MY_CONTROL, so.WHY_NOT_CLIMB, so.WHY_NOT_TALK, so.WHY_NOT_LEVER,
                 so.LOG_RELEASE.replace("[NetSync] ", ""), "step-out selftest: ", so.STANDIN_GEO,
                 so.LOG_OUT.replace("[NetSync] ", ""), so.LOG_IN.replace("[NetSync] ", "")]}
''')
    missing = [w for w in out["words"] if w not in added]
    assert not missing, missing
