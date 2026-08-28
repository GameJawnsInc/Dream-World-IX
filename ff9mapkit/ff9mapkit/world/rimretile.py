"""ff9mapkit.world.rimretile -- terminate a carried island's CROPPED SHALLOW RING.

Carrying a coastal island standalone necessarily crops the neighbour blocks that hosted its
sea5 transition rings, so the shallow band ends against the open-ocean deep with no
transition: a hard ``sea3|deep`` seam along a straight block-frame line. The wang-carry gate
flags exactly this and has always named the remedy -- *"re-tile the rim"* -- while pointing
at a study script hardcoded to one island. This is that remedy as a real operator.

THE GOVERNING LAW, learned the expensive way: **CARRY THE TILES, DO NOT AUTHOR THEM.**
Replacement uvs are HARVESTED byte-exact from the donor's own sea5 termination tiles, and a
deep-set with no verbatim donor tile REFUSES rather than being synthesized. Two authored-uv
attempts reached playtests first -- a per-triangle quadrant choice rendered the whole sheet
as a checkerboard, and a tile-anchored uv stretched every coast-cut triangle -- and both
passed every geometry gate, because geometry was never what was wrong.

**The edit is a pure REPARTITION.** Each flagged quad keeps its exact verts, normals and
tangent-x topo; only the uv rect and the containing Sea file change. The (verts, topo)
multiset is therefore identical before and after -- gated here, not asserted -- so walkmesh
raycast, coverage and boat legality are preserved by construction.

**It must ITERATE.** The deep-set derivation reads the shade map, and converting sea3->sea5
changes that map, so neighbours' deep-sets shift underneath a single pass. In-game proven on
the Path D isthmus: pass 1 leaves 20 residual mismatches, and the fixed point arrives at
pass 2.

In-game proven 2026-08-04 (the isthmus, donor (6,6)+2x2 at Disc9 (14,12)): the owner's
verdict was *"that's a pass, the hard edge became a series of Wang tiles"*, with the
hard-seam class -- tiles whose uv UNDER-covers the deep they face -- measured 3 -> 0.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from . import water as W
from .extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN, decode_id

SEA = ("sea3", "sea4", "sea5")
G = 16
CELL = 4.0
DIRV = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}


def cell_of(v):
    return int(v[0] // CELL), int((-v[2]) // CELL)


def corner_of(v, i, j):
    return (round((v[0] - i * CELL) / CELL), round((-v[2] - j * CELL) / CELL))


def part_tris(bm):
    """``[[(i,j), [(pos,nrm,uv,tan) x3], topo], ...]`` -- one entry per triangle."""
    out = []
    if bm is None:
        return out
    V, N, U, T, fi = bm.verts, bm.normals, bm.uvs, bm.tangents, bm.flat_index
    for t in range(len(fi) // 3):
        idx = fi[3 * t:3 * t + 3]
        i, j = cell_of([sum(V[k][0] for k in idx) / 3, 0, sum(V[k][2] for k in idx) / 3])
        out.append([(i, j),
                    [(tuple(V[k]), tuple(N[k]), tuple(U[k]), tuple(T[k])) for k in idx],
                    decode_id(int(round(T[idx[0]][0])))["topograph"]])
    return out


def build_part(tris, name, bx, by, disc, lod="0_1"):
    """Rebuild a flat/unindexed BlockMesh; an UNCHANGED tri list round-trips byte-identically."""
    pos, nrm, uv, tan, flat, tri_idx = [], [], [], [], [], []
    vi = 0
    for tri in tris:
        base = vi
        for (p, n, u, t) in tri:
            pos.append([float(c) for c in p])
            nrm.append([float(c) for c in n])
            uv.append([float(u[0]), float(u[1])])
            tan.append([float(c) for c in t])
            flat.append(vi)
            vi += 1
        tri_idx.append([base, base + 1, base + 2])
    return BlockMesh(name=f"Block[{bx}][{by}] {name}", disc=disc, x=bx, y=by, lod=lod,
                     vcount=vi, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2),
                               CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=tri_idx, raw_vbuf=b"", raw_ibuf=b"",
                     use32=True, submeshes=[])


def harvest_variants(donors, *, disc: int = 1, lod: str = "0_1", game=None) -> dict:
    """``{(strip, rot): {corner: (u, v)}}`` -- the donors' OWN sea5 termination tiles.

    THE VERBATIM SOURCE. ``water.DEEPSET2TILE`` is only the validator that says which
    variant a deep-set needs; the uv values themselves are never computed here. A donor
    block with no sea5 part is skipped, and a variant whose instances disagree is dropped
    rather than averaged -- an inconsistent variant is not a vocabulary.
    """
    from . import extract as X
    per = defaultdict(list)
    for (dx, dy) in donors:
        try:
            bm = X.read_block(dx, dy, disc=disc, lod=lod, part="sea5", game=game)
        except ValueError as e:
            if "mesh not found" not in str(e):
                raise
            continue
        corners = defaultdict(dict)
        for tri in bm.tris:
            i, j = cell_of([sum(bm.verts[k][0] for k in tri) / 3, 0,
                            sum(bm.verts[k][2] for k in tri) / 3])
            for k in tri:
                corners[(i, j)][corner_of(bm.verts[k], i, j)] = tuple(bm.uvs[k])
        for d in corners.values():
            cls = W.classify_sea5_cell(d, min_corners=4)
            if cls is not None:
                per[(cls[0], cls[1])].append(
                    {c: d[c] for c in ((0, 0), (1, 0), (1, 1), (0, 1))})
    out = {}
    for key, maps in per.items():
        rep = maps[0]
        spread = max((abs(m[c][k] - rep[c][k]) for m in maps for c in rep for k in (0, 1)),
                     default=0.0)
        if spread <= 1e-4:
            out[key] = rep
    return out


def _neighbour(shade, water, island, bx, by, i, j, d):
    di, dj = DIRV[d]
    ni, nj, nbx, nby = i + di, j + dj, bx, by
    if ni < 0:
        nbx, ni = bx - 1, G - 1
    elif ni >= G:
        nbx, ni = bx + 1, 0
    if nj < 0:
        nby, nj = by - 1, G - 1
    elif nj >= G:
        nby, nj = by + 1, 0
    if (nbx, nby) in shade:
        return shade[(nbx, nby)][ni][nj], water[(nbx, nby)][ni][nj]
    return "ring", True                       # off-island: the generic deep ocean ring


def _is_deep(sh, wet):
    # LAND-AWARENESS: a 'sea4' shade with no water triangle is a coast, not deep water.
    return sh == "ring" or (sh == "sea4" and wet)


def deepset(shade, water, island, bx, by, i, j) -> frozenset:
    """The land-aware marching-band deep-set: which sides face genuine deep water."""
    return frozenset(d for d in "NESW"
                     if _is_deep(*_neighbour(shade, water, island, bx, by, i, j, d)))


#: THE OPPOSITE-PINCH RULE (2026-08-05, the horseshoe carry). A crop line can leave a shallow
#: quad pinched between deep on OPPOSITE sides, and ``DEEPSET2TILE`` has no such key: the wang
#: alphabet is closed at 12 (4 tips, 4 corners, 4 triples) -- an opposite pair is unrepresentable
#: BY CONSTRUCTION, so no harvest, however wide, can ever cover it. Stock SHIPS the shape
#: (censused disc-1 map-wide: 5 EW-pinched sea5 cells, 0 NS, 0 4-deep) and resolves it 5/5 with a
#: 3-deep tile CONTAINING the pair -- (2,10)@(12,9)=ESW, (4,15)@(3,0)=ESW, (4,15)@(12,5)=ENW,
#: (5,13)@(6,12)=ESW, (6,6)@(6,12)=ENW -- never a 1-deep tip. That direction is also the only safe
#: one under this module's own taxonomy: a superset scores as ``over`` (the owner-accepted
#: gradient, :func:`seam_report`), a subset as ``under`` (the hard-seam DEFECT). The degradation
#: mechanism itself is not new -- :func:`water._repro_deepset` has always folded an invalid set
#: onto the nearest representable tile; only its opposite-channel CHOICE (a single tip, i.e. an
#: under) is contradicted here by stock's own complete population. The extra side is picked to
#: avoid pointing a new deep-facing quarter at a ``sea3`` neighbour; the default order (S for an
#: EW pinch, its 90-degree rotation W for NS) follows stock's 3:2 ESW-over-ENW majority.
#:
#: ⚠ **THE FOLD IS UNILATERAL AND THAT IS NOT WHAT STOCK DOES** (2026-08-05, the owner's
#: *"missed wangs -- 2 single-edged touching each other then a third with a mis-aligned edge"* at
#: world (513,-689)/(513,-760)). Re-reading the same 5 stock pinches WITH their neighbours: in
#: 4/4 readable cases the neighbour on the added side paints that shared edge deep TOO -- an
#: EW pinch at (4,15)@(12,5) paints ENW while (12,4) above it paints ES though its own geometry
#: is only E; (5,13)@(6,12) paints ESW while (6,13) paints EN; (6,6)@(6,12) paints ENW while
#: (6,11) paints SW; (4,15)@(3,0) paints ESW while (3,1) paints ENS off an EMPTY geometric set.
#: The pinch resolution is MUTUAL: two tiles agree to close the channel across one edge. A
#: unilateral fold declares deep against a neighbour still painting shallow -- a hard texture
#: step, which is exactly what reached that playtest. And where NEITHER neighbour can absorb the
#: extra side (both already 3-deep -- a shallow strip one cell wide), *no* painting exists:
#: stock ships ZERO deep-enclosed shallow components and ZERO 1-wide shallow runs longer than one
#: cell (93 EW + 92 NS runs map-wide, every one length 1). The lawful answer there is not a tile
#: at all, it is to let the deep CLOSE over the strip. Both conditions are now MEASURED and
#: reported -- :func:`edge_disagreements` and :func:`unpaintable_slivers`, surfaced by
#: :func:`rim_retile` and printed by ``world-rim-retile`` -- so the class is loud at the call
#: site instead of invisible until a playtest.
_PINCH_PREFS = {frozenset("EW"): "SN", frozenset("NS"): "WE"}

_OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}


def representable(ds, shade, water, island, bx, by, i, j) -> frozenset:
    """Fold an unrepresentable deep-set onto the wang alphabet -- see :data:`_PINCH_PREFS`.

    Representable sets pass through untouched. A 4-deep set is left alone (it is not a pinch;
    :func:`plan_rim` targets it at ``sea4`` and :func:`uncovered` still refuses it, unchanged).
    """
    if not ds or ds in W.DEEPSET2TILE:
        return ds
    prefs = _PINCH_PREFS.get(frozenset(ds))
    if prefs is None:
        return ds
    add = next((d for d in prefs
                if _neighbour(shade, water, island, bx, by, i, j, d)[0] != "sea3"), prefs[0])
    return frozenset(set(ds) | {add})


def _grids(cells):
    from .transplant import _sea_shade_grid, _sea_water_grid
    shade = {c: _sea_shade_grid(v) for c, v in cells.items()}
    water = {c: _sea_water_grid(v) for c, v in cells.items()}
    return shade, water


def _refuse_seam_span(cells):
    """The rim fold is seam-blind by construction: ``_neighbour`` steps ``bx +- 1`` with no
    modulo, so at the interior 23|0 boundary BOTH sides read the missing neighbour as the
    generic deep-ocean ring, and the frame detection inverts for a footprint like {22,23,0,1}.
    Toroidalizing the fold is a follow-on rung; until then a seam-spanning cell set refuses
    loudly instead of silently retiling against a phantom ocean. Guards plan_rim (the write
    lane) AND unpaintable_slivers (the audit -- a wrong audit is how gates lie)."""
    cols = {c[0] for c in cells}
    if 0 in cols and 23 in cols:
        raise ValueError(
            "cell set spans the wrapped column seam 23|0: rim folding steps bx+-1 linearly and "
            "would treat the interior seam as open-ocean frame on both sides. Retile each side "
            "of the seam separately, or make _neighbour/on_frame toroidal first (THE SEAM-WRAP "
            "arc, 2026-08-27 -- the world-island mint lane is wrap-aware; this verb is not yet).")


def plan_rim(cells) -> dict:
    """``{(bx,by): {(i,j): (target_part, deepset)}}`` for every shallow quad that NEEDS
    re-tiling: an outer-frame quad (the original cropped-rim class -- an unshifted carry
    lands its crop lines on the island bbox frame), OR a MEASURED seam anywhere in the
    cells -- a sea3 quad touching deep (stock abuts sea3 to deep NOWHERE map-wide), or a
    sea5 whose encoded deep-set mismatches its geometric one. THE CROP-SEAM WIDENING
    (2026-08-04): a cluster-SHIFTED carry lands its crop lines MID-CELL, where the
    frame-only audit never looked -- measured on the composed dot pair's channel."""
    _refuse_seam_span(cells)
    island = list(cells)
    shade, water = _grids(cells)
    xs = sorted({c[0] for c in island})
    ys = sorted({c[1] for c in island})

    # THE SHORE SCOPE (2026-08-04, the bent crescent's beach): inside a live shore
    # system, sea4 lawfully runs UNDER the shallow bands (the sea4-under-land law), so
    # tile-local "sea3 touches deep" arithmetic false-flags lawful ladder tiles -- the
    # measured-seam rules apply only AWAY from shore (no land / beach1 / sea1 / sea2 in
    # the 8-neighbourhood). Genuine crop seams (the dot pair's channel) are open-water.
    def _bins(bm):
        g = [[False] * G for _ in range(G)]
        if bm is None:
            return g
        for tri in bm.tris:
            i = int((sum(bm.verts[q][0] for q in tri) / 3) // CELL)
            j = int((-sum(bm.verts[q][2] for q in tri) / 3) // CELL)
            if 0 <= i < G and 0 <= j < G:
                g[i][j] = True
        return g
    shore = {}
    for c in island:
        g = [[False] * G for _ in range(G)]
        for p in ("sea1", "sea2", "beach1"):
            b = _bins(cells[c].get(p))
            for i in range(G):
                for j in range(G):
                    g[i][j] = g[i][j] or b[i][j]
        for i in range(G):
            for j in range(G):
                g[i][j] = g[i][j] or not water[c][i][j]     # a dry cell is land
        shore[c] = g

    def _near_shore(bx, by, i, j):
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                ni, nj, nbx, nby = i + di, j + dj, bx, by
                if ni < 0:
                    nbx, ni = bx - 1, G - 1
                elif ni >= G:
                    nbx, ni = bx + 1, 0
                if nj < 0:
                    nby, nj = by - 1, G - 1
                elif nj >= G:
                    nby, nj = by + 1, 0
                if (nbx, nby) in shore and shore[(nbx, nby)][ni][nj]:
                    return True
        return False

    plan = defaultdict(dict)
    for (bx, by) in island:
        enc5 = _sea5_deepsets(cells[(bx, by)])
        for i in range(G):
            for j in range(G):
                if not water[(bx, by)][i][j]:
                    continue
                sh = shade[(bx, by)][i][j]
                if sh not in ("sea3", "sea5"):
                    continue
                ds = deepset(shade, water, island, bx, by, i, j)
                if not ds:
                    continue
                # an opposite pinch has no wang key at all -- fold it onto the containing
                # triple stock itself uses (THE OPPOSITE-PINCH RULE). Planning only: the
                # seam census below keeps reading the RAW geometry, so the fold shows up
                # honestly as under -> over, never as a masked defect.
                ds = representable(ds, shade, water, island, bx, by, i, j)
                on_frame = ((bx == xs[0] and i == 0) or (bx == xs[-1] and i == G - 1)
                            or (by == ys[0] and j == 0) or (by == ys[-1] and j == G - 1))
                # UNDER only -- the defect class (a tile facing deep with no transition
                # there). An OVER (a transition facing shallow) is a needless gradient,
                # owner-accepted at 20/82 on the proven isthmus; converting it churned
                # 23 coast tiles into visible shards on the bent crescent (2026-08-04).
                seam = (not _near_shore(bx, by, i, j)
                        and (sh == "sea3"
                             or not frozenset(ds) <= frozenset(enc5.get((i, j), ()))))
                if not (on_frame or seam):
                    continue
                plan[(bx, by)][(i, j)] = ("sea4" if len(ds) == 4 else "sea5", ds)
    return dict(plan)


def uncovered(plan, variants) -> list:
    """Deep-sets the plan needs that the donors' own vocabulary cannot supply, VERBATIM."""
    need = {ds for cs in plan.values() for (_p, ds) in cs.values() if ds}
    out = []
    for ds in sorted(need, key=lambda s: "".join(sorted(s))):
        opts = W.DEEPSET2TILE.get(ds, [])
        if not opts or not [o for o in opts if tuple(o) in variants]:
            out.append("".join(sorted(ds)))
    return out


def _tile_uv(uvmap, p, i, j):
    """The variant's map evaluated AT the vert: bilinear over the 4 harvested corner uvs
    at the vert's fractional position in the tile. On a full tile's corner verts this is
    bit-identical to the corner lookup (fractions are exactly 0/1 on the lattice); on a
    COAST-CUT triangle's mid-tile verts it is the tile's real axis-aligned wang-rect map
    -- the corner SNAP smeared them (the stretched-face playtest, 2026-08-04; the module
    docstring's second authored-uv failure, re-created from the inside by the crop-seam
    widening planning partial tiles)."""
    fx = min(max((p[0] - i * CELL) / CELL, 0.0), 1.0)
    fz = min(max((-p[2] - j * CELL) / CELL, 0.0), 1.0)
    u00, u10 = uvmap[(0, 0)], uvmap[(1, 0)]
    u11, u01 = uvmap[(1, 1)], uvmap[(0, 1)]
    return ((u00[0] * (1 - fx) + u10[0] * fx) * (1 - fz)
            + (u01[0] * (1 - fx) + u11[0] * fx) * fz,
            (u00[1] * (1 - fx) + u10[1] * fx) * (1 - fz)
            + (u01[1] * (1 - fx) + u11[1] * fx) * fz)


def apply_rim(cells, plan, variants, *, disc: int, lod: str = "0_1"):
    """Repartition the flagged quads. Returns ``({(bx,by): {part: BlockMesh}}, n_quads)``."""
    from .transplant import _sea_shade_grid
    post, n = {}, 0
    for (bx, by), cellplan in plan.items():
        pre = cells[(bx, by)]
        shade = _sea_shade_grid(pre)
        buckets = {p: part_tris(pre.get(p)) for p in SEA}
        for (i, j), (_tp, ds) in cellplan.items():
            src = shade[i][j]
            uvmap = variants[tuple(W.DEEPSET2TILE[ds][0])]
            moved = [e for e in buckets[src] if e[0] == (i, j)]
            if not moved:
                continue
            buckets[src] = [e for e in buckets[src] if e[0] != (i, j)]
            for [c, verts, topo] in moved:
                nv = []
                for (p, nr, _u, t) in verts:
                    nv.append((p, nr, _tile_uv(uvmap, p, i, j), t))
                buckets["sea5"].append([c, nv, topo])
            n += 1
        post[(bx, by)] = {p: build_part([e[1] for e in buckets[p]], p.capitalize(),
                                        bx, by, disc, lod)
                          for p in SEA if pre.get(p) is not None}
    return post, n


def repartition_ok(before, after) -> bool:
    """THE NON-REGRESSION GATE: geometry must be untouched -- only shade may change."""
    def ms(d):
        return Counter((tuple(round(x, 4) for x in v[0]), t)
                       for p in SEA if d.get(p) is not None
                       for [_i, vs, t] in part_tris(d[p]) for v in vs)
    return all(ms(before[c]) == ms(after[c]) for c in after)


def seam_report(cells) -> dict:
    """``under`` is the DEFECT: a tile facing deep with no transition there IS a hard seam.

    ``over`` (a transition facing shallow) is a gradient where none is needed -- a much
    subtler class, owner-accepted at 20/82 on the proven isthmus.
    """
    shade, water = _grids(cells)
    island = list(cells)
    under = over = total = 0
    for c in island:
        for (i, j), enc in _sea5_deepsets(cells[c]).items():
            geo = deepset(shade, water, island, c[0], c[1], i, j)
            if not geo:
                continue
            total += 1
            if frozenset(enc) != frozenset(geo):
                if not frozenset(geo) <= frozenset(enc):
                    under += 1
                else:
                    over += 1
    return dict(tiles=total, under=under, over=over)


def _painted(shade, water, uvds, bx, by, i, j):
    """What a cell's TEXTURE declares deep, which is the only question the renderer asks:
    a ``sea4`` mains tile paints deep on all four sides, a ``sea3`` on none, a ``sea5`` on the
    sides its wang tile encodes. ``None`` = nothing to compare (dry land, off-island, or a
    coast-cut cell whose tile fits no pure rotation)."""
    if (bx, by) not in shade:
        return set("NESW")                            # off-island: the generic deep ocean ring
    if not water[(bx, by)][i][j]:
        return None
    sh = shade[(bx, by)][i][j]
    if sh == "sea4":
        return set("NESW")
    if sh == "sea3":
        return set()
    ds = uvds[(bx, by)].get((i, j))
    return None if ds is None else set(ds)


def edge_disagreements(cells) -> list:
    """Shared edges whose two tiles CONTRADICT each other -- one paints deep right up to the
    line, the other paints shallow. That is a hard texture step, and it is the defect class the
    owner reads as a *"mis-aligned edge"*.

    THE ORACLE (stock disc 1, 214 sea blocks, 60,689 shared edges): 60,683 agree, **6 disagree
    = 0.010%**, and not one of the six is a ``sea5|sea5`` pair. So a transition tile contradicting
    another transition tile is a shape the real game never ships, at any coordinate.

    Distinct from :func:`seam_report`, which scores each tile against its own GEOMETRY. A pair of
    tiles can each be a defensible answer to its own neighbourhood and still contradict each
    other; only this census asks the neighbour. Returns
    ``[((bx, by, i, j), dir, painted_here, painted_there), ...]``.
    """
    shade, water = _grids(cells)
    uvds = {c: _sea5_deepsets(v) for c, v in cells.items()}
    out = []
    for (bx, by) in sorted(cells):
        for i in range(G):
            for j in range(G):
                a = _painted(shade, water, uvds, bx, by, i, j)
                if a is None:
                    continue
                for d in ("E", "S"):                   # each shared edge visited once
                    di, dj = DIRV[d]
                    ni, nj, nbx, nby = i + di, j + dj, bx, by
                    if ni >= G:
                        nbx, ni = bx + 1, 0
                    if nj >= G:
                        nby, nj = by + 1, 0
                    if (nbx, nby) not in cells:
                        continue                       # the ring is deep by definition, and the
                        #                                frame's own facing is scored from inside
                    b = _painted(shade, water, uvds, nbx, nby, ni, nj)
                    if b is None:
                        continue
                    if (d in a) != (_OPP[d] in b):
                        out.append(((bx, by, i, j), d,
                                    "".join(sorted(a)) or "-", "".join(sorted(b)) or "-"))
    return out


def unpaintable_slivers(cells) -> list:
    """Pinched shallow cells that NO wang tile can serve -- see :data:`_PINCH_PREFS`.

    A cell whose geometric deep-set is an opposite pair is representable only as a MUTUAL fold:
    the neighbour on the added side must paint that edge deep too, so its own deep-set gains the
    opposite direction and must STILL be a wang key. When neither neighbour on the pinch's open
    axis can absorb that (both are already 3-deep), the cell sits in a shallow strip one cell
    wide -- a shape stock ships nowhere (0 deep-enclosed shallow components; 185 one-wide runs
    map-wide, all of length 1). The lawful remedy is to let the deep close over the strip
    (repartition it to ``Sea4``), not to fold a tile onto it. Returns
    ``[((bx, by, i, j), geometric_deepset), ...]``.
    """
    _refuse_seam_span(cells)
    island = list(cells)
    shade, water = _grids(cells)
    out = []
    for (bx, by) in sorted(cells):
        for i in range(G):
            for j in range(G):
                if not water[(bx, by)][i][j] or shade[(bx, by)][i][j] not in ("sea3", "sea5"):
                    continue
                ds = deepset(shade, water, island, bx, by, i, j)
                if not ds or ds in W.DEEPSET2TILE:
                    continue
                prefs = _PINCH_PREFS.get(frozenset(ds))
                if prefs is None:
                    continue                           # a 4-deep set: not a pinch, see representable
                absorbs = False
                for d in prefs:
                    di, dj = DIRV[d]
                    ni, nj, nbx, nby = i + di, j + dj, bx, by
                    if ni < 0:
                        nbx, ni = bx - 1, G - 1
                    elif ni >= G:
                        nbx, ni = bx + 1, 0
                    if nj < 0:
                        nby, nj = by - 1, G - 1
                    elif nj >= G:
                        nby, nj = by + 1, 0
                    if (nbx, nby) not in cells or not water[(nbx, nby)][ni][nj]:
                        continue
                    if shade[(nbx, nby)][ni][nj] not in ("sea3", "sea5"):
                        continue
                    nds = deepset(shade, water, island, nbx, nby, ni, nj)
                    if frozenset(set(nds) | {_OPP[d]}) in W.DEEPSET2TILE:
                        absorbs = True
                        break
                if not absorbs:
                    out.append(((bx, by, i, j), "".join(sorted(ds))))
    return out


def _sea5_deepsets(parts) -> dict:
    """``{(i,j): deepset}`` read back from each sea5 tile's own uv."""
    bm = parts.get("sea5")
    out = {}
    if bm is None:
        return out
    corners = defaultdict(dict)
    for tri in bm.tris:
        i, j = cell_of([sum(bm.verts[k][0] for k in tri) / 3, 0,
                        sum(bm.verts[k][2] for k in tri) / 3])
        for k in tri:
            corners[(i, j)][corner_of(bm.verts[k], i, j)] = tuple(bm.uvs[k])
    for (i, j), d in corners.items():
        # THE ARITY FIX (audit rec 7): this reader used to fit WHATEVER corners existed --
        # a 2-corner sliver got the first rotation in ROTS order, an arbitrary answer the
        # rim audit then iterated to a fixed point on. Now the shared classifier with the
        # carry gate's explicit >=3 relaxation: the two deepset readers agree by construction.
        ds = W.sea5_deepset_of(d, min_corners=3, min_uv_span=1e-6)
        if ds is not None:
            out[(i, j)] = ds
    return out


def rim_retile(mod_folder, cells_xy, donors, *, disc: int = 1, target_disc=None,
               lod: str = "0_1", game=None, apply: bool = False, max_passes: int = 6):
    """Re-tile a deployed island's cropped shallow rim. Returns a report dict.

    ``cells_xy`` are the DEPLOYED target cells; ``donors`` the blocks the island was carried
    from (the verbatim vocabulary). Iterates to a fixed point -- see the module docstring:
    one pass does not converge, because retiling changes the shade map the next pass reads.
    """
    from . import mesh as M
    from .. import config
    td = disc if target_disc is None else int(target_disc)
    root = config.find_game_path(game) / mod_folder / "FF9_Data" / "WorldMap" / f"Disc{td}" / lod

    def load():
        out = {}
        for (bx, by) in cells_xy:
            d = {}
            for part in SEA:
                p = root / f"r{by}" / f"Block[{bx}][{by}] {part.capitalize()}.ff9mesh"
                if p.exists():
                    d[part] = M.blockmesh_from_ff9mesh(str(p), disc=td, x=bx, y=by,
                                                       lod=lod, part=part)
            out[(bx, by)] = d
        return out

    variants = harvest_variants(donors, disc=disc, lod=lod, game=game)
    if not variants:
        return dict(refused="no sea5 termination tiles could be harvested from the donors "
                            "-- there is no verbatim vocabulary to re-tile from")
    cells = load()
    if not any(v.get("sea3") or v.get("sea5") for v in cells.values()):
        return dict(refused="these cells carry no shallow ring -- nothing to re-tile")

    before = seam_report(cells)
    edges_before = len(edge_disagreements(cells))
    passes, total = [], 0
    for _k in range(max_passes):
        plan = plan_rim(cells)
        miss = uncovered(plan, variants)
        if miss:
            return dict(refused=f"deep-set(s) {miss} have no verbatim donor tile -- "
                                f"synthesizing one is what produced the checkerboard",
                        variants=len(variants))
        post, n = apply_rim(cells, plan, variants, disc=td, lod=lod)
        if not repartition_ok(cells, post):
            return dict(refused="repartition gate: geometry changed -- not a pure re-shade")
        passes.append(n)
        total += n
        after = {c: dict(cells[c], **post.get(c, {})) for c in cells}
        if seam_report(after) == seam_report(cells) and _k:
            break                                   # fixed point
        cells = after
        if len(passes) >= 2 and passes[-1] == passes[-2]:
            break
    # THE NEIGHBOUR-FACING GATE (2026-08-05, the east-frame mis-aligned edges). seam_report
    # scores each tile against its OWN geometry and was green (under 0) while the column shipped
    # three contradicting edges; only these two census the pair and the shape.
    contradictions = edge_disagreements(cells)
    rep = dict(variants=len(variants), passes=passes, quads=total,
               before=before, after=seam_report(cells),
               edges_disagreeing={"before": edges_before, "after": len(contradictions)},
               contradictions=contradictions, unpaintable=unpaintable_slivers(cells))
    if not apply:
        rep["dry_run"] = True
        return rep
    written = []
    for (bx, by), parts in cells.items():
        for part, bm in parts.items():
            p = root / f"r{by}" / f"Block[{bx}][{by}] {part.capitalize()}.ff9mesh"
            bak = p.with_suffix(".ff9mesh.prerim")
            if p.exists() and not bak.exists():
                import shutil
                shutil.copy2(p, bak)
            M.write_ff9mesh(bm, p)
            # ledger the in-place retile (same law as coastnav's stamp): without a row, the
            # next deploy_override at this cell+part refuses our own bytes as foreign
            M.record_ledger_write(p, cell=(bx, by), part=part.capitalize(), write_disc=td)
            written.append(p)
    rep["written"] = [str(p) for p in written]
    return rep
