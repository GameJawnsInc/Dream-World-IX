"""s158 -- THE PARTY-SCENE STEP-OUT (studies/field-coop/GUEST-TRAVERSAL-TWO-PC.md Finding 3, memoria-patches s158), the SOLO bench.
[ff9mapkit netsync s158]

THE DEFECT. Both copies run the same scene script and each walks its OWN player object along the same path, so in a host scene the
host saw the guest's dressed ghost inside Zidane beside the scene's own party member, and the guest saw its own dressed body play
Zidane's part beside the host's Zidane ghost (Dali 359).

THE FIX (s158). While the host is here with control off and my control is off (no guest climb in flight, not a relayed talk), the
guest STEPS OUT: its wire mask is 0 (the host's ghost of it hides), its screen hides the host's ghost, and a DRESSED body goes dark at
the edge (meshes only: the blob shadow keeps stock's own switch) while a Zidane stand-in plays its part from the body's own pose, raw
source clip and normalized time. It starts at once on a FRESH line on my copy, else after a 1.5 s dwell (THE ARRIVAL LAW); it ends
500 ms after my control comes back, at once when a relayed talk or a guest climb starts inside it, on a field change, or at the end.

THE BENCH. One instance root, the selftest role; the mirror is the host's ghost of me, `netsync hostscene 1` is "the host is here
with its control off" (the step-out reads it directly on the selftest role), a STOCK ladder climb under `bench 0` is my control off
with a moving body. A climb carries no line, so every positive leg HANGS mid-ladder past the dwell (the loop waits on a held key):
the dwell itself is under test (THE ARRIVAL LAW, both ways: N-DWELL's short climb never steps out). 114 climbs UNDRESSED (the field's
Vivi), 207 DRESSED (`selfdress self steiner` before the warp: Zidane's player object wears Steiner).

  K0        provenance; newgame; warp 114 (the env-slot law); noencounter; `netsync selftest 1`; `netsync bench 0`; the offset
            preflight (|SelfTestOffset| < 640) and a fresh process (no --attach).
  K1        "step-out selftest: OK (N rows, M mutants caught, dwell 1500 ms, step-in 500 ms)" within 20 s; `stepout.selftest` "ok".
  K2        `netsync.stepout` at rest before any lever: active false, lever null, wire_mask > 0, the mirror shown (dress.ghost.shown_mask
            > 0), base.why_not "the host has control" (no host scene yet).
  N-REST    hostscene 1 with MY control on, 2 s: never active, why_not "I have control", the mirror shown.
  U-UP      114 UNDRESSED, bench 0, hostscene 1, the stock climb up with a mid-ladder hang: OUT by the DWELL (why "dwell", 1.4-2.3 s after
            control went off -- never sooner) with dressed false, wire_mask 0, the mirror hidden (shown_mask 0), the body's renderers ON,
            no stand-in; IN after control, with the 500 ms debounce (still out >= 0.4 s after control; in by 1.5 s), in_why.control +1,
            the mask and the mirror back.
  N-CLIMB   114, bench 1 (a GUEST climb: InFlightNow), hostscene raised once mounted, a hang past the dwell: never out; a mid-climb sample
            shows every other start term true (host_ctl_off, my_ctl_off) and why_not "my guest climb is in flight".
  N-TALK    114, bench 1, hostscene 1, `netsync talk 3` (JJY, a RELAYED talk; its window is a fresh line): never out over the line and
            past the dwell; a sample with the fresh line and every other term true shows why_not "a relayed talk owns my copy";
            talk_accepts +1.
  D-ARM     207 DRESSED: `selfdress self steiner` then warp 207 -> dress.self.why "dressed" on the controlled body; no stand-in.
  D-UP      207 DRESSED, bench 0, hostscene 1, the stock climb up with a mid-ladder hang: OUT by the dwell with dressed true, body_rends_on 0
            on EVERY out sample (the edge is synchronous), the shadow equal to stock's own switch (shadow_off), a stand-in shown wearing
            GEO_MAIN_F0_ZDN, the loop's own clip (ANH_MAIN_F0_ZDN_LADDER_1_2: RunAnimation 10539 in Zidane_50's loop, both ways -- a
            lost raw record plays the MOUNT clip) on a mid-ladder sample, its own clip time moving and within 0.25 of the body's (read
            live), within 80 u of the body (one frame of ladder motion), wire_mask 0, the mirror hidden; THE SHADOW in the step-in
            debounce (active, control back, stock's switch on again after EnableShadow): drawn -- a shadow that went dark with the
            body would show there; IN after control: the body, the mask and the mirror back within a logic tick, the stand-in gone.
  N-DWELL   207, the stock climb DOWN with no hang, hostscene raised once MOUNTED (the base, and its dwell clock, start there): its
            longest base age (base.age_ms) under 1.4 s and at least 0.2 s, and never out (THE ARRIVAL LAW in game); a longer one
            reads not-reached.
  D-DN      the D-UP extras on the climb down (the start pose regained by a bench-0 stock climb up, no host scene).
  M-352     [ff9mapkit netsync s159] THE ANCHOR (GUEST-TRAVERSAL-TWO-PC.md Finding 6): `selfdress self steiner`, the control latch
            VAR_GlobBool_158 cleared (`flag 158 0`: 351's inn rest clears it before Field(352), so 352's Main_Init never EnableMoves;
            a debug warp from 207 would inherit it set and give control), a RAW warp 352 entrance 3 at scenario 2505 (Session.warp
            waits for control, which the night scene never gives), hostscene 1 (Dali's inn night scene: Zidane_Init dresses the
            Zidane entry but skips its bind, Dagger_Init takes control -- s140's D3). Witnessed first (else not reached):
            dress.self.ctl_elsewhere +1 on 352 and
            stepout.anchor's ctl_uid != dressed_uid. Then OUT on the DRESSED body (stepout.uid == anchor.dressed_uid, dressed true)
            with its renderers 0 on every out sample, a GEO_MAIN_F0_ZDN stand-in shown, the controlled actor still lit
            (anchor.ctl_rends_on > 0), wire_mask 0, the mirror hidden. s158 stepped out on Dagger, undressed, and left Steiner lit.
  K-R       `reset` releases the lever (its line when the calibration held one); re-read with the role: lever null.

THE CALIBRATION (COOP_CALIBRATE=1): `stepout off` is pulled right after K2 and HELD. PREDICTED_OFF = U-UP, D-UP, D-DN, M-352 red, each
with OFF_MARKER (control went off past the dwell, never active, base.why_not "the stepout lever is off"); the negatives judge only
"never out" under the lever. K-CAL-M (judged before K-CAL) is green only when every predicted red carries its marker.
[ff9mapkit netsync s159] THE ANCHOR CALIBRATION (COOP_CALIBRATE=anchor): `stepout ctl` (s158's rule: anchor on the controlled actor)
is pulled right after K2 and HELD. PREDICTED_CTL = M-352 red alone (everywhere else the anchor IS the controlled actor), with
CTL_MARKER (out on the controlled actor -- uid == anchor.ctl_uid, not the dressed body -- and undressed).

NOT PROVEN HERE (selftest rows only, or the two-PC session): the FRESH-LINE start (no local talk is reachable solo: the bench's only
line is a relayed one, which the talk term blocks), the end on a talk or a climb started inside the episode (a relayed talk needs
bench 1, where every climb is a guest climb), the relayed talk's section-5 nonce half (a live lane only), the field and session ends,
the guest's own hide of the host's ghost (reason step_out: a CLIENT role), a host's zero-mask and option-C hides (a HOST role), the
stand-in's lighting, slice and blend copies (no stock slice on 207/114).

    py tools/play.py studies/test-harness/scenarios/coop_step_out.py --instance C:\\gd\\ff9-inst\\host
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_step_out.py --instance C:\\gd\\ff9-inst\\host
"""
from __future__ import annotations

import os
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
TALK_HOLD_S = 1.9                        # N-TALK's window once the line is open (past the 1.5 s dwell)
MOUNT_S = 3.0                            # a press to the mount (TimedTurn + the mount jump)
PART_MOVE_U = 50.0                       # a short held climb before the hang: about 3 of the loop's 20 u steps (207 has 13)
PART_HOLD_MAX_S = 1.0                    # ...measured in game units, never in frames (the render rate varies: review r2)
HANG_S = 2.4                             # the mid-ladder hang: past DwellMs (1.5 s) from control off, with margin
CLIMB_S = 15.0
LAND_S = 6.0
IN_BY_S = 1.5                            # an IN must land this soon after control (StepInMs 500 + the publish cadence)
DEBOUNCE_MIN_S = 0.4                     # ...and not before this (StepInMs 500, less two publishes)
RELIGHT_S = 0.25                         # the body's renderers come back at the next logic tick after the IN
DWELL_MIN_S, DWELL_MAX_S = 1.4, 2.3      # OUT by the dwell: never before 1.5 s of base (less a publish), and not long after
NDWELL_MAX_S = 1.4                       # N-DWELL discriminates only when its control-off span is shorter than this
DPOS_MAX = 80.0                          # one frame of ladder / mount motion: the copy runs in LateUpdate, the publish in an Update
NORM_TOL = 0.25                          # the stand-in's own clip time vs the body's (sampled one Update apart)
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
LADDER_LOOP_CLIP = "ANH_MAIN_F0_ZDN_LADDER_1_2"        # 207's Zidane_50 loop: RunAnimation(10539) every iteration, up and down
NDWELL_MIN_S = 0.2                                   # N-DWELL's base must have armed (else the leg proves nothing)

CLAIMS = {
    "K0": "the forced selftest role on 114 (newgame, warp 114, noencounter, `netsync selftest 1`, `bench 0`); a fresh process "
          "and |SelfTestOffset| < 640",
    "K1": "the s158 proof line 'step-out selftest: OK (N rows, M mutants caught, dwell 1500 ms, step-in 500 ms)' within 20 s, "
          "and `netsync.stepout.selftest` 'ok'",
    "K2": "`netsync.stepout` at rest before any lever: active false, lever null, wire_mask > 0, the mirror shown (shown_mask > 0), "
          "base.why_not 'the host has control'",
    "N-REST": "hostscene 1 with MY control on, 2 s: never active, why_not 'I have control', the mirror shown",
    "U-UP": "114 UNDRESSED, the stock climb up with a mid-ladder hang under hostscene 1: OUT by the dwell (1.4-2.3 s after control "
            "went off) with dressed false, wire_mask 0, the mirror hidden, the body's renderers on, no stand-in; IN 0.4-1.5 s after "
            "control (the debounce), in_why.control +1, the mask and the mirror back",
    "N-CLIMB": "a GUEST climb on 114 (bench 1), hostscene raised once mounted, a hang past the dwell: never out; a mid-climb sample "
               "has every other start term true and why_not 'my guest climb is in flight'",
    "N-TALK": "a RELAYED talk (`netsync talk 3`, JJY) under hostscene 1: never out over its fresh line and past the dwell; an armed "
              "sample has why_not 'a relayed talk owns my copy'; talk_accepts +1",
    "D-ARM": "207 DRESSED: `selfdress self steiner` then warp 207 -> dress.self.why 'dressed' on the controlled body; no stand-in",
    "D-UP": "207 DRESSED, the stock climb up with a mid-ladder hang under hostscene 1: OUT by the dwell with dressed true, body dark "
            "on every out sample, the shadow = stock's switch, a stand-in shown as GEO_MAIN_F0_ZDN playing the loop's LADDER_1_2 "
            "mid-ladder, its time moving and within 0.25 of the body's, within 80 u of the body, wire_mask 0, the mirror hidden; the "
            "shadow drawn in the step-in debounce; IN after control: body, mask and mirror back within a logic tick, the stand-in gone",
    "N-DWELL": "207, a stock climb down with NO hang, hostscene raised once mounted: a base held 0.2-1.4 s never steps out (THE "
               "ARRIVAL LAW in game)",
    "D-DN": "207 DRESSED, the stock climb down with a mid-ladder hang: the D-UP extras",
    "M-352": "352 entrance 3 at 2505 DRESSED (Dali's inn night scene: control on Dagger, the Zidane entry dressed), hostscene 1: "
             "witnessed by dress.self.ctl_elsewhere +1 on 352 and anchor.ctl_uid != anchor.dressed_uid; OUT on the DRESSED body "
             "(uid == anchor.dressed_uid, dressed true) with its renderers 0 on every out sample, a GEO_MAIN_F0_ZDN stand-in shown, "
             "the controlled actor lit (anchor.ctl_rends_on > 0), wire_mask 0, the mirror hidden",
    "K-R": "`reset` releases the lever (its line when the calibration held one); re-read with the role: lever null",
}
PREDICTED_OFF = ("U-UP", "D-UP", "D-DN", "M-352")
OFF_MARKER = "control off past the dwell; never active; base.why_not 'the stepout lever is off'"
# [ff9mapkit netsync s159] the anchor calibration (COOP_CALIBRATE=anchor: the `stepout ctl` lever, s158's rule)
CAL_MODE = os.environ.get("COOP_CALIBRATE", "").strip().lower()
CAL_CTL = CAL_MODE == "anchor"
PREDICTED_CTL = ("M-352",)
CTL_MARKER = "out on the controlled actor (uid == anchor.ctl_uid, not anchor.dressed_uid) and undressed"
M352_FIELD, M352_ENTRANCE, M352_SCENARIO = 352, 3, 2505     # Dali's inn night scene (351's rest sets entrance 3)
M352_LATCH = 158                                           # VAR_GlobBool_158: 352's Main_Init EnableMoves only when it is set
M352_ARRIVE_S = 15.0                                       # the warp to the D3 shape (Dagger_Init's bind after the dress)
M352_HOLD_S = 4.0                                          # past the dwell (the night scene's first line is ~7 s in)
FINALS = ("K-R", "K-CAL-M", "K-CAL")


def catalog(calibrate: bool, ctl: bool = False) -> dict:
    cat = dict(CLAIMS)
    if ctl:                                                 # [ff9mapkit netsync s159] the anchor calibration
        cat["K-CAL-M"] = "every predicted red carries its marker: " + CTL_MARKER
        cat["K-CAL"] = "the anchor calibration: exactly " + ", ".join(PREDICTED_CTL) + " red"
    elif calibrate:
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


def mirror_mask(x) -> int | None:
    """The mirror's enabled renderers as a mask (netsync.dress.ghost.shown_mask): 0 hidden, > 0 shown, None / -1 no mirror."""
    v = cb.path(x, "netsync.dress.ghost.shown_mask")
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def mirror_hidden(x) -> bool:
    return mirror_mask(x) == 0


def mirror_shown(x) -> bool:
    m = mirror_mask(x)
    return m is not None and m > 0


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


def first_t(samples, pred):
    s = next((x for x in samples if pred(x)), None)
    return None if s is None else s.get("_t")


def judge_dwell(samples) -> tuple:
    """OUT by the dwell: the first active sample is 'dwell' and lands DWELL_MIN_S..DWELL_MAX_S after control first went off."""
    t_off = first_t(samples, lambda s: not control(s))
    t_out = first_t(samples, lambda s: so_get(so(s), "active") is True)
    if t_off is None:
        return False, "control never went off"
    if t_out is None:
        return False, "never OUT"
    why = so_get(so(next(s for s in samples if so_get(so(s), "active") is True)), "why")
    dt = t_out - t_off
    ok = why == "dwell" and DWELL_MIN_S <= dt <= DWELL_MAX_S
    return ok, f"OUT {dt:.2f} s after control went off, why {why!r} (want 'dwell', {DWELL_MIN_S}-{DWELL_MAX_S} s)"


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
        if so_get(b, "wire_mask") != 0:
            bad.append(f"wire_mask {so_get(b, 'wire_mask')!r}")
        if not mirror_hidden(s):
            bad.append(f"mirror mask {mirror_mask(s)!r}")
        if not (isinstance(so_get(b, "body_rends_on"), int) and so_get(b, "body_rends_on") > 0):
            bad.append(f"body_rends_on {so_get(b, 'body_rends_on')!r}")
        if so_get(b, "standin.on") is not False:
            bad.append("a stand-in on an undressed body")
    ok_d, why_d = judge_dwell(samples)
    bad = sorted(set(bad)) + ([] if ok_d else ["dwell"])
    return not bad, (f"{len(outs)} of {len(offs)} control-off samples OUT; {why_d}"
                     + (f"; WRONG: {bad}" if bad else " (undressed, mask 0, mirror hidden, body on)"))


def _on_ladder(s, spec) -> bool:
    p = gt.pos(s)
    return p is not None and spec is not None and gt.on_ladder(p, spec)


def judge_out_dressed(samples, shadow_rest, spec=None) -> tuple:
    """D-UP / D-DN's OUT half: over the control-off samples. ``spec`` = the ladder (gt.LADDERS[207]) for the mid-ladder clip witness."""
    offs = off_samples(samples)
    outs = actives(offs)
    if not offs:
        return False, "control never went off (no climb)"
    if not outs:
        return False, f"never OUT over {len(offs)} control-off samples; why_not {sorted({str(so_get(so(s), 'base.why_not')) for s in offs})}"
    bad, clips, worst_d, worst_n, norms, ladder_clip = [], set(), 0.0, 0.0, set(), False
    prev_off = None
    for s in outs:
        b = so(s)
        if so_get(b, "dressed") is not True:
            bad.append("not dressed")
        if so_get(b, "body_rends_on") != 0:
            bad.append(f"body_rends_on {so_get(b, 'body_rends_on')!r}")
        off = so_get(b, "shadow_off")
        if shadow_rest in (0, 1) and off in (0, 1) and off == prev_off:     # stock's switch, steady for two samples (one tick)
            want = 1 if off == 0 and so_get(b, "stock_visible") is True else 0
            if so_get(b, "shadow") != want:
                bad.append(f"shadow {so_get(b, 'shadow')!r} where stock's switch says {want}")
        prev_off = off
        if so_get(b, "wire_mask") != 0:
            bad.append(f"wire_mask {so_get(b, 'wire_mask')!r}")
        if not mirror_hidden(s):
            bad.append(f"mirror mask {mirror_mask(s)!r}")
        if so_get(b, "standin.on") is not True or so_get(b, "standin.shown") is not True:
            bad.append("no stand-in shown")
            continue
        if so_get(b, "standin.geo") != STANDIN_GEO:
            bad.append(f"stand-in geo {so_get(b, 'standin.geo')!r}")
        clip = so_get(b, "standin.clip")
        clips.add(clip)
        if not (isinstance(clip, str) and "_ZDN_" in clip):
            bad.append(f"stand-in clip {clip!r}")
        if clip == LADDER_LOOP_CLIP and _on_ladder(s, spec):
            ladder_clip = True
        d = so_get(b, "standin.dpos")
        if not isinstance(d, (int, float)) or d < 0 or d > DPOS_MAX:
            bad.append(f"dpos {d!r}")
        else:
            worst_d = max(worst_d, float(d))
        n, bn = so_get(b, "standin.norm"), so_get(b, "standin.body_norm")
        if isinstance(n, (int, float)) and isinstance(bn, (int, float)) and n >= 0 and bn >= 0:
            worst_n = max(worst_n, circ(float(n), float(bn)))
            norms.add(round(float(n), 3))
            if circ(float(n), float(bn)) > NORM_TOL:
                bad.append(f"norm {n} vs body {bn}")
        else:
            bad.append(f"norm {n!r} / body_norm {bn!r}")
    if spec is not None and not ladder_clip:
        bad.append(f"no mid-ladder sample played the loop clip {LADDER_LOOP_CLIP}")
    if len(norms) < 2:
        bad.append(f"the stand-in's clip time never moved ({sorted(norms)})")
    ok_d, why_d = judge_dwell(samples)
    if not ok_d:
        bad.append("dwell")
    bad = sorted(set(bad))
    return not bad, (f"{len(outs)} of {len(offs)} control-off samples OUT; {why_d}; clips {sorted(c for c in clips if c)}; worst dpos "
                     f"{worst_d:.1f} u, worst |norm - body| {worst_n:.3f}, {len(norms)} distinct times"
                     + (f"; WRONG: {bad[:8]}" if bad else ""))


def judge_in(after, land_t: float | None, b0, *, dressed: bool) -> tuple:
    """The IN half: the first sample after control with active false lands DEBOUNCE_MIN_S..IN_BY_S after control, with in_why.control
    +1, the mask and the mirror back; the body's renderers are on by RELIGHT_S after it (a logic tick) and stay on; the stand-in is
    gone."""
    if land_t is None:
        return False, "no landing (control never came back)"
    first_in = next((s for s in after if so_get(so(s), "active") is False), None)
    if first_in is None:
        return False, f"still OUT {IN_BY_S:g} s after control ({len(after)} samples)"
    dt = first_in["_t"]
    b = so(first_in)
    later = [s for s in after if s["_t"] >= dt + RELIGHT_S]
    every = lambda pred: bool(later) and all(pred(s) for s in later)               # noqa: E731
    parts = [("debounce", DEBOUNCE_MIN_S <= dt <= IN_BY_S),
             ("in_why.control +1", so_get(b, "in_why.control", 0) == so_get(b0, "in_why.control", 0) + 1),
             ("wire_mask back", every(lambda s: isinstance(so_get(so(s), "wire_mask"), int) and so_get(so(s), "wire_mask") > 0)),
             ("mirror shown", every(mirror_shown)),
             ("body on", every(lambda s: isinstance(so_get(so(s), "body_rends_on"), int) and so_get(so(s), "body_rends_on") > 0))]
    if dressed:
        parts.append(("stand-in gone", all(so_get(so(s), "standin.on") is False for s in after if s["_t"] >= dt)))
    ok = all(v for _, v in parts)
    return ok, f"IN {dt:.2f} s after control; " + ", ".join(f"{k} {'ok' if v else 'NO'}" for k, v in parts)


def judge_shadow_debounce(after, shadow_rest) -> tuple:
    """THE SHADOW, where it can fail: the step-in debounce (active, control back), on samples whose stock switch (shadow_off) reads 0
    twice in a row (EnableShadow ran: one tick for its needUpdate) -- the blob shadow must be drawn. A shadow that followed the body's
    dark term would read 0 there. A field that draws no shadow at rest cannot judge it (a pass with that note)."""
    if shadow_rest != 1:
        return True, f"the field draws no shadow at rest ({shadow_rest!r}): not judged"
    judged, bad, prev = 0, 0, None
    for s in after:
        b = so(s)
        off = so_get(b, "shadow_off")
        if so_get(b, "active") is True and control(s) and off == 0 and prev == 0:
            judged += 1
            if so_get(b, "shadow") != 1:
                bad += 1
        prev = off
    if judged == 0:
        return False, "no debounce sample with stock's shadow switch on: the shadow was never judged"
    return bad == 0, f"{judged} debounce samples with stock's switch on, {bad} with the shadow dark"


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


def judge_short(samples, *, lever: bool = False) -> tuple:
    """N-DWELL: (verdict, why) -- verdict None = not discriminating (the base's dwell clock reached NDWELL_MAX_S). The span is the
    base's own age (base.age_ms: the dwell clock), never the control-off span: the base arms only when every term holds."""
    if not off_samples(samples):
        return False, "control never went off"
    ages = [so_get(so(s), "base.age_ms") for s in samples]
    ages = [a for a in ages if isinstance(a, int) and a >= 0]
    top = max(ages) / 1000.0 if ages else 0.0
    outs = actives(samples)
    if outs:
        return False, f"stepped OUT (why {so_get(so(outs[0]), 'why')!r}) after a base of {top:.2f} s"
    if lever:
        return True, f"never out over {len(samples)} samples (the lever: the base never arms, its clock reads -1)"
    if top < NDWELL_MIN_S:
        return False, f"the base never armed for {NDWELL_MIN_S} s (longest {top:.2f} s): the leg proves nothing"
    if top >= NDWELL_MAX_S:
        return None, f"the base held {top:.2f} s (>= {NDWELL_MAX_S} s): not a short episode"
    return True, f"the base held {top:.2f} s at most and never stepped out"


def anchor_of(x) -> dict:
    """[ff9mapkit netsync s159] `netsync.stepout.anchor` ({} when absent: an s158 engine)."""
    a = so_get(so(x), "anchor")
    return a if isinstance(a, dict) else {}


def d3_shape(x, field: int, ctl_elsewhere_before: int) -> bool:
    """M-352's precondition: on ``field``, a NEW ctl_elsewhere there (a co-actor bound control after the dress), and the anchor block
    names two different bodies (the controlled actor, the live dressed one)."""
    a = anchor_of(x)
    ce = cb.path(x, "netsync.dress.self.ctl_elsewhere")
    cef = cb.path(x, "netsync.dress.self.ctl_elsewhere_field")
    ctl, dressed = a.get("ctl_uid"), a.get("dressed_uid")
    return (gt.field_of(x) == field and isinstance(ce, int) and ce > ctl_elsewhere_before and cef == field
            and isinstance(ctl, int) and isinstance(dressed, int) and ctl >= 0 and dressed >= 0 and ctl != dressed)


def judge_m352(samples) -> tuple:
    """[ff9mapkit netsync s159] M-352: OUT, and every out sample acts on the DRESSED body -- uid == anchor.dressed_uid, dressed,
    its renderers 0, a ZDN stand-in shown -- while the controlled actor (anchor.ctl_uid) stays lit, the wire mask is 0 and the mirror
    hidden."""
    outs = actives(samples)
    if not outs:
        return False, f"never OUT over {len(samples)} samples (why_not {sorted({str(so_get(so(s), 'base.why_not')) for s in samples})})"
    bad = []
    for s in outs:
        b, a = so(s) or {}, anchor_of(s)
        dressed_uid, ctl_uid = a.get("dressed_uid"), a.get("ctl_uid")
        if not (isinstance(dressed_uid, int) and dressed_uid >= 0 and b.get("uid") == dressed_uid and dressed_uid != ctl_uid):
            bad.append(f"uid {b.get('uid')!r} (dressed {dressed_uid!r}, ctl {ctl_uid!r})")
        elif b.get("dressed") is not True:
            bad.append("undressed")
        elif b.get("body_rends_on") != 0:
            bad.append(f"body_rends_on {b.get('body_rends_on')!r}")
        elif not (isinstance(a.get("ctl_rends_on"), int) and a["ctl_rends_on"] > 0):
            bad.append(f"ctl_rends_on {a.get('ctl_rends_on')!r}")
        elif b.get("wire_mask") != 0:
            bad.append(f"wire_mask {b.get('wire_mask')!r}")
        elif not mirror_hidden(s):
            bad.append(f"mirror shown (shown_mask {mirror_mask(s)!r})")
    if bad:
        return False, f"{len(bad)} of {len(outs)} out samples wrong: {bad[0]}"
    shown = [s for s in outs if so_get(so(s), "standin.shown") is True and so_get(so(s), "standin.geo") == STANDIN_GEO]
    if not shown:
        return False, f"OUT on the dressed body but no {STANDIN_GEO} stand-in shown on any of {len(outs)} out samples"
    first = outs[0]
    return True, (f"OUT ({so_get(so(first), 'why')!r}) on the dressed uid {so_get(so(first), 'uid')!r}, control on uid "
                  f"{anchor_of(first).get('ctl_uid')!r} lit ({anchor_of(first).get('ctl_rends_on')!r} renderers); {len(outs)} out "
                  f"samples, the body dark on every one, the stand-in shown on {len(shown)}")


def ctl_marker(samples) -> tuple:
    """[ff9mapkit netsync s159] the anchor calibration's marker: out on the controlled actor, undressed, never the dressed body."""
    outs = actives(samples)
    on_ctl = [s for s in outs if so_get(so(s), "uid") == anchor_of(s).get("ctl_uid") != anchor_of(s).get("dressed_uid")]
    undressed = [s for s in on_ctl if so_get(so(s), "dressed") is False]
    parts = [("out", bool(outs)), ("on the controlled actor", bool(on_ctl) and len(on_ctl) == len(outs)),
             ("undressed", bool(undressed) and len(undressed) == len(on_ctl))]
    return all(v for _, v in parts), ", ".join(f"{k} {'ok' if v else 'NO'}" for k, v in parts)


def off_marker(samples) -> tuple:
    offs = off_samples(samples)
    span = (offs[-1]["_t"] - offs[0]["_t"]) if offs else 0.0
    named = [s for s in offs if so_get(so(s), "base.why_not") == WHY_NOT_LEVER]
    parts = [("control off past the dwell", span >= DWELL_MIN_S), ("never active", not actives(samples)),
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
    cb.poll(g, lambda s: so_get(so(s), "base.host_ctl_off") is on or not on, 2.0, f"hostscene {int(on)} read back")


def _stamp(samples, t0: float) -> list:
    return gt._stamp(samples, t0)


def watch_after(g, t_land: float) -> list:
    """Every publish for IN_BY_S + RELIGHT_S + 0.3 s after control, each stamped with its seconds since control."""
    out = []
    seen = None
    deadline = t_land + IN_BY_S + RELIGHT_S + 0.3
    while time.time() < deadline:
        st = g.state
        if st.frame != seen:
            seen = st.frame
            d = dict(cb.raw(st))
            d["_t"] = time.time() - t_land
            out.append(d)
        time.sleep(0.004)
    return out


def hang_climb(g, ctx: Ctx, leg: str, fid: int, direction: str, *, bench: bool, scene_before: bool, scene_on_mount: bool = False,
               hang: bool = True) -> dict:
    """The start pose, `bench`, hostscene (before the press, or once mounted), the press, the mount, a short hold, a HANG past the
    dwell (no key: the climb loop waits), the rest of the climb (gt.climb_hold, released at the exit bound), the landing, then every
    publish for ~2 s after control. hostscene is dropped at the end, at rest. Every sample is stamped from the press."""
    spec = gt.LADDERS[fid]
    pose = "bottom" if direction == "up" else "top"
    ok, why = gt.ensure_pose(g, ctx.gt, leg, fid, pose)
    if not ok:
        raise HarnessError(f"{leg}: the start pose ({pose}) failed: {why}")
    ok, why = gt.set_bench(g, bench)
    if not ok:
        raise HarnessError(f"{leg}: bench {int(bench)} failed: {why}")
    entry = spec["entry_up"] if direction == "up" else spec["entry_down"]
    mount = spec["mount_bottom"] if direction == "up" else spec["mount_top"]
    res = gt.press_rec(g, ctx.gt, leg, fid, entry)
    res["b0"] = so(gt.rest(g, 3.0))
    res["shadow_rest"] = so_get(res["b0"], "shadow")
    if scene_before:
        hostscene(g, True)
    t0 = time.time()
    g.press("confirm", 2)
    samples, hit = cb.watch(g, lambda s: gt.is_mounted(s, mount), MOUNT_S)
    res["samples"] = _stamp(samples, t0)
    if hit is None:
        res["mounted"] = False
        gt._close_rec(g, res)
        gt.recover(g, fid)
        return res
    res["mounted"] = True
    if scene_on_mount:
        hostscene(g, True)
    button = spec["buttons"][direction]
    if hang:
        y0 = (gt.pos(g.state) or (0.0, float(mount[1]), 0.0))[1]
        g.hold(button, 600)
        try:
            part, _hit = cb.watch(g, lambda s: abs(((gt.pos(s) or (0.0, y0, 0.0))[1]) - y0) >= PART_MOVE_U or control(s),
                                  PART_HOLD_MAX_S)
        finally:
            try:
                g.release(button)
            except HarnessError:
                pass
        res["samples"] += _stamp(part, t0)
        res["samples"] += _stamp(cb.hold_for(g, HANG_S), t0)
    c = gt.climb_hold(g, spec, direction, t0)
    res["samples"] += c["samples"]
    res["crossed"] = c["crossed"]
    tail, hit = cb.watch(g, lambda s: control(s), LAND_S)
    res["samples"] += _stamp(tail, t0)
    res["land"] = dict(cb.raw(hit)) if hit is not None else None
    res["land_at"] = time.time() if hit is not None else None
    res["after"] = watch_after(g, res["land_at"]) if res["land_at"] is not None else []
    try:
        hostscene(g, False)
    finally:
        gt.rest(g)
    return res


def run(g, field: int | None = None):
    ctl_cal = CAL_CTL                                      # [ff9mapkit netsync s159] COOP_CALIBRATE=anchor: the `ctl` lever
    calibrate = cb.CALIBRATE and not ctl_cal               # the `off` lever (COOP_CALIBRATE=1)
    st0 = cb.poll(g, lambda s: s.netsync is not None, 15.0, "the netsync block (protocol 5)") or g.state
    ctx = Ctx(calibrate)
    led = cb.Ledger(g, catalog(calibrate, ctl_cal), finals=FINALS, width=1600)
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
        if ctl_cal:
            ok, why = _ns(g, "stepout", "ctl")
            st = cb.poll(g, lambda s: so_get(so(s), "lever") == "ctl", 3.0, "the ctl lever read back")
            ctx.lever_held = ok and st is not None
            g.note(f"ANCHOR CALIBRATION: `stepout ctl` {'taken' if ok else 'REFUSED: ' + why}, held for the whole run; predicted "
                   f"red {', '.join(PREDICTED_CTL)}")
        _field_114(g, ctx, led)
        _field_207(g, ctx, led)
        _field_352(g, ctx, led)                            # [ff9mapkit netsync s159]
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
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'step-out-' + ('anchor' if ctl_cal else 'lever' if calibrate else 'plain'))}")
        if ctl_cal:                                        # [ff9mapkit netsync s159]
            led.close("not reached: the run ended before this check")
            marks_ok = all(leg in ctx.marks and ctl_marker(ctx.marks[leg])[0] for leg in PREDICTED_CTL)
            led.check("K-CAL-M", marks_ok, "; ".join(f"{leg}: {ctl_marker(ctx.marks[leg])[1] if leg in ctx.marks else 'NO RUN'}"
                                                     for leg in PREDICTED_CTL))
            led.judge_calibration("K-CAL", PREDICTED_CTL)
        elif calibrate:
            led.close("not reached: the run ended before this check")
            marks_ok = all(leg in ctx.marks and off_marker(ctx.marks[leg])[0] for leg in PREDICTED_OFF)
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
             ("mirror shown", mirror_shown(st)),
             ("why_not " + WHY_NOT_HOST_CONTROL, so_get(b, "base.why_not") == WHY_NOT_HOST_CONTROL)]
    led.check("K2", all(v for _, v in parts), ", ".join(f"{k} {'ok' if v else 'NO'}" for k, v in parts)
              + f"; why_not {so_get(b, 'base.why_not')!r}, wire_mask {so_get(b, 'wire_mask')!r}, mirror mask {mirror_mask(st)!r}")


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
    shown = all(mirror_shown(s) for s in samples)
    led.check("N-REST", ok and shown, why + ("" if shown else "; the mirror HID with my control on"))


def _u_up(g, ctx, led):
    res = hang_climb(g, ctx, "U-UP", 114, "up", bench=False, scene_before=True)
    samples = res.get("samples") or []
    if ctx.calibrate:
        ctx.marks["U-UP"] = samples
    ok1, why1 = judge_out_undressed(samples)
    ok2, why2 = judge_in(res.get("after") or [], res.get("land_at"), res["b0"], dressed=False)
    led.check("U-UP", ok1 and ok2, f"OUT: {why1} || IN: {why2}")


def _n_climb(g, ctx, led):
    res = hang_climb(g, ctx, "N-CLIMB", 114, "down", bench=True, scene_before=False, scene_on_mount=True)
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
    need = (lambda s: so_get(so(s), "base.host_ctl_off") is True and so_get(so(s), "base.my_ctl_off") is True
            and so_get(so(s), "base.talk") is True)
    ok, why = judge_never(samples, lever=ctx.calibrate, why_not=WHY_NOT_TALK, need=need)
    accepts = so_get(b1, "talk_accepts", 0) - so_get(b0, "talk_accepts", 0)
    led.check("N-TALK", opened is not None and ok and accepts == 1,
              (why if opened is not None else "the relayed talk never opened a window with control off") + f"; talk_accepts +{accepts}")


def _field_207(g, ctx: Ctx, led: cb.Ledger) -> None:
    legs = [c for c in ("D-ARM", "D-UP", "N-DWELL", "D-DN") if c in led.catalog]
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
        led.unreached(["D-UP", "N-DWELL", "D-DN"], "D-ARM: the body is not dressed")
        return
    _guard(g, led, "D-UP", 207, lambda: _d_climb(g, ctx, led, "D-UP", "up"))
    _guard(g, led, "N-DWELL", 207, lambda: _n_dwell(g, ctx, led))
    _guard(g, led, "D-DN", 207, lambda: _d_climb(g, ctx, led, "D-DN", "down"))


def _field_352(g, ctx: Ctx, led: cb.Ledger) -> None:
    """[ff9mapkit netsync s159] M-352: the anchor on Dali's inn night scene (a co-actor binder holds control)."""
    if "M-352" not in led.catalog:
        return
    gt.set_bench(g, False)
    ok, why = _ns(g, "selfdress", "self", "steiner")
    if not ok:
        led.unreached(["M-352"], f"`selfdress self steiner` refused: {why}")
        return
    before = cb.path(g.state, "netsync.dress.self.ctl_elsewhere")
    before = before if isinstance(before, int) else 0
    try:
        g.poke(13, 0)
        g.poke(14, 0)
        g.flag(M352_LATCH, False)                          # the real path's latch: 352 keeps control off (no EnableMove)
    except (HarnessError, AttributeError) as err:
        led.unreached(["M-352"], f"warp {M352_FIELD}: the env-slot / latch pokes refused ({str(err)[:160]})")
        return
    # a RAW warp step: Session.warp waits for control (wait_playable), which the night scene never gives (cutscene_check.py)
    ok, why = cb.try_send(g, f"warp {M352_FIELD} {M352_ENTRANCE} {M352_SCENARIO}")
    if not ok:
        led.unreached(["M-352"], f"warp {M352_FIELD} entrance {M352_ENTRANCE} refused: {why}")
        return
    st = cb.poll(g, lambda s: d3_shape(s, M352_FIELD, before), M352_ARRIVE_S, "352's D3 shape (control on a co-actor)")
    if st is None:
        x = g.state
        led.unreached(["M-352"], f"no D3 shape on {M352_FIELD}: field {gt.field_of(x)!r}, ctl_elsewhere "
                                 f"{cb.path(x, 'netsync.dress.self.ctl_elsewhere')!r} (before {before}) on "
                                 f"{cb.path(x, 'netsync.dress.self.ctl_elsewhere_field')!r}, anchor {anchor_of(x)!r}")
        return
    try:
        hostscene(g, True)
        t0 = time.time()
        samples = _stamp(cb.hold_for(g, M352_HOLD_S), t0)
    finally:
        try:
            hostscene(g, False)
        except HarnessError:
            pass
    ctx.marks["M-352"] = samples
    ok, why = judge_m352(samples)
    led.check("M-352", ok, why)
    # the night scene never gives control back and the host's state never ends an episode: the `off` lever ends it (in_why.lever)
    # before K-R's reset, and the end is witnessed (an episode left out is NOTED -- K-R's reset would end it as "session")
    ok, why = _ns(g, "stepout", "off")
    st = cb.poll(g, lambda s: so_get(so(s), "active") is False, 3.0, "the M-352 episode ended") if ok else None
    if st is None:
        g.note(f"M-352: the episode did not end on the off lever ({why or 'still active after 3 s'}); K-R's reset ends it")


def _d_climb(g, ctx, led, leg: str, direction: str):
    res = hang_climb(g, ctx, leg, 207, direction, bench=False, scene_before=True)
    samples = res.get("samples") or []
    if ctx.calibrate:
        ctx.marks[leg] = samples
    ok1, why1 = judge_out_dressed(samples, res.get("shadow_rest"), gt.LADDERS[207])
    ok2, why2 = judge_in(res.get("after") or [], res.get("land_at"), res["b0"], dressed=True)
    ok3, why3 = judge_shadow_debounce(res.get("after") or [], res.get("shadow_rest"))
    led.check(leg, ok1 and ok2 and ok3, f"OUT: {why1} || IN: {why2} || SHADOW: {why3}; shadow at rest {res.get('shadow_rest')!r}")


def _n_dwell(g, ctx, led):
    res = hang_climb(g, ctx, "N-DWELL", 207, "down", bench=False, scene_before=False, scene_on_mount=True, hang=False)
    verdict, why = judge_short(res.get("samples") or [], lever=ctx.calibrate)
    if verdict is None:
        led.unreached(["N-DWELL"], why)
        return
    led.check("N-DWELL", verdict, why)


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
