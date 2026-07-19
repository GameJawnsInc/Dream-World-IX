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
from collections import Counter, defaultdict

from . import grassland as G
from . import transplant as TR
from .extract import decode_id, encode_id
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
    in another water part would stay behind under the part-scoped tweaks = a weld crack.
    The refusal NAMES the offending vert (positional -- the coast window scanner steers
    its sub-window search by it, like the ``window gap K`` decode refusals)."""
    for part in ("sea1", "sea2", "sea3", "sea5", "beach1"):
        tris = TR.world_tris(*win.donor, part, disc=disc, lod=lod, game=game)
        hits = [v[0] for t3 in tris for v in t3 if _pk(v[0]) in keyed]
        if hits:
            raise ValueError(f"the morph window's waterline touches {part} ({len(hits)} "
                             f"vert instance(s), first at ({hits[0][0]:.4f},"
                             f"{hits[0][2]:.4f})) -- cliff morphs need a pure-sea4 shore "
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
    idall_grass = tuple(drop_grass[0][0][3])
    return _grass_fill_region(bpts3, gnrm, cell_quad, idall_grass)


def _grass_fill_region(bpts3, gnrm, cell_quad, idall_grass):
    """The native lattice grass fill over ONE closed boundary loop ``bpts3`` (3D verts,
    ordered) -- the region-generic core shared by the cliff structural morphs
    (:func:`_grass_fill`) and the beach slide's vacated-strip fill: 4u interior lattice,
    Delaunay, per-cell mains with the avoid-same policy vs ``cell_quad`` (the REAL
    neighbouring tiles' quadrant picks), the CRACK GATE (fill once-edges == the loop
    exactly) and the GRAIN GATE."""
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


def _freeform_window(donor, start, end, *, disc=1, lod="0_1", game=None):
    """The FREE-FORM shore window decode (chain-walk, no lattice-column assumption) --
    the shared opening of :func:`beach_bump` and the seaward :func:`beach_slide`:
    beach1's boundary loop, the waterline run between the snapped endpoints (interior
    verts sea2-welded, terrain-free), the seaward normal by THE DEFINITIVE RULE (minus
    the mean per-vert wl->nearest-seam direction), and the arc parameterization."""
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

    # seaward normal: MINUS the mean wl->nearest-seam direction, per window vert (the
    # definitive local rule -- a global sand centroid flips on multi-beach islands, and
    # centroid mid-tests flip on curved runs: the (9,17)/(19,16) lessons, 2026-07-10)
    seam_all = [pos_of[k] for k in adj if k in reg["terrain"]]
    if not seam_all:
        raise ValueError("the beach has no sand seam -- not a morphable shore")
    sdx = sdz = 0.0
    for p in pts:
        q = min(seam_all, key=lambda q: math.hypot(p[0] - q[0], p[2] - q[2]))
        dq = math.hypot(p[0] - q[0], p[2] - q[2]) or 1.0
        sdx += (q[0] - p[0]) / dq
        sdz += (q[2] - p[2]) / dq
    t = (pts[-1][0] - pts[0][0], pts[-1][2] - pts[0][2])
    tl = math.hypot(*t) or 1.0
    nh = (-t[1] / tl, t[0] / tl)
    if nh[0] * sdx + nh[1] * sdz > 0:
        nh = (-nh[0], -nh[1])

    acc, arcs = 0.0, [0.0]
    for a, b in zip(pts, pts[1:]):
        acc += math.dist(a, b)
        arcs.append(acc)
    return beach, others, reg, pos_of, adj, pts, nh, arcs, acc, seam_all


def beach_bump(donor, start, end, depth, *, disc: int = 1, lod: str = "0_1", game=None):
    """The BEACH conforming bow -- the waterline move on a sandy shore (the beach frontier's
    rung 1). A beach is an INTERLEAVED RAMP ASSEMBLY: sand terrain -> beach1 foam (the swash
    ribbon, Y 0.2..1.2) -> sea2 wash, welded at two chains -- the WATERLINE (beach1's seaward
    boundary, every vert shared bit-exact with sea2) and the SAND SEAM (shared with terrain),
    with load-bearing multi-part END-CAP welds. The bow is ONE displacement FIELD over the
    whole assembly (sin^2 along-shore profile, + = seaward): the waterline at factor 1, the
    seaward water tapered over the depth-scaled reach (the LADDER TAPER -- strain <=~16%,
    verbatim drag), and -- THE HUG LAW (user-called in-game 2026-07-10; within-beach swash
    width is near-constant map-wide) -- the LANDWARD side rides too: flat factor across the
    swash + sand seam, cos^2 decay over the berm, so the foam line stays parallel to the
    sand's hard edge and the berm terrain DRAGS (the proven land fine-adjustment mechanism,
    which also caps |depth| at ~2.5). THE SHAPE-CLASS GATE rules direction: a beach may
    deepen its own chord-relative curvature (a nose grows seaward, a pocket landward), never
    cross toward the opposite class. Frame verts are PINNED (a moved block-frame vert opens
    a sliver against the neighbour prefab); the strain gate judges the pin's cost. Works on
    FREE-FORM shores (conforming waterlines, unmatched chains) -- the chain-walk decoder
    has no lattice-column assumption, unlike :func:`beach_reshape`."""
    if abs(depth) > 2.6:
        raise ValueError("the assembly bow DRAGS the berm -- the land-drag envelope caps "
                         "depth at ~2.5 (the cliff-bump precedent); past it, use "
                         "beach_slide (the full-assembly slide)")
    (beach, others, reg, pos_of, adj, pts, nh,
     arcs, acc, seam_all) = _freeform_window(donor, start, end,
                                             disc=disc, lod=lod, game=game)

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

    fx0, fx1 = 64.0 * donor[0], 64.0 * donor[0] + 64.0
    fz0, fz1 = -64.0 * donor[1] - 64.0, -64.0 * donor[1]

    def near_frame(p, eps=1.5):
        return (min(p[0] - fx0, fx1 - p[0]) < eps or min(p[2] - fz0, fz1 - p[2]) < eps)
    moves = {}                                    # the waterline chain (foam side, factor 1)
    for i in range(1, len(pts) - 1):
        if near_frame(pts[i], eps=0.05):          # ON the frame = a neighbour weld: never
            raise ValueError(f"waterline vert ({pts[i][0]:.0f},{pts[i][2]:.0f}) sits on "
                             f"the block frame -- shrink the window off the frame")
        d = depth * math.sin(math.pi * arcs[i] / acc) ** 2
        moves[pts[i]] = (d * nh[0], 0.0, d * nh[1])
    sand_seam = [pos_of[k] for k in adj if k in reg["terrain"]]
    swash_flat = 1.0 + max(min(math.hypot(p[0] - q[0], p[2] - q[2]) for q in sand_seam)
                           for p in moves) if sand_seam and moves else 6.0
    LAND_REACH = 8.0
    water_moves = dict(moves)                     # + the tapered fields, both sides
    for name in ("sea1", "sea2", "sea3", "sea5", "sea4", "terrain", "beach1"):
        for t3 in (beach if name == "beach1" else others[name]):
            for v in t3:
                k = _pk(v[0])
                if k in {_pk(p) for p in water_moves} or near_frame(v[0]):
                    continue
                d, f = chain_param(v[0])
                if abs(d) < 1e-6:
                    continue
                if f > 0.05:                      # seaward: the ladder taper
                    if f >= TAPER_REACH or name in ("terrain", "beach1"):
                        continue
                    fac = math.cos(math.pi / 2.0 * f / TAPER_REACH) ** 2
                elif f < -0.05:                   # landward: the assembly rides (hug)
                    if name not in ("terrain", "beach1"):
                        continue
                    fl = -f
                    if fl <= swash_flat:
                        fac = 1.0
                    elif fl < swash_flat + LAND_REACH:
                        fac = math.cos(math.pi / 2.0 * (fl - swash_flat) / LAND_REACH) ** 2
                    else:
                        continue
                else:                             # on the waterline but not a chain vert
                    fac = 1.0 if name == "beach1" else \
                        math.cos(math.pi / 2.0 * max(f, 0.0) / TAPER_REACH) ** 2
                if abs(d * fac) < 0.05:
                    continue
                water_moves[v[0]] = (d * fac * nh[0], 0.0, d * fac * nh[1])
    keyed = {_pk(p): v for p, v in water_moves.items()}

    def _mvp(p):
        d_ = keyed.get(_pk(p))
        return (p[0] + d_[0], p[1], p[2] + d_[2]) if d_ else p

    # THE RIBBON + HUG GATES: the swash stays inside the real absolute envelope AND rides
    # the (moved) sand edge -- within-beach width is near-constant (the hug law)
    for p in list(moves):
        d0 = min(math.hypot(p[0] - q[0], p[2] - q[2]) for q in sand_seam)
        pm = _mvp(p)
        d1 = min(math.hypot(pm[0] - q[0], pm[2] - q[2]) for q in (_mvp(q) for q in sand_seam))
        # the hug always binds; the absolute envelope only binds verts that START inside
        # it (a verbatim outlier -- e.g. a wide frame tail -- may ride, never re-band)
        if abs(d1 - d0) > 0.6 or (2.6 <= d0 <= 8.2 and not (2.6 <= d1 <= 8.2)):
            raise ValueError(f"RIBBON/HUG GATE: the bow moves the swash {d0:.1f} -> "
                             f"{d1:.1f}u at ({p[0]:.0f},{p[2]:.0f}) -- the ribbon must "
                             f"ride the sand edge inside the real envelope; reduce depth")

    # THE SHAPE-CLASS GATE: deepen the beach's own chord-relative curvature, never cross
    # toward the opposite class (the coast behind sets the class)
    a2, b2 = pts[0], pts[-1]
    ex2, ez2 = b2[0] - a2[0], b2[2] - a2[2]
    L2 = math.hypot(ex2, ez2) or 1.0
    nx2, nz2 = -ez2 / L2, ex2 / L2
    if nx2 * nh[0] + nz2 * nh[1] < 0:            # align with the seaward normal
        nx2, nz2 = -nx2, -nz2

    def _dev2(p):
        return (p[0] - a2[0]) * nx2 + (p[2] - a2[2]) * nz2
    d0s = [_dev2(p) for p in pts[1:-1]]
    d1s = [_dev2(_mvp(p)) for p in pts[1:-1]]
    sea_cap = 0.25 * L2 if max(d0s) > 0.5 else max(d0s) + 0.3
    land_cap = -0.48 * L2 if min(d0s) < -0.5 else min(d0s) - 0.3
    if max(d1s) > sea_cap + 1e-6 or min(d1s) < land_cap - 1e-6:
        klass = "convex (headland-nose)" if max(d0s) > 0.5 else \
                "concave (pocket)" if min(d0s) < -0.5 else "straight"
        raise ValueError(f"SHAPE-CLASS GATE: this beach is {klass} (chord devs "
                         f"{min(d0s):.1f}..{max(d0s):.1f} over {L2:.0f}u); the bow takes "
                         f"it to {min(d1s):.1f}..{max(d1s):.1f}, past its class envelope "
                         f"[{land_cap:.1f},{sea_cap:.1f}] -- a beach may deepen its own "
                         f"curvature, never cross toward the opposite class")

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
    # THE BAND GATE: no shore band may compress below ~60% of its verbatim width (the
    # ladder-taper's whole point -- the pinched wash was the in-game seam)
    reg_pk = {n: {_pk(v[0]) for t3 in t for v in t3} for n, t in others.items()}
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


def _tvertex_gate(near):
    """THE T-VERTEX GATE: over ``near`` = [(is_new, t3), ...], no NEW/MOVED vert may sit
    strictly inside another terrain edge and no vert mid a NEW edge -- the offline
    oracle for angle-dependent rasterization pinholes (the playtest seam class).
    Pre-existing donor T-junctions are not ours to judge: only pairs involving our
    delta are gated."""
    new_vk = {_pk(v[0], 6) for nw, t3 in near if nw for v in t3}
    vset = {}
    for _, t3 in near:
        for v in t3:
            vset.setdefault(_pk(v[0], 6), v[0])
    for nw, t3 in near:
        for k2 in range(3):
            a, b = t3[k2][0], t3[(k2 + 1) % 3][0]
            ka2, kb2 = _pk(a, 6), _pk(b, 6)
            ex, ey, ez = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            el2 = ex * ex + ez * ez
            if el2 < 1e-12:
                continue
            for kp, p in vset.items():
                if kp in (ka2, kb2) or (not nw and kp not in new_vk):
                    continue
                t_ = ((p[0] - a[0]) * ex + (p[2] - a[2]) * ez) / el2
                if not (1e-4 < t_ < 1 - 1e-4):
                    continue
                dx = a[0] + t_ * ex - p[0]
                dzz = a[2] + t_ * ez - p[2]
                if dx * dx + dzz * dzz < 1e-10 \
                        and abs(a[1] + t_ * ey - p[1]) < 1e-3:
                    raise ValueError(
                        f"T-VERTEX GATE: vert ({p[0]:.3f},{p[2]:.3f}) sits mid-edge "
                        f"on another terrain tri -- an angle-dependent pinhole (the "
                        f"playtest seam class)")


def _merge_loops(pieces, kd: int = 9):
    """Merge one source tri's BSP fragments back into boundary LOOP(s) (internal edges
    appear twice with bit-identical verts -- same clip lines, same interpolation -- and
    cancel; boundary edges appear once and chain). THE T-VERTEX LAW (in-game 2026-07-10,
    'a small seam ... only visible from certain camera angles'): fragment interfaces run
    along the strip quads' INFINITE edge lines, so emitting fragments directly plants
    mid-edge verts on edges shared with UNSPLIT neighbours -- classic angle-dependent
    rasterization pinholes. Re-triangulating the merged loop uses only loop verts."""
    edges = {}
    for piece in pieces:
        m = len(piece)
        for k in range(m):
            a, b = piece[k], piece[(k + 1) % m]
            ka, kb = _pk(a[0], kd), _pk(b[0], kd)
            if ka == kb:
                continue
            edges.setdefault(frozenset((ka, kb)), []).append((ka, a, b))
    nxt = {}
    for insts in edges.values():
        if len(insts) == 1:
            ka, a, b = insts[0]
            nxt[ka] = (a, b, _pk(b[0], kd))
    loops, seen = [], set()
    for start in list(nxt):
        if start in seen:
            continue
        loop, k = [], start
        while k in nxt and k not in seen:
            seen.add(k)
            a, b, kb = nxt[k]
            loop.append(a)
            k = kb
        if len(loop) >= 3 and k == start:
            loops.append(loop)
    return loops


def _drop_collinear(loop, keep_keys, eps: float = 1e-6):
    """Remove a loop's collinear (plan) verts EXCEPT load-bearing chain verts -- the
    spurious quad-line-extension verts on straight perimeter edges are exactly what
    plants T-vertices against unsplit neighbours. Clip verts are 3D-collinear on their
    source edge (lerp), so plan collinearity is safe to judge by."""
    out = list(loop)
    changed = True
    while changed and len(out) > 3:
        changed = False
        for k in range(len(out)):
            b = out[k]
            if _pk(b[0]) in keep_keys:
                continue
            a, c = out[k - 1], out[(k + 1) % len(out)]
            cr = ((b[0][0] - a[0][0]) * (c[0][2] - a[0][2])
                  - (c[0][0] - a[0][0]) * (b[0][2] - a[0][2]))
            if abs(cr) < eps * max(1.0, math.hypot(c[0][0] - a[0][0],
                                                   c[0][2] - a[0][2])):
                del out[k]
                changed = True
                break
    return out


def _ear_clip(loop):
    """Triangulate a simple (possibly non-convex) xz loop using ONLY its own verts."""
    pts = list(loop)
    a2 = sum(pts[k][0][0] * pts[(k + 1) % len(pts)][0][2]
             - pts[(k + 1) % len(pts)][0][0] * pts[k][0][2] for k in range(len(pts)))
    if a2 < 0:
        pts.reverse()

    def cross(a, b, c):
        return ((b[0][0] - a[0][0]) * (c[0][2] - a[0][2])
                - (c[0][0] - a[0][0]) * (b[0][2] - a[0][2]))
    out, guard = [], 0
    while len(pts) > 3 and guard < 4096:
        guard += 1
        for k in range(len(pts)):
            a, b, c = pts[k - 1], pts[k], pts[(k + 1) % len(pts)]
            if cross(a, b, c) <= 1e-9:
                continue                             # reflex or degenerate corner
            if any(p is not a and p is not b and p is not c
                   and _pip_xz(p[0][0], p[0][2], (a, b, c)) for p in pts):
                continue                             # another vert inside the ear
            out.append([a, b, c])
            del pts[k]
            break
        else:
            break                                    # no ear found (degenerate loop)
    if len(pts) == 3:
        out.append(list(pts))
    return out


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


def beach_reshape(donor, start, end, depth, *, disc: int = 1, lod: str = "0_1", game=None,
                  _assembly: bool = False):
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
    if not _assembly and abs(depth) > 2.6:
        raise ValueError("the sand-slide DRAGS the berm -- the land-drag envelope caps "
                         "depth at ~2.5 (the cliff-bump precedent); past it, use "
                         "beach_slide (the full-assembly slide)")
    if _assembly and not (-6.0 <= depth < 0):
        raise ValueError("beach_slide v1 slides LANDWARD only (-6 <= depth < 0): a "
                         "seaward slide vacates the berm strip BEHIND the band, and a "
                         "painted-wash berm has no fill language (the baked-terrain "
                         "refusal) -- the grass-berm seaward rung is a later vocabulary")
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

    # THE SHAPE-CLASS GATE (user-called in-game 2026-07-10; the class envelope re-derived
    # over a corrected 32-run census 2026-07-18): a beach's convexity class is INHERITED
    # from the coastline it aprons -- headland-nose beaches bow seaward of their cap-to-cap
    # chord (no more than +19% of length), pocket beaches recede landward of it (up to -46%
    # of length). A morph may DEEPEN the beach's own curvature but must never push past its
    # own extreme toward the OPPOSITE class: a pocket that crosses its chord reads as the
    # beach peeling off the coast (the v2 'extruded ends'), because the land behind it is
    # still concave. Devs are chord-relative, seaward-positive.
    # (2026-07-18 correction: the earlier "37-run, nose up to +46%" reading was a POCKET
    # misread -- the +46% figure belongs to pocket recede, not nose bow; the sea_cap/
    # land_cap constants below were already asymmetric in the nose/pocket-correct direction
    # and are unaffected by this prose fix.)
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
    sea_cap = 0.25 * L_ if max(d0) > 0.5 else max(d0) + 0.3
    land_cap = -0.48 * L_ if min(d0) < -0.5 else min(d0) - 0.3
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
    for name in ("sea2", "sea1", "sea3", "sea5", "sea4"):
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
        if name not in ("sea1", "sea5"):
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
            if (po is None and eo == "sea4"
                    and src[1] < int(-(donor[1] + 1) * 64 / 4)):
                break        # the block frame: beyond is prefab open ocean -- sea4 knits
            if po is None or eo is None:
                raise ValueError(f"the pullback walks off the census at ({ci},{j})")
            ps, es = shade.get(src), shade.get(c)
            # a strip band (sea1/sea5 -- ONE learned language, sea1 = sea5's a rung
            # down) reconciles only shade-to-shade; sea3 (anti-tiling quadrants) and
            # sea4 (open water, the knit law) reconcile band-to-band. THE GRADED-LADDER
            # RE-LAY: a full-row slide shifts the whole ladder, so the walk re-labels
            # sea5's top rows too and terminates in sea4 -- the customer sea5 emission
            # was proven for (strips_rebuild, 2026-07-10).
            if po == eo and (po not in ("sea1", "sea5")
                             or (ps is not None and ps == es)):
                break                                # reconciled: below stays verbatim
            if po in ("sea1", "sea5") and ps is None:
                raise ValueError(f"pullback source ({ci},{j + t}) is {po} but "
                                 f"undecodable (an inset/conforming residual) -- "
                                 f"shift the window")
            changes[c] = (po, ps if po in ("sea1", "sea5") else None)
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
            # {sea1, sea5} is NOT illegal: the real (7,17) ring carries it at
            # (122,-286)|(123,-286) -- the two strip fields' edge shades explain it
            # (each band's edge toward the other reads deep/shallow consistently)
            if pair in ({"sea2", "sea3"}, {"sea2", "sea5"},
                        {"sea2", "sea4"}, {"sea1", "sea4"}):
                raise ValueError(f"BAND LADDER: the new map makes {sorted(pair)} adjacent "
                                 f"at {c} -- an unreal grade jump; reduce depth")

    # --- THE EDGE-SHADE FIELDS: transported, then re-solved per STRIP band (min-flip
    # exact search). sea1 and sea5 carry the SAME learned language (sea1 = sea5's one
    # rung down, the strip-family closure) but are SEPARATE Wang fields: sea1's deep
    # side is sea3/sea5/sea4, sea5's deep side is sea4 only. ---
    EDGE = {"E": (1, 0), "W": (-1, 0), "N": (0, 1), "S": (0, -1)}
    OPP = {"E": "W", "W": "E", "N": "S", "S": "N"}
    domain = sorted(TR.EDGESET2STRIP, key=lambda es: (len(es), sorted(es)))
    solved_by_band, band_of, flipped = {}, {}, []
    for band, deeper in (("sea1", ("sea3", "sea5", "sea4")), ("sea5", ("sea4",))):
        core = {c for c, (b, _) in changes.items() if b == band}
        frontier = set()
        for c in set(changes) | set(wash_new):
            for d_ in EDGE.values():
                nb = (c[0] + d_[0], c[1] + d_[1])
                if (new_owner(nb) == band and nb not in core and nb not in changes
                        and x0 - 0.1 <= 4.0 * nb[0] and 4.0 * nb[0] + 4 <= x1 + 0.1):
                    frontier.add(nb)
        if not core and not frontier:
            solved_by_band[band] = {}
            continue
        cells = sorted(core | frontier)
        cellset = set(cells)
        prefer = {c: (changes[c][1] if c in core else shade.get(c)) for c in cells}
        pins = {}
        for c in cells:
            for e, d_ in EDGE.items():
                nb = (c[0] + d_[0], c[1] + d_[1])
                b = new_owner(nb)
                if b in deeper:
                    pins[(c, e)] = True              # deep faces deeper
                elif b is None and band == "sea5":
                    pass                             # off-census open water: unpinned
                elif b != band:
                    pins[(c, e)] = False             # the shallow side
                elif nb not in cellset:              # a verbatim same-band neighbour: pin
                    nes = shade.get(nb)
                    if nes is None:
                        raise ValueError(f"cell {c} edge {e}: verbatim {band} neighbour "
                                         f"{nb} is undecodable -- shift the window")
                    pins[(c, e)] = OPP[e] in nes
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
            raise ValueError(f"EDGE-SHADE SOLVER [{band}]: no table-valid field fits the "
                             f"new band map -- the transported shades cannot be repaired; "
                             f"reduce depth or shift the window")
        solved_by_band[band] = best[0]
        for c in frontier:
            band_of[c] = band
        flipped += sorted(c for c in frontier if best[0][c] != prefer[c])
    for c, (b, _) in changes.items():
        band_of[c] = b

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
    drop_band = {"sea1": [], "sea3": [], "sea5": [], "sea4": []}
    for c in sorted(set(changes) | set(wash_new) | set(flipped)):
        old_b = owner[c]
        if old_b == "sea2":
            continue                                 # already in the wash drop set
        for t3 in cell_tris[(old_b, c)]:
            if not all(on_lat(v) for v in t3):
                raise ValueError(f"changed cell {c} carries a conforming {old_b} tri -- "
                                 f"shift the window off the conforming ring")
            drop_band[old_b].append(t3)
    drop_sea1, drop_sea3, drop_sea5, drop_sea4 = (
        drop_band[b] for b in ("sea1", "sea3", "sea5", "sea4"))

    # --- emissions ---
    posY = {}
    for name in ("terrain", "sea1", "sea2", "sea3", "sea5", "sea4", "beach1"):
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
    for name in ("beach1", "sea2", "sea1", "sea3", "sea5", "sea4"):
        for t3 in (beach if name == "beach1" else parts[name]):
            nrm_ex[name], id_ex[name] = t3[0][1], tuple(t3[0][3])
            break
    foam_emit, sea2_emit, sea1_emit, sea3_emit = [], [], [], []
    sea5_emit, sea4_emit = [], []
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
        b = band_of[c]
        if b in ("sea1", "sea5"):
            emit_cell(b, sea1_emit if b == "sea1" else sea5_emit, c,
                      _strip_uvf(c, solved_by_band[b][c]))
        elif b == "sea3":
            emit_cell("sea3", sea3_emit, c, sea3_map(c))
        elif b == "sea4":
            emit_cell("sea4", sea4_emit, c, mains_map(c))
        elif b == "sea2":
            emit_cell("sea2", sea2_emit, c, mains_map(c))

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

    # sea5 emission self-check (the strips_rebuild recipe): every emitted strip cell must
    # re-decode to its solved edge-set through the learned table
    for c in sorted({c for c in set(changes) | set(flipped)
                     if band_of[c] == "sea5"}):
        cell_new = [t3 for t3 in sea5_emit
                    if (math.floor(sum(v[0][0] for v in t3) / 3.0 / 4.0),
                        math.floor(sum(v[0][2] for v in t3) / 3.0 / 4.0)) == c]
        got = {TR.strip_edge_set(t3) for t3 in cell_new}
        got.discard(None)
        if got != {solved_by_band["sea5"][c]}:
            raise ValueError(f"sea5 cell {c}: the emitted strip re-decodes to "
                             f"{[sorted(g) for g in got]} instead of "
                             f"{sorted(solved_by_band['sea5'][c])} -- the emission "
                             f"self-check failed")
    # sea4 language self-check: real nearby sea4 tiles must read as the mains quadrant
    # language before we emit any. COASTAL sea4 places its quadrants over DIHEDRAL-8
    # (byte-measured on (7,17) 2026-07-10: a rotation-4 fit misses the mirrored half at
    # err ~0.49 -- the exact sea3 lesson recurring); the emission's rotation-4 picks are
    # a lawful subset.
    if sea4_emit:
        from .water import URECT as W_URECT, VRECT as W_VRECT
        maps8 = TR._dih_maps()

        def sea4_fit(t3, eps=0.05):
            uvf_ = TR._affine_uv(t3)
            cx = 4.0 * math.floor(sum(v[0][0] for v in t3) / 3 / 4.0)
            cz = 4.0 * math.floor(sum(v[0][2] for v in t3) / 3 / 4.0)
            err_best = 1e9
            for (u0, u1) in W_URECT:
                for (v0, v1) in W_VRECT:
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
        samples = [t3 for (nm, c), tris in sorted(cell_tris.items()) if nm == "sea4"
                   and (nm, c) not in cell_conf for t3 in tris][:8]
        if not samples or not all(sea4_fit(t3) for t3 in samples):
            raise ValueError("sea4 here does not read as the mains quadrant language -- "
                             "refuse rather than emit an unverified band")

    ter_drop, ter_emit = [], []
    if not _assembly:
        # --- the BERM DRAG: terrain tris keep welding to the slid sand seam (land drags
        # -- the proven fine-adjustment mechanism; the emitted foam's seam verts are the
        # SAME floats, so the weld is bit-exact by construction) ---
        seam_moves = {S[i]: (0.0, 0.0, dz[i]) for i in range(1, n - 1)
                      if abs(dz[i]) > 1e-9}
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
    else:
        # --- THE FULL-ASSEMBLY SLIDE (beach_slide): the whole ladder rides one profile.
        # THE FULL-ASSEMBLY LAW (byte-measured 2026-07-10): the sand band is a chain-to-
        # chain RIBBON in the foam's own grammar -- run columns stretch ONE v-rect
        # (land 0.5664/74 -> seam 0.5947/57) over real widths 1.8..6.6u ONLY, row B
        # (0.6006->0.625) is strictly TERMINAL (end columns/wedges, 56/56 map-wide), and
        # the only multi-row shape is the double-sided spit fold ((3,11), both edges at
        # the seam value). So a widened band has NO lawful fill: past the drag envelope
        # the band must MOVE, not stretch -- land chain + seam + waterline together, the
        # band's tris verbatim (width/density/pins preserved by construction), the berm
        # strip it moves into CLIPPED at the translated chain (pure bytes, the SpillClip
        # precedent), the vacated shore re-laid by the language machinery above. ---
        from .mesh import _clip_edge, _poly_area2_xz  # the proven exact-footprint splitters
        _fam = _sand_band_family(parts["terrain"], what="the reshape block") or _SAND_GRASS
        sand = [t for t in parts["terrain"]
                if decode_id(int(round(t[0][3][0])))["topograph"] == _fam["topo"]]
        other = [t for t in parts["terrain"]
                 if decode_id(int(round(t[0][3][0])))["topograph"] != _fam["topo"]]
        sand_in = []
        for t3 in sand:
            if in_win(t3):
                sand_in.append(t3)
            elif any(x0 + 0.1 < v[0][0] < x1 - 0.1 for v in t3):
                raise ValueError("a sand tri straddles the window frame -- the window "
                                 "must cover whole band columns")
        other_k = {_pk(v[0]) for t3 in other for v in t3}
        seam_set = {_pk(p) for p in S}
        land_map, inter_map = {}, {}
        for t3 in sand_in:
            for v in t3:
                k = _pk(v[0])
                if k in seam_set:
                    continue
                (land_map if k in other_k else inter_map).setdefault(k, v[0])
        L = sorted(land_map.values(), key=lambda p: p[0])
        if len(L) != n or any(abs(L[i][0] - S[i][0]) > 0.05 for i in range(n)):
            raise ValueError(f"the sand band's LAND chain does not column-match the seam "
                             f"({len(L)} vs {n} verts) -- beach_slide needs the "
                             f"(7,17)-class one-quad ribbon")

        def surf_y(x, z):
            for t3 in other:
                if _pip_xz(x, z, t3):
                    (a, b, c) = (v[0] for v in t3)
                    d_ = (b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])
                    if abs(d_) < 1e-9:
                        continue
                    w1 = ((x - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (z - a[2])) / d_
                    w2 = ((b[0] - a[0]) * (z - a[2]) - (x - a[0]) * (b[2] - a[2])) / d_
                    return a[1] + w1 * (b[1] - a[1]) + w2 * (c[1] - a[1])
            return None
        moves = {S[i]: (0.0, 0.0, dz[i]) for i in range(1, n - 1) if abs(dz[i]) > 1e-9}
        L2 = list(L)
        for i in range(n):
            if abs(dz[i]) <= 1e-9:
                continue
            zt = L[i][2] + dz[i]
            yt = surf_y(L[i][0], zt)
            if yt is None:
                raise ValueError(f"the translated land chain leaves the painted terrain "
                                 f"at ({L[i][0]:.0f},{zt:.1f}) -- no berm surface to "
                                 f"conform to; reduce depth")
            d_ = (0.0, yt - L[i][1], dz[i])
            moves[L[i]] = d_
            # L2 = pos+delta EXACTLY as VertexDisplace computes it at apply time -- the
            # canonical floats every clipped/emitted vert must weld to (a+(b-a) != b in
            # floats; the ulp mismatch was half the playtest seam)
            L2[i] = (L[i][0] + d_[0], L[i][1] + d_[1], L[i][2] + d_[2])
        # THE SLOPE GATE: the translated band's cross profile must stay a real beach
        # ramp (map-wide rise/run envelope 0.097..0.579 over 32 beaches)
        for i in range(n):
            run = math.hypot(L2[i][0] - S2[i][0], L2[i][2] - S2[i][2])
            if run < 0.5:
                raise ValueError(f"column {L[i][0]:.0f}: the slide pinches the band")
            sl = (L2[i][1] - S2[i][1]) / run
            if not (0.08 <= sl <= 0.60):
                raise ValueError(f"SLOPE GATE: column {L[i][0]:.0f} slides onto a "
                                 f"{sl:.2f} rise/run berm (real envelope 0.10..0.58) -- "
                                 f"the beach would climb off-language; reduce depth")
        for k, p in inter_map.items():
            i = max(0, min(n - 2, next((j for j in range(n - 1)
                                        if p[0] <= L[j + 1][0] + 0.01), n - 2)))
            t_ = (p[0] - L[i][0]) / max(L[i + 1][0] - L[i][0], 1e-6)
            t_ = max(0.0, min(1.0, t_))
            dzh = dz[i] + t_ * (dz[i + 1] - dz[i])
            if abs(dzh) <= 1e-9:
                continue
            sz = S[i][2] + t_ * (S[i + 1][2] - S[i][2])
            lz = L[i][2] + t_ * (L[i + 1][2] - L[i][2])
            fr = max(0.0, min(1.0, (p[2] - sz) / (lz - sz) if abs(lz - sz) > 1e-6 else 0.0))
            dyl = (moves.get(L[i], (0, 0, 0))[1]
                   + t_ * (moves.get(L[i + 1], (0, 0, 0))[1]
                           - moves.get(L[i], (0, 0, 0))[1]))
            moves[p] = (0.0, fr * dyl, dzh)

        # the consumed strip (old chain -> translated chain), one convex trapezoid per
        # column; every berm tri it touches is clipped at the new chain -- pure bytes
        quads = []
        for i in range(n - 1):
            if max(abs(dz[i]), abs(dz[i + 1])) <= 1e-9:
                continue
            q = [(L[i][0], L[i][2]), (L[i + 1][0], L[i + 1][2]),
                 (L2[i + 1][0], L2[i + 1][2]), (L2[i][0], L2[i][2])]
            # the end columns pin (dz=0) so an end trapezoid degenerates to a triangle;
            # a repeated vertex makes a zero-length BSP edge that keeps EVERYTHING (the
            # double-count defect) -- dedupe consecutive verts
            q = [p for j, p in enumerate(q)
                 if abs(p[0] - q[j - 1][0]) > 1e-9 or abs(p[1] - q[j - 1][1]) > 1e-9]
            if len(q) < 3:
                continue
            nq = len(q)
            a2 = sum(q[j][0] * q[(j + 1) % nq][1] - q[(j + 1) % nq][0] * q[j][1]
                     for j in range(nq))
            if abs(a2) <= 1e-9:
                continue
            if a2 < 0:
                q.reverse()
            quads.append((q, abs(a2) / 2.0))
        strip_area = sum(a for _, a in quads)

        def _clip_quads(t3):
            """(consumed_area, kept_pieces) of one tri vs the strip polygons -- SH inside
            + the BSP outside decomposition (split_retarget_by_polygon's proven pattern).
            Each strip polygon is convex by construction (a pure-z translation trapezoid,
            deduped)."""
            pieces, consumed = [list(t3)], 0.0
            for q, _a in quads:
                nq = len(q)
                nxt = []
                for piece in pieces:
                    inside = piece
                    for j in range(nq):
                        inside = _clip_edge(inside, q[j], q[(j + 1) % nq], keep_left=True)
                        if len(inside) < 3:
                            break
                    ia = _poly_area2_xz(inside) / 2.0 if len(inside) >= 3 else 0.0
                    if ia <= 1e-6:
                        nxt.append(piece)
                        continue
                    consumed += ia
                    for j in range(nq):
                        frag = piece
                        for jj in range(j):
                            frag = _clip_edge(frag, q[jj], q[(jj + 1) % nq],
                                              keep_left=True)
                            if len(frag) < 3:
                                break
                        if len(frag) < 3:
                            continue
                        frag = _clip_edge(frag, q[j], q[(j + 1) % nq], keep_left=False)
                        if len(frag) >= 3 and _poly_area2_xz(frag) > 2e-6:
                            nxt.append(frag)
                pieces = nxt
            return consumed, pieces
        sand_in_keys = {_key_set(t) for t in sand_in}
        for t3 in sand:
            if _key_set(t3) not in sand_in_keys and _clip_quads(t3)[0] > 1e-4:
                raise ValueError("the consumed strip reaches ANOTHER sand band -- a "
                                 "component within reach; reduce depth or the window")
        for t3 in TR.world_tris(*donor, "object", disc=disc, lod=lod, game=game):
            if _clip_quads(t3)[0] > 1e-4:
                raise ValueError("the consumed strip reaches the block's prefab Object "
                                 "ground (the object-anchor law) -- reduce depth")
        consumed_total, clipped = 0.0, []
        for t3 in other:
            consumed, pieces = _clip_quads(t3)
            if consumed <= 1e-6:
                continue
            plan2 = _poly_area2_xz(t3)
            if plan2 < 0.02 or TR._tri_area2_3d(list(t3)) > 2.0 * plan2:
                raise ValueError("the consumed strip cuts a STEEP face -- relief is a "
                                 "component, cut around it never through; reduce depth")
            kept = sum(_poly_area2_xz(p) / 2.0 for p in pieces)
            if abs(plan2 / 2.0 - consumed - kept) > 1e-4 * max(1.0, plan2 / 2.0):
                raise ValueError("PARTITION LEDGER: a clipped berm tri's pieces do not "
                                 "sum to the original -- a clip defect")
            consumed_total += consumed
            ter_drop.append(list(t3))
            clipped.append((t3, pieces, kept))
        if abs(consumed_total - strip_area) > max(0.01 * strip_area, 0.02):
            raise ValueError(f"STRIP COVERAGE: the consumed strip ({strip_area:.2f} sq-u) "
                             f"is only {consumed_total:.2f} painted terrain -- the band "
                             f"would slide into a hole; reduce depth")
        # no survivor may reference a moved vert (drop-don't-drag, the escape check)
        mvk = {_pk(p) for p in moves}
        drop_ks = {_key_set(t) for t in ter_drop}
        for t3 in other:
            if any(_pk(v[0]) in mvk for v in t3) and _key_set(t3) not in drop_ks:
                raise ValueError("a berm tri rides a moved chain vert but escapes the "
                                 "strip clip -- the drag this verb exists to remove")

        # THE T-VERTEX LAW (in-game 2026-07-10, 'a small seam where the transition tile
        # hits the grass, only visible from certain camera angles'): re-triangulate each
        # clipped tri's KEPT region from its MERGED boundary loop -- the raw BSP
        # fragments split along the strip quads' infinite edge lines and plant mid-edge
        # verts on edges shared with UNSPLIT grass neighbours (classic angle-dependent
        # rasterization pinholes).
        l2_keep = {_pk(p) for p in L2} | {_pk(p) for p in L}
        for t3, pieces, kept in clipped:
            tris_out = []
            for loop in _merge_loops(pieces):
                loop = _drop_collinear(loop, l2_keep)
                tris_out += _ear_clip(loop)
            area_out = sum(_poly_area2_xz(t_) / 2.0 for t_ in tris_out)
            if abs(area_out - kept) > 1e-3 * max(1.0, kept):
                raise ValueError("LOOP LEDGER: a clipped berm tri's re-triangulated "
                                 "loops do not cover its kept area -- a merge defect "
                                 "(the hairline law's T-vertex flavour)")
            ter_emit += [_up_tri(t_) for t_ in tris_out]
        # canonical snap: crossing verts shared by two clipped tris are computed by
        # independent interpolations (t vs 1-t) -- collapse ulp twins to ONE float triple
        # (bit-exact welds; positions only, UVs stay per-tile)
        canon = {_pk(p, 6): tuple(p) for p in L2}

        def _snap(v):
            tgt = canon.setdefault(_pk(v[0], 6), tuple(v[0]))
            return v if tgt == tuple(v[0]) else (tgt, v[1], v[2], v[3])
        ter_emit = [[_snap(v) for v in t3] for t3 in ter_emit]

        # the band's land edge must carry the SAME verts as the mural pieces' cut edge:
        # subdivide the hosting band tri at every mid-segment cut crossing (verbatim
        # texture -- the tile is affine, so edge UVs interpolate exactly)
        mvround = {_pk(k): tuple(d) for k, d in moves.items()}
        seg_cuts = defaultdict(dict)
        for t3e in ter_emit:
            for v in t3e:
                p = v[0]
                for i in range(n - 1):
                    A, B = L2[i], L2[i + 1]
                    ex, ez = B[0] - A[0], B[2] - A[2]
                    el2 = ex * ex + ez * ez
                    if el2 < 1e-9:
                        continue
                    t_ = ((p[0] - A[0]) * ex + (p[2] - A[2]) * ez) / el2
                    if not (1e-4 < t_ < 1 - 1e-4):
                        continue
                    if abs(ex * (p[2] - A[2]) - ez * (p[0] - A[0])) \
                            > 1e-6 * max(1.0, math.hypot(ex, ez)):
                        continue
                    seg_cuts[i][round(t_, 9)] = p
        for i, cuts in sorted(seg_cuts.items()):
            ka, kb = _pk(L[i]), _pk(L[i + 1])
            hosts = [t3 for t3 in sand_in if {ka, kb} <= {_pk(v[0]) for v in t3}]
            if len(hosts) != 1:
                raise ValueError(f"column {L[i][0]:.0f}: cut crossings on the new chain "
                                 f"but {len(hosts)} band tris host the land edge")
            host = hosts[0]
            ter_drop.append(list(host))
            tv = []
            for v in host:
                d_ = mvround.get(_pk(v[0]))
                pos = (v[0][0] + d_[0], v[0][1] + d_[1], v[0][2] + d_[2]) if d_ else v[0]
                tv.append((pos, v[1], v[2], v[3]))
            byk = {_pk(v[0]): tvv for v, tvv in zip(host, tv)}
            va2, vb2 = byk[ka], byk[kb]
            vc2 = next(tvv for v, tvv in zip(host, tv) if _pk(v[0]) not in (ka, kb))

            def _edge_attr(t_):
                nrm = tuple(va2[1][j] + t_ * (vb2[1][j] - va2[1][j]) for j in range(3))
                uv = tuple(va2[2][j] + t_ * (vb2[2][j] - va2[2][j]) for j in range(2))
                tan = tuple(va2[3][j] + t_ * (vb2[3][j] - va2[3][j]) for j in range(4))
                return nrm, uv, tan
            pts = [va2]
            for t_, p in sorted(cuts.items()):
                nrm, uv, tan = _edge_attr(t_)
                pts.append((tuple(p), nrm, uv, tan))
            pts.append(vb2)
            for v0, v1 in zip(pts, pts[1:]):
                ter_emit.append(_up_tri([vc2, v0, v1]))
        seam_moves = moves
        drop_all_keys = ({_key_set(t) for t in ter_drop}
                         | {_key_set(t) for t in
                            drop_foam + drop_sea2 + drop_sea1 + drop_sea3
                            + drop_sea5 + drop_sea4})

        # THE T-VERTEX GATE: in the touched neighbourhood, no NEW/MOVED vert may sit
        # strictly inside another terrain edge and no vert mid a NEW edge -- the offline
        # oracle for the pinhole class the playtest caught (pre-existing donor
        # T-junctions are not ours to judge: only pairs involving our delta are gated)
        final = [(True, t3) for t3 in ter_emit]
        for t3 in parts["terrain"]:
            if _key_set(t3) in drop_all_keys:
                continue
            movedt = False
            out_ = []
            for v in t3:
                d_ = mvround.get(_pk(v[0]))
                if d_:
                    movedt = True
                    out_.append(((v[0][0] + d_[0], v[0][1] + d_[1], v[0][2] + d_[2]),
                                 v[1], v[2], v[3]))
                else:
                    out_.append(v)
            final.append((movedt, out_))
        xlo_, xhi_ = x0 - 6.0, x1 + 6.0
        zlo_ = min(p[2] for p in L) - 2.0
        zhi_ = max(p[2] for p in L2) + 8.0
        _tvertex_gate([(nw, t3) for nw, t3 in final
                       if any(xlo_ <= v[0][0] <= xhi_ and zlo_ <= v[0][2] <= zhi_
                              for v in t3)])
        n_seam = 0
        for name in ("terrain", "sea1", "sea2", "sea3", "sea5", "sea4"):
            for t3 in parts[name]:
                if _key_set(t3) in drop_all_keys:
                    continue
                n_seam += sum(1 for v in t3 if _pk(v[0]) in mvk)
        for t3 in beach:
            if _key_set(t3) not in drop_all_keys:
                n_seam += sum(1 for v in t3 if _pk(v[0]) in mvk)

    # --- gates: union crack (move-aware) + water density + the ledger ---
    def once(tris):
        ec = defaultdict(int)
        for t3 in tris:
            ps = [v[0] for v in t3]
            for i2 in range(3):
                ec[frozenset((_pk(ps[i2]), _pk(ps[(i2 + 1) % 3])))] += 1
        return {e for e, cn in ec.items() if cn == 1}
    all_drop = drop_foam + drop_sea2 + drop_sea1 + drop_sea3 + drop_sea5 + drop_sea4
    all_emit = foam_emit + sea2_emit + sea1_emit + sea3_emit + sea5_emit + sea4_emit
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
                                   ("sea3", drop_sea3 or parts["sea3"], sea3_emit),
                                   ("sea5", drop_sea5 or parts["sea5"], sea5_emit),
                                   ("sea4", drop_sea4 or parts["sea4"], sea4_emit)):
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
                          TR.DropTris("sea5", drop_sea5) if drop_sea5 else None,
                          TR.DropTris("sea4", drop_sea4) if drop_sea4 else None,
                          TR.DropTris("terrain", ter_drop) if ter_drop else None,
                          TR.VertexDisplace(moves=seam_moves, expected=n_seam)
                          if seam_moves else None,
                          TR.EmitTris("beach1", foam_emit),
                          TR.EmitTris("sea2", sea2_emit),
                          TR.EmitTris("sea1", sea1_emit) if sea1_emit else None,
                          TR.EmitTris("sea3", sea3_emit) if sea3_emit else None,
                          TR.EmitTris("sea5", sea5_emit) if sea5_emit else None,
                          TR.EmitTris("sea4", sea4_emit) if sea4_emit else None,
                          TR.EmitTris("terrain", ter_emit) if ter_emit else None)
            if tw is not None]


def beach_slide(donor, start, end, depth, *, disc: int = 1, lod: str = "0_1", game=None):
    """THE FULL-ASSEMBLY SLIDE (Path B resolved, 2026-07-10) -- TRUE beach movement past
    the +-2.5u drag cap. The banked 'mirror continuation' fill was FALSIFIED by the sand
    census: the run band's one v-rect stretches over real widths 1.8..6.6u ONLY, row B is
    strictly terminal (56/56 tris map-wide sit at ends/wedges), the sole multi-row shape
    is the double-sided spit fold, and run-seam verts pin to 0.5947/0.5957 with zero
    exceptions -- so a WIDENED single-sided band has no lawful fill at any width past the
    drag envelope. What the artists do instead is move the WHOLE ladder with the coast.
    Hence: the land chain rides the same sin^2 profile as the seam + waterline (the HUG
    law completed one chain landward), the sand band translates VERBATIM (width, texel
    density and both chain pins preserved by construction), the berm strip it moves into
    is CLIPPED at the translated chain (pure real bytes -- the SpillClip/watchtower
    precedent, T-junctions on-line by construction), the band's y re-conforms to the
    clipped berm surface (SLOPE GATE: the real 0.10..0.58 rise/run envelope), and the
    vacated shore re-lays through beach_reshape's proven water machinery (wash re-band +
    patchwork pullback + edge-shade re-solve + density/crack gates).

    SEAWARD (depth > 0) is the GRASS-BERM NOSE rung (:func:`_beach_slide_seaward`), on
    the FREE-FORM chain machinery: the map-wide census (2026-07-10) found the
    lattice-column beach class = {(7,17)} exactly (a pocket, landward-only by the
    shape-class law), while every true nose is free-form conforming -- so the seaward
    slide rides :func:`beach_bump`'s in-game-proven displacement field instead (the
    ladder taper seaward, factor 1 across the assembly), with the two changes that
    define the slide: the BAND translates instead of stretching (drop-don't-drag: every
    sand tri touching a moved vert re-emits translated; grass never moves -- the
    GRASS-PIN law), and the vacated strip behind the band re-fills with NATIVE GRASS
    (:func:`_grass_fill_region`, the headland fill vocabulary; a mural berm refuses --
    the baked-terrain law)."""
    if depth >= 0:
        return _beach_slide_seaward(donor, start, end, depth, disc=disc, lod=lod,
                                    game=game)
    return beach_reshape(donor, start, end, depth, disc=disc, lod=lod, game=game,
                         _assembly=True)


def _beach_slide_seaward(donor, start, end, depth, *, disc: int = 1, lod: str = "0_1",
                         game=None):
    """The seaward FULL-ASSEMBLY SLIDE on a free-form grass-berm shore -- see
    :func:`beach_slide`. Landward of the waterline everything rides at factor 1 (the
    hug law completed); seaward water follows the proven ladder taper; the band's
    verbatim texture translates; grass is PINNED and the vacated strip grass-fills."""
    if not (0.5 <= depth <= 6.0):
        raise ValueError("the seaward slide takes 0.5 <= depth <= 6")
    (beach, others, reg, pos_of, adj, pts, nh,
     arcs, acc, seam_all) = _freeform_window(donor, start, end,
                                             disc=disc, lod=lod, game=game)
    topo = lambda t3: decode_id(int(round(t3[0][3][0])))["topograph"]
    _fam = _sand_band_family(others["terrain"], what="the slide block") or _SAND_GRASS
    sand = [t for t in others["terrain"] if topo(t) == _fam["topo"]]
    gother = [t for t in others["terrain"] if topo(t) != _fam["topo"]]
    grass_k = {_pk(v[0]) for t3 in gother for v in t3}
    TAPER_REACH = max(12.0, depth * math.pi / 0.32)

    def chain_param(p):
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
    fx0, fx1 = 64.0 * donor[0], 64.0 * donor[0] + 64.0
    fz0, fz1 = -64.0 * donor[1] - 64.0, -64.0 * donor[1]

    def near_frame(p, eps=1.5):
        return (min(p[0] - fx0, fx1 - p[0]) < eps or min(p[2] - fz0, fz1 - p[2]) < eps)
    moves = {}
    for i in range(1, len(pts) - 1):
        if near_frame(pts[i], eps=0.05):
            raise ValueError(f"waterline vert ({pts[i][0]:.0f},{pts[i][2]:.0f}) sits on "
                             f"the block frame -- shrink the window off the frame")
        d = depth * math.sin(math.pi * arcs[i] / acc) ** 2
        moves[pts[i]] = (d * nh[0], 0.0, d * nh[1])
    # water: the seaward ladder taper; foam: rides at factor 1 (the whole assembly).
    # TERRAIN NEVER ENTERS THE MOVES DICT -- the band re-emits, grass is pinned.
    wl_keys = {_pk(p) for p in moves}
    for name in ("sea1", "sea2", "sea3", "sea5", "sea4", "beach1"):
        for t3 in (beach if name == "beach1" else others[name]):
            for v in t3:
                k = _pk(v[0])
                if k in wl_keys or near_frame(v[0]):
                    continue
                d, f = chain_param(v[0])
                if abs(d) < 1e-6:
                    continue
                if f > 0.05:
                    if f >= TAPER_REACH or name == "beach1":
                        continue
                    fac = math.cos(math.pi / 2.0 * f / TAPER_REACH) ** 2
                elif name == "beach1":
                    fac = 1.0                        # the foam rides whole
                else:
                    continue                         # landward water: none exists
                if abs(d * fac) < 0.05:
                    continue
                moves[v[0]] = (d * fac * nh[0], 0.0, d * fac * nh[1])
                wl_keys.add(k)
    keyed = {_pk(p): v for p, v in moves.items()}
    # THE GRASS-PIN LAW: no displaced vert may have a live instance in a non-sand
    # terrain tri (grass never drags -- the fill bridges instead)
    for k in keyed:
        if k in grass_k:
            raise ValueError("a displaced vert is welded to the grass berm (an end-cap "
                             "corner mid-window?) -- the slide window must reach the "
                             "beach's pinned end-caps; grass never drags")

    # the BAND: per-vert factor-1 ride; drop-don't-drag closure (every sand tri touching
    # a moved vert re-emits translated, so no survivor references a moved vert)
    ride = {}
    for t3 in sand:
        for v in t3:
            k = _pk(v[0])
            if k in ride or near_frame(v[0], eps=0.05):
                continue
            if k in keyed:
                ride[k] = keyed[k]
                continue
            d, f = chain_param(v[0])
            if abs(d) < 0.05:
                continue
            ride[k] = (d * nh[0], 0.0, d * nh[1])
    band_drop, band_emit = [], []
    for t3 in sand:
        if not any(_pk(v[0]) in ride for v in t3):
            continue
        band_drop.append(list(t3))
        out = []
        for (p, nrm, uv, tan) in t3:
            d_ = ride.get(_pk(p))
            if d_ is not None:
                p = (p[0] + d_[0], p[1] + d_[1], p[2] + d_[2])
            out.append((p, nrm, uv, tan))
        a0 = TR.VertexDisplace._area2(list(t3))
        a1 = TR.VertexDisplace._area2(out)
        if abs(a0) > 0.02 and (a0 * a1 <= 0.0 or abs(a1) < 0.02):
            raise ValueError(f"depth {depth:g} folds a band tile -- reduce depth")
        band_emit.append(out)
    if not band_drop:
        raise ValueError("the window moves no sand -- not a beach slide")

    # the vacated strip: the band's old sand-grass boundary polyline vs its translated
    # twin, one fill loop per moved stretch (pinch points split lobes)
    grass_edges = set()
    for t3 in gother:
        ps = [v[0] for v in t3]
        for i in range(3):
            grass_edges.add(frozenset((_pk(ps[i]), _pk(ps[(i + 1) % 3]))))
    badj, bpos = defaultdict(set), {}
    for t3 in band_drop:
        ps = [v[0] for v in t3]
        for i in range(3):
            a, b = ps[i], ps[(i + 1) % 3]
            e = frozenset((_pk(a), _pk(b)))
            if e in grass_edges:
                badj[_pk(a)].add(_pk(b))
                badj[_pk(b)].add(_pk(a))
                bpos.setdefault(_pk(a), a)
                bpos.setdefault(_pk(b), b)
    if not badj:
        raise ValueError("the moved band shares no boundary with the berm terrain -- "
                         "not a grass-backed beach (a spit?); no strip to fill")
    ends = [k for k, ns in badj.items() if len(ns) == 1]
    if len(ends) != 2 or any(len(ns) > 2 for ns in badj.values()):
        raise ValueError("the sand-grass boundary is not one open polyline -- the "
                         "window must cover a mid-beach run clear of forks")
    poly, seen_k = [ends[0]], {ends[0]}
    while True:
        nxts = [n for n in badj[poly[-1]] if n not in seen_k]
        if not nxts:
            break
        poly.append(nxts[0])
        seen_k.add(nxts[0])
    old_poly = [bpos[k] for k in poly]
    if any(k in ride for k in (poly[0], poly[-1])):
        raise ValueError("the sand-grass boundary still moves at the window's edge -- "
                         "extend the window to the beach's pinned end-caps")

    # berm census: the fill vocabulary must exist (grass mains behind the strip)
    grass_real = [t3 for t3 in gother
                  if all(any(lo - 0.012 <= v[2][0] <= hi + 0.012
                             for (lo, hi) in G.GRASS_U_HALF + G.MEADOW_U_HALF)
                         and any(lo - 0.012 <= v[2][1] <= hi + 0.012
                                 for (lo, hi) in G.GRASS_V_HALF)
                         for v in t3)
                  and any(min(math.hypot(v[0][0] - p[0], v[0][2] - p[2])
                              for p in old_poly) < 14.0 for v in t3)]
    if len(grass_real) < 3:
        raise ValueError("the berm behind this beach carries no grass mains (a painted "
                         "wash) -- the baked-terrain law: no fill language; the slide "
                         "needs a grass-berm nose")
    cell_quad = {}
    for t3 in grass_real:
        cx = math.floor(sum(v[0][0] for v in t3) / 3.0 / 4.0)
        cz = math.floor(sum(v[0][2] for v in t3) / 3.0 / 4.0)
        cell_quad.setdefault((cx, cz), TR._quad_of_uv(t3[0][2]))
    gnrm = {}
    for t3 in gother:
        for v in t3:
            gnrm.setdefault(_pk(v[0]), tuple(v[1]))
    idall_grass = tuple(grass_real[0][0][3])
    fill_emit = []
    i0 = 0
    for i1 in range(1, len(poly)):
        if poly[i1] in ride and i1 < len(poly) - 1:
            continue
        # [i0..i1] closes a stretch when its interior moved and its ends are pinned
        if i1 - i0 >= 1 and any(poly[k] in ride for k in range(i0 + 1, i1)):
            seg_old = old_poly[i0:i1 + 1]
            seg_new = []
            for p in seg_old:
                d_ = ride.get(_pk(p))
                seg_new.append((p[0] + d_[0], p[1] + d_[1], p[2] + d_[2])
                               if d_ else p)
            bpts3 = seg_old + list(reversed(seg_new[1:-1]))
            fill_emit += _grass_fill_region(bpts3, gnrm, cell_quad, idall_grass)
        if poly[i1] not in ride:
            i0 = i1

    # --- the gates (the bump's proven set + the slide's own) ---
    def _mvp(p):
        d_ = keyed.get(_pk(p)) or ride.get(_pk(p))
        return (p[0] + d_[0], p[1], p[2] + d_[2]) if d_ else p
    for p in pts[1:-1]:
        d0 = min(math.hypot(p[0] - q[0], p[2] - q[2]) for q in seam_all)
        pm = _mvp(p)
        d1 = min(math.hypot(pm[0] - q[0], pm[2] - q[2])
                 for q in (_mvp(q) for q in seam_all))
        if abs(d1 - d0) > 0.6 or (2.6 <= d0 <= 8.2 and not (2.6 <= d1 <= 8.2)):
            raise ValueError(f"RIBBON/HUG GATE: the slide moves the swash {d0:.1f} -> "
                             f"{d1:.1f}u at ({p[0]:.0f},{p[2]:.0f}) -- the ribbon must "
                             f"ride the sand edge inside the real envelope; reduce depth")
    a2, b2 = pts[0], pts[-1]
    ex2, ez2 = b2[0] - a2[0], b2[2] - a2[2]
    L2_ = math.hypot(ex2, ez2) or 1.0
    nx2, nz2 = -ez2 / L2_, ex2 / L2_
    if nx2 * nh[0] + nz2 * nh[1] < 0:
        nx2, nz2 = -nx2, -nz2

    def _dev2(p):
        return (p[0] - a2[0]) * nx2 + (p[2] - a2[2]) * nz2
    d0s = [_dev2(p) for p in pts[1:-1]]
    d1s = [_dev2(_mvp(p)) for p in pts[1:-1]]
    sea_cap = 0.25 * L2_ if max(d0s) > 0.5 else max(d0s) + 0.3
    land_cap = -0.48 * L2_ if min(d0s) < -0.5 else min(d0s) - 0.3
    if max(d1s) > sea_cap + 1e-6 or min(d1s) < land_cap - 1e-6:
        klass = "convex (headland-nose)" if max(d0s) > 0.5 else \
                "concave (pocket)" if min(d0s) < -0.5 else "straight"
        raise ValueError(f"SHAPE-CLASS GATE: this beach is {klass} (chord devs "
                         f"{min(d0s):.1f}..{max(d0s):.1f} over {L2_:.0f}u); the slide "
                         f"takes it to {min(d1s):.1f}..{max(d1s):.1f}, past its class "
                         f"envelope [{land_cap:.1f},{sea_cap:.1f}]")
    band_drop_ks = {_key_set(t) for t in band_drop}
    for tris in [beach] + list(others.values()):
        for t3 in tris:
            if _key_set(t3) in band_drop_ks:
                continue
            if not any(_pk(v[0]) in keyed for v in t3):
                continue
            out = []
            for (p, nrm, uv, tan) in t3:
                dd = keyed.get(_pk(p))
                if dd is not None:
                    p = (p[0] + dd[0], p[1] + dd[1], p[2] + dd[2])
                out.append((p, nrm, uv, tan))
            a0 = TR.VertexDisplace._area2(list(t3))
            a1 = TR.VertexDisplace._area2(out)
            if abs(a0) > 0.02 and (a0 * a1 <= 0.0 or abs(a1) < 0.02):
                raise ValueError(f"depth {depth:g} folds a shore tile -- reduce depth")
    reg_pk = {n: {_pk(v[0]) for t3 in t for v in t3} for n, t in others.items()}
    c1 = [pos_of.get(k) or next(v[0] for t3 in others["sea2"] for v in t3
                                if _pk(v[0]) == k)
          for k in (reg_pk["sea2"] & reg_pk["sea1"])]
    for p in pts[1:-1]:
        if not c1:
            break
        w0 = min(math.hypot(p[0] - q[0], p[2] - q[2]) for q in c1)
        pm = _mvp(p)
        w1 = min(math.hypot(pm[0] - q[0], pm[2] - q[2]) for q in (_mvp(q) for q in c1))
        if w0 > 0.5 and w1 < 0.6 * w0:
            raise ValueError(f"BAND GATE: the wash band pinches {w0:.1f} -> {w1:.1f}u at "
                             f"({p[0]:.0f},{p[2]:.0f}) despite the taper -- reduce depth")
    for name in ("sea1", "sea2", "sea3", "sea5", "sea4"):
        for t3 in others[name]:
            if not any(_pk(v[0]) in keyed for v in t3):
                continue
            ps0 = [v[0] for v in t3]
            ps1 = [((p[0] + keyed[_pk(p)][0], p[1], p[2] + keyed[_pk(p)][2])
                    if _pk(p) in keyed else p) for p in ps0]
            for i in range(3):
                l0 = math.hypot(ps0[i][0] - ps0[(i + 1) % 3][0],
                                ps0[i][2] - ps0[(i + 1) % 3][2])
                l1 = math.hypot(ps1[i][0] - ps1[(i + 1) % 3][0],
                                ps1[i][2] - ps1[(i + 1) % 3][2])
                if l0 > 0.5 and not (0.75 <= l1 / l0 <= 1.33):
                    raise ValueError(f"STRAIN GATE: a {name} edge strains x{l1 / l0:.2f} "
                                     f"near ({ps0[i][0]:.0f},{ps0[i][2]:.0f}) -- reduce "
                                     f"depth")
    # THE T-VERTEX GATE over the touched terrain neighbourhood
    xs = [p[0] for p in old_poly]
    zs = [p[2] for p in old_poly]
    xlo_, xhi_ = min(xs) - 8.0, max(xs) + 8.0
    zlo_, zhi_ = min(zs) - 8.0 - depth, max(zs) + 8.0 + depth
    final = [(True, t3) for t3 in band_emit + fill_emit]
    for t3 in others["terrain"]:
        if _key_set(t3) in band_drop_ks:
            continue
        final.append((False, list(t3)))
    _tvertex_gate([(nw, t3) for nw, t3 in final
                   if any(xlo_ <= v[0][0] <= xhi_ and zlo_ <= v[0][2] <= zhi_
                          for v in t3)])

    n_all = 0
    for tris in [beach] + list(others.values()):
        for t3 in tris:
            if _key_set(t3) in band_drop_ks:
                continue
            n_all += sum(1 for v in t3 if _pk(v[0]) in keyed)
    return [TR.DropTris("terrain", band_drop),
            TR.VertexDisplace(moves=moves, expected=n_all),
            TR.EmitTris("terrain", band_emit + fill_emit)]


def _outline_min_clear(pts):
    """Min distance between NON-ADJACENT segments of an ordered xz outline polyline."""
    def segd(p1, p2, q1, q2):
        best = 1e18
        for a, (b, c) in ((p1, (q1, q2)), (p2, (q1, q2)), (q1, (p1, p2)), (q2, (p1, p2))):
            ex, ez = c[0] - b[0], c[1] - b[1]
            L2 = ex * ex + ez * ez or 1.0
            t = max(0.0, min(1.0, ((a[0] - b[0]) * ex + (a[1] - b[1]) * ez) / L2))
            best = min(best, math.hypot(a[0] - b[0] - t * ex, a[1] - b[1] - t * ez))
        return best
    best = 1e18
    for i in range(len(pts) - 1):
        for j in range(i + 3, len(pts) - 1):
            best = min(best, segd(pts[i], pts[i + 1], pts[j], pts[j + 1]))
    return best


def _clearance_gate(win, new_base, d_cols):
    """THE CLEARANCE GATE -- the cliff SHAPE law (2026-07-10). Measured over the proven
    deploys + the full catalog: cliffs are CLASS-FREE (a headland on a bay rim read clean
    in-game, (16,9)) and push-direction SHEAR is harmless (drop-don't-drag REBUILDS the
    wall natively, so the global normal is a pure outline parameter -- 81-degree crest
    shear proven at (16,9)). The real hazard on a wrapping window is the pushed outline
    PINCHING: the catalog's (21,10) D=8 came within 1.7u of itself (a wall-against-wall
    sliver channel); every proven point sits >= 5.6u. Gate: >= 4u (the lattice grain)
    against (a) the outline's own non-adjacent segments -- with the ride-never-tighten
    escape for windows whose STOCK outline is already close -- and (b) the block's other
    cliff-base verts, tested from MOVED segments only (both endpoints displaced > 0.5u,
    so a pinned end's natural 4u gap to the run's continuation never false-trips)."""
    old2 = [(p[0], p[2]) for p in win.base]
    new2 = [(p[0], p[2]) for p in new_base]
    c_old = _outline_min_clear(old2)
    c_new = _outline_min_clear(new2)
    if c_new < 4.0 and c_new < c_old - 0.01:
        raise ValueError(f"CLEARANCE GATE: the pushed outline pinches to {c_new:.1f}u "
                         f"against itself (stock {c_old:.1f}u) -- a wall-against-wall "
                         f"sliver; reduce depth or shrink the window")
    win_k = {_pk(p) for p in win.base}
    other = [(v[0][0], v[0][2]) for t3 in win.cliff for v in t3
             if v[0][1] < BASE_Y_MAX and _pk(v[0]) not in win_k]
    if not other:
        return
    moved = [abs(d) > 0.5 for d in d_cols]
    worst = 1e18
    for i in range(len(new2) - 1):
        if not (i < len(moved) and i + 1 < len(moved) and moved[i] and moved[i + 1]):
            continue
        ex, ez = new2[i + 1][0] - new2[i][0], new2[i + 1][1] - new2[i][1]
        L2 = ex * ex + ez * ez or 1.0
        for q in other:
            t = max(0.0, min(1.0, ((q[0] - new2[i][0]) * ex
                                   + (q[1] - new2[i][1]) * ez) / L2))
            worst = min(worst, math.hypot(q[0] - new2[i][0] - t * ex,
                                          q[1] - new2[i][1] - t * ez))
    if worst < 4.0:
        raise ValueError(f"CLEARANCE GATE: the pushed outline comes within {worst:.1f}u "
                         f"of the block's other cliff base -- a pinched channel; reduce "
                         f"depth or shrink the window")


def strips_rebuild(donor, parts=("sea1", "sea5"), *, disc: int = 1, lod: str = "0_1",
                   game=None):
    """The STRIP-BAND identity rebuild -- SEA5 EMISSION proven the way sea1 was (the
    beach_rebuild pattern, block-wide): DROP every DECODABLE Wang strip cell of the given
    bands and RE-DERIVE its tiles from the learned table over the same verts. The
    edge-shade field is READ from the donor (shape data); the tile comes from
    EDGESET2STRIP in emission mode with a hash-picked variant, so the rebuild is
    indistinguishable-BY-DESIGN (fresh anti-tiling picks), not byte-identical.

    The census behind it (2026-07-10, 140 blocks): sea5 decodes 1644/1763 lattice cells
    through the table with ZERO inconsistent cells and ZERO boundary violations over 3875
    band edges (sea1 baseline: 208/208) -- the learned table IS both strip bands' one
    language (sea1 = sea5's one rung down, now generative for both). The ~7% residual:
    INSET-RECT strip variants (edges shaved 1-8 texels -- the sea3-inset family, no
    structural correlation) and conforming ring tris -- both stay VERBATIM, like the
    ring cells the beach rebuild leaves in place. Self-check: every emitted cell must
    re-decode to its source edge-set."""
    out = []
    for part in parts:
        tris_all = TR.world_tris(*donor, part, disc=disc, lod=lod, game=game)
        if not tris_all:
            continue

        def on_lat(v, eps=0.02):
            return (abs(v[0][0] / 4 - round(v[0][0] / 4)) < eps
                    and abs(v[0][2] / 4 - round(v[0][2] / 4)) < eps)
        cells = defaultdict(list)
        for t3 in tris_all:
            if all(on_lat(v) for v in t3):
                c = (math.floor(sum(v[0][0] for v in t3) / 3.0 / 4.0),
                     math.floor(sum(v[0][2] for v in t3) / 3.0 / 4.0))
                cells[c].append(t3)
        drop, emit = [], []
        for c, tris in sorted(cells.items()):
            decs = {TR.strip_edge_set(t3) for t3 in tris}
            decs.discard(None)
            if len(decs) != 1:
                continue                    # conforming / inset-variant residual: verbatim
            es = next(iter(decs))
            uvf = _strip_uvf(c, es)
            new_tris = [[(v[0], v[1], uvf(v[0][0], v[0][2]), v[3]) for v in t3]
                        for t3 in tris]
            got = {TR.strip_edge_set(t3) for t3 in new_tris}
            got.discard(None)
            if got != {es}:
                raise ValueError(f"{part} cell {c}: the emitted strip re-decodes to "
                                 f"{[sorted(g) for g in got]} instead of {sorted(es)} -- "
                                 f"the emission self-check failed")
            drop.extend(tris)
            emit.extend(new_tris)
        if not drop:
            raise ValueError(f"donor {donor} has no decodable {part} strip cells")
        out += [TR.DropTris(part, drop), TR.EmitTris(part, emit)]
    return out


#: THE DEFORMED-TILE RECT LAW (byte-learned 2026-07-11 -- the conforming-tier study,
#: the rung-3 convergence-fan vocabulary): a strip tile's UV map is a <=2u x <=2v
#: RECT of snap values ASSIGNED TO ITS CORNER VERTS, independent of geometric
#: deformation -- the coast outline drags a tile's verts and the uvs STAY at their
#: corner values (why every position-evaluated fit failed: the map deforms WITH the
#: tile). Clip-INSERTED verts carry EDGE-LERPED uvs at the position's own parameter
#: (the Sutherland-Hodgman signature). The value vocabulary is one small snap set
#: shared by BOTH tiers (lattice tiles decode 186/186 sea1, 1622/1624 sea5 through
#: the same law); the conforming residual (~5%: rotated groups pending the
#: transposed test, cross-group lerp anchors, oddballs) stays verbatim.
STRIP_U_SNAPS = (0.0, 33.0, 65.0, 1008.0)
STRIP_V_SNAPS = (0.0, 16.0, 242.0, 250.0, 258.0, 274.0, 282.0, 508.0, 516.0, 524.0,
                 742.0, 758.0, 766.0, 774.0, 782.0, 790.0, 1000.0, 1024.0)
_SNAP_EPS_T = 2.5                     # texels/1024


def _snap_t(val, snaps):
    t = val * 1024
    for s in snaps:
        if abs(t - s) <= _SNAP_EPS_T:
            return s
    return None


def _deformed_strip_groups(tris):
    """Decode a strip band's tris (both tiers) into DEFORMED-TILE groups under the
    rect law. Groups = union-find over uv-equal shared edges with the ROW-BOUNDARY
    guard (adjacent rows share a v-continuous edge; a merge may never exceed one
    <=2 x <=2 rect). Yields ``(member_tris, kind, detail)`` with kind ``"rect"``
    (corners + explained lerp verts: detail = {poskey: (anchorA, anchorB, t)})
    or ``"residual"`` (rotated / cross-group-anchored / oddball: keep verbatim)."""
    def uvr(v):
        return (round(v[2][0], 4), round(v[2][1], 4))

    def tri_rect(t3, ori):
        su, sv = (STRIP_U_SNAPS, STRIP_V_SNAPS) if ori == 0 \
            else (STRIP_V_SNAPS, STRIP_U_SNAPS)
        us, vs = set(), set()
        for v in t3:
            a, b = _snap_t(v[2][0], su), _snap_t(v[2][1], sv)
            if a is not None:
                us.add(a)
            if b is not None:
                vs.add(b)
        return us, vs
    parent = list(range(len(tris)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    edge_insts = defaultdict(list)
    for i, t3 in enumerate(tris):
        for a in range(3):
            b = (a + 1) % 3
            key = frozenset((_pk(t3[a][0]), _pk(t3[b][0])))
            edge_insts[key].append((i, {_pk(t3[a][0]): uvr(t3[a]),
                                        _pk(t3[b][0]): uvr(t3[b])}))
    comp_rect = {i: tri_rect(tris[i], 0) for i in range(len(tris))}
    for key, insts in edge_insts.items():
        for (i, uva), (j, uvb) in zip(insts, insts[1:]):
            if uva != uvb:
                continue
            ri, rj = find(i), find(j)
            if ri == rj:
                continue
            gu = comp_rect[ri][0] | comp_rect[rj][0]
            gv = comp_rect[ri][1] | comp_rect[rj][1]
            if len(gu) <= 2 and len(gv) <= 2:
                parent[rj] = ri
                comp_rect[ri] = (gu, gv)
    groups = defaultdict(list)
    for i in range(len(tris)):
        groups[find(i)].append(i)
    for root, mem in sorted(groups.items(),
                            key=lambda kv: min(_pk(tris[i][0][0]) for i in kv[1])):
        gtris = [tris[i] for i in mem]
        uv_of = {}                    # poskey -> (pos, RAW uv floats)
        bad = False
        for t3 in gtris:
            for v in t3:
                k = _pk(v[0])
                if k in uv_of and (round(uv_of[k][1][0], 4),
                                   round(uv_of[k][1][1], 4)) != uvr(v):
                    bad = True
                uv_of.setdefault(k, (v[0], (v[2][0], v[2][1])))
        if bad:
            yield gtris, "residual", None
            continue
        done = None
        for ori in (0, 1):                 # unrotated, then the transposed roles
            su, sv = (STRIP_U_SNAPS, STRIP_V_SNAPS) if ori == 0 \
                else (STRIP_V_SNAPS, STRIP_U_SNAPS)
            corners, unknown = {}, {}
            for k, (p, uv) in uv_of.items():
                a, b = _snap_t(uv[0], su), _snap_t(uv[1], sv)
                if a is not None and b is not None:
                    corners[k] = (p, uv, (a, b))
                else:
                    unknown[k] = (p, uv)
            if not corners:
                continue
            us = {c[2][0] for c in corners.values()}
            vs = {c[2][1] for c in corners.values()}
            if len(us) > 2 or len(vs) > 2:
                continue
            explained = {k: (p, uv) for k, (p, uv, _s) in corners.items()}
            lerps = {}
            changed = True
            while changed and unknown:
                changed = False
                ex = list(explained.items())
                for k, (p, uv) in list(unknown.items()):
                    for (ka, (pa, ua)), (kb, (pb, ub)) in (
                            (ex[i2], ex[j2]) for i2 in range(len(ex))
                            for j2 in range(len(ex)) if i2 != j2):
                        dx, dz = pb[0] - pa[0], pb[2] - pa[2]
                        L2 = dx * dx + dz * dz
                        if L2 < 1e-9:
                            continue
                        t_ = ((p[0] - pa[0]) * dx + (p[2] - pa[2]) * dz) / L2
                        if not (-1e-3 < t_ < 1 + 1e-3):
                            continue
                        if math.hypot(pa[0] + t_ * dx - p[0],
                                      pa[2] + t_ * dz - p[2]) > 0.02:
                            continue
                        lu = ua[0] + t_ * (ub[0] - ua[0])
                        lv = ua[1] + t_ * (ub[1] - ua[1])
                        if abs(lu - uv[0]) * 1024 <= _SNAP_EPS_T \
                                and abs(lv - uv[1]) * 1024 <= _SNAP_EPS_T:
                            lerps[k] = (ka, kb, t_)
                            explained[k] = (p, uv)
                            del unknown[k]
                            changed = True
                            break
                    if k in lerps:
                        continue
            if not unknown:
                done = (corners, lerps)
                break
        if done is None:
            yield gtris, "residual", None
        else:
            yield gtris, "rect", done


def conforming_rebuild(donor, parts=("sea1", "sea5"), *, disc: int = 1,
                       lod: str = "0_1", game=None):
    """The DEFORMED-TILE identity rebuild (the rect law's completeness proof, the
    cap_rebuild pattern): every decodable CONFORMING strip group re-derives through
    the law -- corner verts take their snap-rect assignment (canonical snap floats),
    inserted verts take EDGE-LERPS recomputed from their own positions -- under an
    internal EQUALITY gate (4dp): tiles have no positional freedom under the law, so
    the round-trip IS the proof that corner assignment + positional lerps fully
    explain the conforming tier. Residual groups (rotated-ambiguous, cross-group
    anchors, oddballs) stay verbatim, like the inset variants in strips_rebuild."""
    out = []
    for part in parts:
        tris_all = TR.world_tris(*donor, part, disc=disc, lod=lod, game=game)
        if not tris_all:
            continue

        def on_lat(v, eps=0.02):
            return (abs(v[0][0] / 4 - round(v[0][0] / 4)) < eps
                    and abs(v[0][2] / 4 - round(v[0][2] / 4)) < eps)
        drop, emit = [], []
        for gtris, kind, detail in _deformed_strip_groups(tris_all):
            if kind != "rect":
                continue
            if all(all(on_lat(v) for v in t3) for t3 in gtris):
                continue                   # lattice tiles are strips_rebuild's scope
            corners, lerps = detail
            # corners TRANSPORT their exact donor floats (the snap classes are the
            # law's structure, not the engine floats); the derivation content = the
            # rect structure + the POSITIONAL lerps recomputed below
            new_uv = {}
            for k, (p, uv, _snapped) in corners.items():
                new_uv[k] = uv
            guard = 0
            while len(new_uv) < len(corners) + len(lerps) and guard < 8:
                guard += 1
                for k, (ka, kb, t_) in lerps.items():
                    if k in new_uv or ka not in new_uv or kb not in new_uv:
                        continue
                    ua, ub = new_uv[ka], new_uv[kb]
                    new_uv[k] = (ua[0] + t_ * (ub[0] - ua[0]),
                                 ua[1] + t_ * (ub[1] - ua[1]))
            if len(new_uv) < len(corners) + len(lerps):
                continue                   # a lerp chain that never grounded: verbatim
            new_tris = [[(v[0], v[1], new_uv[_pk(v[0])], v[3]) for v in t3]
                        for t3 in gtris]
            for t3o, t3n in zip(gtris, new_tris):
                for vo, vn in zip(t3o, t3n):
                    if abs(vo[2][0] - vn[2][0]) * 1024 > _SNAP_EPS_T \
                            or abs(vo[2][1] - vn[2][1]) * 1024 > _SNAP_EPS_T:
                        raise ValueError(
                            f"{part} group at {_pk(gtris[0][0][0])}: the law "
                            f"derivation strays from the donor bytes -- the "
                            f"round-trip gate failed")
            drop.extend(gtris)
            emit.extend(new_tris)
        if not drop:
            raise ValueError(f"donor {donor} has no decodable conforming {part} "
                             f"groups")
        out += [TR.DropTris(part, drop), TR.EmitTris(part, emit)]
    if not out:
        raise ValueError(f"donor {donor} carries none of {parts}")
    return out


#: THE ONE-CELL BAND-CONVERSION (rung 3, step 1 -- the first FRESH deformed-tile
#: emission; byte-grounded 2026-07-11 on donors (7,17)/(3,13)/(9,17)):
#: * **THE DISCRETE ROLE-DECODE is exact**: every strip group (lattice AND
#:   conforming) decodes to EXACTLY ONE (v-row, dihedral-8 orientation) by matching
#:   every corner snap through its NEAREST-CELL-CORNER role (29/29 conforming
#:   groups across the three donors, zero ambiguity, zero misses) -- stronger than
#:   a least-squares frame fit, which misreads leaning convergence quads.
#: * **the strip float dialect is per-BLOCK byte-read**: the proven donors all
#:   speak the uniform dialect (u {0, 62/63}, v rows {0, 31/127, 63/127, 95/127,
#:   1}), but emission NEVER types constants -- it reads the exact floats from the
#:   block's own decoded groups and refuses a row it hasn't byte-observed.
#: * **THE SHADE-AGREEMENT LAW** (the gate): a strip tile's deep-claim at a shared
#:   4-adjacent edge must be TWO-SIDED within a band (both or neither -- real
#:   back-to-back deep pinches exist, so claims may exceed the depth facts, never
#:   one-sidedly) and must equal the depth FACT against a different band. The gate
#:   runs on the PRE state (the donor must pass -- the null test) and the POST.
#: * conversion transports geometry, normals and IDALL VERBATIM (water topograph =
#:   movement/vehicle semantics; a band conversion is a uv + part edit), so the
#:   frame weld set and T-vertex exposure are unchanged BY CONSTRUCTION.
WATER_DEPTH = {"beach1": 1, "sea2": 2, "sea1": 3, "sea3": 4, "sea5": 5, "sea4": 6}
#: THE LATTICE ADJACENCY LAW (owner-cell 4-adjacency, map-wide census 2026-07-11)
_LAWFUL_ADJ = {frozenset(p) for p in (
    ("sea2", "sea2"), ("sea2", "sea1"), ("sea1", "sea1"), ("sea1", "sea3"),
    ("sea1", "sea5"), ("sea3", "sea3"), ("sea3", "sea5"), ("sea5", "sea5"),
    ("sea5", "sea4"), ("sea4", "sea4"))}
_OPP = {"E": "W", "W": "E", "N": "S", "S": "N"}
#: v-row BOUNDARY snap families (texels/1024): family i | i+1 brackets row i
_V_FAMILIES = ((0.0, 16.0), (242.0, 250.0, 258.0, 274.0, 282.0),
               (508.0, 516.0, 524.0), (742.0, 758.0, 766.0, 774.0, 782.0, 790.0),
               (1000.0, 1024.0))


def _cell_of_tri(t3):
    return (math.floor(sum(v[0][0] for v in t3) / 3.0 / 4.0),
            math.floor(sum(v[0][2] for v in t3) / 3.0 / 4.0))


def _corner_role(p, cell):
    """A vert's corner ROLE (fx, fz) in {0,1}^2 = the nearest 4u-cell corner (exact on
    lattice verts; unambiguous on conforming quads, whose drags stay under 2u)."""
    fx = 0 if abs(p[0] - 4.0 * cell[0]) < abs(p[0] - 4.0 * (cell[0] + 1)) else 1
    fz = 0 if abs(p[2] - 4.0 * cell[1]) < abs(p[2] - 4.0 * (cell[1] + 1)) else 1
    return (fx, fz)


def _v_family(t):
    for i, fam in enumerate(_V_FAMILIES):
        if any(abs(t - s) <= _SNAP_EPS_T for s in fam):
            return i
    return None


def _strip_float_vocab(groups_by_part):
    """The block's own strip float dialect, byte-read from its decoded rect groups:
    ``(u_pair, {row_index: (v0, v1)})`` in exact raw floats. Refuses a mixed dialect
    (two float pairs for one row) or an inset u variant -- v1 emits base tiles only."""
    u_pairs, rows = set(), {}
    for gs in groups_by_part.values():
        for _gtris, kind, det in gs:
            if kind != "rect":
                continue
            us = sorted({round(uv[0], 6) for (_p, uv, _s) in det[0].values()})
            vs = sorted({round(uv[1], 6) for (_p, uv, _s) in det[0].values()})
            if len(us) == 2:
                u_pairs.add(tuple(us))
            if len(vs) == 2:
                fa, fb = _v_family(vs[0] * 1024), _v_family(vs[1] * 1024)
                if fa is not None and fb == fa + 1:
                    prev = rows.setdefault(fa, tuple(vs))
                    if prev != tuple(vs):
                        raise ValueError(
                            f"mixed strip v-dialect in this block (row {fa}: "
                            f"{prev} vs {tuple(vs)}) -- band conversion refuses")
    if len(u_pairs) != 1:
        raise ValueError(f"strip u-dialect not unique in this block ({sorted(u_pairs)}) "
                         f"-- band conversion refuses")
    return next(iter(u_pairs)), rows


def _role_decode(corners, cell, u_pair, v_rows):
    """THE DISCRETE ROLE-DECODE: the (row, orientation) placements that reproduce
    EVERY corner uv through nearest-cell-corner roles (no least squares). The byte
    survey found exactly one hit per real group."""
    hits = []
    for ri, (v0, v1) in sorted(v_rows.items()):
        for oname, om in sorted(TR._dih_maps().items()):
            ok = True
            for _k, (p, uv, _s) in corners.items():
                a, b = om(*_corner_role(p, cell))
                if abs(u_pair[0] + a * (u_pair[1] - u_pair[0]) - uv[0]) * 1024 > _SNAP_EPS_T \
                        or abs(v0 + b * (v1 - v0) - uv[1]) * 1024 > _SNAP_EPS_T:
                    ok = False
                    break
            if ok:
                hits.append((ri, oname))
    return hits


def _shade_gate(reg, water_of, center, label):
    """THE SHADE-AGREEMENT LAW over the 5x5 neighbourhood of ``center``: same-band
    deep-claims two-sided, cross-band claims == the depth fact. Cells with no water
    data (terrain-only, out of block) and residual tiles are skipped -- the law only
    judges pairs it can read both sides of."""
    cx, cz = center
    for (p, c), t in reg.items():
        if t["es"] is None or max(abs(c[0] - cx), abs(c[1] - cz)) > 2:
            continue
        for dname, (dx, dz) in TR._DIRS.items():
            n = (c[0] + dx, c[1] + dz)
            claim = dname in t["es"]
            nw = water_of(n)
            if not nw:
                continue
            if p in nw:
                nt = reg.get((p, n))
                if nt is None or nt["es"] is None:
                    continue
                if claim != (_OPP[dname] in nt["es"]):
                    raise ValueError(
                        f"shade gate [{label}]: one-sided deep-claim between {p} "
                        f"{c} and {n} -- the {dname} edge disagrees")
            else:
                fact = max(WATER_DEPTH[q] for q in nw) > WATER_DEPTH[p]
                if claim != fact:
                    raise ValueError(
                        f"shade gate [{label}]: {p} {c} claims {dname} "
                        f"{'deep' if claim else 'shallow'} against {sorted(nw)} at "
                        f"{n} (fact: {'deep' if fact else 'shallow'})")


def _strip_pick(es, cell):
    """The learned-table variant pick for a deep-edge-set (the deterministic cell
    hash -- the _strip_uvf pick formula, shared by band_convert and the virgin mint)."""
    variants = TR.EDGESET2STRIP[es]
    return variants[int(TR._h01(4.0 * cell[0] + 0.3, 4.0 * cell[1] + 2.9)
                        * len(variants)) % len(variants)]


def _strip_emit(gtris, corners, lerps, cell, ri, oname, u_pair, v_rows):
    """Corner-role strip emission under THE DEFORMED-TILE RECT LAW (band_convert's
    proven emitter, shared with the virgin mint): the block's own rect floats assigned
    at nearest-cell-corner roles, inserted verts lerping positionally (the
    Sutherland-Hodgman signature). Geometry transports verbatim."""
    if ri not in v_rows:
        raise ValueError(f"strip row {ri} is not byte-observed in this block -- "
                         f"no exact floats to emit with")
    om = TR._dih_maps()[oname]
    v0, v1 = v_rows[ri]
    new_uv = {}
    for k, (p, _uv, _s) in corners.items():
        a, b = om(*_corner_role(p, cell))
        new_uv[k] = (u_pair[0] + a * (u_pair[1] - u_pair[0]), v0 + b * (v1 - v0))
    guard = 0
    while len(new_uv) < len(corners) + len(lerps) and guard < 8:
        guard += 1
        for k, (ka, kb, t_) in lerps.items():
            if k in new_uv or ka not in new_uv or kb not in new_uv:
                continue
            ua, ub = new_uv[ka], new_uv[kb]
            new_uv[k] = (ua[0] + t_ * (ub[0] - ua[0]), ua[1] + t_ * (ub[1] - ua[1]))
    if len(new_uv) < len(corners) + len(lerps):
        raise ValueError(f"a lerp chain in the tile at {cell} never grounds -- refusing")
    return [[(v[0], v[1], new_uv[_pk(v[0])], v[3]) for v in t3] for t3 in gtris]


def band_convert(donor, cell, to_part, *, disc: int = 1, lod: str = "0_1", game=None):
    """RUNG 3, step 1 -- THE ONE-CELL BAND-CONVERSION PROBE: re-band one LATTICE
    water cell of a non-strip band (sea3/sea4) into strip band ``to_part`` and
    re-emit every affected strip neighbour under its new deep-edge-set via THE
    DEFORMED-TILE RECT LAW. The neighbour re-emissions are the first genuinely
    FRESH deformed-tile emissions -- their rects are CHOSEN from the learned Wang
    table for the new shade field, not transported -- and the whole edit is the
    exact miniature of the virgin mint's ring re-band (every virgin pocket is one
    lattice column short).

    ``cell`` is a donor-frame 4u lattice cell index ``(cx, cz)`` (world x in
    ``[4cx, 4cx+4)``, z in ``[4cz, 4cz+4)``). Geometry/normals/IDALL transport
    verbatim; only uvs and the part change. Every law gate raises ``ValueError``."""
    if to_part not in ("sea1", "sea5"):
        raise ValueError(f"band conversion targets a strip band (sea1/sea5), not {to_part}")
    cx, cz = cell
    bx, by = donor
    if not (16 * bx < cx < 16 * bx + 15 and -16 * by - 16 < cz < -16 * by - 1):
        raise ValueError(f"cell {cell} sits on block {donor}'s frame ring -- a frame "
                         f"cell's shade field crosses into the neighbour block")
    parts = ("beach1", "sea2", "sea1", "sea3", "sea5", "sea4")
    tris = {p: TR.world_tris(*donor, p, disc=disc, lod=lod, game=game) for p in parts}
    groups_by_part = {p: list(_deformed_strip_groups(tris[p])) for p in ("sea1", "sea5")}
    u_pair, v_rows = _strip_float_vocab(groups_by_part)

    owner = defaultdict(set)
    by_cell = defaultdict(list)
    for p in parts:
        for t3 in tris[p]:
            c = _cell_of_tri(t3)
            owner[c].add(p)
            by_cell[(p, c)].append(t3)

    def water_of(c):
        return {p for p in owner.get(c, ()) if p in WATER_DEPTH}

    own_c = water_of((cx, cz))
    if len(own_c) != 1:
        raise ValueError(f"cell {cell} is owned by {sorted(own_c)} -- the one-cell "
                         f"conversion needs exactly one water band there")
    from_part = next(iter(own_c))
    if from_part not in ("sea3", "sea4"):
        raise ValueError(f"cell {cell} is {from_part} -- v1 converts FROM a non-strip "
                         f"band (sea3/sea4) only (a strip source needs its own re-band)")
    if from_part == to_part:
        raise ValueError(f"cell {cell} already is {to_part}")
    c_tris = by_cell[(from_part, (cx, cz))]

    def on_lat(v, eps=0.02):
        return (abs(v[0][0] / 4 - round(v[0][0] / 4)) < eps
                and abs(v[0][2] / 4 - round(v[0][2] / 4)) < eps)
    if not all(on_lat(v) for t3 in c_tris for v in t3):
        raise ValueError(f"cell {cell}'s {from_part} tile is shore-conforming -- the "
                         f"v1 probe converts a pure LATTICE cell")

    # ---- the strip-tile registry: discrete role-decode of every strip group
    reg = {}
    for p, gs in groups_by_part.items():
        for gtris, kind, det in gs:
            c = Counter(_cell_of_tri(t) for t in gtris).most_common(1)[0][0]
            ent = {"gtris": gtris, "det": det, "es": None, "row": None, "oname": None}
            if kind == "rect":
                hits = _role_decode(det[0], c, u_pair, v_rows)
                if len(hits) == 1:
                    ri, oname = hits[0]
                    ent.update(row=ri, oname=oname,
                               es=TR.STRIP_EDGESET.get((ri, oname)))
            reg[(p, c)] = ent

    _shade_gate(reg, water_of, cell, "pre")            # the donor must pass: null test

    # ---- C's own new edge-set (pure depth facts -- a fresh tile carries no pinches)
    es_c = frozenset(
        dname for dname, (dx, dz) in TR._DIRS.items()
        if water_of((cx + dx, cz + dz))
        and max(WATER_DEPTH[q] for q in water_of((cx + dx, cz + dz))) > WATER_DEPTH[to_part])
    if es_c not in TR.EDGESET2STRIP:
        raise ValueError(f"cell {cell} -> {to_part} needs edge-set {sorted(es_c)}, "
                         f"which has no learned strip -- not a lawful conversion site")

    # ---- affected strip neighbours: claims toward C that must change
    affected = []
    for dname, (dx, dz) in TR._DIRS.items():
        n = (cx + dx, cz + dz)
        for p in ("sea1", "sea5"):
            if p not in water_of(n):
                continue
            if p != to_part:
                # the other strip band: its C-facing depth fact must not flip
                if (WATER_DEPTH[from_part] > WATER_DEPTH[p]) \
                        != (WATER_DEPTH[to_part] > WATER_DEPTH[p]):
                    raise ValueError(f"conversion flips the {p} tile at {n}'s depth "
                                     f"fact -- v1 re-emits only the target band")
                continue
            t = reg.get((p, n))
            if t is None or t["es"] is None:
                raise ValueError(f"the {p} tile at {n} does not role-decode -- its "
                                 f"re-emission would not be law-derived; refusing")
            if _OPP[dname] not in t["es"]:
                continue                        # already shallow toward C: unaffected
            es_new = frozenset(t["es"] - {_OPP[dname]})
            if es_new not in TR.EDGESET2STRIP:
                raise ValueError(
                    f"the {p} tile at {n} would need edge-set {sorted(es_new)} "
                    f"(no learned strip) -- the conversion cascades; refusing")
            affected.append((p, n, t, es_new))
    if not affected:
        raise ValueError(f"cell {cell}: no affected {to_part} neighbour -- nothing "
                         f"here exercises the deformed emission; pick a ring cell")

    # ---- emission (block floats; hash-picked variant, the _strip_uvf pick formula)
    def pick(esf, c):
        return _strip_pick(esf, c)

    def emit_group(gtris, corners, lerps, c, ri, oname):
        return _strip_emit(gtris, corners, lerps, c, ri, oname, u_pair, v_rows)

    ri_c, oname_c = pick(es_c, (cx, cz))
    corners_c = {}
    for t3 in c_tris:
        for v in t3:
            corners_c.setdefault(_pk(v[0]), (v[0], (v[2][0], v[2][1]), None))
    if len(corners_c) != 4:
        raise ValueError(f"cell {cell}'s {from_part} tile has {len(corners_c)} distinct "
                         f"verts (want a clean 4-corner quad) -- refusing")
    c_new = emit_group(c_tris, corners_c, {}, (cx, cz), ri_c, oname_c)

    re_drop, re_emit, post_reg = [], [], dict(reg)
    for p, n, t, es_new in affected:
        ri_n, oname_n = pick(es_new, n)
        corners, lerps = t["det"]
        new_tris = emit_group(t["gtris"], corners, lerps, n, ri_n, oname_n)
        re_drop.extend(t["gtris"])
        re_emit.extend(new_tris)
        post_reg[(p, n)] = {"gtris": new_tris, "det": None, "es": es_new,
                            "row": ri_n, "oname": oname_n}
    post_reg[(to_part, (cx, cz))] = {"gtris": c_new, "det": None, "es": es_c,
                                     "row": ri_c, "oname": oname_c}

    # ---- gates on the POST state
    owner2 = defaultdict(set, {c: set(ps) for c, ps in owner.items()})
    owner2[(cx, cz)] = (owner2[(cx, cz)] - {from_part}) | {to_part}

    def water2(c):
        return {p for p in owner2.get(c, ()) if p in WATER_DEPTH}
    _shade_gate(post_reg, water2, cell, "post")
    for c in list(owner2):
        if max(abs(c[0] - cx), abs(c[1] - cz)) > 2:
            continue
        for dx, dz in ((1, 0), (0, 1)):
            n = (c[0] + dx, c[1] + dz)
            for a in water2(c) - {"beach1", "sea2"}:
                for b in water2(n) - {"beach1", "sea2"}:
                    if frozenset((a, b)) not in _LAWFUL_ADJ:
                        raise ValueError(f"adjacency gate: {a} at {c} beside {b} at "
                                         f"{n} is off-language after the conversion")
    # re-decode gate: every emission re-reads as the intended tile
    for (p, c), t in post_reg.items():
        if t["det"] is not None:
            continue
        decoded = list(_deformed_strip_groups(t["gtris"]))
        if len(decoded) != 1 or decoded[0][1] != "rect":
            raise ValueError(f"re-decode gate: the emitted {p} tile at {c} does not "
                             f"decode as one rect group")
        hits = _role_decode(decoded[0][2][0], c, u_pair, v_rows)
        if hits != [(t["row"], t["oname"])]:
            raise ValueError(f"re-decode gate: the emitted {p} tile at {c} reads "
                             f"{hits}, wanted {[(t['row'], t['oname'])]}")
    for t3 in c_new:                             # the strips_rebuild-style self-check
        if TR.strip_edge_set(t3) != es_c:
            raise ValueError("re-decode gate: C's lattice tile does not decode to its "
                             "edge-set through the learned table")
    # geometry-identity gate (no T-vertex exposure by construction)
    if sorted(_pk(v[0]) for t3 in re_emit + c_new for v in t3) \
            != sorted(_pk(v[0]) for t3 in re_drop + c_tris for v in t3):
        raise ValueError("geometry gate: emitted positions differ from dropped -- a "
                         "band conversion must transport geometry verbatim")

    return [TR.DropTris(from_part, c_tris), TR.EmitTris(to_part, c_new),
            TR.DropTris(to_part, re_drop), TR.EmitTris(to_part, re_emit)]


#: THE SAND-BAND LANGUAGE (byte-learned 2026-07-10, Path A -- the census over every
#: topo-31 band map-wide: 14 connected bands, 437 tris across 27 blocks; each law below
#: held with ZERO exceptions):
#:
#: * **u-strip** -- the whole band lives in atlas u [270, 396]/1024, split at 334 into two
#:   rects P = [270, 334] and Q = [334, 396]; every run/cap tri spans exactly ONE rect
#:   (never both outer edges), interior verts interpolate affinely (lawful subdivision).
#: * **v-ribbon** (the sand-ribbon law, re-confirmed): run columns stretch one v-rect,
#:   land-chain pin 580 or 581 /1024 -> seam-chain pin 609 or 610; the pins are per-BAND
#:   constants (a band picks one of each, independently). The CAP band (row B) is
#:   strictly terminal: land 612-615 -> seam 640-642.
#: * **THE ONE-SHADE LAW** -- at a column boundary (a u-constant PORT edge) any lattice
#:   edge may abut any other: all pairs are byte-observed (share x36, wrap 3867|2637 x32,
#:   3262|2637 x18, 3867|3262 x12, ...) and the atlas texel columns at the three edges
#:   differ no more than sand differs from itself 8px away (12.8/15.9/17.1 vs baseline
#:   11.8-17.8) -- homogeneous noise, so a fresh restart anywhere is invisible. The CAP
#:   band is the opposite (a directional taper gradient, 38-69 vs ~17-27): caps are only
#:   lawful in rect Q, 0.3867 edge facing the beach END (all 19 clean real caps).
#: * **Grain** -- in the land-on-left frame ~86% of run tiles read u-increasing (P+ 44 /
#:   Q+ 42 vs P- 8 / Q- 6); mirror FOLDS (Q+ = Q- sharing an outer edge) are real but
#:   rare. Emission transports the donor's orientation and re-picks only the RECT --
#:   a lawful subset, the strips-emission precedent.
SAND_ULAT = (270.0 / 1024, 334.0 / 1024, 396.0 / 1024)
#: decode anchors (4dp census values; per-band quarter-texel snap variants)
SAND_V_LAND = (0.5664, 0.5674)
SAND_V_SEAM = (0.5947, 0.5957)
SAND_V_CAP_LAND = (0.5977, 0.5986, 0.5996, 0.6006, 0.6045, 0.6123)
SAND_V_CAP_SEAM = (0.625, 0.626, 0.627)
_SAND_EPS_V = 0.0022
_SAND_EPS_U = 0.004

#: THE SAND-BAND FAMILIES (the beach translation law -- 2026-07-15,
#: ``studies/overworld-topography/desert_beach_{anatomy,decode}.py``): the desert
#: coast's sand band (topo 32 -- the Outer Continent's 14 beach blocks; 112 map-wide
#: back-welds onto topo-17 ground) is the grass band's STRUCTURE at its own atlas
#: spot: the u-strip shifted EXACTLY +335/1024 texels (P/Q split preserved, both
#: rects used), and its own SINGLE-VALUED v pins -- run 548->579, cap 580->611
#: (vs grass run 580->609/610, cap 612..615->640..642: land edges -32, seam edges
#: -30 texels; the desert ribbon is 2 texels taller). The sand topo is FAMILY-KEYED
#: 1:1 with the backing ground (every beach block is PURE 31 or PURE 32; 31 <=>
#: grass-backed, 32 <=> desert-backed, zero exceptions). Foam (beach1) is universal.
#: Desert ``eps_v`` must stay under half the 1-texel run-seam/cap-land gap (579 vs
#: 580) or the tiers smear. topo 33 = the Lost Continent's foam-less frozen shore
#: (+330 texels) -- measured, NOT yet a mintable family.
SAND_BANDS = {
    "grass": dict(topo=31, du=0.0, eps_v=_SAND_EPS_V,
                  v_land=SAND_V_LAND, v_seam=SAND_V_SEAM,
                  v_cap_land=SAND_V_CAP_LAND, v_cap_seam=SAND_V_CAP_SEAM),
    "desert": dict(topo=32, du=335.0 / 1024, eps_v=0.0004,
                   v_land=(0.53516,), v_seam=(0.56543,),
                   v_cap_land=(0.56641,), v_cap_seam=(0.59668,)),
}
_SAND_GRASS = SAND_BANDS["grass"]


def _sand_band_family(terr, *, what="donor"):
    """Detect a block's sand-band family from its terrain tris (PURE 31 or PURE 32
    per the census; mixed = off-language, refuse). Returns the family dict with a
    ``name`` key, or ``None`` when the block carries no sand at all."""
    counts = {}
    for t3 in terr:
        tp = decode_id(int(round(t3[0][3][0])))["topograph"]
        for name, fam in SAND_BANDS.items():
            if tp == fam["topo"]:
                counts[name] = counts.get(name, 0) + 1
    if not counts:
        return None
    if len(counts) > 1:
        raise ValueError(f"{what} carries MIXED sand families {counts} -- "
                         f"off-language (the census: every beach block is pure)")
    name = next(iter(counts))
    return dict(SAND_BANDS[name], name=name)


def _sand_vclass(v, fam=_SAND_GRASS):
    """A sand vert's v-band role, or ``None`` off every pin (the conforming tier)."""
    for name, anchors in (("run_land", fam["v_land"]), ("run_seam", fam["v_seam"]),
                          ("cap_land", fam["v_cap_land"]),
                          ("cap_seam", fam["v_cap_seam"])):
        if any(abs(v - a) <= fam["eps_v"] for a in anchors):
            return name
    return None


def _sand_tri_decode(t3, fam=_SAND_GRASS):
    """``(tier, rect)`` for a decodable sand tri -- tier ``run``/``cap`` with every v on
    that tier's chain pins and every u inside ONE u-rect; ``None`` = the conforming /
    spit-fold / skew-cap residual (stays verbatim, like the strips' inset variants)."""
    cls = [_sand_vclass(v[2][1], fam) for v in t3]
    if any(c is None for c in cls):
        return None
    tier = "run" if all(c.startswith("run") for c in cls) else \
        "cap" if all(c.startswith("cap") for c in cls) else None
    if tier is None:
        return None
    du = fam["du"]
    us = [v[2][0] for v in t3]
    rects = [r for r in (0, 1)
             if all(SAND_ULAT[r] + du - _SAND_EPS_U <= u
                    <= SAND_ULAT[r + 1] + du + _SAND_EPS_U for u in us)]
    if not rects:
        return None
    if tier == "cap" and rects != [1]:
        return None                       # the taper gradient only exists in rect Q
    # a tri hugging the shared edge 334 decodes to either rect; pick by span midpoint
    r = rects[0] if len(rects) == 1 else \
        (0 if (min(us) + max(us)) / 2.0 < SAND_ULAT[1] + du else 1)
    return (tier, r)


def sand_rebuild(donor, *, disc: int = 1, lod: str = "0_1", game=None):
    """The SAND-BAND identity rebuild (Path A shipped) -- the strips_rebuild recipe on the
    beach's third discrete language: DROP every closed decodable sand column group and
    RE-DERIVE its u's from the learned strip, same verts, v/normals/positions byte-
    unchanged. Freshness = a deterministic per-group RECT FLIP (P <-> Q): a two-way
    hash pick can silently coincide with the donor and prove nothing (the (7,17)
    two-group coincidence), while the flip makes every emitted group a REAL
    re-derivation -- all-same-rect runs are byte-real ((17,9)'s east run) and every
    flipped boundary lands in the observed pair set, so the flip is lawful by the
    ONE-SHADE law. The donor's orientation, folds and subdivisions TRANSPORT through
    the 1-D u-affine.

    Grouping: tris union over uv-equal shared edges OF THE SAME RECT (merges a quad's
    diagonal, subdivision edges and the real mirror folds; never merges across the
    P+=Q+ wallpaper share). THE CLOSURE FREEZE: a group emits only if every non-internal
    edge is a PORT (u-constant) or a CHAIN edge (v-equal) -- half-quads against the
    conforming tier and columns split by a block frame both fail it and stay verbatim
    (both are real: (7,17)'s bend fan, the (17,9)/(17,10) frame-straddling column).
    RUN groups only: the row-B CAP tiles belong to the end-cap ASSEMBLY rung (the other
    beach-mint prerequisite) and stay verbatim here, like the conforming tier.
    Self-check: every emitted tri must re-decode to its group's fresh rect."""
    terr = TR.world_tris(*donor, "terrain", disc=disc, lod=lod, game=game)
    fam = _sand_band_family(terr, what=f"donor {donor}")
    if fam is None:
        raise ValueError(f"donor {donor} has no sand band -- not a sandy shore")
    sand = [t3 for t3 in terr
            if decode_id(int(round(t3[0][3][0])))["topograph"] == fam["topo"]]
    dec = [_sand_tri_decode(t3, fam) for t3 in sand]

    def uv4(v):
        return (round(v[2][0], 4), round(v[2][1], 4))

    # union decodable tris over uv-equal same-rect shared edges
    idx = [i for i, d in enumerate(dec) if d is not None]
    parent = {i: i for i in idx}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    edge_insts = defaultdict(list)        # poskey-pair -> [(tri, {poskey: uv4})]
    for i in idx:
        t3 = sand[i]
        for a in range(3):
            b = (a + 1) % 3
            key = frozenset((_pk(t3[a][0]), _pk(t3[b][0])))
            edge_insts[key].append((i, {_pk(t3[a][0]): uv4(t3[a]),
                                        _pk(t3[b][0]): uv4(t3[b])}))
    for key, insts in edge_insts.items():
        if len(insts) != 2:
            continue
        (i, uva), (j, uvb) = insts
        if dec[i][1] == dec[j][1] and uva == uvb:
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[rj] = ri
    groups = defaultdict(list)
    for i in idx:
        groups[find(i)].append(i)

    # closure freeze + emission
    drop, emit = [], []
    for root, mem in sorted(groups.items(),
                            key=lambda kv: min(_pk(sand[i][0][0]) for i in kv[1])):
        tier, rect = dec[mem[0]]
        if tier != "run" or any(dec[i] != (tier, rect) for i in mem):
            continue                      # caps verbatim; a mixed group = decode artifact
        ec = defaultdict(int)
        einfo = {}
        for i in mem:
            t3 = sand[i]
            for a in range(3):
                b = (a + 1) % 3
                key = frozenset((_pk(t3[a][0]), _pk(t3[b][0])))
                ec[key] += 1
                einfo[key] = (abs(t3[a][2][0] - t3[b][2][0]) <= 1e-4,   # port: u const
                              abs(t3[a][2][1] - t3[b][2][1]) <= 1e-4)   # chain: v const
        closed = all(ec[k] == 2 or einfo[k][0] or einfo[k][1] for k in ec)
        if not closed:
            continue                      # half-quad / frame-split: verbatim residual
        us = [v[2][0] for i in mem for v in sand[i]]
        d0, d1 = min(us), max(us)
        if abs(d0 - SAND_ULAT[rect] - fam["du"]) > _SAND_EPS_U \
                or abs(d1 - SAND_ULAT[rect + 1] - fam["du"]) > _SAND_EPS_U:
            continue                      # ports must span the FULL rect (never stretch)
        new_rect = 1 - rect
        e0, e1 = SAND_ULAT[new_rect] + fam["du"], SAND_ULAT[new_rect + 1] + fam["du"]
        scale = (e1 - e0) / (d1 - d0)
        new_tris = []
        for i in mem:
            new_tris.append([(v[0], v[1], (e0 + (v[2][0] - d0) * scale, v[2][1]), v[3])
                             for v in sand[i]])
        for t3 in new_tris:
            got = _sand_tri_decode(t3, fam)
            if got != ("run", new_rect):
                raise ValueError(f"sand group at {_pk(sand[mem[0]][0][0])}: the emitted "
                                 f"column re-decodes to {got} instead of "
                                 f"('run', {new_rect}) -- the emission self-check failed")
        drop.extend(sand[i] for i in mem)
        emit.extend(new_tris)
    if not drop:
        raise ValueError(f"donor {donor} has no closed decodable sand columns")
    return [TR.DropTris("terrain", drop), TR.EmitTris("terrain", emit)]


#: THE END-CAP LAWS (byte-learned 2026-07-11 -- the assembly census over all 40 beach1
#: blocks: 50 foam cap groups; every whole cap derives from these laws, the residual is
#: exactly frame-split fragments + the (3,11) spit + the BR slot):
#:
#: * The foam texture is a 64px 2x2 sheet: run swash TL [0,.5]x[0,.5]; TWO interchangeable
#:   end-cap GRAPHICS -- **BL** [0,.5]x[.5,1] (the taper band BELOW the run tile; v jumps
#:   at the junction) and **TR** [.5,1]x[0,.5] (the run band's rightward fade; v CONTINUES
#:   the run rows, so its v snaps are FORCED to the block's run family). Both are squared
#:   QUADS between the sand seam and the waterline (the old "wedge" reading was a weld
#:   artifact -- the free-water corner often welds terrain at the pinch). BR = the
#:   spit/river-mouth tip vocabulary (verbatim residual, like the sand spit fold).
#: * Orientation is LAW: the junction edge carries the tile edge NEAREST the run graphic
#:   (BL u=uJ~0.5; TR u~0.5/0.5156) and the free edge faces the beach end (BL u=uF~0;
#:   TR u=0.9844) -- mirrored per end, both ends use the same graphic values.
#: * The rest is per-cap TEXEL SNAPS, all byte-observed: BL uF in {0, 0.0156}, uJ in
#:   {0.4844, 0.5}, vS in {0.5, 0.5156, 0.5312}, vW in {60..63}/64.
#: * **THE TAPER ASYMMETRY (in-game falsified 2026-07-11 at the (9,8) slot-flip A/B --
#:   "non-capped straight lines"):** the global beach texture (4 animated frames
#:   ``11_0_128_*``, 128x64) is ONE curling-swash composition -- only the BL window
#:   carries a true FADE (band collapses at u->0), while the TR window carries the
#:   FULL-STRENGTH band curling waterward (strengthens toward u->1). A TR cap never
#:   fades: it reads right only where the end's geometry carries the curl into the
#:   water; on a straight squared end it reads as a non-capped hard cut. So the slot
#:   is NOT a free style -- THE SLOT LAW: rebuilds TRANSPORT the donor's slot; mint
#:   defaults to BL (the universal fade) and uses TR only as a deliberate curl-out.
#: * The SAND cap (row B, Path A census): rect Q [0.3262, 0.3867], junction edge 0.3262,
#:   free edge 0.3867, v = per-cap pins land {612..615}/1024 -> seam {640..642}/1024.
#:
#: Families keyed by the block's modal run-tile (vS_run, vW_run); each maps to its
#: byte-observed BL snaps (uF, uJ, vS, vW) and TR junction-u. The (0.0156, 0.4531)
#: family has no observed TR cap -- its TR values are LAW-FORCED (v continues the run
#: rows), the generalization the A/B deploy tests.
FOAM_FAMILIES = {
    (0.0, 0.4844): {"BL": (0.0, 0.5, 0.5, 0.9844), "TR_UJ": 0.5},
    (0.0156, 0.4688): {"BL": (0.0, 0.5, 0.53125, 0.953125), "TR_UJ": 0.515625},
    (0.0156, 0.4531): {"BL": (0.015625, 0.5, 0.53125, 0.9375), "TR_UJ": 0.515625},
    (0.0, 0.4531): {"BL": (0.0, 0.5, 0.53125, 0.9375), "TR_UJ": 0.5},
}
FOAM_TR_UT = 0.984375                 # the TR free edge (63/64)
_CAP_EPS = 0.0022


def _foam_family(foam_tris):
    """The block's run family = the modal (vS, vW) over its TL run tiles."""
    from collections import Counter
    cnt = Counter()
    for t3 in foam_tris:
        us = [v[2][0] for v in t3]
        vs = [v[2][1] for v in t3]
        if max(us) <= 0.502 and max(vs) <= 0.502:
            cnt[(round(min(vs), 4), round(max(vs), 4))] += 1
    for (v0, v1), _n in cnt.most_common():
        for fam in FOAM_FAMILIES:
            if abs(v0 - fam[0]) <= _CAP_EPS and abs(v1 - fam[1]) <= _CAP_EPS:
                return fam
    return None


def emit_foam_cap(sj, wj, sf, wf, *, slot, family, diag="wj-sf", nrm=None, idall=None,
                  snaps=None, interior=()):
    """SYNTHESIZE a beach end-cap foam tile (the mint-facing emitter): corners
    sand-junction / water-junction / sand-free / water-free (positions), the cap
    ``slot`` (``"BL"`` the universal fade | ``"TR"`` the curl-out -- see THE TAPER
    ASYMMETRY above: TR only where the end carries the curl into the water), the
    block's run ``family`` key, and the quad ``diag`` (``"wj-sf"`` | ``"sj-wf"``, the
    donor-alternating split). ``snaps=(uF, uJ, vS, vW)`` overrides the family's modal
    snap scalars (the rebuild transports the donor cap's own). Returns the cap's
    triangles."""
    if snaps is not None:
        uF, uJ, vS, vW = snaps
    elif slot == "BL":
        uF, uJ, vS, vW = FOAM_FAMILIES[family]["BL"]
    else:
        uF, uJ, vS, vW = FOAM_TR_UT, FOAM_FAMILIES[family]["TR_UJ"], family[0], family[1]
    uv = {id(sj): (uJ, vS), id(wj): (uJ, vW), id(sf): (uF, vS), id(wf): (uF, vW)}
    nrm = nrm or (0.0, 1.0, 0.0)
    idall = idall or (0.0, 0.0, 0.0, 0.0)

    def V(p):
        return (p, nrm, uv[id(p)], idall)
    split = ((wj, sf, sj), (wj, wf, sf)) if diag == "wj-sf" \
        else ((sj, wf, wj), (sj, sf, wf))
    tris = [_up_tri([V(p) for p in t]) for t in split]
    if interior:
        raise ValueError("interior subdivision emission is the rebuild's transport "
                         "path -- the mint emitter takes clean corner quads")
    return tris


def emit_sand_cap(lj, sj, lf, sf, *, land_pin, seam_pin, diag="sj-lf", nrm=None,
                  idall=None, fam=_SAND_GRASS):
    """SYNTHESIZE a sand row-B cap tile: corners land-junction / seam-junction /
    land-free / seam-free; the per-cap v pins (byte-observed bands: grass land
    612-615, seam 640-642 /1024; desert 580 -> 611). u is LAW: rect Q (shifted per
    family) with the junction edge at the split and the free edge at the strip end
    (the taper points outward)."""
    uJ, uF = SAND_ULAT[1] + fam["du"], SAND_ULAT[2] + fam["du"]
    uv = {id(lj): (uJ, land_pin), id(sj): (uJ, seam_pin),
          id(lf): (uF, land_pin), id(sf): (uF, seam_pin)}
    nrm = nrm or (0.0, 1.0, 0.0)
    idall = idall or (0.0, 0.0, 0.0, 0.0)

    def V(p):
        return (p, nrm, uv[id(p)], idall)
    split = ((sj, lf, lj), (sj, sf, lf)) if diag == "sj-lf" \
        else ((lj, sf, sj), (lj, lf, sf))
    return [_up_tri([V(p) for p in t]) for t in split]


def _foam_cap_groups(foam):
    """Group a block's non-TL foam tris into cap groups (shared verts, same slot).
    Yields ``(slot, [tri, ...])``."""
    def slot_of(t3):
        us = [v[2][0] for v in t3]
        vs = [v[2][1] for v in t3]
        uu = "L" if max(us) <= 0.502 else ("R" if min(us) >= 0.498 else "X")
        vv = "T" if max(vs) <= 0.502 else ("B" if min(vs) >= 0.498 else "X")
        return vv + uu
    caps = [(slot_of(t3), t3) for t3 in foam]
    caps = [(s, t3) for s, t3 in caps if s in ("BL", "TR", "BR")]
    used = [False] * len(caps)
    for i in range(len(caps)):
        if used[i]:
            continue
        grp = [caps[i][1]]
        used[i] = True
        keys = {_pk(v[0]) for v in caps[i][1]}
        changed = True
        while changed:
            changed = False
            for j in range(len(caps)):
                if used[j] or caps[j][0] != caps[i][0]:
                    continue
                if keys & {_pk(v[0]) for v in caps[j][1]}:
                    grp.append(caps[j][1])
                    used[j] = True
                    keys |= {_pk(v[0]) for v in caps[j][1]}
                    changed = True
        yield caps[i][0], grp


#: 4dp census value -> the exact atlas float (64px v-texels / 128px u-texels); the
#: byte gate proves every real cap corner sits EXACTLY on these.
_CAP_CANON = {0.0: 0.0, 0.0156: 0.015625, 0.4531: 0.453125, 0.4688: 0.46875,
              0.4844: 0.484375, 0.5: 0.5, 0.5156: 0.515625, 0.5312: 0.53125,
              0.9375: 0.9375, 0.9531: 0.953125, 0.9688: 0.96875, 0.9844: 0.984375}


def cap_rebuild(donor, *, disc: int = 1, lod: str = "0_1", game=None):
    """The END-CAP identity rebuild (the assembly rung's completeness proof): every
    lawful foam cap re-emits through :func:`emit_foam_cap` with the donor's OWN slot
    (THE SLOT LAW -- the slot-flip A/B falsified slot freedom in-game: TR never fades)
    and its snap scalars identified to the exact canonical atlas floats, and every
    lawful sand row-B cap re-emits through :func:`emit_sand_cap`. BOTH parts carry an
    internal BYTE-EQUALITY gate: the emitted cap must equal the donor bytes exactly --
    caps have zero lawful freedom beyond their snaps, so the round-trip IS the proof
    that the laws are complete. Residual (BR spit vocabulary, frame-split fragments,
    subdivided caps) stays verbatim."""
    foam = TR.world_tris(*donor, "beach1", disc=disc, lod=lod, game=game)
    if not foam:
        raise ValueError(f"donor {donor} has no beach1 mesh -- not a sandy shore")
    family = _foam_family(foam)
    if family is None:
        raise ValueError(f"donor {donor}: no lawful foam run family decodes")
    run_keys = set()
    for t3 in foam:
        us = [v[2][0] for v in t3]
        vs = [v[2][1] for v in t3]
        if max(us) <= 0.502 and max(vs) <= 0.502:
            run_keys |= {_pk(v[0]) for v in t3}
    drop_f, emit_f = [], []
    for slot, grp in _foam_cap_groups(foam):
        if slot == "BR" or len(grp) != 2:
            continue                       # spit vocabulary / subdivided: verbatim
        verts = {}
        for t3 in grp:
            for v in t3:
                verts.setdefault(_pk(v[0]), v)
        if len(verts) != 4:
            continue
        vl = list(verts.values())
        rows = sorted({round(v[2][1], 4) for v in vl})
        cols = sorted({round(v[2][0], 4) for v in vl})
        if len(rows) != 2 or len(cols) != 2:
            continue                       # skewed cap (a non-2x2 UV grid): verbatim
        if slot == "BL":
            uF_d, uJ_d = cols
        else:
            uJ_d, uF_d = cols
        lawful = (uF_d in (0.0, 0.0156, 0.9844) and uJ_d in (0.4844, 0.5, 0.5156)
                  and (slot != "BL" or (rows[0] in (0.5, 0.5156, 0.5312)
                                        and rows[1] in (0.9375, 0.9531, 0.9688,
                                                        0.9844)))
                  and (slot != "TR" or (abs(rows[0] - family[0]) <= _CAP_EPS
                                        and abs(rows[1] - family[1]) <= _CAP_EPS)))
        if not lawful:
            continue                       # frame-split / half caps: verbatim
        # corners by (donor u ~ junction/free, donor v ~ sand/water row)
        c = {}
        for v in vl:
            j = abs(v[2][0] - uJ_d) < abs(v[2][0] - uF_d)
            s = abs(v[2][1] - rows[0]) < abs(v[2][1] - rows[1])
            c[("J" if j else "F") + ("S" if s else "W")] = v
        if len(c) != 4:
            continue
        # the donor's diagonal: which corner pair shares both tris
        both = set.intersection(*({_pk(v[0]) for v in t3} for t3 in grp))
        diag = "wj-sf" if both == {_pk(c["JW"][0]), _pk(c["FS"][0])} else "sj-wf"
        nrm, idall = vl[0][1], tuple(vl[0][3])
        snaps = (_CAP_CANON[uF_d], _CAP_CANON[uJ_d],
                 _CAP_CANON[rows[0]], _CAP_CANON[rows[1]])
        tris = emit_foam_cap(c["JS"][0], c["JW"][0], c["FS"][0], c["FW"][0],
                             slot=slot, family=family, diag=diag, snaps=snaps,
                             nrm=nrm, idall=idall)
        want = {frozenset((_pk(v[0]), round(v[2][0], 4), round(v[2][1], 4))
                          for v in t3) for t3 in grp}
        got = {frozenset((_pk(v[0]), round(v[2][0], 4), round(v[2][1], 4))
                         for v in t3) for t3 in tris}
        if got != want:
            raise ValueError(f"foam cap at {_pk(vl[0][0])}: the law derivation is not "
                             f"byte-exact -- the round-trip gate failed")
        drop_f.extend(grp)
        emit_f.extend(tris)

    # sand row-B caps: byte-identity through the emitter (rect Q forced = the proof)
    terr = TR.world_tris(*donor, "terrain", disc=disc, lod=lod, game=game)
    fam = _sand_band_family(terr, what=f"donor {donor}") or _SAND_GRASS
    uJ4 = round(SAND_ULAT[1] + fam["du"], 4)
    uF4 = round(SAND_ULAT[2] + fam["du"], 4)
    sand_caps = [t3 for t3 in terr
                 if decode_id(int(round(t3[0][3][0])))["topograph"] == fam["topo"]
                 and _sand_tri_decode(t3, fam) is not None
                 and _sand_tri_decode(t3, fam)[0] == "cap"]
    drop_s, emit_s = [], []
    grouped = []                          # [[keyset, [tris]], ...]
    for t3 in sand_caps:
        keys = frozenset(_pk(v[0]) for v in t3)
        hit = next((g for g in grouped if g[0] & keys), None)
        if hit is not None:
            hit[0] = hit[0] | keys
            hit[1].append(t3)
        else:
            grouped.append([keys, [t3]])
    for keys, grp in grouped:
        if len(grp) != 2:
            continue
        verts = {}
        for t3 in grp:
            for v in t3:
                verts.setdefault(_pk(v[0]), v)
        if len(verts) != 4:
            continue
        vl = list(verts.values())
        us = sorted({round(v[2][0], 4) for v in vl})
        vs = sorted({round(v[2][1], 4) for v in vl})
        if len(us) != 2 or len(vs) != 2 or us != [uJ4, uF4]:
            continue
        c = {}
        for v in vl:
            j = abs(v[2][0] - uJ4) < abs(v[2][0] - uF4)
            land = abs(v[2][1] - vs[0]) < abs(v[2][1] - vs[1])
            c[("J" if j else "F") + ("L" if land else "S")] = v
        if len(c) != 4:
            continue
        both = set.intersection(*({_pk(v[0]) for v in t3} for t3 in grp))
        diag = "sj-lf" if both == {_pk(c["JS"][0]), _pk(c["FL"][0])} else "lj-sf"
        tris = emit_sand_cap(c["JL"][0], c["JS"][0], c["FL"][0], c["FS"][0],
                             land_pin=c["JL"][2][1], seam_pin=c["JS"][2][1],
                             diag=diag, nrm=vl[0][1], idall=tuple(vl[0][3]), fam=fam)
        want = {frozenset((_pk(v[0]), round(v[2][0], 4), round(v[2][1], 4))
                          for v in t3) for t3 in grp}
        got = {frozenset((_pk(v[0]), round(v[2][0], 4), round(v[2][1], 4))
                         for v in t3) for t3 in tris}
        if got != want:
            raise ValueError(f"sand cap at {_pk(vl[0][0])}: the law derivation is not "
                             f"byte-exact -- the round-trip gate failed")
        drop_s.extend(grp)
        emit_s.extend(tris)

    if not drop_f and not drop_s:
        raise ValueError(f"donor {donor} has no lawful end caps")
    out = []
    if drop_f:
        out += [TR.DropTris("beach1", drop_f), TR.EmitTris("beach1", emit_f)]
    if drop_s:
        out += [TR.DropTris("terrain", drop_s), TR.EmitTris("terrain", emit_s)]
    return out


#: mint gates -- the byte-measured beach envelopes (the ribbon law / the slope gate /
#: the cross-beach swash envelope)
MINT_BAND_W = (1.8, 6.6)
MINT_SLOPE = (0.097, 0.579)
MINT_SWASH = (3.3, 6.7)


def beach_mint(donor, *, width=None, land=None, disc: int = 1, lod: str = "0_1",
               game=None):
    """BEACH-MINT rung 1 (the shore-vocabulary capstone's first composition): re-mint a
    real beach's sand band + foam ASSEMBLY from chain specs -- everything between the
    pinned INTERFACES is synthesized. Pinned (verts shared with parts the mint does not
    touch): the land chain L (grass welds), the waterline W (sea2 welds), and the two
    end columns' outer verts (the coast/wash/ring welds). Synthesized: the interior
    SAND SEAM chain (repositioned to a smooth ``width`` profile eased from the pinned
    end widths, on the L->W ramp), the clean column topology (the donor's conforming
    fan and subdivisions are NOT copied -- gentle bends carry clean ribbon quads, the
    (17,10) pocket precedent), and every UV by language walk: sand run columns hash-
    pick P/Q per column (the sand_rebuild-proven freedom), sand caps via
    :func:`emit_sand_cap`, foam run stamps + BL caps via :func:`emit_foam_cap`
    (THE SLOT LAW: BL is the mint default -- the universal fade).

    RUNG 2a -- the FREE-FOOTPRINT mint, landward (``land``): the interior LAND CHAIN is
    synthesized too. Each interior L vert pushes ``land * sin^2(pi t)`` landward along
    its own cross-shore ray (cap ends stay pinned -- they weld the flanking wall/grass)
    and CONFORMS to the berm surface; the berm is CLIPPED at the new chain (the
    beach_slide landward machinery: convex strip clip in pure real bytes, merged-loop
    re-triangulation, canonical float snaps) and the widened band takes the vacated
    strip. The band's land edge SUBDIVIDES at every genuine clip crossing so both sides
    carry identical verts (THE T-VERTEX LAW). Lawful on any painted berm -- clipping
    transports real bytes, only fills need a tile language (the baked-terrain law).

    Gates: the ribbon width envelope per column, the band slope gate, the swash
    envelope, the T-VERTEX gate against the pinned interfaces, per-tri language
    re-decode, and the ASSEMBLY BOUNDARY gate -- the emitted union's outer boundary
    must equal the dropped assembly's exactly (every outer edge is pinned, so any
    mismatch is a synthesis crack); with ``land`` also the slide's clip ledgers
    (partition / strip coverage / steep-face / object-anchor / drop-don't-drag).
    Rung-1 class: the block's single x-monotone column beach (the (7,17) class)."""
    foam_all = TR.world_tris(*donor, "beach1", disc=disc, lod=lod, game=game)
    terr = TR.world_tris(*donor, "terrain", disc=disc, lod=lod, game=game)
    if not foam_all:
        raise ValueError(f"donor {donor} has no beach1 mesh -- not a sandy shore")
    fam = _sand_band_family(terr, what=f"donor {donor}")
    if fam is None:
        raise ValueError(f"donor {donor} has no sand band")
    sand = [t3 for t3 in terr
            if decode_id(int(round(t3[0][3][0])))["topograph"] == fam["topo"]]
    other_k = {_pk(v[0]) for t3 in terr for v in t3
               if decode_id(int(round(t3[0][3][0])))["topograph"] != fam["topo"]}
    foam_k = {_pk(v[0]) for t3 in foam_all for v in t3}
    sea2_k = {_pk(v[0])
              for t3 in TR.world_tris(*donor, "sea2", disc=disc, lod=lod, game=game)
              for v in t3}
    family = _foam_family(foam_all)
    if family is None:
        raise ValueError(f"donor {donor}: no lawful foam run family decodes")

    # --- chain acquisition (whole band, caps in scope) ---
    sand_verts = {}
    for t3 in sand:
        for v in t3:
            sand_verts.setdefault(_pk(v[0]), v[0])
    # the end SL pinch verts weld to terrain too -- foam-welded wins (they are S ends)
    L = sorted((p for k, p in sand_verts.items()
                if k in other_k and k not in foam_k), key=lambda p: p[0])
    S_don = sorted((p for k, p in sand_verts.items() if k in foam_k),
                   key=lambda p: p[0])
    foam_verts = {}
    for t3 in foam_all:
        for v in t3:
            foam_verts.setdefault(_pk(v[0]), v[0])
    W = sorted((p for k, p in foam_verts.items()
                if k in sea2_k and k not in other_k), key=lambda p: p[0])
    n = len(L)
    if not (len(S_don) == n and len(W) == n and n >= 4):
        raise ValueError(f"the beach is not the rung-1 column class "
                         f"(L/S/W = {len(L)}/{len(S_don)}/{len(W)} verts)")
    if any(L[i][0] >= L[i + 1][0] for i in range(n - 1)):
        raise ValueError("the land chain is not x-monotone -- rung-1 class only")
    # donor pin constants (per-band lawful reads)
    run_pins = cap_pins = None
    for t3 in sand:
        d = _sand_tri_decode(t3, fam)
        if d is None:
            continue
        vs = sorted({round(v[2][1], 4) for v in t3})
        if d[0] == "run" and run_pins is None and len(vs) == 2:
            run_pins = vs
        if d[0] == "cap" and cap_pins is None and len(vs) == 2:
            cap_pins = vs
    if run_pins is None or cap_pins is None:
        raise ValueError("the donor band does not carry both run and cap pins")

    # --- the synthetic sand seam: width profile eased between the pinned ends ---
    def plan(p, q):
        return math.hypot(p[0] - q[0], p[2] - q[2])
    w_end = (plan(L[0], S_don[0]), plan(L[-1], S_don[-1]))
    S = [S_don[0]]
    for i in range(1, n - 1):
        t_ = i / (n - 1.0)
        base = w_end[0] + (w_end[1] - w_end[0]) * t_
        if width is not None:
            ease = math.sin(math.pi * t_) ** 2
            base = base + (float(width) - base) * ease
        d = plan(L[i], W[i])
        if d < 1e-6:
            raise ValueError(f"column {i}: land chain touches the waterline")
        f = base / d
        S.append((L[i][0] + (W[i][0] - L[i][0]) * f,
                  L[i][1] + (W[i][1] - L[i][1]) * f,
                  L[i][2] + (W[i][2] - L[i][2]) * f))
    S.append(S_don[-1])

    # --- rung 2a: the synthetic LAND chain + the berm clip ---
    L2, ter_drop, ter_emit, seg_cuts = list(L), [], [], {}
    if land is not None:
        if not (0.3 <= float(land) <= 4.0):
            raise ValueError("land takes 0.3 <= land <= 4.0 (the band width envelope "
                             "binds long before 4)")
        other = [t for t in terr
                 if decode_id(int(round(t[0][3][0])))["topograph"] != fam["topo"]]

        def surf_y(x, z):
            for t3 in other:
                if _pip_xz(x, z, t3):
                    (a, b, c) = (v[0] for v in t3)
                    d_ = (b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])
                    if abs(d_) < 1e-9:
                        continue
                    w1 = ((x - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (z - a[2])) / d_
                    w2 = ((b[0] - a[0]) * (z - a[2]) - (x - a[0]) * (b[2] - a[2])) / d_
                    return a[1] + w1 * (b[1] - a[1]) + w2 * (c[1] - a[1])
            return None
        for i in range(1, n - 1):
            d = float(land) * math.sin(math.pi * i / (n - 1.0)) ** 2
            if d < 0.02:
                continue
            m_ = plan(L[i], W[i])
            px = L[i][0] + d * (L[i][0] - W[i][0]) / m_
            pz = L[i][2] + d * (L[i][2] - W[i][2]) / m_
            yt = surf_y(px, pz)
            if yt is None:
                raise ValueError(f"column {i}: the widened land chain leaves the "
                                 f"painted terrain at ({px:.1f},{pz:.1f}) -- no berm "
                                 f"surface to conform to; reduce land")
            L2[i] = (px, yt, pz)

        # the consumed strip (old chain -> new chain), clipped as convex TRIANGLES
        # (an eased chain's column quads need not be convex; tris always are)
        from .mesh import _clip_edge, _poly_area2_xz
        strip_polys = []
        for i in range(n - 1):
            q = [(L[i][0], L[i][2]), (L[i + 1][0], L[i + 1][2]),
                 (L2[i + 1][0], L2[i + 1][2]), (L2[i][0], L2[i][2])]
            q = [p for j, p in enumerate(q)
                 if abs(p[0] - q[j - 1][0]) > 1e-9 or abs(p[1] - q[j - 1][1]) > 1e-9]
            if len(q) < 3:
                continue
            for tri2 in ([q[:3]] if len(q) == 3 else [q[:3], [q[0], q[2], q[3]]]):
                a2 = sum(tri2[j][0] * tri2[(j + 1) % 3][1]
                         - tri2[(j + 1) % 3][0] * tri2[j][1] for j in range(3))
                if abs(a2) <= 1e-9:
                    continue
                if a2 < 0:
                    tri2 = list(reversed(tri2))
                strip_polys.append((tri2, abs(a2) / 2.0))
        strip_area = sum(a for _, a in strip_polys)
        if strip_area <= 1e-6:
            raise ValueError("land displaces no interior column -- nothing to widen")

        def _clip_strip(t3):
            """(consumed_area, kept_pieces) of one berm tri vs the strip triangles --
            the beach_slide BSP inside/outside decomposition, verbatim bytes."""
            pieces, consumed = [list(t3)], 0.0
            for q, _a in strip_polys:
                nxt = []
                for piece in pieces:
                    inside = piece
                    for j in range(3):
                        inside = _clip_edge(inside, q[j], q[(j + 1) % 3], keep_left=True)
                        if len(inside) < 3:
                            break
                    ia = _poly_area2_xz(inside) / 2.0 if len(inside) >= 3 else 0.0
                    if ia <= 1e-6:
                        nxt.append(piece)
                        continue
                    consumed += ia
                    for j in range(3):
                        frag = piece
                        for jj in range(j):
                            frag = _clip_edge(frag, q[jj], q[(jj + 1) % 3],
                                              keep_left=True)
                            if len(frag) < 3:
                                break
                        if len(frag) < 3:
                            continue
                        frag = _clip_edge(frag, q[j], q[(j + 1) % 3], keep_left=False)
                        if len(frag) >= 3 and _poly_area2_xz(frag) > 2e-6:
                            nxt.append(frag)
                pieces = nxt
            return consumed, pieces
        for t3 in TR.world_tris(*donor, "object", disc=disc, lod=lod, game=game):
            if _clip_strip(t3)[0] > 1e-4:
                raise ValueError("the widened band reaches the block's prefab Object "
                                 "ground (the object-anchor law) -- reduce land")
        consumed_total, clipped = 0.0, []
        for t3 in other:
            consumed, pieces = _clip_strip(t3)
            if consumed <= 1e-6:
                continue
            plan2 = _poly_area2_xz(t3)
            if plan2 < 0.02 or TR._tri_area2_3d(list(t3)) > 2.0 * plan2:
                raise ValueError("the widened band cuts a STEEP berm face -- relief "
                                 "is a component, cut around it never through; "
                                 "reduce land")
            kept = sum(_poly_area2_xz(p) / 2.0 for p in pieces)
            if abs(plan2 / 2.0 - consumed - kept) > 1e-4 * max(1.0, plan2 / 2.0):
                raise ValueError("PARTITION LEDGER: a clipped berm tri's pieces do "
                                 "not sum to the original -- a clip defect")
            consumed_total += consumed
            ter_drop.append(list(t3))
            clipped.append((pieces, kept))
        if abs(consumed_total - strip_area) > max(0.01 * strip_area, 0.02):
            raise ValueError(f"STRIP COVERAGE: the widened band's strip "
                             f"({strip_area:.2f} sq-u) is only {consumed_total:.2f} "
                             f"painted berm -- the band would widen into a hole; "
                             f"reduce land")
        # no survivor may reference a vanished old chain vert (drop-don't-drag)
        moved_k = {_pk(L[i]) for i in range(1, n - 1) if L2[i] != L[i]}
        drop_ks = {_key_set(t) for t in ter_drop}
        for t3 in other:
            if any(_pk(v[0]) in moved_k for v in t3) and _key_set(t3) not in drop_ks:
                raise ValueError("a berm tri rides a moved land-chain vert but escapes "
                                 "the strip clip (an along-shore sliver) -- reduce "
                                 "land or shift the profile")
        # THE T-VERTEX LAW: re-triangulate each kept region from its MERGED loop, snap
        # every vert to canonical floats, then subdivide the band's land edge at every
        # genuine crossing so both sides carry IDENTICAL verts
        keep_k = {_pk(p) for p in L2} | {_pk(p) for p in L}
        for pieces, kept in clipped:
            tris_out = []
            for loop in _merge_loops(pieces):
                loop = _drop_collinear(loop, keep_k)
                tris_out += _ear_clip(loop)
            area_out = sum(_poly_area2_xz(t_) / 2.0 for t_ in tris_out)
            if abs(area_out - kept) > 1e-3 * max(1.0, kept):
                raise ValueError("LOOP LEDGER: a clipped berm tri's re-triangulated "
                                 "loops do not cover its kept area -- a merge defect")
            ter_emit += [_up_tri(t_) for t_ in tris_out]
        canon = {_pk(p, 6): tuple(p) for p in L2}

        def _snap(v):
            tgt = canon.setdefault(_pk(v[0], 6), tuple(v[0]))
            return v if tgt == tuple(v[0]) else (tgt, v[1], v[2], v[3])
        ter_emit = [[_snap(v) for v in t3] for t3 in ter_emit]
        for t3e in ter_emit:
            for v in t3e:
                p = v[0]
                for i in range(n - 1):
                    A, B = L2[i], L2[i + 1]
                    ex, ez = B[0] - A[0], B[2] - A[2]
                    el2 = ex * ex + ez * ez
                    if el2 < 1e-9:
                        continue
                    t_ = ((p[0] - A[0]) * ex + (p[2] - A[2]) * ez) / el2
                    if not (1e-4 < t_ < 1 - 1e-4):
                        continue
                    if abs(ex * (p[2] - A[2]) - ez * (p[0] - A[0])) \
                            > 1e-6 * max(1.0, math.hypot(ex, ez)):
                        continue
                    seg_cuts.setdefault(i, {})[round(t_, 9)] = p

    # --- gates: ribbon / slope / swash per column ---
    for i in range(n):
        bw = plan(L2[i], S[i])
        if not (MINT_BAND_W[0] - 0.05 <= bw <= MINT_BAND_W[1] + 0.05):
            raise ValueError(f"column {i}: band width {bw:.2f}u is outside the ribbon "
                             f"envelope {MINT_BAND_W} -- pick a lawful width")
        sl = abs(L2[i][1] - S[i][1]) / max(bw, 1e-6)
        if not (MINT_SLOPE[0] - 0.02 <= sl <= MINT_SLOPE[1] + 0.02):
            raise ValueError(f"column {i}: band slope {sl:.2f} rise/run is outside the "
                             f"envelope {MINT_SLOPE}")
        sw = plan(S[i], W[i])
        if not (MINT_SWASH[0] - 0.05 <= sw <= MINT_SWASH[1] + 0.05):
            raise ValueError(f"column {i}: swash width {sw:.2f}u is outside the "
                             f"envelope {MINT_SWASH} -- the width consumes the wash")

    # --- emission ---
    s_nrm = sand[0][0][1]
    s_id = tuple(sand[0][0][3])
    f_nrm = foam_all[0][0][1]
    f_id = tuple(foam_all[0][0][3])
    sand_emit, foam_emit = [], []
    # with ``land`` a column emits as a FAN from a seam corner: the land edge
    # L2[i]->L2[i+1] subdivides at the clip crossings (u affine along the edge,
    # v = the land pin) so band and clipped berm carry IDENTICAL verts
    for i in range(n - 1):
        lj, lf = (L2[i + 1], L2[i]) if i == 0 else (L2[i], L2[i + 1])
        sj, sf = (S[i + 1], S[i]) if i == 0 else (S[i], S[i + 1])
        wj, wf = (W[i + 1], W[i]) if i == 0 else (W[i], W[i + 1])
        diag_s = "sj-lf" if i % 2 else "lj-sf"
        diag_f = "wj-sf" if i % 2 else "sj-wf"
        cuts = sorted(seg_cuts.get(i, {}).items())
        if i in (0, n - 2):                # the end columns are the CAPS
            if land is None:
                sand_emit += emit_sand_cap(lj, sj, lf, sf, land_pin=cap_pins[0],
                                           seam_pin=cap_pins[1], diag=diag_s,
                                           nrm=s_nrm, idall=s_id, fam=fam)
            else:
                # the cap fan: same laws as emit_sand_cap (rect Q shifted per family,
                # junction at the split / free at the strip end, cap v pins), land
                # edge subdivided at the crossings
                uJ, uF = SAND_ULAT[1] + fam["du"], SAND_ULAT[2] + fam["du"]
                ua = uJ if lj is L2[i] else uF          # u at L2[i] / L2[i+1]
                ub = uF if lj is L2[i] else uJ
                la, lb = L2[i], L2[i + 1]
                el = plan(la, lb) or 1.0
                uv_of = {id(sj): (uJ, cap_pins[1]), id(sf): (uF, cap_pins[1])}

                def luv(p, ua=ua, ub=ub, la=la, el=el):
                    f = plan(la, p) / el
                    return (ua + f * (ub - ua), cap_pins[0])
                apex, closing = (sj, (sj, sf, lf)) if diag_s == "sj-lf" \
                    else (sf, (sf, sj, lj))
                pts = [la] + [p for _, p in cuts] + [lb]
                for p, q in zip(pts, pts[1:]):
                    sand_emit.append(_up_tri([(apex, s_nrm, uv_of[id(apex)], s_id),
                                              (p, s_nrm, luv(p), s_id),
                                              (q, s_nrm, luv(q), s_id)]))
                sand_emit.append(_up_tri([
                    (closing[0], s_nrm, uv_of[id(closing[0])], s_id),
                    (closing[1], s_nrm, uv_of[id(closing[1])], s_id),
                    (closing[2], s_nrm, luv(closing[2]), s_id)]))
            foam_emit += emit_foam_cap(sj, wj, sf, wf, slot="BL", family=family,
                                       diag=diag_f, nrm=f_nrm, idall=f_id)
        else:                              # run columns: fresh language walks
            rect = 0 if TR._h01(L2[i][0] + 2.9, L2[i][2] + 1.3) < 0.5 else 1
            u0, u1 = SAND_ULAT[rect] + fam["du"], SAND_ULAT[rect + 1] + fam["du"]
            if land is None:
                uv = {id(L2[i]): (u0, run_pins[0]), id(L2[i + 1]): (u1, run_pins[0]),
                      id(S[i]): (u0, run_pins[1]), id(S[i + 1]): (u1, run_pins[1])}
                split = ((S[i], L2[i + 1], L2[i]), (S[i], S[i + 1], L2[i + 1])) \
                    if i % 2 else ((L2[i], S[i + 1], S[i]),
                                   (L2[i], L2[i + 1], S[i + 1]))
                for tri_pts in split:
                    sand_emit.append(_up_tri([(p, s_nrm, uv[id(p)], s_id)
                                              for p in tri_pts]))
            else:
                la, lb = L2[i], L2[i + 1]
                el = plan(la, lb) or 1.0

                def luv(p, la=la, el=el, u0=u0, u1=u1):
                    f = plan(la, p) / el
                    return (u0 + f * (u1 - u0), run_pins[0])
                suv = {id(S[i]): (u0, run_pins[1]), id(S[i + 1]): (u1, run_pins[1])}
                apex, closing = (S[i], (S[i], S[i + 1], lb)) if i % 2 \
                    else (S[i + 1], (S[i + 1], S[i], la))
                pts = [la] + [p for _, p in cuts] + [lb]
                for p, q in zip(pts, pts[1:]):
                    sand_emit.append(_up_tri([(apex, s_nrm, suv[id(apex)], s_id),
                                              (p, s_nrm, luv(p), s_id),
                                              (q, s_nrm, luv(q), s_id)]))
                sand_emit.append(_up_tri([
                    (closing[0], s_nrm, suv[id(closing[0])], s_id),
                    (closing[1], s_nrm, suv[id(closing[1])], s_id),
                    (closing[2], s_nrm, luv(closing[2]), s_id)]))
            fam_bl = FOAM_FAMILIES[family]["BL"]
            fuv = {id(S[i]): (fam_bl[0], family[0]),
                   id(S[i + 1]): (0.5, family[0]),
                   id(W[i]): (fam_bl[0], family[1]),
                   id(W[i + 1]): (0.5, family[1])}
            fsplit = ((W[i], S[i + 1], S[i]), (W[i], W[i + 1], S[i + 1])) if i % 2 \
                else ((S[i], W[i + 1], W[i]), (S[i], S[i + 1], W[i + 1]))
            for tri_pts in fsplit:
                foam_emit.append(_up_tri([(p, f_nrm, fuv[id(p)], f_id)
                                          for p in tri_pts]))

    # --- self-check: every emitted tri decodes in its language ---
    for t3 in sand_emit:
        if _sand_tri_decode(t3, fam) is None:
            raise ValueError("a minted sand tri does not decode -- the emission "
                             "self-check failed")
    for t3 in foam_emit:
        us = [v[2][0] for v in t3]
        vs = [v[2][1] for v in t3]
        if not ((max(us) <= 0.502 and max(vs) <= 0.502)
                or (max(us) <= 0.502 and min(vs) >= 0.498)):
            raise ValueError("a minted foam tri is outside the run/BL windows -- the "
                             "emission self-check failed")

    # --- THE ASSEMBLY BOUNDARY gate: (a) every emitted once-edge must be a PINNED
    # edge (a once-edge on a synthetic vert = a crack inside the assembly), and
    # (b) the donor's pinned-vert boundary is preserved exactly. The donor's own
    # seam-subdivision asymmetries (the fan side subdividing an S edge the foam side
    # does not) involve non-pinned verts and are excluded by construction. ---
    def once_edges(tris):
        ec = defaultdict(int)
        for t3 in tris:
            for a in range(3):
                ec[frozenset((_pk(t3[a][0]), _pk(t3[(a + 1) % 3][0])))] += 1
        return {e for e, c in ec.items() if c == 1}
    if land is None:
        pinned = {_pk(p) for p in L} | {_pk(p) for p in W} | {_pk(S[0]), _pk(S[-1])}
        emit_once = once_edges(sand_emit + foam_emit)
        if any(not all(k in pinned for k in e) for e in emit_once):
            raise ValueError("ASSEMBLY BOUNDARY gate: a minted boundary edge sits on "
                             "a synthetic vert -- a crack inside the assembly")
        don_once = {e for e in once_edges(sand + foam_all)
                    if all(k in pinned for k in e)}
        if don_once != emit_once:
            raise ValueError("ASSEMBLY BOUNDARY gate: the minted assembly's pinned "
                             "outer boundary differs from the donor's -- the "
                             "interface moved")
    else:
        # the UNION crack gate: with the berm clipped, the touched union's outer
        # boundary (dropped originals vs emissions) must be preserved EXACTLY -- the
        # old L edges are interior to the drop union, the new L2 edges interior to
        # the emit union (band land edge == pieces' cut edge, vert for vert), so any
        # missing crossing or moved interface breaks the equality
        if once_edges(sand + foam_all + ter_drop) \
                != once_edges(sand_emit + foam_emit + ter_emit):
            raise ValueError("ASSEMBLY BOUNDARY gate: the widened assembly's outer "
                             "boundary differs from the dropped union's -- a weld or "
                             "T-junction defect at the berm clip")
    # T-vertices against the pinned neighbours (grass + wash near the assembly)
    keys = {k for t3 in sand + foam_all + ter_drop for v in t3 for k in (_pk(v[0]),)}
    drop_sets = {_key_set(t) for t in ter_drop}
    near = [(True, t3) for t3 in sand_emit + foam_emit + ter_emit]
    for t3 in terr:
        if any(_pk(v[0]) in keys for v in t3) and t3 not in sand \
                and _key_set(t3) not in drop_sets:
            near.append((False, t3))
    _tvertex_gate(near)

    return [TR.DropTris("terrain", sand + ter_drop),
            TR.EmitTris("terrain", sand_emit + ter_emit),
            TR.DropTris("beach1", foam_all), TR.EmitTris("beach1", foam_emit)]


def _apply_pre(tris_by_part, tweaks):
    """Apply a PRE tweak list (VertexDisplace / DropTris / EmitTris) to a loaded
    world-tri soup: the virgin mint composes AFTER earlier morphs (e.g. a bank
    reshape), so it must compute on the geometry those tweaks produce; the caller
    then deploys pre + mint together (tweaks ride the transplant in order)."""
    out = {p: [list(t3) for t3 in ts] for p, ts in tris_by_part.items()}
    for tw in tweaks:
        if isinstance(tw, TR.VertexDisplace):
            for p, ts in out.items():
                if tw.part is not None and p != tw.part:
                    continue
                for i, t3 in enumerate(ts):
                    if not any(tw._key(v[0]) in tw.moves for v in t3):
                        continue
                    nt = []
                    for (pos, nrm, uv, tan) in t3:
                        d = tw.moves.get(tw._key(pos))
                        if d is not None:
                            pos = (pos[0] + d[0], pos[1] + d[1], pos[2] + d[2])
                        nt.append((pos, nrm, uv, tan))
                    ts[i] = nt
        elif isinstance(tw, TR.DropTris):
            out[tw.part] = [t3 for t3 in out[tw.part]
                            if tw._key_set(t3) not in tw.keys]
        elif isinstance(tw, TR.EmitTris):
            out[tw.part] = out[tw.part] + [list(t3) for t3 in tw.tris]
        else:
            raise ValueError(f"pre tweak {type(tw).__name__} is not simulatable -- "
                             f"the mint composes after VertexDisplace/DropTris/"
                             f"EmitTris only")
    return out


def bank_lower(donor, center, *, radius=14.0, shore_slope=0.55, cap=2.2,
               along=None, disc: int = 1, lod: str = "0_1", game=None):
    """THE BANK RESHAPE -- the virgin mint's site-preparation verb: lower a
    mesa/cliff-top bank into a beach-capable profile (RESHAPE stock verts, never
    overlay). Every terrain vert within ``radius`` of ``center`` (plan) sinks to at
    most ``min(shore_slope * d_shore, cap)`` -- a gentle rise from the pinned
    waterline -- blended smoothly to zero effect at the radius (the untouched mesa
    keeps its height beyond, reading as a natural cove shoulder). Water-welded
    verts and block-frame verts never move; ground UVs/normals stay verbatim (the
    displacement semantics the cliff/beach bows proved), while touched topo-58
    WALL faces re-pin V per column under the lip anchor (crest keeps the painted
    lip row; the base crops the deepest strip rows at the column's own density;
    the V-IN-BAND gate polices the byte-derived band). Returns
    ``[DropTris, VertexDisplace, EmitTris]`` for the transplant/fuse tweak list
    (and the mint's ``pre=``)."""
    parts = ("terrain", "beach1", "sea2", "sea1", "sea3", "sea5", "sea4")
    tris = {p: TR.world_tris(*donor, p, disc=disc, lod=lod, game=game)
            for p in parts}
    water_k = {_pk(v[0]) for p in parts[1:] for t3 in tris[p] for v in t3}
    fx0, fx1 = 64.0 * donor[0], 64.0 * donor[0] + 64.0
    fz0, fz1 = -64.0 * donor[1] - 64.0, -64.0 * donor[1]
    shore = []
    tverts = {}
    for t3 in tris["terrain"]:
        for v in t3:
            k = _pk(v[0])
            tverts.setdefault(k, v[0])
            if k in water_k:
                shore.append(v[0])
    if not shore:
        raise ValueError(f"donor {donor} has no shoreline to profile the bank from")
    moves = {}
    for k, p in tverts.items():
        if k in water_k:
            continue
        if along is not None:
            # corridor mode: the falloff distance runs from the beach CHORD
            # segment, so the sink hugs the cove and the far rim keeps its
            # natural walls (a small islet has no room for a radial reach)
            (ax_, az_), (bx_, bz_) = along
            ex_, ez_ = bx_ - ax_, bz_ - az_
            el2_ = ex_ * ex_ + ez_ * ez_ or 1.0
            t_ = max(0.0, min(1.0, ((p[0] - ax_) * ex_
                                    + (p[2] - az_) * ez_) / el2_))
            r = math.hypot(p[0] - (ax_ + t_ * ex_), p[2] - (az_ + t_ * ez_))
        else:
            r = math.hypot(p[0] - center[0], p[2] - center[1])
        if r >= radius:
            continue
        if min(p[0] - fx0, fx1 - p[0], p[2] - fz0, fz1 - p[2]) < 1.5:
            continue
        d = min(math.hypot(p[0] - q[0], p[2] - q[2]) for q in shore)
        # plateau falloff: full effect inside, rolling off only over the outer
        # band (an islet is water-bounded -- the roll-off matters only where the
        # mesa continues past the radius)
        band = min(6.0, radius / 3.0)
        t = max(0.0, min(1.0, (radius - r) / band))
        w = t * t * (3.0 - 2.0 * t)
        tgt = min(shore_slope * d, cap)
        if p[1] > tgt + 1e-6:
            dy = (tgt - p[1]) * w
            if dy < -1e-4:
                moves[p] = (0.0, dy, 0.0)
    if not moves:
        raise ValueError("bank_lower moves nothing -- the bank already fits the "
                         "profile (or center/radius miss it)")
    keyed = {_pk(p) for p in moves}
    # a y-only sink cannot fold plan geometry and only FLATTENS 3D relief; the
    # remaining hazard is a plan-degenerate touched tri (a vertical wall face,
    # which a sink would z-fight) -- refuse those
    from .mesh import _poly_area2_xz
    for t3 in tris["terrain"]:
        if any(_pk(v[0]) in keyed for v in t3) and _poly_area2_xz(t3) < 1e-6:
            raise ValueError("bank_lower touches a plan-degenerate (vertical) tri "
                             "-- a wall face; shrink the radius off it")
    # CLIFF V NEVER DRAGS + THE LIP ANCHOR, per COLUMN (the corner-role
    # vocabulary): a real wall's V is a CORNER ASSIGNMENT, never a function of y
    # -- every crest vert carries the painted lip row and every base vert the
    # base row, whatever the face's height (byte-checked: crest 0.8926 / base
    # 0.9229 exact on every INTERIOR wall vert 0.9..5.5u tall across (10,18)/
    # (9,17)/(3,13); the strip never wraps. (7,17) and (16,17) hold the same
    # two-value law with a small documented frame-edge/waterline exception --
    # 7/105 and 4/153 verts respectively carry near-values 0.8936/0.9219 on
    # those edge verts, 2026-07-18 re-check). A sink therefore keeps every
    # crest v VERBATIM (the lip survives -- no hard/bevel alternation) and
    # re-pins each BASE vert along its own column at the column's original
    # density: v = crest_v + (base_v - crest_v) * h_new/h_old -- the face sheds
    # its DEEPEST rows (the free-base law), strata keep their real spacing (the
    # accepted round-2 read), and v stays inside the byte-derived band by
    # construction (h_new <= h_old). The map is per-VERT over the whole touched
    # wall group, so faces sharing a column vert agree exactly -- a per-FACE
    # affine cannot do this (the round-3/round-4 lesson: per-face shifts seam at
    # shared columns and push v outside the rock strip = white gashes).
    # Mechanically: drop the original face, emit it moved + re-pinned (drop
    # FIRST so the keys still match; emissions bypass the displacement).
    def _dy(pos):
        d = moves.get(tuple(pos))
        if d is None:
            k = _pk(pos)
            d = next((dd for pp, dd in moves.items() if _pk(pp) == k), None)
        return d[1] if d is not None else 0.0
    topo = lambda t3: decode_id(int(round(t3[0][3][0])))["topograph"]
    band = [t3 for t3 in tris["terrain"] if topo(t3) == 58]
    wall_drop, wall_emit = [], []
    if band and any(_pk(v[0]) in keyed for t3 in band for v in t3):
        # crest vs base per vert + column adjacency, decoded over the block's
        # WHOLE rock band (a touched face's side-edge tri may itself be
        # untouched -- the pairing must still find each base vert's true column
        # crest, or it grabs a diagonal partner and crops wrong). The strip
        # carries exactly two painted rows; no interior wall verts exist
        # (walls are one quad tall map-wide).
        pos_uv, kind_of = {}, {}
        adj_w = defaultdict(set)
        allv = [v[2][1] for t3 in band for v in t3]
        vmid = (min(allv) + max(allv)) / 2.0
        for t3 in band:
            ks = [_pk(v[0]) for v in t3]
            for (pos, nrm, uv, tan), k in zip(t3, ks):
                pos_uv.setdefault(k, (pos, uv))
                kind_of[k] = "crest" if uv[1] < vmid else "base"
            for i in range(3):
                adj_w[ks[i]].add(ks[(i + 1) % 3])
                adj_w[ks[(i + 1) % 3]].add(ks[i])
        crop = {}                # key -> (column crest v, frac); frac<1 = crop
        for k, kd_ in kind_of.items():
            if kd_ == "crest":
                continue                            # the lip row, verbatim
            pos, uv = pos_uv[k]
            crests = [c for c in adj_w[k] if kind_of.get(c) == "crest"]
            if not crests:
                continue                            # no column partner: verbatim
            c = min(crests, key=lambda c: (pos_uv[c][0][0] - pos[0]) ** 2
                    + (pos_uv[c][0][2] - pos[2]) ** 2)
            cpos, cuv = pos_uv[c]
            h_old = cpos[1] - pos[1]
            if h_old <= 1e-6:
                continue
            h_new = (cpos[1] + _dy(cpos)) - (pos[1] + _dy(pos))
            frac = max(0.0, min(1.0, h_new / h_old))
            if frac < 1.0:
                crop[k] = (cuv[1], frac)
        # re-emit every band face whose verts change (position OR v): a quad tri
        # holding a cropped base vert but not the moved crest would otherwise
        # survive verbatim and seam against its re-emitted neighbours. The crop
        # applies to each instance's OWN v (duplicate positions may carry
        # different uvs -- key-by-index law).
        for t3 in band:
            ks = [_pk(v[0]) for v in t3]
            if not any(k in keyed or k in crop for k in ks):
                continue
            nt = []
            for (pos, nrm, uv, tan), k in zip(t3, ks):
                if k in crop:
                    cv, frac = crop[k]
                    uv = (uv[0], cv + (uv[1] - cv) * frac)
                dy = _dy(pos)
                if dy:
                    pos = (pos[0], pos[1] + dy, pos[2])
                nt.append((pos, nrm, uv, tan))
            wall_drop.append(list(t3))
            wall_emit.append(nt)
        # THE V-IN-BAND GATE (permanent): every emitted wall v must sit inside
        # the band's byte-derived strip rows -- the round-4 gash class (v
        # escaping into neighbouring atlas rows) can never pass offline again
        v_lo, v_hi = min(allv) - 1e-4, max(allv) + 1e-4
        for nt in wall_emit:
            for (_, _, uv, _) in nt:
                if not (v_lo <= uv[1] <= v_hi):
                    raise ValueError(
                        f"V-IN-BAND GATE: an emitted wall v {uv[1]:.4f} escapes "
                        f"the rock strip's band [{v_lo + 1e-4:.4f},"
                        f"{v_hi - 1e-4:.4f}] -- off-strip texels read as white "
                        f"gashes/grass in-game")
    n_inst = sum(_pk(v[0]) in keyed
                 for p in parts for t3 in tris[p] for v in t3)
    n_inst -= sum(_pk(v[0]) in keyed for t3 in wall_drop for v in t3)
    out = []
    if wall_drop:
        out.append(TR.DropTris("terrain", wall_drop))
    out.append(TR.VertexDisplace(moves=moves, expected=n_inst))
    if wall_emit:
        out.append(TR.EmitTris("terrain", wall_emit))
    return out


def _blk_of(x, z):
    """The canonical block of a donor-world point: (floor(x/64), floor(-z/64))."""
    return (math.floor(x / 64.0), math.floor(-z / 64.0))


def parse_bank_lower_spec(spec: str) -> dict:
    """Parse the CLI ``--bank-lower "CX,CZ:RADIUS[:SLOPE[:CAP]][:along=AX,AZ/BX,BZ]"``
    into the ``build_shore_tweaks(bank=...)`` dict (the fuse layout's
    ``[placement.bank_lower]`` shape). Tail segments are positional floats
    (radius, shore_slope, cap) unless ``name=``-prefixed."""
    parts = [s.strip() for s in spec.strip().split(":")]
    if len(parts) < 2 or not parts[0]:
        raise ValueError("--bank-lower needs at least CX,CZ:RADIUS")
    out = {"center": [float(v) for v in parts[0].split(",")]}
    pos_keys = ["radius", "shore_slope", "cap"]
    for seg in parts[1:]:
        if not seg:
            continue
        if "=" in seg:
            name, _, val = seg.partition("=")
            if name.strip() != "along":
                raise ValueError(f"--bank-lower: unknown named segment '{name}'")
            a, _, b = val.partition("/")
            out["along"] = [[float(v) for v in a.split(",")],
                            [float(v) for v in b.split(",")]]
        else:
            if not pos_keys:
                raise ValueError("--bank-lower: too many positional segments")
            out[pos_keys.pop(0)] = float(seg)
    if "radius" not in out:
        raise ValueError("--bank-lower needs at least CX,CZ:RADIUS")
    return out


def parse_virgin_mint_spec(spec: str) -> dict:
    """Parse the CLI ``--virgin-mint
    "X0,Z0:X1,Z1[:WIDTH[:SWASH]][:pins=PX,PY][:wash=R]"`` into the
    ``build_shore_tweaks(mint=...)`` dict (the fuse layout's
    ``[placement.virgin_mint]`` shape). ``wash=R`` = the wash-apron reach:
    sea3/sea5 within R of the waterline re-band to wash (default 4.0; real
    beaches keep a much wider pure-wash apron -- the (16,5) A/B measured 13u+,
    and a too-short reach reads as a squared deep-band tile against the foam)."""
    parts = [s.strip() for s in spec.strip().split(":")]
    if len(parts) < 2:
        raise ValueError("--virgin-mint needs at least X0,Z0:X1,Z1")
    out = {"start": [float(v) for v in parts[0].split(",")],
           "end": [float(v) for v in parts[1].split(",")]}
    pos_keys = ["width", "swash"]
    for seg in parts[2:]:
        if not seg:
            continue
        if "=" in seg:
            name, _, val = seg.partition("=")
            if name.strip() == "pins":
                out["pins_from"] = [int(v) for v in val.split(",")]
            elif name.strip() == "wash":
                out["wash_reach"] = float(val)
            else:
                raise ValueError(f"--virgin-mint: unknown named segment '{name}'")
        else:
            if not pos_keys:
                raise ValueError("--virgin-mint: too many positional segments")
            out[pos_keys.pop(0)] = float(seg)
    return out


def build_shore_tweaks(donor, size=(1, 1), *, bank=None, mint=None,
                       disc: int = 1, lod: str = "0_1", game=None):
    """The PRODUCTIZED island-B pattern -- an optional :func:`bank_lower` plus an
    optional :func:`virgin_mint` riding ONE placement, the shared core of the
    ``world-transplant --bank-lower/--virgin-mint`` and ``world-fuse``
    ``[placement.bank_lower]``/``[placement.virgin_mint]`` paths. The mint
    composes on the bank via ``pre=`` (the composition rule: reconciliation
    mutates the SAME list, so exactly the returned tweaks must ride the
    deploy). Each verb's tweak BLOCK is derived from its own spec coords (the
    canonical ``floor(x/64), floor(-z/64)`` triple) and must sit inside the
    placement region ``donor+size`` -- coords in a foreign block refuse
    actionably. ``bank``/``mint`` are plain dicts:

    * bank: ``center=[x,z]`` (required), ``radius``, ``shore_slope``, ``cap``,
      ``along=[[ax,az],[bx,bz]]`` (the corridor mode).
    * mint: ``start=[x,z]``/``end=[x,z]`` (required), ``width``, ``swash``,
      ``wash_reach``, ``pins_from=[bx,by]`` (a beach-bearing reference block --
      REQUIRED when the mint block itself carries no beach).

    Returns ``(tweaks, notes)`` like :func:`transplant.build_grow_tweaks`."""
    (dx, dy) = (int(donor[0]), int(donor[1]))
    (snx, sny) = (int(size[0]), int(size[1]))

    def gate_blk(blk, what):
        if not (dx <= blk[0] < dx + snx and dy <= blk[1] < dy + sny):
            raise ValueError(
                f"{what} coords land in block {blk}, outside the placement "
                f"region {(dx, dy)}+{snx}x{sny} -- shore tweak coords are "
                f"donor-WORLD coords inside the carried region")
        return blk

    tweaks, notes = [], []
    pre = ()
    if bank is not None:
        if "center" not in bank:
            raise ValueError("bank_lower needs 'center' = [x, z]")
        cx, cz = (float(v) for v in bank["center"])
        blk = gate_blk(_blk_of(cx, cz), "bank_lower center")
        along = bank.get("along")
        if along is not None:
            along = (tuple(float(v) for v in along[0]),
                     tuple(float(v) for v in along[1]))
        pre = bank_lower(blk, (cx, cz),
                         radius=float(bank.get("radius", 14.0)),
                         shore_slope=float(bank.get("shore_slope", 0.55)),
                         cap=float(bank.get("cap", 2.2)),
                         along=along, disc=disc, lod=lod, game=game)
        tweaks += list(pre)
        notes.append(f"bank_lower @ block {blk}"
                     + (" (corridor)" if along is not None else " (radial)"))
    if mint is not None:
        for req in ("start", "end"):
            if req not in mint:
                raise ValueError(f"virgin_mint needs '{req}' = [x, z]")
        p0 = tuple(float(v) for v in mint["start"])
        p1 = tuple(float(v) for v in mint["end"])
        blk = gate_blk(_blk_of(*p0), "virgin_mint start")
        gate_blk(_blk_of(*p1), "virgin_mint end")
        pins = mint.get("pins_from")
        if pins is not None:
            pins = (int(pins[0]), int(pins[1]))
        wr = mint.get("wash_reach")                # None = the proven defaults
        tw = virgin_mint(blk, p0, p1,              # (deep 4.0 / shelf off)
                         width=float(mint.get("width", 2.4)),
                         swash=float(mint.get("swash", 4.6)),
                         wash_reach=None if wr is None else float(wr),
                         pre=pre, pins_from=pins,
                         disc=disc, lod=lod, game=game)
        tweaks += list(tw)
        notes.append(f"virgin_mint @ block {blk}"
                     + (f" (pins from {pins})" if pins else ""))
    return tweaks, notes


#: THE VIRGIN-MINT ENVELOPES (rung 3, 2026-07-11). Column widths: the map-wide foam
#: run-column census (608 constant-v run edges over all 40 beach blocks: 0.92..6.27u,
#: median 4.01 -- short columns are real grammar). Slope: MINT_SLOPE's ceiling widened
#: to the (9,17) beach's own cap column (0.66 rise/run); PINNED-real cap ends bypass
#: the synth envelopes entirely (transported real geometry is lawful by construction).
#: Separation: THE RUNG-2 WINDOW STUDY's grass-tongue law (min real inter-beach
#: separation 4.06u, the (3,12) pair) -- judged vert-to-segment BOTH ways.
VIRGIN_COL = (0.9, 6.3)
VIRGIN_SLOPE = (0.097, 0.68)
BEACH_SEP = 4.06
#: the chain-height priors (the rung-2 window study, (7,17) real chains)
S_MID_Y = 0.75
W_Y = 0.195


def virgin_mint(donor, start, end, *, width=2.4, swash=4.6, pre=(),
                pins_from=None, wash_reach=None, disc: int = 1,
                lod: str = "0_1", game=None):
    """BEACH-MINT rung 3 -- THE VIRGIN-SHORE MINT: author a NEW beach on a bare grass
    coast, no donor beach to pin to. ``start``/``end`` are world ``(x, z)`` anchors for
    the two cap pinch points on the shoreline (snapped to a real shore vert within
    0.6u, else inserted on the shore edge). Everything else is synthesized from the
    window's grass edge and gated:

    * the chains: S rides the real shoreline (plan) with the prior height profile
      (S ends = the real pinch verts, mid eased to ~0.75); L pushes landward onto the
      berm (``width`` target, conformed to the painted surface, slope-gated; a cap
      end pins to the flanking coast's real terminal crease vert when one exists --
      the real beach-end grammar); W pushes seaward (``swash`` target) into the wash,
      snapping to a real multi-band convergence vert when one is in reach (the ring
      weld) and otherwise auto-tilting inward until THE GRASS-TONGUE LAW clears.
    * the berm CLIPS at the assembly footprint (the rung-2a machinery: convex-tri BSP
      in real bytes, partition/coverage/steep-face/object-anchor ledgers, merged-loop
      re-triangulation, canonical snaps, land-edge fan subdivision).
    * touched WATER tiles drop whole and their outside fragments re-emit with
      clip-lerped uvs (exact affine continuation -- ``_clip_edge`` lerps the full
      vertex tuple), boundary verts lifted onto the new waterline.
    * sand + foam emit by the proven language walks (run stamps, P/Q hash picks, BL
      cap fades), fan-subdividing any boundary edge a fragment vert lands on
      (THE T-VERTEX LAW).
    * the ring re-bands where the mint leaves sea3 fronting wash ({2,3} is
      off-language): sea3 quads flip to sea1 by corner-role assignment (THE
      DEFORMED-TILE RECT LAW -- conforming quads included, the band_convert emitter)
      and affected strip neighbours re-emit under their new deep-edge-sets.
    * master gates: the UNION CRACK GATE (once-edges of everything dropped == of
      everything emitted), the T-VERTEX gate over the touched neighbourhood, the
      lattice adjacency law, the shade-agreement scan, per-tri language re-decodes,
      the wash-width march, and the separation law against every existing beach."""
    from .mesh import _clip_edge, _poly_area2_xz

    parts = ("terrain", "object", "beach1", "sea2", "sea1", "sea3", "sea5", "sea4")
    water_parts = ("sea2", "sea1", "sea3", "sea5", "sea4")
    tris = {p: TR.world_tris(*donor, p, disc=disc, lod=lod, game=game) for p in parts}
    if pre:
        tris = _apply_pre(tris, pre)
    terr = tris["terrain"]
    foam_all = tris["beach1"]

    def topo(t3):
        return decode_id(int(round(t3[0][3][0])))["topograph"]
    # the language pins (foam family + sand v-pins + the SAND FAMILY) come from the
    # block's own beach, or -- on a beach-less block -- byte-read from a reference
    # block via ``pins_from`` (the sand/foam atlas is the ONE world texture; the
    # family follows the pins: a desert reference mints topo-32 desert sand)
    if pins_from is not None:
        pin_terr = TR.world_tris(*pins_from, "terrain", disc=disc, lod=lod,
                                 game=game)
        pin_foam = TR.world_tris(*pins_from, "beach1", disc=disc, lod=lod,
                                 game=game)
    else:
        pin_terr, pin_foam = terr, foam_all
    fam = _sand_band_family(pin_terr, what=f"the pins block") or _SAND_GRASS
    sand = [t3 for t3 in terr if topo(t3) == fam["topo"]]
    other = [t3 for t3 in terr if topo(t3) != fam["topo"]]
    pin_sand = [t3 for t3 in pin_terr if topo(t3) == fam["topo"]]
    if not pin_foam:
        raise ValueError(f"donor {donor} carries no beach1 -- pass pins_from=a "
                         f"beach block to mint on a beach-less coast")
    if not pin_sand:
        raise ValueError(f"no sand band to read the mint pins from -- pass "
                         f"pins_from=a beach block")
    family = _foam_family(pin_foam)
    if family is None:
        raise ValueError("no lawful foam run family decodes in the pins block")
    run_pins = cap_pins = None
    for t3 in pin_sand:
        d = _sand_tri_decode(t3, fam)
        if d is None:
            continue
        vs = sorted({round(v[2][1], 4) for v in t3})
        if d[0] == "run" and run_pins is None and len(vs) == 2:
            run_pins = vs
        if d[0] == "cap" and cap_pins is None and len(vs) == 2:
            cap_pins = vs
    if run_pins is None or cap_pins is None:
        raise ValueError("the pins block's sand carries no run+cap pins")

    # --- the virgin shoreline graph: terrain boundary edges welded to open water ---
    water_of_k = defaultdict(set)
    wpos = {}
    for p in water_parts:
        for t3 in tris[p]:
            for v in t3:
                water_of_k[_pk(v[0])].add(p)
                wpos.setdefault(_pk(v[0]), v[0])
    foam_k = {_pk(v[0]) for t3 in foam_all for v in t3}
    e_count = defaultdict(int)
    pos_of = {}
    for t3 in terr:
        ps = [v[0] for v in t3]
        for v in t3:
            pos_of.setdefault(_pk(v[0]), v[0])
        for i in range(3):
            e_count[frozenset((_pk(ps[i]), _pk(ps[(i + 1) % 3])))] += 1
    shore_adj = defaultdict(set)
    for e, c in e_count.items():
        if c != 1 or len(e) != 2:
            continue
        a, b = tuple(e)
        if a in water_of_k and b in water_of_k:
            shore_adj[a].add(b)
            shore_adj[b].add(a)
    if not shore_adj:
        raise ValueError(f"donor {donor} has no shoreline (terrain boundary welded "
                         f"to water)")

    def _host(anchor):
        """-> (position, snapped_key | None, host_edge | None) for a pinch anchor."""
        ax, az = float(anchor[0]), float(anchor[1])
        bk = min(shore_adj, key=lambda k: (pos_of[k][0] - ax) ** 2
                 + (pos_of[k][2] - az) ** 2)
        bp = pos_of[bk]
        if math.hypot(bp[0] - ax, bp[2] - az) <= 0.6:
            return bp, bk, None
        best = None
        for a in shore_adj:
            for b in shore_adj[a]:
                pa, pb = pos_of[a], pos_of[b]
                ex, ez = pb[0] - pa[0], pb[2] - pa[2]
                el2 = ex * ex + ez * ez or 1.0
                t = max(0.0, min(1.0, ((ax - pa[0]) * ex + (az - pa[2]) * ez) / el2))
                qx, qz = pa[0] + t * ex, pa[2] + t * ez
                d2 = (ax - qx) ** 2 + (az - qz) ** 2
                if best is None or d2 < best[0]:
                    best = (d2, (a, b), t)
        if best is None or best[0] > 1.0:
            raise ValueError(f"anchor {tuple(anchor)} is off the shoreline -- pick a "
                             f"point on the coast")
        (a, b), t = best[1], best[2]
        pa, pb = pos_of[a], pos_of[b]
        return ((pa[0] + t * (pb[0] - pa[0]), pa[1] + t * (pb[1] - pa[1]),
                 pa[2] + t * (pb[2] - pa[2])), None, (a, b))

    posA, keyA, edgeA = _host(start)
    posB, keyB, edgeB = _host(end)

    # BFS the shoreline between the two pinch hosts
    fromA = {keyA} if keyA else set(edgeA)
    fromB = {keyB} if keyB else set(edgeB)
    prev = {k: None for k in fromA}
    queue = list(fromA)
    hit = None
    while queue and hit is None:
        k = queue.pop(0)
        if k in fromB:
            hit = k
            break
        for nk in shore_adj[k]:
            if nk not in prev:
                prev[nk] = k
                queue.append(nk)
    if hit is None:
        raise ValueError("start and end do not lie on one connected shoreline")
    path = [hit]
    while prev[path[-1]] is not None:
        path.append(prev[path[-1]])
    path.reverse()                                  # A-side ... B-side keys
    if edgeA is not None and len(path) > 1 and path[0] not in edgeA:
        path.insert(0, next(k for k in edgeA if k in shore_adj[path[0]]))
    S_poly = [posA] + [pos_of[k] for k in path
                       if _pk(posA) != k and _pk(posB) != k] + [posB]
    # drop path verts that sit outside the pinch span (behind an inserted pinch)
    def _along(p, a, b):
        ex, ez = b[0] - a[0], b[2] - a[2]
        return ((p[0] - a[0]) * ex + (p[2] - a[2]) * ez) / (ex * ex + ez * ez or 1.0)
    S_poly = [S_poly[0]] + [p for p in S_poly[1:-1]
                            if 0.02 < _along(p, posA, posB) < 0.98] + [S_poly[-1]]
    for p in S_poly[1:-1]:
        front = water_of_k.get(_pk(p), set())
        if not front <= {"sea1", "sea2", "sea3", "sea5"}:
            raise ValueError(f"shore vert ({p[0]:.1f},{p[2]:.1f}) fronts "
                             f"{sorted(front)} -- a sea4 plunge coast has no "
                             f"lawful ladder (sea5 interposition is out of scope)")
        if _pk(p) in foam_k:
            raise ValueError(f"shore vert ({p[0]:.1f},{p[2]:.1f}) welds an existing "
                             f"beach -- not a virgin window")

    # --- columns: equal-arc resample inside the real column-width envelope ---
    arcs = [0.0]
    for p, q in zip(S_poly, S_poly[1:]):
        arcs.append(arcs[-1] + math.hypot(q[0] - p[0], q[2] - p[2]))
    acc = arcs[-1]
    ncol = max(3, int(round(acc / 3.5)))
    while ncol > 3 and acc / ncol < VIRGIN_COL[0] + 0.15:
        ncol -= 1
    if not (VIRGIN_COL[0] <= acc / ncol <= VIRGIN_COL[1]):
        raise ValueError(f"column width {acc / ncol:.2f}u (arc {acc:.1f}u / {ncol} "
                         f"columns) is outside the real along-shore envelope "
                         f"{VIRGIN_COL} -- move the anchors")
    n = ncol + 1

    def at_arc(s):
        for i in range(len(arcs) - 1):
            if s <= arcs[i + 1] or i == len(arcs) - 2:
                t = (s - arcs[i]) / max(arcs[i + 1] - arcs[i], 1e-9)
                a, b = S_poly[i], S_poly[i + 1]
                return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]),
                        a[2] + t * (b[2] - a[2]))
    S_base = [S_poly[0]] + [at_arc(acc * i / ncol) for i in range(1, ncol)] \
        + [S_poly[-1]]

    def surf_y(x, z):
        for t3 in other:
            if _pip_xz(x, z, t3):
                (a, b, c) = (v[0] for v in t3)
                d_ = (b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])
                if abs(d_) < 1e-9:
                    continue
                w1 = ((x - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (z - a[2])) / d_
                w2 = ((b[0] - a[0]) * (z - a[2]) - (x - a[0]) * (b[2] - a[2])) / d_
                return a[1] + w1 * (b[1] - a[1]) + w2 * (c[1] - a[1])
        return None

    # per-column seaward normal; the SIGN comes from the painted-terrain side (a
    # narrow peninsula has water both ways -- a water-mass mean can flip it)
    normals = []
    for i in range(n):
        a = S_base[max(i - 1, 0)]
        b = S_base[min(i + 1, n - 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        tl = math.hypot(tx, tz) or 1.0
        nx, nz = tz / tl, -tx / tl
        p = S_base[i]
        sign = None
        for off in (0.6, 1.2):
            land_pos = surf_y(p[0] - nx * off, p[2] - nz * off) is not None
            land_neg = surf_y(p[0] + nx * off, p[2] + nz * off) is not None
            if land_pos != land_neg:
                sign = 1.0 if land_pos else -1.0
                break
        if sign is None:
            raise ValueError(f"column {i}: cannot orient the shore normal at "
                             f"({p[0]:.1f},{p[2]:.1f}) -- terrain on both sides?")
        normals.append((nx * sign, nz * sign))

    def plan(p, q):
        return math.hypot(p[0] - q[0], p[2] - q[2])

    # THE GRASS-TONGUE LAW helpers: the other beaches' assembly verts + edges
    their_v = {}
    for t3 in list(foam_all) + list(sand):
        for v in t3:
            their_v.setdefault(_pk(v[0]), v[0])
    their_e = []
    for t3 in list(foam_all) + list(sand):
        ps = [v[0] for v in t3]
        for i in range(3):
            their_e.append((ps[i], ps[(i + 1) % 3]))

    def _pt_seg(p, a, b):
        ex, ez = b[0] - a[0], b[2] - a[2]
        el2 = ex * ex + ez * ez or 1.0
        t = max(0.0, min(1.0, ((p[0] - a[0]) * ex + (p[2] - a[2]) * ez) / el2))
        return math.hypot(p[0] - (a[0] + t * ex), p[2] - (a[2] + t * ez))

    def _sep(a, b=None):
        """Min plan distance from vert ``a`` (or segment ``a-b``) to the other
        beaches' assemblies (verts + edges, both ways)."""
        best = min((_pt_seg(a, qa, qb) for qa, qb in their_e), default=9e9)
        best = min(best, min((plan(a, q) for q in their_v.values()), default=9e9))
        if b is not None:
            best = min(best, _sep(b))
            for q in their_v.values():
                best = min(best, _pt_seg(q, a, b))
        return best

    # --- cap L ends: pin the flanking coast's real terminal crease when it exists ---
    tadj = defaultdict(set)
    for t3 in terr:
        ps = [v[0] for v in t3]
        for i in range(3):
            a, b = _pk(ps[i]), _pk(ps[(i + 1) % 3])
            tadj[a].add(b)
            tadj[b].add(a)

    def _cap_L(end):
        pinch = S_base[0] if end == 0 else S_base[-1]
        key = keyA if end == 0 else keyB
        nx, nz = normals[0 if end == 0 else n - 1]
        if key is not None:
            best = None
            for nk in tadj.get(key, ()):
                q = pos_of.get(nk)
                if q is None or nk in water_of_k or q[1] < 0.6:
                    continue
                dx, dz = q[0] - pinch[0], q[2] - pinch[2]
                d = math.hypot(dx, dz)
                if not (0.4 <= d <= 6.6):
                    continue
                if (dx * nx + dz * nz) / d > -0.2:
                    continue
                if best is None or d < best[0]:
                    best = (d, q)
            if best is not None:
                return best[1], True
        w = max(width, MINT_BAND_W[0])
        while w <= MINT_BAND_W[1]:
            px, pz = pinch[0] - nx * w, pinch[2] - nz * w
            y = surf_y(px, pz)
            if y is None:
                break
            if (y - pinch[1]) / w <= VIRGIN_SLOPE[1] - 0.02:
                return (px, y, pz), False
            w += 0.2
        raise ValueError(f"cap end {end}: no lawful band width -- the berm is too "
                         f"steep for the slope envelope; move the anchor")

    capL = (_cap_L(0), _cap_L(1))

    # --- cap W ends: snap to a real multi-band convergence vert, else synthesize
    # with an inward tilt until the grass-tongue law clears (real cap edges tilt) ---
    def _cap_W(end):
        pinch = S_base[0] if end == 0 else S_base[-1]
        i0 = 0 if end == 0 else n - 1
        nx, nz = normals[i0]
        tgt = (pinch[0] + nx * swash, pinch[2] + nz * swash)
        best = None
        for k, ps in water_of_k.items():
            if len(ps) < 2 or k in foam_k:
                continue
            q = wpos[k]
            d = math.hypot(q[0] - tgt[0], q[2] - tgt[1])
            if d <= 1.2 and (best is None or d < best[0]):
                best = (d, q)
        if best is not None:
            return best[1], True
        j = S_base[min(i0 + 1, n - 1)] if end == 0 else S_base[max(i0 - 1, 0)]
        tl = plan(pinch, j) or 1.0
        tx, tz = (j[0] - pinch[0]) / tl, (j[2] - pinch[2]) / tl   # inward tangent
        for sw in (max(MINT_SWASH[0] + 0.2, swash - 1.1), swash):
            for tilt in [0.25 * k2 for k2 in range(11)]:
                cx_ = pinch[0] + nx * sw + tx * tilt
                cz_ = pinch[2] + nz * sw + tz * tilt
                cand = (cx_, W_Y, cz_)
                if _sep(cand, pinch) >= BEACH_SEP:
                    return cand, False
        raise ValueError(f"cap end {end}: no W end clears the grass-tongue law "
                         f"({BEACH_SEP}u) -- the window is too close to a beach")

    capW = (_cap_W(0), _cap_W(1))

    # --- the chains ---
    w_end = (plan(capL[0][0], S_base[0]), plan(capL[1][0], S_base[-1]))
    sw_end = (plan(capW[0][0], S_base[0]), plan(capW[1][0], S_base[-1]))
    S, L, W = [], [], []
    for i in range(n):
        t = i / (n - 1.0)
        base = S_base[i]
        if i in (0, n - 1):
            S.append(base)
        else:
            yl = S_base[0][1] + (S_base[-1][1] - S_base[0][1]) * t
            S.append((base[0], yl + (S_MID_Y - yl) * math.sin(math.pi * t) ** 2,
                      base[2]))
    for i in range(n):
        t = i / (n - 1.0)
        nx, nz = normals[i]
        if i == 0:
            L.append(capL[0][0])
            W.append(capW[0][0])
            continue
        if i == n - 1:
            L.append(capL[1][0])
            W.append(capW[1][0])
            continue
        bw = w_end[0] + (w_end[1] - w_end[0]) * t
        bw = bw + (float(width) - bw) * math.sin(math.pi * t) ** 2
        px, pz = S[i][0] - nx * bw, S[i][2] - nz * bw
        y = surf_y(px, pz)
        if y is None:
            raise ValueError(f"column {i}: the land chain leaves the painted berm at "
                             f"({px:.1f},{pz:.1f}) -- reduce width")
        L.append((px, y, pz))
        sw = sw_end[0] + (sw_end[1] - sw_end[0]) * t
        sw = sw + (float(swash) - sw) * math.sin(math.pi * t) ** 2
        W.append((S[i][0] + nx * sw, W_Y, S[i][2] + nz * sw))

    # --- chain gates ---
    for i in range(n):
        bw, sw = plan(L[i], S[i]), plan(S[i], W[i])
        pinned = (i == 0 and capL[0][1]) or (i == n - 1 and capL[1][1])
        if not pinned:
            if not (MINT_BAND_W[0] - 0.05 <= bw <= MINT_BAND_W[1] + 0.05):
                raise ValueError(f"column {i}: band width {bw:.2f}u is outside "
                                 f"{MINT_BAND_W}")
            sl = abs(L[i][1] - S[i][1]) / max(bw, 1e-6)
            if not (VIRGIN_SLOPE[0] - 0.02 <= sl <= VIRGIN_SLOPE[1] + 0.02):
                raise ValueError(f"column {i}: band slope {sl:.2f} is outside "
                                 f"{VIRGIN_SLOPE}")
        if not (MINT_SWASH[0] - 0.05 <= sw <= MINT_SWASH[1] + 0.05):
            raise ValueError(f"column {i}: swash width {sw:.2f}u is outside "
                             f"{MINT_SWASH}")
    for ch in (S, W):
        for i in range(n - 1):
            cw = plan(ch[i], ch[i + 1])
            if not (VIRGIN_COL[0] - 0.05 <= cw <= VIRGIN_COL[1] + 0.05):
                raise ValueError(f"column edge {i} spans {cw:.2f}u -- outside the "
                                 f"along-shore envelope {VIRGIN_COL}")
    # THE GRASS-TONGUE LAW over the whole assembly boundary
    bounds = [(L[i], L[i + 1]) for i in range(ncol)] \
        + [(W[i], W[i + 1]) for i in range(ncol)] \
        + [(L[0], S[0]), (S[0], W[0]), (L[-1], S[-1]), (S[-1], W[-1])]
    for a, b in bounds:
        d = _sep(a, b)
        if d < BEACH_SEP - 1e-6:
            raise ValueError(f"THE GRASS-TONGUE LAW: the minted assembly passes "
                             f"{d:.2f}u from an existing beach (< {BEACH_SEP}) near "
                             f"({a[0]:.1f},{a[2]:.1f}) -- move the anchors")

    import os
    if os.environ.get("FF9_VIRGIN_DEBUG"):
        for nm, ch in (("L", L), ("S", S), ("W", W)):
            print(f"[debug] {nm}: " + " ".join(
                f"({p[0]:.2f},{p[1]:.2f},{p[2]:.2f})" for p in ch))
    # --- the footprint (the rung-2a strip machinery, reflex-aware: a pinned real
    # crease-base pair can make a cap quad REFLEX at the corner -- only ONE diagonal
    # is interior; the wrong one spills the footprint into the flanking wall) ---
    strip_polys = []
    quad_diag = {}                       # (kind, i) -> 0 (q0-q2) | 1 (q1-q3)
    quad_forced = set()                  # reflex cap quads: only one diagonal valid

    def _tri_a2(tri2):
        return sum(tri2[j][0] * tri2[(j + 1) % 3][1]
                   - tri2[(j + 1) % 3][0] * tri2[j][1] for j in range(3))

    for i in range(ncol):
        for kind, quad in (("sand", (L[i], L[i + 1], S[i + 1], S[i])),
                           ("foam", (S[i], S[i + 1], W[i + 1], W[i]))):
            q = [(p[0], p[2]) for p in quad]
            q = [p for j, p in enumerate(q)
                 if abs(p[0] - q[j - 1][0]) > 1e-9 or abs(p[1] - q[j - 1][1]) > 1e-9]
            if len(q) < 3:
                continue
            if len(q) == 3:
                splits = {0: [q]}
            else:
                splits = {0: [q[:3], [q[0], q[2], q[3]]],
                          1: [[q[0], q[1], q[3]], [q[1], q[2], q[3]]]}
                for d in (0, 1):
                    a2s = [_tri_a2(t) for t in splits[d]]
                    if not all(abs(a) > 1e-9 for a in a2s) \
                            or (a2s[0] > 0) != (a2s[1] > 0):
                        del splits[d]
                if not splits:
                    raise ValueError(f"column {i}: the {kind} quad is degenerate")
            d = sorted(splits)[0]
            quad_diag[(kind, i)] = d if len(q) == 4 else 0
            if len(q) == 4 and len(splits) == 1:
                if i not in (0, ncol - 1):
                    raise ValueError(f"column {i}: a REFLEX interior {kind} quad -- "
                                     f"the chains fold; move the anchors")
                quad_forced.add((kind, i))
            for tri2 in splits[d]:
                a2 = _tri_a2(tri2)
                if a2 < 0:
                    tri2 = list(reversed(tri2))
                strip_polys.append((tri2, abs(a2) / 2.0))
    foot_area = sum(a for _, a in strip_polys)
    if foot_area <= 1e-6:
        raise ValueError("the assembly footprint is degenerate")

    # --- the exact footprint cut: the assembly is ONE simple polygon P; a touched
    # source tri loses tri INTERSECT P and keeps tri MINUS P, whose boundary = its
    # own out-of-P edge sub-segments + P's in-tri portions. Every intersection vert
    # is computed ONCE (per P-seg x unordered tri-edge), so neighbouring tris, the
    # fans, and the water zip weld bit-exact by construction -- no BSP extension
    # lines, no fragment-interface repair. ---
    fp = [tuple(p) for p in (L + [S[-1]] + list(reversed(W)) + [S[0]])]
    fp2 = [(p[0], p[2]) for p in fp]
    m_fp = len(fp)
    a2_fp = sum(fp2[j][0] * fp2[(j + 1) % m_fp][1]
                - fp2[(j + 1) % m_fp][0] * fp2[j][1] for j in range(m_fp))
    if a2_fp < 0:
        fp = list(reversed(fp))
        fp2 = list(reversed(fp2))
        a2_fp = -a2_fp
    foot_area = a2_fp / 2.0
    if foot_area <= 1e-6:
        raise ValueError("the assembly footprint is degenerate")

    def _in_fp(px, pz):
        return _in_poly(px, pz, fp2)

    def _fp_dist(px, pz):
        best = 9e9
        for j in range(m_fp):
            a, b = fp[j], fp[(j + 1) % m_fp]
            ex, ez = b[0] - a[0], b[2] - a[2]
            el2 = ex * ex + ez * ez or 1.0
            t = max(0.0, min(1.0, ((px - a[0]) * ex + (pz - a[2]) * ez) / el2))
            best = min(best, math.hypot(px - (a[0] + t * ex), pz - (a[2] + t * ez)))
        return best

    canon = {(round(p[0], 6), round(p[2], 6)): tuple(p) for p in L + S + W}
    xcache = {}

    def _xvert(a, b, si):
        """The canonical intersection vert of unordered tri edge (a, b) with fp
        segment ``si`` -- one float tuple everywhere it appears."""
        ka, kb = _pk(a), _pk(b)
        ek = (min(ka, kb), max(ka, kb), si)
        if ek in xcache:
            return xcache[ek]
        p0, p1 = (a, b) if ka <= kb else (b, a)
        r = _seg_x(p0, p1, fp[si], fp[(si + 1) % m_fp])
        t = r[0]
        pos = (p0[0] + t * (p1[0] - p0[0]), p0[1] + t * (p1[1] - p0[1]),
               p0[2] + t * (p1[2] - p0[2]))
        # an intersection vert within the weld-audit tolerance of a chain vert
        # ADOPTS it (both sides share this cache, so the near-miss sliver
        # collapses consistently everywhere -- the canonical-snap law)
        snap = canon.get((round(pos[0], 6), round(pos[2], 6)))
        if snap is None:
            for q in canon.values():
                if abs(q[0] - pos[0]) < 0.08 and abs(q[2] - pos[2]) < 0.08                         and math.hypot(q[0] - pos[0], q[2] - pos[2]) < 0.08:
                    snap = q
                    break
        if snap is None:
            # crossings also merge with EACH OTHER inside the tolerance (a
            # boundary line grazing a donor vert crosses its two edges at two
            # nearby points -- one shared vert, no sliver)
            for q in xcache.values():
                if abs(q[0] - pos[0]) < 0.08 and abs(q[2] - pos[2]) < 0.08                         and math.hypot(q[0] - pos[0], q[2] - pos[2]) < 0.08:
                    snap = q
                    break
        pos = snap if snap is not None else pos
        xcache[ek] = pos
        return pos

    def _seg_x(a, b, c, d):
        ex, ez = b[0] - a[0], b[2] - a[2]
        fx, fz = d[0] - c[0], d[2] - c[2]
        den = ex * fz - ez * fx
        if abs(den) < 1e-12:
            return None
        t = ((c[0] - a[0]) * fz - (c[2] - a[2]) * fx) / den
        u = ((a[0] - c[0]) * ez - (a[2] - c[2]) * ex) / -den
        if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
            return t, u
        return None

    def _touches(t3):
        ps = [v[0] for v in t3]
        for ei in range(3):
            a, b = ps[ei], ps[(ei + 1) % 3]
            for si in range(m_fp):
                r = _seg_x(a, b, fp[si], fp[(si + 1) % m_fp])
                if r and 1e-7 < r[0] < 1 - 1e-7 and 1e-7 < r[1] < 1 - 1e-7:
                    return True
        for v in t3:
            if _fp_dist(v[0][0], v[0][2]) > 1e-6 and _in_fp(v[0][0], v[0][2]):
                return True
        for q in fp:
            if _pip_xz(q[0], q[2], t3) \
                    and min(_pt_seg(q, ps[j], ps[(j + 1) % 3])
                            for j in range(3)) > 1e-6:
                return True
        return False

    def _bary(tt, px, pz):
        (a, b, c) = (v[0] for v in tt)
        d_ = (b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])
        w1 = ((px - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (pz - a[2])) / d_
        w2 = ((b[0] - a[0]) * (pz - a[2]) - (px - a[0]) * (b[2] - a[2])) / d_
        return 1.0 - w1 - w2, w1, w2

    def _cut_tri(t3):
        """(consumed_area, kept_tris | None) of one source tri vs the footprint."""
        if not _touches(t3):
            return 0.0, None
        a2t = sum(t3[j][0][0] * t3[(j + 1) % 3][0][2]
                  - t3[(j + 1) % 3][0][0] * t3[j][0][2] for j in range(3))
        tt = list(t3) if a2t > 0 else [t3[0], t3[2], t3[1]]
        ps = [v[0] for v in tt]
        tri_area = abs(a2t) / 2.0
        cxt = sum(p[0] for p in ps) / 3.0
        czt = sum(p[2] for p in ps) / 3.0
        vcache = {}

        def V(pos):
            k = _pk(pos)
            if k not in vcache:
                for v in tt:
                    if _pk(v[0]) == k:
                        vcache[k] = v
                        break
                else:
                    w0, w1, w2 = _bary(tt, pos[0], pos[2])
                    nrm = tuple(w0 * tt[0][1][j] + w1 * tt[1][1][j]
                                + w2 * tt[2][1][j] for j in range(3))
                    uv = tuple(w0 * tt[0][2][j] + w1 * tt[1][2][j]
                               + w2 * tt[2][2][j] for j in range(2))
                    vcache[k] = (tuple(pos), nrm, uv, tt[0][3])
            return vcache[k]

        edges_out = []
        for ei in range(3):
            a, b = ps[ei], ps[(ei + 1) % 3]
            hits = []
            for si in range(m_fp):
                r = _seg_x(a, b, fp[si], fp[(si + 1) % m_fp])
                if r is None or not (1e-9 < r[0] < 1 - 1e-9):
                    continue
                hits.append((r[0], _xvert(a, b, si)))
            hits.sort(key=lambda h: h[0])
            pts = [(0.0, a)] + hits + [(1.0, b)]
            for (t0, p0), (t1, p1) in zip(pts, pts[1:]):
                if t1 - t0 < 1e-9 or _pk(p0) == _pk(p1):
                    continue
                mx, mz = (p0[0] + p1[0]) / 2.0, (p0[2] + p1[2]) / 2.0
                dx, dz = cxt - mx, czt - mz
                dl = math.hypot(dx, dz) or 1.0
                if _in_fp(mx + dx / dl * 1e-3, mz + dz / dl * 1e-3):
                    continue                        # the consumed side
                edges_out.append((V(p0), V(p1)))
        for si in range(m_fp):
            fa, fb = fp[si], fp[(si + 1) % m_fp]
            hits = []
            for ei in range(3):
                a, b = ps[ei], ps[(ei + 1) % 3]
                r = _seg_x(a, b, fa, fb)
                if r is None or not (1e-9 < r[0] < 1 - 1e-9):
                    continue
                hits.append((r[1], _xvert(a, b, si)))
            pts = [(0.0, fa)] + sorted(hits, key=lambda h: h[0]) + [(1.0, fb)]
            for (u0, p0), (u1, p1) in zip(pts, pts[1:]):
                if u1 - u0 < 1e-9 or _pk(p0) == _pk(p1):
                    continue
                mx, mz = (p0[0] + p1[0]) / 2.0, (p0[2] + p1[2]) / 2.0
                w0, w1, w2 = _bary(tt, mx, mz)
                if min(w0, w1, w2) < 1e-7:
                    continue                        # outside / on this tri's edge
                edges_out.append((V(p1), V(p0)))    # kept region left of b->a
        nxt = {}
        for va, vb in edges_out:
            ka, kb = _pk(va[0]), _pk(vb[0])
            if ka == kb:
                continue
            if ka in nxt:
                raise ValueError("footprint cut: a non-manifold kept boundary "
                                 "(two out-edges at one vert) -- a degenerate "
                                 "crossing; nudge the anchors")
            nxt[ka] = (va, vb, kb)
        kept_tris = []
        seen = set()
        for start in list(nxt):
            if start in seen:
                continue
            loop, k = [], start
            ok = True
            while k in nxt and k not in seen:
                seen.add(k)
                va, vb, kb = nxt[k]
                loop.append(va)
                k = kb
            if k != start:
                ok = False
            if ok and len(loop) >= 3:
                kept_tris += _ear_clip(loop)
            elif not ok:
                raise ValueError("footprint cut: an open kept-boundary chain -- "
                                 "a degenerate crossing; nudge the anchors")
        kept_area = sum(_poly_area2_xz(t_) / 2.0 for t_ in kept_tris)
        if kept_area > tri_area + 1e-3:
            raise ValueError("footprint cut: kept exceeds the source tri")
        return tri_area - kept_area, kept_tris

    for t3 in tris["object"]:
        if _touches(t3):
            raise ValueError("the assembly reaches the block's prefab Object ground "
                             "(the object-anchor law) -- move the anchors")
    for name, tset in (("sand", sand), ("foam", foam_all)):
        for t3 in tset:
            if _touches(t3):
                raise ValueError(f"the assembly consumes an existing beach's {name} "
                                 f"-- the grass-tongue law should have refused")

    bsegs = [(L[i], L[i + 1], ("L", i)) for i in range(ncol)] \
        + [(W[i], W[i + 1], ("W", i)) for i in range(ncol)] \
        + [(L[0], S[0], ("TL", 0)), (S[0], W[0], ("TW", 0)),
           (L[n - 1], S[n - 1], ("TL", 1)), (S[n - 1], W[n - 1], ("TW", 1))]

    def _on_seg(p):
        for a, b, tag in bsegs:
            ex, ez = b[0] - a[0], b[2] - a[2]
            el2 = ex * ex + ez * ez
            if el2 < 1e-9:
                continue
            t = ((p[0] - a[0]) * ex + (p[2] - a[2]) * ez) / el2
            if not (1e-4 < t < 1 - 1e-4):
                continue
            if abs(ex * (p[2] - a[2]) - ez * (p[0] - a[0])) \
                    > 1e-6 * max(1.0, math.hypot(ex, ez)):
                continue
            return tag, t, (a[1] + t * (b[1] - a[1]))
        return None

    def _lift_v(v):
        """A water vert on a boundary segment conforms to the new waterline's
        height there (waterline tiles CONFORM to the coast)."""
        hit = _on_seg(v[0])
        if hit is None or abs(v[0][1] - hit[2]) < 1e-9:
            return v
        return ((v[0][0], hit[2], v[0][2]), v[1], v[2], v[3])

    # --- the berm cut (terrain) + the water cut ---
    ter_drop, ter_emit = [], []
    terr_consumed = 0.0
    for t3 in other:
        consumed, kept = _cut_tri(t3)
        if kept is None:
            continue
        plan2 = _poly_area2_xz(t3)
        # THE RELIEF LAW: never cut THROUGH a steep face (a kept fragment of one)
        # -- FULL consumption of a shore bank is replacement, the thing a beach IS
        if kept and (plan2 < 0.02 or TR._tri_area2_3d(list(t3)) > 2.0 * plan2):
            vs = " ".join(f"({v[0][0]:.2f},{v[0][1]:.2f},{v[0][2]:.2f})" for v in t3)
            raise ValueError(f"the assembly cuts THROUGH a STEEP berm face at {vs} "
                             f"-- relief is a component, cut around it never "
                             f"through; move the anchors or reduce width")
        terr_consumed += consumed
        ter_drop.append(list(t3))
        ter_emit += [_up_tri(t_) for t_ in kept]
    wat_drop = {p: [] for p in water_parts}
    wat_emit = {p: [] for p in water_parts}
    wat_consumed = 0.0
    mains_map = _mains_factory()

    def _to_wash(t_):
        """Re-band a deep tile (or fragment) to sea2 WASH: fresh per-cell mains uvs
        (the beach_rebuild conforming precedent -- position-evaluated), geometry/
        normals/IDALL verbatim (a band conversion is a uv+part edit)."""
        uvf = mains_map(_cell_of_tri(t_))
        return [(v[0], v[1], uvf(v[0][0], v[0][2]), v[3]) for v in t_]

    cut_frags = []
    for p in water_parts:
        for t3 in tris[p]:
            consumed, kept = _cut_tri(t3)
            if kept is None:
                continue
            wat_consumed += consumed
            wat_drop[p].append(list(t3))
            cut_frags.append((p, [_up_tri([_lift_v(v) for v in t_])
                                  for t_ in kept]))
    # THE LADDER SYNTHESIS: on a DEEP-fronted shore (the footprint cut no sea2 --
    # no wash to continue) cut sea3/sea5 remainders re-band to WASH, and uncut
    # deep tiles the W chain runs close by join it (the swash needs its real
    # seaward sea2 depth); the ring trigger then interposes sea1. On a
    # wash-fronted SHELF shore everything keeps its own band by default -- but a
    # real beach owns a PURE-WASH apron (the (16,5) A/B measured ~13u; a stock
    # outer band at ~4u reads as a squared deep tile against the foam), so an
    # EXPLICIT wash_reach re-proportions the ladder there too (THE LADDER-TAPER
    # LAW's mint analogue): whole sea1/sea3/sea5 tiles within reach of the
    # waterline re-band to wash, and the ladder-repair fixpoint interposes sea1
    # at the new boundary + re-emits affected strip neighbours. wash_reach=None
    # keeps every proven behavior byte-exact (deep -> 4.0, shelf -> off).
    deep_shore = not wat_drop["sea2"]
    reach = ((4.0 if deep_shore else 0.0) if wash_reach is None
             else float(wash_reach))
    conv_parts = ("sea3", "sea5") if deep_shore else ("sea1", "sea3", "sea5")

    def _near_w(t_):
        """Within ``reach`` of the waterline chain (centroid to nearest segment).
        Deliberately NOT restricted to the beach face: lateral growth into a
        frame-bound pocket is handled by the repair fixpoint's ROLLBACK rule,
        which knows the true criterion (does the cascade need a frame-row
        cell), where geometry cannot (the (16,5) NW pocket is 'seaward' of the
        chain's north run yet frame-bound; the SE lateral is open water)."""
        cx_ = sum(v[0][0] for v in t_) / 3.0
        cz_ = sum(v[0][2] for v in t_) / 3.0
        return min(_pt_seg((cx_, 0.0, cz_), W[i], W[i + 1])
                   for i in range(ncol)) <= reach

    for p, frags in cut_frags:
        if deep_shore and p in ("sea3", "sea5"):
            wat_emit["sea2"] += [_to_wash(t_) for t_ in frags]
        else:
            wat_emit[p] += frags
    if deep_shore and reach > 0.0:
        wash_dropped = {p: {_key_set(t) for t in wat_drop[p]}
                        for p in ("sea3", "sea5")}
        for p in ("sea3", "sea5"):
            for t3 in tris[p]:
                if _key_set(t3) in wash_dropped[p]:
                    continue
                if _near_w(t3):
                    wat_drop[p].append(list(t3))
                    wat_emit["sea2"].append(_to_wash(list(t3)))
    # shelf-shore re-proportion seeds ride THE LADDER-REPAIR FIXPOINT itself
    # (planned below, next to the ring re-band): the repair's rollback rule is
    # what makes them frame-safe, so they cannot be applied here.
    shelf_reach = 0.0 if deep_shore else reach
    if abs(terr_consumed + wat_consumed - foot_area) > max(0.01 * foot_area, 0.05):
        raise ValueError(f"COVERAGE LEDGER: the footprint ({foot_area:.2f} sq-u) is "
                         f"covered by only {terr_consumed + wat_consumed:.2f} sq-u "
                         f"of dropped terrain+water -- a hole under the beach; move "
                         f"the anchors")

    chain_k = {_pk(p) for p in L + S + W}
    # no surviving tri may sit INSIDE the footprint (a sliver that escaped the cut)
    drop_sets = {_key_set(t) for t in ter_drop}
    for p in water_parts:
        drop_sets |= {_key_set(t) for t in wat_drop[p]}
    for p in ("terrain",) + water_parts:
        for t3 in tris[p]:
            if _key_set(t3) in drop_sets:
                continue
            cx_ = sum(v[0][0] for v in t3) / 3.0
            cz_ = sum(v[0][2] for v in t3) / 3.0
            if _in_fp(cx_, cz_) and _fp_dist(cx_, cz_) > 1e-4:
                raise ValueError(f"a surviving {p} tri sits inside the footprint -- "
                                 f"an escaped sliver (z-fight); a cut defect")

    # boundary cuts from every emitted fragment vert (post lift/snap)
    seg_cuts = {}
    for t3 in ter_emit + [t for p in water_parts for t in wat_emit[p]]:
        for v in t3:
            if _pk(v[0]) in chain_k:
                continue
            hit = _on_seg(v[0])
            if hit is not None:
                seg_cuts.setdefault(hit[0], {})[round(hit[1], 9)] = v[0]

    if os.environ.get("FF9_VIRGIN_DEBUG"):
        for tag in sorted(seg_cuts, key=str):
            print(f"[debug] cuts {tag}: "
                  + " ".join(f"t={t:.4f}({p[0]:.4f},{p[1]:.3f},{p[2]:.4f})"
                             for t, p in sorted(seg_cuts[tag].items())))
    # --- sand + foam emission (cut-aware fans; the proven language walks) ---
    # exemplars: the block's own where it has a beach; on a beach-less block the
    # IDALL keeps the LOCAL area/event bits (encounters/entrances stay this
    # block's) with the language's topograph, and normals come from the pins
    if sand:
        s_nrm, s_id = sand[0][0][1], tuple(sand[0][0][3])
    else:
        ld = decode_id(int(round(other[0][0][3][0])))
        pd = tuple(pin_sand[0][0][3])
        s_nrm = pin_sand[0][0][1]
        s_id = (float(encode_id(event=0, area=ld["area"], topograph=fam["topo"],
                                flags=decode_id(int(round(pd[0])))["flags"])),
                ) + tuple(pd[1:])
    if foam_all:
        f_nrm, f_id = foam_all[0][0][1], tuple(foam_all[0][0][3])
    else:
        ld = decode_id(int(round(other[0][0][3][0])))
        pf = tuple(pin_foam[0][0][3])
        pfd = decode_id(int(round(pf[0])))
        f_nrm = pin_foam[0][0][1]
        f_id = (float(encode_id(event=0, area=ld["area"],
                                topograph=pfd["topograph"], flags=pfd["flags"])),
                ) + tuple(pf[1:])
    uJ_s, uF_s = SAND_ULAT[1] + fam["du"], SAND_ULAT[2] + fam["du"]
    bl = FOAM_FAMILIES[family]["BL"]
    sand_emit, foam_emit = [], []

    def _fan(apex, poly, uv_of, nrm, idall):
        out = []
        for p, q in zip(poly, poly[1:]):
            t_ = [(apex, nrm, uv_of(apex), idall), (p, nrm, uv_of(p), idall),
                  (q, nrm, uv_of(q), idall)]
            if TR._tri_area2_3d(t_) > 1e-6:
                out.append(_up_tri(t_))
        return out

    def _cuts(tag, a):
        cs = sorted(seg_cuts.get(tag, {}).items())
        return [p for _, p in cs] if a else [p for _, p in reversed(cs)]

    for i in range(ncol):
        lcut = _cuts(("L", i), True)
        wcut = _cuts(("W", i), True)
        if i in (0, ncol - 1):
            end = 0 if i == 0 else 1
            # cap corner naming: j = junction (interior side), f = free (terminal)
            if end == 0:
                lj, lf, sj, sf, wj, wf = L[1], L[0], S[1], S[0], W[1], W[0]
                lcut_jf = _cuts(("L", i), True)       # seg runs free -> junction
                wcut_jf = _cuts(("W", i), True)
            else:
                lj, lf, sj, sf, wj, wf = L[n - 2], L[n - 1], S[n - 2], S[n - 1], \
                    W[n - 2], W[n - 1]
                lcut_jf = _cuts(("L", i), False)      # seg runs junction -> free
                wcut_jf = _cuts(("W", i), False)
            tl = _cuts(("TL", end), True)             # L-end -> S-end order
            tw = _cuts(("TW", end), True)             # S-end -> W-end order
            # the emitted split must cover the SAME region the footprint claimed --
            # a reflex cap corner (a leaning real crease-base pair) fixes the diagonal
            ds = quad_diag[("sand", i)]
            df = quad_diag[("foam", i)]
            diag_s = ("sj-lf" if ds == 0 else "lj-sf") if end == 0 \
                else ("lj-sf" if ds == 0 else "sj-lf")
            diag_f = ("wj-sf" if df == 0 else "sj-wf") if end == 0 \
                else ("sj-wf" if df == 0 else "wj-sf")
            if ("sand", i) in quad_forced and diag_s != "sj-lf":
                raise ValueError(f"cap {end}: the sand quad is reflex away from the "
                                 f"junction diagonal -- outside the v1 fan language")
            if ("foam", i) in quad_forced and diag_f == "wj-sf" and (tw or wcut):
                raise ValueError(f"cap {end}: a reflex foam quad with boundary cuts "
                                 f"-- outside the v1 fan language")
            # sand cap: fan from the junction seam corner over free/land edges
            el_t = plan(lf, sf) or 1.0
            el_l = plan(lf, lj) or 1.0

            def uv_sc(p, lf=lf, sf=sf, lj=lj, sj=sj, el_t=el_t, el_l=el_l):
                if p is sj or p is sf:
                    return (uJ_s if p is sj else uF_s, cap_pins[1])
                if p is lj:
                    return (uJ_s, cap_pins[0])
                if p is lf:
                    return (uF_s, cap_pins[0])
                hit = _on_seg(p)
                if hit and hit[0][0] == "TL":
                    f = plan(lf, p) / el_t
                    return (uF_s, cap_pins[0] + f * (cap_pins[1] - cap_pins[0]))
                f = plan(lf, p) / el_l
                return (uF_s + f * (uJ_s - uF_s), cap_pins[0])
            if not tl and not lcut:
                sand_emit += emit_sand_cap(lj, sj, lf, sf, land_pin=cap_pins[0],
                                           seam_pin=cap_pins[1], diag=diag_s,
                                           nrm=s_nrm, idall=s_id)
            else:
                poly = [sf] + list(reversed(tl)) + [lf] + lcut_jf + [lj]
                sand_emit += _fan(sj, poly, uv_sc, s_nrm, s_id)
            # foam cap (BL fade): fan from the junction seam corner
            uF_f, uJ_f, vS_f, vW_f = bl
            el_tw = plan(sf, wf) or 1.0
            el_w = plan(wf, wj) or 1.0

            def uv_fc(p, sf=sf, wf=wf, wj=wj, sj=sj, el_tw=el_tw, el_w=el_w):
                if p is sj:
                    return (uJ_f, vS_f)
                if p is sf:
                    return (uF_f, vS_f)
                if p is wf:
                    return (uF_f, vW_f)
                if p is wj:
                    return (uJ_f, vW_f)
                hit = _on_seg(p)
                if hit and hit[0][0] == "TW":
                    f = plan(sf, p) / el_tw
                    return (uF_f, vS_f + f * (vW_f - vS_f))
                f = plan(wf, p) / el_w
                return (uF_f + f * (uJ_f - uF_f), vW_f)
            if not tw and not wcut:
                foam_emit += emit_foam_cap(sj, wj, sf, wf, slot="BL", family=family,
                                           diag=diag_f, nrm=f_nrm, idall=f_id)
            else:
                poly = [sf] + tw + [wf] + wcut_jf + [wj]
                foam_emit += _fan(sj, poly, uv_fc, f_nrm, f_id)
            continue
        # run column: sand
        rect = 0 if TR._h01(L[i][0] + 2.9, L[i][2] + 1.3) < 0.5 else 1
        u0, u1 = SAND_ULAT[rect] + fam["du"], SAND_ULAT[rect + 1] + fam["du"]
        la, lb = L[i], L[i + 1]
        el = plan(la, lb) or 1.0

        def uv_sr(p, la=la, el=el, u0=u0, u1=u1, i=i):
            if p is S[i]:
                return (u0, run_pins[1])
            if p is S[i + 1]:
                return (u1, run_pins[1])
            return (u0 + (plan(la, p) / el) * (u1 - u0), run_pins[0])
        if not lcut:
            uv = {id(la): (u0, run_pins[0]), id(lb): (u1, run_pins[0]),
                  id(S[i]): (u0, run_pins[1]), id(S[i + 1]): (u1, run_pins[1])}
            split = ((S[i], lb, la), (S[i], S[i + 1], lb)) if i % 2 \
                else ((la, S[i + 1], S[i]), (la, lb, S[i + 1]))
            for tri_pts in split:
                sand_emit.append(_up_tri([(p, s_nrm, uv[id(p)], s_id)
                                          for p in tri_pts]))
        else:
            apex, closing = (S[i], (S[i], S[i + 1], lb)) if i % 2 \
                else (S[i + 1], (S[i + 1], S[i], la))
            sand_emit += _fan(apex, [la] + lcut + [lb], uv_sr, s_nrm, s_id)
            t_ = [(closing[0], s_nrm, uv_sr(closing[0]), s_id),
                  (closing[1], s_nrm, uv_sr(closing[1]), s_id),
                  (closing[2], s_nrm, uv_sr(closing[2]), s_id)]
            if TR._tri_area2_3d(t_) > 1e-6:
                sand_emit.append(_up_tri(t_))
        # run column: foam
        wa, wb = W[i], W[i + 1]
        el_w = plan(wa, wb) or 1.0

        def uv_fr(p, wa=wa, el_w=el_w, i=i):
            if p is S[i]:
                return (bl[0], family[0])
            if p is S[i + 1]:
                return (0.5, family[0])
            if p is wa:
                return (bl[0], family[1])
            if p is wb:
                return (0.5, family[1])
            return (bl[0] + (plan(wa, p) / el_w) * (0.5 - bl[0]), family[1])
        if not wcut:
            fuv = {id(S[i]): (bl[0], family[0]), id(S[i + 1]): (0.5, family[0]),
                   id(wa): (bl[0], family[1]), id(wb): (0.5, family[1])}
            fsplit = ((wa, S[i + 1], S[i]), (wa, wb, S[i + 1])) if i % 2 \
                else ((S[i], wb, wa), (S[i], S[i + 1], wb))
            for tri_pts in fsplit:
                foam_emit.append(_up_tri([(p, f_nrm, fuv[id(p)], f_id)
                                          for p in tri_pts]))
        else:
            apex, closing = (S[i], (S[i], S[i + 1], wb)) if i % 2 \
                else (S[i + 1], (S[i + 1], S[i], wa))
            foam_emit += _fan(apex, [wa] + wcut + [wb], uv_fr, f_nrm, f_id)
            t_ = [(closing[0], f_nrm, uv_fr(closing[0]), f_id),
                  (closing[1], f_nrm, uv_fr(closing[1]), f_id),
                  (closing[2], f_nrm, uv_fr(closing[2]), f_id)]
            if TR._tri_area2_3d(t_) > 1e-6:
                foam_emit.append(_up_tri(t_))

    cut_keys = {_pk(p) for cs in seg_cuts.values() for p in cs.values()}
    for t3 in sand_emit:
        if _sand_tri_decode(t3, fam) is not None:
            continue
        # a boundary-cut vert carries an affinely-interpolated v (lawful
        # subdivision, the u-strip law); every other vert must sit on the pins
        for v in t3:
            if _pk(v[0]) in cut_keys:
                continue
            if _sand_vclass(round(v[2][1], 4), fam) is None:
                raise ValueError("a minted sand tri does not decode -- the "
                                 "emission self-check failed")
    for t3 in foam_emit:
        us = [v[2][0] for v in t3]
        vs = [v[2][1] for v in t3]
        if not ((max(us) <= 0.502 and max(vs) <= 0.502)
                or (max(us) <= 0.502 and min(vs) >= 0.498)):
            raise ValueError("a minted foam tri is outside the run/BL windows")

    # --- the ring re-band: sea3 may not front the minted wash ({2,3} is
    # off-language); flip such cells to sea1 by corner-role assignment and re-emit
    # affected strip neighbours (THE DEFORMED-TILE RECT LAW, band_convert's emitter)
    groups_by_part = {p: list(_deformed_strip_groups(tris[p]))
                      for p in ("sea1", "sea5")}
    u_pair, v_rows = _strip_float_vocab(groups_by_part)
    reg = {}
    for p, gs in groups_by_part.items():
        for gtris, kind, det in gs:
            if any(_key_set(t) in drop_sets for t in gtris):
                continue                              # dropped under the mint
            c = Counter(_cell_of_tri(t) for t in gtris).most_common(1)[0][0]
            ent = {"gtris": gtris, "det": det, "es": None, "row": None, "oname": None}
            if kind == "rect":
                hits = _role_decode(det[0], c, u_pair, v_rows)
                if len(hits) == 1:
                    ri, oname = hits[0]
                    ent.update(row=ri, oname=oname,
                               es=TR.STRIP_EDGESET.get((ri, oname)))
            reg[(p, c)] = ent

    # pre/post owner maps (cell -> parts)
    owner = defaultdict(set)
    for p in ("terrain", "beach1") + water_parts:
        for t3 in tris[p]:
            owner[_cell_of_tri(t3)].add(p)
    owner2 = defaultdict(set)
    surv = {}
    for p in ("terrain", "beach1") + water_parts:
        surv[p] = [t3 for t3 in tris[p] if _key_set(t3) not in drop_sets]
    emits0 = {"terrain": ter_emit + sand_emit, "beach1": foam_emit}
    for p in ("terrain", "beach1") + water_parts:
        for t3 in surv[p] + emits0.get(p, []) + wat_emit.get(p, []):
            owner2[_cell_of_tri(t3)].add(p)

    def water2(c):
        return {p for p in owner2.get(c, ()) if p in WATER_DEPTH}

    win_cells = {(math.floor(p[0] / 4.0), math.floor(p[2] / 4.0)) for p in L + S + W}
    scan_r = max(3, int(math.ceil(reach / 4.0)) + 1)
    scan = {(cx_ + dx, cz_ + dz) for cx_, cz_ in win_cells
            for dx in range(-scan_r, scan_r + 1) for dz in range(-scan_r, scan_r + 1)}
    ring_drop_by = defaultdict(list)
    ring_emit_by = defaultdict(list)
    post_reg = dict(reg)
    changed_cells = {c for c in scan if water2(c) != {p for p in owner.get(c, ())
                                                     if p in WATER_DEPTH}}
    def water_pre(c):
        return {p for p in owner.get(c, ()) if p in WATER_DEPTH}

    # a deep tile (sea3/sea5) sharing a geometric EDGE with the minted foam is
    # wash-fronted regardless of what else its cell carries -- the ring must
    # interpose there
    foam_ek = set()
    for t3 in foam_emit:
        ps = [v[0] for v in t3]
        for j in range(3):
            foam_ek.add(frozenset((_pk(ps[j]), _pk(ps[(j + 1) % 3]))))

    def _foam_welded_deep():
        for sp_ in ("sea3", "sea5"):
            for t3 in surv[sp_]:
                ps = [v[0] for v in t3]
                for j in range(3):
                    if frozenset((_pk(ps[j]), _pk(ps[(j + 1) % 3]))) in foam_ek:
                        return sp_, _cell_of_tri(t3)
        return None

    #: THE LADDER REPAIR MAP: an introduced unlawful band pair converts the
    #: DEEPER tile one step shallower; iterating converges every pair class
    #: ({wash|4} heals via 4->5 then 5->1; {1|4} via 4->5; {wash|3} via 3->1)
    _LADDER_DOWN = {"sea4": "sea5", "sea5": "sea1", "sea3": "sea1"}

    def _pair_lawful(a, b):
        """The lattice adjacency law over two cells' water sets, wash included:
        band pairs must be in the learned table, and a wash-class cell (foam/
        sea2 only) may sit beside nothing deeper than sea1."""
        sa = {q for q in a if q not in ("beach1", "sea2")}
        sb = {q for q in b if q not in ("beach1", "sea2")}
        for qa in sa:
            for qb in sb:
                if qa != qb and frozenset((qa, qb)) not in _LAWFUL_ADJ:
                    return False
        if (a and not sa and sb
                and max(WATER_DEPTH[q] for q in sb) > WATER_DEPTH["sea1"]):
            return False
        if (b and not sb and sa
                and max(WATER_DEPTH[q] for q in sa) > WATER_DEPTH["sea1"]):
            return False
        return True

    # PLAN-THEN-EMIT: the repair fixpoint runs on the OWNER MAP only (band
    # bookkeeping); geometry emits ONCE afterwards from the FINAL facts -- an
    # in-loop emission goes stale the moment a later conversion changes its
    # neighbour (the shade gate catches exactly that)
    #
    # THE SHELF RE-PROPORTION (the ladder-taper law's mint analogue): a real
    # beach owns a PURE-WASH apron (the (16,5) A/B measured ~13u; a stock deep
    # band at ~4u reads as a squared tile against the foam). An explicit
    # wash_reach on a wash-fronted shore SEEDS whole facing tiles within reach
    # as planned wash conversions -- they ride this fixpoint (plan-then-emit,
    # strip re-emission, every gate) rather than the drop stage, because only
    # the fixpoint can ROLL a seed BACK when its repair cascade would need a
    # FRAME-ROW cell: the repair is border-blind by construction (an edge-set
    # at the frame cannot see the neighbour block's bands, so a frame-row cell
    # never re-bands lawfully in a single-cell morph -- the (16,5) NW-pocket
    # trace). The apron grows exactly where the block allows.
    fx0_, fx1_ = 64.0 * donor[0], 64.0 * donor[0] + 64.0
    fz1_, fz0_ = -64.0 * donor[1], -64.0 * donor[1] - 64.0
    frame_ring = set()
    for p_ in water_parts:
        for t3 in tris[p_]:
            if any(min(abs(v[0][0] - fx0_), abs(v[0][0] - fx1_),
                       abs(v[0][2] - fz0_), abs(v[0][2] - fz1_)) < 0.01
                   for v in t3):
                frame_ring.add(_cell_of_tri(t3))
    cell_src = defaultdict(set)
    partial_pc = set()   # (part, cell) with a cut tri: no whole tile of THAT part
    for p_ in ("sea1", "sea3", "sea5"):
        for t3 in tris[p_]:
            c_ = _cell_of_tri(t3)
            cell_src[c_].add(p_)
            if _key_set(t3) in drop_sets:
                partial_pc.add((p_, c_))
    seeds = {}
    if shelf_reach > 0.0:
        for c_, srcs in sorted(cell_src.items()):
            if c_ in frame_ring or len(srcs) != 1:
                continue
            src_ = next(iter(srcs))
            if (src_, c_) in partial_pc:
                continue
            c_tris = [t3 for t3 in surv[src_] if _cell_of_tri(t3) == c_]
            if not c_tris or not _near_w(c_tris[0]):
                continue
            seeds[c_] = src_
    conversions = {}                     # cell -> [source_part, current_target]
    frozen = set()                       # rolled back -- never re-seeded
    fallen = set()                       # sea1 attempt fell back -- proven unlearnable
    for c_, src_ in sorted(seeds.items()):
        conversions[c_] = [src_, "sea2"]
        owner2[c_] = (owner2[c_] - {src_}) | {"sea2"}
        changed_cells.add(c_)
    for _outer in range(20):
        for _round in range(400):
            viol = None
            hit = _foam_welded_deep()
            if hit is not None and hit[1] not in conversions:
                viol = (hit[0], hit[1], None)
            for c in sorted(scan):
                if viol is not None:
                    break
                cw = water2(c)
                if not cw:
                    continue
                for dname, (dx, dz) in TR._DIRS.items():
                    nb = (c[0] + dx, c[1] + dz)
                    nbw = water2(nb)
                    if not nbw or _pair_lawful(cw, nbw):
                        continue
                    # only a pair the MINT created triggers (the no-introduced-
                    # misses law: real shore cells carry pre-existing contacts)
                    if (water_pre(c) and water_pre(nb)
                            and not _pair_lawful(water_pre(c), water_pre(nb))):
                        continue
                    deep_c = (c if max(WATER_DEPTH[q] for q in cw)
                              >= max(WATER_DEPTH[q] for q in nbw) else nb)
                    dw = water2(deep_c)
                    sp_ = max((q for q in dw if q in _LADDER_DOWN),
                              key=lambda q: WATER_DEPTH[q], default=None)
                    if sp_ is None:
                        raise ValueError(f"adjacency repair: no ladder step for "
                                         f"{sorted(dw)} at {deep_c}")
                    viol = (sp_, deep_c, nb if deep_c is c else c)
                    break
            if viol is None:
                break
            sp, c, other = viol
            if (c in frame_ring or c in fallen or (sp, c) in partial_pc) \
                    and other is not None and other in conversions:
                # THE ROLLBACK RULE: some cells should not re-band -- a
                # FRAME-ROW cell (the repair is border-blind: its edge-set
                # cannot see the neighbour block's bands, and an in-place
                # deploy's frame gate would refuse the re-label), a FALLEN
                # cell (proven unlearnable: its sea1 attempt fell back), and a
                # PARTIAL (part, cell) (footprint-cut fragments have no whole
                # tile to re-band). When the pair's shallow side is a
                # revertible conversion, revert THAT instead (monotone: each
                # rollback removes one conversion). A merely rolled-back cell
                # stays convertible DOWN-ladder (the compressed
                # wash->sea1->frame-sea3 form is lawful and real). With no
                # revertible neighbour, fall through to the legacy behavior --
                # the natural gates (no-ladder-step, the PARTIAL emit check,
                # the deploy frame gate) stay the judges, byte-compatible with
                # every proven build.
                src0, cur0 = conversions.pop(other)
                owner2[other] = (owner2[other] - {cur0, "sea2"}) | {src0}
                frozen.add(other)
                if os.environ.get("FF9_VIRGIN_DEBUG"):
                    print(f"[debug] ladder ROLLBACK: {other} back to {src0} "
                          f"(the pair needed frame/fallen/partial {c})")
                continue
            prev = conversions.get(c)
            src = prev[0] if prev else sp
            cur = prev[1] if prev else sp
            tgt = _LADDER_DOWN.get(cur)
            if tgt is None:
                raise ValueError(f"adjacency repair: {cur} at {c} has no further "
                                 f"ladder step")
            if os.environ.get("FF9_VIRGIN_DEBUG"):
                print(f"[debug] ladder plan: {src} at {c} -> {tgt}")
            conversions[c] = [src, tgt]
            owner2[c] = (owner2[c] - {cur}) | {tgt}
            changed_cells.add(c)
        else:
            raise ValueError("the ladder repair did not converge in 400 rounds")
        # --- EMIT from the final owner map; a cell with no lawful strip form
        # falls back to WASH (monotone: re-plan and re-emit) ---
        staged_wash, staged_strip, fell_back = [], [], False
        for c, (src, tgt) in sorted(conversions.items()):
            c_tris = [t3 for t3 in surv[src] if _cell_of_tri(t3) == c]
            if not c_tris:
                raise ValueError(f"ladder repair: the {src} at {c} is a PARTIAL "
                                 f"tile (a cut fragment) -- no whole tile to "
                                 f"re-band; shrink the footprint off it")
            if tgt == "sea2":
                staged_wash.append((src, c, c_tris))
                continue
            ent = post_reg.get((src, c)) if src == "sea5" else None
            corners_c = lerps_c = None
            if ent is not None and ent.get("det") is not None:
                corners_c, lerps_c = ent["det"]
            else:
                corners_c, lerps_c = {}, {}
                for t3 in c_tris:
                    for v in t3:
                        corners_c.setdefault(_pk(v[0]),
                                             (v[0], (v[2][0], v[2][1]), None))
                if len(corners_c) != 4:
                    corners_c = None
            es_c = frozenset(
                dname for dname, (dx, dz) in TR._DIRS.items()
                if water2((c[0] + dx, c[1] + dz))
                and max(WATER_DEPTH[q] for q in water2((c[0] + dx, c[1] + dz)))
                > WATER_DEPTH[tgt])
            if corners_c is None or es_c not in TR.EDGESET2STRIP:
                if tgt != "sea1":
                    raise ValueError(f"adjacency repair: the {src} at {c} has no "
                                     f"lawful {tgt} form (a non-quad / an "
                                     f"unlearned edge-set) -- refusing")
                if os.environ.get("FF9_VIRGIN_DEBUG"):
                    print(f"[debug] ladder fallback: {src} at {c} -> sea2")
                conversions[c] = [src, "sea2"]
                owner2[c] = (owner2[c] - {tgt}) | {"sea2"}
                fallen.add(c)
                fell_back = True
                break
            ri_c, oname_c = _strip_pick(es_c, c)
            c_new = _strip_emit(c_tris, corners_c, lerps_c, c, ri_c, oname_c,
                                u_pair, v_rows)
            staged_strip.append((src, c, tgt, c_tris, c_new, es_c, ri_c, oname_c))
        if fell_back:
            continue
        for src, c, c_tris in staged_wash:
            ring_emit_by["sea2"].extend(_to_wash(t3) for t3 in c_tris)
            ring_drop_by[src].extend(c_tris)
            surv[src] = [t3 for t3 in surv[src] if _cell_of_tri(t3) != c]
            post_reg.pop((src, c), None)
        for src, c, tgt, c_tris, c_new, es_c, ri_c, oname_c in staged_strip:
            ring_drop_by[src].extend(c_tris)
            ring_emit_by[tgt].extend(c_new)
            surv[src] = [t3 for t3 in surv[src] if _cell_of_tri(t3) != c]
            post_reg.pop((src, c), None)
            post_reg[(tgt, c)] = {"gtris": c_new, "det": None, "es": es_c,
                                  "row": ri_c, "oname": oname_c}
        break
    else:
        raise ValueError("the ladder repair kept falling back to wash -- the "
                         "site has no lawful ladder")
    # remaining unlawful band pairs anywhere in the scan window -> refuse
    for c in sorted(scan):
        for dx, dz in ((1, 0), (0, 1)):
            nb = (c[0] + dx, c[1] + dz)
            for a in water2(c) - {"beach1", "sea2"}:
                for b in water2(nb) - {"beach1", "sea2"}:
                    if frozenset((a, b)) not in _LAWFUL_ADJ:
                        raise ValueError(f"adjacency gate: {a} at {c} beside {b} at "
                                         f"{nb} is off-language after the mint")

    # affected strip neighbours: any surviving decoded tile whose claims toward
    # CHANGED cells no longer hold re-emits under its adjusted edge-set
    for (p, c), t in sorted(reg.items()):
        if (p, c) not in post_reg or post_reg[(p, c)] is not t:
            continue                                  # replaced already
        if t["es"] is None:
            continue
        es_new = set(t["es"])
        touched = False
        for dname, (dx, dz) in TR._DIRS.items():
            nb = (c[0] + dx, c[1] + dz)
            if nb not in changed_cells:
                continue
            touched = True
            nbw = water2(nb)
            if p in nbw:
                nt = post_reg.get((p, nb))
                claim = nt is not None and nt["es"] is not None \
                    and _OPP[dname] in nt["es"]
            else:
                claim = bool(nbw) and max(WATER_DEPTH[q] for q in nbw) \
                    > WATER_DEPTH[p]
            if claim:
                es_new.add(dname)
            else:
                es_new.discard(dname)
        if not touched or frozenset(es_new) == t["es"]:
            continue
        es_new = frozenset(es_new)
        if p == "sea1" and not es_new and c not in frame_ring:
            # THE ENGULFED-TILE RULE: an empty edge-set has NO strip form
            # because no such tile exists (a strip band tile always fronts
            # deeper water somewhere) -- a sea1 tile whose deep neighbours all
            # re-banded is INTERIOR to the new wash apron and re-bands to wash
            # itself. Always lawful by construction: es=[] means every
            # neighbour is wash/sea1, so the conversion mints only {2,<=1}
            # pairs. (A frame-row tile still refuses -- the part re-label
            # would break the border welds.)
            if os.environ.get("FF9_VIRGIN_DEBUG"):
                print(f"[debug] engulfed sea1 at {c} -> sea2")
            ring_drop_by[p].extend(t["gtris"])
            ring_emit_by["sea2"].extend(_to_wash(t3) for t3 in t["gtris"])
            surv[p] = [x for x in surv[p]
                       if _key_set(x) not in {_key_set(g) for g in t["gtris"]}]
            post_reg.pop((p, c), None)
            owner2[c] = (owner2[c] - {p}) | {"sea2"}
            changed_cells.add(c)
            continue
        if t["row"] is None:
            raise ValueError(f"the {p} tile at {c} does not role-decode -- its "
                             f"re-emission would not be law-derived; refusing")
        if es_new not in TR.EDGESET2STRIP:
            raise ValueError(f"the {p} tile at {c} would need edge-set "
                             f"{sorted(es_new)} (no learned strip) -- refusing")
        ri_n, oname_n = _strip_pick(es_new, c)
        corners, lerps = t["det"]
        new_tris = _strip_emit(t["gtris"], corners, lerps, c, ri_n, oname_n,
                               u_pair, v_rows)
        ring_drop_by[p].extend(t["gtris"])
        ring_emit_by[p].extend(new_tris)
        surv[p] = [x for x in surv[p]
                   if _key_set(x) not in {_key_set(g) for g in t["gtris"]}]
        post_reg[(p, c)] = {"gtris": new_tris, "det": None, "es": es_new,
                            "row": ri_n, "oname": oname_n}
    ring_drop = [t for p in water_parts for t in ring_drop_by.get(p, [])]
    ring_emit = [t for p in water_parts for t in ring_emit_by.get(p, [])]

    # shade-agreement scan over the whole registry (the donor is null-clean; the
    # post state must be too)
    for (p, c), t in post_reg.items():
        if t["es"] is None:
            continue
        for dname, (dx, dz) in TR._DIRS.items():
            nb = (c[0] + dx, c[1] + dz)
            claim = dname in t["es"]
            nbw = water2(nb)
            if not nbw:
                continue
            if p in nbw:
                nt = post_reg.get((p, nb))
                if nt is None or nt["es"] is None:
                    continue
                if claim != (_OPP[dname] in nt["es"]):
                    raise ValueError(f"shade gate [post]: one-sided deep-claim "
                                     f"between {p} {c} and {nb}")
            else:
                fact = max(WATER_DEPTH[q] for q in nbw) > WATER_DEPTH[p]
                if claim != fact:
                    raise ValueError(f"shade gate [post]: {p} {c} claims {dname} "
                                     f"{'deep' if claim else 'shallow'} against "
                                     f"{sorted(nbw)} at {nb}")
    # re-decode gate on every fresh strip emission
    for (p, c), t in post_reg.items():
        if t["det"] is not None or t["es"] is None:
            continue
        decoded = list(_deformed_strip_groups(t["gtris"]))
        if len(decoded) != 1 or decoded[0][1] != "rect":
            raise ValueError(f"re-decode gate: the emitted {p} tile at {c} does not "
                             f"decode as one rect group")
        hits = _role_decode(decoded[0][2][0], c, u_pair, v_rows)
        if hits != [(t["row"], t["oname"])]:
            raise ValueError(f"re-decode gate: the emitted {p} tile at {c} reads "
                             f"{hits}, wanted {[(t['row'], t['oname'])]}")
    if sorted(_pk(v[0]) for t3 in ring_emit for v in t3) \
            != sorted(_pk(v[0]) for t3 in ring_drop for v in t3):
        raise ValueError("geometry gate: the ring re-band must transport geometry "
                         "verbatim")

    # --- master gates ---
    all_drops = list(ter_drop) + [t for p in water_parts for t in wat_drop[p]] \
        + list(ring_drop)
    all_emits = list(ter_emit) + list(sand_emit) + list(foam_emit) \
        + [t for p in water_parts for t in wat_emit[p]] + list(ring_emit)

    def once(ts):
        ec = defaultdict(int)
        for t3 in ts:
            for a in range(3):
                ec[frozenset((_pk(t3[a][0]), _pk(t3[(a + 1) % 3][0])))] += 1
        return {e for e, cn in ec.items() if cn == 1}
    if once(all_drops) != once(all_emits):
        d_only = once(all_drops) - once(all_emits)
        e_only = once(all_emits) - once(all_drops)
        msg = ""
        for nm, es in (("drop-only", d_only), ("emit-only", e_only)):
            for e in sorted(es)[:6]:
                msg += f"\n  {nm}: {sorted(e)}"
        raise ValueError(f"UNION CRACK GATE: the minted union's outer boundary "
                         f"differs from the dropped union's ({len(d_only)} drop-only,"
                         f" {len(e_only)} emit-only){msg}")
    # T-vertices over the touched neighbourhood, all parts
    touched_k = {k for t3 in all_drops for v in t3 for k in (_pk(v[0]),)}
    near = [(True, t3) for t3 in all_emits]
    for p in ("terrain", "beach1") + water_parts:
        for t3 in surv[p]:
            if any(_pk(v[0]) in touched_k for v in t3):
                near.append((False, list(t3)))
    _tvertex_gate(near)

    # seaward of every interior W vert the water must read WASH (sea2) for at
    # least the real minimum band depth (THE ABSOLUTE WASH ENVELOPE's floor) --
    # on a synthesized ladder this is the gate that steers wash_reach
    post_sea2 = surv["sea2"] + wat_emit["sea2"] + ring_emit_by.get("sea2", [])
    for i in range(1, n - 1):
        nx, nz = normals[i]
        d = 0.3
        while d < 2.45:
            px, pz = W[i][0] + nx * d, W[i][2] + nz * d
            if not any(_pip_xz(px, pz, t3) for t3 in post_sea2):
                raise ValueError(f"the wash seaward of W[{i}] runs only "
                                 f"{d - 0.3:.1f}u of sea2 (< the 2.4u envelope "
                                 f"floor) -- grow wash_reach")
            d += 0.25

    out = [TR.DropTris("terrain", ter_drop),
           TR.EmitTris("terrain", ter_emit + sand_emit),
           TR.EmitTris("beach1", foam_emit)]
    for p in water_parts:
        drops = wat_drop[p] + ring_drop_by.get(p, [])
        if drops:
            out.append(TR.DropTris(p, drops))
        emits = wat_emit[p] + ring_emit_by.get(p, [])
        if emits:
            out.append(TR.EmitTris(p, emits))
    # RECONCILE against ``pre``: a mint DROP that matches a pre EMISSION cancels
    # pairwise (emissions bypass later tweaks in the transplant stream, so the
    # mint could never drop them -- the face is simply never re-emitted; its
    # ORIGINAL was already dropped by the pre's own DropTris). Mutates the
    # caller's pre tweaks in place -- pass the SAME pre list to the deploy.
    for tw_pre in pre:
        if not isinstance(tw_pre, TR.EmitTris):
            continue
        for tw_mint in out:
            if not isinstance(tw_mint, TR.DropTris)                     or tw_mint.part != tw_pre.part:
                continue
            keep = []
            for t3 in tw_pre.tris:
                ks = tw_mint._key_set(t3)
                if ks in tw_mint.keys:
                    tw_mint.keys.discard(ks)
                    tw_mint.expected -= 1
                else:
                    keep.append(t3)
            tw_pre.tris = keep
    return out


def cliff_bump(donor, start, end, depth, *, disc: int = 1, lod: str = "0_1", game=None):
    """The CONFORMING BOW (rung 1): displace the window's interior columns (crease + base +
    coincident water verts) seaward by ``depth * sin^2(pi t)``. Land UVs drag (approved
    in-game at 2.5u); water re-evaluates through its own tile map. The displacement envelope
    is geometric: a depth that folds any tile is refused here (offline), not at deploy."""
    win = CliffWindow(donor, start, end, disc=disc, lod=lod, game=game)
    ts = win.arc_params()
    moves = {}
    d_cols = [0.0]
    for i in range(1, len(win.base) - 1):
        d = depth * math.sin(math.pi * ts[i]) ** 2
        d_cols.append(d)
        for p in (win.base[i], win.crease[i]):
            moves[p] = (d * win.nhat[0], 0.0, d * win.nhat[1])
    d_cols.append(0.0)
    keyed = {_pk(p): v for p, v in moves.items()}
    _assert_pure_sea4(win, keyed, disc=disc, lod=lod, game=game)
    new_base = [(p[0] + d * win.nhat[0], p[1], p[2] + d * win.nhat[1])
                for p, d in zip(win.base, d_cols)]
    _clearance_gate(win, new_base, d_cols)
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
    _clearance_gate(win, new_base, d_cols)
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
