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

        # the wall quads between consecutive columns (exactly 2 tris each)
        self.quads = []
        for i in range(len(self.base) - 1):
            roles = {_pk(self.base[i]), _pk(self.crease[i]),
                     _pk(self.base[i + 1]), _pk(self.crease[i + 1])}
            tris = [t for t in self.cliff if _key_set(t) <= roles]
            if len(tris) != 2:
                raise ValueError(f"window gap {i} is not a clean one-quad wall "
                                 f"({len(tris)} tris match)")
            self.quads.append(tris)

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
    win = CliffWindow(donor, start, end, disc=disc, lod=lod, game=game)
    ncols = len(win.base)
    gaps = ncols - 1
    if gaps % 4:
        raise ValueError(f"the window has {gaps} wall gaps -- one inserted column per gap "
                         f"needs a multiple of 4 (the U-ramp with wrap is deterministic: "
                         f"interior column count must stay = old (mod 4))")

    drop_wall = [t for q in win.quads for t in q]
    ck = [_pk(p) for p in win.crease]
    bk = [_pk(p) for p in win.base]
    crease_keys = set(ck)
    moved_ck = set(ck[1:-1])
    moved_bk = set(bk[1:-1])
    drop_grass = [t for t in win.grass
                  if _key_set(t) & moved_ck
                  or any({ck[i], ck[i + 1]} <= _key_set(t) for i in range(gaps))]
    _assert_pure_sea4(win, moved_bk | moved_ck, disc=disc, lod=lod, game=game)

    # --- the new outline: old columns displaced + one new column per gap midpoint ---
    def arcpos(chain, i):
        return sum(math.dist(chain[j], chain[j + 1]) for j in range(i))
    LB = arcpos(win.base, ncols - 1)
    LCr = arcpos(win.crease, ncols - 1)
    t_cols = [arcpos(win.base, i) / LB for i in range(ncols)]
    params, kinds = [], []
    for i in range(gaps):
        params.append(t_cols[i])
        kinds.append(("old", i))
        params.append((t_cols[i] + t_cols[i + 1]) / 2.0)
        kinds.append(("new", None))
    params.append(1.0)
    kinds.append(("old", ncols - 1))

    def interp_chain(chain, s):
        acc = 0.0
        for a, b in zip(chain, chain[1:]):
            seg = math.dist(a, b)
            if acc + seg >= s - 1e-9:
                f = (s - acc) / seg
                return tuple(a[k] + f * (b[k] - a[k]) for k in range(3))
            acc += seg
        return chain[-1]
    bump_of = lambda t_: depth * math.sin(math.pi * t_) ** 2
    new_base, new_crease = [], []
    for t_, (kind, i) in zip(params, kinds):
        d = bump_of(t_)
        if kind == "old":
            nb = win.moved(win.base[i], d) if d > 1e-9 else win.base[i]
            nc = win.moved(win.crease[i], d) if d > 1e-9 else win.crease[i]
        else:
            nb = win.moved(interp_chain(win.base, t_ * LB), d)
            nb = (nb[0], 0.0, nb[2])
            nc = win.moved(interp_chain(win.crease, t_ * LCr), d)
        new_base.append(nb)
        new_crease.append(nc)
    widths = [math.dist(a, b) for a, b in zip(new_base, new_base[1:])]
    if min(widths) < 2.0:
        raise ValueError(f"degenerate wall column ({min(widths):.2f}u) -- widen the window "
                         f"or reduce depth")
    head_moves = {}
    for idx, (kind, i) in enumerate(kinds):
        if kind == "old" and 0 < i < ncols - 1:
            d = bump_of(params[idx])
            for p in (win.base[i], win.crease[i]):
                head_moves[p] = (d * win.nhat[0], 0.0, d * win.nhat[1])

    # --- the extended sea drop set: moved-vert fans + wedge overlap ---
    wedge_poly = [(p[0], p[2]) for p in new_base] + \
                 [(p[0], p[2]) for p in reversed(win.base)]
    drop_sea = []
    for t3 in win.sea4:
        ks = _key_set(t3)
        if (ks & moved_bk or any(_in_poly(v[0][0], v[0][2], wedge_poly) for v in t3)
                or any(_pip_xz(px, pz, t3) for (px, pz) in wedge_poly)):
            drop_sea.append(t3)
    for i, nb in enumerate(new_base[1:-1], 1):
        if not any(_pip_xz(nb[0], nb[2], t3) for t3 in drop_sea):
            raise ValueError(f"new outline vert {i} escapes the sea drop set -- depth too "
                             f"large for the local water (extend impossible: non-sea4 or "
                             f"frame within reach)")

    # --- wall emissions: per-quad corner copy by LEFT-COLUMN PHASE (wrap seams come free) ---
    def quad_corners(qi):
        roles = {bk[qi]: "bl", ck[qi]: "cl", bk[qi + 1]: "br", ck[qi + 1]: "cr"}
        out = {}
        for t3 in win.quads[qi]:
            for v in t3:
                out.setdefault(roles[_pk(v[0])], (v[2], v[1]))
        split = [tuple(roles[_pk(v[0])] for v in t3) for t3 in win.quads[qi]]
        return out, split
    idall_wall = tuple(drop_wall[0][0][3])
    wall_emit = []
    for qi in range(2 * gaps):
        corners, split = quad_corners(qi % 4)
        pos = {"bl": new_base[qi], "br": new_base[qi + 1],
               "cl": new_crease[qi], "cr": new_crease[qi + 1]}
        for tri_roles in split:
            wall_emit.append([(pos[r], corners[r][1], corners[r][0], idall_wall)
                              for r in tri_roles])

    # --- the native grass fill over the hole + wedge ---
    cell_quad = {}
    for t3 in win.grass:
        cx = math.floor(sum(v[0][0] for v in t3) / 3.0 / 4.0)
        cz = math.floor(sum(v[0][2] for v in t3) / 3.0 / 4.0)
        cell_quad.setdefault((cx, cz), TR._quad_of_uv(t3[0][2]))
    gloop, gpos, _guv, gnrm = _boundary_loop(drop_grass)
    for k in (ck[0], ck[-1]):
        if k not in gloop:
            raise ValueError("window crease end not on the grass hole boundary")
    crease_run = list(ck)
    for k in (crease_run[0], crease_run[-1]):
        i0 = gloop.index(k)
        rot = gloop[i0:] + gloop[:i0]
        if all(rot[i] == crease_run[i] for i in range(ncols)):
            gloop = rot
            break
        if all(rot[i] == crease_run[-1 - i] for i in range(ncols)):
            gloop = rot
            crease_run = list(reversed(crease_run))
            break
    else:
        raise ValueError("crease run not contiguous on the grass hole boundary")
    outer_cr = new_crease if crease_run[0] == ck[0] else list(reversed(new_crease))
    bpts3 = list(outer_cr) + [gpos[k] for k in gloop[ncols:]]
    poly2 = [(p[0], p[2]) for p in bpts3]
    interior = []
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
                if math.hypot(px - (x1 + tt * ex), pz - (z1 + tt * ez)) < 1.4:
                    clear = False
                    break
            if clear:
                interior.append((px, pz))

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
    pts3 = list(bpts3) + [(px, idw_y(px, pz) + (TR._h01(px, pz) - 0.5) * 0.4, pz)
                          for (px, pz) in interior]
    nrms = [gnrm.get(_pk(p)) or near_nrm(p[0], p[2]) for p in bpts3] \
           + [near_nrm(px, pz) for (px, pz) in interior]
    idall_grass = tuple(drop_grass[0][0][3])
    grass_emit = []
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
            avoid = {cell_quad.get((cell[0], cell[1] - 1)), cell_quad.get((cell[0] - 1, cell[1])),
                     cell_quad.get((cell[0] + 1, cell[1])), cell_quad.get((cell[0], cell[1] + 1)),
                     fill_quad.get((cell[0], cell[1] - 1)), fill_quad.get((cell[0] - 1, cell[1])),
                     fill_quad.get((cell[0] + 1, cell[1])), fill_quad.get((cell[0], cell[1] + 1))}
            choices = [q for q in ((0, 0), (0, 1), (1, 0), (1, 1)) if q not in avoid] \
                      or [(0, 0), (0, 1), (1, 0), (1, 1)]
            h = TR._h01(4.0 * cell[0] + 1.7, 4.0 * cell[1] + 2.3)
            fill_quad[cell] = choices[int(h * len(choices)) % len(choices)]
        ori = (0, 90, 180, 270)[int(TR._h01(4.0 * cell[0] + 3.1, 4.0 * cell[1] + 0.9) * 4) % 4]
        tri = [(p, nr, tuple(G.mains_uv(p[0], p[2], cell, fill_quad[cell], ori)), idall_grass)
               for p, nr in zip(tri_pts, tri_nrm)]
        ux, uz = tri[1][0][0] - tri[0][0][0], tri[1][0][2] - tri[0][0][2]
        vx, vz = tri[2][0][0] - tri[0][0][0], tri[2][0][2] - tri[0][0][2]
        if uz * vx - ux * vz <= 0:
            tri = [tri[0], tri[2], tri[1]]
        grass_emit.append(tri)

    # THE CRACK GATE + THE GRAIN GATE
    fe_count = defaultdict(int)
    for t3 in grass_emit:
        ps = [v[0] for v in t3]
        for i in range(3):
            fe_count[frozenset((_pk(ps[i]), _pk(ps[(i + 1) % 3])))] += 1
    fill_once = {e for e, c in fe_count.items() if c == 1}
    poly_edges = {frozenset((_pk(bpts3[i]), _pk(bpts3[(i + 1) % len(bpts3)])))
                  for i in range(len(bpts3))}
    if fill_once != poly_edges:
        raise ValueError(f"CRACK GATE: the grass fill's boundary does not match the region "
                         f"({len(fill_once - poly_edges)} extra / "
                         f"{len(poly_edges - fill_once)} missing edges = T-junction cracks)")
    longest = max(max(math.dist(t3[i][0], t3[(i + 1) % 3][0]) for i in range(3))
                  for t3 in grass_emit)
    if longest > MAX_GRAIN:
        raise ValueError(f"GRAIN GATE: a grass fill edge is {longest:.1f}u (> {MAX_GRAIN}) -- "
                         f"off the real terrain grain, reads as stretch")

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
        c = (math.floor(cx / 4.0), math.floor(cz / 4.0))
        if c in cell_tile:
            return cell_tile[c]
        best, bd = None, 1e18
        for t3 in drop_sea:
            tx = sum(v[0][0] for v in t3) / 3.0
            tz = sum(v[0][2] for v in t3) / 3.0
            d2 = (cx - tx) ** 2 + (cz - tz) ** 2
            if d2 < bd:
                best, bd = t3, d2
        return best
    idall_sea = tuple(drop_sea[0][0][3])
    ring_nrm = nrm_of[bk[len(bk) // 2]]
    sea_ring = []
    for (pa, pb, pc) in zip_tris:
        cx = (pa[0] + pb[0] + pc[0]) / 3.0
        cz = (pa[2] + pb[2] + pc[2]) / 3.0
        uvf = TR._affine_uv(tile_for(cx, cz))
        # PURE affine, no clamp: the tri carries EXACTLY a real tile's map (a clamp squashes
        # far verts onto the bbox edge = smear); extrapolation lands in a sibling quadrant of
        # the same tiling water texture -- content, not gutter.
        t3 = [(p, ring_nrm, tuple(uvf(p[0], p[2])), idall_sea) for p in (pa, pb, pc)]
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
    poly_a = abs(poly_a) / 2.0
    if abs((plan_area(drop_sea) - plan_area(sea_ring)) - poly_a) > 1.0:
        raise ValueError("LEDGER: dropped sea - emitted sea != the new land wedge")

    surv = _count_instances(win, {_pk(p) for p in head_moves},
                            exclude_sets=[_key_set(t) for t in
                                          drop_wall + drop_grass + drop_sea])
    return [TR.DropTris("terrain", drop_wall + drop_grass),
            TR.DropTris("sea4", drop_sea),
            TR.VertexDisplace(moves=head_moves, expected=surv),
            TR.EmitTris("terrain", wall_emit + grass_emit),
            TR.EmitTris("sea4", sea_ring)]
