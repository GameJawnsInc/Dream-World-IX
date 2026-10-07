"""Score terrain_session1's published heights against the LIVE mesh at the exact x/z each reading was taken.

For every vertical sample: the engine's SKY ground query at (x, z) (first registered walk mesh with a passing hit,
first passing tri in buffer order, skip ids out, geometric ny > 0.1, 0x31EE veto abandons the mesh -- the same rule
as gap_area_layer/arealib.raster, which is calibrated against world/placement.place), the topograph there, and
published_y - ground. Registered prediction (vertical V3): topo 36/37/38 -> -1.171875; anything else -> 0 (+-0.15).
Also re-reads the area under each area-part position.

Rerun:  py studies/terrain-malleability/ingame/session1_post.py <.harness-runs/... run dir>
"""
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "gap_area_layer"))
import arealib as A                                  # noqa: E402
import numpy as np                                   # noqa: E402

SINK = 1.171875
CANOPY = (36, 37, 38)
TOL = 0.15
_CELLS = None
_MESH = {}


def walk_meshes(bx, by, disc=1):
    global _CELLS
    if (bx, by) in _MESH:
        return _MESH[(bx, by)]
    if _CELLS is None:
        _CELLS = A.live_cells()
    cf = _CELLS.get((disc, bx, by), {})
    if cf:
        _pk, _why, walk = A.live_walk_list(disc, bx, by, cf)
    else:
        walk = [(n, k, "stock") for n, k in A.stock_walk_list(disc, bx, by)]
    _MESH[(bx, by)] = (A.load_walk_arrays(walk), walk)
    return _MESH[(bx, by)]


def ground(x, z, disc=1):
    bx, by = int(math.floor(x / 64.0)), int(math.floor(-z / 64.0))
    meshes, walk = walk_meshes(bx, by, disc)
    lx, lz = x - bx * 64.0, z + by * 64.0
    for (name, V, ids), w in zip(meshes, walk):
        if V.size == 0:
            continue
        a, b, c = V[:, 0], V[:, 1], V[:, 2]
        u, v = b - a, c - a
        cx = u[:, 1] * v[:, 2] - u[:, 2] * v[:, 1]
        cy = u[:, 2] * v[:, 0] - u[:, 0] * v[:, 2]
        cz = u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]
        L = np.sqrt(cx * cx + cy * cy + cz * cz)
        L[L == 0] = 1.0
        d = (b[:, 2] - c[:, 2]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 2] - c[:, 2])
        ok = (cy / L > 0.1) & ~np.isin(ids, A.IDALL_SKIP) & (np.abs(d) >= 1e-12)
        dd = np.where(ok, d, 1.0)
        w0 = ((b[:, 2] - c[:, 2]) * (lx - c[:, 0]) + (c[:, 0] - b[:, 0]) * (lz - c[:, 2])) / dd
        w1 = ((c[:, 2] - a[:, 2]) * (lx - c[:, 0]) + (a[:, 0] - c[:, 0]) * (lz - c[:, 2])) / dd
        w2 = 1 - w0 - w1
        inside = ok & (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        hits = np.nonzero(inside)[0]
        if hits.size == 0:
            continue
        t = hits[0]
        idv = int(ids[t])
        if idv == A.VETO:
            continue
        hy = float(w0[t] * a[t, 1] + w1[t] * b[t, 1] + w2[t] * c[t, 1])
        return {"ground": round(hy, 4), "part": name, "id": idv, "area": (idv & 0x3F00) >> 8,
                "topo": (idv & 0xFC) >> 2, "event": (idv & 0xC000) >> 14, "cell": [bx, by]}
    return {"ground": None, "part": "MISS", "cell": [bx, by]}


def main(run_dir):
    run_dir = Path(run_dir)
    rec = json.loads((run_dir / "terrain_session1.json").read_text(encoding="utf-8"))
    out = {"vertical": {}, "area": {}}
    for tag, rows in rec.get("vertical", {}).items():
        scored = []
        for r in rows:
            if r.get("x") is None or r.get("y") is None:
                continue
            g = ground(r["x"], r["z"])
            row = {**r, **g}
            if g["ground"] is not None:
                delta = r["y"] - g["ground"]
                want = -SINK if g["topo"] in CANOPY else 0.0
                row.update(delta=round(delta, 4), predicted=want, ok=abs(delta - want) <= TOL)
            scored.append(row)
        out["vertical"][tag] = scored
        for s in scored:
            print(f"{tag:6s} {s['after']:12s} ({s['x']:.2f},{s['z']:.2f}) y {s['y']:.3f} ground {s.get('ground')} "
                  f"topo {s.get('topo')} {s.get('part')} delta {s.get('delta')} predicted {s.get('predicted')} "
                  f"{'OK' if s.get('ok') else 'MISMATCH'}")
    for k in ("P14_start", "P12_reached", "P14_back"):
        p = rec.get("area", {}).get(k)
        if p and p.get("x") is not None:
            g = ground(p["x"], p["z"])
            out["area"][k] = {**p, **g}
            print(f"area {k:12s} ({p['x']:.2f},{p['z']:.2f}) -> area {g.get('area')} topo {g.get('topo')} "
                  f"event {g.get('event')} {g.get('part')}  published y {p.get('y')} ground {g.get('ground')}")
    (run_dir / "session1_post.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(f"wrote {run_dir / 'session1_post.json'}")


if __name__ == "__main__":
    main(sys.argv[1])
