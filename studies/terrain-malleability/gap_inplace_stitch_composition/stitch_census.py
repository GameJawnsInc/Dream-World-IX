"""METHOD A -- the STOCK STITCH GRAPH of the overworld, discs 1 and 4, folder 0_1.

What does Terrain share with the other parts (Beach1/2, Sea1-6, River/RiverJoint/Falls/Stream, Object, Volcano*)
and with its neighbour blocks (incl. the x-seam 23<->0 and z-seam 19<->0 torus wraps)? Every coincidence a
Terrain-only Y edit can tear.

Instruments (all EXACT-container reads via stitchlib.load_disc; positions keyed exactly after the torus fold):
  1. EXACT WELDS: union over identical world positions (wrapped). Every unordered pair of distinct
     (block, part) owners at one position is a weld; classified (partA, partB, relation) with relation
     same-block / border / border-wrapx / border-wrapz.
  2. NEAR-MISS pairs: two distinct positions closer than 0.05u in 3D (the transplant/mesh.weld_audit tol),
     across ALL parts and blocks (spatial hash) -- stock hairlines.
  3. XZ-STACKS: positions identical in XZ but |dy| >= 0.05 between different owners (a vertical skirt/stack;
     NOT a weld, but an ordering a Y edit can invert).
  4. T-JUNCTIONS: a vertex of owner Q lying ON an edge interior of owner P (3D distance < 1e-3, not at an
     endpoint), P/Q any parts in the block or its 4 neighbours, including P == Q (a self T-vertex).
     A nonlinear Y field moves the vertex by f(v) and the edge by the lerp of f(a), f(b): a T-junction tears
     even when both sides are displaced.
  5. BORDERS: for every pair of torus-adjacent blocks that both carry Terrain: Terrain border edges per side,
     coverage intervals, the UNCOVERED stretches (one side's Terrain border spans along-coordinates the other's
     does not -- disc4/VERIFY.md D4-06's fix: these are NOT gap-0), the gap over the MUTUALLY covered stretch
     (top polyline, weld_gap.py's metric), and what part of the other block covers an uncovered stretch.
Writes out/stitch_census.json (per disc, per block pair-type counts + global totals + border table).
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/stitch_census.py
"""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402

EDGE_TOL = 1e-3          # "on the edge" (3D) for a T-junction
END_EPS = 1e-4           # not at an endpoint
NEAR = S.TOL


def rel(o1, o2):
    (x1, y1, _), (x2, y2, _) = o1, o2
    if (x1, y1) == (x2, y2):
        return "same"
    dx, dy = (x2 - x1) % S.GX, (y2 - y1) % S.GY
    adj_x = dx in (1, S.GX - 1) and dy == 0
    adj_y = dy in (1, S.GY - 1) and dx == 0
    diag = dx in (1, S.GX - 1) and dy in (1, S.GY - 1)
    wrapx = abs(x2 - x1) == S.GX - 1
    wrapz = abs(y2 - y1) == S.GY - 1
    if adj_x or adj_y:
        return "border-wrapx" if wrapx else "border-wrapz" if wrapz else "border"
    if diag:
        return "corner-wrap" if (wrapx or wrapz) else "corner"
    return "far"


def norm_part(p):
    return p


def pair_key(o1, o2):
    a, b = o1[2], o2[2]
    r = rel(o1, o2)
    if a > b:
        a, b = b, a
    return f"{a}|{b}|{r}"


def census_disc(disc):
    M = S.load_disc(disc)
    land = set(S.land_blocks(M))
    owners = defaultdict(set)                          # wrapped exact pos -> {(x,y,part)}
    for k, m in M.items():
        for p in m.wv:
            owners[S.wrap_key(p)].add(k)
    # ---- 1. exact welds ----------------------------------------------------------------------
    weld = Counter()
    per_block_pairs = defaultdict(Counter)             # block -> every weld pair type touching it (all parts)
    per_block = defaultdict(Counter)                   # land block -> Terrain-partner counts (unique Terrain positions)
    terr_pos_n = {}
    for pos, os_ in owners.items():
        if len(os_) < 2:
            continue
        ol = sorted(os_)
        for i in range(len(ol)):
            for j in range(i + 1, len(ol)):
                pk = pair_key(ol[i], ol[j])
                weld[pk] += 1
                for o in {ol[i][:2], ol[j][:2]}:
                    per_block_pairs[o][pk] += 1
    for (x, y) in land:
        tp = {S.wrap_key(p) for p in M[(x, y, "terrain")].wv}
        terr_pos_n[(x, y)] = len(tp)
        c = per_block[(x, y)]
        for pos in tp:
            others = owners[pos] - {(x, y, "terrain")}
            if not others:
                c["terrain_only"] += 1
                continue
            c["welded_any"] += 1
            kinds = set()
            for o in others:
                r = rel((x, y, "terrain"), o)
                kinds.add(f"{o[2]}@{'same' if r == 'same' else 'nbr'}")
            for kd in kinds:
                c[kd] += 1
            if any(o[2] != "terrain" for o in others):
                c["welded_nonterrain"] += 1
    # ---- 2. near-miss pairs + 3. XZ stacks ---------------------------------------------------
    cells = defaultdict(list)
    for pos in owners:
        cells[(math.floor(pos[0] / NEAR), math.floor(pos[1] / NEAR), math.floor(pos[2] / NEAR))].append(pos)
    near = Counter()
    near_examples = []
    for (cx, cy, cz), pts in cells.items():
        cand = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    cand.extend(cells.get((cx + dx, cy + dy, cz + dz), ()))
        for p1 in pts:
            for p2 in cand:
                if p1 < p2:
                    d2 = (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2
                    if 0 < d2 < NEAR * NEAR:
                        for o1 in owners[p1]:
                            for o2 in owners[p2]:
                                near[pair_key(o1, o2)] += 1
                        if len(near_examples) < 40:
                            near_examples.append({"a": p1, "b": p2, "d": round(math.sqrt(d2), 5),
                                                  "owners_a": sorted(owners[p1]), "owners_b": sorted(owners[p2])})
    xz = defaultdict(set)
    for pos, os_ in owners.items():
        xz[(pos[0], pos[2])].add((pos[1], frozenset(os_)))
    stack = Counter()
    for k, ys in xz.items():
        if len(ys) < 2:
            continue
        ys = sorted(ys, key=lambda t: t[0])
        for i in range(len(ys)):
            for j in range(i + 1, len(ys)):
                if ys[j][0] - ys[i][0] < NEAR:
                    continue
                for o1 in ys[i][1]:
                    for o2 in ys[j][1]:
                        if o1 != o2:
                            stack[pair_key(o1, o2)] += 1
    tj, tj_near, tj_block = tjunctions(M)
    # ---- 5. borders ---------------------------------------------------------------------------
    border_rows = []
    for (x, y) in sorted(land):
        for (nx, ny, side) in S.neighbours(x, y)[::2]:          # E and S only (each pair once)
            if (nx, ny) not in land:
                continue
            opp = {"E": "W", "S": "N"}[side]
            A = border_profile(M, (x, y), side)
            Bp = border_profile(M, (nx, ny), opp)
            row = compare_border(A, Bp)
            row.update({"a": [x, y, side], "b": [nx, ny, opp],
                        "wrap": (side == "E" and x == S.GX - 1) or (side == "S" and y == S.GY - 1)})
            # what covers each side's uncovered stretch on the OTHER block (any part)
            for who, other_blk, other_side in (("A_only", (nx, ny), opp), ("B_only", (x, y), side)):
                st = row[f"uncovered_{who}"]
                if not st:
                    continue
                cov = {}
                for (bx_, by_, p), m in M.items():
                    if (bx_, by_) != other_blk or p == "terrain":
                        continue
                    pr = border_profile(M, other_blk, other_side, part=p)
                    tot = sum(overlap_len(iv, pr["cover"]) for iv in st)
                    if tot > 1e-6:
                        cov[p] = round(tot, 3)
                row[f"cover_{who}_by_other_part"] = cov
            border_rows.append(row)
    # ---- 6. Terrain-partner classes (the task's taxonomy) + what transplant.PARTS (VertexDisplace's reach in
    #         morph_in_place) can co-move ---------------------------------------------------------------------
    from ff9mapkit.world.transplant import PARTS as TPARTS
    cls_of = {"beach1": "Beach1/2", "beach2": "Beach1/2", "sea1": "Sea1/2/3 (shallow rim)",
              "sea2": "Sea1/2/3 (shallow rim)", "sea3": "Sea1/2/3 (shallow rim)", "sea4": "Sea4/5/6/4f (open water)",
              "sea5": "Sea4/5/6/4f (open water)", "sea6": "Sea4/5/6/4f (open water)", "sea4f": "Sea4/5/6/4f (open water)",
              "river": "River/RiverJoint/Falls/Stream", "riverjoint": "River/RiverJoint/Falls/Stream",
              "falls": "River/RiverJoint/Falls/Stream", "stream": "River/RiverJoint/Falls/Stream",
              "object": "Object", "volcanocrater": "Volcano*", "volcanolava": "Volcano*", "terrain": "Terrain"}
    classes = Counter()
    outside_parts = Counter()
    for k, v in weld.items():
        a, b, r = k.split("|")
        if "terrain" not in (a, b):
            continue
        other = b if a == "terrain" else a
        if other == "terrain":
            classes["Terrain-Terrain " + ("across a border" if r.startswith("border") else r)] += v
            continue
        classes[f"Terrain-{cls_of.get(other, other)} ({'same block' if r == 'same' else 'across a border'})"] += v
        if other not in TPARTS:
            outside_parts[other] += v
    summary_classes = {"terrain_partner_classes": dict(classes.most_common()),
                       "terrain_welds_outside_transplant_PARTS": dict(outside_parts.most_common()),
                       "terrain_welds_outside_transplant_PARTS_total": sum(outside_parts.values()),
                       "transplant_PARTS": list(TPARTS)}
    summary = {
        **summary_classes,
        "disc": disc, "meshes": len(M), "land_blocks": len(land),
        "unique_positions": len(owners),
        "weld_pair_types": dict(weld.most_common()),
        "near_miss_pair_types": dict(near.most_common()), "near_miss_examples": near_examples,
        "xz_stack_pair_types": dict(stack.most_common()),
        "tjunction_pair_types": dict(tj.most_common()),
        "tjunction_near_pair_types": dict(tj_near.most_common()),
        "per_block_terrain_partners": {f"{x},{y}": dict(c) | {"terrain_positions": terr_pos_n[(x, y)]}
                                       for (x, y), c in sorted(per_block.items())},
        "per_block_tjunctions": {f"{x},{y}": dict(c) for (x, y), c in sorted(tj_block.items())},
        "per_block_weld_pair_types": {f"{x},{y}": dict(c.most_common()) for (x, y), c in sorted(per_block_pairs.items())},
        "borders": border_rows,
    }
    return summary


def tjunctions(M, blocks=None):
    """T-junction scan (see module docstring, instrument 4). ``blocks`` limits which blocks' EDGES are scanned
    (vertices still come from the block + its 4 torus neighbours). Returns (exact Counter, near Counter,
    per-block Counter, examples)."""
    tj = Counter()
    tj_near = Counter()
    tj_block = defaultdict(Counter)
    edges_by = {k: S.mesh_edges(m) for k, m in M.items()}
    for (x, y) in sorted(blocks if blocks is not None else {(k[0], k[1]) for k in M}):
        mine = [k for k in M if (k[0], k[1]) == (x, y)]
        # vertex owners: this block + 4 neighbours, moved into THIS block's unwrapped frame
        cand_owners = list(mine)
        for (nx, ny, _s) in S.neighbours(x, y):
            cand_owners += [k for k in M if (k[0], k[1]) == (nx, ny)]
        verts = []                                      # (pos_in_this_frame, owner)
        for k in set(cand_owners):
            m = M[k]
            sx = sz = 0.0
            if (k[0], k[1]) != (x, y):
                ddx = k[0] - x
                ddy = k[1] - y
                if ddx > 1:
                    sx = -S.WX
                elif ddx < -1:
                    sx = S.WX
                if ddy > 1:
                    sz = S.WZ                         # row y+19 -> it is the block NORTH of row 0: z shifts +1280
                elif ddy < -1:
                    sz = -S.WZ
            seen = set()
            for p in m.wv:
                q = (p[0] + sx, p[1], p[2] + sz)
                if q in seen:
                    continue
                seen.add(q)
                verts.append((q, k))
        # only vertices within 0.1u of this block's frame or inside it matter
        ox0, ox1, oz1, oz0 = x * S.B, x * S.B + S.B, -y * S.B, -y * S.B - S.B
        grid = defaultdict(list)
        for (q, k) in verts:
            if ox0 - 0.1 <= q[0] <= ox1 + 0.1 and oz0 - 0.1 <= q[2] <= oz1 + 0.1:
                grid[(math.floor(q[0] / 2.0), math.floor(q[2] / 2.0))].append((q, k))
        for kP in mine:
            for (a, b), _tris in edges_by[kP].items():
                gx0, gx1 = math.floor((min(a[0], b[0]) - 0.06) / 2.0), math.floor((max(a[0], b[0]) + 0.06) / 2.0)
                gz0, gz1 = math.floor((min(a[2], b[2]) - 0.06) / 2.0), math.floor((max(a[2], b[2]) + 0.06) / 2.0)
                for gx in range(gx0, gx1 + 1):
                    for gz in range(gz0, gz1 + 1):
                        for (q, kQ) in grid.get((gx, gz), ()):
                            if math.dist(q, a) < END_EPS or math.dist(q, b) < END_EPS:
                                continue
                            d, t = S.seg_point_dist(q, a, b)
                            if not (1e-6 < t < 1 - 1e-6):
                                continue
                            if d < EDGE_TOL:
                                key = pair_key(kP, kQ) + ("|self" if kP == kQ else "")
                                tj[key] += 1
                                if kP[2] == "terrain" or kQ[2] == "terrain":
                                    tj_block[(x, y)][f"{kP[2]}<-{kQ[2]}"] += 1
                            elif d < NEAR:
                                tj_near[pair_key(kP, kQ) + ("|self" if kP == kQ else "")] += 1
    return tj, tj_near, tj_block


def border_profile(M, blk, side, part="terrain"):
    """Border edges of ``part`` on one side, in LOCAL along-coords. Returns {cover: [intervals], pts:
    [(along, y)], edges: [(a0,y0,a1,y1)]}."""
    m = M.get((blk[0], blk[1], part))
    out = {"cover": [], "pts": set(), "edges": []}
    if m is None:
        return out
    lv, fi = m.lv, m.fi

    def on(v):
        if side == "E":
            return abs(v[0] - 64.0) < 1e-4, v[2]
        if side == "W":
            return abs(v[0]) < 1e-4, v[2]
        if side == "N":
            return abs(v[2]) < 1e-4, v[0]
        return abs(v[2] + 64.0) < 1e-4, v[0]
    seen = set()
    for t in range(len(fi) // 3):
        cs = [lv[fi[3 * t + k]] for k in range(3)]
        for i, j in ((0, 1), (1, 2), (2, 0)):
            oi, ai = on(cs[i])
            oj, aj = on(cs[j])
            if oi:
                out["pts"].add((ai, cs[i][1]))
            if oi and oj:
                e = (ai, cs[i][1], aj, cs[j][1])
                ek = tuple(sorted([(ai, cs[i][1]), (aj, cs[j][1])]))
                if ek in seen:
                    continue
                seen.add(ek)
                out["edges"].append(e)
    ivs = sorted((min(e[0], e[2]), max(e[0], e[2])) for e in out["edges"] if abs(e[0] - e[2]) > 1e-6)
    merged = []
    for a, b in ivs:
        if merged and a <= merged[-1][1] + 1e-6:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out["cover"] = merged
    return out


def overlap_len(iv, cover):
    a, b = iv
    return sum(max(0.0, min(b, d) - max(a, c)) for c, d in cover)


def subtract(cov_a, cov_b):
    """cov_a minus cov_b as intervals."""
    out = []
    for a, b in cov_a:
        cur = [[a, b]]
        for c, d in cov_b:
            nxt = []
            for p, q in cur:
                if d <= p or c >= q:
                    nxt.append([p, q])
                    continue
                if c > p:
                    nxt.append([p, c])
                if d < q:
                    nxt.append([d, q])
            cur = nxt
        out += [iv for iv in cur if iv[1] - iv[0] > 1e-6]
    return out


def top_y(edges, a):
    """max y over border edges covering along-coordinate a (lerp), or None."""
    best = None
    for (a0, y0, a1, y1) in edges:
        lo, hi = min(a0, a1), max(a0, a1)
        if hi - lo < 1e-9:
            if abs(a - lo) < 1e-6:
                y = max(y0, y1)
            else:
                continue
        elif lo - 1e-6 <= a <= hi + 1e-6:
            y = y0 + (y1 - y0) * ((a - a0) / (a1 - a0))
        else:
            continue
        best = y if best is None else max(best, y)
    return best


def compare_border(A, B):
    pa, pb = A["pts"], B["pts"]
    exact = pa == pb
    ua = subtract(A["cover"], B["cover"])
    ub = subtract(B["cover"], A["cover"])
    both = subtract(A["cover"], ua)
    # sample the mutual stretch at every vertex along-coordinate of either side inside it + midpoints
    alongs = sorted({p[0] for p in pa} | {p[0] for p in pb})
    samples = []
    for a in alongs:
        if any(c - 1e-6 <= a <= d + 1e-6 for c, d in both):
            samples.append(a)
    gap = 0.0
    worst_at = None
    for a in samples:
        ha, hb = top_y(A["edges"], a), top_y(B["edges"], a)
        if ha is None or hb is None:
            continue
        if abs(ha - hb) > gap:
            gap, worst_at = abs(ha - hb), a
    # unmatched border verts (vertex present on one side only) inside the mutual stretch
    only_a = [p for p in pa if p not in pb and any(c - 1e-6 <= p[0] <= d + 1e-6 for c, d in both)]
    only_b = [p for p in pb if p not in pa and any(c - 1e-6 <= p[0] <= d + 1e-6 for c, d in both)]
    return {"exact": exact, "gap_mutual": round(gap, 4), "gap_at": worst_at,
            "uncovered_A_only": ua, "uncovered_B_only": ub,
            "uncovered_len": round(sum(b - a for a, b in ua) + sum(b - a for a, b in ub), 3),
            "unmatched_A": len(only_a), "unmatched_B": len(only_b),
            "nA": len(pa), "nB": len(pb)}


def main():
    res = {}
    for disc in (1, 4):
        s = census_disc(disc)
        res[f"disc{disc}"] = s
        b = s["borders"]
        print(f"\n=== disc {disc}: {s['meshes']} meshes, {s['land_blocks']} land blocks, "
              f"{s['unique_positions']} unique wrapped positions")
        print(" exact-weld pair types (top 30):")
        for k, v in list(s["weld_pair_types"].items())[:30]:
            print(f"   {k:45s} {v}")
        print(" Terrain partner classes (weld positions):")
        for k, v in s["terrain_partner_classes"].items():
            print(f"   {k:58s} {v}")
        print(" Terrain welds whose partner is OUTSIDE transplant.PARTS (VertexDisplace cannot co-move them):",
              s["terrain_welds_outside_transplant_PARTS_total"], s["terrain_welds_outside_transplant_PARTS"])
        print(" near-miss (<0.05u) pair types:", s["near_miss_pair_types"])
        print(" XZ-stack (|dy|>=0.05) pair types (top 15):", dict(list(s["xz_stack_pair_types"].items())[:15]))
        print(" T-junction pair types (top 25):", dict(list(s["tjunction_pair_types"].items())[:25]))
        print(" near-T (1e-3..0.05) pair types:", dict(list(s["tjunction_near_pair_types"].items())[:15]))
        ex = sum(1 for r in b if r["exact"])
        unc = [r for r in b if r["uncovered_len"] > 1e-6]
        gp = [r for r in b if r["gap_mutual"] > 0.01]
        print(f" borders terrain|terrain: {len(b)} pairs ({sum(1 for r in b if r['wrap'])} across a wrap); "
              f"exact {ex}; mutual-stretch gap>0.01: {len(gp)}; uncovered stretches: {len(unc)} "
              f"(total {sum(r['uncovered_len'] for r in unc):.1f}u)")
    p = S.save_json("stitch_census.json", res)
    print("->", p)


if __name__ == "__main__":
    main()
