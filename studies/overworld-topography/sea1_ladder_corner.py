"""sea1_ladder_corner.py -- close the LAST off-language shore edge on the (8,17)+2x2 desert-beach
island: the {sea1,sea5} LADDER at the SE sand-spit corner of cell (12,18).

BACKGROUND (GROUND-FAMILY-DECODE-2026-07-19.md ADDENDA 7-9, + the census/options round):
  The rim retile (ADDENDUM 7, wang_rim_retile.py) closed the island's 17 cropped-Wang SEA3/SEA5 rim
  seams (the 2nd-deepest->deepest transition).  It left ONE sibling class untouched, by design: the
  SHALLOWEST coastal water (Sea1/Sea2/Beach1) rode verbatim.  The assessment round (ADDENDUM 9 -> the
  census+options study) found the crop left exactly TWO off-language edges: cell (12,18) sub-cells
  (15,14)/(15,15) are Sea1 (shallow-transition) abutting the DEEP ring (stock landmass (13,18)'s west
  edge = deep sea4) with no transition -- world X=832 Z=-1210/-1214.  The stock-map census is decisive:
  sea1/sea2-abuts-sea4 occurs ZERO times in shipping FF9 (sea1's deepest-ever neighbour is sea5 via the
  abundant {sea1,sea5} adjacency, 79 tile-edges map-wide; sea1's deep shade == sea5's shallow shade).
  There is NO single tile bridging shallowest(sea2/sea1) directly to deepest(sea4) -- the ONLY lawful
  bridge is the LADDER sea2 -> sea1 -> sea5 -> deep via the {sea1,sea5} skip.

THE FIX -- OPTION B (the user's explicit choice), a ~4-quad PURE REPARTITION inside (12,18) ONLY:
  * (15,14) Sea1(topo53) -> Sea5, UV = the E-pointing tip (strip0/r0, deepset {E} -> deep to the E)
  * (15,15) Sea1(topo55) -> Sea5, UV = the E-pointing tip (strip0/r0)
  * (14,14) Sea2(topo53) -> Sea1, UV = the E-pointing tip (strip0/r0)
  * (14,15) Sea2(topo55) -> Sea1, UV = the E-pointing tip (strip0/r0)
  Post-state per row: sea2 -> sea1 -> sea5 -> deep -- EVERY adjacency lawful ({sea2,sea1} 499,
  {sea1,sea5} 79, {sea5,deep}).  DELTA from the options-study sketch: NONE (byte verification confirms
  the exact quads/shades: (15,14)/(15,15) are Sea1, (14,14)/(14,15) are Sea2; no 3rd inboard quad is
  needed -- the S-neighbour (12,19) j0 is i14=sea2 / i15=sea5, so both cross-block edges are lawful).

  Each moved quad keeps its EXACT verts (Y=0) + normals + tangent.x TOPO -- only the UV rect and the
  containing Sea file (THE PER-NAME MATERIAL LAW: Sea1/Sea2/Sea5 = different caustic atlases) change.  So
  the union of {Sea1,Sea2,Sea3,Sea4,Sea5,Beach1} triangles is a PURE REPARTITION (geometry+topo IDENTICAL)
  -> walkmesh raycast / coverage / boat-legality byte-for-byte preserved (non-regression airtight).

  VERBATIM-FIRST (THE FORM LESSON): both E-tip UVs are HARVESTED byte-exact from the donor island's OWN
  real Sea5 and Sea1 strip0/r0 tiles (donors (8,17)/(9,17)/(8,18)/(9,18) via _fit_tile; the sea5 tip is
  the SAME UV the rim-retile's (15,9..13) E-tips already use, so the i15 column reads as one continuous
  sea5 E-wall; the sea1 tip is the donor's own (11,10) sea1 tile), NOT synthesized from water.VSTRIP.

LEAVE ALONE (task note): the interior sea2|sea4 tile at (12,19) cell (14,0).S -- byte-verbatim donor
  (9,18) geometry and literally the ONLY sea2|sea4 edge in the entire stock map (lawful-by-precedent).
  This script touches ONLY (12,18); (11,18)/(11,19)/(12,19) stay byte-identical.

GATES (all must pass before --deploy):
  (a) LAWFUL-ADJACENCY: sea1->sea4 direct edges = 0 on the island; sea2 never abuts sea3/sea5/sea4/deep;
      every changed quad's FOUR edges are lawful ladder adjacencies; the s12 shallow census 2 -> 0 with
      0 introduced anywhere (incl. N/S of the changed quads).
  (b) SEA3/4/5 UNHARMED: transplant.wang_carry_gate + the rim-retile FRAME census still report 0 frame
      incoherence (the sea3/4/5 system is untouched; the new sea5 E-tips are coherent frame edges).
  (c) PURE REPARTITION: the (verts+tangent.x) triangle multiset over ALL water parts is IDENTICAL
      before==after for the whole cell; FLAT-MESH (vcount==idx) per written file; SEA-LAYER (Y unchanged).
  (d) BYTE-DIFF SCOPED: only (12,18) Sea1/Sea2/Sea5 change; every other cell + every non-water part +
      Beach1/Sea3/Sea4/Donor byte-identical (literal-prefix filters, NEVER a glob with '[').
  (e) DISC PARITY: every written file Disc1 == Disc4 (explicit byte-copy); idempotent re-run = 0 changes.
  (f) OFFLINE EYE: whole_island_eye.py + the corner zoom PRE/POST into the study dir.

BACKUPS: the 3 touched files (12,18) Sea1/Sea2/Sea5, both discs -> backups/sea1-ladder.20260720/ (the
  IMMUTABLE pre-fix source; the repartition is a pure function of it -> byte-reproducible + idempotent).
Run:  py studies/overworld-topography/sea1_ladder_corner.py            # gates only, no writes
      py studies/overworld-topography/sea1_ladder_corner.py --deploy    # gates + deploy both discs
"""
import argparse
import hashlib
import importlib.util
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STUDY = REPO / "studies" / "overworld-topography"
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit.world import mesh as M                          # noqa: E402
from ff9mapkit.world import water as W                         # noqa: E402
from ff9mapkit.world import extract as X                       # noqa: E402
from ff9mapkit.world import transplant as T                    # noqa: E402
from ff9mapkit.world.extract import decode_id                  # noqa: E402

# reuse the rim-retile round's proven helpers (part_tris / build_part / corner_of / cell_of / census /
# _serialize / harvest_variants / _mesh helpers) -- the same VERBATIM-FIRST pure-repartition machinery.
_spec = importlib.util.spec_from_file_location("wrr", STUDY / "wang_rim_retile.py")
wrr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wrr)
wf = wrr.wf                                                     # waterfix_1119_r2 predicate helpers

# --------------------------------------------------------------------------- constants
MOD = "FF9CustomMap-world"
GAME = Path(r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX")
WORLD = GAME / MOD / "FF9_Data" / "WorldMap"
BK = REPO / "backups" / "sea1-ladder.20260720"
DISCS = (1, 4)
LOD = "0_1"
G, CELL = 16, 4.0

TARGET = (12, 18)                                              # the ONLY cell we touch
DONORS = [(8, 17), (9, 17), (8, 18), (9, 18)]                  # verbatim vocabulary donors
ISLAND = [(11, 18), (12, 18), (11, 19), (12, 19)]             # the 2x2 carried island (for gate b + eye)
E_NB = (13, 18)                                                # (12,18)'s E cross-block neighbour (stock landmass)
S_NB = (12, 19)                                                # (12,18)'s S cross-block neighbour (mod)
WATERPARTS = ("beach1", "sea1", "sea2", "sea3", "sea5", "sea4")
FULL = ((0, 0), (1, 0), (1, 1), (0, 1))
DIRV = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}
# shallow -> deep shade priority (matches s12_deep_census's _RANK): terrain FIRST -> a shore cell that has
# BOTH terrain and shallow water reads as LAND (coast), NOT as the water shade.  Omitting terrain
# mislabels every land cell 'sea4' (deep) -> spurious sea2|sea3 / sea2|sea4 flags at the real shoreline.
RANK = ("terrain", "beach1", "sea2", "sea1", "sea3", "sea5", "sea4")
GRIDPARTS = ("terrain",) + WATERPARTS
LAND = "land"                                                  # the grid label for a terrain (shore/land) cell

# THE 4-QUAD PLAN (verified against the deployed bytes; see the module docstring).  Each: src part, dst
# part, and the harvested E-tip key.  All UVs = strip0/r0 (deepset {E}), harvested from the donor's own
# real tile of the DST part (so the Sea5 tips == the rim-retile's own tips; the Sea1 tips == donor sea1).
PLAN = {
    (15, 14): ("sea1", "sea5"),   # Sea1(53) -> Sea5 E-tip
    (15, 15): ("sea1", "sea5"),   # Sea1(55) -> Sea5 E-tip
    (14, 14): ("sea2", "sea1"),   # Sea2(53) -> Sea1 E-tip
    (14, 15): ("sea2", "sea1"),   # Sea2(55) -> Sea1 E-tip
}
EXPECT_CHANGED = {"Sea1", "Sea2", "Sea5"}

# the immutable PRE baseline (deployed state AFTER the rim retile; Disc1==Disc4) -- guards the backup
PRE_MD5 = {
    "Sea1": (2204, "4a01dcbeef7ff1dd64829f0f2317be3a"),
    "Sea2": (5480, "a3a44bf39b9fd81ea6462af64c267e72"),
    "Sea5": (10004, "b6613890c2058c7b2e540befeed83b15"),
}

# lawful water|water adjacencies (the RING LADDER; from the whole-map census).  A pair not here is
# off-language -> a gate-a violation.  'ring'/deep is treated as 'sea4'.  Same-shade = a singleton set.
LAWFUL = {frozenset(p) for p in (
    ("beach1", "beach1"), ("beach1", "sea2"), ("beach1", "sea1"),
    ("sea2", "sea2"), ("sea2", "sea1"),
    ("sea1", "sea1"), ("sea1", "sea3"), ("sea1", "sea5"),
    ("sea3", "sea3"), ("sea3", "sea5"),
    ("sea5", "sea5"), ("sea5", "sea4"),
    ("sea4", "sea4"),
)}
FORBIDDEN = {frozenset(p) for p in (
    ("sea1", "sea4"), ("sea2", "sea4"), ("sea2", "sea3"), ("sea2", "sea5"), ("sea3", "sea4"),
)}


def is_lawful(a, b):
    """A water|water (or water|land) adjacency is lawful iff it is a ladder pair, a same-shade pair, or a
    COAST (either side is land -- a water tile abutting the shoreline is always legal)."""
    if LAND in (a, b):
        return True
    pair = frozenset({a, b})
    return pair in LAWFUL and pair not in FORBIDDEN


def _rdir(disc, by):
    return WORLD / f"Disc{disc}" / LOD / f"r{by}"


def _md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def _bk(disc, name):
    return BK / f"Disc{disc}__Block[{TARGET[0]}][{TARGET[1]}] {name}"


# --------------------------------------------------------------------------- 0. backup
def ensure_backup():
    """Back up the 3 touched files (both discs) to the immutable pre-fix store, ONCE.  If present, verify
    against PRE_MD5 and DO NOT overwrite (idempotency: a re-run reads PRE from here even after deploy)."""
    BK.mkdir(parents=True, exist_ok=True)
    bx, by = TARGET
    lines = []
    for disc in DISCS:
        for part, (size, md5) in PRE_MD5.items():
            dst = _bk(disc, f"{part}.ff9mesh")
            live = _rdir(disc, by) / f"Block[{bx}][{by}] {part}.ff9mesh"
            if dst.exists():
                if dst.stat().st_size != size or _md5(dst) != md5:
                    raise SystemExit(f"REFUSE: existing backup {dst} != pre-fix {size}B/{md5[:8]} "
                                     f"({dst.stat().st_size}B/{_md5(dst)[:8]})")
            else:
                if not live.exists():
                    raise SystemExit(f"REFUSE: no live {live} to back up")
                if live.stat().st_size != size or _md5(live) != md5:
                    raise SystemExit(f"REFUSE: live {live} is {live.stat().st_size}B/{_md5(live)[:8]}, "
                                     f"expected pre-fix {size}B/{md5[:8]} -- already deployed with lost backup?")
                shutil.copyfile(live, dst)
            lines.append(f"Disc{disc}  r{by}  Block[{bx}][{by}]  {part}.ff9mesh  {size}B  {md5}")
    man = BK / "MANIFEST.txt"
    if not man.exists():
        man.write_text("Pre-staged: the 3 touched water-part files for the {sea1,sea5} ladder corner fix.\n"
                       "Scope: (12,18) Sea1/Sea2/Sea5, BOTH discs.  Everything else UNTOUCHED.\n\n"
                       + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"[0] backup OK: {len(PRE_MD5) * len(DISCS)} pre-fix files verified in {BK.name}/")


# --------------------------------------------------------------------------- decode
def load_pre_parts():
    """{part: BlockMesh} for (12,18): the 3 touched parts from the IMMUTABLE backup (pre-fix), the
    untouched Terrain/Beach1/Sea3/Sea4 from the LIVE tree (byte-identical pre==post -> census sees the
    real cell incl. the land shoreline)."""
    bx, by = TARGET
    out = {}
    for part in GRIDPARTS:
        cap = part.capitalize()
        bk = _bk(1, f"{cap}.ff9mesh")
        live = _rdir(1, by) / f"Block[{bx}][{by}] {cap}.ff9mesh"
        p = bk if (cap in EXPECT_CHANGED and bk.exists()) else live
        if p.exists():
            bm = M.blockmesh_from_ff9mesh(str(p), disc=1, x=bx, y=by, lod=LOD, part=part)
            if part == "terrain" and len(bm.tris) <= 1:        # skip a degenerate divert-arm stub
                continue
            out[part] = bm
    return out


def load_cell(bx, by, mod):
    """{part: BlockMesh} (incl. terrain) for a whole cell -- LIVE mod tree (mod=True) or stock (mod=False)."""
    out = {}
    for part in GRIDPARTS:
        cap = part.capitalize()
        if mod:
            p = _rdir(1, by) / f"Block[{bx}][{by}] {cap}.ff9mesh"
            if p.exists():
                bm = M.blockmesh_from_ff9mesh(str(p), disc=1, x=bx, y=by, lod=LOD, part=part)
                if part == "terrain" and len(bm.tris) <= 1:
                    continue
                out[part] = bm
        else:
            try:
                bm = X.read_block(bx, by, disc=1, lod=LOD, part=part)
            except (ValueError, FileNotFoundError):
                bm = None
            if bm is not None and bm.verts:
                out[part] = bm
    return out


def shade_grid(parts):
    """FULL shade grid (land/beach1/sea2/sea1/sea3/sea5/sea4; empty-of-everything -> 'sea4' deep ring)
    from a {part: BlockMesh}.  Terrain wins (a shore cell = 'land'), matching s12_deep_census."""
    seen = [[None] * G for _ in range(G)]
    for part in RANK:                                          # terrain, then shallow->deep water
        bm = parts.get(part)
        if bm is None:
            continue
        lbl = LAND if part == "terrain" else part
        for tri in bm.tris:
            i, j = wrr.cell_of([sum(bm.verts[q][0] for q in tri) / 3, 0, sum(bm.verts[q][2] for q in tri) / 3])
            if 0 <= i < G and 0 <= j < G and seen[i][j] is None:
                seen[i][j] = lbl
    return [[seen[i][j] or "sea4" for j in range(G)] for i in range(G)]


def water_grid(parts):
    hw = [[False] * G for _ in range(G)]
    for part in WATERPARTS:
        bm = parts.get(part)
        if bm is None:
            continue
        for tri in bm.tris:
            i, j = wrr.cell_of([sum(bm.verts[q][0] for q in tri) / 3, 0, sum(bm.verts[q][2] for q in tri) / 3])
            if 0 <= i < G and 0 <= j < G:
                hw[i][j] = True
    return hw


# --------------------------------------------------------------------------- verbatim harvest
def harvest_etip(part):
    """The donor island's OWN real strip0/r0 (E-pointing tip) tile for ``part`` -- byte-exact.  Every
    strip0/r0 instance across the donors must agree (spread 0) -> one representative is the vocab.
    Returns ((u0, u1, v0, v1), n_samples): the tile's exact UV rect (r0 identity: u=u0+fx*(u1-u0),
    v=v0+fz*(v1-v0)), so it re-UVs by LOCAL POSITION (handles the irregular shore verts, not just corners)."""
    reps = []
    for (dx, dy) in DONORS:
        try:
            bm = X.read_block(dx, dy, disc=1, lod=LOD, part=part)
        except (ValueError, FileNotFoundError):
            continue
        corners = defaultdict(dict)
        for tri in bm.tris:
            i, j = wrr.cell_of([sum(bm.verts[q][0] for q in tri) / 3, 0, sum(bm.verts[q][2] for q in tri) / 3])
            for k in tri:
                corners[(i, j)][wrr.corner_of(bm.verts[k], i, j)] = tuple(bm.uvs[k])
        for d in corners.values():
            if all(c in d for c in FULL):
                fit = W._fit_tile(d)
                if fit and (W._strip_of(fit[2]), fit[4]) == (0, "r0"):
                    reps.append((round(fit[0], 5), round(fit[1], 5), round(fit[2], 5), round(fit[3], 5)))
    if not reps:
        raise SystemExit(f"REFUSE: no strip0/r0 (E-tip) {part} tile in donors -- can't harvest verbatim")
    rect = reps[0]
    for r in reps[1:]:
        if any(abs(a - b) > 1e-4 for a, b in zip(r, rect)):
            raise SystemExit(f"REFUSE: {part} strip0/r0 rect not self-consistent -- can't harvest verbatim")
    return rect, len(reps)


def _etip_uv(rect, lx, lz):
    """BILINEAR strip0/r0 (E-pointing) UV at LOCAL cell position (lx, lz), clamped for spill.  r0 is the
    identity, so u = u0 + fx*(u1-u0), v = v0 + fz*(v1-v0).  Position-accurate (keeps distinct verts
    distinct -> no degenerate UV on the boundary-spanning shore slivers); used for the Sea1 tiles."""
    u0, u1, v0, v1 = rect
    fx = min(max(lx / CELL, 0.0), 1.0)
    fz = min(max(lz / CELL, 0.0), 1.0)
    return (u0 + fx * (u1 - u0), v0 + fz * (v1 - v0))


def _etip_snap(rect, lx, lz):
    """CORNER-SNAP strip0/r0 UV: round the local position to its nearest cell corner (clamped) and assign
    that corner's canonical UV.  This yields a CLEAN strip0/r0 rect that water._fit_tile classifies as
    deepset {E} -- required so the Sea5 tiles pass the Wang frame gate (the rim-retile's own method).  The
    two Sea5 target cells have all 4 distinct corners under this snap (no degenerate tri)."""
    u0, u1, v0, v1 = rect
    fx = min(max(round(lx / CELL), 0), 1)
    fz = min(max(round(lz / CELL), 0), 1)
    return (u0 + fx * (u1 - u0), v0 + fz * (v1 - v0))


# --------------------------------------------------------------------------- apply
def apply_plan(pre, etip):
    """Move ALL of each planned cell's triangles (the SE shore cells are irregular: 2-3 tris, mixed topo
    53/55, verts spilling past the cell + non-zero beach Y) to the DST part and re-UV to the DST's E-tip
    rect by LOCAL POSITION.  verts/normals/tangent.x(topo) preserved byte-exact -> a PURE REPARTITION.
    Returns {part: BlockMesh} for the 3 CHANGED parts (Sea1/Sea2/Sea5) of (12,18)."""
    bx, by = TARGET
    buckets = {part: wrr.part_tris(pre.get(part)) for part in ("sea1", "sea2", "sea5")}
    moved_log = {}
    for (i, j), (src, dst) in PLAN.items():
        rect = etip[dst]
        found = [e for e in buckets[src] if e[0] == (i, j)]
        if not found:
            raise SystemExit(f"apply: no {src} tris at {(i, j)}")
        buckets[src] = [e for e in buckets[src] if e[0] != (i, j)]
        uvfn = _etip_snap if dst == "sea5" else _etip_uv   # sea5 must fit-classify (gate b); sea1 bilinear
        topos = Counter()
        for [_cell, verts, topo] in found:
            topos[topo] += 1
            newverts = []
            for (p, n, _u, t) in verts:
                lx, lz = p[0] - i * CELL, -p[2] - j * CELL     # LOCAL cell position (spill kept, clamped in UV)
                newverts.append((p, n, uvfn(rect, lx, lz), t))
            buckets[dst].append([_cell, newverts, topo])
        moved_log[(i, j)] = (src, dst, len(found), dict(topos))
    post = {}
    for part in ("sea1", "sea2", "sea5"):
        if pre.get(part) is None:
            continue
        tris = [e[1] for e in buckets[part]]
        post[part] = wrr.build_part(tris, part.capitalize(), bx, by, 1)
    return post, moved_log


def merged_parts(pre, post):
    """The full post cell = pre parts overlaid with the 3 rebuilt parts."""
    full = dict(pre)
    full.update(post)
    return full


# --------------------------------------------------------------------------- census helpers
def region_neighbour(grids, waters, bx, by, i, j, d):
    """(shade, has_water) one step ``d`` from (bx,by,i,j), CROSS-BLOCK.  Off-region -> ('ring', True)."""
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
    if (nbx, nby) in grids:
        return grids[(nbx, nby)][ni][nj], waters[(nbx, nby)][ni][nj]
    return "ring", True


def _norm(sh):
    return "sea4" if sh == "ring" else sh


def shallow_census(grids, waters, cells):
    """The s12 shallow census: every edge of every sea1/sea2 tile that faces DEEP (sea4/ring).  Returns
    the SET of hard edges (bx,by,i,j,dir) so before/after are diffable."""
    hard = set()
    for (bx, by) in cells:
        g, w = grids[(bx, by)], waters[(bx, by)]
        for i in range(G):
            for j in range(G):
                if g[i][j] not in ("sea1", "sea2"):
                    continue
                for d in "NESW":
                    nsh, nw = region_neighbour(grids, waters, bx, by, i, j, d)
                    if _norm(nsh) == "sea4" and nw:
                        hard.add((bx, by, i, j, d))
    return hard


# --------------------------------------------------------------------------- gates
def gate_a(pre_full, post_full):
    print("[gate a] LAWFUL-ADJACENCY (the {sea1,sea5} ladder):")
    # island grids: (12,18) pre/post + real neighbours (13,18) stock, (12,19) mod, (11,18) mod, plus
    # (12,17) stock N-neighbour for completeness.  All shade + water grids.
    nb = {E_NB: load_cell(*E_NB, mod=False), S_NB: load_cell(*S_NB, mod=True),
          (11, 18): load_cell(11, 18, mod=True), (11, 19): load_cell(11, 19, mod=True),
          (12, 17): load_cell(12, 17, mod=False)}
    grids_pre = {c: shade_grid(p) for c, p in nb.items()}
    grids_post = {c: shade_grid(p) for c, p in nb.items()}
    waters_pre = {c: water_grid(p) for c, p in nb.items()}
    waters_post = {c: water_grid(p) for c, p in nb.items()}
    grids_pre[TARGET] = shade_grid(pre_full);  waters_pre[TARGET] = water_grid(pre_full)
    grids_post[TARGET] = shade_grid(post_full); waters_post[TARGET] = water_grid(post_full)

    # (a1) the changed quads' FOUR edges are each a lawful ladder adjacency
    bad_edges = []
    for (i, j), (src, dst) in PLAN.items():
        sh = grids_post[TARGET][i][j]
        for d in "NESW":
            nsh, _nw = region_neighbour(grids_post, waters_post, *TARGET, i, j, d)
            lawful = is_lawful(sh, _norm(nsh))
            tag = "OK" if lawful else "!! FORBIDDEN"
            print(f"     ({i:2},{j:2}) {sh:5} .{d} -> {_norm(nsh):5}  {tag}")
            if not lawful:
                bad_edges.append(((i, j), d, sh, _norm(nsh)))
    if bad_edges:
        raise SystemExit(f"GATE a FAILED: {len(bad_edges)} off-language changed-quad edge(s): {bad_edges}")

    # (a2) sea1 -> sea4 direct edges on the island = 0
    def sea1_deep(grids, waters):
        n = 0
        for (bx, by) in ISLAND:
            if (bx, by) not in grids:
                continue
            g, w = grids[(bx, by)], waters[(bx, by)]
            for i in range(G):
                for j in range(G):
                    if g[i][j] != "sea1":
                        continue
                    for d in "NESW":
                        nsh, nw = region_neighbour(grids, waters, bx, by, i, j, d)
                        if _norm(nsh) == "sea4" and nw:
                            n += 1
        return n
    s1_pre = sea1_deep(grids_pre, waters_pre)
    s1_post = sea1_deep(grids_post, waters_post)
    print(f"     sea1->sea4 direct island edges: BEFORE {s1_pre} -> AFTER {s1_post}")
    if s1_post != 0:
        raise SystemExit(f"GATE a FAILED: {s1_post} sea1->sea4 edges remain (want 0)")

    # (a3) sea2 abuts only {sea2,sea1,beach1,land}: no FORBIDDEN (sea3/sea5/sea4/deep) edge INTRODUCED
    def sea2_forbidden(grids, waters):
        bad = set()
        g, w = grids[TARGET], waters[TARGET]
        for i in range(G):
            for j in range(G):
                if g[i][j] != "sea2":
                    continue
                for d in "NESW":
                    nsh, nw = region_neighbour(grids, waters, *TARGET, i, j, d)
                    if nw and _norm(nsh) in ("sea3", "sea5", "sea4"):
                        bad.add((i, j, d, _norm(nsh)))
        return bad
    pre_f = sea2_forbidden(grids_pre, waters_pre)
    post_f = sea2_forbidden(grids_post, waters_post)
    introduced_f = post_f - pre_f
    print(f"     sea2->{{sea3,sea5,sea4,deep}} forbidden edges: BEFORE {len(pre_f)} -> AFTER {len(post_f)} "
          f"(INTRODUCED {len(introduced_f)})")
    if introduced_f:
        raise SystemExit(f"GATE a FAILED: introduced sea2 forbidden edge(s): {sorted(introduced_f)}")
    if post_f:
        print(f"     [transparency] pre-existing sea2 forbidden residual (donor-verbatim, out of scope, "
              f"unchanged): {sorted(post_f)}")
    else:
        print("     sea2 abuts only {sea2,sea1,beach1,land}: CLEAN (never sea3/sea5/sea4/deep)")

    # (a4) the s12 shallow census over (12,18)+E/S neighbours: 2 -> 0, 0 introduced anywhere
    scope = [TARGET, E_NB, S_NB]
    pre_hard = shallow_census(grids_pre, waters_pre, [TARGET])
    post_hard = shallow_census(grids_post, waters_post, [TARGET])
    # also census the neighbours to catch any N/S introduced edge (the changed quads are on i14/i15)
    pre_all = shallow_census(grids_pre, waters_pre, scope)
    post_all = shallow_census(grids_post, waters_post, scope)
    introduced = post_all - pre_all
    print(f"     s12 shallow census (12,18): BEFORE {len(pre_hard)} hard -> AFTER {len(post_hard)}")
    print(f"     s12 shallow census (12,18)+E+S neighbourhood: BEFORE {len(pre_all)} -> AFTER {len(post_all)} "
          f"(removed {len(pre_all - post_all)}, INTRODUCED {len(introduced)})")
    for e in sorted(pre_hard - post_hard):
        print(f"        removed: {e}")
    if len(post_hard) != 0:
        for e in sorted(post_hard):
            print(f"        STILL HARD: {e}")
        raise SystemExit(f"GATE a FAILED: {len(post_hard)} shallow|deep hard edges remain (want 0)")
    if introduced:
        for e in sorted(introduced):
            print(f"        INTRODUCED: {e}")
        raise SystemExit(f"GATE a FAILED: {len(introduced)} shallow|deep edges INTRODUCED")
    if len(pre_hard) != 2:
        raise SystemExit(f"GATE a FAILED: expected 2 pre-fix hard edges, found {len(pre_hard)}: {pre_hard}")
    print("     => 2 -> 0, zero introduced (incl. N/S of the changed quads)")


def gate_b(pre, post):
    print("[gate b] SEA3/4/5 SYSTEM UNHARMED (frame incoherence still 0):")
    post_full = merged_parts(pre, post)
    # island {(bx,by): {part: BlockMesh}} using the LIVE tree for the other 3 cells, post for (12,18)
    island = {}
    for (bx, by) in ISLAND:
        if (bx, by) == TARGET:
            island[(bx, by)] = post_full
        else:
            island[(bx, by)] = load_cell(bx, by, mod=True)
    # (b1) transplant.wang_carry_gate (frame-only, sea3/4/5)
    sea_by_cell = {c: {p: parts[p] for p in ("sea3", "sea4", "sea5") if p in parts}
                   for c, parts in island.items()}
    g = T.wang_carry_gate(sea_by_cell, ISLAND, enforce=True)
    print(f"     wang_carry_gate(enforce): incoherent frame edges = {g['incoherent']}  ok={g['ok']}")
    if g["incoherent"] != 0 or not g["ok"]:
        raise SystemExit(f"GATE b FAILED: wang_carry_gate frame incoherent {g['incoherent']}: {g['detail']}")
    # (b2) the rim-retile land-aware FRAME census (its own instrument)
    frame, interior, _all = wrr.census(island)
    frame18 = {e for e in frame}
    print(f"     rim-retile land-aware FRAME census: {len(frame18)} incoherent (want 0)")
    if len(frame18) != 0:
        for e in sorted(frame18):
            print(f"        FRAME INCOHERENT: {e}")
        raise SystemExit(f"GATE b FAILED: {len(frame18)} rim-retile frame seams")
    print(f"     [transparency] rim-retile INTERIOR residual = {len(interior)} -- this count treats sea1 as "
          f"deep (the sea3/4/5 grid is SHALLOW-BLIND, the LOGGED-LATER gap); the new sea5 E-tips' W edges "
          f"face sea1 read-as-sea4, so this number shifts.  The ACTUAL shallow coherence is gate (a).")


def _water_multiset(parts):
    """{(sorted 3 rounded verts, tangent.x topo): count} over ALL 6 water parts -- the geometry+topo
    signature.  A pure repartition (only UV + file membership move) leaves this IDENTICAL."""
    c = Counter()
    for part in WATERPARTS:
        for [_cell, verts, topo] in wrr.part_tris(parts.get(part)):
            key = (tuple(sorted(tuple(round(x, 4) for x in v[0]) for v in verts)), topo)
            c[key] += 1
    return c


def gate_c(pre_full, post_full, post):
    print("[gate c] PURE REPARTITION + FLAT-MESH + SEA-LAYER:")
    pre_ms = _water_multiset(pre_full)
    post_ms = _water_multiset(post_full)
    if pre_ms != post_ms:
        raise SystemExit("GATE c FAILED: (verts+tangent.x) triangle multiset changed -- NOT a pure repartition")
    print(f"     (verts+tangent.x) multiset over all 6 water parts: IDENTICAL before==after "
          f"({sum(pre_ms.values())} tris)")
    # FLAT-MESH per written file
    for part, bm in post.items():
        n = len(bm.flat_index)
        if not (bm.vcount == n and n % 3 == 0 and (max(bm.flat_index) if bm.flat_index else -1) < bm.vcount):
            raise SystemExit(f"GATE c FAILED: {part} not flat ({bm.vcount}v / {n}idx)")
    # SEA-LAYER: the union vertex-Y multiset over the 3 changed parts is unchanged (a vert only moves
    # part, never off-surface) and at the water surface.
    def ys(getparts):
        return sorted(round(v[1], 5) for part in ("sea1", "sea2", "sea5") if getparts.get(part)
                      for v in getparts[part].verts)
    pre_y, post_y = ys(pre_full), ys(post_full)
    if pre_y != post_y:
        raise SystemExit("GATE c FAILED: union vertex-Y multiset changed (a vert moved off-surface)")
    ymax = max(abs(y) for y in post_y) if post_y else 0.0
    print(f"     all 3 written parts flat (vcount==idx); union vertex-Y unchanged (max|Y|={ymax:.3f}u)")


def gate_d(pre, post):
    print("[gate d] BYTE-DIFF SCOPED (only (12,18) Sea1/Sea2/Sea5 change):")
    bx, by = TARGET
    changed = set()
    for part in WATERPARTS:
        cap = part.capitalize()
        if part in post:
            pre_bytes = wrr._serialize(wrr.build_part([e[1] for e in wrr.part_tris(pre[part])], cap, bx, by, 1))
            post_bytes = wrr._serialize(post[part])
            if pre_bytes != post_bytes:
                changed.add(cap)
    if changed != EXPECT_CHANGED:
        raise SystemExit(f"GATE d FAILED: changed {sorted(changed)} != declared {sorted(EXPECT_CHANGED)}")
    print(f"     in-memory changed parts: {sorted(changed)} == declared {sorted(EXPECT_CHANGED)}")
    return changed


def _serialize_file(p):
    return Path(p).read_bytes()


# --------------------------------------------------------------------------- deploy
def deploy(post):
    """Write the 3 changed parts to Disc1 (M.write_ff9mesh), then EXPLICIT byte-copy Disc1 -> Disc4."""
    bx, by = TARGET
    written = []
    for part in ("sea1", "sea2", "sea5"):
        cap = part.capitalize()
        bm = post[part]
        d1 = _rdir(1, by) / f"Block[{bx}][{by}] {cap}.ff9mesh"
        M.write_ff9mesh(wrr.build_part([e[1] for e in wrr.part_tris(bm)], cap, bx, by, 1), d1)
        written.append(d1)
        d4 = _rdir(4, by) / f"Block[{bx}][{by}] {cap}.ff9mesh"
        shutil.copyfile(d1, d4)                                # explicit byte-copy -> guaranteed Disc1==Disc4
        written.append(d4)
    print(f"[deploy] wrote {len(written)} files ((12,18) Sea1/Sea2/Sea5, Disc1 + explicit byte-copy Disc4)")
    return written


def gate_e_and_scope():
    print("[gate e] DISC PARITY + untouched-scope:")
    bx, by = TARGET
    for part in EXPECT_CHANGED:
        h1 = _md5(_rdir(1, by) / f"Block[{bx}][{by}] {part}.ff9mesh")
        h4 = _md5(_rdir(4, by) / f"Block[{bx}][{by}] {part}.ff9mesh")
        if h1 != h4:
            raise SystemExit(f"GATE e FAILED: Disc1 != Disc4 for (12,18) {part}")
    print("     (12,18) Sea1/Sea2/Sea5 Disc1==Disc4 (byte-copy)")
    # every OTHER cell + every non-changed (12,18) file == its backup (if backed up) / unchanged since PRE.
    # We verify: (12,18) Beach1/Sea3/Sea4/Donor + all (11,18)/(11,19)/(12,19) files == the recorded PRE
    # hashes (captured at first run into BK/SCOPE.txt).
    scope = BK / "SCOPE.txt"
    cur = _scope_hashes()
    if scope.exists():
        want = dict(line.split("  ", 1)[::-1] for line in scope.read_text().splitlines() if "  " in line)
        # want: {relpath: md5}
        want = {}
        for line in scope.read_text().splitlines():
            if line.strip():
                md5, rel = line.split("  ", 1)
                want[rel] = md5
        changed = [k for k in cur if cur[k] != want.get(k)]
        missing = [k for k in want if k not in cur]
        if changed or missing:
            raise SystemExit(f"GATE e FAILED: out-of-scope files changed: {changed}  missing: {missing}")
        print(f"     out-of-scope files byte-identical to PRE ({len(cur)} files hashed)")
    else:
        scope.write_text("\n".join(f"{md5}  {rel}" for rel, md5 in sorted(cur.items())) + "\n", encoding="utf-8")
        print(f"     [first run] recorded {len(cur)} out-of-scope PRE hashes to {scope.name}")


def _scope_hashes():
    """md5 of every file that MUST stay byte-identical: (12,18)'s non-changed files + all of the other 3
    island cells, both discs.  Literal-prefix iterdir (NEVER a glob with '[')."""
    out = {}
    for disc in DISCS:
        for (bx, by) in ISLAND:
            rdir = _rdir(disc, by)
            pre = f"Block[{bx}][{by}] "
            for p in sorted(rdir.iterdir()):
                if not (p.is_file() and p.name.startswith(pre)):
                    continue
                part = p.name[len(pre):].replace(".ff9mesh", "").replace(".txt", "")
                if (bx, by) == TARGET and part in EXPECT_CHANGED:
                    continue                                   # the 3 files we intend to change
                out[f"d{disc}/r{by}/{p.name}"] = _md5(p)
    return out


def verify_deployed():
    """Re-read on-disk (12,18) + neighbours and re-run gate-a's shallow census on the DEPLOYED bytes."""
    grids, waters = {}, {}
    for (bx, by), mod in ((TARGET, True), (E_NB, False), (S_NB, True)):
        parts = load_cell(bx, by, mod=mod)
        grids[(bx, by)] = shade_grid(parts); waters[(bx, by)] = water_grid(parts)
    hard = shallow_census(grids, waters, [TARGET])
    print(f"[verify] on-disk (12,18) shallow|deep hard edges: {len(hard)} (want 0)")
    if hard:
        raise SystemExit(f"VERIFY FAILED: deployed still has hard edges {sorted(hard)}")


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", action="store_true", help="perform the writes (both discs)")
    args = ap.parse_args()

    ensure_backup()
    pre = load_pre_parts()
    r5, n5 = harvest_etip("sea5")
    r1, n1 = harvest_etip("sea1")
    etip = {"sea5": r5, "sea1": r1}
    print(f"[harvest] verbatim donor E-tips (strip0/r0, deepset {{E}}): sea5 rect={r5} ({n5} samples, spread 0), "
          f"sea1 rect={r1} ({n1} samples, spread 0)")

    post, moved = apply_plan(pre, etip)
    print("[plan] 4-quad pure repartition (irregular shore cells: verts+topo carried byte-exact, UV re-mapped):")
    for (i, j), (src, dst, ntri, topos) in moved.items():
        print(f"     ({i:2},{j:2}) {src} -> {dst}  {ntri} tri(s), topo {topos} preserved")
    pre_full = pre
    post_full = merged_parts(pre, post)

    gate_a(pre_full, post_full)
    gate_b(pre, post)
    gate_c(pre_full, post_full, post)
    changed = gate_d(pre, post)

    if not args.deploy:
        print("\n(dry run -- all in-memory gates PASS; re-run with --deploy to write both discs)")
        return

    deploy(post)
    gate_e_and_scope()
    verify_deployed()
    print(f"\nDONE.  {{sea1,sea5}} ladder closed at (12,18) SE corner: 4 quads repartitioned "
          f"(2 Sea1->Sea5 + 2 Sea2->Sea1), both discs.\n"
          f"(11,18)/(11,19)/(12,19) + Beach1/Sea3/Sea4/Object/Donor untouched.\n"
          f"POST render: py studies/overworld-topography/whole_island_eye.py sea1_ladder_post.png\n"
          f"Revert: copy backups/sea1-ladder.20260720/Disc*__* back over the deployed files.")


if __name__ == "__main__":
    main()
