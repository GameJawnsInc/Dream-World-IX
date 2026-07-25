"""NIMBRA's three clips -- ``emerge`` / ``drift`` / ``strike`` (STORYBOARD 1.7), authored as raw curves.

PURE (stdlib only) so the headless-Blender offline eye can import it and pose the rig with EXACTLY the
numbers the ``.anim`` files carry -- one source of truth for the motion, no re-typing.

Each builder returns ``{boneNum: {"rot": [(t_seconds, (x,y,z,w)), ...], "pos": [...]}}`` -- the shape
``models/anim.py:new_clip`` consumes. Every unkeyed bone gets a static rest channel from ``new_clip``
itself (``anim.py:551-556``), which is why the neck can be keyed here and the arm points left alone
without the engine's head-focus offset accumulating anywhere.

--------------------------------------------------------------------------------------------------
THE PLAYLIST-SEAM RULE (STORYBOARD 1.7), and the one place it is read literally
--------------------------------------------------------------------------------------------------
``SFXDataMesh.cs:845-869`` chains ``Animations[]`` with NO blending -- it hard-sets ``clipState.time``.
So every SEAM must be pose-continuous. The playlist is

    emerge | driftlook | strike | drift

(the shipped build's ``emerge | drift | drift | strike | drift | drift`` before the 2026-07-24 retime)
and its internal seams are emerge->drift, drift->drift, drift->strike, strike->drift. This module
makes every one of them exact by pinning the shared pose to the model's own REST pose:

  * ``drift`` uses ``wave(t, phase, amp) = amp * (sin(2*pi*t + phase) - sin(phase))`` -- a phase-offset
    sine RECENTRED so it is exactly 0 at t=0 AND t=1. That buys the phase-offset travelling wave the
    storyboard asks for while keeping frame 0 == frame N-1 == rest, so ``drift`` is perfectly loopable
    and both its ends match everything else.
  * ``emerge`` ENDS at rest; ``strike`` STARTS and ENDS at rest.
  * ``emerge``'s FIRST frame is the only boundary that is NOT rest -- it is the collapsed/folded pose,
    which is what STORYBOARD 1.7's own description of the clip requires ("veil ribbons collapsed inward
    at the root and unfurling ... arms unfolding from crossed"). It is also the only clip boundary in
    the whole playlist with no predecessor: it is manifest frame 0, played at Scaling 0.15 inside a
    full blackout. There is no seam there to pop. Flagged for the storyboard, not silently deviated.

--------------------------------------------------------------------------------------------------
FRAME COUNTS -- and THE SPEED-DIVISOR DEFECT (2026-07-24, adversarial round: STORYBOARD 11.9)
--------------------------------------------------------------------------------------------------
Keys sit at f = 0 .. N-1 at 30 fps, so the clip's LENGTH is (N-1)/30 s and Unity reports N frames.

STORYBOARD 1.7's "Speed compensation" equation read TWO of the three lines that drive a playlist --
``animMaxFrame = ceil(N / Speed)`` and ``animFrame = floor(ticks * Speed)`` -- and never checked the
third, the line that actually poses the rig:

    SFXDataMesh.cs:869   clipState.time = clipState.length * animFrame / animMaxFrame[animIndex];

``animFrame`` is a CLIP-FRAME index; ``animMaxFrame`` is a TICK count. They are equal only at
**Speed 1**, and line 863's exhausted branch (``animFrame = animMaxFrame`` -> ``time = length``)
proves the divisor was meant to be "animFrame's value at the end of the clip" -- i.e. ~N, not
animMaxFrame. So at Speed s a clip advances s^2 clip-frames per tick: it finishes after 1/s of its
entry and FREEZES for the rest. ``playlist_sim.py`` prints the trajectory; on the retimed playlist it
measured emerge frozen 12 of 15 ticks, the look frozen 16 of 25, strike frozen 15 of 30 -- and the
lunge peak landing at t 74 against a .seq that fires the flash at t 83.

**THEREFORE: EVERY entry is authored at Speed 1 and the CLIP is sized to its beat.** Speed 1 is the
only value at which both readings of line 869 agree, so this is correct whichever reading is right.
The tick table, the window and the entry boundaries are UNCHANGED -- only where the frames come from:

    emerge     N=15  Speed=1 ->  15 ticks   (frames   0..15)   the rise
    driftlook  N=25  Speed=1 ->  25 ticks   (frames  15..40)   THE LOOK
    strike     N=30  Speed=1 ->  30 ticks   (frames  40..70)   wind-back + the lunge peak + settle
    drift      N=75  Speed=1 ->  75 ticks   (frames  70..145)  the eerie half-speed sway, UNCHANGED

``drift`` keeps N=75 and is bit-identical to the shipped build (it was already the one correct entry).
``emerge`` and ``strike`` are RE-CUT: the same authored envelopes, breakpoints scaled by (N-1)/(REF-1),
so the motion is the identical shape resampled onto its own tick count. At Speed 1 the sampler shows
exactly one clip frame per tick, so a 15-tick rise shows 15 distinct poses either way -- the re-cut
costs no fidelity, it just makes those poses the RIGHT ones. ``driftlook`` is ``drift``'s own builder
at N=25 (it is normalized on ``u = f/(N-1)``, so this is a pure resample of one full sine cycle).

The playlist is ``emerge | driftlook | strike | drift`` -- the same four seam KINDS as before, and
every clip still opens and closes on the shared rest pose (asserted below).
"""
from __future__ import annotations

import math

from nimbra_spec import BONE_NUM

RATE = 30.0

#: the clips as SHIPPED -- one entry each, every playlist entry at Speed 1 (see the docstring).
N_EMERGE, N_DRIFT, N_STRIKE, N_DRIFTLOOK = 15, 75, 30, 25

#: the frame counts the envelopes below were AUTHORED against (STORYBOARD 1.7's shape). Breakpoints are
#: written in these reference frames and scaled to the shipped N by :func:`rescale`, so the storyboard's
#: own numbers ("frames 0-24 wind-back, 24-36 lunge, 36-60 settle") stay readable in the source.
REF_EMERGE, REF_STRIKE = 90, 60


def rescale(keys, ref_n, n):
    """Map envelope breakpoints authored against ``ref_n`` frames onto a clip of ``n`` frames.

    Proportional in the clip's own normalized time: ``f -> f * (n - 1) / (ref_n - 1)``. Endpoints are
    exact (0 -> 0, ref_n-1 -> n-1), which is what keeps THE PLAYLIST-SEAM RULE's rest-pose ends intact
    after a re-cut."""
    k = (n - 1) / (ref_n - 1)
    return [(f * k, v) for (f, v) in keys]


# --------------------------------------------------------------------------- quaternion helpers

def qaxis(axis, deg):
    """Quaternion (x,y,z,w) for ``deg`` degrees about ``axis`` (need not be normalized)."""
    ax, ay, az = axis
    n = math.sqrt(ax * ax + ay * ay + az * az) or 1.0
    h = math.radians(deg) / 2.0
    s = math.sin(h) / n
    return (ax * s, ay * s, az * s, math.cos(h))


def qmul(a, b):
    """Unity Hamilton product a*b -- 'apply b first, then a'."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def qchain(*qs):
    out = (0.0, 0.0, 0.0, 1.0)
    for q in qs:
        out = qmul(out, q)
    return out


IDENT = (0.0, 0.0, 0.0, 1.0)
X, Y, Z = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)


# --------------------------------------------------------------------------- easing / envelopes

def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def env(keys):
    """A smoothstep-interpolated envelope from [(frame, value), ...] (frames ascending)."""
    ks = sorted(keys)

    def at(f):
        if f <= ks[0][0]:
            return ks[0][1]
        if f >= ks[-1][0]:
            return ks[-1][1]
        for i in range(len(ks) - 1):
            f0, v0 = ks[i]
            f1, v1 = ks[i + 1]
            if f0 <= f <= f1:
                return v0 + (v1 - v0) * smooth((f - f0) / (f1 - f0)) if f1 > f0 else v0
        return ks[-1][1]
    return at


def wave(t, phase, amp):
    """A phase-offset sine RECENTRED to be exactly 0 at t=0 and t=1 -- the loop-safe travelling wave.
    See the module docstring: this is what lets ``drift`` carry a per-ribbon phase AND still open and
    close on the shared rest pose."""
    return amp * (math.sin(2.0 * math.pi * t + phase) - math.sin(phase))


# --------------------------------------------------------------------------- the veil's swing axes
# For ribbon i (azimuth 45 + 90i degrees): r = the outward radial, a = r x y_down. Rotating a veil bone
# by +theta about ``a`` swings its ribbon INWARD toward the central axis; rotating about ``r`` sways it
# sideways. The veil bones parent to bone000, whose rest rotation is identity -- so the parent frame IS
# the world frame and these world axes are usable verbatim.

def veil_axes(i):
    az = math.radians(45.0 + 90.0 * i)
    r = (math.sin(az), 0.0, math.cos(az))
    a = (-math.cos(az), 0.0, math.sin(az))
    return r, a


VEIL_BONES = [BONE_NUM["bone011"], BONE_NUM["bone012"], BONE_NUM["bone013"]]


# --------------------------------------------------------------------------- clip 1: EMERGE
# "Veil ribbons collapsed inward at the root and unfurling; neck bowed, mask rising to level; arms
# unfolding from crossed." Paired in the manifest with Scaling 0.15 -> 1.0 so the unfurl and the growth
# are one gesture. ENDS at rest (STORYBOARD 1.7).

def build_emerge() -> dict:
    N = N_EMERGE
    R = REF_EMERGE                  # breakpoints stay written in the AUTHORED 90-frame shape
    # envelopes are 1.0 at the folded start and 0.0 at rest; each limb releases on its own schedule
    e_veil = env(rescale([(0, 1.0), (14, 0.92), (58, 0.18), (R - 1, 0.0)], R, N))   # veil first + longest
    e_arm = env(rescale([(0, 1.0), (20, 0.95), (66, 0.12), (R - 1, 0.0)], R, N))    # arms uncross late
    e_neck = env(rescale([(0, 1.0), (34, 0.86), (74, 0.10), (R - 1, 0.0)], R, N))   # the mask levels LAST
    e_spine = env(rescale([(0, 1.0), (46, 0.40), (R - 1, 0.0)], R, N))

    curves = {b: {"rot": []} for b in (
        BONE_NUM["bone001"], BONE_NUM["bone002"], BONE_NUM["bone003"], BONE_NUM["bone004"],
        BONE_NUM["bone005"], BONE_NUM["bone006"], BONE_NUM["bone007"], BONE_NUM["bone008"],
        *VEIL_BONES)}

    for f in range(N):
        t = f / RATE
        kv, ka, kn, ks = e_veil(f), e_arm(f), e_neck(f), e_spine(f)

        # --- spine: a forward curl that straightens (the thing is unfolding out of the mist) -------
        curves[BONE_NUM["bone001"]]["rot"].append((t, qaxis(X, -13.0 * ks)))
        curves[BONE_NUM["bone002"]]["rot"].append((t, qaxis(X, -9.0 * ks)))
        # --- neck bowed / mask face-down, rising to level -----------------------------------------
        # A big NEGATIVE bone003 X shoves the plate forward as much as it lowers it (the child sits
        # 135u along -Y, so sin(theta) is pure Z travel); keep the bow modest and let bone004 carry
        # the "looking at the ground" read.
        curves[BONE_NUM["bone003"]]["rot"].append((t, qaxis(X, -26.0 * kn)))
        curves[BONE_NUM["bone004"]]["rot"].append((t, qchain(qaxis(X, 34.0 * kn),
                                                             qaxis(Y, 7.0 * kn))))
        # --- arms unfolding from CROSSED (in front of the core) -----------------------------------
        # SIGN: for the LEFT arm (side=-1, hanging at x<0) the limb direction is ~(-0.06, 1, 0) and a
        # Z rotation sends x' = x*cos - y*sin; crossing toward the midline needs x' > 0, i.e. a
        # NEGATIVE angle. So the angle is +55*side, not -55*side -- the first draft had the sign
        # inverted and the offline eye showed a bird with its wings out.
        for side, sh, fa in ((-1.0, "bone005", "bone007"), (1.0, "bone006", "bone008")):
            curves[BONE_NUM[sh]]["rot"].append(
                (t, qchain(qaxis(Z, 58.0 * side * ka), qaxis(X, 22.0 * ka))))
            curves[BONE_NUM[fa]]["rot"].append(
                (t, qchain(qaxis(Z, 36.0 * side * ka), qaxis(X, 14.0 * ka))))
        # --- veil: collapsed inward at the root, unfurling with a per-ribbon lag -------------------
        for i, b in enumerate(VEIL_BONES):
            r, a = veil_axes(i)
            lag = 1.0 + 0.10 * i                       # ribbons release fractionally out of step
            k = max(0.0, min(1.0, kv * lag))
            curves[b]["rot"].append((t, qchain(qaxis(a, 74.0 * k), qaxis(r, 16.0 * k * (1 if i % 2 else -1)))))

    _assert_ends_at_rest(curves, N, "emerge", check_start=False)
    return curves


# --------------------------------------------------------------------------- clip 2: DRIFT
# LOOPABLE. Root Y +/- 14u over one full sine cycle; the mask counter-rotates +/- 5 deg; the four
# ribbons carry a phase-offset travelling wave; the arms trail one beat behind the core. Played at
# Speed = 1 -- deliberate HALF speed: everything else in the frame moves at battle tempo, NIMBRA
# does not (STORYBOARD 1.7).

ROOT_REST_Y = -740.0        # bone000's rest local pos y -- a pos curve REPLACES localPosition


def build_drift(n: int = None) -> dict:
    """One full sine cycle over ``n`` frames. Everything below is keyed on ``u = f/(N-1)``, so this
    builder is length-agnostic: ``drift`` (N=75, the eerie 5 s tail) and ``driftlook`` (N=25, THE LOOK)
    are the SAME motion resampled, not two authored clips."""
    N = N_DRIFT if n is None else n
    root, chest, mask = BONE_NUM["bone000"], BONE_NUM["bone002"], BONE_NUM["bone004"]
    curves = {root: {"pos": []}, chest: {"rot": []}, mask: {"rot": []},
              BONE_NUM["bone005"]: {"rot": []}, BONE_NUM["bone006"]: {"rot": []},
              BONE_NUM["bone007"]: {"rot": []}, BONE_NUM["bone008"]: {"rot": []}}
    for b in VEIL_BONES:
        curves[b] = {"rot": []}

    for f in range(N):
        t = f / RATE
        u = f / (N - 1)                                # 0 -> 1 across exactly one cycle

        # --- the bob: root Y +/- 14u (Y-DOWN, so -14 is the top of the rise) ----------------------
        curves[root]["pos"].append((t, (0.0, ROOT_REST_Y - wave(u, 0.0, 14.0), 0.0)))
        # --- the core sways, the mask COUNTER-rotates ---------------------------------------------
        curves[chest]["rot"].append((t, qchain(qaxis(Y, wave(u, 0.0, 5.0)),
                                               qaxis(Z, wave(u, 1.05, 2.6)))))
        curves[mask]["rot"].append((t, qchain(qaxis(Y, wave(u, math.pi, 5.0)),   # the spec's +/-5
                                              qaxis(X, wave(u, 0.6, 3.0)))))
        # --- the arms trail one beat behind the core (a ~0.55-cycle lag) ---------------------------
        for side, sh, fa in ((-1.0, "bone005", "bone007"), (1.0, "bone006", "bone008")):
            curves[BONE_NUM[sh]]["rot"].append(
                (t, qchain(qaxis(X, wave(u, -0.55 * 2 * math.pi, 6.0)),
                           qaxis(Z, wave(u, -0.55 * 2 * math.pi + 0.4, 4.0 * side)))))
            curves[BONE_NUM[fa]]["rot"].append(
                (t, qaxis(X, wave(u, -0.80 * 2 * math.pi, 7.0))))
        # --- the travelling wave down the veil -----------------------------------------------------
        # AMPLITUDE: a veil bone sits at MID-ribbon, so ~370u of ribbon swings past it -- 15 degrees
        # is a ~95u travel at the tip. The first pass used 8/5.5 and the offline eye could not see the
        # wave at all across six sampled frames, which for the clip that carries the whole 12-second
        # hang is a failure, not restraint.
        for i, b in enumerate(VEIL_BONES):
            r, a = veil_axes(i)
            ph = i * (2.0 * math.pi / 3.0)             # a third of a cycle between neighbours
            curves[b]["rot"].append((t, qchain(qaxis(a, wave(u, ph, 15.0)),
                                               qaxis(r, wave(u, ph + 1.9, 9.0)))))

    _assert_ends_at_rest(curves, N, "drift", check_start=True)
    _assert_loop(curves, "drift")
    return curves


# --------------------------------------------------------------------------- clip 3: STRIKE
# 0-24 a slow wind-back (arms drawing up and behind, mask tipping down); 24-36 a fast forward lunge of
# both arm-points, mask snapping level; 36-60 settle back to the drift rest pose.

def build_strike() -> dict:
    N = N_STRIKE
    R = REF_STRIKE                  # breakpoints stay written in the AUTHORED 60-frame shape
    # one shared shape function: negative = wound back, positive = lunged. THE LUNGE PEAK is the
    # `(36, 1.0)` breakpoint -- 36/59 of the clip, which at N=30 / Speed 1 shows at t 83 (STORYBOARD
    # 11.9): the exact tick nimbra.seq fires the sting, the rift-flash and the relight.
    drive = env(rescale([(0, 0.0), (24, -1.0), (30, 0.55), (36, 1.0), (46, -0.12), (R - 1, 0.0)], R, N))
    # the mask has its own beat: tips down through the wind-back, SNAPS level on the lunge
    mask_tip = env(rescale([(0, 0.0), (24, 1.0), (33, -0.22), (44, 0.06), (R - 1, 0.0)], R, N))
    veil_drag = env(rescale([(0, 0.0), (28, -0.8), (40, 1.0), (52, -0.2), (R - 1, 0.0)], R, N))

    keyed = [BONE_NUM[n] for n in ("bone002", "bone003", "bone004", "bone005", "bone006",
                                   "bone007", "bone008", "bone009", "bone010")] + VEIL_BONES
    curves = {b: {"rot": []} for b in keyed}

    for f in range(N):
        t = f / RATE
        d, mt, vd = drive(f), mask_tip(f), veil_drag(f)

        curves[BONE_NUM["bone002"]]["rot"].append((t, qaxis(X, 7.0 * d)))
        curves[BONE_NUM["bone003"]]["rot"].append((t, qaxis(X, -9.0 * mt)))
        curves[BONE_NUM["bone004"]]["rot"].append((t, qaxis(X, 30.0 * mt)))
        for side, sh, fa, pt in ((-1.0, "bone005", "bone007", "bone009"),
                                 (1.0, "bone006", "bone008", "bone010")):
            # wind-back: up and BEHIND (X negative raises + pushes -Z). Lunge: X positive drives +Z.
            curves[BONE_NUM[sh]]["rot"].append(
                (t, qchain(qaxis(X, 47.0 * d), qaxis(Z, 9.0 * side * max(0.0, -d)))))
            curves[BONE_NUM[fa]]["rot"].append((t, qaxis(X, 30.0 * d)))
            curves[BONE_NUM[pt]]["rot"].append((t, qaxis(X, 17.0 * d)))
        for i, b in enumerate(VEIL_BONES):
            r, a = veil_axes(i)
            curves[b]["rot"].append((t, qchain(qaxis(a, -13.0 * vd), qaxis(r, 4.0 * vd * (1 if i % 2 else -1)))))

    _assert_ends_at_rest(curves, N, "strike", check_start=True)
    return curves


# --------------------------------------------------------------------------- seam / loop assertions

_REST = {"rot": (0.0, 0.0, 0.0, 1.0), "pos": None, "scale": (1.0, 1.0, 1.0)}


def _rest_value(chan, bone_num):
    if chan == "pos":
        from nimbra_spec import build_bones
        return tuple(build_bones()[bone_num]["pos"])
    return _REST[chan]


def _close(a, b, eps=1e-6):
    return all(abs(x - y) <= eps for x, y in zip(a, b))


def _assert_ends_at_rest(curves, n, name, *, check_start):
    """THE PLAYLIST-SEAM RULE, enforced in code rather than trusted to the author's arithmetic."""
    for bn, ch in curves.items():
        for chan, keys in ch.items():
            assert len(keys) == n, f"{name}: bone{bn:03d}.{chan} has {len(keys)} keys, expected {n}"
            rest = _rest_value(chan, bn)
            if check_start and not _close(keys[0][1], rest):
                raise AssertionError(f"{name}: bone{bn:03d}.{chan} frame 0 {keys[0][1]} != rest {rest}")
            if not _close(keys[-1][1], rest):
                raise AssertionError(f"{name}: bone{bn:03d}.{chan} frame {n-1} {keys[-1][1]} != rest {rest}")


def _assert_loop(curves, name):
    for bn, ch in curves.items():
        for chan, keys in ch.items():
            if not _close(keys[0][1], keys[-1][1]):
                raise AssertionError(f"{name}: bone{bn:03d}.{chan} is not loopable "
                                     f"({keys[0][1]} vs {keys[-1][1]})")


# --------------------------------------------------------------------------- registry

CLIPS = [
    # (name, builder, frames, the clip's FIRST playlist Speed, .anim numeric key)
    # The Speed here is a REPORTING default only -- bench/rung8.field.toml's [[summon.staging.play]] is
    # the source of truth and make_nimbra_anims.py reads it from there (see this module's docstring).
    # ORDER IS LOAD-BEARING: deploy.clip_key_of mints AUTHORED_CLIP_KEY_BASE + list index, so this order
    # must match `clips = [...]` in the TOML or the manifest names clips that are not on disc.
    ("emerge", build_emerge, N_EMERGE, 1, 0),
    ("drift", build_drift, N_DRIFT, 1, 1),
    ("strike", build_strike, N_STRIKE, 1, 2),
    ("driftlook", lambda: build_drift(N_DRIFTLOOK), N_DRIFTLOOK, 1, 3),
]


def all_clips() -> dict:
    return {name: {"curves": fn(), "frames": n, "speed": sp, "key": key}
            for (name, fn, n, sp, key) in CLIPS}
