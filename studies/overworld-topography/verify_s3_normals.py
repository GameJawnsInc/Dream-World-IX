"""ADVERSARIAL RE-MEASUREMENT of S3 "THE GROUND-NORMAL LAW" (ground_normal_law.py).

Independent method, not a rerun. Four attacks:

  A1 PALETTE CLOSURE BY A DIFFERENT SAMPLE -- rebuild the normal set on **disc 4**
     terrain (260 blocks the claim never read) and on the non-terrain PARTS, and ask how
     many entries are NOT in the disc-1 182. A "fixed 182-entry table" must not grow.
  A2 THE NEAR-UP / POLAR-HOLE HUNT -- the minimum tilt-from-up over every normal in every
     sampled source (terrain d1+d4, sea1/3/4/5, beach, river, riverjoint, falls, object,
     volcano*), i.e. a targeted counterexample hunt for the claim "no entry within 11.88deg
     of up" and "exactly (0,1,0) = 0".
  A3 THE CROSS-BLOCK WELD -- the claim's split test keys positions BLOCK-LOCALLY, so it can
     only see welds inside one block. The bench's seams ARE block borders. Re-key every
     vertex by WORLD position and ask whether stock ships one normal per world position
     across a block border.
  A4 THE CONSTRUCTION, WITH THE CONTROL THEY OMITTED -- the claim tests area-weighted-all,
     area-weighted-ground and unweighted-GROUND, and concludes "AREA-weighted average of
     ALL incident faces". The missing cell of the 2x2 is unweighted-ALL. Snap-test 8
     constructions (incl. angle-weighted, engine-winding, per-block vs world-stitched,
     own-face) against a MODAL-GUESS null baseline, on a sample disjoint from theirs, split
     by rock-adjacency and by border/interior.

Read-only: stock p0data via ff9mapkit.world.extract. Nothing is written outside out/.
Run: py -X utf8 verify_s3_normals.py     Artifacts: out/verify_s3_normals.json + .png
"""
from __future__ import annotations

import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import extract as X                      # noqa: E402

OUT = Path(__file__).with_name("out") / "verify_s3_normals.json"
PNG = Path(__file__).with_name("out") / "verify_s3_normals.png"

FOOT_MASK = (0x0010667F << 32) | 0xD8FF3CFF
ROCK = {49, 7, 62, 58}
UP = np.array([0.0, 1.0, 0.0])
T0 = time.time()
R = {}                                                        # the json artifact

walkable = lambda t: bool((FOOT_MASK >> t) & 1) if 0 <= t < 64 else False   # noqa: E731
_dec = {}


def topo_of(v):
    i = int(round(v))
    if i not in _dec:
        _dec[i] = X.decode_id(i)["topograph"]
    return _dec[i]


def tilt(n):
    n = np.asarray(n, float)
    L = float(np.linalg.norm(n))
    if L < 1e-12:
        return None
    return math.degrees(math.acos(max(-1.0, min(1.0, float(n[1]) / L))))


def pct(a, q):
    return round(float(np.percentile(a, q)), 3) if len(a) else None


def q4096(vals):
    return all(abs(c * 4096 - round(c * 4096)) < 1e-6 for c in vals)


def read(bx, by, disc, part="terrain"):
    bm = X.read_block(bx, by, disc=disc, part=part)
    V = np.asarray(bm.verts, float)
    N = np.asarray(bm.normals, float)
    T = np.asarray(bm.tangents, float)
    fi = np.asarray(bm.flat_index, np.int64)
    tri = fi[:(len(fi) // 3) * 3].reshape(-1, 3)
    return V, N, T, tri


# =================================================================================================
print("== A1/A2  PALETTE CLOSURE + NEAR-UP HUNT (independent sample: disc 4 + the parts) ==")
blocks1 = X.list_blocks(disc=1)
blocks4 = X.list_blocks(disc=4)
print(f"   disc-1 blocks {len(blocks1)}  disc-4 blocks {len(blocks4)}")

lut1, lut4 = Counter(), Counter()
for bx, by in blocks1:
    try:
        _, N, _, _ = read(bx, by, 1)
    except Exception:                                          # noqa: BLE001
        continue
    for n in map(tuple, N):
        lut1[n] += 1
for bx, by in blocks4:
    try:
        _, N, _, _ = read(bx, by, 4)
    except Exception:                                          # noqa: BLE001
        continue
    for n in map(tuple, N):
        lut4[n] += 1

new4 = {k: v for k, v in lut4.items() if k not in lut1}
union = set(lut1) | set(lut4)
print(f"   disc-1 terrain palette   : {len(lut1):5d} entries / {sum(lut1.values())} records")
print(f"   disc-4 terrain palette   : {len(lut4):5d} entries / {sum(lut4.values())} records")
print(f"   disc-4 entries NOT on the disc-1 palette: {len(new4)} "
      f"({sum(new4.values())} records)  -> union {len(union)}")
print(f"   disc-4 all 1/4096-quantized: {all(q4096(k) for k in lut4)}")

# the parts, disc 1 (sampled over every block; a part read that fails just is not there)
PARTS = ["sea1", "sea3", "sea4", "sea5", "beach", "river", "riverjoint", "falls",
         "object", "volcanocrater", "volcanolava"]
part_lut = {}
for part in PARTS:
    c = Counter()
    nb = 0
    for bx, by in blocks1:
        try:
            _, N, _, _ = read(bx, by, 1, part)
        except Exception:                                      # noqa: BLE001
            continue
        nb += 1
        for n in map(tuple, N):
            c[n] += 1
    if c:
        part_lut[part] = (c, nb)

near_up = {}
for label, c in [("terrain disc1", lut1), ("terrain disc4", lut4)] + \
                [(f"{p} disc1", part_lut[p][0]) for p in part_lut]:
    ts = sorted((tilt(k), k) for k in c if tilt(k) is not None)
    exact = c.get((0.0, 1.0, 0.0), 0)
    n_le5 = sum(v for k, v in c.items() if (tilt(k) or 99) <= 5.0)
    near_up[label] = dict(entries=len(c), records=sum(c.values()),
                          min_tilt=round(ts[0][0], 4) if ts else None,
                          argmin=[round(x, 6) for x in ts[0][1]] if ts else None,
                          exact_up_records=exact,
                          records_within_5deg=n_le5,
                          q4096=bool(all(q4096(k) for k in c)))
    print(f"   {label:22s} entries {len(c):5d}  MIN TILT {near_up[label]['min_tilt']:8}deg "
          f"at {near_up[label]['argmin']}  exact(0,1,0) records {exact:6d}  "
          f"<=5deg records {n_le5:6d}  1/4096 {near_up[label]['q4096']}")

R["a1_palette"] = dict(disc1_entries=len(lut1), disc4_entries=len(lut4),
                       disc4_not_on_disc1=len(new4), disc4_new_records=sum(new4.values()),
                       union_entries=len(union),
                       disc4_new_examples=[[list(k), v, round(tilt(k), 2)]
                                           for k, v in sorted(new4.items(), key=lambda q: -q[1])[:8]])
R["a2_near_up"] = near_up
print(f"   [{time.time() - T0:.0f}s]")

# =================================================================================================
# one full pass over disc-1 terrain, WORLD-keyed -- feeds A3 and A4
# =================================================================================================
print("\n== full disc-1 pass, WORLD-position keyed ==")
pos_id = {}
rec_idx, rec_fn, rec_fu, rec_fa, rec_ship, rec_gnd, rec_rock, rec_blk = [], [], [], [], [], [], [], []
loc_id = {}
rec_loc = []                                                  # block-LOCAL position id (their key)
wind_up = [0, 0]
n_gtri = 0
donor_rows = None

for bi, (bx, by) in enumerate(blocks1):
    try:
        V, N, T, tri = read(bx, by, 1)
    except Exception:                                          # noqa: BLE001
        continue
    a = V[tri[:, 0]]
    b = V[tri[:, 1]]
    c = V[tri[:, 2]]
    g = np.cross(b - a, c - a)                                # engine winding (WMBlock.cs:66)
    topo = np.array([topo_of(T[i][0]) for i in tri[:, 0]])
    gnd = np.array([walkable(int(t)) for t in topo])
    rck = np.isin(topo, list(ROCK))
    n_gtri += int(gnd.sum())
    wind_up[0] += int((g[gnd, 1] > 0).sum())
    wind_up[1] += int(gnd.sum())
    gflip = np.where(g[:, 1:2] < 0, -g, g)                    # the claim's up-flip
    L = np.linalg.norm(gflip, axis=1)
    unitf = gflip / np.maximum(L, 1e-12)[:, None]
    world = V + np.array([64.0 * bx, 0.0, -64.0 * by])
    wk = np.round(world, 3)
    lk = np.round(V, 3)
    # interior angle at each corner, for the angle-weighted variant
    e = [(b - a, c - a), (c - b, a - b), (a - c, b - c)]
    for k in range(3):
        u, v = e[k]
        cu = u / np.maximum(np.linalg.norm(u, axis=1), 1e-12)[:, None]
        cv = v / np.maximum(np.linalg.norm(v, axis=1), 1e-12)[:, None]
        w = np.arccos(np.clip((cu * cv).sum(1), -1.0, 1.0))
        vi = tri[:, k]
        for t in range(len(tri)):
            key = tuple(wk[vi[t]])
            j = pos_id.get(key)
            if j is None:
                j = len(pos_id)
                pos_id[key] = j
            lkey = (bi, tuple(lk[vi[t]]))
            jl = loc_id.get(lkey)
            if jl is None:
                jl = len(loc_id)
                loc_id[lkey] = jl
            rec_idx.append(j)
            rec_loc.append(jl)
            rec_fn.append(gflip[t])
            rec_fu.append(unitf[t])
            rec_fa.append(unitf[t] * w[t])
            rec_ship.append(N[vi[t]])
            rec_gnd.append(bool(gnd[t]))
            rec_rock.append(bool(rck[t]))
            rec_blk.append(bi)

IDX = np.array(rec_idx, np.int64)
LOC = np.array(rec_loc, np.int64)
FN = np.array(rec_fn, float)
FU = np.array(rec_fu, float)
FA = np.array(rec_fa, float)
SH = np.array(rec_ship, float)
GN = np.array(rec_gnd, bool)
RK = np.array(rec_rock, bool)
BK = np.array(rec_blk, np.int64)
NP_, NL = len(pos_id), len(loc_id)
print(f"   {len(IDX)} vertex records, {n_gtri} walkable-ground tris, "
      f"{NP_} distinct WORLD positions, {NL} distinct (block,local) positions")
print(f"   engine-winding face normal points UP on {wind_up[0]}/{wind_up[1]} ground tris "
      f"({wind_up[0] / max(1, wind_up[1]):.2%}) -> winding is consistent, the up-flip is a no-op there")
print(f"   [{time.time() - T0:.0f}s]")

# =================================================================================================
print("\n== A3  THE CROSS-BLOCK WELD (their key is block-local; this one is world) ==")
order = np.lexsort((np.arange(len(IDX)), IDX))
Is = IDX[order]
Ss = SH[order]
Bs = BK[order]
Gs = GN[order]
Rs = RK[order]
same = Is[1:] == Is[:-1]
d = np.einsum("ij,ij->i", Ss[1:], Ss[:-1])
n1 = np.linalg.norm(Ss[1:], axis=1) * np.linalg.norm(Ss[:-1], axis=1)
angc = np.degrees(np.arccos(np.clip(d / np.maximum(n1, 1e-12), -1.0, 1.0)))
diff = same & (angc > 0.5)
# group bookkeeping
grp_nblk = defaultdict(set)
grp_cls = defaultdict(lambda: [False, False])
for i in range(len(Is)):
    grp_nblk[Is[i]].add(int(Bs[i]))
    if Gs[i]:
        grp_cls[Is[i]][0] = True
    if Rs[i]:
        grp_cls[Is[i]][1] = True
shared_world = [k for k, v in grp_nblk.items() if True]
cross_pos = {k for k, v in grp_nblk.items() if len(v) >= 2}
counts = Counter(Is)
multi = {k for k, v in counts.items() if v >= 2}
print(f"   world positions with >=2 vertex records: {len(multi)}")
print(f"   world positions shared by >=2 BLOCKS   : {len(cross_pos)}")
bad = defaultdict(float)
for i in np.nonzero(diff)[0]:
    bad[int(Is[i])] = max(bad[int(Is[i])], float(angc[i]))
bad_cross = {k: v for k, v in bad.items() if k in cross_pos}
bad_in = {k: v for k, v in bad.items() if k not in cross_pos}
gg = [v for k, v in bad.items() if grp_cls[k][0] and not grp_cls[k][1]]
print(f"   positions whose records disagree >0.5deg: {len(bad)} total  "
      f"({len(bad_in)} within one block, {len(bad_cross)} spanning a block border)")
if bad_cross:
    a = sorted(bad_cross.values())
    print(f"   CROSS-BORDER disagreement: {len(bad_cross)}/{len(cross_pos)} = "
          f"{len(bad_cross) / max(1, len(cross_pos)):.2%} of border positions; "
          f"med {pct(a, 50)} p90 {pct(a, 90)} max {round(max(a), 2)}deg")
    gnd_cross = [v for k, v in bad_cross.items() if grp_cls[k][0]]
    print(f"   of those, positions carrying walkable GROUND: {len(gnd_cross)} "
          f"(med {pct(gnd_cross, 50)} max {round(max(gnd_cross), 2) if gnd_cross else None}deg)")
print(f"   within-one-block disagreement: {len(bad_in)}/{len(multi) - len(cross_pos)} "
      f"= {len(bad_in) / max(1, len(multi) - len(cross_pos)):.4%} (their '1 in 41,559' analogue)")
R["a3_weld"] = dict(world_positions_multi=len(multi), world_positions_cross_block=len(cross_pos),
                    disagree_total=len(bad), disagree_within_block=len(bad_in),
                    disagree_cross_block=len(bad_cross),
                    cross_block_disagree_frac=round(len(bad_cross) / max(1, len(cross_pos)), 5),
                    cross_med=pct(list(bad_cross.values()), 50) if bad_cross else None,
                    cross_p90=pct(list(bad_cross.values()), 90) if bad_cross else None,
                    cross_max=round(max(bad_cross.values()), 2) if bad_cross else None,
                    within_block_disagree_frac=round(
                        len(bad_in) / max(1, len(multi) - len(cross_pos)), 6))
print(f"   [{time.time() - T0:.0f}s]")

# =================================================================================================
print("\n== A4  THE CONSTRUCTION + THE OMITTED CONTROL (unweighted-ALL) ==")
arr = np.array([list(k) for k in lut1.keys()], float)
Ln = np.linalg.norm(arr, axis=1)
unit = arr / Ln[:, None]
pal_tilt = np.degrees(np.arccos(np.clip(unit[:, 1], -1, 1)))
print(f"   palette: {len(arr)} entries, min tilt {pal_tilt.min():.3f}deg, "
      f"1/4096 {all(q4096(k) for k in lut1)}")


def accum(key, vecs, mask=None, n=None):
    A = np.zeros((n, 3))
    if mask is None:
        np.add.at(A, key, vecs)
    else:
        np.add.at(A, key[mask], vecs[mask])
    return A


CONS = {}
CONS["area_ALL_stitched"] = accum(IDX, FN, None, NP_)
CONS["unweighted_ALL_stitched"] = accum(IDX, FU, None, NP_)          # THE OMITTED CONTROL
CONS["angle_ALL_stitched"] = accum(IDX, FA, None, NP_)
CONS["area_GROUND_stitched"] = accum(IDX, FN, GN, NP_)
CONS["unweighted_GROUND_stitched"] = accum(IDX, FU, GN, NP_)
LOCC = {}
LOCC["area_ALL_perblock"] = accum(LOC, FN, None, NL)                 # == the claim's own key
LOCC["unweighted_ALL_perblock"] = accum(LOC, FU, None, NL)
LOCC["area_GROUND_perblock"] = accum(LOC, FN, GN, NL)

# shipped normal per world position (modal) + flags
ship_pos = np.zeros((NP_, 3))
ship_pos[IDX] = SH
gnd_pos = np.zeros(NP_, bool)
np.logical_or.at(gnd_pos, IDX, GN)
rock_pos = np.zeros(NP_, bool)
np.logical_or.at(rock_pos, IDX, RK)
WPOS = np.zeros((NP_, 3))
for k, j in pos_id.items():
    WPOS[j] = k
border = (np.abs(WPOS[:, 0] / 64.0 - np.round(WPOS[:, 0] / 64.0)) < 1e-4) | \
         (np.abs(WPOS[:, 2] / 64.0 - np.round(WPOS[:, 2] / 64.0)) < 1e-4)
ship_loc = np.zeros((NL, 3))
ship_loc[LOC] = SH
gnd_loc = np.zeros(NL, bool)
np.logical_or.at(gnd_loc, LOC, GN)
rock_loc = np.zeros(NL, bool)
np.logical_or.at(rock_loc, LOC, RK)

# the CLAIM's sample was blocks[:80]; use the DISJOINT remainder as the primary sample
blk_of_pos = np.full(NP_, -1, np.int64)
blk_of_pos[IDX] = BK
in_their_80 = blk_of_pos < 80
blk_of_loc = np.full(NL, -1, np.int64)
blk_of_loc[LOC] = BK
loc_in_80 = blk_of_loc < 80


def snap_score(cand, ship, keep):
    L = np.linalg.norm(cand, axis=1)
    ok = keep & (L > 1e-9)
    u = cand[ok] / L[ok][:, None]
    j = np.argmax(u @ unit.T, axis=1)
    got = arr[j]
    tgt = ship[ok]
    exact = np.all(np.abs(got - tgt) < 1e-9, axis=1)
    dd = np.einsum("ij,ij->i", got, tgt) / np.maximum(
        np.linalg.norm(got, axis=1) * np.linalg.norm(tgt, axis=1), 1e-12)
    res = np.degrees(np.arccos(np.clip(dd, -1, 1)))
    return int(ok.sum()), float(exact.mean()), res


rows = []
subsets = dict(
    ALL_disjoint=(gnd_pos & ~in_their_80),
    ALL_their80=(gnd_pos & in_their_80),
    pureGROUND_disjoint=(gnd_pos & ~rock_pos & ~in_their_80),
    rockADJ_disjoint=(gnd_pos & rock_pos & ~in_their_80),
    interior_disjoint=(gnd_pos & ~border & ~in_their_80),
    border_disjoint=(gnd_pos & border & ~in_their_80),
)
for nm, cand in CONS.items():
    for sn, keep in subsets.items():
        n, ex, res = snap_score(cand, ship_pos, keep)
        rows.append((nm, sn, n, ex, pct(res, 50), pct(res, 90)))
for nm, cand in LOCC.items():
    for sn, keep in (("ALL_disjoint", gnd_loc & ~loc_in_80), ("ALL_their80", gnd_loc & loc_in_80),
                     ("pureGROUND_disjoint", gnd_loc & ~rock_loc & ~loc_in_80),
                     ("rockADJ_disjoint", gnd_loc & rock_loc & ~loc_in_80)):
        n, ex, res = snap_score(cand, ship_loc, keep)
        rows.append((nm, sn, n, ex, pct(res, 50), pct(res, 90)))

# NULL BASELINES: always guess the modal palette entry / snap the OWN FACE normal
gr = Counter()
for i in np.nonzero(GN)[0]:
    gr[tuple(SH[i])] += 1
modal = max(gr.items(), key=lambda q: q[1])
gtot = sum(gr.values())
own_keep = GN & (BK >= 80)
nO, exO, resO = snap_score(FN[own_keep], SH[own_keep], np.ones(int(own_keep.sum()), bool))
print(f"   NULL 1 modal-guess: the single commonest ground normal {tuple(round(c, 5) for c in modal[0])} "
      f"covers {modal[1] / gtot:.2%} of the {gtot} ground vertex records "
      f"(tilt {tilt(modal[0]):.2f}deg)")
print(f"   NULL 2 own-face->snap (no weld at all): n={nO} EXACT {exO:.2%} res med {pct(resO, 50)}")
print(f"   {'construction':30s} {'subset':22s} {'n':>7s} {'EXACT':>8s} {'res50':>7s} {'res90':>7s}")
for nm, sn, n, ex, m50, m90 in rows:
    print(f"   {nm:30s} {sn:22s} {n:7d} {ex:7.2%} {str(m50):>7s} {str(m90):>7s}")

R["a4_construction"] = dict(
    palette_min_tilt=round(float(pal_tilt.min()), 3),
    modal_null=dict(normal=[round(c, 6) for c in modal[0]], frac=round(modal[1] / gtot, 4),
                    tilt=round(tilt(modal[0]), 3), ground_records=gtot),
    own_face_null=dict(n=nO, exact=round(exO, 4), res_med=pct(resO, 50)),
    rows=[dict(construction=nm, subset=sn, n=n, exact=round(ex, 4), res_med=m50, res_p90=m90)
          for nm, sn, n, ex, m50, m90 in rows])
print(f"   [{time.time() - T0:.0f}s]")

# =================================================================================================
print("\n== A5  IS THE 11.88deg 'FLOOR' A FLOOR? (a different flat-ground statistic) ==")
# their statistic: verts whose whole incident neighbourhood is <1deg (n=30). mine: rank ground
# positions by how close the CONSTRUCTED (area-all) average is to up, and read the shipped tilt.
ca = CONS["area_ALL_stitched"]
La = np.linalg.norm(ca, axis=1)
ok = gnd_pos & (La > 1e-9)
ct = np.degrees(np.arccos(np.clip(ca[ok, 1] / La[ok], -1, 1)))
st = np.degrees(np.arccos(np.clip(ship_pos[ok, 1] / np.maximum(
    np.linalg.norm(ship_pos[ok], axis=1), 1e-12), -1, 1)))
bins = [(0, 1), (1, 2), (2, 5), (5, 10), (10, 20), (20, 40), (40, 91)]
flat_tbl = []
for lo, hi in bins:
    m = (ct >= lo) & (ct < hi)
    if m.sum() == 0:
        continue
    flat_tbl.append(dict(cand_tilt=f"{lo}-{hi}", n=int(m.sum()), shipped_med=pct(st[m], 50),
                         shipped_min=pct(st[m], 0), shipped_p90=pct(st[m], 90)))
    print(f"   constructed tilt {lo:2d}-{hi:2d}deg: n={int(m.sum()):6d}  shipped tilt "
          f"min {pct(st[m], 0):7} med {pct(st[m], 50):7} p90 {pct(st[m], 90)}")
print(f"   GLOBAL min shipped tilt over {int(ok.sum())} ground positions: {st.min():.4f}deg; "
      f"records under 11.0deg: {int((st < 11.0).sum())} ({(st < 11.0).mean():.3%})")
R["a5_floor"] = dict(table=flat_tbl, min_shipped_tilt=round(float(st.min()), 4),
                     n_under_11deg=int((st < 11.0).sum()),
                     frac_under_11deg=round(float((st < 11.0).mean()), 5),
                     n_ground_positions=int(ok.sum()))

# =================================================================================================
print("\n== A6  'STOCK GROUND IS ALMOST NEVER FLAT' -- re-measured without the strict AND ==")
# the claim's N6 requires EVERY incident face <1deg AND every incident tri to be ground, then
# counts vertex RECORDS (n=30). Re-measure the same object three fairer ways.
fslope_rec = np.degrees(np.arccos(np.clip(FU[:, 1], -1, 1)))    # per-RECORD own-face slope
gmask = GN
tri_slope = fslope_rec[::1][gmask]
uniq_tri = fslope_rec.reshape(-1)                              # records, 3 per tri (corner-major)
maxsl = np.zeros(NP_)
np.maximum.at(maxsl, IDX[gmask], fslope_rec[gmask])
anyrock = np.zeros(NP_, bool)
np.logical_or.at(anyrock, IDX, RK)
for lim in (1.0, 2.0, 3.0):
    m = gnd_pos & (maxsl < lim)
    print(f"   ground POSITIONS whose every incident ground face is <{lim}deg: {int(m.sum())} "
          f"of {int(gnd_pos.sum())} ({m.mean() * 100 / max(1e-9, gnd_pos.mean()):.2f}% of ground)")
gt = fslope_rec[gmask]
print(f"   ground FACE slope (per record): <0.5deg {int((gt < 0.5).sum())} "
      f"<1deg {int((gt < 1).sum())} <2deg {int((gt < 2).sum())} of {len(gt)} "
      f"({(gt < 2).mean():.1%} within 2deg of level)")
R["a6_flat"] = dict(ground_positions=int(gnd_pos.sum()),
                    pos_all_faces_under_1deg=int((gnd_pos & (maxsl < 1.0)).sum()),
                    pos_all_faces_under_2deg=int((gnd_pos & (maxsl < 2.0)).sum()),
                    pos_all_faces_under_3deg=int((gnd_pos & (maxsl < 3.0)).sum()),
                    rec_face_under_1deg=int((gt < 1).sum()), rec_face_under_2deg=int((gt < 2).sum()),
                    rec_total=int(len(gt)))

print("\n== A7  IS THE TABLE 182 ENTRIES, OR BIGGER? (the object part uses more) ==")
tbl = dict()
for label in list(part_lut):
    c = part_lut[label][0]
    extra = [k for k in c if k not in lut1]
    tbl[label] = dict(entries=len(c), not_on_terrain_182=len(extra),
                      min_tilt_of_extra=round(min((tilt(k) for k in extra), default=None), 3)
                      if extra else None)
    print(f"   {label:16s} entries {len(c):4d}  NOT on the terrain 182: {len(extra):4d}"
          + (f"  (their min tilt {tbl[label]['min_tilt_of_extra']}deg)" if extra else ""))
allpal = set(lut1) | set(lut4)
for label in part_lut:
    allpal |= set(part_lut[label][0])
print(f"   union over EVERY source sampled: {len(allpal)} entries; all 1/4096 "
      f"{all(q4096(k) for k in allpal)}; min tilt "
      f"{min(tilt(k) for k in allpal):.4f}deg; exact (0,1,0) present: {(0.0, 1.0, 0.0) in allpal}")
R["a7_table_size"] = dict(per_part=tbl, union_entries=len(allpal),
                          union_min_tilt=round(min(tilt(k) for k in allpal), 4),
                          union_has_exact_up=bool((0.0, 1.0, 0.0) in allpal),
                          union_q4096=bool(all(q4096(k) for k in allpal)))

# =================================================================================================
# render: the palette + what disc 4 adds + the polar hole
PNG.parent.mkdir(parents=True, exist_ok=True)
W, H = 1000, 520
img = Image.new("RGB", (W, H), (20, 22, 26))
dr = ImageDraw.Draw(img)
cx, cy, RR = 250, 280, 205
dr.text((12, 8), "A. PALETTE CLOSURE: disc-1 terrain (green) vs disc-4-ONLY entries (cyan)",
        fill=(232, 232, 232))
dr.text((12, 24), f"disc1 {len(lut1)}  disc4 {len(lut4)}  disc4-only {len(new4)}  "
                  f"union {len(union)} -- a closed table cannot grow", fill=(150, 152, 160))
dr.ellipse([cx - RR, cy - RR, cx + RR, cy + RR], outline=(60, 64, 72))
hole = RR * (pal_tilt.min() / 90.0)
dr.ellipse([cx - hole, cy - hole, cx + hole, cy + hole], outline=(230, 190, 80))
dr.text((cx - 60, cy - hole - 14), f"polar hole r={pal_tilt.min():.2f}deg", fill=(230, 190, 80))


def sxy(k):
    u = np.array(k, float)
    u = u / max(1e-12, float(np.linalg.norm(u)))
    t = math.degrees(math.acos(max(-1.0, min(1.0, abs(u[1])))))
    r = RR * t / 90.0
    h = math.hypot(u[0], u[2])
    if h < 1e-9:
        return cx, cy
    return cx + r * u[0] / h, cy + r * u[2] / h


for k in lut1:
    px, py = sxy(k)
    dr.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(110, 200, 140))
for k in new4:
    px, py = sxy(k)
    dr.line([px - 3, py, px + 3, py], fill=(90, 230, 240))
    dr.line([px, py - 3, px, py + 3], fill=(90, 230, 240))

x0, y0 = 540, 60
dr.text((520, 8), "B. EXACT-BYTE snap match by construction (disjoint 180-block sample)",
        fill=(232, 232, 232))
dr.text((520, 24), "the omitted control is unweighted-ALL; dashed = modal-guess null",
        fill=(150, 152, 160))
bars = [(nm, ex) for nm, sn, n, ex, a, b in rows if sn == "ALL_disjoint"]
bars.append(("NULL modal-guess", modal[1] / gtot))
bars.append(("NULL own-face", exO))
BW = 400
for i, (nm, ex) in enumerate(bars):
    y = y0 + i * 34
    col = (240, 200, 90) if nm.startswith("NULL") else (
        (120, 200, 250) if "unweighted_ALL" in nm else (110, 200, 140))
    dr.rectangle([x0, y, x0 + BW * ex, y + 20], fill=col)
    dr.text((x0 + 4, y + 5), f"{ex:.1%}", fill=(20, 22, 26))
    dr.text((x0, y - 12), nm, fill=(178, 182, 190))
img.save(PNG)
print(f"\nrender -> {PNG}")
OUT.write_text(json.dumps(R, indent=0))
print(f"artifact -> {OUT}   [{time.time() - T0:.0f}s total]")
