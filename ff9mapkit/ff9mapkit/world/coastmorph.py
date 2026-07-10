"""ff9mapkit.world.coastmorph -- CLIFF-COAST MORPHS on verbatim transplants (the coast-morph pillar).

In-game proven 2026-07-09 on donor (7,17)'s NE cliff (base-outline window x 492..508, pure
sea4 seaward): rung 1 = :func:`cliff_bump` (a <=2.5u conforming bow, VertexDisplace on land +
SeaBump on water) and rung 2 = :func:`cliff_headland` (a structural promontory -- the window's
wall quads are REBUILT over a sin^2-pushed outline with one inserted column per gap).

The laws this module encodes (each byte-measured, then in-game proven):

* **Column quantization** -- a cliff wall's texture advances exactly ONE 64px rock tile per
  column and the rock strip is exactly 4 tiles, so the U-ramp with wrap is DETERMINISTIC: a
  legal wall rebuild keeps interior column count ``k = old-k (mod 4)`` (one inserted column
  per gap needs a window whose gap count is a multiple of 4).
* **Drop, don't drag** -- every tri touching a moved vert is dropped and re-filled natively;
  a survivor whose vert drags smears its tile (the sunburst class). The displace tweak then
  gates that ZERO survivors reference moved verts.
* **Native grass fill** -- the wedge re-fills on the 4u lattice with per-cell mains
  quadrant+rotation (avoid-same vs real neighbours) via :func:`grassland.mains_uv`; gated by
  the CRACK GATE (fill once-edges == region boundary segments exactly) and the GRAIN GATE
  (no edge over 6.6u).
* **Water never drags, never clamps** -- moved water verts re-evaluate through the tile's own
  affine (:class:`transplant.SeaBump`); the rebuilt shore ring is a ZIP STRIP (short tris
  outline<->outer-boundary, the real conforming-fan structure), each tri carrying ONE dropped
  tile's affine UNCLAMPED. Gated by the WATER DENSITY GATE (uv-from-world singular values
  inside the real tiles' envelope) and the exact area LEDGER (dropped - emitted == wedge).

Both builders return a tweak list for :func:`transplant.transplant`; every build-time gate
raises ``ValueError`` with the failing law, mirroring ``build_grow_tweaks``.
"""
from __future__ import annotations

import math
from collections import defaultdict

from . import grassland as G
from . import transplant as TR
from .extract import decode_id
from .island import _delaunay

#: the real terrain grain ceiling (max tri edge); longer fill edges read as stretch
MAX_GRAIN = 6.6
#: the free-base law's waterline band -- a cliff base edge tops out below this Y
BASE_Y_MAX = 0.75


def _pk(p, kd: int = 4):
    return (round(p[0], kd), round(p[1], kd), round(p[2], kd))


def _key_set(t3):
    return frozenset(_pk(v[0]) for v in t3)


def _pip_xz(px, pz, t3):
    (ax, _, az), (bx, _, bz), (cx, _, cz) = (v[0] for v in t3)
    d1 = (px - bx) * (az - bz) - (ax - bx) * (pz - bz)
    d2 = (px - cx) * (bz - cz) - (bx - cx) * (pz - cz)
    d3 = (px - ax) * (cz - az) - (cx - ax) * (pz - az)
    neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (neg and pos)


def _in_poly(px, pz, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        (x1, z1), (x2, z2) = poly[i], poly[(i + 1) % n]
        if (z1 > pz) != (z2 > pz):
            if px < x1 + (pz - z1) / (z2 - z1) * (x2 - x1):
                inside = not inside
    return inside


def _boundary_loop(tris):
    """The dropped set's hole boundary as a directed vertex-key loop (edge-count == 1),
    plus position/uv/normal lookups. Raises on a non-manifold or multi-loop boundary."""
    e_count = defaultdict(int)
    e_dir = {}
    pos_of, uv_of, nrm_of = {}, {}, {}
    for t3 in tris:
        ps = [v[0] for v in t3]
        for v in t3:
            pos_of.setdefault(_pk(v[0]), v[0])
            uv_of.setdefault(_pk(v[0]), v[2])
            nrm_of.setdefault(_pk(v[0]), v[1])
        for i in range(3):
            a, b = _pk(ps[i]), _pk(ps[(i + 1) % 3])
            e_count[frozenset((a, b))] += 1
            e_dir.setdefault(frozenset((a, b)), (a, b))
    nxt = {}
    for e, c in e_count.items():
        if c == 1:
            a, b = e_dir[e]
            if a in nxt:
                raise ValueError("non-manifold hole boundary (a drop-set pinch)")
            nxt[a] = b
    loop = [next(iter(nxt))]
    while True:
        n = nxt[loop[-1]]
        if n == loop[0]:
            break
        loop.append(n)
    if len(loop) != len(nxt):
        raise ValueError(f"the drop set's hole has {len(nxt) - len(loop)} extra boundary "
                         f"edges (multiple loops) -- the morph window must be one region")
    return loop, pos_of, uv_of, nrm_of


class CliffWindow:
    """A run of a donor's cliff-base outline, decoded from the real bytes: ordered base
    columns, their crease partners, the wall quads between them, and the seaward normal."""

    def __init__(self, donor, start, end, *, disc: int = 1, lod: str = "0_1", game=None):
        (dbx, dby) = donor
        self.donor = (dbx, dby)
        self.terr = TR.world_tris(dbx, dby, "terrain", disc=disc, lod=lod, game=game)
        self.sea4 = TR.world_tris(dbx, dby, "sea4", disc=disc, lod=lod, game=game)
        topo = lambda t3: decode_id(int(round(t3[0][3][0])))["topograph"]
        self.cliff = [t for t in self.terr if topo(t) == 58]
        self.grass = [t for t in self.terr if topo(t) == 0]
        if not self.cliff:
            raise ValueError(f"donor {donor} has no topo-58 cliff band")

        # classify cliff edges: interior / crease (shared with land) / frame / base (free, Y~0)
        cnt = defaultdict(int)
        for t3 in self.cliff:
            ps = [v[0] for v in t3]
            for i in range(3):
                cnt[frozenset((_pk(ps[i]), _pk(ps[(i + 1) % 3])))] += 1
        land_edges = set()
        for t3 in self.terr:
            if topo(t3) == 58:
                continue
            ps = [v[0] for v in t3]
            for i in range(3):
                land_edges.add(frozenset((_pk(ps[i]), _pk(ps[(i + 1) % 3]))))
        x0, x1 = 64.0 * dbx, 64.0 * dbx + 64.0
        z0, z1 = -64.0 * dby - 64.0, -64.0 * dby

        def on_frame(a, b, eps=0.02):
            for ax, lo, hi in ((0, x0, x1), (2, z0, z1)):
                for plane in (lo, hi):
                    if abs(a[ax] - plane) < eps and abs(b[ax] - plane) < eps:
                        return True
            return False
        base_edges = [e for e, c in cnt.items()
                      if c == 1 and e not in land_edges
                      and not on_frame(*tuple(e))
                      and max(a[1] for a in e) < BASE_Y_MAX]

        # chain the base edges, walk the chain between the snapped endpoints
        adj = defaultdict(list)
        for e in base_edges:
            a, b = tuple(e)
            adj[a].append(b)
            adj[b].append(a)
        pos_of = {}
        for t3 in self.cliff:
            for v in t3:
                pos_of.setdefault(_pk(v[0]), v[0])

        def snap(p):
            best, bd = None, 0.6
            for k in adj:
                d = math.hypot(pos_of[k][0] - p[0], pos_of[k][2] - p[1])
                if d < bd:
                    best, bd = k, d
            if best is None:
                raise ValueError(f"no cliff-base outline vert within 0.6u of {p}")
            return best
        ks, ke = snap(start), snap(end)
        chain = None
        for first in adj[ks]:                       # a mid-chain start walks either way
            trial, prev = [ks, first], ks
            while trial[-1] != ke and len(trial) <= 4096:
                nxts = [n for n in adj[trial[-1]] if n != prev]
                if not nxts:
                    break
                prev = trial[-1]
                trial.append(nxts[0])
            if trial[-1] == ke:
                chain = trial
                break
        if chain is None:
            raise ValueError("start/end are not on one connected cliff-base run")
        if len(chain) < 3:
            raise ValueError("the morph window needs at least 2 base-outline gaps")
        self.base = [pos_of[k] for k in chain]

        # crease partner per column = the nearest elevated cliff vert connected by an edge
        elevated = {}
        for e, c in cnt.items():
            a, b = tuple(e)
            for p, q in ((a, b), (b, a)):
                if p in set(chain) and q not in adj and pos_of.get(q, (0, 99, 0))[1] > BASE_Y_MAX:
                    elevated.setdefault(p, []).append(q)
        self.crease = []
        for k, bp in zip(chain, self.base):
            cands = elevated.get(k, [])
            if not cands:
                raise ValueError(f"base vert {bp} has no crease partner (not a one-quad wall?)")
            self.crease.append(pos_of[min(
                cands, key=lambda q: (pos_of[q][0] - bp[0]) ** 2 + (pos_of[q][2] - bp[2]) ** 2)])

        # the wall between consecutive columns: a clean 2-tri QUAD, or a REFINED gap -- the
        # real vocabulary includes crease-refinement verts (a crease vert with no base
        # partner, carrying the half-step U: e.g. (7,17)'s (482, 2.41, -1111.2) at 0.7305
        # between 0.7617 and 0.6992). The column quantization holds ACROSS a refined gap
        # (one tile per column), so the mod-4 law is unaffected; refined verts simply
        # vanish into the drops and the rebuilt wall is clean quads.
        self.quads = []           # per gap: the wall tris (2 for clean, 2+n for refined)
        self.refined = []         # per gap: the refined crease verts, ordered along it
        for i in range(len(self.base) - 1):
            bl, cl = self.base[i], self.crease[i]
            br, cr = self.base[i + 1], self.crease[i + 1]
            roles = {_pk(bl), _pk(cl), _pk(br), _pk(cr)}
            tris = [t for t in self.cliff if _key_set(t) <= roles]
            extra = []
            if len(tris) != 2:
                # gather elevated verts whose plan projection falls strictly inside the gap
                ex, ez = br[0] - bl[0], br[2] - bl[2]
                L2 = ex * ex + ez * ez or 1.0
                mids = {}
                for t3 in self.cliff:
                    ks = _key_set(t3)
                    if not (ks & {_pk(bl), _pk(br)}):
                        continue
                    ok, cand = True, []
                    for v in t3:
                        k = _pk(v[0])
                        if k in roles:
                            continue
                        tt = ((v[0][0] - bl[0]) * ex + (v[0][2] - bl[2]) * ez) / L2
                        if v[0][1] > BASE_Y_MAX and 0.02 < tt < 0.98:
                            cand.append((tt, v[0]))
                        else:
                            ok = False
                            break
                    if ok:
                        for tt, p in cand:
                            mids[_pk(p)] = (tt, p)
                roles_ext = roles | set(mids)
                tris = [t for t in self.cliff if _key_set(t) <= roles_ext
                        and _key_set(t) & {_pk(bl), _pk(br)}]
                extra = [p for (tt, p) in sorted(mids.values())]
                if len(tris) != 2 + len(extra) or not extra:
                    raise ValueError(f"window gap {i} is neither a clean one-quad wall nor "
                                     f"a refined fan ({len(tris)} tris, "
                                     f"{len(extra)} refined verts)")
            self.quads.append(tris)
            self.refined.append(extra)
        # the FULL old crease chain (columns + refinement verts, in order) -- the grass
        # splice and footprint must follow the real crease line
        self.crease_chain = []
        for i in range(len(self.base) - 1):
            self.crease_chain.append(self.crease[i])
            self.crease_chain.extend(self.refined[i])
        self.crease_chain.append(self.crease[-1])

        # the seaward normal: perpendicular to the window chord, away from the cliff centroid
        t = (self.base[-1][0] - self.base[0][0], self.base[-1][2] - self.base[0][2])
        tl = math.hypot(*t) or 1.0
        nh = (-t[1] / tl, t[0] / tl)
        cc = (sum(v[0][0] for t3 in self.cliff for v in t3) / (3 * len(self.cliff)),
              sum(v[0][2] for t3 in self.cliff for v in t3) / (3 * len(self.cliff)))
        mid = self.base[len(self.base) // 2]
        if ((mid[0] + nh[0] - cc[0]) ** 2 + (mid[2] + nh[1] - cc[1]) ** 2
                < (mid[0] - nh[0] - cc[0]) ** 2 + (mid[2] - nh[1] - cc[1]) ** 2):
            nh = (-nh[0], -nh[1])
        self.nhat = nh

    def moved(self, p, d):
        return (p[0] + d * self.nhat[0], p[1], p[2] + d * self.nhat[1])

    def arc_params(self):
        """Each column's arc-length parameter (0..1) along the base chain."""
        acc, out = 0.0, [0.0]
        for a, b in zip(self.base, self.base[1:]):
            acc += math.dist(a, b)
            out.append(acc)
        return [s / acc for s in out]


def _count_instances(win, keys, exclude_sets=()):
    exclude = set(exclude_sets)
    n = 0
    for tris in (win.terr, win.sea4):
        for t3 in tris:
            if _key_set(t3) in exclude:
                continue
            n += sum(_pk(v[0]) in keys for v in t3)
    return n


def _assert_pure_sea4(win, keyed, *, disc, lod, game):
    """The window's moved waterline verts may touch ONLY terrain + sea4 -- a coincident vert
    in another water part would stay behind under the part-scoped tweaks = a weld crack."""
    for part in ("sea1", "sea2", "sea3", "sea5", "beach1"):
        tris = TR.world_tris(*win.donor, part, disc=disc, lod=lod, game=game)
        n = sum(_pk(v[0]) in keyed for t3 in tris for v in t3)
        if n:
            raise ValueError(f"the morph window's waterline touches {part} ({n} vert "
                             f"instance(s)) -- cliff morphs need a pure-sea4 shore "
                             f"(the cliff seam law); pick a different run")


def _grass_fill(win, drop_grass, new_crease, ck, cell_quad):
    """The native lattice fill over one drop set's hole + wedge: hole boundary spliced with
    the new crease chain, 4u interior lattice, Delaunay, per-cell mains, crack + grain
    gates. Raises ValueError when the gates cannot be satisfied (the caller's ring-extension
    ladder then deepens the drop set and retries)."""
    gloop, gpos, _guv, gnrm = _boundary_loop(drop_grass)
    for k in (ck[0], ck[-1]):
        if k not in gloop:
            raise ValueError("window crease end not on the grass hole boundary")
    # the splice follows the FULL old crease chain (columns + refinement verts)
    crease_run = [_pk(p) for p in win.crease_chain]
    nrun = len(crease_run)
    for k in (crease_run[0], crease_run[-1]):
        i0 = gloop.index(k)
        rot = gloop[i0:] + gloop[:i0]
        if all(rot[i] == crease_run[i] for i in range(nrun)):
            gloop = rot
            break
        if all(rot[i] == crease_run[-1 - i] for i in range(nrun)):
            gloop = rot
            crease_run = list(reversed(crease_run))
            break
    else:
        raise ValueError("crease run not contiguous on the grass hole boundary")
    outer_cr = new_crease if crease_run[0] == ck[0] else list(reversed(new_crease))
    bpts3 = list(outer_cr) + [gpos[k] for k in gloop[nrun:]]
    poly2 = [(p[0], p[2]) for p in bpts3]

    def lattice_interior(clearance):
        pts = []
        xs = [p[0] for p in poly2]
        zs = [p[1] for p in poly2]
        for gx in range(int(min(xs) // 4) - 1, int(max(xs) // 4) + 2):
            for gz in range(int(min(zs) // 4) - 1, int(max(zs) // 4) + 2):
                px, pz = 4.0 * gx, 4.0 * gz
                if not _in_poly(px, pz, poly2):
                    continue
                clear = True
                for k in range(len(poly2)):
                    (x1, z1), (x2, z2) = poly2[k], poly2[(k + 1) % len(poly2)]
                    ex, ez = x2 - x1, z2 - z1
                    L2 = ex * ex + ez * ez or 1.0
                    tt = max(0.0, min(1.0, ((px - x1) * ex + (pz - z1) * ez) / L2))
                    if math.hypot(px - (x1 + tt * ex), pz - (z1 + tt * ez)) < clearance:
                        clear = False
                        break
                if clear:
                    pts.append((px, pz))
        return pts

    def idw_y(px, pz):
        num = den = 0.0
        for p in bpts3:
            w = 1.0 / ((px - p[0]) ** 2 + (pz - p[2]) ** 2 + 1e-6)
            num += w * p[1]
            den += w
        return num / den

    def near_nrm(px, pz):
        best, bd = None, 1e18
        for p in bpts3:
            d2 = (px - p[0]) ** 2 + (pz - p[2]) ** 2
            if d2 < bd:
                best, bd = p, d2
        return gnrm.get(_pk(best), (0.0, 1.0, 0.0))
    idall_grass = tuple(drop_grass[0][0][3])
    poly_edges = {frozenset((_pk(bpts3[i]), _pk(bpts3[(i + 1) % len(bpts3)])))
                  for i in range(len(bpts3))}

    def build_fill(clearance):
        interior = lattice_interior(clearance)
        pts3 = list(bpts3) + [(px, idw_y(px, pz) + (TR._h01(px, pz) - 0.5) * 0.4, pz)
                              for (px, pz) in interior]
        nrms = [gnrm.get(_pk(p)) or near_nrm(p[0], p[2]) for p in bpts3] \
               + [near_nrm(px, pz) for (px, pz) in interior]
        emit = []
        fill_quad = {}
        xz = [(p[0], p[2]) for p in pts3]
        for (ia, ib, ic) in sorted(_delaunay(xz)):
            tri_pts = [pts3[k] for k in (ia, ib, ic)]
            tri_nrm = [nrms[k] for k in (ia, ib, ic)]
            cx = sum(p[0] for p in tri_pts) / 3.0
            cz = sum(p[2] for p in tri_pts) / 3.0
            if not _in_poly(cx, cz, poly2):
                continue
            cell = (math.floor(cx / 4.0), math.floor(cz / 4.0))
            if cell not in fill_quad:
                avoid = {cell_quad.get((cell[0], cell[1] - 1)),
                         cell_quad.get((cell[0] - 1, cell[1])),
                         cell_quad.get((cell[0] + 1, cell[1])),
                         cell_quad.get((cell[0], cell[1] + 1)),
                         fill_quad.get((cell[0], cell[1] - 1)),
                         fill_quad.get((cell[0] - 1, cell[1])),
                         fill_quad.get((cell[0] + 1, cell[1])),
                         fill_quad.get((cell[0], cell[1] + 1))}
                choices = [q for q in ((0, 0), (0, 1), (1, 0), (1, 1)) if q not in avoid] \
                          or [(0, 0), (0, 1), (1, 0), (1, 1)]
                h = TR._h01(4.0 * cell[0] + 1.7, 4.0 * cell[1] + 2.3)
                fill_quad[cell] = choices[int(h * len(choices)) % len(choices)]
            ori = (0, 90, 180, 270)[int(TR._h01(4.0 * cell[0] + 3.1,
                                                4.0 * cell[1] + 0.9) * 4) % 4]
            tri = [(p, nr, tuple(G.mains_uv(p[0], p[2], cell, fill_quad[cell], ori)),
                    idall_grass) for p, nr in zip(tri_pts, tri_nrm)]
            ux, uz = tri[1][0][0] - tri[0][0][0], tri[1][0][2] - tri[0][0][2]
            vx, vz = tri[2][0][0] - tri[0][0][0], tri[2][0][2] - tri[0][0][2]
            if uz * vx - ux * vz <= 0:
                tri = [tri[0], tri[2], tri[1]]
            emit.append(tri)
        # THE CRACK GATE: fill once-edges must equal the region boundary exactly
        fe_count = defaultdict(int)
        for t3 in emit:
            ps = [v[0] for v in t3]
            for i in range(3):
                fe_count[frozenset((_pk(ps[i]), _pk(ps[(i + 1) % 3])))] += 1
        fill_once = {e for e, c in fe_count.items() if c == 1}
        return emit, fill_once

    # THE CLEARANCE LADDER: a wiggly composed boundary can steal Delaunay edges from a
    # too-close interior point (T-junction cracks); retry with wider clearance. 1.4 first
    # keeps the proven single-lobe fills byte-identical.
    grass_emit = None
    for clearance in (1.4, 1.9, 2.4, 2.9):
        emit, fill_once = build_fill(clearance)
        if fill_once == poly_edges:
            grass_emit = emit
            break
    if grass_emit is None:
        miss = [" -- ".join(f"({a[0]:.1f},{a[2]:.1f})" for a in sorted(e))
                for e in list(poly_edges - fill_once)[:4]]
        raise ValueError(f"CRACK GATE: the grass fill's boundary does not match the region "
                         f"at any interior clearance ({len(fill_once - poly_edges)} extra / "
                         f"{len(poly_edges - fill_once)} missing edges = T-junction cracks; "
                         f"missing: {miss})")
    longest = max(max(math.dist(t3[i][0], t3[(i + 1) % 3][0]) for i in range(3))
                  for t3 in grass_emit)
    if longest > MAX_GRAIN:
        raise ValueError(f"GRAIN GATE: a grass fill edge is {longest:.1f}u (> {MAX_GRAIN}) -- "
                         f"off the real terrain grain, reads as stretch")

    return grass_emit


def beach_bump(donor, start, end, depth, *, disc: int = 1, lod: str = "0_1", game=None):
    """The BEACH conforming bow -- the waterline move on a sandy shore (the beach frontier's
    rung 1). A beach is an INTERLEAVED RAMP ASSEMBLY: sand terrain -> beach1 foam (the swash
    ribbon, Y 0.2..1.2) -> sea2 wash, welded at two chains -- the WATERLINE (beach1's seaward
    boundary, every vert shared bit-exact with sea2) and the SAND SEAM (shared with terrain),
    with load-bearing multi-part END-CAP welds. The bow displaces interior WATERLINE verts
    (sin^2 profile, + = seaward) in BOTH welded parts: the FOAM drags verbatim (it is
    edge-anchored -- the swash ribbon's width varies 3.3-6.7u naturally, so foam strain is
    real behaviour and the white band must follow the line), but the sea2 WASH re-evaluates
    through its own tile map (:class:`transplant.SeaBump`) -- dragged wash UVs smush the
    water pattern (in-game 2026-07-10, the cliff-bump lesson repeating on the beach: WATER
    NEVER DRAGS, on any band). Gates: end-caps must stay fixed, the ribbon must stay inside
    the real width envelope, and no touched tile may fold."""
    from .extract import decode_id as _did
    beach = TR.world_tris(*donor, "beach1", disc=disc, lod=lod, game=game)
    if not beach:
        raise ValueError(f"donor {donor} has no beach1 mesh -- not a sandy shore")
    others = {p: TR.world_tris(*donor, p, disc=disc, lod=lod, game=game)
              for p in ("terrain", "sea1", "sea2", "sea3", "sea5", "sea4")}
    reg = {name: {_pk(v[0]) for t3 in tris for v in t3} for name, tris in others.items()}

    # beach1's boundary loop -> the waterline run (sea2-welded) vs the sand seam
    e_count = defaultdict(int)
    pos_of = {}
    for t3 in beach:
        ps = [v[0] for v in t3]
        for v in t3:
            pos_of.setdefault(_pk(v[0]), v[0])
        for i in range(3):
            e_count[frozenset((_pk(ps[i]), _pk(ps[(i + 1) % 3])))] += 1
    adj = defaultdict(list)
    for e, c in e_count.items():
        if c == 1:
            a, b = tuple(e)
            adj[a].append(b)
            adj[b].append(a)

    def snap(p):
        best, bd = None, 0.8
        for k in adj:
            d = math.hypot(pos_of[k][0] - p[0], pos_of[k][2] - p[1])
            if d < bd:
                best, bd = k, d
        if best is None:
            raise ValueError(f"no beach1 boundary vert within 0.8u of {p}")
        return best
    ks, ke = snap(start), snap(end)
    chain = None
    for first in adj[ks]:
        trial, prev = [ks, first], ks
        while trial[-1] != ke and len(trial) <= 4096:
            nxts = [n for n in adj[trial[-1]] if n != prev]
            if not nxts:
                break
            prev = trial[-1]
            trial.append(nxts[0])
        if trial[-1] == ke:
            # prefer the WATERLINE side: every interior vert sea2-welded, none terrain-welded
            if all(k in reg["sea2"] and k not in reg["terrain"] for k in trial[1:-1]):
                chain = trial
                break
    if chain is None:
        raise ValueError("start/end do not bound a waterline run (interior verts must be "
                         "sea2-welded and terrain-free -- pick the foam line, not the sand "
                         "seam, and keep end-caps outside the interior)")
    pts = [pos_of[k] for k in chain]

    # seaward normal: away from the sand centroid
    sand = [t for t in others["terrain"] if _did(int(round(t[0][3][0])))["topograph"] == 31]
    src = sand or others["terrain"]
    cc = (sum(v[0][0] for t3 in src for v in t3) / (3 * len(src)),
          sum(v[0][2] for t3 in src for v in t3) / (3 * len(src)))
    t = (pts[-1][0] - pts[0][0], pts[-1][2] - pts[0][2])
    tl = math.hypot(*t) or 1.0
    nh = (-t[1] / tl, t[0] / tl)
    mid = pts[len(pts) // 2]
    if ((mid[0] + nh[0] - cc[0]) ** 2 + (mid[2] + nh[1] - cc[1]) ** 2
            < (mid[0] - nh[0] - cc[0]) ** 2 + (mid[2] - nh[1] - cc[1]) ** 2):
        nh = (-nh[0], -nh[1])

    acc, arcs = 0.0, [0.0]
    for a, b in zip(pts, pts[1:]):
        acc += math.dist(a, b)
        arcs.append(acc)

    # THE LADDER TAPER (in-game 2026-07-10: a waterline-only bow pinches the sea2 wash band
    # OUT of the real width envelope -- 4.0u -> 0.8u at the apex, tilt x3 -- so the band
    # boundary reads as a hard seam; real shores keep band widths in PROPORTION). The bow is
    # a decaying FIELD: the waterline moves d(s); every SEAWARD water vert within reach moves
    # d(s) * cos^2-taper of its cross-shore distance, so each band compresses only
    # fractionally and the ladder keeps its real statistics. Weld-safe by construction: the
    # delta is a pure function of position, so shared band-boundary verts agree across parts.
    # the reach scales with depth: max cross-shore strain = depth*pi/(2*reach), so reach =
    # depth*pi/(2*0.16) caps every tile's strain at ~16% (round-3's fixed 12u reach gave
    # ~33% at D=2.5 -- the strain gate caught it)
    TAPER_REACH = max(12.0, abs(depth) * math.pi / 0.32)

    def chain_param(p):
        """(along-shore profile displacement d(s), signed cross-shore distance f)."""
        best, bs, bf = 1e18, 0.0, 0.0
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            ex, ez = b[0] - a[0], b[2] - a[2]
            L2 = ex * ex + ez * ez or 1.0
            tt = max(0.0, min(1.0, ((p[0] - a[0]) * ex + (p[2] - a[2]) * ez) / L2))
            qx, qz = a[0] + tt * ex, a[2] + tt * ez
            d2 = (p[0] - qx) ** 2 + (p[2] - qz) ** 2
            if d2 < best:
                best = d2
                bs = arcs[i] + tt * (arcs[i + 1] - arcs[i])
                side = (p[0] - qx) * nh[0] + (p[2] - qz) * nh[1]
                bf = math.copysign(math.sqrt(d2), side)
        return depth * math.sin(math.pi * bs / acc) ** 2, bf

    moves = {}                                    # the waterline chain (foam side, factor 1)
    for i in range(1, len(pts) - 1):
        d = depth * math.sin(math.pi * arcs[i] / acc) ** 2
        moves[pts[i]] = (d * nh[0], 0.0, d * nh[1])
    water_moves = dict(moves)                     # + the tapered seaward field
    for name in ("sea1", "sea2", "sea3", "sea5", "sea4"):
        for t3 in others[name]:
            for v in t3:
                k = _pk(v[0])
                if k in {_pk(p) for p in water_moves}:
                    continue
                d, f = chain_param(v[0])
                if f <= 0.05 or f >= TAPER_REACH or abs(d) < 1e-6:
                    continue
                fac = math.cos(math.pi / 2.0 * f / TAPER_REACH) ** 2
                if abs(d * fac) < 0.05:
                    continue
                water_moves[v[0]] = (d * fac * nh[0], 0.0, d * fac * nh[1])
    keyed = {_pk(p): v for p, v in water_moves.items()}

    # THE RIBBON GATE: each moved waterline vert's distance to the sand seam must stay
    # inside the real swash envelope (measured 3.3-6.7u; band widened for donor variety)
    sand_seam = [pos_of[k] for k in adj if k in reg["terrain"]]
    for p in list(moves):
        d0 = min(math.hypot(p[0] - q[0], p[2] - q[2]) for q in sand_seam)
        dd = moves[p]
        d1 = min(math.hypot(p[0] + dd[0] - q[0], p[2] + dd[2] - q[2]) for q in sand_seam)
        if not (2.6 <= d1 <= 8.2):
            raise ValueError(f"RIBBON GATE: the bow moves the swash ribbon to {d1:.1f}u at "
                             f"({p[0]:.0f},{p[2]:.0f}) -- outside the real 3.3-6.7u envelope "
                             f"(pre-move {d0:.1f}); reduce depth")

    # fold precheck across every part (the local envelope, offline)
    for tris in [beach] + list(others.values()):
        for t3 in tris:
            if not any(_pk(v[0]) in keyed for v in t3):
                continue
            out = []
            for (pos, nrm, uv, tan) in t3:
                dd = keyed.get(_pk(pos))
                if dd is not None:
                    pos = (pos[0] + dd[0], pos[1] + dd[1], pos[2] + dd[2])
                out.append((pos, nrm, uv, tan))
            a0 = TR.VertexDisplace._area2(list(t3))
            a1 = TR.VertexDisplace._area2(out)
            if abs(a0) > 0.02 and (a0 * a1 <= 0.0 or abs(a1) < 0.02):
                raise ValueError(f"depth {depth:g} folds a shore tile -- the waterline "
                                 f"envelope is geometric; reduce depth")
    n_terr = sum(_pk(v[0]) in keyed for t3 in others["terrain"] for v in t3)
    if n_terr:
        raise ValueError(f"{n_terr} moved instance(s) belong to TERRAIN -- the sand must "
                         f"not move; pick a waterline run clear of the sand seam")
    # THE BAND GATE: no shore band may compress below ~60% of its verbatim width (the
    # ladder-taper's whole point -- the pinched wash was the in-game seam)
    reg_pk = {n: {_pk(v[0]) for t3 in t for v in t3} for n, t in others.items()}
    beach_pk = {_pk(v[0]) for t3 in beach for v in t3}
    c1 = [pos_of.get(k) or next(v[0] for t3 in others["sea2"] for v in t3 if _pk(v[0]) == k)
          for k in (reg_pk["sea2"] & reg_pk["sea1"])]
    def _mv(p):
        d = keyed.get(_pk(p))
        return (p[0] + d[0], p[1], p[2] + d[2]) if d else p
    for p in list(moves):
        if not c1:
            break
        w0 = min(math.hypot(p[0] - q[0], p[2] - q[2]) for q in c1)
        pm = _mv(p)
        w1 = min(math.hypot(pm[0] - q[0], pm[2] - q[2]) for q in (_mv(q) for q in c1))
        if w0 > 0.5 and w1 < 0.6 * w0:
            raise ValueError(f"BAND GATE: the wash band pinches {w0:.1f} -> {w1:.1f}u at "
                             f"({p[0]:.0f},{p[2]:.0f}) despite the taper -- reduce depth")
    # THE STRAIN GATE + the mechanism law (in-game rounds 1-3, 2026-07-10): water tolerates
    # SMALL strain, not sharp strain, and never extrapolated re-evaluation. Under the taper
    # every tile strains <=~15%, so verbatim DRAG is correct (zero uv discontinuities by
    # construction); per-tile re-evaluation at field scale extrapolates past tile footprints
    # -- the clamp binds (smush) and every tile pins to its OWN map while geometry slides
    # (border tiling). Gate: every touched water edge's plan length stays within [0.75,1.33].
    for name in ("sea1", "sea2", "sea3", "sea5", "sea4"):
        for t3 in others[name]:
            if not any(_pk(v[0]) in keyed for v in t3):
                continue
            ps0 = [v[0] for v in t3]
            ps1 = [( (p[0] + keyed[_pk(p)][0], p[1], p[2] + keyed[_pk(p)][2])
                     if _pk(p) in keyed else p) for p in ps0]
            for i in range(3):
                l0 = math.hypot(ps0[i][0] - ps0[(i + 1) % 3][0],
                                ps0[i][2] - ps0[(i + 1) % 3][2])
                l1 = math.hypot(ps1[i][0] - ps1[(i + 1) % 3][0],
                                ps1[i][2] - ps1[(i + 1) % 3][2])
                if l0 > 0.5 and not (0.75 <= l1 / l0 <= 1.33):
                    raise ValueError(f"STRAIN GATE: a {name} edge strains x{l1 / l0:.2f} "
                                     f"near ({ps0[i][0]:.0f},{ps0[i][2]:.0f}) -- the taper "
                                     f"should cap strain at ~15%; reduce depth")
    n_all = sum(_pk(v[0]) in keyed
                for tris in [beach] + list(others.values()) for t3 in tris for v in t3)
    return [TR.VertexDisplace(moves=water_moves, expected=n_all)]


#: the FOAM RUN tile (byte-decoded 2026-07-10 from (7,17)): one half-texture per 4u column,
#: repeating; v = the cross-shore ramp. The END-CAP band (v 0.5312-0.9375) is a SEPARATE
#: taper graphic carried by the beach's two TERMINAL columns (u 0.0156 at the terminal
#: end -> 0.5 at the run junction, mirrored per end) -- it narrows the foam into the
#: coast and hides the strip's straight end (user-called in-game 2026-07-10: a run-tile
#: cap reads as a hard straight line at the beach end). Emission therefore TRANSPORTS
#: each column's own corner UVs from the donor (:func:`_foam_corner_uvs`) instead of
#: assuming the run constants; these constants remain as the decoded reference.
FOAM_U = (0.0156, 0.5)
FOAM_V_SAND = 0.0156
FOAM_V_WATER = 0.4531


def _foam_corner_uvs(drop_foam, S, W):
    """Per foam column, the donor's OWN corner UVs keyed sand-left/sand-right/water-left/
    water-right (identity transport: run columns decode to the learned run constants, the
    beach's terminal columns to their CAP taper corners -- and a different beach's atlas
    layout carries over untouched). A chain vert shared by two columns carries DIFFERENT
    uv per column (the cap<->run junction), so the decode is per-column."""
    cols = []
    for i in range(len(W) - 1):
        xa, xb = W[i][0], W[i + 1][0]
        m = {}
        for t3 in drop_foam:
            if xa - 0.1 <= sum(v[0][0] for v in t3) / 3.0 <= xb + 0.1:
                for v in t3:
                    m.setdefault(_pk(v[0]), (v[2][0], v[2][1]))
        cs = {}
        for tag, p in (("sl", S[i]), ("sr", S[i + 1]), ("wl", W[i]), ("wr", W[i + 1])):
            uv = m.get(_pk(p))
            if uv is None:
                raise ValueError(f"foam column {i}: chain vert ({p[0]:.0f},{p[2]:.1f}) "
                                 f"is not on any of the column's foam tris")
            cs[tag] = uv
        # the donor's own quad DIAGONAL (it alternates per column; the interior affine
        # differs per split, so identity means reproducing it)
        kwl, ksr = _pk(W[i]), _pk(S[i + 1])
        cs["diag"] = "wl-sr" if any(
            xa - 0.1 <= sum(v[0][0] for v in t3) / 3.0 <= xb + 0.1
            and {kwl, ksr} <= {_pk(v[0]) for v in t3} for t3 in drop_foam) else "sl-wr"
        cols.append(cs)
    return cols


def _up_tri(tri):
    """Wind a tri up-facing in plan -- the emission convention across the shore ladder."""
    ux, uz = tri[1][0][0] - tri[0][0][0], tri[1][0][2] - tri[0][0][2]
    vx, vz = tri[2][0][0] - tri[0][0][0], tri[2][0][2] - tri[0][0][2]
    return [tri[0], tri[2], tri[1]] if uz * vx - ux * vz <= 0 else tri


def _beach_window(donor, start, end, *, disc=1, lod="0_1", game=None):
    """Decode the beach ramp assembly + a window's matched chains (waterline W / sand S,
    x-sorted lattice columns) -- the shared opening of the structural beach machinery."""
    beach = TR.world_tris(*donor, "beach1", disc=disc, lod=lod, game=game)
    parts = {p: TR.world_tris(*donor, p, disc=disc, lod=lod, game=game)
             for p in ("terrain", "sea1", "sea2", "sea3", "sea5", "sea4")}
    if not beach:
        raise ValueError(f"donor {donor} has no beach1 mesh")
    reg = {n: {_pk(v[0]) for t3 in t for v in t3} for n, t in parts.items()}
    e_count = defaultdict(int)
    pos_of = {}
    for t3 in beach:
        ps = [v[0] for v in t3]
        for v in t3:
            pos_of.setdefault(_pk(v[0]), v[0])
        for i in range(3):
            e_count[frozenset((_pk(ps[i]), _pk(ps[(i + 1) % 3])))] += 1
    bnd = {k for e, c in e_count.items() if c == 1 for k in e}
    water_chain = sorted((pos_of[k] for k in bnd
                          if k in reg["sea2"] and k not in reg["terrain"]),
                         key=lambda p: p[0])
    sand_chain = sorted((pos_of[k] for k in bnd if k in reg["terrain"]),
                        key=lambda p: p[0])
    for p_, nm in ((start, "start"), (end, "end")):
        if min((math.hypot(q[0] - p_[0], q[2] - p_[1]) for q in water_chain),
               default=9e9) > 0.8:
            raise ValueError(f"{nm} {tuple(p_)} is not on the waterline chain -- pick the "
                             f"foam line (beach1's seaward boundary), not the sand seam")
    x0, x1 = sorted((start[0], end[0]))
    W = [p for p in water_chain if x0 - 0.1 <= p[0] <= x1 + 0.1]
    S = [p for p in sand_chain if x0 - 0.1 <= p[0] <= x1 + 0.1]
    if len(W) < 3 or len(W) != len(S):
        raise ValueError(f"the window needs matched waterline/sand columns "
                         f"(got {len(W)}/{len(S)}) -- pick a mid-beach run clear of the "
                         f"end-caps")
    return beach, parts, reg, W, S, x0, x1


def _mains_factory():
    """Per-cell anti-tiling MAINS picks (2x2 quadrant + rotation, deterministic hash) as a
    ``cell -> uvf(x, z)`` factory; one shared pick store per build. The proven sea2 wash
    vocabulary (sea3 has its OWN quadrant language -- :func:`_sea3_factory`)."""
    from .water import URECT, VRECT, OMAPS
    cell_pick = {}

    def mains_map(cell):
        (ci, cj) = cell
        if cell not in cell_pick:
            h = TR._h01(4.0 * ci + 1.7, 4.0 * cj + 2.3)
            cell_pick[cell] = ((int(h * 2) % 2, int(h * 4) % 2),
                               ("r0", "r90", "r180", "r270")[
                                   int(TR._h01(4.0 * ci + 3.1, 4.0 * cj + 0.9) * 4) % 4])
        (uh, vh), rname = cell_pick[cell]
        m = OMAPS[rname]
        (u0, u1), (v0, v1) = URECT[uh], VRECT[vh]

        def uvf(x, z):
            fx = (x - 4.0 * ci) / 4.0
            fz = (z - 4.0 * cj) / 4.0
            a, b = m(fx, fz)
            return (u0 + a * (u1 - u0), v0 + b * (v1 - v0))
        return uvf
    return mains_map


#: SEA3's learned quadrant language (byte-learned 2026-07-10, ~90 cells over 4 coastal
#: blocks, every fit err 0.0000): u-halves like sea4's but its OWN v split at 0.50794, and
#: placement over DIHEDRAL-8 (flips are real -- a rotation-4 fit misses half the tiles).
#: Real tiles also carry optional ~2-texel border-inset rect variants with no structural
#: correlation; the un-inset base appears in bulk on every half, so emission uses bases
#: only and the decode fit accepts insets within eps.
SEA3_URECT = [(0.0, 0.50394), (0.50394, 0.99213)]
SEA3_VRECT = [(0.0, 0.50794), (0.50794, 1.0)]


def _sea3_factory():
    """Per-cell anti-tiling SEA3 picks (quadrant + dihedral-8, deterministic hash) as a
    ``cell -> uvf(x, z)`` factory."""
    maps8 = TR._dih_maps()
    onames = sorted(maps8)

    def sea3_map(cell):
        (ci, cj) = cell
        h = TR._h01(4.0 * ci + 2.9, 4.0 * cj + 1.3)
        (u0, u1) = SEA3_URECT[int(h * 2) % 2]
        (v0, v1) = SEA3_VRECT[int(h * 4) % 2]
        m = maps8[onames[int(TR._h01(4.0 * ci + 0.7, 4.0 * cj + 3.7) * 8) % 8]]

        def uvf(x, z):
            fx = (x - 4.0 * ci) / 4.0
            fz = (z - 4.0 * cj) / 4.0
            a, b = m(fx, fz)
            return (u0 + a * (u1 - u0), v0 + b * (v1 - v0))
        return uvf
    return sea3_map


def _strip_uvf(cell, es):
    """The learned-table EMISSION: a deep-edge-set -> a placed strip tile's uv map (variant
    picked by the deterministic cell hash)."""
    from .water import UFULL, VSTRIP
    variants = TR.EDGESET2STRIP.get(es)
    if not variants:
        raise ValueError(f"sea1 cell {cell}: edge-set {sorted(es)} has no learned strip")
    k, oname = variants[int(TR._h01(4.0 * cell[0] + 0.3, 4.0 * cell[1] + 2.9)
                            * len(variants)) % len(variants)]
    m = TR._dih_maps()[oname]
    (su0, su1), (sv0, sv1) = UFULL, VSTRIP[k]

    def uvf(x, z):
        fx = (x - 4.0 * cell[0]) / 4.0
        fz = (z - 4.0 * cell[1]) / 4.0
        a, b = m(fx, fz)
        return (su0 + a * (su1 - su0), sv0 + b * (sv1 - sv0))
    return uvf


def beach_rebuild(donor, start, end, *, disc: int = 1, lod: str = "0_1", game=None):
    """The STRUCTURAL beach machinery, identity mode (rung 2, step 1): DROP the window's
    shore ladder (foam run tiles + sea2 wash + the sea1 Wang ring) and RE-DERIVE it from
    pure language over the SAME vertex set -- foam by the run-tile rule, sea2 as quadrant
    mains + affine-continued conforming zip, sea1 by the LEARNED WANG TABLE in emission
    mode (deep-edge-sets from the band map -> EDGESET2STRIP). The generative proof: if the
    rebuilt window reads verbatim in-game, reshaping the chains becomes a controlled delta.
    Self-check: every derived sea1 edge-set must equal the real tile's decode."""
    beach, parts, reg, W, S, x0, x1 = _beach_window(donor, start, end,
                                                    disc=disc, lod=lod, game=game)

    def in_win(t3):
        return all(x0 - 0.1 <= v[0][0] <= x1 + 0.1 for v in t3)
    drop_foam = [t for t in beach if in_win(t)]
    drop_sea2 = [t for t in parts["sea2"] if in_win(t)]
    drop_sea1 = [t for t in parts["sea1"] if in_win(t)]
    if not (drop_foam and drop_sea2 and drop_sea1):
        raise ValueError("the window does not cover a full foam/wash/ring ladder")

    # original positions by key (identity: the vertex SET is fixed; only topology + UVs
    # re-derive) + per-part normals/idall exemplars
    posY = {}
    nrm_ex, id_ex = {}, {}
    for name, tris in (("beach1", drop_foam), ("sea2", drop_sea2), ("sea1", drop_sea1)):
        for t3 in tris:
            for v in t3:
                posY.setdefault(_pk((v[0][0], 0, v[0][2]))[::2], v[0])
            nrm_ex.setdefault(name, t3[0][1])
            id_ex.setdefault(name, tuple(t3[0][3]))

    def P(x, z):
        p = posY.get((round(x, 4), round(z, 4)))
        if p is None:
            raise ValueError(f"rebuild references ({x},{z}) -- not an original shore vert")
        return p

    # --- (a) FOAM: per-column tiles between the chains, corner UVs transported from the
    # donor (run columns = the learned run tile; terminal columns = the CAP taper) ---
    foam_emit = []
    corner_uvs = _foam_corner_uvs(drop_foam, S, W)
    for i in range(len(W) - 1):
        sl, sr, wl, wr = S[i], S[i + 1], W[i], W[i + 1]
        cs = corner_uvs[i]
        uv = {id(sl): cs["sl"], id(sr): cs["sr"], id(wl): cs["wl"], id(wr): cs["wr"]}
        split = ((sr, wl, sl), (sr, wr, wl)) if cs["diag"] == "wl-sr" \
            else ((wr, wl, sl), (wr, sl, sr))
        for tri_pts in split:
            foam_emit.append(_up_tri([(p, nrm_ex["beach1"], uv[id(p)], id_ex["beach1"])
                                      for p in tri_pts]))

    # --- band map (identity: the real footprints) + cell registries ---
    def cell_of(t3):
        return (math.floor(sum(v[0][0] for v in t3) / 3.0 / 4.0),
                math.floor(sum(v[0][2] for v in t3) / 3.0 / 4.0))
    band_rank = {"sea2": 0, "sea1": 1, "sea3": 2, "sea5": 3, "sea4": 4}

    def band_at(px, pz):
        """The DEEPEST band whose tile covers the point -- the interleaved shore means one
        4u cell can carry tris of two bands (the teardown's two-meshes-per-cell fact), so
        cell labels mislabel edges; coverage sampling is the honest band field."""
        for name in ("sea4", "sea5", "sea3", "sea1", "sea2"):
            for t3 in parts[name]:
                if _pip_xz(px, pz, t3):
                    return band_rank[name]
        return -1                                    # land / beach side

    # --- (b) SEA2: lattice mains + affine-continued conforming zip to the waterline ---
    def on_lat(v, eps=0.02):
        return (abs(v[0][0] / 4 - round(v[0][0] / 4)) < eps
                and abs(v[0][2] / 4 - round(v[0][2] / 4)) < eps)
    lat2 = [t for t in drop_sea2 if all(on_lat(v) for v in t)]
    conf2 = [t for t in drop_sea2 if not all(on_lat(v) for v in t)]
    sea2_emit = []
    mains_map = _mains_factory()
    for t3 in lat2:
        c = cell_of(t3)
        uvf = mains_map(c)
        tri = [ (v[0], nrm_ex["sea2"], uvf(v[0][0], v[0][2]), id_ex["sea2"]) for v in t3]
        sea2_emit.append(_up_tri(tri))
    # conforming: re-emit each conforming tri through its landward lattice cell's map
    for t3 in conf2:
        cx = sum(v[0][0] for v in t3) / 3.0
        cz = sum(v[0][2] for v in t3) / 3.0
        c = (math.floor(cx / 4.0), math.floor(cz / 4.0))
        uvf = mains_map(c)
        tri = [(v[0], nrm_ex["sea2"], uvf(v[0][0], v[0][2]), id_ex["sea2"]) for v in t3]
        sea2_emit.append(_up_tri(tri))

    # --- (c) SEA1: the Wang ring by the learned table (emission mode + decode self-check) ---
    sea1_cells = {}
    for t3 in drop_sea1:
        sea1_cells.setdefault(cell_of(t3), []).append(t3)
    sea1_emit = []
    for c, tris in sorted(sea1_cells.items()):
        # THE EDGE-SHADE FIELD IS SHAPE DATA (2026-07-10): thick interleaved sea1 regions
        # carry directional strips on INTERIOR cells too -- edge states are SHADES that must
        # agree across tiles (the Wang rule), so they cannot be derived from a neighbour-band
        # map (the thin-band special case). Identity mode READS the field from the donor's
        # own tiles (like the cliff morph read the crease polyline); a future shape morph
        # transports/re-solves it. The TILES still re-derive from the learned table.
        decs = {TR.strip_edge_set(t3) for t3 in tris}
        decs.discard(None)
        if len(decs) != 1:
            raise ValueError(f"sea1 cell {c}: inconsistent/undecodable edge-shade field "
                             f"{[sorted(d) for d in decs]} -- a conforming ring cell; keep "
                             f"it outside the window")
        es = next(iter(decs))
        # boundary sanity: an edge facing sea3+ must be deep (the field's boundary condition)
        cx0, cz0 = 4.0 * c[0], 4.0 * c[1]
        for d, pts in (("E", ((cx0 + 5.0, cz0 + 2.0),)), ("W", ((cx0 - 1.0, cz0 + 2.0),)),
                       ("N", ((cx0 + 2.0, cz0 + 5.0),)), ("S", ((cx0 + 2.0, cz0 - 1.0),))):
            if max(band_at(*p) for p in pts) > band_rank["sea1"] and d not in es:
                raise ValueError(f"sea1 cell {c}: edge {d} faces a deeper band but the "
                                 f"field reads shallow -- the donor decode is off")
        uvf = _strip_uvf(c, es)
        for t3 in tris:
            tri = [(v[0], nrm_ex["sea1"], uvf(v[0][0], v[0][2]), id_ex["sea1"]) for v in t3]
            sea1_emit.append(_up_tri(tri))

    # --- gates: per-part crack (hole boundary == emissions' once-edges) ---
    for name, dropped, emitted in (("beach1", drop_foam, foam_emit),
                                   ("sea2", drop_sea2, sea2_emit),
                                   ("sea1", drop_sea1, sea1_emit)):
        def once(tris):
            ec = defaultdict(int)
            for t3 in tris:
                ps = [v[0] for v in t3]
                for i in range(3):
                    ec[frozenset((_pk(ps[i]), _pk(ps[(i + 1) % 3])))] += 1
            return {e for e, cn in ec.items() if cn == 1}
        if once(dropped) != once(emitted):
            raise ValueError(f"CRACK GATE [{name}]: the rebuilt window's boundary does not "
                             f"match the dropped hole")
    return [TR.DropTris("beach1", drop_foam),
            TR.DropTris("sea2", drop_sea2),
            TR.DropTris("sea1", drop_sea1),
            TR.EmitTris("beach1", foam_emit),
            TR.EmitTris("sea2", sea2_emit),
            TR.EmitTris("sea1", sea1_emit)]


def beach_reshape(donor, start, end, depth, *, disc: int = 1, lod: str = "0_1", game=None):
    """The STRUCTURAL beach SHAPE morph (rung 2, step 2) -- slide the beach ASSEMBLY (sand
    seam + waterline together) and re-derive the whole shore ladder over the new footprint
    from pure language (ZERO water strain -- the bow DRAGS everything within its
    ~10x-depth reach; this re-lays):

    * the FOAM re-derives as run tiles over the moved chain (the step-1 vocabulary);
    * the WASH re-lays per column with a WIDTH-DRIVEN lattice boundary: each column picks
      the C1 shift that keeps its waterline->C1 widths nearest the donor's own, so the band
      map keeps REAL width statistics instead of straining (the ladder-taper law, honored
      structurally); the conforming zip is row-clipped (T-junction-free by construction);
    * the sea1/sea3 PATCHWORK TRANSPORTS by a per-column lattice pullback -- a shifted
      column's band pattern slides with the shore and stops where the pulled pattern
      reconciles with the existing one -- and THE EDGE-SHADE FIELD re-solves over the new
      map: transported shades preferred, flips minimized (a small exact search), domain =
      the learned table's 12 edge-sets, so the 4 non-table configs are unreachable.

    THE HUG LAW (user-called in-game 2026-07-10, byte-confirmed map-wide): within one
    beach the swash ribbon is near-CONSTANT (median range 1.26u over 32 real beaches;
    donor (7,17) = 0.38u around 4.0) -- the 3.3-6.7u envelope is CROSS-beach spread, a
    false within-beach law. The artists pull the foam line in PARALLEL to the sand's hard
    edge, so a widened ribbon reads wrong even when every band is lawful. Hence the
    ASSEMBLY SLIDES: the sand seam moves WITH the waterline (index-paired columns, same
    profile -- the connector-assembly law), the ribbon is preserved by construction, and
    the berm terrain DRAGS (land drag is the proven fine-adjustment mechanism, the
    cliff-bump 2.5u precedent -- which also caps depth). v1 scope: a south-facing
    (seaward = -z), z-dominant shore in donor frame (the transplant's rot places it any
    way in the world); single cell."""
    if abs(depth) > 2.6:
        raise ValueError("the sand-slide DRAGS the berm -- the land-drag envelope caps "
                         "depth at ~2.5 (the cliff-bump precedent)")
    beach, parts, reg, W, S, x0, x1 = _beach_window(donor, start, end,
                                                    disc=disc, lod=lod, game=game)
    n = len(W)
    if any(abs(W[i + 1][0] - W[i][0] - 4.0) > 0.01 for i in range(n - 1)):
        raise ValueError("the waterline window is not uniform 4u lattice columns -- the "
                         "band map is x-quantized; v1 reshapes column-quantized shores")
    if sum(p[2] for p in W) / n >= sum(p[2] for p in S) / n:
        raise ValueError("v1 reshapes south-facing shores (seaward = -z in donor frame); "
                         "the transplant's rot places the result any way in the world")
    if abs(W[-1][2] - W[0][2]) > 0.75 * abs(W[-1][0] - W[0][0]):
        raise ValueError("the shore is not z-dominant across the window -- v1 scope")

    # the displaced waterline: a pure-z sin^2 profile (+depth = seaward). Lattice x is
    # PRESERVED -- the staircase band map is x-quantized, so a structural morph on an
    # x-running shore is z-free / x-pinned; endpoints never move (end welds load-bearing).
    acc, arcs = 0.0, [0.0]
    for a, b in zip(W, W[1:]):
        acc += math.dist(a, b)
        arcs.append(acc)
    dz = [-depth * math.sin(math.pi * s_ / acc) ** 2 for s_ in arcs]
    dz[0] = dz[-1] = 0.0
    W2 = [(p[0], p[1], p[2] + d) for p, d in zip(W, dz)]
    S2 = [(p[0], p[1], p[2] + d) for p, d in zip(S, dz)]

    # THE HUG GATE: the assembly slide preserves the ribbon by construction; this catches
    # slope pathologies (the min-dist can wiggle where adjacent columns' dz differ)
    for i in range(1, n - 1):
        w0 = min(math.hypot(W[i][0] - q[0], W[i][2] - q[2]) for q in S)
        w1 = min(math.hypot(W2[i][0] - q[0], W2[i][2] - q[2]) for q in S2)
        if abs(w1 - w0) > 0.6:
            raise ValueError(f"HUG GATE: the slide changes the swash {w0:.1f} -> {w1:.1f}u "
                             f"at ({W[i][0]:.0f},{W[i][2]:.0f}) -- the ribbon must ride "
                             f"the sand edge (within-beach width is near-constant)")

    # THE SHAPE-CLASS GATE (user-called in-game 2026-07-10, byte-confirmed over 37 real
    # waterline runs): a beach's convexity class is INHERITED from the coastline it aprons
    # -- headland-nose beaches bow seaward of their cap-to-cap chord (up to +46% of
    # length), pocket beaches stay landward of it. A morph may DEEPEN the beach's own
    # curvature (up to the map-wide class envelope, ~35% of length) but must never push
    # past its own extreme toward the OPPOSITE class: a pocket that crosses its chord
    # reads as the beach peeling off the coast (the v2 'extruded ends'), because the land
    # behind it is still concave. Devs are chord-relative, seaward-positive.
    a_, b_ = W[0], W[-1]
    ex_, ez_ = b_[0] - a_[0], b_[2] - a_[2]
    L_ = math.hypot(ex_, ez_) or 1.0
    nx_, nz_ = -ez_ / L_, ex_ / L_
    if nz_ > 0:                                       # seaward = -z on this shore class
        nx_, nz_ = -nx_, -nz_
    def _dev(p):
        return (p[0] - a_[0]) * nx_ + (p[2] - a_[2]) * nz_
    d0 = [_dev(p) for p in W[1:-1]]
    d1 = [_dev(p) for p in W2[1:-1]]
    sea_cap = 0.35 * L_ if max(d0) > 0.5 else max(d0) + 0.3
    land_cap = -0.35 * L_ if min(d0) < -0.5 else min(d0) - 0.3
    if max(d1) > sea_cap + 1e-6 or min(d1) < land_cap - 1e-6:
        klass = "convex (headland-nose)" if max(d0) > 0.5 else \
                "concave (pocket)" if min(d0) < -0.5 else "straight"
        raise ValueError(f"SHAPE-CLASS GATE: this beach is {klass} (chord devs "
                         f"{min(d0):.1f}..{max(d0):.1f} over {L_:.0f}u); the morph takes "
                         f"it to {min(d1):.1f}..{max(d1):.1f}, past its class envelope "
                         f"[{land_cap:.1f},{sea_cap:.1f}] -- a beach may deepen its own "
                         f"curvature, never cross toward the opposite class")

    # --- the cell census (a bounded working region around the window) ---
    def cell_of(t3):
        return (math.floor(sum(v[0][0] for v in t3) / 3.0 / 4.0),
                math.floor(sum(v[0][2] for v in t3) / 3.0 / 4.0))

    def on_lat(v, eps=0.02):
        return (abs(v[0][0] / 4 - round(v[0][0] / 4)) < eps
                and abs(v[0][2] / 4 - round(v[0][2] / 4)) < eps)
    xlo, xhi = x0 - 8.0, x1 + 8.0
    zhi = max(p[2] for p in S) + 8.0
    zlo = min(p[2] for p in W) - 40.0
    owner, cell_tris, cell_conf = {}, defaultdict(list), set()
    for name in ("sea2", "sea1", "sea3", "sea5"):
        for t3 in parts[name]:
            c = cell_of(t3)
            if not (xlo <= 4.0 * c[0] <= xhi and zlo <= 4.0 * c[1] <= zhi):
                continue
            cell_tris[(name, c)].append(t3)
            if all(on_lat(v) for v in t3):
                prev = owner.get(c)
                if prev not in (None, name):
                    raise ValueError(f"cell {c} carries lattice tiles of {prev} AND {name}"
                                     f" -- an interleave the v1 census cannot own")
                owner[c] = name
            else:
                cell_conf.add((name, c))
    shade = {}
    for (name, c), tris in cell_tris.items():
        if name != "sea1":
            continue
        decs = {TR.strip_edge_set(t3) for t3 in tris}
        decs.discard(None)
        if len(decs) == 1:
            shade[c] = next(iter(decs))

    # --- the wash boundary, width-driven per column (the band map keeps real statistics) ---
    def col_ci(i):
        return int(round(W[i][0])) // 4
    sea2_rows = defaultdict(list)
    for c, nm in owner.items():
        if nm == "sea2":
            sea2_rows[c[0]].append(c[1])
    old_c1, new_c1, s_col = {}, {}, {}
    for i in range(n - 1):
        ci = col_ci(i)
        if sea2_rows.get(ci):
            old_c1[i] = 4.0 * min(sea2_rows[ci])
        else:
            old_c1[i] = 4.0 * math.floor(min(W[i][2], W[i + 1][2]) / 4.0)
        cands = (0,) if i in (0, n - 2) else (0, 1, -1, 2)
        best = None
        for s_ in cands:
            c1 = old_c1[i] - 4.0 * s_
            ok, dev = True, 0.0
            # the ABSOLUTE real envelope is the law (the donor's wash occupies 2.4-8u and
            # its own columns jump 4<->8 between neighbours, so a ratio-to-old gate is a
            # false law; dev-minimization keeps the new map nearest the donor's) -- with a
            # small-excursion escape for verts that START outside it (the beach's natural
            # end taper runs 2.4 -> 0; those columns may only wiggle, never re-band)
            for w1_, w0_ in (((W2[i][2] - c1), (W[i][2] - old_c1[i])),
                             ((W2[i + 1][2] - c1), (W[i + 1][2] - old_c1[i]))):
                if not ((2.4 <= w1_ <= 8.4)
                        or (w1_ >= -0.01 and w1_ <= 8.4 and abs(w1_ - w0_) <= 1.2)):
                    ok = False
                dev += abs(w1_ - w0_)
            if ok and (best is None or (dev, abs(s_)) < best[:2]):
                best = (dev, abs(s_), s_)
        if best is None:
            raise ValueError(f"BAND GATE: no lattice wash boundary keeps column "
                             f"{W[i][0]:.0f}..{W[i + 1][0]:.0f} inside the real width "
                             f"envelope -- reduce depth")
        s_col[i] = best[2]
        new_c1[i] = old_c1[i] - 4.0 * best[2]

    # --- the patchwork pullback (band pattern slides with the shore, reconciles below) ---
    changes, wash_new = {}, {}
    for i in range(n - 1):
        t = s_col[i]
        if t == 0:
            continue
        ci = col_ci(i)
        jo, jn = int(round(old_c1[i] / 4)), int(round(new_c1[i] / 4))
        for j in range(jn, jo):                      # rows the wash grows over (seaward)
            if owner.get((ci, j)) is None:
                raise ValueError(f"wash growth hits an unowned cell ({ci},{j})")
            wash_new[(ci, j)] = owner[(ci, j)]
        for k in range(8):
            j = jn - 1 - k
            c, src = (ci, j), (ci, j + t)
            po, eo = owner.get(src), owner.get(c)
            if po is None or eo is None:
                raise ValueError(f"the pullback walks off the census at ({ci},{j})")
            if "sea5" in (po, eo):
                raise ValueError(f"the pullback reaches sea5 at ({ci},{j}) -- v1 scope; "
                                 f"reduce depth")
            ps, es = shade.get(src), shade.get(c)
            if po == eo and (po != "sea1" or (ps is not None and ps == es)):
                break                                # reconciled: below stays verbatim
            if po == "sea1" and ps is None:
                raise ValueError(f"pullback source ({ci},{j + t}) is sea1 but undecodable")
            changes[c] = (po, ps if po == "sea1" else None)
        else:
            raise ValueError(f"column {W[i][0]:.0f}.. never reconciles within 8 rows -- "
                             f"reduce depth")

    def new_owner(c):
        if c in wash_new:
            return "sea2"
        if c in changes:
            return changes[c][0]
        return owner.get(c)

    # band-adjacency legality over the touched neighbourhood (the ladder must not skip)
    for c in set(wash_new) | set(changes):
        for d_ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            pair = {new_owner(c), new_owner((c[0] + d_[0], c[1] + d_[1]))}
            if None in pair:
                continue
            if pair in ({"sea2", "sea3"}, {"sea2", "sea5"}, {"sea1", "sea5"},
                        {"sea2", "sea4"}, {"sea1", "sea4"}):
                raise ValueError(f"BAND LADDER: the new map makes {sorted(pair)} adjacent "
                                 f"at {c} -- an unreal grade jump; reduce depth")

    # --- THE EDGE-SHADE FIELD: transported, then re-solved (min-flip exact search) ---
    core = {c for c, (b, _) in changes.items() if b == "sea1"}
    frontier = set()
    for c in set(changes) | set(wash_new):
        for d_ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (c[0] + d_[0], c[1] + d_[1])
            if (new_owner(nb) == "sea1" and nb not in core and nb not in changes
                    and x0 - 0.1 <= 4.0 * nb[0] and 4.0 * nb[0] + 4 <= x1 + 0.1):
                frontier.add(nb)
    cells = sorted(core | frontier)
    cellset = set(cells)
    EDGE = {"E": (1, 0), "W": (-1, 0), "N": (0, 1), "S": (0, -1)}
    OPP = {"E": "W", "W": "E", "N": "S", "S": "N"}
    prefer = {c: (changes[c][1] if c in core else shade.get(c)) for c in cells}
    pins = {}
    for c in cells:
        for e, d_ in EDGE.items():
            nb = (c[0] + d_[0], c[1] + d_[1])
            b = new_owner(nb)
            if b in ("sea3", "sea5", "sea4"):
                pins[(c, e)] = True                  # deep faces deeper
            elif b != "sea1":
                pins[(c, e)] = False                 # wash / beach / land side: shallow
            elif nb not in cellset:                  # a verbatim sea1 neighbour: pin to it
                nes = shade.get(nb)
                if nes is None:
                    raise ValueError(f"cell {c} edge {e}: verbatim sea1 neighbour {nb} is "
                                     f"undecodable -- shift the window")
                pins[(c, e)] = OPP[e] in nes
    domain = sorted(TR.EDGESET2STRIP, key=lambda es: (len(es), sorted(es)))
    best = [None, len(cells) + 1]

    def _bt(idx, assign, flips):
        if flips >= best[1]:
            return
        if idx == len(cells):
            best[0], best[1] = dict(assign), flips
            return
        c = cells[idx]
        for es in sorted(domain, key=lambda e_: e_ != prefer[c]):
            ok = True
            for e, d_ in EDGE.items():
                p = pins.get((c, e))
                if p is not None and (e in es) != p:
                    ok = False
                    break
                nb = (c[0] + d_[0], c[1] + d_[1])
                if nb in assign and (e in es) != (OPP[e] in assign[nb]):
                    ok = False
                    break
            if ok:
                assign[c] = es
                _bt(idx + 1, assign, flips + (es != prefer[c]))
                del assign[c]
    _bt(0, {}, 0)
    if best[0] is None:
        raise ValueError("EDGE-SHADE SOLVER: no table-valid field fits the new band map -- "
                         "the transported shades cannot be repaired; reduce depth or shift "
                         "the window")
    solved = best[0]
    flipped = sorted(c for c in frontier if solved[c] != prefer[c])

    # --- drops ---
    def in_win(t3):
        return all(x0 - 0.1 <= v[0][0] <= x1 + 0.1 for v in t3)
    for name in ("beach1", "sea2", "sea1", "sea3"):
        tris = beach if name == "beach1" else parts[name]
        for t3 in tris:
            xs = [v[0][0] for v in t3]
            if not in_win(t3) and any(x0 + 0.1 < x_ < x1 - 0.1 for x_ in xs):
                raise ValueError(f"a {name} tri straddles the window frame -- the window "
                                 f"must cut at clean column boundaries")
    zdeep = min(min(old_c1.values()), min(new_c1.values()))
    drop_foam = [t for t in beach if in_win(t)]
    drop_sea2 = [t for t in parts["sea2"] if in_win(t)
                 and sum(v[0][2] for v in t) / 3.0 > zdeep - 0.1]
    drop_sea1, drop_sea3 = [], []
    for c in sorted(set(changes) | set(wash_new) | set(flipped)):
        old_b = owner[c]
        if old_b == "sea2":
            continue                                 # already in the wash drop set
        for t3 in cell_tris[(old_b, c)]:
            if not all(on_lat(v) for v in t3):
                raise ValueError(f"changed cell {c} carries a conforming {old_b} tri -- "
                                 f"shift the window off the conforming ring")
            (drop_sea1 if old_b == "sea1" else drop_sea3).append(t3)

    # --- emissions ---
    posY = {}
    for name in ("terrain", "sea1", "sea2", "sea3", "sea5", "beach1"):
        for t3 in (beach if name == "beach1" else parts[name]):
            for v in t3:
                posY.setdefault((round(v[0][0], 4), round(v[0][2], 4)), v[0][1])
    w2y = {(round(p[0], 4), round(p[2], 4)): p[1] for p in W2}

    def corner(x, z):
        k = (round(x, 4), round(z, 4))
        if k in w2y:                                 # a (possibly moved) waterline vert
            return (x, w2y[k], z)
        if abs(x - x0) < 0.05 or abs(x - x1) < 0.05:  # the frame welds to unchanged mesh
            return (x, posY.get(k, 0.0), z)
        return (x, 0.0, z)                           # interior open water
    nrm_ex, id_ex = {}, {}
    for name in ("beach1", "sea2", "sea1", "sea3"):
        for t3 in (beach if name == "beach1" else parts[name]):
            nrm_ex[name], id_ex[name] = t3[0][1], tuple(t3[0][3])
            break
    foam_emit, sea2_emit, sea1_emit, sea3_emit = [], [], [], []
    corner_uvs = _foam_corner_uvs(drop_foam, S, W)
    for i in range(n - 1):
        sl, sr, wl_, wr_ = S2[i], S2[i + 1], W2[i], W2[i + 1]
        cs = corner_uvs[i]
        # the moved waterline can cross a lattice row mid-column; the conforming zip splits
        # there, so the foam MUST carry the same vert (identical floats) or the shared
        # waterline becomes a T-junction. UVs stay exact: each foam tile (run OR cap) is
        # bilinear in x over its transported donor corners.
        wline = [wl_]
        zmin, zmax = sorted((wl_[2], wr_[2]))
        k = math.floor(zmin / 4.0) + 1
        cross = []
        while 4.0 * k < zmax - 1e-9:
            if 4.0 * k > zmin + 1e-9:
                t_ = (4.0 * k - wl_[2]) / (wr_[2] - wl_[2])
                cross.append((wl_[0] + t_ * (wr_[0] - wl_[0]),
                              wl_[1] + t_ * (wr_[1] - wl_[1]), 4.0 * k))
            k += 1
        wline += sorted(cross, key=lambda p: p[0]) + [wr_]

        def foam_uv(p, water):
            fx = (p[0] - wl_[0]) / (wr_[0] - wl_[0])
            (u0, v0), (u1, v1) = (cs["wl"], cs["wr"]) if water else (cs["sl"], cs["sr"])
            return (u0 + fx * (u1 - u0), v0 + fx * (v1 - v0))
        if cs["diag"] == "wl-sr":                    # fan from sr = the donor's diagonal
            polys = [(sr, wline[k_], wline[k_ + 1]) for k_ in range(len(wline) - 1)]
            polys.append((sr, sl, wline[0]))
        else:                                        # fan from sl
            polys = [(sl, wline[k_], wline[k_ + 1]) for k_ in range(len(wline) - 1)]
            polys.append((sl, wline[-1], sr))
        for tp in polys:
            tri = []
            for p in tp:
                tri.append((p, nrm_ex["beach1"], foam_uv(p, p not in (sl, sr)),
                            id_ex["beach1"]))
            foam_emit.append(_up_tri(tri))
    mains_map = _mains_factory()

    def emit_cell(part_, out, c, uvf):
        q = [corner(4.0 * c[0], 4.0 * c[1]), corner(4.0 * c[0] + 4, 4.0 * c[1]),
             corner(4.0 * c[0] + 4, 4.0 * c[1] + 4), corner(4.0 * c[0], 4.0 * c[1] + 4)]
        for tp in ((q[0], q[1], q[2]), (q[0], q[2], q[3])):
            out.append(_up_tri([(p, nrm_ex[part_], uvf(p[0], p[2]), id_ex[part_])
                                for p in tp]))

    def clip_band(pts, z0_, z1_):
        """Sutherland-Hodgman clip of a convex xz polygon to the row band [z0_, z1_] --
        the conforming zip splits at every lattice row line it spans (no T-junctions)."""
        for keep, zb in ((lambda p: p[2] >= z0_ - 1e-9, z0_),
                         (lambda p: p[2] <= z1_ + 1e-9, z1_)):
            out, m_ = [], len(pts)
            for a_i in range(m_):
                a, b = pts[a_i], pts[(a_i + 1) % m_]
                if keep(a):
                    out.append(a)
                if keep(a) != keep(b):
                    t_ = (zb - a[2]) / (b[2] - a[2])
                    out.append((a[0] + t_ * (b[0] - a[0]), a[1] + t_ * (b[1] - a[1]), zb))
            pts = out
            if not pts:
                return []
        return pts
    for i in range(n - 1):
        wa, wb = W2[i], W2[i + 1]
        ci = col_ci(i)
        zline = 4.0 * math.floor(min(wa[2], wb[2]) / 4.0)
        if zline < new_c1[i] - 0.01:
            raise ValueError(f"column {W[i][0]:.0f}..: the waterline undercuts its own "
                             f"wash boundary -- the band search should have refused")

        def ramp_y(x, z, wa=wa, wb=wb):
            """The shore ramp FIELD: the wash y ramps waterline->0 within the waterline's
            OWN row at that x (the donor's conf vocabulary), flat 0 below -- a field, so
            shared verts agree across pieces and columns (watertight by construction)."""
            t_ = (x - wa[0]) / (wb[0] - wa[0])
            zw = wa[2] + t_ * (wb[2] - wa[2])
            yw = wa[1] + t_ * (wb[1] - wa[1])
            zf = 4.0 * math.floor(zw / 4.0)
            if zw - zf < 1e-6:
                return yw if z >= zw - 1e-6 else 0.0
            return yw * max(0.0, min(1.0, (z - zf) / (zw - zf)))
        # the conforming zip, clipped row by row (side edges split at every lattice line)
        quad = [wa, wb, (wb[0], 0.0, zline), (wa[0], 0.0, zline)]
        j = int(round(4.0 * math.floor(max(wa[2], wb[2]) / 4.0) / 4))
        while 4.0 * j >= zline - 0.01:
            piece = clip_band(quad, 4.0 * j, 4.0 * j + 4.0)
            piece = [p for k_, p in enumerate(piece)
                     if math.hypot(p[0] - piece[k_ - 1][0], p[2] - piece[k_ - 1][2]) > 1e-6]
            piece = [(p[0], ramp_y(p[0], p[2]), p[2]) for p in piece]
            if len(piece) >= 3:
                uvf = mains_map((ci, j))
                for k_ in range(1, len(piece) - 1):
                    t3 = [(piece[0], nrm_ex["sea2"], uvf(piece[0][0], piece[0][2]),
                           id_ex["sea2"]),
                          (piece[k_], nrm_ex["sea2"], uvf(piece[k_][0], piece[k_][2]),
                           id_ex["sea2"]),
                          (piece[k_ + 1], nrm_ex["sea2"],
                           uvf(piece[k_ + 1][0], piece[k_ + 1][2]), id_ex["sea2"])]
                    if TR._tri_area2_3d(t3) > 1e-6:
                        sea2_emit.append(_up_tri(t3))
            j -= 1
        # the full wash rows from the zip floor down to the new boundary
        j = int(round(zline / 4)) - 1
        while 4.0 * (j + 1) > new_c1[i] + 0.01:
            emit_cell("sea2", sea2_emit, (ci, j), mains_map((ci, j)))
            j -= 1
    sea3_map = _sea3_factory()
    for c in sorted(set(changes) | set(flipped)):
        b = changes[c][0] if c in changes else "sea1"
        if b == "sea1":
            emit_cell("sea1", sea1_emit, c, _strip_uvf(c, solved[c]))
        elif b == "sea3":
            emit_cell("sea3", sea3_emit, c, sea3_map(c))

    # sea3 language self-check: the LEARNED quadrant/dihedral-8 fit must hold on REAL
    # nearby sea3 tiles before we emit any (inset rect variants pass within eps)
    if sea3_emit:
        maps8 = TR._dih_maps()

        def sea3_fit(t3, eps=0.05):
            uvf_ = TR._affine_uv(t3)
            cx = 4.0 * math.floor(sum(v[0][0] for v in t3) / 3 / 4.0)
            cz = 4.0 * math.floor(sum(v[0][2] for v in t3) / 3 / 4.0)
            err_best = 1e9
            for (u0, u1) in SEA3_URECT:
                for (v0, v1) in SEA3_VRECT:
                    for m_ in maps8.values():
                        err = 0.0
                        for fx in (0, 1):
                            for fz in (0, 1):
                                a_, b_ = m_(fx, fz)
                                u, v = uvf_(cx + 4.0 * fx, cz + 4.0 * fz)
                                err = max(err, abs(u0 + a_ * (u1 - u0) - u),
                                          abs(v0 + b_ * (v1 - v0) - v))
                        err_best = min(err_best, err)
            return err_best <= eps
        samples = [t3 for (nm, c), tris in sorted(cell_tris.items()) if nm == "sea3"
                   and (nm, c) not in cell_conf for t3 in tris][:8]
        if not samples or not all(sea3_fit(t3) for t3 in samples):
            raise ValueError("sea3 here does not read as the learned quadrant language -- "
                             "refuse rather than emit an unverified band")

    # --- the BERM DRAG: terrain tris keep welding to the slid sand seam (land drags --
    # the proven fine-adjustment mechanism; the emitted foam's seam verts are the SAME
    # floats, so the weld is bit-exact by construction) ---
    seam_moves = {S[i]: (0.0, 0.0, dz[i]) for i in range(1, n - 1) if abs(dz[i]) > 1e-9}
    seam_mv_k = {_pk(p): d for p, d in seam_moves.items()}
    n_seam = 0
    for t3 in parts["terrain"]:
        if not any(_pk(v[0]) in seam_mv_k for v in t3):
            continue
        n_seam += sum(_pk(v[0]) in seam_mv_k for v in t3)
        out = []
        for (pos, nrm, uv, tan) in t3:
            d_ = seam_mv_k.get(_pk(pos))
            if d_ is not None:
                pos = (pos[0] + d_[0], pos[1] + d_[1], pos[2] + d_[2])
            out.append((pos, nrm, uv, tan))
        a0 = TR.VertexDisplace._area2(list(t3))
        a1 = TR.VertexDisplace._area2(out)
        if abs(a0) > 0.02 and (a0 * a1 <= 0.0 or abs(a1) < 0.02):
            raise ValueError(f"depth {depth:g} folds a berm tile -- the sand-slide "
                             f"envelope is geometric; reduce depth")

    # --- gates: union crack (move-aware) + water density + the ledger ---
    def once(tris):
        ec = defaultdict(int)
        for t3 in tris:
            ps = [v[0] for v in t3]
            for i2 in range(3):
                ec[frozenset((_pk(ps[i2]), _pk(ps[(i2 + 1) % 3])))] += 1
        return {e for e, cn in ec.items() if cn == 1}
    all_drop = drop_foam + drop_sea2 + drop_sea1 + drop_sea3
    all_emit = foam_emit + sea2_emit + sea1_emit + sea3_emit
    # the sand-seam boundary MOVED with the slide: map the dropped hole's seam verts
    # through the move before comparing (the dragged terrain sits at the new positions)
    mv = {_pk(S[i]): _pk(S2[i]) for i in range(n)}
    moved_drop = {frozenset(mv.get(k, k) for k in e) for e in once(all_drop)}
    if moved_drop != once(all_emit):
        raise ValueError("CRACK GATE: the reshaped ladder's outer boundary does not match "
                         "the dropped hole -- a weld or T-junction defect")

    def uv_sv(t3):
        (p0, _, uv0, _), (p1, _, uv1, _), (p2, _, uv2, _) = t3
        d1 = (p1[0] - p0[0], p1[2] - p0[2])
        d2 = (p2[0] - p0[0], p2[2] - p0[2])
        e1 = (uv1[0] - uv0[0], uv1[1] - uv0[1])
        e2 = (uv2[0] - uv0[0], uv2[1] - uv0[1])
        det = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(det) < 1e-9:
            return None
        inv = ((d2[1] / det, -d2[0] / det), (-d1[1] / det, d1[0] / det))
        a, b = (e1[0] * inv[0][0] + e2[0] * inv[1][0], e1[0] * inv[0][1] + e2[0] * inv[1][1])
        c, d = (e1[1] * inv[0][0] + e2[1] * inv[1][0], e1[1] * inv[0][1] + e2[1] * inv[1][1])
        s1 = a * a + b * b + c * c + d * d
        s2 = math.hypot(a * a + b * b - c * c - d * d, 2 * (a * c + b * d))
        return (math.sqrt(max((s1 + s2) / 2, 0.0)), math.sqrt(max((s1 - s2) / 2, 0.0)))
    for name, dropped, emitted in (("sea2", drop_sea2, sea2_emit),
                                   ("sea1", drop_sea1 or parts["sea1"], sea1_emit),
                                   ("sea3", drop_sea3 or parts["sea3"], sea3_emit)):
        if not emitted:
            continue
        real_sv = [sv for t3 in dropped if (sv := uv_sv(t3))]
        lo_env = min(s[1] for s in real_sv) * 0.7
        hi_env = max(s[0] for s in real_sv) * 1.3
        for t3 in emitted:
            sv = uv_sv(t3)
            if sv and (sv[0] > hi_env or sv[1] < lo_env):
                raise ValueError(f"WATER DENSITY GATE [{name}]: an emitted tri's uv "
                                 f"density {sv} is outside the real envelope "
                                 f"[{lo_env:.4f},{hi_env:.4f}] -- stretch/smush")
    return [tw for tw in (TR.DropTris("beach1", drop_foam),
                          TR.DropTris("sea2", drop_sea2),
                          TR.DropTris("sea1", drop_sea1) if drop_sea1 else None,
                          TR.DropTris("sea3", drop_sea3) if drop_sea3 else None,
                          TR.VertexDisplace(moves=seam_moves, expected=n_seam)
                          if seam_moves else None,
                          TR.EmitTris("beach1", foam_emit),
                          TR.EmitTris("sea2", sea2_emit),
                          TR.EmitTris("sea1", sea1_emit) if sea1_emit else None,
                          TR.EmitTris("sea3", sea3_emit) if sea3_emit else None)
            if tw is not None]


def cliff_bump(donor, start, end, depth, *, disc: int = 1, lod: str = "0_1", game=None):
    """The CONFORMING BOW (rung 1): displace the window's interior columns (crease + base +
    coincident water verts) seaward by ``depth * sin^2(pi t)``. Land UVs drag (approved
    in-game at 2.5u); water re-evaluates through its own tile map. The displacement envelope
    is geometric: a depth that folds any tile is refused here (offline), not at deploy."""
    win = CliffWindow(donor, start, end, disc=disc, lod=lod, game=game)
    ts = win.arc_params()
    moves = {}
    for i in range(1, len(win.base) - 1):
        d = depth * math.sin(math.pi * ts[i]) ** 2
        for p in (win.base[i], win.crease[i]):
            moves[p] = (d * win.nhat[0], 0.0, d * win.nhat[1])
    keyed = {_pk(p): v for p, v in moves.items()}
    _assert_pure_sea4(win, keyed, disc=disc, lod=lod, game=game)
    # the offline fold precheck (the ~2.5u envelope law, made a build-time refusal)
    for tris in (win.terr, win.sea4):
        for t3 in tris:
            if not any(_pk(v[0]) in keyed for v in t3):
                continue
            out = []
            for (pos, nrm, uv, tan) in t3:
                dd = keyed.get(_pk(pos))
                if dd is not None:
                    pos = (pos[0] + dd[0], pos[1] + dd[1], pos[2] + dd[2])
                out.append((pos, nrm, uv, tan))
            a0 = TR.VertexDisplace._area2(list(t3))
            a1 = TR.VertexDisplace._area2(out)
            if abs(a0) > 0.02 and (a0 * a1 <= 0.0 or abs(a1) < 0.02):
                raise ValueError(f"depth {depth:g} folds a tile at the waterline -- the "
                                 f"conforming-bump envelope is geometric (~2.5u on real "
                                 f"shores); use cliff_headland for a bigger move")
    n_land = sum(_pk(v[0]) in keyed for t3 in win.terr for v in t3)
    n_sea = sum(_pk(v[0]) in keyed for t3 in win.sea4 for v in t3)
    return [TR.VertexDisplace(moves=moves, expected=n_land, part="terrain"),
            TR.SeaBump(moves=moves, expected=n_sea)]


def cliff_headland(donor, start, end, depth, *, disc: int = 1, lod: str = "0_1", game=None):
    """The STRUCTURAL PROMONTORY (rung 2): rebuild the window's wall over a sin^2-pushed
    outline with ONE inserted column per gap (the gap count must be a multiple of 4 -- the
    deterministic-U-ramp law), re-fill the grass wedge natively on the 4u lattice, and zip
    the sea back to the new outline. Every law gate runs here at build time."""
    return _cliff_reshape(donor, start, end,
                          lambda t_: 1.0 * depth * math.sin(math.pi * t_) ** 2,
                          disc=disc, lod=lod, game=game)


def cliff_bay(donor, start, end, depth, *, disc: int = 1, lod: str = "0_1", game=None):
    """The structural BAY -- the promontory's inward mirror: the outline is pushed LANDWARD,
    the wedge consumes grass instead of sea (the grass drop set extends by wedge overlap,
    exactly as the sea side does for a headland), the rebuilt wall lines the bay's rim, and
    the sea zips landward over the vacated wedge. Zip tris beyond any dropped sea tile take
    the nearest tile's map TRANSLATE-CLONED (evaluated at the position shifted back into the
    source tile's own 4u cell -- the proven water fill vocabulary, never raw extrapolation).
    Same laws, same gates; the sea ledger flips (emitted - dropped == the wedge)."""
    return _cliff_reshape(donor, start, end,
                          lambda t_: -1.0 * depth * math.sin(math.pi * t_) ** 2,
                          disc=disc, lod=lod, game=game)


def cliff_lobes(donor, start, end, depths, *, disc: int = 1, lod: str = "0_1", game=None):
    """COMPOSED morphs in ONE window -- a piecewise profile of sin^2 lobes, one per entry of
    ``depths`` (signed: + = seaward headland, - = landward bay; e.g. ``(3.5, -5, 6.5)`` = a
    bay between two headlands). One reshape means the walls, fills and sea zip are continuous
    across the lobes BY CONSTRUCTION -- no per-lobe seams to certify. Each lobe joint has
    zero displacement and zero slope, so joint columns stay verbatim welds. The window still
    needs gap count = 0 (mod 4) and every law gate applies to the whole composition."""
    depths = [float(d) for d in depths]
    if not depths:
        raise ValueError("cliff_lobes needs at least one signed lobe depth")

    def profile(t_):
        n = len(depths)
        i = min(int(t_ * n), n - 1)
        return depths[i] * math.sin(math.pi * (t_ * n - i)) ** 2
    return _cliff_reshape(donor, start, end, profile, disc=disc, lod=lod, game=game)


def _cliff_reshape(donor, start, end, profile, *, disc: int = 1, lod: str = "0_1",
                   game=None):
    win = CliffWindow(donor, start, end, disc=disc, lod=lod, game=game)
    ncols = len(win.base)
    gaps = ncols - 1

    drop_wall = [t for q in win.quads for t in q]
    ck = [_pk(p) for p in win.crease]
    bk = [_pk(p) for p in win.base]
    moved_ck = set(ck[1:-1])
    moved_bk = set(bk[1:-1])
    # refinement verts VANISH (every tri touching one is dropped; nothing references them
    # after the rebuild) -- they trigger grass drops exactly like moved column creases
    refined_keys = {_pk(p) for gap in win.refined for p in gap}
    drop_grass = [t for t in win.grass
                  if _key_set(t) & (moved_ck | refined_keys)
                  or any({ck[i], ck[i + 1]} <= _key_set(t) for i in range(gaps))]
    if not drop_grass:
        # THE BAKED-TERRAIN REFUSAL: no grass behind the window's crease = a painted-mural
        # top family (highland 17/38/49 etc., e.g. the whole (9,5) island) -- there is NO
        # tile language to re-fill with (the baked-terrain law), so structural morphs
        # cannot hold here. The conforming bow (cliff_bump) still applies: it drags.
        raise ValueError("the window's top carries no grass mains -- a painted-mural family "
                         "(the baked-terrain law: no fill language). Structural morphs need "
                         "a grass top; cliff_bump (the conforming bow) still applies")
    _assert_pure_sea4(win, moved_bk | moved_ck | refined_keys, disc=disc, lod=lod, game=game)

    # --- the new outline. PINNED scheme first (the proven arithmetic: old columns
    # displaced + one new column per gap midpoint; needs gaps = 0 mod 4). If it is not
    # applicable or yields degenerate columns (multi-lobe profiles SHRINK some gaps), fall
    # back to a FREE equal-arc resample: after drop-don't-drag only the END columns are
    # welds (surv is gated 0), so interior columns place freely on the new outline --
    # total column count keeps = ncols (mod 4), so the deterministic U-ramp still lands
    # on the window-end phase. ---
    def arcpos(chain, i):
        return sum(math.dist(chain[j], chain[j + 1]) for j in range(i))
    LB = arcpos(win.base, ncols - 1)
    LCr = arcpos(win.crease, ncols - 1)
    t_cols = [arcpos(win.base, i) / LB for i in range(ncols)]

    def interp_chain(chain, s):
        acc = 0.0
        for a, b in zip(chain, chain[1:]):
            seg = math.dist(a, b)
            if acc + seg >= s - 1e-9:
                f = (s - acc) / seg
                return tuple(a[k] + f * (b[k] - a[k]) for k in range(3))
            acc += seg
        return chain[-1]
    bump_of = profile

    def build_cols(params, kinds):
        nb_, nc_ = [], []
        for t_, (kind, i) in zip(params, kinds):
            d = bump_of(t_)
            if kind == "old":
                nb = win.moved(win.base[i], d) if abs(d) > 1e-9 else win.base[i]
                nc = win.moved(win.crease[i], d) if abs(d) > 1e-9 else win.crease[i]
            else:
                nb = win.moved(interp_chain(win.base, t_ * LB), d)
                nb = (nb[0], 0.0, nb[2])
                nc = win.moved(interp_chain(win.crease, t_ * LCr), d)
            nb_.append(nb)
            nc_.append(nc)
        return nb_, nc_
    new_base = None
    if gaps % 4 == 0:
        params, kinds = [], []
        for i in range(gaps):
            params.append(t_cols[i])
            kinds.append(("old", i))
            params.append((t_cols[i] + t_cols[i + 1]) / 2.0)
            kinds.append(("new", None))
        params.append(1.0)
        kinds.append(("old", ncols - 1))
        new_base, new_crease = build_cols(params, kinds)
        widths = [math.dist(a, b) for a, b in zip(new_base, new_base[1:])]
        if min(widths) < 2.0:
            new_base = None                                # fall through to the free resample
    if new_base is None:
        import bisect
        nd = 512
        dts = [j / nd for j in range(nd + 1)]
        acc = [0.0]
        prev = None
        for t_ in dts:
            p = win.moved(interp_chain(win.base, t_ * LB), bump_of(t_))
            if prev is not None:
                acc.append(acc[-1] + math.hypot(p[0] - prev[0], p[2] - prev[2]))
            prev = p
        new_arc_est = acc[-1]
        cands = [ncols + 4 * k for k in range(-2, 4) if ncols + 4 * k >= 5]
        total = min(cands, key=lambda c: abs(new_arc_est / (c - 1) - 4.4))
        params, kinds = [0.0], [("old", 0)]
        for j in range(1, total - 1):
            s = new_arc_est * j / (total - 1)
            idx = min(max(bisect.bisect_left(acc, s), 1), nd)
            f = (s - acc[idx - 1]) / ((acc[idx] - acc[idx - 1]) or 1.0)
            params.append(dts[idx - 1] + f * (dts[idx] - dts[idx - 1]))
            kinds.append(("new", None))
        params.append(1.0)
        kinds.append(("old", ncols - 1))
        new_base, new_crease = build_cols(params, kinds)
        widths = [math.dist(a, b) for a, b in zip(new_base, new_base[1:])]
        if min(widths) < 2.0:
            raise ValueError(f"degenerate wall column ({min(widths):.2f}u) even at equal "
                             f"arc -- widen the window or reduce depth")
    head_moves = {}
    for idx, (kind, i) in enumerate(kinds):
        if kind == "old" and 0 < i < ncols - 1:
            d = bump_of(params[idx])
            for p in (win.base[i], win.crease[i]):
                head_moves[p] = (d * win.nhat[0], 0.0, d * win.nhat[1])

    # --- the extended drop sets: moved-vert fans + wedge overlap (the wedge consumes SEA
    # for a headland and GRASS for a bay -- both sides get the symmetric overlap clause) ---
    wedge_poly = [(p[0], p[2]) for p in new_base] + \
                 [(p[0], p[2]) for p in reversed(win.base)]

    def _pip_strict(px, pz, t3, eps=1e-6):
        (ax, _, az), (bx, _, bz), (cx, _, cz) = (v[0] for v in t3)
        d1 = (px - bx) * (az - bz) - (ax - bx) * (pz - bz)
        d2 = (px - cx) * (bz - cz) - (bx - cx) * (pz - cz)
        d3 = (px - ax) * (cz - az) - (cx - ax) * (pz - az)
        return (d1 > eps and d2 > eps and d3 > eps) or (d1 < -eps and d2 < -eps and d3 < -eps)

    def _overlaps(t3, poly):
        # STRICT interior only -- a tri merely TOUCHING the footprint boundary (a fixed
        # window-end vert on its edge) must not drop; boundary-inclusive tests over-drop
        cx = sum(v[0][0] for v in t3) / 3.0
        cz = sum(v[0][2] for v in t3) / 3.0
        return (_in_poly(cx, cz, poly)
                or any(_in_poly(v[0][0], v[0][2], poly) for v in t3)
                or any(_pip_strict(px, pz, t3) for (px, pz) in poly))
    # THE REACH GATE: the morph's footprint may touch ONLY sea4 water -- a wedge lobe
    # overlapping an undropped sea1/2/3/5/beach1 tile would leave new land poking through
    # (or a shore band unre-zipped). Windows near a shallow ladder get an honest refusal.
    for part in ("sea1", "sea2", "sea3", "sea5", "beach1"):
        tris = TR.world_tris(*win.donor, part, disc=disc, lod=lod, game=game)
        for t3 in tris:
            if _overlaps(t3, wedge_poly):
                raise ValueError(f"the morph's footprint reaches {part} -- a cliff morph "
                                 f"needs pure sea4 within its reach (the cliff seam law); "
                                 f"shrink the lobe or move the window")

    # the sea overlap keeps the PROVEN headland semantics exactly (boundary-inclusive --
    # shore-touching tiles are fan members anyway); only the grass path is strict
    drop_sea = [t3 for t3 in win.sea4
                if _key_set(t3) & moved_bk
                or any(_in_poly(v[0][0], v[0][2], wedge_poly) for v in t3)
                or any(_pip_xz(px, pz, t3) for (px, pz) in wedge_poly)]
    # grass is consumed up to the CREASE line (the land component begins there, one wall-run
    # inland of the base) -- a bay's grass overlap tests the crease-based footprint, along
    # the FULL old crease chain (refinement verts bend the real crease line)
    crease_poly = [(p[0], p[2]) for p in new_crease] + \
                  [(p[0], p[2]) for p in reversed(win.crease_chain)]
    have = {_key_set(t) for t in drop_grass}
    drop_grass = drop_grass + [t3 for t3 in win.grass
                               if _key_set(t3) not in have and _overlaps(t3, crease_poly)]
    # every interior outline vert (base AND crease) must land in DROPPED territory (sea for
    # a headland, grass/wall for a bay) -- else the refill polygons cannot contain it
    dropped_all = drop_sea + drop_wall + drop_grass
    for chain in (new_base, new_crease):
        for i, nb in enumerate(chain[1:-1], 1):
            if not any(_pip_xz(nb[0], nb[2], t3) for t3 in dropped_all):
                raise ValueError(f"new outline vert {i} escapes the drop sets -- depth too "
                                 f"large for the local terrain/water (a component or frame "
                                 f"within reach)")

    # --- wall emissions: per-quad corner copy by LEFT-COLUMN PHASE (wrap seams come free).
    # The 4 patterns come from the window's CLEAN gaps keyed by their canonical ramp U
    # (a refined gap cannot donate a pattern but still steps ONE tile -- measured); the new
    # run's left-U ramps the deterministic cycle from the window-start phase, which on a
    # clean-gap window reproduces the positional qi%4 mapping exactly. ---
    CYC = (0.8242, 0.7617, 0.6992, 0.8867)

    def canon_u(vals):
        # the wrap quad's corners carry the SEAM value (canonical + 0.25) -- fold both ways
        for u in vals:
            for u2 in (u, u - 0.25, u + 0.25):
                for c in CYC:
                    if abs(u2 - c) < 0.004:
                        return c
        return None
    phase_pat = {}
    u0 = None
    for qi in range(gaps):
        if len(win.quads[qi]) != 2:
            continue
        roles = {bk[qi]: "bl", ck[qi]: "cl", bk[qi + 1]: "br", ck[qi + 1]: "cr"}
        out = {}
        for t3 in win.quads[qi]:
            for v in t3:
                out.setdefault(roles[_pk(v[0])], (v[2], v[1]))
        split = [tuple(roles[_pk(v[0])] for v in t3) for t3 in win.quads[qi]]
        u = canon_u([out["bl"][0][0], out["cl"][0][0]])
        if u is not None:
            phase_pat.setdefault(u, (out, split))
            if u0 is None:
                u0 = CYC[(CYC.index(u) - qi) % 4]      # back-step the ramp to gap 0
    if len(phase_pat) < 4:
        raise ValueError(f"the window's clean gaps cover only {len(phase_pat)}/4 texture "
                         f"phases -- widen the window")
    idall_wall = tuple(drop_wall[0][0][3])
    wall_emit = []
    for qi in range(len(new_base) - 1):
        corners, split = phase_pat[CYC[(CYC.index(u0) + qi) % 4]]
        pos = {"bl": new_base[qi], "br": new_base[qi + 1],
               "cl": new_crease[qi], "cr": new_crease[qi + 1]}
        for tri_roles in split:
            wall_emit.append([(pos[r], corners[r][1], corners[r][0], idall_wall)
                              for r in tri_roles])

    # --- the native grass fill over the hole + wedge. THE RING-EXTENSION LADDER: a bay
    # rim diving within a couple of units of the hole's inner boundary leaves a SUB-GRAIN
    # corridor no triangulation can make lawful -- when the fill fails its gates, consume
    # one more grass ring along the LANDWARD-displaced segments (drop-don't-drag, one level
    # deeper) and rebuild. Margin 0 runs first, keeping the proven builds byte-identical. ---
    cell_quad = {}
    for t3 in win.grass:
        cx = math.floor(sum(v[0][0] for v in t3) / 3.0 / 4.0)
        cz = math.floor(sum(v[0][2] for v in t3) / 3.0 / 4.0)
        cell_quad.setdefault((cx, cz), TR._quad_of_uv(t3[0][2]))
    d_cols = [bump_of(t_) for t_ in params]
    bay_segs = [(new_crease[i], new_crease[i + 1]) for i in range(len(new_crease) - 1)
                if min(d_cols[i], d_cols[i + 1]) < -0.25]

    def _seg_dist(p, a, b):
        ex, ez = b[0] - a[0], b[2] - a[2]
        L2 = ex * ex + ez * ez or 1.0
        tt = max(0.0, min(1.0, ((p[0] - a[0]) * ex + (p[2] - a[2]) * ez) / L2))
        return math.hypot(p[0] - (a[0] + tt * ex), p[2] - (a[2] + tt * ez))
    grass_emit = None
    last_err = None
    for margin in (0.0, 3.2):
        dg = drop_grass
        if margin > 0.0:
            if not bay_segs:
                break
            have = {_key_set(t) for t in dg}
            dg = dg + [t3 for t3 in win.grass if _key_set(t3) not in have
                       and any(_seg_dist(v[0], a, b) < margin
                               for v in t3 for (a, b) in bay_segs)]
        try:
            grass_emit = _grass_fill(win, dg, new_crease, ck, cell_quad)
            drop_grass = dg
            break
        except ValueError as e:
            last_err = e
    if grass_emit is None:
        raise last_err
    # --- the sea ZIP STRIP back to the new outline ---
    loop, pos_of, uv_of, nrm_of = _boundary_loop(drop_sea)
    shore = list(bk)
    for k in shore:
        i0 = loop.index(k)
        rot = loop[i0:] + loop[:i0]
        if set(rot[:ncols]) == set(shore):
            loop = rot
            break
    else:
        raise ValueError("shore run not contiguous in the sea hole boundary")
    outline_pts = new_base if loop[0] == bk[0] else list(reversed(new_base))
    A_chain = outline_pts
    B_chain = [pos_of[k] for k in reversed(loop[ncols:])]
    zip_tris = []
    i = j = 0
    while i < len(A_chain) - 1 or j < len(B_chain) - 1:
        if j == len(B_chain) - 1:
            adv_a = True
        elif i == len(A_chain) - 1:
            adv_a = False
        else:
            adv_a = (math.dist(A_chain[i + 1], B_chain[j])
                     <= math.dist(A_chain[i], B_chain[j + 1]))
        if adv_a:
            zip_tris.append((A_chain[i], B_chain[j], A_chain[i + 1]))
            i += 1
        else:
            zip_tris.append((A_chain[i], B_chain[j], B_chain[j + 1]))
            j += 1
    cell_tile = {}
    for t3 in drop_sea:
        cx = sum(v[0][0] for v in t3) / 3.0
        cz = sum(v[0][2] for v in t3) / 3.0
        cell_tile.setdefault((math.floor(cx / 4.0), math.floor(cz / 4.0)), t3)

    def tile_for(cx, cz):
        """The zip tri's source tile + a translate offset: the centroid's own cell if a
        dropped tile covers it (offset zero -- the proven headland path), else the nearest
        dropped tile TRANSLATE-CLONED by the integer 4u cell delta (the proven water fill
        vocabulary -- the map is evaluated inside the source tile's own footprint, never
        raw-extrapolated tiles away; a bay's new water sits beyond every dropped tile)."""
        c = (math.floor(cx / 4.0), math.floor(cz / 4.0))
        if c in cell_tile:
            return cell_tile[c], (0.0, 0.0)
        best, bd = None, 1e18
        for t3 in drop_sea:
            tx = sum(v[0][0] for v in t3) / 3.0
            tz = sum(v[0][2] for v in t3) / 3.0
            d2 = (cx - tx) ** 2 + (cz - tz) ** 2
            if d2 < bd:
                best, bd = t3, d2
        bx_ = sum(v[0][0] for v in best) / 3.0
        bz_ = sum(v[0][2] for v in best) / 3.0
        bc = (math.floor(bx_ / 4.0), math.floor(bz_ / 4.0))
        return best, (4.0 * (c[0] - bc[0]), 4.0 * (c[1] - bc[1]))
    idall_sea = tuple(drop_sea[0][0][3])
    ring_nrm = nrm_of[bk[len(bk) // 2]]
    sea_ring = []
    for (pa, pb, pc) in zip_tris:
        cx = (pa[0] + pb[0] + pc[0]) / 3.0
        cz = (pa[2] + pb[2] + pc[2]) / 3.0
        src, (ox, oz) = tile_for(cx, cz)
        uvf = TR._affine_uv(src)
        # PURE affine, no clamp: the tri carries EXACTLY a real tile's map (a clamp squashes
        # far verts onto the bbox edge = smear); extrapolation lands in a sibling quadrant of
        # the same tiling water texture -- content, not gutter.
        t3 = [(p, ring_nrm, tuple(uvf(p[0] - ox, p[2] - oz)), idall_sea)
              for p in (pa, pb, pc)]
        ux, uz = t3[1][0][0] - t3[0][0][0], t3[1][0][2] - t3[0][0][2]
        vx, vz = t3[2][0][0] - t3[0][0][0], t3[2][0][2] - t3[0][0][2]
        if uz * vx - ux * vz <= 0:
            t3 = [t3[0], t3[2], t3[1]]
        if TR._tri_area2_3d(t3) < 1e-6:
            continue
        sea_ring.append(t3)

    # THE WATER DENSITY GATE + THE LEDGER
    def uv_sv(t3):
        (p0, _, uv0, _), (p1, _, uv1, _), (p2, _, uv2, _) = t3
        d1 = (p1[0] - p0[0], p1[2] - p0[2])
        d2 = (p2[0] - p0[0], p2[2] - p0[2])
        e1 = (uv1[0] - uv0[0], uv1[1] - uv0[1])
        e2 = (uv2[0] - uv0[0], uv2[1] - uv0[1])
        det = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(det) < 1e-9:
            return None
        inv = ((d2[1] / det, -d2[0] / det), (-d1[1] / det, d1[0] / det))
        a, b = (e1[0] * inv[0][0] + e2[0] * inv[1][0], e1[0] * inv[0][1] + e2[0] * inv[1][1])
        c, d = (e1[1] * inv[0][0] + e2[1] * inv[1][0], e1[1] * inv[0][1] + e2[1] * inv[1][1])
        s1 = a * a + b * b + c * c + d * d
        s2 = math.hypot(a * a + b * b - c * c - d * d, 2 * (a * c + b * d))
        return (math.sqrt(max((s1 + s2) / 2, 0.0)), math.sqrt(max((s1 - s2) / 2, 0.0)))
    real_sv = [sv for t3 in drop_sea if (sv := uv_sv(t3))]
    lo_env = min(s[1] for s in real_sv) * 0.7
    hi_env = max(s[0] for s in real_sv) * 1.3
    for t3 in sea_ring:
        sv = uv_sv(t3)
        if sv and (sv[0] > hi_env or sv[1] < lo_env):
            raise ValueError(f"WATER DENSITY GATE: a ring tri's uv density {sv} is outside "
                             f"the real envelope [{lo_env:.4f},{hi_env:.4f}] -- stretch/smush")

    def plan_area(tris):
        s = 0.0
        for t3 in tris:
            (ax, _, az), (bx, _, bz), (cx, _, cz) = (v[0] for v in t3)
            s += abs((bx - ax) * (cz - az) - (cx - ax) * (bz - az)) / 2.0
        return s
    poly_a = 0.0
    for i in range(len(wedge_poly)):
        (x1, z1), (x2, z2) = wedge_poly[i], wedge_poly[(i + 1) % len(wedge_poly)]
        poly_a += x1 * z2 - x2 * z1
    poly_a = poly_a / 2.0                      # SIGNED shoelace: mixed lobes net out
    # the sea ledger is SIGNED: seaward lobes consume sea, landward lobes yield it; the
    # net must match the wedge's signed area (orientation-agnostic: either sign matches)
    delta = plan_area(drop_sea) - plan_area(sea_ring)
    if min(abs(delta - poly_a), abs(delta + poly_a)) > 1.0:
        raise ValueError("LEDGER: net dropped-emitted sea != the wedge's signed area")

    excl = [_key_set(t) for t in drop_wall + drop_grass + drop_sea]
    surv = _count_instances(win, {_pk(p) for p in head_moves}, exclude_sets=excl)
    # in the FREE-resample scheme interior columns are DELETED, not moved: any surviving
    # reference (a non-grass/sea component touching the crease) would be a crack
    surv_all = _count_instances(win, moved_ck | moved_bk | refined_keys, exclude_sets=excl)
    if surv_all > surv:
        raise ValueError(f"{surv_all - surv} surviving tri-vert instance(s) reference "
                         f"deleted window columns -- a component outside the drop sets "
                         f"touches the crease; the drop-don't-drag law cannot hold here")
    return [TR.DropTris("terrain", drop_wall + drop_grass),
            TR.DropTris("sea4", drop_sea),
            TR.VertexDisplace(moves=head_moves, expected=surv),
            TR.EmitTris("terrain", wall_emit + grass_emit),
            TR.EmitTris("sea4", sea_ring)]
