"""THE SEA-CUT FIX — subdivide+delete-hidden on Sea4 (5,7) tri #430 (the V-corner poisoner).

Registration: VSHORE-SEAL-PREDICTION.md "THE SEA-CUT FIX ROUND" (P-F..P-H). The dual
kill: (1) hidden under-land sea deleted -> the corner-gap probe MISSES and a miss
writes nothing to the ring; (2) subdivision bounds every kept fragment below the
deflection fan's 0.875u candidate circle, so no cached sea fragment can ever answer
the whole fan again.

Default run: verify identity -> build staged -> verify staged -> run the walk/seal
gates against the STAGED bytes (no bench mutation). `--deploy`: re-verify, back up
the live file to the MAIN repo's backups/, copy staged over live, emit the revert
script, re-gate quick against live.
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

BX, BY = 5, 7
OX, OZ = 64.0 * BX, -64.0 * BY
TRI = 430
N = 8                                                       # subdivision (max edge 5.66/8 = 0.71u < 0.875u fan)
SNAP = Path(r"C:\gd\Dream-World-IX\backups\vcorner-trap-live.20260802-133500\r7\Block[5][7] Sea4.ff9mesh")
SNAP_MD5 = "1984a99f9dddf6f8d2c66d96ebc96b57"
LIVE = W.GAME / W.MOD / "FF9_Data" / "WorldMap" / f"Disc{W.DISC}" / "0_1" / f"r{BY}" / f"Block[{BX}][{BY}] Sea4.ff9mesh"
OUTD = HERE / "out" / "vcorner_seacut"
STAGED = OUTD / f"Block[{BX}][{BY}] Sea4.ff9mesh"
BACKUPS = Path(r"C:\gd\Dream-World-IX\backups")
BOAT_LEGAL = {53, 54, 57}
EXPECT_LOCAL = [(56.0, 0.0, -60.0), (60.0, 0.0, -64.0), (56.0, 0.0, -64.0)]
PIN = (376.5, -509.5)


def bary2(p, a, b, c):
    d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(d) < 1e-12:
        return None
    w0 = ((b[1] - c[1]) * (p[0] - c[0]) + (c[0] - b[0]) * (p[1] - c[1])) / d
    w1 = ((c[1] - a[1]) * (p[0] - c[0]) + (a[0] - c[0]) * (p[1] - c[1])) / d
    return w0, w1, 1.0 - w0 - w1


def terrain_cover(world, x, z):
    """Terrain geometry present at plan (x,z) at/above the sea plane -- ANY tri, no
    walk filters: hidden-from-above is about presence, not walkability."""
    bk = W.block_key(x, z)
    if bk not in world:
        return False
    terr = next(m for m in world[bk] if m["name"] == "Terrain")
    for ti in terr["grid"].get((int(x // 4), int(z // 4)), ()):
        tri = terr["tris"][ti]
        w = bary2((x, z), (tri[0][0], tri[0][2]), (tri[1][0], tri[1][2]), (tri[2][0], tri[2][2]))
        if w is None or min(w) < -1e-9:
            continue
        hy = w[0] * tri[0][1] + w[1] * tri[1][1] + w[2] * tri[2][1]
        if hy >= -0.05:
            return True
    return False


def build_staged(world):
    d = W.M.read_ff9mesh(LIVE)
    idx = d["indices"]
    t = idx[TRI * 3:TRI * 3 + 3]
    loc = [d["verts"][vi] for vi in t]
    assert all(max(abs(a - b) for a, b in zip(v, e)) < 1e-4 for v, e in zip(loc, EXPECT_LOCAL)), \
        f"tri {TRI} drifted: {loc} != {EXPECT_LOCAL} -- shared install changed, STOP"
    tans = [d["tangents"][vi] for vi in t]
    nrms = [d["normals"][vi] for vi in t]
    assert all(tans[0] == x for x in tans), f"corner tangents differ: {tans}"
    assert all(nrms[0] == x for x in nrms), f"corner normals differ: {nrms}"
    uvs = [d["uvs"][vi] for vi in t]

    A, B, C = loc
    dU = [(B[k] - A[k]) / N for k in range(3)]
    dV = [(C[k] - A[k]) / N for k in range(3)]
    verts = [list(v) for v in d["verts"]]
    normals = [list(v) for v in d["normals"]]
    uvl = [list(v) for v in d["uvs"]]
    tangents = [list(v) for v in d["tangents"]]
    grid_idx = {}

    def gv(i, j):
        if (i, j) not in grid_idx:
            wu, wv = i / N, j / N
            w0 = 1.0 - wu - wv
            verts.append([A[k] + i * dU[k] + j * dV[k] for k in range(3)])
            uvl.append([w0 * uvs[0][k] + wu * uvs[1][k] + wv * uvs[2][k] for k in range(2)])
            normals.append(list(nrms[0]))
            tangents.append(list(tans[0]))
            grid_idx[(i, j)] = len(verts) - 1
        return grid_idx[(i, j)]

    def covered_subtri(p3):
        """7 plan samples (corners, edge midpoints, centroid), ALL Terrain-covered."""
        cx = sum(p[0] for p in p3) / 3 + OX
        cz = sum(p[2] for p in p3) / 3 + OZ
        pts = [(p[0] + OX, p[2] + OZ) for p in p3]
        pts += [((pts[a][0] + pts[b][0]) / 2, (pts[a][1] + pts[b][1]) / 2)
                for a, b in ((0, 1), (1, 2), (0, 2))]
        pts.append((cx, cz))
        return all(terrain_cover(world, x, z) for (x, z) in pts)

    kept, deleted = [], []
    subs = []
    for i in range(N):
        for j in range(N - i):
            subs.append(((i, j), (i + 1, j), (i, j + 1)))
            if i + j < N - 1:
                subs.append(((i + 1, j), (i + 1, j + 1), (i, j + 1)))
    max_edge = 0.0
    for s in subs:
        p3 = [[A[k] + i * dU[k] + j * dV[k] for k in range(3)] for (i, j) in s]
        for a, b in ((0, 1), (1, 2), (0, 2)):
            e = math.dist(p3[a], p3[b])
            max_edge = max(max_edge, e)
        (deleted if covered_subtri(p3) else kept).append(s)

    new_idx = idx[:TRI * 3] + idx[TRI * 3 + 3:]
    for s in kept:
        tri_i = [gv(i, j) for (i, j) in s]
        a, b, c = (verts[v] for v in tri_i)
        ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
        if ny < 0:
            tri_i[1], tri_i[2] = tri_i[2], tri_i[1]
        new_idx += tri_i

    assert max_edge < 0.875, f"sub-edge {max_edge} >= fan diameter -- raise N"
    print(f"BUILD: {len(subs)} sub-tris -> kept {len(kept)}, deleted {len(deleted)}; "
          f"max sub-edge {max_edge:.3f}u; verts {d['vcount']} -> {len(verts)}; "
          f"tris {len(idx) // 3} -> {len(new_idx) // 3}")
    assert 0 < len(deleted) < len(subs), "degenerate cut: nothing (or everything) deleted"

    bm = W.M.blockmesh_from_ff9mesh(LIVE, disc=W.DISC, x=BX, y=BY, part="sea4")
    chan = dict(bm.chan_arrays)
    chan[CH_POS], chan[CH_NRM], chan[CH_UV], chan[CH_TAN] = verts, normals, uvl, tangents
    tris = [[new_idx[k], new_idx[k + 1], new_idx[k + 2]] for k in range(0, len(new_idx), 3)]
    out = dataclasses.replace(bm, vcount=len(verts), chan_arrays=chan,
                              flat_index=new_idx, tris=tris)
    OUTD.mkdir(parents=True, exist_ok=True)
    W.M.write_ff9mesh(out, STAGED)
    rt = W.M.read_ff9mesh(STAGED)
    assert rt["vcount"] == len(verts) and len(rt["indices"]) == len(new_idx), "round-trip mismatch"
    print(f"STAGED: {STAGED}")
    return kept, deleted, (A, dU, dV)


def verify_staged(world_live, world_staged, kept, geom):
    """P-G: hidden-cut fine sample + boat legality map."""
    A, dU, dV = geom

    def in_kept(x, z):                                      # plan point -> covered by a kept sub-tri?
        lx, lz = x - OX, z - OZ
        w = bary2((lx, lz), (A[0], A[2]), (A[0] + N * dU[0], A[2] + N * dU[2]),
                  (A[0] + N * dV[0], A[2] + N * dV[2]))
        if w is None or min(w) < -1e-9:
            return None                                     # outside the parent tri
        u, v = w[1] * N, w[2] * N
        i, j = int(u), int(v)
        fu, fv = u - i, v - j
        s = ((i, j), (i + 1, j), (i, j + 1)) if fu + fv <= 1.0 else ((i + 1, j), (i + 1, j + 1), (i, j + 1))
        return s in kept_set

    kept_set = set(kept)
    bad = n_del = n_keep = 0
    worst = None
    step = 0.1
    for ii in range(1, int(4 / step)):
        for jj in range(1, int(4 / step)):
            lx, lz = 56.0 + ii * step, -64.0 + jj * step
            w = bary2((lx, lz), (56.0, -60.0), (60.0, -64.0), (56.0, -64.0))
            if w is None or min(w) < 0.02:
                continue                                    # strictly inside the parent
            x, z = lx + OX, lz + OZ
            k = in_kept(x, z)
            if k:
                n_keep += 1
                continue
            n_del += 1
            if not terrain_cover(world_live, x, z):
                bad += 1
                worst = (round(x, 2), round(z, 2))
    print(f"HIDDEN-CUT GATE: {n_del} deleted-region samples, {bad} NOT terrain-covered "
          f"({'PASS' if bad == 0 else f'FAIL worst={worst}'}); {n_keep} kept samples")

    # boat legality over block (5,7), sea-level origin (cur_y = 0)
    changed_new_legal = 0
    to_miss = 0
    n = 0
    for ii in range(0, 256):
        for jj in range(0, 256):
            x, z = 320.0 + ii * 0.25, -512.0 + jj * 0.25   # inside (5,7): z (-512, -448)
            if z >= -448.0 or W.block_key(x, z) != (5, 7):
                continue
            n += 1
            a = W.full_scan(world_live, (5, 7), x, z, 0.0 + W.OFFSET)
            b = W.full_scan(world_staged, (5, 7), x, z, 0.0 + W.OFFSET)
            la = a is not None and a[4] in BOAT_LEGAL
            lb = b is not None and b[4] in BOAT_LEGAL
            if lb and not la:
                changed_new_legal += 1
            if a is not None and b is None:
                to_miss += 1
    print(f"BOAT GATE: {n} sea-level columns, NEW-legal {changed_new_legal} "
          f"({'PASS' if changed_new_legal == 0 else 'FAIL'}), hit->MISS {to_miss} (the cut, expected >0)")
    return bad == 0 and changed_new_legal == 0


def replay_escape(world, title):
    """The deterministic due-south walker; PASS iff no permanent lock (stall -> the
    turning player escapes within 100 ticks, ring free to refresh)."""
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
    print(f"REPLAY [{title}]: stalled at ({pos0[0]:.2f},{pos0[1]:.2f}), STILL STUCK after 100 -> FAIL")
    return False


def run_gates(world_live, world_staged):
    print("\n--- gate 0: calibration (live still traps) ---")
    g0 = not replay_escape(world_live, "LIVE calibration")   # live must still LOCK
    print(f"g0 live-still-locks: {'PASS' if g0 else 'FAIL (defect vanished from live?!)'}")

    print("\n--- gates on STAGED bytes ---")
    g1 = replay_escape(world_staged, "STAGED")
    ev, hard, ringy = drive_walkers(world_staged, "STAGED")
    own0 = [e for e in ev if e["own"] == 0]
    g2 = len(own0) == 0
    print(f"g2 no own-ring-0 stalls: {'PASS' if g2 else f'FAIL {own0[:4]}'}")
    tl, cl, cells_l = static_map(world_live, "LIVE (for the identity gate)")
    ts, cs, cells_s = static_map(world_staged, "STAGED")
    g3 = cells_l == cells_s and len(ts) == 0
    print(f"g3 cold map identical: {'PASS' if g3 else 'FAIL'}")
    hard_c, poisonable, _cl = sweep(world_staged, "STAGED")
    hard_f = refine(world_staged, poisonable, "STAGED")
    g4 = len(hard_c) == 0 and len(hard_f) == 0
    print(f"g4 latent hard = 0 bench-wide: {'PASS' if g4 else 'FAIL'}")
    gates = dict(g0_live_locks=g0, g1_staged_escapes=g1, g2_no_own0=g2,
                 g3_cold_identical=g3, g4_latent_zero=g4)
    print("\n=== SEA-CUT GATES ===")
    for k, v in gates.items():
        print(f"   {k}: {'PASS' if v else 'FAIL'}")
    json.dump(gates, open(OUTD / "gates.json", "w"), indent=1)
    return all(gates.values())


def deploy():
    assert STAGED.is_file(), "no staged mesh -- run the build first"
    live_md5 = hashlib.md5(LIVE.read_bytes()).hexdigest()
    assert live_md5 == SNAP_MD5, f"live Sea4 drifted since gating ({live_md5}) -- STOP, re-gate"
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bk = BACKUPS / f"Block[{BX}][{BY}] Sea4.ff9mesh.{ts}"
    shutil.copy2(LIVE, bk)
    shutil.copy2(STAGED, LIVE)
    rv = HERE / "revert_vcorner_seacut.py"
    rv.write_text(
        "import shutil\n"
        f"shutil.copy2(r'{bk}', r'{LIVE}')\n"
        f"print('reverted Sea4 (5,7) from {bk.name}')\n", encoding="utf-8")
    print(f"DEPLOYED {STAGED.name} -> {LIVE}\nbackup: {bk}\nrevert: {rv}")
    live_world = W.load_world()
    ok = replay_escape(live_world, "LIVE post-deploy")
    ev, hard, ringy = drive_walkers(live_world, "LIVE post-deploy")
    own0 = [e for e in ev if e["own"] == 0]
    print(f"post-deploy: replay {'PASS' if ok else 'FAIL'}, own-ring-0 stalls {len(own0)} "
          f"({'PASS' if not own0 else 'FAIL'})")


def main():
    if "--deploy" in sys.argv:
        deploy()
        return
    live_md5 = hashlib.md5(LIVE.read_bytes()).hexdigest()
    assert live_md5 == SNAP_MD5, f"live Sea4 drifted ({live_md5} != snapshot) -- re-decode first"
    print("loading LIVE world ...")
    world_live = W.load_world()
    kept, deleted, geom = build_staged(world_live)
    world_staged = W.load_world(part_src={(BX, BY, "Sea4"): STAGED})
    ok_v = verify_staged(world_live, world_staged, kept, geom)
    ok_g = run_gates(world_live, world_staged)
    print(f"\nVERDICT: verify {'PASS' if ok_v else 'FAIL'}, gates {'PASS' if ok_g else 'FAIL'}"
          + ("" if ok_v and ok_g else " -- DO NOT DEPLOY"))


if __name__ == "__main__":
    main()
