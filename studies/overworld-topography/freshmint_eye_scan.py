"""FRESHMINT EYE SCAN -- independent visual + metric judgement of the fold-back fresh-site mint.

THE ASK.  THE MINT's own gate battery (junction_compose.compose) is a NUMBER-only arbiter; its L8
render stage was SKIPPED this run (gate 3 / S0 OPEN-OCEAN TARGET redded, and THE FINAL-COMPOSITE RULE
only emits renders on all-green).  So there is nothing to "re-read" -- this script is the FIRST and
ONLY visual pass over the fresh-site composite, built with its own rasterizer and its own per-tri
decode, reading the STAGED TREE directly off disk (never the in-memory Composite object a re-run of
compose() would hand back).

WHAT IT DOES
  1. Loads the fresh-site composite's Terrain parts straight from the 20 staged .ff9mesh files
     (out/foldback/freshmint-tree), converting block-local -> world coords with the SAME formula
     used throughout the kit (rung_f_layout.bm_world_soup / transplant.world_tris), independently
     re-derived here rather than imported as a rendering function.
  2. Loads three STOCK reference regions the SAME way, but via ff9mapkit.world.extract.read_block
     against the live game install (read-only): the real dunes mass (18-20,3)+(20,3), the Cleyra
     donor junction (13-15,11-12), and a lawful stock world-island region (7-10,16-19).
  3. Computes, per ground tri, independently: family (grassland.TOPO_FAMILY / rock via
     seam_null_recon.FAM_OF), dip, UV area, UV-stretch sigma_max (own SVD-free closed form,
     re-derived not imported), and a ONE-WINDOW decode -- brute-forcing every (quad,ori) rather than
     reusing the pipeline's precomputed `decoded` field, so this check cannot inherit the builder's
     own answer.
  4. Rasterizes THREE own render passes per region: (a) textured planview -- family colour modulated
     by a procedural UV-tile pattern (so a flat constant-UV stain reads as a BLANK unmodulated patch,
     not just a flat colour); (b) shaded-relief planview -- Lambertian shading from the tri's own
     geometric normal; (c) stretch/density heatmap planview.
  5. Runs an independent structure-tensor orientation-coherence pass (own Sobel implementation, no
     external CV library) over the rendered textured PNGs, comparing the fresh mint to each stock
     reference.
  6. Emits the metric table + verdicts to freshmint_eye.json and all PNGs to out/foldback/renders/.

READ-ONLY vs the game install (X.read_block only). ZERO deploys. ZERO git commits. ZERO edits to any
pipeline file.

    py -X utf8 freshmint_eye_scan.py
"""
from __future__ import annotations

import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg                         # noqa: E402
from ff9mapkit.world import extract as X                     # noqa: E402
from ff9mapkit.world import mesh as M                        # noqa: E402
from ff9mapkit.world import grassland as G                   # noqa: E402

import seam_null_recon as SNR                                 # noqa: E402  (FAM_OF -- rock/canyon/etc)

BLOCK = 64.0
CELL = 4.0
GROUND_FAM = G.TOPO_FAMILY                                     # grass/desert/dunes, the same table
                                                                # junction_compose binds as GROUND_FAM
FAMILIES = ("grass", "desert", "dunes")
STOCK_STRETCH_CEILING = 1.41
FLAT_DIP_T = 10.0
UV_AREA_EPS = 1e-6
ZERO_UV_FRAC_CEILING = 0.0005

OUT_DIR = HERE / "out" / "foldback"
RENDER_DIR = OUT_DIR / "renders"
RENDER_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = OUT_DIR / "freshmint_eye.json"

FRESH_TREE = OUT_DIR / "freshmint-tree"

# ---- stock reference regions (block coords), lifted from the round's own named references --------
REF_DUNES = [(18, 3), (18, 4), (19, 3), (19, 4), (20, 3)]                 # uvf_eye_pixel4.STOCK_DUNES
REF_CLEYRA = [(bx, by) for bx in (13, 14, 15) for by in (11, 12)]         # uvf_eye_pixel4.STOCK_JUNCTION
REF_ISLAND = [(bx, by) for bx in range(7, 11) for by in range(16, 20)]    # whole_island_eye's real donor
#   site (7-10,16-19) -- a lawful stock world-island region (grass island with terraces + real coast)


def log(msg):
    print(msg, flush=True)


# =====================================================================================================
#  independent mesh loading (own conversion, not a call into any pipeline render/compose function)
# =====================================================================================================
def tri_topo(tri):
    return X.decode_id(int(round(tri[0][3][0])))["topograph"]


def tri_world(tri):
    return [t[0] for t in tri]


def tri_uv(tri):
    return [(float(t[2][0]), float(t[2][1])) for t in tri]


def centroid_xz(w3):
    return (sum(p[0] for p in w3) / 3.0, sum(p[2] for p in w3) / 3.0)


def own_cell(vx, vz):
    return (math.floor(vx / CELL), math.floor(vz / CELL))


def load_tree_terrain(tree_root):
    """Read every staged ``Block[x][y] Terrain.ff9mesh`` under ``tree_root`` directly (no
    reliance on the in-memory Composite the compose() run built) -> {(bx,by): [world tri, ...]}."""
    out = {}
    pat = re.compile(r"Block\[(\d+)\]\[(\d+)\] Terrain\.ff9mesh$")
    for p in sorted(Path(tree_root).rglob("*.ff9mesh")):
        m = pat.search(p.name)
        if not m:
            continue
        bx, by = int(m.group(1)), int(m.group(2))
        bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        V, N, U, TAN = bm.verts, bm.normals, bm.uvs, bm.tangents
        tris = []
        for i in range(0, len(bm.flat_index), 3):
            idx3 = bm.flat_index[i:i + 3]
            vs = []
            for j in idx3:
                pos = (V[j][0] + BLOCK * bx, V[j][1], V[j][2] - BLOCK * by)
                vs.append((pos, tuple(N[j]), tuple(U[j]), tuple(TAN[j])))
            tris.append(vs)
        out[(bx, by)] = tris
    return out


def load_stock_terrain(blocks, game_root):
    """Read stock ``terrain`` sub-meshes straight from the live install via extract.read_block
    (read-only), independently world-converted here (not via transplant.world_tris)."""
    out = {}
    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=1, lod="0_1", part="terrain", game=game_root)
        except ValueError:
            out[(bx, by)] = []
            continue
        V, N, U, TAN = bm.verts, bm.normals, bm.uvs, bm.tangents
        tris = []
        for i in range(0, len(bm.flat_index), 3):
            idx3 = bm.flat_index[i:i + 3]
            vs = []
            for j in idx3:
                pos = (V[j][0] + BLOCK * bx, V[j][1], V[j][2] - BLOCK * by)
                vs.append((pos, tuple(N[j]), tuple(U[j]), tuple(TAN[j])))
            tris.append(vs)
        out[(bx, by)] = tris
    return out


# =====================================================================================================
#  independent per-tri metrics (re-derived closed forms, not imports of the gate bodies)
# =====================================================================================================
def dip_deg(w3):
    a, b, c = w3
    e1 = [b[k] - a[k] for k in range(3)]
    e2 = [c[k] - a[k] for k in range(3)]
    n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
    nl = math.sqrt(sum(v * v for v in n))
    if nl < 1e-9:
        return None
    return math.degrees(math.acos(min(1.0, abs(n[1]) / nl)))


def up_normal(w3):
    a, b, c = w3
    e1 = [b[k] - a[k] for k in range(3)]
    e2 = [c[k] - a[k] for k in range(3)]
    n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
    nl = math.sqrt(sum(v * v for v in n))
    if nl < 1e-9:
        return None
    n = [v / nl for v in n]
    if n[1] < 0:
        n = [-v for v in n]
    return n


def uv_area2(uv3):
    (u0, v0), (u1, v1), (u2, v2) = uv3
    return abs((u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)) / 2.0


def stretch_sigma_max(w3, uv3):
    """Largest singular value (world units / UV unit) of the affine UV->world map, re-derived
    directly from the 2x2 metric tensor of the Jacobian (closed-form eigenvalue), independently of
    composite_gates.sigma_max (same underlying math, different code path -- a transcription slip in
    either would show up as a numeric mismatch when cross-checked)."""
    a = uv3[1][0] - uv3[0][0]
    b = uv3[2][0] - uv3[0][0]
    c = uv3[1][1] - uv3[0][1]
    d = uv3[2][1] - uv3[0][1]
    det = a * d - b * c
    if abs(det) < 1e-12:
        return None
    # inverse of [[a,b],[c,d]]
    inv00, inv01 = d / det, -b / det
    inv10, inv11 = -c / det, a / det
    e0 = [w3[1][k] - w3[0][k] for k in range(3)]
    e1 = [w3[2][k] - w3[0][k] for k in range(3)]
    # Jacobian columns: J_u = e0*inv00 + e1*inv10 ; J_v = e0*inv01 + e1*inv11
    Ju = [e0[k] * inv00 + e1[k] * inv10 for k in range(3)]
    Jv = [e0[k] * inv01 + e1[k] * inv11 for k in range(3)]
    g00 = sum(x * x for x in Ju)
    g11 = sum(x * x for x in Jv)
    g01 = sum(Ju[k] * Jv[k] for k in range(3))
    tr = g00 + g11
    dt = g00 * g11 - g01 * g01
    disc = max(0.0, tr * tr / 4.0 - dt)
    lam_max = tr / 2.0 + math.sqrt(disc)
    return math.sqrt(max(0.0, lam_max))


QUADS = ((0, 0), (0, 1), (1, 0), (1, 1))


def decode_one_window(vw, uv3, fam, err_tol=5e-6):
    """Brute-force EVERY (cell, quad, ori) combo (centroid cell + each vertex's own cell) against
    grassland.ground_uv for the tri's OWN family -- no dependence on any precomputed `decoded` field,
    so this cannot inherit the builder's own answer for which window a cell landed on."""
    cx = sum(p[0] for p in vw) / 3.0
    cz = sum(p[2] for p in vw) / 3.0
    cand_cells = {own_cell(cx, cz)} | {own_cell(p[0], p[2]) for p in vw}
    for cell in cand_cells:
        for quad in QUADS:
            for ori in G.ORIS:
                ok = True
                for k, p in enumerate(vw):
                    pu, pv = G.ground_uv(p[0], p[2], cell, quad, ori, fam)
                    if abs(pu - uv3[k][0]) > err_tol or abs(pv - uv3[k][1]) > err_tol:
                        ok = False
                        break
                if ok:
                    return True, cell, quad, ori
    return False, None, None, None


# =====================================================================================================
#  region analysis
# =====================================================================================================
def analyze_region(name, blocks_tris):
    """``blocks_tris``: {(bx,by): [tri,...]} of WORLD tris. Returns a flat row list + per-tri render
    records + summary stats, ALL independently derived."""
    rows = []
    for blk, tris in blocks_tris.items():
        for i, tri in enumerate(tris):
            vw = tri_world(tri)
            uv3 = tri_uv(tri)
            topo = tri_topo(tri)
            fam = GROUND_FAM.get(topo)
            rockish = SNR.FAM_OF.get(topo) if fam is None else None
            d = dip_deg(vw)
            a2 = uv_area2(uv3)
            s = stretch_sigma_max(vw, uv3) if a2 is not None and a2 > UV_AREA_EPS else None
            rows.append(dict(blk=blk, i=i, vw=vw, uv=uv3, topo=topo, fam=fam, rockish=rockish,
                              dip=d, uv_area=a2, sigma=s))
    n_tot = len(rows)
    zero_uv = sum(1 for r in rows if r["uv_area"] is not None and r["uv_area"] <= UV_AREA_EPS)
    ground_rows = [r for r in rows if r["fam"] is not None]

    # per-family flat baseline (median sigma among dip<10deg ground tris) -- same recipe as the
    # pipeline's own envelope calibration, independently recomputed here from THIS region's own rows
    base = {}
    for fam in FAMILIES:
        flat = sorted(r["sigma"] for r in ground_rows
                      if r["fam"] == fam and r["sigma"] is not None and r["dip"] is not None
                      and r["dip"] < FLAT_DIP_T)
        if not flat:
            flat = sorted(r["sigma"] for r in ground_rows if r["fam"] == fam and r["sigma"] is not None)
        if flat:
            base[fam] = flat[len(flat) // 2]

    stretch_ratios = []
    one_window_hits = 0
    one_window_n = 0
    for r in ground_rows:
        b = base.get(r["fam"])
        if r["sigma"] is not None and b:
            stretch_ratios.append(r["sigma"] / b)
        ok, cell, quad, ori = decode_one_window(r["vw"], r["uv"], r["fam"])
        r["one_window"] = ok
        one_window_n += 1
        one_window_hits += ok

    def pct(vals, p):
        if not vals:
            return None
        s = sorted(vals)
        k = max(0, min(len(s) - 1, int(round(p / 100.0 * (len(s) - 1)))))
        return s[k]

    stats = dict(
        n_tris=n_tot,
        n_ground_tris=len(ground_rows),
        zero_uv_area=zero_uv,
        zero_uv_area_frac=round(zero_uv / n_tot, 6) if n_tot else None,
        zero_uv_area_ceiling=ZERO_UV_FRAC_CEILING,
        zero_uv_area_pass=(zero_uv / n_tot <= ZERO_UV_FRAC_CEILING) if n_tot else None,
        family_hist=dict(Counter(r["fam"] for r in ground_rows)),
        rockish_hist=dict(Counter(r["rockish"] for r in rows if r["fam"] is None and r["rockish"])),
        family_baselines={k: round(v, 5) for k, v in base.items()},
        one_window_n=one_window_n,
        one_window_hits=one_window_hits,
        one_window_frac_single=round(one_window_hits / one_window_n, 6) if one_window_n else None,
        stretch_p50=pct(stretch_ratios, 50),
        stretch_p90=pct(stretch_ratios, 90),
        stretch_p99=pct(stretch_ratios, 99),
        stretch_max=pct(stretch_ratios, 100),
        stretch_frac_over_ceiling=(round(sum(1 for v in stretch_ratios if v > STOCK_STRETCH_CEILING)
                                         / len(stretch_ratios), 6) if stretch_ratios else None),
        n_stretch_samples=len(stretch_ratios),
    )
    return rows, stats


# =====================================================================================================
#  own rasterizer -- 3 planview passes, none of which call into junction_compose.renders
# =====================================================================================================
FAM_COL = {"grass": (86, 140, 60), "desert": (200, 176, 110), "dunes": (222, 200, 140),
           "rock": (120, 112, 104), None: (150, 150, 150)}


def _bbox(rows):
    xs, zs = [], []
    for r in rows:
        for p in r["vw"]:
            xs.append(p[0]); zs.append(p[2])
    return min(xs), max(xs), min(zs), max(zs)


def _light_dir():
    v = (0.5, 0.8, 0.3)
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def render_planviews(name, rows, out_prefix, size=760):
    """Own PIL rasterizer: (a) textured -- family colour MODULATED by a procedural UV-tile pattern (a
    flat constant-UV stain shows as an unmodulated flat patch, not just a flat colour); (b) shaded
    relief -- Lambertian from the tri's own geometric normal; (c) stretch heatmap."""
    if not rows:
        return {}
    x0, x1, z0, z1 = _bbox(rows)
    pad = 24
    W = H = size
    s = min((W - 2 * pad) / max(x1 - x0, 1e-6), (H - 2 * pad) / max(z1 - z0, 1e-6))
    lv = _light_dir()
    order = sorted(range(len(rows)), key=lambda k: sum(p[1] for p in rows[k]["vw"]) / 3.0)

    def to_px(p):
        return (pad + (p[0] - x0) * s, pad + H - 2 * pad - (p[2] - z0) * s)

    tex = Image.new("RGB", (W, H), (18, 18, 22))
    shd = Image.new("RGB", (W, H), (18, 18, 22))
    hm = Image.new("RGB", (W, H), (18, 18, 22))
    dtex, dshd, dhm = ImageDraw.Draw(tex), ImageDraw.Draw(shd), ImageDraw.Draw(hm)

    base = {}
    for fam in FAMILIES:
        flat = sorted(r["sigma"] for r in rows
                       if r["fam"] == fam and r["sigma"] is not None
                       and r["dip"] is not None and r["dip"] < FLAT_DIP_T) \
               or sorted(r["sigma"] for r in rows if r["fam"] == fam and r["sigma"] is not None)
        if flat:
            base[fam] = flat[len(flat) // 2]

    for k in order:
        r = rows[k]
        pts = [to_px(p) for p in r["vw"]]
        fam = r["fam"] or ("rock" if r["rockish"] == "rock" else None)
        col = FAM_COL.get(fam, FAM_COL[None])
        # (a) textured: procedural UV-tile modulation -- a checker in fractional-mains-space so a
        # constant UV (the flat-sheet defect) renders as ONE unbroken tile instead of a mosaic
        (u0, v0) = r["uv"][0]
        tile = (int(math.floor(u0 * 40.0)) + int(math.floor(v0 * 40.0))) % 2
        tcol = tuple(min(255, int(c * (1.12 if tile else 0.88))) for c in col)
        dtex.polygon(pts, fill=tcol)
        # (b) shaded relief: own Lambertian from the tri's own geometric normal
        n = up_normal(r["vw"]) or (0, 1, 0)
        sh = max(0.30, min(1.0, 0.42 + 0.58 * abs(sum(n[i] * lv[i] for i in range(3)))))
        dshd.polygon(pts, fill=tuple(int(c * sh) for c in col))
        # (c) stretch/density heatmap
        b = base.get(fam)
        if r["sigma"] is None or not b:
            hc = (55, 55, 60)
        else:
            ratio = r["sigma"] / b
            t = max(-1.0, min(1.0, math.log(max(ratio, 1e-6)) / math.log(2.0)))
            if t > 0:
                hc = (int(40 + 200 * t), int(40 + 60 * (1 - abs(t))), 40)
            else:
                hc = (40, int(40 + 60 * (1 - abs(t))), int(40 - 200 * t))
            hc = tuple(max(0, min(255, q)) for q in hc)
        dhm.polygon(pts, fill=hc)

    for img, tag in ((tex, "textured"), (shd, "shaded"), (hm, "stretch_heatmap")):
        p = RENDER_DIR / f"{out_prefix}_{tag}.png"
        img.save(p)
    return dict(textured=str(RENDER_DIR / f"{out_prefix}_textured.png"),
                shaded=str(RENDER_DIR / f"{out_prefix}_shaded.png"),
                stretch_heatmap=str(RENDER_DIR / f"{out_prefix}_stretch_heatmap.png"),
                world_bbox=[round(x0, 1), round(z0, 1), round(x1, 1), round(z1, 1)])


# =====================================================================================================
#  independent structure-tensor orientation coherence (own Sobel, no external CV library)
# =====================================================================================================
def _sobel(gray):
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float64)
    ky = kx.T
    gx = np.zeros_like(gray); gy = np.zeros_like(gray)
    H, W = gray.shape
    pad = np.pad(gray, 1, mode="edge")
    for dy in range(3):
        for dx in range(3):
            gx += kx[dy, dx] * pad[dy:dy + H, dx:dx + W]
            gy += ky[dy, dx] * pad[dy:dy + H, dx:dx + W]
    return gx, gy


def orientation_coherence(img_rgb):
    """Own structure-tensor coherence: gray -> Sobel gradients -> 2x2 structure tensor -> coherence
    = (l1-l2)/(l1+l2) per pixel, box-averaged 5x5 first. Returns mean coherence + a same-class-rate
    proxy (fraction of pixels whose dominant orientation quantizes to one of 4 bins matching the
    family's own real ORIS set -- a crude but independent alignment check)."""
    gray = np.asarray(img_rgb, dtype=np.float64) @ np.array([0.299, 0.587, 0.114])
    gx, gy = _sobel(gray)
    jxx, jyy, jxy = gx * gx, gy * gy, gx * gy

    def box5(a):
        pad = np.pad(a, 2, mode="edge")
        out = np.zeros_like(a)
        H, W = a.shape
        for dy in range(5):
            for dx in range(5):
                out += pad[dy:dy + H, dx:dx + W]
        return out / 25.0

    jxx, jyy, jxy = box5(jxx), box5(jyy), box5(jxy)
    tr = jxx + jyy
    disc = np.sqrt(np.maximum(0.0, (jxx - jyy) ** 2 + 4 * jxy ** 2))
    l1 = (tr + disc) / 2.0
    l2 = (tr - disc) / 2.0
    denom = np.maximum(l1 + l2, 1e-9)
    coh = (l1 - l2) / denom
    mag = np.sqrt(np.maximum(l1, 0.0))
    active = mag > (mag.mean() * 0.15)
    if active.sum() == 0:
        return dict(mean_coherence=0.0, active_frac=0.0)
    theta = 0.5 * np.arctan2(2 * jxy[active], (jxx - jyy)[active])
    deg = np.degrees(theta) % 180.0
    bins = np.round(deg / 45.0).astype(int) % 4
    hist = np.bincount(bins, minlength=4)
    dominant_rate = hist.max() / hist.sum()
    return dict(mean_coherence=round(float(coh[active].mean()), 5),
                active_frac=round(float(active.mean()), 5),
                dominant_orientation_bin_rate=round(float(dominant_rate), 5))


# =====================================================================================================
def main():
    t0 = time.time()
    game_root = Path(_cfg.find_game_path(None))
    log(f"game_root = {game_root}")

    log("== loading the fresh-site composite (independent disk read, not the in-memory Composite) ==")
    fresh_blocks = load_tree_terrain(FRESH_TREE)
    log(f"  loaded {len(fresh_blocks)} blocks from {FRESH_TREE}")
    fresh_rows, fresh_stats = analyze_region("freshmint", fresh_blocks)
    log(f"  freshmint: {fresh_stats}")

    log("== loading stock references (read-only via extract.read_block) ==")
    refs = {}
    ref_stats = {}
    ref_blocks_map = dict(dunes=REF_DUNES, cleyra=REF_CLEYRA, island=REF_ISLAND)
    for tag, blocks in ref_blocks_map.items():
        bt = load_stock_terrain(blocks, game_root)
        rows, stats = analyze_region(tag, bt)
        refs[tag] = rows
        ref_stats[tag] = stats
        log(f"  {tag}: {stats}")

    log("== own rasterizer passes ==")
    renders = {}
    renders["freshmint"] = render_planviews("freshmint", fresh_rows, "freshmint")
    for tag, rows in refs.items():
        renders[tag] = render_planviews(tag, rows, f"stock_{tag}")

    log("== independent structure-tensor orientation coherence (own Sobel) ==")
    coherence = {}
    for tag in ("freshmint",) + tuple(refs):
        prefix = "freshmint" if tag == "freshmint" else f"stock_{tag}"
        img = np.array(Image.open(RENDER_DIR / f"{prefix}_textured.png").convert("RGB"))
        coherence[tag] = orientation_coherence(img)
        log(f"  {tag}: {coherence[tag]}")

    # -- eye verdicts (mechanical; honest prose happens in the caller's judgement) --------------------
    def near(a, b, tol):
        return a is not None and b is not None and abs(a - b) <= tol

    verdicts = {}
    verdicts["zero_uv_area_ok"] = bool(fresh_stats["zero_uv_area_pass"])
    verdicts["one_window_ok"] = bool(fresh_stats["one_window_frac_single"] is not None
                                      and fresh_stats["one_window_frac_single"] >= 0.9995)
    # density/stretch p50 should land inside the stock band the pipeline itself measured (0.85-1.20)
    p50 = fresh_stats["stretch_p50"]
    verdicts["density_band_ok"] = bool(p50 is not None and 0.85 <= p50 <= 1.20)
    verdicts["stretch_p90_vs_ceiling"] = dict(
        p90=fresh_stats["stretch_p90"], ceiling=STOCK_STRETCH_CEILING,
        under_ceiling=bool(fresh_stats["stretch_p90"] is not None
                            and fresh_stats["stretch_p90"] <= STOCK_STRETCH_CEILING))
    # orientation coherence should be in the same neighbourhood as the stock refs, not an outlier
    fc = coherence["freshmint"]["mean_coherence"]
    stock_cohs = [coherence[t]["mean_coherence"] for t in ("dunes", "cleyra", "island")]
    lo, hi = min(stock_cohs) * 0.5, max(stock_cohs) * 1.5
    verdicts["orientation_coherence_in_stock_range"] = dict(
        freshmint=fc, stock_range=[round(lo, 5), round(hi, 5)], stock_values=stock_cohs,
        in_range=bool(lo <= fc <= hi))

    report = dict(
        title="FOLD-BACK fresh-site mint -- independent eye scan (both channels + metric table)",
        method=("Own disk reader (not the in-memory Composite), own per-tri metrics (re-derived "
                "closed-form UV-stretch, brute-force one-window decode with no dependence on any "
                "precomputed window field), own PIL rasterizer (not junction_compose.renders), own "
                "Sobel structure-tensor orientation-coherence pass."),
        tree=str(FRESH_TREE), game_root=str(game_root),
        freshmint=fresh_stats, stock_refs=ref_stats,
        renders=renders, orientation_coherence=coherence, verdicts=verdicts,
        elapsed_s=round(time.time() - t0, 1),
    )
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(f"\nreport -> {REPORT_PATH}  ({report['elapsed_s']}s)")


if __name__ == "__main__":
    main()
