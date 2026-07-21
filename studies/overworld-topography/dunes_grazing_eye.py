"""THE GRAZING MESH EYE -- the instrument the dunes arc never had, promoted from forensics
(scratchpad `grazing_eye.py` + `byte_compare.py`) into a FROZEN study instrument.

WHY THIS EXISTS (the verdict it is built to catch)
  The deployed dunes mint at centre (1248,-1184) was REJECTED in-game: the dune/desert ecotone
  reads as an unaligned CASTELLATED grid of tiles, while stock comp[1] in situ reads smooth and
  organic. The prior eye (`dunes_mint_eye.py`) judged the mint on ROW LABELS (a {cell: row} map)
  at a TOP-DOWN mis-framed zoom, and PASSED it -- because the label axis was never the defect.
  The defect lives in the MESH BYTES:
    Factor 1 (dominant) -- the mint enforced ZERO vertex motion, so its dune|desert boundary is
      100%% on the 4u grid; stock has ~15%% sub-cell conforming seam vertices (mean off-cell 0.022).
      A staircase by construction.
    Factor 2 -- every ecotone tile was emitted at orientation 0; stock orients the pale->red ramp
      tiles boundary-awarely across all four {0,90,180,270}. ~80%% of the mint's boundary tiles
      point the wrong way, and their per-corner UVs do not byte-derive from the donor at all.
  Neither factor is visible top-down on a row map. Both are obvious in a low-pitch GAME-CAMERA
  perspective render through the real atlas -- the view this instrument adds.

WHAT IT IS
  A mesh-level judge with THREE new numeric gates, each calibrated ON STOCK FIRST (comp[1] must
  clear every gate before any mint is judged) and each with a DONOR-DERIVED band:
    GATE A  sub-cell boundary-conformance   -- the seam's off-4u-grid vertex population.
    GATE B  per-tile orientation fidelity    -- paired same-orientation fraction vs the donor,
                                                + the byte-derivation assert (carried UVs must
                                                EQUAL the donor's bytes, not regenerate).
    GATE C  boundary-framed render check      -- a low-pitch painter-sorted grazing render whose
                                                frame is ASSERTED to contain the dune|desert
                                                boundary (never a mis-framed interior zoom), then
                                                a render-space CASTELLATION index on that boundary.
  Calibration law (the arc's hardest-won): CALIBRATE THE INSTRUMENT BEFORE YOU JUDGE WITH IT.
  Every band is the donor's own value with a stated margin; the self-test proves the instrument
  PASSES 100%% stock, and the anti-test proves it FAILS the deployed label-stamp mint on ALL three.

FREEZE MODEL (matches `dunes_mint_eye.py`)
  Stock bytes never change, so `calibrate()` is deterministic. `__main__` re-measures the donor,
  derives + writes the frozen CRITERIA to out/dunes_grazing_eye.json, renders the calibration
  sheets, and runs the self-test + anti-test. The gate FUNCTIONS are pure (criteria in, verdict
  out) so the build phase imports `judge_mesh()` cheaply -- this module does NO heavy work at
  import (the atlas is lazy-loaded only when a render is requested).

Run from the repo root:  py studies/overworld-topography/dunes_grazing_eye.py
Artifacts -> out/dunes_grazing_eye.json + out/dunes_grazing_eye_*.png
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit import config as _cfg          # noqa: E402
from ff9mapkit.world import extract as X      # noqa: E402
from ff9mapkit.world import mesh as MESH      # noqa: E402
from ff9mapkit.world import grassland as G    # noqa: E402

BLOCK = 64.0
CELL = 4.0
NEI4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
ORIS = (0, 90, 180, 270)
OUTD = HERE / "out"
OUTD.mkdir(exist_ok=True)

GP = Path(_cfg.find_game_path(None))
MOD_WORLD = "FF9CustomMap-world"

# family map (topograph id -> ecotone family). desert = the dune host; dunes = topo 41.
TOPO_FAM = {}
for t in (0, 1, 2, 3, 10, 11, 12, 13, 42):
    TOPO_FAM[t] = "grass"
for t in (4, 5, 6):
    TOPO_FAM[t] = "scrub"
for t in (17, 16, 19, 20):
    TOPO_FAM[t] = "desert"
TOPO_FAM[38] = "brush"
TOPO_FAM[41] = "dunes"
TOPO_FAM[58] = "rock"
TOPO_FAM[59] = "hole"

# the reference regions (blocks). comp[1] = the 130-cell dunes twin + its 14-cell topo-59 butte
# hole, in blocks ~(13,11); the deployed label-stamp mint is at blocks (18-20,17-19).
STOCK_BLOCKS = [(bx, by) for bx in range(12, 16) for by in range(10, 14)]
MINT_BLOCKS = [(bx, by) for bx in range(18, 21) for by in range(17, 20)]

# generative-UV decode constants (byte_compare provenance) --------------------------------------
_S = G.STRIPS[("desert", "dunes")]
_DU, _DV = _S["du"], _S["dv"]


def _clamp01(v):
    return max(0.0, min(1.0, v))


def _strip_uv(x, z, cell, row, ori):
    i, j = cell
    fx = (x - CELL * i) / CELL
    fz = (z - CELL * j) / CELL
    a, b = G.rot_ab(fx, fz, ori)
    a, b = _clamp01(a), _clamp01(b)
    u0, u1 = G.STRIP_U
    v0, v1 = G.STRIPS_V[row]
    return [u0 + a * (u1 - u0) + _DU, v0 + b * (v1 - v0) + _DV]


# ================================================================================================
# LOADING -- mesh bytes -> tris (world 3D, per-corner UV, normal, topo, family) + a per-cell map
# ================================================================================================
def _tris_of(bm, bx, by):
    V, N, U, TAN = bm.verts, bm.normals, bm.uvs, bm.tangents
    out = []
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        p3 = [(float(V[j][0]) + BLOCK * bx, float(V[j][1]), float(V[j][2]) - BLOCK * by) for j in tri]
        uv3 = [(float(U[j][0]), float(U[j][1])) for j in tri]
        n3 = [(float(N[j][0]), float(N[j][1]), float(N[j][2])) for j in tri]
        topo = X.decode_id(int(round(TAN[tri[0]][0])))["topograph"]
        out.append((p3, uv3, n3, topo, TOPO_FAM.get(topo, f"t{topo}")))
    return out


def load_stock(blocks=STOCK_BLOCKS):
    out = []
    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except (ValueError, FileNotFoundError):
            continue
        out += _tris_of(bm, bx, by)
    return out


def load_mod(blocks, mod=MOD_WORLD):
    out = []
    for (bx, by) in blocks:
        p = GP / mod / MESH.override_relpath(1, bx, by, part="Terrain")
        if not p.exists():
            continue
        bm = MESH.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        out += _tris_of(bm, bx, by)
    return out


def load_paths(paths):
    """paths: iterable of (path, bx, by) for freshly-built (pre-deploy) .ff9mesh -- the build hook."""
    out = []
    for (p, bx, by) in paths:
        bm = MESH.blockmesh_from_ff9mesh(Path(p), disc=1, x=bx, y=by, part="terrain")
        out += _tris_of(bm, bx, by)
    return out


def cells_map(tris):
    """{cell (i,j) -> list of (topo, [(wx,wz) per corner], [(u,v) per corner])}  (the decode input)."""
    out = defaultdict(list)
    for (p3, uv3, n3, topo, fam) in tris:
        w = [(p[0], p[2]) for p in p3]
        cx = sum(p[0] for p in w) / 3.0
        cz = sum(p[1] for p in w) / 3.0
        out[(math.floor(cx / CELL), math.floor(cz / CELL))].append((topo, w, uv3))
    return dict(out)


def cell_family(tris):
    """{cell -> dominant family} by tri count (centroid membership)."""
    fam_ct = defaultdict(Counter)
    for (p3, uv3, n3, topo, fam) in tris:
        cx = sum(p[0] for p in p3) / 3.0
        cz = sum(p[2] for p in p3) / 3.0
        fam_ct[(math.floor(cx / CELL), math.floor(cz / CELL))][fam] += 1
    return {c: ct.most_common(1)[0][0] for c, ct in fam_ct.items()}


def dunes_footprint(cellfam):
    """the largest 4-connected dunes component (centroid-dominant)."""
    dcells = {c for c, f in cellfam.items() if f == "dunes"}
    seen, comps = set(), []
    for s in dcells:
        if s in seen:
            continue
        comp, q = set(), deque([s])
        seen.add(s)
        while q:
            c = q.popleft()
            comp.add(c)
            for di, dj in NEI4:
                n = (c[0] + di, c[1] + dj)
                if n in dcells and n not in seen:
                    seen.add(n)
                    q.append(n)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    return comps[0] if comps else set()


def topo41_footprint(cmap):
    """the largest 4-connected component of cells carrying ANY topo-41 tri (the byte_compare
    definition: 143 for stock comp[1], 144 for the hole-filled mint) -- used for cell pairing."""
    dcells = {c for c, tl in cmap.items() if any(t == 41 for (t, _w, _uv) in tl)}
    seen, comps = set(), []
    for s in dcells:
        if s in seen:
            continue
        comp, q = set(), deque([s])
        seen.add(s)
        while q:
            c = q.popleft()
            comp.add(c)
            for di, dj in NEI4:
                n = (c[0] + di, c[1] + dj)
                if n in dcells and n not in seen:
                    seen.add(n)
                    q.append(n)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    return comps[0] if comps else set()


# ================================================================================================
# GATE A -- sub-cell boundary-conformance (the staircase detector)
# ================================================================================================
def boundary_conformance(tris, footprint):
    """For every triangle EDGE that separates a dunes tri from a non-dunes tri (a visible seam
    edge, by centroid cell membership in `footprint`), measure each endpoint's distance to the
    nearest 4u grid line (in CELL units). A pure 4u staircase puts every endpoint at 0 (all seam
    verts sit on cell lines); stock's real geometry has ~15%% off-grid conforming verts.

    Returns dict(n, frac_on_grid, off_grid_frac, mean_offcell, p90_offcell)."""
    fp = set(footprint)

    def is_dune(w):
        cx = sum(p[0] for p in w) / 3.0
        cz = sum(p[1] for p in w) / 3.0
        return (math.floor(cx / CELL), math.floor(cz / CELL)) in fp

    edges = defaultdict(list)
    for (p3, uv3, n3, topo, fam) in tris:
        w = [(p[0], p[2]) for p in p3]
        d = is_dune(w)
        ks = [tuple(round(v, 3) for v in p) for p in w]
        for i in range(3):
            e = frozenset((ks[i], ks[(i + 1) % 3]))
            if len(e) == 2:
                edges[e].append(d)
    seam = []
    for e, ds in edges.items():
        if len(set(ds)) == 2 or (len(ds) == 1 and ds[0]):
            for (px, pz) in e:
                rx = abs(px / CELL - round(px / CELL))
                rz = abs(pz / CELL - round(pz / CELL))
                seam.append(min(rx, rz))
    if not seam:
        return dict(n=0, frac_on_grid=None, off_grid_frac=None, mean_offcell=None, p90_offcell=None)
    arr = np.array(seam)
    on_grid = float((arr < 0.05).mean())
    return dict(n=len(arr), frac_on_grid=on_grid, off_grid_frac=round(1.0 - on_grid, 5),
                mean_offcell=float(arr.mean()), p90_offcell=float(np.percentile(arr, 90)))


# ================================================================================================
# GATE B -- per-tile orientation fidelity + byte-derivation (the generative decode)
# ================================================================================================
def _classify_tri(topo, world_pts, uvs, cell, eps=0.004):
    """Brute-force recover a tri's tile identity from its UVs: ('strip',row,ori) /
    ('mains',ground,quad,ori) / ('other',). Tries all four orientations -- so the recovered ori
    is real, not assumed."""
    def match(fn):
        return all(abs(fn(p)[0] - uv[0]) < eps and abs(fn(p)[1] - uv[1]) < eps
                   for p, uv in zip(world_pts, uvs))
    fam = TOPO_FAM.get(topo)
    if fam in ("desert", "dunes"):
        for ori in ORIS:
            for row in range(4):
                if match(lambda p, r=row, o=ori: _strip_uv(p[0], p[2], cell, r, o)):
                    return ("strip", row, ori)
    for ground in ("dunes", "desert"):
        for uh in (0, 1):
            for vh in (0, 1):
                for ori in ORIS:
                    if match(lambda p, q=(uh, vh), o=ori, g=ground:
                             G.ground_uv(p[0], p[2], cell, q, o, g)):
                        return ("mains", ground, (uh, vh), ori)
    return ("other", None, None)


def _cell_class(tris_of_cell, cell):
    """Collapse a cell's tris to (class, key, ori-set): strip -> (rows), mains -> (grounds)."""
    strips, mains = [], []
    for (topo, w3, uv3) in tris_of_cell:
        world_pts = [(wx, 0.0, wz) for (wx, wz) in w3]
        cls = _classify_tri(topo, world_pts, uv3, cell)
        if cls[0] == "strip":
            strips.append((cls[1], cls[2]))
        elif cls[0] == "mains":
            mains.append((cls[1], cls[3]))
    if strips:
        return ("strip", tuple(sorted(set(r for r, o in strips))),
                tuple(sorted(set(o for r, o in strips))))
    if mains:
        return ("mains", tuple(sorted(set(g for g, o in mains))),
                tuple(sorted(set(o for g, o in mains))))
    return ("other", (), ())


def _cell_uvset(tris_of_cell, nd=5):
    """the SET of distinct per-corner (u,v) a cell wears (rounded) -- the byte-derivation key.
    A rigid world-space carry copies UVs verbatim, so a true carry's set EQUALS the donor's."""
    s = set()
    for (topo, w3, uv3) in tris_of_cell:
        for (u, v) in uv3:
            s.add((round(u, nd), round(v, nd)))
    return frozenset(s)


def orientation_fidelity(donor_cmap, cand_cmap, donor_fp, T):
    """Pair each donor footprint cell to its candidate twin (donor + T), decode both, and report:
      paired_same_ori  -- fraction of donor cells that decode to strip/mains whose candidate twin
                          has the SAME class AND the SAME orientation set (class disagreement = miss)
      byte_derivation  -- fraction of those paired cells whose candidate per-corner UV SET is
                          byte-identical to the donor's (a true carry -> 1.0; a regenerate -> ~0)
    Also returns the raw orientation histograms (donor vs candidate) for the record."""
    n_decodable = 0
    n_same_ori = 0
    n_byte = 0
    don_ori = Counter()
    cand_ori = Counter()
    class_agree = 0
    for dc in donor_fp:
        dtris = donor_cmap.get(dc)
        mtris = cand_cmap.get((dc[0] + T[0], dc[1] + T[1]))
        if not dtris:
            continue
        dcls = _cell_class(dtris, dc)
        if dcls[0] == "other":
            continue
        n_decodable += 1
        for o in dcls[2]:
            don_ori[o] += 1
        if not mtris:
            continue
        mcls = _cell_class(mtris, (dc[0] + T[0], dc[1] + T[1]))
        for o in mcls[2]:
            cand_ori[o] += 1
        if mcls[0] == dcls[0]:
            class_agree += 1
        if mcls[0] == dcls[0] and mcls[2] == dcls[2]:
            n_same_ori += 1
        if _cell_uvset(mtris) == _cell_uvset(dtris):
            n_byte += 1
    return dict(
        n_decodable=n_decodable,
        paired_same_ori=(n_same_ori / n_decodable) if n_decodable else None,
        byte_derivation=(n_byte / n_decodable) if n_decodable else None,
        class_agreement=(class_agree / n_decodable) if n_decodable else None,
        donor_ori_hist=dict(don_ori), cand_ori_hist=dict(cand_ori),
    )


# ================================================================================================
# GRAZING RENDER (painter-sorted, per-corner UV, perspective-correct) + the family buffer
# ================================================================================================
_ATLAS = None
_APX = None
_AW = _AH = 0


def _load_atlas():
    global _ATLAS, _APX, _AW, _AH
    if _ATLAS is not None:
        return
    from PIL import Image
    mog = (GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap"
           / "textures" / "res(1_24)_terrain.png")
    _ATLAS = Image.open(mog).convert("RGBA")
    _AW, _AH = _ATLAS.size
    _APX = _ATLAS.load()


def _atlas_bilinear(u, v):
    fx = (u % 1.0) * _AW - 0.5
    fy = (1.0 - v % 1.0) * _AH - 0.5
    x0, y0 = int(math.floor(fx)), int(math.floor(fy))
    tx, ty = fx - x0, fy - y0
    acc = [0.0, 0.0, 0.0]
    aa = 0.0
    for (dx, dy, wg) in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)),
                         (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
        r, g, b, a = _APX[min(max(x0 + dx, 0), _AW - 1), min(max(y0 + dy, 0), _AH - 1)]
        acc[0] += r * wg
        acc[1] += g * wg
        acc[2] += b * wg
        aa += a * wg
    return aa, (acc[0], acc[1], acc[2])


_FAM_ID = {"dunes": 1, "desert": 2, "grass": 3, "scrub": 3, "brush": 3, "rock": 4, "hole": 4}


def render_grazing(tris, cam_pos, look_at, fov_y_deg, W, H, *, shade=True, want_family=False):
    """Painter-sorted (back-to-front by tri centroid depth) perspective render through the real
    atlas, per-corner UV, perspective-correct varyings. Returns a PIL RGB image; if `want_family`
    also returns a HxW int family-id buffer (0 sky / 1 dunes / 2 desert / 3 grass / 4 rock)."""
    _load_atlas()
    from PIL import Image
    up_world = np.array([0.0, 1.0, 0.0])
    cam = np.array(cam_pos, float)
    fwd = np.array(look_at, float) - cam
    fwd = fwd / (np.linalg.norm(fwd) or 1.0)
    right = np.cross(fwd, up_world)
    right = right / (np.linalg.norm(right) or 1.0)
    up = np.cross(right, fwd)
    f = (H / 2.0) / math.tan(math.radians(fov_y_deg) / 2.0)
    LDIR = np.array([-0.45, 0.72, 0.45])
    LDIR = LDIR / np.linalg.norm(LDIR)

    img = Image.new("RGB", (W, H), (150, 176, 214))
    px = img.load()
    fam_buf = [[0] * W for _ in range(H)] if want_family else None

    def project(p):
        rel = np.array(p, float) - cam
        return (float(np.dot(rel, right)), float(np.dot(rel, up)), float(np.dot(rel, fwd)))

    # painter's sort: farthest centroid first
    prepared = []
    for (p3, uv3, n3, topo, fam) in tris:
        pv = [project(p) for p in p3]
        if any(v[2] < 0.6 for v in pv):
            continue
        cz = (pv[0][2] + pv[1][2] + pv[2][2]) / 3.0
        prepared.append((cz, pv, uv3, n3, fam))
    prepared.sort(key=lambda t: -t[0])

    for (_cz, pv, uv3, n3, fam) in prepared:
        sx = [W / 2.0 + f * v[0] / v[2] for v in pv]
        sy = [H / 2.0 - f * v[1] / v[2] for v in pv]
        invw = [1.0 / v[2] for v in pv]
        uvw = [(uv3[k][0] * invw[k], uv3[k][1] * invw[k]) for k in range(3)]
        nw = [(n3[k][0] * invw[k], n3[k][1] * invw[k], n3[k][2] * invw[k]) for k in range(3)]
        minx, maxx = int(max(0, math.floor(min(sx)))), int(min(W - 1, math.ceil(max(sx))))
        miny, maxy = int(max(0, math.floor(min(sy)))), int(min(H - 1, math.ceil(max(sy))))
        if minx > maxx or miny > maxy:
            continue
        d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
        if abs(d) < 1e-9:
            continue
        fid = _FAM_ID.get(fam, 4)
        for yy in range(miny, maxy + 1):
            for xx in range(minx, maxx + 1):
                w0 = ((sy[1] - sy[2]) * (xx - sx[2]) + (sx[2] - sx[1]) * (yy - sy[2])) / d
                w1 = ((sy[2] - sy[0]) * (xx - sx[2]) + (sx[0] - sx[2]) * (yy - sy[2])) / d
                w2 = 1.0 - w0 - w1
                if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6:
                    continue
                iw = w0 * invw[0] + w1 * invw[1] + w2 * invw[2]
                u = (w0 * uvw[0][0] + w1 * uvw[1][0] + w2 * uvw[2][0]) / iw
                v = (w0 * uvw[0][1] + w1 * uvw[1][1] + w2 * uvw[2][1]) / iw
                aa, rgb = _atlas_bilinear(u, v)
                if aa < 24:
                    continue
                if shade:
                    nx = (w0 * nw[0][0] + w1 * nw[1][0] + w2 * nw[2][0]) / iw
                    ny = (w0 * nw[0][1] + w1 * nw[1][1] + w2 * nw[2][1]) / iw
                    nz = (w0 * nw[0][2] + w1 * nw[1][2] + w2 * nw[2][2]) / iw
                    nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
                    sh = 0.5 + 0.5 * max(0.0, (nx * LDIR[0] + ny * LDIR[1] + nz * LDIR[2]) / nl)
                else:
                    sh = 1.0
                px[xx, yy] = tuple(min(255, int(c * sh)) for c in rgb)
                if fam_buf is not None:
                    fam_buf[yy][xx] = fid
    if want_family:
        return img, np.array(fam_buf, dtype=np.int16)
    return img


# ---- camera: stand on the dunes interior, look OUT across the ecotone at grazing pitch ----------
def _centroid_world(cells):
    xs = [c[0] for c in cells]
    zs = [c[1] for c in cells]
    return (CELL * (sum(xs) / len(xs) + 0.5), CELL * (sum(zs) / len(zs) + 0.5))


def _ground_y_at(tris, wx, wz):
    best, by = None, 0.0
    for (p3, uv3, n3, topo, fam) in tris:
        cx = sum(p[0] for p in p3) / 3.0
        cz = sum(p[2] for p in p3) / 3.0
        d = (cx - wx) ** 2 + (cz - wz) ** 2
        if best is None or d < best:
            best = d
            by = sum(p[1] for p in p3) / 3.0
    return by


def best_desert_azimuth(footprint, cellfam):
    dirs = {(1, 0): 0, (-1, 0): 0, (0, 1): 0, (0, -1): 0}
    fp = set(footprint)
    for (di, dj) in dirs:
        cnt = 0
        for c in fp:
            for k in (1, 2, 3):
                n = (c[0] + di * k, c[1] + dj * k)
                if n not in fp and cellfam.get(n) == "desert":
                    cnt += 1
        dirs[(di, dj)] = cnt
    best = max(dirs, key=dirs.get)
    return (float(best[0]), float(best[1])), dirs


def make_camera(footprint, tris, azimuth, pitch_deg, dh=48.0):
    Cf = _centroid_world(footprint)
    xs = [c[0] for c in footprint]
    zs = [c[1] for c in footprint]
    span = CELL * max(max(xs) - min(xs), max(zs) - min(zs))
    ax, az = azimuth
    T = (Cf[0] + ax * span * 0.5, 0.0, Cf[1] + az * span * 0.5)
    gy_T = _ground_y_at(tris, T[0], T[2])
    T = (T[0], gy_T, T[2])
    cx, cz = T[0] - ax * dh, T[2] - az * dh
    gy_cam = _ground_y_at(tris, cx, cz)
    ch = dh * math.tan(math.radians(pitch_deg))
    return (cx, max(gy_cam, gy_T) + ch, cz), T


# ================================================================================================
# GATE C -- the boundary-framed render check: framing assert (guard) + castellation index
# ================================================================================================
def frame_contains_boundary(fam_buf, *, min_dunes_px=1500, min_desert_px=1500, min_columns=0.35):
    """GUARD (the TIGHT mis-framing was a real miss): the judged frame MUST contain the
    dune|desert boundary. Assert both families are present in force AND that a dunes/desert
    vertical transition exists in >= min_columns of the image columns.

    Returns dict(ok, dunes_px, desert_px, boundary_cols_frac)."""
    H, Wd = fam_buf.shape
    dunes_px = int((fam_buf == 1).sum())
    desert_px = int((fam_buf == 2).sum())
    cols_with_boundary = 0
    for x in range(Wd):
        col = fam_buf[:, x]
        has_d = np.any(col == 1)
        has_s = np.any(col == 2)
        if has_d and has_s:
            cols_with_boundary += 1
    frac = cols_with_boundary / Wd
    ok = (dunes_px >= min_dunes_px and desert_px >= min_desert_px and frac >= min_columns)
    return dict(ok=bool(ok), dunes_px=dunes_px, desert_px=desert_px,
                boundary_cols_frac=round(frac, 4))


def _boundary_pixels(fam_buf):
    """dune pixels 4-adjacent to a desert pixel -- the rendered pale|red frontier."""
    d = (fam_buf == 1)
    s = (fam_buf == 2)
    nb = np.zeros_like(s)
    nb[1:, :] |= s[:-1, :]
    nb[:-1, :] |= s[1:, :]
    nb[:, 1:] |= s[:, :-1]
    nb[:, :-1] |= s[:, 1:]
    return d & nb


def boundary_organicity(fam_buf):
    """RENDER-SPACE READ of the sub-cell conformance defect (the calibrated gate-C metric).

    Build the frontier profile y(x) = median rendered row of the dune|desert boundary in each
    column, lightly smoothed, then count DIRECTION REVERSALS (local extrema) per 100 columns.
    Stock's ~15%% off-grid conforming seam verts push the boundary in-and-out at sub-cell scale,
    so its rendered frontier WIGGLES -> many reversals (~46-56/100col). The label-stamp mint's
    grid-locked verts make the boundary a monotone staircase trend -> almost no reversals
    (~2/100col). A ~25x separation, measured on both stock and the deployed mint before freezing.

    HIGHER = more organic (good). Returns dict(turns_per_100col, n_cols, reversals)."""
    H, Wd = fam_buf.shape
    bp = _boundary_pixels(fam_buf)
    ys_by_col = defaultdict(list)
    yy, xx = np.where(bp)
    for (x, y) in zip(xx.tolist(), yy.tolist()):
        ys_by_col[x].append(y)
    cols = sorted(ys_by_col)
    if len(cols) < 20:
        return dict(turns_per_100col=None, n_cols=len(cols), reversals=0)
    prof = np.array([np.median(ys_by_col[c]) for c in cols], float)
    # slope sign-change count on the RAW frontier profile (the validated forensics metric; a
    # ~25x stock/mint separation -- smoothing was tried and destroys the very fine wiggle that
    # IS the signal, so the raw profile is used deliberately).
    d1 = np.diff(prof)
    reversals = int(np.sum(np.abs(np.diff(np.sign(d1))) > 0))
    tp = reversals / len(prof) * 100.0
    return dict(turns_per_100col=round(tp, 3), n_cols=len(prof), reversals=reversals)


# ================================================================================================
# CALIBRATION -- measure the donor, derive the frozen bands (donor value + stated margin)
# ================================================================================================
def _bbox_min(cells):
    return (min(c[0] for c in cells), min(c[1] for c in cells))


def calibrate(*, render=True):
    """Read stock comp[1], derive every frozen band from IT. Returns (criteria, calib) where
    criteria is the frozen gate dict and calib is the full measurement record."""
    print("=" * 96)
    print("CALIBRATE ON STOCK -- comp[1] must clear every gate before any mint is judged")
    print("=" * 96)
    stock = load_stock()
    scfam = cell_family(stock)
    scmap = cells_map(stock)
    FP = dunes_footprint(scfam)              # centroid-dominant (boundary conformance + camera)
    FP41 = topo41_footprint(scmap)           # any-topo41 (cell pairing)
    print(f"  stock dunes footprint (centroid-dominant) = {len(FP)} cells, "
          f"topo41 component = {len(FP41)} cells, centroid {tuple(round(v,1) for v in _centroid_world(FP))}")

    # ---- GATE A donor measurement ----
    A = boundary_conformance(stock, FP)
    print(f"\n  GATE A donor boundary-conformance: {A}")
    # band: a candidate must show >= half the donor's off-grid population AND >= half its mean
    # off-cell displacement. A rigid carry reproduces the donor exactly (both == donor); the
    # label-stamp mint is 0.0/0.0 -> hard fail. The half-margin absorbs finite-sample variation
    # in the ring/margin the carry welds.
    A_OFFGRID_MIN = round(A["off_grid_frac"] * 0.5, 5)
    A_MEANOFF_MIN = round(A["mean_offcell"] * 0.5, 6)

    # ---- GATE B: donor-vs-donor (identity) must be perfect ----
    B_self = orientation_fidelity(scmap, scmap, FP41, (0, 0))
    print(f"  GATE B donor self-fidelity (identity): paired_same_ori={B_self['paired_same_ori']:.4f} "
          f"byte_derivation={B_self['byte_derivation']:.4f} class_agreement={B_self['class_agreement']:.4f} "
          f"(n_decodable={B_self['n_decodable']})")
    # a true carry equals the donor byte-for-byte -> both metrics 1.0; require >= 0.90 to absorb
    # brute-force decode epsilon noise. the label-stamp mint scores ~0.18 / ~0.10 -> fail.
    B_ORI_MIN = 0.90
    B_BYTE_MIN = 0.90

    # ---- GATE C: render the donor, confirm smooth (framing ok + low castellation) ----
    C_calib = None
    if render:
        AZ, dirct = best_desert_azimuth(FP, scfam)
        print(f"  GATE C camera desert-facing azimuth = {AZ} (per-dir desert counts {dirct})")
        c_org = []
        c_frames = []
        for pitch in (22.0, 34.0):
            cam, look = make_camera(FP, stock, AZ, pitch)
            _img, fam = render_grazing(stock, cam, look, 34.0, 960, 600, shade=False, want_family=True)
            fr = frame_contains_boundary(fam)
            org = boundary_organicity(fam)
            c_org.append(org["turns_per_100col"])
            c_frames.append((pitch, fr, org))
            print(f"    pitch {pitch:.0f}: framing {fr}  organicity {org}")
        C_calib = dict(azimuth=list(AZ), frames=[(p, fr, org) for (p, fr, org) in c_frames])
        # band: HIGHER organicity = more sub-cell wiggle = good. Stock ~46-56/100col, the deployed
        # mint ~2 (a 25x gap). A candidate must clear half the donor's WORST-pitch organicity on
        # BOTH pitches; a rigid carry reproduces the donor's wiggle (pass), the staircase fails.
        donor_min_org = min(o for o in c_org if o is not None)
        C_ORG_MIN = round(donor_min_org * 0.5, 4)
    else:
        C_ORG_MIN = None

    criteria = dict(
        gateA_offgrid_frac_min=A_OFFGRID_MIN,
        gateA_mean_offcell_min=A_MEANOFF_MIN,
        gateB_orientation_fidelity_min=B_ORI_MIN,
        gateB_byte_derivation_min=B_BYTE_MIN,
        gateC_organicity_min=C_ORG_MIN,
        gateC_framing_required=True,
        donor=dict(
            footprint_cells=len(FP), topo41_cells=len(FP41),
            boundary_conformance=A,
            self_fidelity=dict(paired_same_ori=B_self["paired_same_ori"],
                               byte_derivation=B_self["byte_derivation"],
                               class_agreement=B_self["class_agreement"],
                               n_decodable=B_self["n_decodable"]),
            render_calibration=C_calib,
        ),
    )
    return criteria, dict(stock=stock, scfam=scfam, scmap=scmap, FP=FP, FP41=FP41, A=A, B_self=B_self)


# ================================================================================================
# THE FROZEN JUDGE -- the entry point the build phase imports
# ================================================================================================
def judge_mesh(cand_tris, cand_cmap, cand_fp_centroid, cand_fp41,
               donor_cmap, donor_fp41, T, criteria, *,
               cand_fam=None, cand_azimuth=None, label="MINT", render=True, render_tag=None):
    """Judge a candidate mesh against the donor on the THREE frozen mesh gates. ALL must pass.

    cand_tris        : the candidate's tris (world 3D)                     -> GATE A + render
    cand_cmap        : cells_map(cand_tris)                                -> GATE B decode
    cand_fp_centroid : the candidate's centroid-dominant dunes footprint   -> GATE A + camera
    cand_fp41        : the candidate's topo-41 component                    -> (report only)
    donor_cmap       : the donor's cells_map                               -> GATE B pairing
    donor_fp41       : the donor's topo-41 component                       -> GATE B pairing keys
    T                : (dx,dz) donor-cell -> candidate-cell translation     -> GATE B pairing
    criteria         : the frozen band dict from calibrate()
    cand_fam         : cell_family(cand_tris) (for the render azimuth); computed if None

    Returns dict(passed, gates)."""
    res = {}

    # GATE A
    A = boundary_conformance(cand_tris, cand_fp_centroid)
    a_ok = (A["off_grid_frac"] is not None
            and A["off_grid_frac"] >= criteria["gateA_offgrid_frac_min"]
            and A["mean_offcell"] >= criteria["gateA_mean_offcell_min"])
    res["A_sub_cell_conformance"] = (
        dict(off_grid_frac=A["off_grid_frac"], mean_offcell=(round(A["mean_offcell"], 5)
             if A["mean_offcell"] is not None else None), n=A["n"]), bool(a_ok))

    # GATE B
    B = orientation_fidelity(donor_cmap, cand_cmap, donor_fp41, T)
    b_ok = (B["paired_same_ori"] is not None
            and B["paired_same_ori"] >= criteria["gateB_orientation_fidelity_min"]
            and B["byte_derivation"] >= criteria["gateB_byte_derivation_min"])
    res["B_orientation_fidelity"] = (
        dict(paired_same_ori=(round(B["paired_same_ori"], 4) if B["paired_same_ori"] is not None else None),
             byte_derivation=(round(B["byte_derivation"], 4) if B["byte_derivation"] is not None else None),
             class_agreement=(round(B["class_agreement"], 4) if B["class_agreement"] is not None else None),
             n_decodable=B["n_decodable"]), bool(b_ok))

    # GATE C
    if render:
        if cand_fam is None:
            cand_fam = cell_family(cand_tris)
        AZ = cand_azimuth or best_desert_azimuth(cand_fp_centroid, cand_fam)[0]
        framings = []
        orgs = []
        imgs = []
        for pitch in (22.0, 34.0):
            cam, look = make_camera(cand_fp_centroid, cand_tris, AZ, pitch)
            img, fam = render_grazing(cand_tris, cam, look, 34.0, 960, 600, shade=False, want_family=True)
            fr = frame_contains_boundary(fam)
            org = boundary_organicity(fam)
            framings.append(fr)
            orgs.append(org)
            imgs.append((pitch, img))
        frame_ok = all(fr["ok"] for fr in framings)
        if not frame_ok:
            # the guard: a mis-framed render CANNOT be judged (never repeat the TIGHT miss)
            res["C_boundary_render"] = (dict(framing="MIS-FRAMED -- cannot judge", framings=framings), False)
        else:
            per = [o["turns_per_100col"] for o in orgs]
            cmin = min((o for o in per if o is not None), default=None)
            c_ok = (cmin is not None and cmin >= criteria["gateC_organicity_min"])
            res["C_boundary_render"] = (
                dict(organicity_min=cmin, per_pitch=per, framing_ok=True), bool(c_ok))
        if render_tag:
            _save_judge_render(imgs, render_tag)
    else:
        res["C_boundary_render"] = (dict(skipped="render=False"), True)

    allpass = all(p for _v, p in res.values())
    print(f"\n[judge_mesh {label}] {'>>> PASS <<<' if allpass else '>>> FAIL <<<'}")
    for g, (v, p) in res.items():
        print(f"   {g:28s} {'ok  ' if p else 'FAIL'}  {v}")
    return dict(passed=allpass, gates=res)


def load_criteria():
    """Return the frozen gate bands: read the committed out/dunes_grazing_eye.json if present
    (cheap -- the build hook), else re-calibrate from stock. Lets `dunes_mint_eye.judge(mesh=...)`
    and the build phase get the frozen bands without re-reading the atlas + stock every time."""
    p = OUTD / "dunes_grazing_eye.json"
    if p.exists():
        return json.loads(p.read_text())["criteria"]
    crit, _ = calibrate(render=True)
    return crit


def strip_rowmap(cmap, footprint):
    """{cell -> strip row 0-3} for the footprint cells that decode as a strip cell -- the input
    `dunes_mint_eye`'s ROW judge (M1/M2) expects. Lets the same deployed artifact be judged on the
    row axis AND the mesh axis in one coherent call (the integration demo)."""
    out = {}
    for c in footprint:
        tl = cmap.get(c)
        if not tl:
            continue
        cls = _cell_class(tl, c)
        if cls[0] == "strip" and cls[1]:
            out[c] = int(cls[1][0])
    return out


def translation(donor_fp41, cand_fp41):
    """(dx,dz) mapping a donor cell to its candidate twin, by topo-41 footprint bbox-min."""
    d = _bbox_min(donor_fp41)
    m = _bbox_min(cand_fp41)
    return (m[0] - d[0], m[1] - d[1])


def _save_judge_render(imgs, tag):
    from PIL import Image, ImageDraw
    W = H = 0
    for (_p, im) in imgs:
        W, H = im.size
    pad = 8
    sheet = Image.new("RGB", (W, H * len(imgs) + pad * (len(imgs) + 1) + 20), (16, 16, 16))
    dr = ImageDraw.Draw(sheet)
    dr.text((pad, 4), f"judge_mesh render -- {tag}", fill=(255, 230, 140))
    y = 20 + pad
    for (p, im) in imgs:
        sheet.paste(im, (pad, y))
        y += H + pad
    sheet.save(OUTD / f"dunes_grazing_eye_judge_{tag}.png")


# ================================================================================================
# __main__ : calibrate -> freeze -> render calibration sheet -> self-test -> anti-test
# ================================================================================================
def _calibration_sheet(calib):
    """the LEFT=stock smooth / RIGHT=mint castellated grazing sheet, at 2 pitches (the witness)."""
    from PIL import Image, ImageDraw
    stock = calib["stock"]
    scfam = calib["scfam"]
    FP = calib["FP"]
    mint = load_mod(MINT_BLOCKS)
    mfam = cell_family(mint)
    MFP = dunes_footprint(mfam)
    AZ, _ = best_desert_azimuth(FP, scfam)
    W, H = 960, 600
    for pitch in (22.0, 34.0):
        cam_s, look_s = make_camera(FP, stock, AZ, pitch)
        cam_m, look_m = make_camera(MFP, mint, AZ, pitch)
        s_img = render_grazing(stock, cam_s, look_s, 34.0, W, H, shade=False)
        m_img = render_grazing(mint, cam_m, look_m, 34.0, W, H, shade=False)
        pad = 8
        lh = 20
        sheet = Image.new("RGB", (W * 2 + pad * 3, H + lh + pad * 2 + 24), (16, 16, 16))
        dr = ImageDraw.Draw(sheet)
        dr.text((pad, 6), f"GRAZING CALIBRATION pitch={pitch:.0f} -- LEFT stock comp[1] (must read SMOOTH) / "
                          f"RIGHT deployed label-stamp MINT (castellated). Painter-sorted, per-corner UV.",
                fill=(255, 230, 140))
        dr.text((pad, 24 + pad), "STOCK comp[1] -- calibration (smooth)", fill=(220, 220, 220))
        dr.text((pad + W + pad, 24 + pad), "MINT deployed -- anti-fixture (castellated)", fill=(220, 220, 220))
        sheet.paste(s_img, (pad, 24 + pad + lh))
        sheet.paste(m_img, (pad + W + pad, 24 + pad + lh))
        sheet.save(OUTD / f"dunes_grazing_eye_calib_pitch{int(pitch)}.png")
        print(f"    -> out/dunes_grazing_eye_calib_pitch{int(pitch)}.png")


def main():
    criteria, calib = calibrate(render=True)

    print("\n" + "=" * 96)
    print("THE FROZEN GATES (donor value + stated margin)")
    print("=" * 96)
    for k, v in criteria.items():
        if k != "donor":
            print(f"   {k:36s} = {v}")

    print("\n" + "=" * 96)
    print("CALIBRATION SHEET (stock smooth vs deployed mint castellated)")
    print("=" * 96)
    _calibration_sheet(calib)

    # ---- INSTRUMENT SELF-TEST: judge stock comp[1] against itself -> PASS all three ----
    print("\n" + "=" * 96)
    print("SELF-TEST -- judge stock comp[1] against itself (a faithful carry == this) -> must PASS")
    print("=" * 96)
    stock = calib["stock"]
    scfam = calib["scfam"]
    scmap = calib["scmap"]
    FP = calib["FP"]
    FP41 = calib["FP41"]
    self_res = judge_mesh(stock, scmap, FP, FP41, scmap, FP41, (0, 0), criteria,
                          cand_fam=scfam, label="STOCK comp[1] (self-test)", render=True,
                          render_tag="selftest_stock")

    # ---- ANTI-TEST: judge the deployed label-stamp mint against the donor -> must FAIL all three ----
    print("\n" + "=" * 96)
    print("ANTI-TEST -- judge the DEPLOYED label-stamp mint against the donor -> must FAIL all three")
    print("=" * 96)
    mint = load_mod(MINT_BLOCKS)
    mfam = cell_family(mint)
    mcmap = cells_map(mint)
    MFP = dunes_footprint(mfam)
    MFP41 = topo41_footprint(mcmap)
    # donor-cell -> mint-cell translation by topo41 footprint bbox-min
    dmin = _bbox_min(FP41)
    mmin = _bbox_min(MFP41)
    T = (mmin[0] - dmin[0], mmin[1] - dmin[1])
    print(f"  donor->mint translation T = {T}  (donor bbox-min {dmin}, mint bbox-min {mmin})")
    anti_res = judge_mesh(mint, mcmap, MFP, MFP41, scmap, FP41, T, criteria,
                          cand_fam=mfam, label="DEPLOYED label-stamp mint (anti-test)",
                          render=True, render_tag="antitest_mint")

    # ---- mis-framing demonstration: a deep-interior camera FAILS the framing guard ----
    print("\n" + "=" * 96)
    print("MIS-FRAMING DEMO -- an interior-zoom camera must fail the GATE C framing guard")
    print("=" * 96)
    Cf = _centroid_world(FP)
    gy = _ground_y_at(stock, Cf[0], Cf[1])
    tight_cam = (Cf[0], gy + 6.0, Cf[1] + 4.0)     # low over the dune interior, looking inward
    tight_look = (Cf[0], gy, Cf[1] - 8.0)
    _img, fam = render_grazing(stock, tight_cam, tight_look, 20.0, 960, 600, shade=False, want_family=True)
    fr = frame_contains_boundary(fam)
    print(f"  interior-zoom framing = {fr}  -> guard {'CORRECTLY BLOCKS (cannot judge)' if not fr['ok'] else 'FAILED TO BLOCK (BAD)'}")

    # ---- dump the frozen instrument ----
    out = dict(
        instrument="dunes_grazing_eye -- the grazing mesh eye (3 mesh gates, frozen)",
        note="stock bytes are deterministic; re-runs reproduce these bands byte-for-byte",
        criteria=criteria,
        self_test=dict(passed=self_res["passed"],
                       gates={g: (v, p) for g, (v, p) in self_res["gates"].items()}),
        anti_test=dict(passed=anti_res["passed"], translation=list(T),
                       gates={g: (v, p) for g, (v, p) in anti_res["gates"].items()}),
        misframe_guard=dict(interior_zoom_framing=fr, blocks_correctly=not fr["ok"]),
        renders=[p.name for p in sorted(OUTD.glob("dunes_grazing_eye_*.png"))],
    )
    (OUTD / "dunes_grazing_eye.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"\n-> {OUTD / 'dunes_grazing_eye.json'}")

    ok = (self_res["passed"] and not anti_res["passed"] and not fr["ok"])
    # the anti-test must fail on ALL THREE axes, not just one
    anti_all_three = all(not p for _v, p in anti_res["gates"].values())
    print("\n" + "=" * 96)
    print(f"INSTRUMENT FROZEN. self-test PASS={self_res['passed']}  "
          f"anti-test FAIL={not anti_res['passed']} (all three axes={anti_all_three})  "
          f"misframe-guard blocks={not fr['ok']}")
    print("=" * 96)
    assert self_res["passed"], "SELF-TEST FAILED: instrument rejects 100% stock -- miscalibrated"
    assert anti_all_three, "ANTI-TEST INCOMPLETE: deployed mint did not fail all three gates"
    assert not fr["ok"], "MIS-FRAMING GUARD FAILED: an interior zoom was judgeable"
    print("ALL INSTRUMENT INVARIANTS HOLD. The eye is frozen; the build phase may not touch it.")
    return ok


if __name__ == "__main__":
    main()
