"""THE DESERT BEACH DECODE -- is topo-32 sand the topo-31 sand band TRANSLATED?

Part 1 (desert_beach_anatomy.py) found stock desert beaches in force (112/320 back
welds on topo 17, Outer Continent) and TWO sand vocabularies: topo 31 at the known
grass band u[270,396]/1024, topo 32 at u[~605,731]/1024 with identical spans. Here:

  A. Cross-tab per beach block: sand topo x back-ground family (does 32 <-> desert?).
  B. THE SAND TRANSLATION FIT: decode every topo-32 corner against the topo-31 pin
     table (SAND_ULAT + run/cap v pins) shifted by a candidate (du, dv); recover the
     translation from the u-strip edges + v-pin modes; report texel-exactness.
  C. The foam ribbon: beach1 UV ranges on desert-backed vs grass-backed beaches --
     same foam texture band or family-keyed?
  D. topo-33 (Lost Continent shore, no beach1 part): uv range vs the band structure.

    py studies/overworld-topography/desert_beach_decode.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import coastmorph as CM                # noqa: E402

BLOCK = 64.0
OUTD = Path(__file__).with_name("out")
out = {}
prev = json.loads((OUTD / "desert_beach.json").read_text())
beach_blocks = [tuple(map(int, s.split(","))) for s in prev["beach_blocks"]]
backs = {tuple(map(int, k.split(","))): v for k, v in prev["back_by_block"].items()}


def mode5(vals):
    return Counter(round(v, 5) for v in vals).most_common(1)[0][0]


# ---- A. cross-tab: per block, sand topo counts + dominant back family ---------------------------
print("A. per-block sand topo x back family:")
rows = []
for (bx, by) in beach_blocks:
    bm = X.read_block(bx, by, disc=1, part="terrain")
    c = Counter()
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
        if topo in (30, 31, 32, 33):
            c[topo] += 1
    b = backs.get((bx, by), {})
    fam = "desert" if b.get("17", 0) > b.get("0", 0) else \
        ("grass" if b.get("0", 0) else "?")
    rows.append(((bx, by), dict(c), fam))
    print(f"   {(bx, by)}: sand {dict(c)}  back={fam} {b}")
n_ok = sum(1 for _, c, fam in rows
           if (fam == "desert") == (c.get(32, 0) > c.get(31, 0)))
print(f"   correlation [32-dominant <=> desert-backed]: {n_ok}/{len(rows)} blocks")
out["crosstab"] = [[f"{b[0]},{b[1]}", c, fam] for b, c, fam in rows]

# ---- B. THE SAND TRANSLATION FIT ----------------------------------------------------------------
uv32, uv31 = [], []
for (bx, by) in beach_blocks:
    bm = X.read_block(bx, by, disc=1, part="terrain")
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
        if topo in (31, 32):
            for j in tri:
                (uv32 if topo == 32 else uv31).append(
                    (float(bm.uvs[j][0]), float(bm.uvs[j][1])))
u32 = np.array([u for u, v in uv32])
v32 = np.array([v for u, v in uv32])
# u-strip edges: the 3-lattice (P lo, split, Q hi) via clustered extremes + the split
# (u values cluster AT the lattice: pick the 3 strongest 5dp modes spanning the range)
um = Counter(round(u, 5) for u in u32).most_common(12)
print(f"\nB. topo-32 u modes (top): {um[:8]}")
u_lo, u_hi = min(u32), max(u32)
DU = round(float(u_lo) - CM.SAND_ULAT[0], 5)
split_expect = CM.SAND_ULAT[1] + DU
n_at_split = sum(1 for u in u32 if abs(u - split_expect) < 0.004)
print(f"   u range [{u_lo:.5f},{u_hi:.5f}] -> DU {DU} "
      f"({DU * 1024:.2f} texels); Q-hi check: {u_hi:.5f} vs "
      f"{CM.SAND_ULAT[2] + DU:.5f}; verts at the shifted split: {n_at_split}")
# v pins: run land/seam = the two strongest v modes; fit DV on the land pin
vm = Counter(round(v, 5) for v in v32).most_common(10)
print(f"   v modes (top): {vm[:8]}")
land32 = min(m for m, n in vm[:2])
seam32 = max(m for m, n in vm[:2])
DV_land = round(land32 - CM.SAND_V_LAND[0], 5)
DV_seam = round(seam32 - CM.SAND_V_SEAM[0], 5)
print(f"   run pins: land {land32} seam {seam32} -> DV_land {DV_land} "
      f"({DV_land * 1024:.2f} texels), DV_seam {DV_seam} ({DV_seam * 1024:.2f})")
# full-corner accounting under the shifted pin table
DV = DV_land
n_run = n_cap = n_off = 0
for u, v in uv32:
    vv = v - DV
    if any(abs(vv - a) <= CM._SAND_EPS_V for a in CM.SAND_V_LAND + CM.SAND_V_SEAM):
        n_run += 1
    elif any(abs(vv - a) <= CM._SAND_EPS_V
             for a in CM.SAND_V_CAP_LAND + CM.SAND_V_CAP_SEAM):
        n_cap += 1
    else:
        n_off += 1
in_u = sum(1 for u, v in uv32
           if CM.SAND_ULAT[0] + DU - 0.004 <= u <= CM.SAND_ULAT[2] + DU + 0.004)
print(f"   corner accounting under [pins + ({DU},{DV})]: run {n_run} cap {n_cap} "
      f"off-pin {n_off} (conforming tier); u in shifted strip {in_u}/{len(uv32)}")
out["sand_translation"] = dict(du=DU, dv=DV, dv_seam=DV_seam,
                               run=n_run, cap=n_cap, off=n_off, corners=len(uv32))

# ---- C. the foam ribbon on desert vs grass beaches ----------------------------------------------
print("\nC. beach1 (foam) uv ranges:")
foam = {"desert": [], "grass": []}
for (bx, by), c, fam in rows:
    if fam not in foam:
        continue
    fb = X.read_block(bx, by, disc=1, part="beach1")
    for vtx in range(len(fb.uvs)):
        foam[fam].append((float(fb.uvs[vtx][0]), float(fb.uvs[vtx][1])))
for fam, uvs in foam.items():
    if not uvs:
        continue
    ua = np.array([u for u, v in uvs])
    va = np.array([v for u, v in uvs])
    print(f"   {fam:6s}: {len(uvs)} corners, u [{ua.min():.4f},{ua.max():.4f}] "
          f"v [{va.min():.4f},{va.max():.4f}]")
    out[f"foam_{fam}"] = dict(u=[round(float(ua.min()), 4), round(float(ua.max()), 4)],
                              v=[round(float(va.min()), 4), round(float(va.max()), 4)])

# ---- D. topo-33 (Lost Continent shore) ----------------------------------------------------------
uv33 = []
for blk in ((6, 3), (7, 2), (7, 3), (8, 2), (8, 3)):
    bm = X.read_block(*blk, disc=1, part="terrain")
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        if X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"] == 33:
            for j in tri:
                uv33.append((float(bm.uvs[j][0]), float(bm.uvs[j][1])))
if uv33:
    ua = np.array([u for u, v in uv33])
    va = np.array([v for u, v in uv33])
    du33 = round(float(ua.min()) - CM.SAND_ULAT[0], 5)
    print(f"\nD. topo-33: {len(uv33)} corners, u [{ua.min():.5f},{ua.max():.5f}] "
          f"v [{va.min():.5f},{va.max():.5f}]  (candidate DU {du33} = "
          f"{du33 * 1024:.1f} texels)")
    out["t33"] = dict(u=[round(float(ua.min()), 5), round(float(ua.max()), 5)],
                      v=[round(float(va.min()), 5), round(float(va.max()), 5)])

(OUTD / "desert_beach_decode.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'desert_beach_decode.json'}")
