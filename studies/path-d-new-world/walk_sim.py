"""THE BENCH WALK SIMULATOR (study B) — the decoded walk query over the deployed bytes.

Implements studies/path-d-new-world/WALK-QUERY-DECODE.md's banked algorithm exactly:
unbounded down-ray from y+2.34375, first-hit-in-order (mesh registration order, then
buffer order), the 10-slot ring with the corrected probe order and NO invalidation, the
filter-free cached retest, the on-foot topograph mask, the +/-78.75deg deflection fan,
and the two-probe slope-corrected snap commit. Core geometry lifted from the proven
scratch/synth-island/sim_place.py (in-game validated 2026-07-07); its dead-parameter
2.8u drop cap is corrected to UNBOUNDED per the decode.

Registration + calibration gates: BENCH-WALK-SIM.md. READ-ONLY: no deploy, no bench
mutation.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit import config                                # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import mesh as M                       # noqa: E402

GAME = Path(config.find_game_path(None))
MOD = "FF9CustomMap-world"
DISC = 9
CELLS = [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)]
BLOCK = 64.0

# WMWorld.LoadBlock framework registration order over the parts the bench ships (BL-6)
FRAMEWORK_ORDER = ["Object", "Terrain", "Beach1", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5"]

IDALL_SKIP = {4078, 4088, 2040}                             # WMPhysics full-scan skip
VETO = 0x31EE                                               # flight-only; abandons the WHOLE mesh
OFFSET = 2.34375                                            # ff9.rayStartOffsetY
SPEED = 0.4375                                              # on-foot XZSpeed per tick
# on-foot limit mask {0x0010667F, 0xD8FF3CFF} bit-decoded (FC-3, double-confirmed)
WALK_OK = frozenset(list(range(0, 8)) + list(range(10, 14)) + list(range(16, 24))
                    + [27, 28, 30, 31] + list(range(32, 39)) + [41, 42, 45, 46, 52])

PIN = (434.0, -542.0)                                       # the owner's defect locus
PIN_R = 8.0
SUNKEN_EPS = 0.3                                            # committed y below top walk surface
DEDUP_EPS = 0.02
GRID = 0.5
REGION = (320.0, 512.0, -576.0, -448.0)                     # x0, x1, z0, z1 (blocks 5-7 x 7-8)
PRISTINE_BK = Path(r"C:\gd\Dream-World-IX\backups\terrace-strip-prewall.20260731-220001")
OUTD = HERE / "out" / "walk_sim"


# ---------------------------------------------------------------- world loading
def load_world(terrain_src=None):
    """Blocks -> meshes in framework order; tris in buffer order, world frame.
    terrain_src: optional dict (bx,by)->Path replacing the live Terrain file (controls)."""
    root = GAME / MOD / "FF9_Data" / "WorldMap" / f"Disc{DISC}" / "0_1"
    world = {}
    for (bx, by) in CELLS:
        ox, oz = BLOCK * bx, -BLOCK * by
        meshes = []
        for part in FRAMEWORK_ORDER:
            p = root / f"r{by}" / f"Block[{bx}][{by}] {part}.ff9mesh"
            if part == "Terrain" and terrain_src is not None:
                p = terrain_src.get((bx, by), p)
            if not p.is_file():
                continue
            bm = M.blockmesh_from_ff9mesh(p, disc=DISC, x=bx, y=by, part=part.lower())
            pos = bm.chan_arrays[X.CH_POS]
            tan = bm.chan_arrays[X.CH_TAN]
            tris, grid = [], defaultdict(list)
            for ti, t in enumerate(bm.tris):
                a = (pos[t[0]][0] + ox, pos[t[0]][1], pos[t[0]][2] + oz)
                b = (pos[t[1]][0] + ox, pos[t[1]][1], pos[t[1]][2] + oz)
                c = (pos[t[2]][0] + ox, pos[t[2]][1], pos[t[2]][2] + oz)
                mapid = int(round(tan[t[0]][0]))            # engine: tangents[triangles[i*3]].x
                topo = (mapid & 0xFC) >> 2
                tris.append((a, b, c, mapid, topo, up_ny(a, b, c)))
                x0 = min(a[0], b[0], c[0]); x1 = max(a[0], b[0], c[0])
                z0 = min(a[2], b[2], c[2]); z1 = max(a[2], b[2], c[2])
                for gi in range(int(x0 // 4), int(x1 // 4) + 1):
                    for gj in range(int(z0 // 4), int(z1 // 4) + 1):
                        grid[(gi, gj)].append(ti)
                tris[-1] = tris[-1] + ((x0, x1, z0, z1),)
            meshes.append(dict(name=part, tris=tris, grid=grid))
        world[(bx, by)] = meshes
    return world


def up_ny(a, b, c):
    """Engine TriangleNormals: normalized cross(v1-v0, v2-v0), y component (sim_place)."""
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    ny = uz * vx - ux * vz
    L = math.sqrt((uy * vz - uz * vy) ** 2 + ny * ny + (ux * vy - uy * vx) ** 2) or 1.0
    return ny / L


def bary_y(x, z, tri):
    """Y where the vertical line pierces the tri's plane, or None if outside (XZ barycentric,
    inclusive within float eps -- the engine's own strict-in-float boundary quirk noted)."""
    a, b, c = tri[0], tri[1], tri[2]
    d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
    if abs(d) < 1e-12:
        return None
    w0 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
    w1 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
    w2 = 1.0 - w0 - w1
    if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
        return None
    return w0 * a[1] + w1 * b[1] + w2 * c[1]


def block_key(x, z):
    return (int(x / 64.0), int(abs(z) / 64.0))              # C# (Int32) truncation


# ---------------------------------------------------------------- the engine query
class Ring:
    """ff9.s_moveCHRCache: 10 slots, Number semantics per the decode's correction."""
    __slots__ = ("blocks", "mesh_i", "tri_i", "number")

    def __init__(self):
        self.blocks = [None] * 10
        self.mesh_i = [0] * 10
        self.tri_i = [0] * 10
        self.number = 0


def full_scan(world, bk, x, z, origin_y):
    """First-in-order over meshes then buffer order; full-scan filters; 0x31EE abandons
    the mesh. Returns (mesh_i, tri_i, y, mapid, topo) or None."""
    cell = (int(x // 4), int(z // 4))
    for mi, mesh in enumerate(world[bk]):
        cand = mesh["grid"].get(cell)
        if not cand:
            continue
        tris = mesh["tris"]
        best = None
        for ti in cand:                                     # grid lists are built ascending -> buffer order
            tri = tris[ti]
            if tri[3] in IDALL_SKIP or tri[5] <= 0.1:
                continue
            hy = bary_y(x, z, tri)
            if hy is None or hy > origin_y:
                continue
            best = (mi, ti, hy, tri[3], tri[4])
            break
        if best is not None:
            if best[3] == VETO:
                continue                                    # veto: abandon this WHOLE mesh
            return best
    return None


def ground_query(world, ring, x, z, cur_y):
    """w_nwpHit: cached probe first (filter-free), else full scan + write-back."""
    bk = block_key(x, z)
    if bk not in world:
        return None
    origin_y = cur_y + OFFSET
    if ring is not None:
        for i in range(10):
            s = (ring.number + i) % 10
            if ring.blocks[s] != bk:
                continue
            mesh = world[bk][ring.mesh_i[s]]
            tri = mesh["tris"][ring.tri_i[s]]
            hy = bary_y(x, z, tri)                          # NO mapid skip, NO normal filter
            if hy is None or hy > origin_y:
                continue
            if tri[3] == VETO:
                continue                                    # slot fails, probe goes on
            return (ring.mesh_i[s], ring.tri_i[s], hy, tri[3], tri[4], "cache")
    f = full_scan(world, bk, x, z, origin_y)
    if f is None:
        return None
    if ring is not None:
        ring.number = (ring.number + 1) % 10
        ring.blocks[ring.number] = bk
        ring.mesh_i[ring.number] = f[0]
        ring.tri_i[ring.number] = f[1]
    return f + ("scan",)


def round_check(world, ring, px, py, pz, heading, speed):
    """w_movementRoundCheck: candidate at new (x,z) from OLD y; miss/mask reject."""
    nx = px + math.sin(heading) * speed
    nz = pz + math.cos(heading) * speed
    q = ground_query(world, ring, nx, nz, py)
    if q is None or q[4] not in WALK_OK:
        return None
    return (nx, q[2], nz, q)


def walk_step(world, ring, st):
    """One tick of w_movementControl: the deflection fan + the two-probe commit.
    st = dict(x, y, z, heading). Returns event string."""
    for magd in [11.25 * k for k in range(8)]:
        for sgn in ((1,) if magd == 0 else (1, -1)):
            h = st["heading"] + sgn * math.radians(magd)
            p1 = round_check(world, ring, st["x"], st["y"], st["z"], h, SPEED)
            if p1 is None:
                continue
            dx, dy, dz = p1[0] - st["x"], p1[1] - st["y"], p1[2] - st["z"]
            num8 = math.sqrt(dx * dx + dy * dy + dz * dz)   # 3D on land classes
            num9 = SPEED * SPEED / num8 if num8 > 1e-9 else SPEED
            p2 = round_check(world, ring, st["x"], st["y"], st["z"], h, num9)
            if p2 is None:
                continue
            st["x"], st["y"], st["z"] = p2[0], p2[1], p2[2]
            return "move" if magd == 0 else "deflect"
    return "stall"


# ---------------------------------------------------------------- census (static)
def all_sheets(world, x, z):
    """Every full-scan-filter-passing intersection on the vertical line, in scan order.
    Returns list of (y, topo, mesh_i, ti) deduped by y (DEDUP_EPS), order preserved."""
    bk = block_key(x, z)
    if bk not in world:
        return []
    cell = (int(x // 4), int(z // 4))
    out = []
    for mi, mesh in enumerate(world[bk]):
        for ti in mesh["grid"].get(cell, ()):
            tri = mesh["tris"][ti]
            if tri[3] in IDALL_SKIP or tri[5] <= 0.1 or tri[3] == VETO:
                continue
            hy = bary_y(x, z, tri)
            if hy is None:
                continue
            if any(abs(hy - y0) <= DEDUP_EPS for (y0, _, _, _) in out):
                continue
            out.append((hy, tri[4], mi, ti))
    return out


def census(world, title):
    """The two-sheet map over the region: stacked-walkable points, gaps, inversions."""
    x0, x1, z0, z1 = REGION
    nx = int((x1 - x0) / GRID) + 1
    nz = int((z1 - z0) / GRID) + 1
    stacked = {}                                            # (i,j) -> record
    blocked_under = 0
    inversions = 0
    npts = 0
    for i in range(nx):
        x = x0 + i * GRID
        for j in range(nz):
            z = z0 + j * GRID
            sh = all_sheets(world, x, z)
            if not sh:
                continue
            npts += 1
            walk = [s for s in sh if s[1] in WALK_OK]
            top_all = max(s[0] for s in sh)
            first = sh[0]
            if len(walk) >= 2:
                ys = sorted(s[0] for s in walk)
                gap = ys[-1] - ys[0]
                inv = first[0] < top_all - DEDUP_EPS
                stacked[(i, j)] = dict(x=x, z=z, gap=gap, n=len(walk),
                                       ys=[round(y, 3) for y in ys], inv=inv,
                                       first_topo=first[1])
                if inv:
                    inversions += 1
            elif len(walk) == 1 and any(s[1] not in WALK_OK and s[0] < walk[0][0] - DEDUP_EPS
                                        for s in sh):
                blocked_under += 1                          # rule-(f) class (moat trap fodder)
    # cluster stacked points, 8-connected
    seen, clusters = set(), []
    for key in stacked:
        if key in seen:
            continue
        comp, stack = [], [key]
        seen.add(key)
        while stack:
            k = stack.pop()
            comp.append(k)
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    nb = (k[0] + di, k[1] + dj)
                    if nb in stacked and nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
        pts = [stacked[k] for k in comp]
        cx = sum(p["x"] for p in pts) / len(pts)
        cz = sum(p["z"] for p in pts) / len(pts)
        clusters.append(dict(
            n=len(pts), cx=round(cx, 1), cz=round(cz, 1),
            max_gap=round(max(p["gap"] for p in pts), 3),
            armed=sum(1 for p in pts if p["gap"] > OFFSET),
            inv=sum(1 for p in pts if p["inv"]),
            pin_d=round(math.hypot(cx - PIN[0], cz - PIN[1]), 1),
            bbox=[round(min(p["x"] for p in pts), 1), round(max(p["x"] for p in pts), 1),
                  round(min(p["z"] for p in pts), 1), round(max(p["z"] for p in pts), 1)]))
    clusters.sort(key=lambda c: -c["n"])
    pin_dmin = min((math.hypot(p["x"] - PIN[0], p["z"] - PIN[1]) for p in stacked.values()),
                   default=float("inf"))
    print(f"\n=== CENSUS [{title}]: {npts} land pts, {len(stacked)} stacked-walkable, "
          f"{inversions} order-inversions, {blocked_under} blocked-under-walkable, "
          f"pin_dmin={pin_dmin:.2f} ===")
    for c in clusters[:12]:
        print(f"   cluster n={c['n']:4d} at ({c['cx']:6.1f},{c['cz']:7.1f}) "
              f"max_gap={c['max_gap']:6.2f} armed={c['armed']:4d} inv={c['inv']:4d} "
              f"pin_d={c['pin_d']:6.1f} bbox={c['bbox']}")
    return stacked, clusters, pin_dmin


# ---------------------------------------------------------------- trajectories (dynamic)
def top_walk_surface(world, x, z):
    ys = [s[0] for s in all_sheets(world, x, z) if s[1] in WALK_OK]
    return max(ys) if ys else None


def run_walkers(world, targets, title, n_headings=12, steps=90):
    """Walkers crossing each target from n_headings directions, cold ring warmed on
    approach. Events: SUNKEN (y < top walk surface - eps), STALL, POP (dy > 1.0)."""
    events = []
    for (tx, tz, tag) in targets:
        for hk in range(n_headings):
            th = 2 * math.pi * hk / n_headings
            sx, sz = tx - 15.0 * math.sin(th), tz - 15.0 * math.cos(th)
            r = 15.0
            while r < 26.0:
                sx, sz = tx - r * math.sin(th), tz - r * math.cos(th)
                sh = all_sheets(world, sx, sz)
                walk = [s for s in sh if s[1] in WALK_OK]
                if len(walk) == 1:
                    break
                r += 2.0
            else:
                continue                                    # no clean spawn on this heading
            st = dict(x=sx, y=walk[0][0], z=sz, heading=th)
            ring = Ring()
            for k in range(steps):
                ev = walk_step(world, ring, st)
                top = top_walk_surface(world, st["x"], st["z"])
                if ev == "stall":
                    events.append(dict(tag=tag, hd=hk, step=k, ev="STALL",
                                       x=round(st["x"], 2), z=round(st["z"], 2),
                                       y=round(st["y"], 2)))
                    break
                if top is not None and st["y"] < top - SUNKEN_EPS:
                    events.append(dict(tag=tag, hd=hk, step=k, ev="SUNKEN",
                                       x=round(st["x"], 2), z=round(st["z"], 2),
                                       y=round(st["y"], 2), top=round(top, 2)))
    kinds = defaultdict(int)
    for e in events:
        kinds[(e["tag"], e["ev"])] += 1
    print(f"\n=== WALKERS [{title}]: {len(events)} events ===")
    for (tag, ev), n in sorted(kinds.items()):
        print(f"   {tag:24s} {ev:7s}: {n}")
    return events


# ---------------------------------------------------------------- main
def main():
    OUTD.mkdir(parents=True, exist_ok=True)
    csvs = list(GAME.glob("FF9CustomMap*/**/TransportControls.csv"))
    print(f"TransportControls.csv in mod folders: {[str(p) for p in csvs] or 'NONE (hardcoded mask stands)'}")

    print("\nloading LIVE world (the shingle build) ...")
    live = load_world()
    for bk in sorted(live):
        print(f"   block {bk}: " + ", ".join(f"{m['name']}({len(m['tris'])})" for m in live[bk]))

    stacked, clusters, pin_dmin = census(live, "LIVE shingle build")

    print(f"\nPIN check: nearest stacked-walkable point to {PIN}: {pin_dmin:.2f}u")

    targets = [(PIN[0], PIN[1], "PIN(434,-542)")]
    for c in clusters[:6]:
        targets.append((c["cx"], c["cz"], f"cluster@({c['cx']},{c['cz']})"))
    ev_live = run_walkers(live, targets, "LIVE")

    print("\nloading PRISTINE control (backup Terrain) ...")
    tsrc = {}
    for (bx, by) in CELLS:
        p = PRISTINE_BK / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if p.is_file():
            tsrc[(bx, by)] = p
    print(f"   pristine Terrain files: {len(tsrc)}/6")
    pristine = load_world(terrain_src=tsrc)
    p_stacked, p_clusters, _p_dmin = census(pristine, "PRISTINE control")
    ev_pris = run_walkers(pristine, targets, "PRISTINE (same targets)")

    sunken_live = sum(1 for e in ev_live if e["ev"] == "SUNKEN")
    sunken_pris = sum(1 for e in ev_pris if e["ev"] == "SUNKEN")
    gates = dict(
        g1_strips_exist=len(stacked) > 0,
        g2_pin_reproduced=pin_dmin <= PIN_R,
        g3_walkers_sink=sunken_live > 0,
        g4_pristine_clean=(len(p_stacked) == 0 and sunken_pris == 0),
    )
    print("\n=== CALIBRATION GATES ===")
    for k, v in gates.items():
        print(f"   {k}: {'PASS' if v else 'FAIL'}")

    json.dump(dict(gates=gates, clusters=clusters, pristine_clusters=p_clusters,
                   events_live=ev_live, events_pristine=ev_pris,
                   stacked_n=len(stacked), pristine_stacked_n=len(p_stacked)),
              open(OUTD / "report.json", "w"), indent=1)
    print(f"\nreport: {OUTD / 'report.json'}")


if __name__ == "__main__":
    main()
