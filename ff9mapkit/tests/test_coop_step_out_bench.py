"""[ff9mapkit netsync s158] THE PARTY-SCENE STEP-OUT BENCH's REPO HALF -- studies/test-harness/scenarios/coop_step_out.py.

The bench judges s158 by the `netsync.stepout` block, the mirror's shown mask (`netsync.dress.ghost.shown_mask`, an int: the engine
publishes `hidden` as a LIST of renderer paths, never a bool -- review 2026-10-27) and control, over every publish of a stock climb that
hangs past the dwell, a short one, or a relayed talk. These tests pin, offline, with fixtures in the ENGINE's types:

  * its catalog: the predicted reds of the lever calibration sit in it, the calibration rows appear only under COOP_CALIBRATE;
  * every pure judge CAN go red: an OUT before the dwell, after it, or by another start; an undressed OUT that hides the body, keeps the
    mask or the mirror; a dressed OUT whose body still draws, whose shadow differs from stock's own switch, whose stand-in is missing,
    wears another model, plays a non-Zidane clip, never plays a ladder clip mid-ladder, holds one clip time, trails the body or runs
    off its time; an IN with no debounce, too late, without its counter, with the body dark past a logic tick, or the stand-in left
    behind; a negative that stepped out, or that never armed (vacuous), or names another reason; a short climb that stepped out (and a
    long one never green); the lever marker without each of its parts;
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
LAD = {"mount_bottom": (115, -9, 161), "mount_top": (284, -269, 203), "lo": -269, "hi": -9}
MID = (200.0, 139.0, 182.0)     # on 207's ladder path, mid-height in the published frame (y negated by gt.pos)
def st(active=True, control=False, dressed=False, why="dwell", wire=0, shown=0, body=6, shadow=1, shadow_off=0, stock_visible=True,
       standin=None, why_not=None, line=False, host_ctl_off=True, my_ctl_off=None, climb=False, talk=False, t=None, inc=0, pos=None,
       age=-1):
    my_ctl_off = (not control) if my_ctl_off is None else my_ctl_off
    s = {"player": {"control": control},
         "netsync": {"dress": {"ghost": {"shown_mask": shown, "hidden": [] if shown else ["a/b"]}},
                     "stepout": {"active": active, "dressed": dressed, "why": why if active else None, "wire_mask": wire,
                                 "body_rends_on": body, "shadow": shadow, "shadow_off": shadow_off, "stock_visible": stock_visible,
                                 "standin": standin or {"on": False, "shown": False},
                                 "in_why": {"control": inc},
                                 "base": {"why_not": why_not, "line": line, "host_ctl_off": host_ctl_off,
                                          "my_ctl_off": my_ctl_off, "climb": climb, "talk": talk, "age_ms": age}}}}
    if pos is not None:
        s["player"].update(x=pos[0], y=pos[1], z=pos[2])
    if t is not None:
        s["_t"] = t
    return s

GOOD_SI = {"on": True, "shown": True, "geo": "GEO_MAIN_F0_ZDN", "clip": "ANH_MAIN_F0_ZDN_LADDER_1_2", "dpos": 3.0,
           "norm": 0.42, "body_norm": 0.43}
def si(**kw):
    d = dict(GOOD_SI); d.update(kw); return d
def seq(make, n=4, t_out=1.6):
    """control off at 0.2, OUT from t_out on: a rest sample, two control-off samples before the OUT, then n OUT samples"""
    rows = [st(control=True, active=False, wire=31, shown=31, t=0.0, why_not="I have control"),
            st(active=False, wire=31, shown=31, t=0.2, why_not=None), st(active=False, wire=31, shown=31, t=1.0, why_not=None)]
    for k in range(n):
        rows.append(make(k, t_out + 0.05 * k))
    return rows
def und(**kw):
    return seq(lambda k, t: st(t=t, **kw))
def drs(n=4, **kw):
    def mk(k, t):
        base = dict(dressed=True, body=0, standin=si(norm=0.1 + 0.2 * k, body_norm=0.1 + 0.2 * k), t=t, pos=MID)
        base.update(kw)
        if "standin" in kw and kw["standin"] is not None and "norm" not in kw["standin"]:
            base["standin"] = dict(kw["standin"], norm=0.1 + 0.2 * k, body_norm=0.1 + 0.2 * k)
        return st(**base)
    return seq(mk, n)
'''


def test_the_dwell_judge_wants_the_dwell_and_nothing_sooner():
    out = _child(_FIXTURES + r'''
OUT = {"good": so.judge_dwell(und())[0],
       "too_soon": so.judge_dwell(seq(lambda k, t: st(t=t), t_out=0.9))[0],
       "too_late": so.judge_dwell(seq(lambda k, t: st(t=t), t_out=3.0))[0],
       "by_line": so.judge_dwell(und(why="line"))[0],
       "never": so.judge_dwell(und(active=False))[0]}
''')
    assert out.pop("good") is True, out
    assert not any(out.values()), out


def test_the_undressed_out_judge_can_go_red():
    out = _child(_FIXTURES + r'''
OUT = {"good": so.judge_out_undressed(und())[0],
       "never": so.judge_out_undressed(und(active=False))[0],
       "no_climb": so.judge_out_undressed([st(control=True)])[0],
       "dressed": so.judge_out_undressed(und(dressed=True))[0],
       "mask_kept": so.judge_out_undressed(und(wire=31))[0],
       "mirror_shown": so.judge_out_undressed(und(shown=31))[0],
       "no_mirror": so.judge_out_undressed(und(shown=-1))[0],
       "body_dark": so.judge_out_undressed(und(body=0))[0],
       "standin": so.judge_out_undressed(und(standin=si()))[0],
       "too_soon": so.judge_out_undressed(seq(lambda k, t: st(t=t), t_out=0.9))[0]}
''')
    assert out.pop("good") is True, out
    assert not any(out.values()), out


def test_the_dressed_out_judge_can_go_red():
    out = _child(_FIXTURES + r'''
G = lambda rows: so.judge_out_dressed(rows, 1, LAD)[0]
OUT = {"good": G(drs()),
       "good_shadow_off_by_stock": G(drs(shadow=0, shadow_off=1)),
       "good_no_shadow_field": so.judge_out_dressed(drs(shadow=-1, shadow_off=-1), -1, LAD)[0],
       "never": G(drs(active=False)),
       "not_dressed": G(drs(dressed=False)),
       "body_draws": G(drs(body=4)),
       "shadow_lost": G(drs(shadow=0, shadow_off=0)),
       "shadow_kept_when_stock_hid_it": G(drs(shadow=1, shadow_off=1)),
       "mask_kept": G(drs(wire=31)),
       "mirror_shown": G(drs(shown=31)),
       "no_standin": G(drs(standin={"on": False, "shown": False})),
       "standin_hidden": G(drs(standin=si(shown=False))),
       "wrong_geo": G(drs(standin=si(geo="GEO_MAIN_F0_STN"))),
       "rig_clip": G(drs(standin=si(clip="ANH_MAIN_F0_STN_IDLE"))),
       "idle_on_the_ladder": G(drs(standin=si(clip="ANH_MAIN_F0_ZDN_IDLE"))),
       "mount_clip_on_the_ladder": G(drs(standin=si(clip="ANH_MAIN_F0_ZDN_LADDER_1_1"))),
       "trails": G(drs(standin=si(dpos=120.0))),
       "off_time": G([r if i < 3 else dict(r, netsync=dict(r["netsync"], stepout=dict(r["netsync"]["stepout"],
                      standin=dict(r["netsync"]["stepout"]["standin"], norm=0.9)))) for i, r in enumerate(drs())]),
       "frozen_time": G([r if i < 3 else dict(r, netsync=dict(r["netsync"], stepout=dict(r["netsync"]["stepout"],
                         standin=dict(r["netsync"]["stepout"]["standin"], norm=0.42, body_norm=0.42)))) for i, r in enumerate(drs())]),
       "no_time": G(drs(standin=si(norm=-1))),
       "too_soon": G(seq(lambda k, t: st(dressed=True, body=0, standin=si(norm=0.1 * k, body_norm=0.1 * k), t=t, pos=MID), t_out=0.9))}
''')
    for k in ("good", "good_shadow_off_by_stock", "good_no_shadow_field"):
        assert out.pop(k) is True, (k, out)
    assert not any(out.values()), out


def test_the_in_judge_needs_the_debounce_the_counter_and_the_body_after_a_tick():
    out = _child(_FIXTURES + r'''
b0 = {"in_why": {"control": 2}}
def after(t_in, inc=3, wire=31, shown=31, body=6, standin=None, body_first=None):
    rows = [st(active=True, control=True, t=0.05, inc=2), st(active=True, control=True, t=t_in - 0.05, inc=2)]
    dark_first = body_first is not None                  # the first IN publish before the relight: mask, mirror and body all dark
    rows.append(st(active=False, control=True, t=t_in, inc=inc, wire=0 if dark_first else wire, shown=0 if dark_first else shown,
                   body=body_first if dark_first else body, standin=standin or {"on": False}))
    rows.append(st(active=False, control=True, t=t_in + 0.3, inc=inc, wire=wire, shown=shown, body=body, standin=standin or {"on": False}))
    return rows
OUT = {"good": so.judge_in(after(0.55), 1.0, b0, dressed=True)[0],
       "good_relit_a_tick_later": so.judge_in(after(0.55, body_first=0), 1.0, b0, dressed=True)[0],
       "no_debounce": so.judge_in(after(0.1), 1.0, b0, dressed=False)[0],
       "too_late": so.judge_in(after(2.4), 1.0, b0, dressed=False)[0],
       "never_in": so.judge_in([st(active=True, control=True, t=0.2)], 1.0, b0, dressed=False)[0],
       "no_landing": so.judge_in(after(0.55), None, b0, dressed=False)[0],
       "no_counter": so.judge_in(after(0.55, inc=2), 1.0, b0, dressed=False)[0],
       "mask_still_0": so.judge_in(after(0.55, wire=0), 1.0, b0, dressed=False)[0],
       "mirror_hidden": so.judge_in(after(0.55, shown=0), 1.0, b0, dressed=False)[0],
       "body_dark_past_a_tick": so.judge_in(after(0.55, body=0), 1.0, b0, dressed=True)[0],
       "standin_left": so.judge_in(after(0.55, standin={"on": True}), 1.0, b0, dressed=True)[0]}
''')
    assert out.pop("good") is True and out.pop("good_relit_a_tick_later") is True, out
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


def test_a_short_climb_never_steps_out_and_a_long_one_is_never_green():
    out = _child(_FIXTURES + r'''
short = [st(control=True, active=False, t=0.0), st(active=False, t=0.2, age=300), st(active=False, t=1.1, age=900),
         st(control=True, active=False, t=1.3)]
long_ = [st(control=True, active=False, t=0.0), st(active=False, t=0.2, age=300), st(active=False, t=1.9, age=1450),
         st(control=True, active=False, t=2.0)]
never_armed = [st(control=True, active=False, t=0.0), st(active=False, t=0.4, age=-1), st(control=True, active=False, t=0.9)]
OUT = {"good": so.judge_short(short)[0],
       "stepped_out": so.judge_short(short[:2] + [st(active=True, t=1.1)] + short[3:])[0],
       "long": so.judge_short(long_)[0],
       "never_armed": so.judge_short(never_armed)[0],
       "lever_never_armed_is_green": so.judge_short(never_armed, lever=True)[0],
       "lever_stepped_out": so.judge_short(short[:2] + [st(active=True, t=1.1)] + short[3:], lever=True)[0],
       "no_climb": so.judge_short([st(control=True, active=False, t=0.0)])[0]}
''')
    assert out == {"good": True, "stepped_out": False, "long": None, "never_armed": False, "lever_never_armed_is_green": True,
                   "lever_stepped_out": False, "no_climb": False}, out


def test_the_debounce_shadow_judge_can_fail():
    """THE SHADOW where a dark-term leak shows: the step-in debounce, stock's switch back on (two samples) -- drawn, or red."""
    out = _child(_FIXTURES + r'''
deb = lambda shadow, off=0: [st(active=True, control=True, shadow=shadow, shadow_off=off, t=0.1 * k) for k in range(4)]
OUT = {"good": so.judge_shadow_debounce(deb(1), 1)[0],
       "leaked_dark": so.judge_shadow_debounce(deb(0), 1)[0],
       "vacuous": so.judge_shadow_debounce(deb(0, off=1), 1)[0],
       "no_shadow_field": so.judge_shadow_debounce(deb(-1, off=-1), -1)[0]}
''')
    assert out == {"good": True, "leaked_dark": False, "vacuous": False, "no_shadow_field": True}, out


def test_the_lever_marker_needs_every_part():
    out = _child(_FIXTURES + r'''
good = [st(active=False, why_not=so.WHY_NOT_LEVER, t=0.2), st(active=False, why_not=so.WHY_NOT_LEVER, t=2.0)]
OUT = {"good": so.off_marker(good)[0],
       "short": so.off_marker([st(active=False, why_not=so.WHY_NOT_LEVER, t=0.2), st(active=False, why_not=so.WHY_NOT_LEVER, t=0.6)])[0],
       "no_climb": so.off_marker([st(active=False, control=True, why_not=so.WHY_NOT_LEVER, t=0.0)])[0],
       "active": so.off_marker(good + [st(active=True, t=2.1)])[0],
       "other_reason": so.off_marker([st(active=False, why_not=so.WHY_NOT_CLIMB, t=0.2), st(active=False, why_not=so.WHY_NOT_CLIMB, t=2.0)])[0]}
''')
    assert out.pop("good") is True, out
    assert not any(out.values()), out


def test_the_mirror_witness_reads_the_engines_int_mask_never_a_bool():
    out = _child(_FIXTURES + r'''
OUT = {"hidden": so.mirror_hidden(st(shown=0)), "shown": so.mirror_shown(st(shown=7)),
       "bool_is_not_a_mask": so.mirror_mask({"netsync": {"dress": {"ghost": {"shown_mask": True}}}}),
       "no_ghost_not_hidden": so.mirror_hidden(st(shown=-1)), "no_ghost_not_shown": so.mirror_shown(st(shown=-1))}
''')
    assert out == {"hidden": True, "shown": True, "bool_is_not_a_mask": None, "no_ghost_not_hidden": False,
                   "no_ghost_not_shown": False}, out


def test_the_catalog_holds_the_predicted_reds():
    out = _child(r'''
plain, cal = so.catalog(False), so.catalog(True)
OUT = {"pred_in": all(p in plain for p in so.PREDICTED_OFF), "plain_cal": "K-CAL" in plain or "K-CAL-M" in plain,
       "cal_rows": "K-CAL" in cal and "K-CAL-M" in cal, "finals": all(f in cal for f in so.FINALS),
       "dwell_window_brackets_the_engine": so.DWELL_MIN_S < 1.5 < so.DWELL_MAX_S and so.NDWELL_MAX_S < 1.5,
       "hang_past_the_dwell": so.HANG_S > 1.5}
''')
    assert out == {"pred_in": True, "plain_cal": False, "cal_rows": True, "finals": True,
                   "dwell_window_brackets_the_engine": True, "hang_past_the_dwell": True}, out


def test_the_bench_matches_the_engines_own_words():
    """The reasons, the proof line, the release line, the stand-in's model and the dwell the bench matches are the s158 patch's
    NetSyncStepOut literals."""
    added = "\n".join(ln[1:] for ln in PATCH.read_text(encoding="utf-8", errors="replace").splitlines()
                      if ln.startswith("+") and not ln.startswith("+++"))
    out = _child(r'''
OUT = {"words": [so.WHY_NOT_HOST_CONTROL, so.WHY_NOT_MY_CONTROL, so.WHY_NOT_CLIMB, so.WHY_NOT_TALK, so.WHY_NOT_LEVER,
                 so.LOG_RELEASE.replace("[NetSync] ", ""), "step-out selftest: ", so.STANDIN_GEO,
                 so.LOG_OUT.replace("[NetSync] ", ""), so.LOG_IN.replace("[NetSync] ", ""),
                 'OutNames = { null, "line", "dwell" }', "internal const Int32 DwellMs = 1500;", "internal const Int32 StepInMs = 500;"]}
''')
    missing = [w for w in out["words"] if w not in added]
    assert not missing, missing


# ================================================================================================ [ff9mapkit netsync s159] THE ANCHOR
_M352 = r'''
def ma(active=True, uid=17, dressed=True, body=0, ctl=19, dressed_uid=17, ctl_rends=5, wire=0, shown=0, standin=None, why="dwell",
       ctl_elsewhere=1, ce_field=352, field=352, why_not=None):
    s = st(active=active, dressed=dressed, why=why, wire=wire, shown=shown, body=body, standin=standin or GOOD_SI, why_not=why_not)
    s["netsync"]["stepout"]["uid"] = uid if active else -1
    s["netsync"]["stepout"]["anchor"] = {"uid": uid, "ctl_uid": ctl, "dressed_uid": dressed_uid, "ctl_rends_on": ctl_rends}
    s["netsync"]["dress"]["self"] = {"ctl_elsewhere": ctl_elsewhere, "ctl_elsewhere_field": ce_field}
    s["field"] = {"id": field}                   # the engine publishes `field` as a block (gt.field_of)
    return s
def run(**kw):
    rows = [ma(active=False, why_not=None)] + [ma(**kw) for _ in range(4)]
    return so.judge_m352(rows)[0]
'''


def test_the_m352_judge_can_go_red_on_each_part():
    """M-352 is green only when every OUT sample acts on the DRESSED body (not the controlled one), dark, with a ZDN stand-in shown,
    the controlled actor lit, the mask 0 and the mirror hidden -- and red when it never steps out."""
    out = _child(_FIXTURES + _M352 + r'''
bad_si = dict(GOOD_SI); bad_si["geo"] = "GEO_MAIN_F0_STN"
OUT = {"good": run(), "on_ctl": run(uid=19), "undressed": run(dressed=False), "body_lit": run(body=4),
       "ctl_dark": run(ctl_rends=0), "ctl_none": run(ctl_rends=-1), "mask": run(wire=31), "mirror": run(shown=31),
       "wrong_standin": run(standin=bad_si), "same_body": run(ctl=17), "never": so.judge_m352([ma(active=False)] * 3)[0]}
''')
    assert out == {"good": True, "on_ctl": False, "undressed": False, "body_lit": False, "ctl_dark": False, "ctl_none": False,
                   "mask": False, "mirror": False, "wrong_standin": False, "same_body": False, "never": False}, out


def test_the_m352_precondition_and_the_anchor_marker_can_fail():
    """d3_shape needs 352, a NEW ctl_elsewhere there and two different bodies; the anchor calibration's marker needs an OUT on the
    controlled actor, undressed, on every out sample."""
    out = _child(_FIXTURES + _M352 + r'''
f = lambda **kw: so.d3_shape(ma(**kw), 352, 0)
mk = lambda **kw: so.ctl_marker([ma(active=False)] + [ma(**kw)] * 3)[0]
OUT = {"shape": f(), "old_ce": so.d3_shape(ma(), 352, 1), "other_field": f(ce_field=351), "same": f(ctl=17),
       "no_ctl": f(ctl=-1), "not_here": f(field=351),
       "marker": mk(uid=19, dressed=False), "marker_dressed": mk(uid=19, dressed=True), "marker_anchor": mk(uid=17, dressed=False),
       "marker_never": so.ctl_marker([ma(active=False)] * 3)[0]}
''')
    assert out == {"shape": True, "old_ce": False, "other_field": False, "same": False, "no_ctl": False, "not_here": False,
                   "marker": True, "marker_dressed": False, "marker_anchor": False, "marker_never": False}, out


def test_the_m352_leg_never_waits_for_control_and_clears_the_latch():
    """M-352 reaches the night scene by a RAW warp step (Session.warp waits for control the scene never gives), after clearing
    VAR_GlobBool_158 (the real path's latch: set, 352's Main_Init EnableMoves and the step-out never starts), and ends its episode
    on the off lever, witnessed -- never a warp back whose verdict is dropped."""
    out = _child(r'''
import inspect
src = inspect.getsource(so._field_352)
OUT = {"raw": 'cb.try_send(g, f"warp {M352_FIELD} {M352_ENTRANCE} {M352_SCENARIO}")' in src, "no_warp": "g.warp(" not in src,
       "latch": "g.flag(M352_LATCH, False)" in src and so.M352_LATCH == 158,
       "latch_first": src.index("g.flag(M352_LATCH, False)") < src.index("cb.try_send(g, f\"warp"),
       "ends": '_ns(g, "stepout", "off")' in src and "_arrive(" not in src}
''')
    assert out == {"raw": True, "no_warp": True, "latch": True, "latch_first": True, "ends": True}, out


def test_the_anchor_calibration_predicts_m352_alone():
    """COOP_CALIBRATE=anchor: K-CAL / K-CAL-M name M-352 alone; the off lever's predicted reds gain M-352 (never out there either)."""
    out = _child(r'''
OUT = {"ctl": so.catalog(False, True)["K-CAL"], "off": so.catalog(True)["K-CAL"], "pred": list(so.PREDICTED_CTL),
       "off_has": "M-352" in so.PREDICTED_OFF, "claim": "M-352" in so.CLAIMS, "where": [so.M352_FIELD, so.M352_ENTRANCE, so.M352_SCENARIO]}
''')
    assert out["pred"] == ["M-352"] and out["ctl"].endswith("exactly M-352 red") and out["off_has"] and out["claim"]
    assert "M-352" in out["off"] and out["where"] == [352, 3, 2505], out
