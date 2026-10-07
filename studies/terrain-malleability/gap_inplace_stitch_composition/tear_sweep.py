"""METHOD B -- the TEAR-CONSEQUENCE model: what a Terrain-only Y displacement (world-terrain / world-deploy's
deform_radial, smooth falloff -- mesh.py _falloff + deform_radial, applied to Terrain ONLY, terrain.py:159) does to
the stock stitch graph, and what each torn stitch costs.

Reference sweep (disc 1, folder 0_1): the 44 beach-bearing blocks (Beach1 or Beach2) and the 63 Object-bearing
blocks. Centres: every occupied 16u cell of a block's Terrain|Beach (beach blocks) or Terrain|Object (object
blocks) weld positions; the centre is the weld position nearest the cell's mean. Edits: amount in
{+1,-1,+3,-3,+6,-6} x radius {8,16,24}. For each edit:

  TORN     a stock exact weld (a Terrain vertex position shared with a non-Terrain part, same or neighbour block)
           whose Terrain side moves by |f| > 0.05u (the weld_audit tolerance; calibrate.py C3a: 0.06 flagged, 0.01
           passes). Terrain|Terrain welds never tear inside the grid (reshape displaces every in-range block with the
           same world-space weight) and stock has NO mesh in column 23 or row 19 (stitch_census.py), so the torus
           seam carries no stock stitch.
  RENDER   every torn weld is a slit of height |f| between two faces (no geometry spans it; world shaders keep
           Unity's default Cull Back -- consumption/VERIFY.md C12). Reported: torn positions, torn seam edges and
           their length, max slit.
  WALK     on-foot crossings over every torn WALKABLE seam (partner Beach1/Beach2/walkable Object; Sea/River/Falls/
           Stream are not on-foot topographs, stitchlib topo census). Probe points 0.4u into each incident tri;
           a step A->B uses the engine walk query: actor y = ground(A) + slice (topo 36/37/38 sink -1.171875,
           ff9.cs w_movementGetSliceHeight), ray origin y+2.34375 (ff9.cs rayStartOffsetY), a 10-slot hit-cache
           test FIRST (WMBlock.Raycast; cached tris are tested WITHOUT the up-facing/idall filters,
           WMPhysics.RaycastOnSpecifiedTriangle; no cache when standing on topo 49/52, ff9.cs
           w_movementRoundCheck), then the first-mesh/first-tri scan (placement.place). Legal iff a hit and the
           hit topograph is in the on-foot mask (placement.WALK_OK). A miss refuses the step (ff9.cs ~5700
           `if (num3 >= 0)`). Classified before vs after: INTRODUCED WALL (legal -> refused).
  ENTRANCE event!=0 Terrain tris with a vertex moved > 0.05u (world-deploy refuses these; terrain.reshape does not).
  OBJECT   torn Terrain|Object welds (base burial on a raise, a floating skirt on a lower).
Writes out/tear_sweep.json (per-edit rows + distributions) and prints the summary.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/tear_sweep.py
"""
from __future__ import annotations

import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402
from ff9mapkit.world import placement as P             # noqa: E402
from ff9mapkit.world.mesh import _falloff              # noqa: E402  the kit's own falloff (smooth)

AMOUNTS = (1.0, -1.0, 3.0, -3.0, 6.0, -6.0)
RADII = (8.0, 16.0, 24.0)
CELL = 16.0
PROBE = 0.4
WALK_START = P.WALK_RAY_START
CANOPY = {36, 37, 38}
SINK = 1.171875
WALKABLE_PARTNERS = {"beach1", "beach2", "object"}


class BM:
    """Minimal BlockMesh stand-in for placement.place/build_index (local frame)."""
    __slots__ = ("verts", "tangents", "flat_index", "tris", "x", "y", "name")

    def __init__(self, verts, idall, fi, x, y, name):
        self.verts = verts
        self.tangents = [(float(a), 0.0, 0.0, 0.0) for a in idall]
        self.flat_index = fi
        self.tris = [fi[i:i + 3] for i in range(0, len(fi), 3)]
        self.x, self.y, self.name = x, y, name


def build_world(M):
    blocks = defaultdict(dict)
    for (x, y, p), m in M.items():
        blocks[(x, y)][p] = m
    return blocks


def meshlist_for(blocks, blk, terrain_verts=None):
    parts = {}
    for p, m in blocks[blk].items():
        if P.canonical_part(p) is None:
            continue                                   # volcano*/sea4f: not in the modelled registration order
        v = terrain_verts if (p == "terrain" and terrain_verts is not None) else m.lv
        parts[p] = BM(v, m.idall, m.fi, blk[0], blk[1], p)
    ml = P.build_meshlist(parts)
    return ml


def walk_step(ml, idx, qx, qz, y_actor, cache, use_cache=True):
    """Engine walk query at block-local (qx, qz) from actor y. cache = [(mesh_i, tri)] most-recent-first."""
    oy = y_actor + WALK_START
    if use_cache:
        for (mi, t) in cache:
            bm = ml[mi][1]
            fi, V = bm.flat_index, bm.verts
            a, b, c = V[fi[3 * t]], V[fi[3 * t + 1]], V[fi[3 * t + 2]]
            d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
            if abs(d) < 1e-12:
                continue
            w0 = ((b[2] - c[2]) * (qx - c[0]) + (c[0] - b[0]) * (qz - c[2])) / d
            w1 = ((c[2] - a[2]) * (qx - c[0]) + (a[0] - c[0]) * (qz - c[2])) / d
            w2 = 1 - w0 - w1
            if min(w0, w1, w2) < -1e-9:
                continue
            hy = w0 * a[1] + w1 * b[1] + w2 * c[1]
            if hy > oy:
                continue
            ida = int(round(bm.tangents[fi[3 * t]][0]))
            return hy, ml[mi][0], ida, S.topo(ida), "cache"
    gy, name, ida, tp = P.place(ml, qx, qz, y_actor, sky=False, index=idx)
    return gy, name, ida, tp, "scan"


def hit_tri(ml, idx, qx, qz, y, sky):
    """(mesh_i, tri) the full scan picks -- for seeding the cache with the start tri."""
    origin = y + (P.SKY_RAY_START if sky else WALK_START)
    for mi, (name, bm) in enumerate(ml):
        V, T, fi = bm.verts, bm.tangents, bm.flat_index
        cand = idx[mi].get((math.floor(qx / P.INDEX_GRID), math.floor(qz / P.INDEX_GRID)), ())
        for t in cand:
            a, b, c = V[fi[3 * t]], V[fi[3 * t + 1]], V[fi[3 * t + 2]]
            ida = int(round(T[fi[3 * t]][0]))
            if ida in P.IDALL_SKIP:
                continue
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            ny = uz * vx - ux * vz
            L = math.sqrt((uy * vz - uz * vy) ** 2 + ny * ny + (ux * vy - uy * vx) ** 2) or 1.0
            if ny / L <= 0.1:
                continue
            d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
            if abs(d) < 1e-12:
                continue
            w0 = ((b[2] - c[2]) * (qx - c[0]) + (c[0] - b[0]) * (qz - c[2])) / d
            w1 = ((c[2] - a[2]) * (qx - c[0]) + (a[0] - c[0]) * (qz - c[2])) / d
            w2 = 1 - w0 - w1
            if min(w0, w1, w2) < -1e-9:
                continue
            hy = w0 * a[1] + w1 * b[1] + w2 * c[1]
            if hy > origin:
                continue
            if ida == P.VETO:
                break
            return (mi, t), hy, ida
    return None, 0.0, 0


def crossing(ml_a, idx_a, A, ml_b, idx_b, B):
    """On-foot step from block-local point A (in block a's meshlist) to B (block b). Returns
    (legal, detail)."""
    st, gy, ida = hit_tri(ml_a, idx_a, A[0], A[1], 0.0, sky=True)
    if st is None:
        return None, "start-miss"
    tp = S.topo(ida)
    if tp not in P.WALK_OK:
        return None, "start-unwalkable"
    y_actor = gy - (SINK if tp in CANOPY else 0.0)
    use_cache = tp not in (49, 52) and ml_a is ml_b
    cache = [st] if use_cache else []
    hy, name, ida2, tp2, how = walk_step(ml_b, idx_b, B[0], B[1], y_actor, cache, use_cache=use_cache)
    if name == "MISS":
        return False, f"miss(climb>{WALK_START - (SINK if tp in CANOPY else 0):.3f})"
    if tp2 not in P.WALK_OK:
        return False, f"unwalkable topo {tp2} on {name}"
    return True, f"{name}:{how}"


def main():
    t0 = time.time()
    M = S.load_disc(1)
    blocks = build_world(M)
    owners = defaultdict(set)
    for k, m in M.items():
        for p in m.wv:
            owners[S.wrap_key(p)].add(k)
    # Terrain weld index: per land block, local terrain position -> partners (non-terrain or other-block terrain)
    welds = {}
    tri_at = defaultdict(lambda: defaultdict(list))     # blk -> local pos -> [(part, tri)]
    for (x, y), parts in blocks.items():
        for p, m in parts.items():
            for t in range(m.ntri):
                for k in range(3):
                    tri_at[(x, y)][m.lv[m.fi[3 * t + k]]].append((p, t))
    for (x, y), parts in blocks.items():
        if "terrain" not in parts:
            continue
        ter = parts["terrain"]
        w = {}
        for lp, wp in zip(ter.lv, ter.wv):
            if lp in w:
                continue
            others = owners[S.wrap_key(wp)] - {(x, y, "terrain")}
            if others:
                w[lp] = sorted(others)
        welds[(x, y)] = w
    beach_blocks = sorted({(x, y) for (x, y, p) in M if p in ("beach1", "beach2")})
    obj_blocks = sorted({(x, y) for (x, y, p) in M if p == "object"})

    def centres(blk, kinds):
        cells = defaultdict(list)
        for lp, others in welds[blk].items():
            if any(o[2] in kinds for o in others):
                wx, wz = lp[0] + blk[0] * S.B, lp[2] - blk[1] * S.B
                cells[(math.floor(wx / CELL), math.floor(wz / CELL))].append((wx, wz))
        out = []
        for c, pts in sorted(cells.items()):
            mx = sum(p[0] for p in pts) / len(pts)
            mz = sum(p[1] for p in pts) / len(pts)
            best = min(pts, key=lambda p: (p[0] - mx) ** 2 + (p[1] - mz) ** 2)
            out.append((best, len(pts)))
        return out

    plan = []
    for b in beach_blocks:
        for (c, n) in centres(b, {"beach1", "beach2"}):
            plan.append(("beach", b, c, n))
    for b in obj_blocks:
        for (c, n) in centres(b, {"object"}):
            plan.append(("object", b, c, n))
    print(f"[plan] {len(beach_blocks)} beach blocks, {len(obj_blocks)} object blocks -> "
          f"{sum(1 for p in plan if p[0] == 'beach')} beach centres, {sum(1 for p in plan if p[0] == 'object')} "
          f"object centres; x {len(AMOUNTS) * len(RADII)} edits")

    base_ml, base_idx, order_exc = {}, {}, set()

    def ml_of(blk, tv=None):
        ml = meshlist_for(blocks, blk, tv)
        return ml

    def base(blk):
        if blk not in base_ml:
            try:
                ml = ml_of(blk)
                base_idx[blk] = P.build_meshlist_index(ml)
                base_ml[blk] = ml
            except ValueError:
                order_exc.add(blk)
                base_ml[blk] = None
        return base_ml[blk]

    rows = []
    for (kind, b0, c, n) in plan:
        cx, cz = c
        for R in RADII:
            # the blocks reshape would touch (terrain.reshape: AABB of centre +- R, in-grid, with terrain)
            bx0, bx1 = math.floor((cx - R) / S.B), math.floor((cx + R) / S.B)
            by0, by1 = math.floor(-(cz + R) / S.B), math.floor(-(cz - R) / S.B)
            touched = [(bx, by) for bx in range(bx0, bx1 + 1) for by in range(by0, by1 + 1)
                       if 0 <= bx < S.GX and 0 <= by < S.GY and (bx, by) in welds]
            offgrid = [(bx, by) for bx in range(bx0, bx1 + 1) for by in range(by0, by1 + 1)
                       if not (0 <= bx < S.GX and 0 <= by < S.GY)]
            # weights per touched block's terrain local positions
            wts = {}
            for blk in touched:
                ox, oz = blk[0] * S.B, -blk[1] * S.B
                wt = {}
                for lp in set(blocks[blk]["terrain"].lv):
                    w = _falloff(math.hypot(lp[0] + ox - cx, lp[2] + oz - cz) / R, "smooth")
                    if w > 0:
                        wt[lp] = w
                wts[blk] = wt
            for A in AMOUNTS:
                row = {"kind": kind, "block": list(b0), "centre": [round(cx, 3), round(cz, 3)], "welds_in_cell": n,
                       "amount": A, "radius": R, "touched": len(touched), "offgrid": len(offgrid)}
                torn = Counter()
                maxslit = 0.0
                torn_pos = []                                    # (blk, lp, f, partners)
                for blk in touched:
                    wt = wts[blk]
                    for lp, others in welds[blk].items():
                        f = A * wt.get(lp, 0.0)
                        tparts = {o[2] for o in others if o[2] != "terrain"}
                        # Terrain|Terrain: the neighbour moves iff it is in `touched` (same world weight)
                        tt = [o for o in others if o[2] == "terrain" and (o[0], o[1]) not in wts]
                        if abs(f) > S.TOL and (tparts or tt):
                            for p in tparts:
                                torn[p] += 1
                            if tt:
                                torn["terrain(unmoved nbr)"] += 1
                            maxslit = max(maxslit, abs(f))
                            torn_pos.append((blk, lp, f, others))
                row["torn"] = dict(torn)
                row["torn_positions"] = len(torn_pos)
                row["max_slit"] = round(maxslit, 3)
                # torn seam edges: terrain edges with both ends welded to the same partner part, either end torn
                seam_len = 0.0
                seam_n = 0
                for blk in touched:
                    ter = blocks[blk]["terrain"]
                    wb = welds[blk]
                    wt = wts[blk]
                    seen = set()
                    for t in range(ter.ntri):
                        cs = [ter.lv[ter.fi[3 * t + k]] for k in range(3)]
                        for i, j in ((0, 1), (1, 2), (2, 0)):
                            a, bb = cs[i], cs[j]
                            e = (a, bb) if a <= bb else (bb, a)
                            if e in seen:
                                continue
                            seen.add(e)
                            if a not in wb or bb not in wb:
                                continue
                            pa = {o for o in wb[a] if o[2] != "terrain"}
                            pb = {o for o in wb[bb] if o[2] != "terrain"}
                            if not (pa & pb):
                                continue
                            fa, fb = A * wt.get(a, 0.0), A * wt.get(bb, 0.0)
                            if max(abs(fa), abs(fb)) > S.TOL:
                                seam_n += 1
                                seam_len += math.dist(a, bb)
                row["torn_seam_edges"] = seam_n
                row["torn_seam_len"] = round(seam_len, 2)
                # entrance tiles moved
                ent = 0
                for blk in touched:
                    ter = blocks[blk]["terrain"]
                    wt = wts[blk]
                    for t in range(ter.ntri):
                        if S.event(ter.tri_idall(t)):
                            if any(abs(A * wt.get(ter.lv[ter.fi[3 * t + k]], 0.0)) > S.TOL for k in range(3)):
                                ent += 1
                row["entrance_tris_moved"] = ent
                # walk crossings at torn walkable seams
                walls = Counter()
                details = Counter()
                crossings = 0
                after_ml = {}
                for (blk, lp, f, others) in torn_pos:
                    wparts = [o for o in others if o[2] in WALKABLE_PARTNERS]
                    if not wparts:
                        continue
                    if base(blk) is None:
                        details["order-exception block (not modelled)"] += 1
                        continue
                    if blk not in after_ml:
                        ter = blocks[blk]["terrain"]
                        wt = wts[blk]
                        tv = [(v[0], v[1] + A * wt.get(v, 0.0), v[2]) for v in ter.lv]
                        after_ml[blk] = ml_of(blk, tv)
                    mlb, idx = base_ml[blk], base_idx[blk]
                    mla = after_ml[blk]
                    # probe points: 0.4u into every incident tri (same-block tris only)
                    probes = []
                    for (p, t) in tri_at[blk][lp]:
                        m = blocks[blk][p]
                        cs = [m.lv[m.fi[3 * t + k]] for k in range(3)]
                        gx, gz = sum(q[0] for q in cs) / 3 - lp[0], sum(q[2] for q in cs) / 3 - lp[2]
                        L = math.hypot(gx, gz)
                        if L < 1e-6:
                            continue
                        probes.append((p, (lp[0] + PROBE * gx / L, lp[2] + PROBE * gz / L)))
                    for (pa_, A_) in probes:
                        for (pb_, B_) in probes:
                            if pa_ == pb_ or "terrain" not in (pa_, pb_):
                                continue
                            if pa_ not in WALKABLE_PARTNERS | {"terrain"} or pb_ not in WALKABLE_PARTNERS | {"terrain"}:
                                continue
                            before, db = crossing(mlb, idx, A_, mlb, idx, B_)
                            after, da = crossing(mla, idx, A_, mla, idx, B_)
                            crossings += 1
                            if before and after is False:
                                walls[f"{pa_}->{pb_}"] += 1
                                details[da.split('(')[0]] += 1
                row["walk_crossings"] = crossings
                row["introduced_walls"] = dict(walls)
                row["wall_reasons"] = dict(details)
                rows.append(row)
    # ---- distributions ----------------------------------------------------------------------------
    dist = {}
    for kind in ("beach", "object"):
        for A in AMOUNTS:
            for R in RADII:
                sel = [r for r in rows if r["kind"] == kind and r["amount"] == A and r["radius"] == R]
                if not sel:
                    continue
                tp = sorted(r["torn_positions"] for r in sel)
                tw = [sum(r["introduced_walls"].values()) for r in sel]
                worst = Counter()
                for r in sel:
                    if sum(r["introduced_walls"].values()):
                        worst["WALL"] += 1
                    elif r["entrance_tris_moved"]:
                        worst["ENTRANCE"] += 1
                    elif r["torn_positions"]:
                        worst["SLIT"] += 1
                    else:
                        worst["NONE"] += 1
                part_tot = Counter()
                for r in sel:
                    part_tot.update(r["torn"])
                dist[f"{kind} A{A:+g} R{R:g}"] = {
                    "edits": len(sel), "torn_median": tp[len(tp) // 2], "torn_max": tp[-1],
                    "torn_p90": tp[int(0.9 * (len(tp) - 1))],
                    "max_slit": max(r["max_slit"] for r in sel),
                    "edits_with_wall": sum(1 for x in tw if x), "walls_total": sum(tw),
                    "edits_moving_entrance": sum(1 for r in sel if r["entrance_tris_moved"]),
                    "worst": dict(worst), "torn_by_partner": dict(part_tot)}
    out = {"n_edits": len(rows), "beach_blocks": len(beach_blocks), "object_blocks": len(obj_blocks),
           "order_exception_blocks": sorted(order_exc), "distribution": dist, "rows": rows,
           "seconds": round(time.time() - t0, 1)}
    print(f"{len(rows)} edits in {time.time() - t0:.0f}s; order-exception blocks skipped for walk: {sorted(order_exc)}")
    print(f"{'edit class':22s} {'n':>4s} {'torn med/p90/max':>18s} {'maxslit':>8s} {'walls(edits/total)':>19s} "
          f"{'entr':>5s}  worst")
    for k, d in dist.items():
        print(f"{k:22s} {d['edits']:4d} {d['torn_median']:6d}/{d['torn_p90']:4d}/{d['torn_max']:5d} {d['max_slit']:8.2f} "
              f"{d['edits_with_wall']:8d}/{d['walls_total']:<8d} {d['edits_moving_entrance']:5d}  {d['worst']}")
    p = S.save_json("tear_sweep.json", out)
    print("->", p)


if __name__ == "__main__":
    main()
