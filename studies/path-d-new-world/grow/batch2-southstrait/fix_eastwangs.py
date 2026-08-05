#!/usr/bin/env python
r"""fix_eastwangs.py -- the horseshoe carry's EAST crop column: close the unpaintable slivers.

THE DEFECT (owner, 2026-08-05): *"513,-689 and 513,-760 have missed wangs -- 2 single-edged
touching each other then a third with a mis-aligned edge."*  Both coordinates land on block
column ``i=15`` of Disc9 ``(7,10)``/``(7,11)`` -- world x 508..512, the east crop line.

THE MEASUREMENT.  Every water cell gets a token: ``sea3`` / ``sea4`` / the uv-decoded deep-set of
its Sea5 wang tile.  Stock disc-1 was censused for the adjacency table of those tokens (60,689
shared edges over 214 sea blocks) -- THE LEARNED WANG TABLE.  Two independent readings of it:

* **EDGE AGREEMENT.** Stock: 60,683 agreeing / 6 disagreeing = 0.010%, and ZERO of the six is a
  sea5|sea5 pair.  The carry ships 3 disagreements, ALL sea5|sea5, two of them at exactly the
  owner's z: ``(7,10)(15,11)|S`` at z=-688 and ``(7,11)(15,13)|S`` at z=-760.
* **BIGRAM SUPPORT.** ``ESW|ESW`` (vertical) = 0 in stock; ``ENW|ESW`` = 0; ``sea4|ESW`` = 0;
  ``ENW|sea4`` = 0 -- against ``sea4|ENW`` = 77 and ``ESW|sea4`` = 99.  The owner's two clauses map
  one-to-one onto the two zero-support pairs the column ships: ENW|ESW ("2 single-edged touching
  each other") then ESW|ESW ("a third with a mis-aligned edge").

THE CAUSE.  The east crop severed the donor's shallow field lengthwise (stock (8,15) i=0..2 is
sea3 right up to the cut), leaving 1-CELL-WIDE shallow slivers enclosed by deep.  Stock ships
**zero** deep-enclosed shallow components and **zero** 1-wide shallow runs longer than one cell
(93 EW + 92 NS runs map-wide, every one of length 1).  A 1-wide sliver has NO lawful painting: its
middle cell is an EW pinch, and ``rimretile._PINCH_PREFS`` folded it onto ESW -- which is where the
mis-aligned edge came from.  Stock's own 5 pinches resolve MUTUALLY (the neighbour on the added
side paints that edge deep too, 4/4 readable), and that is impossible here because both neighbours
are already 3-deep.  Re-tiling cannot fix a shape the alphabet cannot express.

THE FIX -- **the deep closes over the sliver.**  Six cells move Sea5 -> Sea4.  No uv is authored:
the moved triangles take a corner-uv map HARVESTED byte-exact from the same block's own Sea4
mains tiles (verbatim donor bytes), picked by the byte-derived anti-tiling rule (quadrant parity
and rotation different from the placed neighbours).  Positions, normals and tangents -- and so the
IDALL topograph and every coastnav navigation class -- are carried through untouched.

REJECTED, with the measurement that killed it: the pure-uv "mutual over" (repaint (7,11)(15,12)
E->ES and (15,13) ESW->ENW, zero shade change, the exact stock idiom at (4,15)@(12,4)-(12,5)).  It
turns ESW|ESW into ENW|ESW -- another zero-support pair.  Candidate scores, east column:
baseline 7 -> mutual-over 6 -> THIS 3 -> close-S3-too 10 cells for 2.  The 3 that remain are
horizontal ``W|E``/``NSW|E`` pairs whose shared edge AGREES (no hard step) and whose left tile is
untouched verbatim donor geometry.

FILES: only ``Block[7][10] Sea4/Sea5`` and ``Block[7][11] Sea4/Sea5`` in
``FF9CustomMap-world/FF9_Data/WorldMap/Disc9/0_1``.  No Terrain, no Donor.txt, no other block --
so the 31 armed event tris in ``Block[6][11] Terrain`` are safe by construction AND by gate (their
manifest md5 is re-checked).

USAGE
    py fix_eastwangs.py                 # dry run (default): reads only, prints every gate
    py fix_eastwangs.py --compare       # dry run + the candidate scoreboard
    py fix_eastwangs.py --write         # back up to the MAIN repo backups/, then write

RELAUNCH (or exit + re-enter the overworld) after --write, then look at x=513, z=-689 / -760.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path

KIT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\path-d-rung-6-handoff-e2535a\ff9mapkit")
BACKUP_ROOT = Path(r"C:\gd\Dream-World-IX\backups")
ARMED_MANIFEST = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\path-d-rung-6-handoff-e2535a"
                      r"\studies\path-d-new-world\rung6\worldside\armed_manifest.json")
MOD_FOLDER = "FF9CustomMap-world"
TARGET_DISC, READ_DISC, LOD = 9, 1, "0_1"
CARRY = [(bx, by) for by in (10, 11) for bx in (5, 6, 7)]     # the whole carry: census context
SEA = ("sea3", "sea4", "sea5")
G = 16

#: THE PLAN -- cells that move Sea5 -> Sea4.  S1/S2 are the two enclosed slivers at the owner's
#: first coordinate; S3's tail is the second.  Nothing else is touched.
DEEPEN = {
    (7, 10): [(15, 6), (15, 7),                       # sliver S1  (z -664..-672)
              (15, 10), (15, 11), (15, 12)],          # sliver S2  (z -680..-692)  <- (513,-689)
    (7, 11): [(15, 14)],                              # sliver S3's tail (z -760..-764) <- (513,-760)
}

sys.path.insert(0, str(KIT))


# ---------------------------------------------------------------- deployed / stock readers
def _root(game):
    from ff9mapkit import config
    return (config.find_game_path(game) / MOD_FOLDER / "FF9_Data" / "WorldMap"
            / f"Disc{TARGET_DISC}" / LOD)


def _path(root, bx, by, part):
    return root / f"r{by}" / f"Block[{bx}][{by}] {part.capitalize()}.ff9mesh"


def load_deployed(game):
    from ff9mapkit.world import mesh as M
    root = _root(game)
    out = {}
    for (bx, by) in CARRY:
        d = {}
        for part in SEA:
            p = _path(root, bx, by, part)
            if p.exists():
                d[part] = M.blockmesh_from_ff9mesh(str(p), disc=TARGET_DISC, x=bx, y=by,
                                                   lod=LOD, part=part)
        out[(bx, by)] = d
    return out


def load_stock(game):
    from ff9mapkit.world import extract as X
    out = {}
    for (bx, by) in X.list_blocks(disc=READ_DISC, game=game):
        d = {}
        for part in SEA:
            try:
                d[part] = X.read_block(bx, by, disc=READ_DISC, part=part, game=game)
            except ValueError as e:
                if "mesh not found" not in str(e):
                    raise
        if d:
            out[(bx, by)] = d
    return out


# ---------------------------------------------------------------- the wang tokenizer + tables
from ff9mapkit.world import rimretile as R                       # noqa: E402
from ff9mapkit.world import water as W                           # noqa: E402
from ff9mapkit.world.transplant import _sea_shade_grid, _sea_water_grid   # noqa: E402

DIRV, OPP = R.DIRV, {"N": "S", "S": "N", "E": "W", "W": "E"}


def step(bx, by, i, j, d):
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
    return nbx, nby, ni, nj


def tokenizer(cells, *, offisland):
    """``tok(bx,by,i,j)`` -> 'sea3' | 'sea4' | a deep-set string | 'cut' | 'L' | offisland."""
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


def bigram_tables(stock):
    """Stock's vertical (N->S) and horizontal (W->E) adjacency counts -- THE LEARNED WANG TABLE."""
    tok = tokenizer(stock, offisland=None)
    vert, horiz = Counter(), Counter()
    for (bx, by) in stock:
        for i in range(G):
            for j in range(G):
                a = tok(bx, by, i, j)
                if a is None:
                    continue
                s, e = tok(*step(bx, by, i, j, "S")), tok(*step(bx, by, i, j, "E"))
                if s is not None:
                    vert[(a, s)] += 1
                if e is not None:
                    horiz[(a, e)] += 1
    return vert, horiz


def declared(tok_v):
    """Which sides a token's texture paints DEEP (the only question the renderer asks)."""
    if tok_v in ("sea4", "ring"):
        return set("NESW")
    if tok_v in ("sea3",):
        return set()
    if tok_v in ("cut", "L", None):
        return None
    return set(tok_v)


def edge_census(cells, *, offisland="sea4"):
    """Shared edges where the two tiles disagree about deep-vs-shallow -- a HARD texture step."""
    tok = tokenizer(cells, offisland=offisland)
    bad = []
    n = 0
    for (bx, by) in sorted(cells):
        for i in range(G):
            for j in range(G):
                a = declared(tok(bx, by, i, j))
                if a is None:
                    continue
                for d in ("E", "S"):
                    nb = step(bx, by, i, j, d)
                    b = declared(tok(*nb))
                    if b is None:
                        continue
                    n += 1
                    if (d in a) != (OPP[d] in b):
                        bad.append(((bx, by, i, j), d, tok(bx, by, i, j), tok(*nb)))
    return n, bad


def zero_support(cells, vert, horiz, *, offisland="sea4", only=None):
    tok = tokenizer(cells, offisland=offisland)
    bad = []
    for (bx, by) in sorted(cells):
        for i in range(G):
            for j in range(G):
                a = tok(bx, by, i, j)
                if a == "L":
                    continue
                for d, tbl in (("S", vert), ("E", horiz)):
                    nb = step(bx, by, i, j, d)
                    b = tok(*nb)
                    if b == "L" or "cut" in (a, b) or (a == "sea4" and b == "sea4"):
                        continue
                    if tbl.get((a, b), 0) == 0:
                        if only and not only(bx, by, i, j):
                            continue
                        bad.append(((bx, by, i, j), d, a, b))
    return bad


EAST_COLUMN = lambda bx, by, i, j: bx == 7 and i >= 14          # noqa: E731


# ---------------------------------------------------------------- the edit
def mains_maps(parts):
    """``{(i,j): (corner-uv map, fit)}`` for every FULL Sea4 quad in the block -- the verbatim
    deep-water vocabulary this block already carries."""
    bm = parts.get("sea4")
    if bm is None:
        return {}
    corners = defaultdict(dict)
    for tri in bm.tris:
        i, j = R.cell_of([sum(bm.verts[k][0] for k in tri) / 3, 0,
                          sum(bm.verts[k][2] for k in tri) / 3])
        for k in tri:
            corners[(i, j)][R.corner_of(bm.verts[k], i, j)] = tuple(bm.uvs[k])
    out = {}
    for c, d in corners.items():
        if all(k in d for k in ((0, 0), (1, 0), (1, 1), (0, 1))):
            fit = W._fit_tile(d)
            if fit is not None:
                out[c] = (d, fit)
    return out


def _quad_parity(fit):
    ub = 0 if abs(fit[0]) < 1e-6 else 1
    vb = 0 if abs(fit[2]) < 1e-6 else 1
    return ub ^ vb, fit[4]


def pick_mains(maps, i, j):
    """THE ANTI-TILING PICK (water.assign_quadrants/assign_rotations, byte-derived from real
    block (8,4)): prefer a quadrant parity and a rotation that DIFFER from the already-placed
    4-neighbours, then the nearest source cell.  Deterministic; the map itself is verbatim."""
    nb = [_quad_parity(maps[c][1]) for c in ((i, j + 1), (i - 1, j), (i, j - 1), (i + 1, j))
          if c in maps]
    best = None
    for c, (d, fit) in sorted(maps.items()):
        p = _quad_parity(fit)
        score = (sum(1 for q in nb if q[0] == p[0]), sum(1 for q in nb if q[1] == p[1]),
                 abs(c[0] - i) + abs(c[1] - j))
        if best is None or score < best[0]:
            best = (score, c, d)
    return best[1], best[2]


def apply_plan(cells, deepen):
    """Move each planned cell's triangles Sea3/Sea5 -> Sea4 with a verbatim mains uv map."""
    post, notes = {}, []
    for blk, cellist in deepen.items():
        parts = cells[blk]
        shade = _sea_shade_grid(parts)
        maps = mains_maps(parts)
        buckets = {p: R.part_tris(parts.get(p)) for p in SEA}
        for (i, j) in cellist:
            src = shade[i][j]
            if src == "sea4":
                raise SystemExit(f"plan error: {blk} cell {(i, j)} is already Sea4")
            moved = [e for e in buckets[src] if e[0] == (i, j)]
            if not moved:
                raise SystemExit(f"plan error: {blk} cell {(i, j)} has no {src} triangles")
            buckets[src] = [e for e in buckets[src] if e[0] != (i, j)]
            srcc, uvmap = pick_mains(maps, i, j)
            for [c, verts, topo] in moved:
                nv = [(p, nr, R._tile_uv(uvmap, p, i, j), t) for (p, nr, _u, t) in verts]
                # VERBATIM PROOF: a full quad's verts sit exactly on the lattice, so the
                # bilinear evaluates to the harvested corner value bit-for-bit.
                for (p, _n, u, _t) in nv:
                    exact = uvmap[R.corner_of(p, i, j)]
                    if abs(u[0] - exact[0]) > 1e-9 or abs(u[1] - exact[1]) > 1e-9:
                        raise SystemExit(f"uv is not verbatim at {blk} {(i, j)}: {u} != {exact}")
                buckets["sea4"].append([c, nv, topo])
            notes.append(f"{blk} cell {(i, j)}: {src} -> sea4, uv carried from this block's "
                         f"own Sea4 cell {srcc} ({len(moved)} tris)")
        post[blk] = {p: R.build_part([e[1] for e in buckets[p]], p.capitalize(),
                                     blk[0], blk[1], TARGET_DISC, LOD)
                     for p in SEA if parts.get(p) is not None}
    return post, notes


def geometry_fingerprint(parts):
    """(position, normal, tangent) multiset -- STRICTER than rimretile.repartition_ok, which
    only pins (position, topograph): this also pins the coastnav class + every IDALL bit."""
    return Counter((tuple(round(x, 4) for x in v[0]), tuple(round(x, 4) for x in v[1]),
                    tuple(round(x, 4) for x in v[3]))
                   for p in SEA if parts.get(p) is not None
                   for [_c, vs, _t] in R.part_tris(parts[p]) for v in vs)


# ---------------------------------------------------------------- report helpers
def column_run(cells, bx, by, i, lo, hi, vert):
    tok = tokenizer(cells, offisland="sea4")
    seq = [tok(bx, by, i, j) for j in range(lo, hi + 1)]
    rows = []
    for k in range(len(seq) - 1):
        rows.append((lo + k, seq[k], seq[k + 1], vert.get((seq[k], seq[k + 1]), 0),
                     -by * 64 - (lo + k + 1) * 4))
    return seq, rows


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="actually write (default: dry run)")
    ap.add_argument("--dry-run", action="store_true", help="explicit no-op default")
    ap.add_argument("--compare", action="store_true", help="also score the rejected candidates")
    ap.add_argument("--game", default=None)
    args = ap.parse_args(argv)
    apply_write = bool(args.write) and not args.dry_run

    from ff9mapkit.world import mesh as M

    root = _root(args.game)
    print(f"fix_eastwangs  target={root}")
    print(f"               mode={'WRITE' if apply_write else 'DRY RUN'}")

    print("\n[1] reading the deployed carry + censusing stock disc-1 (the oracle) ...")
    cells = load_deployed(args.game)
    stock = load_stock(args.game)
    vert, horiz = bigram_tables(stock)
    sn, sbad = edge_census(stock, offisland=None)
    print(f"    stock: {len(stock)} sea blocks, {sn} shared edges, {len(sbad)} disagreeing "
          f"({100.0 * len(sbad) / sn:.3f}%), {len(vert)}+{len(horiz)} bigram kinds")
    s5 = [e for e in sbad if e[2] not in ("sea3", "sea4") and e[3] not in ("sea3", "sea4")]
    print(f"    stock sea5|sea5 disagreements: {len(s5)}   <- the class the owner reported")
    for k in (("ESW", "ESW"), ("ENW", "ESW"), ("sea4", "ENW"), ("ESW", "sea4"),
              ("sea4", "ESW"), ("ENW", "sea4"), ("ENW", "E"), ("E", "ESW")):
        print(f"      stock vertical {k[0]:>5} | {k[1]:<5} = {vert.get(k, 0)}")

    n0, bad0 = edge_census(cells)
    z0 = zero_support(cells, vert, horiz)
    z0e = zero_support(cells, vert, horiz, only=EAST_COLUMN)
    print(f"\n[2] deployed carry BEFORE: {n0} edges, {len(bad0)} disagreeing, "
          f"{len(z0)} zero-support pairs ({len(z0e)} on the east column)")
    for e in bad0:
        (bx, by, i, j), d, a, b = e
        print(f"    DISAGREE ({bx},{by}) cell {(i, j)} -{d}-> {a} | {b}   "
              f"world x={bx * 64 + i * 4} z={-by * 64 - j * 4}")
    before_seam = R.seam_report(cells)
    print(f"    rimretile.seam_report BEFORE: {before_seam}")
    seq, rows = column_run(cells, 7, 10, 15, 5, 13, vert)
    print(f"    (7,10) i=15 j=5..13 run: {seq}")
    for (j, a, b, n, z) in rows:
        print(f"       j{j}->j{j + 1} (z={z}) {a:>5} | {b:<5} stock={n}"
              + ("   <-- ZERO SUPPORT" if n == 0 else ""))
    seq, rows = column_run(cells, 7, 11, 15, 10, 15, vert)
    print(f"    (7,11) i=15 j=10..15 run: {seq}")
    for (j, a, b, n, z) in rows:
        print(f"       j{j}->j{j + 1} (z={z}) {a:>5} | {b:<5} stock={n}"
              + ("   <-- ZERO SUPPORT" if n == 0 else ""))

    print("\n[3] applying the plan (in memory) ...")
    post, notes = apply_plan(cells, DEEPEN)
    for s in notes:
        print("    " + s)
    after = {c: dict(cells[c], **post.get(c, {})) for c in cells}

    print("\n[4] GATES")
    ok = True
    g = geometry_fingerprint
    same_geo = all(g(cells[c]) == g(after[c]) for c in after)
    print(f"    G1 (pos,normal,tangent) multiset invariant (topograph + coastnav class carried): "
          f"{'PASS' if same_geo else 'FAIL'}")
    ok &= same_geo
    rok = R.repartition_ok(cells, after)
    print(f"    G2 rimretile.repartition_ok (the module's own pure-reshade gate): "
          f"{'PASS' if rok else 'FAIL'}")
    ok &= rok
    bad_v = []
    for blk, parts in post.items():
        for part, bm in parts.items():
            try:
                M.validate_blockmesh(bm)
            except Exception as e:                                   # noqa: BLE001
                bad_v.append((blk, part, str(e)))
    print(f"    G3 validate_blockmesh (engine loader predicates): "
          f"{'PASS' if not bad_v else 'FAIL ' + str(bad_v)}")
    ok &= not bad_v
    n1, bad1 = edge_census(after)
    print(f"    G4 hard edge disagreements: {len(bad0)} -> {len(bad1)}")
    for e in bad1:
        (bx, by, i, j), d, a, b = e
        print(f"         remaining: ({bx},{by}) {(i, j)} -{d}-> {a}|{b}  "
              f"x={bx * 64 + i * 4} z={-by * 64 - j * 4}  [north frame, shore context -- "
              f"out of scope, see the report]")
    east_ok = not [e for e in bad1 if EAST_COLUMN(*e[0])]
    print(f"       east column clear of disagreements: {'PASS' if east_ok else 'FAIL'}")
    ok &= east_ok
    z1 = zero_support(after, vert, horiz)
    z1e = zero_support(after, vert, horiz, only=EAST_COLUMN)
    print(f"    G5 zero-support bigrams: global {len(z0)} -> {len(z1)}; "
          f"east column {len(z0e)} -> {len(z1e)}")
    for e in z1e:
        print(f"         remaining (edge AGREES, no hard step): {e}")
    ok &= all(e[1] == "E" for e in z1e)                # only horizontal, agreeing pairs may remain
    after_seam = R.seam_report(after)
    print(f"    G6 rimretile.seam_report: {before_seam} -> {after_seam}")
    ok &= after_seam["under"] == 0
    print(f"       hard seams (under) still 0: {'PASS' if after_seam['under'] == 0 else 'FAIL'}")
    print("    G7 the corrected runs, every pair cited against stock:")
    for (bx, by, lo, hi) in ((7, 10, 5, 13), (7, 11, 10, 15)):
        seq, rows = column_run(after, bx, by, 15, lo, hi, vert)
        print(f"       ({bx},{by}) i=15 j={lo}..{hi}: {seq}")
        for (j, a, b, n, z) in rows:
            print(f"          j{j}->j{j + 1} (z={z}) {a:>5} | {b:<5} stock={n}"
                  + ("   <-- ZERO" if n == 0 else ""))
    touched = {(7, 10), (7, 11)}
    untouched_ok = all(geometry_fingerprint(cells[c]) == geometry_fingerprint(after[c])
                       and all(R.part_tris(cells[c].get(p)) == R.part_tris(after[c].get(p))
                               for p in SEA)
                       for c in cells if c not in touched)
    print(f"    G8 the other four carry blocks byte-untouched: "
          f"{'PASS' if untouched_ok else 'FAIL'}")
    ok &= untouched_ok

    if args.compare:
        print("\n[5] candidate scoreboard (east-column zero-support pairs; lower is better)")
        cands = {
            "baseline (deployed)": {},
            "C2 mutual-over, uv only (REJECTED)": None,
            "C3 owner's two spots only": {(7, 10): [(15, 10), (15, 11), (15, 12)],
                                          (7, 11): [(15, 14)]},
            "C0 THIS PLAN": DEEPEN,
            "C1 close S3 as well": {(7, 10): DEEPEN[(7, 10)],
                                    (7, 11): [(15, 11), (15, 12), (15, 13), (15, 14), (14, 12)]},
        }
        for name, plan in cands.items():
            if plan is None:
                mp, _ = apply_repaint(cells)
                merged = {c: dict(cells[c], **mp.get(c, {})) for c in cells}
            elif plan == {}:
                merged = cells
            else:
                mp, _ = apply_plan(cells, plan)
                merged = {c: dict(cells[c], **mp.get(c, {})) for c in cells}
            e = zero_support(merged, vert, horiz, only=EAST_COLUMN)
            _n, b = edge_census(merged)
            cellsn = 0 if not plan else sum(len(v) for v in plan.values())
            print(f"    {name:<38} east-zero={len(e)}  disagreements={len(b)}  cells={cellsn}")

    if not ok:
        print("\nGATES FAILED -- nothing written.")
        return 2
    if not apply_write:
        print("\ndry run -- nothing written.  Re-run with --write to apply.")
        return 0

    print("\n[6] WRITING")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_ROOT / f"eastwangs-disc9-7x10-7x11-{stamp}"
    written = []
    for blk in sorted(post):
        for part in SEA:
            bm = post[blk].get(part)
            if bm is None:
                continue
            p = _path(root, blk[0], blk[1], part)
            new = M.ff9mesh_bytes(bm)
            if p.exists() and p.read_bytes() == new:
                continue                                     # unchanged part -- do not rewrite
            out = dest / f"r{blk[1]}"
            out.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, out / p.name)
            M.write_ff9mesh(bm, p)
            M.record_ledger_write(p, cell=blk, part=part.capitalize(), write_disc=TARGET_DISC)
            written.append(p)
    print(f"    backed up {len(written)} file(s) -> {dest}")
    for p in written:
        print(f"    wrote {p}")

    print("\n[7] POST-WRITE re-read from disk + all gates again")
    re_cells = load_deployed(args.game)
    n2, bad2 = edge_census(re_cells)
    z2e = zero_support(re_cells, vert, horiz, only=EAST_COLUMN)
    print(f"    disagreements {len(bad2)} (east column "
          f"{len([e for e in bad2 if EAST_COLUMN(*e[0])])}), east zero-support {len(z2e)}")
    print(f"    seam_report {R.seam_report(re_cells)}")
    bad_v2 = []
    for blk in sorted(post):
        for part in SEA:
            p = _path(root, blk[0], blk[1], part)
            if not p.exists():
                continue
            try:
                M.validate_blockmesh(M.blockmesh_from_ff9mesh(
                    str(p), disc=TARGET_DISC, x=blk[0], y=blk[1], lod=LOD, part=part))
            except Exception as e:                               # noqa: BLE001
                bad_v2.append((p.name, str(e)))
    print(f"    validate_blockmesh on re-read: {'PASS' if not bad_v2 else 'FAIL ' + str(bad_v2)}")
    nonsea = [p.name for p in written if "Sea" not in p.name]
    print(f"    non-Sea files written: {nonsea or 'NONE -- sea-only edit'}")
    man = json.loads(ARMED_MANIFEST.read_text())
    for key, rows in man.items():
        bx, by = (int(x) for x in key.split(","))
        t = root / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if t.exists():
            cur = md5(t)
            want = rows[-1]["armed_md5"]
            print(f"    armed Terrain ({bx},{by}) md5 {cur} "
                  f"{'== manifest (INTACT)' if cur == want else '!= manifest (CHECK)'}")
    print("\n    RELAUNCH (or exit + re-enter the overworld), then look at x=513 z=-689 / -760.")
    return 0 if (not bad_v2 and not [e for e in bad2 if EAST_COLUMN(*e[0])]) else 2


def apply_repaint(cells):
    """The REJECTED pure-uv mutual-over candidate, kept runnable for --compare."""
    var = R.harvest_variants([(7, 15)], disc=READ_DISC)
    plan = {(7, 11): {(15, 12): "ES", (15, 13): "ENW"}}
    post = {}
    for blk, cellplan in plan.items():
        parts = cells[blk]
        shade = _sea_shade_grid(parts)
        buckets = {p: R.part_tris(parts.get(p)) for p in SEA}
        for (i, j), ds in cellplan.items():
            uvmap = var[tuple(W.DEEPSET2TILE[frozenset(ds)][0])]
            src = shade[i][j]
            moved = [e for e in buckets[src] if e[0] == (i, j)]
            buckets[src] = [e for e in buckets[src] if e[0] != (i, j)]
            for [c, verts, topo] in moved:
                buckets["sea5"].append([c, [(p, nr, R._tile_uv(uvmap, p, i, j), t)
                                            for (p, nr, _u, t) in verts], topo])
        post[blk] = {p: R.build_part([e[1] for e in buckets[p]], p.capitalize(),
                                     blk[0], blk[1], TARGET_DISC, LOD)
                     for p in SEA if parts.get(p) is not None}
    return post, []


if __name__ == "__main__":
    raise SystemExit(main())
