"""THE REAL-SCALE comp[1] WHOLE-STAMP DUNES MINT -- rung 5 of the dunes arc (2026-07-21).

THE DUNES SIZE-CLASS LAW (GROUND-FAMILY-DECODE-2026-07-19.md Round 4) closed the small-patch mint
(dunes_patch_mint.py v1-v4) as FALSIFIED: at ~31 cells every dressing quilts, because stock's
ecotone vocabulary is painted for its only two real dunes components (273/130 cells, ZERO freckles
map-wide). The lawful unit is a >=~130-cell multi-block dunes field that STAMPS A REAL COMPONENT
WHOLE.

This builds it: comp[1] (130 dunes cells + its 14-cell topo-59 enclosed hole) stamped VERBATIM
(bijective rigid dihedral+translation) onto a fresh multi-block `--ground desert` host, with the
ecotone rows CARRIED verbatim (the full-scale stamp makes the ENTIRE boundary real comp[1]
boundary, so a bijection lets the dressing be carried, not synthesized -- THE FORM LESSON's end).
Geometry stays byte-identical to a plain desert island; only uv + tangent.x change on the stamped
cells. The frozen instrument (dunes_mint_eye.judge) is the visual gate; the stamp equals comp[1]
relocated, so it passes by construction. The ONE deliberate deviation: the 14 topo-59 hole cells
(undecoded, non-walkable) are FILLED with plain dunes mains (the only in-vocabulary faithful
option; the hole is interior, invisible to silhouette/ecotone, stock interiors are ~all plain
mains, and filling makes the interior seamless walkable dunes).

Run OFFLINE (judges + renders, writes NOTHING to the game):  py studies/overworld-topography/dunes_field_mint.py
DEPLOY (guarded):                                             py studies/overworld-topography/dunes_field_mint.py --deploy
Artifacts -> out/dunes_field_mint.json, out/dunes_field_mint_*.png
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import math
import shutil
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg                          # noqa: E402
from ff9mapkit.world import discmirror as DM                  # noqa: E402
from ff9mapkit.world import extract as X                      # noqa: E402
from ff9mapkit.world import grassland as G                    # noqa: E402
from ff9mapkit.world import island as I                       # noqa: E402
from ff9mapkit.world import mesh as M                          # noqa: E402
from ff9mapkit.world import placement as P                    # noqa: E402

import dunes_mint_eye as EYE                                  # noqa: E402  (census + judge + comp1 + render prims)

BLOCK = 64.0
CELL_U = 4.0
NEI4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
GROUND = "desert"
MOD = "FF9CustomMap-world"
MAINS_SEED = 0xF91
EPS = 0.006
TOL_V = 0.008
ROW_PITCH = 0.03125
OUTD = HERE / "out"
OUTD.mkdir(exist_ok=True)
BACKUP_DIR = HERE.parents[1] / "backups" / "dunes-mint.20260720"

# post-reset occupied blocks (comp20 massif (6-7,18-19) + desert islet (8,19) + the (8,17)+2x2
# desert-beach water island (11-12,18-19) + its water-only (11,19); (9,19) reserved-untouched)
EXCLUDED_BLOCKS = {(6, 18), (7, 18), (6, 19), (7, 19), (8, 19), (9, 19),
                   (11, 18), (12, 18), (11, 19), (12, 19)}

# candidate host ladder: census-siting-preferred (a coherent little desert archipelago at the
# host census's own centre (608,-1376), near the (8,19) islet), at the stamp-design's radii. EACH
# entry is a ZERO-WELD-PAIR seed (scanned: build_landmass's big-mint edge refinement leaves hairline
# near-miss verts for SOME seeds -- e.g. the census's own s11 -- caught by mesh.weld_audit though
# verify_landmass's coarser once-edge/crack gates pass; the verbatim stamp is seed-independent, so we
# choose a crack-free host). resolve_host() REQUIRES per-block weld==0 AND a strict dilate3 placement,
# and prefers identity (k=0). PRIMARY = r56 s2: zero-weld + k=0 + 17 placements (probe-confirmed).
HOST_LADDER = [
    ("census (9,21) r56 s2", (608.0, -1376.0), 56.0, 2.0),      # zero-weld, k=0 identity, 17 placements
    ("census (9,21) r56 s8", (608.0, -1376.0), 56.0, 8.0),      # zero-weld fallback
    ("census (9,21) r56 s10", (608.0, -1376.0), 56.0, 10.0),    # zero-weld fallback
    ("census (9,21) r52 s2", (608.0, -1376.0), 52.0, 2.0),      # zero-weld, r52 precedent
    ("census (9,21) r52 s5", (608.0, -1376.0), 52.0, 5.0),      # zero-weld fallback
    ("census (9,21) r52 s6", (608.0, -1376.0), 52.0, 6.0),      # zero-weld fallback
    ("census (9,21) r52 s8", (608.0, -1376.0), 52.0, 8.0),      # zero-weld fallback
    ("stamp (19,18) r56 s2", (1248.0, -1184.0), 56.0, 2.0),     # the stamp-design site, last resort
]

GATES: list = []


def gate(name: str, ok: bool, detail: str = "") -> bool:
    GATES.append((name, bool(ok), detail))
    print(f"GATE [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    return bool(ok)


# ============================================================================================
# cell-set helpers (LAW 5 -- re-derived inline, independently rerunnable)
# ============================================================================================
def dilate(cells, exclude):
    nxt = set()
    for c in cells:
        for di, dj in NEI4:
            n = (c[0] + di, c[1] + dj)
            if n not in exclude:
                nxt.add(n)
    return nxt


def dilate_n(cells, n):
    full = set(cells)
    frontier = set(cells)
    for _ in range(n):
        ring = dilate(frontier, full)
        full |= ring
        frontier = ring
    return full


def boundary_of(cellset):
    return {c for c in cellset if any((c[0] + di, c[1] + dj) not in cellset for di, dj in NEI4)}


def enclosed_hole(cellset):
    xs = [c[0] for c in cellset]; zs = [c[1] for c in cellset]
    x0, x1, z0, z1 = min(xs) - 1, max(xs) + 1, min(zs) - 1, max(zs) + 1
    outside, q = set(), deque()
    border = [(i, z0) for i in range(x0, x1 + 1)] + [(i, z1) for i in range(x0, x1 + 1)] \
        + [(x0, j) for j in range(z0, z1 + 1)] + [(x1, j) for j in range(z0, z1 + 1)]
    for seed in border:
        if seed not in cellset and seed not in outside:
            outside.add(seed); q.append(seed)
    while q:
        c = q.popleft()
        for di, dj in NEI4:
            n = (c[0] + di, c[1] + dj)
            if x0 <= n[0] <= x1 and z0 <= n[1] <= z1 and n not in cellset and n not in outside:
                outside.add(n); q.append(n)
    return {(i, j) for i in range(x0, x1 + 1) for j in range(z0, z1 + 1)
            if (i, j) not in cellset and (i, j) not in outside}


def dihedral_point(i, j, k):
    if k >= 4:
        i = -i
    r = k % 4
    return (i, j) if r == 0 else (-j, i) if r == 1 else (-i, -j) if r == 2 else (j, -i)


# ---- strip_uv + zero-residual classifier (base-script verbatim -- LAW 5) ----------------------
PAIR = ("desert", "dunes")
STRIP_U0, STRIP_U1 = G.STRIP_U
ROW0_V0 = G.STRIPS_V[0][0]
_S = G.STRIPS[PAIR]
_DU, _DV = _S["du"], _S["dv"]
TOPO_FAM = {17: "desert", 41: "dunes", 58: "rock"}


def strip_uv(x, z, cell, row, ori=0):
    (i, j) = cell
    fx, fz = (x - CELL_U * i) / CELL_U, (z - CELL_U * j) / CELL_U
    a, b = G.rot_ab(fx, fz, ori)
    a, b = max(0.0, min(1.0, a)), max(0.0, min(1.0, b))
    u0, u1 = G.STRIP_U
    v0, v1 = G.STRIPS_V[row]
    return [u0 + a * (u1 - u0) + _DU, v0 + b * (v1 - v0) + _DV]


def _mains_rect(fam):
    m = G.FAM_REGION["main"]; g = G.GROUNDS[fam]
    return (m[0] + g["mains_du"], m[1] + g["mains_dv"], m[2] + g["mains_du"], m[3] + g["mains_dv"])


RECTS = {"desert": _mains_rect("desert"), "dunes": _mains_rect("dunes")}


def _rect_contains(rect, uv3, eps=EPS):
    return all(rect[0] - eps <= u <= rect[2] + eps and rect[1] - eps <= v <= rect[3] + eps for (u, v) in uv3)


def classify_strip(uv3):
    u_lo, u_hi = STRIP_U0 + _DU - EPS, STRIP_U1 + _DU + EPS
    if not all(u_lo <= u <= u_hi for (u, _v) in uv3):
        return None
    v_min = min(v for (_u, v) in uv3)
    row0 = ROW0_V0 + _DV
    k = round((v_min - row0) / ROW_PITCH)
    if k < 0 or k > 3 or abs((v_min - row0) - k * ROW_PITCH) > TOL_V:
        return None
    return int(k)


def classify_tri(topo, uv3):
    fam = TOPO_FAM.get(topo)
    if fam in PAIR:
        k = classify_strip(uv3)
        if k is not None:
            return ("strip", k)
    rect = RECTS.get(fam)
    if rect and _rect_contains(rect, uv3):
        return ("mains", fam)
    return ("other",)


def to_world(bm, cell):
    bx, by = cell
    return [(v[0] + BLOCK * bx, v[1], v[2] - BLOCK * by) for v in bm.verts]


def once_edges_from_bm(bm, cell):
    world_pos = to_world(bm, cell)
    tris_idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
    c = Counter()
    for tri in tris_idx:
        ks = [tuple(round(v, 3) for v in world_pos[j]) for j in tri]
        for i in range(3):
            e = frozenset((ks[i], ks[(i + 1) % 3]))
            if len(e) == 2:
                c[e] += 1
    return {e for e, n in c.items() if n == 1}


# ============================================================================================
# STEP 1 -- reconstruct comp[1]'s full painting in its own WORLD frame (from the census)
# ============================================================================================
def build_comp1_painting():
    COMP1 = EYE.COMP1                                # 130 dunes cells (world coords)
    strip_cells = EYE.strip_cells                   # {world cell: row 0-3} map-wide
    HOLE = enclosed_hole(COMP1)
    FOOTPRINT = COMP1 | HOLE
    BOUNDARY = boundary_of(COMP1)
    OUTER = dilate(FOOTPRINT, FOOTPRINT)
    dune_rows = {c: strip_cells[c] for c in COMP1 if c in strip_cells}       # dune-side strip
    desert_rows = {c: strip_cells[c] for c in OUTER if c in strip_cells}     # desert-side strip
    hole_fams = Counter()
    for c in HOLE:
        fc = EYE.fams_at.get(c)
        hole_fams[fc.most_common(1)[0][0] if fc else None] += 1
    # cross-check against dunes_blob_shapes.json's committed real_component_1_verbatim template
    disk = HERE / "out" / "dunes_blob_templates.json"
    xok, xdet = None, "templates json absent"
    if disk.is_file():
        rec = json.loads(disk.read_text(encoding="utf-8"))
        t = next((t for t in rec["templates"] if t["name"] == "real_component_1_verbatim"), None)
        if t is not None:
            xs = [c[0] for c in COMP1]; zs = [c[1] for c in COMP1]
            norm = {(c[0] - min(xs), c[1] - min(zs)) for c in COMP1}
            disk_norm = {tuple(c) for c in t["cell_offsets"]}
            xok = (norm == disk_norm)
            xdet = f"live={len(norm)} disk={len(disk_norm)} match={xok}"
    gate("comp[1] cell-set matches dunes_blob_shapes.py's committed real_component_1_verbatim "
         "template (130 cells, byte-normalized -- LAW 5)", xok is True, xdet)
    return dict(COMP1=COMP1, HOLE=HOLE, FOOTPRINT=FOOTPRINT, BOUNDARY=BOUNDARY, OUTER=OUTER,
                dune_rows=dune_rows, desert_rows=desert_rows, hole_fams=dict(hole_fams),
                strip_cells=strip_cells)


# ============================================================================================
# STEP 2 -- the desert host + multi-block regular-cell gather + placement search
# ============================================================================================
def build_host(center, radius, seed):
    built = I.build_landmass(center=center, base_radius=radius, seed=seed, ground=GROUND,
                             stamps=None, disc=1)
    occ = {blk: o for blk in built["blocks"] if (o := I._real_block_parts(blk, disc=1, game=None))}
    excl = {blk for blk in built["blocks"] if blk in EXCLUDED_BLOCKS}
    if occ or excl:
        return None, f"occupied={sorted(occ)} excluded={sorted(excl)}"
    geom_by_block, all_mains, regular = {}, {}, set()
    for blk, bm in built["blocks"].items():
        bx, by = blk
        wp = to_world(bm, blk)
        tris = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
        geom_by_block[blk] = dict(bm=bm, world_pos=wp, tris_idx=tris)
        cellt = defaultdict(list)
        for ti, tri in enumerate(tris):
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            if topo != 17:
                continue
            cx = sum(wp[j][0] for j in tri) / 3.0
            cz = sum(wp[j][2] for j in tri) / 3.0
            cellt[(math.floor(cx / CELL_U), math.floor(cz / CELL_U))].append(ti)
        for cell, tl in cellt.items():
            all_mains[cell] = (blk, tl)
            ci, cj = cell
            ok = True
            for ti in tl:
                for j in tris[ti]:
                    fx = (wp[j][0] - CELL_U * ci) / CELL_U
                    fz = (wp[j][2] - CELL_U * cj) / CELL_U
                    if min(abs(fx), abs(fx - 1)) > 0.02 or min(abs(fz), abs(fz - 1)) > 0.02:
                        ok = False; break
                if not ok:
                    break
            if ok:
                regular.add(cell)
    return dict(built=built, geom_by_block=geom_by_block, all_mains=all_mains, regular=regular,
                blocks=sorted(built["blocks"]), center=center, radius=radius, seed=seed), None


def search_placement(regular, footprint, host_center):
    """Placement = dihedral k + translation with dilate3(footprint) (footprint+ring+2-margin)
    entirely on regular cells. Prefer k=0 (identity, comp[1] as-is relocated), then nearest to
    host centre. Returns (k, ti0, tj0, oi, oj, n_candidates) or None."""
    if not regular:
        return None
    xs = sorted({c[0] for c in regular}); zs = sorted({c[1] for c in regular})
    bx0 = min(c[0] for c in footprint); bz0 = min(c[1] for c in footprint)
    fp_norm = [(c[0] - bx0, c[1] - bz0) for c in footprint]
    best, n_cand = None, 0
    for k in range(8):
        pts = [dihedral_point(i, j, k) for (i, j) in fp_norm]
        ti0 = min(p[0] for p in pts); tj0 = min(p[1] for p in pts)
        fpn = {(p[0] - ti0, p[1] - tj0) for p in pts}
        w = max(p[0] for p in fpn) + 1; h = max(p[1] for p in fpn) + 1
        for oi in range(xs[0] - 3, xs[-1] - w + 4):
            for oj in range(zs[0] - 3, zs[-1] - h + 4):
                fp = {(oi + a, oj + b) for (a, b) in fpn}
                if not fp <= regular:
                    continue
                if not dilate_n(fp, 3) <= regular:
                    continue
                n_cand += 1
                wx = CELL_U * (oi + w / 2.0); wz = CELL_U * (oj + h / 2.0)
                d = math.hypot(wx - host_center[0], wz - host_center[1])
                score = (0 if k == 0 else 1, round(d, 3), k, oi, oj)
                if best is None or score < best[0]:
                    best = (score, k, ti0, tj0, oi, oj)
    if best is None:
        return None
    _s, k, ti0, tj0, oi, oj = best
    return dict(k=k, ti0=ti0, tj0=tj0, oi=oi, oj=oj, bx0=bx0, bz0=bz0, n_candidates=n_cand)


def resolve_host(paint):
    for label, center, radius, seed in HOST_LADDER:
        host, err = build_host(center, radius, seed)
        if host is None:
            print(f"  host [{label}] REJECT -- {err}")
            continue
        # per-block weld audit (mesh.weld_audit works in a single block's LOCAL frame -- audit each
        # block on its own, the proven usage; a host with ANY hairline near-miss pair is rejected)
        wpairs = sum(len(M.weld_audit([g["bm"]])) for g in host["geom_by_block"].values())
        if wpairs:
            print(f"  host [{label}] REJECT -- {wpairs} weld near-miss pair(s) in the plain host")
            continue
        pl = search_placement(host["regular"], paint["FOOTPRINT"], center)
        if pl is None:
            print(f"  host [{label}] OK build ({len(host['regular'])} regular) but NO strict placement")
            continue
        print(f"\n=== HOST WINNER: {label} centre={center} r={radius} seed={seed} "
              f"blocks={host['blocks']} regular={len(host['regular'])} "
              f"dihedral={pl['k']} origin=({pl['oi']},{pl['oj']}) placements={pl['n_candidates']} ===\n")
        host["label"] = label
        return host, pl
    raise SystemExit("no strict host in the ladder -- widen radius or revisit siting")


def place_cell(cell, pl):
    a, b = cell[0] - pl["bx0"], cell[1] - pl["bz0"]
    pi, pj = dihedral_point(a, b, pl["k"])
    return (pi - pl["ti0"] + pl["oi"], pj - pl["tj0"] + pl["oj"])


# ============================================================================================
# STEP 3 -- multi-block retile (stamp comp[1] whole + fill hole + verbatim ecotone dressing)
# ============================================================================================
def plan_retile(paint, pl):
    T = {c: place_cell(c, pl) for c in paint["OUTER"] | paint["FOOTPRINT"]}
    placed_comp1 = {T[c] for c in paint["COMP1"]}
    placed_hole = {T[c] for c in paint["HOLE"]}
    placed_footprint = placed_comp1 | placed_hole
    placed_outer = {T[c] for c in paint["OUTER"]}
    placed_dune_rows = {T[c]: r for c, r in paint["dune_rows"].items()}     # host cell -> row (topo41 strip)
    placed_desert_rows = {T[c]: r for c, r in paint["desert_rows"].items()}  # host cell -> row (topo17 strip)
    dunes_mains = placed_footprint - set(placed_dune_rows)                  # comp1 non-strip + hole -> dunes mains
    return dict(T=T, placed_comp1=placed_comp1, placed_hole=placed_hole,
                placed_footprint=placed_footprint, placed_outer=placed_outer,
                placed_dune_rows=placed_dune_rows, placed_desert_rows=placed_desert_rows,
                dunes_mains=dunes_mains)


def apply_retile(host, rp):
    all_mains, geom = host["all_mains"], host["geom_by_block"]
    idall_dunes = float(X.encode_id(topograph=41))
    idall_desert = float(X.encode_id(topograph=17))
    quad, ori = G.assign_mains(rp["dunes_mains"], seed=MAINS_SEED)
    n = Counter()
    for cell in rp["dunes_mains"]:
        blk, tl = all_mains[cell]; bm, wp, tris = geom[blk]["bm"], geom[blk]["world_pos"], geom[blk]["tris_idx"]
        q, o = quad[cell], ori[cell]
        for ti in tl:
            for j in tris[ti]:
                u, v = G.ground_uv(wp[j][0], wp[j][2], cell, q, o, "dunes")
                bm.uvs[j][0], bm.uvs[j][1] = u, v
                bm.tangents[j][0] = idall_dunes
        n["dunes_mains"] += 1
    for cell, row in rp["placed_dune_rows"].items():
        blk, tl = all_mains[cell]; bm, wp, tris = geom[blk]["bm"], geom[blk]["world_pos"], geom[blk]["tris_idx"]
        for ti in tl:
            for j in tris[ti]:
                u, v = strip_uv(wp[j][0], wp[j][2], cell, row)
                bm.uvs[j][0], bm.uvs[j][1] = u, v
                bm.tangents[j][0] = idall_dunes
        n["inner_strip"] += 1
    for cell, row in rp["placed_desert_rows"].items():
        blk, tl = all_mains[cell]; bm, wp, tris = geom[blk]["bm"], geom[blk]["world_pos"], geom[blk]["tris_idx"]
        for ti in tl:
            for j in tris[ti]:
                u, v = strip_uv(wp[j][0], wp[j][2], cell, row)
                bm.uvs[j][0], bm.uvs[j][1] = u, v
                bm.tangents[j][0] = idall_desert
        n["outer_strip"] += 1
    print(f"  retiled cells: {dict(n)} (untouched-outer = {len(rp['placed_outer']) - n['outer_strip']})")
    return dict(n_cells=dict(n))


# ============================================================================================
# STEP 4 -- the gate suite
# ============================================================================================
def run_gates(host, rp, snapshot, plane):
    geom = host["geom_by_block"]; all_mains = host["all_mains"]
    touched = rp["placed_footprint"] | rp["placed_outer"]

    # (a) zero vertex motion, per touched block
    vok = nok = True
    for blk, snap in snapshot.items():
        bm = geom[blk]["bm"]
        vok = vok and bm.verts == snap["verts"]
        nok = nok and bm.normals == snap["normals"]
    gate("zero vertex motion (verts byte-identical across all touched blocks)", vok)
    gate("zero vertex motion (normals byte-identical across all touched blocks)", nok)

    # (b) zero-residual classification over the touched footprint+ring
    tally, n_other = Counter(), 0
    for cell in touched:
        if cell not in all_mains:
            continue
        blk, tl = all_mains[cell]; bm, tris = geom[blk]["bm"], geom[blk]["tris_idx"]
        for ti in tl:
            tri = tris[ti]
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            tag = classify_tri(topo, [tuple(bm.uvs[j]) for j in tri])
            tally[tag[0]] += 1
            n_other += tag[0] == "other"
    gate("retile zero-residual classification (touched footprint+ring: only dunes-mains/strip/"
         "desert-mains, zero 'other')", n_other == 0, f"tally={dict(tally)}")

    # (c) boundary invariance + weld + frame, per touched block
    binv = True
    for blk, snap in snapshot.items():
        binv = binv and (once_edges_from_bm(geom[blk]["bm"], blk) == snap["once_edges"])
    gate("boundary invariance (once-edge set unchanged by retile, every touched block)", binv)
    # weld_audit reads verts in each block's LOCAL frame -> audit PER BLOCK (the proven usage;
    # combining blocks would mix local frames). The host was already resolved to zero-weld; this
    # re-runs post-retile (verts untouched -> still zero) as the regression proof.
    weld_by_block = {blk: len(M.weld_audit([geom[blk]["bm"]])) for blk in geom}
    total_pairs = sum(weld_by_block.values())
    gate("weld audit (0 near-miss vertex pairs, every block audited in its own local frame)",
         total_pairs == 0, f"per-block={ {b: n for b, n in weld_by_block.items() if n} } total={total_pairs}")
    fok = True
    for blk in geom:
        bm = geom[blk]["bm"]
        lx = [v[0] for v in bm.verts]; lz = [v[2] for v in bm.verts]
        fok = fok and (-0.06 <= min(lx) and max(lx) <= 64.06 and -64.06 <= min(lz) and max(lz) <= 0.06)
    gate("frame-bounds (local verts inside the block frame, every block)", fok)

    # (d) IDALL_SKIP structurally impossible (area 0 everywhere)
    skip = any(int(round(geom[blk]["bm"].tangents[j][0])) in P.IDALL_SKIP
               for blk in geom for j in range(geom[blk]["bm"].vcount))
    gate("IDALL_SKIP collision (structurally impossible, area always 0)", not skip)

    # (e) placement census MISS regression + MISS==0, per touched block
    def meshlist(blk, bm):
        bx, by = blk
        hid = lambda nm: M.hidden_block_mesh(name=nm, disc=1, x=bx, y=by)  # noqa: E731
        return [("Object", hid("Object")), ("Terrain", bm), ("Sea1", hid("Sea1")), ("Sea2", hid("Sea2")),
                ("Sea3", hid("Sea3")), ("Sea4", dataclasses.replace(plane, x=bx, y=by)), ("Sea5", hid("Sea5"))]
    touched_blocks = {all_mains[c][0] for c in touched if c in all_mains}
    miss_reg = miss0 = True
    miss_detail = {}
    for blk in sorted(touched_blocks):
        after = P.census(meshlist(blk, geom[blk]["bm"]), samples=24)
        before = P.census(meshlist(blk, snapshot[blk]["bm_plain"]), samples=24)
        miss_reg = miss_reg and (set(map(tuple, after["miss"])) == set(map(tuple, before["miss"])))
        miss0 = miss0 and (len(after["miss"]) == 0)
        miss_detail[blk] = (len(before["miss"]), len(after["miss"]))
    gate("placement census MISS regression (retile identical to plain host, every touched block)",
         miss_reg, f"{miss_detail}")
    gate("placement census MISS==0 (post-retile, every touched block)", miss0, f"{miss_detail}")

    # (f) save-brick probes -- actually ground-query
    def probe(cell):
        blk = all_mains[cell][0]; bx, by = blk
        px, pz = CELL_U * cell[0] + CELL_U / 2, CELL_U * cell[1] + CELL_U / 2
        lx, lz = px - BLOCK * bx, pz + BLOCK * (by + 1) - BLOCK
        gy, nm, _idall, topo = P.place(meshlist(blk, geom[blk]["bm"]), lx, lz, sky=True)
        return nm, topo, gy
    # footprint centre-ish: a core dunes cell nearest the placed-footprint centroid
    cx = CELL_U * (sum(c[0] for c in rp["placed_footprint"]) / len(rp["placed_footprint"]) + 0.5)
    cz = CELL_U * (sum(c[1] for c in rp["placed_footprint"]) / len(rp["placed_footprint"]) + 0.5)
    core_pool = [c for c in rp["dunes_mains"] if c in rp["placed_comp1"]] or list(rp["dunes_mains"])
    core_cell = min(core_pool, key=lambda c: (CELL_U * c[0] - cx) ** 2 + (CELL_U * c[1] - cz) ** 2)
    nm, topo, gy = probe(core_cell)
    gate(f"save-brick probe: a CORE dunes cell {core_cell} grounds walkable dunes (topo 41)",
         nm == "Terrain" and topo == 41, f"mesh={nm} topo={topo} y={gy:.2f}")
    hole_ok = True; hole_det = []
    for c in list(rp["placed_hole"])[:3]:
        nm, topo, _ = probe(c); hole_ok = hole_ok and nm == "Terrain" and topo == 41
        hole_det.append((c, nm, topo))
    gate("save-brick probe: filled-hole cells ground walkable dunes (topo 41)", hole_ok or not rp["placed_hole"], f"{hole_det}")
    ring_ok = True; ring_det = []
    for c in sorted(list(rp["placed_dune_rows"])[:2] + list(rp["placed_desert_rows"])[:2]):
        nm, topo, _ = probe(c); ok = nm == "Terrain" and topo in (17, 41)
        ring_ok = ring_ok and ok; ring_det.append((c, nm, topo, ok))
    gate("save-brick probe: sampled inner/outer strip-ring cells ground walkable", ring_ok, f"{ring_det}")

    # (g) shape-fidelity: placed comp1 (130) silhouette IDENTICAL to comp[1]'s own (rigid transform)
    s_tmpl = EYE.shape_stats(EYE.COMP1)
    s_plac = EYE.shape_stats(rp["placed_comp1"])
    shp_ok = (s_tmpl["convexity"] == s_plac["convexity"] and s_tmpl["max_run"] == s_plac["max_run"]
              and s_tmpl["n_holes"] == s_plac["n_holes"])
    gate("SHAPE-FIDELITY -- placed comp[1] silhouette (convexity/max_run/holes) IDENTICAL to the "
         "stock template (rigid transform; any diff = a dropped cell)", shp_ok,
         f"template={s_tmpl} placed={s_plac}")

    # (h) ROW-0 GUARD -- non-degeneracy
    all_rows = list(rp["placed_dune_rows"].values()) + list(rp["placed_desert_rows"].values())
    gate("ROW-0 GUARD (>=2 distinct rows across the ecotone; all-one-row is the sole out-of-family "
         "assignment)", len(set(all_rows)) >= 2, f"rows used={sorted(set(all_rows))}")
    return dict(tally=dict(tally), miss=miss_detail, shape_template=s_tmpl, shape_placed=s_plac)


# ============================================================================================
# STEP 5 -- the frozen instrument (dunes_mint_eye.judge)
# ============================================================================================
def run_judge(paint, rp):
    T = rp["T"]
    placed_comp1_130 = {T[c] for c in paint["COMP1"]}
    placed_dune_rows = {T[c]: paint["strip_cells"][c] for c in paint["COMP1"] if c in paint["strip_cells"]}
    print("\n--- THE FROZEN EYE: judge(placed dune-side rows, placed comp[1] 130-cell silhouette) ---")
    verdict = EYE.judge(placed_dune_rows, placed_comp1_130, label="dunes MINT (verbatim comp[1] stamp)")
    gate("THE FROZEN EYE (dunes_mint_eye.judge) -- ALL frozen gates PASS (M1 jumpiness, M2 same-row, "
         "M3 silhouette+hole, M4 interior-coverage)", verdict["passed"],
         {g: v for g, (v, p) in verdict["gates"].items()})
    return verdict


# ============================================================================================
# STEP 6 -- renders (mint vs comp[1] in-situ, the eye's three frozen zooms)
# ============================================================================================
LDIR = (-0.45, 0.72, 0.45)
_l = math.sqrt(sum(q * q for q in LDIR)); LDIR = tuple(q / _l for q in LDIR)
ROW_COLOR = {0: (230, 60, 60), 1: (240, 170, 40), 2: (70, 190, 90), 3: (70, 130, 240)}


def _atlas():
    GP = Path(_cfg.find_game_path(None))
    MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / "textures" / "res(1_24)_terrain.png"
    a = Image.open(MOG).convert("RGBA")
    return a, a.size, a.load()


def synth_tris(bm, cell):
    bx, by = cell
    V, N, U, TAN = bm.verts, bm.normals, bm.uvs, bm.tangents
    out = []
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        p3 = [(V[j][0] + BLOCK * bx, V[j][1], V[j][2] - BLOCK * by) for j in tri]
        uv3 = [tuple(U[j][:2]) for j in tri]
        n3 = [tuple(N[j][:3]) for j in tri]
        topo = X.decode_id(int(round(TAN[tri[0]][0])))["topograph"]
        out.append((p3, uv3, n3, topo))
    return out


def stock_tris(bx, by):
    return synth_tris(X.read_block(bx, by, disc=1, part="terrain"), (bx, by))


def paint(tris, cx, cz, win, sc, atlas_wh, atlas_px, rowmap=False):
    AW, AH = atlas_wh

    def at_b(u_, v_):
        fx = (u_ % 1.0) * AW - 0.5; fy = (1.0 - v_ % 1.0) * AH - 0.5
        x0, y0 = int(math.floor(fx)), int(math.floor(fy)); tx, ty = fx - x0, fy - y0
        acc = [0.0, 0.0, 0.0]; aa = 0.0
        for (dx, dy, wg) in ((0, 0, (1-tx)*(1-ty)), (1, 0, tx*(1-ty)), (0, 1, (1-tx)*ty), (1, 1, tx*ty)):
            r, g, b, a = atlas_px[min(max(x0+dx, 0), AW-1), min(max(y0+dy, 0), AH-1)]
            acc[0] += r*wg; acc[1] += g*wg; acc[2] += b*wg; aa += a*wg
        return aa, (acc[0], acc[1], acc[2])

    x0, x1, z0, z1 = cx - win/2, cx + win/2, cz - win/2, cz + win/2
    RW = RH = int(win * sc)
    tex = Image.new("RGB", (RW, RH), (120, 150, 200)); com = Image.new("RGB", (RW, RH), (120, 150, 200))
    tp, cp = tex.load(), com.load()
    plotted = []
    for (p3, uv3, n3, topo) in tris:
        if max(p[0] for p in p3) < x0 or min(p[0] for p in p3) > x1:
            continue
        if max(p[2] for p in p3) < z0 or min(p[2] for p in p3) > z1:
            continue
        srow = classify_strip(uv3) if topo in (17, 41) else None
        plotted.append((max(p[1] for p in p3), p3, uv3, n3, srow))
    for _, p3, q3, n3, srow in sorted(plotted, key=lambda t: t[0]):
        sx = [(p[0]-x0)*sc for p in p3]; sy = [(z1-p[2])*sc for p in p3]
        d = (sy[1]-sy[2])*(sx[0]-sx[2]) + (sx[2]-sx[1])*(sy[0]-sy[2])
        if abs(d) < 1e-9:
            continue
        flat = ROW_COLOR.get(srow, (70, 70, 70)) if rowmap else None
        for pxx in range(max(0, int(min(sx))), min(RW, int(max(sx))+1)):
            for pyy in range(max(0, int(min(sy))), min(RH, int(max(sy))+1)):
                w0 = ((sy[1]-sy[2])*(pxx-sx[2]) + (sx[2]-sx[1])*(pyy-sy[2]))/d
                w1 = ((sy[2]-sy[0])*(pxx-sx[2]) + (sx[0]-sx[2])*(pyy-sy[2]))/d
                w2 = 1-w0-w1
                if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
                    continue
                if flat is not None:
                    rgb = flat
                else:
                    aa, rgb = at_b(w0*q3[0][0]+w1*q3[1][0]+w2*q3[2][0], w0*q3[0][1]+w1*q3[1][1]+w2*q3[2][1])
                    if aa < 24:
                        continue
                nx = sum(w*n3[k][0] for k, w in enumerate((w0, w1, w2)))
                ny = sum(w*n3[k][1] for k, w in enumerate((w0, w1, w2)))
                nz = sum(w*n3[k][2] for k, w in enumerate((w0, w1, w2)))
                nl = math.sqrt(nx*nx+ny*ny+nz*nz) or 1.0
                f = 0.45 + 0.55*max(0.0, (nx*LDIR[0]+ny*LDIR[1]+nz*LDIR[2])/nl)
                tp[pxx, pyy] = tuple(min(255, int(c)) for c in rgb)
                cp[pxx, pyy] = tuple(min(255, int(c*f)) for c in rgb)
    return tex, com


def sheet(panels, cols, cw, ch, path, title=""):
    rows = (len(panels)+cols-1)//cols; pad = 10; lh = 22
    W = cols*(cw+pad)+pad; H = rows*(ch+lh+pad)+pad+(24 if title else 0)
    im = Image.new("RGB", (W, H), (16, 16, 16)); dr = ImageDraw.Draw(im)
    if title:
        dr.text((pad, 6), title, fill=(255, 230, 140))
    for i, (label, panel) in enumerate(panels):
        r, c = divmod(i, cols); x = pad+c*(cw+pad); y = pad+(24 if title else 0)+r*(ch+lh+pad)
        dr.text((x, y), label, fill=(230, 230, 230))
        pw, ph = panel.size; scale = min(cw/pw, ch/ph)
        im.paste(panel.resize((max(1, int(pw*scale)), max(1, int(ph*scale))), Image.NEAREST), (x, y+lh))
    im.save(path); print(f"-> {path}")


def _centroid(cells):
    return (CELL_U * (sum(c[0] for c in cells)/len(cells) + 0.5),
            CELL_U * (sum(c[1] for c in cells)/len(cells) + 0.5))


def render_comparison(host, rp, paint_data):
    atlas, awh, apx = _atlas()
    mint_tris = []
    for blk in host["geom_by_block"]:
        mint_tris += synth_tris(host["geom_by_block"][blk]["bm"], blk)
    # MINT: WIDE frames the whole blob (footprint centroid); MEDIUM/TIGHT frame the ECOTONE (the
    # decoded load-bearing axis) -- centre on the placed dune-side strip cells' centroid
    mint_wide = _centroid(rp["placed_footprint"])
    mint_eco = _centroid(list(rp["placed_dune_rows"]) or rp["placed_footprint"])
    # comp[1] in-situ, same framing on the stock twin
    comp1_wide = _centroid(EYE.COMP1)
    comp1_eco = _centroid([c for c in EYE.COMP1 if c in paint_data["strip_cells"]] or list(EYE.COMP1))
    cb = (int(math.floor(comp1_wide[0]/BLOCK)), int(math.floor(-comp1_wide[1]/BLOCK)))
    stock = []
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            try:
                stock += stock_tris(cb[0]+dx, cb[1]+dy)
            except Exception:  # noqa: BLE001
                pass
    zooms = [("WIDE 200u sc6", 200, 6, mint_wide, comp1_wide),
             ("MEDIUM 56u sc16", 56, 16, mint_eco, comp1_eco),
             ("TIGHT 24u sc32", 24, 32, mint_eco, comp1_eco)]
    for zlabel, win, sc, mctr, cctr in zooms:
        panels = []
        mt, mc = paint(mint_tris, mctr[0], mctr[1], win, sc, awh, apx)
        st, sc_im = paint(stock, cctr[0], cctr[1], win, sc, awh, apx)
        panels.append((f"MINT {zlabel} TEX", mt)); panels.append((f"comp[1] in-situ {zlabel} TEX", st))
        panels.append((f"MINT {zlabel} SHADED", mc)); panels.append((f"comp[1] in-situ {zlabel} SHADED", sc_im))
        if sc == 32:
            _, mr = paint(mint_tris, mctr[0], mctr[1], win, sc, awh, apx, rowmap=True)
            _, sr = paint(stock, cctr[0], cctr[1], win, sc, awh, apx, rowmap=True)
            panels.append((f"MINT {zlabel} ROWMAP", mr)); panels.append((f"comp[1] {zlabel} ROWMAP", sr))
        sheet(panels, 2, 560, 448, OUTD / f"dunes_field_mint_{zlabel.split()[0].lower()}.png",
              title=f"{zlabel}: the verbatim comp[1] stamp (mint) beside comp[1] in-situ -- must read as "
                    "comp[1] relocated. WIDE=whole blob; MEDIUM/TIGHT=the ECOTONE. Stock twin = the eye's ref.")
    return [str(OUTD / f"dunes_field_mint_{z[0].split()[0].lower()}.png") for z in zooms]


# ============================================================================================
# STEP 7 -- deploy (guarded) + Disc4 mirror
# ============================================================================================
def deploy(host, plane):
    built = host["built"]
    game_root = Path(_cfg.find_game_path(None))
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for blk in sorted(built["blocks"]):
        bx, by = blk
        bm = host["geom_by_block"][blk]["bm"]
        # MOD-OVERWRITE gate + backup any pre-existing file
        for part in ("Terrain", "Sea4", *I.HIDDEN_PARTS):
            rel = M.override_relpath(1, bx, by, part=part)
            p = game_root / MOD / rel
            if p.exists():
                dst = BACKUP_DIR / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)
        written.append(M.deploy_override(bm, mod_folder=MOD, part="Terrain"))
        sea = dataclasses.replace(plane, x=bx, y=by, name=f"Block[{bx}][{by}] Sea4")
        written.append(M.deploy_override(sea, mod_folder=MOD, part="Sea4"))
        for part in I.HIDDEN_PARTS:
            written.append(M.deploy_override(M.hidden_block_mesh(name=f"Block[{bx}][{by}] {part}", disc=1, x=bx, y=by),
                                             mod_folder=MOD, part=part))
        written.append(M.deploy_donor_sidecar(I.DEFAULT_DONOR[0], I.DEFAULT_DONOR[1], mod_folder=MOD, disc=1, x=bx, y=by))
    DM.auto_mirror(written, mod_folder=MOD)
    return written


# ============================================================================================
# main
# ============================================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", action="store_true")
    args = ap.parse_args()

    print("=== dunes_field_mint.py -- real-scale comp[1] whole-stamp dunes mint ===\n")
    paint_data = build_comp1_painting()
    print(f"comp[1] painting: footprint={len(paint_data['FOOTPRINT'])} "
          f"(comp1={len(paint_data['COMP1'])} + hole={len(paint_data['HOLE'])} {paint_data['hole_fams']}) "
          f"boundary={len(paint_data['BOUNDARY'])} outer={len(paint_data['OUTER'])} "
          f"dune-strip={len(paint_data['dune_rows'])} desert-strip={len(paint_data['desert_rows'])}")

    print("\n--- resolve host (census-siting-first ladder, strict dilate3 margin) ---")
    host, pl = resolve_host(paint_data)

    # baseline verify on the plain host (pre-retile)
    plane = I._sea_plane(disc=1, game=None)
    base_report = I.verify_landmass(host["built"], sea_plane=plane, land_height=3.2)
    gate("mint acceptance -- verify_landmass on the plain desert host (baseline, pre-retile: "
         "watertight/winding/on-grain/UV-region/holes/coastline/MISS)", base_report["clean"],
         {k: v for k, v in base_report.items() if k not in ("placement", "shape")})
    gate("OPEN-OCEAN TARGET (every touched host block is true open ocean, none excluded)", True,
         f"blocks={host['blocks']}")

    rp = plan_retile(paint_data, pl)
    # snapshot pre-retile (per touched block)
    touched_blocks = {host["all_mains"][c][0] for c in (rp["placed_footprint"] | rp["placed_outer"])
                      if c in host["all_mains"]}
    snapshot = {}
    for blk in touched_blocks:
        bm = host["geom_by_block"][blk]["bm"]
        snapshot[blk] = dict(verts=copy.deepcopy(bm.verts), normals=copy.deepcopy(bm.normals),
                             once_edges=once_edges_from_bm(bm, blk),
                             bm_plain=dataclasses.replace(bm, chan_arrays={k: copy.deepcopy(v) for k, v in bm.chan_arrays.items()}))

    print("\n--- STEP 3: multi-block retile (stamp + hole-fill + verbatim ecotone) ---")
    retile_info = apply_retile(host, rp)

    print("\n--- STEP 4: gate suite ---")
    gate_info = run_gates(host, rp, snapshot, plane)

    print("\n--- STEP 5: the frozen instrument ---")
    verdict = run_judge(paint_data, rp)

    print("\n--- STEP 6: renders (mint vs comp[1] in-situ, 3 frozen zooms) ---")
    renders = render_comparison(host, rp, paint_data)

    n_fail = sum(1 for _, ok, _ in GATES if not ok)
    print(f"\n=== {len(GATES)} gates, {n_fail} FAILED ===")

    deployed = False
    if args.deploy:
        if n_fail:
            sys.exit(f"REFUSING --deploy: {n_fail} gate(s) failed")
        print("\n--- STEP 7: DEPLOY (both discs via auto-mirror) ---")
        written = deploy(host, plane)
        print(f"deployed {len(written)} Disc1 files (+ Disc4 mirror); blocks {host['blocks']}")
        deployed = True

    out = dict(
        mod_folder=MOD, ground=GROUND, host_label=host["label"], center=list(host["center"]),
        radius=host["radius"], seed=host["seed"], blocks=[list(b) for b in host["blocks"]],
        dihedral=pl["k"], origin=[pl["oi"], pl["oj"]], n_placement_candidates=pl["n_candidates"],
        footprint_cells=len(rp["placed_footprint"]), comp1_cells=len(rp["placed_comp1"]),
        hole_cells=len(rp["placed_hole"]), hole_families=paint_data["hole_fams"],
        dune_strip_cells=len(rp["placed_dune_rows"]), desert_strip_cells=len(rp["placed_desert_rows"]),
        dunes_mains_cells=len(rp["dunes_mains"]),
        retile=retile_info, gate_info={k: v for k, v in gate_info.items() if k != "miss"},
        judge=dict(passed=verdict["passed"], gates={g: [v, p] for g, (v, p) in verdict["gates"].items()}),
        n_gates=len(GATES), n_failed=n_fail, deployed=deployed,
        gates=[{"name": n, "ok": ok, "detail": str(d)} for n, ok, d in GATES],
        renders=renders,
    )
    (OUTD / "dunes_field_mint.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"\n-> {OUTD / 'dunes_field_mint.json'}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
