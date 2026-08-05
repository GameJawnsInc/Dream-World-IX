#!/usr/bin/env py
r"""fix_fragment.py -- retire the CLIPPED DESERT WEDGE at world (473,-643), Disc9 block (7,10).

THE DEFECT (measured, not inferred)
-----------------------------------
`world-transplant --cell 5,10 --donor 5,15 --size 3x2` carried donor block (7,15) VERBATIM into
target block (7,10) (pure translation dz=+320; the deployed Terrain is byte-equivalent to stock
disc-1 Block[7][15] Terrain, 41 tris).  Stock (7,15) holds TWO disjoint land pieces:

  * 14 tris in its SW corner  -- the horseshoe's own mass, continuous into (6,15)/(7,16),
    both of which the carry took.  Kept.
  * 27 tris in its NE corner  -- a TOE of the big (7,14) landmass (474 tris) that pokes across
    the z=-1024 block border into (7,15).  Block (7,14) is OUTSIDE the 3x2 donor rect, so the
    rect's NORTH frame sliced this toe flat.

That severed toe is the wedge islet the owner stood on.  Its boundary audit:

    11 once-edges; 7 are ordinary waterline (y=0) edges -- lawful, THE FREE-BASE LAW --
     4 are an OPEN CUT in the z=-640 plane, up to y=3.164:
        (466.043, 0.000, -640) -> (467.348, 3.160, -640)     wall profile, up
        (467.348, 3.160, -640) -> (472.000, 3.164, -640)     plateau crest
        (472.000, 3.164, -640) -> (475.621, 3.039, -640)     plateau crest
        (475.621, 3.039, -640) -> (477.418, 0.000, -640)     wall profile, down

i.e. an 11.375u x 3.164u cross-section with NO face closing it.  That is the "bright flat
untextured pale face / raw cut face": the mesh is UNCLOSED there, so from the north the engine
draws whatever is behind the hole (backface-culled interior -> sea/sky/fog) in the shape of the
cut profile.  `--strips auto` DID arm the N tongue (the donor's own land reaches the rect's N
border), and the rect's re-partition then clipped it away at shift 0,0 -- so nothing ever
capped the slice.  Same class in Block[6][10] (18 tris, cut x 386.910..397.566) -- NOT fixed
here, see the report: its hole is flanked by sea4 on the west and sea3/sea5 on the east, so it
needs a 3-band mini-ladder, its own round.

THE FIX
-------
Drop the 27 severed tris and close the water lattice-lawfully.  Measured constraints:

  * plan-coverage census: block (7,10) has ZERO plan holes today; dropping the toe opens a
    110.4u2 hole that MUST be filled or the ground raycast misses (a vehicle wall + a
    see-through hole).
  * THE LATTICE ADJACENCY LAW ({3:1,3,5} {5:1,3,4,5} {4:4,5} -- sea3 NEVER touches sea4):
    the hole is flanked by sea5 in the z in [-644,-640] frame row and by sea3 below it.
    A plain excise-style sea4 fill is therefore UNLAWFUL here.  The band boundary on BOTH
    flanks already sits exactly on the z=-644 lattice line, so the fill is split there and
    each half simply CONTINUES the band its own flanks carry.  No new band, no new seam.
  * THE LATTICE LAW: both halves are emitted by `meshedit.lattice_patch` -- full 4u tiles plus
    per-cell-clipped margins, so no triangle spans a tile (the 2026-08-04 "faceted iceberg").
  * CARRY THE TILES, DO NOT AUTHOR THEM (rimretile's governing law): every uv rect, the sheet
    normal and the winding are BYTE-READ from block (7,10)'s own sea3 / sea5 (THE PER-BLOCK
    FLOAT DIALECT).  sea5's v-row is shade-bearing, so its rect is harvested from the two
    IMMEDIATE FLANK tiles of the hole in the same lattice row and the script REFUSES if they
    disagree.  sea3's mains quadrants are the free anti-tiling set (`water.assign_quadrants`).
  * THE SEA-SHEET LAWS: winding taken from the sheet (-1, plan cross), normal taken from the
    sheet ((-0.1211, 0.9785, 0.1665) -- NOT (0,1,0)).
  * THE T-VERTEX LAW: a lattice fill mints a vertex wherever a hole-boundary edge crosses a
    4u line, and the sheet triangle on the far side of that edge still spans it. Those
    neighbours are split at the fill's EXACT coordinates (3 in Sea3, 3 in Sea5).
  * coastnav: `stamp` only ever RAISES a class, so the removed shore's BELT(55)/KEEL(56)
    ring would survive as an invisible boat wall (55 and 56 are outside the Narciss legality
    mask {53,54,57}). The 27 such triangles in the removed shore's reach that are provably
    beyond every surviving land (> FRINGE_R 16 + BELT_R 3.5 + 3) are reset to open-sea 57,
    then `coastnav.stamp(policy="land-anywhere")` -- the verb and policy batch 2 deployed --
    is re-run over cell (7,10) to re-raise anything that still qualifies.

FILES TOUCHED (all under <game>/FF9CustomMap-world/FF9_Data/WorldMap/Disc9/0_1/r10/):
    Block[7][10] Terrain.ff9mesh   41 -> 14 tris   (the 27 severed tris dropped)
    Block[7][10] Sea3.ff9mesh     124 -> 139 tris  (+12 fill, +3 T-vertex splits)
    Block[7][10] Sea5.ff9mesh     151 -> 169 tris  (+15 fill, +3 T-vertex splits)
    Block[7][10] Sea4.ff9mesh     untouched at --nav-reset seal (the default)
NOT touched: every other cell, the .prerim rim-retile backups, and
`Block[6][11] Terrain.ff9mesh` -- the 31 event=1 armed tiles (armed_manifest.json) live there
and its sha256 is asserted unchanged.

USAGE
    py fix_fragment.py                       # --dry-run (default): read-only, full gate report
    py fix_fragment.py --scratch <DIR>       # stage a scratch game root, WRITE there, gate it
    py fix_fragment.py --write               # back up to C:\gd\Dream-World-IX\backups\ then write live
    py fix_fragment.py --nav-reset full      # ALSO clear the donor-inherited stale nav classes
    py fix_fragment.py --nav-reset none      # geometry only, leave every nav class alone

Every mode runs the same 22 gates first and REFUSES to write if any of them fails.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

KIT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\path-d-rung-6-handoff-e2535a\ff9mapkit")
if str(KIT) not in sys.path:
    sys.path.insert(0, str(KIT))

from ff9mapkit import config                                             # noqa: E402
from ff9mapkit.world import coastnav, meshedit as ME                     # noqa: E402
from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN, encode_id  # noqa: E402
from ff9mapkit.world.mesh import (blockmesh_from_ff9mesh, ff9mesh_bytes, override_relpath,
                                  validate_blockmesh, weld_audit, write_ff9mesh)  # noqa: E402

MOD_FOLDER = "FF9CustomMap-world"
DISC = 9
LOD = "0_1"
BX, BY = 7, 10                       # the block holding the fragment
OX, OZ = 64.0 * BX, -64.0 * BY       # its world origin (448.0, -640.0)
SPLIT_Z = -644.0                     # the sea5|sea3 band line BOTH flanks already carry
FRAME_Z = -640.0                     # the carry rect's north frame == the block's north border
BACKUP_ROOT = Path(r"C:\gd\Dream-World-IX\backups")
ARMED_FILE = ("r11", "Block[6][11] Terrain.ff9mesh")

# ---- the fragment FINGERPRINT: refuse if the deployed bytes are not what was diagnosed ----
EXPECT_TRIS = 27
EXPECT_TERRAIN_TRIS = 41
EXPECT_RING = [(466.043, -640.0), (469.625, -644.0), (476.0, -648.0), (480.0, -649.016),
               (484.664, -644.293), (485.773, -641.035), (480.0, -640.0), (477.418, -640.0),
               (475.621, -640.0), (472.0, -640.0), (467.348, -640.0)]
EXPECT_CUT_EDGES = 4
SEA_TOPO_OPEN = 57                   # coastnav's "open sea"; restamped right after

PARTS = ("Terrain", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Beach1")


# --------------------------------------------------------------------------- small helpers
def K(p):
    return (round(p[0], 3), round(p[1], 3), round(p[2], 3))


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def part_path(root: Path, bx: int, by: int, part: str) -> Path:
    return root / override_relpath(DISC, bx, by, LOD, part)


def read_part(root: Path, bx: int, by: int, part: str):
    p = part_path(root, bx, by, part)
    if not p.is_file():
        return None
    return blockmesh_from_ff9mesh(p, disc=DISC, x=bx, y=by, lod=LOD, part=part.lower())


def world_tris(bm, bx, by):
    """[(pos, nrm, uv, tan) x3] per tri, in WORLD coords."""
    ox, oz = 64.0 * bx, -64.0 * by
    V, N, U, T = bm.verts, bm.normals, bm.uvs, bm.tangents
    return [[((V[i][0] + ox, V[i][1], V[i][2] + oz), tuple(N[i]), tuple(U[i]), tuple(T[i]))
             for i in t] for t in bm.tris]


def build_part(tris_world, name, bx, by):
    """Rebuild an unindexed BlockMesh from WORLD tris (translated back to block-local).
    An unchanged tri list round-trips BYTE-IDENTICALLY (asserted by the gates)."""
    ox, oz = 64.0 * bx, -64.0 * by
    pos, nrm, uv, tan, flat, tri = [], [], [], [], [], []
    vi = 0
    for t in tris_world:
        base = vi
        for (p, n, u, g) in t:
            pos.append([float(p[0]) - ox, float(p[1]), float(p[2]) - oz])
            nrm.append([float(c) for c in n])
            uv.append([float(u[0]), float(u[1])])
            tan.append([float(c) for c in g])
            flat.append(vi)
            vi += 1
        tri.append([base, base + 1, base + 2])
    return BlockMesh(name=f"Block[{bx}][{by}] {name}", disc=DISC, x=bx, y=by, lod=LOD,
                     vcount=vi, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=tri, raw_vbuf=b"", raw_ibuf=b"", use32=True,
                     submeshes=[])


def plan_inside(px, pz, tri):
    (ax, _, az), (bx_, _, bz), (cx, _, cz) = (v[0] for v in tri)
    d1 = (px - bx_) * (az - bz) - (ax - bx_) * (pz - bz)
    d2 = (px - cx) * (bz - cz) - (bx_ - cx) * (pz - cz)
    d3 = (px - ax) * (cz - az) - (cx - ax) * (pz - az)
    return not (((d1 < 0) or (d2 < 0) or (d3 < 0)) and ((d1 > 0) or (d2 > 0) or (d3 > 0)))


def block_samples(bx, by, step):
    """Plan sample points inside block (bx,by). The in-cell offsets are DELIBERATELY not
    (step/2, step/2): stock sea tiles split on a 45-degree diagonal, so a half-step grid puts
    every other sample exactly ON that diagonal and the (inclusive) point-in-triangle test
    reports every one of them as double-covered -- 888 phantom 'overlaps' per block."""
    x0, z1 = 64.0 * bx, -64.0 * by
    n = int(64 / step)
    return [(x0 + i * step + 0.1371 * step, z1 - (j * step + 0.6197 * step))
            for i in range(n) for j in range(n)]


def coverage_holes(tris_by_part, bx, by, step=1.0):
    """Plan samples inside block (bx,by) covered by NO part -- the world-sheet hole census."""
    return [(px, pz) for (px, pz) in block_samples(bx, by, step)
            if not any(plan_inside(px, pz, t) for tris in tris_by_part.values() for t in tris)]


def once_edges(tris):
    c = Counter()
    for t in tris:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            c[tuple(sorted((K(t[a][0]), K(t[b][0]))))] += 1
    return [e for e, n in c.items() if n == 1]


def tri_stats(tris):
    ars, eds, wind = [], [], Counter()
    for t in tris:
        a, b, c = (v[0] for v in t)
        cr = (b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])
        wind[-1 if cr < 0 else 1] += 1
        ars.append(abs(cr) / 2.0)
        for p, q in ((a, b), (b, c), (c, a)):
            eds.append(math.dist((p[0], p[2]), (q[0], q[2])))
    ars.sort(); eds.sort()
    return dict(n=len(tris), area_med=ars[len(ars) // 2] if ars else 0.0,
                area_max=ars[-1] if ars else 0.0,
                edge_med=eds[len(eds) // 2] if eds else 0.0,
                edge_max=eds[-1] if eds else 0.0, winding=dict(wind))


# --------------------------------------------------------------------------- the diagnosis
def find_fragment(terr_world):
    """The severed component: a terrain vertex-component that TOUCHES the carry's north frame
    and is not the block's main mass.  Fail-closed on the fingerprint."""
    comps = ME.vertex_components(terr_world)
    hits = [c for c in comps if max(v[0][2] for t in c for v in t) >= FRAME_Z - 1e-6]
    if len(hits) != 1:
        raise SystemExit(f"REFUSE: expected exactly 1 frame-touching terrain component in "
                         f"({BX},{BY}), found {len(hits)} (of {len(comps)} components)")
    frag = hits[0]
    if len(frag) != EXPECT_TRIS:
        raise SystemExit(f"REFUSE: the frame-touching component has {len(frag)} tris, the "
                         f"diagnosis was {EXPECT_TRIS} -- the deployed bytes changed")
    cuts = [e for e in once_edges(frag)
            if not (abs(e[0][1]) < 1e-6 and abs(e[1][1]) < 1e-6)]
    if len(cuts) != EXPECT_CUT_EDGES:
        raise SystemExit(f"REFUSE: {len(cuts)} open-cut edges, expected {EXPECT_CUT_EDGES}")
    for e in cuts:
        if abs(e[0][2] - FRAME_Z) > 1e-6 or abs(e[1][2] - FRAME_Z) > 1e-6:
            raise SystemExit(f"REFUSE: an open-cut edge is not on the frame plane: {e}")
    ev = {int(round(t[0][3][0])) >> 14 for t in frag}
    if ev != {0}:
        raise SystemExit(f"REFUSE: the fragment carries event-armed tiles ({ev}) -- would "
                         f"destroy a trigger")
    return frag, cuts


def plan_ring(frag):
    """The fragment's PLAN boundary cycle (waterline arc + the frame chord).

    ROUND TO KEY, EMIT THE FLOAT (the sea-sheet E-2 law): the cycle is WALKED on rounded
    keys but every emitted point is the ORIGINAL float. Returning the key as geometry is
    how `boundary_cycles` once minted 16 near-miss weld pairs 0.00004u wide -- and this
    script reproduced it verbatim on its first run (4 introduced pairs, gate-caught)."""
    exact = {}
    for t in frag:
        for v in t:
            k = (round(v[0][0], 3), round(v[0][2], 3))
            e = (float(v[0][0]), float(v[0][2]))
            if exact.setdefault(k, e) != e:
                raise SystemExit(f"REFUSE: plan key {k} maps to two distinct floats "
                                 f"{exact[k]} / {e} -- the 3dp key is not injective here")
    adj = defaultdict(set)
    for a, b in once_edges(frag):
        pa, pb = (a[0], a[2]), (b[0], b[2])
        if pa != pb:
            adj[pa].add(pb)
            adj[pb].add(pa)
    bad = {k: v for k, v in adj.items() if len(v) != 2}
    if bad:
        raise SystemExit(f"REFUSE: the plan boundary is not a simple cycle: {bad}")
    start = min(adj)
    ring, prev, cur = [start], None, start
    while True:
        nxt = [p for p in adj[cur] if p != prev]
        prev, cur = cur, nxt[0]
        if cur == start:
            break
        ring.append(cur)
    if len(ring) != len(adj):
        raise SystemExit("REFUSE: the plan boundary has more than one cycle")
    if [(round(a, 3), round(b, 3)) for a, b in ring] != EXPECT_RING:
        raise SystemExit(f"REFUSE: plan ring changed.\n got {ring}\n want {EXPECT_RING}")
    return [exact[k] for k in ring]                 # EMIT THE FLOAT, not the key


# --------------------------------------------------------------------------- the dialect
def full_tile_rects(tris, row=None):
    """uv rects of tris that lie wholly inside one 4u lattice cell (optionally one z-row)."""
    out = Counter()
    for t in tris:
        xs = [v[0][0] for v in t]; zs = [v[0][2] for v in t]
        gx, gz = math.floor(min(xs) / 4.0), math.floor((-max(zs)) / 4.0)
        if math.floor(max(xs) / 4.0 - 1e-9) != gx or math.floor((-min(zs)) / 4.0 - 1e-9) != gz:
            continue
        if row is not None and gz != row:
            continue
        uu = [v[2][0] for v in t]; vv = [v[2][1] for v in t]
        out[(round(min(uu), 5), round(min(vv), 5), round(max(uu), 5), round(max(vv), 5))] += 1
    return out


def sheet_dialect(tris):
    nrm = Counter(tuple(round(c, 4) for c in t[0][1]) for t in tris).most_common(1)[0][0]
    w = Counter()
    for t in tris:
        a, b, c = (v[0] for v in t)
        w[-1.0 if ((b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])) < 0 else 1.0] += 1
    if len(w) != 1:
        raise SystemExit(f"REFUSE: mixed plan winding in a sea sheet: {dict(w)}")
    # the sheet's own tangent TAIL (y,z,w). lattice_patch defaults to w=1.0; stock/coastnav
    # sea tangents here are (idall,0,0,0) -- per-block dialect again, so take it from bytes.
    tail = Counter(tuple(round(c, 6) for c in t[0][3][1:]) for t in tris).most_common(1)[0][0]
    return nrm, next(iter(w)), tail


def retail_tangents(fill, tail):
    """Rewrite an emitted patch's tangent tail to the sheet's own (keeps tangent.x = IDALL)."""
    return [[(p, n, u, (g[0],) + tuple(tail)) for (p, n, u, g) in t] for t in fill]


def split_at_points(tris, pts, *, eps: float = 1e-6, rounds: int = 24):
    """Split existing sheet triangles at plan points lying strictly INSIDE one of their edges.

    THE T-VERTEX LAW: the lattice fill necessarily mints a vertex where a hole-boundary edge
    crosses a 4u line, and the sheet triangle on the OTHER side of that edge still spans it --
    a coplanar hairline pinhole no weld audit can see. Only we can fix it, so we split the
    neighbour. The new vertex takes the fill's EXACT (x, z) (so the two sides are identical by
    construction, not by tolerance), y/uv/normal lerped along the edge, and the parent's
    tangent verbatim (measured: 100% of this block's sea tris carry a uniform per-tri tangent,
    and tangent.x IS the IDALL)."""
    P = [(float(p[0]), float(p[1])) for p in pts]
    out, n_split = list(tris), 0
    for _ in range(rounds):
        grown, changed = [], 0
        for t in out:
            hit = None
            for a, b in ((0, 1), (1, 2), (2, 0)):
                pa, pb = t[a][0], t[b][0]
                dx, dz = pb[0] - pa[0], pb[2] - pa[2]
                L2 = dx * dx + dz * dz
                if L2 < 1e-12:
                    continue
                for w in P:
                    if (abs(w[0] - pa[0]) < 1e-9 and abs(w[1] - pa[2]) < 1e-9) or \
                       (abs(w[0] - pb[0]) < 1e-9 and abs(w[1] - pb[2]) < 1e-9):
                        continue
                    s = ((w[0] - pa[0]) * dx + (w[1] - pa[2]) * dz) / L2
                    if not (1e-6 < s < 1 - 1e-6):
                        continue
                    if abs((w[0] - pa[0]) * dz - (w[1] - pa[2]) * dx) / math.sqrt(L2) >= eps:
                        continue
                    hit = (a, b, w, s)
                    break
                if hit:
                    break
            if hit is None:
                grown.append(t)
                continue
            a, b, w, s = hit
            c = t[3 - a - b]
            va, vb = t[a], t[b]
            lerp = lambda p, q: tuple(p[i] + s * (q[i] - p[i]) for i in range(len(p)))
            V = ((w[0], va[0][1] + s * (vb[0][1] - va[0][1]), w[1]),
                 lerp(va[1], vb[1]), lerp(va[2], vb[2]), tuple(t[0][3]))
            grown.append([va, V, c])          # winding-preserving for every edge choice
            grown.append([V, vb, c])
            changed += 1
            n_split += 1
        out = grown
        if not changed:
            return out, n_split
    raise SystemExit("REFUSE: T-junction split did not converge")


def sea5_flank_rect(sea5_tris, ring):
    """THE HARVEST. sea5's v-row is shade-bearing, so take the rect from the hole's two
    IMMEDIATE FLANK tiles in the frame lattice row -- and REFUSE if they disagree."""
    row = int((-FRAME_Z) // 4.0)                       # world lattice row of z in [-644,-640]
    xs = [p[0] for p in ring if p[1] >= SPLIT_Z - 1e-6]
    lo, hi = min(xs), max(xs)
    rows = defaultdict(Counter)
    for t in sea5_tris:
        tx = [v[0][0] for v in t]; tz = [v[0][2] for v in t]
        gx, gz = math.floor(min(tx) / 4.0), math.floor((-max(tz)) / 4.0)
        if gz != row:
            continue
        uu = [v[2][0] for v in t]; vv = [v[2][1] for v in t]
        rows[gx][(round(min(vv), 5), round(max(vv), 5))] += 1
    # the 4 full v-rows this block's sea5 actually uses
    full = sorted({(r[1], r[3]) for r in full_tile_rects(sea5_tris)
                   if (r[2] - r[0]) > 0.9 and (r[3] - r[1]) > 0.23})
    if len(full) != 4:
        raise SystemExit(f"REFUSE: block sea5 shows {len(full)} full v-rows, expected 4: {full}")

    def band_of(gx):
        if gx not in rows:
            return None
        got = set()
        for (v0, v1), _ in rows[gx].items():
            for k, (f0, f1) in enumerate(full):
                if v0 >= f0 - 1e-6 and v1 <= f1 + 1e-6:
                    got.add(k)
        return got.pop() if len(got) == 1 else None

    west, east = band_of(int(lo // 4.0)), band_of(int(math.ceil(hi / 4.0)) - 1)
    if west is None or east is None or west != east:
        raise SystemExit(f"REFUSE: the hole's frame-row sea5 flanks disagree "
                         f"(west v-row {west}, east v-row {east}) -- no verbatim tile to carry")
    ufull = sorted({(r[0], r[2]) for r in full_tile_rects(sea5_tris)
                    if (r[2] - r[0]) > 0.9 and (r[3] - r[1]) > 0.23})[0]
    return (ufull[0], full[west][0], ufull[1], full[west][1]), west


# --------------------------------------------------------------------------- build the fix
def build(root: Path, nav_reset: str = 'seal'):
    rep: dict = {}
    parts = {p: read_part(root, BX, BY, p) for p in PARTS}
    parts = {p: b for p, b in parts.items() if b is not None}
    tw = {p: world_tris(b, BX, BY) for p, b in parts.items()}
    rep["parts_before"] = {p: len(t) for p, t in tw.items()}
    if len(tw["Terrain"]) != EXPECT_TERRAIN_TRIS:
        raise SystemExit(f"REFUSE: Block[{BX}][{BY}] Terrain has {len(tw['Terrain'])} tris, "
                         f"the diagnosis was {EXPECT_TERRAIN_TRIS}")

    frag, cuts = find_fragment(tw["Terrain"])
    frag_ids = {id(t) for t in frag}
    kept = [t for t in tw["Terrain"] if id(t) not in frag_ids]
    ring = plan_ring(frag)
    rep["cut_edges"] = [[list(e[0]), list(e[1])] for e in sorted(cuts)]
    rep["hole_plan_area"] = abs(sum(ring[i][0] * ring[(i + 1) % len(ring)][1]
                                    - ring[(i + 1) % len(ring)][0] * ring[i][1]
                                    for i in range(len(ring)))) / 2.0
    rep["dropped_tris"], rep["kept_terrain_tris"] = len(frag), len(kept)

    n3, w3, tail3 = sheet_dialect(tw["Sea3"])
    n5, w5, tail5 = sheet_dialect(tw["Sea5"])
    quads3 = [r for r, _ in full_tile_rects(tw["Sea3"]).most_common(4)]
    quads3.sort(key=lambda r: (r[1], r[0]))
    if len(quads3) != 4 or len({(round(r[0], 3), round(r[1], 3)) for r in quads3}) != 4:
        raise SystemExit(f"REFUSE: block sea3 does not show 4 distinct mains quadrants: {quads3}")
    rect5, vrow = sea5_flank_rect(tw["Sea5"], ring)
    rep["dialect"] = dict(sea3_normal=list(n3), sea3_winding=w3, sea3_quads=[list(q) for q in quads3],
                          sea5_normal=list(n5), sea5_winding=w5, sea5_rect=list(rect5),
                          sea5_vrow=vrow)

    # snap targets: every EXISTING waterline vertex of the sea sheets in the neighbourhood
    snap = {}
    for p in ("Sea3", "Sea4", "Sea5"):
        for (bx, by) in ((BX, BY), (BX - 1, BY), (BX + 1, BY), (BX, BY + 1), (BX, BY - 1)):
            b = read_part(root, bx, by, p)
            if b is None:
                continue
            for t in world_tris(b, bx, by):
                for v in t:
                    if abs(v[0][1]) < 1e-6:
                        snap.setdefault((round(v[0][0], 4), round(v[0][2], 4)),
                                        (v[0][0], v[0][2]))

    ring3 = [(p[0], 0.0, p[1]) for p in ME._clip_plan(ring, 1, SPLIT_Z, True)]     # z <= -644
    ring5 = [(p[0], 0.0, p[1]) for p in ME._clip_plan(ring, 1, SPLIT_Z, False)]    # z >= -644
    idall = encode_id(topograph=SEA_TOPO_OPEN)
    fill3 = ME.lattice_patch(ring3, y=0.0, uv_quads=quads3, idall=idall, normal=n3,
                             winding=w3, snap_verts=list(snap.values()))
    fill5 = ME.lattice_patch(ring5, y=0.0, uv_quads=[rect5], idall=idall, normal=n5,
                             winding=w5, snap_verts=list(snap.values()))
    fill3 = retail_tangents(fill3, tail3)
    fill5 = retail_tangents(fill5, tail5)
    rep["fill"] = dict(sea3=tri_stats(fill3), sea5=tri_stats(fill5))

    # THE T-VERTEX REPAIR. Every vertex the fill mints on the HOLE OUTLINE is a T-junction
    # against the sheet triangle that still spans that edge from the other side. Split those
    # -- and, symmetrically, split the fill where a retained sheet vertex lands inside a fill
    # edge (the fill is ours, so both halves of the pinhole are ours to close).
    fill_pts = {(round(v[0][0], 6), round(v[0][2], 6)) for t in fill3 + fill5 for v in t}
    sheet_pts = {(round(v[0][0], 6), round(v[0][2], 6))
                 for p in ("Sea3", "Sea4", "Sea5") for t in tw[p] for v in t
                 if abs(v[0][1]) < 1e-6}
    sea3n, s3n = split_at_points(tw["Sea3"], fill_pts)
    sea4n, s4n = split_at_points(tw["Sea4"], fill_pts)
    sea5n, s5n = split_at_points(tw["Sea5"], fill_pts)
    fill3, f3n = split_at_points(fill3, sheet_pts)
    fill5, f5n = split_at_points(fill5, sheet_pts)
    rep["tvertex_splits"] = dict(sea3=s3n, sea4=s4n, sea5=s5n, fill3=f3n, fill5=f5n)

    # THE ORPHANED NAV RING. coastnav.stamp only ever RAISES a class (its classifier `continue`s
    # when no ground is near), so removing a shore leaves its KEEL(56)/BELT(55)/CLIFF(54)/
    # BEACH(53) ring stamped on water that now fronts nothing -- an invisible boat wall.
    # Reset exactly the triangles stamp PROVABLY cannot re-raise: farther than
    # FRINGE_R(16) + BELT_R(3.5) + one ground-scan step from every surviving land triangle in
    # the 3x3 block ring.  Then `stamp` is re-run and re-raises anything that still qualifies.
    land = []
    for by in (BY - 1, BY, BY + 1):
        for bx in (BX - 1, BX, BX + 1):
            b = read_part(root, bx, by, "Terrain")
            if b is None:
                continue
            for t in world_tris(b, bx, by):
                if (bx, by) == (BX, BY) and t in frag:
                    continue
                land.append(t)
    SAFE = coastnav.FRINGE_R + coastnav.BELT_R + 3.0
    nav_classes = {'seal': (55, 56), 'full': (53, 54, 55, 56), 'none': ()}[nav_reset]
    reset = Counter()

    def _probe(t):
        pts = [(v[0][0], v[0][2]) for v in t]
        return pts + [(sum(p[0] for p in pts) / 3.0, sum(p[1] for p in pts) / 3.0)]

    def _reaches(t, tris, r):
        for lt in tris:
            a, b_, c = ((v[0][0], v[0][2]) for v in lt)
            for (px, pz) in _probe(t):
                if coastnav._tri_dist2d(px, pz, a, b_, c) <= r:
                    return True
        return False

    # SCOPE: only the ring the REMOVED shore could have stamped, and by default only the two
    # classes that are BOAT WALLS -- BELT(55) and KEEL(56) are outside the Narciss legality
    # mask {53,54,57}, so leaving them turns the vanished islet into an invisible wall in open
    # water. 53/54 stay boat-legal and are left alone: the carried sheets ALSO hold stock
    # classes inherited from the donor's other (uncarried) landmasses -- ~115 more triangles
    # block-wide -- which is pre-existing across the whole carry, not this defect. `--nav-reset
    # full` clears those too (provably right: every reset triangle is >19.5u from all surviving
    # land, so coastnav's own classifier could never raise it), `--nav-reset none` skips it.
    def retopo(tris, part):
        out = []
        for t in tris:
            idall = int(round(t[0][3][0]))
            topo = (idall & 0xFC) >> 2
            if topo in nav_classes and _reaches(t, frag, SAFE) \
                    and not _reaches(t, land, SAFE):
                nid = float((idall & ~0xFC) | (SEA_TOPO_OPEN << 2))
                out.append([(p, n, u, (nid,) + tuple(g[1:])) for (p, n, u, g) in t])
                reset[(part, topo)] += 1
            else:
                out.append(t)
        return out

    sea3n, sea4n, sea5n = (retopo(sea3n, "Sea3"), retopo(sea4n, "Sea4"), retopo(sea5n, "Sea5"))
    rep["orphan_nav_reset"] = {f"{p}:{t}": n for (p, t), n in sorted(reset.items())}
    rep["nav_reset_mode"] = nav_reset

    new = {"Terrain": build_part(kept, "Terrain", BX, BY),
           "Sea3": build_part(sea3n + fill3, "Sea3", BX, BY),
           "Sea5": build_part(sea5n + fill5, "Sea5", BX, BY)}
    if s4n or any(k[0] == "Sea4" for k in reset):
        new["Sea4"] = build_part(sea4n, "Sea4", BX, BY)
    after = dict(tw)
    after["Terrain"], after["Sea3"], after["Sea5"] = kept, sea3n + fill3, sea5n + fill5
    after["Sea4"] = sea4n
    return rep, new, dict(before=tw, after=after, frag=frag, fill3=fill3, fill5=fill5,
                          ring=ring, parts=parts, snap=snap, root=root)


# --------------------------------------------------------------------------- the gates
def gates(rep, new, ctx):
    root, before, after = ctx["root"], ctx["before"], ctx["after"]
    fails, notes = [], []

    def check(name, ok, detail=""):
        (notes if ok else fails).append(f"{'PASS' if ok else 'FAIL'}  {name}{' -- ' + detail if detail else ''}")

    # 1. engine loader predicates + the UNINDEXED CONTRACT on every mesh we write
    for p, bm in new.items():
        try:
            validate_blockmesh(bm)
            check(f"validate_blockmesh[{p}]", True, f"vcount={bm.vcount} tris={len(bm.tris)}")
        except ValueError as e:
            check(f"validate_blockmesh[{p}]", False, str(e))

    # 2. the REBUILD IS LOSSLESS: rebuilding an unchanged part reproduces its bytes exactly
    for p in ("Sea4",):
        b = read_part(root, BX, BY, p)
        rt = build_part(world_tris(b, BX, BY), p, BX, BY)
        check(f"rebuild-identity[{p}]", ff9mesh_bytes(rt) == part_path(root, BX, BY, p).read_bytes(),
              "an unchanged tri list must round-trip byte-identically")

    # 3. the kept terrain tris are byte-identical to their deployed originals, and the split
    #    sea sheets are AREA-NEUTRAL (a T-split re-triangulates, it never moves the sheet)
    orig = [tuple(tuple(map(tuple, v)) for v in t) for t in before["Terrain"]]
    kept = [tuple(tuple(map(tuple, v)) for v in t) for t in after["Terrain"]]
    check("kept-terrain-verbatim", len(kept) == 14 and all(k in orig for k in kept),
          f"{len(kept)} tris kept, each byte-identical to its deployed original")
    for p in ("Sea3", "Sea4", "Sea5"):
        pa = sum(abs((t[1][0][0] - t[0][0][0]) * (t[2][0][2] - t[0][0][2])
                     - (t[2][0][0] - t[0][0][0]) * (t[1][0][2] - t[0][0][2])) / 2.0
                 for t in before[p])
        fa = sum(abs((t[1][0][0] - t[0][0][0]) * (t[2][0][2] - t[0][0][2])
                     - (t[2][0][0] - t[0][0][0]) * (t[1][0][2] - t[0][0][2])) / 2.0
                 for t in (ctx["fill3"] if p == "Sea3" else ctx["fill5"] if p == "Sea5" else []))
        aa = sum(abs((t[1][0][0] - t[0][0][0]) * (t[2][0][2] - t[0][0][2])
                     - (t[2][0][0] - t[0][0][0]) * (t[1][0][2] - t[0][0][2])) / 2.0
                 for t in after[p])
        check(f"area-conserved[{p}]", abs(aa - pa - fa) < 1e-6,
              f"before {pa:.4f} + fill {fa:.4f} == after {aa:.4f} (delta {aa - pa - fa:+.2e})")

    # 3b. no DOUBLE COVER: the fill must not overlap the sheets it welds to
    def multiplicity(state, step=0.5):
        worst, n = 0, 0
        for p in ("Terrain", "Sea3", "Sea4", "Sea5"):
            for (px, pz) in block_samples(BX, BY, step):
                m = sum(1 for t in state[p] if plan_inside(px, pz, t))
                worst = max(worst, m)
                n += m > 1
        return worst, n
    mb, nb = multiplicity(before)
    ma, na = multiplicity(after)
    check("no-introduced-double-cover", na <= nb and ma <= mb,
          f"before max={mb} overlapping={nb} | after max={ma} overlapping={na}")

    # 4. the OPEN CUT is gone and no new non-waterline once-edge appeared on the terrain
    cuts_after = [e for e in once_edges(after["Terrain"])
                  if not (abs(e[0][1]) < 1e-6 and abs(e[1][1]) < 1e-6)
                  and not (abs(e[0][2] + 704.0) < 1e-3 and abs(e[1][2] + 704.0) < 1e-3)
                  and not (abs(e[0][0] - 448.0) < 1e-3 and abs(e[1][0] - 448.0) < 1e-3)]
    check("open-cut-closed", not cuts_after, f"{len(cuts_after)} residual off-frame cut edges")

    # 5. plan coverage: ZERO holes before and after (the sheet stays watertight in plan)
    h_before = coverage_holes(before, BX, BY)
    h_after = coverage_holes(after, BX, BY)
    check("plan-holes-before", not h_before, f"{len(h_before)}")
    check("plan-holes-after", not h_after, f"{len(h_after)} (introduced: "
          f"{len(set(h_after) - set(h_before))})")

    # 6. THE LATTICE LAW: no fill triangle spans a 4u tile, and its envelope sits inside the
    #    block's own sea envelope
    env = tri_stats(before["Sea3"] + before["Sea4"] + before["Sea5"])
    for band in ("sea3", "sea5"):
        f = rep["fill"][band]
        check(f"lattice-envelope[{band}]",
              f["area_max"] <= env["area_max"] + 1e-6 and f["edge_max"] <= env["edge_max"] + 1e-6,
              f"area {f['area_max']:.3f}<={env['area_max']:.3f}  edge {f['edge_max']:.3f}<={env['edge_max']:.3f}")
        check(f"winding[{band}]", set(f["winding"]) == {-1}, str(f["winding"]))
    spanning = 0
    for t in ctx["fill3"] + ctx["fill5"]:
        xs = [v[0][0] for v in t]; zs = [v[0][2] for v in t]
        if math.floor(min(xs) / 4.0) != math.floor(max(xs) / 4.0 - 1e-9) \
                or math.floor((-max(zs)) / 4.0) != math.floor((-min(zs)) / 4.0 - 1e-9):
            spanning += 1
    check("no-tile-spanning-fill-tri", spanning == 0, f"{spanning}")

    # 7. THE EXACTNESS GATE: every fill boundary vertex is an existing sheet vertex, a ring
    #    vertex, or a lattice crossing ON the hole outline -- nothing minted off the outline
    have = {(round(x, 3), round(z, 3)) for (x, z) in ctx["snap"]}
    ringpts = [(p[0], p[1]) for p in ctx["ring"]]
    off = []
    for e in once_edges(ctx["fill3"] + ctx["fill5"]):
        for v in e:
            p = (v[0], v[2])
            if (round(p[0], 3), round(p[1], 3)) in have:
                continue
            on = False
            for i in range(len(ringpts)):
                a, b = ringpts[i], ringpts[(i + 1) % len(ringpts)]
                dx, dz = b[0] - a[0], b[1] - a[1]
                L2 = dx * dx + dz * dz
                if L2 < 1e-12:
                    continue
                s = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
                if math.hypot(p[0] - (a[0] + s * dx), p[1] - (a[1] + s * dz)) < 2e-3:
                    on = True
                    break
            if not on:
                off.append(p)
    check("fill-boundary-on-outline", not off, f"{len(set(off))} off-outline boundary verts")

    # 8. THE WELD AUDIT: no INTRODUCED near-miss vertex pairs anywhere in the block
    ring_parts = [(bx, by, p) for by in (BY - 1, BY, BY + 1) for bx in (BX - 1, BX, BX + 1)
                  for p in PARTS]
    def audit(over):
        ms = []
        for (bx, by, p) in ring_parts:
            if (bx, by) == (BX, BY) and p in over:
                ms.append(over[p])
                continue
            b = read_part(root, bx, by, p)
            if b is not None:
                ms.append(b)
        return set(weld_audit(ms))
    a_before, a_after = audit({}), audit(new)
    check("weld-audit-no-introduced", not (a_after - a_before),
          f"before={len(a_before)} after={len(a_after)} introduced={len(a_after - a_before)}")

    # 9. T-JUNCTION census over the block's plan geometry: no introduced pinholes
    def tj(state):
        tris = [[(v[0][0], v[0][2]) for v in t]
                for p in ("Terrain", "Sea3", "Sea4", "Sea5") for t in state[p]]
        return len(ME.find_tjunctions(tris))
    t_before, t_after = tj(before), tj(after)
    check("tjunctions-no-introduced", t_after <= t_before, f"before={t_before} after={t_after}")

    # 10. THE LATTICE ADJACENCY LAW: the fill introduces no unlawful water band pair
    LAWFUL = {1: {1, 2, 3, 5}, 2: {1, 2}, 3: {1, 3, 5}, 4: {4, 5}, 5: {1, 3, 4, 5}}
    edge_band = defaultdict(set)
    for p, rank in (("Sea1", 1), ("Sea2", 2), ("Sea3", 3), ("Sea4", 4), ("Sea5", 5)):
        for t in after.get(p, []):
            for a, b in ((0, 1), (1, 2), (2, 0)):
                edge_band[tuple(sorted((K(t[a][0]), K(t[b][0]))))].add(rank)
    bad = [(e, s) for e, s in edge_band.items() if len(s) > 1
           and any(y not in LAWFUL[x] for x in s for y in s)]
    check("band-adjacency-lawful", not bad, f"{len(bad)} unlawful shared edges")

    # 11. the armed tiles' file is untouched
    ap = root / "FF9_Data/WorldMap/Disc9" / LOD / ARMED_FILE[0] / ARMED_FILE[1]
    check("armed-tiles-file-untouched", ap.is_file(), f"{ap.name} sha={sha(ap)[:12] if ap.is_file() else 'MISSING'}")

    return fails, notes


# --------------------------------------------------------------------------- write / scratch
def stage_scratch(live_root: Path, scratch: Path) -> Path:
    dst = scratch / MOD_FOLDER
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(live_root / "FF9_Data", dst / "FF9_Data")
    for f in ("DictionaryPatch.txt",):
        src = live_root / f
        if src.is_file():
            shutil.copyfile(src, dst / f)
    return dst


def write_out(root: Path, new, backup_dir: Path | None, do_coastnav: bool, game_root: Path):
    written = []
    if backup_dir:
        backup_dir.mkdir(parents=True, exist_ok=True)
        man = {}
        for p in list(new) + ["Sea4"]:
            src = part_path(root, BX, BY, p)
            if src.is_file():
                shutil.copyfile(src, backup_dir / src.name)
                man[src.name] = dict(src=str(src), sha256=sha(src))
        (backup_dir / "manifest.json").write_text(json.dumps(man, indent=2), encoding="utf-8")
    from ff9mapkit.world import mesh as M
    for p, bm in new.items():
        dest = part_path(root, BX, BY, p)
        write_ff9mesh(bm, dest)
        # LEDGER the direct write (as coastnav.stamp does for its in-place rewrite): without
        # it the next deploy_override at this cell+part refuses our own bytes as foreign.
        M.record_ledger_write(dest, cell=(BX, BY), part=p, write_disc=DISC)
        written.append(str(dest))
    if do_coastnav:
        r = coastnav.stamp(MOD_FOLDER, disc=DISC, cells=[(BX, BY)], policy="land-anywhere",
                           deploy=True, game=game_root, backup_dir=backup_dir, backup=False)
        return written, r
    return written, None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", default=True,
                   help="(default) read-only: diagnose, build in memory, run every gate")
    g.add_argument("--write", action="store_true",
                   help="back up to C:\\gd\\Dream-World-IX\\backups\\ then WRITE the live install")
    g.add_argument("--scratch", metavar="DIR",
                   help="stage a scratch game root from the live files, write THERE, gate it")
    ap.add_argument("--game", default=None, help="game root (default: the kit's resolver)")
    ap.add_argument("--nav-reset", choices=("seal", "full", "none"), default="seal",
                    help="clear the removed shore's orphaned coastnav classes: "
                         "seal (default) = only BELT(55)/KEEL(56), the boat walls; "
                         "full = also the boat-legal 53/54; none = leave them")
    ap.add_argument("--no-coastnav", action="store_true",
                    help="skip the coastnav re-stamp (leaves the orphaned KEEL/BELT ring)")
    ap.add_argument("--backup-dir", default=None,
                    help=r"park the pre-edit bytes here (default: a timestamped dir "
                         r"under C:\gd\Dream-World-IXackups\ in --write mode)")
    ap.add_argument("--json", metavar="PATH", help="write the report as JSON")
    a = ap.parse_args()

    game = Path(a.game) if a.game else config.find_game_path()
    live = game / MOD_FOLDER
    mode = "write" if a.write else ("scratch" if a.scratch else "dry-run")
    print(f"== fix_fragment  mode={mode}  game={game}")

    if a.scratch:
        scratch = Path(a.scratch)
        scratch.mkdir(parents=True, exist_ok=True)
        root = stage_scratch(live, scratch)
        game_root = scratch
        print(f"   staged scratch root -> {root}")
    else:
        root, game_root = live, game

    rep, new, ctx = build(root, nav_reset=a.nav_reset)
    print(f"\n-- DIAGNOSIS -------------------------------------------------")
    print(f"   Block[{BX}][{BY}] parts before: {rep['parts_before']}")
    print(f"   severed component: {rep['dropped_tris']} tris, {rep['kept_terrain_tris']} kept")
    print(f"   open-cut edges ({len(rep['cut_edges'])}), all in the z={FRAME_Z:.0f} frame plane:")
    for e in rep["cut_edges"]:
        print(f"      {tuple(e[0])} -> {tuple(e[1])}")
    print(f"   hole plan area: {rep['hole_plan_area']:.2f} u2")
    print(f"\n-- DIALECT (byte-read from block ({BX},{BY})'s own sheets) ----")
    d = rep["dialect"]
    print(f"   sea3 normal={tuple(d['sea3_normal'])} winding={d['sea3_winding']:+.0f}")
    for q in d["sea3_quads"]:
        print(f"        quad {tuple(q)}")
    print(f"   sea5 normal={tuple(d['sea5_normal'])} winding={d['sea5_winding']:+.0f} "
          f"v-row {d['sea5_vrow']} rect {tuple(d['sea5_rect'])} (harvested from both flanks)")
    print(f"\n-- FILL ------------------------------------------------------")
    for band in ("sea3", "sea5"):
        f = rep["fill"][band]
        print(f"   {band}: {f['n']:3d} tris  area med={f['area_med']:.3f} max={f['area_max']:.3f}"
              f"  edge med={f['edge_med']:.3f} max={f['edge_max']:.3f}  winding {f['winding']}")
    print(f"   T-vertex splits: {rep['tvertex_splits']}")
    print(f"   orphaned nav classes reset to open-sea 57: {rep['orphan_nav_reset'] or 'none'}")
    print(f"   parts after: " + ", ".join(f"{p}={len(t)}" for p, t in ctx['after'].items()))

    fails, notes = gates(rep, new, ctx)
    print(f"\n-- GATES -----------------------------------------------------")
    for line in notes + fails:
        print("   " + line)
    rep["gates"] = dict(pass_=notes, fail=fails)

    if fails:
        print(f"\nREFUSING: {len(fails)} gate(s) failed -- nothing written.")
        if a.json:
            Path(a.json).write_text(json.dumps(rep, indent=2), encoding="utf-8")
        return 2

    if mode == "dry-run":
        print("\nDRY RUN -- nothing written. Re-run with --scratch DIR to prove the write, "
              "or --write to deploy.")
    else:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        bdir = Path(a.backup_dir) if a.backup_dir else (
            (BACKUP_ROOT / f"fragment-c2-{ts}") if mode == "write" else None)
        written, cn = write_out(root, new, bdir, not a.no_coastnav, game_root)
        print(f"\n-- WROTE -----------------------------------------------------")
        for w in written:
            print(f"   {w}")
        if bdir:
            print(f"   backups -> {bdir}")
        if cn:
            print(f"   coastnav re-stamp: {json.dumps({k: v for k, v in cn.items() if k != 'cells'})[:400]}")
        # post-write read-back
        for p in new:
            print(f"   read-back {p}: sha={sha(part_path(root, BX, BY, p))[:16]}")
        rep["written"] = written

    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
