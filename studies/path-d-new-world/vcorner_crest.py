"""THE SHORE FAIRING — the V-corner coast rebuilt additive so the wall-slide survives.

Registration: VSHORE-SEAL-PREDICTION.md, AMENDMENT 2 (+ the build-time discovery,
recorded in AMENDMENT 3): the crest verts are HUB verts with lawn on both sides, so
moving them drags interior lawn inside-out (3 flipped tris on the first build — the
winding gate held). And v5->v8 is already STRAIGHT at 114.9°: no vertex motion can
steepen a straight line. The fix is ADDITIVE:

- a new lawn strip seaward of the old boundary: outer edge = the 126° chord from
  v5 (376.29,-509.40) to the tip twin v9' (383.44,-514.59), then a fairing across
  the notch (v9-v10-v11) into the southern 181.5° run at v11 (380.08,-516.73);
- old topo-58 faces whose plan the strip covers are DELETED (first-hit shadowing);
- a new near-vertical curtain (feet 0.45u seaward at y=0, the bench's own cliff
  vocabulary: mapid 232, v 0.893/0.923, u sawtooth 0.699+0.012643/u) along the new
  outer edge;
- every new tri seam-clipped to its owner block (THE BLOCK LAW);
- the incremental sea cut beneath the new lawn (treat_part vs staged terrain).

No vertex moves -> no flip risk by construction. Stages: --stage1 build+verify+walk
gates (default) / --stage2 latent sweep / --deploy. READ-ONLY except --deploy.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import os
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402
from probe_vcorner_trap import static_map, drive_walkers    # noqa: E402
from probe_vcorner_latent import sweep, refine              # noqa: E402
from vcorner_sea_cut import treat_part, live_path           # noqa: E402
from ff9mapkit.world.extract import CH_POS, CH_NRM, CH_UV, CH_TAN  # noqa: E402

BLOCKS = [(5, 7), (5, 8)]
V5 = (376.29, -509.40)
# THE QUANTIZED-FAN LAW (measured on the 126° staged run): the fan probes in 11.25°
# steps, so a slide is robust only when |hold - tangent| <= 78.75 - 11.25 = 67.5°.
# Chord 138° gives both 202.5° (south hug) and 22.5° (north hug) a 64.5° mismatch.
CHORD_DEG = 138.0
DIR = (math.sin(math.radians(CHORD_DEG)), math.cos(math.radians(CHORD_DEG)))
# the old boundary (inner polyline) v5..v11, from probe_vcorner_boundary
INNER = [(376.29, -509.40), (380.00, -511.12), (381.12, -511.64), (381.90, -512.00),
         (383.79, -514.11), (383.29, -514.46), (380.08, -516.73)]
LAWN_Y = 3.2
CURTAIN_OUT = 0.45                                          # feet seaward at y=0 (ny ~0.139 > 0.1)
V_TOP, V_BOT = 0.893, 0.923                                 # the cliff vocabulary (full_skirt)
U0, URATE = 0.699, 0.012643
TAN_CLIFF = (232.0, 0.0, 0.0, 1.0)
SEAM_Z = -512.0
CHANGED_BBOX = (374.0, 386.5, -518.0, -507.5)
OUTD = HERE / "out" / "vcorner_crest"
BACKUPS = Path(r"C:\gd\Dream-World-IX\backups")
PIN = (376.5, -509.5)
# v2 builds from the PRE-fairing Terrain baseline (live carries the v1 fairing + fins);
# live Sea4 stays the input -- it already carries the crest cut for the same strip.
# THE BASELINE SEAM (P0 fold-back). These timestamped backups are NOT the
# source of truth — they are a snapshot of one. PROVEN 2026-08-02:
# `full_skirt.py --bench-src <any terrace-strip-prewall.*>` reproduces both
# of these files BYTE-IDENTICALLY, and all 19 prewall snapshots are
# themselves byte-identical. So the corner's base is regenerable, and
# $FF9_BENCH_BASELINE (a dir holding the six regenerated Terrain files) lets
# the whole corner build run off the regenerated bench instead of off backups
# that nothing tracks. Driver: `bench_pipeline.py`.
_BASE_ENV = os.environ.get("FF9_BENCH_BASELINE")
if _BASE_ENV:
    BASELINE_T = {(bx, by): Path(_BASE_ENV) / f"Block[{bx}][{by}] Terrain.ff9mesh"
                  for (bx, by) in ((5, 7), (5, 8))}
else:
    BASELINE_T = {(5, 7): BACKUPS / "Block[5][7] Terrain.ff9mesh.r7.20260802-025232",
                  (5, 8): BACKUPS / "Block[5][8] Terrain.ff9mesh.r8.20260802-025232"}


def perp_foot(p):
    t = (p[0] - V5[0]) * DIR[0] + (p[1] - V5[1]) * DIR[1]
    return (V5[0] + t * DIR[0], V5[1] + t * DIR[1])


def seg_project(p, a, b):
    d = (b[0] - a[0], b[1] - a[1])
    L = math.hypot(*d)
    t = max(0.0, min(L, ((p[0] - a[0]) * d[0] + (p[1] - a[1]) * d[1]) / L))
    return (a[0] + t * d[0] / L, a[1] + t * d[1] / L)


# E: the chord point from which the fairing to v11 runs at EXACTLY 202.5° (the south
# hug's held heading -> mismatch 0 on the fairing; northbound reverse 22.5° likewise)
_k = math.tan(math.radians(22.5))
_t = ((INNER[6][0] - V5[0]) - _k * (INNER[6][1] - V5[1])) / (DIR[0] - _k * DIR[1])
E = (V5[0] + _t * DIR[0], V5[1] + _t * DIR[1])
OUTER = [INNER[0],                                          # pinched start at v5
         perp_foot(INNER[1]), perp_foot(INNER[2]), perp_foot(INNER[3]),
         E, INNER[6]]                                       # fairing straight to v11 (pinched end)


def poly_area2(ps):
    s = 0.0
    for i in range(len(ps)):
        a, b = ps[i], ps[(i + 1) % len(ps)]
        s += a[0] * b[1] - b[0] * a[1]
    return s


STRIP_POLY = INNER + list(reversed(OUTER[1:-1]))            # the strip ring (plan)


def in_strip(p, eps=1e-6):
    n = len(STRIP_POLY)
    inside = False
    for i in range(n):
        a, b = STRIP_POLY[i], STRIP_POLY[(i + 1) % n]
        if (a[1] > p[1]) != (b[1] > p[1]):
            xin = a[0] + (p[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if p[0] < xin - eps:
                inside = not inside
    return inside


def zip_tris(A, B):
    """Triangulate between polylines A and B sharing endpoints (A[0]==B[0], A[-1]==B[-1])."""
    tris = []
    i = j = 0
    while i < len(A) - 1 or j < len(B) - 1:
        adv_a = i < len(A) - 1 and (j >= len(B) - 1 or i <= j)
        if adv_a:
            tris.append((A[i], A[i + 1], B[j]))
            i += 1
        else:
            tris.append((A[i], B[j + 1], B[j]))
            j += 1
    return [t for t in tris
            if abs((t[1][0] - t[0][0]) * (t[2][1] - t[0][1])
                   - (t[2][0] - t[0][0]) * (t[1][1] - t[0][1])) > 1e-6]


def clip_halfplane(poly, keep_north):
    """Sutherland-Hodgman vs z = SEAM_Z. poly = [(x,z),...]; keep z>=SEAM (north) or z<=SEAM."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ain = (a[1] >= SEAM_Z) if keep_north else (a[1] <= SEAM_Z)
        bin_ = (b[1] >= SEAM_Z) if keep_north else (b[1] <= SEAM_Z)
        if ain:
            out.append(a)
        if ain != bin_:
            t = (SEAM_Z - a[1]) / (b[1] - a[1])
            out.append((a[0] + t * (b[0] - a[0]), SEAM_Z))
    return out


def fan(poly):
    return [(poly[0], poly[i], poly[i + 1]) for i in range(1, len(poly) - 1)]


def lawn_affines(paths_with_offsets):
    """Per-tri WORLD-frame plan->uv affine maps for every walkable lawn tri across the
    given blocks — the lawn's u-phase flips between tile families, so each strip tri
    borrows the affine of the old lawn tri across its INNER edge (the same donor for
    every clipped fragment -> uv continuity across the block seam AND the boundary)."""
    out = []
    for (path, ox, oz) in paths_with_offsets:
        d = W.M.read_ff9mesh(path)
        idx, V, Uv, T = d["indices"], d["verts"], d["uvs"], d["tangents"]
        for t0 in range(0, len(idx), 3):
            t = idx[t0:t0 + 3]
            topo = (int(round(T[t[0]][0])) & 0xFC) >> 2
            if topo not in W.WALK_OK:
                continue
            p3 = [(V[j][0] + ox, V[j][1], V[j][2] + oz) for j in t]
            d0 = ((p3[1][0] - p3[0][0]) * (p3[2][2] - p3[0][2])
                  - (p3[2][0] - p3[0][0]) * (p3[1][2] - p3[0][2]))
            if abs(d0) < 1e-6:
                continue
            u3 = [Uv[j] for j in t]

            def make(pp, uu, dd):
                def f(x, z):
                    w1 = ((x - pp[0][0]) * (pp[2][2] - pp[0][2])
                          - (pp[2][0] - pp[0][0]) * (z - pp[0][2])) / dd
                    w2 = ((pp[1][0] - pp[0][0]) * (z - pp[0][2])
                          - (x - pp[0][0]) * (pp[1][2] - pp[0][2])) / dd
                    w0 = 1.0 - w1 - w2
                    return (w0 * uu[0][0] + w1 * uu[1][0] + w2 * uu[2][0],
                            w0 * uu[0][1] + w1 * uu[1][1] + w2 * uu[2][1])
                return f
            out.append((p3, make(p3, u3, d0)))
    assert out, "no lawn tris for affine maps"
    return out


def affine_for(affs, x, z):
    """The affine of the lawn tri containing WORLD (x, z), else the nearest one."""
    for (p3, f) in affs:
        d0 = ((p3[1][0] - p3[0][0]) * (p3[2][2] - p3[0][2])
              - (p3[2][0] - p3[0][0]) * (p3[1][2] - p3[0][2]))
        w1 = ((x - p3[0][0]) * (p3[2][2] - p3[0][2])
              - (p3[2][0] - p3[0][0]) * (z - p3[0][2])) / d0
        w2 = ((p3[1][0] - p3[0][0]) * (z - p3[0][2])
              - (x - p3[0][0]) * (p3[1][2] - p3[0][2])) / d0
        if w1 >= -1e-9 and w2 >= -1e-9 and (1 - w1 - w2) >= -1e-9:
            return f
    best = min(affs, key=lambda pf: min((v[0] - x) ** 2 + (v[2] - z) ** 2 for v in pf[0]))
    return best[1]


U_SEED = 0.8579                                             # the kept face #42/#43's u AT v5
U_LO, U_HI = 0.699, 0.947                                   # the local sawtooth band (measured)


def outer_with_seam():
    """OUTER with the block-seam crossing inserted as a vertex — no curtain quad may
    cross z = SEAM_Z, so vertical faces are never plan-clipped (the run-3 fin bug)."""
    t_seam = (SEAM_Z - V5[1]) / DIR[1]
    S = (V5[0] + t_seam * DIR[0], SEAM_Z)
    out = [OUTER[0]]
    for i in range(1, len(OUTER)):
        prev, cur = out[-1], OUTER[i]
        if (prev[1] - SEAM_Z) * (cur[1] - SEAM_Z) < 0:
            out.append(S)
        out.append(cur)
    return out


def build_terrain():
    print("=== BUILD: THE SHORE FAIRING v2 (seam-safe curtain, edge-donor lawn UVs) ===")
    outerS = outer_with_seam()
    for i in range(len(outerS) - 1):
        d = (outerS[i + 1][0] - outerS[i][0], outerS[i + 1][1] - outerS[i][1])
        print(f"   outer ({outerS[i][0]:7.2f},{outerS[i][1]:8.2f}) -> seg {math.hypot(*d):5.2f}u "
              f"@ {math.degrees(math.atan2(d[0], d[1])) % 360:6.1f}deg")
    assert abs(poly_area2(STRIP_POLY)) > 1.0, "degenerate strip polygon"

    affs = lawn_affines([(BASELINE_T[(bx, by)], 64.0 * bx, -64.0 * by)
                         for (bx, by) in BLOCKS])
    lawn3 = []                                              # (tri_plan, donor) per pre-clip tri
    i = j = 0
    A, B = INNER, outerS
    last_donor = None
    while i < len(A) - 1 or j < len(B) - 1:
        adv_a = i < len(A) - 1 and (j >= len(B) - 1 or i <= j)
        if adv_a:
            tri = (A[i], A[i + 1], B[j])
            mx, mz = (A[i][0] + A[i + 1][0]) / 2, (A[i][1] + A[i + 1][1]) / 2
            dx, dz = A[i + 1][0] - A[i][0], A[i + 1][1] - A[i][1]
            L = math.hypot(dx, dz) or 1.0
            donor = affine_for(affs, mx - 0.06 * dz / L, mz + 0.06 * dx / L)  # landward nudge
            last_donor = donor
            i += 1
        else:
            tri = (A[i], B[j + 1], B[j])
            donor = last_donor or affine_for(affs, A[i][0], A[i][1])
            j += 1
        a2 = abs((tri[1][0] - tri[0][0]) * (tri[2][1] - tri[0][1])
                 - (tri[2][0] - tri[0][0]) * (tri[1][1] - tri[0][1]))
        if a2 > 1e-6:
            lawn3.append((tri, donor))

    feet = []
    for i, p in enumerate(outerS):
        segs = []
        if i > 0:
            segs.append((p[0] - outerS[i - 1][0], p[1] - outerS[i - 1][1]))
        if i < len(outerS) - 1:
            segs.append((outerS[i + 1][0] - p[0], outerS[i + 1][1] - p[1]))
        nx = nz = 0.0
        for (dx, dz) in segs:
            L = math.hypot(dx, dz) or 1.0
            nx += dz / L
            nz += -dx / L
        L = math.hypot(nx, nz) or 1.0
        feet.append((p[0] + CURTAIN_OUT * nx / L, p[1] + CURTAIN_OUT * nz / L))
    arc = [0.0]
    for i in range(len(outerS) - 1):
        arc.append(arc[-1] + math.hypot(outerS[i + 1][0] - outerS[i][0],
                                        outerS[i + 1][1] - outerS[i][1]))

    def saw(a):
        return U_LO + (U_SEED - U_LO + URATE * a) % (U_HI - U_LO)

    curt = []                                               # (block_by, tri3, uv3)
    for i in range(len(outerS) - 1):
        a, b, fa, fb = outerS[i], outerS[i + 1], feet[i], feet[i + 1]
        cz = (a[1] + b[1]) / 2
        cby = 7 if cz >= SEAM_Z else 8
        ua, ub = saw(arc[i]), saw(arc[i + 1])
        if ub < ua:                                         # the sawtooth wrapped mid-quad:
            ub = ua + URATE * (arc[i + 1] - arc[i])         # extend past U_HI for this quad
        c0 = ((a[0], LAWN_Y, a[1]), (b[0], LAWN_Y, b[1]), (fa[0], 0.0, fa[1]))
        c1 = ((b[0], LAWN_Y, b[1]), (fb[0], 0.0, fb[1]), (fa[0], 0.0, fa[1]))
        curt.append((cby, c0, ((ua, V_TOP), (ub, V_TOP), (ua, V_BOT))))
        curt.append((cby, c1, ((ub, V_TOP), (ub, V_BOT), (ua, V_BOT))))
    for (_cby, _t3, uv3) in curt:                           # uv audit: the local cliff band
        for (u, v) in uv3:
            assert U_LO - 1e-6 <= u <= U_HI + 0.06 and V_TOP - 1e-6 <= v <= V_BOT + 1e-6, \
                f"curtain uv ({u},{v}) outside the local cliff band"

    staged = {}
    for (bx, by) in BLOCKS:
        ox, oz = 64.0 * bx, -64.0 * by
        lp = BASELINE_T[(bx, by)]
        d = W.M.read_ff9mesh(lp)
        verts = [list(v) for v in d["verts"]]
        normals = [list(v) for v in d["normals"]]
        uvs = [list(v) for v in d["uvs"]]
        tans = [list(v) for v in d["tangents"]]
        idx = d["indices"]

        drop = set()
        for t0 in range(0, len(idx), 3):
            t = idx[t0:t0 + 3]
            topo = (int(round(tans[t[0]][0])) & 0xFC) >> 2
            if topo != 58:
                continue
            pw = [(verts[j][0] + ox, verts[j][2] + oz) for j in t]
            cen = ((pw[0][0] + pw[1][0] + pw[2][0]) / 3, (pw[0][1] + pw[1][1] + pw[2][1]) / 3)
            if any(in_strip(p) for p in pw) or in_strip(cen) \
                    or any(in_tri(q, pw) for q in STRIP_POLY):
                drop.add(t0 // 3)
        new_idx = []
        for t0 in range(0, len(idx), 3):
            if t0 // 3 not in drop:
                new_idx += list(idx[t0:t0 + 3])

        lawn_nrm = lawn_tan = None
        for t0 in range(0, len(idx), 3):
            t = idx[t0:t0 + 3]
            topo = (int(round(tans[t[0]][0])) & 0xFC) >> 2
            if topo in W.WALK_OK:
                lawn_nrm = list(normals[t[0]])
                lawn_tan = list(tans[t[0]])
                break
        wall_nrm = list(normals[idx[next(iter(drop)) * 3]]) if drop else [0.0, 0.3, 0.9]

        def emit(p3, uv3, nrm, tan, up_sign):
            a2 = ((p3[1][0] - p3[0][0]) * (p3[2][2] - p3[0][2])
                  - (p3[2][0] - p3[0][0]) * (p3[1][2] - p3[0][2]))
            if abs(a2) < 1e-6 and up_sign > 0:
                return                                      # degenerate LAWN tri; curtain
            order = (0, 1, 2)                               # plan-degenerates are legitimate
            ny = (p3[1][2] - p3[0][2]) * (p3[2][0] - p3[0][0]) \
                - (p3[1][0] - p3[0][0]) * (p3[2][2] - p3[0][2])
            if ny * up_sign < 0:
                order = (0, 2, 1)
            for k in order:
                verts.append([p3[k][0] - ox, p3[k][1], p3[k][2] - oz])
                uvs.append(list(uv3[k]))
                normals.append(list(nrm))
                tans.append(list(tan))
                new_idx.append(len(verts) - 1)

        n_lawn = 0
        for ((a, b, c), donor) in lawn3:
            poly = clip_halfplane([a, b, c], keep_north=(by == 7))
            for (p, q, r) in fan(poly):
                p3 = [(p[0], LAWN_Y, p[1]), (q[0], LAWN_Y, q[1]), (r[0], LAWN_Y, r[1])]
                uv3 = [donor(pt[0], pt[2]) for pt in p3]    # ONE world-frame donor per pre-clip tri
                emit(p3, uv3, lawn_nrm, lawn_tan, +1)
                n_lawn += 1

        n_curt = 0
        for (cby, tri3, uv3) in curt:
            if cby != by:
                continue
            emit([list(v) for v in tri3], list(uv3), wall_nrm, list(TAN_CLIFF), +1)
            n_curt += 1

        print(f"   [{bx}][{by}]: {len(drop)} old faces deleted, {n_lawn} lawn tris + "
              f"{n_curt} curtain tris added; tris {len(idx) // 3} -> {len(new_idx) // 3}, "
              f"verts {d['vcount']} -> (expanded)")
        # THE UNINDEXED CONTRACT: 3 fresh verts per tri (WMBlock.AddWalkMesh's layout)
        ev, en, eu, et, eidx = [], [], [], [], []
        for k in new_idx:
            eidx.append(len(ev))
            ev.append(list(verts[k]))
            en.append(list(normals[k]))
            eu.append(list(uvs[k]))
            et.append(list(tans[k]))
        bm = W.M.blockmesh_from_ff9mesh(lp, disc=W.DISC, x=bx, y=by, part="terrain")
        chan = dict(bm.chan_arrays)
        chan[CH_POS], chan[CH_NRM], chan[CH_UV], chan[CH_TAN] = ev, en, eu, et
        tris = [[eidx[k], eidx[k + 1], eidx[k + 2]] for k in range(0, len(eidx), 3)]
        out = dataclasses.replace(bm, vcount=len(ev), chan_arrays=chan,
                                  flat_index=eidx, tris=tris)
        OUTD.mkdir(parents=True, exist_ok=True)
        sp = OUTD / f"Block[{bx}][{by}] Terrain.ff9mesh"
        W.M.write_ff9mesh(out, sp)
        staged[(bx, by, "Terrain")] = sp
    return staged


def in_tri(p, tw):
    d0 = ((tw[1][0] - tw[0][0]) * (tw[2][1] - tw[0][1])
          - (tw[2][0] - tw[0][0]) * (tw[1][1] - tw[0][1]))
    if abs(d0) < 1e-9:
        return False
    w1 = ((p[0] - tw[0][0]) * (tw[2][1] - tw[0][1])
          - (tw[2][0] - tw[0][0]) * (p[1] - tw[0][1])) / d0
    w2 = ((tw[1][0] - tw[0][0]) * (p[1] - tw[0][1])
          - (p[0] - tw[0][0]) * (tw[1][1] - tw[0][1])) / d0
    return w1 > 0 and w2 > 0 and (1 - w1 - w2) > 0


def hug(world, spawns, along, inward, pass_line, steps=400):
    out = []
    for (sx, sz) in spawns:
        walk = [s for s in W.all_sheets(world, sx, sz) if s[1] in W.WALK_OK]
        if len(walk) != 1:
            out.append((sx, sz, "bad-spawn", 0))
            continue
        st = dict(x=sx, y=walk[0][0], z=sz, heading=along + inward)
        ring = W.Ring()
        stalls = 0
        passed = None
        for k in range(steps):
            if W.walk_step(world, ring, st) == "stall":
                stalls += 1
            if pass_line(st["x"], st["z"]):
                passed = k
                break
        out.append((sx, sz, f"PASS@{passed}" if passed is not None
                    else f"CAUGHT({st['x']:.1f},{st['z']:.1f})", stalls))
    return out


def coverage_delta(world_live, world_staged):
    lost, gained, off = [], [], []
    x = 372.0
    while x <= 390.0:
        z = -519.0
        while z <= -506.0:
            a = any(s[1] in W.WALK_OK for s in W.all_sheets(world_live, x, z))
            b = any(s[1] in W.WALK_OK for s in W.all_sheets(world_staged, x, z))
            if a and not b:
                lost.append((round(x, 1), round(z, 1)))
            if b and not a:
                gained.append((x, z))
                if not in_strip((x, z)):
                    off.append((round(x, 1), round(z, 1)))
            z += 0.2
        x += 0.2
    print(f"COVERAGE DELTA: lost={len(lost)} gained={len(gained)} off-strip={len(off)}")
    if lost:
        print(f"   LOST (must be 0): {lost[:8]}")
    if off:
        print(f"   OFF-STRIP gained (must be ~0): {off[:8]}")
    return len(lost) == 0 and len(off) <= 2


def stage1():
    print("loading the PRE-FAIRING BASELINE world (backups Terrain + live sea) ...")
    world_base = W.load_world(part_src={(bx, by, "Terrain"): BASELINE_T[(bx, by)]
                                        for (bx, by) in BLOCKS})
    staged = build_terrain()
    world_t = W.load_world(part_src=dict(staged))

    g_cov = coverage_delta(world_base, world_t)

    print("\n=== incremental SEA CUT (coverage vs staged terrain) ===")
    sea_records = {}
    for (bx, by) in BLOCKS:
        changed, out, records = treat_part(world_t, bx, by, "Sea4")
        if changed:
            sp = OUTD / f"Block[{bx}][{by}] Sea4.ff9mesh"
            W.M.write_ff9mesh(out, sp)
            staged[(bx, by, "Sea4")] = sp
            sea_records[(bx, by, "Sea4")] = records
    world_full = W.load_world(part_src=dict(staged))
    from vcorner_sea_cut import verify as sea_verify
    g_sea = sea_verify(world_t, world_full, sea_records) if sea_records else True

    print("\n=== THE HUG GATES ===")
    south = [(377.5, -503.0), (377.2, -505.5), (377.0, -507.0)]
    r1 = hug(world_full, south, math.pi, math.radians(22.5), lambda x, z: z < -516.5)
    r2 = hug(world_full, south, math.pi, math.radians(45.0), lambda x, z: z < -516.5)
    north = [(381.5, -517.5), (381.0, -518.5)]
    r3 = hug(world_full, north, 0.0, math.radians(22.5), lambda x, z: z > -507.0)
    ctrl = hug(world_full, [(446.5, -496.0)], math.pi, math.radians(-22.5),
               lambda x, z: z < -516.0)
    for tag, rr in (("south+22.5", r1), ("south+45 (report)", r2),
                    ("north+22.5", r3), ("control east", ctrl)):
        print(f"   {tag}:")
        for (sx, sz, res, stalls) in rr:
            print(f"      ({sx:6.1f},{sz:7.1f}): {res}  stalls={stalls}")
    g_hug = (all(r[2].startswith("PASS") for r in r1)
             and all(r[2].startswith("PASS") for r in r3)
             and all(r[2].startswith("PASS") for r in ctrl))

    print("\n=== walk gates ===")
    ev, hard, ringy = drive_walkers(world_full, "STAGED fairing")
    own0 = [e for e in ev if e["own"] == 0]
    g_own0 = len(own0) == 0
    tl, cl, cells_l = static_map(world_base, "BASELINE (identity)")
    ts, cs, cells_s = static_map(world_full, "STAGED (identity)")
    bx0, bx1, bz0, bz1 = CHANGED_BBOX
    diff_out = 0
    for kk in set(cells_l) | set(cells_s):
        if cells_l.get(kk) != cells_s.get(kk):
            x = 368.0 + kk[0] * 0.25
            z = -516.0 + kk[1] * 0.25
            if not (bx0 <= x <= bx1 and bz0 <= z <= bz1):
                diff_out += 1
    g_stat = diff_out == 0 and len(ts) == 0
    print(f"   cold-map diffs outside the changed bbox: {diff_out} "
          f"({'PASS' if g_stat else 'FAIL'}); staged all-stall={len(ts)}")

    gates = dict(g_coverage=g_cov, g_sea_increment=g_sea, g_hug=g_hug,
                 g_no_own0=g_own0, g_statics=g_stat)
    print("\n=== STAGE-1 GATES ===")
    for k, v in gates.items():
        print(f"   {k}: {'PASS' if v else 'FAIL'}")
    json.dump(dict(gates=gates,
                   staged={f"{k[0]},{k[1]},{k[2]}": str(v) for k, v in staged.items()}),
              open(OUTD / "gates_stage1.json", "w"), indent=1)


def load_staged_src():
    src = {}
    for (bx, by) in BLOCKS:
        for part in ("Terrain", "Sea4"):
            sp = OUTD / f"Block[{bx}][{by}] {part}.ff9mesh"
            if sp.is_file():
                src[(bx, by, part)] = sp
    return src


def stage2():
    print("loading STAGED world for the bench-wide latent sweep ...")
    world = W.load_world(part_src=load_staged_src())
    hard_c, poisonable, _cl = sweep(world, "STAGED fairing")
    hard_f = refine(world, poisonable, "STAGED fairing")
    g = len(hard_c) == 0 and len(hard_f) == 0
    print(f"\ng_latent = 0 bench-wide: {'PASS' if g else 'FAIL'}")
    json.dump(dict(g_latent_zero=g), open(OUTD / "gates_stage2.json", "w"), indent=1)


def deploy():
    g1 = json.load(open(OUTD / "gates_stage1.json"))
    g2 = json.load(open(OUTD / "gates_stage2.json"))
    assert all(g1["gates"].values()) and g2["g_latent_zero"], \
        f"gates not green: {g1['gates']} {g2} -- NO DEPLOY"
    src = load_staged_src()
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    lines = ["import shutil"]
    for (bx, by, part), sp in sorted(src.items()):
        lp = live_path(bx, by, part)
        bk = BACKUPS / f"{lp.name}.r{by}.{ts}"
        shutil.copy2(lp, bk)
        shutil.copy2(sp, lp)
        lines.append(f"shutil.copy2(r'{bk}', r'{lp}')")
        print(f"DEPLOYED {lp.name} (r{by})   backup: {bk.name}")
    lines.append("print('reverted the shore-fairing deploy (all files)')")
    (HERE / "revert_vcorner_crest.py").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"revert: {HERE / 'revert_vcorner_crest.py'}")
    world = W.load_world()
    r = hug(world, [(377.5, -503.0), (377.0, -507.0)], math.pi, math.radians(22.5),
            lambda x, z: z < -516.5)
    ev, hard, ringy = drive_walkers(world, "LIVE post-deploy")
    own0 = [e for e in ev if e["own"] == 0]
    print("post-deploy hug:", r)
    print(f"post-deploy own-ring-0 stalls: {len(own0)} ({'PASS' if not own0 else 'FAIL'})")


if __name__ == "__main__":
    if "--deploy" in sys.argv:
        deploy()
    elif "--stage2" in sys.argv:
        stage2()
    else:
        stage1()
