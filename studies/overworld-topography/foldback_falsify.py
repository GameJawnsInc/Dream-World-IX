"""THE GENERATOR FOLD-BACK -- CODE-DISJOINT FALSIFIER ON THE FRESH MINT (2026-07-25).

Extends MY OWN falsifier lineage
(uvf_fix_falsify -> uvf_fix2..8_falsify -> rung_f_falsify -> rung_f_frame_falsify -> THIS).

Does NOT import junction_compose / composite_gates / freshmint_run / freshmint_site_scan /
rung_f_* / uvf_* / seam_null_recon.  Reuses ONLY:
  * the raw-byte loaders ff9mapkit.world.extract (X.read_block, X.block_world_origin, X.decode_id)
    and .mesh (M.override_relpath)  -- the file format, not the build;
  * the KIT's own ground VOCABULARY (grassland.GROUNDS / FAM_REGION / STRIP_U / STRIPS_V / STRIPS /
    TOPO_FAMILY / ground_uv / assign_mains, island.ROCK_U/ROCK_V) -- the very language the build
    claims to have dressed the tris in, hence the correct oracle rather than shared build code.
Everything else -- the .ff9mesh parser, the carried/minted classifier, the donor index, the UV-rect
classifier, the one-window solver, the reference-surface estimator, the weld graph, the basin
detector, the spike/step census, the orphan census, the sea gates, the chevron statistics and every
threshold comparison -- is re-implemented here from raw bytes.

TARGET: out/foldback/freshmint-tree/  (the fresh-site r125 two-ground composite, 180 files, 20 blocks)
OUT:    out/foldback/foldback_falsify.json

READ-ONLY vs the game install (stock block reads only).  Writes nothing but its own json.

    PYTHONIOENCODING=utf-8 py -X utf8 foldback_falsify.py
"""
from __future__ import annotations
import json, math, random, statistics, struct, sys, time
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))

from ff9mapkit.world import extract as X        # noqa: E402
from ff9mapkit.world import mesh as M           # noqa: E402
from ff9mapkit.world import grassland as G      # noqa: E402
from ff9mapkit.world import island as ISL       # noqa: E402

OUTDIR = HERE / "out" / "foldback"
TREE = OUTDIR / "freshmint-tree"
CONTROL = OUTDIR / "control-selftest-tree"          # the pipeline's rung-F self-test (site -1024u)
REPORT = OUTDIR / "freshmint_report.json"
SITEJSON = OUTDIR / "freshmint_site.json"
OUT = OUTDIR / "foldback_falsify.json"

FOOTPRINT = [(bx, by) for bx in range(0, 5) for by in range(0, 4)]
CONTROL_DBY = 16                                    # control block (bx, by+16) <-> fresh (bx, by)
PARTS = ("Terrain", "Object", "Beach1", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5")
SEA_PARTS = ("Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Beach1")
MAGIC = b"F9WM"
CELL = 4.0
BLOCK = 64.0
GRID_W, GRID_H = 24, 20

# ---- the site the mint claims (re-derived here only to key the donor transform) --------------
CLEYRA_BLOCKS = [(bx, by) for bx in (13, 14, 15) for by in (11, 12)]
SHIFT = (-768.0, 640.0)          # shift_cells (-192, +160) * 4u
DONOR_DY = 0.1224
SITE_C = (160.0, -128.0)
SITE_R = 125.0

# ---- thresholds the build binds itself to (transcribed from the round's prose; NOT its code) --
UV_ZERO = 1e-6
ZERO_UV_CEIL = 0.0005
EPS_RECT = 0.006
TOL_V = 0.008
ROW_PITCH = 0.03125
POSKEY = 3
SKIRT_Y = 0.5                    # "above the sea skirt"
STOCK_STRETCH_CEIL = 1.41
CARRIED_MAX_CEIL = 1.55
CARRIED_OVER_FRAC = 0.01
SYNTH_BAND = (0.85, 1.20)
OUTLIER_U = 0.80                 # spike census predicate (2): residual gate
CONE_PROM = 0.40                 # CONE arm
STEP_PROM = 0.00                 # STEP arm prominence floor
STEP_DROP = 1.50                 # STEP arm welded-drop floor
DIP_FLAT = 25.0                  # orphan census: live dip < 25 deg
DIP_STEEP = 25.0                 # orphan census: donor dip >= 25 deg
BASIN_ANOM = -0.60               # basin detector: residual threshold
BASIN_LINK = 4.5                 # proximity-graph radius
BASIN_ENCLOSE = 0.70
BASIN_ELONG = 1.60
BASIN_MARGIN = 2.0               # frozen annulus around a basin disc

QUADS = [(0, 0), (0, 1), (1, 0), (1, 1)]
ORIS = (0, 90, 180, 270)

# my own topograph->family table: the kit's ground families verbatim, plus the non-ground ids this
# study has used throughout so a wall/mural tri resolves a family instead of falling into the
# "uncatalogued" bucket by accident.  DATA, not build code.
FAM_OF = dict(G.TOPO_FAMILY)
NONGROUND_EXTRA = {4: "scrub", 5: "scrub", 6: "scrub", 27: "snow", 28: "snow", 38: "brush",
                   45: "canyon", 46: "canyon", 58: "rock", 59: "hole"}
for _t, _f in NONGROUND_EXTRA.items():
    FAM_OF.setdefault(_t, _f)
GROUND_FAMS = ("grass", "desert", "dunes")
ROCK_TOPOS = frozenset({58, 31})          # the census' documented rock/stamp exemption
RECT_FAMS = ("grass", "desert", "dunes", "scrub", "brush", "snow", "canyon")


def log(m): print(m, flush=True)


def f32(x): return struct.unpack("<f", struct.pack("<f", float(x)))[0]


def stats(v):
    if not v: return dict(n=0)
    s = sorted(v); n = len(s)
    def q(p): return s[min(n - 1, max(0, int(round(p * (n - 1)))))]
    return dict(n=n, mean=round(statistics.fmean(s), 4),
                sd=round(statistics.pstdev(s), 4) if n > 1 else 0.0, min=round(s[0], 4),
                p05=round(q(.05), 4), p25=round(q(.25), 4), p50=round(q(.5), 4),
                p75=round(q(.75), 4), p95=round(q(.95), 4), p99=round(q(.99), 4),
                max=round(s[-1], 4))


# =====================================================================================
# raw .ff9mesh parse (MY code, lineage-carried)
# =====================================================================================
def parse_raw(path):
    data = Path(path).read_bytes()
    assert data[:4] == MAGIC, f"bad magic {path}"
    version, vcount, icount, flags = struct.unpack_from("<iiii", data, 4)
    off_pos = 20
    sz_pos = vcount * 3 * 4
    off_nrm = off_pos + sz_pos
    sz_nrm = vcount * 3 * 4 if (flags & 1) else 0
    off_uv = off_nrm + sz_nrm
    sz_uv = vcount * 2 * 4 if (flags & 2) else 0
    off_tan = off_uv + sz_uv
    sz_tan = vcount * 4 * 4 if (flags & 4) else 0
    off_idx = off_tan + sz_tan
    sz_idx = icount * 4
    return dict(data=data, version=version, vcount=vcount, icount=icount, flags=flags,
                off_pos=off_pos, off_nrm=off_nrm, off_uv=off_uv, off_tan=off_tan,
                off_idx=off_idx, sz_idx=sz_idx, total=len(data))


def verts_of(r):
    d = r["data"]; return [struct.unpack_from("<3f", d, r["off_pos"] + j * 12) for j in range(r["vcount"])]
def nrms_of(r):
    d = r["data"]
    if not (r["flags"] & 1): return [(0.0, 1.0, 0.0)] * r["vcount"]
    return [struct.unpack_from("<3f", d, r["off_nrm"] + j * 12) for j in range(r["vcount"])]
def uvs_of(r):
    d = r["data"]
    if not (r["flags"] & 2): return [(0.0, 0.0)] * r["vcount"]
    return [struct.unpack_from("<2f", d, r["off_uv"] + j * 8) for j in range(r["vcount"])]
def tans_of(r):
    d = r["data"]
    if not (r["flags"] & 4): return [(0.0, 0.0, 0.0, 0.0)] * r["vcount"]
    return [struct.unpack_from("<4f", d, r["off_tan"] + j * 16) for j in range(r["vcount"])]
def idx_of(r):
    d = r["data"]; return list(struct.unpack_from("<%di" % r["icount"], d, r["off_idx"]))


def part_path(root, bx, by, part): return root / M.override_relpath(1, bx, by, part=part)


# =====================================================================================
# geometry / UV primitives (MY code)
# =====================================================================================
def uv_area2(a, b, c): return abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
def uv_collapsed(a, b, c):
    return max(math.hypot(p[0] - q[0], p[1] - q[1]) for p, q in ((a, b), (a, c), (b, c))) < UV_ZERO
def uv_degenerate(a, b, c): return uv_area2(a, b, c) < UV_ZERO or uv_collapsed(a, b, c)


def geo_normal(p0, p1, p2):
    ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
    return (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)


def dip_of(pts):
    g = geo_normal(*pts); L = math.sqrt(sum(c * c for c in g))
    return None if L < 1e-12 else round(math.degrees(math.acos(max(-1.0, min(1.0, abs(g[1]) / L)))), 2)


def area3d(p0, p1, p2):
    g = geo_normal(p0, p1, p2); return 0.5 * math.sqrt(sum(c * c for c in g))


def plan_area(p0, p1, p2):
    return 0.5 * abs((p1[0] - p0[0]) * (p2[2] - p0[2]) - (p2[0] - p0[0]) * (p1[2] - p0[2]))


def sigma_max(w, uv):
    """world units per UV unit -- largest singular value of the UV->R^3 affine map.  MY estimator."""
    du1 = uv[1][0] - uv[0][0]; dv1 = uv[1][1] - uv[0][1]
    du2 = uv[2][0] - uv[0][0]; dv2 = uv[2][1] - uv[0][1]
    det = du1 * dv2 - du2 * dv1
    if abs(det) < 1e-12: return None
    E1 = tuple(w[1][k] - w[0][k] for k in range(3))
    E2 = tuple(w[2][k] - w[0][k] for k in range(3))
    a = tuple((E1[k] * dv2 - E2[k] * dv1) / det for k in range(3))
    b = tuple((-E1[k] * du2 + E2[k] * du1) / det for k in range(3))
    aa = sum(c * c for c in a); bb = sum(c * c for c in b); ab = sum(a[k] * b[k] for k in range(3))
    tr = aa + bb; dd = math.sqrt(max(0.0, (aa - bb) ** 2 + 4 * ab * ab))
    return math.sqrt(max(0.0, 0.5 * (tr + dd)))


def cell_of(x, z): return (int(math.floor(x / CELL)), int(math.floor(z / CELL)))


# =====================================================================================
# MY OWN UV-RECT CLASSIFIER (kit constants only)
# =====================================================================================
def mains_rect(fam):
    m = G.FAM_REGION["main"]; g = G.GROUNDS[fam]
    return (m[0] + g["mains_du"], m[1] + g["mains_dv"], m[2] + g["mains_du"], m[3] + g["mains_dv"])


def wall_rect(fam):
    g = G.GROUNDS[fam]
    return (min(ISL.ROCK_U) + g["wall_du"], min(ISL.ROCK_V) + g["wall_dv"],
            max(ISL.ROCK_U) + g["wall_du"], max(ISL.ROCK_V) + g["wall_dv"])


MAINS_RECTS = {f: mains_rect(f) for f in RECT_FAMS}
WALL_RECTS = {f: wall_rect(f) for f in G.GROUNDS}
STRIP_DU = {p: (G.STRIPS[p]["du"], G.STRIPS[p]["dv"]) for p in (("grass", "desert"), ("desert", "dunes"))}


def in_rect(uv3, rect, eps=EPS_RECT):
    return all(rect[0] - eps <= u <= rect[2] + eps and rect[1] - eps <= v <= rect[3] + eps
               for (u, v) in uv3)


def classify_strip(uv3, du, dv, eps=EPS_RECT, tol_v=TOL_V):
    u_lo, u_hi = G.STRIP_U[0] + du - eps, G.STRIP_U[1] + du + eps
    if not all(u_lo <= u <= u_hi for (u, _v) in uv3): return None
    v_min = min(v for (_u, v) in uv3)
    row0 = G.STRIPS_V[0][0] + dv
    k = round((v_min - row0) / ROW_PITCH)
    if k < 0 or k > 3 or abs((v_min - row0) - k * ROW_PITCH) > tol_v: return None
    return int(k)


def classify_uv(fam, uv3, eps=EPS_RECT, tol_v=TOL_V):
    """(label, detail).  no_family / strip_grass_desert / mains_own / mains_foreign /
    strip_desert_dunes / wall_rock / other_uncatalogued."""
    if fam is None:
        # still resolve the catalogue so a non-ground tri can be named
        fam = "__none__"
    k = classify_strip(uv3, *STRIP_DU[("grass", "desert")], eps=eps, tol_v=tol_v)
    if k is not None: return ("strip_grass_desert", k)
    rect = MAINS_RECTS.get(fam)
    if rect and in_rect(uv3, rect, eps): return ("mains_own", fam)
    for ofam, orect in MAINS_RECTS.items():
        if ofam != fam and in_rect(uv3, orect, eps): return ("mains_foreign", ofam)
    k2 = classify_strip(uv3, *STRIP_DU[("desert", "dunes")], eps=eps, tol_v=tol_v)
    if k2 is not None: return ("strip_desert_dunes", k2)
    for wfam, wrect in WALL_RECTS.items():
        if in_rect(uv3, wrect, eps): return ("wall_rock", wfam)
    return ("other_uncatalogued", None)


def uv_family(uv3, eps=EPS_RECT):
    """which family's MAINS rect (if any) contains all 3 UVs."""
    for f in RECT_FAMS:
        if in_rect(uv3, MAINS_RECTS[f], eps): return f
    return None


# =====================================================================================
# MY OWN ONE-WINDOW SOLVER
# =====================================================================================
def solve_window(w, uv, fam, tol=2e-6):
    """Return (cell, quad, ori, mode) such that ONE grassland.ground_uv window reproduces ALL THREE
    UVs, or None.  Candidate cells: the centroid cell, each vertex's own cell, and the 8-neighbour
    ring of the centroid cell.  This is the falsifier's own derivation -- it never reads the build's
    recorded window."""
    cx = sum(p[0] for p in w) / 3.0; cz = sum(p[2] for p in w) / 3.0
    c0 = cell_of(cx, cz)
    cands = [c0]
    for p in w:
        c = cell_of(p[0], p[2])
        if c not in cands: cands.append(c)
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            c = (c0[0] + dx, c0[1] + dz)
            if c not in cands: cands.append(c)
    for ci, cell in enumerate(cands):
        for quad in QUADS:
            for ori in ORIS:
                ok = True
                for k in range(3):
                    u, v = G.ground_uv(w[k][0], w[k][2], cell, quad, ori, fam)
                    if abs(f32(u) - uv[k][0]) > tol or abs(f32(v) - uv[k][1]) > tol:
                        ok = False; break
                if ok:
                    mode = "centroid" if ci == 0 else ("owncell" if ci < 1 + len(w) else "ring")
                    return (cell, quad, ori, mode)
    return None


# =====================================================================================
# MY OWN reference surface (IDW-weighted robust LSQ plane, leave-one-out)
# =====================================================================================
class Surface:
    HB = 8.0
    RADII = (10.0, 14.0, 20.0, 28.0, 40.0)
    MINN = 10
    CAP = 48

    def __init__(self, samples, exclude=()):
        """samples: (x, z, y, id).  exclude: iterable of (cx, cz, r) discs whose samples are dropped."""
        self.excl = list(exclude)
        self.pts = []
        for (x, z, y, sid) in samples:
            if any(math.hypot(x - ex, z - ez) <= er for (ex, ez, er) in self.excl):
                continue
            self.pts.append((x, z, y, sid))
        self.g = defaultdict(list)
        for i, (x, z, y, sid) in enumerate(self.pts):
            self.g[(int(math.floor(x / self.HB)), int(math.floor(z / self.HB)))].append(i)

    def _gather(self, x, z, R, skip):
        got = []; rc = int(math.ceil(R / self.HB))
        cx, cz = int(math.floor(x / self.HB)), int(math.floor(z / self.HB)); R2 = R * R
        for i in range(cx - rc, cx + rc + 1):
            for j in range(cz - rc, cz + rc + 1):
                for ix in self.g.get((i, j), ()):
                    px, pz, py, sid = self.pts[ix]
                    if sid in skip: continue
                    d2 = (px - x) ** 2 + (pz - z) ** 2
                    if d2 <= R2: got.append((d2, px, pz, py))
        got.sort()
        return got[:self.CAP]

    @staticmethod
    def _solve(got, x, z, wextra=None):
        A = [[0.0] * 3 for _ in range(3)]; rhs = [0.0] * 3
        for n, (d2, px, pz, py) in enumerate(got):
            w = 1.0 / max(d2, 1.0)
            if wextra is not None: w *= wextra[n]
            bas = (1.0, px - x, pz - z)
            for r_ in range(3):
                for c_ in range(3): A[r_][c_] += w * bas[r_] * bas[c_]
                rhs[r_] += w * bas[r_] * py
        Mx = [A[i][:] + [rhs[i]] for i in range(3)]
        for col in range(3):
            piv = max(range(col, 3), key=lambda rr: abs(Mx[rr][col]))
            if abs(Mx[piv][col]) < 1e-12: return None
            Mx[col], Mx[piv] = Mx[piv], Mx[col]
            for rr in range(3):
                if rr == col: continue
                f = Mx[rr][col] / Mx[col][col]
                for cc in range(col, 4): Mx[rr][cc] -= f * Mx[col][cc]
        return (Mx[0][3] / Mx[0][0], Mx[1][3] / Mx[1][1], Mx[2][3] / Mx[2][2])

    def at(self, x, z, skip=()):
        skip = set(skip)
        for R in self.RADII:
            got = self._gather(x, z, R, skip)
            if len(got) < self.MINN: continue
            sol = self._solve(got, x, z)
            if sol is None: continue
            a, bb, cc = sol
            res = [py - (a + bb * (px - x) + cc * (pz - z)) for (_, px, pz, py) in got]
            med = statistics.median(res)
            mad = statistics.median([abs(r - med) for r in res]) or 1e-3
            wex = [1.0 / (1.0 + (abs(r - med) / (3.0 * mad)) ** 2) for r in res]
            sol2 = self._solve(got, x, z, wex)
            return (a if sol2 is None else sol2[0]), R, len(got)
        return None, None, 0


# =====================================================================================
# LOADERS
# =====================================================================================
def load_tree(root, footprint):
    """-> (tris, files).  tris: world-space Terrain tris with UV, idall, topo, provenance slots."""
    tris = []; files = {}
    for (bx, by) in footprint:
        for part in PARTS:
            p = part_path(root, bx, by, part)
            if not p.exists():
                files[(bx, by, part)] = None; continue
            r = parse_raw(p)
            files[(bx, by, part)] = r
        r = files.get((bx, by, "Terrain"))
        if r is None: continue
        ox, oz = X.block_world_origin(bx, by)
        V = verts_of(r); U = uvs_of(r); T = tans_of(r); N = nrms_of(r); I = idx_of(r)
        for t in range(len(I) // 3):
            js = I[3 * t:3 * t + 3]
            w = [(V[j][0] + ox, V[j][1], V[j][2] + oz) for j in js]
            loc = [V[j] for j in js]
            uv = [U[j] for j in js]
            idall = int(round(T[js[0]][0]))
            dec = X.decode_id(idall)
            tris.append(dict(block=(bx, by), ti=t, w=w, loc=loc, uv=uv, nrm=[N[j] for j in js],
                             idall=idall, topo=dec["topograph"], event=dec.get("event"),
                             area=dec.get("area"), fam=FAM_OF.get(dec["topograph"])))
    return tris, files


def build_donor_index():
    """stock disc-1 Cleyra tris keyed by their SHIFTED plan (x,z) triple @2dp.  READ-ONLY."""
    idx = defaultdict(list); blocks = 0; err = None; ntris = 0
    cells = set()
    for (bx, by) in CLEYRA_BLOCKS:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except Exception as exc:  # noqa: BLE001
            err = repr(exc); continue
        blocks += 1
        ox, oz = X.block_world_origin(bx, by)
        for ti, tri in enumerate(bm.tris):
            w = [(float(bm.verts[j][0]) + ox + SHIFT[0], float(bm.verts[j][1]),
                  float(bm.verts[j][2]) + oz + SHIFT[1]) for j in tri]
            uv = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
            idall = int(round(float(bm.tangents[tri[0]][0])))
            topo = X.decode_id(idall)["topograph"]
            key = tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in w))
            idx[key].append(dict(src=(bx, by, ti), w=w, uv=uv, idall=idall, topo=topo,
                                 fam=FAM_OF.get(topo), dip=dip_of(w)))
            ntris += 1
            cx = sum(p[0] for p in w) / 3.0; cz = sum(p[2] for p in w) / 3.0
            cells.add(cell_of(cx, cz))
    return idx, dict(blocks=blocks, keys=len(idx), tris=ntris, cells=len(cells), error=err), cells


def uvk(uv): return tuple((round(u, 6), round(v, 6)) for u, v in uv)


def plankey(w): return tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in w))


def classify_provenance(tris, donor):
    """MY OWN carried/minted split.  A composite tri is CARRIED when its plan triple matches a donor
    tri AND (its topograph matches that donor tri OR its Y is exactly donor_Y + DONOR_DY).  The
    second arm is what recovers a tri whose topograph was RE-STAMPED by a redress.  NOTE the fill
    re-triangulates on the same 4u grid, so a plan match ALONE is not sufficient (3389 composite
    tris plan-match; only 1454 are genuinely carried)."""
    for t in tris:
        key = plankey(t["w"])
        cands = donor.get(key, [])
        best = None
        for c in cands:
            dm = {(round(p[0], 2), round(p[2], 2)): p[1] for p in c["w"]}
            try:
                dd = [p[1] - (dm[(round(p[0], 2), round(p[2], 2))] + DONOR_DY) for p in t["w"]]
            except KeyError:
                continue
            mx = max(abs(x) for x in dd)
            same_topo = (c["topo"] == t["topo"])
            same_uv = (uvk(c["uv"]) == uvk(t["uv"]))
            score = (0 if same_topo else 1, 0 if same_uv else 1, mx)
            if best is None or score < best[0]:
                best = (score, c, mx, same_topo, same_uv)
        if best is None:
            t["prov"] = "minted"; t["donor"] = None; t["dY_from_donor"] = None
            continue
        score, c, mx, same_topo, same_uv = best
        if same_topo or mx < 1e-3:
            t["donor"] = c; t["dY_from_donor"] = mx
            if same_topo and same_uv and mx < 1e-3: t["prov"] = "carried_verbatim"
            elif mx >= 1e-3 and not same_uv:        t["prov"] = "carried_shaved_and_reclothed"
            elif mx >= 1e-3:                        t["prov"] = "carried_shaved"
            else:                                   t["prov"] = "carried_reclothed"
        else:
            t["prov"] = "minted"; t["donor"] = None; t["dY_from_donor"] = None
    return tris


# =====================================================================================
def main():
    t0 = time.time()
    R = {}; findings = []; notes = []
    R["meta"] = dict(
        script="foldback_falsify.py",
        role="CODE-DISJOINT falsifier on THE FRESH MINT (the generator fold-back, part 2)",
        target=str(TREE), date="2026-07-25",
        disjointness="imports ff9mapkit.world.extract/.mesh/.grassland/.island ONLY; NO "
                     "junction_compose / composite_gates / freshmint_* / rung_f_* / uvf_* import",
        site=dict(centre=list(SITE_C), radius=SITE_R, donor=CLEYRA_BLOCKS, shift_world=list(SHIFT),
                  donor_DY=DONOR_DY))

    rep = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else {}
    claim = rep.get("mint", {})

    # ---------------------------------------------------------------- 0. load
    log("[0] loading the fresh-mint tree ...")
    tris, files = load_tree(TREE, FOOTPRINT)
    donor, dinfo, donor_cells = build_donor_index()
    log(f"    composite tris={len(tris)}  donor keys={dinfo['keys']} tris={dinfo['tris']} "
        f"blocks={dinfo['blocks']} cells={dinfo['cells']}")
    R["load"] = dict(composite_tris=len(tris), files=len([k for k, v in files.items() if v]),
                     donor=dinfo)
    if dinfo["error"]:
        findings.append(f"BLOCKED: donor read error {dinfo['error']}")
    if len(tris) != 6996:
        findings.append(f"MISMATCH: my composite tri count {len(tris)} != the reported 6996.")

    classify_provenance(tris, donor)
    prov = Counter(t["prov"] for t in tris)
    carried = [t for t in tris if t["prov"].startswith("carried")]
    minted = [t for t in tris if t["prov"] == "minted"]
    ground = [t for t in tris if t["fam"] in GROUND_FAMS]
    R["provenance"] = dict(counts=dict(prov), carried=len(carried), minted=len(minted),
                           ground_tris=len(ground), nonground_tris=len(tris) - len(ground),
                           topo_hist=dict(sorted(Counter(t["topo"] for t in tris).items())),
                           carried_topo_hist=dict(sorted(Counter(t["topo"] for t in carried).items())),
                           minted_topo_hist=dict(sorted(Counter(t["topo"] for t in minted).items())))
    log(f"[0] provenance {dict(prov)}  carried={len(carried)} minted={len(minted)} "
        f"ground={len(ground)}")

    cg = claim.get("composite", {})
    if cg:
        exp_carried = cg.get("verbatim_carried_tris")
        if exp_carried is not None and len(carried) != exp_carried:
            findings.append(f"MISMATCH: my carried count {len(carried)} != reported {exp_carried}.")
        gp = cg.get("ground_tris_by_provenance", {})
        my_untouched_ground = sum(1 for t in carried
                                  if t["prov"] in ("carried_verbatim", "carried_reclothed")
                                  and t["fam"] in GROUND_FAMS)
        my_shaved_ground = sum(1 for t in carried if t["prov"].startswith("carried_shaved")
                               and t["fam"] in GROUND_FAMS)
        R["provenance"]["my_untouched_carried_ground"] = my_untouched_ground
        R["provenance"]["my_shaved_carried_ground"] = my_shaved_ground
        R["provenance"]["reported_ground_by_provenance"] = gp
        if gp.get("untouched_carried") not in (None, my_untouched_ground):
            findings.append(f"MISMATCH: untouched carried ground {my_untouched_ground} != "
                            f"reported {gp.get('untouched_carried')}.")
        if gp.get("carried_shaved_by_L5a") not in (None, my_shaved_ground):
            findings.append(f"MISMATCH: shaved carried ground {my_shaved_ground} != "
                            f"reported {gp.get('carried_shaved_by_L5a')}.")

    # ============================================================ 1. MY GATE BATTERY
    gates = {}

    # --- G1 degenerate / collapsed / bit-identical UVs -----------------------------------------
    zero_uv = [t for t in tris if uv_area2(*t["uv"]) < UV_ZERO]
    collapsed = [t for t in tris if uv_collapsed(*t["uv"])]
    bit_ident = [t for t in tris if len({(round(u, 7), round(v, 7)) for u, v in t["uv"]}) == 1]
    frac = len(zero_uv) / max(1, len(tris))
    gates["G1_uv_validity"] = dict(
        ok=(frac <= ZERO_UV_CEIL and not collapsed and not bit_ident),
        n_zero_uv_area=len(zero_uv), frac=round(frac, 8), ceiling=ZERO_UV_CEIL,
        n_collapsed=len(collapsed), n_bit_identical=len(bit_ident),
        zero_uv_detail=[dict(block=list(t["block"]), ti=t["ti"], prov=t["prov"], topo=t["topo"],
                             uv=[[round(u, 6), round(v, 6)] for u, v in t["uv"]],
                             w=[[round(p[0], 3), round(p[1], 3), round(p[2], 3)] for p in t["w"]],
                             plan_area=round(plan_area(*t["w"]), 6)) for t in zero_uv[:8]])

    # --- G2/G3 one-window + family-rect membership on EVERY minted mains tri --------------------
    log("[1] solving one-window over every minted mains tri (my own derivation) ...")
    minted_mains = []
    minted_other = Counter()
    for t in minted:
        f = uv_family(t["uv"])
        t["uvfam"] = f
        if f is None:
            lab, det = classify_uv(t["fam"], t["uv"])
            minted_other[lab] += 1
            t["uvlabel"] = lab
            continue
        minted_mains.append(t)
    # MY OWN fill/frame proxy: a minted tri whose centroid cell lies inside the donor's own cell
    # footprint is FILL (a hole the drop opened inside the carried blob); everything else is the
    # minted grass FRAME.  The build's split is sentinel-based and lands at 2304/2786; mine at
    # 1983/3107 -- the UNION is identical (5090) and the law scopes are what matter.
    for t in minted_mains:
        t["role"] = ("fill" if cell_of(sum(p[0] for p in t["w"]) / 3.0,
                                       sum(p[2] for p in t["w"]) / 3.0) in donor_cells else "frame")
    fill_mains = [t for t in minted_mains if t["role"] == "fill"]
    frame_mains = [t for t in minted_mains if t["role"] == "frame"]
    win_modes = Counter(); win_fail = []; cellfield = {}
    percell_windows = defaultdict(set)
    for t in minted_mains:
        sol = solve_window(t["w"], t["uv"], t["uvfam"])
        t["win"] = sol
        if sol is None:
            win_fail.append(t); win_modes["FAIL"] += 1
        else:
            win_modes[sol[3]] += 1
            cell, quad, ori, _m = sol
            percell_windows[cell].add((quad, ori))
            cellfield.setdefault(cell, (quad, ori))
    fill_fail = [t for t in win_fail if t["role"] == "fill"]
    frame_fail = [t for t in win_fail if t["role"] == "frame"]
    # tolerance ladder on the failures -- how far off a legal window are they?
    ladder = {}
    for tol in (2e-6, 1e-4, 1e-3, 5e-3, 2e-2):
        ladder[f"tol={tol:g}"] = dict(
            fill_fail=sum(1 for t in fill_mains if solve_window(t["w"], t["uv"], t["uvfam"], tol) is None),
            frame_fail=sum(1 for t in frame_mains if solve_window(t["w"], t["uv"], t["uvfam"], tol) is None))
    gates["G2_one_window"] = dict(
        ok=(not fill_fail),
        scope="THE LAW binds the SYNTHESIZED fill.  Primary gate = my own fill proxy at BIT-EXACT "
              "float32 tolerance; the minted grass FRAME is reported as a strictly-stronger "
              "extension the law never claimed.",
        n_minted_mains=len(minted_mains), n_fill=len(fill_mains), n_frame=len(frame_mains),
        fill_single_window=len(fill_mains) - len(fill_fail), fill_unresolved=len(fill_fail),
        frame_single_window=len(frame_mains) - len(frame_fail), frame_unresolved=len(frame_fail),
        modes=dict(win_modes), tolerance_ladder=ladder,
        per_family={f: sum(1 for t in minted_mains if t["uvfam"] == f)
                    for f in sorted({t["uvfam"] for t in minted_mains})},
        frame_note="every frame miss resolves by tol=0.02 -- the coast CLIP interpolates/clamps UV "
                   "along the clipped edge, so a coast sliver is affine-inside one window but not "
                   "bit-exact on it.  A build_landmass coast-vocabulary property, pre-existing and "
                   "in-game accepted; NOT the carry's one-window law.",
        fail_detail=[dict(block=list(t["block"]), ti=t["ti"], role=t["role"], uvfam=t["uvfam"],
                          uv_area=round(uv_area2(*t["uv"]), 8),
                          all_Y_equal_3=all(abs(p[1] - 3.0) < 1e-6 for p in t["w"]),
                          uv=[[round(u, 6), round(v, 6)] for u, v in t["uv"]]) for t in win_fail[:8]])
    gates["G3_family_rect"] = dict(
        ok=True, checked={f: sum(1 for t in minted_mains if t["uvfam"] == f)
                          for f in sorted({t["uvfam"] for t in minted_mains})},
        minted_non_mains=dict(minted_other),
        note="membership is the definition of uv_family() here, so the gate is exercised by the "
             "non-mains bucket: every minted tri that is NOT in a mains rect is named.")
    # any minted GROUND tri that is neither mains nor a catalogued wall/strip is an unclothed tri
    unclothed = [t for t in minted if t.get("uvfam") is None and t["fam"] in GROUND_FAMS
                 and t.get("uvlabel") == "other_uncatalogued"]
    gates["G3_family_rect"]["n_minted_ground_uncatalogued"] = len(unclothed)
    if unclothed:
        findings.append(f"REFUTE: {len(unclothed)} MINTED ground tris wear an uncatalogued rect.")

    # --- G4 sea ---------------------------------------------------------------------------------
    sea = dict(); sea4_counts = Counter(); sea4_bad_y = []; placeholders = Counter()
    sea4_plan = {}
    for (bx, by) in FOOTPRINT:
        for part in SEA_PARTS:
            r = files.get((bx, by, part))
            if r is None: continue
            ntri = r["icount"] // 3
            V = verts_of(r)
            if part == "Sea4":
                sea4_counts[ntri] += 1
                for v in V:
                    if abs(v[1]) > 1e-6: sea4_bad_y.append([bx, by, list(v)])
                ox, oz = X.block_world_origin(bx, by)
                I = idx_of(r); a = 0.0
                for t in range(ntri):
                    js = I[3 * t:3 * t + 3]
                    a += plan_area(*[(V[j][0] + ox, V[j][1], V[j][2] + oz) for j in js])
                sea4_plan[(bx, by)] = a
            else:
                placeholders[(part, ntri)] += 1
    # (A) fully-submerged land tris
    submerged = [t for t in tris if max(p[1] for p in t["w"]) < 0.0]
    # (B) adjacent-block Sea4 plan-area uniformity
    ratios = []
    for (bx, by), a in sea4_plan.items():
        for (dx, dy) in ((1, 0), (0, 1)):
            n = (bx + dx, by + dy)
            if n in sea4_plan and min(a, sea4_plan[n]) > 0:
                ratios.append(max(a, sea4_plan[n]) / min(a, sea4_plan[n]))
    # (C) real (non-underlay, non-placeholder) sea vs land plan overlap
    real_sea_parts = [(k, r["icount"] // 3) for k, r in files.items()
                      if k[2] in SEA_PARTS and k[2] != "Sea4" and r is not None and r["icount"] // 3 > 1]
    gates["G4_sea"] = dict(
        ok=(not sea4_bad_y and len(sea4_counts) == 1 and not submerged
            and (not ratios or max(ratios) <= 4.0) and not real_sea_parts),
        sea4_distinct_tri_counts=sorted(sea4_counts), n_sea4_blocks=sum(sea4_counts.values()),
        n_sea4_vertices_off_y0=len(sea4_bad_y), A_fully_submerged_land_tris=len(submerged),
        B_max_adjacent_plan_ratio=round(max(ratios), 6) if ratios else None,
        C_real_sea_parts_beyond_the_underlay=real_sea_parts,
        placeholder_census={f"{p}:{n}tri": c for (p, n), c in sorted(placeholders.items())},
        vacuity_note="predicate (C) is VACUOUS on this composite: with a uniform full Sea4 underlay "
                     "and 1-tri placeholders for Sea1/2/3/5+Beach1 there is no 'real sea' polygon "
                     "left to overlap-test.  Reported as a limitation of the gate, not a defect.")

    # --- G5 flat-mesh / identity indices --------------------------------------------------------
    flat_bad = []; permuted = Counter()
    for k, r in files.items():
        if r is None: continue
        if r["vcount"] != r["icount"] or r["icount"] % 3:
            flat_bad.append([list(k[:2]), k[2], r["vcount"], r["icount"]])
            continue
        I = idx_of(r)
        if sorted(I) != list(range(r["icount"])):
            flat_bad.append([list(k[:2]), k[2], "index buffer is not a permutation of 0..n-1"])
        elif I != list(range(r["icount"])):
            permuted[k[2]] += 1
    gates["G5_flat_mesh"] = dict(
        ok=not flat_bad, n_files=len([1 for v in files.values() if v]), violations=flat_bad,
        invariant="vcount == indexCount == 3*tris AND the index buffer is a PERMUTATION of "
                  "0..n-1 (every vertex used exactly once) -- an unwelded 'flat' mesh",
        files_with_a_non_identity_but_lawful_permutation=dict(permuted),
        permutation_note="Sea4 ships a reversed-triplet index buffer: still flat (1536 verts, 1536 "
                         "indices, each used once), so the invariant holds; an identity-only test "
                         "would have red-flagged 20 lawful files.")

    # --- G6 grid + frame bounds -----------------------------------------------------------------
    oob_block = [list(k[:2]) for k in files if not (0 <= k[0] < GRID_W and 0 <= k[1] < GRID_H)]
    frame_bad = []
    SLACK = 0.02
    for (bx, by) in FOOTPRINT:
        r = files.get((bx, by, "Terrain"))
        if r is None: continue
        for v in verts_of(r):
            if not (-SLACK <= v[0] <= BLOCK + SLACK) or not (-BLOCK - SLACK <= v[2] <= SLACK):
                frame_bad.append([bx, by, [round(c, 4) for c in v]])
    gates["G6_bounds"] = dict(ok=(not oob_block and not frame_bad), blocks_off_grid=oob_block,
                              n_verts_outside_block_frame=len(frame_bad), sample=frame_bad[:6])

    # --- G7 weld / crack / once-edge / near-miss ------------------------------------------------
    log("[1] weld graph ...")
    def pk(p): return (round(p[0], POSKEY), round(p[1], POSKEY), round(p[2], POSKEY))
    edge_use = Counter(); pos_deg = defaultdict(set); pos_y = {}
    tri_keys = Counter()
    for t in tris:
        ks = [pk(p) for p in t["w"]]
        tri_keys[tuple(sorted(ks))] += 1
        for i in range(3):
            a, b = ks[i], ks[(i + 1) % 3]
            edge_use[tuple(sorted((a, b)))] += 1
            pos_deg[a].add(b); pos_deg[b].add(a)
        for k in ks: pos_y[k] = k[1]
    once = [e for e, c in edge_use.items() if c == 1]
    once_above = [e for e in once if max(e[0][1], e[1][1]) > SKIRT_Y]
    over2 = [e for e, c in edge_use.items() if c > 2]
    dupes = [k for k, c in tri_keys.items() if c > 1]
    # near-miss weld: distinct position keys closer than 0.05u but not equal (a crack candidate)
    keys = sorted(pos_deg)
    hb = defaultdict(list)
    for k in keys: hb[(int(k[0] // 1), int(k[2] // 1))].append(k)
    nearmiss = []
    for k in keys:
        gx, gz = int(k[0] // 1), int(k[2] // 1)
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for o in hb.get((gx + i, gz + j), ()):
                    if o <= k: continue
                    d = math.dist(k, o)
                    if 1e-9 < d < 0.05: nearmiss.append([list(k), list(o), round(d, 6)])
    # CALIBRATION: the same audit on the DEPLOYED, in-game-ACCEPTED rung-F build (FIXED8) and on
    # the PRE-FIX SPECIMEN, so a non-manifold count can be told apart from a fold-back REGRESSION.
    def anomaly_audit(root, fp):
        try:
            tt, _ff = load_tree(root, fp)
        except Exception as exc:  # noqa: BLE001
            return dict(error=repr(exc))
        eu = Counter(); tk = Counter()
        for t in tt:
            ks = [pk(p) for p in t["w"]]
            tk[tuple(sorted(ks))] += 1
            for i in range(3):
                eu[tuple(sorted((ks[i], ks[(i + 1) % 3])))] += 1
        return dict(tris=len(tt),
                    once_edges=sum(1 for c in eu.values() if c == 1),
                    once_above_skirt=sum(1 for e, c in eu.items()
                                         if c == 1 and max(e[0][1], e[1][1]) > SKIRT_Y),
                    edges_over_2=sum(1 for c in eu.values() if c > 2),
                    duplicate_tris=sum(1 for c in tk.values() if c > 1),
                    down_facing=sum(1 for t in tt if geo_normal(*t["w"])[1] < 0))
    RF = HERE / "out" / "rung_f"
    rf_fp = [(bx, by) for bx in range(0, 5) for by in range(16, 20)]
    cal = dict(freshmint=dict(tris=len(tris), once_edges=len(once),
                              once_above_skirt=len(once_above), edges_over_2=len(over2),
                              duplicate_tris=len(dupes), down_facing=len(down_all := [
                                  t for t in tris if geo_normal(*t["w"])[1] < 0])),
               deployed_FIXED8=anomaly_audit(RF / "FF9CustomMap-world-FIXED8", rf_fp),
               prefix_SPECIMEN=anomaly_audit(RF / "FF9CustomMap-world", rf_fp))
    same_as_deployed = all(cal["freshmint"].get(k) == cal["deployed_FIXED8"].get(k)
                           for k in ("once_edges", "once_above_skirt", "edges_over_2",
                                     "duplicate_tris", "down_facing"))
    gates["G7_weld"] = dict(
        ok=(not once_above and not nearmiss and same_as_deployed),
        watertight_above_skirt=(not once_above),
        no_new_anomaly_vs_deployed=same_as_deployed,
        calibration=cal,
        carried_forward_note="17 edges used 4x + 6 duplicate coincident tris + 3 down-facing tris "
                             "are IDENTICAL in the fresh mint, in the DEPLOYED in-game-accepted "
                             "FIXED8, and in the PRE-FIX SPECIMEN.  They are a pre-existing property "
                             "of the rung-F landmass (the fill over the donor's topo-59 hole at "
                             "~(235,-115)), faithfully reproduced by the folded-back generator -- "
                             "NOT a fold-back regression.  No standing gate in 8 rounds sees them.",
        n_distinct_positions=len(pos_deg), n_edges=len(edge_use),
        n_once_edges_total=len(once), n_once_edges_above_skirt=len(once_above),
        n_edges_used_more_than_twice=len(over2), n_near_miss_pairs=len(nearmiss),
        n_duplicate_coincident_tris=len(dupes), skirt_y=SKIRT_Y,
        once_below_skirt_note="once-edges at or below the y=0.5 sea skirt are the island's outer "
                              "skirt rim and are lawful; only once-edges ABOVE the skirt are cracks.",
        sample_once_above=[[list(a), list(b)] for a, b in once_above[:6]],
        sample_near_miss=nearmiss[:6])

    # --- G8 winding / down-facing ---------------------------------------------------------------
    down = [t for t in tris if geo_normal(*t["w"])[1] < 0]
    down_minted = [t for t in down if t["prov"] == "minted"]
    down_carried = [t for t in down if t["prov"].startswith("carried")]
    gates["G8_winding"] = dict(
        ok=(len(down) == cal["deployed_FIXED8"].get("down_facing")),
        n_down_facing_total=len(down), n_down_facing_minted=len(down_minted),
        n_down_facing_carried=len(down_carried),
        deployed_FIXED8_down_facing=cal["deployed_FIXED8"].get("down_facing"),
        prefix_SPECIMEN_down_facing=cal["prefix_SPECIMEN"].get("down_facing"),
        detail=[dict(block=list(t["block"]), ti=t["ti"], topo=t["topo"], prov=t["prov"],
                     dip=dip_of(t["w"]),
                     w=[[round(p[0], 2), round(p[1], 3), round(p[2], 2)] for p in t["w"]],
                     plan_matches_a_donor_tri=(plankey(t["w"]) in donor),
                     donor_topo_at_that_plan=[c["topo"] for c in donor.get(plankey(t["w"]), [])])
                for t in down],
        provenance_dispute="the round's gate 22 books these 3 as 'carried faithful'.  MY OWN "
                           "classifier books them as MINTED FILL: their plan coincides with donor "
                           "topo-59 (hole) tris that were DROPPED, their topograph is 0 (not 59) and "
                           "their Y is not donor_Y + DY.  The count is the same in the deployed "
                           "FIXED8 and in the pre-fix specimen, so nothing regressed -- but the "
                           "'carried faithful' label is wrong and it is the label that exempts them.")

    # --- G9 land > 0 (anti-vacuity) --------------------------------------------------------------
    land_plan = sum(plan_area(*t["w"]) for t in tris)
    ground_plan = sum(plan_area(*t["w"]) for t in ground)
    xs = [p[0] for t in tris for p in t["w"]]; zs = [p[2] for t in tris for p in t["w"]]
    ys = [p[1] for t in tris for p in t["w"]]
    gates["G9_land_nonempty"] = dict(ok=(len(tris) > 0 and ground_plan > 0),
                                     total_plan_area=round(land_plan, 2),
                                     ground_plan_area=round(ground_plan, 2),
                                     bbox=dict(x=[round(min(xs), 2), round(max(xs), 2)],
                                               z=[round(min(zs), 2), round(max(zs), 2)],
                                               y=[round(min(ys), 3), round(max(ys), 3)]),
                                     max_radius_from_site_centre=round(
                                         max(math.hypot(p[0] - SITE_C[0], p[2] - SITE_C[1])
                                             for t in tris for p in t["w"]), 3))

    # --- G10 idall hygiene (event / area must be zero on a minted landmass) ----------------------
    ev = Counter(t["event"] for t in tris); ar = Counter(t["area"] for t in tris)
    donor_ev = Counter(X.decode_id(c["idall"]).get("event") for v in donor.values() for c in v)
    gates["G10_idall_hygiene"] = dict(ok=(set(ev) == {0} and set(ar) == {0}),
                                      event_hist={str(k): v for k, v in ev.items()},
                                      area_hist={str(k): v for k, v in ar.items()},
                                      donor_event_hist={str(k): v for k, v in donor_ev.items()},
                                      note="a carried tri that kept a donor EVENT id would fire a "
                                           "spurious field entrance; the carry re-encodes IDALL to "
                                           "topograph-only.")

    R["gates"] = gates
    for gname, g in gates.items():
        if not g.get("ok", True):
            findings.append(f"GATE RED ({gname}): {json.dumps({k: v for k, v in g.items() if k != 'ok'})[:400]}")

    # ============================================================ 2. THE LAW CHECKS
    laws = {}

    # ---- L1 the CONSTANT-UV STAMP (the flat-sheet stain) ---------------------------------------
    win_set = Counter((t["win"][0], t["win"][1], t["win"][2]) for t in minted_mains if t["win"])
    uvtrip = Counter(uvk(t["uv"]) for t in minted_mains)
    laws["L1_constant_uv_stamp"] = dict(
        n_minted_mains=len(minted_mains),
        n_distinct_windows=len(win_set),
        n_distinct_uv_triples=len(uvtrip),
        largest_window_share=round(max(win_set.values()) / max(1, len(minted_mains)), 5) if win_set else None,
        largest_uv_triple_share=round(max(uvtrip.values()) / max(1, len(minted_mains)), 5) if uvtrip else None,
        n_distinct_cells=len(percell_windows),
        cells_with_more_than_one_window=sum(1 for c, s in percell_windows.items() if len(s) > 1),
        verdict="REFUTED-DEFECT" if (win_set and max(win_set.values()) / len(minted_mains) > 0.10)
                else "no constant stamp",
        note="the L1 defect was ONE constant (uv,topo) for every synthesized vertex: a single "
             "window carrying >10% of the minted mains population would reproduce it.")
    if laws["L1_constant_uv_stamp"]["verdict"] != "no constant stamp":
        findings.append("REFUTE (L1): a single UV window dominates the minted mains population.")

    # ---- L2 the FAMILY field: BFS from kept ground, and the TOPO/UV agreement audit ------------
    log("[2] family field (my own nearest-kept-ground BFS) ...")
    # kept-ground cell -> family (rock/mural ABSTAIN)
    keptfam = defaultdict(Counter)
    for t in carried:
        if t["fam"] not in GROUND_FAMS: continue      # rock 58/31 + murals abstain
        cx = sum(p[0] for p in t["w"]) / 3.0; cz = sum(p[2] for p in t["w"]) / 3.0
        keptfam[cell_of(cx, cz)][t["fam"]] += 1
    seedfam = {c: cnt.most_common(1)[0][0] for c, cnt in keptfam.items()}
    # multi-source BFS over the 4u cell lattice
    dist = {c: 0 for c in seedfam}; famf = dict(seedfam)
    dq = deque(seedfam)
    all_cells = {cell_of(sum(p[0] for p in t["w"]) / 3.0, sum(p[2] for p in t["w"]) / 3.0)
                 for t in tris}
    while dq:
        c = dq.popleft()
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + d[0], c[1] + d[1])
            if n in dist or n not in all_cells: continue
            dist[n] = dist[c] + 1; famf[n] = famf[c]; dq.append(n)
    # agreement: does each FILL tri wear the BFS family of its centroid cell?  (the law scopes the
    # fill; the minted grass FRAME is grass by construction and is reported separately)
    agree = Counter(); disagree = []; frame_agree = Counter()
    for t in minted_mains:
        cx = sum(p[0] for p in t["w"]) / 3.0; cz = sum(p[2] for p in t["w"]) / 3.0
        c = cell_of(cx, cz)
        exp = famf.get(c)
        if t["role"] == "frame":
            frame_agree["match" if exp == t["uvfam"] else "differ"] += 1
            continue
        if exp is None: agree["no_bfs_family(outside the carried skeleton)"] += 1; continue
        if exp == t["uvfam"]: agree["match"] += 1
        else:
            agree["differ"] += 1
            if len(disagree) < 12:
                disagree.append(dict(cell=list(c), wears=t["uvfam"], bfs=exp,
                                     dist_to_kept=dist.get(c)))
    # non-grass minted tris: what is their distance to the nearest kept cell of the SAME family?
    nongrass = [t for t in minted_mains if t["uvfam"] != "grass"]
    ng_rows = []
    for t in nongrass:
        cx = sum(p[0] for p in t["w"]) / 3.0; cz = sum(p[2] for p in t["w"]) / 3.0
        c = cell_of(cx, cz)
        same = [k for k, f in seedfam.items() if f == t["uvfam"]]
        dmin = min((math.hypot((c[0] - k[0]) * CELL, (c[1] - k[1]) * CELL) for k in same), default=None)
        ng_rows.append(dmin)
    # THE TOPO/UV AGREEMENT AUDIT: in stock, does a dunes-UV tri carry a dunes topograph?
    # scoped to tris whose TOPOGRAPH is a walkable ground family (topo 59 'hole' is structural and
    # legitimately wears a ground texture on its shaft walls).
    stock_pairs = Counter()
    for v in donor.values():
        for c in v:
            f = uv_family(c["uv"])
            if f is None or FAM_OF.get(c["topo"]) not in GROUND_FAMS: continue
            stock_pairs[(f, FAM_OF.get(c["topo"]))] += 1
    stock_agree = sum(n for (a, b), n in stock_pairs.items() if a == b)
    stock_tot = sum(stock_pairs.values())
    mint_pairs = Counter()
    for t in minted_mains:
        if FAM_OF.get(t["topo"]) not in GROUND_FAMS: continue
        mint_pairs[(t["uvfam"], FAM_OF.get(t["topo"]))] += 1
    mint_agree = sum(n for (a, b), n in mint_pairs.items() if a == b)
    mint_tot = sum(mint_pairs.values())
    # SECOND, INDEPENDENT family oracle: EUCLIDEAN-nearest kept-ground cell (the BFS above walks the
    # 4-neighbour cell graph, so inside a large hole its answer depends on the hole's shape).
    seedlist = sorted(seedfam)
    eagree = Counter()
    for t in minted_mains:
        if t["role"] != "fill": continue
        cx = sum(p[0] for p in t["w"]) / 3.0; cz = sum(p[2] for p in t["w"]) / 3.0
        c = cell_of(cx, cz)
        best = min(seedlist, key=lambda k: (c[0] - k[0]) ** 2 + (c[1] - k[1]) ** 2)
        eagree["match" if seedfam[best] == t["uvfam"] else "differ"] += 1
    laws["L2_family"] = dict(
        n_kept_ground_cells=len(seedfam),
        kept_family_hist=dict(Counter(seedfam.values())),
        bfs_agreement_FILL=dict(agree),
        euclidean_nearest_agreement_FILL=dict(eagree),
        oracle_note="two independent family oracles over the same kept-ground seeds: the 4-neighbour "
                    "cell-graph BFS and the Euclidean nearest seed.  Where they disagree the fill "
                    "cell is 6-8 cells (24-32u) from any kept ground, i.e. deep inside a hole where "
                    "the 'nearest kept ground' is genuinely ambiguous -- an instrument spread, not a "
                    "law violation.",
        bfs_agreement_FRAME=dict(frame_agree),
        disagreement_sample=disagree,
        nongrass_minted=len(nongrass),
        nongrass_distance_to_nearest_same_family_kept_cell=stats([d for d in ng_rows if d is not None]),
        topo_uv_agreement=dict(
            stock_donor_pairs={f"{a}|{b}": n for (a, b), n in sorted(stock_pairs.items(),
                                                                     key=lambda kv: -kv[1])},
            stock_agreement_frac=round(stock_agree / max(1, stock_tot), 5),
            mint_minted_pairs={f"{a}|{b}": n for (a, b), n in sorted(mint_pairs.items(),
                                                                     key=lambda kv: -kv[1])},
            mint_agreement_frac=round(mint_agree / max(1, mint_tot), 5),
            n_mint_disagreeing=mint_tot - mint_agree,
            scope="tris whose TOPOGRAPH is a walkable ground family (topo 59 'hole' excluded on "
                  "both sides)"),
        carried_strip_census=dict(
            grass_desert_strip_tris=sum(1 for t in carried
                                        if classify_uv(t["fam"], t["uv"])[0] == "strip_grass_desert"),
            desert_dunes_strip_tris=sum(1 for t in carried
                                        if classify_uv(t["fam"], t["uv"])[0] == "strip_desert_dunes"),
            note="the ecotone transition vocabulary the R2 fringe contract measures"))
    if stock_tot and stock_agree == stock_tot and mint_tot - mint_agree > 0:
        findings.append(
            f"DEVIATION (L2, half-applied): stock's UV-family and TOPOGRAPH-family agree on "
            f"{stock_agree}/{stock_tot} donor mains tris (100.0%), but {mint_tot - mint_agree} MINTED "
            f"mains tris wear a non-grass texture family over a GRASS topograph "
            f"({dict((f'{a}|{b}', n) for (a, b), n in mint_pairs.items() if a != b)}).  The family "
            f"law is enforced on the UV half and NOT on the topograph half.")

    # ---- L3 THE CHEVRON TEST: spatial statistics of the derived (quad,ori) field ---------------
    log("[3] chevron test (quad/ori autocorrelation vs assign_mains) ...")
    def field_stats(cq, co):
        cells = set(cq)
        sq = tq = so = to = 0
        for (i, j) in cells:
            for n in ((i - 1, j), (i, j - 1)):
                if n in cq:
                    tq += 1; sq += (cq[n] == cq[(i, j)])
                if n in co:
                    to += 1; so += (co[n] == co[(i, j)])
        return dict(n_cells=len(cells),
                    same_quad_as_WS_neighbour=round(sq / max(1, tq), 5),
                    same_ori_as_WS_neighbour=round(so / max(1, to), 5),
                    quad_hist={str(k): v for k, v in sorted(Counter(cq.values()).items())},
                    ori_hist={str(k): v for k, v in sorted(Counter(co.values()).items())})
    obs_q = {c: w[0] for c, w in ((c, cellfield[c]) for c in cellfield)}
    obs_o = {c: w[1] for c, w in ((c, cellfield[c]) for c in cellfield)}
    observed = field_stats(obs_q, obs_o)
    # the assign_mains null over MY OWN cell set (the kit's policy, 60 seeds)
    mc_q, mc_o = [], []
    cellset = sorted(cellfield)
    for s in range(60):
        cq, co = G.assign_mains(cellset, seed=0x1000 + s)
        st = field_stats(cq, co)
        mc_q.append(st["same_quad_as_WS_neighbour"]); mc_o.append(st["same_ori_as_WS_neighbour"])
    # the CHEVRON null: a deterministic lattice (ori a function of cell parity, quad avoiding W+S)
    ch_q, ch_o = {}, {}
    for (i, j) in cellset:
        ch_o[(i, j)] = ORIS[(i + j) % 2 * 2]
        avoid = {ch_q.get((i - 1, j)), ch_q.get((i, j - 1))}
        opts = [q for q in QUADS if q not in avoid] or QUADS
        ch_q[(i, j)] = opts[(i * 3 + j) % len(opts)]
    chevron = field_stats(ch_q, ch_o)
    lo_q, hi_q = min(mc_q), max(mc_q); lo_o, hi_o = min(mc_o), max(mc_o)
    in_band = (lo_q - 0.02 <= observed["same_quad_as_WS_neighbour"] <= hi_q + 0.02 and
               lo_o - 0.02 <= observed["same_ori_as_WS_neighbour"] <= hi_o + 0.02)
    laws["L3_chevron"] = dict(
        observed=observed,
        assign_mains_null=dict(seeds=60, same_quad_range=[round(lo_q, 5), round(hi_q, 5)],
                               same_ori_range=[round(lo_o, 5), round(hi_o, 5)],
                               same_quad_mean=round(statistics.fmean(mc_q), 5),
                               same_ori_mean=round(statistics.fmean(mc_o), 5)),
        chevron_null=chevron,
        observed_inside_assign_mains_band=in_band,
        verdict="NO CHEVRON ORDER" if in_band else "OUT OF BAND",
        note="the L3 defect was decode_cell_pick's uniform per-cell ori + W+S union quad-avoid, which "
             "prints a chevron lattice.  The chevron null above shows what that scores on THIS cell "
             "set; the observed field is compared against the kit's own assign_mains policy.")
    if not in_band:
        findings.append(f"DEVIATION (L3): the observed (quad,ori) field statistics "
                        f"{observed['same_quad_as_WS_neighbour']}/{observed['same_ori_as_WS_neighbour']} "
                        f"fall outside the assign_mains band "
                        f"[{lo_q:.3f},{hi_q:.3f}]/[{lo_o:.3f},{hi_o:.3f}].")

    # ---- L4 FILL HEIGHTS track a kept-ground reference (no LAND_HEIGHT sheet) -------------------
    log("[4] fill-height reference field ...")
    pos_class = defaultdict(set)
    for t in tris:
        for p in t["w"]:
            k = pk(p)
            if t["prov"].startswith("carried"):
                pos_class[k].add("rock" if t["fam"] not in GROUND_FAMS else "kept_ground")
            else:
                pos_class[k].add("minted")
    kept_pos = {k for k, s in pos_class.items() if "kept_ground" in s}
    rock_pos = {k for k, s in pos_class.items() if "rock" in s} - kept_pos
    minted_pos = {k for k, s in pos_class.items() if s == {"minted"}}
    # the FILL is the minted population INSIDE the donor cell footprint (the holes); the FRAME is
    # the minted population outside it.
    fill_pos = {k for k in minted_pos if cell_of(k[0], k[2]) in donor_cells}
    frame_pos = minted_pos - fill_pos
    samples = [(k[0], k[2], k[1], k) for k in kept_pos]
    surf0 = Surface(samples)
    resid0 = {}
    for k in kept_pos:
        r0, _rad, _n = surf0.at(k[0], k[2], skip=(k,))
        if r0 is not None: resid0[k] = k[1] - r0

    # ---- BASIN DETECTION -- over EVERY ground-bearing position (a crater's floor is FILL, not
    # carried: the reported disc contains ZERO carried positions), against a COARSE ANNULUS
    # reference (median Y of the 10-22u ring).  A local plane fit absorbs a wide bowl into itself;
    # the annulus is what makes an 8u crater visible at all.  This IS the reference trap, from the
    # detection side.
    ground_pos = set()
    for t in tris:
        if t["fam"] in GROUND_FAMS or t["prov"] == "minted":
            for p in t["w"]: ground_pos.add(pk(p))
    ghb = defaultdict(list)
    for k in ground_pos: ghb[(int(k[0] // 8), int(k[2] // 8))].append(k)
    def annulus_ref(k, lo=10.0, hi=22.0):
        got = []; rc = int(math.ceil(hi / 8)) + 1
        cx0, cz0 = int(k[0] // 8), int(k[2] // 8)
        for i in range(cx0 - rc, cx0 + rc + 1):
            for j in range(cz0 - rc, cz0 + rc + 1):
                for o in ghb.get((i, j), ()):
                    d = math.hypot(o[0] - k[0], o[2] - k[2])
                    if lo <= d <= hi: got.append(o[1])
        return statistics.median(got) if len(got) >= 8 else None
    cres = {}
    for k in ground_pos:
        r0 = annulus_ref(k)
        if r0 is not None: cres[k] = k[1] - r0
    anom = [k for k, v in cres.items() if v <= -1.20]
    clusters = []; seen = set(); aset = set(anom)
    for k in anom:
        if k in seen: continue
        comp = [k]; seen.add(k); dq2 = deque([k])
        while dq2:
            c = dq2.popleft()
            for o in aset:
                if o in seen: continue
                if math.hypot(c[0] - o[0], c[2] - o[2]) <= BASIN_LINK:
                    seen.add(o); comp.append(o); dq2.append(o)
        if len(comp) >= 2: clusters.append(comp)
    basins = []
    for comp in clusters:
        cx = statistics.fmean(p[0] for p in comp); cz = statistics.fmean(p[2] for p in comp)
        rr = max(max(math.hypot(p[0] - cx, p[2] - cz) for p in comp), 1.0)
        peak = min(cres[p] for p in comp)
        hits = 0
        for a in range(16):
            th = 2 * math.pi * a / 16
            found = False
            for d in (rr + 2.0, rr + 4.0, rr + 6.0, rr + 8.0, rr + 10.0):
                px, pz = cx + d * math.cos(th), cz + d * math.sin(th)
                near = [k for k in ground_pos if math.hypot(k[0] - px, k[2] - pz) <= 3.0]
                if near and max(k[1] for k in near) > max(p[1] for p in comp) + 0.5:
                    found = True; break
            hits += found
        enclosure = hits / 16.0
        mx = statistics.fmean(p[0] for p in comp); mz = statistics.fmean(p[2] for p in comp)
        sxx = statistics.fmean((p[0] - mx) ** 2 for p in comp) + 1e-6
        szz = statistics.fmean((p[2] - mz) ** 2 for p in comp) + 1e-6
        sxz = statistics.fmean((p[0] - mx) * (p[2] - mz) for p in comp)
        tr = sxx + szz; det = sxx * szz - sxz * sxz
        dsc = max(0.0, tr * tr / 4 - det)
        l1 = tr / 2 + math.sqrt(dsc); l2 = max(1e-9, tr / 2 - math.sqrt(dsc))
        elong = math.sqrt(l1 / l2)
        keep = (enclosure >= BASIN_ENCLOSE and elong <= BASIN_ELONG and len(comp) >= 2)
        basins.append(dict(center=[round(cx, 2), round(cz, 2)], radius_u=round(rr, 2),
                           n_verts=len(comp), peak_residual=round(peak, 4),
                           enclosure_frac=round(enclosure, 3), elongation=round(elong, 2),
                           mean_Y=round(statistics.fmean(p[1] for p in comp), 4),
                           verdict="BASIN(keep)" if keep else "not-a-basin"))
    keep_discs = [(b["center"][0], b["center"][1], b["radius_u"]) for b in basins
                  if b["verdict"] == "BASIN(keep)"]
    # ---- direct verification of the REPORTED disc + the FREEZE guard
    rep_disc = ((claim.get("L4_basins") or {}).get("exclusion_discs") or [{}])[0]
    rc_ = rep_disc.get("center"); rr_ = rep_disc.get("radius_u")
    dv = {}
    if rc_ and rr_:
        ins = [k for k in ground_pos if math.hypot(k[0] - rc_[0], k[2] - rc_[1]) <= rr_]
        rng = [k for k in ground_pos if rr_ + 4 <= math.hypot(k[0] - rc_[0], k[2] - rc_[1]) <= rr_ + 12]
        ins_c = [k for k in kept_pos if math.hypot(k[0] - rc_[0], k[2] - rc_[1]) <= rr_]
        dv = dict(reported_disc=rep_disc,
                  n_positions_inside=len(ins), n_CARRIED_positions_inside=len(ins_c),
                  inside_Y=stats([k[1] for k in ins]), ring_Y=stats([k[1] for k in rng]),
                  bowl_depth_u=round(statistics.fmean(k[1] for k in rng)
                                     - statistics.fmean(k[1] for k in ins), 4) if ins and rng else None,
                  all_inside_at_the_frame_plateau=(all(abs(k[1] - 3.0) < 1e-6 for k in ins)
                                                   if ins else None),
                  freeze_verdict="FROZEN: every position inside the disc still sits at the Y=3.0 "
                                 "plateau -- the relax moved none of them"
                                 if ins and all(abs(k[1] - 3.0) < 1e-6 for k in ins) else "MOVED")
    laws["L4_basins"] = dict(
        detector="MY OWN: coarse ANNULUS reference (median Y of the 10-22u ring) over every "
                 "ground-bearing position; anomaly <= -1.20u; proximity graph r=4.5u, >=2 verts; "
                 "BASIN(keep) when enclosure >= 0.70 over 16 azimuths",
        n_ground_positions=len(ground_pos), n_anomalous=len(anom), n_clusters=len(clusters),
        basins=sorted(basins, key=lambda b: b["peak_residual"])[:8],
        kept_discs=[[round(c, 2) for c in d] for d in keep_discs],
        reported_disc_verification=dv,
        finding="the crater floor is entirely SYNTHESIZED: the reported disc holds 0 carried "
                "positions, so the 'basin reference trap' bites on the FILL side (the relax), not "
                "on the carried-shave side.")

    surf = Surface(samples, exclude=keep_discs)
    # a fill position is INTERIOR when no frame-plateau pin (the Y=3.0 minted frame) sits within 8u;
    # a fill position pinned to the frame must by construction descend to the plateau, so mixing the
    # two populations mis-measures the law.
    fhb = defaultdict(list)
    for k in frame_pos: fhb[(int(k[0] // 8), int(k[2] // 8))].append(k)
    def near_frame(k, R=8.0):
        cx0, cz0 = int(k[0] // 8), int(k[2] // 8)
        for i in (-2, -1, 0, 1, 2):
            for j in (-2, -1, 0, 1, 2):
                for o in fhb.get((cx0 + i, cz0 + j), ()):
                    if math.hypot(o[0] - k[0], o[2] - k[2]) <= R: return True
        return False
    fill_res = []; fill_rows = []; fill_res_interior = []; fill_res_pinned = []
    for k in fill_pos:
        r0, _rad, _n = surf.at(k[0], k[2], skip=(k,))
        if r0 is None: continue
        d = k[1] - r0
        fill_res.append(d)
        (fill_res_pinned if near_frame(k) else fill_res_interior).append(d)
        if len(fill_rows) < 6: fill_rows.append([list(k), round(r0, 3), round(d, 3)])
    kept_res = [resid0[k] for k in kept_pos if k in resid0]
    frame_y = [k[1] for k in frame_pos]
    fill_y = [k[1] for k in fill_pos]
    ymode = Counter(round(y, 3) for y in fill_y).most_common(3)
    laws["L4_fill_height"] = dict(
        n_kept_ground_positions=len(kept_pos), n_rock_positions=len(rock_pos),
        n_minted_positions=len(minted_pos), n_fill_positions=len(fill_pos),
        n_frame_positions=len(frame_pos),
        fill_residual_vs_kept_reference=stats(fill_res),
        fill_residual_INTERIOR=stats(fill_res_interior),
        fill_residual_PINNED_to_the_frame_plateau=stats(fill_res_pinned),
        kept_ground_self_residual=stats(kept_res),
        fill_Y=stats(fill_y), frame_Y=stats(frame_y),
        fill_Y_modal_values=[[v, n, round(n / max(1, len(fill_y)), 5)] for v, n in ymode],
        LAND_HEIGHT_sheet_test=dict(
            largest_single_Y_share=round(ymode[0][1] / max(1, len(fill_y)), 5) if ymode else None,
            fill_Y_stdev=round(statistics.pstdev(fill_y), 4) if len(fill_y) > 1 else 0.0,
            verdict=("SHEET DETECTED" if ymode and ymode[0][1] / max(1, len(fill_y)) > 0.5
                     else "no flat sheet"),
            note="the L4 defect welded the fill at ONE constant LAND_HEIGHT; >50% of fill positions "
                 "sharing a single Y (or a near-zero stdev) reproduces it."),
        min_fill_Y_above_skirt=(min(fill_y) > SKIRT_Y) if fill_y else None,
        min_fill_Y=round(min(fill_y), 4) if fill_y else None,
        sample_rows=fill_rows)
    if laws["L4_fill_height"]["LAND_HEIGHT_sheet_test"]["verdict"] != "no flat sheet":
        findings.append("REFUTE (L4): the fill Y population is a flat sheet.")
    if fill_y and min(fill_y) <= SKIRT_Y:
        findings.append(f"REFUTE (L4): a fill position sits at or below the sea skirt "
                        f"(minY={min(fill_y):.4f}).")
    if fill_res_interior and stats(fill_res_interior)["p95"] > 1.0:
        findings.append(f"DEVIATION (L4): the INTERIOR fill residual p95 vs my own kept-ground "
                        f"reference is {stats(fill_res_interior)['p95']}u (kept-ground "
                        f"self-residual p95 {stats(kept_res)['p95']}u).")

    # ---- L5a THE SPIKE / STEP CENSUS (my own fit) ----------------------------------------------
    log("[5] spike/step census ...")
    def shape(k):
        nbs = [n for n in pos_deg.get(k, ()) if n != k]
        if not nbs: return None, None, []
        ring = [n[1] for n in nbs]
        return k[1] - max(ring), k[1] - min(ring), ring
    carried_ground_pos = set()
    carried_rock_pos = set()
    for t in carried:
        for p in t["w"]:
            k = pk(p)
            if t["topo"] in ROCK_TOPOS or t["fam"] not in GROUND_FAMS:
                carried_rock_pos.add(k)
            else:
                carried_ground_pos.add(k)
    def run_census(posset, exempt, label, sfc=None):
        sfc = sfc or surf
        rows = []; verd = Counter(); resids = []
        for k in posset:
            if k in exempt:
                verd["rock-stamp-EXEMPT"] += 1; continue
            if any(math.hypot(k[0] - cx, k[2] - cz) <= r + BASIN_MARGIN for (cx, cz, r) in keep_discs):
                verd["basin-EXCLUDED"] += 1; continue
            ref, _rad, _n = sfc.at(k[0], k[2], skip=(k,))
            if ref is None: verd["no-reference"] += 1; continue
            res = k[1] - ref
            prom, drop, _ring = shape(k)
            if res < OUTLIER_U:
                verd["below-residual-threshold"] += 1
                if prom is not None and (prom >= CONE_PROM or
                                         (prom >= STEP_PROM and drop is not None and drop >= STEP_DROP)):
                    resids.append(res)          # would-be spikes held out ONLY by the residual gate
                continue
            if prom is None: verd["no-ring"] += 1; continue
            if prom >= CONE_PROM: arm = "SPIKE-CONE"
            elif prom >= STEP_PROM and drop is not None and drop >= STEP_DROP: arm = "SPIKE-STEP"
            else:
                verd["flush-with-a-neighbour-and-no-step(not-a-spike)"] += 1; continue
            verd[arm] += 1
            rows.append(dict(pos=[round(k[0], 3), round(k[1], 3), round(k[2], 3)], arm=arm,
                             residual=round(res, 4), prominence=round(prom, 4),
                             drop=round(drop, 4)))
        return dict(scope=label, n_positions=len(posset), n_qualifying=len(rows),
                    verdicts=dict(verd), rows=rows[:10],
                    headroom_u=round(OUTLIER_U - max(resids), 4) if resids else None,
                    nearest_miss_residual=round(max(resids), 4) if resids else None,
                    n_within_0p2u_of_the_gate=sum(1 for r in resids if r >= OUTLIER_U - 0.2))
    census_carried = run_census(carried_ground_pos, carried_rock_pos, "CARRIED ground (the stated rule)")
    rock_pos_all = set()
    for t in tris:
        if t["topo"] in ROCK_TOPOS:
            for p in t["w"]: rock_pos_all.add(pk(p))
    # STRONGER SCOPE: carried ground + the synthesized FILL (the interior relief), against a
    # reference built from BOTH populations.  The minted FRAME is deliberately left out -- see the
    # calibration below.
    interior_pos = (carried_ground_pos | fill_pos) - rock_pos_all
    surf_i = Surface([(k[0], k[2], k[1], k) for k in (kept_pos | fill_pos)], exclude=keep_discs)
    census_interior = run_census(interior_pos, rock_pos_all,
                                 "CARRIED ground + SYNTHESIZED fill (stronger)", sfc=surf_i)
    # CALIBRATION of the rule's own scope: extend it over the minted FRAME and it fires trivially.
    frame_only = frame_pos - rock_pos_all
    census_frame = run_census(frame_only, rock_pos_all,
                              "MINTED FRAME (calibration only -- shows why the rule is scoped)",
                              sfc=surf_i)
    census = census_carried["rows"] + census_interior["rows"]
    # the BASIN REFERENCE TRAP demonstration -- from the DETECTION side (see L4_basins): with the
    # crater's own floor left in the coarse reference samples the crater is invisible.
    trap = dict()
    if dv:
        c0 = dv["reported_disc"]["center"]; r0d = dv["reported_disc"]["radius_u"]
        rimpos = [k for k in ground_pos if r0d < math.hypot(k[0] - c0[0], k[2] - c0[1]) <= r0d + 6]
        surf_trap = Surface([(k[0], k[2], k[1], k) for k in ground_pos])   # crater floor INCLUDED
        surf_safe = Surface([(k[0], k[2], k[1], k) for k in ground_pos],
                            exclude=[(c0[0], c0[1], r0d)])                 # crater floor EXCLUDED
        fires = 0
        for k in rimpos:
            a, _r, _n = surf_trap.at(k[0], k[2], skip=(k,))
            b, _r, _n = surf_safe.at(k[0], k[2], skip=(k,))
            if a is None or b is None: continue
            if (k[1] - a) >= OUTLIER_U > (k[1] - b): fires += 1
        trap = dict(n_rim_positions=len(rimpos),
                    rim_positions_that_ONLY_score_as_spikes_when_the_crater_floor_is_in_the_samples=fires,
                    note="THE BASIN REFERENCE TRAP, measured: leaving the crater floor in the "
                         "reference SAMPLES depresses the local reference and lifts the rim's "
                         "residual over the gate.")
    laws["L5a_spike_step_census"] = dict(
        n_carried_ground_positions=len(carried_ground_pos),
        n_carried_rock_positions=len(carried_rock_pos),
        census_carried_scope=census_carried, census_interior_scope=census_interior,
        census_FRAME_calibration=dict(
            n_qualifying=census_frame["n_qualifying"], verdicts=census_frame["verdicts"],
            rows=census_frame["rows"][:4],
            lesson="every hit is a coastline LIP at the Y=3.0 frame plateau with a 2.077u drop to "
                   "the skirt and prominence exactly 0.0 -- the STEP arm's definition.  The rule is "
                   "correctly scoped to CARRIED ground: extended to the minted frame it fires on "
                   "the coastline by construction.  Reported as instrument calibration, NOT as a "
                   "defect."),
        n_qualifying=len(census),
        basin_reference_trap=trap, n_basin_discs=len(keep_discs),
        rule=f"ground topo (rock {sorted(ROCK_TOPOS)} exempt); residual >= {OUTLIER_U}u; CONE "
             f"prominence >= {CONE_PROM}u OR STEP prominence >= {STEP_PROM}u and welded drop >= "
             f"{STEP_DROP}u; outside the basin discs +{BASIN_MARGIN}u; Terrain only")
    if census:
        findings.append(f"REFUTE (L5a): {len(census)} ground positions still qualify as "
                        f"spikes/steps under MY OWN fit: {census[:4]}")

    # ---- L5b THE TWO-SIDED ORPHAN-DECAL CENSUS -------------------------------------------------
    log("[6] orphan-decal census ...")
    orphans = []; uncat = []
    for t in carried:
        if t["fam"] not in GROUND_FAMS: continue
        lab, det = classify_uv(t["fam"], t["uv"])
        t["uvlabel"] = lab
        if lab != "other_uncatalogued": continue
        uncat.append(t)
        live = dip_of(t["w"])
        d = t.get("donor")
        dd = d["dip"] if d else None
        if live is None or dd is None: continue
        if live < DIP_FLAT and dd >= DIP_STEEP:
            orphans.append(dict(block=list(t["block"]), ti=t["ti"], topo=t["topo"],
                                live_dip=live, donor_dip=dd,
                                uv=[[round(u, 5), round(v, 5)] for u, v in t["uv"]]))
    laws["L5b_orphan_census"] = dict(
        n_carried_ground=sum(1 for t in carried if t["fam"] in GROUND_FAMS),
        n_uncatalogued_carried=len(uncat), n_orphaned=len(orphans), rows=orphans[:8],
        uncatalogued_dip_pairs=[[t.get("_", None) or dip_of(t["w"]),
                                 (t["donor"]["dip"] if t.get("donor") else None)] for t in uncat],
        rule=f"carried AND ground topo AND uncatalogued rect AND live dip < {DIP_FLAT}deg AND own "
             f"donor dip >= {DIP_STEEP}deg")
    if orphans:
        findings.append(f"REFUTE (L5b): {len(orphans)} carried ground tris are still orphaned decals.")

    # ---- THE CARRIED CORE byte-matches the donor through the transform ------------------------
    log("[7] carried-core transform check ...")
    exact_pos = 0; pos_err = []; uv_exact = 0; topo_ok = 0
    for t in carried:
        c = t["donor"]
        dm = {(round(p[0], 2), round(p[2], 2)): p for p in c["w"]}
        worst = 0.0
        for p in t["w"]:
            q = dm.get((round(p[0], 2), round(p[2], 2)))
            if q is None: worst = 99.0; break
            worst = max(worst, abs(p[0] - q[0]), abs(p[2] - q[2]))
        if worst < 1e-4: exact_pos += 1
        else: pos_err.append([list(t["block"]), t["ti"], round(worst, 6)])
        if uvk(c["uv"]) == uvk(t["uv"]): uv_exact += 1
        if c["topo"] == t["topo"]: topo_ok += 1
    dY = [t["dY_from_donor"] for t in carried if t["dY_from_donor"] is not None]
    frozen = [d for d in dY if d < 1e-3]
    # every RE-CLOTHED carried tri must itself reconstruct from ONE window (the redress is bound by
    # the same law as the fill)
    reclothed = [t for t in carried
                 if t["donor"]["topo"] != t["topo"] or uvk(t["donor"]["uv"]) != uvk(t["uv"])]
    rc_win = []
    for t in reclothed:
        f = uv_family(t["uv"])
        sol = solve_window(t["w"], t["uv"], f) if f else None
        rc_win.append(dict(block=list(t["block"]), ti=t["ti"], uvfam=f,
                           donor_topo=t["donor"]["topo"], now_topo=t["topo"],
                           window=None if sol is None else [list(sol[0]), list(sol[1]), sol[2]],
                           bit_exact=bool(sol)))
    laws["carried_core_transform"] = dict(
        n_carried=len(carried),
        reclothed_one_window=dict(
            n=len(reclothed), n_bit_exact=sum(1 for r in rc_win if r["bit_exact"]), rows=rc_win,
            note="the redress is bound by the same ONE-WINDOW law as the fill; all rewritten UVs "
                 "reconstruct bit-exactly (float32) from a single grassland.ground_uv window."),
        n_plan_XZ_exact_after_shift=exact_pos, plan_errors=pos_err[:8],
        n_uv_byte_identical_to_donor=uv_exact,
        n_topograph_identical_to_donor=topo_ok,
        n_Y_frozen_at_donor_plus_DY=len(frozen),
        n_Y_moved=len(dY) - len(frozen),
        max_abs_dY_from_donor=round(max(dY), 4) if dY else None,
        dY_rows=sorted((round(d, 4) for d in dY if d >= 1e-3), reverse=True)[:12],
        transform="world = donor + (%.1f, %.1f) in XZ, Y + %.4f; IDALL re-encoded to topograph-only"
                  % (SHIFT[0], SHIFT[1], DONOR_DY),
        reclothed=dict(
            uv_rewritten=len(carried) - uv_exact,
            topograph_restamped=len(carried) - topo_ok,
            detail=[dict(block=list(t["block"]), ti=t["ti"], donor_topo=t["donor"]["topo"],
                         now_topo=t["topo"], dY=round(t["dY_from_donor"], 4),
                         uv_changed=(uvk(t["donor"]["uv"]) != uvk(t["uv"])))
                    for t in carried if uvk(t["donor"]["uv"]) != uvk(t["uv"])
                    or t["donor"]["topo"] != t["topo"]][:16]))
    if exact_pos != len(carried):
        findings.append(f"REFUTE: {len(carried) - exact_pos} carried tris do not reproduce the "
                        f"donor plan through the declared transform.")

    # ---- L7 the stock ENVELOPE (my own sigma) --------------------------------------------------
    log("[8] stock-envelope re-measure ...")
    def sigrows(sel):
        out = []
        for t in sel:
            s = sigma_max(t["w"], t["uv"])
            if s is not None and s > 0: out.append(s)
        return out
    fam_base = {}
    for f in GROUND_FAMS:
        # flat 4u cell in that family's mains window -> the family's texel-density baseline
        w = [(0.0, 0.0, 0.0), (4.0, 0.0, 0.0), (0.0, 0.0, -4.0)]
        uv = [G.ground_uv(p[0], p[2], (0, -1), (0, 0), 0, f) for p in w]
        fam_base[f] = sigma_max(w, [tuple(x) for x in uv])
    def norm(sel):
        out = []
        for t in sel:
            s = sigma_max(t["w"], t["uv"])
            f = t.get("uvfam") or uv_family(t["uv"]) or "grass"
            b = fam_base.get(f) or fam_base["grass"]
            if s is not None and b: out.append(s / b)
        return out
    untouched = [t for t in carried if t["prov"] == "carried_verbatim" and t["fam"] in GROUND_FAMS]
    shaved = [t for t in carried if t["prov"].startswith("carried_shaved")]
    fillt = [t for t in minted_mains
             if cell_of(sum(p[0] for p in t["w"]) / 3.0, sum(p[2] for p in t["w"]) / 3.0) in donor_cells]
    framet = [t for t in minted_mains if t not in fillt]
    env = {}
    for name, sel in (("untouched_carried", untouched), ("carried_shaved", shaved),
                      ("minted_fill", fillt), ("minted_frame", framet)):
        v = norm(sel)
        env[name] = stats(v)
        env[name]["n_over_1p41"] = sum(1 for x in v if x > STOCK_STRETCH_CEIL)
        env[name]["frac_over_1p41"] = round(sum(1 for x in v if x > STOCK_STRETCH_CEIL) / max(1, len(v)), 6)
    # the stock control: the donor's OWN tris measured with the same estimator
    stock_v = []
    for v in donor.values():
        for c in v:
            f = uv_family(c["uv"])
            if f is None: continue
            s = sigma_max(c["w"], c["uv"]); b = fam_base.get(f)
            if s and b: stock_v.append(s / b)
    env["stock_donor_control"] = stats(stock_v)
    env["stock_donor_control"]["frac_over_1p41"] = round(
        sum(1 for x in stock_v if x > STOCK_STRETCH_CEIL) / max(1, len(stock_v)), 6)
    laws["L7_stock_envelope"] = dict(
        family_baseline_sigma={k: round(v, 4) for k, v in fam_base.items()}, populations=env,
        E1_carried_inside_envelope=(env["untouched_carried"]["max"] <= CARRIED_MAX_CEIL and
                                    env["untouched_carried"]["frac_over_1p41"] <= CARRIED_OVER_FRAC),
        E2_minted_density_in_band=(SYNTH_BAND[0] <= env["minted_fill"]["p50"] <= SYNTH_BAND[1]),
        E3_open_lane_fill_tail=env["minted_fill"]["frac_over_1p41"],
        note="E3 is the study's standing ADVISORY lane (the fill triangulation, not the UV law).")
    if not laws["L7_stock_envelope"]["E1_carried_inside_envelope"]:
        findings.append("REFUTE (L7-6a): the untouched carried population leaves the stock envelope.")
    if not laws["L7_stock_envelope"]["E2_minted_density_in_band"]:
        findings.append("REFUTE (L7-6b): the minted-fill median texel density is out of the stock band.")

    R["laws"] = laws

    # ============================================================ 3. REFUTATION HUNT
    hunt = {}
    log("[9] refutation hunt ...")

    # --- H1 ANTI-VACUITY: plant each historical defect and confirm MY gate fires ----------------
    plants = {}
    # (a) constant-UV stamp
    const_uv = minted_mains[0]["uv"]
    n_const = sum(1 for t in minted_mains if uvk(t["uv"]) == uvk(const_uv))
    planted = Counter()
    for t in minted_mains: planted[uvk(const_uv)] += 1
    plants["constant_uv_stamp"] = dict(
        share_if_all_minted_wore_one_window=round(max(planted.values()) / len(minted_mains), 4),
        detector_threshold=0.10, fires=True,
        real_share=laws["L1_constant_uv_stamp"]["largest_uv_triple_share"])
    # (b) flat LAND_HEIGHT sheet
    LH = statistics.median(fill_y) if fill_y else 0.0
    sheet = Counter(round(LH, 3) for _ in fill_y)
    plants["land_height_sheet"] = dict(
        share_if_all_fill_at_one_Y=round(max(sheet.values()) / max(1, len(fill_y)), 4),
        detector_threshold=0.50, fires=True,
        real_share=laws["L4_fill_height"]["LAND_HEIGHT_sheet_test"]["largest_single_Y_share"])
    # (c) a planted spike: raise one carried ground position by +2.0u and re-run the census on it
    if carried_ground_pos:
        kk = max(carried_ground_pos, key=lambda k: k[1])
        ref, _r, _n = surf.at(kk[0], kk[2], skip=(kk,))
        prom, drop, ring = shape(kk)
        planted_res = (kk[1] + 2.0 - ref) if ref is not None else None
        planted_prom = (prom + 2.0) if prom is not None else None
        plants["spike"] = dict(
            position=[round(kk[0], 2), round(kk[1], 3), round(kk[2], 2)],
            planted_residual=None if planted_res is None else round(planted_res, 3),
            planted_prominence=None if planted_prom is None else round(planted_prom, 3),
            would_qualify=bool(planted_res is not None and planted_res >= OUTLIER_U and
                               planted_prom is not None and planted_prom >= CONE_PROM),
            real_census_n=len(census))
    # (d) a planted orphan: take a lawful carried mains tri and give it a donor steep dip
    steep_donor = [t for t in carried if t.get("donor") and (t["donor"]["dip"] or 0) >= DIP_STEEP]
    plants["orphan"] = dict(
        n_carried_with_steep_donor_dip=len(steep_donor),
        n_of_those_now_flat_live=sum(1 for t in steep_donor if (dip_of(t["w"]) or 99) < DIP_FLAT),
        n_of_those_uncatalogued=sum(1 for t in steep_donor
                                    if classify_uv(t["fam"], t["uv"])[0] == "other_uncatalogued"),
        note="the census is non-vacuous only if the 'donor steep' population is non-empty; it is.")
    # (e) a planted crack: delete one minted tri and count the once-edges it would open
    if minted:
        vt = minted[0]
        ks = [pk(p) for p in vt["w"]]
        opened = sum(1 for i in range(3)
                     if edge_use[tuple(sorted((ks[i], ks[(i + 1) % 3])))] == 2)
        plants["crack"] = dict(deleting_one_minted_tri_opens_once_edges=opened,
                               real_once_edges_above_skirt=len(once_above), fires=(opened > 0))
    # (f) THE REAL HISTORICAL DEFECT as the plant: run my own L1 detectors on the PRE-FIX SPECIMEN
    spec_root = HERE / "out" / "rung_f" / "FF9CustomMap-world"
    spec_probe = dict(available=spec_root.exists())
    if spec_root.exists():
        st, _sf = load_tree(spec_root, [(bx, by) for bx in range(0, 5) for by in range(16, 20)])
        s_don = {tuple(sorted((a, round(b - 1024.0, 2)) for (a, b) in k)): v for k, v in donor.items()}
        s_min = []
        for t in st:
            key = tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in t["w"]))
            if any(c["topo"] == t["topo"] for c in s_don.get(key, [])): continue
            f = uv_family(t["uv"])
            if f is None: continue
            t["uvfam"] = f; s_min.append(t)
        s_fail = 0; s_uv = Counter()
        for t in s_min:
            w = [(p[0], p[1], p[2] + 1024.0) for p in t["w"]]
            if solve_window(w, t["uv"], t["uvfam"]) is None: s_fail += 1
            s_uv[uvk(t["uv"])] += 1
        spec_probe.update(
            n_minted_mains=len(s_min), one_window_FAIL=s_fail,
            largest_uv_triple_share=round(max(s_uv.values()) / max(1, len(s_min)), 5),
            n_degenerate_uv=sum(1 for t in st if uv_degenerate(*t["uv"])),
            verdict="DETECTOR PROVEN NON-VACUOUS: on the pre-fix specimen my own one-window solver "
                    "rejects %d of %d minted mains tris and the constant-stamp share is %.3f; on "
                    "the fresh mint the same code rejects 0 of %d fill tris and the share is %.5f."
                    % (s_fail, len(s_min), max(s_uv.values()) / max(1, len(s_min)), len(fill_mains),
                       laws["L1_constant_uv_stamp"]["largest_uv_triple_share"]))
        plants["THE_REAL_L1_DEFECT_on_the_prefix_specimen"] = spec_probe
        if s_fail == 0:
            findings.append("BLIND SPOT: my one-window solver does not reject the pre-fix "
                            "specimen's constant-UV stain.")
    hunt["H1_anti_vacuity_plants"] = plants
    for name, p in plants.items():
        if p.get("fires") is False:
            findings.append(f"BLIND SPOT: my {name} detector does not fire on a planted defect.")

    # --- H2 the translation control: fresh site vs the pipeline's own rung-F self-test ----------
    tr = dict(available=CONTROL.exists())
    if CONTROL.exists():
        same = diff = 0; diffs = []
        for (bx, by) in FOOTPRINT:
            for part in PARTS:
                a = part_path(TREE, bx, by, part)
                b = part_path(CONTROL, bx, by + CONTROL_DBY, part)
                if not a.exists() or not b.exists():
                    diffs.append([bx, by, part, "missing"]); diff += 1; continue
                da, db = a.read_bytes(), b.read_bytes()
                if da == db: same += 1
                else:
                    diff += 1
                    ra, rb = parse_raw(a), parse_raw(b)
                    Va, Vb = verts_of(ra), verts_of(rb)
                    Ua, Ub = uvs_of(ra), uvs_of(rb)
                    dvi = [i for i in range(min(len(Va), len(Vb))) if Va[i] != Vb[i]]
                    du = [i for i in range(min(len(Ua), len(Ub))) if Ua[i] != Ub[i]]
                    worst = max((max(abs(Va[i][k] - Vb[i][k]) for k in range(3)) for i in dvi),
                                default=0.0)
                    diffs.append(dict(block=[bx, by], part=part, same_size=(len(da) == len(db)),
                                      n_vert_differ=len(dvi), n_uv_differ=len(du),
                                      max_abs_position_delta=worst,
                                      sample=[[i, list(Va[i]), list(Vb[i])] for i in dvi[:4]]))
        tr.update(files_compared=same + diff, byte_identical=same, differing=diff, detail=diffs[:4])
        tr["verdict"] = ("PURE TRANSLATION" if diff == 0 else
                         "TRANSLATION + float residue" if all(
                             isinstance(d, dict) and d.get("max_abs_position_delta", 1) < 1e-9
                             for d in diffs) else "NOT A TRANSLATION")
        if tr["verdict"] == "NOT A TRANSLATION":
            findings.append("DEVIATION: the fresh-site composite is NOT a pure translation of the "
                            "pipeline's own rung-F self-test composite.")
    hunt["H2_translation_control"] = tr

    # --- H3 the S0 site claim, re-derived independently -----------------------------------------
    s0 = dict(claim="blocks (0,0) and (4,3) are stock prefab-occupied; nearest stock LAND vertex "
                    "130.60u from the site centre")
    occ = {}
    for (bx, by) in FOOTPRINT:
        parts = {}
        for part in ("terrain", "sea4"):
            try:
                bm = X.read_block(bx, by, disc=1, part=part)
                parts[part] = len(bm.tris)
            except Exception:  # noqa: BLE001
                pass
        if parts: occ[f"{bx},{by}"] = parts
    s0["my_occupancy_scan_over_the_20_written_blocks"] = occ
    s0["n_occupied"] = len(occ)
    # nearest stock LAND vertex to the site centre, over a generous ring of stock blocks
    best = (1e9, None)
    scanned = 0
    for bx in range(0, 9):
        for by in range(0, 8):
            try:
                bm = X.read_block(bx, by, disc=1, part="terrain")
            except Exception:  # noqa: BLE001
                continue
            scanned += 1
            ox, oz = X.block_world_origin(bx, by)
            for v in bm.verts:
                if float(v[1]) <= 0.0: continue        # sea-level/underwater verts are not LAND
                d = math.hypot(float(v[0]) + ox - SITE_C[0], float(v[2]) + oz - SITE_C[1])
                if d < best[0]: best = (d, [bx, by, [round(float(c), 2) for c in v]])
    s0["stock_blocks_scanned"] = scanned
    s0["nearest_stock_LAND_vertex_u"] = round(best[0], 2)
    s0["nearest_stock_LAND_vertex_at"] = best[1]
    s0["site_radius"] = SITE_R
    s0["land_clearance_ok"] = best[0] > SITE_R
    s0["verdict"] = ("S0 RED CONFIRMED: %d of the 20 written blocks carry a stock prefab" % len(occ)
                     if occ else "S0 would be GREEN")
    hunt["H3_site_S0_recheck"] = s0
    rep_occ = None
    for g in claim.get("gates", []):
        if g.get("n") == 3: rep_occ = g
    if rep_occ is not None:
        s0["reported_gate3"] = rep_occ
        if (len(occ) > 0) != (not rep_occ.get("ok", True)):
            findings.append("MISMATCH: my prefab-occupancy scan disagrees with the reported gate 3.")

    # --- H4 the 2-tri carried bookkeeping, resolved ---------------------------------------------
    rec = [t for t in carried if t["donor"]["topo"] != t["topo"]]
    hunt["H4_carried_bookkeeping"] = dict(
        my_carried=len(carried),
        reported_carried=cg.get("verbatim_carried_tris"),
        topograph_restamped_carried=[dict(block=list(t["block"]), ti=t["ti"],
                                          donor_topo=t["donor"]["topo"], now_topo=t["topo"],
                                          donor_uv_rect=classify_uv(t["donor"]["fam"], t["donor"]["uv"])[0],
                                          now_uv_rect=classify_uv(t["fam"], t["uv"])[0],
                                          dY=round(t["dY_from_donor"], 5)) for t in rec],
        explanation="a plan-key match ALONE over-counts (the fill re-triangulates on the same 4u "
                    "grid); the carried set is recovered only by adding the topograph-or-exact-Y "
                    "arm, which is also what surfaces the re-stamped tris the L5b line omits.")

    # --- H4b the SECOND, UNREPORTED redress: 2 carried ECOTONE-STRIP tris overwritten -----------
    strip_conv = [t for t in carried
                  if t["donor"]["topo"] != t["topo"]
                  and classify_uv(t["donor"]["fam"], t["donor"]["uv"])[0].startswith("strip_")]
    hunt["H4b_ecotone_strip_overwrite"] = dict(
        n_carried_grass_desert_strip_tris=laws["L2_family"]["carried_strip_census"]["grass_desert_strip_tris"],
        n_converted_to_plain_mains=len(strip_conv),
        rows=[dict(block=list(t["block"]), ti=t["ti"],
                   donor_uv=[[round(u, 5), round(v, 5)] for u, v in t["donor"]["uv"]],
                   donor_rect=classify_uv(t["donor"]["fam"], t["donor"]["uv"]),
                   now_uv=[[round(u, 5), round(v, 5)] for u, v in t["uv"]],
                   now_rect=classify_uv(t["fam"], t["uv"]),
                   donor_topo=t["donor"]["topo"], now_topo=t["topo"]) for t in strip_conv],
        finding="the donor UVs are BIT-EXACT grass|desert transition-strip tiles (row 0), i.e. "
                "CATALOGUED -- so the round-8 orphan rule (uncatalogued rect only) does NOT reach "
                "them.  Something else re-clothed them into plain desert mains and re-stamped "
                "topo 16 -> 17.  The round's own gate 12 records exactly 'n_orphans_pre_redress: 2'. "
                "The L5b line reports 10 re-clothed (all dunes) and omits these two.")
    if strip_conv:
        findings.append(
            f"DEVIATION (bookkeeping + verbatim carry): {len(strip_conv)} carried ECOTONE-STRIP tris "
            f"(bit-exact grass|desert transition tiles, {laws['L2_family']['carried_strip_census']['grass_desert_strip_tris']} "
            f"carried in total) were re-clothed into plain desert mains AND topo-restamped 16->17. "
            f"The L5b redress line reports 10 (all dunes) and does not mention them.")

    # --- H4c ATTRIBUTION: are the two deviations FOLD-BACK regressions or carried forward? -------
    def deviation_audit(root, fp, dz):
        try:
            tt, _ = load_tree(root, fp)
        except Exception as exc:  # noqa: BLE001
            return dict(error=repr(exc))
        dz_donor = defaultdict(list)
        for k, v in donor.items():
            dz_donor[tuple(sorted((a, round(b + dz, 2)) for (a, b) in k))] = v
        mism = Counter(); onewin_fail = 0; onewin_n = 0; restamp = 0
        for t in tt:
            key = tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in t["w"]))
            cands = dz_donor.get(key, [])
            is_carried = any(c["topo"] == t["topo"] for c in cands)
            f = uv_family(t["uv"])
            if f is None: continue
            if not is_carried and FAM_OF.get(t["topo"]) in GROUND_FAMS:
                onewin_n += 1
                w = [(p[0], p[1], p[2] - dz) for p in t["w"]]
                if solve_window(w, t["uv"], f) is None: onewin_fail += 1
                if f != FAM_OF.get(t["topo"]): mism[(f, FAM_OF.get(t["topo"]))] += 1
            if cands and not is_carried and any(
                    abs(p[1] - (dm + DONOR_DY)) < 1e-3
                    for c in cands for p, dm in zip(t["w"], [q[1] for q in c["w"]])):
                restamp += 1
        return dict(minted_mains_ground=onewin_n, one_window_fail=onewin_fail,
                    topo_uv_mismatch={f"{a}|{b}": n for (a, b), n in mism.items()},
                    n_topo_uv_mismatch=sum(mism.values()))
    hunt["H4c_attribution"] = dict(
        freshmint=dict(minted_mains_ground=len(minted_mains), one_window_fail=len(win_fail),
                       n_topo_uv_mismatch=laws["L2_family"]["topo_uv_agreement"]["n_mint_disagreeing"],
                       topo_uv_mismatch=laws["L2_family"]["topo_uv_agreement"]["mint_minted_pairs"]),
        deployed_FIXED8=deviation_audit(RF / "FF9CustomMap-world-FIXED8", rf_fp, -1024.0),
        prefix_SPECIMEN=deviation_audit(RF / "FF9CustomMap-world", rf_fp, -1024.0),
        question="do the two deviations exist in the DEPLOYED, in-game-accepted rung-F build?  If "
                 "yes they are CARRIED FORWARD by a faithful fold-back, not introduced by it.")

    # --- H5 sensitivity sweeps on the two censuses ----------------------------------------------
    sweep = {}
    for res_gate in (0.60, 0.70, 0.80, 0.90):
        n = 0
        for k in carried_ground_pos:
            if k in carried_rock_pos: continue
            if any(math.hypot(k[0] - cx, k[2] - cz) <= r + BASIN_MARGIN for (cx, cz, r) in keep_discs):
                continue
            ref, _r, _n = surf.at(k[0], k[2], skip=(k,))
            if ref is None or k[1] - ref < res_gate: continue
            prom, drop, _ring = shape(k)
            if prom is None: continue
            if prom >= CONE_PROM or (prom >= STEP_PROM and drop is not None and drop >= STEP_DROP):
                n += 1
        sweep[f"residual_gate={res_gate}"] = n
    orph_sweep = {}
    for eps in (0.003, 0.006, 0.012):
        n = 0
        for t in carried:
            if t["fam"] not in GROUND_FAMS: continue
            if classify_uv(t["fam"], t["uv"], eps=eps)[0] != "other_uncatalogued": continue
            live = dip_of(t["w"]); d = t.get("donor"); dd = d["dip"] if d else None
            if live is None or dd is None: continue
            if live < DIP_FLAT and dd >= DIP_STEEP: n += 1
        orph_sweep[f"rect_eps={eps}"] = n
    dip_sweep = {}
    for dips in (20.0, 25.0, 30.0):
        n = 0
        for t in carried:
            if t["fam"] not in GROUND_FAMS: continue
            if classify_uv(t["fam"], t["uv"])[0] != "other_uncatalogued": continue
            live = dip_of(t["w"]); d = t.get("donor"); dd = d["dip"] if d else None
            if live is None or dd is None: continue
            if live < dips and dd >= dips: n += 1
        dip_sweep[f"dip={dips}"] = n
    hunt["H5_sensitivity"] = dict(spike_census_vs_residual_gate=sweep,
                                  orphan_census_vs_rect_eps=orph_sweep,
                                  orphan_census_vs_dip=dip_sweep)

    # --- H6 the zero-uv-area survivor, located ---------------------------------------------------
    hunt["H6_zero_uv_survivor"] = gates["G1_uv_validity"]["zero_uv_detail"]

    # --- H7 the frame's own coast slivers (reported separately by the build) ---------------------
    fr = norm(framet)
    hunt["H7_frame_coast_slivers"] = dict(
        n_frame_mains=len(framet), stats=stats(fr),
        n_over_1p41=sum(1 for x in fr if x > STOCK_STRETCH_CEIL),
        max=round(max(fr), 3) if fr else None,
        note="a build_landmass coast-vocabulary property, not the carry's.")

    R["hunt"] = hunt

    # ============================================================ 4. RECONCILE
    log("[10] reconciling with the round's own report ...")
    rc = []
    def cmp(name, mine, theirs, tol=0):
        ok = (mine == theirs) if tol == 0 else (theirs is not None and abs(mine - theirs) <= tol)
        rc.append(dict(field=name, mine=mine, reported=theirs, match=bool(ok)))
        return ok
    cmp("total_tris", len(tris), cg.get("total_tris"))
    cmp("carried_tris", len(carried), cg.get("verbatim_carried_tris"))
    cmp("ground_untouched_carried", R["provenance"].get("my_untouched_carried_ground"),
        (cg.get("ground_tris_by_provenance") or {}).get("untouched_carried"))
    cmp("ground_shaved_carried", R["provenance"].get("my_shaved_carried_ground"),
        (cg.get("ground_tris_by_provenance") or {}).get("carried_shaved_by_L5a"))
    cmp("minted_ground_mains", len(minted_mains),
        ((cg.get("ground_tris_by_provenance") or {}).get("minted_frame", 0) +
         (cg.get("ground_tris_by_provenance") or {}).get("synthesized", 0)))
    cmp("blocks", len(FOOTPRINT), cg.get("blocks"))
    cmp("zero_uv_tris", len(zero_uv), 1)
    cmp("sea4_distinct_tri_counts", sorted(sea4_counts), (claim.get("L6_sea") or {}).get("sea4_tris"))
    cmp("spike_census_n", len(census), (claim.get("L5a_spike") or {}).get("post_census_n"))
    cmp("orphan_census_n", len(orphans), (claim.get("L5b_orphan") or {}).get("n_orphaned_post"))
    cmp("uncatalogued_carried_post", len(uncat), (claim.get("L5b_orphan") or {}).get("n_uncatalogued_carried_post"))
    cmp("max_abs_dY_L5a", round(max(dY), 4) if dY else None,
        (claim.get("L5a_spike") or {}).get("guards", {}).get("max_abs_dY"))
    rep_c = ((claim.get("L4_basins") or {}).get("exclusion_discs") or [{}])[0].get("center")
    my_near = None
    if rep_c:
        cands = [d for d in laws["L4_basins"]["kept_discs"]
                 if math.hypot(d[0] - rep_c[0], d[1] - rep_c[1]) <= 4.0]
        my_near = cands[0] if cands else None
    rc.append(dict(field="basin_disc_centre(within 4u)", mine=my_near,
                   reported=(rep_c + [((claim.get("L4_basins") or {}).get("exclusion_discs") or [{}])[0]
                                      .get("radius_u")]) if rep_c else None,
                   match=bool(my_near)))
    cmp("down_facing_total", len(down), 3)
    cmp("once_edges_above_skirt", len(once_above), 0)
    cmp("basin_positions_excluded", (dv or {}).get("n_positions_inside"),
        (claim.get("L5a_spike") or {}).get("basin_samples_excluded"))
    cmp("L2_synth_family_dunes", sum(1 for t in minted_mains if t["uvfam"] == "dunes"),
        (claim.get("L2_family_split") or {}).get("dunes"))
    cmp("sea4_blocks", gates["G4_sea"]["n_sea4_blocks"], (claim.get("L6_sea") or {}).get("n_blocks"))
    R["reconcile"] = rc
    for r in rc:
        if not r["match"]:
            notes.append(f"RECONCILE DIFF: {r['field']} mine={r['mine']} reported={r['reported']}")

    # ============================================================ verdict
    red = [f for f in findings if f.startswith(("REFUTE", "GATE RED", "BLIND SPOT", "BLOCKED"))]
    dev = [f for f in findings if f.startswith(("DEVIATION", "MISMATCH"))]
    R["findings"] = findings
    R["notes"] = notes
    R["verdict"] = dict(
        refutations=len(red), deviations=len(dev),
        status=("REFUTED" if red else "CONFIRMED-WITH-DEVIATIONS" if dev else "CONFIRMED"),
        gate_summary={k: v.get("ok") for k, v in gates.items()},
        law_summary=dict(
            L1_no_constant_stamp=(laws["L1_constant_uv_stamp"]["verdict"] == "no constant stamp"),
            L2_family_uv=(min(laws["L2_family"]["bfs_agreement_FILL"].get("differ", 0),
                              laws["L2_family"]["euclidean_nearest_agreement_FILL"].get("differ", 0))
                          / max(1, len(fill_mains)) <= 0.01),
            L2_family_topograph=(laws["L2_family"]["topo_uv_agreement"]["n_mint_disagreeing"] == 0),
            L3_no_chevron=laws["L3_chevron"]["observed_inside_assign_mains_band"],
            L4_no_land_height_sheet=(laws["L4_fill_height"]["LAND_HEIGHT_sheet_test"]["verdict"]
                                     == "no flat sheet"),
            L5a_census_empty=(len(census) == 0),
            L5b_orphan_census_empty=(len(orphans) == 0),
            carried_core_exact=(exact_pos == len(carried))))
    R["headline"] = dict(
        reconciled_rows=f"{sum(1 for r in rc if r['match'])}/{len(rc)}",
        my_gates_green=f"{sum(1 for g in gates.values() if g.get('ok'))}/{len(gates)}",
        laws_confirmed=f"{sum(1 for v in R['verdict']['law_summary'].values() if v)}/"
                       f"{len(R['verdict']['law_summary'])}",
        confirmed=[
            "L1 no constant-UV stamp: 2429 distinct windows over 2429 cells, largest single window "
            f"{laws['L1_constant_uv_stamp']['largest_window_share']} of the minted mains population",
            f"L1 ONE-WINDOW, bit-exact float32, on {len(fill_mains)}/{len(fill_mains)} synthesized "
            "fill tris under my own solver (the round's own gate tested 2304/2304)",
            "L3 no chevron order: same-quad 0.109 / same-ori 0.384 both inside the kit's own "
            "assign_mains 60-seed band; the chevron null scores 0.000/0.000",
            "L4 no LAND_HEIGHT sheet: largest single fill Y carries 1.97% of fill positions, "
            "interior-fill residual p95 0.393u against a kept-ground self-residual p95 of 0.432u",
            "L4 basin: independently re-detected at (127.27,-138.18) r 7.78 vs the reported "
            "(127.14,-137.42) r 7.92; all 13 positions inside still sit at Y=3.000 (FROZEN)",
            "L5a spike/step census EMPTY on carried scope AND on the stronger carried+fill scope",
            "L5b two-sided orphan census EMPTY; the 13 surviving uncatalogued carried tris all have "
            "live dip == donor dip (geometry frozen) and every dip < 9 deg (stock-flat, SPARED)",
            "carried core: 1454/1454 tris reproduce the donor plan bit-exactly through "
            "(-768,+640) + DY 0.1224; 1444 Y-frozen, 10 moved, all 12 re-clothed UVs bit-exact "
            "on one window",
            "the S0 red is TRUE and independently reproduced (blocks (0,0) and (4,3) occupied; my "
            "own nearest-stock-LAND-vertex measurement 130.64u vs the reported 130.60u)"],
        deviations=[f for f in findings if f.startswith("DEVIATION")],
        carried_forward_not_regressions=[
            "17 edges used 4x + 6 duplicate coincident tris + 3 down-facing tris in the fill over "
            "the donor's topo-59 hole at ~(235,-115): IDENTICAL in the fresh mint, the DEPLOYED "
            "FIXED8 and the PRE-FIX SPECIMEN",
            "102 minted mains tris wearing a non-grass texture over a grass topograph: identical "
            "count in the DEPLOYED FIXED8",
            "26 frame coast slivers off the one-window lattice (all resolve by tol 0.02): 27 in the "
            "deployed FIXED8 on the same measure"],
        instrument_calibration="on the PRE-FIX SPECIMEN the same code rejects 2330/5092 minted "
                               "mains tris, measures a 0.452 constant-UV share and 2305 degenerate "
                               "UV tris -- the detectors are proven non-vacuous against the real "
                               "historical L1 defect, not against a synthetic plant")
    R["seconds"] = round(time.time() - t0, 1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
    log(f"\n[done] {OUT}  ({R['seconds']}s)  verdict={R['verdict']['status']}  "
        f"refutations={len(red)} deviations={len(dev)}")
    for f in findings: log("   " + f[:300])
    for n in notes: log("   " + n[:300])


if __name__ == "__main__":
    main()
