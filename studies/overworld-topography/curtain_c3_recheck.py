"""C3 SKEPTIC -- adversarial RE-MEASUREMENT of the CURTAIN GRAMMAR claims.

Written from scratch (no code imported or copied from the curtain instrument) to test six
registered claims about how stock disc-1 joins interior rock (topo 49/50) to the coast:

  A  POPULATION   -- the wall-meets-water member/site count, swept over match radius
                     (4u / 8u / 12u), over the water DEFINITION (sea1..5 only vs
                     sea+beach -- beach sheets are topo 30/34/35, i.e. FOOT-LEGAL ground,
                     not water), over vert de-duplication, and over four clusterings
                     (8u/16u/24u plan cells + single-link 16u components).
  B  SPOT READS   -- direct per-block reads of the five named sites in the claims.
  C  FREE-EDGE    -- the hover test, by a DIFFERENT edge definition: a FREE edge is used
                     by exactly ONE triangle in a 3x3-block merged context (a properly
                     stitched curtain makes its top edge 2-owner, so it cannot appear
                     here at all -- the free set IS the candidate defect set).  Each free
                     edge is resolved against: T-join partner, top-most up-facing terrain
                     surface below the midpoint (>0.5u), un-stitched steep face hanging
                     off an endpoint, water-sheet plan cover, object-part cover at level.
  D  SEAM ANATOMY -- per-EDGE (not per-site) census of 2-owner edges whose partner is a
                     steep face descending below: sealing-face topograph, sealed-surface
                     topograph + foot-legality, drop, and bottom-vs-waterline.  Steepness
                     swept at |ny| <= 0.2 (the instrument's) and |ny| < 0.5 (mine).
  E  DESCENT      -- min rock y near water vs the water plane, per site.
  F  FREQUENCY    -- site classification as a JOINT distribution (sealed x corridor cover)
                     with the cover threshold swept 0.60/0.75/0.90/0.95, instead of a
                     precedence cascade, to test the "continuum" reading.
  G  SPOT/EXPOSE  -- 1u plan transects through named world points (topmost surface y +
                     topograph + water cover per sample) and a water-EXPOSURE census (is
                     the site's nearest water plan-covered by terrain >1u above it?), which
                     re-derives the HIDDEN-WATER exclusion count.

Every run first executes a POSITIVE CONTROL (`selftest`): a synthetic slab floating 6u over
a ground sheet MUST be reported as 4 hover-over-ground edges, and the same slab with a
stitched curtain MUST report 0 hover + 4 seal edges.  A zero hover count on stock data only
means something because that control fires.  Per-edge spot dumps: curtain_c3_spotread.py.

Read-only against the user's own stock disc-1 world mesh.  Nothing is deployed or written
outside out/.  Artifacts -> out/curtain_c3_recheck.json (+ .log).
Regenerate: py -X utf8 curtain_c3_recheck.py [stages]     (e.g. "AB", default "ABCDEF")
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                                      # noqa: E402

ROCK = {49, 50}
FOOT_LEGAL = {0, 1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 16, 17, 18, 19, 20, 21, 22, 23,
              27, 28, 30, 31, 32, 33, 34, 35, 36, 37, 38, 41, 42, 45, 46, 52}
SEA_PARTS = ("sea1", "sea2", "sea3", "sea4", "sea5")
BEACH_PARTS = ("beach1", "beach2")
OUT = Path(__file__).with_name("out") / "curtain_c3_recheck.json"
Q = 256.0                       # coords are exact multiples of 1/256 (verified)
UP = 0.5                        # |ny| >= UP  -> a surface (up-facing)
EPS = 1e-9


def key(v):
    return (int(round(v[0] * Q)), int(round(v[1] * Q)), int(round(v[2] * Q)))


def ny_of(v0, v1, v2):
    ax, ay, az = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
    bx, by, bz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
    nx = ay * bz - az * by
    ny = az * bx - ax * bz
    nz = ax * by - ay * bx
    n = math.sqrt(nx * nx + ny * ny + nz * nz)
    return 0.0 if n < EPS else ny / n


def load(part_names):
    """{(bx,by): [ (v0,v1,v2,topo,ny), ... ]} in the WORLD frame."""
    out = {}
    for (bx, by) in X.list_blocks(disc=1):
        ox, oz = bx * 64.0, -by * 64.0
        tris = []
        for part in part_names:
            try:
                bm = X.read_block(bx, by, disc=1, part=part)
            except Exception:                                                 # noqa: BLE001
                continue
            V, T, F = bm.verts, bm.tangents, bm.flat_index
            for t in range(len(F) // 3):
                i0, i1, i2 = F[3 * t], F[3 * t + 1], F[3 * t + 2]
                v0 = (V[i0][0] + ox, V[i0][1], V[i0][2] + oz)
                v1 = (V[i1][0] + ox, V[i1][1], V[i1][2] + oz)
                v2 = (V[i2][0] + ox, V[i2][1], V[i2][2] + oz)
                topo = X.decode_id(int(round(T[i0][0])))["topograph"]
                tris.append((v0, v1, v2, topo, ny_of(v0, v1, v2)))
        if tris:
            out[(bx, by)] = tris
    return out


# ---- plan geometry --------------------------------------------------------------------------
def bary(px, pz, tri):
    (x0, _, z0), (x1, _, z1), (x2, _, z2) = tri[0], tri[1], tri[2]
    d = (z1 - z2) * (x0 - x2) + (x2 - x1) * (z0 - z2)
    if abs(d) < 1e-7:
        return None
    a = ((z1 - z2) * (px - x2) + (x2 - x1) * (pz - z2)) / d
    b = ((z2 - z0) * (px - x2) + (x0 - x2) * (pz - z2)) / d
    c = 1.0 - a - b
    return (a, b, c)


def y_at(px, pz, tri, tol=1e-4):
    w = bary(px, pz, tri)
    if w is None or min(w) < -tol:
        return None
    return w[0] * tri[0][1] + w[1] * tri[1][1] + w[2] * tri[2][1]


class Grid:
    """Plan hash grid of triangle indices."""

    def __init__(self, tris, cell=4.0, want=None):
        self.cell, self.tris, self.g = cell, tris, defaultdict(list)
        for i, tr in enumerate(tris):
            if want is not None and not want(tr):
                continue
            xs = (tr[0][0], tr[1][0], tr[2][0])
            zs = (tr[0][2], tr[1][2], tr[2][2])
            for cx in range(int(math.floor(min(xs) / cell)), int(math.floor(max(xs) / cell)) + 1):
                for cz in range(int(math.floor(min(zs) / cell)), int(math.floor(max(zs) / cell)) + 1):
                    self.g[(cx, cz)].append(i)

    def at(self, px, pz):
        return self.g.get((int(math.floor(px / self.cell)), int(math.floor(pz / self.cell))), ())

    def top_below(self, px, pz, y, gap):
        """Highest tri surface strictly `gap` below y at (px,pz). -> (y, topo) | None."""
        best = None
        for i in self.at(px, pz):
            tr = self.tris[i]
            yy = y_at(px, pz, tr)
            if yy is None or yy > y - gap:
                continue
            if best is None or yy > best[0]:
                best = (yy, tr[3])
        return best

    def top_at(self, px, pz):
        best = None
        for i in self.at(px, pz):
            tr = self.tris[i]
            yy = y_at(px, pz, tr)
            if yy is None:
                continue
            if best is None or yy > best[0]:
                best = (yy, tr[3])
        return best

    def near_level(self, px, pz, y, tol=0.5):
        """ANY surface within +-tol of y (not just the topmost)."""
        for i in self.at(px, pz):
            yy = y_at(px, pz, self.tris[i])
            if yy is not None and abs(yy - y) <= tol:
                return (yy, self.tris[i][3])
        return None

    def any_cover(self, px, pz):
        for i in self.at(px, pz):
            if y_at(px, pz, self.tris[i]) is not None:
                return self.tris[i]
        return None


def uf_find(par, a):
    while par[a] != a:
        par[a] = par[par[a]]
        a = par[a]
    return a


def uf_union(par, a, b):
    ra, rb = uf_find(par, a), uf_find(par, b)
    if ra != rb:
        par[rb] = ra


# =============================================================================================
def stage_A(TERR, WATER_SEA, WATER_ALL):
    res = {}
    rock_raw, rock_uni = [], {}
    blocks_rock, blocks_water, blocks_both = set(), set(), set()
    for b, tris in TERR.items():
        hit = False
        for tr in tris:
            if tr[3] in ROCK:
                hit = True
                for v in tr[:3]:
                    rock_raw.append(v)
                    rock_uni[key(v)] = v
        if hit:
            blocks_rock.add(b)
    for b in set(WATER_SEA) | set(WATER_ALL):
        blocks_water.add(b)
    blocks_both = blocks_rock & blocks_water
    res["blocks_terrain"] = len(TERR)
    res["blocks_with_rock"] = len(blocks_rock)
    res["blocks_with_water_part"] = len(blocks_water)
    res["blocks_with_both"] = len(blocks_both)
    res["rock_verts_raw"] = len(rock_raw)
    res["rock_verts_unique"] = len(rock_uni)

    for wname, WSRC in (("sea_only", WATER_SEA), ("sea_plus_beach", WATER_ALL)):
        wv = {}
        for tris in WSRC.values():
            for tr in tris:
                for v in tr[:3]:
                    wv[key(v)] = v
        wverts = list(wv.values())
        for R in (4.0, 8.0, 12.0):
            g = defaultdict(list)
            for v in wverts:
                g[(int(math.floor(v[0] / R)), int(math.floor(v[2] / R)))].append(v)

            def near(v, R=R, g=g):
                cx, cz = int(math.floor(v[0] / R)), int(math.floor(v[2] / R))
                best = None
                for dx in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        for w in g.get((cx + dx, cz + dz), ()):
                            d = math.hypot(v[0] - w[0], v[2] - w[2])
                            if d <= R and (best is None or d < best[0]):
                                best = (d, w)
                return best

            mem_u = [(v, near(v)) for v in rock_uni.values()]
            mem_u = [(v, nb) for v, nb in mem_u if nb]
            raw_n = sum(1 for v in rock_raw if near(v))
            tag = f"{wname}_R{int(R)}"
            row = {"members_unique": len(mem_u), "members_raw": raw_n}
            for cs in (8.0, 16.0, 24.0):
                cells = {(int(math.floor(v[0] / cs)), int(math.floor(v[2] / cs))) for v, _ in mem_u}
                row[f"sites_cell{int(cs)}"] = len(cells)
            # single-link components at 16u plan link
            pts = [v for v, _ in mem_u]
            par = list(range(len(pts)))
            gg = defaultdict(list)
            for i, v in enumerate(pts):
                gg[(int(math.floor(v[0] / 16.0)), int(math.floor(v[2] / 16.0)))].append(i)
            for (cx, cz), idxs in gg.items():
                for dx in (0, 1):
                    for dz in (-1, 0, 1):
                        if dx == 0 and dz < 0:
                            continue
                        for j in gg.get((cx + dx, cz + dz), ()):
                            for i in idxs:
                                if i == j:
                                    continue
                                if math.hypot(pts[i][0] - pts[j][0], pts[i][2] - pts[j][2]) <= 16.0:
                                    uf_union(par, i, j)
            comps = Counter(uf_find(par, i) for i in range(len(pts)))
            row["sites_singlelink16"] = len(comps)
            row["singlelink_size_median"] = sorted(comps.values())[len(comps) // 2] if comps else 0
            row["singlelink_size_max"] = max(comps.values()) if comps else 0
            res[tag] = row
    return res


def stage_B(TERR, WATER_ALL, WATER_SEA, named):
    rows = {}
    for b in named:
        tris = TERR.get(b, [])
        topo = Counter(tr[3] for tr in tris)
        rock = [tr for tr in tris if tr[3] in ROCK]
        steep = [tr for tr in tris if abs(tr[4]) <= 0.2]
        mid = [tr for tr in tris if 0.2 < abs(tr[4]) < 0.5]
        wsea = WATER_SEA.get(b, [])
        wall = WATER_ALL.get(b, [])
        ys = [v[1] for tr in rock for v in tr[:3]]
        rows[str(b)] = {
            "terrain_tris": len(tris), "rock_tris": len(rock),
            "topo_hist": dict(topo.most_common()),
            "near_vertical_tris_le0.2": len(steep),
            "steep_tris_0.2to0.5": len(mid),
            "near_vertical_topo": dict(Counter(tr[3] for tr in steep).most_common()),
            "sea_tris": len(wsea), "water_incl_beach_tris": len(wall),
            "rock_y_min": round(min(ys), 3) if ys else None,
            "rock_y_max": round(max(ys), 3) if ys else None,
            "sea_y_levels": sorted({round(v[1], 3) for tr in wsea for v in tr[:3]})[:6],
        }
    return rows


# ---- stage C / D ----------------------------------------------------------------------------
def context(TERR, b, rad=1):
    (bx, by) = b
    ctx, own = [], []
    for dx in range(-rad, rad + 1):
        for dz in range(-rad, rad + 1):
            nb = (bx + dx, by + dz)
            for tr in TERR.get(nb, ()):
                ctx.append(tr)
                own.append(nb)
    return ctx, own


def edge_pass(TERR, WATER_ALL, OBJ, blocks, steep_thr):
    """Free-edge + seam-edge grammar. Returns (free_recs, seam_recs, counters)."""
    have = set(TERR)
    free_recs, seam_recs = [], []
    cnt = Counter()
    for b in blocks:
        ctx, own = context(TERR, b)
        if not ctx:
            continue
        # edge ownership over the merged context
        edges = defaultdict(list)
        for i, tr in enumerate(ctx):
            k = [key(tr[0]), key(tr[1]), key(tr[2])]
            for a, c in ((0, 1), (1, 2), (2, 0)):
                edges[(min(k[a], k[c]), max(k[a], k[c]))].append(i)
        surf = Grid(ctx, 4.0, want=lambda tr: abs(tr[4]) >= UP)
        steepg = Grid(ctx, 4.0, want=lambda tr: abs(tr[4]) < steep_thr)
        wat = WATER_ALL.get(b, []) + sum((WATER_ALL.get((b[0] + dx, b[1] + dz), [])
                                          for dx in (-1, 0, 1) for dz in (-1, 0, 1)), [])
        wg = Grid(wat, 8.0) if wat else None
        og = None
        objt = sum((OBJ.get((b[0] + dx, b[1] + dz), []) for dx in (-1, 0, 1) for dz in (-1, 0, 1)), [])
        if objt:
            og = Grid(objt, 4.0)
        # index steep faces by endpoint key for the un-stitched seal probe
        by_key = defaultdict(list)
        for i, tr in enumerate(ctx):
            if abs(tr[4]) < steep_thr:
                for v in tr[:3]:
                    by_key[key(v)].append(i)
        # free edges of THIS block only
        freelist = [(e, o) for e, o in edges.items() if len(o) == 1 and own[o[0]] == b]
        freeset = {e for e, _ in freelist}
        for e, o in freelist:
            tr = ctx[o[0]]
            a = (e[0][0] / Q, e[0][1] / Q, e[0][2] / Q)
            c = (e[1][0] / Q, e[1][1] / Q, e[1][2] / Q)
            # map-border: seam plane with the neighbour block absent
            border = False
            for coord, mod, nbs in ((0, 64.0, ((-1, 0), (1, 0))), (2, 64.0, ((0, -1), (0, 1)))):
                if abs(a[coord] % mod) < 1e-6 and abs(c[coord] % mod) < 1e-6:
                    if not any((b[0] + dx, b[1] + dz) in have for dx, dz in nbs):
                        border = True
            if border:
                cnt["free_border"] += 1
                continue
            ymid = 0.5 * (a[1] + c[1])
            px, pz = 0.5 * (a[0] + c[0]), 0.5 * (a[2] + c[2])
            orient = "surface" if abs(tr[4]) >= UP else ("steep" if abs(tr[4]) < steep_thr else "mid")
            # T-join: a collinear overlapping free edge
            tj = False
            dx1, dz1 = c[0] - a[0], c[2] - a[2]
            L = math.hypot(dx1, dz1)
            for e2 in freeset:
                if e2 == e:
                    continue
                if e2[0] != e[0] and e2[1] != e[1] and e2[0] != e[1] and e2[1] != e[0]:
                    continue
                p = (e2[0][0] / Q, e2[0][1] / Q, e2[0][2] / Q)
                q = (e2[1][0] / Q, e2[1][1] / Q, e2[1][2] / Q)
                dx2, dz2 = q[0] - p[0], q[2] - p[2]
                L2 = math.hypot(dx2, dz2)
                if L < 1e-6 or L2 < 1e-6:
                    continue
                cr = abs(dx1 * dz2 - dz1 * dx2) / (L * L2)
                if cr < 1e-3 and abs((q[1] - p[1]) * L - (c[1] - a[1]) * L2) < 1e-3 * max(L, L2):
                    tj = True
                    break
            # un-stitched steep face hanging off an endpoint, descending
            seal_un = None
            for i in by_key.get(e[0], []) + by_key.get(e[1], []):
                lo = min(v[1] for v in ctx[i][:3])
                if lo <= ymid - 0.5:
                    if seal_un is None or lo < seal_un[0]:
                        seal_un = (lo, ctx[i][3])
            below = surf.top_below(px, pz, ymid, 0.5)
            level = surf.near_level(px, pz, ymid, 0.5)
            # outward probe: away from the owner triangle's plan centroid
            gx = (tr[0][0] + tr[1][0] + tr[2][0]) / 3.0
            gz = (tr[0][2] + tr[1][2] + tr[2][2]) / 3.0
            ux, uz = px - gx, pz - gz
            un = math.hypot(ux, uz)
            out_below = None
            if un > 1e-6:
                for d in (0.5, 1.0):
                    ob = surf.top_below(px + ux / un * d, pz + uz / un * d, ymid, 0.5)
                    if ob is not None and (out_below is None or ob[0] > out_below[0]):
                        out_below = ob
            wcov = wg.any_cover(px, pz) if wg else None
            ocov = og.top_at(px, pz) if og else None
            rec = {"block": b, "topo": tr[3], "orient": orient, "y": round(ymid, 3),
                   "len": round(math.hypot(dx1, dz1), 3), "px": round(px, 2), "pz": round(pz, 2)}
            if out_below is not None:
                rec["out_drop"] = round(ymid - out_below[0], 3)
                rec["out_topo"] = out_below[1]
                cnt["outward_ground_below"] += 1
                if seal_un is None and below is None:
                    cnt["outward_ground_below_unsealed_nomid"] += 1
            if tj:
                cls = "tjoin"
            elif below is not None and seal_un is None:
                cls = "HOVER_GROUND"
                rec["below_y"] = round(below[0], 3)
                rec["below_topo"] = below[1]
                rec["drop"] = round(ymid - below[0], 3)
            elif below is not None:
                cls = "sealed_unstitched"
                rec["seal_bottom"] = round(seal_un[0], 3)
                rec["seal_topo"] = seal_un[1]
                rec["below_y"] = round(below[0], 3)
            elif seal_un is not None:
                cls = "sealed_unstitched_nofloor"
                rec["seal_bottom"] = round(seal_un[0], 3)
                rec["seal_topo"] = seal_un[1]
            elif wcov is not None:
                cls = "hover_water"
                rec["water_y"] = round(max(v[1] for v in wcov[:3]), 3)
                rec["above_water"] = round(ymid - max(v[1] for v in wcov[:3]), 3)
            elif ocov is not None and abs(ocov[0] - ymid) <= 0.5:
                cls = "object_seam"
            elif level is not None:
                cls = "level_continuation"
            else:
                cls = "void"
            rec["cls"] = cls
            cnt["free_" + cls] += 1
            cnt["free_total"] += 1
            free_recs.append(rec)
        # seam edges: exactly 2 owners, one surface + one steep-descending
        for e, o in edges.items():
            if len(o) != 2 or own[o[0]] != b:
                continue
            t0, t1 = ctx[o[0]], ctx[o[1]]
            ups = [t for t in (t0, t1) if abs(t[4]) >= UP]
            stp = [t for t in (t0, t1) if abs(t[4]) < steep_thr]
            if len(ups) != 1 or not stp:
                continue
            a = (e[0][0] / Q, e[0][1] / Q, e[0][2] / Q)
            c = (e[1][0] / Q, e[1][1] / Q, e[1][2] / Q)
            ylo = min(a[1], c[1])
            s = stp[0]
            bot = min(v[1] for v in s[:3])
            if bot > ylo - 0.5:
                cnt["seam_up_or_flat"] += 1
                continue
            cnt["seal_edges"] += 1
            seam_recs.append({"block": b, "seal_topo": s[3], "surf_topo": ups[0][3],
                              "surf_foot": ups[0][3] in FOOT_LEGAL,
                              "edge_y": round(ylo, 3), "seal_bottom": round(bot, 3),
                              "drop": round(ylo - bot, 3),
                              "px": round(0.5 * (a[0] + c[0]), 2),
                              "pz": round(0.5 * (a[2] + c[2]), 2)})
    return free_recs, seam_recs, cnt


def selftest(WALL, OBJ):
    """POSITIVE CONTROL -- the scan must FIND a hovering hem when one exists.

    Synthesises, in an unused block slot, a ground sheet at y=0 and a floating slab at
    y=6 whose boundary edges are unshared (the exact shipped defect shape), plus a second
    slab whose edge IS sealed by a curtain quad, and runs the real edge_pass over both.
    """
    def quad(x0, z0, s, y):
        a, b, c, d = (x0, y, z0), (x0 + s, y, z0), (x0 + s, y, z0 + s), (x0, y, z0 + s)
        return [(a, b, c, 0, ny_of(a, b, c)), (a, c, d, 0, ny_of(a, c, d))]

    B = (1, 1)                                                   # not in list_blocks(disc=1)
    ox, oz = B[0] * 64.0, -B[1] * 64.0
    T = []
    T += quad(ox + 8, oz - 56, 48, 0.0)                           # ground sheet
    T += quad(ox + 20, oz - 44, 12, 6.0)                          # FLOATING slab (4 free edges)
    T += quad(ox + 36, oz - 44, 8, 6.0)                           # slab to be sealed
    for (p, q) in (((ox + 36, 6.0, oz - 44), (ox + 44, 6.0, oz - 44)),
                   ((ox + 44, 6.0, oz - 44), (ox + 44, 6.0, oz - 36)),
                   ((ox + 44, 6.0, oz - 36), (ox + 36, 6.0, oz - 36)),
                   ((ox + 36, 6.0, oz - 36), (ox + 36, 6.0, oz - 44))):
        p2 = (p[0], 0.0, p[2])
        q2 = (q[0], 0.0, q[2])
        T.append((p, q, q2, 58, ny_of(p, q, q2)))                  # curtain, shares the edge
        T.append((p, q2, p2, 58, ny_of(p, q2, p2)))
    fake = {B: T}
    fr, sr, cn = edge_pass(fake, WALL, OBJ, [B], 0.5)
    return {"counts": dict(cn),
            "hover_ground": [{k: r[k] for k in ("y", "drop", "below_y", "len")}
                             for r in fr if r["cls"] == "HOVER_GROUND"],
            "seal_edges": len(sr),
            "seal_drops": sorted({r["drop"] for r in sr})}


def stage_E(TERR, WATER_SEA, R=8.0):
    """Per 16u site: min rock y near water vs the local water plane."""
    wv = []
    for tris in WATER_SEA.values():
        for tr in tris:
            for v in tr[:3]:
                wv.append(v)
    g = defaultdict(list)
    for v in wv:
        g[(int(math.floor(v[0] / R)), int(math.floor(v[2] / R)))].append(v)
    sites = defaultdict(lambda: {"ys": [], "wy": []})
    seen = set()
    for tris in TERR.values():
        for tr in tris:
            if tr[3] not in ROCK:
                continue
            for v in tr[:3]:
                k = key(v)
                if k in seen:
                    continue
                seen.add(k)
                cx, cz = int(math.floor(v[0] / R)), int(math.floor(v[2] / R))
                best = None
                for dx in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        for w in g.get((cx + dx, cz + dz), ()):
                            d = math.hypot(v[0] - w[0], v[2] - w[2])
                            if d <= R and (best is None or d < best[0]):
                                best = (d, w)
                if best is None:
                    continue
                s = sites[(int(math.floor(v[0] / 16.0)), int(math.floor(v[2] / 16.0)))]
                s["ys"].append(v[1])
                s["wy"].append(best[1][1])
    rows = []
    for cell, s in sites.items():
        wy = sorted(s["wy"])[len(s["wy"]) // 2]
        rows.append({"cell": cell, "n": len(s["ys"]), "rock_ymin": round(min(s["ys"]), 3),
                     "water_y": round(wy, 3), "delta": round(min(s["ys"]) - wy, 3)})
    return rows


def stage_F(TERR, WATER_SEA, seal_px, R=8.0):
    """Joint (sealed x corridor-cover) per 16u site, cover threshold swept."""
    surf_all = []
    for tris in TERR.values():
        for tr in tris:
            if abs(tr[4]) >= UP:
                surf_all.append(tr)
    SG = Grid(surf_all, 8.0)
    wv = []
    for tris in WATER_SEA.values():
        for tr in tris:
            for v in tr[:3]:
                wv.append(v)
    g = defaultdict(list)
    for v in wv:
        g[(int(math.floor(v[0] / R)), int(math.floor(v[2] / R)))].append(v)
    sites = defaultdict(lambda: {"cov": [], "n": 0, "rock_ymin": 1e9, "wy": []})
    seen = set()
    for tris in TERR.values():
        for tr in tris:
            if tr[3] not in ROCK:
                continue
            for v in tr[:3]:
                k = key(v)
                if k in seen:
                    continue
                seen.add(k)
                cx, cz = int(math.floor(v[0] / R)), int(math.floor(v[2] / R))
                best = None
                for dx in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        for w in g.get((cx + dx, cz + dz), ()):
                            d = math.hypot(v[0] - w[0], v[2] - w[2])
                            if d <= R and (best is None or d < best[0]):
                                best = (d, w)
                if best is None:
                    continue
                s = sites[(int(math.floor(v[0] / 16.0)), int(math.floor(v[2] / 16.0)))]
                s["n"] += 1
                s["rock_ymin"] = min(s["rock_ymin"], v[1])
                s["wy"].append(best[1][1])
                w = best[1]
                ok = 0
                for j in range(1, 8):
                    t = j / 8.0
                    px, pz = v[0] + (w[0] - v[0]) * t, v[2] + (w[2] - v[2]) * t
                    top = SG.top_at(px, pz)
                    if top is not None and top[1] in FOOT_LEGAL:
                        ok += 1
                s["cov"].append(ok / 7.0)
    rows = []
    for cell, s in sites.items():
        sealed = seal_px.get(cell, 0)
        cov = sum(s["cov"]) / len(s["cov"]) if s["cov"] else 0.0
        wy = sorted(s["wy"])[len(s["wy"]) // 2]
        rows.append({"cell": list(cell), "n": s["n"], "sealed_edges": sealed,
                     "cover": round(cov, 3), "rock_ymin": round(s["rock_ymin"], 3),
                     "water_y": round(wy, 3)})
    return rows


def stage_G(TERR, WSEA, WALL, spots):
    """Direct spot reads: plan transects + a water-exposure census (the HIDDEN-WATER claim)."""
    surf, wat = [], []
    for tris in TERR.values():
        for tr in tris:
            surf.append(tr)
    for tris in WSEA.values():
        for tr in tris:
            wat.append(tr)
    SG = Grid([t for t in surf if abs(t[4]) >= UP], 8.0)
    ALLG = Grid(surf, 8.0)
    WG = Grid(wat, 8.0)
    out = {"transects": {}}
    for name, (cx, cz) in spots.items():
        rows = []
        for i in range(-14, 15):
            for axis in ("x", "z"):
                px = cx + i if axis == "x" else cx
                pz = cz if axis == "x" else cz + i
                top = SG.top_at(px, pz)
                anyt = ALLG.top_at(px, pz)
                w = WG.top_at(px, pz)
                rows.append({"axis": axis, "d": i, "px": round(px, 1), "pz": round(pz, 1),
                             "surf_y": None if top is None else round(top[0], 3),
                             "surf_topo": None if top is None else top[1],
                             "any_y": None if anyt is None else round(anyt[0], 3),
                             "any_topo": None if anyt is None else anyt[1],
                             "water_y": None if w is None else round(w[0], 3)})
        out["transects"][name] = rows
    # exposure: is the site's nearest water plan-covered by terrain more than 1u above it?
    wv = []
    for tris in WSEA.values():
        for tr in tris:
            for v in tr[:3]:
                wv.append(v)
    g = defaultdict(list)
    for v in wv:
        g[(int(math.floor(v[0] / 8.0)), int(math.floor(v[2] / 8.0)))].append(v)
    site_w = defaultdict(list)
    seen = set()
    for tris in TERR.values():
        for tr in tris:
            if tr[3] not in ROCK:
                continue
            for v in tr[:3]:
                k = key(v)
                if k in seen:
                    continue
                seen.add(k)
                cxx, czz = int(math.floor(v[0] / 8.0)), int(math.floor(v[2] / 8.0))
                best = None
                for dx in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        for w in g.get((cxx + dx, czz + dz), ()):
                            d = math.hypot(v[0] - w[0], v[2] - w[2])
                            if d <= 8.0 and (best is None or d < best[0]):
                                best = (d, w)
                if best:
                    site_w[(int(math.floor(v[0] / 16.0)),
                            int(math.floor(v[2] / 16.0)))].append(best[1])
    hidden, rows = 0, []
    for cell, ws in site_w.items():
        cov = 0
        for w in ws:
            top = SG.top_below(w[0], w[2], 1e9, -1e9)          # topmost surface anywhere
            if top is not None and top[0] > w[1] + 1.0:
                cov += 1
        frac = 1.0 - cov / len(ws)
        rows.append({"cell": list(cell), "n": len(ws), "exposure": round(frac, 3)})
        if frac < 0.30:
            hidden += 1
    out["exposure"] = {"sites": len(rows), "hidden_lt30pct": hidden,
                       "exposure_median": round(sorted(r["exposure"] for r in rows)[len(rows) // 2], 3),
                       "sites_exposure_lt_1.0": sum(1 for r in rows if r["exposure"] < 1.0)}
    out["exposure_rows_low"] = sorted(rows, key=lambda r: r["exposure"])[:12]
    return out


def main():
    stages = sys.argv[1] if len(sys.argv) > 1 else "ABCDEF"
    res = {"stages": stages}
    TERR = load(("terrain",))
    WSEA = load(SEA_PARTS)
    WALL = load(SEA_PARTS + BEACH_PARTS)
    OBJ = load(("object",))
    res["loaded"] = {"terrain_blocks": len(TERR), "sea_blocks": len(WSEA),
                     "water_beach_blocks": len(WALL), "object_blocks": len(OBJ),
                     "terrain_tris": sum(len(v) for v in TERR.values()),
                     "object_tris": sum(len(v) for v in OBJ.values())}
    print("loaded", res["loaded"], flush=True)

    res["S_selftest"] = selftest(WALL, OBJ)
    print("SELFTEST", json.dumps(res["S_selftest"]), flush=True)

    if "A" in stages:
        res["A_population"] = stage_A(TERR, WSEA, WALL)
        print("A", json.dumps(res["A_population"], indent=1)[:1600], flush=True)

    named = [(12, 11), (13, 16), (13, 17), (15, 1), (16, 1), (16, 5), (16, 6)]
    if "B" in stages:
        res["B_spot"] = stage_B(TERR, WALL, WSEA, named)
        print("B", json.dumps(res["B_spot"], indent=1)[:2500], flush=True)

    # coastal rock blocks = rock topo AND a sea part in the same block, plus the named set
    coastal = sorted({b for b, tris in TERR.items() if any(tr[3] in ROCK for tr in tris)}
                     & set(WALL)) or []
    res["coastal_blocks"] = len(coastal)
    if "C" in stages or "D" in stages or "F" in stages:
        free_recs, seam_recs, cnt = edge_pass(TERR, WALL, OBJ, coastal, 0.5)
        res["C_free_counts"] = dict(cnt)
        res["C_hover_ground"] = [r for r in free_recs if r["cls"] == "HOVER_GROUND"]
        res["C_hover_water"] = [r for r in free_recs if r["cls"] == "hover_water"]
        res["C_free_by_cls_topo"] = {c: dict(Counter(r["topo"] for r in free_recs
                                                     if r["cls"] == c).most_common())
                                     for c in {r["cls"] for r in free_recs}}
        res["C_free_by_cls_orient"] = {c: dict(Counter(r["orient"] for r in free_recs
                                                       if r["cls"] == c).most_common())
                                       for c in {r["cls"] for r in free_recs}}
        print("C", json.dumps(res["C_free_counts"]), flush=True)
        print("C hover_ground", len(res["C_hover_ground"]),
              "hover_water", len(res["C_hover_water"]), flush=True)
        # hover_water is the whole coast hem -- split it by height above the water plane
        hw = res["C_hover_water"]
        hh = sorted(r["above_water"] for r in hw)
        band = Counter()
        for x in hh:
            band["<=0.5" if x <= 0.5 else ("0.5-1" if x <= 1.0 else
                                           ("1-2" if x <= 2.0 else
                                            ("2-4" if x <= 4.0 else ">4")))] += 1
        res["C_hover_water_height_bands"] = dict(band)
        hi = sorted(hw, key=lambda r: -r["above_water"])[:40]
        res["C_hover_water_top40"] = hi
        res["C_hover_water_gt1u_blocks"] = dict(Counter(
            str(r["block"]) for r in hw if r["above_water"] > 1.0).most_common())
        res["C_hover_water_gt1u_unique_xz"] = len({(r["px"], r["pz"]) for r in hw
                                                   if r["above_water"] > 1.0})
        print("C hover_water bands", json.dumps(res["C_hover_water_height_bands"]),
              "gt1u blocks", json.dumps(res["C_hover_water_gt1u_blocks"]), flush=True)
        print("C hover_water >1u:", json.dumps([r for r in hw if r["above_water"] > 1.0]),
              flush=True)
        if hi:
            res["_hw1"] = (hi[0]["px"], hi[0]["pz"])
        # strict-threshold variant (the instrument's |ny|<=0.2 steepness)
        f2, s2, c2 = edge_pass(TERR, WALL, OBJ, coastal, 0.2)
        res["C_free_counts_thr02"] = dict(c2)
        res["C_hover_ground_thr02"] = [r for r in f2 if r["cls"] == "HOVER_GROUND"]
        print("C thr0.2", json.dumps(res["C_free_counts_thr02"]), flush=True)
        res["C_void_edges"] = [r for r in free_recs if r["cls"] == "void"]
        res["C_outward_cases"] = [r for r in free_recs if "out_drop" in r]
        res["C_outward_cases_thr02"] = [r for r in f2 if "out_drop" in r]
        print("C outward cases", json.dumps(res["C_outward_cases"]), flush=True)
        print("C void edges", json.dumps(res["C_void_edges"][:12]), flush=True)
        res["C_unstitched_nofloor_top"] = sorted(
            [r for r in free_recs if r["cls"] == "sealed_unstitched_nofloor"],
            key=lambda r: -r["y"])[:15]
        # seal census restricted to the 16u member-site cells (comparable to the claim)
        site_cells = set()
        wv = []
        for tris in WALL.values():
            for tr in tris:
                for v in tr[:3]:
                    wv.append(v)
        gw = defaultdict(list)
        for v in wv:
            gw[(int(math.floor(v[0] / 8.0)), int(math.floor(v[2] / 8.0)))].append(v)
        seen = set()
        for tris in TERR.values():
            for tr in tris:
                if tr[3] not in ROCK:
                    continue
                for v in tr[:3]:
                    k = key(v)
                    if k in seen:
                        continue
                    seen.add(k)
                    cx, cz = int(math.floor(v[0] / 8.0)), int(math.floor(v[2] / 8.0))
                    for dx in (-1, 0, 1):
                        for dz in (-1, 0, 1):
                            for w in gw.get((cx + dx, cz + dz), ()):
                                if math.hypot(v[0] - w[0], v[2] - w[2]) <= 8.0:
                                    site_cells.add((int(math.floor(v[0] / 16.0)),
                                                    int(math.floor(v[2] / 16.0))))
        res["site_cells_n"] = len(site_cells)
        for tag, recs in (("thr05", seam_recs), ("thr02", s2)):
            sub = [r for r in recs if (int(math.floor(r["px"] / 16.0)),
                                       int(math.floor(r["pz"] / 16.0))) in site_cells]
            res["D_atsites_" + tag] = {
                "seal_edges": len(sub),
                "seal_face_topo": dict(Counter(r["seal_topo"] for r in sub).most_common()),
                "seal_face_footlegal": sum(1 for r in sub if r["seal_topo"] in FOOT_LEGAL),
                "sealed_surface_footlegal": sum(1 for r in sub if r["surf_foot"]),
                "sealed_surface_topo": dict(Counter(r["surf_topo"] for r in sub).most_common(8)),
                "bottom_at_or_below_0.5": sum(1 for r in sub if r["seal_bottom"] <= 0.5),
                "drop_median": sorted(r["drop"] for r in sub)[len(sub) // 2] if sub else None,
                "bottom_median": sorted(r["seal_bottom"] for r in sub)[len(sub) // 2] if sub else None,
            }
            print("D@sites", tag, json.dumps(res["D_atsites_" + tag]), flush=True)

        if "D" in stages:
            d = {"seal_edges": len(seam_recs),
                 "seal_face_topo": dict(Counter(r["seal_topo"] for r in seam_recs).most_common()),
                 "sealed_surface_topo": dict(Counter(r["surf_topo"] for r in seam_recs).most_common()),
                 "sealed_surface_footlegal": dict(Counter(r["surf_foot"] for r in seam_recs)),
                 "drop_quantiles": None, "bottom_vs_water": None}
            drops = sorted(r["drop"] for r in seam_recs)
            if drops:
                q = lambda f: drops[min(len(drops) - 1, int(f * len(drops)))]        # noqa: E731
                d["drop_quantiles"] = {"p25": q(.25), "median": q(.5), "p75": q(.75),
                                       "max": drops[-1]}
            bots = sorted(r["seal_bottom"] for r in seam_recs)
            if bots:
                q = lambda f: bots[min(len(bots) - 1, int(f * len(bots)))]           # noqa: E731
                d["bottom_vs_water"] = {"p25": q(.25), "median": q(.5), "p75": q(.75),
                                        "max": bots[-1],
                                        "at_or_below_0.5": sum(1 for x in bots if x <= 0.5)}
            d2 = {"seal_edges": len(s2),
                  "seal_face_topo": dict(Counter(r["seal_topo"] for r in s2).most_common()),
                  "sealed_surface_topo": dict(Counter(r["surf_topo"] for r in s2).most_common()),
                  "sealed_surface_footlegal": dict(Counter(r["surf_foot"] for r in s2))}
            res["D_seal_thr05"] = d
            res["D_seal_thr02"] = d2
            print("D", json.dumps(d), flush=True)
            print("D thr0.2", json.dumps(d2), flush=True)

        seal_px = Counter()
        for r in seam_recs:
            seal_px[(int(math.floor(r["px"] / 16.0)), int(math.floor(r["pz"] / 16.0)))] += 1
        if "F" in stages:
            rows = stage_F(TERR, WSEA, seal_px)
            res["F_sites"] = rows
            n = len(rows)
            summ = {"sites": n, "sealed_sites": sum(1 for r in rows if r["sealed_edges"] > 0)}
            for thr in (0.60, 0.75, 0.90, 0.95):
                summ[f"cover_ge_{thr}"] = sum(1 for r in rows if r["cover"] >= thr)
                summ[f"wrap_only_ge_{thr}"] = sum(1 for r in rows if r["cover"] >= thr
                                                  and r["sealed_edges"] == 0)
                summ[f"sealed_and_ge_{thr}"] = sum(1 for r in rows if r["cover"] >= thr
                                                   and r["sealed_edges"] > 0)
            covs = sorted(r["cover"] for r in rows)
            if covs:
                q = lambda f: covs[min(len(covs) - 1, int(f * len(covs)))]           # noqa: E731
                summ["cover_quantiles"] = {"p10": q(.1), "p25": q(.25), "median": q(.5),
                                           "p75": q(.75), "p90": q(.9), "max": covs[-1]}
            summ["descent_sites_rock_le_water_plus_0.5"] = sum(
                1 for r in rows if r["rock_ymin"] <= r["water_y"] + 0.5)
            res["F_summary"] = summ
            print("F", json.dumps(summ), flush=True)

    if "E" in stages:
        rows = stage_E(TERR, WSEA)
        res["E_sites"] = rows
        d = sorted(r["delta"] for r in rows)
        q = lambda f: d[min(len(d) - 1, int(f * len(d)))]                            # noqa: E731
        res["E_summary"] = {"sites": len(rows), "delta_p10": q(.1), "delta_median": q(.5),
                            "delta_p90": q(.9), "min": d[0], "max": d[-1],
                            "sites_reaching_water": sum(1 for x in d if x <= 0.5),
                            "sites_above_2u": sum(1 for x in d if x > 2.0)}
        print("E", json.dumps(res["E_summary"]), flush=True)

    if "G" in stages:
        spots = {"claimed_worst_cluster": (867.5, -1097.6),
                 "void_cluster_b6_15": (386.83, -1016.68),
                 "hover_water_edge1": tuple(res.get("_hw1", (867.0, -1097.0))),
                 "b12_11_coast": (12 * 64 + 32.0, -11 * 64 - 40.0),
                 "b16_1_coast": (16 * 64 + 32.0, -1 * 64 - 32.0)}
        res["G"] = stage_G(TERR, WSEA, WALL, spots)
        print("G exposure", json.dumps(res["G"]["exposure"]), flush=True)
        print("G low-exposure sites", json.dumps(res["G"]["exposure_rows_low"]), flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
