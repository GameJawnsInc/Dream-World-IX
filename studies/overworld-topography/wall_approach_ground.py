"""THE APPROACH-GROUND LAW -- what stock's GROUND does outward from a wall foot (S5).

Registered in studies/path-d-new-world/GROUND-JUNCTION-SYNTHESIS.md S5. The structural
fact under test: the (15,14) donor mesa's ground-weld line has 4.4u of relief (y 3.0 ->
7.4), so seating it on a FLAT bench at LOWLAND 3.2 admits only BURY (cut the donor's
transitional band away -> "mismatched faces") or LIFT (raise bench grass to the weld line
-> "raised-grass cliff" / "the hill still isn't fixed"). Both have failed in game. This
instrument measures what stock actually puts under and around a wall foot:

  A1 WELD RELIEF -- max-min y of every wall component's ground-weld (foot) line, and
     whether that relief is a PLANE (a regional tilt the wall stands on) or scatter.
     The (15,14) donor is labelled in every distribution.
  A2 OUTWARD SLOPE PROFILE -- from each foot station, march the ground plan-outward in
     2u steps to 64u sampling the true ground surface; slope by distance band
     (0-4 / 4-8 / 8-16 / 16-32 / 32-64u), median + spread.
  A3 RETURN TO LOWLAND -- distance at which the profile first reaches its component's
     local lowland (p10 of its own 64u-radius neighbourhood ground) and the share of
     components that ever find a FLAT plane (a >=16u run with <=1.0u of y range) at all.
     A3b THE HOSTING TEST -- the height SPAN of the ground inside a disc of radius
     8/16/32/50.6u around the foot (50.6u = the bench island's own grass reach), by two
     independent samplers. A3c how far out the HIGH side stays elevated.
  A4 MOUND vs REGIONAL SLOPE -- the discriminant is TILT INHERITANCE: across a feature's
     stations, compare the relief of the weld line with the relief of the ground at a
     fixed radius d (8/16/32u) plus their correlation. ratio ~1 means the weld's relief is
     the region's own field sampled at the foot (REGIONAL); ratio <=0.25 means the far
     ground is flat while the weld varies, i.e. the relief is LOCAL to the foot -- a
     pedestal/MOUND, which is what LIFT builds. BERM = a local maximum ring outward of
     the foot. Excess p10/p90 measure whether the rise is all-round or one-sided.
  A5 RELIEF vs EXTENT -- least-squares fit of approach radius on weld relief: does more
     weld relief demand more ground radius, and how much per u?

Population/enumeration is VERBATIM from the five prior wall studies (rock_wall_rim.py /
rock_wall_base.py / rock_wall_massing.py): X.list_blocks(disc=1), 49-rock components
seeded by a 49|plateau crest edge, kept at y-span >= 6u and >= 12 tris, and measured
PER BLOCK -- a cross-block union-find merge is computed and REPORTED but not used as the
unit, because disc-1's 49-rock is one connected sheet (62 per-block components collapse
to 4 merged features, one of them 12.4k tris spanning 692u: a regional quantity, not a
wall's). The ground surface sampler is global (all 260 disc-1 blocks, plan point -> top
ground y by barycentric test) so a profile may march across block borders, and it excludes
the UPPER altitude world (plateau grass + high forest = the wall's own top surface).

DECLARED LIMITS (read before quoting a number):
  * stations march until the ground sheet ENDS (median reach 12u -- 690/936 stations stop
    at rock), so every statistic past ~16u is computed on the surviving long-reach
    subsample (n falls 45 -> 33 -> 19 -> 11 -> 8 features at 8/16/32/48u). The median
    profile's rise between 16u and 24u is that survivorship, not a berm.
  * the neighbourhood GRID sampler is 4u cell-centre: ground detail finer than one cell at
    the immediate foot is under-read (e.g. (15,12) welds over 5.0u while its grid disc
    spans 0.75u). The RAY sampler is exact-surface but truncated by the march reach, so it
    understates spread at R=32/50.6. Use grid for large R, ray for the near-foot band.
  * the unit is a per-block component; a wall crossing a block frame is measured twice and
    each half's weld line is cut by the frame. Every one of the 45 is frame-touching.
  * the "bench round 8" curve in the render is the ARITHMETIC of the registration's own
    description (4u lift, 24u falloff), NOT a measurement of the deployed Disc9 bytes.

Read-only against stock disc-1. Nothing is written outside out/.
Artifacts -> out/wall_approach_ground.json + out/approach_profiles.png
Regenerate: py -X utf8 wall_approach_ground.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402

PLATEAU = {10, 11, 12}
ROCKY = {49, 7, 62, 58}                                     # wall/lip rock -- never "approach ground"
FOREST = {36, 37}
# THE TERRACE LAW says walkable land lives in two altitude worlds (lowland 2-8u, plateau
# 26-32u). The APPROACH ground is the one the foot stands on, so the wall's own TOP surface
# (plateau grass + the high forest that grows on it) is excluded from the ground field --
# otherwise a 26u plateau top 8u inland of the crest reads as "ground near the foot".
UPPER = PLATEAU | {36}
CELL = 4.0
STEP = 2.0                                                  # march step, u
DMAX = 64.0
BANDS = ((0.0, 4.0), (4.0, 8.0), (8.0, 16.0), (16.0, 32.0), (32.0, 64.0))
DONOR_BLK = (15, 14)
OUT = Path(__file__).with_name("out") / "wall_approach_ground.json"
PNG = Path(__file__).with_name("out") / "approach_profiles.png"
kk = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))   # noqa: E731
fk = lambda p: (round(p[0], 2), round(p[1], 2), round(p[2], 2))   # noqa: E731 -- frame weld key


# ============================================================ pass 1: read the whole map
ground_tris = []                                            # (x0,z0, e1x,e1z, e2x,e2z, det, y0,y1,y2, topo)
rock_cells = set()                                          # plan cells holding rocky tris
upper_cells = set()                                         # plan cells holding UPPER-world ground
gbucket = defaultdict(list)                                 # plan cell -> ground tri ids
blocks = X.list_blocks(disc=1)
per_block = {}                                              # (bx,by) -> component payload
n_read = n_fail = 0
topo_seen = Counter()

for (bx, by) in blocks:
    try:
        bm = X.read_block(bx, by, disc=1, part="terrain")
    except Exception:                                       # noqa: BLE001
        n_fail += 1
        continue
    n_read += 1
    V, T = bm.verts, bm.tangents
    ox, oz = 64.0 * bx, -64.0 * by
    ntri = len(bm.flat_index) // 3
    tri_idx = [bm.flat_index[3 * t:3 * t + 3] for t in range(ntri)]
    topo = [X.decode_id(int(round(T[idx[0]][0])))["topograph"] for idx in tri_idx]
    topo_seen.update(topo)
    W = [(V[i][0] + ox, V[i][1], V[i][2] + oz) for i in range(len(V))]

    for t, idx in enumerate(tri_idx):
        a, b, c = (W[idx[0]], W[idx[1]], W[idx[2]])
        if topo[t] in ROCKY:
            for p in (a, b, c):
                rock_cells.add((math.floor(p[0] / CELL), math.floor(p[2] / CELL)))
            continue
        if topo[t] in UPPER:
            for p in (a, b, c):
                upper_cells.add((math.floor(p[0] / CELL), math.floor(p[2] / CELL)))
            continue
        e1x, e1z = b[0] - a[0], b[2] - a[2]
        e2x, e2z = c[0] - a[0], c[2] - a[2]
        det = e1x * e2z - e2x * e1z
        if abs(det) < 1e-9:                                 # plan-degenerate (a vertical curtain)
            continue
        gid = len(ground_tris)
        ground_tris.append((a[0], a[2], e1x, e1z, e2x, e2z, det,
                            a[1], b[1], c[1], topo[t]))
        xs = (a[0], b[0], c[0])
        zs = (a[2], b[2], c[2])
        for ci in range(math.floor(min(xs) / CELL), math.floor(max(xs) / CELL) + 1):
            for cj in range(math.floor(min(zs) / CELL), math.floor(max(zs) / CELL) + 1):
                gbucket[(ci, cj)].append(gid)

    # ---- wall components (verbatim extraction from the prior wall studies) --------------
    if not any(t in PLATEAU for t in topo):
        continue
    edge_tris = defaultdict(list)
    for t, idx in enumerate(tri_idx):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_tris[tuple(sorted((kk(V[idx[a]]), kk(V[idx[b]]))))].append(t)
    crest49 = set()
    for e, ts in edge_tris.items():
        if len(ts) == 2:
            pair = {topo[ts[0]], topo[ts[1]]}
            if 49 in pair and pair & PLATEAU:
                crest49.add(ts[0] if topo[ts[0]] == 49 else ts[1])
    adj49 = defaultdict(set)
    for e, ts in edge_tris.items():
        r = [t for t in ts if topo[t] == 49]
        for i in range(len(r)):
            for j in range(i + 1, len(r)):
                adj49[r[i]].add(r[j])
                adj49[r[j]].add(r[i])
    comp_of, seen = {}, set()
    for s in crest49:
        if s in seen:
            continue
        comp, st = {s}, [s]
        while st:
            t = st.pop()
            for t2 in adj49[t]:
                if t2 not in comp:
                    comp.add(t2)
                    st.append(t2)
        seen |= comp
        for t in comp:
            comp_of[t] = s
    if not comp_of:
        continue

    comp_tris = defaultdict(list)
    for t, r in comp_of.items():
        comp_tris[r].append(t)
    keep = {}
    for root, ts in comp_tris.items():
        ys = [V[i][1] for t in ts for i in tri_idx[t]]
        if max(ys) - min(ys) >= 6.0 and len(ts) >= 12:
            keep[root] = ts
    if not keep:
        continue

    # foot edges: exactly one wall tri, the other side walkable ground
    foot = defaultdict(list)                                # root -> [(pA, pB, ground_topo)]
    for e, ts in edge_tris.items():
        w = [t for t in ts if t in comp_of and comp_of[t] in keep]
        if len(w) != 1:
            continue
        o = [t for t in ts if t not in comp_of]
        if not o or any(topo[t] in PLATEAU or topo[t] in ROCKY for t in o):
            continue
        pA = (e[0][0] + ox, e[0][1], e[0][2] + oz)
        pB = (e[1][0] + ox, e[1][1], e[1][2] + oz)
        gt = o[0]
        gc = (float(np.mean([V[i][0] for i in tri_idx[gt]])) + ox,
              float(np.mean([V[i][2] for i in tri_idx[gt]])) + oz)
        foot[comp_of[w[0]]].append((pA, pB, topo[gt], gc))

    # verts on the block frame (for the cross-block component merge)
    frame = defaultdict(set)
    for root, ts in keep.items():
        for t in ts:
            for i in tri_idx[t]:
                x, y, z = V[i]
                if min(abs(x), abs(x - 64.0)) < 0.05 or min(abs(z), abs(z + 64.0)) < 0.05:
                    frame[root].add(fk((x + ox, y, z + oz)))
    per_block[(bx, by)] = dict(keep={r: len(ts) for r, ts in keep.items()},
                               ys={r: (min(V[i][1] for t in ts for i in tri_idx[t]),
                                       max(V[i][1] for t in ts for i in tri_idx[t]))
                                   for r, ts in keep.items()},
                               foot=foot, frame=frame)

print(f"read {n_read}/{len(blocks)} disc-1 blocks ({n_fail} unreadable); "
      f"{len(ground_tris)} plan-valid LOWER-world ground tris bucketed, "
      f"{len(rock_cells)} rocky cells, {len(upper_cells)} upper-world cells")


# ============================================================ the ground surface sampler
def ground_y(x, z):
    """Top ground y at plan (x, z), or None where no walkable ground sheet exists."""
    best = None
    for gid in gbucket.get((math.floor(x / CELL), math.floor(z / CELL)), ()):
        x0, z0, e1x, e1z, e2x, e2z, det, y0, y1, y2, _tp = ground_tris[gid]
        px, pz = x - x0, z - z0
        u = (px * e2z - e2x * pz) / det
        if u < -1e-6:
            continue
        v = (e1x * pz - px * e1z) / det
        if v < -1e-6 or u + v > 1.0 + 1e-6:
            continue
        y = y0 + u * (y1 - y0) + v * (y2 - y0)
        if best is None or y > best:
            best = y
    return best


def stop_reason(x, z):
    c = (math.floor(x / CELL), math.floor(z / CELL))
    return "rock" if c in rock_cells else ("upper" if c in upper_cells else "void")


# ============================================================ cross-block component merge
parent = {}


def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a


def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb


by_frame = defaultdict(list)
for blk, pay in per_block.items():
    for root in pay["keep"]:
        parent[(blk, root)] = (blk, root)
        for key in pay["frame"][root]:
            by_frame[key].append((blk, root))
for key, owners in by_frame.items():
    for o in owners[1:]:
        union(owners[0], o)

groups = defaultdict(list)
for cid in parent:
    groups[find(cid)].append(cid)
print(f"components: {len(parent)} per-block -> {len(groups)} merged features")


# ============================================================ per-feature measurement
def pct(a, q):
    return round(float(np.percentile(a, q)), 2) if len(a) else None


def plane_fit(pts):
    """y = a*x + b*z + c over (x,y,z) points -> (grad_deg, dir_deg, resid_std, r2)."""
    if len(pts) < 4:
        return None
    A = np.array([[p[0], p[2], 1.0] for p in pts])
    y = np.array([p[1] for p in pts])
    if np.std(A[:, 0]) < 1e-6 and np.std(A[:, 1]) < 1e-6:
        return None
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ sol
    g = math.hypot(sol[0], sol[1])
    var = float(np.var(y))
    return dict(grad=round(math.degrees(math.atan(g)), 2),
                gvec=(float(sol[0]), float(sol[1])),
                dir=round(math.degrees(math.atan2(sol[1], sol[0])), 1),
                resid=round(float(np.std(res)), 2),
                r2=round(1.0 - float(np.var(res)) / var, 3) if var > 1e-9 else None)


units = []                                                  # the studied unit = a per-block comp
for blk in sorted(per_block):
    pay = per_block[blk]
    for root in sorted(pay["keep"]):
        if len(pay["foot"][root]) < 4:
            continue
        units.append((blk, root))

feats = []
for (blk, root) in units:
    pay = per_block[blk]
    fedges = pay["foot"][root]
    tri_n = pay["keep"][root]
    ylo, yhi = pay["ys"][root]
    blks = [blk]
    truncated = bool(pay["frame"][root])
    is_donor = (blk == DONOR_BLK
                and tri_n == max(per_block[DONOR_BLK]["keep"].values()))

    # ---- A1: the weld line ---------------------------------------------------------------
    fv, fv_nf = {}, {}                                      # foot verts (all / non-forest)
    for pA, pB, gt, gc in fedges:
        for p in (pA, pB):
            fv[fk(p)] = p
            if gt not in FOREST:
                fv_nf[fk(p)] = p
    fpts = list(fv.values())                                # PRIMARY = the whole weld line
    ys = [p[1] for p in fpts]
    relief = round(max(ys) - min(ys), 2)
    nfy = [p[1] for p in fv_nf.values()]
    relief_nf = round(max(nfy) - min(nfy), 2) if len(nfy) >= 2 else None
    wplane = plane_fit(fpts)

    # ---- stations: deduped foot verts with an outward plan direction ---------------------
    outdir = defaultdict(list)
    for pA, pB, gt, gc in fedges:
        for p in (pA, pB):
            outdir[fk(p)].append(gc)
    stations = []
    for key, p in sorted(fv.items()):
        if any(math.hypot(p[0] - s["p"][0], p[2] - s["p"][2]) < 3.5 for s in stations):
            continue
        gs = outdir[key]
        dx = float(np.mean([g[0] for g in gs])) - p[0]
        dz = float(np.mean([g[1] for g in gs])) - p[2]
        L = math.hypot(dx, dz)
        if L < 1e-3:
            continue
        stations.append(dict(p=p, d=(dx / L, dz / L)))
        if len(stations) >= 80:
            break
    if len(stations) < 3:
        continue

    # ---- A2: march outward ---------------------------------------------------------------
    prof, reaches, stops = [], [], Counter()
    for s in stations:
        (px, py, pz), (dx, dz) = s["p"], s["d"]
        ysamp = {0.0: py}
        d = STEP
        stop = "full"
        while d <= DMAX + 1e-9:
            qx, qz = px + dx * d, pz + dz * d
            gy = ground_y(qx, qz)
            if gy is None:
                stop = stop_reason(qx, qz)
                break
            ysamp[d] = gy
            d += STEP
        reaches.append(round(d - STEP, 1))
        stops[stop] += 1
        prof.append(ysamp)

    allsamp = [y for ps in prof for dd, y in ps.items() if dd > 0]
    if len(allsamp) < 20:
        continue

    # ---- the NEIGHBOURHOOD ground field (independent of the marching): a 4u grid over the
    #      footprint + 64u, keeping points within 64u of a foot vert. Gives the local lowland
    #      AND how flat the region is at all.
    fxs = [p[0] for p in fv.values()]
    fzs = [p[2] for p in fv.values()]
    nb = []
    gx0, gx1 = math.floor((min(fxs) - 64.0) / CELL), math.ceil((max(fxs) + 64.0) / CELL)
    gz0, gz1 = math.floor((min(fzs) - 64.0) / CELL), math.ceil((max(fzs) + 64.0) / CELL)
    fvl = list(fv.values())
    for gi in range(gx0, gx1 + 1):
        for gj in range(gz0, gz1 + 1):
            qx, qz = (gi + 0.5) * CELL, (gj + 0.5) * CELL
            dmin = min(math.hypot(qx - p[0], qz - p[2]) for p in fvl)
            if dmin > 64.0:
                continue
            gy = ground_y(qx, qz)
            if gy is not None:
                nb.append((dmin, gy))
    if len(nb) < 20:
        continue
    nby = [q[1] for q in nb]
    lowland = float(np.percentile(nby, 10))
    nb_flat = round(sum(1 for y in nby if y <= lowland + 0.5) / len(nby), 3)
    # THE HOSTING TEST: how much height does the ground SPAN inside a disc of radius R
    # around this wall's foot? (R=50.6 is the bench island's own grass reach.)
    spread = {}
    for R in (8.0, 16.0, 32.0, 50.6):
        ins = [y for d, y in nb if d <= R]
        spread[f"{R:g}"] = dict(n=len(ins),
                                span=round(max(ins) - min(ins), 2) if len(ins) >= 8 else None,
                                std=round(float(np.std(ins)), 2) if len(ins) >= 8 else None)

    band_slope = {f"{a:g}-{b:g}": [] for a, b in BANDS}
    excess, ret_d, flat_d, berm, berm_h = [], [], [], 0, []
    for ps in prof:
        for a, b in BANDS:
            if a in ps and b in ps:
                band_slope[f"{a:g}-{b:g}"].append(
                    round(math.degrees(math.atan((ps[a] - ps[b]) / (b - a))), 2))
        y0 = ps[0.0]
        excess.append(round(y0 - lowland, 2))
        ds = sorted(ps)
        hit = None
        for dd in ds:
            if dd > 0 and ps[dd] <= lowland + 0.5:
                fwd = [ps[e] for e in ds if dd <= e <= dd + 8.0]
                if max(fwd) <= lowland + 1.0:
                    hit = dd
                    break
        ret_d.append(hit)
        fl = None
        for dd in ds:
            win = [ps[e] for e in ds if dd <= e <= dd + 16.0]
            if len(win) >= 8 and max(win) - min(win) <= 1.0:
                fl = dd
                break
        flat_d.append(fl)
        out = [(dd, ps[dd]) for dd in ds if dd >= 4.0]
        if out:
            mx = max(out, key=lambda q: q[1])
            after = [y for dd, y in out if dd > mx[0]]
            if mx[1] - y0 >= 1.0 and after and mx[1] - min(after) >= 1.0:
                berm += 1
                berm_h.append(round(mx[1] - y0, 2))

    got = [d for d in ret_d if d is not None]

    # ---- A4 THE DISCRIMINANT: TILT INHERITANCE. Does the ground OUT AT RADIUS d carry the
    #      same relief, in the same arrangement, as the weld line itself? If yes the weld's
    #      relief is the region's own tilt (REGIONAL). If the far ground is flat while the
    #      weld varies, the relief is local to the foot (a PEDESTAL / MOUND -- our bench).
    inherit = {}
    for dd in (8.0, 16.0, 32.0):
        pairs = [(ps[0.0], ps[dd]) for ps in prof if dd in ps]
        if len(pairs) < 6:
            inherit[f"{dd:g}"] = None
            continue
        w = np.array([q[0] for q in pairs])
        far = np.array([q[1] for q in pairs])
        rw = float(w.max() - w.min())
        rf = float(far.max() - far.min())
        r = (float(np.corrcoef(w, far)[0, 1])
             if np.std(w) > 1e-6 and np.std(far) > 1e-6 else None)
        inherit[f"{dd:g}"] = dict(n=len(pairs), weld_relief=round(rw, 2),
                                  far_relief=round(rf, 2),
                                  ratio=round(rf / rw, 3) if rw > 0.3 else None,
                                  r=round(r, 3) if r is not None else None)

    # HIGH-SIDE vs LOW-SIDE profiles: the high stations are the ones a flat destination
    # must fake, so they are reported separately.
    exq = float(np.percentile(excess, 75)) if len(excess) >= 4 else 1e9
    hi_prof = [ps for ps, e in zip(prof, excess) if e >= exq]
    lo_prof = [ps for ps, e in zip(prof, excess) if e <= float(np.percentile(excess, 25))]

    def med_prof(pl):
        return {f"{d:g}": round(float(np.median([ps[d] for ps in pl if d in ps])) - lowland, 2)
                for d in [0.0] + [STEP * k for k in range(1, int(DMAX / STEP) + 1)]
                if sum(1 for ps in pl if d in ps) >= max(2, len(pl) // 3)}

    # the same hosting test measured on the EXACT ray samples (the nb grid is 4u cell-centre
    # sampling and can under-read ground detail within one cell of the foot)
    spread_ray = {}
    for R in (8.0, 16.0, 32.0, 50.6):
        ins = [y for ps in prof for dd, y in ps.items() if dd <= R]
        spread_ray[f"{R:g}"] = round(max(ins) - min(ins), 2) if len(ins) >= 8 else None
    # how far out does the HIGH side stay elevated? (what a flat destination must fake)
    hi_at = {}
    for dd in (8.0, 16.0, 32.0, 48.0, 64.0):
        v = [ps[dd] - lowland for ps in hi_prof if dd in ps]
        hi_at[f"{dd:g}"] = round(float(np.median(v)), 2) if len(v) >= 2 else None

    ex_p10, ex_p90 = pct(excess, 10), pct(excess, 90)
    med_ret = pct(got, 50)
    i16 = inherit.get("16") or inherit.get("8")
    ratio16 = i16["ratio"] if i16 else None
    r16 = i16["r"] if i16 else None
    mound = (ratio16 is not None and ratio16 <= 0.25
             and relief >= 1.5 and med_ret is not None and med_ret <= 16.0)
    regional = (ratio16 is not None and ratio16 >= 0.5
                and (r16 is None or r16 >= 0.4))
    feats.append(dict(
        blocks=sorted(set(blks)), donor=bool(is_donor), tris=tri_n, truncated=truncated,
        height=round(yhi - ylo, 1), foot_verts=len(fv), stations=len(stations),
        extent=[round(max(fxs) - min(fxs), 1), round(max(fzs) - min(fzs), 1)],
        relief=relief, relief_no_forest=relief_nf,
        weld_y=[round(min(ys), 2), round(max(ys), 2)],
        weld_plane=wplane, inherit=inherit, spread=spread, spread_ray=spread_ray,
        hi_at=hi_at,
        compact=bool(max(fxs) - min(fxs) < 63.9 and max(fzs) - min(fzs) < 63.9
                     and tri_n < 700),
        lowland=round(lowland, 2), nb_flat_share=nb_flat, nb_pts=len(nb),
        excess=dict(p10=ex_p10, p50=pct(excess, 50), p90=ex_p90),
        band_slope={k: dict(n=len(v), p25=pct(v, 25), med=pct(v, 50), p75=pct(v, 75))
                    for k, v in band_slope.items()},
        reach=dict(med=pct(reaches, 50), p10=pct(reaches, 10)), stops=dict(stops),
        return_dist=dict(med=med_ret, p90=pct(got, 90),
                         share=round(len(got) / len(ret_d), 3)),
        flat=dict(med=pct([d for d in flat_d if d is not None], 50),
                  share=round(sum(1 for d in flat_d if d is not None) / len(flat_d), 3)),
        berm=dict(n=berm, share=round(berm / len(prof), 3), med_h=pct(berm_h, 50)),
        klass="MOUND" if mound else ("REGIONAL" if regional else "MIXED"),
        profile_med=med_prof(prof), profile_hi=med_prof(hi_prof),
        profile_lo=med_prof(lo_prof),
    ))

donor = next((f for f in feats if f["donor"]), None)
print(f"measured {len(feats)} features with >=4 foot edges and >=3 stations; "
      f"donor {DONOR_BLK} {'FOUND' if donor else 'MISSING'}")


# ============================================================ distributions
def where(vals, x):
    return round(100.0 * sum(1 for v in vals if v <= x) / max(1, len(vals)), 1)


rel = [f["relief"] for f in feats]
whole = [f for f in feats if f["compact"]]
relw = [f["relief"] for f in whole]
print("\n== A1 WELD-LINE RELIEF (ground-weld max-min y, per wall component) ==")
print(f"   ALL n={len(rel)}  min {min(rel)}  p10 {pct(rel, 10)}  p25 {pct(rel, 25)}  "
      f"MED {pct(rel, 50)}  p75 {pct(rel, 75)}  p90 {pct(rel, 90)}  max {max(rel)}")
print(f"   COMPACT (extent < 64u both axes, < 700 tris -- the DONOR's own size class) "
      f"n={len(relw)}  p10 {pct(relw, 10)}  p25 {pct(relw, 25)}  MED {pct(relw, 50)}  "
      f"p75 {pct(relw, 75)}  p90 {pct(relw, 90)}  max {max(relw) if relw else None}")
print(f"   (every one of the {len(feats)} components has wall verts on a block frame: the "
      f"49-rock of the continent is ONE connected sheet -- see the limits note)")
if donor:
    print(f"   DONOR (15,14): relief {donor['relief']}u (excluding forest-abutted edges "
          f"{donor['relief_no_forest']}u) -> percentile {where(rel, donor['relief'])}% of ALL, "
          f"{where(relw, donor['relief'])}% of COMPACT")
for lab, pop in (("ALL    ", feats), ("COMPACT", whole)):
    pl = [f["weld_plane"]["r2"] for f in pop
          if f["weld_plane"] and f["weld_plane"]["r2"] is not None]
    gd = [f["weld_plane"]["grad"] for f in pop if f["weld_plane"]]
    rs = [f["weld_plane"]["resid"] for f in pop if f["weld_plane"]]
    print(f"   {lab} weld line as a PLANE: r2 med {pct(pl, 50)} (p25 {pct(pl, 25)} "
          f"p75 {pct(pl, 75)}), resid med {pct(rs, 50)}u; plane TILT med {pct(gd, 50)} deg "
          f"(p75 {pct(gd, 75)} p90 {pct(gd, 90)})")
if donor and donor["weld_plane"]:
    w = donor["weld_plane"]
    print(f"   DONOR weld plane: tilt {w['grad']} deg, r2 {w['r2']}, resid {w['resid']}u, "
          f"dir {w['dir']} deg")

print("\n== A2 OUTWARD SLOPE by distance band (deg, + = ground DESCENDS outward) ==")
for a, b in BANDS:
    k = f"{a:g}-{b:g}"
    v = [f["band_slope"][k]["med"] for f in feats if f["band_slope"][k]["med"] is not None]
    ns = sum(f["band_slope"][k]["n"] for f in feats)
    print(f"   {k:>7}u  stations {ns:5d}  feature-median slope: p25 {pct(v, 25)}  "
          f"MED {pct(v, 50)}  p75 {pct(v, 75)}  p90 {pct(v, 90)}"
          + (f"   | DONOR {donor['band_slope'][k]['med']}" if donor else ""))

print("\n== A3 RETURN TO LOWLAND / FLATNESS ==")
rd = [f["return_dist"]["med"] for f in feats if f["return_dist"]["med"] is not None]
sh = [f["return_dist"]["share"] for f in feats]
fs = [f["flat"]["share"] for f in feats]
print(f"   median return distance per feature: p25 {pct(rd, 25)} MED {pct(rd, 50)} "
      f"p75 {pct(rd, 75)} p90 {pct(rd, 90)}u (n={len(rd)} features)")
print(f"   station share reaching lowland within 64u: med {pct(sh, 50)}; "
      f"features where >=50% of stations reach it: "
      f"{sum(1 for f in feats if f['return_dist']['share'] >= 0.5)}/{len(feats)}")
print(f"   station share finding a FLAT run (>=16u, <=1.0u range): med {pct(fs, 50)}; "
      f"features with >=50%: {sum(1 for f in feats if f['flat']['share'] >= 0.5)}/{len(feats)}")
print(f"   march reach: med {pct([f['reach']['med'] for f in feats], 50)}u; stop reasons "
      f"{dict(sum((Counter(f['stops']) for f in feats), Counter()))}")
if donor:
    print(f"   DONOR: return med {donor['return_dist']['med']} (share "
          f"{donor['return_dist']['share']}), flat share {donor['flat']['share']}, "
          f"reach med {donor['reach']['med']}u, lowland {donor['lowland']}")

print("\n== A4 MOUND vs REGIONAL SLOPE -- THE TILT-INHERITANCE DISCRIMINANT ==")
kl = Counter(f["klass"] for f in feats)
print(f"   classes: {dict(kl)}   (MOUND = far ground carries <=25% of the weld's relief "
      f"and returns to lowland within 16u; REGIONAL = far ground carries >=50%, r>=0.4)")
for dd in ("8", "16", "32"):
    iv = [f["inherit"][dd] for f in feats if f["inherit"].get(dd)]
    ra = [q["ratio"] for q in iv if q["ratio"] is not None]
    rr = [q["r"] for q in iv if q["r"] is not None]
    print(f"   at {dd:>2}u out: n={len(ra)} features; relief RATIO (far/weld) p25 "
          f"{pct(ra, 25)} MED {pct(ra, 50)} p75 {pct(ra, 75)}; corr(weld, far) MED "
          f"{pct(rr, 50)}; ratio>=0.5 in {sum(1 for q in ra if q >= 0.5)}/{len(ra)}"
          + (f"   | DONOR ratio {donor['inherit'][dd]['ratio']} r "
             f"{donor['inherit'][dd]['r']}"
             if donor and donor["inherit"].get(dd) else ""))
exp10 = [f["excess"]["p10"] for f in feats]
exp90 = [f["excess"]["p90"] for f in feats]
print(f"   weld EXCESS over local lowland: p10-of-stations med {pct(exp10, 50)}u "
      f"(the all-sides floor), p90-of-stations med {pct(exp90, 50)}u (the high side); "
      f"one-sided (p10<=0.75) in {sum(1 for f in feats if f['excess']['p10'] <= 0.75)}"
      f"/{len(feats)}")
print(f"   BERM (a local max ring outward of the foot): station share med "
      f"{pct([f['berm']['share'] for f in feats], 50)}; features with >=25% berm stations: "
      f"{sum(1 for f in feats if f['berm']['share'] >= 0.25)}/{len(feats)}")
print(f"   neighbourhood FLATNESS (share of the 64u-radius ground within 0.5u of lowland): "
      f"med {pct([f['nb_flat_share'] for f in feats], 50)}")
mb = Counter()
for f in feats:
    i16 = f["inherit"].get("16") or f["inherit"].get("8")
    r = i16["ratio"] if i16 else None
    mb["unmeasurable" if r is None else
       ("<=0.25 (pedestal)" if r <= 0.25 else
        ("0.25-0.5" if r < 0.5 else ">=0.5 (inherited)"))] += 1
print(f"   ratio buckets at 16u (fallback 8u): {dict(mb)}")

print("\n== A3b THE HOSTING TEST -- height SPAN of the ground inside a disc of radius R "
      "around the foot ==")
print("   (R=50.6u is the bench island's own grass reach; two independent samplers)")
for R in ("8", "16", "32", "50.6"):
    sp = [f["spread"][R]["span"] for f in feats if f["spread"][R]["span"] is not None]
    spc = [f["spread"][R]["span"] for f in whole if f["spread"][R]["span"] is not None]
    ry = [f["spread_ray"][R] for f in feats if f["spread_ray"][R] is not None]
    print(f"   R={R:>4}u  GRID n={len(sp):3d} min {min(sp):5} p10 {pct(sp, 10):5} "
          f"MED {pct(sp, 50):5} (compact {pct(spc, 50):5}) | RAY min {min(ry):5} p10 "
          f"{pct(ry, 10):5} MED {pct(ry, 50):5}"
          + (f" | DONOR grid {donor['spread'][R]['span']} ray {donor['spread_ray'][R]}"
             if donor else ""))

print("\n== A3c HOW FAR OUT THE HIGH SIDE STAYS UP (median high-side excess over lowland) ==")
for dd in ("8", "16", "32", "48", "64"):
    v = [f["hi_at"][dd] for f in feats if f["hi_at"][dd] is not None]
    print(f"   at {dd:>2}u out: n={len(v):3d}  p25 {pct(v, 25):5} MED {pct(v, 50):5} "
          f"p75 {pct(v, 75):5};  still >=1.0u up: {sum(1 for q in v if q >= 1.0)}/{len(v)}"
          + (f"   | DONOR {donor['hi_at'][dd]}" if donor else ""))
if donor:
    print(f"   DONOR: class {donor['klass']}, excess p10 {donor['excess']['p10']} / p50 "
          f"{donor['excess']['p50']} / p90 {donor['excess']['p90']}, berm share "
          f"{donor['berm']['share']}, nb-flat {donor['nb_flat_share']}")

print("\n== A5 RELIEF vs APPROACH EXTENT ==")
fit = None
for lab, key in (("median-station", "med"), ("high-side (p90)", "p90")):
    xy = [(f["relief"], f["return_dist"][key]) for f in feats
          if f["return_dist"][key] is not None]
    if len(xy) < 6:
        continue
    xa = np.array([q[0] for q in xy])
    ya = np.array([q[1] for q in xy])
    m, c = np.polyfit(xa, ya, 1)
    r = float(np.corrcoef(xa, ya)[0, 1])
    f5 = dict(which=lab, n=len(xy), slope=round(float(m), 2), intercept=round(float(c), 2),
              r=round(r, 3), pred_4u4=round(float(m * 4.4 + c), 1))
    print(f"   {lab:16s} return_dist = {f5['slope']}*relief + {f5['intercept']}  "
          f"(r={f5['r']}, n={f5['n']}) -> at 4.4u of relief: {f5['pred_4u4']}u")
    if key == "p90":
        fit = f5
hp = [f["return_dist"]["p90"] for f in feats if f["return_dist"]["p90"] is not None]
print(f"   high-side return distance overall: med {pct(hp, 50)}u p75 {pct(hp, 75)} "
      f"p90 {pct(hp, 90)}"
      + (f"   | DONOR {donor['return_dist']['p90']}u" if donor else ""))
# relief vs the wall's own plan size: is relief just (regional tilt x footprint)?
rz = [(f["relief"], max(f["extent"])) for f in feats]
if len(rz) >= 6:
    rr = float(np.corrcoef([q[0] for q in rz], [q[1] for q in rz])[0, 1])
    print(f"   corr(weld relief, footprint extent) = {round(rr, 3)}  -- relief/extent "
          f"(the implied ground tilt) med "
          f"{pct([q[0] / max(1e-6, q[1]) for q in rz], 50)} u/u")

# ---- top of the relief table, donor in place ------------------------------------------
print("\n== the relief table (top 12 + the donor) ==")
tab = sorted(feats, key=lambda f: -f["relief"])
rows = tab[:12] + ([donor] if donor and donor not in tab[:12] else [])
for f in rows:
    wp = f["weld_plane"] or {}
    i16 = f["inherit"].get("16") or {}
    print(f"   {'*DONOR*' if f['donor'] else '       '} blk {str(f['blocks'][0]):9s} "
          f"{'cut' if f['truncated'] else '   '} tris {f['tris']:5d} h {f['height']:5.1f} "
          f"ext {str(f['extent']):16s} relief {f['relief']:5.2f} tilt "
          f"{str(wp.get('grad')):>5} exc10 {str(f['excess']['p10']):>5} exc90 "
          f"{str(f['excess']['p90']):>5} ret50 {str(f['return_dist']['med']):>5} ret90 "
          f"{str(f['return_dist']['p90']):>5} inh16 {str(i16.get('ratio')):>6} {f['klass']}")


# ============================================================ the picture
W, H = 1180, 620
im = Image.new("RGB", (W, H), (20, 20, 24))
dr = ImageDraw.Draw(im)
L, R, TP, BT = 70, W - 210, 60, H - 60
YLO, YHI = -2.0, 12.0


def sx(d):
    return L + (R - L) * d / DMAX


def sy(y):
    return BT - (BT - TP) * (y - YLO) / (YHI - YLO)


for y in range(int(YLO), int(YHI) + 1, 2):
    dr.line([L, sy(y), R, sy(y)], fill=(46, 46, 54))
    dr.text((L - 30, sy(y) - 6), f"{y:+d}", fill=(140, 140, 150))
for d in range(0, int(DMAX) + 1, 8):
    dr.line([sx(d), TP, sx(d), BT], fill=(38, 38, 46))
    dr.text((sx(d) - 8, BT + 8), f"{d}", fill=(140, 140, 150))
COL = {"REGIONAL": (90, 150, 210), "MOUND": (220, 130, 70), "MIXED": (120, 120, 130)}
for f in feats:
    if f["donor"]:
        continue
    pm = sorted(((float(k), v) for k, v in f["profile_hi"].items()))
    if len(pm) < 4:
        continue
    dr.line([q for d, y in pm for q in (sx(d), sy(y))], fill=COL[f["klass"]], width=1)
if donor:
    pm = sorted(((float(k), v) for k, v in donor["profile_hi"].items()))
    dr.line([q for d, y in pm for q in (sx(d), sy(y))], fill=(255, 215, 60), width=4)
    pm = sorted(((float(k), v) for k, v in donor["profile_med"].items()))
    dr.line([q for d, y in pm for q in (sx(d), sy(y))], fill=(190, 160, 60), width=2)
# the bench build as DESCRIBED in the round-8 registration (arithmetic, not measured bytes)
bench = [(d, 4.0 * max(0.0, 1.0 - d / 24.0)) for d in range(0, 66, 2)]
dr.line([q for d, y in bench for q in (sx(d), sy(y))], fill=(230, 70, 90), width=3)
for i, (lab, col) in enumerate((
        ("REGIONAL-inherited (high side)", COL["REGIONAL"]), ("MOUND features", COL["MOUND"]),
        ("MIXED", COL["MIXED"]), ("DONOR (15,14) HIGH side", (255, 215, 60)),
        ("DONOR all-station median", (190, 160, 60)),
        ("bench round 8 (as described)", (230, 70, 90)))):
    dr.rectangle([R + 16, TP + 20 + 22 * i, R + 40, TP + 32 + 22 * i], fill=col)
    dr.text((R + 46, TP + 20 + 22 * i), lab, fill=(225, 225, 230))
for d in (24.0, 50.6):                                      # the bench's own two radii
    for yy in range(TP, BT, 8):
        dr.line([sx(d), yy, sx(d), yy + 4], fill=(120, 90, 90))
dr.text((sx(24.0) + 4, TP + 4), "bench falloff ends (24u)", fill=(200, 120, 130))
dr.text((sx(50.6) + 4, TP + 4), "bench grass reach (50.6u)", fill=(200, 120, 130))
dr.text((L, H - 26), "STOCK STAYS UP: median high-side excess 1.7u at 8u, 1.3u at 32u, "
        "1.2u at 48u -- 5 of 8 measurable features are still >=1u up at 48u. The bench "
        "returns to lowland at 24u and is flat beyond.", fill=(200, 200, 210))
dr.text((L, 18), "APPROACH GROUND -- ground height ABOVE the feature's own local lowland, "
        "marching outward from the wall foot (HIGH-SIDE stations)", fill=(235, 235, 240))
dr.text((L, 36), f"x = plan distance from the ground-weld line (u)   |   y = y - lowland "
        f"(u)   |   n={len(feats)} stock wall components, disc 1", fill=(160, 160, 170))
PNG.parent.mkdir(exist_ok=True)
im.save(PNG)
print(f"\nrender -> {PNG}")

OUT.write_text(json.dumps(dict(
    population=dict(blocks_read=n_read, blocks_listed=len(blocks),
                    ground_tris=len(ground_tris), per_block_comps=len(parent),
                    merged_features=len(groups), measured=len(feats),
                    stations=sum(f["stations"] for f in feats),
                    topo_hist=dict(topo_seen.most_common())),
    relief=dict(n=len(rel), med=pct(rel, 50), p10=pct(rel, 10), p25=pct(rel, 25),
                p75=pct(rel, 75), p90=pct(rel, 90), mx=max(rel), mn=min(rel),
                whole_n=len(relw), whole_med=pct(relw, 50), whole_p75=pct(relw, 75),
                whole_p90=pct(relw, 90),
                donor=donor["relief"] if donor else None,
                donor_pctile=where(rel, donor["relief"]) if donor else None),
    inherit_med={dd: dict(ratio=pct([f["inherit"][dd]["ratio"] for f in feats
                                     if f["inherit"].get(dd)
                                     and f["inherit"][dd]["ratio"] is not None], 50),
                          r=pct([f["inherit"][dd]["r"] for f in feats
                                 if f["inherit"].get(dd)
                                 and f["inherit"][dd]["r"] is not None], 50))
                 for dd in ("8", "16", "32")},
    return_dist_med=dict(
        med=pct([f["return_dist"]["med"] for f in feats
                 if f["return_dist"]["med"] is not None], 50),
        p90=pct([f["return_dist"]["p90"] for f in feats
                 if f["return_dist"]["p90"] is not None], 50)),
    band_slope_med={f"{a:g}-{b:g}": pct([f["band_slope"][f"{a:g}-{b:g}"]["med"] for f in feats
                                         if f["band_slope"][f"{a:g}-{b:g}"]["med"] is not None],
                                        50) for a, b in BANDS},
    classes=dict(kl), ratio_buckets=dict(mb), relief_extent_fit=fit,
    hosting_test={R: dict(all_med=pct([f["spread"][R]["span"] for f in feats
                                       if f["spread"][R]["span"] is not None], 50),
                          compact_med=pct([f["spread"][R]["span"] for f in whole
                                           if f["spread"][R]["span"] is not None], 50),
                          ray_med=pct([f["spread_ray"][R] for f in feats
                                       if f["spread_ray"][R] is not None], 50),
                          ray_min=min([f["spread_ray"][R] for f in feats
                                       if f["spread_ray"][R] is not None], default=None),
                          donor=donor["spread"][R]["span"] if donor else None,
                          donor_ray=donor["spread_ray"][R] if donor else None)
                  for R in ("8", "16", "32", "50.6")},
    high_side_excess={dd: dict(med=pct([f["hi_at"][dd] for f in feats
                                        if f["hi_at"][dd] is not None], 50),
                               n_up=sum(1 for f in feats if f["hi_at"][dd] is not None
                                        and f["hi_at"][dd] >= 1.0),
                               n=sum(1 for f in feats if f["hi_at"][dd] is not None),
                               donor=donor["hi_at"][dd] if donor else None)
                      for dd in ("8", "16", "32", "48", "64")},
    donor=donor, features=feats,
), indent=1))
print(f"json -> {OUT}")
