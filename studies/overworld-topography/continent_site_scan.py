"""ANGLE B -- THE NEW CONTINENT: site the largest ONE-CALL multi-lobe landmass the free map allows.

WHY ONE CALL (the design-critical fact this script exists to quantify):
`island.landmass()` writes a per-block Terrain/Sea override and its OPEN-OCEAN TARGET LAW only tests
REAL stock blocks (`_real_block_parts`). A SECOND overlapping mint would silently CLOBBER the first
island's block files, with no weld across the shared block. So a coherent continent = exactly ONE
`world-island` invocation, and its size is bounded by (base_radius, lobes, seed) -- NOT by the
max-inscribed-disc number the canvas census reports (multi_blob_outline reaches ~1.2-1.45x
base_radius on its long axis).

multi_blob_outline's radii are EXACTLY linear in base_radius (verified r(2R)/r(R) == 2.0), so unit
profiles are precomputed once per (lobes, seed) and scaled.

Read-only. Writes JSON to out/world-design/.
"""
from __future__ import annotations
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "ff9mapkit"))
from ff9mapkit.world import mesh as M  # noqa: E402

OUT = os.path.join(HERE, "out", "world-design")
os.makedirs(OUT, exist_ok=True)
BLOCK = 64.0
NX, NY = 24, 20
WORLD_W = NX * BLOCK

fb = json.load(open(os.path.join(OUT, "_forbidden_blocks.json")))
FORBIDDEN = set()
for key in ("stock_occ", "live", "named"):
    for bx, by in fb[key]:
        FORBIDDEN.add((int(bx), int(by)))
FREE = {(x, y) for x in range(NX) for y in range(NY)} - FORBIDDEN
wrapx = lambda x: x % NX


def components(cells):
    seen, comps = set(), []
    for c in sorted(cells):
        if c in seen:
            continue
        stack, comp = [c], []
        seen.add(c)
        while stack:
            x, y = stack.pop()
            comp.append((x, y))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (wrapx(x + dx), y + dy)
                if 0 <= n[1] < NY and n in cells and n not in seen:
                    seen.add(n)
                    stack.append(n)
        comps.append(sorted(comp))
    return sorted(comps, key=len, reverse=True)


COMPS = components(FREE)

# ------------------------------------------------------------------ unit profiles
NSEED = 48
PROF = {}
for lobes in (1, 2, 3):
    for s in range(NSEED):
        if lobes >= 2:
            _, radii = M.multi_blob_outline(0.0, 0.0, lobes=lobes, base_radius=1.0, seed=float(s))
        else:
            _, radii = M.blob_outline(0.0, 0.0, base_radius=1.0, seed=float(s), n=160,
                                      n_corners=3, corner_strength=0.26)
        PROF[(lobes, s)] = (radii, max(radii), min(radii))


def dx_wrap(a, b):
    d = abs(a - b) % WORLD_W
    return min(d, WORLD_W - d)


def pt_block_dist(cx, cz, bx, by):
    """distance from world point to the block's rectangle (x wraps)."""
    x0, x1 = bx * BLOCK, bx * BLOCK + BLOCK
    z1, z0 = -(by * BLOCK), -(by * BLOCK + BLOCK)   # z0 < z1
    # x term with wrap
    if dx_wrap(cx, x0) + dx_wrap(cx, x1) <= BLOCK + 1e-9:
        ddx = 0.0
    else:
        ddx = min(dx_wrap(cx, x0), dx_wrap(cx, x1))
    ddz = 0.0 if z0 <= cz <= z1 else min(abs(cz - z0), abs(cz - z1))
    return math.hypot(ddx, ddz)


FORB = sorted(FORBIDDEN)


def r_at(radii, th):
    n = len(radii)
    f = (th % (2 * math.pi)) / (2 * math.pi) * n
    i = int(f) % n
    t = f - int(f)
    return radii[i] * (1 - t) + radii[(i + 1) % n] * t


def block_hit(radii, R, cx, cz, bx, by, samp=9):
    for i in range(samp):
        wx = bx * BLOCK + (i + 0.5) * BLOCK / samp
        ddx = wx - cx
        if ddx > WORLD_W / 2:
            ddx -= WORLD_W
        elif ddx < -WORLD_W / 2:
            ddx += WORLD_W
        for j in range(samp):
            wz = -(by * BLOCK + (j + 0.5) * BLOCK / samp)
            ddz = wz - cz
            d = math.hypot(ddx, ddz)
            if d <= R * r_at(radii, math.atan2(ddz, ddx)):
                return True
    return False


def touched(radii, R, cx, cz, samp=9):
    rmax = R * max(radii)
    out = set()
    b0x = int(math.floor((cx - rmax) / BLOCK)) - 1
    b1x = int(math.ceil((cx + rmax) / BLOCK)) + 1
    b0y = int(math.floor((-cz - rmax) / BLOCK)) - 1
    b1y = int(math.ceil((-cz + rmax) / BLOCK)) + 1
    for by in range(b0y, b1y + 1):
        for bx in range(b0x, b1x + 1):
            if block_hit(radii, R, cx, cz, bx, by, samp):
                out.add((wrapx(bx), by))
    return out


def area_of(radii, R):
    n = len(radii)
    k = math.sin(2 * math.pi / n)
    return 0.5 * R * R * sum(radii[i] * radii[(i + 1) % n] * k for i in range(n))


def centres(lattice=32.0):
    out = []
    n = int(BLOCK / lattice)
    for (bx, by) in sorted(FREE):
        for i in range(n):
            for j in range(n):
                cx = bx * BLOCK + (i + 0.5) * lattice
                cz = -(by * BLOCK + (j + 0.5) * lattice)
                near = sorted(((pt_block_dist(cx, cz, fx, fy), (fx, fy)) for (fx, fy) in FORB))
                out.append((cx, cz, near[0][0], [b for _, b in near[:40]]))
    return out


CENTRES = centres()
print(f"{len(CENTRES)} candidate centres; best clearance = {max(c[2] for c in CENTRES):.1f}u")


def evaluate(cx, cz, clearance, nearlist, R, lobes, seed):
    radii, rmx, rmn = PROF[(lobes, seed)]
    rmax = R * rmx
    if rmax > clearance:
        for (bx, by) in nearlist:
            if pt_block_dist(cx, cz, bx, by) > rmax:
                break
            if block_hit(radii, R, cx, cz, bx, by):
                return None
        # out-of-lattice safety: south/north world edge
    blocks = touched(radii, R, cx, cz)
    if blocks & FORBIDDEN or any(b[1] < 0 or b[1] >= NY for b in blocks):
        return None
    return {"center": [cx, cz], "radius": R, "lobes": lobes, "seed": seed,
            "n_blocks": len(blocks), "blocks": sorted(blocks),
            "area_u2": round(area_of(radii, R)),
            "rmin_u": round(R * rmn, 1), "rmax_u": round(rmax, 1)}


def detail(h):
    radii, _, _ = PROF[(h["lobes"], h["seed"])]
    R, (cx, cz) = h["radius"], h["center"]
    n = len(radii)
    pts = [(cx + R * radii[i] * math.cos(2 * math.pi * i / n),
            cz + R * radii[i] * math.sin(2 * math.pi * i / n)) for i in range(n)]
    st = M.outline_shape_stats(pts)
    h["span_x"] = round(max(p[0] for p in pts) - min(p[0] for p in pts), 1)
    h["span_z"] = round(max(p[1] for p in pts) - min(p[1] for p in pts), 1)
    h["shape"] = {k: (round(v, 2) if isinstance(v, (int, float)) else v) for k, v in st.items()}
    return h


if __name__ == "__main__":
    rep = {"free_blocks": len(FREE),
           "free_components": [{"n": len(c),
                                "bbox_x": [min(p[0] for p in c), max(p[0] for p in c)],
                                "bbox_y": [min(p[1] for p in c), max(p[1] for p in c)],
                                "cells": c} for c in COMPS[:6]],
           "sweep": {}}
    print("free components (n, bx0..bx1, by0..by1):")
    for c in COMPS[:6]:
        print("  ", len(c), min(p[0] for p in c), max(p[0] for p in c),
              min(p[1] for p in c), max(p[1] for p in c))
    for R in (84.0, 96.0, 108.0, 120.0, 132.0, 144.0):
        for lobes in (1, 2, 3):
            hits = []
            for (cx, cz, clr, near) in CENTRES:
                for s in range(NSEED):
                    r = evaluate(cx, cz, clr, near, R, lobes, s)
                    if r:
                        hits.append(r)
            hits.sort(key=lambda h: -h["area_u2"])
            top = [detail(h) for h in hits[:5]]
            rep["sweep"][f"r{int(R)}_l{lobes}"] = {"n_legal": len(hits), "top": top}
            msg = f"R={R:5.0f} lobes={lobes}: {len(hits):6d} legal"
            if top:
                h = top[0]
                msg += (f"  BEST area={h['area_u2']}u2 blocks={h['n_blocks']} "
                        f"span={h['span_x']}x{h['span_z']} c={h['center']} seed={h['seed']}")
            print(msg, flush=True)
    with open(os.path.join(OUT, "continent_sites.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)
    print("wrote", os.path.join(OUT, "continent_sites.json"))
