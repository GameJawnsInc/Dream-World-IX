"""CALIBRATION of the lane's two mesh instruments -- run BEFORE stock_atlas.py / live_audit.py are trusted.

C1  THE AREA READER: a stock block's per-tri IDALL list + area histogram read (a) from p0data through the EXACT
    container match and (b) from a byte-copy serialized with the kit's own ff9mesh_bytes() into the SCRATCHPAD
    (never the repo) and parsed by arealib.read_ff9mesh_arrays, must be IDENTICAL. Then the check is shown to be
    able to FAIL: flipping one tri's area bits in the copy must be detected.
C2  THE RASTER: arealib.raster (vectorized sky query) vs the kit's byte-exact simulator world/placement.place(sky=True)
    on random sample points of random stock cells on both discs (incl. IsSea cells and Object-bearing cells). The
    (idall, part) verdict must agree on >= 99.5% of samples; every disagreement is listed.

Rerun:  py studies/terrain-malleability/gap_area_layer/calibrate.py   -> out/calibration.json  (exit 1 on FAIL)
"""
import json
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import arealib as A                                  # noqa: E402
import numpy as np                                   # noqa: E402
from ff9mapkit.world import mesh as WM               # noqa: E402
from ff9mapkit.world import placement as P           # noqa: E402


def c1():
    key = "d1/0_1/8,17/terrain"
    bm = A.stock_bm(key)
    V0, ids0 = A.arrays_from_bm(bm.verts, bm.tangents, bm.flat_index)
    A.SCRATCH.mkdir(parents=True, exist_ok=True)
    cp = A.SCRATCH / "calib_8_17_terrain.ff9mesh"
    raw = WM.ff9mesh_bytes(bm)
    cp.write_bytes(raw)
    V1, ids1 = A.read_ff9mesh_arrays(cp)
    h0, h1 = A.tri_hist(V0, ids0), A.tri_hist(V1, ids1)
    same = bool(np.array_equal(ids0, ids1)) and h0 == h1 and np.allclose(V0, V1, atol=1e-5)
    # can-fail: corrupt the area bits of tri 0's corner-0 tangent.x in the copy
    import struct
    b = bytearray(raw)
    vc, ic, fl = struct.unpack_from("<iii", b, 8)
    off_tan = 20 + vc * 12 + (vc * 12 if fl & 1 else 0) + (vc * 8 if fl & 2 else 0)
    idx0 = struct.unpack_from("<i", b, off_tan + vc * 16)[0]       # tri 0 corner 0 vertex index
    tx = struct.unpack_from("<f", b, off_tan + idx0 * 16)[0]
    newid = (int(tx) & ~0x3F00) | (((((int(tx) >> 8) & 0x3F) + 1) & 0x3F) << 8)
    struct.pack_into("<f", b, off_tan + idx0 * 16, float(newid))
    cp2 = A.SCRATCH / "calib_8_17_terrain_corrupt.ff9mesh"
    cp2.write_bytes(bytes(b))
    _, ids2 = A.read_ff9mesh_arrays(cp2)
    detects = A.tri_hist(V1, ids2) != h0 or not np.array_equal(ids0, ids2)
    return {"block": key, "tris": int(len(ids0)), "hist_p0data": h0, "hist_ff9mesh": h1, "identical": same,
            "corruption_detected": bool(detects), "ok": bool(same and detects)}


def c2(seed=7, ncell=24, nsamp=96):
    rng = random.Random(seed)
    cen = A.census()
    rows, agree, total = [], 0, 0
    from collections import Counter
    names = Counter()
    for d in (1, 4):
        cells = [(x, y) for x in range(24) for y in range(20)]
        pick = rng.sample(cells, ncell)
        # guarantee coverage of interesting cases: an IsSea cell and an Object-bearing cell
        pick += [(0, 0), (11, 0), (19, 18), (12, 10)]
        for (x, y) in pick:
            walk = A.stock_walk_list(d, x, y)
            meshes = [(n, *A.stock_mesh(k)) for n, k in walk]
            ids, pi, ys = A.raster(meshes, pitch=1.0)
            bms = [(n, A.stock_bm(k)) for n, k in walk]
            idx = [P.build_index(bm) for _, bm in bms]
            px, pz, n = A.sample_grid(1.0)
            for s in rng.sample(range(px.size), nsamp):
                gy, name, idall, topo = P.place(bms, float(px[s]), float(pz[s]), 0.0, sky=True, index=idx)
                mine_name = walk[pi[s]][0] if pi[s] >= 0 else "MISS"
                mine_id = int(ids[s]) if ids[s] >= 0 else 0
                ok = (mine_name == name) and (mine_id == idall) and (name == "MISS" or abs(gy - ys[s]) < 1e-3)
                total += 1
                names[name] += 1
                agree += int(bool(ok))
                if not ok and len(rows) < 40:
                    rows.append({"disc": d, "cell": [x, y], "x": float(px[s]), "z": float(pz[s]),
                                 "place": [name, idall, round(gy, 4)], "raster": [mine_name, mine_id, round(float(ys[s]), 4)]})
    rate = agree / total
    return {"samples": total, "agree": agree, "rate": rate, "by_part": dict(names), "disagreements": rows, "ok": rate >= 0.995}


def main():
    A.OUT.mkdir(exist_ok=True)
    r1 = c1()
    print("C1 area reader:", {k: v for k, v in r1.items() if not k.startswith("hist")})
    r2 = c2()
    print("C2 raster vs placement.place:", {k: v for k, v in r2.items() if k != "disagreements"})
    for row in r2["disagreements"][:10]:
        print("   ", row)
    ok = r1["ok"] and r2["ok"]
    (A.OUT / "calibration.json").write_text(json.dumps({"C1": r1, "C2": r2, "ok": ok}, indent=1), encoding="utf-8")
    print("CALIBRATION", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
