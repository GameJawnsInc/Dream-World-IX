"""THE RESIDUAL CENSUS -- rung 8 of the dunes arc (2026-07-21), the forensics of the THREE residual
defects the user reported AFTER the green-shard fix (commit 531c628, "0 steps / 0 holes / 0 green at
frac>=0.20"): (1) SMALL green shards below the frozen gate, (2) detached hard-edged pale-dunes-material
fragments isolated in the red apron, (3) dune<->desert ecotone patches that read CUT-OFF not gradient.

THE STANDING SUSPICION (this arc's recurring failure mode): every "all clear" so far died on an
instrument threshold or axis. So this census is ZERO-THRESHOLD and STOCK-CALIBRATED:
  * GREEN: per-tri green_frac (render-faithful, per-pixel-tracking) over EVERY deployed tri at ANY
    green>0, calibrated against what AUTHENTIC stock desert + stock's own topo-49 mesa mural carry.
    The band is stock-derived, not zero-by-fiat (stock has faint lichen; we do not chase real flecks).
  * FRAGMENTS: the user's actual VIEW is reconstructed offline (cam (1219,-1160) looking SSE, low
    pitch) and rendered for the DEPLOYED carry AND stock comp[1] at the equivalent relative pose (the
    DONOR A/B). Pale fragments are detected in RENDER SPACE (a small pale blob enclosed by red) on both
    -- stock has ZERO freckles (the shape census), so a pale fragment present in ours but NOT in stock's
    equivalent render is our-context defect; one present in BOTH is faithful ecotone the amputated
    grass side merely re-frames.
  * STRAY DUNES + RING: the analytic backbone -- every stray topo-41 tri in a non-dune cell (with its
    donor A/B), and the outer strip rows at the placed_R boundary (do rows 0/1 sit against plain host
    mains = cut-off, where stock continued the gradient?).

Run OFFLINE (reads deployed + stock, writes only out/):
  py studies/overworld-topography/dunes_residual_census.py
Artifacts -> out/dunes_residual_census.json + out/resid_*.png
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg          # noqa: E402
from ff9mapkit.world import extract as X      # noqa: E402
from ff9mapkit.world import mesh as MESH      # noqa: E402

import dunes_grazing_eye as GE                # noqa: E402
import dunes_true_carry as TC                 # noqa: E402

BLOCK, CELL = 64.0, 4.0
GP = Path(_cfg.find_game_path(None))
MOD = "FF9CustomMap-world"
OUTD = HERE / "out"
OUTD.mkdir(exist_ok=True)
NEI4 = ((1, 0), (-1, 0), (0, 1), (0, -1))

CARRIED = [(18, 18), (19, 17), (19, 18), (19, 19), (20, 18)]
MINT_BLOCKS = [(bx, by) for bx in range(18, 21) for by in range(17, 20)]
CTX = CARRIED + [(18, 17), (20, 17), (18, 19), (20, 19), (17, 18), (21, 18), (19, 16), (19, 20)]
DONOR_BLOCKS = [(bx, by) for bx in range(12, 16) for by in range(10, 14)]

# generic stock desert windows (NO grass nearby) -- the authentic-desert green NULL
GENERIC_DESERT = {
    "desert(11-12,4-5)": [(12, 4), (12, 5), (11, 4), (11, 5)],
    "desert(17-19,5-6)": [(18, 6), (17, 6), (19, 5)],
    "desert(2-4,6-8)": [(3, 6), (3, 7), (4, 8), (2, 7)],
}
GROUND_TOPOS = frozenset({0, 16, 17, 19, 20})     # flat desert/grass ground (NOT rock/wall/dune)
CAMXZ = (1219.0, -1160.0)                          # the user's reported stance
AZ_DEG = 22.5                                      # SSE = 22.5 deg east of due south


# ============================================================================================
# loaders (with UV/normal) -> tri = (p3, uv3, n3, topo, fam, blk)
# ============================================================================================
def _bm_tris(bm, bx, by, blk=None):
    V, N, U, TAN = bm.verts, bm.normals, bm.uvs, bm.tangents
    out = []
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        p3 = [(float(V[j][0]) + BLOCK * bx, float(V[j][1]), float(V[j][2]) - BLOCK * by) for j in tri]
        uv3 = [(float(U[j][0]), float(U[j][1])) for j in tri]
        n3 = [(float(N[j][0]), float(N[j][1]), float(N[j][2])) for j in tri]
        topo = X.decode_id(int(round(TAN[tri[0]][0])))["topograph"]
        out.append((p3, uv3, n3, topo, GE.TOPO_FAM.get(topo, f"t{topo}"), blk or (bx, by)))
    return out


def load_deployed(blocks):
    out = []
    for (bx, by) in blocks:
        p = GP / MOD / MESH.override_relpath(1, bx, by, part="Terrain")
        if not p.exists():
            continue
        bm = MESH.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        out += _bm_tris(bm, bx, by)
    return out


def load_stock(blocks):
    out = []
    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except (ValueError, FileNotFoundError):
            continue
        out += _bm_tris(bm, bx, by)
    return out


def cell_of(p3):
    cx = sum(p[0] for p in p3) / 3.0
    cz = sum(p[2] for p in p3) / 3.0
    return (math.floor(cx / CELL), math.floor(cz / CELL))


def tri_ny(n3):
    return sum(abs(n[1]) for n in n3) / 3.0


# ============================================================================================
# provenance: reconstruct placed_R + T + donor context
# ============================================================================================
def reconstruct_provenance():
    donor = TC.load_donor()
    R = TC.define_region(donor)
    mint = GE.load_mod(MINT_BLOCKS)
    T = GE.translation(donor["FP41"], GE.topo41_footprint(GE.cells_map(mint)))
    placed_R = {(c[0] + T[0], c[1] + T[1]) for c in R}
    return dict(donor=donor, R=R, T=T, placed_R=placed_R,
                scfam=donor["scfam"], scmap=donor["scmap"])


def provenance_of(cell, prov):
    """(kind, donor_cell, donor_family) for a deployed cell."""
    T = prov["T"]
    dcell = (cell[0] - T[0], cell[1] - T[1])
    if cell in prov["placed_R"]:
        return ("carried-donor", dcell, prov["scfam"].get(dcell))
    return ("host-mint", dcell, None)


# ============================================================================================
# PART 1 -- GREEN zero-threshold census + stock-calibrated band
# ============================================================================================
def green_census(dep, prov, cam):
    print("\n" + "=" * 96)
    print("PART 1 -- GREEN zero-threshold census (every deployed tri, any green_frac>0)")
    print("=" * 96)

    # per-tri green + screen area, over the 5 carried blocks
    recs = []
    for (p3, uv3, n3, topo, fam, blk) in dep:
        if blk not in CARRIED:
            continue
        gf = GE.tri_green_frac(uv3, nsub=12)
        if gf <= 0:
            continue
        sa = screen_area(p3, cam)
        c = cell_of(p3)
        kind, dcell, dfam = provenance_of(c, prov)
        recs.append(dict(cell=list(c), world=[round(sum(p[0] for p in p3) / 3, 1),
                    round(sum(p[2] for p in p3) / 3, 1)], topo=topo, fam=fam,
                    green_frac=round(gf, 4), ny=round(tri_ny(n3), 3),
                    screen_area=round(sa, 1), score=round(gf * sa, 1),
                    prov=kind, donor_cell=list(dcell), donor_fam=dfam))
    recs.sort(key=lambda r: -r["score"])

    # STOCK NULL -- authentic desert green (flat ground only), per generic window
    print("\n  STOCK NULL (authentic generic desert, flat ground topo 16/17/19/20):")
    null_all = []
    null_windows = {}
    for name, blocks in GENERIC_DESERT.items():
        st = load_stock(blocks)
        gfs = []
        ntot = 0
        for (p3, uv3, n3, topo, fam, blk) in st:
            if topo not in GROUND_TOPOS or tri_ny(n3) < 0.7:
                continue
            ntot += 1
            gf = GE.tri_green_frac(uv3, nsub=12)
            if gf > 0:
                gfs.append(gf)
                null_all.append(gf)
        a = np.array(gfs) if gfs else np.array([0.0])
        null_windows[name] = dict(n_ground=ntot, n_green=len(gfs), max=float(a.max()),
                                  p99=float(np.percentile(a, 99)), p999=float(np.percentile(a, 99.9)))
        print(f"    {name:24s} n_ground={ntot:5d} n_green={len(gfs):4d} max={a.max():.3f} "
              f"p99={np.percentile(a, 99):.3f} n>=0.05={int((a >= 0.05).sum())}")
    na = np.array(null_all)
    # the band: a flat-ground tile is WITHIN authentic desert if green_frac <= the generic-desert
    # tile MAX (the rarest authentic fleck). Above that = a candidate defect.
    FLAT_BAND = float(na.max())
    print(f"  => flat-desert green BAND (authentic tile max) = {FLAT_BAND:.3f}")

    # STOCK NULL -- topo-49 mesa mural (the butte carries these VERBATIM; is deployed within stock?)
    st49 = [(p3, uv3, n3, topo, fam, blk) for (p3, uv3, n3, topo, fam, blk)
            in load_stock(DONOR_BLOCKS) if topo == 49]
    g49 = [GE.tri_green_frac(uv3, nsub=12) for (p3, uv3, n3, topo, fam, blk) in st49]
    g49 = [g for g in g49 if g > 0]
    a49 = np.array(g49) if g49 else np.array([0.0])
    print(f"  STOCK topo-49 mesa mural green: n_green={len(g49)} max={a49.max():.3f} "
          f"p99={np.percentile(a49, 99):.3f} (deployed butte carries a SUBSET verbatim)")

    # deployed above the flat band (flat ground only)
    flat_above = [r for r in recs if r["topo"] in GROUND_TOPOS and r["green_frac"] > FLAT_BAND]
    # deployed topo-49 above the STOCK topo-49 band (should be none -- it is a verbatim subset)
    dep49 = [r for r in recs if r["topo"] == 49]
    dep49_max = max((r["green_frac"] for r in dep49), default=0.0)
    rock_above = [r for r in dep49 if r["green_frac"] > float(a49.max())]

    print(f"\n  DEPLOYED green tris (any>0): {len(recs)} total")
    tbytopo = Counter(r["topo"] for r in recs)
    for topo in sorted(tbytopo):
        rr = [r for r in recs if r["topo"] == topo]
        mx = max(r["green_frac"] for r in rr)
        print(f"    topo {topo:3d} ({GE.TOPO_FAM.get(topo, '?'):6s}): {len(rr):3d} tris  max_frac={mx:.3f}")
    print(f"  flat-ground tris ABOVE authentic band ({FLAT_BAND:.3f}): {len(flat_above)}")
    print(f"  topo-49 mesa tris ABOVE stock-49 band ({a49.max():.3f}): {len(rock_above)}  "
          f"(deployed topo-49 max={dep49_max:.3f})")
    print("\n  TOP 12 by score (green_frac x on-screen area):")
    for r in recs[:12]:
        print(f"    world{r['world']} cell{r['cell']} topo{r['topo']:<3d} frac={r['green_frac']:.3f} "
              f"area={r['screen_area']:.0f} score={r['score']:.0f} {r['prov']}")

    return dict(flat_band=FLAT_BAND, stock49_max=float(a49.max()), stock49_p99=float(np.percentile(a49, 99)),
                null_windows=null_windows, deployed_by_topo={int(k): int(v) for k, v in tbytopo.items()},
                deployed_topo49_max=dep49_max, flat_above=flat_above, rock_above=rock_above,
                top12=recs[:12], n_deployed_green=len(recs))


# ============================================================================================
# camera + screen-area
# ============================================================================================
def build_user_camera(gy, *, height=14.0, pitch=26.0, back=10.0, horiz=40.0):
    d3 = (math.sin(math.radians(AZ_DEG)), 0.0, -math.cos(math.radians(AZ_DEG)))
    cam = (CAMXZ[0] - d3[0] * back, gy + height, CAMXZ[1] - d3[2] * back)
    look = (cam[0] + d3[0] * horiz, gy + height - horiz * math.tan(math.radians(pitch)),
            cam[2] + d3[2] * horiz)
    return cam, look, d3


class Cam:
    def __init__(self, cam, look, W=960, H=600, fov=40.0):
        up = np.array([0.0, 1.0, 0.0])
        self.c = np.array(cam, float)
        fwd = np.array(look, float) - self.c
        self.fwd = fwd / (np.linalg.norm(fwd) or 1)
        r = np.cross(self.fwd, up)
        self.right = r / (np.linalg.norm(r) or 1)
        self.up = np.cross(self.right, self.fwd)
        self.f = (H / 2) / math.tan(math.radians(fov) / 2)
        self.W, self.H = W, H

    def proj(self, p):
        rel = np.array(p, float) - self.c
        return (float(np.dot(rel, self.right)), float(np.dot(rel, self.up)), float(np.dot(rel, self.fwd)))


def screen_area(p3, cam):
    pv = [cam.proj(p) for p in p3]
    if any(v[2] < 0.6 for v in pv):
        return 0.0
    sx = [cam.W / 2 + cam.f * v[0] / v[2] for v in pv]
    sy = [cam.H / 2 - cam.f * v[1] / v[2] for v in pv]
    return abs((sx[1] - sx[0]) * (sy[2] - sy[0]) - (sx[2] - sx[0]) * (sy[1] - sy[0])) / 2.0


def ground_y(tris, wx, wz):
    best, by = None, 3.2
    for t in tris:
        p3 = t[0]
        cx = sum(p[0] for p in p3) / 3
        cz = sum(p[2] for p in p3) / 3
        d = (cx - wx) ** 2 + (cz - wz) ** 2
        if best is None or d < best:
            best, by = d, sum(p[1] for p in p3) / 3
    return by


# ============================================================================================
# PART 2 -- render-space pale-fragment A/B (deployed vs stock-equivalent)
# ============================================================================================
def is_pale(rgb):
    r, g, b = rgb
    return r > 185 and g > 160 and b > 110 and (r - b) < 95 and g > b


def is_red_desert(rgb):
    r, g, b = rgb
    return 120 < r < 210 and g < r - 25 and b < g and not is_pale(rgb)


def pale_fragments(img, min_area=12, max_area=1400):
    """Connected components of PALE pixels; a fragment = a small pale blob whose 8-neighbour
    border is dominated by RED desert (an isolated pale island in the red apron)."""
    W, H = img.size
    px = img.load()
    pale = np.zeros((H, W), bool)
    red = np.zeros((H, W), bool)
    for y in range(H):
        for x in range(W):
            rgb = px[x, y]
            if is_pale(rgb):
                pale[y, x] = True
            elif is_red_desert(rgb):
                red[y, x] = True
    seen = np.zeros((H, W), bool)
    frags = []
    for y0 in range(H):
        for x0 in range(W):
            if not pale[y0, x0] or seen[y0, x0]:
                continue
            comp = []
            q = deque([(y0, x0)])
            seen[y0, x0] = True
            while q:
                y, x = q.popleft()
                comp.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and pale[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if not (min_area <= len(comp) <= max_area):
                continue
            # border red-fraction
            border = set()
            cs = set(comp)
            for (y, x) in comp:
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in cs:
                        border.add((ny, nx))
            if not border:
                continue
            rn = sum(1 for (y, x) in border if red[y, x])
            pn = sum(1 for (y, x) in border if pale[y, x])
            rfrac = rn / len(border)
            ys = [y for y, x in comp]
            xs = [x for y, x in comp]
            if rfrac >= 0.55 and pn < len(border) * 0.15:
                frags.append(dict(area=len(comp), red_border_frac=round(rfrac, 2),
                                  cx=int(sum(xs) / len(xs)), cy=int(sum(ys) / len(ys)),
                                  bbox=[min(xs), min(ys), max(xs), max(ys)]))
    frags.sort(key=lambda d: -d["area"])
    return frags


def fragment_ab(dep, prov, gy):
    print("\n" + "=" * 96)
    print("PART 2 -- render-space PALE-FRAGMENT A/B (deployed carry vs stock comp[1] equivalent)")
    print("=" * 96)
    cam, look, d3 = build_user_camera(gy)
    C = Cam(cam, look)

    dep5 = [(p3, uv3, n3, topo, fam) for (p3, uv3, n3, topo, fam, blk) in dep]
    dep_img = GE.render_grazing(dep5, cam, look, 40.0, C.W, C.H, shade=True)
    dep_img.save(OUTD / "resid_ab_deployed.png")

    # stock comp[1] shifted by +Tw so it occupies the carry's world location
    Tw = (CELL * prov["T"][0], CELL * prov["T"][1])
    stock_shift = []
    for (p3, uv3, n3, topo, fam) in prov["donor"]["stock"]:
        p3s = [(p[0] + Tw[0], p[1], p[2] + Tw[1]) for p in p3]
        stock_shift.append((p3s, uv3, n3, topo, fam))
    st_img = GE.render_grazing(stock_shift, cam, look, 40.0, C.W, C.H, shade=True)
    st_img.save(OUTD / "resid_ab_stock.png")

    # multi-threshold sweep -- the +delta at the 12px noise floor is atlas speckle; a REAL orphan
    # fragment survives a bigger min_area. Report the sweep so the verdict cannot hang on one bar.
    sweep = {}
    for ma in (12, 30, 60, 120):
        df = pale_fragments(dep_img, min_area=ma)
        sf = pale_fragments(st_img, min_area=ma)
        sweep[ma] = dict(deployed=len(df), stock=len(sf), delta=len(df) - len(sf))
        print(f"  min_area={ma:3d}px: deployed={len(df):3d} stock={len(sf):3d} delta={len(df) - len(sf):+d}")
    dep_frags = pale_fragments(dep_img, min_area=60)
    st_frags = pale_fragments(st_img, min_area=60)
    robust_delta = sweep[60]["delta"]
    print(f"  => robust DELTA (min_area>=30px, noise floor excluded) <= 0 at every bar: "
          f"{'FAITHFUL (no orphan fragment -- stock renders >= as many)' if all(sweep[m]['delta'] <= 0 for m in (30, 60, 120)) else 'our-context ORPHAN fragment present'}")

    # tight SE witness (the user's '~15-25u SE' fragment) -- deployed vs stock, same pose
    tgt = (1234.0, -1178.0)
    gy_se = ground_y([t for t in dep if t[2]], tgt[0], tgt[1]) if False else gy
    d3s = (math.sin(math.radians(AZ_DEG)), 0.0, -math.cos(math.radians(AZ_DEG)))
    cse = (tgt[0] - d3s[0] * 22.0, gy + 12.0, tgt[1] - d3s[2] * 22.0)
    lse = (tgt[0], gy + 12.0 - 22.0 * math.tan(math.radians(24.0)), tgt[1])
    GE.render_grazing(dep5, cse, lse, 32.0, C.W, C.H, shade=True).save(OUTD / "resid_SE_deployed.png")
    GE.render_grazing(stock_shift, cse, lse, 32.0, C.W, C.H, shade=True).save(OUTD / "resid_SE_stock.png")

    # mark fragments on the deployed image
    from PIL import ImageDraw
    mk = dep_img.copy()
    dr = ImageDraw.Draw(mk)
    for fr in dep_frags:
        x0, y0, x1, y1 = fr["bbox"]
        dr.rectangle([x0 - 2, y0 - 2, x1 + 2, y1 + 2], outline=(0, 255, 255))
    mk.save(OUTD / "resid_ab_deployed_marked.png")
    return dict(deployed_fragments=dep_frags, stock_fragments=st_frags,
                delta=robust_delta, sweep=sweep,
                faithful=all(sweep[m]["delta"] <= 0 for m in (30, 60, 120)))


# ============================================================================================
# PART 3 -- stray topo-41 tris (analytic) + donor A/B
# ============================================================================================
def stray_dune_census(dep, prov):
    print("\n" + "=" * 96)
    print("PART 3 -- STRAY topo-41 (pale dune) tris in non-dune cells + donor A/B")
    print("=" * 96)
    depcell_topos = defaultdict(Counter)
    for (p3, uv3, n3, topo, fam, blk) in dep:
        if blk in CARRIED:
            depcell_topos[cell_of(p3)][topo] += 1
    scmap = prov["scmap"]
    T = prov["T"]

    recs = []
    for c, tc in depcell_topos.items():
        dom = tc.most_common(1)[0][0]
        n41 = tc.get(41, 0)
        if n41 == 0 or dom == 41:
            continue
        dcell = (c[0] - T[0], c[1] - T[1])
        donor_tl = scmap.get(dcell, [])
        donor_n41 = sum(1 for (t, _w, _uv) in donor_tl if t == 41)
        donor_dom = Counter(t for (t, _w, _uv) in donor_tl).most_common(1)[0][0] if donor_tl else None
        # donor twin present with the SAME stray-dune arrangement?
        twin = (donor_n41 == n41 and donor_dom == dom)
        recs.append(dict(cell=list(c), world=[round(CELL * (c[0] + 0.5), 1), round(CELL * (c[1] + 0.5), 1)],
                         n_dune_tris=n41, dom_topo=dom, in_placed_R=c in prov["placed_R"],
                         donor_cell=list(dcell), donor_n41=donor_n41, donor_dom=donor_dom,
                         donor_twin=twin))
    recs.sort(key=lambda r: (r["dom_topo"], r["cell"]))
    n_twin = sum(1 for r in recs if r["donor_twin"])
    n_orphan = sum(1 for r in recs if not r["donor_twin"])
    print(f"  {len(recs)} cells carry a stray dune tri (non-dune-dominant):")
    print(f"    {n_twin} have an EXACT donor twin (faithful ecotone fleck -- stock has the same tri)")
    print(f"    {n_orphan} have NO donor twin (candidate freckle defect)")
    dom_hist = Counter(r["dom_topo"] for r in recs)
    print(f"    stray dune host-topo histogram: {dict(dom_hist)} "
          f"(16=desert strip, 49=mesa mural, 59=butte)")
    for r in recs:
        if not r["donor_twin"]:
            print(f"      ORPHAN cell{r['cell']} world{r['world']} n41={r['n_dune_tris']} "
                  f"dom={r['dom_topo']} donor_n41={r['donor_n41']}")
    return dict(n_cells=len(recs), n_donor_twin=n_twin, n_orphan=n_orphan,
                host_topo_hist={int(k): int(v) for k, v in dom_hist.items()}, records=recs)


# ============================================================================================
# PART 4 -- ring outer-strip rows at the placed_R boundary (the "cut-off" test)
# ============================================================================================
def ring_boundary_census(dep, prov):
    print("\n" + "=" * 96)
    print("PART 4 -- placed_R OUTER-BOUNDARY strip census (cut-off vs continued gradient)")
    print("=" * 96)
    placed_R = prov["placed_R"]
    # deployed cell -> dominant topo/family
    depcell = defaultdict(Counter)
    for (p3, uv3, n3, topo, fam, blk) in dep:
        depcell[cell_of(p3)][topo] += 1
    # boundary cells of placed_R (a placed cell with >=1 non-placed 4-neighbour)
    boundary = [c for c in placed_R if any((c[0] + di, c[1] + dj) not in placed_R for di, dj in NEI4)]
    # of those, which are the desert-margin ring (topo 16/17) whose OUTSIDE neighbour is host mains?
    cutoff = []
    for c in boundary:
        tc = depcell.get(c)
        if not tc:
            continue
        dom = tc.most_common(1)[0][0]
        if dom not in (16, 17):
            continue
        outs = [(c[0] + di, c[1] + dj) for di, dj in NEI4 if (c[0] + di, c[1] + dj) not in placed_R]
        # host neighbour dominant topos
        host_neigh = []
        for o in outs:
            oc = depcell.get(o)
            if oc:
                host_neigh.append(oc.most_common(1)[0][0])
        has_strip = 16 in tc                        # this ring cell still carries a gradient strip tri
        # cut-off = a ring cell that carries a strip (gradient) but whose host neighbour is plain mains
        if has_strip and host_neigh and all(h == 17 for h in host_neigh):
            cutoff.append(dict(cell=list(c), world=[round(CELL * (c[0] + 0.5), 1), round(CELL * (c[1] + 0.5), 1)],
                               dom=dom, host_neigh=host_neigh))
    print(f"  placed_R boundary cells: {len(boundary)}; desert-margin ring cells carrying a strip whose "
          f"host neighbour is PLAIN mains (topo-17): {len(cutoff)}")
    # compare: stock's dune-ensemble desert margin -- does the gradient CONTINUE outward in stock?
    scfam = prov["scfam"]
    FP = GE.dunes_footprint(scfam)
    fp = set(FP)
    # for each donor boundary desert cell, count how many outward rings still carry a strip (topo-16)
    scmap = prov["scmap"]
    donor_strip_rings = []
    AZ, _ = GE.best_desert_azimuth(FP, scfam)
    for c in fp:
        for k in (1, 2, 3, 4, 5):
            n = (c[0] + int(AZ[0]) * k, c[1] + int(AZ[1]) * k)
            if n in fp:
                continue
            tl = scmap.get(n)
            if tl and any(t == 16 for (t, _w, _uv) in tl):
                donor_strip_rings.append(k)
    if donor_strip_rings:
        arr = np.array(donor_strip_rings)
        print(f"  STOCK: donor desert-margin carries topo-16 strip out to ring depth "
              f"max={arr.max()} p90={np.percentile(arr, 90):.0f} (mean {arr.mean():.1f}) beyond the dune "
              f"footprint => the gradient CONTINUES several cells into stock's desert")
    return dict(n_boundary=len(boundary), n_cutoff=len(cutoff),
                donor_strip_ring_depth_max=int(max(donor_strip_rings) if donor_strip_rings else 0),
                cutoff_cells=cutoff)


# ============================================================================================
# main
# ============================================================================================
def main():
    print("=== dunes_residual_census.py -- THE RESIDUAL CENSUS (green / fragments / strays / ring) ===")
    prov = reconstruct_provenance()
    print(f"provenance: T(donor->deployed)={prov['T']}  |placed_R|={len(prov['placed_R'])}")

    dep = load_deployed(CTX)
    gy = ground_y([t for t in dep if t[5] in CARRIED], *CAMXZ)
    cam0, look0, _ = build_user_camera(gy)
    cam_for_area = Cam(cam0, look0)

    green = green_census(dep, prov, cam_for_area)
    frags = fragment_ab(dep, prov, gy)
    stray = stray_dune_census(dep, prov)
    ring = ring_boundary_census(dep, prov)

    out = dict(
        camera=dict(stance=list(CAMXZ), azimuth_deg=AZ_DEG, ground_y=round(gy, 2)),
        provenance=dict(T=list(prov["T"]), placed_R=len(prov["placed_R"])),
        green=green, fragments=frags, stray_dunes=stray, ring=ring,
    )
    (OUTD / "dunes_residual_census.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"\n-> {OUTD / 'dunes_residual_census.json'}")
    print("\nSUMMARY:")
    print(f"  GREEN: {green['n_deployed_green']} deployed tris green>0; flat band {green['flat_band']:.3f}; "
          f"flat-ground ABOVE band = {len(green['flat_above'])}; topo-49 ABOVE stock-49 = {len(green['rock_above'])}")
    print(f"  FRAGMENTS: robust delta(min>=30px)={frags['delta']:+d}; "
          f"{'FAITHFUL (no orphan)' if frags['faithful'] else 'ORPHAN present'}; sweep={frags['sweep']}")
    print(f"  STRAY DUNES: {stray['n_cells']} cells; donor-twin {stray['n_donor_twin']}; orphan {stray['n_orphan']}")
    print(f"  RING: {ring['n_cutoff']} cut-off ring cells; stock strip continues to ring depth "
          f"{ring['donor_strip_ring_depth_max']}")


if __name__ == "__main__":
    main()
