"""THE LADDER MINT -- a beach arc on a `world-island` mint (built 2026-07-15).

The desert-beach arc's destination: on OUR islands we own the whole coast, so the
beach and its water ladder lay out clean -- no border-blind frame rows, no stock
inlets, no pre-existing contacts. `world-island --beach B0,B1` replaces the cliff
wall along an outline arc with the measured beach profile and mints the ladder:

    plain (land_height) -> BERM slope -> SAND band (L->S) -> FOAM ribbon (S->W)
      -> WASH collar (conforming, W -> the sea1 ring's lattice staircase)
      -> sea1 ring -> sea5 ring -> the sea4 plane (cut back)

Everything speaks the byte-measured languages: sand = the family band (SAND_BANDS,
run P/Q picks + the pins block's v pins), foam = the universal foam family (run
stamps), wash = the sea2 mains vocabulary (position-evaluated), sea1/sea5 = the
learned Wang table via the deformed-tile emitters, adjacency lawful BY CONSTRUCTION
(wash|1, 1|5, 5|4 -- the ring sets are built by dilation, THE LATTICE ADJACENCY
LAW). The arc ENDS pinch to the outline (all chains converge on the end vertex),
so the beach dies against the full-height flanking cliff -- the bay-arc grammar.

v1 scope: single-block beach geometry (the lattice parts split naturally; the
chain-based tris refuse a border crossing -- place the arc mid-face), pinch ends
(no BL cap fade graphics yet), grass + desert families only (the sand topo is
family-keyed; snow's topo-33 shore is measured but not mintable).
"""
from __future__ import annotations

import math
from collections import defaultdict

from . import transplant as TR
from .extract import encode_id

BLOCK = 64.0
CELL = 4.0
#: the byte-read beach profile (the (20,5)/(7,17)/(16,5) censuses): chain elevations
L_Y = 1.5625                 # the sand band's land edge
S_Y = 0.78125                # the sand/foam seam
W_Y = 0.0                    # the foam's waterline edge (desert (20,5): y 0)
SEA_Y = 0.0                  # every water tile
#: foam topo is FAMILY-KEYED (byte-read: grass beaches 30, desert beaches 34)
FOAM_TOPO = {"grass": 30, "desert": 34}
SAND_TOPO = {"grass": 31, "desert": 32}


def _cell_of(x, z):
    return (math.floor(x / CELL), math.floor(z / CELL))


def plan_arc(outline, center, bearing):
    """The contiguous outline-vertex run inside ``bearing = (deg0, deg1)`` (degrees
    CCW, east = 0, wrap allowed). Returns ``dict(idx=[...ordered...], ends=(e0, e1))``
    where ends are the two pinch anchors (the run's boundary vertices)."""
    b0, b1 = (float(bearing[0]) % 360.0, float(bearing[1]) % 360.0)
    cx, cz = center

    def inside(i):
        ox, oz = outline[i]
        d = math.degrees(math.atan2(oz - cz, ox - cx)) % 360.0
        return (b0 <= d <= b1) if b0 <= b1 else (d >= b0 or d <= b1)

    n = len(outline)
    flags = [inside(i) for i in range(n)]
    if all(flags) or not any(flags):
        raise ValueError("--beach: the bearing range selects the whole outline or "
                         "nothing -- give a partial arc")
    # rotate so the run is contiguous ([False..True..False])
    start = next(i for i in range(n) if not flags[i] and flags[(i + 1) % n])
    run = []
    j = (start + 1) % n
    while flags[j]:
        run.append(j)
        j = (j + 1) % n
    # any second run = a non-contiguous selection (a concave outline) -- refuse
    if sum(flags) != len(run):
        raise ValueError("--beach: the bearing range selects a NON-CONTIGUOUS arc "
                         "(a concave outline crosses the range twice) -- narrow it")
    if len(run) < 4:
        raise ValueError(f"--beach: only {len(run)} outline verts in the arc -- "
                         f"widen the bearing range (need >= 4)")
    return {"idx": run, "ends": (start, (run[-1] + 1) % n)}


def build_beach(outline, radii, center, arc, *, ground, land_height, rim,
                width=2.4, swash=4.0, pins_from=(20, 5), disc=1, game=None):
    """Build every beach artifact in the WORLD frame. Returns::

        dict(terrain=[(corners, idall, fam), ...],   # berm + sand -> the parent soup
             foam=[t3...], wash=[t3...], sea1=[t3...], sea5=[t3...],
             sea4_cut={cell...}, wall_skip={(i, j)...}, berm_cells=[...],
             block=(bx, by))

    where a ``t3`` is ``[(pos, nrm, uv, tan) x3]`` (transplant convention)."""
    from . import coastmorph as CM
    if ground not in SAND_TOPO:
        raise ValueError(f"--beach: no measured sand band for ground '{ground}' "
                         f"(families: {sorted(SAND_TOPO)}; snow's topo-33 shore is "
                         f"measured but not yet mintable)")
    fam = dict(CM.SAND_BANDS[ground], name=ground)
    cx, cz = center
    run, (e0, e1) = arc["idx"], arc["ends"]

    # --- the language pins (byte-read from the reference beach block) ---
    pin_terr = TR.world_tris(*pins_from, "terrain", disc=disc, game=game)
    pin_foam = TR.world_tris(*pins_from, "beach1", disc=disc, game=game)
    pfam = CM._sand_band_family(pin_terr, what="the pins block")
    if pfam is None or pfam["name"] != ground:
        raise ValueError(f"--beach-pins {pins_from} carries "
                         f"{'no' if pfam is None else pfam['name']} sand -- pass a "
                         f"real {ground}-family beach block")
    run_pins = cap_pins = None
    for t3 in pin_terr:
        d = CM._sand_tri_decode(t3, fam) if _topo(t3) == fam["topo"] else None
        if d is None:
            continue
        vs = sorted({round(v[2][1], 4) for v in t3})
        if d[0] == "run" and run_pins is None and len(vs) == 2:
            run_pins = vs
        if d[0] == "cap" and cap_pins is None and len(vs) == 2:
            cap_pins = vs
    if run_pins is None:
        raise ValueError("the pins block's sand carries no run pins")
    foam_family = CM._foam_family(pin_foam)
    if foam_family is None:
        raise ValueError("no lawful foam run family decodes in the pins block")
    fam_bl = CM.FOAM_FAMILIES[foam_family]["BL"]
    # the strip float dialect (sea1/sea5 emission) -- the pins block's own groups
    groups_by_part = {p: list(CM._deformed_strip_groups(
        TR.world_tris(*pins_from, p, disc=disc, game=game))) for p in ("sea1", "sea5")}
    u_pair, v_rows = CM._strip_float_vocab(groups_by_part)
    # part idalls (byte convention: flags 0)
    id_sand = float(encode_id(topograph=SAND_TOPO[ground]))
    id_foam = float(encode_id(topograph=FOAM_TOPO[ground]))
    id_sea12 = float(encode_id(topograph=53))
    id_sea55 = float(encode_id(topograph=54))

    # --- the chains (per arc vertex; ends pinch to the outline) ---
    def out_unit(i):
        ox, oz = outline[i]
        r = radii[i] if radii is not None else math.hypot(ox - cx, oz - cz)
        return ((ox - cx) / r, (oz - cz) / r)

    # the chains span the arc's INTERIOR vertices and PINCH at its first/last: the
    # end segments (outside the pinch) stay WALL -- with the bank-inset rim they
    # read as ~25-degree rocky slopes flanking the beach (the cliff connection),
    # and the pinch welds the wall base at outline[run[0]]/outline[run[-1]] exactly
    idxs = list(run)
    L, S, W = [], [], []
    for k, i in enumerate(idxs):
        ox, oz = outline[i]
        if k == 0 or k == len(idxs) - 1:
            p = (ox, 0.0, oz)                            # THE PINCH: all chains converge
            L.append(p)
            S.append(p)
            W.append(p)
        else:
            ux, uz = out_unit(i)
            L.append((ox - ux * width, L_Y, oz - uz * width))
            S.append((ox, S_Y, oz))
            W.append((ox + ux * swash, W_Y, oz + uz * swash))
    ncol = len(idxs) - 1

    # single-block gate (v1): every chain point in ONE block
    blks = {(math.floor(p[0] / BLOCK), math.floor(-p[2] / BLOCK))
            for ch in (L, S, W) for p in ch}
    if len(blks) != 1:
        raise ValueError(f"--beach: the beach spans blocks {sorted(blks)} -- v1 is "
                         f"single-block; move the arc off the border")
    blk = next(iter(blks))

    up = _up_tri
    terrain_items = []                                   # (corners5, idall, fam_name)
    berm_cells = set()

    # --- the berm (rim -> L), the island's own ground family. Subdivided RADIALLY
    # to ~2.2u rows: a single 4.6u quad wears ONE cell's mains map, overruns the
    # quadrant rect and SMEARS at the bleed clamp (the in-game "stretched" berm,
    # round 1) -- lattice-scale tris keep every map near its home cell.
    def _lerp3(a, b, t):
        return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]),
                a[2] + t * (b[2] - a[2]))

    nrows = max(1, int(math.ceil(max(
        math.hypot(rim[i][0] - L[k][0], rim[i][1] - L[k][2])
        for k, i in enumerate(idxs)) / 2.2)))            # ONE count: shared radial
    def _berm_tri(tri):
        if _area2(tri) < 1e-9:
            return
        tri = up(*tri)
        for p in tri:
            berm_cells.add(_cell_of(p[0], p[2]))
        berm_cells.add(_cell_of(sum(p[0] for p in tri) / 3.0,
                                sum(p[2] for p in tri) / 3.0))
        terrain_items.append((tri, "berm"))

    for k in range(ncol):                                # edges weld exactly
        i, j = idxs[k], idxs[k + 1]
        b0 = (rim[i][0], land_height, rim[i][1])
        b1 = (rim[j][0], land_height, rim[j][1])
        la, lb = L[k], L[k + 1]
        if la is S[k] or lb is S[k + 1]:
            # a PINCH column: fan from the pinch over the INNER (shared) edge's row
            # points -- the OUTER lateral edge stays one segment and welds the
            # transition wall quad exactly
            if la is S[k]:                               # left pinch
                pts = [_lerp3(b1, lb, r / nrows) for r in range(nrows + 1)]
                _berm_tri((b0, pts[0], la))
                for r in range(nrows):
                    _berm_tri((la, pts[r], pts[r + 1]))
            else:                                        # right pinch
                pts = [_lerp3(b0, la, r / nrows) for r in range(nrows + 1)]
                _berm_tri((pts[0], b1, lb))
                for r in range(nrows):
                    _berm_tri((lb, pts[r], pts[r + 1]))
            continue
        prev_a, prev_b = b0, b1
        for r in range(1, nrows + 1):
            t = r / nrows
            cur_a, cur_b = _lerp3(b0, la, t), _lerp3(b1, lb, t)
            for tri in ((prev_a, prev_b, cur_a), (cur_a, prev_b, cur_b)):
                _berm_tri(tri)
            prev_a, prev_b = cur_a, cur_b

    # --- the sand band (L -> S): run columns + conforming pinch triangles ---
    sand_tris = []                                       # (corners5, ...) via uv assign
    for k in range(ncol):
        la, lb, sa, sb = L[k], L[k + 1], S[k], S[k + 1]
        pinched = la is sa or lb is sb                   # an end column
        rect = 0 if TR._h01(la[0] + 2.9, la[2] + 1.3) < 0.5 else 1
        u0 = CM.SAND_ULAT[rect] + fam["du"]
        u1 = CM.SAND_ULAT[rect + 1] + fam["du"]
        uv = {id(la): (u0, run_pins[0]), id(lb): (u1, run_pins[0]),
              id(sa): (u0, run_pins[1]), id(sb): (u1, run_pins[1])}
        if la is sa:                                     # left pinch: one triangle
            uv[id(la)] = (u0, (run_pins[0] + run_pins[1]) / 2.0)
            tris = [(la, lb, sb)] if _area2((la, lb, sb)) > 1e-9 else []
        elif lb is sb:                                   # right pinch
            uv[id(lb)] = (u1, (run_pins[0] + run_pins[1]) / 2.0)
            tris = [(la, lb, sa)] if _area2((la, lb, sa)) > 1e-9 else []
        else:
            tris = ((sa, lb, la), (sa, sb, lb)) if k % 2 else ((la, sb, sa), (la, lb, sb))
        for tri in tris:
            tri = up(*tri)
            corners = tuple((p[0], p[1], p[2], *uv[id(p)]) for p in tri)
            sand_tris.append(corners)
    for corners in sand_tris:
        terrain_items.append((corners, "sand"))

    # --- the foam ribbon (S -> W), the beach1 part ---
    foam = []
    f_nrm = (0.0, 1.0, 0.0)
    f_id = (id_foam, 0.0, 0.0, 1.0)
    for k in range(ncol):
        sa, sb, wa, wb = S[k], S[k + 1], W[k], W[k + 1]
        fuv = {id(sa): (fam_bl[0], foam_family[0]), id(sb): (0.5, foam_family[0]),
               id(wa): (fam_bl[0], foam_family[1]), id(wb): (0.5, foam_family[1])}
        if sa is wa:
            fuv[id(sa)] = (fam_bl[0], (foam_family[0] + foam_family[1]) / 2.0)
            tris = [(sa, sb, wb)] if _area2((sa, sb, wb)) > 1e-9 else []
        elif sb is wb:
            fuv[id(sb)] = (0.5, (foam_family[0] + foam_family[1]) / 2.0)
            tris = [(sa, sb, wa)] if _area2((sa, sb, wa)) > 1e-9 else []
        else:
            tris = ((wa, sb, sa), (wa, wb, sb)) if k % 2 else ((sa, wb, wa), (sa, sb, wb))
        for tri in tris:
            foam.append(_up_tri4([(p, f_nrm, fuv[id(p)], f_id) for p in tri]))

    # --- the lattice cell sets: crossed / ring1 / ring5 (dilation = lawful chains) ---
    def seg_cells(a, b):
        cells = set()
        n = max(2, int(math.hypot(b[0] - a[0], b[2] - a[2]) / 1.0) + 1)
        for t in range(n + 1):
            f = t / n
            cells.add(_cell_of(a[0] + f * (b[0] - a[0]), a[2] + f * (b[2] - a[2])))
        return cells

    crossed = set()
    for ch in (S, W):
        for k in range(len(ch) - 1):
            crossed |= seg_cells(ch[k], ch[k + 1])
    for k in range(len(S)):
        crossed |= seg_cells(S[k], W[k])
    # the outline polygon = the land test for full cells
    poly = outline

    def land_corner(x, z):
        return _pip(x, z, poly)

    def cell_fully_sea(c):
        (ci, cj) = c
        return not any(land_corner(ci * CELL + dx, cj * CELL + dz)
                       for dx in (0.0, CELL) for dz in (0.0, CELL))

    DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
    ring1 = set()
    for c in crossed:
        for dx, dz in DIRS:
            nb = (c[0] + dx, c[1] + dz)
            if nb not in crossed and cell_fully_sea(nb):
                ring1.add(nb)
    ring5 = set()
    for c in ring1:
        for dx, dz in DIRS:
            nb = (c[0] + dx, c[1] + dz)
            if nb not in crossed and nb not in ring1 and cell_fully_sea(nb):
                ring5.add(nb)

    # demote engulfed ring1 cells (no ring5 neighbour -> no deep edge -> no strip form)
    demoted = {c for c in ring1
               if not any((c[0] + dx, c[1] + dz) in ring5 for dx, dz in DIRS)}
    ring1 -= demoted
    wash_full = demoted

    # --- sea1 / sea5 strip tiles (the learned Wang table, pins-block floats) ---
    def lattice_quad(c, idall):
        (ci, cj) = c
        pts = [(ci * CELL, SEA_Y, cj * CELL), ((ci + 1) * CELL, SEA_Y, cj * CELL),
               ((ci + 1) * CELL, SEA_Y, (cj + 1) * CELL), (ci * CELL, SEA_Y, (cj + 1) * CELL)]
        split = ((0, 1, 2), (0, 2, 3)) if (ci + cj) % 2 else ((1, 2, 3), (1, 3, 0))
        out = []
        for tri in split:
            out.append(_up_tri4([(pts[t], (0.0, 1.0, 0.0), (0.0, 0.0), idall)
                                 for t in tri]))
        return out

    def emit_strip(c, es, idall):
        if es not in TR.EDGESET2STRIP:
            raise ValueError(f"--beach: the ring cell {c} needs edge-set "
                             f"{sorted(es)} (no learned strip) -- shift the arc")
        gtris = lattice_quad(c, idall)
        corners = {}
        for t3 in gtris:
            for v in t3:
                corners.setdefault(CM._pk(v[0]), (v[0], (0.0, 0.0), None))
        for ri, oname in _pick_variants(es, c):
            if ri in v_rows:
                return CM._strip_emit(gtris, corners, {}, c, ri, oname, u_pair, v_rows)
        raise ValueError(f"--beach: no variant of edge-set {sorted(es)} has "
                         f"byte-observed floats in the pins block -- pick a pins "
                         f"block carrying that row")

    def _pick_variants(es, c):
        variants = TR.EDGESET2STRIP[es]
        first = int(TR._h01(4.0 * c[0] + 0.3, 4.0 * c[1] + 2.9) * len(variants)) % len(variants)
        return variants[first:] + variants[:first]

    dirname = {v: k for k, v in TR._DIRS.items()}
    sea1_tris, sea5_tris = [], []
    for c in sorted(ring1):
        es = frozenset(dirname[(dx, dz)] for dx, dz in DIRS
                       if (c[0] + dx, c[1] + dz) in ring5)
        sea1_tris += emit_strip(c, es, (id_sea12, 0.0, 0.0, 1.0))
    for c in sorted(ring5):
        es = frozenset(dirname[(dx, dz)] for dx, dz in DIRS
                       if ((c[0] + dx, c[1] + dz) not in ring5
                           and (c[0] + dx, c[1] + dz) not in ring1
                           and (c[0] + dx, c[1] + dz) not in crossed
                           and cell_fully_sea((c[0] + dx, c[1] + dz))))
        sea1_5 = emit_strip(c, es, (id_sea55, 0.0, 0.0, 1.0))
        sea5_tris += sea1_5

    # --- the wash collar: zip W -> the ring1/wash_full inner staircase ---
    inner = crossed | wash_full
    stair_edges = set()
    for c in sorted(ring1):
        (ci, cj) = c
        for (dx, dz), (a, b) in ((( -1, 0), ((ci * CELL, (cj + 1) * CELL), (ci * CELL, cj * CELL))),
                                 ((1, 0), (((ci + 1) * CELL, cj * CELL), ((ci + 1) * CELL, (cj + 1) * CELL))),
                                 ((0, -1), ((ci * CELL, cj * CELL), ((ci + 1) * CELL, cj * CELL))),
                                 ((0, 1), (((ci + 1) * CELL, (cj + 1) * CELL), (ci * CELL, (cj + 1) * CELL)))):
            if (ci + dx, cj + dz) in inner:
                stair_edges.add((a, b))
    # chain the staircase segments into the longest polyline
    adj = defaultdict(list)
    for a, b in stair_edges:
        adj[a].append(b)
        adj[b].append(a)
    ends = [p for p, ns in adj.items() if len(ns) == 1]
    if not stair_edges:
        raise ValueError("--beach: no wash staircase -- the ring sets came out "
                         "empty (arc too small?)")
    if len(ends) < 2:
        raise ValueError("--beach: the wash staircase is closed/branched -- "
                         "shift the arc")
    start = min(ends)
    chain, prev, cur = [start], None, start
    while True:
        nxt = [q for q in adj[cur] if q != prev]
        if not nxt:
            break
        prev, cur = cur, nxt[0]
        chain.append(cur)
    # orient the staircase along W's direction
    if math.hypot(chain[0][0] - W[0][0], chain[0][1] - W[0][2]) > \
            math.hypot(chain[-1][0] - W[0][0], chain[-1][1] - W[0][2]):
        chain.reverse()
    stair = [(p[0], SEA_Y, p[1]) for p in chain]

    mains_map = CM._mains_factory()
    w_id = (id_sea12, 0.0, 0.0, 1.0)

    def wash_tri(a, b, c_):
        t3 = _up_tri4([(p, (0.0, 1.0, 0.0), (0.0, 0.0), w_id) for p in (a, b, c_)])
        ccx = sum(v[0][0] for v in t3) / 3.0
        ccz = sum(v[0][2] for v in t3) / 3.0
        uvf = mains_map(_cell_of(ccx, ccz))
        return [(v[0], v[1], uvf(v[0][0], v[0][2]), v[3]) for v in t3]

    wash = []
    ia = ib = 0
    while ia < len(W) - 1 or ib < len(stair) - 1:
        adv_a = ia < len(W) - 1 and (
            ib >= len(stair) - 1
            or _d2(W[ia + 1], stair[ib]) <= _d2(W[ia], stair[ib + 1]))
        if adv_a:
            t = (W[ia], W[ia + 1], stair[ib])
            ia += 1
        else:
            t = (W[ia], stair[ib + 1], stair[ib])
            ib += 1
        if _area2(t) > 1e-9:
            wash.append(wash_tri(*t))
    # the demoted full wash cells
    for c in sorted(wash_full):
        for t3 in lattice_quad(c, w_id):
            uvf = mains_map(c)
            wash.append([(v[0], v[1], uvf(v[0][0], v[0][2]), v[3]) for v in t3])

    # --- THE COVERAGE CUT (the z-fight law): the sea4 plane loses ONLY cells the
    # ladder FULLY owns; wash tris straying into kept-plane cells are dropped
    # (coplanar water over the plane shimmers). The pinch tapers therefore keep
    # deep water under them -- the flanking wall+sea4 arrangement.
    cand = crossed | ring1 | ring5 | wash_full

    def _fully_covered(c, tris):
        (ci, cj) = c
        for si in range(4):
            for sj in range(4):
                px = ci * CELL + (si + 0.5) * CELL / 4.0
                pz = cj * CELL + (sj + 0.5) * CELL / 4.0
                hit = False
                for t3 in tris:
                    (a, b, c3) = (v[0] for v in t3)
                    d = (b[2] - c3[2]) * (a[0] - c3[0]) + (c3[0] - b[0]) * (a[2] - c3[2])
                    if abs(d) < 1e-9:
                        continue
                    w0 = ((b[2] - c3[2]) * (px - c3[0]) + (c3[0] - b[0]) * (pz - c3[2])) / d
                    w1 = ((c3[2] - a[2]) * (px - c3[0]) + (a[0] - c3[0]) * (pz - c3[2])) / d
                    if w0 >= -.02 and w1 >= -.02 and 1 - w0 - w1 >= -.02:
                        hit = True
                        break
                if not hit:
                    return False
        return True

    solid = foam + sea1_tris + sea5_tris
    sand_cover = [[((c5[0], c5[1], c5[2]), None, None, None) for c5 in corners]
                  for corners, fn in terrain_items]
    wash_keep = list(wash)
    cut = set()
    for _ in range(6):
        allc = solid + sand_cover + wash_keep
        cut = {c for c in cand if _fully_covered(c, allc)}
        kept = [t3 for t3 in wash_keep
                if _cell_of(sum(v[0][0] for v in t3) / 3.0,
                            sum(v[0][2] for v in t3) / 3.0) in cut]
        if len(kept) == len(wash_keep):
            break
        wash_keep = kept
    # RAISE, DON'T DROP (round-1 playtest: the dropped taper tris left a hard
    # straight cut in the light band at each beach side): wash tris over KEPT
    # plane cells stay, lifted 0.02u above the sea4 plane (in-family -- stock
    # wash spans y 0..0.195; per-tri vert entries, so no cracks) -- the wash
    # tapers to the pinch as a FADE over deep water, the flanking arrangement.
    kept_keys = {id(t3) for t3 in wash_keep}
    raised = []
    for t3 in wash:
        if id(t3) in kept_keys:
            raised.append(t3)
        else:
            raised.append([((v[0][0], max(v[0][1], SEA_Y + 0.1), v[0][2]),
                            v[1], v[2], v[3]) for v in t3])
    wash = raised
    # the taper FOAM's W edge approaches y=0 asymptotically over the kept plane --
    # the round-3 shimmer sliver; lift its low verts clear (per-tri entries, opaque
    # ribbon: the 0.05 step is sub-visible)
    lifted = []
    for t3 in foam:
        c = _cell_of(sum(v[0][0] for v in t3) / 3.0, sum(v[0][2] for v in t3) / 3.0)
        if c in cut:
            lifted.append(t3)
        else:
            lifted.append([((v[0][0], max(v[0][1], SEA_Y + 0.05), v[0][2]),
                            v[1], v[2], v[3]) for v in t3])
    foam = lifted

    # water tris must stay single-block too (lattice cells align; the zip could cross)
    wblks = {(math.floor(v[0][0] / BLOCK), math.floor(-v[0][2] / BLOCK))
             for part in (foam, wash, sea1_tris, sea5_tris) for t3 in part for v in t3}
    if len(wblks - {blk}) > 0:
        raise ValueError(f"--beach: water tris span blocks {sorted(wblks)} -- v1 is "
                         f"single-block; move the arc off the border")

    return {"terrain": terrain_items, "foam": foam, "wash": wash,
            "sea1": sea1_tris, "sea5": sea5_tris,
            "sea4_cut": cut,
            "wall_skip": {(idxs[k], idxs[k + 1]) for k in range(ncol)},
            "berm_cells": sorted(berm_cells), "block": blk, "arc": arc,
            "chains": {"L": L, "S": S, "W": W}, "sand_fam": fam["name"],
            "pins_from": tuple(pins_from)}


def _topo(t3):
    from .extract import decode_id
    return decode_id(int(round(t3[0][3][0])))["topograph"]


def _area2(tri):
    (a, b, c) = tri
    return abs((b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2]))


def _d2(p, q):
    return (p[0] - q[0]) ** 2 + (p[2] - q[2]) ** 2


def _up_tri(a, b, c):
    ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
    return (a, b, c) if ny > 0 else (a, c, b)


def _up_tri4(t3):
    (a, b, c) = (v[0] for v in t3)
    ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
    return list(t3) if ny > 0 else [t3[0], t3[2], t3[1]]


def _pip(px, pz, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        (x1, z1), (x2, z2) = poly[i], poly[(i + 1) % n]
        if (z1 > pz) != (z2 > pz):
            xin = x1 + (pz - z1) / (z2 - z1) * (x2 - x1)
            if px < xin:
                inside = not inside
    return inside
