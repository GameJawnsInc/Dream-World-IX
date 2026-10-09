"""Q1/Q2/Q4/Q6: per block x part x disc inventory for the four Shimmering blocks, and the geometric tri diff
(kept-exact / re-heighted / removed / added) with y, topo, area, event, winding of each class.
Run: cd C:\\gd\\Dream-World-IX\\ff9mapkit ; py <this>   -> out/q1_parts.json + stdout
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np                                         # noqa: E402
import shim_lib as S                                       # noqa: E402


def stats(V, ids, UV=None, N=None):
    if V is None or V.size == 0:
        return {"tris": 0}
    cyraw, cyn = S.plan_cross(V)
    ys = V[:, :, 1].ravel()
    d = {"tris": int(V.shape[0]),
         "y[min,med,max]": S.rng(ys),
         "verts_y==0": f"{int((ys == 0).sum())}/{ys.size}",
         "up_facing": int((cyn > 0.1).sum()), "down_facing": int((cyn < -0.1).sum()),
         "plan_winding_neg": int((cyraw < 0).sum()),
         "plan_area": round(float(S.plan_area(V).sum()), 1),
         "topo": S.hist(S.topo(ids)), "area": S.hist(S.area_bits(ids)), "event": S.hist(S.event_bits(ids)),
         "idall": S.hist(ids, 8)}
    if N is not None:
        d["normals_distinct"] = len({tuple(np.round(n, 4)) for n in N.reshape(-1, 3)})
    return d


def cls_stats(V, ids, sel):
    if not sel.any():
        return {"tris": 0}
    return stats(V[sel], ids[sel])


res = {}
for (bx, by) in S.SHIM:
    blk = {}
    for part in S.PARTS_ALL:
        b1, b4 = S.read(bx, by, 1, part), S.read(bx, by, 4, part)
        if b1 is None and b4 is None:
            continue
        t1 = S.tri_arrays(b1) if b1 else None
        t4 = S.tri_arrays(b4) if b4 else None
        row = {"d1": stats(t1["V"], t1["ids"], N=t1["N"]) if t1 else "ABSENT",
               "d4": stats(t4["V"], t4["ids"], N=t4["N"]) if t4 else "ABSENT"}
        if t1 and t4:
            k1 = [S.tri_key(t) for t in t1["V"]]
            k4 = [S.tri_key(t) for t in t4["V"]]
            x1 = [S.xz_key(t) for t in t1["V"]]
            x4 = [S.xz_key(t) for t in t4["V"]]
            s1, s4 = Counter(k1), Counter(k4)
            sx1, sx4 = Counter(x1), Counter(x4)
            kept4 = np.array([s1[k] > 0 for k in k4])
            reh4 = np.array([(s1[k] == 0) and sx1[x] > 0 for k, x in zip(k4, x4)])
            new4 = ~kept4 & ~reh4
            kept1 = np.array([s4[k] > 0 for k in k1])
            reh1 = np.array([(s4[k] == 0) and sx4[x] > 0 for k, x in zip(k1, x1)])
            gone1 = ~kept1 & ~reh1
            # attribute changes on kept tris: idall / uv
            id_chg = uv_chg = 0
            m1 = {}
            for i, k in enumerate(k1):
                m1.setdefault(k, i)
            for j, k in enumerate(k4):
                if s1[k] > 0:
                    i = m1[k]
                    if t1["ids"][i] != t4["ids"][j]:
                        id_chg += 1
                    if t1["UV"] is not None and t4["UV"] is not None:
                        # compare uv per matched corner
                        o1 = {tuple(np.round(p, 3)): uv for p, uv in zip(t1["V"][i], t1["UV"][i])}
                        if any(not np.allclose(o1.get(tuple(np.round(p, 3)), uv), uv, atol=1e-4)
                               for p, uv in zip(t4["V"][j], t4["UV"][j])):
                            uv_chg += 1
            row["diff"] = {
                "d4_kept_exact": int(kept4.sum()), "d4_reheighted": int(reh4.sum()), "d4_new": int(new4.sum()),
                "d1_removed": int(gone1.sum()),
                "kept_idall_changed": id_chg, "kept_uv_changed": uv_chg,
                "removed_d1": cls_stats(t1["V"], t1["ids"], gone1),
                "reheighted_d1": cls_stats(t1["V"], t1["ids"], reh1),
                "reheighted_d4": cls_stats(t4["V"], t4["ids"], reh4),
                "new_d4": cls_stats(t4["V"], t4["ids"], new4),
            }
        blk[part] = row
    res[f"{bx},{by}"] = blk

(S.OUT / "q1_parts.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
for bk, blk in res.items():
    print(f"\n=== block ({bk}) ===")
    for part, row in blk.items():
        d1, d4 = row["d1"], row["d4"]
        f = lambda d: d if isinstance(d, str) else (f"{d['tris']} tris y{d.get('y[min,med,max]')} topo{d.get('topo')} "
                                                     f"ev{d.get('event')} area{d.get('area')} y0 {d.get('verts_y==0')} "
                                                     f"up{d.get('up_facing')} dn{d.get('down_facing')} neg{d.get('plan_winding_neg')} "
                                                     f"A{d.get('plan_area')}")
        print(f" {part:8s} d1: {f(d1)}")
        print(f" {'':8s} d4: {f(d4)}")
        if "diff" in row:
            df = row["diff"]
            print(f"   diff kept {df['d4_kept_exact']} reh {df['d4_reheighted']} new {df['d4_new']} removed {df['d1_removed']}"
                  f" | kept id-chg {df['kept_idall_changed']} uv-chg {df['kept_uv_changed']}")
            for c in ("removed_d1", "reheighted_d1", "reheighted_d4", "new_d4"):
                d = df[c]
                if d["tris"]:
                    print(f"     {c:14s} {f(d)}")
