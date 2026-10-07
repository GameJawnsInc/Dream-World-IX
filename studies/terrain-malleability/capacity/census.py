"""CAPACITY lane, step 4 -- THE STOCK GEOMETRY CENSUS: per part, per block, both discs, both mesh dirs
(0_1 = Form 1, 0_2 = Form 2 -- see universe.py / prefab_children.py): vertex/index/triangle counts,
the unindexed-contract check, terrain edge-length / area / lattice / up-facing distributions, and the
per-tri UV RATE (atlas px per world unit, isometric-unfold Jacobian singular values) for BOTH the vanilla
atlas and the HD atlas the engine actually renders.

Decodes straight from the bundle's Mesh objects with numpy (one pass, ~2200 meshes). CALIBRATED against
the kit's own reader: for 3 blocks the vertex positions + index buffer must equal
`ff9mapkit.world.extract.read_block` exactly (asserted -- the run aborts otherwise).

Writes out/census_cache.json (per-mesh stats; derived numbers only) + prints the summary.
Run:  py studies/terrain-malleability/capacity/census.py            (uses the cache if present)
      py studies/terrain-malleability/capacity/census.py --rebuild  (re-decode from the install)
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
CACHE = OUT / "census_cache.json"
PAT = re.compile(r"worldmap/disc(\d+)/(0_[12])/r(\d+)/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
LATTICE = 4.0
TOL = 1e-3
# atlas dims (verified by atlas_dims.py): vanilla p0data texture vs the loose HD override the engine renders
ATLAS = {"vanilla": (1024.0, 1024.0), "hd": (2048.0, 4096.0)}
# the OBJECT atlas the engine renders is a different loose file: res(1_24)_objects.png = 4096x4096 (resolution.py)
ATLAS_OBJECT = {"vanilla": (1024.0, 1024.0), "hd": (4096.0, 4096.0)}


def decode(md):
    """(V[n,3], U[n,2] or None, T[n,4] or None, I[m]) from a Unity 5.2 Mesh (float32 channels, u16/u32 idx)."""
    vd = md.m_VertexData
    raw = bytes(vd.m_DataSize)
    n = int(vd.m_VertexCount)
    chans, stride = {}, 0
    for ci, c in enumerate(vd.m_Channels):
        if c.dimension:
            chans[ci] = (int(c.offset), int(c.dimension))
            stride = max(stride, int(c.offset) + int(c.dimension) * 4)
    assert n * stride == len(raw), "stride mismatch"
    buf = np.frombuffer(raw, dtype="<f4").reshape(n, stride // 4)

    def ch(ci):
        if ci not in chans:
            return None
        off, dim = chans[ci]
        return buf[:, off // 4: off // 4 + dim].astype(np.float64)

    ib = bytes(md.m_IndexBuffer)
    use32 = getattr(md, "m_IndexFormat", None) == 1 or getattr(md, "m_Use16BitIndices", 1) in (0, False)
    I = np.frombuffer(ib, dtype="<u4" if use32 else "<u2").astype(np.int64)
    return ch(X.CH_POS), ch(X.CH_UV), ch(X.CH_TAN), I, use32, len(md.m_SubMeshes)


def pct(a, ps=(0, 1, 5, 50, 95, 99, 100)):
    a = np.asarray(a, dtype=float)
    if a.size == 0:
        return {}
    return {f"p{p}": round(float(np.percentile(a, p)), 5) for p in ps} | {"n": int(a.size),
                                                                          "mean": round(float(a.mean()), 5)}


def tri_metrics(V, U, I, atlas=None):
    atlas = atlas or ATLAS
    T = I.reshape(-1, 3)
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    e = np.stack([np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1), np.linalg.norm(a - c, axis=1)], 1)
    exz = np.stack([np.linalg.norm((b - a)[:, [0, 2]], axis=1), np.linalg.norm((c - b)[:, [0, 2]], axis=1),
                    np.linalg.norm((a - c)[:, [0, 2]], axis=1)], 1)
    cr = np.cross(b - a, c - a)
    area3 = 0.5 * np.linalg.norm(cr, axis=1)
    areaxz = 0.5 * np.abs(cr[:, 1])
    ny = np.where(area3 > 0, cr[:, 1] / np.maximum(2 * area3, 1e-30), 0.0)   # WMBlock.cs:70 geometric normal .y
    out = {"edge3d": e.ravel(), "edgexz": exz.ravel(), "area3d": area3, "areaxz": areaxz, "ny": ny,
           "maxedge3d": e.max(1), "minedge3d": e.min(1)}
    if U is not None:
        # isometric unfold: local 2D frame on the tri plane, then J = dUV/dS (2x2); singular values = px/u
        e1 = b - a
        e2 = c - a
        l1 = np.linalg.norm(e1, axis=1)
        ok = (l1 > 1e-9) & (area3 > 1e-9)
        x1 = l1
        uhat = e1 / np.maximum(l1, 1e-30)[:, None]
        x2 = np.einsum("ij,ij->i", e2, uhat)
        y2 = 2 * area3 / np.maximum(l1, 1e-30)
        du1 = U[T[:, 1]] - U[T[:, 0]]
        du2 = U[T[:, 2]] - U[T[:, 0]]
        rates = {}
        for nm, (W, H) in atlas.items():
            p1 = du1 * np.array([W, H])
            p2 = du2 * np.array([W, H])
            # J * [x1,0]^T = p1 ; J * [x2,y2]^T = p2  ->  J = [p1/x1 , (p2 - x2*p1/x1)/y2]
            c0 = p1 / np.maximum(x1, 1e-30)[:, None]
            c1 = (p2 - x2[:, None] * c0) / np.maximum(y2, 1e-30)[:, None]
            J = np.stack([c0, c1], axis=2)            # [m,2,2], columns = dUV/ds along the two frame axes
            s = np.linalg.svd(J, compute_uv=False)
            rates[nm] = (s[ok, 0], s[ok, 1])
        out["rates"] = rates
        out["uv_area_frac"] = 0.5 * np.abs(du1[:, 0] * du2[:, 1] - du1[:, 1] * du2[:, 0])
    return out


def calibrate(env_idx):
    for (bx, by) in ((12, 10), (19, 10), (15, 14)):
        bm = X.read_block(bx, by, disc=1, part="terrain")
        key = [c for c in env_idx if c.endswith(f"worldmap/disc1/0_1/r{by}/block[{bx}][{by}] terrain")
               or c.endswith(f"worldmap/disc1/0_1/r{by}/block[{bx}][{by}] terrain.asset")][0]
        V, U, T, I, use32, ns = decode(env_idx[key].read())
        assert np.array_equal(V, np.array(bm.verts, dtype=np.float64)), f"pos mismatch {bx},{by}"
        assert list(I) == list(bm.flat_index), f"index mismatch {bx},{by}"
        assert np.array_equal(U, np.array(bm.uvs, dtype=np.float64)), f"uv mismatch {bx},{by}"
        print(f"calibration OK: block ({bx},{by}) v={len(V)} i={len(I)} == read_block")


def build():
    env = X._worldmap_env(1)
    idx = X._mesh_index(env)
    calibrate(idx)
    rows = []
    agg = defaultdict(lambda: defaultdict(list))   # (disc, dir, part) -> metric -> arrays
    for c, o in idx.items():
        m = PAT.search(c)
        if not m:
            continue
        disc, d, by, bx, part = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4)), m.group(6)
        V, U, T, I, use32, ns = decode(o.read())
        n, ni = len(V), len(I)
        r = {"disc": disc, "dir": d, "x": bx, "y": by, "part": part, "v": n, "i": ni, "tris": ni // 3,
             "u32": bool(use32), "subm": ns, "unindexed": bool(n == ni),
             "idx_max": int(I.max()) if ni else -1,
             "xz_min": [round(float(V[:, 0].min()), 3), round(float(V[:, 2].min()), 3)],
             "xz_max": [round(float(V[:, 0].max()), 3), round(float(V[:, 2].max()), 3)],
             "y_min": round(float(V[:, 1].min()), 3), "y_max": round(float(V[:, 1].max()), 3)}
        tm = tri_metrics(V, U, I, ATLAS_OBJECT if part == "object" else ATLAS)
        onlat = (np.abs(V[:, 0] / LATTICE - np.round(V[:, 0] / LATTICE)) < TOL / LATTICE) & \
                (np.abs(V[:, 2] / LATTICE - np.round(V[:, 2] / LATTICE)) < TOL / LATTICE)
        r["onlattice_frac"] = round(float(onlat.mean()), 4)
        r["degenerate_tris"] = int((tm["area3d"] < 1e-6).sum())
        r["upfacing_frac"] = round(float((tm["ny"] > 0.1).mean()), 4) if len(tm["ny"]) else 0.0
        r["sublattice_tris"] = int((tm["maxedge3d"] < LATTICE * 0.5).sum())      # every edge < 2u
        r["area3d_sum"] = round(float(tm["area3d"].sum()), 2)
        r["areaxz_sum"] = round(float(tm["areaxz"].sum()), 2)
        r["edge3d_med"] = round(float(np.median(tm["edge3d"])), 4)
        r["edge3d_min"] = round(float(tm["edge3d"].min()), 5)
        r["area3d_min_nondeg"] = round(float(tm["area3d"][tm["area3d"] >= 1e-6].min()), 6) \
            if (tm["area3d"] >= 1e-6).any() else None
        if T is not None:
            ids = np.round(T[I.reshape(-1, 3)[:, 0], 0]).astype(np.int64)
            r["distinct_idall"] = int(len(np.unique(ids)))
        if "rates" in tm:
            for nm, (smax, smin) in tm["rates"].items():
                if len(smax):
                    r[f"rate_{nm}_med_max"] = round(float(np.median(smax)), 3)
                    r[f"rate_{nm}_med_min"] = round(float(np.median(smin)), 3)
        rows.append(r)
        k = (disc, d, part)
        for nm in ("edge3d", "edgexz", "area3d", "areaxz"):
            agg[k][nm].append(tm[nm])
        if "rates" in tm:
            for nm, (smax, smin) in tm["rates"].items():
                agg[k][f"rate_{nm}_max"].append(smax)
                agg[k][f"rate_{nm}_min"].append(smin)
            agg[k]["uv_area_frac"].append(tm["uv_area_frac"])
    dist = {}
    for (disc, d, part), mets in agg.items():
        dist[f"disc{disc}|{d}|{part}"] = {nm: pct(np.concatenate(arrs)) for nm, arrs in mets.items()}
    data = {"rows": rows, "dist": dist}
    CACHE.write_text(json.dumps(data), encoding="utf-8")
    return data


def summarize(data):
    rows = data["rows"]
    print(f"\nmeshes decoded: {len(rows)}")
    print("index format:", {k: sum(1 for r in rows if r['u32'] == k) for k in (False, True)},
          "| submesh counts:", sorted({r['subm'] for r in rows}),
          "| unindexed (v==i):", sum(r['unindexed'] for r in rows), "/", len(rows),
          "| max index value:", max(r['idx_max'] for r in rows))
    byk = defaultdict(list)
    for r in rows:
        byk[(r["disc"], r["dir"], r["part"])].append(r)
    print("\nPER PART (tris per mesh): n | min | median | p99 | max | argmax")
    for k in sorted(byk):
        t = np.array([r["tris"] for r in byk[k]])
        am = max(byk[k], key=lambda r: r["tris"])
        print(f"  disc{k[0]} {k[1]} {k[2]:14s} n={len(t):3d}  min={t.min():5d} med={int(np.median(t)):5d} "
              f"p99={int(np.percentile(t, 99)):5d} max={t.max():5d}  argmax=({am['x']},{am['y']}) v={am['v']}")
    # per-block totals (all parts in the 0_1 Form-1 set = what Form 1 registers as render + walkmesh)
    for disc in (1, 4):
        tot = defaultdict(int)
        ter = {}
        for r in rows:
            if r["disc"] == disc and r["dir"] == "0_1" and r["part"] != "sea4f":
                tot[(r["x"], r["y"])] += r["tris"]
                if r["part"] == "terrain":
                    ter[(r["x"], r["y"])] = r["tris"]
        vals = np.array(list(tot.values()))
        top = sorted(tot.items(), key=lambda kv: -kv[1])[:8]
        print(f"\ndisc{disc} per-block ALL-PARTS tris (0_1, {len(vals)} blocks): med={int(np.median(vals))} "
              f"p99={int(np.percentile(vals, 99))} max={vals.max()} sum={vals.sum()}")
        print("   densest blocks:", [(f"{xy}", t, ter.get(xy)) for xy, t in top])
        print(f"   whole-disc 0_1 vertex total = {sum(r['v'] for r in rows if r['disc'] == disc and r['dir'] == '0_1')}")
    print("\nTERRAIN DISTRIBUTIONS (disc1 0_1):")
    for nm, d in data["dist"]["disc1|0_1|terrain"].items():
        print(f"   {nm:18s} {d}")
    print("\nOBJECT DISTRIBUTIONS (disc1 0_1):")
    for nm in ("edge3d", "area3d", "rate_hd_max", "rate_hd_min"):
        print(f"   {nm:18s} {data['dist']['disc1|0_1|object'].get(nm)}")
    ter1 = [r for r in rows if r["disc"] == 1 and r["dir"] == "0_1" and r["part"] == "terrain"]
    lat = np.array([r["onlattice_frac"] for r in ter1])
    sub = np.array([r["sublattice_tris"] for r in ter1])
    print(f"\nterrain on-4u-lattice vertex fraction: median={np.median(lat):.4f} min={lat.min():.4f} "
          f"blocks<0.99={int((lat < 0.99).sum())}/{len(lat)} | blocks with any all-edges<2u tri: "
          f"{int((sub > 0).sum())}  (total such tris {int(sub.sum())})")
    print("   least-lattice blocks:", sorted(((r['onlattice_frac'], (r['x'], r['y']), r['tris']) for r in ter1))[:6])
    print("   degenerate (area<1e-6) terrain tris:", sum(r["degenerate_tris"] for r in ter1),
          "| non-up-facing (ny<=0.1) terrain-tri share median:",
          round(float(np.median([1 - r['upfacing_frac'] for r in ter1])), 4))
    print("   terrain y range overall:", min(r["y_min"] for r in ter1), max(r["y_max"] for r in ter1))
    print("   terrain distinct IDALL per block: med", int(np.median([r['distinct_idall'] for r in ter1])),
          "max", max(r['distinct_idall'] for r in ter1))
    # 0_1 vs 0_2 (Form1 vs Form2) terrain tri counts
    t01 = {(r["disc"], r["x"], r["y"]): r for r in rows if r["dir"] == "0_1" and r["part"] == "terrain"}
    t02 = [r for r in rows if r["dir"] == "0_2" and r["part"] == "terrain"]
    print("\nFORM-1 (0_1) vs FORM-2 (0_2) terrain tris, disc1:",
          [((r["x"], r["y"]), t01[(1, r["x"], r["y"])]["tris"], r["tris"]) for r in t02 if r["disc"] == 1])


def main():
    if CACHE.exists() and "--rebuild" not in sys.argv:
        data = json.loads(CACHE.read_text(encoding="utf-8"))
    else:
        data = build()
    summarize(data)


if __name__ == "__main__":
    main()
