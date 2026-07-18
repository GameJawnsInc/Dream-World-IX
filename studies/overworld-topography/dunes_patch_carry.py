"""THE BIOME-PATCH WINDOW CARRY -- the mixed-biome landmass, rung 1 (SCRUB veins).

The adjacency census: desert is the hub family; scrub fringes it with 958 boundary
edges. THE CARRY LAW's answer to the seam vocabulary: carry a whole real patch
ensemble VERBATIM inside a lattice CELL-SET window whose ring closes in plain desert,
onto a minted desert islet's flat interior. The window machinery (straddle fixpoint +
THE DESERT-RING CLOSURE + the donor-context ring gate) was built for DUNES first and
FALSIFIED there by census: **THE NO-ENCLOSED-DUNES LAW** -- no dunes ensemble in
stock closes in desert alone (cliff-free or cliffs-carried, cap 2000 cells: every
closure chains into brush/grass first), so a dunes patch has NO verbatim window and
waits on the ecotone-strip vocabulary decode. SCRUB converges: 16 desert-ringed scrub
windows exist (9-15 cells, ~(988,-312) on the Outer Continent) -- rung 1 carries one.

  1. WINDOW SCAN: cells touched by the dunes component + 1-cell dilation, grown to a
     straddle-free fixpoint (a tri is IN iff all its bbox cells are in the window);
     gates -- no foreign topos ({41,17,16,19,20} only), the carried once-edge ring on
     lattice corners, axis-aligned 4u segments (the weld contract with the mint)
  2. mint a desert islet at block (8,19), centre (544,-1248) (seed-scanned)
  3. THE CARRY: drop the islet's flat fill in the target cells (gate: flat desert
     mains, exactly 2 tris per cell), translate by a 4u-multiple offset, y-conform by
     ring plane-fit + ring-exact IDW residuals; area/event bits rewritten to the
     islet's own (topo + flags stay donor-verbatim)
  4. gates: BOUNDARY INVARIANCE (the block's once-edge set unchanged by the swap),
     weld audit, the engine placement census (0 MISS)
  5. re-deploy the Terrain override (world-mirror after)

Run from the repo root:  py studies/overworld-topography/dunes_patch_carry.py [--deploy]
"""
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import grassland as G                  # noqa: E402
from ff9mapkit.world import island as I                     # noqa: E402
from ff9mapkit.world import mesh as M                       # noqa: E402
from ff9mapkit.world import placement as P                  # noqa: E402
from ff9mapkit.world import transplant as TR                # noqa: E402
from ff9mapkit import config                                # noqa: E402

DEPLOY = "--deploy" in sys.argv
MOD = "FF9CustomMap-world"
CELL = (8, 19)
CENTER = (544.0, -1248.0)
RADIUS = 26.0
#: the Outer-Continent scrub belt, loaded WHOLE so cross-border patches unify
REGIONS = [[(bx, by) for bx in range(13, 22) for by in range(3, 8)]]
#: the carry layer: the target family + the desert it embeds in. FOREIGN = everything
#: else walkable/structural; 59 (the solid base) and 62 (subsurface) are neither.
TARGET_TOPOS = {4, 5, 6}                                     # scrub
DESERT_TOPOS = {17, 16, 19, 20}
OK_TOPOS = TARGET_TOPOS | DESERT_TOPOS
IGNORE_TOPOS = {59, 62}
MAX_CELLS = 72
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))


def once_edges(tris):
    c = Counter()
    for t in tris:
        ks = [kk(v[0]) for v in t]
        for i in range(3):
            e = frozenset((ks[i], ks[(i + 1) % 3]))
            if len(e) == 2:
                c[e] += 1
    return {e for e, n in c.items() if n == 1}


def bbox_cells(t, step=0.5):
    """4u cells the tri ACTUALLY overlaps, by plan sampling (verts + edges + an interior
    barycentric grid), each sample nudged toward the centroid so edge-on contact along a
    cell line never claims the far cell. A bbox test overclaims badly on the big diagonal
    mural/cliff tris and poisoned every window."""
    (a, b, c) = [v[0] for v in t]
    cx = (a[0] + b[0] + c[0]) / 3.0
    cz = (a[2] + b[2] + c[2]) / 3.0
    pts = []
    for (p, q) in ((a, b), (b, c), (c, a)):
        n = max(1, int(math.hypot(q[0] - p[0], q[2] - p[2]) / step))
        for k in range(n + 1):
            f = k / n
            pts.append((p[0] + f * (q[0] - p[0]), p[2] + f * (q[2] - p[2])))
    n = max(1, int(max(math.hypot(b[0] - a[0], b[2] - a[2]),
                       math.hypot(c[0] - a[0], c[2] - a[2])) / step))
    for i in range(n + 1):
        for j in range(n + 1 - i):
            u, v_, w = i / n, j / n, 1.0 - i / n - j / n
            if w < -1e-9:
                continue
            pts.append((u * a[0] + v_ * b[0] + w * c[0], u * a[2] + v_ * b[2] + w * c[2]))
    cells = set()
    for (px, pz) in pts:
        qx = px + (cx - px) * 1e-5
        qz = pz + (cz - pz) * 1e-5
        cells.add((math.floor(qx / 4.0), math.floor(qz / 4.0)))
    return cells


def window_candidates():
    out = []
    for blocks in REGIONS:
        tris = []
        for (bx, by) in blocks:
            tris += TR.world_tris(bx, by, "terrain")
        (bx, by) = blocks[0]                                 # region label for messages
        topo = [X.decode_id(int(round(t[0][3][0])))["topograph"] for t in tris]
        cells_of = [bbox_cells(t) for t in tris]
        foreign_cells = set()
        for ti, tp in enumerate(topo):
            if tp not in OK_TOPOS and tp not in IGNORE_TOPOS:
                foreign_cells |= cells_of[ti]
        surf = [ti for ti, tp in enumerate(topo) if tp in OK_TOPOS]
        # seed a window from every pure-dunes cell + 1-ring, grow to the straddle
        # fixpoint (a window's boundary settles on clean mains-only cell lines);
        # dedupe terminal windows
        target_cells = set()
        for ti, tp in enumerate(topo):
            if tp in TARGET_TOPOS:
                target_cells |= cells_of[ti]
        def fixpoint(W):
            for _ in range(48):                               # straddle fixpoint (surface only)
                grow = set()
                for ti in surf:
                    cs = cells_of[ti]
                    if not cs or cs <= W or not (cs & W):
                        continue
                    grow |= cs - W
                if not grow:
                    return W
                if (grow & foreign_cells) or len(W | grow) > MAX_CELLS:
                    return None
                W = W | grow
            return None

        # tri-level edge ownership (for the desert-ring closure + the ctx gate)
        eowner_all = defaultdict(list)
        for ti in surf:
            ks = [kk(v[0]) for v in tris[ti]]
            for i in range(3):
                e = frozenset((ks[i], ks[(i + 1) % 3]))
                if len(e) == 2:
                    eowner_all[e].append(ti)

        def desert_ring_closure(W):
            """Absorb neighbouring pockets through any ring edge whose donor outside
            is NOT desert-family, until the ring is desert-ringed (or refuses)."""
            for _ in range(24):
                W = fixpoint(W)
                if W is None or (W & foreign_cells) or len(W) > MAX_CELLS:
                    return None
                inside = {ti for ti in surf if cells_of[ti] and cells_of[ti] <= W}
                add = set()
                for t2 in inside:
                    ks = [kk(v[0]) for v in tris[t2]]
                    for i in range(3):
                        e = frozenset((ks[i], ks[(i + 1) % 3]))
                        if len(e) != 2:
                            continue
                        for to in eowner_all[e]:
                            if to not in inside and topo[to] not in DESERT_TOPOS:
                                add |= cells_of[to] - W
                if not add:
                    return W
                if (add & foreign_cells) or len(W | add) > MAX_CELLS:
                    return None
                W = W | add
            return None

        seen_windows = set()
        for seed_cell in sorted(target_cells):
            W = desert_ring_closure({(seed_cell[0] + di, seed_cell[1] + dj)
                                     for di in (-1, 0, 1) for dj in (-1, 0, 1)})
            if W is None or (W & foreign_cells) or len(W) > MAX_CELLS:
                continue
            wkey = frozenset(W)
            if wkey in seen_windows:
                continue
            seen_windows.add(wkey)
            inside = [ti for ti in surf if cells_of[ti] and cells_of[ti] <= W]
            tl = [ti for ti in inside if topo[ti] in TARGET_TOPOS]
            if not tl:
                continue
            tps = {topo[ti] for ti in inside}
            if not tps <= OK_TOPOS:
                print(f"   reject {bx},{by} comp({len(tl)}t): foreign topos {sorted(tps - OK_TOPOS)}")
                continue
            carried = [tris[ti] for ti in inside]
            ring = once_edges(carried)
            ring_ok = True
            for e in ring:
                (a, b) = sorted(e)
                axis_seg = (abs(a[0] - b[0]) < 1e-6) != (abs(a[2] - b[2]) < 1e-6)
                lat = all(abs(v / 4 - round(v / 4)) < 2.5e-4 for p in (a, b) for v in (p[0], p[2]))
                if not (axis_seg and lat):
                    ring_ok = False
                    break
            if not ring_ok:
                print(f"   reject {bx},{by} comp({len(tl)}t): non-lattice window ring")
                continue
            # THE DONOR-CONTEXT RING GATE: the deployed outside of every ring edge is
            # the mint's desert mains -- lawful iff the DONOR's own tri on the other
            # side is DESERT-FAMILY too (the pairing then existed in the donor modulo
            # a within-family texel swap, which the anti-tiling system makes free;
            # the seam anatomy attests strip|desert-mains directly, 26/163). A ring
            # edge whose donor outside is DUNES would deploy a raw dunes|mains seam
            # stock never shows (mains-both 0/190) -- refused.
            eowner = defaultdict(list)
            for ti in surf:
                ks = [kk(v[0]) for v in tris[ti]]
                for i in range(3):
                    e = frozenset((ks[i], ks[(i + 1) % 3]))
                    if len(e) == 2:
                        eowner[e].append(ti)
            inside_set = set(inside)
            bad_ctx = Counter()
            for e in ring:
                others = [ti for ti in eowner.get(e, []) if ti not in inside_set]
                if not others:
                    bad_ctx["no-owner"] += 1
                for ti in others:
                    if topo[ti] not in DESERT_TOPOS:
                        bad_ctx[topo[ti]] += 1
            if bad_ctx:
                print(f"   reject {bx},{by} comp({len(tl)}t): ring context "
                      f"{dict(bad_ctx)} of {len(ring)} edges")
                continue
            # every window cell must be covered (2 tris per cell in plain fields; the
            # census re-checks after integration)
            cover = Counter()
            for ti in inside:
                for c in cells_of[ti]:
                    cover[c] += 1
            if any(cover.get(c, 0) == 0 for c in W):
                print(f"   reject {bx},{by} comp({len(tl)}t): uncovered window cell")
                continue
            ndun = sum(1 for ti in inside if topo[ti] in TARGET_TOPOS)
            xs = [4 * i for (i, j) in W] + [4 * i + 4 for (i, j) in W]
            zs = [4 * j for (i, j) in W] + [4 * j + 4 for (i, j) in W]
            out.append(dict(block=(bx, by), cells=W, ncells=len(W),
                            w=max(xs) - min(xs), h=max(zs) - min(zs),
                            cxz=((min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2),
                            tris=carried, ring=ring, ndunes=ndun))
    return sorted(out, key=lambda c: -c["ndunes"])


cands = window_candidates()
print(f"window candidates ({len(cands)}):")
for c in cands:
    print(f"   {c['block']}: {c['ncells']} cells  {c['w']:.0f}x{c['h']:.0f}u  "
          f"{len(c['tris'])} tris ({c['ndunes']} dunes)")
if not cands:
    sys.exit("no lawful window")

# ---- 2. mint the islet (seed scan: the mint's gates are seed-sensitive) -------------------------
summary = None
SEED = None
for seed in [float(s) for s in range(1, 40)]:
    try:
        summary = I.landmass(MOD, center=CENTER, base_radius=RADIUS, seed=seed,
                             ground="desert", flat=True, dry_run=not DEPLOY)
        SEED = seed
        break
    except ValueError:
        continue
if summary is None:
    sys.exit("no clean islet seed at this radius")
print(f"islet: {'deployed' if DEPLOY else 'dry-run built'} at {CENTER} r{RADIUS} seed {SEED}")

game_root = config.find_game_path(None)
tpath = game_root / MOD / M.override_relpath(1, CELL[0], CELL[1], part="Terrain")
if DEPLOY:
    bm0 = M.blockmesh_from_ff9mesh(tpath, disc=1, x=CELL[0], y=CELL[1], part="terrain")
else:
    bm0 = I.build_landmass(center=CENTER, base_radius=RADIUS, seed=SEED, ground="desert",
                           stamps=None)["blocks"][CELL]
isl = []
for tri in np.asarray(bm0.flat_index, dtype=np.int64).reshape(-1, 3):
    isl.append([((bm0.verts[j][0] + 64.0 * CELL[0], bm0.verts[j][1],
                  bm0.verts[j][2] - 64.0 * CELL[1]),
                 tuple(bm0.normals[j]), tuple(bm0.uvs[j]), tuple(bm0.tangents[j]))
                for j in tri])

# ---- 3. the carry ------------------------------------------------------------------------------
m = G.FAM_REGION["main"]
gd = G.GROUNDS["desert"]
DRECT = (m[0] + gd["mains_du"], m[1] + gd["mains_dv"],
         m[2] + gd["mains_du"], m[3] + gd["mains_dv"])
chosen = None
for cand in cands:
    dx = 4.0 * round((CENTER[0] - cand["cxz"][0]) / 4.0)
    dz = 4.0 * round((CENTER[1] - cand["cxz"][1]) / 4.0)
    tcells = {(i + int(dx // 4), j + int(dz // 4)) for (i, j) in cand["cells"]}
    drop, keep = [], []
    for t in isl:
        cx = sum(v[0][0] for v in t) / 3
        cz = sum(v[0][2] for v in t) / 3
        tp = X.decode_id(int(round(t[0][3][0])))["topograph"]
        if tp == 17 and (math.floor(cx / 4.0), math.floor(cz / 4.0)) in tcells:
            drop.append(t)                                   # the flat fill only
        else:
            keep.append(t)                                   # walls, base, everything else
    ys = [v[0][1] for t in drop for v in t]
    flat = bool(drop) and max(ys) - min(ys) < 1e-6
    mains = all(DRECT[0] - 0.006 <= v[2][0] <= DRECT[2] + 0.006
                and DRECT[1] - 0.006 <= v[2][1] <= DRECT[3] + 0.006
                for t in drop for v in t)
    if flat and mains and len(drop) == 2 * cand["ncells"]:
        chosen = (cand, dx, dz, drop, keep)
        break
    print(f"   candidate {cand['block']} does not sit in the flat interior "
          f"(flat={flat} mains={mains} drop={len(drop)}/{2 * cand['ncells']}) -- next")
if chosen is None:
    sys.exit("no candidate fits the islet interior -- grow RADIUS")
(cand, dx, dz, drop, keep) = chosen
H = drop[0][0][0][1]
print(f"CHOSEN: donor {cand['block']} {cand['ncells']} cells -> offset ({dx:+g},{dz:+g}), H={H}")

# y-conform: plane over the window RING verts, residuals IDW-blended (ring-exact)
ring_verts = {}
for e in cand["ring"]:
    for p in e:
        ring_verts[(p[0], p[2])] = p[1]
A = np.array([[px, pz, 1.0] for (px, pz) in ring_verts])
Y = np.array(list(ring_verts.values()))
(pa, pb, pc), *_ = np.linalg.lstsq(A, Y, rcond=None)
resid = {k: y - (pa * k[0] + pb * k[1] + pc) for k, y in ring_verts.items()}
print(f"conform: ring plane slope {math.degrees(math.atan(math.hypot(pa, pb))):.2f} deg, "
      f"residuals max {max(abs(r) for r in resid.values()):.3f}")


def conform_y(px, pz, py):
    base = py - (pa * px + pb * pz + pc) + H
    num = den = 0.0
    for (qx, qz), r in resid.items():
        d2 = (px - qx) ** 2 + (pz - qz) ** 2
        if d2 < 1e-12:
            return base - r
        w = 1.0 / d2
        num += w * r
        den += w
    return base - num / den


ev_ar = X.decode_id(int(round(drop[0][0][3][0])))
rkeys = set(ring_verts)
carried = []
for t in cand["tris"]:
    nt = []
    for (p, nr, uv, tan) in t:
        py = conform_y(p[0], p[2], p[1])
        onb = (round(p[0], 3), round(p[2], 3)) in rkeys
        d = X.decode_id(int(round(tan[0])))
        idall = X.encode_id(ev_ar["event"], ev_ar["area"], d["topograph"], d["flags"])
        nt.append(((p[0] + dx, H if onb else py, p[2] + dz),
                   nr, uv, (float(idall),) + tuple(tan[1:])))
    carried.append(nt)

new = keep + carried


def to_local(tris):
    """WORLD -> block-LOCAL: _soup_block_mesh stores its input verbatim as the block's
    local frame (docstring: 'triangles in the block-LOCAL frame'). isl/new were built in
    WORLD coords (the block offset added on read), so they MUST be un-offset here -- else
    the override deploys at local (518,-1248) and the engine draws the island 512E/1216
    off in open ocean (the 'clobbered' report, 2026-07-17). Inverse of the isl read."""
    return [[((p[0] - 64.0 * CELL[0], p[1], p[2] + 64.0 * CELL[1]), n, u, t)
             for (p, n, u, t) in tri] for tri in tris]


# ---- 4. gates ----------------------------------------------------------------------------------
inv = once_edges(isl) == once_edges(new)
print(f"GATE boundary-invariance: {'ok' if inv else 'FAIL'}")
new_l = to_local(new)
nbm = TR._soup_block_mesh(f"Block[{CELL[0]}][{CELL[1]}] Terrain", CELL, new_l, disc=1, lod="0_1")
pairs = M.weld_audit([nbm])
print(f"GATE weld-audit: {len(pairs)} pairs -> {'ok' if not pairs else 'FAIL'}")
# FRAME GATE: a block override's local verts MUST sit in the block frame (every real
# block does). Catches a world-vs-local frame error that the differential census masks.
lx = [p[0] for tri in new_l for (p, *_ ) in tri]
lz = [p[2] for tri in new_l for (p, *_ ) in tri]
frame_ok = -0.06 <= min(lx) and max(lx) <= 64.06 and -64.06 <= min(lz) and max(lz) <= 0.06
print(f"GATE frame-bounds: local x[{min(lx):.1f},{max(lx):.1f}] z[{min(lz):.1f},{max(lz):.1f}]"
      f" -> {'ok' if frame_ok else 'FAIL (mesh outside the block frame)'}")
sea = []
if DEPLOY:
    for part in ("Sea4",):
        pp = game_root / MOD / M.override_relpath(1, CELL[0], CELL[1], part=part)
        if pp.is_file():
            sea.append((part, M.blockmesh_from_ff9mesh(pp, disc=1, x=CELL[0], y=CELL[1],
                                                       part=part.lower())))
# DIFFERENTIAL census: the swap must not change the miss set (without the Sea4 mesh a
# dry-run "misses" every open-water sample -- the plain islet is the honest baseline)
obm = TR._soup_block_mesh(f"Block[{CELL[0]}][{CELL[1]}] Terrain", CELL, to_local(isl),
                          disc=1, lod="0_1")
cen0 = P.census([("Terrain", obm)] + sea, samples=24)
cen = P.census([("Terrain", nbm)] + sea, samples=24)
cen_ok = set(map(tuple, cen["miss"])) == set(map(tuple, cen0["miss"]))
print(f"GATE census: miss {len(cen['miss'])} vs plain {len(cen0['miss'])} -> "
      f"{'ok' if cen_ok else 'FAIL'}")
tps = Counter(X.decode_id(int(round(t[0][3][0])))["topograph"] for t in carried)
ys = [v[0][1] for t in carried for v in t]
print(f"carried topos: {dict(tps)}; y-range [{min(ys):.2f},{max(ys):.2f}] (H={H})")
if not (inv and not pairs and cen_ok and frame_ok):
    sys.exit("gates FAILED -- not deploying the patch")

# ---- 5. deploy ---------------------------------------------------------------------------------
if DEPLOY:
    outp = M.deploy_override(nbm, mod_folder=MOD, part="Terrain")
    print(f"deployed the patched Terrain -> {outp}")
    print(f"teleport {CENTER}; the REAL patch for A/B: block {cand['block']} centre "
          f"({cand['cxz'][0]:.0f},{cand['cxz'][1]:.0f}). Run world-mirror + world re-entry.")
else:
    print("dry run complete -- re-run with --deploy")
