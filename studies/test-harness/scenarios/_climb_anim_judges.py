"""[ff9mapkit netsync s157] THE CLIMB-ANIM BENCH's PURE JUDGES (studies/field-coop/GUEST-TRAVERSAL-TWO-PC.md Findings 1 + 2;
memoria-patches/s157-netsync-climb-anim.patch). No game, no harness import, no sys.path edit: the solo bench (the selftest
mirror), the wire half (coop_peer serve-guest) and the offline test ff9mapkit/tests/test_coop_climb_anim_bench.py all read it.

Each judge takes the RAW publishes of one leg (``cb.raw(state)`` dicts, oldest first) and returns ``(ok, why)``. A
``*_marker`` returns ``(True, why)`` when the publishes carry that predicted RED's signature (a calibration leg's verdict).
Every path a judge reads is in :data:`READS` -- the keys s157 actually publishes, pinned to the agent's writers offline:

  ``netsync.ghostframe.*``   Spec B's block (HarnessAgent.AppendGhostFrame; netsync's LAST key): lever_off, follow, why
                             (None | "lever" | "no_frame" | "frame_n" | "loco" | "clip"), has_frame, wire_frame, wire_frame_n,
                             clip, speed, time, length, shown, target, steps, wraps, snaps, restores, selftest.
                             Its lever: ``netsync bench ghostframe on|off`` (selftest role).
  ``netsync.dress.self.*``   Spec A's twin keys (AppendDressTwin, inside `self` after `polish`): twins / twin_misses (PER FIELD
                             LOAD -- read deltas inside one load), twin_last {src, twin, site}, twin ("on" | "off" | "miss" as
                             set), armed. Its lever: ``netsync selfdress twin on|off|miss`` (selftest role).
  ``netsync.dress.ghost.clip``   the clip the ghost drives (== ghostframe.clip).
  ``player.*``               model, anim, geo, anim_geo, clip, anim_frame, frame_n (s138's PlayerDress).

Expected ids come from the CALLER (battlewire: TWIN_BY_KEY, rig_row(rig)["idle"] / ["idle_alias"]) -- never a literal here.
A ghost judge needs the publishes AFTER a settle of at least 1 s from the last change (the ease settles in about 0.7 s).
"""
from __future__ import annotations

import math

GF = "netsync.ghostframe"
SELF = "netsync.dress.self"
SPEED_EPS = 1e-3                       # AnimationState.speed: 0 while following, 1 free-running
FRAME_EPS = 1e-3                       # shown / target are floats in the sender's frame units
TIME_EPS = 0.002                       # seconds of AnimationState.time (B's GF-2 bound)

#: every dotted path these judges read (the offline test pins each to a key the s157 agent publishes)
READS = (
    GF + ".lever_off", GF + ".follow", GF + ".why", GF + ".has_frame", GF + ".wire_frame", GF + ".wire_frame_n", GF + ".clip",
    GF + ".speed", GF + ".time", GF + ".length", GF + ".shown", GF + ".target", GF + ".steps", GF + ".wraps", GF + ".snaps",
    GF + ".restores",
    SELF + ".twins", SELF + ".twin_misses", SELF + ".twin_last.src", SELF + ".twin_last.twin", SELF + ".twin", SELF + ".armed",
    "netsync.dress.ghost.clip",
    "player.model", "player.anim", "player.geo", "player.anim_geo", "player.clip", "player.anim_frame", "player.frame_n",
)


def get(d, dotted, default=None):
    node = d
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def delta(b0, b1, dotted):
    """``b1 - b0`` at ``dotted`` (two publishes), None when either side is not a number."""
    a, b = get(b0, dotted), get(b1, dotted)
    return b - a if _num(a) and _num(b) else None


def _wrap(d: float, n: float) -> float:
    """``d`` folded into [-n/2, n/2): a distance on a loop of ``n``."""
    return (d + n / 2.0) % n - n / 2.0


def _gf(s, key, default=None):
    return get(s, GF + "." + key, default)


def _share(n_hit: int, n: int, share: float) -> bool:
    return n > 0 and n_hit >= share * n


# ================================================================================================ the ghost frame (Finding 1)
def judge_hold(samples, *, wire_tol: int = 0, min_n: int = 8) -> tuple:
    """GF-HOLD -- THE FINDING-1 VERDICT: the climber HANGS (no key; ``player.anim_frame`` constant) and its ghost HOLDS the
    same pose: on every publish follow true and why null, speed 0, shown == target == wire_frame, wire_frame_n the body's
    frame_n, the wire frame within ``wire_tol`` of the body's (the selftest mirror reads it locally: 0; a peer's echo of the
    host may trail a tick: 1), and time constant at shown / frame_n x length."""
    if len(samples) < min_n:
        return False, f"{len(samples)} hold publishes (< {min_n})"
    body = {get(s, "player.anim_frame") for s in samples}
    if len(body) != 1 or not _num(next(iter(body))):
        return False, f"the body moved during the hold (player.anim_frame {sorted(map(str, body))})"
    f = next(iter(body))
    n = get(samples[0], "player.frame_n")
    bad = []
    for k, s in enumerate(samples):
        sh, tg, wf, wn = _gf(s, "shown"), _gf(s, "target"), _gf(s, "wire_frame"), _gf(s, "wire_frame_n")
        sp, t, ln = _gf(s, "speed"), _gf(s, "time"), _gf(s, "length")
        if _gf(s, "follow") is not True or _gf(s, "why") is not None:
            bad.append(f"#{k} follow {_gf(s, 'follow')!r} why {_gf(s, 'why')!r}")
        elif not all(_num(v) for v in (sh, tg, wf, wn, sp, t, ln)) or wn <= 1 or ln <= 0:
            bad.append(f"#{k} no witness (shown {sh}, wire {wf}/{wn}, speed {sp}, time {t}, length {ln})")
        elif abs(sp) >= SPEED_EPS:
            bad.append(f"#{k} speed {sp}")
        elif abs(sh - wf) > FRAME_EPS or abs(tg - wf) > FRAME_EPS:
            bad.append(f"#{k} shown {sh} / target {tg} != wire_frame {wf}")
        elif wn != n or abs(_wrap(wf - f, wn)) > wire_tol:
            bad.append(f"#{k} wire {wf}/{wn} vs body {f}/{n} (tol {wire_tol})")
        elif abs(_wrap(t - sh / wn * ln, ln)) > TIME_EPS:
            bad.append(f"#{k} time {t:.4f} != shown/frame_n x length {sh / wn * ln:.4f}")
    times = [_gf(s, "time") for s in samples if _num(_gf(s, "time"))]
    spread = max(times) - min(times) if times else None
    if spread is not None and spread > TIME_EPS:
        bad.append(f"time spread {spread:.4f} s")
    ok = not bad
    return ok, (f"{len(samples)} publishes on body frame {f}/{n}: " + ("the ghost holds (speed 0, shown == wire, time "
                                                                       "constant)" if ok else "; ".join(bad[:4])))


def frame_red_marker(samples, *, why: str, lever: bool = False) -> tuple:
    """THE PREDICTED RED of GF-HOLD (the s156 ghost): with the body holding, the ghost FREE-RUNS -- follow false, ``why`` the
    expected reason on every publish ("lever" under `netsync bench ghostframe off`, with lever_off true; "no_frame" for a
    37-byte peer), speed 1, and time ADVANCING (a spread over 0.05 s, or a loop wrap) while player.anim_frame stays put."""
    if len(samples) < 2:
        return False, f"{len(samples)} publishes"
    body = {get(s, "player.anim_frame") for s in samples}
    off = [s for s in samples if _gf(s, "follow") is False and _gf(s, "why") == why
           and _num(_gf(s, "speed")) and abs(_gf(s, "speed") - 1.0) < SPEED_EPS
           and (not lever or _gf(s, "lever_off") is True)]
    ts = [_gf(s, "time") for s in samples]
    moved = all(_num(t) for t in ts) and (max(ts) - min(ts) > 0.05 or any(b < a for a, b in zip(ts, ts[1:])))
    ok = len(off) == len(samples) and len(body) == 1 and moved
    return ok, (f"{len(off)}/{len(samples)} publishes free-running with why {why!r}{' and lever_off' if lever else ''}; body "
                f"frames {sorted(map(str, body))}; ghost time moved: {moved}")


def judge_track(samples, *, lag_frames: float = 2.5, share: float = 0.9, min_n: int = 8, min_wraps: int = 0) -> tuple:
    """GF-TRACK: while the body CLIMBS (frames stepping), the ghost is DRIVEN, not free-running -- >= ``share`` of the
    publishes follow at speed 0, the median wrap-aware |shown - wire_frame| <= ``lag_frames`` (the ease trails a step), at
    least 3 distinct body frames, steps +1 or more, snaps not counting every frame, and wraps >= ``min_wraps``."""
    rows = [s for s in samples if all(_num(v) for v in (_gf(s, "shown"), _gf(s, "wire_frame"), _gf(s, "wire_frame_n")))
            and _gf(s, "wire_frame_n") > 1]
    if len(rows) < min_n:
        return False, f"{len(rows)} publishes with a frame witness (< {min_n})"
    held = sum(1 for s in rows if _gf(s, "follow") is True and _num(_gf(s, "speed")) and abs(_gf(s, "speed")) < SPEED_EPS)
    lags = sorted(abs(_wrap(_gf(s, "shown") - _gf(s, "wire_frame"), _gf(s, "wire_frame_n"))) for s in rows)
    med = lags[len(lags) // 2]
    frames = len({get(s, "player.anim_frame") for s in rows})
    d_steps, d_wraps, d_snaps = (delta(rows[0], rows[-1], GF + "." + k) for k in ("steps", "wraps", "snaps"))
    ok = (_share(held, len(rows), share) and med <= lag_frames and frames >= 3 and _num(d_steps) and d_steps >= 1
          and _num(d_wraps) and d_wraps >= min_wraps and _num(d_snaps) and d_snaps < frames)
    return ok, (f"{held}/{len(rows)} following at speed 0, median lag {med:.2f} frames, {frames} body frames, steps +{d_steps}"
                f", wraps +{d_wraps}, snaps +{d_snaps}")


def judge_freerun_guard(samples, *, why: str, min_n: int = 4) -> tuple:
    """A free-run path (frameN 0 / 1 / 255: "frame_n"; a 37-byte peer: "no_frame"; a walking loco: "loco"; a clip the rule
    cannot follow: "clip") -- the ghost is NEVER frozen: follow false, ``why`` that reason, speed 1 on every publish."""
    if len(samples) < min_n:
        return False, f"{len(samples)} publishes (< {min_n})"
    good = [s for s in samples if _gf(s, "follow") is False and _gf(s, "why") == why
            and _num(_gf(s, "speed")) and abs(_gf(s, "speed") - 1.0) < SPEED_EPS]
    whys = sorted({str(_gf(s, "why")) for s in samples})
    speeds = sorted({round(_gf(s, "speed"), 3) for s in samples if _num(_gf(s, "speed"))})
    return len(good) == len(samples), f"{len(good)}/{len(samples)} free-running at speed 1 with why {why!r} (whys {whys}, speeds {speeds})"


def judge_pinned(samples, frame: int, frame_n: int, *, clip: str | None = None, min_n: int = 6) -> tuple:
    """W-1 (`coop_peer serve-guest --frame F/N`, the host's ghost of the fake guest): the ghost holds the WIRE's frame -- follow,
    wire_frame == F and wire_frame_n == N on every publish, speed 0, shown == F, time constant at F / N x length, and (given)
    the clip by name."""
    if len(samples) < min_n:
        return False, f"{len(samples)} publishes (< {min_n})"
    bad = []
    for k, s in enumerate(samples):
        sh, t, ln, sp = _gf(s, "shown"), _gf(s, "time"), _gf(s, "length"), _gf(s, "speed")
        if _gf(s, "follow") is not True or _gf(s, "wire_frame") != frame or _gf(s, "wire_frame_n") != frame_n:
            bad.append(f"#{k} follow {_gf(s, 'follow')!r} wire {_gf(s, 'wire_frame')}/{_gf(s, 'wire_frame_n')}")
        elif not all(_num(v) for v in (sh, t, ln, sp)) or ln <= 0 or abs(sp) >= SPEED_EPS or abs(sh - frame) > FRAME_EPS:
            bad.append(f"#{k} speed {sp} shown {sh}")
        elif abs(_wrap(t - frame / frame_n * ln, ln)) > TIME_EPS:
            bad.append(f"#{k} time {t} != {frame}/{frame_n} x {ln}")
        elif clip is not None and _gf(s, "clip") != clip:
            bad.append(f"#{k} clip {_gf(s, 'clip')!r}")
    return not bad, (f"{len(samples)} publishes hold {frame}/{frame_n}" if not bad else "; ".join(bad[:4]))


def judge_seam(samples, *, direction: int, min_wraps: int, min_steps: int, max_snaps: int = 1,
               judged_share: float = 0.75) -> tuple:
    """W-2 / W-3 (`--frame F/N --frame-step +1 | -1`): the ghost crosses the loop seam the WIRE's way -- wraps and steps grow,
    snaps stay at most ``max_snaps``, and time never runs against ``direction`` (modulo length) between publishes.

    THE READ-GAP RULE (the s157 review's K3): time is only known modulo the clip's length, so a pair of publishes the wire moved a
    quarter loop or more between (a state-read stall: ~200 ms is half a 12-frame loop at 30 Hz) cannot tell forward from back.
    Such a pair is SKIPPED, by the engine's own counters and its own quarter rule (GhostFrameStep): wire changes between the two
    (steps + wraps) with 4 x changes >= frameN, any snap, or a time move of a quarter length or more. Every other pair is JUDGED,
    and at least ``judged_share`` of the pairs must be (a starved run reports as unjudgeable, never passes silently)."""
    if len(samples) < 2:
        return False, f"{len(samples)} publishes"
    d = {k: delta(samples[0], samples[-1], GF + "." + k) for k in ("wraps", "steps", "snaps")}
    back = judged = skipped = 0
    for a, b in zip(samples, samples[1:]):
        ta, tb, ln, n = _gf(a, "time"), _gf(b, "time"), _gf(b, "length"), _gf(b, "wire_frame_n")
        moved = [delta(a, b, GF + "." + k) for k in ("steps", "wraps", "snaps")]
        if not all(_num(v) for v in [ta, tb, ln, n] + moved) or ln <= 0 or n <= 0:
            skipped += 1
            continue
        w = _wrap(tb - ta, ln)
        if moved[2] > 0 or 4 * (moved[0] + moved[1]) >= n or 4 * abs(w) >= ln:
            skipped += 1                       # too far apart to tell the direction (or a snap): not scored
            continue
        judged += 1
        if w * direction < -TIME_EPS:
            back += 1
    pairs = len(samples) - 1
    enough = judged >= max(2, judged_share * pairs)
    ok = (all(_num(v) for v in d.values()) and d["wraps"] >= min_wraps and d["steps"] >= min_steps
          and d["snaps"] <= max_snaps and back == 0 and enough)
    return ok, (f"wraps +{d['wraps']}, steps +{d['steps']}, snaps +{d['snaps']}, {back} step(s) against direction {direction:+d} "
                f"over {judged}/{pairs} judged pair(s) ({skipped} skipped: a read gap of a quarter loop or more"
                + ("" if enough else f" -- UNJUDGEABLE, under {judged_share:.0%} judged") + ")")


# ================================================================================================ the twin rows (Finding 2)
def judge_twin(samples, *, twin_ids, alias_ids, d_twins, d_misses, share: float = 0.8, ghost_share: float | None = 0.8,
               follow_share: float | None = None, min_n: int = 3) -> tuple:
    """A DRESSED leg's mid-leg publishes (207 ladder / 408 hop as Steiner): >= ``share`` play one of the rig's TWIN ids with the
    worn GEO's clip (player.anim_geo == player.geo), NONE plays an alias / idle id, the per-load twin counter moved
    (``d_twins`` >= 1), no twin's clip was missing (``d_misses`` == 0), twin_last names a twin; given ``ghost_share`` the
    mirror ghost drives the same clip, given ``follow_share`` it frame-follows it."""
    if len(samples) < min_n:
        return False, f"{len(samples)} mid-leg publishes (< {min_n})"
    twin_ids, alias_ids = set(twin_ids), set(alias_ids)
    hit = sum(1 for s in samples if get(s, "player.anim") in twin_ids and get(s, "player.anim_geo") == get(s, "player.geo"))
    alias = sum(1 for s in samples if get(s, "player.anim") in alias_ids)
    last = get(samples[-1], SELF + ".twin_last.twin")
    parts = [f"{hit}/{len(samples)} mid publishes on a twin id with the worn GEO", f"{alias} on the alias / idle",
             f"twins +{d_twins}", f"twin_misses +{d_misses}", f"twin_last.twin {last}"]
    ok = (_share(hit, len(samples), share) and alias == 0 and _num(d_twins) and d_twins >= 1 and d_misses == 0
          and last in twin_ids)
    if ghost_share is not None:
        same = sum(1 for s in samples
                   if get(s, "player.clip") is not None and get(s, "netsync.dress.ghost.clip") == get(s, "player.clip"))
        parts.append(f"ghost on the body's clip {same}/{len(samples)}")
        ok = ok and _share(same, len(samples), ghost_share)
    if follow_share is not None:
        fol = sum(1 for s in samples if _gf(s, "follow") is True)
        parts.append(f"ghost following {fol}/{len(samples)}")
        ok = ok and _share(fol, len(samples), follow_share)
    return ok, "; ".join(parts)


def twin_red_marker(samples, *, alias_ids, mode: str, d_twins=None, d_misses=None, share: float = 0.8) -> tuple:
    """THE PREDICTED RED of a dressed leg: the mid-leg publishes play the rig's idle ALIAS (s156's pencil). ``mode``:
    "s156" -- the deployed s156 DLL (no `dress.self.twins` key: the alias alone); "off" -- `selfdress twin off` (twin "off" on
    every publish, twins +0, twin_misses +0); "miss" -- `selfdress twin miss` (twin "miss", twins +0, twin_misses +1 or more:
    the clip-present guard fell back)."""
    alias = sum(1 for s in samples if get(s, "player.anim") in set(alias_ids))
    ok = _share(alias, len(samples), share)
    why = [f"{alias}/{len(samples)} mid publishes on the alias"]
    if mode == "s156":
        keyless = all(get(s, SELF + ".twins") is None for s in samples)
        ok = ok and keyless
        why.append(f"no twin key: {keyless}")
    elif mode in ("off", "miss"):
        lever = all(get(s, SELF + ".twin") == mode for s in samples)
        counts = d_twins == 0 and (d_misses == 0 if mode == "off" else _num(d_misses) and d_misses >= 1)
        ok = ok and lever and counts
        why.append(f"twin {mode!r} throughout: {lever}; twins +{d_twins}, twin_misses +{d_misses}")
    else:
        return False, f"unknown mode {mode!r}"
    return ok, "; ".join(why)


def judge_undressed(samples, *, model: int, d_twins, d_misses, share: float = 0.8) -> tuple:
    """114's NEGATIVE CONTROL (the field's own Vivi, SetModel 8, never dressed): player.model ``model`` and dress.self.armed
    false on every publish, the body's own GEO clip on most, and neither twin counter moved -- under every lever. A delta of
    None (the s156 DLL publishes no twin key: the s156 calibration) counts as unmoved; the bench tells the engines apart at K0."""
    bad = [s for s in samples if get(s, "player.model") != model or get(s, SELF + ".armed") is True]
    own = sum(1 for s in samples if get(s, "player.anim_geo") is not None and get(s, "player.anim_geo") == get(s, "player.geo"))
    ok = bool(samples) and not bad and _share(own, len(samples), share) and d_twins in (0, None) and d_misses in (0, None)
    return ok, (f"{len(samples) - len(bad)}/{len(samples)} undressed on model {model}; {own} on the body's own GEO clip; "
                f"twins +{d_twins}, twin_misses +{d_misses}")


# ================================================================================================ the wire half's sender witness
def host_trailer_edges(lines) -> list:
    """The ``host type-0: ...`` EDGE lines in a coop_peer serve-guest --log (coop_peer.HOST_TRAILER_LINE /
    HOST_NO_TRAILER_LINE), in order -- P0: an s157 host's first is "39 B -- the s157 frame bytes"; an s156 host logs none."""
    return [ln[ln.index("host type-0: "):] for ln in lines if "host type-0: " in ln]


def judge_sender(lines) -> tuple:
    """P0: the HOST engine sends the s157 trailer -- the peer's first type-0 edge is the 39-byte one and none says it stopped."""
    edges = host_trailer_edges(lines)
    ok = bool(edges) and edges[0].startswith("host type-0: 39 B -- the s157 frame bytes") and \
        not any("no frame bytes" in e for e in edges)
    return ok, f"{len(edges)} trailer edge(s): {edges[:2]}"
