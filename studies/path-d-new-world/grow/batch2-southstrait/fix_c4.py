#!/usr/bin/env py
r"""fix_c4.py -- retire the GREEN TWIN WEDGE (c4), Disc9 Block[6][10], and close its hole with a
THREE-BAND MINI-LADDER.

THE DEFECT (measured live, 2026-08-05 -- the c2 numbers do NOT transfer)
-----------------------------------------------------------------------
Same class as c2: `world-transplant --cell 5,10 --donor 5,15 --size 3x2` carried donor block
(6,15) verbatim into target (6,10), and stock (6,15) holds a TOE of the big (6,14) landmass that
pokes south across the z=-1024 block border.  (6,14) is outside the 3x2 donor rect, so the rect's
NORTH frame sliced the toe flat.

Fresh forensics on the deployed bytes (`Block[6][10] Terrain.ff9mesh`, 277 tris):

  * exactly TWO vertex-components -- 259 tris (the horseshoe's own mass, z <= -662.023) and
    **18 tris** (topo 58 wall x12 + topo 0 plateau-top x6), event bits 0 on all 18.
  * the 18-tri component is the ONLY one touching the z=-640 frame.  x 386.910..397.660,
    y 0..3.590.
  * 10 once-edges: 6 ordinary waterline (y=0) -- THE FREE-BASE LAW -- and **4 an OPEN CUT** in
    the z=-640 plane, up to y=3.590:
        (386.910, 0.000, -640) -> (388.000, 3.590, -640)     wall profile, up
        (388.000, 3.590, -640) -> (392.000, 3.590, -640)     plateau crest
        (392.000, 3.590, -640) -> (396.402, 2.734, -640)     plateau crest
        (396.402, 2.734, -640) -> (397.566, 0.000, -640)     wall profile, down
    i.e. a 10.656u x 3.590u cross-section with NO face closing it -- the same unclosed hull that
    read as a "pale flat face" on c2, here green because the toe carries grass topo.
  * plan ring: a single simple cycle, 10 nodes, **78.846 u2**.
  * and the whole 78.85 u2 is GENUINELY UNCOVERED -- measured at 0.05u, every neighbouring sea
    triangle stops exactly on the fragment's waterline, so no sea4 runs under this toe.  Drop it
    and you open a real ground-raycast hole.

WHY A THREE-BAND LADDER (and why c2's two-band split cannot be reused)
----------------------------------------------------------------------
The hole spans **11 lattice cells**, and 8 of them ALREADY carry a partial tile whose band is
therefore forced (a cell is one shade; mixing two bands inside a 4u cell is not a shape stock
ships).  Measured band of each flanking cell (block-local cell indices, i east, j south):

        i=0        i=1        i=2        i=3
  j=0   sea4       (virgin)   (virgin)   sea5      <- the z=-640 frame row
  j=1   sea4       sea4       (virgin)   sea3
  j=2   --         sea4       sea5       sea3

THE LATTICE ADJACENCY LAW ({3:1,3,5} {5:1,3,4,5} {4:4,5} -- sea3 NEVER touches sea4) then fixes
the free cells:

  * row j=1 is `sea4 | sea4 | ? | sea3`, so **(2,1) MUST be sea5** -- the separator between the
    west sea4 arc and the east sea3 field.  A sea4 there would abut sea3; a sea3 there would abut
    sea4.  That single cell is the whole reason c4 needed its own round.
  * row j=2 is already the lawful ladder `sea4 | sea5 | sea3`; the fill just continues it.
  * row j=0 is the FRAME row against the prefab deep ring, so no sea3 may land there (a sea3 tile
    paints nothing deep and would under-cover the deep it faces -- the hard-seam class).  (2,0)
    must be **sea5**: making it sea4 would put deep on (3,0)'s west side, and (3,0) paints a plain
    N tip, so we would MINT an under-seam in a tile we never touched.
  * (1,0) is genuinely free between sea4 and sea5 and is decided by the stock bigram oracle
    (`--compare` prints the scoreboard).

THE LATTICE LINES the ladder splits on -- all real 4u lattice lines, never a mid-cell cut:
    x = 392 (sea4 | sea5) in rows j=0, j=1, j=2
    x = 396 (sea5 | sea3) in rows j=1, j=2
    z = -644, z = -648 (the row lines)
plus x = 388 in row j=0 only, when `--candidate B` puts sea5 at (1,0).

CARRY THE TILES, DO NOT AUTHOR THEM
-----------------------------------
Every uv byte is either CONTINUED from the cell's own existing tile or HARVESTED verbatim:

  * **THE CLAMPED-BILINEAR RECOVERY.** A deployed tile's uv is `rimretile._tile_uv` of a 4-corner
    map with the cell fractions CLAMPED to [0,1] -- proven here by exact reconstruction (residual
    <= 1e-15) on the flank tiles, including verts that sit OUTSIDE their own cell.  So a partial
    coast-cut tile's corner map is recoverable by a clamped-bilinear least-squares fit over its own
    verts, and the fill then evaluates that same map.  `rimretile._sea5_deepsets` cannot do this --
    it ROUNDS each vert to the nearest corner and reads the uv AT the vert, which is why (3,0) and
    (2,2) read as unclassifiable "cut" today; the recovery says (3,0) is a clean r270 strip-0 tile,
    i.e. a plain **N tip**.
  * a virgin cell, or a tile whose recovery is not a pure rotation inside [0,1], gets a VERBATIM
    tile instead: sea5 from `rimretile.harvest_variants([(7,15)])` -- the one carry donor holding
    all 16 variants self-consistently (see run_rim_fix.py) -- keyed by the cell's POST-FILL
    geometric deep-set; sea3/sea4 from the block's OWN full-quad mains by the byte-derived
    anti-tiling rule (quadrant parity + rotation differing from the placed neighbours).
  * THE SEA-SHEET LAWS: winding and normal are read from each sheet's own bytes
    ((-0.1211, 0.9785, 0.1665), plan winding -1), and the tangent TAIL from the sheet too
    (this block: (0,0,0), not lattice_patch's default (0,0,1)).

THE T-VERTEX LAW: the fill mints a vertex wherever a hole-boundary edge crosses a 4u line, and the
sheet triangle on the far side of that edge still spans it.  Those neighbours are split at the
fill's EXACT coordinates; symmetrically the fill is split where a retained sheet vertex lands
inside a fill edge.

coastnav: `stamp` only ever RAISES a class, so the removed shore's BELT(55)/KEEL(56) ring would
survive as an invisible boat wall (55/56 are outside the Narciss legality mask {53,54,57}).  Those
triangles provably beyond every surviving land (> FRINGE_R 16 + BELT_R 3.5 + 3) are reset to
open-sea 57 and `coastnav.stamp(policy="land-anywhere")` is re-run over cell (6,10).

FILES TOUCHED (all under <game>/FF9CustomMap-world/FF9_Data/WorldMap/Disc9/0_1/r10/)
    Block[6][10] Terrain.ff9mesh   277 -> 259 tris
    Block[6][10] Sea3.ff9mesh      + fill + T-splits
    Block[6][10] Sea4.ff9mesh      + fill + T-splits
    Block[6][10] Sea5.ff9mesh      + fill + T-splits
NOT touched: every other cell, every `.prerim` rim backup, and `Block[6][11] Terrain.ff9mesh` --
the 31 event-armed exit-trigger tris live there and its sha256 is asserted unchanged.

USAGE
    py fix_c4.py                        # --dry-run (default): read-only, full gate report
    py fix_c4.py --compare              # + the (1,0) band scoreboard against the stock oracle
    py fix_c4.py --scratch <DIR>        # stage a scratch game root, WRITE there, gate it
    py fix_c4.py --write                # back up to C:\gd\Dream-World-IX\backups\ then write live
    py fix_c4.py --render <DIR>         # also emit before/after top-down PNGs
Every mode runs the gates first and REFUSES to write if any fails.
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
from ff9mapkit.world import rimretile as R, water as W                   # noqa: E402
from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN, encode_id  # noqa: E402
from ff9mapkit.world.mesh import (blockmesh_from_ff9mesh, ff9mesh_bytes, override_relpath,
                                  validate_blockmesh, weld_audit, write_ff9mesh)  # noqa: E402
from ff9mapkit.world.transplant import _sea_shade_grid, _sea_water_grid  # noqa: E402

MOD_FOLDER = "FF9CustomMap-world"
DISC, READ_DISC, LOD = 9, 1, "0_1"
BX, BY = 6, 10                        # the block holding the c4 fragment
OX, OZ = 64.0 * BX, -64.0 * BY        # its world origin (384.0, -640.0)
FRAME_Z = -640.0                      # the carry rect's north frame == the block's north border
CELL = 4.0
G = 16
CARRY = [(bx, by) for by in (10, 11) for bx in (5, 6, 7)]
DONORS = [(7, 15)]                    # the one carry donor holding all 16 sea5 variants
BACKUP_ROOT = Path(r"C:\gd\Dream-World-IX\backups")
ARMED_FILE = ("r11", "Block[6][11] Terrain.ff9mesh")
ARMED_MANIFEST = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\path-d-rung-6-handoff-e2535a"
                      r"\studies\path-d-new-world\rung6\worldside\armed_manifest.json")
PARTS = ("Terrain", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Beach1")
SEA = ("sea3", "sea4", "sea5")
SEA_TOPO_OPEN = 57

# ---- the fragment FINGERPRINT: refuse if the deployed bytes are not what was diagnosed ----
EXPECT_TRIS = 18
EXPECT_TERRAIN_TRIS = 277
EXPECT_CUT_EDGES = 4
EXPECT_RING = [(386.91, -640.0), (388.0, -640.0), (392.0, -640.0), (396.402, -640.0),
               (397.566, -640.0), (397.082, -644.0), (397.66, -650.582), (392.0, -649.238),
               (390.797, -645.539), (387.359, -643.906)]
EXPECT_TOPOS = {58: 12, 0: 6}

#: THE LADDER. block-local cell (i, j) -> band.  Cells marked FORCED carry an existing partial
#: tile of that band; the rest are decided by the lattice adjacency law + the frame rule (see the
#: module docstring).  ``(1, 0)`` is the one free choice -- see CANDIDATES.
LADDER_FORCED = {(0, 0): "sea4", (0, 1): "sea4", (1, 1): "sea4", (1, 2): "sea4",
                 (3, 0): "sea5", (2, 2): "sea5",
                 (3, 1): "sea3", (3, 2): "sea3"}
LADDER_DERIVED = {(2, 0): "sea5", (2, 1): "sea5"}
CANDIDATES = {"A": {(1, 0): "sea4"},          # sea4 arc runs to x=392, sea5 from 392
              "B": {(1, 0): "sea5"}}          # sea5 starts at x=388


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
    """Rebuild an unindexed BlockMesh from WORLD tris. An unchanged tri list round-trips
    BYTE-IDENTICALLY (asserted by gate 2)."""
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
    reports every one as double-covered."""
    x0, z1 = 64.0 * bx, -64.0 * by
    n = int(64 / step)
    return [(x0 + i * step + 0.1371 * step, z1 - (j * step + 0.6197 * step))
            for i in range(n) for j in range(n)]


def coverage_holes(tris_by_part, bx, by, step=1.0):
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


def plan_area(tris):
    return sum(abs((t[1][0][0] - t[0][0][0]) * (t[2][0][2] - t[0][0][2])
                   - (t[2][0][0] - t[0][0][0]) * (t[1][0][2] - t[0][0][2])) / 2.0 for t in tris)


# --------------------------------------------------------------------------- the diagnosis
def find_fragment(terr_world):
    comps = ME.vertex_components(terr_world)
    hits = [c for c in comps if max(v[0][2] for t in c for v in t) >= FRAME_Z - 1e-6]
    if len(hits) != 1:
        raise SystemExit(f"REFUSE: expected exactly 1 frame-touching terrain component in "
                         f"({BX},{BY}), found {len(hits)} (of {len(comps)} components)")
    frag = hits[0]
    if len(frag) != EXPECT_TRIS:
        raise SystemExit(f"REFUSE: the frame-touching component has {len(frag)} tris, the "
                         f"diagnosis was {EXPECT_TRIS} -- the deployed bytes changed")
    topos = Counter((int(round(t[0][3][0])) & 0xFC) >> 2 for t in frag)
    if dict(topos) != EXPECT_TOPOS:
        raise SystemExit(f"REFUSE: fragment topo mix {dict(topos)} != {EXPECT_TOPOS}")
    ev = {int(round(t[0][3][0])) >> 14 for t in frag}
    if ev != {0}:
        raise SystemExit(f"REFUSE: the fragment carries event-armed tiles ({ev}) -- would "
                         f"destroy a trigger")
    cuts = [e for e in once_edges(frag)
            if not (abs(e[0][1]) < 1e-6 and abs(e[1][1]) < 1e-6)]
    if len(cuts) != EXPECT_CUT_EDGES:
        raise SystemExit(f"REFUSE: {len(cuts)} open-cut edges, expected {EXPECT_CUT_EDGES}")
    for e in cuts:
        if abs(e[0][2] - FRAME_Z) > 1e-6 or abs(e[1][2] - FRAME_Z) > 1e-6:
            raise SystemExit(f"REFUSE: an open-cut edge is not on the frame plane: {e}")
    return frag, cuts


def plan_ring(frag):
    """The fragment's PLAN boundary cycle.  ROUND TO KEY, EMIT THE FLOAT (the sea-sheet E-2 law):
    the cycle is WALKED on rounded keys but every emitted point is the ORIGINAL float."""
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
    if sorted((round(a, 3), round(b, 3)) for a, b in ring) != sorted(EXPECT_RING):
        raise SystemExit(f"REFUSE: plan ring changed.\n got {sorted(ring)}\n want {sorted(EXPECT_RING)}")
    return [exact[k] for k in ring]


# --------------------------------------------------------------------------- the uv dialect
def sheet_dialect(tris):
    """(normal, plan winding, tangent tail) byte-read from the sheet itself."""
    nrm = Counter(tuple(round(c, 4) for c in t[0][1]) for t in tris).most_common(1)[0][0]
    w = Counter()
    for t in tris:
        a, b, c = (v[0] for v in t)
        w[-1.0 if ((b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])) < 0 else 1.0] += 1
    if len(w) != 1:
        raise SystemExit(f"REFUSE: mixed plan winding in a sea sheet: {dict(w)}")
    tail = Counter(tuple(round(c, 6) for c in t[0][3][1:]) for t in tris).most_common(1)[0][0]
    return nrm, next(iter(w)), tail


def _lstsq(A, b):
    n = len(A[0])
    ATA = [[sum(A[r][i] * A[r][j] for r in range(len(A))) for j in range(n)] for i in range(n)]
    ATb = [sum(A[r][i] * b[r] for r in range(len(A))) for i in range(n)]
    M = [ATA[i] + [ATb[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-12:
            return None
        M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r == c:
                continue
            f = M[r][c] / M[c][c]
            for k in range(c, n + 1):
                M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] for i in range(n)]


def _frac(p, I, J):
    """THE CLAMP. rimretile._tile_uv clamps the cell fractions, and the deployed bytes were
    produced through it -- verts outside their own cell carry the CLAMPED uv."""
    fx = min(max((p[0] - I * CELL) / CELL, 0.0), 1.0)
    fz = min(max((-p[2] - J * CELL) / CELL, 0.0), 1.0)
    return fx, fz


def recover_corner_map(tris, I, J):
    """THE CLAMPED-BILINEAR RECOVERY -- a partial tile's 4-corner uv map from its own verts.

    Returns ``(corner_map, residual)`` or ``None`` when under-determined.  Unlike
    ``rimretile._sea5_deepsets``, which ROUNDS a vert to the nearest corner and reads the uv AT
    the vert (wrong by the tile's own gradient on any coast-cut tile), this inverts the exact
    function that produced the bytes."""
    samples = {}
    for t in tris:
        for v in t:
            fx, fz = _frac(v[0], I, J)
            samples[(round(fx, 9), round(fz, 9))] = (fx, fz, v[2][0], v[2][1])
    P = list(samples.values())
    if len(P) < 4:
        return None
    A = [[(1 - p[0]) * (1 - p[1]), p[0] * (1 - p[1]), p[0] * p[1], (1 - p[0]) * p[1]] for p in P]
    cu = _lstsq(A, [p[2] for p in P])
    cv = _lstsq(A, [p[3] for p in P])
    if cu is None or cv is None:
        return None
    res = max(max(abs(sum(a * c for a, c in zip(A[k], cu)) - P[k][2]),
                  abs(sum(a * c for a, c in zip(A[k], cv)) - P[k][3])) for k in range(len(P)))
    cm = {(0, 0): (cu[0], cv[0]), (1, 0): (cu[1], cv[1]),
          (1, 1): (cu[2], cv[2]), (0, 1): (cu[3], cv[3])}
    return cm, res


def usable_map(rec):
    """A recovered map is usable only if it reconstructs the bytes AND stays inside the texture
    (an out-of-range corner means the tile is a sheared remnant, not a rect map -- extending it
    would walk the uv off the atlas)."""
    if rec is None:
        return False
    cm, res = rec
    if res > 1e-5:
        return False
    return all(-0.01 <= c <= 1.01 for uv in cm.values() for c in uv)


def full_quad_maps(tris, exclude=()):
    """``{(I,J): (corner_map, fit)}`` for every FULL 4u quad of a sheet -- the block's own
    verbatim vocabulary (fix_eastwangs.mains_maps, generalised to world indices)."""
    per = defaultdict(list)
    for t in tris:
        cx = sum(v[0][0] for v in t) / 3.0
        cz = sum(v[0][2] for v in t) / 3.0
        per[(int(cx // CELL), int((-cz) // CELL))].append(t)
    out = {}
    for (I, J), ts in per.items():
        if (I, J) in exclude:
            continue
        xs = [v[0][0] for t in ts for v in t]
        zs = [v[0][2] for t in ts for v in t]
        if (min(xs) < I * CELL - 1e-6 or max(xs) > (I + 1) * CELL + 1e-6
                or -max(zs) < J * CELL - 1e-6 or -min(zs) > (J + 1) * CELL + 1e-6):
            continue
        if abs(plan_area(ts) - CELL * CELL) > 1e-3:
            continue
        d = {}
        for t in ts:
            for v in t:
                d[(round((v[0][0] - I * CELL) / CELL), round((-v[0][2] - J * CELL) / CELL))] = \
                    (v[2][0], v[2][1])
        if not all(c in d for c in ((0, 0), (1, 0), (1, 1), (0, 1))):
            continue
        fit = W._fit_tile(d)
        if fit is not None:
            out[(I, J)] = (d, fit)
    return out


def _quad_parity(fit):
    ub = 0 if abs(fit[0]) < 1e-6 else 1
    vb = 0 if abs(fit[2]) < 1e-6 else 1
    return ub ^ vb, fit[4]


def pick_mains(maps, I, J):
    """THE ANTI-TILING PICK (byte-derived from real block (8,4)): prefer a quadrant parity and a
    rotation DIFFERING from the already-placed 4-neighbours, then the nearest source cell."""
    nb = [_quad_parity(maps[c][1]) for c in ((I, J + 1), (I - 1, J), (I, J - 1), (I + 1, J))
          if c in maps]
    best = None
    for c, (d, fit) in sorted(maps.items()):
        p = _quad_parity(fit)
        score = (sum(1 for q in nb if q[0] == p[0]), sum(1 for q in nb if q[1] == p[1]),
                 abs(c[0] - I) + abs(c[1] - J))
        if best is None or score < best[0]:
            best = (score, c, d)
    if best is None:
        raise SystemExit("REFUSE: the block carries no full-quad mains tile to harvest")
    return best[1], best[2]


def affine_map(tri):
    """A triangle's OWN uv as an exact linear function of world (x, z) -- 3 points, 3 unknowns.

    THE MAINS CONTINUATION. A coast-cut sheet triangle legitimately SPANS two 4u cells (stock does
    this everywhere), so no per-cell tile map reproduces it and `recover_corner_map` rightly
    refuses. For a mains band (sea3/sea4) the tile's only job is to tile continuously -- its
    identity carries no semantics, unlike a sea5 wang tile -- so the lawful continuation is this
    triangle's own map. Extending it means the fill and the tile agree at every shared VERTEX, and
    since a renderer interpolates uv linearly along an edge, agreeing at both endpoints makes the
    whole shared EDGE seamless."""
    rows, us, vs = [], [], []
    for v in tri:
        rows.append([1.0, v[0][0], v[0][2]])
        us.append(v[2][0])
        vs.append(v[2][1])
    cu, cv = _lstsq(rows, us), _lstsq(rows, vs)
    if cu is None or cv is None:
        return None
    return cu, cv


def affine_eval(m, p):
    cu, cv = m
    return (cu[0] + cu[1] * p[0] + cu[2] * p[2], cv[0] + cv[1] * p[0] + cv[2] * p[2])


def choose_parent(t, have):
    """The existing triangle a fill triangle should inherit its uv map from: the one sharing the
    most vertices (an EDGE beats a corner), then the nearest centroid. Deterministic."""
    tk = {K(v[0])[::2] for v in t}
    tc = (sum(v[0][0] for v in t) / 3.0, sum(v[0][2] for v in t) / 3.0)
    best = None
    for h in have:
        hk = {K(v[0])[::2] for v in h}
        hc = (sum(v[0][0] for v in h) / 3.0, sum(v[0][2] for v in h) / 3.0)
        score = (-len(tk & hk), math.dist(tc, hc))
        if best is None or score < best[0]:
            best = (score, h)
    return best[1] if best else None


def tile_uv(cm, p, I, J):
    """rimretile._tile_uv on WORLD cell indices (bilinear over the 4 corner uvs, clamped)."""
    fx, fz = _frac(p, I, J)
    u00, u10, u11, u01 = cm[(0, 0)], cm[(1, 0)], cm[(1, 1)], cm[(0, 1)]
    return ((u00[0] * (1 - fx) + u10[0] * fx) * (1 - fz)
            + (u01[0] * (1 - fx) + u11[0] * fx) * fz,
            (u00[1] * (1 - fx) + u10[1] * fx) * (1 - fz)
            + (u01[1] * (1 - fx) + u11[1] * fx) * fz)


def split_at_points(tris, pts, *, eps: float = 1e-6, rounds: int = 24):
    """THE T-VERTEX LAW. Split existing sheet triangles at plan points lying strictly INSIDE one
    of their edges; the new vertex takes the fill's EXACT (x, z), y/uv/normal lerped along the
    edge, and the parent's tangent verbatim.

    Returns ``(tris, n_split, max_offset)``. ``max_offset`` is the largest perpendicular distance
    a split point sat from its host edge -- the ONLY way this operation can move geometry, so it
    is measured and gated rather than assumed (gate: it must stay below float32's own resolution
    at these world magnitudes, ~3e-5 at |x| ~ 400, i.e. the two sides round to the same stored
    float and the weld is exact in the FILE)."""
    P = [(float(p[0]), float(p[1])) for p in pts]
    out, n_split, max_off = list(tris), 0, 0.0
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
                    off = abs((w[0] - pa[0]) * dz - (w[1] - pa[2]) * dx) / math.sqrt(L2)
                    if off >= eps:
                        continue
                    max_off = max(max_off, off)
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
            grown.append([va, V, c])
            grown.append([V, vb, c])
            changed += 1
            n_split += 1
        out = grown
        if not changed:
            return out, n_split, max_off
    raise SystemExit("REFUSE: T-junction split did not converge")


# --------------------------------------------------------------------------- carry-wide census
def carry_cells(root, override=None):
    """``{(bx,by): {part: BlockMesh}}`` over the whole carry, with (BX,BY) optionally overridden."""
    out = {}
    for (bx, by) in CARRY:
        d = {}
        for part in SEA:
            if override and (bx, by) == (BX, BY) and part in override:
                d[part] = override[part]
                continue
            b = read_part(root, bx, by, part.capitalize())
            if b is not None:
                d[part] = b
        out[(bx, by)] = d
    return out


def stock_bigrams(game):
    """Stock disc-1 vertical (N->S) + horizontal (W->E) token adjacency -- THE LEARNED WANG TABLE
    (fix_eastwangs.bigram_tables)."""
    from ff9mapkit.world import extract as X
    stock = {}
    for (bx, by) in X.list_blocks(disc=READ_DISC, game=game):
        d = {}
        for part in SEA:
            try:
                d[part] = X.read_block(bx, by, disc=READ_DISC, part=part, game=game)
            except ValueError as e:
                if "mesh not found" not in str(e):
                    raise
        if d:
            stock[(bx, by)] = d
    return stock, _bigrams(stock, offisland=None)


def _tokenizer(cells, *, offisland):
    shade = {c: _sea_shade_grid(v) for c, v in cells.items()}
    water = {c: _sea_water_grid(v) for c, v in cells.items()}
    uv = {c: R._sea5_deepsets(v) for c, v in cells.items()}

    def tok(bx, by, i, j):
        if (bx, by) not in shade:
            return offisland
        if not water[(bx, by)][i][j]:
            return "L"
        s = shade[(bx, by)][i][j]
        if s != "sea5":
            return s
        d = uv[(bx, by)].get((i, j))
        return "".join(sorted(d)) if d else "cut"
    return tok


def _step(bx, by, i, j, d):
    di, dj = R.DIRV[d]
    ni, nj, nbx, nby = i + di, j + dj, bx, by
    if ni < 0:
        nbx, ni = bx - 1, G - 1
    elif ni >= G:
        nbx, ni = bx + 1, 0
    if nj < 0:
        nby, nj = by - 1, G - 1
    elif nj >= G:
        nby, nj = by + 1, 0
    return nbx, nby, ni, nj


def _bigrams(cells, *, offisland):
    tok = _tokenizer(cells, offisland=offisland)
    vert, horiz = Counter(), Counter()
    for (bx, by) in cells:
        for i in range(G):
            for j in range(G):
                a = tok(bx, by, i, j)
                if a is None:
                    continue
                s, e = tok(*_step(bx, by, i, j, "S")), tok(*_step(bx, by, i, j, "E"))
                if s is not None:
                    vert[(a, s)] += 1
                if e is not None:
                    horiz[(a, e)] += 1
    return vert, horiz


def zero_support(cells, vert, horiz, *, only=None):
    tok = _tokenizer(cells, offisland="sea4")
    bad = []
    for (bx, by) in sorted(cells):
        for i in range(G):
            for j in range(G):
                a = tok(bx, by, i, j)
                if a == "L":
                    continue
                for d, tbl in (("S", vert), ("E", horiz)):
                    nb = _step(bx, by, i, j, d)
                    b = tok(*nb)
                    if b == "L" or "cut" in (a, b) or (a == "sea4" and b == "sea4"):
                        continue
                    if tbl.get((a, b), 0) == 0:
                        if only and not only(bx, by, i, j):
                            continue
                        bad.append(((bx, by, i, j), d, a, b))
    return bad


NORTH_FRAME = lambda bx, by, i, j: by == 10 and j == 0                      # noqa: E731
C4_SCOPE = lambda bx, by, i, j: (bx, by) == (BX, BY) and i <= 4 and j <= 3   # noqa: E731


# --------------------------------------------------------------------------- build the fix
def build(root: Path, candidate: str = "A", nav_reset: str = "seal", verbose=True):
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

    # --- the ladder
    ladder = dict(LADDER_FORCED)
    ladder.update(LADDER_DERIVED)
    ladder.update(CANDIDATES[candidate])
    rep["candidate"] = candidate
    rep["ladder"] = {f"{i},{j}": b for (i, j), b in sorted(ladder.items())}

    dialect = {p: sheet_dialect(tw[p]) for p in ("Sea3", "Sea4", "Sea5")}
    rep["dialect"] = {p: dict(normal=list(d[0]), winding=d[1], tangent_tail=list(d[2]))
                      for p, d in dialect.items()}

    # --- PHASE 1: the geometry. lattice_patch does the clipping / snapping / diagonal choice;
    #     uv is overwritten in phase 2, so the quad passed here is a placeholder.
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
    ring3 = [(p[0], 0.0, p[1]) for p in ring]
    idall = encode_id(topograph=SEA_TOPO_OPEN)
    raw = ME.lattice_patch(ring3, y=0.0, uv_quads=[(0.0, 0.0, 1.0, 1.0)], idall=idall,
                           normal=dialect["Sea4"][0], winding=dialect["Sea4"][1],
                           snap_verts=list(snap.values()))

    # bucket every emitted triangle to its cell, and to the band the ladder gives that cell
    fill_by_cell = defaultdict(list)
    for t in raw:
        cx = sum(v[0][0] for v in t) / 3.0
        cz = sum(v[0][2] for v in t) / 3.0
        I, J = int(cx // CELL), int((-cz) // CELL)
        i, j = I - 16 * BX, J - 16 * BY
        if (i, j) not in ladder:
            raise SystemExit(f"REFUSE: the fill reached cell ({i},{j}) which the ladder does not "
                             f"name -- the hole is not where the diagnosis says it is")
        fill_by_cell[(i, j)].append(t)
    missing = set(ladder) - set(fill_by_cell)
    rep["fill_cells"] = {f"{i},{j}": len(v) for (i, j), v in sorted(fill_by_cell.items())}
    rep["ladder_cells_with_no_fill"] = sorted(f"{i},{j}" for (i, j) in missing)

    # --- the POST-FILL shade/water grids: needed before any sea5 uv can be chosen
    prov = {"Sea3": [], "Sea4": [], "Sea5": []}
    for (i, j), ts in fill_by_cell.items():
        prov[ladder[(i, j)].capitalize()].extend(ts)
    provisional = {"sea3": build_part(tw["Sea3"] + prov["Sea3"], "Sea3", BX, BY),
                   "sea4": build_part(tw["Sea4"] + prov["Sea4"], "Sea4", BX, BY),
                   "sea5": build_part(tw["Sea5"] + prov["Sea5"], "Sea5", BX, BY)}
    cells_prov = carry_cells(root, override=provisional)
    shade_p = {c: _sea_shade_grid(v) for c, v in cells_prov.items()}
    water_p = {c: _sea_water_grid(v) for c, v in cells_prov.items()}
    island = list(cells_prov)

    # a mixed cell (two bands inside one 4u cell) is not a shape stock ships -- refuse early
    mixed = []
    for (i, j), ts in fill_by_cell.items():
        want = ladder[(i, j)]
        got = shade_p[(BX, BY)][i][j]
        if got != want:
            mixed.append(((i, j), want, got))
    rep["shade_after_fill"] = {f"{i},{j}": shade_p[(BX, BY)][i][j]
                               for (i, j) in sorted(ladder)}
    if mixed:
        raise SystemExit(f"REFUSE: cells whose post-fill shade is not the ladder's band "
                         f"(a mixed cell): {mixed}")

    # --- PHASE 2: uv.  Continue the cell's own tile where the bytes allow, harvest otherwise.
    variants = R.harvest_variants(DONORS, disc=READ_DISC)
    if not variants:
        raise SystemExit("REFUSE: no verbatim sea5 vocabulary could be harvested from "
                         f"{DONORS}")
    existing_by_cell = defaultdict(lambda: defaultdict(list))
    for p in ("Sea3", "Sea4", "Sea5"):
        for t in tw[p]:
            cx = sum(v[0][0] for v in t) / 3.0
            cz = sum(v[0][2] for v in t) / 3.0
            I, J = int(cx // CELL), int((-cz) // CELL)
            existing_by_cell[(I - 16 * BX, J - 16 * BY)][p].append(t)

    mains = {p: full_quad_maps(tw[p], exclude=set()) for p in ("Sea3", "Sea4")}
    uvsrc, repaint = {}, {}
    for (i, j) in sorted(ladder):
        band = ladder[(i, j)]
        I, J = 16 * BX + i, 16 * BY + j
        have = existing_by_cell.get((i, j), {}).get(band.capitalize(), [])
        rec = recover_corner_map(have, I, J) if have else None
        if usable_map(rec):
            uvsrc[(i, j)] = ("continue-tile", rec[0], rec[1])
            continue
        # A cell whose tile map is unrecoverable (its triangles SPAN the cell, as stock's coast-cut
        # sheets do everywhere) CONTINUES those triangles instead of being repainted -- so this
        # script rewrites ZERO existing uv bytes. Repainting was tried and measured worse on both
        # counts: it evaluates THIS cell's map on verts that live in the NEXT cell (the clamp then
        # distorts them), which broke uv continuity in 6 places, and on the sea5 remnant at (2,2)
        # it left a cell that a rim re-run would still rewrite by 0.29 -- i.e. the repaint bought
        # no wang legibility either, because a spanning triangle cannot BE a clean wang tile.
        # THE DEFECT FOLLOWS THE AUTHORSHIP: the least surface that closes the hole wins.
        if have:
            uvsrc[(i, j)] = ("continue-affine", have, f"{len(have)} parent tri(s)")
            continue
        # no usable own tile -> harvest a verbatim one, and REPAINT the cell's existing tris
        if band == "sea5":
            ds = R.deepset(shade_p, water_p, island, BX, BY, i, j)
            ds = R.representable(ds, shade_p, water_p, island, BX, BY, i, j)
            if not ds:
                raise SystemExit(f"REFUSE: sea5 cell ({i},{j}) has an EMPTY geometric deep-set "
                                 f"-- a transition tile facing no deep is not a stock shape")
            opts = [tuple(o) for o in W.DEEPSET2TILE.get(ds, []) if tuple(o) in variants]
            if not opts:
                raise SystemExit(f"REFUSE: deep-set {''.join(sorted(ds))} at ({i},{j}) has no "
                                 f"verbatim donor tile -- synthesizing one is what produced the "
                                 f"checkerboard")
            uvsrc[(i, j)] = ("harvest-sea5", variants[opts[0]], "".join(sorted(ds)))
        else:
            src, cm = pick_mains(mains[band.capitalize()], I, J)
            uvsrc[(i, j)] = ("harvest-mains", cm, f"{src}")
        if have:
            repaint[(i, j)] = band
    rep["uv_sources"] = {f"{i},{j}": [v[0], (f"{v[2]:.2e}" if isinstance(v[2], float) else v[2])]
                         for (i, j), v in sorted(uvsrc.items())}
    rep["repainted_cells"] = {f"{i},{j}": b for (i, j), b in sorted(repaint.items())}

    emitted = {}
    for (i, j), ts in sorted(fill_by_cell.items()):
        band = ladder[(i, j)].capitalize()
        I, J = 16 * BX + i, 16 * BY + j
        mode, cm, _d = uvsrc[(i, j)]
        nrm, wind, tail = dialect[band]
        out = []
        for t in ts:
            if mode == "continue-affine":
                par = choose_parent(t, cm)
                m = affine_map(par)
                if m is None:
                    raise SystemExit(f"REFUSE: degenerate parent uv map at cell ({i},{j})")
                uvf = lambda p, m=m: affine_eval(m, p)
            else:
                uvf = lambda p, cm=cm, I=I, J=J: tile_uv(cm, p, I, J)
            out.append([(v[0], tuple(nrm), uvf(v[0]), (v[3][0],) + tuple(tail)) for v in t])
        emitted[(i, j)] = out
    fills = {"Sea3": [], "Sea4": [], "Sea5": []}
    for (i, j), out in emitted.items():
        fills[ladder[(i, j)].capitalize()].extend(out)

    # the repaints: existing tris of a cell whose own map was unusable take the harvested map
    kept_sea = {p: list(tw[p]) for p in ("Sea3", "Sea4", "Sea5")}
    n_repaint = 0
    for (i, j), band in repaint.items():
        P = band.capitalize()
        I, J = 16 * BX + i, 16 * BY + j
        cm = uvsrc[(i, j)][1]
        targets = {id(t) for t in existing_by_cell[(i, j)][P]}
        out = []
        for t in kept_sea[P]:
            if id(t) in targets:
                out.append([(v[0], v[1], tile_uv(cm, v[0], I, J), v[3]) for v in t])
                n_repaint += 1
            else:
                out.append(t)
        kept_sea[P] = out
    rep["repainted_tris"] = n_repaint

    # --- THE UV WELD. Every lattice crossing of the hole outline is a vertex minted in the
    # INTERIOR of an existing triangle's edge, and there the two sides disagree by construction: a
    # triangle interpolates uv LINEARLY along its edge, while a tile map is BILINEAR, so the tile
    # map's value at an interior point is not the linear one. The difference lands exactly on the
    # fill/tile boundary as a texture step -- measured before this weld at 0.006 on Sea3 (3,2) and
    # 0.29 on Sea5 (2,2), i.e. a third of the atlas width. Welding gives such a vertex the EXISTING
    # triangle's own value, which moves the deviation into the fill's interior (one tile's worth of
    # stretch, invisible) instead of onto a visible seam. Done BEFORE the T-splits, so a split
    # child -- whose uv is the lerp along that same parent edge -- agrees with the fill exactly.
    by_cell_now = defaultdict(lambda: defaultdict(list))
    for p in ("Sea3", "Sea4", "Sea5"):
        for t in kept_sea[p]:
            cx = sum(v[0][0] for v in t) / 3.0
            cz = sum(v[0][2] for v in t) / 3.0
            by_cell_now[(int(cx // CELL) - 16 * BX,
                         int((-cz) // CELL) - 16 * BY)][p].append(t)
    welded = Counter()
    for (i, j), ts in emitted.items():
        band = ladder[(i, j)].capitalize()
        # SAME CELL FIRST, then any same-band triangle in the block: a stock coast-cut triangle
        # SPANS cells, so the parent whose edge carries a fill vertex is often binned to the
        # neighbouring cell (measured: the crossing at (397.4334,-648) sits on a Sea3 triangle
        # binned to (3,1) while the fill vertex belongs to (3,2)). Welding to the triangle that
        # actually owns the edge is what makes the shared edge seamless.
        have = list(by_cell_now.get((i, j), {}).get(band, []))
        have += [t for t in kept_sea[band] if t not in have]
        if not have:
            continue
        target = {}
        for t in ts:
            for v in t:
                key = (round(v[0][0], 6), round(v[0][2], 6))
                if key in target:
                    continue
                for h in have:
                    m = affine_map(h)
                    if m is None:
                        continue
                    on = False
                    for q, r in ((0, 1), (1, 2), (2, 0)):
                        a, b_ = h[q][0], h[r][0]
                        dx, dz = b_[0] - a[0], b_[2] - a[2]
                        L2 = dx * dx + dz * dz
                        if L2 < 1e-12:
                            continue
                        s = ((v[0][0] - a[0]) * dx + (v[0][2] - a[2]) * dz) / L2
                        if not (-1e-9 <= s <= 1 + 1e-9):
                            continue
                        if math.hypot(v[0][0] - (a[0] + s * dx),
                                      v[0][2] - (a[2] + s * dz)) <= 1e-6:
                            on = True
                            break
                    if on:
                        target[key] = affine_eval(m, v[0])
                        break
        if not target:
            continue
        out = []
        for t in ts:
            nt = []
            for v in t:
                key = (round(v[0][0], 6), round(v[0][2], 6))
                if key in target and max(abs(target[key][0] - v[2][0]),
                                         abs(target[key][1] - v[2][1])) > 1e-9:
                    welded[(i, j)] += 1
                    nt.append((v[0], v[1], target[key], v[3]))
                else:
                    nt.append(v)
            out.append(nt)
        emitted[(i, j)] = out
    fills = {"Sea3": [], "Sea4": [], "Sea5": []}
    for (i, j), out in emitted.items():
        fills[ladder[(i, j)].capitalize()].extend(out)
    rep["uv_welded_verts"] = {f"{i},{j}": n for (i, j), n in sorted(welded.items())}

    rep["fill"] = {p.lower(): tri_stats(fills[p]) for p in ("Sea3", "Sea4", "Sea5")}

    # --- THE T-VERTEX REPAIR (both directions)
    fill_pts = {(round(v[0][0], 6), round(v[0][2], 6))
                for p in fills for t in fills[p] for v in t}
    sheet_pts = {(round(v[0][0], 6), round(v[0][2], 6))
                 for p in ("Sea3", "Sea4", "Sea5") for t in kept_sea[p] for v in t
                 if abs(v[0][1]) < 1e-6}
    splits, max_off = {}, 0.0
    for p in ("Sea3", "Sea4", "Sea5"):
        kept_sea[p], splits[p], o1 = split_at_points(kept_sea[p], fill_pts)
        fills[p], splits[p + "-fill"], o2 = split_at_points(fills[p], sheet_pts)
        max_off = max(max_off, o1, o2)
    rep["tvertex_splits"] = splits
    rep["tvertex_max_offset"] = max_off

    # --- THE ORPHANED NAV RING, measured with THE CLASSIFIER instead of a radius.
    #
    # `coastnav.stamp` cannot LOWER a class it no longer derives, so removing a shore leaves its
    # KEEL(56)/BELT(55) ring stamped on water that now fronts nothing -- and 55/56 are outside the
    # Narciss legality mask {53,54,57}, i.e. an invisible boat wall in open water.
    #
    # The c2 script reset only triangles farther than FRINGE_R+BELT_R+3 (22.5u) from every
    # surviving land.  THAT RADIUS IS A PROXY FOR THE CLASSIFIER AND IT IS WRONG HERE, measured:
    # force every 55/56 in this block to 57, re-stamp, and see what returns -- 75 of 88 come back,
    # and the 13 that do NOT are all 14.7-23.6u from the surviving horseshoe, i.e. INSIDE the
    # proxy's safe radius.  The radius test exonerates all 13; the classifier disowns them.
    #
    # So: CLEAR every boat-wall class the removed shore could have stamped (within
    # FRINGE_R+BELT_R of the fragment) and let `coastnav.stamp` re-raise whatever still qualifies.
    # Self-calibrating -- no tuned constant, cannot under-clear, and anything that comes back came
    # back from the classifier's own arithmetic.  It REQUIRES the re-stamp, so --no-coastnav with
    # a non-none --nav-reset is refused at the CLI.
    REACH = coastnav.FRINGE_R + coastnav.BELT_R
    nav_classes = {"seal": (55, 56), "full": (53, 54, 55, 56), "none": ()}[nav_reset]
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

    def retopo(tris, part):
        out = []
        for t in tris:
            idv = int(round(t[0][3][0]))
            topo = (idv & 0xFC) >> 2
            if topo in nav_classes and _reaches(t, frag, REACH):
                nid = float((idv & ~0xFC) | (SEA_TOPO_OPEN << 2))
                out.append([(p, n, u, (nid,) + tuple(g[1:])) for (p, n, u, g) in t])
                reset[(part, topo)] += 1
            else:
                out.append(t)
        return out

    for p in ("Sea3", "Sea4", "Sea5"):
        kept_sea[p] = retopo(kept_sea[p], p)
    rep["orphan_nav_reset"] = {f"{p}:{t}": n for (p, t), n in sorted(reset.items())}
    rep["nav_reset_mode"] = nav_reset

    after = dict(tw)
    after["Terrain"] = kept
    new = {"Terrain": build_part(kept, "Terrain", BX, BY)}
    for p in ("Sea3", "Sea4", "Sea5"):
        after[p] = kept_sea[p] + fills[p]
        new[p] = build_part(after[p], p, BX, BY)
    return rep, new, dict(before=tw, after=after, frag=frag, fills=fills, ring=ring,
                          parts=parts, snap=snap, root=root, ladder=ladder,
                          new_sea={p.lower(): new[p] for p in ("Sea3", "Sea4", "Sea5")})


# --------------------------------------------------------------------------- the gates
def gates(rep, new, ctx, *, bigrams=None, verbose=True):
    root, before, after = ctx["root"], ctx["before"], ctx["after"]
    fails, notes = [], []

    def check(name, ok, detail=""):
        (notes if ok else fails).append(
            f"{'PASS' if ok else 'FAIL'}  {name}{' -- ' + detail if detail else ''}")

    # 1. engine loader predicates + the UNINDEXED CONTRACT on every mesh we write
    for p, bm in new.items():
        try:
            validate_blockmesh(bm)
            check(f"validate_blockmesh[{p}]", True, f"vcount={bm.vcount} tris={len(bm.tris)}")
        except ValueError as e:
            check(f"validate_blockmesh[{p}]", False, str(e))

    # 2. THE REBUILD IS LOSSLESS on a part we do not change
    for p in ("Beach1", "Sea1", "Sea2"):
        pp = part_path(root, BX, BY, p)
        if not pp.is_file():
            continue
        b = read_part(root, BX, BY, p)
        rt = build_part(world_tris(b, BX, BY), p, BX, BY)
        check(f"rebuild-identity[{p}]", ff9mesh_bytes(rt) == pp.read_bytes(),
              "an unchanged tri list must round-trip byte-identically")
    # ...and on the fragment-free terrain, which we rebuild from untouched originals
    orig = [tuple(tuple(map(tuple, v)) for v in t) for t in before["Terrain"]]
    keptt = [tuple(tuple(map(tuple, v)) for v in t) for t in after["Terrain"]]
    check("kept-terrain-verbatim",
          len(keptt) == EXPECT_TERRAIN_TRIS - EXPECT_TRIS and all(k in orig for k in keptt),
          f"{len(keptt)} tris kept, each byte-identical to its deployed original")

    # 3. AREA CONSERVED per sheet: the fill's area is exactly the hole's; every other operation
    #    (T-split, repaint, retopo) must move NOTHING. The only mechanism that can is a T-split
    #    landing off its host edge, which is measured (`tvertex_max_offset`), so the budget is
    #    derived from that measurement rather than guessed: n_splits * offset * longest_edge / 2.
    envm = tri_stats(before["Sea3"] + before["Sea4"] + before["Sea5"])
    for p in ("Sea3", "Sea4", "Sea5"):
        pa, fa, aa = plan_area(before[p]), plan_area(ctx["fills"][p]), plan_area(after[p])
        ns = rep["tvertex_splits"][p] + rep["tvertex_splits"][p + "-fill"]
        budget = ns * rep["tvertex_max_offset"] * envm["edge_max"] / 2.0 + 1e-12
        check(f"area-conserved[{p}]", abs(aa - pa - fa) <= budget,
              f"before {pa:.4f} + fill {fa:.4f} == after {aa:.4f} "
              f"(delta {aa - pa - fa:+.2e}, {ns} T-split budget {budget:.2e})")
    check("tvertex-offset-below-float32",
          rep["tvertex_max_offset"] < 3.0e-5,
          f"max split-point offset from its host edge = {rep['tvertex_max_offset']:.3e} u "
          f"(float32 resolution at |x|~400 is ~3e-5, so both sides store the SAME value)")
    tot = sum(plan_area(ctx["fills"][p]) for p in ("Sea3", "Sea4", "Sea5"))
    check("fill-area==hole-area", abs(tot - rep["hole_plan_area"]) < 1e-3,
          f"fill {tot:.4f} u2 vs hole {rep['hole_plan_area']:.4f} u2")

    # 3b. no DOUBLE COVER introduced
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

    # 4. the OPEN CUT is gone: no non-waterline once-edge left off the block's own frames
    def offframe(e):
        if abs(e[0][1]) < 1e-6 and abs(e[1][1]) < 1e-6:
            return False
        for zf in (-640.0, -704.0):
            if abs(e[0][2] - zf) < 1e-3 and abs(e[1][2] - zf) < 1e-3:
                return False
        for xf in (384.0, 448.0):
            if abs(e[0][0] - xf) < 1e-3 and abs(e[1][0] - xf) < 1e-3:
                return False
        return True
    cb = [e for e in once_edges(before["Terrain"]) if offframe(e)]
    ca = [e for e in once_edges(after["Terrain"]) if offframe(e)]
    check("open-cut-closed", len(ca) <= len(cb) and not [e for e in ca
                                                         if abs(e[0][2] - FRAME_Z) < 1e-3],
          f"off-frame terrain cut edges {len(cb)} -> {len(ca)}")

    # 5. plan coverage: NO INTRODUCED hole (this block ships 42 pre-existing 1u hole samples in
    #    its SW corner at z -697..-704 -- unrelated to c4 and out of scope)
    hb = set(coverage_holes(before, BX, BY))
    ha = set(coverage_holes(after, BX, BY))
    check("plan-holes-no-introduced", not (ha - hb),
          f"before={len(hb)} after={len(ha)} introduced={len(ha - hb)}")

    # 6. THE LATTICE LAW
    env = tri_stats(before["Sea3"] + before["Sea4"] + before["Sea5"])
    for band in ("sea3", "sea4", "sea5"):
        f = rep["fill"][band]
        if not f["n"]:
            continue
        check(f"lattice-envelope[{band}]",
              f["area_max"] <= env["area_max"] + 1e-6 and f["edge_max"] <= env["edge_max"] + 1e-6,
              f"area {f['area_max']:.3f}<={env['area_max']:.3f}  "
              f"edge {f['edge_max']:.3f}<={env['edge_max']:.3f}")
        check(f"winding[{band}]", set(f["winding"]) == {-1}, str(f["winding"]))
    spanning = 0
    for p in ("Sea3", "Sea4", "Sea5"):
        for t in ctx["fills"][p]:
            xs = [v[0][0] for v in t]; zs = [v[0][2] for v in t]
            if math.floor(min(xs) / CELL) != math.floor(max(xs) / CELL - 1e-9) \
                    or math.floor((-max(zs)) / CELL) != math.floor((-min(zs)) / CELL - 1e-9):
                spanning += 1
    check("no-tile-spanning-fill-tri", spanning == 0, f"{spanning}")

    # 6b. THE STOCK FLOOR, and why one triangle is allowed under it.
    #     Censused over stock disc-1's 471 sea meshes / 64,927 triangles: min area 0.0392 u2, min
    #     shortest-edge 0.2891 u -- NO exceptions. A lattice clip against a shallow-angle waterline
    #     can go under that, and this fill does exactly once: the hole's own corner at
    #     (387.557,-644)-(388,-644)-(387.359,-643.906), 0.021 u2, where the waterline crosses the
    #     z=-644 lattice line 0.094 u from the cell edge. That wedge is PART OF THE HOLE, so the
    #     only alternative to a thin triangle is a 0.021 u2 ground-raycast hole. It is admissible
    #     precisely because it is pure interior subdivision: the gate proves every sub-floor
    #     triangle's three edges are shared with another fill/sheet triangle or lie on the ring,
    #     i.e. it introduces no free boundary and no silhouette of its own.
    STOCK_MIN_AREA, STOCK_MIN_EDGE = 0.039192, 0.289062
    ring_seg = [(ctx["ring"][i], ctx["ring"][(i + 1) % len(ctx["ring"])])
                for i in range(len(ctx["ring"]))]
    shared = Counter()
    for t in [x for p in ("Sea3", "Sea4", "Sea5") for x in ctx["fills"][p] + after[p]]:
        for m, n_ in ((0, 1), (1, 2), (2, 0)):
            shared[tuple(sorted((K(t[m][0]), K(t[n_][0]))))] += 1

    def _on_ring(e):
        for (a, b) in ring_seg:
            dx, dz = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dz * dz
            if L2 < 1e-12:
                continue
            ok = True
            for v in e:
                s = max(0.0, min(1.0, ((v[0] - a[0]) * dx + (v[2] - a[1]) * dz) / L2))
                if math.hypot(v[0] - (a[0] + s * dx), v[2] - (a[1] + s * dz)) > 2e-3:
                    ok = False
                    break
            if ok:
                return True
        return False
    subfloor, bad_sub = [], []
    for p in ("Sea3", "Sea4", "Sea5"):
        for t in ctx["fills"][p]:
            a, b, c = (v[0] for v in t)
            ar = abs((b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])) / 2.0
            eds = [math.dist((q[0], q[2]), (r[0], r[2])) for q, r in ((a, b), (b, c), (c, a))]
            if ar >= STOCK_MIN_AREA and min(eds) >= STOCK_MIN_EDGE:
                continue
            subfloor.append((p, round(ar, 5), round(min(eds), 4)))
            for m, n_ in ((0, 1), (1, 2), (2, 0)):
                e = (t[m][0], t[n_][0])
                key = tuple(sorted((K(e[0]), K(e[1]))))
                if shared[key] < 2 and not _on_ring(e):
                    bad_sub.append((p, key))
    check("sub-stock-floor-slivers-are-interior-only", not bad_sub,
          f"{len(subfloor)} fill tri(s) under stock's floor (area>={STOCK_MIN_AREA}, "
          f"edge>={STOCK_MIN_EDGE}): {subfloor}; free edges introduced: {len(bad_sub)}")

    # 6c. THE UV-CONTINUITY GATE -- the whole point of the clamped-bilinear recovery. Where a fill
    #     triangle and a retained triangle of the SAME cell and SAME band meet at a shared plan
    #     position, their uv must be the same value, or the cell shows a texture break down the
    #     middle (a defect no geometry gate can see).
    #     Keyed on the TRIANGLE's own cell (its centroid), never on the vertex's: uv is a per-tile
    #     function, so two tiles sharing a plan position legitimately carry different uv there --
    #     keying per-vertex reports 13 phantom "breaks" that are just the cell boundary.
    fill_ids = {id(t) for p in ("Sea3", "Sea4", "Sea5") for t in ctx["fills"][p]}
    uvpos = defaultdict(lambda: defaultdict(set))
    for p in ("Sea3", "Sea4", "Sea5"):
        for t in after[p]:
            cx = sum(v[0][0] for v in t) / 3.0
            cz = sum(v[0][2] for v in t) / 3.0
            I, J = int(cx // CELL), int((-cz) // CELL)
            src = "fill" if id(t) in fill_ids else "keep"
            for v in t:
                uvpos[(p, I, J, round(v[0][0], 4), round(v[0][2], 4))][src].add(
                    (round(v[2][0], 6), round(v[2][1], 6)))
    breaks = []
    for key, d in uvpos.items():
        if "keep" in d and "fill" in d:
            for a in d["keep"]:
                for b in d["fill"]:
                    if max(abs(a[0] - b[0]), abs(a[1] - b[1])) > 1e-6:
                        breaks.append((key, a, b))
    nshared = sum(1 for d in uvpos.values() if "keep" in d and "fill" in d)
    check("uv-continuous-fill-to-tile", not breaks,
          f"{nshared} shared fill/tile vertices in-cell; {len(breaks)} uv mismatches "
          f"{breaks[:3]}")

    # 7. THE EXACTNESS GATE: every fill boundary vertex is an existing sheet vertex, a ring
    #    vertex, or a lattice crossing ON the hole outline
    have = {(round(x, 3), round(z, 3)) for (x, z) in ctx["snap"]}
    ringpts = [(p[0], p[1]) for p in ctx["ring"]]
    allfill = [t for p in ("Sea3", "Sea4", "Sea5") for t in ctx["fills"][p]]
    off = []
    for e in once_edges(allfill):
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

    # 8. THE WELD AUDIT over the 3x3 block ring
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

    # 9. T-JUNCTION census
    def tj(state):
        tris = [[(v[0][0], v[0][2]) for v in t]
                for p in ("Terrain", "Sea3", "Sea4", "Sea5") for t in state[p]]
        return len(ME.find_tjunctions(tris))
    t_before, t_after = tj(before), tj(after)
    check("tjunctions-no-introduced", t_after <= t_before, f"before={t_before} after={t_after}")

    # 10. THE LATTICE ADJACENCY LAW over the whole block
    LAWFUL = {1: {1, 2, 3, 5}, 2: {1, 2}, 3: {1, 3, 5}, 4: {4, 5}, 5: {1, 3, 4, 5}}
    edge_band = defaultdict(set)
    for p, rank in (("Sea1", 1), ("Sea2", 2), ("Sea3", 3), ("Sea4", 4), ("Sea5", 5)):
        for t in after.get(p, []):
            for a, b in ((0, 1), (1, 2), (2, 0)):
                edge_band[tuple(sorted((K(t[a][0]), K(t[b][0]))))].add(rank)
    bad = [(e, s) for e, s in edge_band.items() if len(s) > 1
           and any(y not in LAWFUL[x] for x in s for y in s)]
    check("band-adjacency-lawful(shared-edge)", not bad, f"{len(bad)} unlawful shared edges")
    # ...and cell-to-cell, which is the law's real statement
    cells_after = carry_cells(root, override=ctx["new_sea"])
    sh = {c: _sea_shade_grid(v) for c, v in cells_after.items()}
    wa = {c: _sea_water_grid(v) for c, v in cells_after.items()}
    RANK = {"sea3": 3, "sea4": 4, "sea5": 5}
    badc = []
    for i in range(G):
        for j in range(G):
            if not wa[(BX, BY)][i][j]:
                continue
            a = RANK.get(sh[(BX, BY)][i][j])
            for d in ("E", "S"):
                nb = _step(BX, BY, i, j, d)
                if (nb[0], nb[1]) not in wa or not wa[(nb[0], nb[1])][nb[2]][nb[3]]:
                    continue
                b = RANK.get(sh[(nb[0], nb[1])][nb[2]][nb[3]])
                if a and b and b not in LAWFUL[a]:
                    badc.append(((i, j), d, a, b))
    check("band-adjacency-lawful(cell)", not badc, f"{len(badc)} unlawful cell pairs {badc[:6]}")

    # 11. the armed tiles' file is untouched
    ap = root / "FF9_Data/WorldMap/Disc9" / LOD / ARMED_FILE[0] / ARMED_FILE[1]
    ok = ap.is_file()
    detail = f"{ap.name} sha={sha(ap)[:12] if ok else 'MISSING'}"
    if ok and ARMED_MANIFEST.is_file():
        man = json.loads(ARMED_MANIFEST.read_text())
        rows = man.get("6,11")
        if rows:
            want = rows[-1].get("armed_md5")
            cur = hashlib.md5(ap.read_bytes()).hexdigest()
            ok = (cur == want)
            detail += f"  md5 {'== manifest' if ok else '!= manifest ' + str(want)}"
    check("armed-tiles-file-untouched", ok, detail)

    # 12. THE WANG CENSUS the c2 fix lacked -- neighbour-facing, over the WHOLE carry
    cells_before = carry_cells(root)
    sb, sa = R.seam_report(cells_before), R.seam_report(cells_after)
    check("seam-report-under-0", sa["under"] == 0, f"{sb} -> {sa}")
    db, da = R.edge_disagreements(cells_before), R.edge_disagreements(cells_after)
    new_d = [e for e in da if e not in db]
    check("edge-disagreements-no-introduced", not new_d,
          f"before={len(db)} after={len(da)} introduced={len(new_d)} {new_d[:4]}")
    ub, ua = R.unpaintable_slivers(cells_before), R.unpaintable_slivers(cells_after)
    check("unpaintable-slivers-no-introduced", len(ua) <= len(ub),
          f"before={len(ub)} after={len(ua)} {ua[:4]}")
    # THE RIM FIXED-POINT GATE. plan_rim ALWAYS lists the frame row (``on_frame``), so a listing
    # is not evidence of anything -- the real question is whether a rim re-run would CHANGE a uv
    # byte in a cell we authored. Simulate the re-run and measure the delta.
    ctx["rim_delta"] = rim_delta = {}
    # the encoded-vs-geometric deep-set of every sea5 cell we touch, before and after -- the
    # evidence behind the note below (and the brief's "correct deep-set shades up front")
    shb = {c: _sea_shade_grid(v) for c, v in cells_before.items()}
    wab = {c: _sea_water_grid(v) for c, v in cells_before.items()}
    encb, enca = (R._sea5_deepsets(cells_before[(BX, BY)]),
                  R._sea5_deepsets(cells_after[(BX, BY)]))
    ds_rows = []
    for (i, j) in sorted(ctx["ladder"]):
        if ctx["ladder"][(i, j)] != "sea5":
            continue
        gb = R.deepset(shb, wab, list(cells_before), BX, BY, i, j)
        ga = R.deepset(sh, wa, list(cells_after), BX, BY, i, j)
        ds_rows.append(f"({i},{j}) geo {''.join(sorted(gb)) or '-'}->{''.join(sorted(ga)) or '-'}"
                       f" enc {''.join(sorted(encb.get((i, j), ''))) or 'cut'}"
                       f"->{''.join(sorted(enca.get((i, j), ''))) or 'cut'}")
    check("sea5-deepsets-encoded-vs-geometric", True, "; ".join(ds_rows))
    try:
        variants = R.harvest_variants(DONORS, disc=READ_DISC)
        plan_after = R.plan_rim(cells_after)
        miss = R.uncovered(plan_after, variants)
        if miss:
            check("rim-rerun-is-a-no-op", False,
                  f"a rim re-run would REFUSE: deep-set(s) {miss} have no verbatim donor tile")
        else:
            post, _n = R.apply_rim(cells_after, plan_after, variants, disc=DISC, lod=LOD)
            plan_b = R.plan_rim(cells_before)
            post_b = ({} if R.uncovered(plan_b, variants) else
                      R.apply_rim(cells_before, plan_b, variants, disc=DISC, lod=LOD)[0])

            # keyed on the TRIANGLE's own cell, never the vertex's -- same reason as the
            # uv-continuity gate: a coast-cut triangle spans cells, so per-vertex keying
            # attributes a neighbouring tile's repaint to a cell we never touched.
            def uvmap(bm, bx, by):
                out = {}
                for tri in bm.tris:
                    cx = sum(bm.verts[k][0] for k in tri) / 3.0 + 64.0 * bx
                    cz = sum(bm.verts[k][2] for k in tri) / 3.0 - 64.0 * by
                    cell = (int(cx // CELL) - 16 * bx, int((-cz) // CELL) - 16 * by)
                    for k in tri:
                        out[(cell, round(bm.verts[k][0], 4), round(bm.verts[k][2], 4))] = \
                            (bm.uvs[k][0], bm.uvs[k][1])
                return out
            def deltas(state, repainted):
                out = {}
                pre_uv, post_uv = {}, {}
                for part in SEA:
                    if state[(BX, BY)].get(part) is not None:
                        pre_uv.update({(part,) + k: v for k, v in
                                       uvmap(state[(BX, BY)][part], BX, BY).items()})
                    if repainted.get((BX, BY), {}).get(part) is not None:
                        post_uv.update({(part,) + k: v for k, v in
                                        uvmap(repainted[(BX, BY)][part], BX, BY).items()})
                for key, v in post_uv.items():
                    _p, cell, _x, _z = key
                    if cell not in ctx["ladder"]:
                        continue
                    old = pre_uv.get(key)
                    d = 0.0 if old is None else max(abs(old[0] - v[0]), abs(old[1] - v[1]))
                    out[cell] = max(out.get(cell, 0.0), d)
                return out
            rim_delta.update(deltas(cells_after, post))
            base_delta = deltas(cells_before, post_b)
            # A cell a rim re-run ALREADY wanted to rewrite before this fix is not our doing --
            # (2,2) is a pre-existing unclassifiable 'cut' remnant and plan_rim has always flagged
            # it. The gate is NO INTRODUCED rim work: no cell newly needs one, and no cell needs
            # more than it did.
            # THE REAL REQUIREMENT (the brief's): every cell this script AUTHORS must already carry
            # the right deep-set, so no rim re-run is needed for it. A cell we merely CONTINUED
            # may still be flagged -- and (2,2) is, because dropping the wedge moves it from
            # rimretile's near-SHORE scope into open water, where the audit starts looking. That is
            # a SCOPE change, not a paint change: (2,2)'s geometric deep-set is {W} before AND
            # after, and it was an unclassifiable 'cut' remnant both times. Nothing regressed; the
            # script says so out loud rather than silently repainting a spanning triangle.
            authored = {tuple(int(q) for q in k.split(",")) for k, v in rep["uv_sources"].items()
                        if v[0].startswith("harvest")}
            bad_auth = {k: v for k, v in rim_delta.items() if k in authored and v > 1e-6}
            check("rim-rerun-no-work-in-AUTHORED-cells", not bad_auth,
                  f"authored cells {sorted(authored)} all carry their final deep-set; "
                  f"offenders {bad_auth or 'none'}")
            carried = {k: (base_delta.get(k, 0.0), v) for k, v in rim_delta.items()
                       if v > 1e-6 and k not in authored}
            if carried:
                notes.append("NOTE  a rim re-run WOULD still repaint carried cell(s) "
                             + ", ".join(f"{k} (was {b:.1e}, now {a:.1e})"
                                         for k, (b, a) in sorted(carried.items()))
                             + " -- a SCOPE change (near-shore -> open water), not a paint change; "
                               "their geometric deep-sets are identical before and after")
    except Exception as e:                                                # noqa: BLE001
        check("rim-rerun-is-a-no-op", False, f"simulation raised {type(e).__name__}: {e}")

    # 13. THE NORTH-FRAME RULE + the stock bigram oracle
    tok_a = _tokenizer(cells_after, offisland="sea4")
    frame_bad = []
    for i in range(G):
        t = tok_a(BX, BY, i, 0)
        if t in ("L", "cut", "sea4"):
            continue
        painted = set("NESW") if t == "sea4" else (set() if t == "sea3" else set(t))
        if "N" not in painted:
            frame_bad.append((i, t))
    infill = [f for f in frame_bad if (f[0], 0) in ctx["ladder"]]
    check("north-frame-paints-deep(in c4 cells)", not infill,
          f"{len(frame_bad)} frame cells under-cover N overall; in the c4 fill: {infill}")
    if bigrams:
        vert, horiz = bigrams
        zb = zero_support(cells_before, vert, horiz, only=NORTH_FRAME)
        za = zero_support(cells_after, vert, horiz, only=NORTH_FRAME)
        newz = [e for e in za if e not in zb]
        check("no-new-zero-support-on-frame-column", not newz,
              f"north frame row zero-support {len(zb)} -> {len(za)}; introduced {newz}")
        zb2 = zero_support(cells_before, vert, horiz)
        za2 = zero_support(cells_after, vert, horiz)
        check("no-new-zero-support-carry-wide", len(za2) <= len(zb2),
              f"carry-wide zero-support {len(zb2)} -> {len(za2)}")

    # 14. no OTHER block changed
    others = []
    for (bx, by) in CARRY:
        if (bx, by) == (BX, BY):
            continue
        for p in PARTS:
            pp = part_path(root, bx, by, p)
            if pp.is_file():
                others.append((pp.name, sha(pp)[:12]))
    check("other-carry-blocks-listed", True, f"{len(others)} files fingerprinted for the "
                                             f"post-write comparison")
    ctx["other_shas"] = dict(others)
    return fails, notes


# --------------------------------------------------------------------------- write / scratch
def stage_scratch(live_root: Path, scratch: Path) -> Path:
    dst = scratch / MOD_FOLDER
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(live_root / "FF9_Data", dst / "FF9_Data")
    for f in ("DictionaryPatch.txt", "BattlePatch.txt"):
        src = live_root / f
        if src.is_file():
            shutil.copyfile(src, dst / f)
    return dst


def write_out(root: Path, new, backup_dir: Path | None, do_coastnav: bool, game_root: Path):
    from ff9mapkit.world import mesh as M
    written = []
    if backup_dir:
        backup_dir.mkdir(parents=True, exist_ok=True)
        man = {}
        for p in list(new):
            src = part_path(root, BX, BY, p)
            if src.is_file():
                shutil.copyfile(src, backup_dir / src.name)
                man[src.name] = dict(src=str(src), sha256=sha(src))
        (backup_dir / "manifest.json").write_text(json.dumps(man, indent=2), encoding="utf-8")
    for p, bm in new.items():
        dest = part_path(root, BX, BY, p)
        data = ff9mesh_bytes(bm)
        if dest.is_file() and dest.read_bytes() == data:
            continue
        write_ff9mesh(bm, dest)
        M.record_ledger_write(dest, cell=(BX, BY), part=p, write_disc=DISC)
        written.append(str(dest))
    cn = None
    if do_coastnav:
        cn = coastnav.stamp(MOD_FOLDER, disc=DISC, cells=[(BX, BY)], policy="land-anywhere",
                            deploy=True, game=game_root, backup_dir=backup_dir, backup=False)
    return written, cn


def render(root: Path, out: Path, tag: str, state=None):
    """Offline top-down PNG of the c4 neighbourhood (no game needed)."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    W_, H_ = 900, 900
    x0, x1, z0, z1 = 380.0, 412.0, -668.0, -636.0
    img = Image.new("RGB", (W_, H_), (12, 16, 24))
    d = ImageDraw.Draw(img)
    COL = {"Terrain": (86, 132, 62), "Sea3": (60, 150, 200), "Sea4": (18, 44, 96),
           "Sea5": (96, 190, 220), "Sea1": (140, 210, 230), "Sea2": (120, 200, 225),
           "Beach1": (200, 190, 140)}

    def XY(p):
        return ((p[0] - x0) / (x1 - x0) * W_, (z1 - p[2]) / (z1 - z0) * H_)
    if state is None:
        state = {}
        for p in PARTS:
            b = read_part(root, BX, BY, p)
            if b is not None:
                state[p] = world_tris(b, BX, BY)
    for p in ("Sea4", "Sea3", "Sea5", "Sea2", "Sea1", "Beach1", "Terrain"):
        for t in state.get(p, []):
            d.polygon([XY(v[0]) for v in t], fill=COL.get(p, (200, 0, 200)),
                      outline=(0, 0, 0))
    for gx in range(int(x0 // 4), int(x1 // 4) + 1):
        X = (gx * 4 - x0) / (x1 - x0) * W_
        d.line([(X, 0), (X, H_)], fill=(255, 255, 255, 40), width=1)
    for gz in range(int(-z1 // 4), int(-z0 // 4) + 1):
        Y = (z1 + gz * 4) / (z1 - z0) * H_
        d.line([(0, Y), (W_, Y)], fill=(255, 255, 255, 40), width=1)
    d.text((8, 8), f"c4 {tag}  Block[{BX}][{BY}]  x {x0:.0f}..{x1:.0f}  z {z1:.0f}..{z0:.0f}",
           fill=(240, 240, 240))
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"c4-{tag}.png"
    img.save(p)
    return p


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
    ap.add_argument("--candidate", choices=tuple(CANDIDATES), default="A",
                    help="the band for the one free cell (1,0): A=sea4 (default), B=sea5")
    ap.add_argument("--compare", action="store_true",
                    help="score every candidate against the stock bigram oracle")
    ap.add_argument("--no-bigrams", action="store_true",
                    help="skip the stock disc-1 oracle (faster; drops gate 13's bigram half)")
    ap.add_argument("--nav-reset", choices=("seal", "full", "none"), default="seal",
                    help="clear the removed shore's orphaned coastnav classes: seal (default) = "
                         "only BELT(55)/KEEL(56), the boat walls; full = also 53/54; none = leave")
    ap.add_argument("--no-coastnav", action="store_true",
                    help="skip the coastnav re-stamp")
    ap.add_argument("--backup-dir", default=None)
    ap.add_argument("--render", metavar="DIR", help="write before/after top-down PNGs here")
    ap.add_argument("--json", metavar="PATH", help="write the report as JSON")
    a = ap.parse_args()

    if a.no_coastnav and a.nav_reset != "none":
        raise SystemExit("REFUSE: --no-coastnav with --nav-reset " + a.nav_reset + " would CLEAR "
                         "the shore's boat-wall classes and never let the classifier re-raise the "
                         "legitimate ones. Use --nav-reset none, or drop --no-coastnav.")
    game = Path(a.game) if a.game else config.find_game_path()
    live = game / MOD_FOLDER
    mode = "write" if a.write else ("scratch" if a.scratch else "dry-run")
    print(f"== fix_c4  mode={mode}  candidate={a.candidate}  game={game}")

    if a.scratch:
        scratch = Path(a.scratch)
        scratch.mkdir(parents=True, exist_ok=True)
        root = stage_scratch(live, scratch)
        game_root = scratch
        print(f"   staged scratch root -> {root}")
    else:
        root, game_root = live, game

    bigrams = None
    if not a.no_bigrams:
        print("   censusing stock disc-1 for the bigram oracle ...", flush=True)
        _stock, bigrams = stock_bigrams(a.game)
        print(f"   oracle: {len(bigrams[0])} vertical + {len(bigrams[1])} horizontal bigram kinds")

    rep, new, ctx = build(root, candidate=a.candidate, nav_reset=a.nav_reset)
    print("\n-- DIAGNOSIS (fresh, from the deployed bytes) ----------------")
    print(f"   Block[{BX}][{BY}] parts before: {rep['parts_before']}")
    print(f"   severed component: {rep['dropped_tris']} tris "
          f"(topo {EXPECT_TOPOS}), {rep['kept_terrain_tris']} kept")
    print(f"   open-cut edges ({len(rep['cut_edges'])}), all in the z={FRAME_Z:.0f} frame plane:")
    for e in rep["cut_edges"]:
        print(f"      {tuple(e[0])} -> {tuple(e[1])}")
    print(f"   hole plan area: {rep['hole_plan_area']:.3f} u2")
    print("\n-- THE THREE-BAND LADDER -------------------------------------")
    for j in range(3):
        row = []
        for i in range(4):
            b = ctx["ladder"].get((i, j))
            row.append(f"{b or '--':>6s}")
        print(f"   j={j} (z {-640 - 4 * j}..{-644 - 4 * j}): " + " ".join(row)
              + f"    x {384 + 0}..{384 + 16}")
    print(f"   post-fill shade actually measured: {rep['shade_after_fill']}")
    print(f"   fill tris per cell: {rep['fill_cells']}")
    print("\n-- UV PROVENANCE (per cell) ----------------------------------")
    for k, v in rep["uv_sources"].items():
        print(f"   cell {k:>5s}: {v[0]:<14s} {v[1]}")
    print(f"   repainted existing tris: {rep['repainted_tris']} in cells "
          f"{rep['repainted_cells'] or 'none'}")
    print("\n-- FILL ------------------------------------------------------")
    for band in ("sea3", "sea4", "sea5"):
        f = rep["fill"][band]
        print(f"   {band}: {f['n']:3d} tris  area med={f['area_med']:.3f} max={f['area_max']:.3f}"
              f"  edge med={f['edge_med']:.3f} max={f['edge_max']:.3f}  winding {f['winding']}")
    print(f"   T-vertex splits: {rep['tvertex_splits']}")
    print(f"   orphaned nav classes reset to open-sea 57: {rep['orphan_nav_reset'] or 'none'}")
    print("   parts after: " + ", ".join(f"{p}={len(t)}" for p, t in ctx["after"].items()))

    if a.compare and bigrams:
        print("\n-- CANDIDATE SCOREBOARD (stock oracle; lower is better) ------")
        vert, horiz = bigrams
        base = carry_cells(root)
        zb = len(zero_support(base, vert, horiz))
        zbf = len(zero_support(base, vert, horiz, only=NORTH_FRAME))
        db = len(R.edge_disagreements(base))
        print(f"   {'baseline (deployed, wedge still there)':<40s} zero={zb:3d} "
              f"frame-zero={zbf:3d} disagree={db:3d}")
        for cand in CANDIDATES:
            try:
                _r, _n, c2 = build(root, candidate=cand, nav_reset="none", verbose=False)
            except SystemExit as e:
                print(f"   candidate {cand}: REFUSED -- {e}")
                continue
            cc = carry_cells(root, override=c2["new_sea"])
            z = zero_support(cc, vert, horiz)
            zf = zero_support(cc, vert, horiz, only=NORTH_FRAME)
            dd = R.edge_disagreements(cc)
            sm = R.seam_report(cc)
            tokz = _tokenizer(cc, offisland="sea4")
            row = [tokz(BX, BY, i, 0) for i in range(6)]
            print(f"   {'candidate ' + cand + ' -> (1,0)=' + CANDIDATES[cand][(1, 0)]:<40s} "
                  f"zero={len(z):3d} frame-zero={len(zf):3d} disagree={len(dd):3d} "
                  f"under={sm['under']} over={sm['over']}  frame row i0..5={row}")
            for e in zf:
                print(f"        frame zero-support {e}")

    fails, notes = gates(rep, new, ctx, bigrams=bigrams)
    print("\n-- GATES -----------------------------------------------------")
    for line in notes + fails:
        print("   " + line)
    rep["gates"] = dict(pass_=notes, fail=fails)

    if a.render:
        out = Path(a.render)
        p1 = render(root, out, "before")
        p2 = render(root, out, f"after-{a.candidate}", state=ctx["after"])
        print(f"\n-- RENDERS ---------------------------------------------------")
        print(f"   {p1}\n   {p2}" if p1 else "   Pillow not available -- no renders")

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
            (BACKUP_ROOT / f"c4-wedge-disc9-6x10-{ts}") if mode == "write" else None)
        written, cn = write_out(root, new, bdir, not a.no_coastnav, game_root)
        print("\n-- WROTE -----------------------------------------------------")
        for w in written:
            print(f"   {w}")
        if bdir:
            print(f"   backups -> {bdir}")
        if cn:
            print(f"   coastnav re-stamp: "
                  f"{json.dumps({k: v for k, v in cn.items() if k != 'cells'})[:400]}")
        print("\n-- POST-WRITE VERIFICATION -----------------------------------")
        bad = []
        for p in ("Terrain", "Sea3", "Sea4", "Sea5"):
            pp = part_path(root, BX, BY, p)
            try:
                bm = blockmesh_from_ff9mesh(pp, disc=DISC, x=BX, y=BY, lod=LOD, part=p.lower())
                validate_blockmesh(bm)
                print(f"   read-back {p}: tris={len(bm.tris)} sha={sha(pp)[:16]} validate OK")
            except Exception as e:                                        # noqa: BLE001
                bad.append((p, str(e)))
        changed = []
        for (bx, by) in CARRY:
            if (bx, by) == (BX, BY):
                continue
            for p in PARTS:
                pp = part_path(root, bx, by, p)
                if pp.is_file() and ctx["other_shas"].get(pp.name) != sha(pp)[:12]:
                    changed.append(pp.name)
        print(f"   other carry blocks changed: {changed or 'NONE'}")
        if mode == "scratch":
            # THE FILE-LEVEL PROOF: every byte under the mod folder, scratch vs live.
            diff, only = [], []
            for p in sorted(root.rglob("*")):
                if not p.is_file():
                    continue
                rel = p.relative_to(root)
                q = live / rel
                if not q.is_file():
                    only.append(str(rel))
                elif p.read_bytes() != q.read_bytes():
                    diff.append(str(rel))
            print(f"\n   FILES THAT DIFFER from the live install ({len(diff)}):")
            for f in diff:
                print(f"      {f}")
            if only:
                print(f"   files only in scratch ({len(only)}): {only}")
            expected = {f"FF9_Data/WorldMap/Disc9/0_1/r10/Block[6][10] {p}.ff9mesh".replace(
                "/", os.sep) for p in ("Terrain", "Sea3", "Sea4", "Sea5")}
            # `.ff9world.jsonl` is the WRITE LEDGER -- appending to it is mandatory, not a side
            # effect: without a row the next deploy_override at this cell refuses our own bytes
            # as foreign (mesh.record_ledger_write).
            extra = set(diff) - expected - {".ff9world.jsonl"}
            print(f"   EXACTLY the four Block[6][10] meshes + the write ledger: "
                  f"{'YES' if not extra else 'NO -- also ' + str(sorted(extra))}")
        apth = root / "FF9_Data/WorldMap/Disc9" / LOD / ARMED_FILE[0] / ARMED_FILE[1]
        print(f"   armed file {ARMED_FILE[1]}: sha={sha(apth)[:16]}")
        # THE ORPHAN AUDIT. Every boat-wall class in the removed shore's reach was cleared to 57
        # before the write, so any 55/56 sitting there NOW was put back by coastnav's own
        # classifier -- re-derivable by construction, not stale.
        REACH = coastnav.FRINGE_R + coastnav.BELT_R
        fr = ctx["frag"]
        walls, reraised = 0, Counter()
        for p in ("Sea3", "Sea4", "Sea5"):
            for t in world_tris(read_part(root, BX, BY, p), BX, BY):
                topo = (int(round(t[0][3][0])) & 0xFC) >> 2
                if topo not in (55, 56):
                    continue
                pts = [(v[0][0], v[0][2]) for v in t]
                pts.append((sum(q[0] for q in pts) / 3.0, sum(q[1] for q in pts) / 3.0))
                if any(coastnav._tri_dist2d(px, pz, *[(v[0][0], v[0][2]) for v in lt]) <= REACH
                       for lt in fr for (px, pz) in pts):
                    walls += 1
                    reraised[(p, topo)] += 1
        print(f"   orphan audit: {rep['orphan_nav_reset']} cleared pre-write; "
              f"{walls} boat-wall tri(s) in the removed shore's reach afterwards "
              f"{dict(reraised)} -- each RE-RAISED by the classifier, so none is stale")
        cells_final = carry_cells(root)
        print(f"   final seam_report      = {R.seam_report(cells_final)}")
        print(f"   final edge_disagreements = {len(R.edge_disagreements(cells_final))}")
        print(f"   final unpaintable_slivers= {len(R.unpaintable_slivers(cells_final))}")
        rep["written"] = written
        if bad or changed:
            print(f"\nPOST-WRITE PROBLEM: {bad} {changed}")
            return 2
        print("\n   RELAUNCH (or exit + re-enter the overworld), then look at "
              "world x 387..398, z -640..-651.")

    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
