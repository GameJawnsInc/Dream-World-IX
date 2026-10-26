"""[ff9mapkit netsync s154] THE FOLLOW-RACE BENCH's pure judges -- studies/test-harness/scenarios/coop_follow_race_duo.py.

The duo bench judges each race on the OBSERVED order of edges in the guest's own state stream (the critique's law: dgame
alone cannot make s153 red). These tests feed its judges a FRAME-LEVEL STAND-IN of that stream -- a guest whose own faded
warp (Ff9mkDebugMenu's 0.9 s game-time timer) and follow-warp (NetSyncClient's 0.9 s timer) both spend Unity's
deltaTime, whose scene change shows as the _Fade's IsFading frames, and whose engine is either s153 (the commit is blind:
wiped before the new field's init, a reload after it) or s154 (the commit guard drops a commit while a scene change is
committed and its init has not run -- attr & 8 stays set until then -- and re-arms; the landing step cancels a pending
follow). The stand-in runs in ENGINE ORDER [ff9mapkit netsync s154]: IsFading falls FIRST and the new field's init (s154's
landing step, the per-load dress counter's tick) runs one or more frames LATER, optionally on a long init frame -- so a
published sample reads landed with the pending still set, on both engines.

THE CLOCK LAW [ff9mapkit netsync s154] (the s153 calibration run 20261026-121127-duo-s154-follow-cal153): the stand-in's
level-load frame spends ONE nominal frame of game time (Unity's post-load delta), not its wall stall -- the bench's old
single clock counted the stall in full, so every FD attempt there read the pending's fall 0.35-0.5 s "late" ('mismatch')
and FS's aim landed the commit past 250's init on two of three attempts. Its sampler can MISS frames: a same-field
reload's fade pulse (``hide``) and every other frame (``every``), as the run's did, so the reload's only trace is the
load's stall. The run-shaped rows below are built from that run's measured numbers (the FD attempt 3 dgame 0.818 and its
0.403 s shutdown stall; the FS strand/hard-cut split at dgame ~0.13; one ghost line per double load).

  * an s153-shaped strand is REACHED (in-load: the pending down before 250's init post-witness, the fall on the timer) and
    reads FS-a / FS-b RED, the shutdown seen by its fade or -- as on the run -- only by the load's stall; the same race on
    s154 reads them GREEN; a commit past the init (s153's hard cut), before the shutdown, or overwriting the guest's own
    warp is UNREACHED, never judged;
  * an s153-shaped double load is REACHED (after-landing on the conservative clock, the fall on the timer's interval,
    the load witnessed by the dress counter) and reads FD-a / FD-b RED -- FD-a even with the second load's fade pulse
    unsampled and one ghost line; on s154 the pending falls at the landing's init (the landing step) and reads them GREEN,
    with the pre-init sample present, with a zero-tick frame before the init and with a long init frame (THE INIT LAG);
  * the clock's interval holds the engine's own game time on every sample, and the old single clock is its upper bound;
  * the ordinary follow (FE) passes on one load and one ghost line, measures the follow's timer straddling 0.9 s, and
    fails on a second load or an s154 line;
  * the calibration judge: an s153-shaped ledger passes, an s154-shaped one (all green) fails, an s154 line fails it, an
    unreached leg is excluded and named, and nothing reached fails.

Every call runs in a CHILD process (the scenario puts its own dir and tools/ on sys.path, and reads COOP_CALIBRATE at import).
"""
import json
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCENARIOS = REPO / "studies" / "test-harness" / "scenarios"
TOOLS = REPO / "tools"
MODULE = "coop_follow_race_duo"
HOME, AWAY = 250, 30602

_CHILD = r'''
import importlib.util, json, os, sys
scen, tools = sys.argv[1], sys.argv[2]
doc = json.loads(sys.stdin.read())
for k, v in (doc.get("env") or {}).items():
    os.environ[k] = v
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("bench_under_test", os.path.join(scen, doc["module"] + ".py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
out = []
for c in doc["calls"]:
    try:
        fn = getattr(m, c["fn"])
        val = fn(*c.get("args", []), **c.get("kwargs", {})) if callable(fn) else fn
        out.append({"ok": True, "value": val})
    except Exception as e:
        out.append({"ok": False, "error": repr(e)})
print(json.dumps({"results": out}, default=lambda o: sorted(o) if isinstance(o, (set, frozenset)) else repr(o)))
'''


def call(*calls, env=None):
    """Run ``calls`` ([fn, args, kwargs]) against the bench module in a child process; return each value."""
    doc = {"module": MODULE, "env": dict(env or {"COOP_CALIBRATE": ""}),
           "calls": [{"fn": c[0], "args": list(c[1]) if len(c) > 1 else [], "kwargs": dict(c[2]) if len(c) > 2 else {}}
                     for c in calls]}
    p = subprocess.run([sys.executable, "-c", _CHILD, str(SCENARIOS), str(TOOLS)], input=json.dumps(doc),
                       capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr[-3000:]
    res = json.loads(p.stdout.strip().splitlines()[-1])["results"]
    for r, c in zip(res, calls):
        assert r["ok"], f"{c[0]}: {r.get('error')}"
    return [r["value"] for r in res]


# ------------------------------------------------------------------------------------------------ the stand-in
DT = 1.0 / 60.0
GHOST = "[NetSync] ghost spawned as GEO_MAIN_F0_ZDN on field {} (ui=FieldHUD)"
DRESS = "[NetSync] self-dress: field {} uid 1 sid 1: Zidane (98) -> GEO_NPC_F0_MOG (model 220, rig 8, eye -200) [host]"


def simulate(engine, leg, dgame, load_s, *, after_s=12.0, timer_s=0.9, own=True, step_k=4, init_s=0.0, post_k=0,
             reset=True, consume_k=0, hide=(), hide_all=False, every=1, dress=True, ctl_k=2, ghosts="each"):
    """The guest's stream, frame by frame, in ENGINE ORDER. Per frame: the debug menu's Update (the guest's own warp timer),
    NetSyncClient's Update (StartFollowWarp / ServiceFollowWarp), then the field's HonoUpdate (a committed scene change's
    consumption ``consume_k`` frames after its commit, the load's frames, the init), then the publish. A load's frames, k
    from its consumption: k 0 the shutdown (fldMapNo = nextMapNo, IsFading), k 1 the synchronous level load (``load_s``
    of WALL time; with ``reset`` -- Unity's post-load delta -- one nominal frame of GAME time), k 2 the fade-in, k 3
    IsFading FALLS (landed: FieldHUD, the target, fading false -- the init has NOT run), and at k ``step_k`` +
    ``post_k`` the new field's init (HonoUpdate's first pass: the wipe, s154's landing step, Main_Init's SetModel = the
    dress counter + its 'self-dress' line), that frame spending ``init_s`` more wall (its synchronous field load); control
    comes back ``ctl_k`` frames later. A follow commit while a committed change has not reached its init: s153 before the
    consumption OVERWRITES the target, after it is wiped by the init; s154 drops it (attr & 8 until the init) and re-arms.
    ``own``: the guest's own warp starts at frame 30 at timescale 0.1, the follow ``dgame`` of game time later, the switch
    to 1 three frames after it (published on its own frame, which still spent the old scale); ``own`` False: an ordinary
    follow at timescale 1. The sampler drops k in ``hide`` of the guest's own load (of every load with ``hide_all``) and
    keeps one frame in ``every``. ``eng`` on each row is the engine's own game clock (for the clock tests).
    -> (rows, ghost / self-dress lines, the own warp's send time)."""
    assert step_k >= 4, "the init runs after IsFading falls (k 3)"
    own_target = HOME if leg == "FS" else AWAY
    init_k = step_k + post_k
    st = {"field": HOME, "fading": False, "ui": "FieldHUD", "control": True, "pending": -1, "warped_to": -1}
    rows, msgs = [], []
    t, ts, eng = 1000.0, (0.1 if own else 1.0), 0.0
    fw = 30
    fr = fw + int(round(dgame * 60.0 / 0.1)) if own else 20
    fsw = fr + 3
    t_send = t + (fw - 0.5) * DT if own else t + 5 * DT
    own_timer = fol_timer = None
    load = pend = None
    rearm_at = ctl_at = None
    n_dress = 10
    away_landings = 0
    for f in range(fsw + int(after_s * 60) + 120):
        k0 = f - load["start"] if load is not None else None
        dt = DT + (load_s if k0 == 1 else 0.0) + (init_s if k0 == init_k else 0.0)
        if f:
            t += dt
        gdt = (DT if (reset and k0 == 1) else min(dt, 1.0 / 3.0)) * ts
        if f:
            eng += gdt
        # Ff9mkDebugMenu.Update: the guest's own faded warp (control off, the 0.9 s timer, then SetNextMap + attr |= 8)
        if own and f == fw:
            st["control"] = False
            own_timer = 0.9
        elif own_timer is not None:
            own_timer -= gdt
            if own_timer <= 0:
                own_timer = None
                pend = {"at": f + consume_k, "target": own_target, "own": True, "rearm": False}
        # NetSyncClient.Update: StartFollowWarp / ServiceFollowWarp
        if f == fr or (rearm_at is not None and f == rearm_at and st["field"] != AWAY):
            st.update(pending=AWAY, warped_to=AWAY, control=False)
            fol_timer = timer_s
            rearm_at = None
        elif fol_timer is not None:
            fol_timer -= gdt
            if fol_timer <= 0:                                # the commit
                fol_timer = None
                st["pending"] = -1
                kc = f - load["start"] if load is not None else None
                if pend is not None or (kc is not None and kc <= init_k):   # a committed change, its init not yet run
                    if engine == "s154":                      # the commit guard: drop, void the latch, re-arm
                        st["warped_to"] = -1
                        (pend if pend is not None else load)["rearm"] = True
                    elif pend is not None:                    # s153: SetNextMap before the consumption overwrites it
                        pend["target"] = AWAY
                    # s153 inside a load: written, then wiped by the new field's init
                else:                                         # a quiet field: written (both engines)
                    st["control"] = False
                    pend = {"at": f + consume_k, "target": AWAY, "own": False, "rearm": False}
        # HonoluluFieldMain.HonoUpdate: the consumption, the load's frames, the init
        if pend is not None and load is None and f >= pend["at"]:
            load = {"start": f, "target": pend["target"], "own": pend["own"], "rearm": pend["rearm"]}
            pend = None
        hidden = False
        if load is not None:
            k = f - load["start"]
            hidden = (hide_all or load["own"]) and k in hide
            if k == 0:                                        # the shutdown
                st.update(fading=True, field=load["target"])
            elif k < 3:                                       # the level load, the fade-in
                st["fading"] = True
            elif k == 3:                                      # IsFading falls: landed, NOT yet inited
                st["fading"] = False
                if load["target"] == AWAY:
                    away_landings += 1
                    if ghosts == "each":
                        msgs.append(GHOST.format(AWAY))
            if k == init_k:                                   # the init (HonoUpdate's first pass)
                if engine == "s154" and st["pending"] >= 0:   # the landing step: Arrived / Superseded
                    if st["pending"] != load["target"]:
                        load["rearm"] = True
                    st["pending"] = -1
                    fol_timer = None
                if dress:                                     # Main_Init's SetModel: the per-load dress counter
                    n_dress += 1
                    msgs.append(DRESS.format(load["target"]))
                ctl_at = f + ctl_k
                if load["rearm"]:
                    rearm_at = f + 2
                load = None
        if ctl_at is not None and f == ctl_at:
            ctl_at = None
            if fol_timer is None and st["pending"] < 0 and pend is None and load is None:
                st["control"] = True
        if own and f == fsw:                                  # the switch: published now, spent from the next frame
            ts = 1.0
        overlay = "peer_elsewhere" if st["field"] != AWAY and st["warped_to"] == AWAY and st["pending"] < 0 else None
        if not hidden and f % every == 0:
            rows.append(dict(t=round(t, 6), frame=f, ts=ts, overlay=overlay, mirroring=True,
                             dress=n_dress if dress else None, eng=round(eng, 6), **st))
    if ghosts == "once" and away_landings:                    # the run: the ghost spawns once the host is there
        msgs.append(GHOST.format(AWAY))
    return rows, msgs, t_send


def race(engine, leg, dgame, load_s, **kw):
    rows, msgs, t_send = simulate(engine, leg, dgame, load_s, **kw)
    own_target = HOME if leg == "FS" else AWAY
    order, = call(("race_order", [rows], {"dest": AWAY, "own_target": own_target, "t_own_send": t_send}))
    return rows, msgs, order


#: [ff9mapkit netsync s154] The s153 calibration run's shape: its load stalls (0.40-0.53 s), its sampler (every other
#: frame, the reload's fade pulse missed), the consumption a logic tick after the commit, one ghost line per double load.
RUN = {"consume_k": 1, "hide": (0, 1, 2), "every": 2}


# ------------------------------------------------------------------------------------------------ the clock
def test_game_clock_spends_the_earlier_timescale_and_caps_the_load_frame():
    rows = [dict(t=0.0, frame=0, ts=0.1), dict(t=1.0, frame=60, ts=0.1), dict(t=1.0 + 1 / 60, frame=61, ts=1.0),
            dict(t=3.0, frame=62, ts=1.0), dict(t=3.5, frame=92, ts=1.0)]
    g, (lo, hi) = call(("game_clock", [rows]), ("game_bounds", [rows]))
    assert g == hi
    assert abs(g[1] - 0.1) < 1e-9                       # 1 s real at 0.1
    assert abs(g[2] - g[1] - 0.1 / 60) < 1e-9           # the switch frame still spent the OLD timescale
    assert abs(g[3] - g[2] - 1.0 / 3.0) < 1e-9          # a 2 s load frame: hi counts Unity's 1/3 s cap ...
    assert abs(lo[3] - lo[2] - 1.0 / 90.0) < 1e-9       # ... lo one frame at the floor (THE CLOCK LAW)
    assert abs(g[4] - g[3] - 0.5) < 1e-9 and abs(lo[4] - lo[3] - 0.5) < 1e-9   # an ordinary gap: both alike


@pytest.mark.parametrize("reset", [True, False])
@pytest.mark.parametrize("kw", [{}, RUN])
def test_the_clock_interval_holds_the_engine_game_time(reset, kw):
    # the engine's own clock lies inside [lo, hi] on every sample, whatever Unity spends on the load frame
    rows, _msgs, _t = simulate("s153", "FD", 0.818, 0.403, reset=reset, **kw)
    lo, hi = call(("game_bounds", [rows]))[0]
    for j, r in enumerate(rows):
        e = r["eng"] - rows[0]["eng"]
        assert lo[j] <= e + 1e-6 and e <= hi[j] + 1e-6, (j, lo[j], e, hi[j])
    if reset:                                           # the old single clock (hi) overcounts the load by its stall
        assert hi[-1] - (rows[-1]["eng"] - rows[0]["eng"]) > 0.3


def test_offset_and_latency_are_inverse_and_aims_stay_in_range():
    o, lat, fs, fd, fs_wide, fd_max, fs_lo, fs_hi, margin = call(
        ("offset_for", [0.09, 0.05]), ("implied_lat", [-0.05, 0.09]), ("first_target", ["FS"]), ("first_target", ["FD"]),
        ("first_target", ["FS", 0.9]), ("FD_MAX_G",), ("FS_MIN_G",), ("FS_MAX_G",), ("FD_MARGIN_G",))
    assert abs(o - (-0.05)) < 1e-9 and abs(lat - 0.05) < 1e-9
    assert fs_lo <= fs <= fs_hi < 0.2                   # FS: a few frames past the guest's own commit, never mid-wall-stall
    assert fs_wide == fs                                # FE's measured wall window no longer moves the aim
    assert margin <= fd <= fd_max < 0.9                 # FD: late, but the follow still starts before the own commit


# ------------------------------------------------------------------------------------------------ FS, the strand
def test_fs_s153_strand_is_reached_and_red():
    rows, msgs, order = race("s153", "FS", 0.05, 0.15, post_k=4)
    assert order["order"] == "in-load" and order["fall"] == "timer" and order["consistent"], order["why"]
    assert order["shut_by"] == "fade" and order["post_by"] == "dress", order["why"]
    reached, j = call(("reached", ["FS", order]), ("judge_strand", [rows, order], {"dest": AWAY, "host_field": AWAY}))
    assert reached
    assert j["a"][0] is False, j["a"]                   # stranded on 250
    assert j["b"][0] is False, j["b"]                   # pending -1, warped_to 30602, off 30602


@pytest.mark.parametrize("post_k,init_s", [(4, 0.0), (6, 0.15)])
def test_fs_s154_same_race_is_reached_and_green(post_k, init_s):
    rows, msgs, order = race("s154", "FS", 0.05, 0.15, post_k=post_k, init_s=init_s)
    assert order["order"] == "in-load" and order["consistent"], order["why"]
    assert call(("reached", ["FS", order]))[0]
    j, = call(("judge_strand", [rows, order], {"dest": AWAY, "host_field": AWAY}))
    assert j["a"][0] is True, j["a"]
    assert j["b"][0] is True, j["b"]


@pytest.mark.parametrize("engine", ["s153", "s154"])
def test_fs_run_shaped_reload_is_seen_by_its_stall_and_reached(engine):
    # the s153 calibration's attempt 3 (it DID strand): the reload's fade pulse unsampled, 250 -> 250 moves no field id,
    # so the old bench found 'no sample showed the guest's own shutdown'. The load's 0.45 s stall is the shutdown.
    rows, msgs, order = race(engine, "FS", 0.10, 0.45, post_k=10, **RUN)
    i_s = order["i_s"]
    assert not any(r["fading"] for r in rows[order["i_w"]:i_s + 1]), "the stand-in must hide the reload's fade pulse"
    assert order["shut_by"] == "stall" and order["order"] == "in-load" and order["fall"] == "timer", order["why"]
    reached, j = call(("reached", ["FS", order]), ("judge_strand", [rows, order], {"dest": AWAY, "host_field": AWAY}))
    assert reached
    want = engine == "s154"
    assert j["a"][0] is want and j["b"][0] is want, (j, order["why"])


def test_fs_run_shaped_hard_cut_past_the_init_is_unreached():
    # the s153 calibration's attempts 1 and 2: the commit fell past 250's init -- s153 hard-cut to 30602 (green there).
    # The old bench mistook that departure for the reload ('never landed on 250 after its shutdown'); now the stall is
    # the reload, the guest re-landed on 250 with the pending still set, and the order reads after the init.
    rows, msgs, order = race("s153", "FS", 0.136, 0.45, post_k=2, **RUN)
    assert order["shut_by"] == "stall" and order["landed_on"] == HOME, order["why"]
    assert order["order"] == "after-init", order["why"]
    nxt, reached = call(("next_dgame", ["FS", order, 0.136]), ("reached", ["FS", order]))
    assert not reached and nxt < 0.136                  # aim earlier
    assert any(r["field"] == AWAY for r in rows[order["i_l"]:])   # it really left: green on s153, rightly never judged


@pytest.mark.parametrize("engine,want", [("s153", "after-init"), ("s154", ("ambiguous", "after-init"))])
def test_fs_commit_after_the_init_is_unreached_on_both(engine, want):
    _rows, _msgs, order = race(engine, "FS", 0.3, 0.05)
    assert order["order"] in ((want,) if isinstance(want, str) else want), (engine, order["why"])
    assert call(("reached", ["FS", order]))[0] is False


def test_fs_commit_before_the_consumption_is_unreached_on_both():
    # the follow's commit inside the logic tick between the guest's own commit and its consumption: s153 OVERWRITES the
    # own warp (straight to 30602: no reload), s154 drops it (attr & 8) before the shutdown -- neither is the strand
    _rows, _msgs, order3 = race("s153", "FS", 0.004, 0.15, consume_k=2)
    _rows, _msgs, order4 = race("s154", "FS", 0.004, 0.15, consume_k=2)
    assert order3["order"] == "overwrite" and order3["landed_on"] == AWAY, order3["why"]
    assert order4["order"] == "before-shutdown", order4["why"]
    r3, r4, n3, n4 = call(("reached", ["FS", order3]), ("reached", ["FS", order4]),
                          ("next_dgame", ["FS", order3, 0.05]), ("next_dgame", ["FS", order4, 0.05]))
    assert not r3 and not r4 and n3 > 0.05 and n4 > 0.05   # aim later


def test_fs_an_unseen_reload_then_a_departure_is_no_shutdown_not_an_overwrite():
    # a fast reload (no stall) whose fade pulse was missed, then s153's hard cut: the first shutdown evidence is the later
    # departure to 30602 -- the reload went unseen; it is not the follow overwriting the guest's own warp
    _rows, _msgs, order = race("s153", "FS", 0.136, 0.05, post_k=2, **RUN)
    assert order["order"] == "no-shutdown" and order["landed_on"] == AWAY, order["why"]
    nxt, reached = call(("next_dgame", ["FS", order, 0.07]), ("reached", ["FS", order]))
    assert not reached and nxt == 0.07                   # the aim says nothing: kept


def test_fs_without_an_init_witness_is_unreached():
    _rows, _msgs, order = race("s153", "FS", 0.05, 0.15, post_k=4, dress=False, ctl_k=10000)
    assert order["order"] == "no-init-witness", order["why"]
    assert call(("reached", ["FS", order]))[0] is False


def test_a_fall_off_the_timer_model_is_an_instrument_mismatch():
    _rows, _msgs, order = race("s153", "FS", 0.05, 0.15, post_k=4, timer_s=1.6)
    assert order["fall"] == "mismatch" and not order["consistent"], order["why"]
    assert call(("reached", ["FS", order]))[0] is False


# ------------------------------------------------------------------------------------------------ FD, the double load
#: [ff9mapkit netsync s154] THE INIT LAG's variants: (the init's frame after the fade ends, that frame's extra init time).
#: (4, 0) the init on the next frame; (5, 0) a frame with no logic tick between; (*, 0.15) a long init frame (its
#: synchronous field load) -- the first sample after the pending's fall is written only after it.
INIT_LAGS = [(4, 0.0), (5, 0.0), (4, 0.15), (5, 0.15)]
TOL_G = 0.05                                            # the bench's timer slack (the old 'landing' bound was land + TOL_G)


@pytest.mark.parametrize("step_k,init_s", INIT_LAGS)
def test_fd_s153_double_load_is_reached_and_red(step_k, init_s):
    rows, msgs, order = race("s153", "FD", 0.5667, 0.2, step_k=step_k, init_s=init_s)
    assert order["order"] == "after-landing" and order["fall"] == "timer" and order["consistent"], order["why"]
    assert order["witness"] and order["loads"] == 2, order["why"]
    reached, j, ghosts = call(("reached", ["FD", order]), ("judge_double", [rows, order, msgs], {"dest": AWAY}),
                              ("ghosts_on", [msgs, AWAY]))
    assert reached
    assert ghosts == 2
    assert j["a"][0] is False, j["a"]
    assert j["b"][0] is False, j["b"]                   # the pending survives PAST the init grace, to the timer


@pytest.mark.parametrize("step_k,init_s", INIT_LAGS)
def test_fd_s154_landing_cancel_is_reached_by_the_schedule_and_green(step_k, init_s):
    rows, msgs, order = race("s154", "FD", 0.5667, 0.2, step_k=step_k, init_s=init_s)
    # the stand-in is in ENGINE order: the landed sample the bench picks still reads the pending (the init has not run)
    i_l = order["i_l"]
    assert rows[i_l]["field"] == AWAY and not rows[i_l]["fading"] and rows[i_l]["pending"] == AWAY, rows[i_l]
    assert order["init_lag"]["samples"] == step_k - 3, order["why"]
    if init_s:                                          # the old bound (the first post-fall sample <= land + TOL_G) misses
        assert order["fall_at"][1] - order["land"][1] > TOL_G, order["why"]
    assert order["order"] == "after-landing" and order["fall"] == "landing" and order["consistent"], order["why"]
    reached, j = call(("reached", ["FD", order]), ("judge_double", [rows, order, msgs], {"dest": AWAY}))
    assert reached
    assert j["a"][0] is True, j["a"]
    assert j["b"][0] is True, j["b"]


@pytest.mark.parametrize("engine", ["s153", "s154"])
def test_fd_run_shaped_double_load_is_reached(engine):
    # the s153 calibration's FD attempt 3: dgame 0.818, a 0.403 s shutdown stall, the landing two frames later. The old
    # single clock put the commit at rise + 0.9 on a clock that counted the stall in full, so s153's pending fell 0.36 s
    # past it ('mismatch' on every attempt). The interval agrees with the timer; and the second load -- its fade pulse
    # unsampled, ONE ghost line, as on the run -- is still seen, by the per-load dress counter and its 'self-dress' lines.
    rows, msgs, order = race(engine, "FD", 0.818, 0.403, hide_all=True, ghosts="once", **RUN)
    assert order["order"] == "after-landing" and order["consistent"] and order["witness"], order["why"]
    reached, j, ghosts = call(("reached", ["FD", order]), ("judge_double", [rows, order, msgs], {"dest": AWAY}),
                              ("ghosts_on", [msgs, AWAY]))
    assert reached and ghosts == 1
    if engine == "s153":
        assert order["fall"] == "timer" and order["fall_at"][0] - order["fc"] > 0.3, order["why"]   # the old 'mismatch'
        assert "second fade-outs after the landing: 0" in j["a"][1], j["a"]   # the fade pulse unseen ...
        assert j["a"][0] is False and j["b"][0] is False, j              # ... and FD-a red all the same
    else:
        assert order["fall"] == "landing", order["why"]
        assert j["a"][0] is True and j["b"][0] is True, j


def test_fd_b_still_sees_a_pending_that_rises_again_past_the_grace():
    # the grace only absorbs the init lag: a pending that re-rises on 30602 after the landing (a follow armed toward the
    # field the guest stands on) is still the defect FD-b names
    rows, msgs, order = race("s154", "FD", 0.5667, 0.2, step_k=5)
    t_land = rows[order["i_l"]]["t"]
    risen = [dict(r, pending=AWAY) if t_land + 0.5 <= r["t"] <= t_land + 0.6 else r for r in rows]
    j, = call(("judge_double", [risen, order, msgs], {"dest": AWAY}))
    assert j["b"][0] is False, j["b"]


def test_the_init_grace_covers_a_tick_and_a_frame_and_stays_under_the_fd_margin():
    grace, margin, tol = call(("INIT_GRACE_G",), ("FD_MARGIN_G",), ("TOL_G",))
    assert 1.0 / 30.0 + 1.0 / 60.0 < grace                 # one 30 Hz logic tick plus a render frame
    assert grace + tol < margin                             # even FD's lowest aim lands past it: s153's pending stays judged
    assert tol == TOL_G


def test_fd_commit_inside_the_init_grace_is_unreached():
    # a commit just past the landed sample may precede the field's init (s153 would wipe it, s154's fall reads 'timer'):
    # neither a double load nor its cure can be told -- the order is "in-init", never judged as FD
    for engine in ("s153", "s154"):
        _rows, _msgs, order = race(engine, "FD", 0.34, 0.2)
        assert order["order"] == "in-init", (engine, order["why"])
        assert 0 < order["rel_land"][0] <= 0.1 + TOL_G, (engine, order["why"])
        assert call(("reached", ["FD", order]))[0] is False


def test_fd_commit_not_provably_past_the_landing_is_unreached():
    # a short lead on a long stall: the conservative clock cannot put the commit past the init -- never judged as FD
    _rows, _msgs, order = race("s153", "FD", 0.15, 0.3)
    assert order["order"] in ("ambiguous", "in-load", "before-shutdown"), order["why"]
    nxt, reached = call(("next_dgame", ["FD", order, 0.15]), ("reached", ["FD", order]))
    assert not reached and nxt > 0.15                    # aim later


def test_fd_without_a_load_witness_is_unreached():
    # no per-load dress counter: FD-a could not see a second load whose fade pulse the sampler missed -- never judged
    _rows, _msgs, order = race("s153", "FD", 0.5667, 0.2, dress=False)
    assert order["order"] == "after-landing" and order["witness"] is False, order["why"]
    assert call(("reached", ["FD", order]))[0] is False


def test_next_aims_step_the_right_way_and_stay_in_range():
    _rows, _msgs, fs_late = race("s153", "FS", 0.3, 0.05)
    _rows, _msgs, fd_init = race("s153", "FD", 0.34, 0.2)
    a, b, c = call(("next_dgame", ["FS", fs_late, 0.3]), ("next_dgame", ["FD", fd_init, 0.34]),
                   ("next_dgame", ["FD", fd_init, 0.86]))
    assert a < 0.3                                       # the commit fell past the init: aim earlier
    assert b > 0.34                                      # not provably past the init: aim later
    assert c <= 0.86                                     # never past the cap


# ------------------------------------------------------------------------------------------------ FE, the ordinary follow
def test_fe_one_load_one_ghost_passes_and_measures_the_window_and_the_timer():
    rows, msgs, t_send = simulate("s153", "FD", 0.0, 0.2, own=False, after_s=4.0)
    res, = call(("judge_follow", [rows, msgs], {"dest": AWAY, "origin": HOME, "t_send": t_send}))
    assert res["ok"], res["why"]
    assert 0.2 < res["window"] < 0.35
    lo, hi = res["timer"]                                # the follow's timer with no load inside straddles 0.9
    assert lo < 0.9 + TOL_G and hi >= 0.9 - TOL_G, res["why"]
    assert res["loads"] == 1, res["why"]


def test_fe_fails_on_a_second_load_or_an_s154_line():
    rows, msgs, t_send = simulate("s153", "FD", 0.0, 0.2, own=False, after_s=4.0)
    two = list(rows)
    i = len(two) - 30
    two[i] = dict(two[i], fading=True)                  # a second scene change on 30602 after the landing
    drop = msgs + ["[NetSync] follow-warp to field 30602 dropped: a scene load is in flight -- the load already in flight "
                   "ends this fade; the follow re-arms on the field it lands on"]
    a, b, c = call(("judge_follow", [two, msgs], {"dest": AWAY, "origin": HOME, "t_send": t_send}),
                   ("judge_follow", [rows, drop], {"dest": AWAY, "origin": HOME, "t_send": t_send}),
                   ("judge_follow", [rows, msgs + [GHOST.format(AWAY)]], {"dest": AWAY, "origin": HOME, "t_send": t_send}))
    assert not a["ok"] and not b["ok"] and not c["ok"]


def test_the_world_drop_line_is_not_an_s154_line_and_every_s154_form_is():
    world = "[NetSync] follow-warp to field 30602 dropped: the field left for the world map inside its fade (the world " \
            "rejoin takes over)"
    s154 = ["[NetSync] follow-warp to field 30602 never landed (field 250 loaded instead: its commit was wiped or overwritten) "
            "-- its latch is cleared and the follow re-arms here",
            "[NetSync] follow-warp to field 30602 cancelled: this load already landed on it (no second load)",
            "[NetSync] the same-field kick on field 250 cancelled: field 30602 loaded first (its fade ended with that field) -- "
            "the kick re-arms if this load skips the mirror",
            "[NetSync] the follow to field 30602 waits: a scene fade is in flight (this field is already changing scene -- "
            "the follow re-arms where it lands)",
            "[NetSync] follow-warp to field 30602 dropped: a scene load is in flight -- the load already in flight ends this "
            "fade; the follow re-arms on the field it lands on"]
    news, = call(("s154_lines", [[world] + s154 + [GHOST.format(AWAY)]]))
    assert news == s154


def test_the_self_dress_line_counts_one_per_load_of_that_field():
    # the run's own lines: one per load of the guest's body; the rig and ARMED lines never count
    msgs = [DRESS.format(AWAY), "[NetSync] self-dress: uid 1 wears rig 8 (GEO_NPC_F0_MOG), which has no footfall frames "
            "(as in stock) -- its footstep ops are dropped", DRESS.format(AWAY),
            "[NetSync] self-dress ARMED (host): section 8 model 220 charId 255 -> rig 8 (GEO_NPC_F0_MOG)",
            "[NetSync] self-dress: field 250 uid 10 sid 10: Zidane (98) -> GEO_NPC_F0_MOG (model 220, rig 8, eye -200) [host]"]
    away, home = call(("dress_lines_on", [msgs, AWAY]), ("dress_lines_on", [msgs, HOME]))
    assert away == 2 and home == 1


# ------------------------------------------------------------------------------------------------ the calibration
GREEN = {"FR-PRE": True, "FE1": True, "FE2": True, "FS-pre": True, "FS-a": True, "FS-b": True, "FD-pre": True,
         "FD-a": True, "FD-b": True}


def _cal(done, s154=()):
    sets, = call(("cal_sets", [done]))
    predicted, maybe, got, missed = sets
    verdict, = call(("cal_judgement", [done, predicted, maybe, list(s154)]))
    return verdict, got, missed


def test_calibration_passes_an_s153_shaped_run():
    done = dict(GREEN, **{"FS-a": False, "FS-b": False, "FD-a": False, "FD-b": False})
    (ok, why), got, missed = _cal(done)
    assert ok, why
    assert got == ["FS", "FD"] and missed == []


def test_calibration_fails_an_s154_shaped_run_and_an_s154_line():
    (ok, why), _g, _m = _cal(dict(GREEN))
    assert not ok and "stayed GREEN" in why
    done = dict(GREEN, **{"FS-a": False, "FS-b": False, "FD-a": False, "FD-b": False})
    (ok, why), _g, _m = _cal(done, s154=["[NetSync] follow-warp to field 30602 cancelled: this load already landed on it"])
    assert not ok and "s154" in why


def test_calibration_counts_only_reached_legs_and_fails_when_none_was():
    done = dict(GREEN, **{"FS-pre": False, "FS-a": False, "FS-b": False, "FD-a": False, "FD-b": False})
    (ok, why), got, missed = _cal(done)
    assert ok and got == ["FD"] and missed == ["FS"], why
    done = dict(GREEN, **{"FS-pre": False, "FS-a": False, "FS-b": False, "FD-pre": False, "FD-a": False, "FD-b": False})
    (ok, why), got, _m = _cal(done)
    assert not ok and got == [] and "nothing was calibrated" in why
    done = dict(GREEN, **{"FE1": False, "FS-a": False, "FS-b": False, "FD-a": False, "FD-b": False})
    (ok, why), _g, _m = _cal(done)
    assert not ok and "FE1" in why                      # an instrument red voids the calibration


def test_the_catalog_carries_the_cal_row_only_when_calibrating():
    plain, cal, pred = call(("catalog", [False]), ("catalog", [True]), ("PREDICTED_S153",))
    assert "FR-CAL" not in plain and "FR-CAL" in cal
    assert pred == {"FS": ["FS-a", "FS-b"], "FD": ["FD-a", "FD-b"]}
    assert all(c in plain for ids in pred.values() for c in ids)
