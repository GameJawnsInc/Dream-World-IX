"""THE MISSING VIEW: a grazing-angle PERSPECTIVE render of the deployed dunes mint seam AND
stock comp[1]'s seam in situ, through the real Moguri atlas with per-corner UVs honored
(perspective-correct). SAME camera for both. Calibrated on stock first.

This is the instrument the whole dunes arc never had: every prior eye rendered TOP-DOWN
orthographic at fixed zooms. The game camera is a low-pitch perspective. Reads the DEPLOYED
mint bytes (mod folder) + stock bundles; writes ONLY render PNGs into the study out/ dir.

Run:  py <scratchpad>/grazing_eye.py
"""
from __future__ import annotations
import math
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path("C:/gd/Dream-World-IX/.claude/worktrees/overworld-work-continue-0d139c")
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit import config as _cfg                    # noqa: E402
from ff9mapkit.world import extract as X                # noqa: E402
from ff9mapkit.world import mesh as MESH                # noqa: E402

BLOCK = 64.0
CELL = 4.0
OUTD = REPO / "studies" / "overworld-topography" / "out"
OUTD.mkdir(exist_ok=True)
MOD = "FF9CustomMap-world"
NEI4 = ((1, 0), (-1, 0), (0, 1), (0, -1))

TOPO_FAM = {17: "desert", 16: "desert", 19: "desert", 20: "desert", 41: "dunes", 58: "rock", 59: "hole"}

GP = Path(_cfg.find_game_path(None))
MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / "textures" / "res(1_24)_terrain.png"
ATLAS = Image.open(MOG).convert("RGBA")
AW, AH = ATLAS.size
APX = ATLAS.load()
print(f"atlas {AW}x{AH}")


def at_b(u_, v_):
    fx = (u_ % 1.0) * AW - 0.5
    fy = (1.0 - v_ % 1.0) * AH - 0.5
    x0, y0 = int(math.floor(fx)), int(math.floor(fy))
    tx, ty = fx - x0, fy - y0
    acc = [0.0, 0.0, 0.0]
    aa = 0.0
    for (dx, dy, wg) in ((0, 0, (1-tx)*(1-ty)), (1, 0, tx*(1-ty)), (0, 1, (1-tx)*ty), (1, 1, tx*ty)):
        r, g, b, a = APX[min(max(x0+dx, 0), AW-1), min(max(y0+dy, 0), AH-1)]
        acc[0] += r*wg; acc[1] += g*wg; acc[2] += b*wg; aa += a*wg
    return aa, (acc[0], acc[1], acc[2])


def tris_of(bm, bx, by):
    """Yield (p3 world, uv3, n3, topo) for a block mesh."""
    V, N, U, TAN = bm.verts, bm.normals, bm.uvs, bm.tangents
    out = []
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        p3 = [(V[j][0] + BLOCK*bx, V[j][1], V[j][2] - BLOCK*by) for j in tri]
        uv3 = [(float(U[j][0]), float(U[j][1])) for j in tri]
        n3 = [(float(N[j][0]), float(N[j][1]), float(N[j][2])) for j in tri]
        topo = X.decode_id(int(round(TAN[tri[0]][0])))["topograph"]
        out.append((p3, uv3, n3, topo))
    return out


def load_stock(blocks):
    out = []
    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except (ValueError, FileNotFoundError):
            continue
        out += tris_of(bm, bx, by)
    return out


def load_mint(blocks):
    out = []
    for (bx, by) in blocks:
        p = GP / MOD / MESH.override_relpath(1, bx, by, part="Terrain")
        if not p.exists():
            continue
        bm = MESH.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        out += tris_of(bm, bx, by)
    return out


def cells_by_fam(tris):
    """cell -> dominant family, from tri centroids."""
    fam_ct = defaultdict(Counter)
    for (p3, uv3, n3, topo) in tris:
        cx = sum(p[0] for p in p3) / 3.0
        cz = sum(p[2] for p in p3) / 3.0
        cell = (math.floor(cx / CELL), math.floor(cz / CELL))
        fam_ct[cell][TOPO_FAM.get(topo, f"t{topo}")] += 1
    return {c: ct.most_common(1)[0][0] for c, ct in fam_ct.items()}


def dunes_component(cellfam, want=130):
    dcells = {c for c, f in cellfam.items() if f == "dunes"}
    seen, comps = set(), []
    for s in dcells:
        if s in seen:
            continue
        comp, q = set(), deque([s]); seen.add(s)
        while q:
            c = q.popleft(); comp.add(c)
            for di, dj in NEI4:
                n = (c[0]+di, c[1]+dj)
                if n in dcells and n not in seen:
                    seen.add(n); q.append(n)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    # for the mint the hole is filled so comp is 144; for stock it's 130. take the biggest.
    return comps[0]


# ============================================================================================
# BOUNDARY GEOMETRY MEASURE -- is the dune/desert interface a fixed 4u staircase or sub-cell?
# ============================================================================================
def boundary_geometry(tris, footprint):
    """For every tri edge that separates a dunes tri from a non-dunes tri (the visible seam),
    collect the edge endpoints' fractional position within the 4u lattice. If the seam runs
    ONLY along 4u cell lines, all endpoints sit at integer multiples of 4u (frac ~0). Sub-cell
    conforming geometry (stock) puts endpoints at fractional positions."""
    # map each tri to dunes/not by centroid cell membership
    fintset = set(footprint)

    def is_dune(p3):
        cx = sum(p[0] for p in p3)/3.0; cz = sum(p[2] for p in p3)/3.0
        return (math.floor(cx/CELL), math.floor(cz/CELL)) in fintset
    # build edge -> list of (is_dune)
    edges = defaultdict(list)
    for (p3, uv3, n3, topo) in tris:
        d = is_dune(p3)
        ks = [tuple(round(v, 3) for v in p) for p in p3]
        for i in range(3):
            e = frozenset((ks[i], ks[(i+1) % 3]))
            if len(e) == 2:
                edges[e].append(d)
    seam_pts = []
    for e, ds in edges.items():
        if len(set(ds)) == 2 or (len(ds) == 1 and ds[0]):  # dune|non-dune boundary edge
            for (px, py, pz) in e:
                fx = (px / CELL); fz = (pz / CELL)
                rx = abs(fx - round(fx)); rz = abs(fz - round(fz))
                seam_pts.append(min(rx, rz))  # distance to nearest 4u grid line (in cells)
    if not seam_pts:
        return None
    arr = np.array(seam_pts)
    return dict(n=len(arr), frac_on_grid=float((arr < 0.05).mean()),
                mean_offcell=float(arr.mean()), p90_offcell=float(np.percentile(arr, 90)))


# ============================================================================================
# PERSPECTIVE GRAZING RENDER
# ============================================================================================
def render_grazing(tris, cam_pos, look_at, fov_y_deg, W, H, shade=True):
    up_world = (0.0, 1.0, 0.0)
    fwd = np.array(look_at, float) - np.array(cam_pos, float)
    fwd = fwd / (np.linalg.norm(fwd) or 1.0)
    right = np.cross(fwd, up_world); right = right / (np.linalg.norm(right) or 1.0)
    up = np.cross(right, fwd)
    cam = np.array(cam_pos, float)
    f = (H / 2.0) / math.tan(math.radians(fov_y_deg) / 2.0)
    LDIR = np.array([-0.45, 0.72, 0.45]); LDIR = LDIR / np.linalg.norm(LDIR)

    img = Image.new("RGB", (W, H), (150, 176, 214))
    px = img.load()
    zbuf = [[1e30] * W for _ in range(H)]

    def project(p):
        rel = np.array(p, float) - cam
        vx = float(np.dot(rel, right)); vy = float(np.dot(rel, up)); vz = float(np.dot(rel, fwd))
        return vx, vy, vz

    order = 0
    for (p3, uv3, n3, topo) in tris:
        pv = [project(p) for p in p3]
        if any(v[2] < 0.6 for v in pv):   # behind / too near the eye
            continue
        sx = [W/2.0 + f*v[0]/v[2] for v in pv]
        sy = [H/2.0 - f*v[1]/v[2] for v in pv]
        invw = [1.0/v[2] for v in pv]
        # perspective-correct varyings: uv*invw, n*invw
        uvw = [(uv3[k][0]*invw[k], uv3[k][1]*invw[k]) for k in range(3)]
        nw = [(n3[k][0]*invw[k], n3[k][1]*invw[k], n3[k][2]*invw[k]) for k in range(3)]
        minx, maxx = int(max(0, math.floor(min(sx)))), int(min(W-1, math.ceil(max(sx))))
        miny, maxy = int(max(0, math.floor(min(sy)))), int(min(H-1, math.ceil(max(sy))))
        if minx > maxx or miny > maxy:
            continue
        d = (sy[1]-sy[2])*(sx[0]-sx[2]) + (sx[2]-sx[1])*(sy[0]-sy[2])
        if abs(d) < 1e-9:
            continue
        order += 1
        for yy in range(miny, maxy+1):
            for xx in range(minx, maxx+1):
                w0 = ((sy[1]-sy[2])*(xx-sx[2]) + (sx[2]-sx[1])*(yy-sy[2]))/d
                w1 = ((sy[2]-sy[0])*(xx-sx[2]) + (sx[0]-sx[2])*(yy-sy[2]))/d
                w2 = 1.0 - w0 - w1
                if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6:
                    continue
                iw = w0*invw[0] + w1*invw[1] + w2*invw[2]
                depth = 1.0/iw
                if depth >= zbuf[yy][xx]:
                    continue
                u = (w0*uvw[0][0] + w1*uvw[1][0] + w2*uvw[2][0]) / iw
                v = (w0*uvw[0][1] + w1*uvw[1][1] + w2*uvw[2][1]) / iw
                aa, rgb = at_b(u, v)
                if aa < 24:
                    continue
                if shade:
                    nx = (w0*nw[0][0] + w1*nw[1][0] + w2*nw[2][0]) / iw
                    ny = (w0*nw[0][1] + w1*nw[1][1] + w2*nw[2][1]) / iw
                    nz = (w0*nw[0][2] + w1*nw[1][2] + w2*nw[2][2]) / iw
                    nl = math.sqrt(nx*nx+ny*ny+nz*nz) or 1.0
                    sh = 0.5 + 0.5*max(0.0, (nx*LDIR[0]+ny*LDIR[1]+nz*LDIR[2])/nl)
                else:
                    sh = 1.0
                zbuf[yy][xx] = depth
                px[xx, yy] = tuple(min(255, int(c*sh)) for c in rgb)
    return img


def centroid_world(cells):
    xs = [c[0] for c in cells]; zs = [c[1] for c in cells]
    return (CELL*(sum(xs)/len(xs)+0.5), CELL*(sum(zs)/len(zs)+0.5))


def ground_y_at(tris, wx, wz):
    best, by = None, 0.0
    for (p3, uv3, n3, topo) in tris:
        cx = sum(p[0] for p in p3)/3.0; cz = sum(p[2] for p in p3)/3.0
        d = (cx-wx)**2 + (cz-wz)**2
        if best is None or d < best:
            best = d; by = sum(p[1] for p in p3)/3.0
    return by


def best_desert_azimuth(footprint, cellfam):
    """Compass direction (unit (ax,az)) with the most desert cells in a 3-deep band just beyond
    the footprint boundary -- the side to look OUT across the dune/desert ecotone."""
    dirs = {(1, 0): 0, (-1, 0): 0, (0, 1): 0, (0, -1): 0}
    fp = set(footprint)
    for (di, dj) in dirs:
        cnt = 0
        for c in fp:
            for k in (1, 2, 3):
                n = (c[0]+di*k, c[1]+dj*k)
                if n not in fp and cellfam.get(n) == "desert":
                    cnt += 1
        dirs[(di, dj)] = cnt
    best = max(dirs, key=dirs.get)
    return (float(best[0]), float(best[1])), dirs


def make_camera(footprint, tris, azimuth, pitch_deg, dh=44.0):
    """Stand on the dunes interior, look OUTWARD along `azimuth` across the ecotone to the desert
    beyond, at grazing `pitch_deg`. Congruent footprints + identical params => identical framing.
    Camera lifted above the local plateau so relief on the interior side does not occlude."""
    Cf = centroid_world(footprint)
    xs = [c[0] for c in footprint]; zs = [c[1] for c in footprint]
    span = CELL * max(max(xs)-min(xs), max(zs)-min(zs))
    ax, az = azimuth
    # look-at = the far boundary on the desert side
    T = (Cf[0] + ax*span*0.5, 0.0, Cf[1] + az*span*0.5)
    gy_T = ground_y_at(tris, T[0], T[2])
    T = (T[0], gy_T, T[2])
    # camera = dh inside from the boundary (on the dunes), lifted for grazing pitch
    cx, cz = T[0] - ax*dh, T[2] - az*dh
    gy_cam = ground_y_at(tris, cx, cz)
    ch = dh * math.tan(math.radians(pitch_deg))
    cam = (cx, max(gy_cam, gy_T) + ch, cz)
    return cam, T


# ============================================================================================
# DATA
# ============================================================================================
print("loading stock (comp[1] region)...")
STOCK_BLOCKS = [(bx, by) for bx in range(11, 17) for by in range(9, 14)]
stock_tris = load_stock(STOCK_BLOCKS)
stock_fam = cells_by_fam(stock_tris)
COMP1 = dunes_component(stock_fam, want=130)
print(f"  stock dunes comp = {len(COMP1)} cells, centroid {tuple(round(v,1) for v in centroid_world(COMP1))}")

print("loading MINT (deployed bytes 18-20,17-19)...")
MINT_BLOCKS = [(bx, by) for bx in range(18, 21) for by in range(17, 20)]
mint_tris = load_mint(MINT_BLOCKS)
mint_fam = cells_by_fam(mint_tris)
MINTFP = dunes_component(mint_fam, want=144)
print(f"  mint dunes comp = {len(MINTFP)} cells, centroid {tuple(round(v,1) for v in centroid_world(MINTFP))}")

# ---- boundary geometry measure ----
bg_stock = boundary_geometry(stock_tris, COMP1)
bg_mint = boundary_geometry(mint_tris, MINTFP)
print("\n=== BOUNDARY GEOMETRY (dune|non-dune seam edge endpoints; offcell dist in CELL units) ===")
print(f"  STOCK comp[1]: {bg_stock}")
print(f"  MINT deployed: {bg_mint}")

# ============================================================================================
# RENDER -- same camera, calibrate on stock first
# ============================================================================================
W, H = 960, 600
FOV = 34.0
# auto-pick the desert-facing side from STOCK (the calibration), apply the SAME azimuth to the
# congruent mint footprint (mint has desert on every side, so this is fair).
AZ, dirct = best_desert_azimuth(COMP1, stock_fam)
print(f"stock desert-facing azimuth = {AZ}  (per-dir desert counts {dirct})")

for pitch in (22.0, 34.0):
    cam_s, T_s = make_camera(COMP1, stock_tris, AZ, pitch, dh=48.0)
    cam_m, T_m = make_camera(MINTFP, mint_tris, AZ, pitch, dh=48.0)
    print(f"\npitch {pitch}deg  stock cam {tuple(round(v,1) for v in cam_s)} -> {tuple(round(v,1) for v in T_s)}")
    print(f"             mint  cam {tuple(round(v,1) for v in cam_m)} -> {tuple(round(v,1) for v in T_m)}")
    s_tex = render_grazing(stock_tris, cam_s, T_s, FOV, W, H, shade=False)
    s_shd = render_grazing(stock_tris, cam_s, T_s, FOV, W, H, shade=True)
    m_tex = render_grazing(mint_tris, cam_m, T_m, FOV, W, H, shade=False)
    m_shd = render_grazing(mint_tris, cam_m, T_m, FOV, W, H, shade=True)

    pad = 8; lh = 20
    sheet = Image.new("RGB", (W*2+pad*3, H*2+lh*2+pad*3+26), (16, 16, 16))
    dr = ImageDraw.Draw(sheet)
    dr.text((pad, 6), f"GRAZING PERSPECTIVE pitch={pitch:.0f}deg fov={FOV:.0f} -- SAME camera rel. to congruent footprints. "
                      f"LEFT=STOCK comp[1] in situ (calibration) / RIGHT=deployed MINT bytes. Per-corner UV, perspective-correct.",
            fill=(255, 230, 140))
    panels = [("STOCK comp[1] -- UNSHADED", s_tex, 0, 0), ("MINT deployed -- UNSHADED", m_tex, 1, 0),
              ("STOCK comp[1] -- SHADED", s_shd, 0, 1), ("MINT deployed -- SHADED", m_shd, 1, 1)]
    for label, im, cx, cy in panels:
        x = pad + cx*(W+pad); y = 26 + pad + cy*(H+lh+pad)
        dr.text((x, y), label, fill=(230, 230, 230))
        sheet.paste(im, (x, y+lh))
    outp = OUTD / f"grazing_eye_pitch{int(pitch)}.png"
    sheet.save(outp)
    print(f"-> {outp}")

print("\nDONE.")
