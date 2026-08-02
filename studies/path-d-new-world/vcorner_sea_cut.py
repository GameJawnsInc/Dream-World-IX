"""THE SEA-CUT FIX (AMENDMENT 1) — subdivide+delete-hidden on EVERY under-land sea tri
of the six bench cells.

Registration: VSHORE-SEAL-PREDICTION.md "THE SEA-CUT FIX ROUND" + AMENDMENT 1. Run 1
(tri #430 only) fixed the pin wedge but g2 named a RELOCATION to the neighbor tri —
the per-SITE treatment became per-CLASS: all sea-part tris (Beach1/Sea1-5, six cells)
intersecting Terrain plan coverage get adaptive subdivision (sub-edge < 0.875u, the
fan diameter) and deletion of fully-hidden sub-tris. The dual kill is unchanged:
a hidden probe now MISSES (writes nothing to the ring), and no kept fragment can
cover the deflection fan's candidate circle.

Stages (each fits one runner slot):  --stage1  build + verify + walk gates (default)
                                     --stage2  bench-wide latent sweep vs staged
                                     --deploy  backup live, copy staged, revert script
READ-ONLY except --deploy.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402
from probe_vcorner_trap import static_map, drive_walkers    # noqa: E402
from probe_vcorner_latent import sweep, refine              # noqa: E402
from ff9mapkit.world.extract import CH_POS, CH_NRM, CH_UV, CH_TAN  # noqa: E402

SEA_PARTS = ["Beach1", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5"]
SNAPDIR = Path(r"C:\gd\Dream-World-IX\backups\vcorner-trap-live.20260802-133500")
LIVE_ROOT = W.GAME / W.MOD / "FF9_Data" / "WorldMap" / f"Disc{W.DISC}" / "0_1"
OUTD = HERE / "out" / "vcorner_seacut"
BACKUPS = Path(r"C:\gd\Dream-World-IX\backups")
BOAT_LEGAL = {53, 54, 57}
PIN = (376.5, -509.5)
POISONER_LOCAL = [(56.0, 0.0, -60.0), (60.0, 0.0, -64.0), (56.0, 0.0, -64.0)]  # (5,7) Sea4#430


def live_path(bx, by, part):
    return LIVE_ROOT / f"r{by}" / f"Block[{bx}][{by}] {part}.ff9mesh"


def staged_path(bx, by, part):
    return OUTD / f"Block[{bx}][{by}] {part}.ff9mesh"


def snap_path(bx, by, part):
    return SNAPDIR / f"r{by}" / f"Block[{bx}][{by}] {part}.ff9mesh"


def assert_no_drift():
    for (bx, by) in W.CELLS:
        for part in SEA_PARTS:
            lp, sp = live_path(bx, by, part), snap_path(bx, by, part)
            if not lp.is_file():
                continue
            assert sp.is_file(), f"no snapshot for {lp.name} r{by}"
            assert hashlib.md5(lp.read_bytes()).digest() == hashlib.md5(sp.read_bytes()).digest(), \
                f"LIVE DRIFT: {lp} != archived snapshot -- shared install changed, STOP and re-decode"


def bary2(p, a, b, c):
    d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(d) < 1e-12:
        return None
    w0 = ((b[1] - c[1]) * (p[0] - c[0]) + (c[0] - b[0]) * (p[1] - c[1])) / d
    w1 = ((c[1] - a[1]) * (p[0] - c[0]) + (a[0] - c[0]) * (p[1] - c[1])) / d
    return w0, w1, 1.0 - w0 - w1


def terrain_cover(world, x, z):
    """Terrain geometry at plan (x,z) at/above the sea band (hy >= -0.05): hidden-from-
    above is presence, not walkability. ANY terrain tri counts (lawn, wall faces)."""
    bk = W.block_key(x, z)
    if bk not in world:
        return False
    terr = next((m for m in world[bk] if m["name"] == "Terrain"), None)
    if terr is None:
        return False
    for ti in terr["grid"].get((int(x // 4), int(z // 4)), ()):
        tri = terr["tris"][ti]
        w = bary2((x, z), (tri[0][0], tri[0][2]), (tri[1][0], tri[1][2]), (tri[2][0], tri[2][2]))
        if w is None or min(w) < -1e-9:
            continue
        if w[0] * tri[0][1] + w[1] * tri[1][1] + w[2] * tri[2][1] >= -0.05:
            return True
    return False


def tri_samples(p3w):
    """7 canonical plan samples of a (world-frame) tri: corners, edge mids, centroid."""
    pts = [(p[0], p[2]) for p in p3w]
    pts += [((pts[a][0] + pts[b][0]) / 2, (pts[a][1] + pts[b][1]) / 2)
            for a, b in ((0, 1), (1, 2), (0, 2))]
    pts.append((sum(p[0] for p in pts[:3]) / 3, sum(p[1] for p in pts[:3]) / 3))
    return pts


def treat_part(world, bx, by, part, src_path=None, cover=None):
    """Returns (changed_bool, staged BlockMesh or None, records) -- records hold each
    CHANGED tri's subdivision geometry for the independent hidden-cut verifier.
    src_path: read THIS file instead of the live one (pristine-baseline rebuilds).
    cover: alternative cover predicate f(world,x,z) (default terrain_cover = ANY
    terrain; the transplant round cuts under WALKABLE cover only -- sea under the
    non-walk wall band is stock's own FREE-BASE arrangement, and cutting it there
    exposed the deletion boundary as waterline slivers under the overhanging lip)."""
    lp = src_path if src_path is not None else live_path(bx, by, part)
    if not lp.is_file():
        return False, None, []
    if cover is None:
        cover = terrain_cover
    d = W.M.read_ff9mesh(lp)
    if d["tangents"] is None:
        print(f"   [{bx}][{by}] {part}: no tangent channel -- SKIP (mapid semantics unknown)")
        return False, None, []
    ox, oz = 64.0 * bx, -64.0 * by
    idx = d["indices"]
    verts = [list(v) for v in d["verts"]]
    normals = [list(v) for v in d["normals"]] if d["normals"] else None
    uvl = [list(v) for v in d["uvs"]] if d["uvs"] else None
    tangents = [list(v) for v in d["tangents"]]
    new_idx = []
    records = []
    n_treat = n_del_tris = 0
    for t0 in range(0, len(idx), 3):
        t = idx[t0:t0 + 3]
        p3 = [d["verts"][vi] for vi in t]
        p3w = [(p[0] + ox, p[1], p[2] + oz) for p in p3]
        area2 = abs((p3w[1][0] - p3w[0][0]) * (p3w[2][2] - p3w[0][2])
                    - (p3w[2][0] - p3w[0][0]) * (p3w[1][2] - p3w[0][2]))
        if area2 < 0.02 or not any(cover(world, x, z) for (x, z) in tri_samples(p3w)):
            new_idx += list(t)                              # untouched: verbatim
            continue
        tans = [d["tangents"][vi] for vi in t]
        assert tans[0] == tans[1] == tans[2], \
            f"[{bx}][{by}] {part} tri {t0 // 3}: corner tangents differ {tans} -- mapid not uniform, STOP"
        n_treat += 1
        A, B, C = p3
        max_edge = max(math.dist(A, B), math.dist(B, C), math.dist(A, C))
        N = max(2, math.ceil(max_edge / 0.7))
        dU = [(B[k] - A[k]) / N for k in range(3)]
        dV = [(C[k] - A[k]) / N for k in range(3)]
        uvc = [d["uvs"][vi] for vi in t] if uvl is not None else None
        nrc = [d["normals"][vi] for vi in t] if normals is not None else None
        subs = []
        for i in range(N):
            for j in range(N - i):
                subs.append(((i, j), (i + 1, j), (i, j + 1)))
                if i + j < N - 1:
                    subs.append(((i + 1, j), (i + 1, j + 1), (i, j + 1)))
        kept, deleted = [], []
        for s in subs:
            q3 = [[A[k] + i * dU[k] + j * dV[k] for k in range(3)] for (i, j) in s]
            q3w = [(q[0] + ox, q[1], q[2] + oz) for q in q3]
            (deleted if all(cover(world, x, z) for (x, z) in tri_samples(q3w))
             else kept).append(s)
        if not deleted:
            new_idx += list(t)                              # nothing hidden: verbatim
            continue
        n_del_tris += 1
        grid_idx = {}

        def gv(i, j):
            if (i, j) not in grid_idx:
                wu, wv = i / N, j / N
                w0 = 1.0 - wu - wv
                verts.append([A[k] + i * dU[k] + j * dV[k] for k in range(3)])
                if uvl is not None:
                    uvl.append([w0 * uvc[0][k] + wu * uvc[1][k] + wv * uvc[2][k] for k in range(2)])
                if normals is not None:
                    normals.append([w0 * nrc[0][k] + wu * nrc[1][k] + wv * nrc[2][k] for k in range(3)])
                tangents.append(list(tans[0]))
                grid_idx[(i, j)] = len(verts) - 1
            return grid_idx[(i, j)]

        for s in kept:
            tri_i = [gv(i, j) for (i, j) in s]
            a, b, c = (verts[v] for v in tri_i)
            ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
            orig_ny = (p3[1][2] - p3[0][2]) * (p3[2][0] - p3[0][0]) \
                - (p3[1][0] - p3[0][0]) * (p3[2][2] - p3[0][2])
            if ny * orig_ny < 0:
                tri_i[1], tri_i[2] = tri_i[2], tri_i[1]
            new_idx += tri_i
        records.append(dict(ti=t0 // 3, A=A, dU=dU, dV=dV, N=N,
                            kept=set(kept), n_kept=len(kept), n_del=len(deleted),
                            ox=ox, oz=oz))
    if not records:
        return False, None, []
    # THE UNINDEXED CONTRACT (WMBlock.AddWalkMesh iterates vertices.Length/3): expand
    # to 3 fresh verts per tri before writing -- write_ff9mesh asserts vcount == icount.
    ev, en, eu, et, eidx = [], [], [], [], []
    for k in new_idx:
        eidx.append(len(ev))
        ev.append(list(verts[k]))
        if normals is not None:
            en.append(list(normals[k]))
        if uvl is not None:
            eu.append(list(uvl[k]))
        et.append(list(tangents[k]))
    bm = W.M.blockmesh_from_ff9mesh(lp, disc=W.DISC, x=bx, y=by, part=part.lower())
    chan = dict(bm.chan_arrays)
    chan[CH_POS] = ev
    if normals is not None:
        chan[CH_NRM] = en
    if uvl is not None:
        chan[CH_UV] = eu
    chan[CH_TAN] = et
    tris = [[eidx[k], eidx[k + 1], eidx[k + 2]] for k in range(0, len(eidx), 3)]
    out = dataclasses.replace(bm, vcount=len(ev), chan_arrays=chan,
                              flat_index=eidx, tris=tris)
    print(f"   [{bx}][{by}] {part}: {len(idx) // 3} tris, {n_treat} coverage-touched, "
          f"{n_del_tris} changed (subdiv+delete) -> {len(new_idx) // 3} tris, "
          f"{d['vcount']} -> {len(verts)} verts")
    return True, out, records


def build_all(world):
    OUTD.mkdir(parents=True, exist_ok=True)
    manifest = {}
    all_records = {}
    poisoner_treated = False
    for (bx, by) in W.CELLS:
        for part in SEA_PARTS:
            changed, out, records = treat_part(world, bx, by, part)
            if not changed:
                continue
            sp = staged_path(bx, by, part)
            W.M.write_ff9mesh(out, sp)
            manifest[f"{bx},{by},{part}"] = sp.name
            all_records[(bx, by, part)] = records
            if (bx, by, part) == (5, 7, "Sea4") and any(r["ti"] == 430 for r in records):
                poisoner_treated = True
    assert poisoner_treated, "tri #430 (the PROVEN poisoner) was not treated -- predicate broken, STOP"
    json.dump({k: v for k, v in manifest.items()}, open(OUTD / "manifest.json", "w"), indent=1)
    n_changed = sum(len(r) for r in all_records.values())
    print(f"BUILD: {len(manifest)} part files changed, {n_changed} tris subdiv+cut")
    return manifest, all_records


def part_src_from_staged():
    src = {}
    for (bx, by) in W.CELLS:
        for part in SEA_PARTS:
            sp = staged_path(bx, by, part)
            if sp.is_file():
                src[(bx, by, part)] = sp
    return src


def verify(world_live, world_staged, all_records):
    """P-G generalized: per changed tri, fine-sample -- every deleted-region point must
    be Terrain-covered; then the boat legality map over all six blocks."""
    bad = n_del = 0
    worst = None
    for (bx, by, part), records in all_records.items():
        for r in records:
            A, dU, dV, N, kept = r["A"], r["dU"], r["dV"], r["N"], r["kept"]
            step = 1.0 / (N * 3)                            # 3 samples per sub-edge
            m = int(1.0 / step)
            for iu in range(1, m):
                for jv in range(1, m - iu):
                    u, v = iu * step * N, jv * step * N     # barycentric-grid coords
                    if u + v >= N - 1e-9:
                        continue
                    i, j = int(u), int(v)
                    fu, fv = u - i, v - j
                    s = ((i, j), (i + 1, j), (i, j + 1)) if fu + fv <= 1.0 \
                        else ((i + 1, j), (i + 1, j + 1), (i, j + 1))
                    if s in kept:
                        continue
                    n_del += 1
                    x = A[0] + u * dU[0] + v * dV[0] + r["ox"]
                    z = A[2] + u * dU[2] + v * dV[2] + r["oz"]
                    if not terrain_cover(world_live, x, z):
                        bad += 1
                        worst = (part, r["ti"], round(x, 2), round(z, 2))
    print(f"HIDDEN-CUT GATE: {n_del} deleted-region samples over all changed tris, "
          f"{bad} NOT terrain-covered ({'PASS' if bad == 0 else f'FAIL worst={worst}'})")

    new_legal = to_miss = n = 0
    for (bx, by) in W.CELLS:
        x0, z1 = 64.0 * bx, -64.0 * by
        for ii in range(128):
            for jj in range(1, 128):
                x, z = x0 + ii * 0.5, z1 - jj * 0.5
                if W.block_key(x, z) != (bx, by):
                    continue
                n += 1
                a = W.full_scan(world_live, (bx, by), x, z, W.OFFSET)
                b = W.full_scan(world_staged, (bx, by), x, z, W.OFFSET)
                la = a is not None and a[4] in BOAT_LEGAL
                lb = b is not None and b[4] in BOAT_LEGAL
                if lb and not la:
                    new_legal += 1
                if a is not None and b is None:
                    to_miss += 1
    print(f"BOAT GATE: {n} sea-level columns (six blocks), NEW-legal {new_legal} "
          f"({'PASS' if new_legal == 0 else 'FAIL'}), hit->MISS {to_miss} (the cut)")
    return bad == 0 and new_legal == 0


def replay_escape(world, title):
    sx, sz = PIN[0], PIN[1] + 8.0
    walk = [s for s in W.all_sheets(world, sx, sz) if s[1] in W.WALK_OK]
    st = dict(x=sx, y=walk[0][0], z=sz, heading=math.pi)
    ring = W.Ring()
    stalled = False
    for k in range(200):
        if W.walk_step(world, ring, st) == "stall":
            stalled = True
            break
    if not stalled:
        print(f"REPLAY [{title}]: no stall in 200 ticks -> PASS (wedge gone)")
        return True
    pos0 = (st["x"], st["z"])
    for k in range(100):
        st["heading"] = math.radians(11.25 * (k % 32))
        if W.walk_step(world, ring, st) != "stall":
            print(f"REPLAY [{title}]: stalled at ({pos0[0]:.2f},{pos0[1]:.2f}), "
                  f"ESCAPED after {k} turning ticks -> PASS")
            return True
    print(f"REPLAY [{title}]: stalled at ({pos0[0]:.2f},{pos0[1]:.2f}), STILL STUCK -> FAIL")
    return False


def stage1():
    assert_no_drift()
    print("loading LIVE world ...")
    world_live = W.load_world()
    manifest, all_records = build_all(world_live)
    world_staged = W.load_world(part_src=part_src_from_staged())
    ok_v = verify(world_live, world_staged, all_records)
    print("\n--- gate 0: calibration (live still locks) ---")
    g0 = not replay_escape(world_live, "LIVE calibration")
    print(f"g0 live-still-locks: {'PASS' if g0 else 'FAIL'}")
    print("\n--- walk gates on STAGED bytes ---")
    g1 = replay_escape(world_staged, "STAGED")
    ev, hard, ringy = drive_walkers(world_staged, "STAGED")
    own0 = [e for e in ev if e["own"] == 0]
    g2 = len(own0) == 0
    print(f"g2 no own-ring-0 stalls: {'PASS' if g2 else f'FAIL {own0[:4]}'}")
    tl, cl, cells_l = static_map(world_live, "LIVE (identity)")
    ts, cs, cells_s = static_map(world_staged, "STAGED (identity)")
    g3 = cells_l == cells_s and len(ts) == 0
    print(f"g3 cold map identical: {'PASS' if g3 else 'FAIL'}")
    gates = dict(verify=ok_v, g0_live_locks=g0, g1_staged_escapes=g1,
                 g2_no_own0=g2, g3_cold_identical=g3)
    print("\n=== STAGE-1 GATES ===")
    for k, v in gates.items():
        print(f"   {k}: {'PASS' if v else 'FAIL'}")
    json.dump(gates, open(OUTD / "gates_stage1.json", "w"), indent=1)


def stage2():
    print("loading STAGED world for the bench-wide latent sweep ...")
    world_staged = W.load_world(part_src=part_src_from_staged())
    hard_c, poisonable, _cl = sweep(world_staged, "STAGED")
    hard_f = refine(world_staged, poisonable, "STAGED")
    g4 = len(hard_c) == 0 and len(hard_f) == 0
    print(f"\ng4 latent hard = 0 bench-wide: {'PASS' if g4 else 'FAIL'}")
    json.dump(dict(g4_latent_zero=g4, poisonable_n=len(poisonable)),
              open(OUTD / "gates_stage2.json", "w"), indent=1)


def deploy():
    g1 = json.load(open(OUTD / "gates_stage1.json"))
    g2 = json.load(open(OUTD / "gates_stage2.json"))
    assert all(g1.values()) and g2["g4_latent_zero"], f"gates not green: {g1} {g2} -- NO DEPLOY"
    assert_no_drift()
    manifest = json.load(open(OUTD / "manifest.json"))
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    lines = ["import shutil"]
    for key in manifest:
        bx, by, part = key.split(",")
        lp = live_path(int(bx), int(by), part)
        bk = BACKUPS / f"{lp.name}.r{by}.{ts}"
        shutil.copy2(lp, bk)
        shutil.copy2(staged_path(int(bx), int(by), part), lp)
        lines.append(f"shutil.copy2(r'{bk}', r'{lp}')")
        print(f"DEPLOYED {lp.name} (r{by})   backup: {bk.name}")
    lines.append("print('reverted the sea-cut deploy (all files)')")
    (HERE / "revert_vcorner_seacut.py").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"revert: {HERE / 'revert_vcorner_seacut.py'}")
    live_world = W.load_world()
    ok = replay_escape(live_world, "LIVE post-deploy")
    ev, hard, ringy = drive_walkers(live_world, "LIVE post-deploy")
    own0 = [e for e in ev if e["own"] == 0]
    print(f"post-deploy: replay {'PASS' if ok else 'FAIL'}, "
          f"own-ring-0 stalls {len(own0)} ({'PASS' if not own0 else 'FAIL'})")


if __name__ == "__main__":
    if "--deploy" in sys.argv:
        deploy()
    elif "--stage2" in sys.argv:
        stage2()
    else:
        stage1()
