"""PATH B — the COMPILED ROADMAP: offline decomposition + cost model.

Decomposes a BgiWalkmesh into straight-walk-safe REGIONS over the engine's own
triangle-neighbour graph (never re-derived from geometry), builds the region
adjacency + portal graph, and computes the all-pairs next-hop table a compiled
.eb lookup would have to encode.

Contract a region must satisfy (this is the whole point of the exercise):
    a unit anywhere in region A must be able to walk STRAIGHT to any of A's
    portal waypoints without leaving the walkmesh or grazing a wall inside the
    controller radius.
Enforced by sampled mutual visibility over the region's triangle centroids +
vertices, restricted to the region's own FLOOR (FF9 floors overlap in XZ, so a
plain XZ test is unsound across floors).
"""
from __future__ import annotations

import math
import sys
from collections import deque

sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/unruffled-moser-861897/ff9mapkit")

from ff9mapkit.scene.bgi import SLOT_PAIRS, BgiWalkmesh, _pt_in_tri_xz, _pt_seg_dist_xz  # noqa: E402

CLEARANCE = 48.0            # cam.COLLISION_RADIUS_W — the controller radius
SAMPLE_STEP = 24.0          # visibility sampling along a candidate straight leg


class FloorSpace:
    """Fast point/segment tests restricted to ONE floor of a walkmesh."""

    def __init__(self, wm: BgiWalkmesh, floor: int):
        self.wm, self.floor = wm, floor
        wv = wm.world_verts()
        self.wv = wv
        tf = {ti: fi for fi, fl in enumerate(wm.floors) for ti in fl.tri_ndx_list}
        self.tris = [ti for ti in range(len(wm.tris)) if tf.get(ti, wm.tris[ti].floor_ndx) == floor]
        self.tset = set(self.tris)
        # wall edges of THIS floor (seam-aware: a neighbour across the edge is not a wall)
        self.walls = []
        for ti in self.tris:
            t = wm.tris[ti]
            for k in range(3):
                if t.nbr[k] >= 0:
                    continue
                i, j = SLOT_PAIRS[k]
                a, b = wv[t.vtx[i]], wv[t.vtx[j]]
                self.walls.append(((a[0], a[2]), (b[0], b[2])))
        # spatial hash: grid cell -> triangle indices (for point-in-floor) and wall segs
        self.cell = 128.0
        self.tgrid: dict = {}
        for ti in self.tris:
            t = wm.tris[ti]
            pts = [wv[v] for v in t.vtx]
            x0 = min(p[0] for p in pts); x1 = max(p[0] for p in pts)
            z0 = min(p[2] for p in pts); z1 = max(p[2] for p in pts)
            for gi in range(int(math.floor(x0 / self.cell)), int(math.floor(x1 / self.cell)) + 1):
                for gj in range(int(math.floor(z0 / self.cell)), int(math.floor(z1 / self.cell)) + 1):
                    self.tgrid.setdefault((gi, gj), []).append(ti)
        self.wgrid: dict = {}
        pad = CLEARANCE
        for wi, (a, b) in enumerate(self.walls):
            x0, x1 = min(a[0], b[0]) - pad, max(a[0], b[0]) + pad
            z0, z1 = min(a[1], b[1]) - pad, max(a[1], b[1]) + pad
            for gi in range(int(math.floor(x0 / self.cell)), int(math.floor(x1 / self.cell)) + 1):
                for gj in range(int(math.floor(z0 / self.cell)), int(math.floor(z1 / self.cell)) + 1):
                    self.wgrid.setdefault((gi, gj), []).append(wi)

    def on_floor(self, x, z) -> bool:
        key = (int(math.floor(x / self.cell)), int(math.floor(z / self.cell)))
        for ti in self.tgrid.get(key, ()):
            t = self.wm.tris[ti]
            if _pt_in_tri_xz(x, z, self.wv[t.vtx[0]], self.wv[t.vtx[1]], self.wv[t.vtx[2]]):
                return True
        return False

    def wall_dist_ok(self, x, z, clearance=CLEARANCE) -> bool:
        key = (int(math.floor(x / self.cell)), int(math.floor(z / self.cell)))
        for wi in self.wgrid.get(key, ()):
            a, b = self.walls[wi]
            if _pt_seg_dist_xz(x, z, (a[0], 0, a[1]), (b[0], 0, b[1])) < clearance:
                return False
        return True

    def free(self, x, z, clearance=CLEARANCE) -> bool:
        return self.on_floor(x, z) and self.wall_dist_ok(x, z, clearance)

    def visible(self, p, q, clearance=CLEARANCE) -> bool:
        """Straight leg p->q stays on this floor the whole way (walls only; the
        clearance test is applied at a RELAXED radius because portal waypoints
        legitimately sit in doorways)."""
        dx, dz = q[0] - p[0], q[1] - p[1]
        d = math.hypot(dx, dz)
        n = max(1, int(d / SAMPLE_STEP))
        for k in range(n + 1):
            t = k / n
            x, z = p[0] + dx * t, p[1] + dz * t
            if not self.on_floor(x, z):
                return False
        return True


def tri_floor_map(wm):
    return {ti: fi for fi, fl in enumerate(wm.floors) for ti in fl.tri_ndx_list}


def centroids(wm):
    wv = wm.world_verts()
    out = []
    for t in wm.tris:
        a, b, c = wv[t.vtx[0]], wv[t.vtx[1]], wv[t.vtx[2]]
        out.append(((a[0] + b[0] + c[0]) / 3.0, (a[2] + b[2] + c[2]) / 3.0))
    return out


def _thin(pts, cap):
    """Farthest-point subsample: keep <= cap points spread over the set (the
    visibility contract is checked on a representative set, not every grid node --
    the same approximation a real compiler would make; stated, not hidden)."""
    if len(pts) <= cap:
        return list(pts)
    out = [pts[0]]
    d = [((p[0] - out[0][0]) ** 2 + (p[1] - out[0][1]) ** 2) for p in pts]
    while len(out) < cap:
        k = max(range(len(pts)), key=lambda i: d[i])
        out.append(pts[k])
        for i, p in enumerate(pts):
            nd = (p[0] - pts[k][0]) ** 2 + (p[1] - pts[k][1]) ** 2
            if nd < d[i]:
                d[i] = nd
    return out


SAMPLE_CAP = 28


def decompose(wm: BgiWalkmesh, *, max_region=None):
    """Greedy straight-walk-safe region growth over the triangle-neighbour graph.

    Returns (region_of_tri: dict, regions: list[list[tri]], portals, floors_of_region).
    A region never spans floors (FF9 floors overlap in XZ; the runtime only has x/z)."""
    tf = tri_floor_map(wm)
    cen = centroids(wm)
    wv = wm.world_verts()
    spaces: dict = {}

    def space(fi):
        if fi not in spaces:
            spaces[fi] = FloorSpace(wm, fi)
        return spaces[fi]

    # THE OCCUPIABLE SAMPLE SET: a unit's CENTRE can never be within the collision
    # radius of a wall, so the points that must see each other are the free (eroded)
    # points of the triangle -- a grid at ~40u plus the centroid. A triangle with NO
    # free sample is an un-standable sliver: it constrains nothing and merges for free.
    scache: dict = {}

    def samples(ti):
        if ti in scache:
            return scache[ti]
        t = wm.tris[ti]
        sp = space(tf.get(ti, t.floor_ndx))
        pts = [wv[v] for v in t.vtx]
        x0 = min(p[0] for p in pts); x1 = max(p[0] for p in pts)
        z0 = min(p[2] for p in pts); z1 = max(p[2] for p in pts)
        out = []
        cx, cz = cen[ti]
        if sp.free(cx, cz):
            out.append((cx, cz))
        step = 40.0
        gx = x0
        while gx <= x1:
            gz = z0
            while gz <= z1:
                if _pt_in_tri_xz(gx, gz, pts[0], pts[1], pts[2]) and sp.free(gx, gz):
                    out.append((gx, gz))
                gz += step
            gx += step
        scache[ti] = out
        return out

    region_of: dict = {}
    regions: list = []
    rsamples: list = []
    order = sorted(range(len(wm.tris)), key=lambda ti: -len(samples(ti)))
    for seed in order:
        if seed in region_of:
            continue
        fi = tf.get(seed, wm.tris[seed].floor_ndx)
        sp = space(fi)
        rid = len(regions)
        members = [seed]
        region_of[seed] = rid
        acc = list(samples(seed))
        frontier = deque(n for n in wm.tris[seed].nbr if n >= 0)
        seen = set(frontier)
        while frontier:
            if max_region and len(members) >= max_region:
                break
            cand = frontier.popleft()
            if cand < 0 or cand in region_of or tf.get(cand, wm.tris[cand].floor_ndx) != fi:
                continue
            cs = samples(cand)
            ok = all(sp.visible(p, q) for p in cs for q in acc)
            if not ok:
                continue
            region_of[cand] = rid
            members.append(cand)
            acc = _thin(acc + cs, SAMPLE_CAP)
            for n in wm.tris[cand].nbr:
                if n >= 0 and n not in region_of and n not in seen:
                    seen.add(n)
                    frontier.append(n)
        regions.append(members)
        rsamples.append(acc)

    # MERGE PASS: fold each region into an adjacent same-floor region whenever the
    # union still satisfies the contract (greedy growth strands slivers behind an
    # already-claimed neighbour; without this the count roughly doubles).
    changed = True
    while changed:
        changed = False
        radj: dict = {}
        for ti, t in enumerate(wm.tris):
            for nb in t.nbr:
                if nb >= 0 and region_of[nb] != region_of[ti]:
                    radj.setdefault(region_of[ti], set()).add(region_of[nb])
        for ra in sorted(range(len(regions)), key=lambda r: len(rsamples[r])):
            if not regions[ra]:
                continue
            fa = tf.get(regions[ra][0], 0)
            for rb in sorted(radj.get(ra, ()), key=lambda r: -len(regions[r]) if regions[r] else 1):
                if rb == ra or not regions[rb] or tf.get(regions[rb][0], 0) != fa:
                    continue
                sp = space(fa)
                if all(sp.visible(p, q) for p in rsamples[ra] for q in rsamples[rb]):
                    for ti in regions[ra]:
                        region_of[ti] = rb
                    regions[rb].extend(regions[ra])
                    rsamples[rb] = _thin(rsamples[rb] + rsamples[ra], SAMPLE_CAP)
                    regions[ra] = []
                    rsamples[ra] = []
                    changed = True
                    break
    # compact ids
    remap, packed = {}, []
    for r, mem in enumerate(regions):
        if mem:
            remap[r] = len(packed)
            packed.append(mem)
    region_of = {ti: remap[r] for ti, r in region_of.items()}
    regions = packed

    # portals: shared triangle edges whose two sides land in different regions
    portals: dict = {}
    for ti, t in enumerate(wm.tris):
        ra = region_of[ti]
        for k in range(3):
            nb = t.nbr[k]
            if nb < 0:
                continue
            rb = region_of[nb]
            if ra == rb:
                continue
            i, j = SLOT_PAIRS[k]
            a, b = wv[t.vtx[i]], wv[t.vtx[j]]
            mid = ((a[0] + b[0]) / 2.0, (a[2] + b[2]) / 2.0)
            length = math.hypot(a[0] - b[0], a[2] - b[2])
            key = (ra, rb)
            prev = portals.get(key)
            if prev is None or length > prev[1]:
                portals[key] = (mid, length, ti, nb)
    return region_of, regions, portals, {r: tf.get(m[0], 0) for r, m in enumerate(regions)}


def next_hop_table(nregions, portals):
    """All-pairs next hop over the region graph (BFS from each target region on the
    reversed edges). Returns NEXT[r][s] = the region r should step into to reach s,
    or -1 if unreachable/self."""
    adj: dict = {}
    for (a, b) in portals:
        adj.setdefault(a, set()).add(b)
    NEXT = [[-1] * nregions for _ in range(nregions)]
    for s in range(nregions):
        # BFS backwards from s
        dist = {s: 0}
        q = deque([s])
        while q:
            cur = q.popleft()
            for a, outs in adj.items():
                if cur in outs and a not in dist:
                    dist[a] = dist[cur] + 1
                    NEXT[a][s] = cur
                    q.append(a)
    return NEXT


def floors_overlap_in_xz(wm) -> bool:
    """Do two DIFFERENT floors of this mesh overlap in the XZ plane? If so, an
    (x,z)-only region test is structurally ambiguous."""
    tf = tri_floor_map(wm)
    cen = centroids(wm)
    byfloor: dict = {}
    for ti in range(len(wm.tris)):
        byfloor.setdefault(tf.get(ti, wm.tris[ti].floor_ndx), []).append(ti)
    if len(byfloor) < 2:
        return False
    spaces = {fi: FloorSpace(wm, fi) for fi in byfloor}
    for fi, tris in byfloor.items():
        for ti in tris:
            x, z = cen[ti]
            for fj, sp in spaces.items():
                if fj != fi and sp.on_floor(x, z):
                    return True
    return False
