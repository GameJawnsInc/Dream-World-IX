"""s158 -- THE PARTY-SCENE STEP-OUT (studies/field-coop/GUEST-TRAVERSAL-TWO-PC.md Finding 3, memoria-patches s158), the SOLO bench.
[ff9mapkit netsync s158]

THE DEFECT. Both copies run the same scene script and each walks its OWN player object along the same path, so in a host scene the
host saw the guest's dressed ghost inside Zidane beside the scene's own party member, and the guest saw its own dressed body play
Zidane's part beside the host's Zidane ghost (Dali 359).

THE FIX (s158). While the host is here with control off and my control is off (no guest climb in flight, not a relayed talk), the
guest STEPS OUT: its wire mask is 0 (the host's ghost of it hides), its screen hides the host's ghost, and a DRESSED body goes dark
(meshes only: the blob shadow keeps the stock flag4) while a Zidane stand-in plays its part from the body's own pose, raw source clip
and normalized time. It starts at once on a line or the host's scene, else after a 1.5 s dwell (THE ARRIVAL LAW); it ends 500 ms
after my control comes back, on a field change, or at the session's end.

THE BENCH. One instance root, the selftest role; the mirror is the host's ghost of me, `netsync hostscene 1` is "the host is here
in a scene with its control off" (the step-out reads it directly on the selftest role), a STOCK ladder climb under `bench 0` is my
control off with a moving body. 114 climbs UNDRESSED (the field's Vivi), 207 DRESSED (`selfdress self steiner` before the warp:
Zidane's player object wears Steiner).

  K0        provenance; newgame; warp 114 (the env-slot law); noencounter; `netsync selftest 1`; `netsync bench 0`; the offset
            preflight (|SelfTestOffset| < 640) and a fresh process (no --attach).
  K1        "step-out selftest: OK (N rows, M mutants caught, dwell 1500 ms, step-in 500 ms)" within 20 s; `stepout.selftest` "ok".
  K2        `netsync.stepout` at rest before any lever: active false, lever null, wire_mask > 0, the mirror shown, base.why_not
            "the host has control" (no host scene yet).
  N-REST    hostscene 1 with MY control on, 2 s: never active, why_not "I have control", the mirror shown.
  U-UP      114 UNDRESSED, bench 0, hostscene 1, the stock climb up: OUT while control is off (dressed false, why "scene",
            wire_mask 0, the mirror hidden, the body's renderers ON, no stand-in); IN after control, with the 500 ms debounce
            (still out >= 0.4 s after control; in by 1.5 s), in_why.control +1, the mask and the mirror back.
  N-CLIMB   114, bench 1 (a GUEST climb: InFlightNow), hostscene raised MID-climb: never out; a mid-climb sample shows every other
            start term true (host_ctl_off, my_ctl_off, host_scene) and why_not "my guest climb is in flight".
  N-TALK    114, bench 1, hostscene 1, `netsync talk 3` (JJY, a RELAYED talk): never out; a sample with the line open and every
            other term true shows why_not "a relayed talk owns my copy"; talk_accepts +1.
  D-ARM     207 DRESSED: `selfdress self steiner` then warp 207 -> dress.self.why "dressed" on the controlled body; no stand-in.
  D-UP      207 DRESSED, bench 0, hostscene 1, the stock climb up: OUT with dressed true, body_rends_on 0, the shadow kept when the
            field draws one, a stand-in shown wearing GEO_MAIN_F0_ZDN and playing a ZDN clip, within 2 u of the body, its
            normalized time within 0.1 of the body's, wire_mask 0, the mirror hidden; IN after control: the body's renderers back,
            the stand-in gone.
  D-DN      the same, the stock climb down.
  K-R       `reset` releases the lever (its line when the calibration held one); re-read with the role: lever null.

THE CALIBRATION (COOP_CALIBRATE=1): `stepout off` is pulled right after K2 and HELD. PREDICTED_OFF = U-UP, D-UP, D-DN red, each with
OFF_MARKER (control went off, the host scene was up, never active, base.why_not "the stepout lever is off"); the negatives judge
only "never out" under the lever. K-CAL-M (judged before K-CAL) is green only when every predicted red carries its marker.

NOT PROVEN HERE (selftest rows only): THE ARRIVAL LAW's dwell (the bench's host scene starts at once by design), the relayed talk's
section-5 nonce half (a live lane only), the field and session ends, a host's zero-mask and option-C hides (a HOST role: the
two-PC session), the stand-in's lighting.

    py tools/play.py studies/test-harness/scenarios/coop_step_out.py --instance C:\\gd\\ff9-inst\\host
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_step_out.py --instance C:\\gd\\ff9-inst\\host
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import coop_guest_traversal as gt                          # noqa: E402 - the s156 bench's poses, climbs and arrival

HarnessError = cb.HarnessError

KEY = "netsync.stepout"
PROBE = KEY + ".outs"                    # key PRESENCE is the capability (protocol 5, additive)
JJY_UID = gt.JJY_UID                     # f114 e3: one WindowSync, a bracketed EnableMove. NEVER uid 2 (BBA)

SELFTEST_S = 20.0
REST_HOLD_S = 2.0                        # N-REST's window
TALK_HOLD_S = 1.5                        # N-TALK's window once the line is open
IN_BY_S = 1.5                            # an IN must land this soon after control (StepInMs 500 + the publish cadence)
DEBOUNCE_MIN_S = 0.4                     # ...and not before this (StepInMs 500, less two publishes)
DPOS_MAX = 2.0                           # the stand-in's distance from the body (copied every LateUpdate)
NORM_TOL = 0.1                           # its normalized time vs the body's (both sampled the same frame)
SC_UNARMED_207, SC_SAFE_207 = gt.SC_UNARMED_207, gt.SC_SAFE_207

PROOF_RX = re.compile(r"step-out selftest: OK \((\d+) rows, (\d+) mutants caught, dwell (\d+) ms, step-in (\d+) ms\)")
WHY_NOT_HOST_CONTROL = "the host has control"
WHY_NOT_MY_CONTROL = "I have control"
WHY_NOT_CLIMB = "my guest climb is in flight"
WHY_NOT_TALK = "a relayed talk owns my copy"
WHY_NOT_LEVER = "the stepout lever is off"
LOG_OUT = "[NetSync] step-out: OUT on field "
LOG_IN = "[NetSync] step-out: IN on field "
LOG_RELEASE = "[NetSync] harness: step-out lever released (act)"
STANDIN_GEO = "GEO_MAIN_F0_ZDN"

CLAIMS = {
    "K0": "the forced selftest role on 114 (newgame, warp 114, noencounter, `netsync selftest 1`, `bench 0`); a fresh process "
          "and |SelfTestOffset| < 640",
    "K1": "the s158 proof line 'step-out selftest: OK (N rows, M mutants caught, dwell 1500 ms, step-in 500 ms)' within 20 s, "
          "and `netsync.stepout.selftest` 'ok'",
    "K2": "`netsync.stepout` at rest before any lever: active false, lever null, wire_mask > 0, the mirror shown, base.why_not "
          "'the host has control'",
    "N-REST": "hostscene 1 with MY control on, 2 s: never active, why_not 'I have control', the mirror shown",
    "U-UP": "114 UNDRESSED, the stock climb up under hostscene 1: OUT while control is off (dressed false, why 'scene', "
            "wire_mask 0, the mirror hidden, the body's renderers on, no stand-in); IN 0.4-1.5 s after control (the debounce), "
            "in_why.control +1, the mask and the mirror back",
    "N-CLIMB": "a GUEST climb on 114 (bench 1) with hostscene raised mid-climb: never out; a mid-climb sample has every other "
               "start term true and why_not 'my guest climb is in flight'",
    "N-TALK": "a RELAYED talk (`netsync talk 3`, JJY) under hostscene 1: never out; a sample with the line open and every other "
              "term true has why_not 'a relayed talk owns my copy'; talk_accepts +1",
    "D-ARM": "207 DRESSED: `selfdress self steiner` then warp 207 -> dress.self.why 'dressed' on the controlled body; no stand-in",
    "D-UP": "207 DRESSED, the stock climb up under hostscene 1: OUT with dressed true, body_rends_on 0, the shadow kept, a stand-in "
            "shown as GEO_MAIN_F0_ZDN on a ZDN clip within 2 u and 0.1 of the body's time, wire_mask 0, the mirror hidden; IN "
            "after control: the body back, the stand-in gone",
    "D-DN": "207 DRESSED, the stock climb down: the D-UP extras",
    "K-R": "`reset` releases the lever (its line when the calibration held one); re-read with the role: lever null",
}
PREDICTED_OFF = ("U-UP", "D-UP", "D-DN")
OFF_MARKER = ("control went off; the host scene was up; never active; base.why_not 'the stepout lever is off'")
FINALS = ("K-R", "K-CAL-M", "K-CAL")


def catalog(calibrate: bool) -> dict:
    cat = dict(CLAIMS)
    if calibrate:
        cat["K-CAL-M"] = "every predicted red carries its marker: " + OFF_MARKER
        cat["K-CAL"] = "the lever calibration: exactly " + ", ".join(PREDICTED_OFF) + " red"
    return cat


# --------------------------------------------------------------------------------------------- reads (pure)
def so(x) -> dict | None:
    b = cb.path(x, KEY)
    return b if isinstance(b, dict) else None


def so_get(b, dotted: str, default=None):
    cur = b
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def mirror_hidden(x) -> bool | None:
    v = cb.path(x, "netsync.dress.ghost.hidden")
    return v if isinstance(v, bool) else None


def control(x) -> bool:
    return gt.control(x)


def actives(samples) -> list:
    return [s for s in samples if so_get(so(s), "active") is True]


def off_samples(samples) -> list:
    return [s for s in samples if not control(s)]


def circ(a: float, b: float) -> float:
    """The distance of two normalized times on the unit circle (a looping clip wraps)."""
    d = abs(a - b) % 1.0
    return min(d, 1.0 - d)


def judge_out_undressed(samples) -> tuple:
    """U-UP's OUT half: over the control-off samples."""
    offs = off_samples(samples)
    outs = actives(offs)
    if not offs:
        return False, "control never went off (no climb)"
    if not outs:
        return False, f"never OUT over {len(offs)} control-off samples; why_not {sorted({str(so_get(so(s), 'base.why_not')) for s in offs})}"
    bad = []
    for s in outs:
        b = so(s)
        if so_get(b, "dressed") is not False:
            bad.append("dressed")
        if so_get(b, "why") != "scene":
            bad.append(f"why {so_get(b, 'why')!r}")
        if so_get(b, "wire_mask") != 0:
            bad.append(f"wire_mask {so_get(b, 'wire_mask')!r}")
        if mirror_hidden(s) is not True:
            bad.append(f"mirror hidden {mirror_hidden(s)!r}")
        if not (isinstance(so_get(b, "body_rends_on"), int) and so_get(b, "body_rends_on") > 0):
            bad.append(f"body_rends_on {so_get(b, 'body_rends_on')!r}")
        if so_get(b, "standin.on") is not False:
            bad.append("a stand-in on an undressed body")
    bad = sorted(set(bad))
    return not bad, f"{len(outs)} of {len(offs)} control-off samples OUT" + (f"; WRONG: {bad}" if bad else " (undressed, why 'scene', mask 0, mirror hidden, body on)")


def judge_out_dressed(samples, shadow_rest) -> tuple:
    """D-UP / D-DN's OUT half: over the control-off samples."""
    offs = off_samples(samples)
    outs = actives(offs)
    if not offs:
        return False, "control never went off (no climb)"
    if not outs:
        return False, f"never OUT over {len(offs)} control-off samples; why_not {sorted({str(so_get(so(s), 'base.why_not')) for s in offs})}"
    bad, clips, worst_d, worst_n = [], set(), 0.0, 0.0
    for s in outs:
        b = so(s)
        if so_get(b, "dressed") is not True:
            bad.append("not dressed")
        if so_get(b, "body_rends_on") != 0:
            bad.append(f"body_rends_on {so_get(b, 'body_rends_on')!r}")
        if shadow_rest == 1 and so_get(b, "shadow") != 1:
            bad.append(f"shadow {so_get(b, 'shadow')!r} (was 1 at rest)")
        if so_get(b, "wire_mask") != 0:
            bad.append(f"wire_mask {so_get(b, 'wire_mask')!r}")
        if mirror_hidden(s) is not True:
            bad.append(f"mirror hidden {mirror_hidden(s)!r}")
        if so_get(b, "standin.on") is not True or so_get(b, "standin.shown") is not True:
            bad.append("no stand-in shown")
            continue
        if so_get(b, "standin.geo") != STANDIN_GEO:
            bad.append(f"stand-in geo {so_get(b, 'standin.geo')!r}")
        clip = so_get(b, "standin.clip")
        clips.add(clip)
        if not (isinstance(clip, str) and "_ZDN_" in clip):
            bad.append(f"stand-in clip {clip!r}")
        d = so_get(b, "standin.dpos")
        if not isinstance(d, (int, float)) or d < 0 or d > DPOS_MAX:
            bad.append(f"dpos {d!r}")
        else:
            worst_d = max(worst_d, float(d))
        n, bn = so_get(b, "standin.norm"), so_get(b, "standin.body_norm")
        if isinstance(n, (int, float)) and isinstance(bn, (int, float)) and n >= 0 and bn >= 0:
            worst_n = max(worst_n, circ(float(n), float(bn)))
            if circ(float(n), float(bn)) > NORM_TOL:
                bad.append(f"norm {n} vs body {bn}")
        else:
            bad.append(f"norm {n!r} / body_norm {bn!r}")
    bad = sorted(set(bad))
    return not bad, (f"{len(outs)} of {len(offs)} control-off samples OUT; clips {sorted(c for c in clips if c)}; worst dpos "
                     f"{worst_d:.2f} u, worst |norm - body| {worst_n:.3f}" + (f"; WRONG: {bad[:8]}" if bad else ""))


def judge_in(after, land_t: float | None, b0, *, dressed: bool) -> tuple:
    """The IN half: the first sample after control with active false lands DEBOUNCE_MIN_S..IN_BY_S after control; then the
    body, the mask and the mirror are back; in_why.control +1."""
    if land_t is None:
        return False, "no landing (control never came back)"
    first_in = next((s for s in after if so_get(so(s), "active") is False), None)
    if first_in is None:
        return False, f"still OUT {IN_BY_S:g} s after control ({len(after)} samples)"
    dt = first_in["_t"]
    b = so(first_in)
    parts = [("debounce", DEBOUNCE_MIN_S <= dt <= IN_BY_S),
             ("in_why.control +1", so_get(b, "in_why.control", 0) == so_get(b0, "in_why.control", 0) + 1),
             ("wire_mask back", isinstance(so_get(b, "wire_mask"), int) and so_get(b, "wire_mask") > 0),
             ("mirror shown", mirror_hidden(first_in) is False),
             ("body on", isinstance(so_get(b, "body_rends_on"), int) and so_get(b, "body_rends_on") > 0)]
    if dressed:
        parts.append(("stand-in gone", so_get(b, "standin.on") is False))
    ok = all(v for _, v in parts)
    return ok, f"IN {dt:.2f} s after control; " + ", ".join(f"{k} {'ok' if v else 'NO'}" for k, v in parts)


def judge_never(samples, *, lever: bool, why_not: str, need) -> tuple:
    """A negative: never active; (plain) at least one sample where ``need(sample)`` holds shows ``why_not``."""
    outs = actives(samples)
    if outs:
        return False, f"stepped OUT on {len(outs)} of {len(samples)} samples (why {so_get(so(outs[0]), 'why')!r})"
    if lever:
        return True, f"never out over {len(samples)} samples (the lever: the reason is the lever's)"
    hits = [s for s in samples if need(s)]
    named = [s for s in hits if so_get(so(s), "base.why_not") == why_not]
    if not hits:
        return False, f"never out, but no sample had every other start term true ({len(samples)} samples) -- vacuous"
    if not named:
        return False, f"never out; {len(hits)} armed samples but why_not {sorted({str(so_get(so(s), 'base.why_not')) for s in hits})}"
    return True, f"never out over {len(samples)} samples; {len(named)} of {len(hits)} armed samples name {why_not!r}"


def off_marker(samples) -> tuple:
    offs = off_samples(samples)
    scene = [s for s in offs if so_get(so(s), "base.host_scene") is True]
    named = [s for s in offs if so_get(so(s), "base.why_not") == WHY_NOT_LEVER]
    parts = [("control off", bool(offs)), ("host scene up", bool(scene)), ("never active", not actives(samples)),
             ("why_not the lever", bool(named))]
    return all(v for _, v in parts), ", ".join(f"{k} {'ok' if v else 'NO'}" for k, v in parts)


# --------------------------------------------------------------------------------------------- the run
class Ctx:
    def __init__(self, calibrate: bool):
        self.calibrate = calibrate
        self.gt = gt.Ctx("plain", True)  # the s156 helpers' own context (their legs run bench-0 stock moves here)
        self.marks: dict = {}
        self.lever_held = False
        self.k0_ok = False


def _ns(g, sub: str, *args) -> tuple:
    return cb.try_ns(g, sub, *args)


def hostscene(g, on: bool) -> None:
    ok, why = _ns(g, "hostscene", 1 if on else 0)
    if not ok:
        raise HarnessError(f"hostscene {int(on)} refused: {why}")
    cb.poll(g, lambda s: so_get(so(s), "base.host_scene") is on or not on, 2.0, f"hostscene {int(on)} read back")


def watch_after(g, t_land: float) -> list:
    """Every publish for IN_BY_S + 0.3 s after control, each stamped with its seconds since control."""
    out = []
    seen = None
    deadline = t_land + IN_BY_S + 0.3
    while time.time() < deadline:
        st = g.state
        if st.frame != seen:
            seen = st.frame
            d = dict(cb.raw(st))
            d["_t"] = time.time() - t_land
            out.append(d)
        time.sleep(0.004)
    return out


def climb_leg(g, ctx: Ctx, leg: str, fid: int, direction: str, *, bench: bool, scene_before: bool, on_mount=None) -> dict:
    """The start pose, `bench`, hostscene (before the press, or from ``on_mount``), the climb (gt.ladder_run), the landing,
    then every publish for 1.8 s after control. hostscene is dropped at the end, at rest."""
    pose = "bottom" if direction == "up" else "top"
    ok, why = gt.ensure_pose(g, ctx.gt, leg, fid, pose)
    if not ok:
        raise HarnessError(f"{leg}: the start pose ({pose}) failed: {why}")
    ok, why = gt.set_bench(g, bench)
    if not ok:
        raise HarnessError(f"{leg}: bench {int(bench)} failed: {why}")
    st0 = gt.rest(g)
    b0 = so(st0)
    shadow_rest = so_get(b0, "shadow")
    if scene_before:
        hostscene(g, True)
    res = gt.ladder_run(g, ctx.gt, leg, fid, direction, act=bench, on_mount=on_mount)
    t_land = res.get("land_at")
    res["after"] = watch_after(g, t_land) if t_land is not None and res.get("land") is not None else []
    res["b0"] = b0
    res["shadow_rest"] = shadow_rest
    try:
        hostscene(g, False)
    finally:
        gt.rest(g)
    return res


def run(g, field: int | None = None):
    calibrate = cb.CALIBRATE
    st0 = cb.poll(g, lambda s: s.netsync is not None, 15.0, "the netsync block (protocol 5)") or g.state
    ctx = Ctx(calibrate)
    led = cb.Ledger(g, catalog(calibrate), finals=FINALS, width=1600)
    if field is not None:
        g.note(f"--field {field} is ignored: the bench picks its own fields (114 -> 207)")
    if not cb.has(st0, PROBE):
        g.note("this engine publishes no `netsync.stepout` (s158): every leg is red by absence")
    try:
        ctx.k0_ok = _k0(g, ctx, led)
        if not ctx.k0_ok:
            led.close("not reached: K0 (the setup or a preflight) refused")
            return
        _k1_k2(g, ctx, led)
        if calibrate:
            ok, why = _ns(g, "stepout", "off")
            st = cb.poll(g, lambda s: so_get(so(s), "lever") == "off", 3.0, "the off lever read back")
            ctx.lever_held = ok and st is not None
            g.note(f"CALIBRATION: `stepout off` {'taken' if ok else 'REFUSED: ' + why}, held for the whole run; predicted red "
                   f"{', '.join(PREDICTED_OFF)}")
        _field_114(g, ctx, led)
        _field_207(g, ctx, led)
    except HarnessError as err:
        g.note(f"the run raised: {str(err)[:400]}")
        led.close(f"not reached: the run raised ({str(err)[:200]})")
    finally:
        gt._release_all(g)
        try:
            _ns(g, "hostscene", 0)
            _ns(g, "selfdress", "self", "off")
        except HarnessError:
            pass
        if ctx.k0_ok:
            _k_r(g, ctx, led)
        else:
            led.unreached(["K-R"], "K0 refused")
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'step-out-' + ('lever' if calibrate else 'plain'))}")
        if calibrate:
            led.close("not reached: the run ended before this check")
            marks_ok = all(off_marker(ctx.marks[leg])[0] for leg in PREDICTED_OFF if leg in ctx.marks) \
                and all(leg in ctx.marks for leg in PREDICTED_OFF)
            led.check("K-CAL-M", marks_ok, "; ".join(f"{leg}: {off_marker(ctx.marks[leg])[1] if leg in ctx.marks else 'NO RUN'}"
                                                     for leg in PREDICTED_OFF))
            led.judge_calibration("K-CAL", PREDICTED_OFF)
        led.close(final=True)


def _k0(g, ctx: Ctx, led: cb.Ledger) -> bool:
    cb.provenance(g)
    if getattr(g, "attach", False):
        led.check("K0", False, "refused: --attach (a reused process carries earlier counters and episodes)")
        return False
    try:
        g.newgame()
    except HarnessError as err:
        led.check("K0", False, f"newgame failed: {str(err)[:300]}")
        return False
    ok, why = _arrive(g, 114)
    if not ok:
        led.check("K0", False, why)
        return False
    try:
        g.no_encounters(True)
    except (HarnessError, AttributeError) as err:
        g.note(f"noencounter refused ({str(err)[:120]})")
    g.wait_frames(45)
    ok1, why1 = _ns(g, "selftest", 1)
    ok2, why2 = _ns(g, "bench", 0)
    st = cb.poll(g, lambda s: bool((s.netsync or {}).get("forced")) and bool((s.netsync or {}).get("selftest")), 5.0,
                 "the forced selftest role") or g.state
    ns = st.netsync or {}
    dx, dz, src = gt.offset_from(cb.log_lines(g), cb.ini_value(g, "Netsync", "SelfTestOffset"))
    off_ok = gt.offset_ok(dx, dz)
    good = ok1 and ok2 and bool(ns.get("forced")) and bool(ns.get("selftest")) and off_ok
    led.check("K0", good, f"selftest={ns.get('selftest')!r} forced={ns.get('forced')!r} bench={ns.get('bench')!r}; "
                          f"SelfTestOffset {dx},{dz} ({src})" + (f"; {why1 or why2}" if (why1 or why2) else ""))
    return good


def _arrive(g, fid: int, scenario: int | None = None) -> tuple:
    """gt.arrive's warp half (the env-slot law, entrance 0, the post-init witness) WITHOUT its undress: 207 is dressed here."""
    try:
        g.poke(13, 0)
        g.poke(14, 0)
    except (HarnessError, AttributeError) as err:
        g.note(f"warp {fid}: the env-slot poke refused ({str(err)[:120]})")
    try:
        g.warp(fid, entrance=0, scenario=scenario)
    except HarnessError as err:
        return False, f"warp {fid} failed: {str(err)[:200]}"
    st = cb.poll(g, lambda s: gt.arrived(s, fid)[0], 15.0, f"field {fid}'s post-init witness")
    ok, why = gt.arrived(st or g.state, fid)
    return ok, why if ok else f"no post-init witness on {fid}: {why}"


def _k1_k2(g, ctx: Ctx, led: cb.Ledger) -> None:
    lines = cb.wait_log(g, 0, "step-out selftest:", timeout=SELFTEST_S)
    m = next((PROOF_RX.search(ln) for ln in lines if PROOF_RX.search(ln)), None)
    st = cb.poll(g, lambda s: so_get(so(s), "selftest") is not None, SELFTEST_S, "netsync.stepout.selftest") or g.state
    b = so(st)
    led.check("K1", m is not None and so_get(b, "selftest") == "ok" and m.group(3) == "1500" and m.group(4) == "500",
              f"{cb.grep(lines, 'step-out selftest')}; stepout.selftest {so_get(b, 'selftest')!r}")
    st = gt.rest(g)
    b = so(st)
    parts = [("present", b is not None), ("active false", so_get(b, "active") is False), ("lever null", so_get(b, "lever") is None),
             ("wire_mask > 0", isinstance(so_get(b, "wire_mask"), int) and so_get(b, "wire_mask") > 0),
             ("mirror shown", mirror_hidden(st) is False),
             ("why_not " + WHY_NOT_HOST_CONTROL, so_get(b, "base.why_not") == WHY_NOT_HOST_CONTROL)]
    led.check("K2", all(v for _, v in parts), ", ".join(f"{k} {'ok' if v else 'NO'}" for k, v in parts)
              + f"; why_not {so_get(b, 'base.why_not')!r}, wire_mask {so_get(b, 'wire_mask')!r}")


def _guard(g, led: cb.Ledger, leg: str, fid: int, fn) -> None:
    if leg not in led.catalog or leg in led.done:
        return
    try:
        fn()
    except HarnessError as err:
        led.unreached([leg], f"the leg raised: {str(err)[:300]}")
        gt.recover(g, fid)
    except Exception as err:                             # noqa: BLE001 - a BENCH bug: red and loud, the run goes on
        g.note(f"{leg} FAULTED (a bench bug, not a verdict): {err!r}"[:400])
        led.unreached([leg], f"the leg FAULTED (a bench bug): {err!r}"[:300])
        gt.recover(g, fid)
    finally:
        try:
            _ns(g, "hostscene", 0)
        except HarnessError:
            pass
    if leg not in led.done:
        led.unreached([leg], "the leg recorded nothing")


def _field_114(g, ctx: Ctx, led: cb.Ledger) -> None:
    _guard(g, led, "N-REST", 114, lambda: _n_rest(g, ctx, led))
    _guard(g, led, "U-UP", 114, lambda: _u_up(g, ctx, led))
    _guard(g, led, "N-CLIMB", 114, lambda: _n_climb(g, ctx, led))
    _guard(g, led, "N-TALK", 114, lambda: _n_talk(g, ctx, led))
    gt.set_bench(g, False)


def _n_rest(g, ctx, led):
    gt.rest(g)
    hostscene(g, True)
    samples = [dict(cb.raw(s)) for s in cb.hold_for(g, REST_HOLD_S)]
    hostscene(g, False)
    ok, why = judge_never(samples, lever=ctx.calibrate, why_not=WHY_NOT_MY_CONTROL,
                          need=lambda s: so_get(so(s), "base.host_ctl_off") is True and control(s))
    shown = all(mirror_hidden(s) is False for s in samples)
    led.check("N-REST", ok and shown, why + ("" if shown else "; the mirror HID with my control on"))


def _u_up(g, ctx, led):
    res = climb_leg(g, ctx, "U-UP", 114, "up", bench=False, scene_before=True)
    samples = res.get("samples") or []
    if ctx.calibrate:
        ctx.marks["U-UP"] = samples
    ok1, why1 = judge_out_undressed(samples)
    ok2, why2 = judge_in(res["after"], res.get("land_at"), res["b0"], dressed=False)
    led.check("U-UP", ok1 and ok2, f"OUT: {why1} || IN: {why2}")


def _n_climb(g, ctx, led):
    def scene_mid(g2, res):
        hostscene(g2, True)
    res = climb_leg(g, ctx, "N-CLIMB", 114, "down", bench=True, scene_before=False, on_mount=scene_mid)
    samples = (res.get("samples") or []) + (res.get("after") or [])
    need = (lambda s: so_get(so(s), "base.host_ctl_off") is True and so_get(so(s), "base.my_ctl_off") is True
            and so_get(so(s), "base.climb") is True)
    ok, why = judge_never(samples, lever=ctx.calibrate, why_not=WHY_NOT_CLIMB, need=need)
    climbed = gt.landed_at(res["land"], gt.LADDERS[114]["land_bottom"]) if res.get("land") else False
    led.check("N-CLIMB", ok and climbed, why + ("" if climbed else "; the guest climb did not land at the foot"))


def _n_talk(g, ctx, led):
    ok, why = gt.set_bench(g, True)
    if not ok:
        raise HarnessError(f"bench 1: {why}")
    st0 = gt.rest(g)
    b0 = so(st0)
    hostscene(g, True)
    ok, why = _ns(g, "talk", JJY_UID)
    if not ok:
        raise HarnessError(f"talk {JJY_UID} refused: {why}")
    opened = cb.poll(g, lambda s: s.dialog_open and not s.control, 4.0, "the relayed talk's window with control off")
    samples = [dict(cb.raw(s)) for s in cb.hold_for(g, TALK_HOLD_S)] if opened is not None else []
    gt.close_line(g)
    hostscene(g, False)
    b1 = so(gt.rest(g))
    need = (lambda s: so_get(so(s), "base.line") is True and so_get(so(s), "base.host_ctl_off") is True
            and so_get(so(s), "base.my_ctl_off") is True)
    ok, why = judge_never(samples, lever=ctx.calibrate, why_not=WHY_NOT_TALK, need=need)
    accepts = so_get(b1, "talk_accepts", 0) - so_get(b0, "talk_accepts", 0)
    led.check("N-TALK", opened is not None and ok and accepts == 1,
              (why if opened is not None else "the relayed talk never opened a window with control off") + f"; talk_accepts +{accepts}")


def _field_207(g, ctx: Ctx, led: cb.Ledger) -> None:
    legs = [c for c in ("D-ARM", "D-UP", "D-DN") if c in led.catalog]
    gt.set_bench(g, False)
    ok, why = _ns(g, "selfdress", "self", "steiner")
    if not ok:
        led.unreached(legs, f"`selfdress self steiner` refused: {why}")
        return
    sc = g.state.scenario
    ok, why = _arrive(g, 207, scenario=SC_SAFE_207 if sc in SC_UNARMED_207 else None)
    if not ok:
        led.unreached(legs, why)
        return
    st = gt.rest(g)
    me = (cb.raw(st).get("player") or {})
    dwhy, duid = cb.path(st, "netsync.dress.self.why"), cb.path(st, "netsync.dress.self.uid")
    ok = dwhy == "dressed" and so_get(so(st), "standin.on") is False
    led.check("D-ARM", ok, f"dress.self.why {dwhy!r} uid {duid!r} rig {cb.path(st, 'netsync.dress.self.rig')!r}; player.model "
                           f"{me.get('model')!r}; stand-in on {so_get(so(st), 'standin.on')!r}")
    if not ok:
        led.unreached(["D-UP", "D-DN"], "D-ARM: the body is not dressed")
        return
    _guard(g, led, "D-UP", 207, lambda: _d_climb(g, ctx, led, "D-UP", "up"))
    _guard(g, led, "D-DN", 207, lambda: _d_climb(g, ctx, led, "D-DN", "down"))


def _d_climb(g, ctx, led, leg: str, direction: str):
    res = climb_leg(g, ctx, leg, 207, direction, bench=False, scene_before=True)
    samples = res.get("samples") or []
    if ctx.calibrate:
        ctx.marks[leg] = samples
    ok1, why1 = judge_out_dressed(samples, res.get("shadow_rest"))
    ok2, why2 = judge_in(res["after"], res.get("land_at"), res["b0"], dressed=True)
    led.check(leg, ok1 and ok2, f"OUT: {why1} || IN: {why2}; shadow at rest {res.get('shadow_rest')!r}")


def _k_r(g, ctx: Ctx, led: cb.Ledger) -> None:
    at = cb.mark(g)
    try:
        cb.release(g)
    except HarnessError as err:
        led.check("K-R", False, f"the release raised: {str(err)[:200]}")
        return
    lines = cb.new(g, at)
    try:
        _ns(g, "selftest", 1)
        st = cb.poll(g, lambda s: bool((s.netsync or {}).get("selftest")), 5.0, "the role again") or g.state
        lever = so_get(so(st), "lever")
        _ns(g, "selftest", 0)
    except HarnessError as err:
        led.check("K-R", False, f"the re-read raised: {str(err)[:200]}")
        return
    line = cb.count(lines, LOG_RELEASE) > 0
    ok = lever is None and (line or not ctx.lever_held)
    led.check("K-R", ok, f"lever {lever!r} after the release; release line {'seen' if line else 'absent'} (a lever "
                         f"{'was' if ctx.lever_held else 'was not'} held into it)")
