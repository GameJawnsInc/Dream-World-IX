"""Q5: the UV / normal / weld grammar of the Sea4 the game added over the sunk island, against the stock sheet.
Per 4u lattice cell (by tri centroid): CLEAN = 2 lattice tris covering 16u2 whose 4 corners carry exactly one quadrant
rect of the 2x2 scheme (u breaks 0/0.5039/0.9921, v breaks 0/0.5079/1.0); otherwise CONFORMING. Cells are tagged
by provenance: OPEN (disc-1 sea4 covered all 16u2), PARTIAL (disc 1 covered part: the old coast fringe), NEW (disc 1
had no sea4 there: old land). Reports clean rates, the quadrant + dihedral orientation of clean cells, neighbour
same-quadrant rate, per-tri uv density, whether disc-4 uv in PARTIAL cells continues disc-1's map, normals, and
welds of the new Sea4 to the surviving terrain.
Run: cd C:\\gd\\Dream-World-IX\\ff9mapkit ; py <this>   -> out/q5_uv.json
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np                                         # noqa: E402
import shim_lib as S                                       # noqa: E402

UB = (0.0, 0.5039, 0.9921)
VB = (0.0, 0.5079, 1.0)


def snap(v, brks, tol=2e-3):
    for i, b in enumerate(brks):
        if abs(v - b) < tol:
            return i
    return None


def on_lattice(p, tol=1e-3):
    return abs(p[0] / 4 - round(p[0] / 4)) * 4 < tol and abs(p[2] / 4 - round(p[2] / 4)) * 4 < tol


def cell_of(tri):
    c = tri.mean(axis=0)
    return int(np.floor(c[0] / 4)), int(np.floor(-c[2] / 4))   # (ix, iz) with z going south


def affine(tri, uv):
    A = np.c_[tri[:, 0], tri[:, 2], np.ones(3)]
    try:
        return np.linalg.solve(A, uv)        # 3x2: rows du/dx.., du/dz.., offset
    except np.linalg.LinAlgError:
        return None


def classify_cell(trs):
    """trs = [(V3x3, UV3x2)] -> (clean?, quadrant (qu,qv), orientation key)"""
    if len(trs) != 2:
        return False, None, None
    area = sum(float(S.plan_area(V[None])[0]) for V, _ in trs)
    if abs(area - 16.0) > 1e-3 or not all(on_lattice(p) for V, _ in trs for p in V):
        return False, None, None
    corners = {}
    for V, UV in trs:
        for p, uv in zip(V, UV):
            corners[(round(p[0], 3), round(p[2], 3))] = (snap(uv[0], UB), snap(uv[1], VB))
    if len(corners) != 4 or any(a is None or b is None for a, b in corners.values()):
        return False, None, None
    us = {a for a, _ in corners.values()}
    vs = {b for _, b in corners.values()}
    if len(us) != 2 or len(vs) != 2 or max(us) - min(us) != 1 or max(vs) - min(vs) != 1:
        return False, None, None
    q = (min(us), min(vs))
    xs = sorted({k[0] for k in corners})
    zs = sorted({k[1] for k in corners})
    # orientation: which corner (x-low/high, z-low/high) holds the (u-low, v-low) corner, and the u-axis direction
    ori = []
    for x in xs:
        for z in zs:
            a, b = corners[(x, z)]
            ori.append((a - min(us), b - min(vs)))
    return True, q, tuple(ori)


out = {}
glob = defaultdict(Counter)
dens = defaultdict(list)
cont = Counter()
qmaps = {}
for (bx, by) in S.SHIM:
    t1 = S.tri_arrays(S.read(bx, by, 1, "sea4"))
    t4 = S.tri_arrays(S.read(bx, by, 4, "sea4"))
    k1 = Counter(S.tri_key(v) for v in t1["V"])
    cells = {1: defaultdict(list), 4: defaultdict(list)}
    for d, t in ((1, t1), (4, t4)):
        for V, UV in zip(t["V"], t["UV"]):
            cells[d][cell_of(V)].append((V, UV))
    cov1 = {c: sum(float(S.plan_area(V[None])[0]) for V, _ in trs) for c, trs in cells[1].items()}
    blk = Counter()
    for c, trs in cells[4].items():
        a1 = cov1.get(c, 0.0)
        prov = "OPEN" if a1 > 16 - 1e-3 else ("PARTIAL" if a1 > 1e-3 else "NEW")
        changed = any(k1[S.tri_key(V)] == 0 for V, _ in trs)
        clean, q, ori = classify_cell(trs)
        key = f"{prov}{'-changed' if changed else '-same'}"
        blk[(key, clean)] += 1
        glob[key][clean] += 1
        if clean:
            glob[f"{key}:quadrant"][str(q)] += 1
            glob[f"{key}:orient"][str(ori)] += 1
            qmaps[(bx, by, c)] = q
        # disc-1 grammar of the same cell in OPEN cells (baseline orientation set)
        # continuation test for PARTIAL cells: does a disc-1 tri's affine map predict the disc-4 new tris' uvs?
        if prov == "PARTIAL" and changed:
            M = None
            for V, UV in cells[1][c]:
                M = affine(V, UV)
                if M is not None:
                    break
            if M is not None:
                for V, UV in trs:
                    if k1[S.tri_key(V)] == 0:
                        pred = np.c_[V[:, 0], V[:, 2], np.ones(3)] @ M
                        cont["affine_continuation" if np.allclose(pred, UV, atol=5e-3) else "not_continuation"] += 1
        for V, UV in trs:
            M = affine(V, UV)
            if M is not None:
                dens[(prov, k1[S.tri_key(V)] > 0)].append(float(np.sqrt(abs(np.linalg.det(M[:2, :])))))
    out[f"{bx},{by}"] = {f"{k[0]}|clean={k[1]}": v for k, v in sorted(blk.items())}
    # disc-1 baseline over the same block: clean rate of OPEN cells and of PARTIAL (coast) cells
    b1 = Counter()
    for c, trs in cells[1].items():
        a1 = cov1[c]
        clean, q, ori = classify_cell(trs)
        b1[("d1-full" if a1 > 16 - 1e-3 else "d1-partial", clean)] += 1
        if clean:
            glob["d1-full:orient"][str(ori)] += 1
            glob["d1-full:quadrant"][str(q)] += 1
    out[f"{bx},{by}_d1_baseline"] = {f"{k[0]}|clean={k[1]}": v for k, v in sorted(b1.items())}

out["global"] = {k: {str(a): b for a, b in v.items()} for k, v in glob.items()}
out["partial_cell_continuation_of_d1_map"] = dict(cont)
out["uv_density_per_u[min,med,max]"] = {f"{p}|kept={k}": S.rng(v) + [len(v)] for (p, k), v in dens.items()}

# neighbour same-quadrant rate among clean cells, new vs stock (disc-4 map; 4-neighbour pairs inside a block)
same = Counter()
for (bx, by, (ix, iz)), q in qmaps.items():
    for dx, dz in ((1, 0), (0, 1)):
        q2 = qmaps.get((bx, by, (ix + dx, iz + dz)))
        if q2 is not None:
            same[q == q2] += 1
out["d4_clean_neighbour_same_quadrant"] = {str(k): v for k, v in same.items()}

# normals + welds
nr = Counter()
weld = Counter()
for (bx, by) in S.SHIM:
    t1 = S.tri_arrays(S.read(bx, by, 1, "sea4"))
    t4 = S.tri_arrays(S.read(bx, by, 4, "sea4"))
    tr4 = S.tri_arrays(S.read(bx, by, 4, "terrain"))
    k1 = Counter(S.tri_key(v) for v in t1["V"])
    old_n = Counter(tuple(np.round(n, 4)) for n in t1["N"].reshape(-1, 3))
    tv = {(round(p[0], 3), round(p[2], 3)): p[1] for p in tr4["V"].reshape(-1, 3)}
    sv_old = {(round(p[0], 3), round(p[2], 3)) for p in t1["V"].reshape(-1, 3)}
    for V, N in zip(t4["V"], t4["N"]):
        new = k1[S.tri_key(V)] == 0
        for p, nn in zip(V, N):
            key = tuple(np.round(nn, 4))
            nr[(new, "n=(-0.1211,0.9785,0.1665)" if key == (-0.1211, 0.9785, 0.1665) else
                ("n=(0,1,0)" if key == (0.0, 1.0, 0.0) else ("other_seen_on_d1" if old_n[key] else "other_novel")))] += 1
            if new:
                xz = (round(p[0], 3), round(p[2], 3))
                weld["new_vert_total"] += 1
                if xz in tv:
                    weld["new_vert_on_d4_terrain_vert"] += 1
                    weld["...that_terrain_vert_y==0"] += int(abs(tv[xz]) < 1e-6)
                if xz in sv_old:
                    weld["new_vert_on_d1_sea4_vert_xz"] += 1
                if on_lattice(p):
                    weld["new_vert_on_4u_lattice"] += 1
    # every disc-4 terrain vert at y==0 (the waterline ring of the surviving rocks): is it a sea4 vert too?
    s4v = {(round(p[0], 3), round(p[2], 3)) for p in t4["V"].reshape(-1, 3)}
    for p in tr4["V"].reshape(-1, 3):
        if abs(p[1]) < 1e-6:
            weld["d4_terrain_y0_vert"] += 1
            weld["...shared_with_d4_sea4"] += int((round(p[0], 3), round(p[2], 3)) in s4v)
out["new_sea4_normals"] = {f"new={k[0]}|{k[1]}": v for k, v in nr.items()}
out["welds"] = dict(weld)
(S.OUT / "q5_uv.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print(json.dumps(out, indent=1, default=str))
