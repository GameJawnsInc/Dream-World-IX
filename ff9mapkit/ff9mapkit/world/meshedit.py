"""ff9mapkit.world.meshedit -- the coast-edit primitives, promoted out of study scripts.

These operators built the Path D V-shore corner, which is owner-accepted in game on
both axes (flow and look) after twelve playtests. Each one carries a law that was
expensive to learn, so each law is enforced HERE, at the call site, and covered by a
test that fails when the law is removed -- a law in a docstring is a wish.

The laws, and what falsified the alternative in each case:

* **THE FLOW CONSTRAINT** (:func:`flow_ok`) -- every seated boundary heading must stay
  >= 135 deg, or a walker hugging the shore is CAUGHT at the joint. The relaxation to
  125 was tried and falsified by the hug gate in one offline run.
* **THE JOINT-KINK LAW** (:func:`joint_kinks`) -- a C0 weld with a tangent jump reads as
  a floating slab at land-side oblique vantages. Fix by DONOR SELECTION, never by
  bending the donor: the bend-carry is a registered dead end.
* **THE OVERHANG-CONTEXT LAW** (:func:`sweep_wall`) -- a verbatim stock element can be
  wrong for the CONTEXT it is torn from. Stock coast lips all overhang; over a cut sea
  they hang above dry void and force a cascade of auxiliary surfaces (walk membrane,
  foot apron, inner curtain), each of which then carries the next defect. Take the
  profile from the NEIGHBOURS instead: crest flush with the lawn edge, foot ~0.9u
  SEAWARD at the waterline. That profile is walk-visible (no membrane) and seals the
  under-lip sightline by construction (no apron, no curtain) -- 332 authored triangles
  collapsed to 14.
* **THE TEXEL-DENSITY GATE** (:func:`sweep_wall`) -- a mishandled band wrap compresses a
  whole atlas band into one face and renders as vertical picket-fence streaking.
  Density, not seam count, is the property that must hold: stock butt-seams its wall
  texture constantly and the band does not tile.
* **DENSIFY FIRST** (:func:`sweep_wall` returns its rungs) -- two meshes that share a
  boundary must be built on ONE pre-densified chain. If either subdivides later, every
  new vertex is a T-junction against the other.
* **A REPAIR THAT IS NOT EXACT IS A HOLE** (:func:`repair_tjunctions`) -- splitting an
  edge at a point merely NEAR it leaves a sliver gap the width of the offset, which is
  strictly worse than the T-junction it closes.
* **THE FAN LAW** (:func:`earclip` ``quality=``) -- a triangulation that is exact can
  still be wrong. First-ear clipping fans a run of collinear ring vertices into slivers,
  and the defect surfaces only DOWNSTREAM, where a re-partition mints a vertex per
  diagonal and two land inside the weld tolerance. Fix the ear CHOICE; adding ring
  vertices (densify) and removing them (collapse) were both falsified.
* **SCORE AGAINST THE NEIGHBOUR** (:func:`cover_gap`) -- validate a cloned patch against
  the retained surface it lands in, not against its own donor. A donor can be perfectly
  lawful and still be a visible tone patch where you put it.

Deliberately NOT here yet: the sea cut (``cut_sea_under``), which is entangled with
per-part world mesh semantics rather than being pure geometry -- see
``studies/path-d-new-world/vcorner_sea_cut.py``.

Conventions: plan points are ``(x, z)`` 2-tuples; space points are ``(x, y, z)``.
"Seaward" of a segment ``a -> b`` is ``(dz, -dx)`` normalised -- i.e. land lies LEFT of
travel, the convention the bench boundary walks use.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Iterable, Sequence

__all__ = [
    "FLOW_MIN_HEADING", "FLOW_MAX_HEADING", "KINK_MAX", "URATE", "ROCK_BAND",
    "V_TOP", "V_BOT",
    "seaward", "densify", "miter_offset", "seat_transform", "seated_headings",
    "flow_ok", "joint_kinks", "texel_density", "WallSweep", "sweep_wall",
    "earclip", "cover_gap", "find_tjunctions", "repair_tjunctions",
    "vertex_components", "boundary_cycles", "flat_patch",
]

# Measured on the bench and re-derived over five independent spans.
FLOW_MIN_HEADING = 135.0
FLOW_MAX_HEADING = 272.0
KINK_MAX = 12.0
URATE = 0.012643                 # atlas u per world unit along a coast
ROCK_BAND = (0.699, 0.947)       # the grass-family lip band
V_TOP, V_BOT = 0.8926, 0.9229    # crest / foot v pins


# --------------------------------------------------------------------- helpers
def seaward(a: Sequence[float], b: Sequence[float]) -> tuple[float, float]:
    """Unit seaward normal of plan segment ``a -> b`` (land LEFT of travel)."""
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz)
    if L < 1e-12:
        raise ValueError("degenerate segment has no seaward direction")
    return (dz / L, -dx / L)


def _heading(a, b) -> float:
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360.0


def _circ_delta(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def densify(chain: Sequence[Sequence[float]], seg_max: float) -> list[tuple[float, float]]:
    """Insert collinear points so no segment exceeds ``seg_max``.

    DENSIFY FIRST: do this once and build every mesh that shares the chain on the
    result. Inserted points are collinear, so shape and texture are untouched.
    """
    if seg_max <= 0:
        raise ValueError("seg_max must be positive")
    out = [tuple(chain[0][:2])]
    for i in range(len(chain) - 1):
        a, b = chain[i], chain[i + 1]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        k = max(1, math.ceil(L / seg_max)) if L > 0 else 1
        for j in range(1, k + 1):
            t = j / k
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def miter_offset(chain: Sequence[Sequence[float]], dist, *,
                 max_ratio: float = 2.5) -> list[tuple[float, float]]:
    """Offset a plan chain seaward, mitred at interior vertices.

    ``dist`` is a constant or a per-vertex sequence. The mitre is clamped at
    ``max_ratio * dist`` so a sharp interior corner cannot fire a spike.
    """
    n = len(chain)
    if n < 2:
        raise ValueError("need at least two points")
    ds = [float(dist)] * n if isinstance(dist, (int, float)) else list(dist)
    if len(ds) != n:
        raise ValueError("per-vertex dist must match the chain length")
    seas = [seaward(chain[i], chain[i + 1]) for i in range(n - 1)]
    out = []
    for i in range(n):
        if i == 0:
            d, s = ds[0], seas[0]
        elif i == n - 1:
            d, s = ds[-1], seas[-1]
        else:
            mx = seas[i - 1][0] + seas[i][0]
            mz = seas[i - 1][1] + seas[i][1]
            mL = math.hypot(mx, mz)
            if mL < 1e-9:
                raise ValueError(f"180-degree reversal at vertex {i}: no mitre exists")
            s = (mx / mL, mz / mL)
            cosh = s[0] * seas[i - 1][0] + s[1] * seas[i - 1][1]
            d = min(ds[i] / max(cosh, 1e-6), max_ratio * ds[i])
        out.append((chain[i][0] + d * s[0], chain[i][1] + d * s[1]))
    return out


# ------------------------------------------------------- donor seating + laws
def seat_transform(donor_a, donor_b, target_a, target_b) -> Callable:
    """Rigid chord seat: map the donor chord onto the target chord.

    Rotation + uniform plan scale only -- no shear, no bending. (Bending a donor to
    fit is the registered bend-carry dead end; a donor that does not fit is the wrong
    donor.)
    """
    d0 = (donor_b[0] - donor_a[0], donor_b[1] - donor_a[1])
    d1 = (target_b[0] - target_a[0], target_b[1] - target_a[1])
    L0, L1 = math.hypot(*d0), math.hypot(*d1)
    if L0 < 1e-9:
        raise ValueError("degenerate donor chord")
    s = L1 / L0
    th = math.atan2(d1[0], d1[1]) - math.atan2(d0[0], d0[1])
    ct, st = math.cos(th), math.sin(th)

    def seat(p):
        rx, rz = p[0] - donor_a[0], p[1] - donor_a[1]
        return (target_a[0] + s * (rx * ct + rz * st),
                target_a[1] + s * (-rx * st + rz * ct))

    seat.scale = s
    seat.rotation_deg = math.degrees(th)
    return seat


def seated_headings(seg: Sequence[Sequence[float]], target_a, target_b) -> list[float]:
    """Per-segment compass headings the donor window would have once seated."""
    seat = seat_transform(seg[0], seg[-1], target_a, target_b)
    pts = [seat(p) for p in seg]
    return [_heading(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]


def flow_ok(headings: Iterable[float], *, lo: float = FLOW_MIN_HEADING,
            hi: float = FLOW_MAX_HEADING) -> bool:
    """THE FLOW CONSTRAINT -- every seated heading inside the quantised-fan window."""
    return all(lo <= h <= hi for h in headings)


def joint_kinks(headings: Sequence[float], tan_in: float,
                tan_out: float) -> tuple[float, float]:
    """THE JOINT-KINK LAW -- tangent jump at each weld, in degrees."""
    if not headings:
        raise ValueError("no headings")
    return (_circ_delta(headings[0], tan_in), _circ_delta(headings[-1], tan_out))


# ------------------------------------------------------------------ the sweep
def texel_density(p3: Sequence[Sequence[float]], uv3: Sequence[Sequence[float]]) -> float:
    """Atlas u spanned per world unit of plan width across one face."""
    du = max(u for u, _ in uv3) - min(u for u, _ in uv3)
    wid = max(math.hypot(p3[a][0] - p3[b][0], p3[a][2] - p3[b][2])
              for a, b in ((0, 1), (1, 2), (2, 0)))
    return du / wid if wid > 1e-9 else float("inf")


def _up_ny(a, b, c) -> float:
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    L = math.sqrt(nx * nx + ny * ny + nz * nz)
    return ny / L if L > 1e-12 else 0.0


@dataclass
class WallSweep:
    """``tris`` are ``(p3, uv3)``; ``rungs`` is the chain BOTH meshes must share."""
    tris: list = field(default_factory=list)
    rungs: list = field(default_factory=list)
    wrap_splits: int = 0
    cut_rung: int = -1


def sweep_wall(crest: Sequence[Sequence[float]], *, top_y: float, u_start: float,
               foot_y: float = 0.0, foot_offset=0.94, u_end: float | None = None,
               urate: float = URATE, band: tuple = ROCK_BAND,
               v_top: float = V_TOP, v_bot: float = V_BOT, seg_max: float = 2.0,
               min_ny: float = 0.1, density_factor: float = 2.0,
               foot_anchor_a=None, foot_anchor_b=None) -> WallSweep:
    """Sweep a coast wall along ``crest`` in the neighbours' own vocabulary.

    Crest flush with the lawn edge at ``top_y``; foot ``foot_offset`` SEAWARD at
    ``foot_y``, mitred. ``u`` advances with arc at ``urate``, wrapping inside ``band``;
    a foot vertex inherits its crest vertex's ``u``; ``v`` is linear in height. With
    ``u_end`` the run is parameterised forward from the entry AND backward from the
    exit, so both joints stay texture-continuous and the unavoidable mismatch is spent
    as ONE uv cut at an interior rung.

    Raises ``ValueError`` if the result would not be walk-visible (``min_ny``) or if any
    face exceeds ``density_factor * urate`` -- the two ways this sweep goes wrong.
    """
    crest = densify(crest, seg_max)
    n = len(crest)
    if n < 2:
        raise ValueError("crest needs at least two points")
    seas = [seaward(crest[i], crest[i + 1]) for i in range(n - 1)]
    arc = [0.0]
    for i in range(n - 1):
        arc.append(arc[-1] + math.hypot(crest[i + 1][0] - crest[i][0],
                                        crest[i + 1][1] - crest[i][1]))
    total = arc[-1]

    if isinstance(foot_offset, (int, float)):
        ds = [float(foot_offset)] * n
    else:
        d0, d1 = foot_offset
        ds = [d0 + (d1 - d0) * (arc[i] / total if total else 0.0) for i in range(n)]
    foot_plan = miter_offset(crest, ds)
    foot = [(p[0], foot_y, p[1]) for p in foot_plan]
    if foot_anchor_a is not None:
        foot[0] = tuple(foot_anchor_a)
    if foot_anchor_b is not None:
        foot[-1] = tuple(foot_anchor_b)

    lo, hi = band
    span = hi - lo
    mid = (min(range(1, n - 1), key=lambda i: abs(arc[i] - total / 2))
           if (u_end is not None and n > 3) else n - 1)

    def u_at(i):
        if u_end is None or i <= mid:
            return u_start + arc[i] * urate
        return u_end - (total - arc[i]) * urate

    def wrap(u):
        return lo + (u - lo) % span

    cont = []
    for i in range(n - 1):
        if u_end is not None and i == mid:
            ul = u_at(i)
            cont.append((ul, ul + (arc[i + 1] - arc[i]) * urate))
        else:
            cont.append((u_at(i), u_at(i + 1)))

    quads, nwrap = [], 0
    for i, (u0c, u1c) in enumerate(cont):
        k0 = math.floor((u0c - lo) / span)
        k1 = math.floor((u1c - lo) / span)
        if k0 == k1:
            quads.append((i, 0.0, 1.0, wrap(u0c), wrap(u1c)))
            continue
        ub = lo + span * (k0 + 1 if k1 > k0 else k0)
        t = (ub - u0c) / (u1c - u0c) if abs(u1c - u0c) > 1e-12 else 0.5
        t = min(max(t, 0.02), 0.98)
        quads.append((i, 0.0, t, wrap(u0c), hi if k1 > k0 else lo))
        quads.append((i, t, 1.0, lo if k1 > k0 else hi, wrap(u1c)))
        nwrap += 1

    def lerp(a, b, t):
        return tuple(a[j] + (b[j] - a[j]) * t for j in range(len(a)))

    out, rungs = [], []
    for (i, t0, t1, ua, ub) in quads:
        c0, c1 = lerp(crest[i], crest[i + 1], t0), lerp(crest[i], crest[i + 1], t1)
        f0, f1 = lerp(foot[i], foot[i + 1], t0), lerp(foot[i], foot[i + 1], t1)
        if not rungs or math.dist(rungs[-1], c0) > 1e-9:
            rungs.append(c0)
        rungs.append(c1)
        C0, C1 = (c0[0], top_y, c0[1]), (c1[0], top_y, c1[1])
        for tri, uv in (((C0, C1, f0), ((ua, v_top), (ub, v_top), (ua, v_bot))),
                        ((C1, f1, f0), ((ub, v_top), (ub, v_bot), (ua, v_bot)))):
            p3, uv3 = list(tri), list(uv)
            ax, az = p3[1][0] - p3[0][0], p3[1][2] - p3[0][2]
            bx, bz = p3[2][0] - p3[0][0], p3[2][2] - p3[0][2]
            fnx = (p3[1][1] - p3[0][1]) * bz - az * (p3[2][1] - p3[0][1])
            fnz = ax * (p3[2][1] - p3[0][1]) - (p3[1][1] - p3[0][1]) * bx
            if fnx * seas[i][0] + fnz * seas[i][1] < 0:      # face the sea
                p3 = [p3[0], p3[2], p3[1]]
                uv3 = [uv3[0], uv3[2], uv3[1]]
            out.append((p3, uv3))

    nys = [_up_ny(*p3) for p3, _uv in out]
    if nys and min(nys) <= min_ny:
        raise ValueError(
            f"wall is not walk-visible (min ny {min(nys):.3f} <= {min_ny}); an "
            f"overhanging profile would need a separate walk membrane -- take the "
            f"profile from the neighbours instead (THE OVERHANG-CONTEXT LAW)")
    worst = max((texel_density(p3, uv3) for p3, uv3 in out), default=0.0)
    if worst >= density_factor * urate:
        raise ValueError(
            f"texel density {worst:.4f} u/unit vs {urate:.4f}: a band wrap was "
            f"mishandled (renders as vertical streaking)")
    return WallSweep(tris=out, rungs=[(p[0], p[1]) for p in rungs],
                     wrap_splits=nwrap, cut_rung=mid if u_end is not None else -1)


# ------------------------------------------------------------- the gap cover
def _cross(o, a, b) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (b[0] - o[0]) * (a[1] - o[1])


def _ear_quality(a, b, c) -> float:
    """The SMALLEST interior angle (degrees) of ear ``a-b-c`` -- the selection score.

    A sliver ear scores near 0, a well-shaped one near 60. See :func:`earclip`'s
    ``quality`` for why the shape of an ear -- not just its validity -- is load-bearing.
    """
    worst = 180.0
    for (p, q, r) in ((a, b, c), (b, c, a), (c, a, b)):
        ux, uy = p[0] - q[0], p[1] - q[1]
        vx, vy = r[0] - q[0], r[1] - q[1]
        nu = math.hypot(ux, uy) or 1e-30
        nv = math.hypot(vx, vy) or 1e-30
        cs = max(-1.0, min(1.0, (ux * vx + uy * vy) / (nu * nv)))
        worst = min(worst, math.degrees(math.acos(cs)))
    return worst


def earclip(ring: Sequence[Sequence[float]], *, quality: bool = False) -> list[tuple]:
    """Ear-clip a simple polygon. Handles the fold-back rings a cut/fill strip makes.

    THE FAN LAW (``quality=True``) -- take the BEST-SHAPED valid ear, not the first one.

    Taking the first valid ear is correct but produces a fan of slivers wherever the ring
    carries a run of collinear vertices: a collinear vertex can never BE an ear (its cross
    product is zero), so the run survives until its neighbourhood has been eaten away and
    is then triangulated against whatever distant vertex happens to be adjacent by then.
    That is invisible in the patch itself -- every vertex is still a ring vertex and the
    coverage is exact -- and it only becomes a defect DOWNSTREAM: the transplant's block-
    border re-partition mints a vertex where each fan diagonal crosses the border, and
    near-parallel diagonals cross within the 0.05u weld tolerance of one another. Measured
    on the excise fills: the sinuous island (3,11)+2x4 put two crossings 0.0239u apart on
    z=-64 and Daguerreo (5,15)+3x2 four more on x=64/x=128, all four failing the weld
    audit. Scoring ears by their smallest angle keeps every diagonal local: the same rings,
    the same triangle counts, the same coverage, closest interior pair 0.0239 -> 0.1444 and
    0.0294 -> 0.3585, weld pairs 1 and 4 -> 0.

    It stays OFF by default because it changes which diagonals a triangulation picks, and
    the Path-D V-shore bench's cover is owner-confirmed in game -- moving its diagonals is
    a playtest, not a refactor. :func:`flat_patch` (the excise fill) opts in.
    """
    P = [tuple(p[:2]) for p in ring]
    if len(P) < 3:
        raise ValueError("ring needs at least three points")
    if sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1]
           for i in range(len(P))) < 0:
        P.reverse()
    tris, guard = [], 0
    while len(P) > 3 and guard < 4000:
        guard += 1
        n = len(P)
        best = None
        for i in range(n):
            a, b, c = P[(i - 1) % n], P[i], P[(i + 1) % n]
            if _cross(a, b, c) <= 1e-12:
                continue
            if any(_cross(a, b, q) >= -1e-12 and _cross(b, c, q) >= -1e-12
                   and _cross(c, a, q) >= -1e-12
                   for q in P if q not in (a, b, c)):
                continue
            if not quality:
                best = (0.0, i, (a, b, c))
                break
            score = _ear_quality(a, b, c)
            if best is None or score > best[0]:
                best = (score, i, (a, b, c))
        if best is None:
            break
        tris.append(best[2])
        del P[best[1]]
    if len(P) != 3:
        raise ValueError(f"ear-clip stuck with {len(P)} vertices")
    tris.append(tuple(P))
    return tris


def cover_gap(ring: Sequence[Sequence[float]], *, uv_at: Callable, shifts: Sequence,
              is_clean: Callable, tone: Callable | None = None,
              ref_tone: Callable | None = None, tone_max: float = 12.0,
              min_edge: float = 0.30, on_ring: Callable | None = None,
              max_depth: int = 6, max_work: int = 6000) -> list[tuple]:
    """Fill a ring with triangles, each assigned a clean, tonally-matched donor shift.

    ``uv_at(p, shift) -> (u, v)``; ``is_clean(uv3) -> bool``; ``tone(uv3) -> rgb|None``;
    ``ref_tone(centroid) -> rgb|None`` is the NEIGHBOURHOOD reference -- the retained
    surface the patch lands in, NOT the donor's own paint. ``on_ring(a, b) -> bool``
    marks edges shared with geometry we are not rewriting; those are never split.

    A triangle with no clean shift is not a verdict, it is a triangle that is still too
    big: it is split and retried (the ground field's unpainted texels are scattered, so
    a smaller footprint has somewhere clean to land).
    """
    work = [(t, 0) for t in reversed(earclip(ring))]
    out, guard = [], 0
    while work and guard < max_work:
        guard += 1
        tri, depth = work.pop()
        cen = (sum(p[0] for p in tri) / 3.0, sum(p[1] for p in tri) / 3.0)
        want = ref_tone(cen) if ref_tone is not None else None
        best = None
        for sh in shifts:
            uv3 = [uv_at(p, sh) for p in tri]
            if not is_clean(uv3):
                continue
            d = 0.0
            if want is not None and tone is not None:
                got = tone(uv3)
                if got is not None:
                    d = math.dist(got, want)
            if best is None or d < best[0]:
                best = (d, sh)
                if d == 0.0:
                    break
        if best is not None and (want is None or best[0] <= tone_max):
            out.append((tri, best[1]))
            continue
        cands = [(math.dist(a, b), (a, b), c)
                 for (a, b, c) in ((tri[0], tri[1], tri[2]),
                                   (tri[1], tri[2], tri[0]),
                                   (tri[2], tri[0], tri[1]))
                 if (on_ring is None or not on_ring(a, b)) and math.dist(a, b) > min_edge]
        if cands and depth < max_depth:
            _L, (a, b), c = max(cands)
            m = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
            work.append(((a, m, c), depth + 1))
            work.append(((m, b, c), depth + 1))
            continue
        out.append((tri, best[1] if best else (shifts[0] if len(shifts) else None)))
    if work:
        raise ValueError("cover_gap did not terminate; loosen min_edge or shifts")
    return out


# ----------------------------------------------------------------- T-junctions
def find_tjunctions(tris: Sequence[Sequence[Sequence[float]]],
                    ext_verts: Iterable = (), eps: float = 2e-3) -> list[tuple]:
    """Vertices lying in the INTERIOR of another face's edge.

    Watertight in exact arithmetic, a crack under float32 -- invisible to a renderer at
    most cameras and to a weld audit, which only looks for near-MISS duplicates.
    """
    verts = {tuple(p[:2]) for t in tris for p in t} | {tuple(p[:2]) for p in ext_verts}
    hits = []
    for t in tris:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            pa, pb = tuple(t[a][:2]), tuple(t[b][:2])
            dx, dz = pb[0] - pa[0], pb[1] - pa[1]
            L2 = dx * dx + dz * dz
            if L2 < 1e-12:
                continue
            for w in verts:
                if w == pa or w == pb:
                    continue
                s = ((w[0] - pa[0]) * dx + (w[1] - pa[1]) * dz) / L2
                if not (1e-5 < s < 1 - 1e-5):
                    continue
                off = abs((w[0] - pa[0]) * dz - (w[1] - pa[1]) * dx) / math.sqrt(L2)
                if off < eps:
                    hits.append((w, pa, pb, off))
    return hits


def repair_tjunctions(pairs: Sequence[tuple], ext_verts: Iterable = (),
                      exact_eps: float = 1e-4, rounds: int = 24) -> tuple[list, int]:
    """Split faces at vertices lying EXACTLY on their edges. ``pairs`` = ``(tri, payload)``.

    ``exact_eps`` is deliberately tight and must stay that way: **a repair that is not
    exact is a hole.** Splitting an edge at a point merely close to it leaves a sliver
    gap the width of the offset -- measured at 2.5e-3, that opened visible background
    where there had been none. Feed neighbours' vertices via ``ext_verts``: a retained
    face's vertex on our edge is just as much a crack, and only we can fix it.
    """
    if exact_eps > 5e-4:
        raise ValueError(
            f"exact_eps {exact_eps} is too loose: splitting at a point that is merely "
            f"NEAR an edge opens a gap of that width -- worse than the T-junction")
    ext = {tuple(p[:2]) for p in ext_verts}
    pairs = [(tuple(tuple(p) for p in t), pl) for t, pl in pairs]
    for r in range(rounds):
        vset = {tuple(p[:2]) for t, _ in pairs for p in t} | ext
        grown, changed = [], 0
        for t, pl in pairs:
            hit = None
            for a, b in ((0, 1), (1, 2), (2, 0)):
                pa, pb = tuple(t[a][:2]), tuple(t[b][:2])
                dx, dz = pb[0] - pa[0], pb[1] - pa[1]
                L2 = dx * dx + dz * dz
                if L2 < 1e-12:
                    continue
                for w in vset:
                    if w == pa or w == pb:
                        continue
                    s = ((w[0] - pa[0]) * dx + (w[1] - pa[1]) * dz) / L2
                    if not (1e-5 < s < 1 - 1e-5):
                        continue
                    if abs((w[0] - pa[0]) * dz - (w[1] - pa[1]) * dx) / math.sqrt(L2) \
                            < exact_eps:
                        hit = (a, b, w)
                        break
                if hit:
                    break
            if hit is None:
                grown.append((t, pl))
                continue
            a, b, w = hit
            c = t[3 - a - b]
            grown.append(((t[a], w, c), pl))
            grown.append(((w, t[b], c), pl))
            changed += 1
        pairs = grown
        if not changed:
            return pairs, r
    return pairs, -1


# --------------------------------------------------------------------------- excise
# The donor-rect EXCISE primitives (registration:
# studies/coast-shape-language/EXCISE-PREDICTION.md). A multi-block carry is refused by
# the land-fit gate whenever a NEIGHBOURING landmass crosses the donor rect frame -- it
# would ship a mass cropped to a ruler-straight 64u slice hanging in mid-air. Excise
# drops that mass and re-zips the deep-ocean sheet over its footprint.


def vertex_components(tris, *, key_decimals: int = 4) -> list[list]:
    """Group triangles into components joined by SHARED VERTEX KEYS.

    This is what makes a drop set well-defined: two landmasses that share no vertex are
    separable exactly, with no geometric tolerance in the decision. Measured on donor
    rect (6,6)+2x2 -- three components, no shared vertices, so the frame-crossers can be
    dropped without touching the island being kept.

    ``tris`` is a triangle soup of ``(pos, normal, uv, tangent)`` vertex tuples (the
    shape :func:`transplant.world_tris` returns). Returned largest-first.
    """
    kd = int(key_decimals)

    def k(v):
        return (round(v[0], kd), round(v[1], kd), round(v[2], kd))

    parent: dict = {}

    def find(a):
        parent.setdefault(a, a)
        root = a
        while parent[root] != root:
            root = parent[root]
        while parent[a] != root:                       # path compression
            parent[a], a = root, parent[a]
        return root

    for t in tris:
        ks = [k(v[0]) for v in t]
        r0 = find(ks[0])
        for kk in ks[1:]:
            r = find(kk)
            if r != r0:
                parent[r] = r0

    groups: dict = {}
    for t in tris:
        groups.setdefault(find(k(t[0][0])), []).append(t)
    return sorted(groups.values(), key=len, reverse=True)


def boundary_cycles(tris, *, key_decimals: int = 4) -> list[list]:
    """Trace the true boundary CYCLES of a triangle soup (junction-safe).

    Boundary edges are those used by exactly one triangle. The obvious implementation --
    connected components of the boundary graph -- is WRONG at a junction vertex: two
    disjoint cycles that touch at one vertex merge into a single reported "loop". That
    error is why a first pass on donor rect (6,6)+2x2 reported the sea sheet as having no
    island hole at all, when in fact 132 of its 218 boundary verts trace island coast.

    So this consumes EDGES, not vertices: each walk leaves a vertex by an unused edge, so
    a junction is traversed once per incident cycle. Returns rings of ``(x, y, z)``
    tuples, largest first; each ring is open (the closing edge is implied).
    """
    kd = int(key_decimals)

    def k(v):
        return (round(v[0], kd), round(v[1], kd), round(v[2], kd))

    # Round ONLY to key; emit the EXACT float. Returning the rounded key as geometry
    # re-creates the hairline-crack class this codebase already has a law about: real
    # donor verts are off-lattice floats like 394.003906, and a ring carrying 394.0039
    # lands 4e-6 away -- identical to the eye, a near-miss pair to the weld audit, and 16
    # of them were measured before this line existed.
    exact: dict = {}
    count: dict = {}
    for t in tris:
        ks = [k(v[0]) for v in t]
        for kk, v in zip(ks, t):
            exact.setdefault(kk, tuple(float(c) for c in v[0]))
        for a, b in ((0, 1), (1, 2), (2, 0)):
            e = (ks[a], ks[b]) if ks[a] <= ks[b] else (ks[b], ks[a])
            count[e] = count.get(e, 0) + 1

    adj: dict = {}
    unused = set()
    for e, c in count.items():
        if c != 1:
            continue
        unused.add(e)
        adj.setdefault(e[0], []).append(e[1])
        adj.setdefault(e[1], []).append(e[0])

    rings = []
    # Termination here rests ENTIRELY on consuming an edge per step. A mutation that
    # removed the consumption test did not fail the suite, it HUNG it -- so the bound is
    # explicit rather than emergent, and a non-manifold input raises instead of spinning.
    budget = 4 * len(unused) + 16
    while unused:
        a, b = next(iter(unused))
        unused.discard((a, b))
        ring, cur, prev = [a, b], b, a
        while True:
            budget -= 1
            if budget < 0:
                raise ValueError("boundary_cycles: walk exceeded its edge budget -- "
                                 "the input is not edge-manifold")
            nxt = None
            for w in adj.get(cur, ()):
                e = (cur, w) if cur <= w else (w, cur)
                if e in unused and w != prev:
                    nxt = w
                    break
            if nxt is None:                            # closed, or a dead end
                break
            unused.discard((cur, nxt) if cur <= nxt else (nxt, cur))
            if nxt == ring[0]:
                break
            ring.append(nxt)
            prev, cur = cur, nxt
        if len(ring) >= 3:
            rings.append([exact[p] for p in ring])
    rings.sort(key=len, reverse=True)
    return rings


def flat_patch(ring, *, y: float, uv_quads, idall: int, normal=(0.0, 1.0, 0.0),
               pick=None, winding: float = -1.0) -> list[list[tuple]]:
    """Fill a ring with flat triangles at constant ``y`` -- the deep-ocean re-zip.

    Sea4 is a single plane (measured: every vertex at y=0.000) whose UV vocabulary is a
    2x2 quadrant scheme, and the quadrant is distributed UNIFORMLY across world-cell
    parities -- the anti-tiling choice is genuinely free, so a patch cannot pick a wrong
    tile. That is why this takes no tone or cleanliness validator, unlike
    :func:`cover_gap`: there is no ground field to match and no unpainted texel to avoid.

    ``ring`` is the hole boundary in world coords, and its vertices are reused EXACTLY --
    the patch introduces no new boundary vertex, so the weld is exact by construction
    rather than by tolerance. ``uv_quads`` is a sequence of (u0, v0, u1, v1) quadrant
    rects; ``pick(tri_index) -> quad_index`` chooses among them (default: round-robin,
    which is deterministic and reproducible -- Math.random is unavailable in this stack
    and a fixed rotation matches stock's uniform spread as well as noise would).

    ``winding`` is the SIGN OF THE PLAN CROSS PRODUCT the emitted triangles must carry,
    and it defaults to stock sea's -1. This is not a detail: a patch wound the other way
    is back-facing to the engine's downward ground raycast, so it renders yet registers
    as void. Measured -- all 1025 stock sea4 tris in one donor rect wind negative, and an
    otherwise-exact fill wound positive scored 73 introduced census misses. Pass the
    neighbouring sheet's own ``normal`` too: stock sea normals are a shared byte constant
    like (-0.121, 0.9785, 0.1665), NOT the (0,1,0) that looks obviously right.
    """
    quads = [tuple(float(c) for c in q) for q in uv_quads]
    if not quads:
        raise ValueError("flat_patch needs at least one uv quadrant")
    plan = [(float(p[0]), float(p[2])) for p in ring]      # ear-clip in the x/z plane
    # THE FAN LAW: this fill is re-partitioned at the target's block borders downstream,
    # so a sliver fan across the ring turns into near-miss vertex pairs ON a border that
    # the weld audit (rightly) refuses. Quality ear selection keeps the diagonals local.
    tris2 = earclip(plan, quality=True)
    at = {(round(p[0], 6), round(p[1], 6)): i for i, p in enumerate(plan)}

    out = []
    for ti, tri in enumerate(tris2):
        # THE PER-TILE QUADRANT LAW (see _tile_quad_index): both triangles of a 4u
        # tile must take the same quadrant. Per-triangle round-robin checkerboards
        # the sheet -- invisible on a 17-tri fill, catastrophic at scale.
        qi = (pick(ti) if pick else _tile_quad_index(
            [((p[0], y, p[1]),) for p in tri], len(quads))) % len(quads)
        u0, v0, u1, v1 = quads[qi]
        cross = ((tri[1][0] - tri[0][0]) * (tri[2][1] - tri[0][1])
                 - (tri[2][0] - tri[0][0]) * (tri[1][1] - tri[0][1]))
        if winding and cross * winding < 0:
            tri = (tri[0], tri[2], tri[1])
        poly = []
        for p in tri:
            i = at.get((round(p[0], 6), round(p[1], 6)))
            if i is None:
                raise ValueError("flat_patch: ear-clip introduced a vertex off the ring "
                                 "-- the weld would not be exact")
            src = ring[i]
            # UV is positional inside the quadrant, so neighbouring patch tris agree
            fu = (p[0] / 4.0) % 1.0
            fv = (-p[1] / 4.0) % 1.0
            poly.append(((float(src[0]), float(y), float(src[2])),
                         tuple(float(c) for c in normal),
                         (u0 + (u1 - u0) * fu, v0 + (v1 - v0) * fv),
                         (float(idall), 0.0, 0.0, 1.0)))
        out.append(poly)
    return out


def _clip_plan(poly, axis: int, plane: float, below: bool):
    """Sutherland-Hodgman half-plane clip of a plan polygon [(x, z), ...].

    Keeps ORIGINAL vertices that are inside (byte-exact -- the ring reuse contract) and
    mints crossings by the same lerp expression regardless of which side asks, so two
    lattice cells clipping the same edge against their shared plane produce the SAME
    point (the watertightness argument the transplant's border re-partition already uses).
    """
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        av, bv = a[axis], b[axis]
        ain = (av <= plane + 1e-9) if below else (av >= plane - 1e-9)
        bin_ = (bv <= plane + 1e-9) if below else (bv >= plane - 1e-9)
        if ain:
            out.append(a)
        if ain != bin_:
            t = (plane - av) / (bv - av)
            p = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
            out.append((plane, p[1]) if axis == 0 else (p[0], plane))
    # collapse consecutive duplicates a grazing clip can mint
    dedup = []
    for p in out:
        if not dedup or abs(p[0] - dedup[-1][0]) > 1e-9 or abs(p[1] - dedup[-1][1]) > 1e-9:
            dedup.append(p)
    if len(dedup) > 1 and abs(dedup[0][0] - dedup[-1][0]) < 1e-9 \
            and abs(dedup[0][1] - dedup[-1][1]) < 1e-9:
        dedup.pop()
    return dedup


def _plan_area2(poly) -> float:
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1]
                   - poly[(i + 1) % len(poly)][0] * poly[i][1]
                   for i in range(len(poly))))


def _despur(poly):
    """Remove zero-width spurs (A, X, A) a half-plane clip mints where the ring boundary
    runs along the clip plane and back -- the ear-clipper cannot eat a repeated vertex
    (measured: the crescent's cell (235,-42) piece carried (940,-168), (940,-164),
    (940,-168) and stuck with 5 verts)."""
    poly = list(poly)
    changed = True
    while changed and len(poly) >= 3:
        changed = False
        n = len(poly)
        for i in range(n):                            # adjacent duplicate (snap can mint)
            a, b = poly[i], poly[(i + 1) % n]
            if abs(a[0] - b[0]) < 1e-9 and abs(a[1] - b[1]) < 1e-9:
                del poly[(i + 1) % n]
                changed = True
                break
        if changed:
            continue
        for i in range(n):
            a, b = poly[i], poly[(i + 2) % n]
            if abs(a[0] - b[0]) < 1e-9 and abs(a[1] - b[1]) < 1e-9:
                for k in sorted(((i + 1) % n, (i + 2) % n), reverse=True):
                    del poly[k]
                changed = True
                break
    return poly


def lattice_patch(ring, *, y: float, uv_quads, idall: int, normal=(0.0, 1.0, 0.0),
                  winding: float = -1.0, tile: float = 4.0,
                  snap_verts=(), snap_tol: float = 0.049) -> list[list[tuple]]:
    """Fill a ring with STOCK-SHAPED water: full 4u lattice tiles plus per-cell margins.

    THE LATTICE LAW. :func:`flat_patch` ear-clips the whole footprint, which is lawful
    GEOMETRY and a synthetic WATER SHAPE: stock sea4 is a strict 4u lattice (measured:
    tri area median 8.0 max 10.5u2, edge max 7.0u), while the crescent's 41-tri ear-clip
    fill minted 615u2 / 71.5u-edge triangles. The engine's wave animation displaces
    per-vertex, so a giant triangle renders as a faceted 'iceberg' with its single tile
    quadrant smeared across ~18 tiles of water (playtest 2026-08-04). Shape is part of
    the vocabulary; carry it.

    Construction: clip the ring polygon to every 4u lattice cell it overlaps. A piece
    that IS the full cell becomes stock's own two tris (diagonal orientation mixed per
    tile by the calibrated hash -- stock measures 298 NW-SE / 156 NE-SW); a partial piece
    is ear-clipped WITHIN its cell, so no emitted triangle spans a tile. Ring vertices
    are reused byte-exact (the clipper keeps inside originals); adjacent cells share
    every minted crossing by identical-expression construction. UV is the per-tile
    quadrant (both tris of a tile agree -- THE PER-TILE QUADRANT LAW) with the positional
    rule inside the quadrant, and ``winding``/``normal`` follow the sheet as in
    :func:`flat_patch`.
    """
    quads = [tuple(float(c) for c in q) for q in uv_quads]
    if not quads:
        raise ValueError("lattice_patch needs at least one uv quadrant")
    plan = [(float(p[0]), float(p[2])) for p in ring]
    exact = {(round(p[0], 6), round(p[2], 6)): (float(p[0]), float(p[2])) for p in ring}
    # DENSIFY FIRST, one chain: a lattice line crossing a ring edge mints a vertex, and
    # when the neighbouring sheet already subdivides that boundary a hair away, the pair
    # is a near-miss the weld audit (rightly) refuses -- measured on the crescent:
    # (912.0, -160.8919) minted 0.012u from sea4's own (912.0117, -160.8945). A minted
    # vertex within ``snap_tol`` of an EXISTING sheet vertex snaps ONTO it. The rule is
    # deterministic on position, so two cells clipping the same edge snap identically
    # and stay watertight; ring verts themselves are never snapped.
    snap_grid: dict = {}
    for p in snap_verts:
        q = (float(p[0]), float(p[-1])) if len(p) > 2 else (float(p[0]), float(p[1]))
        snap_grid.setdefault((int(q[0] // 1), int(q[1] // 1)), []).append(q)

    def _snap(p):
        if not snap_grid or (round(p[0], 6), round(p[1], 6)) in exact:
            return p
        best, bd = p, snap_tol
        gx, gz = int(p[0] // 1), int(p[1] // 1)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for q in snap_grid.get((gx + dx, gz + dz), ()):
                    d = math.hypot(p[0] - q[0], p[1] - q[1])
                    if d < bd:
                        best, bd = q, d
        return best
    if len(plan) < 3:
        raise ValueError("ring needs at least three points")
    xs = [p[0] for p in plan]
    zs = [p[1] for p in plan]
    gx0, gx1 = math.floor(min(xs) / tile), math.ceil(max(xs) / tile)
    gz0, gz1 = math.floor(min(zs) / tile), math.ceil(max(zs) / tile)

    out = []

    def emit(tri, qi, cx0, cz1):
        # UV is positional RELATIVE TO THE CELL, far edge at 1.0 -- the modulo rule
        # ((x/4) % 1) wraps a lattice-aligned far edge back to 0, which collapses a full
        # tile's four corners onto the quadrant corner: one texel smeared over the tile
        # (measured: the gate read 121 of 142 fill tiles as quadrant (0,0) with
        # adjacent-variation 0.098 against stock's 0.880). Every tri is within one cell,
        # so the cell frame is well-defined.
        u0, v0, u1, v1 = quads[qi]
        cross = ((tri[1][0] - tri[0][0]) * (tri[2][1] - tri[0][1])
                 - (tri[2][0] - tri[0][0]) * (tri[1][1] - tri[0][1]))
        if winding and cross * winding < 0:
            tri = (tri[0], tri[2], tri[1])
        poly = []
        for p in tri:
            src = exact.get((round(p[0], 6), round(p[1], 6)), p)   # ring verts byte-exact
            fu = (p[0] - cx0) / tile
            fv = (cz1 - p[1]) / tile
            poly.append(((float(src[0]), float(y), float(src[1])),
                         tuple(float(c) for c in normal),
                         (u0 + (u1 - u0) * fu, v0 + (v1 - v0) * fv),
                         (float(idall), 0.0, 0.0, 1.0)))
        out.append(poly)

    for gx in range(gx0, gx1 + 1):
        for gz in range(gz0, gz1 + 1):
            x0, x1 = gx * tile, (gx + 1) * tile
            z0, z1 = gz * tile, (gz + 1) * tile
            piece = plan
            for (axis, plane, below) in ((0, x0, False), (0, x1, True),
                                         (1, z0, False), (1, z1, True)):
                piece = _clip_plan(piece, axis, plane, below)
                if len(piece) < 3:
                    break
            piece = _despur([_snap(p) for p in piece])
            if len(piece) < 3 or _plan_area2(piece) < 1e-9:
                continue
            # the per-TILE choices: quadrant, and diagonal orientation for a full cell.
            # Cell indices in the SAME convention as _tile_quad_index's centroid mapping
            # (plan z IS world z), so a fill tile and a retagged tile at one location
            # hash identically.
            cgx, cgz = int((x0 + tile / 2.0) // tile), int((-(z0 + tile / 2.0)) // tile)
            qi = _cell_quad_index(cgx, cgz, len(quads))
            if (_plan_area2(piece) >= 2.0 * tile * tile - 1e-6 and len(piece) == 4):
                c00, c10, c11, c01 = (x0, z0), (x1, z0), (x1, z1), (x0, z1)
                h = (_cell_quad_index(cgx, cgz, 1 << 30) >> 7) & 1
                if h:                                             # NE-SW hypotenuse
                    tris = [(c00, c10, c01), (c10, c11, c01)]
                else:                                             # NW-SE hypotenuse
                    tris = [(c00, c10, c11), (c00, c11, c01)]
            else:
                tris = earclip(piece, quality=True)
            for t in tris:
                emit(t, qi, x0, z1)
    return out


def _tile_origin(tri, tile: float = 4.0) -> tuple[float, float]:
    """World (x, -z) origin of the 4u tile a flat triangle sits in, keyed on its centroid."""
    cx = sum(v[0][0] for v in tri) / 3.0
    cz = sum(v[0][2] for v in tri) / 3.0
    return (math.floor(cx / tile) * tile, math.floor((-cz) / tile) * tile)


def _tile_quad_index(tri, n_quads: int, tile: float = 4.0) -> int:
    """Which uv quadrant a flat water triangle takes, keyed on its 4u TILE.

    Both triangles of a tile land on the same index by construction, because the key is
    the tile, not the triangle. The spread across tiles is a fixed hash rather than a
    counter: a counter walks in scan order and lays down visible diagonal banding, while
    stock's own spread is uniform across parities (measured).
    """
    cx = sum(v[0][0] for v in tri) / 3.0
    cz = sum(v[0][2] for v in tri) / 3.0
    return _cell_quad_index(int(cx // tile), int((-cz) // tile), n_quads)


def _cell_quad_index(gx: int, gz: int, n_quads: int) -> int:
    """The tile hash on CELL INDICES -- callers that already know the cell must use this
    rather than faking a triangle for :func:`_tile_quad_index` (a 1-vert fake divides by
    the 3 of a real centroid, collapsing neighbouring cells onto one key: measured on the
    first lattice fill as quadrant counts 119/10/1/5 and adjacent-variation 0.078 against
    stock's 0.880 -- a flat repeat).

    A MIXING hash, not `(a*p ^ b*q) % n`. Taking a modulus keeps only the LOW BITS, so
    large primes collapse to a small lattice: the first version made tile parity PREDICT
    the quadrant, every neighbour differed (adjacent-variation 1.000 against stock's
    0.880), and the sheet alternated in perfect lockstep -- regular where stock is
    irregular. Avalanche the bits first so the low bits actually depend on all of them.
    """
    h = (gx * 0x9E3779B1) ^ (gz * 0x85EBCA77)
    h &= 0xFFFFFFFF
    h ^= h >> 16
    h = (h * 0x7FEB352D) & 0xFFFFFFFF
    h ^= h >> 15
    h = (h * 0x846CA68B) & 0xFFFFFFFF
    h ^= h >> 16
    return h % n_quads


def retag_flat(tris, *, uv_quads, idall: int, pick=None, winding: float = -1.0) -> list:
    """Re-shade flat water triangles into another band's vocabulary, geometry VERBATIM.

    The counterpart to :func:`flat_patch`: that one FILLS a hole with new triangles, this
    one leaves every triangle exactly where it is and changes only what it looks like.
    Positions, normals and vertex order are untouched, so the tri count cannot change and
    no weld can move -- the edit is unable to introduce a crack by construction.

    Why this and not drop-and-fill: removing an island's shallow ring leaves an ANNULUS
    (bounded inside by the waterline, outside by the deep sheet's inner edge), which
    :func:`flat_patch` cannot fill -- it takes a simple ring. And nothing about the ring's
    geometry is wrong: stock sea3/sea5 are flat at y=0, share the deep sheet's normal byte
    constant, and wind the same way. Only the SHADE is wrong once the ring has been cropped
    out of its context.

    UV follows the same positional rule as :func:`flat_patch` (4u period inside the chosen
    quadrant), so a converted band and a neighbouring fill agree where they meet.
    ``winding`` is asserted, not imposed: a caller converting a band that does not already
    wind the target's way is doing something other than a re-shade and should know.
    """
    quads = [tuple(float(c) for c in q) for q in uv_quads]
    if not quads:
        raise ValueError("retag_flat needs at least one uv quadrant")
    out = []
    for ti, t3 in enumerate(tris):
        # THE PER-TILE QUADRANT LAW. Measured on stock sea4: of 135 distinct 4u tiles,
        # 134 have EVERY triangle on the same quadrant (99.3%). The quadrant is a
        # per-TILE choice and the two triangles of a tile must agree. Choosing per
        # TRIANGLE puts a different atlas sub-tile either side of every tile diagonal --
        # over 644 converted tris that renders as a checkerboard across the whole sheet,
        # which is exactly what reached a playtest.
        #
        # The earlier claim that the quadrant is "genuinely free, so a patch cannot pick
        # a wrong tile" over-read the measurement: what was measured is that the
        # DISTRIBUTION is uniform across world-cell parities, which says nothing about
        # whether NEIGHBOURING triangles may differ. They may not.
        cq = (pick(ti) if pick else _tile_quad_index(t3, len(quads))) % len(quads)
        cross = ((t3[1][0][0] - t3[0][0][0]) * (t3[2][0][2] - t3[0][0][2])
                 - (t3[2][0][0] - t3[0][0][0]) * (t3[1][0][2] - t3[0][0][2]))
        if winding and cross and cross * winding < 0:
            raise ValueError(
                f"retag_flat: triangle {ti} winds {'+' if cross > 0 else '-'} but the "
                f"target band winds {'+' if winding > 0 else '-'} -- a re-shade must not "
                f"flip a face (a back-facing sea tri renders yet reads as void)")
        u0, v0, u1, v1 = quads[cq]
        # UV RELATIVE TO THE TRIANGLE'S OWN TILE, NOT MODULO THE LATTICE. `x/4 % 1` wraps
        # to 0 at every tile edge, so a triangle SPANNING a tile gets fu = 0 at both ends
        # -- a collapsed UV that stretches one texel across the face. flat_patch can use
        # the modulo form because its fill triangles are small slivers inside a hole;
        # these are stock water tris with median plan area 8u2 against a 16u2 tile, so
        # they span most of one. Anchoring on the tile the triangle sits in lets fu reach
        # 1.0 at the far edge, which is how stock maps a tile across its quadrant.
        gx0, gz0 = _tile_origin(t3)
        poly = []
        for (pos, nrm, _uv, _tan) in t3:
            fu = min(max((pos[0] - gx0) / 4.0, 0.0), 1.0)
            fv = min(max((-pos[2] - gz0) / 4.0, 0.0), 1.0)
            poly.append((tuple(float(c) for c in pos), tuple(float(c) for c in nrm),
                         (u0 + (u1 - u0) * fu, v0 + (v1 - v0) * fv),
                         (float(idall), 0.0, 0.0, 1.0)))
        out.append(poly)
    return out
