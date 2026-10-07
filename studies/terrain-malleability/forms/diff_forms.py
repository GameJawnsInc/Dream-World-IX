"""forms lane CENSUS 3 -- for every IsSwitchable block on disc 1 and disc 4, diff FORM 1 vs FORM 2 the way the
engine sees them.

Form lists are rebuilt exactly as WMWorld.LoadBlock registers them (WMWorld.cs:582-811, stock order):
  normal block   form1 = [ObjectForm1, TerrainForm1, VolcanoCrater1, VolcanoLava1, <shared>]
                 form2 = [ObjectForm2, TerrainForm2, VolcanoCrater2, VolcanoLava2, <shared>]
                 <shared> = Beach1, Beach2, Stream, River, RiverJoint, Falls, Sea1..Sea6  (registered true,true)
  block 219      form1 = [ObjectForm1, TerrainForm1, Sea3, Sea4, Sea5]        (early-return branch :602-636)
                 form2 = [ObjectForm2, TerrainForm2, Sea3_2, Sea4_2, Sea5_2]
The SURFACE instrument emulates a sky cast (WMPhysics.CastRayFromSky; walk-decode-claims.md items 5/8/112): at each
of 64x64 sample points (0.5u inset lattice), the FIRST mesh in list order, and within it the FIRST triangle in
array order, whose XZ projection contains the point and whose normal.y > 0.1 (WMPhysics.cs:22-28) wins -> (y, IDALL).
CALIBRATION (runs first, aborts on failure): (a) form1-vs-form1 must report 0 changed samples; (b) a synthetic
+1.0u lift of the terrain tris whose centroid lies in local x<16 must be detected with changed-sample bbox inside
x<20 and dy_max == 1.0 -> proves the detector can fail.
Outputs out/form_diff.json (derived numbers only).  Rerun:  py diff_forms.py
"""
import sys, json, re, collections
from pathlib import Path
import numpy as np
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X

HERE = Path(__file__).parent
CENSUS = json.loads((HERE / "out" / "prefab_census.json").read_text())
SHARED = ["Beach1", "Beach2", "Stream", "River", "RiverJoint", "Falls", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Sea6"]


def form_lists(row):
    s = row["slots"]
    if row["Number"] == 219:
        f1 = ["ObjectForm1", "TerrainForm1", "Sea3", "Sea4", "Sea5"]
        f2 = ["ObjectForm2", "TerrainForm2", "Sea3_2", "Sea4_2", "Sea5_2"]
    else:
        f1 = ["ObjectForm1", "TerrainForm1", "VolcanoCrater1", "VolcanoLava1"] + SHARED
        f2 = ["ObjectForm2", "TerrainForm2", "VolcanoCrater2", "VolcanoLava2"] + SHARED
    return [k for k in f1 if k in s], [k for k in f2 if k in s]


_mcache = {}


def load_mesh(mesh_path):
    m = re.match(r"worldmap/disc(\d)/(0_\d)/r(\d+)/block\[(\d+)\]\[(\d+)\] (\w+)\.asset", mesh_path)
    disc, lod, x, y, part = int(m.group(1)), m.group(2), int(m.group(4)), int(m.group(5)), m.group(6)
    key = (disc, lod, x, y, part)
    if key not in _mcache:
        bm = X.read_block(x, y, disc=disc, lod=lod, part=part)
        V = np.array(bm.verts, dtype=np.float64)
        T = np.array(bm.tris, dtype=np.int64)
        tan = bm.tangents
        ids = np.array([int(tan[t[0]][0]) for t in bm.tris], dtype=np.int64) if tan else np.zeros(len(T), np.int64)
        _mcache[key] = (V, T, ids)
    return _mcache[key]


XS = np.arange(64) + 0.5
PX, PZ = np.meshgrid(XS, -XS, indexing="xy")       # local x in [0,64], local z in [-64,0]
PX, PZ = PX.ravel(), PZ.ravel()


def surface(meshes):
    """meshes: list of (name, V, T, ids) in registration order -> y, idall, part-index per sample (nan/-1 = miss)."""
    n = PX.size
    Y = np.full(n, np.nan)
    ID = np.full(n, -1, np.int64)
    P = np.full(n, -1, np.int64)
    for mi, (name, V, T, ids) in enumerate(meshes):
        if not np.isnan(Y).any():
            break
        a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        nrm = np.cross(b - a, c - a)
        ln = np.linalg.norm(nrm, axis=1)
        ln[ln == 0] = 1
        ok = (nrm[:, 1] / ln) > 0.1
        for ti in np.nonzero(ok)[0]:
            un = np.isnan(Y)
            if not un.any():
                break
            ax, az, bx, bz, cx, cz = a[ti, 0], a[ti, 2], b[ti, 0], b[ti, 2], c[ti, 0], c[ti, 2]
            sel = un & (PX >= min(ax, bx, cx) - 1e-6) & (PX <= max(ax, bx, cx) + 1e-6) & \
                (PZ >= min(az, bz, cz) - 1e-6) & (PZ <= max(az, bz, cz) + 1e-6)
            if not sel.any():
                continue
            idx = np.nonzero(sel)[0]
            px, pz = PX[idx], PZ[idx]
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
            Y[j] = l1[inside] * a[ti, 1] + l2[inside] * b[ti, 1] + l3[inside] * c[ti, 1]
            ID[j] = ids[ti]
            P[j] = mi
    return Y, ID, P


def topo(idall):
    return (idall & 0xFC) >> 2


def event(idall):
    return (idall & 0xC000) >> 14


def area(idall):
    return (idall & 0x3F00) >> 8


def tri_sigs(V, T, ids):
    out = collections.Counter()
    for t, i in zip(T, ids):
        out[(tuple(sorted(tuple(np.round(V[k], 3)) for k in t)), int(i))] += 1
    return out


def compare(S1, S2):
    (Y1, I1, P1), (Y2, I2, P2) = S1, S2
    hit1, hit2 = ~np.isnan(Y1), ~np.isnan(Y2)
    both = hit1 & hit2
    dy = np.where(both, Y2 - np.where(both, Y1, 0), 0.0)
    ychg = both & (np.abs(dy) > 0.05)
    idchg = both & (I1 != I2)
    t1, t2 = topo(np.where(I1 < 0, 0, I1)), topo(np.where(I2 < 0, 0, I2))
    topochg = both & (t1 != t2)
    cover = hit1 != hit2
    anychg = ychg | idchg | cover
    res = {"samples": int(PX.size), "hit_f1": int(hit1.sum()), "hit_f2": int(hit2.sum()),
           "y_changed": int(ychg.sum()), "id_changed": int(idchg.sum()), "topo_changed": int(topochg.sum()),
           "coverage_changed": int(cover.sum()), "any_changed": int(anychg.sum()),
           "dy_max": float(dy[ychg].max()) if ychg.any() else 0.0,
           "dy_min": float(dy[ychg].min()) if ychg.any() else 0.0,
           "dy_mean_abs": float(np.abs(dy[ychg]).mean()) if ychg.any() else 0.0}
    if anychg.any():
        res["bbox_local"] = [float(PX[anychg].min() - .5), float(PX[anychg].max() + .5),
                             float(PZ[anychg].min() - .5), float(PZ[anychg].max() + .5)]
    tt = collections.Counter((int(a), int(b)) for a, b in zip(t1[topochg], t2[topochg]))
    res["topo_transitions_top"] = [[f"{a}->{b}", n] for (a, b), n in tt.most_common(6)]
    ev1 = collections.Counter(int(event(i)) for i in I1[hit1])
    ev2 = collections.Counter(int(event(i)) for i in I2[hit2])
    res["event_samples_f1"] = {str(k): v for k, v in ev1.items() if k}
    res["event_samples_f2"] = {str(k): v for k, v in ev2.items() if k}
    part_f1 = collections.Counter(int(p) for p in P1[anychg])
    part_f2 = collections.Counter(int(p) for p in P2[anychg])
    res["_parts_idx"] = [dict(part_f1), dict(part_f2)]
    res["changed_mask"] = anychg
    return res


def calibrate():
    row = [r for r in CENSUS["1"] if (r["x"], r["y"]) == (19, 10)][0]
    f1, _ = form_lists(row)
    ms = [(k, *load_mesh(row["slots"][k]["mesh"])) for k in f1]
    S = surface(ms)
    r0 = compare(S, S)
    assert r0["any_changed"] == 0, ("self-compare not zero", r0)
    ms2 = []
    for k, V, T, ids in ms:
        if k == "TerrainForm1":
            V = V.copy()
            cen = V[T].mean(axis=1)
            lift = np.zeros(len(V), bool)
            for t, cc in zip(T, cen):
                if cc[0] < 16:
                    lift[t] = True
            V[lift, 1] += 1.0
        ms2.append((k, V, T, ids))
    r1 = compare(S, surface(ms2))
    ok = r1["y_changed"] > 0 and r1["bbox_local"][1] <= 20.0 and abs(r1["dy_max"] - 1.0) < 1e-6
    assert ok, ("lift not detected", {k: v for k, v in r1.items() if k != "changed_mask"})
    print(f"CALIBRATION OK: self-diff 0/{r0['samples']}; synthetic x<16 +1.0 lift -> {r1['y_changed']} samples, "
          f"bbox x[{r1['bbox_local'][0]},{r1['bbox_local'][1]}], dy_max {r1['dy_max']:.3f}  "
          f"(note: samples where Object1 is first-hit stay unchanged -> fewer than 16*64)")


def main():
    calibrate()
    out = {}
    for d in ("1", "4"):
        rows = [r for r in CENSUS[d] if r["IsSwitchable"]]
        out[d] = {}
        print(f"\n=== disc {d}: {len(rows)} switchable blocks ===")
        print(f"{'cell':>8} {'num':>4} {'L1/L2':>5} {'terr tri f1/f2':>15} {'obj tri f1/f2':>13} {'sig rm/add':>10} "
              f"{'chg/4096':>8} {'cov':>4} {'dy range':>14} {'topo':>5}  bbox(local)          topo transitions")
        for r in sorted(rows, key=lambda r: r["Number"]):
            f1, f2 = form_lists(r)
            m1 = [(k, *load_mesh(r["slots"][k]["mesh"])) for k in f1]
            m2 = [(k, *load_mesh(r["slots"][k]["mesh"])) for k in f2]
            S1, S2 = surface(m1), surface(m2)
            res = compare(S1, S2)
            mask = res.pop("changed_mask")
            pidx = res.pop("_parts_idx")
            res["changed_first_hit_part_f1"] = {f1[k]: v for k, v in pidx[0].items() if k >= 0}
            res["changed_first_hit_part_f2"] = {f2[k]: v for k, v in pidx[1].items() if k >= 0}

            def ntri(ms, key):
                for k, V, T, ids in ms:
                    if k == key:
                        return len(T)
                return 0
            res["terrain_tris"] = [ntri(m1, "TerrainForm1"), ntri(m2, "TerrainForm2")]
            res["object_tris"] = [ntri(m1, "ObjectForm1"), ntri(m2, "ObjectForm2")]
            res["walk_list_len"] = [len(f1), len(f2)]
            res["walk_list"] = [f1, f2]
            a = [m for m in m1 if m[0] == "TerrainForm1"][0]
            b = [m for m in m2 if m[0] == "TerrainForm2"][0]
            sa, sb = tri_sigs(*a[1:]), tri_sigs(*b[1:])
            res["terrain_sig_removed"] = int(sum((sa - sb).values()))
            res["terrain_sig_added"] = int(sum((sb - sa).values()))
            res["terrain_sig_common"] = int(sum((sa & sb).values()))
            res["terrain_y_range_f1"] = [float(a[1][:, 1].min()), float(a[1][:, 1].max())]
            res["terrain_y_range_f2"] = [float(b[1][:, 1].min()), float(b[1][:, 1].max())]
            res["areas_f1"] = sorted({int(area(i)) for i in a[3]})
            res["areas_f2"] = sorted({int(area(i)) for i in b[3]})
            res["mask_rows"] = ["".join("#" if mask[j * 64 + i] else "." for i in range(0, 64, 2)) for j in range(0, 64, 2)]
            out[d][f"{r['x']},{r['y']}"] = res
            bb = res.get("bbox_local")
            bbs = f"[{bb[0]:.0f},{bb[1]:.0f},{bb[2]:.0f},{bb[3]:.0f}]" if bb else "-"
            print(f"{str((r['x'], r['y'])):>8} {r['Number']:>4} {len(f1)}/{len(f2):<3} "
                  f"{res['terrain_tris'][0]:>6}/{res['terrain_tris'][1]:<7} {res['object_tris'][0]:>5}/{res['object_tris'][1]:<6}"
                  f" {res['terrain_sig_removed']:>4}/{res['terrain_sig_added']:<5} {res['any_changed']:>8} "
                  f"{res['coverage_changed']:>4} {res['dy_min']:>6.2f}..{res['dy_max']:<6.2f} {res['topo_changed']:>5}  "
                  f"{bbs:<20} {res['topo_transitions_top'][:3]}")
    (HERE / "out" / "form_diff.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("\nwrote", HERE / "out" / "form_diff.json")


if __name__ == "__main__":
    main()
