"""READ-ONLY re-verification of every premise of the Lantern Quay marker design (live install)."""
import sys, math, collections
sys.path.insert(0, r"C:\gd\Dream-World-IX\.claude\worktrees\gui-workspace-improvements-277c74\ff9mapkit")
from ff9mapkit.world import mesh as M
from ff9mapkit.world import extract as W

G = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"
MOD = G + r"\FF9CustomMap-world\FF9_Data\WorldMap"
BX, BY = 0, 18
OX, OZ = W.block_world_origin(BX, BY)


def idall_of(bm, t):
    return int(round(bm.tangents[bm.flat_index[3 * t]][0]))


def dec(i):
    return W.decode_id(i)


def tri_pts(bm, t, ox, oz):
    idx = bm.flat_index[3 * t:3 * t + 3]
    return [(bm.verts[k][0] + ox, bm.verts[k][1], bm.verts[k][2] + oz) for k in idx]


def ny_of(pts):
    a, b, c = pts
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return ny / L


print("=" * 96)
print("PREMISE 1 -- the quay TRIGGER cluster in the DEPLOYED Block[0][18] Terrain (both discs)")
print("=" * 96)
ters = {}
for disc in (1, 4):
    p = f"{MOD}\\Disc{disc}\\0_1\\r18\\Block[0][18] Terrain.ff9mesh"
    bm = M.blockmesh_from_ff9mesh(p, disc=disc, x=BX, y=BY, part="terrain")
    ters[disc] = bm
    ev = []
    for t in range(len(bm.tris)):
        i = idall_of(bm, t)
        if dec(i)["event"]:
            pts = tri_pts(bm, t, OX, OZ)
            ev.append((t, i, pts))
    xs = [p2[0] for e in ev for p2 in e[2]]
    zs = [p2[2] for e in ev for p2 in e[2]]
    ys = [p2[1] for e in ev for p2 in e[2]]
    print(f"disc{disc}: terrain verts={bm.vcount} tris={len(bm.tris)}   EVENT tris={len(ev)}"
          f"  idall set={sorted({e[1] for e in ev})}")
    if ev:
        print(f"        union bbox x[{min(xs):.2f},{max(xs):.2f}] z[{min(zs):.2f},{max(zs):.2f}] "
              f"y[{min(ys):.2f},{max(ys):.2f}]  decoded={dec(ev[0][1])}")

IDALL_SKIP = {4078, 4088, 2040}


def ground(parts, wx, wz, *, ignore_filters=False):
    """First-mesh/first-tri-in-buffer-order wins, up-facing geometric winding. parts = [(name, bm, ox, oz)]."""
    lx, lz = wx, wz
    for (nm, bm, ox, oz) in parts:
        for t in range(len(bm.tris)):
            i = idall_of(bm, t)
            if not ignore_filters and i in IDALL_SKIP:
                continue
            a, b, c = tri_pts(bm, t, ox, oz)
            if not ignore_filters and ny_of((a, b, c)) <= 0.1:
                continue
            d = (b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])
            if abs(d) < 1e-12:
                continue
            w1 = ((lx - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (lz - a[2])) / d
            w2 = ((b[0] - a[0]) * (lz - a[2]) - (lx - a[0]) * (b[2] - a[2])) / d
            if w1 < -1e-9 or w2 < -1e-9 or w1 + w2 > 1 + 1e-9:
                continue
            y = a[1] + w1 * (b[1] - a[1]) + w2 * (c[1] - a[1])
            return (nm, y, i, t)
    return None


print()
print("=" * 96)
print("PREMISE 2 -- ground query at the key points (Object FIRST in buffer order, then Terrain)")
print("=" * 96)
for disc in (1, 4):
    objp = f"{MOD}\\Disc{disc}\\0_1\\r18\\Block[0][18] Object.ff9mesh"
    ob = M.blockmesh_from_ff9mesh(objp, disc=disc, x=BX, y=BY, part="object")
    parts = [("Object", ob, OX, OZ), ("Terrain", ters[disc], OX, OZ)]
    print(f"-- disc{disc}: Object mesh verts={ob.vcount} tris={len(ob.tris)}")
    for t in range(len(ob.tris)):
        pts = tri_pts(ob, t, OX, OZ)
        print(f"     obj tri{t}: idall={idall_of(ob, t)} ny={ny_of(pts):+.3f} "
              f"y[{min(p[1] for p in pts):.2f},{max(p[1] for p in pts):.2f}] "
              f"x[{min(p[0] for p in pts):.2f},{max(p[0] for p in pts):.2f}] "
              f"z[{min(p[2] for p in pts):.2f},{max(p[2] for p in pts):.2f}] uv={ob.uvs[ob.flat_index[3*t]]}")
    for nm, (wx, wz) in [("trigger (48,-1168)", (48.0, -1168.0)),
                         ("ARRIVAL (60,-1168)", (60.0, -1168.0)),
                         ("marker N (48,-1158)", (48.0, -1158.0)),
                         ("marker S (48,-1178)", (48.0, -1178.0)),
                         ("anchor  (48,-1168)", (48.0, -1168.0))]:
        g = ground(parts, wx, wz)
        gi = ground(parts, wx, wz, ignore_filters=True)
        s = "MISS" if g is None else f"{g[0]} y={g[1]:.3f} idall={g[2]} {dec(g[2])}"
        si = "MISS" if gi is None else f"{gi[0]} y={gi[1]:.3f} idall={gi[2]}"
        print(f"   {nm:<22} filtered-> {s:<70} ignoreExc-> {si}")

print()
print("=" * 96)
print("PREMISE 3 -- the DONOR post: stock Block[18][13] Object (pristine p0data)")
print("=" * 96)
d = W.read_block(18, 13, disc=1, lod="0_1", part="object")
dox, doz = W.block_world_origin(18, 13)
xs = [v[0] for v in d.verts]; ys = [v[1] for v in d.verts]; zs = [v[2] for v in d.verts]
print(f"verts={d.vcount} tris={len(d.tris)} stride={d.stride} channels={sorted(d.channels)}")
print(f"local bbox x[{min(xs):.3f},{max(xs):.3f}] y[{min(ys):.3f},{max(ys):.3f}] z[{min(zs):.3f},{max(zs):.3f}]")
print(f"footprint = {max(xs)-min(xs):.3f} x {max(zs)-min(zs):.3f}   height = {max(ys)-min(ys):.3f}")
print(f"world origin of donor block = ({dox}, {doz}) -> world x[{min(xs)+dox:.2f},{max(xs)+dox:.2f}] "
      f"z[{min(zs)+doz:.2f},{max(zs)+doz:.2f}]")
h = collections.Counter(idall_of(d, t) for t in range(len(d.tris)))
print("donor idall histogram:", {k: (v, dec(k)) for k, v in h.items()})
uvs = d.uvs
print(f"donor UV count={len(uvs)} umin={min(u[0] for u in uvs):.5f} umax={max(u[0] for u in uvs):.5f} "
      f"vmin={min(u[1] for u in uvs):.5f} vmax={max(u[1] for u in uvs):.5f}")
print("donor per-tri:")
for t in range(len(d.tris)):
    pts = tri_pts(d, t, 0, 0)
    idx = d.flat_index[3 * t:3 * t + 3]
    print(f"  tri{t}: ny={ny_of(pts):+.3f} y[{min(p[1] for p in pts):.2f},{max(p[1] for p in pts):.2f}] "
          f"uv={[tuple(round(c,5) for c in uvs[k]) for k in idx]}")
print("donor tangents (all 4 comps of first vert of each tri):")
for t in range(len(d.tris)):
    print("   ", [round(c, 4) for c in d.tangents[d.flat_index[3 * t]]])

print()
print("=" * 96)
print("PREMISE 4 -- the reclaim donor (0,0)'s pristine Object (what the stub blanks)")
print("=" * 96)
try:
    p00 = W.read_block(0, 0, disc=1, lod="0_1", part="object")
    print(f"pristine (0,0) Object: verts={p00.vcount} tris={len(p00.tris)} "
          f"idall={dict(collections.Counter(idall_of(p00, t) for t in range(len(p00.tris))))}")
except Exception as ex:
    print("read (0,0) object failed:", ex)
try:
    pris18 = W.read_block(0, 18, disc=1, lod="0_1", part="terrain")
    print(f"pristine (0,18) Terrain: verts={pris18.vcount} tris={len(pris18.tris)}")
except Exception as ex:
    print("pristine (0,18) terrain -> NO PARTS (expected for a reclaimed ocean cell):", type(ex).__name__, ex)
