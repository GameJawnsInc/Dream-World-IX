"""READ-ONLY probe of the DEPLOYED Lantern Quay block (0,18): event tiles, ground, free space."""
import sys, math
sys.path.insert(0, r"C:\gd\Dream-World-IX\.claude\worktrees\gui-workspace-improvements-277c74\ff9mapkit")
from ff9mapkit.world import mesh as M
from ff9mapkit.world import extract as W

G = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"
BASE = G + r"\FF9CustomMap-world\FF9_Data\WorldMap\Disc1\0_1\r18"
BX, BY = 0, 18
OX, OZ = W.block_world_origin(BX, BY)
print("block origin (world):", OX, OZ)

ter = M.blockmesh_from_ff9mesh(BASE + r"\Block[0][18] Terrain.ff9mesh", disc=1, x=BX, y=BY, part="terrain")
print("terrain: verts=%d tris=%d" % (ter.vcount, len(ter.tris)))

V = ter.verts
T = ter.tangents
fi = ter.flat_index


def idall_of(t):
    return int(round(T[fi[3 * t]][0]))


def decode(i):
    return {"event": (i & 0xC000) >> 14, "area": (i & 0x3F00) >> 8, "topo": (i & 0xFC) >> 2}


# ---- 1. every tri carrying event bits -> its world XZ centroid + extent
ev = []
for t in range(len(fi) // 3):
    i = idall_of(t)
    d = decode(i)
    if d["event"]:
        idx = fi[3 * t:3 * t + 3]
        pts = [V[k] for k in idx]
        cx = sum(p[0] for p in pts) / 3 + OX
        cz = sum(p[2] for p in pts) / 3 + OZ
        ev.append((t, i, d, cx, cz,
                   min(p[0] for p in pts) + OX, max(p[0] for p in pts) + OX,
                   min(p[2] for p in pts) + OZ, max(p[2] for p in pts) + OZ))
print("\n=== EVENT TILES (idall event bits set): %d tris ===" % len(ev))
if ev:
    xs0 = min(e[5] for e in ev); xs1 = max(e[6] for e in ev)
    zs0 = min(e[7] for e in ev); zs1 = max(e[8] for e in ev)
    print("  union world bbox: x[%.2f, %.2f]  z[%.2f, %.2f]" % (xs0, xs1, zs0, zs1))
    print("  idall values:", sorted({e[1] for e in ev}), "->", [decode(v) for v in sorted({e[1] for e in ev})])
    for e in ev[:40]:
        print("   tri%-5d idall=%-6d ev=%d area=%-3d topo=%-3d  centroid=(%.2f, %.2f)"
              % (e[0], e[1], e[2]["event"], e[2]["area"], e[2]["topo"], e[3], e[4]))

# ---- 2. ground query (walk convention) on a grid near the quay
IDALL_SKIP = {4078, 4088, 2040}


def ground(wx, wz, *, ignore_filters=False):
    """First-tri-in-buffer-order wins; up-facing geometric winding; returns (y, idall) or None."""
    lx, lz = wx - OX, wz - OZ
    for t in range(len(fi) // 3):
        i = idall_of(t)
        if not ignore_filters and i in IDALL_SKIP:
            continue
        idx = fi[3 * t:3 * t + 3]
        a, b, c = V[idx[0]], V[idx[1]], V[idx[2]]
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        ny = uz * vx - ux * vz
        L = math.sqrt((uy * vz - uz * vy) ** 2 + ny * ny + (ux * vy - uy * vx) ** 2) or 1.0
        if not ignore_filters and ny / L <= 0.1:
            continue
        d = (b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])
        if abs(d) < 1e-12:
            continue
        w1 = ((lx - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (lz - a[2])) / d
        w2 = ((b[0] - a[0]) * (lz - a[2]) - (lx - a[0]) * (b[2] - a[2])) / d
        if w1 < -1e-9 or w2 < -1e-9 or w1 + w2 > 1 + 1e-9:
            continue
        y = a[1] + w1 * (b[1] - a[1]) + w2 * (c[1] - a[1])
        return (y, i, t)
    return None


print("\n=== GROUND GRID around the quay (walk convention) ===")
print("     wx     wz      y  idall  ev area topo")
for wz in range(-1184, -1151, 4):
    for wx in range(28, 81, 4):
        g = ground(float(wx), float(wz))
        if g is None:
            print("  %6d %6d   MISS" % (wx, wz))
        else:
            d = decode(g[1])
            print("  %6d %6d %6.2f %6d  %d  %3d  %3d" % (wx, wz, g[0], g[1], d["event"], d["area"], d["topo"]))

print("\n=== KEY POINTS ===")
for name, (wx, wz) in [("trigger (48,-1168)", (48.0, -1168.0)), ("arrival (60,-1168)", (60.0, -1168.0))]:
    g = ground(wx, wz)
    print(" %-22s ->" % name, "MISS" if g is None else
          ("y=%.3f idall=%d %s tri=%d" % (g[0], g[1], decode(g[1]), g[2])))

# ---- 3. topograph histogram + land extent
import collections
h = collections.Counter()
for t in range(len(fi) // 3):
    h[decode(idall_of(t))["topo"]] += 1
print("\ntopograph histogram (terrain):", dict(sorted(h.items())))
xs = [v[0] + OX for v in V]; zs = [v[2] + OZ for v in V]; ys = [v[1] for v in V]
print("terrain world bbox: x[%.2f, %.2f] z[%.2f, %.2f] y[%.2f, %.2f]"
      % (min(xs), max(xs), min(zs), max(zs), min(ys), max(ys)))
