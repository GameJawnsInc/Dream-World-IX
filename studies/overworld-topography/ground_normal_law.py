"""THE GROUND-NORMAL LAW -- what normals stock ships on walkable ground, and who reads them.

S3 of the GROUND-JUNCTION SYNTHESIS (studies/path-d-new-world/GROUND-JUNCTION-SYNTHESIS.md).
Round 8 of the mesa arc added a pass that REPLACES ground normals with one smooth
area-weighted field across the whole touched surface (apron + cut fragments + lifted
bench grass). Nobody measured whether that is stock-lawful. This instrument measures:

  N0 CONSUMER AUDIT -- who reads a terrain vertex normal at all? Parses the LIVE
     WorldMap/Terrain shader listing (the loose StreamingAssets/Shaders copy AND the
     bundled Material's shader) for its vertex Bind list, with WorldMap/Mobile/VertexLit
     as the positive control (a shader that DOES bind normal). Plus the engine call-site
     census over the Memoria clone (WMMesh.Normals vs TriangleNormals).
  N1 THE PALETTE -- every distinct normal on disc-1 terrain: count, quantization
     denominator, unit-length spread, nearest-neighbour angular spacing, saturation.
  N2 TOPOLOGY -- per-tri corner-constant fraction; SPLIT normals at shared positions
     (ground|ground and ground|rock), i.e. does stock ever ship a deliberate hard edge?
  N3 TILT vs SLOPE -- angle(shipped, world up) binned by the local face slope.
  N4 THE MODEL -- shipped vs (own face normal / welded area-weighted average of ground
     faces / of ALL faces / unweighted average), before AND after snapping the candidate
     to the N1 palette. Which construction reproduces the shipped bytes?
  N5 BREAKS + WELDS -- normal spread as a function of the incident-face dihedral, and
     what a ground vert ON the rock/ground weld line carries.
  N6 FLAT LOWLAND -- is it exactly (0,1,0)? (spoiler: no) -- the palette, tilt, azimuth.
  N7 THE DONOR APRON -- block (15,14)'s grass ring within 10u of the mesa's rock/ground
     weld line: all of the above, restricted, as the builder's actual carry set.
  N8 THE LIVE BENCH -- READ-ONLY over the deployed Disc9 blocks (5..7)x(7..8): how many
     of the bench's ground normals are still ON the stock palette after round 8's
     smoothing pass, and how far off-palette the rest are.

Read-only against stock disc-1, the loose shader listings, and the deployed bench.
Nothing is written outside out/. Artifacts -> out/ground_normal_law.json + out/ground_normals.png
Regenerate: py -X utf8 ground_normal_law.py
"""
from __future__ import annotations

import glob
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit import config                                  # noqa: E402
from ff9mapkit.world import extract as X                      # noqa: E402
from ff9mapkit.world import mesh as M                         # noqa: E402

OUT = Path(__file__).with_name("out") / "ground_normal_law.json"
PNG = Path(__file__).with_name("out") / "ground_normals.png"

# the engine's FOOT movement mask (ff9.cs w_movementCheckTopographID) -- {high, low}
FOOT_MASK = (0x0010667F << 32) | 0xD8FF3CFF
ROCK = {49, 7, 62, 58}
GRASS = {0, 1, 2, 3, 42}
DONOR = (15, 14)
BENCH_BLOCKS = [(bx, by) for bx in (5, 6, 7) for by in (7, 8)]
BENCH_DISC = 9
MOD_FOLDER = "FF9CustomMap-world"
UP = np.array([0.0, 1.0, 0.0])

kk = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))     # noqa: E731
walkable = lambda t: bool((FOOT_MASK >> t) & 1) if 0 <= t < 64 else False   # noqa: E731


def ang(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    la, lb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if la < 1e-12 or lb < 1e-12:
        return None
    return math.degrees(math.acos(max(-1.0, min(1.0, float(a @ b) / (la * lb)))))


def pct(a, q):
    return round(float(np.percentile(a, q)), 2) if len(a) else None


def dist(a, name, unit=""):
    return (f"{name}: n={len(a)} med {pct(a, 50)}{unit} p10 {pct(a, 10)} p90 {pct(a, 90)} "
            f"p99 {pct(a, 99)} max {round(max(a), 2) if len(a) else None}")


def load_block(bx, by):
    """(verts, normals, tangents, tri index list, per-tri topograph) for a stock disc-1 block."""
    bm = X.read_block(bx, by, disc=1, part="terrain")
    tri = [bm.flat_index[3 * t:3 * t + 3] for t in range(len(bm.flat_index) // 3)]
    topo = [X.decode_id(int(round(bm.tangents[i[0]][0])))["topograph"] for i in tri]
    return bm.verts, bm.normals, bm.tangents, tri, topo


# =============================================================================================
# N0 -- who reads a terrain vertex normal?
# =============================================================================================
print("== N0 CONSUMER AUDIT: does anything consume a terrain vertex NORMAL? ==")
gp = Path(config.find_game_path(None))
shader_audit = {}


def bind_list(text):
    return sorted(set(re.findall(r'Bind\s+"(\w+)"', text)))


for label, rel in (("live loose WorldMap/Terrain", "StreamingAssets/Shaders/WorldMap/Terrain.txt"),
                   ("control WorldMap/Mobile/VertexLit",
                    "StreamingAssets/Shaders/WorldMap/Mobile/VertexLit.txt"),
                   ("live loose WorldMap/Beach", "StreamingAssets/Shaders/WorldMap/Beach.txt")):
    p = gp / rel
    if not p.is_file():
        shader_audit[label] = dict(present=False)
        print(f"   {label:38s} MISSING ({p})")
        continue
    t = p.read_text(encoding="utf8", errors="replace")
    b = bind_list(t)
    fb = re.findall(r'Fallback\s+"([^"]+)"', t)
    shader_audit[label] = dict(present=True, binds=b, fallback=fb,
                               subprograms=sorted(set(re.findall(r'SubProgram\s+"(\S+)', t))),
                               reads_normal=("normal" in b))
    print(f"   {label:38s} binds={b} fallback={fb} reads_normal={'normal' in b}")

# the bundled Material's shader (the asset the engine actually Loads), for a second source
bundled = dict(found=False)
try:
    X._unitypy()
    import UnityPy
    sa = gp / "StreamingAssets"
    cand = sorted(glob.glob(str(sa / "p0data*.bin")),
                  key=lambda q: (0 if "p0data3." in Path(q).name else 1, q))
    for p in cand[:4]:
        env = UnityPy.load(p)
        for o in env.objects:
            if o.type.name != "Shader":
                continue
            d = o.read()
            if getattr(d, "m_Name", "") != "WorldMap-Terrain":
                continue
            s = d.m_Script
            bundled = dict(found=True, bundle=Path(p).name, name=d.m_Name,
                           binds=bind_list(s), fallback=re.findall(r'Fallback\s+"([^"]+)"', s),
                           subprograms=sorted(set(re.findall(r'SubProgram\s+"(\S+)', s))),
                           reads_normal=("normal" in bind_list(s)))
            break
        if bundled["found"]:
            break
except Exception as ex:                                       # noqa: BLE001
    bundled = dict(found=False, error=str(ex))
print(f"   bundled Material shader: {bundled}")

# the FALLBACK question: "Fallback VertexLit" DOES read normals, so it matters whether the
# d3d9 SubShader is the one the machine selects. Census every loose shader listing's targets --
# if the whole game ships d3d9-only programs, a non-d3d9 run would render nothing at all.
targets = Counter()
shd = gp / "StreamingAssets" / "Shaders"
n_shader_files = 0
if shd.is_dir():
    for p in shd.rglob("*.txt"):
        n_shader_files += 1
        for m in set(re.findall(r'SubProgram\s+"(\S+)', p.read_text(encoding="utf8", errors="replace"))):
            targets[m] += 1
print(f"   shader-target census over {n_shader_files} loose listings: {targets.most_common()}")

engine_sites = {}
mem = Path(r"C:\gd\FFIX\Memoria\Assembly-CSharp")
if mem.is_dir():
    hits = defaultdict(list)
    for p in mem.rglob("*.cs"):
        try:
            for i, line in enumerate(p.read_text(encoding="utf8", errors="replace").splitlines(), 1):
                if ".Normals" in line and "TriangleNormals" not in line:
                    hits["WMMesh.Normals"].append(f"{p.relative_to(mem)}:{i}")
                if "TriangleNormals" in line:
                    hits["TriangleNormals"].append(f"{p.relative_to(mem)}:{i}")
        except OSError:
            continue
    engine_sites = {k: v for k, v in hits.items()}
    print(f"   engine call sites: WMMesh.Normals -> {engine_sites.get('WMMesh.Normals')}")
    print(f"                      TriangleNormals -> {engine_sites.get('TriangleNormals')}")
else:
    print("   (Memoria clone absent -- engine call-site census skipped)")

# =============================================================================================
# stock census
# =============================================================================================
blocks = X.list_blocks(disc=1)
lut = Counter()
lut_growth = []
n_blocks = 0

tilt_by_slope = defaultdict(list)                             # N3
corner_const = []                                             # N2
split_gg, split_gr = [], []                                   # N2
mdl = defaultdict(list)                                       # N4 residual angles
mdl_exact = Counter()
dihedral_bins = defaultdict(list)                             # N5
weld_ground_only, weld_all = [], []                           # N5
weld_split = []
flat_norms = Counter()                                        # N6 strict (<1 deg neighbourhood)
flat_tilt, flat_azi = [], []
flat2_norms = Counter()                                       # N6 loose (<3 deg neighbourhood)
flat2_tilt = []
n_ground_tris = n_ground_verts = 0
per_block_pos = {}                                            # for the donor / render

SLOPE_BINS = ((0.0, 2.0, "0-2"), (2.0, 10.0, "2-10"), (10.0, 25.0, "10-25"),
              (25.0, 40.0, "25-40"), (40.0, 90.1, "40+"))


def slope_bin(s):
    for lo, hi, nm in SLOPE_BINS:
        if lo <= s < hi:
            return nm
    return "40+"


print("\n== reading stock disc-1 terrain ==")
for k, (bx, by) in enumerate(blocks):
    try:
        V, N, T, tri, topo = load_block(bx, by)
    except Exception:                                         # noqa: BLE001
        continue
    n_blocks += 1
    for n in N:
        lut[tuple(n)] += 1
    lut_growth.append((n_blocks, len(lut)))

    fn = []                                                   # geometric face normal (up-oriented)
    fslope = []
    for idx in tri:
        a, b, c = (np.array(V[i], float) for i in idx)
        g = np.cross(b - a, c - a)
        if g[1] < 0:
            g = -g
        fn.append(g)
        L = float(np.linalg.norm(g))
        fslope.append(ang(g, UP) if L > 1e-12 else None)

    ground = [t for t in range(len(tri)) if walkable(topo[t])]
    gset = set(ground)
    n_ground_tris += len(ground)

    # welded accumulators
    acc_g = defaultdict(lambda: np.zeros(3))                  # area-weighted, GROUND faces only
    acc_a = defaultdict(lambda: np.zeros(3))                  # area-weighted, ALL faces
    acc_u = defaultdict(lambda: np.zeros(3))                  # unweighted (unit face normals), ground
    at = defaultdict(list)                                    # pos -> [(tri, vert index)]
    for t, idx in enumerate(tri):
        g = fn[t]
        L = float(np.linalg.norm(g))
        for i in idx:
            p = kk(V[i])
            at[p].append((t, i))
            acc_a[p] += g
            if t in gset:
                acc_g[p] += g
                if L > 1e-12:
                    acc_u[p] += g / L

    for t in ground:
        idx = tri[t]
        same = all(tuple(N[idx[0]]) == tuple(N[idx[j]]) for j in (1, 2))
        corner_const.append(1 if same else 0)
        s = fslope[t]
        for i in idx:
            sh = np.array(N[i], float)
            n_ground_verts += 1
            tl = ang(sh, UP)
            if s is not None and tl is not None:
                tilt_by_slope[slope_bin(s)].append(round(tl, 2))
            p = kk(V[i])
            for nm, cand in (("own_face", fn[t]), ("weld_area_ground", acc_g[p]),
                             ("weld_area_all", acc_a[p]), ("weld_unweighted", acc_u[p])):
                a_ = ang(sh, cand)
                if a_ is not None:
                    mdl[nm].append(round(a_, 2))

    for p, lst in at.items():
        gg = [(t, i) for t, i in lst if t in gset]
        rr = [(t, i) for t, i in lst if topo[t] in ROCK]
        if len(gg) >= 2:
            ns = [N[i] for _, i in gg]
            mx = 0.0
            for a_ in range(len(ns)):
                for b_ in range(a_ + 1, len(ns)):
                    mx = max(mx, ang(ns[a_], ns[b_]) or 0.0)
            split_gg.append(round(mx, 3))
            # N5: the dihedral this shared vertex actually spans
            dh = 0.0
            for a_ in range(len(gg)):
                for b_ in range(a_ + 1, len(gg)):
                    dh = max(dh, ang(fn[gg[a_][0]], fn[gg[b_][0]]) or 0.0)
            db = "0-10" if dh < 10 else "10-25" if dh < 25 else "25-50" if dh < 50 else "50+"
            dihedral_bins[db].append(round(mx, 3))
        if gg and rr:                                         # a rock/ground WELD vertex
            mx = 0.0
            for t1, i1 in gg:
                for t2, i2 in rr:
                    mx = max(mx, ang(N[i1], N[i2]) or 0.0)
            split_gr.append(round(mx, 3))
            weld_split.append(round(mx, 3))
            sh = np.array(N[gg[0][1]], float)
            a1 = ang(sh, acc_g[p])
            a2 = ang(sh, acc_a[p])
            if a1 is not None:
                weld_ground_only.append(round(a1, 2))
            if a2 is not None:
                weld_all.append(round(a2, 2))

    # N6 -- verts whose ENTIRE incident ground neighbourhood is flat (<1 deg)
    for p, lst in at.items():
        gg = [(t, i) for t, i in lst if t in gset]
        if not gg or len(gg) != len(lst):
            continue
        worst = max((fslope[t] or 90.0) for t, _ in gg)
        n0 = tuple(N[gg[0][1]])
        tl = ang(n0, UP)
        if worst < 3.0:
            flat2_norms[n0] += 1
            if tl is not None:
                flat2_tilt.append(round(tl, 3))
        if worst >= 1.0:
            continue
        flat_norms[n0] += 1
        if tl is not None:
            flat_tilt.append(round(tl, 3))
        if abs(n0[0]) + abs(n0[2]) > 1e-6:
            flat_azi.append(round(math.degrees(math.atan2(n0[2], n0[0])) % 360.0, 1))

    if (bx, by) == DONOR:
        per_block_pos[DONOR] = (V, N, T, tri, topo, fn, fslope, at, acc_g)

print(f"   {n_blocks} blocks read; {n_ground_tris} walkable-ground tris, "
      f"{n_ground_verts} ground vertex records")

# ---- N1 the palette --------------------------------------------------------------------------
arr = np.array([list(k) for k in lut.keys()], float)
Ln = np.linalg.norm(arr, axis=1)
unit = arr / Ln[:, None]
D = unit @ unit.T
np.fill_diagonal(D, -2.0)
nn = np.degrees(np.arccos(np.clip(D.max(axis=1), -1.0, 1.0)))
dens = []
for v in arr.ravel():
    for d in (256, 512, 1024, 2048, 4096, 8192, 16384):
        if abs(v * d - round(v * d)) < 1e-9:
            dens.append(d)
            break
    else:
        dens.append(None)
den_ok = all(d is not None and 4096 % d == 0 for d in dens)
exact_up = lut.get((0.0, 1.0, 0.0), 0)
print(f"\n== N1 THE PALETTE ==")
print(f"   distinct terrain normals map-wide: {len(lut)} (for {sum(lut.values())} vertex records)")
print(f"   growth: {[g for i, g in enumerate(lut_growth) if i in (0, 4, 19, 49, 99, 149, 199, len(lut_growth) - 1)]}")
print(f"   all components integer multiples of 1/4096: {den_ok}")
print(f"   |n| range {Ln.min():.6f}..{Ln.max():.6f} (never exactly 1)")
print(f"   nearest-neighbour angle within the palette: med {np.median(nn):.2f} "
      f"p10 {np.percentile(nn, 10):.2f} p90 {np.percentile(nn, 90):.2f} max {nn.max():.2f}")
print(f"   exact (0,1,0) entries: {exact_up}")
print(f"   top 6: {[(tuple(round(c, 4) for c in k), v) for k, v in lut.most_common(6)]}")
tail = sum(1 for v in lut.values() if v <= 5)
cov60 = sum(v for _, v in lut.most_common(60)) / sum(lut.values())
print(f"   rare tail (<=5 records): {tail} entries; top-60 entries cover {cov60:.1%} of all records")
rings = defaultdict(set)                                      # elevation rings -> azimuths
for k in lut:
    t = round(ang(k, UP), 2)
    rings[t].add(round(math.degrees(math.atan2(k[2], k[0])) % 360.0, 1)
                 if abs(k[0]) + abs(k[2]) > 1e-9 else None)
ring_tab = sorted((t, len(a)) for t, a in rings.items())
print(f"   ELEVATION RINGS (tilt deg -> distinct azimuths): {ring_tab[:12]}")
low_ring = sorted(rings)[0]
print(f"   lowest ring: tilt {low_ring}deg with {len(rings[low_ring])} azimuths "
      f"{sorted(x for x in rings[low_ring] if x is not None)} -- the palette has NO pole entry")

# ---- N2 topology ----------------------------------------------------------------------------
print(f"\n== N2 TOPOLOGY (faceted vs welded vs split) ==")
print(f"   per-tri corner-constant (all 3 corners identical): "
      f"{np.mean(corner_const):.1%} of {len(corner_const)} ground tris")
for nm, a in (("ground|ground shared positions", split_gg), ("ground|ROCK shared positions", split_gr)):
    if not a:
        continue
    print(f"   {nm}: n={len(a)}; spread med {pct(a, 50)} p99 {pct(a, 99)} max {round(max(a), 3)}; "
          f"SPLIT COUNTS >0.5deg {sum(1 for q in a if q > 0.5)} ({sum(1 for q in a if q > 0.5) / len(a):.3%}); "
          f">5deg {sum(1 for q in a if q > 5)}; >15deg {sum(1 for q in a if q > 15)}")

# ---- N3 tilt vs slope -----------------------------------------------------------------------
print(f"\n== N3 SHIPPED TILT FROM WORLD UP, BY LOCAL FACE SLOPE ==")
for _, _, nm in SLOPE_BINS:
    a = tilt_by_slope.get(nm, [])
    if a:
        print(f"   face slope {nm:6s} deg: {dist(a, 'tilt', 'deg')}")
tilt_all = [q for a in tilt_by_slope.values() for q in a]
print(f"   ALL ground verts: {dist(tilt_all, 'tilt', 'deg')}; "
      f"within 1deg of up: {sum(1 for q in tilt_all if q < 1.0) / max(1, len(tilt_all)):.2%}")

# ---- N4 which construction reproduces the bytes? --------------------------------------------
print(f"\n== N4 THE CONSTRUCTION (shipped vs candidate models, raw and palette-SNAPPED) ==")
snap_res = {}
# snap test: recompute per-vert candidate, snap to the palette, compare to shipped
V, N, T, tri, topo, fn, fslope, at, acc_g = per_block_pos[DONOR]
for nm, a in mdl.items():
    print(f"   shipped vs {nm:18s}: {dist(a, 'angle', 'deg')}")

snap_stats = defaultdict(lambda: dict(n=0, exact=0, res=[]))
SNAP_BLOCKS = blocks[:80]                                     # deterministic 80-block subsample
for bx, by in SNAP_BLOCKS:
    try:
        Vb, Nb, Tb, trib, topob = load_block(bx, by)
    except Exception:                                         # noqa: BLE001
        continue
    fnb = []
    for idx in trib:
        a, b, c = (np.array(Vb[i], float) for i in idx)
        g = np.cross(b - a, c - a)
        if g[1] < 0:
            g = -g
        fnb.append(g)
    gset = {t for t in range(len(trib)) if walkable(topob[t])}
    accs = dict(ground=defaultdict(lambda: np.zeros(3)), allf=defaultdict(lambda: np.zeros(3)),
                unw=defaultdict(lambda: np.zeros(3)))
    for t, idx in enumerate(trib):
        g = fnb[t]
        L = float(np.linalg.norm(g))
        for i in idx:
            p = kk(Vb[i])
            accs["allf"][p] += g
            if t in gset:
                accs["ground"][p] += g
                if L > 1e-12:
                    accs["unw"][p] += g / L
    seen = set()
    for t in gset:
        for i in trib[t]:
            p = kk(Vb[i])
            if p in seen:
                continue
            seen.add(p)
            # BORDER verts cannot see the neighbouring block's faces -- score them apart
            border = (min(abs(p[0]), abs(64.0 - p[0])) < 0.01 or
                      min(abs(p[2]), abs(-64.0 - p[2])) < 0.01)
            for nm, acc in (("area_ground", accs["ground"]), ("area_ALLfaces", accs["allf"]),
                            ("unweighted_ground", accs["unw"])):
                cand = acc[p]
                L = float(np.linalg.norm(cand))
                if L < 1e-12:
                    continue
                u = cand / L
                snapped = tuple(arr[int(np.argmax(unit @ u))])
                for key in (f"{nm}->snap", f"{nm}->snap[{'border' if border else 'interior'}]"):
                    st = snap_stats[key]
                    st["n"] += 1
                    st["exact"] += 1 if snapped == tuple(Nb[i]) else 0
                    r = ang(Nb[i], snapped)
                    if r is not None:
                        st["res"].append(round(r, 2))
print(f"   (snap test over {len(SNAP_BLOCKS)} blocks; a correct pre-snap direction must land "
      f"within ~half the {np.median(nn):.1f}deg palette spacing)")
for nm in sorted(snap_stats):
    st = snap_stats[nm]
    print(f"   {nm:40s}: n={st['n']:6d} EXACT-byte {st['exact'] / max(1, st['n']):6.2%}  "
          f"residual med {pct(st['res'], 50):5} p90 {pct(st['res'], 90)}")
    snap_res[nm] = dict(n=st["n"], exact_frac=round(st["exact"] / max(1, st["n"]), 4),
                        res_med=pct(st["res"], 50), res_p90=pct(st["res"], 90))

# ---- N5 breaks + welds ----------------------------------------------------------------------
print(f"\n== N5 SLOPE BREAKS + THE ROCK/GROUND WELD ==")
for db in ("0-10", "10-25", "25-50", "50+"):
    a = dihedral_bins.get(db, [])
    if a:
        print(f"   incident-face dihedral {db:5s} deg: normal spread at the shared vert "
              f"med {pct(a, 50)} max {round(max(a), 3)} (n={len(a)})")
print(f"   weld verts (ground tri + rock tri at one position): n={len(weld_split)}; "
      f"ground-vs-rock normal spread med {pct(weld_split, 50)} p90 {pct(weld_split, 90)} "
      f"max {round(max(weld_split), 2) if weld_split else None}; "
      f"split>5deg {sum(1 for q in weld_split if q > 5) / max(1, len(weld_split)):.1%}")
print(f"   at a weld vert, shipped vs GROUND-ONLY average: med {pct(weld_ground_only, 50)} "
      f"p90 {pct(weld_ground_only, 90)}")
print(f"   at a weld vert, shipped vs ALL-FACES average:   med {pct(weld_all, 50)} "
      f"p90 {pct(weld_all, 90)}")

# ---- N6 flat lowland ------------------------------------------------------------------------
print(f"\n== N6 FLAT LOWLAND GROUND ==")
tot_flat = max(1, sum(flat_norms.values()))
tot_f2 = max(1, sum(flat2_norms.values()))
print(f"   NOTE stock ground is almost never truly flat -- the sample size IS a finding")
print(f"   near-flat tier (<3deg neighbourhood): n={tot_f2}, distinct normals {len(flat2_norms)}, "
      f"tilt med {pct(flat2_tilt, 50)} min {pct(flat2_tilt, 0)}, exactly (0,1,0) "
      f"{flat2_norms.get((0.0, 1.0, 0.0), 0)}")
print(f"   fully-flat ground vertices (every incident face <1deg): {tot_flat}")
print(f"   exactly (0,1,0): {flat_norms.get((0.0, 1.0, 0.0), 0)} ({flat_norms.get((0.0, 1.0, 0.0), 0) / tot_flat:.2%})")
print(f"   {dist(flat_tilt, 'tilt from up', 'deg')}")
print(f"   distinct normals used on flat ground: {len(flat_norms)}; top 6:")
for k, v in flat_norms.most_common(6):
    print(f"      {tuple(round(c, 6) for c in k)}  x{v}  tilt {ang(k, UP):.2f}deg  "
          f"azimuth {math.degrees(math.atan2(k[2], k[0])) % 360.0:.1f}deg")
azi_hist = Counter(round(a / 5.0) * 5 for a in flat_azi)
print(f"   azimuth histogram (5deg bins, top 8): {azi_hist.most_common(8)}")

# =============================================================================================
# N7 THE DONOR APRON -- (15,14) grass within 10u of the mesa's rock/ground weld line
# =============================================================================================
print(f"\n== N7 THE DONOR APRON: block {DONOR}, grass within 10u of the rock/ground weld ==")
V, N, T, tri, topo, fn, fslope, at, acc_g = per_block_pos[DONOR]
edge_tris = defaultdict(list)
for t, idx in enumerate(tri):
    for a_, b_ in ((0, 1), (1, 2), (2, 0)):
        edge_tris[tuple(sorted((kk(V[idx[a_]]), kk(V[idx[b_]]))))].append(t)
weld_pts = []
for e, ts in edge_tris.items():
    if len(ts) != 2:
        continue
    cls = {topo[ts[0]], topo[ts[1]]}
    if (cls & ROCK) and any(walkable(c) for c in cls):
        weld_pts.extend([e[0], e[1]])
WP = np.array([[p[0], p[2]] for p in weld_pts]) if weld_pts else np.zeros((0, 2))
print(f"   weld-line points: {len(weld_pts)} (from {len(set(map(tuple, weld_pts)))} distinct)")

apron = []
for t, idx in enumerate(tri):
    if topo[t] not in GRASS:
        continue
    c = np.mean([[V[i][0], V[i][2]] for i in idx], axis=0)
    if len(WP) and float(np.min(np.hypot(WP[:, 0] - c[0], WP[:, 1] - c[1]))) <= 10.0:
        apron.append(t)
ap_tilt, ap_split, ap_mdl_g, ap_mdl_f = [], [], [], []
ap_norms = Counter()
ap_slope = []
seen_ap = set()
for t in apron:
    ap_slope.append(round(fslope[t] or 0.0, 2))
    for i in tri[t]:
        sh = np.array(N[i], float)
        ap_norms[tuple(N[i])] += 1
        tl = ang(sh, UP)
        if tl is not None:
            ap_tilt.append(round(tl, 2))
        p = kk(V[i])
        a1 = ang(sh, acc_g[p])
        a2 = ang(sh, fn[t])
        if a1 is not None:
            ap_mdl_g.append(round(a1, 2))
        if a2 is not None:
            ap_mdl_f.append(round(a2, 2))
apset = set(apron)
for p, lst in at.items():
    gg = [(t, i) for t, i in lst if t in apset]
    if len(gg) >= 2:
        ns = [N[i] for _, i in gg]
        mx = 0.0
        for a_ in range(len(ns)):
            for b_ in range(a_ + 1, len(ns)):
                mx = max(mx, ang(ns[a_], ns[b_]) or 0.0)
        ap_split.append(round(mx, 3))
print(f"   apron: {len(apron)} grass tris, {len(ap_tilt)} vertex records, "
      f"{len(ap_norms)} distinct normals")
print(f"   face slope: {dist(ap_slope, 'slope', 'deg')}")
print(f"   {dist(ap_tilt, 'shipped tilt from up', 'deg')}")
print(f"   split at shared apron verts: n={len(ap_split)} max "
      f"{round(max(ap_split), 3) if ap_split else None} (0 = one normal per position)")
print(f"   shipped vs welded ground average: {dist(ap_mdl_g, 'angle', 'deg')}")
print(f"   shipped vs own face normal:       {dist(ap_mdl_f, 'angle', 'deg')}")
print(f"   apron palette (top 6):")
for k, v in ap_norms.most_common(6):
    print(f"      {tuple(round(c, 6) for c in k)}  x{v}  tilt {ang(k, UP):.2f}deg")
ap_on_lut = sum(v for k, v in ap_norms.items() if k in lut)
print(f"   on the disc-1 palette: {ap_on_lut}/{sum(ap_norms.values())} vertex records "
      f"({ap_on_lut / max(1, sum(ap_norms.values())):.1%})")

# =============================================================================================
# N8 THE LIVE BENCH -- read-only over the deployed Disc9 overrides
# =============================================================================================
print(f"\n== N8 THE LIVE BENCH (read-only, Disc{BENCH_DISC} {MOD_FOLDER}) ==")
bench = dict(found=[], missing=[])
b_ground = dict(n=0, on_lut=0, quant=0, tilt=[], nearest=[], split=[], exact_up=0)
b_rock = dict(n=0, on_lut=0)
b_by_topo = defaultdict(lambda: dict(n=0, on_lut=0))
b_ground_norms = Counter()
bench_render = []
root = gp / MOD_FOLDER / "FF9_Data" / "WorldMap" / f"Disc{BENCH_DISC}" / "0_1"
for bx, by in BENCH_BLOCKS:
    p = root / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
    if not p.is_file():
        bench["missing"].append(f"({bx},{by})")
        continue
    bench["found"].append(f"({bx},{by})")
    bm = M.blockmesh_from_ff9mesh(p, disc=BENCH_DISC, x=bx, y=by, part="terrain")
    Vb, Nb, Tb = bm.verts, bm.normals, bm.tangents
    if Nb is None:
        continue
    trib = [bm.flat_index[3 * t:3 * t + 3] for t in range(len(bm.flat_index) // 3)]
    topob = [X.decode_id(int(round(Tb[i[0]][0])))["topograph"] for i in trib]
    atb = defaultdict(list)
    for t, idx in enumerate(trib):
        for i in idx:
            atb[kk(Vb[i])].append((t, i))
    for t, idx in enumerate(trib):
        tgt = b_ground if walkable(topob[t]) else (b_rock if topob[t] in ROCK else None)
        if tgt is None:
            continue
        for i in idx:
            n = tuple(Nb[i])
            tgt["n"] += 1
            b_by_topo[topob[t]]["n"] += 1
            if n in lut:
                tgt["on_lut"] += 1
                b_by_topo[topob[t]]["on_lut"] += 1
            if tgt is b_ground:
                b_ground_norms[n] += 1
                if all(abs(c * 4096 - round(c * 4096)) < 1e-6 for c in n):
                    b_ground["quant"] += 1
                if n == (0.0, 1.0, 0.0):
                    b_ground["exact_up"] += 1
                tl = ang(n, UP)
                if tl is not None:
                    b_ground["tilt"].append(round(tl, 2))
                if n not in lut:
                    u = np.array(n, float)
                    u = u / max(1e-12, float(np.linalg.norm(u)))
                    b_ground["nearest"].append(round(
                        math.degrees(math.acos(max(-1.0, min(1.0, float((unit @ u).max()))))), 2))
        if walkable(topob[t]):
            bench_render.append(([(Vb[i][0] + 64.0 * bx, Vb[i][2] - 64.0 * by) for i in idx],
                                 all(tuple(Nb[i]) in lut for i in idx)))
    for p2, lst in atb.items():
        gg = [(t, i) for t, i in lst if walkable(topob[t])]
        if len(gg) >= 2:
            ns = [Nb[i] for _, i in gg]
            mx = 0.0
            for a_ in range(len(ns)):
                for b_ in range(a_ + 1, len(ns)):
                    mx = max(mx, ang(ns[a_], ns[b_]) or 0.0)
            b_ground["split"].append(round(mx, 3))
print(f"   blocks found {bench['found']}  missing {bench['missing']}")
if b_ground["n"]:
    print(f"   GROUND vertex records {b_ground['n']}: on the stock palette "
          f"{b_ground['on_lut'] / b_ground['n']:.1%}; 1/4096-quantized "
          f"{b_ground['quant'] / b_ground['n']:.1%}; exactly (0,1,0) {b_ground['exact_up']}")
    print(f"   {dist(b_ground['tilt'], 'bench ground tilt from up', 'deg')}")
    print(f"   OFF-palette records: n={len(b_ground['nearest'])}; "
          f"{dist(b_ground['nearest'], 'angle to nearest palette entry', 'deg')}")
    print(f"   split at shared bench ground verts: n={len(b_ground['split'])} "
          f"med {pct(b_ground['split'], 50)} max "
          f"{round(max(b_ground['split']), 3) if b_ground['split'] else None}")
if b_rock["n"]:
    print(f"   ROCK vertex records {b_rock['n']}: on the stock palette "
          f"{b_rock['on_lut'] / b_rock['n']:.1%} (round 8 left wall normals untouched)")
print(f"   per-topograph on-palette share (carried classes should be ~100%):")
for t in sorted(b_by_topo):
    d = b_by_topo[t]
    print(f"      topo {t:3d}: n={d['n']:6d}  on-palette {d['on_lut'] / max(1, d['n']):6.1%}")

# =============================================================================================
# render
# =============================================================================================
PNG.parent.mkdir(parents=True, exist_ok=True)
W, H = 1180, 560
img = Image.new("RGB", (W, H), (22, 24, 28))
dr = ImageDraw.Draw(img)

# panel A -- the palette as a plan projection of the direction sphere
cx, cy, R = 250, 290, 210
dr.text((14, 8), "A. THE STOCK NORMAL PALETTE (disc-1 terrain)", fill=(230, 230, 230))
dr.text((14, 24), f"{len(lut)} distinct vectors, all 1/4096-quantized; dot area ~ use count",
        fill=(150, 152, 160))
dr.text((14, 40), "radius = tilt from up (edge = 90deg); RED CROSSES = the live bench's own "
                  "ground normals", fill=(150, 152, 160))
dr.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(60, 64, 72))
for rr in (0.25, 0.5, 0.75):
    dr.ellipse([cx - R * rr, cy - R * rr, cx + R * rr, cy + R * rr], outline=(42, 45, 52))
mx_cnt = max(lut.values())


def sphere_xy(k):
    u = np.array(k, float)
    u = u / max(1e-12, float(np.linalg.norm(u)))
    t = math.degrees(math.acos(max(-1.0, min(1.0, abs(u[1])))))
    r = R * t / 90.0
    h = math.hypot(u[0], u[2])
    if h < 1e-9:
        return cx, cy
    return cx + r * u[0] / h, cy + r * u[2] / h


for k, v in lut.items():
    px, py = sphere_xy(k)
    s = 1.5 + 4.5 * (v / mx_cnt) ** 0.4
    col = (110, 210, 140) if k[1] > 0 else (210, 130, 110)
    dr.ellipse([px - s, py - s, px + s, py + s], fill=col)
for k in list(b_ground_norms)[:4000]:
    px, py = sphere_xy(k)
    dr.line([px - 2, py - 2, px + 2, py + 2], fill=(240, 80, 80))
    dr.line([px - 2, py + 2, px + 2, py - 2], fill=(240, 80, 80))
dr.text((14, H - 34), "green = upward palette entry  red-orange = downward  "
                      "(no entry is exactly (0,1,0))", fill=(150, 152, 160))

# panel B -- the donor apron, tilt buckets + the weld line
ox, oy = 640, 290
xs = [V[i][0] for t in range(len(tri)) for i in tri[t]]
zs = [V[i][2] for t in range(len(tri)) for i in tri[t]]
cx2, cz2 = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
sc = 400.0 / max(max(xs) - min(xs), max(zs) - min(zs), 8.0)
Mp = lambda x, z: (ox + (x - cx2) * sc, oy + (z - cz2) * sc)   # noqa: E731
dr.text((490, 8), f"B. DONOR {DONOR}: ground tilt-from-up per tri (mean of corners)",
        fill=(230, 230, 230))
dr.text((490, 24), "yellow = rock/ground weld line; magenta outline = the 10u apron",
        fill=(150, 152, 160))
for t in range(len(tri)):
    if not walkable(topo[t]):
        continue
    tl = np.mean([ang(N[i], UP) or 0.0 for i in tri[t]])
    g = int(max(0, min(255, 40 + 215 * min(1.0, tl / 40.0))))
    q = [Mp(V[i][0], V[i][2]) for i in tri[t]]
    dr.polygon(q, fill=(g // 3, g, 90))
for t in apron:
    q = [Mp(V[i][0], V[i][2]) for i in tri[t]]
    dr.polygon(q, outline=(220, 90, 220))
for e, ts in edge_tris.items():
    if len(ts) == 2:
        cls = {topo[ts[0]], topo[ts[1]]}
        if (cls & ROCK) and any(walkable(c) for c in cls):
            dr.line([Mp(e[0][0], e[0][2]), Mp(e[1][0], e[1][2])], fill=(245, 220, 90), width=2)
img.save(PNG)
print(f"\nrender -> {PNG}")

# =============================================================================================
OUT.write_text(json.dumps(dict(
    population=dict(blocks=n_blocks, ground_tris=n_ground_tris, ground_vert_records=n_ground_verts,
                    donor=list(DONOR), bench_blocks=bench),
    n0_consumers=dict(shaders=shader_audit, bundled_shader=bundled, engine_sites=engine_sites,
                      loose_shader_targets=dict(targets), loose_shader_files=n_shader_files),
    n1_palette=dict(distinct=len(lut), records=sum(lut.values()),
                    quantized_1_4096=bool(den_ok),
                    len_min=round(float(Ln.min()), 6), len_max=round(float(Ln.max()), 6),
                    nn_med=round(float(np.median(nn)), 2), nn_p10=round(float(np.percentile(nn, 10)), 2),
                    nn_p90=round(float(np.percentile(nn, 90)), 2), nn_max=round(float(nn.max()), 2),
                    exact_up_entries=exact_up,
                    growth=lut_growth[::20], rare_tail_le5=tail, top60_coverage=round(cov60, 4),
                    elevation_rings=[[t, n] for t, n in ring_tab],
                    top=[[list(k), v] for k, v in lut.most_common(10)]),
    n2_topology=dict(corner_constant_frac=round(float(np.mean(corner_const)), 4),
                     split_ground_ground=dict(n=len(split_gg), med=pct(split_gg, 50),
                                              max=round(max(split_gg), 3) if split_gg else None,
                                              frac_gt_half_deg=round(sum(1 for q in split_gg if q > 0.5) / max(1, len(split_gg)), 5)),
                     split_ground_rock=dict(n=len(split_gr), med=pct(split_gr, 50),
                                            p90=pct(split_gr, 90),
                                            max=round(max(split_gr), 3) if split_gr else None,
                                            frac_gt_5_deg=round(sum(1 for q in split_gr if q > 5) / max(1, len(split_gr)), 4))),
    n3_tilt_by_slope={nm: dict(n=len(a), med=pct(a, 50), p10=pct(a, 10), p90=pct(a, 90))
                      for nm, a in tilt_by_slope.items()},
    n3_all=dict(med=pct(tilt_all, 50), p90=pct(tilt_all, 90),
                frac_within_1deg_of_up=round(sum(1 for q in tilt_all if q < 1.0) / max(1, len(tilt_all)), 5)),
    n4_models={nm: dict(n=len(a), med=pct(a, 50), p10=pct(a, 10), p90=pct(a, 90)) for nm, a in mdl.items()},
    n4_snap=snap_res,
    n5_breaks={db: dict(n=len(a), med=pct(a, 50), max=round(max(a), 3) if a else None)
               for db, a in dihedral_bins.items()},
    n5_weld=dict(n=len(weld_split), spread_med=pct(weld_split, 50), spread_p90=pct(weld_split, 90),
                 spread_max=round(max(weld_split), 2) if weld_split else None,
                 frac_split_gt5=round(sum(1 for q in weld_split if q > 5) / max(1, len(weld_split)), 4),
                 vs_ground_only_med=pct(weld_ground_only, 50),
                 vs_all_faces_med=pct(weld_all, 50)),
    n6_flat_loose=dict(n=tot_f2, distinct=len(flat2_norms),
                       exact_up=flat2_norms.get((0.0, 1.0, 0.0), 0),
                       tilt_med=pct(flat2_tilt, 50), tilt_min=pct(flat2_tilt, 0)),
    n6_flat=dict(n=tot_flat, exact_up=flat_norms.get((0.0, 1.0, 0.0), 0),
                 tilt_med=pct(flat_tilt, 50), tilt_min=pct(flat_tilt, 0), tilt_max=pct(flat_tilt, 100),
                 distinct=len(flat_norms),
                 top=[[list(k), v, round(ang(k, UP), 3)] for k, v in flat_norms.most_common(8)],
                 azimuth_hist=dict(sorted(azi_hist.items()))),
    n7_donor_apron=dict(weld_pts=len(weld_pts), tris=len(apron), vert_records=len(ap_tilt),
                        distinct_normals=len(ap_norms),
                        slope=dict(med=pct(ap_slope, 50), p90=pct(ap_slope, 90)),
                        tilt=dict(med=pct(ap_tilt, 50), p10=pct(ap_tilt, 10), p90=pct(ap_tilt, 90),
                                  max=round(max(ap_tilt), 2) if ap_tilt else None),
                        split_max=round(max(ap_split), 3) if ap_split else None,
                        vs_welded_avg=dict(med=pct(ap_mdl_g, 50), p90=pct(ap_mdl_g, 90)),
                        vs_own_face=dict(med=pct(ap_mdl_f, 50), p90=pct(ap_mdl_f, 90)),
                        on_palette_frac=round(ap_on_lut / max(1, sum(ap_norms.values())), 4),
                        top=[[list(k), v, round(ang(k, UP), 3)] for k, v in ap_norms.most_common(8)]),
    n8_bench=dict(blocks=bench,
                  ground=dict(n=b_ground["n"],
                              on_palette_frac=round(b_ground["on_lut"] / max(1, b_ground["n"]), 4),
                              quantized_frac=round(b_ground["quant"] / max(1, b_ground["n"]), 4),
                              exact_up=b_ground["exact_up"],
                              tilt_med=pct(b_ground["tilt"], 50), tilt_p90=pct(b_ground["tilt"], 90),
                              off_palette_n=len(b_ground["nearest"]),
                              off_palette_angle_med=pct(b_ground["nearest"], 50),
                              off_palette_angle_p90=pct(b_ground["nearest"], 90),
                              split_med=pct(b_ground["split"], 50),
                              split_max=round(max(b_ground["split"]), 3) if b_ground["split"] else None),
                  rock=dict(n=b_rock["n"],
                            on_palette_frac=round(b_rock["on_lut"] / max(1, b_rock["n"]), 4)),
                  per_topo={str(t): dict(n=d["n"], on_palette=round(d["on_lut"] / max(1, d["n"]), 4))
                            for t, d in sorted(b_by_topo.items())}),
), indent=0))
print(f"artifact -> {OUT}")
