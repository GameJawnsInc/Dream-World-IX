"""VERIFIER (forms lane, F5/F10) -- does diff_forms.py's sky-cast emulator omit engine raycast filters that matter?

diff_forms.py emulates WMPhysics.Raycast with ONLY the `normal.y > 0.1` rule (WMPhysics.cs:22-23). The engine ALSO:
  (a) skips every triangle whose IDALL (tangent.x of corner 0) is 4078, 4088 or 2040 (WMPhysics.cs:15-20,
      unless WMPhysics.IgnoreExceptions), and
  (b) in WMBlock.Raycast(ray, WMMesh, ...) (WMBlock.cs:202-215) REJECTS the whole mesh when its first-hit tri's
      IDALL == 0x31EE (on foot; vehicle type 1 exempt) -- the loop then moves on to the NEXT walk mesh.
This script (1) counts those IDALLs in every switchable cell's form-1/form-2 parts, and (2) re-runs the lane's
sampler with (a)+(b) applied and reports any cell whose changed-sample count or entrance/event counts move.
CALIBRATION: with the filter set EMPTY the patched sampler must reproduce diff_forms.py's numbers exactly.
Rerun:  py verify_raycast_exceptions.py   (needs out/prefab_census.json)
"""
import sys, json, collections
from pathlib import Path
import numpy as np
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import diff_forms as D

SKIP = {4078, 4088, 2040}
REJECT_MESH = 0x31EE


def surface_engine(meshes, skip, reject):
    """Same lattice + barycentric test as D.surface, plus the engine's exception filters."""
    n = D.PX.size
    Y = np.full(n, np.nan)
    ID = np.full(n, -1, np.int64)
    rejected = np.zeros(n, bool)          # samples whose first hit in an EARLIER mesh was a 0x31EE tri
    for mi, (name, V, T, ids) in enumerate(meshes):
        a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        nrm = np.cross(b - a, c - a)
        ln = np.linalg.norm(nrm, axis=1)
        ln[ln == 0] = 1
        ok = ((nrm[:, 1] / ln) > 0.1) & ~np.isin(ids, list(skip))
        claimed = np.zeros(n, bool)       # samples whose first hit is within THIS mesh
        for ti in np.nonzero(ok)[0]:
            un = np.isnan(Y) & ~claimed
            if not un.any():
                break
            ax, az, bx, bz, cx, cz = a[ti, 0], a[ti, 2], b[ti, 0], b[ti, 2], c[ti, 0], c[ti, 2]
            sel = un & (D.PX >= min(ax, bx, cx) - 1e-6) & (D.PX <= max(ax, bx, cx) + 1e-6) & \
                (D.PZ >= min(az, bz, cz) - 1e-6) & (D.PZ <= max(az, bz, cz) + 1e-6)
            if not sel.any():
                continue
            idx = np.nonzero(sel)[0]
            px, pz = D.PX[idx], D.PZ[idx]
            det = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
            if abs(det) < 1e-12:
                continue
            l1 = ((bz - cz) * (px - cx) + (cx - bx) * (pz - cz)) / det
            l2 = ((cz - az) * (px - cx) + (ax - cx) * (pz - cz)) / det
            l3 = 1 - l1 - l2
            inside = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
            if not inside.any():
                continue
            j = idx[inside]
            claimed[j] = True
            if reject is not None and ids[ti] == reject:
                rejected[j] = True       # whole mesh rejected for these samples -> try the next mesh
                continue
            Y[j] = l1[inside] * a[ti, 1] + l2[inside] * b[ti, 1] + l3[inside] * c[ti, 1]
            ID[j] = ids[ti]
    return Y, ID, np.full(n, -1, np.int64)


def main():
    census = json.loads((HERE / "out" / "prefab_census.json").read_text())
    ref = json.loads((HERE / "out" / "form_diff.json").read_text())
    cnt = collections.Counter()
    moved = []
    calib_bad = []
    for d in ("1", "4"):
        for r in sorted([r for r in census[d] if r["IsSwitchable"]], key=lambda r: r["Number"]):
            f1, f2 = D.form_lists(r)
            m1 = [(k, *D.load_mesh(r["slots"][k]["mesh"])) for k in f1]
            m2 = [(k, *D.load_mesh(r["slots"][k]["mesh"])) for k in f2]
            for form, ms in ((1, m1), (2, m2)):
                for k, V, T, ids in ms:
                    for v in (4078, 4088, 2040, REJECT_MESH):
                        c = int((ids == v).sum())
                        if c:
                            cnt[(d, r["x"], r["y"], form, k, v)] += c
            key = f"{r['x']},{r['y']}"
            # calibration: empty filters == the lane's numbers
            base = D.compare(surface_engine(m1, set(), None), surface_engine(m2, set(), None))
            if base["any_changed"] != ref[d][key]["any_changed"]:
                calib_bad.append((d, key, base["any_changed"], ref[d][key]["any_changed"]))
            eng = D.compare(surface_engine(m1, SKIP, REJECT_MESH), surface_engine(m2, SKIP, REJECT_MESH))
            fields = ("any_changed", "y_changed", "topo_changed", "coverage_changed")
            evd = (eng["event_samples_f1"], eng["event_samples_f2"])
            if any(eng[f] != base[f] for f in fields) or evd != (base["event_samples_f1"], base["event_samples_f2"]):
                moved.append((d, key, {f: (base[f], eng[f]) for f in fields},
                              ("events", (base["event_samples_f1"], base["event_samples_f2"]), evd)))
    print("CALIBRATION (empty filters reproduce form_diff.json any_changed):", "OK" if not calib_bad else calib_bad)
    assert not calib_bad
    print("\nexception IDALLs present in switchable-cell walk parts (disc, x, y, form, part, idall): count")
    for k, v in sorted(cnt.items()):
        print("   ", k, v)
    print(f"\ncells whose numbers MOVE once the engine filters are applied: {len(moved)}")
    for m in moved:
        print("   ", m)


if __name__ == "__main__":
    main()
